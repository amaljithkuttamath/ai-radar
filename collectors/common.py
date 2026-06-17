"""Shared collector utilities: item schema, dated folder IO, cross-run dedup, date windows.
Stdlib only — collection must never require a model or heavy deps."""
from __future__ import annotations
import json, re, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SEEN_PATH = ROOT / "data" / "seen.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_window(window: str) -> timedelta:
    """'24h' / '48h' / '7d' -> timedelta."""
    m = re.fullmatch(r"(\d+)\s*([hd])", window.strip().lower())
    if not m:
        raise ValueError(f"bad window: {window!r} (use e.g. 24h, 48h, 7d)")
    n, unit = int(m.group(1)), m.group(2)
    return timedelta(hours=n) if unit == "h" else timedelta(days=n)


def make_item(*, id: str, category: str, title: str, url: str, source: str,
              authors=None, published=None, raw_summary="", signals=None,
              links=None, keywords=None) -> dict:
    return {
        "id": id,
        "category": category,
        "title": title.strip(),
        "url": url,
        "source": source,
        "authors": authors or [],
        "published": published,
        "fetched": now_iso(),
        "raw_summary": (raw_summary or "").strip(),
        # Secondary artifact links (e.g. a paper's github repo / project page). `url` stays the
        # primary artifact; `links` lets the distiller and the gh-stars enricher find a repo
        # without re-fetching.
        "links": {k: v for k, v in (links or {}).items() if v},
        # Source-provided topic tags (e.g. HF ai_keywords). A cheap recall aid for clustering/FOCUS.
        "keywords": [k for k in (keywords or []) if k],
        "signals": signals or {},
        "score": None,
    }


def _seen() -> set[str]:
    if SEEN_PATH.exists():
        return set(json.loads(SEEN_PATH.read_text()))
    return set()


def _save_seen(seen: set[str]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(sorted(seen), indent=0))


def _safe_name(item_id: str) -> str:
    return hashlib.sha1(item_id.encode()).hexdigest()[:16]


def _merge_signals(item_id: str, signals: dict) -> bool:
    """An item with this id was already written (possibly by another collector on an earlier
    run). If the new copy carries signals the stored one lacks, merge them in so cross-collector
    signal (e.g. HF upvotes on a paper arxiv already wrote) is not lost to dedup. Returns True
    if a stored file was updated."""
    if not signals:
        return False
    target = f"{_safe_name(item_id)}.json"
    for p in RAW.rglob(target):
        try:
            stored = json.loads(p.read_text())
        except Exception:
            continue
        merged = {**signals, **(stored.get("signals") or {})}  # keep existing, fill gaps
        if merged != (stored.get("signals") or {}):
            stored["signals"] = merged
            p.write_text(json.dumps(stored, indent=2))
        return True
    return False


def write_items(category: str, items: list[dict]) -> int:
    """Write new items into data/raw/<category>/<date>/<id>.json. Skips ids already seen,
    but merges any new signals into the already-stored copy first (order-independent dedup).
    Returns count of newly written items."""
    seen = _seen()
    out_dir = RAW / category / today_str()
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for it in items:
        if it["id"] in seen:
            _merge_signals(it["id"], it.get("signals") or {})
            continue
        (out_dir / f"{_safe_name(it['id'])}.json").write_text(json.dumps(it, indent=2))
        seen.add(it["id"])
        written += 1
    _save_seen(seen)
    return written


def iter_raw(window: str = "48h"):
    """Yield raw item dicts fetched within the window, across all categories."""
    cutoff = datetime.now(timezone.utc) - parse_window(window)
    if not RAW.exists():
        return
    for p in RAW.rglob("*.json"):
        try:
            it = json.loads(p.read_text())
        except Exception:
            continue
        try:
            fetched = datetime.fromisoformat(it.get("fetched", ""))
        except ValueError:
            continue
        if fetched >= cutoff:
            it["_path"] = str(p)
            yield it
