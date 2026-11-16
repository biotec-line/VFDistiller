# -*- coding: utf-8 -*-
"""Allgemeine Hilfsfunktionen und Abbruchsignal ohne GUI-Abhängigkeit."""
from __future__ import annotations

import datetime
import math
import threading
from typing import Optional


def fmt_eta(seconds: Optional[float]) -> str:
    """Formatiert Sekunden in ein ETA-Format."""
    if seconds is None:
        return "ETA --:--"
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    s2 = s % 60
    if h > 0:
        return f"ETA {h:02d}:{m:02d}:{s2:02d}"
    return f"ETA {m:02d}:{s2:02d}"


def safe_float(x, allow_negative: bool = False) -> Optional[float]:
    """
    FIX: Erweiterte Float-Konvertierung mit Range-Validation.

    Änderungen:
    - Optional: erlaube negative Werte (für CADD etc.)
    - Strikte Validierung für AF-Werte
    """
    try:
        f = float(x)

        # NaN/Inf immer reject
        if math.isnan(f) or math.isinf(f):
            return None

        # Range-Check (nur wenn nicht explizit negativ erlaubt)
        if not allow_negative and f < 0.0:
            return None

        return f

    except (ValueError, TypeError):
        return None


def now_iso() -> str:
    """Gibt den aktuellen UTC‑Zeitpunkt als ISO‑String mit 'Z' zurück."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_utc(s: Optional[str]) -> Optional[datetime.datetime]:
    """
    Parst einen ISO‑Zeitstempel (ggf. mit 'Z') und gibt ein naive datetime in UTC zurück.
    Falls Parsing fehlschlägt, wird None geliefert.
    """
    if not s:
        return None
    try:
        if s.endswith("Z"):
            return (
                datetime.datetime.fromisoformat(s[:-1] + "+00:00")
                .astimezone(datetime.timezone.utc)
                .replace(tzinfo=None)
            )
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def determine_is_coding(consequence):
    if not consequence:
        return None
    cons = str(consequence).lower()
    coding_terms = [
        "missense", "stop_gained", "stop_lost", "synonymous",
        "frameshift", "inframe", "start_lost", "start_gained", "splice"
    ]
    return int(any(t in cons for t in coding_terms))


def safe_nested_get(data, *keys, default=None):
    """
    Sicheres navigieren durch verschachtelte Dictionaries.

    Args:
        data: Das Start-Dictionary
        *keys: Sequenz von Keys zum Navigieren
        default: Rückgabewert wenn Navigation fehlschlägt

    Returns:
        Wert am Ende des Pfads oder default

    Beispiel:
        safe_nested_get(data, "level1", "level2", "value", default="")
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current


class StopFlag:
    def __init__(self):
        self.ev = threading.Event()

    def stop(self):
        """Signalisiert Abbruch."""
        self.ev.set()

    def clear(self):
        """Reset für neuen Run."""
        self.ev.clear()

    def is_set(self):
        """Prüft, ob Abbruch signalisiert wurde."""
        return self.ev.is_set()
