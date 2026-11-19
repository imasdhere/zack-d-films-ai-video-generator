# Dependency register

Selection principle: use the smallest toolchain that delivers the required quality on the available hardware (CPU only, 15 GiB RAM). No repository was forked. Where a candidate was not adopted, the reason is recorded.

## Adopted

| Function | Component | Version / commit | Install method | Software licence | Model / data licence | Notes |
|---|---|---|---|---|---|---|
| Narration (primary) | Qwen3-TTS — github.com/QwenLM/Qwen3-TTS | `qwen-tts` 0.1.1 (PyPI); models `Qwen3-TTS-12Hz-1.7B-VoiceDesign`, `…-1.7B-Base`, `Qwen3-TTS-Tokenizer-12Hz` | `uv pip install qwen-tts` (venv `qwen`, Py 3.12, transformers 4.57.3) | Apache-2.0 | Apache-2.0 (Hugging Face model cards) | CPU bf16. Voice designed once, then cloned. |
| Narration v2 (English and Arabic clones) | VoxCPM2 — github.com/OpenBMB/VoxCPM | `voxcpm` 2.0.3 (PyPI); weights `openbmb/VoxCPM2` | `uv pip install voxcpm==2.0.3 torch==2.15.0` (venv `voxcpm`, Py 3.12) | Apache-2.0 | Apache-2.0 | CPU bf16 (AMX). 2B parameters, 48 kHz output. "Ultimate" cloning: reference clip + transcript. About 11.5 GB RAM. |
| Narration v2 (candidate) | Audar-TTS-V1-Flash — github.com/AudarAI/Audar-TTS-V1 (cloned to `/home/user/imasdhere/audar-tts-v1` @ 8316d3f) | weights `audarai/Audar-TTS-V1-Flash` (`transformers/`), codec `neuphonic/neucodec` | venv `audar`: torch 2.15, transformers ≥4.57, neucodec 0.0.6 | Apache-2.0 (reference code) | AudarAI Open License v1.0; NeuCodec Apache-2.0 (gated) | Adapter and worker ready. Not run: the gated codec could not be downloaded. |
| Voice QA | Whisper large-v3-turbo; WavLM-base-plus-sv; torchaudio SQUIM | `openai/whisper-large-v3-turbo`; `microsoft/wavlm-base-plus-sv` | transformers (venv `ml`) | MIT / MIT / BSD | MIT / MIT (model cards) | Arabic and English ASR, speaker similarity, signal-quality estimates |
| Dereverberation test | nara_wpe 0.0.11 | — | pip (venv `ml`) | MIT | — | WPE was tested on the Arabic reference. Not adopted, because it made the tail worse. |
| Quran text (second orthography) | Tanzil Simple (diacritised) | `research/raw_sources/quran/quran-simple.txt` | tanzil.net download | — | Tanzil terms (verbatim, attribution) | Quranic n-gram scan and the second rendering variant; quran.com API v4 for the cross-check |
| Narration (backup) | Kokoro — github.com/hexgrad/kokoro (user fork `imasdhere/kokoro` @ dfb907a) | `kokoro` 0.9.4, `misaki` 0.9.4; weights `hexgrad/Kokoro-82M` | pip (venv `ml`) | Apache-2.0 | Apache-2.0 | Voice `bm_lewis` |
| Image generation | ComfyUI — user fork `imasdhere/ComfyUI` @ 995456d (v0.46.0) | — | local checkout; `pip install -r requirements.txt` (venv `comfy`) | GPL-3.0 | — | Headless API, `--cpu --bf16-unet` |
| Image model | Stable Diffusion XL base 1.0 | `sd_xl_base_1.0.safetensors` | Hugging Face | — | CreativeML **OpenRAIL++-M** (commercial use allowed, with use-based restrictions) | |
| Image speed-up | SDXL-Lightning (ByteDance) | `sdxl_lightning_8step_lora.safetensors` | Hugging Face | — | OpenRAIL++ | 8 steps, CFG 1 |
| VAE | madebyollin/sdxl-vae-fp16-fix | `sdxl_vae.safetensors` | Hugging Face | — | MIT | |
| Depth for parallax | Depth-Anything-V2-Small (HF) | `depth-anything/Depth-Anything-V2-Small-hf` | transformers | — | Apache-2.0 | Small model only. Base/Large are CC-BY-NC. |
| 3D layouts & schematic | Blender as a Python module | `bpy` 5.3.0 (PyPI, Python 3.13) | `uv pip install bpy==5.3.0` (venv `blender`) | GPL-3.0 | — | Cycles CPU. The user's `blender` fork is source only; no build needed. |
| Transcription / QC | OpenAI Whisper (user fork `imasdhere/whisper` @ 8609812) | `openai-whisper` 20250625; `small.en` | pip | MIT | MIT | WER checks |
| Encoding / audio | FFmpeg (system) | 6.1.1 (Ubuntu) | apt (pre-installed) | LGPL/GPL (build with `--enable-gpl`, libx264) | — | The user's `FFmpeg` fork was not built. The system binary is sufficient. |
| Compositing / editor | Custom Python (`scripts/editing/edit.py`): NumPy, OpenCV, Pillow (+raqm) | numpy 2.3, opencv-python-headless 5.1, pillow 12/13 | pip | BSD / Apache / MIT-CMU | — | Frame-accurate moves, parallax, crossfades, grade, overlays |
| Typography / diagrams | Custom Pillow renderer (`scripts/animation/graphics.py`) | — | — | — | Fonts: Amiri, Amiri Quran, Cinzel, EB Garamond (SIL OFL 1.1); Inter (OFL, system) | Arabic shaping via libraqm |
| Maps | Custom renderer (`scripts/animation/maps.py`) with rasterio | rasterio 1.5.2 | pip | BSD | Copernicus GLO-90 DEM (free, with attribution); Natural Earth (public domain) | |
| Sound design | Custom procedural synthesis (`scripts/editing/sfx.py`), SciPy | scipy 1.18 | pip | BSD | — | No samples, no music |
| Loudness | pyloudnorm 0.2 and FFmpeg `loudnorm` (EBU R128) | — | pip | MIT | — | |
| Research fetch | trafilatura, requests, Playwright (pre-installed) | — | pip | Apache / Apache / Apache | — | |

