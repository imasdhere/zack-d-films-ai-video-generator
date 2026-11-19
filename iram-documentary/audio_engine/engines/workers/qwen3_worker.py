"""Qwen3-TTS-12Hz-1.7B-Base clone worker (legacy engine of version 1; English only). Runs in venvs/qwen."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, torch
from _worker_common import args, loop

a = args()
torch.set_num_threads(a.threads)
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(a.model, device_map='cpu', dtype=torch.bfloat16)
_prompts = {}


def synth(j, seed):
    if j['ref_wav'] not in _prompts:
        _prompts[j['ref_wav']] = model.create_voice_clone_prompt(ref_audio=j['ref_wav'], ref_text=j['ref_text'])
    torch.manual_seed(seed)
    cap = int(12 * (len(j['text']) / 9.0 + 4))
    wavs, sr = model.generate_voice_clone(text=j['text'], language='English', voice_clone_prompt=_prompts[j['ref_wav']], max_new_tokens=cap)
    return np.asarray(wavs[0], np.float32), sr


loop('qwen3-base', synth, a)
