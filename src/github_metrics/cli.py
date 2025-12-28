"""CLI for GitHub Metrics."""
import sys
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .api import GitHubAPI, get_github_token, get_username


console = Console()


def create_contribution_graph(daily_contributions: list[dict], year: int) -> str:
    """Create ASCII contribution graph."""
    # Group by month
    months = {}
    for day in daily_contributions:
        date = datetime.strptime(day["date"], "%Y-%m-%d")
        month_key = date.strftime("%Y-%m")
        if month_key not in months:
            months[month_key] = []
        months[month_key].append(day["contributionCount"])

    # Simple intensity mapping
    def intensity(count: int) -> str:
        if count == 0:
            return "░"
        elif count <= 3:
            return "▒"
        elif count <= 6:
            return "▓"
        else:
            return "█"

    lines = []
    for month_key in sorted(months.keys()):
        month_name = datetime.strptime(month_key, "%Y-%m").strftime("%b")
        counts = months[month_key]
        graph = "".join(intensity(c) for c in counts)
        total = sum(counts)
        lines.append(f"{month_name}: {graph} ({total})")

    return "\n".join(lines)


def print_year_report(stats: dict, username: str) -> None:
    """Print a formatted report for a year."""
    year = stats["year"]

    # Header
    console.print()
    console.print(Panel(
        f"[bold cyan]GitHub Metrics Report[/bold cyan]\n"
        f"[dim]@{username} - {year}[/dim]",
        expand=False
    ))

    # Summary table
    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column("Metric", style="dim")
    summary.add_column("Value", style="bold green")

    summary.add_row("Total Contributions", f"{stats['total_contributions']:,}")
    summary.add_row("Commits", f"{stats['commits']:,}")
    summary.add_row("Pull Requests", f"{stats['pull_requests']:,}")
    summary.add_row("Issues", f"{stats['issues']:,}")
    summary.add_row("Code Reviews", f"{stats['reviews']:,}")
    summary.add_row("Repositories", f"{stats['repositories_contributed']:,}")
    summary.add_row("Current Streak", f"{stats['current_streak']} days")
    summary.add_row("Longest Streak", f"{stats['max_streak']} days")

    console.print(summary)

    # Contribution graph
    if stats["daily_contributions"]:
        console.print()
        console.print("[bold]Monthly Activity[/bold]")
        graph = create_contribution_graph(stats["daily_contributions"], year)
        console.print(Text(graph, style="green"))

    # Top repositories
    if stats["top_repositories"]:
        console.print()
        repo_table = Table(title="Top Repositories", show_lines=False)
        repo_table.add_column("Repository", style="cyan")
        repo_table.add_column("Commits", justify="right", style="green")
        repo_table.add_column("Type", style="dim")

        for repo in stats["top_repositories"][:5]:
            visibility = "private" if repo["private"] else "public"
            repo_table.add_row(
                repo["name"],
                str(repo["commits"]),
                visibility
            )

        console.print(repo_table)


@click.command()
@click.option("--year", "-y", multiple=True, type=int, help="Year(s) to report (can specify multiple)")
@click.option("--username", "-u", help="GitHub username (defaults to authenticated user)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def create_report(year: tuple[int, ...], username: str | None, output_json: bool) -> None:
    """Generate GitHub contribution metrics report."""
    try:
        token = get_github_token()
        api = GitHubAPI(token)

        if not username:
            username = get_username()

        years = list(year) if year else [datetime.now().year]

        if output_json:
            import json
            results = []
            for y in years:
                stats = api.get_user_stats(username, y)
                # Remove daily_contributions for cleaner JSON
                stats.pop("daily_contributions", None)
                results.append(stats)
            console.print_json(json.dumps(results, indent=2))
        else:
            console.print(f"[dim]Fetching metrics for @{username}...[/dim]")
            for y in sorted(years):
                try:
                    stats = api.get_user_stats(username, y)
                    print_year_report(stats, username)
                except Exception as e:
                    console.print(f"[red]Error fetching {y}: {e}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@click.group()
def main():
    """GitHub Metrics CLI tool."""
    pass


main.add_command(create_report, name="create-report")


if __name__ == "__main__":
    main()
