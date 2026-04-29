from __future__ import annotations

from pathlib import Path

import pytest

from gadaj.config import Config, lookup_pricing, resolve_nick, _DEFAULT_PRICING, _DEFAULT_AUTHORS


def _default_cfg() -> Config:
    return Config(
        authors=dict(_DEFAULT_AUTHORS),
        pricing=dict(_DEFAULT_PRICING),
    )


# ---------------------------------------------------------------------------
# resolve_nick

def test_resolve_nick_known():
    cfg = _default_cfg()
    assert resolve_nick("Samuel Sydänlammi", cfg) == "Samuel"


def test_resolve_nick_unknown():
    cfg = _default_cfg()
    assert resolve_nick("Unknown Person", cfg) == "Unknown Person"


def test_resolve_nick_mikko():
    cfg = _default_cfg()
    assert resolve_nick("Mikko Lastname", cfg) == "Mikko"


# ---------------------------------------------------------------------------
# lookup_pricing

def test_lookup_pricing_exact():
    cfg = _default_cfg()
    p = lookup_pricing("claude-sonnet-4-6", cfg)
    assert p == (3.00, 15.00, 3.75, 0.300)


def test_lookup_pricing_versioned_suffix():
    cfg = _default_cfg()
    p = lookup_pricing("claude-sonnet-4-6-20250514", cfg)
    assert p is not None
    assert p[0] == 3.00  # input price matches claude-sonnet-4-6


def test_lookup_pricing_unknown():
    cfg = _default_cfg()
    p = lookup_pricing("gpt-4o", cfg)
    assert p is None


def test_lookup_pricing_haiku_versioned():
    cfg = _default_cfg()
    p = lookup_pricing("claude-haiku-4-5-20251001", cfg)
    assert p is not None
    assert p[0] == 0.80


def test_lookup_pricing_prefix_longest_wins():
    """Versioned haiku should match exact key, not shorter claude-haiku-4-5."""
    cfg = _default_cfg()
    # claude-haiku-4-5-20251001 is in pricing exactly
    p = lookup_pricing("claude-haiku-4-5-20251001-extra", cfg)
    assert p is not None
    assert p[0] == 0.80


# ---------------------------------------------------------------------------
# Threshold defaults

def test_config_default_cost_warn():
    cfg = Config()
    assert cfg.cost_warn_usd == 1.0


def test_config_default_cost_alert():
    cfg = Config()
    assert cfg.cost_alert_usd == 5.0


# ---------------------------------------------------------------------------
# TOML threshold loading

def test_apply_toml_thresholds(tmp_path):
    import sys
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            pytest.skip("tomllib/tomli not available")

    toml_file = tmp_path / "test.toml"
    toml_file.write_text(
        "[thresholds]\n"
        "cost_warn = 2.0\n"
        "cost_alert = 10.0\n"
    )

    cfg = Config()
    from gadaj.config import _apply_toml
    _apply_toml(cfg, toml_file)
    assert cfg.cost_warn_usd == 2.0
    assert cfg.cost_alert_usd == 10.0
