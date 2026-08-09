# ADR-0005. Monitor artifact freshness, in one reading, from outside the pipeline

**Status.** Accepted, 2026-08.

## Context

Two outages, one month apart, went unnoticed for their entire duration:

- **2026-07-13.** The eval loop stopped. Noticed six days later. `watchdog.yml` was built in response and correctly detects it.
- **2026-07-31.** `distill.yml` began failing on every run — the model backend started returning `410 Gone` — and committed no digest for ten days. `collect-corpus` stayed green throughout.

Both were fully visible in the Actions tab the whole time. Neither was seen. The second is the more instructive: a watchdog already existed, ran daily, and was already red. It said nothing about the digest because it only watched `evals/latest.json`. A monitor that watches one of three artifacts does not report two-thirds of the truth — it reports "stale" for the wrong reason and actively conceals the rest.

Investigating that outage also found `watchdog.yml` had never once filed an issue. `gh issue create --label watchdog` fails hard when the label does not exist, and the label was never created; under `set -euo pipefail` the step aborted, so the alerting surface carrying the runbook had never worked, and the "one open issue at a time" dedup never engaged. The watchdog built to catch silent failures was itself failing silently.

Three design questions fell out:

1. Where does the monitor run?
2. What does it measure?
3. Who decides that a reading is bad?

## Decision

**One reading, written from outside the things it watches.** `scripts/health.py` runs as its own workflow (`health.yml`, 16:00 UTC, last in the daily chain) and writes `data/health.json`. It does not run as a step of `distill.yml`, for the same reason the grader does not (ADR-0003): a monitor hosted by one of its subjects reports nothing exactly when there is something to report. `distill` had been failing for ten days; a health step inside it would have produced ten silences.

**Measure artifacts, not processes.** Freshness comes from `git log` commit times, never from a timestamp inside the file. A producer that dies mid-write, or writes a stale-but-well-formed artifact, leaves its own `date` field looking current; git's clock is the one clock the producer does not author. Workflow conclusions are read from the Actions API as secondary colour — they explain *why* an artifact is stale, but staleness is what is true regardless of cause.

**Split measuring from escalating.** `health.py` reports and never escalates: it always exits 0, even when everything is broken. `watchdog.yml` escalates and never measures: it consumes `health.py --reasons` and owns the issue and the red run. Thresholds live in exactly one file, which is what stops the two surfaces disagreeing about the meaning of "stale" — the drift that produced a watchdog blind to a ten-day outage.

**Unknown is a state.** A workflow with no observed runs, or an Actions API that cannot be read, serialises as `unknown`, never as `ok`, and is excluded from the overall reading in both directions. An unreadable API is not evidence that the pipeline is broken, and it is not evidence that it is healthy.

**The monitor must be able to report its own absence.** `data/health.json` carries its own `generated` timestamp, and the status page treats a reading older than one cadence as the headline, marking every other value not-current. A monitor that shows its last good reading forever after its writer dies manufactures confidence, which is strictly worse than no monitor.

## Consequences

**Positive.**

- One artifact (`data/health.json`) serves three surfaces: the status page, the README block, and the watchdog. They cannot disagree.
- Adding a signal means adding one entry in `health.py`; every surface picks it up.
- The status page is static and reads the JSON live at view time, so publishing it is independent of the reading — a failed commit still leaves a page showing the true, stale state.
- `health.py` is stdlib-only and installs nothing. A job whose value is running when something else is broken must not be able to fail on a dependency resolver.

**Negative.**

- Up to 24h of detection latency, bounded by the daily cadence. Acceptable against outages measured in days; if that changes, the cron is the dial.
- The Actions API read costs one token-authenticated request per workflow per day, and its failure mode is silent (`unknown`).
- Freshness needs `fetch-depth: 0`. On a shallow clone every artifact reads as new as the clone, which would report permanently healthy — a footgun for anyone copying the checkout step.

**Deferred.**

- An active probe of the model backend. It would have caught the `410` on day one rather than day ten, but the endpoint's current contract is unknown — that is the open incident — and a probe guessed against a retired API would itself be a false signal. Backend health is inferred from `distill`'s failure streak until the endpoint is resolved.
