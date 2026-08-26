"""Card model — the typed shape the importer builds before anything touches SQLite.

Content only: this is the seam between the CSV importer and the SQLite layer.
SRS state (ease_factor, interval, repetitions, due_date) and timestamps live in
the database (defaults on insert) and the SRS engine (Phase 2), never here.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    """A single vocabulary card's content, mirrored from the Word Bank export.

    Frozen: the importer constructs a Card and never mutates it, so an immutable
    value object is both safer and hashable. The free __eq__ lets tests assert
    ``parsed == Card(...)`` directly.
    """

    card_id: str
    source: str
    front: str
    back: str | None = None
    reading: str | None = None

    @classmethod
    def from_export_row(cls, row: dict[str, str], source: str = "word_bank") -> Card:
        """Build a Card from one Word Bank CSV row.

        Mapping (locked): id→card_id, kanji→front, english→back, reading→reading.
        source defaults to "word_bank"; pass e.g. "n5_core" for other exports.
        Row keys are lowercased by the reader, so index with row["id"].
        """
        return cls(
            card_id=row["id"],
            source=source,
            front=row["kanji"],
            back=row["english"],
            reading=row["reading"],
        )