#!/usr/bin/env python3
"""
channel_narrator_factory.py
===========================
Bespoke Narrator & Avatar Provisioning Engine for Stickman Channels.
Automatically designs, rigs, and generates customized 2D stickman presenters
and YouTube channel avatars tailored to any channel niche or topic category.

Supported Niches:
- Crayon Combat / Military Tech Satire (@tacticallcrayon)
- Blackbox / Aviation Investigation
- Crayon Capital / Tech & Finance Deep Dives
- Science / Space / Physics
- Cyber / AI / Tech Breakdowns
- True Crime / Historical Investigations
- General Boş Kafa / Sketch Comedy / Video Essays
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if not (BASE_DIR / "assets").exists():
    BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
CHARACTERS_DIR = ASSETS_DIR / "characters"
BOSKAFA_DIR = ASSETS_DIR / "boskafa"

NICHE_ARCHETYPES = {
    "crayon_combat": {
        "role_name": "Tactical Scribe",
        "description": "Charismatic military contractor / tactical skeptic with olive operator cap and giant wax crayon.",
        "cap_color": (59, 78, 52),       # Tactical Olive Drab
        "cap_type": "tactical_operator",
        "badge_color": (234, 179, 8),     # Hazard Gold
        "bg_style": "blueprint_parchment",
        "prop": "tactical_crayon",
        "avatar_title": "TACTICAL CRAYON"
    },
    "aviation": {
        "role_name": "Flight Captain",
        "description": "Veteran commercial & test pilot with captain's cap, gold braids, and aviator headset.",
        "cap_color": (15, 23, 42),       # Navy Officer Blue
        "cap_type": "pilot_captain",
        "badge_color": (56, 189, 248),    # Horizon Cyan
        "bg_style": "cockpit_hud",
        "prop": "flight_kneeboard",
        "avatar_title": "BLACKBOX INVESTIGATOR"
    },
    "tech_finance_essay": {
        "role_name": "Wall Street Analyst",
        "description": "Sharp financial essayist with round reading glasses, slicked hair, and ledger pointer.",
        "cap_color": (30, 41, 59),
        "cap_type": "glasses_analyst",
        "badge_color": (34, 197, 94),     # Cash Green
        "bg_style": "emerald_ledger",
        "prop": "candlestick_pointer",
        "avatar_title": "CRAYON CAPITAL"
    },
    "science": {
        "role_name": "Lab Researcher",
        "description": "Curious scientist with blue safety goggles, white lab coat, and glowing test tube.",
        "cap_color": (14, 116, 144),
        "cap_type": "scientist_goggles",
        "badge_color": (168, 85, 247),    # Quantum Purple
        "bg_style": "quantum_grid",
        "prop": "glowing_flask",
        "avatar_title": "ATOMIC LOGIC"
    },
    "tech": {
        "role_name": "Cyber Hacker",
        "description": "Tech architect with black hoodie, neon terminal visor, and mechanical keys.",
        "cap_color": (2, 6, 23),
        "cap_type": "hoodie_hacker",
        "badge_color": (59, 130, 246),    # Electric Blue
        "bg_style": "cyber_matrix",
        "prop": "cyber_tablet",
        "avatar_title": "TECH DISSECTED"
    },
    "absurd_science": {
        "role_name": "Theoretical Physicist / Mad Scientist",
        "description": "Wild-haired curious scientist stickman with safety goggles, lab coat, chalkboard pointer, and quantum thought bubbles.",
        "cap_color": (30, 58, 138),       # Quantum Navy
        "cap_type": "scientist_goggles",
        "badge_color": (168, 85, 247),    # Purple Neon / Quantum Glow
        "bg_style": "quantum_grid",
        "prop": "chalkboard_pointer",
        "avatar_title": "WHAT IF LAB"
    },
    "general": {
        "role_name": "Sketch Presenter",
        "description": "Iconic Boş Kafa style stickman with clean black ink lines and expressive baseball cap.",
        "cap_color": (30, 58, 138),      # Classic Navy
        "cap_type": "baseball_cap",
        "badge_color": (250, 204, 21),    # Pop Yellow
        "bg_style": "sketch_notebook",
        "prop": "sketch_pen",
        "avatar_title": "BOŞ KAFA PRESENTER"
    }
}


def get_niche_config(topic_category: str) -> dict:
    c = (topic_category or "").lower().strip()
    if c in ("crayon_combat", "military", "military_tech", "tacticallcrayon", "askeri"):
        return NICHE_ARCHETYPES["crayon_combat"]
    if c in ("aviation", "blackbox", "havacilik", "flight"):
        return NICHE_ARCHETYPES["aviation"]
    if c in ("tech_finance_essay", "crayon_capital", "finans", "finance", "ekonomi"):
        return NICHE_ARCHETYPES["tech_finance_essay"]
    if c in ("science", "space", "physics", "uzay", "cosmos"):
        return NICHE_ARCHETYPES["science"]
    if c in ("tech", "coding", "ai", "cyber", "yazilim"):
        return NICHE_ARCHETYPES["tech"]
    if c in ("absurd_science", "what_if", "whatif", "simulasyon", "simulation", "eger_olsaydi", "absurd_engineering", "fizik"):
        return NICHE_ARCHETYPES["absurd_science"]
    return NICHE_ARCHETYPES["general"]


class ChannelNarratorFactory:
    """Manages creation, customization, and deployment of channel-specific stickman rigs and avatars."""

    @staticmethod
    def get_channel_character_dir(channel_id: str) -> Path:
        char_dir = CHARACTERS_DIR / channel_id
        char_dir.mkdir(parents=True, exist_ok=True)
        return char_dir

    @classmethod
    def ensure_channel_narrator(
        cls,
        channel_id: str,
        topic_category: str = "crayon_combat",
        channel_name: str = "",
        custom_avatar_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Guarantees that a channel has its own dedicated sprite rig and YouTube avatar.
        If not yet generated, provisions them based on the channel's niche archetype.
        """
        char_dir = cls.get_channel_character_dir(channel_id)
        niche = get_niche_config(topic_category)
        display_name = channel_name or channel_id.replace("_", " ").title()

        avatar_path = char_dir / "channel_avatar.png"
        meta_path = char_dir / "narrator_profile.json"

        # 1. Provision Sprite Rig if missing
        required_sprites = [
            "pointing_open.png", "pointing_closed.png", "pointing_blink_open.png", "pointing_blink_closed.png",
            "walking_open.png", "walking_blink.png",
            "shocked_open.png", "shocked_blink.png",
            "smug_open.png", "smug_blink.png"
        ]

        missing_sprites = [s for s in required_sprites if not (char_dir / s).exists()]
        if missing_sprites:
            # Seed from clean Boş Kafa base sprites
            if BOSKAFA_DIR.exists():
                for s in required_sprites:
                    src = BOSKAFA_DIR / s
                    if src.exists():
                        shutil.copy2(src, char_dir / s)
            print(f"[NARRATOR-FACTORY] ✨ Seeded {len(required_sprites)} discrete stickman sprites for channel '{channel_id}'")

        # 2. Generate or link Channel Avatar
        if custom_avatar_path and custom_avatar_path.exists():
            shutil.copy2(custom_avatar_path, avatar_path)
            print(f"[NARRATOR-FACTORY] 🎨 Applied custom avatar for channel '{channel_id}' from {custom_avatar_path.name}")
        elif not avatar_path.exists():
            cls._generate_fallback_channel_avatar(avatar_path, display_name, niche, char_dir)

        # 3. Save narrator metadata
        profile = {
            "channel_id": channel_id,
            "channel_name": display_name,
            "topic_category": topic_category,
            "role_name": niche["role_name"],
            "description": niche["description"],
            "cap_color_rgb": list(niche["cap_color"]),
            "badge_color_rgb": list(niche["badge_color"]),
            "prop": niche["prop"],
            "avatar_path": str(avatar_path),
            "sprite_dir": str(char_dir)
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        return profile

    @classmethod
    def _generate_fallback_channel_avatar(
        cls,
        output_path: Path,
        channel_name: str,
        niche: dict,
        char_dir: Path
    ):
        """Generates a high-contrast, broadcast-ready 1024x1024 YouTube channel avatar."""
        size = 1024
        img = Image.new("RGBA", (size, size), (248, 246, 239, 255))
        draw = ImageDraw.Draw(img)

        # 1. Circular badge outline
        cx, cy, r = size // 2, size // 2, 470
        badge_col = niche["badge_color"]
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(255, 255, 255), outline=badge_col, width=18)

        # Outer dashed tech ring
        import math
        for i in range(36):
            ang = (i / 36.0) * 2 * math.pi
            px = cx + int((r + 14) * math.cos(ang))
            py = cy + int((r + 14) * math.sin(ang))
            if i % 2 == 0:
                draw.ellipse([(px - 4, py - 4), (px + 4, py + 4)], fill=badge_col)

        # 2. Sketch notebook background lines inside circle
        for y in range(cy - r + 80, cy + r - 80, 52):
            # calculate chord
            dy = abs(y - cy)
            if dy < r - 20:
                dx = int(math.sqrt((r - 20)**2 - dy**2))
                draw.line([(cx - dx, y), (cx + dx, y)], fill=(232, 228, 218), width=2)

        # 3. Paste stickman presenter bust
        sprite_source = char_dir / "pointing_open.png"
        if not sprite_source.exists():
            sprite_source = BOSKAFA_DIR / "pointing_open.png"

        if sprite_source.exists():
            sp = Image.open(sprite_source).convert("RGBA")
            # Scale up bust to fill avatar
            target_h = 780
            sc = target_h / float(sp.height)
            target_w = int(sp.width * sc)
            sp_scaled = sp.resize((target_w, target_h), Image.Resampling.LANCZOS)
            img.alpha_composite(sp_scaled, (cx - target_w // 2, cy - target_h // 2 + 100))

        # 4. Top/Bottom Curved or Banner Label
        # Bottom ribbon
        bw, bh = 820, 110
        bx, by = cx - bw // 2, cy + r - 150
        draw.rounded_rectangle([(bx + 8, by + 10), (bx + bw + 8, by + bh + 10)], radius=18, fill=(0, 0, 0, 120))
        draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=18, fill=(15, 23, 42, 245), outline=badge_col, width=4)

        # Font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Impact.ttf", 52)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), channel_name.upper(), font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw // 2, by + (bh - th) // 2 - 4), channel_name.upper(), font=font, fill=(255, 255, 255))

        img.save(output_path, "PNG")
        print(f"[NARRATOR-FACTORY] 📸 Generated avatar: {output_path} (1024x1024)")


if __name__ == "__main__":
    test_profile = ChannelNarratorFactory.ensure_channel_narrator("tacticallcrayon", "crayon_combat", "Tactical Crayon")
    print(f"Profile: {test_profile}")
