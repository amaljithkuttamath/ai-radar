"""URL extraction and liveness checking for `A2 source_integrity`.

`A2` is the one quality dimension with a hard, checkable floor: the rubric caps it at 2 if
any URL in the digest 404s. That cap must be applied by code, not by asking a model whether
the links looked fine — a judge cannot observe an HTTP status, and if asked it will
confabulate one. Everything here runs before the model sees anything.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Markdown inline links only. Bare URLs in prose are deliberately not checked: the rubric
# scores whether *claims* are sourced, and an unlinked URL is not a claim's source.
_MD_LINK = re.compile(r"\[[^\]]*\]\((https?://[^\s)]+)\)")

# The nav block links to sibling digests by relative path, never absolute, so it does not
# match the pattern above and needs no special-casing.

TIMEOUT = 15
MAX_PARALLEL = 8

# Hosts that answer HEAD with a non-2xx while serving GET fine. arxiv.org in particular
# returns 403 to HEAD from datacentre IPs, which would cap A2 at 2 on almost every digest
# — a false negative that looks exactly like a real integrity failure.
_HEAD_HOSTILE = ("arxiv.org", "huggingface.co")

# Statuses that actually mean "the thing the digest cited is not there".
#
# This list is short on purpose, and the host table above is why: it was the first attempt
# at the same problem, and it does not generalise — every anti-bot host would need adding,
# forever. Classifying by *status* does generalise, because the question A2 asks is not
# "did we get a 2xx" but "did the digest cite something that does not exist".
#
#   404 / 410  the resource is gone. Unambiguous, and the digest's fault.
#   451        removed for legal reasons; the link no longer serves the content.
#
# Everything else non-2xx is the server declining to answer, not an answer:
#
#   401 / 403  "we will not tell you" — anti-bot rules, datacentre IP blocks, an egress
#              proxy refusing CONNECT. A 403 from a blocking proxy and a 403 from an
#              origin are byte-identical, and neither is evidence the page is gone.
#   405        the host dislikes HEAD.
#   429        rate limited.
#   5xx        the origin is having a bad day, which is not the author's doing.
#
# Getting this wrong is expensive in a specific way: a false "broken link" caps A2 at 2,
# files an `[eval]` issue, and puts a fabricated integrity failure into a permanent trend.
DEAD_STATUS = frozenset({404, 410, 451})


def dead(broken: list[dict]) -> list[dict]:
    """The subset of `check()`'s output that is genuinely a dead link."""
    return [b for b in broken if b.get("status") in DEAD_STATUS]


def inconclusive(broken: list[dict]) -> list[dict]:
    """Non-2xx answers that say nothing about whether the link is alive, status 0 included.

    Reported rather than ignored: a run where most links are inconclusive has measured the
    runner's connectivity, not the digest, and a caller that cannot tell those apart will
    read its own network policy as an editorial failure.
    """
    return [b for b in broken if b.get("status") not in DEAD_STATUS]


def extract(body: str) -> list[str]:
    """Ordered, de-duplicated markdown link targets."""
    seen: dict[str, None] = {}
    for url in _MD_LINK.findall(body):
        seen.setdefault(url.rstrip(".,;"), None)
    return list(seen)


def _probe(url: str) -> int:
    """HTTP status for one URL, or 0 if it could not be reached at all.

    GET-with-tiny-range for hosts that dislike HEAD, HEAD otherwise. A network failure
    returns 0 rather than raising: the grader must not fail because one link timed out,
    and 0 is reported distinctly from a real 4xx so a reader can tell "unreachable from
    the runner" from "the page is gone".
    """
    method = "GET" if any(h in url for h in _HEAD_HOSTILE) else "HEAD"
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": "ai-radar-grader (+https://github.com/amaljithkuttamath/ai-radar)",
        # Ask for almost nothing on the GET path so a hostile-to-HEAD host still costs
        # one packet rather than a full page.
        **({"Range": "bytes=0-64"} if method == "GET" else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status
    except urllib.error.HTTPError as ex:
        return ex.code
    except (urllib.error.URLError, OSError, ValueError):
        return 0


def check(urls: list[str]) -> list[dict]:
    """`[{url, status}]` for every URL that did NOT answer 2xx, matching the
    `broken_urls` shape in eval-schema.md. Empty list when everything is live."""
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        statuses = list(pool.map(_probe, urls))
    return [{"url": u, "status": s} for u, s in zip(urls, statuses) if not (200 <= s < 300)]


def a2_ceiling(broken: list[dict]) -> int:
    """The cap the rubric puts on A2. Applied to whatever the judge returns, so a generous
    model cannot score around a dead link.

    Only `DEAD_STATUS` caps. This used to cap on any non-zero status, which meant an
    anti-bot 403, a rate limit or a blocking proxy read as an integrity failure — and on
    2026-09-19 exactly that happened: a run from a sandboxed network recorded two proxy
    403s as broken links and wrote them into the permanent trend. Punishing the digest's
    author for the runner's connectivity puts noise straight into the one quality
    dimension that is supposed to be falsifiable.
    """
    return 2 if dead(broken) else 5
