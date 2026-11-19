"""Procedural natural sound effects (no music, no samples). 48 kHz stereo float32.
Every generator is seeded, so the mix is reproducible. Sounds are built only from filtered noise and
short physical impulses (wind, sand, footsteps, fire, water, stone, thunder); none is tonal or rhythmic music."""
import numpy as np
from scipy import signal

SR = 48000

def rng(seed): return np.random.default_rng(seed)

def pink(n, r):
    w = r.standard_normal(n + 1)
    f = np.fft.rfft(w); k = np.arange(len(f)); k[0] = 1
    p = np.fft.irfft(f / np.sqrt(k), n + 1)[:n]
    return (p / (np.std(p) + 1e-9)).astype(np.float32)

def brown(n, r):
    b = np.cumsum(r.standard_normal(n)); b = signal.sosfilt(signal.butter(1, 15, 'hp', fs=SR, output='sos'), b)
    return (b / (np.std(b) + 1e-9)).astype(np.float32)

def bp(x, lo, hi, order=2): return signal.sosfilt(signal.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x).astype(np.float32)
def lp(x, f, order=2): return signal.sosfilt(signal.butter(order, f, 'lowpass', fs=SR, output='sos'), x).astype(np.float32)
def hp(x, f, order=2): return signal.sosfilt(signal.butter(order, f, 'highpass', fs=SR, output='sos'), x).astype(np.float32)

def slow_env(n, r, rate_hz=0.15, lo=0.0, hi=1.0):
    """Smooth random envelope (gusts)."""
    k = max(4, int(n / SR * rate_hz * 4) + 4)
    pts = r.uniform(lo, hi, k); x = np.linspace(0, k - 1, n)
    e = np.interp(x, np.arange(k), pts)
    e = lp(e, rate_hz * 1.5, 1) if n > SR else e
    return np.clip(e, 0, None).astype(np.float32)

def stereo(l, r_): return np.stack([l, r_], 1).astype(np.float32)

def wind(dur, intensity=0.5, seed=0, structures=False, ramp=None):
    """Broadband wind: bands of pink/brown noise with independent gust envelopes; stereo decorrelated."""
    n = int(dur * SR); r = rng(seed); chans = []
    base = np.full(n, intensity, np.float32) if ramp is None else np.linspace(ramp[0], ramp[1], n, dtype=np.float32)
    gust = 0.55 + 0.9 * slow_env(n, r, 0.12, 0, 1) ** 1.5
    for c in range(2):
        rc = rng(seed * 7 + c + 1); acc = np.zeros(n, np.float32)
        bands = [(40, 160, 1.0, brown), (120, 400, 0.8, pink), (300, 900, 0.55, pink), (800, 2200, 0.28, pink), (2000, 6000, 0.10, pink)]
        for lo, hi, g, gen in bands:
            e = 0.6 + 0.8 * slow_env(n, rc, 0.2 + lo / 4000, 0, 1)
            acc += g * bp(gen(n, rc), lo, hi) * e
        if structures:   # air moving past stone edges: narrow, irregular, noisy resonances (not pitched notes)
            for k in range(3):
                fc = rc.uniform(500, 1300); drift = 1 + 0.15 * (slow_env(n, rc, 0.05, 0, 1) - 0.5)
                band = bp(pink(n, rc), fc * 0.85, fc * 1.18, 2)
                acc += 0.12 * band * slow_env(n, rc, 0.3, 0, 1) ** 2 * drift
        chans.append(acc * gust * base)
    out = stereo(chans[0], 0.75 * chans[1] + 0.25 * chans[0])
    return out * 0.18

def sand_hiss(dur, intensity=0.5, seed=1):
    n = int(dur * SR); r = rng(seed)
    g = slow_env(n, r, 0.25, 0, 1) ** 2.0
    ch = []
    for c in range(2):
        rc = rng(seed * 3 + c); x = hp(rc.standard_normal(n).astype(np.float32), 3500)
        grains = (rc.random(n) < 0.004).astype(np.float32) * rc.standard_normal(n).astype(np.float32)
        x = x * 0.6 + bp(grains, 3000, 9000) * 3.0
        ch.append(x * g * intensity)
    return stereo(*ch) * 0.05

