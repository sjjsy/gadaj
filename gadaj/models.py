from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Commit:
    hash: str
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
    commits: list[Commit] = field(default_factory=list)
    cc_sessions: list[CCSession] = field(default_factory=list)
    contributors: dict[str, ContributorStats] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
