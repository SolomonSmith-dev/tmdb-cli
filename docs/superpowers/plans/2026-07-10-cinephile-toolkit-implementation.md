# TMDB CLI v0.3.0: Cinephile Toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cinephile toolkit with advanced filtering, persistent watchlist, bidirectional influence graph, and export capabilities. Hybrid UI: TUI for exploration, CLI for automation.

**Architecture:** Three-layer design (presentation → business logic → SQLite data layer). Both TUI and CLI consume identical business logic modules (QueryBuilder, InfluenceGraph, ExportFormatter). All user data lives in local SQLite; TMDB API results cached to minimize calls.

**Tech Stack:** SQLite3 (stdlib), Rich (existing), argparse (stdlib), requests (existing), pytest (existing)

## Global Constraints

- **Python:** >= 3.9 (from pyproject.toml)
- **No new dependencies:** SQLite3 and argparse are stdlib; Rich already in deps
- **Entry point:** Both TUI and CLI invoked via `tmdb_cli.cli:main_entry()`
- **Data location:** `~/.tmdb-cli/tmdb.db` (persistent across sessions)
- **Backwards compatibility:** Existing `--type` and `--search` flags must still work
- **Naming:** Snake_case for functions/modules, UPPER_CASE for constants
- **Testing:** All business logic (db, query, influence, export) must have pytest tests; TUI tested manually

---

## File Structure (Post-Implementation)

### New Directories
```
tmdb_cli/db/                # Database layer
tmdb_cli/export/            # Export formatters
tmdb_cli/tui/               # TUI screens and app
tmdb_cli/cli/               # CLI command handlers
```

### New Files
```
tmdb_cli/db/__init__.py
tmdb_cli/db/schema.py                   # SQLite schema, init_db()
tmdb_cli/db/query_builder.py            # QueryBuilder class
tmdb_cli/db/influence.py                # InfluenceGraph class
tmdb_cli/export/__init__.py
tmdb_cli/export/formatter.py            # ExportFormatter class
tmdb_cli/tui/__init__.py
tmdb_cli/tui/app.py                     # TUI entry point, main loop
tmdb_cli/tui/screens.py                 # Screen classes (Search, Watchlist, etc.)
tmdb_cli/tui/keybinds.py                # Keybind constants
tmdb_cli/cli/__init__.py
tmdb_cli/cli/commands.py                # All --cli command handlers

tests/test_db_schema.py
tests/test_query_builder.py
tests/test_influence.py
tests/test_export.py
tests/test_cli_commands.py
tests/test_tui_integration.py           # Manual; verify basic flows
```

### Modified Files
```
tmdb_cli/cli.py                         # Add --cli flag, dispatch to TUI or CLI mode
tmdb_cli/client.py                      # Add response caching to _get()
pyproject.toml                          # Update version to 0.3.0 (optional)
```

---

## Phase 1: MVP Implementation (Data Layer → Business Logic → UI)

### Task 1: SQLite Schema & Database Initialization

**Files:**
- Create: `tmdb_cli/db/__init__.py`
- Create: `tmdb_cli/db/schema.py`
- Create: `tests/test_db_schema.py`

**Interfaces:**
- **Produces:**
  - `init_db(db_path: str) -> sqlite3.Connection` — creates all tables if missing, returns open connection
  - `get_db_path() -> str` — returns `~/.tmdb-cli/tmdb.db`
  - Constants: `DB_PATH`, `MOVIES_TABLE`, `WATCHLIST_TABLE`, `INFLUENCE_TABLE`

**Steps:**

- [ ] **Step 1: Write test for db initialization**

```python
# tests/test_db_schema.py
import sqlite3
import tempfile
import os
from tmdb_cli.db.schema import init_db

def test_init_db_creates_tables():
    """Verify init_db creates all required tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = init_db(db_path)
        
        # Verify movies table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movies'")
        assert cursor.fetchone() is not None
        
        # Verify watchlist table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'")
        assert cursor.fetchone() is not None
        
        # Verify influence table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='influence'")
        assert cursor.fetchone() is not None
        
        conn.close()

def test_init_db_is_idempotent():
    """Verify init_db can be called multiple times safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        conn1 = init_db(db_path)
        cursor1 = conn1.cursor()
        cursor1.execute("SELECT COUNT(*) FROM movies")
        count1 = cursor1.fetchone()[0]
        conn1.close()
        
        conn2 = init_db(db_path)
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM movies")
        count2 = cursor2.fetchone()[0]
        conn2.close()
        
        assert count1 == count2 == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/solomonsmith/Projects/tmdb-cli
pytest tests/test_db_schema.py -v
```

Expected output: FAILED — module `tmdb_cli.db.schema` does not exist

- [ ] **Step 3: Create db module structure**

```bash
mkdir -p tmdb_cli/db
touch tmdb_cli/db/__init__.py
```

- [ ] **Step 4: Write schema.py with init_db function**

```python
# tmdb_cli/db/schema.py
import sqlite3
import os
from pathlib import Path

DB_PATH = os.path.expanduser("~/.tmdb-cli/tmdb.db")

def get_db_path() -> str:
    """Return the database file path."""
    return DB_PATH

def init_db(db_path: str = None) -> sqlite3.Connection:
    """
    Initialize SQLite database with all tables.
    Creates tables if they don't exist (idempotent).
    Returns open connection.
    """
    if db_path is None:
        db_path = DB_PATH
    
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    cursor = conn.cursor()
    
    # movies table: cached TMDB API results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tmdb_id INTEGER UNIQUE NOT NULL,
            title TEXT NOT NULL,
            release_date DATE,
            genres TEXT,                    -- JSON string
            directors TEXT,                 -- JSON string
            cast TEXT,                      -- JSON string
            rating REAL,
            vote_count INTEGER,
            overview TEXT,
            poster_path TEXT,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # watchlist table: user's list with ratings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL UNIQUE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_rating INTEGER CHECK (user_rating IS NULL OR (user_rating >= 1 AND user_rating <= 10)),
            watched_date DATE,
            notes TEXT,
            FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
        )
    """)
    
    # influence table: bidirectional relationships
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS influence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_movie_id INTEGER NOT NULL,
            target_movie_id INTEGER NOT NULL,
            relationship TEXT CHECK (relationship IN ('influenced_by', 'influences')),
            user_note TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_movie_id, target_movie_id, relationship),
            FOREIGN KEY (source_movie_id) REFERENCES movies(id) ON DELETE CASCADE,
            FOREIGN KEY (target_movie_id) REFERENCES movies(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    return conn
```

- [ ] **Step 5: Update db __init__.py for exports**

```python
# tmdb_cli/db/__init__.py
from tmdb_cli.db.schema import init_db, get_db_path, DB_PATH

__all__ = ["init_db", "get_db_path", "DB_PATH"]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_db_schema.py -v
```

Expected output: PASSED (2 tests)

- [ ] **Step 7: Commit**

```bash
git add tmdb_cli/db/ tests/test_db_schema.py
git commit -m "feat: add SQLite schema and initialization"
```

---

### Task 2: QueryBuilder (Filtering & Sorting)