def footsteps(dur, seed=2, pace=0.62):
    n = int(dur * SR); r = rng(seed); out = np.zeros((n, 2), np.float32)
    t = r.uniform(0.2, 0.6)
    while t < dur - 0.3:
        i = int(t * SR); L = int(0.18 * SR); env = np.exp(-np.linspace(0, 1, L) * 9) * (1 - np.exp(-np.linspace(0, 1, L) * 60))
        thud = lp(brown(L, r), 500) * 0.8 + bp(r.standard_normal(L).astype(np.float32), 1500, 5000) * 0.25
        crunch = bp((r.random(L) < 0.03) * r.standard_normal(L), 2000, 6000) * 2.0
        s = (thud + crunch) * env * r.uniform(0.7, 1.0)
        pan = 0.5 + 0.15 * np.sin(t)
        out[i:i + L, 0] += s[:n - i] * (1 - pan) * 2; out[i:i + L, 1] += s[:n - i] * pan * 2
        t += pace * r.uniform(0.9, 1.12)
    return out * 0.06

def fire(dur, seed=3):
    n = int(dur * SR); r = rng(seed)
    bed = bp(pink(n, r), 80, 500) * (0.6 + 0.4 * slow_env(n, r, 0.5, 0, 1)) * 0.25
    clicks = np.zeros(n, np.float32); k = r.poisson(9 * dur)
    for _ in range(k):
        i = r.integers(0, n - 2000); L = r.integers(200, 1600)
        clicks[i:i + L] += r.standard_normal(L).astype(np.float32) * np.exp(-np.linspace(0, 8, L)) * r.uniform(0.3, 1.5)
    clicks = bp(clicks, 1200, 7000)
    return stereo(bed + clicks * 0.5, bed * 0.9 + np.roll(clicks, 911) * 0.5) * 0.12

def thunder_far(dur, seed=4, at=None):
    n = int(dur * SR); r = rng(seed); out = np.zeros(n, np.float32)
    start = int((at if at is not None else r.uniform(0.2, 0.45) * dur) * SR)
    L = min(n - start, int(r.uniform(4, 7) * SR))
    if L > SR:
        x = brown(L, r); env = np.zeros(L, np.float32); tt = np.linspace(0, 1, L)
        for _ in range(r.integers(2, 5)):
            c = r.uniform(0.05, 0.6); w = r.uniform(0.05, 0.25); env += np.exp(-((tt - c) / w) ** 2) * r.uniform(0.4, 1.0)
        env *= np.exp(-tt * 2.2)
        out[start:start + L] = lp(x, 160, 4) * env
    return stereo(out, lp(np.roll(out, 300), 140)) * 0.5

def water_spring(dur, seed=5):
    n = int(dur * SR); r = rng(seed); out = np.zeros(n, np.float32)
    trickle = bp(pink(n, r), 400, 3000) * 0.08
    for _ in range(r.poisson(14 * dur)):
        i = r.integers(0, n - 4000); L = r.integers(600, 2400); f0 = r.uniform(400, 1400)
        tt = np.arange(L) / SR; f = f0 * (1 + 2.5 * tt / tt[-1])
        out[i:i + L] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * r.uniform(40, 90)) * r.uniform(0.05, 0.25)
    out += trickle
    return stereo(out, np.roll(out, 431)) * 0.1

def reverb(x, secs=1.6, seed=9, wet=0.35):
    r = rng(seed); L = int(secs * SR); ir = r.standard_normal(L).astype(np.float32) * np.exp(-np.linspace(0, 7, L)); ir = lp(ir, 3000)
    y = signal.fftconvolve(x, ir)[:len(x)] * 0.06
    return x * (1 - wet) + y * wet

def water_drip(dur, seed=6):
    n = int(dur * SR); r = rng(seed); out = np.zeros(n, np.float32); t = r.uniform(0.3, 1.0)
    while t < dur - 0.3:
        i = int(t * SR); L = int(0.09 * SR); tt = np.arange(L) / SR; f = r.uniform(900, 1800) * (1 + 1.8 * tt / tt[-1])
        out[i:i + L] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 55) * r.uniform(0.3, 0.6)
        t += r.uniform(1.2, 3.0)
    out = reverb(out, 2.2, seed, 0.6)
    return stereo(out, np.roll(out, 977)) * 0.12

def cave(dur, seed=7):
    n = int(dur * SR); r = rng(seed); x = lp(brown(n, r), 250) * 0.12
    return stereo(x, np.roll(x, 1200)) * 0.25

def room(dur, seed=8):
    n = int(dur * SR); r = rng(seed); x = lp(pink(n, r), 450) * 0.05 + bp(pink(n, r), 150, 900) * 0.02 * slow_env(n, r, 0.8, 0, 1)
    return stereo(x, np.roll(x, 700)) * 0.4

def cloth(dur, seed=10):
    n = int(dur * SR); r = rng(seed); g = slow_env(n, r, 0.4, 0, 1) ** 2
    flap = (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * np.cumsum(2 + 3 * slow_env(n, r, 0.3, 0, 1)) / SR))) * g
    x = bp(pink(n, r), 200, 1500) * lp(flap, 25)
    return stereo(x, np.roll(x, 500)) * 0.07

