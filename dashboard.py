"""Streamlit dashboard for CARLA simulation test health."""

from pathlib import Path

import pandas as pd
import streamlit as st

from comparison import compare_releases
from database import list_releases, load_route_results
from health import build_health_report


DATABASE_PATH = Path(__file__).parent / "data" / "test_health.db"

st.set_page_config(page_title="CARLA Test Health", page_icon="🚦", layout="wide")
st.title("CARLA Simulation Test Health")
st.caption("Health signals calculated from imported CARLA Leaderboard results")

if not DATABASE_PATH.exists():
    st.warning("No database found. Run `python3 cli.py import` first.")
    st.stop()

releases = list_releases(DATABASE_PATH)
selected_release = st.selectbox("Release filter", ["All releases", *releases])
release_filter = None if selected_release == "All releases" else selected_release
routes = load_route_results(DATABASE_PATH, release_filter)
if not routes:
    st.warning("The database contains no CARLA route results.")
    st.stop()

report = build_health_report(routes)

metric_columns = st.columns(6)
metric_columns[0].metric("Routes", report.total_routes)
metric_columns[1].metric("Completion", f"{report.completion_rate:.1%}")
metric_columns[2].metric("Average score", f"{report.average_composed_score:.2f}")
metric_columns[3].metric("p95 system time", f"{report.p95_system_duration:.2f}s")
metric_columns[4].metric("Infractions", report.total_infractions)
metric_columns[5].metric("Critical", report.critical_infraction_count)

st.subheader("Health status")
if report.healthy:
    st.success("All health objectives are satisfied.")
else:
    for alert in report.alerts:
        st.error(alert)

st.subheader("Infraction patterns")
infraction_data = [
    {"infraction": name, "count": count}
    for name, count in report.infraction_counts.items()
]
if infraction_data:
    infraction_frame = pd.DataFrame(infraction_data)
    st.dataframe(infraction_frame, width="stretch", hide_index=True)
    st.bar_chart(infraction_frame.set_index("infraction")["count"])
else:
    st.info("No infractions were recorded.")

st.subheader("Routes requiring investigation")
unhealthy_ids = set(report.unhealthy_route_ids)
route_data = [
    {
        "route_id": route.route_id,
        "status": route.status,
        "composed_score": route.composed_score,
        "system_duration_seconds": route.duration_system,
        "infractions": route.num_infractions,
    }
    for route in routes
    if route.route_id in unhealthy_ids
]
if route_data:
    st.dataframe(pd.DataFrame(route_data), width="stretch", hide_index=True)
else:
    st.success("No routes require investigation.")

st.subheader("Release comparison")
if len(releases) < 2:
    st.info("Import results from at least two releases to enable comparison.")
else:
    comparison_columns = st.columns(2)
    baseline_name = comparison_columns[0].selectbox("Baseline", releases, index=0)
    candidate_name = comparison_columns[1].selectbox(
        "Candidate", releases, index=len(releases) - 1
    )

    if baseline_name == candidate_name:
        st.info("Choose two different releases.")
    else:
        comparison = compare_releases(DATABASE_PATH, baseline_name, candidate_name)
        delta_columns = st.columns(4)
        delta_columns[0].metric(
            "Completion delta", f"{comparison.completion_rate_delta:+.1%}"
        )
        delta_columns[1].metric(
            "Score delta", f"{comparison.average_score_delta:+.2f}"
        )
        delta_columns[2].metric(
            "p95 time delta", f"{comparison.p95_duration_delta:+.2f}s"
        )
        delta_columns[3].metric(
            "Critical delta", f"{comparison.critical_infraction_delta:+d}"
        )

        if comparison.release_ready:
            st.success("Candidate release is ready.")
        else:
            for regression in comparison.regressions:
                st.error(regression)
