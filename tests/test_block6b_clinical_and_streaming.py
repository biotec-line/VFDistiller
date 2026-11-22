# -*- coding: utf-8 -*-
"""Unit- und Concurrency-Tests für Block 6b (B1/B2/B3):
- B1: QualityManager.passes() — dokumentiertes Standard-"PASS ODER QUAL"-Verhalten
      sowie explizites Opt-in `strict_qual_gate=True`.
- B2: Strikte Token-/Vorrang-Klassifikation für kombinierte ClinVar-`clin_sig`-Strings
      (`Conflicting_*` als eigene Klasse `conflicting`, `Pathogenic/Likely_pathogenic`,
      `Benign/Likely_benign`, `,`- und `;`-getrennte Mehrfachwerte) inkl. `App.apply_post_filter`.
- B3: Deterministischer Laufzeit-Concurrency-Test (< 2 s, Event/Barrier-gesteuert ohne sleeps)
      für `missing_done -> _phase_alphagenome_streaming` und `flush_pending_writes` in `Distiller`.
"""
from __future__ import annotations

import sqlite3
import threading
import time
import types
from unittest.mock import MagicMock

import pytest

import vfdistiller
from vfdistiller.db import VariantDB
from vfdistiller.filters import (
    CLIN_SIG_PRECEDENCE,
    classify_clin_sig,
    is_clin_sig_allowed,
    tokenize_clin_sig,
)
from vfdistiller.quality import QualityManager


# =============================================================================
# B1: QualityManager.passes() — PASS ODER QUAL (Default) vs. strict_qual_gate
# =============================================================================


def _make_record(
    *,
    flt: str = "PASS",
    qual: object = 50.0,
    dp: int = 30,
    gt: str = "0/1",
) -> dict:
    return {
        "filter": flt,
        "qual": qual,
        "info": f"DP={dp}",
        "fmt": "GT:DP",
        "samples": [f"{gt}:{dp}"],
    }


def test_b1_quality_manager_default_pass_or_qual_preserved():
    """Standard (`strict_qual_gate=False`): PASS-Varianten passieren auch unterhalb `qual_threshold`."""
    qm = QualityManager(preset="clinical")  # filter_pass_only=True, qual_threshold=30.0
    assert qm.get_settings()["strict_qual_gate"] is False
    assert "PASS ODER QUAL" in (QualityManager.passes.__doc__ or "")

    # FILTER=PASS mit niedrigem QUAL=5.0 oder fehlendem QUAL='.' bleibt im Default akzeptiert
    assert qm.passes(_make_record(flt="PASS", qual=5.0, dp=25)) is True
    assert qm.passes(_make_record(flt="PASS", qual=".", dp=25)) is True
    assert qm.stats["failed_qual"] == 0
    assert qm.stats["passed"] == 2

    # Nicht-PASS wird weiterhin in Stufe 1 über failed_filter abgewiesen
    assert qm.passes(_make_record(flt="LowQual", qual=99.0, dp=25)) is False
    assert qm.stats["failed_filter"] == 1


def test_b1_quality_manager_strict_qual_gate_positive_and_negative():
    """Explizite Option `strict_qual_gate=True`: QUAL >= qual_threshold greift eigenständig."""
    qm_strict = QualityManager(preset="clinical", strict_qual_gate=True)
    assert qm_strict.get_settings()["strict_qual_gate"] is True

    # Negativfälle: trotz FILTER=PASS scheitert QUAL < 30.0 bzw. unlesbares QUAL='.'
    assert qm_strict.passes(_make_record(flt="PASS", qual=12.5, dp=25)) is False
    assert qm_strict.passes(_make_record(flt="PASS", qual=".", dp=25)) is False
    assert qm_strict.stats["failed_qual"] == 2
    assert qm_strict.stats["passed"] == 0

    # Positivfälle: QUAL == Schwellwert (30.0) und QUAL > Schwellwert (45.0) passieren
    assert qm_strict.passes(_make_record(flt="PASS", qual=30.0, dp=25)) is True
    assert qm_strict.passes(_make_record(flt="PASS", qual=45.0, dp=25)) is True
    assert qm_strict.stats["passed"] == 2
    assert qm_strict.stats["failed_qual"] == 2

    # Custom-Settings und Aufruf-Override unterstützen `strict_qual_gate` symmetrisch
    qm_custom = QualityManager(preset="clinical")
    assert qm_custom.passes(_make_record(flt="PASS", qual=10.0, dp=25), strict_qual_gate=True) is False
    qm_custom.set_custom_settings(qual_threshold=40.0, strict_qual_gate=True)
    assert qm_custom.get_settings()["strict_qual_gate"] is True
    assert qm_custom.passes(_make_record(flt="PASS", qual=39.9, dp=25)) is False
    assert qm_custom.passes(_make_record(flt="PASS", qual=40.0, dp=25)) is True


