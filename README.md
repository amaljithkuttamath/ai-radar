# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Mon 16 Nov

> NVIDIA’s Vera Rubin platform debuted on MLPerf, sweeping training benchmarks and posting over 10× throughput-per-watt gains for agentic inference. Frontier labs simultaneously shipped agent tooling: OpenAI added computer-use agents for healthcare, Microsoft released TokenEconomizer to cut coding-agent token waste, and NVIDIA expanded CUDA-X libraries for agent-driven scientific workloads.

- **[NVIDIA Sweeps MLPerf Training and Endpoints as Vera Rubin Debuts With Leading Performance](https://blogs.nvidia.com/blog/mlperf-training-endpoints-vera-rubin/)** NVIDIA’s Vera Rubin platform swept every MLPerf Training v6.1 benchmark and, in its first MLPerf Endpoints submission, delivered >10× generational throughput-per-watt gains for ag…
- **[NVIDIA CUDA-X Libraries Give Agents the Tools to Accelerate Scientific Discovery](https://blogs.nvidia.com/blog/cuda-x-libraries-agents-accelerate-scientific-discovery/)** New CUDA-X libraries (cuPhoton, cuPotential, cuSpa) let AI agents accelerate data-intensive research in astrophysics, materials science, and single-cell biology.
- **[TokenEconomizer: Learning from Experience to Make AI Coding Agents More Efficient](https://www.microsoft.com/en-us/research/blog/tokeneconomizer-learning-from-experience-to-make-ai-coding-agents-more-efficient/)** Microsoft Research open-sourced a plugin that reuses past coding-session context to cut token spend while preserving task success.
- **[More ways to move care forward with ChatGPT for Healthcare](https://openai.com/index/more-ways-to-move-care-forward-with-chatgpt-for-healthcare)** OpenAI launched computer-use agents, improved clinical answers, and healthcare plugins that operate across EHR and scheduling software.
- **[Advancing computer-use agents for healthcare teams](https://openai.com/index/advancing-computer-use-for-healthcare-teams)** Companion release detailing the computer-use agent architecture for healthcare: screen observation, action execution, and safety guardrails.
- **[NVIDIA Vera Rubin NVL72 Achieves up to 2× Blackwell Ultra Performance in MLPerf Training v6.1](https://developer.nvidia.com/blog/nvidia-vera-rubin-nvl72-achieves-up-to-2x-blackwell-ultra-performance-in-mlperf-training-v6-1/)** Technical deep-dive on the NVL72 rack-scale system: 2× Blackwell Ultra training speed, enabling faster model-agent co-iteration.

### Still unfolding

- **[Vyber07/cyber-security](https://huggingface.co/datasets/Vyber07/cyber-security)** · day 11
- **[nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B)** · day 9
- **[Zyphra/ZONOS3-Mini](https://huggingface.co/Zyphra/ZONOS3-Mini)** · day 5
- **[google/multimodal-knowledge-agent](https://huggingface.co/datasets/google/multimodal-knowledge-agent)** · day 3

[Read the full briefing](reports/2026-11-16-digest.md) · [Every edition](reports/README.md)

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
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43741470059) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43741547885) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/43756093189) | 🟢 ok | last run success |

Generated 2026-11-15 20:37 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
