"""Regressionstests — bugfix-library-transfer 2026-06-21."""
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
BUILD = ROOT / "build_release.py"
MANAGE_TRANS = ROOT / "manage_translations.py"
TRANSLATOR = ROOT / "translator.py"
V17 = ROOT / "Variant_Fusion_pro_V17.py"


class TestD3SubprocessTimeout(unittest.TestCase):
    """BUG-D3: subprocess.run ohne timeout= in build_release.py."""

    def test_pyinstaller_version_has_timeout(self):
        src = BUILD.read_text(encoding="utf-8")
        idx = src.find('"--version"')
        self.assertGreater(idx, 0, '"--version" nicht in build_release.py gefunden')
        snippet = src[max(0, idx - 50):idx + 200]
        self.assertIn(
            "timeout=",
            snippet,
            "build_release.py: subprocess.run --version ohne timeout= — BUG-D3",
        )


class TestU2JsonLoadHandlers(unittest.TestCase):
    """BUG-U2: json.load ohne JSONDecodeError-Handler."""

    def test_manage_translations_json_load_handler(self):
        src = MANAGE_TRANS.read_text(encoding="utf-8")
        idx = src.find("json.load(f)")
        self.assertGreater(idx, 0, "json.load(f) nicht in manage_translations.py gefunden")
        window = src[max(0, idx - 150):idx + 50]
        self.assertIn(
            "JSONDecodeError",
            window,
            "manage_translations: json.load ohne JSONDecodeError-Handler — BUG-U2",
        )

    def test_translator_json_load_handler(self):
        src = TRANSLATOR.read_text(encoding="utf-8")
        idx = src.find("json.load(f)")
        self.assertGreater(idx, 0, "json.load(f) nicht in translator.py gefunden")
        window = src[max(0, idx - 80):idx + 100]
        self.assertIn(
            "JSONDecodeError",
            window,
            "translator.py: json.load ohne JSONDecodeError-Handler — BUG-U2",
        )


class TestU3EncodingV17(unittest.TestCase):
    """BUG-U3: open() ohne encoding= bei Settings-JSON in Variant_Fusion_pro_V17.py."""

    def _src(self):
        return V17.read_text(encoding="utf-8")

    def test_config_file_load_has_encoding(self):
        src = self._src()
        self.assertIn(
            'open(self.CONFIG_FILE, "r", encoding="utf-8")',
            src,
            "V17: CONFIG_FILE load ohne encoding= — BUG-U3",
        )
        self.assertNotIn(
            'open(self.CONFIG_FILE, "r")',
            src,
            "V17: CONFIG_FILE load ohne encoding= noch vorhanden — BUG-U3",
        )

    def test_config_file_save_has_encoding(self):
        src = self._src()
        self.assertIn(
            'open(self.CONFIG_FILE, "w", encoding="utf-8")',
            src,
            "V17: CONFIG_FILE save ohne encoding= — BUG-U3",
        )

    def test_settings_file_load_has_encoding(self):
        src = self._src()
        self.assertNotIn(
            'open(Config.SETTINGS_FILE, "r")',
            src,
            "V17: SETTINGS_FILE load ohne encoding= — BUG-U3",
        )

    def test_settings_file_save_has_encoding(self):
        src = self._src()
        self.assertNotIn(
            'open(Config.SETTINGS_FILE, "w")',
            src,
            "V17: SETTINGS_FILE save ohne encoding= — BUG-U3",
        )


if __name__ == "__main__":
    unittest.main()
