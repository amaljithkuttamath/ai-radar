<!-- radar:nav -->
`radar`  ·  [← 2026-10-31](2026-10-31-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-11-01

Two major open-source frameworks anchor this window: Hugging Face Transformers (168k stars observed) remains the central model-definition library across text, vision, and audio, while Microsoft's ML-For-Beginners (92k stars) reappears as a comprehensive 12-week curriculum. NVIDIA's SimReady assets dataset (1.1M downloads observed) and a new wave of agentic models — notably Sage-A1.5's capability-composition architecture and Qwen/DeepSeek multimodal releases — signal continued investment in long-horizon agents and simulation-ready data. Coverage is limited to the 8 scored items in this 48-hour window.

## What changed

**New to radar (18)**  
- [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) — 12-week ML curriculum  
- [Tencent/WeKnora](https://github.com/Tencent/WeKnora) — Open-source LLM knowledge platform for RAG and agents  
- [getzep/graphiti](https://github.com/getzep/graphiti) — Real-time knowledge graphs for AI agents  
- [ComposioHQ/composio](https://github.com/ComposioHQ/composio) — 1000+ toolkits and sandboxed workbench for agents  
- [EvolvingLMMs-Lab/lmms-eval](https://github.com/EvolvingLMMs-Lab/lmms-eval) — Multimodal evaluation toolkit  
… and 13 more.

**Climbing (1)**  
- [codepawl/simready-glb](https://huggingface.co/datasets/codepawl/simready-glb) — Dataset traction rising (mag_delta +0.55)

**Cooled (6)**  
- [Intrinsic Distribution Matching](https://arxiv.org/abs/2610.39633) — mag_delta –2.25  
- [WeVisOne-VL: Unified Visual Perception from Objects to Pixels](https://arxiv.org/abs/2610.31329) — mag_delta –1.66  
- [DONIC: Generalist Dexterous Bimanual Tracking Control from Human Demonstrations](https://arxiv.org/abs/2610.29997) — mag_delta –1.05  
- [Making MLLM Latents Matter: Factor-Aware Predictive Learning for Cinematic Video Generation](https://arxiv.org/abs/2610.30926) — mag_delta –0.98  
- [Looking Ahead: Modeling Future Evolution in Autoregressive Video Generation](https://arxiv.org/abs/2610.29989) — mag_delta –0.62  
… and 1 more.

## Main list

### Machine
**[huggingface/transformers](https://github.com/huggingface/transformers)** — The core model-definition framework for text, vision, audio, and multimodal models, used for both inference and training. 168k GitHub stars observed. · 4/5

**[microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners)** — 12-week, 26-lesson classic ML curriculum with 52 quizzes. 92k stars observed; new to radar this window. · 4/5

### Qwen & DeepSeek multimodal models
**[Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)** — Image-text-to-text model (Apache 2.0), 18.9k HF likes, 7.9M downloads observed. Published Aug 2026. · 3/5

**[deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)** — Image-text-to-text model (MIT), 4.2k HF likes, 170k downloads observed. Published Oct 2026; tracked 8 consecutive days with rising traction. · 3/5

### Other
**[nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets)** — CC-BY-4.0 simulation-ready 3D assets dataset; 1.1M downloads, 1.1k likes observed. Published Oct 29. · 4/5

**[Sage-A1.5: From Long-Horizon Execution to Scientific Exploration with Capability Composition](https://arxiv.org/abs/2610.28578)** — 35B MoE agentic model with adaptive capability composition for long-horizon problem solving; agentic orchestration, verification, and self-correction. GitHub: [InternScience/Agents-A1](https://github.com/InternScience/Agents-A1), Project: [Sage-A1.5](https://alpha-innovator.github.io/Sage-A1.5/). 607 stars, 72 HF upvotes; tracked 11 runs, traction rising. · 3/5

**[Looking Ahead: Modeling Future Evolution in Autoregressive Video Generation](https://arxiv.org/abs/2610.29989)** — Introduces Future Chunk Prediction (FCP) auxiliary task to model scene evolution in autoregressive video diffusion. GitHub: [TencentARC/Looking-Ahead](https://github.com/TencentARC/Looking-Ahead), Project: [looking-ahead](https://hellorpg.github.io/looking-ahead/). 186 stars, 84 HF upvotes; tracked 10 runs, though traction cooled this window (mag_delta –0.62). · 3/5

**[secemp9/arxiv-complete](https://huggingface.co/datasets/secemp9/arxiv-complete)** — 100M–1B record arXiv dataset (Parquet) for text generation/retrieval; 164k downloads, 784 likes observed. Published Sep 2026. · 3/5

## Watch-list / Still developing

- [Multimodal Embodied Agents: A Unified Capability-centric Perspective](https://arxiv.org/abs/2610.30108) — 10-day streak, 103.6% mag increase  
- [SolarRenderer: Few-Step Generative Reference Rendering](https://arxiv.org/abs/2610.28630) — 11-day streak, 84.7% mag increase  
- [Learning the 4D World through Point Trajectory Forecasting](https://arxiv.org/abs/2610.28594) — 11-day streak, 57.6% mag increase  
- [DONIC: Generalist Dexterous Bimanual Tracking Control from Human Demonstrations](https://arxiv.org/abs/2610.29997) — 10-day streak, 30.7% mag increase (also cooled this window)  
- [WeVisOne-VL: Unified Visual Perception from Objects to Pixels](https://arxiv.org/abs/2610.31329) — 9-day streak, 30.2% mag increase (also cooled this window)  
- [S-Agent 2.0: Spatial Reasoning with a General Coding Agent](https://arxiv.org/abs/2610.28354) — 11-day streak, 24.7% mag increase (also cooled this window)  
- [google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2) — 8-day streak, 0.8% mag increase  

## Action items

1. **Try**: [Sage-A1.5](https://arxiv.org/abs/2610.28578) agentic orchestration codebase ([InternScience/Agents-A1](https://github.com/InternScience/Agents-A1)) for long-horizon task decomposition — the capability-composition approach is actively climbing.  
2. **Read**: [Looking Ahead](https://arxiv.org/abs/2610.29989) FCP auxiliary task for autoregressive video — relevant if building video generation pipelines, though traction cooled this window.  
3. **Track**: [nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets) dataset for simulation-ready 3D assets — 1.1M downloads suggest strong adoption for embodied AI / sim-to-real work.