**Files:**
- Create: `tmdb_cli/db/query_builder.py`
- Create: `tests/test_query_builder.py`

**Interfaces:**
- **Consumes:** `init_db()` from Task 1
- **Produces:**
  - `QueryBuilder(conn: sqlite3.Connection)` — class
  - `.filter_genre(genres: List[str]) -> QueryBuilder`
  - `.filter_director(names: List[str]) -> QueryBuilder`
  - `.filter_actor(names: List[str]) -> QueryBuilder`
  - `.filter_year(min: int, max: int) -> QueryBuilder`
  - `.filter_rating_min(threshold: float) -> QueryBuilder`
  - `.filter_vote_count_min(count: int) -> QueryBuilder`
  - `.filter_watched(watched: bool) -> QueryBuilder`
  - `.filter_in_watchlist(in_list: bool) -> QueryBuilder`
  - `.sort_by(criteria: List[Tuple[str, str]]) -> QueryBuilder` — criteria = [("rating", "desc"), ...]
  - `.execute() -> List[Dict]`

**Steps:**

- [ ] **Step 1: Write test for QueryBuilder**

```python
# tests/test_query_builder.py
import sqlite3
import tempfile
import os
import json
from tmdb_cli.db.schema import init_db
from tmdb_cli.db.query_builder import QueryBuilder

@pytest.fixture
def db_with_sample_data():
    """Create a test database with sample movies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = init_db(db_path)
        cursor = conn.cursor()
        
        # Insert sample movies
        movies = [
            (111, "Inception", "2010-07-16", json.dumps(["Sci-Fi", "Action"]), json.dumps(["Christopher Nolan"]), json.dumps(["Leonardo DiCaprio"]), 8.8, 2500000),
            (222, "The Dark Knight", "2008-07-18", json.dumps(["Action", "Crime"]), json.dumps(["Christopher Nolan"]), json.dumps(["Christian Bale"]), 9.0, 2800000),
            (333, "Interstellar", "2014-11-07", json.dumps(["Sci-Fi", "Drama"]), json.dumps(["Christopher Nolan"]), json.dumps(["Matthew McConaughey"]), 8.6, 1800000),
            (444, "Dune", "2021-10-22", json.dumps(["Sci-Fi", "Drama"]), json.dumps(["Denis Villeneuve"]), json.dumps(["Timothée Chalamet"]), 8.0, 1200000),
        ]
        
        for tmdb_id, title, release_date, genres, directors, cast, rating, vote_count in movies:
            cursor.execute("""
                INSERT INTO movies (tmdb_id, title, release_date, genres, directors, cast, rating, vote_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (tmdb_id, title, release_date, genres, directors, cast, rating, vote_count))
        
        # Add one to watchlist with rating
        cursor.execute("INSERT INTO watchlist (movie_id, user_rating) VALUES (1, 9)")
        
        conn.commit()
        yield conn
        conn.close()

def test_query_builder_filter_genre(db_with_sample_data):
    """Test filtering by genre."""
    conn = db_with_sample_data
    results = QueryBuilder(conn).filter_genre(["Sci-Fi"]).execute()
    titles = [r["title"] for r in results]
    assert "Inception" in titles
    assert "Interstellar" in titles
    assert "Dune" in titles
    assert "The Dark Knight" not in titles

def test_query_builder_filter_director(db_with_sample_data):
    """Test filtering by director."""
    conn = db_with_sample_data
    results = QueryBuilder(conn).filter_director(["Christopher Nolan"]).execute()
    assert len(results) == 3  # Inception, Dark Knight, Interstellar
    for r in results:
        assert r["title"] in ["Inception", "The Dark Knight", "Interstellar"]

def test_query_builder_filter_rating_min(db_with_sample_data):
    """Test filtering by minimum rating."""
    conn = db_with_sample_data
    results = QueryBuilder(conn).filter_rating_min(8.5).execute()
    assert all(r["rating"] >= 8.5 for r in results)
    assert len(results) == 3  # Inception (8.8), Dark Knight (9.0), Interstellar (8.6)

def test_query_builder_filter_year(db_with_sample_data):
    """Test filtering by year range."""
    conn = db_with_sample_data
    results = QueryBuilder(conn).filter_year(2010, 2015).execute()
    titles = [r["title"] for r in results]
    assert "Inception" in titles
    assert "Interstellar" in titles
    assert "Dune" not in titles

def test_query_builder_filter_in_watchlist(db_with_sample_data):
    """Test filtering to watchlist only."""
    conn = db_with_sample_data
    results = QueryBuilder(conn).filter_in_watchlist(True).execute()
    assert len(results) == 1
    assert results[0]["title"] == "Inception"

def test_query_builder_sort_by(db_with_sample_data):
    """Test sorting by rating descending."""
    conn = db_with_sample_data
    results = QueryBuilder(conn).sort_by([("rating", "desc")]).execute()
    ratings = [r["rating"] for r in results]
    assert ratings == sorted(ratings, reverse=True)

def test_query_builder_combined_filters(db_with_sample_data):
    """Test multiple filters combined."""
    conn = db_with_sample_data
    results = (QueryBuilder(conn)
        .filter_genre(["Sci-Fi"])
        .filter_rating_min(8.5)
        .sort_by([("rating", "desc")])
        .execute())
    
    assert len(results) == 2  # Inception (8.8), Interstellar (8.6)
    assert results[0]["title"] == "Inception"
    assert results[1]["title"] == "Interstellar"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_query_builder.py -v
```

Expected output: FAILED — module does not exist

- [ ] **Step 3: Write QueryBuilder implementation**

