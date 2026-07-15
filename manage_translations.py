import json
import re
import os

TRANSLATION_FILE = "locales/translations.json"
SOURCE_DIR = "."  # durchsucht rekursiv alle .py-Dateien ab hier

# Regex: einfache Erkennung von text="..." in Tkinter-Widgets
STRING_PATTERN = re.compile(r'text\s*=\s*"([^"]+)"')

# Typische deutsche GUI-Wörter für Filter
GERMAN_HINTS = [
    "datei", "filter", "fehler", "laden", "speichern",
    "ansicht", "optionen", "zurück", "anzeigen", "export",
    "whitelist", "blacklist", "phase", "varianten", "schlüssel"
]

def find_german_strings(source_dir):
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

def manage_translations():
    # Bestehende Übersetzungen laden
    if os.path.exists(TRANSLATION_FILE):
        with open(TRANSLATION_FILE, "r", encoding="utf-8") as f:
            translations = json.load(f)
    else:
        translations = {}

    # Neue Strings finden
    found = find_german_strings(SOURCE_DIR)

    added = []
    for s in sorted(found):
        if s not in translations:
            translations[s] = {"de": s, "en": ""}
            added.append(s)

    # Datei aktualisieren
    os.makedirs(os.path.dirname(TRANSLATION_FILE), exist_ok=True)
    with open(TRANSLATION_FILE, "w", encoding="utf-8") as f:
        json.dump(translations, f, indent=2, ensure_ascii=False)

    # Report
    if added:
        print("✅ Neue Einträge hinzugefügt:")
        for s in added:
            print(" -", s)
    else:
        print("ℹ️ Keine neuen deutschen Strings gefunden.")

    # Fehlende Übersetzungen prüfen
    missing = [k for k, v in translations.items() if not v.get("en")]
    if missing:
        print("\n⚠️ Fehlende englische Übersetzungen für:")
        for k in missing:
            print(" -", k)
    else:
        print("\n✅ Alle Keys haben englische Übersetzungen.")

if __name__ == "__main__":
    manage_translations()