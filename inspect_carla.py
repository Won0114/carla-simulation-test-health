from pathlib import Path

from carla_parser import load_carla_result, parse_route_results
from health import build_health_report


json_path = Path(__file__).parent / "data" / "raw" / "679_0_0_result.json"
result = load_carla_result(json_path)

print("Top-level keys:")
for key in result:
    print(f"- {key}")

# Navigate through the nested CARLA result structure.
checkpoint = result["_checkpoint"]
global_record = checkpoint["global_record"]
scores = global_record["scores_mean"]

print("\nRun summary:")
print(f"- Entry status: {result['entry_status']}")
print(f"- Simulation status: {global_record['status']}")
print(f"- Eligible: {result['eligible']}")
print(f"- Route score: {scores['score_route']}")
print(f"- Penalty score: {scores['score_penalty']}")
print(f"- Composed score: {scores['score_composed']}")

# Inspect each individual route result.
route_results = parse_route_results(result)
print(f"\nIndividual route results: {len(route_results)}")

for route in route_results:
    print(f"\nRoute: {route.route_id}")
    print(f"- Status: {route.status}")
    print(f"- Composed score: {route.composed_score}")
    print(f"- System duration: {route.duration_system} seconds")

    for infraction_name, details in route.infractions.items():
        if details:
            print(f"- Infraction: {infraction_name}")
            for detail in details:
                print(f"  - {detail}")

health = build_health_report(route_results)
print("\nHealth report:")
print(f"- Total routes: {health.total_routes}")
print(f"- Completion rate: {health.completion_rate:.1%}")
print(f"- Average composed score: {health.average_composed_score:.3f}")
print(f"- Average system duration: {health.average_system_duration:.2f} seconds")
print(f"- p95 system duration: {health.p95_system_duration:.2f} seconds")
print(f"- Total infractions: {health.total_infractions}")
print(f"- Critical infractions: {health.critical_infraction_count}")
print(f"- Healthy: {health.healthy}")

if health.alerts:
    print("- Alerts:")
    for alert in health.alerts:
        print(f"  - {alert}")
