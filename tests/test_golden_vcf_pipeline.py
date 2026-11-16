# -*- coding: utf-8 -*-
"""Deterministic Golden-VCF and pipeline verification suite for VFDistiller.

Covers real behavioral invariants across synthetic fixtures generated in tmp_path
(zero external network calls, zero tracked bio data files):
  - VCF/gVCF/gzip parsing, multiallelic splitting, multi-sample preservation
  - Genotype normalization & FORMAT/INFO DP priority
  - QualityManager presets, HomRef/PASS/DP/QUAL contracts
  - MainFilterGate, AfNoneTreatmentManager, FetchStatusManager & CodingFilter
  - VariantDB SQLite persistence & partial annotation flush preservation
  - 23andMe-to-VCF converter, FASTQmap alignment/genotyping, gVCF safety
  - End-to-end cohort routing matrix
"""
from __future__ import annotations

import datetime
import gzip
from pathlib import Path
from unittest.mock import MagicMock

import Variant_Fusion_pro_V17 as vf


def _make_logger() -> MagicMock:
    lg = MagicMock()
    lg.log = MagicMock()
    return lg


def _make_distiller(
    *,
    af_threshold: float = 0.01,
    include_none: bool = False,
    af_none_policy: str = "clinical",
    only_protein_coding: bool = False,
    gene_annotator=None,
    db=None,
):
    logger = _make_logger()
    fm = vf.Flag_and_Options_Manager(logger=logger)
    fm.set_af_threshold(af_threshold)
    fm.set_include_none(include_none)
    fm.set_af_none_policy(af_none_policy)
    fm.set_only_protein_coding(only_protein_coding)

    db_obj = db if db is not None else MagicMock()
    distiller = vf.Distiller.__new__(vf.Distiller)
    distiller.logger = logger
    distiller.db = db_obj
    distiller.flag_manager = fm
    distiller.main_filter_gate = vf.MainFilterGate(
        flag_manager=fm,
        db=db_obj,
        gene_annotator=gene_annotator,
        logger=logger,
    )
    distiller._get_variants_bulk_cached = lambda keys: (
        db_obj.get_variants_bulk(keys) if db is not None else {}
    )
    return distiller