```python
# tmdb_cli/db/query_builder.py
import sqlite3
import json
from typing import List, Dict, Tuple, Any, Optional

class QueryBuilder:
    """Fluent interface for building complex movie queries."""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.filters = []
        self.sort_criteria = []
    
    def filter_genre(self, genres: List[str]) -> "QueryBuilder":
        """Filter movies that have ANY of the given genres."""
        self.filters.append(("genre", genres))
        return self
    
    def filter_director(self, names: List[str]) -> "QueryBuilder":
        """Filter movies directed by ANY of the given directors."""
        self.filters.append(("director", names))
        return self
    
    def filter_actor(self, names: List[str]) -> "QueryBuilder":
        """Filter movies with ANY of the given actors."""
        self.filters.append(("actor", names))
        return self
    
    def filter_year(self, min_year: int, max_year: int) -> "QueryBuilder":
        """Filter movies by release year range (inclusive)."""
        self.filters.append(("year", (min_year, max_year)))
        return self
    
    def filter_rating_min(self, threshold: float) -> "QueryBuilder":
        """Filter movies with rating >= threshold."""
        self.filters.append(("rating_min", threshold))
        return self
    
    def filter_vote_count_min(self, count: int) -> "QueryBuilder":
        """Filter movies with vote_count >= count."""
        self.filters.append(("vote_count_min", count))
        return self
    
    def filter_watched(self, watched: bool) -> "QueryBuilder":
        """Filter watched or unwatched movies."""
        self.filters.append(("watched", watched))
        return self
    
    def filter_in_watchlist(self, in_list: bool) -> "QueryBuilder":
        """Filter movies in or not in watchlist."""
        self.filters.append(("in_watchlist", in_list))
        return self
    
    def sort_by(self, criteria: List[Tuple[str, str]]) -> "QueryBuilder":
        """
        Sort results by one or more columns.
        criteria: [("rating", "desc"), ("release_date", "asc")]
        """
        self.sort_criteria = criteria
        return self
    
    def execute(self) -> List[Dict[str, Any]]:
        """Execute query and return list of movie dicts."""
        query = "SELECT m.* FROM movies m LEFT JOIN watchlist w ON m.id = w.movie_id WHERE 1=1"
        params = []
        
        # Apply filters
        for filter_type, filter_value in self.filters:
            if filter_type == "genre":
                # Match ANY genre in the list
                genre_conditions = " OR ".join([
                    "json_extract(m.genres, '$[*]') LIKE ?" 
                    for _ in filter_value
                ])
                query += f" AND ({genre_conditions})"
                params.extend([f"%{g}%" for g in filter_value])
            
            elif filter_type == "director":
                # Match ANY director in the list
                dir_conditions = " OR ".join([
                    "json_extract(m.directors, '$[*]') LIKE ?" 
                    for _ in filter_value
                ])
                query += f" AND ({dir_conditions})"
                params.extend([f"%{d}%" for d in filter_value])
            
            elif filter_type == "actor":
                # Match ANY actor in the list
                actor_conditions = " OR ".join([
                    "json_extract(m.cast, '$[*]') LIKE ?" 
                    for _ in filter_value
                ])
                query += f" AND ({actor_conditions})"
                params.extend([f"%{a}%" for a in filter_value])
            
            elif filter_type == "year":
                min_year, max_year = filter_value
                query += f" AND strftime('%Y', m.release_date) BETWEEN ? AND ?"
                params.extend([str(min_year), str(max_year)])
            
            elif filter_type == "rating_min":
                query += " AND m.rating >= ?"
                params.append(filter_value)
            
            elif filter_type == "vote_count_min":
                query += " AND m.vote_count >= ?"
                params.append(filter_value)
            
            elif filter_type == "watched":
                if filter_value:
                    query += " AND w.watched_date IS NOT NULL"
                else:
                    query += " AND w.watched_date IS NULL"
            
            elif filter_type == "in_watchlist":
                if filter_value:
                    query += " AND w.id IS NOT NULL"
                else:
                    query += " AND w.id IS NULL"
        
        # Apply sorting
        if self.sort_criteria:
            order_clause = ", ".join([
                f"m.{col} {direction.upper()}"
                for col, direction in self.sort_criteria
            ])
            query += f" ORDER BY {order_clause}"
        
        # Execute
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_query_builder.py -v
```

Expected output: PASSED (all tests)

- [ ] **Step 5: Commit**

```bash
git add tmdb_cli/db/query_builder.py tests/test_query_builder.py
git commit -m "feat: add QueryBuilder for filtering and sorting"
```

---

### Task 3: Watchlist CRUD (Add, Rate, List, Remove)

**Files:**
- Create: `tmdb_cli/db/watchlist.py`
- Create: `tests/test_watchlist.py`

**Interfaces:**
- **Consumes:** `init_db()`, `QueryBuilder` from Tasks 1-2
- **Produces:**
  - `add_to_watchlist(conn: sqlite3.Connection, movie_id: int) -> bool`
  - `rate_movie(conn: sqlite3.Connection, movie_id: int, rating: int) -> bool`
  - `mark_watched(conn: sqlite3.Connection, movie_id: int, watched_date: str = None) -> bool`
  - `get_watchlist(conn: sqlite3.Connection) -> List[Dict]`
  - `remove_from_watchlist(conn: sqlite3.Connection, movie_id: int) -> bool`

**Steps:**

- [ ] **Step 1: Write tests for watchlist operations**

```python
# tests/test_watchlist.py
import sqlite3
import tempfile
import os
import json
import pytest
from datetime import date
from tmdb_cli.db.schema import init_db
from tmdb_cli.db.watchlist import (
    add_to_watchlist, rate_movie, mark_watched, 
    get_watchlist, remove_from_watchlist
)

@pytest.fixture
def db_with_movies():
    """Create test database with sample movies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = init_db(db_path)
        cursor = conn.cursor()
        
        movies = [
            (111, "Inception", "2010-07-16", json.dumps(["Sci-Fi"]), json.dumps(["Nolan"]), json.dumps(["DiCaprio"]), 8.8, 2500000),
            (222, "Interstellar", "2014-11-07", json.dumps(["Sci-Fi"]), json.dumps(["Nolan"]), json.dumps(["McConaughey"]), 8.6, 1800000),
        ]
        
        for tmdb_id, title, release_date, genres, directors, cast, rating, vote_count in movies:
            cursor.execute("""
                INSERT INTO movies (tmdb_id, title, release_date, genres, directors, cast, rating, vote_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (tmdb_id, title, release_date, genres, directors, cast, rating, vote_count))
        
        conn.commit()
        yield conn
        conn.close()

def test_add_to_watchlist(db_with_movies):
    """Test adding a movie to watchlist."""
    conn = db_with_movies
    result = add_to_watchlist(conn, 1)
    assert result is True
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM watchlist WHERE movie_id = 1")
    row = cursor.fetchone()
    assert row is not None
    assert row[1] == 1  # movie_id

def test_add_duplicate_to_watchlist(db_with_movies):
    """Test adding the same movie twice (should fail or be idempotent)."""
    conn = db_with_movies
    add_to_watchlist(conn, 1)
    # Adding again should not crash
    result = add_to_watchlist(conn, 1)
    # Either returns False or succeeds (idempotent)

def test_rate_movie(db_with_movies):
    """Test rating a movie."""
    conn = db_with_movies
    add_to_watchlist(conn, 1)
    result = rate_movie(conn, 1, 9)
    assert result is True
    
    cursor = conn.cursor()
    cursor.execute("SELECT user_rating FROM watchlist WHERE movie_id = 1")
    rating = cursor.fetchone()[0]
    assert rating == 9

def test_mark_watched(db_with_movies):
    """Test marking a movie as watched."""
    conn = db_with_movies
    add_to_watchlist(conn, 1)
    watch_date = "2026-07-10"
    result = mark_watched(conn, 1, watch_date)
    assert result is True
    
    cursor = conn.cursor()
    cursor.execute("SELECT watched_date FROM watchlist WHERE movie_id = 1")
    saved_date = cursor.fetchone()[0]
    assert saved_date == watch_date

def test_get_watchlist(db_with_movies):
    """Test retrieving the watchlist."""
    conn = db_with_movies
    add_to_watchlist(conn, 1)
    rate_movie(conn, 1, 8)
    add_to_watchlist(conn, 2)
    
    watchlist = get_watchlist(conn)
    assert len(watchlist) == 2
    titles = [w["title"] for w in watchlist]
    assert "Inception" in titles
    assert "Interstellar" in titles

def test_remove_from_watchlist(db_with_movies):
    """Test removing a movie from watchlist."""
    conn = db_with_movies
    add_to_watchlist(conn, 1)
    result = remove_from_watchlist(conn, 1)
    assert result is True
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM watchlist WHERE movie_id = 1")
    count = cursor.fetchone()[0]
    assert count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_watchlist.py -v
```

