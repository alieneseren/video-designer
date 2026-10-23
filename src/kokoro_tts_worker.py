"""Isolated Kokoro-ONNX batch inference entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: kokoro_tts_worker.py REQUEST.json", file=sys.stderr)
        return 2

    request_path = Path(sys.argv[1])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    texts = request["texts"]
    output_paths = request["output_paths"]
    if not texts or len(texts) != len(output_paths):
        raise ValueError("Kokoro metin ve çıktı dosyası sayıları eşleşmelidir.")

    model_path = Path(request["model_path"])
    voices_path = Path(request["voices_path"])
    if not model_path.is_file() or not voices_path.is_file():
        raise FileNotFoundError("Kokoro model veya ses dosyası kurulu değil.")

    from kokoro_onnx import Kokoro
    import soundfile as sf

    engine = Kokoro(str(model_path), str(voices_path))
    for text, output_path in zip(texts, output_paths):
        samples, sample_rate = engine.create(
            text,
            voice=request["voice"],
            speed=float(request["speed"]),
            lang=request["language"],
        )
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(target), samples, sample_rate)
        if not target.is_file() or target.stat().st_size < 1000:
            raise RuntimeError(f"Kokoro boş ses oluşturdu: {target.name}")
        print(f"[KOKORO] {target.name}: {sample_rate} Hz, {target.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