def _write_golden_mini_vcf(path: Path, *, compressed: bool = False) -> None:
    lines = [
        "##fileformat=VCFv4.2\n",
        "##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Total Depth\">\n",
        "##INFO=<ID=MIN_DP,Number=1,Type=Integer,Description=\"Minimum Depth\">\n",
        "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n",
        "##FORMAT=<ID=DP,Number=1,Type=Integer,Description=\"Read Depth\">\n",
        "##FORMAT=<ID=GQ,Number=1,Type=Integer,Description=\"Genotype Quality\">\n",
        "##FORMAT=<ID=AD,Number=R,Type=Integer,Description=\"Allelic Depths\">\n",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_A\tSAMPLE_B\n",
        "chr1\t100\trs1\tA\tG\t50\tPASS\tDP=40\tGT:DP:GQ:AD\t0/1:35:99:18,17\t0/0:42:90:42,0\n",
        "chrX\t250\t.\tAT\tA,ATG\t80\tPASS\tMIN_DP=4;DP=60\tGT:DP\t1/2:48\t0/1:52\n",
        "chrM\t400\t.\tC\tCT\t25\tLowQual\tDP=15\tGT:DP\t1\t0\n",
    ]
    payload = "".join(lines)
    if compressed:
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(payload)
    else:
        path.write_text(payload, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1-5: VCF I/O, Multiallelic, Multi-Sample, Format & Genotype
# ---------------------------------------------------------------------------


def test_vcf_io_snv_indel_and_multiallelic_splitting(tmp_path):
    vcf_path = tmp_path / "golden.vcf"
    _write_golden_mini_vcf(vcf_path, compressed=False)

    recs = list(vf.parse_vcf_records_smart(str(vcf_path)))
    # 3 lines -> 1 + 2 (multiallelic) + 1 = 4 records
    assert len(recs) == 4
    assert recs[0]["header"] is not None
    assert all(r["header"] is None for r in recs[1:])

    assert (recs[0]["chrom"], recs[0]["pos"], recs[0]["ref"], recs[0]["alt"]) == ("1", 100, "A", "G")
    assert [(r["chrom"], r["alt"]) for r in recs[1:3]] == [("X", "A"), ("X", "ATG")]
    assert (recs[3]["chrom"], recs[3]["pos"], recs[3]["ref"], recs[3]["alt"]) == ("MT", 400, "C", "CT")


def test_vcf_io_gzip_roundtrip(tmp_path):
    plain = tmp_path / "plain.vcf"
    gz = tmp_path / "comp.vcf.gz"
    _write_golden_mini_vcf(plain, compressed=False)
    _write_golden_mini_vcf(gz, compressed=True)

    plain_keys = [(r["chrom"], r["pos"], r["ref"], r["alt"]) for r in vf.parse_vcf_records_smart(str(plain))]
    gz_keys = [(r["chrom"], r["pos"], r["ref"], r["alt"]) for r in vf.parse_vcf_records_smart(str(gz))]
    assert gz_keys == plain_keys
    assert list(vf.parse_vcf_keys(str(gz))) == [("1", 100, "A", "G"), ("X", 250, "AT", "A"), ("X", 250, "AT", "ATG"), ("MT", 400, "C", "CT")]


def test_vcf_io_multisample_preserves_sample_list_without_tab_corruption(tmp_path):
    vcf_path = tmp_path / "multisample.vcf"
    _write_golden_mini_vcf(vcf_path, compressed=False)

    recs = list(vf.parse_vcf_records(str(vcf_path)))
    assert recs[0]["samples"] == ["0/1:35:99:18,17", "0/0:42:90:42,0"]
    assert all("\t" not in s for s in recs[0]["samples"])


def test_vcf_io_limit_multiallelic_alt_and_format_fields():
    line = "chrX\t250\t.\tAT\tA,ATG\t80\tPASS\tDP=60\tGT:DP\t1/2:48\t0/1:52\n"
    limited = vf._limit_vcf_line_to_alt(line, "ATG")
    assert limited.rstrip("\n").split("\t")[4] == "ATG"

    rec_orig = {"fmt": "GT:DP:GQ:AD", "sample": "0/1:35:99:18,17\t0/0:42:90:42,0", "info": {"DP": "10"}}
    assert vf._extract_format_field(rec_orig, "GQ") == "99"
    assert vf._get_dp_value(rec_orig) == "35"
    fmt_str, smp_str = vf._build_format_fields(rec_orig, "0/1")
    assert fmt_str == "GT:DP:GQ:AD"
    assert smp_str == "0/1:35:99:18,17"

    rec_parser = {"fmt": "GT:DP:AD", "samples": ["0/1:28:14,14"], "info": {}}
    assert vf._get_dp_value(rec_parser) == "28"


def test_genotype_label_and_normalize_display():
    assert vf.get_genotype_label("GT:DP", ["0/0:30"]) == "ref"
    assert vf.get_genotype_label("GT:DP", ["0|1:30"]) == "het"
    assert vf.get_genotype_label("GT:DP", ["1/1:30"]) == "hom"
    assert vf.get_genotype_label("GT:DP", ["1/2:30"]) == "het"
    assert vf.get_genotype_label("GT:DP", ["./.:30"]) == "."
    assert vf.get_genotype_label("GT", ["1"]) == "hemi"
    assert vf.get_genotype_label("GT", ["0"]) == "ref"
    assert vf.normalize_genotype_display("0|1") == "het"
    assert vf.normalize_genotype_display("1/1") == "hom"


# ---------------------------------------------------------------------------
# 6-11: QualityManager invariants
# ---------------------------------------------------------------------------


def test_quality_manager_rejects_homref_and_keeps_rma_mode():
    rec = {"filter": "PASS", "qual": "50", "info": {"DP": "30"}, "fmt": "GT:DP", "samples": ["0/0:30"]}
    assert vf.QualityManager(preset="clinical").passes(rec) is False
    assert vf.QualityManager(preset="rma_sensitive").passes(rec) is True


def test_quality_manager_filter_pass_only_toggle():
    rec = {"filter": "LowQual", "qual": "80", "info": {"DP": "35"}, "fmt": "GT:DP", "samples": ["0/1:35"]}
    assert vf.QualityManager(preset="clinical").passes(rec) is False
    qm_relaxed = vf.QualityManager(preset="custom")
    qm_relaxed.set_custom_settings(filter_pass_only=False)
    assert qm_relaxed.passes(rec) is True


def test_quality_manager_format_dp_overrides_info_dp():
    low_fmt_dp = {"filter": "PASS", "qual": "80", "info": {"DP": "500"}, "fmt": "GT:DP", "samples": ["0/1:3"]}
    high_fmt_dp = {"filter": "PASS", "qual": "80", "info": {"DP": "5"}, "fmt": "GT:DP", "samples": ["0/1:40"]}
    qm = vf.QualityManager(preset="clinical")  # min_dp=20
    assert qm.passes(low_fmt_dp) is False
    assert qm.passes(high_fmt_dp) is True


def test_quality_manager_info_dict_min_dp_vs_dp_from_parsed_vcf(tmp_path):
    vcf_path = tmp_path / "min_dp.vcf"
    _write_golden_mini_vcf(vcf_path, compressed=False)
    recs = list(vf.parse_vcf_records(str(vcf_path)))
    # Record 1 is chrX:250 MIN_DP=4;DP=60 with FORMAT DP=48 -> must extract >= 20 and pass
    assert recs[1]["info"]["MIN_DP"] == "4"
    assert recs[1]["info"]["DP"] == "60"
    assert vf.QualityManager(preset="clinical").passes(recs[1]) is True

    # Dict-only fallback (no FORMAT DP): still resolves INFO["DP"]=60 instead of MIN_DP=4
    rec_info_only = {"filter": "PASS", "qual": "80", "info": recs[1]["info"], "fmt": "GT", "samples": ["0/1"]}
    assert vf.QualityManager(preset="clinical")._extract_dp(rec_info_only) == 60


def test_quality_manager_preserves_block6b_combined_pass_or_qual_contract():
    # Intentionally deferred in Block 6b (1d11312): FILTER=PASS implies pass before QUAL gate
    low_qual_pass = {"filter": "PASS", "qual": "5.0", "info": {"DP": "40"}, "fmt": "GT:DP", "samples": ["0/1:40"]}
    assert vf.QualityManager(preset="strict").passes(low_qual_pass) is True


def test_quality_manager_multisample_header_names(tmp_path):
    vcf_path = tmp_path / "samples.vcf"
    vcf_path.write_text(
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tNA12878\tNA12891\tNA12892\n"
        "1\t10\t.\tA\tG\t50\tPASS\tDP=20\tGT\t0/1\t0/0\t1/1\n",
        encoding="utf-8",
    )
    assert vf.QualityManager().get_vcf_sample_names(str(vcf_path)) == ["NA12878", "NA12891", "NA12892"]


# ---------------------------------------------------------------------------
# 12-18: AF Filter, AfNoneTreatmentManager, FetchStatusManager & CodingFilter
# ---------------------------------------------------------------------------


def test_af_filter_rare_common_and_exact_boundary():
    d = _make_distiller(af_threshold=0.01)
    assert d._apply_af_filter_final(("1", 10, "A", "G", "GRCh38"), {"af_filter_mean": 0.0001}) == "emit"
    assert d._apply_af_filter_final(("1", 11, "A", "G", "GRCh38"), {"af_filter_mean": 0.25}) == "reject"
    # Strictly '>' threshold rejects; exact equality is emitted
    assert d._apply_af_filter_final(("1", 12, "A", "G", "GRCh38"), {"af_filter_mean": 0.01}) == "emit"


def test_af_filter_singleton_zero_not_treated_as_none():
    d = _make_distiller(af_threshold=0.01, include_none=False, af_none_policy="strict")
    val = {"af_filter_mean": 0.0, "meanAF_fetch_success": "111", "meanAF_last_fetch": vf.now_iso()}
    assert d._apply_af_filter_final(("1", 20, "C", "T", "GRCh38"), val) == "emit"


def test_af_none_true_none_classification_and_presets():
    key = ("1", 30, "G", "A", "GRCh38")
    row = {"af_filter_mean": None, "meanAF_fetch_success": "111", "meanAF_last_fetch": vf.now_iso()}

    mgr = vf.AfNoneTreatmentManager(preset="clinical")
    assert mgr.classify_none_type(row) == "true_none"

    for preset, expected in [("clinical", "emit"), ("research", "emit"), ("permissive", "emit"), ("strict", "reject")]:
        d = _make_distiller(include_none=False, af_none_policy=preset)
        assert d._apply_af_filter_final(key, row) == expected


def test_af_none_never_fetched_classification_and_include_none_override():
    key = ("1", 40, "T", "C", "GRCh38")
    row = {"af_filter_mean": None, "meanAF_fetch_success": None, "meanAF_last_fetch": None}

    assert vf.AfNoneTreatmentManager(preset="clinical").classify_none_type(row) == "never_fetched"
    assert _make_distiller(include_none=False, af_none_policy="clinical")._apply_af_filter_final(key, row) == "reject"
    assert _make_distiller(include_none=False, af_none_policy="research")._apply_af_filter_final(key, row) == "emit"
    assert _make_distiller(include_none=True, af_none_policy="clinical")._apply_af_filter_final(key, row) == "emit"


def test_af_none_fetch_failed_classification_and_retry_codes():
    s1 = vf.FetchStatusManager.update_status(None, success=False)
    s2 = vf.FetchStatusManager.update_status(s1, success=False)
    assert (s1, s2) == ("010", "011")

    key = ("1", 50, "A", "C", "GRCh38")
    row = {"af_filter_mean": None, "meanAF_fetch_success": s1, "meanAF_last_fetch": vf.now_iso()}
    assert vf.AfNoneTreatmentManager(preset="clinical").classify_none_type(row) == "fetch_failed"

    assert _make_distiller(include_none=False, af_none_policy="clinical")._apply_af_filter_final(key, row) == "reject"
    assert _make_distiller(include_none=False, af_none_policy="research")._apply_af_filter_final(key, row) == "reject"
    assert _make_distiller(include_none=False, af_none_policy="permissive")._apply_af_filter_final(key, row) == "emit"


def test_main_filter_gate_coding_filter_with_mock_annotator(tmp_path):
    db = vf.VariantDB(str(tmp_path / "coding.sqlite"))
    coding_key = ("1", 100, "A", "G", "GRCh38")
    intergenic_key = ("1", 200, "C", "T", "GRCh38")

    annotator = MagicMock()
    annotator.available = True
    annotator.annotate_batch.return_value = {
        coding_key: {"is_coding": True, "gene_symbol": "BRCA1"},
        intergenic_key: {"is_coding": False, "gene_symbol": None},
    }

    d_coding = _make_distiller(only_protein_coding=True, gene_annotator=annotator, db=db)
    ok_c, reason_c, data_c = d_coding.main_filter_gate.check_variant(coding_key, af_value=0.001, fetch_status="111")
    ok_i, reason_i, _ = d_coding.main_filter_gate.check_variant(intergenic_key, af_value=0.001, fetch_status="111")
    assert ok_c is True and reason_c == "passed" and data_c["gene_symbol"] == "BRCA1"
    assert ok_i is False and reason_i == "not_coding"

    d_all = _make_distiller(only_protein_coding=False, gene_annotator=annotator, db=db)
    ok_all, _, _ = d_all.main_filter_gate.check_variant(intergenic_key, af_value=0.001, fetch_status="111")
    assert ok_all is True


def test_distiller_db_fallback_and_stale_reclassification(tmp_path):
    db = vf.VariantDB(str(tmp_path / "fallback.sqlite"))
    key_fresh = ("1", 500, "G", "T", "GRCh38")
    key_stale = ("1", 501, "G", "T", "GRCh38")
    stale_ts = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=400)).isoformat()

    db.upsert_many([
        (key_fresh, {"af_filter_mean": None, "meanAF_fetch_success": "111", "meanAF_last_fetch": vf.now_iso()}),
        (key_stale, {"af_filter_mean": None, "meanAF_fetch_success": "111", "meanAF_last_fetch": stale_ts}),
    ])

    d = _make_distiller(include_none=False, af_none_policy="clinical", db=db)
    assert d._apply_af_filter_final(key_fresh, None) == "emit"
    assert d._apply_af_filter_final(key_stale, None) == "reject"


