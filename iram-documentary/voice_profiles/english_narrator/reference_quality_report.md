# Reference audio report: english_narrator

Source: `Video1.mp4` (sha256 `d6dff13a05ad0f31…`), 26.1 s, video 720×1280, audio aac 44100 Hz, 2 ch. The original file is kept unchanged in `original_video/` (local only).

## Full recording

| Measure | Value |
|---|---|
| Peak level | -2.95 dBFS |
| Clipped samples | 0 |
| Integrated loudness | -16.7 LUFS |
| Left/right correlation | 0.9992 |
| Bandwidth (last frequency within 40 / 60 dB of the peak) | 9722 / 15696 Hz |
| Level in pauses (noise floor or music bed) | -44.7 dBFS over 2.98 s |
| Reverberation: level 150–300 ms after phrase ends | -53.9 dB |
| Median pitch (p10–p90) | 92.8 Hz (51.8–124.5 Hz) |
| Pitch spread | 5.12 semitones |
| Sustained (held) vowels ≥ 0.4 s | 1 |
| Speaking rate | 160.5 words/min |

## Selected reference clip

3.09–12.96 s of the source (10.24 s after padding). Transcript:

> If you breathe with your belly, then your voice starts to drop a couple of frequencies. When you breathe with your diaphragm, it would sound something like this.

Selection rules: 8.0–15.0 s, boundaries in pauses, excluded ranges:
- 0.0–3.05 s: demonstration of an exaggerated 'belly' register (median F0 55 Hz, creaky voice)
- 15.0–18.1 s: raised-pitch coaching aside (median F0 123 Hz)

Score = −(pitch spread) − 0.6 × (held vowels) + 0.02 × (dryness) + 0.05 × (duration). Top candidates:

| Start–end (s) | Score | Median F0 (Hz) | Pitch spread (st) | Held vowels | Tail (dB) |
|---|---|---|---|---|---|
| 3.09–12.96 | -2.78 | 98.3 | 3.72 | 1 | -52.3 |
| 3.09–12.92 | -2.783 | 98.3 | 3.72 | 1 | -52.3 |

Cleaning: mono downmix (L/R correlation above); high-pass 60 Hz, 2 poles; dereverberation: none; 12 ms edge fades; loudness gain to -20 LUFS, peak <= -1 dBFS; no pitch shift, no EQ, no time stretch.

## Suitability for cloning

**Good.** One speaker only. Close-microphone studio recording, dry (noise-gated pauses), no music bed, no clipping in the source. The clip is short (26 s) and the speaker changes register on purpose to teach voice technique, so two passages were excluded: an exaggerated low "belly" voice (creaky, about 55 Hz) and a raised aside (about 123 Hz). The selected 9.9 s clip is his steady speaking register (median 98 Hz). The recording passed through social-media AAC compression (bandwidth about 15.7 kHz), which is adequate for 16–24 kHz cloning inputs.
