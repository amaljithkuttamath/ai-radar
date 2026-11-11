"""Reader frontpage: Yesterday (README block), This week, This month. Stdlib only.

Readers come to the repository to keep up, so its first screen should answer three
questions at three time scales:

  Yesterday   what is new since I last looked?      -> a block inside README.md
  This week   which stories stuck?                  -> reports/week.md
  This month  where is attention moving?            -> reports/month.md

All three are derived deterministically from the published digests in reports/, the same
evidence the personal-site reader uses. No model call, no network, no new state: "first
seen" for a story is the first digest whose main list or still-developing section links
its URL. Each page opens with the same row of links, which renders on GitHub as tabs.

Topic trends are lexical: per edition, how often each topic's terms occur, compared with
the previous period. That is a rough instrument and the pages say so; it is honest about
direction, not precise about size.

Run: python -m distill.frontpage   (reindex.main() also calls it after every digest)
"""

from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import ROOT  # noqa: E402
from radar.storage import atomic_text  # noqa: E402

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})-digest\.md$")
NAV_BLOCK_RE = re.compile(r"<!-- radar:nav -->.*?<!-- /radar:nav -->\n?", re.DOTALL)
README_START = "<!-- frontpage:start -->"
README_END = "<!-- frontpage:end -->"

# `**[Title](url)** · 3/5`, `### [Title](url) · 3/5`, `### 1. [Title](url) · 3/5`, or a bullet.
ITEM_RE = re.compile(
    r"^(?:\*\*|#{3}\s+(?:\d+\.\s+)?|[-*]\s+(?:\*\*)?)\[(?P<title>[^\]]+)\]\((?P<url>[^)\s]+)\)(?:\*\*)?"
    r"(?:\s*·\s*(?P<score>\d)\s*/\s*5)?(?P<rest>.*)$",
    re.MULTILINE,
)

# Topic -> pattern. Plain-language labels because readers see them.
TOPICS: dict[str, str] = {
    "Agents": r"\bagent",
    "Computer-use agents": r"computer[- ]use|GUI agent|browser agent",
    "Coding agents": r"\bcod(?:e|ing) (?:agent|model|assistant)|software engineering|\bSWE\b",
    "Benchmarks and evaluation": r"benchmark|\beval",
    "Robotics": r"\bVLA\b|robot|embodied",
    "Reasoning": r"\breason",
    "Retrieval and RAG": r"\bRAG\b|retriev",
    "Inference cost and speed": r"inference|speculative|quantiz|throughput|latency",
    "Multimodal and vision": r"multimodal|vision|image|video",
    "Open-weight models": r"open[- ]weight|Apache[- ]2|MIT licen",
    "Diffusion models": r"diffusion",
    "AI for science": r"scien|biolog|chemi|molec|protein",
    "Safety and security": r"safety|secur|jailbreak|vulnerab",
    "Long context and memory": r"long[- ]context|\bmemory\b",
}
MIN_RATE = 1.0  # mentions per edition needed before a topic's change is worth reporting


# --------------------------------------------------------------------------- parsing


def _strip_nav(text: str) -> str:
    return NAV_BLOCK_RE.sub("", text, count=1).lstrip("\n")


def _section(text: str, name: str) -> str:
    """Body of `## <name...>` up to the next `## ` heading ('###' stays inside)."""
    m = re.search(rf"^##\s+{name}[^\n]*\n", text, re.MULTILINE | re.IGNORECASE)
    if not m:
        return ""
    end = re.search(r"^##\s", text[m.end() :], re.MULTILINE)
    return text[m.end() : m.end() + end.start()] if end else text[m.end() :]


def _first_sentence(text: str, limit: int = 180) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # keep link text, drop URLs
    text = " ".join(text.replace("**", "").split()).lstrip("—-–· ").strip()
    m = re.match(r"(.+?[.!?])(?:\s|$)", text)
    sentence = m.group(1) if m else text
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rstrip() + "…"


def _items(section: str) -> list[dict]:
    out = []
    matches = list(ITEM_RE.finditer(section))
    for n, m in enumerate(matches):
        nxt = matches[n + 1].start() if n + 1 < len(matches) else len(section)
        blurb = (m.group("rest") or "") + " " + section[m.end() : nxt]
        blurb = re.split(r"\n\s*#{2,3}\s", blurb)[0]
        out.append(
            {
                "title": m.group("title").strip(),
                "url": m.group("url").strip(),
                "score": int(m.group("score")) if m.group("score") else None,
                "blurb": _first_sentence(blurb),
            }
        )
    return out


def opening(text: str) -> str:
    after = re.sub(r"^#\s+.*$", "", _strip_nav(text), count=1, flags=re.MULTILINE).strip()
    for para in re.split(r"\n\s*\n", after):
        line = para.strip()
        if line and not line.startswith(("#", "---", "<!--", ">")):
            return " ".join(line.split())
    return ""


