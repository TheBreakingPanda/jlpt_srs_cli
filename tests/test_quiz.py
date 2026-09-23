import logging

import pytest

from jlpt.quiz import check_meaning, check_reading, grade_from_attempts

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    ("attempts", "correct", "expected"),
    [
        (1, True, 5),
        (2, True, 3),
        (2, False, 1),
        (1, False, 1),
    ],
)
def test_grade_from_attempts(attempts, correct, expected):
    actual = grade_from_attempts(attempts, correct)
    logger.info("grade_from_attempts(%r, %r) = %r; expected %r", attempts, correct, actual, expected)
    assert actual == expected


@pytest.mark.parametrize("attempts", [0, -1])
def test_grade_from_attempts_returns_minimum_for_incorrect_answers(attempts):
    actual = grade_from_attempts(attempts, False)
    logger.info("grade_from_attempts(%r, False) = %r; expected 1", attempts, actual)
    assert actual == 1


@pytest.mark.parametrize("typed", ["がくせい", "  がくせい  "])
def test_check_reading_accepts_exact_and_surrounding_whitespace(typed):
    actual = check_reading("がくせい", typed)
    logger.info("check_reading(%r, %r) = %r; expected True", "がくせい", typed, actual)
    assert actual is True


def test_check_reading_rejects_a_mismatch():
    actual = check_reading("がくせい", "せんせい")
    logger.info("check_reading(%r, %r) = %r; expected False", "がくせい", "せんせい", actual)
    assert actual is False


@pytest.mark.parametrize("typed", ["  せんせい", "ガクセイ", "学生"])
def test_check_reading_rejects_invalid_answers(typed):
    actual = check_reading("がくせい", typed)
    logger.info("check_reading(%r, %r) = %r; expected False", "がくせい", typed, actual)
    assert actual is False


@pytest.mark.parametrize("typed", ["book", " BOOK ", "the book", "book."])
def test_check_meaning_accepts_expected_answers(typed):
    actual = check_meaning("book", typed)
    logger.info("check_meaning(%r, %r) = %r; expected True", "book", typed, actual)
    assert actual is True


@pytest.mark.parametrize("typed", ["book", "volume"])
def test_check_meaning_accepts_semicolon_separated_answers(typed):
    actual = check_meaning("book; volume", typed)
    logger.info("check_meaning(%r, %r) = %r; expected True", "book; volume", typed, actual)
    assert actual is True


def test_check_meaning_rejects_a_wrong_answer():
    actual = check_meaning("book", "pen")
    logger.info("check_meaning(%r, %r) = %r; expected False", "book", "pen", actual)
    assert actual is False


@pytest.mark.parametrize("typed", ["", "   ", "Bookish", "not a book"])
def test_check_meaning_rejects_invalid_answers(typed):
    actual = check_meaning("book", typed)
    logger.info("check_meaning(%r, %r) = %r; expected False", "book", typed, actual)
    assert actual is False
