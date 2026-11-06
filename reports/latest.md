<!-- radar:nav -->
`radar`  ·  [← 2026-11-05](2026-11-05-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-11-06

The strongest signals center on making models production-practical: NEO-VLA removes the visual encoder bottleneck for vision-language-action policies, Drex replaces autoregressive decoding with decision distributions to cut cost and latency, and Muir refines linear attention for constant-memory inference. Together they target the inference pipeline from perception to reasoning to memory. Coverage is limited to the past 48 hours and the scored candidate pool; many new GitHub repositories and datasets appeared but lack usable artifacts or traction evidence.

## What changed

**New to radar (290 items):** [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) (100+ AI agents and RAG apps), [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) (fast RAG framework), [VFlash: Fast, Accurate Visual Planning via Flash Primitive Decoding](https://arxiv.org/abs/2611.08449), [Towards Foundation Decision Models: Drex](https://arxiv.org/abs/2611.07854), [JuliaLang/julia](https://github.com/JuliaLang/julia), [paperless-ngx/paperless-ngx](https://github.com/paperless-ngx/paperless-ngx), [apache/airflow](https://github.com/apache/airflow), [MoreThought/Fable-5.1-Max-Reasoning-Filtered-10000x](https://huggingface.co/datasets/MoreThought/Fable-5.1-Max-Reasoning-Filtered-10000x), [WeThinkIn/AIGC-Interview-Book](https://github.com/WeThinkIn/AIGC-Interview-Book), [bones-studio/seed](https://huggingface.co/datasets/bones-studio/seed).

**Climbing (2):** [nvidia/Granary-v2](https://huggingface.co/datasets/nvidia/Granary-v2) (score +1), [codepawl/abo-glb](https://huggingface.co/datasets/codepawl/abo-glb) (score +1).

**Cooled (1):** [microsoft/AI-For-Beginners](https://github.com/microsoft/AI-For-Beginners) (score –1).

## Main list

### Cost & decision models
**[Towards Foundation Decision Models: Drex](https://arxiv.org/abs/2611.07854) · 3/5** — Family of open decision models (8B–35B) that return a probability distribution over user-supplied options instead of autoregressive decoding, targeting inconsistent answers, parsing overhead, and latency in production. GitHub: [nace-ai/drex-decision-models](https://github.com/nace-ai/drex-decision-models). Use when you need structured, verifiable choices without chain-of-thought cost.

**[Terminal-style Mathematical Modeling Bench](https://arxiv.org/abs/2611.08237) · 2/5** — TB-MathModel makes 18 real contest modeling problems agentic and verifiable in a terminal environment, checking both solution credibility and physical feasibility. GitHub: [wxj630/terminal-bench-math-modeling](https://github.com/wxj630/terminal-bench-math-modeling). Use to evaluate end-to-end mathematical reasoning agents.

**[LeanContext: Disentangling Mathematical Resources in Lean Whole-Proof Generation](https://arxiv.org/abs/2611.08277) · 2/5** — Benchmark of 129,826 Lean problems separating Mathematical Context from Environment Context to measure retrieval advantage in theorem proving. Use for neural theorem-proving retrieval research.

### Perception & action
**[From Pixels to Actions - Towards Native Vision-Language-Action Policies](https://arxiv.org/abs/2611.06918) · 4/5** — NEO-VLA introduces an encoder-free VLA framework where images are tokenized by lightweight patch embeddings, letting action reasoning access evolving visual computation directly. Project: [lmms-lab.com/posts/neo_vla](https://www.lmms-lab.com/posts/neo_vla/). Use for manipulation tasks where local geometry and subtle state changes matter.

### Throughput & attention
**[Muir: Linear Attention with Sensitivity-Allocated Gating and Matched-Filter Readout](https://arxiv.org/abs/2611.08376) · 2/5** — Shows erase gates in gated delta-rule models can be simplified because state updates are far less sensitive to erasure than to writes; yields a linear attention variant with constant-memory inference and reduced gating overhead. Use when optimizing long-context inference throughput.

### Evaluation & embeddings
**[On the limitations of molecular representations](https://arxiv.org/abs/2611.08420) · 2/5** — Systematic investigation finding no state-of-the-art molecular embedding captures graph structure, 3D shape, or ADMET similarity better than simple fingerprints across diverse cheminformatics tasks. Use to ground embedding choices in molecular ML pipelines.

### Core frameworks & data
**[huggingface/transformers](https://github.com/huggingface/transformers) · 4/5** — Model-definition framework for text, vision, audio, and multimodal models; 168.6k stars observed. The de facto standard for loading, training, and deploying transformer architectures.

**[nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets) · 4/5** — CC-BY-4.0 dataset of simulation-ready 3D assets; 1.37M downloads, 1.44k likes observed. Use for Omniverse, robotics sim, and synthetic data generation.

### Models
**[Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) · 3/5** — Multimodal image-text-to-text model (Apache-2.0); 19.3k likes, 7.8M downloads observed. Use for vision-language tasks needing open weights.

**[deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) · 3/5** — Multimodal model (MIT license); 5.3k likes, 259k downloads observed. Use for fast image-text reasoning with open weights.

## Watch-list / Still developing

**Carryovers with sustained traction (STORY ARCS):**
- [WeVisOne-VL: Unified Visual Perception from Objects to Pixels](https://arxiv.org/abs/2610.31329) — streak 14, +36% traction; GitHub: [Tencent/WeVisOne-VL](https://github.com/Tencent/WeVisOne-VL)
- [Intrinsic Distribution Matching](https://arxiv.org/abs/2610.39633) — streak 8, +13% traction; GitHub: [inclusionAI/IDM](https://github.com/inclusionAI/IDM)
- [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) — streak 13, +9% traction
- [google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2) — streak 13, +1% traction
- [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) — streak 13, persistent agent memory across sessions
- [morluto/rea](https://github.com/morluto/rea) — streak 11, reverse engineering with agents
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — streak 13, codebase-to-knowledge-graph skill
- [rohitg00/ai-engineering-from-scratch](https://github.com/rohitg00/ai-engineering-from-scratch) — streak 13, learn-by-building curriculum
- [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) — streak 9, agent memory that learns

**Other tracked items:**
- [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) — 12-week ML curriculum, 92k stars
- [Vyber07/cyber-security](https://huggingface.co/datasets/Vyber07/cyber-security) — small cybersecurity QA dataset
- [The Wizard of Open Weights: Chris Alexiuk Makes AI Easy With Open Models](https://blogs.nvidia.com/blog/nvidia-life-chris-alexiuk/) — NVIDIA engineer advocacy for open models
- [Vera Delivers the Best of Both Worlds: Highest Throughput and Fastest Agents](https://blogs.nvidia.com/blog/vera-cpu-highest-throughput-fastest-agents/) — NVIDIA Vera CPU for agent workloads

## Action items

**Read:** [NEO-VLA project page](https://www.lmms-lab.com/posts/neo_vla/) — encoder-free VLA design and patch tokenization details for vision-language-action research.

**Try:** [Drex decision models](https://github.com/nace-ai/drex-decision-models) — swap autoregressive decoding for option-distribution outputs in a production classifier or router to measure latency and consistency gains.

**Track:** [Muir linear attention](https://arxiv.org/abs/2611.08376) — watch for reference implementation release; the simplified erase-gate design could integrate into existing linear attention kernels for long-context serving.