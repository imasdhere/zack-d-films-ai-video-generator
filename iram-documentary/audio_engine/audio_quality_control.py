"""Objective audio QA (runs in venvs/ml): ASR intelligibility, speaker similarity, pitch, pace, signal quality.

Automated scores are supporting evidence only. A speaker-verification cosine does not prove that a clone preserves
a person's identity, and no metric here replaces a human listening test.
"""
import json, re, functools, pathlib
import numpy as np
from .common import ROOT, WORK, config, read_audio, strip_diacritics, peak_db, lufs, frame_db

SR = 16000


# ------------------------------------------------------------------ models (loaded once)
@functools.lru_cache(None)
def _asr():
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    torch.set_num_threads(4)
    mp = WORK / 'models/whisper-large-v3-turbo'
    m = AutoModelForSpeechSeq2Seq.from_pretrained(mp, dtype=torch.float32); p = AutoProcessor.from_pretrained(mp)
    return pipeline('automatic-speech-recognition', model=m, tokenizer=p.tokenizer, feature_extractor=p.feature_extractor)


@functools.lru_cache(None)
def _sv():
    from transformers import AutoFeatureExtractor, WavLMForXVector
    mp = WORK / 'models/wavlm-base-plus-sv'
    return AutoFeatureExtractor.from_pretrained(mp), WavLMForXVector.from_pretrained(mp).eval()


@functools.lru_cache(None)
def _squim():
    import torchaudio
    return torchaudio.pipelines.SQUIM_OBJECTIVE.get_model().eval()


def load16(path):
    x, _ = read_audio(path, sr=SR); return x


def pieces(x, max_s=28.0):
    """Split at pauses into pieces of at most max_s seconds."""
    db = frame_db(x, SR, 0.05, 0.01); quiet = np.where(db < np.percentile(db, 20) + 6)[0] * 0.01
    out, a = [], 0.0; dur = len(x) / SR
    while dur - a > max_s:
        cands = quiet[(quiet > a + max_s * 0.5) & (quiet < a + max_s)]
        b = float(cands[-1]) if len(cands) else a + max_s
        out.append((a, b)); a = b
    out.append((a, dur))
    return [x[int(a * SR):int(b * SR)] for a, b in out if b - a > 0.3]


def transcribe(x, lang):
    import torch
    asr = _asr(); txt = []
    for p in pieces(x):
        with torch.inference_mode():
            r = asr(p, generate_kwargs={'language': 'arabic' if lang == 'ar' else 'english', 'task': 'transcribe', 'num_beams': 1})
        txt.append(r['text'].strip())
    return ' '.join(txt)


def embed(x):
    import torch
    fe, m = _sv(); embs = []
    for p in pieces(x, 10.0):
        with torch.inference_mode():
            e = m(**fe(p, sampling_rate=SR, return_tensors='pt')).embeddings[0]
        embs.append(torch.nn.functional.normalize(e, dim=-1).numpy())
    e = np.mean(embs, 0); return e / np.linalg.norm(e)


def cos(a, b): return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def squim(x):
    import torch
    m = _squim(); vals = []
    for p in pieces(x, 10.0):
        with torch.inference_mode():
            stoi, pesq, sisdr = m(torch.from_numpy(p)[None])
        vals.append((float(stoi), float(pesq), float(sisdr)))
    v = np.mean(vals, 0)
    return {'stoi_est': round(v[0], 3), 'pesq_est': round(v[1], 2), 'si_sdr_est_db': round(v[2], 1)}


def pitch(x):
    import librosa
    f0, vf, _ = librosa.pyin(x, fmin=50, fmax=400, sr=SR, frame_length=1024, hop_length=160)
    v = f0[vf]
    if len(v) < 20: return {'f0_median_hz': None}
    st = 12 * np.log2(v / 55.0)
    return {'f0_median_hz': round(float(np.median(v)), 1), 'f0_sd_semitones': round(float(st.std()), 2)}


# ------------------------------------------------------------------ text normalisation and error rates
ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = 'zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()


