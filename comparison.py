"""Baseline-versus-candidate CARLA release comparison."""

from dataclasses import dataclass
from pathlib import Path

from database import load_route_results
from health import HealthReport, build_health_report


@dataclass(frozen=True)
class RouteRegression:
    """A route-level change that helps an engineer locate a regression."""

    route_id: str
    baseline_status: str
    candidate_status: str
    score_delta: float
    duration_delta: float
    infraction_delta: int


@dataclass(frozen=True)
class ReleaseComparison:
    """Health deltas and regression decisions for two releases."""

    baseline: HealthReport
    candidate: HealthReport
    completion_rate_delta: float
    average_score_delta: float
    p95_duration_delta: float
    critical_infraction_delta: int
    route_regressions: tuple[RouteRegression, ...]
    regressions: tuple[str, ...]
    release_ready: bool


def compare_releases(
    database_path: str | Path,
    baseline_name: str,
    candidate_name: str,
) -> ReleaseComparison:
    """Compare candidate health with a stored baseline release."""

    baseline_routes = load_route_results(database_path, baseline_name)
    candidate_routes = load_route_results(database_path, candidate_name)
    if not baseline_routes:
        raise ValueError(f"Baseline release has no routes: {baseline_name}")
    if not candidate_routes:
        raise ValueError(f"Candidate release has no routes: {candidate_name}")

    baseline = build_health_report(baseline_routes)
    candidate = build_health_report(candidate_routes)
    completion_delta = candidate.completion_rate - baseline.completion_rate
    score_delta = candidate.average_composed_score - baseline.average_composed_score
    duration_delta = candidate.p95_system_duration - baseline.p95_system_duration
    critical_delta = candidate.critical_infraction_count - baseline.critical_infraction_count

    baseline_by_route = {route.route_id: route for route in baseline_routes}
    candidate_by_route = {route.route_id: route for route in candidate_routes}
    route_regressions = []
    for route_id in sorted(baseline_by_route.keys() & candidate_by_route.keys()):
        baseline_route = baseline_by_route[route_id]
        candidate_route = candidate_by_route[route_id]
        score_change = candidate_route.composed_score - baseline_route.composed_score
        duration_change = candidate_route.duration_system - baseline_route.duration_system
        infraction_change = candidate_route.num_infractions - baseline_route.num_infractions
        status_regressed = (
            baseline_route.status in {"Completed", "Perfect"}
            and candidate_route.status not in {"Completed", "Perfect"}
        )
        if status_regressed or score_change < -3.0 or infraction_change > 0:
            route_regressions.append(
                RouteRegression(
                    route_id=route_id,
                    baseline_status=baseline_route.status,
                    candidate_status=candidate_route.status,
                    score_delta=score_change,
                    duration_delta=duration_change,
                    infraction_delta=infraction_change,
                )
            )

    regressions = []
    if completion_delta < -0.02:
        regressions.append(f"Completion rate decreased by {abs(completion_delta):.1%}")
    if score_delta < -3.0:
        regressions.append(f"Average score decreased by {abs(score_delta):.2f} points")
    if baseline.p95_system_duration and duration_delta / baseline.p95_system_duration > 0.15:
        regressions.append("p95 system duration increased by more than 15%")
    if critical_delta > 0:
        regressions.append(f"Critical infractions increased by {critical_delta}")

    return ReleaseComparison(
        baseline=baseline,
        candidate=candidate,
        completion_rate_delta=completion_delta,
        average_score_delta=score_delta,
        p95_duration_delta=duration_delta,
        critical_infraction_delta=critical_delta,
        route_regressions=tuple(route_regressions),
        regressions=tuple(regressions),
        release_ready=not regressions and candidate.healthy,
    )
