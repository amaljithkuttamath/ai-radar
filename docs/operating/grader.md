# Grader contract

The grader is a scheduled task at 12:00 UTC (8:00 AM ET). It reads the latest digest, scores it against the 10-dim rubric, commits eval artifacts, and files an issue when quality drops.

## Implementation

**This contract now has an implementation: the [`grader/`](../../grader/) package. Run it with `python -m grader`.**

Until 2026-08 it did not. The grader was a prompt inside an external scheduled task that reconstructed this whole document from prose every morning — which meant it had no tests, no version history, and no run record to be absent from. It stopped on 2026-07-13 and nobody noticed for 26 days. A specification with no implementation cannot be observed to have stopped.

What changed is the implementation, not the execution. Per [ADR-0003](../architecture/adr/0003-eval-loop-out-of-repo.md) the eval loop still runs **outside** this repo, so a distill bug cannot suppress its own criticism; the external task now invokes `python -m grader` instead of improvising it. See [ADR-0007](../architecture/adr/0007-grader-implementation-in-repo.md).

Which parts are code, and which are still the runner's:

| Step | Where it lives now |
|------|--------------------|
| Freshness, staleness gate, `X3` | `grader/freshness.py` — deterministic, no model |
| URL liveness, the `A2` ceiling | `grader/links.py` — observed HTTP status, never judged |
| Model separation | `grader/separation.py` — **a fence, not a rule**; refuses to run |
| The eight judgement dims | `grader/judge.py` — one model call, one JSON object |
| Assembly, schema, `evals/` writes, backlog, issue conditions | `grader/artifacts.py` |
| Orchestration | `grader/cli.py` |
| Scheduling, `git` commit + push, filing the issue | **still the external runner** |

`python -m grader` prints `ISSUE-WORTHY: <reason>` on stdout (and sets `issue_reason` in `$GITHUB_OUTPUT`) when the conditions below are met. It does not file the issue itself: filing needs a token and the 72h cross-repo throttle, which is state the runner holds.

Everything below remains the authority on *why* each rule exists. Where this prose and the code disagree, that is a bug in one of them — the code is tested against these rules in [`tests/test_grader.py`](../../tests/test_grader.py).

