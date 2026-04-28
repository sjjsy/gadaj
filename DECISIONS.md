# gadaj — Implementation Decisions

Judgment calls made during v0.1 implementation. Conflicts resolved using
the principle: design.md wins over README.md; wip.md wins over both for
details not yet in the other files.

---

## 1. JSON key order: `summary` first

wip.md states "The `summary` key comes first in JSON output."  
design.md §6 schema listing shows `window` first.  
**Decision: `summary` first**, per wip.md. Python 3.7+ dict insertion order is
guaranteed, so `summary` is inserted first in `JsonReporter`.

---

## 2. design.md `spec.md` reference removed

design.md header says "For product goals, competition analysis, and CLI spec,
see `spec.md`." No `spec.md` exists — `README.md` is the CLI spec.  
**Decision: updated design.md to reference README.md.**

---

## 3. Per-commit git stats via `--stat`

`Commit` has `files_changed`, `insertions`, `deletions`. wip.md's fixture spec
requests plain log format (no stats). **Decision: use `git log --stat`** to get
per-commit stats. This gives accurate `WorkPeriod` totals via summation and
richer JSON output. `sample_git_log.txt` uses the `--stat` format accordingly.

---

## 4. `--git-filter` filters commit messages only

wip.md says "Filter by commit message or changed path." Path filtering would
require per-commit `git show` calls (expensive).  
**Decision: filter on commit message only** using `git log --grep -i` for v0.1.
Documented in `--help` text.

---

## 5. `--tz` accepts `"auto"` or a float string

README defines `--tz HOURS` but config allows `"auto"`.  
**Decision: `type=str`** in argparse, resolved at runtime. Both `"+3"` and `"3"` 
and `"auto"` are accepted.

---

## 6. Gap fixture uses two `.jsonl` files

wip.md says "a gap of more than 30 minutes between two messages" in `sample.jsonl`.
The spec's gap detection is between sessions (separate `.jsonl` files).  
**Decision: create `sample.jsonl` (session 1) and `sample2.jsonl` (session 2)**
with a 53-minute gap between them. The internal 35-minute gap within `sample.jsonl`
satisfies the wip.md fixture requirement; the inter-file gap exercises session
gap detection in tests.

---

## 7. `DECISIONS.md` at repo root

design.md §2 layout does not list `DECISIONS.md`.  
**Decision: added per wip.md instructions.** No code changes required.

---

## 8. `--git-author` passes raw name to git

`--git-author NAME` is passed as `--author=NAME` to git, which does substring
matching against author name or email. The nick is NOT expanded back to full name.
User should pass the full name or a fragment.

---

## 9. `parse_since` handles weekday names

README example uses `gadaj -s monday`. wip.md lists "N hours ago", "N days ago",
"today", "yesterday" but not weekday names. **Decision: add weekday name support**
to `parse_since`. "monday" when today is Monday means "last Monday" (7 days back).