# =============================================================================
# B2: Klinische `clin_sig`-Token-/Vorrang-Klassifikation & Post-Filter
# =============================================================================


@pytest.mark.parametrize(
    ("raw_sig", "expected_class"),
    [
        # Fehlende / leere Platzhalter
        (None, "missing"),
        ("", "missing"),
        (".", "missing"),
        ("-", "missing"),
        ("None", "missing"),
        ("null", "missing"),
        # Conflicting (eigene Klasse — NIEMALS `pathogenic`!)
        ("Conflicting_classifications_of_pathogenicity", "conflicting"),
        ("Conflicting classifications of pathogenicity", "conflicting"),
        ("Conflicting_interpretations_of_pathogenicity", "conflicting"),
        ("Conflicting interpretations of pathogenicity", "conflicting"),
        ("Conflicting_interpretations_of_pathogenicity; other", "conflicting"),
        ("Conflicting_classifications_of_pathogenicity, drug_response", "conflicting"),
        ("Conflicting_data_from_submitters", "conflicting"),
        ("Pathogenic/Benign", "conflicting"),
        ("Likely_pathogenic; Likely_benign", "conflicting"),
        # Pathogenic & kombinierte Pathogenic-Formen
        ("Pathogenic", "pathogenic"),
        ("Pathogenic/Likely_pathogenic", "pathogenic"),
        ("Pathogenic/Likely pathogenic", "pathogenic"),
        ("Likely_pathogenic/Pathogenic", "pathogenic"),
        ("Pathogenic, drug_response", "pathogenic"),
        ("Pathogenic; risk_factor", "pathogenic"),
        ("Pathogenic/Likely_pathogenic, other", "pathogenic"),
        ("Pathogenic_low_penetrance", "pathogenic"),
        # Likely pathogenic
        ("Likely_pathogenic", "likely_pathogenic"),
        ("Likely pathogenic", "likely_pathogenic"),
        ("Likely_pathogenic, low_penetrance", "likely_pathogenic"),
        ("Likely_pathogenic; drug_response", "likely_pathogenic"),
        # VUS / Uncertain significance
        ("Uncertain_significance", "vus"),
        ("Uncertain significance", "vus"),
        ("VUS", "vus"),
        ("Uncertain_significance/Uncertain_risk_allele", "vus"),
        # Benign & kombinierte Benign-Formen
        ("Benign", "benign"),
        ("Benign/Likely_benign", "benign"),
        ("Benign/Likely benign", "benign"),
        ("Likely_benign/Benign", "benign"),
        ("Benign, other", "benign"),
        # Likely benign
        ("Likely_benign", "likely_benign"),
        ("Likely benign", "likely_benign"),
        # Nicht-Mendelsche / sonstige Annotationen
        ("drug_response", "other"),
        ("risk_factor", "other"),
        ("not_provided", "other"),
    ],
)
def test_b2_classify_clin_sig_matrix(raw_sig, expected_class):
    assert expected_class in CLIN_SIG_PRECEDENCE
    assert classify_clin_sig(raw_sig) == expected_class


