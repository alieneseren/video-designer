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
import textwrap
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if not (BASE_DIR / "assets").exists():
    BASE_DIR = Path(__file__).resolve().parent.parent
if not (BASE_DIR / "assets").exists():
    BASE_DIR = Path("/home/ubuntu/yt-remote-worker")
if not (BASE_DIR / "assets").exists():
    BASE_DIR = Path("/Users/alienes/yt-oto-video/files")

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR / "src") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "src"))

# Assets Directories & Backgrounds
CHAR_DIR = BASE_DIR / "assets/characters/defense_finance"
BOSKAFA_DIR = BASE_DIR / "assets/boskafa"
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


_CURRENT_CHANNEL_ID = ""
_CURRENT_TOPIC_CATEGORY = ""

def set_current_channel_id(channel_id: str, topic_category: str = ""):
    global _CURRENT_CHANNEL_ID, _CURRENT_TOPIC_CATEGORY
    _CURRENT_CHANNEL_ID = channel_id.strip().lower() if channel_id else ""
    _CURRENT_TOPIC_CATEGORY = topic_category.strip().lower() if topic_category else ""


_SPRITE_CACHE = {}

def get_clean_boskafa_sprite(pose: str, t: float = 0.0, is_speaking: bool = True, target_h: int = 640) -> Image.Image:
    # 1. Natural discrete blinking: blinks every 3.0s for exactly 0.12s (3 frames)
    blink_cycle = t % 3.0
    is_blinking = (blink_cycle < 0.12)

    # 2. Speaking lip-sync: alternates open and closed mouth in rhythm with speech
    if is_speaking:
        mouth_open = (int(t * 7.5) % 3 != 0)
    else:
        mouth_open = False

    if pose == "pointing":
        if is_blinking:
            fname = "pointing_blink_open.png" if mouth_open else "pointing_blink_closed.png"
        else:
            fname = "pointing_open.png" if mouth_open else "pointing_closed.png"
    elif pose == "walking":
        fname = "walking_blink.png" if is_blinking else "walking_open.png"
    elif pose == "shocked":
        fname = "shocked_blink.png" if is_blinking else "shocked_open.png"
    elif pose == "smug":
        fname = "smug_blink.png" if is_blinking else "smug_open.png"
    else:
        fname = "pointing_open.png"

    cache_key = (_CURRENT_CHANNEL_ID, fname, target_h)
    if cache_key in _SPRITE_CACHE:
        return _SPRITE_CACHE[cache_key]

    p = None
    if _CURRENT_CHANNEL_ID:
        chan_p = CHAR_DIR.parent / _CURRENT_CHANNEL_ID / fname
        if chan_p.exists():
            p = chan_p

    if not p or not p.exists():
        p = BOSKAFA_DIR / fname
    if not p.exists():
        p = BOSKAFA_DIR / f"{pose}.png"

    if p.exists():
        img = Image.open(p).convert("RGBA")
        ratio = target_h / float(img.height)
        new_w = max(10, int(img.width * ratio))
        scaled = img.resize((new_w, target_h), Image.Resampling.LANCZOS)
        _SPRITE_CACHE[cache_key] = scaled
        return scaled
    return Image.new("RGBA", (int(target_h * 0.45), target_h), (0, 0, 0, 0))


_CACHED_POSES = {}

def get_host_pose(name: str, target_h: int = 620, t: float = 0.0, is_speaking: bool = True) -> Image.Image:
    # If Boş Kafa sprite pack is available, use razor-sharp discrete animated stickman
    if BOSKAFA_DIR.exists():
        sp = get_clean_boskafa_sprite(name, t=t, is_speaking=is_speaking, target_h=target_h)
        if sp.width > 20 and sp.height > 20:
            return sp

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


def draw_notebook_paper(draw: ImageDraw.ImageDraw, punch_in: bool = False, shake_x: int = 0, shake_y: int = 0):
    # Cream paper background
    bg_col = (248, 246, 239) if not punch_in else (252, 250, 244)
    draw.rectangle([(0, 0), (W, H)], fill=bg_col)

    # Ruled horizontal lines
    line_col = (228, 224, 212)
    step = 56 if not punch_in else 64
    for y in range(60 + shake_y, H + 60, step):
        draw.line([(0, y), (W, y)], fill=line_col, width=1)

    # Vertical red/pink left margin line
    margin_x = 180 + shake_x if not punch_in else 140 + shake_x
    draw.line([(margin_x, 0), (margin_x, H)], fill=(240, 168, 168), width=2)

    # Left binder holes
    for y in [160, 420, 680, 940]:
        hx = 80 + shake_x if not punch_in else 50 + shake_x
        hy = y + shake_y
        draw.ellipse([(hx - 14, hy - 14), (hx + 14, hy + 14)], fill=(210, 204, 190), outline=(180, 172, 156), width=2)
        draw.ellipse([(hx - 10, hy - 10), (hx + 10, hy + 10)], fill=(65, 55, 45))


def draw_doodle_arrow(draw: ImageDraw.ImageDraw, start: tuple, end: tuple, color=(220, 38, 38), width: int = 5):
    x1, y1 = start
    x2, y2 = end
    cx = (x1 + x2) / 2 + 25
    cy = (y1 + y2) / 2 - 20
    pts = []
    for i in range(11):
        t_prog = i / 10.0
        px = (1 - t_prog) ** 2 * x1 + 2 * (1 - t_prog) * t_prog * cx + t_prog ** 2 * x2
        py = (1 - t_prog) ** 2 * y1 + 2 * (1 - t_prog) * t_prog * cy + t_prog ** 2 * y2
        pts.append((px, py))
    draw.line(pts, fill=color, width=width)
    angle = math.atan2(y2 - cy, x2 - cx)
    al = 22
    a1 = angle + math.pi * 0.8
    a2 = angle - math.pi * 0.8
    draw.line([(x2, y2), (x2 + al * math.cos(a1), y2 + al * math.sin(a1))], fill=color, width=width)
    draw.line([(x2, y2), (x2 + al * math.cos(a2), y2 + al * math.sin(a2))], fill=color, width=width)


def draw_doodle_circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, rx: int, ry: int, progress: float = 1.0, color=(220, 38, 38), width: int = 5):
    total_steps = 36
    draw_steps = int(total_steps * min(1.0, max(0.0, progress)))
    if draw_steps < 2:
        return
    pts = []
    for i in range(draw_steps + 1):
        a = (i / float(total_steps)) * 2 * math.pi
        wobble_r = 1.0 + 0.06 * math.sin(a * 4.0) + 0.04 * math.cos(a * 3.0)
        px = cx + rx * wobble_r * math.cos(a)
        py = cy + ry * wobble_r * math.sin(a)
        pts.append((px, py))
    draw.line(pts, fill=color, width=width)


def draw_scotch_tape(draw: ImageDraw.ImageDraw, x: int, y: int, w: int = 90, h: int = 32, angle_deg: float = -10.0):
    tape = Image.new("RGBA", (w, h), (245, 235, 205, 195))
    td = ImageDraw.Draw(tape)
    td.rectangle([(0, 0), (w, h)], outline=(220, 205, 175, 180), width=1)
    return tape.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=True)


def draw_subtitle_pill(draw: ImageDraw.ImageDraw, text: str):
    if not text:
        return
    font = get_pop_font(34)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    sx = (W - tw) // 2
    sy = H - 90
    draw.rounded_rectangle([(sx - 24, sy - 8), (sx + tw + 24, sy + th + 10)], radius=12, fill=(15, 23, 42, 235))
    draw.text((sx, sy), text, font=font, fill=(250, 204, 21), stroke_width=3, stroke_fill=(0, 0, 0))


def load_character_sprite(char_role: str, target_h: int = 600) -> Image.Image:
    role_u = char_role.upper()
    is_av_chan = any(w in _CURRENT_CHANNEL_ID for w in ("blackbox", "aviation", "flight"))
    file_map = {
        "CAPTAIN": "captain_calm.png",
        "FIRST_OFFICER": "first_officer_panicked.png",
        "FO": "first_officer_panicked.png",
        "ATC": "atc_controller.png",
        "CONTROLLER": "atc_controller.png",
        "NTSB": "ntsb_investigator.png",
        "INVESTIGATOR": "ntsb_investigator.png",
        "MECHANIC": "aircraft_mechanic.png",
        "ENGINEER": "aircraft_mechanic.png",
        "HOST": "host_smug.png",
        "PILOT": "captain_calm.png" if is_av_chan else "test_pilot.png",
        "GENERAL": "crayon_pentagon_general.png",
        "CEO": "crayon_defense_ceo.png",
        "SPY": "foreign_spy.png",
        "FOUNDER": "crayon_tech_founder.png",
        "TRADER": "crayon_wall_street_trader.png",
        "SCIENTIST": "crayon_tech_founder.png"
    }
    target_file = "host_smug.png"
    for k, v in file_map.items():
        if k in role_u:
            target_file = v
            break

    search_dirs = [
        CHAR_DIR,
        BASE_DIR / "assets/characters/aviation",
        BASE_DIR / "assets/characters/defense_finance",
        BASE_DIR / "assets/characters/tacticallcrayon",
        BASE_DIR / "assets/characters",
        BASE_DIR / "assets/boskafa"
    ]
    if _CURRENT_CHANNEL_ID:
        search_dirs.insert(0, CHAR_DIR.parent / _CURRENT_CHANNEL_ID)

    for s_dir in search_dirs:
        p = s_dir / target_file
        if not p.exists():
            alt_name = target_file.replace("crayon_", "")
            if (s_dir / alt_name).exists():
                p = s_dir / alt_name
        if p.exists():
            raw = Image.open(p).convert("RGBA")
            scale = target_h / float(raw.height)
            new_w = int(raw.width * scale)
            return raw.resize((new_w, target_h), Image.Resampling.LANCZOS)
    return Image.new("RGBA", (int(target_h * 0.45), target_h), (0, 0, 0, 0))


_CACHED_STAMPS = {}

