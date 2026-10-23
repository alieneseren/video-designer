"""
chatterbox_voice.py
===================
Resemble AI Chatterbox TTS Entegrasyonu.
Apple Silicon (MPS) GPU hızlandırması ile yerel çalışır, stüdyo kalitesinde seslendirme üretir.
Edge-TTS gibi dış API ve rate limit (403 Handshake) kısıtlamalarına takılmaz.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
import soundfile as sf
import torch

CHATTERBOX_ROOT = Path(__file__).resolve().parent.parent / "chatterbox" / "src"
if str(CHATTERBOX_ROOT) not in sys.path:
    sys.path.insert(0, str(CHATTERBOX_ROOT))


class ChatterboxVoiceEngine:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChatterboxVoiceEngine, cls).__new__(cls)
        return cls._instance

    def _get_device(self) -> str:
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def get_model(self):
        if self._model is None:
            device = self._get_device()
            map_location = torch.device(device)
            orig_load = torch.load
            # MPS uyumluluk yaması
            torch.load = lambda *a, **k: orig_load(*a, **{**k, "map_location": map_location} if "map_location" not in k else k)

            print(f"[Chatterbox] Model {device.upper()} üzerinde yükleniyor...")
            from chatterbox.tts import ChatterboxTTS, Conditionals
            self._model = ChatterboxTTS.from_pretrained(device=device)

            # Varsayılan geliştirilmiş belgesel anlatıcı ses modelini (.pt) yükle
            default_pt = Path(__file__).resolve().parent.parent / "config" / "assets" / "voice_samples" / "documentary_narrator_v2.pt"
            if default_pt.exists():
                try:
                    self._model.conds = Conditionals.load(default_pt, map_location=map_location)
                    print(f"[Chatterbox] 🎙️ Geliştirilmiş Belgesel Anlatıcı Model v2 (.pt) aktif edildi.")
                except Exception as e_pt:
                    print(f"[Chatterbox] ⚠️ Conditionals yükleme uyarısı: {e_pt}")

            print("[Chatterbox] ✅ Model başarıyla hazırlandı.")
        return self._model

    def synthesize(self, text: str, output_path: str, audio_prompt_path: str = None) -> bool:
        """Metni seslendirir ve stüdyo mastering'li broadcast MP3/WAV formatında kaydeder."""
        try:
            model = self.get_model()
            text_clean = text.strip()
            if not text_clean:
                return False

            if audio_prompt_path and str(audio_prompt_path).endswith(".pt"):
                from chatterbox.tts import Conditionals
                device = self._get_device()
                model.conds = Conditionals.load(audio_prompt_path, map_location=torch.device(device))
                wav = model.generate(
                    text_clean,
                    exaggeration=1.1,
                    cfg_weight=0.6
                )
            elif audio_prompt_path:
                wav = model.generate(
                    text_clean,
                    audio_prompt_path=audio_prompt_path,
                    exaggeration=1.1,
                    cfg_weight=0.6
                )
            else:
                wav = model.generate(
                    text_clean,
                    exaggeration=1.1,
                    cfg_weight=0.6
                )
            audio_data = wav.cpu().squeeze().numpy()

            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            if out_p.suffix.lower() == ".mp3":
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_f:
                    tmp_wav = tmp_f.name
                sf.write(tmp_wav, audio_data, model.sr)
                # FFmpeg ile broadcast kalitesinde ve belgesel mastering'li MP3 yap
                # 60Hz High-pass, 3.2kHz netlik, 2:1 kompresör, -14 LUFS EBU R128 loudness
                master_filter = (
                    "highpass=f=60,"
                    "equalizer=f=3200:width_type=q:w=1.2:g=1.8,"
                    "acompressor=threshold=-18dB:ratio=2.0:attack=10:release=120,"
                    "loudnorm=I=-14:TP=-1.0:LRA=7"
                )
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", tmp_wav,
                        "-af", master_filter,
                        "-codec:a", "libmp3lame", "-b:a", "192k",
                        str(out_p)
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                try:
                    os.remove(tmp_wav)
                except Exception:
                    pass
            else:
                sf.write(str(out_p), audio_data, model.sr)

            return True
        except Exception as e:
            print(f"[Chatterbox] ❌ Ses sentezleme hatası: {e}")
            return False

    def synthesize_material_scenes(self, material_folder: Path, scenes: list, audio_prompt_path: str = None) -> int:
        """Materyal klasöründeki tüm sahneler için scene_{idx}_audio.mp3 üretir."""
        material_folder = Path(material_folder)
        generated_count = 0
        for idx, sc in enumerate(scenes):
            narration = sc.get("narration") or sc.get("text") or sc.get("voiceover") or ""
            if not narration:
                continue
            out_file = material_folder / f"scene_{idx}_audio.mp3"
            if out_file.exists() and out_file.stat().st_size > 5000:
                generated_count += 1
                continue
            ok = self.synthesize(narration, str(out_file), audio_prompt_path=audio_prompt_path)
            if ok:
                generated_count += 1
                print(f"[Chatterbox] ✅ Sahne {idx} sesi broadcast kalitesinde üretildi ({out_file.name})")
        return generated_count
