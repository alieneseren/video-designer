"""
crayon_mesh_renderer.py
=======================
Authentic Tactical Crayon Hand-Drawn Puppet & Boiling Line Shader.
Translates projected 2D skeletal joints into raw wax-crayon stickman art
with 12 FPS boiling line turbulence, expressive googly eyes, and archetype props.
"""

import math
import random
from typing import Tuple, List, Optional, Dict
import numpy as np
from PIL import Image, ImageDraw

from .satire_motion_catalog import (
    SMPL_22_JOINTS,
    SKELETAL_BONES
)


class CrayonMeshRenderer:
    """
    Renders expressive, hand-drawn crayon stickmen from 2D joint coordinates.
    Emulates classic 12 FPS boiling lines (line boil effect) on 30 FPS video.
    """

    def __init__(self, stroke_color: Tuple[int, int, int] = (25, 25, 25)):
        self.stroke_color = stroke_color

    def render_puppet(
        self,
        draw: ImageDraw.ImageDraw,
        joints_2d: np.ndarray,  # (22, 2)
        frame_idx: int,
        archetype: str = "general",
        emotion: str = "neutral",
        look_target: Optional[Tuple[float, float]] = None,
        scale: float = 1.0
    ):
        """
        Draws the complete articulated crayon stickman onto a PIL ImageDraw context.
        """
        # 12 FPS Boiling Line Seed: changes every 2 frames
        boil_step = frame_idx // 2
        rng = random.Random(boil_step * 7919)

        def jitter(val: float, amp: float = 3.5) -> float:
            return val + rng.uniform(-amp, amp)

        def get_joint(name: str) -> Tuple[float, float]:
            idx = SMPL_22_JOINTS[name]
            return (joints_2d[idx, 0], joints_2d[idx, 1])

        # Extract primary landmarks
        head_xy = get_joint("head")
        neck_xy = get_joint("neck")
        spine3_xy = get_joint("spine3")
        spine2_xy = get_joint("spine2")
        pelvis_xy = get_joint("pelvis")

        l_shoulder = get_joint("left_shoulder")
        l_elbow = get_joint("left_elbow")
        l_wrist = get_joint("left_wrist")

        r_shoulder = get_joint("right_shoulder")
        r_elbow = get_joint("right_elbow")
        r_wrist = get_joint("right_wrist")

        l_hip = get_joint("left_hip")
        l_knee = get_joint("left_knee")
        l_ankle = get_joint("left_ankle")
        l_foot = get_joint("left_foot")

        r_hip = get_joint("right_hip")
        r_knee = get_joint("right_knee")
        r_ankle = get_joint("right_ankle")
        r_foot = get_joint("right_foot")

        # ── 1. DRAW LEGS & FEET ──
        leg_width = max(6, int(9 * scale))
        self._draw_crayon_limb(draw, l_hip, l_knee, leg_width, rng)
        self._draw_crayon_limb(draw, l_knee, l_ankle, leg_width, rng)
        self._draw_crayon_foot(draw, l_ankle, l_foot, rng)

        self._draw_crayon_limb(draw, r_hip, r_knee, leg_width, rng)
        self._draw_crayon_limb(draw, r_knee, r_ankle, leg_width, rng)
        self._draw_crayon_foot(draw, r_ankle, r_foot, rng)

        # ── 2. DRAW TORSO / BODY ──
        torso_width = max(10, int(16 * scale))
        self._draw_crayon_limb(draw, pelvis_xy, spine2_xy, torso_width, rng)
        self._draw_crayon_limb(draw, spine2_xy, spine3_xy, torso_width, rng)
        self._draw_crayon_limb(draw, spine3_xy, neck_xy, max(8, int(12 * scale)), rng)

        # ── 3. DRAW ARMS & HANDS ──
        arm_width = max(6, int(8 * scale))
        self._draw_crayon_limb(draw, l_shoulder, l_elbow, arm_width, rng)
        self._draw_crayon_limb(draw, l_elbow, l_wrist, arm_width, rng)
        self._draw_crayon_hand(draw, l_wrist, rng)

        self._draw_crayon_limb(draw, r_shoulder, r_elbow, arm_width, rng)
        self._draw_crayon_limb(draw, r_elbow, r_wrist, arm_width, rng)
        self._draw_crayon_hand(draw, r_wrist, rng)

        # ── 4. DRAW HEAD & EXPRESSIVE FACE ──
        head_radius = int(48 * scale)
        self._draw_crayon_head(
            draw,
            head_xy,
            head_radius,
            frame_idx,
            emotion=emotion,
            look_target=look_target,
            rng=rng
        )

        # ── 5. DRAW ARCHETYPE ACCESSORIES ──
        self._draw_archetype_props(
            draw,
            head_xy,
            neck_xy,
            spine3_xy,
            l_wrist,
            r_wrist,
            head_radius,
            archetype=archetype,
            scale=scale,
            rng=rng
        )

    def _draw_crayon_limb(
        self,
        draw: ImageDraw.ImageDraw,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        width: int,
        rng: random.Random
    ):
        """Draws a rough, multi-pass crayon line with boiling edge jitter."""
        x1, y1 = p1
        x2, y2 = p2

        # 3 textured passes for wax density
        for pass_idx in range(3):
            j1 = (x1 + rng.uniform(-2.5, 2.5), y1 + rng.uniform(-2.5, 2.5))
            j2 = (x2 + rng.uniform(-2.5, 2.5), y2 + rng.uniform(-2.5, 2.5))
            w = max(2, width + rng.randint(-1, 1))
            draw.line([j1, j2], fill=self.stroke_color, width=w)

    def _draw_crayon_foot(
        self,
        draw: ImageDraw.ImageDraw,
        ankle: Tuple[float, float],
        toe: Tuple[float, float],
        rng: random.Random
    ):
        """Draws simple, bold crayon shoes."""
        ax, ay = ankle
        tx, ty = toe
        draw.line(
            [(ax + rng.uniform(-2, 2), ay + rng.uniform(-2, 2)),
             (tx + rng.uniform(-2, 2), ty + rng.uniform(-2, 2))],
            fill=(40, 40, 40),
            width=9
        )

    def _draw_crayon_hand(
        self,
        draw: ImageDraw.ImageDraw,
        wrist: Tuple[float, float],
        rng: random.Random
    ):
        """Draws a compact circular hand with crayon texture."""
        wx, wy = wrist
        r = 11 + rng.randint(-1, 1)
        draw.ellipse(
            [wx - r, wy - r, wx + r, wy + r],
            fill=self.stroke_color,
            outline=self.stroke_color
        )

    def _draw_crayon_head(
        self,
        draw: ImageDraw.ImageDraw,
        center: Tuple[float, float],
        radius: int,
        frame_idx: int,
        emotion: str,
        look_target: Optional[Tuple[float, float]],
        rng: random.Random
    ):
        """Renders hand-drawn head circle with autonomous googly eyes."""
        cx, cy = center
        # Head paper fill
        bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
        draw.ellipse(bbox, fill=(248, 246, 240), outline=None)

        # Multi-pass crayon perimeter
        for _ in range(3):
            j_rad = radius + rng.uniform(-2.0, 2.0)
            j_box = [cx - j_rad + rng.uniform(-1.5, 1.5),
                     cy - j_rad + rng.uniform(-1.5, 1.5),
                     cx + j_rad + rng.uniform(-1.5, 1.5),
                     cy + j_rad + rng.uniform(-1.5, 1.5)]
            draw.ellipse(j_box, outline=self.stroke_color, width=4)

        # Autonomous Googly Eyes
        eye_y = cy - int(radius * 0.15)
        eye_spacing = int(radius * 0.38)
        left_eye_center = (cx - eye_spacing, eye_y)
        right_eye_center = (cx + eye_spacing, eye_y)

        # Natural blink cycle: blinks every 105 frames for 3 frames
        is_blinking = (frame_idx % 105) < 3

        if is_blinking:
            # Draw shut eyelid dashes
            draw.line([left_eye_center[0] - 10, eye_y, left_eye_center[0] + 10, eye_y], fill=self.stroke_color, width=3)
            draw.line([right_eye_center[0] - 10, eye_y, right_eye_center[0] + 10, eye_y], fill=self.stroke_color, width=3)
        else:
            eye_radius = int(radius * 0.28)
            if emotion == "panic":
                eye_radius = int(radius * 0.38)  # Wide panic eyes
            elif emotion == "smug":
                eye_radius = int(radius * 0.22)  # Squinty eyes

            # White eyeballs
            for ex, ey in [left_eye_center, right_eye_center]:
                draw.ellipse([ex - eye_radius, ey - eye_radius, ex + eye_radius, ey + eye_radius], fill=(255, 255, 255), outline=self.stroke_color, width=3)

                # Pupil calculation (looks toward look_target or forward)
                pupil_r = max(3, int(eye_radius * 0.45))
                px, py = ex, ey
                if look_target:
                    dx = look_target[0] - ex
                    dy = look_target[1] - ey
                    dist = math.hypot(dx, dy)
                    if dist > 1.0:
                        max_offset = eye_radius - pupil_r - 2
                        px += (dx / dist) * min(max_offset, dist * 0.05)
                        py += (dy / dist) * min(max_offset, dist * 0.05)
                elif emotion == "panic":
                    px += rng.uniform(-4, 4)
                    py += rng.uniform(-4, 4)

                draw.ellipse([px - pupil_r, py - pupil_r, px + pupil_r, py + pupil_r], fill=(20, 20, 20))

        # Mouth Expression
        mouth_y = cy + int(radius * 0.42)
        if emotion == "angry":
            # Serrated zigzag mouth
            draw.line([cx - 18, mouth_y, cx - 9, mouth_y - 6, cx, mouth_y + 4, cx + 9, mouth_y - 6, cx + 18, mouth_y], fill=self.stroke_color, width=4)
        elif emotion == "smug":
            # Asymmetrical wry grin
            draw.arc([cx - 16, mouth_y - 8, cx + 18, mouth_y + 12], start=10, end=170, fill=self.stroke_color, width=4)
        elif emotion == "panic":
            # Agonized open 'O'
            draw.ellipse([cx - 12, mouth_y - 12, cx + 12, mouth_y + 16], fill=(40, 20, 20), outline=self.stroke_color, width=3)
        else:
            # Neutral gentle curve
            draw.arc([cx - 14, mouth_y - 6, cx + 14, mouth_y + 10], start=20, end=160, fill=self.stroke_color, width=3)

    def _draw_archetype_props(
        self,
        draw: ImageDraw.ImageDraw,
        head_xy: Tuple[float, float],
        neck_xy: Tuple[float, float],
        spine3_xy: Tuple[float, float],
        l_wrist: Tuple[float, float],
        r_wrist: Tuple[float, float],
        head_radius: int,
        archetype: str,
        scale: float,
        rng: random.Random
    ):
        """Draws iconic satirical props (General cap, necktie, medals, coffee mug)."""
        hx, hy = head_xy

        if archetype == "general":
            # Military General Peaked Visor Cap
            cap_y = hy - head_radius + 4
            cap_w = int(head_radius * 1.5)
            cap_h = int(head_radius * 0.55)
            cap_pts = [
                (hx - cap_w // 2, cap_y + 8),
                (hx - cap_w // 3, cap_y - cap_h),
                (hx + cap_w // 3, cap_y - cap_h),
                (hx + cap_w // 2, cap_y + 8),
                (hx + cap_w // 2 + 10, cap_y + 16),  # Visor peak
                (hx - cap_w // 2 - 10, cap_y + 16)
            ]
            draw.polygon(cap_pts, fill=(58, 77, 57), outline=self.stroke_color)
            # Gold braid ribbon
            draw.line([cap_pts[0], cap_pts[3]], fill=(218, 165, 32), width=4)

            # Chest Medals
            mx = spine3_xy[0] - 12
            my = spine3_xy[1]
            draw.rectangle([mx, my, mx + 8, my + 14], fill=(220, 38, 38), outline=self.stroke_color)
            draw.rectangle([mx + 10, my, mx + 18, my + 14], fill=(37, 99, 235), outline=self.stroke_color)

        elif archetype in ("defense_ceo", "lobbyist"):
            # Corporate Necktie
            tx, ty = neck_xy
            draw.polygon(
                [(tx - 6, ty), (tx + 6, ty), (tx + 12, ty + 50), (tx, ty + 68), (tx - 12, ty + 50)],
                fill=(220, 38, 38),  # Bold red power tie
                outline=self.stroke_color
            )

        elif archetype == "auditor":
            # Wireframe reading glasses
            gy = hy - int(head_radius * 0.15)
            draw.rectangle([hx - 28, gy - 12, hx - 6, gy + 12], outline=self.stroke_color, width=3)
            draw.rectangle([hx + 6, gy - 12, hx + 28, gy + 12], outline=self.stroke_color, width=3)
            draw.line([hx - 6, gy, hx + 6, gy], fill=self.stroke_color, width=3)

        elif archetype == "soldier":
            # Combat Kevlar Helmet
            helm_r = int(head_radius * 1.15)
            draw.arc([hx - helm_r, hy - helm_r - 4, hx + helm_r, hy + 4], start=180, end=360, fill=(75, 83, 32), width=18)
