# -*- coding: utf-8 -*-
"""Vertrags- und Integrationstests für das GUI-freie Paket `vfdistiller` und seine CLI."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import Variant_Fusion_pro_V17 as vf
import vfdistiller
from vfdistiller import VariantDB, cli

ROOT = Path(__file__).resolve().parent.parent


def _write_sample_vcf(path: Path) -> None:
    path.write_text(
        "##fileformat=VCFv4.2\n"
        "##contig=<ID=chr1,length=248956422>\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_A\tSAMPLE_B\n"
        "chr1\t100\trs1\tA\tG\t80\tPASS\tDP=50\tGT:DP\t0/0:40\t0/1:35\n"
        "chr1\t200\trs2\tC\tT\t90\tLowQual\tDP=50\tGT:DP\t0/1:45\t0/1:45\n"
        "chr1\t300\trs3\tG\tA\t95\tPASS\tDP=50\tGT:DP\t0/1:8\t0/1:30\n",
        encoding="utf-8",
    )


def test_vfdistiller_imports_headless_without_tkinter_or_ttkbootstrap():
    script = (
        "import json, sys\n"
        "for mod in ('tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', "
        "'ttkbootstrap', 'pystray'):\n"
        "    sys.modules[mod] = None\n"
        "import vfdistiller\n"
        "qm = vfdistiller.QualityManager(preset='clinical')\n"
        "print(json.dumps({'version': vfdistiller.__version__, 'preset': qm.current_preset}))\n"
    )
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    res = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout.strip().splitlines()[-1])
    assert data == {"version": "17.0.2", "preset": "clinical"}


def test_vfdistiller_source_contains_zero_gui_imports():
    pkg_dir = ROOT / "vfdistiller"
    forbidden = ("tkinter", "ttkbootstrap", "pystray")
    for py_file in sorted(pkg_dir.glob("*.py")):
        txt = py_file.read_text(encoding="utf-8")
        for mod in forbidden:
            assert f"import {mod}" not in txt and f"from {mod}" not in txt, (py_file.name, mod)


def test_reexport_identity_parity_with_monolith():
    symbols = [
        "fmt_eta",
        "safe_float",
        "now_iso",
        "parse_iso_utc",
        "determine_is_coding",
        "safe_nested_get",
        "StopFlag",
        "is_gzipped",
        "open_text_maybe_gzip",
        "is_vcf",
        "_normalize_chrom_vcf",
        "_limit_vcf_line_to_alt",
        "parse_vcf_records",
        "parse_vcf_records_mmap",
        "parse_vcf_records_smart",
        "parse_vcf_keys",
        "count_variants_exact",
        "get_genotype_label",
        "normalize_genotype_display",
        "_extract_format_field",
        "_get_dp_value",
        "_build_format_fields",
        "QualityManager",
        "FetchStatusManager",
        "AfNoneTreatmentManager",
        "Flag_and_Options_Manager",
        "MainFilterGate",
        "CodingFilter",
        "VariantDB",
        "get_robust_session",
        "load_fai_index",
        "fetch_base_from_fasta",
        "indel_ref_alt_from_spdi",
        "make_hgvs_indel",
        "_is_pure_snv_key",
        "_is_indel_key",
        "make_hgvs",
        "HGVS_REGEX",
        "is_valid_hgvs",
        "normalize_variant",
        "normalize_indel",
        "get_ref_base",
        "StreamingFastaToGVCF",
        "FASTQmap",
    ]
    for name in symbols:
        assert getattr(vfdistiller, name) is getattr(vf, name), name


def test_cli_version_via_module_subprocess():
    res = subprocess.run(
        [sys.executable, "-m", "vfdistiller", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    assert "17.0.2" in res.stdout


def test_cli_inspect_and_missing_input(tmp_path, capsys):
    vcf = tmp_path / "sample.vcf"
    _write_sample_vcf(vcf)

    rc = cli.main(["inspect", str(vcf), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["records"] == 3
    assert payload["pass_or_dot_records"] == 2
    assert payload["samples"] == ["SAMPLE_A", "SAMPLE_B"]
    assert payload["chromosomes"] == ["1"]

    rc_limit = cli.main(["inspect", str(vcf), "--limit", "1", "--json"])
    assert rc_limit == 0
    assert json.loads(capsys.readouterr().out)["records"] == 1

    rc_missing = cli.main(["inspect", str(tmp_path / "does_not_exist.vcf")])
    assert rc_missing == 2


def test_cli_filter_writes_filtered_vcf_and_supports_sample_index(tmp_path, capsys):
    vcf = tmp_path / "cohort.vcf"
    out_vcf = tmp_path / "filtered.vcf"
    _write_sample_vcf(vcf)

    # SAMPLE_A: rs1=0/0 (excluded), rs2=LowQual (excluded), rs3=DP=8 (<20, excluded) -> 0 pass
    rc_a = cli.main(["filter", str(vcf), "--preset", "clinical", "--sample-index", "0", "--json"])
    assert rc_a == 0
    summary_a = json.loads(capsys.readouterr().out)
    assert summary_a["total"] == 3
    assert summary_a["passed"] == 0

    # SAMPLE_B: rs1=0/1 DP=35 (PASS), rs2=LowQual (excluded), rs3=0/1 DP=30 (PASS) -> 2 pass
    rc_b = cli.main(
        [
            "filter",
            str(vcf),
            "--out-vcf",
            str(out_vcf),
            "--preset",
            "clinical",
            "--min-dp",
            "20",
            "--sample-index",
            "1",
            "--json",
        ]
    )
    assert rc_b == 0
    summary_b = json.loads(capsys.readouterr().out)
    assert summary_b["passed"] == 2
    assert summary_b["rejected"] == 1
    assert out_vcf.is_file()
    data_lines = [ln for ln in out_vcf.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
    assert len(data_lines) == 2
    assert "rs1" in data_lines[0] and "rs3" in data_lines[1]

    # RMA mode preserves 0/0 genotypes on SAMPLE_A
    rc_rma = cli.main(
        ["filter", str(vcf), "--preset", "rma_sensitive", "--keep-hom-ref", "--sample-index", "0", "--json"]
    )
    assert rc_rma == 0
    summary_rma = json.loads(capsys.readouterr().out)
    assert summary_rma["passed"] == 1  # rs1 passes (0/0, DP=40); rs2 LowQual; rs3 DP=8<10

    assert cli.main(["filter", str(tmp_path / "missing.vcf")]) == 2


def test_cli_db_stats_reads_variantdb_without_creating_missing_files(tmp_path, capsys):
    db_file = tmp_path / "variants.sqlite"
    db = VariantDB(str(db_file))
    db.upsert_many(
        [
            (
                ("1", 101, "A", "G", "GRCh38"),
                {
                    "af_filter_mean": 0.001,
                    "meanAF_fetch_success": "1",
                },
            ),
            (
                ("2", 202, "C", "T", "GRCh37"),
                {
                    "af_filter_mean": None,
                    "meanAF_fetch_success": "111",
                },
            ),
        ]
    )

    capsys.readouterr()
    rc = cli.main(["db-stats", str(db_file), "--json"])
    assert rc == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["total_variants"] == 2
    assert stats["af_populated"] == 1
    assert stats["af_missing"] == 1
    assert stats["by_build"] == {"GRCh37": 1, "GRCh38": 1}

    missing_db = tmp_path / "missing.sqlite"
    assert cli.main(["db-stats", str(missing_db)]) == 2
    assert not missing_db.exists()
