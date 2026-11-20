"""Animated documentary maps (1920x1080) from real data.
Basemap: Copernicus GLO-90 DEM hillshade + Natural Earth land/borders (equirectangular, standard parallel = view centre).
Overlays (regions, pins, routes, labels) are animated per frame. Coordinates: see assets/maps_coordinates_wikipedia.json."""
import os
import functools, json, math, pathlib
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
import graphics as G

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = pathlib.Path(os.environ.get('IRAM_WORK', '/home/user/iram-work'))
W, H = 1920, 1080
STD_LAT = 22.0
COS = math.cos(math.radians(STD_LAT))

BASEMAPS = {  # name: (lon0, lon1, lat0, lat1, px per x-unit, dem file, dem extent)
    'arabia': (22.0, 72.0, 4.0, 38.0, 110, 'arabia_wide_150ppd.npy', (22, 72, 4, 38)),
    'dhofar': (50.0, 57.0, 16.0, 21.0, 650, 'dhofar_600ppd.npy', (50, 57, 16, 21)),
}
P = {  # verified coordinates (lat, lon)
    'Salalah': (17.0197, 54.0897), 'Khor Rori': (17.0393, 54.4305), 'Al-Baleed': (17.0064, 54.1306), 'Shisr': (18.2631, 53.6578),
    'Thumrait': (17.6669, 54.0328), 'Wabar': (21.5025, 50.4742), 'Wadi Ramm': (29.5931, 35.4200), 'al-Shihr': (14.7608, 49.6069),
    'Hadramawt': (16.0, 49.0), 'Qabr Hud': (16.1017, 49.5684), 'Shabwa': (15.3689, 47.0236), 'Qana': (14.025, 48.3419),
    'Najran': (17.4917, 44.1322), 'Hegra': (26.7917, 37.9528), 'Gaza': (31.5075, 34.4597), 'Riyadh': (24.6383, 46.715),
    'Mecca': (21.4225, 39.8262), 'Medina': (24.4672, 39.6111), 'Petra': (30.3285, 35.4444), 'Sanaa': (15.3483, 44.2064),
    'Muscat': (23.588, 58.383), 'Doha': (25.2867, 51.5333), 'Aden': (12.8, 45.0333),
}

def xy(lon, lat, bm):
    lon0, lon1, lat0, lat1, ppu = BASEMAPS[bm][:5]
    return ((lon - lon0) * COS * ppu, (lat1 - lat) * ppu)

def geo_polys(path, name_filter=None):
    d = json.load(open(path))
    out = []
    for f in d['features']:
        if name_filter and name_filter not in (f['properties'].get('NAME') or ''): continue
        g = f['geometry']; polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in polys: out.append(poly)
    return out

