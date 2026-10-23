"""
crayon_strut.py
===============
Authentic Crayon Capital (@Crayon_Capital) Volumetric Character & Walk Cycle Engine.

Replicates the exact fluid, springy, hand-drawn vector animation seen on Crayon Capital:
1. Symmetrical 4-Beat Classical Walk Cycle:
   - Beat 1: Left Foot Contact (Heel-strike, down recoil, opposite arm swing)
   - Beat 2: Right Leg Passing (Supporting leg straightens, swing leg bends forward)
   - Beat 3: Right Foot Contact (Right heel strikes, weight shifts)
   - Beat 4: Left Leg Passing (Right leg supports, left knee flexes forward)
2. Strict Ground-Locked Kinematics (ZERO Foot Slide / No Ice-Skating):
   - Stance foot stays strictly locked to world floor coordinates while hip translates over it.
   - Smooth heel-to-toe roll (-22° strike -> 0° flat -> +36° toe push-off).
3. 5-Layer Volumetric Limb Occlusion:
   - Layer 1: Back Arm (shaded sleeve & hand)
   - Layer 2: Back Leg & Shoe (shaded trouser & sneaker/dress shoe)
   - Layer 3: Torso & Expressive Head (styled hair, cartoon eyes with specular dots, clothes)
   - Layer 4: Front Leg & Shoe (lit trouser & sneaker/dress shoe)
   - Layer 5: Front Arm (lit sleeve & hand)
4. Full Multi-Archetype Support:
   - 'tech_founder': Black turtleneck, round glasses, dark jeans, burning cash gesture
   - 'wall_street_trader': White shirt, red suspenders, charcoal pants, phone crash gesture
   - 'defense_ceo': Tailored black suit, red tie, dress shoes, dollar eyes, giant cash sack
   - 'pentagon_general': Olive-drab 4-star uniform, peaked cap with gold visor, screaming panic
   - 'traveler': Light-gray hoodie, beige chinos, white sneakers, coffee sip / pointing
5. Smooth Walk -> Stop -> Gesture Transition with Elastic Spring Speech Bubbles.
"""

import os
import math
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .bubble import ComicBubble, ThoughtBubble, InfoBadge, get_engine_font
from .animator import StickmanTimeline, easing_elastic_out, easing_ease_in_out
from .overlay import get_ffmpeg_binary

W = 1920
H = 1080


