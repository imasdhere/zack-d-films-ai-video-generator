#!/usr/bin/env python3
"""
Make a finished vertical short from one spec file, on the local machine.

  spec (shorts/<id>.json)
    -> narration.wav + timing.json   local Kokoro TTS, word-level timings
    -> scene.json                    every visual pinned to the word that triggers it
    -> audio.wav                     narration + synthesized whooshes/pops, -14 LUFS
    -> final.mp4                     1080x1920, 30 fps, H.264 + AAC

No API keys and no paid services. The audio holds narration and short
synthesized sound effects only. This script never adds music.

Usage:
  python local/make_short.py shorts/honey.json
  python local/make_short.py shorts/honey.json --stills      # preview PNGs only
  python local/make_short.py shorts/honey.json --no-sfx      # voice only
"""

import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tts  # noqa: E402

SR = tts.SAMPLE_RATE
CUT_LEAD = 0.10        # the visual cut lands this long before a beat's first word
DEFAULT_BG = ["#2a3a8f", "#0b1030"]
TARGET_LUFS = -14.0         # the loudness TikTok, YouTube and Instagram normalise to
MIN_TIKTOK_REWARDS = 61.0   # Creator Rewards pays only for videos longer than 1 minute
MAX_SHORTS = 180.0          # YouTube Shorts limit


def norm(word):
    return re.sub(r"[^a-z0-9]", "", word.lower())


def find_word(words, key, nth=1):
    """Start time of the nth word in a beat that matches key (exact, then prefix)."""
    k = norm(key)
    for match in (lambda w: norm(w["w"]) == k, lambda w: norm(w["w"]).startswith(k)):
        hits = [w for w in words if match(w)]
        if len(hits) >= nth:
            return hits[nth - 1]["s"]
    return None


def resolve_scene(spec, timing):
    """Merge the spec with the narration timings into what the renderer draws."""
    beats_in, beats_t = spec["beats"], timing["beats"]
    starts = []
    for i, bt in enumerate(beats_t):
        starts.append(0.0 if i == 0 else round(bt["words"][0]["s"] - CUT_LEAD, 3))
    duration = timing["duration"]

    beats_out, sfx = [], []
    for i, (beat, bt) in enumerate(zip(beats_in, beats_t)):
        start = starts[i]
        end = starts[i + 1] if i + 1 < len(starts) else duration
        words = bt["words"]
        elements, impacts, untimed = [], [], 0
        for el in beat.get("elements", []):
            el = dict(el)
            if el.get("on"):
                t0 = find_word(words, el["on"], el.get("nth", 1))
                if t0 is None:
                    sys.exit(f"[scene] beat {i + 1}: no word '{el['on']}' in: {beat['text']}")
                t0 += el.get("delay", 0.0)
            else:
                delay = el.get("delay", 0.06 * untimed)
                untimed += 1
                t0 = (start - 0.3 if i == 0 else start) + delay
            el["t0"] = round(t0, 3)
            if el.get("outOn"):
                t1 = find_word(words, el["outOn"], el.get("outNth", 1))
                if t1 is None:
                    sys.exit(f"[scene] beat {i + 1}: no word '{el['outOn']}' in: {beat['text']}")
                el["t1"] = round(t1, 3)
            if el.get("hueOn"):
                th = find_word(words, el["hueOn"])
                if th is None:
                    sys.exit(f"[scene] beat {i + 1}: no word '{el['hueOn']}' for hueOn")
                el["th"] = round(th, 3)
            if el.get("impact"):
                impacts.append(round(max(t0, 0) + 0.06, 3))
                sfx.append({"t": max(t0, 0), "kind": "pop"})
            elif el.get("sfx"):
                sfx.append({"t": max(t0, 0), "kind": el["sfx"]})
            elements.append(el)
        if not any(el["t0"] <= start + 0.35 for el in elements):
            print(f"[warn] beat {i + 1} shows nothing in its first moment; add an element without 'on'")
        for key in beat.get("impactOn", []):
            t = find_word(words, key)
            if t is None:
                sys.exit(f"[scene] beat {i + 1}: no word '{key}' for impactOn")
            impacts.append(round(t + 0.04, 3))
            sfx.append({"t": t, "kind": "pop"})
        if i > 0:
            sfx.append({"t": start - 0.08, "kind": "whoosh"})
        beats_out.append({
            "start": start, "end": round(end, 3), "bg": beat.get("bg", DEFAULT_BG),
            "words": words, "elements": elements, "impacts": sorted(impacts),
        })
    return {"title": spec.get("title", ""), "fps": spec.get("fps", 30), "duration": duration,
            "beats": beats_out, "sfx": sorted(sfx, key=lambda e: e["t"])}


