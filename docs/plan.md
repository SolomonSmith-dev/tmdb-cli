# Plan — TMDB CLI v0.2.0 Polish

**Scope:** finish the `polish/search-and-rich` branch. Source code (cli/client/formatter/pyproject) is already edited; tests and docs are not. Two existing tests are silently broken by the source changes.

**Target:** `~30 tests passing`, README updated, PR opened against `main`, version bumped to `0.2.0`.

---

## Phase 0 — Discovery (read-only, single session)

Goal: confirm the APIs we're about to call actually exist with the signatures we assume. No code edits.

### 0.1 Rich library
- Confirm `rich.console.Console(record=True, width=N, color_system=None)` + `console.print(table)` + `console.export_text()` is the documented pattern for capturing tableless ANSI-stripped output.
- Source of truth: https://rich.readthedocs.io/en/stable/console.html#recording (and `Table` reference).
- Output: list of allowed APIs in this file under "Allowed APIs" once verified.

### 0.2 TMDB `/search/movie` endpoint
- Confirm the endpoint path is `search/movie` (already used in `tmdb_cli/client.py:38`).
- Confirm required params: `api_key`, `query`. Optional: `page`, `include_adult`, `language`.
- Source: https://developer.themoviedb.org/reference/search-movie
- Output: confirm response shape matches `{"results": [...]}` like other endpoints.

### 0.3 Existing test breakage audit
Two known broken assumptions to verify:
- `tests/test_client.py:19` asserts URL `f"{BASE_URL}/popular"` but `client.py:34` now resolves to `f"{BASE_URL}/movie/popular"` via `ENDPOINTS["popular"]`. **Test is broken pre-existing.**
- `tests/test_formatter.py` asserts plain-text structure (`|` separators, exact line counts, header+separator). The new `format_movies` returns a `rich.Table` rendered via `Console.export_text()` which uses Unicode box characters, not `|`. **All five tests will fail.**

Confirm by running `pytest tests/ -v` once and capturing the failure list.

### Allowed APIs (fill in after 0.1–0.3)
- `rich.console.Console(record=True, width=int, color_system=None)`
- `Console.print(renderable)`
- `Console.export_text() -> str`
- `rich.table.Table(show_header=bool, header_style=str)` + `add_column(...)` + `add_row(...)`
- TMDB: `GET /search/movie?api_key=...&query=...&page=...`

### Anti-patterns to avoid
- Do **not** assert on specific Unicode box characters in formatter tests — assert on data content (titles, dates, ratings) instead. Rich may change box defaults across versions.
- Do **not** add `include_adult` or `language` params to `search_movies` — out of scope.
- Do **not** invent `Console.export_html()` or other unverified methods.

---

## Phase 1 — Fix the broken tests + add search tests

**Files:** `tests/test_client.py`, `tests/test_cli.py`, `tests/test_formatter.py`

### 1.1 `tests/test_client.py`
- Fix `test_url_construction`: change expected URL to `f"{BASE_URL}/movie/popular"`.
- Add `test_search_url_construction`: mock `requests.get`, call `client.search_movies("inception", page=2)`, assert called with `f"{BASE_URL}/search/movie"` and `params={"query": "inception", "page": 2, "api_key": "test-key"}`.
- Add `test_search_network_error_raises_runtime`: parallels existing network-error test but for `search_movies`.

### 1.2 `tests/test_cli.py`
- Add `TestParseArgs.test_valid_search`: `parse_args(["--search", "inception"])` → `args.search == "inception"`, `args.type is None`.
- Add `TestParseArgs.test_search_and_type_mutex_exits`: `parse_args(["--type", "popular", "--search", "x"])` raises `SystemExit`.
- Add `TestParseArgs.test_search_with_page`: `parse_args(["--search", "x", "--page", "2"])` → `args.page == 2`.
- Add `TestMain.test_successful_search`: mock `TMDBClient.search_movies` to return one result, call `main(["--search", "inception"])`, assert exit 0 and title appears in stdout. Mirror existing `test_successful_fetch`.

