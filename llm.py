"""One provider, one key, one endpoint — shared by every stage that calls a model.

The pipeline used to divide providers by responsibility: `distill` had its own backend
env vars, `grader` had a parallel set, and running both meant two accounts, two keys,
two base URLs, and two ways for the config to be wrong. Separation of *concerns* had
leaked into separation of *vendors*, which is not the same thing and buys nothing.

What the grader actually requires is that its model and the digest's model come from
different **families** — a model grading its own family self-enhances by roughly
+10-25% (`docs/operating/grader.md`). Family is a property of the model, not of the
account it was billed to. So one gateway that serves many families satisfies the fence
exactly as well as two direct accounts, with half the configuration:

    RADAR_LLM_BASE_URL=https://openrouter.ai/api/v1
    RADAR_LLM_API_KEY=sk-or-...

That is the whole setup. Roles pick *models* through the one endpoint, not providers.

You do not have to know which models. `model_for()` falls back to a per-provider
default pair chosen from two different families, so a key and a URL is a working,
separated configuration. Override either role when you want to; `python3 -m llm
--catalog` prints what the provider actually serves, with families detected, so the
choice is one command rather than guesswork.

A caveat worth stating plainly: a single-family provider cannot satisfy the fence on
its own. Perplexity serves only `sonar`, Groq and Cerebras are Llama-dominated. Those
are fine for synthesis; the grader then needs a second family from somewhere. A gateway
(OpenRouter and similar) is what makes the one-provider setup actually work end to end.

Stdlib only, and imports nothing from `distill` or `grader`. This is a leaf: both
depend on it, it depends on neither, so it cannot become the coupling between the
pipeline and its critic that ADR-0003 exists to prevent.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT = int(os.environ.get("RADAR_LLM_TIMEOUT", "180"))

# Roles, not providers. Add a role here and it inherits config, families and defaults.
SYNTHESIS = "synthesis"
GRADER = "grader"
ROLES = (SYNTHESIS, GRADER)


# ---------------------------------------------------------------------------
# Model families
# ---------------------------------------------------------------------------
# Substring -> family. Shared by every consumer so "same family" means one thing
# repo-wide; `grader/separation.py` enforces the rule, this table defines the terms.
# Deliberately conservative: an unrecognised id has NO family, and the fence refuses
# rather than assumes. A gate that opens when it is confused is not a gate.
_FAMILY_HINTS = {
    "claude": "anthropic", "anthropic": "anthropic",
    "gpt-": "openai", "o1-": "openai", "o3-": "openai", "openai": "openai",
    "gemini": "google", "gemma": "google", "google": "google",
    "llama": "meta", "meta-llama": "meta",
    "qwen": "alibaba", "alibaba": "alibaba",
    "mistral": "mistral", "mixtral": "mistral", "magistral": "mistral",
    "deepseek": "deepseek",
    "grok": "xai", "x-ai": "xai",
    "sonar": "perplexity", "perplexity": "perplexity",
    "command": "cohere", "cohere": "cohere",
    "nova": "amazon",
    "phi-": "microsoft",
}


def family(model_id: str) -> str | None:
    """Best-effort family for a model id, or None when unrecognised.

    Handles the `vendor/model` form gateways use (`anthropic/claude-sonnet-5`) as well
    as bare ids. Callers must treat None as a failure, never as a pass.
    """
    if not model_id:
        return None
    lowered = model_id.lower()
    if "/" in lowered:
        prefix = lowered.split("/", 1)[0]
        if prefix in set(_FAMILY_HINTS.values()):
            return prefix
        hinted = _FAMILY_HINTS.get(prefix)
        if hinted:
            return hinted
    for hint in sorted(_FAMILY_HINTS, key=len, reverse=True):
        if hint in lowered:
            return _FAMILY_HINTS[hint]
    return None


# ---------------------------------------------------------------------------
# Provider config
# ---------------------------------------------------------------------------
# Default role pairs per provider, keyed by a substring of the base URL. Each pair is
# two DIFFERENT families, so a bare key+URL is separated without the operator choosing
# anything. These are starting points, not promises — provider catalogues change under
# you, so `--catalog` is the source of truth and a wrong id fails loudly naming it.
_PROFILES = {
    # OpenRouter deliberately ships NO default ids. Its free tier is the reason to pick
    # it, and free variants carry a `:free` suffix while the bare id is the metered one
    # — so a plausible-looking default is a 402 that degrades to the template digest and
    # reads exactly like the pipeline still being broken. Rather than hardcode ids that
    # cannot be verified without calling the API, `--resolve` reads the live catalogue
    # and prints the two lines to set. One command beats a guess that fails tomorrow.
    "openrouter.ai": {SYNTHESIS: "", GRADER: ""},
    "api.groq.com": {
        SYNTHESIS: "llama-3.3-70b-versatile",
        GRADER: "",   # Llama-dominated: no second family here. Point the grader elsewhere.
    },
    "generativelanguage.googleapis.com": {
        SYNTHESIS: "gemini-2.5-pro",
        GRADER: "",
    },
    "api.perplexity.ai": {
        SYNTHESIS: "sonar-pro",
        GRADER: "",   # `sonar` only — cannot grade itself.
    },
}


def base_url(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    return env.get("RADAR_LLM_BASE_URL", "").rstrip("/")


def api_key(env: dict | None = None) -> str:
    """The one key. Falls back to the older per-vendor variable so configurations
    written before the providers were unified keep working."""
    env = os.environ if env is None else env
    return env.get("RADAR_LLM_API_KEY") or env.get("OPENAI_API_KEY") or ""


def _profile(env: dict | None = None) -> dict:
    # Every reader threads `env` through rather than closing over os.environ, so a
    # caller can resolve a hypothetical configuration — which is exactly what the
    # separation fence does when it asks "what would synthesis have used here?".
    url = base_url(env)
    for marker, models in _PROFILES.items():
        if marker in url:
            return models
    return {}


def model_for(role: str, env: dict | None = None) -> str:
    """The model id for a role: explicit override first, then the provider's default
    pair, then empty. Empty is a real answer — it means this provider cannot serve the
    role and the caller must say so rather than guess an id."""
    env = os.environ if env is None else env
    explicit = env.get(f"RADAR_{role.upper()}_MODEL", "")
    if explicit:
        return explicit
    return _profile(env).get(role, "")


def configured(env: dict | None = None) -> bool:
    return bool(base_url(env) and api_key(env))


def describe(env: dict | None = None) -> str:
    """One line for logs — never includes the key."""
    if not configured(env):
        return "no RADAR_LLM_BASE_URL / RADAR_LLM_API_KEY configured"
    roles = ", ".join(f"{r}={model_for(r, env) or '(unset)'}" for r in ROLES)
    return f"{base_url(env)} · {roles}"


# ---------------------------------------------------------------------------
# The call
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """Config or transport failure. HTTP errors from the provider are re-raised as
    `urllib.error.HTTPError` so callers can branch on the status code — the
    permanent-vs-transient distinction in `distill/synthesize.py` depends on it."""


def chat(system: str, user: str, model: str, *, max_tokens: int = 4000) -> str:
    """One OpenAI-compatible chat completion.

    Every provider worth using speaks this shape, which is exactly why the pipeline
    can have one caller instead of one per vendor. Anthropic's native Messages API is
    the exception, and it is reachable through any gateway as `anthropic/claude-*` —
    so the native client stays available in `distill` for direct-key users, but it is
    no longer the thing a second stage has to duplicate.
    """
    if not model:
        raise LLMError(
            f"no model configured for this role. Set RADAR_<ROLE>_MODEL, or point "
            f"RADAR_LLM_BASE_URL at a provider that serves more than one model family "
            f"(`python3 -m llm --catalog` lists what {base_url() or 'the provider'} offers).")
    if not configured():
        raise LLMError("RADAR_LLM_BASE_URL and RADAR_LLM_API_KEY must both be set")

    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(
        f"{base_url()}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {api_key()}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError:
        raise                      # status code is meaningful — let the caller classify
    except (urllib.error.URLError, OSError) as ex:
        raise LLMError(f"{base_url()} unreachable: {ex}") from ex
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as ex:
        raise LLMError(f"unexpected response shape from {base_url()}: {str(data)[:200]}") from ex


def is_free(model: dict) -> bool:
    """True when the provider prices both directions at zero.

    OpenAI-compatible catalogues are not uniform here — OpenRouter reports
    `pricing: {prompt, completion}` as decimal strings, others omit pricing entirely.
    Absent pricing is treated as NOT free: assuming free because a field is missing is
    how a "free tier" setup quietly starts billing.
    """
    pricing = model.get("pricing") or {}
    if not pricing:
        return False
    try:
        return all(float(pricing.get(k, 1)) == 0.0 for k in ("prompt", "completion"))
    except (TypeError, ValueError):
        return False


def resolve_pair(free_only: bool = True) -> dict:
    """Pick a model for each role from the live catalogue, from two DIFFERENT families.

    This is the answer to "which models?" that does not involve anybody guessing — not
    the operator, and not whoever wrote this file. Provider catalogues change under you;
    the catalogue is the only thing that knows what is currently served and at what price.

    Deterministic: candidates are sorted by (-context_length, id), so the same catalogue
    always yields the same pair and a pinned config stays reproducible.
    """
    models = [m for m in catalog() if not free_only or is_free(m)]
    ranked = sorted(models, key=lambda m: (-(m.get("context_length") or 0), m.get("id", "")))

    chosen: dict[str, str] = {}
    used_families: set[str] = set()
    for role in ROLES:
        for m in ranked:
            mid = m.get("id", "")
            fam = family(mid)
            if fam and fam not in used_families:
                chosen[role] = mid
                used_families.add(fam)
                break
    return chosen


def catalog() -> list[dict]:
    """`GET {base}/models`, the OpenAI-compatible discovery endpoint. Used by
    `--catalog` so choosing a model is a command rather than a guess."""
    if not configured():
        raise LLMError("RADAR_LLM_BASE_URL and RADAR_LLM_API_KEY must both be set")
    req = urllib.request.Request(
        f"{base_url()}/models",
        headers={"Authorization": f"Bearer {api_key()}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("data", [])
    except (urllib.error.URLError, OSError, ValueError) as ex:
        raise LLMError(f"could not read {base_url()}/models: {ex}") from ex


def _main() -> None:
    if "--resolve" in sys.argv:
        free_only = "--any" not in sys.argv
        try:
            pair = resolve_pair(free_only=free_only)
        except LLMError as ex:
            print(f"[llm] {ex}", file=sys.stderr)
            raise SystemExit(1)
        if len(pair) < len(ROLES):
            print(f"[llm] could not find {len(ROLES)} models from different families"
                  f"{' among free ones' if free_only else ''} on {base_url()}.\n"
                  "       Retry with --any, or use a provider with a broader catalogue —\n"
                  "       the grader's separation fence needs two families.", file=sys.stderr)
            raise SystemExit(1)
        print(f"# resolved from {base_url()}"
              f"{' (free models only)' if free_only else ''}\n")
        for role, mid in pair.items():
            print(f"RADAR_{role.upper()}_MODEL={mid}    # family: {family(mid)}")
        print("\n# Set these as repository variables; they pin the choice so a catalogue\n"
              "# change cannot silently move you to a different model mid-week.")
        return

    if "--catalog" in sys.argv:
        try:
            models = catalog()
        except LLMError as ex:
            print(f"[llm] {ex}", file=sys.stderr)
            raise SystemExit(1)
        rows = sorted((family(m.get("id", "")) or "?", m.get("id", ""), is_free(m))
                      for m in models)
        n_free = sum(1 for *_, free in rows if free)
        print(f"{len(rows)} models on {base_url()} ({n_free} free)\n")
        for fam, mid, free in rows:
            print(f"  {'free' if free else '    '} {fam:<12} {mid}")
        fams = sorted({f for f, _ in rows if f != "?"})
        print(f"\nfamilies served: {', '.join(fams) or 'none recognised'}")
        if len(fams) < 2:
            print("\nWARNING: fewer than two recognised families. The grader's "
                  "separation fence needs two — see docs/operating/grader.md.")
        return
    print(f"[llm] {describe()}")


if __name__ == "__main__":
    _main()
