"""Review persistence - the database side of a study session.

`due_cards` selects what to study; `apply_review` is the seam where the pure
SM-2 scheduler (srs.py) meets the database, writing the card's new state and the
review-history row together. The maths lives in srs.py; all I/O lives here.
"""

from jlpt import srs

# --- config ------------------------------------------------------------------

DEFAULT_NEW_LIMIT = 25   # module-level, so the CLI's --new default reads the same value


# --- due-card selection ------------------------------------------------------

def due_cards(conn, today, new_limit=DEFAULT_NEW_LIMIT):
    """Cards to study today: every due review, plus up to `new_limit`
    never-seen cards."""
    new_limit = max(0, new_limit)   # SQLite treats LIMIT -1 as "no limit"

    # Reviews: previously-seen cards whose due_date has arrived - all of them.
    reviews = conn.execute(
        """
        SELECT card_id, front, reading, back, ease_factor, interval, repetitions, due_date
        FROM cards
        WHERE due_date IS NOT NULL AND due_date <= ?
        ORDER BY due_date
        """,
        (today.isoformat(),),
    ).fetchall()

    # New: never-reviewed cards (due_date IS NULL), capped at new_limit.
    new = conn.execute(
        """
        SELECT card_id, front, reading, back, ease_factor, interval, repetitions, due_date
        FROM cards
        WHERE due_date IS NULL
        ORDER BY card_id
        LIMIT ?
        """,
        (new_limit,),
    ).fetchall()

    return reviews + new


# --- grading a review (the persistence seam) ---------------------------------

def apply_review(conn, card_id, grade, today):
    """Grade a review: reschedule the card and record the review, atomically.

    Loads the card's current SRS state, runs it through the pure
    scheduler, then writes the new state to `cards` and appends a
    `reviews` row in a single transaction. Returns the new due date
    as an ISO string.
    """
    # Load current SRS state; a missing id is a programming error, not a no-op.
    cur = conn.execute(
        "SELECT ease_factor, interval, repetitions, due_date FROM cards WHERE card_id = ?",
        (card_id,),
    )
    card = cur.fetchone()
    if card is None:
        raise ValueError(f"Card with ID {card_id} not found.")

    # Pure maths: hand the state + grade to the scheduler, take the next state.
    sched = srs.schedule(
        card["ease_factor"], card["interval"], card["repetitions"], grade, today
    )
    new_due_date = sched.due_date.isoformat()

    # Persist both writes together - card state and history never half-exist.
    with conn:
        conn.execute(
            """
            UPDATE cards
            SET ease_factor = ?, interval = ?, repetitions = ?, due_date = ?
            WHERE card_id = ?
            """,
            (sched.ease_factor, sched.interval, sched.repetitions,
             new_due_date, card_id),
        )
        conn.execute(
            """
            INSERT INTO reviews (
                card_id, grade, interval_after, ease_after,
                ease_before, interval_before, repetitions_before, due_before
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card_id, grade, sched.interval, sched.ease_factor,
                card["ease_factor"], card["interval"], card["repetitions"],
                card["due_date"],
            ),
        )

    return new_due_date
