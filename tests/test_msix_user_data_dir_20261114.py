# -*- coding: utf-8 -*-
"""MSIX/Store: Nutzerdateien nicht im schreibgeschützten Installationsordner (2026-11-14).

Im Store-Paket liegt die EXE unter Program Files/WindowsApps, dort darf die App nicht schreiben.
Seit V17.3 wich nur die Variant-DB nach %LOCALAPPDATA%/VariantFusion aus; Einstellungen, Cache,
Log, Instanz-Lock, resources_config.json, 23andMe-Konvertierungen und die Downloads unter data/
zielten weiter auf BASE_DIR = EXE-Ordner und gingen still verloren bzw. schlugen fehl.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import Variant_Fusion_pro_V17 as vf

ROOT = Path(__file__).resolve().parents[1]


def test_user_data_dir_stays_beside_a_writable_exe(tmp_path):
    assert vf._resolve_user_data_dir(str(tmp_path)) == str(tmp_path)
    assert not (tmp_path / ".vf_write_test").exists()


def test_user_data_dir_moves_to_localappdata_when_install_dir_is_not_writable(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    install_dir = tmp_path / "WindowsApps" / "VFDistiller"  # existiert nicht -> Schreibtest scheitert
    expected = tmp_path / "Local" / "VariantFusion"
    assert vf._resolve_user_data_dir(str(install_dir)) == str(expected)
    assert expected.is_dir()


def test_frozen_store_build_puts_all_user_files_into_localappdata(tmp_path):
    """Ganzer Modulstart wie in der Store-EXE: alle Schreibziele hängen an BASE_DIR."""
    install_dir = tmp_path / "WindowsApps" / "VFDistiller"
    local = tmp_path / "Local"
    script = (
        "import json, sys\n"
        f"sys.frozen = True\nsys.executable = {str(install_dir / 'VFDistiller.exe')!r}\n"
        "import Variant_Fusion_pro_V17 as vf\n"
        "print(json.dumps({'base': vf.BASE_DIR, 'settings': vf.SETTINGS_FILE, 'cache': vf.CACHE_FILE,"
        " 'vcf': vf.TEMP_VCF_DIR, 'log': vf.logger.logfile_path}))\n"
    )
    env = {**os.environ, "LOCALAPPDATA": str(local), "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=180)
    assert result.returncode == 0, result.stderr[-1500:]
    paths = json.loads(result.stdout.strip().splitlines()[-1])
    data_dir = local / "VariantFusion"
    assert Path(paths["base"]) == data_dir
    for key in ("settings", "cache", "vcf", "log"):
        assert Path(paths[key]).parent == data_dir, (key, paths[key])
