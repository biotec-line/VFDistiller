"""Regression tests — VFDistiller PARTIAL bugsweep 2026-06-22, BLOCK 5b (Z. 16809-19404).

Block 5b = Distiller part 2 (high-complexity streaming phases + file dispatch).
Static source assertions (no cheap unit seam in these threaded streaming phases).
Behavioural non-regression: existing tests/ suite (78 green). Red-on-revert: VFD_SRC=PRE-block5b.
assertTrue(needle in SRC, msg) so failures print a short message, not the 24k module.

  B3 (KRITISCH) Done-Event deadlock: _phase_alphagenome_streaming final wait used event.wait()
     with no timeout/stopflag; _phase_missing_fill_streaming left missing_done unset on stop
     (early return) and on an unguarded get_variants_bulk exception -> pipeline hung on normal Stop.
     Fix: set missing_done on stop-return; guard get_variants_bulk (retry); wait-loop with
     stopflag + timeout.
  B1 _filter_gvcf / B2 _process_fasta: `line.split("\t")[4]` IndexError on <5-column line -> guard.
  A1 _phase_full_annotation_streaming.flush_pending_writes: cleared buffer on DB error ->
     up to BATCH_WRITE_SIZE annotations silently lost (keys already in processed_keys). Retain on error.
"""
import os
from pathlib import Path
import unittest

_DEFAULT = Path(__file__).resolve().parent.parent / "Variant_Fusion_pro_V17.py"
SRC = Path(os.environ.get("VFD_SRC", str(_DEFAULT))).read_text(encoding="utf-8")


def has(n):
    return n in SRC


class B3_AlphaGenomeDeadlock(unittest.TestCase):
    def test_missing_done_set_on_stop(self):
        self.assertTrue(has("Deadlock auf dem normalen Stop-Pfad"), "B3a stop-return set missing")

    def test_get_variants_bulk_guarded(self):
        self.assertTrue(has("get_variants_bulk fehlgeschlagen, retry"), "B3b unguarded get_variants_bulk")

    def test_final_wait_has_stopflag_timeout(self):
        self.assertTrue(has("sonst Deadlock falls eine Phase ihr Event nie setzt"),
                        "B3c final wait still uses blocking event.wait()")


class B1B2_SplitIndexGuard(unittest.TestCase):
    def test_filter_gvcf_guarded(self):
        self.assertTrue(has('war wirkungslos (Iteration'), "B1 _filter_gvcf split[4] guard missing")

    def test_process_fasta_guarded(self):
        # B2 region got encoding= on both opens alongside the len(parts) guard.
        self.assertTrue(has('open(tmp_vcf, "r", encoding="utf-8") as fin'), "B2 _process_fasta guard missing")

    def test_guard_pattern_present(self):
        self.assertTrue(has('len(parts) > 4 and parts[4] != "."'), "split-guard pattern missing")


class A1_FullAnnoRetainOnError(unittest.TestCase):
    def test_buffer_retained_on_error(self):
        self.assertTrue(has("Buffer behalten, Retry): {e}"), "A1 retain-on-error marker missing")


if __name__ == "__main__":
    unittest.main()
