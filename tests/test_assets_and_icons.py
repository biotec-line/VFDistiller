# -*- coding: utf-8 -*-
"""Vertragstests für App-Icons, Multi-Resolution-ICOs, PWA-Assets und Runtime-Iconloader."""

import json
from pathlib import Path
import struct
from PIL import Image



def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_ico_sizes(ico_path: Path):
    with open(ico_path, "rb") as f:
        _reserved, ico_type, count = struct.unpack("<HHH", f.read(6))
        assert ico_type == 1, f"{ico_path.name} ist keine valide ICO-Datei"
        sizes = []
        for _ in range(count):
            w, h, _colors, _res, _planes, _bpp, _size, _offset = struct.unpack(
                "<BBBBHHII", f.read(16)
            )
            sizes.append((w or 256, h or 256))
        return set(sizes)


def test_master_icon_properties():
    """Verifiziert die 1024x1024 Master-Icons auf Dimension, Format und RGBA-Kanal."""
    root = _get_project_root()
    master_files = [
        root / "DesktopIcon.png",
        root / "icon.png",
        root / "VFDistiller.png",
        root / "assets" / "DesktopIcon.png",
        root / "assets" / "icon.png",
        root / "assets" / "VFDistiller.png",
        root / "mobile_icons" / "icon.png",
    ]
    for path in master_files:
        assert path.is_file(), f"Master-Icon fehlt: {path}"
        with Image.open(path) as img:
            assert img.format == "PNG", f"Ungültiges Format für {path}: {img.format}"
            assert img.size == (1024, 1024), f"Falsche Dimensionen für {path}: {img.size}"
            assert img.mode == "RGBA", f"Falscher Farbmodus für {path}: {img.mode}"


def test_windows_multi_res_ico_layers():
    """Verifiziert, dass alle 7 Windows-Auflösungs-Layer in den App-ICOs vorhanden sind."""
    root = _get_project_root()
    required_layers = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}
    ico_targets = [
        root / "DesktopIcon.ico",
        root / "VFDistiller.ico",
        root / "icon.ico",
        root / "ICO" / "ICO.ico",
        root / "assets" / "DesktopIcon.ico",
        root / "assets" / "vfdistiller.ico",
        root / "assets" / "icon.ico",
        root / "assets" / "app_icon.ico",
    ]
    for ico_path in ico_targets:
        assert ico_path.is_file(), f"ICO fehlt: {ico_path}"
        available = _read_ico_sizes(ico_path)
        for req in required_layers:
            assert req in available, f"Fehlende Ebene {req} in {ico_path} (vorhanden: {available})"

    fav_icos = [
        root / "assets" / "favicon.ico",
        root / "mobile_icons" / "favicon.ico",
        root / "web_companion" / "favicon.ico",
        root / "web_companion" / "icons" / "favicon.ico",
    ]
    fav_req = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)}
    for fav_path in fav_icos:
        assert fav_path.is_file(), f"Favicon fehlt: {fav_path}"
        available = _read_ico_sizes(fav_path)
        for req in fav_req:
            assert req in available, f"Fehlende Favicon-Ebene {req} in {fav_path}"


def test_pwa_mobile_icons_and_manifest():
    """Verifiziert die PWA- und Mobile-Iconsuite inklusive Web App Manifest."""
    root = _get_project_root()
    manifest_path = root / "mobile_icons" / "manifest.json"
    assert manifest_path.is_file(), "manifest.json fehlt in mobile_icons/"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("short_name") == "VFDistiller"
    assert "VFDistiller" in manifest.get("name", "")
    assert manifest.get("theme_color") == "#0067ba"
    assert len(manifest.get("icons", [])) >= 4

    expected_sizes = {
        root / "mobile_icons" / "icon-192.png": (192, 192),
        root / "mobile_icons" / "icon-512.png": (512, 512),
        root / "mobile_icons" / "icon-maskable-192.png": (192, 192),
        root / "mobile_icons" / "icon-maskable-512.png": (512, 512),
        root / "mobile_icons" / "apple-touch-icon.png": (180, 180),
        root / "mobile_icons" / "apple-touch-icon-180.png": (180, 180),
        root / "mobile_icons" / "favicon.png": (32, 32),
        root / "mobile_icons" / "icons" / "icon-192.png": (192, 192),
        root / "mobile_icons" / "icons" / "icon-512.png": (512, 512),
        root / "mobile_icons" / "icons" / "icon-maskable-192.png": (192, 192),
        root / "mobile_icons" / "icons" / "icon-maskable-512.png": (512, 512),
        root / "mobile_icons" / "icons" / "apple-touch-icon.png": (180, 180),
        root / "mobile_icons" / "icons" / "favicon.png": (32, 32),
    }

    for file_path, size in expected_sizes.items():
        assert file_path.is_file(), f"Mobile-Icon fehlt: {file_path}"
        with Image.open(file_path) as img:
            assert img.format == "PNG"
            assert img.size == size, f"Falsche Abmessung für {file_path}: {img.size} != {size}"


def test_store_assets_dimensions():
    """Verifiziert die Windows Store- und Kachel-Assets auf standardkonforme Dimensionen."""
    root = _get_project_root()
    expected_tiles = {
        root / "store_assets" / "icon_44x44.png": (44, 44),
        root / "store_assets" / "icon_50x50.png": (50, 50),
        root / "store_assets" / "icon_150x150.png": (150, 150),
        root / "store_assets" / "icon_310x150.png": (310, 150),
        root / "store_assets" / "icon_310x310.png": (310, 310),
        root / "store_assets" / "Square44x44Logo.png": (44, 44),
        root / "store_assets" / "Square50x50Logo.png": (50, 50),
        root / "store_assets" / "Square150x150Logo.png": (150, 150),
        root / "store_assets" / "Square310x310Logo.png": (310, 310),
        root / "store_assets" / "Wide310x150Logo.png": (310, 150),
        root / "store_assets" / "StoreLogo.png": (50, 50),
        root / "store_package" / "icons" / "icon_44x44.png": (44, 44),
        root / "store_package" / "icons" / "icon_50x50.png": (50, 50),
        root / "store_package" / "icons" / "icon_150x150.png": (150, 150),
        root / "store_package" / "icons" / "icon_310x150.png": (310, 150),
        root / "store_package" / "icons" / "icon_310x310.png": (310, 310),
    }
    for file_path, size in expected_tiles.items():
        assert file_path.is_file(), f"Store-Asset fehlt: {file_path}"
        with Image.open(file_path) as img:
            assert img.size == size, f"Falsche Dimensionen für {file_path}: {img.size} != {size}"


def test_runtime_app_icon_loader():
    """Verifiziert, dass der Runtime-Loader das App-Icon korrekt lokalisiert."""
    import sys
    root = _get_project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app_icon_loader import get_app_icon_path, load_app_icon, get_project_root

    assert get_project_root() == root
    icon_path = get_app_icon_path()
    assert icon_path is not None, "get_app_icon_path liefert None"
    assert icon_path.is_file(), f"Icon existiert nicht: {icon_path}"
    assert icon_path.suffix.lower() in {".ico", ".png"}

    # Test ohne Fenster
    loaded = load_app_icon(None)
    assert loaded == icon_path

    # Test mit Dummy-Fenster-Mock
    class DummyWindow:
        def __init__(self):
            self.bitmap_path = None
        def iconbitmap(self, path):
            self.bitmap_path = path

    dummy = DummyWindow()
    res = load_app_icon(dummy)
    assert res == icon_path
    assert dummy.bitmap_path == str(icon_path)
