"""
HyperFrames Video Renderer Bridge for yt-oto-video.
Provides deterministic, HTML/CSS/GSAP-based video rendering via HeyGen HyperFrames.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("hyperframes_renderer")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HYPERFRAMES_DIR = PROJECT_ROOT / "hyperframes"
HYPERFRAMES_BIN = HYPERFRAMES_DIR / "node_modules" / ".bin" / "hyperframes"
TEMPLATES_DIR = HYPERFRAMES_DIR / "templates"


def is_hyperframes_available() -> bool:
    """Checks if Node.js and HyperFrames CLI are installed and ready."""
    if not HYPERFRAMES_BIN.exists():
        return False
    if not shutil.which("node"):
        return False
    return True


def render_project(
    project_dir: Path | str,
    output_path: Path | str,
    variables: Optional[Dict[str, Any]] = None,
    fps: int = 30,
    timeout_sec: int = 180,
) -> bool:
    """
    Renders an existing HyperFrames project directory to an MP4 video file.
    
    :param project_dir: Path to directory containing index.html and hyperframes.json.
    :param output_path: Target .mp4 file path.
    :param variables: Optional dictionary of variables injected into window.__hyperframes.getVariables().
    :param fps: Target render FPS (default: 30).
    :param timeout_sec: Subprocess timeout in seconds.
    :return: True if render succeeded, False otherwise.
    """
    if not is_hyperframes_available():
        logger.error("[HYPERFRAMES] CLI bulunamadı (%s)", HYPERFRAMES_BIN)
        return False

    proj_path = Path(project_dir).resolve()
    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not (proj_path / "index.html").exists():
        logger.error("[HYPERFRAMES] Proje dizininde index.html bulunamadı: %s", proj_path)
        return False

    cmd = [
        str(HYPERFRAMES_BIN.resolve()),
        "render",
        "-o",
        str(out_path),
        "--fps",
        str(fps),
    ]

    if variables:
        cmd.extend(["--variables", json.dumps(variables, ensure_ascii=False)])

    try:
        logger.info("[HYPERFRAMES] Render başlatılıyor: %s -> %s", proj_path.name, out_path.name)
        result = subprocess.run(
            cmd,
            cwd=str(proj_path),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

        if result.returncode != 0:
            logger.error("[HYPERFRAMES] Render hatası:\n%s", result.stderr[-1000:])
            return False

        if out_path.exists() and out_path.stat().st_size > 1000:
            logger.info("[HYPERFRAMES] Render başarıyla tamamlandı: %s (%.1f MB)", out_path.name, out_path.stat().st_size / (1024 * 1024))
            return True

        logger.error("[HYPERFRAMES] Çıktı dosyası oluşmadı veya çok küçük: %s", out_path)
        return False

    except subprocess.TimeoutExpired:
        logger.error("[HYPERFRAMES] Render zaman aşımına uğradı (%d sn): %s", timeout_sec, proj_path)
        return False
    except Exception as exc:
        logger.error("[HYPERFRAMES] Beklenmeyen hata: %s", exc)
        return False


def render_kinetic_hook(
    title: str,
    subtitle: str = "",
    badge: str = "ÖZEL BÖLÜM",
    output_path: Optional[Path | str] = None,
) -> Optional[Path]:
    """
    Renders a 4-second modern avant-garde kinetic typography hook for YouTube Shorts (1080x1920).
    
    :param title: Main hook headline.
    :param subtitle: Supporting hook text.
    :param badge: Pill badge label (e.g. "SHORTS", "BUNU BİLİYOR MUYDUNUZ?").
    :param output_path: Where to save the resulting .mp4 file.
    :return: Path to output MP4 if successful, None otherwise.
    """
    hook_template_dir = TEMPLATES_DIR / "kinetic_hook"
    if not hook_template_dir.exists():
        logger.error("[HYPERFRAMES] kinetic_hook şablonu bulunamadı: %s", hook_template_dir)
        return None

    if output_path is None:
        import uuid
        output_path = PROJECT_ROOT / "output" / f"hook_{uuid.uuid4().hex[:8]}.mp4"
    else:
        output_path = Path(output_path)

    variables = {
        "title": title.strip(),
        "subtitle": subtitle.strip(),
        "badge": badge.strip(),
    }

    success = render_project(hook_template_dir, output_path, variables=variables)
    return output_path if success else None


def prepend_hook_to_video(
    hook_video_path: Path | str,
    main_video_path: Path | str,
    output_path: Path | str,
) -> bool:
    """
    Seamlessly concatenates a HyperFrames hook video to the front of a main video using FFmpeg.
    Normalizes audio/video streams to prevent desync or glitching.
    """
    hook_p = Path(hook_video_path).resolve()
    main_p = Path(main_video_path).resolve()
    out_p = Path(output_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    if not hook_p.exists() or not main_p.exists():
        logger.error("[HYPERFRAMES] Birleştirilecek videolardan biri bulunamadı (%s veya %s)", hook_p, main_p)
        return False

    # FFmpeg concat filter with video scale & audio resample to ensure 100% smooth transition
    cmd = [
        "ffmpeg", "-y",
        "-i", str(hook_p),
        "-i", str(main_p),
        "-filter_complex",
        (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v0];"
            "[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v1];"
            "[0:a]aresample=44100[a0];"
            "[1:a]aresample=44100[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
        ),
        "-map", "[outv]",
        "-map", "[outa]",
    ]

    import platform
    if platform.system() == "Darwin" and platform.machine() in ("arm64", "aarch64"):
        cmd.extend(["-c:v", "h264_videotoolbox", "-b:v", "8000k"])
    else:
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "18"])

    cmd.extend([
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_p)
    ])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return res.returncode == 0 and out_p.exists()
    except Exception as exc:
        logger.error("[HYPERFRAMES] Concat hatası: %s", exc)
        return False


def apply_hook_zoom_filter(
    video_path: Path | str,
    output_path: Path | str,
    hook_duration: float = 1.5,
    start_scale: float = 1.05,
) -> bool:
    """
    Casper AI: Videonun ilk hook_duration saniyesinde (varsayılan 1.5s)
    %105'ten %100'e yumuşak Ken Burns zoom-in uygulayarak izleyicinin parmak kaydırmasını (Thumb-stop) engeller.
    """
    in_p = Path(video_path).resolve()
    out_p = Path(output_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    if not in_p.exists():
        logger.error("[HYPERFRAMES] Video bulunamadı: %s", in_p)
        return False

    try:
        from src.video_editor import apply_hook_intro_zoom
        from moviepy import VideoFileClip
        with VideoFileClip(str(in_p)) as clip:
            zoomed = apply_hook_intro_zoom(clip, hook_duration=hook_duration, start_scale=start_scale)
            zoomed.write_videofile(
                str(out_p),
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )
        return out_p.exists()
    except Exception as exc:
        logger.error("[HYPERFRAMES] Hook zoom filtresi hatası: %s", exc)
        return False

