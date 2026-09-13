# CARLA Simulation Test Health

A Python project that validates public CARLA Leaderboard JSON results, stores them in SQLite, and analyzes simulation test health and release regressions. Its Streamlit dashboard displays completion rates, scores, execution times, recurring infractions, and routes that require investigation.

## Why this project exists

Autonomous-driving simulations produce many route-level result files. A model can
improve on an aggregate score while becoming slower, failing particular routes,
or introducing safety-critical infractions. This project turns those raw files
into a repeatable release-quality check and identifies the routes an engineer
should investigate first.

The central question is: **Is the candidate release safe and reliable enough to
ship, and if not, where did it regress?**

## Features

- Validates CARLA JSON structure and data types
- Imports multiple JSON files without stopping when one file is invalid
- Prevents duplicate imports using SHA-256 hashes
- Stores normalized results in SQLite
- Calculates completion rate, average score, and average and p95 execution time
- Detects recurring and critical infractions
- Compares a baseline release with a candidate release for regressions
- Matches route IDs across releases for route-level regression triage
- Provides both a command-line interface and a Streamlit dashboard
- Includes unit and integration tests with GitHub Actions CI

## Architecture

```text
CARLA JSON
    ↓
carla_parser.py       Validate and convert data into RouteResult objects
    ↓
importer.py           Process a directory of JSON files
    ↓
database.py           Store and query normalized SQLite data
    ↓
health.py             Evaluate SLOs and recurring issues
    ↓
comparison.py         Compare releases for regressions
    ↓
cli.py / dashboard.py Provide CLI commands and visualizations
```

## Installation

Python 3.10 or later is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Reproducible portfolio demo

Build a two-release SQLite database from the included public samples:

```bash
python -m scripts.build_demo
carla-health compare --database data/demo_health.db \
  --baseline baseline --candidate candidate
streamlit run dashboard.py
```

The script treats the public samples as the baseline and creates a deterministic,
intentionally degraded candidate so every reviewer can reproduce the regression
workflow. The candidate is clearly synthetic and is used only to demonstrate the
system; it is not presented as output from a real autonomous-driving model.

Expected decision: the candidate is blocked because its average score decreases,
completion rate falls, critical infractions increase, and individual route
regressions cross the triage thresholds.

## Usage

Inspect the structure of a sample JSON file:

```bash
carla-health inspect data/raw/679_0_0_result.json
```

Import a directory of JSON results for one release:

```bash
carla-health import --directory data/raw --release public-sample
```

Generate an overall or release-specific health report:

```bash
carla-health report
carla-health report --release public-sample
```

Compare two releases:

```bash
carla-health compare --baseline release-v1 --candidate release-v2
```

Before comparing releases, import each version from a separate directory and assign it a release name:

```bash
carla-health import --directory results/release-v1 --release release-v1
carla-health import --directory results/release-v2 --release release-v2
```

Start the dashboard:

```bash
streamlit run dashboard.py
```

Then open `http://localhost:8501` in a web browser.

## Default SLOs

| Metric | Target |
|---|---:|
| Route completion | At least 95% |
| Average composed score | At least 80 |
| p95 system duration | At most 600 seconds |
| Critical infractions | 0 |

Critical infractions include collisions, traffic-light violations, route deviations, and timeouts. A recurring-infraction alert is raised when the same type of infraction appears at least twice.

Release-level regression rules block a candidate when completion falls by more
than 2 percentage points, average score falls by more than 3 points, p95 runtime
increases by more than 15%, or critical infractions increase. These are explicit
demo policies rather than CARLA-official thresholds; a production team should
calibrate them from historical runs and its risk tolerance.

## Engineering decisions

| Decision | Reason |
|---|---|
| Validate before storage | Prevent malformed results from contaminating metrics |
| Normalize into SQLite | Support release filtering and reproducible queries |
| SHA-256 deduplication | Make repeated ingestion idempotent |
| Continue after invalid files | Keep batch ingestion resilient and report failures |
| Aggregate and route-level checks | Show both release impact and actionable failure locations |
| Deterministic demo data | Let reviewers reproduce a meaningful regression without running CARLA |

## Tests

```bash
python -m unittest discover -s tests -v
```

## Sample Data

This repository includes three public result files from different CARLA scenarios. Their sources and links are documented in [`data/raw/README.md`](data/raw/README.md). These samples demonstrate the parsing and analysis workflow. Real release decisions should use results generated from multiple software versions under the same test configuration.

## Limitations and next steps

- The repository contains only three public routes, so its metrics demonstrate the
  workflow rather than statistical confidence about a driving system.
- Baseline and candidate runs should use the same route set, seeds, CARLA version,
  weather, and hardware before a real release decision is made.
- With repeated runs, confidence intervals or bootstrap comparisons should replace
  fixed point-estimate thresholds.
- A production deployment would store experiment metadata, publish the dashboard,
  and run the comparison automatically in CI after simulation jobs complete.
