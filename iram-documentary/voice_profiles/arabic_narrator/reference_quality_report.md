# Reference audio report: arabic_narrator

Source: `Video2.mp4` (sha256 `2f67df6030ae2317…`), 55.6 s, video 608×1080, audio aac 44100 Hz, 2 ch. The original file is kept unchanged in `original_video/` (local only).

## Full recording

| Measure | Value |
|---|---|
| Peak level | -4.19 dBFS |
| Clipped samples | 0 |
| Integrated loudness | -22.1 LUFS |
| Left/right correlation | 1.0 |
| Bandwidth (last frequency within 40 / 60 dB of the peak) | 10673 / 14917 Hz |
| Level in pauses (noise floor or music bed) | -58.3 dBFS over 16.53 s |
| Reverberation: level 150–300 ms after phrase ends | -19.7 dB |
| Median pitch (p10–p90) | 74.1 Hz (60.2–105.9 Hz) |
| Pitch spread | 4.04 semitones |
| Sustained (held) vowels ≥ 0.4 s | 5 |
| Speaking rate | 72.9 words/min |

## Selected reference clip

37.24–47.02 s of the source (10.15 s after padding). Transcript:

> والخليفة في الأهل اللهم إني أعوذ بك من وعثاء السفر وكآبة المنظر

Selection rules: 8.0–15.0 s, boundaries in pauses, excluded ranges:
- 0.0–18.3 s: takbir and Quran 43:13-14, chanted with long vowel elongations (not a narration register)

Score = −(pitch spread) − 0.6 × (held vowels) + 0.02 × (dryness) + 0.05 × (duration). Top candidates:

| Start–end (s) | Score | Median F0 (Hz) | Pitch spread (st) | Held vowels | Tail (dB) |
|---|---|---|---|---|---|
| 37.24–47.02 | -2.301 | 67.5 | 2.61 | 1 | -21.0 |
| 37.24–46.84 | -2.32 | 67.5 | 2.62 | 1 | -21.0 |
| 37.37–47.02 | -2.384 | 67.1 | 2.68 | 1 | -20.7 |
| 37.37–46.84 | -2.393 | 67.1 | 2.68 | 1 | -20.7 |
| 39.55–52.91 | -2.65 | 67.9 | 3.15 | 1 | -21.6 |

Cleaning: mono downmix (L/R correlation above); high-pass 60 Hz, 2 poles; dereverberation: none; 12 ms edge fades; loudness gain to -20 LUFS, peak <= -1 dBFS; no pitch shift, no EQ, no time stretch.

Dereverberation test (WPE): tail -22.4 dB without, -17.1 dB with. Rule: use WPE if it lowers the tail by >= 3 dB. Result: **none**.

## Suitability for cloning

**Usable, with limits.** One speaker only, no music bed, no clipping, AAC 44.1 kHz (bandwidth about 14.9 kHz). Two properties limit it as a narration reference. (1) It is a **chanted supplication**, not narration: slow (about 73 words/min), with held vowels and a melodic contour; the first 18 s (takbir and Quran 43:13–14) are the most melodic and were excluded. (2) It is **reverberant**: the level 150–300 ms after phrase ends is about −20 dB, against about −54 dB for Video 1. WPE dereverberation made the tail worse, so the clip is used without it. Expect the clone to inherit some room sound and a slower, more solemn delivery. A 30–60 s dry, spoken (not chanted) recording of the same speaker would give a better Arabic narrator.