def synth_whoosh(dur=0.34, seed=1):
    n = int(SR * dur)
    noise = np.random.default_rng(seed).standard_normal(n)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    band = np.exp(-((np.log(freqs + 1) - np.log(1600)) ** 2) / (2 * 0.55 ** 2))
    sig = np.fft.irfft(spec * band, n)
    x = np.linspace(0, 1, n)
    sig *= np.sin(np.pi * x ** 0.6) ** 2
    return sig / (np.abs(sig).max() or 1)


def synth_pop(dur=0.12):
    t = np.arange(int(SR * dur)) / SR
    freq = 650 * np.exp(-t * 28) + 170
    sig = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 36)
    return sig / (np.abs(sig).max() or 1)


def build_audio(out_dir, scene, with_sfx=True):
    """Mix narration with synthesized effects and normalise to -14 LUFS."""
    voice, sr = sf.read(os.path.join(out_dir, "narration.wav"), dtype="float32")
    if sr != SR:
        sys.exit(f"[audio] narration sample rate {sr} != {SR}")
    mixbuf = voice.astype(np.float64).copy()
    if with_sfx:
        shapes = {"whoosh": (synth_whoosh(), 0.10), "pop": (synth_pop(), 0.15)}
        for ev in scene["sfx"]:
            shape, gain = shapes[ev["kind"]]
            a = int(max(0.0, ev["t"]) * SR)
            b = min(len(mixbuf), a + len(shape))
            if b > a:
                mixbuf[a:b] += shape[: b - a] * gain
    peak = np.abs(mixbuf).max() or 1.0
    if peak > 0.98:
        mixbuf *= 0.98 / peak
    mix_path = os.path.join(out_dir, "mix.wav")
    sf.write(mix_path, mixbuf.astype(np.float32), SR)

    # Speech peaks sit ~20 dB above its loudness, so loudnorm's linear mode cannot
    # reach -14 LUFS under the peak ceiling. Compress, add gain, then limit the peaks.
    comp = "acompressor=threshold=0.125:ratio=3:attack=5:release=120:makeup=1.5"
    loud, _ = measure_lufs(mix_path, comp)
    gain = TARGET_LUFS - loud
    audio_path = os.path.join(out_dir, "audio.wav")
    for _ in range(3):
        chain = (f"{comp},volume={gain:.2f}dB,"
                 "alimiter=limit=0.79:attack=1:release=60:level=0,aresample=48000")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", mix_path,
                        "-af", chain, "-ac", "2", audio_path], check=True)
        got, peak = measure_lufs(audio_path)
        if abs(got - TARGET_LUFS) <= 0.3:
            break
        gain += TARGET_LUFS - got
    print(f"[audio] {got:.1f} LUFS integrated, peak {peak:.1f} dBFS")
    return audio_path


def measure_lufs(path, chain=None):
    """Integrated loudness (LUFS) and sample peak (dBFS) of a file."""
    af = (chain + "," if chain else "") + "ebur128=peak=sample"
    run = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", af, "-f", "null", "-"],
                         capture_output=True, text=True, check=True)
    summary = run.stderr[run.stderr.rindex("Summary:"):]
    loud = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary).group(1)
    return loud, float(peak) if peak != "-inf" else -120.0


