import sqlite3
from datetime import date

import pytest

SCHEMA = """
CREATE TABLE cards (
  card_id     TEXT PRIMARY KEY,
  source      TEXT NOT NULL,
  front       TEXT NOT NULL,
  back        TEXT,
  reading     TEXT,
  ease_factor REAL    DEFAULT 2.5,
  interval    INTEGER DEFAULT 0,
  repetitions INTEGER DEFAULT 0,
  due_date    TEXT,
  created_at  TEXT DEFAULT (date('now')),
  updated_at  TEXT DEFAULT (date('now'))
);
CREATE TABLE reviews (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id        TEXT NOT NULL REFERENCES cards(card_id),
  reviewed_at    TEXT DEFAULT (datetime('now')),
  grade          INTEGER NOT NULL,
  interval_after INTEGER,
  ease_after     REAL
);
"""


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    yield connection
    connection.close()


@pytest.fixture
def today():
    return date(2026, 9, 23)