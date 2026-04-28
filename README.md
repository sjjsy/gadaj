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
══ GIT  2026-04-28 10:00 – 13:25 EEST ════════════════════════════

  Commits   8 · 51d38b6 – e60d59b
  Authors   Samuel (8)
  Files     7 changed · +672 / -7

══ CLAUDE CODE  2026-04-28 10:00 – 13:25 EEST ════════════════════

  Sessions  2 in window

  Session 1  10:02 – 11:47  ~1.7h
  Session 2  12:10 – 13:24  ~1.2h   ← most recent

  Model                In     Out    Cache↑   Cache↓    Cost
  claude-sonnet-4-6   180k   174k    293k     9.6M    ~$6.59
  ──────────────────────────────────────────────────────────
  2 sessions total                                    ~$6.59

══ SUMMARY ════════════════════════════════════════════════════════

  Window    ~3.4h  (2026-04-28 10:00 – 13:25 EEST)
  Git       8 commits · Samuel
  CC        2 sessions · claude-sonnet-4-6 · ~$6.59
  Total                                              ~$6.59
```

---

## Why gadaj?

Most teams using AI coding agents quickly notice a gap: the agent produces
work, but there is no easy way to see what happened across a session, who
contributed what, or what it cost — especially when a human and one or more
agents are working in parallel or in sequence on the same repo.

Existing tools solve only half the problem. CC session analyzers (ccusage,
claude-monitor, ccstats) track token consumption and cost but know nothing
about git. Git analytics tools (git-quick-stats, gitinspector) know commits
intimately but have no awareness of AI agents or session cost. No tool
combines both into a time-windowed, multi-contributor work log.

`gadaj` fills that gap. It is not a task tracker, narrative generator, or
project manager. It collects evidence and presents it clearly. You decide
what story to tell.

**On the name:** like `grep` or `awk`, `gadaj` is a proper noun that earns
independence from its expansion. The acronym is a mnemonic, not a contract —
as the tool grows to cover more sources, the name stays. Zero collisions on
PyPI and GitHub at time of writing.

---

## Install

```bash
pip install gadaj
```

Requires Python 3.11+. No runtime dependencies — stdlib only.

---

## Quickstart

```bash
# Summarise the last 4 hours (default)
gadaj

# Everything since yesterday morning, with full commit table
gadaj -s yesterday -c

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
| `--since DATETIME` | `-s` | — | Window start. ISO date/datetime, `"yesterday"`, `"today"`, `"N hours ago"` |
| `--until DATETIME` | `-u` | now | Window end |

`--window` and `--since` are mutually exclusive.

### Git options

| Flag | Short | Description |
|---|---|---|
| `--git-range A..B` | `-g` | Explicit hash range, overrides time window for git |
| `--git-last N` | | Last N commits, ignoring time window |
| `--git-author NAME` | `-a` | Filter commits to this author (nick or full name) |
| `--git-filter PATTERN` | `-f` | Filter by commit message or changed path (case-insensitive) |
| `--no-git` | | Exclude git section |

### Claude Code options

| Flag | Short | Description |
|---|---|---|
| `--cc-file PATH` | | Use a specific `.jsonl` instead of scanning by time |
| `--no-cc` | | Exclude Claude Code section |

### Output options

| Flag | Short | Description |
|---|---|---|
| `--commits` | `-c` | Full commits table (default: summary row only) |
| `--json` | `-j` | Machine-readable JSON |
| `--out FILE` | `-o` | Write to file instead of stdout |
| `--raw` | `-R` | Raw token counts (debug) |
| `--tz HOURS` | `-z` | UTC offset override (default: auto-detected) |

### Examples

```bash
# Only git, last 12 commits
gadaj --git-last 12 --no-cc -c

# Only CC sessions from the last 2 days
gadaj -s "2 days ago" --no-git

# Filter to commits touching a specific area
gadaj -w 1d -f "software-factory" -c

# One author's commits this week
gadaj -s monday -a Samuel --no-cc -c

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
"claude-sonnet-4-6"         = [3.00, 15.00, 3.75, 0.300]
"claude-opus-4-6"           = [15.00, 75.00, 18.75, 1.500]
"claude-haiku-4-5-20251001" = [0.80, 4.00, 1.00, 0.080]

[defaults]
window = "4h"
tz     = "auto"   # or e.g. "+2", "+3"
```

Update `[pricing]` when Anthropic changes rates. Update `[authors]` when your
team changes. Neither requires touching the package itself.

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

Sessions with a gap of more than 30 minutes between them are flagged in output.
Parallel sessions (overlapping timestamps, e.g. two agents running at the same
time) are labelled `[parallel]`.

If you want to analyse a session from a different project, use `--cc-file PATH`
to point directly at a `.jsonl` file.

---

## Relation to existing tools

`gadaj` is not a replacement for ccusage, claude-monitor, or similar tools.
Those are real-time consumption monitors useful for staying within plan limits.
`gadaj` is a retrospective aggregator useful for recording what happened.
They answer different questions and complement each other.

| Tool | Question answered |
|---|---|
| ccusage, claude-monitor | Am I about to hit my token limit? |
| git-quick-stats | How active is this repo over time? |
| **gadaj** | What did our team (human + AI) actually do in this window? |

---

## Adding a new source

`gadaj` uses a simple collector protocol. To add support for Aider,
OpenRouter, Toggl, or any other source:

1. Create `gadaj/collectors/<name>.py`
2. Subclass `Collector` and implement two things:

```python
from gadaj.collectors.base import Collector
from gadaj.models import ...   # use an existing type or add a new one

class AiderCollector(Collector):

    @property
    def source_name(self) -> str:
        return "Aider"

    def collect(self, since: datetime, until: datetime) -> list:
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
git clone https://github.com/<you>/gadaj
cd gadaj
pip install -e ".[dev]"
pytest
pytest --cov=gadaj --cov-report=term-missing
```

`gadaj` has no runtime dependencies. Dev dependencies are `pytest` and
`pytest-cov` only.

For architecture, data models, testing strategy, and migration notes from
`journal_facility.py`, see [`design.md`](design.md).

---

## Migrating from journal_facility.py

If you have been using `journal_facility.py` directly, `gadaj` is its
structured replacement. The same logic is preserved — JSONL parsing, cost
calculation, git helpers, and formatting — reorganised into a proper package.

The old script will print a deprecation warning and forward to `gadaj` during
the v0.1 transition period. It will be removed in v0.2.

The main behavioural difference: `gadaj` scans **all** CC sessions in the time
window rather than defaulting to the single most recent `.jsonl` file. Use
`--cc-file` if you want the old single-file behaviour.

---

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md).

---

## License

MIT
