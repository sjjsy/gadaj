from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from gadaj.collectors.cc import CCCollector, _parse_session, _session_window
from gadaj.config import Config, _DEFAULT_AUTHORS, _DEFAULT_PRICING
from tests.conftest import utc

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _default_cfg() -> Config:
    return Config(authors=dict(_DEFAULT_AUTHORS), pricing=dict(_DEFAULT_PRICING))


# ---------------------------------------------------------------------------
# _session_window

def test_session_window_sample(sample_jsonl_path):
    window = _session_window(sample_jsonl_path)
    assert window is not None
    start, end = window
    assert start == utc(2026, 4, 28, 10, 2)
    assert end == utc(2026, 4, 28, 11, 47, 20)


def test_session_window_nonexistent():
    result = _session_window(Path("/nonexistent/file.jsonl"))
    assert result is None


# ---------------------------------------------------------------------------
# _parse_session

def test_parse_session_basic(sample_jsonl_path):
    cfg = _default_cfg()
    sess = _parse_session(sample_jsonl_path, cfg)
    assert sess is not None
    assert sess.session_id == "sample"
    assert sess.start == utc(2026, 4, 28, 10, 2)
    assert sess.end == utc(2026, 4, 28, 11, 47, 20)


def test_parse_session_models(sample_jsonl_path):
    cfg = _default_cfg()
    sess = _parse_session(sample_jsonl_path, cfg)
    assert sess is not None
    assert "claude-sonnet-4-6" in sess.models
    assert "claude-haiku-4-5" in sess.models


def test_parse_session_cost_positive(sample_jsonl_path):
    cfg = _default_cfg()
    sess = _parse_session(sample_jsonl_path, cfg)
    assert sess is not None
    assert sess.total_cost_usd > 0


def test_parse_session_cache_tokens(sample_jsonl_path):
    cfg = _default_cfg()
    sess = _parse_session(sample_jsonl_path, cfg)
    assert sess is not None
    sonnet = sess.models["claude-sonnet-4-6"]
    assert sonnet.cache_write_tokens > 0


def test_parse_session_haiku_messages(sample_jsonl_path):
    cfg = _default_cfg()
    sess = _parse_session(sample_jsonl_path, cfg)
    assert sess is not None
    haiku = sess.models.get("claude-haiku-4-5")
    assert haiku is not None
    assert haiku.messages == 2


# ---------------------------------------------------------------------------
# CCCollector.collect() with injected projects_root

def _make_projects_root_with_session(
    tmp_path: Path, session_files: list[Path], cwd_hash: str
) -> Path:
    """Create a fake CC projects dir structure."""
    projects_root = tmp_path / "projects"
    project_dir = projects_root / cwd_hash
    project_dir.mkdir(parents=True)
    for src in session_files:
        shutil.copy(src, project_dir / src.name)
    return projects_root


def _cwd_hash() -> str:
    """The hash gadaj would derive for Path.cwd()."""
    return str(Path.cwd()).replace("/", "-")


def test_cc_collector_finds_session_in_window(tmp_path):
    cfg = _default_cfg()
    cwd_hash = _cwd_hash()
    projects_root = _make_projects_root_with_session(
        tmp_path,
        [FIXTURES_DIR / "sample.jsonl"],
        cwd_hash,
    )
    collector = CCCollector(cfg=cfg, projects_root=projects_root)
    sessions = collector.collect(
        since=utc(2026, 4, 28, 9, 0),
        until=utc(2026, 4, 28, 14, 0),
    )
    assert len(sessions) == 1
    assert sessions[0].session_id == "sample"


def test_cc_collector_excludes_session_outside_window(tmp_path):
    cfg = _default_cfg()
    cwd_hash = _cwd_hash()
    projects_root = _make_projects_root_with_session(
        tmp_path,
        [FIXTURES_DIR / "sample.jsonl"],
        cwd_hash,
    )
    collector = CCCollector(cfg=cfg, projects_root=projects_root)
    # Window is entirely before the session
    sessions = collector.collect(
        since=utc(2026, 4, 28, 8, 0),
        until=utc(2026, 4, 28, 9, 0),
    )
    assert sessions == []


def test_cc_collector_multi_session(tmp_path):
    cfg = _default_cfg()
    cwd_hash = _cwd_hash()
    projects_root = _make_projects_root_with_session(
        tmp_path,
        [FIXTURES_DIR / "sample.jsonl", FIXTURES_DIR / "sample2.jsonl"],
        cwd_hash,
    )
    collector = CCCollector(cfg=cfg, projects_root=projects_root)
    sessions = collector.collect(
        since=utc(2026, 4, 28, 9, 0),
        until=utc(2026, 4, 28, 14, 0),
    )
    assert len(sessions) == 2
    # Sorted ascending by start time
    assert sessions[0].start < sessions[1].start


def test_cc_collector_gap_between_sessions(tmp_path):
    """sample ends at 11:47, sample2 starts at 12:20 → 33-min gap > threshold."""
    cfg = _default_cfg()
    cwd_hash = _cwd_hash()
    projects_root = _make_projects_root_with_session(
        tmp_path,
        [FIXTURES_DIR / "sample.jsonl", FIXTURES_DIR / "sample2.jsonl"],
        cwd_hash,
    )
    collector = CCCollector(cfg=cfg, projects_root=projects_root)
    sessions = collector.collect(
        since=utc(2026, 4, 28, 9, 0),
        until=utc(2026, 4, 28, 14, 0),
    )
    assert len(sessions) == 2
    gap = sessions[1].start - sessions[0].end
    assert gap.total_seconds() / 60 > 30


def test_cc_collector_cc_file_override(sample_jsonl_path):
    cfg = _default_cfg()
    collector = CCCollector(cfg=cfg, cc_file=str(sample_jsonl_path))
    sessions = collector.collect(
        since=utc(2026, 4, 28, 9, 0),
        until=utc(2026, 4, 28, 14, 0),
    )
    assert len(sessions) == 1


def test_cc_collector_not_available_when_no_dir(tmp_path):
    cfg = _default_cfg()
    empty_root = tmp_path / "empty_projects"
    empty_root.mkdir()
    collector = CCCollector(cfg=cfg, projects_root=empty_root)
    assert not collector.available
