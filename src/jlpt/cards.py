"""Card content edits - the logic behind `jlpt edit`.

Edits touch content only: front / back / reading. SRS state belongs to the
scheduler and is never written here; card_id and source are identity, not
content. Kept out of cli.py so the rules are unit-testable without a CLI run.
"""

from __future__ import annotations

import sqlite3

# Column names can't be bound as SQL parameters - only values can - so the SET
# clause is built from this whitelist, never from caller input directly.
EDITABLE_FIELDS: frozenset[str] = frozenset({"front", "back", "reading"})

# How each column is named to the user (matches the CLI flags and `show`).
FIELD_LABELS: dict[str, str] = {"front": "kanji", "reading": "reading", "back": "meaning"}


class CardNotFoundError(LookupError):
    """No card has the requested card_id."""


def update_card(
    conn: sqlite3.Connection, card_id: str, changes: dict[str, str]
) -> list[str]:
    """Apply content edits to one card, in a single transaction.

    Values are stripped and must not be blank. Fields whose new value equals
    the stored one are dropped; if nothing actually differs, nothing is
    written and updated_at is not bumped - the importer's content-diff rule.

    Returns the changed column names, sorted (an empty list means a no-op).
    Raises ValueError for an empty `changes`, a non-editable field, or a blank
    value, and CardNotFoundError if card_id doesn't exist. Validation happens
    before the database is touched.
    """
    if not changes:
        raise ValueError("Nothing to edit - pass at least one field.")
    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"Not editable: {', '.join(sorted(unknown))}.")

    cleaned: dict[str, str] = {}
    for column, value in changes.items():
        value = value.strip()
        if not value:
            raise ValueError(f"The {FIELD_LABELS[column]} can't be blank.")
        cleaned[column] = value

    with conn:  # one transaction: commit on success, roll back on any error
        row = conn.execute(
            "SELECT front, back, reading FROM cards WHERE card_id = ?", (card_id,)
        ).fetchone()
        if row is None:
            raise CardNotFoundError(card_id)

        changed = sorted(c for c, v in cleaned.items() if row[c] != v)
        if not changed:
            return []

        # Safe to interpolate: every name in `changed` passed the whitelist.
        assignments = ", ".join(f"{column} = ?" for column in changed)
        conn.execute(
            f"UPDATE cards SET {assignments}, updated_at = date('now') "
            "WHERE card_id = ?",
            [cleaned[column] for column in changed] + [card_id],
        )
    return changed
