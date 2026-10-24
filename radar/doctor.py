"""Read-only local health checks; never contacts a model or prints credentials."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from collectors.common import ROOT, timestamp


def inspect(settings) -> dict:
    now = datetime.now(timezone.utc)
    checks = {}
    paths = {
        "digest": ROOT / "reports" / "latest.md",
        "evaluation": ROOT / "evals" / "latest.json",
        "collection": ROOT / "data" / "collection.json",
    }
    for name, path in paths.items():
        if not path.exists():
            checks[name] = {"status": "missing", "path": str(path)}
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if name == "digest":
                match = re.search(r"^# AI Radar — (\d{4}-\d{2}-\d{2})$", text, re.MULTILINE)
                if not match:
                    raise ValueError("missing dated digest header")
                observed = timestamp(match[1] + "T00:00:00Z")
                status = "ok"
            else:
                value = json.loads(text)
                if not isinstance(value, dict):
                    raise ValueError("expected an object")
                observed = (
                    timestamp(value["date"] + "T00:00:00Z")
                    if name == "evaluation"
                    else timestamp(value["finished_at"])
                )
                status = value.get("status", "ok")
                if status not in {"ok", "degraded", "failed"}:
                    raise ValueError("unknown collection status")
            age = (now - observed).total_seconds() / 3600
            if age < -0.1:
                status = "invalid"
            elif age > (48 if name != "collection" else 36):
                status = "stale"
            checks[name] = {"status": status, "age_hours": round(age, 1), "path": str(path)}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            checks[name] = {"status": "invalid", "detail": str(exc)}
    try:
        settings.check_credentials()
        checks["backend"] = {"status": "ok", "name": settings.backend}
    except ValueError as exc:
        checks["backend"] = {"status": "missing", "detail": str(exc)}
    return {
        "healthy": all(v["status"] == "ok" for v in checks.values()),
        "checked_at": now.isoformat(),
        "root": str(ROOT),
        "checks": checks,
    }
