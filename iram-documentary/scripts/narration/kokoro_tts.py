"""Kokoro-82M narration generator (CPU). Sentence-level synthesis so pauses and retakes stay controllable."""
import os
import argparse, json, re, time, pathlib
import numpy as np, soundfile as sf, torch

MODEL_DIR = pathlib.Path(os.environ.get('IRAM_WORK', '/home/user/iram-work') + '/models/kokoro-82m')

def load_pipeline(lang='b'):
    from kokoro import KPipeline, KModel
    model = KModel(repo_id='hexgrad/Kokoro-82M', config=str(MODEL_DIR/'config.json'), model=str(MODEL_DIR/'kokoro-v1_0.pth')).eval()
    return KPipeline(lang_code=lang, repo_id='hexgrad/Kokoro-82M', model=model)

def voice_tensor(spec):
    """spec like 'bm_george' or 'bm_george:0.7,am_michael:0.3' (weighted blend)."""
    parts = [p.split(':') for p in spec.split(',')]
    tot = 0; acc = None
    for p in parts:
        w = float(p[1]) if len(p) > 1 else 1.0
        v = torch.load(MODEL_DIR/'voices'/f'{p[0]}.pt', weights_only=True) * w
        acc = v if acc is None else acc + v; tot += w
    return acc / tot

def synth(pipe, text, voice, speed):
    chunks = []
    for gs, ps, audio in pipe(text, voice=voice, speed=speed, split_pattern=None):
        chunks.append(audio.numpy() if hasattr(audio, 'numpy') else np.asarray(audio))
    return np.concatenate(chunks) if chunks else np.zeros(0, np.float32)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--text', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--voice', default='bm_george'); ap.add_argument('--speed', type=float, default=0.92)
    ap.add_argument('--lang', default='b'); ap.add_argument('--pause', type=float, default=0.38)
    a = ap.parse_args()
    torch.set_num_threads(4)
    pipe = load_pipeline(a.lang); voice = voice_tensor(a.voice)
    text = open(a.text, encoding='utf-8').read().strip()
    sents = [s for s in re.split(r'(?<=[.?!])\s+', text) if s.strip()]
    t0 = time.time(); out = []
    for s in sents:
        out.append(synth(pipe, s, voice, a.speed)); out.append(np.zeros(int(24000*a.pause), np.float32))
    wav = np.concatenate(out); sf.write(a.out, wav, 24000)
    print(json.dumps({'out': a.out, 'voice': a.voice, 'seconds': round(len(wav)/24000, 2), 'compute_s': round(time.time()-t0, 1)}))
