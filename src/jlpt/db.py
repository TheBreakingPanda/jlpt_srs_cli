import sqlite3
from pathlib import Path
from typing import Optional


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a database connection.

    Args:
        db_path: Path to the database file. Defaults to the project's data/jlpt.db.

    Returns:
        sqlite3.Connection: Database connection object
    """
    if db_path is None:
        path = Path(__file__).resolve().parents[2] / "data" / "jlpt.db"
    else:
        path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create database schema for cards and reviews tables.
    
    Args:
        conn: Database connection object
    """
    cursor = conn.cursor()
    
    # Create cards table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            card_id     TEXT PRIMARY KEY,
            source      TEXT NOT NULL,
            front       TEXT NOT NULL,
            back        TEXT,
            reading     TEXT,
            ease_factor REAL    DEFAULT 2.5,
            interval    INTEGER DEFAULT 0,
            repetitions INTEGER DEFAULT 0,
            due_date    TEXT,
            created_at  TEXT DEFAULT (date('now')),
            updated_at  TEXT DEFAULT (date('now'))
        )
    """)
    
    # Create reviews table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id        TEXT NOT NULL,
            reviewed_at    TEXT DEFAULT (datetime('now')),
            grade          INTEGER NOT NULL,
            interval_after INTEGER,
            ease_after     REAL,
            FOREIGN KEY (card_id) REFERENCES cards(card_id)
        )
    """)
    
    conn.commit()


def init_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Initialize database connection and create schema if needed.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        sqlite3.Connection: Initialized database connection
    """
    conn = get_db_connection(db_path)
    create_schema(conn)
    return conn
