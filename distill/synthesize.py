"""Distillation: load scored items in WINDOW, send them to a model with distill/digest.md
as the system prompt, write reports/<date>-digest.md.

Backend-agnostic. Set RADAR_MODEL_BACKEND:
  auto       -> anthropic if ANTHROPIC_API_KEY, else openai if OPENAI_API_KEY, else
                template (default in CI)
  anthropic  -> uses ANTHROPIC_API_KEY (synthesis quality)
  openai     -> the shared provider (llm.py): RADAR_LLM_BASE_URL + RADAR_LLM_API_KEY,
                one OpenAI-compatible endpoint used by synthesis AND the grader. A
                gateway such as OpenRouter serves many model families through it, which
                is what lets one account satisfy the grader's separation rule.
  ollama     -> uses local http://localhost:11434 (cheap)
  template   -> no model; deterministic digest assembled from the scored items
  dryrun     -> no model; dumps the assembled prompt for inspection (default locally)
  github     -> RETIRED, see below. Accepted and redirected so old configs still run.

GitHub Models was fully retired on 2026-07-30 (announced 2026-06-16, brownouts on
07-16 and 07-23). `models.github.ai/inference` now returns `410 Gone` for both
chat completions and embeddings, permanently. This pipeline ran on it as the
default CI backend, so distill failed on every run from 2026-07-31 and published
no digest for ten days while collect-corpus stayed green.

Two things changed as a result, and both matter more than the endpoint swap:

  * A permanent backend failure now DEGRADES to the template digest instead of
    killing the run. Ten days of nothing was not caused by the retirement — it
    was caused by an uncaught exception on a code path with no fallback. A dead
    provider should cost quality, not the entire product.

  * The degraded digest says so, in the digest itself. A reader must be able to
    tell a synthesized brief from an assembled list; silently shipping the
    latter under the former's name is the `X2 instrument_honesty` failure the
    rubric exists to catch.

Run: python -m distill.synthesize
"""
from __future__ import annotations
import os, re, sys, json, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import ROOT, parse_window  # noqa: E402
from distill.rank import rank_key  # noqa: E402
from distill.delta import compute_delta, save_state, story_arcs  # noqa: E402
from distill.focus import active_terms as _focus_active_terms, _term_hit, _blob as _focus_blob  # noqa: E402
from distill.cluster import cluster_items  # noqa: E402
from distill.diversity import diversify  # noqa: E402
import llm  # noqa: E402  (leaf: provider config shared with grader/)

WINDOW = os.environ.get("WINDOW", "48h")
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "10"))
MARKET = os.environ.get("MARKET", "off").lower() == "on"
THRESHOLD = int(os.environ.get("INCLUDE_THRESHOLD", "2"))
_REQUESTED_BACKEND = os.environ.get("RADAR_MODEL_BACKEND", "dryrun").lower()

# HTTP codes no amount of retrying or payload-shrinking can fix. 410 is the one that
# bit us (a retired product), but a revoked key (401) or a deleted model (404) fail
# exactly as permanently, and all of them should degrade rather than abort.
PERMANENT_HTTP = frozenset({400, 401, 403, 404, 410})

# Backends that reach a model over the network, and therefore can fail permanently.
_MODEL_BACKENDS = frozenset({"anthropic", "openai", "ollama"})


