"""The model-separation fence.

`docs/operating/grader.md` states the rule in bold: the grader MUST NOT run on the same
model family as the digest's synthesis model. A model evaluating output from its own
family self-enhances by roughly +10-25%, and the resulting failure is invisible by
construction — `evals/latest.json` reads green for months while the digest is flat or
falling, because the instrument and the subject agree.

Until 2026-08 that rule lived only in prose, inside a contract an LLM was asked to
honour. The repo has already learned once what that is worth: `scripts/check_whitelist.py`
exists because `whitelist.md` claimed to be "enforced in code" and was not — the
assertion was a prose code block an agent was trusted to perform. An instruction inside
the agent's reasoning loop is not a control. This module is the control.

**Family, not vendor.** The rule is about shared training lineage, so an Azure-hosted
GPT is still `openai` and a gateway-served Claude is still `anthropic`. That is why the
pipeline can run both roles through one provider (see `llm.py`): what has to differ is
the model, and the account it bills to is irrelevant. An earlier version of this file
re-derived the synthesis model by mirroring `distill`'s backend resolution, which was
duplication that needed a drift test to stay honest; both roles now read the same
`llm.model_for()`, so there is nothing left to drift.

Deliberately conservative: an UNRECOGNISED model id fails the check rather than passing
it. A fence that opens when it does not recognise something is not a fence, and a new
model appearing is exactly when a stale table would wave a violation through.
"""

from __future__ import annotations

import os

import llm
from llm import family  # re-exported: one definition of "family" repo-wide


class SeparationViolation(Exception):
    """Raised when the grader would grade its own family's output."""


def synthesis_model(env: dict | None = None) -> str | None:
    """The model id the digest was synthesized with, or None when the pipeline makes no
    model call at all (`template` / `dryrun` backends).

    Nothing to be separate from in that case: an assembled digest has no authorial voice
    for a judge to flatter.
    """
    env = os.environ if env is None else env

    # A model-free backend means no synthesis voice exists.
    backend = (env.get("RADAR_MODEL_BACKEND") or "").lower()
    if backend in ("template", "dryrun"):
        return None

    shared = llm.model_for(llm.SYNTHESIS, env)
    if shared:
        return shared

    # Direct-key paths that predate the unified provider, still supported.
    if env.get("ANTHROPIC_API_KEY"):
        return env.get("RADAR_ANTHROPIC_MODEL", "claude-opus-4-8")
    if backend == "ollama":
        return env.get("RADAR_OLLAMA_MODEL", "qwen3:4b")
    return None


def assert_separated(grader_model: str, env: dict | None = None) -> str:
    """Raise unless the grader's family differs from the synthesis family. Returns the
    grader's family on success so the caller can record it in the eval artifact."""
    g_family = family(grader_model)
    if g_family is None:
        raise SeparationViolation(
            f"unrecognised grader model {grader_model!r}: cannot prove it differs in "
            "family from the synthesis model. Add it to llm.py:_FAMILY_HINTS — an "
            "unknown model is refused rather than assumed safe.")

    synth = synthesis_model(env)
    if synth is None:
        return g_family                  # no synthesis call; nothing to share a family with

    s_family = family(synth)
    if s_family is None:
        raise SeparationViolation(
            f"unrecognised synthesis model {synth!r}: cannot prove the grader differs "
            "from it. Add it to llm.py:_FAMILY_HINTS.")

    if g_family == s_family:
        raise SeparationViolation(
            f"grader model {grader_model!r} and synthesis model {synth!r} are both "
            f"'{s_family}'. A model grading its own family self-enhances by roughly "
            "+10-25%, and the resulting green scores are indistinguishable from real "
            "quality. Point RADAR_GRADER_MODEL at a different family — one provider is "
            "fine, the model is what has to differ. `python3 -m llm --catalog` lists "
            "the families your provider serves.")

    return g_family
