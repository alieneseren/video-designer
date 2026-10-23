#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/ubuntu/yt-remote-worker"
ENV_DIR="$BASE_DIR/kokoro-venv"
MODEL_DIR="$BASE_DIR/models/kokoro"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 -m venv "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install --upgrade pip
"$ENV_DIR/bin/python" -m pip install -r "$SCRIPT_DIR/requirements-kokoro.txt"

mkdir -p "$MODEL_DIR"
curl --fail --location --retry 3 \
  "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx" \
  --output "$MODEL_DIR/kokoro-v1.0.onnx.part"
mv "$MODEL_DIR/kokoro-v1.0.onnx.part" "$MODEL_DIR/kokoro-v1.0.onnx"
curl --fail --location --retry 3 \
  "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin" \
  --output "$MODEL_DIR/voices-v1.0.bin.part"
mv "$MODEL_DIR/voices-v1.0.bin.part" "$MODEL_DIR/voices-v1.0.bin"

"$ENV_DIR/bin/python" -c \
  "from kokoro_onnx import Kokoro; import soundfile; print('Kokoro-ONNX hazır')"
echo "Kokoro modelleri kuruldu: $MODEL_DIR"