def resolve_backend(requested: str, env: dict | None = None) -> tuple[str, str | None]:
    """(backend, note). `note` is a human-facing warning, or None when nothing surprising
    happened. Pure so the selection rules are testable without touching the network.

    `github` is accepted rather than rejected. Hard-failing on it would break every
    existing config — distill.yml, the README, anyone's shell — and re-create the
    outage it is meant to end. It redirects, loudly.
    """
    env = os.environ if env is None else env
    if requested == "github":
        chosen, _ = resolve_backend("auto", env)
        return chosen, ("RADAR_MODEL_BACKEND=github is retired (GitHub Models shut down "
                        f"2026-07-30); using '{chosen}'. Set the variable explicitly to silence this.")
    if requested != "auto":
        return requested, None
    # The shared provider comes first: one base URL + one key serves synthesis and the
    # grader alike, and it is the configuration the docs and `python3 -m llm` describe.
    if env.get("RADAR_LLM_BASE_URL") and (env.get("RADAR_LLM_API_KEY")
                                          or env.get("OPENAI_API_KEY")):
        return "openai", None
    # Direct-vendor keys, still supported for anyone who had them before the unification.
    if env.get("ANTHROPIC_API_KEY"):
        return "anthropic", None
    if env.get("OPENAI_API_KEY"):
        return "openai", None
    # Neither key. Still has to publish something: the template digest is a real digest —
    # scored items, observed signals, no invented prose — just not a synthesized one.
    return "template", ("no model provider configured (set RADAR_LLM_BASE_URL + "
                        "RADAR_LLM_API_KEY); falling back to the template backend "
                        "(deterministic, no synthesis)")


BACKEND, _BACKEND_NOTE = resolve_backend(_REQUESTED_BACKEND)
if _BACKEND_NOTE:
    print(f"[distill] {_BACKEND_NOTE}", file=sys.stderr)
SCORED = ROOT / "data" / "scored"
ENRICHED = ROOT / "data" / "enriched"
SPEC = (ROOT / "distill" / "digest.md").read_text()

# Payload caps. These were sized around GitHub Models' ~16k-token INPUT ceiling, which is
# why the per-backend override table existed (github: 24 candidates / 360 summary chars).
# That backend is gone and every remaining one takes a far larger prompt, so the table is
# empty and everything gets the roomy default. The 413 shrink ladder in
# `synthesize_with_fallback` stays regardless — it is the generic defence against a
# provider-specific input limit, and the next backend will have one too.
# Overridable via env for tuning.
_PER_BACKEND_CAND: dict[str, int] = {}
_PER_BACKEND_SUMMARY: dict[str, int] = {}
_CAND_DEFAULT = _PER_BACKEND_CAND.get(BACKEND, 60)
_SUMMARY_DEFAULT = _PER_BACKEND_SUMMARY.get(BACKEND, 600)
MAX_CANDIDATES = int(os.environ.get("MAX_CANDIDATES", _CAND_DEFAULT))
SUMMARY_CHARS = int(os.environ.get("SUMMARY_CHARS", _SUMMARY_DEFAULT))

# Reserve main-list slots for non-research so hardware/releases (which score lower than
# research papers structurally) aren't crowded out. 0/0 reverts to research-only behavior.
HARDWARE_SLOTS = int(os.environ.get("HARDWARE_SLOTS", "2"))
RELEASE_SLOTS = int(os.environ.get("RELEASE_SLOTS", "5"))

