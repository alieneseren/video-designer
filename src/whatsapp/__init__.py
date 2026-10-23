"""
WhatsApp Shorts Video Generator Module
=======================================
Autonomous simulated WhatsApp conversation video generation pipeline.
Includes:
- Playwright Chromium 1080x1920 9:16 layout recorder
- Dual-character neural TTS with pitch/rate/EQ modulation
- Pop/Swoosh SFX and ducked BGM
- Full AI script generator (Claude, Gemini, Ollama, LM Studio)
"""

from .models import Character, Message, Scenario
from .generator import generate_whatsapp_video

__all__ = ["Character", "Message", "Scenario", "generate_whatsapp_video"]
