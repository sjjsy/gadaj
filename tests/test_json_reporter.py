from __future__ import annotations

import json
from pathlib import Path

import pytest

from gadaj.cli import aggregate
from gadaj.collectors.cc import _parse_session
from gadaj.collectors.git import _parse_log_stat
from gadaj.config import Config, _DEFAULT_AUTHORS, _DEFAULT_PRICING
from gadaj.models import WorkPeriod
from gadaj.reporters.json_ import JsonReporter
from tests.conftest import utc

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _default_cfg() -> Config:
    return Config(authors=dict(_DEFAULT_AUTHORS), pricing=dict(_DEFAULT_PRICING))


def _make_period() -> WorkPeriod:
    cfg = _default_cfg()
    commits = _parse_log_stat(
        (FIXTURES_DIR / "sample_git_log.txt").read_text(), cfg
    )
    sessions = []
    for name in ["sample.jsonl", "sample2.jsonl"]:
        s = _parse_session(FIXTURES_DIR / name, cfg)
        if s:
            sessions.append(s)
    return aggregate(
        commits, sessions, utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0)
    )


# ---------------------------------------------------------------------------

def test_json_valid():
    period = _make_period()
    output = JsonReporter().render(period)
    data = json.loads(output)
    assert isinstance(data, dict)


def test_json_summary_key_first():
    period = _make_period()
    output = JsonReporter().render(period)
    data = json.loads(output)
    keys = list(data.keys())
    assert keys[0] == "summary"


def test_json_has_all_top_level_keys():
    period = _make_period()
    data = json.loads(JsonReporter().render(period))
    assert "summary" in data
    assert "window" in data
    assert "git" in data
    assert "cc" in data


def test_json_window_duration():
    period = _make_period()
    data = json.loads(JsonReporter().render(period))
    assert data["window"]["duration_hours"] == 4.0


def test_json_git_commits_count():
    period = _make_period()
    data = json.loads(JsonReporter().render(period))
    assert len(data["git"]["commits"]) == 9


def test_json_cc_sessions_count():
    period = _make_period()
    data = json.loads(JsonReporter().render(period))
    assert len(data["cc"]["sessions"]) == 2


def test_json_cc_total_cost():
    period = _make_period()
    data = json.loads(JsonReporter().render(period))
    assert data["cc"]["total_cost_usd"] > 0


def test_json_summary_contributors():
    period = _make_period()
    data = json.loads(JsonReporter().render(period))
    contributors = data["summary"]["contributors"]
    assert isinstance(contributors, list)
    kinds = {c["kind"] for c in contributors}
    assert "human" in kinds
    assert "ai" in kinds


def test_json_datetime_serialized_as_string():
    period = _make_period()
    data = json.loads(JsonReporter().render(period))
    # Datetimes in window should be ISO strings
    since_str = data["window"]["since"]
    assert isinstance(since_str, str)
    assert "2026" in since_str


def test_json_empty_period():
    period = WorkPeriod(since=utc(2026, 4, 28, 10, 0), until=utc(2026, 4, 28, 14, 0))
    data = json.loads(JsonReporter().render(period))
    assert data["git"]["commits"] == []
    assert data["cc"]["sessions"] == []
    assert data["summary"]["total_cost_usd"] == 0.0