# Carryover budget. Items the radar is already tracking (distill/track.py) re-enter the
# candidate pool with freshly observed traction. They get a small reserved slice so the digest
# stays mostly about what's new — but when the fresh window is thin, that slice widens to
# QUIET_FLOOR. A quiet collection day is precisely when a radar should fall back on what it is
# already watching; the alternative, historically, was publishing a digest with zero items.
CARRYOVER_SLOTS = int(os.environ.get("CARRYOVER_SLOTS", "4"))
QUIET_FLOOR = int(os.environ.get("QUIET_FLOOR", "6"))

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
    # Fresh (first seen this window) vs carryover (already on the radar, re-observed today).
    # The category quotas below are about balancing *today's* collection, so they run over
    # fresh items only; carryovers get their own budget afterwards.
    fresh = [i for i in items if not i.get("carryover")]
    carried = [i for i in items if i.get("carryover")]
    keep = [i for i in fresh if (i.get("score") or 0) >= max(2, THRESHOLD - 1)]

    # Category quotas: guarantee non-research a few slots (they score lower than research
    # papers structurally, e.g. a vendor blog has no HF/GitHub trending). Lower floor (>=1)
    # lets them in; the model still sees their real score and routes them correctly.
    research = [i for i in keep if i["category"] == "research"]
    hardware = [i for i in fresh if i["category"] == "hardware" and (i.get("score") or 0) >= 1]
    releases = [i for i in fresh if i["category"] == "releases" and (i.get("score") or 0) >= 1]
    research_slots = max(0, max_candidates - HARDWARE_SLOTS - RELEASE_SLOTS)
    chosen = (research[:research_slots]
              + hardware[:HARDWARE_SLOTS]
              + releases[:RELEASE_SLOTS])
    # Carryover slice, widened when today's collection was quiet (see CARRYOVER_SLOTS).
    slots = (CARRYOVER_SLOTS if len(chosen) >= QUIET_FLOOR
             else max(CARRYOVER_SLOTS, QUIET_FLOOR - len(chosen)))
    carried.sort(key=rank_key, reverse=True)
    chosen += carried[:slots]
    chosen.sort(key=rank_key, reverse=True)   # model sees a single ranked list
    # Diversity pass: collapse near-duplicate titles (e.g. Foo-1.0-9B / -35B / -GGUF)
    # and cap items-per-source so one lab's release sweep can't dominate the digest.
    # Applied AFTER category quotas + ranking so higher-signal exemplars survive.
    chosen = diversify(chosen)

    compact = []
    for i in chosen:
        sig = i.get("signals") or {}
        prov = _build_provenance(i)
        # Secondary artifact links (github / project page) the collectors captured. The spec
        # REQUIRES surfacing these as visible links, so they must reach the model.
        links = {k: v for k, v in (i.get("links") or {}).items() if v}
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
        if links:
            row["links"] = links
        if prov:
            row["provenance"] = prov
        if i.get("carryover"):
            # Tell the model this is a carryover so it can route it to "Still developing"
            # rather than presenting a week-old item as today's news. traction_delta is the
            # magnitude change since we started tracking: positive means still climbing.
            row["carryover"] = True
            row["runs_tracked"] = i.get("streak", 1)
            row["first_seen"] = i.get("first_seen", "")
            row["traction_delta"] = i.get("traction_delta", 0)
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
        "than padding.\n"
        "Items with carryover=true are NOT new: the radar has been tracking them for "
        "`runs_tracked` runs since `first_seen`, and their traction figures were re-observed "
        "just now. Put them under 'Still developing' with their current numbers, unless "
        "traction_delta is strongly positive — a carryover that is still climbing hard has "
        "earned a main-list slot. Never describe a carryover as new.\n\n"
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


def call_openai_compat(system: str, user: str) -> str:
    """The shared provider path — see `llm.py`.

    This used to carry its own base-URL/key/model env vars, mirroring a near-identical
    set in the grader. Providers are no longer divided by responsibility: both stages
    read one `RADAR_LLM_BASE_URL` + `RADAR_LLM_API_KEY` and differ only in which model
    they name, which is the thing the separation fence actually cares about.
    """
    return llm.chat(system, user, llm.model_for(llm.SYNTHESIS))


# `call_github` lived here until 2026-08. GitHub Models was retired on 2026-07-30 and
# https://models.github.ai/inference returns 410 Gone permanently, so the function is
# deleted rather than kept behind a flag: a helper that dials a dead host is a trap for
# the next person wiring up a backend. History has it if the shape is ever wanted again.
# `call_openai_compat` above is its successor: same free-tier role, no vendor baked in.


def call_ollama(system: str, user: str) -> str:
    body = json.dumps({
        "model": os.environ.get("RADAR_OLLAMA_MODEL", "qwen3:4b"),
        "system": system, "prompt": user, "stream": False,
    }).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=body,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read()).get("response", "")


_DECODER = json.JSONDecoder()


