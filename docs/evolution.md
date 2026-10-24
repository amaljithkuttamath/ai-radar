# Lightweight digest-prompt evolution

Radar can propose one change to its digest prompt, replay saved inputs against
both prompt versions, compare the results, and remember the outcome. This is a
local command using the existing model backends and Python standard library.
It adds no framework, service, scheduler, or runtime dependency.

## Capture real runs

Successful synthesis with `github`, `anthropic`, or `ollama` automatically saves
a JSON case in `data/evolution/cases/`. The case contains the exact system and
user messages, original output, backend, and model name. The assembled user
message already freezes the date, candidate selection, enrichment, movers, and
story arcs. GitHub payload reductions are captured after the final successful
attempt. Capture failure logs a warning without preventing publication.

`dryrun` and `template` outputs do not become cases. The existing production
workflow uploads cases as `digest-replay-<run-id>-<attempt>` artifacts with
30-day retention. Download and extract one or more of these artifacts from the
distill Actions run into `data/evolution/cases/`. Local runs already save there.
Cases and experiments are gitignored. Keep useful cases before CI retention
expires; the optimizer never fabricates missing history.

## Run one experiment

Provide between one and three distinct case files. With no candidate supplied,
Radar proposes one complete prompt revision using the current prompt, the
selected cases, the fixed rubric and interests, and recent experiment lessons:

```bash
uv run python -m distill.evolution run \
  --case data/evolution/cases/<case-id>.json \
  --backend github \
  --judge-backend anthropic \
  --hypothesis "Make numerical claims traceable to the supplied evidence."
```

To test a prompt you or the existing improvement agent have already written:

```bash
uv run python -m distill.evolution run \
  --case data/evolution/cases/<first-case-id>.json \
  --case data/evolution/cases/<second-case-id>.json \
  --candidate /tmp/radar-candidate.md \
  --backend github \
  --judge-backend ollama \
  --judge-model qwen3:4b
```

Use actual case paths in place of the placeholders. Candidate files contain the
entire proposed `distill/digest.md`, starting with a Markdown heading.

The backend credentials are unchanged: GitHub uses `GITHUB_TOKEN`, Anthropic
uses `ANTHROPIC_API_KEY`, and Ollama uses the local service. The CLI accepts
`--model` and `--judge-model`; otherwise it uses the existing `RADAR_*_MODEL`
environment variables and backend defaults. Synthesis and judging must use
different recognized model families, even across providers. Unknown family
names are rejected rather than silently accepting a potentially identical judge.
This heuristic is conservative; it cannot establish independence of arbitrary
fine-tunes with misleading names.

Each experiment makes at most **13 model calls**: one proposal plus, for each of
up to three cases, two synthesis calls and two judgments. Supplying a candidate
removes the proposal call. Identical outputs or failed deterministic checks
skip judging. There are no automatic retries or recurring runs. Calls use the
existing backend timeouts and quotas; a call limit is not a dollar budget.

The proposer receives labeled excerpts (up to 6,000 characters of input and
2,000 of output per case, retaining the beginning and end) and compact prior
lessons. Historical system prompts are omitted from that request. Replay and
judging always use the complete frozen input. An oversized GitHub proposal
request fails before a model call with guidance to supply a candidate or change
backend. The character limit is a conservative estimate, not a tokenizer;
provider context-limit errors are still recorded as failed experiments.

## What is compared

Both versions are regenerated with the same synthesis model and exact saved
user message. The baseline is the current `distill/digest.md`, not the historical
output. The captured original remains evidence for the proposer.

Deterministic checks reject a candidate with the wrong date/header, URLs absent
from the input, or no clickable source link when source URLs were supplied.
These are basic text checks, not a full Markdown parser or live link checker.
The independent judge assesses semantic grounding, numerical claims, useful
insight, alignment, delta clarity, and coverage of the supplied candidates using
A1–A5 from the frozen rubric. It cannot assess missing stories outside the saved
corpus or the X-axis presentation and operational metrics.

Each pair is judged twice with its order reversed:

- `keep`: at least one case wins in both orders; every other case wins or ties
  in both orders; no candidate fails a deterministic check.
- `discard`: a case loses in both orders or fails a deterministic check.
- `inconclusive`: no demonstrated gain, or an order-dependent judgment.
- `error`: a model request fails or returns an invalid response. Partial outputs
  and the failure are retained; the command exits nonzero.

`keep` means **retain for review on these cases**, not proven general improvement.
Two orderings reduce position bias; they do not eliminate model randomness or
overfitting. Before adopting a candidate, rerun it with `--candidate` against
fresh cases that were not supplied to its proposer. Keep the synthesis model and
judge model fixed within a comparison; provider aliases may still change over
time. Review numerical and factual claims yourself before merging.

## Inspect and learn

The command prints the experiment folder under `data/evolution/experiments/`:

- `baseline.md`, `candidate.md`, `candidate.diff`: frozen prompts and review diff.
- `inputs.json`: original cases, fixed rubric, and original interest profile.
- `judge-system.txt`, `proposal-system.txt`: exact evaluator and proposer instructions.
- `proposal-input.json`, `proposal-response.txt`: automatic proposal evidence,
  when a proposal was generated.
- `cases/<n>/`: both outputs and raw judge requests/responses in each order.
- `result.json`: per-case checks, judgments, overall decision, model identities,
  hashes, call count, hypothesis, and lessons.

Every started experiment appends its result to
`data/evolution/experiments.jsonl`, including failures and rejected candidates.
The next automatic proposal receives up to the last five records matching the
current rubric and interest-profile hashes. Lessons are experimental evidence,
not automatically inserted editorial instructions. The judge instructions are
fixed in code and cannot be changed by a candidate prompt.

Run experiments serially in one checkout. The loop never changes the production
prompt, report files, movers state, rubric, or interests, and never sends email,
opens issues, or publishes a PR. To adopt a result, inspect `candidate.diff`,
verify that the current prompt still matches `baseline.md`, and submit only the
digest-prompt change through the existing draft-PR review process. After merge,
the next synthesis uses the approved prompt and captures new evidence.

## Validation

```bash
uv run --with pytest pytest tests/ -q
uv run python -m distill.evolution run --help
```

The tests replace network model calls at their boundary and exercise capture,
replay, order reversal, grounding checks, memory reuse, and error retention.
They verify the mechanism; a model-backed experiment is needed to demonstrate
an actual editorial improvement.

Real-model trial reports: [initial trial](evolution-trial-2026-10-22.md) and
[iteration 2](evolution-trial-2026-10-24.md). Neither candidate has been promoted.
