"""Generate storyboard deliverables from the edited timeline:
storyboard/master_storyboard.csv, storyboard/scene_list.md, storyboard/visual_reference.md."""
import csv, json, pathlib, yaml
ROOT = pathlib.Path(__file__).resolve().parents[2]
tl = json.load(open(ROOT / 'renders/timeline.json'))
script = yaml.safe_load(open(ROOT / 'screenplay/script.yaml', encoding='utf-8'))
assets = yaml.safe_load(open(ROOT / 'storyboard/assets.yaml', encoding='utf-8'))
photos = yaml.safe_load(open(ROOT / 'assets/archaeological_photographs/photo_map.yaml', encoding='utf-8'))
segtext = {s['id']: (' '.join(s['text'].split()), s['evidence'], s.get('claims', [])) for c in script['chapters'] for s in c['segments']}
chap = {c['id']: c['title'] for c in script['chapters']}; chap[7] = 'End credits'
EVN = {'Q': 'Quranic text', 'H': 'Authentic hadith', 'C': 'Classical scholarship', 'L': 'Later tradition / legend', 'A': 'Archaeology / documented history',
       'S': 'Scientific evidence / hypothesis', 'R': 'Artistic reconstruction', 'N': 'Narrative framing'}
MOVES = {'in': 'slow push-in', 'out': 'slow pull-out', 'left': 'pan left', 'right': 'pan right', 'up': 'tilt up', 'down': 'tilt down', 'drift': 'gentle drift',
         'par': 'depth-parallax push-in', 'parl': 'depth-parallax slide left', 'parr': 'depth-parallax slide right', 'gfx': 'animated graphic', 'anim': '3D animation'}

def describe(a):
    if a in assets['ai']: return assets['ai'][a]['prompt'], 'AI image (SDXL)', assets['ai'][a].get('label') or ''
    if a in assets.get('img2img', {}): return assets['img2img'][a]['prompt'], 'Blender layout + SDXL img2img', assets['img2img'][a]['label']
    if a in photos:
        p = photos[a]; return (p.get('credit') or p.get('commons')), ('NASA image' if 'nasa' in p else 'Wikimedia Commons photograph'), 'PHOTOGRAPH / SPACE IMAGERY'
    if a.startswith('M'): return assets['maps'][a]['desc'], 'Animated map (DEM + Natural Earth)', assets['maps'][a]['label']
    if a == 'B03': return assets['blender']['B03']['desc'], 'Blender schematic', assets['blender']['B03']['label']
    if a.startswith('G_'): return a.replace('G_', '').replace('_', ' ').title() + ' card', 'Typography / diagram', ''
    return a, '', ''

rows = []
for i, s in enumerate(tl['shots'], 1):
    seg = s.get('seg'); nar, ev, cl = segtext.get(seg, ('', 'N', []))
    desc, kind, label = describe(s['asset'])
    status = 'rendered' if (ROOT / 'renders/chapters').exists() else 'planned'
    rows.append({'scene_id': f'S{i:03d}', 'chapter': f"{s['chapter']} — {chap.get(s['chapter'], '')}", 'segment': seg or '', 'start_s': round(s['start'], 2),
                 'duration_s': round(s['end'] - s['start'], 2), 'narration': nar if s is next(x for x in tl['shots'] if x.get('seg') == seg) else '(cont.)',
                 'visual_description': desc, 'asset_id': s['asset'], 'asset_type': kind, 'camera_movement': MOVES.get(s['move'], s['move']),
                 'generation_prompt': desc if kind.startswith(('AI', 'Blender layout')) else '', 'sound_effects': ', '.join(s['opts'].get('sfx', [])),
                 'map_or_animation': s['asset'] if s['move'] == 'gfx' else '', 'on_screen_label': label, 'caption': s['opts'].get('caption', ''),
                 'evidence_classification': EVN[ev] if seg else 'Chapter card / credits', 'claim_ids': ' '.join(cl), 'asset_status': status})
with open(ROOT / 'storyboard/master_storyboard.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
md = ['# Scene list', '', f"Total running time: {tl['duration'] / 60:.2f} min · {len(rows)} shots. Generated from `renders/timeline.json`.", '']
cur = None
for r in rows:
    if r['chapter'] != cur:
        cur = r['chapter']; md += ['', f'## Chapter {cur}', '', '| Scene | Start | Dur | Visual | Move | Label |', '|---|---|---|---|---|---|']
    t = r['start_s']; md.append(f"| {r['scene_id']} | {int(t // 60)}:{t % 60:04.1f} | {r['duration_s']}s | {r['asset_id']} — {r['visual_description'][:70]} | {r['camera_movement']} | {r['on_screen_label']} |")
(ROOT / 'storyboard/scene_list.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
vr = ['# Visual reference', '', 'Style grammar used for every generated image (see `configuration/visual_generation.yaml`).', '']
for k, v in assets['style'].items(): vr.append(f'- **{k}**: {v}')
vr += ['', '## Evidence colour grammar (on-screen tags)', '', '| Category | Colour (RGB) |', '|---|---|']
import sys; sys.path.insert(0, str(ROOT / 'scripts/animation')); import graphics as G
for k, (n, c) in G.EVIDENCE.items(): vr.append(f'| {n} | {c} |')
vr += ['', '## Typography', '', '- Titles: Cinzel. Body and quotations: EB Garamond. Labels: Inter. Arabic: Amiri Quran (verses), Amiri (tafsir).',
       '', '## Generated image index', '', '| ID | Label | Prompt |', '|---|---|---|']
for k, v in {**assets['ai'], **assets.get('img2img', {})}.items():
    vr.append(f"| {k} | {v.get('label') or '—'} | {v['prompt']} |")
(ROOT / 'storyboard/visual_reference.md').write_text('\n'.join(vr) + '\n', encoding='utf-8')
print('storyboard docs:', len(rows), 'rows')
