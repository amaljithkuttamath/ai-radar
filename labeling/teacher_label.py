"""Label fetched abstracts with a teacher model, to train a small student on later.

The student we eventually want reads typed decisions straight out of its logits. This
script is the opposite end of that pipeline and deliberately so: a large teacher
*generates* JSON here, once, offline, to manufacture training volume. Generation is
acceptable for the teacher because it runs once and its cost is amortised over every
student training run. It would not be acceptable for the student, which is the whole
point of training one.

Three criteria per abstract, mirroring `config/profile.yaml`'s own split:

* `score`    0-5, "is this big" — traction, not taste.
* `topic`    one of the profile's topics, or `none` — what it is about.
* `relevant` boolean, "is this for this reader" — taste, not traction.

`profile.yaml` insists those axes stay separate and so does this schema. All three are
emitted in one JSON object per call, following the lesson already recorded in
`grader/judge.py`: asking for dimensions incrementally hit output-length limits mid-emit
and produced truncated, schema-invalid results.

## The holdout is not labelled here, on purpose

A model-labelled test set cannot tell you whether a student is *correct*; it can only
tell you whether the student imitates the teacher. So the corpus is split by a hash of
the paper id — deterministic, stable as the corpus grows, decided before any model sees
anything — and this script refuses to label the holdout side. Holdout rows are written
to a separate file with no label fields at all, for a human to fill in.

That file is the only ground truth in the project. Everything else is the teacher's
opinion, recorded as such: every row carries the teacher's model id and family, so a
later run can check that a student is not being graded by its own teacher's family the
way `grader/separation.py` already checks the digest against its critic.

Run: python -m labeling.teacher_label --limit 20      # dry run first, it costs money
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import llm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ABSTRACTS = ROOT / "data" / "labels" / "abstracts.jsonl"
TRAIN_OUT = ROOT / "data" / "labels" / "teacher_train.jsonl"
HOLDOUT_OUT = ROOT / "data" / "labels" / "holdout_unlabeled.jsonl"
FAILURES = ROOT / "data" / "labels" / "teacher_failures.jsonl"
PROFILE = ROOT / "config" / "profile.yaml"

# Fallback only. The real list comes from profile.yaml so the schema cannot drift away
# from the config the rest of the pipeline re-ranks with.
DEFAULT_TOPICS = ["interpretability", "agents", "evals", "rag",
                  "efficient inference", "long context"]

SCORE_ANCHORS = [
    "0 - not a research contribution, or pure noise",
    "1 - minor increment, narrow interest",
    "2 - solid but unremarkable work",
    "3 - notable result the subfield will cite",
    "4 - strong result likely to change practice",
    "5 - landmark, reframes how people work",
]

SYSTEM = (
    "You label machine-learning papers for a daily research digest. "
    "Judge only from the title and abstract given. Do not speculate about work you "
    "cannot see. Answer with one JSON object and no other text."
)


def topics() -> list[str]:
    try:
        import yaml
        loaded = yaml.safe_load(PROFILE.read_text()) or {}
        names = [t["name"] for t in loaded.get("topics", []) if t.get("name")]
        return names or DEFAULT_TOPICS
    except Exception:
        return DEFAULT_TOPICS


def is_holdout(paper_id: str, permille: int) -> bool:
    """Deterministic split on the id alone.

    Not random, not by date, not by position: a hash of the id means the same paper
    lands on the same side on every machine and every rerun, and new papers arriving
    daily cannot quietly shift an existing row from eval into train.
    """
    digest = hashlib.sha256(paper_id.encode()).hexdigest()
    return int(digest[:8], 16) % 1000 < permille


def build_prompt(paper: dict, topic_names: list[str]) -> str:
    return "\n".join([
        "Paper:",
        f"Title: {paper['title']}",
        f"Abstract: {paper['abstract']}",
        "",
        "Return JSON with exactly these keys:",
        '  "score":        integer 0-5, how significant this work is:',
        *[f"                  {anchor}" for anchor in SCORE_ANCHORS],
        '  "score_why":    one sentence, under 25 words',
        f'  "topic":        exactly one of {json.dumps(topic_names + ["none"])}',
        '  "topic_why":    one sentence, under 25 words',
        '  "relevant":     true or false, whether a reader following those topics',
        "                  would want this in their digest",
        '  "relevant_why": one sentence, under 25 words',
        "",
        "Score and relevance are independent: a landmark paper outside these topics "
        "scores high and is not relevant; a minor paper inside them is the reverse.",
    ])


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a reply, tolerating code fences and preamble."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in reply")
    return json.loads(text[start : end + 1])


def validate(label: dict, topic_names: list[str]) -> dict:
    """Reject anything the trainer could not consume exactly as written.

    A malformed label that is silently coerced becomes a wrong training target that
    nothing downstream can distinguish from a right one, so this raises instead.
    """
    score = label.get("score")
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 5:
        raise ValueError(f"score must be an integer 0-5, got {score!r}")
    topic = label.get("topic")
    if topic not in topic_names + ["none"]:
        raise ValueError(f"topic {topic!r} is not in the profile")
    relevant = label.get("relevant")
    if not isinstance(relevant, bool):
        raise ValueError(f"relevant must be a boolean, got {relevant!r}")
    return {
        "score": score,
        "topic": topic,
        "relevant": relevant,
        "score_why": str(label.get("score_why", ""))[:300],
        "topic_why": str(label.get("topic_why", ""))[:300],
        "relevant_why": str(label.get("relevant_why", ""))[:300],
    }


def done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                ids.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return ids


def load_abstracts() -> list[dict]:
    if not ABSTRACTS.exists():
        raise SystemExit(f"{ABSTRACTS} not found — run python -m labeling.fetch_abstracts first")
    papers = []
    for line in ABSTRACTS.read_text().splitlines():
        if line.strip():
            try:
                papers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return papers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0,
                        help="label at most this many papers (0 = all). Use a small "
                             "number first: every call costs money.")
    parser.add_argument("--model", default="",
                        help="teacher model id (default: the grader role's model)")
    parser.add_argument("--holdout-permille", type=int, default=15,
                        help="per-mille of the corpus reserved for human labelling "
                             "(15 of ~16.5k arxiv ids is ~250 papers)")
    parser.add_argument("--holdout-only", action="store_true",
                        help="write the human-labelling file and stop. Needs no model, "
                             "no key and no money — this is the first thing to run.")
    args = parser.parse_args()

    topic_names = topics()
    papers = load_abstracts()
    for path in (TRAIN_OUT, HOLDOUT_OUT, FAILURES):
        path.parent.mkdir(parents=True, exist_ok=True)

    holdout = [p for p in papers if is_holdout(p["id"], args.holdout_permille)]
    train = [p for p in papers if not is_holdout(p["id"], args.holdout_permille)]

    # The holdout is written once, unlabelled, and never passed to the model. Writing it
    # from the same split function that excludes it from training is what makes the two
    # sets provably disjoint rather than disjoint by convention.
    written_holdout = done_ids(HOLDOUT_OUT)
    with HOLDOUT_OUT.open("a", encoding="utf-8") as out:
        new = 0
        for paper in holdout:
            if paper["id"] in written_holdout:
                continue
            out.write(json.dumps({
                "id": paper["id"],
                "title": paper["title"],
                "abstract": paper["abstract"],
                "arxiv_url": paper["arxiv_url"],
                "score": None, "topic": None, "relevant": None,
                "label_source": "human-pending",
            }, ensure_ascii=False) + "\n")
            new += 1
    print(f"[holdout] {len(holdout)} reserved, {new} newly written -> {HOLDOUT_OUT}",
          file=sys.stderr)
    if args.holdout_only:
        print(f"[holdout] {len(holdout)} papers await human labels in {HOLDOUT_OUT}")
        return 0

    # Only the teacher loop below needs a model, so the config check sits here rather
    # than at the top: producing the file a human labels must never depend on a key.
    if not llm.configured():
        raise SystemExit(f"llm not configured: {llm.describe()}")
    model = args.model or llm.model_for(llm.GRADER)
    if not model:
        raise SystemExit("no teacher model: pass --model or set RADAR_GRADER_MODEL")

    already = done_ids(TRAIN_OUT)
    todo = [p for p in train if p["id"] not in already]
    if args.limit:
        todo = todo[: args.limit]
    print(f"[teacher] model={model} family={llm.family(model)} · {len(train)} trainable "
          f"· {len(already)} labelled · {len(todo)} this run", file=sys.stderr)

    labelled = failed = 0
    with TRAIN_OUT.open("a", encoding="utf-8") as out, \
            FAILURES.open("a", encoding="utf-8") as bad:
        for index, paper in enumerate(todo, 1):
            try:
                reply = llm.chat(SYSTEM, build_prompt(paper, topic_names),
                                 model, max_tokens=400)
                label = validate(extract_json(reply), topic_names)
            except (llm.LLMError, urllib.error.HTTPError, ValueError,
                    json.JSONDecodeError) as error:
                bad.write(json.dumps({"id": paper["id"], "error": str(error)[:500]}) + "\n")
                bad.flush()
                failed += 1
                continue
            out.write(json.dumps({
                "id": paper["id"],
                "title": paper["title"],
                "abstract": paper["abstract"],
                **label,
                "label_source": "teacher",
                "teacher_model": model,
                "teacher_family": llm.family(model),
            }, ensure_ascii=False) + "\n")
            out.flush()
            labelled += 1
            if index % 25 == 0:
                print(f"[teacher] {labelled} labelled, {failed} failed "
                      f"({index}/{len(todo)})", file=sys.stderr)

    print(f"[teacher] done: {labelled} labelled, {failed} failed -> {TRAIN_OUT}")
    if failed:
        print(f"[teacher] failures recorded in {FAILURES}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
