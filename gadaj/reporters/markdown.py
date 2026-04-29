from __future__ import annotations

from datetime import timedelta

from gadaj.models import CCSession, WorkPeriod
from gadaj.utils import (
    fmt_cost,
    fmt_duration,
    fmt_hhmm,
    fmt_session_range,
    fmt_time_range,
    fmt_tok,
)

_WIDTH = 70
_GAP_THRESHOLD_MINUTES = 30


class MarkdownReporter:

    def __init__(
        self,
        tz_offset: float,
        show_commits: bool = False,
        show_raw: bool = False,
    ):
        self.tz_offset = tz_offset
        self.show_commits = show_commits
        self.show_raw = show_raw

    def render(self, period: WorkPeriod) -> str:
        parts: list[str] = []

        git_section = self._git_section(period)
        if git_section:
            parts.append(git_section)

        cc_section = self._cc_section(period)
        if cc_section:
            parts.append(cc_section)

        parts.append(self._summary_section(period))

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Git section

    def _git_section(self, period: WorkPeriod) -> str | None:
        if not period.commits:
            return None

        time_range = fmt_time_range(period.since, period.until, self.tz_offset)
        lines = [_header("GIT", time_range), ""]

        # Commit summary
        n = len(period.commits)
        first_h = period.commits[0].hash
        last_h = period.commits[-1].hash
        commit_summary = (
            f"{n} · {first_h} – {last_h}" if n > 1 else f"1 · {first_h}"
        )
        lines.append(f"  Commits   {commit_summary}")

        # Authors
        author_counts: dict[str, int] = {}
        for c in period.commits:
            author_counts[c.author] = author_counts.get(c.author, 0) + 1
        authors_str = "  ".join(
            f"{name} ({count})" for name, count in sorted(author_counts.items())
        )
        lines.append(f"  Authors   {authors_str}")

        # Files
        if period.files_changed > 0:
            lines.append(
                f"  Files     {period.files_changed} changed"
                f" · +{period.insertions} / -{period.deletions}"
            )

        # Optional commits table
        if self.show_commits:
            lines.append("")
            lines.extend(self._commits_table(period))

        return "\n".join(lines)

    def _commits_table(self, period: WorkPeriod) -> list[str]:
        rows = [
            "| Hash      | Datetime         | Author  | Message                    |",
            "|-----------|------------------|---------|----------------------------|",
        ]
        for c in period.commits:
            dt_local = fmt_hhmm(c.datetime, self.tz_offset)
            date_local = (c.datetime + timedelta(hours=self.tz_offset)).strftime(
                "%Y-%m-%d"
            )
            rows.append(
                f"| `{c.hash:<7}` | {date_local} {dt_local} | {c.author:<7} | {c.message} |"
            )
        return rows

    # ------------------------------------------------------------------
    # CC section

    def _cc_section(self, period: WorkPeriod) -> str | None:
        if not period.cc_sessions:
            return None

        time_range = fmt_time_range(period.since, period.until, self.tz_offset)
        lines = [_header("CLAUDE CODE", time_range), ""]

        sessions = period.cc_sessions
        n = len(sessions)
        lines.append(f"  Sessions  {n} in window")
        lines.append("")

        # Detect parallel sessions (overlapping time ranges)
        parallel_flags = _mark_parallel(sessions)

        for i, sess in enumerate(sessions):
            label = f"Session {i + 1}"
            session_range = fmt_session_range(sess.start, sess.end, self.tz_offset)
            dur = fmt_duration(sess.end - sess.start)
            suffix = ""
            if parallel_flags[i]:
                suffix += "  [parallel]"
            if i == n - 1 and n > 1:
                suffix += "   ← most recent"
            lines.append(f"  {label:<10} {session_range}  {dur}{suffix}")

            # Gap to next session
            if i < n - 1:
                gap = sessions[i + 1].start - sess.end
                gap_min = gap.total_seconds() / 60
                if gap_min > _GAP_THRESHOLD_MINUTES:
                    lines.append(f"  ⚠ {gap_min:.0f}m gap")

        # Per-model usage table
        lines.append("")
        if self.show_raw:
            lines.extend(self._models_table_raw(sessions))
        else:
            lines.extend(self._models_table(sessions))

        return "\n".join(lines)

    def _models_table(self, sessions: list[CCSession]) -> list[str]:
        # Aggregate usage across sessions per model
        aggregated = _aggregate_model_usage(sessions)

        header = (
            f"  {'Model':<22}{'In':>7}{'Out':>7}{'Cache↑':>9}{'Cache↓':>9}{'Cost':>10}"
        )
        sep = "  " + "─" * (_WIDTH - 4)
        rows = [header]

        for model, (usage, cost) in sorted(aggregated.items()):
            rows.append(
                f"  {model:<22}"
                f"{fmt_tok(usage.input_tokens):>7}"
                f"{fmt_tok(usage.output_tokens):>7}"
                f"{fmt_tok(usage.cache_write_tokens):>9}"
                f"{fmt_tok(usage.cache_read_tokens):>9}"
                f"{fmt_cost(cost):>10}"
            )

        rows.append(sep)
        total_cost = sum(cost for _, (_, cost) in aggregated.items())
        n = len(sessions)
        session_label = f"{n} session{'s' if n != 1 else ''} total"
        rows.append(f"  {session_label:<22}{'':>7}{'':>7}{'':>9}{'':>9}{fmt_cost(total_cost):>10}")

        return rows

    def _models_table_raw(self, sessions: list[CCSession]) -> list[str]:
        aggregated = _aggregate_model_usage(sessions)
        rows = []
        for model, (usage, cost) in sorted(aggregated.items()):
            rows.append(f"  {model}:")
            rows.append(
                f"    input={usage.input_tokens:,}  output={usage.output_tokens:,}"
                f"  cache_write={usage.cache_write_tokens:,}"
                f"  cache_read={usage.cache_read_tokens:,}"
            )
            rows.append(
                f"    messages={usage.messages}  cost=${cost:.4f}"
            )
        return rows

    # ------------------------------------------------------------------
    # Summary section

    def _summary_section(self, period: WorkPeriod) -> str:
        time_range = fmt_time_range(period.since, period.until, self.tz_offset)
        window_dur = fmt_duration(period.until - period.since)

        lines = [_header("SUMMARY", ""), ""]
        lines.append(f"  Window    {window_dur}  ({time_range})")

        if period.commits:
            n = len(period.commits)
            author_counts: dict[str, int] = {}
            for c in period.commits:
                author_counts[c.author] = author_counts.get(c.author, 0) + 1
            authors_str = ", ".join(
                f"{name}" for name in sorted(author_counts)
            )
            lines.append(f"  Git       {n} commit{'s' if n != 1 else ''} · {authors_str}")
        else:
            lines.append("  Git       no commits in window")

        if period.cc_sessions:
            aggregated = _aggregate_model_usage(period.cc_sessions)
            models_str = ", ".join(sorted(aggregated))
            total_cost = period.total_cost_usd
            n_sess = len(period.cc_sessions)
            lines.append(
                f"  CC        {n_sess} session{'s' if n_sess != 1 else ''}"
                f" · {models_str} · {fmt_cost(total_cost)}"
            )
        else:
            lines.append("  CC        no sessions in window")

        lines.append(f"  Total     {fmt_cost(period.total_cost_usd):>{_WIDTH - 12}}")

        return "\n".join(lines)