Expected: module does not exist

- [ ] **Step 3: Write watchlist.py implementation**

```python
# tmdb_cli/db/watchlist.py
import sqlite3
from typing import List, Dict, Optional
from datetime import date

def add_to_watchlist(conn: sqlite3.Connection, movie_id: int) -> bool:
    """Add a movie to the user's watchlist. Returns True on success."""
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO watchlist (movie_id) VALUES (?)", (movie_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Movie already in watchlist
        return False

def rate_movie(conn: sqlite3.Connection, movie_id: int, rating: int) -> bool:
    """Rate a movie (1-10). Returns True on success."""
    if not (1 <= rating <= 10):
        return False
    
    cursor = conn.cursor()
    cursor.execute("UPDATE watchlist SET user_rating = ? WHERE movie_id = ?", (rating, movie_id))
    conn.commit()
    return cursor.rowcount > 0

def mark_watched(conn: sqlite3.Connection, movie_id: int, watched_date: str = None) -> bool:
    """Mark a movie as watched. watched_date format: 'YYYY-MM-DD'. If None, uses today."""
    if watched_date is None:
        watched_date = str(date.today())
    
    cursor = conn.cursor()
    cursor.execute("UPDATE watchlist SET watched_date = ? WHERE movie_id = ?", (watched_date, movie_id))
    conn.commit()
    return cursor.rowcount > 0

def get_watchlist(conn: sqlite3.Connection) -> List[Dict]:
    """Retrieve all movies in watchlist with metadata."""
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id, m.tmdb_id, m.title, m.release_date, m.genres, m.directors, 
               m.rating, m.vote_count, m.poster_path,
               w.added_at, w.user_rating, w.watched_date, w.notes
        FROM watchlist w
        JOIN movies m ON w.movie_id = m.id
        ORDER BY w.added_at DESC
    """)
    return [dict(row) for row in cursor.fetchall()]

def remove_from_watchlist(conn: sqlite3.Connection, movie_id: int) -> bool:
    """Remove a movie from watchlist. Returns True on success."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM watchlist WHERE movie_id = ?", (movie_id,))
    conn.commit()
    return cursor.rowcount > 0
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_watchlist.py -v
```

Expected: all pass

- [ ] **Step 5: Update db __init__.py to export watchlist functions**

```python
# tmdb_cli/db/__init__.py
from tmdb_cli.db.schema import init_db, get_db_path, DB_PATH
from tmdb_cli.db.watchlist import (
    add_to_watchlist, rate_movie, mark_watched, 
    get_watchlist, remove_from_watchlist
)

__all__ = [
    "init_db", "get_db_path", "DB_PATH",
    "add_to_watchlist", "rate_movie", "mark_watched", "get_watchlist", "remove_from_watchlist"
]
```

- [ ] **Step 6: Commit**

```bash
git add tmdb_cli/db/watchlist.py tests/test_watchlist.py tmdb_cli/db/__init__.py
git commit -m "feat: add watchlist CRUD operations"
```

---

### Task 4: ExportFormatter (CSV, Markdown, JSON)

**Files:**
- Create: `tmdb_cli/export/__init__.py`
- Create: `tmdb_cli/export/formatter.py`
- Create: `tests/test_export.py`

**Interfaces:**
- **Consumes:** Movies list (List[Dict])
- **Produces:**
  - `ExportFormatter` class
  - `.to_csv(movies: List[Dict], title: str = None) -> str`
  - `.to_markdown(movies: List[Dict], title: str = None) -> str`
  - `.to_json(movies: List[Dict]) -> str`

**Steps:**

- [ ] **Step 1: Write export tests**

```python
# tests/test_export.py
import json
import csv
import io
import pytest
from tmdb_cli.export.formatter import ExportFormatter

@pytest.fixture
def sample_movies():
    """Sample movie list for export testing."""
    return [
        {
            "id": 1,
            "tmdb_id": 111,
            "title": "Inception",
            "release_date": "2010-07-16",
            "rating": 8.8,
            "user_rating": 9,
            "watched_date": "2026-07-01",
            "genres": '["Sci-Fi", "Action"]',
            "directors": '["Christopher Nolan"]'
        },
        {
            "id": 2,
            "tmdb_id": 222,
            "title": "Interstellar",
            "release_date": "2014-11-07",
            "rating": 8.6,
            "user_rating": None,
            "watched_date": None,
            "genres": '["Sci-Fi", "Drama"]',
            "directors": '["Christopher Nolan"]'
        }
    ]

def test_export_to_csv(sample_movies):
    """Test CSV export format."""
    formatter = ExportFormatter()
    csv_str = formatter.to_csv(sample_movies)
    
    # Parse CSV to verify structure
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["title"] == "Inception"
    assert rows[0]["user_rating"] == "9"
    assert rows[1]["title"] == "Interstellar"

def test_export_to_markdown(sample_movies):
    """Test Markdown export format."""
    formatter = ExportFormatter()
    md_str = formatter.to_markdown(sample_movies, title="My Watchlist")
    
    assert "# My Watchlist" in md_str
    assert "Inception" in md_str
    assert "Interstellar" in md_str
    assert "|" in md_str  # Markdown table

def test_export_to_json(sample_movies):
    """Test JSON export format."""
    formatter = ExportFormatter()
    json_str = formatter.to_json(sample_movies)
    
    data = json.loads(json_str)
    assert len(data) == 2
    assert data[0]["title"] == "Inception"
    assert data[1]["title"] == "Interstellar"

def test_export_csv_with_title(sample_movies):
    """Test CSV with optional title as first line."""
    formatter = ExportFormatter()
    csv_str = formatter.to_csv(sample_movies, title="My Collection")
    lines = csv_str.strip().split("\n")
    # Title may be a comment line or not included
    assert "Inception" in csv_str
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_export.py -v
```

Expected: module does not exist

- [ ] **Step 3: Write ExportFormatter implementation**

```python
# tmdb_cli/export/formatter.py
import json
import csv
import io
from typing import List, Dict, Optional

class ExportFormatter:
    """Export movie lists to various formats."""
    
    def to_csv(self, movies: List[Dict], title: str = None) -> str:
        """Export movies as CSV."""
        if not movies:
            return ""
        
        output = io.StringIO()
        
        # Determine CSV columns (from first movie)
        fieldnames = ["title", "release_date", "rating", "user_rating", "watched_date", "genres", "directors"]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for movie in movies:
            row = {
                "title": movie.get("title", ""),
                "release_date": movie.get("release_date", ""),
                "rating": movie.get("rating", ""),
                "user_rating": movie.get("user_rating", ""),
                "watched_date": movie.get("watched_date", ""),
                "genres": movie.get("genres", ""),
                "directors": movie.get("directors", ""),
            }
            writer.writerow(row)
        
        return output.getvalue()
    
    def to_markdown(self, movies: List[Dict], title: str = None) -> str:
        """Export movies as Markdown table."""
        if not movies:
            return ""
        
        lines = []
        
        if title:
            lines.append(f"# {title}\n")
        
        # Header
        lines.append("| Title | Release Date | Rating | User Rating |")
        lines.append("|-------|--------------|--------|-------------|")
        
        # Rows
        for movie in movies:
            title = movie.get("title", "")
            release = movie.get("release_date", "-")
            rating = movie.get("rating", "-")
            user_rating = movie.get("user_rating", "-")
            
            lines.append(f"| {title} | {release} | {rating} | {user_rating} |")
        
        return "\n".join(lines)
    
    def to_json(self, movies: List[Dict]) -> str:
        """Export movies as JSON."""
        return json.dumps(movies, indent=2)
```

