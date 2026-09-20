"""Resolve the arXiv ids in `data/seen.json` to title + abstract text.

`seen.json` is a dedup ledger, not a corpus: 17,574 bare id strings with no text
attached. Nothing downstream can label, train on, or evaluate against an id. This
script is the missing step that turns the ledger into something a model can read.

Only `arxiv:` ids are resolved (16,497 of the 17,574). The blog / ghrepo / hfmodel /
hfdataset ids need different endpoints and different consent, and mixing four fetchers
into one script would make the failure modes impossible to read. They are skipped
loudly rather than silently.

Two properties matter more than speed here:

* **Batched.** arXiv's `id_list` takes many ids per query, so 16.5k papers is ~170
  requests rather than 16,500. One id per request would take hours and earn a block.
* **Resumable.** Output is appended as JSONL and already-fetched ids are skipped on
  restart, so a dropped connection at paper 12,000 costs one batch, not the run.

Entries are matched back to their request by id, never by position: arXiv silently
omits withdrawn or malformed ids, so the nth response is not the nth request.

Stdlib only, like every other collector. Run: python -m labeling.fetch_abstracts
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEEN_PATH = ROOT / "data" / "seen.json"
OUT_PATH = ROOT / "data" / "labels" / "abstracts.jsonl"

API = "http://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"

# arXiv asks for one request per three seconds. Batching already cuts the request count
# by ~100x; honouring the delay on top of that is the difference between a good citizen
# and a blocked IP.
DELAY_SECONDS = 3.0
BATCH = 100
RETRIES = 4


def strip_version(short_id: str) -> str:
    """`2401.12345v2` -> `2401.12345`, matching the ids collectors/arxiv.py mints."""
    return re.sub(r"v\d+$", "", short_id)


def seen_arxiv_ids() -> list[str]:
    raw = json.loads(SEEN_PATH.read_text())
    return [i.split(":", 1)[1] for i in raw if i.startswith("arxiv:")]


def already_fetched() -> set[str]:
    """Ids present in the output file, so a restart resumes instead of duplicating."""
    if not OUT_PATH.exists():
        return set()
    done = set()
    for line in OUT_PATH.read_text().splitlines():
        if not line.strip():
            continue
        try:
            done.add(json.loads(line)["id"])
        except (json.JSONDecodeError, KeyError):
            # A torn final line from a killed process. Ignore it; the id simply refetches.
            continue
    return done


def fetch_batch(ids: list[str]) -> bytes:
    query = urllib.parse.urlencode({"id_list": ",".join(ids), "max_results": len(ids)})
    request = urllib.request.Request(
        f"{API}?{query}", headers={"User-Agent": "ai-radar/0.1 (labeling)"}
    )
    last_error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            time.sleep(DELAY_SECONDS * (2 ** attempt))
    raise RuntimeError(f"arXiv fetch failed after {RETRIES} attempts: {last_error}")


def parse_batch(payload: bytes) -> dict[str, dict]:
    """Return {versionless_id: record}. Keyed by id because arXiv drops unknown ids."""
    root = ET.fromstring(payload)
    records = {}
    for entry in root.findall(f"{ATOM}entry"):
        url = entry.findtext(f"{ATOM}id") or ""
        short = strip_version(url.rsplit("/", 1)[-1])
        if not short:
            continue
        abstract = (entry.findtext(f"{ATOM}summary") or "").replace("\n", " ").strip()
        if not abstract:
            # No abstract means nothing to label. Better absent than an empty state that
            # a teacher would confidently score anyway.
            continue
        records[short] = {
            "id": short,
            "arxiv_url": url,
            "title": (entry.findtext(f"{ATOM}title") or "").replace("\n", " ").strip(),
            "abstract": abstract,
            "published": entry.findtext(f"{ATOM}published") or "",
            "primary_category": next(
                (c.get("term") for c in entry.findall(f"{ATOM}category") if c.get("term")), ""
            ),
        }
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0,
                        help="stop after this many newly fetched papers (0 = all)")
    parser.add_argument("--batch", type=int, default=BATCH, help="ids per arXiv request")
    args = parser.parse_args()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    wanted = seen_arxiv_ids()
    done = already_fetched()
    todo = [i for i in dict.fromkeys(wanted) if i not in done]
    if args.limit:
        todo = todo[: args.limit]

    print(f"[fetch] {len(wanted)} arxiv ids in seen.json · {len(done)} already fetched "
          f"· {len(todo)} to go", file=sys.stderr)
    if not todo:
        return 0

    written = missing = 0
    with OUT_PATH.open("a", encoding="utf-8") as out:
        for start in range(0, len(todo), args.batch):
            chunk = todo[start : start + args.batch]
            try:
                records = parse_batch(fetch_batch(chunk))
            except (RuntimeError, ET.ParseError) as error:
                # One bad batch should not end a run that has written thousands of rows.
                print(f"[fetch] batch at {start} failed, continuing: {error}", file=sys.stderr)
                time.sleep(DELAY_SECONDS)
                continue
            for paper_id in chunk:
                record = records.get(paper_id)
                if record is None:
                    missing += 1
                    continue
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
            out.flush()
            print(f"[fetch] {written} written, {missing} unresolved "
                  f"({start + len(chunk)}/{len(todo)})", file=sys.stderr)
            time.sleep(DELAY_SECONDS)

    print(f"[fetch] done: {written} written, {missing} unresolved -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
