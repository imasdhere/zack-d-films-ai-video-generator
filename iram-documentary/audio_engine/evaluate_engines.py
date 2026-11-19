"""Voice-cloning evaluation: identical test text per language, each engine against its language's reference.

  python -m audio_engine.evaluate_engines generate --engine voxcpm --lang en
  python -m audio_engine.evaluate_engines score             # metrics for every sample present -> reports/voice_clone_metrics.json
Samples: voice_profiles/<profile>/test_samples/<engine>_<lang>_test.wav (+ chunk files in test_samples/<engine>/).
"""
import argparse, json, time, pathlib, subprocess, re
import numpy as np, yaml
from .common import ROOT, WORK, config, write_wav, lufs, peak_db, strip_diacritics
from .narration_chunker import chunk
from .language_router import tts_text_en
from . import engines

TEXTS = yaml.safe_load(open(ROOT / 'workflows/tts/eval/clone_test_texts.yaml', encoding='utf-8'))
PROFILE = {'en': 'english', 'ar': 'arabic'}
OUT_SR = 48000


def prof(lang):
    return config()['voice_profiles'][PROFILE[lang]]


def assemble(chunks, out, pause=0.45):
    import soundfile as sf
    from scipy.signal import resample_poly
    parts = []
    for c in chunks:
        w, sr = sf.read(c['out'], dtype='float32')
        if sr != OUT_SR: w = resample_poly(w, OUT_SR, sr).astype(np.float32)
        parts += [w, np.zeros(int(OUT_SR * (pause if c['pause_after'] == 'sentence' else 0.25)), np.float32)]
    y = np.concatenate(parts[:-1]); write_wav(out, y, OUT_SR)
    return len(y) / OUT_SR


def generate(engine, lang, seed=20261119):
    p = prof(lang); d = ROOT / p['dir'] / 'test_samples'; cd = d / engine; cd.mkdir(parents=True, exist_ok=True)
    text = TEXTS[lang] if lang == 'ar' else tts_text_en(TEXTS['en'], engine)
    lim = config()['chunking'][f'{lang}_max_chars']
    cs = chunk(text, lang, lim, merge_short=config()['chunking'].get(f'merge_short_{lang}', False))
    jobs = [{'id': f'{engine}_{lang}_{i:02d}', 'text': c['text'], 'lang': lang, 'out': str(cd / f'{lang}_{i:02d}.wav'),
             'ref_wav': str(ROOT / p['reference']), 'ref_text': (ROOT / p['transcript']).read_text(encoding='utf-8').strip(),
             'seed': seed + i, 'pause_after': c['pause_after']} for i, c in enumerate(cs)]
    ad = engines.get(engine); probs = ad.check()
    if probs: raise SystemExit(f'{engine} not ready: {probs}')
    log = WORK / 'logs' / f'eval_{engine}_{lang}.log'
    t0 = time.time()
    rc, rss_kb, cpu_pct = run_measured(ad.worker_cmd(_write_jobs(jobs, engine, lang)), log)
    wall = time.time() - t0
    if rc != 0: raise SystemExit(f'worker failed ({rc}); see {log}')
    metas = [json.load(open(j['out'] + '.json', encoding='utf-8')) for j in jobs]
    dur = assemble(jobs, d / f'{engine}_{lang}_test.wav')
    info = {'engine': engine, 'lang': lang, 'reference': p['reference'], 'chunks': len(jobs), 'audio_s': round(dur, 2), 'wall_s': round(wall, 1),
            'compute_s_sum_chunks': round(sum(m['compute_s'] for m in metas), 1), 'model_load_and_overhead_s': round(wall - sum(m['compute_s'] for m in metas), 1),
            'real_time_factor': round(sum(m['compute_s'] for m in metas) / max(dur, 1e-6), 2),
            'peak_rss_gb': round(rss_kb / 1e6, 2), 'cpu_percent_avg': cpu_pct,
            'threads': 4, 'device': 'cpu', 'params': {**config()['engines'][engine].get('params', {})},
            'retries': sum(len(m['attempts']) - 1 for m in metas), 'implausible_chunks': [m['id'] for m in metas if m['status'] != 'ok'], 'seed_base': seed,
            'input_text': text}
    json.dump(info, open(d / f'{engine}_{lang}_test.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in info.items() if k != 'input_text'}))


def run_measured(cmd, log):
    """Run a worker, sampling its resident memory every 0.5 s; return (exit code, peak RSS kB, mean CPU %)."""
    import os
    t0 = time.time(); peak = 0
    with open(log, 'w') as lf:
        p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
        while p.poll() is None:
            try:
                for line in open(f'/proc/{p.pid}/status'):
                    if line.startswith('VmRSS:'): peak = max(peak, int(line.split()[1]))
                st = open(f'/proc/{p.pid}/stat').read().split(); ticks = int(st[13]) + int(st[14])
            except (FileNotFoundError, ProcessLookupError, IndexError): pass
            time.sleep(0.5)
    cpu = round(100 * ticks / os.sysconf('SC_CLK_TCK') / max(time.time() - t0, 1e-6)) if 'ticks' in locals() else None
    return p.returncode, peak, cpu


def _write_jobs(jobs, engine, lang):
    p = WORK / 'scratch' / f'eval_{engine}_{lang}.jsonl'
    with open(p, 'w', encoding='utf-8') as f:
        for j in jobs:
            j2 = {k: v for k, v in j.items() if k != 'pause_after'}; j2['params'] = config()['engines'][engine].get('params', {})
            f.write(json.dumps(j2, ensure_ascii=False) + '\n')
    return p


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--engine'); ap.add_argument('--lang')
    a = ap.parse_args()
    if a.cmd == 'generate': generate(a.engine, a.lang)
    elif a.cmd == 'score':
        from .audio_quality_control import score_eval_samples
        score_eval_samples()
