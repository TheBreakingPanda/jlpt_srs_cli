"""Import/sync Word Bank CSV exports into the cards table.

Pipeline: CSV -> read_rows (dumb reader) -> Card.from_export_row (mapping) ->
import_cards (upsert). The upsert updates content by card_id and never touches
SRS state (ease/interval/repetitions/due) or created_at — a re-import re-syncs
words without resetting scheduling.
"""

from __future__ import annotations
import csv
import sqlite3
from pathlib import Path
from .models import Card


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    """Read the export CSV and return one dict per row, keyed by LOWERCASE names.

    The export standard is capitalised headers `ID,Theme,Kanji,Reading,Romaji,
    English`. Lowercase the keys defensively so downstream code can rely on
    row["id"], row["kanji"], ... even if a file is mis-cased. Return the rows raw
    otherwise — the column -> card-field mapping happens in Card.from_export_row,
    keeping this a dumb reader.
    """
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append({k.lower(): v for k, v in row.items()})
    return rows


def import_cards(conn: sqlite3.Connection, cards: list[Card]) -> tuple[int, int]:
    """Upsert cards by card_id. Return (new, updated).

    Content-only sync: DO UPDATE touches front/back/reading and bumps updated_at.
    ease_factor, interval, repetitions, due_date, created_at and source are left
    out of the SET clause on purpose, so a re-import preserves SRS state and the
    original origin/creation stamp.

    Counting: cursor.rowcount can't distinguish insert from update for an upsert,
    so ask the DB which ids already exist BEFORE writing — afterward every id is
    present and the distinction is gone. Assumes card_ids are unique within one
    file (true for a Word Bank export).
    """
    existing = {r[0] for r in conn.execute("SELECT card_id FROM cards")}
    new = sum(1 for c in cards if c.card_id not in existing)
    updated = len(cards) - new

    params = [(c.card_id, c.source, c.front, c.back, c.reading) for c in cards]
    conn.executemany(
        """
        INSERT INTO cards (card_id, source, front, back, reading)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(card_id) DO UPDATE SET
            front      = excluded.front,
            back       = excluded.back,
            reading    = excluded.reading,
            updated_at = date('now')
        """,
        params,
    )
    conn.commit()
    return new, updated


def import_csv(
    conn: sqlite3.Connection, csv_path: Path, source: str = "word_bank"
) -> tuple[int, int]:
    """Read a CSV export and upsert it. Return (new, updated).

    Thin orchestrator: read -> map to Cards -> import_cards. `source` is stamped
    on newly inserted cards (e.g. "n5_core" for a different export).
    """
    cards = [Card.from_export_row(row, source) for row in read_rows(Path(csv_path))]
    return import_cards(conn, cards)
