# 💻 JLPT SRS CLI - Data Model

> SQLite schema as shipped in v1. `cards` holds content + scheduling state; `reviews` holds history. Vocabulary content is mirrored from Obsidian; SRS state is app-owned. The deck lives at `~/.local/share/jlpt/jlpt.db` by default.

---

## `cards`

| Field | Type | Notes |
|-------|------|-------|
| `card_id` | TEXT PK | The Word Bank ID (`EO001`, `VB064`…) - stable, from the vault; hand-added cards get `USR001`, `USR002`… |
| `source` | TEXT | Where it came from (`word_bank`, `n5_core`, `n4_core`, or `user` for `jlpt add`) |
| `front` | TEXT | Prompt side (kanji / word) |
| `back` | TEXT | Answer side (English) |
| `reading` | TEXT | Kana reading |
| `ease_factor` | REAL | SM-2 ease (starts 2.5) |
| `interval` | INTEGER | Days until next review |
| `repetitions` | INTEGER | Consecutive successful reviews |
| `due_date` | TEXT (ISO date) | Next review date; NULL = never reviewed (a "new" card) |
| `created_at` | TEXT | First import |
| `updated_at` | TEXT | Last content change (import sync or `jlpt edit`) |

> `card_id` = the vault ID ⇒ same-reading words (`暑い` IA010 / `熱い` IA012) never collide. Re-import updates content by `card_id` and **never** touches ease/interval/repetitions/due. `jlpt edit` writes only `front` / `back` / `reading` (+ `updated_at`).

> **Quiz answer keys:** `jlpt review` grades typed answers against `reading` (kana) and `back` (English) - a kanji prompt checks both, a kana prompt checks the meaning only. **Romaji is intentionally not stored** (the CSV's `Romaji` column is dropped at import), so the quiz never uses or accepts it.

## `reviews`

| Field | Type | Notes |
|-------|------|-------|
| `id` | INTEGER PK AUTOINCREMENT | Also the order `undo` walks back through |
| `card_id` | TEXT FK → cards | |
| `reviewed_at` | TEXT (ISO datetime) | |
| `grade` | INTEGER | 0-5 (SM-2 quality) |
| `interval_after` | INTEGER | interval assigned by this review |
| `ease_after` | REAL | ease after this review |
| `ease_before` | REAL | **undo snapshot** - card's ease before this review |
| `interval_before` | INTEGER | **undo snapshot** - interval before |
| `repetitions_before` | INTEGER | **undo snapshot** - repetitions before |
| `due_before` | TEXT | **undo snapshot** - due date before (NULL if the card was new) |

> The four `*_before` columns let `jlpt undo` restore a card exactly. They are NULL on reviews logged before they existed; `undo` refuses those rather than write NULLs over the card.

## Relationships

```
cards (1) ───< (many) reviews
```

`jlpt remove` deletes a card's reviews and the card in one transaction (the FK would otherwise block it).

## Migrations

`init_db` runs on every command: `create_schema` (CREATE TABLE IF NOT EXISTS) then `migrate`. Because CREATE IF NOT EXISTS never alters an existing table, decks created before Phase 3 lacked the `*_before` columns; `migrate` detects them with `PRAGMA table_info(reviews)` and adds any that are missing with `ALTER TABLE ... ADD COLUMN`, all in one transaction. It only adds columns, so no data changes, and it is idempotent.

## Future tables (not v1)

- `decks` - if the deck is ever split (N5 / N4 / thematic).
- Settings shipped as a TOML file (`~/.config/jlpt/config.toml`), not a table - see [JLPT SRS CLI - Commands](commands.md).

---

## Schema (SQLite, as in `db.py`)

```sql
CREATE TABLE cards (
  card_id     TEXT PRIMARY KEY,
  source      TEXT NOT NULL,
  front       TEXT NOT NULL,
  back        TEXT,
  reading     TEXT,
  ease_factor REAL    DEFAULT 2.5,
  interval    INTEGER DEFAULT 0,
  repetitions INTEGER DEFAULT 0,
  due_date    TEXT,
  created_at  TEXT DEFAULT (date('now')),
  updated_at  TEXT DEFAULT (date('now'))
);

CREATE TABLE reviews (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id            TEXT NOT NULL REFERENCES cards(card_id),
  reviewed_at        TEXT DEFAULT (datetime('now')),
  grade              INTEGER NOT NULL,
  interval_after     INTEGER,
  ease_after         REAL,
  ease_before        REAL,
  interval_before    INTEGER,
  repetitions_before INTEGER,
  due_before         TEXT
);
```

## See Also
- [JLPT SRS CLI - Architecture](architecture.md) · [JLPT SRS CLI - Commands](commands.md)

