"""SQLite access: open a connection, create the schema, migrate older decks, or
do all three (init_db).

The schema defined here is the single source of truth - the tests build their
in-memory databases by calling `create_schema`, not a hand-copied CREATE TABLE.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from jlpt import config

logger = logging.getLogger(__name__)


# --- connection --------------------------------------------------------------

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a database connection.

    Args:
        db_path: Path to the database file. Defaults to the user-data deck
            (config.default_db_path), the same place the CLI resolves to.

    Returns:
        sqlite3.Connection: Database connection object
    """
    path = Path(db_path) if db_path is not None else Path(config.default_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # off by default in SQLite
    return conn


# --- schema ------------------------------------------------------------------

def create_schema(conn: sqlite3.Connection) -> None:
    """Create database schema for cards and reviews tables.

    Args:
        conn: Database connection object
    """
    cursor = conn.cursor()

    # cards: vocabulary content + SRS scheduling state.
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

    # reviews: one row per graded review, FK back to the card.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id        TEXT NOT NULL,
            reviewed_at    TEXT DEFAULT (datetime('now')),
            grade          INTEGER NOT NULL,
            interval_after INTEGER,
            ease_after     REAL,
            ease_before        REAL,
            interval_before    INTEGER,
            repetitions_before INTEGER,
            due_before         TEXT,
            FOREIGN KEY (card_id) REFERENCES cards(card_id)
        )
    """)

    conn.commit()


# --- migration (older decks -> current schema) -------------------------------

# Undo's snapshot columns, added to `reviews` in Phase 3. Decks created before
# that have a `reviews` table without them, and CREATE TABLE IF NOT EXISTS
# never alters an existing table - so `migrate` adds them in place.
_REVIEW_SNAPSHOT_COLUMNS = (
    ("ease_before", "REAL"),
    ("interval_before", "INTEGER"),
    ("repetitions_before", "INTEGER"),
    ("due_before", "TEXT"),
)


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Bring an older deck up to the current schema, in place. Idempotent.

    Only ever ADDS columns, so no data is touched: existing review rows get
    NULL snapshots, which `undo` treats as "no prior state to restore".
    All additions run in one transaction (SQLite's DDL is transactional), so a
    deck is never left half-migrated. Returns the names of the columns added.
    """
    # PRAGMA table_info rows: (cid, name, type, notnull, default, pk).
    existing = {row[1] for row in conn.execute("PRAGMA table_info(reviews)")}
    missing = [(n, t) for n, t in _REVIEW_SNAPSHOT_COLUMNS if n not in existing]
    if not missing:
        return []

    with conn:
        # sqlite3 only opens transactions implicitly before DML, not DDL,
        # so open one explicitly to make the ALTERs all-or-nothing.
        conn.execute("BEGIN")
        for name, type_ in missing:
            # Interpolating is safe: names and types come from the constant above.
            conn.execute(f"ALTER TABLE reviews ADD COLUMN {name} {type_}")

    added = [name for name, _ in missing]
    logger.info("migrated reviews table: added %s", ", ".join(added))
    return added


# --- init (connect + schema + migrate) ---------------------------------------

def init_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open a deck ready for use: connect, create any missing tables, and
    migrate an older schema. Every CLI command opens its deck through here,
    so an old deck is upgraded on its first use, whichever command that is.

    Args:
        db_path: Path to the database file

    Returns:
        sqlite3.Connection: Initialized database connection
    """
    conn = get_db_connection(db_path)
    create_schema(conn)
    migrate(conn)
    return conn

