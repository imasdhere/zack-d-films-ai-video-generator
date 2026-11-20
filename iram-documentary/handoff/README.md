# THE LOST CITY OF IRAM: handoff to a Mac (Claude Code + WanGP)

This folder contains a documentary that is in production, not a template. Do not start again. Everything below continues
from **version 3** (exported 2026-11-20):

- 20:12.6 long, 2560×1440, 24 fps, H.264
- cloned English narrator (Video 1); Arabic quotations in the Video 2 voice
- Iram and ʿĀd pronounced the Arabic way
- no music; −16 LUFS
- 17/17 automated QC checks pass

See `handoff/PROJECT_STATUS.md` for what is finished and what is still open. See `handoff/NOT_INCLUDED.md` for every file that
is **not** in the archive, with its cloud location and how to get it back or rebuild it.

## 1. What is in the archive

The archive unpacks to `iram_lost_city_handoff/`:

| Folder | Contents |
|---|---|
| `iram-documentary/` | The whole project at git commit shown in `handoff/ARCHIVE_INFO.txt`: script, research, storyboard, all code, reports. It also contains the media that git does not keep: AI images (PNG) and depth maps, Blender renders, photographs, narration segments and chunks, subtitles, the final mix (FLAC), the 540p review copy of version 3 and the thumbnail. |
| `iram-documentary/handoff_work/` | Map basemap cache and the Natural Earth file that the map renderer needs. `mac_setup.sh` copies them to `$IRAM_WORK`. |
| `iram-documentary/handoff/` | This guide, the status, the list of missing files, the WanGP shot list, the Mac setup script, and `FILE_MANIFEST.csv` (size and SHA-256 of every file). |

Key files:

| What | Where |
|---|---|
| Final script (single source of truth) | `screenplay/script.yaml`; readable: `screenplay/final_fact_checked_script.md` |
| Storyboard (shots per segment) | `storyboard/shots.yaml`; `storyboard/master_storyboard.csv`, `storyboard/scene_list.md` |
| Image prompts, labels, seeds | `storyboard/assets.yaml`; per-image records `assets/images/*.json` |
| Scene timeline (every shot, start/end in seconds) | `renders/timeline.json` |
| Narration (assembled, per segment) | `assets/narration/segments/<segment>.wav` + `.json` (sentence timings) |
| Narration chunks (to rebuild single segments) | `assets/narration/english/chunks/`, `assets/narration/arabic/chunks/` |
| Narration manifest (text, engine, settings, QA per chunk) | `assets/narration/narration_manifest.csv` |
| Final mix (narration + ambience, mastered) | `renders/final/mix.flac` (lossless; becomes `mix.wav` on export) |
| Subtitles | `assets/subtitles/iram_lost_city_documentary.en.srt` |
| Review copy of version 3 | `renders/final/iram_lost_city_documentary_1440p_review_540p.mp4` |
| Image-to-video shot list | `handoff/wangp_shot_list.csv` (and `.json`) |
| Rules for any agent | `CLAUDE.md` (read it first) |

## 2. Set up the Mac

```bash
unzip iram_lost_city_handoff_*.zip && cd iram_lost_city_handoff/iram-documentary
bash handoff/mac_setup.sh          # Homebrew ffmpeg + libraqm, Python 3.12 venv (.venv-iram), work folder ~/iram-work
export IRAM_WORK=~/iram-work IRAM_PY="$PWD/.venv-iram/bin/python" DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
$IRAM_PY scripts/editing/edit.py video --chapter 0 --preview && open renders/previews/chapter_0.mp4
```

All paths that were cloud-specific now come from `IRAM_WORK` (default `/home/user/iram-work`). No other path needs to change.

### Arabic text

The quotation and verse cards draw Arabic with Pillow and libraqm. If `mac_setup.sh` prints `raqm: MISSING`, the Arabic
letters come out unjoined. Check that `brew --prefix`/lib holds `libraqm.dylib` and `libfribidi.dylib`, and that
`DYLD_FALLBACK_LIBRARY_PATH` is set in the same terminal. Compare a quotation card with the review copy (chapter 3)
before you render the whole film.

## 3. Render the film locally (current version, no new clips)

```bash
IRAM_JOBS=4 bash scripts/narration/run_v3_render.sh
```

What it does:
1. Renders 2560×1440 in 17 parts, `IRAM_JOBS` at a time. A part that is complete and up to date is skipped, so you can stop and restart.
2. Joins the parts into `renders/chapters_1440/`.
3. Exports `renders/final/iram_lost_city_documentary_1440p.mp4` and a 540p review copy.
4. Runs QC and writes the reports.

The render took 80 minutes on the 4-core cloud machine. A recent Apple Silicon Mac should take less time. Each job needs about 2–3 GB of RAM.
The chapter renders are not in the archive (4.3 GB), so the first local render renders everything.

- 1080p instead: `export IRAM_SCALE=1.0 IRAM_CHAPTER_DIR=renders/chapters IRAM_MASTER_NAME=iram_lost_city_documentary` before running the same script.
- Export only, if the chapters exist: `IRAM_CHAPTER_DIR=renders/chapters_1440 IRAM_MASTER_NAME=iram_lost_city_documentary_1440p bash scripts/export/export_final.sh`.
- QC needs Whisper, which `mac_setup.sh` installs. The first run downloads the `small.en` model (about 460 MB) to `$IRAM_WORK/models/whisper`.

