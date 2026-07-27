"""Carryover tracking + traction re-observation. This is the piece that makes the radar a
radar rather than 37 unrelated newsletters.

## The bug this fixes

`data/seen.json` dedups an item forever, and `data/raw/` is gitignored and rebuilt from
scratch in CI. So a given item is collected exactly once and lands in exactly one run's
scored set. `delta.compute_delta` then diffs today's items against `state.json`, which holds
*yesterday's disjoint set* — the intersection is always empty. Consequences, all confirmed
against the committed history:

  * every state snapshot had `streak == 1`, on every item, for the whole life of the repo;
  * `story_arcs()` (needs streak >= 3) had never once fired;
  * "Climbing" / "Cooled" / "Still developing" were structurally unreachable — empty in all
    37 digests that carry the section;
  * a quiet collection day meant a digest with zero main-list items (it happened on ~30% of
    days) because the only candidates were the handful of items first seen that day.

## The fix

An item that mattered stays on the radar for a while, and its traction is **re-observed**
each run rather than carried forward as fiction:

  1. `promote()` — after a successful digest, items at or above TRACK_MIN_SCORE enter
     `data/tracked.json`. Only items with a re-fetchable traction source are eligible; a
     vendor blog post has no counter to watch, so tracking it would be theatre.
  2. `refresh()` — each run, every live entry is re-fetched from the source of record
     (GitHub stars, HF likes/downloads, HF paper upvotes) and its magnitude appended to a
     rolling history. Real observations, so streaks and arcs mean something.
  3. `carryover_items()` — live entries re-enter `data/scored/` as candidates, re-scored
     against their *current* signals. Now today's set and the previous snapshot overlap, so
     movers work; and a quiet window still has real material to publish.

Pruning keeps the ledger honest and small (it is committed daily): TTL since first sighting,
consecutive-miss cap for dead links, flat-traction cap for items that stopped moving, and a
hard size cap that keeps the highest peaks.

Traction figures reaching the digest are therefore observed at publish time, not inherited
from whenever the item was first collected — which is what `evals/backlog.md` asks for under
X2_instrument_honesty (star counts that didn't match the linked repo).

Stdlib only, and every fetch degrades to "no observation" rather than an exception, so a
network blip costs a data point and never a digest.

Run: python -m distill.track
"""
from __future__ import annotations
import os, sys, json
from datetime import datetime, timezone, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import ROOT  # noqa: E402
from distill.rank import magnitude  # noqa: E402
from distill import tools  # noqa: E402

LEDGER = ROOT / "data" / "tracked.json"
SCORED = ROOT / "data" / "scored"

# Tuning knobs. Defaults are deliberately conservative: a small ledger of things that are
# genuinely moving beats a long tail of stale rows committed to git every day.
TTL_DAYS = int(os.environ.get("TRACK_TTL_DAYS", "14"))        # max age since first_seen
MAX_TRACKED = int(os.environ.get("TRACK_MAX", "60"))          # hard ledger size cap
MIN_SCORE = int(os.environ.get("TRACK_MIN_SCORE", "3"))       # promote at/above this score
MAX_MISSES = int(os.environ.get("TRACK_MAX_MISSES", "3"))     # consecutive failed re-fetches
MAX_FLAT_RUNS = int(os.environ.get("TRACK_MAX_FLAT_RUNS", "5"))  # runs with no traction gain
REFRESH_BUDGET = int(os.environ.get("TRACK_REFRESH_BUDGET", "60"))  # HTTP calls per run
# A carryover has to still clear the routing floor to be worth re-publishing.
MIN_CARRYOVER_SCORE = int(os.environ.get("TRACK_MIN_CARRYOVER_SCORE", "2"))
GH_TOKEN = os.environ.get("GITHUB_TOKEN")


# ---------------------------------------------------------------------------
# Ledger IO
# ---------------------------------------------------------------------------

def load_ledger(path: Path | None = None) -> dict[str, dict]:
    """Read the tracked-item ledger. Missing or corrupt => empty, never an exception: a
    damaged ledger should cost the radar its memory, not today's digest."""
    p = path or LEDGER
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except Exception:
        print("[track] ledger unreadable; starting from empty", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def save_ledger(ledger: dict[str, dict], path: Path | None = None) -> None:
    p = path or LEDGER
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ledger, indent=0, sort_keys=True))


