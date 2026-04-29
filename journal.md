# gadaj Development Journal

Narrative log of reasoning and session context. Reverse-chronological order.

Active work and specs live in `wip.md`. After a work session, and/or
completion of a major task, summarize decisions and the work done here,
update `design.md` if structural and `README.md` when relevant, and
flush `wip.md`.

## Entry requirements

- Title: YYYY-MM-DD HH:mm — Descriptive summary of topics, changes and impacts
- Content: Focus on *why* decisions were made since the actual changes can always be found with git. Omit ephemeral chatter.
- Closing: Every entry must end with Commits and Stats tables

---

## 2026-04-29 18:30 — Inverted commits flag, per-author colors, and v0.2.0

Three usability improvements for the v0.2.0 release, ready for beta testing on PyPI.

### Key decisions

**Commits table as default.** The `--commits` flag was inverted: commits table now shown
by default, hidden with `--no-commits` / `-c`. Rationale: commits are the most frequently
wanted output (developers care about what changed). Making them opt-out (default=True) reduces
friction and aligns with user expectations. The flag still uses `-c` for short form (muscle
memory from the old inverted semantics).

**Per-author color palette.** Authors in the commits table now get assigned distinct colors
from a configurable palette. Default palette has 8 dark ANSI colors ordered as complementary
pairs (green/red, cyan/magenta, yellow/blue, orange/violet) to maximize perceptual distance
when only 2–4 authors are present. Colors assigned in order of first appearance across
commits. Non-configurable until palette is exhausted (unlikely with < 10 authors).

**Palette configuration via TOML.** Added `[colors]` section to config with `author_palette`
setting. Accepts both standard ANSI codes (32 = green) and 256-color codes (130 = dark orange).
Integer → escape-sequence conversion happens in `_apply_toml()`. Default palette (8 colors)
used if section omitted. This allows teams with strong color-blindness accessibility needs
or custom branding to override globally via `~/.config/gadaj/config.toml`.

**Code infrastructure:** Added `_Colors.apply_code(text, code)` method to wrap text in
arbitrary ANSI codes. Enables flexible author coloring without hardcoding specific color
methods. Coloring is disabled when output is piped (follows Unix conventions).

### What was built

- Inverted `--commits` / `--no-commits` flag in CLI (action=store_false, default=True)
- Added `_DEFAULT_AUTHOR_COLORS` (8-color palette) to config.py
- Extended `Config` dataclass with `author_colors: list[str]` field
- Extended `_apply_toml()` to parse `[colors]` TOML section (integer + string codes)
- Added `apply_code()` method to `_Colors` class
- Added `author_colors` parameter to `MarkdownReporter`
- Implemented per-commit author → color mapping in `_commits_table()`
- Updated README: inverted flag docs, added [thresholds] and expanded [colors] sections
- Added comprehensive CHANGELOG entry for 0.2.0
- Updated design.md version and config examples
- 7 new tests (3 config, 4 reporter) validating color parsing and application

### Testing

- All 158 tests pass (151 → 158 +7)
- Verified: commits table shown by default without flags
- Verified: `gadaj -c` / `--no-commits` hides commits table
- Verified: distinct authors get different colors in terminal output
- Verified: TOML color parsing handles integer and string codes
- Verified: piped output (no TTY) has no ANSI codes

### Commits

| Hash | Datetime | Author | Message |
|---|---|---|---|
| `54519cf` | 2026-04-29 18:30 | Samuel | Implement --no-commits flag, author colors, and v0.2.0 |

### Stats

| Item | Details |
|---|---|
| Commits | 1 |
| Files | 9 changed, +184 / -7 |
| Test count | 151 → 158 (+7) |
| claude-haiku-4-5-20251001 | ~$0.40 (implementation) |
| claude-sonnet-4-6 | ~$1.60 (documentation) |
| **Total** | **~$2.00** |

---

## 2026-04-29 17:10 — Commits table refinement and total row format

Four UX refinements to the commits table and summary row.

### Key decisions

**Dynamic "Time" vs "Datetime" header.** When a time window spans a single calendar day
(same_date=true), showing "Datetime" with full `YYYY-MM-DD HH:MM` format is redundant.
Changed header to "Time" (showing just `HH:MM`) for brevity. Multi-day windows keep
"Datetime" for clarity.

**Commits table respects -m flag.** Previously, the commits table always rendered in
Markdown pipe format regardless of the --markdown flag. Now it respects `markdown_tables`:
lightweight mode (default) renders space-aligned columns; -m flag renders pipe tables.
Consistent with other sections.

**Per-commit file stats in table.** Each commit row now includes a "Files" column showing
`N · +X / -Y` (files changed, insertions, deletions), matching the git overview Files row
format. Gives context at a glance for the significance of each commit.

