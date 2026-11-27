<!-- radar:nav -->
`radar`  ·  [← 2026-11-26](2026-11-26-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-11-27

The strongest signal today is the **Mixture-of-Loops Transformer (MoLT)** paper with open code, which has accumulated 97 GitHub stars and 74 HF upvotes in two days while proposing a new attention-memory mechanism for looped architectures. Also notable: a Vulkan-accelerated **waifu2x Windows upscaler** hit 171 stars on its first day. Coverage is broad but shallow — most items are early repos or preprints without independent verification.

## What changed

**New to radar** (5 of 31)
- [Interactive-Active-AI/NextTransformer](https://github.com/Interactive-Active-AI/NextTransformer) — open-source framework for next-gen Transformers with compute-matched benchmarking
- [Red2076-arch/waifu2x-image-upscaler-windows](https://github.com/Red2076-arch/waifu2x-image-upscaler-windows) — free AI image upscaler/denoiser for Windows on Vulkan + ncnn
- [dayuwang401/VidRouteBench](https://github.com/dayuwang401/VidRouteBench) — budgeted text-to-video routing benchmark across 16 model×config arms, no GPU needed
- [logitcai/tinybrain](https://github.com/logitcai/tinybrain) — Chinese-first small LM from scratch: 60B-token dataset, tokenizer, mHC+Engram+MoE, PyTorch
- [I don't expect superposition in transformer MLP neurons](https://www.alignmentforum.org/posts/o9dPGxEbpQrnasgDB/i-don-t-expect-superposition-in-transformer-mlp-neurons) — argues superposition lives in residual stream, not MLP neurons

**Climbing** (3)
- [Jackrong/DeepSeek-V4.1-Flash-Nemotron-Competitive-Coding-Distill](https://huggingface.co/datasets/Jackrong/DeepSeek-V4.1-Flash-Nemotron-Competitive-Coding-Distill) — dataset traction rising (score +1, mag +0.14)
- [AMD-specific fork of llama.cpp](https://devnull.land/amd-specific-llama-cpp) — benchmark-focused fork gaining attention (score +1, mag +0.34)
- [VibeVideoAgent: Closing the Perceptual Loop for Code-Driven Video Generation](https://arxiv.org/abs/2611.34237) — magnitude surged +1.34 on perceptual-loop closure for code-driven video

**Cooled** (2)
- [Real2SimLab: A Unified Platform for Real-to-Simulation Transfer](https://arxiv.org/abs/2611.34849) — score dropped −1
- [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) — score dropped −1

---

## Main list

### [Red2076-arch/waifu2x-image-upscaler-windows](https://github.com/Red2076-arch/waifu2x-image-upscaler-windows) · 3/5
A free Windows image upscaler and photo denoiser using Vulkan GPU acceleration and ncnn neural networks, released today with 171 stars.  
Matters if you need a local, dependency-light upscaler for Windows deployment or want a reference for Vulkan+ncnn inference pipelines.

### [I don't expect superposition in transformer MLP neurons](https://www.alignmentforum.org/posts/o9dPGxEbpQrnasgDB/i-don-t-expect-superposition-in-transformer-mlp-neurons) · 2/5
An Alignment Forum post arguing that superposition-type compression occurs in the residual stream, not in MLP neurons, with a proposed experimental test.  
Matters if you interpret model internals or design sparsity/pruning methods — the claim redirects where to look for feature compression.

### [I'm Scared of AI](https://thesoapbox.email/archive/3) · 2/5
A personal essay on AI anxiety that hit 175 points and 182 comments on Hacker News, reflecting practitioner sentiment.  
Matters if you track community mood or need a snapshot of current engineer concerns for team discussions.

### [GPT 6.2 Astra Solves a Historical Mystery](https://generativehistory.substack.com/p/gpt-62-astra-solves-a-historical) · 2/5
A Substack post claiming GPT-6.2 resolved a historical question, drawing 154 HN points and 63 comments.  
Matters if you evaluate long-context reasoning claims — treat as an anecdotal benchmark, not a verified result.

### [ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF) · 2/5
A quantized (GSQ, RCO) GGUF model from ISTA-DASLab with 224 likes and 24.9k downloads observed.  
Matters if you deploy quantized models on edge — a data point for GSQ+RCO mixed-precision recipes.

### [yurun-chen/EgoUseBench](https://huggingface.co/datasets/yurun-chen/EgoUseBench) · 2/5
A new Hugging Face dataset (41 likes, 78 downloads) tagged as a computer-use benchmark with arXiv:2611.34466.  
Matters if you build agent evaluations — an early benchmark for ego-centric tool use, but too new for established baselines.

### [Mixture-of-Loops Transformer](https://arxiv.org/abs/2611.34923) · 3/5
A preprint introducing MoLT with Mixture-of-Loops Attention (MoLA), using KV as memory across loops; code at github.com/hustvl/MoLT (97 stars, 74 HF upvotes).  
Matters if you research efficient long-context or recurrent architectures — a concrete looped-Transformer variant with open implementation.

### [Sage-Med: Scaling Medical Multimodal Intelligence](https://arxiv.org/abs/2611.34575) · 3/5
Systematic evaluation showing medical MLLMs underperform general MLLMs; scaling helps text more than perception. Code at github.com/Sage-Med/Sage-Med-Preview (27 stars, 81 HF upvotes).  
Matters if you train or evaluate medical multimodal models — evidence that current scaling recipes don't transfer perception gains.

### [Improving and Expanding Video Editing Capabilities Without Videos](https://arxiv.org/abs/2611.34941) · 3/5
Introduces Image-to-Video Transfer (I2VT) to upgrade video editors using only image-edit data; code at github.com/HorizonWind2004/i2v-transfer (45 stars, 46 HF upvotes).  
Matters if you build video editing pipelines — a data-efficient transfer method with open code to test.

### [VibeVideoAgent: Closing the Perceptual Loop for Code-Driven Video Generation](https://arxiv.org/abs/2611.34237) · 3/5
A coding agent that writes rendering programs and uses perceptual feedback to fix visual errors; code at github.com/Kling-Keye/VibeVideoAgent (12 stars, 57 HF upvotes).  
Matters if you generate video from code — an agentic loop that catches rendering bugs (overlapping labels, camera drift) automatically.

---

## Still developing

- [w01fb0ss/PiBot](https://github.com/w01fb0ss/PiBot) — local-first multi-agent desktop team (674 stars, 5 days on radar, traction +0.15)
- [Jackrong/DeepSeek-V4.1-Flash-Nemotron-Competitive-Coding-Distill](https://huggingface.co/datasets/Jackrong/DeepSeek-V4.1-Flash-Nemotron-Competitive-Coding-Distill) — competitive coding dataset (129 likes, 485 downloads, 4 days, traction +0.55)
- [prism-ml/Ternary-Bonsai-2.5-27B-GGUF](https://huggingface.co/prism-ml/Ternary-Bonsai-2.5-27B-GGUF) — 2-bit ternary quantized model (601 likes, 382k downloads, 3 days, traction +0.48)
- [llama.cpp AMD benchmark dashboard](https://huggingface.co/blog/ggml-org/llamacpp-amd-bench) — official AMD Ryzen/Radeon benchmarks for llama.cpp
- [sqlite3_rsync](https://simonwillison.net/2026/Nov/26/sqlite3-rsync/) — SQLite remote-copy tool (experimental since 2024, now understood)
- [Anthropic IPO closing](https://www.anthropic.com/news/ipo-close) — 1.127B shares at $83 (lab announcement)
- [Anthropic prices IPO](https://www.anthropic.com/news/anthropic-prices-initial-public-offering) — pricing announcement
- [Mistral Voxtral 3](https://mistral.ai/news/voxtral-3/) — research release
- [Mistral Timestral](https://mistral.ai/news/timestral/) — research release
- [Meta Muse Spark model API](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/) — featured release
- [Meta Genesis mission with Segment Anything/DINO](https://ai.meta.com/blog/genesis-mission-lawrence-berkeley-national-laboratory-segment-anything-dino/) — science application

**Story arcs** (rising traction ≥3 consecutive days):  
[3AGameFactory-Motion](https://arxiv.org/abs/2611.30013) (streak 4, +91%), [Jeveration](https://arxiv.org/abs/2611.24738) (streak 9, +61%), [WeMM-Ecom](https://arxiv.org/abs/2611.30662) (streak 4, +57%), [PartAgent](https://arxiv.org/abs/2611.32554) (streak 3, +53%), [Embo-Harness](https://arxiv.org/abs/2611.31201) (streak 4, +52%), [Sage S2.1 Flash](https://arxiv.org/abs/2611.21072) (streak 11, +46%), [ThinkMorph-SSL](https://arxiv.org/abs/2611.32183) (streak 3, +44%), [Embodied AI Mirror Test](https://arxiv.org/abs/2611.33010) (streak 3, +43%), [Motion Mamba 2.0](https://arxiv.org/abs/2611.29897) (streak 4, +42%), [WorldLeague](https://arxiv.org/abs/2611.30989) (streak 4, +41%).

---

## Action items

**Read** — [Mixture-of-Loops Transformer](https://arxiv.org/abs/2611.34923) + [github.com/hustvl/MoLT](https://github.com/hustvl/MoLT) for a fresh looped-attention mechanism with open code and early traction.

**Try** — [waifu2x-image-upscaler-windows](https://github.com/Red2076-arch/waifu2x-image-upscaler-windows) if you need a standalone Windows upscaler; Vulkan+ncnn makes it a clean reference for GPU-accelerated inference without CUDA.

**Track** — [VibeVideoAgent](https://github.com/Kling-Keye/VibeVideoAgent) — the perceptual-loop-closing agent for code-driven video; watch whether the feedback-loop architecture generalizes to other generative coding tasks.

---

Collection was incomplete: lab_blogs.
