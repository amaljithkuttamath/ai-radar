<!-- radar:nav -->
`radar`  ·  [← 2026-11-25](2026-11-25-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-11-26

A new attention architecture (Mixture-of-Loops Transformer) claims expressivity gains by reusing KV memory across loops, while Real2SimLab and Sage-Med release unified benchmarks for real-to-sim transfer and medical multimodal scaling. Several video-generation and agent-evaluation platforms also appeared with runnable code.

## What changed

**New to radar** (454 items):  
- [Mixture-of-Loops Transformer](https://arxiv.org/abs/2611.34923) — looped attention with KV reuse  
- [Real2SimLab: A Unified Platform for Real-to-Simulation Transfer](https://arxiv.org/abs/2611.34849) — benchmark suite for video-to-simulation  
- [Sage-Med: Scaling Medical Multimodal Intelligence](https://arxiv.org/abs/2611.34575) — 35B medical MLLM with 3B activated params  
- [Improving and Expanding Video Editing Capabilities Without Videos](https://arxiv.org/abs/2611.34941) — image-to-video transfer for editing  
- [Agentic LongLive: Asynchronous Agentic Memory for Long Video Generation](https://arxiv.org/abs/2611.34907) — separate memory agent for streaming video  

**Climbing** (4 items):  
- [Embodied AI Fails the Mirror Test](https://arxiv.org/abs/2611.33010) — mirror breaks robot policies (mag +139%)  
- [opensetlabs/openset-llm](https://github.com/opensetlabs/openset-llm) — CPU-only LLM server (mag +50%)  
- [JaimeMaLangue/JML-fon-speech-v1](https://huggingface.co/datasets/JaimeMaLangue/JML-fon-speech-v1) — Fon speech dataset (score +1)  
- [alphaXiv/AgentAlphaXiv](https://huggingface.co/datasets/alphaXiv/AgentAlphaXiv) — agent benchmark dataset (score +1)  

## Main list

### [Mixture-of-Loops Transformer](https://arxiv.org/abs/2611.34923) · 4/5
HUST researchers introduced MoLT, a looped Transformer that passes keys and values as memory across loops via Mixture-of-Loops Attention, offering two modes: residual-stream reuse (MoLT-R) or embedding restart with KV memory (MoLT-KV).  
**Matters if** you train deep models and want expressivity without proportional compute; [code](https://github.com/hustvl/MoLT) is available.

### [Real2SimLab: A Unified Platform for Real-to-Simulation Transfer](https://arxiv.org/abs/2611.34849) · 4/5
Real2SimHub released a single evaluation harness that runs any real-to-sim method across multiple benchmarks, replacing N×M custom integrations with a shared interface.  
**Matters if** you build or test sim-from-video pipelines; [platform](https://github.com/Real2SimHub/Real2SimLab) and [project page](https://real2simhub.github.io) are live.

### [Sage-Med: Scaling Medical Multimodal Intelligence](https://arxiv.org/abs/2611.34575) · 4/5
The Sage-Med team published a 35B-parameter medical MLLM (3B activated) showing that scaling model size mainly helps text, not multimodal perception, and released a preview checkpoint.  
**Matters if** you need a medical vision-language baseline; [repo](https://github.com/Sage-Med/Sage-Med-Preview) and [demo](https://sage-med-preview.github.io/) included.

### [Improving and Expanding Video Editing Capabilities Without Videos](https://arxiv.org/abs/2611.34941) · 4/5
HorizonWind2004 proposed Image-to-Video Transfer (I2VT), which post-trains a video editor on single images using an image editor as teacher — no paired video data required.  
**Matters if** you extend video editors to new tasks cheaply; [code](https://github.com/HorizonWind2004/i2v-transfer) and [project](https://i2v-transfer.github.io/) provided.

### [Agentic LongLive: Asynchronous Agentic Memory for Long Video Generation](https://arxiv.org/abs/2611.34907) · 3/5
NVIDIA researchers built a separate memory agent that reads only revealed prompts (never generated frames) to keep long streaming video consistent without offline planning.  
**Matters if** you serve real-time video generation; [LongLive repo](https://github.com/NVlabs/LongLive) and [project page](https://nvlabs.github.io/LongLive/Agentic-LongLive/) linked.

### [EgoUseBench: Benchmarking Computer-Use Agents under Evolving First-Person Contexts](https://arxiv.org/abs/2611.34466) · 3/5
Yurun Chen et al. introduced a benchmark for agents that operate from egocentric wearable video, where tasks arise implicitly from the user's physical activity.  
**Matters if** you build agents for AR glasses or embodied assistants; [benchmark](https://github.com/YurunChen/EgoUseBench) and [site](https://yurunchen.github.io/egousebench/) available.

### [DocSEAM: Bidirectional Cross-Page Encoding for Multi-Page Document Understanding](https://arxiv.org/abs/2611.34420) · 3/5
Mossbee added a lightweight cross-page module between vision encoder and LLM, forming local triplets (prev, current, next) to inject adjacent-page context into visual tokens.  
**Matters if** you process long documents page-by-page; [implementation](https://github.com/mossbee/DocSEAM) and [project](https://mossbee.github.io/projects/DocSEAM/) released.

### [Much shorter version of GRH Lean verification from Anthropic](https://github.com/lsernau/grh-lean) · 3/5
A condensed Lean 4 formalization of the Gödel-Rosser-Hilbert inconsistency proof, derived from Anthropic's original, garnered 526 HN points and 336 comments.  
**Matters if** you track formal verification of LLM reasoning; [repo](https://github.com/lsernau/grh-lean) and [HN discussion](https://news.ycombinator.com/item?id=50648050).

### [One Ocean, Many Tasks: A Data-Grounded Simulation Suite and Benchmark for Marine Robotics](https://arxiv.org/abs/2611.34925) · 2/5
OneOcean harmonizes bathymetry, data-driven currents, tides, and pollution fields into a unified spatiotemporal product with a task ladder from navigation to cleanup.  
**Matters if** you simulate marine robots in realistic ocean conditions; paper includes environment and benchmark design.

### [Enhancing Maritime Domain Awareness using Latent Space Representations](https://arxiv.org/abs/2611.34899) · 2/5
Researchers applied TerraMind's compressed SAR embeddings to vessel detection and anomaly tasks, operating directly on latent representations to avoid data-gravity bottlenecks.  
**Matters if** you process satellite radar at scale; method uses linear/non-linear probes on frozen embeddings.

## Watch-list / Still developing

- [prism-ml/Ternary-Bonsai-2.5-27B-GGUF](https://huggingface.co/prism-ml/Ternary-Bonsai-2.5-27B-GGUF) — 2-bit ternary 27B model (488 likes, 59k downloads observed)
- [orcarouter/Inkling-2-Mini-abliterated-GGUF](https://huggingface.co/orcarouter/Inkling-2-Mini-abliterated-GGUF) — MoE 2-mini variant (263 likes, 12k downloads observed)
- [datapointai/multilingual-tts-ad-human-preferences-270k](https://huggingface.co/datasets/datapointai/multilingual-tts-ad-human-preferences-270k) — 270k human preference pairs for TTS reward modeling
- [Jackrong/DeepSeek-V4.1-Flash-Nemotron-Competitive-Coding-Distill](https://huggingface.co/datasets/Jackrong/DeepSeek-V4.1-Flash-Nemotron-Competitive-Coding-Distill) — competitive coding distillation dataset (3 days on radar, momentum +42%)

## Action items

- **Read** the [Mixture-of-Loops Transformer paper](https://arxiv.org/abs/2611.34923) and [MoLT repo](https://github.com/hustvl/MoLT) if you explore depth-efficient attention alternatives.
- **Try** [Real2SimLab](https://github.com/Real2SimHub/Real2SimLab) to evaluate your own video-to-simulation pipeline against a standardized suite.
- **Track** [Sage-Med-Preview](https://github.com/Sage-Med/Sage-Med-Preview) for medical multimodal checkpoints; the 3B-activated variant may fit constrained serving budgets.

---

Collection was incomplete: lab_blogs.
