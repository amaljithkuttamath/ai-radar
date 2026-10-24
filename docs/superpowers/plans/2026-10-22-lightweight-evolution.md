# Lightweight prompt evolution implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Capture real digest inputs, try one prompt revision, compare fairly, and remember outcomes without changing the published prompt automatically.

**Architecture:** Replay the exact assembled user message rather than reconstructing time-dependent pipeline state. A stdlib CLI proposes one revision or reads a supplied candidate, regenerates both outputs, uses an independent model family to compare them in both orders, and writes an experiment directory plus an append-only JSONL log.

**Tech Stack:** Python >=3.10, existing model backends, pytest. No added runtime dependencies.

**Spec:** User-approved scope in this chat: lightweight replay, comparison, and memory; digest prompt only; fixed rubric and interests; existing draft-PR review policy.

## Global constraints

- No automatic prompt replacement, publishing, scheduling, or GitHub writes.
- Snapshot successful model runs; capture failures must not prevent publication.
- Freeze the user input, baseline/candidate prompts, rubric, interests, and model identities for each experiment.
- One candidate, at most three replay cases per invocation; no unbounded retry/search.
- Log rejected, inconclusive, and failed experiments as well as reviewable improvements.
- Preserve pre-existing collector/blocklist edits.

## Review focus

- A changed clock or movers state must not affect replay.
- A model failure or malformed judge response must never count as improvement.
- Same-family judges must be rejected before model calls.
- Invented URLs, missing source links, and wrong dates must fail deterministic checks.
- Failed experiments must retain artifacts; CI capture must survive its ephemeral checkout.

### Task 1: Capture

- [x] Write tests for frozen input capture and successful synthesis integration, including capture errors.
- [x] Run tests and observe the missing behavior.
- [x] Add `distill/evolution.py` capture helpers and integrate after successful synthesis using the actual final request (including 413 reductions).
- [x] Retain snapshots as CI artifacts; ignore local experiment data.

### Task 2: Compare and remember

- [x] Test candidate win/loss/tie, reversed-order disagreement, invalid judge output, unsupported links, model failure, and model-family separation.
- [x] Implement `python -m distill.evolution run`: optional candidate file, otherwise one automatic proposal; replay using existing backends; fixed judging criteria; evidence and JSONL memory.
- [x] Verify inputs and output artifacts without making live API calls.

### Task 3: Document and verify

- [x] Document commands, call budget, artifact download, limits, and manual review/promotion.
- [x] Run the full test suite and CLI help; inspect the final diff.

## Execution notes

The user explicitly authorized implementation. Work remains in this checkout to preserve their ongoing edits, with only named files changed. No commit or external deployment is needed for this local deliverable.

## Results

- `uv run --with pytest pytest tests/ -q`: 64 passed, including 28 evolution tests.
- CLI help, Python 3.10 syntax compatibility, workflow artifact configuration, and `git diff --check` passed.
- Independent code review identified oversized proposal payloads and missing historical judge/proposer instructions. Both were fixed with regression coverage; full replay inputs remain intact while proposal evidence uses labeled excerpts.
- No live model calls or CI runs were performed. The first model-backed trial needs real captured cases and configured synthesis/judge backends. Tests establish mechanism correctness, not editorial quality gains.
- Existing collector/blocklist edits were preserved.