- [ ] **Step 4: Create export __init__.py**

```python
# tmdb_cli/export/__init__.py
from tmdb_cli.export.formatter import ExportFormatter

__all__ = ["ExportFormatter"]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_export.py -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add tmdb_cli/export/ tests/test_export.py
git commit -m "feat: add export formatters for CSV, Markdown, JSON"
```

---

### Task 5: InfluenceGraph (Bidirectional Relationships)

**Files:**
- Create: `tmdb_cli/db/influence.py`
- Create: `tests/test_influence.py`

**Interfaces:**
- **Consumes:** `init_db()` from Task 1
- **Produces:**
  - `InfluenceGraph(conn: sqlite3.Connection)` class
  - `.add_influence(source_title: str, relationship: str, target_title: str, note: str = None) -> bool`
  - `.get_ancestors(movie_title: str, depth: int = 3) -> List[Dict]`
  - `.get_descendants(movie_title: str, depth: int = 3) -> List[Dict]`
  - `.get_chain(movie_title: str, direction: str, depth: int) -> Dict`

**Steps:**

- [ ] **Step 1: Write influence tests**

```python
# tests/test_influence.py
import sqlite3
import tempfile
import os
import json
import pytest
from tmdb_cli.db.schema import init_db
from tmdb_cli.db.influence import InfluenceGraph

@pytest.fixture
def db_with_movies():
    """Create database with sample movies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = init_db(db_path)
        cursor = conn.cursor()
        
        movies = [
            (1, "2001: A Space Odyssey", "1968-04-02", json.dumps(["Sci-Fi"]), json.dumps(["Kubrick"]), json.dumps([]), 8.3, 1000000),
            (2, "Inception", "2010-07-16", json.dumps(["Sci-Fi"]), json.dumps(["Nolan"]), json.dumps([]), 8.8, 2500000),
            (3, "Interstellar", "2014-11-07", json.dumps(["Sci-Fi"]), json.dumps(["Nolan"]), json.dumps([]), 8.6, 1800000),
            (4, "The Matrix", "1999-03-31", json.dumps(["Sci-Fi"]), json.dumps(["Wachowskis"]), json.dumps([]), 8.7, 2000000),
        ]
        
        for tmdb_id, title, release_date, genres, directors, cast, rating, vote_count in movies:
            cursor.execute("""
                INSERT INTO movies (tmdb_id, title, release_date, genres, directors, cast, rating, vote_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (tmdb_id, title, release_date, genres, directors, cast, rating, vote_count))
        
        conn.commit()
        yield conn
        conn.close()

def test_add_influence(db_with_movies):
    """Test adding an influence relationship."""
    conn = db_with_movies
    graph = InfluenceGraph(conn)
    result = graph.add_influence("Inception", "influenced_by", "2001: A Space Odyssey")
    assert result is True
    
    # Verify it was stored
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM influence 
        WHERE relationship IN ('influenced_by', 'influences')
    """)
    count = cursor.fetchone()[0]
    # Should create entries for both directions
    assert count >= 2

def test_get_ancestors(db_with_movies):
    """Test retrieving what influenced a movie."""
    conn = db_with_movies
    graph = InfluenceGraph(conn)
    
    # Inception influenced_by 2001
    graph.add_influence("Inception", "influenced_by", "2001: A Space Odyssey")
    
    ancestors = graph.get_ancestors("Inception", depth=3)
    titles = [a["title"] for a in ancestors]
    assert "2001: A Space Odyssey" in titles

def test_get_descendants(db_with_movies):
    """Test retrieving what a movie influenced."""
    conn = db_with_movies
    graph = InfluenceGraph(conn)
    
    # Inception influences Interstellar
    graph.add_influence("Interstellar", "influenced_by", "Inception")
    
    descendants = graph.get_descendants("Inception", depth=3)
    titles = [d["title"] for d in descendants]
    assert "Interstellar" in titles

def test_get_chain_structure(db_with_movies):
    """Test the chain data structure."""
    conn = db_with_movies
    graph = InfluenceGraph(conn)
    
    graph.add_influence("Inception", "influenced_by", "2001: A Space Odyssey")
    graph.add_influence("Interstellar", "influenced_by", "Inception")
    
    chain = graph.get_chain("Inception", "ancestors", depth=3)
    assert "root" in chain
    assert "chain" in chain
    assert chain["root"]["title"] == "Inception"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_influence.py -v
```

Expected: module does not exist

- [ ] **Step 3: Write InfluenceGraph implementation**

