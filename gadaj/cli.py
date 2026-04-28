from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from gadaj.collectors.cc import CCCollector
from gadaj.collectors.git import GitCollector
from gadaj.config import load_config
from gadaj.models import CCSession, Commit, ContributorStats, WorkPeriod
from gadaj.reporters.json_ import JsonReporter
from gadaj.reporters.markdown import MarkdownReporter
from gadaj.utils import detect_tz_offset, fmt_duration, parse_since, parse_window


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gadaj",
        description=(
            "Aggregate git history and Claude Code sessions into a time-windowed work log.\n"
            "Default: last 4 hours, markdown output to stdout."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Time window
    window_group = parser.add_mutually_exclusive_group()
    window_group.add_argument(
        "-w", "--window",
        metavar="DURATION",
        help="look back from now: '2h', '1.5d', '90m' (default: 4h)",
    )
    window_group.add_argument(
        "-s", "--since",
        metavar="DATETIME",
        help=(
            "window start: ISO date/datetime, 'yesterday', 'today', "
            "'N hours ago', 'N days ago', weekday name"
        ),
    )
    parser.add_argument(
        "-u", "--until",
        metavar="DATETIME",
        default=None,
        help="window end (default: now); accepts same formats as --since",
    )

    # Git options
    parser.add_argument(
        "-g", "--git-range",
        metavar="A..B",
        help="explicit commit range, overrides time window for git",
    )
    parser.add_argument(
        "--git-last",
        metavar="N",
        type=int,
        help="last N commits, ignoring time window",
    )
    parser.add_argument(
        "-a", "--git-author",
        metavar="NAME",
        help="filter commits to this author (substring match)",
    )
    parser.add_argument(
        "-f", "--git-filter",
        metavar="PATTERN",
        help="filter commits by message (case-insensitive); path filtering not supported in v0.1",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="exclude git section",
    )

    # CC options
    parser.add_argument(
        "--cc-file",
        metavar="PATH",
        help="use a specific .jsonl instead of scanning by time",
    )
    parser.add_argument(
        "--no-cc",
        action="store_true",
        help="exclude Claude Code section",
    )

    # Output options
    parser.add_argument(
        "-c", "--commits",
        action="store_true",
        help="include full commits table (default: summary row only)",
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="machine-readable JSON output",
    )
    parser.add_argument(
        "-o", "--out",
        metavar="FILE",
        help="write output to FILE instead of stdout",
    )
    parser.add_argument(
        "-R", "--raw",
        action="store_true",
        help="raw token counts instead of abbreviated (debug)",
    )
    parser.add_argument(
        "-z", "--tz",
        metavar="HOURS",
        default=None,
        help=(
            "UTC offset override, e.g. '3', '+2', '-5', or 'auto' "
            "(default: auto-detected; fallback: 3.0 = EEST)"
        ),
    )

    return parser.parse_args(argv)


def aggregate(
    commits: list[Commit],
    cc_sessions: list[CCSession],
    since: datetime,
    until: datetime,
) -> WorkPeriod:
    period = WorkPeriod(since=since, until=until)
    period.commits = commits
    period.cc_sessions = cc_sessions

    # Git totals
    for c in commits:
        period.files_changed += c.files_changed
        period.insertions += c.insertions
        period.deletions += c.deletions

    # Human contributors
    human_commits: dict[str, int] = {}
    for c in commits:
        human_commits[c.author] = human_commits.get(c.author, 0) + 1
    for nick, count in human_commits.items():
        period.contributors[nick] = ContributorStats(
            name=nick,
            kind="human",
            model=None,
            sessions=0,
            commits=count,
            cost_usd=0.0,
        )

    # AI contributors — one entry per model, sessions counted per-session
    model_sessions: dict[str, int] = {}
    model_cost: dict[str, float] = {}
    for sess in cc_sessions:
        for model, usage in sess.models.items():
            model_sessions[model] = model_sessions.get(model, 0) + 1
            model_cost[model] = model_cost.get(model, 0.0) + usage.cost_usd
    for model in model_sessions:
        period.contributors[model] = ContributorStats(
            name=model,
            kind="ai",
            model=model,
            sessions=model_sessions[model],
            commits=0,
            cost_usd=model_cost[model],
        )

    period.total_cost_usd = sum(
        c.cost_usd for c in period.contributors.values() if c.kind == "ai"
    )

    return period


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    cfg = load_config()

    # Resolve tz_offset
    tz_source = args.tz if args.tz is not None else cfg.tz_offset
    if tz_source == "auto":
        tz_offset = detect_tz_offset()
    else:
        try:
            tz_offset = float(str(tz_source).lstrip("+"))
            # Handle negative sign properly
            if str(tz_source).startswith("-"):
                tz_offset = -tz_offset
        except (ValueError, TypeError):
            tz_offset = detect_tz_offset()

    # Resolve time window
    now = datetime.now(timezone.utc)

    if args.since:
        try:
            since = parse_since(args.since, now)
        except ValueError as e:
            print(f"error: --since: {e}", file=sys.stderr)
            sys.exit(2)
    elif args.window:
        try:
            delta = parse_window(args.window)
        except ValueError as e:
            print(f"error: --window: {e}", file=sys.stderr)
            sys.exit(2)
        since = now - delta
    else:
        since = now - parse_window(cfg.default_window)

    until = now
    if args.until:
        try:
            until = parse_since(args.until, now)
        except ValueError as e:
            print(f"error: --until: {e}", file=sys.stderr)
            sys.exit(2)

    # Collect
    commits: list[Commit] = []
    cc_sessions: list[CCSession] = []

    if not args.no_git:
        git_collector = GitCollector(
            cfg=cfg,
            git_range=args.git_range,
            git_last=args.git_last,
            git_author=args.git_author,
            git_filter=args.git_filter,
        )
        if git_collector.available:
            try:
                commits = git_collector.collect(since, until)
            except Exception as e:
                print(f"warning: git collection failed: {e}", file=sys.stderr)
        else:
            print("warning: not a git repo or git not found", file=sys.stderr)

    if not args.no_cc:
        cc_collector = CCCollector(cfg=cfg, cc_file=args.cc_file)
        if cc_collector.available:
            try:
                cc_sessions = cc_collector.collect(since, until)
            except Exception as e:
                print(f"warning: CC collection failed: {e}", file=sys.stderr)
        else:
            if args.cc_file:
                print(f"warning: --cc-file not found: {args.cc_file}", file=sys.stderr)
            else:
                print(
                    "warning: no Claude Code session directory found for this project",
                    file=sys.stderr,
                )

    period = aggregate(commits, cc_sessions, since, until)

    # Report
    if args.json:
        reporter: MarkdownReporter | JsonReporter = JsonReporter()
    else:
        reporter = MarkdownReporter(
            tz_offset=tz_offset,
            show_commits=args.commits,
            show_raw=args.raw,
        )

    output = reporter.render(period)

    if args.out:
        try:
            Path(args.out).write_text(output)
        except OSError as e:
            print(f"error: could not write to {args.out}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)
