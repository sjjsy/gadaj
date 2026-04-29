# Changelog

## 0.2.0 — 2026-04-29

**Usability-focused release with author coloring, inverted defaults, and predictable configuration.**

### Added

**Per-author color assignment** — Authors in the commits table are now assigned distinct colors from an 8-color palette (complementary pairs: green/red, cyan/magenta, yellow/blue, orange/violet) for visual differentiation. Colors are assigned in order of first appearance, or can be pinned to specific authors via config.

**Explicit author-to-color mapping** — New `[author_colors]` TOML section lets teams pin specific authors to specific colors for predictability across invocations:
```toml
[author_colors]
"Samuel Sydänlammi" = 32   # always green
"Mikko Lastname"    = 31   # always red
```

**Color palette configuration** — New `[colors]` section in `config.toml` with `author_palette = [32, 31, ...]` accepts standard ANSI codes and 256-color codes (e.g. `130`). Default palette includes 8 dark, perceptually distinct colors.

**Infrastructure** — Added `colors.py` module (ANSI color helpers with enable/disable) and `table.py` module (ANSI-aware tabular formatter supporting lightweight and Markdown modes). Both modules are test-covered and ready for extension.

### Changed

**Commits table is now default** — `--commits` / `-c` flag behavior inverted: commits table is shown by default, hidden with `--no-commits` / `-c`. This aligns with user expectation (developers want to see what changed) and reduces friction. Significant usability improvement validated by 162 tests.

**Datetime header logic fixed** — Commits table now correctly shows "Datetime" header when commits themselves span multiple calendar dates, not just when the query window does. Previously, `gadaj --git-last 10` with commits from 2026-04-27 to 2026-04-28 would show "Time" if the window was narrow. Now correctly shows "Datetime".

**Documentation overhauled** — design.md now documents colors.py and table.py architecture; README sample output demonstrates commits table by default; Quickstart examples corrected to reflect inverted flag.

### Technical

- `_Colors.apply_code(text, code)` method for wrapping text in arbitrary ANSI escape sequences
- `Table` class with ANSI-aware width calculation (`_vlen()`) and padding (`_pad()`) to prevent color codes from shifting column alignment
- Dual rendering modes in `Table.render(markdown=False|True)` for lightweight (space-aligned) and Markdown (pipe format) output
- Author color assignment in `MarkdownReporter._commits_table()` prioritizes explicit mapping, falls back to palette
- Per-commit datetime logic in `_commits_table()` considers actual commit span, not window boundaries

### Fixed

- Commits table header (Time vs Datetime) now based on commit span, not window boundaries
- Author colors are now predictable and configurable, eliminating order-dependent assignment
- All 11 new tests (3 config, 4 reporter, 4 new infrastructure) ensure color mapping and datetime logic are correct

### Stats

- **Tests**: 151 → 162 (+11 new)
- **Code**: colors.py (59 lines), table.py (118 lines), config.py (+13 for author_colors_map), reporters/markdown.py (+18 for author coloring)
- **Test coverage**: 100% for new features (colors, table, author mapping)

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
