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

# The output ceiling. 4000 was sized for a model that answers directly, and the pipeline
# now runs on whatever the catalogue offers — which is increasingly a reasoning model that
# spends thousands of tokens thinking first. At 4000, three digests in six weeks were
# nothing but truncated planning notes. 16000 leaves room to think and still answer; the
# provider caps it lower if the model cannot go that high, and `Truncated` says so either
# way rather than letting a cut-off response pass as an answer.
MAX_TOKENS = int(os.environ.get("RADAR_LLM_MAX_TOKENS", "16000"))

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
    "nemotron": "nvidia", "nvidia": "nvidia",
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


# OpenRouter mints keys with a fixed prefix, so a key is enough to identify the provider.
# Inferring the URL from it means the free tier costs the operator exactly one variable
# instead of two, and two-variable setups are how you end up with a key pointed at the
# wrong endpoint. Only this one provider is inferred: it is the only one whose key format
# is both documented and distinctive.
_KEY_PREFIXES = {"sk-or-": "https://openrouter.ai/api/v1"}


def base_url(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    explicit = env.get("RADAR_LLM_BASE_URL", "").rstrip("/")
    if explicit:
        return explicit
    key = api_key(env)
    for prefix, url in _KEY_PREFIXES.items():
        if key.startswith(prefix):
            return url
    return ""


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


def pinned_model(role: str, env: dict | None = None) -> str:
    """The model id a human or a profile chose for `role`, with no catalogue lookup.

    Kept separate from `model_for` for one structural reason: auto-resolution has to know
    which family the *other* role occupies, and if it asked `model_for` it could trigger
    the other role's auto-resolution, which would ask back. This is the recursion-free
    answer, and it is the only thing auto-resolution is allowed to consult.
    """
    env = os.environ if env is None else env
    explicit = env.get(f"RADAR_{role.upper()}_MODEL", "")
    if explicit:
        return explicit
    return _profile(env).get(role, "")


# Cached per process. `model_for` is called by the separation fence for both sides of
# every check, and an uncached network call in that path would turn a fence into a
# latency budget. Keyed by (role, base_url) so a test switching providers is not served
# a stale answer.
_AUTO_CACHE: dict[tuple, str] = {}


# How many usable models to return. On a free tier the first pick is often throttled —
# PR #35 recorded gemma, gpt-oss and cohere all upstream-429 at once — so resolving to a
# single id means one provider-side rate limit costs the day's judged eval. Candidates are
# what make a free tier actually usable rather than nominally available.
AUTO_CANDIDATES = 4

# HTTP statuses where a DIFFERENT model may still work. 429 is the free tier's normal
# weather; 402 means the model was not actually free despite its pricing; 5xx is the
# provider's upstream. Everything else (400, 401, 403, 404) is a configuration fault that
# the next model would hit identically, so failing over would just be four ways to lose.
RETRYABLE_STATUS = {402, 408, 429, 500, 502, 503, 504}


def auto_candidates(role: str, env: dict | None = None, timeout: int = 15,
                    limit: int = AUTO_CANDIDATES) -> list[str]:
    """Usable models for `role`, best first, at most one per family.

    One per family is not an arbitrary cap: the point of the list is surviving a throttle,
    and a provider rate-limiting `vendor/model-a:free` is likely to be rate-limiting
    `vendor/model-b:free` too. Different families are also different upstreams.
    """
    env = os.environ if env is None else env
    if env.get("RADAR_AUTO_MODEL", "1") == "0" or not configured(env):
        return []

    avoid = {family(pinned_model(other, env)) for other in ROLES if other != role}
    avoid.discard(None)

    try:
        models = catalog(env, timeout=timeout)
    except LLMError as ex:
        print(f"[llm] auto-resolution for {role} unavailable: {ex}", file=sys.stderr)
        return []

    allow_metered = env.get("RADAR_ALLOW_METERED", "0") == "1"
    ranked = sorted((m for m in models if allow_metered or is_free(m)),
                    key=lambda m: (-(m.get("context_length") or 0), m.get("id", "")))

    out: list[str] = []
    seen: set[str] = set()
    for m in ranked:
        mid = m.get("id", "")
        fam = family(mid)
        # An unrecognised family is skipped, not chosen. The fence would refuse it anyway
        # (ADR-0007), and picking one would produce a confusing refusal about a model
        # nobody selected.
        if not fam or fam in avoid or fam in seen:
            continue
        out.append(mid)
        seen.add(fam)
        if len(out) >= limit:
            break
    return out


def auto_model(role: str, env: dict | None = None, timeout: int = 15) -> str:
    """The single best model for `role`, or "".

    A thin front on `auto_candidates` so there is exactly one resolution rule rather than
    two that can disagree. Callers that can retry should use the list; `model_for` cannot,
    so it takes the head.
    """
    env = os.environ if env is None else env
    key = (role, base_url(env))
    if key in _AUTO_CACHE:
        return _AUTO_CACHE[key]

    candidates = auto_candidates(role, env, timeout=timeout)
    chosen = candidates[0] if candidates else ""
    if chosen:
        print(f"[llm] auto-resolved {role}={chosen} (family: {family(chosen)}"
              f"{f'; {len(candidates) - 1} fallback(s)' if len(candidates) > 1 else ''})",
              file=sys.stderr)
    elif configured(env) and env.get("RADAR_AUTO_MODEL", "1") != "0":
        print(f"[llm] no usable {role} model on {base_url(env)} — the fence needs a family "
              "different from synthesis", file=sys.stderr)
    _AUTO_CACHE[key] = chosen
    return chosen


def model_for(role: str, env: dict | None = None) -> str:
    """The model id for a role: explicit override, then the provider's default pair, then
    the live catalogue, then empty.

    The catalogue step only ever runs when the answer would otherwise be "" — that is, when
    the alternative is not a worse model but *no model and no eval*. So it cannot change a
    configuration that already works, and it cannot silently move a pinned one.
    """
    env = os.environ if env is None else env
    return pinned_model(role, env) or auto_model(role, env)


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


class Truncated(LLMError):
    """The model hit the token ceiling before it finished.

    A subclass of `LLMError` so existing handlers keep working, and distinct so callers
    that *can* do something about it — retry with a bigger budget, salvage a usable
    prefix — are able to. `partial` carries what did arrive, because sometimes the answer
    is in there ahead of the truncation and throwing it away loses the day's digest.
    """

    def __init__(self, message: str, partial: str = ""):
        super().__init__(message)
        self.partial = partial


def chat(system: str, user: str, model: str, *, max_tokens: int = MAX_TOKENS) -> str:
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
        choice = data["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as ex:
        raise LLMError(f"unexpected response shape from {base_url()}: {str(data)[:200]}") from ex

    # `finish_reason: length` means the model hit the token ceiling mid-sentence. This
    # used to be discarded, and the cost was three published newsletters that were
    # nothing but the model's own truncated planning notes: a reasoning model spent its
    # whole 4000-token budget thinking and never reached the digest, the call returned
    # 200, and the transcript was written to reports/ unread. A truncated response is a
    # failed response, and the caller cannot tell unless this says so.
    if choice.get("finish_reason") == "length":
        raise Truncated(
            f"{model} hit the {max_tokens}-token ceiling before finishing "
            f"({len(content)} chars returned). Raise max_tokens, or use a model that "
            "does not spend the budget on reasoning.", partial=content)
    return content


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


def catalog(env: dict | None = None, timeout: int = 30) -> list[dict]:
    """`GET {base}/models`, the OpenAI-compatible discovery endpoint. Used by
    `--catalog` so choosing a model is a command rather than a guess, and by
    `auto_model` so it is not even a command.

    `env` is threaded through like every other reader here, so a caller can ask about a
    configuration other than the ambient one — which is what the separation fence does.
    """
    env = os.environ if env is None else env
    if not configured(env):
        raise LLMError("RADAR_LLM_BASE_URL and RADAR_LLM_API_KEY must both be set")
    req = urllib.request.Request(
        f"{base_url(env)}/models",
        headers={"Authorization": f"Bearer {api_key(env)}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("data", [])
    except (urllib.error.URLError, OSError, ValueError) as ex:
        raise LLMError(f"could not read {base_url(env)}/models: {ex}") from ex


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