# ------------------------------------------------------------------
# Helpers


def _header(source: str, time_range: str) -> str:
    if time_range:
        left = f"══ {source}  {time_range} "
    else:
        left = f"══ {source} "
    pad = max(1, _WIDTH - len(left))
    return left + "═" * pad


def _mark_parallel(sessions: list[CCSession]) -> list[bool]:
    flags = [False] * len(sessions)
    for i in range(len(sessions) - 1):
        if sessions[i + 1].start < sessions[i].end:
            flags[i] = True
            flags[i + 1] = True
    return flags


def _aggregate_model_usage(
    sessions: list[CCSession],
) -> dict[str, tuple[object, float]]:
    """Aggregate ModelUsage across sessions, returning {model: (summed_usage, total_cost)}."""
    from gadaj.models import ModelUsage

    totals: dict[str, dict] = {}
    for sess in sessions:
        for model, usage in sess.models.items():
            if model not in totals:
                totals[model] = {
                    "input": 0, "output": 0,
                    "cache_write": 0, "cache_read": 0,
                    "messages": 0, "cost": 0.0,
                }
            t = totals[model]
            t["input"] += usage.input_tokens
            t["output"] += usage.output_tokens
            t["cache_write"] += usage.cache_write_tokens
            t["cache_read"] += usage.cache_read_tokens
            t["messages"] += usage.messages
            t["cost"] += usage.cost_usd

    result: dict[str, tuple[ModelUsage, float]] = {}
    for model, t in totals.items():
        result[model] = (
            ModelUsage(
                input_tokens=t["input"],
                output_tokens=t["output"],
                cache_write_tokens=t["cache_write"],
                cache_read_tokens=t["cache_read"],
                messages=t["messages"],
                cost_usd=t["cost"],
            ),
            t["cost"],
        )
    return result
