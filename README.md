# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Thu 19 Nov

> Frontier labs shipped a wave of agent-facing tooling: OpenAI published a measurement of coding-agent acceleration, NVIDIA released a Rust parser for fragmented tool calls, and Google added tool retrieval to the Gemini API. At the same time, two high-signal research artifacts arrived — Game2Player, a co-development loop that scales verifiable gameplay for visual agents, and Jeveration, which extends single-pass “System One” decision models to image generation. A cluster of new benchmarks and safety probes rounds out the day.

- **[Game2Player: Scaling Gameplay Experience for Visual Agents through Environment-Player Co-Development](https://arxiv.org/abs/2611.24154)** A Builder agent adapts web games, exposes internal state, and a Player agent learns from the resulting verifiable trajectories — producing a scalable dataset of perception, planni…
- **[Research acceleration: The jagged frontier](https://openai.com/index/research-acceleration-jagged-frontier)** OpenAI measures how coding agents accelerate AI research, mapping where performance is strong and where it remains uneven — a signal for recursive self-improvement trajectories.
- **[Build Tool-Calling Parsers in Rust with AI Agents](https://developer.nvidia.com/blog/build-tool-calling-parsers-in-rust-with-ai-agents/)** NVIDIA demonstrates a frontend parser that handles fragmented, truncated, or markup-leaking tool calls — turning messy model output into structured invocations.
- **[Introducing Tool Retrieval in the Gemini API](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-tool-retrieval/)** Google adds a tool-retrieval endpoint so models can fetch and invoke tools dynamically rather than stuffing all definitions into context.
- **[Jeveration: System One Models Now Generate](https://arxiv.org/abs/2611.24738)** The Jev decision model is repurposed for single-pass image generation by conditioning parallel predictions on a shared random state, achieving global consistency without iterative…
- **[Why a Computer Scientist Thinks Superintelligence Won't Happen](https://spectrum.ieee.org/ai-superintelligence-debate)** IEEE Spectrum profiles a researcher arguing that current scaling paths miss qualitative gaps — useful framing for benchmark design and capability forecasting.

### Still unfolding

- **[leostera/git-twig — lightweight git-worktrees for agents](https://github.com/leostera/git-twig)** · day 3
- **[sensenova/SenseNova-Loop-9B (HF Model)](https://huggingface.co/sensenova/SenseNova-Loop-9B)** · day 3

[Read the full briefing](reports/2026-11-19-digest.md) · [Every edition](reports/README.md)

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
