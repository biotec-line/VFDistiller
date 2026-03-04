import json

class Translator:
    def __init__(self, lang="de", file_path="locales/translations.json"):
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