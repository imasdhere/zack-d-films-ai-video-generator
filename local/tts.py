#!/usr/bin/env python3
"""
Local narration for a short, with word-level timings.

Uses the Kokoro TTS model (Apache-2.0) on the CPU. No API key, no cost,
and no music: the output is voice only.

A beat's text can carry two small markups:
  {2015|twenty fifteen}  show "2015" in the captions, say "twenty fifteen"
  *word*                 give the word the accent colour in the captions

Usage (normally called by make_short.py):
  python local/tts.py shorts/honey.json out/shorts/honey
"""

import argparse
import json
import os
import re
import sys

import numpy as np
import soundfile as sf

MODEL_DIR = os.environ.get("KOKORO_DIR", os.path.expanduser("~/.models/kokoro-v1.1"))
SAMPLE_RATE = 24000
LEAD_IN = 0.12       # silence before the first word
SENTENCE_GAP = 0.14  # silence between sentences inside a beat
BEAT_GAP = 0.26      # silence between beats (the visual cut lands here)
TAIL = 1.1           # silence after the last word, so the last caption can land

TOKEN_RE = re.compile(r"\{([^|{}]+)\|([^{}]+)\}|\S+")
SENTENCE_END_RE = re.compile(r"[.!?][\"')\]]*$")
PUNCT = set(";:,.!?¡¿—–…\"'«»“”()[] ")


def parse_words(text):
    """Split beat text into words with a display form and a spoken form."""
    words, prev_end = [], -1
    for m in TOKEN_RE.finditer(text):
        if m.group(1) is not None:
            shown, said = m.group(1), m.group(2)
        else:
            shown = said = m.group(0)
        accent = shown.count("*") >= 2
        shown, said = shown.replace("*", ""), said.replace("*", "")
        if not re.search(r"\w", shown) and words:
            # Punctuation belongs to the word before it: "{2015|...}," or a lone dash
            gap = "" if m.start() == prev_end else " "
            words[-1]["w"] += gap + shown
            words[-1]["say"] += gap + said
        else:
            words.append({"w": shown, "say": said, "accent": accent})
        prev_end = m.end()
    return words


def split_sentences(words):
    sentences, current = [], []
    for word in words:
        current.append(word)
        if SENTENCE_END_RE.search(word["w"]):
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    return sentences


SKIP = PUNCT | set("ˈˌ")


def content_chars(phonemes):
    """Phoneme characters that take time (no spaces, punctuation or stress marks)."""
    return [c for c in phonemes if c not in SKIP]


