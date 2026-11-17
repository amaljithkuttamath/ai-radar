# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Tue 17 Nov

> Three frontier-scale releases dominate today: ScaleVLA connects a 552B DeepSeek backbone to a robot action head, InclusionMed publishes a reproduced Atlas of five healthcare benchmarks, and Sage S2.1 Flash ships a 320B MoE model with scientific encoders and verifiable tool environments. Together they signal a shift from demo-scale VLAs and medical evals toward reproducible, frontier-backed systems.

- **[ScaleVLA: Scaling Vision-Language-Action Models to 552 Billion Parameters](https://arxiv.org/abs/2611.21607)** Galaxy General Robotics connects a 552B DeepSeek-V4.1-Flash backbone to a trainable action DiT and systematically compares VLM backbones from 2B to 552B under shared training.
- **[BLIP-Live: Balancing Timeliness & Firing Precision in Proactive Streaming Video Agents](https://arxiv.org/abs/2611.21553)** Researchers introduce BLIP-Live, a unified dataset, metrics, harness, and training framework for proactive streaming video agents that must decide when to respond vs.
- **[InclusionMed: Benchmarking AI for Inclusive Healthcare](https://arxiv.org/abs/2611.21218)** The InclusionMed Atlas organizes benchmarks across three healthcare roles and three AI capabilities; the first release reproduces four public benchmarks and adds a private diagnos…
- **[Rotation-Invariant Machine Learning for Highly Symmetric Molecular Configurations](https://arxiv.org/abs/2611.21308)** A new lightweight benchmark exposes degeneracies in both invariant and equivariant architectures on n-fold symmetric atomic environments, guiding a proposed fix.
- **[When Do Histology Foundation Models Need Geometric Test-Time Augmentation?](https://arxiv.org/abs/2611.21565)** Benchmarking 9 histology FMs and 6 general-purpose models shows D₄ test-time augmentation loses value as foundation models gain inherent rotational invariance.
- **[Benchmarking memory and nonlinear processing capacity of quantum recurrent neural networks for time series prediction](https://arxiv.org/abs/2611.21552)** A rigorous task-driven benchmark quantifies memory and nonlinear capacity of variational QRNNs, enabling intuitive comparison to classical RNNs.

[Read the full briefing](reports/2026-11-17-digest.md) · [Every edition](reports/README.md)

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
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43952987429) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43953146084) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43980857250) | 🟢 ok | last run success |

Generated 2026-11-16 23:52 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
