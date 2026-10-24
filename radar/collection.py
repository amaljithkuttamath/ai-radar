"""Per-source health accounting shared by all collectors."""

from __future__ import annotations

import sys


class SourceBatch:
    def __init__(self, name: str):
        self.name = name
        self.sources: list[dict] = []

    def fetch(self, source: str, function, *args):
        try:
            items = list(function(*args))
        except Exception as exc:
            self.sources.append({"source": source, "status": "failed", "error": str(exc)[:300]})
            print(f"[{self.name}] {source} failed: {exc}", file=sys.stderr)
            return []
        self.sources.append({"source": source, "status": "ok", "items": len(items)})
        return items

    def finish(self, written: int) -> dict:
        successes = sum(source["status"] == "ok" for source in self.sources)
        if self.sources and not successes:
            raise RuntimeError(f"{self.name}: all {len(self.sources)} sources failed")
        return {
            "collector": self.name,
            "status": "disabled"
            if not self.sources
            else ("ok" if successes == len(self.sources) else "degraded"),
            "written": written,
            "sources": self.sources,
        }
