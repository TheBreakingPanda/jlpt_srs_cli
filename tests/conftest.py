import logging
import sqlite3
from datetime import date

import pytest

from jlpt import db

logger = logging.getLogger("jlpt.tests")


# --- database & date fixtures ------------------------------------------------

@pytest.fixture
def conn():
    logger.info("setup: in-memory SQLite, foreign_keys ON, schema loaded")
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    db.create_schema(connection)
    yield connection
    connection.close()
    logger.info("teardown: connection closed")


@pytest.fixture
def today():
    return date(2026, 9, 23)


# --- logging fixtures (step narration) --------------------------------------

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


# --- hermetic environment ----------------------------------------------------

@pytest.fixture(autouse=True)
def _sandbox_env(tmp_path, monkeypatch):
    """Keep config/DB resolution off the real home directory.

    The CLI callback reads and first-run-creates a config file; point the XDG
    dirs at a per-test temp location so tests never read or write the user's
    real ~/.config or ~/.local/share, and drop any ambient JLPT_* overrides so
    the developer's own environment can't leak into a test.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg_config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    monkeypatch.delenv("JLPT_DB", raising=False)
    monkeypatch.delenv("JLPT_NEW_LIMIT", raising=False)
