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
        author_colors: list[str] | None = None,
        author_colors_map: dict[str, str] | None = None,
    ):
        self.tz_offset = tz_offset
        self.show_commits = show_commits
        self.show_raw = show_raw
        self.markdown_tables = markdown_tables
        self._c = _Colors(color, cost_warn_usd, cost_alert_usd)
        self._author_colors = author_colors or []
        self._author_colors_map = author_colors_map or {}

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
        time_range = self._c.colorize_digits(time_range)
        lines = [_header("GIT", time_range, self.markdown_tables), ""]

        # Build overview table
        table = Table(Col("Field"), Col("Value"))

        # Commit summary
        n = len(period.commits)
        first_h = period.commits[0].hash
        last_h = period.commits[-1].hash
        commit_summary = (
            f"{self._c.nums(str(n))} · {first_h} – {last_h}" if n > 1
            else f"{self._c.nums('1')} · {first_h}"
        )
        table.add_row(self._c.dim("Commits"), commit_summary)

        # Authors
        author_counts: dict[str, int] = {}
        for c in period.commits:
            author_counts[c.author] = author_counts.get(c.author, 0) + 1
        authors_str = "  ".join(
            f"{name} ({self._c.nums(str(count))})" for name, count in sorted(author_counts.items())
        )
        table.add_row(self._c.dim("Authors"), authors_str)

        # Files
        if period.files_changed > 0:
            files_str = (
                f"{self._c.nums(str(period.files_changed))} changed"
                f" · +{self._c.nums(str(period.insertions))} / -{self._c.nums(str(period.deletions))}"
            )
            table.add_row(self._c.dim("Files"), files_str)

        lines.extend(table.render(markdown=self.markdown_tables, indent="  "))

        # Optional commits table
        if self.show_commits:
            lines.append("")
            lines.extend(self._commits_table(period, same_date))

        return "\n".join(lines)

    def _commits_table(self, period: WorkPeriod, same_date: bool) -> list[str]:
        # Assign colors to authors: explicit mapping first, then palette
        author_map: dict[str, str] = {}
        palette_idx = 0
        for c in period.commits:
            if c.author not in author_map:
                # Check explicit mapping first
                if c.author in self._author_colors_map:
                    author_map[c.author] = self._author_colors_map[c.author]
                else:
                    # Fall back to palette in order of appearance
                    color = self._author_colors[palette_idx % len(self._author_colors)] if self._author_colors else ""
                    author_map[c.author] = color
                    palette_idx += 1

        # Check if commits themselves span multiple dates (not just the window)
        commits_same_date = same_date
        if period.commits and len(period.commits) > 1:
            first_local = period.commits[0].datetime + timedelta(hours=self.tz_offset)
            last_local = period.commits[-1].datetime + timedelta(hours=self.tz_offset)
            commits_same_date = first_local.date() == last_local.date()

        # Use "Time" for header when same_date, otherwise "Datetime"
        dt_header = "Time" if commits_same_date else "Datetime"
        table = Table(
            Col("Hash"),
            Col(dt_header),
            Col("Author"),
            Col("Files"),
            Col("Message", max_width=50),
        )
        for c in period.commits:
            local_dt = c.datetime + timedelta(hours=self.tz_offset)
            if commits_same_date:
                dt_str = local_dt.strftime("%H:%M")
            else:
                dt_str = local_dt.strftime("%Y-%m-%d %H:%M")
            dt_str = self._c.colorize_digits(dt_str)
            # Per-commit file stats (similar to git overview Files row)
            if c.files_changed > 0:
                files_str = (
                    f"{self._c.nums(str(c.files_changed))} · "
                    f"+{self._c.nums(str(c.insertions))} / -{self._c.nums(str(c.deletions))}"
                )
            else:
                files_str = ""
            colored_author = self._c.apply_code(c.author, author_map.get(c.author, ""))
            table.add_row(f"`{c.hash}`", dt_str, colored_author, files_str, c.message)
        return table.render(markdown=self.markdown_tables, indent="  ")

    # ------------------------------------------------------------------
    # CC section

    def _cc_section(self, period: WorkPeriod, same_date: bool) -> str | None:
        if not period.cc_sessions:
            return None

        time_range = fmt_time_range(period.since, period.until, self.tz_offset, same_date)
        time_range = self._color_duration_in_range(time_range)
        time_range = self._c.colorize_digits(time_range)
        lines = [_header("CLAUDE CODE", time_range, self.markdown_tables), ""]

        sessions = period.cc_sessions
        n = len(sessions)
        lines.append(f"  {self._c.dim('Sessions')}  {self._c.nums(str(n))} in window")
        lines.append("")

        # Detect parallel sessions (overlapping time ranges)
        parallel_flags = _mark_parallel(sessions)

        # Build sessions table
        table = Table(Col("#"), Col("Range"), Col("Notes"))
        for i, sess in enumerate(sessions):
            session_range = fmt_session_range(sess.start, sess.end, self.tz_offset, same_date)
            session_range = self._color_duration_in_range(session_range)
            session_range = self._c.colorize_digits(session_range)
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
                self._c.nums(fmt_tok(usage.input_tokens)),
                self._c.nums(fmt_tok(usage.output_tokens)),
                self._c.nums(fmt_tok(usage.cache_write_tokens)),
                self._c.nums(fmt_tok(usage.cache_read_tokens)),
                cost_str,
            )

        table.add_separator()
        total_cost = sum(cost for _, (_, cost) in aggregated.items())
        n = len(sessions)
        session_label = f"{self._c.nums(str(n))} session{'s' if n != 1 else ''} total"
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
        time_range = self._c.colorize_digits(time_range)
        lines = [_header("SUMMARY", time_range, self.markdown_tables), ""]

        table = Table(Col("Source"), Col("Summary"))

        # Git row: show span between first and last commit if multiple commits
        if period.commits:
            n = len(period.commits)
            author_counts: dict[str, int] = {}
            for c in period.commits:
                author_counts[c.author] = author_counts.get(c.author, 0) + 1
            authors_str = ", ".join(f"{name}" for name in sorted(author_counts))
            if n > 1:
                span = period.commits[-1].datetime - period.commits[0].datetime
                span_str = self._c.duration(fmt_duration(span))
                summary = f"{self._c.nums(str(n))} commits over {span_str} · {authors_str}"
            else:
                summary = f"{self._c.nums('1')} commit · {authors_str}"
            table.add_row("Git", summary)
        else:
            table.add_row("Git", "no commits in window")

        # CC row: cost first, then over X hours, then N sessions
        if period.cc_sessions:
            cost_str = self._c.cost(fmt_cost(period.total_cost_usd), period.total_cost_usd)
            n_sess = len(period.cc_sessions)
            # Calculate total session duration
            total_sess_dur = sum(
                (s.end - s.start for s in period.cc_sessions), timedelta()
            )
            dur_str = self._c.duration(fmt_duration(total_sess_dur))
            summary = (
                f"{cost_str} over {dur_str} from "
                f"{self._c.nums(str(n_sess))} session{'s' if n_sess != 1 else ''}"
            )
            table.add_row("CC", summary)
        else:
            table.add_row("CC", "no sessions in window")

        # Total row: cost over duration (matching CC row format)
        total_cost_str = self._c.cost(fmt_cost(period.total_cost_usd), period.total_cost_usd)
        if period.cc_sessions:
            total_sess_dur = sum(
                (s.end - s.start for s in period.cc_sessions), timedelta()
            )
            dur_str = self._c.duration(fmt_duration(total_sess_dur))
            table.add_row("Total", f"{total_cost_str} over {dur_str}")
        else:
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