# ---------------------------------------------------------------------------
# 19-20: VariantDB persistence & partial updates
# ---------------------------------------------------------------------------


def test_variant_db_partial_flush_preserves_conservation_and_cadd(tmp_path):
    db = vf.VariantDB(str(tmp_path / "variants.sqlite"))
    key = ("17", 43094464, "G", "A", "GRCh38")
    db.upsert_many([
        (
            key,
            {
                "af_filter_mean": 0.0002,
                "cadd_phred": 28.4,
                "conservation": 4.85,
                "meanAF_fetch_success": "111",
                "meanAF_last_fetch": vf.now_iso(),
            },
        )
    ])

    db.update_variant_fields_bulk([(key, {"gene_symbol": "BRCA1", "is_coding": True})])
    row = db.get_variant(key)
    assert row is not None
    assert row["gene_symbol"] == "BRCA1"
    assert row["is_coding"] == 1
    assert abs(float(row["conservation"]) - 4.85) < 1e-6
    assert abs(float(row["cadd_phred"]) - 28.4) < 1e-6


def test_variant_db_upsert_variants_bulk_preserves_non_af_annotations_on_conflict(tmp_path):
    db = vf.VariantDB(str(tmp_path / "bulk.sqlite"))
    key = ("7", 140753336, "A", "T", "GRCh38")
    db.upsert_many([(key, {"gene_symbol": "BRAF", "conservation": 5.9, "af_filter_mean": 0.005})])

    db.upsert_variants_bulk({
        key: {
            "af_filter_mean": 0.0001,
            "meanAF_fetch_success": "111",
            "meanAF_last_fetch": vf.now_iso(),
        }
    })
    row = db.get_variant(key)
    assert row["gene_symbol"] == "BRAF"
    assert abs(float(row["conservation"]) - 5.9) < 1e-6
    assert abs(float(row["af_filter_mean"]) - 0.0001) < 1e-6


