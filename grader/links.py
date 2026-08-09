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

    Unreachable (status 0) does not cap. It means the runner could not get out — a network
    policy, a proxy, an outage on this machine — and punishing the digest's author for the
    grader's own connectivity would put noise straight into the trend line.
    """
    return 2 if any(b["status"] != 0 for b in broken) else 5
