from __future__ import annotations

import json

from gadaj.models import WorkPeriod
from gadaj.reporters.markdown import _aggregate_model_usage


class JsonReporter:

    def render(self, period: WorkPeriod) -> str:
        # summary key first — stable schema guarantee
        data: dict = {}

        data["summary"] = {
            "total_cost_usd": round(period.total_cost_usd, 4),
            "contributors": [
                {
                    "name": c.name,
                    "kind": c.kind,
                    "model": c.model,
                    "sessions": c.sessions,
                    "commits": c.commits,
                    "cost_usd": round(c.cost_usd, 4),
                }
                for c in period.contributors.values()
            ],
        }

        data["window"] = {
            "since": period.since.isoformat(),
            "until": period.until.isoformat(),
            "duration_hours": round(
                (period.until - period.since).total_seconds() / 3600, 2
            ),
        }

        data["git"] = {
            "commits": [
                {
                    "hash": c.hash,
                    "datetime": c.datetime.isoformat(),
                    "author": c.author,
                    "message": c.message,
                    "files_changed": c.files_changed,
                    "insertions": c.insertions,
                    "deletions": c.deletions,
                }
                for c in period.commits
            ],
            "files_changed": period.files_changed,
            "insertions": period.insertions,
            "deletions": period.deletions,
            "authors": _authors_map(period),
        }

        aggregated = _aggregate_model_usage(period.cc_sessions)
        data["cc"] = {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "start": s.start.isoformat(),
                    "end": s.end.isoformat(),
                    "total_cost_usd": round(s.total_cost_usd, 4),
                    "models": {
                        model: {
                            "input_tokens": u.input_tokens,
                            "output_tokens": u.output_tokens,
                            "cache_write_tokens": u.cache_write_tokens,
                            "cache_read_tokens": u.cache_read_tokens,
                            "messages": u.messages,
                            "cost_usd": round(u.cost_usd, 4),
                        }
                        for model, u in s.models.items()
                    },
                }
                for s in period.cc_sessions
            ],
            "models": {
                model: {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cache_write_tokens": usage.cache_write_tokens,
                    "cache_read_tokens": usage.cache_read_tokens,
                    "messages": usage.messages,
                    "cost_usd": round(cost, 4),
                }
                for model, (usage, cost) in aggregated.items()
            },
            "total_cost_usd": round(period.total_cost_usd, 4),
        }

        return json.dumps(data, indent=2, default=str)


def _authors_map(period: WorkPeriod) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in period.commits:
        counts[c.author] = counts.get(c.author, 0) + 1
    return counts