# ---------------------------------------------------------------------------
# 21-24: Converters, gVCF safety & Cohort Matrix End-to-End
# ---------------------------------------------------------------------------


def test_23andme_converter_plain_and_gzip_end_to_end(tmp_path):
    gz_in = tmp_path / "raw_23.txt.gz"
    with gzip.open(gz_in, "wt", encoding="utf-8") as fh:
        fh.write("# rsid\tchromosome\tposition\tgenotype\nrs101\t1\t500\tca\nrs102\t2\t600\tgg\n")

    conv = vf.convert_23andme_to_vcf(str(gz_in), cache_file=str(tmp_path / "cache.json"))
    conv.cache_upsert(conv.cache, "rs101", "GRCh38", "1", 500, "C")
    conv.cache_upsert(conv.cache, "rs102", "GRCh38", "2", 600, "T")

    rows = conv.parse_23andme()
    out_vcf = tmp_path / "out_23.vcf"
    conv.create_vcf(rows, "GRCh38", str(out_vcf), conv.cache, fasta_path=None, sex="female")

    data_lines = [ln for ln in out_vcf.read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
    assert len(data_lines) == 2
    assert "rs101\tC\tA\t.\tPASS\t.\tGT\t0/1" in data_lines[0]
    assert "rs102\tT\tG\t.\tPASS\t.\tGT\t1/1" in data_lines[1]


def test_fastqmap_gzip_pipeline_heterozygous_call_and_natural_sort(tmp_path):
    ref_fa = tmp_path / "mini.fa.gz"
    with gzip.open(ref_fa, "wt", encoding="utf-8") as fh:
        fh.write(">chr10\ngctagtcagctgatcgatgctagc\n>chr2\naccgttagcgataccggttacgta\n")

    fq = tmp_path / "reads.fastq.gz"
    reads = []
    for idx in range(9):
        reads.append(f"@c10_ref_{idx}\nGCTAGTCAGCTGATCGATGCTAGC\n+\nIIIIIIIIIIIIIIIIIIIIIIII\n")
    for idx in range(3):
        reads.append(f"@c10_alt_{idx}\nGCTAGTCAGCAGATCGATGCTAGC\n+\nIIIIIIIIIIIIIIIIIIIIIIII\n")
    for idx in range(4):
        reads.append(f"@c2_ref_{idx}\nACCGTTAGCGATACCGGTTACGTA\n+\nIIIIIIIIIIIIIIIIIIIIIIII\n")
    for idx in range(6):
        reads.append(f"@c2_alt_{idx}\nACCGTTAGCGGTACCGGTTACGTA\n+\nIIIIIIIIIIIIIIIIIIIIIIII\n")
    with gzip.open(fq, "wt", encoding="ascii") as fh:
        fh.write("".join(reads))

    fm = vf.FASTQmap(build="GRCh38", logger=_make_logger())
    fm.ensure_reference = lambda build="GRCh38": str(ref_fa)
    out_dir = tmp_path / "fq_out"
    fm.process_fastq(str(fq), build="GRCh38", k=8, min_dp=5, min_af=0.08, out_dir=str(out_dir))

    vcf_lines = [ln for ln in (out_dir / "variants.vcf").read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    assert len(vcf_lines) == 2
    assert vcf_lines[0].startswith("chr2\t") and vcf_lines[1].startswith("chr10\t")
    cols_c2 = vcf_lines[0].split("\t")
    assert cols_c2[1] == "11" and cols_c2[3] == "A" and cols_c2[4] == "G" and cols_c2[9] == "0/1"
    cols_c10 = vcf_lines[1].split("\t")
    assert cols_c10[1] == "11" and cols_c10[3] == "T" and cols_c10[4] == "A" and cols_c10[9] == "0/1"


def test_distiller_filter_gvcf_strips_ref_blocks_and_protects_source(tmp_path):
    distiller = _make_distiller()

    gvcf = tmp_path / "sample.g.vcf"
    gvcf.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "chr1\t10\t.\tA\t.\t.\tPASS\tEND=50\n"
        "chr1\t60\t.\tG\tT\t55\tPASS\tDP=25\n",
        encoding="utf-8",
    )
    filtered = Path(distiller._filter_gvcf(str(gvcf)))
    assert filtered != gvcf and filtered.exists()
    data = [ln for ln in filtered.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    assert len(data) == 1 and "\tG\tT\t" in data[0]

    plain_vcf = tmp_path / "plain.vcf"
    raw = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchr1\t90\t.\tC\tA\t40\tPASS\tDP=30\n"
    plain_vcf.write_text(raw, encoding="utf-8")
    out2 = Path(distiller._filter_gvcf(str(plain_vcf)))
    assert out2 != plain_vcf and plain_vcf.read_text(encoding="utf-8") == raw


def test_golden_vcf_mini_cohort_matrix_end_to_end(tmp_path):
    vcf = tmp_path / "cohort.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tPROBAND\n"
        "chr1\t100\t.\tA\tG\t90\tPASS\tDP=40\tGT:DP\t0/0:40\n"
        "chr1\t200\t.\tA\tG\t90\tLowQual\tDP=40\tGT:DP\t0/1:40\n"
        "chr1\t300\t.\tA\tG\t90\tPASS\tDP=40\tGT:DP\t0/1:5\n"
        "chr1\t400\t.\tA\tG\t90\tPASS\tDP=40\tGT:DP\t0/1:40\n"
        "chr1\t500\t.\tA\tG\t90\tPASS\tDP=40\tGT:DP\t0/1:40\n"
        "chr1\t600\t.\tA\tG\t90\tPASS\tDP=40\tGT:DP\t0/1:40\n"
        "chr1\t700\t.\tA\tG\t90\tPASS\tDP=40\tGT:DP\t0/1:40\n"
        "chr1\t800\t.\tA\tG\t90\tPASS\tDP=40\tGT:DP\t0/1:40\n",
        encoding="utf-8",
    )

    qm = vf.QualityManager(preset="clinical")
    d = _make_distiller(af_threshold=0.01, include_none=False, af_none_policy="clinical")
    ts = vf.now_iso()
    af_payloads = {
        400: {"af_filter_mean": 0.25, "meanAF_fetch_success": "111", "meanAF_last_fetch": ts},
        500: {"af_filter_mean": 0.0005, "meanAF_fetch_success": "111", "meanAF_last_fetch": ts},
        600: {"af_filter_mean": 0.0, "meanAF_fetch_success": "111", "meanAF_last_fetch": ts},
        700: {"af_filter_mean": None, "meanAF_fetch_success": "111", "meanAF_last_fetch": ts},
        800: {"af_filter_mean": None, "meanAF_fetch_success": None, "meanAF_last_fetch": None},
    }

    emitted_positions = []
    for rec in vf.parse_vcf_records_smart(str(vcf)):
        if not qm.passes(rec):
            continue
        key = (rec["chrom"], rec["pos"], rec["ref"], rec["alt"], "GRCh38")
        if d._apply_af_filter_final(key, af_payloads[rec["pos"]]) == "emit":
            emitted_positions.append(rec["pos"])

    # 100=HomRef, 200=LowQual, 300=LowFORMAT_DP, 400=CommonAF, 800=NeverFetched
    assert emitted_positions == [500, 600, 700]
