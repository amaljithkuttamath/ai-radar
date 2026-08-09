"""Optional agentic-ish enrichment stage. Runs between score and distill when RADAR_AGENT=on.

NOT an agent loop. For each of the top-N scored items it does deterministic tool fetches
(GitHub stars, HN points — see distill/tools.py; no model), then makes exactly ONE model call
to write a brief over the assembled evidence. Total model cost = N briefs (+ the later 1
synthesis call) = N+1. That bound was sized for a free per-day call quota; it still matters
on a metered backend, where it caps spend per run rather than calls per day.

Backend-agnostic: reuses synthesize.py's caller dispatch and its `resolve_backend` rules, so
RADAR_MODEL_BACKEND=anthropic (paid) or ollama (local, no limits) work unchanged. There is no
template equivalent here — a brief is model output by definition — so a backend with no caller
(dryrun, or `auto` with no key) yields evidence-only briefs rather than a degraded one.

Rate-limit survival: a hard per-run call budget, retry-on-429 with Retry-After, and a per-item
checkpoint (each brief is written to disk before the next call) so a killed run still publishes
whatever it finished.

Run: RADAR_AGENT=on python -m distill.enrich
"""
from __future__ import annotations
import os, sys, json, time, urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import ROOT, parse_window, _merge_signals  # noqa: E402
from distill import tools  # noqa: E402
from distill.rank import rank_key  # noqa: E402
from distill.synthesize import call_anthropic, call_ollama, resolve_backend  # noqa: E402

WINDOW = os.environ.get("WINDOW", "48h")
# Resolve through the same rules as synthesis so `auto` and the retired `github` mean the
# same thing in both stages. Enrichment has no template equivalent — a brief is model
# output by definition — so an unresolvable backend yields evidence-only briefs, which is
# what `_model_brief` already does for dryrun.
BACKEND, _ = resolve_backend(os.environ.get("RADAR_MODEL_BACKEND", "dryrun").lower())
TOP_N = int(os.environ.get("RADAR_AGENT_TOP_N", "8"))        # match MAX_ITEMS so shown==enriched
BUDGET = int(os.environ.get("RADAR_AGENT_BUDGET", "10"))     # 8 briefs + margin
SLEEP = float(os.environ.get("RADAR_AGENT_SLEEP", "5"))       # spacing between model calls
GH_TOKEN = os.environ.get("GITHUB_TOKEN")   # still used by tools.py for repo/star lookups

SCORED = ROOT / "data" / "scored"
ENRICHED = ROOT / "data" / "enriched"
BRIEF_SPEC = (ROOT / "distill" / "brief_spec.md").read_text()

# `github` is gone from this map along with the two-tier model split it existed to serve:
# GitHub Models metered a High tier (gpt-4.1, 50/day) separately from a Low tier
# (gpt-4.1-mini, 150/day), so briefs deliberately used the cheaper one to avoid starving
# the single synthesis call. Neither tier nor endpoint exists now. Anthropic bills by
# token with no per-tier daily cap, so briefs and synthesis share one model and the split
# has nothing left to protect.
_CALLERS = {"anthropic": call_anthropic, "ollama": call_ollama}


def _safe_id(item_id: str) -> str:
    return item_id.replace(":", "_").replace("/", "_")


def load_top_n() -> list[dict]:
    """In-window scored items, highest score first, capped at TOP_N."""
    cutoff = datetime.now(timezone.utc) - parse_window(WINDOW)
    items = []
    if SCORED.exists():
        for p in SCORED.glob("*.json"):
            try:
                it = json.loads(p.read_text())
                fetched = datetime.fromisoformat(it.get("fetched", ""))
            except (ValueError, OSError, json.JSONDecodeError):
                continue
            if fetched >= cutoff:
                it["_scored_path"] = str(p)
                items.append(it)
    items.sort(key=rank_key, reverse=True)   # same key as synthesize -> shown == enriched
    return items[:TOP_N]


def build_evidence(item: dict) -> dict:
    """Deterministic fetches (no model). Returns the evidence bundle for one item."""
    evidence = {"abstract": (item.get("raw_summary") or "")[:1500]}
    repo = tools.best_repo(item, GH_TOKEN)
    if repo:
        evidence["github"] = repo
    hn = tools.fetch_hn_signal(item.get("title", ""))
    if hn:
        evidence["hn"] = hn
    return evidence


