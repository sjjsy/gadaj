from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from gadaj.collectors.base import Collector
from gadaj.config import Config, lookup_pricing
from gadaj.models import CCSession, ModelUsage


class CCCollector(Collector):
    """Collect Claude Code sessions from ~/.claude/projects/<hashed-cwd>/."""

    def __init__(
        self,
        cfg: Config,
        cc_file: str | None = None,
        projects_root: Path | None = None,
    ):
        self._cfg = cfg
        self._cc_file = cc_file
        self._projects_root = projects_root or (Path.home() / ".claude" / "projects")

    @property
    def source_name(self) -> str:
        return "CLAUDE CODE"

    @property
    def available(self) -> bool:
        if self._cc_file is not None:
            return Path(self._cc_file).exists()
        return _find_project_dir(self._projects_root).exists()

    def collect(self, since: datetime, until: datetime) -> list[CCSession]:
        if self._cc_file is not None:
            p = Path(self._cc_file)
            if not p.exists():
                print(f"warning: --cc-file {p} not found", file=sys.stderr)
                return []
            session = _parse_session(p, self._cfg)
            return [session] if session is not None else []

        project_dir = _find_project_dir(self._projects_root)
        if not project_dir.exists():
            return []

        sessions: list[CCSession] = []
        for jsonl_path in sorted(project_dir.glob("*.jsonl")):
            window = _session_window(jsonl_path)
            if window is None:
                continue
            s_start, s_end = window
            # Overlap check: session overlaps window if start < until AND end > since
            if s_start < until and s_end > since:
                session = _parse_session(jsonl_path, self._cfg)
                if session is not None:
                    sessions.append(session)

        sessions.sort(key=lambda s: s.start)
        return sessions


def _find_project_dir(projects_root: Path) -> Path:
    """Return ~/.claude/projects/<hashed-cwd>/ for the current directory."""
    hashed = str(Path.cwd()).replace("/", "-")
    return projects_root / hashed


def _session_window(jsonl_path: Path) -> tuple[datetime, datetime] | None:
    """Return (first_timestamp, last_timestamp) from a .jsonl file, or None."""
    timestamps: list[datetime] = []
    try:
        with open(jsonl_path) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = obj.get("timestamp")
                if ts:
                    try:
                        timestamps.append(_parse_ts(ts))
                    except (ValueError, TypeError):
                        continue
    except OSError:
        return None

    if not timestamps:
        return None
    return min(timestamps), max(timestamps)


def _parse_session(jsonl_path: Path, cfg: Config) -> CCSession | None:
    """Parse a .jsonl file into a CCSession."""
    stats: dict[str, dict] = {}
    timestamps: list[datetime] = []

    try:
        with open(jsonl_path) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts = obj.get("timestamp")
                if ts:
                    try:
                        timestamps.append(_parse_ts(ts))
                    except (ValueError, TypeError):
                        pass

                if obj.get("type") != "assistant":
                    continue

                msg = obj.get("message", {})
                model = msg.get("model", "unknown")
                usage = msg.get("usage", {})
                if not usage:
                    continue

                inp = usage.get("input_tokens", 0)
                out = usage.get("output_tokens", 0)
                cw = usage.get("cache_creation_input_tokens", 0)
                cr = usage.get("cache_read_input_tokens", 0)

                if inp + out + cw + cr == 0:
                    continue

                if model not in stats:
                    stats[model] = {
                        "input": 0,
                        "output": 0,
                        "cache_write": 0,
                        "cache_read": 0,
                        "messages": 0,
                    }
                s = stats[model]
                s["input"] += inp
                s["output"] += out
                s["cache_write"] += cw
                s["cache_read"] += cr
                s["messages"] += 1

    except OSError as e:
        print(f"warning: could not read {jsonl_path}: {e}", file=sys.stderr)
        return None

    if not timestamps:
        return None

    models: dict[str, ModelUsage] = {}
    total_cost = 0.0
    for model, s in stats.items():
        pricing = lookup_pricing(model, cfg)
        if pricing is not None:
            inp_r, out_r, cw_r, cr_r = pricing
            cost = (
                s["input"] * inp_r
                + s["output"] * out_r
                + s["cache_write"] * cw_r
                + s["cache_read"] * cr_r
            ) / 1_000_000
        else:
            cost = 0.0
        usage_obj = ModelUsage(
            input_tokens=s["input"],
            output_tokens=s["output"],
            cache_write_tokens=s["cache_write"],
            cache_read_tokens=s["cache_read"],
            messages=s["messages"],
            cost_usd=cost,
        )
        models[model] = usage_obj
        total_cost += cost

    return CCSession(
        path=jsonl_path,
        session_id=jsonl_path.stem,
        start=min(timestamps),
        end=max(timestamps),
        models=models,
        total_cost_usd=total_cost,
    )


def _parse_ts(ts: str) -> datetime:
    """Parse ISO timestamp string to UTC-aware datetime."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc)
