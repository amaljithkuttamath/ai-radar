"""Blocked-domain ledger, read by every collector before an item is written.

`config/broken_sources.yaml` was whitelisted in `docs/operating/whitelist.md`,
listed in `.github/CODEOWNERS`, and named in `coder.md` as the fix for a failing
`A2 source_integrity` dim — but no code read it. The coder's entire remediation
path for broken URLs wrote to a file nothing consumed: the PR would pass its
whitelist assertion and its YAML sanity check, look correct in review, and have
no effect. A documented control that silently no-ops is worse than an absent
one, because both the contract and the review surface claim the problem is
handled.

This module is the consumer that makes that path real.

Fail-open by design: a missing or malformed ledger must not take down
collection. The ledger suppresses known-bad sources; treating its absence as
fatal would let a typo cost a day's digest, which is a worse failure than
letting a dead domain through for one more run.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from collectors.common import CONFIG

LEDGER = CONFIG / "broken_sources.yaml"


def _normalise(host: str) -> str:
    """Lowercase, strip port and a leading `www.` so ledger entries match hosts
    however they were written."""
    host = host.lower().split(":", 1)[0]
    return host[4:] if host.startswith("www.") else host


def load_blocked_domains(path: Path | None = None) -> set[str]:
    """Read `blocked_domains:` from the ledger. Returns an empty set if the file
    is absent, empty, or unparseable — see the fail-open note above."""
    ledger = path or LEDGER
    if not ledger.exists():
        return set()
    try:
        import yaml  # declared in pyproject.toml

        cfg = yaml.safe_load(ledger.read_text()) or {}
    except Exception as exc:  # noqa: BLE001 - fail open, loudly
        print(
            f"[blocklist] WARNING unreadable ledger {ledger.name}: {exc}. Proceeding with no blocked domains."
        )
        return set()

    if not isinstance(cfg, dict):
        print("[blocklist] WARNING ledger must be a mapping; proceeding with none.")
        return set()
    entries = cfg.get("blocked_domains") or []
    if not isinstance(entries, list):
        print(
            f"[blocklist] WARNING blocked_domains is {type(entries).__name__}, "
            f"expected list. Proceeding with none."
        )
        return set()

    domains = set()
    for entry in entries:
        # Accept both `- example.com` and `- domain: example.com` with metadata,
        # so the coder can record why and when without breaking the reader.
        value = entry.get("domain") if isinstance(entry, dict) else entry
        if isinstance(value, str) and value.strip():
            domains.add(_normalise(value.strip()))
    return domains


def is_blocked(url: str, blocked: set[str]) -> bool:
    """True if `url`'s host is blocked, or is a subdomain of a blocked domain.

    Subdomain matching is deliberate: blocking `example.com` should also stop
    `blog.example.com`, since a dead site rarely dies one subdomain at a time.
    """
    if not blocked or not url:
        return False
    host = _normalise(urlparse(url).netloc)
    if not host:
        return False
    parts = host.split(".")
    return any(".".join(parts[i:]) in blocked for i in range(len(parts)))


def filter_items(items: list[dict], blocked: set[str] | None = None) -> list[dict]:
    """Drop items whose URL is on the ledger. Logs a count so a suppressed
    source is visible in the run log rather than silently vanishing."""
    blocked = load_blocked_domains() if blocked is None else blocked
    if not blocked:
        return items
    kept = [it for it in items if not is_blocked(it.get("url", ""), blocked)]
    dropped = len(items) - len(kept)
    if dropped:
        print(f"[blocklist] dropped {dropped} item(s) from {len(blocked)} blocked domain(s)")
    return kept
