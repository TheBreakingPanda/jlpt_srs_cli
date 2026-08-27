from pathlib import Path

import typer

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

@app.callback()
def main() -> None:
    """JLPT SRS — a spaced-repetition trainer for JLPT vocabulary."""

if __name__ == "__main__":
    app()