from datetime import date
from pathlib import Path

import typer

from jlpt import quiz
from jlpt.review import DEFAULT_NEW_LIMIT, apply_review, due_cards

from .db import init_db
from .importer import import_csv

app = typer.Typer(help="JLPT SRS — a spaced-repetition trainer for JLPT vocabulary.")


@app.command("import")
def import_(
    csv_path: Path = typer.Argument(Path("data/word_bank.csv"),
                                    help="Path to a Word Bank CSV export."),
    source: str = typer.Option("word_bank", help="Origin tag stamped on new cards."),
) -> None:
    """Import/sync a Word Bank CSV export into the deck."""
    conn = init_db()
    try:
        new, updated = import_csv(conn, csv_path, source)
        typer.echo(f"Imported {new + updated} cards ({new} new, {updated} updated).")
    finally:
        conn.close()


def _ask_part(label, check, expected) -> tuple[bool, bool]:
    """Ask one part (reading or meaning), allowing one retry.

    `check` is quiz.check_reading or quiz.check_meaning; `expected` is the
    card's value to check against. Return (passed, used_retry).
    """
    typed = typer.prompt(f"{label}?")
    if check(expected, typed):
        return True, False

    typer.echo("Incorrect — try again.")
    typed = typer.prompt(f"{label}? (retry)")
    passed = check(expected, typed)
    if not passed:
        typer.echo(f"The answer was: {expected}")
    return passed, True


def _quiz_card(card, kana_mode) -> int:
    """Show one card, quiz the required parts, return an SM-2 grade."""
    if kana_mode:
        typer.echo(f"Reading: {card['reading']}")
        passed, used_retry = _ask_part("Meaning", quiz.check_meaning, card["back"])
    else:
        typer.echo(f"Kanji: {card['front']}")
        passed, used_retry = _ask_part("Reading", quiz.check_reading, card["reading"])
        if passed:
            passed, retried = _ask_part("Meaning", quiz.check_meaning, card["back"])
            used_retry = used_retry or retried

    attempts = 2 if used_retry else 1
    grade = quiz.grade_from_attempts(attempts, passed)
    typer.echo(f"Grade: {grade}")
    return grade


@app.command("review")
def review(
    kana: bool = typer.Option(False, "--kana",
        help="Prompt with the kana reading instead of the kanji."),
    new: int = typer.Option(DEFAULT_NEW_LIMIT, "--new",
        help="Max new (never-seen) cards to introduce this session."),
) -> None:
    """Quiz the due cards; the grade is derived from your answers."""
    conn = init_db()
    try:
        today = date.today()
        cards = due_cards(conn, today, new)
        if not cards:
            typer.echo("Nothing's due today.")
            return

        reviewed = 0
        for card in cards:
            grade = _quiz_card(card, kana_mode=kana)
            apply_review(conn, card["card_id"], grade, today)
            reviewed += 1

        typer.echo(f"Reviewed {reviewed} card(s).")
    finally:
        conn.close()


@app.command("add")
def add() -> None:
    """Add a new card to the deck."""
    # Implementation for adding a new card would go here


@app.command("stats")
def stats() -> None:
    """Display statistics about the deck."""
    # Implementation for displaying stats would go here


@app.command("list")
def list_cards() -> None:
    """List all cards in the deck."""
    # Implementation for listing cards would go here


@app.command("show")
def show_card(card_id: str) -> None:
    """Show details for a specific card."""
    # Implementation for showing a specific card would go here


@app.command("undo")
def undo() -> None:
    """Undo the last review action."""
    # Implementation for undoing the last review would go here


@app.callback()
def main() -> None:
    """JLPT SRS — a spaced-repetition trainer for JLPT vocabulary."""


if __name__ == "__main__":
    app()
