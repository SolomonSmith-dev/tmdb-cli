# TMDB CLI Tool

This is a small command line interface (CLI) to fetch lists of movies from The Movie Database (TMDB) and display them in the terminal.

Requirements

- Python 3.8+
- A TMDB API key (set via the TMDB_API_KEY environment variable)
- Install dependencies: `pip install -r requirements.txt`

Usage

Run from the project root (or install the wrapper as an executable):

tmdb-app --type playing
tmdb-app --type popular
tmdb-app --type top
tmdb-app --type upcoming

You can also specify `--page N` to fetch a specific page of results.

Using a local `.env` file

You can keep your API key in a local `.env` file (recommended for local development). Create a file named `.env` in the project root with:

TMDB_API_KEY=your_v3_api_key_here

If `python-dotenv` is installed (it's listed in `requirements.txt`), the CLI will load this file automatically.

Example (using environment variable):

export TMDB_API_KEY=your_api_key_here
./bin/tmdb-app --type popular

Notes

- Handles basic network and API errors and prints a friendly message.
- This is a small demo project. Contributions welcome.
