# gadaj

**Git and AI Data Aggregator for Journaling**

`gadaj` aggregates git commit history and AI coding-agent session data into a
time-windowed work log. Give it a window — `gadaj -w 4h`, `gadaj -s yesterday`
— and it tells you what changed in the repo, which AI models were used, by whom,
for how long, and at what cost. The output is ready to paste into a journal entry
or hand to an AI for narrative drafting.

Built for small human+AI teams where Claude Code, Aider, or similar agents work
alongside humans on the same codebase. `gadaj` is the missing link between raw
session transcripts and a coherent record of the day's work.

```
══ GIT  2026-04-28 10:00 – 13:25 EEST ════════════════════════════════

  Commits   8 · 51d38b6 – e60d59b
  Authors   Samuel (7), Mikko (1)
  Files     7 changed · +672 / -7

  Hash       Time   Author  Files          Message
  `51d38b6`  10:02  Samuel  3 · +95 / -8   Implement feature X
  `8a2c1d9`  10:15  Samuel  1 · +12 / -0   Fix typo
  `e60d59b`  13:15  Mikko   3 · +565 / -5  Refactor component Y
  (5 more commits...)

══ CLAUDE CODE  2026-04-28 10:00 – 13:25 EEST ════════════════════════

  Sessions  2 in window

  Session 1  10:02 – 11:47  ~1.7h
  Session 2  12:10 – 13:24  ~1.2h   ← most recent

  Model                      In    Out   Cache↑  Cache↓    Cost
  claude-haiku-4-5-20251001  200k  283k    1.4M   60.7M  ~$7.39
  claude-sonnet-4-6          180k  174k    293k    9.6M  ~$6.59
  ──────────────────────────────────────────────────────────────────
  2 sessions total                                      ~$13.98

══ SUMMARY ═══════════════════════════════════════════════════════════

  Source  Summary
  Git     8 commits over ~3.1h · Samuel, Mikko
  CC      ~$13.98 over ~2.9h from 2 sessions
  Total   ~$13.98 over ~2.9h
```

---

## Why gadaj?

A new category of small human+AI teams has emerged — 2–5 people working alongside
Claude Code, Aider, or other coding agents on the same codebase simultaneously or
in sequence. These teams quickly notice a gap: the agent produces work, but there
is no easy way to see what happened across a session, who contributed what, or
what it cost — especially when a human and one or more agents are working in
parallel or in sequence on the same repo.

**Existing tools cover only half the picture:**

CC session analytics tools (**ccusage**, **claude-monitor**, **ccstats**,
**claude-token-analyzer**) are purely consumption-focused — tokens in, dollars
out, plan limits. They have no awareness of git history and no concept of a
"work period" that spans multiple sessions or contributors.

Git analytics tools (**git-quick-stats**, **gitinspector**, **git-dev-time**,
**git-journal**) know commits intimately but have zero awareness of AI agents,
session costs, or model usage.

AI commit/report tools (**commitloom**, **ai-git-cli**, **wsr**) generate text
from git history but don't aggregate multi-source activity data.

The closest adjacent project is **git-ai** (git-ai-project), which tracks AI
attribution at the line level — but it solves code provenance and review, not
work logging.

**The gap:** no tool combines git history + AI session data + multi-contributor
time-windowed aggregation into a work log oriented toward human-readable output.
`gadaj` fills this gap. It is not a task tracker, narrative generator, or project
manager. It collects evidence and presents it clearly. You decide what story
to tell.

| Tool | Question answered |
|---|---|
| ccusage, claude-monitor | Am I about to hit my token limit? |
| git-quick-stats, gitinspector | How active is this repo over time? |
| **gadaj** | What did our team (human + AI) actually do in this window? |

**On the name:** like `grep` or `awk`, `gadaj` is a proper noun that earns
independence from its expansion. The acronym is a mnemonic, not a contract —
as the tool grows to cover more sources, the name stays. Zero collisions on
PyPI and GitHub at time of writing.

---

## Install

```bash
pip install gadaj
```

Requires Python 3.8+. Depends only on `tomli` (automatically installed for
Python < 3.11; stdlib `tomllib` is used on Python 3.11+).

---

## Quickstart

```bash
# Summarise the last 4 hours (default, with commits table)
gadaj

# Everything since yesterday morning (commits shown by default)
gadaj -s yesterday

# Hide the commits table, show summary only
gadaj -c

# JSON output for an AI agent to draft a journal entry from
gadaj -w 8h --json
```

---

## Usage

```
gadaj [options]
```

### Time window

All sources are queried against a single time window. These flags control it.

| Flag | Short | Default | Description |
|---|---|---|---|
| `--window DURATION` | `-w` | `4h` | Look back from now: `2h`, `1.5d`, `90m` |
| `--since DATETIME` | `-s` | — | Window start. ISO date/datetime, `"yesterday"`, `"today"`, `"N hours ago"`, weekday name |
| `--until DATETIME` | `-u` | now | Window end |

`--window` and `--since` are mutually exclusive.

### Git options

| Flag | Short | Description |
|---|---|---|
| `--git-range A..B` | `-g` | Explicit hash range, overrides time window for git |
| `--git-last N` | | Last N commits, ignoring time window |
| `--git-author NAME` | `-a` | Filter commits to this author (substring match) |
| `--git-filter PATTERN` | `-f` | Filter by commit message (case-insensitive) |
| `--no-git` | | Exclude git section |

### Claude Code options

