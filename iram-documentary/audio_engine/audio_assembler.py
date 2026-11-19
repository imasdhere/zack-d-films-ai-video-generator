"""Final audio assembly: segments -> timeline -> narration stem + ambience mix -> subtitles, then sync checks.

  python -m audio_engine.audio_assembler all        # assemble segments, rebuild timeline, mix, subtitles, sync check
  python -m audio_engine.audio_assembler sync       # only the audio-video sync check against renders/timeline.json

The mix itself stays in scripts/editing/edit.py (build_audio), so there is one mixing implementation for the film.
"""
import json, subprocess, sys
import numpy as np
from .common import ROOT, read_audio
from . import synthesis_manager as SM

EDIT = ROOT / 'scripts/editing/edit.py'
PY = sys.executable


def edit(cmd):
    r = subprocess.run([PY, str(EDIT), cmd], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.strip()[-800:]); r.check_returncode()


def sync_check():
    """Each narration segment in the mixed stem must start where the timeline says (cross-correlation, ±1 s)."""
    import soundfile as sf
    tl = json.load(open(ROOT / 'renders/timeline.json'))
    stem, sr = sf.read(ROOT / 'assets/narration/narration_stem.wav', dtype='float32')
    if stem.ndim > 1: stem = stem.mean(1)
    offs = []
    for seg in tl['segments']:
        a, s2 = read_audio(SM.SEGDIR / f"{seg['id']}.wav", sr=sr)
        a = a[:int(min(len(a), 3 * sr))]; i0 = int((seg['start'] - 1.0) * sr); win = stem[max(0, i0):i0 + len(a) + 2 * sr]
        if len(win) < len(a): continue
        c = np.correlate(win, a, 'valid'); lag = (np.argmax(c) + max(0, i0)) / sr - seg['start']
        offs.append({'seg': seg['id'], 'offset_ms': round(lag * 1000, 1)})
    bad = [o for o in offs if abs(o['offset_ms']) > 1000 / 24]
    res = {'segments_checked': len(offs), 'max_abs_offset_ms': max(abs(o['offset_ms']) for o in offs), 'over_one_frame': bad}
    json.dump(res, open(ROOT / 'reports/audio_sync_check.json', 'w'), indent=1)
    print(json.dumps(res)[:400])
    return res


def all_():
    SM.assemble()
    edit('timeline'); edit('audio'); edit('srt')
    sync_check()


if __name__ == '__main__':
    {'all': all_, 'sync': sync_check}[sys.argv[1]]()
