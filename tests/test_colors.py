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
    """cost() in warning range uses yellow/orange."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.cost("~$2.00", 2.00)
    # Regular yellow: \x1b[33m (no dim)
    assert "\x1b[33m" in result
    assert "~$2.00" in result


def test_colors_cost_alert_red():
    """cost() at or above alert threshold uses red."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.cost("~$6.00", 6.00)
    # Red: \x1b[31m
    assert "\x1b[31m" in result
    assert "~$6.00" in result


def test_colors_cost_boundary_warn():
    """cost() exactly at warn threshold uses orange."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.cost("~$1.00", 1.00)
    assert "\x1b[33m" in result


def test_colors_cost_boundary_alert():
    """cost() exactly at alert threshold uses red."""
    c = _Colors(enabled=True, cost_warn_usd=1.0, cost_alert_usd=5.0)
    result = c.cost("~$5.00", 5.00)
    assert "\x1b[31m" in result
