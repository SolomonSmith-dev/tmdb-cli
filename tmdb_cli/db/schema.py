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
