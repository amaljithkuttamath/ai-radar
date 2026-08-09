"""The eval loop, as code.

`docs/operating/grader.md` specifies a grader that reads the day's digest, scores it
against a 10-dimension rubric, and commits the result. Until 2026-08 that specification
had no implementation in this repo: the grader was a prompt inside an external scheduled
task, reconstructing the contract from prose every morning. It stopped on 2026-07-13 and
nobody noticed for 26 days, because a thing with no code has no tests, no version, and
no run history to be absent from.

This package is the implementation. Execution stays external per ADR-0003 — the runner
invokes `python -m grader` — so a broken pipeline still cannot suppress its own critic.

Layout:
  freshness.py   publication time, age, staleness gate, X3 (deterministic)
  links.py       URL extraction, liveness, the A2 ceiling (observed, not judged)
  separation.py  the model-separation fence: refuses to grade its own family
  judge.py       one model call for the eight judgement dimensions
  artifacts.py   assembly, schema validation, evals/ writes, backlog, issue conditions
  cli.py         orchestration

Stdlib only, and it never imports `distill`. The eval loop must keep working when the
pipeline it grades cannot even resolve its dependencies.
"""
