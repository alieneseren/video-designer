#!/usr/bin/env python3
"""
crayon_animation_pipeline.py
============================
Broadcast-grade Dynamic Animated Stickman & Episodic Non-Repeating Documentary Engine.
Modeled after high-retention investigative channels (@BoşKafa, @Crayon_Capital, CaspianReport, Johnny Harris).

Key Architecture:
1. 16 Distinct Visual Archetypes (ZERO FORMULAIC REPETITIVE CYCLING):
   - HANGAR_WALK: Major chapter opener on airfield tarmac with host walk and footstep dust.
   - LAB_RND: Skunkworks R&D lab with engineer, laser scanning, and thermal stress test.
   - PENTAGON_AUDIT: Senate committee war room with defense CEO, cash stacks, and subpoena stamps.
   - TACTICAL_RADAR: Deep naval tactical grid, green rotating radar sweep, telemetry sidebar.
   - SPLIT_CIVIL: Side-by-side comparison (Civilian $0.15 vs Mil-Spec $4,800 hardware) with "VS" badge.
   - FLOW_CHAIN: Animated 4-stage cause and effect chain with glowing chevron arrows.
   - COCKPIT_HUD: Fighter cockpit interior with collimated HUD horizon, pitch ladder, pilot sprite.
   - TACTICAL_MAP: Geographic map with curved flight vectors, theater markers (Norway Arctic, Gulf).
   - KEN_BURNS: Real USAF aircraft photo with smooth slow zoom, vignette, and classified stamps.
   - MACRO_BLUEPRINT: CAD blueprint grid with coordinate ticks, technical cutaway, tolerance callouts.
   - EMERGENCY_LOCKDOWN: Diagonal hazard stripes, flashing siren glow, warning shield.
   - URBAN_STREET: Street background with host and tactical wall markings.
   - FINANCIAL_AUDIT: Clean financial chart with glowing animated bars, itemized pricing, deficit counters.
   - FOREIGN_INTELLIGENCE: Secret intelligence dossier with foreign spy, waveform telemetry, intercept stamp.
   - DESK_BRIEFING: Analyst tactical briefing table with digital glowing console.
   - CRT_MAINFRAME: Green phosphor CRT terminal typing actual verbatim quotes and military directives.

2. Sequential Non-Repeating Sub-Shot Scheduler:
   - No two consecutive scenes ever start with the same visual shot.
   - No two consecutive scenes have the same shot sequence.
   - HANGAR_WALK is used ONLY on major act transitions (Scenes 0, 15, 27).
   - Sahneler akışa ve anlatılan konuya göre milisaniyelik dinamizm ile değişir.
"""

import os
import sys
import json
import math
import wave
import time
import shutil
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if not (BASE_DIR / "assets").exists():
    BASE_DIR = Path("/home/ubuntu/yt-remote-worker")
if not (BASE_DIR / "assets").exists():
    BASE_DIR = Path("/Users/alienes/yt-oto-video/files")

# Assets Directories & Backgrounds
CHAR_DIR = BASE_DIR / "assets/characters/defense_finance"
SFX_DIR = BASE_DIR / "assets/sfx/crayon"
if not SFX_DIR.exists():
    SFX_DIR = BASE_DIR / "assets/sfx"

VEH_DIR = BASE_DIR / "assets/vehicles"
REAL_VEH_DIR = VEH_DIR / "real"
BG_DIR = BASE_DIR / "assets/backgrounds"

MAP_BG = BG_DIR / "boskafa_tactical_map.jpg"
HANGAR_BG = BG_DIR / "crayon_hangar_airfield.jpg"
COCKPIT_BG = BG_DIR / "crayon_cockpit_interior.jpg"
WAR_ROOM_BG = BASE_DIR / "assets/crayon_military_bg.jpg"
TECH_BG = BASE_DIR / "assets/crayon_tech_bg.jpg"
STREET_BG = BASE_DIR / "assets/crayon_street_bg.jpg"

B21_BLUEPRINT_IMG = VEH_DIR / "b21_raider_blueprint.png"
B21_FLIGHT_REAL = REAL_VEH_DIR / "b21_flight_real.jpg"
B21_ROLLOUT_REAL = REAL_VEH_DIR / "b21_rollout_real.jpg"
B21_CUTOUT_REAL = REAL_VEH_DIR / "b21_real_cutout.png"

W, H = 1920, 1080
FPS = 25

FFMPEG_BIN = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"


def get_pop_font(size: int = 38) -> ImageFont.FreeTypeFont:
    font_paths = [
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_font_safe(size: int = 24, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    font_paths = []
    if mono:
        font_paths.extend([
            "/System/Library/Fonts/Monaco.dfont",
            "/System/Library/Fonts/Courier.dfont",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ])
    if bold:
        font_paths.extend([
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ])
    font_paths.extend([
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ])
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_pop_title(draw: ImageDraw.ImageDraw, text: str):
    if not text:
        return
    f_size = 40 if len(text) < 36 else (34 if len(text) < 46 else 28)
    font = get_pop_font(f_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    t_w = bbox[2] - bbox[0]
    t_h = bbox[3] - bbox[1]

    cx, cy = W // 2, 85
    tx, ty = cx - t_w // 2, cy - t_h // 2

    # Background card
    pad_x, pad_y = 28, 12
    card_box = [(tx - pad_x, ty - pad_y), (tx + t_w + pad_x, ty + t_h + pad_y)]
    draw.rounded_rectangle(card_box, radius=12, fill=(15, 23, 42, 235), outline=(234, 179, 8), width=3)

    # Fast builtin stroke
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))



def draw_narration_subtitle(draw: ImageDraw.ImageDraw, text: str, t: float, dur: float):
    if not text or dur <= 0:
        return
    words = text.strip().split()
    if not words:
        return
    chunk_size = 7
    chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
    chunk_idx = min(len(chunks) - 1, int((t / dur) * len(chunks)))
    active_chunk = chunks[chunk_idx].upper()

    font = get_pop_font(30)
    bbox = draw.textbbox((0, 0), active_chunk, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (W - tw) // 2
    ty = H - 85

    draw.rounded_rectangle([(tx - 24, ty - 8), (tx + tw + 24, ty + th + 8)], radius=10, fill=(0, 0, 0, 195))
    draw.text((tx, ty), active_chunk, font=font, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))

def get_audio_duration(file_path: str) -> float:
    try:
        with wave.open(file_path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        pass
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        out = subprocess.check_output(cmd, text=True).strip()
        return float(out)
    except Exception:
        return 5.0


# ── CACHED GRAPHICS ASSETS ──
_CACHED_IMGS = {}


_CACHED_PHOTOS = {}
def get_cached_photo(p_img_path: Path, max_dim=(1200, 800)) -> Image.Image:
    k = str(p_img_path)
    if k not in _CACHED_PHOTOS:
        if p_img_path.exists():
            raw = Image.open(p_img_path).convert('RGBA')
            raw.thumbnail(max_dim, Image.Resampling.LANCZOS)
            _CACHED_PHOTOS[k] = raw
        else:
            _CACHED_PHOTOS[k] = Image.new('RGBA', max_dim, (15, 23, 42, 255))
    return _CACHED_PHOTOS[k]

def get_cached_bg(path: Path, target_size=(W, H)) -> Image.Image:
    k = (str(path), target_size)
    if k not in _CACHED_IMGS:
        if path.exists():
            im = Image.open(path).convert("RGBA")
            if target_size:
                im = im.resize(target_size, Image.Resampling.LANCZOS)
            _CACHED_IMGS[k] = im
        else:
            _CACHED_IMGS[k] = Image.new("RGBA", target_size, (15, 23, 42, 255))
    return _CACHED_IMGS[k]


_CACHED_POSES = {}

def get_host_pose(name: str, target_h: int = 620) -> Image.Image:
    k = (name, target_h)
    if k not in _CACHED_POSES:
        p = CHAR_DIR / f"host_{name}.png"
        if not p.exists():
            p = CHAR_DIR / f"crayon_{name}.png"
        if not p.exists():
            p = CHAR_DIR / f"{name}.png"
        if not p.exists():
            p = CHAR_DIR / "boskafa_tactical_host.png"
        if p.exists():
            raw = Image.open(p).convert("RGBA")
            sc = target_h / float(raw.height)
            nw = int(raw.width * sc)
            _CACHED_POSES[k] = raw.resize((nw, target_h), Image.Resampling.LANCZOS)
        else:
            _CACHED_POSES[k] = Image.new("RGBA", (int(target_h * 0.45), target_h), (0, 0, 0, 0))
    return _CACHED_POSES[k]


def load_character_sprite(char_role: str, target_h: int = 600) -> Image.Image:
    role_u = char_role.upper()
    file_map = {
        "HOST": "host_smug.png",
        "PILOT": "test_pilot.png",
        "GENERAL": "crayon_pentagon_general.png",
        "CEO": "crayon_defense_ceo.png",
        "SPY": "foreign_spy.png",
        "FOUNDER": "crayon_tech_founder.png",
        "TRADER": "crayon_wall_street_trader.png"
    }
    target_file = "host_smug.png"
    for k, v in file_map.items():
        if k in role_u:
            target_file = v
            break
    p = CHAR_DIR / target_file
    if not p.exists():
        alt_name = target_file.replace("crayon_", "")
        if (CHAR_DIR / alt_name).exists():
            p = CHAR_DIR / alt_name
    if p.exists():
        raw = Image.open(p).convert("RGBA")
        scale = target_h / float(raw.height)
        new_w = int(raw.width * scale)
        return raw.resize((new_w, target_h), Image.Resampling.LANCZOS)
    return Image.new("RGBA", (int(target_h * 0.45), target_h), (0, 0, 0, 0))


_CACHED_STAMPS = {}

def get_cached_stamp(text: str = "TOP SECRET", angle: int = 14) -> Image.Image:
    k = (text, angle)
    if k not in _CACHED_STAMPS:
        sw, sh = 380, 84
        s_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        sd = ImageDraw.Draw(s_img)
        sd.rectangle([(0, 0), (sw - 1, sh - 1)], outline=(220, 38, 38), width=5)
        s_font = get_pop_font(30)
        sd.text((20, 22), text, font=s_font, fill=(220, 38, 38))
        _CACHED_STAMPS[k] = s_img.rotate(angle, expand=True, resample=Image.Resampling.BILINEAR)
    return _CACHED_STAMPS[k]


def draw_footstep_dust(draw: ImageDraw.ImageDraw, foot_x: int, ground_y: int, walk_phase: float):
    strike = abs(math.sin(walk_phase))
    if strike < 0.35:
        p = 1.0 - (strike / 0.35)
        puff_r = int(14 * p)
        if puff_r > 3:
            draw.ellipse([(foot_x - puff_r - 8, ground_y - puff_r), (foot_x + puff_r - 8, ground_y + 4)], fill=(220, 225, 235, 180), outline=(100, 116, 139, 200), width=2)
            draw.ellipse([(foot_x - puff_r + 12, ground_y - int(puff_r * 0.7)), (foot_x + puff_r + 12, ground_y + 4)], fill=(240, 245, 250, 160), outline=(100, 116, 139, 180), width=1)


# ── 16 DEDICATED VISUAL ARCHETYPE RENDERERS ──

def render_hangar_walk(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_walk: Image.Image, host_smug: Image.Image):
    bg = get_cached_bg(HANGAR_BG).copy()
    frame.paste(bg, (0, 0))
    p_walk = min(1.0, t_sub / 1.8)
    hx = int(-140 + p_walk * 440)
    bob = int(abs(math.sin(t_sub * 10.0)) * 12.0 if p_walk < 1.0 else 0)
    hy = H - host_walk.height - 20 - bob
    host_cur = host_walk if p_walk < 1.0 else host_smug
    frame.alpha_composite(host_cur, (hx, hy))
    if p_walk < 1.0:
        draw_footstep_dust(draw, hx + host_cur.width // 2, H - 20, t_sub * 10.0)
    draw_pop_title(draw, sub_title)


def render_lab_rnd(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, founder_img: Image.Image, scene_data: dict):
    bg = get_cached_bg(TECH_BG).copy()
    frame.paste(bg, (0, 0))
    
    # Skunkworks laboratory console
    card_x, card_y, card_w, card_h = 600, 180, 820, 480
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=16, fill=(15, 23, 42, 235), outline=(56, 189, 248), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 60)], radius=16, fill=(14, 116, 144, 255))
    draw.text((card_x + 30, card_y + 14), "SKUNKWORKS MATERIALS R&D FACILITY // PALMDALE", font=get_pop_font(26), fill=(255, 255, 255))
    
    # Test readouts
    draw.text((card_x + 40, card_y + 90), "SPECIFICATION: MIL-STD-810H THERMAL LOAD", font=get_pop_font(24), fill=(234, 179, 8))
    draw.text((card_x + 40, card_y + 130), "SAMPLE #09: HIGH-ENTHALPY MICROCRYSTALLINE WAX", font=get_font_safe(18, mono=True), fill=(203, 213, 225))
    
    # Laser bar scanner oscillation
    laser_x = int(card_x + 100 + (math.sin(t_sub * 4.0) + 1.0) * 0.5 * (card_w - 200))
    draw.line([(laser_x, card_y + 180), (laser_x, card_y + 360)], fill=(239, 68, 68), width=4)
    
    # Live thermometer bar
    draw.rectangle([(card_x + 80, card_y + 200), (card_x + 500, card_y + 240)], fill=(30, 41, 59), outline=(148, 163, 184), width=2)
    prog = min(1.0, 0.4 + 0.5 * (t_sub / 4.0))
    fill_w = int(420 * prog)
    draw.rectangle([(card_x + 80, card_y + 200), (card_x + 80 + fill_w, card_y + 240)], fill=(239, 68, 68))
    curr_temp = int(32 + prog * 16)
    draw.text((card_x + 520, card_y + 206), f"{curr_temp}°C / {int(curr_temp * 1.8 + 32)}°F", font=get_pop_font(26), fill=(239, 68, 68))
    
    draw.text((card_x + 40, card_y + 280), "STATUS: VISCOSITY COLLAPSE DETECTED", font=get_pop_font(26), fill=(239, 68, 68))
    draw.text((card_x + 40, card_y + 330), "• Paraffin liquifies at 48°C / 98.6°F", font=get_font_safe(20), fill=(255, 255, 255))
    draw.text((card_x + 40, card_y + 370), "• Surface adhesion drops to zero", font=get_font_safe(20), fill=(255, 255, 255))
    draw.text((card_x + 40, card_y + 410), "• Defrost vents contaminated with paraffin", font=get_font_safe(20), fill=(234, 179, 8))
    
    # Place characters
    frame.alpha_composite(host_point, (60, H - host_point.height - 20))
    fx = W - founder_img.width - 60
    fy = H - founder_img.height - 20
    frame.alpha_composite(founder_img, (fx, fy))
    draw_pop_title(draw, sub_title)


