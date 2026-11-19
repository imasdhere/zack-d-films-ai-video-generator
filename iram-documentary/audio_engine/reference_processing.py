"""Reference processing: extract, analyse, select, clean and document a narrator reference clip.

  python -m audio_engine.reference_processing --profile english --video <Video1.mp4>
  python -m audio_engine.reference_processing --profile arabic  --video <Video2.mp4>

Outputs in voice_profiles/<id>/ :
  original_video/              unchanged copy of the upload (sha256 checked; not in git)
  extracted_audio/             full soundtrack at the source rate + 16 kHz mono analysis copy (not in git)
  cleaned_reference.wav        the clip used for cloning (not in git)
  reference_transcript.txt     verified transcript of cleaned_reference.wav
  full_transcript.txt          transcript of the whole recording
  voice_metadata.json          measurements, choices and their reasons
The speaker's pitch is never shifted. Cleaning is limited to a rumble high-pass, optional dereverberation,
trimming, short edge fades and a loudness gain.
"""
import argparse, json, shutil, pathlib, datetime
import numpy as np
from .common import ROOT, WORK, config, sha256, read_audio, write_wav, ffilter, lufs, peak_db, frame_db, run

ASR_EN = WORK / 'models/whisper/small.en.pt'
ASR_MULTI = WORK / 'models/whisper-large-v3-turbo'


# ------------------------------------------------------------------ transcription with word times
def transcribe_words(wav16, lang):
    """Word-level transcript. English: Whisper small.en; Arabic: Whisper large-v3-turbo (chunks < 28 s)."""
    import torch
    torch.set_num_threads(4)
    if lang == 'en':
        import whisper
        m = whisper.load_model(str(ASR_EN))
        r = m.transcribe(wav16, language='en', word_timestamps=True, condition_on_previous_text=False, fp16=False)
        return [{'w': w['word'].strip(), 's': float(w['start']), 'e': float(w['end'])} for s in r['segments'] for w in s['words']]
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    model = AutoModelForSpeechSeq2Seq.from_pretrained(ASR_MULTI, dtype=torch.float32); proc = AutoProcessor.from_pretrained(ASR_MULTI)
    asr = pipeline('automatic-speech-recognition', model=model, tokenizer=proc.tokenizer, feature_extractor=proc.feature_extractor, return_timestamps='word')
    sr = 16000; pauses = find_pauses(wav16, sr, 0.25)
    cuts = [0.0] + [(a + b) / 2 for a, b in pauses] + [len(wav16) / sr]
    groups, start, last = [], 0.0, 0.0
    for c in cuts[1:]:
        if c - start > 28: groups.append((start, last)); start = last
        last = c
    groups.append((start, last)); out = []
    for a, b in groups:
        if b - a < 0.3: continue
        with torch.inference_mode():
            r = asr(wav16[int(a * sr):int(b * sr)], generate_kwargs={'language': 'arabic', 'task': 'transcribe', 'num_beams': 1})
        for c in r['chunks']:
            s0, e0 = c['timestamp']
            out.append({'w': c['text'].strip(), 's': round(a + float(s0), 2), 'e': round(a + float(e0 if e0 is not None else s0), 2)})
    return out


# ------------------------------------------------------------------ measurements
def find_pauses(x, sr, min_len, thr_db=-50):
    db = frame_db(x, sr, 0.05, 0.01); sil = db < thr_db; runs, s = [], None
    for i, v in enumerate(np.append(sil, False)):
        if v and s is None: s = i
        if not v and s is not None:
            if (i - s) * 0.01 >= min_len: runs.append((s * 0.01, i * 0.01 + 0.05))
            s = None
    return runs