def num_words(n):
    n = int(n)
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ('' if n % 10 == 0 else ' ' + ONES[n % 10])
    if n < 1000: return ONES[n // 100] + ' hundred' + ('' if n % 100 == 0 else ' and ' + num_words(n % 100))
    if n < 10000 and 1100 <= n <= 1999:                 # years: nineteen ninety-two (the screenplay's convention)
        hi, lo = divmod(n, 100); return num_words(hi) + ' ' + (num_words(lo) if lo >= 10 else ('oh ' + num_words(lo) if lo else 'hundred'))
    if n < 1000000:                                       # 2004 -> two thousand and four; 650000 -> six hundred and fifty thousand
        hi, lo = divmod(n, 1000)
        return num_words(hi) + ' thousand' + ('' if lo == 0 else (' and ' if lo < 100 else ' ') + num_words(lo))
    return str(n)


def norm_en(t):
    t = t.lower().replace('’', "'")
    for a_, b_ in (('for ever', 'forever'), ('watersprings', 'water springs'), ('haply', 'happily')): t = t.replace(a_, b_)
    t = t.replace('-', ' ')
    t = re.sub(r'(\d),(\d{3})', r'\1\2', t)
    t = re.sub(r'\d+', lambda m: num_words(m.group()), t)
    t = strip_latin_diacritics(t)
    t = re.sub(r"[^a-z' ]", ' ', t).replace("'", '')
    return [UKUS.get(w, w) for w in t.split()]


# British and American spellings count as the same word (the screenplay is British, Whisper writes American)
UKUS = {'travellers': 'travelers', 'traveller': 'traveler', 'travelled': 'traveled', 'kilometres': 'kilometers', 'kilometre': 'kilometer',
        'metres': 'meters', 'metre': 'meter', 'centre': 'center', 'centres': 'centers', 'colour': 'color', 'colours': 'colors',
        'honour': 'honor', 'grey': 'gray', 'favour': 'favor', 'labelled': 'labeled', 'theatre': 'theater', 'mould': 'mold',
        'harbour': 'harbor', 'harbours': 'harbors', 'neighbouring': 'neighboring', 'civilisation': 'civilization', 'recognised': 'recognized',
        'organised': 'organized', 'realised': 'realized', 'analysed': 'analyzed', 'sceptical': 'skeptical', 'defence': 'defense'}


def strip_latin_diacritics(t):
    import unicodedata
    t = t.replace('ʿ', '').replace('ʾ', '')
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')


def norm_ar(t):
    return strip_diacritics(t).split()


def edit_distance(a, b):
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = d[j]; d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1])); prev = cur
    return d[len(b)]


def error_rates(ref, hyp, lang):
    r = norm_ar(ref) if lang == 'ar' else norm_en(ref); h = norm_ar(hyp) if lang == 'ar' else norm_en(hyp)
    wer = edit_distance(r, h) / max(1, len(r))
    rc, hc = ''.join(r), ''.join(h)
    cer = edit_distance(list(rc), list(hc)) / max(1, len(rc))
    return round(wer, 3), round(cer, 3)


# ------------------------------------------------------------------ production chunk QA
@functools.lru_cache(None)
def _ref_emb(profile):
    p = config()['voice_profiles']['arabic' if profile == 'quranic' else profile]
    return embed(load16(ROOT / p['reference']))


@functools.lru_cache(None)
def _names():
    import yaml
    lx = yaml.safe_load(open(ROOT / 'configuration/pronunciation_lexicon.yaml', encoding='utf-8'))
    toks = set()
    for d in lx.values():
        for k, v in d.items(): toks |= set(norm_en(k)) | set(norm_en(v))
    common = {'the', 'and', 'of', 'a', 'an', 'in', 'on', 'to', 'is', 'was', 'were', 'his', 'her', 'their', 'son', 'city', 'name'}
    # names that the screenplay writes in plain English letters (not in the lexicon)
    toks |= set(EXTRA_NAMES)
    return {t for t in toks if t not in common}


EXTRA_NAMES = ['shisr', 'zarins', 'ubar', 'wubar', 'dhofar', 'philby', 'wabar', 'clapp', 'blom', 'elachi', 'hedges', 'fiennes', 'edgell', 'jallad',
               'moscha', 'sumhuram', 'khor', 'rori', 'salalah', 'ramm', 'rum', 'allat', 'nabataean', 'ptolemy', 'periplus', 'erythraean',
               'boswellia', 'sacra', 'iram', 'iobaritae', 'pickthall', 'marmaduke', 'saheeh', 'muhammad', 'jabal', 'wadi', 'rashid', 'bedouin', 'sahib']


