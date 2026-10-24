"""Run orchestration and the boundary between previews and published artifacts."""

from __future__ import annotations

import fcntl
import hashlib
import importlib
import json
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from collectors.common import ROOT, iter_raw, now_iso, parse_window, timestamp
from radar.storage import atomic_json, atomic_text


@contextmanager
def pipeline_lock():
    directory = ROOT / "data"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".pipeline.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another pipeline process is using this data directory") from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def collect(settings) -> dict:
    started = now_iso()
    results = []
    for name in settings.collectors:
        try:
            result = importlib.import_module(f"collectors.{name}").main()
        except Exception as exc:
            result = {"collector": name, "status": "failed", "error": str(exc)[:300], "written": 0}
            print(f"[collect] {name}: {exc}", file=sys.stderr)
        results.append(result)
    successful = [r for r in results if r["status"] in {"ok", "degraded"}]
    observations = [
        item for item in iter_raw(settings.window) if timestamp(item["fetched"]) >= timestamp(started)
    ]
    status = (
        "failed"
        if not successful
        else ("ok" if all(r["status"] in {"ok", "disabled"} for r in results) else "degraded")
    )
    manifest = {
        "version": 1,
        "started_at": started,
        "finished_at": now_iso(),
        "status": status,
        "window": settings.window,
        "collectors": results,
        "item_ids": sorted(item["id"] for item in observations),
        "item_count": len(observations),
    }
    atomic_json(ROOT / "data" / "collection.json", manifest)
    if status == "failed":
        raise RuntimeError("all enabled collectors failed; see data/collection.json")
    print(f"[collect] {status}: {len(observations)} current observations")
    return manifest


def collection_manifest(window: str) -> dict | None:
    path = ROOT / "data" / "collection.json"
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("status") not in {"ok", "degraded"}:
            raise ValueError("collection was not successful")
        age = datetime.now(timezone.utc) - timestamp(manifest.get("finished_at"))
        if age.total_seconds() < -300 or age > parse_window(window):
            raise ValueError("collection manifest is stale or future-dated")
        if manifest.get("window") and parse_window(manifest["window"]) != parse_window(window):
            raise ValueError(
                f"window differs from collected corpus ({manifest['window']}); use the same window or recollect"
            )
        ids = manifest.get("item_ids")
        if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
            raise ValueError("collection manifest has invalid item IDs")
        return manifest
    except (OSError, ValueError) as exc:
        raise ValueError(f"invalid corpus: {exc}") from exc


def distill(settings) -> Path:
    from distill import score, synthesize, reindex

    manifest = collection_manifest(settings.window)
    items = list(iter_raw(settings.window))
    if manifest is not None:
        ids = set(manifest["item_ids"])
        items = [item for item in items if item["id"] in ids]
        if len(items) != len(ids):
            raise ValueError("corpus is incomplete: manifest items are missing or outside the window")
    if not items:
        raise ValueError("no usable corpus in the requested window; run collect or demo first")
    score.score_items(items)
    if settings.enrich and settings.backend not in {"dryrun", "template"}:
        from distill import enrich

        try:
            enrich.main()
        except Exception as exc:
            print(f"[distill] optional enrichment failed: {exc}", file=sys.stderr)
    if settings.backend in {"dryrun", "template"}:
        return synthesize.main()

    # Reindexing and state writes form one logical publication. Individual files
    # are replaced atomically; handled failures restore the previous publication.
    reports = ROOT / "reports"
    state = ROOT / "data" / "state.json"
    metadata = ROOT / "data" / "publication.json"
    ledger = ROOT / "data" / "tracked.json"
    tracked = [*reports.glob("*.md"), state, metadata, ledger]
    before = {path: path.read_text(encoding="utf-8") if path.exists() else None for path in tracked}
    try:
        from distill import track

        track.main()
        report = synthesize.main()
        if manifest and manifest["status"] == "degraded":
            failed = [r["collector"] for r in manifest["collectors"] if r["status"] in {"failed", "degraded"}]
            footer = "\n\n---\n\nCollection was incomplete: " + ", ".join(failed) + ".\n"
            atomic_text(report, report.read_text(encoding="utf-8").rstrip() + footer)
        reindex.main()
        atomic_json(
            metadata,
            {
                "version": 1,
                "published_at": now_iso(),
                "backend": settings.backend,
                "report": str(report.relative_to(ROOT)),
                "item_count": len(items),
                "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                "collection_status": manifest["status"] if manifest else "unverified",
            },
        )
        return report
    except Exception:
        for path in set(before) | set(reports.glob("*.md")):
            if before.get(path) is None:
                path.unlink(missing_ok=True)
            else:
                atomic_text(path, before[path])
        raise
