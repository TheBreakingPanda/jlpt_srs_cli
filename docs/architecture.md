# 💻 JLPT SRS CLI - Architecture

> The technical design as shipped in v1. Layers are decoupled so each can change independently.

---

## Pipeline

```
Obsidian  (Word Bank - source of truth; N5 Core / N4 Core later)
    ↓  CSV export
Importer        importer.py   read rows → Card → content-diff upsert by card_id
    ↓
Card Model      models.py     frozen dataclass, content only
    ↓
SQLite deck     db.py         ~/.local/share/jlpt/jlpt.db - cards + review history;
    ↓                         schema created and older decks migrated on open
SRS Engine      srs.py        pure SM-2: ease, interval, next due date
    ↑↓          review.py     persistence seam: due-card selection, apply_review
    ↑           quiz.py       answer checks, grade from attempts
Review CLI      cli.py        Typer commands → ui.py (all Rich rendering)

Side paths:  config.py → cli.py   deck path + new-card cap, resolved once at startup
             cards.py  ← cli.py   content edits (jlpt edit)
             export.py ← cli.py   deck → JSON / CSV backup (one way, out)
```

## Modules

| Module | Layer | Responsibility |
| --- | --- | --- |
| `cli.py` | interface | Typer app; commands stay thin - open the deck, call the logic, hand results to `ui` |
| `ui.py` | presentation | Shared Rich `Console`, message helpers, `render_*` tables and panels, the help screen |
| `config.py` | configuration | Pure resolvers (flag > env > file > default) plus TOML file I/O and first-run file creation |
| `db.py` | storage | Connection, schema (single source of truth), additive migration, `init_db` |
| `models.py` | domain | `Card` - the importer's typed shape before anything touches SQLite |
| `importer.py` | ingest | CSV → `Card` → content-diff upsert; never touches SRS state |
| `srs.py` | domain | SM-2 maths - no I/O, no clock; `today` is injected |
| `review.py` | persistence | Due-card query with new-card cap; `apply_review` writes card state + review row atomically |
| `quiz.py` | domain | Reading / meaning answer checks; grade from attempts |
| `stats.py` | reporting | Totals, due/reviewed today, accuracy, streak |
| `cards.py` | domain | `update_card` - whitelisted, validated content edits in one transaction |
| `export.py` | backup | Fetch the deck, write JSON / CSV atomically, read a backup back |

## Principles

- **One-way source.** Vocabulary flows *out of* Obsidian into the app; the app never rewrites the vault. Obsidian stays authoritative for content.
- **Import is idempotent.** Re-importing updates card *content* by `card_id`; it never resets SRS state (ease/interval/due), and unchanged rows aren't written.
- **SRS state is app-only.** Ease, interval, repetitions, due date and review history live only in SQLite.
- **Edits are local corrections.** `jlpt edit` changes the deck only; for an imported card the next import restores the vault's text, so a real fix belongs in the vault too. The CLI warns about this.
- **Export is a backup, not a sync.** `jlpt export` writes the deck out (JSON lossless, CSV cards-only); nothing reads a backup back into a live deck.
- **Schema changes are additive and migrate on open.** `init_db` runs `create_schema` then `migrate`, so any command upgrades an older deck in place - columns only ever added, in one transaction, idempotent. Rows logged before a migration keep NULLs in the new columns, and code that reads those columns must handle that (`undo` refuses such reviews).
- **Presentation is separate.** All formatting lives in `ui.py`. Card content is wrapped in Rich `Text`, never interpolated into markup, so a meaning like `to go [home]` prints literally.
- **Configuration is resolved once, at the edge.** The Typer callback resolves settings and passes them down via `ctx.obj`; the resolvers are pure functions of (flag, env, file) and unit-tested without I/O.
- **One clock read per command.** `today` is computed in the CLI and injected into the scheduler and queries - nothing deeper reads the clock.
- **Layers are swappable.** The importer could later read Markdown directly; storage could move off SQLite - the Card Model + SRS Engine wouldn't change.
- **No synthetic data.** The deck is only ever populated from a real Word Bank export or the user's own `jlpt add`. No hardcoded/seed vocabulary.

---

## Source code (WSL)

```
/home/violet/project_base/jlpt_srs_cli
├── src/jlpt/
│   ├── __init__.py  __main__.py  cli.py     ui.py      config.py
│   ├── db.py        models.py    importer.py
│   ├── srs.py       review.py    quiz.py    stats.py
│   ├── cards.py     export.py
├── tests/           (one test_*.py per module, plus conftest.py and test_cli.py)
├── assets/          (report.css - custom pytest-html report theme)
├── data/            (word_bank.csv sample export; a git-ignored pre-XDG jlpt.db)
├── docs/            (architecture.md, commands.md, data-model.md, languages.md, SM-2 algorithm.md)
├── .gitignore  LICENSE  README.md  pyproject.toml  uv.lock
```

Runtime files live outside the repo: the deck at `~/.local/share/jlpt/jlpt.db` and the config at `~/.config/jlpt/config.toml` (XDG locations, so a `pipx` install works the same as a dev checkout).

Git: <https://github.com/TheBreakingPanda/jlpt_srs_cli>

**Start working:**
```bash
cd /home/violet/project_base/jlpt_srs_cli
source .venv/bin/activate          # or prefix commands with `uv run`
```

> These Obsidian docs mirror `docs/` in the repo (architecture / data-model / commands / languages / sm-2 algorithm); the repo copies are the implementation reference, and `README.md` is the user-facing guide.

## Testing

- **Stack:** `pytest`, with `pytest-sugar` (live progress bar) and `pytest-html` (report). Dev deps live in `pyproject.toml` `[project.optional-dependencies].dev` - install with `pip install -e ".[dev]"`. `ruff` lints.
- **Fixtures (`tests/conftest.py`):** `conn` builds a fresh **in-memory** SQLite DB per test with `PRAGMA foreign_keys = ON` and the schema loaded; `today` pins a deterministic date; `step` is a numbered step-logger; an autouse fixture sandboxes the XDG dirs and `JLPT_*` env vars so no test touches the real config or deck.
- **Layered like the code.** `test_srs` exercises the pure scheduler (no DB); `test_db` / `test_importer` the storage layer and migration; `test_review` / `test_quiz` the due-query, the `apply_review` seam and answer checking; `test_cards` / `test_export` / `test_config` / `test_stats` their modules; `test_cli` drives every command end to end through `CliRunner`. Logic tests never re-derive SM-2 maths - that stays in `test_srs`.
- **Rich output is smoke-tested,** not diffed: CLI tests assert that key values appear (whitespace-normalised, since Rich wraps at 80 columns).
- **Self-documenting runs.** Each test calls `step("...")` at every meaningful action; those log at INFO and surface live in the terminal (`log_cli`) and in a styled **`report.html`** (theme `assets/report.css`).

## See Also
- JLPT SRS CLI - MOC · [JLPT SRS CLI - Data Model](data-model.md) · [JLPT SRS CLI - Commands](commands.md)

