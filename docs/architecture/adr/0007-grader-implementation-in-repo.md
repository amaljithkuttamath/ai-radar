# ADR-0007. The grader's implementation moves in-repo; its execution does not

**Status.** Accepted, 2026-08. Extends ADR-0003; does not supersede it.

## Context

ADR-0003 put the eval loop outside this repo so a bug in the pipeline could not suppress its own criticism. That reasoning holds and is not revisited here.

What ADR-0003 did not say is *where the grader's code lives*, and the answer turned out to be nowhere. The grader existed only as a prompt inside a Perplexity scheduled task, reconstructing the whole of `docs/operating/grader.md` from prose every morning. The consequences compounded:

- **No tests.** Every rule in `grader.md` — the 36h staleness boundary, noon-anchoring the H1 date, never parsing the nav block, scoring all ten dimensions in one pass — is written as a warning because an agent got it wrong at least once. Prose cannot regress-test itself.
- **No version.** Scores are only comparable within a fixed model pin, and `grader.md` says so, but nothing recorded what the grader actually was on a given day. `evals/latest.json` still lacks the `grader_model` field its own schema marks required.
- **No run history.** This is what made it fatal. The grader stopped on 2026-07-13 and went unnoticed for 26 days. A scheduled task that silently stops produces no error and no log — "ran fine" and "never ran" are identical from outside — and because the grader appeared in no workflow list and no repo file, there was nothing to observe its absence. `watchdog.yml` was built afterwards for exactly this and now catches it, but detection is the second line; the first is being a thing that can be looked at.

The document specifying the grader was 200 lines of hard-won operational detail. The thing implementing it was a text box in a SaaS product.

## Decision

**The implementation moves into `grader/`. The execution stays external.**

The external scheduled task now invokes `python -m grader` instead of improvising the contract. It keeps the responsibilities that genuinely need to be outside: scheduling, the PAT, the `git` commit and push, and filing the GitHub issue under the 72h cross-repo throttle. The grader package does the reading, checking, scoring, assembling and validating.

This satisfies ADR-0003 exactly as written — the loop runs outside CI, on a different schedule, with a different credential, on a model from a different family — while removing the property that was never a decision, only an accident: that the grader was unversioned and invisible.

**Anything checkable is checked, not judged.** `X3 freshness` is arithmetic on the digest's age. The `A2` ceiling is an observed HTTP status. A judge cannot see a 404 and, asked about one, will confabulate; so the model is asked only for the eight dimensions that require reading, and its `A2` is capped afterwards by what was measured. The one falsifiable quality dimension stays falsifiable.

**Model separation becomes a fence.** `grader/separation.py` resolves the grader's family and the pipeline's, and refuses to run if they match. An unrecognised model id is refused rather than assumed safe — a fence that opens on the unfamiliar is not a fence, and a new provider appearing is precisely when a stale allowlist would wave a violation through. This mirrors `scripts/check_whitelist.py`, which exists because `whitelist.md` claimed to be "enforced in code" and was not.

**The grader never imports `distill`.** It re-implements the pipeline's backend resolution in `separation.py` instead. Importing the graded pipeline into its grader would couple them at the seam ADR-0003 keeps apart, and `distill.synthesize` pulls in pyyaml transitively — which would make the grader unable to run in exactly the scenario where it matters most: when the pipeline's dependencies are the thing that is broken. A test asserts the mirror agrees with the real resolver across the backend matrix, so the duplication cannot drift silently.

**A stale digest still ends the run silently.** Unchanged from `grader.md`, and worth restating as a decision: a missing digest is the pipeline's failure to publish, not the grader's to score. Writing a low eval for an absence would put the grader's opinion of a gap into the quality trend. Detecting the gap belongs to `watchdog.yml` (ADR-0005).

## Consequences

**Positive.**

- The rules that were previously enforced by an LLM's compliance are now enforced by tests: 47 of them, over freshness anchors, link handling, the separation fence, verdict parsing, aggregate arithmetic, schema validation, and the issue conditions.
- A malformed or truncated verdict escalates instead of being defaulted into the permanent trend — the documented failure mode of incremental scoring.
- The grader runs locally (`python -m grader --dry-run`) against any digest, so a rubric change can be tried before it ships.
- `grader_model` is now written on every eval, making score drift across model updates auditable for the first time.

**Negative.**

- Two artefacts must stay in step: `grader.md` (why) and `grader/` (what). The contract explicitly states the code is tested against it and that disagreement is a bug in one of them, but nothing mechanically enforces the pairing.
- The external runner still holds the credential and the schedule, so it can still silently stop. This ADR reduces the blast radius of that; `watchdog.yml` is what detects it.
- Backend resolution is deliberately duplicated between `distill` and `grader`. Guarded by a test, but it is duplication and should be recognised as the cost of independence rather than an oversight.

**Rejected.**

- *Running the grader as a GitHub Actions workflow.* Simplest to operate and the watchdog already covers it, but it puts the critic inside the same repo, runtime and credential surface as its subject, which is the thing ADR-0003 decided against. Not worth reopening for operational convenience.
- *Leaving it fully external and only updating the prose.* Preserves ADR-0003 literally while leaving the grader as untestable and unobservable as it was on 2026-07-13.
- *Having the grader import `distill` for backend resolution.* Less duplication, wrong coupling — see above.
