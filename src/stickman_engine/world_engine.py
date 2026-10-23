"""
world_engine.py
===============
Crayon Capital Style Unified World & Character Production Engine.
Ensures 100% aesthetic coherence:
- Hand-drawn 2D vector illustrated environments (streets, cafes, offices, skylines).
- High-fidelity rigged character animation with matching line weight and warm pastel palette.
- Cinematic camera tracking / smooth panning across panoramic scenes.
- Seamless action transitions: Walk -> Pause -> Look around / Sip Coffee / Check Phone -> Inner Monologue Bubble.
"""

import os
import math
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from .bubble import ComicBubble, ThoughtBubble, InfoBadge, get_engine_font
from .animator import StickmanTimeline, easing_elastic_out, easing_ease_in_out
from .overlay import get_ffmpeg_binary

W = 1920
H = 1080


class CrayonWorldEngine:
    """Unified engine producing complete Crayon Capital / MinutePhysics cinematic scenes."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 25):
        self.w = width
        self.h = height
        self.fps = fps
        self.ffmpeg_bin = get_ffmpeg_binary()

    def render_cinematic_street_scene(
        self,
        output_path: str,
        bg_illustration_path: str,
        character_sprites: Dict[str, Image.Image], # Dict of transparent PIL images for 'contact', 'passing', 'coffee', 'pointing', etc.
        dialogue: str,
        duration_sec: float = 6.0,
        badge_title: str = "İÇ SES // GÜNLÜK",
        location_title: str = "📍 KADIKÖY MODA // TARİHİ SOKAK",
        location_stats: str = "👟 14.850 Adım // 9.5 km • ☀️ 22°C",
        start_x: float = 250.0,
        pause_x: float = 1100.0,
        pause_time: float = 3.5, # Time at which character stops and reacts
        ground_y: float = 880.0,
        walk_speed: float = 2.4, # Steps per second
        char_height: int = 420,
    ) -> Path:
        """
        Renders a complete Crayon Capital style scene:
        1. Character walks smoothly across the hand-drawn illustrated street.
        2. At pause_time, character stops naturally at pause_x.
        3. Character transitions to looking around / sipping coffee or checking phone.
        4. "İç Ses" monologue bubble pops up with elastic spring.
        5. Camera tracks with smooth easing.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(round(duration_sec * self.fps))

        # Load and prepare wide background
        bg_raw = Image.open(bg_illustration_path).convert("RGB")
        # Ensure bg is at least 1920 wide, aspect maintained
        bg_scale = max(self.w / bg_raw.width, self.h / bg_raw.height)
        new_bg_w = int(bg_raw.width * bg_scale)
        new_bg_h = int(bg_raw.height * bg_scale)
        bg_panoramic = bg_raw.resize((new_bg_w, new_bg_h), Image.Resampling.LANCZOS)

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

        for f_idx in range(total_frames):
            t = f_idx / float(self.fps)

            # 1. Timeline & Position Calculations
            if t < pause_time:
                # Walking phase
                p_walk = t / pause_time
                ease_walk = easing_ease_in_out(p_walk)
                char_x = start_x + (pause_x - start_x) * ease_walk
                is_walking = True
                walk_phase = (t * walk_speed) % 1.0
            else:
                # Paused / stopped phase
                char_x = pause_x
                is_walking = False
                walk_phase = 0.0

            # 2. Camera Tracking (Smooth pan on panoramic background)
            max_scroll = max(0, new_bg_w - self.w)
            scroll_progress = min(1.0, max(0.0, (char_x - start_x) / max(1.0, pause_x - start_x)))
            cam_x = int(scroll_progress * max_scroll)
            cam_y = max(0, (new_bg_h - self.h) // 2)

            frame = bg_panoramic.crop((cam_x, cam_y, cam_x + self.w, cam_y + self.h)).convert("RGBA")
            draw = ImageDraw.Draw(frame)

            # 3. Character Pose Selection
            if is_walking:
                # Alternate between contact and passing poses based on walk_phase
                if (walk_phase < 0.25) or (0.5 <= walk_phase < 0.75):
                    pose_key = "contact" if "contact" in character_sprites else list(character_sprites.keys())[0]
                else:
                    pose_key = "passing" if "passing" in character_sprites else list(character_sprites.keys())[0]
                
                # Bobbing motion
                bob_y = -abs(math.sin(walk_phase * math.pi * 2.0)) * 12.0
                tilt_deg = math.sin(walk_phase * math.pi * 2.0) * 3.0
            else:
                # Reaction pose (e.g. coffee, phone, or pointing)
                pose_key = "action" if "action" in character_sprites else list(character_sprites.keys())[-1]
                bob_y = math.sin(t * 1.5 * math.pi * 2.0) * 4.0
                tilt_deg = 0.0

            char_img_orig = character_sprites.get(pose_key, list(character_sprites.values())[0])
            aspect = char_img_orig.width / max(1, char_img_orig.height)
            target_w = int(char_height * aspect)
            char_img = char_img_orig.resize((target_w, char_height), Image.Resampling.LANCZOS)
            if abs(tilt_deg) > 0.5:
                char_img = char_img.rotate(-tilt_deg, resample=Image.Resampling.BICUBIC, expand=True)

            # 4. Soft Ground Shadow
            cx = int(char_x)
            cy = int(ground_y + bob_y)
            shadow_w = int(char_height * 0.42)
            shadow_h = 22
            draw.ellipse(
                [(cx - shadow_w // 2, int(ground_y) - 6), (cx + shadow_w // 2, int(ground_y) + shadow_h - 6)],
                fill=(0, 0, 0, 85)
            )

            # 5. Paste Character
            draw_x = cx - char_img.width // 2
            draw_y = cy - char_img.height
            frame.alpha_composite(char_img, (draw_x, draw_y))

            # 6. Thought Bubble (Pops in after pause)
            bubble_start = pause_time + 0.3
            bubble_scale = StickmanTimeline.bubble_spring_scale(t, t_start=bubble_start, pop_duration=0.55)
            if bubble_scale > 0.05:
                bubble_w = 490
                bubble_h = 160
                bx = min(self.w - bubble_w - 60, max(60, cx - bubble_w - 30))
                by = max(80, draw_y - bubble_h + 30)
                head_pt = (cx, draw_y + int(char_img.height * 0.22))

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

            # 7. Location HUD Card
            if location_title:
                loc_p = min(1.0, max(0.0, (t - 0.2) / 0.35))
                if loc_p > 0.05:
                    InfoBadge.draw(draw=draw, x=60, y=50, title=location_title, subtitle=location_stats)

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Cinematic street render failed: {err}")

        return out_p

    def render_action_scene(
        self,
        output_path: str,
        bg_path: str,
        character_sprites: Dict[str, Image.Image],
        dialogue: str,
        duration_sec: float = 6.0,
        motion_mode: str = "walk_to_target", # 'walk_to_target', 'pacing', 'walk_across'
        start_x: float = 180.0,
        target_x: float = 960.0,
        ground_y: float = 880.0,
        char_height: int = 440,
        walk_speed: float = 2.4,
        pause_time: float = 3.0,
        bubble_type: str = "comic", # 'comic' or 'thought'
        badge_text: str = "DİYALOG",
        badge_color: Tuple[int, int, int] = (234, 88, 12),
        banner_title: Optional[str] = None,
        banner_subtitle: Optional[str] = None,
    ) -> Path:
        """
        Universal dynamic motion & action producer across ANY channel:
        - Walk & stop in front of datacenter / office / radar / street
        - Anxious pacing back and forth with turnaround direction flipping
        - Stopping and transitioning into active gesture (pointing, burning money, holding coffee/phone)
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(round(duration_sec * self.fps))

        bg_raw = Image.open(bg_path).convert("RGBA").resize((self.w, self.h), Image.Resampling.LANCZOS)

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

        for f_idx in range(total_frames):
            t = f_idx / float(self.fps)

            # 1. Motion Calculation
            if motion_mode == "pacing":
                # Pacing back and forth between start_x and target_x
                pace_period = 3.0
                p_norm = (t % pace_period) / pace_period # 0.0 to 1.0
                if p_norm < 0.5:
                    sub_p = p_norm / 0.5
                    char_x = start_x + (target_x - start_x) * easing_ease_in_out(sub_p)
                    facing_right = (target_x >= start_x)
                else:
                    sub_p = (p_norm - 0.5) / 0.5
                    char_x = target_x - (target_x - start_x) * easing_ease_in_out(sub_p)
                    facing_right = not (target_x >= start_x)

                is_walking = True
                walk_phase = (t * walk_speed) % 1.0
                pose_key = "contact" if ((walk_phase < 0.25) or (0.5 <= walk_phase < 0.75)) else "passing"
                bob_y = -abs(math.sin(walk_phase * math.pi * 2.0)) * 11.0
                tilt_deg = math.sin(walk_phase * math.pi * 2.0) * 3.0

            elif motion_mode == "walk_across":
                p_walk = t / max(0.1, duration_sec)
                char_x = start_x + (target_x - start_x) * p_walk
                facing_right = (target_x >= start_x)
                is_walking = True
                walk_phase = (t * walk_speed) % 1.0
                pose_key = "contact" if ((walk_phase < 0.25) or (0.5 <= walk_phase < 0.75)) else "passing"
                bob_y = -abs(math.sin(walk_phase * math.pi * 2.0)) * 11.0
                tilt_deg = math.sin(walk_phase * math.pi * 2.0) * 3.0

            else: # walk_to_target and pause
                if t < pause_time:
                    p_walk = t / max(0.1, pause_time)
                    char_x = start_x + (target_x - start_x) * easing_ease_in_out(p_walk)
                    facing_right = (target_x >= start_x)
                    is_walking = True
                    walk_phase = (t * walk_speed) % 1.0
                    pose_key = "contact" if ((walk_phase < 0.25) or (0.5 <= walk_phase < 0.75)) else "passing"
                    bob_y = -abs(math.sin(walk_phase * math.pi * 2.0)) * 11.0
                    tilt_deg = math.sin(walk_phase * math.pi * 2.0) * 3.0
                else:
                    char_x = target_x
                    facing_right = (target_x >= start_x)
                    is_walking = False
                    walk_phase = 0.0
                    pose_key = "action"
                    bob_y = math.sin(t * 1.5 * math.pi * 2.0) * 3.5
                    tilt_deg = 0.0

            frame = bg_raw.copy()
            draw = ImageDraw.Draw(frame)

            # 2. Prepare Character Sprite
            char_orig = character_sprites.get(pose_key, list(character_sprites.values())[0])
            aspect = char_orig.width / max(1, char_orig.height)
            target_w = int(char_height * aspect)
            char_img = char_orig.resize((target_w, char_height), Image.Resampling.LANCZOS)

            # Flip if walking left
            if not facing_right:
                char_img = ImageOps.mirror(char_img)

            if abs(tilt_deg) > 0.5:
                char_img = char_img.rotate(-tilt_deg, resample=Image.Resampling.BICUBIC, expand=True)

            # 3. Soft Dynamic Ground Shadow
            cx = int(char_x)
            cy = int(ground_y + bob_y)
            shadow_w = int(char_height * 0.44)
            shadow_h = 22
            draw.ellipse(
                [(cx - shadow_w // 2, int(ground_y) - 6), (cx + shadow_w // 2, int(ground_y) + shadow_h - 6)],
                fill=(0, 0, 0, 80)
            )

            # 4. Composite Character
            draw_x = cx - char_img.width // 2
            draw_y = cy - char_img.height
            frame.alpha_composite(char_img, (draw_x, draw_y))

            # 5. Top Banner (optional)
            if banner_title:
                draw.rounded_rectangle(
                    [(self.w // 2 - 450, 20), (self.w // 2 + 450, 85)],
                    radius=14,
                    fill=(15, 23, 42, 235),
                    outline=(59, 130, 246),
                    width=2
                )
                draw.text((self.w // 2 - 420, 28), f">> {banner_title}", font=get_engine_font(16, bold=True), fill=(255, 255, 255))
                if banner_subtitle:
                    draw.text((self.w // 2 - 420, 55), banner_subtitle, font=get_engine_font(13, bold=False), fill=(245, 158, 11))

            # 6. Dialogue / Monologue Bubble
            b_start = pause_time * 0.5 if motion_mode != "walk_to_target" else pause_time * 0.8
            bubble_scale = StickmanTimeline.bubble_spring_scale(t, t_start=b_start, pop_duration=0.5)
            if bubble_scale > 0.05:
                bubble_w = 520
                bubble_h = 160
                bx = min(self.w - bubble_w - 60, max(60, cx - bubble_w // 2))
                by = max(100, draw_y - bubble_h - 20)
                head_pt = (cx, draw_y + int(char_img.height * 0.22))

                if bubble_type == "thought":
                    ThoughtBubble.draw(
                        draw=draw,
                        x=bx,
                        y=by,
                        w=bubble_w,
                        h=bubble_h,
                        head_target=head_pt,
                        badge_text=badge_text,
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
                        badge_text=badge_text,
                        badge_color=badge_color,
                        quote_text=dialogue,
                        scale=bubble_scale,
                        max_chars=28,
                    )

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Action scene render failed: {err}")

        return out_p

