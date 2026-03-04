#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VFDistiller Release Builder
============================
Baut die EXE via PyInstaller und erstellt ein Release-ZIP mit allen
nötigen Dateien für die Distribution.

Verwendung:
    python build_release.py            # Vollständiger Build + ZIP
    python build_release.py --skip-exe # Nur ZIP aus bestehendem dist/
    python build_release.py --clean    # Build-Artefakte aufräumen
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import zipfile

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
RELEASE_DIR = os.path.join(BASE_DIR, "releases")
SPEC_FILE = os.path.join(BASE_DIR, "VFDistiller.spec")
EXE_NAME = "VFDistiller.exe"

APP_VERSION = None  # Wird aus Hauptdatei gelesen

# Dateien die ins Release-ZIP kommen (relativ zu BASE_DIR)
RELEASE_FILES = [
    # Dokumentation
    "README.md",
    "ARCHITECTURE.md",

    # Konfigurationsvorlage
    "variant_fusion_settings.json.example",

    # Lizenzen
    "README/licenses/LICENSE.txt",
    "README/licenses/LICENSE.de.txt",
    "README/licenses/THIRD_PARTY_LICENSES.txt",

    # Übersetzungen
    "locales/translations.json",

    # Icon
    "ICO/ICO.ico",

    # gnomAD Download-Tool
    "Get gnomAD DB light.py",
]

# Verzeichnisse die komplett ins Release kommen
RELEASE_DIRS = [
    "data/annotations",  # GTF-Annotationsdaten (~85 MB)
]

# Dateien in RELEASE_DIRS die NICHT ins Release sollen
EXCLUDE_PATTERNS = [
    "_index.pkl",  # Generierte Caches, werden zur Laufzeit erzeugt
]


def get_version():
    """Liest APP_VERSION aus dem Hauptprogramm."""
    main_file = os.path.join(BASE_DIR, "Variant_Fusion_pro_V17.py")
    with open(main_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("APP_VERSION"):
                # APP_VERSION = "V17"
                return line.split("=")[1].strip().strip('"').strip("'")
    return "unknown"


def clean(args):
    """Räumt Build-Artefakte auf."""
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            print(f"  Entferne {d}")
            shutil.rmtree(d)
    print("  Aufgeräumt.")


def build_exe(args):
    """Baut die EXE via PyInstaller."""
    print("\n=== EXE-Build mit PyInstaller ===\n")

    if not os.path.exists(SPEC_FILE):
        print(f"FEHLER: {SPEC_FILE} nicht gefunden!")
        sys.exit(1)

    # PyInstaller prüfen
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True, check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("FEHLER: PyInstaller nicht installiert!")
        print("        pip install pyinstaller")
        sys.exit(1)

    # Build starten
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        SPEC_FILE,
    ]
    print(f"  Kommando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode != 0:
        print("\nFEHLER: PyInstaller-Build fehlgeschlagen!")
        sys.exit(1)

    exe_path = os.path.join(DIST_DIR, EXE_NAME)
    if not os.path.exists(exe_path):
        print(f"\nFEHLER: {exe_path} wurde nicht erzeugt!")
        sys.exit(1)

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"\n  EXE erzeugt: {exe_path} ({size_mb:.1f} MB)")


def should_exclude(filepath):
    """Prüft ob eine Datei ausgeschlossen werden soll."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in filepath:
            return True
    return False


def create_release_zip(version):
    """Erstellt das Release-ZIP."""
    print("\n=== Release-ZIP erstellen ===\n")

    os.makedirs(RELEASE_DIR, exist_ok=True)

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    zip_name = f"VFDistiller_{version}_{date_str}.zip"
    zip_path = os.path.join(RELEASE_DIR, zip_name)

    # Falls ZIP bereits existiert, mit Nummer versehen
    counter = 1
    while os.path.exists(zip_path):
        zip_name = f"VFDistiller_{version}_{date_str}_{counter}.zip"
        zip_path = os.path.join(RELEASE_DIR, zip_name)
        counter += 1

    release_root = f"VFDistiller_{version}"
    file_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:

        # 1. EXE
        exe_path = os.path.join(DIST_DIR, EXE_NAME)
        if os.path.exists(exe_path):
            arcname = f"{release_root}/{EXE_NAME}"
            zf.write(exe_path, arcname)
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"  + {EXE_NAME} ({size_mb:.1f} MB)")
            file_count += 1
        else:
            print(f"  WARNUNG: {exe_path} nicht gefunden — ZIP ohne EXE!")

        # 2. Einzeldateien
        for rel_path in RELEASE_FILES:
            src = os.path.join(BASE_DIR, rel_path)
            if os.path.exists(src):
                arcname = f"{release_root}/{rel_path}"
                zf.write(src, arcname)
                print(f"  + {rel_path}")
                file_count += 1
            else:
                print(f"  WARNUNG: {rel_path} nicht gefunden, übersprungen")

        # 3. Verzeichnisse
        for rel_dir in RELEASE_DIRS:
            src_dir = os.path.join(BASE_DIR, rel_dir)
            if not os.path.isdir(src_dir):
                print(f"  WARNUNG: Verzeichnis {rel_dir} nicht gefunden")
                continue

            for root, dirs, files in os.walk(src_dir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    rel = os.path.relpath(fpath, BASE_DIR)

                    if should_exclude(rel):
                        continue

                    arcname = f"{release_root}/{rel}"
                    zf.write(fpath, arcname)
                    size_kb = os.path.getsize(fpath) / 1024
                    print(f"  + {rel} ({size_kb:.0f} KB)")
                    file_count += 1

    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n  Release-ZIP: {zip_path}")
    print(f"  Dateien: {file_count}")
    print(f"  Größe: {zip_size_mb:.1f} MB")

    return zip_path


def main():
    parser = argparse.ArgumentParser(description="VFDistiller Release Builder")
    parser.add_argument(
        "--skip-exe", action="store_true",
        help="EXE-Build überspringen, nur ZIP aus bestehendem dist/"
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Build-Artefakte aufräumen (dist/, build/)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("VFDistiller Release Builder")
    print("=" * 60)

    if args.clean:
        clean(args)
        return

    version = get_version()
    print(f"  Version: {version}")
    print(f"  Basis:   {BASE_DIR}")

    # EXE bauen (falls nicht übersprungen)
    if not args.skip_exe:
        build_exe(args)
    else:
        exe_path = os.path.join(DIST_DIR, EXE_NAME)
        if not os.path.exists(exe_path):
            print(f"\nWARNUNG: Keine EXE in {DIST_DIR} gefunden!")
            print("         Verwende 'python build_release.py' ohne --skip-exe")

    # Release-ZIP erstellen
    zip_path = create_release_zip(version)

    print("\n" + "=" * 60)
    print("  FERTIG!")
    print(f"  Release: {zip_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