def _align(r, h):
    """Word alignment (Levenshtein with backtrace): list of (op, ref_index or None)."""
    n, m = len(r), len(h); D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): D[i][0] = i
    for j in range(m + 1): D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i][j] = min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + (r[i - 1] != h[j - 1]))
    ops, i, j = [], n, m
    while i or j:
        if i and j and D[i][j] == D[i - 1][j - 1] + (r[i - 1] != h[j - 1]):
            ops.append(('ok' if r[i - 1] == h[j - 1] else 'sub', i - 1)); i -= 1; j -= 1
        elif i and D[i][j] == D[i - 1][j] + 1: ops.append(('del', i - 1)); i -= 1
        else: ops.append(('ins', i - 1 if i else None)); j -= 1
    return ops[::-1]


def wer_without_names(ref, hyp):
    """WER that ignores errors on transliterated names (Whisper spells them in many ways, and may split one name into
    several words). Substitutions and deletions of a name word, and insertions next to a name word, are not counted.
    Names are checked by listening instead."""
    names = _names(); r = norm_en(ref); h = norm_en(hyp)
    isname = lambda i: i is not None and 0 <= i < len(r) and r[i] in names
    err = 0
    for op, i in _align(r, h):
        if op in ('sub', 'del') and not isname(i): err += 1
        elif op == 'ins' and not (isname(i) or isname((i if i is not None else -1) + 1)): err += 1
    return round(err / max(1, len(r)), 3)


def chunk_qa(item, cfg):
    q = cfg['qa']; x = load16(item['wav']); d = len(x) / SR; notes = []
    hyp = transcribe(x, item['lang'])
    if item['lang'] == 'en':
        ref_t = re.sub(r'[\u0600-\u06FF]+', 'Iram', item['text'])   # Arabic-script names = name tokens
        err = wer_without_names(ref_t, hyp); item = {**item, 'text': ref_t}; raw, _ = error_rates(item['text'], hyp, 'en'); lim = q['max_wer_en']
    else:
        raw, err = error_rates(item['text'], hyp, 'ar'); lim = q['max_cer_ar']
    sim = round(cos(embed(x), _ref_emb(item['profile'])), 3) if d >= 1.5 else None
    exp = len(item['text']) / (14.0 if item['lang'] == 'en' else 11.0)
    if err > lim: notes.append(f'ASR error {err} > {lim}')
    if sim is not None and sim < q['min_speaker_similarity']: notes.append(f'speaker similarity {sim} < {q["min_speaker_similarity"]}')
    if not 0.45 * exp < d < 2.3 * exp + 1.0: notes.append(f'duration {d:.1f}s vs expected {exp:.1f}s')
    full, _ = read_audio(item['wav'])
    if (abs(full) >= 0.999).sum(): notes.append('clipped samples')
    sil, longest = internal_silences(x)
    if sil: notes.append(f'internal silence {longest}s')
    return {'status': 'fail' if notes else 'pass', 'err': err, 'raw_wer': raw, 'similarity': sim, 'asr': hyp, 'duration': round(d, 2), 'notes': notes}


# ------------------------------------------------------------------ evaluation scoring
def internal_silences(x, min_s=1.0):
    db = frame_db(x, SR, 0.05, 0.01); q = db < -45; runs, s = 0, None; longest = 0.0
    for i, v in enumerate(np.append(q, False)):
        if v and s is None: s = i
        if not v and s is not None:
            L = (i - s) * 0.01
            if L >= min_s and s > 0 and i < len(q): runs += 1
            longest = max(longest, L) if s > 0 and i < len(q) else longest; s = None
    return runs, round(longest, 2)


def clamp(v): return int(max(1, min(10, round(v))))


def provisional_scores(m, ref):
    """Metric-derived 1-10 scores. Perceptual criteria without a valid proxy stay None (listening required)."""
    s = {}
    c = m['speaker_similarity']
    s['similarity'] = clamp(5 + (c - 0.80) * 29.4 if c >= 0.80 else 5 - (0.80 - c) * 20)
    s['naturalness'] = None
    err = m['cer'] if m['lang'] == 'ar' else m['wer']
    s['pronunciation'] = clamp(10 - 40 * err)
    s['accent_preservation'] = None
    if m['lang'] == 'en' and ref.get('words_per_minute'):
        s['rhythm_pacing'] = clamp(10 - 12 * abs(np.log2(m['words_per_minute'] / ref['words_per_minute'])))
    else:
        s['rhythm_pacing'] = None     # the Arabic reference is chanted supplication, not narration pace
    if m.get('f0_sd_semitones') and ref.get('f0_sd_semitones'):
        drift = abs(12 * np.log2(m['f0_median_hz'] / ref['f0_median_hz']))
        s['prosody'] = clamp(10 - 8 * abs(np.log2(m['f0_sd_semitones'] / ref['f0_sd_semitones'])) - max(0, drift - 1))
    s['emotional_suitability'] = None
    s['consistency'] = clamp(10 - 60 * m['chunk_similarity_sd'] - 1.5 * m['chunk_f0_median_sd_semitones'])
    s['artefacts'] = clamp(2 * m['squim']['pesq_est'] + 1.5 - 1.0 * m['internal_silences_over_1s'] - (2 if m['clipped_samples'] else 0)
                           - 0.5 * len(m.get('implausible_chunks', [])))
    vals = [v for v in s.values() if v is not None]
    s['overall_provisional'] = round(float(np.mean(vals)), 1)
    return s


