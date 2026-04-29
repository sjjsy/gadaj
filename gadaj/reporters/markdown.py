from __future__ import annotations

from datetime import timedelta

from gadaj.colors import _Colors
from gadaj.models import CCSession, WorkPeriod
from gadaj.table import Col, Table
from gadaj.utils import (
    fmt_cost,
    fmt_duration,
    fmt_hhmm,
    fmt_session_range,
    fmt_time_range,
    fmt_tok,
    period_same_date,
)

_GAP_THRESHOLD_MINUTES = 30


class MarkdownReporter:

    def __init__(
        self,
        tz_offset: float,
        show_commits: bool = False,
        show_raw: bool = False,
        color: bool = False,
        cost_warn_usd: float = 1.0,
        cost_alert_usd: float = 5.0,
        markdown_tables: bool = False,
    ):
        self.tz_offset = tz_offset
        self.show_commits = show_commits
        self.show_raw = show_raw
        self.markdown_tables = markdown_tables
        self._c = _Colors(color, cost_warn_usd, cost_alert_usd)

    def _color_duration_in_range(self, range_str: str) -> str:
        """Extract and color the duration part (e.g. '~4.0h') in a formatted range string."""
        if "  ~" in range_str:
            parts = range_str.rsplit("  ~", 1)
            colored_dur = self._c.duration(f"~{parts[1]}")
            return f"{parts[0]}  {colored_dur}"
        return range_str

    def render(self, period: WorkPeriod) -> str:
        parts: list[str] = []
        same_date = period_same_date(period.since, period.until, self.tz_offset)

        git_section = self._git_section(period, same_date)
        if git_section:
            parts.append(git_section)

        cc_section = self._cc_section(period, same_date)
        if cc_section:
            parts.append(cc_section)

        parts.append(self._summary_section(period, same_date))

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Git section

    def _git_section(self, period: WorkPeriod, same_date: bool) -> str | None:
        if not period.commits:
            return None

        time_range = fmt_time_range(period.since, period.until, self.tz_offset, same_date)
        time_range = self._color_duration_in_range(time_range)
        lines = [_header("GIT", time_range, self.markdown_tables), ""]

        # Commit summary
        n = len(period.commits)
        first_h = period.commits[0].hash
        last_h = period.commits[-1].hash
        commit_summary = (
            f"{n} · {first_h} – {last_h}" if n > 1 else f"1 · {first_h}"
        )
        lines.append(f"  {self._c.dim('Commits')}   {commit_summary}")

        # Authors
        author_counts: dict[str, int] = {}
        for c in period.commits:
            author_counts[c.author] = author_counts.get(c.author, 0) + 1
        authors_str = "  ".join(
            f"{name} ({count})" for name, count in sorted(author_counts.items())
        )
        lines.append(f"  {self._c.dim('Authors')}   {authors_str}")

        # Files
        if period.files_changed > 0:
            lines.append(
                f"  {self._c.dim('Files')}     {period.files_changed} changed"
                f" · +{period.insertions} / -{period.deletions}"
            )

        # Optional commits table
        if self.show_commits:
            lines.append("")
            lines.extend(self._commits_table(period, same_date))

        return "\n".join(lines)

    def _commits_table(self, period: WorkPeriod, same_date: bool) -> list[str]:
        table = Table(
            Col("Hash"),
            Col("Datetime"),
            Col("Author"),
            Col("Message", max_width=50),
        )
        for c in period.commits:
            local_dt = c.datetime + timedelta(hours=self.tz_offset)
            if same_date:
                dt_str = local_dt.strftime("%H:%M")
            else:
                dt_str = local_dt.strftime("%Y-%m-%d %H:%M")
            table.add_row(f"`{c.hash}`", dt_str, c.author, c.message)
        return table.render(markdown=True, indent="  ")

    # ------------------------------------------------------------------
    # CC section

    def _cc_section(self, period: WorkPeriod, same_date: bool) -> str | None:
        if not period.cc_sessions:
            return None

        time_range = fmt_time_range(period.since, period.until, self.tz_offset, same_date)
        time_range = self._color_duration_in_range(time_range)
        lines = [_header("CLAUDE CODE", time_range, self.markdown_tables), ""]

        sessions = period.cc_sessions
        n = len(sessions)
        lines.append(f"  {self._c.dim('Sessions')}  {n} in window")
        lines.append("")

        # Detect parallel sessions (overlapping time ranges)
        parallel_flags = _mark_parallel(sessions)

        # Build sessions table
        table = Table(Col("#"), Col("Range"), Col("Notes"))
        for i, sess in enumerate(sessions):
            session_range = fmt_session_range(sess.start, sess.end, self.tz_offset, same_date)
            session_range = self._color_duration_in_range(session_range)
            notes = ""
            if parallel_flags[i]:
                notes += "[parallel]"
            if i == n - 1 and n > 1:
                if notes:
                    notes += "  ← most recent"
                else:
                    notes = "← most recent"
            # Gap to next session
            if i < n - 1:
                gap = sessions[i + 1].start - sess.end
                gap_min = gap.total_seconds() / 60
                if gap_min > _GAP_THRESHOLD_MINUTES:
                    if notes:
                        notes += f"  ⚠ {gap_min:.0f}m gap"
                    else:
                        notes = f"⚠ {gap_min:.0f}m gap"
            table.add_row(str(i + 1), session_range, notes)

        lines.extend(table.render(markdown=self.markdown_tables, indent="  "))

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

        table = Table(
            Col("Model"),
            Col("In", align="right"),
            Col("Out", align="right"),
            Col("Cache↑", align="right"),
            Col("Cache↓", align="right"),
            Col("Cost", align="right"),
        )

        for model, (usage, cost) in sorted(aggregated.items()):
            cost_str = self._c.cost(fmt_cost(cost), cost)
            table.add_row(
                model,
                fmt_tok(usage.input_tokens),
                fmt_tok(usage.output_tokens),
                fmt_tok(usage.cache_write_tokens),
                fmt_tok(usage.cache_read_tokens),
                cost_str,
            )

        table.add_separator()
        total_cost = sum(cost for _, (_, cost) in aggregated.items())
        n = len(sessions)
        session_label = f"{n} session{'s' if n != 1 else ''} total"
        total_cost_str = self._c.cost(fmt_cost(total_cost), total_cost)
        table.add_row(session_label, "", "", "", "", total_cost_str)

        return table.render(markdown=self.markdown_tables, indent="  ")

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

    def _summary_section(self, period: WorkPeriod, same_date: bool) -> str:
        time_range = fmt_time_range(period.since, period.until, self.tz_offset, same_date)
        time_range = self._color_duration_in_range(time_range)
        lines = [_header("SUMMARY", time_range, self.markdown_tables), ""]

        table = Table(Col("Source"), Col("Summary"))

        if period.commits:
            n = len(period.commits)
            author_counts: dict[str, int] = {}
            for c in period.commits:
                author_counts[c.author] = author_counts.get(c.author, 0) + 1
            authors_str = ", ".join(f"{name}" for name in sorted(author_counts))
            summary = f"{n} commit{'s' if n != 1 else ''} · {authors_str}"
            table.add_row("Git", summary)
        else:
            table.add_row("Git", "no commits in window")

        if period.cc_sessions:
            aggregated = _aggregate_model_usage(period.cc_sessions)
            models_str = ", ".join(sorted(aggregated))
            n_sess = len(period.cc_sessions)
            cost_str = self._c.cost(fmt_cost(period.total_cost_usd), period.total_cost_usd)
            summary = f"{n_sess} session{'s' if n_sess != 1 else ''} · {models_str} · {cost_str}"
            table.add_row("CC", summary)
        else:
            table.add_row("CC", "no sessions in window")

        total_cost_str = self._c.cost(fmt_cost(period.total_cost_usd), period.total_cost_usd)
        table.add_row("Total", total_cost_str)

        lines.extend(table.render(markdown=self.markdown_tables, indent="  "))
        return "\n".join(lines)


# ------------------------------------------------------------------
# Helpers


def _header(source: str, time_range: str = "", markdown_mode: bool = False) -> str:
    """Generate a section header in lightweight or Markdown format."""
    suffix = f"  {time_range}" if time_range else ""
    if markdown_mode:
        return f"#### {source}{suffix}"
    return f"══ {source}{suffix}"


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
