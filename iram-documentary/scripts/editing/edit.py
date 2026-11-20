"""Documentary editor: timeline -> frames -> H.264, narration + procedural ambience mix, subtitles.

  python edit.py timeline                 # build renders/timeline.json from script + narration + shots
  python edit.py depth                    # depth maps (Depth-Anything-V2-Small) for parallax stills
  python edit.py video --chapter N [--preview]   # render one chapter (or 'all') to renders/chapters/
  python edit.py audio                    # narration + ambience mix -> renders/final/mix.wav
  python edit.py srt                      # subtitles -> assets/subtitles/iram.srt
"""
import argparse, json, math, os, pathlib, re, subprocess, sys, functools
import numpy as np, cv2, yaml
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/animation')); sys.path.insert(0, str(ROOT / 'scripts/editing'))
import graphics as G
W, H, FPS = 1920, 1080, 24
XF = 1.0          # crossfade length (s)
GAP = 0.6         # pause between narration paragraphs (s)
CHAPTER_CARD = 5.0
CREDITS = 42.0
TL = pathlib.Path(os.environ.get('IRAM_TIMELINE', ROOT / 'renders/timeline.json'))
# Narration segments from audio_engine (version 2: cloned English + Arabic narrators). Version 1 (Qwen3 designed
# voice) stays reproducible with IRAM_NARRATION_DIR=assets/narration/raw.
NARR = ROOT / os.environ.get('IRAM_NARRATION_DIR', 'assets/narration/segments')
NUM = {1: 'ONE', 2: 'TWO', 3: 'THREE', 4: 'FOUR', 5: 'FIVE', 6: 'SIX'}

def load_yaml(p): return yaml.safe_load(open(ROOT / p, encoding='utf-8'))

# ------------------------------------------------------------------ timeline
def build_timeline():
    script = load_yaml('screenplay/script.yaml'); shots = load_yaml('storyboard/shots.yaml')
    raw = NARR; tl = {'segments': [], 'shots': []}; t = 0.0
    for ch in script['chapters']:
        if ch['id'] > 0:
            first = shots[ch['segments'][0]['id']][0][0]
            tl['shots'].append({'asset': 'G_CHAPTER', 'move': 'gfx', 'start': t, 'end': t + CHAPTER_CARD, 'chapter': ch['id'],
                                'opts': {'number': NUM[ch['id']], 'title': ch['title'], 'bg': first, 'sfx': ['wind_low']}})
            t += CHAPTER_CARD
        for seg in ch['segments']:
            meta = json.load(open(raw / f"{seg['id']}.json"))
            vis0 = t; t += seg.get('pre_silence', 0.0)
            tl['segments'].append({'id': seg['id'], 'chapter': ch['id'], 'start': round(t, 3), 'dur': meta['duration'], 'sentences': meta['sentences']})
            t += meta['duration'] + seg.get('post_silence', 0.0) + GAP
            span = t - vis0; sl = shots[seg['id']]; wsum = sum(s[2] for s in sl); c = vis0
            for a, move, w, *rest in sl:
                d = span * w / wsum
                tl['shots'].append({'asset': a, 'move': move, 'start': round(c, 3), 'end': round(c + d, 3), 'chapter': ch['id'], 'seg': seg['id'], 'opts': rest[0] if rest else {}})
                c += d
    tl['shots'].append({'asset': 'G_CREDITS', 'move': 'gfx', 'start': t, 'end': t + CREDITS, 'chapter': 7, 'opts': {'sfx': ['wind_low']}})
    tl['duration'] = round(t + CREDITS, 3)
    json.dump(tl, open(TL, 'w'), indent=1, ensure_ascii=False)
    short = [s for s in tl['shots'] if s['end'] - s['start'] < 2.5]
    print(f"timeline: {tl['duration'] / 60:.2f} min, {len(tl['shots'])} shots, {len(short)} shorter than 2.5 s")
    return tl

# ------------------------------------------------------------------ assets
ASSETS = load_yaml('storyboard/assets.yaml')
PHOTOS = load_yaml('assets/archaeological_photographs/photo_map.yaml')

@functools.lru_cache(None)
def commons_meta():
    p = ROOT / 'assets/archaeological_photographs/commons_licences.json'
    return json.load(open(p, encoding='utf-8')) if p.exists() else {}

