"""Translation management and validation tool for VFDistiller (Policy P-006 Tier-2 standard).

Provides:
  - CLI translation catalog verification via `--check` flag (exit 0 for 100% parity, exit 1 for gaps).
  - Source scanner to discover new GUI strings in Python files.
  - Multi-language coverage checks for 6 Tier-2 languages: de, en, es, zh, ja, ru.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Configure UTF-8 stdout if available
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

TRANSLATION_FILE = "locales/translations.json"
SOURCE_DIR = "."  # durchsucht rekursiv alle .py-Dateien ab hier
LANGUAGES: tuple[str, ...] = ("de", "en", "es", "zh", "ja", "ru")

# Regex: Erkennung von text="..." in Tkinter-Widgets
STRING_PATTERN = re.compile(r'text\s*=\s*"([^"]+)"')

# Typische deutsche GUI-Wörter für Filter
GERMAN_HINTS = [
    "datei", "filter", "fehler", "laden", "speichern",
    "ansicht", "optionen", "zurück", "anzeigen", "export",
    "whitelist", "blacklist", "phase", "varianten", "schlüssel"
]


def find_german_strings(source_dir: str) -> set[str]:
    """Scan Python files for German GUI string literals."""
    german_strings = set()
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue
                for match in STRING_PATTERN.findall(content):
                    if any(ch in match for ch in "äöüÄÖÜß") or any(
                        w in match.lower() for w in GERMAN_HINTS
                    ):
                        german_strings.add(match.strip())
    return german_strings


def load_translations(file_path: str = TRANSLATION_FILE) -> dict[str, dict[str, str]]:
    """Load existing translation catalog with error resilience."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def check_translations(translations: dict[str, dict[str, str]]) -> int:
    """Validate 100% completeness across all 6 Tier-2 languages. Returns 0 on success, 1 on error."""
    if not translations:
        print("[ERROR] Translation catalog is empty or missing.")
        return 1

    total_keys = len(translations)
    missing_by_lang: dict[str, list[str]] = {lang: [] for lang in LANGUAGES}

    for key, entry in translations.items():
        if not isinstance(entry, dict):
            for lang in LANGUAGES:
                missing_by_lang[lang].append(key)
            continue
        for lang in LANGUAGES:
            val = entry.get(lang)
            if not val or not str(val).strip():
                missing_by_lang[lang].append(key)

    has_errors = any(len(miss) > 0 for miss in missing_by_lang.values())

    if has_errors:
        print(f"[FAIL] Tier-2 translation validation failed across {total_keys} keys:")
        for lang, missing_keys in missing_by_lang.items():
            if missing_keys:
                print(f"  - Language '{lang}': {len(missing_keys)} missing or empty keys (e.g. {missing_keys[:3]})")
        return 1

    print(f"[OK] 100% translation coverage achieved across {total_keys} keys for all 6 languages: {', '.join(LANGUAGES)}.")
    return 0


def manage_translations() -> None:
    """Synchronize source strings with translation catalog and report gaps."""
    translations = load_translations(TRANSLATION_FILE)
    found = find_german_strings(SOURCE_DIR)

    added = []
    for s in sorted(found):
        if s not in translations:
            translations[s] = {lang: (s if lang == "de" else "") for lang in LANGUAGES}
            added.append(s)

    os.makedirs(os.path.dirname(TRANSLATION_FILE), exist_ok=True)
    with open(TRANSLATION_FILE, "w", encoding="utf-8") as f:
        json.dump(translations, f, indent=2, ensure_ascii=False)

    if added:
        print("[INFO] New translation keys added:")
        for s in added:
            print(" -", s)
    else:
        print("[INFO] No new German source strings found.")

    for lang in LANGUAGES:
        missing = [k for k, v in translations.items() if not v.get(lang)]
        if missing:
            print(f"[WARN] Missing translations for '{lang}': {len(missing)} keys")
        else:
            print(f"[OK] All keys have valid '{lang}' translations.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage and validate VFDistiller translations.")
    parser.add_argument("--check", action="store_true", help="Validate 100% translation parity across all 6 languages.")
    args = parser.parse_args()

    if args.check:
        translations = load_translations(TRANSLATION_FILE)
        code = check_translations(translations)
        sys.exit(code)
    else:
        manage_translations()


if __name__ == "__main__":
    main()