def test_b2_conflicting_never_classified_or_filtered_as_pathogenic():
    """Kerninvariante B2: Conflicting-Einträge dürfen NIEMALS durch `allow_path=False` entfallen."""
    conflicting_forms = [
        "Conflicting_classifications_of_pathogenicity",
        "Conflicting classifications of pathogenicity",
        "Conflicting_interpretations_of_pathogenicity",
        "Conflicting_interpretations_of_pathogenicity; drug_response",
        "Pathogenic/Benign",
    ]
    for sig in conflicting_forms:
        assert classify_clin_sig(sig) == "conflicting"
        # Selbst wenn Pathogenic UND Likely Pathogenic deaktiviert sind, bleibt `conflicting` eigenständig!
        assert (
            is_clin_sig_allowed(
                sig,
                allow_path=False,
                allow_likely_path=False,
                allow_vus=True,
                allow_benign=True,
                allow_likely_benign=True,
                allow_conflicting=True,
            )
            is True
        )
        # Und bei explizitem `allow_conflicting=False` wird gezielt `conflicting` gefiltert:
        assert is_clin_sig_allowed(sig, allow_path=True, allow_conflicting=False) is False


def test_b2_combined_pathogenic_and_benign_filter_gates():
    """Prüft alle kombinierten ClinVar-Formen gegen die einzelnen Allow-Flags."""
    assert vfdistiller.classify_clin_sig is classify_clin_sig
    assert vfdistiller.is_clin_sig_allowed is is_clin_sig_allowed
    assert tokenize_clin_sig("Pathogenic/Likely_pathogenic; drug_response") == [
        "pathogenic",
        "likely pathogenic",
        "drug response",
    ]

    # allow_path=False, allow_likely_path=True -> Pathogenic/Likely_pathogenic MUSS gesperrt werden,
    # reines Likely_pathogenic MUSS sichtbar bleiben!
    assert (
        is_clin_sig_allowed("Pathogenic/Likely_pathogenic", allow_path=False, allow_likely_path=True)
        is False
    )
    assert (
        is_clin_sig_allowed("Pathogenic/Likely pathogenic", allow_path=False, allow_likely_path=True)
        is False
    )
    assert (
        is_clin_sig_allowed("Likely_pathogenic", allow_path=False, allow_likely_path=True)
        is True
    )
    assert (
        is_clin_sig_allowed("Likely_pathogenic", allow_path=True, allow_likely_path=False)
        is False
    )

    # Analog für Benign/Likely_benign vs. Likely_benign
    assert (
        is_clin_sig_allowed("Benign/Likely_benign", allow_benign=False, allow_likely_benign=True)
        is False
    )
    assert (
        is_clin_sig_allowed("Benign/Likely benign", allow_benign=False, allow_likely_benign=True)
        is False
    )
    assert (
        is_clin_sig_allowed("Likely_benign", allow_benign=False, allow_likely_benign=True)
        is True
    )
    assert (
        is_clin_sig_allowed("Likely_benign", allow_benign=True, allow_likely_benign=False)
        is False
    )


