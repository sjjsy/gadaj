from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from gadaj.cli import main, parse_args
from gadaj.collectors.cc import CCCollector
from gadaj.collectors.git import GitCollector
from gadaj.models import Commit
from tests.conftest import utc


def _make_commit(
    hash="abc1234",
    author="Samuel",
    datetime_=None,
    files=2,
    ins=10,
    dels=1,
):
    return Commit(
        hash=hash,
        datetime=datetime_ or utc(2026, 4, 28, 10, 0),
        author=author,
        message="Test commit",
        files_changed=files,
        insertions=ins,
        deletions=dels,
    )


# Test parse_args (basic sanity)
def test_parse_args_git_range():
    args = parse_args(["-g", "HEAD~3..HEAD"])
    assert args.git_range == "HEAD~3..HEAD"


def test_parse_args_window_and_git_range():
    args = parse_args(["-g", "HEAD~3..HEAD", "-w", "2h"])
    assert args.git_range == "HEAD~3..HEAD"
    assert args.window == "2h"


# Test main() with git-range-derived window
def test_main_git_range_derives_window_from_commits():
    """When --git-range is given without explicit window, CC window should match commit timestamps."""
    # Setup: commits spanning 10:00 to 14:00
    commits = [
        _make_commit("a1", datetime_=utc(2026, 4, 28, 10, 0)),
        _make_commit("a2", datetime_=utc(2026, 4, 28, 12, 0)),
        _make_commit("a3", datetime_=utc(2026, 4, 28, 14, 0)),
    ]

    cc_collector_collect_called_with = {}

    def mock_cc_collect(since, until):
        cc_collector_collect_called_with["since"] = since
        cc_collector_collect_called_with["until"] = until
        return []

    with patch("gadaj.cli.GitCollector") as mock_git_cls, \
         patch("gadaj.cli.CCCollector") as mock_cc_cls, \
         patch("gadaj.cli.MarkdownReporter") as mock_reporter_cls:

        # Setup GitCollector mock
        mock_git_instance = MagicMock()
        mock_git_instance.available = True
        mock_git_instance.collect.return_value = commits
        mock_git_cls.return_value = mock_git_instance

        # Setup CCCollector mock
        mock_cc_instance = MagicMock()
        mock_cc_instance.available = True
        mock_cc_instance.collect = mock_cc_collect
        mock_cc_cls.return_value = mock_cc_instance

        # Setup MarkdownReporter mock
        mock_reporter = MagicMock()
        mock_reporter.render.return_value = "output"
        mock_reporter_cls.return_value = mock_reporter

        # Run with --git-range but no explicit window
        main(["-g", "HEAD~3..HEAD"])

        # Check that CCCollector was called with timestamps from commits
        assert cc_collector_collect_called_with["since"] == utc(2026, 4, 28, 10, 0)
        assert cc_collector_collect_called_with["until"] == utc(2026, 4, 28, 14, 0)


def test_main_git_range_with_explicit_window_ignores_commits():
    """When --git-range is given WITH explicit window (-w), window should not be derived from commits."""
    # Setup: commits spanning 10:00 to 14:00
    commits = [
        _make_commit("a1", datetime_=utc(2026, 4, 28, 10, 0)),
        _make_commit("a2", datetime_=utc(2026, 4, 28, 14, 0)),
    ]

    cc_collector_collect_called_with = {}

    def mock_cc_collect(since, until):
        cc_collector_collect_called_with["since"] = since
        cc_collector_collect_called_with["until"] = until
        return []

    # -w 1h should result in window of 1 hour, not 10:00-14:00
    with patch("gadaj.cli.GitCollector") as mock_git_cls, \
         patch("gadaj.cli.CCCollector") as mock_cc_cls, \
         patch("gadaj.cli.MarkdownReporter") as mock_reporter_cls, \
         patch("gadaj.cli.datetime") as mock_datetime:

        # Mock datetime.now to return a known time
        now_time = utc(2026, 4, 28, 15, 0)
        mock_datetime.now.return_value = now_time
        mock_datetime.fromtimestamp = datetime.fromtimestamp  # Use real implementation for other calls
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Setup GitCollector mock
        mock_git_instance = MagicMock()
        mock_git_instance.available = True
        mock_git_instance.collect.return_value = commits
        mock_git_cls.return_value = mock_git_instance

        # Setup CCCollector mock
        mock_cc_instance = MagicMock()
        mock_cc_instance.available = True
        mock_cc_instance.collect = mock_cc_collect
        mock_cc_cls.return_value = mock_cc_instance

        # Setup MarkdownReporter mock
        mock_reporter = MagicMock()
        mock_reporter.render.return_value = "output"
        mock_reporter_cls.return_value = mock_reporter

        # Run with --git-range AND -w 1h
        main(["-g", "HEAD~3..HEAD", "-w", "1h"])

        # Window should be 1h (14:00-15:00), not the commit range (10:00-14:00)
        until = cc_collector_collect_called_with["until"]
        since = cc_collector_collect_called_with["since"]
        window_duration = (until - since).total_seconds() / 3600
        # Should be approximately 1 hour (might be slightly different due to parsing)
        assert 0.9 < window_duration < 1.1


