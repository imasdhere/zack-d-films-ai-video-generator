# Cost report

## Spent

**$0.00.** No credits, subscriptions, paid APIs or paid cloud GPUs were used. All generation ran on the session's CPU container: TTS, images, depth, 3D, compositing, encoding and audio.

## Free and open-source components used

Qwen3-TTS, Kokoro, ComfyUI, SDXL + SDXL-Lightning, Depth-Anything-V2-Small, Blender (bpy), Whisper, FFmpeg, NumPy/SciPy/OpenCV/Pillow, rasterio. Data: Tanzil, Copernicus DEM, Natural Earth, NASA, Wikimedia Commons. All were free to use, subject to the licences in `licensing_report.md`.

## Optional paid services that could raise quality (NOT used; need approval)

Prices are indicative ranges for late 2026 and must be checked with each provider before any purchase. They are not quotes.

| Service type | What it would improve | Typical pricing model | Rough estimate for this film |
|---|---|---|---|
| Cloud GPU (e.g. a 24–48 GB GPU, hourly) | Native 4K SDXL/FLUX images; real AI video clips (Wan 2.2, LTX-2) instead of 2.5-D parallax | per GPU-hour | About 10–20 GPU-hours ≈ US$10–60 |
| Hosted image generation API | Faster, higher-resolution stills | per image | 60–120 images ≈ US$3–15 |
| Hosted video generation API | 5–10 s AI video shots | per second of video | 40–80 short clips ≈ US$20–200+ |
| Premium TTS API | Alternative narrator voices, studio-grade prosody | per character | About 18,000 characters ≈ US$5–40 |
| Stock footage licence | Real aerial footage of Dhofar and the Rubʿ al-Khālī | per clip | US$50–300 per clip |

## One-time vs recurring

- One-time: none incurred. A future 4K/AI-video upgrade would be a one-time GPU rental of about US$10–60.
- Recurring: none. Storage stays local or in the user's own GitHub repository.

## Version 2 (cloned narration)

**$0.00.** VoxCPM2 and Audar-TTS-V1-Flash are open weights and ran locally. No hosted voice API was used. The Audar
hosted API and the Audar Pro tier (enterprise licence) were not used. Hugging Face access to the gated NeuCodec model is free.

| Asset | CPU time on this container |
|---|---|
| 1 minute of cloned narration (VoxCPM2, reference mode) | about 3.7 min |
| Voice-cloning evaluation (4 VoxCPM2 tests, 1 Qwen3 baseline, mode A/B, pronunciation probe) | about 50 min |
| Full version 2 narration (210 English + 5 Arabic chunks) | about 65 min |

## Cost per asset (actual, compute-only)

| Asset | CPU time on this container |
|---|---|
| 1 SDXL-Lightning image, 1344×768, 4 steps (landscapes) | about 100 s (about 20 s per step on 4 cores) |
| 1 SDXL-Lightning image, 1344×768, 8 steps (reconstructions, legends) | about 175–190 s |
| 1 minute of narration (Qwen3-TTS 1.7B clone, CPU) | about 5.5 min |
| 1 minute of final 1080p video (compositor + x264) | about 4 min for one process alone; about 12 min per process with 4 in parallel |
| Whole project, wall clock | about 7 h (11:13–18:15), all on a 4-vCPU CPU-only container |
