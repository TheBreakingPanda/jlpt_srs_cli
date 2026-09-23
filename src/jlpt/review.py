import sqlite3
from datetime import date

from jlpt import srs


def due_cards(conn: sqlite3.Connection, today: date) -> list[sqlite3.Row]:
    """Return cards due for review on `today`, soonest-due first.

    A card is due when it has never been reviewed (due_date IS NULL)
    or its due_date is on/before `today`. Assumes conn.row_factory is
    sqlite3.Row (set once when the connection is opened).
    """
    cur = conn.execute(
        """
        SELECT card_id, front, reading, back,
               ease_factor, interval, repetitions, due_date
        FROM cards
        WHERE due_date IS NULL OR due_date <= ?
        ORDER BY due_date IS NULL, due_date
        """,
        (today.isoformat(),),
    )
    return cur.fetchall()


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