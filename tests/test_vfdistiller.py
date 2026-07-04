"""
Funktionstests fuer VFDistiller (Variant_Fusion_pro_V17.py)

Testet reine Business-Logik-Funktionen ohne GUI.
Alle GUI- und externe Abhaengigkeiten werden gemockt.
"""
import itertools
import json
import queue
import sys
import threading
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
_TRANSLATIONS_PATH = Path(__file__).parent.parent / "locales" / "translations.json"
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


class _FakeCursor:
    def execute(self, *args, **kwargs):
        return None

    def executemany(self, *args, **kwargs):
        return None

    def fetchall(self):
        return []


class _FakeConnection:
    def __init__(self):
        self.closed = False
        self.committed = False
        self.cursor_obj = _FakeCursor()

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def _install_connect_spy(monkeypatch, fake_conn):
    calls = []

    def fake_connect(*args, **kwargs):
        calls.append((args, kwargs))
        return fake_conn

    monkeypatch.setattr(_vf.sqlite3, "connect", fake_connect)
    return calls


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


def test_lookup_lightdb_closes_connection_on_cursor_failure(monkeypatch):
    fetcher = _vf.AFFetchController.__new__(_vf.AFFetchController)
    fetcher.logger = MagicMock()

    class CursorFailConnection(_FakeConnection):
        def cursor(self):
            raise RuntimeError("cursor failed")

    fake_conn = CursorFailConnection()
    calls = _install_connect_spy(monkeypatch, fake_conn)

    uncached = [("1", 123, "A", "C", "GRCh37")]
    results, still_uncached = fetcher._lookup_lightdb(uncached, db_path="lightdb.sqlite")

    assert results == {}
    assert still_uncached == uncached
    assert fake_conn.closed is True
    assert calls[0][1]["check_same_thread"] is False


def test_lookup_lightdb_tolerates_connect_failure(monkeypatch):
    fetcher = _vf.AFFetchController.__new__(_vf.AFFetchController)
    fetcher.logger = MagicMock()
    calls = []

    def fail_connect(*args, **kwargs):
        calls.append((args, kwargs))
        raise RuntimeError("connect failed")

    monkeypatch.setattr(_vf.sqlite3, "connect", fail_connect)

    uncached = [("1", 123, "A", "C", "GRCh37")]
    results, still_uncached = fetcher._lookup_lightdb(uncached, db_path="lightdb.sqlite")

    assert results == {}
    assert still_uncached == uncached
    fetcher.logger.log.assert_any_call("[LightDB] ⚠️ Fehler beim Lookup: connect failed")
    assert calls[0][1]["check_same_thread"] is False


def test_lookup_variants_bulk_uses_worker_safe_connection(tmp_path, monkeypatch):
    manager = _vf.LightDBGnomADManager.__new__(_vf.LightDBGnomADManager)
    manager.logger = MagicMock()

    db_path = tmp_path / "lightdb.sqlite"
    db_path.write_text("", encoding="utf-8")
    manager.OUT_DB = str(db_path)

    fake_conn = _FakeConnection()
    calls = _install_connect_spy(monkeypatch, fake_conn)

    results, still_uncached = manager.lookup_variants_bulk([
        ("1", 123, "A", "C", "GRCh37"),
    ])

    assert results == {}
    assert still_uncached == [("1", 123, "A", "C", "GRCh37")]
    assert fake_conn.closed is True
    assert calls[0][1]["check_same_thread"] is False


def test_vcf_migrate_loop_uses_worker_safe_connection(tmp_path, monkeypatch):
    proc = _vf.VCFMigrationsdienst.__new__(_vf.VCFMigrationsdienst)
    proc.cache_path = str(tmp_path / "cache.json")
    proc.db_path = str(tmp_path / "variants.sqlite")
    proc.batch_size = 1
    proc.logger = MagicMock()
    proc._stop_event = threading.Event()
    proc.pidfile = str(tmp_path / "vcf.pid")
    time_values = itertools.count(start=100.0, step=1.0)
    monkeypatch.setattr(_vf.time, "time", lambda: next(time_values))

    Path(proc.cache_path).write_text(
        json.dumps([["variant-1", {"af": 0.123}]]),
        encoding="utf-8",
    )

    fake_conn = _FakeConnection()
    calls = _install_connect_spy(monkeypatch, fake_conn)
    monkeypatch.setattr(proc, "_commit_batch", lambda _cur, _buffer: 0)

    assert proc._migrate_loop() is True
    assert fake_conn.closed is True
    assert calls[0][1]["check_same_thread"] is False


def test_vcf_migrate_to_db_uses_worker_safe_connection(tmp_path, monkeypatch):
    proc = _vf.VCFMigrationsdienst.__new__(_vf.VCFMigrationsdienst)
    proc._record_queue = queue.Queue()
    proc._record_queue.put(("variant-1", {"af": 0.123}))
    proc.db_path = str(tmp_path / "variants.sqlite")
    proc.batch_size = 1
    proc.logger = MagicMock()
    proc._stop_event = threading.Event()
    proc.pidfile = str(tmp_path / "vcf.pid")
    time_values = itertools.count(start=200.0, step=1.0)
    monkeypatch.setattr(_vf.time, "time", lambda: next(time_values))

    fake_conn = _FakeConnection()
    calls = _install_connect_spy(monkeypatch, fake_conn)
    monkeypatch.setattr(proc, "_commit_batch", lambda _cur, _buffer: 0)

    assert proc.migrate_to_db() is True
    assert fake_conn.closed is True
    assert fake_conn.committed is True
    assert calls[0][1]["check_same_thread"] is False


def test_distiller_lookup_lightdb_uses_worker_safe_connection(tmp_path, monkeypatch):
    distiller = _vf.Distiller.__new__(_vf.Distiller)
    distiller.logger = MagicMock()

    fake_conn = _FakeConnection()
    calls = _install_connect_spy(monkeypatch, fake_conn)

    results, still_uncached = distiller._lookup_lightdb(
        [("1", 123, "A", "C", "GRCh37")],
        db_path=str(tmp_path / "lightdb.sqlite"),
    )

    assert results == {}
    assert still_uncached == [("1", 123, "A", "C", "GRCh37")]
    assert fake_conn.closed is True
    assert calls[0][1]["check_same_thread"] is False


def test_compact_icon_buttons_expose_tooltip_context():
    src = _MODULE_PATH.read_text(encoding="utf-8")

    assert 'self._attach_tooltip(refresh_btn, self._t("Ergebnisse neu laden"))' in src
    assert 'self._attach_tooltip(whitelist_btn, self._t("Whitelist laden"))' in src
    assert 'self._attach_tooltip(blacklist_btn, self._t("Blacklist laden"))' in src
    assert 'widget._vf_tooltip_text = text' in src
    assert '("<FocusIn>", schedule_tooltip)' in src


def test_tooltip_translations_cover_refresh_action():
    translations = json.loads(_TRANSLATIONS_PATH.read_text(encoding="utf-8"))

    assert translations["Ergebnisse neu laden"]["de"] == "Ergebnisse neu laden"
    assert translations["Ergebnisse neu laden"]["en"] == "Reload displayed results"
