"""Check how the English narrator says Iram and ʿĀd: cut each spoken name out of a sentence and let an ARABIC speech
recogniser (Whisper large-v3-turbo, language=ar) transcribe it. An Arabic-style pronunciation should come back as
إرم / عاد (or close); an anglicised one usually does not. A listener still has the final say.

  python -m audio_engine.name_check FILE.wav [FILE.wav ...]     # sentences that contain "tribe of ʿĀd" / "columned Iram" / "that Iram"
"""
import sys, json, re
import numpy as np
from .common import WORK, strip_diacritics
from .audio_quality_control import load16, SR, transcribe

ANCHORS = {'ʿĀd': [('tribe', 'of'), ('people', 'of'), ('son', 'of'), ('story', 'of')], 'Iram': [('columned',), ('called',), ('found',), ('name',), ('that',), ('is',)]}


def words_en(x):
    import whisper, torch
    torch.set_num_threads(4)
    m = whisper.load_model(str(WORK / 'models/whisper/small.en.pt'))
    r = m.transcribe(x, language='en', word_timestamps=True, fp16=False, condition_on_previous_text=False)
    return [{'w': re.sub(r'[^a-z\-]', '', w['word'].lower()), 's': w['start'], 'e': w['end']} for s in r['segments'] for w in s['words']]


def cut_after(ws, anchor):
    for i in range(len(ws) - len(anchor)):
        if all(ws[i + k]['w'].endswith(a) for k, a in enumerate(anchor)) and i + len(anchor) < len(ws):
            return ws[i + len(anchor)]
    return None


def check(path):
    x = load16(path); ws = words_en(x); out = []
    for name, anchors in ANCHORS.items():
        for a in anchors:
            w = cut_after(ws, a)
            if not w: continue
            seg = x[max(0, int((w['s'] - 0.06) * SR)):int((w['e'] + 0.08) * SR)]
            if len(seg) < 0.15 * SR: continue
            seg = np.concatenate([np.zeros(int(0.3 * SR), np.float32), seg, np.zeros(int(0.3 * SR), np.float32)])
            ar = transcribe(seg, 'ar').strip()
            a_ = strip_diacritics(ar).replace(' ', '')
            ok = {'ʿĀd': 'عاد', 'Iram': 'ارم'}[name] in a_
            near = bool(re.search({'ʿĀd': '[عا]ا?د', 'Iram': 'ا?را?م'}[name], a_))
            out.append({'file': str(path).split('/')[-1], 'name': name, 'after': ' '.join(a), 'english_asr': w['w'], 'arabic_asr': ar, 'arabic_match': ok, 'near': near})
            break
    return out


if __name__ == '__main__':
    res = [r for p in sys.argv[1:] for r in check(p)]
    for r in res: print(json.dumps(r, ensure_ascii=False))
    print(json.dumps({'arabic_matches': sum(r['arabic_match'] for r in res), 'checked': len(res)}))
