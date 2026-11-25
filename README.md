# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Wed 25 Nov

> A wave of new benchmarks and agent-evaluation frameworks dominates today's radar, headlined by a reinforcement-learning method that teaches agents to act on verified beliefs rather than guess, and a mirror-based stress test that breaks current robot policies. Simultaneously, NVIDIA published a low-level kernel guide for NVFP4 attention on Blackwell, and OpenAI announced GPT-6's protein-design capabilities — though the latter two arrive as lab blogs without open artifacts.

- **[Lazy Agents Answer Against Their Own Beliefs: Reinforcement Learning with Verifiable Beliefs Teaches Them to Act on What They Believe](https://arxiv.org/abs/2611.32884)** Researchers from DECLARE Lab introduce Reinforcement Learning with Verifiable Beliefs (RLVB), a training scheme that uses the simulator's exact posterior at each step to reward ev…
- **[Embodied AI Fails the Mirror Test: How a Simple Mirror Breaks Robot Policies](https://arxiv.org/abs/2611.33010)** A new benchmark, RoboDojo-Mirror, adds single/dual mirrors and mirrored tabletops to existing manipulation tasks.
- **[PartAgent: Agentic 3D Part Segmentation via Expert Integration and Closed-Loop Refinement](https://arxiv.org/abs/2611.32554)** A training-free agentic framework that fuses 3D geometric experts (for region proposals) with 2D semantic experts (for part labels) and iteratively refines segmentations through a…
- **[WorldLeague: Benchmarking Physical Agency](https://arxiv.org/abs/2611.30989)** A benchmark suite testing AI systems across Blender operation, complex video-game instruction following, and real robot-arm manipulation, measuring the breadth of autonomously ach…
- **[3AGameFactory-Motion: Agentic Rigging and Reliable Complex Motion Generation for Diverse 3D Assets](https://arxiv.org/abs/2611.30013)** Introduces DivDynBench, evaluating rigging and motion generation across six morphology categories with multi-phase, timed instructions.
- **[ThinkMorph-SSL: Scaling Interleaved Multimodal Reasoning with Pretext Tasks](https://arxiv.org/abs/2611.32183)** A two-stage recipe: first, models learn to produce interleaved image-text reasoning traces by solving visual pretext tasks (colorization, denoising) without instruction tuning; se…

### Still unfolding

- **[Digitaluz/uzbek-language-corpus](https://huggingface.co/datasets/Digitaluz/uzbek-language-corpus)** · day 6

[Read the full briefing](reports/2026-11-25-digest.md) · [Every edition](reports/README.md)

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
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45486057862) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45486178229) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45512323894) | 🟢 ok | last run success |

Generated 2026-11-25 00:10 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
