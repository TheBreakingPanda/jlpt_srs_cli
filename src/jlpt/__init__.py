"""JLPT SRS CLI - a terminal spaced-repetition trainer for JLPT vocabulary."""

from importlib.metadata import PackageNotFoundError, version

# The version lives in ONE place - pyproject.toml - and is read back from the
# installed package's metadata, so `jlpt --version` can never drift from it.
try:
    __version__ = version("jlpt-srs-cli")
except PackageNotFoundError:  # a source tree that was never installed
    __version__ = "0.0.0+unknown"

