# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Sat 7 Nov

> The radar captures a split between maturing infrastructure — Hugging Face Transformers (168k stars) and Microsoft's ML curriculum (92k stars) — and a wave of new evaluation benchmarks targeting agents in wet-lab science, theorem proving, and molecular representation quality. NVIDIA's simready-assets dataset (1.4M downloads) and fresh Qwen/DeepSeek multimodal models round out the highest-signal items in a 48-hour window heavy on usable artifacts.

- **[Muir: Linear Attention with Sensitivity-Allocated Gating and Matched-Filter Readout](https://arxiv.org/abs/2611.08376)** Linear attention variant (GDN-2 successor) that decouples erase/write gates and allocates sensitivity per channel.
- **[Vera Delivers the Best of Both Worlds: Highest Throughput and Fastest Agents](https://blogs.nvidia.com/blog/vera-cpu-highest-throughput-fastest-agents/)** NVIDIA blog positioning Vera CPU for agent workloads that alternate GPU reasoning and CPU execution.
- **[Measuring how AI agents handle everyday wet-lab science](https://openai.com/index/measuring-how-ai-agents-handle-wet-lab-science)** OpenAI introduces BioBasicsBench: 100 tasks testing agent interpretation of raw experimental data and wet-lab protocol execution.
- **[On the limitations of molecular representations](https://arxiv.org/abs/2611.08420)** Systematic study showing SOTA molecular embeddings fail to capture graph structure, 3D shape, and ADMET similarity better than baselines.
- **[SpecCTMC: Exact Speculative Simulation of Diffusion Language Model Continuous-Time Markov Chains](https://arxiv.org/abs/2611.08362)** Training-free speculative sampler for masked diffusion LMs that preserves exact output distribution while reducing sequential bottleneck.
- **[LeanContext: Disentangling Mathematical Resources from Local Formal Context in Lean Whole-Proof Generation](https://arxiv.org/abs/2611.08277)** 129k-problem Lean benchmark separating mathematical context from environment context for whole-proof generation.

### Still unfolding

- **[huggingface/transformers](https://github.com/huggingface/transformers)** · day 15
- **[Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)** · day 15
- **[nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets)** · day 12
- **[deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)** · day 12

[Read the full briefing](reports/2026-11-07-digest.md) · [Every edition](reports/README.md)

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
| [Daily digest](https://github.com/amaljithkuttamath/ai-radar/blob/main/reports/latest.md) | 🟡 warn | last digest committed 27h ago |
| [Model synthesis](https://github.com/amaljithkuttamath/ai-radar/blob/main/reports/latest.md) | 🟢 ok | latest digest carries model synthesis |
| [Eval loop](https://github.com/amaljithkuttamath/ai-radar/blob/main/evals/latest.json) | 🟡 warn | grader last committed 27h ago · tier 0 only, no model judgement |
| [Self-healing loop](https://github.com/amaljithkuttamath/ai-radar/issues?q=is%3Aissue+is%3Aopen+label%3Awatchdog) | 🟢 ok | no unanswered alarms |
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43075975951) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43076104878) | 🟡 warn | 1 consecutive failures |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43105357578) | 🟢 ok | last run success |

Generated 2026-11-11 22:19 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
