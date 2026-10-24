# Digest evolution, iteration 2 — 2026-10-24

**Result: promising, but still inconclusive.** The candidate received four
preferences and two ties across three paired comparisons judged in both orders.
It won both orders on one development case, but split win/tie on the other
development case and on the fresh reserved case. The production prompt was not
changed. These six votes are not six independent trials.

## What changed

The proposer received both cases and the saved lessons from the
[first trial](evolution-trial-2026-10-22.md). It added four lines to the baseline:

> **Treat a title or model name as a label, not evidence:** do not infer capabilities, mechanisms,
> results, or challenged assumptions from it. Award or describe the model-judged novelty point
> only when the item's summary, reasons, or other supplied fields directly support that judgment;
> otherwise preserve the supplied score and make no novelty claim.

This replaces the previous candidate as the hypothesis under test; it does not
stack additional instructions onto that inconclusive candidate.

## Results

| Case | Candidates | Baseline / candidate words | Forward / reversed judgment | Case verdict |
| --- | --- | --- | --- | --- |
| Oct 22, development | 15 | 835 / 855 | candidate / tie | inconclusive |
| Oct 21, development | 12 | 634 / 745 | candidate / candidate | keep |
| Oct 23, reserved | 13 | 679 / 698 | candidate / tie | inconclusive |

Both experiment-level verdicts were `inconclusive`. All six replay digests
passed the deterministic date/header and supplied-URL checks. Word counts use
whitespace splitting. The candidate was longer on every case, especially Oct 21.

The clearest observed benefits were more conservative novelty scoring and less
inference from model names. For example, the Oct 21 baseline inferred sparse
architecture from Hy-Memory's name, although the supplied fields contained no
architecture description. The candidate explicitly acknowledged that evidence
gap. On the reserved case, the baseline raised WeVisOne-VL from 4 to 5 based on
an assertion of novelty; the candidate retained 4. The supplied excerpt described
its method, but did not establish the novelty claim.

The improvement was not uniform. The Oct 22 candidate still made a broad claim
about architecture complexity. The judge preferred some baseline action items
and returned ties when it weighed those against speculative scoring. Judgments
also contained imprecise descriptions of grouping and coverage; neither a
model vote nor a passed URL check establishes complete factual correctness.

## Method and limits

- Same models as iteration 1: `gpt-5.6-sol` for proposal and generation,
  `claude-sonnet-5-5` for judging, through the isolated CLI transport adapter.
  No production backend or evaluator changes.
- The reserved corpus came from the
  [Oct 23 collection run](https://github.com/amaljithkuttamath/ai-radar/actions/runs/39979375379):
  309 raw items, 13 selected candidates. No raw item's primary URL appeared
  anywhere in either development input, so the overlap filter removed nothing.
  The reserved corpus was not supplied to the proposer.
- The candidate was frozen before reserved evaluation. Baseline, candidate,
  rubric, interest profile, and model identifiers matched across experiments.
- Completed 14 real model calls: one proposal, six replay digests, six judgments,
  and one original digest for reserved-case capture. No retries or candidate
  search until a win. Each pair used identical frozen input.
- Reconstructed cases use lexical clusters, 360-character summaries, no
  enrichment, and first-run movers. Historical delta quality was not tested.
  A single generation per prompt and one judge model leave substantial variance.

The next useful check is another generation pair on unused data with this same
candidate. Editing the prompt again now would make it harder to distinguish a
real gain from generation and judgment variance. This trial alone does not
justify promotion.

## Isolation verification

The digest prompt, latest report, rubric, and profile hashes remained unchanged.
The trial never calls `save_state`, and reserved-case assembly redirects its
state path to a nonexistent file inside the trial directory.

The complete isolation check nevertheless detected a separate workspace change:
`data/state.json` was replaced with a `Reliable agent evaluation` fixture during
the run, and a new `tests/test_pipeline.py` contains that fixture. This trial did
not run those tests or write the state file. The change was left untouched; its
origin is not established by the trial logs. Frozen development inputs and the
reserved case's isolated state path keep it out of these comparisons.

## Local evidence

Raw evidence is gitignored and available in this checkout:

- [Candidate diff](../data/evolution/experiments/20261024T041603Z-7da40e84/candidate.diff)
- [Development results and judge explanations](../data/evolution/experiments/20261024T041603Z-7da40e84/result.json)
- [Reserved results and judge explanations](../data/evolution/experiments/20261024T041925Z-13f5dada/result.json)
- [Reserved baseline digest](../data/evolution/experiments/20261024T041925Z-13f5dada/cases/1/baseline.md)
- [Reserved candidate digest](../data/evolution/experiments/20261024T041925Z-13f5dada/cases/1/candidate.md)
- [Trial runner](../data/evolution/trials/2026-10-24/run_trial.py)
- [Verification and file hashes](../data/evolution/trials/2026-10-24/verification.json)

Both results and their lessons were appended to `data/evolution/experiments.jsonl`.
Candidate SHA-256:
`73b46549a3758d07a0086c660a0b9a3d18c9a53eee9ead066ec7939bf559d72d`.
