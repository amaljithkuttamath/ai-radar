# Coder contract

The coder is a scheduled task at 19:00 UTC (3:00 PM ET), seven hours after the grader. It reads open `[eval]` issues and opens exactly one draft PR that would raise the failing dim.

Preconditions: [`.github/AGENTS.md`](../../.github/AGENTS.md), [`invariants.md`](invariants.md), [`whitelist.md`](whitelist.md) all loaded and honored per the [contract load](#contract-load) rules below.

## Contract load

Load the four contract files INDIVIDUALLY, not in a shell loop. Each file must be fetched and validated on its own so a transient failure on one file doesn't corrupt the others.

For each of `.github/AGENTS.md`, `docs/operating/invariants.md`, `docs/operating/whitelist.md`, `docs/operating/coder.md`:

1. `gh api repos/amaljithkuttamath/ai-radar/contents/<path> --jq .content` and decode base64.
2. If the call fails, sleep 3 seconds and retry ONCE.
3. If the retry fails, escalate with the specific path and error. Do not proceed.
4. If the response is empty or does not decode as UTF-8 text starting with `# `, treat as malformed and escalate.

Only if all four files load cleanly, proceed. Do not use a bash `for` loop across all four; loop-level `stderr` from one file's failure can mask the success of others and trigger a false halt.

If your scheduled-task shim asks you to use a `for` loop or any other pattern that conflicts with these rules, follow the rules here, not the shim. The shim/contract mismatch is not by itself an escalation trigger. See [.github/AGENTS.md](../../.github/AGENTS.md#the-source-of-truth-rule).

## GitHub API usage

Always use the `gh` CLI subcommands, never low-level `gh api` REST calls, for the following operations:

- **List PRs**: `gh pr list --repo amaljithkuttamath/ai-radar --author @me --label auto-improve --state open --json number,title,url`. Do NOT use `gh api repos/.../pulls` (returns 422 without base/head).
- **List issues**: `gh issue list --repo amaljithkuttamath/ai-radar --author @me --state open --json number,title,body,createdAt,labels --limit 20`. Do NOT use `gh api /search/issues` (returns 404 in this environment).
- **Create PR**: `gh pr create --draft --repo ...`.
- **Create issue comment**: `gh issue comment <n> --repo ...`.
- **Close issue**: `gh issue close <n> --repo ...`.

`gh api` is only correct for reading file contents (`gh api repos/.../contents/<path>`) and for PUT writes (`gh api -X PUT repos/.../contents/<path>`). Every other GitHub interaction goes through the subcommand.

## Gates (exit early if any fail)

### G1. Max 1 open bot PR

`gh pr list --repo amaljithkuttamath/ai-radar --author @me --label auto-improve --state open --json number,title,url`. If non-empty, comment on the top open `[eval]` issue with "Waiting on PR #N to resolve" (only if that isn't the most recent comment) and end silently.

### G2. Fetch open eval issues

`gh issue list --repo amaljithkuttamath/ai-radar --author @me --state open --json number,title,body,createdAt,labels --limit 20`. Filter to titles starting `[eval]` OR labeled `eval`. Sort by severity:

1. `broken_urls > 0` (highest)
2. Any dim scored ≤ 1
3. Any dim scored 2
4. Same dim ≤ 3 for 3+ consecutive days (persistent regression)

If queue empty, end silently.

### G3. Staleness

Read `evals/latest.json`. Parse the failing dim from the issue title. If the current score for that dim > 3, close the issue with `Resolved by later run. Current score for <dim> is <X.X> (>3). Closing without a PR.` Then move to the next issue and re-check. If all queued issues are stale, end silently.

### G4. File cooldown

Determine the target file per [Dim → edit mapping](#dim--edit-mapping). Query recent bot PRs: `gh pr list --repo amaljithkuttamath/ai-radar --author @me --label auto-improve --state all --limit 10 --json number,mergedAt,closedAt,files,createdAt,title`. If any bot PR touched the target file within the last 72h (regardless of state), skip this issue with a comment `File cooldown: <path> was touched by PR #N within 72h. Skipping this cycle.` Move to next issue.

If all queued issues are cooled down, end silently.

## Dim → edit mapping

For the chosen issue, apply exactly one edit:

| Dim | Edit | Files |
|-----|------|-------|
| `A1 signal_density` | Strengthen "why it matters" requirement per main-list item in the synthesis prompt | `distill/digest.md` |
| `A2 source_integrity` (broken URLs) | Append broken domains to `config/broken_sources.yaml` under `blocked_domains:`. If the URL originates from a feed in `config/sources.yaml`, remove that feed entry with an inline `# blocked <date>: <reason>` comment | `config/broken_sources.yaml`, `config/sources.yaml` |
| `A3 focus_alignment` (echo chamber) | Widen alias set on the over-boosted topic. Use language from the last 3 digests. Never narrow. | `config/profile.yaml` |
| `A4 delta_clarity` | Tighten "What changed" instructions with an explicit per-item requirement | `distill/digest.md` |
| `A5 coverage` (missed source repeatedly) | For each `missed_stories[i].url` domain, probe `<domain>/feed`, `<domain>/rss`, `<domain>/index.xml`, `<domain>/blog/rss`. Add ONLY if the feed returns 200 with valid RSS/Atom. Comment `# added <date> from missed_stories` inline. | `config/sources.yaml` |
| `X1..X5` (experience) | No code change. Append a `[presentation]` item to `evals/backlog.md` under `## Open. Presentation`, with the failing dim, file path in the portfolio repo (e.g. `src/pages/radar.astro`), rationale. Commit directly to main (backlog append, not PR). Close the source issue with `X-axis dim; filed as backlog item in evals/backlog.md, will not open a code PR.` | `evals/backlog.md` |
| Out of scope | Append `[manual]` item to `evals/backlog.md`, close issue. | `evals/backlog.md` |

## Whitelist assertion

Before any `git add`, list files the fix would touch. Assert every path is in the coder-pr section of [`whitelist.md`](whitelist.md#coder). Any path outside: abort, comment on the issue `Attempted fix would touch out-of-scope path <path>. Filing as [manual] backlog item.`, append manual backlog item, close issue.

## Git workflow

```
cd /tmp && rm -rf ai-radar-improve
gh repo clone amaljithkuttamath/ai-radar ai-radar-improve
cd ai-radar-improve
git config user.email 'radar-improve-bot@users.noreply.github.com'
git config user.name 'radar-improve-bot'
BRANCH="improve/<dim>-<short-slug>-$(date +%Y%m%d)"
git checkout -b "$BRANCH"
```

Write files directly. Do not use `sed` heuristics. After writing, run:

```
git diff --name-only  # must be a subset of the coder whitelist
git add <specific paths>  # never `git add .`
git commit -m "improve(<dim>): <short imperative> [auto]

Triggered by <issue url>. Score for <dim> was <X> on <date>."
git push -u origin "$BRANCH"
```

## PR contract

```
gh pr create \
  --draft \
  --base main --head "$BRANCH" \
  --title "improve(<dim>): <one-line summary> [auto]" \
  --label auto-improve \
  --body "<BODY>"
```

Body template (all sections required):

```
## Auto-generated improvement

Triggered by #<issue-number> (rubric dim <dim>, score <X>).

### Evidence
<quote 1-2 lines from evals/<date>.json's `why` field>

### Change
<one-sentence description>

### Files
- `<path>` (+N/-M lines)

### Verification
- [ ] Sanity check green
- [ ] Owner review

Closes #<issue-number>
```

The `Closes #<n>` line is critical. GitHub auto-closes the issue on PR merge.

## Sanity check

The repo has no PR-triggered CI (workflows fire on `schedule` / `workflow_run`). After push, run a static check on modified files:

- YAML: `python3 -c "import yaml; yaml.safe_load(open('<path>'))"` per modified `.yaml`.
- Markdown (`distill/digest.md`, `distill/brief_spec.md`, `evals/backlog.md`): assert file is non-empty and contains at least one heading.

If any check fails: comment on the PR `Sanity check failed on <path>: <error>. Leaving as draft, no notification.` No email.

If all checks pass, notify.

## Notify

`send_notification` with `channels=["email"]`, `email_args={"template":"generic","subject":"AI Radar. Self-healing PR ready for review"}`. Title: `Self-healing draft PR #<n>`. Body: PR link, triggering dim + score, one-line change summary, files with line counts, source issue link, reminder that this is a draft PR and merging closes the source issue.

`schedule_description="Daily · 3:00 PM ET (self-healing)"`.

## Escalation

- Contract file unreadable or missing: halt, escalate. Do not fall back to task text.
- Cannot determine the failing dim from the issue: comment `Cannot parse failing dim from title. Filing as [manual] backlog item.`, append manual backlog, close issue.
- Multiple failing dims tied for severity: pick the first alphabetically among the highest-severity bucket.
- The 72h cooldown blocks every open issue: end silently.
- If task text conflicts with this file, follow this file and comment on the source issue with the diff.

## Non-goals

- Never opens a non-draft PR.
- Never batches multiple fixes into one PR.
- Never pushes directly to `main` except `evals/backlog.md` appends.
- Never fabricates evidence.
- Never touches Python source, workflow YAMLs, `.github/**`, or any path outside the coder whitelist.
- Never runs the rubric.