def test_b2_app_apply_post_filter_clin_sig_integration():
    """Prüft `App.apply_post_filter` end-to-end mit einem leichtgewichtigen Tree-Stub ohne Tk-Fenster."""
    import Variant_Fusion_pro_V17 as vf

    class _Var:
        def __init__(self, val):
            self._val = val

        def get(self):
            return self._val

    class _DummyTree:
        def __init__(self, rows_by_iid, columns):
            self._columns = columns
            self._values = {
                iid: tuple(row.get(c, "") for c in columns)
                for iid, row in rows_by_iid.items()
            }
            self.attached = list(rows_by_iid.keys())

        def get_children(self, _parent=""):
            return list(self.attached)

        def item(self, iid, option):
            assert option == "values"
            return self._values[iid]

        def detach(self, iid):
            if iid in self.attached:
                self.attached.remove(iid)

        def reattach(self, iid, _parent, _index):
            if iid not in self.attached:
                self.attached.append(iid)

    cols = ("chr", "pos", "gene", "clin_sig", "impact", "coding", "consequence", "cadd")
    rows = {
        "r_conflict": {"clin_sig": "Conflicting_classifications_of_pathogenicity", "gene": "BRCA1"},
        "r_conflict_old": {"clin_sig": "Conflicting_interpretations_of_pathogenicity", "gene": "BRCA2"},
        "r_path_combo": {"clin_sig": "Pathogenic/Likely_pathogenic", "gene": "TP53"},
        "r_lpath": {"clin_sig": "Likely_pathogenic", "gene": "MLH1"},
        "r_benign_combo": {"clin_sig": "Benign/Likely_benign", "gene": "APC"},
        "r_lbenign": {"clin_sig": "Likely_benign", "gene": "PTEN"},
        "r_missing": {"clin_sig": ".", "gene": "EGFR"},
    }

    done_evt = threading.Event()
    dummy_app = types.SimpleNamespace(
        tree=_DummyTree(rows, cols),
        columns=cols,
        _all_iids=set(rows.keys()),
        postfilter_cadd_min=_Var(""),
        postfilter_benign=_Var(False),
        postfilter_likely_benign=_Var(True),
        postfilter_vus=_Var(True),
        postfilter_likely_path=_Var(True),
        postfilter_path=_Var(False),
        postfilter_impact_high=_Var(True),
        postfilter_impact_moderate=_Var(True),
        postfilter_impact_low=_Var(True),
        postfilter_protein_coding=_Var(False),
        postfilter_consequences={},
        gen_whitelist=_Var(""),
        gen_blacklist=_Var(""),
        logger=MagicMock(),
        after=lambda _ms, fn: fn(),
        update_count_label=done_evt.set,
    )

    vf.App.apply_post_filter(dummy_app)
    assert done_evt.wait(timeout=1.5)

    # Pathogenic/Likely_pathogenic und Benign/Likely_benign sind ausgeblendet;
    # Conflicting_*, Likely_pathogenic, Likely_benign und '.' bleiben sichtbar!
    assert set(dummy_app.tree.attached) == {
        "r_conflict",
        "r_conflict_old",
        "r_lpath",
        "r_lbenign",
        "r_missing",
    }


# =============================================================================
# B3: Deterministischer Laufzeit-Concurrency-Test (< 2 s, Event/Barrier)
# =============================================================================


class _OrderTrackingEvent:
    """Wrapper um `threading.Event`, der deterministisch signalisiert, sobald ein Konsument wartet."""

    def __init__(self) -> None:
        self._inner = threading.Event()
        self.wait_entered = threading.Event()

    def is_set(self) -> bool:
        return self._inner.is_set()

    def set(self) -> None:
        self._inner.set()

    def clear(self) -> None:
        self._inner.clear()

    def wait(self, timeout: float | None = None) -> bool:
        self.wait_entered.set()
        return self._inner.wait(timeout=timeout)


def _install_fast_time(monkeypatch, vf_module) -> None:
    """Ersetzt Polling-`time.sleep` in Streaming-Schleifen durch kooperatives Kurz-Yield."""
    fast_time = types.SimpleNamespace(
        sleep=lambda _sec: time.sleep(0.001),
        time=time.time,
        monotonic=time.monotonic,
        perf_counter=time.perf_counter,
    )
    monkeypatch.setattr(vf_module, "time", fast_time)


