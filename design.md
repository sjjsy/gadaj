# gadaj — Technical Design

> **Git and AI Data Aggregator for Journaling**
> This document is the authoritative technical reference for contributors and for AI coding agents implementing or extending `gadaj`. For product goals, competition analysis, and CLI spec, see `README.md`.

---

## 1. Guiding principles

- **Collect, don't interpret.** `gadaj` gathers raw evidence and presents it. It does not write prose, infer task intent, or make editorial judgments about the work. That is the user's job.
- **Source attribution is inviolable.** Git data and AI session data are never silently merged. Every output section carries its source label. This is both a UX principle and a correctness requirement — a commit timestamp and a CC session timestamp may refer to the same work, but they are different facts from different systems.
- **Time is the only join key.** All sources are queried against a common time window. No IDs, no enforced commit message conventions, no external tracker required. The complexity of cross-source correlation is pushed to the user, not the tool.
- **Minimal runtime dependencies.** The tool installs in one command and runs on Python 3.8+. The only runtime dependency is `tomli` (TOML parser) on Python < 3.11; on Python 3.11+ the stdlib `tomllib` module is used. No other runtime dependencies.
- **Refactored from `journal_facility.py`.** The core logic (JSONL parsing, cost calculation, git helpers) was migrated from the original single-file script into a proper package.

---

## 2. Repository layout

```
gadaj/                          ← installable package
│
├── __init__.py                 ← version string only: __version__ = "0.1.0"
├── cli.py                      ← argparse entrypoint, orchestration
├── config.py                   ← config file loading, author nicks, model pricing
├── models.py                   ← all dataclasses
├── utils.py                    ← pure functions: formatting, time parsing
│
├── collectors/
│   ├── __init__.py
│   ├── base.py                 ← Collector ABC
│   ├── git.py                  ← GitCollector
│   └── cc.py                   ← CCCollector (Claude Code JSONL)
│
└── reporters/
    ├── __init__.py
    ├── markdown.py             ← MarkdownReporter
    └── json_.py                ← JsonReporter

pyproject.toml
README.md
CHANGELOG.md
DECISIONS.md                    ← judgment calls made during implementation
design.md                       ← this file
LICENSE
tests/
    conftest.py                 ← shared fixtures
    test_utils.py
    test_config.py
    test_git_collector.py
    test_cc_collector.py
    test_aggregator.py
    test_markdown_reporter.py
    test_json_reporter.py
    fixtures/
        sample.jsonl            ← CC session 1 (10:02–11:47 UTC, two models)
        sample2.jsonl           ← CC session 2 (12:20–13:24 UTC, gap detection)
        sample_git_log.txt      ← git log --stat output with Unix timestamps
```

---

## 3. Data model

All types live in `models.py`. No logic here — pure data containers. `dataclass(frozen=True)` is used throughout to prevent accidental mutation between collection and reporting.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Commit:
    hash: str                   # 7-char short hash
    datetime: datetime          # UTC-aware
    author: str                 # resolved nick (or raw name if no mapping)
    message: str
    files_changed: int
    insertions: int
    deletions: int


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    messages: int
    cost_usd: float


@dataclass(frozen=True)
class CCSession:
    path: Path
    session_id: str             # filename stem of the .jsonl
    start: datetime             # UTC-aware, first timestamp in file
    end: datetime               # UTC-aware, last timestamp in file
    models: dict[str, ModelUsage]
    total_cost_usd: float


@dataclass(frozen=True)
class ContributorStats:
    name: str
    kind: Literal["human", "ai"]
    model: str | None           # None for humans
    sessions: int               # CC sessions; 0 for humans
    commits: int
    cost_usd: float


@dataclass
class WorkPeriod:
    """The aggregated result of one gadaj invocation. Mutable — built incrementally."""
    since: datetime
    until: datetime
    commits: list[Commit]               = field(default_factory=list)
    cc_sessions: list[CCSession]        = field(default_factory=list)
    contributors: dict[str, ContributorStats] = field(default_factory=dict)
    total_cost_usd: float               = 0.0
    files_changed: int                  = 0
    insertions: int                     = 0
    deletions: int                      = 0
```

`WorkPeriod` is the only mutable type because it is built up by the aggregator before being handed to reporters. All other types are frozen after construction.

---

## 4. Collector protocol

`collectors/base.py` defines the interface every source must implement.

```python
from abc import ABC, abstractmethod
from datetime import datetime


