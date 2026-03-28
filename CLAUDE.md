# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python CLI tool that fetches and displays movie lists (now playing, popular, top rated, upcoming) from The Movie Database (TMDB) API v3. Supports table and JSON output formats.

## Commands

- **Install (editable + dev deps):** `pip install -e ".[dev]"`
- **Run:** `tmdb-cli --type <playing|popular|top|upcoming> [--page N] [--format table|json]`
- **Run without install:** `python tmdb_app.py --type popular`
- **Run tests:** `pytest tests/ -v`

## Environment

Requires `TMDB_API_KEY` env var. Can be set in a `.env` file (auto-loaded via python-dotenv).

## Architecture

```
tmdb_cli/
  __init__.py      # Package version
  client.py        # TMDBClient class, ENDPOINTS dict, BASE_URL
  formatter.py     # format_movies() pure function (text table output)
  cli.py           # parse_args(), main(), main_entry() — CLI entry point
tmdb_app.py        # Compatibility shim → delegates to tmdb_cli.cli
bin/tmdb-app       # Bash wrapper (legacy)
pyproject.toml     # Package config, entry point: tmdb-cli
tests/             # pytest suite: test_client, test_formatter, test_cli
```

- `TMDBClient.get_movies(category, page)` is the single API method — categories map to endpoints via the `ENDPOINTS` dict
- `main()` accepts `argv` for testability and returns int exit codes (0=success, 1=API error, 2=missing key)
- The `tmdb-cli` console script is installed via `pyproject.toml [project.scripts]`
