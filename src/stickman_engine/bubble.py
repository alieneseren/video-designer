"""
bubble.py
=========
Bouncing comic speech bubbles, cloud thought bubbles ("İç Ses"), and HUD info badges
for the Stickman Video Production Engine.
Aesthetic: Crayon Capital / MinutePhysics bold black strokes, crisp typography, bouncy spring pop-in.
"""

import math
from typing import Tuple, List, Optional
from PIL import Image, ImageDraw, ImageFont


def get_engine_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Robust cross-platform font resolution."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def wrap_text(text: str, max_chars: int = 32) -> List[str]:
    """Wraps dialogue text into cleanly sized lines."""
    words = (text or "").split()
    lines = []
    current = []
    for w in words:
        current.append(w)
        if len(" ".join(current)) >= max_chars:
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))
    return lines


class ComicBubble:
    """Sharp-tailed comic dialogue bubble with elastic spring entrance."""

    @staticmethod
    def draw(
        draw: ImageDraw.Draw,
        x: int,
        y: int,
        w: int,
        h: int,
        tail_target: Tuple[int, int],
        badge_text: str = "KONUŞMA",
        badge_color: Tuple[int, int, int] = (234, 88, 12),
        quote_text: str = "",
        scale: float = 1.0,
        max_chars: int = 30,
        highlight_keywords: Optional[List[str]] = None,
    ):
        if scale <= 0.05:
            return

        cx, cy = x + w // 2, y + h // 2
        sw, sh = int(w * scale), int(h * scale)
        sx, sy = cx - sw // 2, cy - sh // 2

        # 1. Soft Drop Shadow
        draw.rounded_rectangle(
            [(sx + 6, sy + 6), (sx + sw + 6, sy + sh + 6)],
            radius=18,
            fill=(0, 0, 0, 140)
        )

        # 2. Bubble Body
        draw.rounded_rectangle(
            [(sx, sy), (sx + sw, sy + sh)],
            radius=18,
            fill=(255, 255, 255),
            outline=(15, 23, 42),
            width=5
        )

        # 3. Pointer Tail towards speaker's mouth
        tx, ty = tail_target
        if tx < cx:
            # Tail points to the left
            draw.polygon([(sx + 35, sy + sh - 2), (sx + 70, sy + sh - 2), (sx + 15, sy + sh + 28)], fill=(255, 255, 255))
            draw.line([(sx + 35, sy + sh), (sx + 15, sy + sh + 28)], fill=(15, 23, 42), width=5)
            draw.line([(sx + 70, sy + sh), (sx + 15, sy + sh + 28)], fill=(15, 23, 42), width=5)
        else:
            # Tail points to the right
            draw.polygon([(sx + sw - 70, sy + sh - 2), (sx + sw - 35, sy + sh - 2), (sx + sw - 15, sy + sh + 28)], fill=(255, 255, 255))
            draw.line([(sx + sw - 70, sy + sh), (sx + sw - 15, sy + sh + 28)], fill=(15, 23, 42), width=5)
            draw.line([(sx + sw - 35, sy + sh), (sx + sw - 15, sy + sh + 28)], fill=(15, 23, 42), width=5)

        # 4. Text Contents (Render when pop scale is past 70%)
        if scale > 0.70:
            # Badge
            badge_w = min(sw - 36, int(len(badge_text) * 10) + 24)
            draw.rounded_rectangle([(sx + 18, sy + 16), (sx + 18 + badge_w, sy + 44)], radius=8, fill=badge_color)
            draw.text((sx + 26, sy + 21), badge_text, font=get_engine_font(13, bold=True), fill=(255, 255, 255))

            # Dialogue lines
            lines = wrap_text(quote_text, max_chars)
            default_keywords = ["DİKKAT", "UYARI", "KAYBOLDUM", "İNANILMAZ", "V1", "PULL UP", "STALL", "ALARM", "HARİKA", "YORULDUM"]
            active_keywords = highlight_keywords or default_keywords

            for idx, line in enumerate(lines[:4]):
                has_highlight = any(kw.lower() in line.lower() for kw in active_keywords)
                col = (225, 29, 72) if has_highlight else (15, 23, 42)
                draw.text((sx + 22, sy + 56 + idx * 28), line, font=get_engine_font(19, bold=True), fill=col)


