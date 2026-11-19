"""Pick TTS respellings of recurring Arabic names for one engine and voice.

  python -m audio_engine.pronunciation_probe --engine voxcpm      # writes the engine section of pronunciation_lexicon.yaml

Each candidate spelling is spoken in two carrier sentences with the English reference voice. Whisper large-v3-turbo
then transcribes the result; a candidate scores when the transcript contains the expected word (pattern). This only
ranks candidates. A listener must still confirm the chosen forms.
"""
import argparse, json, re, yaml
from .common import ROOT, WORK, config
from . import engines
from .audio_quality_control import transcribe, load16

# display form -> (accepted transcript pattern, candidate respellings)
TERMS = {
    'Iram': (r'\biram\b|\beram\b', ['Iram', 'Eeram', 'Ee-rahm', 'Irum']),
    'ʿĀd': (r'\b(aad|ad|ahd|aahd)\b', ['Aad', 'Aahd', 'Ahd', 'Aa-d']),
    'al-Ṭabarī': (r'tabar[iy]', ['at-Tabari', 'al-Tabari', 'At Tabaree', 'Tabari']),
    'ʿimād': (r'\bi?mad\b|\bimaad\b|\bemad\b', ['imaad', 'ee-maad', 'imad', 'i-mahd']),
    'Hūd': (r'\bhud\b|\bhood\b|\bhoud\b', ['Hood', 'Hud', 'Hoo-d']),
    'Shisr': (r'\bshis(e)?r\b|\bshisr\b', ['Shisr', 'Shis-ur', 'Shiser']),
}
CARRIERS = ['The name {} appears in the old commentaries.', 'Scholars still argue about {}, and about what it meant.']


def probe(engine):
    cfg = config(); p = cfg['voice_profiles']['english']; out = WORK / 'probe' / engine; out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for term, (_, cands) in TERMS.items():
        for ci, c in enumerate(cands):
            for k, car in enumerate(CARRIERS):
                jobs.append({'id': f'{term}|{ci}|{k}', 'text': car.format(c), 'lang': 'en', 'out': str(out / f'{abs(hash(term)) % 10**6}_{ci}_{k}.wav'),
                             'ref_wav': str(ROOT / p['reference']), 'ref_text': (ROOT / p['transcript']).read_text().strip(), 'seed': 777 + k})
    engines.get(engine).run(jobs, log_path=WORK / 'logs' / f'probe_{engine}.log')
    res = {}
    for j in jobs:
        term, ci, k = j['id'].split('|'); pat = TERMS[term][0]
        try: hyp = transcribe(load16(j['out']), 'en')
        except Exception as e: hyp = f'<error {e}>'
        hit = bool(re.search(pat, hyp.lower().replace('-', ' ')))
        res.setdefault(term, {}).setdefault(TERMS[term][1][int(ci)], []).append({'hit': hit, 'asr': hyp})
    choice = {}
    for term, d in res.items():
        best = max(d, key=lambda c: (sum(x['hit'] for x in d[c]), -TERMS[term][1].index(c)))
        choice[term] = best
    json.dump({'results': res, 'choice': choice}, open(ROOT / f'workflows/tts/eval/pronunciation_probe_{engine}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(choice, ensure_ascii=False))
    return choice


def write_lexicon(engine, choice):
    """Engine section = version-1 lexicon with the probed names replaced (longer phrases keep their structure)."""
    lp = ROOT / 'configuration/pronunciation_lexicon.yaml'; lx = yaml.safe_load(open(lp, encoding='utf-8'))
    base = dict(lx['qwen3']); new = {}
    rep = {'Aad': choice.get('ʿĀd'), 'at-Tabari': choice.get('al-Ṭabarī'), 'imaad': choice.get('ʿimād'), 'Hood': choice.get('Hūd')}
    for k, v in base.items():
        for old, nw in rep.items():
            if not nw: continue
            # whole words only (never inside another name), keeping the capital of the original word
            v = re.sub(rf'(?<![A-Za-z]){re.escape(old)}(?![A-Za-z])',
                       lambda m: nw[0].upper() + nw[1:] if m.group()[0].isupper() else nw, v, flags=re.I)
        new[k] = v
    if 'ʾrm' in new and choice.get('Iram'): new['ʾrm'] = choice['Iram']
    if choice.get('Iram') and choice['Iram'] != 'Iram': new = {'Iram': choice['Iram'], **new}
    if choice.get('Shisr') and choice['Shisr'] != 'Shisr': new = {'Shisr': choice['Shisr'], **new}
    text = open(lp, encoding='utf-8').read()
    block = f"{engine}:   # chosen by audio_engine/pronunciation_probe.py (see workflows/tts/eval/pronunciation_probe_{engine}.json)\n" + \
            ''.join(f'  "{k}": "{v}"\n' for k, v in new.items())
    text = re.sub(rf'(?ms)^{engine}:.*?(?=^\S|\Z)', '', text).rstrip() + '\n' + block
    lp.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--engine', default='voxcpm'); a = ap.parse_args()
    write_lexicon(a.engine, probe(a.engine))
