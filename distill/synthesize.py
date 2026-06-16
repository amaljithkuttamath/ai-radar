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
from distill.delta import compute_delta, save_state, story_arcs  # noqa: E402
from distill.focus import active_terms as _focus_active_terms, _term_hit, _blob as _focus_blob  # noqa: E402
from distill.cluster import cluster_items  # noqa: E402

WINDOW = os.environ.get("WINDOW", "48h")
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "10"))
MARKET = os.environ.get("MARKET", "off").lower() == "on"
THRESHOLD = int(os.environ.get("INCLUDE_THRESHOLD", "2"))
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
RELEASE_SLOTS = int(os.environ.get("RELEASE_SLOTS", "5"))

# How many ranked movers to send per bucket. The model only writes a sentence or two for the
# "What changed" section, so it needs counts + a ranked sample, not every mover serialized in
# full. A busy 7d window can mark 300+ items "new"; dumping them all blew past GitHub Models'
# ~16k-token input ceiling (HTTP 413). This caps the MOVERS block losslessly for the report's
# purposes: exact counts and category breakdowns are preserved; only the long tail of
# per-item detail (which never reaches the digest) is summarized away.
MOVERS_TOP = int(os.environ.get("MOVERS_TOP", "30"))


def _build_provenance(i: dict) -> str:
    """Assemble a concise, deterministic provenance string from available item signals.
    Omits any field that is missing or zero — never fabricates information."""
    parts: list[str] = []
    # Score reasons from heuristic (e.g. 'frontier/strong-group authorship')
    for r in (i.get("score_reasons") or []):
        if r:
            parts.append(r)
    # Traction figures — only emit non-zero values
    sig = i.get("signals") or {}
    gh = sig.get("gh_stars") or 0
    hf_up = sig.get("hf_upvotes") or 0
    hn = sig.get("hn_points") or 0
    if gh:
        parts.append(f"{gh} gh_stars")
    if hf_up:
        parts.append(f"{hf_up} hf_upvotes")
    if hn:
        parts.append(f"{hn} hn_points")
    # FOCUS term hits — which specific term matched
    if i.get("focus_match"):
        try:
            blob = _focus_blob(i)
            terms = _focus_active_terms()
            hit_terms = [t for t in terms if _term_hit(t, blob)]
            if hit_terms:
                parts.append("matches FOCUS:" + ",".join(hit_terms[:3]))
            else:
                parts.append("matches FOCUS")
        except Exception:
            parts.append("matches FOCUS")
    return " · ".join(parts) if parts else ""


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