def extract_candidates(user: str) -> list | None:
    """Recover the candidate array `build_prompt` appends to the end of the user message.

    The obvious regex — `\\[\\s*\\{.*\\}\\s*\\]` with DOTALL — is wrong, and wrong in a way
    that only shows up on real data. The prompt carries several top-level JSON blocks
    (MOVERS, story arcs, clusters, then candidates), so a greedy match spans from the first
    to the last and yields a string that is not valid JSON. With an empty delta there is
    only one array and it appears to work, which is why it survived: every test fixture had
    a quiet window. In production it made the template backend emit "Could not parse items
    JSON" — harmless while template was a testing mode, load-bearing now that it is the
    fallback a dead provider degrades to.

    So: walk the top-level array starts from the end and take the last one that actually
    decodes. `raw_decode` stops at the end of the value and ignores trailing text, and a
    literal newline never appears inside a JSON string (it is escaped), so `\\n[` at column
    zero reliably marks a top-level array rather than a nested or quoted one.
    """
    for idx in reversed([m.start() + 1 for m in re.finditer(r"\n\[", user)]):
        try:
            value, _ = _DECODER.raw_decode(user, idx)
        except ValueError:
            continue
        if isinstance(value, list):
            return value
    return None


def call_template(system: str, user: str) -> str:
    """No-model backend: generate a structured report from the top scored items directly.
    Runs without an API key, and is what a permanent backend failure degrades to."""
    items = extract_candidates(user)
    if items is None:
        # Loud, because this is the floor. Nothing catches a bad digest below this point.
        print("[distill] template backend could not recover the candidate array from the "
              "prompt; emitting an error digest", file=sys.stderr)
        return ("# AI Radar — Template Error\n\n"
                "Could not recover the candidate items from the assembled prompt. "
                "This is a bug in `distill/synthesize.py:extract_candidates`, not a "
                "collection failure — the corpus is intact and re-running distill after "
                "a fix will produce the digest.\n")

    today = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    lines = [
        f"# AI Radar — {today}",
        "",
        f"**Top-line** — {len(items)} candidate items scored in the last {WINDOW}. "
        "Run with `RADAR_MODEL_BACKEND=anthropic` (or `auto` with ANTHROPIC_API_KEY set) "
        "for model synthesis and insights.",
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
    lines.append("- Set a model backend for synthesis: `export RADAR_MODEL_BACKEND=anthropic` + `export ANTHROPIC_API_KEY=...`")
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


def degraded_banner(backend: str, reason: str) -> str:
    """The notice prepended to a digest that lost its synthesis step.

    Load-bearing, not decorative. A degraded digest is an assembled list of scored
    items, not a written brief, and a reader who cannot tell the two apart has been
    misled about what produced the words in front of them — `X2 instrument_honesty`
    in the rubric. It also names the cause, because the alternative is a reader
    concluding the radar got worse rather than that a provider went away.
    """
    return (
        f"> **Degraded run — no model synthesis.** The `{backend}` backend failed "
        f"permanently ({reason}), so this digest was assembled directly from scored "
        "items and observed signals. Rankings and traction numbers are real; the "
        "connective prose, the top-line read, and the insights are absent rather "
        "than machine-written. See `docs/architecture/adr/0006-model-backend-after-"
        "github-models.md`.\n\n"
    )


def synthesize_with_fallback(items: list[dict], system: str, user: str, n_cand: int) -> str:
    """Call the configured backend; degrade to the template digest on a permanent failure.

    The shrink ladder handles 413 (payload too large) by rebuilding a smaller prompt.
    That was the only error class the old code handled, and every other HTTP error
    re-raised straight out of `main()` — which is why a `410 Gone` took the pipeline
    down for ten days instead of costing one day's prose.
    """
    attempts = [
        dict(),
        dict(_strip_briefs=True),
        dict(_strip_briefs=True, max_candidates=18, summary_chars=240),
        dict(_strip_briefs=True, max_candidates=12, summary_chars=180),
        dict(_strip_briefs=True, max_candidates=max(MAX_ITEMS, 8), summary_chars=120),
    ]
    caller = {"anthropic": call_anthropic, "openai": call_openai_compat,
              "ollama": call_ollama}[BACKEND]

    last_413: urllib.error.HTTPError | None = None
    for n, kw in enumerate(attempts):
        if n:
            print(f"[distill] 413 on synthesis; shrinking payload "
                  f"(attempt {n}/{len(attempts)-1}: {kw})", file=sys.stderr)
            system, user, n_cand = build_prompt(items, **kw)
        _log_prompt_stats(system, user, len(items), n_cand, n)
        try:
            return caller(system, user)
        except urllib.error.HTTPError as ex:
            if ex.code == 413:
                last_413 = ex
                continue
            if ex.code in PERMANENT_HTTP:
                print(f"[distill] {BACKEND} backend failed permanently (HTTP {ex.code} "
                      f"{ex.reason}); degrading to the template digest", file=sys.stderr)
                return degraded_banner(BACKEND, f"HTTP {ex.code} {ex.reason}") + \
                    call_template(system, user)
            raise
        except urllib.error.URLError as ex:
            # DNS failure / refused connection / TLS error. Indistinguishable from a
            # retired host at this layer, and equally not worth losing the digest over.
            print(f"[distill] {BACKEND} backend unreachable ({ex.reason}); "
                  "degrading to the template digest", file=sys.stderr)
            return degraded_banner(BACKEND, str(ex.reason)) + call_template(system, user)

    print("[distill] still 413 after shrinking to the floor; degrading to template",
          file=sys.stderr)
    return degraded_banner(BACKEND, f"HTTP 413 after {len(attempts)} shrink attempts") + \
        call_template(system, user)


def main() -> None:
    items = load_scored()
    system, user, n_cand = build_prompt(items)
    if BACKEND in _MODEL_BACKENDS:
        report = synthesize_with_fallback(items, system, user, n_cand)
    elif BACKEND == "template":
        report = call_template(system, user)
    else:
        _log_prompt_stats(system, user, len(items), n_cand, 0)
        report = ("# DRYRUN — assembled prompt (no model called)\n\n"
                  "Set RADAR_MODEL_BACKEND=auto, anthropic, ollama, or template to generate the digest.\n\n"
                  "## SYSTEM\n" + system + "\n\n## USER\n" + user)
    out = ROOT / "reports" / f"{datetime.now(timezone.utc):%Y-%m-%d}-digest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    # Advance state whenever a real digest was published.
    #
    # This used to exclude `template` alongside `dryrun`, on the reasoning that both were
    # testing modes. That stopped being true when GitHub Models was retired: with no API
    # key, `auto` resolves to `template` and it becomes the steady-state production
    # backend. Leaving it excluded would publish a digest daily while never snapshotting
    # state or promoting to the ledger — so every "what changed" diff would compare against
    # a frozen yesterday and carryover would slowly empty out. A silently degrading radar
    # is worse than a visibly broken one.
    #
    # `dryrun` still never advances: it writes no real digest, only the assembled prompt.
    # `RADAR_NO_STATE=1` keeps the old safety valve for anyone running the pipeline locally
    # against a real checkout who does not want to dirty state.json / tracked.json.
    if BACKEND != "dryrun" and os.environ.get("RADAR_NO_STATE", "") != "1":
        save_state(items)
        # Put today's digest-worthy items on the radar so the next run can re-observe their
        # traction. Promotion happens only after a digest is actually written — a run that
        # failed to publish shouldn't leave the ledger claiming it saw these items.
        try:
            from distill.track import load_ledger, promote, save_ledger
            before = load_ledger()
            after = promote(items, before)
            save_ledger(after)
            if len(after) != len(before):
                print(f"[distill] tracking +{len(after) - len(before)} new items "
                      f"({len(after)} on the radar)")
        except Exception as ex:
            print(f"[distill] promotion skipped: {ex}", file=sys.stderr)
    n_carry = sum(1 for i in items if i.get("carryover"))
    print(f"[distill] wrote {out}  (backend={BACKEND}, {len(items)} scored items, "
          f"{n_carry} carryover)")


if __name__ == "__main__":
    main()
