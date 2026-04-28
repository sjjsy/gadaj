# wip.md — Work in progress

- Use this for active editing and review of specs, wireframes,
  brainstorming notes and feedback rounds (discussion) for work
  currently in flight.
- Commit the file before starting a review or implementation round to
  capture spec evolution.
- After finishing a significant implementation work, and before ending a
  work session, add a journal entry that summarizes all the work done
  since the previous (=topmost) entry into `journal.md`, before flushing `wip.md`
  clean/empty, and committing these two file updates.
- Annotate review rounds with TODO/FIXME/IDEA/QUESTION to separate
  earlier and newer input

## `gadaj` — Design Spec v1.0 Header

**Package name:** `gadaj`

**Stands for:** Git and AI Data Aggregator for Journaling

**Tagline:** *A CLI tool for human+AI teams to aggregate git history and AI coding-agent sessions into a time-windowed work log — ready to paste into a journal or hand to an AI for narrative drafting.*

**On the name:** `gadaj` was chosen for uniqueness, memorability, and longevity. Like `grep` or `awk`, it is a proper noun that earns independence from its expansion — the acronym is a mnemonic, not a contract. As the tool grows to cover more AI tools and richer output modes, the expansion may stretch slightly, but the name will not need to change. Zero collisions on PyPI and GitHub at time of writing.

---

## Problem and gap

A new category of small human+AI teams has emerged — 2–5 people working alongside Claude Code, Aider, or other coding agents on the same codebase simultaneously or in sequence. These teams need a shared record of what happened: who worked, which AI models were used, what it cost, and what changed in the repo. This record is the basis for journal entries, retrospectives, cost tracking, and onboarding.

**Existing tools cover only half the picture:**

CC session analytics tools (ccusage, claude-monitor, ccstats, claude-token-analyzer) are purely consumption-focused — tokens in, dollars out, plan limits. They have no awareness of git history and no concept of a "work period" that spans multiple sessions or contributors.

Git analytics tools (git-quick-stats, gitinspector, git-dev-time, git-journal) know commits intimately but have zero awareness of AI agents, session costs, or model usage.

AI commit/report tools (commitloom, ai-git-cli, wsr) generate text from git history but don't aggregate multi-source activity data.

The closest adjacent project is `git-ai` (git-ai-project), which tracks AI attribution at the line level — but it solves code provenance and review, not work logging.

**The gap:** no tool combines git history + AI session data + multi-contributor time-windowed aggregation into a work log oriented toward human-readable output. `gadaj` fills this gap.

---

## Goals

- Given a time window, collect all available evidence (git commits, CC sessions, future: other AI tools) and present it clearly, attributed by source, so a human or AI can write a journal entry without hunting for data.
- Support multi-contributor, multi-session, multi-model work periods naturally.
- Be source-explicit: git output and AI session output are never silently merged.
- Work out of the box with zero config for a solo developer; scale to a small team with a simple config file.
- Be installable as a standard PyPI package and callable as `gadaj` from any directory.
- Emit machine-readable JSON so an AI agent can call `gadaj --json` and draft a journal entry from the output.

## Task: Implement gadaj v0.1

Read these files in full before writing a single line of code:

- `README.md` — user-facing behaviour, CLI flags, output format, JSON schema
- `design.md` — architecture, data models, collector protocol, testing strategy, migration table

After reading, do the following before implementing:

1. **Identify any contradictions or ambiguities** between README and design.md. If you find any, resolve them using the principle stated in design.md §1: collect don't interpret, source attribution is inviolable, time is the only join key. Note your resolutions in a brief comment at the top of the relevant file.

2. **Check for anything underspecified** that would force a guess during implementation. List these and resolve them yourself using good judgment — do not silently assume and do not stop to ask unless genuinely blocked. Document your decisions in a `DECISIONS.md` at the repo root.

