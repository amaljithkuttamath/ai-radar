One or more pipeline artifacts have gone stale:

```
__REASON__
```

Thresholds and classification live in [`scripts/health.py`](../scripts/health.py); this issue is filed by [`watchdog.yml`](workflows/watchdog.yml). The full picture, including signals that are only drifting rather than breached, is on the [status page](https://amaljithkuttamath.github.io/ai-radar/) and in [`data/health.json`](../data/health.json).

This fires regardless of cause. Check by artifact:

**Eval loop (`evals/latest.json`)** — the grader runs as an external scheduled task ([ADR-0003](../docs/architecture/adr/0003-eval-loop-out-of-repo.md)), so it is invisible to this repo's Actions runs. Staleness is the only in-repo signal that it stopped.

1. Does the grader scheduled task still exist? It has silently vanished before (2026-07-13, unnoticed for six days).
2. Has its PAT expired? It needs `contents: write` and `issues: write`.
3. Did it escalate and end silently, per [`grader.md`](../docs/operating/grader.md)?
4. Is there an open `[eval]` issue or bot PR blocking the coder's gates?

**Digest (`reports/*-digest.md`)** — produced by `distill.yml`, which is visible in the Actions tab. A stale digest with a red distill means the pipeline ran and failed; a stale digest with a green distill means it succeeded without committing, which is a different and worse bug.

1. Check the [distill runs](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/distill.yml). The synthesis step calls a model backend and dies on any non-413 HTTP error.
2. On 2026-07-31 the GitHub Models endpoint began returning `410 Gone` and distill failed for ten consecutive days while `collect-corpus` stayed green. A green collector is not evidence of a healthy digest.

**Collector (`collect-corpus`)** — if this is red, nothing downstream can be right. Fix it first; the other two signals are meaningless until the corpus is fresh.

Note that the pipeline stages are independent. `collect-corpus` and `distill` kept committing digests daily throughout the 2026-07 grader outage, and `collect-corpus` stayed green throughout the 2026-08 digest outage. A green anything is not evidence that the rest is alive.

Close this once the named artifacts resume; the watchdog will not file another while it is open.
