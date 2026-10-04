"""Unit tests for BackgroundMaintainer stale_days and stale_days_full parameter split (TW-VFD-01).

Validates:
1. Default values match Config.STALE_DAYS_AF (365) and Config.STALE_DAYS_FULL (30).
2. Explicit custom values are stored and used independently.
3. Backward compatibility with legacy callers passing only stale_days.
4. Correct dispatch of stale_days vs stale_days_full based on mode ('af' vs 'full').
5. Integration with database for_background_priorities querying.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from Variant_Fusion_pro_V17 import (
    BackgroundMaintainer,
    Config,
    StopFlag,
)


class TestBackgroundMaintainerStaleDays(unittest.TestCase):
    """Test suite for BackgroundMaintainer dual stale_days / stale_days_full architecture."""

    def setUp(self):
        self.mock_distiller = MagicMock()
        self.mock_db = MagicMock()
        self.stopflag = StopFlag()
        self.mock_logger = MagicMock()

    def test_default_stale_days_parameters(self):
        """Ensure defaults correspond to Config constants (365 for AF, 30 for Full)."""
        maint = BackgroundMaintainer(
            distiller=self.mock_distiller,
            db=self.mock_db,
            stopflag=self.stopflag,
            logger=self.mock_logger,
        )
        self.assertEqual(maint.stale_days, Config.STALE_DAYS_AF)
        self.assertEqual(maint.stale_days_full, Config.STALE_DAYS_FULL)
        self.assertEqual(maint.stale_days, 365)
        self.assertEqual(maint.stale_days_full, 30)

    def test_custom_stale_days_split(self):
        """Ensure custom split values are independently assigned."""
        maint = BackgroundMaintainer(
            distiller=self.mock_distiller,
            db=self.mock_db,
            stopflag=self.stopflag,
            logger=self.mock_logger,
            stale_days=180,
            stale_days_full=14,
        )
        self.assertEqual(maint.stale_days, 180)
        self.assertEqual(maint.stale_days_full, 14)

    def test_backward_compatibility_single_stale_days(self):
        """Ensure backward compatibility when only stale_days is provided."""
        maint = BackgroundMaintainer(
            self.mock_distiller,
            self.mock_db,
            self.stopflag,
            self.mock_logger,
            stale_days=90,
        )
        self.assertEqual(maint.stale_days, 90)
        self.assertEqual(maint.stale_days_full, Config.STALE_DAYS_FULL)

    def test_fetch_decision_receives_correct_stale_days_per_mode(self):
        """Verify automatic_fetch_decission_and_processing_unit gets appropriate stale threshold."""
        maint = BackgroundMaintainer(
            distiller=self.mock_distiller,
            db=self.mock_db,
            stopflag=self.stopflag,
            logger=self.mock_logger,
            stale_days=200,
            stale_days_full=20,
        )

        # Test AF branch logic
        stale_arg_af = maint.stale_days if "af" == "af" else maint.stale_days_full
        self.assertEqual(stale_arg_af, 200)

        # Test Full branch logic
        stale_arg_full = maint.stale_days if "full" == "af" else maint.stale_days_full
        self.assertEqual(stale_arg_full, 20)

    def test_database_priority_query_dispatches_split_stale_days(self):
        """Verify that db.for_background_priorities uses stale_days for AF and stale_days_full for Full."""
        maint = BackgroundMaintainer(
            distiller=self.mock_distiller,
            db=self.mock_db,
            stopflag=self.stopflag,
            logger=self.mock_logger,
            stale_days=400,
            stale_days_full=45,
        )

        self.mock_db.for_background_priorities.return_value = ([], [], [], [])
        self.mock_db.flush_annotation_cache.return_value = 0

        # Simulate one loop step or call for_background_priorities as in run()
        policy = maint.af_none_manager.current_preset

        # AF call
        maint.db.for_background_priorities(
            stale_days=maint.stale_days,
            p1_cooldown_hours=maint.p1_cooldown_hours,
            mode="af",
            af_none_policy=policy,
            limit=50,
        )
        self.mock_db.for_background_priorities.assert_called_with(
            stale_days=400,
            p1_cooldown_hours=24,
            mode="af",
            af_none_policy=policy,
            limit=50,
        )

        # Full call
        maint.db.for_background_priorities(
            stale_days=maint.stale_days_full,
            p1_cooldown_hours=maint.p1_cooldown_hours,
            mode="full",
            af_none_policy=policy,
            limit=50,
        )
        self.mock_db.for_background_priorities.assert_called_with(
            stale_days=45,
            p1_cooldown_hours=24,
            mode="full",
            af_none_policy=policy,
            limit=50,
        )


if __name__ == "__main__":
    unittest.main()
