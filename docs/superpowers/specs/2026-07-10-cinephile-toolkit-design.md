# TMDB CLI v0.3.0: Cinephile Toolkit — Design Specification

**Date:** 2026-07-10  
**Project:** tmdb-cli  
**Status:** Approved for implementation  

---

## Executive Summary

Transform tmdb-cli from a simple movie browser into a **cinephile toolkit** for advanced discovery, tracking, and film analysis. Hybrid interface: interactive TUI for exploration + scriptable CLI for automation. Local SQLite persistence enables watchlists, ratings, and a user-contributed influence graph that maps directional relationships between films.

---

## Goals & Success Criteria

### Primary Goals
1. Enable complex, multi-criteria filtering (genre, director, actor, year range, rating threshold, vote count)
2. Persistent watchlist with ratings, watched status, and notes
3. Bidirectional influence graph (what influenced X, what did X influence)
4. Export to CSV, Markdown, JSON for external use
5. Hybrid UI: TUI-first for discovery, CLI for scripting and automation

### Success Criteria
- [ ] Filter by 5+ criteria simultaneously (genre + director + year + rating + vote_count)
- [ ] Watchlist persists, sortable/filterable across sessions
- [ ] Influence chains traversable in both directions (influenced_by, influences) to arbitrary depth
- [ ] TUI responsive and intuitive for exploration workflows
- [ ] CLI fully scriptable; all data exportable as JSON
- [ ] Export watchlist + influence graph to CSV for external use

---

## Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────────────────┐
│  Presentation Layer                                 │
│  ├─ TUI (rich-based interactive)  [DEFAULT]        │
│  └─ CLI (argparse/click + JSON)   [--cli flag]     │
├─────────────────────────────────────────────────────┤
│  Business Logic Layer                               │
│  ├─ QueryBuilder (filtering, sorting)              │
│  ├─ InfluenceGraph (bidirectional relationships)   │
│  ├─ ExportFormatter (CSV, Markdown, JSON)          │
│  └─ TMDBClient (API, caching)                      │
├─────────────────────────────────────────────────────┤
│  Data Layer                                         │
│  └─ SQLite (~/.tmdb-cli/tmdb.db)                   │
│     ├─ movies (cached from API)                    │
│     ├─ watchlist (user's list + ratings)           │
│     └─ influence (user-created edges)              │
└─────────────────────────────────────────────────────┘
```

### Key Design Principles

- **Separation of concerns:** TUI and CLI are presentation layers; both consume the same business logic
- **Data-centric:** SQLite is source-of-truth for user data (watchlist, ratings, influence)
- **API caching:** Movies fetched from TMDB are cached locally to minimize API calls
- **Composable:** QueryBuilder and InfluenceGraph are testable, reusable modules

---

## Data Model

### SQLite Schema

#### `movies` table
Cached results from TMDB API. Updated on-demand when user searches or browses.

```sql
CREATE TABLE movies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tmdb_id INTEGER UNIQUE NOT NULL,
  title TEXT NOT NULL,
  release_date DATE,
  genres JSON,                -- ["Action", "Sci-Fi"]
  directors JSON,             -- ["Christopher Nolan", "...]
  cast JSON,                  -- Top 5-10 cast members
  rating FLOAT,               -- Vote average from TMDB
  vote_count INTEGER,         -- Total votes
  overview TEXT,
  poster_path TEXT,           -- Relative URL for display
  cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `watchlist` table
User's personal list with ratings and watched status.

```sql
CREATE TABLE watchlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  movie_id INTEGER NOT NULL UNIQUE,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  user_rating INTEGER CHECK (user_rating IS NULL OR (user_rating >= 1 AND user_rating <= 10)),
  watched_date DATE,          -- NULL = not watched
  notes TEXT,
  FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
);
```

#### `influence` table
Bidirectional relationships between films. Users create edges manually.

```sql
CREATE TABLE influence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_movie_id INTEGER NOT NULL,
  target_movie_id INTEGER NOT NULL,
  relationship TEXT CHECK (relationship IN ('influenced_by', 'influences')),
  user_note TEXT,             -- Optional context ("inspired the time-heist genre")
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_movie_id, target_movie_id, relationship),
  FOREIGN KEY (source_movie_id) REFERENCES movies(id) ON DELETE CASCADE,
  FOREIGN KEY (target_movie_id) REFERENCES movies(id) ON DELETE CASCADE
);
```

#### Database Location
`~/.tmdb-cli/tmdb.db` — user's home directory, persistent across sessions.

---

## Core Components

### 1. QueryBuilder
Fluent interface for constructing complex queries against local `movies` and `watchlist` tables.

**Filters:**
- `filter_genre(genres: List[str])` — match any genre
- `filter_director(names: List[str])` — match any director
- `filter_actor(names: List[str])` — match any cast member
- `filter_year(min: int, max: int)` — release year range
- `filter_rating_min(threshold: float)` — vote_average >= threshold
- `filter_vote_count_min(count: int)` — vote_count >= count
- `filter_watched(watched: bool)` — True = on watchlist and watched_date IS NOT NULL
- `filter_in_watchlist(in_list: bool)` — on/off watchlist

**Sorting:**
- `sort_by(criteria: List[Tuple[str, "asc"|"desc"]])` — multi-column sort
  - Supported columns: rating, release_date, vote_count, added_at, user_rating

**Execution:**
- `execute() -> List[Dict]` — returns result set as dicts with all fields

**Example:**
```python
results = (QueryBuilder(db)
  .filter_genre(["Sci-Fi"])
  .filter_year(2010, 2023)
  .filter_director(["Christopher Nolan"])
  .filter_rating_min(7.5)
  .filter_watched(False)
  .sort_by([("rating", "desc"), ("release_date", "asc")])
  .execute())
```

### 2. InfluenceGraph
Manages bidirectional influence relationships.

**Methods:**
- `add_influence(source_title: str, relationship: "influenced_by"|"influences", target_title: str, note: str = None)`
  - Converts titles to IDs, creates edge in both directions (A influenced_by B ↔ B influences A)
- `get_ancestors(movie_title: str, depth: int = 3) -> List[Dict]`
  - Traverses "influenced_by" edges recursively (what influenced this film)
- `get_descendants(movie_title: str, depth: int = 3) -> List[Dict]`
  - Traverses "influences" edges recursively (what did this film influence)
- `get_chain(movie_title: str, direction: "ancestors"|"descendants", depth: int) -> Dict`
  - Returns structured chain with metadata and notes

**Data Structure (returned from `get_chain`):**
```python
{
  "root": {"tmdb_id": 27205, "title": "Inception", "rating": 8.8},
  "chain": [
    {
      "level": 1,
      "movies": [
        {"id": 240, "title": "2001: A Space Odyssey", "note": "pioneering sci-fi"},
        {"id": 278, "title": "The Shawshank Redemption", "note": "narrative structure"}
      ]
    },
    {
      "level": 2,
      "movies": [...]
    }
  ],
  "total_films": 42
}
```

### 3. ExportFormatter
Multi-format export for watchlists and influence graphs.

**Methods:**
- `to_csv(movies: List[Dict], title: str = None) -> str`
  - Headers: title, release_date, rating, user_rating, watched_date, genres, directors
- `to_markdown(movies: List[Dict], title: str = None) -> str`
  - Markdown table format, optionally with title and metadata
- `to_json(movies: List[Dict]) -> str`
  - Full JSON with all fields

**Export influence graph:**
- `export_influence_chain(root_title: str, direction: str, depth: int, format: str) -> str`

---

## User Interface

### TUI Mode (Default)

**Invocation:** `tmdb-cli` (no arguments)

**Main Menu:**
```
┌────────────────────────────────────────────────────┐
│  TMDB Cinephile Toolkit v0.3.0                    │
├────────────────────────────────────────────────────┤
│ [S]earch  [W]atchlist  [I]nfluence  [E]xport  [H]elp
├────────────────────────────────────────────────────┤
│ > _
```

**Search Flow:**
1. User types movie title
2. Results displayed in scrollable rich Table (title, release_date, rating, genres)
3. Arrow keys to navigate, Enter to select
4. Detail view: full info + actions
   - **A** = Add to watchlist
   - **R** = Rate (1-10)
   - **I** = Add influence link
   - **B** = Back to results
   - **W** = Mark watched
   - **E** = Export this movie's influence chain

**Watchlist View:**
- Scrollable table: title, user_rating, watched_date, genres
- Press **F** to filter (opens filter panel with checkboxes)
- Press **S** to sort (opens sort menu)
- Press **D** to delete from watchlist
- Press **I** to view/edit influence for selected movie

**Influence Mode:**
1. Enter movie title
2. Choose direction: "What influenced this?" or "What did this influence?"
3. Choose depth (1-5)
4. Display chain as tree diagram (using rich.tree)
5. Navigate chain, add/edit relationships

**Export Panel:**
- Choose format: CSV, Markdown, JSON
- Choose source: Watchlist or Influence chain
- Destination: filename, default to current directory

**Interaction Model:**
- **Arrow keys:** Navigate lists
- **Enter:** Select/open
- **Q:** Quit/back
- **H:** Contextual help (always available)
- **?:** Show keybinds

### CLI Mode (Scriptable)

**Invocation:** `tmdb-cli --cli [command] [args]`

All commands return JSON (with `--json` flag), plain text otherwise.

#### Search
```bash
tmdb-cli --cli search "Inception" 
  --genre scifi 
  --year-min 2010 
  --year-max 2023 
  --rating-min 7.5 
  --sort rating:desc,release_date:asc 
  --format json
```

Returns: JSON array of matching movies

#### Watchlist Management
```bash
# Add
tmdb-cli --cli watchlist add "Inception"

# Rate
tmdb-cli --cli watchlist rate "Inception" 9

# List (with filtering)
tmdb-cli --cli watchlist list 
  --genre drama 
  --watched false 
  --format json

# Remove
tmdb-cli --cli watchlist remove "Inception"
```

#### Influence
```bash
# Add relationship
tmdb-cli --cli influence add "Inception" "influenced_by" "2001: A Space Odyssey" --note "pioneering narrative structure"

# Query ancestors (what influenced X)
tmdb-cli --cli influence ancestors "Inception" --depth 3 --format json

# Query descendants (what did X influence)
tmdb-cli --cli influence descendants "Inception" --depth 3 --format json

# Show chain
tmdb-cli --cli influence chain "Inception" --direction ancestors --depth 3 --format json
```

Returns: JSON structure from InfluenceGraph.get_chain()

#### Export
```bash
# Export watchlist
tmdb-cli --cli export watchlist --format csv > my-watchlist.csv
tmdb-cli --cli export watchlist --format markdown > my-list.md

# Export influence chain
tmdb-cli --cli export influence "Inception" --direction ancestors --depth 3 --format csv
```

**JSON piping examples:**
```bash
# Find highest-rated drama in watchlist
tmdb-cli --cli watchlist list --format json | jq '.[] | select(.genres[] | contains("Drama")) | sort_by(.user_rating)[-1]'

# Get all sci-fi movies from TMDB popular list, filter locally
tmdb-cli --cli search "" --genre scifi --format json | jq 'map(select(.rating > 7.5))'
```

---

## Influence System Design

### Principles
- **User-contributed:** No automatic linking; users manually create edges
- **Bidirectional:** "A influenced_by B" creates both directions in the DB
- **Queryable:** Can traverse ancestors (sources) and descendants (results)
- **Contextual:** Users can attach notes explaining the relationship
- **Persistent:** All relationships stored locally; users build their knowledge graph over time

### Workflow Examples

**Discovering Nolan's influences:**
1. Search "Inception" → view influence → choose "ancestors"
2. See: 2001: A Space Odyssey (pioneering), Memento (narrative), etc.
3. Navigate deeper: what influenced 2001?
4. Build understanding of the lineage

**Tracking a director's impact:**
1. Add "Inception" → influences → "The Dark Knight Rises"
2. Add "Inception" → influences → "Interstellar"
3. Later, view descendants of "Inception" to see all inspired work

**Collaborative growth (future):**
- Export influence graph as JSON
- Share with friends; they add relationships locally
- Merge graphs (not in v0.3.0, but architecture supports it)

---

## Implementation Phases

### Phase 1: MVP (Core Features)
1. SQLite schema, migrations, initialization
2. QueryBuilder + sorting
3. Watchlist (add, rate, list, remove)
4. Export (CSV, Markdown, JSON)
5. InfluenceGraph basic add/query
6. TUI skeleton (main menu, search, results table, watchlist view)
7. CLI scaffold (all commands wired, JSON output)

### Phase 2: Polish & UI
1. TUI influence graph visualization
2. TUI filter/sort panels
3. Better error handling and validation
4. Help text and documentation
5. Edge cases (duplicate movies, circular influences)

### Phase 3: Advanced (Future)
- Recommend movies based on influence chains
- Graph visualization (export to DOT, render as image)
- Collaborative influence sharing
- Integration with IMDb/Wikipedia for richer metadata

---

## Technology Stack

| Component | Tool | Notes |
|-----------|------|-------|
| **TUI** | `rich` (Tables, Live, Tree, Prompt) | Already in dependencies; powerful widgets |
| **CLI** | `argparse` (or `click` for simpler composition) | Familiar; stdlib or minimal dependency |
| **DB** | `sqlite3` (stdlib) | No external DB; perfect for local persistence |
| **Export** | `csv`, `json` (stdlib) | Native Python libraries |
| **API** | `requests` (existing) | No changes; add response caching |

**No new dependencies beyond what's already in pyproject.toml.** `rich` is already there; `sqlite3` is stdlib.

---

## Testing Strategy

- **Unit tests:** QueryBuilder (filter + sort combinations), ExportFormatter (CSV/JSON output)
- **Integration tests:** Add/query watchlist, influence relationships
- **CLI tests:** All commands with sample data, JSON output validation
- **TUI tests:** Manual; verify keybinds and navigation (hard to automate)

---

## Known Unknowns / Future Decisions

1. **Movie matching:** How to handle typos/variants in titles? (e.g., "Inception" vs. "Inception: The Cobol Job")
   - *Current assumption:* Use fuzzy matching or require TMDB ID for influence links
2. **Influence graph UI:** Tree diagram vs. graph visualization?
   - *Current assumption:* Tree diagram in TUI; graph export as future feature
3. **API key caching:** Should API responses be cached for X hours?
   - *Current assumption:* Cache indefinitely until user updates (simple approach)

---

## Success Metrics (Post-Implementation)

- [ ] Can construct a 10+ movie influence chain with < 1 second query time
- [ ] Watchlist with 100+ movies loads in < 500ms
- [ ] TUI responsive on all keybinds (no lag)
- [ ] CLI exports are valid JSON/CSV
- [ ] All core workflows testable without manual intervention

---

## Appendix: File Structure (Post-Implementation)

```
tmdb_cli/
  __init__.py
  cli.py                    # CLI entry point (both TUI and --cli modes)
  client.py                 # TMDBClient (existing, extend with caching)
  formatter.py              # Plain text table formatter (existing)
  
  db/
    __init__.py
    schema.py               # SQLite schema + migrations
    query_builder.py        # QueryBuilder class
    influence.py            # InfluenceGraph class
  
  export/
    __init__.py
    formatter.py            # ExportFormatter (CSV, Markdown, JSON)
  
  tui/
    __init__.py
    app.py                  # Main TUI entry point
    screens.py              # Individual screens (search, watchlist, influence)
    keybinds.py             # Keybind definitions
  
  cli/
    __init__.py
    commands.py             # All --cli subcommands

tests/
  test_query_builder.py
  test_influence.py
  test_export.py
  test_cli_commands.py
  test_tui_screens.py (mostly manual)
```

---

## Approval Checklist

- [x] Scope is clear and focused
- [x] Architecture is coherent (three layers, single data source)
- [x] Data model handles all use cases
- [x] TUI and CLI flows are intuitive
- [x] Influence system is bidirectional and queryable
- [x] No missing pieces (filtering, sorting, persistence, export, UI)
- [x] Tech stack is minimal and proven
- [x] Success criteria are measurable
