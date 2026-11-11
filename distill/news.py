"""News ranking: importance x freshness x relevance. Stdlib only.

The integer score (score.py) answers "is there evidence this item is real and usable?".
It is a routing gate, and it is deliberately blind to time. Used as the *ordering* key it
made the front page stale: an evergreen repository clears both lifetime-traction checks
every day, so it led edition after edition, while a frontier lab's own announcement (no
stars, no upvotes) sat in the watch-list.

This module supplies the ordering key a reader expects from a news page, borrowed from how
news aggregators rank:

  importance  the integer score, plus momentum (traction gained over the recent history,
              not lifetime totals), plus a boost for a frontier lab's own announcement.
  freshness   decays with the item's age, using the Hacker News
              "gravity" shape: ((0 + 2) / (age + 2)) ** 1.8. Day 0 = 1.0, day 1 ~ 0.48,
              day 3 ~ 0.19, day 7 ~ 0.07. Old items sink without being deleted.
              Age is the older of two clocks: days since the radar first saw the item,
              and days since the thing itself was created (a repository or model). A
              four-year-old repository that starts trending is new to the radar but
              not news, and must not lead the page.
  relevance   a modest multiplier for profile focus matches.

It never changes `score`, so routing (main list vs watch-list), the grader, and every
trusted metric are untouched. It only adds annotations and an ordering key.
"""

from __future__ import annotations

import re
from datetime import date

from distill.rank import magnitude

GRAVITY = 1.8
# Momentum: magnitude gained across the recent history. magnitude() is log-scaled, so +1.0
# is roughly a 2.7x jump in traction; cap it so one viral repo cannot outrank everything.
MOMENTUM_CAP = 2.0
LAB_RELEASE_BOOST = 1.5
FOCUS_MULTIPLIER = 1.25
# An item first seen this many days ago or more is "seen before": it belongs under
# Still developing unless its momentum earns it a main-list slot.
SEEN_BEFORE_DAYS = 2

FRONTIER_LABS = (
    "anthropic",
    "openai",
    "deepmind",
    "google",
    "meta",
    "microsoft",
    "deepseek",
    "qwen",
    "alibaba",
    "mistral",
    "nvidia",
    "amd",
    "apple",
    "amazon",
    "xai",
    "cohere",
)


def _parse_day(value: str | None) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def age_days(first_seen: str | None, today: date) -> int:
    """Whole days since the radar first saw the item; 0 when unknown (treated as new)."""
    seen = _parse_day(first_seen)
    if seen is None:
        return 0
    return max(0, (today - seen).days)


def freshness(age: int) -> float:
    return (2.0 / (age + 2.0)) ** GRAVITY


def momentum(item: dict, history: list[float] | None) -> float:
    """Traction gained since the oldest point in the rolling history, clamped to [0, cap].
    No history means no evidence of movement, so 0, never a guess."""
    if not history:
        return 0.0
    gained = magnitude(item) - float(history[0])
    return max(0.0, min(MOMENTUM_CAP, gained))


def is_lab_release(item: dict) -> bool:
    """A frontier lab's own announcement: a blog/newsroom post whose source names the lab.
    Papers that merely list a lab among authors do not count; they are scored on evidence."""
    if not str(item.get("id", "")).startswith("blog:"):
        return False
    source = str(item.get("source", "")).lower()
    return any(re.search(rf"\b{re.escape(lab)}\b", source) for lab in FRONTIER_LABS)


def annotate(
    items: list[dict],
    state: dict[str, dict] | None,
    today: date,
    shown: dict[str, date] | None = None,
) -> list[dict]:
    """Add first_seen, days_on_radar, new_to_radar, seen_before, momentum and news_rank to
    each item in place. Returns items.

    `state` is the previous run's snapshot (data/state.json). It only holds the last run's
    items, so an item that skipped a day would look new again. `shown` closes that gap: URL
    -> the first published digest that linked it (distill/frontpage.first_seen). The
    earliest of the two wins, because "new" means new to the reader."""
    state = state or {}
    shown = shown or {}
    for item in items:
        prev = state.get(item.get("id")) or {}
        dates = [d for d in (item.get("first_seen"), prev.get("first_seen")) if _parse_day(d)]
        if item.get("url") in shown:
            dates.append(shown[item["url"]].isoformat())
        first_seen = min(dates, key=lambda d: _parse_day(d)) if dates else None
        radar_age = age_days(first_seen, today)
        age = max(radar_age, age_days(item.get("created"), today))
        gained = momentum(item, prev.get("mag_history"))
        importance = float(item.get("score") or 0) + gained
        if is_lab_release(item):
            importance += LAB_RELEASE_BOOST
        relevance = FOCUS_MULTIPLIER if item.get("focus_match") else 1.0
        item["first_seen"] = first_seen or today.isoformat()
        item["days_on_radar"] = radar_age + 1
        item["new_to_radar"] = not prev and not item.get("carryover") and item.get("url") not in shown
        item["seen_before"] = radar_age >= SEEN_BEFORE_DAYS
        item["project_age_days"] = age_days(item.get("created"), today) if item.get("created") else None
        item["momentum"] = round(gained, 3)
        item["lab_release"] = is_lab_release(item)
        item["news_rank"] = round(importance * freshness(age) * relevance, 4)
    return items


def news_key(item: dict) -> tuple:
    """Sort key, highest first: news_rank, then score, then id for determinism."""
    return (item.get("news_rank") or 0.0, item.get("score") or 0, item.get("id", ""))
