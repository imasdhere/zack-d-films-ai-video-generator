"""Thumbnail (1920x1080 JPEG + 1280x720): a real-looking dune landscape with the title.
A landscape is used, not a reconstruction, so the key art does not suggest that a city was found."""
import pathlib, sys
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/animation')); import graphics as G
src = ROOT / 'assets/images' / (sys.argv[1] if len(sys.argv) > 1 else 'D18.png')
im = Image.open(src).convert('RGB').resize((1920, 1097), Image.LANCZOS).crop((0, 8, 1920, 1088))
im = ImageEnhance.Contrast(im).enhance(1.08)
a = np.array(im).astype(np.float32)
y = np.linspace(0, 1, 1080)[:, None, None]; x = np.linspace(-1, 1, 1920)[None, :, None]
a *= (1 - 0.55 * np.clip((y - 0.35) / 0.65, 0, 1) ** 1.2) * (1 - 0.25 * x ** 2)
im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
G.draw_text(im, (960, 690), 'THE LOST CITY OF IRAM', G.font('title', 118), G.INK, 1.0, spacing=10)
G.draw_text(im, (960, 790), 'In Search of the People of the Pillars', G.font('italic', 58), G.GOLD, 1.0)
G.draw_text(im, (960, 870), 'SCRIPTURE  ·  SCHOLARSHIP  ·  ARCHAEOLOGY  ·  WHAT REMAINS UNKNOWN', G.font('sans', 26), G.INK, 0.85, spacing=4)
out = ROOT / 'renders/final'; out.mkdir(parents=True, exist_ok=True)
im.save(out / 'thumbnail.jpg', quality=92); im.resize((1280, 720), Image.LANCZOS).save(out / 'thumbnail_1280x720.jpg', quality=92)
print('thumbnail written')
