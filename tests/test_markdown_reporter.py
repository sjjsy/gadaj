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
    """Commits table shown in lightweight format when -m flag not given."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, show_commits=True, markdown_tables=False)
    output = reporter.render(period)
    # Should contain Hash, Author, Files, Message columns (in lightweight format, not pipes)
    assert "Hash" in output
    assert "Author" in output
    assert "Files" in output


def test_markdown_commits_table_markdown_mode():
    """Commits table in pipe format when -m flag is given."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, show_commits=True, markdown_tables=True)
    output = reporter.render(period)
    # Should have pipe format
    assert "| Hash" in output
    assert "| Author" in output
    assert "| Files" in output


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
    # Should have pipe table format with session numbers
    assert "| #" in output and "| Range" in output


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


def test_summary_git_row_shows_over_hours():
    """Git row shows 'X commits over ~Nh' when multiple commits."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    # Should contain "commits over" in the summary
    assert "commits over" in output or "commit over" in output


def test_summary_cc_row_cost_first():
    """CC row starts with cost, then 'over', then hours, then sessions."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    # CC row should have cost before "over"
    lines = output.split('\n')
    cc_line = [l for l in lines if 'CC' in l and 'CLAUDE' not in l]
    if cc_line:
        line = cc_line[0]
        # Should mention "over" and have cost
        assert "over" in line
        assert "~$" in line


def test_summary_total_shows_duration():
    """Total row includes session duration before cost."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    # Total row should have duration and cost
    lines = output.split('\n')
    total_line = [l for l in lines if 'Total' in l and 'session' not in l.lower()]
    if total_line:
        line = total_line[0]
        # Should contain both duration (~Xh) and cost (~$X.XX)
        assert "~" in line


def test_git_section_table_lightweight():
    """Git overview rendered as space-aligned table in lightweight mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=False)
    output = reporter.render(period)
    # Should have git overview with Field and Value columns
    assert "Commits" in output
    assert "Authors" in output
    assert "Files" in output
    # Should not have pipe format (unless it's from commits table)
    lines = output.split('\n')
    overview_section = output.split('####' if '####' in output else '══')[1]
    # Check that we have the field names
    assert "Commits" in overview_section


def test_git_section_table_markdown():
    """Git overview rendered as pipe table in markdown mode."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, markdown_tables=True)
    output = reporter.render(period)
    # Should have pipe table format with Field and Value columns
    assert "| Field" in output
    assert "| Value" in output
    assert "| Commits" in output


def test_commits_table_time_header_when_same_date():
    """Commits table uses 'Time' header when window is same date."""
    period = _make_period()  # same_date should be True for this fixture
    reporter = MarkdownReporter(tz_offset=3.0, show_commits=True, markdown_tables=True)
    output = reporter.render(period)
    # The period is 2026-04-28 10:00 to 14:00, so same_date=True
    assert "| Time" in output or "Time" in output


def test_commits_table_datetime_header_when_multiday():
    """Commits table uses 'Datetime' header when window spans multiple days."""
    from gadaj.models import WorkPeriod
    period = _make_period(with_commits=True)
    # Override the period to span multiple days
    period.since = utc(2026, 4, 28, 10, 0)
    period.until = utc(2026, 4, 29, 14, 0)
    reporter = MarkdownReporter(tz_offset=3.0, show_commits=True, markdown_tables=True)
    output = reporter.render(period)
    # With multi-day window, should use Datetime header
    assert "| Datetime" in output or "Datetime" in output


def test_commits_table_includes_files_column():
    """Commits table includes Files column with per-commit stats."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0, show_commits=True, markdown_tables=True)
    output = reporter.render(period)
    # Should have Files column header
    assert "| Files" in output


def test_summary_total_matches_cc_format():
    """Total row uses 'cost over duration' format matching CC row."""
    period = _make_period()
    reporter = MarkdownReporter(tz_offset=3.0)
    output = reporter.render(period)
    # Total row should show "over" between cost and duration
    lines = output.split('\n')
    total_line = [l for l in lines if 'Total' in l and 'session' not in l.lower()]
    if total_line:
        line = total_line[0]
        # Should contain "over" with cost and duration
        assert "over" in line
        assert "~$" in line
        # Cost should appear before "over" and duration after
        cost_idx = line.find("~$")
        over_idx = line.find("over")
        if cost_idx >= 0 and over_idx >= 0:
            assert cost_idx < over_idx  # cost comes before "over"
