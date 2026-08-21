# 💻 JLPT SRS CLI — Architecture

> The stable technical design. Layers are decoupled so each can change independently.

---

## Pipeline

```
Obsidian  (Word Bank / N5 Core / N4 Core — source of truth)
    ↓
Markdown / CSV        (export from the vault)
    ↓
Importer              (parse rows → normalise into Card fields)
    ↓
Card Model            (in-memory representation)
    ↓
SQLite                (data/jlpt.db — cards + review history)
    ↓
SRS Engine            (SM-2: ease, interval, next due date)
    ↓
Review CLI            (jlpt review — prompt, grade, reschedule)
```

## Principles

- **One-way source.** Vocabulary flows *out of* Obsidian into the app; the app never rewrites the vault. Obsidian stays authoritative for content.
- **Import is idempotent.** Re-importing updates card *content* by `card_id`; it never resets SRS state (ease/interval/due).
- **SRS state is app-only.** Ease, interval, repetitions, due date, and review history live only in SQLite.
- **Layers are swappable.** The importer could later read Markdown directly; storage could move off SQLite — the Card Model + SRS Engine wouldn't change.
- **No synthetic data.** The database is only ever populated from a real Word Bank export. No hardcoded/seed vocabulary at any phase — throwaway scripts exercise the real pipeline or they don't exist.

---

## Source code (WSL)

```
/home/violet/project_base/jlpt_srs_cli
├── src/jlpt/
│   ├── __init__.py  __main__.py  cli.py
│   ├── db.py        models.py    importer.py
│   ├── srs.py       review.py    stats.py
├── tests/           (test_srs.py, test_importer.py, test_db.py)
├── data/            (word_bank.csv, jlpt.db)
├── docs/            (architecture.md, data-model.md, commands.md)
├── scripts/         (import_word_bank.py — throwaway; deleted once `jlpt import` lands)
├── .gitignore  LICENSE  README.md  pyproject.toml
```

Git: <https://github.com/TheBreakingPanda/jlpt_srs_cli>