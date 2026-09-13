"""Tests for CARLA health metric calculations."""

import unittest

from carla_parser import RouteResult
from health import build_health_report, percentile


def make_route(status: str, score: float, duration: float, infractions: int) -> RouteResult:
    return RouteResult(
        route_id="test-route",
        status=status,
        route_score=100.0,
        penalty_score=1.0,
        composed_score=score,
        num_infractions=infractions,
        route_length=100.0,
        duration_game=10.0,
        duration_system=duration,
        infractions={},
    )


class HealthReportTests(unittest.TestCase):
    def test_percentile_interpolates_values(self) -> None:
        self.assertEqual(percentile([1.0, 2.0, 3.0], 0.5), 2.0)
        self.assertEqual(percentile([100.0, 200.0], 0.95), 195.0)

    def test_multiple_routes_are_aggregated(self) -> None:
        routes = [
            make_route("Completed", 90.0, 100.0, 1),
            make_route("Failed", 50.0, 200.0, 2),
        ]

        report = build_health_report(routes)

        self.assertEqual(report.total_routes, 2)
        self.assertEqual(report.completion_rate, 0.5)
        self.assertEqual(report.average_composed_score, 70.0)
        self.assertEqual(report.average_system_duration, 150.0)
        self.assertEqual(report.p95_system_duration, 195.0)
        self.assertEqual(report.total_infractions, 3)
        self.assertFalse(report.healthy)
        self.assertEqual(len(report.alerts), 2)
        self.assertEqual(report.unhealthy_route_ids, ("test-route", "test-route"))

    def test_recurring_infractions_create_an_alert(self) -> None:
        first = make_route("Completed", 90.0, 100.0, 1)
        second = make_route("Completed", 90.0, 100.0, 1)
        first.infractions["red_light"] = ["first event"]
        second.infractions["red_light"] = ["second event"]

        report = build_health_report([first, second])

        self.assertEqual(report.infraction_counts["red_light"], 2)
        self.assertEqual(report.critical_infraction_count, 2)
        self.assertEqual(report.recurring_infractions, ("red_light",))
        self.assertTrue(any("Critical infractions" in alert for alert in report.alerts))
        self.assertTrue(any("Recurring infractions" in alert for alert in report.alerts))


if __name__ == "__main__":
    unittest.main()
