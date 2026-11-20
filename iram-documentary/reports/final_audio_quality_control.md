# Final audio quality-control report (version 2: cloned narrators)

Date: 2026-11-20. Master: `renders/final/iram_lost_city_documentary.mp4`.

Automatic checks are listed with their measured values. Items that need a human (listening, Arabic language review, Quranic review) are marked **open** until a person signs them off.

## English narration (Video 1 voice)

| Check | Result | Status |
|---|---|---|
| Chunks generated / passed automatic QA | 210 / 209 | see failures below |
| Intelligibility (Whisper WER without names, median / max) | 0.0 / 0.333 | check |
| Speaker similarity to Video 1 reference (median / min) | 0.945 / 0.852 | supporting evidence only |
| Sounds like Video 1; accent consistent; names pronounced correctly; natural delivery; no robotic artefacts | needs listening | **open** |

Consistency between chapters (English narration):

| Chapter | Median speaker similarity | Median F0 (Hz) | Shift vs reference (semitones) |
|---|---|---|---|
| 0 | 0.931 | 86.1 | -2.29 |
| 1 | 0.943 | 97.2 | -0.19 |
| 2 | 0.945 | 90.6 | -1.41 |
| 3 | 0.942 | 89.6 | -1.6 |
| 4 | 0.944 | 91.2 | -1.3 |
| 5 | 0.957 | 92.2 | -1.11 |
| 6 | 0.95 | 96.3 | -0.36 |

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
| Missing or repeated words in the audio (ASR) | chunk QA flags 1 chunk(s) | see below |
| Segment loudness spread (before mix) | -19.1 to -18.9 LUFS | pass |
| Final mix loudness / true peak | -16.0 LUFS / -4.0 dBTP | pass |
| Silences over 2 s below −55 dB | 0 | pass |
| Audio-video sync (narration onset vs timeline) | max 4.0 ms over 75 segments | pass |
| No background music (ambience stem: tonal components / chroma / rhythm) | 0 / 0.12 / 0.084 | pass |
| Decoder errors / clipped audio | 0 / true peak -4.0 dBTP | pass |

## Chunks that did not pass automatic QA

| Chunk | Notes | ASR |
|---|---|---|
| 0.01_p06_c00 | ASR error 0.333 > 0.15; best of 6 takes (0.01_p06_c00_take4) | Hold Dune's Walk. |

## Sign-off needed

1. Listen to the whole film. Confirm that the English voice sounds like Video 1 and stays the same across chapters.
2. An Arabic speaker checks the four Arabic quotations (five chunks): pronunciation, case endings, pauses.
3. A qualified reciter or tajwid teacher reviews `assets/narration/quranic/` before any synthetic Quranic audio is used. Until then, none is used.
4. Record the results in `assets/narration/narration_manifest.csv` (approval_status) and `research/quranic_verse_registry.csv`.
