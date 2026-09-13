"""Build a deterministic two-release database for the portfolio demo.

The candidate release is synthetic and intentionally degraded. It exists to
exercise regression detection; it is not a claim about a real driving model.
"""

import argparse
import json
import tempfile
from pathlib import Path

from comparison import compare_releases
from importer import import_results_directory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw"
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "demo_health.db"


def build_candidate(source: Path, destination: Path, index: int) -> None:
    """Create one reproducible degraded candidate result."""

    result = json.loads(source.read_text(encoding="utf-8"))
    record = result["_checkpoint"]["records"][0]
    record["scores"]["score_composed"] = max(
        0.0, float(record["scores"]["score_composed"]) - (8.0 + index * 4.0)
    )
    record["meta"]["duration_system"] = (
        float(record["meta"]["duration_system"]) * (1.20 + index * 0.05)
    )

    if index == 1:
        record["status"] = "Failed"
        record["infractions"].setdefault("route_timeout", []).append(
            "Synthetic demo timeout"
        )
        record["num_infractions"] = int(record["num_infractions"]) + 1
    elif index == 2:
        record["infractions"].setdefault("red_light", []).append(
            "Synthetic demo red-light violation"
        )
        record["num_infractions"] = int(record["num_infractions"]) + 1

    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")


def build_demo_database(database_path: Path) -> None:
    """Import public baseline files and a synthetic candidate release."""

    if database_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite {database_path}. Choose a new --database path."
        )

    baseline = import_results_directory(database_path, RAW_DIRECTORY, "baseline")
    with tempfile.TemporaryDirectory() as temporary_directory:
        candidate_directory = Path(temporary_directory)
        for index, source in enumerate(sorted(RAW_DIRECTORY.glob("*.json"))):
            build_candidate(source, candidate_directory / source.name, index)
        candidate = import_results_directory(
            database_path, candidate_directory, "candidate"
        )

    comparison = compare_releases(database_path, "baseline", "candidate")
    print(f"Demo database: {database_path}")
    print(f"Baseline files imported: {baseline.files_imported}")
    print(f"Candidate files imported: {candidate.files_imported}")
    print(f"Release ready: {comparison.release_ready}")
    for regression in comparison.regressions:
        print(f"Regression: {regression}")
    print(f"Routes requiring triage: {len(comparison.route_regressions)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the CARLA portfolio demo")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()
    build_demo_database(args.database)


if __name__ == "__main__":
    main()