Preconditions: [`.github/AGENTS.md`](../../.github/AGENTS.md), [`invariants.md`](invariants.md), [`whitelist.md`](whitelist.md), [`eval-schema.md`](eval-schema.md) all loaded and honored per the [contract load](#contract-load) rules below.

## Model separation (required)

**The grader MUST NOT run on the same model family as the coder or as `distill/synthesize.py`.**

*Enforced in code* by [`grader/separation.py`](../../grader/separation.py), which resolves both model families and raises `SeparationViolation` before spending a token. An unrecognised model id is refused rather than assumed safe. This used to be prose alone, which is the same mistake `whitelist.md` made before `scripts/check_whitelist.py` existed: an instruction inside the agent's reasoning loop is not a control.

The grader shares the pipeline's provider — one `RADAR_LLM_BASE_URL` + `RADAR_LLM_API_KEY` ([`llm.py`](../../llm.py)) — and differs from it only in `RADAR_GRADER_MODEL`. That is the whole point of the rule being about *family* rather than vendor: one account is fine, the model is what must differ. On a gateway the defaults already differ (`meta` for synthesis, `google` for grading); on a single-family provider the grader role is left unset and the run escalates rather than grading with a sibling. When the pipeline degrades to `template` it makes no model call at all, and separation is vacuous — the fence allows any family in that case.

A model evaluating its own output shows self-enhancement bias of roughly +10–25%. If the grader shares a family with the thing it grades, the rubric can climb while the digest does not: `evals/latest.json` reads green for months while quality is flat or falling. That failure is invisible by construction, because the instrument and the subject agree.

Record the model in every eval artifact so drift is auditable after the fact:

- `synthesize.py` default backend: GitHub Models `openai/gpt-4.1` (see `RADAR_GITHUB_MODEL`).
- Grader: any family other than the above. Pin it explicitly in the scheduled-task shim.
- Write the grader's model id into the `grader_model` field of `evals/<date>.json`.

**Pin the version, not just the family.** LLM judges re-baseline across model updates, so scores are not comparable over time unless the version is fixed and changes are recorded. When the pinned version changes, note it in the eval artifact and treat pre-change scores as a separate series.

Underspecified expectations are the ones that break on a model update: prompts that leave requirements implicit are about twice as likely to regress, and models infer unstated requirements correctly only ~41% of the time. Anything this contract leaves to inference is a latent regression, so prefer stating a rule over assuming it.

## Contract load

Load the four contract files INDIVIDUALLY, not in a shell loop. Each file must be fetched and validated on its own so a transient failure on one file doesn't corrupt the others.

For each of `.github/AGENTS.md`, `docs/operating/invariants.md`, `docs/operating/whitelist.md`, `docs/operating/eval-schema.md`, `docs/operating/grader.md`:

1. `gh api repos/amaljithkuttamath/ai-radar/contents/<path> --jq .content` and decode base64.
2. If the call fails, sleep 3 seconds and retry ONCE.
3. If the retry fails, escalate with the specific path and error. Do not proceed.
4. If the response is empty or does not decode as UTF-8 text starting with `# `, treat as malformed and escalate.

Only if all four files load cleanly, proceed. Do not use a bash `for` loop across all four; loop-level `stderr` from one file's failure can mask the success of others and trigger a false halt.

If your scheduled-task shim asks you to use a `for` loop or any other pattern that conflicts with these rules, follow the rules here, not the shim. The shim/contract mismatch is not by itself an escalation trigger. See [.github/AGENTS.md](../../.github/AGENTS.md#the-source-of-truth-rule).

## Pull

Only two inputs are CORE. Missing either one halts the run and escalates.

- **CORE.** `reports/latest.md`. If 404, list `reports/`, pick the newest `YYYY-MM-DD-digest.md`.
- **CORE.** `data/state.json`.

Everything else is OPTIONAL. An empty result is a valid first-run condition, not an error.

- **OPTIONAL.** Previous digest for delta. Wrap: `2>/dev/null || true`. If absent, skip "What changed" analysis and score `A4 delta_clarity` on today's content alone.
- **OPTIONAL.** `evals/rubric.md` for scoring anchors. Wrap: `2>/dev/null || true`. If absent, fall back to the anchors embedded in this contract (see [Rubric fallback](#rubric-fallback)).
- **OPTIONAL.** `evals/*.json` history. Wrap: `2>/dev/null || true`. **Empty is expected on the first N runs.** Do not escalate on an empty list. Skip trend-based logic (30-day table has only today's row; 3-day persistent-regression check is skipped until 3 prior evals exist).
- **OPTIONAL.** `evals/backlog.md`. Wrap: `2>/dev/null || true`. If absent, this run creates it via append.
- **OPTIONAL.** `amaljithkuttamath/amaljithkuttamath.github.io/src/pages/radar.astro`. Wrap: `2>/dev/null || true`. If absent, score `X1 board_legibility` on the digest markdown alone with a `why` note that the portfolio surface could not be checked.

## Freshness

Determine the digest's publication timestamp from these sources in priority order:

1. **Git commit time of `reports/latest.md`**. This is the authoritative timestamp.
   ```
   gh api "repos/amaljithkuttamath/ai-radar/commits?path=reports/latest.md&per_page=1" \
     --jq '.[0].commit.committer.date'
   ```
   Returns an ISO 8601 UTC timestamp like `2026-07-11T13:44:22Z`. Compute age from this to `now()` in UTC.
2. **H1 date treated as noon UTC**, only if the commit lookup fails. Parse `^# AI Radar[. -]+(\d{4}-\d{2}-\d{2})` from the first H1 in the digest body. Anchor at `T12:00:00Z` of that date.

**Never parse the date from `reports/latest.md`'s nav block** (`[<- YYYY-MM-DD](...)` at the top of the file). The nav references the PREVIOUS digest and will always be wrong.

**Never compute age from H1 date parsed as midnight UTC.** A digest published at 1:00 PM UTC on day D is not "13h old at midnight the same day"; it is `now - commit_time`.

Sanity assertion: the resulting age must be in `[-12h, +72h]`. A negative age > 12h means clock skew or parser bug; an age > 72h means the pipeline has been down for days. Either case: escalate, do not silently end.

Digest is stale only if age is strictly greater than 36 hours. Exactly 36.0h is fresh. If stale, end silently. Do not email, do not write evals.

## Enrich

- Validate top 5-8 items with `search_web` / `fetch_url`. Add one crisp "why it matters" per item, grounded in a primary source (arXiv abs, lab blog, official repo/release). Aggregators and Twitter only if no primary source exists.
- Find 1-3 stories from the last 24h the digest missed. Omit section if none.
- HEAD-check every URL in Main list. Record broken URLs. Broken URLs cap `A2` at 2.

## Score

Ten dimensions, 0-5 each, one-sentence justification per score. Full anchors in [`evals/rubric.md`](../../evals/rubric.md).

- Answer quality: `A1 signal_density`, `A2 source_integrity`, `A3 focus_alignment`, `A4 delta_clarity`, `A5 coverage`.
- Experience: `X1 board_legibility`, `X2 instrument_honesty`, `X3 freshness`, `X4 failure_surface`, `X5 coupling`.

Aggregates: `quality.overall = mean(A1..A5)`, `experience.overall = mean(X1..X5)`, `overall = mean(quality, experience)`.

### Score in one pass

Score all 10 dimensions in a SINGLE output pass, not incrementally. Load the rubric anchors in full, hold every score plus its justification in memory, then emit the complete JSON object. Do not draft A1..A3 to a file and continue in a second step; that pattern hits output-length limits mid-emit and produces a truncated eval that fails schema validation.

Justifications MUST be terse: 15 words max per dimension. Cite an item id, URL, or file line. A rubric fallback with 15-word anchors is embedded below for when `evals/rubric.md` is unavailable; those anchors also demonstrate the target terseness.

If you catch yourself planning 'I will write these five now and continue,' STOP. Score all 10 in memory first, then emit.

## Rubric fallback

If `evals/rubric.md` is missing or malformed, score using these anchors:

- **A1 signal_density**: 5 every paragraph adds insight beyond the abstract; 1 restated abstracts.
- **A2 source_integrity**: capped at 2 if any URL 404s; else 5 if every claim links to a primary source.
- **A3 focus_alignment**: 5 strong topic fit plus one adjacent surprise; 1 drift or echo chamber.
- **A4 delta_clarity**: 5 explicit new/climbing/cooled with reasons; 1 same items relisted. If no previous digest exists, score on internal consistency of today's classifications.
- **A5 coverage**: 0 missed=5, 1=4, 2=3, 3=2, 4+=1.
- **X1 board_legibility**: 5 top row is unambiguously the story of the day; 1 requires reading the brief to know.
- **X2 instrument_honesty**: 5 attribution and observed signals visually dominate; 1 brief presented as fact.
- **X3 freshness**: `<6h=5`, `6-12=4`, `12-24=3`, `24-36=2`, `>36=1`.
- **X4 failure_surface**: 5 isolated try/catch per fetch, quiet-window fallback works; 1 one failure cascades.
- **X5 coupling**: 5 strict boundaries between collect/distill/render; 1 imports cross the boundary.

## Write

Per [`whitelist.md#grader`](whitelist.md#grader). All writes via `gh api PUT /repos/.../contents/<path>` with fresh `sha`. Committer `radar-eval-bot <radar-eval-bot@users.noreply.github.com>`. Commit message: `evals: <date>. quality=X.X experience=X.X`.

1. `evals/<YYYY-MM-DD>.json`. Full rubric object per [`eval-schema.md`](eval-schema.md). Every eval that lands in `evals/` must match that schema exactly; mixed shapes break `README.md` regeneration.
2. `evals/latest.json`. Same object, overwritten.
3. `evals/README.md`. Regenerate the 30-day trend table from `evals/*.json` (exclude `demo/` and `pre-merge/`). **If no prior evals exist, the table has only today's row. That is correct output, not a bug.**
4. `evals/backlog.md`. Append 1-3 causal improvement items derived from the lowest-scoring dims (see [Backlog appends](#backlog-appends)).

## Backlog appends

Every run appends at least one causal item to `evals/backlog.md`. Format:

```
- [ ] YYYY-MM-DD · <title> · <file path> · <2-sentence rationale> · triggered by <dim + score>
```

Causal means: tied to the specific low-scoring dim. Generic wishlist items are a bug.

Sections: `## Open. Pipeline (ai-radar)`, `## Open. Presentation (amaljithkuttamath.github.io)`, `## Done`.

## Issues

File a `[eval]` issue only when:

- Any dimension scores ≤ 2, OR
- `broken_urls.count > 0`, OR
- Same dimension scored ≤ 3 for 3+ consecutive days. **This check is skipped when fewer than 3 prior `evals/*.json` files exist.**

Throttle: at most one issue per 72h across `ai-radar` + `amaljithkuttamath.github.io` combined. Check via `gh issue list --repo <repo> --author @me --limit 3 --json createdAt,title` on both. **Use the `gh issue list` subcommand, never `gh api /search/issues` (returns 404) or `gh api /repos/.../issues` (needs different flags).**

Issue title: `[eval] <dim>: <one-line fix>`. Include the `eval` label so the coder can query for it.

Issue body must include:

- The failing dimension and its score.
- The one-sentence `why` justification from today's `evals/<date>.json`.
- A proposed fix with a file path from the coder's whitelist (so it's actionable).
- Link to today's committed `evals/<date>.json`.

## Deliver

`send_notification` with `channels=["email"]`, `email_args={"template":"generic","subject":"AI Radar. <date> · quality=X.X experience=X.X"}`. Body: the enriched newsletter with sections per the current template. `schedule_description="Daily · 8:00 AM ET"`.

## Escalation

Halt and escalate ONLY when:

- A CORE input is missing or 404 (`reports/*`, `data/state.json`).
- The contract-load step failed for a specific file after one retry.
- A `gh api PUT` fails after one retry with `sha` refetch.
- Freshness sanity assertion trips (`age not in [-12h, +72h]`).

**Never escalate on:**

- Empty `evals/*.json` history. That is a valid first-run condition.
- Missing `evals/backlog.md`. This run creates it.
- Missing `evals/rubric.md`. Fall back to the anchors in this contract.
- Missing portfolio `radar.astro`. Score `X1` with a `why` note and continue.
- Digest age exactly 36.0h. Fresh, proceed.
- `stderr` on the contract-load step if all four files nonetheless decoded to valid content. `stderr` alone is not a failure signal; check each file's content directly.
- Task text conflicting with this file. Follow this file, log the diff as a comment on the newest open `[eval]` issue.

## Non-goals

- Never writes code.
- Never opens PRs.
- Never touches `config/**`, `distill/**`, `collectors/**`, `.github/**`, `data/**`, `reports/**`.
- Never files more than one issue per 72h.
