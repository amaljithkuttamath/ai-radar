# Whitelist

Single source of truth for what each agent is allowed to write.

**Enforcement.** [`scripts/check_whitelist.py`](../../scripts/check_whitelist.py) parses the [machine-readable list](#machine-readable-list) below and runs as a required status check on every PR via [`.github/workflows/guard.yml`](../../.github/workflows/guard.yml). The role is derived from the authenticated PR **author**, not the branch name: a branch prefix is agent-chosen, so inferring from it would be an instruction an agent can step around rather than a fence. Bot identities are a closed set; anything else is a human, who widens the fence by review. Review-time enforcement is [`.github/CODEOWNERS`](../../.github/CODEOWNERS).

This file is the input to that check, so the YAML block below is load-bearing: edit it and agent write scope changes. That is why it sits behind CODEOWNERS and inside the fence set.

**Fence paths — never writable by any agent, including roles not yet defined:**

- `.github/workflows/**`
- `.github/CODEOWNERS`, `.github/AGENTS.md`
- `docs/operating/**`
- `scripts/check_whitelist.py`

An agent that can edit the allowlist governing it has no allowlist. This is the one restriction that does not relax as autonomy widens. The enforcer denies these paths for every role, so adding a role cannot accidentally grant them.

> **Note.** Prior to the harness PR this file claimed enforcement "in code (each agent asserts before every git operation)". That assertion lived in a prose code block in [`coder.md`](coder.md) and was performed by the agent itself. An instruction inside the model's reasoning loop is not a control; the CI check above is.

## Grader

Direct commits to `main` allowed on:

- `evals/<YYYY-MM-DD>.json`
- `evals/latest.json`
- `evals/README.md`
- `evals/backlog.md` (append-only per [I-02](invariants.md#i-02-backlogmd-shared-write-rules))
- `evals/pre-merge/<YYYY-MM-DD>.json` (legacy, only if `evals/` root is missing)

Also allowed:

- `gh issue create` on `amaljithkuttamath/ai-radar` and `amaljithkuttamath/amaljithkuttamath.github.io`, throttled per [`grader.md`](grader.md).

Never touches: everything else, including `config/**`, `distill/**`, `collectors/**`, `.github/**`, `reports/**`, `data/**`.

## Coder

PR branches may modify:

- `config/sources.yaml`
- `config/profile.yaml`
- `config/routines.yaml`
- `config/broken_sources.yaml` (new file allowed)
- `distill/digest.md`
- `distill/brief_spec.md`

Direct commits to `main` allowed on:

- `evals/backlog.md` (append-only, for X-axis and out-of-scope escalations only)

Also allowed:

- `gh pr create --draft --label auto-improve`
- `gh issue close` on issues the coder is resolving
- `gh issue comment` on any `[eval]` issue

Never touches: Python source, workflow YAMLs, `.github/**`, `evals/<date>.json`, `evals/latest.json`, `evals/README.md`, `evals/rubric.md`, `reports/**`, `data/**`.

## Machine-readable list

For agents that want to programmatically validate:

```yaml
# Grader write paths (direct commit to main)
grader:
  write:
    - evals/*.json
    - evals/README.md
    - evals/backlog.md
    - evals/pre-merge/*.json

# Coder write paths (branch, then PR)
coder:
  pr:
    - config/sources.yaml
    - config/profile.yaml
    - config/routines.yaml
    - config/broken_sources.yaml
    - distill/digest.md
    - distill/brief_spec.md
  direct:
    - evals/backlog.md
```

Both agents assert `git diff --name-only` (or the equivalent PUT-path check) is a subset of their list before pushing or committing.

## Adding a path

Open a PR that touches this file AND [`.github/CODEOWNERS`](../../.github/CODEOWNERS) AND the relevant role contract ([`grader.md`](grader.md) or [`coder.md`](coder.md)) in the same commit. Reviewer confirms all three are consistent.