def stone_place(dur, seed=11):
    n = int(dur * SR); r = rng(seed); out = np.zeros(n, np.float32)
    for k in range(max(1, int(dur / 3))):
        i = int(r.uniform(0.25, 0.8) * n / max(1, int(dur / 3)) + k * n / max(1, int(dur / 3)))
        L = int(0.35 * SR); tt = np.linspace(0, 1, L)
        scrape = bp(r.standard_normal(L).astype(np.float32), 800, 3500) * np.exp(-((tt - 0.3) / 0.18) ** 2) * 0.5
        thud = lp(brown(L, r), 220) * np.exp(-np.maximum(tt - 0.55, 0) * 30) * (tt > 0.55)
        out[i:i + L] += (scrape + thud)[:n - i]
    return stereo(out, out * 0.9) * 0.12

def stone_rumble(dur, seed=12):
    n = int(dur * SR); r = rng(seed)
    x = lp(brown(n, r), 180) * (0.4 + 0.6 * slow_env(n, r, 0.6, 0, 1)) * 0.5
    gravel = bp((r.random(n) < 0.002) * r.standard_normal(n), 1500, 6000) * 2
    return stereo(x + gravel * 0.3, x + np.roll(gravel, 2000) * 0.3) * 0.12

def excavation(dur, seed=13):
    n = int(dur * SR); r = rng(seed); out = np.zeros(n, np.float32); t = r.uniform(0.2, 0.8)
    while t < dur - 0.6:
        i = int(t * SR); L = int(r.uniform(0.2, 0.45) * SR); tt = np.linspace(0, 1, L)
        s = bp(r.standard_normal(L).astype(np.float32), 1800, 6500) * np.sin(np.pi * tt) ** 2 * r.uniform(0.3, 0.7)
        out[i:i + L] += s[:n - i]; t += r.uniform(0.6, 1.6)
    return stereo(out, np.roll(out, 600)) * 0.08

def sea(dur, seed=14):
    n = int(dur * SR); r = rng(seed); tt = np.arange(n) / SR
    swell = np.zeros(n, np.float32); t = 0.0
    while t < dur:
        p = r.uniform(5.5, 9.0); c = t + p * 0.55
        swell += np.exp(-((tt - c) / (p * 0.22)) ** 2).astype(np.float32); t += p
    body = lp(brown(n, r), 600) * (0.3 + swell) * 0.4
    foam = hp(pink(n, r), 1800) * swell ** 2 * 0.25
    return stereo(body + foam, np.roll(body + foam, 1500)) * 0.18

def water_lake(dur, seed=15):
    n = int(dur * SR); r = rng(seed); g = slow_env(n, r, 0.7, 0, 1) ** 3
    x = bp(pink(n, r), 200, 900) * g * 0.6
    return stereo(x, np.roll(x, 800)) * 0.1

def paper(dur, seed=16):
    n = int(dur * SR); r = rng(seed); out = np.zeros(n, np.float32)
    for _ in range(max(1, int(dur / 4))):
        i = r.integers(0, max(1, n - SR)); L = int(0.5 * SR); tt = np.linspace(0, 1, L)
        out[i:i + L] += bp(r.standard_normal(L).astype(np.float32), 2000, 8000) * np.sin(np.pi * tt) ** 3 * 0.4
    return stereo(out, out) * 0.08

# tag -> (generator, wind_bed_level)  wind level drives the continuous bed (0 = off)
WIND_LEVEL = {'wind_low': 0.22, 'wind_soft': 0.40, 'wind_gust': 0.62, 'wind_night': 0.16, 'wind_rising': 0.55, 'wind_strong': 0.95,
              'wind_structures': 0.45, 'sand_hiss': 0.5, 'lamp_room': 0.0, 'cave': 0.0, 'silence_room': 0.0, 'fog_coast': 0.25}
SPOT = {'sand_hiss': lambda d, s: sand_hiss(d, 0.8, s), 'footsteps': footsteps, 'fire': fire, 'thunder_far': thunder_far,
        'water_spring': water_spring, 'water_drip': water_drip, 'cave': cave, 'lamp_room': room, 'silence_room': lambda d, s: room(d, s) * 0.5,
        'cloth': cloth, 'stone_place': stone_place, 'stone_rumble': stone_rumble, 'excavation': excavation, 'sea': sea,
        'fog_coast': lambda d, s: sea(d, s) * 0.5, 'water_lake': water_lake, 'paper': paper}
STRUCT_TAGS = {'wind_structures'}
