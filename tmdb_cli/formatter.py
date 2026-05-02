from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table


def build_table(movies: List[Dict[str, Any]]) -> Table:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Title", style="white", max_width=50, overflow="fold")
    table.add_column("Release", style="dim", width=10)
    table.add_column("Rating", justify="right", style="green", width=6)

    for m in movies:
        title = m.get("title") or m.get("name") or ""
        release = m.get("release_date") or "-"
        vote = m.get("vote_average")
        rating = f"{vote:.1f}" if isinstance(vote, (int, float)) else "-"
        table.add_row(title, release, rating)

    return table


def format_movies(movies: List[Dict[str, Any]]) -> str:
    """Render the movie table as a plain string (no ANSI). Safe for piping and tests."""
    console = Console(record=True, width=100, color_system=None)
    console.print(build_table(movies))
    return console.export_text().rstrip()


def print_movies(movies: List[Dict[str, Any]]) -> None:
    """Print the movie table to stdout, with color when stdout is a TTY."""
    Console().print(build_table(movies))
