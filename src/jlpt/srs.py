"""SM-2 spaced-repetition scheduler - pure, deterministic, no I/O.

Given a card's current scheduling state and a recall grade, compute the next
state. No database, no clock, no printing: `today` is injected so results are
reproducible and unit-testable. Persistence (writing to cards / reviews) is the
Phase 3 review loop's job, not this module's.

v1 SM-2 variant (see JLPT SRS CLI - SM-2 Algorithm doc):
  - a failed review (grade < 3) resets repetitions/interval; the ease factor is
    left unchanged.
  - the interval is rounded with round() (banker's rounding).

Reference: JLPT SRS CLI - SM-2 Algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# --- SM-2 constants --------------------------------------------------------
DEFAULT_EASE = 2.5      # ease factor of a brand-new card
MIN_EASE = 1.3          # floor; intervals must never collapse to nothing
PASS_THRESHOLD = 3      # grade >= this is a pass; below it is a fail
FIRST_INTERVAL = 1      # days, after the 1st successful review
SECOND_INTERVAL = 6     # days, after the 2nd successful review


@dataclass(frozen=True)
class Schedule:
    """The next scheduling state produced by one review. Immutable."""

    ease_factor: float
    interval: int
    repetitions: int
    due_date: date


def schedule(
    ease_factor: float,
    interval: int,
    repetitions: int,
    grade: int,
    today: date,
) -> Schedule:
    """Apply SM-2 to one review and return the next state.

    Args:
        ease_factor: current ease factor (new cards start at DEFAULT_EASE).
        interval: current interval, in days.
        repetitions: consecutive successful reviews so far.
        grade: recall quality, 0..5.
        today: the date of this review (injected, never read from the clock).

    Returns:
        Schedule: the next (ease_factor, interval, repetitions, due_date).

    Raises:
        ValueError: if grade is outside 0..5.
    """
    if not 0 <= grade <= 5:
        raise ValueError(f"grade must be 0..5, got {grade}")

    if grade < PASS_THRESHOLD:
        # Forgotten: relearn from the start; ease factor left unchanged.
        next_repetitions = 0
        next_interval = FIRST_INTERVAL
        next_ease = ease_factor
    else:
        # Passed: grow the interval using the CURRENT ease factor first...
        if repetitions == 0:
            next_interval = FIRST_INTERVAL
        elif repetitions == 1:
            next_interval = SECOND_INTERVAL
        else:
            next_interval = round(interval * ease_factor)
        next_repetitions = repetitions + 1
        # ...then update the ease factor for next time, floored at MIN_EASE.
        next_ease = max(MIN_EASE, _update_ease(ease_factor, grade))

    due_date = today + timedelta(days=next_interval)
    return Schedule(next_ease, next_interval, next_repetitions, due_date)


def _update_ease(ease_factor: float, grade: int) -> float:
    """SM-2 ease update:  EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))."""
    q = grade
    return ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))