def asset_path(key):
    if key in ASSETS['ai']: return ROOT / f'assets/images/{key}.png'
    if key in PHOTOS and 'nasa' in PHOTOS[key]:
        return next((ROOT / 'assets/archaeological_photographs').glob(PHOTOS[key]['nasa'] + '.*'))
    if key.startswith('PH_'):
        m = commons_meta().get(PHOTOS[key]['commons'], {}); p = ROOT / 'assets/archaeological_photographs' / m.get('local', 'missing')
        return p if p.exists() else asset_path(PHOTOS[key]['fallback'])
    if key.startswith('B02_V'):
        p = ROOT / f'assets/images/{key}.png'          # SDXL img2img pass over the Blender layout
        return p if p.exists() else ROOT / f"assets/3d_models/renders/columns_v{key[-1]}.png"
    if key == 'B03': return ROOT / 'assets/3d_models/renders/shisr_schematic.png'
    raise KeyError(key)

def anim_frames(key):
    d = ROOT / 'assets/3d_models/renders' / {'B01': 'dunes', 'B04': 'ridge'}[key]
    return sorted(d.glob('*.png'))

def label_for(shot):
    a = shot['asset']; o = shot['opts']
    if o.get('label'): return o['label']
    if a in ASSETS['ai']: return ASSETS['ai'][a].get('label')
    if a.startswith('B0'): return ASSETS['blender'].get(a[:3], {}).get('label')
    if a in PHOTOS:
        if 'commons' in PHOTOS[a] and not real_photo(a):
            fb = PHOTOS[a]['fallback']; return label_for({'asset': fb, 'opts': {}})
        if a == 'NASA_STS59': return 'ARCHIVE PHOTOGRAPH'
        return 'PHOTOGRAPH' if 'commons' in PHOTOS[a] else 'SATELLITE / SPACE IMAGERY'
    if a.startswith('M'): return ASSETS['maps'][a]['label']
    return None

def real_photo(a):
    m = commons_meta().get(PHOTOS[a].get('commons', ''), {})
    return bool(m.get('local')) and (ROOT / 'assets/archaeological_photographs' / m['local']).exists()

def credit_for(shot):
    a = shot['asset']
    if a in PHOTOS and 'commons' in PHOTOS[a] and not real_photo(a):
        return credit_for({'asset': PHOTOS[a]['fallback'], 'opts': {}})
    if a in PHOTOS and 'nasa' in PHOTOS[a]: return PHOTOS[a]['credit'] + ' · public domain'
    if a.startswith('PH_'):
        m = commons_meta().get(PHOTOS[a]['commons'], {})
        if not m: return None
        artist = re.sub(r'\s+', ' ', m.get('artist', '')).strip()[:60]
        return f"{artist} · {m.get('license', '')} · via Wikimedia Commons"
    if a in ASSETS['ai']: return 'AI-generated image (SDXL), animated with AI image-to-video' if clip_for(shot) else 'AI-generated image (SDXL)'
    if a.startswith('B0'): return '3D render (Blender), animated with AI image-to-video' if clip_for(shot) else '3D render (Blender)'
    return None

def tag_color(text):
    t = (text or '').upper()
    if 'LEGEND' in t: return G.EVIDENCE['L'][1]
    if 'RECONSTRUCTION' in t or 'ILLUSTRA' in t or 'SCHEMATIC' in t: return G.EVIDENCE['R'][1]
    if 'HYPOTHES' in t: return G.EVIDENCE['S'][1]
    if 'CLASSICAL' in t: return G.EVIDENCE['C'][1]
    return G.EVIDENCE['A'][1]

# ------------------------------------------------------------------ depth
def compute_depth(keys):
    import torch
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    mp = os.environ.get('IRAM_WORK', '/home/user/iram-work') + '/models/depth-anything-v2-small'
    proc = AutoImageProcessor.from_pretrained(mp); model = AutoModelForDepthEstimation.from_pretrained(mp).eval()
    out = ROOT / 'assets/images/depth'; out.mkdir(parents=True, exist_ok=True)
    for k in keys:
        p = asset_path(k); dst = out / f'{k}.png'
        if dst.exists() or not p.exists(): continue
        im = Image.open(p).convert('RGB')
        with torch.no_grad():
            pred = model(**proc(images=im, return_tensors='pt')).predicted_depth[0].numpy()
        d = cv2.resize(pred, im.size, interpolation=cv2.INTER_CUBIC)
        d = (d - np.percentile(d, 1)) / (np.percentile(d, 99) - np.percentile(d, 1) + 1e-6)
        d = np.clip(d, 0, 1)
        Image.fromarray((d * 65535).astype(np.uint16)).save(dst); print('depth', k, flush=True)

