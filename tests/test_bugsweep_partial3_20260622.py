"""Regression tests — VFDistiller PARTIAL bugsweep 2026-06-22, BLOCK 3 (Z. 7306-10097).

Static source assertions (24082-LOC GUI monolith; sites in async closures / a SQLite
bulk-update / a GTF downloader — no cheap unit seam). Behavioural non-regression: existing
tests/ suite (63 green). Red-on-revert: set VFD_SRC to the PRE-block3 backup → fix asserts fail.
assertTrue(needle in SRC, msg) is used so failures print a short message, not the 24k module.

  A2 result_collector_and_merger: hit.get("gnomad",{}).get("exomes",{}) crashed on JSON null
     (gnomad/exomes/genomes = null) -> AttributeError, raised outside the try/except.
  B1 update_variant_fields_bulk: hardcoded SET ...conservation=? overwrote conservation with
     NULL on every annotation-cache flush (caller passes only gene_symbol/is_coding).
  A3 _ensure_gtf: requests.get(stream=True) without timeout -> hung GeneAnnotator init.
  A4 _flush_buffer: cleared the buffer in `finally` -> up to flush_size results silently
     dropped on a DB error; now cleared only on success.
"""
import os
from pathlib import Path
import unittest

_DEFAULT = Path(__file__).resolve().parent.parent / "Variant_Fusion_pro_V17.py"
SRC = Path(os.environ.get("VFD_SRC", str(_DEFAULT))).read_text(encoding="utf-8")


def has(n):
    return n in SRC


class A2_GnomadNullGuard(unittest.TestCase):
    def test_or_idiom(self):
        self.assertTrue(has('_gnomad = hit.get("gnomad") or {}'), "A2 fix missing")
        self.assertTrue(has('(_gnomad.get("exomes") or {}).get("af")'), "A2 exomes guard missing")

    def test_old_pattern_gone(self):
        self.assertFalse(has('hit.get("gnomad", {}).get("exomes", {})'), "A2 old null-crash present")


class B1_BulkUpdateDynamicSet(unittest.TestCase):
    def test_dynamic_set(self):
        self.assertTrue(has('sets = ", ".join([f"{field}=?" for field in data.keys()])'),
                        "B1 dynamic SET missing (note: also used by update_variant_fields)")

    def test_old_hardcoded_conservation_gone(self):
        self.assertFalse(has("SET gene_symbol=?, is_coding=?, conservation=?"),
                         "B1 hardcoded conservation-overwrite still present")


class A3_GtfDownloadTimeout(unittest.TestCase):
    def test_timeout_present(self):
        self.assertTrue(has("requests.get(url, stream=True, timeout=(10, 60))"), "A3 timeout missing")

    def test_old_no_timeout_gone(self):
        self.assertFalse(has("requests.get(url, stream=True)\n"), "A3 timeoutless call present")


class A4_FlushBufferClearOnSuccess(unittest.TestCase):
    def test_clear_not_in_finally(self):
        # The buffer must be retained on DB error (clear moved into the success path).
        self.assertTrue(has("Buffer behalten, Retry beim nächsten Flush"), "A4 fix marker missing")

    def test_old_finally_clear_gone(self):
        self.assertFalse(has("finally:\n            self.result_buffer.clear()"),
                         "A4 unconditional finally-clear still present")


if __name__ == "__main__":
    unittest.main()
