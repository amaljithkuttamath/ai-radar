# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Fri 20 Nov

> A wave of new diagnostic benchmarks for embodied AI leads today’s observations: Mind2Act World introduces a three-axis test for robotic manipulation, while ZeroVLN, WeMM-Video, EgoCaptioner, and TuringSpace each target a different gap in navigation, omni-modal video, egocentric captioning, and spatial reasoning. Simultaneously, a Hacker News discussion surfaced a paper claiming language models can rewrite their own weights, and a private/local AI desktop project gathered rapid GitHub traction.

- **[Mind2Act World: A Diagnostic Benchmark for Embodied Mind, Physical Action, and Mind-Action Composition in Robotic Manipulation](https://arxiv.org/abs/2611.26444)** Mind2Act World introduces a benchmark that separates history-based reasoning, precise physical execution, and their composition through environmental feedback across robotic manip…
- **[ZeroVLN: Learning to Navigate without Supervised Fine-Tuning of the VLM Brain](https://arxiv.org/abs/2611.26414)** ZeroVLN presents a slow-fast navigation framework that keeps the vision-language model frozen and uses a semantic tool-calling interface for movement decisions, avoiding navigatio…
- **[WeMM-Video: Pushing the Frontiers of Open-Source Omni-Modal Video Understanding](https://arxiv.org/abs/2611.26409)** Tencent releases WeMM-Video, a family of bilingual (Chinese-English) omni-modal models (2B–35B) unifying text, image, audio, and video with hybrid thinking (fast instruct and slow…
- **[EgoCaptioner: Towards Comprehensive and Fine-Grained Egocentric Video Captioning](https://arxiv.org/abs/2611.26380)** EgoCaptioner pairs a video-level overview with timed, adaptive narration steps and key-moment timestamps, plus a coarse-to-fine annotation pipeline to train MLLMs for detailed ego…
- **[Language Models Can Rewrite Their Own Weights](https://arxiv.org/abs/2611.21885)** A paper claiming that language models can directly modify their own parameters during inference surfaced on Hacker News (189 points, 84 comments), proposing a form of self-referen…
- **[han938/open-webui-private-ai-desk](https://github.com/han938/open-webui-private-ai-desk)** A local-first desktop wrapper around Open WebUI that lets users chat with private models offline, observed with 93 GitHub stars in its first day.

### Still unfolding

- **[sensenova/SenseNova-Loop-9B](https://huggingface.co/sensenova/SenseNova-Loop-9B)** · day 4

[Read the full briefing](reports/2026-11-20-digest.md) · [Every edition](reports/README.md)

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
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/44596627164) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/44596743343) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/44629588691) | 🟢 ok | last run success |

Generated 2026-11-19 22:47 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
