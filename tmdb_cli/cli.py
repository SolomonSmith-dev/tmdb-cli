import json
import os
import sys
import argparse
from typing import List, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from tmdb_cli.client import TMDBClient
from tmdb_cli.formatter import format_movies, print_movies


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TMDB CLI - fetch movie lists from TMDB"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--type",
        choices=["playing", "popular", "top", "upcoming"],
        help="Type of movie list to fetch",
    )
    source.add_argument(
        "--search",
        metavar="QUERY",
        help="Search movies by title",
    )
    parser.add_argument(
        "--page", type=int, default=1, help="Page of results to fetch (default: 1)"
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    args = parser.parse_args(argv)
    if args.page < 1:
        parser.error("--page must be >= 1")
    return args


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    if load_dotenv:
        load_dotenv()

    api_key = os.environ.get("TMDB_API_KEY")
    if not api_key:
        print("Error: TMDB_API_KEY environment variable not set.")
        print("Get an API key from https://www.themoviedb.org/")
        return 2

    client = TMDBClient(api_key)

    try:
        if args.search:
            data = client.search_movies(args.search, args.page)
        else:
            data = client.get_movies(args.type, args.page)
        results = data.get("results", [])
        if not results:
            print("No results returned.")
            return 0

        if args.format == "json":
            print(json.dumps(results, indent=2))
        elif sys.stdout.isatty():
            print_movies(results)
        else:
            print(format_movies(results))
        return 0
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1


def main_entry():
    sys.exit(main())
