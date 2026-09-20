"""The one model call: eight judgement dimensions, scored in a single pass.

Two of the ten dimensions never reach the model. `X3 freshness` is arithmetic on the
digest's age (`grader/freshness.py`), and the `A2` ceiling is an observed HTTP status
(`grader/links.py`). A judge cannot observe a 404 and, asked to, will invent one — so
anything checkable is checked before the model is involved, and the model is asked only
for the things that genuinely need reading.

`grader.md#score-in-one-pass` requires all dimensions emitted together rather than
incrementally: the incremental pattern hit output-length limits mid-emit and produced
truncated evals that failed schema validation. A single JSON object enforces that shape.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import llm
from grader.separation import SeparationViolation, assert_separated

ROOT = Path(__file__).resolve().parent.parent

# The eight the model actually judges. A2 is included — the model still assesses whether
# claims cite primary sources — but its score is capped afterwards by the observed link
# statuses, so a generous read cannot score around a dead link.
JUDGED_DIMS = ("A1", "A2", "A3", "A4", "A5", "X1", "X2", "X4", "X5")

_INSTRUCTIONS = """\
You are grading one issue of a daily AI newsletter against a fixed rubric. You are not
writing the newsletter and you are not improving it. Score what is in front of you.

Return ONE JSON object and nothing else. No prose before or after, no markdown fence.

Shape, exactly:

{"A1": {"score": 0-5, "why": "..."}, ... , "X5": {"score": 0-5, "why": "..."},
 "missed_stories": [{"title": "...", "url": "...", "why": "..."}]}

Rules that are not negotiable:

- Keys are exactly A1 A2 A3 A4 A5 X1 X2 X4 X5. Never the long form (A1_signal_density).
  X3 is computed from the digest's age and is not yours to score.
- `score` is an integer 0-5. No half scores.
- `why` is at most 15 words and MUST cite concrete evidence: an item title, a URL, or a
  line in the digest. A vague justification ("good coverage") is a grader bug, not a score.
- Score every dimension in this one response. Do not plan to continue in a second step.
- `missed_stories` lists genuinely important last-24h stories the digest omitted, with a
  <=30 word argument for inclusion each. Empty array if none. Do not pad it: A5 is scored
  from its length, so an invented miss directly falsifies the score.

