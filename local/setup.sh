#!/usr/bin/env bash
# One-time setup for the local renderer: Python venv, Kokoro TTS model, icons and font.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
VENV="$REPO/.venv-local"
MODEL_DIR="${KOKORO_DIR:-$HOME/.models/kokoro-v1.1}"
# The v1.1 export reports phoneme durations, which the captions need
RELEASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"

command -v ffmpeg >/dev/null || { echo "Install ffmpeg first."; exit 1; }
command -v node >/dev/null || { echo "Install Node.js 18 or later first."; exit 1; }

python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -r "$HERE/requirements.txt"

mkdir -p "$MODEL_DIR"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -f "$MODEL_DIR/$f" ] || curl -fL --retry 3 -o "$MODEL_DIR/$f" "$RELEASE/$f"
done

(cd "$HERE" && npm install --no-audit --no-fund)
if ! (cd "$HERE" && node -e "require('playwright')" 2>/dev/null); then
  (cd "$HERE" && npm install --no-save --no-audit --no-fund playwright && npx playwright install chromium)
fi

echo "Ready. Try: $VENV/bin/python local/make_short.py shorts/honey.json"
