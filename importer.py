"""Batch ingestion for directories containing CARLA JSON results."""

import json
from dataclasses import dataclass
from pathlib import Path

from carla_parser import load_carla_result, parse_route_results
from database import save_carla_result


@dataclass(frozen=True)
class ImportSummary:
    """Counts and errors produced by one directory import."""

    files_seen: int
    files_imported: int
    files_duplicated: int
    files_rejected: int
    errors: tuple[str, ...]


def import_results_directory(
    database_path: str | Path,
    results_directory: str | Path,
    release_name: str = "public-sample",
) -> ImportSummary:
    """Validate and import every JSON file without stopping on bad input."""

    directory = Path(results_directory)
    if not directory.is_dir():
        raise ValueError(f"Results directory does not exist: {directory}")

    json_paths = sorted(directory.rglob("*.json"))
    imported = 0
    duplicated = 0
    errors = []

    for json_path in json_paths:
        try:
            raw_result = load_carla_result(json_path)
            routes = parse_route_results(raw_result)
            _, created = save_carla_result(
                database_path, json_path, raw_result, routes, release_name
            )
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"{json_path.name}: {error}")
            continue

        if created:
            imported += 1
        else:
            duplicated += 1

    return ImportSummary(
        files_seen=len(json_paths),
        files_imported=imported,
        files_duplicated=duplicated,
        files_rejected=len(errors),
        errors=tuple(errors),
    )
