from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]
from pathlib import Path
from typing import Literal

_CONFIG_DIR = Path.home() / ".config" / "gadaj"
_CONFIG_PATH = _CONFIG_DIR / "config.toml"

_DEFAULT_PRICING: dict[str, tuple[float, float, float, float]] = {
    "claude-opus-4-7":           (15.00, 75.00, 18.75, 1.500),
    "claude-opus-4-6":           (15.00, 75.00, 18.75, 1.500),
    "claude-sonnet-4-6":         ( 3.00, 15.00,  3.75, 0.300),
    "claude-haiku-4-5":          ( 0.80,  4.00,  1.00, 0.080),
    "claude-haiku-4-5-20251001": ( 0.80,  4.00,  1.00, 0.080),
}

_DEFAULT_AUTHORS: dict[str, str] = {
    "Samuel Sydänlammi": "Samuel",
    "Mikko Lastname":   "Mikko",
    "Vault":             "Vault",
}

_DEFAULT_CONFIG_TOML = """\
[authors]
"Samuel Sydänlammi" = "Samuel"
"Mikko Lastname"   = "Mikko"
"Vault"             = "Vault"

[pricing]
# (input, output, cache_write, cache_read) — $/MTok
"claude-opus-4-7"           = [15.00, 75.00, 18.75, 1.500]
"claude-opus-4-6"           = [15.00, 75.00, 18.75, 1.500]
"claude-sonnet-4-6"         = [3.00, 15.00, 3.75, 0.300]
"claude-haiku-4-5"          = [0.80, 4.00, 1.00, 0.080]
"claude-haiku-4-5-20251001" = [0.80, 4.00, 1.00, 0.080]

[defaults]
window = "4h"
tz     = "auto"   # or e.g. "2", "3"
"""


@dataclass
class Config:
    authors: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_AUTHORS))
    pricing: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: dict(_DEFAULT_PRICING)
    )
    default_window: str = "4h"
    tz_offset: float | Literal["auto"] = "auto"


def load_config(cwd: Path | None = None) -> Config:
    """Load config: built-in defaults < user config < project config."""
    cfg = Config()

    if not _CONFIG_PATH.exists():
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            _CONFIG_PATH.write_text(_DEFAULT_CONFIG_TOML)
        except OSError:
            pass  # read-only filesystem — just use defaults

    _apply_toml(cfg, _CONFIG_PATH)

    project_cfg = (cwd or Path.cwd()) / ".gadaj.toml"
    if project_cfg.exists():
        _apply_toml(cfg, project_cfg)

    return cfg


def _apply_toml(cfg: Config, path: Path) -> None:
    if not path.exists():
        return
    if tomllib is None:
        print(
            "warning: TOML config requires Python 3.11+ or 'pip install tomli'. "
            "Using defaults.",
            file=sys.stderr,
        )
        return
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except OSError as e:
        print(f"warning: could not load config {path}: {e}", file=sys.stderr)
        return
    except Exception as e:  # TOMLDecodeError or similar
        print(f"warning: invalid TOML in {path}: {e}", file=sys.stderr)
        return

    if "authors" in data:
        cfg.authors.update(data["authors"])

    if "pricing" in data:
        for model, rates in data["pricing"].items():
            if isinstance(rates, list) and len(rates) == 4:
                cfg.pricing[model] = tuple(float(r) for r in rates)

    if "defaults" in data:
        defaults = data["defaults"]
        if "window" in defaults:
            cfg.default_window = str(defaults["window"])
        if "tz" in defaults:
            tz_val = str(defaults["tz"])
            if tz_val == "auto":
                cfg.tz_offset = "auto"
            else:
                try:
                    cfg.tz_offset = float(tz_val)
                except (ValueError, TypeError):
                    pass


def resolve_nick(raw_name: str, cfg: Config) -> str:
    return cfg.authors.get(raw_name, raw_name)


def lookup_pricing(
    model: str, cfg: Config
) -> tuple[float, float, float, float] | None:
    """Prefix matching: 'claude-sonnet-4-6-20250514' matches 'claude-sonnet-4-6'."""
    if model in cfg.pricing:
        return cfg.pricing[model]
    best_key: str | None = None
    best_len = 0
    for key in cfg.pricing:
        if model.startswith(key) and len(key) > best_len:
            best_key = key
            best_len = len(key)
    if best_key:
        return cfg.pricing[best_key]
    return None
