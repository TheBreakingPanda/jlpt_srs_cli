"""Configuration resolution for the CLI.

Two settings are resolvable: the SQLite deck path and the daily new-card cap.
Each is resolved with the precedence  flag > env var > config file > default.

The `resolve_*` functions are pure: they take the flag, an env mapping, and the
already-loaded config dict as arguments - they never read os.environ or the disk
themselves - so the whole precedence matrix is unit-testable without I/O.
"""

import os
import tomllib
from pathlib import Path

DEFAULT_NEW_LIMIT = 25

# Written to a new config file on first run. db_path is left commented so the
# built-in user-data-dir default applies until the user chooses to override it.
_DEFAULT_CONFIG_TEMPLATE = """\
# JLPT SRS configuration. Any line you don't set falls back to a built-in default.

# Where the deck (SQLite database) lives:
# db_path = "{db_path}"

# How many new (never-seen) cards a review session may introduce:
new_limit = {new_limit}
"""


class ConfigError(Exception):
    """A configuration value was present but invalid."""


# --- locations ---------------------------------------------------------------

def default_db_path() -> str:
    """The default deck location: $XDG_DATA_HOME or ~/.local/share, + jlpt/jlpt.db."""
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return str(Path(data_home) / "jlpt" / "jlpt.db")


def config_path() -> Path:
    """The config file location: $XDG_CONFIG_HOME or ~/.config, + jlpt/config.toml."""
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home) / "jlpt" / "config.toml"


# --- resolution (pure) -------------------------------------------------------

def _as_int(value, source: str) -> int:
    """int(value), but raise a clear ConfigError naming the source on garbage."""
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ConfigError(
            f"Invalid new-card limit from {source}: {value!r} (expected an integer)."
        ) from None


def resolve_db_path(flag, env, file_cfg) -> str:
    """flag > env['JLPT_DB'] > file_cfg['db_path'] > default_db_path()."""
    if flag is not None:
        return str(flag)
    if env.get("JLPT_DB") is not None:
        return str(env["JLPT_DB"])
    if file_cfg.get("db_path") is not None:
        return str(file_cfg["db_path"])
    return default_db_path()


def resolve_new_limit(flag, env, file_cfg) -> int:
    """flag > env['JLPT_NEW_LIMIT'] > file_cfg['new_limit'] > DEFAULT_NEW_LIMIT."""
    if flag is not None:
        return int(flag)
    if env.get("JLPT_NEW_LIMIT") is not None:
        return _as_int(env["JLPT_NEW_LIMIT"], "JLPT_NEW_LIMIT")
    if file_cfg.get("new_limit") is not None:
        return _as_int(file_cfg["new_limit"], "config file (new_limit)")
    return DEFAULT_NEW_LIMIT


# --- file I/O ----------------------------------------------------------------

def load_config_file(path) -> dict:
    """Parse the TOML config at `path`; return {} if the file doesn't exist.

    Returning an empty dict (not an error) for a missing file is deliberate:
    the resolvers then simply see "no file" and fall through to env/default.
    """
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "rb") as f:          # tomllib requires binary mode
        return tomllib.load(f)


def ensure_file(path) -> None:
    """Create a default config file at `path` once, if it's missing.

    Idempotent: if the file already exists it's left untouched, so a user's
    own edits are never clobbered.
    """
    p = Path(path)
    if p.exists():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        _DEFAULT_CONFIG_TEMPLATE.format(
            db_path=default_db_path(), new_limit=DEFAULT_NEW_LIMIT
        ),
        encoding="utf-8",
    )