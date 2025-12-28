# github-metrics

GitHub contribution metrics reporter - generates beautiful reports of your GitHub activity.

## Installation

```bash
# Using uvx (recommended)
uvx --from git+https://github.com/kazuph/github-metrics create-report --year 2024

# Or install with pip
pip install git+https://github.com/kazuph/github-metrics
```

## Usage

```bash
# Report for current year
create-report

# Report for specific year(s)
create-report --year 2023 --year 2024 --year 2025

# Output as JSON
create-report --year 2024 --json

# For a different user
create-report --username octocat --year 2024
```

## Requirements

- Python 3.10+
- GitHub CLI (`gh`) authenticated, or `GITHUB_TOKEN` environment variable

## Features

- Total contributions breakdown (commits, PRs, issues, reviews)
- Contribution streaks (current and longest)
- Monthly activity visualization
- Top repositories by commit count
- Multi-year comparison support