def render_pentagon_audit(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_smug: Image.Image, ceo_img: Image.Image, general_img: Image.Image, scene_data: dict):
    bg = get_cached_bg(WAR_ROOM_BG).copy()
    frame.paste(bg, (0, 0))
    
    # Hearing Board
    card_x, card_y, card_w, card_h = 580, 180, 840, 500
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=16, fill=(15, 23, 42, 240), outline=(239, 68, 68), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 60)], radius=16, fill=(185, 28, 28, 255))
    draw.text((card_x + 30, card_y + 14), "HOUSE ARMED SERVICES SUBCOMMITTEE // AUDIT", font=get_pop_font(26), fill=(255, 255, 255))
    
    draw.text((card_x + 40, card_y + 85), "DEFENSE PROCUREMENT INQUIRY // FY-2026", font=get_pop_font(24), fill=(234, 179, 8))
    draw.text((card_x + 40, card_y + 130), "DEFENSE CONTRACTOR CLAIM:", font=get_font_safe(18, mono=True), fill=(148, 163, 184))
    draw.text((card_x + 40, card_y + 155), '"Aerospace Grade Tactical Marking Tool - $850.00"', font=get_pop_font(22), fill=(255, 255, 255))
    
    draw.text((card_x + 40, card_y + 205), "CONGRESSIONAL AUDIT FINDING:", font=get_font_safe(18, mono=True), fill=(239, 68, 68))
    draw.text((card_x + 40, card_y + 230), '"Identical to $0.15 Commercial Crayola Wax Formula"', font=get_pop_font(24), fill=(239, 68, 68))
    
    # Financial discrepancy
    draw.rectangle([(card_x + 40, card_y + 280), (card_x + card_w - 40, card_y + 360)], fill=(30, 41, 59), outline=(234, 179, 8), width=2)
    draw.text((card_x + 60, card_y + 295), "UNACCOUNTED SURCHARGE:", font=get_font_safe(18, mono=True), fill=(203, 213, 225))
    draw.text((card_x + 60, card_y + 322), "+5,666% TAXPAYER MARKUP", font=get_pop_font(28), fill=(234, 179, 8))
    
    stamp_img = get_cached_stamp("AUDIT REJECTED", -12)
    frame.alpha_composite(stamp_img, (card_x + card_w - 380, card_y + 160))
    
    frame.alpha_composite(host_smug, (60, H - host_smug.height - 20))
    cx = W - ceo_img.width - 60
    cy = H - ceo_img.height - 20
    frame.alpha_composite(ceo_img, (cx, cy))
    draw_pop_title(draw, sub_title)