def get_cached_stamp(text: str = "TOP SECRET", angle: int = 14, color: tuple = (220, 38, 38)) -> Image.Image:
    k = (text, angle, color)
    if k not in _CACHED_STAMPS:
        sw, sh = 420, 88
        s_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        sd = ImageDraw.Draw(s_img)
        sd.rectangle([(0, 0), (sw - 1, sh - 1)], outline=color, width=5)
        s_font = get_pop_font(28)
        sd.text((16, 24), text, font=s_font, fill=color)
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
    
    text = (scene_data.get("narration", "") + " " + scene_data.get("chapter", "") + " " + sub_title).lower()
    if any(k in text for k in ["wand", "pneumatic", "ultrasonic", "transducer", "tool", "mechanical", "air"]):
        rnd_title = "SKUNKWORKS MATERIALS R&D // PNEUMATIC & ULTRASONIC TESTING"
        spec_text = "SPECIFICATION: MIL-STD-810H VIBRATION & DUST LOAD"
        sample_text = "SAMPLE #04: 40-kHz ULTRASONIC PIEZO TRANSDUCER & AIR WAND"
        status_text = "STATUS: PIEZOELECTRIC TRANSDUCER CERAMIC SHATTERED"
        rnd_bullets = [
            "• Ceramic element cracked under 5.56 rifle recoil shock",
            "• Pneumatic piston seals jammed by fine masonry dust",
            "• Unit weight: 8.4 lbs (vs 0.05 lb pocket wax crayon)",
            "• Contractor R&D cost: $340,000,000 to reinvent crayon"
        ]
    elif any(k in text for k in ["spray", "aerosol", "can", "gas", "chemical", "bead", "glass"]):
        rnd_title = "BALLISTIC TEST LAB // AEROSOL & GLASS BEAD PUNCTURE TRIAL"
        spec_text = "SPECIFICATION: MIL-STD-662F BALLISTIC LIMIT V50"
        sample_text = "SAMPLE #12: COMMERCIAL HIGH-PRESSURE SPRAY CANISTER"
        status_text = "STATUS: CATASTROPHIC PRESSURE VESSEL FAILURE"
        rnd_bullets = [
            "• Canister detonates violently upon 7.62x39mm shrapnel strike",
            "• Solvent vapor ignites, creating 2.5-meter fireball in trench",
            "• High acoustic discharge during spraying (82 decibels)",
            "• Conclusion: Pressurized aerosol disqualified for frontlines"
        ]
    elif any(k in text for k in ["bio", "enzyme", "medical", "blood", "arterial", "triage"]):
        rnd_title = "DEFENSE BIOTECH FACILITY // BIOSENSING WAX REACTION"
        spec_text = "SPECIFICATION: MIL-STD-1830 ARTERIAL HEMOGLOBIN PROBE"
        sample_text = "SAMPLE #88: ENZYMATIC CHROMOPHORE COLOR-SHIFT WAX"
        status_text = "STATUS: ENZYME DENATURATION IN 70% HUMIDITY"
        rnd_bullets = [
            "• Color-shifting enzymes denature in tropical humidity",
            "• Shelf life reduced from 5 years to 48 hours in field",
            "• Unit price: $4,200 per individual triage marking crayon",
            "• Triage medics demand standard four-color grease pencils"
        ]
    else:
        rnd_title = "SKUNKWORKS MATERIALS R&D FACILITY // PALMDALE"
        spec_text = "SPECIFICATION: MIL-STD-810H THERMAL LOAD"
        sample_text = "SAMPLE #09: HIGH-ENTHALPY MICROCRYSTALLINE WAX"
        status_text = "STATUS: VISCOSITY COLLAPSE DETECTED"
        rnd_bullets = [
            "• Paraffin liquifies at 48°C / 98.6°F",
            "• Surface adhesion drops to zero",
            "• Defrost vents contaminated with paraffin",
            "• Deficit: $420M spent without fixing melting point"
        ]

    # Skunkworks laboratory console
    card_x, card_y, card_w, card_h = 580, 180, 860, 490
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=16, fill=(15, 23, 42, 235), outline=(56, 189, 248), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 60)], radius=16, fill=(14, 116, 144, 255))
    draw.text((card_x + 30, card_y + 14), rnd_title[:54], font=get_pop_font(24), fill=(255, 255, 255))
    
    # Test readouts
    draw.text((card_x + 40, card_y + 80), spec_text, font=get_pop_font(22), fill=(234, 179, 8))
    draw.text((card_x + 40, card_y + 115), sample_text, font=get_font_safe(18, mono=True), fill=(203, 213, 225))
    
    # Laser bar scanner oscillation
    laser_x = int(card_x + 100 + (math.sin(t_sub * 4.0) + 1.0) * 0.5 * (card_w - 200))
    draw.line([(laser_x, card_y + 160), (laser_x, card_y + 320)], fill=(239, 68, 68), width=4)
    
    # Live progress/meter bar
    draw.rectangle([(card_x + 80, card_y + 175), (card_x + 500, card_y + 215)], fill=(30, 41, 59), outline=(148, 163, 184), width=2)
    prog = min(1.0, 0.4 + 0.5 * (t_sub / 4.0))
    fill_w = int(420 * prog)
    draw.rectangle([(card_x + 80, card_y + 175), (card_x + 80 + fill_w, card_y + 215)], fill=(239, 68, 68))
    curr_temp = int(32 + prog * 16)
    draw.text((card_x + 520, card_y + 180), f"{curr_temp}°C / {int(curr_temp * 1.8 + 32)}°F", font=get_pop_font(24), fill=(239, 68, 68))
    
    draw.text((card_x + 40, card_y + 245), status_text, font=get_pop_font(24), fill=(239, 68, 68))
    for b_i, bullet in enumerate(rnd_bullets):
        b_col = (234, 179, 8) if b_i == 3 else (255, 255, 255)
        draw.text((card_x + 40, card_y + 290 + b_i * 42), bullet, font=get_font_safe(20), fill=b_col)
    
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
    
    text = (scene_data.get("narration", "") + " " + scene_data.get("chapter", "") + " " + sub_title).lower()
    if any(k in text for k in ["stencil", "titanium"]):
        l_title = "COMMERCIAL CARDBOARD STENCIL"
        l_price = "PRICE: $1.50 / UNIT"
        l_bullets = [
            "• Recycled Pressed Cardboard",
            "• Light & Flexible in Frontline Pack",
            "• Disposable After Heavy Breaches",
            "• ZERO Burden on Troop Mobility"
        ]
        r_title = "PENTAGON CNC TITANIUM STENCIL"
        r_price = "PRICE: $12,000.00 / UNIT"
        r_bullets = [
            "• Grade-5 CNC Milled Titanium Plate",
            "• Weight: 6.8 lbs (Heavy Metal Slab)",
            "• Laser Apertures Clog with Mud & Slime",
            "• Taxpayer Waste: $48M Procurement"
        ]
        stamp_str = "8,000x MARKUP"
    elif any(k in text for k in ["solvent", "oil", "canopy", "decon"]):
        l_title = "COMMERCIAL CANOLA / VEGETABLE OIL"
        l_price = "PRICE: $1.00 / BOTTLE ($0.05/USE)"
        l_bullets = [
            "• 100% Organic Triglyceride Formula",
            "• Dissolves Wax Sludge in 10 Seconds",
            "• ZERO Etching on Indium-Tin RAM Layer",
            "• Keeps Stealth Canopies 100% Intact"
        ]
        r_title = "MIL-SPEC DECON SOLVENT AEROSOL"
        r_price = "PRICE: $640.00 / CANISTER"
        r_bullets = [
            "• Industrial Aromatic Hydrocarbon Spray",
            "• Corrosive Action Strips Stealth RAM",
            "• $280,000 Canopy Replacement Needed",
            "• Annual Taxpayer Cost: $45,000,000"
        ]
        stamp_str = "640x MARKUP"
    elif any(k in text for k in ["shield", "polycarbonate", "bolt"]):
        l_title = "FIELD COMBAT MARK (CHALK/WAX)"
        l_price = "PRICE: $0.00 APPLICATION COST"
        l_bullets = [
            "• Drawn directly on concrete in 2 sec",
            "• Weather-resistant microcrystalline tack",
            "• Zero tools or anchor drills needed",
            "• Frontline squads cleared instantly"
        ]
        r_title = "POLYCARBONATE TACTICAL SHIELD"
        r_price = "PRICE: $1,200.00 / PANEL"
        r_bullets = [
            "• 45-min drilling with hammer drill",
            "• Titanium anchor bolts: $4,500/each",
            "• Attracts hostile sniper fire in CQB",
            "• Zero added tactical combat value"
        ]
        stamp_str = "PATENT FIASCO"
    elif any(k in text for k in ["wand", "pneumatic", "air"]):
        l_title = "STANDARD FRONT-LINE POCKET WAX"
        l_price = "PRICE: $0.85 / STICK"
        l_bullets = [
            "• Fits in tactical breast pocket (0.05 lb)",
            "• Zero batteries, zero firmware updates",
            "• 100% jam-proof in heavy dust storms",
            "• Trusted by combat veterans worldwide"
        ]
        r_title = "PNEUMATIC EXTENDABLE MARKING WAND"
        r_price = "PRICE: $14,000.00 / WAND KIT"
        r_bullets = [
            "• 8.4-lb motorized extending carbon wand",
            "• O-rings fail after 10 min in sandstorms",
            "• Lithium battery drained by jamming",
            "• Contract expansion: $340,000,000"
        ]
        stamp_str = "16,400x MARKUP"
    else:
        l_title = "COMMERCIAL CIVILIAN HARDWARE (CRAYOLA)"
        l_price = "PRICE: $0.15 / UNIT"
        l_bullets = [
            "• 100% Non-Toxic Paraffin & Dye",
            "• Classroom Safety Certified",
            "• Standard Commercial Storage",
            "• Frontline Squads Use Off-the-Shelf"
        ]
        r_title = "PENTAGON 'TACTICAL MARKER' (MIL-SPEC)"
        r_price = "PRICE: $4,800.00 / UNIT"
        r_bullets = [
            "• Contract: DOD-SPEC-810H Tactical Wax",
            "• Melts into Sludge at 48°C / 98.6°F",
            "• Massive Thermal Blooming on FLIR/NVG",
            "• Drips into HVAC Vents Creating Toxic Fumes"
        ]
        stamp_str = "32,000x MARKUP"

    # Left Card: Civil / Normal
    lx, ly, lw, lh = 220, 180, 620, 700
    draw.rounded_rectangle([(lx, ly), (lx + lw, ly + lh)], radius=16, fill=(248, 250, 252), outline=(148, 163, 184), width=3)
    draw.rounded_rectangle([(lx, ly), (lx + lw, ly + 65)], radius=16, fill=(30, 41, 59))
    draw.text((lx + 25, ly + 16), l_title[:38], font=get_pop_font(24), fill=(255, 255, 255))
    draw.text((lx + 35, ly + 95), l_price, font=get_pop_font(34), fill=(34, 197, 94))
    for i, b in enumerate(l_bullets):
        draw.text((lx + 35, ly + 165 + i * 50), b, font=get_pop_font(21), fill=(15, 23, 42))
    
    # Right Card: Mil-Spec Absurd
    rx, ry, rw, rh = 940, 180, 720, 700
    draw.rounded_rectangle([(rx, ry), (rx + rw, ry + rh)], radius=16, fill=(15, 23, 42), outline=(239, 68, 68), width=3)
    draw.rounded_rectangle([(rx, ry), (rx + rw, ry + 65)], radius=16, fill=(220, 38, 38))
    draw.text((rx + 25, ry + 16), r_title[:40], font=get_pop_font(24), fill=(255, 255, 255))
    draw.text((rx + 35, ry + 95), r_price, font=get_pop_font(34), fill=(239, 68, 68))
    for i, b in enumerate(r_bullets):
        if i == 0:
            b_col = (255, 255, 255)
        elif i == 1:
            b_col = (234, 179, 8)
        else:
            b_col = (239, 68, 68)
        draw.text((rx + 35, ly + 165 + i * 50), b, font=get_pop_font(21), fill=b_col)
    
    # VS Center Badge
    vs_x, vs_y = 890, 480
    draw.ellipse([(vs_x - 50, vs_y - 50), (vs_x + 50, vs_y + 50)], fill=(234, 179, 8), outline=(255, 255, 255), width=3)
    draw.text((vs_x - 22, vs_y - 18), "VS", font=get_pop_font(34), fill=(15, 23, 42))
    
    stamp_img = get_cached_stamp(stamp_str, 15)
    frame.alpha_composite(stamp_img, (rx + rw - 340, ry + 420))
    
    frame.alpha_composite(host_shock, (30, H - host_shock.height - 20))
    ceo_side = load_character_sprite("CEO", 520)
    frame.alpha_composite(ceo_side, (W - ceo_side.width - 25, H - ceo_side.height - 20))
    draw_pop_title(draw, sub_title)


