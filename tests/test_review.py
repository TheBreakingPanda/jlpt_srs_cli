from datetime import timedelta

import pytest

from jlpt.review import apply_review, due_cards


def insert_card(conn, card_id, due_date):
    """Insert a minimal card; due_date is the only field this suite cares about."""
    conn.execute(
        "INSERT INTO cards (card_id, source, front, back, reading, due_date) "
        "VALUES (?, 'test_source', 'f', 'b', 'r', ?)",
        (card_id, due_date),
    )


def test_due_selection_and_ordering(conn, today, step):
    step("insert C001 (due today), C002 (future), C003 (overdue), C004 (never reviewed)")
    insert_card(conn, "C001", today.isoformat())
    insert_card(conn, "C002", (today + timedelta(days=1)).isoformat())
    insert_card(conn, "C003", (today - timedelta(days=3)).isoformat())
    insert_card(conn, "C004", None)
    conn.commit()

    step("call due_cards(today) and collect the ids")
    due_ids = [row["card_id"] for row in due_cards(conn, today)]
    step(f"due_ids = {due_ids}")

    step("assert overdue first, then today, then new — C002 (future) excluded")
    assert due_ids == ["C003", "C001", "C004"]


def test_due_selection_empty(conn, today, step):
    step("empty DB -> due_cards returns []")
    assert due_cards(conn, today) == []

    step("insert two future-dated cards")
    insert_card(conn, "C001", (today + timedelta(days=1)).isoformat())
    insert_card(conn, "C002", (today + timedelta(days=2)).isoformat())
    conn.commit()
    step("still nothing due -> []")
    assert due_cards(conn, today) == []


def test_due_selection_all_due(conn, today, step):
    step("insert two overdue cards + one never-reviewed")
    insert_card(conn, "C001", (today - timedelta(days=1)).isoformat())
    insert_card(conn, "C002", (today - timedelta(days=2)).isoformat())
    insert_card(conn, "C003", None)
    conn.commit()

    step("call due_cards and check ordering (oldest overdue first, new last)")
    due_ids = [row["card_id"] for row in due_cards(conn, today)]
    step(f"due_ids = {due_ids}")
    assert due_ids == ["C002", "C001", "C003"]


def test_new_cards_capped_at_limit(conn, today, step):
    step("insert 30 never-reviewed cards")
    for i in range(30):
        insert_card(conn, f"N{i:02d}", None)
    conn.commit()

    step("due_cards(new_limit=25) returns exactly 25 new cards")
    due = due_cards(conn, today, new_limit=25)
    assert len(due) == 25

    step("and they are the first 25 by card_id (deterministic order)")
    assert [row["card_id"] for row in due] == [f"N{i:02d}" for i in range(25)]


def test_new_limit_zero_returns_reviews_only(conn, today, step):
    step("insert one overdue review + three new cards")
    insert_card(conn, "R1", (today - timedelta(days=1)).isoformat())
    for i in range(3):
        insert_card(conn, f"N{i}", None)
    conn.commit()

    step("new_limit=0 -> only the review, no new cards")
    due_ids = [row["card_id"] for row in due_cards(conn, today, new_limit=0)]
    assert due_ids == ["R1"]


def test_reviews_uncapped_while_new_capped(conn, today, step):
    step("insert 3 overdue reviews + 30 new cards")
    insert_card(conn, "R1", (today - timedelta(days=1)).isoformat())
    insert_card(conn, "R2", (today - timedelta(days=2)).isoformat())
    insert_card(conn, "R3", (today - timedelta(days=3)).isoformat())
    for i in range(30):
        insert_card(conn, f"N{i:02d}", None)
    conn.commit()

    step("new_limit=5 -> all 3 reviews (uncapped) + exactly 5 new = 8")
    due_ids = [row["card_id"] for row in due_cards(conn, today, new_limit=5)]
    step(f"due_ids = {due_ids}")
    assert due_ids[:3] == ["R3", "R2", "R1"]        # reviews, oldest-due first
    assert len(due_ids) == 8
    assert due_ids[3:] == [f"N{i:02d}" for i in range(5)]


def test_negative_new_limit_is_clamped(conn, today, step):
    step("insert 3 new cards")
    for i in range(3):
        insert_card(conn, f"N{i}", None)
    conn.commit()
    step("a negative new_limit must clamp to 0 (SQLite treats LIMIT -1 as unlimited)")
    assert due_cards(conn, today, new_limit=-5) == []


def test_apply_review_updates_card_and_records_review(conn, today, step):
    step("insert C001 with known SRS state (ease 2.5, interval 1, reps 1)")
    insert_card(conn, "C001", (today - timedelta(days=1)).isoformat())
    conn.execute(
        "UPDATE cards SET ease_factor = 2.5, interval = 1, repetitions = 1 "
        "WHERE card_id = 'C001'"
    )
    conn.commit()

    step("apply_review(grade=5) — a strong pass")
    new_due_date = apply_review(conn, "C001", grade=5, today=today)
    step(f"returned new_due_date = {new_due_date}")

    step("assert the card advanced to the scheduled values")
    card = conn.execute("SELECT * FROM cards WHERE card_id = 'C001'").fetchone()
    assert card["ease_factor"] == pytest.approx(2.6)
    assert card["interval"] == 6
    assert card["repetitions"] == 2
    assert card["due_date"] == (today + timedelta(days=6)).isoformat()
    assert card["due_date"] == new_due_date

    step("assert exactly one reviews row was written, with the right values")
    assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
    review = conn.execute("SELECT * FROM reviews WHERE card_id = 'C001'").fetchone()
    assert review["grade"] == 5
    assert review["interval_after"] == 6
    assert review["ease_after"] == pytest.approx(2.6)


def test_review_failed(conn, today, step):
    step("insert C002 mid-progression (ease 2.5, interval 6, reps 2)")
    insert_card(conn, "C002", (today - timedelta(days=1)).isoformat())
    conn.execute(
        "UPDATE cards SET ease_factor = 2.5, interval = 6, repetitions = 2 "
        "WHERE card_id = 'C002'"
    )
    conn.commit()

    step("apply_review(grade=2) — a fail")
    new_due_date = apply_review(conn, "C002", grade=2, today=today)
    step(f"returned new_due_date = {new_due_date}")

    step("assert the fail reset repetitions/interval, left ease flat, due tomorrow")
    card = conn.execute("SELECT * FROM cards WHERE card_id = 'C002'").fetchone()
    assert card["ease_factor"] == pytest.approx(2.5)  # unchanged
    assert card["interval"] == 1                      # reset to first interval
    assert card["repetitions"] == 0                   # reset to zero
    assert card["due_date"] == (today + timedelta(days=1)).isoformat()
    assert card["due_date"] == new_due_date

    step("assert the reviews row records grade 2 / interval_after 1")
    review = conn.execute("SELECT * FROM reviews WHERE card_id = 'C002'").fetchone()
    assert review["grade"] == 2
    assert review["interval_after"] == 1
    assert review["ease_after"] == pytest.approx(2.5)


def test_apply_review_nonexistent_card(conn, today, step):
    step("apply_review on a bogus card_id -> expect ValueError")
    with pytest.raises(ValueError, match="Card with ID C999 not found."):
        apply_review(conn, "C999", grade=4, today=today)