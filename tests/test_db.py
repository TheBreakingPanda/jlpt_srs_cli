import sqlite3
import pytest

from jlpt.db import create_schema


def test_init_db_creates_both_tables(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"cards", "reviews"} <= tables


def test_cards_defaults(conn):
    # a minimal insert should get the schema defaults, not nulls
    conn.execute(
        "INSERT INTO cards (card_id, source, front) VALUES ('X1', 'word_bank', '本')"
    )
    conn.commit()
    row = conn.execute(
        "SELECT ease_factor, interval, repetitions, due_date, created_at, updated_at "
        "FROM cards WHERE card_id='X1'"
    ).fetchone()

    assert row["ease_factor"] == 2.5
    assert row["interval"] == 0
    assert row["repetitions"] == 0
    assert row["due_date"] is None
    assert row["created_at"] is not None   # date('now') fired
    assert row["updated_at"] is not None


def test_foreign_keys_are_enforced(conn):
    # PRAGMA foreign_keys = ON in db.py means a review for a missing card raises
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO reviews (card_id, grade) VALUES ('nonexistent', 4)"
        )
        conn.commit()


def test_schema_is_idempotent(conn):
    # CREATE TABLE IF NOT EXISTS -> calling it again must not raise
    create_schema(conn)