def render_flow_chart(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(15, 23, 42))
    for gx in range(0, W, 80): draw.line([(gx, 0), (gx, H)], fill=(24, 36, 60), width=1)
    for gy in range(0, H, 80): draw.line([(0, gy), (W, gy)], fill=(24, 36, 60), width=1)
    
    text = (scene_data.get("narration", "") + " " + scene_data.get("chapter", "") + " " + sub_title).lower()
    if any(k in text for k in ["symbol", "entry", "breach", "clear", "door", "corridor", "triage", "hazard", "mark", "shorthand"]):
        nodes = [
            ("STAGE 1: ENTRY SLASH", "Top-left to bottom-right indicates search active.", (56, 189, 248)),
            ("STAGE 2: SQUAD ADVANCE", "Rooms searched without double-clear risk under fire.", (234, 179, 8)),
            ("STAGE 3: HAZARD RING", "UXO / booby trap cordoned with solid grease circle.", (239, 68, 68)),
            ("STAGE 4: EXTRACTION", "Clean chevron corridor marks route to extraction LZ.", (34, 197, 94)),
        ]
    elif any(k in text for k in ["wand", "procurement", "overengineer", "patent", "shield", "drill", "bolt", "cost", "billion", "dollar"]):
        nodes = [
            ("STAGE 1: $0.85 CRAYON", "Field troops apply instant wax mark in 2.1 seconds flat.", (34, 197, 94)),
            ("STAGE 2: PENTAGON AUDIT", "Contractors lobby to re-engineer with titanium & lasers.", (234, 179, 8)),
            ("STAGE 3: $14,000 WAND", "Pneumatic wand clogs; troops ditch 8-lb battery pack.", (239, 68, 68)),
            ("STAGE 4: RETURN TO CRAYON", "Soldiers ditch high-tech gear and pull out pocket wax.", (56, 189, 248)),
        ]
    elif any(k in text for k in ["solar", "heat", "melt", "paraffin", "temperature", "greenhouse", "canopy", "desert", "sludge"]):
        nodes = [
            ("STAGE 1: SOLAR HEAT", "Canopy reaches 62°C greenhouse thermal load.", (56, 189, 248)),
            ("STAGE 2: LIQUEFACTION", "Paraffin melts completely at 48°C threshold.", (234, 179, 8)),
            ("STAGE 3: VENT INGESTION", "Melted wax seeps into HVAC defrost vents.", (239, 68, 68)),
            ("STAGE 4: MISSION ABORT", "Toxic acrolein smoke forces emergency abort.", (220, 38, 38)),
        ]
    else:
        nodes = [
            ("PHASE 1: INITIATION", f"Operational directive issued for {sub_title[:28]}", (56, 189, 248)),
            ("PHASE 2: DEPLOYMENT", "Frontline operations reveal analog vs digital friction.", (234, 179, 8)),
            ("PHASE 3: FIELD AUDIT", "Survivability and cost metrics scrutinized in combat.", (239, 68, 68)),
            ("PHASE 4: DOCTRINE FIX", "Common sense simplicity triumphs over complex tech.", (34, 197, 94)),
        ]
    
    active_idx = min(3, int(t_sub / 1.1))
    
    start_x = 450
    nw, nh = 310, 360
    spacing = 330
    
    for i, (n_title, n_desc, n_col) in enumerate(nodes):
        nx = start_x + i * spacing
        ny = 320
        is_act = (i <= active_idx)
        card_fill = (24, 36, 60) if is_act else (16, 24, 40)
        border_col = n_col if is_act else (71, 85, 105)
        border_w = 4 if i == active_idx else 2
        
        draw.rounded_rectangle([(nx, ny), (nx + nw, ny + nh)], radius=14, fill=card_fill, outline=border_col, width=border_w)
        draw.rounded_rectangle([(nx, ny), (nx + nw, ny + 55)], radius=14, fill=border_col)
        draw.text((nx + 14, ny + 14), n_title[:24], font=get_pop_font(19), fill=(15, 23, 42) if is_act else (255, 255, 255))
        
        words = n_desc.split()
        line1 = " ".join(words[:4])
        line2 = " ".join(words[4:])
        draw.text((nx + 18, ny + 85), line1, font=get_pop_font(22), fill=(255, 255, 255))
        draw.text((nx + 18, ny + 125), line2, font=get_pop_font(21), fill=(203, 213, 225))
        
        # Arrow to next
        if i < 3:
            ax = nx + nw + 6
            ay = ny + nh // 2
            draw.line([(ax, ay), (ax + 14, ay)], fill=(234, 179, 8), width=3)
            draw.polygon([(ax + 14, ay - 6), (ax + 22, ay), (ax + 14, ay + 6)], fill=(234, 179, 8))
    
    frame.alpha_composite(host_point, (40, H - host_point.height - 20))
    founder_react = load_character_sprite("FOUNDER", 520)
    frame.alpha_composite(founder_react, (W - founder_react.width - 25, H - founder_react.height - 20))
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
    
    text = (scene_data.get("narration", "") + " " + scene_data.get("chapter", "") + " " + sub_title).lower()
    if any(k in text for k in ["symbol", "entry", "breach", "fema", "x-mark", "quadrant", "chevron", "marking", "chalk", "shorthand"]):
        bp_title = "TECHNICAL BLUEPRINT // TACTICAL MARKING MATRIX & SYMBOLOGY"
        fp_text = "SPEC: MIL-STD-1472H COMBAT SYMBOLOGY"
        card_hdr = "SURVIVAL MARKING ARCHITECTURE:"
        specs = [
            "• Standard: NATO & FEMA 4-Quadrant Door Matrix",
            "• Scribe Medium: High-Tack Microcrystalline Wax",
            "• Surface Substrate: Brick, Cinderblock, Rebar & Steel",
            "• Reading Distance: 35 Meters via Day Sight & Thermal NVG",
            "• Application Duration: 2.1 Seconds  |  Tool Cost: $0.85"
        ]
    elif any(k in text for k in ["canopy", "solvent", "decon", "damage", "etching", "ito", "glass"]):
        bp_title = "TECHNICAL BLUEPRINT // CANOPY DAMAGE & SOLVENT ETCHING"
        fp_text = "CRITICAL FLAW: $280,000 CANOPY ETCHING"
        card_hdr = "AIRCRAFT SURFACE DEGRADATION:"
        specs = [
            "• Substrate: Indium-Tin Oxide (ITO) Radar Absorbent Layer",
            "• Chemical Action: Commercial Solvents Strip RAM Coating",
            "• Canopy Replacement: $280,000 per Etched Bubble Canopy",
            "• Stealth Signature: Degraded by 4.2 dB in X-Band Radar",
            "• Field Fix: $1.00 Canola Oil Cleans Wax with 0% Damage"
        ]
    elif any(k in text for k in ["laminate", "chart", "map", "oil", "grease", "kneeboard"]):
        bp_title = "TECHNICAL BLUEPRINT // MAP LAMINATE & KNEEBOARD CHARTING"
        fp_text = "SURFACE FLAW: OILY LAMINATE FRICTION ZERO"
        card_hdr = "TACTICAL NAVIGATION SURFACE:"
        specs = [
            "• Substrate: Heavy-Gauge Polycarbonate Flight Kneeboard",
            "• Friction Barrier: Fingerprint Oil Prevents Ink Adhesion",
            "• Optical Glare: Standard Markers Wash Out Under Direct Sun",
            "• Target Error: Navigator Misreads Route Coordinate Ticks",
            "• Field Solution: High-Tack Wax Bites Through Grease"
        ]
    else:
        bp_title = "TECHNICAL BLUEPRINT // CRITICAL FAILURE MODE ANALYSIS"
        fp_text = "FAILURE POINT: 48°C THERMAL MELT"
        card_hdr = "MIL-SPEC MATERIAL ARCHITECTURE:"
        specs = [
            "• Component: Mil-Spec Tactical Wax Marker",
            "• Formulation: Low-Density Paraffin Base",
            "• Infrared: High 850nm Thermal Blooming",
            "• Contrast under 650nm Red Cockpit Light: 0%",
            "• Solvent Impact: $280,000 Canopy Etching Damage"
        ]

    bx, by, bw, bh = 540, 180, 1300, 720
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=16, fill=(8, 22, 44, 240), outline=(56, 189, 248), width=3)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=16, fill=(14, 116, 144))
    draw.text((bx + 30, by + 16), bp_title[:54], font=get_pop_font(26), fill=(255, 255, 255))
    
    # Blueprint crosshairs
    cx, cy = bx + 320, by + 390
    for r in [85, 170, 255]:
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(56, 189, 248, 110), width=2)
    draw.line([(cx - 280, cy), (cx + 280, cy)], fill=(56, 189, 248, 130), width=1)
    draw.line([(cx, cy - 280), (cx, cy + 280)], fill=(56, 189, 248, 130), width=1)
    
    # Pulsing failure point
    p_rad = int(32 + abs(math.sin(t_sub * 6.0)) * 18.0)
    draw.ellipse([(cx - p_rad, cy - p_rad), (cx + p_rad, cy + p_rad)], outline=(239, 68, 68), width=4)
    draw.text((cx - 140, cy - 60), fp_text[:35], font=get_pop_font(21), fill=(239, 68, 68))
    
    # Specs Card
    draw.rectangle([(bx + 660, by + 95), (bx + bw - 40, by + bh - 55)], fill=(15, 23, 42), outline=(56, 189, 248), width=2)
    draw.text((bx + 685, by + 125), card_hdr, font=get_pop_font(24), fill=(234, 179, 8))
    for s_i, sp in enumerate(specs):
        if any(w in sp for w in ["Damage", "Degraded", "Error"]):
            sp_col = (239, 68, 68)
        elif any(w in sp for w in ["Fix", "Intact", "Cost"]):
            sp_col = (34, 197, 94)
        else:
            sp_col = (255, 255, 255)
        draw.text((bx + 685, by + 175 + s_i * 48), sp, font=get_font_safe(20), fill=sp_col)
    
    frame.alpha_composite(host_shock, (30, H - host_shock.height - 20))
    general_side = load_character_sprite("GENERAL", 540)
    frame.alpha_composite(general_side, (W - general_side.width - 25, H - general_side.height - 20))
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
        
    text = (scene_data.get("narration", "") + " " + scene_data.get("chapter", "") + " " + sub_title).lower()
    if any(k in text for k in ["spray", "aerosol", "can", "paint", "shrapnel", "fume", "flame"]):
        warn_title = "CRITICAL HAZARD // AEROSOL & SPRAY CANISTER FIASCO"
        bullets = [
            "• Pressurized aerosol cans detonate under incoming shrapnel",
            "• Toxic solvent fumes create explosive vapor cloud in rooms",
            "• High-frequency spray hiss betrays breaching team position",
            "• Combat Lesson: Pressurized spray ditched for solid wax"
        ]
        alert_tag = "TACTICAL DIRECTIVE // AEROSOL FORBIDDEN IN CQB"
    elif any(k in text for k in ["drill", "anchor", "bolt", "concrete", "shield", "polycarbonate"]):
        warn_title = "CRITICAL HAZARD // TIME-CRITICAL BREACH FAILURE"
        bullets = [
            "• 45-minute concrete anchor drilling while taking sniper fire",
            "• Heavy rotary hammer drill compromises structural rebar",
            "• Hostile spotters track loud cordless drill motor whine",
            "• Pentagon Directive: Titanium shield mounting abandoned"
        ]
        alert_tag = "TACTICAL BREACH // ZERO DRILLING UNDER FIRE"
    elif any(k in text for k in ["slash", "door", "friendly", "double", "room", "clear", "entry"]):
        warn_title = "CRITICAL HAZARD // DOUBLE-CLEARING & FRIENDLY FIRE RISK"
        bullets = [
            "• Entering occupied rooms without status leads to friendly fire",
            "• High-tempo urban CQB: Follow-on squads mistake friendlies",
            "• Single diagonal slash tells following elements: SQUAD INSIDE",
            "• Combat Doctrine: Slash mandatory on all breached doorways"
        ]
        alert_tag = "CQB PROTOCOL // PREVENTING BLUE-ON-BLUE UNDER FIRE"
    elif any(k in text for k in ["reflec", "bead", "sniper", "illum", "white light", "nvg"]):
        warn_title = "COMPROMISED SIGNATURE // ENEMY SNIPER LOCK-ON"
        bullets = [
            "• Retro-reflective glass micro-beads shine under white light",
            "• Hostile sniper optics spot friendly movement at 1,200m",
            "• High-contrast glow compromises silent night infiltration",
            "• Special Operations Command: Glass beads discarded"
        ]
        alert_tag = "TACTICAL SECURITY // ZERO REFLECTIVE BEADS"
    elif any(k in text for k in ["laser", "dog", "robot", "wire", "jam"]):
        warn_title = "AUTOMATION FAILURE // HIGH-TECH BREAKDOWN"
        bullets = [
            "• Autonomous marking robot ensnared in concertina razor wire",
            "• Electronic warfare jamming drains lithium batteries in 18 min",
            "• High-resolution laser scanner blinded by ambient concrete dust",
            "• Platoon Commander: $450k robot abandoned in rubble"
        ]
        alert_tag = "ROBOTICS COLLAPSE // SQUAD DISCONNECT AUTHORIZED"
    elif any(k in text for k in ["solar", "heat", "melt", "hvac", "canopy", "paraffin"]):
        warn_title = "CRITICAL OPERATIONAL HAZARD // THERMAL MELT"
        bullets = [
            "• 48°C thermal collapse inside greenhouse canopy",
            "• Melted wax contaminates avionics flight stick & HUD",
            "• HVAC defrost intake clogged with paraffin sludge",
            "• Flight Safety Directive: Immediate mission abort"
        ]
        alert_tag = "MIL-STD 810H PROTOCOL BREACH // ABORT"
    else:
        warn_title = "TACTICAL THREAT ALERT // OPERATIONAL CONTAMINATION"
        bullets = [
            f"• High operational friction: {sub_title[:38]}",
            "• Frontline tactical marking protocol compromised",
            "• Analog backup demanded by frontline combat leaders",
            "• Pentagon oversight notified of procedural deviation"
        ]
        alert_tag = "TACTICAL ALERT // IMMEDIATE REVIEW MANDATE"

    # Central Warning Badge
    cx, cy, bw, bh = 960, 500, 960, 430
    bx, by = cx - bw // 2, cy - bh // 2
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=20, fill=(15, 23, 42, 245), outline=(239, 68, 68), width=5)
    
    draw.text((bx + 60, by + 50), warn_title, font=get_pop_font(28), fill=(239, 68, 68))
    for i, b in enumerate(bullets):
        if i == 2:
            b_c = (234, 179, 8)
        elif i == 3:
            b_c = (34, 197, 94)
        else:
            b_c = (255, 255, 255)
        draw.text((bx + 60, by + 115 + i * 50), b, font=get_pop_font(23), fill=b_c)
    draw.text((bx + 60, by + 325), alert_tag, font=get_pop_font(26), fill=(239, 68, 68))
    
    frame.alpha_composite(host_shock, (30, H - host_shock.height - 20))
    founder_panicked = load_character_sprite("FOUNDER", 540)
    frame.alpha_composite(founder_panicked, (W - founder_panicked.width - 25, H - founder_panicked.height - 20))
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
    
    text = (scene_data.get("narration", "") + " " + scene_data.get("chapter", "") + " " + sub_title).lower()
    if any(k in text for k in ["symbol", "entry", "breach", "fema", "x-mark", "quadrant", "chevron", "marking", "shorthand"]):
        table_hdr = "TACTICAL URBAN DOCTRINE // COMBAT SYMBOLOGY BRIEFING"
        lesson_title = "DOCTRINE #1: STANDARDIZED MARKING SAVES LIVES"
        b1 = "• Room-to-room CQB requires immediate, unmistakable entry status."
        b2 = "• 4-Quadrant Door Matrix communicates time, unit, hazards, and victims."
        b3 = "• Single wax stroke prevents friendly squads from double-clearing."
        verdict = "VERDICT: CRITICAL SURVIVAL SHORTCUT ACROSS ALL CQB SECTORS"
    elif any(k in text for k in ["wand", "procurement", "overengineer", "patent", "shield", "drill", "bolt"]):
        table_hdr = "DEFENSE PROCUREMENT AUDIT // SIMPLICITY VS GADGETS"
        lesson_title = "LESSON #2: COMPLEX HARDWARE DITCHED ON FRONTLINE"
        b1 = "• 8-lb pneumatic wands and titanium stencils fail in battlefield dust."
        b2 = "• Batteries die, mechanical seals freeze, and electronics glitch."
        b3 = "• Troops invariably revert to the $0.85 pocket wax marker."
        verdict = "VERDICT: COMMON SENSE TRUMPS OVER-ENGINEERED DEFENSE GEAR"
    else:
        table_hdr = "STRATEGIC DEFENSE DOCTRINE & LESSONS LEARNED"
        lesson_title = "LESSON #1: ANALOG IS ESSENTIAL WHEN TECH FAILS"
        b1 = "• Satellite datalinks and digital GPS go dark under EW jamming."
        b2 = "• Analog grease markings remain the only failsafe combat channel."
        b3 = "• Yet $68B procurement waste cripples frontline readiness."
        verdict = "VERDICT: PENTAGON AUDIT DEMANDS DOCTRINAL REALITY CHECK"

    # Holographic Briefing Table
    bx, by, bw, bh = 500, 210, 1340, 640
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=20, fill=(18, 30, 50, 240), outline=(56, 189, 248), width=3)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=20, fill=(14, 116, 144))
    draw.text((bx + 30, by + 16), table_hdr, font=get_pop_font(26), fill=(255, 255, 255))
    
    draw.text((bx + 40, by + 95), lesson_title, font=get_pop_font(28), fill=(234, 179, 8))
    draw.text((bx + 40, by + 155), b1, font=get_font_safe(22), fill=(203, 213, 225))
    draw.text((bx + 40, by + 205), b2, font=get_font_safe(22), fill=(203, 213, 225))
    draw.text((bx + 40, by + 255), b3, font=get_font_safe(22), fill=(239, 68, 68))
    draw.text((bx + 40, by + 325), verdict, font=get_pop_font(28), fill=(34, 197, 94))
    
    frame.alpha_composite(host_cur, (30, H - host_cur.height - 20))
    table_partner = load_character_sprite("GENERAL", 550)
    frame.alpha_composite(table_partner, (W - table_partner.width - 25, H - table_partner.height - 20))
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


