<!-- radar:nav -->
`radar`  ·  [← 2026-11-10](2026-11-10-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-11-12

The strongest signals center on making agents more reliable: WikiTrace shows evidence-linked memory cuts degradation in LLM agents, Tree-Ising repairs models via bit-level weight edits without gradients, and MMDM introduces a benchmark for massive multitask decision-making. Meanwhile, a Google SWE team deployed 48 agents to discover an unmapped Maya pyramid in 72 hours, and NVIDIA refactors Kubernetes for agent-scale idle time.

## What changed

**New to radar:** [Don't Just Trust Your Memory: Evidence-Linked Memory Reduces Memory-Induced Degradation in LLM Agents](https://arxiv.org/abs/2611.14320) · [Tree-Ising: Repairing Language Models with Bit-Level Ising Edits](https://arxiv.org/abs/2611.14210) · [microsoft/TokenEconomizer](https://github.com/microsoft/TokenEconomizer) · [MMDM: Measuring Massive Multitask Decision Making](https://arxiv.org/abs/2611.14309) · [Few-Step Streaming Video Generation via Condition Shifting](https://arxiv.org/abs/2611.14033)

**Climbing:** [MiniMaxAI/MiniMax-H3-Image](https://huggingface.co/MiniMaxAI/MiniMax-H3-Image)

**Cooled:** [SWAM: Scaling World Action Models with Cross-Modal Alignment](https://arxiv.org/abs/2611.12870) · [nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B)

## Main list

### Agents

[Don't Just Trust Your Memory: Evidence-Linked Memory Reduces Memory-Induced Degradation in LLM Agents](https://arxiv.org/abs/2611.14320) · 4/5  
Researchers introduced WikiTrace, a method that links agent memory lessons to their source trajectories so agents can verify lessons before applying them, reducing memory-induced failures. Matters if you build agents that learn from experience. [GitHub](https://github.com/yukyeongleee/wikitrace) · [Project](https://yukyeongleee.github.io/wikitrace/)

[Lazare, veni foras: Reprogramming Dormant Neurons to Backdoor AI Agents](https://www.microsoft.com/en-us/research/blog/lazare-veni-foras-reprogramming-dormant-neurons-to-backdoor-ai-agents/) · 1/5  
Microsoft Research details a backdoor technique that repurposes dormant neurons to trigger malicious behavior in agents with tool access. Matters if you secure agent deployments against supply-chain or weight-space attacks.

[Cogent and OpenAI build cyber defense factories for enterprises](https://openai.com/index/cogent-security) · 1/5  
OpenAI partners with Cogent to combine models with enterprise context for automated vulnerability remediation via agents. Matters if you run enterprise security automation.

[Agent Substrate: Advancing Kubernetes for Agents at Scale](https://developer.nvidia.com/blog/agent-substrate-advancing-kubernetes-for-agents-at-scale/) · 1/5  
NVIDIA proposes Kubernetes extensions to handle agent idle time, tool waits, and model response latency at scale. Matters if you orchestrate agent fleets on Kubernetes.

[Google SWE points 48 AI agents at NASA Lidar, finds unmapped Maya pyramid in 72h](https://pietromiotti.com/latest/maya-site/?maya) · 2/5  
A Google software engineer deployed 48 agents to process NASA lidar data, discovering a previously unmapped Maya pyramid in three days. Matters if you explore multi-agent scientific discovery workflows. [Discussion](https://news.ycombinator.com/item?id=50452455)

[Q3.5 Timelines Update: Looks Like the Intelligence Explosion Will Happen in 2027 After All](https://www.alignmentforum.org/posts/f9PajMLmBYzmWzyDv/q3-5-timelines-update-looks-like-the-intelligence-explosion) · 2/5  
An updated timeline model incorporating METR's 17x progress speedup estimate suggests recursive AI improvement could arrive in 2027. Matters if you plan long-term compute or research strategy.

### Evaluation

[Tree-Ising: Repairing Language Models with Bit-Level Ising Edits](https://arxiv.org/abs/2611.14210) · 4/5  
A new method casts model repair as sparse discrete optimization over BF16 weights, weakening reasoning loops and strengthening correct directions without gradients, using forward-pass statistics. Matters if you debug or patch model behavior post-training. [GitHub](https://github.com/TheQuantumGOAT/Tree-Ising)

[MMDM: Measuring Massive Multitask Decision Making](https://arxiv.org/abs/2611.14309) · 3/5  
A new benchmark evaluates System-1 decision models on long-context, large-option-space tasks with complex logical dependencies, addressing gaps in existing benchmarks. Matters if you evaluate or serve decision-making models. [GitHub](https://github.com/mmdm-benchmark/mmdm) · [Project](https://mmdm-benchmark.github.io/)

[Mitra-v2: Scaling synthetic pretraining for tabular foundation models](https://www.amazon.science/blog/mitra-v2-scaling-synthetic-pretraining-for-tabular-foundation-models) · 1/5  
Amazon Science shows expanding synthetic pretraining data lets a single tabular foundation model adapt to new tables without retraining, leading TabArena. Matters if you work with tabular data and foundation models.

### Other

[Few-Step Streaming Video Generation via Condition Shifting](https://arxiv.org/abs/2611.14033) · 3/5  
Extends APEX to streaming video by using condition shifting to estimate velocity fields within the generator, removing the need for a separate fake-score network. Matters if you optimize video diffusion inference. [Project](https://www.vidu.com/vidu-stream/avatar)

## Still developing

[pathwaycom/serviette](https://github.com/pathwaycom/serviette) · 3/5 — No-code RAG server syncing answers with documents across 8 vector databases (58.7k stars, 3 runs)

[infiniflow/ragflow](https://github.com/infiniflow/ragflow) · 3/5 — Agent-native RAG engine evolved into context infrastructure (94k stars, 4 runs)

[Angais/pixel-art-atlas-1.4m](https://huggingface.co/datasets/Angais/pixel-art-atlas-1.4m) · 3/5 — 1.4M pixel art images, CC0, 41.6k downloads (4 runs)

[NousResearch/arete-data-pairs](https://huggingface.co/datasets/NousResearch/arete-data-pairs) · 2/5 — Preference pairs for text generation and QA, 1.3k downloads (6 runs)

### Story arcs (rising traction ≥3 runs)

[Intrinsic Distribution Matching](https://arxiv.org/abs/2610.39633) — 13-day streak, +13.3% traction

[vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) — 14-day streak, agent memory that learns

[DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) — 14-day streak, token-saving coding agent proxy

[paperclipai/paperclip](https://github.com/paperclipai/paperclip) — 14-day streak, agent management app

[rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch) — 13-day streak, from-scratch LLM implementation

## Action items

- **Read:** [WikiTrace paper](https://arxiv.org/abs/2611.14320) and [GitHub](https://github.com/yukyeongleee/wikitrace) for evidence-linked agent memory.
- **Try:** [Tree-Ising](https://github.com/TheQuantumGOAT/Tree-Ising) for gradient-free model repair on your own checkpoints.
- **Track:** [MMDM benchmark](https://github.com/mmdm-benchmark/mmdm) as a new standard for decision-model evaluation.

---

Collection was incomplete: lab_blogs.
