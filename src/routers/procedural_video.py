"""
procedural_video.py
===================
FastAPI router for pure code-based procedural film styles and rendering.
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

try:
    from src.procedural_film_renderer import (
        list_procedural_styles,
        render_procedural_film,
        OUTPUT_DIR,
    )
except ImportError:
    from procedural_film_renderer import (
        list_procedural_styles,
        render_procedural_film,
        OUTPUT_DIR,
    )

router = APIRouter(prefix="/api/procedural-styles", tags=["Procedural Styles"])


class RenderProceduralRequest(BaseModel):
    style_name: str
    duration_sec: Optional[float] = 10.0
    fps: Optional[int] = 30
    width: Optional[int] = 1920
    height: Optional[int] = 1080
    audio_path: Optional[str] = None
    output_filename: Optional[str] = None


@router.get("")
def get_styles():
    """List all available sanitized procedural styles."""
    styles = list_procedural_styles()
    return {
        "count": len(styles),
        "styles": styles,
    }


@router.post("/render")
def trigger_render(req: RenderProceduralRequest, background_tasks: BackgroundTasks):
    """Triggers an async procedural film render job."""
    out_name = req.output_filename or f"procedural_{req.style_name}_{int(os.times()[4])}.mp4"
    out_path = OUTPUT_DIR / out_name

    def run_job():
        render_procedural_film(
            style_name=req.style_name,
            output_path=out_path,
            duration_sec=req.duration_sec,
            fps=req.fps or 30,
            width=req.width or 1920,
            height=req.height or 1080,
            audio_path=req.audio_path,
        )

    background_tasks.add_task(run_job)
    return {
        "status": "queued",
        "style": req.style_name,
        "target_file": str(out_path),
        "target_url": f"/output/{out_name}",
    }
