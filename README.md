# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Sat 14 Nov

> Frontier labs shipped a wave of agent and infrastructure updates: OpenAI added a wallet for agent purchases and published a customer story on legacy-portal handoffs, Google Research highlighted Antigravity's teamwork feature, and NVIDIA released cuPhoton for black-hole interferometry and new FP64 cuBLAS kernels. Meanwhile, a Hacker News thread alleging Nvidia engineered GPU scarcity via startup funding drew 911 points, and several lightweight local-first agent tools appeared on GitHub.

- **[Shield helps technicians hand off legacy portal work with OpenAI](https://openai.com/business/customer-stories/shield)** OpenAI published a customer story showing Shield using its models to let IT technicians offload routine work in legacy portals to Forge agents.
- **[Advancing science & engineering with Antigravity's /teamwork](https://research.google/blog/advancing-science-engineering-with-antigravitys-teamwork-feature/)** Google Research highlighted Antigravity's teamwork feature for collaborative science and engineering workflows.
- **[Run GPU-Powered Black Hole Interferometry with NVIDIA cuPhoton](https://developer.nvidia.com/blog/run-gpu-powered-black-hole-interferometry-with-nvidia-cuphoton/)** NVIDIA introduced cuPhoton, a GPU-accelerated library for very-long-baseline interferometry imaging, demonstrating M87* reconstruction.
- **[Faster Scientific Simulations with New FP64 Algorithms in NVIDIA cuBLAS](https://developer.nvidia.com/blog/faster-scientific-simulations-with-new-fp64-algorithms-in-nvidia-cublas/)** NVIDIA added high-precision FP64 kernels to cuBLAS, targeting molecular chemistry and materials-science workloads that spend most time in dense GEMM.
- **[Nvidia allegedly engineered scarcity by funding AI startups to buy its GPUs](https://www.techpowerup.com/354814/nvidia-allegedly-engineered-scarcity-by-funding-ai-startups-to-buy-its-gpus)** A TechPowerUp report, amplified to 911 Hacker News points, claims Nvidia funded startups to purchase GPUs, creating artificial scarcity.
- **[orderesworks42213/crypto-rpocket-accumulation-scanner](https://github.com/orderesworks42213/crypto-rpocket-accumulation-scanner)** A Python scanner that detects coins in quiet accumulation, back-tested on 961 samples with Telegram alerts.

### Still unfolding

- **[Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)** · day 22
- **[deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)** · day 19
- **[nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets)** · day 19
- **[Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)** · day 9

[Read the full briefing](reports/2026-11-14-digest.md) · [Every edition](reports/README.md)

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
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43481379502) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43481541761) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43507964106) | 🟢 ok | last run success |

Generated 2026-11-13 21:41 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
