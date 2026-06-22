"""Regression tests — VFDistiller PARTIAL bugsweep 2026-06-22, BLOCK 6a (Z. 19499-22537).

Block 6a = QualityManager/QualitySettingsDialog/ResourceSetupDialog + App part 1 (GUI core,
table/row, threading, on_close, on_start). Static source assertions (ttkbootstrap GUI / threading;
no cheap unit seam). Behavioural non-regression: existing tests/ suite (85 green). Red-on-revert:
VFD_SRC=PRE-block6a. assertTrue(needle in SRC, msg) -> short failure messages.

NOTE: A1 (QualityManager.passes — qual_threshold gate inert because has_pass is always True at
the gate) is DEFERRED, not fixed: every fix changes which variants clear a clinical filter
(independent QUAL gate vs OR-rescue). Surfaced to the user for a one-word decision. Not covered here.

  A2 _build_single_resource_card: download lambda referenced out-of-scope `_t` -> NameError on
     download click. Fix: thread `_t` through (param + caller passes it).
  B1 _fetch_row_async/eviction: rows_cache mutated from worker thread without _table_lock -> race.
  B3 on_close: no reentrancy guard -> double close (2nd crawler thread + 2nd destroy).
  B5 _refresh_progress: delayed after(2000) lambdas without winfo_exists -> TclError on close.
  B8 on_start: unreliable text-heuristic double-start protection -> _starting guard flag.
  B10 _on_start_continue: float/int casts on entry vars without try -> ValueError aborted start;
      guard + _starting reset on every exit path (no permanent lock-out).
"""
import os
from pathlib import Path
import unittest

_DEFAULT = Path(__file__).resolve().parent.parent / "Variant_Fusion_pro_V17.py"
SRC = Path(os.environ.get("VFD_SRC", str(_DEFAULT))).read_text(encoding="utf-8")


def has(n):
    return n in SRC


class A2_ResourceCardTranslator(unittest.TestCase):
    def test_param_added(self):
        self.assertTrue(has("def _build_single_resource_card(parent, key, info, is_ok, rm, logger_inst, card_widgets, _t=None):"),
                        "A2 _t param missing")

    def test_caller_passes_t(self):
        self.assertTrue(has("rm, logger_inst, card_widgets, _t=_t)"), "A2 caller does not pass _t")


class B1_RowsCacheLock(unittest.TestCase):
    def test_worker_write_locked(self):
        self.assertTrue(has("Worker-Thread-Schreibzugriff auf rows_cache unter _table_lock"),
                        "B1 worker-write lock missing")

    def test_eviction_locked(self):
        self.assertTrue(has("Eviction (next(iter)/del) ohne Lock"), "B1 eviction lock comment missing")
        # the with-lock must wrap the eviction for-loop
        seg = SRC.split("Eviction (next(iter)/del) ohne Lock", 1)[1][:200]
        self.assertIn("with self._table_lock:", seg, "B1 eviction not under lock")


class B3_OnCloseReentrancy(unittest.TestCase):
    def test_closing_guard(self):
        self.assertTrue(has('if getattr(self, "_closing", False):'), "B3 reentrancy guard missing")
        self.assertTrue(has("self._closing = True"), "B3 closing flag set missing")


class B5_ProgressLambdaGuard(unittest.TestCase):
    def test_winfo_guard_on_delayed_lambdas(self):
        self.assertTrue(has("self.winfo_exists() and self.progress_bar.configure(value=0)"),
                        "B5 winfo_exists guard missing")


class B8B10_StartGuard(unittest.TestCase):
    def test_starting_guard_in_on_start(self):
        self.assertTrue(has('if getattr(self, "_starting", False):'), "B8 _starting guard missing")
        self.assertTrue(has("self._starting = True"), "B8 _starting set missing")

    def test_kwargs_validation(self):
        self.assertTrue(has('Ungültiger Filterwert'), "B10 kwargs validation/messagebox missing")

    def test_starting_reset_on_all_exits(self):
        # at least: validation-error return, no-file return, normal end
        self.assertGreaterEqual(SRC.count("self._starting = False"), 3,
                                "B10/B8 _starting not reset on all exit paths")


if __name__ == "__main__":
    unittest.main()
