"""Integration test for the deterministic portfolio demo."""

import tempfile
import unittest
from pathlib import Path

from comparison import compare_releases
from scripts.build_demo import build_demo_database


class DemoTests(unittest.TestCase):
    def test_demo_creates_a_detectable_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "demo.db"
            build_demo_database(database_path)
            comparison = compare_releases(database_path, "baseline", "candidate")

        self.assertFalse(comparison.release_ready)
        self.assertGreaterEqual(len(comparison.route_regressions), 1)
        self.assertLess(comparison.average_score_delta, -3.0)


if __name__ == "__main__":
    unittest.main()
