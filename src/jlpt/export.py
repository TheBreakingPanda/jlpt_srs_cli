"""Back up the deck to JSON or CSV - and read a backup back.

Export is a backup, not a sync: the vault's Word Bank stays the canonical source
of vocabulary, and `jlpt import` remains the only way content enters the deck.
The readers exist so a backup can be verified (and so the tests can prove the
round-trip), not to restore over a live deck.

Format is chosen by the file suffix:
- .json - lossless: every card column plus the full review history, under a
  small header (format, version, exported_at) so a file identifies itself.
- .csv  - cards only, one row each, for opening in a spreadsheet. Review history
  doesn't fit a flat table, so it's JSON-only. CSV also has no NULL: empty
  due_date / SRS cells read back as None, other empty cells as "".
"""

from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

FORMAT_NAME = "jlpt-export"
FORMAT_VERSION = 1

# Explicit, ordered columns: the file layout is a contract, so it must not
# shift if the schema ever grows a column (SELECT * would).
CARD_COLUMNS = (
    "card_id", "source", "front", "back", "reading",
    "ease_factor", "interval", "repetitions", "due_date",
    "created_at", "updated_at",
)
REVIEW_COLUMNS = (
    "id", "card_id", "reviewed_at", "grade", "interval_after", "ease_after",
    "ease_before", "interval_before", "repetitions_before", "due_before",
)

# Every CSV cell is text; these restore the stored types on the way back in.
_CSV_TYPES = {"ease_factor": float, "interval": int, "repetitions": int}
_CSV_NULLABLE = {"due_date", "ease_factor", "interval", "repetitions"}

_SUFFIX_FORMATS = {".json": "json", ".csv": "csv"}


class ExportError(Exception):
    """A backup file can't be written or read (bad suffix, not an export)."""


@dataclass(frozen=True)
class Backup:
    """The deck as plain data. `reviews` is None for CSV, which has no history."""

    cards: list[dict]
    reviews: list[dict] | None


def format_for(path: Path) -> str:
    """'json' or 'csv' from the file suffix; ExportError for anything else."""
    try:
        return _SUFFIX_FORMATS[path.suffix.lower()]
    except KeyError:
        shown = path.suffix or "(no suffix)"
        raise ExportError(
            f"Unsupported export format {shown} - use .json or .csv."
        ) from None


# --- read the deck -----------------------------------------------------------

def fetch_cards(conn: sqlite3.Connection) -> list[dict]:
    """Every card, all columns, ordered by card_id."""
    columns = ", ".join(CARD_COLUMNS)
    rows = conn.execute(f"SELECT {columns} FROM cards ORDER BY card_id")
    return [dict(row) for row in rows]


def fetch_reviews(conn: sqlite3.Connection) -> list[dict]:
    """Every review, all columns, in the order they happened."""
    columns = ", ".join(REVIEW_COLUMNS)
    rows = conn.execute(f"SELECT {columns} FROM reviews ORDER BY id")
    return [dict(row) for row in rows]


# --- write -------------------------------------------------------------------

def write_json(
    path: Path, cards: list[dict], reviews: list[dict], exported_at: datetime
) -> None:
    payload = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "exported_at": exported_at.isoformat(timespec="seconds"),
        "cards": cards,
        "reviews": reviews,
    }
    with open(path, "w", encoding="utf-8") as f:
        # ensure_ascii=False keeps 本 as 本 rather than \u672c - readable backups.
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_csv(path: Path, cards: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CARD_COLUMNS)
        writer.writeheader()
        writer.writerows(cards)  # DictWriter writes None as an empty cell


def export_deck(conn: sqlite3.Connection, path: Path, now: datetime) -> Backup:
    """Write the deck to `path` (format from its suffix) and return what was written.

    Writes to a temp file first and renames it into place, so a failed export
    never leaves a half-written file where a good backup used to be.
    """
    fmt = format_for(path)
    cards = fetch_cards(conn)
    reviews = fetch_reviews(conn) if fmt == "json" else None

    tmp = path.with_name(path.name + ".tmp")
    try:
        if fmt == "json":
            write_json(tmp, cards, reviews, now)
        else:
            write_csv(tmp, cards)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)  # only still there if the write failed
    return Backup(cards, reviews)


# --- read a backup back ------------------------------------------------------

def read_json(path: Path) -> Backup:
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        raise ExportError(f"{path} isn't valid JSON: {e}") from None
    if not isinstance(payload, dict) or payload.get("format") != FORMAT_NAME:
        raise ExportError(f"{path} isn't a jlpt export.")
    if payload.get("version") != FORMAT_VERSION:
        raise ExportError(
            f"{path} is export version {payload.get('version')!r}; "
            f"this jlpt reads version {FORMAT_VERSION}."
        )
    return Backup(payload["cards"], payload["reviews"])


def _card_from_csv(row: dict[str, str]) -> dict:
    """One CSV row back into the stored types."""
    card: dict = {}
    for column in CARD_COLUMNS:
        value = row[column]
        if value == "" and column in _CSV_NULLABLE:
            card[column] = None
        elif column in _CSV_TYPES:
            card[column] = _CSV_TYPES[column](value)
        else:
            card[column] = value
    return card


def read_csv(path: Path) -> Backup:
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != CARD_COLUMNS:
            raise ExportError(f"{path} isn't a jlpt CSV export (unexpected columns).")
        return Backup([_card_from_csv(row) for row in reader], None)


def read_export(path: Path) -> Backup:
    """Load a backup written by `export_deck` (format from its suffix)."""
    return read_json(path) if format_for(path) == "json" else read_csv(path)
