"""Distillation: load scored items in WINDOW, send them to a model with distill/digest.md
as the system prompt, write reports/<date>-digest.md.

Backend-agnostic. Set RADAR_MODEL_BACKEND:
  anthropic  -> uses ANTHROPIC_API_KEY (synthesis quality)
  github     -> uses GitHub Models, auth via GITHUB_TOKEN (free; default in CI)
  ollama     -> uses local http://localhost:11434 (cheap)
  dryrun     -> no model; dumps the assembled prompt for inspection (default)

Run: python -m distill.synthesize
"""
from __future__ import annotations
import os, sys, json, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import ROOT, parse_window  # noqa: E402
from distill.rank import rank_key  # noqa: E402
from distill.delta import compute_delta, save_state  # noqa: E402

WINDOW = os.environ.get("WINDOW", "48h")
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "8"))
MARKET = os.environ.get("MARKET", "off").lower() == "on"
THRESHOLD = int(os.environ.get("INCLUDE_THRESHOLD", "3"))
BACKEND = os.environ.get("RADAR_MODEL_BACKEND", "dryrun").lower()
SCORED = ROOT / "data" / "scored"
ENRICHED = ROOT / "data" / "enriched"
SPEC = (ROOT / "distill" / "digest.md").read_text()

# Payload caps. GitHub Models' free tier has a ~16k-token INPUT limit, so the candidate
# set must stay small there (a busy 7d window scores 500+ items). The digest only emits
# MAX_ITEMS anyway, so a tight candidate list is plenty. Other backends can take more.
# Overridable via env for tuning.
_CAND_DEFAULT = {"github": 24}.get(BACKEND, 60)
_SUMMARY_DEFAULT = {"github": 360}.get(BACKEND, 600)
MAX_CANDIDATES = int(os.environ.get("MAX_CANDIDATES", _CAND_DEFAULT))
SUMMARY_CHARS = int(os.environ.get("SUMMARY_CHARS", _SUMMARY_DEFAULT))

# Reserve main-list slots for non-research so hardware/releases (which score lower than
# research papers structurally) aren't crowded out. 0/0 reverts to research-only behavior.
HARDWARE_SLOTS = int(os.environ.get("HARDWARE_SLOTS", "2"))
RELEASE_SLOTS = int(os.environ.get("RELEASE_SLOTS", "1"))


def load_scored() -> list[dict]:
    # Enforce the window on read too: synthesize can be run independently of score.py, so
    # don't trust data/scored/ to contain only in-window items.
    cutoff = datetime.now(timezone.utc) - parse_window(WINDOW)
    items = []
    if SCORED.exists():
        for p in SCORED.glob("*.json"):
            try:
                it = json.loads(p.read_text())
            except Exception:
                continue
            try:
                fetched = datetime.fromisoformat(it.get("fetched", ""))
            except ValueError:
                continue
            if fetched >= cutoff:
                items.append(it)
    # rank_key (score + signal magnitude) is primary; focus_match only breaks exact ties,
    # staying a re-rank boost rather than overriding traction.
    items.sort(key=lambda x: (rank_key(x), 1 if x.get("focus_match") else 0), reverse=True)
    return items


def load_enriched() -> dict[str, dict]:
    """Per-item enrichment briefs from the (optional) enrich stage, keyed by item id.
    Empty when RADAR_AGENT never ran — synthesis then behaves exactly as before."""
    out: dict[str, dict] = {}
    if ENRICHED.exists():
        for p in ENRICHED.glob("*.json"):
            try:
                e = json.loads(p.read_text())
            except Exception:
                continue
            if e.get("item_id"):
                out[e["item_id"]] = e
    return out


