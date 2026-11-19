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
        key = it['sentence_key']
        if timings and timings[-1]['key'] == key:
            timings[-1]['end'] = round(t + len(w) / sr, 3)
        else:
            timings.append({'key': key, 'i': len(timings), 'lang': it['lang'], 'profile': it['profile'], 'engine': it['engine'],
                            'display': it['display'], 'tts': it['sentence_tts'], 'start': round(t, 3), 'end': round(t + len(w) / sr, 3)})
        parts.append(w); t += len(w) / sr
        gap = pause_after(it, nxt, cfg)
        if gap: parts.append(np.zeros(int(sr * gap), np.float32)); t += gap
    # no per-segment peak gain: it would make segment levels uneven. Segments are stored as 32-bit float, and the
    # mix stage (scripts/editing/edit.py: build_audio) applies one gentle compressor and limiter to the whole stem.
    y = np.concatenate(parts).astype(np.float32)
    for tm in timings: tm.pop('key')
    return y, timings
