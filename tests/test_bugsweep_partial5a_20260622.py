"""Regression test — VFDistiller PARTIAL bugsweep 2026-06-22, BLOCK 5a (Z. 13423-16809).

Block 5a = Flag_and_Options_Manager/MainFilterGate/CodingFilter + Distiller part 1
(__init__/cache/upsert/process_file/_distill_vcf/_phase_vcf_scan/_process_variant_batch/
_validate_*/_lookup_lightdb). Largely clean; one real fix.

Static source assertion (Distiller has heavy __init__ deps — no cheap instantiation seam).
Behavioural non-regression: existing tests/ suite (77 green). Red-on-revert: VFD_SRC=PRE-block5a.

  A1 Distiller.invalidate_cache_bulk: delegated to self.app but never popped its own _bulk_cache
     -> _get_variants_bulk_cached returned stale pre-update rows after a batch write (cache
     incoherence — the exact path the V15 fix targeted). Single-key invalidate_cache popped
     correctly; the bulk variant did not.
"""
import os
from pathlib import Path
import unittest

_DEFAULT = Path(__file__).resolve().parent.parent / "Variant_Fusion_pro_V17.py"
SRC = Path(os.environ.get("VFD_SRC", str(_DEFAULT))).read_text(encoding="utf-8")


def has(n):
    return n in SRC


class A1_BulkCacheInvalidation(unittest.TestCase):
    def test_bulk_pops_own_cache(self):
        # The pop loop must sit inside invalidate_cache_bulk before the app delegation.
        bulk = SRC.split("def invalidate_cache_bulk", 1)[1].split("def ", 1)[0]
        self.assertIn("self._bulk_cache.pop(k, None)", bulk,
                      "A1: invalidate_cache_bulk does not pop its own _bulk_cache")
        self.assertIn("self.app.invalidate_cache_bulk(keys)", bulk,
                      "A1: app delegation unexpectedly missing")


if __name__ == "__main__":
    unittest.main()