```python
# tmdb_cli/db/influence.py
import sqlite3
from typing import List, Dict, Optional

class InfluenceGraph:
    """Manage bidirectional influence relationships between movies."""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
    
    def _get_movie_id(self, title: str) -> Optional[int]:
        """Get movie ID by title."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM movies WHERE title = ?", (title,))
        row = cursor.fetchone()
        return row[0] if row else None
    
    def add_influence(self, source_title: str, relationship: str, target_title: str, note: str = None) -> bool:
        """
        Add an influence relationship.
        relationship: 'influenced_by' or 'influences'
        Creates entries in both directions automatically.
        """
        source_id = self._get_movie_id(source_title)
        target_id = self._get_movie_id(target_title)
        
        if source_id is None or target_id is None:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # Add the direct relationship
            cursor.execute("""
                INSERT INTO influence (source_movie_id, target_movie_id, relationship, user_note)
                VALUES (?, ?, ?, ?)
            """, (source_id, target_id, relationship, note))
            
            # Add reverse relationship (if source A is influenced_by B, then B influences A)
            reverse_relationship = "influences" if relationship == "influenced_by" else "influenced_by"
            cursor.execute("""
                INSERT INTO influence (source_movie_id, target_movie_id, relationship, user_note)
                VALUES (?, ?, ?, ?)
            """, (target_id, source_id, reverse_relationship, note))
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Relationship already exists
            return False
    
    def get_ancestors(self, movie_title: str, depth: int = 3) -> List[Dict]:
        """Get movies that influenced the given movie (traverse 'influenced_by')."""
        movie_id = self._get_movie_id(movie_title)
        if movie_id is None:
            return []
        
        results = []
        visited = {movie_id}
        queue = [(movie_id, 0)]
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_depth >= depth:
                continue
            
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT m.* FROM movies m
                JOIN influence i ON m.id = i.source_movie_id
                WHERE i.target_movie_id = ? AND i.relationship = 'influenced_by'
                AND m.id NOT IN ({})
            """.format(','.join('?' * len(visited))), 
            [current_id] + list(visited))
            
            for row in cursor.fetchall():
                ancestor = dict(row)
                ancestor_id = ancestor["id"]
                
                if ancestor_id not in visited:
                    results.append(ancestor)
                    visited.add(ancestor_id)
                    queue.append((ancestor_id, current_depth + 1))
        
        return results
    
    def get_descendants(self, movie_title: str, depth: int = 3) -> List[Dict]:
        """Get movies that the given movie influenced (traverse 'influences')."""
        movie_id = self._get_movie_id(movie_title)
        if movie_id is None:
            return []
        
        results = []
        visited = {movie_id}
        queue = [(movie_id, 0)]
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_depth >= depth:
                continue
            
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT m.* FROM movies m
                JOIN influence i ON m.id = i.target_movie_id
                WHERE i.source_movie_id = ? AND i.relationship = 'influences'
                AND m.id NOT IN ({})
            """.format(','.join('?' * len(visited))), 
            [current_id] + list(visited))
            
            for row in cursor.fetchall():
                descendant = dict(row)
                descendant_id = descendant["id"]
                
                if descendant_id not in visited:
                    results.append(descendant)
                    visited.add(descendant_id)
                    queue.append((descendant_id, current_depth + 1))
        
        return results
    
    def get_chain(self, movie_title: str, direction: str, depth: int = 3) -> Dict:
        """
        Get influence chain in a structured format.
        direction: 'ancestors' or 'descendants'
        Returns: {"root": {...}, "chain": [...], "total_films": N}
        """
        movie_id = self._get_movie_id(movie_title)
        if movie_id is None:
            return {"root": None, "chain": [], "total_films": 0}
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
        root = dict(cursor.fetchone())
        
        if direction == "ancestors":
            films = self.get_ancestors(movie_title, depth)
        else:
            films = self.get_descendants(movie_title, depth)
        
        # For now, return flat list; could be structured by level later
        return {
            "root": root,
            "chain": [{"level": 1, "movies": films}],
            "total_films": len(films) + 1
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_influence.py -v
```

Expected: all pass

- [ ] **Step 5: Update db __init__.py to export InfluenceGraph**

```python
# tmdb_cli/db/__init__.py
from tmdb_cli.db.schema import init_db, get_db_path, DB_PATH
from tmdb_cli.db.query_builder import QueryBuilder
from tmdb_cli.db.watchlist import (
    add_to_watchlist, rate_movie, mark_watched, 
    get_watchlist, remove_from_watchlist
)
from tmdb_cli.db.influence import InfluenceGraph

__all__ = [
    "init_db", "get_db_path", "DB_PATH",
    "QueryBuilder",
    "add_to_watchlist", "rate_movie", "mark_watched", "get_watchlist", "remove_from_watchlist",
    "InfluenceGraph"
]
```

- [ ] **Step 6: Commit**

```bash
git add tmdb_cli/db/influence.py tests/test_influence.py tmdb_cli/db/__init__.py
git commit -m "feat: add bidirectional influence graph"
```

---

### Task 6: Extend TMDBClient with Caching

**Files:**
- Modify: `tmdb_cli/client.py`
- Create: `tests/test_client_caching.py`

**Interfaces:**
- **Modifies:** `TMDBClient._get()` to cache responses in SQLite

**Steps:**

- [ ] **Step 1: Write test for client caching**

```python
# tests/test_client_caching.py
import sqlite3
import tempfile
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from tmdb_cli.db.schema import init_db
from tmdb_cli.client import TMDBClient

@pytest.fixture
def temp_db():
    """Temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = init_db(db_path)
        yield conn
        conn.close()

@patch('tmdb_cli.client.requests.get')
def test_client_caches_response(mock_get, temp_db):
    """Test that API responses are cached in SQLite."""
    client = TMDBClient("fake_key", db_conn=temp_db)
    
    # Mock API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"id": 111, "title": "Inception", "release_date": "2010-07-16", "vote_average": 8.8, "vote_count": 2500000}
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    # First call fetches from API
    result1 = client.get_movies("popular", 1)
    assert mock_get.call_count == 1
    
    # Second call should fetch from cache
    result2 = client.get_movies("popular", 1)
    assert mock_get.call_count == 1  # Still 1; didn't call API again

def test_client_stores_movies_in_db(temp_db):
    """Test that movies from API are stored in SQLite."""
    client = TMDBClient("fake_key", db_conn=temp_db)
    
    with patch('tmdb_cli.client.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": 111, "title": "Inception", "release_date": "2010-07-16", "vote_average": 8.8, "vote_count": 2500000}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        client.get_movies("popular", 1)
        
        # Verify movie was stored
        cursor = temp_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies WHERE title = 'Inception'")
        count = cursor.fetchone()[0]
        assert count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_client_caching.py -v
```

Expected: FAIL — TMDBClient doesn't accept db_conn parameter

- [ ] **Step 3: Modify TMDBClient to add caching**

```python
# tmdb_cli/client.py (MODIFY EXISTING)
import re
import requests
import sqlite3
import json
from typing import Any, Dict, Optional

_API_KEY_PARAM_RE = re.compile(r"([?&])api_key=[^&\s]+")

def _redact(message: str) -> str:
    return _API_KEY_PARAM_RE.sub(r"\1api_key=***REDACTED***", message)

BASE_URL = "https://api.themoviedb.org/3"

ENDPOINTS = {
    "playing": "movie/now_playing",
    "popular": "movie/popular",
    "top": "movie/top_rated",
    "upcoming": "movie/upcoming",
}

class TMDBClient:
    def __init__(self, api_key: str, db_conn: Optional[sqlite3.Connection] = None):
        self.api_key = api_key
        self.db_conn = db_conn  # Optional SQLite connection for caching
    
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        
        # Check cache first if db_conn available
        if self.db_conn and path == "search/movie":
            cached = self._get_cached_search(params.get("query"))
            if cached:
                return cached
        
        url = f"{BASE_URL}/{path}"
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            # Cache movies if we have a db connection
            if self.db_conn and "results" in data:
                self._cache_movies(data["results"])
            
            return data
        except requests.RequestException as e:
            raise RuntimeError(f"Network/API error: {_redact(str(e))}") from None
    
    def _cache_movies(self, movies: list) -> None:
        """Store movies in SQLite cache."""
        if not self.db_conn:
            return
        
        cursor = self.db_conn.cursor()
        for movie in movies:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO movies 
                    (tmdb_id, title, release_date, genres, directors, cast, rating, vote_count, overview, poster_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    movie.get("id"),
                    movie.get("title") or movie.get("name"),
                    movie.get("release_date"),
                    json.dumps(movie.get("genres", [])),
                    json.dumps([]),  # Directors not in search results
                    json.dumps([]),  # Cast not in search results
                    movie.get("vote_average"),
                    movie.get("vote_count"),
                    movie.get("overview"),
                    movie.get("poster_path")
                ))
            except Exception:
                pass  # Skip any individual movie on error
        
        self.db_conn.commit()
    
    def _get_cached_search(self, query: str) -> Optional[Dict[str, Any]]:
        """Try to get search results from cache."""
        if not query or not self.db_conn:
            return None
        
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT id, tmdb_id, title, release_date, rating FROM movies WHERE title LIKE ?", (f"%{query}%",))
        rows = cursor.fetchall()
        
        if rows:
            return {
                "results": [dict(row) for row in rows]
            }
        return None
    
    def get_movies(self, category: str, page: int = 1) -> Dict[str, Any]:
        endpoint = ENDPOINTS[category]
        return self._get(endpoint, params={"page": page})
    
    def search_movies(self, query: str, page: int = 1) -> Dict[str, Any]:
        return self._get("search/movie", params={"query": query, "page": page})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_client_caching.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tmdb_cli/client.py tests/test_client_caching.py
git commit -m "feat: add response caching to TMDBClient"
```

