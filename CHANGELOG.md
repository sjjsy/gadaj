# Changelog

## 0.2.0 — 2026-04-29

### Added
- Commits table is now shown by default; no flag needed to see per-commit detail
- Per-author color palette in the commits table: each author gets a distinct color from a configurable 8-color palette (complementary pairs: green/red, cyan/magenta, yellow/blue, orange/violet)
- `[colors]` section in `config.toml`: `author_palette = [32, 31, ...]` accepts standard and 256-color ANSI codes

### Changed
- `--commits` / `-c` flag inverted to `--no-commits` / `-c`: the flag now **hides** the commits table rather than showing it

### Technical
- `_Colors.apply_code(text, code)` method added to apply an arbitrary ANSI escape sequence and reset

---

## 0.1.0 — 2026-04-28

Initial release. Refactored and restructured from `journal_facility.py`.

### Added
- `GitCollector`: collect commits within a time window via `git log --stat`
- `CCCollector`: collect Claude Code sessions from `~/.claude/projects/` JSONL files
- Multi-session aggregation across all CC sessions in a time window
- `MarkdownReporter`: human-readable terminal output with separate Git and CC sections
- `JsonReporter`: stable JSON schema for downstream scripts and AI agents
- `--window`, `--since`, `--until` time window flags
- `--git-range`, `--git-last`, `--git-author`, `--git-filter` git flags
- `--cc-file` CC override flag
- `--commits`, `--json`, `--out`, `--raw`, `--tz` output flags
- `~/.config/gadaj/config.toml` config with author nicks and model pricing
- `.gadaj.toml` project-level config override
- Gap detection between CC sessions (> 30 min flagged as `⚠ Xm gap`)
- Parallel session detection (overlapping sessions labelled `[parallel]`)