# ---------------------------------------------------------------------------
# Re-observation
# ---------------------------------------------------------------------------

def signal_source(entry: dict) -> tuple[str, str] | None:
    """What can be re-fetched for this item, as (kind, key). None => nothing to observe, so
    the item is not trackable. Derived from the id scheme the collectors mint:
    `ghrepo:owner/repo`, `hfmodel:id`, `hfdataset:id`, `arxiv:id`, `blog:hash`.
    A blog post falls back to a linked repo if the collector captured one."""
    iid = entry.get("id") or ""
    if iid.startswith("ghrepo:"):
        return ("github", iid.split(":", 1)[1])
    if iid.startswith("hfmodel:"):
        return ("hf_model", iid.split(":", 1)[1])
    if iid.startswith("hfdataset:"):
        return ("hf_dataset", iid.split(":", 1)[1])
    if iid.startswith("arxiv:"):
        return ("arxiv", iid.split(":", 1)[1])
    gh = (entry.get("links") or {}).get("github") or ""
    if "github.com/" in gh:
        repos = tools.extract_github_repos(gh)
        if repos:
            return ("github", f"{repos[0][0]}/{repos[0][1]}")
    return None


def is_trackable(item: dict) -> bool:
    """True when the item has a counter we can re-read on a later run."""
    return signal_source(item) is not None


def observe(entry: dict, fetchers: dict | None = None) -> dict | None:
    """Re-fetch current traction for one tracked entry. Returns a signals dict, or None when
    the source could not be read (network error, 404, deleted repo). `fetchers` overrides the
    live tools for tests — the network is the only thing this module can't reason about."""
    src = signal_source(entry)
    if not src:
        return None
    kind, key = src
    f = fetchers or {}
    try:
        if kind == "github":
            owner, _, repo = key.partition("/")
            fetch = f.get("github") or (lambda o, r: tools.fetch_github_repo(o, r, GH_TOKEN))
            info = fetch(owner, repo)
            if not info:
                return None
            return {"gh_stars": info.get("stars") or 0, "gh_forks": info.get("forks") or 0}
        if kind in ("hf_model", "hf_dataset"):
            fetch = f.get("hf_repo") or tools.fetch_hf_repo
            return fetch("models" if kind == "hf_model" else "datasets", key)
        if kind == "arxiv":
            fetch = f.get("hf_paper") or tools.fetch_hf_paper
            paper = fetch(key)
            # A paper may also ship a repo; stars are the stronger long-run signal, so fold
            # them in when the collector captured a link. Absent => paper counts alone.
            gh = (entry.get("links") or {}).get("github") or ""
            repos = tools.extract_github_repos(gh) if gh else []
            if repos:
                gh_fetch = f.get("github") or (lambda o, r: tools.fetch_github_repo(o, r, GH_TOKEN))
                info = gh_fetch(repos[0][0], repos[0][1])
                if info:
                    return {**(paper or {}), "gh_stars": info.get("stars") or 0}
            return paper
    except Exception as ex:                       # belt and braces: tools already swallow
        print(f"[track] observe failed for {entry.get('id')}: {ex}", file=sys.stderr)
        return None
    return None


# ---------------------------------------------------------------------------
# Ledger maintenance
# ---------------------------------------------------------------------------

def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _days_between(start: str, end: str) -> int:
    try:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days
    except Exception:
        return 0


def _apply_observation(entry: dict, signals: dict | None, today: str) -> dict:
    """Fold one run's observation into an entry. Missing observation increments `misses` and
    leaves the history untouched — an unreadable source is not evidence of cooling."""
    e = dict(entry)
    history: list[float] = list(e.get("mag_history") or [])
    if signals is None:
        e["misses"] = int(e.get("misses") or 0) + 1
        return e
    e["misses"] = 0
    # Merge rather than replace: a paper's hf_upvotes and a repo's gh_stars arrive from
    # different endpoints and neither observation should erase the other's field.
    e["signals"] = {**(e.get("signals") or {}), **signals}
    mag = round(magnitude(e), 4)
    prev = history[-1] if history else None
    history.append(mag)
    e["mag_history"] = history[-TTL_DAYS:] or [mag]
    e["peak_mag"] = round(max(mag, float(e.get("peak_mag") or 0)), 4)
    # streak counts consecutive runs actually observed; flat_runs counts runs without gain.
    e["streak"] = int(e.get("streak") or 0) + 1
    e["flat_runs"] = 0 if (prev is not None and mag > prev) else int(e.get("flat_runs") or 0) + 1
    e["last_seen"] = today
    return e


