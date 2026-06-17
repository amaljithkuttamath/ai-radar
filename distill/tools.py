"""Deterministic enrichment fetchers — NO model, no framework. Each function takes plain
values and returns a plain dict (or None on miss/error). Stdlib only, graceful degradation:
any failure returns None and logs to stderr, never aborts the run.

These are the "tools" the enrich stage uses. They are unconditional lookups (every top item
wants its GitHub stars + HN points), so there is nothing for a model to decide — hence plain
Python, not an agent loop.
"""
from __future__ import annotations
import os, sys, re, json, urllib.parse, urllib.request

UA = {"User-Agent": "ai-radar/0.1"}

# github.com/{owner}/{repo} — but skip non-repo paths (gists, org pages, settings, etc.).
_REPO_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
_NON_REPO_OWNERS = {"orgs", "settings", "about", "features", "sponsors", "marketplace",
                    "topics", "collections", "apps", "login", "join", "notifications"}


def _get_json(url: str, headers: dict | None = None, timeout: int = 20):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def extract_github_repos(text: str) -> list[tuple[str, str]]:
    """Pull (owner, repo) pairs from any github.com URLs in the text. Dedups, filters
    known non-repo paths, and strips a trailing '.git' or punctuation from the repo name."""
    out, seen = [], set()
    for owner, repo in _REPO_RE.findall(text or ""):
        owner_l = owner.lower()
        if owner_l in _NON_REPO_OWNERS:
            continue
        repo = re.sub(r"\.git$", "", repo).rstrip(".,);]")
        key = (owner_l, repo.lower())
        if repo and key not in seen:
            seen.add(key)
            out.append((owner, repo))
    return out


def fetch_github_repo(owner: str, repo: str, token: str | None = None) -> dict | None:
    """api.github.com/repos/{owner}/{repo}. Authenticated runs at 5000 req/hr (non-binding).
    Returns stars/forks/description/language/pushed_at, or None on 404/error."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        d = _get_json(f"https://api.github.com/repos/{owner}/{repo}", headers)
    except Exception as ex:
        print(f"[tools] github repo {owner}/{repo} failed: {ex}", file=sys.stderr)
        return None
    return {
        "owner": owner, "repo": repo,
        "stars": d.get("stargazers_count", 0),
        "forks": d.get("forks_count", 0),
        "description": d.get("description") or "",
        "language": d.get("language") or "",
        "pushed_at": d.get("pushed_at"),
    }


def fetch_hn_signal(title: str) -> dict | None:
    """HN Algolia search (free, unauthed) for the paper title. Returns the top story's
    points/comments/url, or None if there's no real hit. Title search is fuzzy, so we only
    trust a result that actually has points (a 0-point match is noise)."""
    if not title:
        return None
    q = urllib.parse.urlencode({"query": title, "tags": "story", "hitsPerPage": 3})
    try:
        d = _get_json(f"https://hn.algolia.com/api/v1/search?{q}")
    except Exception as ex:
        print(f"[tools] hn search failed: {ex}", file=sys.stderr)
        return None
    hits = d.get("hits") or []
    if not hits:
        return None
    top = hits[0]
    points = top.get("points") or 0
    if points <= 0:
        return None
    obj_id = top.get("objectID")
    return {
        "points": points,
        "num_comments": top.get("num_comments") or 0,
        "objectID": obj_id,
        "url": f"https://news.ycombinator.com/item?id={obj_id}" if obj_id else None,
    }


def best_repo(item: dict, token: str | None = None) -> dict | None:
    """Convenience: find the first resolvable GitHub repo referenced by an item and return
    its stats. Checks the collector-captured links.github first (e.g. HF's githubRepo, which
    is rarely in the abstract text), then falls back to scanning url + raw_summary."""
    candidates = " ".join([
        (item.get("links", {}) or {}).get("github", ""),
        item.get("url", ""),
        item.get("raw_summary", ""),
    ])
    for owner, repo in extract_github_repos(candidates):
        info = fetch_github_repo(owner, repo, token)
        if info:
            return info
    return None