**Total row format consistency.** Changed Total row from "~Xh  ~$Y.YY" (duration before
cost) to "~$Y.YY over ~Xh" (cost before duration), matching the CC row format and
establishing a consistent "metric over duration" pattern in the summary.

### What was built

- Refined `_commits_table()`: dynamic header, markdown respect, files column
- Updated `_summary_section()`: total row now "cost over duration"
- 5 new tests for commits table variants and total row format

### Testing

- All 149 tests pass (144 → 149 +5)
- Verified: same-day windows show "Time" header in pipe format
- Verified: multi-day windows show "Datetime" header
- Verified: lightweight mode shows space-aligned table; -m shows pipes
- Verified: files column displays per-commit stats
- Verified: total row shows "cost over duration"

### Commits

| Hash | Datetime | Author | Message |
|---|---|---|---|
| `976bb37` | 2026-04-29 17:10 | Samuel | Refine commits table and total row format |

### Stats

| Item | Details |
|---|---|
| Commits | 1 |
| Files | 3 changed, +90 / -10 |
| Test count | 144 → 149 (+5) |
| claude-haiku-4-5-20251001 | ~$1.20 (this session) |
| **Total** | **~$1.20** |

---

## 2026-04-29 13:20 — Git overview table, blue digits, darker colors, summary overhaul

Four quality-of-life improvements to visual output and information density.

### Key decisions

**Consistent column width enforcement in Markdown mode.** The Markdown separator row
enforced min-width-3 dashes (standard Markdown requirement), but header and data rows
used the actual column width. For a column like `#` (1 char), this created visible
misalignment: `| # |` vs `| --- |`. Fixed by enforcing min-width-3 globally in
Markdown mode so all rows (header, separator, data) use consistent widths.

**Blue digit coloring with ANSI-aware processing.** Most numeric values (commit counts,
file counts, session counts, date/time digits, token counts) now appear in dark blue.
The challenge: some strings already have ANSI coloring (e.g. durations are cyan). A new
`colorize_digits()` method splits text by ANSI codes and only colors uncolored digit
sequences, preserving existing colors. For single-value wrapping, a simpler `nums()`
method wraps text directly in blue.

**Darker warn cost color.** Changed from standard ANSI yellow `\x1b[33m` to 256-color
dark golden amber `\x1b[38;5;136m` for better visual distinction. Below warn stays dim
yellow, warn range becomes darker amber, alert threshold remains red.

**Richer summary rows with time context.** Git row now shows "X commits over ~Yh" (Y =
hours between first and last commit), giving temporal context. CC row reformatted to
"cost over ~Xh from Y sessions" putting cost first, then duration, then session count.
Total row includes session duration before cost, matching the context-first principle.

**Git overview as proper Table.** Converted `_git_section()` to use the Table class
(Field/Value columns) consistent with Summary section. Field labels kept dim-styled for
visual grouping. Markdown mode renders pipe table; lightweight renders space-aligned.

### What was built

- Enhanced `gadaj/table.py`: min-width enforcement in Markdown mode
- Enhanced `gadaj/colors.py`: `nums()` and `colorize_digits()` methods; darker warn
- Refactored `gadaj/reporters/markdown.py`: Git overview as Table; blue coloring
  applied throughout; summary rows reformatted with duration context
- 10 new tests: 5 color tests (nums, colorize_digits, darker warn), 5 reporter tests

### Testing

- All 144 tests pass (134 → 144 +10)
- Verified: sessions table separator aligns perfectly (`| # |`, `| --- |`, `| 1 |`)
- Verified: digits are blue in terminal (TTY); no ANSI in pipe
- Verified: markdown mode has pipe tables; lightweight has space-aligned columns

### Commits

| Hash | Datetime | Author | Message |
|---|---|---|---|
| `495a485` | 2026-04-29 13:20 | Samuel | Add git overview table, blue digit coloring, darker warn color, summary overhaul |

### Stats

| Item | Details |
|---|---|
| Commits | 1 |
| Files | 6 changed, +209 / -30 |
| Test count | 134 → 144 (+10) |
| claude-haiku-4-5-20251001 | ~$2.80 (this session) |
| **Total** | **~$2.80** |

---

## 2026-04-29 12:44 — Table formatter, --markdown flag, and alignment fixes

Comprehensive refactor of the Markdown reporter to use a reliable tabular formatter,
eliminating manual f-string column arithmetic and fixing misalignment issues with long
model names. Introduced --markdown/-m flag for Markdown-formatted output (####
headers, pipe tables) vs lightweight default (══ headers, space-aligned columns).

### Key decisions

