# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Wed 18 Nov

> The strongest signal is a demonstrable shift away from Transformer-centric design: researchers showed LLMs can write neural weights directly without gradient descent, while a separate system claims 385× inference efficiency gains using energy-based reasoning. Frontier labs shipped new models (OpenAI GPT‑6.2 Astra/Sol, SenseNova‑Loop‑9B, Tencent Hy4‑flash) and hardware (NVIDIA RTX Spark desktops), and multiple teams released agent frameworks for coding, robotics, and multi‑humanoid collaboration.

- **[Weight-Space Programming Doesn't Need Transformers](https://arxiv.org/abs/2611.22055)** Researchers tasked three frontier LLMs with writing neural-network weights by hand, without gradient-based training; given minimal guidance and a sandbox, the models designed plai…
- **[Heave-Ho: Decentralized Long-Horizon Multi-Humanoid Collaboration](https://arxiv.org/abs/2611.22275)** A decentralized framework adapts a humanoid foundation model for physically coupled multi-robot loco-manipulation, enabling coordinated control from local observations and long-ho…
- **[GPT‑6.2 Astra and GPT‑6.2 Sol](https://simonwillison.net/2026/Nov/17/gpt62-astra-and-sol/)** OpenAI released two new API models: Astra for hardest projects (80% of prior price) and Sol for everyday work; LLM CLI tool added same-day support.
- **[StringQFT: A Multiuse Textbook Resource for AI-Assisted Theoretical Physics](https://arxiv.org/abs/2611.23225)** An 18-volume, 3,795-page textbook collection with an open-book benchmark (1,073 items, 499 auto-checkable) and RAG infrastructure for AI-assisted physics research.
- **[TeleChat to Xing4: Advancing Frontier Agentic Models on Domestic Chips and Frameworks](https://arxiv.org/abs/2611.22115)** The Xing 4 series extends TeleChat through architecture and training infrastructure advances on Ascend chips, covering sparse activation, attention design, and speculative decodin…
- **[Build Training-Ready Physical AI Datasets with Two Prompts in NVIDIA Cosmos](https://developer.nvidia.com/blog/build-training-ready-physical-ai-datasets-with-two-prompts-in-nvidia-cosmos/)** NVIDIA demonstrates generating diverse, simulation-ready robotics datasets from two text prompts using Cosmos world models, targeting rare defects and challenging scenarios.

[Read the full briefing](reports/2026-11-18-digest.md) · [Every edition](reports/README.md)

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
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/44159165461) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/44159315193) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/44193097912) | 🟢 ok | last run success |

Generated 2026-11-17 23:11 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
