from __future__ import annotations

from datetime import timedelta, timezone

import pytest

from gadaj.utils import (
    detect_tz_offset,
    fmt_cost,
    fmt_datetime,
    fmt_duration,
    fmt_hhmm,
    fmt_tok,
    parse_since,
    parse_window,
)
from tests.conftest import utc


# ---------------------------------------------------------------------------
# parse_window

def test_parse_window_hours():
    assert parse_window("4h") == timedelta(hours=4)


def test_parse_window_fractional_hours():
    assert parse_window("1.5h") == timedelta(hours=1.5)


def test_parse_window_minutes():
    assert parse_window("90m") == timedelta(minutes=90)


def test_parse_window_days():
    assert parse_window("2d") == timedelta(days=2)


def test_parse_window_bad_input():
    with pytest.raises(ValueError):
        parse_window("4x")


def test_parse_window_bad_no_unit():
    with pytest.raises(ValueError):
        parse_window("100")


# ---------------------------------------------------------------------------
# parse_since

def test_parse_since_today():
    now = utc(2026, 4, 28, 14, 30)
    result = parse_since("today", now)
    assert result == utc(2026, 4, 28, 0, 0)


def test_parse_since_yesterday():
    now = utc(2026, 4, 28, 14, 30)
    result = parse_since("yesterday", now)
    assert result == utc(2026, 4, 27, 0, 0)


def test_parse_since_hours_ago():
    now = utc(2026, 4, 28, 14, 0)
    result = parse_since("3 hours ago", now)
    assert result == utc(2026, 4, 28, 11, 0)


def test_parse_since_days_ago():
    now = utc(2026, 4, 28, 12, 0)
    result = parse_since("2 days ago", now)
    assert result == utc(2026, 4, 26, 12, 0)


def test_parse_since_iso_date():
    now = utc(2026, 4, 28, 12, 0)
    result = parse_since("2026-04-20", now)
    assert result == utc(2026, 4, 20, 0, 0)


def test_parse_since_iso_datetime():
    now = utc(2026, 4, 28, 12, 0)
    result = parse_since("2026-04-20T10:30:00", now)
    assert result == utc(2026, 4, 20, 10, 30)


def test_parse_since_monday():
    # 2026-04-28 is a Tuesday (weekday=1)
    now = utc(2026, 4, 28, 12, 0)
    result = parse_since("monday", now)
    assert result == utc(2026, 4, 27, 0, 0)


def test_parse_since_same_weekday_goes_back_7():
    # 2026-04-28 is a Tuesday; asking for "tuesday" gives last Tuesday (7 days back)
    now = utc(2026, 4, 28, 12, 0)
    result = parse_since("tuesday", now)
    assert result == utc(2026, 4, 21, 0, 0)


def test_parse_since_invalid():
    with pytest.raises(ValueError):
        parse_since("not-a-date", utc(2026, 4, 28))


# ---------------------------------------------------------------------------
# fmt_tok

def test_fmt_tok_millions():
    assert fmt_tok(1_500_000) == "1.5M"


def test_fmt_tok_thousands():
    assert fmt_tok(12_000) == "12k"


def test_fmt_tok_small():
    assert fmt_tok(800) == "800"


def test_fmt_tok_zero():
    assert fmt_tok(0) == "0"


# ---------------------------------------------------------------------------
# fmt_cost

def test_fmt_cost():
    assert fmt_cost(6.59) == "~$6.59"


def test_fmt_cost_zero():
    assert fmt_cost(0.0) == "~$0.00"


# ---------------------------------------------------------------------------
# fmt_duration

def test_fmt_duration():
    assert fmt_duration(timedelta(hours=3.4)) == "~3.4h"


def test_fmt_duration_short():
    assert fmt_duration(timedelta(minutes=30)) == "~0.5h"


# ---------------------------------------------------------------------------
# fmt_datetime

def test_fmt_datetime_eest():
    dt = utc(2026, 4, 28, 10, 0)
    result = fmt_datetime(dt, 3.0)
    assert result == "2026-04-28 13:00 EEST"


def test_fmt_datetime_utc():
    dt = utc(2026, 4, 28, 10, 0)
    result = fmt_datetime(dt, 0.0)
    assert result == "2026-04-28 10:00 UTC"


def test_fmt_datetime_other_offset():
    dt = utc(2026, 4, 28, 10, 0)
    result = fmt_datetime(dt, 5.0)
    assert result == "2026-04-28 15:00 UTC+5"


# ---------------------------------------------------------------------------
# fmt_hhmm

def test_fmt_hhmm():
    dt = utc(2026, 4, 28, 10, 30)
    assert fmt_hhmm(dt, 3.0) == "13:30"


# ---------------------------------------------------------------------------
# detect_tz_offset

def test_detect_tz_offset_returns_float():
    result = detect_tz_offset()
    assert isinstance(result, float)
    assert -12.0 <= result <= 14.0
