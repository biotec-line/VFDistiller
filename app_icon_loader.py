# -*- coding: utf-8 -*-
"""Anwendungs-Icon-Loader für VFDistiller.

Stellt robuste Funktionen bereit, um das Anwendungs-Icon zur Laufzeit
mit Multi-Pfad-Fallback zu lokalisieren und an Tkinter/ttkbootstrap-
Fenster zu binden.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Optional


def get_project_root() -> Path:
    """Ermittelt das Projekt-Wurzelverzeichnis."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def get_app_icon_path() -> Optional[Path]:
    """Sucht und liefert den Pfad zum besten verfügbaren Anwendungs-Icon."""
    base_dirs = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dirs.append(Path(sys._MEIPASS))
    base_dirs.append(Path(__file__).resolve().parent)
    base_dirs.append(Path.cwd())

    icon_candidates = [
        "VFDistiller.ico",
        "icon.ico",
        "DesktopIcon.ico",
        "assets/vfdistiller.ico",
        "assets/icon.ico",
        "assets/app_icon.ico",
        "assets/DesktopIcon.ico",
        "ICO/ICO.ico",
        "icon.png",
        "DesktopIcon.png",
        "assets/icon.png",
    ]

    for base in base_dirs:
        for rel in icon_candidates:
            candidate = base / rel
            if candidate.is_file():
                return candidate
    return None


def load_app_icon(window: Optional[Any] = None) -> Optional[Path]:
    """Lädt das Anwendungs-Icon und bindet es optional an ein Tkinter-Fenster."""
    icon_path = get_app_icon_path()
    if icon_path is None:
        return None

    if window is not None:
        try:
            # Unter Windows bevorzugt iconbitmap mit 7-Layer ICO
            if icon_path.suffix.lower() == ".ico":
                window.iconbitmap(str(icon_path))
            else:
                import tkinter as tk
                photo = tk.PhotoImage(file=str(icon_path))
                window.iconphoto(True, photo)
        except Exception:
            pass

    return icon_path