### 1.3 `tests/test_formatter.py`
Rewrite all assertions to be **content-based**, not structure-based:
- `test_format_movies_single`: keep — already content-based, will still pass with rich (substring checks for "Inception", "2010-07-16", "8.4").
- `test_format_movies_empty`: replace line-count assertion with: output is non-empty string and contains the column headers ("Title", "Release", "Rating").
- `test_format_movies_long_title_truncated`: replace `split("|")` with: assert no single line in output exceeds the configured width (100). Title may wrap due to `overflow="fold"` — assert all 60 `A`s appear in the output but not on one line.
- `test_format_movies_missing_fields`: keep — substring checks for "Fallback Name" and "-" still hold.
- `test_format_movies_line_count`: replace exact line-count with: assert each title ("A", "B", "C") appears in the output exactly once.

### Verification
```
pytest tests/ -v
```
Target: all tests pass. Expected count: 23 existing + ~7 new = ~30.

### Anti-pattern guards
- No assertions on `|` characters or box-drawing glyphs in formatter tests.
- No assertions on exact line counts beyond "≥ N" for resilience.

---

## Phase 2 — README + version bump

**Files:** `README.md`, `pyproject.toml`, `tmdb_cli/__init__.py` (if it has `__version__`)

### 2.1 README
- Add `--search` example under "Usage":
  ```bash
  tmdb-cli --search "inception"
  tmdb-cli --search "inception" --format json | jq '.[0].title'
  ```
- Update demo block: replace ASCII `|` table with a note that output is now a colored `rich.Table` in TTY, plain text when piped.
- Find roadmap section (if exists) and check off: search support, rich output. If no roadmap section, skip.
- Update Tech Stack table: add `rich` row.
- Update Project Structure: no change (file layout is unchanged).

### 2.2 Version bump
- `pyproject.toml:8` — bump `version = "0.1.0"` → `"0.2.0"`.
- `tmdb_cli/__init__.py` — if it exposes `__version__`, sync to `"0.2.0"`. Otherwise skip.

### Verification
- `grep -n "0.2.0" pyproject.toml tmdb_cli/__init__.py 2>/dev/null` — confirm.
- Visually re-read README for the `--search` block + tech stack row.

---

## Phase 3 — Manual smoke + PR

### 3.1 Smoke tests (need `TMDB_API_KEY` in env)
```bash
pip install -e ".[dev]"
tmdb-cli --search "inception"                              # colored table
tmdb-cli --search "inception" --format json | jq '.[0].title'  # no color leak
tmdb-cli --type popular                                    # regression check
tmdb-cli --type popular --format json | jq 'length'        # regression check
```

### 3.2 Final test + lint gate
```bash
pytest tests/ -v
# whatever lint the CI workflow runs (check .github/workflows/ci.yml)
```

### 3.3 Commit + PR
- Stage only the intended files: `pyproject.toml`, `tmdb_cli/`, `tests/`, `README.md`. Do **not** stage `task-brief.md`, `plan.md`, `~/`, `.claude/` — those are untracked working notes.
- Commit message: `polish: add --search flag and rich table output (v0.2.0)`.
- Push branch, open PR against `main` via `gh pr create`. Body: link to README diff and test count delta (23 → ~30).

### Verification checklist (final)
- [ ] `pytest tests/ -v` shows all green
- [ ] `tmdb-cli --search "inception"` prints colored output in TTY
- [ ] `tmdb-cli --search "inception" --format json | jq` works without ANSI corruption
- [ ] README shows `--search` example
- [ ] `pyproject.toml` says `version = "0.2.0"`
- [ ] PR open, CI green
- [ ] `task-brief.md` and `plan.md` either deleted or kept untracked (not committed)

---

## Resume notes
- Branch: `polish/search-and-rich`. Source files already edited (uncommitted).
- Phase 1 is the only phase with real risk (test rewrites). Phases 2 and 3 are mechanical.
- If Rich's default box style changes between versions, formatter tests will be resilient because they assert on data content, not glyphs.
