"""The trusted set and the Goodhart brake — ADR-0009 §3.

The problem. The coder edits `distill/digest.md`; the grader scores the digest that prompt
writes. That is proxy-reward optimisation, and Gao, Schulman & Hilton (ICML 2023) measured
its shape: past some optimisation pressure the proxy score keeps climbing while ground truth
falls. Their practical result is not "avoid proxies" — you cannot — it is that the divergence
point is unpredictable but the divergence itself is *detectable*, provided you are holding a
signal the optimiser is not optimising.

The rule that defines one, mechanically:

    A metric is TRUSTED iff it is computed solely from code and state
    outside the coder's whitelist.

That rule is checkable, and `check_whitelist.py` checks it (invariant I-10). It also
disqualifies the tempting candidates, correctly. Source diversity and novelty depend on
`config/profile.yaml` and `config/sources.yaml`; the A2 ceiling depends on
`config/broken_sources.yaml`. All three are whitelisted, so all three are legitimate
*targets* of improvement — and a target cannot also be the referee.

What survives is deliberately small. A large trusted set would mean the whitelist was too
narrow to improve anything.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# metric -> the paths its value is derived from. Declared rather than inferred, because
# `check_whitelist.py` has to be able to prove the disjointness without importing this
# package or executing anything.
SOURCES: dict[str, tuple[str, ...]] = {
    # Produced by track.py and the collectors from counters fetched live. No prompt or
    # config edit the coder may make can move it.
    "reobservation_rate": ("distill/track.py", "collectors/"),
    # Settled by observations that had not happened when the prompt ran. The strongest
    # signal available here: no wording change can retroactively make a counter go up.
    "forecast_accuracy": ("grader/forecast.py", "distill/track.py"),
}

TRUSTED = tuple(SOURCES)

# Freshness is trusted under the rule above — it is arithmetic on the clock and git — but it
# is deliberately NOT in the brake. It is constant by construction with respect to the
# planner: no edit can move it in either direction, so it carries no information about
# overoptimisation. It remains a liveness signal (X3, `watchdog.yml`), which is a different
# job. Listing it here would pad the set without strengthening it.
EXCLUDED_CONSTANT = ("age_h",)

# Windows for the brake. Fourteen days is roughly the shortest span over which a daily
# single-sample trend says anything at all; comparing it against the preceding fourteen is
# what makes "rising" and "falling" mean something more than yesterday's noise.
WINDOW_DAYS = 14
# Minimum judged evals in each half. Below this the comparison is two small samples and the
# brake would fire on noise — which, in a system whose response is to revert a change, is
# strictly worse than not firing.
MIN_SAMPLES = 5
# How much a trusted metric must fall before the divergence counts. Same reasoning as
# `forecast.FLAT_BAND`: re-fetch jitter is not a regression.
DEGRADE_BAND = 0.05


def _mean(values: list[float]) -> float | None:
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else None


def reading(tier0: dict, forecast_stats: dict | None = None) -> dict:
    """The trusted values for one eval, pulled from the tier-0 metrics and the forecast
    ledger. Absent metrics are omitted, never zeroed — a metric that could not be computed
    is not a metric that read zero."""
    out = {}
    value = (tier0.get("metrics") or {}).get("reobservation_rate")
    if value is not None:
        out["reobservation_rate"] = value
    value = (forecast_stats or {}).get("forecast_accuracy")
    if value is not None:
        out["forecast_accuracy"] = value
    return out


def _split(history: list[dict], window: int) -> tuple[list[dict], list[dict]]:
    """(recent, prior) — two equal windows, newest first. `history` is newest-first, as
    `artifacts.load_history` returns it."""
    return history[:window], history[window:window * 2]


def divergence(history: list[dict], window: int = WINDOW_DAYS,
               min_samples: int = MIN_SAMPLES,
               band: float = DEGRADE_BAND) -> dict | None:
    """Detect "rubric up, ground truth down" across two windows, or None.

    Returns the finding rather than acting on it: this module measures and
    `scripts/automerge.py` acts, the same reporter/escalator split ADR-0005 draws between
    `health.py` and `watchdog.yml`. A module that both detects overoptimisation and reverts
    for it would be one bug away from reverting on its own noise.

    Only judged evals contribute the rubric side — a deterministic day has no score, and
    treating its absence as a low score would fire the brake every time the model is
    unavailable, which is precisely when nothing has been optimised at all.
    """
    judged = [h for h in history if h.get("mode") != "deterministic" and "overall" in h]
    recent, prior = _split(judged, window)
    if len(recent) < min_samples or len(prior) < min_samples:
        return None

    rubric_now = _mean([h.get("overall") for h in recent])
    rubric_then = _mean([h.get("overall") for h in prior])
    if rubric_now is None or rubric_then is None or rubric_now <= rubric_then:
        return None        # the proxy is not rising; nothing to be suspicious of

    for metric in TRUSTED:
        now = _mean([(h.get("trusted") or {}).get(metric) for h in recent])
        then = _mean([(h.get("trusted") or {}).get(metric) for h in prior])
        if now is None or then is None or then == 0:
            continue
        drop = (then - now) / abs(then)
        if drop > band:
            return {
                "metric": metric,
                "rubric_before": rubric_then, "rubric_after": rubric_now,
                "trusted_before": then, "trusted_after": now,
                "drop": round(drop, 4),
                "detail": (f"rubric rose {rubric_then}→{rubric_now} while {metric} fell "
                           f"{then}→{now} ({drop:.0%}) over {window}d. Goodhart: the proxy "
                           "is improving and the ground truth is not."),
            }
    return None
