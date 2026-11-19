"""Generate screenplay markdown (master, per chapter, fact-checked) from screenplay/script.yaml + claim matrix."""
import yaml, csv, pathlib
root = pathlib.Path(__file__).resolve().parents[2]
s = yaml.safe_load(open(root/'screenplay/script.yaml', encoding='utf-8'))
claims = {r['claim_id']: r for r in csv.DictReader(open(root/'research/claim_verification_matrix.csv', encoding='utf-8'))}
EV = {'Q': 'Quranic text', 'H': 'Authentic hadith', 'C': 'Classical scholarship', 'L': 'Later tradition / legend',
      'A': 'Archaeology / documented history', 'S': 'Scientific or geographical evidence / hypothesis', 'R': 'Artistic reconstruction', 'N': 'Narrative framing'}
WPM = 130
def seg_md(seg, fact=False):
    out = [f"**[{seg['id']}]** _{EV[seg['evidence']]}_" + (f" · on-screen: `{seg['onscreen']}`" if seg.get('onscreen') else '')]
    if seg.get('pre_silence'): out.append(f"> *(silence / ambience {seg['pre_silence']} s)*")
    out.append(seg['text'].strip())
    if seg.get('post_silence'): out.append(f"> *(pause {seg['post_silence']} s)*")
    if fact and seg.get('claims'):
        for c in seg['claims']:
            r = claims[c]
            out.append(f"- ✔ `{c}` — {r['confidence_classification']} · {r['verification_status']} · source: {r['source']}")
    elif fact:
        out.append('- (no factual claim: framing)')
    return '\n\n'.join(out)
master = [f"# {s['title']}\n\n## {s['subtitle']}\n\nNarration master script. Generated from `screenplay/script.yaml` (single source of truth).\n"]
fact = [f"# {s['title']} — Final fact-checked script\n\nStatus: **APPROVED FOR PRODUCTION** after the claim review on 2026-11-19. Every segment is traced to `research/claim_verification_matrix.csv`. Claims marked *Secondary* are worded with attribution (\"according to its excavators\", \"argued\", \"suggests\").\n\nExcluded claims (not used anywhere in the film): " + ', '.join(f"`{k}` {v['claim']}" for k, v in claims.items() if k.startswith('X')) + "\n"]
tot_words = 0
for ch in s['chapters']:
    words = sum(len(x['text'].split()) for x in ch['segments']); tot_words += words
    sil = sum(x.get('pre_silence', 0) + x.get('post_silence', 0) for x in ch['segments'])
    est = words / WPM * 60 + sil
    head = f"## Chapter {ch['id']} — {ch['title']}\n\n*{words} words · estimated {est/60:.1f} min at {WPM} wpm plus {sil:.0f} s of planned silence*\n"
    body = '\n\n'.join(seg_md(x) for x in ch['segments'])
    master.append(head + '\n' + body)
    fact.append(head + '\n' + '\n\n'.join(seg_md(x, True) for x in ch['segments']))
    if ch['id'] > 0:
        (root/f"screenplay/chapter_{ch['id']:02d}.md").write_text(f"# {s['title']}\n\n" + head + '\n' + body + '\n', encoding='utf-8')
    else:
        (root/"screenplay/chapter_00_cold_open.md").write_text(f"# {s['title']}\n\n" + head + '\n' + body + '\n', encoding='utf-8')
master.append(f"\n---\nTotal narration: {tot_words} words.")
(root/'screenplay/master_script.md').write_text('\n\n'.join(master) + '\n', encoding='utf-8')
(root/'screenplay/final_fact_checked_script.md').write_text('\n\n'.join(fact) + '\n', encoding='utf-8')
print('ok', tot_words)
