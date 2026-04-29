from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


def parse_window(s: str) -> timedelta:
    """Parse "2h", "1.5d", "90m" → timedelta. Raise ValueError on bad input."""
    s = s.strip().lower()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([hmd])", s)
    if not m:
        raise ValueError(
            f"Invalid window: {s!r}. Use e.g. '4h', '1.5d', '90m'."
        )
    val, unit = float(m.group(1)), m.group(2)
    if unit == "h":
        return timedelta(hours=val)
    if unit == "d":
        return timedelta(days=val)
    # unit == "m"
    return timedelta(minutes=val)


_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_since(s: str, now: datetime) -> datetime:
    """
    Parse natural language and ISO strings to UTC-aware datetime.

    Supported:
      ISO date/datetime, "today", "yesterday",
      "N hours ago", "N days ago", "N minutes ago",
      weekday names ("monday", "friday", …).

    `now` is injected for testability — callers pass datetime.now(UTC).
    """
    s_stripped = s.strip()
    s_lower = s_stripped.lower()

    if s_lower == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    if s_lower == "yesterday":
        d = now - timedelta(days=1)
        return d.replace(hour=0, minute=0, second=0, microsecond=0)

    # "N unit(s) ago"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(hours?|days?|minutes?)\s+ago", s_lower)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        if unit.startswith("hour"):
            return now - timedelta(hours=val)
        if unit.startswith("day"):
            return now - timedelta(days=val)
        return now - timedelta(minutes=val)

    # Weekday names
    if s_lower in _WEEKDAYS:
        target_wd = _WEEKDAYS.index(s_lower)
        current_wd = now.weekday()
        days_back = (current_wd - target_wd) % 7 or 7
        d = now - timedelta(days=days_back)
        return d.replace(hour=0, minute=0, second=0, microsecond=0)

    # ISO datetime (possibly timezone-aware)
    try:
        dt = datetime.fromisoformat(s_stripped)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    raise ValueError(f"Cannot parse datetime: {s!r}")


def fmt_tok(n: int) -> str:
    """1_500_000 → "1.5M", 12_000 → "12k", 800 → "800"."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1000}k"
    return str(n)


def fmt_cost(usd: float) -> str:
    """6.59 → "~$6.59"."""
    return f"~${usd:.2f}"


def fmt_duration(td: timedelta) -> str:
    """timedelta(hours=3.4) → "~3.4h"."""
    hours = td.total_seconds() / 3600
    return f"~{hours:.1f}h"


def fmt_datetime(dt: datetime, tz_offset: float) -> str:
    """UTC datetime → "2026-04-28 13:25 EEST" given tz_offset=3.0."""
    local = dt + timedelta(hours=tz_offset)
    date_str = local.strftime("%Y-%m-%d %H:%M")
    if tz_offset == 3.0:
        tz_label = "EEST"
    elif tz_offset == 2.0:
        tz_label = "EET"
    elif tz_offset == 0.0:
        tz_label = "UTC"
    else:
        sign = "+" if tz_offset >= 0 else "-"
        tz_label = f"UTC{sign}{abs(tz_offset):.0f}"
    return f"{date_str} {tz_label}"


def fmt_hhmm(dt: datetime, tz_offset: float) -> str:
    """UTC datetime → "13:25" in local time."""
    local = dt + timedelta(hours=tz_offset)
    return local.strftime("%H:%M")


def fmt_session_range(start: datetime, end: datetime, tz_offset: float) -> str:
    """Format a session time range as "10:00 – 13:25" or with dates if spanning days."""
    local_start = start + timedelta(hours=tz_offset)
    local_end = end + timedelta(hours=tz_offset)
    start_date = local_start.date()
    end_date = local_end.date()

    start_str = local_start.strftime("%H:%M")
    if start_date == end_date:
        end_str = local_end.strftime("%H:%M")
    else:
        end_str = local_end.strftime("%Y-%m-%d %H:%M")
    return f"{start_str} – {end_str}"


def fmt_time_range(since: datetime, until: datetime, tz_offset: float) -> str:
    """Format a time range as "2026-04-28 10:00 – 13:25 EEST" or with both dates if spanning days."""
    local_since = since + timedelta(hours=tz_offset)
    local_until = until + timedelta(hours=tz_offset)
    since_date = local_since.date()
    until_date = local_until.date()

    since_str = local_since.strftime("%Y-%m-%d %H:%M")
    if since_date == until_date:
        until_str = local_until.strftime("%H:%M")
    else:
        until_str = local_until.strftime("%Y-%m-%d %H:%M")

    if tz_offset == 3.0:
        tz_label = "EEST"
    elif tz_offset == 2.0:
        tz_label = "EET"
    elif tz_offset == 0.0:
        tz_label = "UTC"
    else:
        sign = "+" if tz_offset >= 0 else "-"
        tz_label = f"UTC{sign}{abs(tz_offset):.0f}"
    return f"{since_str} – {until_str} {tz_label}"


def detect_tz_offset() -> float:
    """Return local UTC offset in hours. Fallback: 3.0 (EEST, team default)."""
    try:
        offset = datetime.now().astimezone().utcoffset()
        if offset is None:
            return 3.0
        return offset.total_seconds() / 3600
    except Exception:
        return 3.0
