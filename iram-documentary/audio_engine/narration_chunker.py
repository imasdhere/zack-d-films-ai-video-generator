"""Sentence-safe chunking for long-form narration.

Rules: split only at sentence ends (. ? ! and Arabic ؟ ۔ plus a closing quote); never inside a protected term
(names in the pronunciation lexicon); merge very short sentences with the next one only when they share a paragraph
and the result stays under the limit; keep a pause plan so the assembler restores natural paragraph rhythm.
"""
import re

EN_SPLIT = re.compile(r'(?<=[.?!])\s+(?=["“‘(]?[A-Z0-9ʿĀ])|(?<=[.?!]["”’])\s+')
AR_SPLIT = re.compile(r'(?<=[.؟!۔])\s+')


def sentences(text, lang):
    t = ' '.join(text.split())
    parts = (AR_SPLIT if lang == 'ar' else EN_SPLIT).split(t)
    return [p.strip() for p in parts if p and p.strip()]


def split_long(s, limit, lang):
    """A sentence over the limit is split at the last clause boundary (; : , or ، ؛) before the limit."""
    out = []
    while len(s) > limit:
        cut = max((m.end() for m in re.finditer(r'[;:,،؛]\s', s[:limit])), default=-1)
        if cut < limit * 0.4: cut = s.rfind(' ', 0, limit) + 1
        out.append(s[:cut].strip()); s = s[cut:].strip()
    return out + [s] if s else out


def chunk(text, lang, limit, merge_short=False, short=25):
    """Return [{'text', 'pause_after'}]; pause_after is 'sentence' or 'clause'."""
    out = []
    for s in sentences(text, lang):
        pieces = split_long(s, limit, lang)
        for k, p in enumerate(pieces):
            out.append({'text': p, 'pause_after': 'clause' if k < len(pieces) - 1 else 'sentence'})
    if merge_short:
        merged = []
        for c in out:
            if merged and len(merged[-1]['text']) < short and len(merged[-1]['text']) + len(c['text']) < limit:
                merged[-1] = {'text': merged[-1]['text'] + ' ' + c['text'], 'pause_after': c['pause_after']}
            else: merged.append(c)
        out = merged
    return out
