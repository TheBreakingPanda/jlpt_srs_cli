import sqlite3

import pytest
from typer.testing import CliRunner

from jlpt import cli
from jlpt.db import create_schema

runner = CliRunner()


def _make_db(cards):
    """Build an in-memory DB seeded with `cards` (dicts of column → value)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    for c in cards:
        conn.execute(
            "INSERT INTO cards (card_id, source, front, back, reading, due_date) "
            "VALUES (?, 'word_bank', ?, ?, ?, ?)",
            (c["card_id"], c["front"], c["back"], c["reading"], c["due_date"]),
        )
    conn.commit()
    return conn


@pytest.fixture
def seed(monkeypatch):
    """Seed a deck and point `jlpt review` at it by patching cli.init_db."""
    def _seed(cards):
        conn = _make_db(cards)
        monkeypatch.setattr(cli, "init_db", lambda *a, **k: conn)
        return conn
    return _seed


def _card(
    card_id: str = "T1",
    front: str = "本",
    back: str = "book",
    reading: str = "ほん",
    due_date: str | None = "2000-01-01",
) -> dict[str, str | None]:
    return {"card_id": card_id, "front": front, "back": back,
            "reading": reading, "due_date": due_date}


def test_kanji_first_try_pass_grades_5(seed):
    seed([_card()])
    result = runner.invoke(cli.app, ["review"], input="ほん\nbook\n")
    assert result.exit_code == 0
    assert "Grade: 5" in result.output
    assert "Reviewed 1 card(s)." in result.output


def test_kanji_stumble_grades_3(seed):
    # reading wrong once then right; meaning right → one retry used
    seed([_card()])
    result = runner.invoke(cli.app, ["review"], input="wrong\nほん\nbook\n")
    assert result.exit_code == 0
    assert "Grade: 3" in result.output


def test_kanji_miss_grades_1(seed):
    # reading fails both attempts → loop short-circuits, card is a fail
    seed([_card()])
    result = runner.invoke(cli.app, ["review"], input="wrong\nnope\n")
    assert result.exit_code == 0
    assert "Grade: 1" in result.output
    assert "The answer was: ほん" in result.output


def test_kana_first_try_pass_grades_5(seed):
    # --kana shows the reading and asks the meaning only
    seed([_card()])
    result = runner.invoke(cli.app, ["review", "--kana"], input="book\n")
    assert result.exit_code == 0
    assert "Grade: 5" in result.output


def test_kana_stumble_grades_3(seed):
    seed([_card()])
    result = runner.invoke(cli.app, ["review", "--kana"], input="wrong\nbook\n")
    assert result.exit_code == 0
    assert "Grade: 3" in result.output


def test_no_cards_due(seed):
    seed([_card(due_date="2100-01-01")])  # due in the far future
    result = runner.invoke(cli.app, ["review"])
    assert result.exit_code == 0
    assert "Nothing's due today." in result.output


def test_new_cards_limit_caps_the_session(seed):
    seed([
        _card("T1", "本", "book", "ほん", None),
        _card("T2", "人", "person", "ひと", None),
    ])
    result = runner.invoke(cli.app, ["review", "--new", "1"], input="ほん\nbook\n")
    assert result.exit_code == 0
    assert "Reviewed 1 card(s)." in result.output