3. **Plan the implementation order** before writing code. Dependencies flow: `models.py` → `utils.py` → `config.py` → `collectors/` → aggregator in `cli.py` → `reporters/` → full `cli.py` wiring. Tests should be written alongside each module, not after all code is done.

---

## What to produce

Implement the full `gadaj` package as described in README.md and design.md. Specifically:

### Source files
All files under `gadaj/` as laid out in `design.md §2`. Do not add files not listed there without documenting why in `DECISIONS.md`.

### `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "gadaj"
version = "0.1.0"
description = "Git and AI Data Aggregator for Journaling — aggregate git history and AI coding-agent sessions into a time-windowed work log."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
keywords = ["git", "claude-code", "ai", "developer-tools", "journal", "worklog", "aider", "llm"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Version Control :: Git",
]
dependencies = []

[project.optional-dependencies]
dev = ["pytest", "pytest-cov"]

[project.scripts]
gadaj = "gadaj.cli:main"

[project.urls]
Homepage   = "https://github.com/PLACEHOLDER/gadaj"
Repository = "https://github.com/PLACEHOLDER/gadaj"
```

Replace `PLACEHOLDER` with the actual GitHub username once known. Zero runtime dependencies — do not add any without flagging it explicitly.

### `CHANGELOG.md`

```markdown
# Changelog

## 0.1.0 — 2026-04-28

Initial release. Refactored and restructured from `journal_facility.py`.

### Added
- `GitCollector`: collect commits within a time window via `git log`
- `CCCollector`: collect Claude Code sessions from `~/.claude/projects/` JSONL files
- Multi-session aggregation across all CC sessions in a time window
- `MarkdownReporter`: human-readable terminal output with separate Git and CC sections
- `JsonReporter`: stable JSON schema for downstream scripts and AI agents
- `--window`, `--since`, `--until` time window flags
- `--git-range`, `--git-last`, `--git-author`, `--git-filter` git flags
- `--cc-file` CC override flag
- `--commits`, `--json`, `--out`, `--raw`, `--tz` output flags
- `~/.config/gadaj/config.toml` config with author nicks and model pricing
- `.gadaj.toml` project-level config override
- Deprecation shim at repo root `journal_facility.py`
```

### `journal_facility.py` deprecation shim

Replace the existing `journal_facility.py` in the repo root with this shim. Preserve the original file as `journal_facility_original.py` so the git history of the logic is not lost.

```python
#!/usr/bin/env python3
"""
journal_facility.py — DEPRECATED.

This script has been replaced by gadaj. Please install and use gadaj instead:

    pip install gadaj
    gadaj --help

This shim will be removed in gadaj v0.2.
"""
import sys

def main():
    print(
        "warning: journal_facility.py is deprecated. Use 'gadaj' instead.",
        file=sys.stderr,
    )
    from gadaj.cli import main as gadaj_main
    gadaj_main()

if __name__ == "__main__":
    main()