**ANSI-aware column width calculation.** Created `gadaj/table.py` with a `Table` class
that computes dynamic column widths while ignoring ANSI escape codes. The `_vlen(s)`
function strips escape codes before measuring string length, and `_pad(s, width, align)`
accounts for invisible characters when padding. This solves the long-model-name overflow
problem without special-casing.

**Two rendering modes in one Table class.** Rather than having separate code paths for
lightweight vs Markdown, the `Table.render(markdown=False)` method switches format:
- Lightweight (default): columns separated by two spaces, separator rows use `─`
- Markdown: pipe table format `| col |` with alignment separators `| --- |`

This keeps the data structure unified and prevents divergence between rendering modes.

**Separator rows via add_separator().** The `Table` class supports explicit separators
via `add_separator()`, which are skipped in Markdown mode (header sep already present)
but rendered as `─` dashes in lightweight mode. This required careful handling in the
render loop to treat `None` row differently from data rows.

**All sections use Table for consistency.** Refactored five methods in `MarkdownReporter`:
- `_git_section()`: key-value table (Commits, Authors, Files)
- `_commits_table()`: pipe table always (readable in terminal)
- `_cc_section()`: sessions table with dynamic #/Range/Notes columns
- `_models_table()`: model usage with right-aligned numeric columns
- `_summary_section()`: source/summary table

Manual f-string arithmetic is eliminated; column widths are computed from data.

**Headers change based on markdown_tables setting.** The `_header()` function now takes
a `markdown_mode` parameter: returns `#### ` in Markdown mode, `══ ` in lightweight.
All call sites updated to pass `self.markdown_tables`.

**Markdown mode via --markdown/-m flag.** New CLI argument `--markdown` sets
`markdown_tables=True` on the reporter, triggering pipe table format and `####` headers.
Default remains lightweight mode for terminal readability and eye-friendly output.

### What was built

- New `gadaj/table.py` (118 lines): `Col` dataclass and `Table` class with ANSI-aware
  column width calculation and dual rendering modes
- Refactored `gadaj/reporters/markdown.py`: all five table-generating methods now use
  `Table` for consistent, overflow-proof formatting
- Added `--markdown/-m` flag in `gadaj/cli.py`
- Comprehensive test suite: 44 new tests across table, color, utils, config, and
  markdown reporter modules (134 total, all passing)

### Testing

- 17 tests for `Table` class: ANSI stripping, padding, markdown/lightweight render,
  separators, max_width truncation, alignment
- 8 tests for `_Colors` class from prior session
- 10 new tests in `test_markdown_reporter.py`: markdown headers, session/models/summary
  tables in both modes, long model name handling
- All 134 tests pass; no breaking changes

### Verification

Ran `gadaj -w 30d` (lightweight) and `gadaj -w 30d -m` (markdown) with live data:
- Long model name `claude-haiku-4-5-20251001` does not shift columns
- Two-space gap visible between Cache↑ and Cache↓ columns in both modes
- Headers switch: `══` to `####`, no trailing `═` padding
- Sessions and models tables render cleanly in both formats
- Pipe table alignment correct in Markdown mode; space alignment correct in lightweight

### Commits

| Hash | Datetime | Author | Message |
|---|---|---|---|
| `f7440ba` | 2026-04-29 12:44 | Samuel | Implement table formatter, --markdown flag, alignment fixes |

### Stats

| Item | Details |
|---|---|
| Commits | 1 |
| Files | 8 changed, +615 / -54 |
| Test count | 124 → 134 (+10 new tests) |
| claude-haiku-4-5-20251001 | ~$2.20 (this session) |
| **Total** | **~$2.20** |

---

## 2026-04-29 12:10 — Datetime consistency, terminal coloring, cost thresholds

Three major improvements to the Markdown reporter for better visual clarity and
terminal experience.

### Key decisions

**Datetime consistency by window scope.** Rather than making each format function
independently decide whether to abbreviate dates, the reporter computes `same_date`
once per render (from `period.since/until` boundaries) and threads it through all
format calls. This keeps the logic centralized and simplifies format functions.

**Duration always shown in ranges.** `fmt_time_range()` and `fmt_session_range()`
now compute and append duration (e.g. `~4.0h`) to their output. Format is
`range_str  duration_str` with two spaces as separator, matching the existing
session line format.

**ANSI coloring without new dependencies.** A new `gadaj/colors.py` module
provides a `_Colors` class with dim(), duration(), and cost() methods. Each
method returns the text wrapped in ANSI escape codes if coloring is enabled, or
plain text otherwise. This avoids a runtime dependency on colorama/rich and keeps
the module testable.

**Auto-detect TTY for coloring.** Coloring is disabled by default and auto-enabled
when `sys.stdout.isatty()` returns True. This preserves plain text when output is
piped, redirected, or logged, following Unix conventions. No new CLI flag needed.

