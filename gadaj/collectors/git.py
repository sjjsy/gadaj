from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Callable

from gadaj.collectors.base import Collector
from gadaj.config import Config, resolve_nick
from gadaj.models import Commit

# Sentinel prefix used to split git log --stat output into per-commit blocks.
_COMMIT_PREFIX = "GADAJ:"


class GitCollector(Collector):
    """Collect commits from the current git repository."""

    def __init__(
        self,
        cfg: Config,
        git_range: str | None = None,
        git_last: int | None = None,
        git_author: str | None = None,
        git_filter: str | None = None,
        runner: Callable = subprocess.run,
    ):
        self._cfg = cfg
        self._git_range = git_range
        self._git_last = git_last
        self._git_author = git_author
        self._git_filter = git_filter
        self._run = runner

    @property
    def source_name(self) -> str:
        return "GIT"

    @property
    def available(self) -> bool:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                timeout=5,
            )
            return r.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    def collect(self, since: datetime, until: datetime) -> list[Commit]:
        extra_args: list[str] = []

        if self._git_range:
            extra_args.append(self._git_range)
        elif self._git_last is not None:
            extra_args.append(f"-{self._git_last}")
        else:
            # Pass with explicit UTC offset so git does not interpret as local time
            extra_args += [
                f"--after={since.strftime('%Y-%m-%dT%H:%M:%S+00:00')}",
                f"--before={until.strftime('%Y-%m-%dT%H:%M:%S+00:00')}",
            ]

        if self._git_author:
            extra_args.append(f"--author={self._git_author}")

        if self._git_filter:
            extra_args += [f"--grep={self._git_filter}", "-i"]

        cmd = [
            "git", "log",
            f"--format={_COMMIT_PREFIX}%h\t%at\t%an\t%s",
            "--stat",
            "--reverse",
        ] + extra_args

        try:
            result = self._run(cmd, capture_output=True, text=True, timeout=30)
        except (FileNotFoundError, OSError) as e:
            print(f"warning: git not available: {e}", file=sys.stderr)
            return []
        except subprocess.TimeoutExpired:
            print("warning: git log timed out", file=sys.stderr)
            return []

        if result.returncode != 0:
            return []

        return _parse_log_stat(result.stdout, self._cfg)


def _parse_log_stat(output: str, cfg: Config) -> list[Commit]:
    """Parse output of `git log --format=GADAJ:... --stat`."""
    commits: list[Commit] = []
    # Split on lines starting with the sentinel prefix
    blocks = re.split(rf"^{_COMMIT_PREFIX}", output, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if not lines:
            continue

        parts = lines[0].split("\t", 3)
        if len(parts) < 4:
            continue
        h, dt_str, raw_author, message = parts

        try:
            dt = datetime.fromtimestamp(int(dt_str), tz=timezone.utc)
        except (ValueError, OSError):
            continue

        author = resolve_nick(raw_author, cfg)

        # The stat summary line is the last non-empty line of the block.
        stat_line = ""
        for line in reversed(lines[1:]):
            stripped = line.strip()
            if stripped:
                stat_line = stripped
                break

        files_changed, insertions, deletions = _parse_stat_summary(stat_line)
        commits.append(
            Commit(
                hash=h,
                datetime=dt,
                author=author,
                message=message,
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions,
            )
        )
    return commits


def _parse_stat_summary(line: str) -> tuple[int, int, int]:
    """Parse '3 files changed, 10 insertions(+), 5 deletions(-)' → (3, 10, 5)."""
    files_m = re.search(r"(\d+) files? changed", line)
    ins_m = re.search(r"(\d+) insertion", line)
    del_m = re.search(r"(\d+) deletion", line)
    return (
        int(files_m.group(1)) if files_m else 0,
        int(ins_m.group(1)) if ins_m else 0,
        int(del_m.group(1)) if del_m else 0,
    )
