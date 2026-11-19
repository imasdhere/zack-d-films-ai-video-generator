# Production log

All times are the container's local time on 2026-11-19.

| Time | Stage | Event / decision |
|---|---|---|
| 11:13 | 1 Audit | The environment is a Linux cloud container (4 vCPU Xeon, 15 GiB, no GPU), not a Mac. No local machine was attached. Network: allow-list proxy. |
| 11:15 | 1 Audit | Hugging Face, PyTorch CDN, Whisper, Wikimedia and Tanzil were blocked. **User approved** adding those hosts to the "AI video studio" environment. |
| 11:17 | 3 Install | ML venv: the PyTorch CPU index redirects to a blocked host, so PyPI wheels were used. Kokoro needs Python < 3.13, so Python 3.12 was used. `bpy` 5.3.0 installed on Python 3.13. |
| 11:20 | 4 Research | Quran (Uthmani) and translations downloaded from Tanzil. All 40 verses containing عاد extracted; 23 verses (24 occurrences) confirmed by script. |
| 11:21 | 4 Research | Web-reader agents could not reach research hosts. **User approved** adding the research sites (Wikipedia, UNESCO, JPL, sunnah.com, quran.com, tafsir sites, archive.org …). |
| 11:24 | 4 Research | Tafsir al-Ṭabarī and Ibn Kathīr on 89:6–8 retrieved verbatim (quran.com API). Key finding: al-Ṭabarī prefers "tent poles" and says no columned building of ʿĀd is known by authentic report. Ibn Kathīr calls the golden city a fable. |
| 11:30 | 4 Research | sunnah.com and UNESCO pages pass Cloudflare in headless Chromium. Hadith Bukhari 1035 / 4828–29 and Muslim 899b / 900a verified. |
| 11:33 | 4 Research | Wikipedia "ʿĀd" points to Al-Jallad (2025): a tribe of ʿĀd is attested in pre-Islamic northern inscriptions (Wadi Ramm). Its wording "widely accepted" was **not adopted**; the film calls it a proposal. |
| 11:38 | 4 Research | Ibn Khaldūn's Muqaddimah text could not be retrieved (scanned pages only), so it was **excluded** rather than quoted from memory. |
| 11:40 | 4 Research | PubMed: Fleitmann et al. 2003 (Science) and Zaki et al. 2025 (Commun. Earth Environ.) abstracts verified. |
| 11:42 | 3 Install | HF downloads stalled on `us.aws.cdn.hf.co`. **User approved** adding the HF CDN hosts. All weights downloaded (about 17 GB). |
| 11:45 | TTS eval | Same 145-word sample: Kokoro (6 voices plus 1 blend) and Qwen3-TTS VoiceDesign. Objective metrics (Whisper WER, Arabic terms, F0, SQUIM PESQ/STOI/SI-SDR). |
| 11:58 | TTS eval | Voice designed (seed 7) and cloned with the Qwen3 Base model: PESQ 4.33, WER 0.095, F0 about 91 Hz. **Primary: Qwen3-TTS clone. Backup: Kokoro bm_lewis.** |
| 12:01 | 8 Narration | Full narration started (75 segments, sentence by sentence, resumable). |
| 12:05 | 6 Storyboard | 144 shots planned (`storyboard/shots.yaml`), 52+ AI images defined with labels and style grammar (photo / recon / legend). |
| 12:10 | 7 Visuals | ComfyUI (CPU, bf16) was **killed for lack of memory** while loading SDXL (11 GB RSS) alongside narration. Image generation was postponed until narration finishes. |
| 12:12 | 7 Visuals | Copernicus GLO-90 DEM mosaics built (Arabia 605 tiles, Dhofar, Wadi Rum). Natural Earth vectors and OFL fonts fetched. |
| 12:20 | 7 Visuals | Typography/diagram renderer and map renderer built. Arabic shaping verified (raqm). Coordinates verified from Wikipedia page metadata. |
| 12:28 | 7 Visuals | Blender procedural dunes looked like CG, so the two dune animations were replaced by AI stills with depth parallax. Blender is kept for the column layout (guide for SDXL img2img) and the Shisr cutaway schematic. |
| 12:30 | 7 Visuals | Wikimedia Commons rate-limited (HTTP 429) the API and file downloads from this egress IP. NASA public-domain imagery added (ASTER Rubʿ al-Khālī, ISS Dhofar and dunes, Salalah, Wadi Rum, STS-59 Endeavour liftoff). Labelled fallbacks defined for every Commons photo. |
| 12:45 | 8 Narration | Found that Qwen3-TTS occasionally misses its end token and generates up to 2048 tokens (about 170 s) per sentence, costing minutes per segment. Fix: per-sentence `max_new_tokens` cap plus duration sanity check with seed retries. Narration restarted (resumable). |
| 12:47 | Script | Segment 1.06 reworded: "Poets wrote of a city of a thousand pillars" became "Popular retellings still speak of…", because no poetic source was verified. Re-voiced after the main run. |
| 13:00 | Repo | Copyrighted full texts (Saheeh, Hilali, Yusuf Ali, Itani, the Darussalam tafsir, sunnah.com and UNESCO dumps) moved out of git. The primary-sources file keeps Saheeh only for 89:6–8. |
| 13:46 | Narration | Narration complete: 75 segments, 18.3 min, no retries after the token-cap fix. Whisper spot checks confirm the names. |
| 13:48 | Edit | Timeline 21.03 min, 154 shots (none shorter than 2.5 s). SRT built from sentence timings (308 cues, max 42 characters per line, no overlaps). |
| 13:50 | Visuals | ComfyUI was OOM-killed again (13 GB anonymous memory: the runtime LoRA patch keeps a backup copy of the UNet). Switched to ByteDance's **merged** SDXL-Lightning UNets plus the SDXL text encoders: 6 GB steady. |
| 13:55 | Visuals | Benchmark: about 20 s per step at 1344×768 on 4 cores. Plan: 4-step for landscapes (about 100 s per image), 8-step for reconstructions, legends and figures (about 175 s per image). |
| 14:05 | Audio | Mix v1 peaked at +6.8 dBTP (TTS crest factor, thunder). Added voice compression and limiting, an ambience limiter, a premaster limiter at −9 dBFS, then two-pass loudnorm. Final mix: −16.0 LUFS, LRA 4.1 LU. |
| 14:20 | Review | **Rejected and regenerated:** D06 (cartoon cloud instead of a haboob), D20 (garbled "signature" artefact), R01/R02 (Greco-Roman columns, wrong tradition for South Arabia; now square Sabaean-type monoliths), L01 (domes and a minaret in the legend city: anachronistic and inappropriate). |
| 14:45 | Review | **Removed from the cut:** E11 and K01 (pseudo-text pages that could read as fabricated documents), S02 (not a convincing stalagmite section), E12/E13 (botanically inaccurate frankincense). P06 (robed figures) moved away from the line naming the Prophet Hūd. |
| 15:00 | Photos | Wikimedia Commons stayed rate-limited (HTTP 429 on the API for 40+ minutes). Only 2 of 19 photos downloaded (Wabar craters, Wabar meteorite section). Labelled NASA/AI fallbacks used for the rest. |
| 15:15 | Edit | Depth maps (Depth-Anything-V2-Small) checked. Chapter 0 (36.7 s) and the credits rendered and reviewed. |
| 16:15 | Review | The img2img pass over the Blender layout (denoise 0.55–0.60, Lightning) lost the structure in view 1. View 2 (square monoliths) and view 3 (distant settlement) are kept. 2.05 now uses the stronghold P05. |
| 16:50 | Review | The regenerated R01 still drifted classical (round columns, dome), so it is not used. R02 (sturdy rock-cut pillars) is kept. 3.12 = R02 → B02_V2 → R03. |
| 17:00 | Review | The legend style was changed from Persian miniature to ink-and-gold storybook engraving, because the miniature style kept producing domes and minarets (an Islamic-looking skyline is inappropriate for the destroyed city of the story). L01 accepted. L02 and L03 still had domes, so they were **rejected and removed from the cut** (replaced by L01, D13, K02, D18). |
| 17:05 | Review | E05 harbour regenerated with South Arabian forms (flat roofs, fortress wall, sewn-plank boats). Accepted. |
| 17:25 | Edit | Chapters 3 and 4 re-rendered with the corrected shots. Chapter 4 was split into two parallel parts (`--part 1/2`, `2/2`) and joined losslessly. |
| 17:50 | Export | First mux used `-shortest`, which cut the master to the subtitle track's end (20:11). Fixed: trim to the picture length. **Final master 21:01.6**, 1920×1080, 24 fps, H.264 High, AAC 256k, soft English subtitles. 540p review copy (65 MB) and thumbnail generated. |
| 18:10 | QC | `qc.py`: 17/17 automated checks pass. No decode errors; the only black frames are the intended final fade; no freezes; −16.0 LUFS, true peak −4.8 dBTP; **no musical content** (0 sustained tonal components); narration WER 0.091 (sampled). See `reports/quality_control_report.md`. |
