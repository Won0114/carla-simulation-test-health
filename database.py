"""SQLite persistence for parsed CARLA results."""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from carla_parser import RouteResult


SCHEMA = """
CREATE TABLE IF NOT EXISTS carla_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    release_name TEXT NOT NULL DEFAULT 'public-sample',
    source_file TEXT NOT NULL,
    source_sha256 TEXT NOT NULL UNIQUE,
    entry_status TEXT NOT NULL,
    eligible INTEGER NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS route_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    route_id TEXT NOT NULL,
    status TEXT NOT NULL,
    route_score REAL NOT NULL,
    penalty_score REAL NOT NULL,
    composed_score REAL NOT NULL,
    num_infractions INTEGER NOT NULL,
    route_length REAL NOT NULL,
    duration_game REAL NOT NULL,
    duration_system REAL NOT NULL,
    FOREIGN KEY(file_id) REFERENCES carla_files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS infractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_result_id INTEGER NOT NULL,
    infraction_name TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    FOREIGN KEY(route_result_id) REFERENCES route_results(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_route_results_file ON route_results(file_id);
CREATE INDEX IF NOT EXISTS idx_route_results_route ON route_results(route_id);
CREATE INDEX IF NOT EXISTS idx_infractions_route ON infractions(route_result_id);
CREATE INDEX IF NOT EXISTS idx_infractions_name ON infractions(infraction_name);
"""


@contextmanager
def connect(database_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open a transaction and always close the SQLite connection."""

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()


def initialize_database(database_path: str | Path) -> None:
    """Create tables and apply small forward-compatible migrations."""

    with connect(database_path) as connection:
        connection.executescript(SCHEMA)
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(carla_files)")
        }
        if "release_name" not in columns:
            connection.execute(
                "ALTER TABLE carla_files "
                "ADD COLUMN release_name TEXT NOT NULL DEFAULT 'public-sample'"
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_carla_files_release "
            "ON carla_files(release_name)"
        )


def save_carla_result(
    database_path: str | Path,
    source_path: str | Path,
    raw_result: dict[str, Any],
    routes: list[RouteResult],
    release_name: str = "public-sample",
) -> tuple[int, bool]:
    """Save one parsed CARLA file and return its ID and whether it was new."""

    initialize_database(database_path)
    source = Path(source_path)
    if not release_name.strip():
        raise ValueError("release_name must not be empty")
    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()

    with connect(database_path) as connection:
        existing = connection.execute(
            "SELECT id FROM carla_files WHERE source_sha256 = ?",
            (source_sha256,),
        ).fetchone()
        if existing:
            return int(existing["id"]), False

        cursor = connection.execute(
            """
            INSERT INTO carla_files (
                release_name, source_file, source_sha256,
                entry_status, eligible, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                release_name,
                source.name,
                source_sha256,
                raw_result["entry_status"],
                int(raw_result["eligible"]),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        file_id = int(cursor.lastrowid)

        for route in routes:
            route_cursor = connection.execute(
                """
                INSERT INTO route_results (
                    file_id, route_id, status, route_score, penalty_score,
                    composed_score, num_infractions, route_length,
                    duration_game, duration_system
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    route.route_id,
                    route.status,
                    route.route_score,
                    route.penalty_score,
                    route.composed_score,
                    route.num_infractions,
                    route.route_length,
                    route.duration_game,
                    route.duration_system,
                ),
            )
            route_result_id = int(route_cursor.lastrowid)

            for infraction_name, details in route.infractions.items():
                for detail in details:
                    connection.execute(
                        """
                        INSERT INTO infractions (
                            route_result_id, infraction_name, detail_json
                        ) VALUES (?, ?, ?)
                        """,
                        (route_result_id, infraction_name, json.dumps(detail)),
                    )

    return file_id, True


def load_route_results(
    database_path: str | Path,
    release_name: str | None = None,
) -> list[RouteResult]:
    """Rebuild normalized route results from SQLite rows."""

    initialize_database(database_path)
    where_clause = "WHERE cf.release_name = ?" if release_name else ""
    parameters = (release_name,) if release_name else ()
    with connect(database_path) as connection:
        route_rows = connection.execute(
            f"""
            SELECT rr.*
            FROM route_results rr
            JOIN carla_files cf ON cf.id = rr.file_id
            {where_clause}
            ORDER BY rr.id
            """,
            parameters,
        ).fetchall()
        infraction_rows = connection.execute(
            f"""
            SELECT i.*
            FROM infractions i
            JOIN route_results rr ON rr.id = i.route_result_id
            JOIN carla_files cf ON cf.id = rr.file_id
            {where_clause}
            ORDER BY i.id
            """,
            parameters,
        ).fetchall()

    infractions_by_route: dict[int, dict[str, list[Any]]] = {}
    for row in infraction_rows:
        route_infractions = infractions_by_route.setdefault(row["route_result_id"], {})
        details = route_infractions.setdefault(row["infraction_name"], [])
        details.append(json.loads(row["detail_json"]))

    return [
        RouteResult(
            route_id=row["route_id"],
            status=row["status"],
            route_score=float(row["route_score"]),
            penalty_score=float(row["penalty_score"]),
            composed_score=float(row["composed_score"]),
            num_infractions=int(row["num_infractions"]),
            route_length=float(row["route_length"]),
            duration_game=float(row["duration_game"]),
            duration_system=float(row["duration_system"]),
            infractions=infractions_by_route.get(row["id"], {}),
        )
        for row in route_rows
    ]


def list_releases(database_path: str | Path) -> list[str]:
    """Return stored release names in alphabetical order."""

    initialize_database(database_path)
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT DISTINCT release_name FROM carla_files ORDER BY release_name"
        ).fetchall()
    return [str(row["release_name"]) for row in rows]
