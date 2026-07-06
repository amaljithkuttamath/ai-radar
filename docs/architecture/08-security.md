# 08. Security

## Threat model (STRIDE)

The pipeline is a small public system with one human writer and one bot writer per critical path. STRIDE keeps the analysis honest.

| Threat | Category | Vector | Mitigation |
|--------|----------|--------|------------|
| Malicious content in RSS/HTML | Tampering | A source injects prompt-injection payloads into `title` or `raw_summary` | Content is rendered as Markdown, never as HTML. Never interpolated into shell commands. Model prompt (`digest.md`) treats items as data, not instructions. |
| Poisoned model output writes shell to digest | Injection | Model emits `![alt](javascript:...)` or similar | Digest is Markdown only; the site renders with a Markdown pipeline that strips `javascript:` URLs. |
| Broken or hostile URL in Main list | Repudiation | Digest links to a domain that later hosts phishing | Grader HEAD-checks URLs at eval time. Site does not preload link targets; user-initiated clicks only. |
| Grader token leaked | Info disclosure | Token exfiltrated via logs or task history | Token stored as a Perplexity task credential; never printed. `contents: write` + `issues: write` scope only. Rotation runbook in [06-deployment.md](06-deployment.md). |
| Actions workflow escalates its own permissions | Elevation | A PR from a fork adds `permissions: write-all` | Default is `permissions: read-all` at repo level. Workflow-level permissions are pinned. `pull_request` from a fork cannot use secrets by GitHub design. |
| DoS via source spam | Denial of service | An RSS feed emits 10,000 items | `collectors/common.py` caps items per source per run. `seen.json` dedups. Artifact size bounded. |
| Repudiation of bad digest | Repudiation | Owner denies committing a bad digest | Every commit is signed by the bot identity (`radar-bot` for pipeline, `radar-eval-bot` for evals). Human commits are attributed to the owner. Full git history is public. |
| Spoofing the bot identity | Spoofing | Someone pushes as `radar-bot` | Only workflows using `GITHUB_TOKEN` can produce commits attributed to the bot. Branch protection on `main` requires status checks + no direct pushes by humans other than the owner. |

## Attack surface

**Ingress.**
- Collector HTTP GETs to public sources. No credentials sent.
- `gh api` calls from the grader (authenticated).
- `workflow_dispatch` inputs (`window`, `focus`, `backend`, `radar_agent`, `deliver_email`, `focus_backend`). Values are used in env vars; each is validated by the downstream script.

**Egress.**
- Repo commits.
- One model call per distill run.
- Optional SMTP to configured provider.
- Grader posts issues.

**Not an attack surface.**
- Reader traffic to the site is one-way; the site does not accept user input.
- `data/raw/` is gitignored; the artifact is 3-day retention and not public without a GitHub token.

## Defenses

**Input validation.**
- URL parsing uses `urllib.parse`. Non-`https?://` URLs are dropped at collector level.
- `id` prefix is checked against the reserved list; unknown prefixes are dropped.
- HTML from lab blogs is parsed with `feedparser`; freeform HTML never reaches the model.

**Output validation.**
- Digest is Markdown. The site's Markdown pipeline sanitises rendered HTML.
- Grader HEAD-checks every URL in the Main list before scoring `A2`. Broken URLs cap the score at 2 and file an issue.

**Auth boundaries.**
- Workflows use `GITHUB_TOKEN` with least-privilege permissions.
- Grader uses a PAT scoped to `contents: write` + `issues: write` on the two known repos.
- Branch protection on `main` requires PRs for human changes.

**Reproducibility as defense.**
- The corpus is regenerable. A poisoned commit can be reverted; the next collect run rebuilds cleanly from public sources.
- The digest is a pure function of corpus + config + model output. Corpus and config are auditable. Model output is the only non-deterministic input.

## Out of scope

Explicit "we don't do this and here's why."

- **User accounts.** No login, no user data, no sessions. Nothing to breach.
- **Encryption at rest.** All content is public. No encryption needed.
- **DDoS protection at the pipeline layer.** GitHub Actions and GitHub raw-content handle this at their layer.
- **SBOM / supply-chain attestation.** Dependency footprint is `pyyaml`, `feedparser`, and stdlib. If this became a wider system, we'd add `pip-audit` in CI.
- **Multi-tenancy.** One user (owner), one project. Nothing to isolate.

## Incident response

**A malicious digest ships.** Revert commit, file post-mortem as an ADR under `adr/`. Update `digest.md` prompt or `score.py` heuristic if the root cause is model behaviour on a specific input class.

**A grader token leaks.** Rotate immediately per [06-deployment.md](06-deployment.md). Audit `evals/**` history for unauthorized writes.

**A workflow is modified without a PR.** Only possible with owner credentials. If seen, rotate GitHub credentials and audit repo settings for added collaborators.
