from __future__ import annotations

from gadaj.table import Col, Table, _pad, _vlen


# ---------------------------------------------------------------------------
# _vlen and _pad helpers

def test_vlen_plain_text():
    assert _vlen("hello") == 5


def test_vlen_strips_ansi():
    # Cyan color code: \x1b[36m
    assert _vlen("\x1b[36mhello\x1b[0m") == 5


def test_vlen_multiple_ansi():
    # Multiple escape codes
    text = "\x1b[2mfoo\x1b[0m\x1b[36mbar\x1b[0m"
    assert _vlen(text) == 6


def test_pad_left_align():
    result = _pad("hi", 5, "left")
    assert result == "hi   "
    assert _vlen(result) == 5


def test_pad_right_align():
    result = _pad("hi", 5, "right")
    assert result == "   hi"
    assert _vlen(result) == 5


def test_pad_with_ansi_left():
    text = "\x1b[36mhi\x1b[0m"
    result = _pad(text, 5, "left")
    # Visual length 2 + 3 spaces = 5
    assert _vlen(result) == 5


def test_pad_no_extra():
    result = _pad("hello", 5, "left")
    assert result == "hello"


# ---------------------------------------------------------------------------
# Table class

def test_table_single_row():
    table = Table(Col("Name"), Col("Age", "right")).add_row("Alice", "30")
    lines = table.render(markdown=False)
    assert len(lines) == 2  # header + data
    assert "Name" in lines[0]
    assert "Alice" in lines[1]


def test_table_dynamic_width():
    table = Table(Col("Name"), Col("Value", "right"))
    table.add_row("x", "1")
    table.add_row("verylongname", "999")
    lines = table.render(markdown=False)
    # The Name column should be at least 12 chars (len("verylongname"))
    # Visual check: verylongname should be in the table
    full = "\n".join(lines)
    assert "verylongname" in full


def test_table_markdown_render():
    table = Table(Col("A"), Col("B", "right")).add_row("x", "1").add_row("y", "2")
    lines = table.render(markdown=True)
    # First line: header with pipes
    assert lines[0].startswith("|")
    assert "A" in lines[0]
    # Second line: alignment separators
    assert lines[1].startswith("|")
    assert "---" in lines[1]
    # Data rows
    assert "|" in lines[2]
    assert "x" in lines[2]


def test_table_right_align_markdown():
    table = Table(Col("Label"), Col("Value", "right")).add_row("Total", "100")
    lines = table.render(markdown=True)
    # Alignment row should have "---:" for right-aligned column
    assert "---:" in lines[1]


def test_table_separator_lightweight():
    table = Table(Col("A"), Col("B")).add_row("x", "1").add_separator().add_row("y", "2")
    lines = table.render(markdown=False)
    # Should have: header, data row, separator row (─), data row
    assert len(lines) == 4
    # Separator row contains dashes
    assert "─" in lines[2]


def test_table_separator_markdown_skipped():
    table = Table(Col("A"), Col("B")).add_row("x", "1").add_separator().add_row("y", "2")
    lines = table.render(markdown=True)
    # Separator rows (None) should be skipped in Markdown output
    # Should have: header, alignment, data row, data row (no separator row between data)
    assert len(lines) == 4  # | header | + | align | + data1 + data2
    full = "\n".join(lines)
    assert full.count("|") >= 10  # pipes from header, align, and both data rows


def test_table_max_width_truncates():
    table = Table(Col("Name"), Col("Message", max_width=5))
    table.add_row("Test", "Hello World Long")
    lines = table.render(markdown=False)
    full = "\n".join(lines)
    # Message should be truncated to 4 chars + ellipsis = "Hel…" (visual width 4)
    assert "…" in full


def test_table_max_width_ansi_preserved():
    # Colored text that exceeds max_width
    colored_text = "\x1b[31m" + "very long text" + "\x1b[0m"
    table = Table(Col("Data", max_width=5))
    table.add_row(colored_text)
    lines = table.render(markdown=False)
    full = "\n".join(lines)
    # Ellipsis should still be there even with ANSI codes
    assert "…" in full
    # And ANSI codes should be preserved
    assert "\x1b[" in full


def test_table_alignment_lightweight():
    table = Table(Col("Left"), Col("Right", "right")).add_row("a", "1").add_row("bb", "22")
    lines = table.render(markdown=False)
    # Left column: "a" padded, "bb" not padded
    # Right column: "1" padded, "22" not padded
    assert "a " in lines[1]  # "a" should have padding to match "bb"
    assert " 1" in lines[1]  # "1" should be right-aligned
    assert "22" in lines[2]


def test_table_chaining():
    table = (
        Table(Col("Name"), Col("Value", "right"))
        .add_row("A", "1")
        .add_row("B", "2")
        .add_separator()
        .add_row("Total", "3")
    )
    lines = table.render(markdown=False)
    assert len(lines) == 5  # header + 2 data + separator + total