**Summary heading gets time range.** The SUMMARY section now displays the window
range in its header (`══ SUMMARY  YYYY-MM-DD HH:MM – HH:MM EEST  ~Nh ══`) matching
GIT and CC section format. The redundant `Window` line in the body was removed.

**Config-driven cost thresholds.** New `[thresholds]` TOML section allows users to
set `cost_warn` and `cost_alert` boundaries. Costs color from dark-yellow (< warn),
dark-orange (warn ≤ cost < alert), to dark-red (≥ alert). Defaults: $1.00 and $5.00.

### What was built

- New `gadaj/colors.py` with conditional ANSI coloring (no dependencies)
- Updated format functions: `period_same_date()`, `fmt_time_range()`, 
  `fmt_session_range()` now accept `same_date` param and include duration
- Enhanced `MarkdownReporter`: threads `same_date` and color through all sections,
  moves time range to SUMMARY header, removes Window body line
- Extended `Config`: `cost_warn_usd` and `cost_alert_usd` fields with TOML parsing
- `cli.py` now passes `color=sys.stdout.isatty()` and threshold values to reporter

### Testing

- All 90 existing tests pass (no test changes needed — color=False by default)
- Verified same-day formatting: "2026-04-28 13:00 – 17:00 EEST  ~4.0h" + HH:MM sessions
- Verified multi-day formatting: "2026-04-28 23:00 – 2026-04-29 07:00 EEST  ~8.0h"
- Verified color output: dim labels, cyan durations, red/orange/yellow costs by threshold
- No new CLI flags or breaking changes

### Commits

| Hash | Datetime | Author | Message |
|---|---|---|---|
| `68a108d` | 2026-04-29 08:03 | Samuel | Show YYYY-MM-DD dates in ranges when spanning multiple days |
| `6720358` | 2026-04-29 12:04 | Samuel | Add datetime consistency, terminal coloring, cost thresholds |

### Stats

| Item | Details |
|---|---|
| Commits | 2 |
| Files | 5 changed, +144 / -307 |
| claude-haiku-4-5 | ~$2.50 (this session) |
| **Total** | **~$2.50** |

---

## 2026-04-28 21:30 — gadaj v0.1 implementation

Full package implemented from the spec in `wip.md`. The implementation is a
refactor of `journal_facility.py` into a proper installable package.

### Key decisions

**Python 3.8 compatibility** was required (Ubuntu 20.04). The spec assumed Python
3.11+ (`tomllib`). Solution: `tomli` as a conditional dependency for Python < 3.11,
same interface. `requires-python` lowered to `>=3.8`. All `X | Y` union type hints
work via `from __future__ import annotations` (lazy evaluation).

**Unix timestamps (`%at`) for git dates.** The original spec used
`--date=format:%Y-%m-%d %H:%M` which produces local time, causing off-by-timezone
bugs when the tool runs with a different UTC offset than the commit author. `%at`
is always UTC-epoch and portable.

**UTC suffix on `--after`/`--before` args.** Without `+00:00`, git interprets the
datetime as local time. This caused commits to be silently excluded when querying
by time window — the most important core feature. Fixed by appending explicit UTC
offset.

**`fmt_time_range` helper.** The original design formatted the since and until
times separately, putting the timezone label in the middle (`10:00 EEST – 13:25`).
Added a unified `fmt_time_range(since, until, tz_offset)` function that produces
the expected `10:00 – 13:25 EEST` format with the label at the end.

**Per-commit stats via `--stat`.** Rather than running a separate `git diff --stat`
for the whole range, each commit carries its own stats from the `--stat` output.
This enables richer JSON output and correct `WorkPeriod` totals by summation.

**`journal_facility.py` removed.** The spec called for a deprecation shim in v0.1
and removal in v0.2. Given the user explicitly requested removal as part of this
session, it was deleted directly. The git history preserves the original logic.

### What was built

- Full `gadaj` package (10 source files, ~700 lines)
- 90 tests, all passing (pytest on Python 3.8.10)
- Installed as `gadaj` CLI: detects current CC session and git commits, formats output
- Output verified: markdown sections, JSON schema with `summary` first, UTC-correct datetimes

### Commits

| Hash | Datetime | Author | Message |
|---|---|---|---|
| `6f3e992` | 2026-04-28 21:15 | Samuel | Capture spec state before v0.1 implementation |
| `d378715` | 2026-04-28 21:29 | Samuel | Implement gadaj v0.1 |

### Stats

| Item | Details |
|---|---|
| Commits | 2 |
| Files | 28 changed, +2670 / -1 |
| claude-sonnet-4-6 | ~$7.08 (this session) |
| **Total** | **~$7.08** |
