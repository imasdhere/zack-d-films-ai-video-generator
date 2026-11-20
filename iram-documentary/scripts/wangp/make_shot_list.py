"""Shot list for image-to-video (WanGP) from the current timeline.

  python scripts/wangp/make_shot_list.py
  -> handoff/wangp_shot_list.csv and handoff/wangp_shot_list.json

One row per shot. "animate" says whether the shot may be turned into a clip:
  yes  AI-generated image or Blender render (already labelled as reconstruction, legend or illustration on screen)
  no   real photograph (evidence: do not invent motion in it), map, title, chapter card or quotation graphic
Each animatable row gives the start image, the clip file name the editor looks for, the length the shot needs,
a motion prompt and a negative prompt. Clip names use stable shot keys, so they stay valid when timings change.
"""
import csv, json, pathlib, sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/editing')); sys.path.insert(0, str(ROOT / 'scripts/animation'))
import edit  # noqa: E402

MOVE = {'in': 'a very slow, steady camera push-in', 'out': 'a very slow, steady camera pull-back', 'left': 'a slow, steady camera pan to the left',
        'right': 'a slow, steady camera pan to the right', 'up': 'a slow, steady camera tilt up', 'down': 'a slow, steady camera tilt down',
        'drift': 'a slow, gentle camera drift', 'par': 'a slow dolly forward with gentle parallax', 'parl': 'a slow lateral move to the left with parallax',
        'parr': 'a slow lateral move to the right with parallax'}
NATURAL = {'D': 'wind lifting thin streams of sand off the dune crests, slowly moving cloud shadows, heat haze',
           'R': 'drifting dust in the air, slowly moving light and shadow, faint haze; the stone structures stay completely still',
           'L': 'faint drifting dust and slowly shifting light; the engraved, painted storybook style is kept exactly',
           'P': 'distant, anonymous figures move slowly and naturally; faces are never visible',
           'E': 'gentle natural motion of water, smoke or light as fitting the scene',
           'K': 'flickering lamp light and slowly drifting dust motes',
           'B': 'slowly moving light and faint drifting dust; the structures stay completely still'}
NEG = ('new people, faces, close-up figures, text, letters, writing, watermark, logo, modern objects, buildings changing shape, morphing, '
       'flicker, camera shake, fast motion, cartoon, music instruments')


def main():
    tl = edit.shot_keys(json.load(open(ROOT / 'renders/timeline.json')))
    assets = yaml.safe_load(open(ROOT / 'storyboard/assets.yaml', encoding='utf-8'))
    rows = []
    for s in tl['shots']:
        a = s['asset']; dur = round(s['end'] - s['start'] + edit.XF, 2); ok = edit.animatable(s)
        why = '' if ok else ('real photograph: evidence, do not add invented motion' if a in edit.PHOTOS else
                            'map: rendered by scripts/animation/maps.py' if a.startswith('M') else 'graphic, title or quotation card')
        prompt = img = ''
        if ok:
            spec = assets['ai'].get(a, {})
            scene = spec.get('prompt') or {'B01': 'a 3D architectural layout of tall stone columns in the desert'}.get(a, 'a 3D render of the ancient site')
            prompt = (f"{scene}. {NATURAL.get(a[0], NATURAL['E'])}. {MOVE.get(s['move'], 'a slow, steady camera move')}. "
                      'Keep the composition, lighting and every element of the start image; no new objects appear.')
            if a.startswith('P'): prompt += ' The Prophet Hud is never shown; people stay small, distant and anonymous.'
            img = str(edit.asset_path(a).relative_to(ROOT))
        rows.append({'shot_key': s['_key'], 'chapter': s['chapter'], 'segment': s.get('seg', ''), 'asset': a, 'camera_move': s['move'],
                     'start_s': round(s['start'], 2), 'end_s': round(s['end'], 2), 'clip_seconds_needed': dur,
                     'animate': 'yes' if ok else 'no', 'reason_if_no': why, 'on_screen_label': edit.label_for(s) or '',
                     'start_image': img, 'clip_file': f'assets/generated_video/{s["_key"]}.mp4' if ok else '',
                     'motion_prompt': prompt, 'negative_prompt': NEG if ok else ''})
    out = ROOT / 'handoff'; out.mkdir(exist_ok=True)
    with open(out / 'wangp_shot_list.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump(rows, open(out / 'wangp_shot_list.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n = sum(r['animate'] == 'yes' for r in rows)
    print(f'{len(rows)} shots, {n} animatable, {sum(r["clip_seconds_needed"] for r in rows if r["animate"] == "yes"):.0f} s of clips needed')


if __name__ == '__main__':
    main()