def render_editorial_briefing(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    host_point: Image.Image,
    scene_data: dict,
):
    palette = {
        "EDITORIAL_BRIEFING": ((15, 23, 42), (56, 189, 248)),
        "EDITORIAL_BLUEPRINT": ((10, 25, 47), (34, 211, 238)),
        "EDITORIAL_FIELD_NOTE": ((38, 35, 28), (234, 179, 8)),
        "EDITORIAL_VERDICT": ((15, 35, 35), (52, 211, 153)),
    }
    mode = sub_title if sub_title in palette else "EDITORIAL_BRIEFING"
    background, accent = palette[mode]
    draw.rectangle([(0, 0), (W, H)], fill=background)
    if mode == "EDITORIAL_BLUEPRINT":
        for gx in range(0, W, 64):
            draw.line([(gx, 0), (gx, H)], fill=(20, 48, 75), width=1)
        for gy in range(0, H, 64):
            draw.line([(0, gy), (W, gy)], fill=(20, 48, 75), width=1)

    panel = (400, 170, W - 90, H - 130)
    draw.rounded_rectangle(panel, radius=20, fill=(15, 23, 42), outline=accent, width=3)
    chapter = str(scene_data.get("chapter") or "VIDEO ESSAY").strip()
    draw.text((panel[0] + 36, panel[1] + 30), chapter[:64].upper(), font=get_pop_font(34), fill=accent)
    draw.line(
        [(panel[0] + 36, panel[1] + 92), (panel[2] - 36, panel[1] + 92)],
        fill=(71, 85, 105),
        width=2,
    )

    narration = re.sub(r"\s+", " ", str(scene_data.get("narration") or "")).strip()
    excerpt = narration[:260]
    if len(narration) > len(excerpt):
        excerpt = excerpt.rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    lines = textwrap.wrap(excerpt, width=54)[:5]
    body_font = get_font_safe(32)
    for line_index, line in enumerate(lines):
        draw.text(
            (panel[0] + 40, panel[1] + 140 + line_index * 52),
            line,
            font=body_font,
            fill=(241, 245, 249),
        )
    draw.text(
        (panel[0] + 40, panel[3] - 72),
        "TACTICAL CRAYON  //  EDITORIAL BREAKDOWN",
        font=get_font_safe(18, mono=True),
        fill=(148, 163, 184),
    )
    frame.alpha_composite(host_point, (24, H - host_point.height - 18))


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


_PANEL_SPRITE_CACHE = {}

def get_cached_panel_sprite(sprite: Image.Image, target_h: int = 460) -> Image.Image:
    k = (id(sprite), target_h)
    if k not in _PANEL_SPRITE_CACHE:
        scale_ratio = target_h / float(sprite.height)
        new_w, new_h = int(sprite.width * scale_ratio), int(sprite.height * scale_ratio)
        _PANEL_SPRITE_CACHE[k] = sprite.resize((new_w, new_h), Image.Resampling.LANCZOS)
    return _PANEL_SPRITE_CACHE[k]


def render_blueprint_symbol_hud(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, scene_data: dict):
    # Blueprint background (deep navy with coordinate grid)
    draw.rectangle([(0, 0), (W, H)], fill=(8, 22, 42))
    grid_color = (20, 48, 86)
    for gx in range(0, W, 60): draw.line([(gx, 0), (gx, H)], fill=grid_color, width=1)
    for gy in range(0, H, 60): draw.line([(0, gy), (W, gy)], fill=grid_color, width=1)
    
    draw.line([(60, 60), (W - 60, 60)], fill=(56, 189, 248), width=2)
    draw.line([(60, H - 60), (W - 60, H - 60)], fill=(56, 189, 248), width=2)
    draw.text((80, 25), "US MIL-STD-1472H // TACTICAL URBAN COMBAT MARKING MATRIX (BLUEPRINT HUD)", font=get_font_safe(18, mono=True), fill=(56, 189, 248))
    draw.text((W - 380, 25), "CLASSIFICATION: DECLASSIFIED // NATO", font=get_font_safe(16, mono=True), fill=(234, 179, 8))

    cx, cy, r_m = 880, 480, 190
    draw.ellipse([(cx - r_m - 20, cy - r_m - 20), (cx + r_m + 20, cy + r_m + 20)], outline=(30, 64, 110), width=2)
    
    # Step-by-step drawing of the 4-quadrant X matrix
    p1 = min(1.0, t_sub / 0.8)
    draw.line([(cx - r_m, cy + r_m), (int((cx - r_m) + 2 * r_m * p1), int((cy + r_m) - 2 * r_m * p1))], fill=(255, 255, 255), width=12)
    
    if t_sub >= 0.8:
        p2 = min(1.0, (t_sub - 0.8) / 0.8)
        draw.line([(cx - r_m, cy - r_m), (int((cx - r_m) + 2 * r_m * p2), int((cy - r_m) + 2 * r_m * p2))], fill=(255, 255, 255), width=12)

    # 4 Quadrants with illuminated leader lines
    if t_sub >= 1.2:
        draw.line([(cx, cy - 80), (cx, cy - 240), (cx + 120, cy - 240)], fill=(56, 189, 248), width=2)
        draw.rounded_rectangle([(cx - 160, cy - 290), (cx + 200, cy - 240)], radius=8, fill=(15, 30, 55, 240), outline=(56, 189, 248), width=2)
        draw.text((cx - 140, cy - 280), "▲ ENTRY: 19-OCT // 04:15 ZULU", font=get_font_safe(18, mono=True), fill=(56, 189, 248))
        
    if t_sub >= 1.7:
        draw.line([(cx - 80, cy), (cx - 260, cy)], fill=(34, 197, 94), width=2)
        draw.rounded_rectangle([(cx - 480, cy - 30), (cx - 260, cy + 30)], radius=8, fill=(15, 30, 55, 240), outline=(34, 197, 94), width=2)
        draw.text((cx - 460, cy - 14), "◀ UNIT: ALPHA-1 SQD", font=get_font_safe(18, mono=True), fill=(34, 197, 94))
        
    if t_sub >= 2.2:
        draw.line([(cx + 80, cy), (cx + 260, cy)], fill=(239, 68, 68), width=2)
        draw.rounded_rectangle([(cx + 260, cy - 30), (cx + 560, cy + 30)], radius=8, fill=(15, 30, 55, 240), outline=(239, 68, 68), width=2)
        draw.text((cx + 280, cy - 14), "▶ HAZARD: BOOBY TRAP (UXO)", font=get_font_safe(18, mono=True), fill=(239, 68, 68))
        
    if t_sub >= 2.7:
        draw.line([(cx, cy + 80), (cx, cy + 240), (cx - 120, cy + 240)], fill=(234, 179, 8), width=2)
        draw.rounded_rectangle([(cx - 200, cy + 240), (cx + 180, cy + 290)], radius=8, fill=(15, 30, 55, 240), outline=(234, 179, 8), width=2)
        draw.text((cx - 180, cy + 252), "▼ VICTIMS: 0 KIA / 2 WIA CLEARED", font=get_font_safe(18, mono=True), fill=(234, 179, 8))

    # Satirical Price Contrast Cards at Bottom
    draw.rounded_rectangle([(80, H - 220), (520, H - 90)], radius=12, fill=(15, 30, 55, 240), outline=(34, 197, 94), width=2)
    draw.text((100, H - 205), "SOLDIER ON-SITE MARKING", font=get_pop_font(20), fill=(34, 197, 94))
    draw.text((100, H - 170), "TOOL: Standard $0.85 Wax Stick", font=get_font_safe(16), fill=(226, 232, 240))
    draw.text((100, H - 140), "TIME: 2.1 SECONDS  |  COST: $0.00", font=get_pop_font(18), fill=(255, 255, 255))
    
    draw.rounded_rectangle([(W - 580, H - 220), (W - 80, H - 90)], radius=12, fill=(45, 15, 20, 240), outline=(239, 68, 68), width=2)
    draw.text((W - 560, H - 205), "PENTAGON RE-EVALUATION CONTRACT", font=get_pop_font(20), fill=(239, 68, 68))
    draw.text((W - 560, H - 170), "STUDY: Multi-Agency Certification Study", font=get_font_safe(16), fill=(226, 232, 240))
    draw.text((W - 560, H - 140), "PROCUREMENT COST: $42,000,000", font=get_pop_font(20), fill=(239, 68, 68))
    
    stamp = get_cached_stamp("APPROVED BY CONGRESS", -10, (239, 68, 68))
    frame.alpha_composite(stamp, (W - 420, H - 170))
    frame.alpha_composite(host_point, (20, H - host_point.height - 20))
    draw_pop_title(draw, sub_title)


def render_exploded_patent_schema(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_shock: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(13, 27, 42))
    for gx in range(40, W - 40, 40): draw.line([(gx, 40), (gx, H - 40)], fill=(22, 45, 70), width=1)
    for gy in range(40, H - 40, 40): draw.line([(40, gy), (W - 40, gy)], fill=(22, 45, 70), width=1)
    
    draw.rectangle([(40, 40), (W - 40, H - 40)], outline=(56, 189, 248), width=2)
    draw.text((60, 50), "UNITED STATES PATENT & TRADEMARK OFFICE // DOD-PAT-884219", font=get_font_safe(18, mono=True), fill=(56, 189, 248))
    draw.text((60, 75), "FIG. 4: OVER-ENGINEERED COMBAT MARKING ENCLOSURE (EXPLODED VIEW)", font=get_pop_font(22), fill=(255, 255, 255))
    
    cx, cy = 960, 480
    draw.line([(cx - 360, cy), (cx + 360, cy)], fill=(56, 189, 248), width=2)
    
    # 1. Polycarbonate Shield
    draw.polygon([(cx - 280, cy - 140), (cx - 160, cy - 140), (cx - 200, cy + 140), (cx - 320, cy + 140)], fill=(30, 58, 95, 200), outline=(56, 189, 248), width=3)
    draw.text((cx - 310, cy - 170), "[1] POLYCARBONATE SHIELD", font=get_font_safe(16, mono=True), fill=(56, 189, 248))
    draw.text((cx - 310, cy + 160), "PRICE: $1,200 / PANEL", font=get_pop_font(18), fill=(234, 179, 8))
    
    # 2. Titanium Anchor Hex Bolts
    for bx, by in [(-330, -160), (-140, -160), (-340, 160), (-180, 160)]:
        draw.ellipse([(cx + bx - 16, cy + by - 16), (cx + bx + 16, cy + by + 16)], fill=(203, 213, 225), outline=(255, 255, 255), width=2)
        draw.line([(cx + bx - 10, cy + by), (cx + bx + 10, cy + by)], fill=(15, 23, 42), width=3)
    draw.line([(cx - 240, cy - 160), (cx - 240, cy - 240), (cx - 380, cy - 240)], fill=(234, 179, 8), width=2)
    draw.text((cx - 560, cy - 250), "[2] TITANIUM HEX BOLTS (x4): $4,500/EACH", font=get_font_safe(16, mono=True), fill=(234, 179, 8))
    
    # 3. 40-kHz Ultrasonic Resonant Transducer Core
    draw.rectangle([(cx - 80, cy - 90), (cx + 80, cy + 90)], fill=(30, 41, 59), outline=(239, 68, 68), width=3)
    for arc_r in [110, 130, 150]:
        draw.arc([(cx - arc_r, cy - arc_r), (cx + arc_r, cy + arc_r)], start=30, end=150, fill=(239, 68, 68), width=2)
        draw.arc([(cx - arc_r, cy - arc_r), (cx + arc_r, cy + arc_r)], start=210, end=330, fill=(239, 68, 68), width=2)
    draw.text((cx - 70, cy - 30), "40-kHz TRANSDUCER", font=get_pop_font(16), fill=(239, 68, 68))
    draw.text((cx - 70, cy + 10), "(HOWLS WORKING DOGS)", font=get_font_safe(14, mono=True), fill=(255, 255, 255))
    draw.text((cx - 70, cy + 110), "COST: $125,000 / UNIT", font=get_pop_font(18), fill=(239, 68, 68))
    
    # 4. Standard Wax Crayon
    draw.rectangle([(cx + 180, cy - 30), (cx + 340, cy + 30)], fill=(202, 138, 4), outline=(255, 255, 255), width=2)
    draw.polygon([(cx + 340, cy - 30), (cx + 390, cy), (cx + 340, cy + 30)], fill=(234, 179, 8), outline=(255, 255, 255), width=2)
    draw.text((cx + 190, cy - 10), "STANDARD WAX CRAYON", font=get_font_safe(14, bold=True), fill=(15, 23, 42))
    draw.line([(cx + 280, cy + 30), (cx + 280, cy + 120), (cx + 180, cy + 120)], fill=(34, 197, 94), width=2)
    draw.text((cx + 180, cy + 130), "[4] CORE AGENT: $0.85 CRAYON", font=get_pop_font(18), fill=(34, 197, 94))
    
    # Bottom Audit Summary Card
    draw.rounded_rectangle([(480, H - 180), (W - 80, H - 60)], radius=12, fill=(15, 23, 42, 240), outline=(234, 179, 8), width=2)
    draw.text((510, H - 165), "DEFENSE PROCUREMENT AUDIT VERDICT:", font=get_pop_font(20), fill=(234, 179, 8))
    draw.text((510, H - 130), "• Total Program Cost: $86,400,000 to protect an 85-cent wax line", font=get_font_safe(18), fill=(255, 255, 255))
    draw.text((510, H - 95), "• Field Result: Transducers cracked under rifle recoil; dog howling alerted sentries", font=get_font_safe(18), fill=(239, 68, 68))
    
    frame.alpha_composite(host_shock, (40, H - host_shock.height - 20))
    draw_pop_title(draw, sub_title)


