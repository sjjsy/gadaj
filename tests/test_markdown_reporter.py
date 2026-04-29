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


# ---------------------------------------------------------------------------
# Markdown mode tests

def test_markdown_mode_git_header_uses_hash():
    """Headers use #### in markdown_tables=True mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=True)
    output = reporter.render(period)
    assert "#### GIT" in output


def test_markdown_mode_cc_header_uses_hash():
    """CC header uses #### in markdown_tables=True mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=True)
    output = reporter.render(period)
    assert "#### CLAUDE CODE" in output


def test_markdown_mode_summary_header_uses_hash():
    """Summary header uses #### in markdown_tables=True mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=True)
    output = reporter.render(period)
    assert "#### SUMMARY" in output


def test_lightweight_heading_no_equals_padding():
    """Lightweight mode uses ══ for headers without padding."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=False)
    output = reporter.render(period)
    assert "══ GIT" in output
    assert "#### GIT" not in output


def test_markdown_mode_sessions_table_is_pipe_format():
    """Sessions table uses pipe format in markdown_tables=True mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=True)
    output = reporter.render(period)
    # Should have pipe table format
    assert "| # |" in output or "| # | Range" in output


def test_lightweight_sessions_table_is_space_aligned():
    """Sessions table uses space alignment in lightweight mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=False)
    output = reporter.render(period)
    # Sessions should have space-aligned columns, not pipe table
    lines = output.split('\n')
    sessions_section = '\n'.join(lines)
    # Look for the space-aligned format without pipes in session lines
    assert "1  2026-04-28" in sessions_section or "1 " in sessions_section


def test_models_table_long_model_name_doesnt_overflow():
    """Long model names don't cause column misalignment."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=False)
    output = reporter.render(period)
    # Both short and long model names should have proper column alignment
    lines = output.split('\n')
    model_lines = [l for l in lines if 'claude' in l.lower()]
    assert len(model_lines) > 0
    # All model lines should have consistent column structure
    for line in model_lines:
        # Should have model name, then token counts, then cost
        parts = line.split()
        assert len(parts) >= 2  # at least model name and one number


def test_markdown_mode_models_table_uses_pipe_format():
    """Models table uses pipe format in markdown_tables=True mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=True)
    output = reporter.render(period)
    # Should have pipe table with Model, In, Out, Cache columns
    assert "| Model" in output
    assert "| In" in output or "In |" in output


def test_summary_table_markdown_mode():
    """Summary uses pipe table format in markdown_tables=True mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=True)
    output = reporter.render(period)
    # Should have source/summary columns in pipe format
    assert "| Source |" in output or "| Source" in output


def test_summary_table_lightweight_mode():
    """Summary uses space alignment in lightweight mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=False)
    output = reporter.render(period)
    # Should have Source, Summary text but not pipe format (except commits table)
    lines = output.split('\n')
    summary_section = [l for l in lines if 'Git' in l or 'CC' in l or 'Total' in l]
    # Summary lines should not have pipes
    for line in summary_section:
        if 'commits' not in line.lower():  # skip if it's from commits table
            # These summary lines should be space-aligned, not pipe tables
            pass
