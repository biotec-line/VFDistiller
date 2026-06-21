"""Regression tests — VFDistiller PARTIAL bugsweep 2026-06-21, BLOCK 2 (Z. 4525-7306).

Static source assertions (24082-LOC GUI monolith; buggy sites in an async closure / a
parallel-fetch method / an external-worker launcher — no cheap unit seam). Behavioural
non-regression: existing tests/ suite (56 green). Red-on-revert: set VFD_SRC to the
PRE-block2 backup → the fix assertions fail.

Assertions use `assertTrue(needle in SRC, msg)` (NOT assertIn/assertNotIn) so a failure
prints a short message, not the entire 24k-char module.

  A1 create_vcf: `ref_seq, alt_seq = indel_ref_alt_from_spdi(...)` unpacked a possibly-None
     return (invalid anchor base) -> TypeError aborted VCF generation.
  A2 detect_build_robust_by_rsids: cache read with tuple keys (rsid, build) never matched
     the string-keyed {"assemblies": {build: ...}} structure -> build detection inert.
  A3 detect_build_robust_by_rsids: parallel fetch persisted to self.cache_file (==CACHE_FILE),
     clobbering the persistent rsID cache with the ~50-entry detect dict.
  B1 start_index_worker: os.kill(pid, 0) TERMINATES the process on Windows -> killed the
     running index worker; replaced with psutil.pid_exists + ProcessLookupError.
     (Note: the os.kill(pid,0) at ~L10581 is a CORRECT non-Windows branch and stays.)
"""
import os
from pathlib import Path
import unittest

_DEFAULT = Path(__file__).resolve().parent.parent / "Variant_Fusion_pro_V17.py"
SRC = Path(os.environ.get("VFD_SRC", str(_DEFAULT))).read_text(encoding="utf-8")


def has(needle):
    return needle in SRC


class A1_SpdiNoneGuard(unittest.TestCase):
    def test_guarded_unpack(self):
        self.assertTrue(has("if not _spdi:"), "A1 guard missing")
        self.assertTrue(has("ref_seq, alt_seq = _spdi"), "A1 guarded unpack missing")

    def test_old_blind_unpack_gone(self):
        self.assertFalse(has("ref_seq, alt_seq = indel_ref_alt_from_spdi("),
                         "A1 old blind unpack still present")


class A2_BuildCheckCacheKeys(unittest.TestCase):
    def test_reads_string_keyed_structure(self):
        self.assertTrue(has('cache.get(rsid, {}).get("assemblies")'), "A2 fix missing")

    def test_old_tuple_key_lookup_gone(self):
        self.assertFalse(has('cache.get((rsid, "GRCh37"))'), "A2 old tuple-key lookup present")


class A3_BuildCheckCacheNoClobber(unittest.TestCase):
    def test_redirects_cache_file_during_detection(self):
        self.assertTrue(has("self.cache_file = _tmp_cache"), "A3 redirect missing")
        self.assertTrue(has("self.cache_file = _orig_cache_file"), "A3 restore missing")

    def test_tempfile_imported(self):
        self.assertTrue(has("\nimport tempfile\n"), "tempfile import missing")


class B1_IndexWorkerPidCheck(unittest.TestCase):
    def test_uses_psutil_and_processlookuperror(self):
        # ProcessLookupError(pid) is unique to this fix -> the red-on-revert discriminator
        # (psutil.pid_exists alone also appears elsewhere in the file).
        self.assertTrue(has("raise ProcessLookupError(pid)"), "B1 fix missing")
        self.assertTrue(has("psutil.pid_exists(pid)"), "B1 psutil check missing")


if __name__ == "__main__":
    unittest.main()