def pitch_stats(x, sr):
    import librosa
    f0, vf, _ = librosa.pyin(x, fmin=50, fmax=400, sr=sr, frame_length=2048, hop_length=256)
    v = f0[vf]
    if len(v) < 10: return {}
    st = 12 * np.log2(v / 55.0); runs, cur = [], 0
    for i in range(1, len(f0)):
        if vf[i] and vf[i - 1] and abs(12 * np.log2(f0[i] / f0[i - 1])) < 0.35: cur += 1
        else:
            if cur: runs.append(cur * 256 / sr)
            cur = 0
    runs = np.array(runs or [0.0])
    return {'f0_median_hz': round(float(np.median(v)), 1), 'f0_p10_hz': round(float(np.percentile(v, 10)), 1), 'f0_p90_hz': round(float(np.percentile(v, 90)), 1),
            'f0_sd_semitones': round(float(st.std()), 2), 'voiced_fraction': round(float(vf.mean()), 2),
            'sustained_pitch_runs_ge_0.4s': int((runs >= 0.4).sum()), 'longest_sustained_pitch_s': round(float(runs.max()), 2)}


def tail_level(x, sr):
    """Median level 150-300 ms after each phrase end, relative to the last 150 ms of the phrase (dB).
    Gated, dry speech is around -50 dB or lower; a reverberant room leaves a tail around -20 to -30 dB."""
    db = np.maximum(frame_db(x, sr, 0.02, 0.005), -90.0); loud = np.percentile(db, 95); act = db > loud - 25; out = []
    for i in range(30, len(db) - 70):
        if act[i - 1] and not act[i] and act[i - 30:i].mean() > 0.8 and (~act[i:i + 70]).mean() > 0.9:
            out.append(db[i + 30:i + 60].mean() - db[i - 30:i].mean())
    return round(float(np.median(out)), 1) if out else None


def band_limit(x, sr):
    S = np.abs(np.fft.rfft(x[:sr * 30] * np.hanning(min(len(x), sr * 30)))) ** 2
    fr = np.fft.rfftfreq(min(len(x), sr * 30), 1 / sr)
    db = 10 * np.log10(np.convolve(S, np.ones(64) / 64, 'same') + 1e-20); pk = db.max()
    return {f'last_hz_above_{-t}dB': int(fr[np.where(db > pk + t)[0].max()]) for t in (-40, -60)}


def pause_noise(x, sr, pauses):
    """Noise floor and tonal content inside pauses (music-bed check)."""
    segs = [x[int(a * sr):int(b * sr)] for a, b in pauses if b - a > 0.2]
    if not segs: return {'pause_rms_dbfs': None}
    y = np.concatenate(segs); rms = 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-12)
    S = np.abs(np.fft.rfft(y * np.hanning(len(y)))); S /= S.max() + 1e-12
    flat = float(np.exp(np.mean(np.log(S + 1e-12))) / (np.mean(S) + 1e-12))
    return {'pause_rms_dbfs': round(float(rms), 1), 'pause_spectral_flatness': round(flat, 3), 'pause_total_s': round(len(y) / sr, 2)}


def analyse(x, sr, words=None):
    pauses = find_pauses(x, sr, 0.2)
    d = {'duration_s': round(len(x) / sr, 2), 'sample_rate': sr, 'peak_dbfs': round(peak_db(x), 2),
         'clipped_samples': int((np.abs(x) >= 0.999).sum()), 'integrated_lufs': round(lufs(x, sr), 1),
         'phrase_end_tail_db': tail_level(x, sr), 'pause_count': len(pauses)}
    d.update(band_limit(x, sr)); d.update(pause_noise(x, sr, pauses)); d.update(pitch_stats(x, sr))
    if words:
        sp = sum(w['e'] - w['s'] for w in words)
        d['words'] = len(words); d['words_per_minute'] = round(60 * len(words) / max(1e-6, words[-1]['e'] - words[0]['s']), 1)
        d['articulation_words_per_s'] = round(len(words) / max(sp, 1e-6), 2)
    return d


