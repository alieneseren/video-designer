"""
Pydantic schemas for video operations, editing, and shorts.
"""
from typing import Optional
from pydantic import BaseModel


class CreateShortsFromFolderPayload(BaseModel):
    folder: str
    count: int = 4


class EditVideoPayload(BaseModel):
    folder: str
    transition: Optional[str] = None
    transition_dur: Optional[float] = None
    subtitle_preset: Optional[str] = None
    subtitle_animation: Optional[str] = None
    bgm_path: Optional[str] = None
    bgm_volume: Optional[float] = None
    watermark_text: Optional[str] = None
    censor_faces: Optional[bool] = None
    auto_editor: Optional[bool] = None
    enable_i2v: Optional[bool] = None
    i2v_model_quality: Optional[str] = None
    i2v_fps_multiplier: Optional[int] = None
