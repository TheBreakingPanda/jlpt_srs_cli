from jlpt.models import Card
from jlpt.importer import import_cards


def test_fresh_import_inserts_all(conn, step):
    step("build 2 fresh cards")
    cards = [
        Card("EO001", "word_bank", "本", "book", "ほん"),
        Card("EO002", "word_bank", "辞書", "dictionary", "じしょ"),
    ]
    step("import into an empty DB -> expect (2 new, 0 updated)")
    assert import_cards(conn, cards) == (2, 0)
    step("assert both rows are present")
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 2


def test_reimport_updates_content_but_preserves_srs(conn, step):
    step("import EO001 once")
    import_cards(conn, [Card("EO001", "word_bank", "本", "book", "ほん")])

    step("simulate review history + stamp OLD sentinel timestamps")
    conn.execute(
        "UPDATE cards SET ease_factor=2.8, interval=6, repetitions=3, "
        "due_date='2026-08-15', created_at='2000-01-01', updated_at='2000-01-01' "
        "WHERE card_id='EO001'"
    )
    conn.commit()

    step("re-import EO001 with CHANGED content -> expect (0 new, 1 updated)")
    changed = Card("EO001", "word_bank", "本", "book (revised)", "ほん")
    assert import_cards(conn, [changed]) == (0, 1)

    step("read the row back")
    row = conn.execute(
        "SELECT back, ease_factor, interval, repetitions, due_date, "
        "created_at, updated_at FROM cards WHERE card_id='EO001'"
    ).fetchone()

    step("assert content updated, SRS state + created_at preserved, updated_at bumped")
    assert row["back"] == "book (revised)"        # content updated
    assert row["ease_factor"] == 2.8              # SRS state preserved
    assert row["interval"] == 6
    assert row["repetitions"] == 3
    assert row["due_date"] == "2026-08-15"
    assert row["created_at"] == "2000-01-01"      # creation stamp preserved
    assert row["updated_at"] != "2000-01-01"      # bumped away from the sentinel


def test_reimport_unchanged_is_noop(conn, step):
    step("import EO001, then stamp an old updated_at sentinel")
    card = Card("EO001", "word_bank", "本", "book", "ほん")
    import_cards(conn, [card])
    conn.execute("UPDATE cards SET updated_at='2000-01-01' WHERE card_id='EO001'")
    conn.commit()

    step("re-import the identical card -> expect (0 new, 0 updated)")
    assert import_cards(conn, [card]) == (0, 0)   # nothing new, nothing changed

    step("assert updated_at untouched (true no-op)")
    row = conn.execute("SELECT updated_at FROM cards WHERE card_id='EO001'").fetchone()
    assert row["updated_at"] == "2000-01-01"      # untouched
