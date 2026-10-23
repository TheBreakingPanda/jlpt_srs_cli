"""Rich presentation layer for the CLI.

Commands stay thin: they fetch plain data, then hand it to a `render_*` helper
or a message helper here. All formatting - colour, tables, layout - lives in
this module so the command logic stays testable and the look is swappable.

Markup safety: card content (a meaning like "to go [home]") must never be
interpolated into a Rich markup string, or the "[home]" would be parsed as a
style tag. So every value that comes from the deck is wrapped in `Text`, which
Rich renders literally. Only our own fixed labels use markup.
"""

from rich import box
from rich.console import Console, Group, RenderableType
from rich.table import Table
from rich.text import Text

console = Console()


# --- message helpers ---------------------------------------------------------

def success(msg: str) -> None:
    """A green confirmation line (e.g. 'Added USR001.')."""
    console.print(Text(msg), style="bold green")


def error(msg: str) -> None:
    """A red error line (e.g. 'No card with ID X.')."""
    console.print(Text(msg), style="bold red")


def warn(msg: str) -> None:
    """A yellow caution line (e.g. 'Incorrect - try again.')."""
    console.print(Text(msg), style="yellow")


def info(msg: str) -> None:
    """A plain status line."""
    console.print(Text(msg))


def _field(label: str, value: object) -> Text:
    """One 'Label: value' line - label styled, value rendered literally."""
    line = Text()
    line.append(f"{label}: ", style="bold cyan")
    line.append(str(value))
    return line


# --- stats -------------------------------------------------------------------

def render_stats(stats: dict) -> RenderableType:
    """A label -> value metrics table for `jlpt stats`."""
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Total cards", str(stats["total_cards"]))
    table.add_row("Due today", str(stats["due_today"]))
    table.add_row("Reviewed today", str(stats["reviews_today"]))
    table.add_row("Streak", f"{stats['streak']} days")
    table.add_row(
        "Accuracy",
        f"{stats['accuracy']:.0f}% ({stats['total_passes']}/{stats['total_reviews']})",
    )
    return table


# --- list --------------------------------------------------------------------

def render_card_list(rows) -> RenderableType:
    """A table of cards for `jlpt list` (id, kanji, reading, meaning)."""
    table = Table(box=box.SIMPLE_HEAD, header_style="bold")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Kanji")
    table.add_column("Reading", style="magenta")
    table.add_column("Meaning")
    for r in rows:
        # Text() wrappers keep card content from being parsed as Rich markup.
        table.add_row(
            Text(r["card_id"]), Text(r["front"]),
            Text(r["reading"]), Text(r["back"]),
        )
    return table


# --- show --------------------------------------------------------------------

def render_card(row, reviews) -> RenderableType:
    """A card's fields, SRS state, and review history for `jlpt show`."""
    lines = [
        _field("ID", row["card_id"]),
        _field("Source", row["source"]),
        _field("Kanji", row["front"]),
        _field("Reading", row["reading"]),
        _field("Meaning", row["back"]),
        _field(
            "SRS",
            f"ease {row['ease_factor']}, interval {row['interval']}d, "
            f"reps {row['repetitions']}",
        ),
        _field("Due", row["due_date"] or "new (not scheduled)"),
    ]
    if not reviews:
        lines.append(Text("History: no reviews yet.", style="dim"))
    else:
        lines.append(_field("History", f"{len(reviews)} reviews"))
        for r in reviews:
            lines.append(Text(
                f"  {r['reviewed_at']}  grade {r['grade']}  "
                f"-> interval {r['interval_after']}d, ease {r['ease_after']}"
            ))
    return Group(*lines)


# --- help --------------------------------------------------------------------

# Curated so the landing screen reads by purpose, not registration order. If a
# command is added, add its row here too (kept hand-written on purpose - a dump
# of Typer's internals would be less readable than this grouping).
_HELP_GROUPS = [
    ("Study", [
        ("jlpt review", "Quiz the cards that are due (--kana, --new)."),
        ("jlpt stats", "Progress: due, reviewed, streak, accuracy, totals."),
    ]),
    ("Cards", [
        ("jlpt add", "Add a new card by hand."),
        ("jlpt list", "List, search, or filter the deck."),
        ("jlpt show <id>", "One card's content, SRS state, and history."),
        ("jlpt remove <id>", "Delete a card and its review history."),
        ("jlpt undo", "Revert the most recent review."),
    ]),
    ("Data", [
        ("jlpt import <csv>", "Import or sync a Word Bank CSV export."),
    ]),
    ("Help", [
        ("jlpt help", "Show this command reference."),
    ]),
]


def render_help() -> RenderableType:
    """A branded command reference for `jlpt help` (and bare `jlpt`)."""
    title = Text(
        "JLPT SRS — a spaced-repetition trainer for JLPT vocabulary",
        style="bold",
    )
    table = Table(box=box.SIMPLE_HEAD, header_style="bold", pad_edge=False)
    table.add_column("Command", style="bold cyan", no_wrap=True)
    table.add_column("What it does")
    for i, (_section, rows) in enumerate(_HELP_GROUPS):
        if i:
            table.add_section()   # a thin rule between purpose groups
        for command, summary in rows:
            table.add_row(command, summary)
    hint = Text("Run  jlpt COMMAND --help  for a command's options.", style="dim")
    return Group(title, "", table, hint)
