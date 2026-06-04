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
import os, sys, json, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import ROOT, parse_window  # noqa: E402

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
    items.sort(key=lambda x: (x.get("score") or 0,
                              1 if x.get("focus_match") else 0,
                              x.get("signals", {}).get("hf_upvotes") or 0), reverse=True)
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


def build_prompt(items: list[dict]) -> tuple[str, str]:
    enriched = load_enriched()
    keep = [i for i in items if (i.get("score") or 0) >= max(2, THRESHOLD - 1)]
    compact = []
    for i in keep[:MAX_CANDIDATES]:
        row = {
            "title": i["title"], "url": i["url"], "source": i["source"],
            "category": i["category"], "score": i["score"],
            "reasons": i.get("score_reasons", []),
            "focus_match": i.get("focus_match", False),
            "summary": (i.get("raw_summary") or "")[:SUMMARY_CHARS],
            "signals": i.get("signals", {}),
        }
        e = enriched.get(i["id"])
        if e and e.get("brief"):
            # A brief already reasons over fetched evidence (GitHub/HN); prefer it over the
            # raw abstract so the digest model synthesizes across dense briefs, not raw text.
            row["brief"] = e["brief"]
        compact.append(row)
    system = SPEC
    user = (
        f"WINDOW={WINDOW}  MAX_ITEMS={MAX_ITEMS}  MARKET={'on' if MARKET else 'off'}  "
        f"INCLUDE_THRESHOLD={THRESHOLD}\n\n"
        "Here are the scored candidate items (JSON). Produce the digest per the spec. "
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


def call_github(system: str, user: str) -> str:
    """GitHub Models — OpenAI-compatible, free, auth via GITHUB_TOKEN (models:read scope).
    Default backend in CI: no paid key, no card. https://models.github.ai/inference"""
    body = json.dumps({
        "model": os.environ.get("RADAR_GITHUB_MODEL", "openai/gpt-4o-mini"),
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
        report = call_github(system, user)
    elif BACKEND == "ollama":
        report = call_ollama(system, user)
    else:
        report = ("# DRYRUN — assembled prompt (no model called)\n\n"
                  "Set RADAR_MODEL_BACKEND=github (free), anthropic, or ollama to generate the digest.\n\n"
                  "## SYSTEM\n" + system + "\n\n## USER\n" + user)
    out = ROOT / "reports" / f"{datetime.now(timezone.utc):%Y-%m-%d}-digest.md"
    out.parent.mkdir(parents=True, exist_ok=True)   # reports/ is gitignored -> absent on fresh CI
    out.write_text(report)
    print(f"[distill] wrote {out}  (backend={BACKEND}, {len(items)} scored items)")


if __name__ == "__main__":
    main()
