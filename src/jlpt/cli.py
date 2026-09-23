from pathlib import Path
from datetime import date

import typer

from jlpt.review import apply_review, due_cards
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


def _read_grade() -> int:
    """Prompt for an SM-2 grade, reprompting until it is an int in 0..5."""
    while True:
        grade = typer.prompt("Grade (0-5)", type=int)
        if 0 <= grade <= 5:
            return grade
        typer.echo("Grade must be between 0 and 5.")


def _wait_for_reveal() -> None:
    """Pause until the user presses Enter (typer has no `pause`)."""
    typer.prompt(
        "Press Enter to reveal the answer",
        default="",
        show_default=False,
        prompt_suffix="",
    )


@app.command("review")
def review() -> None:
    """Start a review session for the user to practice their cards."""
    conn = init_db()
    try:
        today = date.today()
        cards = due_cards(conn, today)
        if not cards:
            typer.echo("Nothing's due today.")
            return

        reviewed = 0
        for card in cards:
            typer.echo(str(card["front"]))
            _wait_for_reveal()
            typer.echo(f"Reading: {card['reading']}")
            typer.echo(f"Back: {card['back']}")
            grade = _read_grade()
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
def show_card(card_id: int) -> None:
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
