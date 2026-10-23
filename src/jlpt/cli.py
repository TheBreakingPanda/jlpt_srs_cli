from datetime import date
from pathlib import Path

import typer

from jlpt import quiz
from jlpt.review import DEFAULT_NEW_LIMIT, apply_review, due_cards
from jlpt import stats as stats_report   # aliased to avoid clashing with the stats command
from jlpt import ui

from .db import init_db
from .importer import import_csv

app = typer.Typer(help="JLPT SRS — a spaced-repetition trainer for JLPT vocabulary.")


# --- interactive quiz helpers ------------------------------------------------

def _ask_part(label, check, expected) -> tuple[bool, bool]:
    """Ask one part (reading or meaning), allowing one retry.

    `check` is quiz.check_reading or quiz.check_meaning; `expected` is the
    card's value to check against. Return (passed, used_retry).
    """
    typed = typer.prompt(f"{label}?")
    if check(expected, typed):
        return True, False

    ui.warn("Incorrect — try again.")
    typed = typer.prompt(f"{label}? (retry)")
    passed = check(expected, typed)
    if not passed:
        ui.info(f"The answer was: {expected}")
    return passed, True


def _quiz_card(card, kana_mode) -> int:
    """Show one card, quiz the required parts, return an SM-2 grade."""
    if kana_mode:
        ui.info(f"Reading: {card['reading']}")
        passed, used_retry = _ask_part("Meaning", quiz.check_meaning, card["back"])
    else:
        ui.info(f"Kanji: {card['front']}")
        passed, used_retry = _ask_part("Reading", quiz.check_reading, card["reading"])
        if passed:
            passed, retried = _ask_part("Meaning", quiz.check_meaning, card["back"])
            used_retry = used_retry or retried

    attempts = 2 if used_retry else 1
    grade = quiz.grade_from_attempts(attempts, passed)
    ui.console.print(f"[bold]Grade: {grade}[/bold]")
    return grade


# --- import ------------------------------------------------------------------

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
        ui.success(f"Imported {new + updated} cards ({new} new, {updated} updated).")
    finally:
        conn.close()


# --- review ------------------------------------------------------------------

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
            ui.info("Nothing's due today.")
            return

        reviewed = 0
        for card in cards:
            grade = _quiz_card(card, kana_mode=kana)
            apply_review(conn, card["card_id"], grade, today)
            reviewed += 1

        ui.success(f"Reviewed {reviewed} card(s).")
    finally:
        conn.close()


# --- add ---------------------------------------------------------------------

@app.command("add")
def add() -> None:
    """Add a new card to the deck."""
    front = typer.prompt("Kanji")
    reading = typer.prompt("Reading (kana)")
    back = typer.prompt("Meaning (English)")
    conn = init_db()
    try:
        # Mint the next USR id from the highest existing one (MAX + 1), so a
        # removed card never causes a later collision the way a count would.
        row = conn.execute(
            "SELECT card_id FROM cards WHERE card_id LIKE 'USR%' "
            "ORDER BY card_id DESC LIMIT 1"
        ).fetchone()
        next_num = int(row["card_id"][3:]) + 1 if row else 1
        card_id = f"USR{next_num:03d}"

        conn.execute(
            "INSERT INTO cards (card_id, source, front, back, reading) "
            "VALUES (?, 'user', ?, ?, ?)",
            (card_id, front, back, reading),
        )
        conn.commit()
        ui.success(f"Added {card_id}.")
    finally:
        conn.close()


# --- remove ------------------------------------------------------------------

@app.command("remove")
def remove(card_id: str) -> None:
    """Remove a card (and its review history) from the deck."""
    conn = init_db()
    try:
        exists = conn.execute(
            "SELECT 1 FROM cards WHERE card_id = ?", (card_id,)
        ).fetchone()
        if exists is None:
            ui.error(f"No card with ID {card_id}.")
            raise typer.Exit(code=1)

        typer.confirm(f"Delete {card_id} and its review history?", abort=True)

        # Delete the reviews first, then the card, in one transaction - the FK
        # from reviews.card_id would otherwise block deleting a reviewed card.
        with conn:
            conn.execute("DELETE FROM reviews WHERE card_id = ?", (card_id,))
            conn.execute("DELETE FROM cards WHERE card_id = ?", (card_id,))
        ui.success(f"Removed {card_id}.")
    finally:
        conn.close()


