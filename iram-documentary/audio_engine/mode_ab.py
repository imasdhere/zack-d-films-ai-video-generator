"""A/B test of VoxCPM2 cloning modes on sentence-initial words (decision record for the production settings).

  python -m audio_engine.mode_ab
Modes: 'ultimate' (reference clip as continuation prompt + transcript, and as isolated reference) and 'reference'
(isolated reference only). Output is not trimmed, so onsets can be inspected. Results: workflows/tts/eval/voxcpm_mode_ab.json
"""
import json
from .common import ROOT, WORK, config
from . import engines
from .audio_quality_control import transcribe, load16, error_rates, norm_en, norm_ar

TEXTS = {'en': ['And he added a sentence that cuts to the heart of this mystery.', 'Some said Iram was a city: Alexandria, according to one early authority; Damascus, according to another.',
                'A few words in a sacred text have outlived empires, maps and explorers.', 'Aad were people of poles: travellers, moving with the rains and the pasture.'],
         'ar': ['ذكرها القرآنُ الكريمُ مرّةً واحدة، مقرونةً بقومِ عاد، الذين أُرسِلَ إليهم النبيُّ هود.', 'وفي عامِ ألفٍ وتسعمئةٍ واثنين وتسعين، كشفت بعثةٌ أثريةٌ في شِصْر.',
                'فَهُمْ قَبِيلَةٌ وَأُمَّةٌ مِنَ الْأُمَمْ', 'نُصِرْتُ بِالصَّبَا، وَأُهْلِكَتْ عَادٌ بِالدَّبُورْ']}


def main():
    cfg = config(); jobs = []; out = WORK / 'ab'; out.mkdir(exist_ok=True)
    for lang, prof in (('en', 'english'), ('ar', 'arabic')):
        p = cfg['voice_profiles'][prof]
        for i, t in enumerate(TEXTS[lang]):
            for mode in ('ultimate', 'reference'):
                jobs.append({'id': f'{lang}{i}_{mode}', 'text': t, 'lang': lang, 'out': str(out / f'{lang}{i}_{mode}.wav'), 'trim': False,
                             'ref_wav': str(ROOT / p['reference']), 'ref_text': (ROOT / p['transcript']).read_text().strip(), 'seed': 99 + i,
                             'params': {'mode': mode}})
    engines.get('voxcpm').run(jobs, log_path=WORK / 'logs' / 'voxcpm_mode_ab.log', force=True)
    res = []
    for j in jobs:
        hyp = transcribe(load16(j['out']), j['lang']); wer, cer = error_rates(j['text'], hyp, j['lang'])
        n = norm_ar if j['lang'] == 'ar' else norm_en; r, h = n(j['text']), n(hyp)
        res.append({'id': j['id'], 'first_word_ok': bool(h) and r[0] == h[0], 'wer': wer, 'cer': cer, 'asr': hyp})
        print(json.dumps(res[-1], ensure_ascii=False), flush=True)
    summ = {m: {'first_word_ok': sum(r['first_word_ok'] for r in res if r['id'].endswith(m)), 'n': sum(1 for r in res if r['id'].endswith(m)),
                'mean_cer': round(sum(r['cer'] for r in res if r['id'].endswith(m)) / max(1, sum(1 for r in res if r['id'].endswith(m))), 3)} for m in ('ultimate', 'reference')}
    json.dump({'summary': summ, 'results': res}, open(ROOT / 'workflows/tts/eval/voxcpm_mode_ab.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(summ))


if __name__ == '__main__':
    main()