def _drop_reason(entry: dict, today: str) -> str | None:
    """Why this entry should leave the ledger, or None to keep it."""
    if int(entry.get("misses") or 0) >= MAX_MISSES:
        return "unreachable"
    if _days_between(entry.get("first_seen") or today, today) > TTL_DAYS:
        return "expired"
    if int(entry.get("flat_runs") or 0) >= MAX_FLAT_RUNS:
        return "flat"
    return None


def refresh(ledger: dict[str, dict], fetchers: dict | None = None,
            budget: int | None = None) -> tuple[dict[str, dict], dict[str, int]]:
    """Re-observe every tracked entry, then prune. Returns (new_ledger, stats).

    Entries are refreshed highest-peak-first so that when the budget runs out it is the
    least interesting rows that go unobserved. An unobserved row is left exactly as it was
    (no miss recorded) — we didn't look, so we learned nothing either way."""
    today = _today()
    budget = REFRESH_BUDGET if budget is None else budget
    stats = {"observed": 0, "missed": 0, "skipped": 0, "dropped": 0}
    order = sorted(ledger.values(),
                   key=lambda e: float(e.get("peak_mag") or 0), reverse=True)
    out: dict[str, dict] = {}
    for entry in order:
        iid = entry.get("id")
        if not iid:
            continue
        if entry.get("last_seen") == today:
            # Already observed this calendar day (a re-run of distill). Don't double-count
            # the streak or spend a fetch.
            out[iid] = entry
            stats["skipped"] += 1
            continue
        if budget <= 0:
            out[iid] = entry
            stats["skipped"] += 1
            continue
        budget -= 1
        signals = observe(entry, fetchers)
        updated = _apply_observation(entry, signals, today)
        stats["observed" if signals is not None else "missed"] += 1
        reason = _drop_reason(updated, today)
        if reason:
            stats["dropped"] += 1
            continue
        out[iid] = updated

    # Size cap: keep the biggest peaks. Runs after pruning so a cap never evicts an item
    # that pruning would have kept over one it dropped.
    if len(out) > MAX_TRACKED:
        keep = sorted(out.values(), key=lambda e: float(e.get("peak_mag") or 0),
                      reverse=True)[:MAX_TRACKED]
        stats["dropped"] += len(out) - len(keep)
        out = {e["id"]: e for e in keep}
    return out, stats


def promote(items: list[dict], ledger: dict[str, dict] | None = None) -> dict[str, dict]:
    """Add newly qualifying items to the ledger after a successful digest. Items already
    tracked keep their history (their streak came from `refresh`, not from being re-promoted).
    Returns the updated ledger; the caller saves it."""
    ledger = dict(ledger if ledger is not None else load_ledger())
    today = _today()
    for it in items:
        iid = it.get("id")
        if not iid or iid in ledger:
            continue
        if (it.get("score") or 0) < MIN_SCORE or not is_trackable(it):
            continue
        mag = round(magnitude(it), 4)
        ledger[iid] = {
            "id": iid,
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "source": it.get("source", ""),
            "category": it.get("category", "releases"),
            "links": {k: v for k, v in (it.get("links") or {}).items() if v},
            # Enough prose to re-score and to write a "still developing" line without
            # re-fetching the item. Truncated so the committed ledger stays small.
            "summary": (it.get("raw_summary") or "")[:400],
            "keywords": (it.get("keywords") or [])[:8],
            "first_seen": it.get("_first_seen") or today,
            "last_seen": today,
            "streak": 1,
            "misses": 0,
            "flat_runs": 0,
            "signals": dict(it.get("signals") or {}),
            "mag_history": [mag],
            "peak_mag": mag,
        }
    return ledger


# ---------------------------------------------------------------------------
# Carryover candidates
# ---------------------------------------------------------------------------

