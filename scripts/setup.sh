#!/usr/bin/env bash
# One-time setup per session: Python deps + Kokoro voice model (from GitHub releases)
set -e
cd "$(dirname "$0")/.."
pip install -q --break-system-packages kokoro-onnx soundfile pillow numpy
mkdir -p models
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s models/$f ] || curl -sSL -o models/$f https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f
done
echo "setup ok"
