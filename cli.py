"""Command-line interface for CARLA test-health workflows."""

import argparse
from pathlib import Path

from carla_parser import load_carla_result, parse_route_results
from comparison import compare_releases
from database import load_route_results
from health import build_health_report
from importer import import_results_directory


DEFAULT_DATABASE = Path("data/test_health.db")
DEFAULT_RAW_DIRECTORY = Path("data/raw")


def build_parser() -> argparse.ArgumentParser:
    """Define commands and options accepted by the CLI."""

    parser = argparse.ArgumentParser(description="Monitor CARLA simulation test health")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="import a directory of CARLA JSON files")
    import_parser.add_argument("--directory", type=Path, default=DEFAULT_RAW_DIRECTORY)
    import_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    import_parser.add_argument("--release", default="public-sample")

    report_parser = subparsers.add_parser("report", help="show health metrics from SQLite")
    report_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    report_parser.add_argument("--release")

    inspect_parser = subparsers.add_parser("inspect", help="inspect one CARLA JSON file")
    inspect_parser.add_argument("path", type=Path)

    compare_parser = subparsers.add_parser("compare", help="compare candidate with baseline")
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--candidate", required=True)
    compare_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)

    return parser


def main(arguments: list[str] | None = None) -> None:
    """Run the selected CLI command."""

    args = build_parser().parse_args(arguments)

    if args.command == "import":
        summary = import_results_directory(args.database, args.directory, args.release)
        print(f"Files seen: {summary.files_seen}")
        print(f"Imported: {summary.files_imported}")
        print(f"Duplicates: {summary.files_duplicated}")
        print(f"Rejected: {summary.files_rejected}")
        for error in summary.errors:
            print(f"Error: {error}")
        return

    if args.command == "compare":
        comparison = compare_releases(args.database, args.baseline, args.candidate)
        print(f"Completion delta: {comparison.completion_rate_delta:+.1%}")
        print(f"Average score delta: {comparison.average_score_delta:+.2f}")
        print(f"p95 duration delta: {comparison.p95_duration_delta:+.2f}s")
        print(f"Critical infraction delta: {comparison.critical_infraction_delta:+d}")
        print(f"Release ready: {comparison.release_ready}")
        for regression in comparison.regressions:
            print(f"Regression: {regression}")
        return

    if args.command == "report":
        routes = load_route_results(args.database, args.release)
        if not routes:
            scope = f" for release {args.release}" if args.release else ""
            raise SystemExit(
                f"No CARLA results are stored{scope}. Run the import command first."
            )
        report = build_health_report(routes)
        print(f"Total routes: {report.total_routes}")
        print(f"Completion rate: {report.completion_rate:.1%}")
        print(f"Average composed score: {report.average_composed_score:.2f}")
        print(f"Average system duration: {report.average_system_duration:.2f}s")
        print(f"p95 system duration: {report.p95_system_duration:.2f}s")
        print(f"Total infractions: {report.total_infractions}")
        print(f"Critical infractions: {report.critical_infraction_count}")
        print(f"Healthy: {report.healthy}")
        for name, count in report.infraction_counts.items():
            print(f"Infraction: {name}={count}")
        for route_id in report.unhealthy_route_ids:
            print(f"Investigate route: {route_id}")
        for alert in report.alerts:
            print(f"Alert: {alert}")
        return

    result = load_carla_result(args.path)
    routes = parse_route_results(result)
    print(f"Entry status: {result['entry_status']}")
    print(f"Eligible: {result['eligible']}")
    print(f"Routes: {len(routes)}")
    for route in routes:
        print(f"- {route.route_id}: {route.status}, score={route.composed_score:.3f}")


if __name__ == "__main__":
    main()
