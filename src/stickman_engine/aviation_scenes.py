"""
aviation_scenes.py
==================
High-fidelity BlackboxAudioo & Aviation Documentary Scene Production Engine.
Supports:
1. 100% Crayon Capital Style Cockpit CVR Scene:
   - 2D Illustrated Boeing 737 cockpit background (sheepskin seats, glowing PFDs, blizzard storm).
   - Captain Wheaton firmly holding flight control yoke.
   - First Officer Pettit screaming in panic and urgently pointing at Master Warning.
   - Turbulence physics, flashing alarms, bouncy CVR dialogue balloons.
2. Crayon ATC Tower Scene:
   - Sweeping green radar scope, radio mic to mouth, green TX flash, runway lights.
3. NTSB Crash Investigation Scene:
   - Official forensic lab, magnifying glass inspecting the bright orange Flight Data Recorder (Black Box).
"""

import os
import math
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .articulated_rig import ArticulatedRig
from .bubble import ComicBubble, InfoBadge, get_engine_font
from .animator import StickmanTimeline
from .overlay import get_ffmpeg_binary

W = 1920
H = 1080


class AviationSceneProducer:
    """Produces broadcast-quality animated aviation scenes for BlackboxAudioo."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 25):
        self.w = width
        self.h = height
        self.fps = fps
        self.rig = ArticulatedRig(scale=1.2)
        self.ffmpeg_bin = get_ffmpeg_binary()

    def render_crayon_cockpit_scene(
        self,
        output_path: str,
        flight_name: str = "AIR FLORIDA FLIGHT 90",
        situation_title: str = "POTOMAC RIVER APPROACH // CRITICAL STALL WARNING",
        captain_dialogue: str = "Yes it is, there's eighty knots...",
        fo_dialogue: str = "Larry, that don't look right, does it?",
        bank_angle: float = 38.0,
        duration_sec: float = 6.0,
        audio_path: Optional[str] = None,
    ) -> Path:
        """
        Renders an authentic, broadcast-grade CVR cockpit scene matching Crayon Capital aesthetic.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(round(duration_sec * self.fps))

        # Load assets
        bg_path = Path("assets/crayon_cockpit_bg.jpg")
        bg_raw = Image.open(bg_path).convert("RGBA").resize((self.w, self.h), Image.Resampling.LANCZOS)

        cap_img_raw = Image.open("assets/characters/aviation/crayon_captain_yoke.png").convert("RGBA")
        fo_img_raw = Image.open("assets/characters/aviation/crayon_fo_pointing.png").convert("RGBA")

        # Scale characters to fit cockpit seats
        cap_target_h = 560
        cap_scale = cap_target_h / cap_img_raw.height
        cap_img = cap_img_raw.resize((int(cap_img_raw.width * cap_scale), cap_target_h), Image.Resampling.LANCZOS)

        fo_target_h = 540
        fo_scale = fo_target_h / fo_img_raw.height
        fo_img = fo_img_raw.resize((int(fo_img_raw.width * fo_scale), fo_target_h), Image.Resampling.LANCZOS)

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

        if audio_path and Path(audio_path).exists():
            ffmpeg_cmd.extend(["-i", str(audio_path)])

        ffmpeg_cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
        ])

        if audio_path and Path(audio_path).exists():
            ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest"])

        ffmpeg_cmd.append(str(out_p))

        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

        for f_idx in range(total_frames):
            t = f_idx / float(self.fps)

            # Turbulence / Aircraft roll shake
            turb_x = int(math.sin(t * 22.0) * 3.5)
            turb_y = int(math.cos(t * 18.0) * 2.5)

            frame = bg_raw.copy()
            draw = ImageDraw.Draw(frame)

            # Master warning alarm flash on instrument panel
            warn_flash = (math.sin(t * 14.0) > 0.0)
            if warn_flash:
                # Flashing red glare over dashboard warning annunciators
                draw.ellipse([(620, 410), (660, 450)], fill=(255, 30, 30, 200))
                draw.ellipse([(self.w - 660, 410), (self.w - 620, 450)], fill=(255, 30, 30, 200))

            # 1. Left Seat: CAPTAIN (Larry Wheaton)
            # Sitting in left sheepskin seat, hands gripping yoke
            cap_x = 240 + turb_x
            cap_y = 440 + turb_y
            # Slight bank tilt on turbulence
            cap_tilt = math.sin(t * 12.0) * 2.0
            cur_cap = cap_img.rotate(cap_tilt, resample=Image.Resampling.BICUBIC, expand=True) if abs(cap_tilt) > 0.3 else cap_img
            frame.alpha_composite(cur_cap, (cap_x, cap_y))

            # 2. Right Seat: FIRST OFFICER (Roger Pettit)
            # Sitting in right seat, scream/panic, pointing urgently at Master Warning / stall
            fo_x = self.w - fo_img.width - 160 + turb_x
            fo_y = 430 + turb_y
            fo_tilt = math.cos(t * 15.0) * 2.5
            cur_fo = fo_img.rotate(fo_tilt, resample=Image.Resampling.BICUBIC, expand=True) if abs(fo_tilt) > 0.3 else fo_img
            frame.alpha_composite(cur_fo, (fo_x, fo_y))

            # 3. Top Telemetry Banner
            draw.rounded_rectangle([(self.w // 2 - 420, 20), (self.w // 2 + 420, 80)], radius=12, fill=(15, 23, 42, 230), outline=(51, 65, 85), width=2)
            draw.text((self.w // 2 - 380, 28), f"🎙️ {flight_name} // CVR RECORDING", font=get_engine_font(16, bold=True), fill=(255, 255, 255))
            draw.text((self.w // 2 - 380, 52), situation_title, font=get_engine_font(13, bold=False), fill=(244, 63, 94))

            # 4. First Officer Dialogue Bubble (Right, pointing from mouth)
            fo_scale = StickmanTimeline.bubble_spring_scale(t, t_start=0.3, pop_duration=0.45)
            if fo_scale > 0.05:
                ComicBubble.draw(
                    draw=draw,
                    x=self.w - 740,
                    y=110,
                    w=520,
                    h=150,
                    tail_target=(fo_x + 80, fo_y + 120),
                    badge_text="FIRST OFFICER PETTIT [CVR]",
                    badge_color=(239, 68, 68),
                    quote_text=fo_dialogue,
                    scale=fo_scale,
                    max_chars=26,
                )

            # 5. Captain Dialogue Bubble (Left, answering)
            cap_scale = StickmanTimeline.bubble_spring_scale(t, t_start=2.4, pop_duration=0.45)
            if cap_scale > 0.05:
                ComicBubble.draw(
                    draw=draw,
                    x=180,
                    y=110,
                    w=520,
                    h=150,
                    tail_target=(cap_x + cap_img.width - 80, cap_y + 140),
                    badge_text="CAPTAIN WHEATON [CVR]",
                    badge_color=(37, 99, 235),
                    quote_text=captain_dialogue,
                    scale=cap_scale,
                    max_chars=26,
                )

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Crayon Cockpit render failed: {err}")

        return out_p

    def render_atc_tower_scene(
        self,
        output_path: str,
        facility_name: str = "WASHINGTON NATIONAL TOWER (DCA)",
        atc_instruction: str = "Palm 90, Washington Tower, Runway 36 cleared for takeoff!",
        duration_sec: float = 5.0,
    ) -> Path:
        """
        Renders an authentic animated Air Traffic Control Tower scene using Crayon ATC character.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(round(duration_sec * self.fps))

        atc_raw = Image.open("assets/characters/aviation/crayon_atc_radio.png").convert("RGBA")
        atc_h = 600
        atc_scale = atc_h / atc_raw.height
        atc_img = atc_raw.resize((int(atc_raw.width * atc_scale), atc_h), Image.Resampling.LANCZOS)

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

            # Panoramic Tower Glass Window looking onto Runway
            frame = Image.new("RGBA", (self.w, self.h), (10, 16, 26, 255))
            draw = ImageDraw.Draw(frame)

            # Runway lighting in distance
            for lx in range(120, self.w - 120, 48):
                draw.ellipse([(lx, 380), (lx + 6, 386)], fill=(255, 245, 180, 200))

            # Tower Console Desk
            desk_y = 520
            draw.polygon([(0, desk_y), (self.w, desk_y), (self.w, self.h), (0, self.h)], fill=(15, 23, 42))
            draw.line([(0, desk_y), (self.w, desk_y)], fill=(30, 41, 59), width=4)

            # Sweeping Phosphor Green Radar Scope (Left)
            rx, ry, rr = 340, desk_y + 140, 150
            draw.ellipse([(rx - rr, ry - rr), (rx + rr, ry + rr)], fill=(5, 20, 12), outline=(16, 185, 129), width=4)
            for rad_c in [45, 90, 135]:
                draw.ellipse([(rx - rad_c, ry - rad_c), (rx + rad_c, ry + rad_c)], outline=(16, 185, 129, 80), width=1)

            # Sweeping beam
            sweep_angle = (t * 160.0) % 360.0
            sw_x = rx + rr * math.cos(math.radians(sweep_angle))
            sw_y = ry + rr * math.sin(math.radians(sweep_angle))
            draw.line([(rx, ry), (sw_x, sw_y)], fill=(52, 211, 153), width=3)
            # Flight blip
            draw.ellipse([(rx + 55, ry - 35), (rx + 65, ry - 25)], fill=(255, 255, 255))
            draw.text((rx + 72, ry - 42), "PALM 90\nFL004 // 84KT", font=get_engine_font(11, bold=True), fill=(52, 211, 153))

            # Right: ATC Controller (Illustrated Crayon Character holding radio mic to mouth)
            atc_x = self.w - atc_img.width - 180
            atc_y = self.h - atc_img.height - 10
            # Subtle breathing bob
            atc_bob = math.sin(t * 2.0 * math.pi) * 3.0
            frame.alpha_composite(atc_img, (atc_x, int(atc_y + atc_bob)))

            # Green TX Transmitting Indicator Light on Console
            tx_flash = (math.sin(t * 12.0) > -0.3)
            draw.rounded_rectangle([(atc_x - 180, desk_y + 40), (atc_x - 60, desk_y + 80)], radius=6, fill=(16, 185, 129) if tx_flash else (10, 40, 25), outline=(255, 255, 255) if tx_flash else (15, 23, 42), width=2)
            draw.text((atc_x - 165, desk_y + 52), "RADIO TX ON", font=get_engine_font(12, bold=True), fill=(255, 255, 255))

            # Top Facility Header
            draw.rounded_rectangle([(self.w // 2 - 380, 25), (self.w // 2 + 380, 80)], radius=12, fill=(15, 23, 42, 230), outline=(51, 65, 85), width=2)
            draw.text((self.w // 2 - 350, 34), f"📡 {facility_name}", font=get_engine_font(16, bold=True), fill=(255, 255, 255))
            draw.text((self.w // 2 - 350, 56), "VHF 119.1 MHz // RUNWAY 36 TOWER CONTROL", font=get_engine_font(13, bold=False), fill=(52, 211, 153))

            # ATC Comic Speech Balloon
            b_scale = StickmanTimeline.bubble_spring_scale(t, t_start=0.3, pop_duration=0.45)
            if b_scale > 0.05:
                ComicBubble.draw(
                    draw=draw,
                    x=540,
                    y=150,
                    w=540,
                    h=150,
                    tail_target=(atc_x + 40, atc_y + 120),
                    badge_text="LOCAL TOWER CONTROLLER [ATC]",
                    badge_color=(16, 185, 129),
                    quote_text=atc_instruction,
                    scale=b_scale,
                    max_chars=28,
                )

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"ATC Tower render failed: {err}")

        return out_p