| Flag | Short | Description |
|---|---|---|
| `--cc-file PATH` | | Use a specific `.jsonl` instead of scanning by time |
| `--no-cc` | | Exclude Claude Code section |

### Output options

| Flag | Short | Description |
|---|---|---|
| `--no-commits` | `-c` | Hide the full commits table (shown by default) |
| `--json` | `-j` | Machine-readable JSON |
| `--out FILE` | `-o` | Write to file instead of stdout |
| `--raw` | `-R` | Raw token counts (debug) |
| `--tz HOURS` | `-z` | UTC offset override, e.g. `3`, `+2`, `-5`, or `auto` |

### Examples

```bash
# Only git, last 12 commits
gadaj --git-last 12 --no-cc

# Only CC sessions from the last 2 days
gadaj -s "2 days ago" --no-git

# Filter to commits touching a specific area
gadaj -w 1d -f "software-factory"

# One author's commits this week
gadaj -s monday -a Samuel --no-cc

# Pipe JSON to another tool
gadaj -w 8h --json | jq '.summary'
```

---

## Configuration

`gadaj` reads config from `~/.config/gadaj/config.toml`, created with defaults
on first run. To override for a specific repo, add `.gadaj.toml` at the repo root.

```toml
[authors]
"Your Full Name"  = "YourNick"
"Collaborator"    = "Nick"

[pricing]
# (input, output, cache_write, cache_read) — $/MTok
"claude-opus-4-7"           = [15.00, 75.00, 18.75,  1.500]
"claude-opus-4-6"           = [15.00, 75.00, 18.75,  1.500]
"claude-sonnet-4-6"         = [ 3.00, 15.00,  3.75,  0.300]
"claude-haiku-4-5"          = [ 0.80,  4.00,  1.00,  0.080]
"claude-haiku-4-5-20251001" = [ 0.80,  4.00,  1.00,  0.080]

[defaults]
window = "4h"
tz     = "auto"   # or e.g. "2", "3"

[thresholds]
cost_warn  = 1.0   # yellow → orange coloring boundary (USD)
cost_alert = 5.0   # orange → red coloring boundary (USD)

[colors]
# Author color palette for the commits table (ANSI color codes).
# Values are integers (standard or 256-color codes). The default palette
# has 8 colors in complementary pairs: green/red, cyan/magenta,
# yellow/blue, orange/violet.
# author_palette = [32, 31, 36, 35, 33, 34, 130, 93]

[author_colors]
# Explicit author name → ANSI color code mapping for commits table.
# If defined, these colors take precedence over the palette.
# Authors not listed here use palette colors in order of first appearance.
# "Samuel Marisa"     = 32   # green
# "Mikko Lastname"    = 31   # red
```

Update `[pricing]` when Anthropic changes rates. Update `[authors]` when your
team changes. Use `[author_colors]` to pin specific authors to specific colors.
Neither requires touching the package itself.

---

## JSON output

`gadaj --json` emits a stable schema suitable for downstream scripts or AI
agents. The `summary` key is first so an agent can stop reading early if it
only needs the overview.

```json
{
  "summary": {
    "total_cost_usd": 6.59,
    "contributors": [...]
  },
  "window": {
    "since": "2026-04-28T10:00:00+00:00",
    "until": "2026-04-28T13:25:00+00:00",
    "duration_hours": 3.4
  },
  "git": { "commits": [...], "files_changed": 7, ... },
  "cc":  { "sessions": [...], "models": {...}, "total_cost_usd": 6.59 }
}
```

The schema is stable across patch versions. Breaking changes require a minor
version bump. See `design.md §6` for the full schema definition.

---

## How gadaj finds Claude Code sessions

Claude Code writes `.jsonl` session files to `~/.claude/projects/<hashed-path>/`.
`gadaj` hashes the current working directory the same way CC does, scans all
`.jsonl` files in that directory, and includes any whose timestamp range
overlaps the requested window — regardless of how many sessions that covers.

Sessions with a gap of more than 30 minutes between them are flagged in output
(`⚠ Xm gap`). Parallel sessions (overlapping timestamps, e.g. two agents running
at the same time) are labelled `[parallel]`.

If you want to analyse a session from a different project, use `--cc-file PATH`
to point directly at a `.jsonl` file.

---

## Adding a new source

`gadaj` uses a simple collector protocol. To add support for Aider,
OpenRouter, Toggl, or any other source:

1. Create `gadaj/collectors/<name>.py`
2. Subclass `Collector` and implement two things:

```python
from gadaj.collectors.base import Collector

class AiderCollector(Collector):

    @property
    def source_name(self) -> str:
        return "Aider"

    def collect(self, since, until) -> list:
        # Parse Aider's .aider.chat.history.md or similar log file
        # Filter to the given window
        # Return a list of model instances
        ...
```

3. Register it in `cli.py` alongside `GitCollector` and `CCCollector`

No other files need to change. See `design.md §4` for the full protocol
including the `available` property for graceful degradation when a source
is not present.

---

## Development

```bash
git clone https://github.com/sjjsy/gadaj
cd gadaj
pip install -e ".[dev]"
pytest
pytest --cov=gadaj --cov-report=term-missing
```

`gadaj` has one runtime dependency (`tomli`) only on Python < 3.11.
Dev dependencies are `pytest` and `pytest-cov`.

For architecture, data models, testing strategy, and design decisions, see
[`design.md`](design.md).

---

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md).

---

## License

MIT