```

### Tests and fixtures

As described in `design.md §10`. Write tests alongside each module. Minimum one test per collector and one for the aggregator. Use the injectable dependency pattern described in design.md — no subprocess calls or real filesystem access in tests.

Generate realistic fixture content:

**`tests/fixtures/sample.jsonl`** — a minimal CC session transcript that covers:
- At least 10 assistant messages across two models (e.g. `claude-sonnet-4-6` and one other)
- Cache tokens present (both `cache_creation_input_tokens` and `cache_read_input_tokens`)
- A gap of more than 30 minutes between two messages (to exercise gap detection)
- Realistic timestamp spread of ~2 hours total

**`tests/fixtures/sample_git_log.txt`** — raw output of:
```
git log --format="%h\t%ad\t%an\t%s" --date=format:"%Y-%m-%d %H:%M" --reverse
```
covering a fictional repo with:
- At least 6 commits
- Two distinct authors (use "Samuel Sydänlammi" and "Mikko Sysikaski" — these map to nicks "Samuel" and "Mikko" in default config)
- Commits spanning ~3 hours
- One commit outside the test window to verify filtering

---

## Key design decisions to preserve

These are not in README or design.md explicitly but are important:

**Time window is universal and UTC-aware throughout.** All `datetime` objects inside the package are UTC-aware. Conversion to local time happens only in formatters (`utils.fmt_datetime`). Never store or compare naive datetimes.

**`WorkPeriod` is the only mutable dataclass.** All others use `frozen=True`. The aggregator builds up `WorkPeriod` incrementally; reporters treat it as read-only.

**Collectors fail softly, argument errors fail hard.** If git is not on PATH or no `.jsonl` directory exists, print a one-line warning to stderr and continue with empty results. Do not raise. Invalid CLI arguments use `argparse` error handling (prints usage and exits 2).

**`parse_since` takes `now` as a parameter.** This is essential for testability. The caller always passes `datetime.now(timezone.utc)`. Do not call `datetime.now()` inside `parse_since`.

**`--git-last N` and `--git-range` are git-only overrides.** They do not affect the CC time window. When either is used, the CC window still uses `--window`/`--since`/`--until`. This asymmetry is intentional and should be clear in `--help` text.

**Config prefix matching for model pricing.** The model string from a JSONL file may include a date suffix (e.g. `claude-sonnet-4-6-20250514`). `lookup_pricing` must match this against `claude-sonnet-4-6` in config. Use prefix matching: if the model string starts with a config key, it matches. Longest prefix wins in case of ambiguity.

**Session ID is the `.jsonl` filename stem**, not a UUID parsed from inside the file. This is stable and requires no JSONL parsing to derive.

**The `summary` key comes first in JSON output.** Use `dict` insertion order (guaranteed in Python 3.7+) and construct the output dict with `summary` first.

**Gap threshold is 30 minutes.** If two consecutive CC sessions (sorted by start time) have a gap of more than 30 minutes between the end of one and the start of the next, flag it in the CC section output as `⚠ Xm gap`. This is informational only — it does not split the output or affect cost totals.

**Parallel session detection.** If two CC sessions have overlapping time ranges (start of B < end of A), label both as `[parallel]` in the CC section. This covers the case of two agents running simultaneously.

**`--tz auto` behaviour.** Try `datetime.now().astimezone().utcoffset()` to get the local offset. If that raises or returns `None`, fall back to `+3.0` (EEST). This fallback is a team-specific default and should be documented in `--help` as such, with a note to override via `--tz` or config.

---

## What good output looks like

The markdown output format is specified in README.md. Two additional details not shown there:

The commits table (when `--commits` is passed) uses this exact column order and format:
```
| Hash      | Datetime         | Author  | Message                    |
|-----------|------------------|---------|----------------------------|
| `51d38b6` | 2026-04-28 10:02 | Samuel  | Draft workflow setup       |
```

The CC section shows sessions in chronological order (oldest first), with the most recent labelled `← most recent`. If there is only one session, omit the label.

---

## What to do if you hit a genuine conflict

If README.md and design.md directly contradict each other on a specific behaviour, **design.md wins** — it is the more detailed specification. Note the conflict and your resolution in `DECISIONS.md`.

If the spec is silent on something and you cannot infer the right answer from first principles, make the most conservative choice (least output, least side effect) and document it in `DECISIONS.md`.

Do not invent features not described in the spec. Do not add dependencies not already approved. Do not restructure the package layout without documenting why in `DECISIONS.md`.

---

## Definition of done

- `pip install -e ".[dev]" && pytest` passes with no failures
- `gadaj --help` prints coherent usage
- `gadaj -w 4h` runs without error in this repo (even if git or CC data is absent — graceful degradation)
- `gadaj -w 4h --json | python3 -m json.tool` produces valid JSON
- All files listed in `design.md §2` exist
- `DECISIONS.md` exists and documents any judgment calls made during implementation
- No runtime dependencies added to `pyproject.toml`
