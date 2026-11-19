"""VoxCPM2 worker (runs in /home/user/iram-work/venvs/voxcpm). Mode: 'ultimate' cloning =
reference audio + its transcript as the continuation prompt, and the same clip as the isolated reference."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, torch
from _worker_common import args, loop

a = args()
torch.set_num_threads(a.threads)
from voxcpm import VoxCPM

model = VoxCPM(voxcpm_model_path=a.model, zipenhancer_model_path=None, enable_denoiser=False, optimize=False, device='cpu')
SR = model.tts_model.sample_rate


def synth(j, seed):
    torch.manual_seed(seed); np.random.seed(seed % 2**32); random.seed(seed)
    p = {'cfg_value': 2.0, 'inference_timesteps': 10, 'normalize': False, 'denoise': False, **j.get('params', {})}
    mode = p.pop('mode', 'ultimate')
    kw = dict(text=j['text'], reference_wav_path=j['ref_wav'], retry_badcase=True, retry_badcase_max_times=2, **p)
    if mode == 'ultimate':
        kw.update(prompt_wav_path=j['ref_wav'], prompt_text=j['ref_text'])
    with torch.inference_mode():
        w = model.generate(**kw)
    return w, SR


loop('voxcpm2', synth, a)
