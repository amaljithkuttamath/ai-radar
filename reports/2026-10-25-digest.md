<!-- radar:nav -->
`radar`  ·  [← 2026-10-24](2026-10-24-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-10-25

The strongest signals today center on training infrastructure and agent-oriented model architectures: Hugging Face Transformers and NVIDIA Megatron-LM remain the most widely adopted frameworks, while the Jeva and VideoJev papers (both on 8-day streaks) advance “System One” models that replace autoregressive decoding with structured decision heads. A new benchmark dataset (LocalLLaMA/typed-decisions) and NVIDIA’s Vietnamese persona corpus round out the high-signal releases. Twenty-two projects entered the radar for the first time, including vLLM, CopilotKit, and Graphiti.

## What changed

**New to radar**
- [vllm-project/vllm](https://github.com/vllm-project/vllm) — High-throughput, memory-efficient LLM inference and serving engine · 3/5
- [labmlai/annotated_deep_learning_paper_implementations](https://github.com/labmlai/annotated_deep_learning_paper_implementations) — 60+ annotated paper implementations (transformers, optimizers, RL, GANs) · 3/5
- [CopilotKit/CopilotKit](https://github.com/CopilotKit/CopilotKit) — Frontend stack for agents & generative UI (React, Angular, AG-UI protocol) · 3/5
- [getzep/graphiti](https://github.com/getzep/graphiti) — Real-time knowledge graphs for AI agents · 3/5
- [simstudioai/sim](https://github.com/simstudioai/sim) — Collaborative workspace to build, deploy, and monitor AI agents (100k+ builders) · 3/5

**Climbing**
- [nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets) (HF Dataset) — Simulation-ready 3D assets; traction rose to 4/5 (+1) · 4/5

**Cooled**
- [microsoft/AI-For-Beginners](https://github.com/microsoft/AI-For-Beginners) — 12-week curriculum; score slipped to 3/5 (−1) · 3/5

---

## Training

**[huggingface/transformers](https://github.com/huggingface/transformers)** · 4/5  
Model-definition framework for text, vision, audio, and multimodal models; 168k stars observed. Core dependency for most open-weight model work. Use when you need a unified API across architectures and hardware backends.

**[NVIDIA/Megatron-LM](https://github.com/NVIDIA/Megatron-LM)** · 4/5  
Ongoing research codebase for training transformer models at scale; 18k stars. Targets tensor/sequence/pipeline parallelism on GPU clusters. Relevant for teams building custom large-model training pipelines.

**[Jeva: System One Models from First Principles](https://arxiv.org/abs/2610.18773)** · 3/5  
[GitHub](https://github.com/LiQiiiii/Jeva) · [Project](https://liqiiiii.github.io/Jeva/)  
Proposes null-aware, permutation-invariant decision heads that replace answer decoding. 8-day streak, 177 stars, 436 HF upvotes. Read if you’re designing low-latency agents that must distinguish “no answer” from uncertainty.

---

## Qwen / Embedding Gemma

**[Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)** · 3/5  
27B image-text-to-text model (Apache-2.0); 18k likes, 7.8M downloads observed. Strong multimodal candidate for vision-language tasks needing open weights.

**[google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2)** · 3/5  
Sentence-transformers style embedding model; 2.9k likes, 213k downloads. Use for retrieval, clustering, or semantic search where a compact, high-quality embedder is needed.

---

## Other

**[LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions)** · 4/5  
Benchmark dataset for text classification (1K–10K samples, Apache-2.0); 246 likes, 44k downloads. Focus-matched for evaluation work; try it when you need a fresh classification benchmark with typed labels.

**[nvidia/Nemotron-Personas-Vietnam](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Vietnam)** · 4/5  
Vietnamese text-generation persona dataset (1M–10M samples, CC-BY-4.0, parquet, includes images); 222 likes, 20k downloads. Useful for multilingual persona conditioning or synthetic data generation.

**[VideoJev: System One Model for Video Understanding and Interaction](https://arxiv.org/abs/2610.18615)** · 3/5  
[GitHub](https://github.com/MCG-NJU/VideoJev) · [Project](https://mcg-nju.github.io/VideoJev/)  
Extends Jea’s System One paradigm to video: shared decision head over MLLM features for timely interaction. 8-day streak, 248 stars, 341 HF upvotes. Track if you build video-grounded agents that must act on streaming observations.

---

## Watch-list / Still developing

- [Bringing foundational models to the front lines of TB screening](https://research.google/blog/bringing-foundational-models-to-the-front-lines-of-tb-screening/) — Google Research blog; application note, no code artifact · 1/5
- [Rapidly scaling online storage to serve over 1 billion ChatGPT users (Part II)](https://openai.com/index/scaling-storage-one-billion-users-part-two) — OpenAI engineering blog on Habitat/Cosmos DB scaling · 1/5

---

## Action items

1. **Try** [vllm-project/vllm](https://github.com/vllm-project/vllm) for high-throughput LLM serving — it entered radar today and is production-hardened.
2. **Read** [Jeva](https://arxiv.org/abs/2610.18773) and [VideoJev](https://arxiv.org/abs/2610.18615) together — they define a coherent “System One” alternative to autoregressive agents.
3. **Track** [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) as a new classification benchmark; its traction (44k downloads) suggests community adoption.