# --- stats ------------------------------------------------------------------

@app.command("stats")
def stats() -> None:
    """Display statistics about the deck."""
    conn = init_db()
    try:
        s = stats_report.gather_stats(conn, date.today())
        ui.console.print(ui.render_stats(s))
    finally:
        conn.close()


# --- list ------------------------------------------------------------------

@app.command("list")
def list_cards(
    query: str = typer.Argument(
        None, help="Filter by text in the front / reading / back."),
    source: str = typer.Option(
        None, "--source", help="Only cards from this source (e.g. user, word_bank)."),
    due: bool = typer.Option(
        False, "--due", help="Only cards that are due for review."),
    limit: int = typer.Option(
        0, "--limit", help="Max cards to show (0 = all)."),
) -> None:
    """List cards in the deck, optionally filtered."""
    conn = init_db()
    try:
        conditions: list[str] = []
        params: list = []

        if source is not None:
            conditions.append("source = ?")
            params.append(source)
        if due:
            conditions.append("due_date IS NOT NULL AND due_date <= ?")
            params.append(date.today().isoformat())
        if query:
            conditions.append("(front LIKE ? OR reading LIKE ? OR back LIKE ?)")
            like = f"%{query}%"
            params += [like, like, like]

        sql = "SELECT card_id, front, reading, back FROM cards"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY card_id"
        if limit > 0:
            sql += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        if not rows:
            ui.info("No cards match." if conditions else "No cards in the deck.")
            return

        ui.console.print(ui.render_card_list(rows))
    finally:
        conn.close()


# --- show ------------------------------------------------------------------

@app.command("show")
def show_card(card_id: str) -> None:
    """Show details for a specific card."""
    conn = init_db()
    try:
        row = conn.execute(
            "SELECT card_id, source, front, reading, back, "
            "ease_factor, interval, repetitions, due_date "
            "FROM cards WHERE card_id = ?",
            (card_id,),
        ).fetchone()
        if row is None:
            ui.error(f"No card with ID {card_id}.")
            raise typer.Exit(code=1)

        reviews = conn.execute(
            "SELECT reviewed_at, grade, interval_after, ease_after "
            "FROM reviews WHERE card_id = ? ORDER BY reviewed_at",
            (card_id,),
        ).fetchall()
        ui.console.print(ui.render_card(row, reviews))
    finally:
        conn.close()


# --- undo ------------------------------------------------------------------

@app.command("undo")
def undo() -> None:
    """Undo the most recent review, restoring the card's prior state."""
    conn = init_db()
    try:
        last = conn.execute(
            "SELECT * FROM reviews ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if last is None:
            ui.info("Nothing to undo.")
            return

        # Restore the card to the snapshot taken before that review, then delete
        # the review row - both in one transaction so they can't desync.
        with conn:
            conn.execute(
                """
                UPDATE cards
                SET ease_factor = ?, interval = ?, repetitions = ?, due_date = ?
                WHERE card_id = ?
                """,
                (
                    last["ease_before"], last["interval_before"],
                    last["repetitions_before"], last["due_before"],
                    last["card_id"],
                ),
            )
            conn.execute("DELETE FROM reviews WHERE id = ?", (last["id"],))

        due = last["due_before"] or "new (not scheduled)"
        ui.success(
            f"Undid review of {last['card_id']} (grade {last['grade']}) — "
            f"restored interval {last['interval_before']}, due {due}."
        )
    finally:
        conn.close()


# --- help --------------------------------------------------------------------

@app.command("help")
def help_() -> None:
    """Show the command reference."""
    ui.console.print(ui.render_help())


# --- entry point -------------------------------------------------------------

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """JLPT SRS — a spaced-repetition trainer for JLPT vocabulary."""
    # Bare `jlpt` (no subcommand) lands on the styled reference instead of a
    # terse "Missing command" usage error.
    if ctx.invoked_subcommand is None:
        ui.console.print(ui.render_help())


if __name__ == "__main__":
    app()
