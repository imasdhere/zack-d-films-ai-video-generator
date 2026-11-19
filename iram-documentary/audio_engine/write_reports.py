"""Write the voice reports from measured data.

  python -m audio_engine.write_reports evaluation   # reports/voice_cloning_evaluation.md + voice_profiles/*/reference_quality_report.md
  python -m audio_engine.write_reports final        # reports/final_audio_quality_control.md (after assembly and mix)
"""
import json, sys, csv, datetime
from .common import ROOT, config

LANG = {'en': 'English', 'ar': 'Arabic'}
CRIT = [('similarity', 'Similarity to the reference speaker'), ('naturalness', 'Naturalness'), ('pronunciation', 'Pronunciation accuracy'),
        ('accent_preservation', 'Accent preservation'), ('rhythm_pacing', 'Rhythm and pacing'), ('prosody', 'Prosody'),
        ('emotional_suitability', 'Emotional suitability'), ('consistency', 'Consistency between generated segments'),
        ('artefacts', 'Absence of robotic artefacts'), ('overall_provisional', 'Overall (mean of scored rows)')]
ENGINE_NAME = {'voxcpm-reference': 'VoxCPM2, reference mode (production)', 'voxcpm-ultimate': 'VoxCPM2, ultimate mode', 'audar': 'Audar-TTS-V1-Flash',
               'qwen3': 'Qwen3-TTS 1.7B Base (version 1 engine)'}


def fmt(v): return '—' if v is None else v


def reference_report(key):
    cfg = config(); p = cfg['voice_profiles'][key]; m = json.load(open(ROOT / p['dir'] / 'voice_metadata.json', encoding='utf-8'))
    f = m['full_recording']; c = m['reference_clip']['measurements']; cl = m['reference_clip']['cleaned_measurements']
    src = m['source']['probe']; a = [s for s in src['streams'] if s['codec_type'] == 'audio'][0]; v = [s for s in src['streams'] if s['codec_type'] == 'video'][0]
    lines = [f"# Reference audio report: {p['id']}", '',
             f"Source: `{p['source']['upload_name']}` (sha256 `{p['source']['sha256'][:16]}…`), {float(src['format']['duration']):.1f} s, "
             f"video {v['width']}×{v['height']}, audio {a['codec_name']} {a['sample_rate']} Hz, {a['channels']} ch. The original file is kept unchanged in `original_video/` (local only).", '',
             '## Full recording', '', '| Measure | Value |', '|---|---|']
    rows = [('Peak level', f"{f['peak_dbfs']} dBFS"), ('Clipped samples', f['clipped_samples']), ('Integrated loudness', f"{f['integrated_lufs']} LUFS"),
            ('Left/right correlation', f.get('left_right_correlation')), ('Bandwidth (last frequency within 40 / 60 dB of the peak)', f"{f['last_hz_above_40dB']} / {f['last_hz_above_60dB']} Hz"),
            ('Level in pauses (noise floor or music bed)', f"{f['pause_rms_dbfs']} dBFS over {f['pause_total_s']} s"),
            ('Reverberation: level 150–300 ms after phrase ends', f"{f['phrase_end_tail_db']} dB"),
            ('Median pitch (p10–p90)', f"{f['f0_median_hz']} Hz ({f['f0_p10_hz']}–{f['f0_p90_hz']} Hz)"), ('Pitch spread', f"{f['f0_sd_semitones']} semitones"),
            ('Sustained (held) vowels ≥ 0.4 s', f['sustained_pitch_runs_ge_0.4s']), ('Speaking rate', f"{f['words_per_minute']} words/min")]
    lines += [f'| {k} | {v_} |' for k, v_ in rows]
    lines += ['', '## Selected reference clip', '',
              f"{m['reference_clip']['start_s']}–{m['reference_clip']['end_s']} s of the source ({cl['duration_s']} s after padding). Transcript:", '',
              f"> {m['transcript']['reference']}", '',
              f"Selection rules: {m['selection_rules']['min_s']}–{m['selection_rules']['max_s']} s, boundaries in pauses, excluded ranges:"]
    lines += [f"- {e[0]}–{e[1]} s: {e[2]}" for e in m['selection_rules'].get('exclude', [])]
    lines += ['', 'Score = −(pitch spread) − 0.6 × (held vowels) + 0.02 × (dryness) + 0.05 × (duration). Top candidates:', '',
              '| Start–end (s) | Score | Median F0 (Hz) | Pitch spread (st) | Held vowels | Tail (dB) |', '|---|---|---|---|---|---|']
    lines += [f"| {x['start']}–{x['end']} | {x['score']} | {x['f0_median_hz']} | {x['f0_sd_semitones']} | {x['sustained_pitch_runs_ge_0.4s']} | {x['phrase_end_tail_db']} |" for x in m['candidates_top5']]
    lines += ['', f"Cleaning: {'; '.join(m['processing'])}.", '']
    if m['dereverberation']['evaluation']:
        e = m['dereverberation']['evaluation']
        lines += [f"Dereverberation test (WPE): tail {e['phrase_end_tail_db_without']} dB without, {e['phrase_end_tail_db_with_wpe']} dB with. Rule: {e['rule']}. Result: **{m['dereverberation']['method']}**.", '']
    lines += ['## Suitability for cloning', '', SUITABILITY[key], '']
    out = ROOT / p['dir'] / 'reference_quality_report.md'; out.write_text('\n'.join(lines), encoding='utf-8')
    return m


