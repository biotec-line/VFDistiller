"""Regression tests — VFDistiller PARTIAL bugsweep 2026-06-22, BLOCK 6b (Z. 22581-Ende).

Block 6b = App apply_post_filter + export_* + settings + GUI build. Static source assertions.
Behavioural non-regression: existing tests/ suite (94 green). Red-on-revert: VFD_SRC=PRE-block6b.

Applied fixes (non-logic, safe):
  E1 export_complete_vcf_optimized: passed ungeguarded self.distiller.build to the reference
     header -> "##reference=None" if build is None. Fix: use current_build (GRCh37 fallback).
  B1 _load_settings: column_links taken by reference without type/schema guard or merge ->
     AttributeError later on schema drift + default-link loss. Fix: guarded merge.
  A4 _enrich_vcf_line: db_rsid.startswith without isinstance -> AttributeError on non-str rsid.

DOCUMENTED, NOT changed (clinical/display-filter logic — Maintainer decision, per Lukas'
explicit caution that this logic was historically mis-flagged):
  A1 QualityManager.passes — qual_threshold gate inert (review note in code).
  A2 apply_post_filter/visible — clin_sig substring classification ambiguity (review note in code).
"""
import os
from pathlib import Path
import unittest

_DEFAULT = Path(__file__).resolve().parent.parent / "Variant_Fusion_pro_V17.py"
SRC = Path(os.environ.get("VFD_SRC", str(_DEFAULT))).read_text(encoding="utf-8")


def has(n):
    return n in SRC


class E1_CompleteExportReferenceBuild(unittest.TestCase):
    def test_uses_current_build(self):
        self.assertTrue(has("self._check_and_add_reference_header(outfile, original_vcf, current_build)"),
                        "E1 fix missing")

    def test_old_unguarded_build_gone(self):
        self.assertFalse(has("self._check_and_add_reference_header(outfile, original_vcf, self.distiller.build)"),
                         "E1 unguarded self.distiller.build still present")


class B1_ColumnLinksGuard(unittest.TestCase):
    def test_isinstance_guard(self):
        self.assertTrue(has('if isinstance(data.get("column_links"), dict):'), "B1 type guard missing")

    def test_old_blind_assign_gone(self):
        self.assertFalse(has('self.column_links = data["column_links"]'), "B1 blind assign still present")


class A4_RsidTypeGuard(unittest.TestCase):
    def test_isinstance(self):
        self.assertTrue(has('if isinstance(db_rsid, str) and db_rsid.startswith("rs")'), "A4 guard missing")


class ReviewNotesDocumented(unittest.TestCase):
    def test_two_review_notes_present(self):
        # A1 (passes) + A2 (clin_sig) documented in-code, not auto-fixed.
        self.assertGreaterEqual(SRC.count("REVIEW-NOTIZ (Bugsweep 2026-06-22"), 2,
                                "A1/A2 review notes missing")

    def test_passes_logic_unchanged(self):
        # The deferred passes() gate must remain as-is (no premature fix).
        self.assertTrue(has("if not has_pass and not has_qual:"), "passes() gate unexpectedly changed")


if __name__ == "__main__":
    unittest.main()
