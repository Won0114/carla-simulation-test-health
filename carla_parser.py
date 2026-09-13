"""Load and validate CARLA result files."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_KEYS = {"_checkpoint", "entry_status", "eligible"}


@dataclass(frozen=True)
class RouteResult:
    """Normalized values from one CARLA route execution."""

    route_id: str
    status: str
    route_score: float
    penalty_score: float
    composed_score: float
    num_infractions: int
    route_length: float
    duration_game: float
    duration_system: float
    infractions: dict[str, list[Any]]


def load_carla_result(path: str | Path) -> dict[str, Any]:
    """Load one CARLA JSON result and validate its basic structure."""

    json_path = Path(path)
    with json_path.open(encoding="utf-8") as file:
        result = json.load(file)

    if not isinstance(result, dict):
        raise ValueError("CARLA result must contain a JSON object at the top level")

    missing_keys = REQUIRED_TOP_LEVEL_KEYS - result.keys()
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ValueError(f"CARLA result is missing required keys: {missing}")

    checkpoint = result["_checkpoint"]
    if not isinstance(checkpoint, dict):
        raise ValueError("_checkpoint must be a JSON object")

    records = checkpoint.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("_checkpoint.records must be a non-empty list")

    for index, record in enumerate(records):
        location = f"_checkpoint.records[{index}]"

        if not isinstance(record, dict):
            raise ValueError(f"{location} must be a JSON object")

        for key in ("route_id", "status"):
            if not isinstance(record.get(key), str) or not record[key]:
                raise ValueError(f"{location}.{key} must be a non-empty string")

        scores = record.get("scores")
        if not isinstance(scores, dict):
            raise ValueError(f"{location}.scores must be a JSON object")

        for key in ("score_route", "score_penalty", "score_composed"):
            value = scores.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{location}.scores.{key} must be numeric")

        num_infractions = record.get("num_infractions")
        if isinstance(num_infractions, bool) or not isinstance(num_infractions, (int, float)):
            raise ValueError(f"{location}.num_infractions must be numeric")

        metadata = record.get("meta")
        if not isinstance(metadata, dict):
            raise ValueError(f"{location}.meta must be a JSON object")

        for key in ("route_length", "duration_game", "duration_system"):
            value = metadata.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{location}.meta.{key} must be numeric")

        infractions = record.get("infractions")
        if not isinstance(infractions, dict):
            raise ValueError(f"{location}.infractions must be a JSON object")

        for name, details in infractions.items():
            if not isinstance(name, str) or not isinstance(details, list):
                raise ValueError(f"{location}.infractions must map names to lists")

    return result


def parse_route_results(result: dict[str, Any]) -> list[RouteResult]:
    """Convert validated CARLA records into normalized route results."""

    route_results = []
    for record in result["_checkpoint"]["records"]:
        scores = record["scores"]
        metadata = record["meta"]
        route_results.append(
            RouteResult(
                route_id=record["route_id"],
                status=record["status"],
                route_score=float(scores["score_route"]),
                penalty_score=float(scores["score_penalty"]),
                composed_score=float(scores["score_composed"]),
                num_infractions=int(record["num_infractions"]),
                route_length=float(metadata["route_length"]),
                duration_game=float(metadata["duration_game"]),
                duration_system=float(metadata["duration_system"]),
                infractions=record["infractions"],
            )
        )
    return route_results
