"""
satire_scenes.py
================
Broadcast-grade production engine for:
1. Technology & Silicon Valley Finance Documentaries (Crayon Capital style):
   - AI Datacenter & Startup Crash background with glowing cyan server racks & neural networks.
   - Silicon Valley Tech Founder sweating with burning cash.
   - Wall Street Trader screaming at plummeting red stock crash line on phone.
   - Animated stock crash ticker, valuation metrics, VC runway alerts.
2. Military Vehicles & Defense Satire (Crayon Combat style):
   - Pentagon Briefing War Room with tactical radar screens, missile trajectories & blueprints.
   - 4-Star Pentagon General screaming in sheer panic over budget overruns.
   - Defense Contractor CEO smugly grinning with dollar signs in eyes and giant cash sack.
   - Tactical radar sweep, blueprint HUD telemetry, Classified stamps.
"""

import os
import math
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .bubble import ComicBubble, InfoBadge, get_engine_font, wrap_text
from .animator import StickmanTimeline
from .overlay import get_ffmpeg_binary

W = 1920
H = 1080


class SatireSceneProducer:
    """Produces broadcast-quality animated satire and documentary scenes."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 25):
        self.w = width
        self.h = height
        self.fps = fps
        self.ffmpeg_bin = get_ffmpeg_binary()

    def render_tech_finance_scene(
        self,
        output_path: str,
        headline: str = "SILICON VALLEY VC DISASTER // CASH BURN REPORT",
        company_name: str = "NEURALSCALE AI (SERIES B)",
        valuation_drop: str = "$2.4 BILLION -> $80 MILLION (-97% COLLAPSE)",
        founder_dialogue: str = "We bought 24,000 H100 GPUs... and built a chatbot that writes haikus!",
        trader_dialogue: str = "The market cap just vaporized! Liquidate the margin calls!",
        duration_sec: float = 6.0,
        audio_path: Optional[str] = None,
    ) -> Path:
        """
        Renders a Crayon Capital style Tech & Finance Documentary scene.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(round(duration_sec * self.fps))

        # 1. Load Background & Characters
        bg_path = Path("assets/crayon_tech_bg.jpg")
        bg_raw = Image.open(bg_path).convert("RGBA").resize((self.w, self.h), Image.Resampling.LANCZOS)

        founder_raw = Image.open("assets/characters/defense_finance/crayon_tech_founder.png").convert("RGBA")
        trader_raw = Image.open("assets/characters/defense_finance/crayon_wall_street_trader.png").convert("RGBA")

        # Scale characters
        f_target_h = 580
        f_scale = f_target_h / founder_raw.height
        founder_img = founder_raw.resize((int(founder_raw.width * f_scale), f_target_h), Image.Resampling.LANCZOS)

        tr_target_h = 580
        tr_scale = tr_target_h / trader_raw.height
        trader_img = trader_raw.resize((int(trader_raw.width * tr_scale), tr_target_h), Image.Resampling.LANCZOS)

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

            frame = bg_raw.copy()
            draw = ImageDraw.Draw(frame)

            # Micro-movements
            # Tech founder nervous shudder & burning cash flame flicker
            f_tremble_x = math.sin(t * 22.0) * 2.0
            f_tremble_y = math.cos(t * 16.0) * 1.5
            f_x = 240 + int(f_tremble_x)
            f_y = self.h - founder_img.height - 40 + int(f_tremble_y)

            # Trader panic shake holding smartphone
            tr_tremble_x = math.cos(t * 25.0) * 2.5
            tr_tremble_y = math.sin(t * 20.0) * 2.0
            tr_x = self.w - trader_img.width - 240 + int(tr_tremble_x)
            tr_y = self.h - trader_img.height - 40 + int(tr_tremble_y)

            # Floating burning cash ember particles
            for i_p in range(7):
                p_phase = (t * 1.8 + i_p * 0.45) % 1.0
                p_px = f_x + 130 + int(math.sin(t * 6.0 + i_p) * 25)
                p_py = f_y + 360 - int(p_phase * 160)
                p_r = int((1.0 - p_phase) * 5) + 2
                draw.ellipse([(p_px - p_r, p_py - p_r), (p_px + p_r, p_py + p_r)], fill=(255, 120, 30, int((1.0 - p_phase) * 220)))

            # Composite characters
            frame.alpha_composite(founder_img, (f_x, f_y))
            frame.alpha_composite(trader_img, (tr_x, tr_y))

            # Dynamic Stock Crash Glow on Wall Display
            pulse = (math.sin(t * 8.0) + 1.0) * 0.5
            chart_glow = int(180 + pulse * 75)
            # Red warning circle at crash nadir
            draw.ellipse([(1180, 520), (1210, 550)], fill=(chart_glow, 20, 20, 220), outline=(255, 255, 255), width=2)
            draw.text((1220, 522), "-97% DIP", font=get_engine_font(15, bold=True), fill=(255, 50, 50))

            # 1. Top Silicon Valley / Wall Street Ticker Header
            draw.rounded_rectangle(
                [(self.w // 2 - 460, 20), (self.w // 2 + 460, 85)],
                radius=14,
                fill=(10, 15, 30, 235),
                outline=(59, 130, 246),
                width=2
            )
            draw.text((self.w // 2 - 430, 28), f">> {headline}", font=get_engine_font(16, bold=True), fill=(255, 255, 255))
            draw.text((self.w // 2 - 430, 55), f"ENTITY: {company_name}  |  COLLAPSE: {valuation_drop}", font=get_engine_font(13, bold=False), fill=(239, 68, 68))

            # 2. Bottom Financial Telemetry HUD
            draw.rounded_rectangle(
                [(self.w // 2 - 380, self.h - 75), (self.w // 2 + 380, self.h - 20)],
                radius=10,
                fill=(15, 23, 42, 230),
                outline=(239, 68, 68),
                width=2
            )
            draw.text(
                (self.w // 2 - 350, self.h - 62),
                f"$ GPU DEBT: $1.2B  •  RUNWAY: 18 DAYS  •  NET CASH FLOW: -$45M/MO",
                font=get_engine_font(14, bold=True),
                fill=(254, 202, 202)
            )

            # 3. Founder Dialogue Bubble (Left, bouncing in at t=0.3s)
            f_scale = StickmanTimeline.bubble_spring_scale(t, t_start=0.3, pop_duration=0.45)
            if f_scale > 0.05:
                ComicBubble.draw(
                    draw=draw,
                    x=140,
                    y=110,
                    w=540,
                    h=165,
                    tail_target=(f_x + founder_img.width - 60, f_y + 110),
                    badge_text="AI FOUNDER [SERIES B]",
                    badge_color=(234, 88, 12),
                    quote_text=founder_dialogue,
                    scale=f_scale,
                    max_chars=27,
                    highlight_keywords=["H100", "GPUs", "chatbot", "haikus", "$100M", "burnt"],
                )

            # 4. Wall Street Trader Dialogue Bubble (Right, bouncing in at t=2.5s)
            tr_scale = StickmanTimeline.bubble_spring_scale(t, t_start=2.5, pop_duration=0.45)
            if tr_scale > 0.05:
                ComicBubble.draw(
                    draw=draw,
                    x=self.w - 710,
                    y=110,
                    w=550,
                    h=165,
                    tail_target=(tr_x + 60, tr_y + 110),
                    badge_text="WALL STREET ANALYST [SHORT SELLER]",
                    badge_color=(225, 29, 72),
                    quote_text=trader_dialogue,
                    scale=tr_scale,
                    max_chars=28,
                    highlight_keywords=["vaporized", "margin", "liquidate", "moat", "crash"],
                )

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Crayon Tech Finance render failed: {err}")

        return out_p

    def render_military_satire_scene(
        self,
        output_path: str,
        program_title: str = "PROJECT OVERLORD // F-35 STEALTH FIGHTER PROGRAM",
        budget_summary: str = "ORIGINAL: $233 BILLION -> CURRENT: $1.7 TRILLION (+630%)",
        general_dialogue: str = "We gave you 1.7 TRILLION dollars! Why does it crash when it gets wet?!",
        ceo_dialogue: str = "Relax General, for another $500 Billion, we might install windshield wipers.",
        duration_sec: float = 6.0,
        audio_path: Optional[str] = None,
    ) -> Path:
        """
        Renders an authentic Crayon Combat style Pentagon War Room & Military Satire scene.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        total_frames = int(round(duration_sec * self.fps))

        # 1. Load Background & Characters
        bg_path = Path("assets/crayon_military_bg.jpg")
        bg_raw = Image.open(bg_path).convert("RGBA").resize((self.w, self.h), Image.Resampling.LANCZOS)

        general_raw = Image.open("assets/characters/defense_finance/crayon_pentagon_general.png").convert("RGBA")
        ceo_raw = Image.open("assets/characters/defense_finance/crayon_defense_ceo.png").convert("RGBA")

        # Scale characters
        gen_target_h = 600
        gen_scale = gen_target_h / general_raw.height
        general_img = general_raw.resize((int(general_raw.width * gen_scale), gen_target_h), Image.Resampling.LANCZOS)

        ceo_target_h = 580
        ceo_scale = ceo_target_h / ceo_raw.height
        ceo_img = ceo_raw.resize((int(ceo_raw.width * ceo_scale), ceo_target_h), Image.Resampling.LANCZOS)

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

            frame = bg_raw.copy()
            draw = ImageDraw.Draw(frame)

            # Animated Tactical Radar Sweep on War Room Map (Center-Left)
            radar_cx, radar_cy = 960, 240
            sweep_angle = (t * 2.5) % (2 * math.pi)
            radar_len = 140
            rx_end = radar_cx + int(math.cos(sweep_angle) * radar_len)
            ry_end = radar_cy + int(math.sin(sweep_angle) * radar_len)
            draw.line([(radar_cx, radar_cy), (rx_end, ry_end)], fill=(34, 197, 94, 180), width=3)
            # Radar Blips
            draw.ellipse([(radar_cx + 40, radar_cy - 30), (radar_cx + 48, radar_cy - 22)], fill=(239, 68, 68, 220))
            draw.ellipse([(radar_cx - 60, radar_cy + 50), (radar_cx - 52, radar_cy + 58)], fill=(59, 130, 246, 220))

            # Micro-movements:
            # 1. Pentagon General screaming panic shake (both hands gripping head)
            gen_shake_x = math.sin(t * 32.0) * 3.5
            gen_shake_y = math.cos(t * 26.0) * 2.0
            gen_x = 220 + int(gen_shake_x)
            gen_y = self.h - general_img.height - 40 + int(gen_shake_y)

            # 2. Defense Contractor CEO triumphant slow cash-bag breathing bob
            ceo_bob_y = math.sin(t * 5.0) * 6.0
            ceo_x = self.w - ceo_img.width - 220
            ceo_y = self.h - ceo_img.height - 40 + int(ceo_bob_y)

            # Composite characters
            frame.alpha_composite(general_img, (gen_x, gen_y))
            frame.alpha_composite(ceo_img, (ceo_x, ceo_y))

            # 1. Top War Room Strategic Banner
            draw.rounded_rectangle(
                [(self.w // 2 - 470, 20), (self.w // 2 + 470, 85)],
                radius=14,
                fill=(15, 23, 42, 240),
                outline=(245, 158, 11),
                width=2
            )
            draw.text((self.w // 2 - 440, 28), f">> {program_title}", font=get_engine_font(16, bold=True), fill=(255, 255, 255))
            draw.text((self.w // 2 - 440, 55), f"BUDGET OVERRUN: {budget_summary}", font=get_engine_font(13, bold=False), fill=(245, 158, 11))

            # 2. Flashing TOP SECRET / CLASSIFIED Stamp (Bottom Center)
            stamp_flash = (math.sin(t * 10.0) > -0.2)
            if stamp_flash:
                draw.rectangle([(self.w // 2 - 200, self.h - 90), (self.w // 2 + 200, self.h - 35)], fill=(185, 28, 28, 220), outline=(254, 202, 202), width=2)
                draw.text((self.w // 2 - 170, self.h - 78), "TOP SECRET // CLASSIFIED SPEND", font=get_engine_font(15, bold=True), fill=(255, 255, 255))

            # 3. General Dialogue Bubble (Left, screaming in rage at t=0.3s)
            gen_scale = StickmanTimeline.bubble_spring_scale(t, t_start=0.3, pop_duration=0.45)
            if gen_scale > 0.05:
                ComicBubble.draw(
                    draw=draw,
                    x=130,
                    y=110,
                    w=550,
                    h=165,
                    tail_target=(gen_x + general_img.width - 50, gen_y + 110),
                    badge_text="GENERAL VANCE [PENTAGON]",
                    badge_color=(220, 38, 38),
                    quote_text=general_dialogue,
                    scale=gen_scale,
                    max_chars=27,
                    highlight_keywords=["1.7 TRILLION", "TRILLION", "crash", "wet", "dollars"],
                )

            # 4. Defense CEO Dialogue Bubble (Right, smug grin with cash bag at t=2.5s)
            ceo_scale = StickmanTimeline.bubble_spring_scale(t, t_start=2.5, pop_duration=0.45)
            if ceo_scale > 0.05:
                ComicBubble.draw(
                    draw=draw,
                    x=self.w - 720,
                    y=110,
                    w=560,
                    h=165,
                    tail_target=(ceo_x + 70, ceo_y + 110),
                    badge_text="DEFENSE CONTRACTOR CEO [LOCKHEED / BOEING]",
                    badge_color=(16, 185, 129),
                    quote_text=ceo_dialogue,
                    scale=ceo_scale,
                    max_chars=28,
                    highlight_keywords=["$500 Billion", "Billion", "windshield wipers", "Relax"],
                )

            proc.stdin.write(frame.tobytes())

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Crayon Military Satire render failed: {err}")

        return out_p
