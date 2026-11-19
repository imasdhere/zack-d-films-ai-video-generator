"""Audar-TTS-V1-Flash worker (runs in /home/user/iram-work/venvs/audar). Follows the official reference
inference (github.com/AudarAI/Audar-TTS-V1, audar_tts/audar_tts_infer.py) on CPU in float32:
prompt = reference transcript + NeuCodec codes of the 16 kHz reference clip + target text; output 24 kHz."""
import os, sys, re, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, torch, librosa
from _worker_common import args, loop, CPS

a = args()
torch.set_num_threads(a.threads)
from transformers import AutoModelForCausalLM, AutoTokenizer
from neucodec import NeuCodec

tok = AutoTokenizer.from_pretrained(a.model)
model = AutoModelForCausalLM.from_pretrained(a.model, dtype=torch.float32).eval()
codec = NeuCodec.from_pretrained(a.codec).eval()
SPEECH = re.compile(r"<\|speech_(\d+)\|>")
TCE = tok.convert_tokens_to_ids('<|TARGET_CODES_END|>')
_ref_cache = {}


def ref_codes(path):
    if path not in _ref_cache:
        w, _ = librosa.load(path, sr=16000, mono=True)
        with torch.inference_mode():
            _ref_cache[path] = codec.encode_code(torch.from_numpy(w.astype(np.float32))[None, None, :]).squeeze().tolist()
    return _ref_cache[path]


def synth(j, seed):
    torch.manual_seed(seed); np.random.seed(seed % 2**32); random.seed(seed)
    codes = ''.join(f'<|speech_{c}|>' for c in ref_codes(j['ref_wav']))
    prompt = ('user: Convert the text to speech:'
              f"<|REF_TEXT_START|>{j['ref_text']}<|REF_TEXT_END|>"
              f'<|REF_SPEECH_START|>{codes}<|REF_SPEECH_END|>'
              f"<|TARGET_TEXT_START|>{j['text']}<|TARGET_TEXT_END|>"
              '\nassistant:<|TARGET_CODES_START|>')
    ids = tok.encode(prompt, add_special_tokens=False, return_tensors='pt')
    p = {'do_sample': True, 'temperature': 0.7, 'top_k': 40, 'top_p': 0.9, 'repetition_penalty': 1.1, **j.get('params', {})}
    # NeuCodec runs at 50 codes per second; cap the budget at 2.3x the expected duration + 2 s
    cap = int(50 * (2.3 * len(j['text']) / CPS.get(j.get('lang', 'en'), 13.0) + 2))
    with torch.inference_mode():
        out = model.generate(ids, max_new_tokens=cap, min_new_tokens=25, eos_token_id=TCE, pad_token_id=151643, **p)
        text = tok.decode(out[0, ids.shape[1]:], skip_special_tokens=False)
        cs = [int(x) for x in SPEECH.findall(text)]
        if not cs: raise RuntimeError('no speech tokens')
        w = codec.decode_code(torch.tensor(cs)[None, None, :]).cpu().numpy()[0, 0, :]
    return w, 24000


loop('audar-flash', synth, a)
