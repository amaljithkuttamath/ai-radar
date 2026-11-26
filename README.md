# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Thu 26 Nov

> A new attention architecture (Mixture-of-Loops Transformer) claims expressivity gains by reusing KV memory across loops, while Real2SimLab and Sage-Med release unified benchmarks for real-to-sim transfer and medical multimodal scaling. Several video-generation and agent-evaluation platforms also appeared with runnable code.

- **[Mixture-of-Loops Transformer](https://arxiv.org/abs/2611.34923)** HUST researchers introduced MoLT, a looped Transformer that passes keys and values as memory across loops via Mixture-of-Loops Attention, offering two modes: residual-stream reuse…
- **[Real2SimLab: A Unified Platform for Real-to-Simulation Transfer](https://arxiv.org/abs/2611.34849)** Real2SimHub released a single evaluation harness that runs any real-to-sim method across multiple benchmarks, replacing N×M custom integrations with a shared interface.
- **[Sage-Med: Scaling Medical Multimodal Intelligence](https://arxiv.org/abs/2611.34575)** The Sage-Med team published a 35B-parameter medical MLLM (3B activated) showing that scaling model size mainly helps text, not multimodal perception, and released a preview checkp…
- **[Improving and Expanding Video Editing Capabilities Without Videos](https://arxiv.org/abs/2611.34941)** HorizonWind2004 proposed Image-to-Video Transfer (I2VT), which post-trains a video editor on single images using an image editor as teacher — no paired video data required.
- **[Agentic LongLive: Asynchronous Agentic Memory for Long Video Generation](https://arxiv.org/abs/2611.34907)** NVIDIA researchers built a separate memory agent that reads only revealed prompts (never generated frames) to keep long streaming video consistent without offline planning.
- **[EgoUseBench: Benchmarking Computer-Use Agents under Evolving First-Person Contexts](https://arxiv.org/abs/2611.34466)** Yurun Chen et al.

[Read the full briefing](reports/2026-11-26-digest.md) · [Every edition](reports/README.md)

<!-- frontpage:end -->

## Want a radar for another topic?

AI Radar is a template. Fork it, point `config/sources.yaml` at the feeds you care about,
describe your interests in `config/profile.yaml`, and add a model API key as a repository
secret. Your own radar publishes the next morning. Try it first with no keys at all:

```bash
uv sync --locked && uv run python -m radar demo
```

## How stories are picked

Each story is ranked by **importance × freshness × relevance**. Importance counts evidence
you can check (a frontier lab's own announcement, a usable artifact, a concrete result, and
traction gained recently rather than all-time totals). Freshness fades a story day by day,
so new developments lead and older ones move to "Still unfolding". Relevance follows the
interests in the profile. Details in [distill/news.py](distill/news.py).

**Sources (40+):** arXiv (machine learning, language, AI, robotics, vision), Hugging Face
papers and trending, GitHub trending, Hacker News; the labs themselves (OpenAI, Anthropic,
Google DeepMind, Google AI, Meta AI, Mistral, Microsoft Research, Apple, Amazon, NVIDIA,
AMD, Hugging Face, AWS, Berkeley AI Research, MIT); press (TechCrunch, MIT Technology
Review, IEEE Spectrum); expert writers (Simon Willison, Import AI, Latent Space,
Interconnects, One Useful Thing, Ahead of AI, Lil'Log, Eugene Yan); and policy and safety
(AI Alignment Forum, CSET). The full list is in [config/sources.yaml](config/sources.yaml).

<details>
<summary><strong>Pipeline status</strong></summary>

<!-- health:start -->

| signal | status | detail |
|---|---|---|
| [Daily digest](https://github.com/amaljithkuttamath/ai-radar/blob/main/reports/latest.md) | 🟢 ok | last digest committed 3h ago |
| [Model synthesis](https://github.com/amaljithkuttamath/ai-radar/blob/main/reports/latest.md) | 🟢 ok | latest digest carries model synthesis |
| [Eval loop](https://github.com/amaljithkuttamath/ai-radar/blob/main/evals/latest.json) | 🟡 warn | grader last committed 3h ago · tier 0 only, no model judgement |
| [Self-healing loop](https://github.com/amaljithkuttamath/ai-radar/issues?q=is%3Aissue+is%3Aopen+label%3Awatchdog) | 🟢 ok | no unanswered alarms |
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45693779959) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45693885945) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45721457421) | 🟢 ok | last run success |

Generated 2026-11-25 23:49 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