SUITABILITY = {
    'english': ('**Good.** One speaker only. Close-microphone studio recording, dry (noise-gated pauses), no music bed, no clipping in the source. '
                'The clip is short (26 s) and the speaker changes register on purpose to teach voice technique, so two passages were excluded: '
                'an exaggerated low "belly" voice (creaky, about 55 Hz) and a raised aside (about 123 Hz). The selected 9.9 s clip is his steady '
                'speaking register (median 98 Hz). The recording passed through social-media AAC compression (bandwidth about 15.7 kHz), which is '
                'adequate for 16–24 kHz cloning inputs.'),
    'arabic': ('**Usable, with limits.** One speaker only, no music bed, no clipping, AAC 44.1 kHz (bandwidth about 14.9 kHz). Two properties '
               'limit it as a narration reference. (1) It is a **chanted supplication**, not narration: slow (about 73 words/min), with held vowels '
               'and a melodic contour; the first 18 s (takbir and Quran 43:13–14) are the most melodic and were excluded. (2) It is **reverberant**: '
               'the level 150–300 ms after phrase ends is about −20 dB, against about −54 dB for Video 1. WPE dereverberation made the tail worse, '
               'so the clip is used without it. Expect the clone to inherit some room sound and a slower, more solemn delivery. A 30–60 s dry, '
               'spoken (not chanted) recording of the same speaker would give a better Arabic narrator.'),
}