## Evaluated, not adopted

| Candidate | Finding (2026-11-19) | Decision |
|---|---|---|
| **Revideo** (redotvideo/revideo, now served from `midrender/revideo`) | MIT. `@revideo/*` 0.11.0 on npm (Jul 2026). Needs headless Chromium. Telemetry is on by default. | Not needed. A TypeScript/Node render stack adds no capability over the Python compositor for this film, and stills-based motion runs faster in-process. |
| **Manim Community** | v0.22.1 (Oct 2026), MIT. A major refactor is under way. | Not adopted. The explanatory graphics are typographic and cartographic. Pillow + OpenCV render them faster on CPU, with full Arabic shaping (raqm). Manim needs LaTeX/Cairo/Pango for comparable typography. |
| **MoviePy** | v2.2.1 (May 2025), MIT, "maintainers wanted". | Not adopted. Per-frame Python compositing in MoviePy is slower than direct NumPy/OpenCV with an FFmpeg pipe, and it adds no needed feature. |
| html-video (nexu-io) | Apache-2.0. Only the Hyperframes engine is built; Revideo/Manim adapters are on the roadmap. | Not adopted. No advantage. |
| Remotion (user fork) | Special licence (free for individuals and companies of ≤3 people; otherwise a company licence). | Not adopted. Licence and toolchain weight. |
| Fish Speech / OpenAudio | Fish Audio Community / Research licences; GPU-oriented | Excluded (weights licence, hardware). |
| CosyVoice 3 | Apache-2.0; heavy install (Python 3.10, submodules, NVIDIA Docker) | Not needed (Qwen3-TTS covers design plus clone). |
| VibeVoice | TTS-1.5B code removed (Sep 2025); Realtime-0.5B is research-only | Excluded. |
| F5-TTS | Weights CC-BY-NC-4.0 | Excluded (non-commercial). |
| Wan 2.2 (user fork) | TI2V-5B needs ≥24 GB VRAM | Not feasible on CPU. |
| LTX-Video / LTX-2 (user fork) | LTX-Video 0.9.x no longer developed. LTX-2.x weights about 66 GiB, GPU; Community License with a revenue threshold and a duty to disclose machine-generated content. | Not feasible on CPU. |
| WanGP (user fork) | GPU-poor Wan wrapper; still needs a GPU | Not feasible. |
| OpenAnimateMyMaps (OpenAMM, user fork) | MIT. Next.js + MapLibre browser studio; needs online map tiles (blocked) and interactive use | Not adopted. A programmatic DEM renderer gives reproducible, headless results. |
| mapcast (user fork) | A **Go library that casts `map[string]string` types**. Not a cartography tool. | Not relevant. |
| zack-d-films-ai-video-generator (host repo) | Pipeline built on the paid MuAPI / Veo services | Not used (paid). This project is stored inside it under `iram-documentary/`. |
| Z-Image-Turbo / FLUX.2-klein-4B | Apache-2.0, but each needs an ~8 GB text encoder plus a 4–6B diffusion model. Exceeds RAM with narration running; slow on CPU. | Not used. SDXL + Lightning fits the memory budget. |

## Virtual environments (outside the git repository)

| venv | Python | Purpose |
|---|---|---|
| `/home/user/iram-work/venvs/ml` | 3.12 | torch 2.15 (CPU use), Kokoro, Whisper, transformers 5.x, OpenCV, rasterio, editor |
| `/home/user/iram-work/venvs/qwen` | 3.12 | qwen-tts 0.1.1 (pins transformers 4.57.3) |
| `/home/user/iram-work/venvs/comfy` | 3.12 | ComfyUI requirements |
| `/home/user/iram-work/venvs/blender` | 3.13 | bpy 5.3.0 |

Model weights are in `/home/user/iram-work/models/` (about 17 GB). See `documentation/installation.md`.
