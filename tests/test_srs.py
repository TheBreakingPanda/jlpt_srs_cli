from datetime import date

import pytest

from jlpt.srs import schedule, DEFAULT_EASE, MIN_EASE

TODAY = date(2026, 1, 1)


# --- successful reviews: interval progression -----------------------------

def test_first_success_interval_is_1():
    s = schedule(DEFAULT_EASE, interval=0, repetitions=0, grade=4, today=TODAY)
    assert s.interval == 1
    assert s.repetitions == 1
    assert s.due_date == date(2026, 1, 2)


def test_second_success_interval_is_6():
    s = schedule(DEFAULT_EASE, interval=1, repetitions=1, grade=4, today=TODAY)
    assert s.interval == 6
    assert s.repetitions == 2
    assert s.due_date == date(2026, 1, 7)


def test_third_success_multiplies_by_ease():
    # grade 4 keeps EF at 2.5; interval 6 -> round(6 * 2.5) = 15
    s = schedule(2.5, interval=6, repetitions=2, grade=4, today=TODAY)
    assert s.interval == 15
    assert s.repetitions == 3
    assert s.due_date == date(2026, 1, 16)


def test_interval_rounds_half_to_even():
    # 15 * 2.5 = 37.5 ; Python round() is banker's rounding -> 38
    s = schedule(2.5, interval=15, repetitions=3, grade=4, today=TODAY)
    assert s.interval == 38


# --- ease-factor behaviour ------------------------------------------------

def test_grade_4_keeps_ease_flat():
    s = schedule(2.5, interval=6, repetitions=2, grade=4, today=TODAY)
    assert s.ease_factor == 2.5


def test_grade_5_raises_ease():
    s = schedule(2.5, interval=6, repetitions=2, grade=5, today=TODAY)
    assert s.ease_factor == pytest.approx(2.6)


def test_ease_floored_at_min():
    # grade 3 update: 0.1 - 2*(0.08 + 2*0.02) = -0.14 ; 1.35 - 0.14 = 1.21 -> floored
    s = schedule(1.35, interval=10, repetitions=3, grade=3, today=TODAY)
    assert s.ease_factor == MIN_EASE


# --- failure resets, ease untouched ---------------------------------------

def test_fail_resets_repetitions_and_interval():
    s = schedule(2.5, interval=40, repetitions=5, grade=1, today=TODAY)
    assert s.repetitions == 0
    assert s.interval == 1
    assert s.due_date == date(2026, 1, 2)


def test_fail_leaves_ease_unchanged():
    s = schedule(2.3, interval=40, repetitions=5, grade=0, today=TODAY)
    assert s.ease_factor == 2.3


# --- guard ----------------------------------------------------------------

def test_invalid_grade_raises():
    with pytest.raises(ValueError):
        schedule(2.5, interval=1, repetitions=0, grade=6, today=TODAY)