def test_main_git_range_with_explicit_since_ignores_commits():
    """When --git-range is given WITH explicit -s (since), window should not be derived."""
    commits = [
        _make_commit("a1", datetime_=utc(2026, 4, 28, 10, 0)),
        _make_commit("a2", datetime_=utc(2026, 4, 28, 14, 0)),
    ]

    cc_collector_collect_called_with = {}

    def mock_cc_collect(since, until):
        cc_collector_collect_called_with["since"] = since
        cc_collector_collect_called_with["until"] = until
        return []

    with patch("gadaj.cli.GitCollector") as mock_git_cls, \
         patch("gadaj.cli.CCCollector") as mock_cc_cls, \
         patch("gadaj.cli.MarkdownReporter") as mock_reporter_cls:

        # Setup mocks
        mock_git_instance = MagicMock()
        mock_git_instance.available = True
        mock_git_instance.collect.return_value = commits
        mock_git_cls.return_value = mock_git_instance

        mock_cc_instance = MagicMock()
        mock_cc_instance.available = True
        mock_cc_instance.collect = mock_cc_collect
        mock_cc_cls.return_value = mock_cc_instance

        mock_reporter = MagicMock()
        mock_reporter.render.return_value = "output"
        mock_reporter_cls.return_value = mock_reporter

        # Run with --git-range and explicit -s
        main(["-g", "HEAD~3..HEAD", "-s", "2026-04-27"])

        # Window should start from 2026-04-27, not 10:00
        since = cc_collector_collect_called_with["since"]
        assert since.day == 27  # From explicit -s


def test_main_git_range_with_explicit_until_ignores_commits():
    """When --git-range is given WITH explicit -u (until), window should not be derived."""
    commits = [
        _make_commit("a1", datetime_=utc(2026, 4, 28, 10, 0)),
        _make_commit("a2", datetime_=utc(2026, 4, 28, 14, 0)),
    ]

    cc_collector_collect_called_with = {}

    def mock_cc_collect(since, until):
        cc_collector_collect_called_with["since"] = since
        cc_collector_collect_called_with["until"] = until
        return []

    with patch("gadaj.cli.GitCollector") as mock_git_cls, \
         patch("gadaj.cli.CCCollector") as mock_cc_cls, \
         patch("gadaj.cli.MarkdownReporter") as mock_reporter_cls:

        # Setup mocks
        mock_git_instance = MagicMock()
        mock_git_instance.available = True
        mock_git_instance.collect.return_value = commits
        mock_git_cls.return_value = mock_git_instance

        mock_cc_instance = MagicMock()
        mock_cc_instance.available = True
        mock_cc_instance.collect = mock_cc_collect
        mock_cc_cls.return_value = mock_cc_instance

        mock_reporter = MagicMock()
        mock_reporter.render.return_value = "output"
        mock_reporter_cls.return_value = mock_reporter

        # Run with --git-range and explicit -u
        main(["-g", "HEAD~3..HEAD", "-u", "2026-04-29"])

        # Window should end at 2026-04-29, not 14:00
        until = cc_collector_collect_called_with["until"]
        assert until.day == 29  # From explicit -u


def test_main_git_range_no_commits_no_derivation():
    """When --git-range finds no commits, CC window should not be derived (uses default)."""
    cc_collector_collect_called_with = {}

    def mock_cc_collect(since, until):
        cc_collector_collect_called_with["since"] = since
        cc_collector_collect_called_with["until"] = until
        return []

    with patch("gadaj.cli.GitCollector") as mock_git_cls, \
         patch("gadaj.cli.CCCollector") as mock_cc_cls, \
         patch("gadaj.cli.MarkdownReporter") as mock_reporter_cls:

        # Setup GitCollector to return empty list (no commits)
        mock_git_instance = MagicMock()
        mock_git_instance.available = True
        mock_git_instance.collect.return_value = []
        mock_git_cls.return_value = mock_git_instance

        mock_cc_instance = MagicMock()
        mock_cc_instance.available = True
        mock_cc_instance.collect = mock_cc_collect
        mock_cc_cls.return_value = mock_cc_instance

        mock_reporter = MagicMock()
        mock_reporter.render.return_value = "output"
        mock_reporter_cls.return_value = mock_reporter

        # Run with --git-range but it finds no commits
        main(["-g", "HEAD~100..HEAD~50"])

        # CC collect should have been called (so it was not skipped due to empty commits)
        assert "since" in cc_collector_collect_called_with
        assert "until" in cc_collector_collect_called_with