Be a critic. The rubric's 5 is "every line earns its space", not "nothing was wrong".
A digest that is merely competent is a 3.
"""


class JudgeError(Exception):
    """The model call or its output could not be turned into scores."""


def build_prompt(digest: str, rubric: str, age_h: float,
                 broken: list[dict], prev_digest: str | None) -> tuple[str, str]:
    """(system, user). The rubric text is passed verbatim rather than summarised so the
    anchors the model scores against are the same ones committed in `evals/rubric.md`."""
    system = _INSTRUCTIONS + "\n\nRUBRIC (authoritative anchors):\n\n" + rubric

    parts = [f"DIGEST AGE AT EVAL: {age_h}h\n"]
    if broken:
        parts.append(
            "OBSERVED BROKEN LINKS (HEAD/GET checked just now — status 0 means the runner "
            f"could not reach it, which is not the digest's fault):\n{json.dumps(broken, indent=2)}\n"
            "A2 is capped at 2 by any genuinely broken link; score A2 on source quality "
            "and the cap will be applied for you.\n")
    else:
        parts.append("OBSERVED BROKEN LINKS: none. Every markdown link answered 2xx.\n")

    if prev_digest:
        parts.append("\nPREVIOUS DIGEST (for A4 delta_clarity — is 'What changed' a real "
                     "diff against this, or a restatement?):\n\n" + prev_digest[:12000] + "\n")
    else:
        parts.append("\nNo previous digest available. Score A4 on the internal consistency "
                     "of today's own new/climbing/cooled classifications.\n")

    parts.append("\nTODAY'S DIGEST:\n\n" + digest)
    return system, "".join(parts)


# --- the model call -------------------------------------------------------
# One provider, shared with synthesis (see llm.py). The grader used to carry its own
# backend enum, its own base URL, and its own copies of the anthropic/openai/ollama
# callers — three functions that differed from distill's only in which module they
# lived in. What the grader actually needs to differ is the model FAMILY, which
# `separation.py` enforces; the transport was never the thing keeping it independent.


def resolve_model() -> str:
    return llm.model_for(llm.GRADER)


# --- parsing ---------------------------------------------------------------

def parse_verdict(raw: str) -> dict:
    """Pull the JSON object out of a model response.

    Models wrap JSON in prose or a fence no matter how firmly asked not to, so this
    tolerates both rather than failing the run over formatting. It does NOT tolerate
    missing dimensions: a truncated verdict is the documented failure mode of scoring
    incrementally, and silently defaulting the absent dims would write a fabricated score
    into the permanent trend.
    """
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    decoder = json.JSONDecoder()
    for idx in (m.start() for m in re.finditer(r"\{", text)):
        try:
            value, _ = decoder.raw_decode(text, idx)
        except ValueError:
            continue
        if isinstance(value, dict) and any(d in value for d in JUDGED_DIMS):
            return _validate_verdict(value)
    raise JudgeError(f"no JSON verdict found in model output (first 300 chars): {raw[:300]!r}")


def _validate_verdict(v: dict) -> dict:
    missing = [d for d in JUDGED_DIMS if d not in v]
    if missing:
        raise JudgeError(
            f"verdict is missing {', '.join(missing)}. This is the truncated-emit failure "
            "grader.md#score-in-one-pass warns about; the run must escalate rather than "
            "default the absent dimensions.")
    out: dict = {}
    for dim in JUDGED_DIMS:
        entry = v[dim]
        if not isinstance(entry, dict) or "score" not in entry:
            raise JudgeError(f"{dim} is not a {{score, why}} object: {entry!r}")
        try:
            score = int(entry["score"])
        except (TypeError, ValueError):
            raise JudgeError(f"{dim} score is not an integer: {entry.get('score')!r}")
        if not 0 <= score <= 5:
            raise JudgeError(f"{dim} score {score} is outside 0-5")
        why = str(entry.get("why", "")).strip()
        if not why:
            raise JudgeError(f"{dim} has no justification; an unjustified score is a bug")
        out[dim] = {"score": score, "why": why}

    misses = v.get("missed_stories") or []
    out["missed_stories"] = [
        {"title": str(m.get("title", "")), "url": str(m.get("url", "")),
         "why": str(m.get("why", ""))}
        for m in misses if isinstance(m, dict)
    ]
    return out


def candidate_models(env: dict | None = None) -> list[str]:
    """Models to try, best first.

    A pinned id is a decision, so it is the only candidate — silently grading on something
    else because the chosen model was busy would make `grader_model` a record of what
    happened to be available rather than of what was configured.

    Unpinned, the list comes from the live catalogue. On a free tier that plurality is the
    difference between usable and nominal: PR #35 recorded gemma, gpt-oss and cohere all
    upstream-429 simultaneously, and a single resolved id would have cost the day's judged
    eval to a rate limit that a different family would have sailed through.
    """
    if pinned := llm.pinned_model(llm.GRADER, env):
        return [pinned]
    return llm.auto_candidates(llm.GRADER, env)


def judge(digest: str, rubric: str, age_h: float, broken: list[dict],
          prev_digest: str | None = None, env: dict | None = None) -> tuple[dict, str]:
    """(verdict, model_id). Enforces model separation before spending a token on the call.

    Tries each candidate in turn, moving on only for reasons a *different model* could
    survive: a separation refusal, or one of `llm.RETRYABLE_STATUS`. A malformed verdict
    is not retried — that is the truncated-emit failure `grader.md#score-in-one-pass`
    warns about, and quietly asking a second model would turn a bug into a coin flip.
    """
    candidates = candidate_models(env)
    model = candidates[0] if candidates else ""
    if not model:
        # Reached only after auto-resolution has also come up empty (llm.auto_model), so
        # the remedy is never "pin something" alone — the catalogue was unreachable, or it
        # genuinely serves no free model outside synthesis's family.
        raise JudgeError(
            f"no grader model available on {llm.base_url() or '(no provider configured)'}. "
            "Resolution from the live catalogue found nothing usable: the grader needs a "
            "model of a DIFFERENT FAMILY from synthesis, not a different provider. Check "
            "`python3 -m llm --catalog`; pin RADAR_GRADER_MODEL to override, or set "
            "RADAR_ALLOW_METERED=1 if only paid models remain.")
    system, user = build_prompt(digest, rubric, age_h, broken, prev_digest)
    only_candidate = len(candidates) == 1
    refusals: list[str] = []

    for attempt, model in enumerate(candidates):
        try:
            assert_separated(model, env)          # raises SeparationViolation
        except SeparationViolation:
            if only_candidate:
                # A pinned model that collides is a configuration error and must be loud.
                # I-08: the fence is never worked around, only reported.
                raise
            # An auto-resolved candidate should already differ from synthesis; if the
            # fence disagrees it wins, and the next family is tried.
            refusals.append(f"{model}: separation refused")
            continue

        try:
            raw = llm.chat(system, user, model)
        except urllib.error.HTTPError as ex:
            if ex.code in llm.RETRYABLE_STATUS and attempt < len(candidates) - 1:
                print(f"[grader] {model} unavailable ({ex.code}); trying the next family",
                      file=sys.stderr)
                refusals.append(f"{model}: HTTP {ex.code}")
                continue
            raise JudgeError(f"grader model call failed on {model}: HTTP {ex.code}") from ex
        except llm.LLMError as ex:
            raise JudgeError(str(ex)) from ex
        except (urllib.error.URLError, OSError) as ex:
            raise JudgeError(f"grader model call failed: {ex}") from ex

        return parse_verdict(raw), model

    raise JudgeError(
        f"every candidate grader model was unusable ({'; '.join(refusals)}). On a free "
        "tier this is normally upstream rate limiting and clears on its own; the run "
        "degrades to a tier-0 eval meanwhile.")