def build_prompt(items: list[dict], _strip_briefs: bool = False,
                 max_candidates: int | None = None,
                 summary_chars: int | None = None) -> tuple[str, str, int]:
    # max_candidates / summary_chars let the 413 fallback shrink the request below the
    # backend's input ceiling. Default to the module caps when unset.
    max_candidates = MAX_CANDIDATES if max_candidates is None else max_candidates
    summary_chars = SUMMARY_CHARS if summary_chars is None else summary_chars
    enriched = load_enriched()
    keep = [i for i in items if (i.get("score") or 0) >= max(2, THRESHOLD - 1)]

    # Category quotas: guarantee non-research a few slots (they score lower than research
    # papers structurally, e.g. a vendor blog has no HF/GitHub trending). Lower floor (>=1)
    # lets them in; the model still sees their real score and routes them correctly.
    research = [i for i in keep if i["category"] == "research"]
    hardware = [i for i in items if i["category"] == "hardware" and (i.get("score") or 0) >= 1]
    releases = [i for i in items if i["category"] == "releases" and (i.get("score") or 0) >= 1]
    research_slots = max(0, max_candidates - HARDWARE_SLOTS - RELEASE_SLOTS)
    chosen = (research[:research_slots]
              + hardware[:HARDWARE_SLOTS]
              + releases[:RELEASE_SLOTS])
    chosen.sort(key=rank_key, reverse=True)   # model sees a single ranked list

    compact = []
    for i in chosen:
        sig = i.get("signals") or {}
        prov = _build_provenance(i)
        row = {
            "title": i["title"], "url": i["url"], "source": i["source"],
            "category": i["category"], "score": i["score"],
            "reasons": i.get("score_reasons", []),
            "focus_match": i.get("focus_match", False),
            "summary": (i.get("raw_summary") or "")[:summary_chars],
            # Promote traction to explicit named fields so the spec can REQUIRE citing them
            # (buried inside `signals` the model flattens them into "growing interest").
            "hf_upvotes": sig.get("hf_upvotes") or 0,
            "gh_stars": sig.get("gh_stars") or 0,
            "hn_points": sig.get("hn_points") or 0,
            "reddit_score": sig.get("reddit_score") or 0,
        }
        if prov:
            row["provenance"] = prov
        if not _strip_briefs:
            e = enriched.get(i["id"])
            if e and e.get("brief"):
                del row["summary"]
                row["brief"] = e["brief"][:summary_chars]
        compact.append(row)
    system = SPEC
    today = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    # Movers vs. the previous run — turns a standalone digest into a radar. Computed over the
    # full scored set (not just `chosen`) so a climbing item that fell out of the cut still
    # registers. Empty/first-run delta degrades to no "What changed" section.
    delta = compute_delta(items)
    delta_note = (
        "\n\nMOVERS since the previous run (use these to write the 'What changed' section; "
        "if first_run is true, skip that section). Counts are exact; `top` lists the highest-"
        "ranked movers in each bucket (the long tail is summarized to counts):\n"
        + json.dumps(_compact_delta(delta), indent=2) + "\n"
    )
    # Story arcs: items with multi-run streak + rising traction. Cap at 10; skip when none.
    arcs = story_arcs()
    arcs_note = ""
    if arcs:
        arcs_note = (
            "\n\nSTORY ARCS (items with rising traction across >= 3 consecutive runs; "
            "use these for the optional 'Story arcs' subsection in the digest):\n"
            + json.dumps(arcs, indent=2) + "\n"
        )
    # Topic clusters: group candidates into emergent themes. Degrade to empty when
    # clustering yields nothing useful, which keeps the main list flat.
    clusters: list[dict] = []
    try:
        clusters = cluster_items(chosen)
    except Exception:
        clusters = []
    clusters_note = ""
    if clusters:
        # Build a compact id->label map for items in a named cluster
        id_to_label: dict[str, str] = {}
        for c in clusters:
            for iid in c.get("item_ids") or []:
                id_to_label[iid] = c["label"]
        clusters_note = (
            "\n\nTOPIC CLUSTERS (emergent themes for the main list; group items under these "
            "short headers in the output. Items not in a cluster go under their natural "
            "position. Degrade to the flat list if clusters don't add clarity):\n"
            + json.dumps(clusters, indent=2) + "\n"
        )
    user = (
        f"TODAY={today}  WINDOW={WINDOW}  MAX_ITEMS={MAX_ITEMS}  "
        f"MARKET={'on' if MARKET else 'off'}  INCLUDE_THRESHOLD={THRESHOLD}\n\n"
        f"Date the report {today}. Use ONLY that date in any header; do not infer a date from "
        "your training data or the items.\n\n"
        + delta_note + arcs_note + clusters_note +
        "\nHere are the scored candidate items (JSON). Produce the digest per the spec. "
        "The heuristic traction score is 0–4 from observable signals; add up to +1 yourself "
        "for genuine novelty / challenging a common assumption (max 5), and explain it. "
        "Items with focus_match=true are in a FOCUS area — use that ONLY as a re-rank boost "
        "for ordering and relevance, never added to the score. Skip low-signal items rather "
        "than padding.\n\n"
        f"{json.dumps(compact, indent=2)}"
    )
    return system, user, len(compact)


def _compact_delta(delta: dict, top: int = MOVERS_TOP) -> dict:
    """Condense the movers delta for the prompt without losing reader-visible signal.
    Keeps the exact per-bucket count plus the highest-scoring sample of each bucket as the
    rows the delta actually stores (title/url/score, and score/mag deltas for climbing/
    cooled). The digest's 'What changed' section is a sentence or two, so the full per-item
    dump — which can be 300+ objects on a busy window and overflow the model's ~16k input
    limit — is unnecessary. Counts stay exact; only the long tail of rows is dropped."""
    out: dict = {"first_run": delta.get("first_run")}
    for bucket in ("new", "climbing", "cooled"):
        rows = [x for x in (delta.get(bucket) or []) if isinstance(x, dict)]
        # Sort by the strongest signal each bucket carries: score-tier change for
        # climbing/cooled, else raw score. (Delta rows don't carry traction signals, so
        # rank_key can't be used here.)
        rows = sorted(rows, key=lambda r: (r.get("score_delta", 0), r.get("score", 0)),
                      reverse=True)
        out[bucket] = {"count": len(rows), "top": rows[:top]}
    return out


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