def _model_brief(item: dict, evidence: dict) -> str:
    caller = _CALLERS.get(BACKEND)
    if caller is None:                     # dryrun / unknown -> no model, evidence-only brief
        return ""
    user = (
        "Write the brief per the spec for this item.\n\n"
        f"TITLE: {item.get('title','')}\nSOURCE: {item.get('source','')}\n"
        f"URL: {item.get('url','')}\nSCORE: {item.get('score')}\n\n"
        f"EVIDENCE (fetched, real):\n{json.dumps(evidence, indent=2)}"
    )
    return caller(BRIEF_SPEC, user)


def _brief_with_retry(item: dict, evidence: dict, budget: list[int]) -> str | None:
    """One brief call, with retry-on-429. Each real attempt spends from the shared budget;
    dryrun/unknown backends make no call and cost nothing."""
    if BACKEND not in _CALLERS:
        return _model_brief(item, evidence)     # dryrun -> "" , no budget spent
    for attempt in range(3):
        if budget[0] <= 0:
            print("[enrich] budget exhausted; stopping briefs", file=sys.stderr)
            return None
        budget[0] -= 1
        try:
            return _model_brief(item, evidence)
        except urllib.error.HTTPError as ex:
            if ex.code == 429 and attempt < 2:
                wait = int(ex.headers.get("Retry-After", "30") or 30) + 2
                print(f"[enrich] 429; retry in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"[enrich] brief failed ({ex.code}): {item.get('id')}", file=sys.stderr)
            return None
        except Exception as ex:
            print(f"[enrich] brief failed: {item.get('id')}: {ex}", file=sys.stderr)
            return None
    return None


def _new_signals(evidence: dict) -> dict:
    sig = {}
    if "github" in evidence:
        sig["gh_stars"] = evidence["github"]["stars"]
    if "hn" in evidence:
        sig["hn_points"] = evidence["hn"]["points"]
        sig["hn_url"] = evidence["hn"].get("url")
    return sig


def merge_signals(item: dict, evidence: dict) -> None:
    """Persist gh_stars / hn_points so they survive into the next run. score.py rebuilds
    data/scored/ from data/raw/ every run, so the durable home is the RAW file — writing there
    (via the same helper collectors use) is what makes score.py's gh_stars>=50 heuristic fire
    next time. Also update this run's scored file so the digest sees the signals immediately."""
    sig = _new_signals(evidence)
    if not sig:
        return
    _merge_signals(item["id"], sig)        # durable: lands in data/raw/<...>.json for next run

    path = item.get("_scored_path")         # this run: so synthesize's top-N JSON shows them now
    if path:
        try:
            stored = json.loads(Path(path).read_text())
            stored["signals"] = {**(stored.get("signals") or {}), **sig}
            Path(path).write_text(json.dumps(stored, indent=2))
        except (OSError, json.JSONDecodeError):
            pass


def main() -> None:
    ENRICHED.mkdir(parents=True, exist_ok=True)
    for old in ENRICHED.glob("*.json"):    # only in-window items should persist
        old.unlink()

    items = load_top_n()
    budget = [BUDGET]                       # shared, mutable ceiling
    n_briefs = 0
    for i, item in enumerate(items):
        evidence = build_evidence(item)     # deterministic, no model, no budget cost
        brief = _brief_with_retry(item, evidence, budget) if budget[0] > 0 else None
        ENRICHED_path = ENRICHED / f"{_safe_id(item['id'])}.json"
        ENRICHED_path.write_text(json.dumps({       # checkpoint BEFORE sleeping
            "item_id": item["id"],
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "evidence": evidence,
            "brief": brief,
        }, indent=2))
        merge_signals(item, evidence)
        if brief:
            n_briefs += 1
        if i < len(items) - 1 and budget[0] > 0 and BACKEND in _CALLERS:
            time.sleep(SLEEP)
    print(f"[enrich] {len(items)} items enriched, {n_briefs} briefs written "
          f"(backend={BACKEND}, budget left={budget[0]}/{BUDGET})")


if __name__ == "__main__":
    main()
