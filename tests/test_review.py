from datetime import timedelta

from jlpt.review import apply_review, due_cards
import pytest


def insert_card(conn, card_id, due_date):
    """Insert a minimal card; due_date is the only field this suite cares about."""
    conn.execute(
        "INSERT INTO cards (card_id, source, front, back, reading, due_date) "
        "VALUES (?, 'test_source', 'f', 'b', 'r', ?)",
        (card_id, due_date),
    )


def test_due_selection_and_ordering(conn, today):
    insert_card(conn, "C001", today.isoformat())                        # due today
    insert_card(conn, "C002", (today + timedelta(days=1)).isoformat())  # not due yet
    insert_card(conn, "C003", (today - timedelta(days=3)).isoformat())  # overdue
    insert_card(conn, "C004", None)                                     # never reviewed
    conn.commit()

    due_ids = [row["card_id"] for row in due_cards(conn, today)]

    # overdue first, then today, then new — C002 (future) excluded
    assert due_ids == ["C003", "C001", "C004"]

def test_due_selection_empty(conn, today):
    # no cards at all
    assert due_cards(conn, today) == []

    # no cards due
    insert_card(conn, "C001", (today + timedelta(days=1)).isoformat())
    insert_card(conn, "C002", (today + timedelta(days=2)).isoformat())
    conn.commit()
    assert due_cards(conn, today) == []

def test_due_selection_all_due(conn, today):
    insert_card(conn, "C001", (today - timedelta(days=1)).isoformat())
    insert_card(conn, "C002", (today - timedelta(days=2)).isoformat())
    insert_card(conn, "C003", None)
    conn.commit()

    due_ids = [row["card_id"] for row in due_cards(conn, today)]
    assert due_ids == ["C002", "C001", "C003"]

def test_apply_review_updates_card_and_records_review(conn, today):
    insert_card(conn, "C001", (today - timedelta(days=1)).isoformat())
    conn.execute(
        "UPDATE cards SET ease_factor = 2.5, interval = 1, repetitions = 1 "
        "WHERE card_id = 'C001'"
    )
    conn.commit()

    new_due_date = apply_review(conn, "C001", grade=5, today=today)

    card = conn.execute("SELECT * FROM cards WHERE card_id = 'C001'").fetchone()
    assert card["ease_factor"] == pytest.approx(2.6)
    assert card["interval"] == 6
    assert card["repetitions"] == 2
    assert card["due_date"] == (today + timedelta(days=6)).isoformat()
    assert card["due_date"] == new_due_date

    assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
    review = conn.execute("SELECT * FROM reviews WHERE card_id = 'C001'").fetchone()
    assert review["grade"] == 5
    assert review["interval_after"] == 6
    assert review["ease_after"] == pytest.approx(2.6)

def test_review_failed(conn, today):
    insert_card(conn, "C002", (today - timedelta(days=1)).isoformat())
    conn.execute(
        "UPDATE cards SET ease_factor = 2.5, interval = 6, repetitions = 2 "
        "WHERE card_id = 'C002'"
    )
    conn.commit()

    new_due_date = apply_review(conn, "C002", grade=2, today=today)

    card = conn.execute("SELECT * FROM cards WHERE card_id = 'C002'").fetchone()
    assert card["ease_factor"] == pytest.approx(2.5)  # unchanged
    assert card["interval"] == 1                      # reset to first interval
    assert card["repetitions"] == 0                   # reset to zero
    assert card["due_date"] == (today + timedelta(days=1)).isoformat()
    assert card["due_date"] == new_due_date

    review = conn.execute("SELECT * FROM reviews WHERE card_id = 'C002'").fetchone()
    assert review["grade"] == 2
    assert review["interval_after"] == 1
    assert review["ease_after"] == pytest.approx(2.5)

def test_apply_review_nonexistent_card(conn, today):
    with pytest.raises(ValueError, match="Card with ID C999 not found."):
        apply_review(conn, "C999", grade=4, today=today)