def parse_digest(path: Path) -> dict:
    text = _strip_nav(path.read_text(encoding="utf-8"))
    still = _section(text, "Still developing") or _section(text, "Watch-list / Still developing")
    return {
        "date": date.fromisoformat(DATE_RE.search(path.name).group(1)),
        "path": path,
        "text": text,
        "opening": opening(text),
        "main": _items(_section(text, "Main list")),
        "still": _items(still),
    }


def load_digests(reports: Path) -> list[dict]:
    """Every dated digest, oldest first."""
    files = sorted((p for p in reports.glob("*.md") if DATE_RE.search(p.name)), key=lambda p: p.name)
    return [parse_digest(p) for p in files]


def first_seen(digests: list[dict]) -> dict[str, date]:
    seen: dict[str, date] = {}
    for d in digests:
        for item in d["main"] + d["still"]:
            seen.setdefault(item["url"], d["date"])
    return seen


# --------------------------------------------------------------------------- analysis


def window(digests: list[dict], end: date, days: int) -> list[dict]:
    start = end - timedelta(days=days - 1)
    return [d for d in digests if start <= d["date"] <= end]


def topic_rates(digests: list[dict]) -> dict[str, float]:
    if not digests:
        return {t: 0.0 for t in TOPICS}
    return {
        topic: sum(len(re.findall(p, d["text"], re.IGNORECASE)) for d in digests) / len(digests)
        for topic, p in TOPICS.items()
    }


def topic_changes(current: list[dict], previous: list[dict]) -> list[dict]:
    """Topics whose per-edition rate moved, biggest relative move first."""
    cur, prev = topic_rates(current), topic_rates(previous)
    rows = []
    for topic in TOPICS:
        c, p = cur[topic], prev[topic]
        if max(c, p) < MIN_RATE:
            continue
        ratio = (c + 0.1) / (p + 0.1)
        rows.append({"topic": topic, "current": round(c, 1), "previous": round(p, 1), "ratio": ratio})
    rows.sort(key=lambda r: abs(r["ratio"] - 1 if r["ratio"] >= 1 else 1 / r["ratio"] - 1), reverse=True)
    return rows


def describe_change(ratio: float) -> str:
    if ratio >= 1.5:
        return f"Up {ratio:.1f}x" if ratio < 10 else "Up 10x+"
    if ratio <= 1 / 1.5:
        return f"Down {round((1 - ratio) * 100)}%"
    return "Steady"


def stories(digests: list[dict], seen: dict[str, date]) -> list[dict]:
    """Stories in a period ranked by staying power: editions it appeared in x best score."""
    by_url: dict[str, dict] = {}
    for d in digests:
        for item in d["main"]:
            s = by_url.setdefault(item["url"], {**item, "editions": 0, "best": 0, "dates": []})
            s["editions"] += 1
            s["best"] = max(s["best"], item["score"] or 0)
            s["dates"].append(d["date"])
            if item["blurb"] and not s["blurb"]:
                s["blurb"] = item["blurb"]
    rows = list(by_url.values())
    start = min((d["date"] for d in digests), default=None)
    for r in rows:
        r["first_seen"] = seen.get(r["url"], min(r["dates"]))
    # A period's stories are the ones that *arrived* in it. Items carried in from before
    # already had their moment; counting their repeat appearances is exactly how an
    # evergreen repository ends up at the top of every recap.
    rows = [r for r in rows if start is None or r["first_seen"] >= start]
    rows.sort(key=lambda r: (r["editions"] * max(r["best"], 1), r["best"], r["url"]), reverse=True)
    return rows


# --------------------------------------------------------------------------- rendering


def tabs(current: str, base: str) -> str:
    """Tab row. `base` is the page's location: 'root' (README) or 'reports'."""
    links = {
        "root": {"Yesterday": "README.md", "This week": "reports/week.md", "This month": "reports/month.md"},
        "reports": {"Yesterday": "../README.md", "This week": "week.md", "This month": "month.md"},
    }[base]
    return " · ".join(
        f"**{name}**" if name == current else f"[{name}]({href})" for name, href in links.items()
    )


def _md(text: str) -> str:
    return text.replace("|", "\\|")


def _day(d: date) -> str:
    return f"{d:%a} {d.day} {d:%b}"


def _story_line(item: dict, prefix: str) -> str:
    title = _md(item["title"])
    blurb = f" {item['blurb']}" if item.get("blurb") else ""
    return f"- **[{title}]({item['url']})**{blurb}{prefix}"


