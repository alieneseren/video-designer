from dataclasses import dataclass, field
from typing import List, Optional
import os
from pathlib import Path

DEFAULT_AVATAR = str(Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets" / "avatars" / "mom.jpg")
if not os.path.exists(DEFAULT_AVATAR):
    DEFAULT_AVATAR = str(Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets" / "avatars" / "male.png")

@dataclass
class Character:
    name: str
    role: str  # "contact" (incoming, left) or "user" (outgoing, right)
    voice: str = "tr-TR-AhmetNeural"
    pitch: str = "+0Hz"
    rate: str = "+0%"
    avatar: str = ""

@dataclass
class Message:
    id: str
    sender: str  # "contact" or "user"
    text: str
    timestamp: str = "14:15"
    typing_duration: float = 0.8  # seconds to show typing indicator
    audio_path: Optional[str] = None
    audio_duration: float = 0.0
    start_time: float = 0.0
    bubble_appear_time: float = 0.0
    sender_name: Optional[str] = None
    sender_avatar: Optional[str] = None
    sender_color: Optional[str] = None
    emotion: Optional[str] = "normal"  # normal, shock, happy
    emotion_avatar: Optional[str] = None

    @property
    def time(self) -> str:
        return self.timestamp

    @property
    def time_str(self) -> str:
        return self.timestamp


@dataclass
class Scenario:
    title: str
    contact_name: str
    contact_status: str = "çevrimiçi"
    contact_avatar: str = DEFAULT_AVATAR
    whatsapp_username: str = ""
    profile_avatar: str = ""
    watermark_username: str = "YazanYazana"
    tts_engine: str = "auto"
    layout: str = "dublaj_style"  # "dublaj_style" (@1dublaj viral benchmark montage), "compact_top", or "fullscreen"
    characters: dict = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    theme: str = "dark_amoled"  # "dark_amoled" | "classic_light" | "retro_bubble"
    wallpaper_path: Optional[str] = None
    bgm_enabled: bool = True
    bgm_track: Optional[str] = None
    bgm_volume: float = 0.12
    contact_avatar_gender: str = "female"
    user_gender: str = "male"
    is_group: bool = False
    group_participants: str = ""

    def to_dict(self):
        return {
            "title": self.title,
            "contact_name": self.contact_name,
            "contact_status": self.contact_status,
            "contact_avatar": self.contact_avatar,
            "whatsapp_username": self.whatsapp_username or self.contact_name,
            "profile_avatar": self.profile_avatar or self.contact_avatar,
            "watermark_username": self.watermark_username,
            "tts_engine": self.tts_engine,
            "theme": self.theme,
            "layout": self.layout,
            "wallpaper_path": self.wallpaper_path,
            "characters": {k: v.__dict__ if hasattr(v, "__dict__") else v for k, v in self.characters.items()},
            "messages": [m.__dict__ for m in self.messages],
            "bgm_enabled": self.bgm_enabled,
            "bgm_track": self.bgm_track,
            "bgm_volume": self.bgm_volume,
            "contact_avatar_gender": self.contact_avatar_gender,
            "user_gender": self.user_gender,
            "is_group": self.is_group,
            "group_participants": self.group_participants
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        messages = [
            Message(**m) for m in data.get("messages", [])
        ]
        characters = {}
        raw_characters = data.get("characters", {})
        if isinstance(raw_characters, list):
            normalized_characters = {}
            for index, value in enumerate(raw_characters):
                if isinstance(value, dict):
                    role = str(value.get("role") or value.get("sender") or
                               ("contact" if index == 0 else "user")).lower()
                    normalized_characters[role] = value
                else:
                    role = "contact" if index == 0 else "user"
                    normalized_characters[role] = value
            raw_characters = normalized_characters
        elif not isinstance(raw_characters, dict):
            raw_characters = {}

        for k, v in raw_characters.items():
            if isinstance(v, dict):
                character_data = dict(v)
                character_data.setdefault("name", k)
                character_data.setdefault("role", k)
                character_data.setdefault("voice", "tr-TR-AhmetNeural")
                character_data.setdefault("pitch", "+0Hz")
                character_data.setdefault("rate", "+0%")
                character_data.setdefault("avatar", "")
                characters[k] = Character(**character_data)
            else:
                characters[k] = Character(
                    name=str(v),
                    role=k,
                    voice="tr-TR-EmelNeural" if ("kad" in str(v).lower() or "emel" in str(v).lower())
                    else "tr-TR-AhmetNeural",
                )
        username = data.get("whatsapp_username", data.get("contact_name", "Kanka"))
        avatar = data.get("profile_avatar", data.get("contact_avatar", DEFAULT_AVATAR))
        return cls(
            title=data.get("title", "WhatsApp Sohbet"),
            contact_name=data.get("contact_name", username),
            contact_status=data.get("contact_status", "çevrimiçi"),
            contact_avatar=data.get("contact_avatar", avatar),
            whatsapp_username=username,
            profile_avatar=avatar,
            watermark_username=data.get("watermark_username", "YazanYazana"),
            tts_engine=data.get("tts_engine", "auto"),
            theme=data.get("theme") or "dark_amoled",
            layout=data.get("layout", "dublaj_style"),
            wallpaper_path=data.get("wallpaper_path"),
            characters=characters,
            messages=messages,
            bgm_enabled=data.get("bgm_enabled", True),
            bgm_track=data.get("bgm_track"),
            bgm_volume=data.get("bgm_volume", 0.12),
            contact_avatar_gender=data.get("contact_avatar_gender", "female"),
            user_gender=data.get("user_gender", "male"),
            is_group=bool(data.get("is_group", False)),
            group_participants=str(data.get("group_participants", ""))
        )
