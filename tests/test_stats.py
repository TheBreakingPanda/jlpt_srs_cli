from datetime import timedelta

from jlpt import stats


def _add_card(conn, card_id, due_date=None):
    conn.execute(
        "INSERT INTO cards (card_id, source, front, back, reading, due_date) "
        "VALUES (?, 'test', 'f', 'b', 'r', ?)",
        (card_id, due_date),
    )


def _add_review(conn, card_id, reviewed_at, grade):
    conn.execute(
        "INSERT INTO reviews (card_id, reviewed_at, grade) VALUES (?, ?, ?)",
        (card_id, reviewed_at, grade),
    )


# --- totals / due / reviewed-today / accuracy --------------------------------

def test_empty_deck_is_all_zero(conn, today, step):
    step("gather_stats on an empty deck")
    s = stats.gather_stats(conn, today)
    assert s["total_cards"] == 0
    assert s["total_reviews"] == 0
    assert s["due_today"] == 0
    assert s["reviews_today"] == 0
    assert s["streak"] == 0
    assert s["accuracy"] == 0.0


def test_totals_and_due_today(conn, today, step):
    step("insert overdue, due-today, future, and new cards")
    _add_card(conn, "C1", (today - timedelta(days=1)).isoformat())  # overdue
    _add_card(conn, "C2", today.isoformat())                        # due today
    _add_card(conn, "C3", (today + timedelta(days=1)).isoformat())  # future
    _add_card(conn, "C4", None)                                     # new (not "due")
    conn.commit()

    s = stats.gather_stats(conn, today)
    assert s["total_cards"] == 4
    assert s["due_today"] == 2     # overdue + today only


def test_reviewed_today_counts_only_today(conn, today, step):
    _add_card(conn, "C1")
    _add_review(conn, "C1", today.isoformat(), 5)
    _add_review(conn, "C1", (today - timedelta(days=1)).isoformat(), 5)
    conn.commit()

    assert stats.gather_stats(conn, today)["reviews_today"] == 1


def test_accuracy_is_passes_over_total(conn, today, step):
    step("2 passes (grade 5, 4) and 2 fails (grade 2, 1)")
    _add_card(conn, "C1")
    for grade in (5, 4, 2, 1):
        _add_review(conn, "C1", today.isoformat(), grade)
    conn.commit()

    s = stats.gather_stats(conn, today)
    assert s["total_reviews"] == 4
    assert s["total_passes"] == 2
    assert s["accuracy"] == 50.0


# --- streak ------------------------------------------------------------------

def test_streak_counts_run_ending_today(conn, today, step):
    _add_card(conn, "C1")
    for i in range(3):   # today, today-1, today-2
        _add_review(conn, "C1", (today - timedelta(days=i)).isoformat(), 5)
    conn.commit()
    assert stats.gather_stats(conn, today)["streak"] == 3


def test_streak_survives_an_unreviewed_today(conn, today, step):
    step("reviewed yesterday + the day before, nothing today -> grace keeps it alive")
    _add_card(conn, "C1")
    _add_review(conn, "C1", (today - timedelta(days=1)).isoformat(), 5)
    _add_review(conn, "C1", (today - timedelta(days=2)).isoformat(), 5)
    conn.commit()
    assert stats.gather_stats(conn, today)["streak"] == 2


def test_streak_breaks_after_a_full_missed_day(conn, today, step):
    step("reviewed 2 and 3 days ago, but missed both today AND yesterday -> 0")
    _add_card(conn, "C1")
    _add_review(conn, "C1", (today - timedelta(days=2)).isoformat(), 5)
    _add_review(conn, "C1", (today - timedelta(days=3)).isoformat(), 5)
    conn.commit()
    assert stats.gather_stats(conn, today)["streak"] == 0


def test_streak_stops_at_an_internal_gap(conn, today, step):
    step("reviewed today and 2 days ago (skipped yesterday) -> only today counts")
    _add_card(conn, "C1")
    _add_review(conn, "C1", today.isoformat(), 5)
    _add_review(conn, "C1", (today - timedelta(days=2)).isoformat(), 5)
    conn.commit()
    assert stats.gather_stats(conn, today)["streak"] == 1