# wip.md — Work in progress

- Use this for active editing and review of specs, wireframes,
  brainstorming notes and feedback rounds (discussion) for work
  currently in flight.
- Commit the file before starting a review or implementation round to
  capture spec evolution.
- After finishing a significant implementation work, and before ending a
  work session, add a journal entry that summarizes all the work done
  since the previous (=topmost) entry into `journal.md`, before flushing `wip.md`
  clean/empty, and committing these two file updates.
- Annotate review rounds with TODO/FIXME/IDEA/QUESTION to separate
  earlier and newer input

## Todo
- The topmost table (git commits, authors and files) should also be a table
- The header-content divider in the sessions table is wider than the rest of the table due to the first column having only 1 char of content but the divider has ' --- '. Please make the divider in all tables to extend to the '|' chars. This should fix the issue.
- Coloring: Make most digits (commit counts, file counts, session counts, date and time digits, usage figures) dark blue except the ones already colored; Make the yellow/orange used for costs slightly darker if such a shade is available.
- Summary table:
  - The Git row should include "X commits over Y hours" with Y being the number of hours between last and first commit.
  - The CC row should move cost to left and have: ~$A.BC over X hours from Y sessions, where hours is the sum of session durations.
  - The total should include total session time duration just before cost figure in the same row.