def test_b3_streaming_handoff_missing_done_to_alphagenome_deterministic(tmp_path, monkeypatch):
    """Prüft deterministisch (< 2 s) den Phasen-Übergang `missing_done -> _phase_alphagenome_streaming`."""
    import Variant_Fusion_pro_V17 as vf

    _install_fast_time(monkeypatch, vf)
    monkeypatch.setattr(vf, "is_api_enabled", lambda phase, api: (phase, api) == ("phase6_ag", "alphagenome"))

    t0 = time.perf_counter()
    db_inst = VariantDB(str(tmp_path / "streaming_handoff.sqlite"))
    keys = [("chr1", 1000 + i, "A", "G", "GRCh38") for i in range(10)]
    db_inst.upsert_many(
        [
            (
                k,
                {
                    "rsid": f"rs{100 + idx}",
                    "clinical_significance": "Pathogenic",
                    "phenotypes": "Example syndrome",
                    "conservation": "4.2",
                    "full_fetch_success": "111",
                },
            )
            for idx, k in enumerate(keys)
        ]
    )

    entered_missing_scan = threading.Event()
    release_missing_scan = threading.Event()
    real_get_bulk = db_inst.get_variants_bulk

    def gated_get_variants_bulk(req_keys):
        if threading.current_thread().name == "phase-missing-fill":
            entered_missing_scan.set()
            assert release_missing_scan.wait(timeout=1.5), "Timeout waiting for release_missing_scan"
        return real_get_bulk(req_keys)

    monkeypatch.setattr(db_inst, "get_variants_bulk", gated_get_variants_bulk)

    scored_barrier = threading.Barrier(2, timeout=1.5)

    class _DeterministicAGScorer:
        available = True

        def score_batch(self, batch_keys, logger=None):
            scored_barrier.wait()
            return {tup: 0.875 for tup in batch_keys}

    distiller = vf.Distiller.__new__(vf.Distiller)
    distiller._keys_lock = threading.RLock()
    distiller.logger = MagicMock()
    distiller.db = db_inst
    distiller.stopflag = vf.StopFlag()
    distiller.progress = vf.PipelineProgress()
    distiller.progress.total_variants = len(keys)
    distiller.display_keys = set(keys)
    distiller.ag_scorer = _DeterministicAGScorer()

    missing_done_evt = _OrderTrackingEvent()
    pipeline_state = {
        "af_done": threading.Event(),
        "full_done": threading.Event(),
        "gene_done": threading.Event(),
        "rsid_done": threading.Event(),
        "missing_done": missing_done_evt,
        "alphagenome_done": threading.Event(),
    }
    for done_key in ("af_done", "full_done", "gene_done", "rsid_done"):
        pipeline_state[done_key].set()

    errors: list[BaseException] = []

    def run_missing():
        try:
            distiller._phase_missing_fill_streaming("GRCh38", pipeline_state)
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    def run_alphagenome():
        try:
            distiller._phase_alphagenome_streaming(pipeline_state)
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    t_missing = threading.Thread(target=run_missing, name="phase-missing-fill", daemon=True)
    t_ag = threading.Thread(target=run_alphagenome, name="phase-alphagenome", daemon=True)
    t_missing.start()
    t_ag.start()

    # 1. Missing-Fill steht deterministisch in seiner Scan-Phase; AlphaGenome scort parallel Batch 1
    assert entered_missing_scan.wait(timeout=1.5)
    scored_barrier.wait()

    # 2. AlphaGenome erreicht deterministisch `missing_done.wait(...)`, BEVOR `missing_done` gesetzt wird
    assert missing_done_evt.wait_entered.wait(timeout=1.5)
    assert not pipeline_state["missing_done"].is_set()
    assert not pipeline_state["alphagenome_done"].is_set()

    # 3. Freigabe von Missing-Fill -> setzt `missing_done` -> entsperrt AlphaGenome-Abschluss
    release_missing_scan.set()
    t_missing.join(timeout=1.5)
    t_ag.join(timeout=1.5)

    elapsed = time.perf_counter() - t0
    assert not errors, f"Unexpected thread errors: {errors!r}"
    assert not t_missing.is_alive()
    assert not t_ag.is_alive()
    assert pipeline_state["missing_done"].is_set()
    assert pipeline_state["alphagenome_done"].is_set()
    assert "ag_score" in distiller.progress._phases_completed

    stored = real_get_bulk(keys)
    assert len(stored) == len(keys)
    assert all(stored[k]["ag_score"] == pytest.approx(0.875) for k in keys)
    assert elapsed < 2.0, f"Concurrency test exceeded 2s budget: {elapsed:.3f}s"


