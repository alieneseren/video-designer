"""
engine.py
=========
Main unified interface for 2D Stickman Video Production Engine.
Provides high-level APIs for:
1. Travel & Walking Vlog Monologue Engine ("İç Ses / Yürüyüş ve Gezi")
2. Aviation CVR & Investigation Dialogue Scenes
3. Defense & Tech Finance Infographic Battles
4. Custom Stickman Scene Composition
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from .character import StickmanCharacter, CharacterState
from .bubble import ComicBubble, ThoughtBubble, InfoBadge
from .animator import StickmanTimeline
from .overlay import StickmanOverlayCompositor


class StickmanEngine:
    """Unified Facade for Stickman Scene Generation."""

    def __init__(self, fps: int = 25, width: int = 1920, height: int = 1080):
        self.fps = fps
        self.w = width
        self.h = height
        self.compositor = StickmanOverlayCompositor(output_width=width, output_height=height, fps=fps)

    def render_travel_vlog_monologue(
        self,
        output_path: str,
        dialogue: str,
        character_pose: str = CharacterState.TRAVEL_WALKING,
        duration_sec: float = 5.0,
        badge_title: str = "İÇ SES // GÜNLÜK",
        location_title: str = "📍 KADIKÖY MODA SAHİLİ",
        location_stats: str = "👟 8.420 Adım // 5.2 km • ☀️ 22°C",
        bg_media: Optional[str] = None, # Path to background video or photo
        green_screen: bool = False,
        audio_path: Optional[str] = None,
        char_pos: Tuple[int, int] = (1450, 620),
        char_height: int = 430,
        bubble_type: str = "thought",
    ) -> Path:
        """
        Renders a travel vlog inner-monologue scene.
        Perfect for walking videos where the host doesn't talk to camera directly,
        but an expressive stickman avatar reenacts the inner thoughts ("iç ses").
        """
        char = StickmanCharacter(category="travel", character_id=character_pose)
        
        is_walking = ("walking" in character_pose.lower())
        loc_badge = (location_title, location_stats) if location_title else None
        
        bg_p = Path(bg_media) if bg_media else None
        audio_p = Path(audio_path) if audio_path else None
        
        out_p = Path(output_path)
        
        return self.compositor.render_overlay_video(
            output_path=out_p,
            duration_sec=duration_sec,
            character=char,
            dialogue=dialogue,
            badge_title=badge_title,
            char_pos=char_pos,
            char_height=char_height,
            bubble_type=bubble_type,
            location_badge=loc_badge,
            is_walking=is_walking,
            bg_media=bg_p,
            green_screen=green_screen,
            audio_path=audio_p,
        )

    def render_aviation_dialogue(
        self,
        output_path: str,
        captain_text: str,
        fo_text: str,
        flight_title: str = "FLIGHT CVR INVESTIGATION",
        duration_sec: float = 6.0,
        audio_path: Optional[str] = None,
    ) -> Path:
        """
        Wrapper connecting to high-fidelity aviation cockpit scene if needed.
        """
        from ..aviation_stickman_composite import generate_animated_cvr_video
        return generate_animated_cvr_video(
            flight_name=flight_title,
            captain_quote=captain_text,
            fo_quote=fo_text,
            duration_sec=duration_sec,
            output_path=output_path,
        )