@functools.lru_cache(None)
def basemap(bm):
    cache = WORK / f'cache/maps/{bm}.png'
    if cache.exists():
        return np.array(Image.open(cache))
    lon0, lon1, lat0, lat1, ppu, demf, (dl0, dl1, da0, da1) = BASEMAPS[bm]
    Wb = int((lon1 - lon0) * COS * ppu); Hb = int((lat1 - lat0) * ppu)
    # land mask from Natural Earth
    land = Image.new('L', (Wb, Hb), 0); dr = ImageDraw.Draw(land)
    for poly in geo_polys(WORK / 'data/ne/ne_10m_land.geojson'):
        for ring_i, ring in enumerate(poly):
            pts = [xy(x, y, bm) for x, y in ring]
            if len(pts) > 2: dr.polygon(pts, fill=255 if ring_i == 0 else 0)
    land = np.array(land, np.float32) / 255
    # DEM resampled to the canvas grid
    dem = np.load(WORK / 'data/dem' / demf); dh, dw = dem.shape
    gx, gy = np.meshgrid(np.arange(Wb), np.arange(Hb))
    lon = lon0 + gx / (COS * ppu); lat = lat1 - gy / ppu
    mx = ((lon - dl0) / (dl1 - dl0) * dw).astype(np.float32); my = ((da1 - lat) / (da1 - da0) * dh).astype(np.float32)
    z = cv2.remap(dem.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    z = np.maximum(z, 0) * (land > 0.5)
    # hillshade (metres per pixel)
    mpp = 111320.0 / ppu
    zz = cv2.GaussianBlur(z, (0, 0), 0.8)
    dzdx = cv2.Sobel(zz, cv2.CV_32F, 1, 0, ksize=3) / (8 * mpp); dzdy = cv2.Sobel(zz, cv2.CV_32F, 0, 1, ksize=3) / (8 * mpp)
    ex = 6.0 if bm == 'arabia' else 3.0
    slope = np.arctan(ex * np.hypot(dzdx, dzdy)); aspect = np.arctan2(-dzdx, dzdy)
    az, alt = math.radians(315), math.radians(42)
    hs = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect - math.pi / 2)
    hs = np.clip(hs, 0, 1)
    # hypsometric desert palette
    stops = np.array([0, 300, 800, 1500, 2500, 4000], np.float32)
    cols = np.array([[196, 160, 112], [186, 150, 104], [166, 132, 96], [140, 114, 88], [120, 102, 86], [150, 140, 130]], np.float32)
    rgb = np.stack([np.interp(z, stops, cols[:, i]) for i in range(3)], -1)
    shade = (0.45 + 0.75 * hs)[..., None]
    rgb = rgb * shade
    # sand seas slightly warmer
    sand = Image.new('L', (Wb, Hb), 0); ds = ImageDraw.Draw(sand)
    for poly in geo_polys(WORK / 'data/ne/ne_10m_geography_regions_polys.geojson', 'AL KHALI'):
        ds.polygon([xy(x, y, bm) for x, y in poly[0]], fill=255)
    sand = cv2.GaussianBlur(np.array(sand, np.float32) / 255, (0, 0), ppu * 0.6)[..., None]
    rgb = rgb * (1 - 0.18 * sand) + np.array([214, 160, 98], np.float32) * 0.18 * sand
    ocean = np.array([30, 40, 48], np.float32)
    depthish = cv2.GaussianBlur(land, (0, 0), ppu * 0.8)[..., None]
    sea = ocean * (0.85 + 0.35 * depthish)
    m = cv2.GaussianBlur(land, (0, 0), 0.7)[..., None]
    out = rgb * m + sea * (1 - m)
    # coastline
    coast = cv2.morphologyEx((land > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((2, 2), np.uint8)).astype(np.float32)[..., None]
    out = out * (1 - 0.5 * coast) + np.array([235, 225, 205], np.float32) * 0.5 * coast
    # country borders (thin, light)
    bimg = Image.new('L', (Wb, Hb), 0); db = ImageDraw.Draw(bimg)
    for poly in geo_polys(WORK / 'data/ne/ne_10m_admin_0_countries.geojson'):
        pts = [xy(x, y, bm) for x, y in poly[0]]
        if len(pts) > 2: db.line(pts + [pts[0]], fill=255, width=max(1, int(ppu / 110)))
    bord = (np.array(bimg, np.float32) / 255)[..., None] * m
    out = out * (1 - 0.35 * bord) + np.array([240, 230, 210], np.float32) * 0.35 * bord
    out = np.clip(out * 0.92, 0, 255).astype(np.uint8)
    cache.parent.mkdir(parents=True, exist_ok=True); Image.fromarray(out).save(cache)
    return out

def view(bm, lon, lat, width_deg):
    """Affine from basemap px to frame px for a camera centred at (lon,lat) showing width_deg of longitude."""
    ppu = BASEMAPS[bm][4]; cx, cy = xy(lon, lat, bm)
    s = W / (width_deg * COS * ppu)
    return np.array([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]], np.float32)

def to_frame(M, lon, lat, bm):
    x, y = xy(lon, lat, bm); return (M[0, 0] * x + M[0, 2], M[1, 1] * y + M[1, 2])

def lerp(a, b, u): return a + (b - a) * u

