"""Contract and parity tests for VFDistiller Internationalization (Tier-2 Policy P-006).

Validates:
  - 100% 6-language parity across DE, EN, ES, ZH, JA, RU.
  - Deterministic 4-level fallback chain: target -> en -> de -> key.
  - Translator singleton and helper functions.
  - Language detection and normalization.
  - String formatting interpolation with kwargs.
  - UTF-8 and German umlaut integrity.
  - CLI validation via manage_translations.py --check.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from translator import (
    DEFAULT_LANGUAGE,
    FALLBACK_CHAIN,
    LANGUAGE_DISPLAY_NAMES,
    LANGUAGE_NAMES,
    SUPPORTED_LANGUAGES,
    Translator,
    detect_system_language,
    get_language,
    get_translator,
    normalize_language,
    set_language,
    t,
)
from manage_translations import check_translations, load_translations

ROOT_DIR = Path(__file__).resolve().parent.parent
TRANSLATIONS_FILE = ROOT_DIR / "locales" / "translations.json"


def test_supported_languages_constants():
    """Verify Tier-2 6-language constants and mappings."""
    expected = ("de", "en", "es", "zh", "ja", "ru")
    assert SUPPORTED_LANGUAGES == expected
    assert DEFAULT_LANGUAGE == "de"
    assert FALLBACK_CHAIN == ("en", "de")

    for lang in expected:
        assert lang in LANGUAGE_NAMES
        assert lang in LANGUAGE_DISPLAY_NAMES
        assert LANGUAGE_NAMES[lang].strip()
        assert LANGUAGE_DISPLAY_NAMES[lang].strip()


def test_translations_catalog_full_parity_six_languages():
    """Verify that all keys in locales/translations.json have 100% non-empty coverage across all 6 languages."""
    assert TRANSLATIONS_FILE.exists(), f"Missing {TRANSLATIONS_FILE}"

    with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    assert len(catalog) >= 150, f"Expected at least 150 translation keys, found {len(catalog)}"

    missing_items = []
    for key, entry in catalog.items():
        assert isinstance(entry, dict), f"Key '{key}' entry must be a dictionary"
        for lang in SUPPORTED_LANGUAGES:
            val = entry.get(lang)
            if not val or not str(val).strip():
                missing_items.append((key, lang))

    assert not missing_items, f"Found {len(missing_items)} missing/empty translations: {missing_items[:10]}"


def test_translator_fallback_chain(tmp_path):
    """Verify 4-tier fallback: target -> en -> de -> key."""
    mock_translations = {
        "full_key": {
            "de": "Voll Deutsch",
            "en": "Full English",
            "es": "Lleno Español",
            "zh": "完整中文",
            "ja": "完全日本語",
            "ru": "Полный Русский",
        },
        "no_es_key": {
            "de": "Nur DE und EN",
            "en": "Only DE and EN",
        },
        "only_de_key": {
            "de": "Nur DE",
        },
    }
    dummy_file = tmp_path / "translations.json"
    dummy_file.write_text(json.dumps(mock_translations, ensure_ascii=False), encoding="utf-8")

    tr = Translator(lang="es", file_path=str(dummy_file))
    # Target language present
    assert tr.t("full_key") == "Lleno Español"

    # Missing in ES -> falls back to EN
    assert tr.t("no_es_key") == "Only DE and EN"

    # Missing in ES and EN -> falls back to DE
    assert tr.t("only_de_key") == "Nur DE"

    # Completely non-existent key -> returns key itself
    assert tr.t("completely_unknown_key") == "completely_unknown_key"


def test_translator_string_interpolation():
    """Verify kwargs string interpolation with graceful failure handling."""
    tr = Translator(lang="en", file_path=str(TRANSLATIONS_FILE))

    # Existing placeholder key in catalog
    key = "Platzhalter: {value}, {chr}, {pos}, {ref}, {alt}, {gene}, {rsid}"
    res = tr.t(key, value="VAL", chr="chr1", pos="100", ref="A", alt="G", gene="TP53", rsid="rs123")
    assert "VAL" in res and "chr1" in res and "TP53" in res

    # Unknown key with format kwargs
    custom = tr.t("Welcome, {user}!", user="Lukas")
    assert custom == "Welcome, Lukas!"

    # Format mismatch / missing kwargs should not crash
    safe = tr.t("Welcome, {missing}!")
    assert safe == "Welcome, {missing}!"


def test_translator_singleton_and_helpers():
    """Verify singleton get_translator, set_language, get_language, t()."""
    inst = get_translator()
    assert isinstance(inst, Translator)

    set_language("ja")
    assert get_language() == "ja"
    assert t("Abbrechen") == "キャンセル"

    set_language("es")
    assert get_language() == "es"
    assert t("Abbrechen") == "Cancelar"

    set_language("zh")
    assert get_language() == "zh"
    assert t("Abbrechen") == "取消"

    set_language("ru")
    assert get_language() == "ru"
    assert t("Abbrechen") == "Отмена"

    # Reset back to de
    set_language("de")
    assert get_language() == "de"
    assert t("Abbrechen") == "Abbrechen"


def test_normalize_language():
    """Verify language code normalization and fallbacks."""
    assert normalize_language("de_DE") == "de"
    assert normalize_language("en-US") == "en"
    assert normalize_language("ES_es") == "es"
    assert normalize_language("zh-CN") == "zh"
    assert normalize_language("ja_JP") == "ja"
    assert normalize_language("ru_RU") == "ru"
    assert normalize_language("fr_FR") == "de"
    assert normalize_language(None) == "de"
    assert normalize_language("") == "de"


def test_detect_system_language(monkeypatch):
    """Verify system language detection via environment variables."""
    monkeypatch.setenv("LANG", "es_ES.UTF-8")
    assert detect_system_language() == "es"

    monkeypatch.setenv("LANG", "zh_CN.UTF-8")
    assert detect_system_language() == "zh"

    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    assert detect_system_language() == "de"


def test_manage_translations_check_in_process():
    """Verify in-process check_translations function."""
    catalog = load_translations(str(TRANSLATIONS_FILE))
    assert check_translations(catalog) == 0


def test_manage_translations_cli_subprocess():
    """Verify manage_translations.py --check via CLI."""
    res = subprocess.run(
        [sys.executable, "manage_translations.py", "--check"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res.returncode == 0, f"manage_translations.py --check failed: {res.stderr} {res.stdout}"
    assert "100% translation coverage achieved" in res.stdout


def test_german_umlauts_and_utf8_integrity():
    """Verify German umlauts and international script characters are uncorrupted."""
    tr = Translator(lang="de", file_path=str(TRANSLATIONS_FILE))
    assert tr.t("Schließen") == "Schließen"
    assert tr.t("Übernehmen") == "Übernehmen"
    assert "für" in tr.t("Hinweis: AlphaMissense Scores werden nur für gefilterte Varianten abgerufen.")

    tr.set_lang("ru")
    assert tr.t("Schließen") == "Закрыть"

    tr.set_lang("zh")
    assert tr.t("Schließen") == "关闭"

    tr.set_lang("ja")
    assert tr.t("Schließen") == "閉じる"


def test_spanish_readme_18_point_navigation_parity():
    """Verify README.es.md exists and has all 18 navigation points."""
    readme_es = ROOT_DIR / "README.es.md"
    assert readme_es.exists(), "README.es.md must exist in repository root"
    content = readme_es.read_text(encoding="utf-8")
    for point in range(1, 19):
        assert f"(#{point}-" in content, f"README.es.md missing navigation link for section #{point}"
        assert f'id="{point}-' in content, f"README.es.md missing anchor id for section #{point}"


def test_v17_source_language_menu_and_persistence():
    """Verify V17 GUI source exposes all 6 languages and persists language in settings."""
    v17_path = ROOT_DIR / "Variant_Fusion_pro_V17.py"
    assert v17_path.exists()
    src = v17_path.read_text(encoding="utf-8")
    for code, label in [
        ("de", "Deutsch"),
        ("en", "English"),
        ("es", "Español"),
        ("zh", "简体中文"),
        ("ja", "日本語"),
        ("ru", "Русский"),
    ]:
        assert f'("{code}", "{label}")' in src or f"('{code}', '{label}')" in src
    assert 'self._save_settings()' in src
    assert 'data["language"] = self.translator.get_lang()' in src
    assert 'saved_lang = data.get("language")' in src

