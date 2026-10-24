# Real-model digest evolution trial — 2026-10-22

**Result: no demonstrated improvement.** The proposed prompt revision tied
with the baseline in both judging orders on both corpora. Both experiments
returned `inconclusive`. The candidate was retained as evidence, not adopted.

## Change tested

The proposer added one requirement to the existing Insights instructions:

> Each bullet must name at least two supporting items or observed signals from
> the corpus; omit patterns that lack that support.

The hypothesis was that explicit support would make cross-item insights more
verifiable and discourage unsupported filler without expanding the digest.
The unchanged candidate was then tested on a reserved corpus that was not
provided to the proposer.

## Method

- GPT `gpt-5.6-sol` proposed the change and generated every digest. Claude
  `claude-sonnet-5-5` judged baseline/candidate pairs with their order reversed.
- Used Radar's real `run_experiment` implementation and fixed A1–A5 rubric,
  with a temporary transport adapter for authenticated Codex and Claude CLIs.
  Production backends were not changed. GitHub Models requests did not return
  usable inference responses in this environment; API credentials and a running
  local Ollama model were unavailable.
- Downloaded actual `corpus-raw` collection artifacts from the runs below.
  Built frozen requests through Radar's scoring and prompt assembly, then
  generated fresh original digests for case capture. These are reconstructed
  cases from real collections, not exact historical published requests.
- Used a 48-hour window at each collection's timestamp, maximum 24 candidates,
  360-character summaries, lexical clustering, no enrichment, and first-run
  movers. There was no saved historical delta state for these cases.
- The 15 development and 12 reserved candidates had no overlapping primary
  URLs. Each prompt pair received identical frozen input. The candidate,
  baseline, rubric, interest profile, and model identifiers matched across runs.
- Completed 11 substantive model calls: two original digest captures, one
  proposal, four replay digests, and four judgments. No failed-call retries or
  repeated candidate search were used to obtain a favorable result.

## Results

| Case | Source items / selected | Baseline / candidate words | Forward / reverse vote | Decision |
| --- | --- | --- | --- | --- |
| Development, Oct 22 | 321 / 15 | 859 / 845 | tie / tie | inconclusive |
| Reserved, Oct 21 | 359 / 12 | 755 / 754 | tie / tie | inconclusive |

Word counts use whitespace splitting. All four replay digests passed the
deterministic date/header and supplied-source-URL checks.

On the development case, the judge credited the candidate's more explicitly
supported insights and more conservative novelty scores. It also noted minor
unsupported details in the candidate, including a leaderboard reference for
ARCANA, while preferring the baseline's organization. On the reserved case,
both versions covered the same stories with similar density and useful action
items. The judge found small unsupported inferences and loose groupings on
both sides, with no decisive advantage.

This establishes that real proposal, replay, judging, and lesson retention work.
It does **not** establish improved digest quality. Four judgments are two
orderings of two output pairs, not four independent trials. Generation variance,
one judge model, short source excerpts, and only two corpora limit the result.
CLI instruction delivery also differs from the production API transport, and
this run did not test historical deltas or enriched source content.

The judge occasionally credited grouping even though flat lists are permitted;
its verdict is evidence rather than a definitive quality measurement. The
evaluation rubric was kept fixed throughout this trial.

## Decision and next hypothesis

Keep the production prompt unchanged. The next useful experiment would target
unsupported factual extrapolation or novelty bonuses, which remained visible
in both versions. Any next candidate should again be tested on unused cases;
these two cases now belong to the development evidence pool.

Verified SHA-256 hashes of `distill/digest.md`, `reports/latest.md`,
`data/state.json`, `evals/rubric.md`, and `config/profile.yaml` were unchanged
after the trial. Nothing was published. Both experiment results and their
lessons were appended to the local evolution memory.

## Evidence

Collection sources:

- [Oct 22 collection run](https://github.com/amaljithkuttamath/ai-radar/actions/runs/39807738027)
- [Oct 21 collection run](https://github.com/amaljithkuttamath/ai-radar/actions/runs/39628754001)

Local artifacts below are gitignored; this report preserves the outcome even
when those artifacts are unavailable in another checkout. Experiment IDs use
UTC, while the report date uses America/New_York.

- [Trial adapter](../data/evolution/trials/2026-10-22/run_trial.py)
- [Isolation verification](../data/evolution/trials/2026-10-22/verification.json)
- [Development result and judge explanations](../data/evolution/experiments/20261023T012413Z-3f200edc/result.json)
- [Reserved result and judge explanations](../data/evolution/experiments/20261023T012613Z-0869d25f/result.json)
- [Candidate diff](../data/evolution/experiments/20261023T012413Z-3f200edc/candidate.diff)
- [Reserved baseline digest](../data/evolution/experiments/20261023T012613Z-0869d25f/cases/1/baseline.md)
- [Reserved candidate digest](../data/evolution/experiments/20261023T012613Z-0869d25f/cases/1/candidate.md)

Candidate SHA-256:
`861617da6a294d2ebfca0daae7dcc5b9c3698459cc150ce4c6a48b4054ccc368`.
