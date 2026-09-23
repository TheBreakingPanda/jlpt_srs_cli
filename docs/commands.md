# 💻 JLPT SRS CLI - Commands

> The CLI contract. Entry point `jlpt` (Typer). Not all of this exists yet - this is the target surface.

---

## Running the CLI

**One-time setup** - register the `jlpt` command (venv active):

```bash
pip install -e .
```

**Launch** - every session, from a fresh terminal:

```bash
cd /home/violet/project_base/jlpt_srs_cli   # project root
source .venv/bin/activate                    # activate the virtualenv
jlpt --help          # list every command
jlpt review          # launch a review session
```

No install? Run it as a module from the project root:

```bash
python -m jlpt --help
python -m jlpt review
```

The `jlpt` entry point is declared in `pyproject.toml` (`[project.scripts] jlpt = "jlpt.cli:app"`); `python -m jlpt` runs `src/jlpt/__main__.py`. Typer gives every command `--help` for free.

---

## Contract

| Command                  | Purpose                                                                                                               |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `jlpt import <file.csv>` | Import/sync vocabulary from a Word Bank CSV export into the deck (by `card_id`; content-only, never resets SRS state) |
| `jlpt add`               | Add a single card interactively                                                                                       |
| `jlpt review`            | Quiz the due cards - type your answer, auto-graded by correctness + attempts; `--kana` shows readings instead of kanji |
| `jlpt stats`             | Show progress - due today, streak, accuracy, totals                                                                   |

---

## More commands (recommended)

Beyond the four core commands, these are worth adding. **Status** marks when each fits.

| Command | Purpose | Status |
| ------- | ------- | ------ |
| `jlpt list` | Browse / search / filter the deck (by due, source, or text) | v1 |
| `jlpt show <card_id>` | One card: content, SRS state, and review history | v1 |
| `jlpt edit <card_id>` | Correct a card's fields | v1 |
| `jlpt remove <card_id>` | Delete a card (with confirmation) | v1 |
| `jlpt undo` | Revert the last review - rescue a misgrade | v1 |
| `jlpt export <file>` | Back up the deck + SRS state (CSV / JSON) | v1 |
| `jlpt version` | Print the version (also `--version`) | v1 |
| `jlpt config` | View / set settings (DB path, daily new-card cap) | Phase 4 |
| `jlpt reset [<card_id>]` | Reset SRS state to relearn - **destructive**, confirm | Phase 4 |
| `jlpt gui` | Launch the desktop app | v2 · P6 |
| `jlpt tutorial` | Open the in-app tutorial / help | v2 · P7 |
| `jlpt deck` | List / switch per-level decks (N5 / N4 ...) | v2 · P5 |
| `jlpt mode` | Set review mode - recognition / production | v2 · P5 |
| `jlpt scheduler` | Switch scheduler - SM-2 / FSRS | v2 · P5 |
| `jlpt audio <card_id>` | Play the card's pronunciation | v2 · P7 |

> This is the **target surface**, not a commitment to build all of it. The v2 rows are CLI entry points for features already scoped in [[JLPT SRS CLI - Project Plan]].

---

## Examples

```bash
# import a Word Bank export
jlpt import data/word_bank.csv
# → Imported 20 cards (5 new, 15 updated).

# quiz what's due today (kanji prompts by default)
jlpt review
#   本
#   reading (kana): ほん      ✓
#   meaning:        book      ✓
#   → correct, first try (grade 5)

# show readings instead of kanji while you're still learning kanji
jlpt review --kana
#   ほん
#   meaning: book             ✓

# progress
jlpt stats
# → Due today: 12 · Reviewed today: 8 · Streak: 5 days · Accuracy (30d): 84%

# add one card
jlpt add
# → front: 図書館  reading: としょかん  back: library  source: word_bank
```

## Grading (SM-2 quality)

The scheduler still runs on the SM-2 0-5 scale, but **you no longer pick the grade** - `jlpt review` derives it from your typed answer and attempts:

- all required parts right on the **first try → 5**
- right **after a retry → 3**
- **wrong or revealed → fail (< 3**, the card resets)

The underlying scale it maps onto: `0` blackout · `1-2` fail · `3` correct but hard · `4` correct, hesitant · `5` correct, instant.

## Notes

- The Phase 0 throwaway prototype (`scripts/import_word_bank.py`) has been **deleted** - `jlpt import` (Phase 1) does the job now. Its code remains recoverable in git history.
- Full flag/option details live in the repo's `docs/commands.md`.

## Development & Testing

One-time setup - editable install with the dev extras (pytest, ruff, pytest-sugar, pytest-html):

```bash
pip install -e ".[dev]"
```

Run the tests from the project root, venv active:

```bash
pytest                          # run everything
pytest -v                       # verbose - one line per test
pytest tests/test_importer.py   # a single file
pytest -k reimport              # only tests matching a keyword
```

**Reporting & logging** (in `pyproject.toml` `[tool.pytest.ini_options]`):

- Every run writes a self-contained **`report.html`** (`pytest-html`), restyled by a custom **dark theme** at **`assets/report.css`**. `report.html` is git-ignored; `assets/report.css` is committed.
- `pytest-sugar` gives a nicer live progress bar.
- Tests **narrate their steps.** `conftest.py` provides a `step()` fixture (numbered `INFO` logs) plus an autouse START/END boundary logger. `log_level = "INFO"` captures them into the report's *Captured log*; `log_cli = true` streams them live in the terminal as the run happens.

Test layout (`tests/`):

| File               | Covers                                                                                  |
| ------------------ | --------------------------------------------------------------------------------------- |
| `conftest.py`      | shared fixtures: `conn` (in-memory DB, `PRAGMA foreign_keys = ON`, schema loaded), `today`, `step` (step logger) + an autouse test-boundary logger |
| `test_models.py`   | `Card.from_export_row` column mapping                                                   |
| `test_db.py`       | schema creation, column defaults, FK enforcement                                        |
| `test_importer.py` | fresh import, content-only upsert (SRS state preserved), unchanged re-import is a no-op |
| `test_srs.py`      | SM-2 scheduling (**Phase 2**) - interval progression, rounding, ease floor, failure reset, grade guard |
| `test_review.py`   | **Phase 3** - due-card selection & ordering, and `apply_review` (pass, fail, not-found guard) |

## See Also
- [[JLPT SRS CLI - Architecture]] · [[JLPT SRS CLI - Data Model]] · [[JLPT SRS CLI - MOC]]