def call_template(system: str, user: str) -> str:
    """No-model backend: generate a structured report from the top scored items directly.
    Useful for testing the pipeline or running without API keys."""
    import json, re
    json_match = re.search(r'\[\s*\{.*\}\s*\]', user, re.DOTALL)
    if not json_match:
        return "# AI Radar — Template Error\n\nCould not extract items from prompt."
    try:
        items = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return "# AI Radar — Template Error\n\nCould not parse items JSON."

    today = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    lines = [
        f"# AI Radar — {today}",
        "",
        f"**Top-line** — {len(items)} candidate items scored in the last {WINDOW}. "
        "Run with `RADAR_MODEL_BACKEND=github` or `anthropic` for model synthesis and insights.",
        ""
    ]

    # Main list — respect THRESHOLD and MAX_ITEMS
    main = [i for i in items if (i.get("score") or 0) >= THRESHOLD]
    if main:
        lines.append(f"**Main list** ({len(main)} scored ≥{THRESHOLD}, showing top {min(len(main), MAX_ITEMS)})")
        for i in main[:MAX_ITEMS]:
            sigs = []
            if i.get("hf_upvotes"): sigs.append(f"{i['hf_upvotes']} HF upvotes")
            if i.get("gh_stars"): sigs.append(f"{i['gh_stars']} GitHub stars")
            if i.get("hn_points"): sigs.append(f"{i['hn_points']} HN points")
            if i.get("reddit_score"): sigs.append(f"{i['reddit_score']} Reddit score")
            signal_str = " · ".join(sigs) if sigs else "no tracked traction signal"
            summary = (i.get("summary") or i.get("brief") or "")[:300]
            lines.append(f"- **{i['title']}** [{i['category']}] · score {i['score']}/5")
            lines.append(f"  Source: {i['source']} · [{i['url']}]({i['url']})")
            lines.append(f"  Signal: {signal_str}")
            if i.get("reasons"):
                lines.append(f"  Reasons: {', '.join(i['reasons'])}")
            if summary:
                lines.append(f"  New: {summary}")
            lines.append("")
    else:
        lines.append(f"**Main list**")
        lines.append(f"_No items scored ≥{THRESHOLD} in this window._")
        lines.append("")

    # Watch list — items exactly one point below threshold
    watch = [i for i in items if (i.get("score") or 0) == max(1, THRESHOLD - 1)]
    if watch:
        lines.append(f"**Watch-list** ({len(watch)} items)")
        for i in watch[:8]:
            sigs = []
            if i.get("hf_upvotes"): sigs.append(f"{i['hf_upvotes']} HF upvotes")
            if i.get("gh_stars"): sigs.append(f"{i['gh_stars']} GitHub stars")
            if i.get("hn_points"): sigs.append(f"{i['hn_points']} HN points")
            if i.get("reddit_score"): sigs.append(f"{i['reddit_score']} Reddit score")
            signal_str = " · ".join(sigs) if sigs else "no tracked traction signal"
            lines.append(f"- {i['title']} · {i['source']} · score {i['score']}/5 · {signal_str}")
        lines.append("")

    lines.append("**Insights**")
    lines.append("- Template backend shows raw scored items without model judgment.")
    lines.append(f"- Set a model backend for synthesis: `export RADAR_MODEL_BACKEND=github` + `export GITHUB_TOKEN=...`")
    lines.append("")

    lines.append("**Action items**")
    lines.append("- Review main-list items for personal relevance.")
    lines.append(f"- Re-run with `WINDOW=7d` if the {WINDOW} window is too quiet.")
    lines.append("")

    return "\n".join(lines)





def _log_prompt_stats(system: str, user: str, n_items: int,
                       candidates: int, shrink_level: int) -> None:
    """Log approximate prompt token count and key sizing metrics to stderr.
    Token estimate: len // 4 (industry-standard rough conversion). No deps.
    Format: [distill] prompt ~NNNN tok | candidates=N | shrink_level=N | items=N"""
    tok = (len(system) + len(user)) // 4
    print(f"[distill] prompt ~{tok} tok | candidates={candidates} "
          f"| shrink_level={shrink_level} | items={n_items}", file=sys.stderr)


def main() -> None:
    items = load_scored()
    system, user, n_cand = build_prompt(items)
    if BACKEND == "anthropic":
        _log_prompt_stats(system, user, len(items), n_cand, 0)
        report = call_anthropic(system, user)
    elif BACKEND == "github":
        attempts = [
            dict(),
            dict(_strip_briefs=True),
            dict(_strip_briefs=True, max_candidates=18, summary_chars=240),
            dict(_strip_briefs=True, max_candidates=12, summary_chars=180),
            dict(_strip_briefs=True, max_candidates=max(MAX_ITEMS, 8), summary_chars=120),
        ]
        report = None
        last_413: urllib.error.HTTPError | None = None
        for n, kw in enumerate(attempts):
            if n:
                print(f"[distill] 413 on synthesis; shrinking payload "
                      f"(attempt {n}/{len(attempts)-1}: {kw})", file=sys.stderr)
                system, user, n_cand = build_prompt(items, **kw)
            _log_prompt_stats(system, user, len(items), n_cand, n)
            try:
                report = call_github(system, user)
                break
            except urllib.error.HTTPError as ex:
                if ex.code == 413:
                    last_413 = ex
                    continue
                raise
        if report is None:
            print("[distill] still 413 after shrinking to the floor; giving up",
                  file=sys.stderr)
            raise last_413  # type: ignore[misc]
    elif BACKEND == "ollama":
        _log_prompt_stats(system, user, len(items), n_cand, 0)
        report = call_ollama(system, user)
    elif BACKEND == "template":
        report = call_template(system, user)
    else:
        _log_prompt_stats(system, user, len(items), n_cand, 0)
        report = ("# DRYRUN — assembled prompt (no model called)\n\n"
                  "Set RADAR_MODEL_BACKEND=github (free), anthropic, ollama, or template to generate the digest.\n\n"
                  "## SYSTEM\n" + system + "\n\n## USER\n" + user)
    out = ROOT / "reports" / f"{datetime.now(timezone.utc):%Y-%m-%d}-digest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    # Snapshot state only for real backends (template and dryrun don't advance state).
    if BACKEND not in ("dryrun", "template"):
        save_state(items)
    print(f"[distill] wrote {out}  (backend={BACKEND}, {len(items)} scored items)")


if __name__ == "__main__":
    main()
