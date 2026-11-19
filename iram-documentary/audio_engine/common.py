"""Shared paths, configuration and small audio helpers (numpy, soundfile, ffmpeg only)."""
import json, pathlib, subprocess, hashlib, re
import numpy as np
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = pathlib.Path('/home/user/iram-work')


def load_yaml(rel):
    return yaml.safe_load(open(ROOT / rel, encoding='utf-8'))


def config():
    return load_yaml('configuration/voice_config.yaml')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, capture_output=True, text=True, **kw)


def read_audio(path, sr=None, mono=True):
    """Read any audio or video file through ffmpeg as float32 (mono by default)."""
    import soundfile as sf
    path = pathlib.Path(path)
    if path.suffix.lower() == '.wav' and sr is None:
        x, r = sf.read(path, dtype='float32', always_2d=True)
        return (x.mean(1) if mono else x), r
    # decode all channels and average them here: ffmpeg's own '-ac 1' downmix sums them and can clip
    args = ['ffmpeg', '-v', 'error', '-i', path, '-vn', '-f', 'f32le', '-acodec', 'pcm_f32le']
    if sr: args += ['-ar', str(sr)]
    info = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate,channels', '-of', 'json', path]).stdout)['streams'][0]
    r = sr or int(info['sample_rate']); ch = int(info['channels'])
    raw = subprocess.run([str(a) for a in args] + ['-'], check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).copy().reshape(-1, ch)
    return (x.mean(1) if mono else x), r


def write_wav(path, x, sr, subtype='PCM_24'):
    import soundfile as sf
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, x, sr, subtype=subtype)


def ffilter(x, sr, af):
    """Run a float32 array through an ffmpeg audio filter chain."""
    import soundfile as sf, tempfile
    with tempfile.TemporaryDirectory(dir=WORK) as d:
        a, b = f'{d}/in.wav', f'{d}/out.wav'
        sf.write(a, x, sr, subtype='FLOAT')
        run(['ffmpeg', '-y', '-v', 'error', '-i', a, '-af', af, '-c:a', 'pcm_f32le', b])
        y, _ = sf.read(b, dtype='float32')
    return y[:len(x)]


def lufs(x, sr):
    import pyloudnorm as pyln
    if len(x) < sr * 0.5: x = np.concatenate([x, np.zeros(int(sr * 0.5), np.float32)])
    return float(pyln.Meter(sr).integrated_loudness(x))


def gain_to_lufs(x, sr, target):
    return (x * 10 ** ((target - lufs(x, sr)) / 20)).astype(np.float32)


def peak_db(x):
    return float(20 * np.log10(np.abs(x).max() + 1e-12))


def frame_db(x, sr, win=0.05, hop=0.01):
    n, h = int(win * sr), int(hop * sr)
    if len(x) < n: return np.array([-120.0])
    idx = np.arange(0, len(x) - n, h)
    e = np.array([np.sqrt(np.mean(x[i:i + n] ** 2)) for i in idx])
    return 20 * np.log10(e + 1e-9)


AR_RE = re.compile(r'[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]')
LAT_RE = re.compile(r'[A-Za-z]')


def script_ratio(text):
    """Fraction of letters that are Arabic script (0 = all Latin, 1 = all Arabic)."""
    a = len(AR_RE.findall(text)); l = len(LAT_RE.findall(text))
    return a / (a + l) if a + l else 0.0


HARAKAT = re.compile(r'[ؐ-ًؚ-ٰٟۖ-ۭـ]')


def strip_diacritics(t):
    """Arabic letters only: remove harakat, Quranic annotation marks and tatweel; unify alif and ya forms."""
    t = HARAKAT.sub('', t)
    t = re.sub('[ٱأإآ]', 'ا', t).replace('ى', 'ي').replace('ة', 'ه').replace('ؤ', 'و').replace('ئ', 'ي')
    return re.sub(r'[^ء-ي\s]', ' ', t)
