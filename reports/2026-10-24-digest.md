<!-- radar:nav -->
`radar`  ·  [← 2026-10-23](2026-10-23-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-10-24

The strongest signals today are practical tooling for model compression and new evaluation benchmarks. Intel’s neural-compressor adds MXFP4/NVFP4 quantization paths with PyTorch, TensorFlow, and ONNX Runtime support, while the LocalLLaMA/typed-decisions dataset introduces a structured benchmark for decision-making tasks. Coverage is limited to the past 48 hours; no major model releases appeared in this window.

## What changed
No new, climbing, or cooled items detected since the previous run.

## Main list

### Benchmark
**[LocalLLaMA/typed-decisions (HF Dataset)](https://huggingface.co/datasets/LocalLLaMA/typed-decisions)** — A decision-focused benchmark with 1K–10K English samples, tagged for text-classification and official eval YAML. Useful for teams building or evaluating agents that must choose among structured options. · 4/5

**[AgentPhishing: A Benchmark of LLM Email Agents Under Adaptive Attack](https://arxiv.org/abs/2610.31404)** — Evaluates computer-use agents against persuasive phishing requests in email workflows. Targets a gap left by conventional phishing datasets. Relevant for security teams hardening agent deployments. · 2/5

**[Parameter-Efficient Adaptation of LLMs to a Low-Resource Agglutinative Language: Bashkir Benchmark](https://arxiv.org/abs/2610.31397)** — Corpus (46.9M tokens), three classification datasets, and a reproducible benchmark across eight architectures (82M–8B) testing full FT, QLoRA, and in-context learning. Useful for multilingual adaptation research. · 2/5

**[RIDAR: Safeguarding Research Integrity in Autonomous Research Agents](https://arxiv.org/abs/2610.31372)** — Taxonomy of 14 research integrity violation types and a runtime detection framework claiming 85.2% F1 on a new benchmark. For teams building autonomous research pipelines. · 2/5

**[SurveyGraph: Generating Academic Surveys via Methods-Entity Knowledge Graphs](https://arxiv.org/abs/2610.31317)** — Uses a method-level knowledge graph (follow-on, competition, shared-resource edges) to structure survey generation. Evaluated on a seven-method equal-budget benchmark. Relevant for literature-review automation. · 2/5

### Compression & Quantization
**[intel/neural-compressor](https://github.com/intel/neural-compressor)** — SOTA low-bit quantization (INT8/FP8/MXFP8/INT4/MXFP4/NVFP4) and sparsity across PyTorch, TensorFlow, and ONNX Runtime. 2.7k stars observed. Engineers deploying LLMs on CPU/GPU/XPU can test the latest quantization recipes here. · 4/5

**[Rethinking Sequence Compression with Test-time Regression](https://arxiv.org/abs/2610.31574)** — Replaces pooling/learned projections with a learned regression problem whose closed-form coefficients become the compressed representation. Code at `github.com/Sphere-AI-Lab/ttr-compressor`. For researchers exploring efficient attention alternatives. · 2/5

### Models
**[Qwen/Qwen3.8-27B (HF Model)](https://huggingface.co/Qwen/Qwen3.8-27B)** — Multimodal image-text-to-text model (Apache-2.0) with 7.7M downloads and 18k likes observed. Teams needing a recent open-weight vision-language model can evaluate this directly. · 3/5

**[google/embeddinggemma-2 (HF Model)](https://huggingface.co/google/embeddinggemma-2)** — Sentence-transformers compatible embedding model (feature-extraction) with 193k downloads and 2.9k likes observed. Drop-in for retrieval/RAG pipelines seeking newer embedding bases. · 3/5

### Distillation
**[When to Follow the Teacher: Advantage-Based On-Policy Distillation](https://arxiv.org/abs/2610.31563)** — Weights teacher actions by counterfactual advantage under the student policy rather than imitating at every step. Targets online policy distillation for RLHF/agent training. · 2/5

### Agents & Video
**[VideoJev: System One Model for Video Understanding and Interaction](https://arxiv.org/abs/2610.18615)** — Adapts MLLMs by replacing autoregressive answer decoding with a shared head for structured video decisions. GitHub: `MCG-NJU/VideoJev`. Carryover tracked 7 runs; traction rising. For teams building low-latency video agents. · 3/5

## Watch-list / Still developing
**[Jeva: System One Models from First Principles](https://arxiv.org/abs/2610.18773)** — Carryover (7 runs, traction Δ +3.6). Argues for null-aware, permutation-invariant decision heads. GitHub: `LiQiiiii/Jeva`. · 3/5

**[hfdataset:nvidia/Nemotron-Personas-Vietnam](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Vietnam)** — Vietnamese persona dataset (1M–10M samples, CC-BY-4.0, image+text). 17k downloads observed. · 4/5

**[ghrepo:huggingface/transformers](https://github.com/huggingface/transformers)** — Core framework repo (168k stars observed). No new release in window; tracked for ecosystem updates. · 4/5

**[nvidia/Nemotron-Personas-Vietnam](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Vietnam)** — Duplicate entry; same as above.

## Story arcs

- [Multimodal Embodied Agents: A Unified Capability-centric Perspective from Computer-Use to Robot-Use](https://arxiv.org/abs/2610.30108) — seen 3 runs, traction +94.2% since first seen on 2026-10-22.
- [FlashVSR+: Efficient Video Super-Resolution via Hybrid Attention and Reward-Yield Distribution Matching](https://arxiv.org/abs/2610.17552) — seen 7 runs, traction +83.7% since first seen on 2026-10-14.
- [Sage-A1.5: From Long-Horizon Execution to Scientific Exploration with Capability Composition](https://arxiv.org/abs/2610.28578) — seen 4 runs, traction +81.8% since first seen on 2026-10-21.
- [SolarRenderer: Few-Step Generative Reference Rendering](https://arxiv.org/abs/2610.28630) — seen 4 runs, traction +81.5% since first seen on 2026-10-21.
- [Looking Ahead: Modeling Future Evolution in Autoregressive Video Generation](https://arxiv.org/abs/2610.29989) — seen 3 runs, traction +71.7% since first seen on 2026-10-22.
- [Jeva: System One Models from First Principles](https://arxiv.org/abs/2610.18773) — seen 7 runs, traction +71.6% since first seen on 2026-10-14.
- [AesCode: Aesthetic Code Generation with Decoupled Cross-Modal Rewards](https://arxiv.org/abs/2610.18860) — seen 7 runs, traction +70.9% since first seen on 2026-10-14.
- [VideoJev: System One Model for Video Understanding and Interaction](https://arxiv.org/abs/2610.18615) — seen 7 runs, traction +63.7% since first seen on 2026-10-14.
- [Agent-Reflex: Teaching Language Agents to Act Reflectively](https://arxiv.org/abs/2610.17953) — seen 7 runs, traction +63.4% since first seen on 2026-10-14.
- [Urbex: Agentic Spatial Grounding for City-Scale 3D Scenes](https://arxiv.org/abs/2610.18356) — seen 7 runs, traction +54.3% since first seen on 2026-10-14.

## Action items
1. **Try** the [intel/neural-compressor MXFP4/NVFP4 paths](https://github.com/intel/neural-compressor) on a PyTorch LLM — the repo includes ready-to-run quantization scripts for ONNX Runtime and TensorFlow as well.
2. **Read** the [AgentPhishing benchmark](https://arxiv.org/abs/2610.31404) if you maintain email-enabled agents; it defines a concrete threat model missing from standard phishing corpora.
3. **Track** the [TTR-Compressor repo](https://github.com/Sphere-AI-Lab/ttr-compressor) — test-time regression compression is a distinct architectural bet that could simplify sequence-length bottlenecks.