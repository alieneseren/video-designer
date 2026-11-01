"""
procedural_film_renderer.py
===========================
Pure Code-Based Procedural Film & Animation Rendering Engine for yt-oto-video.
Integrates curated, deterministic HTML5/Canvas/WebGL visual styles (Lemo-Opuscar safe core)
using Playwright and FFmpeg. Zero video/image API costs.
"""

from __future__ import annotations

import http.server
import json
import logging
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("procedural_film_renderer")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCEDURAL_DIR = PROJECT_ROOT / "procedural_styles"
STYLES_DIR = PROCEDURAL_DIR / "styles"
CORE_DIR = PROCEDURAL_DIR / "core"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ProceduralHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Quiet HTTP handler serving sanitized procedural templates."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROCEDURAL_DIR), **kwargs)

    def log_message(self, format, *args):
        pass


def get_free_port() -> int:
    """Finds an available local port for the ephemeral web server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def list_procedural_styles() -> List[Dict[str, Any]]:
    """
    Returns the catalog of all available procedural styles.
    """
    if not STYLES_DIR.exists():
        return []

    styles = []
    for item in sorted(STYLES_DIR.iterdir()):
        if not item.is_dir() or item.name.startswith("_"):
            continue

        demo_dir = item / "demo"
        if not (demo_dir / "index.html").exists():
            continue

        style_info = {
            "slug": item.name,
            "title": item.name.replace("-", " ").title(),
            "category": "Procedural Animation",
            "has_poster": (item / "poster.jpg").exists(),
            "demo_url": f"/styles/{item.name}/demo/index.html",
        }

        # Check if style.json exists for metadata
        json_file = item / "style.json"
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    if isinstance(meta, dict):
                        style_info["title"] = meta.get("title", style_info["title"])
                        style_info["category"] = meta.get("category", style_info["category"])
                        style_info["description"] = meta.get("description", "")
            except Exception:
                pass

        styles.append(style_info)

    return styles


def render_procedural_film(
    style_name: str,
    output_path: str | Path,
    duration_sec: Optional[float] = None,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
    audio_path: Optional[str] = None,
    custom_query: str = "",
    timeout_sec: int = 300,
) -> Dict[str, Any]:
    """
    Renders a procedural style into a production-ready MP4 video file.
    
    :param style_name: Slug name of the style (e.g. 'blueprint', 'crayon-book', 'hologram-hud').
    :param output_path: Target .mp4 video path.
    :param duration_sec: Video duration in seconds. If None, reads window.DUR from the style.
    :param fps: Target frames per second (default: 30).
    :param width: Target width (default: 1920).
    :param height: Target height (default: 1080).
    :param audio_path: Optional path to speech/BGM audio to mux and normalize (-14 LUFS).
    :param custom_query: URL query string to pass to the template.
    :param timeout_sec: Max timeout for rendering.
    :return: Dict containing success flag, output path, frame count, and duration.
    """
    target_demo = STYLES_DIR / style_name / "demo"
    if not (target_demo / "index.html").exists():
        raise FileNotFoundError(f"Style '{style_name}' index.html not found at: {target_demo}")

    from playwright.sync_api import sync_playwright

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    temp_video = out_file.parent / f"_raw_{out_file.stem}_{int(time.time())}.mp4"

    port = get_free_port()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), ProceduralHTTPHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    logger.info("[PROCEDURAL] Server started on port %d for style %s", port, style_name)

    query_str = f"?{custom_query}" if custom_query else ""
    page_url = f"http://127.0.0.1:{port}/styles/{style_name}/demo/index.html{query_str}"

    total_frames = 0
    actual_dur = duration_sec or 10.0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-web-security",
                    "--allow-file-access-from-files",
                    "--enable-webgl",
                    "--use-gl=angle",
                ]
            )
            page = browser.new_page(viewport={"width": width, "height": height})

            # Catch network font errors gracefully inside page context
            page.add_init_script("""
                const origLoad = Document.prototype.fonts ? Document.prototype.fonts.load : null;
                if (origLoad) {
                    Document.prototype.fonts.load = function(...args) {
                        return origLoad.apply(this, args).catch(err => {
                            console.warn('[Font fallback]', err);
                            return [];
                        });
                    };
                }
            """)

            logger.info("[PROCEDURAL] Loading page: %s", page_url)
            page.goto(page_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for style ready flag
            try:
                page.wait_for_function("() => window.READY === true", timeout=15000)
            except Exception as wait_err:
                logger.warning("[PROCEDURAL] window.READY wait timeout (%s), proceeding anyway...", wait_err)

            # Determine video duration
            if duration_sec is None:
                style_dur = page.evaluate("() => typeof window.DUR === 'number' ? window.DUR : 10.0")
                actual_dur = float(style_dur) if style_dur > 0 else 10.0

            total_frames = max(1, int(actual_dur * fps))
            logger.info("[PROCEDURAL] Starting render: %d frames (%.2fs @ %d fps)", total_frames, actual_dur, fps)

            # Find target canvas element
            canvas_exists = page.evaluate("() => !!document.querySelector('canvas')")

            # Spawn FFmpeg image2pipe receiver
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-loglevel", "error",
                "-f", "image2pipe",
                "-framerate", str(fps),
                "-c:v", "mjpeg",
                "-i", "-",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                str(temp_video),
            ]
            ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

            for frame_idx in range(total_frames):
                t = frame_idx / fps
                page.evaluate(f"window.render ? window.render({t}) : null")

                if canvas_exists:
                    buf = page.locator("canvas").first.screenshot(type="jpeg", quality=90)
                else:
                    buf = page.screenshot(type="jpeg", quality=90)

                ffmpeg_proc.stdin.write(buf)

            ffmpeg_proc.stdin.close()
            ffmpeg_proc.wait(timeout=timeout_sec)
            browser.close()

    finally:
        server.shutdown()
        server.server_close()

    # Mux audio if provided
    if audio_path and os.path.exists(audio_path):
        logger.info("[PROCEDURAL] Muxing audio: %s", audio_path)
        mux_cmd = [
            "ffmpeg",
            "-y",
            "-loglevel", "error",
            "-i", str(temp_video),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-af", "loudnorm=I=-14:LRA=11:TP=-1.5",
            "-shortest",
            str(out_file),
        ]
        subprocess.run(mux_cmd, check=True)
        if temp_video.exists():
            temp_video.unlink()
    else:
        if temp_video.exists():
            shutil.move(str(temp_video), str(out_file))

    logger.info("[PROCEDURAL] Render complete -> %s", out_file)
    return {
        "success": True,
        "output_path": str(out_file),
        "duration": actual_dur,
        "frames": total_frames,
        "fps": fps,
        "resolution": f"{width}x{height}",
        "style": style_name,
    }
