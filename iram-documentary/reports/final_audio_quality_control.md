# Final audio quality-control report (cloned narrators)

Date: 2026-11-20. Master: `renders/final/iram_lost_city_documentary_1440p.mp4`.

Automatic checks are listed with their measured values. Items that need a human (listening, Arabic language review, Quranic review) are marked **open** until a person signs them off.

## English narration (Video 1 voice)

| Check | Result | Status |
|---|---|---|
| Chunks generated / passed automatic QA | 103 / 103 | pass |
| Intelligibility (Whisper WER without names, median / max) | 0.0 / 0.111 | pass |
| Speaker similarity to Video 1 reference (median / min) | 0.981 / 0.949 | supporting evidence only |
| Sounds like Video 1; accent consistent; names pronounced correctly; natural delivery; no robotic artefacts | needs listening | **open** |

Consistency between chapters (English narration):

| Chapter | Median speaker similarity | Median F0 (Hz) | Shift vs reference (semitones) |
|---|---|---|---|
| 0 | 0.983 | 94.4 | -0.7 |
| 1 | 0.98 | 95.5 | -0.5 |
| 2 | 0.979 | 99.4 | 0.19 |
| 3 | 0.98 | 96.6 | -0.3 |
| 4 | 0.981 | 98.9 | 0.11 |
| 5 | 0.98 | 97.7 | -0.11 |
| 6 | 0.984 | 96.0 | -0.41 |

## Arabic narration (Video 2 voice)

| Check | Result | Status |
|---|---|---|
| Arabic parts in the mix | 4 quotations (5 chunks) | — |
| Intelligibility (Whisper CER, letters only; median / max) | 0.0 / 0.077 | pass |
| Speaker similarity to Video 2 reference (median) | 0.974 | supporting evidence only |
| Quotation letters equal the on-screen text (vowel marks only added) | checked by the router for every part | pass |
| Sounds like Video 2; MSA pronunciation, case endings and pause forms; names; pacing | needs a native Arabic reviewer | **open** |

## Quranic material

| Check | Result | Status |
|---|---|---|
| Verses in the registry | 22; letters match quran.com for 22 | pass |
| Synthetic renderings made for review | 4 verses (+ 1 routed hadith chunk(s) with Quranic wording) | review candidates only |
| Quranic audio in the film | none: the film shows the Arabic on screen and the English narrator reads the translation | pass |
| Qualified human review (tajwid) | not done | **open**: nothing approved |

## Technical checks

| Check | Result | Status |
|---|---|---|
| Every sentence of the script is covered exactly once by the chunk plan | 214 parts, 0 mismatches | pass |
| Missing or repeated words in the audio (ASR) | chunk QA flags 0 chunk(s) | pass |
| Segment loudness spread (before mix) | -19.1 to -19.0 LUFS | pass |
| Final mix loudness / true peak | -16.0 LUFS / -4.8 dBTP | pass |
| Silences over 2 s below −55 dB | 0 | pass |
| Audio-video sync (narration onset vs timeline) | max 4.0 ms over 75 segments | pass |
| No background music (ambience stem: tonal components / chroma / rhythm) | 0 / 0.12 / 0.094 | pass |
| Decoder errors / clipped audio | 0 / true peak -4.8 dBTP | pass |

## Sign-off needed

1. Listen to the whole film. Confirm that the English voice sounds like Video 1 and stays the same across chapters.
2. An Arabic speaker checks the four Arabic quotations (five chunks): pronunciation, case endings, pauses.
3. A qualified reciter or tajwid teacher reviews `assets/narration/quranic/` before any synthetic Quranic audio is used. Until then, none is used.
4. Record the results in `assets/narration/narration_manifest.csv` (approval_status) and `research/quranic_verse_registry.csv`.
