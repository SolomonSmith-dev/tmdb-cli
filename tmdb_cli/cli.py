import os
import sys
import argparse
from typing import List, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from tmdb_cli.client import TMDBClient
from tmdb_cli.formatter import format_movies


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TMDB CLI - fetch movie lists from TMDB")
    parser.add_argument("--type", required=True, choices=["playing", "popular", "top", "upcoming"], help="Type of movies to fetch")
    parser.add_argument("--page", type=int, default=1, help="Page of results to fetch (default: 1)")
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
        data = client.get_movies(args.type, args.page)
        results = data.get("results", [])
        if not results:
            print("No results returned.")
            return 0

        print(format_movies(results))
        return 0
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1


def main_entry():
    sys.exit(main())
