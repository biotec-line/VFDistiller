"""Die Logdatei darf keine Variantenkennungen tragen — CodeQL #2/#3, 2026-08-06.

`MultiSinkLogger` schrieb jede Zeile wörtlich in `logfile_path`, also auch
`[Cache] rs1801133 @ hg38 → chr1:11796321`. Die Konsole darf das zeigen — dort
sitzt die Person, deren Genom das ist. Die Datei überlebt die Sitzung und geht
in Bugreports mit, deshalb wird sie redigiert.

Die Gegenprobe ist der wichtigere Teil dieser Tests: Ein Redaktionsmuster, das
Zähler, Prozentwerte oder Zeitstempel mitschwärzt, macht das Log unlesbar und
wird beim ersten Ärger wieder ausgebaut.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
V17 = ROOT / "Variant_Fusion_pro_V17.py"


def _load_redactor():
    """Holt `redact_for_logfile`, ohne das GUI-Modul komplett zu importieren.

    Variant_Fusion_pro_V17 zieht beim Import den ganzen Qt-/Netz-Stack nach; für
    eine reine Textfunktion wäre das eine unnötige Abhängigkeit im CI. Also wird
    der Funktionsblock aus der Quelle geschnitten und einzeln ausgeführt.
    """
    src = V17.read_text(encoding="utf-8")
    start = src.index("_LOGFILE_REDACTIONS = (")
    end = src.index("class MultiSinkLogger:")
    namespace: dict = {}
    exec("import re\n" + src[start:end], namespace)
    return namespace["redact_for_logfile"]


class TestLogfileRedaction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.redact = staticmethod(_load_redactor())

    def test_rsids_and_loci_are_removed(self):
        for line in (
            "[2026-08-06 00:20:15] [Cache] rs1801133 @ hg38 -> chr1:11796321 C",
            "[ALFA] HTTP 429 for rs429358",
            "[dbSNP] rs7412: keine Daten erhalten",
            "[BuildDetect] 1:230710048 gefunden",
            "[AF] chrX:154360000 verarbeitet",
        ):
            with self.subTest(line=line):
                out = self.redact(line)
                self.assertNotIn("rs1801133", out)
                self.assertNotRegex(out, r"\brs\d{2,}\b")
                self.assertNotRegex(out, r"\b(?:chr)?(?:[0-9]{1,2}|[XYM]|MT):\d{3,}\b")

    def test_ordinary_log_lines_survive_untouched(self):
        """Gegenprobe: Was kein Genom ist, bleibt lesbar."""
        for line in (
            "[2026-08-06 00:20:15] [AF-Streaming] VCF-Scan complete",
            "[BuildCheck] geprueft: 1234 rsIDs -> m37=812, m38=99",
            "[GeneAnnotator] Index hg38: 24 Chromosomen, 19821 Gene",
            "[Logger] Fortschritt 45% in 12:34:56",
            "C:/Users/User/data/export.vcf geschrieben",
        ):
            with self.subTest(line=line):
                self.assertEqual(self.redact(line), line)

    def test_logger_writes_through_the_redactor(self):
        """Die Verdrahtung, nicht nur das Muster: der Datei-Write muss sie nutzen."""
        src = V17.read_text(encoding="utf-8")
        # Gezielt die Methode von MultiSinkLogger — _NullLogger definiert weiter
        # oben ein gleichnamiges log() ohne Datei-Sink.
        cls_idx = src.index("class MultiSinkLogger:")
        idx = src.index("def log(self, msg: str", cls_idx)
        block = src[idx:idx + 1600]
        self.assertIn("redact_for_logfile(line)", block)
        # Die Konsolenausgabe im selben Block bleibt bewusst unredigiert.
        self.assertIn("print(line)", block)


if __name__ == "__main__":
    unittest.main()
