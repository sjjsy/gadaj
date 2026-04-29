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