# ------------------------------------------------------------------ clip selection
def candidates(words, pauses, dur, sel):
    """Windows that start and end inside pauses, avoid excluded ranges and last min_s..max_s."""
    gaps = [(w0['e'] + w1['s']) / 2 for w0, w1 in zip(words, words[1:]) if w1['s'] - w0['e'] >= 0.25]
    bounds = sorted({round(v, 2) for v in [0.0, dur] + [(a + b) / 2 for a, b in pauses] + gaps})
    ex = [(a, b) for a, b, _ in sel.get('exclude', [])]
    out = []
    for i, a in enumerate(bounds):
        for b in bounds[i + 1:]:
            if not sel['min_s'] <= b - a <= sel['max_s']: continue
            if any(a < e1 and b > e0 for e0, e1 in ex): continue
            ws = [w for w in words if w['s'] >= a - 0.05 and w['e'] <= b + 0.05]
            if ws: out.append((round(a, 2), round(b, 2), ws))
    return out


def score(m):
    """Prefer a steady, narration-like register: low pitch spread, few sustained (chanted) vowels, fast decay."""
    s = -m.get('f0_sd_semitones', 9) - 0.6 * m.get('sustained_pitch_runs_ge_0.4s', 0)
    s += 0.02 * min(-(m.get('phrase_end_tail_db') or 0), 60) + 0.05 * m['duration_s']
    return round(s, 3)


def dereverb_wpe(x, sr):
    from nara_wpe.wpe import wpe
    from nara_wpe.utils import stft, istft
    X = stft(x[None], size=512, shift=128).transpose(2, 0, 1)
    Y = wpe(X, taps=10, delay=3, iterations=3, statistics_mode='full').transpose(1, 2, 0)
    y = istft(Y, size=512, shift=128)[0][:len(x)]
    return y.astype(np.float32)


def clean(x, sr, a, b, dereverb):
    pad0, pad1 = 0.12, 0.25
    y = x[max(0, int((a - pad0) * sr)):int((b + pad1) * sr)].copy()
    y = ffilter(y, sr, 'highpass=f=60:poles=2')
    if dereverb == 'wpe': y = dereverb_wpe(y, sr)
    n = int(0.012 * sr); y[:n] *= np.linspace(0, 1, n); y[-n:] *= np.linspace(1, 0, n)
    y *= 10 ** ((-20.0 - lufs(y, sr)) / 20)
    if peak_db(y) > -1.0: y *= 10 ** ((-1.0 - peak_db(y)) / 20)
    return y.astype(np.float32)


