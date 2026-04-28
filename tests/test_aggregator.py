from __future__ import annotations

from pathlib import Path

import pytest

from gadaj.cli import aggregate
from gadaj.collectors.cc import _parse_session
from gadaj.collectors.git import _parse_log_stat
from gadaj.config import Config, _DEFAULT_AUTHORS, _DEFAULT_PRICING
from gadaj.models import CCSession, Commit, ModelUsage
from tests.conftest import utc

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _default_cfg() -> Config:
    return Config(authors=dict(_DEFAULT_AUTHORS), pricing=dict(_DEFAULT_PRICING))


def _make_commit(hash="abc1234", author="Samuel", files=2, ins=10, dels=1):
    return Commit(
        hash=hash,
        datetime=utc(2026, 4, 28, 10, 0),
        author=author,
        message="Test commit",
        files_changed=files,
        insertions=ins,
        deletions=dels,
    )


def _make_session(session_id="sess1", cost=1.5) -> CCSession:
    usage = ModelUsage(
        input_tokens=1000,
        output_tokens=500,
        cache_write_tokens=2000,
        cache_read_tokens=5000,
        messages=5,
        cost_usd=cost,
    )
    return CCSession(
        path=Path(f"/fake/{session_id}.jsonl"),
        session_id=session_id,
        start=utc(2026, 4, 28, 10, 0),
        end=utc(2026, 4, 28, 11, 30),
        models={"claude-sonnet-4-6": usage},
        total_cost_usd=cost,
    )


# ---------------------------------------------------------------------------

def test_aggregate_empty():
    since = utc(2026, 4, 28, 10, 0)
    until = utc(2026, 4, 28, 14, 0)
    period = aggregate([], [], since, until)
    assert period.since == since
    assert period.until == until
    assert period.total_cost_usd == 0.0
    assert period.files_changed == 0
    assert period.commits == []
    assert period.cc_sessions == []


def test_aggregate_git_totals():
    commits = [
        _make_commit("a1", files=2, ins=10, dels=1),
        _make_commit("a2", files=3, ins=20, dels=5),
    ]
    period = aggregate(commits, [], utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0))
    assert period.files_changed == 5
    assert period.insertions == 30
    assert period.deletions == 6


def test_aggregate_human_contributors():
    commits = [
        _make_commit("a1", author="Samuel"),
        _make_commit("a2", author="Samuel"),
        _make_commit("a3", author="Mikko"),
    ]
    period = aggregate(commits, [], utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0))
    assert "Samuel" in period.contributors
    assert "Mikko" in period.contributors
    assert period.contributors["Samuel"].commits == 2
    assert period.contributors["Mikko"].commits == 1
    assert period.contributors["Samuel"].kind == "human"


def test_aggregate_ai_contributors():
    sessions = [_make_session("s1", cost=2.0), _make_session("s2", cost=1.5)]
    period = aggregate([], sessions, utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0))
    assert "claude-sonnet-4-6" in period.contributors
    ai = period.contributors["claude-sonnet-4-6"]
    assert ai.kind == "ai"
    assert ai.sessions == 2
    assert abs(ai.cost_usd - 3.5) < 0.001


def test_aggregate_total_cost():
    sessions = [_make_session("s1", cost=2.0), _make_session("s2", cost=1.5)]
    period = aggregate([], sessions, utc(2026, 4, 28, 10, 0), utc(2026, 4, 28, 14, 0))
    assert abs(period.total_cost_usd - 3.5) < 0.001


def test_aggregate_with_fixtures():
    """End-to-end test using real fixture files."""
    cfg = _default_cfg()

    # Parse commits from fixture
    fixture_log = (FIXTURES_DIR / "sample_git_log.txt").read_text()
    commits = _parse_log_stat(fixture_log, cfg)

    # Parse sessions from fixtures
    sess1 = _parse_session(FIXTURES_DIR / "sample.jsonl", cfg)
    sess2 = _parse_session(FIXTURES_DIR / "sample2.jsonl", cfg)
    sessions = [s for s in [sess1, sess2] if s is not None]

    since = utc(2026, 4, 28, 10, 0)
    until = utc(2026, 4, 28, 14, 0)
    period = aggregate(commits, sessions, since, until)

    assert len(period.commits) == 9
    assert len(period.cc_sessions) == 2
    assert period.total_cost_usd > 0
    assert period.files_changed > 0
