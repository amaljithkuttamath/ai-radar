The eval loop has produced nothing recently: __REASON__

The grader runs as an external scheduled task ([ADR-0003](../docs/architecture/adr/0003-eval-loop-out-of-repo.md)), so it is invisible to this repo's Actions runs. Staleness of `evals/latest.json` is the only in-repo signal that it stopped.

This fires regardless of cause. Check in order:

1. Does the grader scheduled task still exist? It has silently vanished before (2026-07-13, unnoticed for six days).
2. Has its PAT expired? It needs `contents: write` and `issues: write`.
3. Did it escalate and end silently, per [`grader.md`](../docs/operating/grader.md)?
4. Is there an open `[eval]` issue or bot PR blocking the coder's gates?

Note the pipeline itself may be perfectly healthy. `collect-corpus` and `distill` are independent of the grader and kept committing digests daily throughout the last outage, so a green digest is not evidence the eval loop is alive.

Close this once evals resume; the watchdog will not file another while it is open.
