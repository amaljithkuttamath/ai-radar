<!-- radar:nav -->
`radar`  ·  [← 2026-10-23](2026-10-23-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-10-24

The radar picks up a wave of new agent frameworks (OpenBB, atomic-agents, FinRobot) and a benchmark dataset for typed decisions, while core libraries (Transformers, Qwen, Gemma) and two System One model lines (Jeva, VideoJev) continue climbing. Together they signal a shift toward structured decision-making agents, open financial tooling, and evaluation infrastructure.

## What changed

### New to radar
- [openbq-org/OpenBB](https://github.com/openbq-org/OpenBB) — Open Data Platform for analysts, quants and AI agents. · 3/5
- [Eigenwise/atomic-agents](https://github.com/Eigenwise/atomic-agents) — Building AI agents, atomically · 3/5
- [Developer-Y/cs-video-courses](https://github.com/Developer-Y/cs-video-courses) — List of Computer Science courses with video lectures. · 3/5
- [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) — FinRobot: An Open-Source AI Agent Platform for Financial Applications using Large Language Models · 3/5
- [bones-studio/seed](https://huggingface.co/datasets/bones-studio/seed) — HF Dataset · 3/5

### Climbing
- [scenario-labs/3d-collection](https://huggingface.co/datasets/scenario-labs/3d-collection) — HF Dataset, score increased to 3 (Δ+1)

## Main list

### Benchmark
- [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) — Benchmark dataset for text-classification evaluation with official YAML specs; 245 likes, 45k downloads observed. · 4/5

### Hugging Face Transformers
- [huggingface/transformers](https://github.com/huggingface/transformers) — Core model-definition framework for text, vision, audio, and multimodal models; 168k stars observed. · 4/5
- [Jeva: System One Models from First Principles](https://arxiv.org/abs/2610.18773) — System One models for low-latency, structured decision-making; repo and project page linked. Observed 7 consecutive runs with rising traction. · 3/5

### Qwen & Gemma
- [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) — Image-text-to-text model (Qwen3.5 series); 18k likes, 7.85M downloads observed. · 3/5
- [google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2) — Feature-extraction embedding model (sentence-transformers compatible); 2.9k likes, 207k downloads observed. · 3/5

### Agent & Video
- [VideoJev: System One Model for Video Understanding and Interaction](https://arxiv.org/abs/2610.18615) — System One model family casting video understanding as structured decisions; repo and project page linked. Observed 7 consecutive runs with rising traction. · 3/5

### Methods
- [Rethinking Sequence Compression with Test-time Regression](https://arxiv.org/abs/2610.31574) — TTR-Compressor learns sequence compression via test-time regression; GitHub and project page available. · 2/5
- [When to Follow the Teacher: Advantage-Based On-Policy Distillation](https://arxiv.org/abs/2610.31563) — AOPD weights teacher actions by counterfactual advantage under the student policy. · 2/5

### Data & Education
- [microsoft/AI-For-Beginners](https://github.com/microsoft/AI-For-Beginners) — 12-week, 24-lesson AI curriculum; 70k stars observed. · 4/5
- [nvidia/Nemotron-Personas-Vietnam](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Vietnam) — Vietnamese persona dataset with image modality; 217 likes, 19k downloads observed. · 4/5

## Watch-list / Still developing
- [AgentPhishing: A Benchmark of LLM Email Agents Under Adaptive Attack](https://arxiv.org/abs/2610.31404) — Benchmark for agent susceptibility to persuasive phishing. · 2/5
- [Parameter-Efficient Adaptation of Large Language Models to a Low-Resource Agglutinative Language](https://arxiv.org/abs/2610.31397) — Bashkir language corpus, datasets, and reproducible benchmark across eight architectures. · 2/5
- [RIDAR: Safeguarding Research Integrity in Autonomous Research Agents](https://arxiv.org/abs/2610.31372) — Automated detection and runtime intervention for research integrity violations (85.2% F1 claimed). · 2/5
- [CrisiLangs: A Multilingual Resource for Crisis Warning Generation](https://arxiv.org/abs/2610.31356) — Multilingual extension of CrisiText to Italian, Bulgarian, German, Greek. · 2/5

## Action items
- **Read** [Rethinking Sequence Compression with Test-time Regression](https://arxiv.org/abs/2610.31574) — introduces TTR-Compressor, a test-time regression approach to sequence compression with a GitHub implementation.
- **Try** [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) — benchmark dataset for text classification with official eval YAML; useful for evaluating small-model decision making.
- **Track** [Jeva](https://arxiv.org/abs/2610.18773) and [VideoJev](https://arxiv.org/abs/2610.18615) — System One model family climbing for 7 consecutive runs with rising traction; repos available for experimentation.