"""
Clean, High-Performance, Local-First Voice Engine.
Derived from VoiceStudio core concepts, stripped of all bloat, electron, and supply-chain risks.
Supports:
- Local Kokoro-82M ONNX (Ultra-fast, studio grade English/Japanese/Spanish/French voices)
- Edge-TTS fallback (Multi-lingual & cloud backup)
- OpenAI-compatible audio protocol: POST /v1/audio/speech, GET /v1/audio/voices, GET /v1/models
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("voice_engine")

# Default model locations
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models" / "kokoro"
KOKORO_ONNX_PATH = MODEL_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES_PATH = MODEL_DIR / "voices-v1.0.bin"

# Curated Persona Presets for YouTube Channels
VOICE_PERSONAS: Dict[str, Dict[str, Any]] = {
    # Blackbox Audio (Aviation Documentaries)
    "aviation_narrator": {
        "engine": "kokoro",
        "voice": "am_adam",
        "description": "Deep, calm, dramatic documentary narrator for aviation catastrophes",
        "gender": "male",
        "language": "en-us",
        "recommended_speed": 1.0,
    },
    "aviation_investigator": {
        "engine": "kokoro",
        "voice": "am_michael",
        "description": "Authoritative NTSB investigator tone, measured and technical",
        "gender": "male",
        "language": "en-us",
        "recommended_speed": 0.98,
    },
    "atc_tower": {
        "engine": "kokoro",
        "voice": "am_echo",
        "description": "Crisp, concise Air Traffic Controller / Tower radio delivery",
        "gender": "male",
        "language": "en-us",
        "recommended_speed": 1.05,
    },
    # Tactical Crayon (Military Satire & Procurement Breakdown)
    "tactical_analyst": {
        "engine": "kokoro",
        "voice": "bm_george",
        "description": "Sophisticated, cynical military procurement analyst / British accent",
        "gender": "male",
        "language": "en-gb",
        "recommended_speed": 1.02,
    },
    "tactical_host": {
        "engine": "kokoro",
        "voice": "am_onyx",
        "description": "Heavy baritone, sarcastic military gear debunker",
        "gender": "male",
        "language": "en-us",
        "recommended_speed": 1.0,
    },
    # Standard OpenAI Mappings
    "alloy": {"engine": "kokoro", "voice": "af_alloy", "gender": "female", "language": "en-us"},
    "echo": {"engine": "kokoro", "voice": "am_echo", "gender": "male", "language": "en-us"},
    "fable": {"engine": "kokoro", "voice": "bm_fable", "gender": "male", "language": "en-gb"},
    "onyx": {"engine": "kokoro", "voice": "am_onyx", "gender": "male", "language": "en-us"},
    "nova": {"engine": "kokoro", "voice": "af_nova", "gender": "female", "language": "en-us"},
    "shimmer": {"engine": "kokoro", "voice": "af_nicole", "gender": "female", "language": "en-us"},
    # Turkish Fallbacks (Edge-TTS)
    "tr_narrator_male": {"engine": "edge-tts", "voice": "tr-TR-AhmetNeural", "gender": "male", "language": "tr-tr"},
    "tr_narrator_female": {"engine": "edge-tts", "voice": "tr-TR-EmelNeural", "gender": "female", "language": "tr-tr"},
}


class VoiceEngine:
    _instance: Optional["VoiceEngine"] = None

    def __init__(self, onnx_path: Optional[Path] = None, voices_path: Optional[Path] = None):
        self.onnx_path = Path(onnx_path or KOKORO_ONNX_PATH)
        self.voices_path = Path(voices_path or KOKORO_VOICES_PATH)
        self._kokoro_instance = None
        self._kokoro_voices: List[str] = []
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "VoiceEngine":
        if cls._instance is None:
            cls._instance = VoiceEngine()
        return cls._instance

    @property
    def is_kokoro_available(self) -> bool:
        return self.onnx_path.is_file() and self.voices_path.is_file()

    def _ensure_kokoro(self):
        if self._kokoro_instance is not None:
            return self._kokoro_instance

        if not self.is_kokoro_available:
            raise FileNotFoundError(
                f"Kokoro model files not found at {self.onnx_path} or {self.voices_path}."
            )

        try:
            from kokoro_onnx import Kokoro
        except ImportError:
            raise ImportError("kokoro-onnx package is not installed.")

        logger.info(f"Loading Kokoro-ONNX model from {self.onnx_path}...")
        t0 = time.time()
        self._kokoro_instance = Kokoro(str(self.onnx_path), str(self.voices_path))
        self._kokoro_voices = self._kokoro_instance.get_voices()
        logger.info(f"Kokoro-ONNX model loaded in {time.time() - t0:.2f}s with {len(self._kokoro_voices)} voices.")
        return self._kokoro_instance

    def list_voices(self) -> List[Dict[str, Any]]:
        """Return list of all available voices across Kokoro, Edge-TTS and custom personas."""
        voices_list = []

        # Add personas first
        for name, p in VOICE_PERSONAS.items():
            voices_list.append({
                "voice_id": name,
                "name": name.replace("_", " ").title(),
                "engine": p["engine"],
                "target_voice": p["voice"],
                "category": "Curated Channel Persona" if "narrator" in name or "tactical" in name or "atc" in name else "OpenAI Mapping",
                "gender": p.get("gender", "neutral"),
                "language": p.get("language", "en-us"),
                "description": p.get("description", ""),
            })

        # Add Kokoro native voices
        if self.is_kokoro_available:
            try:
                engine = self._ensure_kokoro()
                for v in self._kokoro_voices:
                    if v not in VOICE_PERSONAS:
                        gender = "female" if v.startswith(("af_", "bf_", "ef_", "ff_", "hf_", "if_", "jf_", "pf_", "zf_")) else "male"
                        lang = "en-us" if v.startswith("a") else "en-gb" if v.startswith("b") else "other"
                        voices_list.append({
                            "voice_id": v,
                            "name": v,
                            "engine": "kokoro",
                            "target_voice": v,
                            "category": "Kokoro Native",
                            "gender": gender,
                            "language": lang,
                            "description": f"Kokoro v1.0 native model voice ({gender})",
                        })
            except Exception as e:
                logger.warning(f"Could not inspect Kokoro voices: {e}")

        # Add user-uploaded voice clones from registry.json
        clones_reg = BASE_DIR / "data" / "voice_clones" / "registry.json"
        if clones_reg.is_file():
            try:
                import json
                data = json.loads(clones_reg.read_text(encoding="utf-8"))
                for c in data.get("clones", []):
                    c_id = c.get("id")
                    if c_id:
                        voices_list.append({
                            "voice_id": c_id,
                            "name": c.get("name") or c_id,
                            "engine": "voice_clone",
                            "target_voice": c.get("voice_wav_path") or c.get("voice_pt_path") or "",
                            "category": "User Voice Clone",
                            "gender": "custom",
                            "language": "custom",
                            "description": c.get("description", "Kullanıcı tarafından yüklenen örnek ses profili"),
                        })
            except Exception as ex:
                logger.warning(f"Could not load custom voice clones: {ex}")

        # Add prominent Edge-TTS voices
        edge_defaults = [
            ("en-US-ChristopherNeural", "male", "en-us", "Edge-TTS Christopher (Radio/Narrator)"),
            ("en-US-GuyNeural", "male", "en-us", "Edge-TTS Guy (News/Documentary)"),
            ("en-US-JennyNeural", "female", "en-us", "Edge-TTS Jenny (Conversational)"),
            ("tr-TR-AhmetNeural", "male", "tr-tr", "Edge-TTS Ahmet (Turkish Documentary)"),
            ("tr-TR-EmelNeural", "female", "tr-tr", "Edge-TTS Emel (Turkish Professional)"),
        ]
        for v_id, gender, lang, desc in edge_defaults:
            voices_list.append({
                "voice_id": v_id,
                "name": v_id,
                "engine": "edge-tts",
                "target_voice": v_id,
                "category": "Edge-TTS Cloud",
                "gender": gender,
                "language": lang,
                "description": desc,
            })

        return voices_list

    def clean_text_for_speech(self, text: str) -> str:
        """Strip markdown, excessive punctuation, and formatting markers."""
        if not text:
            return ""
        # Remove markdown bold/italic/links
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"[*_~`#]", "", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def synthesize(
        self,
        text: str,
        voice: str = "am_adam",
        speed: float = 1.0,
        response_format: Literal["wav", "mp3"] = "wav",
        lang: Optional[str] = None,
    ) -> Tuple[bytes, int]:
        """
        Synthesize text to raw audio bytes and sample rate.
        Supports Kokoro-ONNX and fallback to Edge-TTS.
        """
        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            raise ValueError("Input text cannot be empty.")

        # Resolve persona aliases
        actual_voice = voice
        target_engine = "kokoro"
        target_lang = lang or "en-us"

        if voice in VOICE_PERSONAS:
            p = VOICE_PERSONAS[voice]
            actual_voice = p["voice"]
            target_engine = p["engine"]
            target_lang = lang or p.get("language", "en-us")
            if "recommended_speed" in p and speed == 1.0:
                speed = p["recommended_speed"]
        elif voice.startswith(("tr-", "en-", "de-", "es-", "fr-")) and "Neural" in voice:
            target_engine = "edge-tts"
        elif not self.is_kokoro_available:
            target_engine = "edge-tts"

        # Route to selected engine
        if target_engine == "kokoro" and self.is_kokoro_available:
            try:
                wav_bytes, sample_rate = await self._synthesize_kokoro(
                    clean_text, actual_voice, speed, target_lang
                )
            except Exception as e:
                logger.warning(f"Kokoro synthesis failed ({e}), falling back to Edge-TTS.")
                wav_bytes, sample_rate = await self._synthesize_edge_tts(
                    clean_text, "en-US-ChristopherNeural", speed
                )
        else:
            edge_v = actual_voice if "Neural" in actual_voice else "en-US-ChristopherNeural"
            wav_bytes, sample_rate = await self._synthesize_edge_tts(clean_text, edge_v, speed)

        # Convert to MP3 if requested
        if response_format == "mp3":
            mp3_bytes = self._convert_wav_to_mp3(wav_bytes)
            return mp3_bytes, sample_rate

        return wav_bytes, sample_rate

    async def _synthesize_kokoro(
        self, text: str, voice: str, speed: float, lang: str
    ) -> Tuple[bytes, int]:
        """Run Kokoro-ONNX in worker thread."""
        kokoro = self._ensure_kokoro()
        
        # Valid kokoro language codes: 'en-us', 'en-gb', 'ja', 'zh', 'es', 'fr-fr', 'hi', 'it', 'pt-br'
        k_lang = lang.lower()
        if k_lang not in ["en-us", "en-gb", "ja", "zh", "es", "fr-fr", "hi", "it", "pt-br"]:
            k_lang = "en-us"

        def _run():
            samples, sample_rate = kokoro.create(
                text,
                voice=voice,
                speed=float(speed),
                lang=k_lang,
            )
            buf = io.BytesIO()
            sf.write(buf, samples, sample_rate, format="WAV")
            return buf.getvalue(), sample_rate

        return await asyncio.to_thread(_run)

    async def _synthesize_edge_tts(
        self, text: str, voice: str, speed: float
    ) -> Tuple[bytes, int]:
        """Synthesize via Edge-TTS and convert to WAV."""
        import edge_tts

        rate_pct = int(round((speed - 1.0) * 100))
        rate_str = f"{rate_pct:+d}%" if rate_pct != 0 else "+0%"

        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        mp3_buf = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_buf.extend(chunk["data"])

        # Convert MP3 to standard 24kHz / 16-bit WAV
        cmd = [
            "ffmpeg", "-y", "-i", "pipe:0",
            "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1",
            "-f", "wav", "pipe:1"
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate(input=bytes(mp3_buf))
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg error converting Edge-TTS: {stderr.decode('utf-8', errors='ignore')}")

        return stdout, 24000

    def _convert_wav_to_mp3(self, wav_bytes: bytes) -> bytes:
        """Convert WAV byte stream to 192kbps MP3."""
        cmd = [
            "ffmpeg", "-y", "-i", "pipe:0",
            "-codec:a", "libmp3lame", "-qscale:a", "2",
            "-f", "mp3", "pipe:1"
        ]
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        out, err = p.communicate(input=wav_bytes)
        if p.returncode != 0:
            logger.warning(f"MP3 conversion error ({err.decode()[:100]}), returning original WAV.")
            return wav_bytes
        return out

    async def synthesize_to_file(
        self, text: str, output_path: Union[str, Path], voice: str = "am_adam", speed: float = 1.0
    ) -> Path:
        """Synthesize and write directly to destination file."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fmt = "mp3" if target.suffix.lower() == ".mp3" else "wav"
        data, _ = await self.synthesize(text, voice=voice, speed=speed, response_format=fmt)
        target.write_bytes(data)
        return target


