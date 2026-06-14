"""
Tests für make_source_zip.py — Source-ZIP-Builder für Linux/macOS.
"""
import importlib.util
import os
import zipfile
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parent.parent / "make_source_zip.py"
_spec = importlib.util.spec_from_file_location("make_source_zip", str(_SCRIPT))
_msz = importlib.util.module_from_spec(_spec)


def _load():
    if not hasattr(_msz, "should_exclude_from_source"):
        _spec.loader.exec_module(_msz)


# ---------------------------------------------------------------------------
# should_exclude_from_source
# ---------------------------------------------------------------------------

def test_exclude_pyd():
    _load()
    assert _msz.should_exclude_from_source("cython_hotpath/vcf_parser.cp312-win_amd64.pyd") is True


def test_exclude_index_pkl():
    _load()
    assert _msz.should_exclude_from_source("data/annotations/GRCh38_index.pkl") is True


def test_exclude_exe():
    _load()
    assert _msz.should_exclude_from_source("dist/VFDistiller.exe") is True
    assert _msz.should_exclude_from_source("SomeFile.exe") is True


def test_include_pyx():
    _load()
    assert _msz.should_exclude_from_source("cython_hotpath/vcf_parser.pyx") is False


def test_include_py():
    _load()
    assert _msz.should_exclude_from_source("Variant_Fusion_pro_V17.py") is False


def test_include_json():
    _load()
    assert _msz.should_exclude_from_source("locales/translations.json") is False


def test_include_md():
    _load()
    assert _msz.should_exclude_from_source("README.md") is False


# ---------------------------------------------------------------------------
# get_version
# ---------------------------------------------------------------------------

def test_get_version_returns_string(tmp_path):
    _load()
    main_py = tmp_path / "Variant_Fusion_pro_V17.py"
    main_py.write_text('APP_VERSION = "V17"\n', encoding="utf-8")
    version = _msz.get_version(base_dir=str(tmp_path))
    assert isinstance(version, str)
    assert len(version) > 0


def test_get_version_value(tmp_path):
    _load()
    main_py = tmp_path / "Variant_Fusion_pro_V17.py"
    main_py.write_text('APP_VERSION = "V17"\n', encoding="utf-8")
    assert _msz.get_version(base_dir=str(tmp_path)) == "V17"


# ---------------------------------------------------------------------------
# create_source_zip (integration)
# ---------------------------------------------------------------------------

def _build_minimal_project(base: Path):
    """Erstellt ein minimales Projektverzeichnis für Tests."""
    (base / "Variant_Fusion_pro_V17.py").write_text('APP_VERSION = "V17"\n', encoding="utf-8")
    (base / "README.md").write_text("# VFDistiller\n", encoding="utf-8")
    (base / "requirements.txt").write_text("requests\n", encoding="utf-8")
    cython = base / "cython_hotpath"
    cython.mkdir()
    (cython / "vcf_parser.pyx").write_text("# cython source\n", encoding="utf-8")
    (cython / "vcf_parser.cp312-win_amd64.pyd").write_bytes(b"\x00binary\x00")
    locales = base / "locales"
    locales.mkdir()
    (locales / "translations.json").write_text("{}", encoding="utf-8")


def test_create_source_zip_produces_file(tmp_path):
    _load()
    _build_minimal_project(tmp_path)
    out_dir = tmp_path / "out"
    zip_path = _msz.create_source_zip(version="TEST", base_dir=str(tmp_path), out_dir=str(out_dir))
    assert zip_path is not None
    assert os.path.exists(zip_path)
    assert zip_path.endswith(".zip")


def test_create_source_zip_includes_main_py(tmp_path):
    _load()
    _build_minimal_project(tmp_path)
    out_dir = tmp_path / "out"
    zip_path = _msz.create_source_zip(version="TEST", base_dir=str(tmp_path), out_dir=str(out_dir))
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert any("Variant_Fusion_pro_V17.py" in n for n in names)


def test_create_source_zip_includes_pyx(tmp_path):
    _load()
    _build_minimal_project(tmp_path)
    out_dir = tmp_path / "out"
    zip_path = _msz.create_source_zip(version="TEST", base_dir=str(tmp_path), out_dir=str(out_dir))
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert any("vcf_parser.pyx" in n for n in names)


def test_create_source_zip_excludes_pyd(tmp_path):
    _load()
    _build_minimal_project(tmp_path)
    out_dir = tmp_path / "out"
    zip_path = _msz.create_source_zip(version="TEST", base_dir=str(tmp_path), out_dir=str(out_dir))
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert not any(".pyd" in n for n in names)


def test_create_source_zip_includes_locales(tmp_path):
    _load()
    _build_minimal_project(tmp_path)
    out_dir = tmp_path / "out"
    zip_path = _msz.create_source_zip(version="TEST", base_dir=str(tmp_path), out_dir=str(out_dir))
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert any("translations.json" in n for n in names)
