from jlpt.models import Card
from jlpt.importer import import_cards

def test_fresh_import_inserts_all(conn):
    cards = [
        Card("EO001", "word_bank", "本", "book", "ほん"),
        Card("EO002", "word_bank", "辞書", "dictionary", "じしょ"),
    ]
    assert import_cards(conn, cards) == (2, 0)
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 2

def test_reimport_updates_content_but_preserves_srs(conn):
    import_cards(conn, [Card("EO001", "word_bank", "本", "book", "ほん")])

    # simulate this card having been scheduled by reviews, and stamp an OLD sentinel
    conn.execute(
        "UPDATE cards SET ease_factor=2.8, interval=6, repetitions=3, "
        "due_date='2026-08-15', created_at='2000-01-01', updated_at='2000-01-01' "
        "WHERE card_id='EO001'"
    )
    conn.commit()

    # re-import the same id with CHANGED content -> triggers an update
    changed = Card("EO001", "word_bank", "本", "book (revised)", "ほん")
    assert import_cards(conn, [changed]) == (0, 1)

    row = conn.execute(
        "SELECT back, ease_factor, interval, repetitions, due_date, "
        "created_at, updated_at FROM cards WHERE card_id='EO001'"
    ).fetchone()

    assert row["back"] == "book (revised)"        # content updated
    assert row["ease_factor"] == 2.8              # SRS state preserved
    assert row["interval"] == 6
    assert row["repetitions"] == 3
    assert row["due_date"] == "2026-08-15"
    assert row["created_at"] == "2000-01-01"      # creation stamp preserved
    assert row["updated_at"] != "2000-01-01"      # bumped away from the sentinel

def test_reimport_unchanged_is_noop(conn):
    card = Card("EO001", "word_bank", "本", "book", "ほん")
    import_cards(conn, [card])
    conn.execute("UPDATE cards SET updated_at='2000-01-01' WHERE card_id='EO001'")
    conn.commit()

    assert import_cards(conn, [card]) == (0, 0)   # nothing new, nothing changed
    row = conn.execute("SELECT updated_at FROM cards WHERE card_id='EO001'").fetchone()
    assert row["updated_at"] == "2000-01-01"      # untouched