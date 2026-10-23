"""
articulated_rig.py
==================
Advanced 2D Articulated Kinematic Rigging Engine with:
1. True Ankle Roll & Foot Kinematics (Heel-strike, foot-flat, toe-off, swing bend).
2. Articulated Arms & Expressive Hands (Yoke grip, radio mic to mouth, pointing, panic gestures).
3. Aviation Blackbox & Travel Archetypes:
   - Airline Captain (Peaked cap, 4 gold epaulettes, yoke grip & control inputs).
   - First Officer (3 gold stripes, alarmed pointing at instruments, panic reaction).
   - ATC Tower Controller (Aviation headset, boom mic, radio push-to-talk mic action).
   - NTSB Crash Investigator (Hi-vis vest, magnifying glass, inspection clipboard).
   - Traveler / Vlogger (Full walk cycle with foot roll, coffee sip, smartphone GPS, backpack).
"""

import math
import random
from typing import Tuple, Optional, Dict, Any, List
from PIL import Image, ImageDraw, ImageFont

from .bubble import get_engine_font


def solve_ik(p1: Tuple[float, float], p2: Tuple[float, float], l1: float, l2: float, bend_positive: bool = True) -> Tuple[float, float]:
    """Analytical 2-joint IK solver."""
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


class ArticulatedRig:
    """Renders highly expressive, fully articulated vector stickmen for Aviation & Travel."""

    def __init__(self, scale: float = 1.0):
        self.scale = scale

        # Limb segments
        self.thigh_len = 84.0 * scale
        self.shin_len = 88.0 * scale
        self.foot_len = 34.0 * scale
        self.upper_arm = 54.0 * scale
        self.forearm = 52.0 * scale
        self.torso_h = 138.0 * scale
        self.torso_w = 70.0 * scale
        self.head_r = 54.0 * scale

    def draw_foot(
        self,
        draw: ImageDraw.Draw,
        ankle: Tuple[float, float],
        foot_angle_deg: float,
        shoe_color: Tuple[int, int, int] = (234, 88, 12),
        facing_right: bool = True,
    ):
        """Renders an articulated shoe with true rotational roll (heel vs toe)."""
        ax, ay = ankle
        rad = math.radians(foot_angle_deg)
        dir_mult = 1.0 if facing_right else -1.0

        # Local foot vector from ankle
        cos_r = math.cos(rad) * dir_mult
        sin_r = math.sin(rad)

        heel_x = ax - 12.0 * self.scale * cos_r
        heel_y = ay + 12.0 * self.scale * sin_r
        toe_x = ax + 26.0 * self.scale * cos_r
        toe_y = ay - 26.0 * self.scale * sin_r

        # Draw shoe sole
        draw.line([(heel_x, heel_y + 4), (toe_x, toe_y + 4)], fill=(15, 23, 42), width=int(8 * self.scale))
        # Draw shoe upper
        draw.polygon([
            (heel_x, heel_y - 8 * self.scale),
            (toe_x - 6 * self.scale * cos_r, toe_y - 10 * self.scale),
            (toe_x, toe_y + 4),
            (heel_x, heel_y + 4),
        ], fill=shoe_color)
        draw.line([(heel_x, heel_y - 8 * self.scale), (toe_x - 6 * self.scale * cos_r, toe_y - 10 * self.scale)], fill=(15, 23, 42), width=int(3 * self.scale))
        draw.line([(toe_x - 6 * self.scale * cos_r, toe_y - 10 * self.scale), (toe_x, toe_y + 4)], fill=(15, 23, 42), width=int(3 * self.scale))

    def draw_hand(
        self,
        draw: ImageDraw.Draw,
        wrist: Tuple[float, float],
        gesture: str = "relaxed", # 'relaxed', 'fist', 'point', 'yoke_grip', 'mic_hold', 'phone_hold'
        facing_right: bool = True,
    ):
        """Renders detailed articulated hand with fingers/thumb."""
        wx, wy = wrist
        hr = 10.0 * self.scale
        dir_m = 1.0 if facing_right else -1.0

        # Palm base
        draw.ellipse([(wx - hr, wy - hr), (wx + hr, wy + hr)], fill=(255, 255, 255), outline=(15, 23, 42), width=int(3 * self.scale))

        if gesture == "point":
            # Extended index finger
            fx = wx + 20.0 * self.scale * dir_m
            fy = wy - 10.0 * self.scale
            draw.line([(wx + 5 * self.scale * dir_m, wy - 3 * self.scale), (fx, fy)], fill=(15, 23, 42), width=int(7 * self.scale))
            draw.line([(wx + 5 * self.scale * dir_m, wy - 3 * self.scale), (fx, fy)], fill=(255, 255, 255), width=int(3 * self.scale))
            # Thumb
            draw.line([(wx, wy - 4 * self.scale), (wx + 8 * self.scale * dir_m, wy - 12 * self.scale)], fill=(15, 23, 42), width=int(5 * self.scale))

        elif gesture == "yoke_grip":
            # Curved fingers wrapped around airplane yoke
            draw.arc([(wx - 12 * self.scale, wy - 14 * self.scale), (wx + 14 * self.scale, wy + 14 * self.scale)], -90, 90 if facing_right else 270, fill=(15, 23, 42), width=int(6 * self.scale))

        elif gesture == "mic_hold":
            # Hand gripping radio microphone
            draw.rounded_rectangle([(wx - 8 * self.scale, wy - 14 * self.scale), (wx + 14 * self.scale, wy + 10 * self.scale)], radius=int(4 * self.scale), fill=(40, 50, 65), outline=(15, 23, 42), width=int(2 * self.scale))

    def draw_aviation_character(
        self,
        canvas: Image.Image,
        pos_x: float,
        pos_y: float,
        role: str = "captain", # 'captain', 'first_officer', 'atc', 'investigator'
        action: str = "fly", # 'fly', 'panic', 'point_warning', 'talk_mic', 'inspect'
        bank_angle: float = 0.0,
        yoke_turn: float = 0.0,
        t: float = 0.0,
    ):
        """
        Renders an aviation character with cockpit/ATC/NTSB accessories, controls, and expressive hand gestures.
        """
        draw = ImageDraw.Draw(canvas)
        cx = pos_x
        cy = pos_y

        # Subtle cockpit vibration / turbulence shake
        turb_x = math.sin(t * 35.0) * 2.0 if action == "panic" else math.sin(t * 2.0) * 1.0
        turb_y = math.cos(t * 28.0) * 2.5 if action == "panic" else math.cos(t * 1.5) * 1.5
        cx += turb_x
        cy += turb_y

        shoulder_y = cy - self.torso_h + 26.0 * self.scale
        hip_y = cy

        # 1. Torso & Uniform
        shirt_col = (255, 255, 255)
        pants_col = (15, 23, 42) # Dark navy pilot trousers

        torso_box = [(cx - self.torso_w // 2, shoulder_y - 12 * self.scale), (cx + self.torso_w // 2, hip_y)]
        draw.rounded_rectangle(torso_box, radius=int(20 * self.scale), fill=shirt_col, outline=(15, 23, 42), width=int(5 * self.scale))

        # Tie (Black pilot tie)
        if role in ["captain", "first_officer"]:
            tie_top_y = shoulder_y - 6 * self.scale
            draw.polygon([
                (cx - 7 * self.scale, tie_top_y),
                (cx + 7 * self.scale, tie_top_y),
                (cx + 9 * self.scale, tie_top_y + 65 * self.scale),
                (cx, tie_top_y + 85 * self.scale),
                (cx - 9 * self.scale, tie_top_y + 65 * self.scale)
            ], fill=(15, 23, 42))

            # Gold Epaulettes (Stripes on shoulders)
            stripe_count = 4 if role == "captain" else 3
            for ep_x in [cx - self.torso_w // 2 + 8 * self.scale, cx + self.torso_w // 2 - 20 * self.scale]:
                draw.rounded_rectangle([(ep_x, shoulder_y - 14 * self.scale), (ep_x + 14 * self.scale, shoulder_y + 6 * self.scale)], radius=3, fill=(15, 23, 42))
                for s_idx in range(stripe_count):
                    sy = shoulder_y - 11 * self.scale + s_idx * 5 * self.scale
                    draw.line([(ep_x + 2, sy), (ep_x + 12 * self.scale, sy)], fill=(234, 179, 8), width=int(2.5 * self.scale))

        elif role == "investigator":
            # Fluorescent orange safety vest with silver reflective stripes
            vest_box = [(cx - self.torso_w // 2 + 2, shoulder_y - 10 * self.scale), (cx + self.torso_w // 2 - 2, hip_y - 5)]
            draw.rounded_rectangle(vest_box, radius=int(18 * self.scale), fill=(249, 115, 22), outline=(15, 23, 42), width=int(4 * self.scale))
            # Silver stripes
            draw.line([(cx - self.torso_w // 2 + 6, shoulder_y + 25 * self.scale), (cx + self.torso_w // 2 - 6, shoulder_y + 25 * self.scale)], fill=(226, 232, 240), width=int(8 * self.scale))
            draw.line([(cx - self.torso_w // 2 + 6, shoulder_y + 55 * self.scale), (cx + self.torso_w // 2 - 6, shoulder_y + 55 * self.scale)], fill=(226, 232, 240), width=int(8 * self.scale))

        elif role == "atc":
            # Security badge lanyard around neck
            draw.line([(cx - 15 * self.scale, shoulder_y - 5 * self.scale), (cx, shoulder_y + 40 * self.scale)], fill=(59, 130, 246), width=int(4 * self.scale))
            draw.line([(cx + 15 * self.scale, shoulder_y - 5 * self.scale), (cx, shoulder_y + 40 * self.scale)], fill=(59, 130, 246), width=int(4 * self.scale))
            # Plastic badge
            draw.rounded_rectangle([(cx - 10 * self.scale, shoulder_y + 40 * self.scale), (cx + 10 * self.scale, shoulder_y + 62 * self.scale)], radius=3, fill=(255, 255, 255), outline=(15, 23, 42), width=2)

        # 2. Head & Facial Expressions
        head_cy = shoulder_y - self.head_r + 14 * self.scale
        head_box = [(cx - self.head_r, head_cy - self.head_r), (cx + self.head_r, head_cy + self.head_r)]
        draw.ellipse(head_box, fill=(255, 255, 255), outline=(15, 23, 42), width=int(5 * self.scale))

        # Pilot Peaked Hat (Captain)
        if role == "captain":
            cap_y = head_cy - self.head_r + 15 * self.scale
            # Hat crown
            draw.polygon([
                (cx - self.head_r - 6 * self.scale, cap_y + 5 * self.scale),
                (cx - self.head_r + 10 * self.scale, cap_y - 32 * self.scale),
                (cx + self.head_r - 10 * self.scale, cap_y - 32 * self.scale),
                (cx + self.head_r + 6 * self.scale, cap_y + 5 * self.scale)
            ], fill=(15, 23, 42), outline=(15, 23, 42))
            # Gold hat braid / band
            draw.rounded_rectangle([(cx - self.head_r - 2 * self.scale, cap_y - 2 * self.scale), (cx + self.head_r + 2 * self.scale, cap_y + 8 * self.scale)], radius=3, fill=(234, 179, 8))
            # Visor with gold laurel leaves
            draw.arc([(cx - self.head_r - 8 * self.scale, cap_y - 12 * self.scale), (cx + self.head_r + 8 * self.scale, cap_y + 24 * self.scale)], 0, 180, fill=(15, 23, 42), width=int(9 * self.scale))

        elif role in ["first_officer", "atc"]:
            # Aviation Headset
            hs_r = self.head_r + 4 * self.scale
            # Headband over head
            draw.arc([(cx - hs_r, head_cy - hs_r - 8 * self.scale), (cx + hs_r, head_cy + hs_r - 15 * self.scale)], 180, 360, fill=(15, 23, 42), width=int(8 * self.scale))
            # Ear cups
            draw.rounded_rectangle([(cx - self.head_r - 14 * self.scale, head_cy - 16 * self.scale), (cx - self.head_r + 4 * self.scale, head_cy + 22 * self.scale)], radius=8, fill=(30, 41, 59), outline=(15, 23, 42), width=3)
            draw.rounded_rectangle([(cx + self.head_r - 4 * self.scale, head_cy - 16 * self.scale), (cx + self.head_r + 14 * self.scale, head_cy + 22 * self.scale)], radius=8, fill=(30, 41, 59), outline=(15, 23, 42), width=3)
            # Boom mic to mouth
            draw.arc([(cx - 8 * self.scale, head_cy), (cx + self.head_r + 2 * self.scale, head_cy + 34 * self.scale)], 45, 160, fill=(15, 23, 42), width=int(5 * self.scale))
            draw.ellipse([(cx + 6 * self.scale, head_cy + 20 * self.scale), (cx + 20 * self.scale, head_cy + 32 * self.scale)], fill=(15, 23, 42))

        # Eyes & Mouth based on Action
        eye_y = head_cy + 2 * self.scale
        if action == "panic" or role == "first_officer":
            # Panicked wide white eyes with small trembling pupils
            eye_off_x = math.sin(t * 30.0) * 1.5
            draw.ellipse([(cx - 24 * self.scale, eye_y - 14 * self.scale), (cx - 4 * self.scale, eye_y + 10 * self.scale)], fill=(255, 255, 255), outline=(15, 23, 42), width=3)
            draw.ellipse([(cx + 4 * self.scale, eye_y - 14 * self.scale), (cx + 24 * self.scale, eye_y + 10 * self.scale)], fill=(255, 255, 255), outline=(15, 23, 42), width=3)
            draw.ellipse([(cx - 16 * self.scale + eye_off_x, eye_y - 5 * self.scale), (cx - 10 * self.scale + eye_off_x, eye_y + 1 * self.scale)], fill=(15, 23, 42))
            draw.ellipse([(cx + 10 * self.scale + eye_off_x, eye_y - 5 * self.scale), (cx + 16 * self.scale + eye_off_x, eye_y + 1 * self.scale)], fill=(15, 23, 42))
            # Worried slanted eyebrows
            draw.line([(cx - 26 * self.scale, eye_y - 20 * self.scale), (cx - 6 * self.scale, eye_y - 28 * self.scale)], fill=(15, 23, 42), width=int(4 * self.scale))
            draw.line([(cx + 6 * self.scale, eye_y - 28 * self.scale), (cx + 26 * self.scale, eye_y - 20 * self.scale)], fill=(15, 23, 42), width=int(4 * self.scale))
            # Open oval scream
            draw.ellipse([(cx - 14 * self.scale, eye_y + 18 * self.scale), (cx + 14 * self.scale, eye_y + 36 * self.scale)], fill=(15, 23, 42))
            # Flying sweat droplets
            sw_y = head_cy - 10 * self.scale
            draw.ellipse([(cx + self.head_r + 6 * self.scale, sw_y), (cx + self.head_r + 18 * self.scale, sw_y + 14 * self.scale)], fill=(56, 189, 248))
        else:
            # Focused / calm pilot or controller eyes
            draw.ellipse([(cx - 20 * self.scale, eye_y - 6 * self.scale), (cx - 8 * self.scale, eye_y + 6 * self.scale)], fill=(15, 23, 42))
            draw.ellipse([(cx + 8 * self.scale, eye_y - 6 * self.scale), (cx + 20 * self.scale, eye_y + 6 * self.scale)], fill=(15, 23, 42))
            # Intense furrowed brow
            draw.line([(cx - 22 * self.scale, eye_y - 14 * self.scale), (cx - 6 * self.scale, eye_y - 12 * self.scale)], fill=(15, 23, 42), width=int(4 * self.scale))
            draw.line([(cx + 6 * self.scale, eye_y - 12 * self.scale), (cx + 22 * self.scale, eye_y - 14 * self.scale)], fill=(15, 23, 42), width=int(4 * self.scale))
            # Determined firm mouth
            draw.line([(cx - 12 * self.scale, eye_y + 24 * self.scale), (cx + 12 * self.scale, eye_y + 24 * self.scale)], fill=(15, 23, 42), width=int(4 * self.scale))

        # 3. Arms & Hands Animation
        sh_l = (cx - self.torso_w // 2 + 4 * self.scale, shoulder_y + 8 * self.scale)
        sh_r = (cx + self.torso_w // 2 - 4 * self.scale, shoulder_y + 8 * self.scale)

        if action == "fly":
            # Hands firmly on airplane flight control yoke
            # Calculate yoke center and rotation
            yoke_cx = cx
            yoke_cy = cy - 25.0 * self.scale
            y_angle = yoke_turn

            w_l = (yoke_cx - 42.0 * self.scale * math.cos(math.radians(y_angle)), yoke_cy - 42.0 * self.scale * math.sin(math.radians(y_angle)))
            w_r = (yoke_cx + 42.0 * self.scale * math.cos(math.radians(y_angle)), yoke_cy + 42.0 * self.scale * math.sin(math.radians(y_angle)))

            el_l = solve_ik(sh_l, w_l, self.upper_arm, self.forearm, bend_positive=False)
            el_r = solve_ik(sh_r, w_r, self.upper_arm, self.forearm, bend_positive=True)

            # Draw left arm
            draw.line([sh_l, el_l], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([el_l, w_l], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([sh_l, el_l], fill=shirt_col, width=int(6 * self.scale))
            draw.line([el_l, w_l], fill=shirt_col, width=int(6 * self.scale))
            self.draw_hand(draw, w_l, gesture="yoke_grip", facing_right=True)

            # Draw right arm
            draw.line([sh_r, el_r], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([el_r, w_r], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([sh_r, el_r], fill=shirt_col, width=int(6 * self.scale))
            draw.line([el_r, w_r], fill=shirt_col, width=int(6 * self.scale))
            self.draw_hand(draw, w_r, gesture="yoke_grip", facing_right=False)

            # Draw Boeing 737 / Airliner Control Yoke
            draw.line([(yoke_cx, yoke_cy + 75 * self.scale), (yoke_cx, yoke_cy)], fill=(51, 65, 85), width=int(14 * self.scale))
            # W-shaped yoke handles
            draw.line([w_l, (yoke_cx, yoke_cy + 12 * self.scale)], fill=(15, 23, 42), width=int(12 * self.scale))
            draw.line([(yoke_cx, yoke_cy + 12 * self.scale), w_r], fill=(15, 23, 42), width=int(12 * self.scale))
            draw.line([(w_l[0], w_l[1] - 18 * self.scale), (w_l[0], w_l[1] + 18 * self.scale)], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([(w_r[0], w_r[1] - 18 * self.scale), (w_r[0], w_r[1] + 18 * self.scale)], fill=(15, 23, 42), width=int(14 * self.scale))

        elif action == "point_warning":
            # Left hand gripping yoke, Right arm urgently pointing at instrument / warning light
            w_l = (cx - 38.0 * self.scale, cy - 20.0 * self.scale)
            el_l = solve_ik(sh_l, w_l, self.upper_arm, self.forearm, bend_positive=False)
            draw.line([sh_l, el_l], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([el_l, w_l], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([sh_l, el_l], fill=shirt_col, width=int(6 * self.scale))
            draw.line([el_l, w_l], fill=shirt_col, width=int(6 * self.scale))
            self.draw_hand(draw, w_l, gesture="yoke_grip", facing_right=True)

            # Right arm points up and forward
            point_target_x = cx + 110.0 * self.scale
            point_target_y = cy - 95.0 * self.scale
            el_r = solve_ik(sh_r, (point_target_x, point_target_y), self.upper_arm, self.forearm, bend_positive=False)
            draw.line([sh_r, el_r], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([el_r, (point_target_x, point_target_y)], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([sh_r, el_r], fill=shirt_col, width=int(6 * self.scale))
            draw.line([el_r, (point_target_x, point_target_y)], fill=shirt_col, width=int(6 * self.scale))
            self.draw_hand(draw, (point_target_x, point_target_y), gesture="point", facing_right=True)

        elif action == "talk_mic":
            # ATC Controller: Right hand brings handheld radio mic right to mouth
            mic_x = cx + 22.0 * self.scale
            mic_y = head_cy + 24.0 * self.scale
            el_r = solve_ik(sh_r, (mic_x, mic_y), self.upper_arm, self.forearm, bend_positive=True)
            draw.line([sh_r, el_r], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([el_r, (mic_x, mic_y)], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([sh_r, el_r], fill=shirt_col, width=int(6 * self.scale))
            draw.line([el_r, (mic_x, mic_y)], fill=shirt_col, width=int(6 * self.scale))
            # Hand gripping mic with coiled cord down to desk
            self.draw_hand(draw, (mic_x, mic_y), gesture="mic_hold", facing_right=False)
            # Radio cord
            draw.arc([(cx + 10 * self.scale, mic_y + 10 * self.scale), (cx + 50 * self.scale, cy + 30 * self.scale)], 0, 180, fill=(15, 23, 42), width=3)

            # Left hand resting on radar console
            w_l = (cx - 45.0 * self.scale, cy + 10.0 * self.scale)
            el_l = solve_ik(sh_l, w_l, self.upper_arm, self.forearm, bend_positive=False)
            draw.line([sh_l, el_l], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([el_l, w_l], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([sh_l, el_l], fill=shirt_col, width=int(6 * self.scale))
            draw.line([el_l, w_l], fill=shirt_col, width=int(6 * self.scale))
            self.draw_hand(draw, w_l, gesture="relaxed", facing_right=True)

    def draw_travel_walking_rig(
        self,
        canvas: Image.Image,
        pos_x: float,
        ground_y: float,
        walk_phase: float,
        facing_right: bool = True,
        is_walking: bool = True,
        action: str = "walk", # 'walk', 'point', 'coffee', 'phone'
        emotion: str = "happy",
        t: float = 0.0,
    ):
        """
        True articulated walking rig with continuous ankle rotation / foot roll and elbow swings.
        """
        draw = ImageDraw.Draw(canvas)
        cx = pos_x
        dir_m = 1.0 if facing_right else -1.0

        # Kinematics & Recoil
        if is_walking:
            # Hip bobbing: drops lowest at contact, peaks at passing
            hip_bounce = math.cos(walk_phase * 4.0 * math.pi) * (11.0 * self.scale)
            torso_tilt = 4.0 if facing_right else -4.0
        else:
            hip_bounce = math.sin(t * 1.5 * math.pi * 2.0) * (3.5 * self.scale)
            torso_tilt = 0.0

        hip_x = cx
        hip_y = ground_y - (self.thigh_len + self.shin_len - 10.0 * self.scale) + hip_bounce

        # Stride & Foot trajectories with true ankle rotation
        stride_dist = 68.0 * self.scale
        step_lift = 42.0 * self.scale

        # Leg 1 (Front)
        p1 = walk_phase % 1.0
        if is_walking:
            if p1 < 0.5: # Stance: foot rolls on ground
                f1_x = hip_x + (stride_dist - (p1 / 0.5) * 2.0 * stride_dist) * dir_m
                f1_y = ground_y
                # Ankle roll: heel strikes at -22 deg, rolls to 0 deg, pushes off at +40 deg
                if p1 < 0.15:
                    f1_rot = -24.0 * (1.0 - p1 / 0.15)
                elif p1 > 0.35:
                    f1_rot = 42.0 * ((p1 - 0.35) / 0.15)
                else:
                    f1_rot = 0.0
            else: # Swing: foot lifts and reaches forward
                sw = (p1 - 0.5) / 0.5
                f1_x = hip_x + (-stride_dist + sw * 2.0 * stride_dist) * dir_m
                f1_y = ground_y - math.sin(sw * math.pi) * step_lift
                f1_rot = 15.0 * (1.0 - sw) - 15.0 * sw
        else:
            f1_x = hip_x + 18.0 * self.scale * dir_m
            f1_y = ground_y
            f1_rot = 0.0

        # Leg 2 (Back, 180 deg offset)
        p2 = (walk_phase + 0.5) % 1.0
        if is_walking:
            if p2 < 0.5:
                f2_x = hip_x + (stride_dist - (p2 / 0.5) * 2.0 * stride_dist) * dir_m
                f2_y = ground_y
                if p2 < 0.15:
                    f2_rot = -24.0 * (1.0 - p2 / 0.15)
                elif p2 > 0.35:
                    f2_rot = 42.0 * ((p2 - 0.35) / 0.15)
                else:
                    f2_rot = 0.0
            else:
                sw = (p2 - 0.5) / 0.5
                f2_x = hip_x + (-stride_dist + sw * 2.0 * stride_dist) * dir_m
                f2_y = ground_y - math.sin(sw * math.pi) * step_lift
                f2_rot = 15.0 * (1.0 - sw) - 15.0 * sw
        else:
            f2_x = hip_x - 18.0 * self.scale * dir_m
            f2_y = ground_y
            f2_rot = 0.0

        # Solve Knee IK
        hip_off = 12.0 * self.scale
        k1 = solve_ik((hip_x - hip_off * dir_m, hip_y), (f1_x, f1_y), self.thigh_len, self.shin_len, bend_positive=facing_right)
        k2 = solve_ik((hip_x + hip_off * dir_m, hip_y), (f2_x, f2_y), self.thigh_len, self.shin_len, bend_positive=facing_right)

        # 1. Soft Shadow
        sw_w = int(140.0 * self.scale)
        sw_h = int(22.0 * self.scale)
        draw.ellipse([(hip_x - sw_w // 2, ground_y - 6), (hip_x + sw_w // 2, ground_y + sw_h - 6)], fill=(0, 0, 0, 75))

        # 2. Back Leg & Shoe (Leg 2)
        h2 = (hip_x + hip_off * dir_m, hip_y)
        draw.line([h2, k2], fill=(15, 23, 42), width=int(14 * self.scale))
        draw.line([k2, (f2_x, f2_y)], fill=(15, 23, 42), width=int(14 * self.scale))
        draw.line([h2, k2], fill=(235, 235, 235), width=int(6 * self.scale))
        draw.line([k2, (f2_x, f2_y)], fill=(235, 235, 235), width=int(6 * self.scale))
        self.draw_foot(draw, (f2_x, f2_y), f2_rot, facing_right=facing_right)

        # 3. Torso (Orange T-shirt or Gray Sweater)
        torso_top = hip_y - self.torso_h
        torso_box = [(hip_x - self.torso_w // 2, torso_top), (hip_x + self.torso_w // 2, hip_y)]
        draw.rounded_rectangle(torso_box, radius=int(22 * self.scale), fill=(249, 115, 22), outline=(15, 23, 42), width=int(5 * self.scale))

        # Khaki Shorts
        shorts_h = 32.0 * self.scale
        draw.polygon([
            (hip_x - self.torso_w // 2 + 2, hip_y - 12 * self.scale),
            (hip_x + self.torso_w // 2 - 2, hip_y - 12 * self.scale),
            (hip_x + self.torso_w // 2 + 3, hip_y + shorts_h),
            (hip_x - self.torso_w // 2 - 3, hip_y + shorts_h),
        ], fill=(214, 180, 142))
        draw.line([(hip_x - self.torso_w // 2 + 2, hip_y - 12 * self.scale), (hip_x - self.torso_w // 2 - 3, hip_y + shorts_h)], fill=(15, 23, 42), width=int(4 * self.scale))
        draw.line([(hip_x + self.torso_w // 2 - 2, hip_y - 12 * self.scale), (hip_x + self.torso_w // 2 + 3, hip_y + shorts_h)], fill=(15, 23, 42), width=int(4 * self.scale))
        draw.line([(hip_x - self.torso_w // 2 - 3, hip_y + shorts_h), (hip_x + self.torso_w // 2 + 3, hip_y + shorts_h)], fill=(15, 23, 42), width=int(4 * self.scale))

        # 4. Front Leg & Shoe (Leg 1)
        h1 = (hip_x - hip_off * dir_m, hip_y)
        draw.line([h1, k1], fill=(15, 23, 42), width=int(16 * self.scale))
        draw.line([k1, (f1_x, f1_y)], fill=(15, 23, 42), width=int(16 * self.scale))
        draw.line([h1, k1], fill=(255, 255, 255), width=int(7 * self.scale))
        draw.line([k1, (f1_x, f1_y)], fill=(255, 255, 255), width=int(7 * self.scale))
        self.draw_foot(draw, (f1_x, f1_y), f1_rot, facing_right=facing_right)

        # 5. Head & Face
        head_cy = torso_top - self.head_r + 14 * self.scale
        head_box = [(hip_x - self.head_r, head_cy - self.head_r), (hip_x + self.head_r, head_cy + self.head_r)]
        draw.ellipse(head_box, fill=(255, 255, 255), outline=(15, 23, 42), width=int(5 * self.scale))

        # Styled Hair
        draw.polygon([
            (hip_x - 42 * self.scale * dir_m, head_cy - 18 * self.scale),
            (hip_x - 35 * self.scale * dir_m, head_cy - 48 * self.scale),
            (hip_x - 10 * self.scale * dir_m, head_cy - 56 * self.scale),
            (hip_x + 25 * self.scale * dir_m, head_cy - 52 * self.scale),
            (hip_x + 44 * self.scale * dir_m, head_cy - 24 * self.scale),
            (hip_x + 22 * self.scale * dir_m, head_cy - 36 * self.scale),
            (hip_x - 15 * self.scale * dir_m, head_cy - 40 * self.scale),
        ], fill=(15, 23, 42))

        # Eye & Smile
        eye_x = hip_x + (18 * self.scale if facing_right else -18 * self.scale)
        eye_y = head_cy - 2 * self.scale
        draw.ellipse([(eye_x - 6 * self.scale, eye_y - 6 * self.scale), (eye_x + 6 * self.scale, eye_y + 6 * self.scale)], fill=(15, 23, 42))
        draw.arc([(eye_x - 14 * self.scale, eye_y + 4 * self.scale), (eye_x + 14 * self.scale, eye_y + 22 * self.scale)], 10, 170, fill=(15, 23, 42), width=int(3 * self.scale))

        # 6. Arms & Hands
        sh_pt = (hip_x - 6.0 * self.scale * dir_m, torso_top + 28.0 * self.scale)

        if action == "walk":
            # Natural arm swing
            arm_swing = math.sin(walk_phase * 2.0 * math.pi) * (44.0 * self.scale)
            wr_x = hip_x - arm_swing * dir_m
            wr_y = hip_y - 20.0 * self.scale
            el_pt = solve_ik(sh_pt, (wr_x, wr_y), self.upper_arm, self.forearm, bend_positive=not facing_right)
            draw.line([sh_pt, el_pt], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([el_pt, (wr_x, wr_y)], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([sh_pt, el_pt], fill=(255, 255, 255), width=int(6 * self.scale))
            draw.line([el_pt, (wr_x, wr_y)], fill=(255, 255, 255), width=int(6 * self.scale))
            self.draw_hand(draw, (wr_x, wr_y), gesture="relaxed", facing_right=facing_right)

        elif action == "coffee":
            # Hand brings takeaway coffee cup to mouth
            cup_x = eye_x + 10.0 * self.scale * dir_m
            cup_y = eye_y + 16.0 * self.scale
            el_pt = solve_ik(sh_pt, (cup_x, cup_y), self.upper_arm, self.forearm, bend_positive=True)
            draw.line([sh_pt, el_pt], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([el_pt, (cup_x, cup_y)], fill=(15, 23, 42), width=int(14 * self.scale))
            draw.line([sh_pt, el_pt], fill=(255, 255, 255), width=int(6 * self.scale))
            draw.line([el_pt, (cup_x, cup_y)], fill=(255, 255, 255), width=int(6 * self.scale))
            # Coffee cup
            draw.polygon([
                (cup_x - 10 * self.scale, cup_y - 12 * self.scale),
                (cup_x + 10 * self.scale, cup_y - 12 * self.scale),
                (cup_x + 7 * self.scale, cup_y + 14 * self.scale),
                (cup_x - 7 * self.scale, cup_y + 14 * self.scale),
            ], fill=(245, 245, 245), outline=(15, 23, 42))
            draw.rounded_rectangle([(cup_x - 9 * self.scale, cup_y - 4 * self.scale), (cup_x + 9 * self.scale, cup_y + 6 * self.scale)], radius=2, fill=(180, 130, 90))
            self.draw_hand(draw, (cup_x, cup_y), gesture="relaxed", facing_right=facing_right)
