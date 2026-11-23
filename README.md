# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Mon 23 Nov

> NVIDIA shipped a GPU-accelerated DuckDB extension (Sirius Core) while OpenAI and DeepMind published agent case studies — one automating half of customer support in 30 days, another finding faster quantum algorithms. Ladybird delivered its first alpha browser build, and the Jensen Huang CEO reversal drove the day's largest community discussion.

- **[Get Started with GPU-Accelerated DuckDB Analytics Using the Sirius Core Extension](https://developer.nvidia.com/blog/get-started-with-gpu-accelerated-duckdb-analytics-using-the-sirius-core-extension/)** NVIDIA released the Sirius Core extension to run DuckDB analytical queries on GPUs.
- **[Accelerating Direct Sparse Solvers for Computational Engineering with NVIDIA cuDSS 1.0](https://developer.nvidia.com/blog/accelerating-direct-sparse-solvers-for-computational-engineering-with-nvidia-cudss-1-0/)** NVIDIA launched cuDSS 1.0, a direct sparse solver library for structural mechanics, CFD, and circuit simulation on GPUs.
- **[Merry Making: Play, Build and Create With NVIDIA Technologies This Holiday Season](https://blogs.nvidia.com/blog/nvidia-technologies-holidays-2026/)** NVIDIA published a holiday-roundup of hobby projects using its SDKs and hardware.
- **[Richpanel helps companies automate 50% of support in 30 days](https://openai.com/business/customer-stories/richpanel-ai-customer-support)** OpenAI detailed how Richpanel uses GPT-6 Astra, Sol, and Luna to equip AI support agents with tools, procedures, and conversation handling.
- **[Finding faster quantum algorithms with agents and formal verification](https://deepmind.google/blog/finding-faster-quantum-algorithms-with-agents-and-formal-verification/)** DeepMind applied agent teams with formal verification to improve quantum algorithms for fusion and chemistry.
- **[Supercharging transformer residual connections](https://research.google/blog/supercharging-transformer-residual-connections/)** Google Research published a theory-focused post on modified residual connections.

### Still unfolding

- **[Sage S2.1 Flash Technical Report](https://arxiv.org/abs/2611.21072)** · day 7
- **[TeleChat to Xing4: Advancing Frontier Agentic Models on Domestic Chips](https://arxiv.org/abs/2611.22115)** · day 6
- **[Jeveration: System One Models Now Generate](https://arxiv.org/abs/2611.24738)** · day 5
- **[HuggingFaceFW/fineweb-edu](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu)** · day 4

[Read the full briefing](reports/2026-11-23-digest.md) · [Every edition](reports/README.md)

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
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45053461925) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45053523999) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45069043222) | 🟢 ok | last run success |

Generated 2026-11-22 21:20 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