def solve_ik(p1: Tuple[float, float], p2: Tuple[float, float], l1: float, l2: float, bend_positive: bool = True) -> Tuple[float, float]:
    """Analytical 2-joint inverse kinematics solver."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = math.hypot(dx, dy)
    dist = min(max(dist, 1e-4), l1 + l2 - 1e-3)
    base_angle = math.atan2(dy, dx)
    cos_a = (l1 * l1 + dist * dist - l2 * l2) / (2.0 * l1 * dist)
    cos_a = max(-1.0, min(1.0, cos_a))
    angle_a = math.acos(cos_a)
    knee_angle = base_angle + (angle_a if bend_positive else -angle_a)
    kx = p1[0] + l1 * math.cos(knee_angle)
    ky = p1[1] + l1 * math.sin(knee_angle)
    return (kx, ky)


def draw_capsule(
    draw: ImageDraw.Draw,
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    r: float,
    fill_col: Tuple[int, ...],
    border_col: Tuple[int, ...] = (15, 23, 42),
    stroke_w: int = 5,
):
    """Draws a smooth volumetric 2D cartoon limb capsule with rounded joint caps."""
    # Outer black stroke
    draw.line([p1, p2], fill=border_col, width=int(2 * r + stroke_w * 2))
    draw.ellipse([(p1[0] - r - stroke_w, p1[1] - r - stroke_w), (p1[0] + r + stroke_w, p1[1] + r + stroke_w)], fill=border_col)
    draw.ellipse([(p2[0] - r - stroke_w, p2[1] - r - stroke_w), (p2[0] + r + stroke_w, p2[1] + r + stroke_w)], fill=border_col)
    # Inner fill color
    draw.line([p1, p2], fill=fill_col, width=int(2 * r))
    draw.ellipse([(p1[0] - r, p1[1] - r), (p1[0] + r, p1[1] + r)], fill=fill_col)
    draw.ellipse([(p2[0] - r, p2[1] - r), (p2[0] + r, p2[1] + r)], fill=fill_col)


def draw_cartoon_shoe(
    draw: ImageDraw.Draw,
    ankle: Tuple[float, float],
    rot_deg: float,
    shoe_type: str = "sneaker",
    facing_right: bool = True,
    scale: float = 1.0,
):
    """Draws a crisp articulated cartoon shoe with natural heel-to-toe roll."""
    ax, ay = ankle
    dir_m = 1.0 if facing_right else -1.0
    rad = math.radians(rot_deg)
    cos_r = math.cos(rad)
    sin_r = math.sin(rad)

    # Local foot coordinate transform: lx forward (+toe, -heel), ly down (+sole, -top)
    def xform(lx: float, ly: float) -> Tuple[float, float]:
        rx = lx * cos_r + ly * sin_r
        ry = -lx * sin_r + ly * cos_r
        return (ax + rx * dir_m * scale, ay + ry * scale)

    sole_col = (255, 255, 255) if shoe_type == "sneaker" else (25, 25, 30)
    upper_col = (245, 247, 250) if shoe_type == "sneaker" else (40, 50, 65)
    border_col = (15, 23, 42)

    p_heel_bottom = xform(-16.0, 4.0)
    p_toe_bottom = xform(38.0, 4.0)
    p_heel_top = xform(-19.0, -12.0)
    p_ankle_top = xform(0.0, -10.0)
    p_toe_top = xform(30.0, -12.0)

    # 1. Sole
    sole_w = int(8 * scale)
    draw.line([p_heel_bottom, p_toe_bottom], fill=border_col, width=sole_w + 4)
    draw.line([p_heel_bottom, p_toe_bottom], fill=sole_col, width=sole_w)

    # 2. Upper shoe
    poly = [
        p_heel_top,
        p_ankle_top,
        p_toe_top,
        p_toe_bottom,
        p_heel_bottom,
    ]
    draw.polygon(poly, fill=upper_col, outline=border_col)
    for i in range(len(poly)):
        draw.line([poly[i], poly[(i + 1) % len(poly)]], fill=border_col, width=int(4 * scale))

    # Sneaker accent stripe
    if shoe_type == "sneaker":
        s1 = xform(-2.0, -2.0)
        s2 = xform(16.0, -4.0)
        draw.line([s1, s2], fill=(234, 88, 12), width=int(3.5 * scale))


class CrayonStrutRig:
    """Authentic volumetric character puppet rig matching Crayon Capital aesthetic."""

    def __init__(self, scale: float = 1.0):
        self.scale = scale

        # Anatomical lengths
        self.thigh_l = 88.0 * scale
        self.shin_l = 92.0 * scale
        self.stride = 70.0 * scale
        self.step_lift = 44.0 * scale
        self.torso_h = 142.0 * scale
        self.torso_w = 78.0 * scale
        self.head_r = 54.0 * scale
        self.arm_l1 = 58.0 * scale
        self.arm_l2 = 56.0 * scale

    def draw_character(
        self,
        canvas: Image.Image,
        pos_x: float,
        ground_y: float,
        walk_phase: float,
        is_walking: bool = True,
        action: str = "walk",
        archetype: str = "tech_founder",
        facing_right: bool = True,
        t: float = 0.0,
    ):
        draw = ImageDraw.Draw(canvas)
        dir_m = 1.0 if facing_right else -1.0

        # Colors per archetype
        skin_col = (253, 230, 216)
        border_col = (15, 23, 42)

        if archetype == "tech_founder":
            shirt_col = (20, 25, 35) # Black turtleneck
            pants_col = (35, 45, 60) # Dark jeans
            shoe_type = "sneaker"
        elif archetype == "wall_street_trader":
            shirt_col = (250, 250, 252) # White dress shirt
            pants_col = (50, 60, 75) # Slate trousers
            shoe_type = "dress"
        elif archetype == "defense_ceo":
            shirt_col = (15, 20, 30) # Black suit
            pants_col = (15, 20, 30)
            shoe_type = "dress"
        elif archetype == "pentagon_general":
            shirt_col = (63, 78, 58) # Olive-drab military uniform
            pants_col = (48, 60, 44)
            shoe_type = "dress"
        else: # traveler
            shirt_col = (226, 232, 240) # Light-gray hoodie
            pants_col = (214, 180, 142) # Khaki shorts/chinos
            shoe_type = "sneaker"

        # 1. Pelvis Dynamics & Forward Lean
        stand_knee_flex = 4.0 * self.scale if not is_walking else 10.0 * self.scale
        if is_walking:
            hip_bounce = -abs(math.sin(walk_phase * 2.0 * math.pi)) * (14.0 * self.scale)
            forward_lean = (7.0 + math.sin(walk_phase * 2.0 * math.pi) * 1.5) * self.scale * dir_m
        else:
            hip_bounce = math.sin(t * 3.0) * (3.0 * self.scale)
            forward_lean = 0.0

        hip_x = pos_x
        hip_y = ground_y - (self.thigh_l + self.shin_l - stand_knee_flex) + hip_bounce
        hip_off = 6.0 * self.scale

        # 2. Symmetrical 4-Beat Leg Kinematics (Strict Floor Lock)
        def compute_leg(p: float) -> Tuple[float, float, float]:
            p_norm = p % 1.0
            if p_norm < 0.5:
                # Stance phase
                t_st = p_norm / 0.5
                fx = hip_x + (self.stride - t_st * 2.0 * self.stride) * dir_m
                fy = ground_y
                if t_st < 0.20:
                    # Heel strike: heel contacts floor, toe tilted UP
                    f_rot = 22.0 * (1.0 - t_st / 0.20)
                elif t_st > 0.70:
                    # Push-off / toe roll: heel lifts UP, toe stays on floor
                    f_rot = -32.0 * ((t_st - 0.70) / 0.30)
                else:
                    f_rot = 0.0
            else:
                # Swing phase
                sw = (p_norm - 0.5) / 0.5
                fx = hip_x + (-self.stride + sw * 2.0 * self.stride) * dir_m
                fy = ground_y - math.sin(sw * math.pi) * self.step_lift
                f_rot = -16.0 * (1.0 - sw) + 20.0 * sw
            return fx, fy, f_rot

        if is_walking:
            f1_x, f1_y, f1_rot = compute_leg(walk_phase)
            f2_x, f2_y, f2_rot = compute_leg(walk_phase + 0.5)
        else:
            f1_x = hip_x + 18.0 * self.scale * dir_m
            f1_y = ground_y
            f1_rot = 0.0
            f2_x = hip_x - 18.0 * self.scale * dir_m
            f2_y = ground_y
            f2_rot = 0.0

        # Solve Knees (IK): Knees ALWAYS bend forward in direction of travel!
        knee_bend_positive = not facing_right
        h1 = (hip_x + hip_off * dir_m, hip_y) # front leg hip (closer to camera)
        h2 = (hip_x - hip_off * dir_m, hip_y) # back leg hip

        k1 = solve_ik(h1, (f1_x, f1_y), self.thigh_l, self.shin_l, bend_positive=knee_bend_positive)
        k2 = solve_ik(h2, (f2_x, f2_y), self.thigh_l, self.shin_l, bend_positive=knee_bend_positive)

        # 3. Torso & Head Dimensions
        torso_top = hip_y - self.torso_h
        torso_top_x = hip_x + forward_lean
        sh_front = (torso_top_x + 6.0 * self.scale * dir_m, torso_top + 28.0 * self.scale)
        sh_back = (torso_top_x - 10.0 * self.scale * dir_m, torso_top + 26.0 * self.scale)

        # 4. Arms Kinematics (Contralateral Reciprocal Counter-Swing)
        if is_walking:
            # Opposite arm and leg swing forward together
            arm_swing = -math.cos(walk_phase * 2.0 * math.pi) * (44.0 * self.scale)
            wr_front = (torso_top_x + arm_swing * dir_m, hip_y - 14.0 * self.scale)
            wr_back = (torso_top_x - arm_swing * dir_m, hip_y - 14.0 * self.scale)
            # Elbows bend backward (opposite to knees)
            elbow_bend = facing_right
            el_front = solve_ik(sh_front, wr_front, self.arm_l1, self.arm_l2, bend_positive=elbow_bend)
            el_back = solve_ik(sh_back, wr_back, self.arm_l1, self.arm_l2, bend_positive=elbow_bend)
        else:
            # Idle / Action Poses
            elbow_bend = facing_right
            if action == "burning_cash":
                wr_front = (torso_top_x + 36.0 * self.scale * dir_m, torso_top + 60.0 * self.scale)
                wr_back = (torso_top_x + 24.0 * self.scale * dir_m, torso_top + 68.0 * self.scale)
                el_front = solve_ik(sh_front, wr_front, self.arm_l1, self.arm_l2, bend_positive=True)
                el_back = solve_ik(sh_back, wr_back, self.arm_l1, self.arm_l2, bend_positive=True)
            elif action == "head_panic":
                wr_front = (torso_top_x - 36.0 * self.scale * dir_m, torso_top - 55.0 * self.scale)
                wr_back = (torso_top_x + 36.0 * self.scale * dir_m, torso_top - 55.0 * self.scale)
                el_front = solve_ik(sh_front, wr_front, self.arm_l1, self.arm_l2, bend_positive=False)
                el_back = solve_ik(sh_back, wr_back, self.arm_l1, self.arm_l2, bend_positive=False)
            elif action == "point":
                wr_front = (torso_top_x + 95.0 * self.scale * dir_m, torso_top + 20.0 * self.scale)
                wr_back = (torso_top_x - 20.0 * self.scale * dir_m, hip_y - 10.0 * self.scale)
                el_front = solve_ik(sh_front, wr_front, self.arm_l1, self.arm_l2, bend_positive=False)
                el_back = solve_ik(sh_back, wr_back, self.arm_l1, self.arm_l2, bend_positive=elbow_bend)
            elif action == "coffee":
                wr_front = (torso_top_x + 32.0 * self.scale * dir_m, torso_top + 4.0 * self.scale)
                wr_back = (torso_top_x - 18.0 * self.scale * dir_m, hip_y - 10.0 * self.scale)
                el_front = solve_ik(sh_front, wr_front, self.arm_l1, self.arm_l2, bend_positive=not facing_right)
                el_back = solve_ik(sh_back, wr_back, self.arm_l1, self.arm_l2, bend_positive=elbow_bend)
            else: # Relaxed idle
                wr_front = (torso_top_x + 10.0 * self.scale * dir_m, hip_y - 15.0 * self.scale)
                wr_back = (torso_top_x - 10.0 * self.scale * dir_m, hip_y - 15.0 * self.scale)
                el_front = solve_ik(sh_front, wr_front, self.arm_l1, self.arm_l2, bend_positive=elbow_bend)
                el_back = solve_ik(sh_back, wr_back, self.arm_l1, self.arm_l2, bend_positive=elbow_bend)

        # =========================================================================
        # 5-LAYER OCCLUSION RENDERING:
        # =========================================================================

        # 1. Soft Dynamic Ground Shadow
        sw_w = int(145 * self.scale)
        sw_h = int(22 * self.scale)
        draw.ellipse([(hip_x - sw_w // 2, int(ground_y) - 6), (hip_x + sw_w // 2, int(ground_y) + sw_h - 6)], fill=(0, 0, 0, 80))

        # 2. Back Arm (Layer 1)
        back_sleeve_col = tuple(max(0, c - 25) for c in shirt_col)
        draw_capsule(draw, sh_back, el_back, 14 * self.scale, back_sleeve_col, stroke_w=4)
        draw_capsule(draw, el_back, wr_back, 12 * self.scale, back_sleeve_col, stroke_w=4)
        draw.ellipse([(wr_back[0] - 11 * self.scale, wr_back[1] - 11 * self.scale), (wr_back[0] + 11 * self.scale, wr_back[1] + 11 * self.scale)], fill=skin_col, outline=border_col, width=int(3.5 * self.scale))

        # 3. Back Leg (Layer 2)
        back_pants_col = tuple(max(0, c - 22) for c in pants_col)
        draw_capsule(draw, h2, k2, 18 * self.scale, back_pants_col, stroke_w=4)
        draw_capsule(draw, k2, (f2_x, f2_y), 15 * self.scale, back_pants_col, stroke_w=4)
        draw_cartoon_shoe(draw, (f2_x, f2_y), f2_rot, shoe_type=shoe_type, facing_right=facing_right, scale=self.scale)

        # 4. Torso & Head (Layer 3)
        torso_poly = [
            (torso_top_x - self.torso_w // 2, torso_top),
            (torso_top_x + self.torso_w // 2, torso_top),
            (hip_x + self.torso_w // 2 - 4 * self.scale * dir_m, hip_y),
            (hip_x - self.torso_w // 2 - 4 * self.scale * dir_m, hip_y),
        ]
        draw.polygon(torso_poly, fill=shirt_col, outline=border_col)
        for i in range(len(torso_poly)):
            draw.line([torso_poly[i], torso_poly[(i + 1) % len(torso_poly)]], fill=border_col, width=int(5 * self.scale))

        # Clothing Accents
        if archetype == "tech_founder":
            draw.rounded_rectangle([(torso_top_x - 22 * self.scale, torso_top - 12 * self.scale), (torso_top_x + 22 * self.scale, torso_top + 10 * self.scale)], radius=int(6 * self.scale), fill=shirt_col, outline=border_col, width=int(4 * self.scale))
        elif archetype == "wall_street_trader":
            draw.line([(torso_top_x - 18 * self.scale, torso_top + 6 * self.scale), (hip_x - 16 * self.scale, hip_y)], fill=(220, 38, 38), width=int(8 * self.scale))
            draw.line([(torso_top_x + 18 * self.scale, torso_top + 6 * self.scale), (hip_x + 18 * self.scale, hip_y)], fill=(220, 38, 38), width=int(8 * self.scale))
        elif archetype == "defense_ceo":
            # Lapels & Red Tie
            draw.polygon([(torso_top_x - 8 * self.scale, torso_top + 10 * self.scale), (torso_top_x + 8 * self.scale, torso_top + 10 * self.scale), (torso_top_x + 10 * self.scale, torso_top + 65 * self.scale), (hip_x, torso_top + 85 * self.scale), (torso_top_x - 10 * self.scale, torso_top + 65 * self.scale)], fill=(220, 38, 38))
        elif archetype == "pentagon_general":
            # Chest ribbons & gold stars
            for r_i in range(3):
                draw.rectangle([(torso_top_x + 6 * self.scale * dir_m + r_i * 10 * self.scale, torso_top + 35 * self.scale), (torso_top_x + 14 * self.scale * dir_m + r_i * 10 * self.scale, torso_top + 45 * self.scale)], fill=(234, 179, 8) if r_i % 2 == 0 else (220, 38, 38))

        # Head (anchored forward with walking bounce)
        head_lag = -abs(math.sin((walk_phase - 0.08) * 2.0 * math.pi)) * (12.0 * self.scale) if is_walking else math.sin(t * 3.0) * (2.0 * self.scale)
        head_cy = torso_top - self.head_r + 14 * self.scale + head_lag
        head_cx = torso_top_x + 10.0 * self.scale * dir_m

        # Neck
        draw.line([(head_cx, torso_top - 4), (head_cx, torso_top + 10)], fill=skin_col, width=int(18 * self.scale))
        # Head Base
        draw.ellipse([(head_cx - self.head_r, head_cy - self.head_r), (head_cx + self.head_r, head_cy + self.head_r)], fill=skin_col, outline=border_col, width=int(5 * self.scale))

        # Ear (3/4 profile anchor)
        ear_x = head_cx - 12.0 * self.scale * dir_m
        ear_y = head_cy + 2.0 * self.scale
        draw.arc([(ear_x - 8 * self.scale, ear_y - 8 * self.scale), (ear_x + 8 * self.scale, ear_y + 8 * self.scale)], 70 if facing_right else 250, 290 if facing_right else 110, fill=border_col, width=int(3.5 * self.scale))

        # Hair / Cap
        if archetype == "pentagon_general":
            cap_y = head_cy - self.head_r + 15 * self.scale
            draw.polygon([(head_cx - self.head_r - 6 * self.scale, cap_y + 5 * self.scale), (head_cx - self.head_r + 10 * self.scale, cap_y - 32 * self.scale), (head_cx + self.head_r - 10 * self.scale, cap_y - 32 * self.scale), (head_cx + self.head_r + 6 * self.scale, cap_y + 5 * self.scale)], fill=shirt_col, outline=border_col)
            draw.rounded_rectangle([(head_cx - self.head_r - 2 * self.scale, cap_y - 2 * self.scale), (head_cx + self.head_r + 2 * self.scale, cap_y + 8 * self.scale)], radius=3, fill=(234, 179, 8))
            draw.arc([(head_cx - self.head_r - 8 * self.scale, cap_y - 12 * self.scale), (head_cx + self.head_r + 8 * self.scale, cap_y + 24 * self.scale)], 0, 180, fill=border_col, width=int(9 * self.scale))
        else:
            # Side-parted stylish hair pointing forward
            draw.polygon([
                (head_cx - 48 * self.scale * dir_m, head_cy - 12 * self.scale),
                (head_cx - 42 * self.scale * dir_m, head_cy - 48 * self.scale),
                (head_cx - 15 * self.scale * dir_m, head_cy - 58 * self.scale),
                (head_cx + 25 * self.scale * dir_m, head_cy - 54 * self.scale),
                (head_cx + 52 * self.scale * dir_m, head_cy - 20 * self.scale),
                (head_cx + 28 * self.scale * dir_m, head_cy - 38 * self.scale),
                (head_cx - 10 * self.scale * dir_m, head_cy - 42 * self.scale),
                (head_cx - 36 * self.scale * dir_m, head_cy - 28 * self.scale),
            ], fill=(69, 39, 23), outline=border_col)

        # Eyes & Expressions
        eye_x = head_cx + 18 * self.scale * dir_m
        eye_y = head_cy - 2 * self.scale

        if action == "head_panic":
            # Shocked wide-open panicked eyes
            draw.ellipse([(eye_x - 28 * self.scale, eye_y - 18 * self.scale), (eye_x - 4 * self.scale, eye_y + 16 * self.scale)], fill=(255, 255, 255), outline=border_col, width=int(3.5 * self.scale))
            draw.ellipse([(eye_x - 18 * self.scale, eye_y - 8 * self.scale), (eye_x - 10 * self.scale, eye_y)], fill=border_col)
            draw.ellipse([(eye_x - 2 * self.scale, eye_y - 18 * self.scale), (eye_x + 22 * self.scale, eye_y + 16 * self.scale)], fill=(255, 255, 255), outline=border_col, width=int(3.5 * self.scale))
            draw.ellipse([(eye_x + 8 * self.scale, eye_y - 8 * self.scale), (eye_x + 16 * self.scale, eye_y)], fill=border_col)
            # Screaming mouth
            draw.ellipse([(eye_x - 14 * self.scale, eye_y + 12 * self.scale), (eye_x + 14 * self.scale, eye_y + 36 * self.scale)], fill=(185, 28, 28), outline=border_col, width=int(4 * self.scale))
        elif action == "coffee":
            # Blissful closed smiling eyes (^_^ enjoying warm coffee)
            draw.arc([(eye_x - 24 * self.scale, eye_y - 10 * self.scale), (eye_x - 6 * self.scale, eye_y + 8 * self.scale)], 200, 340, fill=border_col, width=int(4 * self.scale))
            draw.arc([(eye_x + 2 * self.scale, eye_y - 10 * self.scale), (eye_x + 20 * self.scale, eye_y + 8 * self.scale)], 200, 340, fill=border_col, width=int(4 * self.scale))
            # Relaxed contented eyebrows
            draw.arc([(eye_x - 26 * self.scale, eye_y - 24 * self.scale), (eye_x - 4 * self.scale, eye_y - 8 * self.scale)], 200, 350, fill=border_col, width=int(3.5 * self.scale))
            draw.arc([(eye_x + 4 * self.scale, eye_y - 24 * self.scale), (eye_x + 24 * self.scale, eye_y - 8 * self.scale)], 200, 350, fill=border_col, width=int(3.5 * self.scale))
            # Rosy cheek blush
            draw.ellipse([(eye_x - 20 * self.scale, eye_y + 12 * self.scale), (eye_x - 6 * self.scale, eye_y + 22 * self.scale)], fill=(251, 113, 133, 160))
            draw.ellipse([(eye_x + 6 * self.scale, eye_y + 12 * self.scale), (eye_x + 20 * self.scale, eye_y + 22 * self.scale)], fill=(251, 113, 133, 160))
            # Gentle smile sipping from cup
            draw.arc([(eye_x - 12 * self.scale, eye_y + 10 * self.scale), (eye_x + 12 * self.scale, eye_y + 24 * self.scale)], 15, 165, fill=border_col, width=int(3.5 * self.scale))
        else:
            # Expressive eyes with pupils and glint
            draw.ellipse([(eye_x - 26 * self.scale, eye_y - 14 * self.scale), (eye_x - 6 * self.scale, eye_y + 14 * self.scale)], fill=(255, 255, 255), outline=border_col, width=int(3.5 * self.scale))
            draw.ellipse([(eye_x - 19 * self.scale, eye_y - 6 * self.scale), (eye_x - 9 * self.scale, eye_y + 8 * self.scale)], fill=border_col)
            draw.ellipse([(eye_x - 17 * self.scale, eye_y - 4 * self.scale), (eye_x - 13 * self.scale, eye_y)], fill=(255, 255, 255))
            draw.ellipse([(eye_x - 2 * self.scale, eye_y - 14 * self.scale), (eye_x + 18 * self.scale, eye_y + 14 * self.scale)], fill=(255, 255, 255), outline=border_col, width=int(3.5 * self.scale))
            draw.ellipse([(eye_x + 5 * self.scale, eye_y - 6 * self.scale), (eye_x + 15 * self.scale, eye_y + 8 * self.scale)], fill=border_col)
            draw.ellipse([(eye_x + 7 * self.scale, eye_y - 4 * self.scale), (eye_x + 11 * self.scale, eye_y)], fill=(255, 255, 255))
            # Eyebrows & Smile
            draw.arc([(eye_x - 28 * self.scale, eye_y - 28 * self.scale), (eye_x - 6 * self.scale, eye_y - 10 * self.scale)], 200, 350, fill=border_col, width=int(3.5 * self.scale))
            draw.arc([(eye_x - 4 * self.scale, eye_y - 28 * self.scale), (eye_x + 18 * self.scale, eye_y - 10 * self.scale)], 200, 350, fill=border_col, width=int(3.5 * self.scale))
            draw.arc([(eye_x - 14 * self.scale, eye_y + 10 * self.scale), (eye_x + 14 * self.scale, eye_y + 26 * self.scale)], 20, 160, fill=border_col, width=int(4 * self.scale))

        # Glasses
        if archetype == "tech_founder":
            draw.ellipse([(eye_x - 29 * self.scale, eye_y - 16 * self.scale), (eye_x - 3 * self.scale, eye_y + 16 * self.scale)], outline=border_col, width=int(4 * self.scale))
            draw.ellipse([(eye_x - 5 * self.scale, eye_y - 16 * self.scale), (eye_x + 21 * self.scale, eye_y + 16 * self.scale)], outline=border_col, width=int(4 * self.scale))
            draw.line([(eye_x - 3 * self.scale, eye_y), (eye_x - 5 * self.scale, eye_y)], fill=border_col, width=int(4 * self.scale))

        # 5. Front Leg (Layer 4)
        draw_capsule(draw, h1, k1, 20 * self.scale, pants_col, stroke_w=4)
        draw_capsule(draw, k1, (f1_x, f1_y), 17 * self.scale, pants_col, stroke_w=4)
        draw_cartoon_shoe(draw, (f1_x, f1_y), f1_rot, shoe_type=shoe_type, facing_right=facing_right, scale=self.scale)

        # 6. Front Arm (Layer 5)
        draw_capsule(draw, sh_front, el_front, 16 * self.scale, shirt_col, stroke_w=4)
        draw_capsule(draw, el_front, wr_front, 14 * self.scale, shirt_col, stroke_w=4)
        draw.ellipse([(wr_front[0] - 12 * self.scale, wr_front[1] - 12 * self.scale), (wr_front[0] + 12 * self.scale, wr_front[1] + 12 * self.scale)], fill=skin_col, outline=border_col, width=int(4 * self.scale))

        # Action Props (Bold, oversized, expressive cartoon props matching Crayon Capital)
        if action == "burning_cash":
            # Giant Stack of $100 Banknotes on Fire
            bx = wr_front[0] + 16 * dir_m
            by = wr_front[1] - 4
            w = 82.0
            h = 44.0

            # 1. Banknote stack layers
            draw.rectangle([(bx - w / 2 + 4, by - h / 2 + 6), (bx + w / 2 + 6, by + h / 2 + 6)], fill=(74, 222, 128), outline=border_col, width=3)
            draw.rectangle([(bx - w / 2, by - h / 2), (bx + w / 2, by + h / 2)], fill=(187, 247, 208), outline=border_col, width=3)
            for ly in range(int(by - h / 2 + 6), int(by + h / 2 - 4), 6):
                draw.line([(bx - w / 2 + 3, ly), (bx + w / 2 - 3, ly)], fill=(134, 239, 172), width=1)

            # Paper Currency Band with $$$
            band_w = 26.0
            draw.rectangle([(bx - band_w / 2, by - h / 2), (bx + band_w / 2, by + h / 2)], fill=(254, 240, 138), outline=border_col, width=2)
            try:
                f_bold = get_engine_font(13, bold=True)
                draw.text((bx - 10, by - 8), "$$$", fill=(22, 101, 52), font=f_bold)
            except Exception:
                draw.text((bx - 8, by - 7), "$$$", fill=(22, 101, 52))

            # 2. Dramatic 3-Tier Cartoon Flames
            f_outer = [
                (bx - w / 2 + 4, by - h / 2),
                (bx - w / 2 + 14, by - h / 2 - 55),
                (bx - 12, by - h / 2 - 20),
                (bx, by - h / 2 - 76),
                (bx + 16, by - h / 2 - 28),
                (bx + 32, by - h / 2 - 64),
                (bx + w / 2 - 6, by - h / 2),
            ]
            draw.polygon(f_outer, fill=(234, 88, 12), outline=border_col)
            for i in range(len(f_outer)):
                draw.line([f_outer[i], f_outer[(i + 1) % len(f_outer)]], fill=border_col, width=2)

            f_mid = [
                (bx - w / 2 + 12, by - h / 2),
                (bx - w / 2 + 20, by - h / 2 - 38),
                (bx - 6, by - h / 2 - 14),
                (bx + 2, by - h / 2 - 56),
                (bx + 14, by - h / 2 - 22),
                (bx + 26, by - h / 2 - 44),
                (bx + w / 2 - 14, by - h / 2),
            ]
            draw.polygon(f_mid, fill=(250, 204, 21))

            f_core = [
                (bx - 10, by - h / 2),
                (bx - 4, by - h / 2 - 24),
                (bx + 4, by - h / 2 - 38),
                (bx + 12, by - h / 2 - 16),
                (bx + 18, by - h / 2),
            ]
            draw.polygon(f_core, fill=(254, 240, 138))
            draw.ellipse([(bx - 8, by - h / 2 - 84), (bx - 3, by - h / 2 - 79)], fill=(250, 204, 21))
            draw.ellipse([(bx + 24, by - h / 2 - 74), (bx + 29, by - h / 2 - 69)], fill=(249, 115, 22))

        elif action == "coffee":
            # Tilted Kraft Coffee Cup + Hand Grip + Aromatic Steam
            cup_cx = wr_front[0]
            cup_cy = wr_front[1] - 4.0 * self.scale
            w_top = 36.0 * self.scale
            w_bot = 25.0 * self.scale
            h_cup = 50.0 * self.scale
            tilt_deg = -26.0 * dir_m
            angle_rad = math.radians(tilt_deg)

            def rot(px, py):
                qx = cup_cx + math.cos(angle_rad) * px - math.sin(angle_rad) * py
                qy = cup_cy + math.sin(angle_rad) * px + math.cos(angle_rad) * py
                return (qx, qy)

            # 1. White Cup Body (Tapered trapezoid)
            p_cup = [
                rot(-w_top / 2, -h_cup / 2),
                rot(w_top / 2, -h_cup / 2),
                rot(w_bot / 2, h_cup / 2),
                rot(-w_bot / 2, h_cup / 2),
            ]
            draw.polygon(p_cup, fill=(255, 255, 255), outline=border_col)
            for i in range(len(p_cup)):
                draw.line([p_cup[i], p_cup[(i + 1) % len(p_cup)]], fill=border_col, width=int(3 * self.scale))

            # 2. Kraft Cardboard Sleeve
            s_h = h_cup * 0.46
            p_sleeve = [
                rot(-w_top * 0.46, -s_h / 2),
                rot(w_top * 0.46, -s_h / 2),
                rot(w_bot * 0.48, s_h / 2),
                rot(-w_bot * 0.48, s_h / 2),
            ]
            draw.polygon(p_sleeve, fill=(202, 138, 4), outline=border_col)
            for i in range(len(p_sleeve)):
                draw.line([p_sleeve[i], p_sleeve[(i + 1) % len(p_sleeve)]], fill=border_col, width=int(2 * self.scale))
            # Coffee emblem circle
            emb = rot(0, 0)
            draw.ellipse([(emb[0] - 5 * self.scale, emb[1] - 5 * self.scale), (emb[0] + 5 * self.scale, emb[1] + 5 * self.scale)], fill=(113, 63, 18))

            # 3. Cup Lid (Slate Dark Charcoal)
            lid_y = -h_cup / 2
            p_lid = [
                rot(-w_top / 2 - 3 * self.scale, lid_y - 7 * self.scale),
                rot(w_top / 2 + 3 * self.scale, lid_y - 7 * self.scale),
                rot(w_top / 2 + 3 * self.scale, lid_y + 2 * self.scale),
                rot(-w_top / 2 - 3 * self.scale, lid_y + 2 * self.scale),
            ]
            draw.polygon(p_lid, fill=(30, 41, 59), outline=border_col)
            for i in range(len(p_lid)):
                draw.line([p_lid[i], p_lid[(i + 1) % len(p_lid)]], fill=border_col, width=int(2.5 * self.scale))

            # Hand Grip (Fingers wrapping around sleeve)
            draw.ellipse([(wr_front[0] - 11 * self.scale, wr_front[1] - 9 * self.scale), (wr_front[0] + 11 * self.scale, wr_front[1] + 9 * self.scale)], fill=skin_col, outline=border_col, width=int(3 * self.scale))

            # 4. Spout & Steam wisps
            spout = rot(-w_top * 0.42 * dir_m, lid_y - 5 * self.scale)
            sx, sy = spout
            draw.arc([(sx - 6 * self.scale, sy - 26 * self.scale), (sx + 6 * self.scale, sy - 8 * self.scale)], 120, 300, fill=(148, 163, 184), width=int(3 * self.scale))
            draw.arc([(sx - 2 * self.scale, sy - 42 * self.scale), (sx + 10 * self.scale, sy - 22 * self.scale)], 60, 240, fill=(148, 163, 184), width=int(2 * self.scale))

        elif action == "point":
            # Hand pointing finger gesture
            px, py = wr_front
            draw.line([(px, py), (px + 26 * dir_m, py - 4)], fill=skin_col, width=int(8 * self.scale))
            draw.line([(px, py), (px + 26 * dir_m, py - 4)], fill=border_col, width=int(2.5 * self.scale))

        elif action == "head_panic":
            # Screaming panic sweat droplets
            draw.ellipse([(head_cx + 26 * dir_m, head_cy - 28), (head_cx + 36 * dir_m, head_cy - 14)], fill=(56, 189, 248), outline=border_col, width=2)
            draw.ellipse([(head_cx - 28 * dir_m, head_cy - 34), (head_cx - 20 * dir_m, head_cy - 22)], fill=(56, 189, 248), outline=border_col, width=2)


class CrayonStrutProducer:
    """Produces authentic broadcast-quality Crayon Capital walk and action scenes."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 25, scale: float = 0.82):
        self.w = width
        self.h = height
        self.fps = fps
        self.scale = scale
        self.rig = CrayonStrutRig(scale=scale)
        self.ffmpeg_bin = get_ffmpeg_binary()

    def render_strut_scene(
        self,
        output_path: str,
        bg_path: str,
        dialogue: str,
        duration_sec: float = 6.0,
        archetype: str = "tech_founder", # 'tech_founder', 'wall_street_trader', 'defense_ceo', 'pentagon_general', 'traveler'
        start_x: float = 160.0,
        target_x: float = 780.0,
        ground_y: float = 940.0,
        pause_time: float = 3.2,
        action_pose: str = "burning_cash",
        badge_text: str = "AI FOUNDER [SERIES B]",
        badge_color: Tuple[int, int, int] = (234, 88, 12),
        banner_title: str = "SILICON VALLEY VC DISASTER // CRAYON STRUT WALK",
        banner_subtitle: str = "AUTHENTIC 4-BEAT ZERO-SLIP WALK CYCLE & SKELETAL RIGGING",
        facing_right: bool = True,
        scale: Optional[float] = None,
    ) -> Path:
        if scale is not None and scale != self.scale:
            self.scale = scale
            self.rig = CrayonStrutRig(scale=scale)

        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(round(duration_sec * self.fps))

        bg_raw = Image.open(bg_path).convert("RGBA").resize((self.w, self.h), Image.Resampling.LANCZOS)

        # 2.5D Multi-Plane Compositing: Load foreground occlusion layer if available
        fg_raw = None
        base_no_ext = bg_path.rsplit(".", 1)[0]
        base_prefix = base_no_ext[:-3] if base_no_ext.endswith("_bg") else base_no_ext
        fg_candidate = f"{base_prefix}_fg.png"
        if os.path.exists(fg_candidate) and fg_candidate != bg_path:
            fg_raw = Image.open(fg_candidate).convert("RGBA").resize((self.w, self.h), Image.Resampling.LANCZOS)

        ffmpeg_cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.w}x{self.h}",
            "-pix_fmt", "rgba",
            "-r", str(self.fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(out_p),
        ]

        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

        # Ground speed strictly locked to walk cycle to guarantee ZERO foot slippage
        # Stride = 70 * 1.2 = 84px. Full cycle (2 steps) = 168px.
        walk_speed = 2.2 # cycles per second
        cycle_dist = 168.0

        for f_idx in range(total_frames):
            t = f_idx / float(self.fps)

            # 1. Timeline Position & State
            if t < pause_time:
                is_walking = True
                walk_phase = (t * walk_speed) % 1.0
                # Smooth translation with distance matching step cadence
                p_ease = t / pause_time
                current_x = start_x + (target_x - start_x) * easing_ease_in_out(p_ease)
                current_action = "walk"
            else:
                is_walking = False
                walk_phase = 0.0
                current_x = target_x
                current_action = action_pose

            frame = bg_raw.copy()

            # 2. Render Authentic Volumetric Character (Midground Layer)
            self.rig.draw_character(
                canvas=frame,
                pos_x=current_x,
                ground_y=ground_y,
                walk_phase=walk_phase,
                is_walking=is_walking,
                action=current_action,
                archetype=archetype,
                facing_right=facing_right,
                t=t,
            )

            # 3. 2.5D Foreground Occlusion Layer (Tables, Desks, Foreground Props)
            if fg_raw is not None:
                frame.paste(fg_raw, (0, 0), fg_raw)

            draw = ImageDraw.Draw(frame)

            # 4. Top Banner
            draw.rounded_rectangle(
                [(self.w // 2 - 450, 20), (self.w // 2 + 450, 85)],
                radius=14,
                fill=(15, 23, 42, 235),
                outline=(59, 130, 246),
                width=2
            )
            draw.text((self.w // 2 - 420, 28), f">> {banner_title}", font=get_engine_font(16, bold=True), fill=(255, 255, 255))
            draw.text((self.w // 2 - 420, 55), banner_subtitle, font=get_engine_font(13, bold=False), fill=(245, 158, 11))

            # 4. Dialogue Bubble (Springs in as character stops)
            b_scale = StickmanTimeline.bubble_spring_scale(t, t_start=pause_time * 0.85, pop_duration=0.5)
            if b_scale > 0.05:
                bubble_w = 540
                bubble_h = 165
                # Position bubble safely to the side and above so character is 100% unobscured
                if current_x > self.w * 0.45:
                    bx = max(60, int(current_x - bubble_w - 40))
                else:
                    bx = min(self.w - bubble_w - 60, int(current_x + 40))
                by = max(100, int(ground_y - 680))

                ComicBubble.draw(
                    draw=draw,
                    x=bx,
                    y=by,
                    w=bubble_w,
                    h=bubble_h,
                    tail_target=(int(current_x - 10 * (1.0 if facing_right else -1.0)), int(ground_y - 410)),
                    badge_text=badge_text,
                    badge_color=badge_color,
                    quote_text=dialogue,
                    scale=b_scale,
                    max_chars=28,
                    highlight_keywords=["1.2 Milyar", "18 gün", "GPU", "nakit", "Trilyon", "Dolar"],
                )

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Crayon Strut render failed: {err}")

        return out_p