def align(a, b):
    """Edit-distance alignment. For each index of a, the matched index of b or None."""
    n, m = len(a), len(b)
    d = np.zeros((n + 1, m + 1), dtype=np.int32)
    d[:, 0] = np.arange(n + 1)
    d[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + cost)
    match = [None] * n
    i, j = n, m
    while i > 0 and j > 0:
        cost = 0 if a[i - 1] == b[j - 1] else 1
        if d[i, j] == d[i - 1, j - 1] + cost:
            match[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif d[i, j] == d[i - 1, j] + 1:
            i -= 1
        else:
            j -= 1
    return match


def time_sentence(kokoro, sentence, timings):
    """Give each word of a sentence its start and end time in seconds.

    The phonemizer sometimes merges words when it reads a whole sentence
    ("out of" becomes one sound group), so the words are found by aligning
    each word's own phonemes against the timed phonemes of the sentence.
    """
    timed_chars = [t for t in timings if t.phoneme not in SKIP]
    chars, owner = [], []
    for index, word in enumerate(sentence):
        own = content_chars(kokoro.tokenizer.phonemize(word["say"], "en-us"))
        chars.extend(own)
        owner.extend([index] * len(own))

    spans = [[None, None] for _ in sentence]
    if timed_chars and chars:
        match = align(chars, [t.phoneme for t in timed_chars])
        for ci, ti in enumerate(match):
            if ti is None:
                continue
            span = spans[owner[ci]]
            if span[0] is None:
                span[0] = timed_chars[ti].start
            span[1] = timed_chars[ti].end

    exact = all(s is not None for s, _ in spans)
    first = timed_chars[0].start if timed_chars else 0.0
    last = timed_chars[-1].end if timed_chars else 0.0
    # A word with no matched sound sits between its neighbours
    for i, span in enumerate(spans):
        if span[0] is None:
            prev_end = next((spans[k][1] for k in range(i - 1, -1, -1) if spans[k][1] is not None), first)
            next_start = next((spans[k][0] for k in range(i + 1, len(spans)) if spans[k][0] is not None), last)
            span[0], span[1] = prev_end, max(prev_end, next_start)

    timed, floor = [], first
    for word, (s, e) in zip(sentence, spans):
        s = max(s, floor)
        e = max(e, s + 0.05)
        floor = s
        timed.append({**word, "s": round(s, 3), "e": round(e, 3)})
    return timed, exact


def load_kokoro():
    from kokoro_onnx import Kokoro

    model = os.path.join(MODEL_DIR, "kokoro-v1.0.onnx")
    voices = os.path.join(MODEL_DIR, "voices-v1.0.bin")
    if not (os.path.exists(model) and os.path.exists(voices)):
        sys.exit(f"[tts] Kokoro model files not found in {MODEL_DIR}. Run local/setup.sh first.")
    kokoro = Kokoro(model, voices)
    if not kokoro.has_timings:
        sys.exit("[tts] This Kokoro export has no duration output. Use the model-files-v1.1 release.")
    return kokoro


def narrate(spec, out_dir):
    """Synthesize the narration. Returns the timing dict and writes narration.wav."""
    kokoro = load_kokoro()
    voice = spec.get("voice", "af_heart")
    speed = float(spec.get("speed", 1.05))

    chunks = [np.zeros(int(LEAD_IN * SAMPLE_RATE), dtype=np.float32)]
    cursor = LEAD_IN
    beats_out, fallbacks = [], 0

    for b_index, beat in enumerate(spec["beats"]):
        if b_index > 0:
            chunks.append(np.zeros(int(BEAT_GAP * SAMPLE_RATE), dtype=np.float32))
            cursor += BEAT_GAP
        words_out = []
        sentences = split_sentences(parse_words(beat["text"]))
        for s_index, sentence in enumerate(sentences):
            if s_index > 0:
                chunks.append(np.zeros(int(SENTENCE_GAP * SAMPLE_RATE), dtype=np.float32))
                cursor += SENTENCE_GAP
            text = " ".join(w["say"] for w in sentence)
            audio, sr, timings = kokoro.create_timed(text, voice=voice, speed=speed, lang="en-us")
            if sr != SAMPLE_RATE:
                sys.exit(f"[tts] Unexpected sample rate {sr}")
            timed, exact = time_sentence(kokoro, sentence, timings)
            fallbacks += 0 if exact else 1
            for w in timed:
                w["s"] = round(w["s"] + cursor, 3)
                w["e"] = round(w["e"] + cursor, 3)
            words_out.extend(timed)
            chunks.append(audio.astype(np.float32))
            cursor += len(audio) / SAMPLE_RATE
        if beat.get("hold"):
            # A dramatic pause, so a reveal stays on screen before the next cut
            chunks.append(np.zeros(int(float(beat["hold"]) * SAMPLE_RATE), dtype=np.float32))
            cursor += float(beat["hold"])
        beats_out.append({"words": words_out})

    chunks.append(np.zeros(int(TAIL * SAMPLE_RATE), dtype=np.float32))
    audio = np.concatenate(chunks)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = (audio / peak * 0.89).astype(np.float32)

    os.makedirs(out_dir, exist_ok=True)
    sf.write(os.path.join(out_dir, "narration.wav"), audio, SAMPLE_RATE)
    timing = {
        "sample_rate": SAMPLE_RATE,
        "duration": round(len(audio) / SAMPLE_RATE, 3),
        "voice": voice,
        "speed": speed,
        "approximate_sentences": fallbacks,
        "beats": beats_out,
    }
    with open(os.path.join(out_dir, "timing.json"), "w", encoding="utf-8") as f:
        json.dump(timing, f, indent=1, ensure_ascii=False)
    return timing


def main():
    parser = argparse.ArgumentParser(description="Narrate a short with local Kokoro TTS")
    parser.add_argument("spec", help="Short spec JSON, e.g. shorts/honey.json")
    parser.add_argument("out_dir", help="Output directory, e.g. out/shorts/honey")
    args = parser.parse_args()
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    timing = narrate(spec, args.out_dir)
    n_words = sum(len(b["words"]) for b in timing["beats"])
    print(f"[tts] {n_words} words, {timing['duration']:.1f}s, "
          f"{timing['approximate_sentences']} sentence(s) with approximate timing")


if __name__ == "__main__":
    main()
