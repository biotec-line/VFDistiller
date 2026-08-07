"""Die Logdatei darf keine Variantenkennungen tragen — CodeQL #2/#3, 2026-08-06.

`MultiSinkLogger` schrieb jede Zeile wörtlich in `logfile_path`, also auch
`[Cache] rs1801133 @ hg38 → chr1:11796321`. Die Konsole darf das zeigen — dort
sitzt die Person, deren Genom das ist. Die Datei überlebt die Sitzung und geht
in Bugreports mit, deshalb wird sie redigiert.

Die Gegenprobe ist der wichtigere Teil dieser Tests: Ein Redaktionsmuster, das
Zähler, Prozentwerte oder Zeitstempel mitschwärzt, macht das Log unlesbar und
wird beim ersten Ärger wieder ausgebaut.
"""
import contextlib
import ast
import datetime
import io
import os
import queue
import tempfile
import unittest
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
V17 = ROOT / "Variant_Fusion_pro_V17.py"


def _load_logger_bits():
    """Holt Redactor und Logger, ohne das GUI-Modul komplett zu importieren.

    Variant_Fusion_pro_V17 zieht beim Import den ganzen Qt-/Netz-Stack nach; für
    eine reine Textfunktion wäre das eine unnötige Abhängigkeit im CI. Also wird
    der Funktionsblock aus der Quelle geschnitten und einzeln ausgeführt.
    """
    src = V17.read_text(encoding="utf-8")
    start = src.index("_LOGFILE_REDACTIONS = (")
    end = src.index("# LOGGER INITIALISIERUNG")
    namespace: dict = {}
    prelude = """
import datetime
import os
import queue
import re
import sys
import threading
from typing import Optional
LOG_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
"""
    exec(prelude + src[start:end], namespace)
    return (
        namespace["redact_for_logfile"],
        namespace["MultiSinkLogger"],
        namespace["log_private_safely"],
    )


def _load_conversion_harness(log_private_safely, temp_dir):
    """Führt die echten ``start``-/``create_vcf``-Methoden ohne GUI-Import aus."""
    tree = ast.parse(V17.read_text(encoding="utf-8"))
    converter = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "convert_23andme_to_vcf"
    )
    methods = [
        node
        for node in converter.body
        if isinstance(node, ast.FunctionDef) and node.name in {"start", "create_vcf"}
    ]
    harness = ast.ClassDef(
        name="ConversionHarness",
        bases=[],
        keywords=[],
        body=methods,
        decorator_list=[],
    )
    module = ast.fix_missing_locations(ast.Module(body=[harness], type_ignores=[]))
    namespace = {
        "Optional": Optional,
        "datetime": datetime,
        "does_fasta_exist": lambda build, logger=None: None,
        "load_fai_index": lambda path: None,
        "build_fasta_index_global": lambda path, logger: None,
        "log_private_safely": log_private_safely,
        "os": os,
        "TEMP_VCF_DIR": temp_dir,
    }
    exec(compile(module, str(V17), "exec"), namespace)
    return namespace["ConversionHarness"]


class TestLogfileRedaction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        redactor, logger_cls, private_log = _load_logger_bits()
        cls.redact = staticmethod(redactor)
        cls.logger_cls = logger_cls
        cls.private_log = staticmethod(private_log)

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
        self.assertIn("self._emit(line, line", block)
        # Die Konsolenausgabe im selben Block bleibt bewusst unredigiert.
        self.assertIn("def log_private", block)

    def test_private_log_keeps_session_detail_but_redacts_persistent_copy(self):
        """Sex und Eingabepfad dürfen den Sitzungsprozess nicht überleben."""
        full_msg = (
            "[23andMe→VCF] Starte Konvertierung: "
            "C:/Users/Alice/genome.txt, Build=GRCh37, Sex=female"
        )
        safe_msg = (
            "[23andMe→VCF] Starte Konvertierung: <Pfad redigiert>, "
            "Build=GRCh37, Sex=<redigiert>"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "variant-fusion.log"
            ui_queue = queue.Queue()
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                logger = self.logger_cls(str(logfile), ui_queue)
                logger.log_private(full_msg, safe_msg)

            self.assertIn("C:/Users/Alice/genome.txt", stdout.getvalue())
            self.assertIn("Sex=female", stdout.getvalue())
            self.assertIn("C:/Users/Alice/genome.txt", ui_queue.get_nowait())

            persisted = logfile.read_text(encoding="utf-8")
            self.assertNotIn("C:/Users/Alice/genome.txt", persisted)
            self.assertNotIn("Sex=female", persisted)
            self.assertIn("<Pfad redigiert>", persisted)
            self.assertIn("Sex=<redigiert>", persisted)

    def test_conversion_start_redacts_input_and_derived_output_paths(self):
        """Der echte Startpfad darf auch den abgeleiteten Dateinamen nicht speichern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            private_input = Path(tmpdir) / "Patient-Alice-genome.txt"
            private_input.write_text("# test\n", encoding="utf-8")
            logfile = Path(tmpdir) / "variant-fusion.log"
            ui_queue = queue.Queue()
            logger = self.logger_cls(str(logfile), ui_queue)
            conversion_cls = _load_conversion_harness(self.private_log, tmpdir)
            converter = conversion_cls()
            converter.file_path = str(private_input)
            converter.logger = logger
            converter.cache = {}
            converter.parse_23andme = lambda: []
            converter.is_rs_id = lambda value: False

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                out_vcf, out_build = converter.start("GRCh37", sex="female")

            persisted = logfile.read_text(encoding="utf-8")
            session_text = stdout.getvalue() + "\n".join(list(ui_queue.queue))
            self.assertEqual(out_build, "GRCh37")
            self.assertIn("Patient-Alice-genome", out_vcf)
            self.assertIn(str(private_input), session_text)
            self.assertIn("Sex=female", session_text)
            self.assertIn(out_vcf, session_text)
            self.assertNotIn(str(private_input), persisted)
            self.assertNotIn("Patient-Alice-genome", persisted)
            self.assertNotIn("Sex=female", persisted)
            self.assertNotIn(out_vcf, persisted)
            self.assertGreaterEqual(persisted.count("<Pfad redigiert>"), 3)

    def test_private_log_fallback_preserves_legacy_logger_contract(self):
        messages = []

        class LegacyLogger:
            def log(self, msg):
                messages.append(msg)

        self.private_log(
            LegacyLogger(),
            "private Patient-Alice-genome Sex=female",
            "safe <Pfad redigiert> Sex=<redigiert>",
        )
        self.assertEqual(messages, ["safe <Pfad redigiert> Sex=<redigiert>"])


if __name__ == "__main__":
    unittest.main()
