"""Tests for CARLA result loading and validation."""

import json
import tempfile
import unittest
from pathlib import Path

from carla_parser import load_carla_result, parse_route_results


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RESULT = PROJECT_ROOT / "data" / "raw" / "679_0_0_result.json"


class CarlaParserTests(unittest.TestCase):
    def test_valid_result_is_loaded(self) -> None:
        result = load_carla_result(SAMPLE_RESULT)

        self.assertEqual(result["entry_status"], "Finished")
        self.assertEqual(len(result["_checkpoint"]["records"]), 1)

    def test_route_result_is_normalized(self) -> None:
        result = load_carla_result(SAMPLE_RESULT)
        route = parse_route_results(result)[0]

        self.assertEqual(route.route_id, "RouteScenario_11_rep0")
        self.assertEqual(route.status, "Completed")
        self.assertAlmostEqual(route.composed_score, 92.593)
        self.assertEqual(route.num_infractions, 1)

    def test_missing_scores_are_rejected(self) -> None:
        invalid_result = json.loads(SAMPLE_RESULT.read_text(encoding="utf-8"))
        del invalid_result["_checkpoint"]["records"][0]["scores"]

        with tempfile.TemporaryDirectory() as temporary_directory:
            invalid_path = Path(temporary_directory) / "invalid.json"
            invalid_path.write_text(json.dumps(invalid_result), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, r"records\[0\]\.scores"):
                load_carla_result(invalid_path)


if __name__ == "__main__":
    unittest.main()
