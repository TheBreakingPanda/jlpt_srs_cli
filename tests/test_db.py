import sqlite3
from datetime import date

import pytest

from jlpt import db
from jlpt.db import create_schema
from jlpt.review import apply_review


def test_init_db_creates_both_tables(conn, step):
    step("query sqlite_master for table names")
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    step(f"tables present: {sorted(tables)}")
    assert {"cards", "reviews"} <= tables


def test_cards_defaults(conn, step):
    step("insert a minimal card (card_id, source, front only)")
    conn.execute(
        "INSERT INTO cards (card_id, source, front) VALUES ('X1', 'word_bank', '本')"
    )
    conn.commit()
    step("read back SRS columns + timestamps")
    row = conn.execute(
        "SELECT ease_factor, interval, repetitions, due_date, created_at, updated_at "
        "FROM cards WHERE card_id='X1'"
    ).fetchone()

    step("assert schema defaults applied (ease 2.5 / interval 0 / reps 0 / due NULL / stamps set)")
    assert row["ease_factor"] == 2.5
    assert row["interval"] == 0
    assert row["repetitions"] == 0
    assert row["due_date"] is None
    assert row["created_at"] is not None   # date('now') fired
    assert row["updated_at"] is not None


def test_foreign_keys_are_enforced(conn, step):
    step("insert a review referencing a non-existent card")
    step("expect IntegrityError because PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO reviews (card_id, grade) VALUES ('nonexistent', 4)"
        )
        conn.commit()


def test_schema_is_idempotent(conn, step):
    step("call create_schema() again on an already-initialised DB")
    create_schema(conn)
    step("no exception -> CREATE TABLE IF NOT EXISTS is idempotent")


# --- migration ---------------------------------------------------------------

# The reviews table exactly as pre-Phase-3 decks have it (copied from a real
# one): no *_before snapshot columns.
_OLD_REVIEWS_DDL = """
    CREATE TABLE reviews (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id        TEXT NOT NULL,
        reviewed_at    TEXT DEFAULT (datetime('now')),
        grade          INTEGER NOT NULL,
        interval_after INTEGER,
        ease_after     REAL,
        FOREIGN KEY (card_id) REFERENCES cards(card_id)
    )
"""
_SNAPSHOT = {"ease_before", "interval_before", "repetitions_before", "due_before"}


def _review_columns(conn):
    return {row[1] for row in conn.execute("PRAGMA table_info(reviews)")}


@pytest.fixture
def old_conn(conn):
    """The `conn` fixture rebuilt with a pre-snapshot reviews table, holding
    one reviewed card and its review - a miniature of a real old deck."""
    conn.execute("DROP TABLE reviews")
    conn.execute(_OLD_REVIEWS_DDL)
    conn.execute(
        "INSERT INTO cards (card_id, source, front, back, reading, ease_factor, "
        "interval, repetitions, due_date) "
        "VALUES ('EO001', 'word_bank', '本', 'book', 'ほん', 2.6, 6, 2, '2026-10-10')"
    )
    conn.execute(
        "INSERT INTO reviews (card_id, reviewed_at, grade, interval_after, ease_after) "
        "VALUES ('EO001', '2026-10-04 09:00:00', 5, 6, 2.6)"
    )
    conn.commit()
    return conn


def test_migrate_adds_missing_snapshot_columns(old_conn, step):
    step("old deck: reviews has no *_before columns")
    assert not _SNAPSHOT & _review_columns(old_conn)
    step("migrate, then expect all four present")
    added = db.migrate(old_conn)
    assert set(added) == _SNAPSHOT
    assert _SNAPSHOT <= _review_columns(old_conn)


def test_migrate_keeps_existing_rows(old_conn, step):
    db.migrate(old_conn)
    step("the old review survives with its values; snapshots are NULL")
    row = old_conn.execute("SELECT * FROM reviews").fetchone()
    assert (row["card_id"], row["grade"], row["interval_after"], row["ease_after"]) \
        == ("EO001", 5, 6, 2.6)
    assert all(row[c] is None for c in _SNAPSHOT)
    step("the card's schedule is untouched")
    card = old_conn.execute("SELECT * FROM cards").fetchone()
    assert (card["ease_factor"], card["interval"], card["due_date"]) == (2.6, 6, "2026-10-10")


def test_migrate_is_idempotent(old_conn):
    db.migrate(old_conn)
    assert db.migrate(old_conn) == []


def test_migrate_is_a_noop_on_a_current_deck(conn):
    assert db.migrate(conn) == []


def test_migrate_completes_a_partial_schema(old_conn):
    old_conn.execute("ALTER TABLE reviews ADD COLUMN ease_before REAL")
    assert set(db.migrate(old_conn)) == _SNAPSHOT - {"ease_before"}
    assert _SNAPSHOT <= _review_columns(old_conn)


def test_reviewing_works_after_migration(old_conn, step):
    step("before migrating, apply_review fails: no column ease_before")
    with pytest.raises(sqlite3.OperationalError):
        apply_review(old_conn, "EO001", 5, date(2026, 10, 10))
    step("after migrating, the same review succeeds and records a snapshot")
    db.migrate(old_conn)
    apply_review(old_conn, "EO001", 5, date(2026, 10, 10))
    latest = old_conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchone()
    assert latest["ease_before"] == 2.6


def test_init_db_migrates_an_old_file(tmp_path, step):
    path = tmp_path / "old.db"
    step("build an old-schema deck on disk")
    raw = sqlite3.connect(path)
    create_schema(raw)
    raw.execute("DROP TABLE reviews")
    raw.execute(_OLD_REVIEWS_DDL)
    raw.commit()
    raw.close()
    step("opening it through init_db upgrades it")
    conn = db.init_db(str(path))
    assert _SNAPSHOT <= _review_columns(conn)
    conn.close()