def render_tactical_radar(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    # Dark tactical radar slate
    draw.rectangle([(0, 0), (W, H)], fill=(8, 16, 26))
    for gx in range(0, W, 80): draw.line([(gx, 0), (gx, H)], fill=(16, 32, 50), width=1)
    for gy in range(0, H, 80): draw.line([(0, gy), (W, gy)], fill=(16, 32, 50), width=1)
    
    cx, cy, r_max = 980, 540, 420
    for r in [105, 210, 315, 420]:
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(34, 197, 94, 90), width=2)
    draw.line([(cx - r_max, cy), (cx + r_max, cy)], fill=(34, 197, 94, 90), width=1)
    draw.line([(cx, cy - r_max), (cx, cy + r_max)], fill=(34, 197, 94, 90), width=1)
    
    # Sweeping radar beam
    ang = (t_sub * 2.8) % (2 * math.pi)
    bx = cx + int(math.cos(ang) * r_max)
    by = cy + int(math.sin(ang) * r_max)
    draw.line([(cx, cy), (bx, by)], fill=(74, 222, 128), width=4)
    
    # Target blips
    b1 = (cx + 160, cy - 140)
    draw.rectangle([(b1[0]-10, b1[1]-10), (b1[0]+10, b1[1]+10)], outline=(239, 68, 68), width=3)
    draw.text((b1[0] + 16, b1[1] - 8), "B-21 RAIDER // TRK-01 [ALT: 52K]", font=get_font_safe(16, mono=True), fill=(239, 68, 68))
    
    b2 = (cx - 220, cy + 80)
    draw.rectangle([(b2[0]-8, b2[1]-8), (b2[0]+8, b2[1]+8)], outline=(234, 179, 8), width=2)
    draw.text((b2[0] + 14, b2[1] - 6), "MQ-9 REAPER // FLIR THERMAL SCAN", font=get_font_safe(14, mono=True), fill=(234, 179, 8))
    
    # Telemetry Card
    draw.rounded_rectangle([(80, 160), (460, 460)], radius=12, fill=(15, 23, 42, 230), outline=(34, 197, 94), width=2)
    draw.text((100, 180), "TACTICAL RADAR TELEMETRY", font=get_pop_font(24), fill=(34, 197, 94))
    draw.text((100, 225), "MODE: AIR-TO-GROUND FLIR", font=get_font_safe(16, mono=True), fill=(203, 213, 225))
    draw.text((100, 260), f"BEARING: {int(math.degrees(ang)):03d}° // SWEEP 36 RPM", font=get_font_safe(16, mono=True), fill=(34, 197, 94))
    draw.text((100, 295), "TARGETS TRACKED: 04", font=get_font_safe(16, mono=True), fill=(203, 213, 225))
    draw.text((100, 330), "THERMAL BLOOMING: DETECTED", font=get_font_safe(16, mono=True), fill=(239, 68, 68))
    draw.text((100, 365), "NVG SATURATION: +450%", font=get_font_safe(16, mono=True), fill=(239, 68, 68))
    
    frame.alpha_composite(host_point, (60, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_split_comparison(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_shock: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(12, 18, 28))
    
    # Left Card: Civil / Normal
    lx, ly, lw, lh = 240, 180, 640, 700
    draw.rounded_rectangle([(lx, ly), (lx + lw, ly + lh)], radius=16, fill=(248, 250, 252), outline=(148, 163, 184), width=3)
    draw.rounded_rectangle([(lx, ly), (lx + lw, ly + 65)], radius=16, fill=(30, 41, 59))
    draw.text((lx + 30, ly + 16), "COMMERCIAL CIVILIAN HARDWARE (CRAYOLA)", font=get_pop_font(26), fill=(255, 255, 255))
    draw.text((lx + 40, ly + 100), "PRICE: $0.15 / UNIT", font=get_pop_font(36), fill=(34, 197, 94))
    draw.text((lx + 40, ly + 170), "• 100% Non-Toxic Paraffin & Dye", font=get_pop_font(22), fill=(15, 23, 42))
    draw.text((lx + 40, ly + 215), "• Classroom Safety Certified", font=get_pop_font(22), fill=(15, 23, 42))
    draw.text((lx + 40, ly + 260), "• Standard Commercial Storage", font=get_pop_font(22), fill=(15, 23, 42))
    draw.text((lx + 40, ly + 320), "INTENDED APPLICATION:", font=get_font_safe(18, mono=True), fill=(100, 116, 139))
    draw.text((lx + 40, ly + 350), "Paper Sketching & Civilian Marking", font=get_pop_font(24), fill=(15, 23, 42))
    
    # Right Card: Mil-Spec Absurd
    rx, ry, rw, rh = 980, 180, 740, 700
    draw.rounded_rectangle([(rx, ry), (rx + rw, ry + rh)], radius=16, fill=(15, 23, 42), outline=(239, 68, 68), width=3)
    draw.rounded_rectangle([(rx, ry), (rx + rw, ry + 65)], radius=16, fill=(220, 38, 38))
    draw.text((rx + 30, ry + 16), "PENTAGON 'TACTICAL MARKER' (MIL-SPEC)", font=get_pop_font(26), fill=(255, 255, 255))
    draw.text((rx + 40, ry + 100), "PRICE: $4,800.00 / UNIT", font=get_pop_font(36), fill=(239, 68, 68))
    draw.text((rx + 40, ry + 170), "• Contract: DOD-SPEC-810H Tactical Wax", font=get_pop_font(22), fill=(255, 255, 255))
    draw.text((rx + 40, ry + 215), "• Melts into Sludge at 48°C / 98.6°F", font=get_pop_font(22), fill=(234, 179, 8))
    draw.text((rx + 40, ry + 260), "• Massive Thermal Blooming on FLIR/NVG", font=get_pop_font(22), fill=(239, 68, 68))
    draw.text((rx + 40, ry + 305), "• Disappears under 650nm Red Cockpit Light", font=get_pop_font(22), fill=(239, 68, 68))
    draw.text((rx + 40, ry + 350), "• Drips into HVAC Vents Creating Toxic Fumes", font=get_pop_font(22), fill=(239, 68, 68))
    
    # VS Center Badge
    vs_x, vs_y = 930, 480
    draw.ellipse([(vs_x - 55, vs_y - 55), (vs_x + 55, vs_y + 55)], fill=(234, 179, 8), outline=(255, 255, 255), width=3)
    draw.text((vs_x - 24, vs_y - 20), "VS", font=get_pop_font(36), fill=(15, 23, 42))
    
    stamp_img = get_cached_stamp("32,000x MARKUP", 15)
    frame.alpha_composite(stamp_img, (rx + rw - 360, ry + 420))
    
    frame.alpha_composite(host_shock, (40, H - host_shock.height - 20))
    draw_pop_title(draw, sub_title)


def render_flow_chart(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(15, 23, 42))
    for gx in range(0, W, 80): draw.line([(gx, 0), (gx, H)], fill=(24, 36, 60), width=1)
    for gy in range(0, H, 80): draw.line([(0, gy), (W, gy)], fill=(24, 36, 60), width=1)
    
    nodes = [
        ("STAGE 1: SOLAR HEAT", "Canopy reaches 62°C greenhouse thermal load.", (56, 189, 248)),
        ("STAGE 2: LIQUEFACTION", "Paraffin melts completely at 48°C threshold.", (234, 179, 8)),
        ("STAGE 3: VENT INGESTION", "Melted wax seeps into HVAC defrost vents.", (239, 68, 68)),
        ("STAGE 4: MISSION ABORT", "Toxic acrolein smoke forces emergency abort.", (220, 38, 38)),
    ]
    
    active_idx = min(3, int(t_sub / 1.1))
    
    start_x = 480
    nw, nh = 310, 360
    spacing = 340
    
    for i, (n_title, n_desc, n_col) in enumerate(nodes):
        nx = start_x + i * spacing
        ny = 320
        is_act = (i <= active_idx)
        card_fill = (24, 36, 60) if is_act else (16, 24, 40)
        border_col = n_col if is_act else (71, 85, 105)
        border_w = 4 if i == active_idx else 2
        
        draw.rounded_rectangle([(nx, ny), (nx + nw, ny + nh)], radius=14, fill=card_fill, outline=border_col, width=border_w)
        draw.rounded_rectangle([(nx, ny), (nx + nw, ny + 55)], radius=14, fill=border_col)
        draw.text((nx + 16, ny + 14), n_title, font=get_pop_font(20), fill=(15, 23, 42) if is_act else (255, 255, 255))
        
        words = n_desc.split()
        line1 = " ".join(words[:4])
        line2 = " ".join(words[4:])
        draw.text((nx + 20, ny + 85), line1, font=get_pop_font(22), fill=(255, 255, 255))
        draw.text((nx + 20, ny + 125), line2, font=get_pop_font(22), fill=(203, 213, 225))
        
        # Arrow to next
        if i < 3:
            ax = nx + nw + 10
            ay = ny + nh // 2
            draw.line([(ax, ay), (ax + 16, ay)], fill=(234, 179, 8), width=3)
            draw.polygon([(ax + 16, ay - 6), (ax + 24, ay), (ax + 16, ay + 6)], fill=(234, 179, 8))
    
    frame.alpha_composite(host_point, (60, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_cockpit_flight_hud(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, pilot_img: Image.Image, scene_data: dict):
    bg = get_cached_bg(COCKPIT_BG).copy()
    frame.paste(bg, (0, 0))
    
    # Fighter HUD
    hud_y = int(320 + math.sin(t_sub * 3.0) * 12.0)
    draw.line([(820, hud_y), (1100, hud_y)], fill=(0, 255, 120), width=2)
    draw.text((850, hud_y - 28), "ALT: 52,400 FT // MACH 0.85", font=get_font_safe(20, mono=True), fill=(0, 255, 120))
    draw.ellipse([(930, hud_y - 30), (990, hud_y + 30)], outline=(0, 255, 120), width=2)
    
    # Blinking Master Caution
    is_flash = (int(t_sub * 2.5) % 2 == 0)
    c_fill = (220, 38, 38, 240) if is_flash else (234, 179, 8, 220)
    draw.rounded_rectangle([(140, 180), (580, 270)], radius=12, fill=c_fill, outline=(255, 255, 255), width=3)
    draw.text((160, 195), "MASTER CAUTION // FLIGHT HAZARD", font=get_pop_font(24), fill=(255, 255, 255))
    draw.text((160, 230), "COCKPIT CANOPY TEMP: 62°C (MELT)", font=get_font_safe(18, mono=True), fill=(255, 255, 255))
    
    px = int(W * 0.58)
    vib_y = int(math.sin(t_sub * 20.0) * 4.0)
    py = H - pilot_img.height + 60 + vib_y
    frame.alpha_composite(pilot_img, (px, py))
    draw_pop_title(draw, sub_title)


def render_tactical_map_theater(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    bg = get_cached_bg(MAP_BG).copy()
    frame.paste(bg, (0, 0))
    
    p1, p2 = (340, 580), (1500, 360)
    mid_x, mid_y = 920, 220
    
    p = min(1.0, t_sub / 2.0)
    num_segs = int(32 * p)
    for seg_i in range(num_segs):
        bt0, bt1 = seg_i / 32.0, (seg_i + 0.6) / 32.0
        def bez(bt):
            bx = (1 - bt)**2 * p1[0] + 2 * (1 - bt) * bt * mid_x + bt**2 * p2[0]
            by = (1 - bt)**2 * p1[1] + 2 * (1 - bt) * bt * mid_y + bt**2 * p2[1]
            return (int(bx), int(by))
        draw.line([bez(bt0), bez(bt1)], fill=(220, 38, 38), width=7)
    
    if t_sub >= 1.5:
        pin_x, pin_y = p2
        draw.ellipse([(pin_x - 18, pin_y - 45), (pin_x + 18, pin_y - 9)], fill=(220, 38, 38), outline=(255, 255, 255), width=3)
        draw.polygon([(pin_x - 14, pin_y - 20), (pin_x + 14, pin_y - 20), (pin_x, pin_y + 6)], fill=(220, 38, 38))
        draw.ellipse([(pin_x - 7, pin_y - 32), (pin_x + 7, pin_y - 18)], fill=(255, 255, 255))
        
        # Ripple circles
        rp = (t_sub - 1.5) * 60
        draw.ellipse([(pin_x - rp, pin_y - rp), (pin_x + rp, pin_y + rp)], outline=(239, 68, 68), width=2)
    
    frame.alpha_composite(host_point, (60, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_ken_burns_archival(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict, photo_tuple: tuple):
    draw.rectangle([(0, 0), (W, H)], fill=(15, 23, 42))
    for gx in range(0, W, 80): draw.line([(gx, 0), (gx, H)], fill=(24, 36, 60), width=1)
    for gy in range(0, H, 80): draw.line([(0, gy), (W, gy)], fill=(24, 36, 60), width=1)
    
    card_w, card_h = 1040, 680
    card_x, card_y = 740, 180
    draw.rectangle([(card_x + 14, card_y + 14), (card_x + card_w + 14, card_y + card_h + 14)], fill=(0, 0, 0, 180))
    draw.rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], fill=(245, 245, 240), outline=(200, 200, 190), width=4)
    
    p_img_path, p_cap, p_sub, p_stamp = photo_tuple
    if p_img_path.exists():
        base_im = get_cached_photo(p_img_path)
        base_w, base_h = card_w - 40, card_h - 110
        zoom = 1.0 + min(0.12, (t_sub / 5.0) * 0.12)
        cur_w, cur_h = int(base_w * zoom), int(base_h * zoom)
        scaled_im = base_im.resize((cur_w, cur_h), Image.Resampling.BILINEAR)
        crop_x = (cur_w - base_w) // 2
        crop_y = (cur_h - base_h) // 2
        cropped = scaled_im.crop((crop_x, crop_y, crop_x + base_w, crop_y + base_h))
        frame.alpha_composite(cropped, (card_x + 20, card_y + 20))
    
    draw.text((card_x + 30, card_y + card_h - 70), p_cap, font=get_pop_font(26), fill=(30, 41, 59))
    draw.text((card_x + 30, card_y + card_h - 36), p_sub, font=get_font_safe(16, mono=True), fill=(100, 116, 139))
    stamp_img = get_cached_stamp(p_stamp, 12)
    frame.alpha_composite(stamp_img, (card_x + card_w - 380, card_y + 40))
    
    frame.alpha_composite(host_point, (60, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_macro_blueprint(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_shock: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(10, 28, 52))
    for gx in range(0, W, 50): draw.line([(gx, 0), (gx, H)], fill=(18, 48, 86), width=1)
    for gy in range(0, H, 50): draw.line([(0, gy), (W, gy)], fill=(18, 48, 86), width=1)
    
    bx, by, bw, bh = 600, 180, 1240, 720
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=16, fill=(8, 22, 44, 240), outline=(56, 189, 248), width=3)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=16, fill=(14, 116, 144))
    draw.text((bx + 30, by + 16), "TECHNICAL BLUEPRINT // CRITICAL FAILURE MODE ANALYSIS", font=get_pop_font(28), fill=(255, 255, 255))
    
    # Blueprint crosshairs
    cx, cy = bx + 360, by + 400
    for r in [90, 180, 270]:
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(56, 189, 248, 120), width=2)
    draw.line([(cx - 300, cy), (cx + 300, cy)], fill=(56, 189, 248, 140), width=1)
    draw.line([(cx, cy - 300), (cx, cy + 300)], fill=(56, 189, 248, 140), width=1)
    
    # Pulsing failure point
    p_rad = int(35 + abs(math.sin(t_sub * 6.0)) * 20.0)
    draw.ellipse([(cx - p_rad, cy - p_rad), (cx + p_rad, cy + p_rad)], outline=(239, 68, 68), width=4)
    draw.text((cx + 50, cy - 50), "FAILURE POINT: 48°C THERMAL MELT", font=get_pop_font(24), fill=(239, 68, 68))
    
    # Specs Card
    draw.rectangle([(bx + 740, by + 100), (bx + bw - 40, by + bh - 60)], fill=(15, 23, 42), outline=(56, 189, 248), width=2)
    draw.text((bx + 760, by + 130), "MIL-SPEC MATERIAL ARCHITECTURE:", font=get_pop_font(24), fill=(234, 179, 8))
    draw.text((bx + 760, by + 180), "• Component: Mil-Spec Tactical Wax Marker", font=get_font_safe(20), fill=(255, 255, 255))
    draw.text((bx + 760, by + 225), "• Formulation: Low-Density Paraffin Base", font=get_font_safe(20), fill=(255, 255, 255))
    draw.text((bx + 760, by + 270), "• Infrared: High 850nm Thermal Blooming", font=get_font_safe(20), fill=(239, 68, 68))
    draw.text((bx + 760, by + 315), "• Contrast under 650nm Red Cockpit Light: 0%", font=get_font_safe(20), fill=(239, 68, 68))
    draw.text((bx + 760, by + 360), "• Solvent Impact: $280,000 Canopy Etching Damage", font=get_font_safe(20), fill=(239, 68, 68))
    
    frame.alpha_composite(host_shock, (60, H - host_shock.height - 20))
    draw_pop_title(draw, sub_title)


def render_emergency_lockdown(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_shock: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(20, 8, 8))
    
    # Flashing siren vignette
    is_flash = (int(t_sub * 4.0) % 2 == 0)
    if is_flash:
        draw.rectangle([(0, 0), (W, H)], fill=(185, 28, 28, 40))
        
    # Top & Bottom Hazard Caution Stripes
    stripe_w = 40
    for sx in range(-stripe_w, W + stripe_w * 2, stripe_w * 2):
        draw.polygon([(sx, 0), (sx + stripe_w, 0), (sx, 40), (sx - stripe_w, 40)], fill=(234, 179, 8))
        draw.polygon([(sx, H - 40), (sx + stripe_w, H - 40), (sx, H), (sx - stripe_w, H)], fill=(234, 179, 8))
        
    # Central Warning Badge
    cx, cy, bw, bh = 960, 500, 920, 420
    bx, by = cx - bw // 2, cy - bh // 2
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=20, fill=(15, 23, 42, 245), outline=(239, 68, 68), width=5)
    
    draw.text((bx + 160, by + 60), "CRITICAL OPERATIONAL HAZARD // SYSTEM BREACH", font=get_pop_font(34), fill=(239, 68, 68))
    draw.text((bx + 160, by + 130), "• HVAC DEFROST INGESTION WITH WAX VAPOR", font=get_pop_font(26), fill=(255, 255, 255))
    draw.text((bx + 160, by + 180), "• FLIGHT CONTROL STICK RESIDUE DETECTED", font=get_pop_font(26), fill=(234, 179, 8))
    draw.text((bx + 160, by + 230), "• NAVIGATION CHARTS RENDERED ILLEGIBLE", font=get_pop_font(26), fill=(239, 68, 68))
    draw.text((bx + 160, by + 300), "MIL-STD 810H PROTOCOL BREACH // ABORT", font=get_pop_font(30), fill=(239, 68, 68))
    
    frame.alpha_composite(host_shock, (60, H - host_shock.height - 20))
    draw_pop_title(draw, sub_title)


def render_urban_street(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    bg = get_cached_bg(STREET_BG).copy()
    frame.paste(bg, (0, 0))
    
    # Tactical Marking Overlay on building
    mx, my, mw, mh = 620, 200, 680, 500
    draw.rounded_rectangle([(mx, my), (mx + mw, my + mh)], radius=16, fill=(15, 23, 42, 235), outline=(234, 179, 8), width=3)
    draw.rounded_rectangle([(mx, my), (mx + mw, my + 60)], radius=16, fill=(202, 138, 4))
    draw.text((mx + 30, my + 14), "URBAN OPERATIONS // BUILDING ENTRY SYMBOLOGY", font=get_pop_font(24), fill=(15, 23, 42))
    
    # 4-quadrant X matrix
    cx, cy = mx + 340, my + 280
    draw.line([(cx - 160, cy - 160), (cx + 160, cy + 160)], fill=(239, 68, 68), width=8)
    draw.line([(cx - 160, cy + 160), (cx + 160, cy - 160)], fill=(239, 68, 68), width=8)
    
    draw.text((cx - 130, cy - 15), "10.02 / 04:30", font=get_pop_font(20), fill=(255, 255, 255))
    draw.text((cx + 40, cy - 15), "HAZARD: IED TRAP", font=get_pop_font(20), fill=(239, 68, 68))
    draw.text((cx - 60, cy - 130), "TF-ORCA // SQD 2", font=get_pop_font(20), fill=(56, 189, 248))
    draw.text((cx - 50, cy + 100), "0 CASUALTIES // CLR", font=get_pop_font(20), fill=(34, 197, 94))
    
    frame.alpha_composite(host_point, (60, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_financial_audit(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_shock: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(10, 16, 26))
    for gx in range(0, W, 80): draw.line([(gx, 0), (gx, H)], fill=(18, 30, 48), width=1)
    for gy in range(0, H, 80): draw.line([(0, gy), (W, gy)], fill=(18, 30, 48), width=1)
    
    bx, by, bw, bh = 540, 180, 1300, 720
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=16, fill=(15, 23, 42, 245), outline=(234, 179, 8), width=3)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=16, fill=(202, 138, 4))
    draw.text((bx + 30, by + 16), "PENTAGON DEFENSE OVERPRICING & PROCUREMENT AUDIT", font=get_pop_font(28), fill=(15, 23, 42))
    
    items = [
        ("Surface Prep Sponge (Unit)", "$0.15", "$4,800.00", 0.85),
        ("Tactical Wax Marker (Unit)", "$0.85", "$850.00", 0.65),
        ("Titanium Distress Stencil", "$12.00", "$12,000.00", 0.95),
        ("Canopy RAM Replacement", "$1,200.00", "$280,000.00", 1.0),
    ]
    
    y_pos = by + 100
    for name, c_cost, m_cost, bar_ratio in items:
        draw.text((bx + 40, y_pos), name, font=get_pop_font(22), fill=(255, 255, 255))
        draw.text((bx + 40, y_pos + 30), f"Sivil Fiyat: {c_cost}", font=get_font_safe(18, mono=True), fill=(34, 197, 94))
        draw.text((bx + 320, y_pos + 30), f"Pentagon Price: {m_cost}", font=get_pop_font(24), fill=(239, 68, 68))
        
        # Bar animation
        draw.rectangle([(bx + 660, y_pos + 20), (bx + bw - 60, y_pos + 50)], fill=(30, 41, 59), outline=(71, 85, 105), width=2)
        prog = min(1.0, (t_sub / 2.0) * bar_ratio)
        cur_w = int((bw - 760) * prog)
        draw.rectangle([(bx + 660, y_pos + 20), (bx + 660 + cur_w, y_pos + 50)], fill=(239, 68, 68))
        
        y_pos += 110
        
    stamp_img = get_cached_stamp("$68.4B BUDGET", -8)
    frame.alpha_composite(stamp_img, (bx + bw - 420, by + bh - 160))
    
    frame.alpha_composite(host_shock, (40, H - host_shock.height - 20))
    draw_pop_title(draw, sub_title)


def render_foreign_intelligence(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, spy_img: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(12, 16, 22))
    
    # Dossier Folder
    dx, dy, dw, dh = 500, 180, 880, 680
    draw.rounded_rectangle([(dx, dy), (dx + dw, dy + dh)], radius=14, fill=(226, 232, 240), outline=(148, 163, 184), width=4)
    draw.rounded_rectangle([(dx, dy), (dx + dw, dy + 60)], radius=14, fill=(51, 65, 85))
    draw.text((dx + 30, dy + 16), "FOREIGN SIGNALS INTELLIGENCE DOSSIER // DECODED", font=get_pop_font(24), fill=(255, 255, 255))
    
    draw.text((dx + 40, dy + 90), "INTERCEPTED SHIPMENT LOGISTICS:", font=get_pop_font(22), fill=(185, 28, 28))
    draw.text((dx + 40, dy + 130), "> CARGO: PALMDALE PLANT 42 TO RAMSTEIN AIR BASE", font=get_font_safe(18, mono=True), fill=(15, 23, 42))
    draw.text((dx + 40, dy + 165), "> PAYLOAD: 50,000x HIGH-HEAT WAX TACTICAL CRAYONS", font=get_font_safe(18, mono=True), fill=(15, 23, 42))
    draw.text((dx + 40, dy + 200), "> VULNERABILITY: EMITS RADIANT 850nm THERMAL GLOW", font=get_font_safe(18, mono=True), fill=(185, 28, 28))
    
    # Signal waveform oscillation
    draw.rectangle([(dx + 40, dy + 260), (dx + dw - 40, dy + 420)], fill=(15, 23, 42), outline=(34, 197, 94), width=2)
    draw.text((dx + 60, dy + 275), "INTERCEPTED RADIO TELEMETRY:", font=get_font_safe(16, mono=True), fill=(34, 197, 94))
    
    wave_pts = []
    for wx in range(dx + 60, dx + dw - 60, 6):
        wy = int(dy + 350 + math.sin((wx * 0.04) + t_sub * 8.0) * 35.0)
        wave_pts.append((wx, wy))
    for wi in range(len(wave_pts) - 1):
        draw.line([wave_pts[wi], wave_pts[wi + 1]], fill=(34, 197, 94), width=2)
        
    stamp_img = get_cached_stamp("DECODED INTERCEPT", 14)
    frame.alpha_composite(stamp_img, (dx + dw - 380, dy + 460))
    
    frame.alpha_composite(host_point, (40, H - host_point.height - 20))
    sx = W - spy_img.width - 40
    sy = H - spy_img.height - 20
    frame.alpha_composite(spy_img, (sx, sy))
    draw_pop_title(draw, sub_title)


def render_desk_briefing(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_cur: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(15, 23, 42))
    for gx in range(0, W, 80): draw.line([(gx, 0), (gx, H)], fill=(24, 36, 60), width=1)
    for gy in range(0, H, 80): draw.line([(0, gy), (W, gy)], fill=(24, 36, 60), width=1)
    
    # Holographic Briefing Table
    bx, by, bw, bh = 540, 240, 1300, 620
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=20, fill=(18, 30, 50, 240), outline=(56, 189, 248), width=3)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=20, fill=(14, 116, 144))
    draw.text((bx + 30, by + 16), "STRATEGIC AIR DOCTRINE & LESSONS LEARNED", font=get_pop_font(26), fill=(255, 255, 255))
    
    draw.text((bx + 40, by + 100), "LESSON #1: ANALOG IS ESSENTIAL WHEN TECH FAILS", font=get_pop_font(28), fill=(234, 179, 8))
    draw.text((bx + 40, by + 150), "• Satellite datalinks and GPS go dark in electronic warfare.", font=get_font_safe(22), fill=(203, 213, 225))
    draw.text((bx + 40, by + 195), "• Analog grease pencils on paper remain the ultimate failsafe.", font=get_font_safe(22), fill=(203, 213, 225))
    draw.text((bx + 40, by + 240), "• Yet buying $0.15 wax for $4,800 cripples operational readiness.", font=get_font_safe(22), fill=(239, 68, 68))
    draw.text((bx + 40, by + 310), "VERDICT: PENTAGON AUDIT FAILS SCRUTINY", font=get_pop_font(30), fill=(239, 68, 68))
    
    frame.alpha_composite(host_cur, (60, H - host_cur.height - 20))
    draw_pop_title(draw, sub_title)


def render_crt_mainframe(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(8, 16, 12))
    for y in range(0, H, 6): draw.line([(0, y), (W, y)], fill=(12, 28, 18), width=2)
    
    draw.rectangle([(100, 160), (W - 100, H - 120)], outline=(0, 255, 120), width=3)
    draw.rectangle([(100, 160), (W - 100, 220)], fill=(0, 255, 120))
    chapter = scene_data.get("chapter", "").strip().upper()
    draw.text((120, 175), f"PENTAGON SECURE TERMINAL // {chapter[:32]}", font=get_pop_font(26), fill=(8, 16, 12))
    
    narr = scene_data.get("narration", "").strip()
    words = narr.split()
    snippet_1 = " ".join(words[:10]) if len(words) >= 10 else narr
    snippet_2 = " ".join(words[10:20]) if len(words) >= 20 else ""
    log_lines = [
        f"> AUDIT CHAPTER: {chapter[:45]}",
        f"> TRANSCRIPT: {snippet_1[:50]}",
        f"> LOG: {snippet_2[:50]}" if snippet_2 else "> STATUS: CRITICAL FAILURE IDENTIFIED",
        f"> VERDICT: MIL-STD 810H PROTOCOL VIOLATION DETECTED",
        f"> CLASSIFICATION: TOP SECRET // DOD OVERSIGHT ONLY"
    ]
    t_chars = int(t_sub * 40)
    curr_chars = 0
    y_pos = 260
    font_term = get_pop_font(26)
    for line in log_lines:
        if t_chars > curr_chars:
            visible = line[:t_chars - curr_chars]
            draw.text((140, y_pos), visible, font=font_term, fill=(0, 255, 120))
        curr_chars += len(line)
        y_pos += 60
    if int(t_sub * 3) % 2 == 0:
        draw.rectangle([(140 + min(t_chars * 14, 800), y_pos - 60), (160 + min(t_chars * 14, 800), y_pos - 30)], fill=(0, 255, 120))
    draw_pop_title(draw, sub_title)


# ── BESPOKE EPISODIC NON-REPEATING SCHEDULER ──


# ── BESPOKE COMBAT SYMBOLOGY & FIASCO RENDERERS ──

def render_symbol_slash(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    bg = get_cached_bg(STREET_BG).copy()
    frame.paste(bg, (0, 0))
    
    card_x, card_y, card_w, card_h = 560, 160, 940, 680
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=18, fill=(15, 23, 42, 245), outline=(234, 179, 8), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 65)], radius=18, fill=(202, 138, 4))
    draw.text((card_x + 30, card_y + 16), "COMBAT MARKING // SYMBOL #1: SINGLE DIAGONAL SLASH", font=get_pop_font(24), fill=(15, 23, 42))
    
    cx, cy = card_x + 320, card_y + 360
    # Step-by-step diagonal stroke [/]
    p = min(1.0, t_sub / 1.2)
    x_s, y_s = cx - 140, cy + 160
    x_e, y_e = cx + 140, cy - 160
    cur_x = int(x_s + (x_e - x_s) * p)
    cur_y = int(y_s + (y_e - y_s) * p)
    draw.line([(x_s, y_s), (cur_x, cur_y)], fill=(239, 68, 68), width=12)
    
    # Legend
    lx = card_x + 520
    draw.text((lx, card_y + 110), "DOCTRINE PROTOCOL:", font=get_pop_font(22), fill=(234, 179, 8))
    draw.text((lx, card_y + 160), "• Meaning: Search & Entry in Progress", font=get_font_safe(18), fill=(255, 255, 255))
    draw.text((lx, card_y + 205), "• Placement: Left Doorframe at Eye Level", font=get_font_safe(18), fill=(255, 255, 255))
    draw.text((lx, card_y + 250), "• Rule: Never cross second slash until exit", font=get_font_safe(18), fill=(239, 68, 68))
    draw.text((lx, card_y + 295), "• Prevents duplicate room clears under fire", font=get_font_safe(18), fill=(34, 197, 94))
    
    frame.alpha_composite(host_point, (40, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_symbol_x(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    bg = get_cached_bg(STREET_BG).copy()
    frame.paste(bg, (0, 0))
    
    card_x, card_y, card_w, card_h = 560, 160, 940, 680
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=18, fill=(15, 23, 42, 245), outline=(234, 179, 8), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 65)], radius=18, fill=(202, 138, 4))
    draw.text((card_x + 30, card_y + 16), "COMBAT MARKING // 4-QUADRANT 'X' MATRIX ANATOMY", font=get_pop_font(24), fill=(15, 23, 42))
    
    cx, cy = card_x + card_w // 2, card_y + 360
    
    # Stroke 1: /
    p1 = min(1.0, t_sub / 0.8)
    x1_s, y1_s = cx - 180, cy + 180
    x1_e, y1_e = cx + 180, cy - 180
    cur_x1 = int(x1_s + (x1_e - x1_s) * p1)
    cur_y1 = int(y1_s + (y1_e - y1_s) * p1)
    draw.line([(x1_s, y1_s), (cur_x1, cur_y1)], fill=(239, 68, 68), width=10)
    
    # Stroke 2: Backslash
    if t_sub >= 0.8:
        p2 = min(1.0, (t_sub - 0.8) / 0.8)
        x2_s, y2_s = cx - 180, cy - 180
        x2_e, y2_e = cx + 180, cy + 180
        cur_x2 = int(x2_s + (x2_e - x2_s) * p2)
        cur_y2 = int(y2_s + (y2_e - y2_s) * p2)
        draw.line([(x2_s, y2_s), (cur_x2, cur_y2)], fill=(239, 68, 68), width=10)
        
    # Quadrant Data
    if t_sub >= 1.4:
        draw.rounded_rectangle([(cx - 140, cy - 240), (cx + 140, cy - 190)], radius=8, fill=(30, 41, 59), outline=(56, 189, 248), width=2)
        draw.text((cx - 120, cy - 232), "DATE: 10.02 // 04:30 HRS", font=get_font_safe(18, mono=True), fill=(56, 189, 248))
        
    if t_sub >= 2.0:
        draw.rounded_rectangle([(cx - 360, cy - 30), (cx - 190, cy + 30)], radius=8, fill=(30, 41, 59), outline=(34, 197, 94), width=2)
        draw.text((cx - 345, cy - 14), "TF-ORCA / SQD 2", font=get_font_safe(18, mono=True), fill=(34, 197, 94))
        
    if t_sub >= 2.6:
        draw.rounded_rectangle([(cx + 190, cy - 30), (cx + 420, cy + 30)], radius=8, fill=(30, 41, 59), outline=(239, 68, 68), width=2)
        draw.text((cx + 205, cy - 14), "! IED / TRIPWIRE IN HALL", font=get_font_safe(18, mono=True), fill=(239, 68, 68))
        
    if t_sub >= 3.2:
        draw.rounded_rectangle([(cx - 160, cy + 190), (cx + 160, cy + 240)], radius=8, fill=(30, 41, 59), outline=(234, 179, 8), width=2)
        draw.text((cx - 140, cy + 204), "0 VICTIMS // CLEARED", font=get_font_safe(18, mono=True), fill=(234, 179, 8))
        
    frame.alpha_composite(host_point, (40, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_symbol_hazard(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    bg = get_cached_bg(STREET_BG).copy()
    frame.paste(bg, (0, 0))
    card_x, card_y, card_w, card_h = 560, 160, 940, 680
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=18, fill=(15, 23, 42, 245), outline=(239, 68, 68), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 65)], radius=18, fill=(185, 28, 28))
    draw.text((card_x + 30, card_y + 16), "TACTICAL HAZARD RING // UXO & BOOBY TRAP PERIMETER", font=get_pop_font(24), fill=(255, 255, 255))
    
    cx, cy, r_hazard = card_x + 320, card_y + 360, 160
    draw.ellipse([(cx - r_hazard, cy - r_hazard), (cx + r_hazard, cy + r_hazard)], outline=(239, 68, 68), width=8)
    draw.ellipse([(cx - r_hazard + 14, cy - r_hazard + 14), (cx + r_hazard - 14, cy + r_hazard - 14)], outline=(234, 179, 8), width=3)
    draw.text((cx - 100, cy - 30), "! DANGER // UXO", font=get_pop_font(24), fill=(239, 68, 68))
    draw.text((cx - 120, cy + 10), "TRIPWIRE DETECTED", font=get_pop_font(22), fill=(234, 179, 8))
    
    # Safe retreat arrow
    draw.line([(cx + r_hazard + 20, cy), (cx + r_hazard + 140, cy)], fill=(34, 197, 94), width=6)
    draw.polygon([(cx + r_hazard + 140, cy - 12), (cx + r_hazard + 170, cy), (cx + r_hazard + 140, cy + 12)], fill=(34, 197, 94))
    draw.text((cx + r_hazard + 20, cy - 35), "SAFE RETREAT LANE", font=get_font_safe(16, mono=True), fill=(34, 197, 94))
    
    lx = card_x + 540
    draw.text((lx, card_y + 110), "SPECIFICATION // DOCTRINE:", font=get_pop_font(22), fill=(234, 179, 8))
    draw.text((lx, card_y + 155), "• Diameter: Exactly 2-Foot Bold Circle", font=get_font_safe(18), fill=(255, 255, 255))
    draw.text((lx, card_y + 195), "• Color: High-Visibility Wax", font=get_font_safe(18), fill=(255, 255, 255))
    draw.text((lx, card_y + 235), "• Standoff: 5 Meters Minimum Flank", font=get_font_safe(18), fill=(239, 68, 68))
    draw.text((lx, card_y + 275), "• Prevents catastrophic entry blast", font=get_font_safe(18), fill=(239, 68, 68))
    
    frame.alpha_composite(host_point, (40, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_symbol_triage(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    bg = get_cached_bg(STREET_BG).copy()
    frame.paste(bg, (0, 0))
    
    card_x, card_y, card_w, card_h = 560, 160, 940, 680
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=18, fill=(15, 23, 42, 245), outline=(34, 197, 94), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 65)], radius=18, fill=(22, 101, 52))
    draw.text((card_x + 30, card_y + 16), "TACTICAL CASUALTY TRIAGE // 4-COLOR COMBAT CROSS", font=get_pop_font(24), fill=(255, 255, 255))
    
    cx, cy = card_x + 300, card_y + 360
    arm_w, arm_l = 48, 140
    draw.rectangle([(cx - arm_w // 2, cy - arm_l), (cx + arm_w // 2, cy)], fill=(239, 68, 68))
    draw.rectangle([(cx - arm_w // 2, cy), (cx + arm_w // 2, cy + arm_l)], fill=(30, 41, 59), outline=(100, 116, 139), width=2)
    draw.rectangle([(cx - arm_l, cy - arm_w // 2), (cx, cy + arm_w // 2)], fill=(234, 179, 8))
    draw.rectangle([(cx, cy - arm_w // 2), (cx + arm_l, cy + arm_w // 2)], fill=(34, 197, 94))
    
    lx = card_x + 480
    draw.rounded_rectangle([(lx, card_y + 110), (card_x + card_w - 40, card_y + 190)], radius=8, fill=(239, 68, 68, 50), outline=(239, 68, 68), width=2)
    draw.text((lx + 20, card_y + 125), "RED ARM: IMMEDIATE PRIORITY", font=get_pop_font(20), fill=(239, 68, 68))
    draw.text((lx + 20, card_y + 155), "Arterial Bleed / Tension Pneumothorax", font=get_font_safe(16), fill=(203, 213, 225))
    
    draw.rounded_rectangle([(lx, card_y + 210), (card_x + card_w - 40, card_y + 290)], radius=8, fill=(234, 179, 8, 50), outline=(234, 179, 8), width=2)
    draw.text((lx + 20, card_y + 225), "YELLOW ARM: DELAYED EVAC", font=get_pop_font(20), fill=(234, 179, 8))
    draw.text((lx + 20, card_y + 255), "Compound Fracture / Stable Trauma", font=get_font_safe(16), fill=(203, 213, 225))
    
    draw.rounded_rectangle([(lx, card_y + 310), (card_x + card_w - 40, card_y + 390)], radius=8, fill=(34, 197, 94, 50), outline=(34, 197, 94), width=2)
    draw.text((lx + 20, card_y + 325), "GREEN ARM: MINOR INJURY", font=get_pop_font(20), fill=(34, 197, 94))
    draw.text((lx + 20, card_y + 355), "Walking Wounded / Shrapnel Superficial", font=get_font_safe(16), fill=(203, 213, 225))
    
    draw.rounded_rectangle([(lx, card_y + 410), (card_x + card_w - 40, card_y + 490)], radius=8, fill=(15, 23, 42), outline=(148, 163, 184), width=2)
    draw.text((lx + 20, card_y + 425), "BLACK ARM: EXPECTANT", font=get_pop_font(20), fill=(148, 163, 184))
    draw.text((lx + 20, card_y + 455), "Catastrophic Trauma / Non-Viable", font=get_font_safe(16), fill=(148, 163, 184))
    
    frame.alpha_composite(host_point, (40, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_symbol_breach(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    bg = get_cached_bg(STREET_BG).copy()
    frame.paste(bg, (0, 0))
    card_x, card_y, card_w, card_h = 560, 160, 940, 680
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=18, fill=(15, 23, 42, 245), outline=(234, 179, 8), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 65)], radius=18, fill=(202, 138, 4))
    draw.text((card_x + 30, card_y + 16), "BALLISTIC BREACHING ANCHOR // C4 DEMOLITION STANDOFF", font=get_pop_font(24), fill=(15, 23, 42))
    
    cx, cy = card_x + 320, card_y + 360
    # Bracket [ + ]
    draw.line([(cx - 80, cy - 100), (cx - 120, cy - 100), (cx - 120, cy + 100), (cx - 80, cy + 100)], fill=(234, 179, 8), width=6)
    draw.line([(cx + 80, cy - 100), (cx + 120, cy - 100), (cx + 120, cy + 100), (cx + 80, cy + 100)], fill=(234, 179, 8), width=6)
    draw.line([(cx - 40, cy), (cx + 40, cy)], fill=(239, 68, 68), width=8)
    draw.line([(cx, cy - 40), (cx, cy + 40)], fill=(239, 68, 68), width=8)
    
    # Blast arc
    draw.arc([(cx - 200, cy - 200), (cx + 200, cy + 200)], start=210, end=330, fill=(239, 68, 68), width=4)
    draw.text((cx - 80, cy - 180), "120° BLAST ARC", font=get_font_safe(16, mono=True), fill=(239, 68, 68))
    
    lx = card_x + 520
    draw.text((lx, card_y + 110), "DEMOLITION SPECIFICATIONS:", font=get_pop_font(22), fill=(234, 179, 8))
    draw.text((lx, card_y + 160), "• Standoff Distance: 45 cm (18 Inches)", font=get_font_safe(18), fill=(255, 255, 255))
    draw.text((lx, card_y + 205), "• Placement: Load-Bearing Rebar Anchor", font=get_font_safe(18), fill=(255, 255, 255))
    draw.text((lx, card_y + 250), "• Prevents structural ceiling collapse", font=get_font_safe(18), fill=(34, 197, 94))
    draw.text((lx, card_y + 295), "• Directs shaped charge inward into bunker", font=get_font_safe(18), fill=(239, 68, 68))
    
    frame.alpha_composite(host_point, (40, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_robot_dog_fiasco(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_shock: Image.Image, scene_data: dict):
    bg = get_cached_bg(TECH_BG).copy()
    frame.paste(bg, (0, 0))
    
    card_x, card_y, card_w, card_h = 520, 160, 980, 680
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=18, fill=(15, 23, 42, 245), outline=(239, 68, 68), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 65)], radius=18, fill=(185, 28, 28))
    draw.text((card_x + 30, card_y + 16), "PENTAGON FIELD TRIAL // ROBOTIC SYMBOLOGY UNIT", font=get_pop_font(26), fill=(255, 255, 255))
    
    sx, sy, sw, sh = card_x + 40, card_y + 90, card_w - 80, 320
    draw.rectangle([(sx, sy), (sx + sw, sy + sh)], fill=(10, 18, 30), outline=(56, 189, 248), width=2)
    
    rx, ry = sx + 320, sy + 140
    draw.rounded_rectangle([(rx, ry), (rx + 220, ry + 80)], radius=12, fill=(71, 85, 105), outline=(148, 163, 184), width=3)
    draw.rounded_rectangle([(rx + 200, ry - 30), (rx + 270, ry + 40)], radius=8, fill=(51, 65, 85), outline=(56, 189, 248), width=2)
    draw.ellipse([(rx + 240, ry - 15), (rx + 260, ry + 5)], fill=(56, 189, 248))
    draw.line([(rx + 30, ry + 80), (rx + 10, ry + 160)], fill=(100, 116, 139), width=8)
    draw.line([(rx + 180, ry + 80), (rx + 200, ry + 160)], fill=(100, 116, 139), width=8)
    draw.line([(rx + 50, ry + 80), (rx + 70, ry + 160)], fill=(71, 85, 105), width=6)
    draw.line([(rx + 160, ry + 80), (rx + 140, ry + 160)], fill=(71, 85, 105), width=6)
    
    wire_x, wire_y = rx - 60, ry + 130
    for w_i in range(8):
        ox = wire_x + w_i * 28
        draw.ellipse([(ox, wire_y - 25), (ox + 45, wire_y + 35)], outline=(203, 213, 225), width=3)
        draw.line([(ox + 10, wire_y - 20), (ox + 16, wire_y - 30)], fill=(239, 68, 68), width=2)
        draw.line([(ox + 30, wire_y + 20), (ox + 36, wire_y + 30)], fill=(239, 68, 68), width=2)
        
    draw.text((sx + 30, sy + 30), "UNIT: A-UGV 'MARKER-HOUND' #04", font=get_font_safe(18, mono=True), fill=(56, 189, 248))
    draw.text((sx + 30, sy + 60), "COST: $450,000 PER UNIT", font=get_font_safe(18, mono=True), fill=(234, 179, 8))
    draw.text((sx + sw - 280, sy + 30), "STATUS: TRAPPED (WIRE)", font=get_pop_font(20), fill=(239, 68, 68))
    
    draw.text((card_x + 50, card_y + 440), "OPERATIONAL TRIAL LOG // INCIDENT REPORT:", font=get_pop_font(22), fill=(234, 179, 8))
    draw.text((card_x + 50, card_y + 480), "• Total Battlefield Survival Time: EXACTLY 11 MINUTES", font=get_font_safe(20), fill=(255, 255, 255))
    draw.text((card_x + 50, card_y + 520), "• Rear titanium actuator entangled in standard concertina wire", font=get_font_safe(20), fill=(203, 213, 225))
    draw.text((card_x + 50, card_y + 560), "• 4 US Infantrymen had to risk sniper fire to rescue the $450K robot", font=get_font_safe(20), fill=(239, 68, 68))
    draw.text((card_x + 50, card_y + 610), "RESULT: ROBOT RETIRED // RETURN TO POCKET CRAYONS", font=get_pop_font(24), fill=(239, 68, 68))
    
    frame.alpha_composite(host_shock, (40, H - host_shock.height - 20))
    draw_pop_title(draw, sub_title)


def render_tank_day_sight(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, pilot_img: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(10, 18, 12))
    
    cx, cy, r_lens = 960, 520, 440
    draw.ellipse([(cx - r_lens, cy - r_lens), (cx + r_lens, cy + r_lens)], outline=(34, 197, 94), width=4)
    draw.ellipse([(cx - r_lens + 8, cy - r_lens + 8), (cx + r_lens - 8, cy + r_lens - 8)], outline=(16, 44, 24), width=2)
    
    draw.line([(cx - r_lens, cy), (cx + r_lens, cy)], fill=(34, 197, 94), width=2)
    draw.line([(cx, cy - r_lens), (cx, cy + r_lens)], fill=(34, 197, 94), width=2)
    for tick in range(-350, 360, 50):
        if tick != 0:
            draw.line([(cx + tick, cy - 8), (cx + tick, cy + 8)], fill=(34, 197, 94), width=2)
            draw.line([(cx - 8, cy + tick), (cx + 8, cy + tick)], fill=(34, 197, 94), width=2)
            
    wx, wy = cx + 80, cy - 40
    draw.polygon([(wx - 140, wy - 100), (wx + 180, wy - 100), (wx + 180, wy + 160), (wx - 140, wy + 160)], fill=(40, 50, 45), outline=(70, 85, 75), width=2)
    draw.line([(wx - 60, wy - 40), (wx + 20, wy), (wx - 60, wy + 40)], fill=(74, 222, 128), width=8)
    draw.line([(wx - 20, wy - 40), (wx + 60, wy), (wx - 20, wy + 40)], fill=(74, 222, 128), width=8)
    
    draw.rectangle([(wx - 80, wy - 60), (wx + 80, wy + 60)], outline=(234, 179, 8), width=3)
    draw.text((wx - 75, wy - 90), "OPTICAL MATCH // BLUE FORCE CHEVRON", font=get_font_safe(16, mono=True), fill=(234, 179, 8))
    
    draw.rounded_rectangle([(100, 180), (600, 320)], radius=12, fill=(15, 23, 42, 235), outline=(34, 197, 94), width=3)
    draw.text((120, 200), "M1A2 ABRAMS // 3x DAY SIGHT", font=get_pop_font(24), fill=(34, 197, 94))
    draw.text((120, 240), "MAIN GUN: 120mm M256 SMOOTHBORE", font=get_font_safe(16, mono=True), fill=(203, 213, 225))
    draw.text((120, 275), "TRIGGER STATUS: ABORTED (0.8s LEFT)", font=get_pop_font(20), fill=(239, 68, 68))
    
    frame.alpha_composite(pilot_img, (W - pilot_img.width - 60, H - pilot_img.height - 20))
    draw_pop_title(draw, sub_title)


V1_BESPOKE_PLAN = [
    # Scene 00: Sales Pitch
    (["HANGAR_WALK", "TACTICAL_RADAR", "SPLIT_CIVIL", "KEN_BURNS"],
     ["$68.4 BILLION PENTAGON CONTRACT!", "WHEN SATELLITE DATALINKS FAIL!", "CIVILIAN HARDWARE VS MIL-SPEC CRAYON!", "B-21 RAIDER CLASSIFIED ROLLOUT"]),
    # Scene 01: 48°C Melting Point Crisis
    (["LAB_RND", "MACRO_BLUEPRINT", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"],
     ["LAB ANALYSIS: 48°C THERMAL CRISIS!", "MOLECULAR BREAKDOWN OF PARAFFIN!", "CRITICAL ALERT: COCKPIT WAX SLUDGE!", "MARKERS MELTING IN TACTICAL VESTS!"]),
    # Scene 02: Fast Jet Cockpit Solar Radiation
    (["COCKPIT_HUD", "FLOW_CHAIN", "KEN_BURNS", "MACRO_BLUEPRINT"],
     ["SOLAR GREENHOUSE COCKPIT EFFECT!", "FROM SOLAR RADIATION TO SYSTEM CRASH!", "USAF FLIGHT TEST ARCHIVE // EDWARDS AFB", "MELTED WAX ON FLIGHT STICK!"]),
    # Scene 03: Phase Two High-Enthalpy Formulation
    (["LAB_RND", "SPLIT_CIVIL", "FINANCIAL_AUDIT", "CRT_MAINFRAME"],
     ["SKUNKWORKS: HIGH-ENTHALPY WAX FORMULA!", "STANDARD WAX VS AEROSPACE GRADE!", "$420M R&D CONTRACT AMENDMENT!", "DECLASSIFIED DEFENSE CHEMICAL PATENT"]),
    # Scene 04: Foreign Intelligence Intercept
    (["FOREIGN_INTELLIGENCE", "TACTICAL_MAP", "KEN_BURNS", "PENTAGON_AUDIT"],
     ["FOREIGN SIGNALS INTEL INTERCEPTS CARGO!", "PALMDALE TO RAMSTEIN AIR LOGISTICS", "DECLASSIFIED STRATEGIC AIRLIFT", "SENATE HEARINGS CROSS-EXAMINATION!"]),
    # Scene 05: Map Laminate Surface Prep
    (["DESK_BRIEFING", "MACRO_BLUEPRINT", "SPLIT_CIVIL", "FLOW_CHAIN"],
     ["FATAL MISTAKE #2: MAP LAMINATE GREASE!", "MICROSCOPIC SURFACE FRICTION BARRIER!", "PRISTINE CHART VS OILY KNEEBOARD", "FLIGHT CREW MISREADS TARGET GRID!"]),
    # Scene 06: Naval Strike Aviation Kneeboards
    (["TACTICAL_MAP", "COCKPIT_HUD", "KEN_BURNS", "MACRO_BLUEPRINT"],
     ["CARRIER STRIKE GROUP FLIGHT CORRIDOR!", "F/A-18 KNEEBOARD OPTICAL GLARE!", "NAVAL FLIGHT DECK OPERATIONS", "PLEXIGLAS SURFACE ABRASION CRACK"]),
    # Scene 07: The $4,800 Sponge Scandal
    (["SPLIT_CIVIL", "FINANCIAL_AUDIT", "PENTAGON_AUDIT", "CRT_MAINFRAME"],
     ["THE $4,800 AEROSPACE SPONGE SCANDAL!", "32,000X TAXPAYER MARKUP RATIO!", "DEFENSE CONTRACTOR GRILL UNDER OATH!", "DEFENSE AUDIT: CONTRACT OVERPRICING!"]),
    # Scene 08: Congress Grills the Budget / Thermal Blooming
    (["PENTAGON_AUDIT", "CRT_MAINFRAME", "TACTICAL_RADAR", "EMERGENCY_LOCKDOWN"],
     ["FATAL MISTAKE #3: INFRARED BLOOMING!", "CONGRESSIONAL SUBCOMMITTEE SUBPOENA", "THERMAL FLIR CAMERA SENSOR OVERLOAD!", "NIGHT VISION SENSOR BLINDED!"]),
    # Scene 09: Dawn Patrol Drone Thermal Cameras
    (["TACTICAL_RADAR", "MACRO_BLUEPRINT", "FOREIGN_INTELLIGENCE", "KEN_BURNS"],
     ["UAV DAWN PATROL THERMAL SURVEILLANCE!", "WAX EMITTING 850nm THERMAL GLOW!", "HOSTILE DRONE INTERCEPTS COLD TARGET!", "GLOBAL HAWK STRATEGIC FLIR RECORDING"]),
    # Scene 10: CAS Pilots Scanning Ground Markers
    (["COCKPIT_HUD", "FLOW_CHAIN", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"],
     ["CLOSE AIR SUPPORT SIGHT RETICLE BLINDED!", "THERMAL BLOOM FORCES MISSION ABORT!", "CAUTION: FLIR NIGHT VISION BLOOM!", "TACTICAL STRIKE HAZARD DETECTED!"]),
    # Scene 11: Low-Emissivity Formulation
    (["LAB_RND", "SPLIT_CIVIL", "FINANCIAL_AUDIT", "KEN_BURNS"],
     ["LOW-EMISSIVITY CARBON COMPOUND!", "STANDARD WAX VS STEALTH PENCIL!", "$850 PER PENCIL CONTRACT MODIFICATION!", "RADAR ABSORBENT MATERIAL ADHESION"]),
    # Scene 12: Map Over-Marking Clutter
    (["DESK_BRIEFING", "MACRO_BLUEPRINT", "TACTICAL_MAP", "PENTAGON_AUDIT"],
     ["FATAL MISTAKE #4: MAP OVER-MARKING!", "5 OVERLAPPING LAYERS OBSCURE THREAT RINGS!", "ACCIDENTAL PENETRATION OF SAM ENVELOPE!", "WHEN MILITARY DOCTRINE FAILS!"]),
    # Scene 13: Cockpit Tactical Display Clutter
    (["COCKPIT_HUD", "EMERGENCY_LOCKDOWN", "FLOW_CHAIN", "KEN_BURNS"],
     ["COCKPIT GLASS BLOCKED BY GREASE LINES!", "CRITICAL AVIONICS DISPLAY OCCLUSION!", "DISPLAY CLUTTER CAUSES ALTITUDE LOSS!", "NIGHT INTERDICTION MULTI-FUNCTION HUD"]),
    # Scene 14: Tiered Modular Overlays
    (["FLOW_CHAIN", "MACRO_BLUEPRINT", "SPLIT_CIVIL", "DESK_BRIEFING"],
     ["TIERED MODULAR OVERLAY DOCTRINE!", "MODULAR ACETATE THREAT OVERLAYS", "CLUTTERED CHART VS $18K OVERLAY FRAME", "JOINT CHIEFS ADOPTS NEW OVERLAY MANUAL"]),
    # Scene 15: Doctrine Analysis Midway
    (["HANGAR_WALK", "URBAN_STREET", "KEN_BURNS", "PENTAGON_AUDIT"],
     ["DOCTRINE CHECK: ALLIED FIELD INVENTORY!", "GROUND JTAC UNITS FACE CLUTTER CRISIS", "JOINT TERMINAL ATTACK CONTROLLER REPORT", "DEFENSE OFFICIALS DEFEND FIELD PROTOCOL"]),
    # Scene 16: Color-Coding Mix-Ups Under Red Light
    (["MACRO_BLUEPRINT", "SPLIT_CIVIL", "COCKPIT_HUD", "EMERGENCY_LOCKDOWN"],
     ["FATAL MISTAKE #5: COCKPIT RED-LIGHT TRAP!", "RED IN DAYLIGHT // INVISIBLE UNDER 650nm!", "MONOCHROMATIC RED LIGHT BLACKOUT!", "RESTRICTED NO-FLY ZONE LINE DISAPPEARS!"]),
    # Scene 17: Optical Illusion Night Interdiction
    (["COCKPIT_HUD", "FLOW_CHAIN", "KEN_BURNS", "DESK_BRIEFING"],
     ["LOW-LEVEL NIGHT TERRAIN INTERDICTION!", "RED LINE VANISHES -> BORDER VIOLATION!", "STEALTH BOMBER LOW-ALTITUDE PENETRATION", "THE ANATOMY OF MONOCHROMATIC BLINDNESS!"]),
    # Scene 18: Chromatic Photochromic Wax
    (["LAB_RND", "SPLIT_CIVIL", "FINANCIAL_AUDIT", "CRT_MAINFRAME"],
     ["PHOTOCHROMIC SHIFT CHEMISTRY!", "LIGHT-ADAPTIVE TACTICAL WAX!", "$2.4 BILLION CONTRACT EXPANSION!", "US PATENT OFFICE: DOD SPECIALTY WAX"]),
    # Scene 19: Norway Arctic Cold Deployment
    (["TACTICAL_MAP", "MACRO_BLUEPRINT", "KEN_BURNS", "DESK_BRIEFING"],
     ["NORWAY ARCTIC: -30°C FREEZING PROTOCOL!", "SUB-ZERO WAX CRYSTALLIZATION FRACTURE!", "NATO EXERCISE COLD RESPONSE // ARCTIC", "FROZEN OPERATIONAL TACTICAL CHARTS!"]),
    # Scene 20: Soldiers Warming Markers in Humvee Vents
    (["URBAN_STREET", "FLOW_CHAIN", "EMERGENCY_LOCKDOWN", "PENTAGON_AUDIT"],
     ["HEATING MARKERS IN HUMVEE DEFROST VENTS!", "WAX VAPORIZES INTO TOXIC ACROLEIN FUMES!", "NOXIOUS SMOKE INHALATION INCIDENT!", "CONGRESS INVESTIGATES CREW INTOXICATION!"]),
    # Scene 21: Distress Symbology Crisis
    (["URBAN_STREET", "MACRO_BLUEPRINT", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["TACTICAL DISTRESS SYMBOLOGY COLLAPSE!", "URBAN SEARCH 4-QUADRANT 'X' MATRIX!", "MISPLACED CHEVRON: FRIENDLY FIRE HAZARD!", "THE SECRET DOCTRINE OF COMBAT MARKING!"]),
    # Scene 22: Titanium Distress Stencils at $12,000
    (["SPLIT_CIVIL", "FINANCIAL_AUDIT", "PENTAGON_AUDIT", "KEN_BURNS"],
     ["THE $12,000 TITANIUM COMBAT STENCIL!", "CARDBOARD $1.50 VS CNC TITANIUM $12,000!", "CONTRACTOR DEFENDS 'BATTLEFIELD SURVIVABILITY'", "PENTAGON LOGISTICS CATALOGUE NSN-7520"]),
    # Scene 23: Muddy Trench Failure
    (["URBAN_STREET", "MACRO_BLUEPRINT", "FLOW_CHAIN", "CRT_MAINFRAME"],
     ["STENCIL CLOGGED IN MUDDY TRENCHES!", "WET SILT BONDS TO LASER-CUT APERTURES!", "ILLEGIBLE CAS COORDINATES IN COMBAT!", "COMBAT LESSONS LEARNED REPORT #883"]),
    # Scene 24: Solvent Cleanup Damaging $280K Canopies
    (["MACRO_BLUEPRINT", "FINANCIAL_AUDIT", "EMERGENCY_LOCKDOWN", "KEN_BURNS"],
     ["$280,000 JET CANOPY ETCHING DAMAGE!", "SOLVENT DISSOLVES INDIUM-TIN OXIDE RAM!", "RADAR CROSS-SECTION DEGRADED BY SOLVENT!", "CANOPY MICRO-FRACTURE DEFECT ARCHIVE"]),
    # Scene 25: Green-Tactical Eco-Solvent Contract
    (["SPLIT_CIVIL", "FINANCIAL_AUDIT", "PENTAGON_AUDIT", "CRT_MAINFRAME"],
     ["THE $640 PER CAN MIL-SPEC DECON SPRAY!", "$45 MILLION ANNUAL DECON PROCUREMENT!", "DEFENSE CONTRACTOR PROFITS SOAR!", "INSPECTOR GENERAL WASTE & ABUSE REPORT"]),
    # Scene 26: Intelligence Test: Vegetable Oil
    (["LAB_RND", "SPLIT_CIVIL", "PENTAGON_AUDIT", "DESK_BRIEFING"],
     ["INTEL TEST: $1.00 CANOLA OIL EXPERIMENT!", "$0.05 VEGETABLE OIL VS $640 PENTAGON DECON!", "IDENTICAL WAX REMOVAL, ZERO CANOPY ETCHING!", "WHEN COMMON SENSE BEATS A $68B PROGRAM!"]),
    # Scene 27: Joint Chiefs Final Verdict
    (["HANGAR_WALK", "TACTICAL_RADAR", "FINANCIAL_AUDIT", "DESK_BRIEFING"],
     ["FINAL VERDICT: THE $68.4B LESSON!", "ANALOG SIMPLICITY IN DIGITAL WARFARE!", "TAXPAYER BILLIONS SPENT ON ANALOG TOOLS!", "LESSONS FOR NEXT-GEN DEFENSE DOCTRINE!"]),
]


V2_BESPOKE_PLAN = [
    # Scene 00: Sales Pitch
    (["HANGAR_WALK", "TACTICAL_RADAR", "SPLIT_CIVIL", "URBAN_STREET"],
     ["THE $54 BILLION COMBAT SYMBOLOGY!", "WHEN SECURE DATALINKS COLLAPSE!", "ANALOG MARKER VS MULTI-MILLION TECH!", "THE CHAOTIC FOG OF URBAN WARFARE"]),
    # Scene 01: Genesis of Combat Marking
    (["URBAN_STREET", "SYMBOL_SLASH", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["BORN IN URBAN RUINS AND REBAR!", "THE ANATOMY OF SURVIVAL MARKINGS", "FROM ENTRY MARK TO EXTRACTION!", "WHY SIMPLE WAX SAVES COMBAT LIVES"]),
    # Scene 02: Symbol #1: Single Diagonal Slash
    (["SYMBOL_SLASH", "URBAN_STREET", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"],
     ["SYMBOL #1: THE SINGLE DIAGONAL SLASH!", "DENOTING 'SEARCH IN PROGRESS'", "BUILDING ENTRY IN HOSTILE SECTORS", "PREVENTING DOUBLE CLEARS UNDER FIRE!"]),
    # Scene 03: Foreign Eavesdropping Intercept
    (["FOREIGN_INTELLIGENCE", "TACTICAL_RADAR", "CRT_MAINFRAME", "PENTAGON_AUDIT"],
     ["FOREIGN INTEL INTERCEPTS ASSAULT COMMS!", "RADIO SIGNATURES TRACKED IN REAL-TIME", "DECLASSIFIED TACTICAL CHATTER", "RADIO SILENCE FORCES ANALOG MARKS!"]),
    # Scene 04: Kinetic Mechanical Marking Wand
    (["LAB_RND", "SPLIT_CIVIL", "FINANCIAL_AUDIT", "DESK_BRIEFING"],
     ["PENTAGON'S PNEUMATIC MARKING WAND!", "$14,000 PER EXTENDABLE AIR WAND!", "$340M DEFENSE CONTRACT AMENDMENT", "THE REINVENTION OF THE WAX CRAYON!"]),
    # Scene 05: Troops Throw Wand Away
    (["URBAN_STREET", "PENTAGON_AUDIT", "FLOW_CHAIN", "CRT_MAINFRAME"],
     ["TROOPS DITCH THE 8-POUND WAND!", "PNEUMATIC SEALS CLOGGED WITH DUST", "CEO DEFENDS 'OPERATIONAL ERGONOMICS'", "RETURN TO THE $0.85 POCKET CRAYON!"]),
    # Scene 06: Symbol #2: The Crossed X Matrix
    (["SYMBOL_X", "URBAN_STREET", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["SYMBOL #2: THE CROSSED 'X' MATRIX!", "FOUR QUADRANTS OF MISSION DATA", "DATE, SQUAD ID, IED HAZARDS, CASUALTIES", "THE CRITICAL LIFE-SAVING X-MARK"]),
    # Scene 07: Polycarbonate Tactical Quadrant Shield
    (["SPLIT_CIVIL", "SYMBOL_X", "PENTAGON_AUDIT", "CRT_MAINFRAME"],
     ["$6,200 BOLT-ON PLASTIC QUADRANT SHIELD!", "CNC MILLED LEXAN BRACKET CONTRACT", "OVER-ENGINEERED DEFENSE PROCUREMENT", "AUDIT SLAMS ZERO BATTLEFIELD VALUE!"]),
    # Scene 08: Drilling Concrete Under Fire
    (["URBAN_STREET", "EMERGENCY_LOCKDOWN", "SYMBOL_X", "DESK_BRIEFING"],
     ["NO TIME TO DRILL ANCHOR BOLTS UNDER FIRE!", "SNIPERS TARGET CONTRACTOR DEVICES", "THE REALITY OF ROOM-TO-ROOM BREACHING", "COMMON SENSE TRIUMPHS IN URBAN COMBAT"]),
    # Scene 09: Symbol #3: The Hazard Ring
    (["SYMBOL_HAZARD", "URBAN_STREET", "EMERGENCY_LOCKDOWN", "TACTICAL_RADAR"],
     ["SYMBOL #3: THE TWO-FOOT HAZARD RING!", "MARKING UNEXPLODED ORDNANCE & BOOBY TRAPS", "WARNING APPROACHING SQUADS: DO NOT ENTER!", "PREVENTING CATASTROPHIC BLAST CASUALTIES"]),
    # Scene 10: Symbol #4: Safe Corridor Chevron
    (["URBAN_STREET", "MACRO_BLUEPRINT", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["SYMBOL #4: THE CLEAN PATH CHEVRON!", "GUIDING CAS EVACUATION THROUGH DEBRIS", "STANDARDIZED ARROW TOWARD SAFE EXTRACTION", "SPEEDING EVACUATION UNDER ARTILLERY FIRE"]),
    # Scene 11: Retro-Reflective Glass Beads
    (["LAB_RND", "SPLIT_CIVIL", "FINANCIAL_AUDIT", "COCKPIT_HUD"],
     ["RETRO-REFLECTIVE GLASS MICRO-BEADS!", "AVIATOR NIGHT VISION ILLUMINATION", "$220 PER RETRO-REFLECTIVE CANISTER", "VISIBLE AT 3,000 FEET ALTITUDE!"]),
    # Scene 12: Enemy Snipers Exploit Reflections
    (["COCKPIT_HUD", "EMERGENCY_LOCKDOWN", "FLOW_CHAIN", "PENTAGON_AUDIT"],
     ["ENEMY SNIPERS SPOT REFLECTIVE CHEVRONS!", "WHITE LIGHT ILLUMINATION REVEALS SQUADS", "TACTICAL TRAP: RETRO-BEADS DISCARDED", "NIGHT INFILTRATION COMPROMISED!"]),
    # Scene 13: Symbol #5: The Triage Cross
    (["SYMBOL_TRIAGE", "URBAN_STREET", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["SYMBOL #5: FOUR-COLOR TRIAGE CROSS!", "GREEN, YELLOW, RED, BLACK PRIORITIES", "SECONDS DETERMINE BATTLEFIELD SURVIVAL", "DIRECTING FLIGHT SURGEONS IN SECONDS"]),
    # Scene 14: Biosensing Medical Wax
    (["LAB_RND", "SPLIT_CIVIL", "SYMBOL_TRIAGE", "CRT_MAINFRAME"],
     ["PATENTED BIOSENSING ENZYMATIC WAX!", "WAX TURNS PURPLE ON ARTERIAL BLEEDING", "$4,200 PER MEDICAL TRIAGE CRAYON", "THE $1.8 BILLION BIOTECH PROGRAM"]),
    # Scene 15: Enzymes Denature in Humidity
    (["FOREIGN_INTELLIGENCE", "LAB_RND", "PENTAGON_AUDIT", "DESK_BRIEFING"],
     ["ENZYMES EXPIRE IN TROPICAL HUMIDITY!", "FOREIGN MEDICAL CORPS TESTS SAMPLES", "PENTAGON GRILLED OVER EXPIRED BIO-WAX", "DOCTORS DEMAND SIMPLE ANALOG COLOR"]),
    # Scene 16: Symbol #6: Ballistic Breaching Anchor
    (["SYMBOL_BREACH", "MACRO_BLUEPRINT", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["SYMBOL #6: BALLISTIC BREACHING ANCHOR!", "C4 DEMOLITION STANDOFF BRACKET", "MARKING LOAD-BEARING PILLARS", "CALCULATING SHAPED-CHARGE BLAST ARCS"]),
    # Scene 17: Demolition Standoff Marking
    (["URBAN_STREET", "SYMBOL_BREACH", "MACRO_BLUEPRINT", "PENTAGON_AUDIT"],
     ["DEMO TEAMS INSCRIBE C4 STANDOFF ON REBAR", "PROTECTING BREACHERS FROM WALL COLLAPSE", "MINIMUM SAFE DISTANCE CALCULATIONS", "TACTICAL PRECISION SAVES ENTRY SQUADS"]),
    # Scene 18: Ultrasonic Resonant Wax Inscriber
    (["LAB_RND", "SPLIT_CIVIL", "FINANCIAL_AUDIT", "CRT_MAINFRAME"],
     ["ULTRASONIC RESONANT CONCRETE INSCRIBER!", "ENGRAVING WAX INTO STONE IN 0.3 SECONDS", "$18,500 PER ULTRASONIC TRANSDUCER", "HIGH-FREQUENCY ACOUSTIC OVER-ENGINEERING"]),
    # Scene 19: Transducers Shatter in Combat
    (["URBAN_STREET", "EMERGENCY_LOCKDOWN", "PENTAGON_AUDIT", "DESK_BRIEFING"],
     ["PIEZOELECTRIC TRANSDUCERS CRACK IN DUST", "BATTERIES EXPLODE UNDER RIFLE RECOIL", "CONTRACTOR CANCELS ULTRASONIC PROGRAM", "BACK TO DRAWING BY HAND ON CONCRETE"]),
    # Scene 20: Symbol #7: The Hollow Diamond
    (["COCKPIT_HUD", "TACTICAL_MAP", "URBAN_STREET", "DESK_BRIEFING"],
     ["SYMBOL #7: THE HOLLOW CASUALTY DIAMOND!", "EXTRACTION ROOFTOP LANDING ZONE", "MEDEVAC PILOTS ACQUIRE CASUALTY LZ", "SAFE CORRIDOR FOR BLACK HAWK INGRESS"]),
    # Scene 21: AR Tactical HUD Glasses
    (["LAB_RND", "COCKPIT_HUD", "FINANCIAL_AUDIT", "PENTAGON_AUDIT"],
     ["AUGMENTED REALITY SYMBOLOGY EYEWEAR!", "PROJECTING FLOATING HUD CHEVRONS", "$68,000 PER INTEGRATED GOGGLE SET", "$8.2 BILLION CONTRACT ALLOCATION"]),
    # Scene 22: Cyber Jamming Drains AR Batteries
    (["FOREIGN_INTELLIGENCE", "CRT_MAINFRAME", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"],
     ["ELECTRONIC WARFARE DRAINS AR HEADSETS!", "LITHIUM BATTERIES OVERHEAT IN 20 MINUTES", "SOLDIERS BLINDED BY DISPLAY GLITCHES", "THE FRAGILITY OF DIGITAL COMBAT SENSORS"]),
    # Scene 23: The Declassified Urban Raid
    (["URBAN_STREET", "TANK_SIGHT", "FLOW_CHAIN", "KEN_BURNS"],
     ["CASE STUDY: THE NEAR FRIENDLY-FIRE RAID!", "SPECIAL FORCES SQUAD PINNED IN BASEMENT", "RADIO ANTENNA SHOT AWAY BY ENEMY FIRE", "ANALOG MARK ON CORNER WALL ONLY DEFENSE"]),
    # Scene 24: M1 Abrams Tank Approaches
    (["TANK_SIGHT", "URBAN_STREET", "EMERGENCY_LOCKDOWN", "COCKPIT_HUD"],
     ["M1 ABRAMS TANK ROLLS INTO INTERSECTION!", "TURRET TRAVERSES TOWARD THE BASEMENT", "120mm HIGH-EXPLOSIVE ROUND LOADED", "SECTOR MISIDENTIFIED AS ENEMY BUNKER!"]),
    # Scene 25: Day Sight Identifies Friendly Chevron
    (["TANK_SIGHT", "URBAN_STREET", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["GUNNER SPOTS TACTICAL WAX CHEVRON!", "3-POWER OPTICAL DAY SIGHT SEES MARK", "TRIGGER ABORTED WITH 0.8 SECONDS LEFT!", "SIMPLE $0.85 MARKER PREVENTS TRAGEDY"]),
    # Scene 26: Corporate PR Spins Incident
    (["PENTAGON_AUDIT", "FINANCIAL_AUDIT", "SPLIT_CIVIL", "NEWS_ARCHIVE"],
     ["CONTRACTORS SPIN NEAR-MISS INTO PR WIN!", "'BLUE FORCE WAX PREVENTS TANK CASUALTIES'", "NEW $3.4 BILLION 'FRIENDLY MARK' PUSH", "CONGRESS QUESTIONS AUDIT TRANSPARENCY"]),
    # Scene 27: Intel Tests $1 Crayon vs $850 Kit
    (["FOREIGN_INTELLIGENCE", "SPLIT_CIVIL", "PENTAGON_AUDIT", "DESK_BRIEFING"],
     ["COMMERCIAL GREASE PENCIL IDENTICAL IN LAB", "ZERO DIFFERENCE UNDER 120mm TANK OPTICS", "THE SAME WAX FORMULA SOLD TO PRESCHOOLS", "HOW DEFENSE CONTRACTORS FLEECE AUDITS"]),
    # Scene 28: CSAR Pilot Rescue Symbology
    (["COCKPIT_HUD", "TACTICAL_MAP", "URBAN_STREET", "DESK_BRIEFING"],
     ["CSAR DOWNED PILOT EXTRACTION DOCTRINE", "SURVIVAL EVASION AND RECOVERY MARKS", "SEARCH PATTERNS ON ENEMY BORDERLINES", "THE CRITICAL VALUE OF GROUND SYMBOLOGY"]),
    # Scene 29: Autonomous Robot Dog Marking
    (["LAB_RND", "SPLIT_CIVIL", "ROBOT_DOG", "PENTAGON_AUDIT"],
     ["AUTONOMOUS ROBOT DOG SYMBOLOGY SQUAD!", "$450,000 PER ROBOT MARKING PLATFORM", "EQUIPPED WITH DUAL-AXIS WAX ENGRAVERS", "THE ABSURD SUMMIT OF OVER-ENGINEERING"]),
    # Scene 30: Robot Trapped in Razor Wire
    (["HANGAR_WALK", "ROBOT_DOG", "FINANCIAL_AUDIT", "DESK_BRIEFING"],
     ["ROBOT DOG LASTS 11 MINUTES IN FIELD!", "LEGS TANGLED IN CONCERTINA RAZOR WIRE", "SOLDIERS RISK LIVES TO RESCUE ROBOT!", "FINAL LESSON: SIMPLICITY RULES THE BATTLEFIELD"]),
]

def select_scene_subshots(scene_data: dict, idx: int, dur: float, vehicle_name: str) -> Tuple[List[str], List[str]]:
    narr = scene_data.get("narration", "").lower()
    ch = scene_data.get("chapter", "").lower()
    v_str = (vehicle_name + " " + narr + " " + ch).lower()

    is_v2 = any(w in v_str for w in ["combat marking", "symbology", "54", "slash", "quadrant", "chevron", "triage", "breaching", "anchor", "robot dog"])
    if is_v2 and idx < len(V2_BESPOKE_PLAN):
        return V2_BESPOKE_PLAN[idx]

    if not is_v2 and idx < len(V1_BESPOKE_PLAN):
        return V1_BESPOKE_PLAN[idx]
        
    # Generic intelligent episodic generator for Video 2 and beyond
    narr = scene_data.get("narration", "").lower()
    ch = scene_data.get("chapter", "").lower()
    t = narr + " " + ch
    
    # 4 distinct archetypes per scene, shifting by index so no repeats
    pools = [
        ["URBAN_STREET", "MACRO_BLUEPRINT", "FLOW_CHAIN", "DESK_BRIEFING"],
        ["SPLIT_CIVIL", "FINANCIAL_AUDIT", "PENTAGON_AUDIT", "KEN_BURNS"],
        ["TACTICAL_RADAR", "COCKPIT_HUD", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"],
        ["LAB_RND", "MACRO_BLUEPRINT", "FOREIGN_INTELLIGENCE", "CRT_MAINFRAME"],
        ["TACTICAL_MAP", "COCKPIT_HUD", "KEN_BURNS", "PENTAGON_AUDIT"],
    ]
    
    p = pools[idx % len(pools)]
    titles = [
        f"{scene_data.get('chapter', vehicle_name)[:28].upper()}: DETAY!",
        "PENTAGON DECLASSIFIED DOSSIER!",
        "CRITICAL OPERATIONAL HAZARD!",
        "STRATEGIC COMBAT DOCTRINE!"
    ]
    return p, titles


def mix_scene_audio(narration_wav: Path, sfx_events: list, output_wav: Path, speaker_side: str = "CENTER"):
    pan_str = "pan=stereo|c0=0.707*c0|c1=0.707*c0"
    valid_sfx = [(p, d, v) for p, d, v in sfx_events if p.exists()]
    if not valid_sfx:
        cmd = [FFMPEG_BIN, "-y", "-i", str(narration_wav), "-af", pan_str, "-c:a", "pcm_s16le", str(output_wav)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return

    cmd = [FFMPEG_BIN, "-y", "-i", str(narration_wav)]
    filter_inputs = ["[vocal]"]
    filter_parts = [f"[0:a]{pan_str}[vocal];"]

    for i, (sfx_p, delay_s, vol) in enumerate(valid_sfx):
        cmd.extend(["-i", str(sfx_p)])
        delay_ms = max(0, int(delay_s * 1000))
        filter_parts.append(f"[{i+1}:a]adelay={delay_ms}|{delay_ms},volume={vol},aformat=channel_layouts=stereo[sfx{i}];")
        filter_inputs.append(f"[sfx{i}]")

    n_in = len(filter_inputs)
    joined_inputs = "".join(filter_inputs)
    filter_parts.append(f"{joined_inputs}amix=inputs={n_in}:duration=first:dropout_transition=0:normalize=0[aout]")

    cmd.extend([
        "-filter_complex", "".join(filter_parts),
        "-map", "[aout]",
        "-c:a", "pcm_s16le",
        str(output_wav)
    ])
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def render_animated_scene(
    scene_data: dict,
    wav_path: Path,
    output_mp4: Path,
    vehicle_name: str,
    idx: int,
    total_scenes: int = 28
):
    dur = get_audio_duration(str(wav_path))
    total_frames = max(25, int(dur * FPS))

    subshots, titles = select_scene_subshots(scene_data, idx, dur, vehicle_name)
    sub_dur = dur / float(len(subshots))

    # SFX events
    sfx_events = []
    whoosh_f = SFX_DIR / "whoosh.mp3"
    pop_f = SFX_DIR / "pop.mp3"
    cash_f = SFX_DIR / "cash_register.wav"
    stamp_f = SFX_DIR / "stamp.wav"
    sonar_f = SFX_DIR / "sonar_ping.wav"

    if whoosh_f.exists(): sfx_events.append((whoosh_f, 0.05, 0.40))
    if pop_f.exists(): sfx_events.append((pop_f, 0.50, 0.50))

    for s_i, stype in enumerate(subshots):
        st_t = s_i * sub_dur
        if s_i > 0 and whoosh_f.exists(): sfx_events.append((whoosh_f, st_t, 0.35))
        if "FINANCIAL" in stype and cash_f.exists(): sfx_events.append((cash_f, st_t + 0.5, 0.45))
        elif stype == "KEN_BURNS" and stamp_f.exists(): sfx_events.append((stamp_f, st_t + 0.5, 0.50))
        elif ("RADAR" in stype or "MAP" in stype or "COCKPIT" in stype) and sonar_f.exists(): sfx_events.append((sonar_f, st_t + 0.7, 0.35))

    mixed_wav = wav_path.parent / f"mixed_{wav_path.name}"
    try:
        mix_scene_audio(wav_path, sfx_events, mixed_wav, speaker_side="CENTER")
    except Exception:
        mixed_wav = wav_path

    # Preload Character Poses
    host_walk = get_host_pose("walking", 620)
    host_point = get_host_pose("pointing", 620)
    host_shock = get_host_pose("shocked", 620)
    host_smug = get_host_pose("smug", 620)
    
    general_img = load_character_sprite("GENERAL", 580)
    pilot_img = load_character_sprite("PILOT", 680)
    ceo_img = load_character_sprite("CEO", 540)
    founder_img = load_character_sprite("FOUNDER", 540)
    spy_img = load_character_sprite("SPY", 600)

    # Real photos pool to rotate
    photos_pool = [
        (B21_FLIGHT_REAL, "USAF FLIGHT TEST ARCHIVE // EDWARDS AFB", "AIRCRAFT: B-21 RAIDER SERIAL AF-21-001", "TOP SECRET"),
        (B21_ROLLOUT_REAL, "PALMDALE PLANT 42 ROLLOUT SPECIFICATION", "AUDIT: RADAR ABSORBENT COATING ADHESION", "DECLASSIFIED"),
        (B21_BLUEPRINT_IMG, "TECHNICAL BLUEPRINT DRAFTING ARCHIVE", "SCHEMATIC: MIL-STD 810H THERMAL SPEC", "SPEC FAILED"),
        (B21_CUTOUT_REAL, "USAF WEAPONS INTEGRATION MATRIX", "PAYLOAD: STANDOFF CRUISE MISSILE INTERFACE", "CRITICAL FLAW"),
    ]

    cmd = [
        FFMPEG_BIN, "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgba", "-r", str(FPS),
        "-i", "-",
        "-i", str(mixed_wav),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_mp4)
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    for f_idx in range(total_frames):
        t = f_idx / float(FPS)
        s_i = min(len(subshots) - 1, int(t / sub_dur))
        t_sub = t - (s_i * sub_dur)
        sub_type = subshots[s_i]
        sub_title = titles[s_i]

        frame = Image.new("RGBA", (W, H), (15, 23, 42, 255))
        draw = ImageDraw.Draw(frame)

        if sub_type == "HANGAR_WALK":
            render_hangar_walk(frame, draw, t_sub, sub_title, host_walk, host_smug)
        elif sub_type == "LAB_RND":
            render_lab_rnd(frame, draw, t_sub, sub_title, host_point, founder_img, scene_data)
        elif sub_type == "PENTAGON_AUDIT":
            render_pentagon_audit(frame, draw, t_sub, sub_title, host_smug, ceo_img, general_img, scene_data)
        elif sub_type == "TACTICAL_RADAR":
            render_tactical_radar(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "SPLIT_CIVIL":
            render_split_comparison(frame, draw, t_sub, sub_title, host_shock, scene_data)
        elif sub_type == "FLOW_CHAIN":
            render_flow_chart(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "COCKPIT_HUD":
            render_cockpit_flight_hud(frame, draw, t_sub, sub_title, pilot_img, scene_data)
        elif sub_type == "TACTICAL_MAP":
            render_tactical_map_theater(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "KEN_BURNS":
            p_tuple = photos_pool[(idx + s_i) % len(photos_pool)]
            render_ken_burns_archival(frame, draw, t_sub, sub_title, host_point, scene_data, p_tuple)
        elif sub_type == "MACRO_BLUEPRINT":
            render_macro_blueprint(frame, draw, t_sub, sub_title, host_shock, scene_data)
        elif sub_type == "EMERGENCY_LOCKDOWN":
            render_emergency_lockdown(frame, draw, t_sub, sub_title, host_shock, scene_data)
        elif sub_type == "URBAN_STREET":
            render_urban_street(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "FINANCIAL_AUDIT":
            render_financial_audit(frame, draw, t_sub, sub_title, host_shock, scene_data)
        elif sub_type == "FOREIGN_INTELLIGENCE":
            render_foreign_intelligence(frame, draw, t_sub, sub_title, host_point, spy_img, scene_data)
        elif sub_type == "DESK_BRIEFING":
            render_desk_briefing(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "SYMBOL_SLASH":
            render_symbol_slash(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "SYMBOL_X":
            render_symbol_x(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "SYMBOL_HAZARD":
            render_symbol_hazard(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "SYMBOL_TRIAGE":
            render_symbol_triage(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "SYMBOL_BREACH":
            render_symbol_breach(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "ROBOT_DOG":
            render_robot_dog_fiasco(frame, draw, t_sub, sub_title, host_shock, scene_data)
        elif sub_type == "TANK_SIGHT":
            render_tank_day_sight(frame, draw, t_sub, sub_title, pilot_img, scene_data)
        else: # CRT_MAINFRAME
            render_crt_mainframe(frame, draw, t_sub, sub_title, scene_data)

        # Broadcast narration subtitles
        narr_str = scene_data.get("narration", "")
        if narr_str:
            draw_narration_subtitle(draw, narr_str, t, dur)

        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()


def format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100: cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_broadcast_ass_subtitles(scenes: list, mat_dir: Path, ass_path: Path):
    header = """[Script Info]
Title: Tactical Crayon Investigative Documentary
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CrayonDoc,Impact,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,2,60,60,65,1
Style: CrayonSpeaker,Arial,30,&H001ED760,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,60,60,125,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    current_time = 0.0

    for i, sc in enumerate(scenes):
        wav_path = mat_dir / f"scene_{i}_audio.wav"
        if not wav_path.exists():
            wav_path = mat_dir / f"scene_{i+1:02d}.wav"
        dur = get_audio_duration(str(wav_path)) if wav_path.exists() else 6.0

        narration = sc.get("narration", "").strip()
        speaker = sc.get("speaker", "SUNUCU")
        if not narration:
            current_time += dur
            continue

        words = narration.split()
        chunk_size = 7
        chunks = [" ".join(words[j:j+chunk_size]) for j in range(0, len(words), chunk_size)]
        chunk_dur = dur / float(len(chunks))

        for c_idx, chunk in enumerate(chunks):
            st = current_time + (c_idx * chunk_dur)
            et = st + chunk_dur
            st_str = format_ass_time(st)
            et_str = format_ass_time(et)

            text_clean = chunk.replace('"', '\"').upper()
            text_styled = f"{{\\fade(100,100)}}{text_clean}"
            events.append(f"Dialogue: 0,{st_str},{et_str},CrayonDoc,,0,0,0,,{text_styled}")

        current_time += dur

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))


def render_full_animated_crayon_video(mat_dir: Path, dest_dir: Path) -> Path:
    start_total = time.time()
    dest_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = dest_dir / "temp_animated_scenes"
    temp_dir.mkdir(parents=True, exist_ok=True)

    mat_json_path = mat_dir / "material.json"
    if not mat_json_path.exists():
        mat_json_path = mat_dir / "storyboard.json"

    with open(mat_json_path, "r", encoding="utf-8") as f:
        mat_data = json.load(f)

    scenes = mat_data.get("scenes", [])
    vehicle_name = mat_data.get("vehicle_name", "B-21 Raider")
    total_scenes = len(scenes)

    print(f"🎬 [Bespoke Non-Repeating Documentary Engine] '{mat_data.get('title', 'Video')}' starting 16-archetype non-repeating production ({total_scenes} sahne)...")

    rendered_scene_mp4s = []
    total_vid_dur = 0.0

    for idx, sc in enumerate(scenes):
        wav_path = mat_dir / f"scene_{idx}_audio.wav"
        if not wav_path.exists():
            wav_path = mat_dir / f"scene_{idx+1:02d}.wav"

        dur = get_audio_duration(str(wav_path)) if wav_path.exists() else 5.0
        total_vid_dur += dur

    print(f"⏱️ Total Video Duration: {total_vid_dur:.1f}s ({total_vid_dur/60.0:.2f} dakika)")

    for idx, sc in enumerate(scenes):
        scene_mp4 = temp_dir / f"scene_{idx:02d}_anim.mp4"
        wav_path = mat_dir / f"scene_{idx}_audio.wav"
        if not wav_path.exists():
            wav_path = mat_dir / f"scene_{idx+1:02d}.wav"

        t0 = time.time()
        render_animated_scene(sc, wav_path, scene_mp4, vehicle_name, idx, total_scenes=total_scenes)
        dt = time.time() - t0
        dur = get_audio_duration(str(wav_path)) if wav_path.exists() else 5.0
        print(f"  ✨ Sahne {idx+1}/{total_scenes} rendered ({dur:.1f}s, render: {dt:.2f}s)")
        rendered_scene_mp4s.append(scene_mp4)

    # Concat
    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in rendered_scene_mp4s:
            f.write(f"file '{p.resolve()}'\n")

    # Direct Stream Concat with Background Music Mix
    bgm_path = BASE_DIR / "assets/music/investigative_synthwave.mp3"
    if not bgm_path.exists():
        bgm_path = BASE_DIR / "assets/music/action_tense.mp3"
    if not bgm_path.exists():
        bgm_candidates = list((BASE_DIR / "assets/music").glob("*.mp3")) if (BASE_DIR / "assets/music").exists() else []
        bgm_path = bgm_candidates[0] if bgm_candidates else None

    final_output = dest_dir / "final.mp4"
    print("🎵 Mixing audio, SFX, and background music into final broadcast cut...")

    if bgm_path and bgm_path.exists():
        cmd_final = [
            FFMPEG_BIN, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
            "-stream_loop", "-1", "-i", str(bgm_path),
            "-filter_complex", "[1:a]volume=0.08[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]",
            "-map", "0:v",
            "-map", "[a_out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(final_output)
        ]
    else:
        cmd_final = [
            FFMPEG_BIN, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
            "-c", "copy",
            str(final_output)
        ]

    subprocess.run(cmd_final, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Cleanup temp scenes
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    total_time = time.time() - start_total
    fsize_mb = final_output.stat().st_size / (1024 * 1024)
    print(f"🎉 [COMPLETED] Broadcast video ready: {final_output.name} ({fsize_mb:.2f} MB, {total_vid_dur/60.0:.2f} dk, toplam: {total_time:.1f}s)")
    return final_output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Episodic Non-Repeating Documentary Engine")
    parser.add_argument("--mat-dir", required=True, help="Material directory path")
    parser.add_argument("--dest-dir", required=True, help="Destination directory path")
    args = parser.parse_args()

    render_full_animated_crayon_video(Path(args.mat_dir), Path(args.dest_dir))
