# 💻 JLPT SRS CLI - Architecture

> The stable technical design. Layers are decoupled so each can change independently.

---

## Pipeline

```
Obsidian  (Word Bank / N5 Core / N4 Core - source of truth)
    ↓
Markdown / CSV        (export from the vault)
    ↓
Importer              (parse rows → normalise into Card fields)
    ↓
Card Model            (in-memory representation)
    ↓
SQLite                (data/jlpt.db - cards + review history)
    ↓
SRS Engine            (SM-2: ease, interval, next due date)
    ↓
Review CLI            (jlpt review - quiz: type answer, auto-grade, reschedule)
```

## Principles

- **One-way source.** Vocabulary flows *out of* Obsidian into the app; the app never rewrites the vault. Obsidian stays authoritative for content.
- **Import is idempotent.** Re-importing updates card *content* by `card_id`; it never resets SRS state (ease/interval/due).
- **SRS state is app-only.** Ease, interval, repetitions, due date, and review history live only in SQLite.
- **Layers are swappable.** The importer could later read Markdown directly; storage could move off SQLite - the Card Model + SRS Engine wouldn't change.
- **No synthetic data.** The database is only ever populated from a real Word Bank export. No hardcoded/seed vocabulary at any phase - throwaway scripts exercise the real pipeline or they don't exist.

---

## Source code (WSL)

```
/home/violet/project_base/jlpt_srs_cli
├── src/jlpt/
│   ├── __init__.py  __main__.py  cli.py
│   ├── db.py        models.py    importer.py
│   ├── srs.py       review.py    stats.py    quiz.py
├── tests/           (conftest.py, test_srs.py, test_db.py, test_importer.py, test_review.py, test_models.py)
├── assets/          (report.css - custom pytest-html report theme)
├── data/            (word_bank.csv, jlpt.db)
├── docs/            (architecture.md, data-model.md, commands.md)
├── scripts/         (import_word_bank.py - throwaway; deleted once `jlpt import` lands)
├── .gitignore  LICENSE  README.md  pyproject.toml
```

Git: <https://github.com/TheBreakingPanda/jlpt_srs_cli>

**Start working:**
```bash
cd /home/violet/project_base/jlpt_srs_cli
source .venv/bin/activate
```

> These Obsidian docs mirror `docs/` in the repo (architecture / data-model / commands) at a planning level; the repo copies are the implementation reference.

## Testing

- **Stack:** `pytest`, with `pytest-sugar` (live progress bar) and `pytest-html` (report). Dev deps live in `pyproject.toml` `[project.optional-dependencies].dev` - install with `pip install -e ".[dev]"`.
- **Fixtures (`tests/conftest.py`):** `conn` builds a fresh **in-memory** SQLite DB per test with `PRAGMA foreign_keys = ON` and the schema loaded; `today` pins a deterministic date; `step` is a numbered step-logger. In-memory storage plus injected dates keep tests fast and independent of the wall clock.
- **Layered like the code.** `test_srs` exercises the pure scheduler (no DB); `test_db` / `test_importer` the storage layer; `test_review` / `test_quiz` the due-query, the `apply_review` persistence seam, and the typed-answer + grade-from-attempts logic. These assert *persistence, branching, and answer-checking* - they never re-derive SM-2 maths; that stays in `test_srs`.
- **Self-documenting runs.** Each test calls `step("...")` at every meaningful action; those log at INFO and surface both live in the terminal (`log_cli`) and in a styled **`report.html`** (`pytest-html`, theme `assets/report.css`). A run reads as a narrative of what each test did.

## See Also
- [[JLPT SRS CLI - MOC]] · [[JLPT SRS CLI - Data Model]] · [[JLPT SRS CLI - Commands]]
