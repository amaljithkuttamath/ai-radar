<!-- radar:nav -->
`radar`  ·  [← 2026-10-12](2026-10-12-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-10-13

A new benchmark for dense visual text rendering and a browser-native Gaussian splatting platform lead a window dominated by model and dataset drops. The standout signal is traction: Visionary pulled 528 GitHub stars in hours, while MMLU-Pro and UltraText Bench confirm evaluation infrastructure is keeping pace with model releases.

## What changed

**New today**  
- [TIGER-Lab/MMLU-Pro (HF Dataset)](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) — benchmark dataset  
- [autotrust/JEV-35B (HF Model)](https://huggingface.co/autotrust/JEV-35B) — 35B MoE model  
- [Visionary: WebGPU Gaussian Splatting](https://github.com/Visionary-Laboratory/visionary) — 528★ browser world model  
- [openbmb/MiniCPM-V-4.7-35B-A3B (HF Model)](https://huggingface.co/openbmb/MiniCPM-V-4.7-35B-A3B) — multimodal 35B  
- [Gemini 4 Argon](https://deepmind.google/blog/introducing-gemini-4-argon/) — DeepMind flagship  

**Climbing** — none  
**Cooled** — none  

## Main list

### Multimodal model releases
- **[autotrust/JEV-35B](https://huggingface.co/autotrust/JEV-35B) · [code](https://huggingface.co/autotrust/JEV-35B/tree/main)** — 35B MoE (Qwen3.5 backbone) tuned for typed decisions and image-text-to-text; tagged `system-one` for structured reasoning. Strong-group authorship, trending on HF. · 3/5
- **[openbmb/MiniCPM-V-4.7-35B-A3B](https://huggingface.co/openbmb/MiniCPM-V-4.7-35B-A3B)** — Latest MiniCPM-V multimodal variant; 35B with 3B active params. OpenBMB’s steady cadence continues; trending on HF but no benchmark deltas published yet. · 2/5

### Benchmark & evaluation
- **[TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro)** — Official MMLU-Pro dataset (MIT license, 10K–100K examples, eval YAML included). The canonical harder MMLU replacement; already wired into major eval harnesses. · 4/5

### Graphics & world models
- **[Visionary](https://github.com/Visionary-Laboratory/visionary)** — Browser-native Gaussian splatting platform powered by WebGPU; bills itself as a “world model carrier.” 528★ in hours — rare instant traction for a graphics runtime. · 3/5

## Story arcs

- [Context Language Models](https://arxiv.org/abs/2609.37725) — seen 11 runs, traction +187.5% since first seen on 2026-09-30.
- [DAEDALUS: Bootstrapping Agent Memory from Self-Generated Tasks](https://arxiv.org/abs/2610.08048) — seen 6 runs, traction +147.9% since first seen on 2026-10-07.
- [Routing Should Pay for Itself: Sparse Supervision for Economical LLM Routing](https://arxiv.org/abs/2609.37402) — seen 11 runs, traction +123.3% since first seen on 2026-09-30.
- [ALIVE: Interaction-Aligned Object Insertion for First-Frame-Guided Video Editing](https://arxiv.org/abs/2610.08779) — seen 5 runs, traction +102.4% since first seen on 2026-10-07.
- [EVO-WAM: Evolving World Action Models through Video-Action Verification](https://arxiv.org/abs/2609.38057) — seen 11 runs, traction +99.1% since first seen on 2026-09-30.
- [UltraText Bench: A Comprehensive Bilingual Benchmark for Evaluating Visual Text Rendering in Image Generation](https://arxiv.org/abs/2610.09823) — seen 5 runs, traction +95.5% since first seen on 2026-10-08.
- [Long-WAM: Scaling the Context of World-Action Models](https://arxiv.org/abs/2610.10528) — seen 5 runs, traction +94.0% since first seen on 2026-10-08.
- [HybridCUA: Learning to Orchestrate GUI and CLI for Computer-Use Agents](https://arxiv.org/abs/2609.38008) — seen 11 runs, traction +89.2% since first seen on 2026-09-30.
- [Beyond the Timeline: Augmenting Long-Video Memory with Grounded Entity Biographies](https://arxiv.org/abs/2609.38155) — seen 11 runs, traction +77.6% since first seen on 2026-09-30.
- [Asking for What Was Never Requested: Horizontal and Vertical Proactivity in Agents](https://arxiv.org/abs/2609.37236) — seen 11 runs, traction +77.2% since first seen on 2026-09-30.

## Watch-list
- [HoneyDataV2/Honey-Data-V2](https://huggingface.co/datasets/HoneyDataV2/Honey-Data-V2) — 10M–100M multilingual VQA/ITT dataset; license “other,” scope unclear.
- [NVIDIA France ecosystem investments](https://blogs.nvidia.com/blog/france-ecosystem-agentic-computing/) — Agentic computing deployment showcase across space, finance, public sector; ecosystem signal, not a product.
- [NVIDIA RTX Spark laptop platform](https://blogs.nvidia.com/blog/local-ai-rtx-spark-laptops-software-updates/) — 128GB unified memory, 1 PFLOP AI compute superchip; software ecosystem announcement, silicon ships later.

## Still developing
- [OneStreamer](https://arxiv.org/abs/2610.01762) — 9th run, 218 → 225 stars, 238 HF upvotes. Streaming video LLM unifying perception, memory, proactive response.
- [UltraText Bench](https://arxiv.org/abs/2610.09823) — 5th run, 51 → 53 stars, 187 HF upvotes. Bilingual dense visual text benchmark (432 prompts, 24 scene categories).

## Insights
- **Evaluation is shipping at model speed.** MMLU-Pro (dataset) and UltraText Bench (visual text) both landed with eval harnesses and real traction — the days of “benchmark later” are ending.
- **Browser-native 3D is having a moment.** Visionary’s 500★ surge signals developer appetite for WebGPU Gaussian splatting without native installs; watch for WebXR/agent integration.
- **MoE + multimodal is the default 35B recipe.** JEV-35B (Qwen3.5 MoE) and MiniCPM-V-4.7 (3B active) both follow the sparse-expert + vision tower pattern — efficiency winning over dense scaling.
- **Carryovers are maturing, not fading.** OneStreamer and UltraText Bench both show positive traction deltas after 5–9 runs; early signals held.

## Action items
- **Try:** Visionary in a WebGPU-enabled browser — 2-minute smoke test for Gaussian splatting workflows.
- **Read:** MMLU-Pro eval YAML and UltraText Bench prompt taxonomy — both are drop-in upgrades for current eval suites.
- **Track:** JEV-35B and MiniCPM-V-4.7 for third-party benchmarks (MMMU, MathVista, VHELM) — the architecture is proven, the deltas are TBD.