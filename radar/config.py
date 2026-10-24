"""Validated runtime settings. CLI overrides environment, then routines.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

BACKENDS = ("dryrun", "template", "auto", "openai", "github", "anthropic", "ollama")
COLLECTORS = ("hf_papers", "arxiv", "lab_blogs", "github_trending", "hf_trending")


def mapping(path: Path) -> dict:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a mapping")
    return value


def positive_int(value, name: str, maximum: int = 10000) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer")
    try:
        result = int(str(value))
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if not 1 <= result <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return result


def boolean(value, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if str(value).lower() in {"on", "true", "1"}:
        return True
    if str(value).lower() in {"off", "false", "0"}:
        return False
    raise ValueError(f"{name} must be on or off")


@dataclass(frozen=True)
class Settings:
    window: str
    backend: str
    max_items: int
    threshold: int
    collectors: tuple[str, ...]
    enrich: bool

    @classmethod
    def load(cls, overrides: dict | None = None):
        from collectors.common import CONFIG, parse_window

        config = mapping(CONFIG / "routines.yaml")
        distill = config.get("distill", {})
        agent = config.get("agent", {})
        if not isinstance(distill, dict) or not isinstance(agent, dict):
            raise ValueError("distill and agent settings must be mappings")
        overrides = overrides or {}

        def pick(key, env, default):
            if overrides.get(key) is not None:
                return overrides[key]
            return os.environ.get(env, distill.get(key, default))

        window = str(pick("window", "WINDOW", "48h"))
        duration = parse_window(window)
        if duration.total_seconds() > 31 * 86400:
            raise ValueError("window must be at most 31 days")
        backend = str(pick("backend", "RADAR_MODEL_BACKEND", "dryrun"))
        if backend not in BACKENDS:
            raise ValueError(f"unknown backend {backend!r}; choose {', '.join(BACKENDS)}")
        collectors = config.get("collectors", list(COLLECTORS))
        if not isinstance(collectors, list) or not collectors or any(c not in COLLECTORS for c in collectors):
            raise ValueError("collectors must be a nonempty list of supported collector names")
        if len(collectors) != len(set(collectors)):
            raise ValueError("duplicate collectors in routines.yaml")
        # Keep cross-source precedence stable, independent of YAML ordering.
        collectors = tuple(c for c in COLLECTORS if c in collectors)
        settings = cls(
            window,
            backend,
            positive_int(pick("max_items", "MAX_ITEMS", 10), "max_items", 100),
            positive_int(pick("include_threshold", "INCLUDE_THRESHOLD", 2), "include_threshold", 5),
            collectors,
            boolean(os.environ.get("RADAR_AGENT", agent.get("enabled", False)), "RADAR_AGENT"),
        )
        market = boolean(pick("market", "MARKET", False), "MARKET")
        os.environ.update(
            WINDOW=window,
            RADAR_MODEL_BACKEND=backend,
            MAX_ITEMS=str(settings.max_items),
            INCLUDE_THRESHOLD=str(settings.threshold),
            MARKET="on" if market else "off",
            RADAR_AGENT="on" if settings.enrich else "off",
        )
        if overrides.get("focus") is not None:
            os.environ["FOCUS"] = overrides["focus"]
        elif "FOCUS" not in os.environ and distill.get("focus"):
            focus = distill["focus"]
            if not isinstance(focus, list) or any(not isinstance(v, str) for v in focus):
                raise ValueError("focus must be a list of terms")
            os.environ["FOCUS"] = ",".join(focus)
        for key, variable, default in (
            ("top_n", "RADAR_AGENT_TOP_N", 8),
            ("budget", "RADAR_AGENT_BUDGET", 10),
        ):
            os.environ[variable] = str(
                positive_int(os.environ.get(variable, agent.get(key, default)), key, 100)
            )
        try:
            sleep = float(os.environ.get("RADAR_AGENT_SLEEP", agent.get("sleep_between", 5)))
        except (TypeError, ValueError) as exc:
            raise ValueError("agent sleep_between must be a number from 0 to 60") from exc
        if not 0 <= sleep <= 60:
            raise ValueError("agent sleep_between must be a number from 0 to 60")
        os.environ["RADAR_AGENT_SLEEP"] = str(sleep)
        if backend in {"dryrun", "template"}:
            os.environ.update(FOCUS_BACKEND="lexical", CLUSTER_BACKEND="lexical")
        track = config.get("track", {})
        if not isinstance(track, dict):
            raise ValueError("track settings must be a mapping")
        for key, variable, default in (
            ("ttl_days", "TRACK_TTL_DAYS", 14),
            ("max_tracked", "TRACK_MAX", 60),
            ("min_score", "TRACK_MIN_SCORE", 3),
            ("max_misses", "TRACK_MAX_MISSES", 3),
            ("max_flat_runs", "TRACK_MAX_FLAT_RUNS", 5),
            ("refresh_budget", "TRACK_REFRESH_BUDGET", 60),
            ("carryover_slots", "CARRYOVER_SLOTS", 4),
            ("quiet_floor", "QUIET_FLOOR", 6),
        ):
            os.environ[variable] = str(positive_int(os.environ.get(variable, track.get(key, default)), key))
        validate_sources(CONFIG)
        return settings

    def check_credentials(self):
        variable = {"anthropic": "ANTHROPIC_API_KEY"}.get(self.backend)
        if variable and not os.environ.get(variable):
            raise ValueError(f"{variable} is required for backend={self.backend}")


def validate_sources(directory: Path) -> None:
    from collectors.common import valid_url

    sources = mapping(directory / "sources.yaml")
    for section in ("research", "hardware", "releases"):
        if not isinstance(sources.get(section, {}), dict):
            raise ValueError(f"sources.{section} must be a mapping")
    for category in ("hardware", "releases"):
        feeds = sources.get(category, {}).get("rss", [])
        if not isinstance(feeds, list):
            raise ValueError(f"{category}.rss must be a list")
        for feed in feeds:
            if not isinstance(feed, dict) or not feed.get("name") or not valid_url(feed.get("url")):
                raise ValueError(f"{category}.rss needs a name and HTTP(S) URL for every feed")
    for section, key in (("research", "arxiv_categories"), ("releases", "github_topics")):
        values = sources.get(section, {}).get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError(f"{section}.{key} must be a list of nonempty strings")
    profile = mapping(directory / "profile.yaml")
    if not isinstance(profile.get("topics", []), list) or not isinstance(profile.get("mute", []), list):
        raise ValueError("profile topics and mute must be lists")
    for topic in profile.get("topics", []):
        if isinstance(topic, str):
            continue
        if not isinstance(topic, dict) or not isinstance(topic.get("name"), str):
            raise ValueError("each profile topic needs a name")
        aliases = topic.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
            raise ValueError("topic aliases must be a list of strings")
    if any(not isinstance(term, str) for term in profile.get("mute", [])):
        raise ValueError("muted topics must be strings")
