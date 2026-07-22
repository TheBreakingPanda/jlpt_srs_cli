# 💻 JLPT SRS CLI — Data Model

> SQLite schema. `cards` holds content + scheduling state; `reviews` holds history. Vocabulary content is mirrored from Obsidian; SRS state is app-owned.

---

## `cards`

| Field | Type | Notes |
|-------|------|-------|
| `card_id` | TEXT PK | The Word Bank ID (`EO001`, `VB064`…) — stable, from the vault |
| `source` | TEXT | Where it came from (`word_bank`, `n5_core`, `n4_core`) |
| `front` | TEXT | Prompt side (kanji / word) |
| `back` | TEXT | Answer side (English) |
| `reading` | TEXT | Kana reading |
| `ease_factor` | REAL | SM-2 ease (starts 2.5) |
| `interval` | INTEGER | Days until next review |
| `repetitions` | INTEGER | Consecutive successful reviews |
| `due_date` | TEXT (ISO date) | Next review date |
| `created_at` | TEXT | First import |
| `updated_at` | TEXT | Last content sync |

> `card_id` = the vault ID ⇒ same-reading words (`暑い` IA010 / `熱い` IA012) never collide. Re-import updates content by `card_id` and **never** touches ease/interval/repetitions/due.

## `reviews`

| Field | Type | Notes |
|-------|------|-------|
| `id` | INTEGER PK AUTOINCREMENT | |
| `card_id` | TEXT FK → cards | |
| `reviewed_at` | TEXT (ISO datetime) | |
| `grade` | INTEGER | 0–5 (SM-2 quality) |
| `interval_after` | INTEGER | interval assigned by this review |
| `ease_after` | REAL | ease after this review |

## Relationships

```
cards (1) ───< (many) reviews
```

## Future tables (not v1)

- `decks` — if the deck is ever split (N5 / N4 / thematic).
- `settings` — per-user config (daily new-card cap, etc.).

---

## Schema (SQLite, v1 sketch — finalised in code)

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
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id        TEXT NOT NULL REFERENCES cards(card_id),
  reviewed_at    TEXT DEFAULT (datetime('now')),
  grade          INTEGER NOT NULL,
  interval_after INTEGER,
  ease_after     REAL
);
```
