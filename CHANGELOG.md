# Changelog

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
