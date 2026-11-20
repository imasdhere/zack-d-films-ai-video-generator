"""Voice-stability test (decision record): which VoxCPM2 set-up keeps the Video 1 voice steady over whole paragraphs?

  python -m audio_engine.stability_test refs      # build the long and padded reference clips
  python -m audio_engine.stability_test run       # generate the test paragraphs under each set-up, then score them

Set-ups: cloning mode (reference / ultimate) x reference clip (9.9 s, or 18 s made from both steady passages of Video 1).
Text: whole paragraphs from the screenplay, chunked by paragraph (several sentences per chunk, at most 260 characters),
with the names Iram and ʿĀd written in Arabic script so that the model says them the Arabic way.
Scores per chunk: speaker similarity to Video 1, median pitch, share of frames far above the median (cracks),
English WER without names, first word. Results: workflows/tts/eval/voice_stability_test.json
"""
import json, sys, pathlib, re
import numpy as np, yaml
from .common import ROOT, WORK, config, read_audio, write_wav, lufs, peak_db
from .narration_chunker import sentences
from .language_router import tts_text_en

P = ROOT / 'voice_profiles/english_narrator'
SEGS = ['0.01', '1.04', '2.04', '3.04', '3.08', '5.10']
ARABIC_NAMES = {'Iram': 'إِرَم', 'ʿĀd': 'عَاد'}          # spoken in Arabic, in the English narrator's voice


def arabic_names(text):
    t = re.sub(r'ʿĀd(?![a-zʾ])', ARABIC_NAMES['ʿĀd'], text)
    return re.sub(r'\bIram\b', ARABIC_NAMES['Iram'], t)


def paragraph_chunks(text, limit=260):
    out, cur = [], ''
    for s in sentences(text, 'en'):
        if cur and len(cur) + 1 + len(s) > limit: out.append(cur); cur = s
        else: cur = (cur + ' ' + s).strip()
    if cur: out.append(cur)
    return out


def refs():
    from .reference_processing import clean
    x, sr = read_audio(P / 'extracted_audio/original_audio.wav')
    a = clean(x, sr, 3.09, 14.98, 'none'); b = clean(x, sr, 18.28, 25.55, 'none')
    long_ = np.concatenate([a, np.zeros(int(0.45 * sr), np.float32), b])
    long_ *= 10 ** ((-20 - lufs(long_, sr)) / 20)
    write_wav(P / 'extracted_audio/reference_long.wav', long_, sr)
    (P / 'extracted_audio/reference_long_transcript.txt').write_text(
        "If you breathe with your belly, then your voice starts to drop a couple of frequencies. When you breathe with your "
        "diaphragm, it would sound something like this. It wouldn't be very, very low. You need to drop your voice and breathe "
        "through the belly. That's how you make that Hollywood sound.\n", encoding='utf-8')
    for name, src in (('reference_long_pad.wav', long_), ('reference_short_pad.wav', read_audio(P / 'cleaned_reference.wav')[0])):
        write_wav(P / 'extracted_audio' / name, np.concatenate([src, np.zeros(int(0.6 * sr), np.float32)]), sr)
    print('long reference', round(len(long_) / sr, 2), 's')


def setups():
    short_t = (P / 'reference_transcript.txt').read_text().strip(); long_t = (P / 'extracted_audio/reference_long_transcript.txt').read_text().strip()
    ex = P / 'extracted_audio'
    return {'ref_short': ('reference', P / 'cleaned_reference.wav', short_t), 'ref_long': ('reference', ex / 'reference_long.wav', long_t),
            'ult_short_pad': ('ultimate', ex / 'reference_short_pad.wav', short_t), 'ult_long_pad': ('ultimate', ex / 'reference_long_pad.wav', long_t)}


def run():
    from . import engines
    script = yaml.safe_load(open(ROOT / 'screenplay/script.yaml', encoding='utf-8'))
    segs = {s['id']: s for ch in script['chapters'] for s in ch['segments']}
    out = WORK / 'stability'; out.mkdir(exist_ok=True); jobs = []
    for name, (mode, ref, rt) in setups().items():
        for sid in SEGS:
            for k, c in enumerate(paragraph_chunks(tts_text_en(arabic_names(' '.join(segs[sid]['text'].split())), 'voxcpm'))):
                jobs.append({'id': f'{name}|{sid}|{k}', 'text': c, 'lang': 'en', 'out': str(out / f'{name}_{sid}_{k}.wav'),
                             'ref_wav': str(ref), 'ref_text': rt, 'seed': 31 + k, 'params': {'mode': mode}})
    engines.get('voxcpm').run(jobs, log_path=WORK / 'logs' / 'stability_test.log', force=True)
    score(jobs)


