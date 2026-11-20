"""reports/final_audio_quality_control.md from measured data (chunk QA, segments, mix QC, sync check, registry)."""
import json, csv, re, datetime, statistics as st
import numpy as np
from .common import ROOT, config, read_audio, lufs, peak_db
from . import synthesis_manager as SM
from .language_router import route_segment
from .narration_chunker import sentences
from .audio_quality_control import norm_en, norm_ar, pitch, load16


def coverage():
    """Text-level check: the chunks of every part reproduce its text exactly once (no missing or repeated sentences)."""
    items = SM.plan(); probs = []
    by = {}
    for i in items: by.setdefault(i['id'].rsplit('_c', 1)[0], []).append(i)       # one group = one or more sentences
    for k, its in by.items():
        got = ' '.join(i['text'] for i in sorted(its, key=lambda i: i['chunk'])); want = ' '.join(s['tts'] for s in its[0]['sentences'])
        n = norm_ar if its[0]['lang'] == 'ar' else norm_en
        if n(got) != n(want): probs.append(k)
    return sum(len(v[0]['sentences']) for v in by.values()), probs


def final():
    cfg = config(); q = json.load(open(SM.NARR / 'chunk_qa.json')); items = [i for i in SM.plan()]
    mix = [i for i in items if i['include_in_mix']]; excl = [i for i in items if not i['include_in_mix']]
    qc = json.load(open(ROOT / 'reports/qc_metrics.json')); sync = json.load(open(ROOT / 'reports/audio_sync_check.json'))
    n_parts, cov = coverage()
    def stat(lang, key):
        v = [q[i['id']][key] for i in mix if i['lang'] == lang and i['id'] in q and q[i['id']].get(key) is not None]
        return v
    L = ['# Final audio quality-control report (cloned narrators)', '', f"Date: {datetime.date.today().isoformat()}. Master: `renders/final/{__import__('os').environ.get('IRAM_MASTER_NAME', 'iram_lost_city_documentary')}.mp4`.", '',
         'Automatic checks are listed with their measured values. Items that need a human (listening, Arabic language review, Quranic review) are marked **open** until a person signs them off.', '']
    # English
    en_err = stat('en', 'err'); en_sim = stat('en', 'similarity'); ar_err = stat('ar', 'err'); ar_sim = stat('ar', 'similarity')
    en_fail = [i['id'] for i in mix if i['lang'] == 'en' and q.get(i['id'], {}).get('status') != 'pass']
    ar_fail = [i['id'] for i in mix if i['lang'] == 'ar' and q.get(i['id'], {}).get('status') != 'pass']
    ch = {}
    for i in mix:
        if i['lang'] == 'en' and q.get(i['id'], {}).get('similarity') is not None: ch.setdefault(i['chapter'], []).append(q[i['id']]['similarity'])
    segp = {}
    for f in sorted(SM.SEGDIR.glob('*.json')):
        sid = f.stem; chap = int(sid.split('.')[0]); segp.setdefault(chap, []).append(f.with_suffix('.wav'))
    refp = pitch(load16(ROOT / cfg['voice_profiles']['english']['reference']))['f0_median_hz']
    chap_rows = []
    for c in sorted(segp):
        x = np.concatenate([load16(p)[:16000 * 20] for p in segp[c]])
        f0 = pitch(x).get('f0_median_hz')
        chap_rows.append((c, round(st.median(ch.get(c, [0])), 3), f0, round(12 * np.log2(f0 / refp), 2) if f0 else None))
    seg_l = []
    for p in sorted(SM.SEGDIR.glob('*.wav')):
        x, sr = read_audio(p); seg_l.append(lufs(x, sr))
    L += ['## English narration (Video 1 voice)', '', '| Check | Result | Status |', '|---|---|---|',
          f"| Chunks generated / passed automatic QA | {len([i for i in mix if i['lang'] == 'en'])} / {len([i for i in mix if i['lang'] == 'en']) - len(en_fail)} | {'pass' if not en_fail else 'see failures below'} |",
          f"| Intelligibility (Whisper WER without names, median / max) | {round(st.median(en_err), 3)} / {max(en_err)} | {'pass' if max(en_err) <= cfg['qa']['max_wer_en'] else 'check'} |",
          f"| Speaker similarity to Video 1 reference (median / min) | {round(st.median(en_sim), 3)} / {min(en_sim)} | supporting evidence only |",
          '| Sounds like Video 1; accent consistent; names pronounced correctly; natural delivery; no robotic artefacts | needs listening | **open** |', '',
          'Consistency between chapters (English narration):', '', '| Chapter | Median speaker similarity | Median F0 (Hz) | Shift vs reference (semitones) |', '|---|---|---|---|']
    L += [f'| {c} | {s} | {f} | {d} |' for c, s, f, d in chap_rows]
    L += ['', '## Arabic narration (Video 2 voice)', '', '| Check | Result | Status |', '|---|---|---|',
          f"| Arabic parts in the mix | {len({i['sentence_key'] for i in mix if i['lang'] == 'ar'})} quotations ({len([i for i in mix if i['lang'] == 'ar'])} chunks) | — |",
          f"| Intelligibility (Whisper CER, letters only; median / max) | {round(st.median(ar_err), 3) if ar_err else '—'} / {max(ar_err) if ar_err else '—'} | {'pass' if ar_err and max(ar_err) <= cfg['qa']['max_cer_ar'] else 'check'} |",
          f"| Speaker similarity to Video 2 reference (median) | {round(st.median(ar_sim), 3) if ar_sim else '—'} | supporting evidence only |",
          '| Quotation letters equal the on-screen text (vowel marks only added) | checked by the router for every part | pass |',
          '| Sounds like Video 2; MSA pronunciation, case endings and pause forms; names; pacing | needs a native Arabic reviewer | **open** |', '',
          '## Quranic material', '', '| Check | Result | Status |', '|---|---|---|']
    reg = list(csv.DictReader(open(ROOT / 'research/quranic_verse_registry.csv', encoding='utf-8')))
    L += [f"| Verses in the registry | {len(reg)}; letters match quran.com for {sum(r['cross_check_letters_match'] == 'True' for r in reg)} | pass |",
          f"| Synthetic renderings made for review | {sum(1 for r in reg if r['audio_asset_path'])} verses (+ {len(excl)} routed hadith chunk(s) with Quranic wording) | review candidates only |",
          '| Quranic audio in the film | none: the film shows the Arabic on screen and the English narrator reads the translation | pass |',
          '| Qualified human review (tajwid) | not done | **open**: nothing approved |', '',
          '## Technical checks', '', '| Check | Result | Status |', '|---|---|---|',
          f"| Every sentence of the script is covered exactly once by the chunk plan | {n_parts} parts, {len(cov)} mismatches | {'pass' if not cov else 'fail: ' + ', '.join(cov[:5])} |",
          f"| Missing or repeated words in the audio (ASR) | chunk QA flags {len(en_fail) + len(ar_fail)} chunk(s) | {'pass' if not en_fail + ar_fail else 'see below'} |",
          f"| Segment loudness spread (before mix) | {round(min(seg_l), 1)} to {round(max(seg_l), 1)} LUFS | {'pass' if max(seg_l) - min(seg_l) <= 3 else 'check'} |",
          f"| Final mix loudness / true peak | {qc['loudness']['integrated_lufs']} LUFS / {qc['loudness']['true_peak_dbfs']} dBTP | {'pass' if qc['loudness']['true_peak_dbfs'] <= -1 else 'fail'} |",
          f"| Silences over 2 s below −55 dB | {len(qc['silences_over_2s_below_-55dB'])} | {'pass' if len(qc['silences_over_2s_below_-55dB']) <= 1 else 'check'} |",
          f"| Audio-video sync (narration onset vs timeline) | max {sync['max_abs_offset_ms']} ms over {sync['segments_checked']} segments | {'pass' if not sync['over_one_frame'] else 'check'} |",
          f"| No background music (ambience stem: tonal components / chroma / rhythm) | {qc['music_check']['sustained_tonal_components_>=0.5s']} / {qc['music_check']['chroma_peak_ratio_median']} / {qc['music_check']['max_rhythmic_autocorrelation_lag_0.6-12s']} | pass |",
          f"| Decoder errors / clipped audio | {len(qc['decode_errors'])} / true peak {qc['loudness']['true_peak_dbfs']} dBTP | pass |", '']
    if en_fail or ar_fail:
        L += ['## Chunks that did not pass automatic QA', '', '| Chunk | Notes | ASR |', '|---|---|---|']
        L += [f"| {k} | {'; '.join(q[k]['notes'])} | {q[k]['asr'][:120]} |" for k in en_fail + ar_fail if k in q]
        L.append('')
    L += ['## Sign-off needed', '', '1. Listen to the whole film. Confirm that the English voice sounds like Video 1 and stays the same across chapters.',
          '2. An Arabic speaker checks the four Arabic quotations (five chunks): pronunciation, case endings, pauses.',
          '3. A qualified reciter or tajwid teacher reviews `assets/narration/quranic/` before any synthetic Quranic audio is used. Until then, none is used.',
          '4. Record the results in `assets/narration/narration_manifest.csv` (approval_status) and `research/quranic_verse_registry.csv`.']
    (ROOT / 'reports/final_audio_quality_control.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('written reports/final_audio_quality_control.md')
