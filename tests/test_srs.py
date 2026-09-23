from datetime import date

import pytest

from jlpt.srs import schedule, DEFAULT_EASE, MIN_EASE

TODAY = date(2026, 1, 1)


# --- successful reviews: interval progression -----------------------------

def test_first_success_interval_is_1(step):
    step("schedule(new card, grade 4) — first success")
    s = schedule(DEFAULT_EASE, interval=0, repetitions=0, grade=4, today=TODAY)
    step(f"got interval={s.interval}, repetitions={s.repetitions}, due={s.due_date}")
    assert s.interval == 1
    assert s.repetitions == 1
    assert s.due_date == date(2026, 1, 2)


def test_second_success_interval_is_6(step):
    step("schedule(reps=1, grade 4) — second success -> interval 6")
    s = schedule(DEFAULT_EASE, interval=1, repetitions=1, grade=4, today=TODAY)
    step(f"got interval={s.interval}, repetitions={s.repetitions}, due={s.due_date}")
    assert s.interval == 6
    assert s.repetitions == 2
    assert s.due_date == date(2026, 1, 7)


def test_third_success_multiplies_by_ease(step):
    step("schedule(interval=6, reps=2, grade 4) — grade 4 keeps EF 2.5; round(6*2.5)=15")
    s = schedule(2.5, interval=6, repetitions=2, grade=4, today=TODAY)
    step(f"got interval={s.interval}, due={s.due_date}")
    assert s.interval == 15
    assert s.repetitions == 3
    assert s.due_date == date(2026, 1, 16)


def test_interval_rounds_half_to_even(step):
    step("15 * 2.5 = 37.5; banker's rounding -> 38")
    s = schedule(2.5, interval=15, repetitions=3, grade=4, today=TODAY)
    step(f"got interval={s.interval}")
    assert s.interval == 38


# --- ease-factor behaviour ------------------------------------------------

def test_grade_4_keeps_ease_flat(step):
    step("grade 4 -> ease delta is exactly 0, stays 2.5")
    s = schedule(2.5, interval=6, repetitions=2, grade=4, today=TODAY)
    step(f"got ease_factor={s.ease_factor}")
    assert s.ease_factor == 2.5


def test_grade_5_raises_ease(step):
    step("grade 5 -> ease rises to ~2.6")
    s = schedule(2.5, interval=6, repetitions=2, grade=5, today=TODAY)
    step(f"got ease_factor={s.ease_factor}")
    assert s.ease_factor == pytest.approx(2.6)


def test_ease_floored_at_min(step):
    step("grade 3 from ease 1.35 would drop below MIN_EASE -> floored")
    s = schedule(1.35, interval=10, repetitions=3, grade=3, today=TODAY)
    step(f"got ease_factor={s.ease_factor}, MIN_EASE={MIN_EASE}")
    assert s.ease_factor == MIN_EASE


# --- failure resets, ease untouched ---------------------------------------

def test_fail_resets_repetitions_and_interval(step):
    step("grade 1 (fail) -> repetitions 0, interval 1, due tomorrow")
    s = schedule(2.5, interval=40, repetitions=5, grade=1, today=TODAY)
    step(f"got repetitions={s.repetitions}, interval={s.interval}, due={s.due_date}")
    assert s.repetitions == 0
    assert s.interval == 1
    assert s.due_date == date(2026, 1, 2)


def test_fail_leaves_ease_unchanged(step):
    step("grade 0 (fail) -> ease unchanged in this SM-2 variant")
    s = schedule(2.3, interval=40, repetitions=5, grade=0, today=TODAY)
    step(f"got ease_factor={s.ease_factor}")
    assert s.ease_factor == 2.3


# --- guard ----------------------------------------------------------------

def test_invalid_grade_raises(step):
    step("grade 6 is out of range 0..5 -> expect ValueError")
    with pytest.raises(ValueError):
        schedule(2.5, interval=1, repetitions=0, grade=6, today=TODAY)
