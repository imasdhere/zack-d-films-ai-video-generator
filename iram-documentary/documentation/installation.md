# Installation

Everything below was run, in this order, on Ubuntu 24.04 (x86-64, CPU only) in the production session. Large files stay outside the git repository in a work directory: `WORK=/home/user/iram-work`.

## 0. Prerequisites

- `ffmpeg` ≥ 6 with libx264 (`apt install ffmpeg`), `git`, `curl`.
- [`uv`](https://github.com/astral-sh/uv) (`pip install uv`). `uv` downloads the Python interpreters it needs.
- Network access to: pypi.org, huggingface.co plus its CDNs (`cdn-lfs*.hf.co`, `cas-bridge.xethub.hf.co`, `us.aws.cdn.hf.co`), openaipublic.azureedge.net (Whisper), copernicus-dem-90m.s3.amazonaws.com, raw.githubusercontent.com (Natural Earth, Google Fonts), images-api.nasa.gov / images-assets.nasa.gov, commons.wikimedia.org / upload.wikimedia.org, tanzil.net, api.quran.com.

## 1. Virtual environments

```bash
WORK=/home/user/iram-work; mkdir -p $WORK/{venvs,models,logs,cache,data}
# main ML / editing environment (Python 3.12: kokoro/misaki require <3.13)
uv venv $WORK/venvs/ml --python 3.12 --seed && source $WORK/venvs/ml/bin/activate
uv pip install torch torchaudio torchvision
uv pip install "numpy<2.4" scipy soundfile librosa pyyaml opencv-python-headless pillow tqdm safetensors "transformers>=4.57" \
  accelerate einops sentencepiece huggingface_hub hf_xet pyloudnorm pandas jiwer kokoro "misaki[en]" openai-whisper \
  rasterio shapely pyproj matplotlib fonttools trafilatura beautifulsoup4 lxml
deactivate
# Qwen3-TTS (pins transformers 4.57.3, so it gets its own env)
uv venv $WORK/venvs/qwen --python 3.12 --seed && $WORK/venvs/qwen/bin/python -m pip install torch torchaudio qwen-tts soundfile numpy
# ComfyUI
uv venv $WORK/venvs/comfy --python 3.12 --seed && source $WORK/venvs/comfy/bin/activate
uv pip install torch torchvision torchaudio && uv pip install -r /home/user/ComfyUI/requirements.txt && deactivate
# Blender as a Python module (bpy 5.3 requires Python 3.13)
uv venv $WORK/venvs/blender --python 3.13 --seed && $WORK/venvs/blender/bin/python -m pip install bpy==5.3.0
```

On CPU-only Linux you can install CPU-only PyTorch wheels from `https://download.pytorch.org/whl/cpu`, which avoids about 3 GB of CUDA libraries. That index redirects to `download-r2.pytorch.org`, which must be reachable. This session used the standard PyPI wheels instead.

## 2. Model weights (about 17 GB)

```bash
source $WORK/venvs/ml/bin/activate; export HF_HOME=$WORK/cache/hf; M=$WORK/models
hf download hexgrad/Kokoro-82M --local-dir $M/kokoro-82m
hf download Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign --local-dir $M/qwen3-tts-1.7b-voicedesign
hf download Qwen/Qwen3-TTS-12Hz-1.7B-Base --local-dir $M/qwen3-tts-1.7b-base
hf download Qwen/Qwen3-TTS-Tokenizer-12Hz --local-dir $M/qwen3-tts-tokenizer-12hz
hf download depth-anything/Depth-Anything-V2-Small-hf --local-dir $M/depth-anything-v2-small
hf download stabilityai/stable-diffusion-xl-base-1.0 sd_xl_base_1.0.safetensors --local-dir $M/sdxl
hf download ByteDance/SDXL-Lightning sdxl_lightning_8step_lora.safetensors sdxl_lightning_4step_lora.safetensors --local-dir $M/sdxl-lightning
hf download madebyollin/sdxl-vae-fp16-fix sdxl_vae.safetensors --local-dir $M/sdxl-vae-fix
python -c "import whisper; whisper.load_model('small.en', download_root='$M/whisper')"
```

## 3. Data

```bash
# Natural Earth vectors (public domain)
cd $WORK/data/ne && for f in ne_10m_land ne_10m_admin_0_countries ne_10m_geography_regions_polys; do
  curl -fsSLO https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/$f.geojson; done
# Copernicus GLO-90 DEM mosaics (range reads of cloud-optimised GeoTIFFs)
python scripts/animation/fetch_dem.py           # then the wide Arabia mosaic: see reports/production_log.md
# Fonts (OFL) into assets/fonts/ — Amiri, Amiri Quran, Cinzel, EB Garamond (google/fonts repository)
```

## 4. Run ComfyUI headless (CPU)

```bash
cd /home/user/ComfyUI && source $WORK/venvs/comfy/bin/activate
python main.py --cpu --bf16-unet --bf16-text-enc --bf16-vae --listen 127.0.0.1 --port 8188 \
  --extra-model-paths-config <project>/workflows/comfyui/extra_model_paths.yaml --output-directory $WORK/comfy_out
```

SDXL needs about 11 GB of RAM at load time on CPU. Do not run it alongside the narration job on a 15 GB machine.

## 5. Uninstall

Delete `$WORK` (venvs, models, caches, about 30 GB). Nothing was installed system-wide except the `uv` pip package.