def score_eval_samples():
    cfg = config(); res = {'references': {}, 'samples': [], 'notes': 'Automated proxies only; see reports/voice_cloning_evaluation.md'}
    refs = {}
    for lang, key in (('en', 'english'), ('ar', 'arabic')):
        p = cfg['voice_profiles'][key]; x = load16(ROOT / p['reference'])
        meta = json.load(open(ROOT / p['dir'] / 'voice_metadata.json', encoding='utf-8'))
        refs[lang] = {'emb': embed(x), **pitch(x), 'words_per_minute': meta['full_recording'].get('words_per_minute')}
        res['references'][lang] = {k: v for k, v in refs[lang].items() if k != 'emb'}
    res['references']['cross_reference_similarity'] = round(cos(refs['en']['emb'], refs['ar']['emb']), 3)
    for lang, key in (('en', 'english'), ('ar', 'arabic')):
        d = ROOT / cfg['voice_profiles'][key]['dir'] / 'test_samples'
        for f in sorted(d.glob('*_test.wav')):
            info = json.load(open(f.with_suffix('.json'), encoding='utf-8'))
            x = load16(f); hyp = transcribe(x, lang)
            ref_text = info['input_text']
            wer, cer = error_rates(ref_text, hyp, lang)
            chunks = sorted((d / info['engine']).glob(f'{lang}_*.wav'))  # chunk folder = engine label
            cs, cf = [], []
            for c in chunks:
                y = load16(c)
                if len(y) < SR * 1.0: continue
                cs.append(cos(embed(y), refs[lang]['emb'])); pc = pitch(y)
                if pc.get('f0_median_hz'): cf.append(12 * np.log2(pc['f0_median_hz'] / 55))
            sil, longest = internal_silences(x)
            m = {'engine': info['engine'], 'lang': lang, 'file': str(f.relative_to(ROOT)), 'duration_s': round(len(x) / SR, 2),
                 'asr_transcript': hyp, 'wer': wer, 'cer': cer,
                 'speaker_similarity': round(cos(embed(x), refs[lang]['emb']), 3),
                 'similarity_to_other_reference': round(cos(embed(x), refs['ar' if lang == 'en' else 'en']['emb']), 3),
                 'chunk_similarity_mean': round(float(np.mean(cs)), 3), 'chunk_similarity_sd': round(float(np.std(cs)), 3),
                 'chunk_f0_median_sd_semitones': round(float(np.std(cf)), 2), **pitch(x),
                 'words_per_minute': round(60 * len(hyp.split()) / (len(x) / SR), 1),
                 'squim': squim(x), 'clipped_samples': int((np.abs(read_audio(f)[0]) >= 0.999).sum()),
                 'internal_silences_over_1s': sil, 'longest_internal_silence_s': longest, 'peak_dbfs': round(peak_db(x), 2),
                 'generation': {k: info[k] for k in ('chunks', 'audio_s', 'wall_s', 'compute_s_sum_chunks', 'model_load_and_overhead_s', 'real_time_factor',
                                                     'peak_rss_gb', 'cpu_percent_avg', 'retries', 'implausible_chunks', 'params', 'seed_base') if k in info},
                 'implausible_chunks': info.get('implausible_chunks', [])}
            if m.get('f0_median_hz') and refs[lang].get('f0_median_hz'):
                m['f0_shift_vs_reference_semitones'] = round(float(12 * np.log2(m['f0_median_hz'] / refs[lang]['f0_median_hz'])), 2)
            m['scores'] = provisional_scores(m, refs[lang])
            res['samples'].append(m); print(json.dumps({k: m[k] for k in ('engine', 'lang', 'wer', 'cer', 'speaker_similarity', 'scores')}), flush=True)
    json.dump(res, open(ROOT / 'reports/voice_clone_metrics.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    return res
