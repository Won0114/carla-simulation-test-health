"""Tests for the command-line workflow."""

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from cli import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RESULT = PROJECT_ROOT / "data" / "raw" / "679_0_0_result.json"


class CliTests(unittest.TestCase):
    def test_import_then_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            results_directory = root / "results"
            results_directory.mkdir()
            (results_directory / "result.json").write_bytes(SAMPLE_RESULT.read_bytes())
            database_path = root / "test.db"

            output = StringIO()
            with redirect_stdout(output):
                main([
                    "import",
                    "--directory",
                    str(results_directory),
                    "--database",
                    str(database_path),
                ])
                main([
                    "report",
                    "--database",
                    str(database_path),
                    "--release",
                    "public-sample",
                ])

        self.assertIn("Imported: 1", output.getvalue())
        self.assertIn("Completion rate: 100.0%", output.getvalue())


if __name__ == "__main__":
    unittest.main()
