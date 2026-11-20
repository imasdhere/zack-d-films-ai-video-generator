# Project status (2026-11-20)

## Finished

| Stage | Status | Evidence |
|---|---|---|
| Research, claim matrix, bibliography | Done (70 claims; 5 excluded as unverified) | `research/` |
| Screenplay, fact-checked | Done: 75 segments in 8 chapters (cold open, 6 chapters, credits) | `screenplay/script.yaml`, `screenplay/final_fact_checked_script.md` |
| Storyboard | Done: 152 shots | `storyboard/shots.yaml`, `renders/timeline.json` |
| Visuals | Done: about 50 AI images (SDXL, labelled), Blender layouts, 6 animated maps, typographic cards; 2 Wikimedia photos plus NASA imagery and labelled stand-ins | `assets/`, `reports/production_log.md` |
| Voice references | Done: Video 1 (English) and Video 2 (Arabic), transcripts verified, consent recorded | `voice_profiles/`, `configuration/voice_config.yaml` |
| Narration, version 3 | Done: 103 English chunks (VoxCPM2, continuation cloning, paragraph chunks); 5 Arabic quotation chunks; 17.5 min | `assets/narration/`, `assets/narration/narration_manifest.csv` |
| Narration QA | 108/108 chunks pass. English similarity to Video 1: minimum 0.949, median 0.981; pitch spread between chunks 1.05 semitones; pitch-break check passed after 3 retakes. | `assets/narration/chunk_qa.json`, `reports/final_audio_quality_control.md` |
| Sound | Done: procedural ambience, no music; mix −16.0 LUFS, −4.8 dBTP | `renders/final/mix.flac` |
| Picture, version 3 | Rendered at 2560×1440, 24 fps | (the cloud master is not in the archive; see NOT_INCLUDED.md) |
| QC | 17/17 automated checks pass; narration WER 0.102 (sampled); sync within 4 ms | `reports/quality_control_report.md`, `reports/qc_metrics.json` |
| Reports | Licensing, dependencies, hardware, costs ($0), production log, voice-cloning evaluation | `reports/` |

## Version history

| Version | Date | What changed |
|---|---|---|
| 1 | 2026-11-19 | Designed synthetic voice (Qwen3-TTS); 21:01, 1080p |
| 2 | 2026-11-20 | Cloned narrators, sentence chunks, VoxCPM2 reference mode; 21:37, 1080p. Owner: the voice cracked and changed, and the names were anglicised. |
| 3 | 2026-11-20 | Steady cloned voice (paragraph chunks, continuation cloning); Iram and ʿĀd in Arabic pronunciation; 20:13, **1440p** |

## Open (needs a person or a decision)

1. **Listening sign-off.** Listen to the whole film: does the English voice sound like Video 1 throughout, and do Iram and ʿĀd sound right?
   The automatic check hears ʿĀd with its ʿayn but sometimes with a short vowel.
2. **Arabic review.** A native speaker should check the 4 Arabic quotations (5 chunks): pronunciation, case endings, pauses.
3. **Quranic review.** No Quranic audio is in the film. The synthetic review candidates in `assets/narration/quranic/` stay unapproved
   until a qualified reciter reviews them. One hadith card (5.04) quotes the words of Quran 46:24, so its Arabic is held out too.
4. **Audar-TTS** was never tested. Its codec (NeuCodec) is gated on Hugging Face, and the token was not accepted. The adapter is ready.
5. **Image-to-video (new).** 78 shots can become WanGP clips. See `handoff/README.md`, section 4.
6. **Photos.** 17 of 19 Wikimedia photographs could not be downloaded (rate limit). Their slots use labelled NASA images or AI stand-ins.
   `assets/archaeological_photographs/photo_map.yaml` lists each wanted file. On the Mac, download the photos and render again.
7. **"dhāt al-ʿimād"** stays in transliteration. Spoken in Arabic, the three words together are the full verse 89:7, which would be synthetic recitation.

## Where the measurements are

- `reports/voice_cloning_evaluation.md`: engine tests, cloning-mode A/B, voice-stability test, name checks
- `reports/final_audio_quality_control.md`: per-chapter voice consistency, Arabic, Quranic, technical checks
- `reports/production_log.md`: every decision with its time and reason
