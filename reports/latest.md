<!-- radar:nav -->
`radar`  ·  [← 2026-11-19](2026-11-19-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-11-20

A wave of new diagnostic benchmarks for embodied AI leads today’s observations: Mind2Act World introduces a three-axis test for robotic manipulation, while ZeroVLN, WeMM-Video, EgoCaptioner, and TuringSpace each target a different gap in navigation, omni-modal video, egocentric captioning, and spatial reasoning. Simultaneously, a Hacker News discussion surfaced a paper claiming language models can rewrite their own weights, and a private/local AI desktop project gathered rapid GitHub traction.

## What changed

**New to radar** (498 items): [Mind2Act World](https://arxiv.org/abs/2611.26444), [ZeroVLN](https://arxiv.org/abs/2611.26414), [WeMM-Video](https://arxiv.org/abs/2611.26409), [EgoCaptioner](https://arxiv.org/abs/2611.26380), [Language Models Can Rewrite Their Own Weights](https://arxiv.org/abs/2611.21885) (HN), [open-webui-private-ai-desk](https://github.com/han938/open-webui-private-ai-desk), [Depth Pro 2](https://arxiv.org/abs/2611.26603), [TuringSpace](https://arxiv.org/abs/2611.25387), [blender-ai-mcp-addon](https://github.com/bookwjitchieni1986/blender-ai-mcp-addon)  
**Climbing** (6): [google/physical-engineerings-last-exam](https://huggingface.co/datasets/google/physical-engineerings-last-exam) (score 5→), [nvidia/USDCraft-10K](https://huggingface.co/datasets/nvidia/USDCraft-10K) (4→), [Digitaluz/uzbek-language-corpus](https://huggingface.co/datasets/Digitaluz/uzbek-language-corpus) (2→), [HubLabs/HubEgo-100K](https://huggingface.co/datasets/HubLabs/HubEgo-100K) (2→), [Jeveration](https://arxiv.org/abs/2611.24738), [inworld/voice-isolator](https://huggingface.co/inworld/voice-isolator)  
**Cooled** (1): [nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB) (score 2→1)

## Main list

### [Mind2Act World: A Diagnostic Benchmark for Embodied Mind, Physical Action, and Mind-Action Composition in Robotic Manipulation](https://arxiv.org/abs/2611.26444) · 4/5
Mind2Act World introduces a benchmark that separates history-based reasoning, precise physical execution, and their composition through environmental feedback across robotic manipulation tasks.  
Matters if you evaluate or build embodied agents and need diagnostics that pinpoint whether failures stem from reasoning, execution, or their interaction.  
Code: [github.com/Mind2Act/Mind2Act_World](https://github.com/Mind2Act/Mind2Act_World) · Project: [mind2act-world.com](https://mind2act-world.com/)

### [ZeroVLN: Learning to Navigate without Supervised Fine-Tuning of the VLM Brain](https://arxiv.org/abs/2611.26414) · 3/5
ZeroVLN presents a slow-fast navigation framework that keeps the vision-language model frozen and uses a semantic tool-calling interface for movement decisions, avoiding navigation-domain fine-tuning that degrades general visual capabilities.  
Matters if you deploy VLMs for robotics and want to preserve broad visual reasoning while adding navigation.  
Code: [github.com/hzx122/ZeroVLN](https://github.com/hzx122/ZeroVLN)

### [WeMM-Video: Pushing the Frontiers of Open-Source Omni-Modal Video Understanding](https://arxiv.org/abs/2611.26409) · 3/5
Tencent releases WeMM-Video, a family of bilingual (Chinese-English) omni-modal models (2B–35B) unifying text, image, audio, and video with hybrid thinking (fast instruct and slow reasoning modes).  
Matters if you need open-weight video-audio understanding at multiple scales and want a single model family covering both quick replies and step-by-step reasoning.  
Code: [github.com/Tencent/WeMM-Video](https://github.com/Tencent/WeMM-Video)

### [EgoCaptioner: Towards Comprehensive and Fine-Grained Egocentric Video Captioning](https://arxiv.org/abs/2611.26380) · 3/5
EgoCaptioner pairs a video-level overview with timed, adaptive narration steps and key-moment timestamps, plus a coarse-to-fine annotation pipeline to train MLLMs for detailed egocentric captioning.  
Matters if you build AR/VR assistants or activity-recognition systems that require precise, temporally grounded descriptions from first-person video.  
Code: [github.com/cactusqq/EgoCaptioner](https://github.com/cactusqq/EgoCaptioner) · Project: [cactusqq.github.io/EgoCaptioner/](https://cactusqq.github.io/EgoCaptioner/)

### [Language Models Can Rewrite Their Own Weights](https://arxiv.org/abs/2611.21885) · 3/5
A paper claiming that language models can directly modify their own parameters during inference surfaced on Hacker News (189 points, 84 comments), proposing a form of self-referential weight editing.  
Matters if you research model plasticity, continual learning, or inference-time adaptation mechanisms.  
Discussion: [news.ycombinator.com/item?id=50577265](https://news.ycombinator.com/item?id=50577265)

### [han938/open-webui-private-ai-desk](https://github.com/han938/open-webui-private-ai-desk) · 3/5
A local-first desktop wrapper around Open WebUI that lets users chat with private models offline, observed with 93 GitHub stars in its first day.  
Matters if you need a ready-to-run, privacy-focused UI for local LLM inference without cloud dependencies.  
(No separate project link; repository is the primary artifact.)

### [Depth Pro 2: Sharp and Temporally Consistent Metric Monocular Depth](https://arxiv.org/abs/2611.26603) · 3/5
Apple’s Depth Pro 2 delivers metrically accurate, boundary-sharp, and temporally consistent depth for both images and video at native resolution from a single scalable network.  
Matters if you work on 3D reconstruction, AR, or video effects and need monocular depth that doesn’t trade sharpness for consistency.  
Code: [github.com/apple-aiml-research/ml-depth-pro-2](https://github.com/apple-aiml-research/ml-depth-pro-2) · Project: [apple-aiml-research.github.io/ml-depth-pro-2/](https://apple-aiml-research.github.io/ml-depth-pro-2/)

### [TuringSpace: Grounding Spatial Intelligence in Action with Interactive CAPTCHAs](https://arxiv.org/abs/2611.25387) · 3/5
TuringSpace introduces 125 synthetic interactive CAPTCHAs spanning five spatial reasoning categories, requiring MLLMs to infer 3D layout, predict action outcomes, and self-correct — mimicking the human perception-action loop.  
Matters if you benchmark spatial reasoning in multimodal models or need a controllable environment for action-grounded evaluation.  
Code: [github.com/os-cua-framework/TuringSpace](https://github.com/os-cua-framework/TuringSpace) · Project: [xuweid.com/turingspace/](https://xuweid.com/turingspace/)

### [One Prior, Two Dynamics: Repurposing Video Diffusion Transformers for Self-Supervised Latent Action Learning](https://arxiv.org/abs/2611.26617) · 2/5
O²LaF initializes both inverse and forward dynamics models from the same pretrained video DiT, adapting them to distinct roles for latent action learning from visual transitions.  
Matters if you explore using video generation priors for robotics action representation without learning dynamics from scratch.  
Code: [github.com/showlab/O2LaF](https://github.com/showlab/O2LaF) · Project: [showlab.github.io/o2laf/](https://showlab.github.io/o2laf/)

### [AgentRoboCritic: Understanding the Capability of Frontier Agents on Direct Robot Control](https://arxiv.org/abs/2611.26613) · 2/5
AgentRoboCritic provides an action-level critique framework where frontier agents (e.g., GPT-6 Astra) state local intent per action across 12 manipulation benchmarks, moving beyond episode-level success rates.  
Matters if you evaluate or debug low-level robot control policies and need fine-grained failure attribution.  
(No public code link observed; paper is the primary artifact.)

## Watch-list / Still developing

- [HuggingFaceFW/fineweb-edu](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) — 447K downloads, 1.4K likes (2 runs tracked)  
- [Digitaluz/uzbek-language-corpus](https://huggingface.co/datasets/Digitaluz/uzbek-language-corpus) — 59 likes, 877 downloads (2 days on radar)  
- [Why a Computer Scientist Thinks Superintelligence Won’t Happen](https://spectrum.ieee.org/ai-superintelligence-debate) (IEEE Spectrum, 2 days)  
- [Meet Shepherd, the Meta-Agent Keeping Rogue AI In Check](https://spectrum.ieee.org/ai-agent-manager) (IEEE Spectrum, 2 days)  
- [sensenova/SenseNova-Loop-9B](https://huggingface.co/sensenova/SenseNova-Loop-9B) — 427 likes, 1.6K downloads (4 days, rising)  
- [tencent/Hy4-flash](https://huggingface.co/tencent/Hy4-flash) — 511 likes, 3.9K downloads (3 days, rising)  
- [bookwjitchieni1986/blender-ai-mcp-addon](https://github.com/bookwjitchieni1986/blender-ai-mcp-addon) — 1,354 stars (new, multi-agent Blender copilot via MCP)  

**Story arcs** (rising traction ≥3 consecutive runs):  
[Sage S2.1 Flash Technical Report](https://arxiv.org/abs/2611.21072) (4-day streak), [Vyber07/cyber-security](https://huggingface.co/datasets/Vyber07/cyber-security) (9-day), [ccch1mneyyy/dsh-Go](https://github.com/ccch1mneyyy/dsh-Go) (9-day), [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) (12-day), [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) (12-day), [wangzan101/Mika](https://github.com/wangzan101/Mika) (9-day), [nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets) (9-day), [venvoo/china-a-share-l2-level2-limit-order-book-tick-data](https://huggingface.co/datasets/venvoo/china-a-share-l2-level2-limit-order-book-tick-data) (9-day), [TeleChat to Xing4](https://arxiv.org/abs/2611.22115) (3-day), [nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB) (3-day, though cooled this run)

## Action items

1. **Read** the [Mind2Act World](https://arxiv.org/abs/2611.26444) paper and [GitHub repo](https://github.com/Mind2Act/Mind2Act_World) for a clean three-axis benchmark design you can adapt to your own embodied evaluation.  
2. **Try** [ZeroVLN’s](https://github.com/hzx122/ZeroVLN) semantic tool-calling navigation approach if you need VLM-based robot navigation without full fine-tuning.  
3. **Track** [FineWeb-Edu](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) — its download velocity (447K observed) makes it a de facto standard for educational-content filtering in LLM pretraining.

---

Collection was incomplete: lab_blogs.
