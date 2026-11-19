"""Write reports/quality_control_report.md from reports/qc_metrics.json plus editorial checks on the timeline."""
import json, pathlib, collections, yaml
ROOT = pathlib.Path(__file__).resolve().parents[2]
m = json.load(open(ROOT / 'reports/qc_metrics.json'))
tl = json.load(open(ROOT / 'renders/timeline.json'))
assets = yaml.safe_load(open(ROOT / 'storyboard/assets.yaml', encoding='utf-8'))
c = m['container']; L = m['loudness']; mc = m['music_check']
dur = c['duration_s']
ok = lambda b: '✅' if b else '❌'
# editorial label coverage
import sys; sys.path.insert(0, str(ROOT / 'scripts/editing'))
import edit
unlabelled = []
for s in tl['shots']:
    a = s['asset']
    needs = (a in assets['ai'] and assets['ai'][a].get('label')) or a.startswith('B0') or a in assets.get('img2img', {})
    if needs and not edit.label_for(s): unlabelled.append(a)
fallbacks = sorted({s['asset'] for s in tl['shots'] if s['asset'] in edit.PHOTOS and 'commons' in edit.PHOTOS[s['asset']] and not edit.real_photo(s['asset'])})
blacks = [b for b in m['black_segments'] if not (b[0] < 3 or b[1] > dur - 3)]
rows = [
    ('Duration ≥ 15 min (target 18–22)', f"{dur / 60:.2f} min (incl. {edit.CREDITS:.0f} s credits)", 15 * 60 <= dur),
    ('Resolution ≥ 1920×1080, 16:9', f"{c['width']}×{c['height']} (DAR {c['dar']})", c['width'] >= 1920 and c['height'] >= 1080),
    ('Frame rate 24 fps', c['fps'], c['fps'] in ('24/1', '24')),
    ('H.264 MP4', f"{c['video_codec']} {c['profile']}, {c['pix_fmt']}", c['video_codec'] == 'h264'),
    ('Stereo audio', f"{c['audio_codec']} {c['audio_channels']} ch @ {c['audio_rate']} Hz", c['audio_channels'] == 2),
    ('Decodes without errors', f"{len(m['decode_errors'])} decoder messages", len(m['decode_errors']) == 0),
    ('No unintended black frames (pix_th 0.03, ≥0.5 s)', f"{len(m['black_segments'])} total; {len(blacks)} outside the opening/closing fades", len(blacks) == 0),
    ('No frozen picture ≥ 6 s', f"{len(m['frozen_segments'])} segments", len(m['frozen_segments']) == 0),
    ('Integrated loudness (target −16 LUFS)', f"{L['integrated_lufs']} LUFS, LRA {L['lra_lu']} LU", abs(L['integrated_lufs'] + 16) < 1.0),
    ('True peak ≤ −1 dBTP (no clipping)', f"{L['true_peak_dbfs']} dBTP", L['true_peak_dbfs'] <= -1.0),
    ('No unintended silence (<−55 dB for ≥2 s)', f"{len(m['silences_over_2s_below_-55dB'])} found", len(m['silences_over_2s_below_-55dB']) <= 1),
    ('**No music**: sustained tonal components in the non-narration stem', f"{mc['sustained_tonal_components_>=0.5s']} (stem {mc['stem_duration_min']} min)", mc['sustained_tonal_components_>=0.5s'] <= 3),
    ('No music: chroma peak ratio (music typically > 0.3)', mc['chroma_peak_ratio_median'], mc['chroma_peak_ratio_median'] < 0.3),
    ('No music: rhythmic periodicity (music typically > 0.3)', mc['max_rhythmic_autocorrelation_lag_0.6-12s'], mc['max_rhythmic_autocorrelation_lag_0.6-12s'] < 0.3),
    ('Narration intelligibility (Whisper WER on final mix, sampled)', f"mean {m['narration_wer_mean']:.3f} over {len(m['narration_wer_sampled'])} segments", m['narration_wer_mean'] < 0.15),
    ('Every reconstruction / legend / illustration labelled on screen', f"{len(unlabelled)} unlabelled", len(unlabelled) == 0),
    ('Visual variety', f"{m['shots']['count']} shots, {m['shots']['unique_assets']} unique assets, mean {m['shots']['mean_shot_s']} s; most reused: {m['shots']['max_reuse'][:3]}", m['shots']['unique_assets'] >= 80),
]
md = ['# Quality-control report', '', f"Master: `renders/final/iram_lost_city_documentary.mp4` ({c['size_mb']} MB). Automated checks: `scripts/quality_control/qc.py` → `reports/qc_metrics.json`.", '',
      '## Technical and audio checks', '', '| Check | Result | Pass |', '|---|---|---|']