def evaluation():
    cfg = config(); M = json.load(open(ROOT / 'reports/voice_clone_metrics.json', encoding='utf-8'))
    refs = {k: reference_report(k) for k in ('english', 'arabic')}
    S = M['samples']; sel = {lang: cfg['voice_profiles'][PROF].get('preferred_engine') for lang, PROF in (('en', 'english'), ('ar', 'arabic'))}
    L = ['# Voice-cloning evaluation', '', f"Date: {datetime.date.today().isoformat()}. Hardware: 4-vCPU Intel Xeon (AVX-512, AMX-BF16), 15 GiB RAM, no GPU, Linux cloud container (not a Mac; see `reports/system_hardware_audit.md`).", '',
         '## Result', '']
    L += SELECTION_TEXT
    L += ['', '## Consent', '', cfg['consent']['statement'] + f" Confirmed by the {cfg['consent']['confirmed_by']} on {cfg['consent']['date']}.", '',
          '## References', '', '| Profile | Source | Clip | Duration | Median F0 | Notes |', '|---|---|---|---|---|---|']
    for k, m in refs.items():
        c = m['reference_clip']
        L.append(f"| {m['profile']} | {m['source']['upload_name']} | {c['start_s']}–{c['end_s']} s | {c['cleaned_measurements']['duration_s']} s | {c['cleaned_measurements']['f0_median_hz']} Hz | see `voice_profiles/{m['profile']}/reference_quality_report.md` |")
    L += ['', f"Speaker-embedding cosine between the two references: {M['references']['cross_reference_similarity']} (two different men; this is the 'different speaker' baseline for the scores below).", '',
          '## Engines investigated', '']
    L += ENGINES_TEXT
    L += ['', '## Test design', '',
          'One standard text per language (`workflows/tts/eval/clone_test_texts.yaml`), identical for every engine. English: 161 words from the approved screenplay. Arabic: 145 words of Modern Standard Arabic written for the test from claims in the claim matrix. '
          'Both texts go through the production chunker (sentence boundaries, at most 260/200 characters) and the production pronunciation lexicon, so the test reflects real production. '
          'Each engine received the same reference clip and transcript. Seeds are fixed (base 20261119 + chunk index). Chunks are joined with 0.45 s pauses.', '',
          '## Test matrix', '', '| Test | Reference | Engine | Language | Status | Output |', '|---|---|---|---|---|---|']
    done = {(s['engine'], s['lang']): s for s in S}
    tests = [('1', 'audar', 'en'), ('2', 'voxcpm-reference', 'en'), ('2b', 'voxcpm-ultimate', 'en'), ('3', 'audar', 'ar'),
             ('4', 'voxcpm-reference', 'ar'), ('4b', 'voxcpm-ultimate', 'ar'), ('baseline', 'qwen3', 'en')]
    for n, eng, lang in tests:
        ref = 'Video 1' if lang == 'en' else 'Video 2'; s = done.get((eng, lang))
        status = 'done' if s else ('not run: NeuCodec codec is gated on Hugging Face and the access token was not accepted' if eng == 'audar' else 'not run')
        L.append(f"| {n} | {ref} | {ENGINE_NAME[eng]} | {LANG[lang]} | {status} | {('`' + s['file'] + '` (local only)') if s else '—'} |")
    L += ['', '## Measurements', '', '| Metric | ' + ' | '.join(f"{ENGINE_NAME[s['engine']]} {s['lang'].upper()}" for s in S) + ' |', '|---|' + '---|' * len(S)]
    def row(name, f): L.append(f'| {name} | ' + ' | '.join(str(fmt(f(s))) for s in S) + ' |')
    row('Audio length (s)', lambda s: s['duration_s']); row('Generation wall time (s, incl. model load)', lambda s: s['generation'].get('wall_s'))
    row('Real-time factor (compute ÷ audio)', lambda s: s['generation'].get('real_time_factor')); row('Peak memory (GB RSS)', lambda s: s['generation'].get('peak_rss_gb'))
    row('Mean CPU use (% of one core; 400 = all 4)', lambda s: s['generation'].get('cpu_percent_avg')); row('Retries', lambda s: s['generation'].get('retries'))
    row('ASR word error rate (Whisper large-v3-turbo)', lambda s: s['wer']); row('ASR character error rate', lambda s: s['cer'])
    row('Speaker similarity to own reference (WavLM-SV cosine)', lambda s: s['speaker_similarity'])
    row('Similarity to the other reference (control)', lambda s: s['similarity_to_other_reference'])
    row('Chunk similarity, mean ± sd', lambda s: f"{s['chunk_similarity_mean']} ± {s['chunk_similarity_sd']}")
    row('Median F0 (Hz) / shift vs reference (semitones)', lambda s: f"{s.get('f0_median_hz')} / {s.get('f0_shift_vs_reference_semitones')}")
    row('Pitch spread (semitones)', lambda s: s.get('f0_sd_semitones')); row('Chunk-to-chunk F0 spread (semitones)', lambda s: s['chunk_f0_median_sd_semitones'])
    row('Speaking rate (words/min, ASR count)', lambda s: s['words_per_minute'])
    row('SQUIM estimates: STOI / PESQ / SI-SDR', lambda s: f"{s['squim']['stoi_est']} / {s['squim']['pesq_est']} / {s['squim']['si_sdr_est_db']} dB")
    row('Internal silences > 1 s / clipped samples', lambda s: f"{s['internal_silences_over_1s']} / {s['clipped_samples']}")
    L += ['', f"Reference values: English reference median F0 {M['references']['en']['f0_median_hz']} Hz, spread {M['references']['en']['f0_sd_semitones']} st; "
          f"Arabic reference median F0 {M['references']['ar']['f0_median_hz']} Hz, spread {M['references']['ar']['f0_sd_semitones']} st.", '',
          '## Scores (1–10)', '',
          'These scores are **provisional and metric-derived**. A dash means that no valid automatic proxy exists: the criterion needs a human listening test. '
          'Mapping: similarity from the WavLM cosine (0.80 → 5, 0.97 → 10); pronunciation from WER (English) or CER (Arabic) (10 − 40 × error); '
          'rhythm from the speaking-rate ratio to the reference (English only, because the Arabic reference is chanted); prosody from the pitch-spread ratio and pitch shift; '
          'consistency from chunk-to-chunk similarity and pitch spread; artefacts from the SQUIM PESQ estimate, long silences and clipping.', '',
          '| Criterion | ' + ' | '.join(f"{ENGINE_NAME[s['engine']]} {s['lang'].upper()}" for s in S) + ' | Listening score (fill in) |', '|---|' + '---|' * len(S) + '---|']
    for k, name in CRIT:
        L.append(f'| {name} | ' + ' | '.join(str(fmt(s['scores'].get(k))) for s in S) + ' |  |')
    L += ['', '## ASR transcripts of the test outputs', '']
    for s in S: L += [f"**{ENGINE_NAME[s['engine']]}, {LANG[s['lang']]}:** {s['asr_transcript']}", '']
    L += ['## Limitations', ''] + LIMITS
    (ROOT / 'reports/voice_cloning_evaluation.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('written reports/voice_cloning_evaluation.md')


SELECTION_TEXT = []   # filled by the caller from the measured results (see bottom of file)
ENGINES_TEXT = []
LIMITS = []

if __name__ == '__main__':
    import importlib
    txt = importlib.import_module('audio_engine.report_text')
    SELECTION_TEXT[:] = txt.SELECTION; ENGINES_TEXT[:] = txt.ENGINES; LIMITS[:] = txt.LIMITS
    if sys.argv[1] == 'evaluation': evaluation()
    elif sys.argv[1] == 'final':
        from .final_report import final
        final()
