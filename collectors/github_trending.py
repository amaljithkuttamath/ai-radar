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
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, write_items, parse_window, CONFIG as CONFIG_DIR
from radar.collection import SourceBatch
from radar.http import fetch_json  # noqa: E402

API = "https://api.github.com/search/repositories"
WINDOW = os.environ.get("WINDOW", "48h")
MIN_STARS = int(os.environ.get("GH_TRENDING_MIN_STARS", "50"))  # noise floor
PER_TOPIC = int(os.environ.get("GH_TRENDING_PER_TOPIC", "15"))
CONFIG = CONFIG_DIR / "sources.yaml"
GH_TOKEN = os.environ.get("GITHUB_TOKEN")

# Sensible default topics if config is missing the key. AI-relevant, high-signal.
DEFAULT_TOPICS = ["llm", "large-language-models", "agents", "rag", "machine-learning", "diffusion-models"]


def load_topics() -> list[str]:
    import yaml

    cfg = yaml.safe_load(CONFIG.read_text())
    topics = cfg.get("releases", {}).get("github_topics", DEFAULT_TOPICS)
    if not isinstance(topics, list) or any(not isinstance(t, str) or not t for t in topics):
        raise ValueError("github_topics must be a list of nonempty strings")
    return topics


def fetch_topic(topic: str, since_date: str) -> list[dict]:
    q = urllib.parse.urlencode(
        {
            "q": f"topic:{topic} pushed:>{since_date} stars:>={MIN_STARS}",
            "sort": "stars",
            "order": "desc",
            "per_page": PER_TOPIC,
        }
    )
    headers = {"User-Agent": "ai-radar/0.1", "Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    req = urllib.request.Request(f"{API}?{q}", headers=headers)
    data = fetch_json(req)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("GitHub response must contain an items list")
    return data["items"]


def to_item(repo: dict) -> dict | None:
    full = repo.get("full_name")
    if not full:
        return None
    desc = repo.get("description") or ""
    return make_item(
        id=f"ghrepo:{full}",
        category="releases",
        title=full + (f" — {desc}" if desc else ""),
        url=repo.get("html_url") or f"https://github.com/{full}",
        source="GitHub Search",
        authors=[(repo.get("owner") or {}).get("login")] if repo.get("owner") else [],
        published=repo.get("pushed_at"),
        raw_summary=desc,
        signals={"gh_stars": repo.get("stargazers_count", 0), "gh_forks": repo.get("forks_count", 0)},
    )


def main() -> dict:
    since = datetime.now(timezone.utc) - parse_window(WINDOW)
    batch = SourceBatch("github_trending")
    items = {}

    def fetch_items(topic):
        for repo in fetch_topic(topic, since.strftime("%Y-%m-%d")):
            item = to_item(repo)
            if item:
                yield item

    for topic in load_topics():
        for item in batch.fetch(topic, fetch_items, topic):
            items.setdefault(item["id"], item)
    written = write_items("releases", list(items.values()))
    print(f"[github_trending] {written} observations written")
    return batch.finish(written)


if __name__ == "__main__":
    main()
