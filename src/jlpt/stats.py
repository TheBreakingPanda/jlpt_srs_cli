"""Deck statistics for `jlpt stats`.

due today, reviewed today, streak (consecutive days with >=1 review),
accuracy (all-time passes / total reviews, pass = grade >= 3), and totals.
All computed as of an injected `today`, so they're unit-testable.
"""

from datetime import timedelta


def gather_stats(conn, today):
    """Return the deck's stats as of `today` (injected, for testability)."""
    iso = today.isoformat()

    total_cards = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]

    total_reviews, total_passes = conn.execute(
        "SELECT COUNT(*), SUM(CASE WHEN grade >= 3 THEN 1 ELSE 0 END) FROM reviews"
    ).fetchone()
    total_passes = total_passes or 0   # SUM over no rows is NULL

    reviews_today = conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE date(reviewed_at) = ?", (iso,)
    ).fetchone()[0]

    # Due = cards whose scheduled due_date has arrived (on cards, not reviews).
    due_today = conn.execute(
        "SELECT COUNT(*) FROM cards WHERE due_date IS NOT NULL AND due_date <= ?",
        (iso,),
    ).fetchone()[0]

    accuracy = (total_passes / total_reviews * 100) if total_reviews else 0.0

    return {
        "total_cards": total_cards,
        "total_reviews": total_reviews,
        "total_passes": total_passes,
        "reviews_today": reviews_today,
        "due_today": due_today,
        "accuracy": accuracy,
        "streak": _current_streak(conn, today),
    }


def _current_streak(conn, today):
    """Consecutive days with >=1 review, ending today or yesterday.

    Not having reviewed *yet today* doesn't break the streak - it stays alive
    through the current day as long as yesterday had a review. The streak only
    breaks once a full day passes with no reviews.
    """
    days = {
        row[0] for row in conn.execute("SELECT DISTINCT date(reviewed_at) FROM reviews")
    }
    # Anchor at today if reviewed today, else yesterday (the day-off grace).
    day = today if today.isoformat() in days else today - timedelta(days=1)
    streak = 0
    while day.isoformat() in days:
        streak += 1
        day -= timedelta(days=1)
    return streak