"""Regression tests — VFDistiller PARTIAL bugsweep 2026-06-22, BLOCK 4 (Z. 10097-13423).

Static source assertions (24082-LOC GUI monolith; sites in a multiprocessing logger, a
background-thread dialog, a FASTA validator — no cheap unit seam). Behavioural non-regression:
existing tests/ suite (71 green). Red-on-revert: set VFD_SRC to the PRE-block4 backup → asserts fail.
assertTrue(needle in SRC, msg) so failures print a short message, not the 24k module.

  B1 FastaValidator._get_reference_base: `if self._fasta_index is None` was dead (init={} -> never
     None) -> lazy FAI-load never fired -> mode-2 validation saw an empty index -> every variant
     failed lookup. Fix: `if not self._fasta_index:`.
  B3 does_user_want_to_use_fasta: opened a tk messagebox from a background thread when app was None
     (tk not thread-safe). Fix: return None instead of a thread dialog.
  A1 MultiSinkLogger: passed across a multiprocessing.Process boundary; threading.Lock + ui_queue
     are unpicklable -> migrator.start() raised TypeError (swallowed) -> migration never ran.
     Fix: __getstate__/__setstate__ drop _lock + q on pickle, recreate _lock on unpickle.
"""
import os
from pathlib import Path
import unittest

_DEFAULT = Path(__file__).resolve().parent.parent / "Variant_Fusion_pro_V17.py"
SRC = Path(os.environ.get("VFD_SRC", str(_DEFAULT))).read_text(encoding="utf-8")


def has(n):
    return n in SRC


class B1_FastaIndexLazyLoad(unittest.TestCase):
    def test_truthiness_check(self):
        self.assertTrue(has("if not self._fasta_index: self._load_fasta_index()"), "B1 fix missing")

    def test_old_is_none_gone(self):
        self.assertFalse(has("if self._fasta_index is None: self._load_fasta_index()"),
                         "B1 dead is-None check still present")


class B3_NoThreadDialog(unittest.TestCase):
    def test_returns_none_without_app(self):
        self.assertTrue(has("kein Thread-Dialog"), "B3 fix marker missing")

    def test_old_unsafe_fallback_gone(self):
        self.assertFalse(has("# Fallback (unsicher, aber besser als Crash)\n        decision = ask_dialog()"),
                         "B3 unsafe thread dialog still present")


class A1_LoggerPicklable(unittest.TestCase):
    def test_getstate_drops_unpicklable(self):
        self.assertTrue(has("def __getstate__(self):"), "A1 __getstate__ missing")
        self.assertTrue(has('state["_lock"] = None'), "A1 lock-drop missing")
        self.assertTrue(has('state["q"] = None'), "A1 queue-drop missing")

    def test_setstate_recreates_lock(self):
        self.assertTrue(has("def __setstate__(self, state):"), "A1 __setstate__ missing")
        self.assertTrue(has("self._lock = threading.Lock()"), "A1 lock-recreate missing")


if __name__ == "__main__":
    unittest.main()
