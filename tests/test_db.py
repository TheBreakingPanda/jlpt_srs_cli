import sqlite3

import pytest

from jlpt.db import create_schema


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
