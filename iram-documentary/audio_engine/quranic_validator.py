"""Quranic text registry and checks.

  python -m audio_engine.quranic_validator build      # research/quranic_verse_registry.csv (+ quran.com cross-check)
  python -m audio_engine.quranic_validator scan TEXT  # report Quranic word sequences inside any Arabic text

Rules: the Arabic of a verse always comes verbatim from the Tanzil files in research/raw_sources/quran/ and is never
edited, normalised or respelled for a TTS engine. Matching uses a letters-only form for search, never for output.
"""
import csv, json, sys, time, functools, urllib.request
from .common import ROOT, strip_diacritics

UTHMANI = ROOT / 'research/raw_sources/quran/quran-uthmani.txt'
SIMPLE = ROOT / 'research/raw_sources/quran/quran-simple.txt'
REGISTRY = ROOT / 'research/quranic_verse_registry.csv'

# Every verse the film quotes (Arabic on screen or English translation spoken) or cites. Claim IDs from the matrix.
FILM_VERSES = [
    ((89, 6), 'Q01', 'arabic_on_screen+english_spoken', '1.04'), ((89, 7), 'Q01;Q02;Q13', 'arabic_on_screen+english_spoken', '1.04;3.01'),
    ((89, 8), 'Q01;Q13', 'arabic_on_screen+english_spoken', '1.04'),
    ((7, 65), 'Q05', 'cited', '2.01'), ((11, 50), 'Q05', 'cited', '2.01'), ((26, 124), 'Q05', 'cited', '2.01'), ((46, 21), 'Q05;Q11', 'english_spoken', '2.06'),
    ((7, 69), 'Q06;Q08', 'english_spoken', '2.03'), ((26, 128), 'Q09', 'english_spoken', '2.04'), ((26, 129), 'Q09', 'english_spoken', '2.04'),
    ((26, 133), 'Q07', 'english_spoken', '2.03'), ((26, 134), 'Q07', 'english_spoken', '2.03'), ((41, 15), 'Q10', 'english_spoken', '2.05'),
    ((46, 24), 'Q14', 'arabic_on_screen+english_spoken', '5.02'), ((46, 25), 'Q14', 'english_spoken', '5.02'),
    ((41, 16), 'Q15', 'cited', '5.03'), ((54, 19), 'Q15', 'cited', '5.03'), ((69, 6), 'Q15', 'cited', '5.03'), ((51, 41), 'Q15', 'cited', '5.03'),
    ((69, 7), 'Q16', 'english_spoken', '5.03'), ((7, 72), 'Q16', 'cited', '5.03'), ((11, 58), 'Q16', 'cited', '5.03'),
]


def _load(path):
    d = {}
    for line in open(path, encoding='utf-8'):
        p = line.rstrip('\n').split('|')
        if len(p) == 3 and p[0].isdigit(): d[(int(p[0]), int(p[1]))] = p[2]
    return d


@functools.lru_cache(None)
def uthmani(): return _load(UTHMANI)


@functools.lru_cache(None)
def simple(): return _load(SIMPLE)


def verse(s, a, script='uthmani'):
    """Exact verse text from Tanzil. Raises KeyError for a reference that does not exist."""
    return (uthmani() if script == 'uthmani' else simple())[(s, a)]


def letters(t): return strip_diacritics(t).split()


@functools.lru_cache(None)
def ngram_index(n):
    idx = {}
    for (s, a), t in simple().items():
        w = letters(t)
        for i in range(len(w) - n + 1): idx.setdefault(tuple(w[i:i + n]), set()).add((s, a))
    return idx


def scan(text, n=3):
    """Return Quranic matches of >= n consecutive words inside an Arabic text: [{'words', 'verses'}]."""
    w = letters(text); idx = ngram_index(n); hits = []; i = 0
    while i <= len(w) - n:
        k = tuple(w[i:i + n])
        if k in idx:
            j = i + n; vs = set(idx[k])
            while j < len(w) and tuple(w[j - n + 1:j + 1]) in idx: vs &= idx[tuple(w[j - n + 1:j + 1])] or vs; j += 1
            hits.append({'words': ' '.join(w[i:j]), 'verses': sorted(f'{s}:{a}' for s, a in vs)[:6]}); i = j
        else: i += 1
    return hits


def quran_com(s, a):
    url = f'https://api.quran.com/api/v4/quran/verses/uthmani?verse_key={s}:{a}'
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'iram-doc-verifier'}), timeout=30) as r:
        return json.loads(r.read())['verses'][0]['text_uthmani']


def build():
    rows = []; old = {}
    if REGISTRY.exists():
        old = {r['verse_key']: r for r in csv.DictReader(open(REGISTRY, encoding='utf-8'))}
    for (s, a), claims, use, segs in FILM_VERSES:
        key = f'{s}:{a}'; u = verse(s, a); sm = verse(s, a, 'simple')
        try:
            q = quran_com(s, a); same = letters(q) == letters(u); src2 = 'quran.com API v4 (text_uthmani)'
        except Exception as e:
            q, same, src2 = '', None, f'quran.com unavailable: {e!r}'[:80]
        time.sleep(0.3)
        prev = old.get(key, {})
        rows.append({'verse_key': key, 'surah': s, 'verse': a, 'arabic_uthmani_exact': u, 'arabic_diacritized_simple': sm,
                     'verified_source': 'Tanzil Quran Text (Uthmani 1.1 and Simple), tanzil.net; verbatim copies in research/raw_sources/quran/',
                     'cross_check': src2, 'cross_check_letters_match': same, 'claims': claims, 'use_in_film': use, 'segments': segs,
                     'audio_asset_path': prev.get('audio_asset_path', ''), 'audio_engine': prev.get('audio_engine', ''),
                     'asr_check_cer': prev.get('asr_check_cer', ''),
                     'verification_status': 'text verified (Tanzil = quran.com letters)' if same else 'CHECK: sources differ or unavailable',
                     'human_review_status': prev.get('human_review_status', 'not reviewed: needs a qualified reciter or tajwid teacher'),
                     'approved_for_publication': prev.get('approved_for_publication', 'no')})
    with open(REGISTRY, 'w', encoding='utf-8', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    print(f'{len(rows)} verses; letters match quran.com: {sum(1 for r in rows if r["cross_check_letters_match"])}/{len(rows)}')
    return rows


def update_audio(key, path, engine, cer):
    rows = list(csv.DictReader(open(REGISTRY, encoding='utf-8')))
    for r in rows:
        if r['verse_key'] == key:
            r.update({'audio_asset_path': path, 'audio_engine': engine, 'asr_check_cer': cer})
    with open(REGISTRY, 'w', encoding='utf-8', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)


def approved(key):
    for r in csv.DictReader(open(REGISTRY, encoding='utf-8')):
        if r['verse_key'] == key: return r['approved_for_publication'].strip().lower() == 'yes'
    return False


if __name__ == '__main__':
    if sys.argv[1] == 'build': build()
    elif sys.argv[1] == 'scan': print(json.dumps(scan(' '.join(sys.argv[2:])), ensure_ascii=False, indent=1))
