"""GitHub API client for fetching contribution metrics."""
import os
import subprocess
from datetime import datetime
from typing import Any

import requests


def get_github_token() -> str:
    """Get GitHub token from environment or gh CLI."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token

    # Try gh CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(
            "GitHub token not found. Set GITHUB_TOKEN or login with `gh auth login`"
        )


def get_username() -> str:
    """Get authenticated user's username."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("Could not determine GitHub username")


class GitHubAPI:
    """GitHub GraphQL API client."""

    GRAPHQL_URL = "https://api.github.com/graphql"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def query(self, query: str, variables: dict[str, Any] | None = None) -> dict:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(
            self.GRAPHQL_URL,
            headers=self.headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")

        return data["data"]

    def get_contribution_calendar(self, username: str, year: int) -> dict:
        """Get contribution calendar for a specific year."""
        # GitHub contribution calendar query
        query = """
        query($username: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $username) {
                contributionsCollection(from: $from, to: $to) {
                    totalCommitContributions
                    totalIssueContributions
                    totalPullRequestContributions
                    totalPullRequestReviewContributions
                    totalRepositoriesWithContributedCommits
                    contributionCalendar {
                        totalContributions
                        weeks {
                            contributionDays {
                                date
                                contributionCount
                                weekday
                            }
                        }
                    }
                    commitContributionsByRepository(maxRepositories: 100) {
                        repository {
                            nameWithOwner
                            isPrivate
                        }
                        contributions {
                            totalCount
                        }
                    }
                }
            }
        }
        """

        from_date = f"{year}-01-01T00:00:00Z"
        to_date = f"{year}-12-31T23:59:59Z"

        # Clamp to current date if year is current year
        now = datetime.utcnow()
        if year == now.year:
            to_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        variables = {
            "username": username,
            "from": from_date,
            "to": to_date,
        }

        return self.query(query, variables)

    def get_user_stats(self, username: str, year: int) -> dict:
        """Get comprehensive user statistics for a year."""
        data = self.get_contribution_calendar(username, year)

        if not data.get("user"):
            raise RuntimeError(f"User '{username}' not found")

        collection = data["user"]["contributionsCollection"]
        calendar = collection["contributionCalendar"]

        # Calculate streaks
        all_days = []
        for week in calendar["weeks"]:
            for day in week["contributionDays"]:
                all_days.append(day)

        current_streak = 0
        max_streak = 0
        temp_streak = 0

        for day in all_days:
            if day["contributionCount"] > 0:
                temp_streak += 1
                max_streak = max(max_streak, temp_streak)
            else:
                temp_streak = 0

        # Current streak (from most recent day backwards)
        for day in reversed(all_days):
            if day["contributionCount"] > 0:
                current_streak += 1
            else:
                break

        # Top repositories
        repos = collection.get("commitContributionsByRepository", [])
        top_repos = sorted(
            repos,
            key=lambda r: r["contributions"]["totalCount"],
            reverse=True
        )[:10]

        return {
            "year": year,
            "total_contributions": calendar["totalContributions"],
            "commits": collection["totalCommitContributions"],
            "issues": collection["totalIssueContributions"],
            "pull_requests": collection["totalPullRequestContributions"],
            "reviews": collection["totalPullRequestReviewContributions"],
            "repositories_contributed": collection["totalRepositoriesWithContributedCommits"],
            "current_streak": current_streak,
            "max_streak": max_streak,
            "top_repositories": [
                {
                    "name": r["repository"]["nameWithOwner"],
                    "private": r["repository"]["isPrivate"],
                    "commits": r["contributions"]["totalCount"],
                }
                for r in top_repos
            ],
            "daily_contributions": all_days,
        }