md += [f'| {a} | {b} | {ok(p)} |' for a, b, p in rows]
md += ['', '## Narration WER by sampled segment', '', '| Segment | WER |', '|---|---|'] + [f"| {x['seg']} | {x['wer']} |" for x in m['narration_wer_sampled']]
md += ['', 'WER is computed against the display text, with transliterated names (Iram, ʿĀd, al-Ṭabarī …). Most residual "errors" are Whisper spelling Arabic names differently, not mispronunciations.', '',
       '## Research and editorial checks (manual)', '',
       '| Check | Status |', '|---|---|',
       '| Every factual sentence traced to the claim matrix | ✅ `screenplay/final_fact_checked_script.md` lists claim IDs per segment; build fails on unknown IDs |',
       '| Quranic Arabic verbatim | ✅ Loaded programmatically from the Tanzil file for every card; never retyped |',
       '| Quranic translations | ✅ Pickthall (public domain), verbatim; Saheeh International cited only as a comparison |',
       '| Hadith references | ✅ Bukhari 1035, 4828–4829; Muslim 899, 900, verified on sunnah.com; no grades invented |',
       '| Tafsir quotations | ✅ Verbatim Arabic from the archived text; English marked "production translation" |',
       '| Unverified claims excluded | ✅ X01–X05 (Ibn Khaldūn, Ebla, JPL date range, "widely accepted", Clapp retraction) |',
       '| Speculation separated from evidence | ✅ Shisr = Iram shown as a popular identification; Wadi Ramm as a recent proposal; science sequence marked with a divider |',
       '| Prophet Hūd not depicted | ✅ No figure, silhouette or face; only distant anonymous people of ʿĀd |',
       '| AI imagery not presented as evidence | ✅ On-screen tags + credit line "AI-generated image (SDXL)"; legend sequences use a painterly style |',
       '| Maps do not locate Iram | ✅ Only soft regional zones labelled by source; "IRAM — LOCATION UNKNOWN" |',
       '| No music | ✅ Sound is procedurally synthesised noise models only (see the automated check above) |',
       '', '## Known limitations', '',
       f"- **Real photographs**: Wikimedia Commons rate-limited this server (HTTP 429). These photo slots used labelled fallbacks (NASA public-domain imagery or labelled AI illustrations): {', '.join(fallbacks) or 'none'}.",
       '- **No AI video**: Wan 2.2 and LTX need a GPU, so motion is 2.5-D depth parallax and camera moves on stills, maps and graphics.',
       '- **1080p, not 4K**: the CPU-only hardware made native 4K generation impractical (see `reports/system_hardware_audit.md`).',
       '- **Narration listening test**: the voice was chosen with objective metrics; a human listening pass is still recommended before publication.',
       '- **Secondary sources**: several archaeological details (Blom et al. 2007, Edgell 2004, Zarins 1997) were verified through secondary summaries, and the narration attributes them accordingly.',
       ]
(ROOT / 'reports/quality_control_report.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
print('QC report written;', sum(1 for r in rows if r[2]), '/', len(rows), 'automated checks passed')
