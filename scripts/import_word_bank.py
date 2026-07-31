"""Phase 0 throwaway: import the real Word Bank export into SQLite.

    data/word_bank.csv  ->  Python  ->  data/jlpt.db  ->  "Imported N cards."

A bare-bones dry run of `jlpt import` (Phase 1). It reads the CSV that the Word
Bank's "Export to CSV" button produces, creates data/jlpt.db, builds a minimal
`cards` table, inserts every row, and reports the count read back from the DB.

NOT seed data: the database is only ever populated from a real export — no
fabricated cards. This script is disposable: delete it once `jlpt import` lands.

Run:
    python scripts/import_word_bank.py             # uses data/word_bank.csv
    python scripts/import_word_bank.py some.csv    # or point at another export
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_CSV = DATA_DIR / "word_bank.csv"
DB_PATH = DATA_DIR / "jlpt.db"

# Every row in a Word Bank export came from the Word Bank, so `source` is a
# constant here. (A real importer will set it per export file.)
SOURCE = "word_bank"

# Minimal Phase 0 table: content spine only, no SRS columns yet. Shaped like the
# real `cards` table so what you learn here transfers to Phase 1.
SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    card_id  TEXT PRIMARY KEY,
    source   TEXT NOT NULL,
    front    TEXT NOT NULL,
    back     TEXT,
    reading  TEXT
);
"""


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    """Read the export CSV and return one dict per row, keyed by LOWERCASE names.

    The export standard is capitalised headers `ID,Theme,Kanji,Reading,Romaji,
    English`. Lowercase the keys defensively so downstream code can rely on
    row["id"], row["kanji"], ... even if a file is mis-cased. Return the rows raw
    otherwise — the column -> card-field mapping happens in insert_cards, keeping
    this a dumb reader.
    """

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append({k.lower(): v for k, v in row.items()})
    return rows


def connect(db_path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the SQLite database and return the connection.

    Make sure data/ exists first, or sqlite3.connect fails on a missing folder.
    """

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def create_schema(conn: sqlite3.Connection) -> None:
    """Create the `cards` table if it doesn't already exist."""

    conn.execute(SCHEMA)
    conn.commit()


def insert_cards(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> int:
    """Insert the rows into `cards`, return how many were written.

    The column -> card-field mapping lives here (keys are lowercase after
    read_rows):
        id      -> card_id
        kanji   -> front
        english -> back
        reading -> reading
        source  -> the SOURCE constant (not a CSV column)
    theme and romaji are intentionally dropped in v1.

    Use a parameterised query (never f-strings) so Japanese text and any commas
    in a field are handled safely. Re-running shouldn't crash on the primary
    key, so use INSERT OR REPLACE (fine for a throwaway).
    """

    tuples = [
        (r.get("id"), SOURCE, r.get("kanji"), r.get("english"), r.get("reading"))
        for r in rows
    ]

    sql = (
        "INSERT OR REPLACE INTO cards"
        "(card_id, source, front, back, reading) VALUES (?, ?, ?, ?, ?)"
    )
    conn.executemany(sql, tuples)
    conn.commit()
    return len(tuples)


def report(conn: sqlite3.Connection) -> None:
    """Count the rows back OUT of the database and print the summary.

    Counting via SELECT (not len(rows)) is the point of Phase 0 — it proves the
    data really reached SQLite. ~605 rows, so print the count, not every card.
    """

    cur = conn.execute("SELECT COUNT(*) FROM cards")
    n = cur.fetchone()[0]
    print(f"Imported {n} cards.")
    for row in conn.execute(
        "SELECT card_id, front, reading, back FROM cards ORDER BY card_id LIMIT 5"
    ):
        print("  ", *row)


def main(argv: list[str]) -> None:
    """Wire the pipeline: read -> connect -> create -> insert -> report.

    argv[1], if given, is the CSV path; otherwise use DEFAULT_CSV.
    """

    csv_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CSV
    rows = read_rows(csv_path)
    conn = connect(DB_PATH)
    try:
        create_schema(conn)
        insert_cards(conn, rows)
        report(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main(sys.argv)