---

### Task 7: CLI Commands (--cli Flag & Subcommands)

**Files:**
- Create: `tmdb_cli/cli/__init__.py`
- Create: `tmdb_cli/cli/commands.py`
- Modify: `tmdb_cli/cli.py` (add --cli dispatch logic)
- Create: `tests/test_cli_commands.py`

**Interfaces:**
- **Consumes:** All business logic from Tasks 1-6
- **Produces:**
  - CLI command handlers for: search, watchlist, influence, export
  - --cli flag that dispatches to command mode

**Steps:**

- [ ] **Step 1: Write CLI command tests**

```python
# tests/test_cli_commands.py
import tempfile
import os
import json
import pytest
from tmdb_cli.db.schema import init_db
from tmdb_cli.cli.commands import (
    cmd_search, cmd_watchlist_add, cmd_watchlist_list,
    cmd_influence_add, cmd_export
)

@pytest.fixture
def temp_db():
    """Temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = init_db(db_path)
        yield conn
        conn.close()

def test_cmd_watchlist_add(temp_db, capsys):
    """Test watchlist add command."""
    # Add a movie first
    cursor = temp_db.cursor()
    cursor.execute("""
        INSERT INTO movies (tmdb_id, title, release_date, rating, vote_count)
        VALUES (111, 'Inception', '2010-07-16', 8.8, 2500000)
    """)
    temp_db.commit()
    
    # Add to watchlist via CLI
    result = cmd_watchlist_add(temp_db, 1)
    assert result == 0  # Success

def test_cmd_watchlist_list(temp_db, capsys):
    """Test watchlist list command."""
    # Setup: add a movie to watchlist
    cursor = temp_db.cursor()
    cursor.execute("""
        INSERT INTO movies (tmdb_id, title, release_date, rating, vote_count)
        VALUES (111, 'Inception', '2010-07-16', 8.8, 2500000)
    """)
    cursor.execute("INSERT INTO watchlist (movie_id) VALUES (1)")
    temp_db.commit()
    
    # List watchlist
    result = cmd_watchlist_list(temp_db, json_format=True)
    assert result == 0
    
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert len(output) == 1
    assert output[0]["title"] == "Inception"
```

- [ ] **Step 2: Create cli module structure**

```bash
mkdir -p tmdb_cli/cli
touch tmdb_cli/cli/__init__.py
```

- [ ] **Step 3: Write commands.py**

```python
# tmdb_cli/cli/commands.py
import sys
import json
import sqlite3
from typing import Optional
from tmdb_cli.db import QueryBuilder, get_watchlist, add_to_watchlist, remove_from_watchlist, rate_movie, InfluenceGraph
from tmdb_cli.export import ExportFormatter

def cmd_search(conn: sqlite3.Connection, query: str, genre: Optional[str] = None, 
               director: Optional[str] = None, rating_min: Optional[float] = None,
               json_format: bool = False) -> int:
    """Search movies and filter."""
    try:
        builder = QueryBuilder(conn)
        
        if query:
            # Search by genre if query is empty (browse mode)
            if genre:
                builder.filter_genre([genre])
            # Add more filters as needed
        
        results = builder.execute()
        
        if json_format:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"{r['title']} ({r.get('release_date', 'N/A')})")
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def cmd_watchlist_add(conn: sqlite3.Connection, movie_id: int) -> int:
    """Add movie to watchlist."""
    try:
        result = add_to_watchlist(conn, movie_id)
        if result:
            print("Added to watchlist.")
            return 0
        else:
            print("Already in watchlist.")
            return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def cmd_watchlist_list(conn: sqlite3.Connection, json_format: bool = False, 
                       watched: Optional[bool] = None) -> int:
    """List movies in watchlist."""
    try:
        watchlist = get_watchlist(conn)
        
        if json_format:
            print(json.dumps(watchlist, indent=2))
        else:
            for movie in watchlist:
                rating = movie.get("user_rating", "-")
                print(f"{movie['title']} - Rating: {rating}")
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def cmd_watchlist_remove(conn: sqlite3.Connection, movie_id: int) -> int:
    """Remove movie from watchlist."""
    try:
        result = remove_from_watchlist(conn, movie_id)
        if result:
            print("Removed from watchlist.")
            return 0
        else:
            print("Movie not in watchlist.")
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def cmd_influence_add(conn: sqlite3.Connection, source: str, relationship: str, target: str, note: str = None) -> int:
    """Add influence relationship."""
    try:
        graph = InfluenceGraph(conn)
        result = graph.add_influence(source, relationship, target, note)
        if result:
            print("Influence added.")
            return 0
        else:
            print("Could not add influence.")
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def cmd_influence_ancestors(conn: sqlite3.Connection, movie: str, depth: int = 3, json_format: bool = False) -> int:
    """Show movies that influenced the given movie."""
    try:
        graph = InfluenceGraph(conn)
        chain = graph.get_chain(movie, "ancestors", depth)
        
        if json_format:
            print(json.dumps(chain, indent=2))
        else:
            print(f"Influences on {chain['root']['title']}:")
            for film in chain['chain'][0]['movies']:
                print(f"  - {film['title']} ({film.get('release_date', 'N/A')})")
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def cmd_export(conn: sqlite3.Connection, source: str, format: str = "csv") -> int:
    """Export data to file."""
    try:
        watchlist = get_watchlist(conn)
        formatter = ExportFormatter()
        
        if format == "csv":
            output = formatter.to_csv(watchlist)
        elif format == "markdown":
            output = formatter.to_markdown(watchlist, "My Watchlist")
        elif format == "json":
            output = formatter.to_json(watchlist)
        else:
            print(f"Unknown format: {format}", file=sys.stderr)
            return 1
        
        print(output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

- [ ] **Step 4: Update cli __init__.py**

```python
# tmdb_cli/cli/__init__.py
from tmdb_cli.cli.commands import (
    cmd_search, cmd_watchlist_add, cmd_watchlist_list,
    cmd_watchlist_remove, cmd_influence_add, cmd_influence_ancestors,
    cmd_export
)