class ThoughtBubble:
    """Puffy cloud thought bubble designed specifically for inner monologues ('İç Ses')."""

    @staticmethod
    def draw(
        draw: ImageDraw.Draw,
        x: int,
        y: int,
        w: int,
        h: int,
        head_target: Tuple[int, int],
        badge_text: str = "İÇ SES // MONOLOG",
        quote_text: str = "",
        scale: float = 1.0,
        max_chars: int = 30,
        cloud_tint: Tuple[int, int, int] = (248, 250, 252),
    ):
        if scale <= 0.05:
            return

        cx, cy = x + w // 2, y + h // 2
        sw, sh = int(w * scale), int(h * scale)
        sx, sy = cx - sw // 2, cy - sh // 2

        # 1. Cloud trail bubbles connecting to character's head
        tx, ty = head_target
        # Interpolate 3 trail bubbles
        trail_pts = [
            (sx + (sw // 4 if tx < cx else 3 * sw // 4), sy + sh + 15, 20),
            (sx + (sw // 4 if tx < cx else 3 * sw // 4) + (tx - cx) // 4, sy + sh + 38, 14),
            (tx + (cx - tx) // 3, ty - 25, 8),
        ]
        for bx, by, br in trail_pts:
            draw.ellipse([(bx - br + 4, by - br + 4), (bx + br + 4, by + br + 4)], fill=(0, 0, 0, 100))
            draw.ellipse([(bx - br, by - br), (bx + br, by + br)], fill=cloud_tint, outline=(15, 23, 42), width=4)

        # 2. Main Cloud Body Shadow
        draw.rounded_rectangle([(sx + 5, sy + 5), (sx + sw + 5, sy + sh + 5)], radius=28, fill=(0, 0, 0, 130))
        
        # 3. Main Cloud Scallops (Puffy cloud circles)
        # Background base rounded rect
        draw.rounded_rectangle([(sx, sy), (sx + sw, sy + sh)], radius=28, fill=cloud_tint, outline=(15, 23, 42), width=5)

        # 4. Content (Badge + Quote)
        if scale > 0.70:
            # Pill badge: "İç Ses" in purple / indigo
            badge_w = min(sw - 36, int(len(badge_text) * 10) + 24)
            draw.rounded_rectangle([(sx + 22, sy + 16), (sx + 22 + badge_w, sy + 44)], radius=12, fill=(99, 102, 241))
            draw.text((sx + 30, sy + 21), badge_text, font=get_engine_font(13, bold=True), fill=(255, 255, 255))

            # Dialogue lines with smooth stylish typography
            lines = wrap_text(quote_text, max_chars)
            for idx, line in enumerate(lines[:4]):
                draw.text((sx + 26, sy + 56 + idx * 28), line, font=get_engine_font(19, bold=True), fill=(30, 41, 59))


class InfoBadge:
    """Modern HUD capsule card for location, step counts, weather, and camera stats."""

    @staticmethod
    def draw(
        draw: ImageDraw.Draw,
        x: int,
        y: int,
        title: str = "📍 KADIKÖY MODA SAHİLİ",
        subtitle: str = "👟 12.450 Adım // 7.8 km • ☀️ 24°C",
        badge_w: int = 380,
        badge_h: int = 70,
        alpha_bg: Tuple[int, int, int, int] = (15, 23, 42, 220),
    ):
        # Translucent glass card with neon left border
        draw.rounded_rectangle([(x, y), (x + badge_w, y + badge_h)], radius=14, fill=alpha_bg, outline=(51, 65, 85), width=2)
        # Accent indicator line
        draw.rounded_rectangle([(x + 4, y + 8), (x + 8, y + badge_h - 8)], radius=2, fill=(249, 115, 22))
        
        # Title
        draw.text((x + 22, y + 12), title, font=get_engine_font(15, bold=True), fill=(255, 255, 255))
        # Subtitle
        draw.text((x + 22, y + 38), subtitle, font=get_engine_font(12, bold=False), fill=(148, 163, 184))