def remux_audio(video_path, audio_path):
    """Swap a rendered video's audio track for a new one without re-rendering frames."""
    tmp = video_path + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video_path, "-i", audio_path,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-shortest", tmp], check=True)
    os.replace(tmp, video_path)


def write_post_kit(spec, out_dir, duration):
    post = spec.get("post", {})
    tags = " ".join("#" + t.lstrip("#") for t in post.get("hashtags", []))
    lines = [
        f"FILE: {spec['id']}.mp4   ({duration:.1f}s, 1080x1920, no music)",
        "",
        "YOUTUBE SHORTS TITLE:",
        post.get("youtube_title", spec.get("title", "")),
        "",
        "TIKTOK / REELS / SHORTS CAPTION:",
        (post.get("caption", "") + "\n\n" + tags).strip(),
        "",
        "PINNED COMMENT (post it yourself right after upload):",
        post.get("pinned_comment", ""),
        "",
        "SOURCES (keep these; reply with them if someone asks):",
        *[f"- {s}" for s in spec.get("sources", [])],
    ]
    with open(os.path.join(out_dir, "post.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Render a music-free vertical short from a spec")
    ap.add_argument("spec", help="shorts/<id>.json")
    ap.add_argument("--out", help="output directory (default out/shorts/<id>)")
    ap.add_argument("--stills", action="store_true", help="only render preview PNGs at each beat")
    ap.add_argument("--reuse-tts", action="store_true", help="reuse narration.wav/timing.json")
    ap.add_argument("--no-sfx", action="store_true", help="voice only, no sound effects")
    ap.add_argument("--remux-audio", action="store_true",
                    help="rebuild only the audio and swap it into the rendered video")
    args = ap.parse_args()
    if args.remux_audio:
        args.reuse_tts = True

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    out_dir = args.out or os.path.join(REPO, "out", "shorts", spec["id"])
    os.makedirs(out_dir, exist_ok=True)

    timing_path = os.path.join(out_dir, "timing.json")
    if args.reuse_tts and os.path.exists(timing_path):
        with open(timing_path, encoding="utf-8") as f:
            timing = json.load(f)
    else:
        timing = tts.narrate(spec, out_dir)
    print(f"[tts] {timing['duration']:.1f}s narration, voice {timing['voice']}, "
          f"{timing['approximate_sentences']} approximate sentence(s)")

    scene = resolve_scene(spec, timing)
    scene_path = os.path.join(out_dir, "scene.json")
    with open(scene_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=1, ensure_ascii=False)

    render = os.path.join(HERE, "render.cjs")
    if args.stills:
        times = [round((b["start"] + b["end"]) / 2 + 0.25, 2) for b in scene["beats"]]
        subprocess.run(["node", render, scene_path, os.path.join(out_dir, "stills"),
                        "--stills", ",".join(map(str, times))], check=True)
        return

    audio_path = build_audio(out_dir, scene, with_sfx=not args.no_sfx)
    final = os.path.join(out_dir, f"{spec['id']}.mp4")
    if args.remux_audio:
        if not os.path.exists(final):
            sys.exit(f"[audio] {final} does not exist yet; render it first")
        remux_audio(final, audio_path)
    else:
        subprocess.run(["node", render, scene_path, final, "--audio", audio_path], check=True)

    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
                            "-of", "json", final], capture_output=True, text=True, check=True)
    fmt = json.loads(probe.stdout)["format"]
    duration = float(fmt["duration"])
    write_post_kit(spec, out_dir, duration)
    print(f"[done] {final}  {duration:.1f}s  {int(fmt['size']) / 1e6:.1f} MB")
    if duration < MIN_TIKTOK_REWARDS:
        print(f"[warn] {duration:.1f}s is too short for TikTok Creator Rewards (needs > 60s)")
    if duration > MAX_SHORTS:
        print(f"[warn] {duration:.1f}s is longer than the YouTube Shorts limit ({MAX_SHORTS:.0f}s)")


if __name__ == "__main__":
    main()
