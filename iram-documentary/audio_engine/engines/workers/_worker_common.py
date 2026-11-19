"""Shared job loop for engine workers. Runs inside each engine's own venv (numpy + soundfile only here).

Job file: JSON lines, one chunk per line:
  {"id": "...", "text": "...", "lang": "en"|"ar", "out": "/abs/path.wav", "ref_wav": "...", "ref_text": "...",
   "seed": 123, "params": {...}}
Each finished job writes <out> (native sample rate) and <out>.json, and prints one JSON line.
"""
import argparse, json, os, pathlib, time, sys
import numpy as np
import soundfile as sf

# Typical narration speed in characters per second (spaces included), used only for sanity bounds.
CPS = {'en': 14.0, 'ar': 11.0}


def args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', required=True); ap.add_argument('--model', required=True)
    ap.add_argument('--codec', default=None); ap.add_argument('--force', action='store_true')
    ap.add_argument('--threads', type=int, default=4); ap.add_argument('--max_attempts', type=int, default=3)
    return ap.parse_args()


def trim(w, sr, thr=0.012):
    """Remove leading and trailing near-silence so that pauses are set by the assembler, not the model."""
    if not len(w): return w
    idx = np.where(np.abs(w) > thr * (np.abs(w).max() + 1e-9))[0]
    if not len(idx): return w
    return w[max(0, idx[0] - int(0.03 * sr)): idx[-1] + int(0.10 * sr)]


def plausible(text, lang, dur):
    exp = len(text) / CPS.get(lang, 13.0)
    return 0.45 * exp < dur < 2.3 * exp + 1.0, round(exp, 2)


def loop(engine, synth, a):
    """synth(job, seed) -> (float32 wav, sr). Retries implausible durations with a new seed."""
    jobs = [json.loads(l) for l in open(a.jobs, encoding='utf-8') if l.strip()]
    for j in jobs:
        out = pathlib.Path(j['out'])
        if out.exists() and not a.force:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time(); tries = []; best = None
        for k in range(a.max_attempts):
            seed = int(j.get('seed', 1234)) + 1000 * k
            try:
                w, sr = synth(j, seed)
            except Exception as e:  # report and retry with another seed
                tries.append({'seed': seed, 'error': repr(e)[:300]}); continue
            w = trim(np.asarray(w, np.float32).reshape(-1), sr); d = len(w) / sr
            ok, exp = plausible(j['text'], j.get('lang', 'en'), d)
            tries.append({'seed': seed, 'dur': round(d, 2), 'expected': exp, 'ok': ok})
            if best is None or ok: best = (w, sr, seed)
            if ok: break
        if best is None:
            print(json.dumps({'id': j['id'], 'engine': engine, 'status': 'failed', 'attempts': tries}), flush=True); continue
        w, sr, seed = best
        sf.write(out, w, sr, subtype='FLOAT')
        meta = {'id': j['id'], 'engine': engine, 'sr': sr, 'duration': round(len(w) / sr, 3), 'compute_s': round(time.time() - t0, 1),
                'seed': seed, 'attempts': tries, 'text': j['text'], 'lang': j.get('lang'), 'params': j.get('params', {}),
                'status': 'ok' if tries[-1].get('ok') else 'implausible_duration'}
        json.dump(meta, open(str(out) + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(json.dumps({k: meta[k] for k in ('id', 'engine', 'duration', 'compute_s', 'status')}), flush=True)
    print(json.dumps({'engine': engine, 'done': True}), flush=True)
