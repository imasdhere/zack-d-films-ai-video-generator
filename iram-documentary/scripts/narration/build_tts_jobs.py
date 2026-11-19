"""Build per-segment TTS input files from screenplay/script.yaml using the pronunciation lexicon."""
import yaml, json, re, pathlib, sys
root = pathlib.Path(__file__).resolve().parents[2]
engine = sys.argv[1] if len(sys.argv) > 1 else 'qwen3'
s = yaml.safe_load(open(root/'screenplay/script.yaml', encoding='utf-8'))
lex = yaml.safe_load(open(root/'configuration/pronunciation_lexicon.yaml', encoding='utf-8'))[engine]
out = root/'assets/narration/jobs'; out.mkdir(parents=True, exist_ok=True)
def tts_text(t):
    t = t.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    for k in sorted(lex, key=len, reverse=True): t = t.replace(k, lex[k])
    t = t.replace('"', '')            # quotation marks are not spoken
    t = re.sub(r'\s+', ' ', t).strip()
    leftover = re.findall(r'[ʿʾĀāĪīŪūḤḥṢṣṬṭḌḍẒẓ]', t)
    if leftover: raise SystemExit(f'unmapped diacritics {set(leftover)} in: {t[:120]}')
    return t
manifest = []
for ch in s['chapters']:
    for seg in ch['segments']:
        t = tts_text(seg['text'])
        (out/f"{seg['id']}.txt").write_text(t, encoding='utf-8')
        manifest.append({'id': seg['id'], 'chapter': ch['id'], 'display': ' '.join(seg['text'].split()), 'tts': t,
                         'pre_silence': seg.get('pre_silence', 0), 'post_silence': seg.get('post_silence', 0), 'quote': seg.get('quote', False)})
json.dump(manifest, open(out/'manifest.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(manifest), 'segments')
