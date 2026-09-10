# -*- coding: utf-8 -*-
"""
Bug-Sweep Block 8 (2026-09-10) — Genotyp- & Qualitäts-Metriken
================================================================

Bereich: Genotyp- & Qualitäts-Metriken (VCF FORMAT DP/GQ Parsing & VCF Export)

Behobene Bugs:
1. _extract_format_field: Suchte nur nach rec["samples"] (Liste aus Parser),
   ignorierte jedoch rec["sample"] (String aus orig_records). Dadurch wurden
   beim VCF-Export via _build_format_fields alle FORMAT-Werte (DP, GQ, AD, PL)
   verworfen und gingen vollständig verloren.
2. QualityManager.get_vcf_sample_names: Methode fehlte auf QualityManager,
   wodurch Aufrufe in Distiller.process_vcf (Z. 15738) mit AttributeError
   scheiterten und Multi-Sample-Warnungen stumm unterdrückt wurden.
3. parse_vcf_records & parse_vcf_records_mmap: split("\t", 9) führte bei
   Multi-Sample-VCFs dazu, dass alle Sample-Spalten ab Index 9 in einen einzigen
   Tab-separierten String zusammengefasst wurden. Dies korrumpierte nachfolgende
   Format- und Genotyp-Parser (z.B. DP-Werte mit eingebetteten Tabs).
4. QualityManager._extract_dp: Bevorzugt nun sample-spezifisches FORMAT-DP
   vor dem Kohorten-Gesamt-DP aus INFO (analoge Priorität wie _get_dp_value).
"""
import os
import pathlib
import sys
import tempfile
from unittest.mock import MagicMock

SRC_FILE = pathlib.Path(__file__).resolve().parent.parent / "Variant_Fusion_pro_V17.py"
SRC = SRC_FILE.read_text(encoding="utf-8")

# Mocking für Module, falls noch nicht importiert
_MOCKS = [
    "tkinter", "tkinter.filedialog", "tkinter.ttk", "tkinter.messagebox",
    "ttkbootstrap", "ttkbootstrap.constants", "ttkbootstrap.dialogs",
    "ttkbootstrap.toast", "ttkbootstrap.scrolled",
    "psutil", "requests", "requests.adapters",
    "PIL", "PIL.Image", "PIL.ImageDraw",
    "intervaltree", "scipy", "scipy.stats", "aiohttp", "pystray"
]
for _m in _MOCKS:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()
if "ttkbootstrap.constants" in sys.modules:
    sys.modules["ttkbootstrap.constants"].BOTH = "both"

from Variant_Fusion_pro_V17 import (  # noqa: E402
    _extract_format_field,
    _get_dp_value,
    _build_format_fields,
    QualityManager,
    parse_vcf_records,
)


# ---------------------------------------------------------------------------
# Statische Quelltext-Prüfungen
# ---------------------------------------------------------------------------

def test_no_maxsplit_9_in_active_parsers():
    """In parse_vcf_records und parse_vcf_records_mmap darf kein split('	', 9) stehen."""
    # parse_vcf_records
    fn1_start = SRC.index("def parse_vcf_records(path,")
    fn1_block = SRC[fn1_start : fn1_start + 1200]
    assert 'split("\t", 9)' not in fn1_block and "split('\t', 9)" not in fn1_block, (
        "parse_vcf_records verwendet noch split mit maxsplit=9"
    )

    # parse_vcf_records_mmap
    fn2_start = SRC.index("def parse_vcf_records_mmap(")
    fn2_block = SRC[fn2_start : fn2_start + 1200]
    assert "split('\t', 9)" not in fn2_block and 'split("\t", 9)' not in fn2_block, (
        "parse_vcf_records_mmap verwendet noch split mit maxsplit=9"
    )


def test_quality_manager_defines_get_vcf_sample_names():
    """QualityManager muss get_vcf_sample_names definieren."""
    qm_start = SRC.index("class QualityManager:")
    qm_end = SRC.index("class QualitySettingsDialog(")
    qm_block = SRC[qm_start:qm_end]
    assert "def get_vcf_sample_names(" in qm_block, (
        "QualityManager hat keine Methode get_vcf_sample_names definiert"
    )


# ---------------------------------------------------------------------------
# Funktionale Tests: _extract_format_field & _build_format_fields
# ---------------------------------------------------------------------------

def test_extract_format_field_from_orig_records_dict():
    """
    orig_records speichert die Sample-Spalte unter dem Key 'sample' (Singular).
    _extract_format_field muss DP, GQ, AD, PL korrekt daraus extrahieren.
    """
    rec_from_orig = {
        "fmt": "GT:DP:GQ:AD:PL",
        "sample": "0/1:45:99:20,25:120,0,450",
    }
    assert _extract_format_field(rec_from_orig, "DP") == "45"
    assert _extract_format_field(rec_from_orig, "GQ") == "99"
    assert _extract_format_field(rec_from_orig, "AD") == "20,25"
    assert _extract_format_field(rec_from_orig, "PL") == "120,0,450"