def _traction_delta(entry: dict) -> float:
    """Magnitude change over the tracked window. Positive => still climbing."""
    h = entry.get("mag_history") or []
    if len(h) < 2:
        return 0.0
    return round(h[-1] - h[0], 3)


def carryover_items(ledger: dict[str, dict]) -> list[dict]:
    """Turn live ledger entries into scored-item dicts the rest of the pipeline understands.

    Re-scored from CURRENT signals, so an item that has kept growing can outrank the day it
    was first published, and one that stalled falls out on its own. `fetched` is stamped now
    because the observation *is* from now — that is what keeps them inside synthesize's
    window check without weakening it."""
    from distill.score import heuristic_score          # local: avoids an import cycle
    from distill.focus import focus_match

    now = datetime.now(timezone.utc).isoformat()
    out: list[dict] = []
    for entry in ledger.values():
        item = {
            "id": entry.get("id"),
            "category": entry.get("category") or "releases",
            "title": entry.get("title", ""),
            "url": entry.get("url", ""),
            "source": entry.get("source", ""),
            "authors": [],
            "published": entry.get("first_seen"),
            "fetched": now,
            "raw_summary": entry.get("summary", ""),
            "links": dict(entry.get("links") or {}),
            "keywords": list(entry.get("keywords") or []),
            "signals": dict(entry.get("signals") or {}),
        }
        score, why = heuristic_score(item)
        if score < MIN_CARRYOVER_SCORE:
            continue
        item["score"] = score
        item["score_reasons"] = why
        item["focus_match"] = focus_match(item)
        # Carryover metadata: synthesize uses these to route the item to "Still developing"
        # and to bound how many carryovers can occupy the main list.
        item["carryover"] = True
        item["streak"] = int(entry.get("streak") or 1)
        item["first_seen"] = entry.get("first_seen", "")
        item["traction_delta"] = _traction_delta(entry)
        out.append(item)
    return out


def story_arcs(ledger: dict[str, dict] | None = None, min_streak: int = 3,
               cap: int = 10) -> list[dict]:
    """Tracked items observed across >= `min_streak` consecutive runs with rising traction.
    This is the query `delta.story_arcs` always wanted to answer and never could, because
    nothing accumulated a streak. Degrades to [] on any error."""
    try:
        ledger = load_ledger() if ledger is None else ledger
        arcs: list[dict] = []
        for entry in ledger.values():
            streak = int(entry.get("streak") or 0)
            history = entry.get("mag_history") or []
            if streak < min_streak or len(history) < 2:
                continue
            first, last = history[0], history[-1]
            if last <= first:
                continue
            arcs.append({
                "title": entry.get("title", ""),
                "url": entry.get("url", ""),
                "streak": streak,
                "first_seen": entry.get("first_seen", ""),
                "mag_pct_change": round((last - first) / max(first, 0.01) * 100, 1),
            })
        arcs.sort(key=lambda a: (a["mag_pct_change"], a["streak"]), reverse=True)
        return arcs[:cap]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Stage entrypoint
# ---------------------------------------------------------------------------

def write_carryovers(items: list[dict]) -> int:
    """Drop carryover candidates into data/scored/ so score.py's consumers pick them up with
    no special-casing. Runs AFTER score.py, which clears the directory each run. Never
    overwrites a file score.py just wrote: a fresh observation of an item beats a stale one."""
    SCORED.mkdir(parents=True, exist_ok=True)
    written = 0
    for it in items:
        out = SCORED / f"{it['id'].replace(':', '_').replace('/', '_')}.json"
        if out.exists():                 # collected again today — the fresh copy wins
            continue
        out.write_text(json.dumps(it, indent=2))
        written += 1
    return written


def main() -> None:
    ledger = load_ledger()
    if not ledger:
        print("[track] ledger empty — nothing to re-observe yet "
              "(entries are added after the next successful digest)")
        return
    ledger, stats = refresh(ledger)
    save_ledger(ledger)
    items = carryover_items(ledger)
    n = write_carryovers(items)
    print(f"[track] {len(ledger)} tracked · observed={stats['observed']} "
          f"missed={stats['missed']} skipped={stats['skipped']} dropped={stats['dropped']} "
          f"· {n} carryover candidates")


if __name__ == "__main__":
    main()
