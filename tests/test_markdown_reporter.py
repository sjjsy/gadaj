from __future__ import annotations

from pathlib import Path

import pytest

from gadaj.cli import aggregate
from gadaj.collectors.cc import _parse_session
from gadaj.collectors.git import _parse_log_stat
from gadaj.config import Config, _DEFAULT_AUTHORS, _DEFAULT_PRICING
from gadaj.models import CCSession, Commit, ModelUsage, WorkPeriod
from gadaj.reporters.markdown import MarkdownReporter, _mark_parallel
from tests.conftest import utc

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _default_cfg() -> Config:
    return Config(authors=dict(_DEFAULT_AUTHORS), pricing=dict(_DEFAULT_PRICING))


def _make_period(with_commits=True, with_sessions=True) -> WorkPeriod:
    cfg = _default_cfg()
    commits = []
    sessions = []

    if with_commits:
        commits = _parse_log_stat(
            (FIXTURES_DIR / "sample_git_log.txt").read_text(), cfg
        )

    if with_sessions:
        for name in ["sample.jsonl", "sample2.jsonl"]:
            s = _parse_session(FIXTURES_DIR / name, cfg)
            if s:
                sessions.append(s)

    return aggregate(
        commits, sessions, utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0)
    )


# ---------------------------------------------------------------------------

def test_markdown_contains_git_header():
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "══ GIT" in output


def test_markdown_contains_cc_header():
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "══ CLAUDE CODE" in output


def test_markdown_contains_summary_header():
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "══ SUMMARY" in output


def test_markdown_shows_two_sessions():
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "2 in window" in output


def test_markdown_shows_most_recent_label():
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "← most recent" in output


def test_markdown_gap_warning():
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "⚠" in output  # gap between session 1 (ends 11:47) and session 2 (starts 12:20)


def test_markdown_no_most_recent_single_session():
    period = _make_period(with_sessions=True)
    # Override to single session
    s = _parse_session(FIXTURES_DIR / "sample.jsonl", _default_cfg())
    period.cc_sessions = [s]
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "← most recent" not in output


def test_markdown_commits_table_when_flag():
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, show_commits=True)
    output = reporter.render(period)
    assert "| Hash" in output
    assert "| Datetime" in output


def test_markdown_no_commits_table_by_default():
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "| Hash" not in output


def test_markdown_empty_period():
    period = WorkPeriod(since=utc(2026, 4, 28, 10, 0), until=utc(2026, 4, 28, 14, 0))
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "no commits" in output
    assert "no sessions" in output


def test_markdown_cost_shown():
    period = _make_period(with_sessions=True)
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    assert "~$" in output


# ---------------------------------------------------------------------------
# _mark_parallel

def test_mark_parallel_no_overlap():
    from gadaj.models import CCSession
    from pathlib import Path
    s1 = CCSession(
        path=Path("a.jsonl"), session_id="a",
        start=utc(2026, 4, 28, 10, 0), end=utc(2026, 4, 28, 11, 0),
        models={}, total_cost_usd=0,
    )
    s2 = CCSession(
        path=Path("b.jsonl"), session_id="b",
        start=utc(2026, 4, 28, 11, 30), end=utc(2026, 4, 28, 12, 30),
        models={}, total_cost_usd=0,
    )
    assert _mark_parallel([s1, s2]) == [False, False]


def test_mark_parallel_with_overlap():
    from gadaj.models import CCSession
    s1 = CCSession(
        path=Path("a.jsonl"), session_id="a",
        start=utc(2026, 4, 28, 10, 0), end=utc(2026, 4, 28, 12, 0),
        models={}, total_cost_usd=0,
    )
    s2 = CCSession(
        path=Path("b.jsonl"), session_id="b",
        start=utc(2026, 4, 28, 11, 0), end=utc(2026, 4, 28, 13, 0),
        models={}, total_cost_usd=0,
    )
    assert _mark_parallel([s1, s2]) == [True, True]
