"""Tests for config resolution and the config file I/O.

The resolvers are pure, so most of these pass plain dicts - no disk, no env
mutation. The file-I/O tests use tmp_path. The precedence tests are the point:
they prove flag > env > file > default, in that order, for both settings.
"""

import pytest

from jlpt import config


# --- resolve_new_limit: precedence ------------------------------------------

def test_new_limit_flag_wins_over_everything():
    assert config.resolve_new_limit(
        5, {"JLPT_NEW_LIMIT": "10"}, {"new_limit": 20}
    ) == 5


def test_new_limit_env_wins_when_no_flag():
    assert config.resolve_new_limit(
        None, {"JLPT_NEW_LIMIT": "10"}, {"new_limit": 20}
    ) == 10


def test_new_limit_file_wins_when_no_flag_or_env():
    assert config.resolve_new_limit(None, {}, {"new_limit": 20}) == 20


def test_new_limit_falls_back_to_default():
    assert config.resolve_new_limit(None, {}, {}) == config.DEFAULT_NEW_LIMIT


# --- resolve_new_limit: fail-loud -------------------------------------------

def test_new_limit_bad_env_fails_loud():
    with pytest.raises(config.ConfigError):
        config.resolve_new_limit(None, {"JLPT_NEW_LIMIT": "abc"}, {})


def test_new_limit_bad_file_fails_loud():
    with pytest.raises(config.ConfigError):
        config.resolve_new_limit(None, {}, {"new_limit": "lots"})


def test_new_limit_valid_env_string_coerces_to_int():
    assert config.resolve_new_limit(None, {"JLPT_NEW_LIMIT": "10"}, {}) == 10


# --- resolve_db_path: precedence --------------------------------------------

def test_db_path_flag_wins():
    assert config.resolve_db_path(
        "/flag.db", {"JLPT_DB": "/env.db"}, {"db_path": "/file.db"}
    ) == "/flag.db"


def test_db_path_env_wins_when_no_flag():
    assert config.resolve_db_path(
        None, {"JLPT_DB": "/env.db"}, {"db_path": "/file.db"}
    ) == "/env.db"


def test_db_path_file_wins_when_no_flag_or_env():
    assert config.resolve_db_path(None, {}, {"db_path": "/file.db"}) == "/file.db"


def test_db_path_falls_back_to_default():
    assert config.resolve_db_path(None, {}, {}) == config.default_db_path()


# --- location helpers honour XDG --------------------------------------------

def test_default_db_path_honours_xdg(monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "/data")
    assert config.default_db_path() == "/data/jlpt/jlpt.db"


def test_config_path_honours_xdg(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/cfg")
    assert str(config.config_path()) == "/cfg/jlpt/config.toml"


# --- file I/O ----------------------------------------------------------------

def test_load_missing_file_returns_empty_dict(tmp_path):
    assert config.load_config_file(tmp_path / "nope.toml") == {}


def test_ensure_file_creates_a_parseable_default(tmp_path):
    path = tmp_path / "jlpt" / "config.toml"
    config.ensure_file(path)
    assert path.exists()
    # The written default must be valid TOML and carry the new_limit default.
    loaded = config.load_config_file(path)
    assert loaded["new_limit"] == config.DEFAULT_NEW_LIMIT


def test_ensure_file_is_idempotent(tmp_path):
    path = tmp_path / "config.toml"
    config.ensure_file(path)
    path.write_text('new_limit = 7\n', encoding="utf-8")   # user edits it
    config.ensure_file(path)                                # must NOT clobber
    assert config.load_config_file(path)["new_limit"] == 7
