#!/usr/bin/env python3
"""
Fetch pictures from the NASA Image and Video Library for the shorts.

A spec refers to an image as "nasa:<nasa_id>", for example "nasa:PIA19400".
The file is cached at assets/nasa/<nasa_id>.jpg, scaled to at most 3200 px on
the long side, which leaves room for slow zooms on a 1080x1920 frame. The
credit line from NASA's metadata is cached next to it.

NASA imagery is generally not copyrighted, but it must not imply NASA
endorsement, and some items credit partners (ESA, STScI, universities).
Always show the credit. See https://www.nasa.gov/nasa-brand-center/images-and-media/

Needs network access to images-api.nasa.gov and images-assets.nasa.gov.

Usage:
  python local/nasa_images.py PIA19400 as11-40-5878     # fetch and print credits
"""

import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from PIL import Image

API = "https://images-api.nasa.gov"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(REPO, "assets", "nasa")
MAX_SIDE = 3200
MAX_DOWNLOAD = 60 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 400_000_000  # some NASA originals are very large


def _get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def _size(url):
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return int(r.headers.get("Content-Length") or 0)
    except Exception:
        return 0


def _pick(hrefs):
    """The largest rendition that is a still image and not too big to download."""
    def quoted(h):
        # The API lists http:// links; the same files are served over https
        return urllib.parse.quote(re.sub(r"^http://", "https://", h), safe=":/~%")
    candidates = []
    for tag in ("~orig", "~large", "~medium"):
        for h in hrefs:
            if tag in h and re.search(r"\.(jpe?g|png|tiff?)$", h, re.I):
                candidates.append(quoted(h))
    for h in candidates:
        size = _size(h)
        if 0 < size <= MAX_DOWNLOAD:
            return h
    return candidates[-1] if candidates else None


def _credit(meta):
    """Best credit line from NASA's metadata."""
    desc = meta.get("description", "") or ""
    m = re.search(r"(?:Image\s+)?Credits?:\s*([^\n]+)", desc)
    if m:
        text = re.sub(r"<[^>]+>", " ", m.group(1))
        # Goddard captions run straight on into boilerplate after the credit
        text = re.split(r"\s+(?:For more information|This |These |NASA image use|Read more)", text)[0]
        return re.sub(r"\s+", " ", text).strip().rstrip(".")
    for key in ("secondary_creator", "photographer"):
        if meta.get(key):
            return f"NASA/{meta[key]}" if "NASA" not in meta[key] else meta[key]
    return f"NASA/{meta.get('center', '')}".rstrip("/")


def fetch(nasa_id, cache=CACHE):
    """Download one image if needed. Returns (path, credit, title)."""
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, f"{nasa_id}.jpg")
    meta_path = os.path.join(cache, f"{nasa_id}.json")
    if os.path.exists(path) and os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
        return path, meta["credit"], meta["title"]

    search = _get_json(f"{API}/search?" + urllib.parse.urlencode({"nasa_id": nasa_id}))
    items = search["collection"]["items"]
    if not items:
        raise SystemExit(f"[nasa] no image with nasa_id {nasa_id}")
    meta = items[0]["data"][0]
    url = None
    if not os.path.exists(path):
        hrefs = _get_json(f"{API}/asset/{urllib.parse.quote(nasa_id)}")["collection"]["items"]
        url = _pick([h["href"] for h in hrefs])
        if not url:
            raise SystemExit(f"[nasa] no still image rendition for {nasa_id}")
        with urllib.request.urlopen(url, timeout=300) as r:
            data = r.read()
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        im.save(path, quality=92, optimize=True)

    info = {"nasa_id": nasa_id, "title": meta.get("title", ""), "credit": _credit(meta),
            "date": meta.get("date_created", "")[:10], "source": url,
            "size": list(Image.open(path).size)}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1, ensure_ascii=False)
    return path, info["credit"], info["title"]


def main():
    for nasa_id in sys.argv[1:]:
        path, credit, title = fetch(nasa_id)
        w, h = Image.open(path).size
        print(f"{nasa_id:52s} {w}x{h}  {credit}  | {title}")


if __name__ == "__main__":
    main()
