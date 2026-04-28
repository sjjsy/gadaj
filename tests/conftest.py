from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def utc(year, month, day, hour=0, minute=0, second=0):
    """Convenience UTC datetime constructor."""
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


@pytest.fixture
def sample_git_log():
    return (FIXTURES_DIR / "sample_git_log.txt").read_text()


@pytest.fixture
def sample_jsonl_path():
    return FIXTURES_DIR / "sample.jsonl"


@pytest.fixture
def sample2_jsonl_path():
    return FIXTURES_DIR / "sample2.jsonl"