class Overlay:
    def __init__(self):
        self.im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im)
    def S(self, p): return (p[0], p[1])
    def poly(self, pts, a, fill=(216, 180, 122), fa=60, la=220, width=3):
        if a <= 0: return
        pts2 = [self.S(p) for p in pts]
        self.d.polygon(pts2, fill=(*fill, int(fa * a)))
        self.d.line(pts2 + [pts2[0]], fill=(*fill, int(la * a)), width=width, joint='curve')
    def glow(self, center, rx, ry, a, color=(216, 180, 122)):
        if a <= 0: return
        q = 8; g = Image.new('L', (W // q, H // q), 0)
        ImageDraw.Draw(g).ellipse([(center[0] - rx) / q, (center[1] - ry) / q, (center[0] + rx) / q, (center[1] + ry) / q], fill=int(150 * a))
        g = g.filter(ImageFilter.GaussianBlur(float(min(rx, ry)) * 0.9 / q)).resize((W, H), Image.BILINEAR)
        col = Image.new('RGBA', g.size, (*color, 0)); col.putalpha(g); self.im.alpha_composite(col)
    def pin(self, p, a, color=(239, 230, 214), r=7):
        if a <= 0: return
        x, y = self.S(p); r2 = r
        self.d.ellipse([x - r2 * 2, y - r2 * 2, x + r2 * 2, y + r2 * 2], outline=(*color, int(120 * a)), width=2)
        self.d.ellipse([x - r2, y - r2, x + r2, y + r2], fill=(*color, int(255 * a)))
    def path(self, pts, u, a, color=(216, 180, 122), width=4, dashed=False):
        if a <= 0 or u <= 0: return
        seg = [(self.S(p)) for p in pts]; L = [math.dist(seg[i], seg[i + 1]) for i in range(len(seg) - 1)]; tot = sum(L); target = tot * u; acc = 0
        drawn = [seg[0]]
        for i, l in enumerate(L):
            if acc + l <= target: drawn.append(seg[i + 1]); acc += l
            else:
                f = (target - acc) / l; drawn.append((lerp(seg[i][0], seg[i + 1][0], f), lerp(seg[i][1], seg[i + 1][1], f))); break
        if dashed:
            for i in range(len(drawn) - 1):
                x0, y0 = drawn[i]; x1, y1 = drawn[i + 1]; n = int(math.dist(drawn[i], drawn[i + 1]) / 12) + 1
                for k in range(n):
                    if k % 2 == 0:
                        self.d.line([(lerp(x0, x1, k / n), lerp(y0, y1, k / n)), (lerp(x0, x1, (k + 1) / n), lerp(y0, y1, (k + 1) / n))], fill=(*color, int(230 * a)), width=width)
        else:
            self.d.line(drawn, fill=(*color, int(230 * a)), width=width, joint='curve')
    def finish(self):
        return self.im

def label(im, p, text, a, sub=None, dx=16, dy=-4, anchor='lm', size=28, color=G.INK):
    if a <= 0: return
    G.draw_text(im, (p[0] + dx, p[1] + dy), text, G.font('sans_b', size), color, a, anchor=anchor)
    if sub: G.draw_text(im, (p[0] + dx, p[1] + dy + size * 1.15), sub, G.font('italic', int(size * 0.95)), G.MUTED, a, anchor=anchor)

def chrome(im, title, sub, a, width_deg, lat, credit='Elevation: Copernicus GLO-90 DEM © DLR/Airbus (EU/ESA) · Vectors: Natural Earth'):
    d = ImageDraw.Draw(im, 'RGBA')
    grad = Image.new('L', (1, 260)); grad.putdata([int(200 * a * (i / 259) ** 1.4) for i in range(260)])
    band = Image.new('RGBA', (W, 260), (10, 8, 6, 0)); band.putalpha(grad.resize((W, 260)))
    im.paste(band, (0, H - 260), band)
    G.draw_text(im, (80, H - 120), title, G.font('title', 44), G.INK, a, anchor='lm', spacing=3)
    if sub: G.draw_text(im, (80, H - 70), sub, G.font('italic', 30), G.GOLD, a, anchor='lm')
    # scale bar (approximate at the view's centre latitude)
    km_per_px = width_deg * 111.32 * math.cos(math.radians(lat)) / W
    nice = [50, 100, 200, 250, 500, 1000]; km = min(nice, key=lambda k: abs(k / km_per_px - 220)); px = km / km_per_px
    x0, y0 = W - 120 - px, H - 80
    d.line([(x0, y0), (x0 + px, y0)], fill=(239, 230, 214, int(230 * a)), width=3)
    for xx in (x0, x0 + px): d.line([(xx, y0 - 8), (xx, y0 + 8)], fill=(239, 230, 214, int(230 * a)), width=3)
    G.draw_text(im, (x0 + px / 2, y0 - 22), f'{km} km (approx.)', G.font('sans', 20), G.INK, a)
    # north arrow
    nx, ny = W - 80, 90
    d.polygon([(nx, ny - 34), (nx - 12, ny + 6), (nx, ny - 4), (nx + 12, ny + 6)], fill=(239, 230, 214, int(230 * a)))
    G.draw_text(im, (nx, ny + 30), 'N', G.font('sans_b', 22), G.INK, a)
    G.draw_text(im, (W - 120, H - 36), credit, G.font('sans', 16), G.MUTED, a * 0.8, anchor='rm')

def frame(bm, cam, t):
    base = basemap(bm); M = view(bm, *cam)
    img = cv2.warpAffine(base, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return Image.fromarray(img), M

def rub_poly(M, bm):
    poly = geo_polys(WORK / 'data/ne/ne_10m_geography_regions_polys.geojson', 'AL KHALI')[0][0]
    return [to_frame(M, x, y, bm) for x, y in poly]

def ease_cam(c0, c1, u):
    u = G.sm(u); return tuple(lerp(a, b, u) for a, b in zip(c0, c1))

# ------------------------------------------------------------------ map shots
def m01(t, dur, step):
    bm = 'arabia'; cam = ease_cam((46.0, 21.5, 40), (49.0, 21.0, 31), t / dur)
    im, M = frame(bm, cam, t); ov = Overlay(); F = G.fade
    rp = rub_poly(M, bm); ov.poly(rp, F(t, dur * 0.35, 1.5))
    im = im.convert('RGBA'); im.alpha_composite(ov.finish()); im = im.convert('RGB')
    for name, (lat, lon), d in [('SAUDI ARABIA', (25.5, 44.0), 0.8), ('OMAN', (21.0, 57.2), 1.1), ('YEMEN', (15.6, 46.6), 1.4), ('U.A.E.', (23.6, 54.3), 1.7)]:
        G.draw_text(im, to_frame(M, lon, lat, bm), name, G.font('sans', 26), G.MUTED, F(t, d, 0.8), spacing=4)
    for name, (lat, lon) in [('RED SEA', (20.0, 38.6)), ('ARABIAN SEA', (15.5, 61.0)), ('GULF OF ADEN', (12.6, 47.5)), ('THE GULF', (27.0, 51.0))]:
        G.draw_text(im, to_frame(M, lon, lat, bm), name, G.font('italic', 28), (150, 170, 180), F(t, 1.0, 1.0))
    c = to_frame(M, 50.5, 20.0, bm); a = F(t, dur * 0.45, 1.2)
    G.draw_text(im, c, 'RUBʿ AL-KHĀLĪ', G.font('sans_b', 40), G.GOLD, a, spacing=6)
    G.draw_text(im, (c[0], c[1] + 46), 'the Empty Quarter  ·  c. 650,000 km²', G.font('italic', 32), G.INK, a)
    chrome(im, 'THE ARABIAN PENINSULA', None, F(t, 0.2, 0.8), cam[2], cam[1])
    return G.global_fade(im, t, dur, 0.4, 0.5)

def m03(t, dur, step):
    bm = 'arabia'; cam = ease_cam((47.5, 20.0, 30), (49.0, 16.6, 13.5), min(1, t / (dur * 0.6)))
    im, M = frame(bm, cam, t); ov = Overlay(); F = G.fade
    ov.poly(rub_poly(M, bm), 0.35, fa=25, la=90, width=2)
    c = to_frame(M, 49.2, 15.6, bm); s = M[0, 0] * BASEMAPS[bm][4] * COS
    ov.glow(c, 2.4 * s, 1.1 * s, F(t, dur * 0.45, 1.6))
    ov.pin(to_frame(M, P['al-Shihr'][1], P['al-Shihr'][0], bm), F(t, dur * 0.6, 0.8))
    im = im.convert('RGBA'); im.alpha_composite(ov.finish()); im = im.convert('RGB')
    a = F(t, dur * 0.6, 0.8)
    label(im, to_frame(M, P['al-Shihr'][1], P['al-Shihr'][0], bm), 'al-Shiḥr', a)
    label(im, to_frame(M, 48.2, 16.0, bm), 'ḤAḌRAMAWT', F(t, dur * 0.5, 0.8), dx=0, anchor='mm', size=30, color=G.GOLD)
    G.draw_text(im, to_frame(M, 51.0, 19.3, bm), 'Rubʿ al-Khālī', G.font('italic', 30), G.MUTED, F(t, 0.5, 1.0))
    chrome(im, 'AL-AḤQĀF — “THE WIND-CURVED SANDHILLS”', 'Placed by al-Ṭabarī (d. 923) in al-Shiḥr, in Ḥaḍramawt, and the lands around it', F(t, 0.2, 0.8), cam[2], cam[1])
    return G.global_fade(im, t, dur, 0.4, 0.5)

def m05(t, dur, step):
    bm = 'arabia'; cam = ease_cam((48.0, 22.5, 26), (50.0, 21.8, 16), t / dur)
    im, M = frame(bm, cam, t); ov = Overlay(); F = G.fade
    ov.poly(rub_poly(M, bm), 0.6, fa=35, la=140, width=2)
    pw = to_frame(M, P['Wabar'][1], P['Wabar'][0], bm); pr = to_frame(M, P['Riyadh'][1], P['Riyadh'][0], bm)
    ov.pin(pw, F(t, 1.2, 0.8), color=(216, 180, 122)); ov.pin(pr, F(t, 0.6, 0.8), r=5)
    im = im.convert('RGBA'); im.alpha_composite(ov.finish()); im = im.convert('RGB')
    label(im, pw, 'Wabar craters', F(t, 1.4, 0.8), sub='reached by H. St J. Philby, 2 Feb 1932')
    label(im, pr, 'Riyadh', F(t, 0.8, 0.8), size=24)
    chrome(im, 'THE SEARCH FOR WABĀR, 1932', 'Not a city: an iron-meteorite impact site', F(t, 0.2, 0.8), cam[2], cam[1])
    return G.global_fade(im, t, dur, 0.4, 0.5)

def m06(t, dur, step):
    bm = 'dhofar'; cam = ease_cam((54.05, 17.62, 4.0), (54.0, 17.6, 3.6), t / dur)
    im, M = frame(bm, cam, t); ov = Overlay(); F = G.fade
    pts = [('Salalah', None, 0.6, 'rm'), ('Khor Rori', 'Moscha · Sumhuram', 1.2, 'lm'), ('Al-Baleed', None, 1.6, 'lb'), ('Thumrait', None, 2.0, 'lm'), ('Shisr', 'caravan oasis (“Ubar”)', 2.6, 'lm')]
    for n, sub, d, an in pts:
        lat, lon = P[n]; ov.pin(to_frame(M, lon, lat, bm), F(t, d, 0.7), color=(216, 180, 122) if n == 'Shisr' else (239, 230, 214))
    im = im.convert('RGBA'); im.alpha_composite(ov.finish()); im = im.convert('RGB')
    for n, sub, d, an in pts:
        lat, lon = P[n]; p = to_frame(M, lon, lat, bm)
        if an == 'lb':
            label(im, p, n, F(t, d, 0.7), dx=12, dy=34, anchor='lm', size=26)
        else:
            label(im, p, n, F(t, d, 0.7), sub=sub, dx=-16 if an == 'rm' else 16, dy=-18 if an == 'rm' else -4, anchor=an, size=28)
    G.draw_text(im, to_frame(M, 55.0, 16.9, bm), 'ARABIAN SEA', G.font('italic', 30), (150, 170, 180), F(t, 0.4, 1.0))
    G.draw_text(im, to_frame(M, 52.6, 18.95, bm), 'towards the Rubʿ al-Khālī', G.font('italic', 28), G.MUTED, F(t, 0.8, 1.0))
    chrome(im, 'DHOFAR, SOUTHERN OMAN', 'The frankincense coast and its hinterland', F(t, 0.2, 0.8), cam[2], cam[1])
    return G.global_fade(im, t, dur, 0.4, 0.5)

ROUTE = ['Khor Rori', 'Qana', 'Shabwa', 'Najran', 'Mecca', 'Medina', 'Hegra', 'Petra', 'Gaza']
def m07(t, dur, step):
    bm = 'arabia'; cam = ease_cam((45.0, 22.0, 36), (43.0, 22.6, 40), t / dur)
    im, M = frame(bm, cam, t); ov = Overlay(); F = G.fade
    pts = [to_frame(M, P[n][1], P[n][0], bm) for n in ROUTE]
    u = G.sm((t - 0.8) / (dur * 0.7))
    ov.path(pts[:2], min(1, u * 8), F(t, 0.6, 0.6), dashed=True)
    if u > 0.12: ov.path(pts[1:], (u - 0.12) / 0.88, 1.0)
    for i, p in enumerate(pts): ov.pin(p, F(t, 0.6 + i * dur * 0.07, 0.5), r=5)
    im = im.convert('RGBA'); im.alpha_composite(ov.finish()); im = im.convert('RGB')
    for i, (n, p) in enumerate(zip(ROUTE, pts)):
        an = 'rm' if n in ('Qana', 'Shabwa', 'Najran', 'Mecca', 'Medina', 'Hegra', 'Petra', 'Gaza') else 'lm'
        label(im, p, n, F(t, 0.7 + i * dur * 0.07, 0.5), dx=-14 if an == 'rm' else 14, anchor=an, size=24)
    G.draw_text(im, to_frame(M, 52.0, 14.4, bm), 'by sea', G.font('italic', 24), G.MUTED, F(t, 1.2, 0.8))
    G.draw_text(im, to_frame(M, 32.5, 33.2, bm), 'MEDITERRANEAN', G.font('italic', 26), (150, 170, 180), F(t, 0.5, 1.0))
    chrome(im, 'THE INCENSE ROUTE', 'Simplified schematic — one of several routes; ports and stations after published reconstructions', F(t, 0.2, 0.8), cam[2], cam[1])
    return G.global_fade(im, t, dur, 0.4, 0.5)

def m09(t, dur, step):
    bm = 'arabia'; cam = (43.5, 22.9, 40)
    im, M = frame(bm, cam, t); ov = Overlay(); F = G.fade
    s = M[0, 0] * BASEMAPS[bm][4] * COS
    south = to_frame(M, 51.0, 16.8, bm); north = to_frame(M, P['Wadi Ramm'][1], P['Wadi Ramm'][0], bm)
    a_s = 1.0 if step >= 2 else F(t, 0.3, 1.0)
    ov.glow(south, 4.8 * s, 1.6 * s, a_s)
    if step == 1:
        u = G.sm((t - 1.2) / (dur * 0.55)); ov.path([south, ((south[0] + north[0]) / 2 + 60, (south[1] + north[1]) / 2), north], u, 1.0, dashed=True)
        ov.glow(north, 1.2 * s, 1.0 * s, F(t, dur * 0.7, 0.8), color=(127, 155, 181))
    else:
        ov.glow(north, 1.2 * s, 1.0 * s, 1.0, color=(127, 155, 181))
    ov.pin(north, F(t, dur * 0.6, 0.6) if step == 1 else 1.0, color=(127, 155, 181))
    im = im.convert('RGBA'); im.alpha_composite(ov.finish()); im = im.convert('RGB')
    a2 = F(t, 0.6, 0.8) if step >= 2 else 0
    label(im, north, 'Wadi Ramm (Wadi Rum)', F(t, dur * 0.65, 0.6) if step == 1 else 1.0, sub='inscriptions naming ʾrm (Iram) and ʿĀd' if step >= 2 else None)
    label(im, south, 'Southern Arabia', a_s, sub='classical tradition (al-Aḥqāf) · popular Shisr identification' if step >= 2 else 'classical tradition', dx=0, anchor='mm', color=G.GOLD)
    if step >= 2:
        G.draw_text(im, (W / 2 + 330, 470), 'IRAM — LOCATION UNKNOWN', G.font('sans_b', 34), G.INK, a2, spacing=6)
        G.draw_text(im, (W / 2 + 330, 515), 'two proposed regions, two kinds of evidence', G.font('italic', 30), G.MUTED, a2)
    chrome(im, 'A TURN TO THE NORTH', 'A recent epigraphic proposal (Al-Jallad, 2025)', F(t, 0.2, 0.8), cam[2], cam[1])
    return G.global_fade(im, t, dur, 0.4, 0.5)

REGISTRY = {'M01': m01, 'M03': m03, 'M05': m05, 'M06': m06, 'M07': m07, 'M09': m09}

def render(key, t, dur, step=0):
    return REGISTRY[key](t, dur, step)

if __name__ == '__main__':
    import sys
    out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    for k in (sys.argv[2:] or list(REGISTRY)):
        for st in ((1, 2) if k == 'M09' else (0,)):
            render(k, 9.0, 10.0, st).save(out / f'{k}_{st}.jpg', quality=88); print('ok', k, st)
