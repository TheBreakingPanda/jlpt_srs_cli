import pytest

from jlpt.cards import CardNotFoundError, update_card


def _insert(conn, card_id="C1", front="本", back="book", reading="ほん"):
    """Seed one card with non-default SRS state and an old updated_at."""
    conn.execute(
        "INSERT INTO cards (card_id, source, front, back, reading, ease_factor, "
        "interval, repetitions, due_date, updated_at) "
        "VALUES (?, 'word_bank', ?, ?, ?, 2.36, 6, 2, '2026-10-01', '2000-01-01')",
        (card_id, front, back, reading),
    )
    conn.commit()


def _row(conn, card_id="C1"):
    return conn.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,)).fetchone()


# --- writes ------------------------------------------------------------------

def test_updates_one_field(conn):
    _insert(conn)
    changed = update_card(conn, "C1", {"back": "a book"})
    assert changed == ["back"]
    assert _row(conn)["back"] == "a book"
    assert _row(conn)["front"] == "本"            # untouched


def test_updates_several_fields_sorted(conn):
    _insert(conn)
    changed = update_card(conn, "C1", {"reading": "もと", "front": "元"})
    assert changed == ["front", "reading"]
    row = _row(conn)
    assert (row["front"], row["reading"]) == ("元", "もと")


def test_keeps_srs_state(conn):
    _insert(conn)
    update_card(conn, "C1", {"back": "a book"})
    row = _row(conn)
    assert (row["ease_factor"], row["interval"], row["repetitions"], row["due_date"]) \
        == (2.36, 6, 2, "2026-10-01")


def test_bumps_updated_at_on_change(conn):
    _insert(conn)
    update_card(conn, "C1", {"back": "a book"})
    assert _row(conn)["updated_at"] != "2000-01-01"


def test_strips_whitespace(conn):
    _insert(conn)
    update_card(conn, "C1", {"back": "  a book  "})
    assert _row(conn)["back"] == "a book"


def test_markup_like_value_is_stored_verbatim(conn):
    _insert(conn)
    update_card(conn, "C1", {"back": "to go [home]"})
    assert _row(conn)["back"] == "to go [home]"


# --- no-ops ------------------------------------------------------------------

def test_identical_value_is_a_noop(conn):
    _insert(conn)
    assert update_card(conn, "C1", {"back": "book"}) == []
    assert _row(conn)["updated_at"] == "2000-01-01"   # nothing written


def test_only_differing_fields_are_reported(conn):
    _insert(conn)
    assert update_card(conn, "C1", {"back": "book", "reading": "もと"}) == ["reading"]


# --- rejections --------------------------------------------------------------

def test_unknown_card_raises(conn):
    with pytest.raises(CardNotFoundError):
        update_card(conn, "NOPE", {"back": "x"})


def test_empty_changes_raises(conn):
    _insert(conn)
    with pytest.raises(ValueError, match="Nothing to edit"):
        update_card(conn, "C1", {})


@pytest.mark.parametrize("column", ["ease_factor", "card_id", "source", "due_date"])
def test_non_content_column_is_rejected(conn, column):
    _insert(conn)
    with pytest.raises(ValueError, match="Not editable"):
        update_card(conn, "C1", {column: "1"})
    assert _row(conn)["ease_factor"] == 2.36


def test_injection_shaped_column_name_is_rejected(conn):
    _insert(conn)
    with pytest.raises(ValueError, match="Not editable"):
        update_card(conn, "C1", {"back = 'x', ease_factor": "9"})
    assert _row(conn)["ease_factor"] == 2.36


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_value_is_rejected(conn, value):
    _insert(conn)
    with pytest.raises(ValueError, match="meaning can't be blank"):
        update_card(conn, "C1", {"back": value})
    assert _row(conn)["back"] == "book"


def test_rejection_writes_nothing_even_alongside_valid_field(conn):
    _insert(conn)
    with pytest.raises(ValueError):
        update_card(conn, "C1", {"reading": "もと", "back": ""})
    assert _row(conn)["reading"] == "ほん"         # validation precedes any write

