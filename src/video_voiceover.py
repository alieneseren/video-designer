"""Re-synthesize a video's spoken audio using a saved Chatterbox voice clone."""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
import re
from typing import Any


def build_mux_command(
    ffmpeg: str,
    video_path: str,
    audio_path: str,
    output_path: str,
    video_duration: float,
    voice_duration: float,
) -> list[str]:
    command = [ffmpeg, "-y", "-i", video_path, "-i", audio_path]
    if voice_duration > video_duration + 0.1:
        extra_duration = voice_duration - video_duration
        command.extend([
            "-vf", f"tpad=stop_mode=clone:stop_duration={extra_duration:.3f}",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-map", "0:s?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-c:s", "mov_text",
            "-t", f"{voice_duration:.3f}",
        ])
    else:
        command.extend([
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-map", "0:s?",
            "-c:v", "copy",
            "-af", f"apad=whole_dur={video_duration:.3f}",
            "-c:a", "aac",
            "-b:a", "192k",
            "-c:s", "mov_text",
            "-t", f"{video_duration:.3f}",
        ])
    command.append(output_path)
    return command


def _atempo_filters(speed: float) -> list[str]:
    filters = []
    while speed > 2.0:
        filters.append("atempo=2.0")
        speed /= 2.0
    if speed > 1.001:
        filters.append(f"atempo={speed:.6f}")
    return filters


def build_timeline_audio_command(
    ffmpeg: str,
    segments: list[dict[str, Any]],
    output_path: str,
    video_duration: float,
) -> list[str]:
    """Place synthesized speech at the source transcription timestamps."""
    if not segments:
        raise ValueError("Senkron ses üretmek için en az bir konuşma segmenti gerekir.")

    command = [ffmpeg, "-y"]
    filters = []
    labels = []
    for index, segment in enumerate(segments):
        command.extend(["-i", str(segment["audio_path"])])
        start = max(0.0, float(segment["start"]))
        next_start = (
            max(start, float(segments[index + 1]["start"]))
            if index + 1 < len(segments)
            else video_duration
        )
        end = min(float(segment["end"]), next_start, video_duration)
        slot_duration = end - start
        if slot_duration <= 0:
            raise ValueError(f"Konuşma segmenti {index + 1} için zaman aralığı geçersiz.")

        source_duration = float(segment["audio_duration"])
        if source_duration <= 0:
            raise ValueError(f"Konuşma segmenti {index + 1} için ses süresi geçersiz.")
        tempo = _atempo_filters(source_duration / slot_duration)
        tempo_chain = ",".join(tempo)
        if tempo_chain:
            tempo_chain = f",{tempo_chain}"
        delay_ms = round(start * 1000)
        label = f"voice{index}"
        filters.append(
            f"[{index}:a:0]aresample=48000{tempo_chain},"
            f"atrim=duration={slot_duration:.6f},asetpts=PTS-STARTPTS,"
            f"adelay=delays={delay_ms}:all=1[{label}]"
        )
        labels.append(f"[{label}]")

    filters.append(
        f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:"
        "dropout_transition=0:normalize=0[mixed]"
    )
    filters.append(
        f"[mixed]apad=whole_dur={video_duration:.6f},"
        f"atrim=duration={video_duration:.6f}[out]"
    )
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[out]",
        "-ar", "48000",
        "-ac", "2",
        "-c:a", "pcm_s16le",
        output_path,
    ])
    return command


