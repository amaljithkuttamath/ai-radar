"""The deferred check: score yesterday's predictions against today's observations.

ADR-0009 §3. This is the only ground truth this repo can have that is not a model's opinion.

The idea. When a digest puts an item under **Climbing** it is not expressing taste, it is
making a falsifiable claim about the near future: this item's traction will keep rising.
**Cooled** claims the opposite. `data/tracked.json` keeps `mag_history`, a per-run series of
the same composite traction number, so three runs later the repo *knows* whether the claim
held — graded by events that had not happened when the prompt ran.

Why that property matters. Gao, Schulman & Hilton (ICML 2023) measured what happens when you
optimise against a proxy: the proxy score keeps rising while ground truth falls. A rubric
scored by a model reading the same prose the prompt produced is exactly such a proxy. The
Goodhart brake in `grader/trusted.py` needs a number the optimiser cannot reach, and a
prediction settled by future observations is that number: no wording change can retroactively
make a counter go up.

It is also *trusted* in the specific mechanical sense ADR-0009 defines — computed solely from
paths outside the coder whitelist. The series comes from `distill/track.py` and the
collectors, neither of which the coder may touch. Contrast source diversity or the A2
ceiling, which depend on `config/profile.yaml` and `config/broken_sources.yaml`: those are
legitimate *targets* of optimisation and so cannot also be the referee.

Claims are recorded at claim time (with the traction reading as it then stood) and settled
later, because `mag_history` carries no timestamps — only order. Storing the series length at
claim time is what makes "three runs later" answerable at all.

This module is a FENCE path. No agent may edit it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORECASTS = ROOT / "evals" / "forecasts.jsonl"

# How many further traction readings must accumulate before a claim is settled. Three runs
# is roughly three days at the current cadence — long enough that one noisy re-fetch cannot
# decide a verdict, short enough to still be feedback rather than history.
HORIZON_RUNS = 3

# Relative change below which a claim is treated as flat rather than confirmed or refuted.
# Traction numbers jitter by a percent or so between re-fetches; scoring that jitter as a
# correct forecast would inflate the one metric here that is supposed to be incorruptible.
FLAT_BAND = 0.05

# ~6 months of daily claims. Bounded for the same reason `attempts.jsonl` is.
MAX_RECORDS = 2000

# Section -> the direction that section asserts.
#
# Only sections that make a genuine forward claim appear. `Still developing` is deliberately
# absent despite looking like a candidate: read the real digests and its entries routinely
# say "traction flat", so the section asserts continued *attention*, not continued rise.
# Scoring it as "up" would manufacture a claim the digest never made, which is the one thing
# this file must not do — a corrupted ground truth is worse than none, because the Goodhart
# brake would then be measuring the same fiction it exists to catch.
CLAIM_SECTIONS = {
    "Climbing": "up",       # "traction +2.5x" — explicit
    "Story arcs": "up",     # "rising traction across >=3 consecutive runs" — explicit
    "Cooled": "down",
}

_LINK = re.compile(r"\[(?P<title>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)")
# `- **Some Title** — 8th run, traction flat.` Story arcs and Cooled entries name the item
# in bold with no link, so URL matching alone silently sees only a third of the claims.
_BOLD = re.compile(r"^\s*[-*]\s+\*\*(?P<title>[^*]+?)\*\*", re.M)
_ARXIV = re.compile(r"arxiv\.org/(?:abs|pdf)/(?P<id>\d{4}\.\d{4,5})", re.I)
_HF = re.compile(r"(?:huggingface\.co|hf\.co)/(?P<kind>datasets/)?(?P<slug>[\w.\-]+/[\w.\-]+)", re.I)
_GH = re.compile(r"github\.com/(?P<slug>[\w.\-]+/[\w.\-]+)", re.I)


# --- locating the claims ---------------------------------------------------

def _blocks(digest: str) -> dict[str, str]:
    """Body text keyed by the nearest preceding heading, `##` or bold sub-label.

    `Climbing` and `Cooled` are bold sub-labels inside `## What changed`, while `Story arcs`
    and `Still developing` are `##` sections. Both shapes are handled rather than one being
    normalised away, because the digest template is a coder-editable file and pinning its
    exact heading level here would make this checker brittle against a legal edit.
    """
    out: dict[str, list[str]] = {}
    current: str | None = None
    for line in digest.splitlines():
        heading = re.fullmatch(r"#{2,3}\s+(.+?)\s*", line) or \
                  re.fullmatch(r"\*\*(.+?)\*\*\s*", line)
        if heading:
            current = heading.group(1).strip()
            out.setdefault(current, [])
            continue
        if current:
            out[current].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def item_key(url: str) -> str | None:
    """Map a digest URL to a `data/tracked.json` key, or None.

    Mirrors the id scheme the collectors mint (`arxiv:`, `hfmodel:`, `hfdataset:`,
    `ghrepo:`). Returning None is a real outcome and is counted: an unresolvable claim is
    reported as unresolved rather than silently dropped, so coverage is visible in the
    metric rather than being something you have to trust.
    """
    if m := _ARXIV.search(url):
        return f"arxiv:{m.group('id')}"
    if m := _HF.search(url):
        slug = m.group("slug")
        return f"hfdataset:{slug}" if m.group("kind") else f"hfmodel:{slug}"
    if m := _GH.search(url):
        return f"ghrepo:{m.group('slug')}"
    return None


def _normalise(title: str) -> str:
    """Casefold and strip punctuation/whitespace runs, so a title survives the cosmetic
    differences between the ledger's copy and the digest's."""
    return re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()


def title_index(tracked: dict) -> dict[str, str]:
    """`{normalised title: key}`. Ambiguous titles are dropped rather than guessed — two
    items sharing a name is rare, and resolving one to the wrong series would put a
    fabricated verdict into the only metric here that is meant to be incorruptible."""
    seen: dict[str, str | None] = {}
    for key, item in tracked.items():
        norm = _normalise(str(item.get("title") or ""))
        if not norm:
            continue
        seen[norm] = None if norm in seen else key
    return {k: v for k, v in seen.items() if v}


def extract_claims(digest: str, tracked: dict | None = None) -> list[dict]:
    """`[{"key", "title", "direction", "section"}]` — every forward claim the digest makes,
    deduplicated on (key, direction).

    Two shapes, because the digest uses both: `Climbing` links the item, while `Story arcs`
    and `Cooled` name it in bold with no URL. Matching only URLs silently saw a third of the
    claims, which would have made the sample too small for the accuracy figure to mean
    anything.
    """
    by_title = title_index(tracked or {})
    claims: dict[tuple, dict] = {}
    blocks = _blocks(digest)
    for section, direction in CLAIM_SECTIONS.items():
        body = blocks.get(section)
        if not body:
            continue

        found: list[tuple[str, str, str | None]] = []
        for m in _LINK.finditer(body):
            found.append((m.group("title").strip(), m.group("url"), item_key(m.group("url"))))
        for m in _BOLD.finditer(body):
            title = m.group("title").strip()
            # A bold entry may also carry a link on the same line; the URL match above
            # already claimed it, and `setdefault` below keeps whichever resolved first.
            found.append((title, "", by_title.get(_normalise(title))))

        for title, url, key in found:
            if not key:
                continue
            claims.setdefault((key, direction), {
                "key": key, "url": url, "title": title,
                "direction": direction, "section": section,
            })
    return list(claims.values())


# --- recording and settling -------------------------------------------------

def open_claims(digest: str, tracked: dict, date: str) -> list[dict]:
    """Claims paired with the traction reading as it stands *now*.

    `history_len` is the load-bearing field: `mag_history` has order but no timestamps, so
    the length at claim time is the only way to later ask "and what happened after that?".
    A claim about an item not on the radar is dropped — there is no series to settle it
    against, and inventing one would be the fabrication this module exists to avoid.
    """
    out = []
    for claim in extract_claims(digest, tracked):
        item = tracked.get(claim["key"])
        history = (item or {}).get("mag_history") or []
        if not history:
            continue
        out.append({**claim, "date": date,
                    "mag_at_claim": round(float(history[-1]), 4),
                    "history_len": len(history)})
    return out


def settle(claim: dict, tracked: dict, horizon: int = HORIZON_RUNS) -> dict | None:
    """Resolve one claim, or None if not enough further readings have accumulated.

    A verdict is `correct`, `wrong` or `flat`. `flat` is its own outcome rather than being
    folded into either: jitter between re-fetches is not a successful forecast, and counting
    it as one would inflate the single metric here that is meant to be incorruptible.
    """
    item = tracked.get(claim["key"])
    history = (item or {}).get("mag_history") or []
    if len(history) < claim["history_len"] + horizon:
        return None

    before = claim["mag_at_claim"]
    after = float(history[claim["history_len"] + horizon - 1])
    # Guard the degenerate case rather than dividing by it: an item whose traction was zero
    # when the claim was made has no meaningful relative change.
    change = (after - before) / before if before else 0.0

    if abs(change) < FLAT_BAND:
        verdict = "flat"
    elif (change > 0) == (claim["direction"] == "up"):
        verdict = "correct"
    else:
        verdict = "wrong"
    return {**claim, "settled_mag": round(after, 4),
            "change": round(change, 4), "verdict": verdict}


def accuracy(settled: list[dict]) -> float | None:
    """Share of decided claims that were right, or None if none were decided.

    `flat` claims are excluded from the denominator, not counted as failures: "traction did
    not move much" says nothing about whether the digest read the item correctly. None is
    returned rather than 0.0 for the same reason tier 0 returns `ok=None` — no evidence is
    not evidence of failure.
    """
    decided = [s for s in settled if s["verdict"] in ("correct", "wrong")]
    if not decided:
        return None
    return round(sum(1 for s in decided if s["verdict"] == "correct") / len(decided), 3)


# --- persistence -------------------------------------------------------------

def load(path: Path | None = None) -> list[dict]:
    p = path or FORECASTS
    try:
        text = p.read_text()
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def save(records: list[dict], path: Path | None = None,
         max_records: int = MAX_RECORDS) -> Path:
    p = path or FORECASTS
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                         for r in records[-max_records:]))
    return p


def update(digest: str, tracked: dict, date: str, path: Path | None = None) -> dict:
    """Settle what can be settled, record today's claims, return the reading.

    One pass, so the caller cannot accidentally record without settling and let the ledger
    grow a tail of claims nobody ever scores.
    """
    existing = load(path)
    resolved, pending = [], []
    for claim in existing:
        if claim.get("verdict"):
            resolved.append(claim)
            continue
        outcome = settle(claim, tracked)
        (resolved if outcome else pending).append(outcome or claim)

    already = {(c["key"], c["direction"], c.get("date")) for c in existing}
    fresh = [c for c in open_claims(digest, tracked, date)
             if (c["key"], c["direction"], c["date"]) not in already]

    save(resolved + pending + fresh, path)

    # Only recently settled claims drive the brake. A lifetime average would take months to
    # move and would mask exactly the regression the brake exists to catch.
    recent = [c for c in resolved if c.get("verdict")][-60:]
    return {
        "claims_recorded": len(fresh),
        "claims_pending": len(pending),
        "claims_settled": len(recent),
        "forecast_accuracy": accuracy(recent),
    }
