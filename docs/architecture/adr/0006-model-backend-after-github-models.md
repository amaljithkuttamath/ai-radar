# ADR-0006. Model backend after GitHub Models, and degradation as a first-class path

**Status.** Accepted, 2026-08. Supersedes the backend choice in ADR-0001's CI notes; does not touch ADR-0003.

## Context

GitHub Models was retired on 2026-07-30 — announced 2026-06-16, with brownouts on 07-16 and 07-23. `https://models.github.ai/inference` now returns `410 Gone` permanently, for both chat completions and embeddings. It was this pipeline's default CI backend, chosen because it was free, needed no card, and authenticated with the `GITHUB_TOKEN` the workflow already had.

The last digest published on 2026-07-30. `distill` then failed on every scheduled run for ten days. `collect-corpus` stayed green the whole time, so the corpus kept growing while nothing was written from it.

The retirement is not the interesting part. Providers withdraw; the announcement was six weeks ahead and the brownouts were two rehearsals. The interesting part is that a provider going away took the entire product down, and did so for ten days:

- `main()` handled exactly one HTTP error class — `413`, via a payload-shrinking ladder. Every other status re-raised out of `main()` and failed the job.
- Nothing downstream distinguished "the digest is bad" from "there is no digest". The workflow went red daily, which is a signal nobody was reading (see ADR-0005).
- The `template` backend — a complete, model-free digest renderer that was already in the repo and needed no key — sat unused, because nothing was wired to reach for it.

So the pipeline had a working fallback the whole time and no path to it.

A second defect surfaced while testing the fallback: `call_template` recovered its input by regex-scanning the assembled prompt with `\[\s*\{.*\}\s*\]` under `DOTALL`. The prompt carries several top-level JSON blocks (movers, story arcs, clusters, then candidates), so a greedy match spans from the first to the last and decodes as nothing. Every test fixture produced an empty delta — one array, greedy match lands correctly — so it passed CI and failed on real data. The fallback would have emitted `Could not parse items JSON` even if it had been reachable.

## Decision

**`auto` is the default backend.** It resolves to `anthropic` when `ANTHROPIC_API_KEY` is present and `template` when it is not. The pipeline therefore publishes with no secrets configured at all, and upgrades to synthesis the moment a key is added — no code change, no workflow edit.

**`github` is accepted and redirected, not rejected.** It resolves to whatever `auto` would choose, with a warning naming the retirement. Hard-failing on it would break every existing config simultaneously — `distill.yml`, the README, any local shell — which is the outage again by a different route. Old configs keep running.

**Permanent failures degrade; transient failures still raise.** `{400, 401, 403, 404, 410}` and unreachable-host errors fall back to the template digest. `5xx` and `429` continue to raise, because they mean "try again", and silently swapping a retry for a worse digest would hide a real problem. `413` keeps its shrink ladder and degrades only after exhausting it.

**A degraded digest says so, in the digest.** The fallback prepends a notice naming the backend, the failure, and what is missing. An assembled list of scored items is not a written brief, and a reader who cannot tell them apart has been misled about what produced the words — `X2 instrument_honesty` in the rubric. This is also the only surface where a degraded run is visible to a human who reads the newsletter rather than the repo.

**Publishing advances state.** The state snapshot and ledger promotion previously skipped `template` alongside `dryrun`, on the reasoning that both were testing modes. With `template` now a steady-state production backend, that would have published a digest daily while never advancing `state.json` or `tracked.json` — every "what changed" diff comparing against a frozen yesterday, carryover slowly emptying. The gate is now "did this run publish a real digest", which excludes only `dryrun`. `RADAR_NO_STATE=1` keeps the safety valve for local runs.

**Semantic FOCUS is disabled, not silently broken.** `distill/embed.py` raises immediately with an explanatory message instead of making a doomed request per run. `FOCUS_BACKEND=embed` degrades to lexical matching, as it already did on error — but now the log says why once, rather than printing a bare `HTTP Error 410: Gone` daily that reads like a transient blip.

## Consequences

**Positive.**

- The pipeline publishes daily with zero secrets. The failure mode of "no budget" is now reduced quality, not silence.
- Adding `ANTHROPIC_API_KEY` restores synthesis with no other change.
- The degradation path is exercised by tests parameterised over every permanent status, so the fallback cannot rot unnoticed the way the unreachable one did.

**Negative.**

- Without a key, digests carry no top-line read, no insights, and no connective prose. The `A1 signal_density` and `A4 delta_clarity` dimensions will score materially lower, and that drop is a budget decision showing up in the rubric rather than a regression to fix.
- `anthropic` is metered. There is no free tier equivalent to what was lost, and per-run cost now scales with `RADAR_AGENT` and candidate count.
- The grader's model-separation rule (`grader.md`) required the grader to differ in family from `synthesize.py`. With Anthropic as the synthesis backend, a grader pinned to an Anthropic model would violate it. Whoever restores the eval loop must pick a different family — this is a live constraint, not a hypothetical.

**Amended 2026-08-09.** The first cut of this ADR left `auto` choosing between `anthropic` and `template`, which meant anyone without a paid key sat on the template digest permanently. That mistook "GitHub Models is gone" for "free inference is gone". It is not: Groq (~14,400 req/day on Llama 3.3 70B), Google AI Studio (~1,500 req/day on Gemini 2.5 Pro) and Cerebras (~1M tokens/day) all offer cardless free tiers speaking the OpenAI chat-completions shape, and this pipeline makes roughly two model calls a day. `auto` now tries `anthropic`, then `openai`, then `template`, and `call_openai_compat` takes its provider from `RADAR_OPENAI_BASE_URL` rather than baking one in — the mistake that produced a `call_github` to delete.

This also resolves the grader constraint recorded below from the other direction: with synthesis on a free Llama or Gemini tier, the grader can sit on a different free tier and satisfy the separation fence without a paid key on either side.

**Amended 2026-08-09 (second pass).** The first amendment restored free inference but kept a per-stage provider surface: `distill` read `RADAR_OPENAI_*`, `grader` read a parallel `RADAR_GRADER_BACKEND`/`_BASE_URL`, and satisfying the separation rule meant two accounts and two keys. That divided providers by *responsibility*, which the rule never asked for — separation is about model **family**, a property of the model, not of the account it bills to.

Both stages now share one provider through [`llm.py`](../../../llm.py): `RADAR_LLM_BASE_URL` + `RADAR_LLM_API_KEY`, one OpenAI-compatible endpoint, roles differing only in which model they name. A gateway serving several families through one URL satisfies the fence on a single free key, and per-role defaults are chosen from different families so the operator need not know any model ids at all. This also deleted a real liability: `separation.py` had been re-deriving the synthesis model by mirroring `distill`'s backend resolution, duplication that needed a drift test to stay honest. Both roles read `llm.model_for()` now, so there is no mirror left to drift.

The caveat is worth recording: a single-family provider cannot satisfy the fence alone. Perplexity serves only `sonar`; Groq and Google AI Studio are effectively one family each. Their profiles leave the grader role empty so the run escalates with a message naming the fix, rather than quietly grading a model with its sibling.

**Rejected.**

- *Microsoft Foundry / Azure AI*, the migration path GitHub pointed at. It needs an Azure subscription and resource provisioning; the free, cardless property that made GitHub Models the right default does not survive the move, so it buys complexity without buying back the original benefit.
- *Failing loudly and publishing nothing* until a key is configured. That is precisely the behaviour being fixed.
- *Deleting the `github` backend name outright.* Redirecting costs one branch and keeps every existing config working.