class Collector(ABC):
    """
    One source of work evidence.

    To add a new source:
      1. Create gadaj/collectors/<name>.py
      2. Subclass Collector and implement collect() and source_name
      3. Register the new collector in cli.py alongside GitCollector and CCCollector

    No other files need to change.
    """

    @abstractmethod
    def collect(self, since: datetime, until: datetime) -> list:
        """
        Return a list of model instances covering the given window.
        - GitCollector returns list[Commit]
        - CCCollector returns list[CCSession]
        - Future collectors return their own types, which reporters handle via isinstance()

        Both datetimes are UTC-aware. Implementations must filter to this window;
        they must not assume the caller will filter.
        """
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable label used in output section headers."""
        ...

    @property
    def available(self) -> bool:
        """
        Return False if this source is not usable in the current environment
        (e.g. git not on PATH, no .jsonl directory found).
        cli.py skips unavailable collectors with a soft warning, not an error.
        Default: True. Override when availability is not guaranteed.
        """
        return True
```

### GitCollector (`collectors/git.py`)

Wraps `git log --stat` via `subprocess`. All git interaction is isolated here —
no subprocess calls elsewhere in the codebase.

Key responsibilities:
- Resolve `--git-range` (explicit hash range) or derive a `--since`/`--until` range from the window
- Map author names to nicks via `config.authors`
- Parse per-commit diff stats (`files_changed`, `insertions`, `deletions`) from `--stat` output
- Return `list[Commit]` sorted ascending by datetime
- Return `[]` gracefully if git is not on PATH or cwd is not a repo (`available = False`)

**Implementation note:** The git log format uses `%at` (author date as Unix timestamp,
UTC) rather than a formatted date string. This avoids timezone ambiguity when the
committer's local timezone differs from the tool's runtime timezone.

Time window arguments are passed with explicit `+00:00` UTC offset
(`--after=2026-04-28T10:00:00+00:00`) so git does not misinterpret UTC times as
local time.

Internal helpers:
- `_parse_log_stat(output, cfg) -> list[Commit]`
- `_parse_stat_summary(line) -> tuple[int, int, int]`

### CCCollector (`collectors/cc.py`)

Scans `~/.claude/projects/<hashed-cwd>/` for `.jsonl` files whose timestamp range overlaps the requested window.

Key responsibilities:
- Find the project directory by hashing `Path.cwd()` (same logic as `journal_facility.py`)
- Read all `.jsonl` files in that directory, parse timestamps to determine overlap with window
- For overlapping files: parse all `assistant` message entries, accumulate token usage per model
- Compute cost per model via `config.PRICING`
- Detect and annotate gaps (> 30 min between sessions) and overlaps (parallel sessions)
- Return `list[CCSession]` sorted ascending by start time
- Return `[]` gracefully if no `.jsonl` directory exists

Internal helpers (migrated from `journal_facility.py`):
- `_find_project_dir(project_path) -> Path`
- `_session_window(jsonl_path) -> tuple[datetime, datetime] | None`
- `_parse_session(jsonl_path) -> CCSession`
- `_compute_cost(model, usage) -> float`

---

## 5. Aggregator

The aggregator lives in `cli.py` as a standalone function, not a class. It is simple enough to not warrant its own module.

```python
def aggregate(
    commits: list[Commit],
    cc_sessions: list[CCSession],
    since: datetime,
    until: datetime,
) -> WorkPeriod:
    ...
```

It:
1. Constructs a `WorkPeriod` with the given window
2. Attaches commits and sessions
3. Derives `ContributorStats` — one entry per human author (from commits) and one per model (from sessions)
4. Sums `total_cost_usd`, `files_changed`, `insertions`, `deletions`
5. Returns the completed `WorkPeriod`

The aggregator does not call any collector. It receives already-collected data. This makes it straightforwardly testable without any subprocess or filesystem mocking.

---

## 6. Reporter protocol

Both reporters accept a `WorkPeriod` and return a string.

```python
class Reporter(ABC):
    @abstractmethod
    def render(self, period: WorkPeriod) -> str: ...
```

### MarkdownReporter (`reporters/markdown.py`)

Produces the human-readable terminal output. Sections:

1. `══ GIT ... ══` — commit summary line, authors, diff stat, optional full commits table
2. `══ CLAUDE CODE ... ══` — per-session block, per-model totals table
3. `══ SUMMARY ══` — one-line per source plus total cost

Section rendering is split into private methods (`_git_section`, `_cc_section`, `_summary_section`) so each can be tested in isolation.

Formatting helpers from `utils.py` are used throughout: `fmt_tok`, `fmt_duration`, `fmt_datetime`, `fmt_cost`.

### JsonReporter (`reporters/json_.py`)

Produces a stable JSON structure suitable for consumption by an AI agent or a downstream script. The schema:

```json
{
  "window": {
    "since": "2026-04-28T10:00:00+00:00",
    "until": "2026-04-28T13:25:00+00:00",
    "duration_hours": 3.4
  },
  "git": {
    "commits": [...],
    "files_changed": 7,
    "insertions": 672,
    "deletions": 7,
    "authors": {"Samuel": 8}
  },
  "cc": {
    "sessions": [...],
    "models": {
      "claude-sonnet-4-6": {
        "input_tokens": 180000,
        "output_tokens": 174000,
        "cache_write_tokens": 293000,
        "cache_read_tokens": 9600000,
        "cost_usd": 6.59
      }
    },
    "total_cost_usd": 6.59
  },
  "summary": {
    "total_cost_usd": 6.59,
    "contributors": [...]
  }
}
```

The `summary` block is placed first in serialization order so an AI reading the output can stop early if it only needs the overview. Use `json.dumps(..., indent=2, default=str)` — no custom encoder needed since `datetime` is serialized via `default=str`.

The JSON schema must remain stable across patch versions. Breaking changes require a minor version bump and a CHANGELOG entry.

---

## 7. Configuration (`config.py`)

Config is loaded once at startup and stored as a module-level singleton. The load order is:

1. Built-in defaults (hardcoded in `config.py`)
2. User config: `~/.config/gadaj/config.toml` (created with defaults on first run if absent)
3. Project config: `<cwd>/.gadaj.toml` (optional, overrides user config for that repo)

`tomllib` (stdlib in Python 3.11+) handles parsing on modern Python. On Python 3.8–3.10, the `tomli` package (a dependency) provides the same interface under `tomli`. The import is handled transparently in `config.py`. If neither is available, config file loading is skipped with a warning and built-in defaults are used.

```python
@dataclass
class Config:
    authors: dict[str, str]             # raw name → nick
    pricing: dict[str, tuple[float, float, float, float]]
    default_window: str                 # e.g. "4h"
    tz_offset: float | Literal["auto"]

def load_config() -> Config: ...
def resolve_nick(raw_name: str, cfg: Config) -> str: ...
def lookup_pricing(model: str, cfg: Config) -> tuple[float, float, float, float] | None: ...
```

`lookup_pricing` uses prefix matching (same logic as `journal_facility.py`) so versioned model strings like `claude-sonnet-4-6-20250514` match against `claude-sonnet-4-6`.

---

## 8. Utilities (`utils.py`)

Pure functions only. No I/O, no subprocess, no config access. All are independently unit-testable.

```python
def parse_window(s: str) -> timedelta:
    """Parse "2h", "1.5d", "90m" → timedelta. Raise ValueError on bad input."""

def parse_since(s: str, now: datetime) -> datetime:
    """
    Parse natural language and ISO strings to UTC-aware datetime.
    Supported: ISO date, ISO datetime, "today", "yesterday", "N hours ago", "N days ago".
    'now' is injected for testability — callers pass datetime.now(UTC).
    """

def fmt_tok(n: int) -> str:
    """1_500_000 → "1.5M", 12_000 → "12k", 800 → "800"."""

def fmt_cost(usd: float) -> str:
    """6.59 → "~$6.59"."""

def fmt_duration(td: timedelta) -> str:
    """timedelta(hours=3.4) → "~3.4h"."""

def fmt_datetime(dt: datetime, tz_offset: float) -> str:
    """UTC datetime → "2026-04-28 13:25 EEST" given tz_offset=3.0."""

def detect_tz_offset() -> float:
    """Return local UTC offset in hours. Fallback: 3.0 (EEST)."""
```

---

## 9. CLI entrypoint (`cli.py`)

`main()` is the `[project.scripts]` target. Its structure:

```
main()
  ├── parse_args()
  ├── load_config()
  ├── resolve_window(args, config) → (since, until)
  ├── for each enabled collector:
  │     if collector.available: results += collector.collect(since, until)
  │     else: warn to stderr
  ├── aggregate(commits, cc_sessions, since, until) → WorkPeriod
  ├── select reporter (Markdown or JSON)
  └── reporter.render(period) → print or write to --out file
```

`parse_args()` is a standalone function (not inline in `main`) so it can be called in tests without triggering I/O.

Error handling philosophy: collectors fail softly (warn + skip); argument errors fail hard with a clear message; unexpected exceptions propagate with a traceback. No `sys.exit` outside `main`.

---

## 10. Testing strategy

### What to test

Every module has a corresponding test file. The coverage target for v0.1 is 80% line coverage, measured with `pytest-cov`. The goal is confidence in the core data pipeline, not exhaustive edge case coverage at this stage.

| Module | Test focus |
|---|---|
| `utils.py` | All formatting and parsing functions. Property-based if worth it for `parse_window`. |
| `config.py` | Config merge order, prefix matching in `lookup_pricing`, nick resolution. |
| `collectors/git.py` | Parse `sample_git_log.txt` fixture, author nick resolution, empty-repo graceful return. |
| `collectors/cc.py` | Parse `sample.jsonl` fixture, window overlap filtering, multi-session detection, cost calculation. |
| Aggregator | `WorkPeriod` construction from known inputs, `ContributorStats` derivation. |
| `reporters/markdown.py` | Section rendering from a known `WorkPeriod`; snapshot test the full output. |
| `reporters/json_.py` | Schema shape, `summary` key present, datetime serialization. |

### Fixtures

`tests/fixtures/sample.jsonl` — a minimal but realistic CC session transcript with at least two models and cache tokens. Should cover: multiple assistant turns, one tool use, one gap of > 30 minutes (to test gap detection).

`tests/fixtures/sample_git_log.txt` — output of `git log --format=GADAJ:%h\t%at\t%an\t%s --stat --reverse` for a fictional repo. Uses Unix timestamps (`%at`) for timezone-correct parsing. At least 9 commits, two authors, one commit outside the test window to verify filtering.

### No subprocess in tests

`GitCollector` accepts an injectable `runner` callable (default: `subprocess.run`). Tests inject a fake that returns the fixture content. This avoids any dependency on a real git repo being present during `pytest`.

```python
class GitCollector(Collector):
    def __init__(self, runner=subprocess.run):
        self._run = runner
```

`CCCollector` accepts an injectable `projects_root` path (default: `Path.home() / ".claude" / "projects"`). Tests point it at a temp directory containing the fixture `.jsonl`.

### Running tests

```bash
pip install -e ".[dev]"
pytest
pytest --cov=gadaj --cov-report=term-missing
```

`[dev]` extras in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = ["pytest", "pytest-cov"]
```

---

## 11. Origins

`gadaj` was refactored from `journal_facility.py`, a single-file script that
produced journal entry tables from a CC session and a git range. The core logic
was preserved and reorganised:

| Original function | Destination in `gadaj` |
|---|---|
| `parse_session()` | `CCCollector._parse_session()` in `collectors/cc.py` |
| `compute_cost()` | `config.lookup_pricing()` + inline in `CCCollector` |
| `find_project_dir()` | `CCCollector._find_project_dir()` in `collectors/cc.py` |
| `find_current_session()` | absorbed into `CCCollector.collect()` |
| `git_commit_table()` | `MarkdownReporter._commits_table()` |
| `git_diff_stat()` | `GitCollector` via `--stat` parsing |
| `fmt_tok()` | `utils.fmt_tok()` |
| `fmt_duration()` | `utils.fmt_duration()` |
| `AUTHOR_NICKS` | `config.toml [authors]` + `config.py` defaults |
| `PRICING` | `config.toml [pricing]` + `config.py` defaults |

The main behavioural change: `gadaj` scans **all** CC sessions in the time window
rather than defaulting to the single most recent `.jsonl` file. Use `--cc-file`
if you want the old single-file behaviour.

---

## 12. Versioning and changelog policy

`gadaj` follows [Semantic Versioning](https://semver.org):

- **Patch** (0.1.x): bug fixes, pricing updates, formatting tweaks. No new flags.
- **Minor** (0.x.0): new flags, new collectors, new output sections. JSON schema additions (not removals).
- **Major** (x.0.0): breaking CLI flag changes, JSON schema removals, Python version drops.

Every release has a `CHANGELOG.md` entry written before tagging. The entry format mirrors the journal entry format from the team's own workflow: date, summary, what changed, why.

---

## 13. Future extension points

These are documented here so they are designed for, not retrofitted.

- **New collectors:** implement `Collector`, register in `cli.py`. Planned: `AiderCollector` (parses `.aider.chat.history.md`), `OpenRouterCollector` (parses local spend logs if available), `TogglCollector` (parses CSV export).
- **New reporters:** implement `Reporter`. Planned: `HtmlReporter` for a static single-file summary page.
- **Multi-repo support:** `WorkPeriod` already supports this — `GitCollector` would need a `repos: list[Path]` parameter and the aggregator would merge across them. The data model does not need to change.
- **Config schema evolution:** add new keys under new `[sections]` in `config.toml`. Never remove or rename existing keys in a patch or minor release.
