from __future__ import annotations

from gadaj.colors import _Colors


def test_colors_disabled_returns_plain():
    """When enabled=False, all color methods return plain text."""
    c = _Colors(enabled=False, cost_warn_usd=1.0, cost_alert_usd=5.0)
    assert c.dim("hello") == "hello"
    assert c.duration("~1.0h") == "~1.0h"
    assert c.cost("~$1.50", 1.50) == "~$1.50"


def test_colors_dim_wraps_ansi():
    """dim() wraps text in ANSI dim code."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.dim("label")
    assert "\x1b[2m" in result  # dim code
    assert "label" in result
    assert "\x1b[0m" in result  # reset code


def test_colors_duration_wraps_ansi():
    """duration() wraps text in ANSI cyan code."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.duration("~1.0h")
    assert "\x1b[36m" in result  # cyan code
    assert "~1.0h" in result
    assert "\x1b[0m" in result


def test_colors_cost_low_dim_yellow():
    """cost() with low value uses dim yellow."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.cost("~$0.50", 0.50)
    # Dim yellow: \x1b[2;33m
    assert "\x1b[2;33m" in result
    assert "~$0.50" in result


def test_colors_cost_warn_orange():
    """cost() in warning range uses dark golden amber (256-color)."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.cost("~$2.00", 2.00)
    # Dark golden amber: \x1b[38;5;136m
    assert "\x1b[38;5;136m" in result
    assert "~$2.00" in result


def test_colors_cost_alert_red():
    """cost() at or above alert threshold uses red."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.cost("~$6.00", 6.00)
    # Red: \x1b[31m
    assert "\x1b[31m" in result
    assert "~$6.00" in result


def test_colors_cost_boundary_warn():
    """cost() exactly at warn threshold uses dark golden amber."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.cost("~$1.00", 1.00)
    assert "\x1b[38;5;136m" in result


def test_colors_cost_boundary_alert():
    """cost() exactly at alert threshold uses red."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.cost("~$5.00", 5.00)
    assert "\x1b[31m" in result


def test_nums_wraps_blue():
    """nums() wraps text in blue ANSI code."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.nums("128k")
    assert "\x1b[34m" in result
    assert "128k" in result
    assert "\x1b[0m" in result


def test_nums_disabled():
    """nums() returns plain text when disabled."""
    c = _Colors(enabled=False, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.nums("128k")
    assert result == "128k"


def test_colorize_digits_colors_bare_numbers():
    """colorize_digits() colors uncolored digit sequences blue."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.colorize_digits("2026-04-28 10:30")
    # Should contain blue codes around digits
    assert "\x1b[34m" in result
    assert "2026" in result or "26" in result  # digits are somewhere in the string
    assert "\x1b[0m" in result


def test_colorize_digits_skips_inside_ansi_block():
    """colorize_digits() does not re-color digits inside existing ANSI blocks."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    # Create a string with cyan-colored duration
    colored_dur = f"\x1b[36m~4.0h\x1b[0m"
    input_str = f"2026-04-28  {colored_dur}"
    result = c.colorize_digits(input_str)
    # The date digits should be blue, but the 4.0 inside cyan should not be re-colored
    assert "\x1b[34m" in result  # date digits are blue
    assert colored_dur in result or "~4.0h" in result  # duration content is preserved
    # The final result should have the cyan color code
    assert "\x1b[36m" in result


def test_colorize_digits_disabled():
    """colorize_digits() is no-op when disabled."""
    c = _Colors(enabled=False, cost_warn_usd=1.0, cost_alert_usd=5.0)
    input_str = "2026-04-28 10:30"
    result = c.colorize_digits(input_str)
    assert result == input_str
    assert "\x1b" not in result
