"""GitHub trending-repos collector. Surfaces hot AI tooling BEFORE it shows up on arXiv —
the best leading indicator of "a release that matters." Stdlib only.

GitHub has no official trending API, so we use the public Search API as a deterministic
proxy: repos under AI topics, pushed within the window, ranked by stars. We carry
signals.gh_stars so score.py's gh_stars>=50 heuristic fires immediately (no enrich pass
needed) and the digest can print real traction.

Auth is optional: with GITHUB_TOKEN the Search API allows 30 req/min instead of 10, but the
collector works unauthenticated. Config-driven from config/sources.yaml (releases.github_topics).

Run: python -m collectors.github_trending
"""
from __future__ import annotations
import os, sys, urllib.parse, urllib.request, json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, write_items, parse_window  # noqa: E402

API = "https://api.github.com/search/repositories"
WINDOW = os.environ.get("WINDOW", "48h")
MIN_STARS = int(os.environ.get("GH_TRENDING_MIN_STARS", "50"))   # noise floor
PER_TOPIC = int(os.environ.get("GH_TRENDING_PER_TOPIC", "15"))
CONFIG = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"
GH_TOKEN = os.environ.get("GITHUB_TOKEN")

# Sensible default topics if config is missing the key. AI-relevant, high-signal.
DEFAULT_TOPICS = ["llm", "large-language-models", "agents", "rag",
                  "machine-learning", "diffusion-models"]


def load_topics() -> list[str]:
    try:
        import yaml  # in requirements.txt
        cfg = yaml.safe_load(CONFIG.read_text()) or {}
        topics = ((cfg.get("releases", {}) or {}).get("github_topics") or [])
        return [str(t) for t in topics] or DEFAULT_TOPICS
    except Exception as ex:
        print(f"[gh-trending] config read failed ({ex}); using default topics", file=sys.stderr)
        return DEFAULT_TOPICS


def fetch_topic(topic: str, since_date: str) -> list[dict]:
    q = urllib.parse.urlencode({
        "q": f"topic:{topic} pushed:>{since_date} stars:>={MIN_STARS}",
        "sort": "stars", "order": "desc", "per_page": PER_TOPIC,
    })
    headers = {"User-Agent": "ai-radar/0.1", "Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    req = urllib.request.Request(f"{API}?{q}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("items", []) or []


def to_item(repo: dict) -> dict | None:
    full = repo.get("full_name")
    if not full:
        return None
    desc = repo.get("description") or ""
    lang = repo.get("language") or ""
    return make_item(
        id=f"ghrepo:{full}",
        category="releases",
        title=full + (f" — {desc}" if desc else ""),
        url=repo.get("html_url") or f"https://github.com/{full}",
        source="GitHub Trending" + (f" ({lang})" if lang else ""),
        authors=[(repo.get("owner") or {}).get("login")] if repo.get("owner") else [],
        published=repo.get("pushed_at"),
        raw_summary=desc,
        signals={"gh_stars": repo.get("stargazers_count", 0),
                 "gh_forks": repo.get("forks_count", 0)},
    )


def main() -> None:
    # GitHub Search 'pushed' filter is date-granular (YYYY-MM-DD), so floor the window to days.
    since = datetime.now(timezone.utc) - parse_window(WINDOW)
    since_date = since.strftime("%Y-%m-%d")
    items, seen_ids = [], set()
    for topic in load_topics():
        try:
            repos = fetch_topic(topic, since_date)
        except Exception as ex:
            print(f"[gh-trending] fetch failed for topic {topic}: {ex}", file=sys.stderr)
            continue
        for repo in repos:
            it = to_item(repo)
            if it and it["id"] not in seen_ids:
                seen_ids.add(it["id"])
                items.append(it)
    n = write_items("releases", items)
    print(f"[gh-trending] {len(items)} trending repos, {n} new written (window={WINDOW})")


if __name__ == "__main__":
    main()
