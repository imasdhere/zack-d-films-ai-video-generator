"""Typography cards and explanatory diagrams (1920x1080), rendered per frame with Pillow (+raqm for Arabic).
render(key, t, dur, step=0) -> PIL.Image (RGB). All text content is taken verbatim from the research files."""
import functools, math, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[2]
F = ROOT / 'assets/fonts'
W, H = 1920, 1080
GOLD = (216, 180, 122); INK = (239, 230, 214); MUTED = (168, 154, 133); DARK = (20, 17, 13)
EVIDENCE = {  # colour grammar used across the film
    'Q': ('QURANIC TEXT', (216, 180, 122)), 'H': ('AUTHENTIC HADITH', (201, 164, 106)),
    'C': ('CLASSICAL SCHOLARSHIP', (185, 163, 127)), 'L': ('LATER TRADITION / LEGEND', (176, 122, 90)),
    'A': ('ARCHAEOLOGY & DOCUMENTED HISTORY', (143, 163, 160)), 'S': ('SCIENTIFIC EVIDENCE / HYPOTHESIS', (127, 155, 181)),
    'R': ('ARTISTIC RECONSTRUCTION', (155, 139, 176)),
}

@functools.lru_cache(None)
def font(name, size):
    files = {'title': 'Cinzel[wght].ttf', 'serif': 'EBGaramond[wght].ttf', 'italic': 'EBGaramond-Italic[wght].ttf',
             'quran': 'AmiriQuran-Regular.ttf', 'arabic': 'Amiri-Regular.ttf', 'arabic_b': 'Amiri-Bold.ttf'}
    if name in ('sans', 'sans_b'):
        p = '/usr/share/fonts/opentype/inter/' + ('Inter-Regular.otf' if name == 'sans' else 'Inter-SemiBold.otf')
        return ImageFont.truetype(p, size, layout_engine=ImageFont.Layout.RAQM)
    f = ImageFont.truetype(str(F / files[name]), size, layout_engine=ImageFont.Layout.RAQM)
    if name == 'title':
        try: f.set_variation_by_axes([500])
        except Exception: pass
    return f

@functools.lru_cache(None)
def _tanzil():
    d = {}
    for line in open(ROOT / 'research/raw_sources/quran/quran-uthmani.txt', encoding='utf-8'):
        p = line.rstrip('\n').split('|', 2)
        if len(p) == 3 and p[0].isdigit(): d[(int(p[0]), int(p[1]))] = p[2]
    return d

def quran(s, a):
    """Verbatim Uthmani text from the archived Tanzil file (never retyped)."""
    return _tanzil()[(s, a)]

def split_at_pause(v):
    for mark in (' ۚ ', ' ۖ ', ' ۗ '):
        if mark in v:
            i = v.index(mark); return [v[:i + len(mark)].strip(), v[i + len(mark):].strip()]
    return [v]

def sm(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)

def fade(t, start, dur=0.8):
    return sm((t - start) / dur)