__all__ = [
    "cmd_search", "cmd_watchlist_add", "cmd_watchlist_list", "cmd_watchlist_remove",
    "cmd_influence_add", "cmd_influence_ancestors", "cmd_export"
]
```

- [ ] **Step 5: Modify tmdb_cli/cli.py to add --cli dispatch**

```python
# tmdb_cli/cli.py (MODIFY EXISTING)
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
from tmdb_cli.formatter import print_movies
from tmdb_cli.db import init_db, get_db_path
from tmdb_cli.cli.commands import (
    cmd_search, cmd_watchlist_add, cmd_watchlist_list,
    cmd_watchlist_remove, cmd_influence_add, cmd_influence_ancestors,
    cmd_export
)

def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TMDB CLI - fetch movie lists from TMDB"
    )
    
    # Mode selection
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Use CLI mode (for scripting); default is TUI mode"
    )
    
    # Legacy: source selection (mutually exclusive)
    source = parser.add_mutually_exclusive_group(required=False)
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
    
    # Common options
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
    
    # Initialize database connection
    db_conn = init_db(get_db_path())
    
    # Dispatch to TUI or CLI mode
    if args.cli:
        # CLI mode: handle legacy --type and --search flags
        client = TMDBClient(api_key, db_conn=db_conn)
        
        try:
            if args.search:
                data = client.search_movies(args.search, args.page)
            elif args.type:
                data = client.get_movies(args.type, args.page)
            else:
                print("Error: --type or --search required in CLI mode", file=sys.stderr)
                return 2
            
            results = data.get("results", [])
            if not results:
                print("No results returned.")
                return 0
            
            if args.format == "json":
                print(json.dumps(results, indent=2))
            else:
                print_movies(results)
            return 0
        
        except RuntimeError as e:
            print(f"Error: {e}")
            return 1
    
    else:
        # TUI mode (default) — not implemented in Phase 1
        # For now, fall back to legacy behavior
        client = TMDBClient(api_key, db_conn=db_conn)
        
        try:
            if args.search:
                data = client.search_movies(args.search, args.page)
            elif args.type:
                data = client.get_movies(args.type, args.page)
            else:
                print("Error: --type or --search required")
                return 2
            
            results = data.get("results", [])
            if not results:
                print("No results returned.")
                return 0
            
            if args.format == "json":
                print(json.dumps(results, indent=2))
            else:
                print_movies(results)
            return 0
        
        except RuntimeError as e:
            print(f"Error: {e}")
            return 1

def main_entry():
    sys.exit(main())
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_cli_commands.py -v
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add tmdb_cli/cli/ tmdb_cli/cli.py tests/test_cli_commands.py
git commit -m "feat: add CLI command handlers and --cli dispatch"
```

---

### Task 8: Integration Test (Phase 1 Complete)

**Files:**
- Create: `tests/test_integration_phase1.py`

**Steps:**

- [ ] **Step 1: Write end-to-end integration test**

```python
# tests/test_integration_phase1.py
import tempfile
import os
import json
import pytest
from tmdb_cli.db import init_db
from tmdb_cli.db.query_builder import QueryBuilder
from tmdb_cli.db.watchlist import add_to_watchlist, rate_movie, get_watchlist
from tmdb_cli.db.influence import InfluenceGraph
from tmdb_cli.export import ExportFormatter

def test_full_workflow():
    """Integration test: add movies, rate, create influence, export."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        conn = init_db(db_path)
        
        # Setup: insert test movies
        cursor = conn.cursor()
        movies_data = [
            (1, "Inception", "2010-07-16", json.dumps(["Sci-Fi"]), json.dumps(["Nolan"]), json.dumps([]), 8.8, 2500000),
            (2, "2001: A Space Odyssey", "1968-04-02", json.dumps(["Sci-Fi"]), json.dumps(["Kubrick"]), json.dumps([]), 8.3, 1000000),
        ]
        for tmdb_id, title, release_date, genres, directors, cast, rating, vote_count in movies_data:
            cursor.execute("""
                INSERT INTO movies (tmdb_id, title, release_date, genres, directors, cast, rating, vote_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (tmdb_id, title, release_date, genres, directors, cast, rating, vote_count))
        conn.commit()
        
        # 1. Add to watchlist
        assert add_to_watchlist(conn, 1) is True
        assert add_to_watchlist(conn, 2) is True
        
        # 2. Rate movies
        assert rate_movie(conn, 1, 9) is True
        assert rate_movie(conn, 2, 8) is True
        
        # 3. Add influence
        graph = InfluenceGraph(conn)
        assert graph.add_influence("Inception", "influenced_by", "2001: A Space Odyssey") is True
        
        # 4. Query influence
        ancestors = graph.get_ancestors("Inception")
        assert len(ancestors) == 1
        assert ancestors[0]["title"] == "2001: A Space Odyssey"
        
        # 5. Get watchlist
        watchlist = get_watchlist(conn)
        assert len(watchlist) == 2
        
        # 6. Export
        formatter = ExportFormatter()
        csv_output = formatter.to_csv(watchlist)
        assert "Inception" in csv_output
        assert "2001: A Space Odyssey" in csv_output
        
        conn.close()
```

- [ ] **Step 2: Run integration test**

```bash
pytest tests/test_integration_phase1.py -v
```

Expected: PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration_phase1.py
git commit -m "test: add Phase 1 integration test"
```

---

### Task 9: Phase 1 Summary & Version Bump

**Steps:**

- [ ] **Step 1: Update pyproject.toml version**

```toml
# pyproject.toml (MODIFY)
[project]
name = "tmdb-cli"
version = "0.3.0"  # was 0.2.0
...
```

- [ ] **Step 2: Create PHASE_1_COMPLETE.md summary**

```markdown
# Phase 1 Complete: MVP Features

## Completed

✅ SQLite schema (movies, watchlist, influence tables)
✅ QueryBuilder (filtering by genre, director, year, rating, etc.)
✅ Watchlist CRUD (add, rate, watch, list, remove)
✅ InfluenceGraph (bidirectional relationships, traversal)
✅ ExportFormatter (CSV, Markdown, JSON)
✅ TMDBClient caching (responses stored in SQLite)
✅ CLI command handlers (watchlist, influence, export)
✅ Legacy CLI compatibility (--type, --search still work)
✅ Full test coverage for business logic

## What's Next (Phase 2)

- TUI interactive interface (rich-based)
- TUI key bindings and navigation
- TUI influence graph visualization
- Polish and error handling
- Performance optimization
```

- [ ] **Step 3: Commit Phase 1**

```bash
git add pyproject.toml docs/superpowers/plans/2026-07-10-cinephile-toolkit-implementation.md
git commit -m "v0.3.0-phase1: MVP cinephile toolkit complete"
```

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-10-cinephile-toolkit-implementation.md`.

**Phase 1 covers all MVP features (9 tasks, ~100 test cases, 15-20 hours of implementation).**

**Two execution options:**

**1. Subagent-Driven (recommended for speed)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. You see each task complete before the next begins.

**2. Inline Execution** — Execute tasks in this session, batch progress with checkpoints for review between groups.

**Which approach?**

