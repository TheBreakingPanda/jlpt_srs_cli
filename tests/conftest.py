import pytest
from jlpt.db import init_db

@pytest.fixture
def conn(tmp_path):
    connection = init_db(tmp_path / "test.db")   # real file, exercises the path logic
    yield connection
    connection.close()