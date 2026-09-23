import sqlite3
from datetime import date

from jlpt import srs

DEFAULT_NEW_LIMIT = 25   # module-level, so the CLI's --new default reads the same value

def due_cards(conn, today, new_limit=DEFAULT_NEW_LIMIT):
    """Cards to study today: every due review, plus up to `new_limit`
    never-seen cards."""
    new_limit = max(0, new_limit)   # SQLite treats LIMIT -1 as "no limit"

    reviews = conn.execute(
        """
        SELECT card_id, front, reading, back, ease_factor, interval, repetitions, due_date
        FROM cards
        WHERE due_date IS NOT NULL AND due_date <= ?
        ORDER BY due_date
        """,
        (today.isoformat(),),
    ).fetchall()

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


def apply_review(conn, card_id, grade, today):
    """Grade a review: reschedule the card and record the review, atomically.

    Loads the card's current SRS state, runs it through the pure
    scheduler, then writes the new state to `cards` and appends a
    `reviews` row in a single transaction. Returns the new due date
    as an ISO string.
    """
    cur = conn.execute(
        "SELECT ease_factor, interval, repetitions FROM cards WHERE card_id = ?",
        (card_id,),
    )
    card = cur.fetchone()
    if card is None:
        raise ValueError(f"Card with ID {card_id} not found.")

    sched = srs.schedule(
        card["ease_factor"], card["interval"], card["repetitions"], grade, today
    )
    new_due_date = sched.due_date.isoformat()

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
            INSERT INTO reviews (card_id, grade, interval_after, ease_after)
            VALUES (?, ?, ?, ?)
            """,
            (card_id, grade, sched.interval, sched.ease_factor),
        )

    return new_due_date