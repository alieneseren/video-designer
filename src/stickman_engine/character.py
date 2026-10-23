"""
character.py
============
Character management for 2D Stickman Video Production Engine.
Supports:
- Cutout-based expressive sprites (Traveler, Aviation, Defense/Finance) with caching and transformations.
- Procedural vector stickman generation for on-the-fly custom poses and accessories.
"""

import os
import math
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageOps

CHARACTER_DIRS = [
    Path("assets/characters"),
    Path(__file__).resolve().parent.parent.parent / "assets" / "characters",
    Path(__file__).resolve().parent.parent / "assets" / "characters",
]

def find_character_asset(category: str, name: str) -> Optional[Path]:
    for base in CHARACTER_DIRS:
        target = base / category / f"{name}.png"
        if target.exists():
            return target
        # fallback to category folder without suffix
        for ext in [".png", ".jpg", ".jpeg"]:
            candidate = base / category / f"{name}{ext}"
            if candidate.exists():
                return candidate
    return None


class StickmanCharacter:
    """Manages sprite-based character textures, scaling, physics tilts, and bounce."""
    
    _cache: Dict[str, Image.Image] = {}

    def __init__(self, category: str = "travel", character_id: str = "traveler_walking"):
        self.category = category
        self.character_id = character_id
        self.texture = self._load_texture()

    def _load_texture(self) -> Image.Image:
        cache_key = f"{self.category}:{self.character_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        asset_path = find_character_asset(self.category, self.character_id)
        if asset_path and asset_path.exists():
            img = Image.open(asset_path).convert("RGBA")
            self._cache[cache_key] = img
            return img
        
        # Fallback: create procedural placeholder
        img = Image.new("RGBA", (240, 360), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([40, 20, 200, 180], fill=(255, 255, 255), outline=(15, 23, 42), width=6)
        draw.line([120, 180, 120, 280], fill=(15, 23, 42), width=8)
        draw.line([120, 220, 60, 260], fill=(15, 23, 42), width=6)
        draw.line([120, 220, 180, 260], fill=(15, 23, 42), width=6)
        draw.line([120, 280, 70, 350], fill=(15, 23, 42), width=6)
        draw.line([120, 280, 170, 350], fill=(15, 23, 42), width=6)
        self._cache[cache_key] = img
        return img

    def get_pose_image(
        self,
        target_height: int = 400,
        tilt_degrees: float = 0.0,
        flip_h: bool = False,
        squish_y: float = 1.0,
        squish_x: float = 1.0,
    ) -> Image.Image:
        """Returns transformed character image with high quality resampling."""
        orig_w, orig_h = self.texture.size
        aspect = orig_w / max(1, orig_h)
        new_h = int(target_height * squish_y)
        new_w = int(target_height * aspect * squish_x)
        if new_w <= 4 or new_h <= 4:
            return Image.new("RGBA", (10, 10), (0, 0, 0, 0))

        img = self.texture.resize((new_w, new_h), Image.Resampling.LANCZOS)

        if flip_h:
            img = ImageOps.mirror(img)

        if abs(tilt_degrees) > 0.1:
            img = img.rotate(-tilt_degrees, resample=Image.Resampling.BICUBIC, expand=True)

        return img


class CharacterState:
    """Predefined emotions & character mapping for travel and documentary channels."""
    
    # Travel Vlog Character States
    TRAVEL_WALKING = "traveler_walking"
    TRAVEL_PHOTOGRAPHER = "traveler_photographer"
    TRAVEL_EXHAUSTED = "traveler_exhausted"
    TRAVEL_LOST = "traveler_lost_map"
    TRAVEL_CONFUSED = "traveler_confused"
    TRAVEL_COFFEE = "traveler_coffee"
    TRAVEL_FOODIE = "traveler_foodie"
    TRAVEL_VLOGGER = "traveler_vlogger"
    
    # Aviation Black Box States
    PILOT_CALM = "captain_calm"
    PILOT_DISORIENTED = "captain_disoriented"
    FO_PANICKED = "first_officer_panicked"
    ATC_CONTROLLER = "atc_controller"
    NTSB_INVESTIGATOR = "ntsb_investigator"
    
    # Defense & Finance States
    DEFENSE_CEO = "defense_ceo"
    GENERAL_PANIC = "pentagon_general"
    TEST_PILOT = "test_pilot"
    WALL_STREET = "wall_street_trader"


class ProceduralStickman:
    """Procedural vector stickman generator for dynamic geometric drawing."""

    @staticmethod
    def draw_stickman(
        width: int = 300,
        height: int = 450,
        emotion: str = "happy",
        walk_phase: float = 0.0,
        is_talking: bool = False,
        accessory: Optional[str] = "backpack",
        shirt_color: Tuple[int, int, int] = (249, 115, 22), # Vibrant Orange
        shorts_color: Tuple[int, int, int] = (214, 180, 142), # Khaki
    ) -> Image.Image:
        """Renders a procedural Kurzgesagt/Crayon style stickman on a transparent RGBA canvas."""
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        cx = width // 2
        
        # Walk kinematics
        leg_swing = math.sin(walk_phase * math.pi * 2) * 28.0
        bob_y = abs(math.cos(walk_phase * math.pi * 2)) * 8.0
        
        torso_top_y = 150 + int(bob_y)
        torso_bot_y = 280 + int(bob_y)
        hip_y = torso_bot_y
        foot_ground_y = height - 25

        # 1. Backpack (drawn behind body if accessory == 'backpack')
        if accessory == "backpack":
            pack_w, pack_h = 75, 110
            pack_x = cx - 75
            pack_y = torso_top_y + 10
            draw.rounded_rectangle(
                [(pack_x, pack_y), (pack_x + pack_w, pack_y + pack_h)],
                radius=18,
                fill=(45, 115, 110),
                outline=(15, 23, 42),
                width=5
            )
            # Pocket flap
            draw.rounded_rectangle(
                [(pack_x + 5, pack_y + 35), (pack_x + 35, pack_y + 80)],
                radius=8,
                fill=(35, 95, 90),
                outline=(15, 23, 42),
                width=4
            )

        # 2. Legs & Shoes
        # Back leg
        l1_x = cx - 18 - int(leg_swing)
        draw.line([(cx - 15, hip_y), (l1_x, foot_ground_y - 12)], fill=(15, 23, 42), width=10)
        draw.line([(cx - 15, hip_y), (l1_x, foot_ground_y - 12)], fill=(255, 255, 255), width=4)
        # Back shoe
        draw.rounded_rectangle([(l1_x - 14, foot_ground_y - 14), (l1_x + 22, foot_ground_y + 4)], radius=8, fill=(234, 88, 12), outline=(15, 23, 42), width=4)

        # Front leg
        l2_x = cx + 18 + int(leg_swing)
        draw.line([(cx + 15, hip_y), (l2_x, foot_ground_y - 12)], fill=(15, 23, 42), width=10)
        draw.line([(cx + 15, hip_y), (l2_x, foot_ground_y - 12)], fill=(255, 255, 255), width=4)
        # Front shoe
        draw.rounded_rectangle([(l2_x - 14, foot_ground_y - 14), (l2_x + 24, foot_ground_y + 4)], radius=8, fill=(234, 88, 12), outline=(15, 23, 42), width=4)

        # Shorts / Pants
        draw.polygon([
            (cx - 38, hip_y - 10),
            (cx + 38, hip_y - 10),
            (cx + 42, hip_y + 35),
            (cx - 42, hip_y + 35)
        ], fill=shorts_color)
        draw.line([(cx - 38, hip_y - 10), (cx + 38, hip_y - 10)], fill=(15, 23, 42), width=5)
        draw.line([(cx - 42, hip_y + 35), (cx + 42, hip_y + 35)], fill=(15, 23, 42), width=5)
        draw.line([(cx - 38, hip_y - 10), (cx - 42, hip_y + 35)], fill=(15, 23, 42), width=5)
        draw.line([(cx + 38, hip_y - 10), (cx + 42, hip_y + 35)], fill=(15, 23, 42), width=5)

        # 3. Torso (Tubular cartoon body with shirt)
        torso_rect = [(cx - 42, torso_top_y), (cx + 42, torso_bot_y)]
        draw.rounded_rectangle(torso_rect, radius=24, fill=shirt_color, outline=(15, 23, 42), width=6)

        # Backpack straps over shoulders
        if accessory == "backpack":
            draw.line([(cx - 24, torso_top_y), (cx - 20, torso_bot_y - 20)], fill=(30, 85, 80), width=9)
            draw.line([(cx + 24, torso_top_y), (cx + 20, torso_bot_y - 20)], fill=(30, 85, 80), width=9)

        # 4. Head & Face
        head_radius = 58
        head_cx = cx
        head_cy = torso_top_y - head_radius + 15
        
        # Solid white head with bold outline
        head_box = [(head_cx - head_radius, head_cy - head_radius), (head_cx + head_radius, head_cy + head_radius)]
        draw.ellipse(head_box, fill=(255, 255, 255), outline=(15, 23, 42), width=6)

        # Hair (stylish comic black hair tuft)
        draw.polygon([
            (head_cx - 50, head_cy - 20),
            (head_cx - 40, head_cy - 52),
            (head_cx - 15, head_cy - 65),
            (head_cx + 25, head_cy - 64),
            (head_cx + 52, head_cy - 35),
            (head_cx + 48, head_cy - 20),
            (head_cx + 30, head_cy - 38),
            (head_cx - 10, head_cy - 48),
            (head_cx - 35, head_cy - 35)
        ], fill=(15, 23, 42))

        # Eyes & Emotion
        eye_y = head_cy - 2
        if emotion in ["happy", "vlogging"]:
            # Cute dot eyes
            draw.ellipse([(head_cx - 22, eye_y - 6), (head_cx - 10, eye_y + 6)], fill=(15, 23, 42))
            draw.ellipse([(head_cx + 10, eye_y - 6), (head_cx + 22, eye_y + 6)], fill=(15, 23, 42))
            # Rosy cheeks
            draw.ellipse([(head_cx - 38, eye_y + 12), (head_cx - 24, eye_y + 22)], fill=(253, 164, 175, 180))
            draw.ellipse([(head_cx + 24, eye_y + 12), (head_cx + 38, eye_y + 22)], fill=(253, 164, 175, 180))
        elif emotion in ["shocked", "panicked"]:
            # Wide white shocked eyes with tiny pupils
            draw.ellipse([(head_cx - 28, eye_y - 14), (head_cx - 6, eye_y + 10)], fill=(255, 255, 255), outline=(15, 23, 42), width=3)
            draw.ellipse([(head_cx + 6, eye_y - 14), (head_cx + 28, eye_y + 10)], fill=(255, 255, 255), outline=(15, 23, 42), width=3)
            draw.ellipse([(head_cx - 19, eye_y - 4), (head_cx - 15, eye_y + 2)], fill=(15, 23, 42))
            draw.ellipse([(head_cx + 15, eye_y - 4), (head_cx + 19, eye_y + 2)], fill=(15, 23, 42))
            # Sweat drop
            draw.polygon([(head_cx + 34, head_cy - 22), (head_cx + 42, head_cy - 35), (head_cx + 38, head_cy - 14)], fill=(56, 189, 248))
        elif emotion in ["exhausted", "tired"]:
            # Slanted closed tired eyes
            draw.line([(head_cx - 26, eye_y - 3), (head_cx - 10, eye_y + 4)], fill=(15, 23, 42), width=4)
            draw.line([(head_cx + 10, eye_y + 4), (head_cx + 26, eye_y - 3)], fill=(15, 23, 42), width=4)
            # Dropping sweat
            draw.ellipse([(head_cx + 36, head_cy - 12), (head_cx + 44, head_cy + 2)], fill=(56, 189, 248))

        # Mouth
        mouth_y = head_cy + 24
        if is_talking:
            # Open talking mouth
            draw.rounded_rectangle([(head_cx - 14, mouth_y - 4), (head_cx + 14, mouth_y + 14)], radius=8, fill=(15, 23, 42))
            draw.arc([(head_cx - 10, mouth_y + 2), (head_cx + 10, mouth_y + 12)], 0, 180, fill=(244, 63, 94), width=4)
        elif emotion in ["happy", "vlogging"]:
            # Big smile
            draw.arc([(head_cx - 18, mouth_y - 10), (head_cx + 18, mouth_y + 12)], 10, 170, fill=(15, 23, 42), width=4)
        elif emotion in ["shocked", "panicked"]:
            # Open oval scream
            draw.ellipse([(head_cx - 12, mouth_y - 4), (head_cx + 12, mouth_y + 20)], fill=(15, 23, 42))
        elif emotion in ["exhausted", "tired"]:
            # Panting tongue
            draw.arc([(head_cx - 16, mouth_y - 4), (head_cx + 16, mouth_y + 12)], 10, 170, fill=(15, 23, 42), width=4)
            draw.rounded_rectangle([(head_cx - 8, mouth_y + 4), (head_cx + 8, mouth_y + 16)], radius=4, fill=(244, 114, 182))
        else:
            # Neutral line
            draw.line([(head_cx - 12, mouth_y + 6), (head_cx + 12, mouth_y + 6)], fill=(15, 23, 42), width=4)

        # 5. Arms & Hands
        arm_swing = math.sin(walk_phase * math.pi * 2) * 22.0
        # Left arm
        draw.line([(cx - 36, torso_top_y + 25), (cx - 55 - int(arm_swing), torso_bot_y - 10)], fill=(15, 23, 42), width=10)
        draw.line([(cx - 36, torso_top_y + 25), (cx - 55 - int(arm_swing), torso_bot_y - 10)], fill=(255, 255, 255), width=5)
        draw.ellipse([(cx - 65 - int(arm_swing), torso_bot_y - 18), (cx - 45 - int(arm_swing), torso_bot_y + 2)], fill=(255, 255, 255), outline=(15, 23, 42), width=4)

        # Right arm
        if accessory == "camera":
            # Holding camera to face
            draw.line([(cx + 36, torso_top_y + 25), (head_cx + 20, head_cy + 15)], fill=(15, 23, 42), width=10)
            draw.line([(cx + 36, torso_top_y + 25), (head_cx + 20, head_cy + 15)], fill=(255, 255, 255), width=5)
            # Camera box
            cam_x, cam_y = head_cx + 8, head_cy - 4
            draw.rounded_rectangle([(cam_x, cam_y), (cam_x + 55, cam_y + 38)], radius=6, fill=(51, 65, 85), outline=(15, 23, 42), width=4)
            draw.ellipse([(cam_x + 18, cam_y + 6), (cam_x + 42, cam_y + 30)], fill=(14, 165, 233), outline=(15, 23, 42), width=3)
        else:
            draw.line([(cx + 36, torso_top_y + 25), (cx + 55 + int(arm_swing), torso_bot_y - 10)], fill=(15, 23, 42), width=10)
            draw.line([(cx + 36, torso_top_y + 25), (cx + 55 + int(arm_swing), torso_bot_y - 10)], fill=(255, 255, 255), width=5)
            draw.ellipse([(cx + 45 + int(arm_swing), torso_bot_y - 18), (cx + 65 + int(arm_swing), torso_bot_y + 2)], fill=(255, 255, 255), outline=(15, 23, 42), width=4)

        return canvas
