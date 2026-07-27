"""Shared ranking key. The integer score (0-5) gates routing (main/watch/drop) but is too
coarse to order within a tier — most HF papers tie at 4. This adds a sub-integer tiebreaker
from signal MAGNITUDE (62 upvotes should beat 16; 8911 stars should beat 28), kept strictly
in [0,1) so it never crosses an integer boundary and never changes routing.

Used by both synthesize.load_scored and enrich.load_top_n so the items shown are exactly the
items enriched (no alignment drift). With no signals, tiebreak=0 and rank_key==score, so the
RADAR_AGENT=off path is unchanged.

Also the home of `magnitude()` — the UNSATURATED traction number. rank_key squashes it into
[0,1) so it can never change routing; delta.py and track.py need the raw version, where
doubling traction is a detectable move rather than a rounding error. It lives here because
this module imports nothing local, so both can use it without an import cycle.
"""
from __future__ import annotations
from math import log1p


def magnitude(item: dict) -> float:
    """Unsaturated traction magnitude. log-scaled, so 0->10 and 1000->10000 are comparable,
    but NOT squashed into [0,1) the way rank_key's tiebreak is. Used for movers and for the
    tracked-item traction history."""
    sig = item.get("signals") or {}
    return (log1p(sig.get("hf_upvotes") or 0)
            + 0.7 * log1p(sig.get("hf_likes") or 0)
            + 0.5 * log1p(sig.get("gh_stars") or 0)
            + 0.3 * log1p(sig.get("hn_points") or 0))


def rank_key(item: dict) -> float:
    sig = item.get("signals") or {}
    mag = (log1p(sig.get("hf_upvotes") or 0)
           + 0.7 * log1p(sig.get("hf_likes") or 0)
           + 0.5 * log1p(sig.get("gh_stars") or 0)
           + 0.5 * log1p(sig.get("hn_points") or 0))
    tiebreak = mag / (mag + 10.0)          # [0, inf) -> [0, 1)
    return (item.get("score") or 0) + tiebreak
