"""Tests for SQLite persistence."""

import tempfile
import unittest
import sqlite3
from pathlib import Path

from carla_parser import load_carla_result, parse_route_results
from database import (
    connect,
    initialize_database,
    list_releases,
    load_route_results,
    save_carla_result,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RESULT = PROJECT_ROOT / "data" / "raw" / "679_0_0_result.json"


class DatabaseTests(unittest.TestCase):
    def test_legacy_database_is_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "legacy.db"
            connection = sqlite3.connect(database_path)
            connection.execute(
                """
                CREATE TABLE carla_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL UNIQUE,
                    entry_status TEXT NOT NULL,
                    eligible INTEGER NOT NULL,
                    imported_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
            connection.close()

            initialize_database(database_path)

            with connect(database_path) as migrated:
                columns = {
                    row["name"] for row in migrated.execute("PRAGMA table_info(carla_files)")
                }

        self.assertIn("release_name", columns)

    def test_result_is_saved_without_duplicates(self) -> None:
        raw_result = load_carla_result(SAMPLE_RESULT)
        routes = parse_route_results(raw_result)

        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "test.db"
            first_id, first_created = save_carla_result(
                database_path, SAMPLE_RESULT, raw_result, routes
            )
            second_id, second_created = save_carla_result(
                database_path, SAMPLE_RESULT, raw_result, routes
            )

            with connect(database_path) as connection:
                route_count = connection.execute(
                    "SELECT COUNT(*) FROM route_results"
                ).fetchone()[0]
                infraction_count = connection.execute(
                    "SELECT COUNT(*) FROM infractions"
                ).fetchone()[0]

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first_id, second_id)
        self.assertEqual(route_count, 1)
        self.assertEqual(infraction_count, 1)

    def test_saved_route_is_loaded_again(self) -> None:
        raw_result = load_carla_result(SAMPLE_RESULT)
        routes = parse_route_results(raw_result)

        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "test.db"
            save_carla_result(database_path, SAMPLE_RESULT, raw_result, routes)
            loaded_routes = load_route_results(database_path)

        self.assertEqual(len(loaded_routes), 1)
        self.assertEqual(loaded_routes[0].route_id, "RouteScenario_11_rep0")
        self.assertEqual(loaded_routes[0].composed_score, 92.593)
        self.assertIn("min_speed_infractions", loaded_routes[0].infractions)

    def test_release_names_are_listed(self) -> None:
        raw_result = load_carla_result(SAMPLE_RESULT)
        routes = parse_route_results(raw_result)

        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "test.db"
            save_carla_result(
                database_path, SAMPLE_RESULT, raw_result, routes, "release-v1"
            )

            releases = list_releases(database_path)

        self.assertEqual(releases, ["release-v1"])


if __name__ == "__main__":
    unittest.main()
