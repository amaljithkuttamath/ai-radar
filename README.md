# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Sat 21 Nov

> Anthropic’s IPO close and a broad AI sell-off dominated attention (444 HN points), while OpenAI published a layered defense against adversarial distillation. On the research side, the Jeveration paper shows System-One-style models can generate images in a single forward pass, and its traction has risen sharply over three consecutive radar runs.

- **[han938/open-webui-private-ai-desk](https://github.com/han938/open-webui-private-ai-desk)** A local-first Open WebUI fork for chatting with private models.
- **[unsloth/Inkling-2-Mini-GGUF](https://huggingface.co/unsloth/Inkling-2-Mini-GGUF)** GGUF quant of the Inkling-2-Mini MoE multimodal model (image-text-to-text).
- **[AgentRoboCritic: Understanding the Capability of Frontier Agents on Direct Robot Control](https://arxiv.org/abs/2611.26613)** Action-level critique framework for frontier agents (e.g., GPT-6 Astra) controlling robots via low-level numerical actions across 12 manipulation benchmarks.
- **[Text-Aware, Vision-Blind: How Multimodal Image Editing Systems Handle Unsafe Inputs](https://arxiv.org/abs/2611.26569)** Introduces EditSafetyBench (5,940 image-instruction pairs, 11 risk categories, 3 edit intents) exposing single-modality safety gaps in instruction-guided editing.
- **[The Geometry of Lies: Knowledge and Persona Directions for Detecting Deception in LLMs](https://arxiv.org/abs/2611.26545)** Label-free persona directions from honest/deceptive role-play outperform single-dataset linear probes on Liars’ Bench at 70B scale, except on Qwen.
- **[AURA: AUdio-dRiven streaming Avatar](https://arxiv.org/abs/2611.26540)** Chunk-by-chunk video generation with rolling KV cache (1.3B and larger), requiring only current audio chunk — no multi-second look-ahead.

### Still unfolding

- **[nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets)** · day 26
- **[deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)** · day 26
- **[Vyber07/cyber-security](https://huggingface.co/datasets/Vyber07/cyber-security)** · day 16
- **[ccch1mneyyy/dsh-Go](https://github.com/ccch1mneyyy/dsh-Go)** · day 8

[Read the full briefing](reports/2026-11-21-digest.md) · [Every edition](reports/README.md)

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
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/44797322697) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/44797424069) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/44825936245) | 🟢 ok | last run success |

Generated 2026-11-20 22:23 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
