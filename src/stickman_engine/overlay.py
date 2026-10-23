"""
overlay.py
==========
Compositing and video export engine for the Stickman Video Production Engine.
Outputs:
1. Direct Composite over user footage (Travel camera footage / background video or photo).
2. Green Screen MP4 for universal video editor chroma-keying.
3. Transparent MOV (ProRes 4444) with full alpha channel.
4. Auto-audio muxing with cloned voiceover / internal monologue narration.
"""

import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .character import StickmanCharacter, CharacterState, ProceduralStickman
from .bubble import ComicBubble, ThoughtBubble, InfoBadge
from .animator import StickmanTimeline, MotionPath

W = 1920
H = 1080

def get_ffmpeg_binary() -> str:
    """Finds best ffmpeg executable (bundled imageio_ffmpeg or system)."""
    bundled = Path(".venv/lib/python3.14/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1")
    if bundled.exists():
        return str(bundled)
    system = shutil.which("ffmpeg")
    if system:
        return system
    return "ffmpeg"


class StickmanOverlayCompositor:
    """Renders animated stickman layers and composites them over travel footage or backdrops."""

    def __init__(self, output_width: int = 1920, output_height: int = 1080, fps: int = 25):
        self.w = output_width
        self.h = output_height
        self.fps = fps
        self.ffmpeg_bin = get_ffmpeg_binary()

    def generate_travel_monologue_frame(
        self,
        t: float,
        character: StickmanCharacter,
        dialogue: str,
        badge_title: str = "İÇ SES // GÜNLÜK",
        char_pos: Tuple[int, int] = (1450, 640),
        char_height: int = 420,
        bubble_type: str = "thought", # 'thought' or 'comic'
        location_badge: Optional[Tuple[str, str]] = None, # (title, subtitle)
        is_walking: bool = False,
        walk_speed: float = 2.0,
        flip_h: bool = False,
    ) -> Image.Image:
        """
        Renders a single RGBA frame with animated stickman and monologue thought bubble.
        """
        frame = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)

        # 1. Kinematics & Physics
        if is_walking:
            bob_y, tilt_deg, walk_phase = StickmanTimeline.walk_cycle(t, speed=walk_speed, step_height=12.0, tilt_amp=3.0)
        else:
            bob_y = StickmanTimeline.breathe_offset(t, freq=1.3, amp=5.0)
            tilt_deg = 0.0

        cx, cy = char_pos
        current_y = cy + int(bob_y)

        # 2. Soft Ground Shadow
        shadow_w = int(char_height * 0.45)
        shadow_h = 24
        shadow_x = cx - shadow_w // 2
        shadow_y = current_y + char_height - 18
        draw.ellipse([(shadow_x, shadow_y), (shadow_x + shadow_w, shadow_y + shadow_h)], fill=(0, 0, 0, 90))

        # 3. Render Stickman Character
        char_img = character.get_pose_image(
            target_height=char_height,
            tilt_degrees=tilt_deg,
            flip_h=flip_h
        )
        # Center horizontally at cx, bottom at (current_y + char_height)
        char_draw_x = cx - char_img.width // 2
        char_draw_y = current_y + char_height - char_img.height
        frame.alpha_composite(char_img, (char_draw_x, char_draw_y))

        # 4. Bubble Entrance Animation (Spring pop-in)
        bubble_scale = StickmanTimeline.bubble_spring_scale(t, t_start=0.3, pop_duration=0.45)
        
        # Position bubble above and slightly to the left/right of head
        head_x = cx
        head_y = char_draw_y + int(char_img.height * 0.22)
        
        bubble_w = 480
        bubble_h = 160
        # If character is on the right side of screen, bubble sits on the left of character
        if cx > self.w // 2:
            bubble_x = max(60, cx - bubble_w - 40)
            bubble_y = max(80, head_y - bubble_h - 40)
        else:
            bubble_x = min(self.w - bubble_w - 60, cx + 50)
            bubble_y = max(80, head_y - bubble_h - 40)

        if bubble_type == "thought":
            ThoughtBubble.draw(
                draw=draw,
                x=bubble_x,
                y=bubble_y,
                w=bubble_w,
                h=bubble_h,
                head_target=(head_x, head_y),
                badge_text=badge_title,
                quote_text=dialogue,
                scale=bubble_scale,
                max_chars=28,
            )
        else:
            ComicBubble.draw(
                draw=draw,
                x=bubble_x,
                y=bubble_y,
                w=bubble_w,
                h=bubble_h,
                tail_target=(head_x, head_y),
                badge_text=badge_title,
                badge_color=(234, 88, 12),
                quote_text=dialogue,
                scale=bubble_scale,
                max_chars=28,
            )

        # 5. Optional Location HUD Card (Top-Left)
        if location_badge:
            loc_scale = min(1.0, max(0.0, (t - 0.1) / 0.3))
            if loc_scale > 0.1:
                title, subtitle = location_badge
                InfoBadge.draw(draw=draw, x=60, y=50, title=title, subtitle=subtitle)

        return frame

    def render_overlay_video(
        self,
        output_path: Path,
        duration_sec: float,
        character: StickmanCharacter,
        dialogue: str,
        badge_title: str = "İÇ SES // GÜNLÜK",
        char_pos: Tuple[int, int] = (1450, 620),
        char_height: int = 430,
        bubble_type: str = "thought",
        location_badge: Optional[Tuple[str, str]] = None,
        is_walking: bool = False,
        bg_media: Optional[Path] = None, # Video or Image to composite over
        green_screen: bool = False,
        audio_path: Optional[Path] = None,
    ) -> Path:
        """
        Renders complete video file with ffmpeg pipe.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(round(duration_sec * self.fps))

        # Prepare background if static image
        bg_image: Optional[Image.Image] = None
        if bg_media and bg_media.exists() and bg_media.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
            bg_raw = Image.open(bg_media).convert("RGB")
            bg_image = bg_raw.resize((self.w, self.h), Image.Resampling.LANCZOS)

        # Setup ffmpeg command
        ffmpeg_cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.w}x{self.h}",
            "-pix_fmt", "rgba",
            "-r", str(self.fps),
            "-i", "-",
        ]

        # Audio input if provided
        if audio_path and Path(audio_path).exists():
            ffmpeg_cmd.extend(["-i", str(audio_path)])

        if green_screen:
            # Output MP4 with standard Green Chroma Key
            ffmpeg_cmd.extend([
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
            ])
        elif output_path.suffix.lower() == ".mov":
            # Output ProRes 4444 with native alpha
            ffmpeg_cmd.extend([
                "-c:v", "prores_ks",
                "-profile:v", "4444",
                "-pix_fmt", "yuva444p10le",
            ])
        else:
            # Default MP4
            ffmpeg_cmd.extend([
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
            ])

        if audio_path and Path(audio_path).exists():
            ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest"])

        ffmpeg_cmd.append(str(output_path))

        process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

        green_canvas = Image.new("RGBA", (self.w, self.h), (0, 177, 64, 255)) # Chroma Green

        for frame_idx in range(total_frames):
            t = frame_idx / float(self.fps)
            overlay_frame = self.generate_travel_monologue_frame(
                t=t,
                character=character,
                dialogue=dialogue,
                badge_title=badge_title,
                char_pos=char_pos,
                char_height=char_height,
                bubble_type=bubble_type,
                location_badge=location_badge,
                is_walking=is_walking,
            )

            if bg_image:
                final_frame = bg_image.copy().convert("RGBA")
                final_frame.alpha_composite(overlay_frame)
            elif green_screen:
                final_frame = green_canvas.copy()
                final_frame.alpha_composite(overlay_frame)
            else:
                final_frame = overlay_frame

            process.stdin.write(final_frame.tobytes())

        process.stdin.close()
        process.wait()

        if process.returncode != 0:
            err = process.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"FFmpeg stickman render failed: {err}")

        return output_path