# ── Global Singleton Access ──────────────────────────────────────────────────
_global_engine: Optional[VoiceEngine] = None

def get_voice_engine() -> VoiceEngine:
    global _global_engine
    if _global_engine is None:
        _global_engine = VoiceEngine.get_instance()
    return _global_engine


# ── OpenAI-Compatible FastAPI Router ──────────────────────────────────────────

router = APIRouter(prefix="/v1", tags=["OpenAI Audio Compatibility"])


class OpenAISpeechRequest(BaseModel):
    model: str = Field(default="tts-1", description="Model ID: tts-1, tts-1-hd, kokoro, edge-tts")
    input: str = Field(..., description="Text to synthesize")
    voice: str = Field(default="am_adam", description="Voice identifier or persona alias")
    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = Field(
        default="mp3", description="Audio format"
    )
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="Speed factor")


@router.post("/audio/speech")
async def openai_speech_endpoint(req: OpenAISpeechRequest):
    """OpenAI standard /v1/audio/speech endpoint."""
    engine = get_voice_engine()
    fmt = "mp3" if req.response_format != "wav" else "wav"
    try:
        audio_bytes, sr = await engine.synthesize(
            text=req.input,
            voice=req.voice,
            speed=req.speed,
            response_format=fmt,
        )
        media_type = "audio/mpeg" if fmt == "mp3" else "audio/wav"
        return Response(
            content=audio_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="speech.{fmt}"',
                "X-Engine": "Kokoro-ONNX" if engine.is_kokoro_available else "Edge-TTS",
                "X-Sample-Rate": str(sr),
            },
        )
    except Exception as e:
        logger.error(f"Speech generation error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": {"message": str(e), "type": "server_error", "code": 500}},
        )


