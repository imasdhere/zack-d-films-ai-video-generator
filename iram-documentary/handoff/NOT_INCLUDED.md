# Files that are NOT in the handoff archive

These files exist only in the cloud session's temporary container. When the session ends, they are deleted.
**Nothing in this list has been transferred to your Mac.** Each row says how to get the file back or rebuild it.
Cloud paths are relative to `/home/user/zack-d-films-ai-video-generator/iram-documentary/`, unless they start with `/home/user/iram-work/` (the cloud work folder).

| File or folder | Cloud location | Size | Why it is left out | How to get it |
|---|---|---|---|---|
| Version 3 master, 2560×1440 | `renders/final/iram_lost_city_documentary_1440p.mp4` | 4.3 GB | Too large for the archive | Rebuild it on the Mac: `bash scripts/narration/run_v3_render.sh` (README §3). Or, while the cloud session is still open, ask Claude to send it on its own. It may exceed the app's upload limit. |
| 1440p chapter renders | `renders/chapters_1440/chapter_0.mp4` … `chapter_7.mp4` | 4.3 GB | Intermediate; the master is made from them | Rebuilt by the same render command |
| Ambience stem | `assets/sound_effects/ambience_stem.wav` | 334 MB | Already inside the final mix (included); regenerable | `$IRAM_PY scripts/editing/edit.py audio` (procedural; same result) |
| Narration stem and premaster | `assets/narration/narration_stem.wav`, `renders/final/mix_premaster.wav` | 167 MB, 445 MB | Intermediate steps of the mix (the final `mix.flac` is included) | `$IRAM_PY scripts/editing/edit.py audio` |
| Version 2 narration (superseded) | `assets/narration/english_v2/` | 197 MB | Replaced by version 3 | Ask in the cloud session if you need it for comparison |
| Version 1 narration (designed voice) | `assets/narration/raw/` | 51 MB | Replaced | Ask in the cloud session; or regenerate with Qwen3-TTS (`scripts/narration/generate_narration.py`) |
| Version 1 and 2 review copies | `/home/user/iram-work/iram_lost_city_documentary_v1_qwen_review_540p.mp4`, `…_v2_review_540p.mp4` | 62 MB, 63 MB | Superseded (the version 3 review copy is included) | Ask in the cloud session |
| Model weights | `/home/user/iram-work/models/` (VoxCPM2, Qwen3-TTS, Kokoro, Whisper, WavLM, SDXL, SDXL-Lightning, Depth-Anything, Audar Flash) | 30 GB | Third-party downloads, too large | Download again from Hugging Face; commands in `documentation/installation.md` and `documentation/voice_engine.md`. Rendering needs **none** of them. |
| Python environments | `/home/user/iram-work/venvs/` | 11 GB | Linux-specific | `handoff/mac_setup.sh` builds the render environment; the TTS environments are in `documentation/voice_engine.md` |
| Elevation data (Copernicus GLO-90) | `/home/user/iram-work/data/dem/` | 306 MB | Needed only to rebuild the map basemaps, which are included as a cache | `$IRAM_PY scripts/animation/fetch_dem.py` (free; needs `rasterio`) |
| Copyrighted full texts (translations, tafsir and sunnah.com dumps) | `/home/user/iram-work/raw_sources_private/` | 3.8 MB | Not redistributable; only short quotations are used | Re-fetch from the cited sources (`research/bibliography.md`) |
| Downloaded web pages (research snapshots) | `research/raw_sources/web_secondary/*.html` | under 1 MB | Third-party pages (the extracted `.txt` versions are included) | Re-fetch from the URLs in `research/bibliography.md` |
| Per-chunk test files of the voice tests | `voice_profiles/*/test_samples/*/` and their `.wav` takes | about 100 MB | Test material; the MP3 listening copies and all metrics are included | Ask in the cloud session |
| Git history | the `.git` folder | — | The archive holds files only | `git clone -b claude/iram-documentary-production-6jbfrx https://github.com/imasdhere/zack-d-films-ai-video-generator.git` |

Not created at all (so not missing):
- 4K master, AI video clips: no GPU was available in the cloud. The WanGP clips are the next step (README §4).
- Audar-TTS outputs: the codec is gated (see PROJECT_STATUS.md).
- Approved Quranic recitation: needs qualified review.
