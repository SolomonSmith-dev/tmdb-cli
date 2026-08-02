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
