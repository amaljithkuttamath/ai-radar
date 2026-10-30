<!-- radar:nav -->
`radar`  ·  [← 2026-10-29](2026-10-29-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-10-30

Microsoft's Qlib quant platform enters the radar with integrated RD-Agent automation, while NVIDIA releases two simulation-ready datasets (SimReady assets and Vietnamese Nemotron personas) showing strong download traction. Distillation research advances with Intrinsic Distribution Matching and token-level multi-teacher self-distillation, and carryover papers on unified vision (WeVisOne-VL) and future-aware video generation (Looking Ahead) continue climbing over 7–8 consecutive days.

## What changed

**New to radar**
- [microsoft/qlib](https://github.com/microsoft/qlib) — AI-oriented Quant investment platform with RD-Agent automation · 4/5
- [Intrinsic Distribution Matching](https://arxiv.org/abs/2610.39633) — reverse-KL decomposition for few-step diffusion distillation · 3/5
- [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) — Simple and fast retrieval-augmented generation · 3/5
- [Youtu-Parsing-Omni: One Encoder, One Schema, All Modalities](https://arxiv.org/abs/2610.39301) — unified multimodal parsing · 3/5
- [rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch) — step-by-step ChatGPT-like LLM in PyTorch · 3/5

**Cooled**
- [microsoft/autogen](https://github.com/microsoft/autogen) — agentic AI framework, score dropped from 4 to 3 · 3/5

## Main list

### Modeling
- **[microsoft/qlib](https://github.com/microsoft/qlib)** — Qlib is an AI-oriented Quant investment platform that aims to use AI tech to empower Quant Research, from exploring ideas to implementing productions. Qlib supports diverse ML modeling paradigms, including supervised learning, market dynamics modeling, and RL, and is now equipped with https://github.com/microsoft/RD-Agent to automate R&D process. · 4/5
- **[Looking Ahead: Modeling Future Evolution in Autoregressive Video Generation](https://arxiv.org/abs/2610.29989)** — introduces Future Chunk Prediction (FCP) auxiliary task to force autoregressive video diffusion models to model scene evolution rather than rely on temporal redundancy. Code at TencentARC/Looking-Ahead. Carryover, streak 8. · 3/5

### Dataset
- **[nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets)** — CC-BY-4.0 licensed 3D assets for simulation workloads; 881K downloads and 1K likes observed. · 4/5
- **[nvidia/Nemotron-Personas-Vietnam](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Vietnam)** — Vietnamese persona dataset for text generation (1M–10M samples, Parquet, image modality); 23K downloads observed. · 4/5

### Qwen / DeepSeek Models
- **[Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)** — 27B multimodal model (image-text-to-text, Apache-2.0); 7.6M downloads and 18.8K likes observed. · 3/5
- **[deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)** — Flash model (image-text-to-text, MIT); 145K downloads, 3.9K likes. Carryover, streak 6. · 3/5

### Distillation
- **[Intrinsic Distribution Matching](https://arxiv.org/abs/2610.39633)** — decomposes reverse-KL into Gaussian moment component and non-Gaussian residual; improves few-step text-to-image generation. Code at inclusionAI/IDM. · 3/5
- **[Every Token Needs Its Own Teacher: Multi-teacher Adaptive On-policy Self-distillation](https://arxiv.org/abs/2610.40574)** — argues teacher preference varies token-by-token; proposes per-token teacher adaptation in on-policy self-distillation. · 2/5

### Other
- **[huggingface/transformers](https://github.com/huggingface/transformers)** — core model-definition framework for text, vision, audio, and multimodal models; 168K stars observed. · 4/5
- **[WeVisOne-VL: Unified Visual Perception from Objects to Pixels](https://arxiv.org/abs/2610.31329)** — unifies object-level and pixel-level perception (detection, segmentation, OCR, matting) via structured next-token prediction. Tencent repo at Tencent/WeVisOne-VL. Carryover, streak 7. · 3/5
- **[Read, Allocate, Route: Role-Coupled Tokenization for Pixel-Space Generative Transformers](https://arxiv.org/abs/2610.40647)** — SpecSlot decouples output detail from global attention length by expanding spatial anchors into multiple slots with routed attention. Code at JiongfanYang/SpecSlot. · 2/5

## Watch-list / Still developing

- [SolarRenderer: Few-Step Generative Reference Rendering](https://arxiv.org/abs/2610.28630) — streak 9, traction +85%
- [Sage-A1.5: From Long-Horizon Execution to Scientific Exploration](https://arxiv.org/abs/2610.28578) — streak 9, traction +83%
- [Learning the 4D World through Point Trajectory Forecasting](https://arxiv.org/abs/2610.28594) — streak 9, traction +59%
- [DONIC: Generalist Dexterous Bimanual Tracking Control](https://arxiv.org/abs/2610.29997) — streak 8, traction +53%
- [S-Agent 2.0: Spatial Reasoning with a General Coding Agent](https://arxiv.org/abs/2610.28354) — streak 9, traction +47%
- [Making MLLM Latents Matter: Factor-Aware Predictive Learning](https://arxiv.org/abs/2610.30926) — streak 7, traction +15%
- [Elucidating the Design Space of LM Data Attribution](https://arxiv.org/abs/2610.40655) — CATT benchmark for fact tracing with synthetic ground truth · 2/5
- [Luggage re-identification: A study of strategies towards a real-world application](https://arxiv.org/abs/2610.40643) — real-world ReID benchmark with occlusions and clutter · 2/5
- [Framework-Conditional Open Materials Generation](https://arxiv.org/abs/2610.40443) — materials generation conditioned on structural frameworks · 2/5
- [microsoft/autogen](https://github.com/microsoft/autogen) — agentic AI framework, cooled this window · 3/5

## Action items

- **Try:** [microsoft/qlib](https://github.com/microsoft/qlib) with [RD-Agent](https://github.com/microsoft/RD-Agent) for automated quant research workflows — the platform now ships end-to-end R&D automation.
- **Read:** [Intrinsic Distribution Matching](https://arxiv.org/abs/2610.39633) and its [code](https://github.com/inclusionAI/IDM) — the Gaussian-moment decomposition offers a principled path for few-step diffusion distillation.
- **Track:** [WeVisOne-VL](https://arxiv.org/abs/2610.31329) and [Looking Ahead](https://arxiv.org/abs/2610.29989) — both carryovers on 7–8 day streaks with rising traction; watch for model releases or benchmark updates.