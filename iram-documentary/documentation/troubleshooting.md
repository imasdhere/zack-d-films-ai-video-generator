# Troubleshooting (problems actually met during production)

| Symptom | Cause | Fix |
|---|---|---|
| `uv pip install torch` from `download.pytorch.org/whl/cpu` fails with "tunnel error" | The CPU index redirects to `download-r2.pytorch.org`, which the network policy blocked | Use the standard PyPI wheels, or allow-list `download-r2.pytorch.org` |
| `kokoro` will not install on Python 3.13 | `kokoro`/`misaki` 0.9.4 on PyPI require Python < 3.13 | Use a Python 3.12 venv (the user's fork at dfb907a supports 3.13) |
| `ImportError: cannot import name 'Qwen3TTSModel' from partially initialized module 'qwen_tts'` | Our script was named `qwen_tts.py` and shadowed the package | Renamed to `qwen3_narrate.py`; run with `python -I` |
| Hugging Face downloads stall at a few MB | Files are served from `us.aws.cdn.hf.co` (Xet CDN), which was not allow-listed | Allow `us.aws.cdn.hf.co`, `eu.aws.cdn.hf.co`, `cdn.hf.co` |
| ComfyUI killed (OOM) while loading SDXL | About 11 GB RSS on CPU even with `--bf16-unet`, plus about 6 GB for the narration job, exceeded the 15 GB cgroup | Run image generation only after narration finishes |
| Wikimedia: HTTP 429 on the API and on `upload.wikimedia.org` | Shared egress IP rate-limited | Long back-off retries (`commons_fetch.py`). NASA public-domain images and labelled fallbacks are defined in `photo_map.yaml`. |
| `thumb.wikimedia.org` blocked | Commons thumbnails come from a different host | Download originals from `upload.wikimedia.org` and downscale locally |
| Cloudflare "Just a moment…" on sunnah.com / UNESCO / Britannica | Bot challenge | Headless Chromium (Playwright) passes it for sunnah.com and UNESCO. Britannica failed; Wikipedia was used for those facts. |
| Wikisource Muqaddimah has only scanned pages | No transcluded text available | Ibn Khaldūn's critique was **excluded** from the script, not quoted from memory |
| Blender 5.x: `OPEN_EXR_MULTILAYER not found` | 5.x moved multilayer EXR to `image_settings.media_type` | Output display-referred PNG; depth comes from Depth-Anything |
| Blender renders completely white | The sky texture already contains the sun, plus a strong sun lamp was added | `sun_disc=False`, sky strength 0.35–0.5, view exposure −2.5 |
| Cinzel shows boxes for Ḥ, Ṭ, ʿ | Cinzel lacks dotted transliteration letters | Automatic glyph-coverage fallback to EB Garamond (`graphics.covered`) |
| Arabic letters disconnected or left-to-right | Pillow without raqm | Use Pillow with libraqm (`features.check('raqm')`) and `direction='rtl'` |
| `numpy.ndarray.ptp` AttributeError | Removed in NumPy 2 | Use `np.ptp(x)` |
