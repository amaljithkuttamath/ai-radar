<!-- radar:nav -->
`radar`  ·  [← 2026-10-13](2026-10-13-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-10-14

A flood of new agent-centric papers and benchmarks arrived in the last 48 hours — 333 fresh entries — while the field's evaluation infrastructure keeps hardening with bilingual text-rendering tests, continual-learning stress tests for radar, and ASR equity audits. Two long-running streaming-video and text-rendering stories are still climbing steadily.

## What changed

**New today** — items not present last run:
- [VideoJev: System One Model for Video Understanding and Interaction](https://arxiv.org/abs/2610.18615) — system-one video agent
- [Agent-Reflex: Teaching Language Agents to Act Reflectively](https://arxiv.org/abs/2610.17953) — reflective agent training
- [AesCode: Aesthetic Code Generation with Decoupled Cross-Modal Rewards](https://arxiv.org/abs/2610.18860) — code aesthetics
- [WorkRover: Scaling Long-Horizon Cowork Agent Training Via Recursive Environment Evolution](https://arxiv.org/abs/2610.18067) — long-horizon agent training
- [DeltaTTG: Training Multi-Turn Agents with a Token-to-Go Progress Meter](https://arxiv.org/abs/2610.17666) — multi-turn progress tracking

**Climbing** — none this window.  
**Cooled** — none this window.

---

### Agents & Multi-Agent RL

**[ProAS: A Progress-Aware Advantage Shaping Framework for Multi-Turn Agentic Reinforcement Learning](http://arxiv.org/abs/2610.18683v1) · 3/5**  
Fixes the uniform credit-assignment flaw in critic-free RL (e.g., GRPO) by shaping advantages around *progress* toward task completion — early pivotal actions get weighted differently than later ones. The authors show it reduces reinforcement of structurally invalid actions without adding a critic. [code](https://github.com/ProAS/ProAS)  

**[BRIDGE: Selective Boundary Repair with Dependency Graph Evidence in Multi-Agent Systems](http://arxiv.org/abs/2610.17805v1) · 3/5**  
Treats broken inter-agent handoffs as a verifiable runtime control problem. A dependency graph tracks what context *should* have been passed; at repair time, BRIDGE selectively intervenes only on the missing edges rather than replaying the whole trajectory. [code](https://github.com/BRIDGE/BRIDGE)  

### Benchmarks & Evaluation

**[Overcoming Catastrophic Forgetting: Continual Learning for Radar Waveform Classification](http://arxiv.org/abs/2610.18404v1) · 3/5**  
First large-scale CL benchmark for radar: 12 methods × 8 waveform families × realistic deployment streams. Replay + regularization hybrids win; pure regularization fails on long sequences. Dataset and evaluation harness released. [code](https://github.com/radar-cl/radar-cl)  

**[Connecting the Dots: Enduring Performance Gaps in ASR Systems Between Standard and Minority English Varieties](http://arxiv.org/abs/2610.17761v1) · 3/5**  
Longitudinal eval of 16 ASR systems (2021–2025) across 8 minority-English datasets. The gap vs. standard English *has not closed* despite scale — Whisper-large-v3 still shows 12–18% relative WER degradation on AAVE and Indian English. Challenges the "bigger models fix bias" assumption. [data](https://github.com/asr-equity/asr-equity)  

**[ShoeFit: A New Dataset and Dual-image-stream DiT Framework for Virtual Footwear Try-On](http://arxiv.org/abs/2610.18325v1) · 3/5**  
First dedicated VFTON benchmark: 12K paired shoe/model images with pose-aligned views. A dual-stream DiT handles viewpoint misalignment and texture transfer better than garment-VTON baselines. Dataset + model released. [project](https://shoefit.github.io) · [code](https://github.com/shoefit/shoefit)  

**[ProbabilityBench: Model Evaluation and Calibration with Exact Ground-Truth Uncertainty](http://arxiv.org/abs/2610.17016v1) · 2/5**  
Three simulated text domains (peer review, covert info transfer, credit risk) where the data-generating process is fully known — so exact class probabilities and Bayes error are computable. Enables calibration eval without human labels. [code](https://github.com/ProbabilityBench/ProbabilityBench)  

**[From Fourier Amplitudes to Persistence Images for Impact-Echo Defect Detection](http://arxiv.org/abs/2610.18732v1) · 2/5**  
Converts noisy impact-echo spectra into 2D frequency–amplitude persistence images via topological data analysis. A lightweight CNN on FA-PI beats hand-crafted spectral features on concrete defect classification. [code](https://github.com/impact-echo/FA-PI)  

### Model Releases

**[openbmb/MiniCPM-V-4.7-1B](https://huggingface.co/openbmb/MiniCPM-V-4.7-1B) · 2/5**  
Latest 1B multimodal checkpoint from the MiniCPM line — image-text-to-text, safetensors, Transformers-ready. Trending on HF; no benchmark deltas published yet.  

**[LiquidAI/LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B) · 2/5**  
24B MoE (2 active experts) from Liquid AI — text-generation, Transformers-compatible. Early community runs show strong throughput on H100; no independent evals yet.

---

## Story arcs

- [Context Language Models](https://arxiv.org/abs/2609.37725) — seen 12 runs, traction +187.9% since first seen on 2026-09-30.
- [DAEDALUS: Bootstrapping Agent Memory from Self-Generated Tasks](https://arxiv.org/abs/2610.08048) — seen 7 runs, traction +151.2% since first seen on 2026-10-07.
- [Routing Should Pay for Itself: Sparse Supervision for Economical LLM Routing](https://arxiv.org/abs/2609.37402) — seen 12 runs, traction +123.3% since first seen on 2026-09-30.
- [ALIVE: Interaction-Aligned Object Insertion for First-Frame-Guided Video Editing](https://arxiv.org/abs/2610.08779) — seen 6 runs, traction +102.4% since first seen on 2026-10-07.
- [EVO-WAM: Evolving World Action Models through Video-Action Verification](https://arxiv.org/abs/2609.38057) — seen 12 runs, traction +101.8% since first seen on 2026-09-30.
- [UltraText Bench: A Comprehensive Bilingual Benchmark for Evaluating Visual Text Rendering in Image Generation](https://arxiv.org/abs/2610.09823) — seen 6 runs, traction +97.6% since first seen on 2026-10-08.
- [Long-WAM: Scaling the Context of World-Action Models](https://arxiv.org/abs/2610.10528) — seen 6 runs, traction +94.3% since first seen on 2026-10-08.
- [HybridCUA: Learning to Orchestrate GUI and CLI for Computer-Use Agents](https://arxiv.org/abs/2609.38008) — seen 12 runs, traction +89.2% since first seen on 2026-09-30.
- [RLHND: Video Foundation Models as Physically Grounded Hand Trackers for Robot Learning](https://arxiv.org/abs/2610.09455) — seen 6 runs, traction +79.8% since first seen on 2026-10-08.
- [Beyond the Timeline: Augmenting Long-Video Memory with Grounded Entity Biographies](https://arxiv.org/abs/2609.38155) — seen 12 runs, traction +77.9% since first seen on 2026-09-30.

## Watch-list

- [moonworks/lunara-art-eval](https://huggingface.co/datasets/moonworks/lunara-art-eval) — HF dataset for text-to-image art evaluation, Apache-2.0, 1K–10K samples.  
- [European Cities Deploy NVIDIA-Powered AI Agents to Run Smarter Urban Operations](https://blogs.nvidia.com/blog/european-cities-agents-urban-operations/) — deployment blog, no technical artifact.  
- [From Enterprise to Earthshot: UK's Ecosystem Moves From Ambition to Application With NVIDIA](https://blogs.nvidia.com/blog/uk-ecosystem-deployment/) — UK deployment announcement, $250M compute commitment cited.  
- [How Third Moment Research runs 10,000 agents for 36+ hours](https://openai.com/index/third-moment-research) — OpenAI blog on GPT-6 Astra/Sol agent runs; no code or reproducibility artifacts.

---

## Still developing

- [OneStreamer: Unifying Perception, Memory, and Proactive Response in Streaming Video Interaction](https://arxiv.org/abs/2610.01762) — 10th run, 224 → 231 stars (+3.2%). Streaming LLM that learns query-independent evidence recording and proactive response jointly. [code](https://github.com/MCG-NJU/OneStreamer) · [project](https://mcg-nju.github.io/OneStreamer)  
- [UltraText Bench: A Comprehensive Bilingual Benchmark for Evaluating Visual Text Rendering in Image Generation](https://arxiv.org/abs/2610.09823) — 6th run, 59 → 61 stars (+3.6%). Bilingual dense-text benchmark (432 prompts, 24 scene categories). [code](https://github.com/LINs-lab/UltraText_Bench)

---

## Insights

- **Evaluation is fragmenting by modality and deployment context** — radar CL, ASR equity, impact-echo NDT, and virtual try-on each now have dedicated benchmarks. General-purpose leaderboards are losing relevance.  
- **Agent RL is moving past "just add GRPO"** — ProAS and BRIDGE both target structural credit-assignment and handoff failures that naive trajectory-level rewards miss. Expect more critic-free shaping tricks.  
- **Model releases are decoupling from papers** — MiniCPM-V-4.7 and LFM2.5-24B drop as HF checkpoints first; technical reports (if any) follow weeks later. Tracking HF trending is now a primary signal.

## Action items

- **Try** ProAS if you're running GRPO-style agent training — drop-in advantage shaper, no critic needed.  
- **Read** the ASR equity paper (Connecting the Dots) before claiming your speech model "works for everyone."  
- **Track** the radar CL benchmark — it's the first realistic continual-learning stress test for RF sensing, and the method ranking (replay+reg > pure reg) likely transfers to other streaming domains.  
- **Test** MiniCPM-V-4.7-1B on your edge multimodal workload — 1B params, Apache-2.0, but verify against your own eval set first; no independent numbers yet.