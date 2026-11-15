# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Sun 15 Nov

> Multiple forks of the **AI Manus 2.0** general-purpose agent system appeared on GitHub today, while Nvidia published new CUDA libraries for scientific computing and Google released a multimodal knowledge-agent dataset. Anthropic and Mistral continue their IPO roadshow communications, carried over from earlier this week.

- **[alicebrown323/pro-tools-desktop](https://github.com/alicebrown323/pro-tools-desktop)** Alice Brown released a Pro Tools 2026 desktop setup with multitrack editing, MIDI sequencing, VST hosting, and a portable mode for Windows 11.
- **[Topkiflare74/ai--manus2.0](https://github.com/Topkiflare74/ai--manus2.0)** Topkiflare74 published AI Manus 2.0, a general-purpose AI agent system that runs tools and operations in a sandbox environment.
- **[Run GPU-Powered Black Hole Interferometry with NVIDIA cuPhoton](https://developer.nvidia.com/blog/run-gpu-powered-black-hole-interferometry-with-nvidia-cuphoton/)** Nvidia introduced cuPhoton for GPU-accelerated black hole interferometry, targeting imaging of microarcsecond-scale structures.
- **[Faster Scientific Simulations with New FP64 Algorithms in NVIDIA cuBLAS](https://developer.nvidia.com/blog/faster-scientific-simulations-with-new-fp64-algorithms-in-nvidia-cublas/)** Nvidia added new FP64 algorithms to cuBLAS for dense linear algebra, accelerating molecular chemistry and materials science workloads.
- **[google/multimodal-knowledge-agent](https://huggingface.co/datasets/google/multimodal-knowledge-agent)** Google released a multimodal knowledge-agent dataset covering image-text-to-text, visual QA, and document QA tasks under Apache-2.0.
- **[higurashi-ai/Haru-4B](https://huggingface.co/higurashi-ai/Haru-4B)** Higurashi-ai released Haru-4B, a full-duplex speech-to-speech audio-to-audio model (safetensors).

### Still unfolding

- **[deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)** · day 20
- **[nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets)** · day 20
- **[Vyber07/cyber-security](https://huggingface.co/datasets/Vyber07/cyber-security)** · day 10
- **[nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B)** · day 8

[Read the full briefing](reports/2026-11-15-digest.md) · [Every edition](reports/README.md)

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
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43617568447) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43617622485) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43633298089) | 🟢 ok | last run success |

Generated 2026-11-14 20:10 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