def render_flir_bakery_incident(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, pilot_img: Image.Image, scene_data: dict):
    # Authentic FLIR Thermal Camera Night-Vision View
    draw.rectangle([(0, 0), (W, H)], fill=(6, 18, 10))
    for y in range(0, H, 4): draw.line([(0, y), (W, y)], fill=(10, 30, 16), width=1)
    
    cx, cy, r_lens = 960, 480, 420
    draw.ellipse([(cx - r_lens, cy - r_lens), (cx + r_lens, cy + r_lens)], outline=(34, 197, 94), width=3)
    draw.ellipse([(cx - r_lens + 8, cy - r_lens + 8), (cx + r_lens - 8, cy + r_lens - 8)], outline=(16, 48, 24), width=2)
    
    draw.line([(cx - r_lens, cy), (cx + r_lens, cy)], fill=(34, 197, 94), width=2)
    draw.line([(cx, cy - r_lens), (cx, cy + r_lens)], fill=(34, 197, 94), width=2)
    for tick in range(-300, 310, 50):
        if tick != 0:
            draw.line([(cx + tick, cy - 6), (cx + tick, cy + 6)], fill=(34, 197, 94), width=2)
            draw.line([(cx - 6, cy + tick), (cx + 6, cy + tick)], fill=(34, 197, 94), width=2)
            
    draw.text((cx - 380, cy - r_lens + 20), "THERMAL FLIR // WHITE-HOT // 12X MAG // LASER RNG: 840M", font=get_font_safe(18, mono=True), fill=(34, 197, 94))
    draw.text((cx - 380, cy - r_lens + 50), "WEAPON: 120mm M256 SMOOTHBORE // FIRE CONTROL: TRACKING", font=get_font_safe(16, mono=True), fill=(203, 213, 225))
    
    bx, by = cx + 80, cy - 30
    draw.polygon([(bx - 180, by - 120), (bx + 180, by - 120), (bx + 180, by + 160), (bx - 180, by + 160)], fill=(30, 45, 36), outline=(45, 70, 55), width=2)
    for wx in [-120, -30, 60]:
        draw.rectangle([(bx + wx, by - 80), (bx + wx + 50, by - 20)], fill=(15, 25, 20), outline=(34, 197, 94), width=1)
        draw.rectangle([(bx + wx, by + 30), (bx + wx + 50, by + 90)], fill=(15, 25, 20), outline=(34, 197, 94), width=1)
        
    # Micro-prismatic wax marking glowing like a thermal flare
    pulse = (math.sin(t_sub * 8) + 1.0) / 2.0
    flare_r = int(35 + pulse * 20)
    draw.ellipse([(bx - 30 - flare_r, by - 50 - flare_r), (bx - 30 + flare_r, by - 50 + flare_r)], fill=(255, 255, 255, int(180 + pulse * 70)))
    draw.ellipse([(bx - 30 - flare_r // 2, by - 50 - flare_r // 2), (bx - 30 + flare_r // 2, by - 50 + flare_r // 2)], fill=(234, 179, 8, 255))
    
    draw.rectangle([(bx - 70, by - 90), (bx + 10, by - 10)], outline=(239, 68, 68), width=3)
    draw.text((bx - 70, by - 120), "TARGET LOCK: 0.8s TO IMPACT", font=get_font_safe(16, mono=True), fill=(239, 68, 68))
    
    # Urgent Radio Wire & Waveform Banner at Bottom
    draw.rounded_rectangle([(80, H - 230), (W - 80, H - 70)], radius=12, fill=(10, 25, 15, 245), outline=(34, 197, 94), width=2)
    for wx in range(100, 360, 8):
        h_wave = int(math.sin(t_sub * 12 + wx * 0.1) * 22)
        draw.line([(wx, H - 150 - h_wave), (wx, H - 150 + h_wave)], fill=(34, 197, 94), width=3)
        
    draw.text((100, H - 215), "SECURE COMBAT NET // 2004 BAKERY INCIDENT", font=get_font_safe(16, mono=True), fill=(234, 179, 8))
    draw.text((380, H - 195), "URGENT INTERCEPT: \"CEASE FIRE! CEASE FIRE! IT'S A BAKERY!\"", font=get_pop_font(24), fill=(239, 68, 68))
    draw.text((380, H - 155), "FRIENDLY PLATOON MARKED SILL WITH BLUE WAX PENCIL // 12 LIVES SAVED", font=get_font_safe(18), fill=(255, 255, 255))
    draw.text((380, H - 120), "RESULT: MAIN GUN TRAVERSED 40° LEFT // TRIGGER ABORTED WITH 0.8s LEFT", font=get_pop_font(18), fill=(34, 197, 94))
    
    frame.alpha_composite(pilot_img, (W - pilot_img.width - 60, H - pilot_img.height - 20))
    draw_pop_title(draw, sub_title)


def render_ticking_budget_counter(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_shock: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(10, 15, 26))
    draw.rectangle([(0, 0), (W, 70)], fill=(15, 23, 42))
    draw.text((60, 20), "CONGRESSIONAL DEFENSE PROCUREMENT CLOCK // COST ESCALATION MATRIX", font=get_pop_font(24), fill=(234, 179, 8))
    draw.text((W - 400, 24), "AUDIT COMMITTEE: H.R. 5422", font=get_font_safe(18, mono=True), fill=(148, 163, 184))
    
    if t_sub < 1.5:
        p = t_sub / 1.5
        val = int(0.85 + (1400000 - 0.85) * (p ** 2))
    elif t_sub < 3.0:
        p = (t_sub - 1.5) / 1.5
        val = int(1400000 + (86000000 - 1400000) * (p ** 2))
    else:
        p = min(1.0, (t_sub - 3.0) / 2.0)
        val = int(86000000 + (16800000000 - 86000000) * (p ** 1.8))
        
    val_str = f"${val:,.2f}" if val < 1000 else f"${val:,.0f}"
    
    draw.rounded_rectangle([(100, 110), (W - 100, 250)], radius=16, fill=(15, 23, 42, 245), outline=(34, 197, 94), width=3)
    draw.text((140, 130), "CURRENT CUMULATIVE PROCUREMENT INVOICE:", font=get_font_safe(18, mono=True), fill=(148, 163, 184))
    draw.text((140, 160), val_str, font=get_pop_font(68), fill=(34, 197, 94))
    
    milestones = [
        ("01. BASELINE ANALOG CRAYON", "$0.85", "Off-the-shelf industrial wax grease pencil", (34, 197, 94)),
        ("02. MK-II HARDENED APPLICATOR", "$1,400,000", "Titanium casing with ergonomic pocket clip", (56, 189, 248)),
        ("03. ULTRASONIC 40-kHz INSCRIBER", "$86,000,000", "Vibrating core (alerted all dogs in 2-mile radius)", (234, 179, 8)),
        ("04. AUTONOMOUS ROBOT DOG FLEET", "$16,800,000,000", "Quadruped robot (trapped in razor wire after 11 min)", (239, 68, 68)),
    ]
    
    start_y = 280
    for i, (m_title, m_cost, m_desc, m_col) in enumerate(milestones):
        y = start_y + i * 115
        is_active = (i == 0) or (i == 1 and t_sub >= 1.0) or (i == 2 and t_sub >= 2.2) or (i == 3 and t_sub >= 3.2)
        border_col = m_col if is_active else (51, 65, 85)
        bg_fill = (20, 30, 48, 240) if is_active else (15, 23, 42, 180)
        
        draw.rounded_rectangle([(100, y), (1350, y + 95)], radius=10, fill=bg_fill, outline=border_col, width=2)
        draw.text((130, y + 16), m_title, font=get_pop_font(22), fill=m_col if is_active else (100, 116, 139))
        draw.text((130, y + 54), m_desc, font=get_font_safe(16), fill=(203, 213, 225) if is_active else (71, 85, 105))
        draw.text((1000, y + 25), m_cost, font=get_pop_font(34), fill=m_col if is_active else (100, 116, 139))

    if t_sub >= 1.8 and t_sub < 3.2:
        stamp = get_cached_stamp("DENIED BY OVERSIGHT", -8, (239, 68, 68))
        frame.alpha_composite(stamp, (920, 150))
    elif t_sub >= 3.2:
        stamp = get_cached_stamp("APPROVED BY CONGRESS", -5, (34, 197, 94))
        frame.alpha_composite(stamp, (920, 150))

    frame.alpha_composite(host_shock, (W - host_shock.width - 20, H - host_shock.height - 20))
    draw_pop_title(draw, sub_title)


def render_comm_split_screen(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, ceo_img: Image.Image, general_img: Image.Image, pilot_img: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(8, 14, 22))
    
    p_w = 600
    gap = 20
    x1, x2, x3 = 30, 30 + p_w + gap, 30 + (p_w + gap) * 2
    y_top, p_h = 100, 780
    
    if t_sub < 2.5:
        active_speaker = 1
    elif t_sub < 5.0:
        active_speaker = 2
    else:
        active_speaker = 3
        
    is_aviation = any(w in _CURRENT_CHANNEL_ID for w in ("blackbox", "aviation", "flight")) or any(w in str(scene_data).lower() for w in ("flight", "boeing", "airbus", "pilot", "cockpit", "atc", "cvr", "ntsb", "squawk", "mayday"))
    if is_aviation:
        capt_sprite = load_character_sprite("CAPTAIN", 460)
        fo_sprite = load_character_sprite("FIRST_OFFICER", 460)
        atc_sprite = load_character_sprite("ATC", 460)
        panels = [
            (1, x1, "CAPTAIN (PILOT IN COMMAND)", "COCKPIT // LEFT SEAT", capt_sprite),
            (2, x2, "FIRST OFFICER (CO-PILOT)", "COCKPIT // RIGHT SEAT", fo_sprite),
            (3, x3, "AIR TRAFFIC CONTROLLER", "AREA CONTROL CENTER // RADAR", atc_sprite),
        ]
        comm_banner = "COCKPIT VOICE RECORDER (CVR) & ATC FREQUENCY // EMERGENCY CHANNEL ACTIVE"
    else:
        panels = [
            (1, x1, "DEFENSE CONTRACTOR CEO", "CORP HQ // ARLINGTON, VA", ceo_img),
            (2, x2, "JOINT CHIEFS GENERAL", "THE PENTAGON // WAR ROOM", general_img),
            (3, x3, "M1 ABRAMS GUNNER / PILOT", "FORWARD COMBAT LINE", pilot_img),
        ]
        comm_banner = "SECURE TRI-SERVICE COMM LINK // DISCUSSION TOPIC: DEFENSE SPECIFICATION"
    
    for p_id, px, title, loc, sprite in panels:
        is_active = (p_id == active_speaker)
        border_col = (34, 197, 94) if is_active else (51, 65, 85)
        border_w = 4 if is_active else 2
        bg_fill = (15, 23, 42) if is_active else (10, 16, 26)
        
        draw.rounded_rectangle([(px, y_top), (px + p_w, y_top + p_h)], radius=14, fill=bg_fill, outline=border_col, width=border_w)
        header_fill = (22, 101, 52) if is_active else (30, 41, 59)
        draw.rounded_rectangle([(px, y_top), (px + p_w, y_top + 60)], radius=14, fill=header_fill)
        draw.text((px + 20, y_top + 14), title, font=get_pop_font(20), fill=(255, 255, 255))
        draw.text((px + 20, y_top + 70), f"LOC: {loc}", font=get_font_safe(14, mono=True), fill=(148, 163, 184))
        
        spr_resized = get_cached_panel_sprite(sprite, 460)
        spr_x = px + (p_w - spr_resized.width) // 2
        spr_y = y_top + p_h - spr_resized.height - 40
        frame.alpha_composite(spr_resized, (spr_x, spr_y))
        
        if is_active:
            eq_y = y_top + 100
            draw.text((px + 20, eq_y), "AUDIO COMM ACTIVE", font=get_font_safe(14, mono=True), fill=(34, 197, 94))
            for b_i in range(14):
                bh = int(8 + math.sin(t_sub * 16 + b_i * 0.8) * 18 + 12)
                draw.rectangle([(px + 240 + b_i * 22, eq_y + 20 - bh), (px + 254 + b_i * 22, eq_y + 20)], fill=(34, 197, 94))
        else:
            for sy in range(y_top + 65, y_top + p_h - 10, 6):
                draw.line([(px + 4, sy), (px + p_w - 4, sy)], fill=(10, 16, 26, 120), width=2)
                
    draw.rounded_rectangle([(30, H - 120), (W - 30, H - 40)], radius=10, fill=(15, 23, 42, 245), outline=(56, 189, 248), width=2)
    draw.text((60, H - 95), comm_banner, font=get_pop_font(20), fill=(56, 189, 248))
    draw_pop_title(draw, sub_title)


def render_foreign_intel_dossier(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, host_point: Image.Image, spy_img: Image.Image, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(28, 22, 16))
    
    doc_x, doc_y, doc_w, doc_h = 100, 80, W - 200, H - 160
    draw.rounded_rectangle([(doc_x, doc_y), (doc_x + doc_w, doc_y + doc_h)], radius=12, fill=(232, 224, 206), outline=(120, 95, 70), width=3)
    
    draw.rectangle([(doc_x + 40, doc_y + 30), (doc_x + 560, doc_y + 80)], fill=(185, 28, 28))
    draw.text((doc_x + 55, doc_y + 42), "TOP SECRET // SOVIET / FOREIGN INTEL INTERCEPT", font=get_pop_font(20), fill=(255, 255, 255))
    draw.text((doc_x + doc_w - 420, doc_y + 45), "DOSSIER ARCHIVE: #84-AKRON-OHIO", font=get_font_safe(16, mono=True), fill=(60, 45, 30))
    
    # Left Section: Laboratory Spectrograph Breakdown
    lx, ly = doc_x + 60, doc_y + 120
    draw.rounded_rectangle([(lx, ly), (lx + 760, ly + 460)], radius=8, fill=(245, 240, 228), outline=(160, 140, 115), width=2)
    draw.text((lx + 30, ly + 20), "STATE CHEMICAL LABORATORY SPECTROGRAPHIC TEST", font=get_pop_font(20), fill=(40, 30, 20))
    draw.line([(lx + 40, ly + 280), (lx + 720, ly + 280)], fill=(80, 60, 40), width=2)
    draw.line([(lx + 40, ly + 80), (lx + 40, ly + 280)], fill=(80, 60, 40), width=2)
    
    spectrum_pts = [
        (lx + 40, ly + 280), (lx + 100, ly + 270), (lx + 140, ly + 120), (lx + 180, ly + 260),
        (lx + 240, ly + 275), (lx + 300, ly + 90), (lx + 340, ly + 270), (lx + 420, ly + 275),
        (lx + 480, ly + 140), (lx + 520, ly + 270), (lx + 600, ly + 280), (lx + 720, ly + 280)
    ]
    draw.line(spectrum_pts, fill=(185, 28, 28), width=3)
    draw.text((lx + 110, ly + 90), "PEAK: PARAFFIN WAX", font=get_font_safe(14, bold=True), fill=(185, 28, 28))
    draw.text((lx + 270, ly + 65), "PEAK: STEARIC ACID", font=get_font_safe(14, bold=True), fill=(185, 28, 28))
    draw.text((lx + 450, ly + 110), "PEAK: RED PIGMENT #40", font=get_font_safe(14, bold=True), fill=(185, 28, 28))
    
    draw.text((lx + 40, ly + 310), "CHEMICAL COMPOSITION: 100% PARAFFIN (HYDROCARBON CH2 CHAIN)", font=get_font_safe(16, mono=True), fill=(40, 30, 20))
    draw.text((lx + 40, ly + 340), "MELTING POINT: 48.5°C // ZERO AEROSPACE COMPOSITE DETECTED", font=get_font_safe(16, mono=True), fill=(185, 28, 28))
    draw.text((lx + 40, ly + 370), "SOURCE: COMMERCIALLY REPACKAGED PRESCHOOL WAX STICKS", font=get_font_safe(16, mono=True), fill=(40, 30, 20))
    draw.text((lx + 40, ly + 400), "PROCUREMENT COST RATIO: 32,000x MARKUP BY DEFENSE CONTRACTORS", font=get_pop_font(18), fill=(185, 28, 28))

    # Right Section: Pinned Polaroid of the $8 Crayons
    rx, ry = doc_x + 860, doc_y + 120
    draw.rounded_rectangle([(rx, ry), (rx + 420, ry + 420)], radius=6, fill=(255, 255, 255), outline=(180, 160, 140), width=2)
    draw.rectangle([(rx + 50, ry + 40), (rx + 370, ry + 320)], fill=(234, 179, 8), outline=(202, 138, 4), width=3)
    draw.rectangle([(rx + 80, ry + 80), (rx + 340, ry + 180)], fill=(34, 197, 94))
    draw.text((rx + 110, ry + 115), "CRAYOLA 64", font=get_pop_font(32), fill=(255, 255, 255))
    draw.text((rx + 90, ry + 210), "ORIGIN: AKRON, OHIO", font=get_pop_font(20), fill=(15, 23, 42))
    draw.text((rx + 90, ry + 250), "RETAIL PRICE: $8.00", font=get_pop_font(26), fill=(185, 28, 28))
    draw.arc([(rx + 40, ry - 15), (rx + 80, ry + 35)], start=180, end=360, fill=(100, 100, 100), width=4)
    draw.line([(rx + 40, ry + 10), (rx + 40, ry + 60)], fill=(100, 100, 100), width=4)
    draw.line([(rx + 80, ry + 10), (rx + 80, ry + 60)], fill=(100, 100, 100), width=4)
    
    cx_box = doc_x + 60
    cy_box = doc_y + 600
    draw.rounded_rectangle([(cx_box, cy_box), (doc_x + doc_w - 60, cy_box + 120)], radius=8, fill=(240, 235, 220), outline=(120, 95, 70), width=2)
    draw.text((cx_box + 30, cy_box + 16), "INTELLIGENCE ASSESSMENT & DIRECTIVE:", font=get_pop_font(22), fill=(185, 28, 28))
    draw.text((cx_box + 30, cy_box + 50), "\"The Americans spent $54 Billion attempting to reverse-engineer standard wax.", font=get_font_safe(18), fill=(40, 30, 20))
    draw.text((cx_box + 30, cy_box + 80), "Do not replicate. Allow them to bankrupt themselves with defense markups.\"", font=get_pop_font(18), fill=(185, 28, 28))
    
    stamp = get_cached_stamp("CLASSIFIED KGB", -12, (185, 28, 28))
    frame.alpha_composite(stamp, (doc_x + doc_w - 380, doc_y + 530))
    frame.alpha_composite(spy_img, (W - spy_img.width - 20, H - spy_img.height - 20))
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
    (["EXPLODED_PATENT", "FINANCIAL_AUDIT", "SPLIT_CIVIL", "PENTAGON_AUDIT"],
     ["EXPLODED SCHEMATIC: $280 PREP SPONGE!", "AUTOMOTIVE SANDPAPER IN BALLISTIC BOX", "32,000x TAXPAYER COST MARKUP!", "CONGRESSIONAL OVERSIGHT CROSS-EXAMINATION"]),
    # Scene 08: Congress Grills the Budget / Thermal Blooming
    (["FLIR_BAKERY_INCIDENT", "TACTICAL_RADAR", "EMERGENCY_LOCKDOWN", "PENTAGON_AUDIT"],
     ["FLIR THERMAL NIGHT VISION OVERLOAD!", "INFRARED BLOOMING UNDER ENEMY SCOPES!", "CARBON WAX GLOWING LIKE A NEON SIGN!", "CONGRESS SUBPOENAS SENSOR TELEMETRY"]),
    # Scene 09: Dawn Patrol Drone Thermal Cameras
    (["TACTICAL_RADAR", "MACRO_BLUEPRINT", "FOREIGN_INTELLIGENCE", "KEN_BURNS"],
     ["UAV DAWN PATROL THERMAL SURVEILLANCE!", "WAX EMITTING 850nm THERMAL GLOW!", "HOSTILE DRONE INTERCEPTS COLD TARGET!", "GLOBAL HAWK STRATEGIC FLIR RECORDING"]),
    # Scene 10: CAS Pilots Scanning Ground Markers
    (["COCKPIT_HUD", "FLOW_CHAIN", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"],
     ["CLOSE AIR SUPPORT SIGHT RETICLE BLINDED!", "THERMAL BLOOM FORCES MISSION ABORT!", "CAUTION: FLIR NIGHT VISION BLOOM!", "TACTICAL STRIKE HAZARD DETECTED!"]),
    # Scene 11: Low-Emissivity Formulation
    (["TICKING_BUDGET", "LAB_RND", "SPLIT_CIVIL", "FINANCIAL_AUDIT"],
     ["$62M LOW-EMISSIVITY BUDGET ESCALATION!", "PROCUREMENT CLOCK JUMPS BY MILLIONS", "APPROVED BY CONGRESSIONAL APPROPRIATION", "CERAMIC DIELECTRIC PIGMENT ADJUSTMENT"]),
    # Scene 12: Map Over-Marking Clutter
    (["BLUEPRINT_SYMBOL_HUD", "DESK_BRIEFING", "MACRO_BLUEPRINT", "FLOW_CHAIN"],
     ["MAP OVER-MARKING CLUTTER MATRIX!", "5 OVERLAPPING LAYERS BLIND STAFF OFFICERS", "CONTOUR LINES OBLITERATED COMPLETELY", "WHEN MILITARY DOCTRINE BLINDS THE BATTLEFIELD"]),
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
    (["COMM_SPLIT_SCREEN", "FLOW_CHAIN", "EMERGENCY_LOCKDOWN", "PENTAGON_AUDIT"],
     ["HEATING MARKERS IN HUMVEE DEFROST VENTS!", "TRI-SERVICE TACTICAL AUDIO LINK!", "WAX VAPORIZES INTO DEFROST VENTS!", "CONGRESS INVESTIGATES CREW INCIDENT!"]),
    # Scene 21: Distress Symbology Crisis
    (["BLUEPRINT_SYMBOL_HUD", "URBAN_STREET", "MACRO_BLUEPRINT", "DESK_BRIEFING"],
     ["TACTICAL DISTRESS SYMBOLOGY MATRIX!", "URBAN SEARCH 4-QUADRANT BLUEPRINT HUD!", "MISPLACED CHEVRON: FRIENDLY FIRE HAZARD!", "THE SECRET DOCTRINE OF COMBAT MARKING!"]),
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
    (["BLUEPRINT_SYMBOL_HUD", "URBAN_STREET", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["DOOR SYMBOL // 4-QUADRANT BLUEPRINT MATRIX!", "PENTAGON RE-EVALUATION COST: $42,000,000", "MISSION-CRITICAL ENTRY & HAZARD QUADRANTS", "SOLDIER APPLICATION TIME: 2.1s ($0.00)"]),
    # Scene 07: Polycarbonate Tactical Quadrant Shield
    (["EXPLODED_PATENT", "SPLIT_CIVIL", "PENTAGON_AUDIT", "CRT_MAINFRAME"],
     ["OVER-ENGINEERED DEFENSE PATENT #884219!", "$1,200 POLYCARBONATE WALL SHIELD!", "TITANIUM HEX ANCHOR BOLTS: $4,500/EACH", "CONGRESS QUESTIONS ZERO-COMBAT VALUE"]),
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
    (["COMM_SPLIT_SCREEN", "FOREIGN_INTELLIGENCE", "PENTAGON_AUDIT", "DESK_BRIEFING"],
     ["TRI-SERVICE SECURE LINK // HEATED DEBATE!", "CONTRACTOR CEO VS PENTAGON GENERAL", "WHY DID WE ALLOCATE $1.8B FOR WAX?", "BATTLEFIELD OPERATORS DEMAND SIMPLICITY"]),
    # Scene 16: Symbol #6: Ballistic Breaching Anchor
    (["SYMBOL_BREACH", "MACRO_BLUEPRINT", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["SYMBOL #6: BALLISTIC BREACHING ANCHOR!", "C4 DEMOLITION STANDOFF BRACKET", "MARKING LOAD-BEARING PILLARS", "CALCULATING SHAPED-CHARGE BLAST ARCS"]),
    # Scene 17: Demolition Standoff Marking
    (["URBAN_STREET", "SYMBOL_BREACH", "MACRO_BLUEPRINT", "PENTAGON_AUDIT"],
     ["DEMO TEAMS INSCRIBE C4 STANDOFF ON REBAR", "PROTECTING BREACHERS FROM WALL COLLAPSE", "MINIMUM SAFE DISTANCE CALCULATIONS", "TACTICAL PRECISION SAVES ENTRY SQUADS"]),
    # Scene 18: Ultrasonic Resonant Wax Inscriber
    (["EXPLODED_PATENT", "LAB_RND", "FINANCIAL_AUDIT", "CRT_MAINFRAME"],
     ["EXPLODED VIEW: 40-kHz ULTRASONIC INSCRIBER!", "$125,000 K9 AGGRAVATION TRANSDUCER", "BATTERIES CRACK UNDER RIFLE RECOIL", "CONCRETE ENGRAVING FIASCO REVEALED"]),
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
    (["URBAN_STREET", "FLIR_BAKERY_INCIDENT", "FLOW_CHAIN", "KEN_BURNS"],
     ["CASE STUDY: THE NEAR FRIENDLY-FIRE RAID!", "FLIR NIGHT VISION RECON OVER CITY", "SPECIAL FORCES SQUAD PINNED IN BASEMENT", "ANALOG WAX MARK ON SILL ONLY DEFENSE"]),
    # Scene 24: M1 Abrams Tank Approaches
    (["FLIR_BAKERY_INCIDENT", "TANK_SIGHT", "EMERGENCY_LOCKDOWN", "COMM_SPLIT_SCREEN"],
     ["FLIR THERMAL LOCK ON INDUSTRIAL BAKERY!", "M1 ABRAMS GUNNER SLEWS 120mm CANNON!", "'CEASE FIRE! CEASE FIRE! IT'S A BAKERY!'", "TRIGGER ABORTED WITH 0.8 SECONDS LEFT!"]),
    # Scene 25: Day Sight Identifies Friendly Chevron
    (["TANK_SIGHT", "FLIR_BAKERY_INCIDENT", "FLOW_CHAIN", "DESK_BRIEFING"],
     ["GUNNER SPOTS TACTICAL WAX CHEVRON!", "3-POWER OPTICAL DAY SIGHT SEES MARK", "MAIN GUN TRAVERSED 40° LEFT TO NEST", "12 FRIENDLY SOLDIERS SURVIVED"]),
    # Scene 26: Corporate PR Spins Incident
    (["TICKING_BUDGET", "PENTAGON_AUDIT", "SPLIT_CIVIL", "KEN_BURNS"],
     ["PENTAGON PROCUREMENT ESCALATION CLOCK!", "FROM $0.85 CRAYON TO $16.8 BILLION FLEET", "RED TAPE SLAMMED: APPROVED BY CONGRESS!", "CONTRACTORS SPIN NEAR-MISS INTO PR WIN"]),
    # Scene 27: Intel Tests $1 Crayon vs $850 Kit
    (["FOREIGN_INTEL_DOSSIER", "SPLIT_CIVIL", "PENTAGON_AUDIT", "DESK_BRIEFING"],
     ["TOP SECRET KGB DOSSIER: THE OHIO CRAYON!", "SPECTROGRAPH TEST: 100% PARAFFIN WAX", "$8.00 PRESCHOOL BOX IN DEFENSE CRATES", "ZERO DEFENSE VALUE: PENTAGON SCAM"]),
    # Scene 28: CSAR Pilot Rescue Symbology
    (["FOREIGN_INTEL_DOSSIER", "FOREIGN_INTELLIGENCE", "SPLIT_CIVIL", "DESK_BRIEFING"],
     ["DECLASSIFIED DOSSIER: 100% AKRON OHIO PARAFFIN", "ZERO MILITARY COMPOSITE FORMULA DETECTED", "'DO NOT REPLICATE: ALLOW THEM TO SPEND BILLIONS'", "HOW DEFENSE CONTRACTORS FLEECE AUDITS"]),
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

    is_tactical_crayon = (
        _CURRENT_TOPIC_CATEGORY in ("crayon_combat", "military", "military_tech")
        or any(name in _CURRENT_CHANNEL_ID for name in ("tacticallcrayon", "tacticalcrayon"))
    )
    is_crayon_capital = _CURRENT_TOPIC_CATEGORY in ("crayon_capital", "tech_finance_essay")
    if is_tactical_crayon or is_crayon_capital:
        modes = ["CRAYON_HOOK", "CRAYON_VISUAL", "CRAYON_EVIDENCE", "CRAYON_REACTION"]
        shot_count = max(1, min(len(modes), int(round(dur / 5.0))))
        offset = 0 if idx == 0 else idx % len(modes)
        shots = [modes[(offset + shot_idx) % len(modes)] for shot_idx in range(shot_count)]
        return shots, shots

    is_v2 = any(w in v_str for w in ["combat marking", "symbology", "54", "slash", "quadrant", "chevron", "triage", "breaching", "anchor", "robot dog"])
    if is_v2 and idx < len(V2_BESPOKE_PLAN):
        return V2_BESPOKE_PLAN[idx]

    if not is_v2 and idx < len(V1_BESPOKE_PLAN):
        return V1_BESPOKE_PLAN[idx]
        
    # High-retention semantic archetype & kinetic shot selector for arbitrary topics/videos
    text = (narr + " " + ch).lower()
    
    # Candidate archetypes evaluated by topical relevance
    candidates = []
    
    # 6 Bespoke High-Impact Satirical / Defense Archetypes
    if any(k in text for k in ["door", "quadrant", "chevron", "marking", "chalk", "slash", "x-mark", "triage", "breach", "fema", "symbol"]):
        candidates.append("BLUEPRINT_SYMBOL_HUD")
    if any(k in text for k in ["patent", "exploded", "bolt", "ultrasonic", "overengineer", "polycarbonate", "shield", "transducer", "sponge"]):
        candidates.append("EXPLODED_PATENT")
    if any(k in text for k in ["flir", "bakery", "thermal", "infrared", "crosshair", "cease fire", "lock-on", "target", "blooming"]):
        candidates.append("FLIR_BAKERY_INCIDENT")
    if any(k in text for k in ["budget", "price tag", "taxpayer", "cost counter", "odometer", "appropriation", "billion", "million"]):
        candidates.append("TICKING_BUDGET")
    if any(k in text for k in ["split-screen", "comm", "radio", "dialogue", "norad", "calling", "air support", "pentagon link", "link"]):
        candidates.append("COMM_SPLIT_SCREEN")
    if any(k in text for k in ["kgb", "soviet", "dossier", "paraffin", "spectrograph", "chemical", "intelligence report", "wax", "classified"]):
        candidates.append("FOREIGN_INTEL_DOSSIER")
    
    if any(k in text for k in ["radar", "stealth", "frequency", "sensor", "jamming", "telemetry", "signature", "sonar", "decibel", "electronic warfare"]):
        candidates.append("TACTICAL_RADAR")
    if any(k in text for k in ["cockpit", "pilot", "mach", "flight", "altitude", "thrust", "airframe", "afterburner", "supersonic", "g-force"]):
        candidates.append("COCKPIT_HUD")
    if any(k in text for k in ["map", "border", "russia", "china", "arctic", "ocean", "theater", "strait", "territory", "pacific", "ukraine", "base"]):
        candidates.append("TACTICAL_MAP")
    if any(k in text for k in ["lab", "engineer", "thermal", "laser", "coating", "stress", "temperature", "ceramic", "synthetic", "physics"]):
        candidates.append("LAB_RND")
    if any(k in text for k in ["blueprint", "cad", "schematic", "internal", "structure", "engine", "cross-section", "cutaway", "tolerance"]):
        candidates.append("MACRO_BLUEPRINT")
    if any(k in text for k in ["audit", "pentagon", "congress", "senate", "subpoena", "hearing", "committee", "investigation", "contractor", "ceo"]):
        candidates.append("PENTAGON_AUDIT")
    if any(k in text for k in ["commercial", "civilian", "shelf", "cots", "hardware", "vs", "versus", "standard issue", "home depot", "store"]):
        candidates.append("SPLIT_CIVIL")
    if any(k in text for k in ["danger", "hazard", "fatal", "fail", "flame", "lockdown", "emergency", "fire", "catastrophe", "critical"]):
        candidates.append("EMERGENCY_LOCKDOWN")
    if any(k in text for k in ["chain", "cascade", "domino", "result", "caused", "because", "sequence", "step", "escalation"]):
        candidates.append("FLOW_CHAIN")
    if any(k in text for k in ["memo", "directive", "quote", "classified wire", "terminal", "order", "bulletin", "statement"]):
        candidates.append("CRT_MAINFRAME")
    if any(k in text for k in ["tank", "gunner", "sight", "optic", "reticle", "crosshair", "abrams", "turret", "aim"]):
        candidates.append("TANK_SIGHT")
    if any(k in text for k in ["robot", "dog", "unmanned", "autonomous", "quadruped", "ugv", "wire"]):
        candidates.append("ROBOT_DOG")
    if any(k in text for k in ["urban", "street", "building", "infantry", "patrol", "door", "window", "city"]):
        candidates.append("URBAN_STREET")
    if any(k in text for k in ["real", "history", "rollout", "usaf", "photo", "flight test", "hangar", "edwards", "plant 42"]):
        candidates.append("KEN_BURNS")

    # Fallback rotation pool ensuring maximum kinetic variety
    default_pool = [
        "BLUEPRINT_SYMBOL_HUD", "EXPLODED_PATENT", "FLIR_BAKERY_INCIDENT",
        "TICKING_BUDGET", "COMM_SPLIT_SCREEN", "FOREIGN_INTEL_DOSSIER",
        "URBAN_STREET", "MACRO_BLUEPRINT", "FLOW_CHAIN", "DESK_BRIEFING",
        "SPLIT_CIVIL", "FINANCIAL_AUDIT", "PENTAGON_AUDIT", "KEN_BURNS",
        "TACTICAL_RADAR", "COCKPIT_HUD", "EMERGENCY_LOCKDOWN", "LAB_RND",
        "TACTICAL_MAP", "FOREIGN_INTELLIGENCE", "CRT_MAINFRAME", "DESK_BRIEFING"
    ]
    
    # Pick 4 distinct archetypes
    selected = []
    for c in candidates:
        if c not in selected:
            selected.append(c)
        if len(selected) >= 4:
            break
            
    # Fill remaining from default_pool offset by idx
    offset = (idx * 3) % len(default_pool)
    for i in range(len(default_pool)):
        candidate = default_pool[(offset + i) % len(default_pool)]
        if candidate not in selected:
            selected.append(candidate)
        if len(selected) >= 4:
            break

    # Dynamic, high-impact defense titles in 100% English
    ch_clean = scene_data.get("chapter", vehicle_name).upper()
    ch_clean = re.sub(r'[^A-Z0-9\s\-\:]', '', ch_clean).strip()
    if not ch_clean: ch_clean = vehicle_name.upper()

    is_aviation = any(w in _CURRENT_CHANNEL_ID for w in ("blackbox", "aviation", "flight")) or any(w in str(scene_data).lower() for w in ("flight", "boeing", "airbus", "pilot", "cockpit", "atc", "cvr", "ntsb", "crash", "squawk"))
    if is_aviation:
        titles = [
            f"{ch_clean[:24]}: CVR FLIGHT DECK",
            "NTSB FORENSIC FLIGHT DATA ANALYSIS",
            "ATC RADAR & SQUAWK 7700 TELEMETRY",
            "INVESTIGATION VERDICT & SAFETY LESSONS"
        ]
    else:
        titles = [
            f"{ch_clean[:24]}: FIELD DOSSIER",
            "TECHNICAL INVESTIGATION ANALYSIS",
            "OPERATIONAL COMBAT TELEMETRY",
            "PENTAGON AUDIT REQUISITION"
        ]
    return selected[:4], titles


def _short_visual_phrase(text: str, max_words: int = 6) -> str:
    words = re.findall(r"[A-Za-z0-9$€£%.,'-]+", str(text or ""))
    return " ".join(words[:max_words]).strip(" ,.-")


def render_crayon_kinetic_shot(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    scene_data: dict,
    shot_type: str,
    t_sub: float,
    duration: float,
    speaker_img: Image.Image,
    topic_category: str = "",
) -> None:
    is_finance = topic_category in ("crayon_capital", "tech_finance_essay")
    accent = (255, 190, 55) if is_finance else (69, 211, 190)
    pale = (235, 243, 250)
    muted = (145, 164, 184)
    progress = min(1.0, max(0.0, t_sub / max(duration, 0.1)))
    chapter = str(scene_data.get("chapter") or "THE QUESTION").strip()
    narration = str(scene_data.get("narration") or "").strip()
    short_phrase = _short_visual_phrase(narration)
    heading_font = get_font_safe(31, mono=True)
    title_font = get_pop_font(76)
    phrase_font = get_pop_font(52)

    draw.rectangle((70, 58, W - 70, H - 58), outline=(56, 73, 93), width=2)
    draw.text((112, 92), chapter[:48].upper(), font=heading_font, fill=accent)
    draw.line((110, 150, W - 110, 150), fill=(54, 70, 89), width=2)
    scan_x = int(190 + progress * 1450)
    draw.line((scan_x, 180, scan_x, 860), fill=(*accent, 125), width=3)

    if shot_type == "CRAYON_HOOK":
        phrase = _short_visual_phrase(narration, 7) or _short_visual_phrase(chapter, 7) or "THE QUESTION"
        draw.rounded_rectangle((170, 285, W - 170, 665), radius=22, fill=(10, 17, 29), outline=accent, width=4)
        draw.text((225, 335), "THE DETAIL THAT CHANGES THE STORY", font=heading_font, fill=muted)
        for line_no, line in enumerate(textwrap.wrap(phrase.upper(), width=26)[:2]):
            draw.text((220, 420 + line_no * 92), line, font=title_font, fill=pale)
        pulse = int(18 + 12 * abs(math.sin(t_sub * 4)))
        draw.ellipse((W - 430 - pulse, 680 - pulse, W - 370 + pulse, 740 + pulse), outline=accent, width=5)
    elif shot_type == "CRAYON_VISUAL":
        draw.text((135, 208), "ILLUSTRATIVE VISUAL", font=heading_font, fill=muted)
        if is_finance:
            left_x, right_x, center_y = 410, 1450, 520
            draw.rounded_rectangle((left_x - 190, center_y - 105, left_x + 190, center_y + 105), radius=24, fill=(21, 35, 51), outline=accent, width=4)
            draw.rounded_rectangle((right_x - 190, center_y - 105, right_x + 190, center_y + 105), radius=24, fill=(21, 35, 51), outline=(231, 93, 99), width=4)
            draw.text((left_x - 100, center_y - 22), "CAPITAL", font=phrase_font, fill=pale)
            draw.text((right_x - 120, center_y - 22), "OUTCOME", font=phrase_font, fill=pale)
            draw.line((left_x + 205, center_y, right_x - 215, center_y), fill=accent, width=12)
            for dot_idx in range(4):
                dot_x = int(left_x + 225 + ((progress * 700 + dot_idx * 175) % 700))
                draw.ellipse((dot_x - 12, center_y - 12, dot_x + 12, center_y + 12), fill=pale)
            draw.text((300, 745), short_phrase.upper(), font=phrase_font, fill=accent)
        else:
            topic = (chapter + " " + narration).lower()
            cx, cy = 960, 530
            sway = int(26 * math.sin(t_sub * 2.7))
            if any(word in topic for word in ("tank", "armour", "armor", "vehicle")):
                draw.rounded_rectangle((cx - 330 + sway, cy - 20, cx + 330 + sway, cy + 190), radius=55, fill=(65, 80, 70), outline=accent, width=6)
                draw.rectangle((cx - 180 + sway, cy - 125, cx + 190 + sway, cy + 5), fill=(83, 101, 87), outline=accent, width=5)
                draw.line((cx + sway, cy - 85, cx + 360 + sway, cy - 85), fill=pale, width=28)
                for wheel_x in range(cx - 230 + sway, cx + 260 + sway, 105):
                    draw.ellipse((wheel_x - 42, cy + 115, wheel_x + 42, cy + 195), fill=(22, 30, 31), outline=accent, width=4)
            elif any(word in topic for word in ("aircraft", "fighter", "bomber", "jet", "flight", "pilot")):
                points = [(cx - 340 + sway, cy), (cx - 55 + sway, cy - 55), (cx + 35 + sway, cy - 255), (cx + 125 + sway, cy - 255), (cx + 90 + sway, cy - 65), (cx + 340 + sway, cy - 5), (cx + 340 + sway, cy + 45), (cx + 80 + sway, cy + 28), (cx + 30 + sway, cy + 205), (cx - 45 + sway, cy + 205), (cx - 90 + sway, cy + 20), (cx - 340 + sway, cy + 45)]
                draw.polygon(points, fill=(65, 92, 111), outline=accent)
            else:
                marker_x = cx + sway
                draw.rounded_rectangle((marker_x - 330, cy - 68, marker_x + 225, cy + 68), radius=55, fill=(46, 107, 120), outline=accent, width=6)
                draw.polygon([(marker_x + 225, cy - 68), (marker_x + 355, cy), (marker_x + 225, cy + 68)], fill=(208, 199, 163), outline=accent)
                draw.rectangle((marker_x - 375, cy - 68, marker_x - 318, cy + 68), fill=(31, 41, 55), outline=accent, width=4)
            draw.text((280, 790), short_phrase.upper(), font=phrase_font, fill=accent)
    elif shot_type == "CRAYON_EVIDENCE":
        draw.rounded_rectangle((250, 228, 1250, 780), radius=20, fill=(231, 237, 240), outline=accent, width=4)
        draw.text((310, 275), "CLAIM UNDER REVIEW", font=heading_font, fill=(39, 54, 68))
        draw.line((310, 335, 1170, 335), fill=(99, 116, 131), width=3)
        for line_no, line in enumerate(textwrap.wrap(short_phrase or chapter, width=27)[:2]):
            draw.text((315, 405 + line_no * 82), line.upper(), font=phrase_font, fill=(32, 46, 60))
        for row in range(4):
            y = 590 + row * 38
            reveal = max(0, min(860, int((progress * 4 - row) * 220)))
            draw.rounded_rectangle((315, y, 315 + reveal, y + 12), radius=6, fill=accent)
    else:
        draw.text((155, 208), "THE HUMAN REACTION", font=heading_font, fill=muted)
        char_w, char_h = speaker_img.size
        char_x, char_y = 1160, 300 + int(20 * math.sin(t_sub * 3))
        frame.alpha_composite(speaker_img, (char_x, char_y))
        dialogue = str(scene_data.get("character_dialogue") or scene_data.get("dialogue") or "")
        reaction = _short_visual_phrase(dialogue, 9) or short_phrase
        draw.rounded_rectangle((185, 355, 1065, 650), radius=28, fill=(240, 244, 246), outline=accent, width=5)
        for line_no, line in enumerate(textwrap.wrap(reaction.upper(), width=27)[:3]):
            draw.text((235, 420 + line_no * 67), line, font=phrase_font, fill=(26, 40, 52))
        draw.polygon([(1020, 605), (1130, 650), (1050, 535)], fill=(240, 244, 246), outline=accent)


def mix_scene_audio(narration_wav: Path, sfx_events: list, output_wav: Path, speaker_side: str = "CENTER"):
    dur = get_audio_duration(str(narration_wav))
    fade_out_st = max(0.0, dur - 0.035)
    pan_str = f"pan=stereo|c0=0.707*c0|c1=0.707*c0,afade=t=in:ss=0:d=0.035,afade=t=out:st={fade_out_st:.3f}:d=0.035"
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
    total_scenes: int = 28,
    **kwargs
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
    impact_f = SFX_DIR / "impact.mp3"
    scribble_f = SFX_DIR / "marker_scribble.wav"
    click_f = SFX_DIR / "click.mp3"
    boing_f = SFX_DIR / "cartoon_boing.wav"

    is_kinetic_sequence = bool(subshots) and all(stype.startswith("CRAYON_") for stype in subshots)
    if not is_kinetic_sequence:
        if whoosh_f.exists(): sfx_events.append((whoosh_f, 0.05, 0.40))
        if pop_f.exists(): sfx_events.append((pop_f, 0.50, 0.50))
    if scene_data.get("audio_cue") == "impact" and impact_f.exists():
        sfx_events.append((impact_f, 0.10, 0.35))
    elif scene_data.get("audio_cue") == "drop" and boing_f.exists():
        sfx_events.append((boing_f, 0.10, 0.35))

    for s_i, stype in enumerate(subshots):
        st_t = s_i * sub_dur
        if s_i > 0 and whoosh_f.exists(): sfx_events.append((whoosh_f, st_t, 0.30))
        if stype.startswith("CRAYON_"):
            cue = {
                "CRAYON_HOOK": impact_f,
                "CRAYON_VISUAL": scribble_f,
                "CRAYON_EVIDENCE": click_f,
                "CRAYON_REACTION": boing_f,
            }.get(stype)
            scene_cue_already_played = s_i == 0 and (
                (stype == "CRAYON_HOOK" and scene_data.get("audio_cue") == "impact")
                or (stype == "CRAYON_REACTION" and scene_data.get("audio_cue") == "drop")
            )
            if cue and cue.exists() and not scene_cue_already_played:
                sfx_events.append((cue, st_t + 0.15, 0.30))
        elif ("FINANCIAL" in stype or "BUDGET" in stype) and cash_f.exists(): sfx_events.append((cash_f, st_t + 0.5, 0.45))
        elif (stype == "KEN_BURNS" or "DOSSIER" in stype) and stamp_f.exists(): sfx_events.append((stamp_f, st_t + 0.5, 0.50))
        elif ("RADAR" in stype or "MAP" in stype or "COCKPIT" in stype or "FLIR" in stype or "PATENT" in stype or "HUD" in stype or "COMM" in stype) and sonar_f.exists(): sfx_events.append((sonar_f, st_t + 0.7, 0.35))

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

        # Boş Kafa dynamic stickman: discrete lip-sync and blink state per frame
        host_walk = get_host_pose("walking", 620, t=t, is_speaking=False)
        host_point = get_host_pose("pointing", 640, t=t, is_speaking=True)
        host_shock = get_host_pose("shocked", 640, t=t, is_speaking=False)
        host_smug = get_host_pose("smug", 640, t=t, is_speaking=True)

        frame = Image.new("RGBA", (W, H), (15, 23, 42, 255))
        draw = ImageDraw.Draw(frame)

        if sub_type == "HANGAR_WALK":
            render_hangar_walk(frame, draw, t_sub, sub_title, host_walk, host_smug)
        elif sub_type.startswith("CRAYON_"):
            character = str(scene_data.get("char") or scene_data.get("active_character") or "").upper()
            speaker_img = (
                pilot_img if "PILOT" in character else
                general_img if "GENERAL" in character else
                spy_img if "SPY" in character else
                ceo_img
            )
            render_crayon_kinetic_shot(
                frame, draw, scene_data, sub_type, t_sub, sub_dur, speaker_img,
                topic_category=_CURRENT_TOPIC_CATEGORY,
            )
        elif sub_type.startswith("EDITORIAL_"):
            render_editorial_briefing(frame, draw, t_sub, sub_title, host_point, scene_data)
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
        elif sub_type == "BLUEPRINT_SYMBOL_HUD":
            render_blueprint_symbol_hud(frame, draw, t_sub, sub_title, host_point, scene_data)
        elif sub_type == "EXPLODED_PATENT":
            render_exploded_patent_schema(frame, draw, t_sub, sub_title, host_shock, scene_data)
        elif sub_type == "FLIR_BAKERY_INCIDENT":
            render_flir_bakery_incident(frame, draw, t_sub, sub_title, pilot_img, scene_data)
        elif sub_type == "TICKING_BUDGET":
            render_ticking_budget_counter(frame, draw, t_sub, sub_title, host_shock, scene_data)
        elif sub_type == "COMM_SPLIT_SCREEN":
            render_comm_split_screen(frame, draw, t_sub, sub_title, ceo_img, general_img, pilot_img, scene_data)
        elif sub_type == "FOREIGN_INTEL_DOSSIER":
            render_foreign_intel_dossier(frame, draw, t_sub, sub_title, host_point, spy_img, scene_data)
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
        wav_path = Path(sc.get("wav_path") or mat_dir / f"scene_{i}_audio.wav")
        dur = float(sc.get("duration") or (get_audio_duration(str(wav_path)) if wav_path.exists() else 6.0))

        narration = sc.get("narration", "").strip()
        speaker = sc.get("speaker", "SUNUCU")
        if not narration:
            current_time = float(sc.get("start_time", current_time)) + dur
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


def _render_single_scene_task(args):
    sc, wav_path, scene_mp4, vehicle_name, idx, total_scenes = args
    dur = get_audio_duration(str(wav_path)) if wav_path.exists() else 5.0
    t0 = time.time()
    render_animated_scene(sc, wav_path, scene_mp4, vehicle_name, idx, total_scenes=total_scenes)
    dt = time.time() - t0
    print(f"  ✨ Sahne {idx+1}/{total_scenes} rendered ({dur:.1f}s, render: {dt:.2f}s)")
    return idx, scene_mp4


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

    chan_id = mat_data.get("channel_id", "")
    set_current_channel_id(chan_id, mat_data.get("topic_category", ""))

    scenes = mat_data.get("scenes") or (mat_data.get("script", {}).get("scenes") if isinstance(mat_data.get("script"), dict) else [])
    vehicle_name = mat_data.get("vehicle_name") or mat_data.get("flight_name") or mat_data.get("title") or "Commercial Flight"
    total_scenes = len(scenes)

    print(f"🎬 [Bespoke Non-Repeating Documentary Engine] '{mat_data.get('title', 'Video')}' starting 16-archetype non-repeating production ({total_scenes} sahne)...")

    # Ensure TTS generator is ready for missing scene audio
    tts_gen = None
    lang = mat_data.get("language") or "en"

    total_vid_dur = 0.0
    tasks = []
    for idx, sc in enumerate(scenes):
        scene_mp4 = temp_dir / f"scene_{idx:02d}_anim.mp4"
        wav_path = mat_dir / f"scene_{idx}_audio.wav"
        if not wav_path.exists():
            wav_path = mat_dir / f"scene_{idx+1:02d}.wav"
        if not wav_path.exists():
            wav_path = mat_dir / f"scene_{idx}_kokoro.wav"
        if not wav_path.exists():
            wav_path = mat_dir / f"scene_{idx}_audio.mp3"
        if not wav_path.exists():
            # Generate missing audio
            wav_fallback = temp_dir / f"scene_{idx}_tts.mp3"
            if not wav_fallback.exists() or wav_fallback.stat().st_size < 1000:
                if tts_gen is None:
                    try:
                        from video_generator import AudioGenerator
                        tts_gen = AudioGenerator()
                    except ImportError:
                        from src.video_generator import AudioGenerator
                        tts_gen = AudioGenerator()
                narration = sc.get("narration") or sc.get("text") or vehicle_name
                tts_gen.generate_sync(narration, lang, str(wav_fallback))
            if wav_fallback.exists():
                wav_path = wav_fallback

        dur = get_audio_duration(str(wav_path)) if wav_path.exists() else 5.0
        total_vid_dur += dur
        tasks.append((sc, wav_path, scene_mp4, vehicle_name, idx, total_scenes))

    print(f"⏱️ Total Video Duration: {total_vid_dur:.1f}s ({total_vid_dur/60.0:.2f} dakika)")

    from concurrent.futures import ProcessPoolExecutor
    workers = min(4, os.cpu_count() or 2)
    print(f"🚀 Multiprocessing scene rendering enabled ({workers} concurrent workers)...")
    results = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for res in executor.map(_render_single_scene_task, tasks):
            results.append(res)

    results.sort(key=lambda x: x[0])
    rendered_scene_mp4s = [r[1] for r in results]

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

    # Sync to video.mp4 for YouTube uploader compatibility
    video_copy = dest_dir / "video.mp4"
    if final_output.exists():
        shutil.copy2(final_output, video_copy)

    # Sync metadata and video_info.json
    info_json = dest_dir / "video_info.json"
    if info_json.exists():
        try:
            with open(info_json, "r", encoding="utf-8") as f:
                info_data = json.load(f)
            info_data["file_size_mb"] = round(final_output.stat().st_size / (1024 * 1024), 2)
            info_data["duration"] = round(total_vid_dur, 2)
            with open(info_json, "w", encoding="utf-8") as f:
                json.dump(info_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

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
