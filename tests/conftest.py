import logging
import sqlite3
from datetime import date

import pytest

logger = logging.getLogger("jlpt.tests")

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
    logger.info("setup: in-memory SQLite, foreign_keys ON, schema loaded")
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    yield connection
    connection.close()
    logger.info("teardown: connection closed")


@pytest.fixture
def today():
    return date(2026, 9, 23)


@pytest.fixture
def step():
    """Call step('doing X') inside a test to record a numbered step.

    Each call logs at INFO, so the steps appear in the pytest-html
    'Captured log' section for that test.
    """
    counter = {"n": 0}

    def _step(message):
        counter["n"] += 1
        logger.info("step %d — %s", counter["n"], message)

    return _step


@pytest.fixture(autouse=True)
def _log_boundaries(request):
    """Bookend every test so none ever shows 'No log output captured'."""
    logger.info("START %s", request.node.name)
    yield
    logger.info("END   %s", request.node.name)
