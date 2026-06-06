"""
source_platform_smoke.py — Plattform-Smoke für Linux und macOS.

Nicht automatisch von pytest gesammelt (kein test_-Präfix, pytest.ini schränkt
Kollektion auf tests/ mit Standard-Discovery ein).

Expliziter Aufruf lokal und in CI:
    pytest tests/source_platform_smoke.py -v
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_MODULE_PATH = Path(__file__).parent.parent / "Variant_Fusion_pro_V17.py"

_MOCKS = [
    "tkinter", "tkinter.filedialog", "tkinter.ttk", "tkinter.messagebox",
    "ttkbootstrap", "ttkbootstrap.constants", "ttkbootstrap.dialogs",
    "ttkbootstrap.toast", "ttkbootstrap.scrolled",
    "psutil", "requests", "requests.adapters",
    "PIL", "PIL.Image", "PIL.ImageDraw",
    "intervaltree", "scipy", "scipy.stats", "aiohttp",
]


def _load_vf_with_mocks():
    """Lädt Variant_Fusion_pro_V17; mockt nur Deps, die NOCH NICHT in sys.modules sind.

    Analog zum Muster in tests/test_vfdistiller.py: installierte echte Module bleiben
    erhalten, damit transitive Imports anderer Pakete (z. B. alphagenome -> anndata ->
    scipy.sparse) nicht durch einen Mock-Tausch brechen.
    """
    added = []
    for m in _MOCKS + ["translator"]:
        if m not in sys.modules:
            sys.modules[m] = MagicMock()
            added.append(m)
    # BOTH ist fuer `from ttkbootstrap.constants import *` noetig (real oder mock)
    sys.modules["ttkbootstrap.constants"].BOTH = "both"

    try:
        spec = importlib.util.spec_from_file_location("_vf_smoke", str(_MODULE_PATH))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for m in added:
            sys.modules.pop(m, None)


# ── Check 1: Python-Version ──────────────────────────────────────────────────

def test_python_version_ge_310():
    assert sys.version_info >= (3, 10), (
        f"Python 3.10+ erwartet; aktuell "
        f"{sys.version_info.major}.{sys.version_info.minor}"
    )


# ── Check 2: Pflicht-Deps real importierbar ───────────────────────────────────

def test_core_deps_importable():
    """requests, psutil, Pillow, scipy, intervaltree ohne Display importierbar."""
    import requests       # noqa: F401
    import psutil         # noqa: F401
    import PIL.Image      # noqa: F401
    import scipy.stats    # noqa: F401
    import intervaltree   # noqa: F401


# ── Check 3: tkinter verfügbar, OHNE Tk()-Instanz ────────────────────────────

def test_tkinter_importable_no_instance():
    """tkinter ist installiert; erzeugt KEINE Tk()-Instanz (headless-safe)."""
    import tkinter
    assert callable(tkinter.Tk), "tkinter.Tk muss aufrufbar sein"


# ── Check 4: ttkbootstrap (headless-tolerant) ────────────────────────────────

def test_ttkbootstrap_importable():
    """ttkbootstrap importierbar; skip bei headless-TclError."""
    try:
        import ttkbootstrap  # noqa: F401
    except Exception as exc:
        msg = str(exc).lower()
        if any(kw in msg for kw in ("display", "tcl", "tk")):
            pytest.skip(f"headless-TclError erwartet ohne DISPLAY: {exc}")
        raise


# ── Check 5: Hauptmodul mit Mocks ladbar, kein sys.exit ──────────────────────

def test_module_loadable_with_mocks():
    mod = _load_vf_with_mocks()
    assert hasattr(mod, "APP_VERSION"), "APP_VERSION fehlt im Modul"
    assert mod.APP_VERSION == "V17", f"APP_VERSION = {mod.APP_VERSION!r}"


# ── Check 6: safe_float Basislogik ───────────────────────────────────────────

def test_safe_float_basic():
    mod = _load_vf_with_mocks()
    assert mod.safe_float("3.14") == pytest.approx(3.14)
    assert mod.safe_float("nicht_zahl") is None   # ungültige Eingabe → None
    assert mod.safe_float(None) is None            # None-Eingabe → None


# ── Check 7: VCF-Erkennung mit echtem Fixture ────────────────────────────────

def test_is_vcf_detection(tmp_path):
    mod = _load_vf_with_mocks()

    vcf = tmp_path / "sample.vcf"
    vcf.write_text("##fileformat=VCFv4.1\n#CHROM\tPOS\n", encoding="utf-8")
    assert mod.is_vcf(str(vcf)) is True

    txt = tmp_path / "nope.txt"
    txt.write_text("nur Text\n", encoding="utf-8")
    assert mod.is_vcf(str(txt)) is False
