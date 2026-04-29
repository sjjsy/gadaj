"""Markdown/lightweight tabular formatter with ANSI-aware column widths."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Align = Literal["left", "right"]


def _vlen(s: str) -> int:
    """String length after stripping ANSI escape codes."""
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))


def _pad(s: str, width: int, align: Align) -> str:
    """Pad a string to visual width, accounting for ANSI codes."""
    extra = max(0, width - _vlen(s))
    return (s + " " * extra) if align == "left" else (" " * extra + s)


@dataclass
class Col:
    """Column definition: header, alignment, and optional max width."""

    header: str
    align: Align = "left"
    max_width: int = 0  # 0 = unconstrained


class Table:
    """Markdown/lightweight table formatter with ANSI-aware widths."""

    def __init__(self, *columns: Col) -> None:
        self._cols = list(columns)
        self._rows: list[list[str] | None] = []  # None = separator row

    def add_row(self, *cells: str) -> Table:
        """Add a data row. Returns self for chaining."""
        row = list(cells)
        # Truncate cells that exceed max_width
        for i, col in enumerate(self._cols):
            if col.max_width and i < len(row) and _vlen(row[i]) > col.max_width:
                # Truncate and add ellipsis
                clean = re.sub(r"\x1b\[[0-9;]*m", "", row[i])
                truncated = clean[: col.max_width - 1] + "…"
                # Preserve any leading ANSI codes from original
                match = re.match(r"(\x1b\[[0-9;]*m)*", row[i])
                prefix = match.group(0) if match else ""
                row[i] = prefix + truncated
        self._rows.append(row)
        return self

    def add_separator(self) -> Table:
        """Add a separator row (rendered as `─` line in lightweight, skipped in Markdown)."""
        self._rows.append(None)
        return self

    def _widths(self) -> list[int]:
        """Compute column widths: max(header, all data cells), respecting max_width."""
        widths = [_vlen(c.header) for c in self._cols]
        for row in self._rows:
            if row is None:
                continue
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], _vlen(cell))
        # Apply max_width constraints
        for i, col in enumerate(self._cols):
            if col.max_width:
                widths[i] = min(widths[i], col.max_width)
        return widths

    def render(self, markdown: bool = False, indent: str = "  ") -> list[str]:
        """Render table in lightweight or Markdown format."""
        widths = self._widths()
        lines = []

        if markdown:
            # Header row
            cells = [_pad(c.header, w, "left") for c, w in zip(self._cols, widths)]
            lines.append("| " + " | ".join(cells) + " |")
            # Alignment separator (standard Markdown: min 3 dashes)
            seps = []
            for c, w in zip(self._cols, widths):
                w = max(w, 3)  # Ensure minimum width for standard Markdown
                if c.align == "right":
                    seps.append("-" * (w - 1) + ":")
                else:
                    seps.append("-" * w)
            lines.append("| " + " | ".join(seps) + " |")
            # Data rows (skip separator placeholders)
            for data_row in self._rows:
                if data_row is None:
                    continue
                cells = [
                    _pad(data_row[j] if j < len(data_row) else "", w, self._cols[j].align)
                    for j, w in enumerate(widths)
                ]
                lines.append("| " + " | ".join(cells) + " |")
        else:
            # Lightweight: space-aligned
            # Header row
            cells = [_pad(c.header, w, c.align) for c, w in zip(self._cols, widths)]
            lines.append(indent + "  ".join(cells).rstrip())
            # Data rows
            for data_row in self._rows:
                if data_row is None:
                    lines.append(indent + "  ".join("─" * w for w in widths))
                    continue
                cells = [
                    _pad(data_row[j] if j < len(data_row) else "", w, self._cols[j].align)
                    for j, w in enumerate(widths)
                ]
                lines.append(indent + "  ".join(cells).rstrip())

        return lines
