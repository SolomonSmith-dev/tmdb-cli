# TMDB CLI

![CI](https://github.com/SolomonSmith-dev/tmdb-cli/actions/workflows/ci.yml/badge.svg) ![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg) ![Python](https://img.shields.io/badge/python-3.9+-blue.svg)

A command-line tool to browse movie listings from [The Movie Database (TMDB)](https://www.themoviedb.org/). Fetch now-playing, popular, top-rated, and upcoming movies directly in your terminal.

## Demo

```
$ tmdb-cli --type popular

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ Title                        ┃ Release    ┃ Rating ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ The Shawshank Redemption     │ 1994-09-23 │    8.7 │
│ The Godfather                │ 1972-03-14 │    8.7 │
│ The Dark Knight              │ 2008-07-16 │    8.5 │
└──────────────────────────────┴────────────┴────────┘
```

Output is colored when stdout is a TTY, and degrades to plain text automatically when piped (so `| jq` and other Unix-pipe workflows stay clean).

## Quick Start

### Prerequisites

- Python 3.9+
- A free TMDB API key ([get one here](https://www.themoviedb.org/settings/api))

### Setup

```bash
# Clone the repo
git clone https://github.com/SolomonSmith-dev/tmdb-cli.git
cd tmdb-cli

# Install the package with dev dependencies
pip install -e ".[dev]"

# Configure your API key via .env
cp .env.example .env
# Edit .env and set TMDB_API_KEY=your_api_key_here

# Or export it directly
export TMDB_API_KEY=your_api_key_here
```

### Usage

```bash
# Using the installed console script
tmdb-cli --type playing     # Now playing in theaters
tmdb-cli --type popular     # Popular movies
tmdb-cli --type top         # Top rated of all time
tmdb-cli --type upcoming    # Upcoming releases

# Or run directly with Python
python -m tmdb_app --type popular

# Search by title
tmdb-cli --search "inception"
tmdb-cli --search "dune" --page 2

# Pagination and JSON output
tmdb-cli --type popular --page 2
tmdb-cli --type top --format json

# JSON output pipes cleanly into jq (no ANSI color leak)
tmdb-cli --search "inception" --format json | jq '.[0].title'
```

## Tech Stack

| Tool | Purpose |
|---|---|
| **Python 3** | Core language |
| **requests** | HTTP client for TMDB API v3 |
| **argparse** | CLI argument parsing (stdlib) |
| **python-dotenv** | Load API key from `.env` file |
| **rich** | Colored terminal tables (with TTY detection for safe piping) |
| **pytest** | Test suite (30 tests across client, CLI, and formatter) |

## Project Structure

```
tmdb_cli/
  client.py        # TMDB API client
  formatter.py     # Table output formatter
  cli.py           # CLI entry point (argparse, main)
pyproject.toml     # Package config and entry points
tests/             # pytest test suite
bin/tmdb-app       # Shell wrapper (legacy)
```

## What I Learned

- How to design a clean API client class with separation between HTTP transport and business logic
- Working with REST APIs: query parameters, error handling, pagination
- CLI design patterns with argparse: subcommands, argument validation, exit codes
- Managing secrets via environment variables instead of hardcoding

## Roadmap

- [x] Wire up `--page` pagination
- [x] Add `--format json` output for piping to other tools
- [x] Package with `pyproject.toml` for `pip install` support
- [x] Add unit tests with pytest
- [x] Add movie search by title (`--search "inception"`)
- [x] Add colored terminal output with `rich` (auto-degrades when piped)

## License

MIT
