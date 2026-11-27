import datetime as dt
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_usage import stats, usage
from inkkit import THEMES, reset_fonts


def week(start, *counts):
    return [(start + dt.timedelta(days=i), count) for i, count in enumerate(counts)]


class UsageTests(unittest.TestCase):
    def test_reset_counts_down_to_sunday(self):
        sunday = dt.date(2026, 11, 22)
        for elapsed in range(1, 8):
            with self.subTest(elapsed=elapsed):
                result = stats(0, [week(sunday, *([0] * elapsed))])
                self.assertEqual(result["resets"], 8 - elapsed)

    def test_pace_excludes_partial_historical_week(self):
        weeks = [
            week(dt.date(2026, 11, 14), 100),
            week(dt.date(2026, 11, 15), 1, 1, 1, 1, 1, 1, 1),
            week(dt.date(2026, 11, 22), 1, 1, 0),
        ]
        result = stats(109, weeks)
        # The trailing zero leaves yesterday's streak active.
        self.assertEqual(result["current"], 10)
        self.assertEqual(result["best"], 100)
        self.assertEqual(result["pace"], "behind")
        weeks[-1][-1] = (dt.date(2026, 11, 24), 1)
        self.assertEqual(stats(110, weeks)["pace"], "on")

    def test_zero_activity_renders_both_themes(self):
        result = stats(0, [week(dt.date(2026, 11, 22), 0)])
        self.assertEqual(result["best"], 0)
        for theme in THEMES:
            with self.subTest(theme=theme):
                reset_fonts()
                card = usage(theme, result)
                ElementTree.fromstring(card)
                self.assertIn("best week 0", card)
                self.assertIn("Resets in 7 days", card)

    def test_empty_calendar_has_clear_error(self):
        with self.assertRaisesRegex(ValueError, "contains no days"):
            stats(0, [])