@functools.lru_cache(8)
def background(seed=1, tone=(26, 22, 17)):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W * 0.5) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
    base = np.array(tone, np.float32)[None, None, :] * (1.15 - 0.9 * r[..., None])
    n = rng.normal(0, 1, (H // 4, W // 4)).astype(np.float32)
    n = np.array(Image.fromarray(((n - n.min()) / (np.ptp(n) + 1e-6) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
    base = base * (0.92 + 0.16 * n[..., None])
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

_BG_CACHE = {}
def canvas(bg=None, dim=0.35, blur=6):
    if bg is not None:
        k = (id(bg), dim, blur)
        if k not in _BG_CACHE:
            im = bg.convert('RGB').resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur))
            _BG_CACHE[k] = Image.blend(Image.new('RGB', (W, H), DARK), im, dim)
        return _BG_CACHE[k].copy()
    return background().copy()

@functools.lru_cache(None)
def _cmap(path):
    from fontTools.ttLib import TTFont
    return set(TTFont(path).getBestCmap().keys())

def covered(fnt, text):
    return all(ord(c) in _cmap(fnt.path) for c in text if not c.isspace())

@functools.lru_cache(4096)
def _sprite(text, fpath, size, fill, anchor, direction, spacing):
    """Tight RGBA sprite of a text run at full opacity, plus the offset of the anchor point."""
    fnt = ImageFont.truetype(fpath, size, layout_engine=ImageFont.Layout.RAQM)
    if fpath.endswith('Cinzel[wght].ttf'):
        try: fnt.set_variation_by_axes([500])
        except Exception: pass
    pad = size * 2
    tmp = Image.new('RGBA', (1, 1)); d = ImageDraw.Draw(tmp)
    kw = {'direction': direction} if direction else {}
    if spacing:
        widths = [d.textlength(c, font=fnt) for c in text]; total = int(sum(widths) + spacing * (len(text) - 1))
        im = Image.new('RGBA', (total + pad * 2, size * 3 + pad), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = pad
        for c, w_ in zip(text, widths):
            dd.text((x, pad + size), c, font=fnt, fill=(*fill, 255), anchor='l' + anchor[1]); x += w_ + spacing
        ox = pad + (total / 2 if anchor[0] == 'm' else 0 if anchor[0] == 'l' else total); oy = pad + size
    else:
        bb = d.textbbox((0, 0), text, font=fnt, anchor=anchor, **kw)
        w_, h_ = bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2
        im = Image.new('RGBA', (int(w_), int(h_)), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
        ox, oy = pad - bb[0], pad - bb[1]
        dd.text((ox, oy), text, font=fnt, fill=(*fill, 255), anchor=anchor, **kw)
    bbox = im.getbbox() or (0, 0, 1, 1); im = im.crop(bbox)
    return im, ox - bbox[0], oy - bbox[1]

def draw_text(im, xy, text, fnt, fill=INK, alpha=1.0, anchor='mm', direction=None, spacing=0):
    if alpha <= 0.01 or not text: return
    if not covered(fnt, text):   # e.g. Cinzel lacks dotted transliteration letters -> EB Garamond
        fnt = font('serif', fnt.size)
    spr, ox, oy = _sprite(text, fnt.path, fnt.size, tuple(int(c) for c in fill), anchor, direction, spacing)
    if alpha < 0.995:
        a = spr.getchannel('A').point(lambda v: int(v * alpha)); spr = spr.copy(); spr.putalpha(a)
    x, y = int(round(xy[0] - ox)), int(round(xy[1] - oy))
    if im.mode == 'RGBA':
        im.alpha_composite(spr, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))
    else:
        im.paste(spr, (x, y), spr)

def wrap(text, fnt, width):
    d = ImageDraw.Draw(Image.new('RGB', (10, 10))); words = text.split(); lines = []; cur = ''
    for w_ in words:
        t = (cur + ' ' + w_).strip()
        if d.textlength(t, font=fnt) <= width: cur = t
        else: lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

def para(im, x, y, text, fnt, width, fill=INK, alpha=1.0, lh=1.35, anchor='ma'):
    for i, ln in enumerate(wrap(text, fnt, width)):
        draw_text(im, (x, y + i * fnt.size * lh), ln, fnt, fill, alpha, anchor=anchor)
    return y + len(wrap(text, fnt, width)) * fnt.size * lh

def rule(im, y, alpha, w=360, color=GOLD):
    d = ImageDraw.Draw(im, 'RGBA'); d.line([(W / 2 - w / 2, y), (W / 2 + w / 2, y)], fill=(*color, int(200 * alpha)), width=2)

def global_fade(im, t, dur, fin=0.7, fout=0.7):
    a = min(fade(t, 0, fin), 1 - fade(t, dur - fout, fout))
    return Image.blend(Image.new('RGB', im.size, (0, 0, 0)), im, max(0.0, a)) if a < 1 else im

# ------------------------------------------------------------------ cards
def g_title(t, dur, step, bg=None):
    im = canvas(bg, 0.55, 2)
    a = fade(t, 0.6, 1.6)
    draw_text(im, (W / 2, 470), 'THE LOST CITY OF IRAM', font('title', 104), INK, a, spacing=10)
    rule(im, 548, fade(t, 1.4, 1.2), 420)
    draw_text(im, (W / 2, 610), 'In Search of the People of the Pillars', font('italic', 52), GOLD, fade(t, 2.0, 1.4))
    return global_fade(im, t, dur, 0.01, 1.2)

def g_chapter(t, dur, step, bg=None, number='', title=''):
    im = canvas(bg, 0.45, 3)
    draw_text(im, (W / 2, 470), f'CHAPTER {number}', font('sans', 30), GOLD, fade(t, 0.3, 1.0), spacing=8)
    draw_text(im, (W / 2, 560), title, font('title', 84), INK, fade(t, 0.7, 1.2), spacing=4)
    return global_fade(im, t, dur, 0.4, 1.0)

def verse_card(t, dur, arabic_lines, english, ref, bg=None):
    im = canvas(bg, 0.25, 8)
    y = 250
    for i, ln in enumerate(arabic_lines):
        draw_text(im, (W / 2, y + i * 120), ln, font('quran', 78), GOLD, fade(t, 0.4 + i * 1.1, 1.0), direction='rtl')
    yb = y + len(arabic_lines) * 120 + 40
    rule(im, yb, fade(t, 0.8 + len(arabic_lines) * 1.1, 1.0), 300)
    ye = para(im, W / 2, yb + 40, english, font('italic', 44), 1400, INK, fade(t, 1.2 + len(arabic_lines) * 1.1, 1.2))
    draw_text(im, (W / 2, min(ye + 50, 990)), ref, font('sans', 24), MUTED, fade(t, 2.0 + len(arabic_lines), 1.0), spacing=2)
    return global_fade(im, t, dur)

def g_q89(t, dur, step, bg=None):
    return verse_card(t, dur, [quran(89, 6), quran(89, 7), quran(89, 8)],
                      '“Dost thou not consider how thy Lord dealt with (the tribe of) A’ad, with many-columned Iram, the like of which was not created in the lands;”',
                      'QURʾĀN 89:6–8  ·  ARABIC: TANZIL UTHMANI TEXT  ·  TRANSLATION: M. M. PICKTHALL (1930)', bg)

def g_q46(t, dur, step, bg=None):
    return verse_card(t, dur, split_at_pause(quran(46, 24)),
                      '“Then, when they beheld it as a dense cloud coming toward their valleys, they said: Here is a cloud bringing us rain. Nay, but it is that which ye did seek to hasten, a wind wherein is painful torment, destroying all things by commandment of its Lord. And morning found them so that naught could be seen save their dwellings.”',
                      'QURʾĀN 46:24–25 (ARABIC: 46:24)  ·  ARABIC: TANZIL  ·  TRANSLATION: M. M. PICKTHALL (1930)', bg)

def g_imad(t, dur, step, bg=None):
    im = canvas(bg, 0.2, 10)
    draw_text(im, (W / 2, 330), 'ٱلْعِمَاد', font('quran', 170), GOLD, fade(t, 0.3, 1.2), direction='rtl')
    draw_text(im, (W / 2, 545), 'al-ʿimād', font('italic', 56), INK, fade(t, 1.0, 1.0))
    words = ['columns', 'pillars', 'the poles of a tent']
    xs = [W / 2 - 520, W / 2, W / 2 + 520]
    for i, (w_, x) in enumerate(zip(words, xs)):
        draw_text(im, (x, 680), w_, font('serif', 52), INK, fade(t, 2.0 + i * 0.9, 0.8))
    for i in range(2):
        draw_text(im, ((xs[i] + xs[i + 1]) / 2, 680), '·', font('serif', 52), GOLD, fade(t, 2.4 + i * 0.9, 0.8))
    draw_text(im, (W / 2, 820), 'One Arabic word, several possible meanings', font('sans', 26), MUTED, fade(t, 4.6, 1.0), spacing=2)
    return global_fade(im, t, dur)

def g_questions(t, dur, step, bg=None):
    im = canvas(bg, 0.25, 8)
    qs = ['What does the text actually say?', 'What did the earliest scholars understand by it?', 'What, if anything, has archaeology really found?']
    for i, q in enumerate(qs):
        a = fade(t, 0.5 + i * (dur / 3.6), 0.9)
        draw_text(im, (W / 2 - 560, 380 + i * 140), f'{i + 1}', font('title', 64), GOLD, a, anchor='mm')
        draw_text(im, (W / 2 - 490, 380 + i * 140), q, font('serif', 54), INK, a, anchor='lm')
    return global_fade(im, t, dur)

def g_evidence_key(t, dur, step, bg=None):
    im = canvas(bg, 0.2, 10)
    draw_text(im, (W / 2, 170), 'HOW EVIDENCE IS MARKED IN THIS FILM', font('sans', 30), GOLD, fade(t, 0.2, 0.8), spacing=6)
    keys = ['Q', 'H', 'C', 'L', 'A', 'S', 'R']
    d = ImageDraw.Draw(im, 'RGBA')
    per = (dur - 2.5) / len(keys)
    for i, k in enumerate(keys):
        name, col = EVIDENCE[k]; a = fade(t, 0.8 + i * per, 0.6); y = 280 + i * 92
        d.rounded_rectangle([W / 2 - 430, y - 22, W / 2 - 386, y + 22], 8, fill=(*col, int(255 * a)))
        draw_text(im, (W / 2 - 350, y), name, font('sans_b', 34), INK, a, anchor='lm')
    return global_fade(im, t, dur)

def g_count(t, dur, step, bg=None):
    im = canvas(bg, 0.2, 10)
    n1 = int(round(24 * sm((t - 0.5) / 2.4)))
    draw_text(im, (W / 2 - 330, 470), f'{n1}', font('title', 220), GOLD, fade(t, 0.3, 0.6))
    draw_text(im, (W / 2 - 330, 650), 'ʿĀd', font('serif', 64), INK, fade(t, 0.3, 0.6))
    draw_text(im, (W / 2 + 330, 470), '1', font('title', 220), GOLD, fade(t, 3.2, 0.8))
    draw_text(im, (W / 2 + 330, 650), 'Iram', font('serif', 64), INK, fade(t, 3.2, 0.8))
    draw_text(im, (W / 2, 820), 'NAMED IN THE QURʾĀN  ·  ʿĀD: 24 OCCURRENCES IN 23 VERSES  ·  IRAM: 89:7 ONLY', font('sans', 24), MUTED, fade(t, 3.8, 1.0), spacing=2)
    return global_fade(im, t, dur)

def two_col(t, dur, title, cols, foot, bg=None):
    im = canvas(bg, 0.2, 10)
    draw_text(im, (W / 2, 190), title, font('sans', 30), GOLD, fade(t, 0.2, 0.8), spacing=6)
    for i, (head, lines) in enumerate(cols):
        x = W / 2 + (-430 if i == 0 else 430); a = fade(t, 0.8 + i * 2.0, 1.0)
        draw_text(im, (x, 300), head, font('sans_b', 30), INK, a)
        y = 380
        for ln in lines:
            y = para(im, x, y, ln, font('italic', 46), 720, INK, a) + 30
    d = ImageDraw.Draw(im, 'RGBA'); d.line([(W / 2, 280), (W / 2, 760)], fill=(*GOLD, 120), width=1)
    draw_text(im, (W / 2, 900), foot, font('sans', 24), MUTED, fade(t, 4.5, 1.0), spacing=2)
    return global_fade(im, t, dur)

def g_translations(t, dur, step, bg=None):
    return two_col(t, dur, 'ONE VERSE, TWO TRANSLATIONS  ·  QURʾĀN 89:7–8',
                   [('M. M. PICKTHALL (1930)', ['“With many-columned Iram,', 'The like of which was not created in the lands;”']),
                    ('SAHEEH INTERNATIONAL (1997)', ['“[With] Iram — who had lofty pillars,', 'The likes of whom had never been created in the land?”'])],
                   'A PLACE (“WHICH”) OR A PEOPLE (“WHOM”)?  THE ARABIC ALLOWS THE QUESTION', bg)

def branches(t, dur, center, center_sub, items, highlight=None, title='', foot='', bg=None):
    im = canvas(bg, 0.2, 10)
    draw_text(im, (W / 2, 140), title, font('sans', 28), GOLD, fade(t, 0.1, 0.8), spacing=5)
    cx, cy = W / 2, 470
    draw_text(im, (cx, cy - 20), center, font('serif', 76), INK, fade(t, 0.3, 0.8))
    draw_text(im, (cx, cy + 45), center_sub, font('sans', 22), MUTED, fade(t, 0.5, 0.8), spacing=2)
    n = len(items); d = ImageDraw.Draw(im, 'RGBA'); per = max(0.8, (dur - 3.0) / n)
    for i, (txt, who) in enumerate(items):
        ang = math.pi * (0.15 + 0.7 * i / max(1, n - 1)); left = i % 2 == 0
        x = cx + (-560 if left else 560); y = 300 + (i // 2) * 210 + (0 if left else 100)
        a = fade(t, 1.0 + i * per, 0.7)
        hl = highlight is not None and i == highlight
        col = GOLD if hl else INK
        d.line([(cx + (-180 if left else 180), cy), (x + (200 if left else -200), y)], fill=(*GOLD, int(110 * a)), width=2)
        draw_text(im, (x, y - 14), txt, font('serif', 44 if hl else 40), col, a)
        draw_text(im, (x, y + 30), who, font('italic', 30), MUTED, a)
        if hl:
            d.rounded_rectangle([x - 330, y - 52, x + 330, y + 62], 14, outline=(*GOLD, int(220 * a)), width=3)
    draw_text(im, (W / 2, 990), foot, font('sans', 22), MUTED, fade(t, 2.0, 1.0), spacing=2)
    return global_fade(im, t, dur)

def g_opinions_iram(t, dur, step, bg=None):
    items = [('A city: Alexandria', 'al-Quraẓī'), ('A city: Damascus', 'al-Maqburī'), ('A nation', 'Mujāhid'),
             ('A clan of ʿĀd — “the royal house of ʿĀd”', 'Qatāda'), ('An ancestor of ʿĀd', 'Ibn Isḥāq'), ('A tribe of ʿĀd', 'al-Ṭabarī’s preferred view')]
    return branches(t if step < 2 else t + 12, dur if step < 2 else dur + 12, 'Iram', 'Q 89:7', items, highlight=5 if step >= 2 else None,
                    title='WHAT IS “IRAM”?  OPINIONS REPORTED BY AL-ṬABARĪ (d. 923)', foot='SOURCE: AL-ṬABARĪ, JĀMIʿ AL-BAYĀN, ON Q 89:7  ·  ARABIC TEXT ARCHIVED IN RESEARCH FILES', bg=bg)

def g_opinions_imad(t, dur, step, bg=None):
    items = [('Their great height', 'Ibn ʿAbbās; Mujāhid'), ('A building on tall columns', 'Ibn Zayd'), ('Strength and power', 'al-Ḍaḥḥāk'),
             ('Poles of tents — a travelling people', 'Mujāhid; Qatāda · preferred by al-Ṭabarī')]
    return branches(t, dur, 'dhāt al-ʿimād', 'Q 89:7', items, highlight=3 if t > dur * 0.62 else None,
                    title='WHAT ARE THE “PILLARS”?  OPINIONS REPORTED BY AL-ṬABARĪ', foot='SOURCE: AL-ṬABARĪ, JĀMIʿ AL-BAYĀN, ON Q 89:7', bg=bg)

def quote_card(t, dur, arabic, english, attribution, note, bg=None):
    im = canvas(bg, 0.2, 10)
    y = 330
    if arabic:
        for i, ln in enumerate(arabic):
            draw_text(im, (W / 2, y + i * 100), ln, font('arabic', 66), GOLD, fade(t, 0.3 + i * 0.6, 1.0), direction='rtl')
        y += len(arabic) * 100 + 30
        rule(im, y, fade(t, 1.0, 1.0), 260); y += 50
    y = para(im, W / 2, y, english, font('italic', 50), 1400, INK, fade(t, 1.6, 1.2))
    draw_text(im, (W / 2, y + 50), attribution, font('sans', 26), MUTED, fade(t, 2.6, 1.0), spacing=2)
    if note: draw_text(im, (W / 2, y + 95), note, font('sans', 20), MUTED, fade(t, 3.0, 1.0) * 0.8, spacing=2)
    return global_fade(im, t, dur)

def g_tabari_quote(t, dur, step, bg=None):
    return quote_card(t, dur, ['ولا يعلم بناء كان لهم بالعماد بخبر صحيح'],
                      '“No building of theirs with columns is known through any authentic report.”',
                      'AL-ṬABARĪ (d. 923), JĀMIʿ AL-BAYĀN, ON QURʾĀN 89:7', 'ENGLISH: PRODUCTION TRANSLATION OF THE ARABIC ABOVE', bg)

def g_ibnkathir_quote(t, dur, step, bg=None):
    return quote_card(t, dur, ['فهم قبيلة وأمة من الأمم'],
                      '“…they were a tribe, a nation among the nations.”',
                      'IBN KATHĪR (d. 1373), TAFSĪR AL-QURʾĀN AL-ʿAẒĪM, ON QURʾĀN 89:8', 'ENGLISH: PRODUCTION TRANSLATION', bg)

def g_ibnkathir_reject(t, dur, step, bg=None):
    return quote_card(t, dur, ['فإن هذا كله من خرافات الإسرائيليين', 'فهذه الحكاية ليس يصح إسنادها'],
                      '“All of this is among the fables of the Israʾīliyyāt.” … “This tale does not have a sound chain of transmission.”',
                      'IBN KATHĪR, TAFSĪR, ON QURʾĀN 89:8 — ON THE GOLDEN CITY AND THE STORY OF IBN QILĀBA', 'ENGLISH: PRODUCTION TRANSLATION', bg)

def g_thomas_quote(t, dur, step, bg=None):
    return quote_card(t, dur, None, '“On my previous journeys I had heard from other Arabs of the name of this Atlantis of the Sands, but none could tell me of even an approximate location.”',
                      'BERTRAM THOMAS, GEOGRAPHICAL JOURNAL, 1931', 'THE PHRASE IS OFTEN CREDITED TO T. E. LAWRENCE; IT DOES NOT APPEAR IN HIS PUBLISHED WORKS', bg)

def g_zarins_quote(t, dur, step, bg=None):
    return quote_card(t, dur, None, '“If you look at the classical texts and the Arab historical sources, Ubar refers to a region and a group of people, not to a specific town.”',
                      'JURIS ZARINS, ARCHAEOLOGIST, INTERVIEW FOR PBS NOVA, 1996', None, bg)

def g_headline(t, dur, step, bg=None):
    im = canvas(bg, 0.2, 10)
    draw_text(im, (W / 2, 300), 'FEBRUARY 1992', font('title', 90), GOLD, fade(t, 0.3, 1.0), spacing=8)
    y = para(im, W / 2, 420, '“Guided by ancient maps and sharp-eyed surveys from space, archaeologists and explorers have discovered a lost city deep in the sands of Arabia, and they are virtually sure it is Ubar…”', font('italic', 46), 1400, INK, fade(t, 1.2, 1.2))
    draw_text(im, (W / 2, y + 50), 'THE NEW YORK TIMES, 5 FEBRUARY 1992', font('sans', 26), MUTED, fade(t, 2.2, 1.0), spacing=3)
    return global_fade(im, t, dur)

def g_edgell(t, dur, step, bg=None):
    im = canvas(bg, 0.2, 10)
    draw_text(im, (W / 2, 330), 'A PUBLISHED CRITIQUE  ·  2004', font('sans', 30), GOLD, fade(t, 0.2, 0.8), spacing=6)
    draw_text(im, (W / 2, 460), 'H. Stewart Edgell', font('serif', 64), INK, fade(t, 0.6, 1.0))
    para(im, W / 2, 540, '“The myth of the ‘lost city of the Arabian Sands’”', font('italic', 56), 1500, INK, fade(t, 1.0, 1.0))
    draw_text(im, (W / 2, 700), 'PROCEEDINGS OF THE SEMINAR FOR ARABIAN STUDIES 34 (2004): 105–120', font('sans', 24), MUTED, fade(t, 1.6, 1.0), spacing=2)
    return global_fade(im, t, dur)

def g_aljallad(t, dur, step, bg=None):
    im = canvas(bg, 0.2, 10)
    draw_text(im, (W / 2, 330), 'A RECENT SCHOLARLY PROPOSAL  ·  2025', font('sans', 30), (127, 155, 181), fade(t, 0.2, 0.8), spacing=6)
    draw_text(im, (W / 2, 460), 'Ahmad Al-Jallad', font('serif', 64), INK, fade(t, 0.6, 1.0))
    para(im, W / 2, 540, '“The Epigraphy of the Tribe of ʿĀd”', font('italic', 60), 1500, INK, fade(t, 1.0, 1.0))
    draw_text(im, (W / 2, 680), 'ATHĪRAT: JOURNAL OF ANCIENT ARABIA 1 (2025): 281–289', font('sans', 24), MUTED, fade(t, 1.6, 1.0), spacing=2)
    draw_text(im, (W / 2, 740), 'PRE-ISLAMIC INSCRIPTIONS BY MEMBERS OF A TRIBE CALLED ʿĀD, IN THE NORTHERN DESERTS', font('sans', 22), MUTED, fade(t, 2.2, 1.0), spacing=2)
    return global_fade(im, t, dur)

def g_three_tiers(t, dur, step, bg=None):
    im = canvas(bg, 0.2, 10); d = ImageDraw.Draw(im, 'RGBA')
    tiers = [('POPULAR IDENTIFICATION', 'a story people choose to tell'), ('ARCHAEOLOGICAL INTERPRETATION', 'an argument from evidence'), ('ESTABLISHED CONCLUSION', 'what survives testing')]
    for i, (a_, b_) in enumerate(tiers):
        a = fade(t, 0.5 + i * (dur / 5), 0.8); y = 720 - i * 190; w = 1100 - i * 220
        d.rounded_rectangle([W / 2 - w / 2, y - 70, W / 2 + w / 2, y + 70], 16, fill=(60 + i * 10, 52 + i * 8, 40 + i * 6, int(200 * a)), outline=(*GOLD, int(180 * a)), width=2)
        draw_text(im, (W / 2, y - 18), a_, font('sans_b', 34), INK, a, spacing=4)
        draw_text(im, (W / 2, y + 28), b_, font('italic', 32), MUTED, a)
    a = fade(t, dur * 0.72, 1.0)
    d.rounded_rectangle([W / 2 + 620, 690, W / 2 + 900, 750], 12, fill=(176, 122, 90, int(230 * a)))
    draw_text(im, (W / 2 + 760, 720), 'Shisr = Iram', font('sans_b', 30), INK, a)
    return global_fade(im, t, dur)

def g_hadith(t, dur, arabic, english, ref, bg=None):
    return quote_card(t, dur, arabic, english, ref, 'AUTHENTIC HADITH  ·  TEXT AS PUBLISHED ON SUNNAH.COM', bg)

def g_hadith_aisha(t, dur, step, bg=None):
    return g_hadith(t, dur, ['عُذِّبَ قَوْمٌ بِالرِّيحِ، وَقَدْ رَأَى قَوْمٌ الْعَذَابَ فَقَالُوا هَذَا عَارِضٌ مُمْطِرُنَا'],
                    '“…some people were punished with a wind. Verily, some people saw the punishment, but they said, ‘This cloud will give us rain.’”',
                    'ṢAḤĪḤ AL-BUKHĀRĪ 4828–4829  ·  ṢAḤĪḤ MUSLIM 899  ·  NARRATED BY ʿĀʾISHA', bg)

def g_hadith_saba(t, dur, step, bg=None):
    return g_hadith(t, dur, ['نُصِرْتُ بِالصَّبَا، وَأُهْلِكَتْ عَادٌ بِالدَّبُورِ'],
                    '“I was granted victory with As-Saba (the east wind), and the nation of ʿĀd was destroyed by Ad-Dabur (the west wind).”',
                    'ṢAḤĪḤ AL-BUKHĀRĪ 1035  ·  ṢAḤĪḤ MUSLIM 900  ·  NARRATED BY IBN ʿABBĀS', bg)

def g_science_divider(t, dur, step, bg=None):
    im = canvas(bg, 0.15, 12); d = ImageDraw.Draw(im, 'RGBA')
    a1 = fade(t, 0.3, 1.0); a2 = fade(t, 1.3, 1.0)
    draw_text(im, (W / 2 - 420, 470), 'RELIGIOUS ACCOUNT', font('sans_b', 34), EVIDENCE['Q'][1], a1, spacing=4)
    draw_text(im, (W / 2 - 420, 530), 'meaning, judgement, memory', font('italic', 34), MUTED, a1)
    draw_text(im, (W / 2 + 420, 470), 'PHYSICAL EVIDENCE', font('sans_b', 34), EVIDENCE['S'][1], a2, spacing=4)
    draw_text(im, (W / 2 + 420, 530), 'climate, landscape, dates', font('italic', 34), MUTED, a2)
    d.line([(W / 2, 380), (W / 2, 620)], fill=(*GOLD, int(160 * fade(t, 2.0, 1.0))), width=2)
    draw_text(im, (W / 2, 760), 'DIFFERENT QUESTIONS, ANSWERED DIFFERENTLY', font('sans', 26), MUTED, fade(t, 2.6, 1.0), spacing=4)
    return global_fade(im, t, dur)

def g_holocene(t, dur, step, bg=None):
    im = canvas(bg, 0.15, 12); d = ImageDraw.Draw(im, 'RGBA')
    x0, x1, y = 260, 1660, 560
    a = fade(t, 0.3, 1.0)
    d.line([(x0, y), (x1, y)], fill=(*INK, int(200 * a)), width=3)
    for k in (10000, 8000, 6000, 4000, 2000, 0):
        x = x0 + (10000 - k) / 10000 * (x1 - x0)
        d.line([(x, y - 12), (x, y + 12)], fill=(*INK, int(200 * a)), width=2)
        draw_text(im, (x, y + 50), f'{k:,}' if k else 'today', font('sans', 26), MUTED, a)
    draw_text(im, (W / 2, y + 110), 'YEARS AGO', font('sans', 22), MUTED, a, spacing=4)
    # qualitative annotation only (no plotted data)
    p = sm((t - 1.2) / 2.5); xm = x0 + 0.2 * (x1 - x0)
    d.rounded_rectangle([x0, y - 190, x0 + (xm - x0) * p, y - 130], 10, fill=(127, 155, 181, int(200 * a)))
    draw_text(im, (x0 + 10, y - 230), 'Stronger monsoon rains (early Holocene)', font('serif', 36), INK, fade(t, 1.5, 1.0), anchor='lm')
    a3 = fade(t, 3.2, 1.0)
    draw_text(im, (xm + 20, y - 80), 'after about 8,000 years ago: a gradual decline', font('italic', 36), INK, a3, anchor='lm')
    d.line([(xm, y - 130), (xm, y)], fill=(*GOLD, int(220 * a3)), width=3)
    draw_text(im, (W / 2, 840), 'QUNF CAVE, DHOFAR — FLEITMANN ET AL., SCIENCE 300 (2003): 1737–1739  ·  SCHEMATIC, NOT A DATA PLOT', font('sans', 22), MUTED, fade(t, 3.8, 1.0), spacing=2)
    return global_fade(im, t, dur)

SUMMARY = [('Q', 'THE QURʾĀN', 'A people named ʿĀd and their prophet Hūd; their strength and building; a wind that left only their dwellings. Iram named once: dhāt al-ʿimād.'),
           ('C', 'CLASSICAL SCHOLARS', 'Al-Ṭabarī and Ibn Kathīr: Iram most likely a tribe; its ʿimād the poles of tents. The golden city rejected as legend.'),
           ('A', 'ARCHAEOLOGY', 'A caravan fortress at Shisr; frankincense ports on the coast; northern inscriptions naming Iram and a tribe called ʿĀd. No city of a thousand pillars.'),
           ('S', 'HYPOTHESES', 'Shisr as Ubar, and Ubar as Iram (popular, not accepted); Wadi Ramm in the north (a recent proposal).'),
           ('L', 'UNKNOWN', 'When ʿĀd lived. Exactly where. What their pillars really were.')]

def g_summary(t, dur, step, bg=None):
    im = canvas(bg, 0.15, 12); d = ImageDraw.Draw(im, 'RGBA')
    draw_text(im, (W / 2, 120), 'WHAT WE CAN ACTUALLY SAY', font('sans', 32), GOLD, 1.0 if step > 0 else fade(t, 0.3, 1.0), spacing=6)
    for i, (k, head, txt) in enumerate(SUMMARY):
        if i >= step and not (step == 4 and i == 4): continue
        if step == 4 and i == 3: pass
        a = 1.0 if i < step - (0 if step < 4 else 1) else fade(t, 0.3, 1.0)
        if step == 4 and i == 4: a = fade(t, 0.3, 1.0)
        y = 220 + i * 165; col = EVIDENCE[k][1]
        d.rounded_rectangle([170, y, 190, y + 120], 6, fill=(*col, int(255 * a)))
        draw_text(im, (220, y + 22), head, font('sans_b', 30), col, a, anchor='lm', spacing=0)
        para(im, 220, y + 52, txt, font('serif', 36), 1520, INK, a, lh=1.25, anchor='la')
    return global_fade(im, t, dur, 0.5, 0.6)

def g_credits(t, dur, step, bg=None):
    lines = [('title', 'THE LOST CITY OF IRAM'), ('italic', 'In Search of the People of the Pillars'), ('gap', ''),
             ('head', 'PRIMARY TEXTS'), ('body', 'Qurʾān: Tanzil Uthmani text (CC BY 3.0) · Translation: M. M. Pickthall (1930)'),
             ('body', 'Hadith: Ṣaḥīḥ al-Bukhārī 1035, 4828–4829; Ṣaḥīḥ Muslim 899, 900 (sunnah.com)'),
             ('body', 'Tafsīr al-Ṭabarī and Tafsīr Ibn Kathīr on Q 89:6–8 (Arabic text, quran.com)'), ('gap', ''),
             ('head', 'SCHOLARSHIP AND SCIENCE'), ('body', 'Blom, Crippen, Elachi, Clapp, Hedges & Zarins (2007) · Edgell (2004) · Al-Jallad (2025)'),
             ('body', 'Fleitmann et al., Science (2003) · Zaki et al., Communications Earth & Environment (2025)'),
             ('body', 'Periplus of the Erythraean Sea (tr. Schoff, 1912) · Pliny, Natural History 12 · UNESCO WHC 1010 & 1377'), ('gap', ''),
             ('head', 'IMAGES'), ('body', 'NASA/JPL (PIA01721, PIA01302) · NASA/METI ASTER · Wikimedia Commons contributors (see on-screen credits)'),
             ('body', 'Elevation: Copernicus GLO-90 DEM © DLR / Airbus, provided under COPERNICUS by the EU and ESA · Natural Earth'), ('gap', ''),
             ('head', 'ABOUT THE IMAGES IN THIS FILM'),
             ('body', 'Scenes marked ARTISTIC RECONSTRUCTION, LEGEND or ILLUSTRATIVE were generated with AI (SDXL) or 3D software (Blender).'),
             ('body', 'They are interpretations, not photographs of any excavated site. The Prophet Hūd is not depicted.'), ('gap', ''),
             ('head', 'NARRATION'), ('body', 'Synthetic voice: Qwen3-TTS (Apache-2.0) · No music is used in this film'), ('gap', ''),
             ('body', 'Full sources: research/bibliography.md and research/claim_verification_matrix.csv')]
    im = background().copy()
    total_h = sum(110 if k == 'title' else 70 if k == 'gap' else 58 for k, _ in lines)
    y = H + 40 - (t / dur) * (total_h + H * 0.9)
    for k, txt in lines:
        if k == 'title': draw_text(im, (W / 2, y), txt, font('title', 70), INK, 1, spacing=6); y += 110
        elif k == 'italic': draw_text(im, (W / 2, y - 30), txt, font('italic', 40), GOLD, 1); y += 58
        elif k == 'gap': y += 70
        elif k == 'head': draw_text(im, (W / 2, y), txt, font('sans', 26), GOLD, 1, spacing=6); y += 58
        else: draw_text(im, (W / 2, y), txt, font('serif', 32), INK, 1); y += 58
    return global_fade(im, t, dur, 1.0, 1.5)

REGISTRY = {'G_TITLE': g_title, 'G_Q89': g_q89, 'G_Q46': g_q46, 'G_IMAD': g_imad, 'G_QUESTIONS': g_questions, 'G_EVIDENCE_KEY': g_evidence_key,
            'G_COUNT': g_count, 'G_TRANSLATIONS': g_translations, 'G_OPINIONS_IRAM': g_opinions_iram, 'G_OPINIONS_IMAD': g_opinions_imad,
            'G_TABARI_QUOTE': g_tabari_quote, 'G_IBNKATHIR_QUOTE': g_ibnkathir_quote, 'G_IBNKATHIR_REJECT': g_ibnkathir_reject,
            'G_THOMAS_QUOTE': g_thomas_quote, 'G_ZARINS_QUOTE': g_zarins_quote, 'G_HEADLINE': g_headline, 'G_EDGELL': g_edgell,
            'G_ALJALLAD': g_aljallad, 'G_THREE_TIERS': g_three_tiers, 'G_HADITH_AISHA': g_hadith_aisha, 'G_HADITH_SABA': g_hadith_saba,
            'G_SCIENCE_DIVIDER': g_science_divider, 'G_HOLOCENE': g_holocene, 'G_SUMMARY': g_summary, 'G_CREDITS': g_credits}

def render(key, t, dur, step=0, bg=None, **kw):
    if key.startswith('G_CHAPTER'):
        return g_chapter(t, dur, step, bg, **kw)
    return REGISTRY[key](t, dur, step, bg)

if __name__ == '__main__':
    import sys
    out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    keys = sys.argv[2:] or list(REGISTRY)
    for k in keys:
        dur = 12.0; im = render(k, dur * 0.8, dur, step=4 if k == 'G_SUMMARY' else 2)
        im.save(out / f'{k}.jpg', quality=88); print('ok', k)