def render_yesterday(digests: list[dict], seen: dict[str, date], reports_href: str = "reports") -> str:
    latest = digests[-1]
    today = latest["date"]
    fresh_since = today - timedelta(days=1)
    new = [i for i in latest["main"] if seen.get(i["url"], today) >= fresh_since]
    unfolding = [i for i in latest["main"] + latest["still"] if seen.get(i["url"], today) < fresh_since]
    unfolding.sort(key=lambda i: seen[i["url"]])
    lines = [tabs("Yesterday", "root"), "", f"### New in the last two days · {_day(today)}", ""]
    if latest["opening"]:
        lines += [f"> {latest['opening']}", ""]
    if new:
        lines += [_story_line(i, "") for i in new[:6]]
    else:
        lines.append("_A quiet day: nothing new cleared the bar. Still unfolding is below._")
    if unfolding:
        lines += ["", "### Still unfolding", ""]
        for i in unfolding[:4]:
            days = (today - seen[i["url"]]).days + 1
            lines.append(f"- **[{_md(i['title'])}]({i['url']})** · day {days}")
    name = latest["path"].name
    lines += [
        "",
        f"[Read the full briefing]({reports_href}/{name}) · [Every edition]({reports_href}/README.md)",
    ]
    return "\n".join(lines)


def _header(current: str, title: str) -> list[str]:
    return [
        "# AI Radar",
        "",
        "What changed in AI, in plain words.",
        "",
        tabs(current, "reports"),
        "",
        f"## {title}",
        "",
    ]


def _trend_table(rows: list[dict], label_now: str, label_before: str) -> list[str]:
    out = [
        f"| Topic | {label_now} | {label_before} | Trend |",
        "|---|---:|---:|---|",
    ]
    for r in rows:
        out.append(f"| {r['topic']} | {r['current']} | {r['previous']} | {describe_change(r['ratio'])} |")
    return out


def render_period(digests: list[dict], seen: dict[str, date], days: int, current: str) -> str:
    end = digests[-1]["date"]
    now = window(digests, end, days)
    before = window(digests, end - timedelta(days=days), days)
    start = end - timedelta(days=days - 1)
    noun = "week" if days == 7 else "month"
    lines = _header(
        current, f"{'The week' if days == 7 else 'The last 30 days'} · {_day(start)} to {_day(end)}"
    )
    top = stories(now, seen)[: 5 if days == 7 else 6]
    if not now:
        return "\n".join(lines + ["_No editions in this period._", ""])
    lines += ["### Stories with staying power" if days > 7 else "### The stories that mattered", ""]
    if not top:
        lines.append("_No new stories this period; see the editions below._")
    for s in top:
        span = f" · {s['editions']} edition{'s' if s['editions'] != 1 else ''}, first seen {_day(s['first_seen'])}"
        lines.append(_story_line(s, span))
    changes = topic_changes(now, before)
    if changes and before:
        heading = "Heating up and cooling off" if days == 7 else "Where attention moved"
        lines += [
            "",
            f"### {heading}",
            "",
            f"How often each topic came up per daily edition, this {noun} against the {noun} before "
            f"({len(now)} editions against {len(before)}). "
            "Counted from the digests' wording, so read it as direction, not exact size.",
            "",
            *_trend_table(changes[:8], f"This {noun}" if days == 7 else "Last 30 days", "Before"),
        ]
        if days > 7:
            shown = sorted(changes[:8], key=lambda r: r["current"], reverse=True)
            labels = ", ".join(f'"{r["topic"]}"' for r in shown)
            values = ", ".join(str(r["current"]) for r in shown)
            lines += [
                "",
                "```mermaid",
                "xychart-beta",
                '    title "Mentions per edition, last 30 days"',
                f"    x-axis [{labels}]",
                '    y-axis "Mentions"',
                f"    bar [{values}]",
                "```",
            ]
    if days == 7:
        lines += ["", "### Every edition this week", ""]
        lines += [f"- [{_day(d['date'])}]({d['path'].name})" for d in reversed(now)]
    else:
        lines += ["", f"[All {len(now)} editions this month, and every one before]({'README.md'})"]
    return "\n".join(lines) + "\n"


def write_readme_block(readme: Path, block: str) -> bool:
    """Replace the frontpage block in README.md. False (no write) when markers are absent,
    so tests and forks without the block are left alone."""
    if not readme.exists():
        return False
    text = readme.read_text(encoding="utf-8")
    start, end = text.find(README_START), text.find(README_END)
    if start < 0 or end < start:
        return False
    new = text[:start] + f"{README_START}\n\n{block}\n\n{README_END}" + text[end + len(README_END) :]
    if new != text:
        atomic_text(readme, new)
    return True


def main(reports: Path | None = None, readme: Path | None = None) -> None:
    reports = reports or ROOT / "reports"
    readme = readme or reports.parent / "README.md"
    digests = load_digests(reports)
    if not digests:
        print("[frontpage] no digests; nothing to do.")
        return
    seen = first_seen(digests)
    atomic_text(reports / "week.md", render_period(digests, seen, 7, "This week"))
    atomic_text(reports / "month.md", render_period(digests, seen, 30, "This month"))
    wrote = write_readme_block(readme, render_yesterday(digests, seen))
    print(f"[frontpage] wrote week.md, month.md{', README block' if wrote else ''}.")


if __name__ == "__main__":
    main()
