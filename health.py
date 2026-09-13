"""Health metrics calculated from normalized CARLA route results."""

import math
from dataclasses import dataclass
from statistics import mean

from carla_parser import RouteResult


COMPLETED_STATUSES = {"Completed", "Perfect"}
COMPLETION_RATE_SLO = 0.95
COMPOSED_SCORE_SLO = 80.0
SYSTEM_DURATION_SLO_SECONDS = 600.0
CRITICAL_INFRACTIONS = {
    "collisions_layout",
    "collisions_pedestrian",
    "collisions_vehicle",
    "red_light",
    "route_dev",
    "route_timeout",
    "scenario_timeouts",
}


@dataclass(frozen=True)
class HealthReport:
    """Aggregated health signals for a collection of CARLA routes."""

    total_routes: int
    completed_routes: int
    completion_rate: float
    average_composed_score: float
    average_system_duration: float
    p95_system_duration: float
    total_infractions: int
    critical_infraction_count: int
    infraction_counts: dict[str, int]
    recurring_infractions: tuple[str, ...]
    unhealthy_route_ids: tuple[str, ...]
    healthy: bool
    alerts: tuple[str, ...]


def percentile(values: list[float], percentile_value: float) -> float:
    """Calculate a linearly interpolated percentile."""

    if not values:
        raise ValueError("At least one value is required")

    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]

    weight = position - lower_index
    return ordered[lower_index] * (1 - weight) + ordered[upper_index] * weight


def build_health_report(routes: list[RouteResult]) -> HealthReport:
    """Calculate summary metrics across multiple CARLA route results."""

    if not routes:
        raise ValueError("At least one route result is required")

    completed_routes = sum(route.status in COMPLETED_STATUSES for route in routes)
    completion_rate = completed_routes / len(routes)
    average_score = mean(route.composed_score for route in routes)
    average_duration = mean(route.duration_system for route in routes)
    p95_duration = percentile([route.duration_system for route in routes], 0.95)

    infraction_counts: dict[str, int] = {}
    for route in routes:
        for name, details in route.infractions.items():
            infraction_counts[name] = infraction_counts.get(name, 0) + len(details)

    recurring_infractions = tuple(
        name for name, count in sorted(infraction_counts.items()) if count >= 2
    )
    critical_infraction_count = sum(
        count for name, count in infraction_counts.items() if name in CRITICAL_INFRACTIONS
    )
    unhealthy_route_ids = tuple(
        route.route_id
        for route in routes
        if route.status not in COMPLETED_STATUSES
        or route.composed_score < COMPOSED_SCORE_SLO
        or route.num_infractions > 0
    )

    alerts = []
    if completion_rate < COMPLETION_RATE_SLO:
        alerts.append(
            f"Completion rate is {completion_rate:.1%}; expected at least {COMPLETION_RATE_SLO:.1%}"
        )
    if average_score < COMPOSED_SCORE_SLO:
        alerts.append(
            f"Average composed score is {average_score:.2f}; expected at least {COMPOSED_SCORE_SLO:.2f}"
        )
    if p95_duration > SYSTEM_DURATION_SLO_SECONDS:
        alerts.append(
            f"p95 system duration is {p95_duration:.2f}s; "
            f"expected at most {SYSTEM_DURATION_SLO_SECONDS:.2f}s"
        )
    if critical_infraction_count:
        alerts.append(f"Critical infractions detected: {critical_infraction_count}")
    if recurring_infractions:
        alerts.append(
            "Recurring infractions detected: " + ", ".join(recurring_infractions)
        )

    return HealthReport(
        total_routes=len(routes),
        completed_routes=completed_routes,
        completion_rate=completion_rate,
        average_composed_score=average_score,
        average_system_duration=average_duration,
        p95_system_duration=p95_duration,
        total_infractions=sum(route.num_infractions for route in routes),
        critical_infraction_count=critical_infraction_count,
        infraction_counts=infraction_counts,
        recurring_infractions=recurring_infractions,
        unhealthy_route_ids=unhealthy_route_ids,
        healthy=not alerts,
        alerts=tuple(alerts),
    )
