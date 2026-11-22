<!-- radar:nav -->
`radar`  ·  [← 2026-11-21](2026-11-21-digest.md)  ·  [index](README.md)  ·  _newest_ →
<!-- /radar:nav -->

# AI Radar — 2026-11-22

Anthropic's IPO closure dominated developer discussion (557 HN points) while OpenAI published a framework for perplexity-based capability evaluation. Concurrently, two single-forward-pass generation papers — Jeveration and Sage S2.1 Flash — showed strongly rising traction across six and four radar runs respectively, and a wave of new desktop agents (Claude Windows, Roamies, Blender MCP) entered the radar alongside MoE model variants (Inkling family).

## What changed

**New to radar**  
- [christinesoft17/claude-desktop-app-win](https://github.com/christinesoft17/claude-desktop-app-win) · 3/5 — Unofficial Windows build of Anthropic's desktop assistant.  
- [bookwjitchieni1986/blender-ai-mcp-addon](https://github.com/bookwjitchieni1986/blender-ai-mcp-addon) · 3/5 — MCP server and visual chat addon for Blender with multi-agent support.  
- [dodo-labs-ai/mem-forge](https://github.com/dodo-labs-ai/mem-forge) · 3/5 — Memory layer for agents citing team knowledge.  
- [KenKaiii/Roamies](https://github.com/KenKaiii/Roamies) · 3/5 — Desktop AI creatures that remember tasks and point at screen elements.  
- [ILSVRC/imagenet-1k (HF Dataset)](https://huggingface.co/datasets/ILSVRC/imagenet-1k) · 3/5 — Classic benchmark dataset resurfaced on Hugging Face.

**Climbing**  
- [nvidia/PhysicalAI-Human-1M-100K (HF Dataset)](https://huggingface.co/datasets/nvidia/PhysicalAI-Human-1M-100K) · 4/5 — Large-scale human motion dataset for physical AI.  
- [codepawl/cmu-mocap-glb (HF Dataset)](https://huggingface.co/datasets/codepawl/cmu-mocap-glb) · 2/5 — CMU motion capture in GLB format.  
- [JaimeMaLangue/JML-fon-speech-v1 (HF Dataset)](https://huggingface.co/datasets/JaimeMaLangue/JML-fon-speech-v1) · 2/5 — Fon language speech dataset.  
- [KORMo-VL/Ko-Online-Mind2Web (HF Dataset)](https://huggingface.co/datasets/KORMo-VL/Ko-Online-Mind2Web) · 2/5 — Korean web agent benchmark.  
- [AJ-Gonzalez/qwen4-max-reasoning-250x (HF Dataset)](https://huggingface.co/datasets/AJ-Gonzalez/qwen4-max-reasoning-250x) · 2/5 — Reasoning traces from Qwen4-Max.

**Cooled**  
- [nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB (HF Model)](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB) · 2/5 — Small Nemotron variant lost traction.

## Main list

[Perplexity and Intelligence](https://openai.com/index/perplexity-and-intelligence) · 1/5  
OpenAI published a blog proposing perplexity as a shared metric for tracking emerging model capabilities. Matters if you need a common yardstick for eval across labs. Lab release.

[Show HN: I built a game where you are an LLM's subagent](https://github.com/gulivan/worker755) · 2/5  
A browser game casting the player as a subagent executing tasks for an LLM supervisor, currently 148 HN points. Matters if you explore human-in-the-loop agent UX patterns. [Discussion](https://news.ycombinator.com/item?id=50599762)

[87% of the Anthropic power will come from gas and 11% from coal in 2028](https://betterdatacenterproject.com/2026/11/16/how-ai-is-powered-a-breakdown-of-byop-and-grid-power/) · 2/5  
Analysis of Anthropic's projected energy mix sparked 557-point HN debate on data-center power sourcing. Matters if you track infrastructure constraints for frontier model deployment. [Discussion](https://news.ycombinator.com/item?id=50597612)

[christinesoft17/claude-desktop-app-win](https://github.com/christinesoft17/claude-desktop-app-win) · 3/5  
Community-built Windows port of Anthropic's Claude desktop app reached 329 stars in one day. Matters if you need a native Windows wrapper for Claude's document analysis and automation features.

[AtomicChat/Inkling-2-Mini-Uncensored-GGUF (HF Model)](https://huggingface.co/AtomicChat/Inkling-2-Mini-Uncensored-GGUF) · 2/5  
Uncensored LoRA fine-tune of the Inkling-2-Mini MoE model, 129k downloads observed. Matters if you run local vision-language MoE models via llama.cpp.

[Jeveration: System One Models Now Generate](https://arxiv.org/abs/2611.24738) · 3/5  
Paper shows frozen vision-language models can be repurposed for single-pass image generation; 122 GitHub stars, 149 HF upvotes, traction rising 2.8× over 4 runs. Matters if you research efficient generative backbones. [Code](https://github.com/Carol-lyh/Jeveration) · [Project](https://carol-lyh.github.io/Jeveration/)

[Sage S2.1 Flash Technical Report](https://arxiv.org/abs/2611.21072) · 3/5  
320B MoE model with dedicated scientific encoders (molecular graphs, spectra); 36 stars, 98 HF upvotes, traction rising 2.0× over 6 runs. Matters if you build scientific reasoning agents. [Code](https://github.com/InternLM/Sage-S2.1-Flash) · [Project](https://internlm.github.io/Sage-S2.1-Flash/)

[unsloth/Inkling-2-Mini-GGUF (HF Model)](https://huggingface.co/unsloth/Inkling-2-Mini-GGUF) · 2/5  
Unsloth-quantized GGUF of the Inkling-2-Mini MoE (image-text-to-text), 805k downloads, 817 likes. Matters if you serve MoE vision-language models locally. Matches focus: mixture-of-experts.

[han938/open-webui-private-ai-desk](https://github.com/han938/open-webui-private-ai-desk) · 3/5  
Local-only Open WebUI distribution for private model chat, 151 stars in 3 days. Matters if you deploy air-gapped LLM interfaces for teams.

[How Google Duplex evolved to also call businesses for you in Gemini](https://research.google/blog/how-google-duplex-evolved-to-also-call-businesses-for-you-in-gemini/) · 1/5  
Google Research details Duplex's integration into Gemini for automated business calling. Matters if you study production voice-agent pipelines. Lab release.

## Watch-list / Still developing

- [TheAgenticDataCompany/open-yap-1k (HF Dataset)](https://huggingface.co/datasets/TheAgenticDataCompany/open-yap-1k) · 3/5 — Audio TTS/ASR dataset, 8.3k downloads, 270 likes, 3 runs tracked.  
- [HuggingFaceFW/fineweb-edu (HF Dataset)](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) · 3/5 — 1B+ token educational web corpus, 460k downloads, 1.4k likes, 4 runs tracked.  
- [Anthropic announces closing of initial public offering](https://www.anthropic.com/news/ipo-close) · 1/5 — IPO closure announcement, 3 runs tracked. Lab release.  
- [Anthropic prices initial public offering](https://www.anthropic.com/news/anthropic-prices-initial-public-offering) · 1/5 — Pricing details, 4 runs tracked. Lab release.  
- [Voxtral 3](https://mistral.ai/news/voxtral-3/) · 1/5 — Mistral audio model, 11 runs tracked. Lab release.  
- [Introducing Timestral](https://mistral.ai/news/timestral/) · 1/5 — Mistral time-series model, 11 runs tracked. Lab release.  
- [Introducing Muse Spark Meta Model API](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/) · 1/5 — Meta model API, 11 runs tracked. Lab release.  
- [Meta AI Models Powering Genesis Mission](https://ai.meta.com/blog/genesis-mission-lawrence-berkeley-national-laboratory-segment-anything-dino/) · 1/5 — Scientific deployment case study, 11 runs tracked. Lab release.

## Story arcs

- [Jeveration: System One Models Now Generate](https://arxiv.org/abs/2611.24738) — seen 4 runs, traction +59.7% since first seen on 2026-11-19.
- [Sage S2.1 Flash Technical Report](https://arxiv.org/abs/2611.21072) — seen 6 runs, traction +44.5% since first seen on 2026-11-17.
- [Vyber07/cyber-security (HF Dataset)](https://huggingface.co/datasets/Vyber07/cyber-security) — seen 11 runs, traction +5.9% since first seen on 2026-11-12.
- [ccch1mneyyy/dsh-Go — dsh-go — DeepSeek Harness 装进口袋：手机本机运行，也能遥控你的电脑。](https://github.com/ccch1mneyyy/dsh-Go) — seen 11 runs, traction +4.3% since first seen on 2026-11-12.
- [nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB (HF Model)](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB) — seen 5 runs, traction +4.1% since first seen on 2026-11-18.
- [venvoo/china-a-share-l2-level2-limit-order-book-tick-data (HF Dataset)](https://huggingface.co/datasets/venvoo/china-a-share-l2-level2-limit-order-book-tick-data) — seen 11 runs, traction +2.6% since first seen on 2026-11-12.
- [TeleChat to Xing4: Advancing Frontier Agentic Models on Domestic Chips and Frameworks](https://arxiv.org/abs/2611.22115) — seen 5 runs, traction +2.3% since first seen on 2026-11-18.
- [mdiri-ai/SoduWork — The AI-native engine for teams and their agents. Multi-harness, multi-agent, self-hosted.](https://github.com/mdiri-ai/SoduWork) — seen 3 runs, traction +1.8% since first seen on 2026-11-20.
- [wangzan101/Mika — An on-device AI agent for Android that operates apps and the web to get things done for you.](https://github.com/wangzan101/Mika) — seen 11 runs, traction +1.7% since first seen on 2026-11-12.
- [nvidia/simready-assets (HF Dataset)](https://huggingface.co/datasets/nvidia/simready-assets) — seen 11 runs, traction +1.6% since first seen on 2026-11-12.

## Action items

**Read** — [Perplexity and Intelligence](https://openai.com/index/perplexity-and-intelligence): OpenAI's proposed eval metric may shape how labs report capability progress.  
**Try** — [unsloth/Inkling-2-Mini-GGUF](https://huggingface.co/unsloth/Inkling-2-Mini-GGUF): Quantized MoE vision-language model ready for local inference via llama.cpp.  
**Track** — [Jeveration](https://github.com/Carol-lyh/Jeveration) and [Sage S2.1 Flash](https://github.com/InternLM/Sage-S2.1-Flash): Both papers show rising traction and offer single-forward-pass generation — a potential efficiency lever for diffusion/vision pipelines.

---

Collection was incomplete: lab_blogs.
