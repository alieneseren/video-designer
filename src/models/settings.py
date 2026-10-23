"""
Pydantic schemas for system settings.
"""
from typing import Optional
from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    nasa_api_key: Optional[str] = None
    instagram_access_token: Optional[str] = None
    instagram_user_id: Optional[str] = None
    instagram_public_base_url: Optional[str] = None
    instagram_graph_api_version: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    lmstudio_url: Optional[str] = None
    lmstudio_model: Optional[str] = None
    output_dir: Optional[str] = None
    tts_engine: Optional[str] = None
    chatterbox_voice: Optional[str] = None
    remote_tts_engine: Optional[str] = None
    kokoro_voice: Optional[str] = None
    kokoro_speed: Optional[str] = None
    # Video edit (v3)
    subtitle_preset: Optional[str] = None
    subtitle_animation: Optional[str] = None
    bgm_path: Optional[str] = None
    bgm_volume: Optional[str] = None
    watermark_path: Optional[str] = None
    watermark_text: Optional[str] = None
    watermark_position: Optional[str] = None
    active_voice_clone_id: Optional[str] = None
    rvc_pth_path: Optional[str] = None
    rvc_index_path: Optional[str] = None
    rvc_pitch: Optional[int] = 0