# ------------------------------------------------------------------ main
def process(profile, video, transcript_override=None, choose=None):
    cfg = config(); p = cfg['voice_profiles'][profile]; d = ROOT / p['dir']; sel = p['reference_selection']
    (d / 'original_video').mkdir(parents=True, exist_ok=True); (d / 'extracted_audio').mkdir(exist_ok=True); (d / 'test_samples').mkdir(exist_ok=True)
    h = sha256(video)
    if h != p['source']['sha256']: raise SystemExit(f'{video}: sha256 {h} does not match the configured source')
    orig = d / 'original_video' / p['source']['upload_name']
    if not orig.exists(): shutil.copy2(video, orig)
    probe = json.loads(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,bit_rate:stream=codec_type,codec_name,sample_rate,channels,bit_rate,width,height', '-of', 'json', orig]).stdout)
    full, sr = read_audio(orig)                    # mono mix at the source rate
    st, _ = read_audio(orig, mono=False)
    write_wav(d / 'extracted_audio/original_audio.wav', st, sr)
    x16, _ = read_audio(orig, sr=16000); write_wav(d / 'extracted_audio/original_audio_16k_mono.wav', x16, 16000)
    lr = float(np.corrcoef(st[:, 0], st[:, 1])[0, 1]) if st.shape[1] == 2 else 1.0
    words = transcribe_words(x16, p['language'])
    full_m = analyse(full, sr, words); full_m['left_right_correlation'] = round(lr, 4)
    pauses = find_pauses(full, sr, 0.2)
    cands = []
    for a, b, ws in candidates(words, pauses, len(full) / sr, sel):
        m = analyse(full[int(a * sr):int(b * sr)], sr, ws); m['score'] = score(m)
        cands.append({'start': a, 'end': b, 'text': ' '.join(w['w'] for w in ws), **m})
    cands.sort(key=lambda c: -c['score'])
    best = cands[0] if choose is None else min(cands, key=lambda c: abs(c['start'] - choose[0]) + abs(c['end'] - choose[1]))
    a, b = best['start'], best['end']
    der = sel.get('dereverb', 'none'); der_eval = None
    if der == 'evaluate':
        dry = clean(full, sr, a, b, 'none'); wet = clean(full, sr, a, b, 'wpe')
        r0, r1 = tail_level(dry, sr), tail_level(wet, sr)
        der_eval = {'phrase_end_tail_db_without': r0, 'phrase_end_tail_db_with_wpe': r1, 'rule': 'use WPE if it lowers the tail by >= 3 dB'}
        der = 'wpe' if (r0 is not None and r1 is not None and r1 <= r0 - 3.0) else 'none'
        write_wav(d / 'extracted_audio/reference_clip_no_dereverb.wav', dry, sr)
        write_wav(d / 'extracted_audio/reference_clip_wpe.wav', wet, sr)
    ref = clean(full, sr, a, b, der)
    write_wav(d / 'cleaned_reference.wav', ref, sr)
    write_wav(d / 'extracted_audio/reference_clip_raw.wav', full[int((a - 0.12) * sr):int((b + 0.25) * sr)], sr)
    text = transcript_override or best['text']
    (d / 'reference_transcript.txt').write_text(text.strip() + '\n', encoding='utf-8')
    (d / 'full_transcript.txt').write_text(' '.join(w['w'] for w in words) + '\n', encoding='utf-8')
    json.dump(words, open(d / 'extracted_audio/word_timestamps.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    meta = {'profile': p['id'], 'language': p['language'], 'created': datetime.date.today().isoformat(),
            'consent': cfg['consent'], 'source': {**p['source'], 'probe': probe},
            'full_recording': full_m, 'reference_clip': {'start_s': a, 'end_s': b, 'padding_s': [0.12, 0.25], 'selection_score': best['score'],
                                                         'measurements': {k: v for k, v in best.items() if k not in ('text',)},
                                                         'cleaned_measurements': analyse(ref, sr)},
            'selection_rules': sel, 'dereverberation': {'method': der, 'evaluation': der_eval},
            'processing': ['mono downmix (L/R correlation above)', 'high-pass 60 Hz, 2 poles', f'dereverberation: {der}', '12 ms edge fades',
                           'loudness gain to -20 LUFS, peak <= -1 dBFS', 'no pitch shift, no EQ, no time stretch'],
            'transcript': {'reference': text.strip(), 'asr_model': 'Whisper small.en' if p['language'] == 'en' else 'Whisper large-v3-turbo',
                           'asr_raw': best['text'], 'override_applied': bool(transcript_override)},
            'candidates_top5': [{k: c[k] for k in ('start', 'end', 'score', 'f0_median_hz', 'f0_sd_semitones', 'sustained_pitch_runs_ge_0.4s', 'phrase_end_tail_db', 'text')} for c in cands[:5]]}
    json.dump(meta, open(d / 'voice_metadata.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({'profile': profile, 'clip': [a, b], 'dereverb': der, 'text': text}, ensure_ascii=False))
    return meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--profile', required=True); ap.add_argument('--video', required=True)
    ap.add_argument('--transcript', default=None, help='verified transcript of the selected clip (overrides ASR spelling)')
    ap.add_argument('--choose', nargs=2, type=float, default=None, help='force a clip near START END (s)')
    a = ap.parse_args()
    process(a.profile, pathlib.Path(a.video), a.transcript, a.choose)