# ------------------------------------------------------------------ image moves
def lut_for(img):
    """Per-shot normalisation + shared warm documentary grade."""
    y = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    lo, hi = np.percentile(y, 1.5), np.percentile(y, 98.5)
    x = np.arange(256, dtype=np.float32)
    n = np.clip((x - lo) / max(30.0, hi - lo), 0, 1); n = 0.5 * n + 0.5 * (x / 255)
    s = 0.04 + 0.92 * (3 * n ** 2 - 2 * n ** 3) * 0.55 + 0.92 * n * 0.45
    r = np.clip((s * 1.03 + 0.008) * 255, 0, 255); g = np.clip(s * 255, 0, 255); b = np.clip((s * 0.94 + 0.01) * 255, 0, 255)
    return [r.astype(np.uint8), g.astype(np.uint8), b.astype(np.uint8)]

def apply_lut(f, lut):
    out = np.empty_like(f)
    for c in range(3): out[..., c] = cv2.LUT(f[..., c], lut[c])
    hsv = cv2.cvtColor(out, cv2.COLOR_RGB2HSV); hsv[..., 1] = (hsv[..., 1] * 0.9).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

class StillShot:
    def __init__(self, shot, scale=1.0):
        self.s = shot; self.move = shot['move']; self.sc = scale
        img = np.array(Image.open(asset_path(shot['asset'])).convert('RGB'))
        h, w = img.shape[:2]; self.framed = shot['asset'] in PHOTOS and (w / h < 1.45 or w < 1700)
        self.lut = lut_for(img)
        Wt, Ht = int(W * scale), int(H * scale)
        if self.framed:
            bg = cv2.resize(img, (Wt, int(Wt * h / w)) if w / h < W / H else (int(Ht * w / h), Ht), interpolation=cv2.INTER_AREA)
            y0 = (bg.shape[0] - Ht) // 2; x0 = (bg.shape[1] - Wt) // 2; bg = bg[y0:y0 + Ht, x0:x0 + Wt]
            self.bg = (cv2.GaussianBlur(bg, (0, 0), 28 * scale) * 0.32).astype(np.uint8)
            fh = int(Ht * 0.80); fw = int(fh * w / h)
            if fw > Wt * 0.86: fw = int(Wt * 0.86); fh = int(fw * h / w)
            self.fg = cv2.resize(img, (fw, fh), interpolation=cv2.INTER_AREA if fw < w else cv2.INTER_LANCZOS4)
        else:
            tw = int(Wt * 1.22); th = int(tw * h / w)
            if th < Ht * 1.22: th = int(Ht * 1.22); tw = int(th * w / h)
            self.img = cv2.resize(img, (tw, th), interpolation=cv2.INTER_LANCZOS4 if tw > w else cv2.INTER_AREA)
            self.depth = None
            if self.move.startswith('par'):
                dp = ROOT / f"assets/images/depth/{shot['asset']}.png"
                if dp.exists():
                    d = np.array(Image.open(dp)).astype(np.float32) / 65535
                    d = cv2.resize(d, (tw, th)); self.depth = cv2.GaussianBlur(d, (0, 0), 6 * scale) ** 1.5
                else:
                    self.move = 'in'
        self.dur = shot['end'] - shot['start'] + XF

    def frame(self, tl):
        u = min(1, max(0, tl / self.dur)); u = 0.85 * u + 0.15 * G.sm(u)
        Wt, Ht = int(W * self.sc), int(H * self.sc)
        if self.framed:
            z = 1.0 + 0.06 * u; fh, fw = self.fg.shape[:2]
            M = np.array([[z, 0, Wt / 2 - z * fw / 2], [0, z, Ht / 2 - z * fh / 2]], np.float32)
            out = self.bg.copy()
            fgw = cv2.warpAffine(self.fg, M, (Wt, Ht), flags=cv2.INTER_LINEAR)
            mask = cv2.warpAffine(np.ones((fh, fw), np.float32), M, (Wt, Ht), flags=cv2.INTER_LINEAR)[..., None]
            out = (out * (1 - 0.5 * np.clip(cv2.GaussianBlur(mask[..., 0], (0, 0), 18 * self.sc), 0, 1))[..., None]).astype(np.float32)
            out = out * (1 - mask) + fgw * mask
            return apply_lut(np.clip(out, 0, 255).astype(np.uint8), self.lut)
        th, tw = self.img.shape[:2]
        zoom = {'in': (1.0, 1.13), 'out': (1.13, 1.0), 'left': (1.1, 1.1), 'right': (1.1, 1.1), 'up': (1.1, 1.1), 'down': (1.1, 1.1),
                'drift': (1.03, 1.08), 'par': (1.0, 1.06), 'parl': (1.06, 1.06), 'parr': (1.06, 1.06)}.get(self.move, (1.0, 1.08))
        z = zoom[0] + (zoom[1] - zoom[0]) * u
        vw = tw / 1.22 / z * 1.0; vh = vw * Ht / Wt                 # source view size (source px)
        span_x = (tw - vw) / 2; span_y = (th - vh) / 2
        cx, cy = tw / 2, th / 2
        if self.move == 'left': cx += span_x * 0.6 * (1 - 2 * u)
        if self.move == 'right': cx -= span_x * 0.6 * (1 - 2 * u)
        if self.move == 'up': cy += span_y * 0.6 * (1 - 2 * u)
        if self.move == 'down': cy -= span_y * 0.6 * (1 - 2 * u)
        if self.move == 'drift': cx += span_x * 0.3 * (u - 0.5); cy += span_y * 0.2 * (0.5 - u)
        s = vw / Wt
        if self.depth is None or not self.move.startswith('par'):
            M = np.array([[s, 0, cx - s * Wt / 2], [0, s, cy - s * Ht / 2]], np.float32)
            f = cv2.warpAffine(self.img, M, (Wt, Ht), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
            return apply_lut(f, self.lut)
        X, Y = np.meshgrid(np.arange(Wt, dtype=np.float32), np.arange(Ht, dtype=np.float32))
        sx = cx + (X - Wt / 2) * s; sy = cy + (Y - Ht / 2) * s
        d = cv2.remap(self.depth, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if self.move == 'par':
            k = 1 + 0.07 * d * u                                    # near objects grow faster: depth push-in
            sx = cx + (sx - cx) / k; sy = cy + (sy - cy) / k
        else:
            dirn = -1 if self.move == 'parl' else 1
            sx = sx + dirn * (d - 0.5) * (u - 0.5) * 0.05 * tw
        f = cv2.remap(self.img, sx, sy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        return apply_lut(f, self.lut)

class AnimShot:
    def __init__(self, shot, scale=1.0):
        self.frames = anim_frames(shot['asset']); self.sc = scale; self.dur = shot['end'] - shot['start'] + XF
        self.lut = lut_for(np.array(Image.open(self.frames[len(self.frames) // 2]).convert('RGB')))
    def frame(self, tl):
        i = min(len(self.frames) - 1, int(tl / self.dur * len(self.frames)))
        im = np.array(Image.open(self.frames[i]).convert('RGB'))
        im = cv2.resize(im, (int(W * self.sc), int(H * self.sc)), interpolation=cv2.INTER_LANCZOS4)
        return apply_lut(im, self.lut)

class GfxShot:
    def __init__(self, shot, scale=1.0):
        self.s = shot; self.sc = scale; self.dur = shot['end'] - shot['start'] + XF
        o = shot['opts']; self.bg = None
        if o.get('bg') and o['bg'] in ASSETS['ai']:
            self.bg = Image.open(asset_path(o['bg'])).convert('RGB')
    def frame(self, tl):
        a = self.s['asset']; o = self.s['opts']
        if a.startswith('M'):
            import maps; im = maps.render(a, tl, self.dur, o.get('step', 0))
        elif a == 'G_CHAPTER':
            im = G.render('G_CHAPTER', tl, self.dur, bg=self.bg, number=o['number'], title=o['title'])
        else:
            im = G.render(a, tl, self.dur, o.get('step', 0), bg=self.bg)
        f = np.array(im)
        if self.sc == 1: return f
        return cv2.resize(f, (int(W * self.sc), int(H * self.sc)), interpolation=cv2.INTER_LANCZOS4 if self.sc > 1 else cv2.INTER_AREA)

# ------------------------------------------------------------------ image-to-video clips (WanGP or any other tool)
GEN_VIDEO = ROOT / 'assets/generated_video'


def shot_keys(tl):
    """Stable key per shot: <segment>_<index of the shot inside the segment>_<asset>, e.g. 1.01_0_D02.
    It does not depend on timings, so clips stay valid when the narration (and so the timeline) changes."""
    n = {}
    for s in tl['shots']:
        seg = s.get('seg') or f"ch{s['chapter']}"; k = n.get(seg, 0); n[seg] = k + 1
        s['_key'] = f"{seg}_{k}_{s['asset']}"
    return tl


def animatable(shot):
    """Only AI images and Blender renders may be animated. Real photographs (evidence), maps and graphics stay as they are."""
    a = shot['asset']
    return shot.get('move', 'still') not in ('gfx', 'anim') and (a in ASSETS['ai'] or a.startswith('B0'))


def clip_for(shot):
    if not animatable(shot) or os.environ.get('IRAM_USE_CLIPS', '1') == '0': return None
    for name in (shot.get('_key'), shot['asset']):
        if name and (GEN_VIDEO / f'{name}.mp4').exists(): return GEN_VIDEO / f'{name}.mp4'
    return None


class VideoShot:
    """A generated clip in place of a still. The clip is stretched to the shot length (neighbouring frames are blended
    when it plays slower), cropped to fill the frame, and graded with the same per-shot LUT as the stills."""
    def __init__(self, shot, path, scale=1.0):
        self.sc = scale; self.dur = shot['end'] - shot['start'] + XF; cap = cv2.VideoCapture(str(path)); fr = []
        while True:
            ok, f = cap.read()
            if not ok: break
            fr.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        cap.release()
        if not fr: raise RuntimeError(f'cannot read {path}')
        self.frames = fr; self.lut = lut_for(fr[len(fr) // 2])

    def frame(self, tl):
        n = len(self.frames); pos = min(1.0, max(0.0, tl / self.dur)) * (n - 1); i = int(pos); a = pos - i
        f = self.frames[i].astype(np.float32)
        if a > 0.01 and i + 1 < n: f = f * (1 - a) + self.frames[i + 1].astype(np.float32) * a
        Wt, Ht = int(W * self.sc), int(H * self.sc); h, w = f.shape[:2]; z = max(Wt / w, Ht / h)
        f = cv2.resize(f, (int(round(w * z)), int(round(h * z))), interpolation=cv2.INTER_LANCZOS4 if z > 1 else cv2.INTER_AREA)
        y0 = (f.shape[0] - Ht) // 2; x0 = (f.shape[1] - Wt) // 2
        return apply_lut(np.clip(f[y0:y0 + Ht, x0:x0 + Wt], 0, 255).astype(np.uint8), self.lut)


def make_shot(shot, scale):
    if shot['move'] == 'gfx': return GfxShot(shot, scale)
    if shot['move'] == 'anim': return AnimShot(shot, scale)
    clip = clip_for(shot)
    if clip: return VideoShot(shot, clip, scale)
    return StillShot(shot, scale)

# ------------------------------------------------------------------ overlays & finishing
@functools.lru_cache(None)
def overlay_layer(asset, label, credit, caption, scale):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); from PIL import ImageDraw
    d = ImageDraw.Draw(ov)
    if label:
        f = G.font('sans_b', 20); tw = d.textlength(label, font=f)
        col = tag_color(label)
        d.rounded_rectangle([60, 52, 60 + tw + 64, 92], 8, fill=(12, 10, 8, 150))
        d.ellipse([76, 64, 92, 80], fill=(*col, 255))
        G.draw_text(ov, (104, 72), label, f, (239, 230, 214), 0.95, anchor='lm')
    if credit:
        G.draw_text(ov, (W - 60, H - 40), credit, G.font('sans', 18), (225, 215, 200), 0.75, anchor='rm')
    if caption:
        f = G.font('italic', 34); tw = d.textlength(caption, font=f)
        grad = Image.new('RGBA', (int(tw) + 140, 90), (10, 8, 6, 120)); ov.alpha_composite(grad, (40, H - 175))
        d.line([(70, H - 160), (130, H - 160)], fill=(216, 180, 122, 230), width=2)
        G.draw_text(ov, (70, H - 125), caption, f, (239, 230, 214), 0.95, anchor='lm')
    if scale != 1: ov = ov.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    a = np.array(ov).astype(np.float32) / 255
    return a[..., :3] * 255, a[..., 3:4]

@functools.lru_cache(None)
def vignette(scale):
    w, h = int(W * scale), int(H * scale); y, x = np.mgrid[0:h, 0:w]
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    return (1 - 0.22 * np.clip(r - 0.55, 0, 1) ** 1.6)[..., None].astype(np.float32)

@functools.lru_cache(None)
def grain_bank(scale, n=12):
    r = np.random.default_rng(3); w, h = int(W * scale), int(H * scale); bank = []
    for _ in range(n):
        g = r.standard_normal((h // 2, w // 2)).astype(np.float32)
        bank.append(cv2.resize(g, (w, h), interpolation=cv2.INTER_LINEAR)[..., None] * 3.2)
    return bank

def finish(frame, fi, scale):
    f = frame.astype(np.float32) * vignette(scale) + grain_bank(scale)[fi % 12]
    return np.clip(f, 0, 255).astype(np.uint8)

# ------------------------------------------------------------------ video render
def render_video(chapter, preview=False, part=None):
    # IRAM_SCALE=1.3333333 renders 2560x1440 (stills are resampled from the source; graphics and overlays drawn at 1080p are upscaled)
    tl = shot_keys(json.load(open(TL))); scale = 0.5 if preview else float(os.environ.get('IRAM_SCALE', '1.0')); fps = 12 if preview else FPS
    shots = [s for s in tl['shots'] if chapter == 'all' or s['chapter'] == int(chapter)]
    t0 = shots[0]['start']; t1 = shots[-1]['end']
    if chapter != 'all' and int(chapter) < 7:
        nxt = [s for s in tl['shots'] if s['chapter'] == int(chapter) + 1]
        t1 = nxt[0]['start'] if nxt else t1
    suffix = '' if not part else f"_part{part[0]}of{part[1]}"
    out = ROOT / ('renders/previews' if preview else os.environ.get('IRAM_CHAPTER_DIR', 'renders/chapters')) / f"chapter_{chapter}{suffix}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    w, h = int(W * scale), int(H * scale)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(fps), '-i', '-',
           '-c:v', 'libx264', '-preset', 'veryfast' if preview else 'medium', '-crf', '23' if preview else os.environ.get('IRAM_CRF', '16'), '-pix_fmt', 'yuv420p',
           '-x264-params', 'keyint=48', '-r', str(fps), str(out)]
    live = {}; nfr = int(round((t1 - t0) * fps)); total_start = tl['shots'][0]['start']; film_end = tl['duration']
    f_lo, f_hi = (0, nfr) if not part else ((part[0] - 1) * nfr // part[1], part[0] * nfr // part[1])
    # resume after an interruption: skip an output that is newer than every input AND has the full expected length
    # (a file cut off mid-write has no index, so ffprobe reports no duration)
    if not preview and os.environ.get('IRAM_FORCE_RENDER') != '1' and out.exists():
        inputs = [TL, ROOT / 'storyboard/shots.yaml', ROOT / 'storyboard/assets.yaml', pathlib.Path(__file__), ROOT / 'scripts/animation/graphics.py'] + \
                 [c for c in (clip_for(s_) for s_ in shots) if c]
        newest = max(p.stat().st_mtime for p in inputs if p.exists())
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(out)], capture_output=True, text=True)
        try: got = float(r.stdout.strip())
        except ValueError: got = -1.0
        if out.stat().st_mtime > newest and abs(got - (f_hi - f_lo) / fps) < 0.1:
            print('up to date, skipped:', out.name, flush=True); return
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)   # started only now: ffmpeg -y truncates the output
    for fi in range(f_lo, f_hi):
        t = t0 + fi / fps
        act = [s for s in tl['shots'] if s['start'] - XF / 2 <= t < s['end'] + XF / 2]
        layers = []
        for s in act:
            k = (s['asset'], s['start'])
            if k not in live: live[k] = make_shot(s, scale)
            tl_local = t - (s['start'] - XF / 2)
            f = live[k].frame(tl_local).astype(np.float32)
            lab = label_for(s); cred = credit_for(s) if s['move'] != 'gfx' else None
            cap = s['opts'].get('caption')
            if (lab or cred or cap) and s['move'] != 'gfx' or (s['asset'].startswith('M') and lab):
                rgb, al = overlay_layer(s['asset'], lab, cred, cap, scale)
                fa = min(G.fade(tl_local, XF + 0.3, 0.6), 1 - G.fade(tl_local, s['end'] - s['start'] + XF / 2 - 0.9, 0.6))
                f = f * (1 - al * fa) + rgb * al * fa
            # crossfade weight
            a_in = min(1.0, max(0.0, (t - (s['start'] - XF / 2)) / XF)); a_out = min(1.0, max(0.0, ((s['end'] + XF / 2) - t) / XF))
            wgt = min(a_in, a_out) if s is not tl['shots'][0] else a_out
            layers.append((wgt, f))
        if not layers: frame = np.zeros((h, w, 3), np.float32)
        else:
            tot = sum(w_ for w_, _ in layers) or 1
            frame = sum(w_ * f for w_, f in layers) / tot
        # global fades: from black at film start, to black before credits are handled by graphics
        if t < total_start + 2.0: frame = frame * max(0, (t - total_start) / 2.0)
        if t > film_end - 2.0: frame = frame * max(0, (film_end - t) / 2.0)
        proc.stdin.write(finish(frame, fi, scale).tobytes())
        for k in [k for k in live if not any((s['asset'], s['start']) == k for s in act)]: del live[k]
        if fi % (fps * 30) == 0: print(f'chapter {chapter}{suffix}: {fi}/{nfr} frames', flush=True)
    proc.stdin.close(); proc.wait(); print('wrote', out, flush=True)

# ------------------------------------------------------------------ audio
def ff_process(x, sr, af):
    """Run a float32 array (N or Nx2) through an ffmpeg audio filter chain and return it."""
    import soundfile as sf, tempfile
    with tempfile.TemporaryDirectory(dir=os.environ.get('IRAM_WORK', '/home/user/iram-work')) as d:
        a, b = f'{d}/in.wav', f'{d}/out.wav'
        sf.write(a, x, sr, subtype='FLOAT')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', a, '-af', af, '-c:a', 'pcm_f32le', b], check=True)
        y, _ = sf.read(b, dtype='float32')
    return y[:len(x)]

def build_audio():
    import soundfile as sf, sfx, pyloudnorm as pyln
    from scipy.signal import resample_poly
    tl = json.load(open(TL)); SR = sfx.SR; N = int((tl['duration'] + 1) * SR)
    narr = np.zeros(N, np.float32)
    for seg in tl['segments']:
        a, sr = sf.read(NARR / f"{seg['id']}.wav", dtype='float32')
        a = resample_poly(a, SR, sr).astype(np.float32); a = sfx.hp(a, 70, 2)
        i = int(seg['start'] * SR); narr[i:i + len(a)] += a[:N - i]
    meter = pyln.Meter(SR); narr *= 10 ** ((-19.0 - meter.integrated_loudness(narr)) / 20)
    # gentle voice compression + peak limiting (TTS output has a high crest factor)
    narr = ff_process(narr, SR, 'acompressor=threshold=-24dB:ratio=2.5:attack=8:release=180:makeup=1.5,alimiter=limit=0.56:attack=4:release=80:level=false')
    narr *= 10 ** ((-17.0 - meter.integrated_loudness(narr)) / 20)
    amb = np.zeros((N, 2), np.float32)
    for k, s in enumerate(tl['shots']):
        a0 = max(0.0, s['start'] - XF); a1 = min(tl['duration'], s['end'] + XF); dur = a1 - a0; n = int(dur * SR)
        tags = s['opts'].get('sfx', ['wind_low']); seed = 1000 + k
        lvl = max([sfx.WIND_LEVEL.get(t, 0.0) for t in tags] + [0.0])
        layer = np.zeros((n, 2), np.float32)
        if lvl > 0:
            ramp = (0.5, 0.95) if 'wind_rising' in tags else None
            layer += sfx.wind(dur, lvl, seed, structures=bool(set(tags) & sfx.STRUCT_TAGS), ramp=ramp)[:n]
        for t in tags:
            if t in sfx.SPOT: layer += sfx.SPOT[t](dur, seed + 7)[:n]
        fl = int(XF * SR); env = np.ones(n, np.float32)
        env[:fl] = np.sin(np.linspace(0, np.pi / 2, fl)) ** 2; env[-fl:] = np.cos(np.linspace(0, np.pi / 2, fl)) ** 2
        i = int(a0 * SR); m = min(n, N - i); amb[i:i + m] += (layer * env[:, None])[:m]
    # duck ambience under narration (~ -8 dB), smooth attack/release
    e = np.sqrt(np.convolve(narr ** 2, np.ones(2400) / 2400, mode='same'))
    e = np.clip(e / (np.percentile(e[e > 1e-4], 60) + 1e-9), 0, 1)
    e = sfx.lp(e, 2.0, 1); duck = 1 - 0.6 * np.clip(e, 0, 1)
    amb_l = meter.integrated_loudness(amb); amb *= 10 ** ((-29.0 - amb_l) / 20)
    amb = ff_process(amb, SR, 'alimiter=limit=0.22:attack=10:release=200:level=false')
    mix = np.stack([narr, narr], 1) + amb * duck[:, None]
    mix *= 10 ** ((-19.0 - meter.integrated_loudness(mix)) / 20)              # premaster at -19 LUFS (stereo)
    mix = ff_process(mix, SR, 'alimiter=limit=0.35:attack=3:release=60:level=false')   # peaks <= about -9 dBFS
    print('premaster peak dBFS', round(float(20 * np.log10(np.abs(mix).max() + 1e-9)), 2), 'LUFS', round(meter.integrated_loudness(mix), 2), flush=True)
    sf.write(ROOT / 'renders/final/mix_premaster.wav', mix, SR, subtype='FLOAT')
    sf.write(ROOT / 'assets/narration/narration_stem.wav', narr, SR, subtype='PCM_24')
    sf.write(ROOT / 'assets/sound_effects/ambience_stem.wav', amb * duck[:, None], SR, subtype='PCM_24')
    # two-pass EBU R128 loudness normalisation to -16 LUFS / -1.5 dBTP
    src = ROOT / 'renders/final/mix_premaster.wav'
    m = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(src), '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    js = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
    af = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
          f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(src), '-af', af, '-ar', '48000', '-c:a', 'pcm_s24le', str(ROOT / 'renders/final/mix.wav')], check=True)
    print('audio done', json.dumps(js))

# ------------------------------------------------------------------ subtitles
def build_srt():
    tl = json.load(open(TL)); script = load_yaml('screenplay/script.yaml')
    disp = {seg['id']: ' '.join(seg['text'].split()) for ch in script['chapters'] for seg in ch['segments']}
    split = lambda t: [x for x in re.split(r'(?<=[.?!])\s+|(?<=[.?!]["”’])\s+', t) if x and x.strip()]
    cues = []
    for seg in tl['segments']:
        ts = seg['sentences']
        if all('display' in s for s in ts):        # audio_engine timings carry the display text of each sentence
            ds = [' '.join(s['display'].split()) for s in ts]
        else: ds = split(disp[seg['id']])
        if len(ds) != len(ts):
            print('sentence mismatch', seg['id'], len(ds), len(ts)); ds = ds[:len(ts)] + [''] * (len(ts) - len(ds))
        for d, s in zip(ds, ts):
            st, en = seg['start'] + s['start'], seg['start'] + s['end']
            words = d.split(); chunks = []; cur = ''
            for w_ in words:
                if len(cur) + len(w_) + 1 > 76 and cur: chunks.append(cur); cur = w_
                else: cur = (cur + ' ' + w_).strip()
            if cur: chunks.append(cur)
            tot = sum(len(c) for c in chunks) or 1; c0 = st
            for c in chunks:
                c1 = c0 + (en - st) * len(c) / tot
                if len(c) <= 42: lines = c
                else:
                    sp = [i for i, ch in enumerate(c) if ch == ' ']
                    i = min(sp, key=lambda i: max(i, len(c) - i - 1)); lines = c[:i] + '\n' + c[i + 1:]
                cues.append((c0, max(c1, c0 + 1.0), lines)); c0 = c1
    cues.sort(key=lambda c: c[0])
    for k in range(len(cues) - 1):               # never overlap the next cue
        a_, b_, t_ = cues[k]
        if b_ > cues[k + 1][0] - 0.04: cues[k] = (a_, max(a_ + 0.5, cues[k + 1][0] - 0.04), t_)
    fmt = lambda x: f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round(x % 1 * 1000)) % 1000:03d}"
    out = ROOT / 'assets/subtitles/iram_lost_city_documentary.en.srt'; out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        for i, (a, b, txt) in enumerate(cues, 1): f.write(f"{i}\n{fmt(a)} --> {fmt(b)}\n{txt}\n\n")
    print('srt cues', len(cues), out)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--chapter', default='all'); ap.add_argument('--preview', action='store_true'); ap.add_argument('--part', default=None)
    a = ap.parse_args()
    if a.cmd == 'timeline': build_timeline()
    elif a.cmd == 'depth':
        sh = load_yaml('storyboard/shots.yaml'); keys = sorted({x[0] for v in sh.values() for x in v if x[1].startswith('par')})
        compute_depth(keys)
    elif a.cmd == 'video': render_video(a.chapter, a.preview, tuple(int(x) for x in a.part.split('/')) if a.part else None)
    elif a.cmd == 'audio': build_audio()
    elif a.cmd == 'srt': build_srt()