def test_b3_full_annotation_flush_pending_writes_retry_and_cache_invalidation(tmp_path, monkeypatch):
    """Prüft deterministisch (< 2 s) `flush_pending_writes` inkl. Buffer-Erhalt bei Fehler + Final-Retry."""
    import Variant_Fusion_pro_V17 as vf

    _install_fast_time(monkeypatch, vf)
    monkeypatch.setattr(vf, "is_api_enabled", lambda phase, api: True)

    t0 = time.perf_counter()
    db_inst = VariantDB(str(tmp_path / "flush_retry.sqlite"))
    keys = [("chr7", 5000 + i, "C", "T", "GRCh38") for i in range(10)]
    db_inst.upsert_many([(k, {"rsid": f"rs{900 + idx}"}) for idx, k in enumerate(keys)])

    real_upsert_many = db_inst.upsert_many
    first_flush_failed = threading.Event()
    upsert_calls: list[int] = []

    def flaky_upsert_many(items):
        upsert_calls.append(len(items))
        if len(upsert_calls) == 1:
            first_flush_failed.set()
            raise sqlite3.OperationalError("simulated transient SQLite lock")
        return real_upsert_many(items)

    monkeypatch.setattr(db_inst, "upsert_many", flaky_upsert_many)
    monkeypatch.setattr(
        vf,
        "extract_fields_from_mv",
        lambda ann, debug_log=False: {
            "gene_symbol": ann["gene"],
            "clinical_significance": ann["clin_sig"],
            "cadd_phred": 28.5,
            "impact": "HIGH",
            "consequence": "missense_variant",
            "phenotypes": "Test phenotype",
            "conservation": "5.1",
        },
    )

    invalidated_batches: list[list[tuple]] = []
    fetch_entered = threading.Event()
    allow_fetch_return = threading.Event()

    distiller = vf.Distiller.__new__(vf.Distiller)
    distiller._keys_lock = threading.RLock()
    distiller.logger = MagicMock()
    distiller.db = db_inst
    distiller.stopflag = vf.StopFlag()
    distiller.progress = vf.PipelineProgress()
    distiller.progress.total_variants = len(keys)
    distiller.status_mgr = vf.FetchStatusManager()
    distiller.display_keys = set(keys)
    distiller.current_vcf_keys = set(keys)
    distiller.emit_queue = MagicMock()
    distiller.invalidate_cache_bulk = lambda k_list: invalidated_batches.append(list(k_list))

    def fake_safe_mv_fetch_async(batch_keys, build, fetch_full, batch_size):
        fetch_entered.set()
        assert allow_fetch_return.wait(timeout=1.5)
        return {
            k: {"gene": "BRAF", "clin_sig": "Conflicting_classifications_of_pathogenicity"}
            for k in batch_keys
        }

    distiller._safe_mv_fetch_async = fake_safe_mv_fetch_async

    pipeline_state = {
        "af_done": threading.Event(),
        "full_done": threading.Event(),
    }
    pipeline_state["af_done"].set()

    worker = threading.Thread(
        target=distiller._phase_full_annotation_streaming,
        args=("GRCh38", 30, pipeline_state),
        name="phase-full-anno",
        daemon=True,
    )
    worker.start()

    assert fetch_entered.wait(timeout=1.5)
    assert not pipeline_state["full_done"].is_set()
    allow_fetch_return.set()

    worker.join(timeout=1.5)
    elapsed = time.perf_counter() - t0

    assert not worker.is_alive()
    assert first_flush_failed.is_set()
    # Versuch 1 (Idle-Exit-Flush) schlug fehl -> Buffer blieb erhalten -> Versuch 2 (Final-Flush) schrieb alle 10 Keys!
    assert upsert_calls == [10, 10]
    assert len(invalidated_batches) == 1
    assert set(invalidated_batches[0]) == set(keys)
    assert pipeline_state["full_done"].is_set()

    rows = db_inst.get_variants_bulk(keys)
    assert all(rows[k]["gene_symbol"] == "BRAF" for k in keys)
    assert all(
        rows[k]["clinical_significance"] == "Conflicting_classifications_of_pathogenicity"
        for k in keys
    )
    assert all(rows[k]["full_fetch_success"] == "111" for k in keys)
    assert elapsed < 2.0, f"Flush retry concurrency test exceeded 2s budget: {elapsed:.3f}s"
