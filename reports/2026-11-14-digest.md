<!-- radar:nav -->
`radar`  ·  [← 2026-11-13](2026-11-13-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-11-14

Frontier labs shipped a wave of agent and infrastructure updates: OpenAI added a wallet for agent purchases and published a customer story on legacy-portal handoffs, Google Research highlighted Antigravity's teamwork feature, and NVIDIA released cuPhoton for black-hole interferometry and new FP64 cuBLAS kernels. Meanwhile, a Hacker News thread alleging Nvidia engineered GPU scarcity via startup funding drew 911 points, and several lightweight local-first agent tools appeared on GitHub.

## What changed

**New to radar** (39 items; top 5):
- [Dodaios/ste80-humanizer](https://github.com/Dodaios/ste80-humanizer) — STE80 Humanizer: agent skill that removes AI tells and rewrites text 80% of the way to ASD-STE100 (Simplified Technical English), the method Andrej Karpathy shared. · 3/5
- [Balanov/verdict](https://github.com/Balanov/verdict) — A 197 KB local semantic verifier for AI agent tool calls. Exit code 0 is not proof. · 3/5
- [Balanov/shim](https://github.com/Balanov/shim) — Tiny local-first AI harness: any model, MCP and Agent Skills, natural-language CLI. Zero dependencies. MIT. · 3/5
- [SAOS-3624/dsh-see-now](https://github.com/SAOS-3624/dsh-see-now) — 让 AI 实时看到你的屏幕：按变量筛选帧、多帧拼进一张图，静止画面几低不花 token · 3/5
- [modelflare-ai/AnyModelBot](https://github.com/modelflare-ai/AnyModelBot) — Open-source, local-first alternative to Grok Bot, OpenAI dots and Claude Duet. Your own AI bots on any model: GPT, Claude, Gemini, Grok, DeepSeek, Kimi, GLM and 70+ more through one Modelflare key. · 3/5

**Climbing** (3 items):
- [google/physical-engineerings-last-exam](https://huggingface.co/datasets/google/physical-engineerings-last-exam) (HF Dataset) — rose to score 4 (+1) · 4/5
- [ccore/ThreeJS-3D-Scenes](https://huggingface.co/datasets/ccore/ThreeJS-3D-Scenes) (HF Dataset) — rose to score 3 (+1) · 3/5
- [Jonathan Blow – If AI solved coding, why is my software still the same?](https://www.youtube.com/watch?v=IRK8h67ol7Q) [video] — rose to score 2 (+1) · 2/5

**Cooled** (3 items):
- [Actor, Judge, or Teacher? Understanding Decision Models in Long-Horizon Agents](https://arxiv.org/abs/2611.17167) — fell to score 1 (−1) · 1/5
- [Unbundling Multimodal Vision Encoding](https://arxiv.org/abs/2611.17334) — fell to score 1 (−1) · 1/5
- [TTB: Test-time Baking for Efficient Rendering of Decoder-only View Synthesis Models](https://arxiv.org/abs/2611.17331) — fell to score 1 (−2) · 1/5

## Main list

### Frontier lab releases

**[Shield helps technicians hand off legacy portal work with OpenAI](https://openai.com/business/customer-stories/shield) · 1/5**  
OpenAI published a customer story showing Shield using its models to let IT technicians offload routine work in legacy portals to Forge agents. Matters if you build agent workflows that must interact with older web systems.  

**[Advancing science & engineering with Antigravity's /teamwork](https://research.google/blog/advancing-science-engineering-with-antigravitys-teamwork-feature/) · 1/5**  
Google Research highlighted Antigravity's teamwork feature for collaborative science and engineering workflows. Matters if you design multi-agent systems for research or technical teams.  

**[Run GPU-Powered Black Hole Interferometry with NVIDIA cuPhoton](https://developer.nvidia.com/blog/run-gpu-powered-black-hole-interferometry-with-nvidia-cuphoton/) · 1/5**  
NVIDIA introduced cuPhoton, a GPU-accelerated library for very-long-baseline interferometry imaging, demonstrating M87* reconstruction. Matters if you work on radio astronomy, computational imaging, or GPU-accelerated signal processing.  

**[Faster Scientific Simulations with New FP64 Algorithms in NVIDIA cuBLAS](https://developer.nvidia.com/blog/faster-scientific-simulations-with-new-fp64-algorithms-in-nvidia-cublas/) · 1/5**  
NVIDIA added high-precision FP64 kernels to cuBLAS, targeting molecular chemistry and materials-science workloads that spend most time in dense GEMM. Matters if you run double-precision HPC simulations on Hopper or Blackwell GPUs.  

### Community signals & tools

**[Nvidia allegedly engineered scarcity by funding AI startups to buy its GPUs](https://www.techpowerup.com/354814/nvidia-allegedly-engineered-scarcity-by-funding-ai-startups-to-buy-its-gpus) · 2/5**  
A TechPowerUp report, amplified to 911 Hacker News points, claims Nvidia funded startups to purchase GPUs, creating artificial scarcity. Matters if you track GPU supply-chain dynamics or startup financing structures. [HN discussion](https://news.ycombinator.com/item?id=50493251)  

**[orderesworks42213/crypto-rpocket-accumulation-scanner](https://github.com/orderesworks42213/crypto-rpocket-accumulation-scanner) · 2/5**  
A Python scanner that detects coins in quiet accumulation, back-tested on 961 samples with Telegram alerts. Matters if you prototype crypto market-signal pipelines or study back-testing methodology. (50 ★ observed)  

**[ElysiumduskImmortal63439/resp-warden-desk](https://github.com/ElysiumduskImmortal63439/resp-warden-desk) · 2/5**  
An eight-agent rule engine for on-chain risk analysis: seven rules propose, one vetoes; read-only, no keys, no execution. Matters if you design multi-agent guardrails for DeFi or on-chain monitoring. (50 ★ observed)  

**[Edge0/Edge0-145B-NVFP4](https://huggingface.co/Edge0/Edge0-145B-NVFP4) (HF Model) · 2/5**  
A 145B-parameter MoE model quantized to 4-bit NVFP4, tagged for edge inference and latent MoE; 250 likes, 33.8K downloads observed. Matters if you evaluate compressed MoE checkpoints for local deployment.  

**[google/multimodal-knowledge-agent](https://huggingface.co/datasets/google/multimodal-knowledge-agent) (HF Dataset) · 2/5**  
Google released a small (n<1K) multimodal dataset covering image-text-to-text, visual QA, and document QA tasks under Apache-2.0. Matters if you benchmark vision-language agents on knowledge-intensive tasks. (27 likes, 2.8K downloads observed)  

## Still developing

Carryovers from previous runs (score ≥2 or lab_release) with current observations:

- [Microsoft Research Focus – Edition #98](https://www.microsoft.com/en-us/research/podcast/microsoft-research-focus-edition-98/) · 1/5 — podcast on AI translation, math breakthroughs, faster coding agents (lab_release)
- [Introducing ChatGPT Wallet](https://openai.com/index/introducing-chatgpt-wallet) · 1/5 — secure purchase approvals for agents in ChatGPT Work, Codex, dots (lab_release)
- [Quantifying structural stability of transparent models for general insurance pricing](https://arxiv.org/abs/2611.17308) · 2/5 — functional transparency metrics for model-update stability
- [FLEX-LBP: Learning Local Binary Patterns with Exact Binary Inference](https://arxiv.org/abs/2611.17302) · 2/5 — learnable LBP parameters with straight-through estimator
- [MALNISI-Infused Graph Construction for HSI](https://arxiv.org/abs/2611.17199) · 2/5 — spectral-index adjacency for hyperspectral unsupervised learning
- [UAV-Flow++: Unified Suite for Language-Guided UAV Flight](https://arxiv.org/abs/2611.17163) · 2/5 — benchmark and learning suite for "Flying-on-a-Word"
- [HiVE-VQA: Hierarchical Interaction via Volumetric Embedding](https://arxiv.org/abs/2611.17146) · 2/5 — JEPA-based video encoder for no-reference quality assessment
- [Compact xDAWN-Guided Spatio-Temporal Network for P300 Detection](https://arxiv.org/abs/2611.17101) · 2/5 — filter-bank convolution for BCI spellers
- [How AI Is Helping Care Teams Get Patients the Right Care, Sooner](https://blogs.nvidia.com/blog/how-ai-is-helping-care-teams/) · 1/5 — NVIDIA healthcare customer stories (lab_release)
- [Anthropic files S-1 with the SEC](https://www.anthropic.com/news/s1-sec) · 1/5 — proposed IPO registration (lab_release)
- [Anthropic launches roadshow for proposed IPO](https://www.anthropic.com/news/roadshow-launch) · 1/5 — (lab_release)
- [Voxtral 3](https://mistral.ai/news/voxtral-3/) · 1/5 — Mistral audio model (lab_release)
- [Introducing Timestral](https://mistral.ai/news/timestral/) · 1/5 — Mistral time-series model (lab_release)
- [Introducing Gemini 4 Hydrogen](https://deepmind.google/blog/introducing-gemini-4-hydrogen/) · 1/5 — Google DeepMind release (lab_release)
- [Google Search gets a major upgrade with Gemini 4 Hydrogen](https://blog.google/products-and-platforms/products/search/gemini-4-hydrogen-search-upgrade/) · 1/5 — (lab_release)
- [Introducing Muse Spark Meta Model API](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/) · 1/5 — Meta AI release (lab_release)
- [How Meta's AI Models Are Powering the Genesis Mission](https://ai.meta.com/blog/genesis-mission-lawrence-berkeley-national-laboratory-segment-anything-dino/) · 1/5 — (lab_release)
- [Zyphra/ZONOS3-Mini](https://huggingface.co/Zyphra/ZONOS3-Mini) (HF Model) · 2/5 — TTS model, 332 likes, 19.7K downloads, momentum 0.28
- [Angais/pixel-art-atlas-1.4m](https://huggingface.co/datasets/Angais/pixel-art-atlas-1.4m) (HF Dataset) · 3/5 — 1.4M pixel-art images, CC0, 474 likes, 57.6K downloads, momentum 0.59

**Story arcs** (observed ≥3 consecutive runs with rising traction):
- [nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B) — streak 9, +1.0% mag
- [HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor) — streak 9, +0.6% mag
- [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) — streak 6, +0.6% mag
- [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) — streak 6, +0.3% mag
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — streak 6, +0.2% mag
- [ccch1mneyyy/dsh-Go](https://github.com/ccch1mneyyy/dsh-Go) — streak 3, +1.4% mag
- [Vyber07/cyber-security](https://huggingface.co/datasets/Vyber07/cyber-security) — streak 3, +1.6% mag
- [venvoo/china-a-share-l2-level2-limit-order-book-tick-data](https://huggingface.co/datasets/venvoo/china-a-share-l2-level2-limit-order-book-tick-data) — streak 3, +0.6% mag
- [wangzan101/Mika](https://github.com/wangzan101/Mika) — streak 3, +0.5% mag
- [nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets) — streak 3, +0.4% mag

## Action items

**Read:** [Nvidia allegedly engineered scarcity by funding AI startups to buy its GPUs](https://www.techpowerup.com/354814/nvidia-allegedly-engineered-scarcity-by-funding-ai-startups-to-buy-its-gpus) — understand the supply-chain narrative moving markets; cross-reference with NVIDIA's own cuPhoton/cuBLAS releases today.

**Try:** [Balanov/shim](https://github.com/Balanov/shim) — zero-dependency local AI harness with MCP and agent skills; useful for prototyping tool-calling loops without cloud APIs.

**Track:** [Edge0/Edge0-145B-NVFP4](https://huggingface.co/Edge0/Edge0-145B-NVFP4) — 145B MoE at 4-bit NVFP4; watch for quantization recipes and edge-inference benchmarks as the latent-MoE architecture matures.

---

Collection was incomplete: lab_blogs.