class VideoVoiceoverManager:
    _instance: "VideoVoiceoverManager | None" = None
    _instance_lock = threading.Lock()
    _synthesis_lock = threading.Lock()
    _jobs: dict[str, dict[str, Any]] = {}
    _jobs_lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def start_job(
        self,
        *,
        video_path: Path,
        clone_id: str,
        clone_name: str,
        voice_prompt_path: Path,
    ) -> str:
        job_id = f"voiceover_{uuid.uuid4().hex}"
        with self._jobs_lock:
            if any(
                job.get("video_path") == str(video_path)
                and job.get("clone_id") == clone_id
                and job.get("status") in {"queued", "processing"}
                for job in self._jobs.values()
            ):
                raise ValueError("Bu video ve ses klonu için bir işlem zaten devam ediyor.")
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "progress": 0,
                "stage": "Kuyruğa alındı",
                "video_path": str(video_path),
                "clone_id": clone_id,
                "clone_name": clone_name,
                "error": None,
                "result": None,
                "created_at": time.time(),
            }
        threading.Thread(
            target=self._run_job,
            args=(job_id, video_path, clone_id, clone_name, voice_prompt_path),
            daemon=True,
        ).start()
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return {key: value for key, value in job.items() if key != "created_at"}

    def _update(self, job_id: str, **updates: Any) -> None:
        with self._jobs_lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(updates)

    def _run_job(
        self,
        job_id: str,
        video_path: Path,
        clone_id: str,
        clone_name: str,
        voice_prompt_path: Path,
    ) -> None:
        safe_clone_id = re.sub(r"[^A-Za-z0-9_-]+", "_", clone_id)[:80] or "clone"
        output_path = video_path.with_name(f"{video_path.stem[:120]}_voice_{safe_clone_id}.mp4")
        temp_audio = video_path.parent / f".{job_id}_voice.wav"
        temp_output = video_path.parent / f".{job_id}_output.mp4"
        temp_segment_paths: list[Path] = []
        started = time.perf_counter()
        try:
            self._update(job_id, status="processing", progress=5, stage="Videodaki konuşma çözümleniyor")
            from faster_whisper import WhisperModel

            whisper = WhisperModel("base", device="cpu", compute_type="int8")
            transcribed_segments, info = whisper.transcribe(str(video_path), vad_filter=True)
            speech_segments = [
                {
                    "text": segment.text.strip(),
                    "start": float(segment.start),
                    "end": float(segment.end),
                }
                for segment in transcribed_segments
                if segment.text.strip()
            ]
            transcript = " ".join(segment["text"] for segment in speech_segments).strip()
            if not transcript:
                raise RuntimeError("Videoda dönüştürülebilecek bir konuşma bulunamadı.")

            language = (getattr(info, "language", None) or "").lower()
            from chatterbox.mtl_tts import SUPPORTED_LANGUAGES

            if language not in SUPPORTED_LANGUAGES:
                raise RuntimeError(
                    f"Videonun konuşma dili ({language or 'belirlenemedi'}) seçilen Chatterbox ses modeli tarafından desteklenmiyor."
                )

            from chatterbox_generator import ChatterboxAudioGenerator

            ffmpeg = shutil.which("ffmpeg")
            ffprobe = shutil.which("ffprobe")
            if not ffmpeg or not ffprobe:
                raise RuntimeError("Video sesini birleştirmek için ffmpeg ve ffprobe kurulu olmalı.")
            video_duration = self._probe_duration(ffprobe, video_path)
            generator = ChatterboxAudioGenerator()
            aligned_segments = []
            with self._synthesis_lock:
                for index, segment in enumerate(speech_segments):
                    start = max(0.0, min(segment["start"], video_duration))
                    end = max(start, min(segment["end"], video_duration))
                    if not segment["text"] or end <= start:
                        continue
                    segment_path = video_path.parent / f".{job_id}_segment_{index:04d}.wav"
                    temp_segment_paths.append(segment_path)
                    generated, _ = generator.generate(
                        text=segment["text"],
                        lang=language,
                        output_path=str(segment_path),
                        audio_prompt_path=str(voice_prompt_path),
                        require_audio_prompt=True,
                    )
                    if not generated or not segment_path.is_file() or segment_path.stat().st_size < 1000:
                        raise RuntimeError(f"Klon sesle konuşma parçası üretilemedi ({index + 1}. parça).")
                    aligned_segments.append({
                        **segment,
                        "start": start,
                        "end": end,
                        "audio_path": segment_path,
                        "audio_duration": self._probe_duration(ffprobe, segment_path),
                    })
                    self._update(
                        job_id,
                        progress=35 + int(35 * (index + 1) / max(1, len(speech_segments))),
                        stage=f"Altyazı zamanına göre konuşma sentezleniyor ({index + 1}/{len(speech_segments)})",
                        transcript=transcript,
                    )

            if not aligned_segments:
                raise RuntimeError("Videoda seslendirilecek, geçerli zamanlı bir konuşma bulunamadı.")
            subprocess.run(
                build_timeline_audio_command(
                    ffmpeg,
                    aligned_segments,
                    str(temp_audio),
                    video_duration,
                ),
                capture_output=True,
                check=True,
                timeout=1800,
            )

            self._update(job_id, progress=75, stage="Senkron klon ses ve altyazılar videoya ekleniyor")
            command = build_mux_command(
                ffmpeg,
                str(video_path),
                str(temp_audio),
                str(temp_output),
                video_duration,
                video_duration,
            )
            subprocess.run(command, capture_output=True, check=True, timeout=1800)
            if not temp_output.is_file() or temp_output.stat().st_size < 10000:
                raise RuntimeError("Seslendirilmiş video çıktısı oluşturulamadı.")
            temp_output.replace(output_path)
            copied_subtitles = self._copy_subtitle_sidecars(video_path, output_path)
            self._update(
                job_id,
                status="completed",
                progress=100,
                stage="Ses klonlama tamamlandı",
                result={
                    "video_path": str(output_path),
                    "clone_id": clone_id,
                    "clone_name": clone_name,
                    "language": language,
                    "transcript": transcript,
                    "subtitle_sidecars": copied_subtitles,
                    "aligned_segments": len(aligned_segments),
                    "processing_time_sec": round(time.perf_counter() - started, 2),
                },
            )
        except Exception as exc:
            self._update(
                job_id,
                status="failed",
                stage="Ses klonlama başarısız",
                error=str(exc),
            )
        finally:
            temp_audio.unlink(missing_ok=True)
            temp_output.unlink(missing_ok=True)
            for segment_path in temp_segment_paths:
                segment_path.unlink(missing_ok=True)

    @staticmethod
    def _copy_subtitle_sidecars(video_path: Path, output_path: Path) -> list[str]:
        candidates = [
            video_path.with_suffix(suffix)
            for suffix in (".srt", ".ass", ".ssa", ".vtt")
        ]
        candidates.extend(
            video_path.parent / f"subtitles{suffix}"
            for suffix in (".srt", ".ass", ".ssa", ".vtt")
        )
        copied = []
        seen = set()
        seen_destinations = set()
        for subtitle_path in candidates:
            destination = output_path.with_suffix(subtitle_path.suffix)
            if (
                subtitle_path in seen
                or destination in seen_destinations
                or not subtitle_path.is_file()
            ):
                continue
            seen.add(subtitle_path)
            shutil.copy2(subtitle_path, destination)
            seen_destinations.add(destination)
            copied.append(str(destination))
        return copied

    @staticmethod
    def _probe_duration(ffprobe: str, media_path: Path) -> float:
        result = subprocess.run(
            [
                ffprobe, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(media_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        try:
            duration = float(result.stdout.strip())
        except ValueError as exc:
            raise RuntimeError(f"Medya süresi okunamadı: {media_path.name}") from exc
        if duration <= 0:
            raise RuntimeError(f"Medya süresi geçersiz: {media_path.name}")
        return duration
