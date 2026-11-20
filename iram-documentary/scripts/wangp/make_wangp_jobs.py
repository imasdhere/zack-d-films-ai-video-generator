"""Turn the shot list into WanGP settings files, one per shot, from a template that you export from YOUR WanGP.

  1. In WanGP, choose an image-to-video model (for example Wan 2.2 I2V), set resolution, steps and so on,
     add any start image, and press "Export Settings". Save the file, for example as ~/wangp_i2v_template.json.
  2. python scripts/wangp/make_wangp_jobs.py --template ~/wangp_i2v_template.json --fps 16 [--only 1.01_0_D02 ...]
  3. bash handoff/wangp_jobs/run_wangp_jobs.sh /path/to/WanGP     (runs `python wgp.py --process <job>.json` per shot)

Only these keys are changed in each copy of the template: prompt, negative_prompt, image_prompt_type ("S" = start image),
image_start (absolute path of the shot's still), video_length (frames) and seed. Everything else (model, resolution,
steps, LoRAs, sliding windows) stays as you set it in WanGP, so the files match your WanGP version.
"""
import argparse, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', required=True, help='settings JSON exported from WanGP (image-to-video model)')
    ap.add_argument('--fps', type=float, default=16.0, help='frame rate of the chosen model (Wan 2.1/2.2 14B: 16; Wan 2.2 TI2V 5B and LTX: 24)')
    ap.add_argument('--max-frames', type=int, default=0, help='cap video_length (0 = no cap; long shots are slowed down by the editor instead)')
    ap.add_argument('--only', nargs='*', help='shot keys to export (default: every animatable shot)')
    ap.add_argument('--seed', type=int, default=20261120)
    a = ap.parse_args()
    tpl = json.load(open(pathlib.Path(a.template).expanduser()))
    rows = [r for r in json.load(open(ROOT / 'handoff/wangp_shot_list.json', encoding='utf-8')) if r['animate'] == 'yes']
    if a.only: rows = [r for r in rows if r['shot_key'] in a.only]
    out = ROOT / 'handoff/wangp_jobs'; out.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(rows):
        frames = int(round(r['clip_seconds_needed'] * a.fps)) + 1
        frames = ((frames - 1 + 3) // 4) * 4 + 1          # Wan-family models want 4n+1 frames
        if a.max_frames: frames = min(frames, a.max_frames)
        job = dict(tpl)
        job.update({'prompt': r['motion_prompt'], 'negative_prompt': r['negative_prompt'], 'image_prompt_type': 'S',
                    'image_start': str((ROOT / r['start_image']).resolve()), 'video_length': frames, 'seed': a.seed + i})
        json.dump(job, open(out / f"{r['shot_key']}.json", 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    (out / 'run_wangp_jobs.sh').write_text(RUNNER, encoding='utf-8')
    print(f'{len(rows)} job files in {out}; run: bash {out}/run_wangp_jobs.sh /path/to/WanGP')


RUNNER = r'''#!/usr/bin/env bash
# Run every WanGP job in this folder headless, one shot at a time, and copy each result to the clip name the editor expects.
# Usage: bash run_wangp_jobs.sh /path/to/WanGP [python]     (run it with the Python environment that runs WanGP)
# Finished shots are skipped, so you can stop and restart it.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; PROJECT="$(cd "$HERE/../.." && pwd)"
WANGP="${1:?path to your WanGP folder}"; PY="${2:-python}"
mkdir -p "$PROJECT/assets/generated_video"
for job in "$HERE"/*.json; do
  key="$(basename "$job" .json)"; dest="$PROJECT/assets/generated_video/$key.mp4"
  [ -f "$dest" ] && { echo "skip $key (done)"; continue; }
  tmp="$HERE/out/$key"; mkdir -p "$tmp"
  echo "== $key"
  (cd "$WANGP" && "$PY" wgp.py --process "$job" --output-dir "$tmp") || { echo "FAILED $key"; continue; }
  clip="$(ls -t "$tmp"/*.mp4 2>/dev/null | head -1)"
  if [ -n "$clip" ]; then cp "$clip" "$dest"; echo "ok $key -> $dest"; else echo "NO OUTPUT $key"; fi
done
'''

if __name__ == '__main__':
    main()
