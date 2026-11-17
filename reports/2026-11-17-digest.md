<!-- radar:nav -->
`radar`  ·  [← 2026-11-16](2026-11-16-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-11-17

Three frontier-scale releases dominate today: ScaleVLA connects a 552B DeepSeek backbone to a robot action head, InclusionMed publishes a reproduced Atlas of five healthcare benchmarks, and Sage S2.1 Flash ships a 320B MoE model with scientific encoders and verifiable tool environments. Together they signal a shift from demo-scale VLAs and medical evals toward reproducible, frontier-backed systems.

## What changed

**New to radar** (top 5 of 468): [openai/gsm8k (HF Dataset)](https://huggingface.co/datasets/openai/gsm8k) · 5/5 • [ScaleVLA: Scaling Vision-Language-Action Models to 552 Billion Parameters](https://arxiv.org/abs/2611.21607) · 4/5 • [InclusionMed: Benchmarking AI for Inclusive Healthcare](https://arxiv.org/abs/2611.21218) · 4/5 • [Sage S2.1 Flash Technical Report](https://arxiv.org/abs/2611.21072) · 4/5 • [K2-Horizon: A Frontier Fleet of Open Source Language Models](https://arxiv.org/abs/2611.21003) · 4/5  
**Climbing**: [nvidia/USDCraft-10K (HF Dataset)](https://huggingface.co/datasets/nvidia/USDCraft-10K) · 3/5 (+1) • [google/multimodal-knowledge-agent (HF Dataset)](https://huggingface.co/datasets/google/multimodal-knowledge-agent) · 3/5 (+1)  
**Cooled**: [leostera/git-twig — lightweight git-worktrees for agents](https://github.com/leostera/git-twig) · 3/5 (−1)

## Main list

### Agents
**[ScaleVLA: Scaling Vision-Language-Action Models to 552 Billion Parameters](https://arxiv.org/abs/2611.21607) · 4/5**  
Galaxy General Robotics connects a 552B DeepSeek-V4.1-Flash backbone to a trainable action DiT and systematically compares VLM backbones from 2B to 552B under shared training. Matters if you build robot policies and want evidence that frontier-scale representations transfer to physical action. [Project page](https://galaxygeneralrobotics.github.io/scalevla/)

**[BLIP-Live: Balancing Timeliness & Firing Precision in Proactive Streaming Video Agents](https://arxiv.org/abs/2611.21553) · 2/5**  
Researchers introduce BLIP-Live, a unified dataset, metrics, harness, and training framework for proactive streaming video agents that must decide when to respond vs. stay silent. Matters if you work on real-time video understanding or agent proactivity.  

### Benchmark
**[InclusionMed: Benchmarking AI for Inclusive Healthcare](https://arxiv.org/abs/2611.21218) · 4/5**  
The InclusionMed Atlas organizes benchmarks across three healthcare roles and three AI capabilities; the first release reproduces four public benchmarks and adds a private diagnostic-reasoning set (InclusionMed-DxFiles). Matters if you evaluate medical models and need transparent, audited coverage across roles and tasks. [GitHub](https://github.com/panuvi/inclusionmed) • [Project](https://inclusionmed.ai/)

**[Rotation-Invariant Machine Learning for Highly Symmetric Molecular Configurations](https://arxiv.org/abs/2611.21308) · 3/5**  
A new lightweight benchmark exposes degeneracies in both invariant and equivariant architectures on n-fold symmetric atomic environments, guiding a proposed fix. Matters if you develop molecular ML potentials and need to handle high-symmetry configurations reliably.  

**[When Do Histology Foundation Models Need Geometric Test-Time Augmentation?](https://arxiv.org/abs/2611.21565) · 2/5**  
Benchmarking 9 histology FMs and 6 general-purpose models shows D₄ test-time augmentation loses value as foundation models gain inherent rotational invariance. Matters if you deploy computational pathology pipelines and want to avoid wasted inference compute.  

**[Benchmarking memory and nonlinear processing capacity of quantum recurrent neural networks for time series prediction](https://arxiv.org/abs/2611.21552) · 2/5**  
A rigorous task-driven benchmark quantifies memory and nonlinear capacity of variational QRNNs, enabling intuitive comparison to classical RNNs. Matters if you explore quantum ML for sequential data and need standardized capacity metrics.  

**[GHySSeg: Real-Time Geometric Ground and Road Segmentation for Hybrid Solid-State LiDAR](https://arxiv.org/abs/2611.21507) · 2/5**  
Classical geometric methods fail on ring-free, frontal-field hybrid LiDAR; GHySSeg provides a real-time geometric alternative that is certifiable and computationally light. Matters if you work on automotive perception with next-gen LiDAR sensors.  

**[AuXSpec: Learning to Autoformalize Program Specifications via Executable Postconditions](https://arxiv.org/abs/2611.21421) · 2/5**  
AuXSpec uses executable postconditions as scalable feedback to train Lean specification generators, avoiding expensive proof or correspondence steps. Matters if you build autoformalization tooling and need cheaper specification-quality signals.  

**[Seeing Isn't Resolving: Visual and Linguistic Disambiguation with Conversational Grounding](https://arxiv.org/abs/2611.21183) · 2/5**  
The JAG-D dataset introduces human-robot conversational multimodal interactions covering visual and linguistic ambiguity; VLMs are evaluated on recognition and resolution. Matters if you build grounded dialogue systems that must handle real-world referential uncertainty.  

### Other
**[Sage S2.1 Flash Technical Report](https://arxiv.org/abs/2611.21072) · 4/5**  
InternLM releases a 320B MoE model with dedicated encoders for molecular graphs, biological sequences, and spectra, plus verifiable tool-use, search, and coding environments. Matters if you need a large scientific agent with multimodal perception and reproducible environment benchmarks. [GitHub](https://github.com/InternLM/Sage-S2.1-Flash) • [Project](https://internlm.github.io/Sage-S2.1-Flash/)

## Watch-list / Still developing

- [DominoBench: Evaluating Multi-Step Physical Reasoning from Still Images](https://arxiv.org/abs/2611.20385) · 2/5 — new benchmark, 4 HF upvotes
- [GPT‑6.2 Astra and Sol (HN discussion)](https://news.ycombinator.com/item?id=50535230) · 2/5 — 571 points, 321 comments
- [How the Claude Code team thinks about verification](https://news.ycombinator.com/item?id=50529612) · 2/5 — 197 points, 158 comments
- [sensenova/SenseNova-Loop-9B (HF Model)](https://huggingface.co/sensenova/SenseNova-Loop-9B) · 2/5 — 130 likes
- [sybil-solutions/inference-optimisation-skill](https://github.com/sybil-solutions/inference-optimisation-skill) · 3/5 — 808 ★, agent skill for hill-climbing local LLM serving speed
- [TypeSafe AI Jev model — decision models to avoid hallucinations](https://spectrum.ieee.org/typesafe-ai-hallucination-decision-models) · 2/5 — 2 days on radar
- [leostera/git-twig — lightweight git-worktrees for agents](https://github.com/leostera/git-twig) · 3/5 — 244 ★, cooled this run
- [scenario-labs/3d-collection (HF Dataset)](https://huggingface.co/datasets/scenario-labs/3d-collection) · 3/5 — carryover, 3 runs tracked, 415 likes, 55k downloads
- [n4ze3m/tiny-voca (HF Model)](https://huggingface.co/n4ze3m/tiny-voca) · 3/5 — 224 likes, 3k downloads, ONNX/GGUF TTS

## Action items

**Read** the [ScaleVLA project page](https://galaxygeneralrobotics.github.io/scalevla/) for the 552B VLA architecture details and scaling curves — rare public evidence on frontier-backbone transfer to robot action.  
**Try** the [sybil-solutions/inference-optimisation-skill](https://github.com/sybil-solutions/inference-optimisation-skill) agent skill to auto-tune local LLM serving (speculative decoding, KV, TTFT) on your hardware; 808 stars suggest active maintenance.  
**Track** the [InclusionMed Atlas](https://inclusionmed.ai/) as it expands beyond the initial five benchmarks — its structured audit/reproduction process sets a new bar for medical AI evaluation transparency.

---

Collection was incomplete: lab_blogs.
