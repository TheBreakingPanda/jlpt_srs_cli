# 💻 JLPT SRS CLI - Languages

> Every language the project uses or plans to use - what it is, what it does here, and why it was chosen. **v1 is pure Python + SQL**; v2 adds others (tentative - see [[JLPT SRS CLI - Project Plan]] › *v2 languages & tech*). Libraries are named where they drove a choice, but this note is about *languages*.

## Status legend

- ✅ **In use** - v1, shipping.
- 🔷 **Planned** - v2, tentative; depends on the Phase 6 framework decision.

---

## In use (v1)

### Python 3.12 ✅

**What it is:** a high-level, general-purpose programming language.
**Used for:** effectively everything in v1 - the `jlpt` CLI, the Word Bank importer, the pure SM-2 scheduler, the review loop and its persistence, and the whole test suite.
**Why chosen:**

- The project's purpose is **learning backend development** (Boot.dev) - Python is the language being learned, so building a real tool in it is the point.
- **Batteries included:** the standard library ships `sqlite3`, so there is no database server or driver to install.
- **Right-shaped ecosystem:** Typer (CLI), Rich (terminal output), and pytest (tests) cover exactly this kind of app.
- Readable and fast to iterate - suits a solo, part-time build.

Pinned to **3.12** for modern typing and stable stdlib behaviour.

### SQL - SQLite dialect ✅

**What it is:** the declarative query language for relational databases; here, the SQLite dialect.
**Used for:** the schema (`cards`, `reviews`), the due-card query, the content-preserving upsert on import, and the stats aggregations.
**Why chosen:**

- The data is naturally **relational** - one card has many reviews - so tables plus a foreign key fit cleanly.
- **SQLite specifically:** serverless, zero-config, single file (`data/jlpt.db`), and reachable straight from Python's stdlib (`sqlite3`) with nothing to install - ideal for a local, single-user tool.
- Keeps SRS state and review history queryable in plain SQL instead of a hand-rolled file format.

Deliberately **not** a client/server database (Postgres, MySQL) in v1: no server to run, no second user - that would be weight without benefit.

### TOML ✅

**What it is:** a minimal, human-readable configuration file format.
**Used for:** `pyproject.toml` - project metadata, dependencies, the `jlpt` entry point, and the `pytest` / `ruff` configuration.
**Why chosen:** it is the **Python packaging standard** (PEP 621); one declarative file configures the build, the console script, and the tooling.

### Markdown ✅

**What it is:** a lightweight markup language for formatted text.
**Used for:** the project documentation - these vault notes, plus the repo's `docs/` and `README.md`.
**Why chosen:** renders everywhere the docs live (Obsidian and GitHub), stays diffable as plain text, and keeps *what and why* beside the code with no heavyweight tooling.

> Shell / Bash is used to *drive* the project (venv, `pytest`, `git`) but as a runner, not project source. It becomes actual project code in v2, below.

---

## Planned (v2, tentative)

> These ride on the **Phase 6 framework decision** (PySide6 + QSS vs a webview shell). Promote each into [[JLPT SRS CLI - Architecture]] once its phase locks it.

### QSS - Qt Style Sheets 🔷 *(Phase 6, if PySide6)*

**What it is:** Qt's CSS-like language for styling widgets.
**Used for:** the desktop GUI's custom theme - colours, typography, spacing.
**Why chosen (leading option):** if the GUI is built on **PySide6**, QSS is the native route to the custom, styled look the v2 goal calls for, in CSS-like syntax already familiar from the web - and it keeps the app pure-Python-plus-stylesheet with no web layer.
**Alternative:** **HTML / CSS / JS** if a webview shell (e.g. pywebview) is chosen instead - same styling goal, authored in literal web languages.

### Markdown / HTML 🔷 *(Phase 7)*

**Used for:** the in-app tutorial / help page - how to use each function, how to build your own Word Bank, and the required fields.
**Why chosen:** help content is text-first; Markdown (or light HTML) authors it cleanly and renders in a help pane without a bespoke format.

### Installer scripting - Inno Setup (`.iss`) or NSIS (`.nsi`) 🔷 *(Phase 8, Windows)*

**What it is:** dedicated scripting languages for building Windows installers.
**Used for:** turning the frozen app into a shareable Windows `.exe` installer - install location, shortcuts, per-user data, uninstall.
**Why chosen:** the standard, well-documented Windows-installer tools; a small script yields the double-click install a non-technical user expects.

### Shell / Bash 🔷 *(Phase 8, Linux + build)*

**Used for:** Linux packaging and build glue - driving the freeze, assembling AppImage / `.deb`, and connecting the steps.
**Why chosen:** the lingua franca of Linux build and packaging pipelines; every tool in that chain speaks it.

### Packaging manifests - YAML / JSON + Debian `control` 🔷 *(Phase 8, Linux)*

**Used for:** declaring the Linux packages - AppImage / Flatpak manifests (YAML / JSON) and `.deb` metadata (Debian `control` files).
**Why chosen:** each Linux packaging format is defined declaratively in its own manifest; these are simply the required inputs.

### Make - Makefile 🔷 *(Phase 8, build)*

**Used for:** a single command to freeze the app and build each installer, so releases are repeatable.
**Why chosen:** a tiny, ubiquitous task runner - captures the multi-step build without a heavier tool.

> If the build is later automated, GitHub Actions **YAML** joins here as CI configuration.

---

## At a glance

| Language | Status | Role in the project |
| --- | --- | --- |
| Python 3.12 | ✅ v1 | Core - CLI, importer, SRS engine, review loop, tests |
| SQL (SQLite) | ✅ v1 | Schema, due query, upsert, stats |
| TOML | ✅ v1 | `pyproject.toml` config |
| Markdown | ✅ v1 | Docs, README |
| QSS *(or HTML/CSS/JS)* | 🔷 v2 · P6 | GUI theming |
| Markdown / HTML | 🔷 v2 · P7 | In-app help page |
| Inno Setup / NSIS | 🔷 v2 · P8 | Windows installer |
| Shell / Bash | 🔷 v2 · P8 | Linux packaging, build glue |
| YAML / JSON, Debian `control` | 🔷 v2 · P8 | Linux package manifests |
| Make | 🔷 v2 · P8 | Build automation |

## See Also
- [[JLPT SRS CLI - MOC]] · [[JLPT SRS CLI - Project Plan]] · [[JLPT SRS CLI - Architecture]]
