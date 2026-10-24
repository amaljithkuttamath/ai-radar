"""A single local/CI entry point. Run `python -m radar --help`."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    app = argparse.ArgumentParser(
        prog="python -m radar",
        description="Collect AI sources, preview digests, and publish validated reports.",
    )
    app.add_argument("--root", type=Path, help="data/report directory (default: repo; also RADAR_HOME)")
    commands = app.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("collect", "Refresh source observations and collection health"),
        ("distill", "Score existing observations and generate a digest"),
        ("run", "Collect and distill in one run"),
        ("doctor", "Inspect local publication and collection health"),
        ("demo", "Run an isolated offline example with synthetic data"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--window", help="positive lookback, e.g. 48h or 7d")
        command.add_argument(
            "--backend", choices=("dryrun", "template", "auto", "openai", "github", "anthropic", "ollama")
        )
        command.add_argument("--max-items", type=int)
        command.add_argument("--include-threshold", type=int)
        command.add_argument("--focus", help="comma-separated interests; empty disables focus")
        if name == "doctor":
            command.add_argument("--json", action="store_true", help="machine-readable health report")
    return app


def demo() -> int:
    from collectors.common import ROOT, make_item
    from radar.storage import atomic_json

    parent = ROOT / "data" / "demo"
    parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
    examples = [
        (
            "research",
            "A reproducible agent evaluation dataset",
            "A synthetic dataset for testing agent reliability.",
        ),
        (
            "hardware",
            "An open inference benchmark for accelerators",
            "A synthetic benchmark with reproducible code.",
        ),
        ("releases", "An inspectable retrieval toolkit", "A synthetic retrieval API with published code."),
    ]
    for index, (category, title, summary) in enumerate(examples):
        item = make_item(
            id=f"demo:{index}",
            category=category,
            title=title,
            url=f"https://example.org/demo/{index}",
            source=f"Synthetic demo {index}",
            raw_summary=summary,
            signals={"gh_stars": 100 + index},
        )
        atomic_json(workspace / "data" / "raw" / f"{index}.json", item)
    env = os.environ | {"RADAR_AGENT": "off", "FOCUS_BACKEND": "lexical", "CLUSTER_BACKEND": "lexical"}
    result = subprocess.run(
        [sys.executable, "-m", "radar", "--root", str(workspace), "distill", "--backend", "template"],
        env=env,
        check=False,
    )
    if result.returncode == 0:
        print(f"Demo complete. Synthetic inputs and preview: {workspace}")
    return result.returncode


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.root:
        os.environ["RADAR_HOME"] = str(args.root.expanduser().resolve())
    try:
        from radar.config import Settings

        settings = Settings.load(vars(args))
        if args.command == "doctor":
            from radar.doctor import inspect

            status = inspect(settings)
            if args.json:
                print(json.dumps(status, indent=2))
            else:
                print(f"AI Radar — {'healthy' if status['healthy'] else 'needs attention'}")
                for name, check in status["checks"].items():
                    detail = check.get("detail", check.get("path", check.get("name", "")))
                    age = f" ({check['age_hours']}h old)" if "age_hours" in check else ""
                    print(f"  {name}: {check['status']}{age} — {detail}")
            return 0 if status["healthy"] else 1
        if args.command == "demo":
            return demo()
        if args.command != "collect":
            settings.check_credentials()
        from radar.pipeline import collect, distill, pipeline_lock

        with pipeline_lock():
            if args.command in {"collect", "run"}:
                collect(settings)
            if args.command in {"distill", "run"}:
                output = distill(settings)
                print(f"{'Preview' if settings.backend in {'dryrun', 'template'} else 'Published'}: {output}")
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"[radar] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
