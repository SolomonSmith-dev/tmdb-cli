# TMDB CLI — Polish to v0.2.0

**Started:** 2026-05-01
**Goal:** Close out README roadmap (search + rich) so this repo is portfolio-ready and can be set down.
**Out of scope:** PyPI publish, watchlist persistence, movie detail view, genre filtering.

## Scope (single PR)

1. `--search "query"` flag — calls TMDB `/search/movie`, mutually exclusive with `--type`.
2. Replace plain-text table formatter with `rich.Table` for colored terminal output. Degrades to plain text when stdout is not a tty (safe for piping into `jq`, etc.).
3. README: check off roadmap items, add `--search` example.

## Files touched

- `tmdb_cli/client.py` — add `search_movies(query, page)`
- `tmdb_cli/cli.py` — add `--search` arg in mutex group with `--type`
- `tmdb_cli/formatter.py` — rewrite using `rich.Table`, keep `format_movies(movies) -> str` signature
- `pyproject.toml` — add `rich>=13.0` dependency
- `tests/test_client.py` — add search tests
- `tests/test_cli.py` — add search-flag tests, mutex enforcement
- `tests/test_formatter.py` — rewrite assertions for rich output
- `README.md` — roadmap checkboxes + usage examples

## Done when

- All tests pass (target: ~30 tests, up from 23)
- Manual smoke: `tmdb-cli --search "inception"` prints colored table in terminal
- Manual smoke: `tmdb-cli --search "inception" --format json | jq '.[0].title'` works (no color leak)
- PR opened against `main`

## Resume notes

If interrupted: check `TaskList` for current step. Tests are the gate — if they pass, the feature works.
