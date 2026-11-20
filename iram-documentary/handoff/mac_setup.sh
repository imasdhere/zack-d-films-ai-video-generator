#!/usr/bin/env bash
# Set up the Iram documentary editor on a Mac (Apple Silicon or Intel). Run from the iram-documentary folder:
#   bash handoff/mac_setup.sh
# It creates .venv-iram (Python 3.12) with what the editor, the mix, the export and the QC need, and a work folder
# (default ~/iram-work) with the map cache from the archive. It does not install TTS or image models (see README).
set -euo pipefail
cd "$(dirname "$0")/.."
WORK="${IRAM_WORK:-$HOME/iram-work}"

command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
command -v ffmpeg >/dev/null || brew install ffmpeg
brew list libraqm >/dev/null 2>&1 || brew install libraqm          # Arabic text shaping for the quotation cards
command -v uv >/dev/null || brew install uv

uv venv -p 3.12 .venv-iram
VIRTUAL_ENV="$PWD/.venv-iram" uv pip install "numpy<2.4" scipy opencv-python-headless "pillow>=11" pyyaml soundfile pyloudnorm librosa
# QC (narration intelligibility) needs Whisper; optional
VIRTUAL_ENV="$PWD/.venv-iram" uv pip install openai-whisper jiwer || echo "Whisper not installed: QC step 6 will fail; render and export still work"

mkdir -p "$WORK/cache" "$WORK/data" "$WORK/logs"
[ -d handoff_work/cache/maps ] && cp -R handoff_work/cache/maps "$WORK/cache/"
[ -d handoff_work/data/ne ] && cp -R handoff_work/data/ne "$WORK/data/"
[ -f renders/final/mix.flac ] && [ ! -f renders/final/mix.wav ] && ffmpeg -y -loglevel error -i renders/final/mix.flac -c:a pcm_s24le renders/final/mix.wav

# Pillow loads libraqm at run time; Homebrew's lib folder must be on the library path
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"
.venv-iram/bin/python - <<'PY'
from PIL import features
ok = features.check('raqm')
print('Arabic shaping (raqm):', 'OK' if ok else 'MISSING - see README, section "Arabic text"')
PY
cat <<EOF

Done. In every new terminal, before rendering:
  cd "$PWD"
  export IRAM_WORK="$WORK" IRAM_PY="$PWD/.venv-iram/bin/python"
  export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
Quick test (half size, about a minute):
  \$IRAM_PY scripts/editing/edit.py video --chapter 0 --preview && open renders/previews/chapter_0.mp4
EOF
