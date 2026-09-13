# CARLA Simulation Test Health

A Python project that validates public CARLA Leaderboard JSON results, stores them in SQLite, and analyzes simulation test health and release regressions. Its Streamlit dashboard displays completion rates, scores, execution times, recurring infractions, and routes that require investigation.

## Features

- Validates CARLA JSON structure and data types
- Imports multiple JSON files without stopping when one file is invalid
- Prevents duplicate imports using SHA-256 hashes
- Stores normalized results in SQLite
- Calculates completion rate, average score, and average and p95 execution time
- Detects recurring and critical infractions
- Compares a baseline release with a candidate release for regressions
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

## Tests

```bash
python -m unittest discover -s tests -v
```

## Sample Data

This repository includes three public result files from different CARLA scenarios. Their sources and links are documented in [`data/raw/README.md`](data/raw/README.md). These samples demonstrate the parsing and analysis workflow. Real release decisions should use results generated from multiple software versions under the same test configuration.