def build_prompt(items: list[dict], _strip_briefs: bool = False) -> tuple[str, str]:
    enriched = load_enriched()
    keep = [i for i in items if (i.get("score") or 0) >= max(2, THRESHOLD - 1)]

    # Category quotas: guarantee non-research a few slots (they score lower than research
    # papers structurally, e.g. a vendor blog has no HF/GitHub trending). Lower floor (>=1)
    # lets them in; the model still sees their real score and routes them correctly.
    research = [i for i in keep if i["category"] == "research"]
    hardware = [i for i in items if i["category"] == "hardware" and (i.get("score") or 0) >= 1]
    releases = [i for i in items if i["category"] == "releases" and (i.get("score") or 0) >= 1]
    research_slots = max(0, MAX_CANDIDATES - HARDWARE_SLOTS - RELEASE_SLOTS)
    chosen = (research[:research_slots]
              + hardware[:HARDWARE_SLOTS]
              + releases[:RELEASE_SLOTS])
    chosen.sort(key=rank_key, reverse=True)   # model sees a single ranked list

    compact = []
    for i in chosen:
        sig = i.get("signals") or {}
        row = {
            "title": i["title"], "url": i["url"], "source": i["source"],
            "category": i["category"], "score": i["score"],
            "reasons": i.get("score_reasons", []),
            "focus_match": i.get("focus_match", False),
            "summary": (i.get("raw_summary") or "")[:SUMMARY_CHARS],
            # Promote traction to explicit named fields so the spec can REQUIRE citing them
            # (buried inside `signals` the model flattens them into "growing interest").
            "hf_upvotes": sig.get("hf_upvotes") or 0,
            "gh_stars": sig.get("gh_stars") or 0,
            "hn_points": sig.get("hn_points") or 0,
        }
        if not _strip_briefs:
            e = enriched.get(i["id"])
            if e and e.get("brief"):
                del row["summary"]
                row["brief"] = e["brief"][:SUMMARY_CHARS]
        compact.append(row)
    system = SPEC
    today = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    # Movers vs. the previous run — turns a standalone digest into a radar. Computed over the
    # full scored set (not just `chosen`) so a climbing item that fell out of the cut still
    # registers. Empty/first-run delta degrades to no "What changed" section.
    delta = compute_delta(items)
    delta_note = (
        "\n\nMOVERS since the previous run (use these to write the 'What changed' section; "
        "if first_run is true, skip that section):\n" + json.dumps(delta, indent=2) + "\n"
    )
    user = (
        f"TODAY={today}  WINDOW={WINDOW}  MAX_ITEMS={MAX_ITEMS}  "
        f"MARKET={'on' if MARKET else 'off'}  INCLUDE_THRESHOLD={THRESHOLD}\n\n"
        f"Date the report {today}. Use ONLY that date in any header; do not infer a date from "
        "your training data or the items.\n\n"
        + delta_note +
        "\nHere are the scored candidate items (JSON). Produce the digest per the spec. "
        "The heuristic traction score is 0–4 from observable signals; add up to +1 yourself "
        "for genuine novelty / challenging a common assumption (max 5), and explain it. "
        "Items with focus_match=true are in a FOCUS area — use that ONLY as a re-rank boost "
        "for ordering and relevance, never added to the score. Skip low-signal items rather "
        "than padding.\n\n"
        f"{json.dumps(compact, indent=2)}"
    )
    return system, user


def call_anthropic(system: str, user: str) -> str:
    body = json.dumps({
        "model": os.environ.get("RADAR_ANTHROPIC_MODEL", "claude-opus-4-8"),
        "max_tokens": 4000, "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return "".join(b.get("text", "") for b in data.get("content", []))


def call_github(system: str, user: str, model: str | None = None) -> str:
    """GitHub Models — OpenAI-compatible, free, auth via GITHUB_TOKEN (models:read scope).
    Default backend in CI: no paid key, no card. https://models.github.ai/inference
    `model` lets callers pick a tier (synthesis uses the strong gpt-4.1; briefs use the
    cheaper-quota gpt-4.1-mini so 8 brief calls don't exhaust the High-tier daily budget)."""
    body = json.dumps({
        "model": model or os.environ.get("RADAR_GITHUB_MODEL", "openai/gpt-4.1"),
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(
        "https://models.github.ai/inference/chat/completions", data=body,
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "Content-Type": "application/json",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2026-03-10"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


def call_ollama(system: str, user: str) -> str:
    body = json.dumps({
        "model": os.environ.get("RADAR_OLLAMA_MODEL", "qwen3:4b"),
        "system": system, "prompt": user, "stream": False,
    }).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=body,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read()).get("response", "")


def main() -> None:
    items = load_scored()
    system, user = build_prompt(items)
    if BACKEND == "anthropic":
        report = call_anthropic(system, user)
    elif BACKEND == "github":
        try:
            report = call_github(system, user)
        except urllib.error.HTTPError as ex:
            if ex.code == 413:
                # Briefs made the payload too large; rebuild without them and retry once.
                print("[distill] 413 on synthesis; retrying without enriched briefs",
                      file=sys.stderr)
                system, user = build_prompt(items, _strip_briefs=True)
                report = call_github(system, user)
            else:
                raise
    elif BACKEND == "ollama":
        report = call_ollama(system, user)
    else:
        report = ("# DRYRUN — assembled prompt (no model called)\n\n"
                  "Set RADAR_MODEL_BACKEND=github (free), anthropic, or ollama to generate the digest.\n\n"
                  "## SYSTEM\n" + system + "\n\n## USER\n" + user)
    out = ROOT / "reports" / f"{datetime.now(timezone.utc):%Y-%m-%d}-digest.md"
    out.parent.mkdir(parents=True, exist_ok=True)   # reports/ is gitignored -> absent on fresh CI
    out.write_text(report)
    # Snapshot this run's ranked set so the NEXT run can compute movers against it. Written
    # only after a successful digest, and only for real backends (dryrun shouldn't advance
    # state, or you'd lose the genuine "new today" diff on the next real run).
    if BACKEND != "dryrun":
        save_state(items)
    print(f"[distill] wrote {out}  (backend={BACKEND}, {len(items)} scored items)")


if __name__ == "__main__":
    main()
