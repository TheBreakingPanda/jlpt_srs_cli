# 💻 JLPT SRS CLI - Commands

> The CLI as shipped in v1. Entry point `jlpt` (Typer); every command takes `--help`. The repo's `README.md` is the user-facing version of this note.

---

## Running the CLI

**Installed** (the v1 target; `pipx` is verified in the Phase 4 packaging step):

```bash
pipx install git+https://github.com/TheBreakingPanda/jlpt_srs_cli.git
jlpt                 # bare `jlpt` shows the styled command reference
```

**From the repo** (development), every session:

```bash
cd /home/violet/project_base/jlpt_srs_cli   # project root
source .venv/bin/activate                    # or prefix commands with `uv run`
jlpt --help
python -m jlpt review                        # same CLI, run as a module
```

The entry point is declared in `pyproject.toml` (`[project.scripts] jlpt = "jlpt.cli:app"`); `python -m jlpt` runs `src/jlpt/__main__.py`.

---

## Shipped commands (v1)

| Command | Options | What it does |
| --- | --- | --- |
| `jlpt import [CSV]` | `--source TAG` (default `word_bank`) | Import or re-sync a Word Bank CSV by `card_id`. Content only: SRS state is never reset, and unchanged rows are not written. `CSV` defaults to `data/word_bank.csv`. |
| `jlpt review` | `--kana`, `--new N` | Quiz every due card plus up to N never-seen ones (N from config, default 25). The grade comes from the typed answers - see Grading. |
| `jlpt stats` | | Total cards, due today, reviewed today, streak, accuracy. |
| `jlpt add` | | Prompts for kanji, reading, meaning; the card gets the next `USR###` id and source `user`. |
| `jlpt list [TEXT]` | `--due`, `--source TAG`, `--limit N` | Table of cards; `TEXT` matches kanji, reading or meaning. |
| `jlpt show ID` | | Content, SRS state and review history. |
| `jlpt edit ID` | `--kanji`, `--reading`, `--meaning` | Correct content in one transaction. SRS state is kept, identical values are a no-op, blank values are rejected. Warns when the card came from an import (the next import would revert it). |
| `jlpt remove ID` | | Asks, then deletes the card and its reviews together. |
| `jlpt undo` | | Restores the card to its snapshot from before the latest review, and deletes that review. Refuses reviews logged before the snapshot columns existed. |
| `jlpt export FILE` | `--force` | Backup by file extension: `.json` = cards + reviews + header (lossless); `.csv` = cards only. Won't overwrite without `--force`. A backup, not a sync. |
| `jlpt version` | | Print the installed version (same as `jlpt --version`). |
| `jlpt help` | | Command reference (same as bare `jlpt`). |

**Global options** go before the command: `--db PATH` picks the deck for this run; `--version` prints the version and exits without creating a config file or opening a deck.

---

## Not built in v1

| Command | Purpose | Status |
| --- | --- | --- |
| `jlpt config` | View / set settings (DB path, daily new-card cap) | Not built - v1 uses the config file `~/.config/jlpt/config.toml` |
| `jlpt reset [<card_id>]` | Reset SRS state to relearn - **destructive**, confirm | Deferred (Phase 4 plan: only if cheap) |
| `jlpt gui` | Launch the desktop app | v2 · P6 |
| `jlpt tutorial` | Open the in-app tutorial / help | v2 · P7 |
| `jlpt deck` | List / switch per-level decks (N5 / N4 ...) | v2 · P5 |
| `jlpt mode` | Set review mode - recognition / production | v2 · P5 |
| `jlpt scheduler` | Switch scheduler - SM-2 / FSRS | v2 · P5 |
| `jlpt audio <card_id>` | Play the card's pronunciation | v2 · P7 |

> The v2 rows are CLI entry points for features scoped in JLPT SRS CLI - Project Plan, not commitments.

---

## Examples (real output)

```bash
jlpt import data/word_bank.csv
# Imported 661 cards (661 new, 0 updated).

jlpt review                      # kanji prompt: reading, then meaning
# Kanji: 本
# Reading?: ほん
# Meaning?: book
# Grade: 5
# Reviewed 1 card(s).

jlpt review --kana               # reading prompt: meaning only
# Reading: ほん
# Meaning?: book

jlpt edit CQ001 --meaning "one (thing)"
# Updated CQ001 (meaning).
# CQ001 came from 'word_bank' - the next import will overwrite this edit unless you fix it in the source file too.
# (then the card, as `jlpt show` prints it)

jlpt export ~/backups/jlpt.json
# Exported 661 cards and 15 reviews to /home/violet/backups/jlpt.json.

jlpt undo                        # on a review from before the migration
# Can't undo the review of CQ015 from 2026-09-25 21:05:55: it predates undo support, so there's no earlier state to restore.
```

