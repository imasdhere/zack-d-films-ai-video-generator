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

## Version 2: dual-language cloned narration (2026-11-19, evening)

| Time | Stage | Event / decision |
|---|---|---|
| 18:14 | Brief | New brief: clone the narrator of Video 1 for English and of Video 2 for Arabic; evaluate Audar-TTS and VoxCPM; Quranic safeguards; re-engineer the audio pipeline. |
| 18:20 | Inspect | Video 1: 26 s vertical clip, one man in a studio (voice coach), English, dry and noise-gated. Video 2: 56 s, still image with the travel supplication (duʿāʾ al-safar), one male voice, chanted, reverberant. No music bed in either. |
| 18:22 | Consent | **Owner confirmed** permission from both speakers to clone their voices for this documentary. Owner chose "bilingual quotations": the Arabic narrator reads the original Arabic of the classical and hadith cards; Quranic audio stays out of the film until a qualified review. |
| 18:24 | Install | VoxCPM2 weights (5.0 GB, Apache-2.0), Audar-TTS-V1-Flash weights (1.1 GB, AudarAI Open v1.0), Whisper large-v3-turbo and WavLM-SV downloaded. Removed the unused SDXL base checkpoint (6.9 GB) and two intermediate render files (4.1 GB) to free disk. |
| 18:25 | Blocker | Audar needs NeuCodec (`neuphonic/neucodec`), which is gated (HTTP 401). The owner saved a Hugging Face credential, but Hugging Face rejects it ("Invalid username or password"). Audar stays untested until a valid token is provided. |
| 18:35 | References | Both transcripts verified: Video 1 by two Whisper models in exact agreement (and the burned-in captions); Video 2 against the on-screen text of the supplication in the video. Clips chosen by measurement: English 3.09–12.96 s (steady register, median 98 Hz; the "belly" demonstration and a raised aside excluded); Arabic 37.24–47.02 s (least chanted passage, median 68 Hz). WPE dereverberation made the Arabic tail worse (−22 → −17 dB), so it is not used. Fixed a downmix bug (ffmpeg `-ac 1` sums channels and clipped). |
| 18:50 | Engines | VoxCPM2 runs on this CPU in bf16: about 4.3× slower than real time, 11.5 GB peak RAM. |
| 18:55 | Quran | Registry of 22 verses built from Tanzil; all 22 match quran.com letter for letter. The router's Quranic scan flags the ʿĀʾisha hadith card, because it contains the words of 46:24 ("هذا عارض ممطرنا"), so that quotation goes to the review workflow, not the mix. |
| 19:28 | Probe | Pronunciation probe (24 respellings × 2 carrier sentences, ranked by Whisper): Iram → "Ee-rahm", ʿĀd → "Aa-d", al-Ṭabarī → "al-Tabari", ʿimād → "ee-maad". A first writer bug replaced "aad" inside other names; fixed to whole words. |
| 19:35 | Decision | VoxCPM2 "ultimate" (continuation) cloning garbled or dropped the first word of most sentences. A/B on 8 sentences: first word correct 1/8 (ultimate) vs 6/8 (reference); CER 0.141 vs 0.077. **Production switched to reference mode.** |
| 19:50 | Narration | Standard tests repeated in reference mode, then the full narration started: 210 English chunks and 5 Arabic chunks (VoxCPM2, about 3.7× slower than real time). |
| 20:24 | Incident | Container restart. Narration resumed from the 110 finished chunks (resumable by design). |
| 21:07 | QA | Whisper large-v3-turbo + WavLM on every chunk: 6 of 215 failed, mostly spelling false alarms. QA now ignores name spellings and British/American variants. |
| 21:28 | Incident | Regeneration was killed for lack of memory (VoxCPM2 loaded while QA models were still in memory). Regeneration now runs as its own process. |
| 21:34 | QA | "Whole dunes walk." failed 3 times (Whisper: "Hold Doom's walk"). Best of 6 takes kept and flagged "review" for listening. All other chunks pass. |
| 21:47 | Render | Narration assembled: 75 segments, 18.9 min, segment loudness −19.1 to −18.9 LUFS. Timeline 21:36.6. Render started. |
| 22:09 | Incident | Container restart during the render. Three chapter files were cut off mid-write (no index). The render was made resumable in 40–130 s parts with a duration check. |
| 07:48 | Render | Render resumed (day 2). Chapter 3 part 1 skipped as complete; 14 parts rendered in 40 minutes, 4 in parallel. |
| 08:29 | Export | **Version 2 master: 21:36.6**, 1920×1080, 24 fps, H.264, AAC 48 kHz, soft English subtitles; 3.8 GB. 540p review copy. |
| 08:48 | QC | 17/17 automated checks pass: −16.0 LUFS, −4.0 dBTP, no music, no freezes, sync within 4 ms, narration WER 0.113 (sampled). Final audio QA report written. |
| 08:55 | Report | Evaluation re-scored. Finding: reference mode is less steady in pitch in English (chunk spread 3.4 vs 0.7 semitones) and the Qwen3 baseline scores best on the English proxies. Reported as an open choice for a listening decision. |

## Version 3: steadier English voice, Arabic names, 1440p (2026-11-20)

| Time | Stage | Event / decision |
|---|---|---|
| 09:30 | Feedback | Owner: the voice often cracks or changes into another person's voice; Iram and (qawm) ʿĀd are said the English way. Wanted: Arabic pronunciation, then a 1440p render. |
| 09:40 | Diagnosis | Version 2 narration measured: 25 of 201 English chunks below 0.90 speaker similarity (another man scores about 0.84); chunk median pitch 70–113 Hz (spread 2.7 semitones); 48 chunks with frames far above their median pitch. The weakest chunks were short sentences (reference-mode cloning with little text context). |
| 10:20 | Test | Voice-stability test, 4 set-ups × 8 paragraph chunks (`workflows/tts/eval/voice_stability_test.json`). Winner: continuation ("ultimate") cloning from the 9.9 s clip with 0.6 s of silence added, paragraph chunks: similarity 0.982 (min 0.973), median pitch 98.6 Hz (Video 1: 98.3 Hz), spread 0.4 semitones, first word 7/8 (the padding fixed most of the version-2 first-word problem). |
| 10:22 | Names | Iram and ʿĀd are written in Arabic script (إِرَم, عَاد) inside the English TTS text. Whisper (English) now hears "Iram"/"Ad", not "Ee-rahm"/"Aa-d"; an Arabic recogniser hears ʿĀd with its ʿayn (عد) and Iram as إرم/إرام. Three Arabic spellings were compared; the differences were within the measurement noise, so the fully vowelled form is used. |
| 10:25 | Narration | English re-voiced in 103 paragraph chunks (was 210 sentence chunks). Arabic quotations kept (they passed QA). Chunk QA now also fails voice drift (similarity < 0.93), pitch shifts over 3 semitones and pitch breaks. |
