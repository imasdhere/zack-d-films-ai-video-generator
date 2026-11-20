"""Post-processing of generated chunks: resample, rumble high-pass, edge fades, joins with planned pauses, and
loudness matching per language within a segment. No pitch change, no time stretch, no heavy compression."""
import numpy as np
from .common import config, ffilter, lufs, peak_db

PAUSE = {'sentence': None, 'clause': 0.25}


def load_chunk(path, sr_out):
    import soundfile as sf
    from scipy.signal import resample_poly
    w, sr = sf.read(path, dtype='float32')
    if w.ndim > 1: w = w.mean(1)
    if sr != sr_out:
        from math import gcd
        g = gcd(sr, sr_out); w = resample_poly(w, sr_out // g, sr // g).astype(np.float32)
    return w


def fade_edges(w, sr, ms):
    n = min(int(sr * ms / 1000), len(w) // 4)
    if n > 1:
        w = w.copy(); w[:n] *= np.linspace(0, 1, n, dtype=np.float32); w[-n:] *= np.linspace(1, 0, n, dtype=np.float32)
    return w


def pause_after(item, nxt, cfg):
    c = cfg['chunking']
    if nxt is None: return 0.0
    if item['lang'] != nxt['lang']: return c['part_pause_s']              # around an Arabic quotation
    if item['pause_after'] == 'clause': return PAUSE['clause']
    return c['sentence_pause_s'] * (c['question_pause_factor'] if item['text'].rstrip().endswith(('?', '؟')) else 1.0)


def sentence_bounds(w, sr, texts):
    """Start and end (s) of each sentence inside one chunk: the expected split points (by text length) move to the
    middle of the nearest pause (at least 90 ms quiet) within 0.9 s. One sentence -> the whole chunk."""
    d = len(w) / sr
    if len(texts) == 1: return [(0.0, d)]
    hop = int(0.01 * sr); e = np.array([np.sqrt(np.mean(w[i:i + 2 * hop] ** 2)) for i in range(0, max(1, len(w) - 2 * hop), hop)])
    quiet = 20 * np.log10(e + 1e-9) < 20 * np.log10(np.percentile(e, 95) + 1e-9) - 30
    runs, s0 = [], None
    for i, q in enumerate(np.append(quiet, False)):
        if q and s0 is None: s0 = i
        if not q and s0 is not None:
            if i - s0 >= 9: runs.append(((s0 + i) / 2 * 0.01, s0 * 0.01, i * 0.01))
            s0 = None
    L = np.cumsum([len(x) for x in texts]); cuts = []
    for k in range(len(texts) - 1):
        exp = d * L[k] / L[-1]; near = [r for r in runs if abs(r[0] - exp) < 0.9 and (not cuts or r[0] > cuts[-1][0] + 0.3)]
        cuts.append(min(near, key=lambda r: abs(r[0] - exp)) if near else (exp, exp, exp))
    out, a = [], 0.0
    for c in cuts: out.append((a, c[1])); a = c[2]
    out.append((a, d))
    return out


def assemble_segment(items, sr=None):
    """items: ordered chunk dicts with 'wav', 'lang', 'pause_after', 'text', 'display', 'sentence_key'.
    Returns (audio, sentence timings)."""
    cfg = config(); pp = cfg['postprocess']; sr = sr or pp['sample_rate']
    ws = []
    for it in items:
        w = load_chunk(it['wav'], sr)
        w = ffilter(w, sr, f"highpass=f={pp['highpass_hz']}:poles=2")
        ws.append(fade_edges(w, sr, pp['edge_fade_ms']))
    # loudness: each language's material in the segment goes to the same target, so both narrators sit at one level
    for lang in {it['lang'] for it in items}:
        idx = [i for i, it in enumerate(items) if it['lang'] == lang]
        joined = np.concatenate([ws[i] for i in idx])
        g = 10 ** ((pp['segment_lufs'] - lufs(joined, sr)) / 20)
        for i in idx: ws[i] = ws[i] * g
    parts, timings, t = [], [], 0.0
    for k, (it, w) in enumerate(zip(items, ws)):
        nxt = items[k + 1] if k + 1 < len(items) else None
        sents = it.get('sentences') or [{'key': it['sentence_key'], 'display': it['display'], 'tts': it['sentence_tts']}]
        bounds = sentence_bounds(w, sr, [s_['tts'] for s_ in sents])
        for s_, (a_, b_) in zip(sents, bounds):
            if timings and timings[-1]['key'] == s_['key']:
                timings[-1]['end'] = round(t + b_, 3)
            else:
                timings.append({'key': s_['key'], 'i': len(timings), 'lang': it['lang'], 'profile': it['profile'], 'engine': it['engine'],
                                'display': s_['display'], 'tts': s_['tts'], 'start': round(t + a_, 3), 'end': round(t + b_, 3)})
        parts.append(w); t += len(w) / sr
        gap = pause_after(it, nxt, cfg)
        if gap: parts.append(np.zeros(int(sr * gap), np.float32)); t += gap
    # no per-segment peak gain: it would make segment levels uneven. Segments are stored as 32-bit float, and the
    # mix stage (scripts/editing/edit.py: build_audio) applies one gentle compressor and limiter to the whole stem.
    y = np.concatenate(parts).astype(np.float32)
    for tm in timings: tm.pop('key')
    return y, timings