## Grading (SM-2 quality)

The scheduler runs on the SM-2 0-5 scale, but **you never pick the grade** - `jlpt review` derives it from your typed answers, with one retry per answer:

| Outcome | Grade | Effect |
| --- | --- | --- |
| Every required part right first try | 5 | passes; ease rises |
| Right, but at least one retry used | 3 | passes; ease drops |
| Still wrong after the retry | 1 | fails; card restarts (due tomorrow), ease unchanged |

A kanji prompt requires reading **and** meaning (the meaning isn't asked if the reading fails); a `--kana` prompt requires the meaning only. The underlying scale: `0` blackout · `1-2` fail · `3` correct but hard · `4` correct, hesitant · `5` correct, instant. The maths is in [JLPT SRS CLI - SM-2 Algorithm](SM-2%20algorithm.md).

## Configuration

Two settings, each resolved **flag > environment variable > config file > built-in default**:

| Setting | Flag | Env var | Config key | Default |
| --- | --- | --- | --- | --- |
| Deck path | `--db` | `JLPT_DB` | `db_path` | `~/.local/share/jlpt/jlpt.db` |
| New cards per session | `--new` | `JLPT_NEW_LIMIT` | `new_limit` | `25` |

The config file is `~/.config/jlpt/config.toml`, written with commented defaults on first run. `XDG_CONFIG_HOME` / `XDG_DATA_HOME` move both locations. A non-integer `new_limit` fails loudly with the source named.

## Development & Testing

One-time setup - editable install with the dev extras (pytest, ruff, pytest-sugar, pytest-html):

```bash
pip install -e ".[dev]"          # or: uv sync --extra dev
```

Run from the project root, venv active (or prefix with `uv run`):

```bash
pytest                          # everything; also writes report.html
pytest -v                       # one line per test
pytest tests/test_export.py     # a single file
pytest -k migrate               # only tests matching a keyword
ruff check .                    # lint
```

**Reporting & logging** (in `pyproject.toml` `[tool.pytest.ini_options]`):

- Every run writes a self-contained **`report.html`** (`pytest-html`), restyled by the dark theme **`assets/report.css`**. `report.html` is git-ignored; the CSS is committed.
- Tests **narrate their steps**: `conftest.py` provides a `step()` fixture (numbered `INFO` logs) and an autouse START/END logger; `log_cli = true` streams them live.
- Tests are **hermetic**: an autouse fixture points the XDG dirs at a temp folder and clears `JLPT_*` variables, so no test reads or writes the real config or deck.

Test layout (`tests/`):

| File | Covers |
| --- | --- |
| `conftest.py` | `conn` (in-memory DB, foreign keys on, schema loaded), `today`, `step`, the boundary logger, the hermetic-environment fixture |
| `test_models.py` | `Card.from_export_row` column mapping |
| `test_db.py` | schema creation, defaults, FK enforcement; **migration** of a pre-snapshot deck (columns added, rows kept, idempotent, review works after) |
| `test_importer.py` | fresh import, content-only re-sync (SRS kept), unchanged re-import is a no-op |
| `test_srs.py` | SM-2 scheduling - interval progression, rounding, ease floor, failure reset, grade guard |
| `test_review.py` | due-card selection and new-card cap; `apply_review` (pass, fail, not found, before-state snapshot) |
| `test_quiz.py` | grade from attempts; reading and meaning answer checks |
| `test_stats.py` | totals, due/reviewed today, accuracy, streak edge cases |
| `test_config.py` | precedence for both settings, fail-loud bad values, XDG paths, first-run file |
| `test_cards.py` | `update_card` - writes, no-ops, whitelist and blank-value rejection |
| `test_export.py` | JSON and CSV round-trips, file contents, foreign/broken file rejection |
| `test_cli.py` | every command end to end through Typer's `CliRunner` |

## See Also
- [JLPT SRS CLI - Architecture](architecture.md) · [JLPT SRS CLI - Data Model](data-model.md) · JLPT SRS CLI - MOC

