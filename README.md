# JLPT SRS

A terminal spaced-repetition trainer for JLPT vocabulary. Import your word list,
review the cards that are due, and let the SM-2 algorithm decide when you see
each word next.

- **Typed answers, automatic grading.** You type the reading and the meaning;
  the grade comes from whether you were right and how many tries it took.
- **One file, no account.** The deck is a single SQLite file on your machine.
- **Your word list stays the source.** Re-importing a CSV updates card content
  without resetting anyone's progress.

Requires **Python 3.12+**.

## Install

With [pipx](https://pipx.pypa.io/), which puts `jlpt` on your PATH in its own
isolated environment:

```bash
pipx install git+https://github.com/TheBreakingPanda/jlpt_srs_cli.git
```

Or from a local clone: `pipx install .` from the project folder.

## Quickstart

```bash
jlpt import word_bank.csv   # load your vocabulary
jlpt review                 # study what's due today
jlpt stats                  # see how it's going
```

The import file is a UTF-8 CSV with this header (`Theme` and `Romaji` are
accepted but not used):

```csv
ID,Theme,Kanji,Reading,Romaji,English
EO001,Everyday Objects,本,ほん,Hon,Book
```

`ID` is the card's permanent identity: import the same file again after editing
it and changed rows are updated in place, with their review progress kept.

## Reviewing

`jlpt review` shows each due card's kanji and asks for its reading, then its
meaning. You get one retry per answer.

| Result | Grade | Effect |
| --- | --- | --- |
| Right first time | 5 | Next gap grows (1 day, 6 days, then x ease); ease rises |
| Right after a retry | 3 | Next gap grows the same way; ease drops, so later gaps grow slower |
| Wrong after the retry | 1 | Card starts over: due again tomorrow, ease unchanged |

`jlpt review --kana` shows the reading instead and asks only for the meaning -
useful while you're still learning the kanji. Each session also introduces up
to 25 never-seen cards (change it with `--new N` or in the config file).

Graded the wrong way? `jlpt undo` reverts the most recent review.

## Commands

| Command | What it does |
| --- | --- |
| `jlpt import [CSV] [--source TAG]` | Import or re-sync a word list |
| `jlpt review [--kana] [--new N]` | Quiz the cards that are due |
| `jlpt stats` | Due today, reviewed today, streak, accuracy, totals |
| `jlpt add` | Add one card by hand (prompts for kanji, reading, meaning) |
| `jlpt list [TEXT] [--due] [--source TAG] [--limit N]` | List, search or filter the deck |
| `jlpt show ID` | One card: content, schedule and review history |
| `jlpt edit ID [--kanji X] [--reading X] [--meaning X]` | Correct a card; its progress is kept |
| `jlpt remove ID` | Delete a card and its history (asks first) |
| `jlpt undo` | Revert the most recent review |
| `jlpt export FILE [--force]` | Back up the deck (see below) |
| `jlpt version` / `jlpt --version` | Print the installed version |
| `jlpt help` / `jlpt` | Show the command reference |

Every command accepts `--help`, and `jlpt --db PATH COMMAND` runs any command
against a different deck.

> **Editing imported cards:** `jlpt edit` changes the deck only. If the card
> came from your CSV, the next import puts the CSV's version back - fix the
> CSV too.

## Where things live

| What | Default location |
| --- | --- |
| Deck (SQLite) | `~/.local/share/jlpt/jlpt.db` |
| Config file | `~/.config/jlpt/config.toml` (created on first run) |

The XDG variables `XDG_DATA_HOME` and `XDG_CONFIG_HOME` move these if set. The
config file has two settings:

```toml
db_path = "/path/to/jlpt.db"   # which deck to use
new_limit = 25                 # new cards per review session
```

Each setting is resolved in this order, first match wins:

1. command-line flag (`--db`, `--new`)
2. environment variable (`JLPT_DB`, `JLPT_NEW_LIMIT`)
3. config file
4. built-in default

## Backups

```bash
jlpt export backup.json   # everything: cards, schedules, full review history
jlpt export cards.csv     # cards and schedules only - opens in a spreadsheet
```

The format follows the file extension. JSON is the complete backup; CSV leaves
out review history, which doesn't fit a single table. Export won't overwrite an
existing file unless you pass `--force`.

## Upgrading an older deck

Decks created before undo existed are upgraded automatically the first time any
command opens them: four columns are added to the review history, and nothing
else is touched. Reviews recorded before the upgrade have no saved "before"
state, so `jlpt undo` refuses to revert those - it works for every review made
afterwards.

## Development

```bash
git clone https://github.com/TheBreakingPanda/jlpt_srs_cli.git
cd jlpt_srs_cli
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest            # test suite; also writes report.html
ruff check .      # lint
```

Project layout: `src/jlpt/` holds the package (`cli.py` is the entry point,
`srs.py` the SM-2 maths, `ui.py` all terminal formatting), `tests/` mirrors it
module by module, and `docs/` has the architecture, command and data-model notes.

## License

[MIT](LICENSE) © 2026 TheBreakingPanda - covering the code and the sample word
list in `data/word_bank.csv`.

