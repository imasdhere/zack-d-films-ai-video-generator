"""Language routing: screenplay segment -> ordered parts, each with language, voice profile and content category.

A segment in screenplay/script.yaml may carry `arabic_quotes`, e.g.
  arabic_quotes:
    - text: "ولا يعلم بناء كان لهم بالعماد بخبر صحيح"      # verbatim, as on the on-screen card
      tts: "وَلَا يُعْلَمُ بِنَاءٌ كَانَ لَهُمْ بِالْعِمَادِ بِخَبَرٍ صَحِيحٍ"  # pronunciation aid (vowel marks only)
      after_sentence: 0            # -1 = before the English text; n = after English sentence n; 'end'
      kind: classical | hadith
      source: "al-Ṭabarī, Jāmiʿ al-Bayān, on Q 89:7"
Routing rules (configuration/voice_config.yaml: routing):
  * the share of Arabic letters decides the language; anything between the two thresholds is flagged for review;
  * a declared language that disagrees with the detected one is flagged, never silently re-routed;
  * any Arabic part with >= n consecutive words found in the Quran goes to the Quranic workflow, is kept out of the
    mix and is never approved automatically.
"""
import yaml
from .common import ROOT, config, script_ratio, strip_diacritics
from . import quranic_validator as QV
from .narration_chunker import sentences


def lexicon(engine):
    lx = yaml.safe_load(open(ROOT / 'configuration/pronunciation_lexicon.yaml', encoding='utf-8'))
    return lx.get(engine) or lx['qwen3']


def tts_text_en(display, engine):
    t = display.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    lx = lexicon(engine)
    for k in sorted(lx, key=len, reverse=True): t = t.replace(k, lx[k])
    return ' '.join(t.replace('"', '').split())


def detect(text):
    r = config()['routing']; x = script_ratio(text)
    if x >= r['arabic_ratio_arabic']: return 'ar', x
    if x <= r['arabic_ratio_english']: return 'en', x
    return 'uncertain', x


def route_segment(seg, chapter):
    """Return the ordered parts of one segment."""
    cfg = config(); n = cfg['routing']['quranic_ngram']
    en = sentences(seg['text'], 'en'); quotes = seg.get('arabic_quotes', [])
    slots = {}
    for q in quotes:
        pos = q.get('after_sentence', 'end')
        pos = len(en) - 1 if pos == 'end' else int(pos)
        slots.setdefault(pos, []).append(q)
    parts = []

    def add_ar(q):
        lang, ratio = detect(q['text']); hits = QV.scan(q['text'], n)
        flags = []
        if lang != 'ar': flags.append(f'language check: detected {lang} ({ratio:.2f}) for a declared Arabic quotation')
        if strip_diacritics(q.get('tts', q['text'])).split() != strip_diacritics(q['text']).split():
            flags.append('TTS form differs from the display text in letters (only vowel marks may be added)')
        cat = 'quranic' if hits else q.get('kind', 'classical')
        parts.append({'lang': 'ar', 'profile': 'quranic' if hits else 'arabic', 'category': cat, 'display': q['text'],
                      'tts': q.get('tts', q['text']), 'source': q.get('source', ''), 'quranic_matches': hits, 'flags': flags,
                      'include_in_mix': not hits, 'approval': 'requires qualified review' if hits else
                      ('pending human review (religious text)' if cat == 'hadith' else 'pending Arabic language review')})

    for q in slots.get(-1, []): add_ar(q)
    for i, s in enumerate(en):
        lang, ratio = detect(s)
        flags = [] if lang == 'en' else [f'language check: detected {lang} ({ratio:.2f}) in English narration']
        parts.append({'lang': 'en', 'profile': 'english', 'category': 'narration', 'display': s, 'flags': flags,
                      'include_in_mix': True, 'approval': 'pending listening review', 'sentence_index': i})
        for q in slots.get(i, []): add_ar(q)
    return parts
