"""Tests for baseline and candidate release comparison."""

import json
import tempfile
import unittest
from pathlib import Path

from carla_parser import load_carla_result, parse_route_results
from comparison import compare_releases
from database import save_carla_result


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RESULT = PROJECT_ROOT / "data" / "raw" / "679_0_0_result.json"


class ReleaseComparisonTests(unittest.TestCase):
    def test_score_regression_blocks_candidate(self) -> None:
        baseline_raw = load_carla_result(SAMPLE_RESULT)
        baseline_routes = parse_route_results(baseline_raw)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database_path = root / "test.db"
            save_carla_result(
                database_path, SAMPLE_RESULT, baseline_raw, baseline_routes, "baseline"
            )

            candidate_raw = json.loads(SAMPLE_RESULT.read_text(encoding="utf-8"))
            candidate_raw["_checkpoint"]["records"][0]["scores"]["score_composed"] = 70.0
            candidate_path = root / "candidate.json"
            candidate_path.write_text(json.dumps(candidate_raw), encoding="utf-8")
            candidate_routes = parse_route_results(candidate_raw)
            save_carla_result(
                database_path, candidate_path, candidate_raw, candidate_routes, "candidate"
            )

            comparison = compare_releases(database_path, "baseline", "candidate")

        self.assertLess(comparison.average_score_delta, -20.0)
        self.assertFalse(comparison.release_ready)
        self.assertTrue(any("Average score" in item for item in comparison.regressions))


if __name__ == "__main__":
    unittest.main()
