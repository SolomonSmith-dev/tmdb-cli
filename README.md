# TMDB CLI

A command-line tool to browse movie listings from [The Movie Database (TMDB)](https://www.themoviedb.org/). Fetch now-playing, popular, top-rated, and upcoming movies directly in your terminal.

## Demo

```
$ tmdb-app --type popular

Title                                    | Release    | Rating
-----------------------------------------------------------------
The Shawshank Redemption                 | 1994-09-23 |    8.7
The Godfather                            | 1972-03-14 |    8.7
The Dark Knight                          | 2008-07-16 |    8.5
...
```

## Quick Start

### Prerequisites

- Python 3.8+
- A free TMDB API key ([get one here](https://www.themoviedb.org/settings/api))

### Setup

```bash
# Clone the repo
git clone https://github.com/<your-username>/TMDB-CLI-tool.git
cd TMDB-CLI-tool

# Install dependencies
pip install -r requirements.txt

# Set your API key (option A: environment variable)
export TMDB_API_KEY=your_api_key_here

# Set your API key (option B: .env file)
echo "TMDB_API_KEY=your_api_key_here" > .env
```

### Usage

```bash
# Browse movie categories
./bin/tmdb-app --type playing     # Now playing in theaters
./bin/tmdb-app --type popular     # Popular movies
./bin/tmdb-app --type top         # Top rated of all time
./bin/tmdb-app --type upcoming    # Upcoming releases

# Pagination
./bin/tmdb-app --type popular --page 2
```

## Tech Stack

| Tool | Purpose |
|---|---|
| **Python 3** | Core language |
| **requests** | HTTP client for TMDB API v3 |
| **argparse** | CLI argument parsing (stdlib) |
| **python-dotenv** | Load API key from `.env` file |

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
- [ ] Add movie search by title (`--search "inception"`)
- [ ] Add colored terminal output with `rich`

## License

MIT
