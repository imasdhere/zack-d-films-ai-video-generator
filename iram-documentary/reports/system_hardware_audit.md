# System hardware audit

Date: 2026-11-19.

## Important: this was not a Mac

The brief assumed Claude Code was running on a Mac. It was not. The session ran in a **managed Linux cloud container** (Claude Code on the web). No Mac or other local machine was attached: `list_computer_folders` returned no folders. Every result below describes that container. If you re-run the pipeline on an Apple Silicon Mac, read the "Mac notes" section.

| Item | Value |
|---|---|
| Machine | KVM virtual machine (cloud container) |
| OS | Ubuntu 24.04.5 LTS, Linux 6.18 x86_64 |
| CPU | Intel Xeon (Sapphire-Rapids class: AVX-512, AVX-512-BF16, AMX-BF16/INT8), **4 vCPU** |
| RAM | 15 GiB total, no swap. The memory cgroup kills processes above roughly 14 GiB. |
| GPU | **None** (no CUDA, no Metal) |
| Disk | 58 GB free at start (252 GB volume) |
| Python | 3.13.18 (system). Python 3.12 virtual environments were created with `uv`. |
| Node.js | 22.23 (pnpm, npm available) |
| FFmpeg | 6.1.1 (Ubuntu build: libx264, libx265, loudnorm, xfade, libass, zscale) |
| Docker | 29.10 (not needed) |
| Homebrew | not applicable (Linux) |
| Browser | Chromium + Playwright (pre-installed) |
| Network | Allow-list proxy. Hugging Face, PyTorch CDN, Whisper weights, Wikimedia, Tanzil and the research sites were added with the user's approval. |

## What can run locally on this hardware

| Task | Feasible? | Measured performance | Decision |
|---|---|---|---|
| TTS: Kokoro-82M | Yes | about 5× faster than real time | Backup engine |
| TTS: Qwen3-TTS 1.7B (bf16, CPU) | Yes, slowly | about 4.3–5.7× slower than real time | **Primary engine**. About 2 h for the whole film. |
| Image generation: SDXL + Lightning (ComfyUI, CPU, bf16) | Yes, slowly | see `reports/production_log.md` | Used. Must not run alongside narration, because it was killed for lack of memory at 11 GB RSS. |
| Video generation: Wan 2.2 TI2V-5B | **No** | README requires ≥24 GB VRAM | Not attempted |
| Video generation: LTX-Video / LTX-2 | Not practical | LTX-2 needs about 66 GiB of weights and a GPU. LTX-Video 0.9.x is no longer developed. | Not attempted. Camera motion was made with 2.5-D depth parallax instead. |
| Blender (bpy 5.3, Cycles CPU) | Yes | 480×270 test about 5 s; 1344×768 at 32 samples about 1–2 min | Used for the layout/schematic renders |
| Whisper `small.en` | Yes | — | Used for TTS evaluation and transcript QC |
| Depth estimation (Depth-Anything-V2-Small) | Yes | about 1–2 s per image | Used for parallax |
| H.264 encoding (x264) and compositing | Yes | about 6 fps at 1080p per process (Python compositor) | Chapters are rendered in parallel |

## Why 1080p and not 4K

The source images are generated at 1344×768 and upscaled. Rendering at 4K would cost four times as much CPU time and add no real detail. The master is **1920×1080, 24 fps, H.264**, which meets the minimum. A 4K master would need GPU image generation at higher native resolution, or a hosted upscaler (paid; not used).

## Mac notes (Apple Silicon)

- Use PyTorch with the MPS backend. ComfyUI supports MPS: run `python main.py` without `--cpu`. SDXL images then take seconds instead of minutes.
- Kokoro: set `PYTORCH_ENABLE_MPS_FALLBACK=1`.
- Qwen3-TTS: officially CUDA-oriented. It works on CPU. MPS support is not documented, so test before you rely on it.
- `bpy` wheels exist for macOS arm64. Alternatively install Blender.app and run the scripts with `blender -b -P`.

## Version 2 voice engines (measured 2026-11-19)

The same container (4 vCPU Xeon with AMX-BF16, 15 GiB RAM, no GPU, Linux, not a Mac). Disk reads of model weights run at about 50 MB/s, so a cold model load takes 1–2 minutes.

| Engine | Precision / device | Speed (compute ÷ audio) | Peak RAM | Fits alongside other jobs? |
|---|---|---|---|---|
| VoxCPM2 (2B), reference-mode cloning | bf16, CPU (AMX) | 3.6–3.8× slower than real time | 10.7–11.3 GB | No. Run it alone (Whisper large-v3-turbo, about 4 GB more, would exceed the 14 GiB limit). |
| VoxCPM2, ultimate-mode cloning | bf16, CPU | 4.1–4.3× | 11.2–11.5 GB | No |
| Qwen3-TTS 1.7B Base clone (baseline) | bf16, CPU | 4.7× | about 6 GB | With light jobs only |
| Audar-TTS-V1-Flash (0.55B) | float32, CPU (Transformers) | not measured: the NeuCodec codec is gated | expected 3–4 GB | — |
| Whisper large-v3-turbo + WavLM-SV (QA) | float32, CPU | about 2 s per chunk | about 4 GB | Yes, when no TTS model is loaded |

The full English narration (about 18 minutes of speech) takes about one hour with VoxCPM2 on this machine.

### Mac notes for the voice engines

- VoxCPM2 can use MPS (`device='mps'` in the worker). Plan for 16 GB of unified memory or more, and compare a test sample against the CPU result before a full run.
- Audar-TTS-V1-Flash/Turbo also ship as GGUF for llama.cpp, which runs on Metal. The NeuCodec codec (PyTorch) still runs on CPU or MPS.
- CUDA-only paths (flash-attention, `torch.compile` with Triton) are not needed. The workers disable `torch.compile`.
