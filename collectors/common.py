"""Validated item envelopes and daily observations; collection never calls a model."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from radar.storage import atomic_json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("RADAR_HOME", PROJECT_ROOT)).expanduser().resolve()
CONFIG = Path(os.environ.get("RADAR_CONFIG_DIR", PROJECT_ROOT / "config")).expanduser().resolve()
RAW = ROOT / "data" / "raw"
SEEN_PATH = ROOT / "data" / "seen.json"
CATEGORIES = frozenset({"research", "hardware", "releases"})


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_window(window: str) -> timedelta:
    match = re.fullmatch(r"(\d+)\s*([hd])", window.strip().lower())
    if not match or int(match[1]) <= 0:
        raise ValueError(f"bad window: {window!r} (use a positive duration, e.g. 24h, 48h, 7d)")
    try:
        return timedelta(**{"hours" if match[2] == "h" else "days": int(match[1])})
    except OverflowError as exc:
        raise ValueError("window is too large") from exc


def timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def valid_url(value: object) -> bool:
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        return False
    try:
        parsed = urlsplit(value)
        return bool(
            parsed.scheme in {"https", "http"}
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def validate_item(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("item must be an object")
    for field in ("id", "title", "source"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise ValueError(f"item needs a nonempty {field}")
    if item.get("category") not in CATEGORIES or not valid_url(item.get("url")):
        raise ValueError("item has an invalid category or URL")
    timestamp(item.get("fetched"))
    signals = item.get("signals") or {}
    if not isinstance(signals, dict):
        raise ValueError("signals must be an object")
    if any(
        isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0
        for n in signals.values()
    ):
        raise ValueError("signals must be finite, nonnegative numbers")
    for field in ("authors", "keywords"):
        value = item.get(field) or []
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            raise ValueError(f"{field} must be a list of strings")
    links = item.get("links") or {}
    if not isinstance(links, dict) or any(not valid_url(url) for url in links.values()):
        raise ValueError("links must contain HTTP(S) URLs")
    if not isinstance(item.get("raw_summary", ""), str):
        raise ValueError("raw_summary must be text")
    score = item.get("score")
    if score is not None and (
        isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 5
    ):
        raise ValueError("score must be between zero and five")
    return item


def make_item(
    *,
    id: str,
    category: str,
    title: str,
    url: str,
    source: str,
    authors=None,
    published=None,
    raw_summary="",
    signals=None,
    links=None,
    keywords=None,
) -> dict:
    return {
        "id": id,
        "category": category,
        "title": title.strip(),
        "url": url,
        "source": source,
        "authors": [a for a in (authors or []) if a],
        "published": published,
        "fetched": now_iso(),
        "raw_summary": (raw_summary or "").strip(),
        "links": {k: v for k, v in (links or {}).items() if valid_url(v)},
        "keywords": [k for k in (keywords or []) if k],
        "signals": signals or {},
        "score": None,
    }


def _seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        value = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            raise ValueError("expected a list of IDs")
        return set(value)
    except (OSError, ValueError) as exc:
        print(f"[collect] ignoring corrupt observation ledger: {exc}", file=sys.stderr)
        return set()


def _save_seen(seen: set[str]) -> None:
    atomic_json(SEEN_PATH, sorted(seen))


def _safe_name(item_id: str) -> str:
    return hashlib.sha256(item_id.encode()).hexdigest()[:24]


def _merge_signals(item_id: str, signals: dict) -> bool:
    """Legacy helper for callers; update the newest observation only."""
    matches = [item for item in iter_raw("3650d") if item["id"] == item_id]
    if not matches:
        return False
    stored = matches[0]
    path = Path(stored.pop("_path"))
    stored["signals"] = (stored.get("signals") or {}) | signals
    atomic_json(path, stored)
    return True


def write_items(category: str, items: list[dict]) -> int:
    """Upsert today's observations, including IDs seen on previous days.

    The historical ID ledger is informational. It must never suppress a fresh
    observation: CI checks out the ledger without yesterday's raw artifact.
    New measurements replace older ones; omitted links/signals are retained.
    """
    from collectors.blocklist import filter_items

    if category not in CATEGORIES:
        raise ValueError(f"unknown category: {category}")
    seen = _seen()
    out_dir = RAW / category / today_str()
    written = 0
    for item in filter_items(items):
        try:
            validate_item(item)
            if item["category"] != category:
                raise ValueError("category does not match output directory")
        except ValueError as exc:
            print(f"[collect] rejected item: {exc}", file=sys.stderr)
            continue
        path = out_dir / f"{_safe_name(item['id'])}.json"
        previous = {}
        if path.exists():
            try:
                previous = validate_item(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
        merged = previous | item
        for field in ("signals", "links"):
            merged[field] = (previous.get(field) or {}) | (item.get(field) or {})
        merged["keywords"] = sorted(set(previous.get("keywords", [])) | set(item.get("keywords", [])))
        atomic_json(path, merged)
        seen.add(item["id"])
        written += 1
    _save_seen(seen)
    return written


def iter_raw(window: str = "48h"):
    """Yield the newest valid observation per ID in the window, deterministically."""
    from collectors.blocklist import is_blocked, load_blocked_domains

    blocked = load_blocked_domains()
    cutoff = datetime.now(timezone.utc) - parse_window(window)
    newest: dict[str, dict] = {}
    for path in sorted(RAW.rglob("*.json")):
        try:
            item = validate_item(json.loads(path.read_text(encoding="utf-8")))
            fetched = timestamp(item["fetched"])
        except (OSError, ValueError) as exc:
            print(f"[collect] skipped {path.name}: {exc}", file=sys.stderr)
            continue
        if fetched < cutoff or fetched > datetime.now(timezone.utc) + timedelta(minutes=5):
            continue
        if is_blocked(item["url"], blocked):
            continue
        previous = newest.get(item["id"])
        if previous is None or fetched > timestamp(previous["fetched"]):
            newest[item["id"]] = item | {"_path": str(path)}
    yield from (newest[key] for key in sorted(newest))
