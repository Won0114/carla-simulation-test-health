"""Print a CARLA health report from the SQLite database."""

from pathlib import Path

from database import load_route_results
from health import build_health_report


database_path = Path(__file__).parent / "data" / "test_health.db"
routes = load_route_results(database_path)

if not routes:
    raise SystemExit("No CARLA results are stored. Run import_carla.py first.")

report = build_health_report(routes)

print("CARLA Test Health Report")
print(f"- Total routes: {report.total_routes}")
print(f"- Completion rate: {report.completion_rate:.1%}")
print(f"- Average composed score: {report.average_composed_score:.2f}")
print(f"- Average system duration: {report.average_system_duration:.2f} seconds")
print(f"- p95 system duration: {report.p95_system_duration:.2f} seconds")
print(f"- Total infractions: {report.total_infractions}")
print(f"- Critical infractions: {report.critical_infraction_count}")
print(f"- Healthy: {report.healthy}")

for name, count in report.infraction_counts.items():
    print(f"- Infraction: {name}={count}")

for route_id in report.unhealthy_route_ids:
    print(f"- Investigate route: {route_id}")

for alert in report.alerts:
    print(f"- Alert: {alert}")
