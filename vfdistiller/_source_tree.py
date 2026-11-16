# -*- coding: utf-8 -*-
"""Hilfsfunktionen zum Laden des kombinierten Projekt-Quelltexts für Vertragstests."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union


def load_project_source(
    repo_root: Optional[Union[str, Path]] = None,
    *,
    respect_env: bool = True,
) -> str:
    """Liest Hauptmodul und extrahierte Paketmodule für statische Quelltext-Tests.

    Ist die Umgebungsvariable ``VFD_SRC`` gesetzt und ``respect_env=True``,
    wird weiterhin gezielt diese Einzeldatei gelesen (Red-on-Revert-Vertrag).
    """
    env_override = os.environ.get("VFD_SRC") if respect_env else None
    if env_override:
        return Path(env_override).read_text(encoding="utf-8")

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parent.parent
    parts: list[str] = []

    main_file = root / "Variant_Fusion_pro_V17.py"
    if main_file.is_file():
        parts.append(main_file.read_text(encoding="utf-8"))

    pkg_dir = root / "vfdistiller"
    if pkg_dir.is_dir():
        for py_file in sorted(pkg_dir.glob("*.py")):
            parts.append(py_file.read_text(encoding="utf-8"))

    return "\n".join(parts)
