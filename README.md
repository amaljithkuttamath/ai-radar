# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Tue 24 Nov

> A wave of new robotics and embodied-AI benchmarks arrived together: Embo-Harness, WorldLeague, 3AGameFactory-Motion, and World Models as Native Latent Action Models all frame frontier multimodal models as closed-loop policies. Meanwhile WeMM-Ecom demonstrates a full-size MoE family tuned for e-commerce multimodal tasks, and NVIDIA published a local deployment guide for Cosmos 3. Coverage is broad but shallow — most items are preprints or announcements without independent replication.

- **[Embo-Harness: Towards Understanding Frontier-Model-as-Policy Harness](https://arxiv.org/abs/2611.31201)** Researchers from DravenALG released a framework that systematically evaluates how frontier multimodal models perform as robot policies, dissecting prompting, planning, action exec…
- **[WorldLeague: Benchmarking Physical Agency](https://arxiv.org/abs/2611.30989)** A new benchmark with 60 simulated robot tasks measures autonomous progress toward physical goals, covering perception, memory, planning, and action in a unified WorldSim environme…
- **[WeMM-Ecom: Advancing Multimodal Content Understanding for WeChat E-Commerce](https://arxiv.org/abs/2611.30662)** Tencent introduced a five-model family (0.8B dense to 35B MoE) trained with continued pre-training on e-commerce data and hybrid-thinking post-training, claiming SOTA general perf…
- **[3AGameFactory-Motion: Agentic Rigging and Reliable Complex Motion Generation for Diverse 3D Assets](https://arxiv.org/abs/2611.30013)** OpenDCAI released DivDynBench evaluating rigging and motion generation across six morphology categories with multi-phase constraints, comparing specialized motion, video-to-motion…
- **[World Models as Native Latent Action Models](https://arxiv.org/abs/2611.30898)** PAW Team showed that pretrained video world models can serve as latent action models by extracting inverse/forward dynamics from their internal representations, avoiding separate…
- **[Why Does Voice AI Still Struggle With Kenyans' Speech?](https://spectrum.ieee.org/swahili-speech-recognition)** IEEE Spectrum reports that Swahili ASR works on read speech but fails on code-switched Sheng dialects, highlighting a persistent gap between benchmark and real-world performance.

### Still unfolding

- **[Vyber07/cyber-security](https://huggingface.co/datasets/Vyber07/cyber-security)** · day 19
- **[Voxtral 3](https://mistral.ai/news/voxtral-3/)** · day 11
- **[Introducing Timestral](https://mistral.ai/news/timestral/)** · day 11
- **[FEATURED](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/)** · day 11

[Read the full briefing](reports/2026-11-24-digest.md) · [Every edition](reports/README.md)

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
