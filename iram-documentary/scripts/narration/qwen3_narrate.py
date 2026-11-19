"""Qwen3-TTS narration (CPU). Mode 'design': VoiceDesign model from a text persona.
Mode 'clone': Base model cloned from a designed reference clip, for a consistent voice across chapters."""
import argparse, json, time, re, pathlib
import numpy as np, soundfile as sf, torch
from qwen_tts import Qwen3TTSModel
M = pathlib.Path('/home/user/iram-work/models')
PERSONA = ("Male narrator, about 55 years old, deep baritone voice with a warm, smooth, rounded tone. "
           "Calm, soothing and measured, like a premium historical documentary. Natural pacing with gentle pauses, "
           "clear articulation, serious and reflective, quietly investigative, never theatrical or exaggerated.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['design', 'clone'], default='design')
    ap.add_argument('--text', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--instruct', default=PERSONA)
    ap.add_argument('--ref', help='reference wav for clone'); ap.add_argument('--ref_text', help='reference transcript file')
    ap.add_argument('--split', action='store_true', help='synthesise sentence by sentence')
    ap.add_argument('--pause', type=float, default=0.35); ap.add_argument('--dtype', default='bfloat16')
    ap.add_argument('--seed', type=int, default=1234)
    a = ap.parse_args()
    torch.set_num_threads(4); torch.manual_seed(a.seed)
    dt = getattr(torch, a.dtype)
    name = 'qwen3-tts-1.7b-voicedesign' if a.mode == 'design' else 'qwen3-tts-1.7b-base'
    t0 = time.time()
    model = Qwen3TTSModel.from_pretrained(str(M/name), device_map='cpu', dtype=dt)
    t_load = time.time() - t0
    text = open(a.text, encoding='utf-8').read().strip()
    parts = [s for s in re.split(r'(?<=[.?!])\s+', text) if s.strip()] if a.split else [text]
    prompt = None
    if a.mode == 'clone':
        prompt = model.create_voice_clone_prompt(ref_audio=a.ref, ref_text=open(a.ref_text, encoding='utf-8').read().strip())
    out = []; sr = 24000; t1 = time.time()
    for p in parts:
        if a.mode == 'design':
            wavs, sr = model.generate_voice_design(text=p, language='English', instruct=a.instruct)
        else:
            wavs, sr = model.generate_voice_clone(text=p, language='English', voice_clone_prompt=prompt)
        out.append(np.asarray(wavs[0], dtype=np.float32))
        if a.split: out.append(np.zeros(int(sr*a.pause), np.float32))
    wav = np.concatenate(out); sf.write(a.out, wav, sr)
    print(json.dumps({'out': a.out, 'mode': a.mode, 'seconds': round(len(wav)/sr, 2), 'load_s': round(t_load, 1), 'gen_s': round(time.time()-t1, 1), 'sr': sr}))

if __name__ == '__main__':
    main()
