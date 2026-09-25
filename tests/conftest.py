import logging
import sqlite3
from datetime import date

import pytest

from jlpt import db

logger = logging.getLogger("jlpt.tests")


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