def test_extract_format_field_from_parser_records_dict():
    """
    Parser liefert 'samples' als Liste. _extract_format_field muss auch diesen
    Typ weiterhin nahtlos unterstützen.
    """
    rec_from_parser = {
        "fmt": "GT:DP:GQ",
        "samples": ["0/1:30:80", "0/0:40:90"],
    }
    assert _extract_format_field(rec_from_parser, "DP") == "30"
    assert _extract_format_field(rec_from_parser, "GQ") == "80"


def test_extract_format_field_missing_or_dot_values():
    """Fehlende Felder oder '.'-Werte müssen None zurückgeben."""
    rec = {
        "fmt": "GT:DP:GQ",
        "sample": "0/1:.:.",
    }
    assert _extract_format_field(rec, "DP") is None
    assert _extract_format_field(rec, "GQ") is None
    assert _extract_format_field(rec, "NONEXISTENT") is None


def test_build_format_fields_preserves_quality_metrics():
    """
    _build_format_fields muss aus orig_records-Records die FORMAT-Tags
    zusammenbauen und darf Metriken wie DP/GQ/AD nicht mehr verwerfen.
    """
    rec = {
        "fmt": "GT:DP:GQ:AD",
        "sample": "0/1:45:99:20,25",
    }
    fmt_str, sample_str = _build_format_fields(rec, "0/1")
    assert fmt_str == "GT:DP:GQ:AD"
    assert sample_str == "0/1:45:99:20,25"


def test_get_dp_value_prioritizes_format_over_info():
    """_get_dp_value muss sample-spezifisches DP aus FORMAT vor INFO bevorzugen."""
    rec = {
        "fmt": "GT:DP",
        "sample": "0/1:15",
        "info": "DP=200;AF=0.05",
    }
    assert _get_dp_value(rec) == "15"


# ---------------------------------------------------------------------------
# Funktionale Tests: QualityManager
# ---------------------------------------------------------------------------

def test_quality_manager_extract_dp_priority():
    """QualityManager._extract_dp muss sample-spezifisches DP aus FORMAT vor INFO bevorzugen."""
    qm = QualityManager()
    rec_with_both = {
        "fmt": "GT:DP",
        "sample": "0/1:18",
        "info": {"DP": 150},
    }
    assert qm._extract_dp(rec_with_both) == 18

    rec_info_only = {
        "fmt": "GT",
        "sample": "0/1",
        "info": {"DP": 150},
    }
    assert qm._extract_dp(rec_info_only) == 150


def test_quality_manager_get_vcf_sample_names():
    """QualityManager.get_vcf_sample_names muss Sample-Namen aus dem #CHROM-Header extrahieren."""
    vcf_data = (
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tPATIENT_TUMOR\tPATIENT_NORMAL\n"
        "chr1\t100\t.\tA\tT\t60\tPASS\t.\tGT:DP\t0/1:40\t0/0:35\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".vcf", delete=False, encoding="utf-8") as f:
        f.write(vcf_data)
        tmp_path = f.name

    try:
        qm = QualityManager()
        names = qm.get_vcf_sample_names(tmp_path)
        assert names == ["PATIENT_TUMOR", "PATIENT_NORMAL"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------------------------
# Funktionale Tests: Multi-Sample Parsing in parse_vcf_records
# ---------------------------------------------------------------------------

def test_parse_vcf_records_multi_sample_separation():
    """
    parse_vcf_records muss bei Multi-Sample-VCFs jedes Sample als eigenes
    Element in rec['samples'] ablegen, nicht in einem gemeinsamen Tab-String.
    """
    vcf_data = (
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\tS2\tS3\n"
        "1\t5000\t.\tC\tG\t50\tPASS\t.\tGT:DP:GQ\t0/1:25:90\t0/0:30:99\t1/1:50:95\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".vcf", delete=False, encoding="utf-8") as f:
        f.write(vcf_data)
        tmp_path = f.name

    try:
        records = list(parse_vcf_records(tmp_path))
        assert len(records) == 1
        rec = records[0]
        assert len(rec["samples"]) == 3
        assert rec["samples"][0] == "0/1:25:90"
        assert rec["samples"][1] == "0/0:30:99"
        assert rec["samples"][2] == "1/1:50:95"
        assert _extract_format_field(rec, "DP") == "25"
        assert _extract_format_field(rec, "GQ") == "90"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
