import csv
import sqlite3

import pytest
from typer.testing import CliRunner

from jlpt import cli
from jlpt.db import create_schema

runner = CliRunner()


# --- fixtures & helpers ----------------------------------------------------

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
    """One in-memory connection — for a SINGLE invoke that asserts on output."""
    def _seed(cards):
        conn = _make_db(cards)
        monkeypatch.setattr(cli, "init_db", lambda *a, **k: conn)
        return conn
    return _seed


@pytest.fixture
def file_db(tmp_path, monkeypatch):
    """A temp-file DB each command opens fresh — survives close across invokes.

    Use when a test chains commands or reads the DB back. Returns the path.
    """
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    conn.commit()
    conn.close()

    def _open(*args, **kwargs):
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        return c

    monkeypatch.setattr(cli, "init_db", _open)
    return path


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _write_csv(path, rows):
    """rows: list of (id, kanji, reading, english) → a Word Bank export CSV."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Theme", "Kanji", "Reading", "Romaji", "English"])
        for cid, kanji, reading, english in rows:
            w.writerow([cid, "", kanji, reading, "", english])


def _card(
    card_id: str = "T1",
    front: str = "本",
    back: str = "book",
    reading: str = "ほん",
    due_date: str | None = "2000-01-01",
) -> dict[str, str | None]:
    return {"card_id": card_id, "front": front, "back": back,
            "reading": reading, "due_date": due_date}


# --- import ----------------------------------------------------------------

def test_import_inserts_all_and_reports_counts(file_db, tmp_path):
    csv_path = tmp_path / "wb.csv"
    _write_csv(csv_path, [("EO001", "本", "ほん", "book"),
                          ("EO002", "人", "ひと", "person")])
    result = runner.invoke(cli.app, ["import", str(csv_path)])
    assert result.exit_code == 0
    assert "Imported 2 cards (2 new, 0 updated)." in result.output
    conn = _connect(file_db)
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 2
    conn.close()


def test_import_unchanged_reimport_is_noop(file_db, tmp_path):
    csv_path = tmp_path / "wb.csv"
    _write_csv(csv_path, [("EO001", "本", "ほん", "book")])
    runner.invoke(cli.app, ["import", str(csv_path)])
    result = runner.invoke(cli.app, ["import", str(csv_path)])
    assert result.exit_code == 0
    assert "(0 new, 0 updated)" in result.output


def test_import_updates_changed_content(file_db, tmp_path):
    csv_path = tmp_path / "wb.csv"
    _write_csv(csv_path, [("EO001", "本", "ほん", "book")])
    runner.invoke(cli.app, ["import", str(csv_path)])
    _write_csv(csv_path, [("EO001", "本", "ほん", "a book")])  # meaning changed
    result = runner.invoke(cli.app, ["import", str(csv_path)])
    assert "(0 new, 1 updated)" in result.output
    conn = _connect(file_db)
    assert conn.execute("SELECT back FROM cards WHERE card_id='EO001'").fetchone()[0] == "a book"
    conn.close()


def test_import_source_option_is_stamped(file_db, tmp_path):
    csv_path = tmp_path / "wb.csv"
    _write_csv(csv_path, [("NC001", "人", "ひと", "person")])
    runner.invoke(cli.app, ["import", str(csv_path), "--source", "n5_core"])
    conn = _connect(file_db)
    assert conn.execute("SELECT source FROM cards WHERE card_id='NC001'").fetchone()[0] == "n5_core"
    conn.close()


# --- review quiz loop ------------------------------------------------------

def test_kanji_first_try_pass_grades_5(seed):
    seed([_card()])
    result = runner.invoke(cli.app, ["review"], input="ほん\nbook\n")
    assert result.exit_code == 0
    assert "Grade: 5" in result.output
    assert "Reviewed 1 card(s)." in result.output


def test_kanji_stumble_grades_3(seed):
    seed([_card()])
    result = runner.invoke(cli.app, ["review"], input="wrong\nほん\nbook\n")
    assert result.exit_code == 0
    assert "Grade: 3" in result.output


def test_kanji_miss_grades_1(seed):
    seed([_card()])
    result = runner.invoke(cli.app, ["review"], input="wrong\nnope\n")
    assert result.exit_code == 0
    assert "Grade: 1" in result.output
    assert "The answer was: ほん" in result.output


def test_kana_first_try_pass_grades_5(seed):
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
    seed([_card(due_date="2100-01-01")])
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


# --- add -------------------------------------------------------------------

def test_add_first_card_is_usr001(file_db):
    result = runner.invoke(cli.app, ["add"], input="本\nほん\nbook\n")
    assert result.exit_code == 0
    assert "Added USR001." in result.output
    conn = _connect(file_db)
    card = conn.execute("SELECT * FROM cards WHERE card_id='USR001'").fetchone()
    conn.close()
    assert card["front"] == "本"
    assert card["reading"] == "ほん"
    assert card["back"] == "book"
    assert card["source"] == "user"
    assert card["due_date"] is None          # enters the new queue


def test_add_increments_to_usr002(file_db):
    runner.invoke(cli.app, ["add"], input="本\nほん\nbook\n")
    result = runner.invoke(cli.app, ["add"], input="人\nひと\nperson\n")
    assert result.exit_code == 0
    assert "Added USR002." in result.output


def test_add_id_uses_max_not_count(file_db):
    # seed a gap: only USR003 exists → next must be USR004, not USR001/USR002
    conn = _connect(file_db)
    conn.execute(
        "INSERT INTO cards (card_id, source, front, back, reading) "
        "VALUES ('USR003', 'user', '水', 'water', 'みず')"
    )
    conn.commit()
    conn.close()
    result = runner.invoke(cli.app, ["add"], input="火\nひ\nfire\n")
    assert result.exit_code == 0
    assert "Added USR004." in result.output


def test_added_card_can_be_reviewed(file_db):
    runner.invoke(cli.app, ["add"], input="本\nほん\nbook\n")
    result = runner.invoke(cli.app, ["review"], input="ほん\nbook\n")
    assert result.exit_code == 0
    assert "Reviewed 1 card(s)." in result.output


def test_added_card_can_be_reviewed_kana(file_db):
    runner.invoke(cli.app, ["add"], input="本\nほん\nbook\n")
    result = runner.invoke(cli.app, ["review", "--kana"], input="book\n")
    assert result.exit_code == 0
    assert "Reviewed 1 card(s)." in result.output


def test_added_card_kana_stumble_grades_3(file_db):
    runner.invoke(cli.app, ["add"], input="本\nほん\nbook\n")
    result = runner.invoke(cli.app, ["review", "--kana"], input="wrong\nbook\n")
    assert result.exit_code == 0
    assert "Grade: 3" in result.output


# --- remove ----------------------------------------------------------------

def test_remove_deletes_a_card(file_db):
    runner.invoke(cli.app, ["add"], input="本\nほん\nbook\n")
    result = runner.invoke(cli.app, ["remove", "USR001"], input="y\n")
    assert result.exit_code == 0
    assert "Delete USR001 and its review history?" in result.output
    assert "Removed USR001." in result.output
    conn = _connect(file_db)
    card = conn.execute("SELECT * FROM cards WHERE card_id='USR001'").fetchone()
    conn.close()
    assert card is None


def test_remove_reviewed_card_cascades(file_db):
    runner.invoke(cli.app, ["add"], input="本\nほん\nbook\n")
    runner.invoke(cli.app, ["review"], input="ほん\nbook\n")
    result = runner.invoke(cli.app, ["remove", "USR001"], input="y\n")
    assert result.exit_code == 0
    conn = _connect(file_db)
    card = conn.execute("SELECT * FROM cards WHERE card_id='USR001'").fetchone()
    review = conn.execute("SELECT * FROM reviews WHERE card_id='USR001'").fetchone()
    conn.close()
    assert card is None
    assert review is None


def test_remove_unknownid_reports_notfound(file_db):
    result = runner.invoke(cli.app, ["remove", "USR999"])
    assert result.exit_code == 1
    assert "No card with ID USR999." in result.output


def test_remove_abort_keeps_card(file_db):
    runner.invoke(cli.app, ["add"], input="本\nほん\nbook\n")
    result = runner.invoke(cli.app, ["remove", "USR001"], input="n\n")
    assert result.exit_code == 1
    conn = _connect(file_db)
    card = conn.execute("SELECT * FROM cards WHERE card_id='USR001'").fetchone()
    conn.close()
    assert card is not None