## 4. Add motion with WanGP (image-to-video)

The film moves by slow camera motion and depth parallax over still images. WanGP can turn the still images into real
video clips. The editor is ready for this: a clip at `assets/generated_video/<shot_key>.mp4` replaces that shot's still.
The clip is stretched to the shot length (neighbouring frames are blended when it plays slower), cropped to fill the frame,
graded like the stills, and keeps its on-screen label. Its credit line becomes "…animated with AI image-to-video".
If you delete a clip, the shot goes back to the still. `IRAM_USE_CLIPS=0` turns all clips off.

**Which shots.** `handoff/wangp_shot_list.csv` has 152 shots:
- **78 can be animated:** AI images and Blender renders, about 633 s in total.
- **74 must stay as they are:**
  - 31 real photographs: these are evidence, so do not invent motion in them;
  - 7 maps;
  - 36 graphics, titles and quotation cards.

Each animatable row gives `shot_key`, `start_image`, `clip_seconds_needed`, `clip_file`, a `motion_prompt` (scene + natural motion + the
original camera move + "keep the composition") and a `negative_prompt`.

**Steps:**
1. In WanGP, choose an image-to-video model your Mac can run, for example *Wan 2.2 I2V*, *Wan 2.2 TI2V 5B* or *LTX*. Set resolution, steps and
   so on, add any start image, then click **Export Settings** and save the file as `~/wangp_i2v_template.json`.
2. Make one job per shot from that template. Only the prompt, negative prompt, start image, length and seed change:
   ```bash
   $IRAM_PY scripts/wangp/make_wangp_jobs.py --template ~/wangp_i2v_template.json --fps 16 --max-frames 81
   # add: --only 0.01_0_D01 0.01_1_D02   to try a few shots first
   ```
   - `--fps`: use the frame rate of your model (Wan 2.1/2.2 14B: 16; TI2V 5B and LTX: 24).
   - `--max-frames 81`: makes 5-second clips. The editor slows them to fit longer shots. Leave it out to generate full length (WanGP sliding windows).
3. Run the jobs headless with WanGP's own Python. Finished shots are skipped, so you can stop and restart:
   ```bash
   bash handoff/wangp_jobs/run_wangp_jobs.sh /path/to/WanGP /path/to/WanGP/python
   ```
   It calls `python wgp.py --process <job>.json --output-dir …` for each shot and copies the result to `assets/generated_video/<shot_key>.mp4`.
4. **Review every clip** before you render. Reject and delete:
   - any clip with morphing buildings, new people, visible faces, text or letters, or flicker;
   - any clip that changes what the image shows.
5. Render again (section 3). Only the parts whose shots got new clips are rendered again.
6. Update the end credits in `scripts/animation/graphics.py` (`g_credits`) to name the image-to-video model you used.

If the narration changes later, the clip names stay valid, because shot keys are `<segment>_<index>_<asset>` and do not depend on timings.
Re-run `scripts/wangp/make_shot_list.py` after any timeline change to update the clip lengths.

## 5. Rules (from CLAUDE.md; they also apply to clips)

- Keep the evidence levels apart. Reconstructions, legends and illustrations stay labelled. Real photographs are never animated or retouched.
- **The Prophet Hūd is never depicted.** The people of ʿĀd appear only as small, distant, anonymous figures, with no faces.
- **No music**, ever. The sound is the procedural ambience in the mix. Image-to-video models that also make audio (for example
  Prism) must not supply the film's sound: the editor uses the picture only.
- No Quranic recitation in the film until a qualified reviewer approves it (`research/quranic_verse_registry.csv`).
- The cloned voices are personal data of the two speakers. Use them only for this documentary, as they agreed. Keep the voice files private.

## 6. Narration and audio

The archive has the finished narration and mix, so you need no TTS model to render. To change narration, see
`documentation/voice_engine.md`. VoxCPM2 runs on a Mac, but you must edit `device='cpu'` to `'mps'` in
`audio_engine/engines/workers/voxcpm_worker.py` and test it. After you change narration:
1. `$IRAM_PY -m audio_engine.audio_assembler all` rebuilds the timeline, mix and subtitles.
2. Run `make_shot_list.py`.
3. Render.

## 7. Continue in Claude Code on the Mac

Open the `iram-documentary` folder in Claude Code. `CLAUDE.md` loads by itself. A good first prompt:

> Read handoff/README.md and handoff/PROJECT_STATUS.md. Then help me generate WanGP image-to-video clips for the
> chapter 1 shots in handoff/wangp_shot_list.csv, review them with me, and re-render chapter 1 at 1440p.

### Keep version control

The archive holds the files, not the git history. The same code is on GitHub:
`imasdhere/zack-d-films-ai-video-generator`, branch `claude/iram-documentary-production-6jbfrx`, folder `iram-documentary/`.
To combine the two:

```bash
git clone -b claude/iram-documentary-production-6jbfrx https://github.com/imasdhere/zack-d-films-ai-video-generator.git
rsync -a iram_lost_city_handoff/iram-documentary/ zack-d-films-ai-video-generator/iram-documentary/
```

The media folders are git-ignored, so they stay local.
