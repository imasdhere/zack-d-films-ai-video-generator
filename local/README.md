# Local mode: finished shorts with no API key

`local/` turns one JSON spec into a finished vertical short on your own
machine. Nothing is sent to a paid service.

| Stage | Tool | License |
|---|---|---|
| Narration with word timings | [Kokoro TTS](https://github.com/thewh1teagle/kokoro-onnx), CPU | Apache-2.0 |
| Illustrations | [Fluent Emoji](https://github.com/microsoft/fluentui-emoji) (3D-style vectors) | MIT |
| Captions and titles | [Inter](https://rsms.me/inter/) | OFL-1.1 |
| Horror callouts (`spooky` style) | [Creepster](https://fonts.google.com/specimen/Creepster) | OFL-1.1 |
| Animation | headless Chromium (Playwright), one exact frame at a time | Apache-2.0 |
| Encode | ffmpeg: 1080x1920, 30 fps, H.264, AAC, -14 LUFS | LGPL/GPL |

**No music.** The audio is the narration plus short synthesized whooshes
and pops. Use `--no-sfx` for voice only.

## Setup (one time)

```bash
bash local/setup.sh
```

It creates `.venv-local/`, downloads the Kokoro model (~350 MB) to
`~/.models/kokoro-v1.1` (override with `KOKORO_DIR`), and installs the icon
set and font in `local/node_modules/`.

## Make a short

```bash
.venv-local/bin/python local/make_short.py shorts/honey.json            # full render
.venv-local/bin/python local/make_short.py shorts/honey.json --stills   # one PNG per beat
```

A 70-second short renders in about 3 minutes on 4 CPU cores. The output goes to
`out/shorts/<id>/`:

- `<id>.mp4` is the video to upload.
- `post.txt` has the title, caption, hashtags, pinned comment and sources.
- `stills/` holds the preview PNGs when you use `--stills`.

## The spec

```json
{
  "id": "honey",
  "title": "Why honey never goes bad",
  "voice": "af_heart",
  "speed": 1.08,
  "post": {"youtube_title": "...", "caption": "...", "hashtags": ["..."], "pinned_comment": "..."},
  "sources": ["..."],
  "beats": [
    {
      "text": "Honey is about {*80%*|eighty percent} sugar.",
      "bg": ["#ffb22e", "#6b2600"],
      "elements": [
        {"type": "icon", "name": "honey-pot", "x": 540, "y": 820, "size": 500},
        {"type": "meter", "label": "Sugar", "value": 80, "x": 540, "y": 1100, "on": "80%"}
      ]
    }
  ]
}
```

A beat is one or two sentences with its own visuals. A new beat cuts with a
camera punch-in and a background colour change. Aim for 12 to 15 beats and
60 to 75 seconds. TikTok Creator Rewards pays only for videos longer than one
minute, and `make_short.py` warns when a render is shorter.

### Narration markup

- `{shown|said}` shows one thing in the captions and says another, for
  example `{2015|twenty fifteen}` or `{pH|pee aitch}`.
- `*word*` gives the word the accent colour in the captions.

### Element fields

Positions are in pixels on the 1080x1920 canvas and mark the element's centre.

| Field | Meaning |
|---|---|
| `on` | The element appears when this word is spoken (prefix match). Without it, it appears at the start of the beat. |
| `nth` | Use the nth match of `on`. |
| `delay` | Seconds after the trigger. |
| `outOn` | The element leaves when this word is spoken. |
| `enter` | `pop`, `zoom`, `drop`, `rise`, `slideL`, `slideR`, `spin`, `fade`, `glitch` (jittery, flickering arrival) or `none` |
| `idle` | `float` (default), `bob`, `pulse`, `heartbeat`, `shake`, `wiggle`, `sway`, `spin`, `swim`, `flicker` (float with random dropouts) or `none` |
| `impact` | Camera punch, small shake and a pop sound when the element lands. |
| `rot`, `flip`, `scale`, `opacity` | Static rotation in degrees, mirror, extra scale and opacity. |

| Type | Extra fields |
|---|---|
| `icon` | `name` (a [Fluent Emoji](https://icon-sets.iconify.design/fluent-emoji/) name such as `honey-pot`), `size`, `label`, `hue`, `hueOn` and `hueSpeed` (colour cycling from a word) |
| `svg` | `markup` (inline SVG; use single quotes in attributes), `w`, `h` |
| `text` | `text` (use `\n` for a new line), `size`, `color`, `bg` (makes a pill) |
| `counter` | `from`, `to`, `format` (`comma`, `compact` or `plain`), `prefix`, `suffix`, `dur`, `decimals` |
| `meter` | `label`, `value` (0 to 100), `color`, `w` |
| `glow` | `r`, `color` |
| `particles` | `name` (icon), `count`, `area` `[x, y, w, h]`, `speed`, `dir` (`up` or `down`), `minSize`, `maxSize`, `seed` |

A beat can also list `impactOn` words for a camera punch without a new element.

### Spooky theme

`"theme": "spooky"` darkens the vignette and turns the floating specks a
sickly green. Text with `"style": "spooky"` uses the Creepster horror font
with a coloured `glow` (any CSS colour). See `shorts/medical/` for ten worked
examples.

### Photo mode (real imagery)

Set `"theme": "photo"` and give each beat a `photo`. The picture fills the
frame with a slow zoom, cross-fades into the next beat, and shows a small
badge such as `● REAL PHOTO · NASA/JPL-Caltech`. See `shorts/space/` for ten
worked examples.

```json
"photo": {"src": "nasa:PIA19400", "fit": "contain", "focus": [0.34, 0.58],
          "zoom": [1.1, 1.35], "badge": "REAL PHOTO", "credit": "NASA/JPL-Caltech/MSSS"}
```

| Field | Meaning |
|---|---|
| `src` | `nasa:<nasa_id>` from the [NASA Image and Video Library](https://images.nasa.gov), or a path in the repo. NASA pictures download on first use into `assets/nasa/` (needs access to `images-api.nasa.gov` and `images-assets.nasa.gov`). |
| `fit` | `cover` (default) fills the frame. `contain` keeps the whole picture sharp over a blurred copy of itself; use it for wide or small pictures. |
| `focus` | The point `[x, y]` (fractions of the picture) that the zoom closes in on. With `cover`, that point lands at the same fraction of the frame, so an overlay at `[x·1080, y·1920]` stays on it. |
| `zoom`, `pan` | Start and end scale (at least 1.04), and start and end offsets in pixels. |
| `crop` | `[x0, y0, x1, y1]` cuts a region out first, for example one planet from a side-by-side image. |
| `dim` | 0 to 1 darkening, for text over bright pictures. |
| `badge`, `credit` | The label and credit in the corner. Say what it is: `REAL PHOTO`, `REAL IMAGE`, `ILLUSTRATION`, `SIMULATION` or `RADAR MAP`. |

Elements also take `"type": "image"` (`src`, `w`, `h`, `fit`, `radius`,
`frame`, `blend`, `zoom`) for an inset picture, and text takes
`"style": "clean"` (shadow, the photo default) or `"glass"` (frosted pill).
A callout that would run past the frame edges is shrunk to fit.

`post.txt` lists the credit of every NASA picture the short uses, and the
caption ends with a short credit line. Keep both when you post: NASA asks
for credit and does not allow use that implies its endorsement.

### Safe zones

- Keep visuals between y = 320 and y = 1290. The title pill sits at the top.
- Captions use y = 1330 to 1590.
- The TikTok and Shorts buttons cover the right edge from about y = 900 down,
  and the description covers the bottom 330 px.
- Show at least one element from the first moment of every beat.
  `make_short.py` warns when a beat starts empty.

### Voices

`af_heart` has the best quality. Other Kokoro voices: `af_bella`, `af_nicole`,
`am_michael`, `am_fenrir`, `bf_emma`, `bm_george` and more (the
`voices-v1.0.bin` file lists them all).

## Before you post

- Check every claim against the sources in the spec. A wrong fact costs more
  trust than a missing one.
- Turn on TikTok's "AI-generated content" label, because the narration voice is
  synthetic.
- Vary topics, structure and visuals from video to video. YouTube does not
  monetize channels that look mass-produced or repetitive.
