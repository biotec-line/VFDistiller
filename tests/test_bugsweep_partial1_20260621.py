"""Regression tests — VFDistiller PARTIAL bugsweep 2026-06-21, BLOCK 1 (infra/config, Z. 1-4525).

Variant_Fusion_pro_V17.py is a 24082-LOC single-file GUI monolith whose import runs a
heavy bootstrap; the buggy sites (an embedded async gnomAD closure, the ResourceManager
singleton, a fasta-index helper) have no cheap unit seam. So these are STATIC SOURCE
ASSERTIONS over the module text — the pipeline's accepted approach when no runtime harness
fits. Behavioural non-regression is covered by the existing tests/ suite (49 green).

Red-on-revert: set VFD_SRC to the PRE-bugsweep backup copy → the three fix assertions fail.

  C1 gnomad_fetch_async: data.get("data", {}).get(...) crashed on JSON null
     ({"data": null}/genome=null) → AttributeError → silent allele-frequency loss.
  C2 load_fai_index: open without encoding + unguarded 5-tuple unpack on bad .fai line.
  B1 ResourceManager.get(absolute=False): relative branch skipped existence check +
     re-discovery (asymmetric with absolute=True).
"""
import os
import re
import unittest
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parent.parent / "Variant_Fusion_pro_V17.py"
SRC = Path(os.environ.get("VFD_SRC", str(_DEFAULT))).read_text(encoding="utf-8")


class C1_GnomadNullGuard(unittest.TestCase):
    def test_data_uses_or_idiom(self):
        self.assertIn('(data.get("data") or {}).get("variant")', SRC)

    def test_genome_exome_use_or_idiom(self):
        self.assertIn('(v.get("genome") or {}).get("af")', SRC)
        self.assertIn('(v.get("exome") or {}).get("af")', SRC)

    def test_old_crashing_pattern_gone(self):
        self.assertNotIn('data.get("data", {}).get("variant")', SRC)


class C2_FaiIndexHardening(unittest.TestCase):
    def test_open_has_encoding(self):
        self.assertIn('open(fai_path, "r", encoding="ascii")', SRC)

    def test_malformed_line_guard(self):
        self.assertRegex(SRC, r"parts = line\.strip\(\)\.split\(.\\t.\)\s*\n\s*if len\(parts\) != 5:")


class B1_ResourceManagerRelativeSymmetry(unittest.TestCase):
    def test_relative_branch_checks_existence(self):
        self.assertIn("os.path.join(BASE_DIR, rel)", SRC)

    def test_relative_branch_no_blind_return(self):
        # The old code returned self._paths.get(key) unconditionally in the else branch.
        self.assertNotRegex(SRC, r"else:\s*\n\s*return self\._paths\.get\(key\)\s*\n")


if __name__ == "__main__":
    unittest.main()
