"""The model-separation fence.

`docs/operating/grader.md` states the rule in bold: the grader MUST NOT run on the same
model family as `distill/synthesize.py`. A model evaluating its own family's output shows
self-enhancement bias of roughly +10-25%, and the resulting failure is invisible by
construction — `evals/latest.json` reads green for months while the digest is flat or
falling, because the instrument and the subject agree.

Until now that rule lived only in prose, inside a contract an LLM was asked to honour. The
repo has already learned once what that is worth: `scripts/check_whitelist.py` exists
because `whitelist.md` claimed to be "enforced in code (each agent asserts before every git
operation)" and was not — the assertion was a prose code block an agent was trusted to
perform. An instruction inside the agent's reasoning loop is not a control. This module is
the control for model separation.

It is deliberately conservative: an UNRECOGNISED model id fails the check rather than
passing it. A fence that opens when it does not recognise something is not a fence, and a
new provider appearing is exactly when a stale allowlist would wave through a violation.

Stdlib only, and it does NOT import `distill`. Importing the graded pipeline into its
grader would couple the two at exactly the seam ADR-0003 exists to keep apart — and
`distill.synthesize` pulls in pyyaml transitively, which would make the grader unable to
run whenever the pipeline's dependencies are the thing that is broken.
"""

from __future__ import annotations

import os

# Substring -> family. Ordered longest-first at match time so `gpt-4` cannot shadow a more
# specific id. Families, not vendors: what matters is shared training lineage, so an
# Azure-hosted GPT is still `openai`.
_FAMILY_HINTS = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gpt-": "openai",
    "o1-": "openai",
    "o3-": "openai",
    "openai": "openai",
    "gemini": "google",
    "gemma": "google",
    "llama": "meta",
    "qwen": "alibaba",
    "mistral": "mistral",
    "mixtral": "mistral",
    "deepseek": "deepseek",
    "grok": "xai",
    "sonar": "perplexity",
    "perplexity": "perplexity",
}


class SeparationViolation(Exception):
    """Raised when the grader would grade its own family's output."""


def family(model_id: str) -> str | None:
    """Best-effort family for a model id. None when unrecognised — callers must treat that
    as a failure, not a pass."""
    if not model_id:
        return None
    lowered = model_id.lower()
    # An explicit `provider/model` prefix wins over substring guessing.
    if "/" in lowered:
        prefix = lowered.split("/", 1)[0]
        if prefix in set(_FAMILY_HINTS.values()):
            return prefix
    for hint in sorted(_FAMILY_HINTS, key=len, reverse=True):
        if hint in lowered:
            return _FAMILY_HINTS[hint]
    return None


def synthesis_model(env: dict | None = None) -> str | None:
    """The model id `distill/synthesize.py` would use, derived from the same environment.

    Mirrors that module's `resolve_backend` rather than importing it — see the note at the
    top of this file. `tests/test_grader.py` asserts the two agree across the backend
    matrix, so the mirror cannot drift silently.

    Returns None when the pipeline would make no model call at all (`template`, `dryrun`).
    Nothing to be separate from in that case: an assembled digest has no authorial voice
    for a judge to flatter.
    """
    env = os.environ if env is None else env
    requested = (env.get("RADAR_MODEL_BACKEND") or "dryrun").lower()

    if requested in ("auto", "github"):     # `github` is retired and redirects to auto
        requested = "anthropic" if env.get("ANTHROPIC_API_KEY") else "template"

    if requested == "anthropic":
        return env.get("RADAR_ANTHROPIC_MODEL", "claude-opus-4-8")
    if requested == "ollama":
        return env.get("RADAR_OLLAMA_MODEL", "qwen3:4b")
    return None                              # template / dryrun / unknown -> no model


def assert_separated(grader_model: str, env: dict | None = None) -> str:
    """Raise unless the grader's family differs from the synthesis family. Returns the
    grader's family on success so the caller can record it in the eval artifact."""
    g_family = family(grader_model)
    if g_family is None:
        raise SeparationViolation(
            f"unrecognised grader model {grader_model!r}: cannot prove it differs in family "
            "from the synthesis model. Add it to grader/separation.py:_FAMILY_HINTS — an "
            "unknown model is refused rather than assumed safe.")

    synth = synthesis_model(env)
    if synth is None:
        return g_family                      # pipeline makes no model call; nothing to share

    s_family = family(synth)
    if s_family is None:
        raise SeparationViolation(
            f"unrecognised synthesis model {synth!r}: cannot prove the grader differs from "
            "it. Add it to grader/separation.py:_FAMILY_HINTS.")

    if g_family == s_family:
        raise SeparationViolation(
            f"grader model {grader_model!r} and synthesis model {synth!r} are both "
            f"'{s_family}'. A model grading its own family self-enhances by roughly "
            "+10-25%, and the resulting green scores are indistinguishable from real "
            "quality. Pin RADAR_GRADER_MODEL to a different family — see "
            "docs/operating/grader.md#model-separation-required.")

    return g_family
