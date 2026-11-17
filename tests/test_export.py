import json
from datetime import datetime
from pathlib import Path

import pytest

from jlpt import export as exporter
from jlpt.export import ExportError, export_deck, read_export

NOW = datetime(2026, 11, 17, 19, 30, 0)


@pytest.fixture
def deck(conn):
    """Two cards (one reviewed, one brand-new) and one review row."""
    conn.execute(
        "INSERT INTO cards (card_id, source, front, back, reading, ease_factor, "
        "interval, repetitions, due_date) VALUES "
        "('EO001', 'word_bank', '本', 'book', 'ほん', 2.36, 6, 2, '2026-11-20')"
    )
    conn.execute(
        "INSERT INTO cards (card_id, source, front, back, reading) VALUES "
        "('USR001', 'user', '人', 'to go [home]', 'ひと')"     # due_date NULL
    )
    conn.execute(
        "INSERT INTO reviews (card_id, reviewed_at, grade, interval_after, "
        "ease_after, ease_before, interval_before, repetitions_before, due_before) "
        "VALUES ('EO001', '2026-11-14 08:00:00', 4, 6, 2.36, 2.5, 1, 1, '2026-11-14')"
    )
    conn.commit()
    return conn


# --- round-trips -------------------------------------------------------------

def test_json_round_trips_cards_and_reviews(deck, tmp_path):
    path = tmp_path / "backup.json"
    written = export_deck(deck, path, NOW)
    assert read_export(path) == written
    assert len(written.cards) == 2
    assert len(written.reviews) == 1


def test_csv_round_trips_cards_with_types(deck, tmp_path):
    path = tmp_path / "backup.csv"
    written = export_deck(deck, path, NOW)
    loaded = read_export(path)
    assert loaded == written
    assert loaded.reviews is None                        # CSV carries no history
    eo = loaded.cards[0]
    assert (eo["ease_factor"], eo["interval"], eo["repetitions"]) == (2.36, 6, 2)


def test_csv_null_due_date_reads_back_as_none(deck, tmp_path):
    path = tmp_path / "backup.csv"
    export_deck(deck, path, NOW)
    usr = read_export(path).cards[1]
    assert usr["card_id"] == "USR001"
    assert usr["due_date"] is None


def test_round_trip_matches_the_database(deck, tmp_path):
    path = tmp_path / "backup.json"
    export_deck(deck, path, NOW)
    in_db = [dict(r) for r in deck.execute("SELECT * FROM cards ORDER BY card_id")]
    assert read_export(path).cards == in_db


def test_empty_deck_exports_and_reads_back(conn, tmp_path):
    path = tmp_path / "empty.json"
    export_deck(conn, path, NOW)
    assert read_export(path) == exporter.Backup([], [])


# --- file contents -----------------------------------------------------------

def test_json_has_header_and_readable_japanese(deck, tmp_path):
    path = tmp_path / "backup.json"
    export_deck(deck, path, NOW)
    text = path.read_text(encoding="utf-8")
    assert "本" in text                                   # not \u672c
    payload = json.loads(text)
    assert payload["format"] == "jlpt-export"
    assert payload["version"] == 1
    assert payload["exported_at"] == "2026-11-17T19:30:00"


def test_csv_header_is_the_column_contract(deck, tmp_path):
    path = tmp_path / "backup.csv"
    export_deck(deck, path, NOW)
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert header == ",".join(exporter.CARD_COLUMNS)


def test_suffix_is_case_insensitive(deck, tmp_path):
    path = tmp_path / "BACKUP.JSON"
    export_deck(deck, path, NOW)
    assert read_export(path).reviews is not None


def test_no_temp_file_left_behind(deck, tmp_path):
    export_deck(deck, tmp_path / "backup.json", NOW)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["backup.json"]


# --- rejections --------------------------------------------------------------

@pytest.mark.parametrize("name", ["backup.txt", "backup", "backup.json.bak"])
def test_unsupported_suffix_raises(name):
    with pytest.raises(ExportError, match="Unsupported export format"):
        exporter.format_for(Path(name))


def test_reading_foreign_json_raises(tmp_path):
    path = tmp_path / "other.json"
    path.write_text('{"cards": []}', encoding="utf-8")
    with pytest.raises(ExportError, match="isn't a jlpt export"):
        read_export(path)


def test_reading_future_version_raises(tmp_path):
    path = tmp_path / "future.json"
    path.write_text(
        '{"format": "jlpt-export", "version": 99, "cards": [], "reviews": []}',
        encoding="utf-8",
    )
    with pytest.raises(ExportError, match="version 99"):
        read_export(path)


def test_reading_broken_json_raises(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ExportError, match="isn't valid JSON"):
        read_export(path)


def test_reading_foreign_csv_raises(tmp_path):
    path = tmp_path / "word_bank.csv"
    path.write_text("ID,Theme,Kanji,Reading,Romaji,English\n", encoding="utf-8")
    with pytest.raises(ExportError, match="unexpected columns"):
        read_export(path)

