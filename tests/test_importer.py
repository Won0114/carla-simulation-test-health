"""Tests for resilient CARLA directory imports."""

import tempfile
import unittest
from pathlib import Path

from importer import import_results_directory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RESULT = PROJECT_ROOT / "data" / "raw" / "679_0_0_result.json"


class ImporterTests(unittest.TestCase):
    def test_bad_file_does_not_stop_directory_import(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            results_directory = root / "results"
            results_directory.mkdir()
            (results_directory / "valid.json").write_bytes(SAMPLE_RESULT.read_bytes())
            (results_directory / "broken.json").write_text("{broken", encoding="utf-8")

            summary = import_results_directory(root / "test.db", results_directory)

        self.assertEqual(summary.files_seen, 2)
        self.assertEqual(summary.files_imported, 1)
        self.assertEqual(summary.files_rejected, 1)
        self.assertIn("broken.json", summary.errors[0])


if __name__ == "__main__":
    unittest.main()
