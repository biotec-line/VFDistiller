#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VFDistiller Source-ZIP Builder (Linux / macOS)
================================================
Erstellt ein Source-ZIP für Plattformen ohne Windows-EXE-Build.
Enthalten: alle Python-Quellen, Übersetzungen, Cython-Hotpath (.pyx),
           Tests, Dokumentation, Lizenzen.
Nicht enthalten: .pyd-Binaries, .exe, generierte Caches,
                 FASTA-Referenzgenome, Nutzerdaten.

Verwendung:
    python make_source_zip.py         # Source-ZIP erstellen
    python make_source_zip.py --clean # Vorhandene Source-ZIPs entfernen
"""

import argparse
import datetime
import os
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RELEASE_DIR = os.path.join(BASE_DIR, "releases")

# Einzeldateien die ins Source-ZIP kommen (relativ zu BASE_DIR)
SOURCE_RELEASE_FILES = [
    # Python-Quellen
    "Variant_Fusion_pro_V17.py",
    "translator.py",
    "translator_patch.py",
    "manage_translations.py",
    "lightdb_index_worker.py",
    # Abhängigkeiten
    "requirements.txt",
    # Dokumentation
    "README.md",
    "README.de.md",
    "ARCHITECTURE.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "PRIVACY_POLICY.md",
    "llms.txt",
    # Lizenzen
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_LICENSES.txt",
    # Konfigurationsvorlage
    "variant_fusion_settings.json.example",
    # Hilfsprogramme
    "Get gnomAD DB light.py",
    # Icon
    "VFDistiller.ico",
    # Build-Skripte (damit Tests im entpackten ZIP funktionieren)
    "make_source_zip.py",
    "build_release.py",
]

# Verzeichnisse die komplett ins Source-ZIP kommen
SOURCE_RELEASE_DIRS = [
    "locales",        # translations.json
    "cython_hotpath", # .pyx + setup.py (optional, Verzeichnis kann fehlen)
    "tests",          # Smoke- und Funktionstests
]

# Dateimuster die aus dem Source-ZIP ausgeschlossen werden
SOURCE_EXCLUDE_PATTERNS = [
    ".pyd",       # Windows-Cython-Binaries
    "_index.pkl", # generierte Annotations-Caches
    ".exe",       # Windows-Executables
]


def should_exclude_from_source(filepath: str) -> bool:
    """Gibt True zurück wenn die Datei aus dem Source-ZIP ausgeschlossen werden soll."""
    for pattern in SOURCE_EXCLUDE_PATTERNS:
        if filepath.endswith(pattern) or pattern in os.path.basename(filepath):
            return True
    return False


def get_version(base_dir: str = None) -> str:
    """Liest APP_VERSION aus dem Hauptprogramm."""
    if base_dir is None:
        base_dir = BASE_DIR
    main_file = os.path.join(base_dir, "Variant_Fusion_pro_V17.py")
    with open(main_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("APP_VERSION"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "unknown"


def create_source_zip(version: str, base_dir: str = None, out_dir: str = None) -> str:
    """Erstellt das Source-ZIP und gibt den Pfad zurück."""
    if base_dir is None:
        base_dir = BASE_DIR
    if out_dir is None:
        out_dir = RELEASE_DIR

    os.makedirs(out_dir, exist_ok=True)

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    zip_name = f"VFDistiller_{version}_source_{date_str}.zip"
    zip_path = os.path.join(out_dir, zip_name)

    counter = 1
    while os.path.exists(zip_path):
        zip_name = f"VFDistiller_{version}_source_{date_str}_{counter}.zip"
        zip_path = os.path.join(out_dir, zip_name)
        counter += 1

    release_root = f"VFDistiller_{version}_source"
    file_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:

        # 1. Einzeldateien
        for rel_path in SOURCE_RELEASE_FILES:
            src = os.path.join(base_dir, rel_path)
            if os.path.exists(src):
                zf.write(src, f"{release_root}/{rel_path}")
                print(f"  + {rel_path}")
                file_count += 1
            else:
                print(f"  WARNUNG: {rel_path} nicht gefunden, uebersprungen")

        # 2. Verzeichnisse
        for rel_dir in SOURCE_RELEASE_DIRS:
            src_dir = os.path.join(base_dir, rel_dir)
            if not os.path.isdir(src_dir):
                print(f"  WARNUNG: Verzeichnis {rel_dir} nicht gefunden, uebersprungen")
                continue

            for root, dirs, files in os.walk(src_dir):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for fname in files:
                    fpath = os.path.join(root, fname)
                    rel = os.path.relpath(fpath, base_dir)
                    if should_exclude_from_source(rel):
                        continue
                    zf.write(fpath, f"{release_root}/{rel}")
                    print(f"  + {rel}")
                    file_count += 1

    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n  Source-ZIP: {zip_path}")
    print(f"  Dateien:    {file_count}")
    print(f"  Groesse:    {zip_size_mb:.1f} MB")

    return zip_path


def clean():
    """Entfernt vorhandene Source-ZIPs aus dem releases/-Verzeichnis."""
    if not os.path.isdir(RELEASE_DIR):
        print("  Nichts zu bereinigen.")
        return
    removed = 0
    for fname in os.listdir(RELEASE_DIR):
        if "_source_" in fname and fname.endswith(".zip"):
            os.remove(os.path.join(RELEASE_DIR, fname))
            print(f"  Entfernt: {fname}")
            removed += 1
    print(f"  {removed} Datei(en) entfernt.")


def main():
    parser = argparse.ArgumentParser(description="VFDistiller Source-ZIP Builder (Linux / macOS)")
    parser.add_argument("--clean", action="store_true",
                        help="Vorhandene Source-ZIPs aus releases/ entfernen")
    args = parser.parse_args()

    print("=" * 60)
    print("VFDistiller Source-ZIP Builder (Linux / macOS)")
    print("=" * 60)

    if args.clean:
        clean()
        return

    version = get_version()
    print(f"  Version: {version}")
    print(f"  Basis:   {BASE_DIR}")
    print()

    zip_path = create_source_zip(version)

    print()
    print("=" * 60)
    print("  FERTIG!")
    print(f"  Source-ZIP: {zip_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
