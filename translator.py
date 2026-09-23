"""Internationalization (i18n) engine for VFDistiller (Tier-2 Policy P-006 standard).

Supported languages (6):
  - de (Deutsch - Default)
  - en (English)
  - es (Español)
  - zh (简体中文)
  - ja (日本語)
  - ru (Русский)

Deterministic 4-level fallback chain: target -> en -> de -> key.
"""
from __future__ import annotations

import json
import locale
import os
import sys
from typing import Any, Final

SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = ("de", "en", "es", "zh", "ja", "ru")
DEFAULT_LANGUAGE: Final[str] = "de"
FALLBACK_CHAIN: Final[tuple[str, ...]] = ("en", "de")

LANGUAGE_NAMES: Final[dict[str, str]] = {
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "zh": "简体中文",
    "ja": "日本語",
    "ru": "Русский",
}

LANGUAGE_DISPLAY_NAMES: Final[dict[str, str]] = {
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "zh": "中文 (简体)",
    "ja": "日本語",
    "ru": "Русский",
}


def normalize_language(lang: str | None) -> str:
    """Normalize language code to one of SUPPORTED_LANGUAGES or fallback to DEFAULT_LANGUAGE."""
    if not lang:
        return DEFAULT_LANGUAGE
    code = lang.lower().split("_")[0].split("-")[0]
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def detect_system_language() -> str:
    """Detect system language from environment or locale settings."""
    for env_var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(env_var)
        if val:
            code = normalize_language(val)
            if code in SUPPORTED_LANGUAGES:
                return code
    try:
        loc = locale.getlocale()[0]
        if loc:
            return normalize_language(loc)
    except Exception:
        pass
    return DEFAULT_LANGUAGE


class Translator:
    """Translation manager with 4-level deterministic fallback and format interpolation."""

    def __init__(self, lang: str = "de", file_path: str = "locales/translations.json") -> None:
        # PyInstaller One-File: Daten liegen in sys._MEIPASS
        if not os.path.isabs(file_path):
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base, file_path)

        self.file_path = file_path
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.translations: dict[str, dict[str, str]] = json.load(f)
        except (json.JSONDecodeError, OSError):
            self.translations = {}

        self.lang = normalize_language(lang)

    def set_lang(self, lang: str) -> None:
        """Set active language code."""
        self.lang = normalize_language(lang)

    def get_lang(self) -> str:
        """Return active language code."""
        return self.lang

    def available_keys(self) -> list[str]:
        """Return list of all translation keys in catalog."""
        return list(self.translations.keys())

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate key into active language with deterministic fallback and parameter interpolation."""
        entry = self.translations.get(key)
        if not entry:
            text = key
        else:
            text = (
                entry.get(self.lang)
                or entry.get("en")
                or entry.get("de")
                or key
            )

        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return text
        return text


# Module-level singleton instance
_GLOBAL_TRANSLATOR: Translator | None = None


def get_translator(lang: str | None = None, file_path: str = "locales/translations.json") -> Translator:
    """Return singleton Translator instance, creating it if needed."""
    global _GLOBAL_TRANSLATOR
    if _GLOBAL_TRANSLATOR is None:
        init_lang = lang if lang is not None else detect_system_language()
        _GLOBAL_TRANSLATOR = Translator(lang=init_lang, file_path=file_path)
    elif lang is not None:
        _GLOBAL_TRANSLATOR.set_lang(lang)
    return _GLOBAL_TRANSLATOR


def t(key: str, **kwargs: Any) -> str:
    """Translate string using global translator singleton."""
    return get_translator().t(key, **kwargs)


def set_language(lang: str) -> None:
    """Set global active language."""
    get_translator().set_lang(lang)


def get_language() -> str:
    """Get global active language."""
    return get_translator().get_lang()
