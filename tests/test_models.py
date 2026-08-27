from jlpt.models import Card

def test_from_export_row_maps_columns():
    row = {"id": "EO001", "theme": "Everyday Objects", "kanji": "本",
           "reading": "ほん", "romaji": "hon", "english": "book"}
    assert Card.from_export_row(row) == Card(
        card_id="EO001", source="word_bank", front="本", back="book", reading="ほん"
    )

def test_from_export_row_source_override():
    row = {"id": "EO001", "theme": "x", "kanji": "本",
           "reading": "ほん", "romaji": "hon", "english": "book"}
    assert Card.from_export_row(row, source="n5_core").source == "n5_core"