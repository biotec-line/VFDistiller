import json
import os
import sys

class Translator:
    def __init__(self, lang="de", file_path="locales/translations.json"):
        # PyInstaller One-File: Daten liegen in sys._MEIPASS
        if not os.path.isabs(file_path):
            base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base, file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            self.translations = json.load(f)
        self.lang = lang

    def set_lang(self, lang):
        self.lang = lang

    def t(self, key: str) -> str:
        entry = self.translations.get(key)
        if not entry:
            return key
        return entry.get(self.lang, entry.get("de", key))