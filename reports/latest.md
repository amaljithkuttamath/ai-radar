<!-- radar:nav -->
`radar`  ·  [← 2026-10-23](2026-10-23-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-10-24

Intel’s Neural Compressor now supports INT8/FP8/MXFP8/INT4/MXFP4/NVFP4 quantization across PyTorch, TensorFlow, and ONNX Runtime, making it the broadest low-bit LLM compression toolkit observed. Two new benchmark datasets — MMLU-Pro (259k downloads) and LocalLLaMA/typed-decisions — extend evaluation coverage for reasoning and structured decision tasks. The Transformers library remains the most-starred artifact in this window (168k stars), though its current push is a routine version bump rather than a feature release.

## What changed

**New to radar**
- [intel/neural-compressor](https://github.com/intel/neural-compressor) — SOTA low-bit LLM quantization (INT8/FP8/MXFP8/INT4/MXFP4/NVFP4) & sparsity · 4/5
- [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) — benchmark dataset for text-classification decisions · 4/5
- [huggingface/transformers](https://github.com/huggingface/transformers) — model-definition framework for text, vision, audio, multimodal · 4/5
- [microsoft/AI-For-Beginners](https://github.com/microsoft/AI-For-Beginners) — 12-week, 24-lesson AI curriculum · 4/5
- [NVIDIA/Megatron-LM](https://github.com/NVIDIA/Megatron-LM) — ongoing research training transformer models at scale · 4/5

**Climbing**
- [Retrieval Augmented Generation Compositionality](https://arxiv.org/abs/2610.29722) — compositionality analysis for RAG systems · 3/5 (+1)
- [nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets) — simulation-ready 3D asset dataset · 3/5 (+1)

**Cooled**
- [RIDAR: Safeguarding Research Integrity in Autonomous Research Agents](https://arxiv.org/abs/2610.31372) — automated detection/runtime intervention for research integrity violations · 2/5
- [What Makes a Good Unmasking Policy?](https://arxiv.org/abs/2610.31576) — controlled study of learned unmasking in diffusion language models · 0/5
- [FlashVSR+: Efficient Video Super-Resolution](https://arxiv.org/abs/2610.17552) — hybrid attention and reward-yield distribution matching · 3/5 (−1)
- [JevGPT: Thinking Fast and Slow in Autonomous Research](https://arxiv.org/abs/2610.18272) — dual-system agent for research tasks · 3/5 (−1)
- [Beyond Watching and Searching: Benchmarking Agents for Video-centered Deep Research](https://arxiv.org/abs/2610.31158) — video-agent benchmark · 2/5 (−1)

## Main list

### Quantization & compression
- [intel/neural-compressor](https://github.com/intel/neural-compressor) — Unified API for INT8/FP8/MXFP8/INT4/MXFP4/NVFP4 quantization and sparsity on PyTorch, TensorFlow, ONNX Runtime. Engineers deploying LLMs on Intel CPUs/GPUs or exporting to ONNX can drop this in for post-training quantization and quantization-aware training. · 4/5

### Benchmarks & evaluation
- [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) — Small (46k downloads) Apache-2.0 dataset for structured decision classification; useful for evaluating agent routing or function-calling accuracy. · 4/5
- [TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) — Expanded MMLU benchmark (259k downloads, MIT) with harder reasoning tasks; standard for comparing foundation-model reasoning. Carryover (8 runs, slight traction rise). · 4/5
- [AgentPhishing: A Benchmark of LLM Email Agents Under Adaptive Attack](https://arxiv.org/abs/2610.31404) — Evaluates computer-use agents against persuasive phishing emails; includes adaptive attack trajectories. Relevant for security hardening of email/automation agents. · 2/5

### Frameworks & libraries
- [huggingface/transformers](https://github.com/huggingface/transformers) — Core model-definition library (168k stars). Current push updates version tags and model cards; no new architecture. Use for loading any HF-hosted model. · 4/5

### System One / fast decision models
- [VideoJev: System One Model for Video Understanding and Interaction](https://arxiv.org/abs/2610.18615) — Adapts MLLMs to structured video decisions via a shared head, replacing autoregressive decoding. Repo and demo linked. Carryover (7 runs, strong traction rise). · 3/5
- [Jeva: System One Models from First Principles](https://arxiv.org/abs/2610.18773) — Formalizes null-aware, permutation-invariant decision heads; GitHub + project page. Carryover (7 runs, strong traction rise). · 3/5

### Models
- [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) — 27B image-text-to-text model (Apache-2.0, 7.7M downloads). Suitable for multimodal chat and visual reasoning; runs on 2×A100 or quantized on consumer GPUs. · 3/5
- [google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2) — Lightweight embedding model (193k downloads) for sentence-transformers pipelines; drop-in for retrieval or clustering. · 3/5

### Attention & sequence compression
- [Rethinking Sequence Compression with Test-time Regression](https://arxiv.org/abs/2610.31574) — TTR-Compressor learns a regression head whose closed-form coefficients compress token sequences end-to-end. Repo + project page. Could replace pooling in long-context or RAG pipelines. · 2/5

## Watch-list / Still developing

- [When to Follow the Teacher: Advantage-Based On-Policy Distillation](https://arxiv.org/abs/2610.31563) — AOPD weights teacher actions by counterfactual student advantage; code linked. · 2/5
- [Parameter-Efficient Adaptation … for the Bashkir Language](https://arxiv.org/abs/2610.31397) — Corpus (46.9M tokens), datasets, and benchmark across 8 architectures (82M–8B) with QLoRA/ICL. · 2/5
- [RIDAR: Safeguarding Research Integrity in Autonomous Research Agents](https://arxiv.org/abs/2610.31372) — Taxonomy of 14 research integrity violations + runtime detector (85.2% F1). Cooled this run. · 2/5
- [SurveyGraph: Generating Academic Surveys via Methods-Entity Knowledge Graphs](https://arxiv.org/abs/2610.31317) — MEKG for structured survey generation; retrieval/outlining/generation components. · 2/5
- [Jeva / VideoJev](https://github.com/LiQiiiii/Jeva) — Carryovers with 7-run streaks and rising traction (Δ≈3.5); track if System One paradigm gains adoption. · 3/5
- [Multimodal Embodied Agents: A Unified Capability-centric Perspective](https://arxiv.org/abs/2610.30108) — 3-run streak, 94% magnitude rise; survey linking computer-use to robot-use. · (story arc)
- [Multimodal Reranking Is a System One Decision](https://arxiv.org/abs/2610.28435) — 4-run streak, 87% magnitude rise; argues reranking is fast heuristic, not slow reasoning. · (story arc)

## Action items

1. **Try** [intel/neural-compressor](https://github.com/intel/neural-compressor) — quantize a 7B–70B model to INT4/MXFP4 on your target hardware (CPU, GPU, or ONNX Runtime) and measure latency/accuracy trade-off against your current pipeline.
2. **Read** [Rethinking Sequence Compression with Test-time Regression](https://arxiv.org/abs/2610.31574) — if you hit context-window or RAG-token budgets, the TTR-Compressor repo offers a drop-in alternative to mean/max pooling with learned compression.
3. **Track** [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) and [AgentPhishing](https://arxiv.org/abs/2610.31404) — both expand evaluation for agent routing and security; add to your CI benchmark suite when they stabilize.