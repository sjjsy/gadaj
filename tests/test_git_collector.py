from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gadaj.collectors.git import GitCollector, _parse_log_stat, _parse_stat_summary
from gadaj.config import Config, _DEFAULT_AUTHORS, _DEFAULT_PRICING
from tests.conftest import utc

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _default_cfg() -> Config:
    return Config(authors=dict(_DEFAULT_AUTHORS), pricing=dict(_DEFAULT_PRICING))


def _make_runner(stdout: str, returncode: int = 0):
    """Return a fake subprocess.run that returns the given stdout."""
    def runner(cmd, **kwargs):
        result = MagicMock()
        result.stdout = stdout
        result.returncode = returncode
        return result
    return runner


# ---------------------------------------------------------------------------
# _parse_stat_summary

def test_parse_stat_summary_full():
    line = "3 files changed, 10 insertions(+), 5 deletions(-)"
    assert _parse_stat_summary(line) == (3, 10, 5)


def test_parse_stat_summary_insertions_only():
    line = "1 file changed, 67 insertions(+)"
    assert _parse_stat_summary(line) == (1, 67, 0)


def test_parse_stat_summary_empty():
    assert _parse_stat_summary("") == (0, 0, 0)


# ---------------------------------------------------------------------------
# _parse_log_stat

def test_parse_log_stat_basic(sample_git_log):
    cfg = _default_cfg()
    commits = _parse_log_stat(sample_git_log, cfg)
    assert len(commits) == 9  # 9 commits in fixture

    # All authors should be resolved to nicks
    authors = {c.author for c in commits}
    assert "Samuel" in authors
    assert "Mikko" in authors

    # First commit is the old one outside any recent window
    assert commits[0].hash == "f4b7d3e"
    assert commits[0].author == "Mikko"

    # Second is first in-window commit
    assert commits[1].hash == "51d38b6"
    assert commits[1].author == "Samuel"
    assert commits[1].files_changed == 2
    assert commits[1].insertions == 40
    assert commits[1].deletions == 0


def test_parse_log_stat_datetime(sample_git_log):
    cfg = _default_cfg()
    commits = _parse_log_stat(sample_git_log, cfg)
    first_in_window = commits[1]
    # Unix timestamp 1777370520 = 2026-04-28 10:02:00 UTC
    assert first_in_window.datetime == utc(2026, 4, 28, 10, 2)


def test_parse_log_stat_models_with_changes(sample_git_log):
    cfg = _default_cfg()
    commits = _parse_log_stat(sample_git_log, cfg)
    # Commit with stat: 1 file changed, 6 insertions(+), 6 deletions(-)
    refactor = next(c for c in commits if c.hash == "7c4f891")
    assert refactor.files_changed == 1
    assert refactor.insertions == 6
    assert refactor.deletions == 6


# ---------------------------------------------------------------------------
# GitCollector.collect() with fake runner

def test_git_collector_collect_with_fake_runner(sample_git_log):
    cfg = _default_cfg()
    runner = _make_runner(sample_git_log)
    collector = GitCollector(cfg=cfg, runner=runner)

    since = utc(2026, 4, 28, 10, 0)
    until = utc(2026, 4, 28, 14, 0)
    commits = collector.collect(since, until)

    assert len(commits) == 9


def test_git_collector_empty_output():
    cfg = _default_cfg()
    runner = _make_runner("")
    collector = GitCollector(cfg=cfg, runner=runner)

    commits = collector.collect(utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0))
    assert commits == []


def test_git_collector_nonzero_returncode():
    cfg = _default_cfg()
    runner = _make_runner("", returncode=128)
    collector = GitCollector(cfg=cfg, runner=runner)

    commits = collector.collect(utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0))
    assert commits == []


def test_git_collector_git_last_uses_count_arg():
    """GitCollector with git_last=5 should pass -5 to git."""
    cfg = _default_cfg()
    received_cmd = []

    def runner(cmd, **kwargs):
        received_cmd.extend(cmd)
        result = MagicMock()
        result.stdout = ""
        result.returncode = 0
        return result

    collector = GitCollector(cfg=cfg, git_last=5, runner=runner)
    collector.collect(utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0))
    assert "-5" in received_cmd


def test_git_collector_git_range_passes_range_arg():
    cfg = _default_cfg()
    received_cmd = []

    def runner(cmd, **kwargs):
        received_cmd.extend(cmd)
        result = MagicMock()
        result.stdout = ""
        result.returncode = 0
        return result

    collector = GitCollector(cfg=cfg, git_range="abc..def", runner=runner)
    collector.collect(utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0))
    assert "abc..def" in received_cmd


def test_git_collector_not_available_on_exception():
    """When git raises FileNotFoundError, collect returns empty list."""
    cfg = _default_cfg()

    def runner(cmd, **kwargs):
        raise FileNotFoundError("git not found")

    collector = GitCollector(cfg=cfg, runner=runner)
    commits = collector.collect(utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0))
    assert commits == []