@router.get("/audio/voices")
async def list_voices_endpoint():
    """List all available voices, personas, and engines."""
    engine = get_voice_engine()
    return {
        "voices": engine.list_voices(),
        "total": len(engine.list_voices()),
        "kokoro_active": engine.is_kokoro_available,
    }


@router.get("/models")
async def list_models_endpoint():
    """OpenAI compatible /v1/models endpoint."""
    return {
        "object": "list",
        "data": [
            {"id": "tts-1", "object": "model", "owned_by": "local-voice-engine"},
            {"id": "tts-1-hd", "object": "model", "owned_by": "local-voice-engine"},
            {"id": "kokoro-82m", "object": "model", "owned_by": "kokoro-onnx"},
            {"id": "edge-tts", "object": "model", "owned_by": "microsoft-cloud"},
        ],
    }


@router.post("/audio/voices/upload")
async def upload_voice_endpoint(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """
    Örnek referans ses yükleme uç noktası.
    Yüklenen .wav veya .mp3 dosyasını kaydeder ve ses profilini sisteme kaydeder.
    """
    try:
        import json
        import shutil

        ext = Path(file.filename).suffix.lower()
        if ext not in [".wav", ".mp3", ".m4a", ".ogg", ".flac"]:
            raise HTTPException(status_code=400, detail="Desteklenmeyen ses formatı. Lütfen .wav veya .mp3 yükleyin.")

        clones_dir = BASE_DIR / "data" / "voice_clones"
        clones_dir.mkdir(parents=True, exist_ok=True)

        clean_slug = re.sub(r"[^a-zA-Z0-9_]", "_", (name or Path(file.filename).stem).lower())
        voice_id = f"vc_{clean_slug}_{int(time.time())}"
        target_folder = clones_dir / voice_id
        target_folder.mkdir(parents=True, exist_ok=True)

        saved_file = target_folder / f"voice{ext}"
        with open(saved_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Standardize to 24kHz Mono WAV
        wav_file = target_folder / "voice.wav"
        if ext != ".wav":
            cmd = ["ffmpeg", "-y", "-i", str(saved_file), "-ar", "24000", "-ac", "1", str(wav_file)]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        else:
            if saved_file != wav_file:
                shutil.copy(saved_file, wav_file)

        # Update registry.json
        reg_path = clones_dir / "registry.json"
        reg_data = {"active_id": "", "clones": []}
        if reg_path.is_file():
            try:
                reg_data = json.loads(reg_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        new_entry = {
            "id": voice_id,
            "name": name or file.filename,
            "description": description or "API üzerinden yüklenen örnek ses",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "voice_wav_path": str(wav_file.resolve()),
            "status": "ready"
        }
        reg_data["clones"].append(new_entry)
        reg_path.write_text(json.dumps(reg_data, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "success": True,
            "voice_id": voice_id,
            "name": new_entry["name"],
            "path": str(wav_file.resolve()),
            "message": f"'{new_entry['name']}' örnek sesi başarıyla yüklendi ve sisteme kaydedildi."
        }
    except Exception as e:
        logger.error(f"Voice upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ses yükleme hatası: {str(e)}")
