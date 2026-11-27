# AI Radar

What changed in AI, in plain words. A new edition every morning, ranked by what is new and
what matters, with every link checked against its source.

[Read on the web](https://amaljithkuttamath.github.io/radar/) · [Every edition](reports/README.md)

<!-- frontpage:start -->

**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)

### New in the last two days · Fri 27 Nov

> The strongest signal today is the **Mixture-of-Loops Transformer (MoLT)** paper with open code, which has accumulated 97 GitHub stars and 74 HF upvotes in two days while proposing a new attention-memory mechanism for looped architectures. Also notable: a Vulkan-accelerated **waifu2x Windows upscaler** hit 171 stars on its first day. Coverage is broad but shallow — most items are early repos or preprints without independent verification.

- **[Red2076-arch/waifu2x-image-upscaler-windows](https://github.com/Red2076-arch/waifu2x-image-upscaler-windows)** A free Windows image upscaler and photo denoiser using Vulkan GPU acceleration and ncnn neural networks, released today with 171 stars.
- **[I don't expect superposition in transformer MLP neurons](https://www.alignmentforum.org/posts/o9dPGxEbpQrnasgDB/i-don-t-expect-superposition-in-transformer-mlp-neurons)** An Alignment Forum post arguing that superposition-type compression occurs in the residual stream, not in MLP neurons, with a proposed experimental test.
- **[I'm Scared of AI](https://thesoapbox.email/archive/3)** A personal essay on AI anxiety that hit 175 points and 182 comments on Hacker News, reflecting practitioner sentiment.
- **[GPT 6.2 Astra Solves a Historical Mystery](https://generativehistory.substack.com/p/gpt-62-astra-solves-a-historical)** A Substack post claiming GPT-6.2 resolved a historical question, drawing 154 HN points and 63 comments.
- **[ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF)** A quantized (GSQ, RCO) GGUF model from ISTA-DASLab with 224 likes and 24.9k downloads observed.
- **[yurun-chen/EgoUseBench](https://huggingface.co/datasets/yurun-chen/EgoUseBench)** A new Hugging Face dataset (41 likes, 78 downloads) tagged as a computer-use benchmark with arXiv:2611.34466.

### Still unfolding

- **[Mistral Voxtral 3](https://mistral.ai/news/voxtral-3/)** · day 14
- **[Mistral Timestral](https://mistral.ai/news/timestral/)** · day 14
- **[Meta Muse Spark model API](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/)** · day 14
- **[Meta Genesis mission with Segment Anything/DINO](https://ai.meta.com/blog/genesis-mission-lawrence-berkeley-national-laboratory-segment-anything-dino/)** · day 14

[Read the full briefing](reports/2026-11-27-digest.md) · [Every edition](reports/README.md)

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
| [Daily digest](https://github.com/amaljithkuttamath/ai-radar/blob/main/reports/latest.md) | 🟢 ok | last digest committed 4h ago |
| [Model synthesis](https://github.com/amaljithkuttamath/ai-radar/blob/main/reports/latest.md) | 🟢 ok | latest digest carries model synthesis |
| [Eval loop](https://github.com/amaljithkuttamath/ai-radar/blob/main/evals/latest.json) | 🟡 warn | grader last committed 4h ago · tier 0 only, no model judgement |
| [Self-healing loop](https://github.com/amaljithkuttamath/ai-radar/issues?q=is%3Aissue+is%3Aopen+label%3Awatchdog) | 🟢 ok | no unanswered alarms |
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45887265557) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45887333571) | 🟢 ok | last run success |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/45910986419) | 🟢 ok | last run success |

Generated 2026-11-27 00:06 UTC by `scripts/health.py`.

<!-- health:end -->

</details>

**For developers:** [run it, configure it, change it](docs/developing.md) ·
[architecture and failure behavior](docs/architecture.md) ·
[independent evaluation](evals/latest.json)
