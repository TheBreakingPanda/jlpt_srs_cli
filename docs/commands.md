# 💻 JLPT SRS CLI — Commands

> The CLI contract. Entry point `jlpt` (Typer). Not all of this exists yet — this is the target surface.

---

## Contract

| Command | Purpose |
|---------|---------|
| `jlpt import <file.csv>` | Import/sync vocabulary from a Word Bank CSV export into the deck (by `card_id`; content-only, never resets SRS state) |
| `jlpt add` | Add a single card interactively |
| `jlpt review` | Run the due-card review loop (prompt → reveal → grade 0–5 → reschedule) |
| `jlpt stats` | Show progress — due today, streak, accuracy, totals |

---

## Examples

```bash
# import a Word Bank export
jlpt import data/word_bank.csv
# → Imported 20 cards (5 new, 15 updated).

# review what's due today
jlpt review
# → 12 cards due.
#   [EO001]  本
#   (space to reveal) → ほん · book
#   grade (0–5): 4

# progress
jlpt stats
# → Due today: 12 · Reviewed today: 8 · Streak: 5 days · Accuracy (30d): 84%

# add one card
jlpt add
# → front: 図書館  reading: としょかん  back: library  source: word_bank
```

## Grading (SM-2 quality)

`0` blackout · `1` wrong, familiar · `2` wrong, easy recall on seeing · `3` correct, hard · `4` correct, hesitant · `5` correct, instant.

## Notes

- Phase 0 is a throwaway prototype (`scripts/import_word_bank.py`) — a bare-bones dry run of the same job. `jlpt import` proper lands in Phase 1, at which point the script is deleted.
- Full flag/option details live in the repo's `docs/commands.md`.
