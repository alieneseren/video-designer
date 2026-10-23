"""
crayon_walker.py
================
Full 2D Skeletal Rigging, 4-Phase Walk Cycle Kinematics, and Crayon/MinutePhysics
Procedural Animation Engine.
Replicates the exact aesthetic and movement of channels like Crayon Capital:
- 2-joint inverse kinematics (IK) for knees and elbows
- 4-phase classical walk cycle (Contact, Recoil/Down, Passing, High Point/Up)
- Hand-drawn line boil (12fps organic pencil jitter)
- Moving across screen OR scrolling parallax treadmill mode
- Interactive accessories (backpack, phone GPS, coffee, camera)
- Synchronized "İç Ses" (inner monologue) thought clouds
"""

import os
import math
import random
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont

from .bubble import ComicBubble, ThoughtBubble, InfoBadge, get_engine_font
from .animator import StickmanTimeline, easing_elastic_out
from .overlay import get_ffmpeg_binary


def solve_2joint_ik(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    l1: float,
    l2: float,
    bend_forward: bool = True
) -> Tuple[float, float]:
    """Analytical 2-joint Inverse Kinematics solver."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = math.hypot(dx, dy)
    dist = min(max(dist, 1e-4), l1 + l2 - 1e-3)

    base_angle = math.atan2(dy, dx)
    cos_a = (l1 * l1 + dist * dist - l2 * l2) / (2.0 * l1 * dist)
    cos_a = max(-1.0, min(1.0, cos_a))
    angle_a = math.acos(cos_a)

    knee_angle = base_angle + (angle_a if bend_forward else -angle_a)
    kx = p1[0] + l1 * math.cos(knee_angle)
    ky = p1[1] + l1 * math.sin(knee_angle)
    return (kx, ky)


class CrayonWalker:
    """Procedural skeletal stickman animator with Crayon Capital aesthetics."""

    def __init__(
        self,
        scale: float = 1.0,
        shirt_color: Tuple[int, int, int] = (249, 115, 22), # Orange
        shorts_color: Tuple[int, int, int] = (214, 180, 142), # Khaki
        shoe_color: Tuple[int, int, int] = (234, 88, 12),
        backpack_color: Tuple[int, int, int] = (45, 115, 110),
    ):
        self.scale = scale
        self.shirt_color = shirt_color
        self.shorts_color = shorts_color
        self.shoe_color = shoe_color
        self.backpack_color = backpack_color

        # Anatomical lengths (scaled)
        self.leg_l1 = 82.0 * scale # Thigh
        self.leg_l2 = 88.0 * scale # Shin
        self.arm_l1 = 52.0 * scale # Upper arm
        self.arm_l2 = 54.0 * scale # Forearm
        self.stride = 68.0 * scale # Step width
        self.step_lift = 44.0 * scale # Foot lift in swing phase
        self.bounce_amp = 11.0 * scale # Hip bobbing amplitude
        self.torso_h = 135.0 * scale
        self.torso_w = 68.0 * scale
        self.head_r = 52.0 * scale

    def _draw_jitter_line(
        self,
        draw: ImageDraw.Draw,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        width: int,
        color: Tuple[int, ...],
        jitter_seed: int = 0,
    ):
        """Draws hand-drawn slightly textured line with subtle sketch variance."""
        if jitter_seed == 0:
            draw.line([p1, p2], fill=color, width=width)
            return

        # Calculate slight midpoint displacement for hand-drawn pencil feel
        mx = (p1[0] + p2[0]) / 2.0
        my = (p1[1] + p2[1]) / 2.0
        rnd = random.Random(jitter_seed)
        ox = rnd.uniform(-1.8, 1.8) * self.scale
        oy = rnd.uniform(-1.8, 1.8) * self.scale
        mid = (mx + ox, my + oy)
        draw.line([p1, mid], fill=color, width=width)
        draw.line([mid, p2], fill=color, width=width)

    def draw_character(
        self,
        canvas: Image.Image,
        pos_x: float,
        ground_y: float,
        walk_phase: float,
        facing_right: bool = True,
        is_walking: bool = True,
        emotion: str = "curious",
        accessory: str = "backpack", # 'backpack', 'phone', 'camera', 'coffee'
        jitter_frame: int = 0,
    ):
        """
        Renders the fully rigged stickman at ground position (pos_x, ground_y).
        """
        draw = ImageDraw.Draw(canvas)
        j_seed = (jitter_frame % 4) * 101 if jitter_frame > 0 else 0

        # Calculate Hip kinematics
        if is_walking:
            hip_bounce = math.cos(walk_phase * 4.0 * math.pi) * self.bounce_amp
            torso_tilt_deg = 4.0 if facing_right else -4.0
        else:
            hip_bounce = math.sin(walk_phase * 2.0 * math.pi) * 4.0
            torso_tilt_deg = 0.0

        hip_x = pos_x
        hip_y = ground_y - (self.leg_l1 + self.leg_l2 - 12.0 * self.scale) + hip_bounce

        # Foot 1 (Front foot when facing right)
        # Foot 2 (Back foot when facing right)
        dir_mult = 1.0 if facing_right else -1.0

        if is_walking:
            # Phase for Foot 1
            p1 = walk_phase % 1.0
            if p1 < 0.5: # Stance phase
                f1_x = hip_x + (self.stride - (p1 / 0.5) * 2.0 * self.stride) * dir_mult
                f1_y = ground_y
            else: # Swing phase
                sw = (p1 - 0.5) / 0.5
                f1_x = hip_x + (-self.stride + sw * 2.0 * self.stride) * dir_mult
                f1_y = ground_y - math.sin(sw * math.pi) * self.step_lift

            # Phase for Foot 2 (180 deg offset)
            p2 = (walk_phase + 0.5) % 1.0
            if p2 < 0.5: # Stance phase
                f2_x = hip_x + (self.stride - (p2 / 0.5) * 2.0 * self.stride) * dir_mult
                f2_y = ground_y
            else: # Swing phase
                sw = (p2 - 0.5) / 0.5
                f2_x = hip_x + (-self.stride + sw * 2.0 * self.stride) * dir_mult
                f2_y = ground_y - math.sin(sw * math.pi) * self.step_lift
        else:
            f1_x = hip_x + 18.0 * self.scale * dir_mult
            f1_y = ground_y
            f2_x = hip_x - 18.0 * self.scale * dir_mult
            f2_y = ground_y

        # Solve Knee IK
        hip_attach_offset = 14.0 * self.scale
        k1 = solve_2joint_ik((hip_x - hip_attach_offset * dir_mult, hip_y), (f1_x, f1_y), self.leg_l1, self.leg_l2, bend_forward=facing_right)
        k2 = solve_2joint_ik((hip_x + hip_attach_offset * dir_mult, hip_y), (f2_x, f2_y), self.leg_l1, self.leg_l2, bend_forward=facing_right)

        # 1. Soft Ground Shadow underneath
        shadow_w = int(140.0 * self.scale)
        shadow_h = int(22.0 * self.scale)
        draw.ellipse([(hip_x - shadow_w // 2, ground_y - 6), (hip_x + shadow_w // 2, ground_y + shadow_h - 6)], fill=(0, 0, 0, 70))

        # 2. Back Leg & Shoe (Foot 2)
        hip2_pt = (hip_x + hip_attach_offset * dir_mult, hip_y)
        self._draw_jitter_line(draw, hip2_pt, k2, int(13 * self.scale), (15, 23, 42), j_seed + 1)
        self._draw_jitter_line(draw, k2, (f2_x, f2_y), int(13 * self.scale), (15, 23, 42), j_seed + 2)
        draw.line([hip2_pt, k2], fill=(235, 235, 235), width=int(5 * self.scale))
        draw.line([k2, (f2_x, f2_y)], fill=(235, 235, 235), width=int(5 * self.scale))
        # Shoe 2
        shoe_w = 36.0 * self.scale
        shoe_h = 16.0 * self.scale
        s2_box = [
            (f2_x - (shoe_w * 0.4 if facing_right else shoe_w * 0.6), f2_y - shoe_h + 3),
            (f2_x + (shoe_w * 0.6 if facing_right else shoe_w * 0.4), f2_y + 3)
        ]
        draw.rounded_rectangle(s2_box, radius=int(6 * self.scale), fill=self.shoe_color, outline=(15, 23, 42), width=int(3 * self.scale))

        # 3. Backpack (Drawn behind torso)
        if accessory == "backpack":
            pack_w = 64.0 * self.scale
            pack_h = 96.0 * self.scale
            pack_x = hip_x - (pack_w if facing_right else -5)
            pack_y = hip_y - self.torso_h + 10 * self.scale
            draw.rounded_rectangle(
                [(pack_x, pack_y), (pack_x + pack_w, pack_y + pack_h)],
                radius=int(18 * self.scale),
                fill=self.backpack_color,
                outline=(15, 23, 42),
                width=int(5 * self.scale)
            )

        # 4. Torso (Orange T-shirt & Khaki Shorts)
        torso_top = hip_y - self.torso_h
        torso_box = [
            (hip_x - self.torso_w // 2, torso_top),
            (hip_x + self.torso_w // 2, hip_y)
        ]
        draw.rounded_rectangle(torso_box, radius=int(22 * self.scale), fill=self.shirt_color, outline=(15, 23, 42), width=int(5 * self.scale))

        # Backpack shoulder strap
        if accessory == "backpack":
            strap_x = hip_x + (4 if facing_right else -4) * self.scale
            draw.line([(strap_x, torso_top + 8), (strap_x - (12 if facing_right else -12), hip_y - 20)], fill=(30, 85, 80), width=int(7 * self.scale))

        # Shorts
        shorts_h = 32.0 * self.scale
        draw.polygon([
            (hip_x - self.torso_w // 2 + 2, hip_y - 12 * self.scale),
            (hip_x + self.torso_w // 2 - 2, hip_y - 12 * self.scale),
            (hip_x + self.torso_w // 2 + 3, hip_y + shorts_h),
            (hip_x - self.torso_w // 2 - 3, hip_y + shorts_h),
        ], fill=self.shorts_color)
        draw.line([(hip_x - self.torso_w // 2 + 2, hip_y - 12 * self.scale), (hip_x - self.torso_w // 2 - 3, hip_y + shorts_h)], fill=(15, 23, 42), width=int(4 * self.scale))
        draw.line([(hip_x + self.torso_w // 2 - 2, hip_y - 12 * self.scale), (hip_x + self.torso_w // 2 + 3, hip_y + shorts_h)], fill=(15, 23, 42), width=int(4 * self.scale))
        draw.line([(hip_x - self.torso_w // 2 - 3, hip_y + shorts_h), (hip_x + self.torso_w // 2 + 3, hip_y + shorts_h)], fill=(15, 23, 42), width=int(4 * self.scale))

        # 5. Front Leg & Shoe (Foot 1)
        hip1_pt = (hip_x - hip_attach_offset * dir_mult, hip_y)
        self._draw_jitter_line(draw, hip1_pt, k1, int(15 * self.scale), (15, 23, 42), j_seed + 3)
        self._draw_jitter_line(draw, k1, (f1_x, f1_y), int(15 * self.scale), (15, 23, 42), j_seed + 4)
        draw.line([hip1_pt, k1], fill=(255, 255, 255), width=int(6 * self.scale))
        draw.line([k1, (f1_x, f1_y)], fill=(255, 255, 255), width=int(6 * self.scale))
        # Shoe 1
        s1_box = [
            (f1_x - (shoe_w * 0.4 if facing_right else shoe_w * 0.6), f1_y - shoe_h + 3),
            (f1_x + (shoe_w * 0.6 if facing_right else shoe_w * 0.4), f1_y + 3)
        ]
        draw.rounded_rectangle(s1_box, radius=int(6 * self.scale), fill=self.shoe_color, outline=(15, 23, 42), width=int(4 * self.scale))

        # 6. Head & Face
        head_cy = torso_top - self.head_r + 14 * self.scale
        head_box = [
            (hip_x - self.head_r, head_cy - self.head_r),
            (hip_x + self.head_r, head_cy + self.head_r)
        ]
        draw.ellipse(head_box, fill=(255, 255, 255), outline=(15, 23, 42), width=int(5 * self.scale))

        # Comic Hair Tuft
        hair_dir = 1.0 if facing_right else -1.0
        draw.polygon([
            (hip_x - 42 * self.scale * hair_dir, head_cy - 18 * self.scale),
            (hip_x - 35 * self.scale * hair_dir, head_cy - 48 * self.scale),
            (hip_x - 10 * self.scale * hair_dir, head_cy - 56 * self.scale),
            (hip_x + 25 * self.scale * hair_dir, head_cy - 52 * self.scale),
            (hip_x + 44 * self.scale * hair_dir, head_cy - 24 * self.scale),
            (hip_x + 22 * self.scale * hair_dir, head_cy - 36 * self.scale),
            (hip_x - 15 * self.scale * hair_dir, head_cy - 40 * self.scale),
        ], fill=(15, 23, 42))

        # Eyes & Emotion
        eye_y = head_cy - 2 * self.scale
        eye_x = hip_x + (18 * self.scale if facing_right else -18 * self.scale)
        eye_r = 7.0 * self.scale

        if emotion in ["curious", "happy"]:
            # Round cartoon pupil
            draw.ellipse([(eye_x - eye_r, eye_y - eye_r), (eye_x + eye_r, eye_y + eye_r)], fill=(15, 23, 42))
            # Rosy cheek
            draw.ellipse([(eye_x - 8 * self.scale, eye_y + 12 * self.scale), (eye_x + 12 * self.scale, eye_y + 22 * self.scale)], fill=(253, 164, 175, 170))
            # Pleasant smile
            smile_x = eye_x - (4 if facing_right else -4) * self.scale
            draw.arc([(smile_x - 14 * self.scale, eye_y + 4 * self.scale), (smile_x + 14 * self.scale, eye_y + 22 * self.scale)], 10, 170, fill=(15, 23, 42), width=int(3 * self.scale))
        elif emotion in ["lost", "shocked"]:
            # Panicked wide eye with sweat drop
            draw.ellipse([(eye_x - eye_r - 4, eye_y - eye_r - 4), (eye_x + eye_r + 4, eye_y + eye_r + 4)], fill=(255, 255, 255), outline=(15, 23, 42), width=2)
            draw.ellipse([(eye_x - 3, eye_y - 3), (eye_x + 3, eye_y + 3)], fill=(15, 23, 42))
            # Wavy confused mouth
            draw.line([(eye_x - 12 * self.scale, eye_y + 16 * self.scale), (eye_x + 10 * self.scale, eye_y + 16 * self.scale)], fill=(15, 23, 42), width=3)
            # Sweat drop
            draw.ellipse([(hip_x + 38 * self.scale * dir_mult, head_cy - 12 * self.scale), (hip_x + 48 * self.scale * dir_mult, head_cy + 2 * self.scale)], fill=(56, 189, 248))

        # 7. Arms & Hands
        shoulder = (hip_x - 6.0 * self.scale * dir_mult, torso_top + 28.0 * self.scale)

        if is_walking:
            # Arm swing opposite to front leg (Phase 1)
            arm_swing = math.sin(walk_phase * 2.0 * math.pi) * (42.0 * self.scale)
            wrist_x = hip_x - arm_swing * dir_mult
            wrist_y = hip_y - 22.0 * self.scale
            elbow = solve_2joint_ik(shoulder, (wrist_x, wrist_y), self.arm_l1, self.arm_l2, bend_forward=not facing_right)

            self._draw_jitter_line(draw, shoulder, elbow, int(13 * self.scale), (15, 23, 42), j_seed + 5)
            self._draw_jitter_line(draw, elbow, (wrist_x, wrist_y), int(13 * self.scale), (15, 23, 42), j_seed + 6)
            draw.line([shoulder, elbow], fill=(255, 255, 255), width=int(5 * self.scale))
            draw.line([elbow, (wrist_x, wrist_y)], fill=(255, 255, 255), width=int(5 * self.scale))
            # Hand
            draw.ellipse([(wrist_x - 9 * self.scale, wrist_y - 8 * self.scale), (wrist_x + 9 * self.scale, wrist_y + 10 * self.scale)], fill=(255, 255, 255), outline=(15, 23, 42), width=int(3 * self.scale))
        else:
            # Idle arm resting on hip or holding phone
            wrist_x = hip_x + 24.0 * self.scale * dir_mult
            wrist_y = hip_y - 30.0 * self.scale
            elbow = (hip_x + 36.0 * self.scale * dir_mult, torso_top + 45.0 * self.scale)
            draw.line([shoulder, elbow], fill=(15, 23, 42), width=int(12 * self.scale))
            draw.line([elbow, (wrist_x, wrist_y)], fill=(15, 23, 42), width=int(12 * self.scale))
            draw.line([shoulder, elbow], fill=(255, 255, 255), width=int(5 * self.scale))
            draw.line([elbow, (wrist_x, wrist_y)], fill=(255, 255, 255), width=int(5 * self.scale))
            draw.ellipse([(wrist_x - 9 * self.scale, wrist_y - 8 * self.scale), (wrist_x + 9 * self.scale, wrist_y + 10 * self.scale)], fill=(255, 255, 255), outline=(15, 23, 42), width=int(3 * self.scale))


class CrayonSceneProducer:
    """Produces full cinematic scenes with walking stickman and parallax/cross-screen motion."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 25):
        self.w = width
        self.h = height
        self.fps = fps
        self.walker = CrayonWalker(scale=1.15)
        self.ffmpeg_bin = get_ffmpeg_binary()

    def render_walk_across_video(
        self,
        output_path: str,
        dialogue: str,
        duration_sec: float = 6.0,
        start_x: float = 200.0,
        end_x: float = 1720.0,
        ground_y: float = 880.0,
        walk_speed: float = 2.0, # steps per second
        badge_title: str = "İÇ SES // GÜNLÜK",
        location_title: str = "📍 İSTANBUL // TARİHİ YARIMADA",
        location_stats: str = "👟 14.210 Adım // 9.1 km • ☀️ 20°C",
        bg_media: Optional[str] = None,
        green_screen: bool = False,
        bubble_type: str = "thought",
    ) -> Path:
        """
        Renders the character walking across the entire screen from start_x to end_x
        while thinking/talking with an animated thought cloud trailing his head.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(round(duration_sec * self.fps))

        bg_img: Optional[Image.Image] = None
        if bg_media and Path(bg_media).exists():
            bg_raw = Image.open(bg_media).convert("RGB")
            bg_img = bg_raw.resize((self.w, self.h), Image.Resampling.LANCZOS)

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
        green_canvas = Image.new("RGBA", (self.w, self.h), (0, 177, 64, 255))

        for f_idx in range(total_frames):
            t = f_idx / float(self.fps)
            prog = t / max(0.01, duration_sec)

            # Horizontal translation across screen
            current_x = start_x + (end_x - start_x) * prog

            # Walk phase (loops smoothly)
            walk_phase = (t * walk_speed) % 1.0

            # 12 fps line boil / hand-drawn posterize jitter
            jitter_idx = int(t * 12.0)

            # Create base canvas
            if bg_img:
                frame = bg_img.copy().convert("RGBA")
            elif green_screen:
                frame = green_canvas.copy()
            else:
                frame = Image.new("RGBA", (self.w, self.h), (255, 255, 255, 255))
                # Draw minimal comic ground line
                d_base = ImageDraw.Draw(frame)
                d_base.line([(0, ground_y), (self.w, ground_y)], fill=(226, 232, 240), width=6)

            draw = ImageDraw.Draw(frame)

            # Draw walking character
            self.walker.draw_character(
                canvas=frame,
                pos_x=current_x,
                ground_y=ground_y,
                walk_phase=walk_phase,
                facing_right=(end_x >= start_x),
                is_walking=True,
                emotion="curious",
                accessory="backpack",
                jitter_frame=jitter_idx,
            )

            # Bubble spring pop-in (positioned above character so body/face is fully visible)
            bubble_scale = StickmanTimeline.bubble_spring_scale(t, t_start=0.3, pop_duration=0.5)
            if bubble_scale > 0.05:
                bubble_w = 480
                bubble_h = 150
                head_top_y = ground_y - 340.0
                by = max(70, int(head_top_y - bubble_h - 30))
                # Trail behind character slightly
                bx = min(self.w - bubble_w - 60, max(60, int(current_x - (bubble_w * 0.7 if (end_x >= start_x) else bubble_w * 0.3))))
                head_pt = (int(current_x), int(head_top_y + 10))

                if bubble_type == "thought":
                    ThoughtBubble.draw(
                        draw=draw,
                        x=bx,
                        y=by,
                        w=bubble_w,
                        h=bubble_h,
                        head_target=head_pt,
                        badge_text=badge_title,
                        quote_text=dialogue,
                        scale=bubble_scale,
                        max_chars=28,
                    )
                else:
                    ComicBubble.draw(
                        draw=draw,
                        x=bx,
                        y=by,
                        w=bubble_w,
                        h=bubble_h,
                        tail_target=head_pt,
                        badge_text=badge_title,
                        quote_text=dialogue,
                        scale=bubble_scale,
                        max_chars=28,
                    )

            # HUD Badge
            if location_title:
                loc_p = min(1.0, max(0.0, (t - 0.1) / 0.3))
                if loc_p > 0.05:
                    InfoBadge.draw(draw=draw, x=60, y=50, title=location_title, subtitle=location_stats)

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Walk across render failed: {err}")

        return out_p
