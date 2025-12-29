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


def get_month_graph(daily_contributions: list[dict], month: int) -> tuple[str, int]:
    """Get graph string and total for a specific month."""
    def intensity(count: int) -> str:
        if count == 0:
            return "░"
        elif count <= 3:
            return "▒"
        elif count <= 6:
            return "▓"
        else:
            return "█"

    counts = []
    for day in daily_contributions:
        date = datetime.strptime(day["date"], "%Y-%m-%d")
        if date.month == month:
            counts.append(day["contributionCount"])

    if not counts:
        return "░" * 31, 0

    graph = "".join(intensity(c) for c in counts)
    graph = graph.ljust(31, " ")
    return graph, sum(counts)


def print_comparison_report(all_stats: list[dict], username: str) -> None:
    """Print a comparison report for multiple years."""
    years = [s["year"] for s in all_stats]

    # Header
    console.print()
    console.print(Panel(
        f"[bold cyan]GitHub Metrics Comparison[/bold cyan]\n"
        f"[dim]@{username} - {', '.join(map(str, years))}[/dim]",
        expand=False
    ))

    # Summary comparison table
    console.print()
    summary_table = Table(title="Year-over-Year Comparison", show_lines=True)
    summary_table.add_column("Metric", style="dim")
    for year in years:
        summary_table.add_column(str(year), justify="right", style="cyan")

    metrics = [
        ("Total", "total_contributions"),
        ("  Public", "public_contributions"),
        ("  Private", "private_contributions"),
        ("Commits", "commits"),
        ("Pull Requests", "pull_requests"),
        ("Issues", "issues"),
        ("Code Reviews", "reviews"),
        ("New Repos", "new_repositories"),
        ("Longest Streak", "max_streak"),
    ]

    for label, key in metrics:
        row = [label]
        for stats in all_stats:
            value = stats.get(key, 0)
            if key == "max_streak":
                row.append(f"{value} days")
            else:
                row.append(f"{value:,}")
        summary_table.add_row(*row)

    console.print(summary_table)

    # Side-by-side monthly graphs
    console.print()
    console.print("[bold]Monthly Activity Comparison[/bold]")

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Header row
    header = "     "
    for stats in all_stats:
        header += f"  {stats['year']}                                "
    console.print(header)

    for month_idx, month_name in enumerate(month_names, 1):
        line = f"{month_name}: "
        for stats in all_stats:
            graph, total = get_month_graph(stats.get("daily_contributions", []), month_idx)
            line += f"{graph} ({total:>3})  "
        console.print(Text(line, style="green"))

    # Top repositories comparison
    console.print()
    repo_table = Table(title="Top Repositories by Year", show_lines=True)
    repo_table.add_column("Rank", style="dim", justify="center")
    for year in years:
        repo_table.add_column(str(year), style="cyan")

    max_repos = 5
    for i in range(max_repos):
        row = [f"#{i+1}"]
        for stats in all_stats:
            repos = stats.get("top_repositories", [])
            if i < len(repos):
                repo = repos[i]
                name = repo["name"].split("/")[-1]  # Short name
                row.append(f"{name} ({repo['commits']})")
            else:
                row.append("-")
        repo_table.add_row(*row)

    console.print(repo_table)


def print_single_report(stats: dict, username: str) -> None:
    """Print a formatted report for a single year."""
    year = stats["year"]

    # Header
    console.print()
    console.print(Panel(
        f"[bold cyan]GitHub Metrics Report[/bold cyan]\n"
        f"[dim]@{username} - {year}[/dim]",
        expand=False
    ))

    # Total contributions breakdown
    console.print()
    console.print(f"[bold]Total Contributions: {stats['total_contributions']:,}[/bold]")
    console.print(f"  [green]Public:  {stats['public_contributions']:,}[/green]")
    console.print(f"  [yellow]Private: {stats['private_contributions']:,}[/yellow]")

    # Public contributions breakdown
    console.print()
    console.print("[bold]Public Breakdown[/bold]")
    public_table = Table(show_header=False, box=None, padding=(0, 2))
    public_table.add_column("Metric", style="dim")
    public_table.add_column("Value", style="green")

    public_table.add_row("  Commits", f"{stats['commits']:,}")
    public_table.add_row("  Pull Requests", f"{stats['pull_requests']:,}")
    public_table.add_row("  Issues", f"{stats['issues']:,}")
    public_table.add_row("  Code Reviews", f"{stats['reviews']:,}")
    public_table.add_row("  New Repositories", f"{stats['new_repositories']:,}")

    console.print(public_table)

    # Activity stats
    console.print()
    console.print("[bold]Activity[/bold]")
    activity_table = Table(show_header=False, box=None, padding=(0, 2))
    activity_table.add_column("Metric", style="dim")
    activity_table.add_column("Value", style="cyan")

    activity_table.add_row("  Repositories Contributed", f"{stats['repositories_contributed']:,}")
    activity_table.add_row("  Current Streak", f"{stats['current_streak']} days")
    activity_table.add_row("  Longest Streak", f"{stats['max_streak']} days")

    console.print(activity_table)

    # Contribution graph
    if stats.get("daily_contributions"):
        console.print()
        console.print("[bold]Monthly Activity[/bold]")

        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        for month_idx, month_name in enumerate(month_names, 1):
            graph, total = get_month_graph(stats["daily_contributions"], month_idx)
            if total > 0 or month_idx <= datetime.now().month:
                console.print(Text(f"{month_name}: {graph} ({total:>3})", style="green"))

    # Top repositories
    if stats.get("top_repositories"):
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
@click.argument("years", nargs=-1, type=int)
@click.option("--year", "-y", multiple=True, type=int, help="Year(s) to report (legacy, use positional args)")
@click.option("--username", "-u", help="GitHub username (defaults to authenticated user)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def create_report(years: tuple[int, ...], year: tuple[int, ...], username: str | None, output_json: bool) -> None:
    """Generate GitHub contribution metrics report.

    Usage: create-report 2024 2025
    """
    try:
        token = get_github_token()
        api = GitHubAPI(token)

        if not username:
            username = get_username()

        # Combine positional args and --year options
        all_years = list(years) + list(year)
        if not all_years:
            all_years = [datetime.now().year]
        all_years = sorted(set(all_years))

        if output_json:
            import json
            results = []
            for y in all_years:
                stats = api.get_user_stats(username, y)
                stats.pop("daily_contributions", None)
                results.append(stats)
            console.print_json(json.dumps(results, indent=2))
        else:
            console.print(f"[dim]Fetching metrics for @{username}...[/dim]")

            all_stats = []
            for y in all_years:
                try:
                    stats = api.get_user_stats(username, y)
                    all_stats.append(stats)
                except Exception as e:
                    console.print(f"[red]Error fetching {y}: {e}[/red]")

            if len(all_stats) == 1:
                print_single_report(all_stats[0], username)
            elif len(all_stats) > 1:
                print_comparison_report(all_stats, username)

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