def score(jobs=None):
    from .audio_quality_control import load16, embed, cos, transcribe, wer_without_names, norm_en
    import librosa
    if jobs is None: jobs = json.load(open(ROOT / 'workflows/tts/eval/voice_stability_test.json'))['jobs']
    ref = embed(load16(P / 'cleaned_reference.wav')); res = {}
    for j in jobs:
        if not pathlib.Path(j['out']).exists(): continue
        x = load16(j['out'])
        f0, vf, _ = librosa.pyin(x, fmin=50, fmax=500, sr=16000, frame_length=1024, hop_length=160); v = f0[vf]
        med = float(np.median(v)) if len(v) else None
        high = float((12 * np.log2(v / med) > 7).mean()) if len(v) else None
        hyp = transcribe(x, 'en'); plain = re.sub(r'[؀-ۿ]+', 'NAME', j['text'])
        r = {'sim': round(cos(embed(x), ref), 3), 'f0': round(med, 1) if med else None, 'high': round(high, 3) if high is not None else None,
             'wer': wer_without_names(plain.replace('NAME', 'Iram'), hyp), 'first_ok': bool(norm_en(hyp)) and norm_en(plain)[0] == norm_en(hyp)[0],
             'asr': hyp, 'dur': round(len(x) / 16000, 2)}
        res[j['id']] = r; print(json.dumps({'id': j['id'], **{k: r[k] for k in ('sim', 'f0', 'high', 'wer', 'first_ok')}}), flush=True)
    summ = {}
    for name in setups():
        rs = [r for k, r in res.items() if k.startswith(name + '|')]
        if not rs: continue
        f0s = np.array([r['f0'] for r in rs if r['f0']])
        summ[name] = {'chunks': len(rs), 'sim_mean': round(float(np.mean([r['sim'] for r in rs])), 3), 'sim_min': min(r['sim'] for r in rs),
                      'f0_median': round(float(np.median(f0s)), 1), 'f0_sd_semitones': round(float((12 * np.log2(f0s / np.median(f0s))).std()), 2),
                      'chunks_with_cracks': sum(1 for r in rs if (r['high'] or 0) > 0.05), 'wer_mean': round(float(np.mean([r['wer'] for r in rs])), 3),
                      'first_word_ok': f"{sum(r['first_ok'] for r in rs)}/{len(rs)}"}
    json.dump({'summary': summ, 'results': res, 'jobs': jobs}, open(ROOT / 'workflows/tts/eval/voice_stability_test.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(summ, indent=1))




def names():
    """Spelling variants of the two names, in three carrier sentences, with the production set-up (ultimate, padded clip)."""
    from . import engines
    mode, ref, rt = setups()['ult_short_pad']; out = WORK / 'names'; out.mkdir(exist_ok=True); jobs = []
    variants = {'v1': ('عَاد', 'إِرَم'), 'v2': ('عَادْ', 'إِرَمْ'), 'v3': ('عاد', 'إرم')}
    carriers = ['They were the tribe of {A}, and their city was called {I}.', 'No one has dated the people of {A}, and no one has found {I}.',
                'The story of {A} begins with a single name: {I}.']
    for v, (a, i) in variants.items():
        for k, c in enumerate(carriers):
            jobs.append({'id': f'{v}|{k}', 'text': c.format(A=a, I=i), 'lang': 'en', 'out': str(out / f'{v}_{k}.wav'), 'ref_wav': str(ref),
                         'ref_text': rt, 'seed': 71 + k, 'params': {'mode': mode}})
    engines.get('voxcpm').run(jobs, log_path=WORK / 'logs' / 'name_variants.log', force=True)
    print('NAMES_GENERATED')

if __name__ == '__main__':
    {'refs': refs, 'run': run, 'score': score, 'names': names}[sys.argv[1]]()
