#!/usr/bin/env python3
"""
Simple TMDB CLI app

Usage examples:
  tmdb-app --type playing
  tmdb-app --type popular
  tmdb-app --type top
  tmdb-app --type upcoming

Set the environment variable TMDB_API_KEY to your TMDB API key before running.
"""
import os
import sys
import argparse
import requests
from typing import Any, Dict, List, Optional
try:
    # optional dependency to load .env files
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


BASE_URL = "https://api.themoviedb.org/3/movie"


class TMDBClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
        params["api_key"] = self.api_key

        url = f"{BASE_URL}/{path}"
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Network/API error: {e}") from e

    def get_now_playing(self) -> Dict[str, Any]:
        return self._get("now_playing")

    def get_popular(self) -> Dict[str, Any]:
        return self._get("popular")

    def get_top_rated(self) -> Dict[str, Any]:
        return self._get("top_rated")

    def get_upcoming(self) -> Dict[str, Any]:
        return self._get("upcoming")


def format_movies(movies: List[Dict[str, Any]]) -> str:
    # Create a simple table-like string
    lines = []
    header = f"{'Title':40} | {'Release Date':10} | {'Rating':6}"
    sep = "-" * len(header)
    lines.append(header)
    lines.append(sep)
    for m in movies:
        title = (m.get("title") or m.get("name") or "")[:40]
        release = m.get("release_date", "-")
        vote = m.get("vote_average", "-")
        lines.append(f"{title:40} | {release:10} | {vote:6}")
    return "\n".join(lines)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TMDB CLI - fetch movie lists from TMDB")
    parser.add_argument("--type", required=True, choices=["playing", "popular", "top", "upcoming"], help="Type of movies to fetch")
    parser.add_argument("--page", type=int, default=1, help="Page of results to fetch (default: 1)")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    # load .env if python-dotenv is available
    if load_dotenv:
        load_dotenv()

    api_key = os.environ.get("TMDB_API_KEY")
    if not api_key:
        print("Error: TMDB_API_KEY environment variable not set.")
        print("Get an API key from https://www.themoviedb.org/")
        return 2

    client = TMDBClient(api_key)

    try:
        if args.type == "playing":
            data = client.get_now_playing()
        elif args.type == "popular":
            data = client.get_popular()
        elif args.type == "top":
            data = client.get_top_rated()
        elif args.type == "upcoming":
            data = client.get_upcoming()
        else:
            print(f"Unknown type: {args.type}")
            return 3

        results = data.get("results", [])
        if not results:
            print("No results returned.")
            return 0

        print(format_movies(results))
        return 0
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
