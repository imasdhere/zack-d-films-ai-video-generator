"""Generate the full narration with Qwen3-TTS (voice-design reference -> Base-model clone), segment by segment.
Resumable: existing segment files are skipped. Writes assets/narration/raw/<seg>.wav and <seg>.json (sentence timings)."""
import json, re, time, pathlib, argparse
import numpy as np, soundfile as sf, torch
from qwen_tts import Qwen3TTSModel
root = pathlib.Path(__file__).resolve().parents[2]
M = pathlib.Path('/home/user/iram-work/models')
ap = argparse.ArgumentParser(); ap.add_argument('--only', nargs='*'); ap.add_argument('--sentence_pause', type=float, default=0.45)
ap.add_argument('--seed', type=int, default=20261119); ap.add_argument('--force', action='store_true'); a = ap.parse_args()
torch.set_num_threads(4)
jobs = json.load(open(root/'assets/narration/jobs/manifest.json', encoding='utf-8'))
raw = root/'assets/narration/raw'; raw.mkdir(parents=True, exist_ok=True)
model = Qwen3TTSModel.from_pretrained(str(M/'qwen3-tts-1.7b-base'), device_map='cpu', dtype=torch.bfloat16)
ref = root/'assets/narration/reference/narrator_reference.wav'
prompt = model.create_voice_clone_prompt(ref_audio=str(ref), ref_text=(root/'assets/narration/reference/ref_text.txt').read_text().strip())
def sentences(t):
    return [x for x in re.split(r'(?<=[.?!])\s+', t) if x.strip()]
for j in jobs:
    if a.only and j['id'] not in a.only: continue
    wav_p = raw/f"{j['id']}.wav"
    if wav_p.exists() and not a.force: continue
    t0 = time.time(); parts = []; timings = []; cur = 0.0; sr = 24000
    for k, snt in enumerate(sentences(j['tts'])):
        # Cap the token budget by sentence length (12 codec frames per second; ~14 chars/s speech + 4 s slack):
        # without it the model occasionally misses its end token and runs to 2048 tokens (~170 s).
        expected = len(snt) / 14.0
        cap = int(12 * (len(snt) / 9.0 + 4))
        for attempt in range(4):
            torch.manual_seed(a.seed + k + 1000 * attempt)
            wavs, sr = model.generate_voice_clone(text=snt, language='English', voice_clone_prompt=prompt, max_new_tokens=cap)
            w = np.asarray(wavs[0], np.float32)
            # trim leading/trailing near-silence so pauses are controlled by us
            thr = 0.01 * np.abs(w).max(); idx = np.where(np.abs(w) > thr)[0]
            if len(idx): w = w[max(0, idx[0]-int(0.03*sr)): idx[-1]+int(0.08*sr)]
            raw_len = len(wavs[0]) / sr; d = len(w) / sr
            ok = (raw_len < cap / 12 * 0.97) and (0.45 * expected < d < 2.2 * expected + 1.0)
            if ok: break
            print(json.dumps({'retry': j['id'], 'sentence': k, 'dur': round(d, 1), 'raw': round(raw_len, 1), 'expected': round(expected, 1)}), flush=True)
        timings.append({'i': k, 'tts': snt, 'start': round(cur, 3), 'end': round(cur + len(w)/sr, 3)})
        parts.append(w); cur += len(w)/sr
        gap = a.sentence_pause * (1.25 if snt.endswith('?') else 1.0)
        parts.append(np.zeros(int(sr*gap), np.float32)); cur += gap
    audio = np.concatenate(parts[:-1]) if len(parts) > 1 else parts[0]
    sf.write(wav_p, audio, sr)
    json.dump({'id': j['id'], 'sr': sr, 'duration': round(len(audio)/sr, 3), 'sentences': timings}, open(raw/f"{j['id']}.json", 'w'), indent=1)
    print(json.dumps({'seg': j['id'], 'audio_s': round(len(audio)/sr, 1), 'compute_s': round(time.time()-t0, 1)}), flush=True)
print('NARRATION_DONE', flush=True)
