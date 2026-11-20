# Quality-control report

Master: `renders/final/iram_lost_city_documentary_1440p.mp4` (2560×1440, 4597.2 MB). Automated checks: `scripts/quality_control/qc.py` → `reports/qc_metrics.json`.

## Technical and audio checks

| Check | Result | Pass |
|---|---|---|
| Duration ≥ 15 min (target 18–22) | 20.21 min (incl. 42 s credits) | ✅ |
| Resolution ≥ 1920×1080, 16:9 | 2560×1440 (aspect 1.778 = 16:9, square pixels) | ✅ |
| Frame rate 24 fps | 24/1 | ✅ |
| H.264 MP4 | h264 High, yuv420p | ✅ |
| Stereo audio | aac 2 ch @ 48000 Hz | ✅ |
| Decodes without errors | 0 decoder messages | ✅ |
| No unintended black frames (pix_th 0.03, ≥0.5 s) | 1 total; 0 outside the opening/closing fades | ✅ |
| No frozen picture ≥ 6 s | 0 segments | ✅ |
| Integrated loudness (target −16 LUFS) | -16.0 LUFS, LRA 2.9 LU | ✅ |
| True peak ≤ −1 dBTP (no clipping) | -4.8 dBTP | ✅ |
| No unintended silence (<−55 dB for ≥2 s) | 0 found | ✅ |
| **No music**: sustained tonal components in the non-narration stem | 0 (stem 20.2 min) | ✅ |
| No music: chroma peak ratio (music typically > 0.3) | 0.12 | ✅ |
| No music: rhythmic periodicity (music typically > 0.3) | 0.094 | ✅ |
| Narration intelligibility (Whisper WER on final mix, sampled) | mean 0.102 over 13 segments | ✅ |
| Every reconstruction / legend / illustration labelled on screen | 0 unlabelled | ✅ |
| Visual variety | 152 shots, 107 unique assets, mean 7.98 s; most reused: [['G_CHAPTER', 6], ['G_SUMMARY', 5], ['D16', 4]] | ✅ |

## Narration WER by sampled segment

| Segment | WER |
|---|---|
| 0.01 | 0.0 |
| 1.05 | 0.278 |
| 2.03 | 0.122 |
| 2.09 | 0.0 |
| 3.05 | 0.107 |
| 3.11 | 0.0 |
| 4.03 | 0.0 |
| 4.09 | 0.143 |
| 4.15 | 0.094 |
| 5.02 | 0.0 |
| 5.08 | 0.354 |
| 6.03 | 0.163 |
| 6.09 | 0.062 |

WER is computed against the display text, with transliterated names (Iram, ʿĀd, al-Ṭabarī …). Most residual "errors" are Whisper spelling Arabic names differently, not mispronunciations.

## Research and editorial checks (manual)

| Check | Status |
|---|---|
| Every factual sentence traced to the claim matrix | ✅ `screenplay/final_fact_checked_script.md` lists claim IDs per segment; build fails on unknown IDs |
| Quranic Arabic verbatim | ✅ Loaded programmatically from the Tanzil file for every card; never retyped |
| Quranic translations | ✅ Pickthall (public domain), verbatim; Saheeh International cited only as a comparison |
| Hadith references | ✅ Bukhari 1035, 4828–4829; Muslim 899, 900, verified on sunnah.com; no grades invented |
| Tafsir quotations | ✅ Verbatim Arabic from the archived text; English marked "production translation" |
| Unverified claims excluded | ✅ X01–X05 (Ibn Khaldūn, Ebla, JPL date range, "widely accepted", Clapp retraction) |
| Speculation separated from evidence | ✅ Shisr = Iram shown as a popular identification; Wadi Ramm as a recent proposal; science sequence marked with a divider |
| Prophet Hūd not depicted | ✅ No figure, silhouette or face; only distant anonymous people of ʿĀd |
| AI imagery not presented as evidence | ✅ On-screen tags + credit line "AI-generated image (SDXL)"; legend sequences use a painterly style |
| Maps do not locate Iram | ✅ Only soft regional zones labelled by source; "IRAM — LOCATION UNKNOWN" |
| No music | ✅ Sound is procedurally synthesised noise models only (see the automated check above) |

## Known limitations

- **Real photographs**: Wikimedia Commons rate-limited this server (HTTP 429). These photo slots used labelled fallbacks (NASA public-domain imagery or labelled AI illustrations): PH_BALEED, PH_BARK, PH_BOSW1, PH_DAWKAH, PH_ROAD_UBAR, PH_RUM1, PH_RUM2, PH_RUM3, PH_RUM4, PH_SHISR1, PH_SHISR2, PH_SHISR_RUIN, PH_SHISR_WELL, PH_THOMAS_BEDU, PH_WABAR2.
- **No AI video**: Wan 2.2 and LTX need a GPU, so motion is 2.5-D depth parallax and camera moves on stills, maps and graphics.
- **1080p, not 4K**: the CPU-only hardware made native 4K generation impractical (see `reports/system_hardware_audit.md`).
- **Narration listening test**: the voice was chosen with objective metrics; a human listening pass is still recommended before publication.
- **Secondary sources**: several archaeological details (Blom et al. 2007, Edgell 2004, Zarins 1997) were verified through secondary summaries, and the narration attributes them accordingly.
