"""
Funktionstests fuer VFDistiller (Variant_Fusion_pro_V17.py)

Testet reine Business-Logik-Funktionen ohne GUI.
Alle GUI- und externe Abhaengigkeiten werden gemockt.
"""
import sys
import importlib
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# GUI- und Third-Party-Module mocken BEVOR das Hauptmodul geladen wird
# ---------------------------------------------------------------------------
_MOCKS = [
    "tkinter", "tkinter.filedialog", "tkinter.ttk", "tkinter.messagebox",
    "ttkbootstrap", "ttkbootstrap.constants", "ttkbootstrap.dialogs",
    "ttkbootstrap.toast", "ttkbootstrap.scrolled",
    "psutil",
    "requests", "requests.adapters",
    "PIL", "PIL.Image", "PIL.ImageDraw",
    "intervaltree",
    "scipy", "scipy.stats",
    "aiohttp",
]
for _m in _MOCKS:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()

# MagicMock fuer ttkbootstrap.constants - sonst scheitert Sternimport
sys.modules["ttkbootstrap.constants"].BOTH = "both"

# Translator- und Logger-Mock (optional, falls im Modul verwendet)
if "translator" not in sys.modules:
    sys.modules["translator"] = MagicMock()

# ---------------------------------------------------------------------------
# Hauptmodul laden
# ---------------------------------------------------------------------------
_MODULE_PATH = Path(__file__).parent.parent / "Variant_Fusion_pro_V17.py"
_spec = importlib.util.spec_from_file_location("vf_v17", str(_MODULE_PATH))
_vf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vf)

# Funktionen extrahieren
safe_float = _vf.safe_float
now_iso = _vf.now_iso
parse_iso_utc = _vf.parse_iso_utc
is_gzipped = _vf.is_gzipped
is_vcf = _vf.is_vcf
_normalize_chrom_vcf = _vf._normalize_chrom_vcf
fmt_eta = _vf.fmt_eta


# ---------------------------------------------------------------------------
# Tests: safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_valid_float(self):
        assert safe_float("0.05") == pytest.approx(0.05)

    def test_integer_string(self):
        assert safe_float("1") == 1.0

    def test_invalid_string_returns_none(self):
        assert safe_float("nicht_zahl") is None

    def test_none_returns_none(self):
        assert safe_float(None) is None

    def test_negative_without_flag_returns_none(self):
        assert safe_float("-0.5") is None

    def test_negative_with_allow_flag(self):
        assert safe_float("-0.5", allow_negative=True) == pytest.approx(-0.5)

    def test_zero_is_valid(self):
        assert safe_float("0.0") == 0.0


# ---------------------------------------------------------------------------
# Tests: is_gzipped / is_vcf
# ---------------------------------------------------------------------------

class TestFileTypeChecks:
    def test_gz_is_gzipped(self):
        assert is_gzipped("file.vcf.gz") is True

    def test_bgz_is_gzipped(self):
        assert is_gzipped("file.vcf.bgz") is True

    def test_plain_vcf_not_gzipped(self):
        assert is_gzipped("file.vcf") is False

    def test_vcf_extension_recognized(self):
        assert is_vcf("variants.vcf") is True

    def test_vcf_gz_recognized(self):
        assert is_vcf("variants.vcf.gz") is True

    def test_txt_not_vcf(self):
        assert is_vcf("file.txt") is False


# ---------------------------------------------------------------------------
# Tests: _normalize_chrom_vcf
# ---------------------------------------------------------------------------

class TestNormalizeChrom:
    def test_chr_prefix_removed(self):
        assert _normalize_chrom_vcf("chr1") == "1"

    def test_uppercase_chr_removed(self):
        assert _normalize_chrom_vcf("CHR1") == "1"

    def test_x_chromosome(self):
        assert _normalize_chrom_vcf("chrX") == "X"

    def test_m_becomes_mt(self):
        assert _normalize_chrom_vcf("M") == "MT"

    def test_chrm_becomes_mt(self):
        assert _normalize_chrom_vcf("chrM") == "MT"

    def test_already_normalized(self):
        assert _normalize_chrom_vcf("22") == "22"


# ---------------------------------------------------------------------------
# Tests: fmt_eta
# ---------------------------------------------------------------------------

class TestFmtEta:
    def test_none_returns_placeholder(self):
        assert fmt_eta(None) == "ETA --:--"

    def test_seconds_under_one_hour(self):
        result = fmt_eta(90)  # 1 Minute 30 Sekunden
        assert result == "ETA 01:30"

    def test_seconds_over_one_hour(self):
        result = fmt_eta(3661)  # 1 Stunde, 1 Minute, 1 Sekunde
        assert "01:01:01" in result
