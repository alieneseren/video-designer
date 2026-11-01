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

try:
    from stickman_engine.crayon_timeline import SFX_ASSETS
except ImportError:
    from src.stickman_engine.crayon_timeline import SFX_ASSETS

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
ARCTIC_MAP_BG = BG_DIR / "norway_arctic_map_1080p.jpg"
HANGAR_BG = BG_DIR / "crayon_hangar_airfield.jpg"
COCKPIT_BG = BG_DIR / "crayon_cockpit_interior.jpg"
WAR_ROOM_BG = BASE_DIR / "assets/crayon_military_bg.jpg"
TECH_BG = BASE_DIR / "assets/crayon_tech_bg.jpg"
STREET_BG = BASE_DIR / "assets/crayon_street_bg.jpg"

B21_BLUEPRINT_IMG = VEH_DIR / "b21_raider_blueprint.png"
B21_FLIGHT_REAL = REAL_VEH_DIR / "b21_flight_real.jpg"
B21_ROLLOUT_REAL = REAL_VEH_DIR / "b21_rollout_real.jpg"
B21_CUTOUT_REAL = REAL_VEH_DIR / "b21_real_cutout.png"
M1A2_ABRAMS_REAL = REAL_VEH_DIR / "m1a2_abrams_tank.jpg"
HUMVEE_ARCTIC_REAL = REAL_VEH_DIR / "humvee_norway_arctic.jpg"
F16_COCKPIT_REAL = REAL_VEH_DIR / "f16_cockpit_flight.jpg"

W, H = 1920, 1080
FPS = 25
RENDER_CACHE_VERSION = "crayon-story-visuals-v8"

def _find_optimal_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        imgio_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if imgio_exe and os.path.exists(imgio_exe):
            res = subprocess.run([imgio_exe, "-filters"], capture_output=True, text=True, timeout=3)
            if "subtitles" in res.stdout or "ass" in res.stdout:
                return imgio_exe
    except Exception:
        pass
    for c in [shutil.which("ffmpeg"), "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        if c and os.path.exists(c):
            try:
                res = subprocess.run([c, "-filters"], capture_output=True, text=True, timeout=3)
                if "subtitles" in res.stdout or "ass" in res.stdout:
                    return c
            except Exception:
                continue
    return shutil.which("ffmpeg") or "/usr/bin/ffmpeg"

FFMPEG_BIN = _find_optimal_ffmpeg()


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


def is_aviation_context(scene_data=None, text: str = "", vehicle_name: str = "", title: str = "") -> bool:
    if _CURRENT_TOPIC_CATEGORY in ("aviation", "blackbox", "air_crash", "flight_disaster", "havacilik"):
        return True
    if any(k in _CURRENT_CHANNEL_ID for k in ("blackbox", "aviation", "flight")):
        return True
    combined = (str(vehicle_name) + " " + str(title) + " " + str(text) + " " + str(scene_data or "")).lower()
    return any(k in combined for k in (
        "flight", "flaps", "cockpit", "black box", "cvr", "ntsb", "atc tower", "airbus", "boeing",
        "spanair", "tenerife", "qantas", "crossair", "gottröra", "fine air", "tuninter",
        "los rodeos", "barajas", "arlanda", "learmonth", "ditching", "stall", "squawk 7700", "mayday"
    ))


AVIATION_INCIDENTS = {
    "spanair_5022": {
        "key": "spanair_5022",
        "is_ground_incident": False,
        "flight_no": "JK5022",
        "squawk": "7000",
        "aircraft": "McDonnell Douglas MD-82",
        "operator": "Spanair",
        "location": "Madrid-Barajas (LEMD), Runway 36L",
        "atc_facility": "MADRID TOWER // 118.15 MHz",
        "atc_msg_1": 'JK5022: "Madrid Tower, Spanair 5022 lining up 36L."',
        "atc_msg_2": 'TOWER: "Spanair 5022, wind 210 at 5 kt, cleared for takeoff 36L."',
        "atc_msg_3": 'JK5022: "Rolling 36L, Spanair 5022."',
        "atc_radar_tag": "JK5022 // FL007 -> GND",
        "radar_sub": "LIFTOFF ROLL // STALL AT 40 FT",
        "dist_info_header": "TAKEOFF CONFIGURATION MONITORING:",
        "dist_info_main": "TOCW HORN INOPERATIVE (RELAY R2-5)",
        "dist_info_sub": "CREW COMMENCED ROTATION WITH FLAPS AND SLATS RETRACTED (0°)",
        "cvr_warning": "TAKEOFF CONFIG // STALL WARNING",
        "cvr_sub_warning": "STICK SHAKER ACTIVATED AT LIFTOFF",
        "telemetry": "ALT: 38 FT // IAS: 154 KT // PITCH: +18° // FLAPS: 0° (RETRACTED)",
        "bank_angle_base": 32.0,
        "maint_header": "CRITICAL RELAY FAILURE // TOCW WARNING DISABLED",
        "maint_box1_title": "DEFECTIVE: RELAY R2-5 (HEATING)",
        "maint_box1_part": "P/N: 206864-1 (CIRCUIT OPEN)",
        "maint_box1_val": "RAT PROBE HEATER OVERHEATING",
        "maint_box1_bullets": [
            "• Ground mechanics pulled circuit breaker Z-29",
            "• Relay R2-5 failed in flight mode while on ground",
            "• Inhibited Take-Off Configuration Warning (TOCW)!"
        ],
        "maint_box2_title": "FAILED WARNING: FLAPS / SLATS 0°",
        "maint_box2_part": "FLAPS: 0° // SLATS: RETRACTED",
        "maint_box2_val": "WING LIFT DEFICIT: -45%",
        "maint_box2_bullets": [
            "• MD-82 checklist item omitted during taxi",
            "• Warning horn stayed silent upon throttle advance",
            "• Aircraft rolled into immediate aerodynamic stall!"
        ],
        "maint_footer_title": "CIAIAC / NTSB SYSTEMIC FAILURE AUDIT:",
        "maint_footer_main": "TOCW RELAY ISOLATION WITHOUT GROUND TEST VERIFICATION",
        "maint_footer_sub": "RESULT: AERODYNAMIC STALL 40 FEET AFTER VR ON RUNWAY 36L",
        "investigation_agency": "CIAIAC (SPAIN) / NTSB ACCIDENT DOSSIER",
        "probable_cause": "Takeoff attempted with flaps and slats in retracted position.",
        "cause_sub": "TOCW warning horn failed to activate due to faulty relay R2-5 in RAT probe circuit.",
        "findings": [
            ("1. CHECKLIST INTERRUPTIONS", "Checklist interrupted during ground delay to service RAT probe temp spike."),
            ("2. INOPERATIVE TOCW WARNING", "Relay R2-5 contacts open prevented warning horn sounding at takeoff thrust."),
            ("3. AERODYNAMIC STALL ON ROTATION", "At liftoff without lift devices, stick shaker fired and aircraft rolled right."),
            ("4. MANDATORY TOCW PRE-FLIGHT TEST", "EASA and FAA mandated functional TOCW audio alarm test before every flight.")
        ],
        "cvr_dialogues": [
            ("14:23:10", "MADRID TOWER", '"Spanair 5022, cleared for takeoff runway 36L."', (234, 179, 8), (255, 255, 255)),
            ("14:23:18", "JK5022 (CAPT)", '"Rolling 36L, takeoff thrust set."', (56, 189, 248), (255, 255, 255)),
            ("14:24:08", "JK5022 (FO)", '"V1... Rotate."', (56, 189, 248), (255, 255, 255)),
            ("14:24:14", "JK5022 (CVR)", '[STICK SHAKER VIBRATION // HORN SILENT // STALL]', (239, 68, 68), (255, 220, 220)),
            ("14:24:20", "JK5022 (CAPT)", '"Engine failure? What is that?! Flaps?!"', (239, 68, 68), (255, 230, 230))
        ],
        "crm_nodes": [
            ("1. SCHEDULE PRESSURE", "2-Hour Departure Delay", "Crew under commercial pressure to reach Gran Canaria after initial maintenance return.", (234, 179, 8)),
            ("2. RELAY DE-ENERGIZATION", "RAT Probe Circuit Isolated", "Mechanic pulled circuit breaker, unknowingly deactivating the Takeoff Config Warning.", (239, 68, 68)),
            ("3. CHECKLIST OMISSIONS", "Flaps Setting Skipped", "Interrupted taxi checklist resulted in throttles pushed with Flaps 0° and Slats Retracted.", (239, 68, 68)),
            ("4. SILENT WARNING HORN", "Failed Fail-Safe Defense", "Audio horn remained dormant; crew rotated blindly into an unrecoverable aerodynamic stall.", (239, 68, 68))
        ],
        "speech_bubble_triggers": [
            (["relay", "r2-5", "breaker", "probe", "heater"], "R2-5 BREAKER PULLED // TOCW INOP", "left", (234, 179, 8), "SYSTEM ANOMALY [R2-5]"),
            (["flaps", "slats", "retracted", "config", "horn"], "FLAPS 0° // TAKEOFF HORN SILENT!", "right", (220, 38, 38), "JK5022 [CREW]"),
            (["stall", "stick shaker", "bank", "rotation"], "STICK SHAKER // STALL WARNING!", "right", (220, 38, 38), "JK5022 [CAPT LUNA]"),
            (["mechanic", "maintenance", "isolation"], "RAT HEATER DEACTIVATED", "left", (234, 179, 8), "LINE MAINTENANCE")
        ]
    },
    "fine_air_101": {
        "key": "fine_air_101",
        "is_ground_incident": False,
        "flight_no": "FJN101",
        "squawk": "1421",
        "aircraft": "McDonnell Douglas DC-8-61F",
        "operator": "Fine Air (Cargo)",
        "location": "Miami International (KMIA), Runway 27R",
        "atc_facility": "MIAMI TOWER // 118.30 MHz",
        "atc_msg_1": 'FJN101: "Miami Tower, Fine Air 101 heavy, ready on 27R."',
        "atc_msg_2": 'TOWER: "Fine Air 101 heavy, cleared for takeoff runway 27R."',
        "atc_msg_3": 'FJN101: "Cleared for takeoff 27R, Fine Air 101 heavy."',
        "atc_radar_tag": "FJN101 // FL008 -> GND",
        "radar_sub": "INITIAL CLIMB // UNCOMMANDED PITCH 35°",
        "dist_info_header": "WEIGHT & BALANCE DISCREPANCY:",
        "dist_info_main": "PALLET MISLOAD // CG AFT LIMIT EXCEEDED",
        "dist_info_sub": "ACTUAL CG BEYOND 60% MAC // STABILIZER TRIM SET INACCURATELY",
        "cvr_warning": "EXTREME PITCH UP // STALL",
        "cvr_sub_warning": "ELEVATOR HYDRAULIC CONTROL OVERPOWERED",
        "telemetry": "ALT: 800 FT // IAS: 110 KT // PITCH: +32° // ELEVATOR: FULL NOSE-DOWN",
        "bank_angle_base": 18.0,
        "maint_header": "CARGO WEIGHT & BALANCE BREAKDOWN // EXTREME AFT CG",
        "maint_box1_title": "CARGO LOAD SHEET: ERRONEOUS",
        "maint_box1_part": "STATED CG: 30.0% MAC (BALANCED)",
        "maint_box1_val": "HEAVY PALLETS LOGGED FORWARD",
        "maint_box1_bullets": [
            "• Cargo personnel placed heavy pallets at rear positions",
            "• Load sheet did not reflect actual aircraft weight distro",
            "• Tail-heavy condition went completely unnoticed by crew!"
        ],
        "maint_box2_title": "ACTUAL LOADING: SEVERE AFT CG",
        "maint_box2_part": "ACTUAL CG: > 60% MAC (UNSTABLE)",
        "maint_box2_val": "HORIZONTAL STAB TRIM MISRIGGED",
        "maint_box2_bullets": [
            "• Trim set for false 30% CG led to violent pitch up on rotation",
            "• Full down elevator stick deflection failed to lower nose",
            "• Massive cargo shifting during rotation accelerated stall!"
        ],
        "maint_footer_title": "NTSB PROBABLE CAUSE INVESTIGATION AUDIT:",
        "maint_footer_main": "AIR CARGO WEIGHING & RE-SECURING IRREGULARITIES",
        "maint_footer_sub": "RESULT: UNCOMMANDED PITCH UP AND IMMEDIATE STALL AFTER ROTATION",
        "investigation_agency": "NTSB (USA) ACCIDENT INVESTIGATION DOSSIER",
        "probable_cause": "Severe aft center of gravity condition caused by misloaded cargo pallets.",
        "cause_sub": "Stabilizer trim misadjusted for false weight manifest; cargo shifted aft on liftoff.",
        "findings": [
            ("1. CARGO LOADING MISMANAGEMENT", "Loading crew swapped pallet positions without updating flight dispatcher or crew."),
            ("2. TRIM DISCREPANCY", "Stabilizer trim was calibrated for fictitious forward CG, inducing instant pitch-up."),
            ("3. LACK OF CARGO SCALE AUDIT", "Pallets were not independently weighed before tarmac staging."),
            ("4. RIGOROUS WEIGHT & BALANCE OVERSIGHT", "FAA mandated certified weight manifests and dual-signature cargo balance locks.")
        ],
        "cvr_dialogues": [
            ("12:35:15", "MIAMI TOWER", '"Fine Air 101 Heavy, cleared for takeoff 27R."', (234, 179, 8), (255, 255, 255)),
            ("12:36:02", "FJN101 (FO)", '"V1... Vr... Rotate."', (56, 189, 248), (255, 255, 255)),
            ("12:36:08", "FJN101 (CAPT)", '"Push the nose down! Push it down!"', (239, 68, 68), (255, 230, 230)),
            ("12:36:14", "FJN101 (FO)", '"I am pushing full down! No effect! Elevator full forward!"', (239, 68, 68), (255, 220, 220)),
            ("12:36:20", "FJN101 (CVR)", '[STALL WARNING AUDIO HORN // GROUND IMPACT ON NW 72ND AVE]', (239, 68, 68), (255, 200, 200))
        ],
        "crm_nodes": [
            ("1. CARGO MISLOAD", "Aft Pallet Staging", "Contract loaders swapped heavy cargo containers without updating the load manifest.", (239, 68, 68)),
            ("2. STABILIZER MISTRIM", "Calibrated for False CG", "Trim set for fictitious 30% CG instead of actual >60% MAC tail-heavy reality.", (239, 68, 68)),
            ("3. CONTROL AERODYNAMICS", "Elevator Authority Overpowered", "Pitching moment created by tail weight exceeded maximum downward elevator authority.", (239, 68, 68)),
            ("4. IMMEDIATE STALL", "Violent Rotation Liftoff", "Aircraft pitched past 32° immediately upon liftoff, entering an irrecoverable stall.", (239, 68, 68))
        ],
        "speech_bubble_triggers": [
            (["pallet", "cargo", "loading", "aft cg", "weight"], "HEAVY PALLETS LOADED AFT!", "left", (234, 179, 8), "FJN101 [CARGO LOAD]"),
            (["trim", "stabilizer", "elevator", "nose", "pitch"], "FULL NOSE-DOWN // NO EFFECT!", "right", (220, 38, 38), "FJN101 [CAPT SANCHEZ]"),
            (["stall", "rotate", "vr"], "VIOLENT PITCH-UP // STALL!", "right", (220, 38, 38), "FJN101 [FLIGHT CREW]")
        ]
    },
    "tenerife": {
        "key": "tenerife",
        "is_ground_incident": True,
        "flight_no": "KLM4805 / PAA1736",
        "squawk": "7000 / 1736",
        "aircraft": "Boeing 747-206B / Boeing 747-121",
        "operator": "KLM / Pan American World Airways",
        "location": "Los Rodeos Airport (GCXO), Tenerife",
        "atc_facility": "TENERIFE TOWER // 118.70 MHz",
        "atc_msg_1": 'KLM4805: "We are now at takeoff." // TOWER: "OK... Stand by for takeoff, I will call you."',
        "atc_msg_2": 'PAA1736: "We are still taxiing down the runway!" [HETERODYNE SQUEAL CANCELLATION]',
        "atc_msg_3": 'TOWER: "Papa Alpha 1736, report runway clear." // PAA1736: "OK, report clear."',
        "atc_radar_tag": "KLM4805 / PAA1736 // RWY 12",
        "radar_sub": "FOG VISIBILITY < 300M // RUNWAY INCURSION",
        "dist_info_header": "RUNWAY STATUS & RADIO COINCIDENCE:",
        "dist_info_main": "ACTIVE RUNWAY 12 // DENSE CLOUD BANK",
        "dist_info_sub": "TWO 747 JUMBOS ON SINGLE RUNWAY WITHOUT GROUND RADAR SURVEILLANCE",
        "cvr_warning": "RUNWAY COLLISION ALERT // FOG",
        "cvr_sub_warning": "RADIO HETERODYNE HIGH-PITCH AUDIO SQUEAL",
        "telemetry": "VISIBILITY: 100-300M // IAS: 146 KT // RUNWAY: 12 BACKTAXI // GROUND RADAR: NONE",
        "bank_angle_base": 0.0,
        "maint_header": "HUMAN FACTORS & RADIO TRANSMISSION CANCEL BREAKDOWN",
        "maint_box1_title": "KLM 4805: UNCLEARED TAKEOFF",
        "maint_box1_part": "CAPT. VAN ZANTEN (CHIEF PILOT)",
        "maint_box1_val": "IMPENDING DUTY TIME EXPIRATION",
        "maint_box1_bullets": [
            "• Urgent desire to return to Amsterdam before strict duty limits",
            "• Misinterpreted ATC route clearance as takeoff clearance",
            "• Initiated takeoff roll blindly into dense zero-visibility fog!"
        ],
        "maint_box2_title": "PAN AM 1736: MISSING EXIT C-3",
        "maint_box2_part": "TAXIING BACKWARDS ON RUNWAY 12",
        "maint_box2_val": "EXIT C-3 SHARP 135° ANGLE",
        "maint_box2_bullets": [
            "• In heavy fog, crew missed exit C-3 and headed toward C-4",
            "• Radioed 'We are still taxiing down the runway'",
            "• Blocked by simultaneous ATC transmission squeal (heterodyne)!"
        ],
        "maint_footer_title": "CIAIAC / NTSB / DUTCH SAFETY BOARD JOINT AUDIT:",
        "maint_footer_main": "SIMULTANEOUS TWO-WAY VHF TRANSMISSION INTERFERENCE",
        "maint_footer_sub": "RESULT: DEADLIEST DISASTER IN AVIATION HISTORY (583 FATALITIES)",
        "investigation_agency": "CIAIAC (SPAIN) / NTSB / DUTCH BOARD DOSSIER",
        "probable_cause": "KLM captain initiated takeoff without obtaining takeoff clearance.",
        "cause_sub": "Dense fog obscured vision; radio heterodyne canceled crucial warning that Pan Am was on runway.",
        "findings": [
            ("1. RADIO HETERODYNE INTERFERENCE", "Concurrent transmissions on same frequency produced squeal, erasing warning."),
            ("2. COCKPIT RESOURCE MANAGEMENT (CRM)", "Junior first officer felt unable to question senior chief training captain."),
            ("3. STANDARDIZED ATC PHRASEOLOGY", "Banned ambiguous word 'takeoff' except when issuing actual takeoff clearance."),
            ("4. CREW RESOURCE MANAGEMENT REVOLUTION", "Instituted mandatory CRM training across all commercial airlines worldwide.")
        ],
        "cvr_dialogues": [
            ("17:05:55", "KLM 4805 (FO MEURS)", '"We are now at takeoff."', (56, 189, 248), (255, 255, 255)),
            ("17:06:05", "KLM 4805 (CAPT VAN ZANTEN)", '"We gaan. (We are going.)" [ADVANCES THROTTLES TO TAKEOFF THRUST]', (239, 68, 68), (255, 230, 230)),
            ("17:06:18", "TENERIFE TOWER", '"OK... Stand by for takeoff, I will call you."', (234, 179, 8), (255, 255, 255)),
            ("17:06:19", "PAA 1736 (FO BRAGG)", "And we are still taxiing down the runway, Clipper 1736!", (34, 197, 94), (255, 255, 255)),
            ("17:06:40", "PAA 1736 (CAPT GRUBBS)", '"There he is! Look at him! Goddamn, that son of a bitch is coming!"', (239, 68, 68), (255, 220, 220))
        ],
        "crm_nodes": [
            ("1. DUTY TIME PRESSURE", "Dutch Law Strict Flight Limits", "KLM crew faced severe legal liability and flight cancellation if delayed past duty limit.", (239, 68, 68)),
            ("2. AUTHORITY GRADIENT", "Chief Flight Instructor Hierarchy", "First Officer Klaas Meurs was certified by Capt. van Zanten; hesitated to forcefully veto him.", (234, 179, 8)),
            ("3. AMBIGUOUS ATC LANGUAGE", "Non-Standard Word 'Takeoff'", "Meurs read back: 'We are now at takeoff.' Tower thought they were holding at threshold.", (56, 189, 248)),
            ("4. FREQUENCY HETERODYNE", "Simultaneous Radio Squeal", "Tower's 'Stand by' and Pan Am's 'Still taxiing' clashed, silencing the collision warning.", (239, 68, 68))
        ],
        "speech_bubble_triggers": [
            (["we gaan", "we are going", "advance throttle", "advances throttle"], "WE GAAN! (WE ARE GOING!)", "left", (220, 38, 38), "KLM 4805 [CAPT VAN ZANTEN]"),
            (["wait a minute", "don't have atc clearance", "don't have clearance", "no clearance"], "WAIT, WE DON'T HAVE CLEARANCE!", "right", (234, 179, 8), "KLM 4805 [FO MEURS]"),
            (["still taxiing", "clipper 1736", "taxiing down the runway", "we are still taxiing"], "WE'RE STILL TAXIING DOWN RUNWAY!", "right", (234, 179, 8), "PAN AM 1736 [FO BRAGG]"),
            (["heterodyne", "simultaneous transmission", "radio squeal", "frequency squeal"], "HETERODYNE // AUDIO SQUEAL!", "left", (220, 38, 38), "TOWER FREQ // 118.70 MHz"),
            (["is he not", "er niet af", "flight engineer"], "IS HE NOT OFF THE RUNWAY?!", "right", (234, 179, 8), "KLM 4805 [FLIGHT ENGR]"),
            (["look at him", "son of a bitch", "that son of a", "coming!"], "GODDAMN, HE'S COMING! GET OFF!", "right", (220, 38, 38), "PAN AM 1736 [CAPT GRUBBS]"),
            (["stand by for takeoff", "report runway clear"], "REPORT RUNWAY CLEAR", "left", (56, 189, 248), "TENERIFE TOWER [ATC]")
        ]
    },
    "qantas_72": {
        "key": "qantas_72",
        "is_ground_incident": False,
        "flight_no": "QF72",
        "squawk": "7422",
        "aircraft": "Airbus A330-303",
        "operator": "Qantas Airways",
        "location": "Over Indian Ocean, near Learmonth (YPLM), Western Australia",
        "atc_facility": "MELBOURNE CENTER // 120.55 MHz",
        "atc_msg_1": 'QF72: "MAYDAY, MAYDAY, MAYDAY! Qantas 72, experienced uncommanded pitch down."',
        "atc_msg_2": 'ATC: "Qantas 72, Melbourne Centre, squawk 7700, say intentions."',
        "atc_msg_3": 'QF72: "We have multiple injured passengers, requesting immediate diversion to Learmonth."',
        "atc_radar_tag": "QF72 // FL370 -> FL110",
        "radar_sub": "INERTIAL SPIKE // UNCOMMANDED FLY-BY-WIRE NOSE DIVE",
        "dist_info_header": "AIR DATA INERTIAL REFERENCE SYSTEM FAULT:",
        "dist_info_main": "ADIRU 1 TRANSMITTED +50.6° ANGLE OF ATTACK DATA SPIKE",
        "dist_info_sub": "FLIGHT CONTROL PRIMARY COMPUTERS COMMANDED FULL NOSE-DOWN STABILIZER",
        "cvr_warning": "UNCOMMANDED PITCH DOWN // ADIRU FAULT",
        "cvr_sub_warning": "AUTOPILOT DISCONNECT // -0.8G ZERO GRAVITY DIVE",
        "telemetry": "ALT: 37,000 FT // G-FORCE: -0.8 G // IAS: 280 KT // PITCH: -8.4° UNCOMMANDED",
        "bank_angle_base": 14.0,
        "maint_header": "AVIONICS ALGORITHM ANOMALY // ADIRU 1 SINGLE-WORD GLITCH",
        "maint_box1_title": "ADIRU 1 INERTIAL SENSOR: FAILED",
        "maint_box1_part": "LTN-101 ADIRU (P/N: 465020-03030316)",
        "maint_box1_val": "TRANSMITTED +50.6° PSEUDO-AOA",
        "maint_box1_bullets": [
            "• Single Event Upset or optical sensor glitch corrupted internal data",
            "• Unit erroneously reported extreme +50.6° nose-high stall angle",
            "• System failed to flag data word as invalid before transmission!"
        ],
        "maint_box2_title": "FCPC PITCH INTEGRITY LIMIT",
        "maint_box2_part": "FCPC SOFTWARE ALGORITHM (EFCS)",
        "maint_box2_val": "OVER-SPEED PROTECTION FIRED",
        "maint_box2_bullets": [
            "• Flight Control Primary Computer accepted single anomalous packet",
            "• Commanded violent 8.4° elevator nose-down to save plane from stall",
            "• Flung unrestrained passengers and crew into cabin ceiling!"
        ],
        "maint_footer_title": "ATSB (AUSTRALIA) / BEA OFFICIAL REPORT:",
        "maint_footer_main": "AIRBUS FCPC SOFTWARE REVISION & ADIRU DATA FILTERING",
        "maint_footer_sub": "RESULT: WORLDWIDE ALGORITHM PATCH PREVENTING SINGLE-SPIKE DIVE COMMANDS",
        "investigation_agency": "ATSB (AUSTRALIA) / BEA OFFICIAL REPORT",
        "probable_cause": "ADIRU 1 transmitted anomalous single-word AOA spikes which FCPC software failed to filter.",
        "cause_sub": "FCPC triggered pitch-down angle-of-attack protection in response to corrupted sensor data.",
        "findings": [
            ("1. SINGLE-WORD SENSOR CORRUPTION", "ADIRU 1 generated false +50.6° AOA spike due to internal CPU memory register fault."),
            ("2. ALGORITHM DESIGN DEFICIENCY", "FCPC pitch protection algorithm could not reject an isolated 1.2-second anomalous spike."),
            ("3. PILOT INTERVENTION", "Captain Kevin Sullivan manually overpowered fly-by-wire and executed visual emergency landing."),
            ("4. GLOBAL AIRBUS SOFTWARE UPDATE", "Airbus revised FCPC operating software worldwide to mandate multi-sample spike rejection.")
        ],
        "cvr_dialogues": [
            ("12:40:26", "QF72 (AVIONICS)", '[NAV IR 1 FAULT // MASTER CAUTION CHIME // AP OFF]', (239, 68, 68), (255, 230, 230)),
            ("12:42:27", "QF72 (CAPT SULLIVAN)", '"What the hell was that?! The nose is pitching down violently!"', (239, 68, 68), (255, 255, 255)),
            ("12:42:30", "QF72 (FO)", '"Negative Gs! We are hitting the ceiling!"', (239, 68, 68), (255, 220, 220)),
            ("12:44:05", "QF72 (CAPT SULLIVAN)", '"Mayday, Mayday, Mayday! Qantas 72, uncommanded pitch down, divert Learmonth."', (56, 189, 248), (255, 255, 255)),
            ("12:44:15", "MELBOURNE CENTER", '"Qantas 72, cleared direct Learmonth runway 18."', (234, 179, 8), (255, 255, 255))
        ],
        "crm_nodes": [
            ("1. SENSOR BIT FLIP", "ADIRU 1 Optical Gyro Spikes", "Cosmic radiation or memory register fault sent +50.6° angle-of-attack signal.", (239, 68, 68)),
            ("2. FLY-BY-WIRE LAW", "FCPC Computer Logic Fired", "Flight computers believed aircraft was stalling and pushed elevator violently forward.", (239, 68, 68)),
            ("3. CABIN ZERO-G IMPACT", "-0.8G Negative Acceleration", "Unrestrained passengers and cabin crew thrown violently against overhead bins.", (234, 179, 8)),
            ("4. MANUAL RECOVERY", "Captain Sullivan Hand-Fly", "Captain disengaged automated protections and safely landed deadstick at Learmonth.", (34, 197, 94))
        ],
        "speech_bubble_triggers": [
            (["adiru", "sensor", "aoa", "spike", "inertial"], "ADIRU 1 SENSOR SPIKE +50.6°!", "left", (234, 179, 8), "FCPC SYSTEM ALERT"),
            (["dive", "pitch", "g-force", "uncommanded", "negative"], "UNCOMMANDED NOSE DIVE!", "right", (220, 38, 38), "QF72 [CAPT SULLIVAN]"),
            (["learmonth", "mayday", "sullivan"], "MAYDAY // DIVERTING LEARMONTH", "right", (56, 189, 248), "QF72 [CAPT SULLIVAN]")
        ]
    },
    "crossair_498": {
        "key": "crossair_498",
        "is_ground_incident": False,
        "flight_no": "CRX498",
        "squawk": "2451",
        "aircraft": "Saab 340B",
        "operator": "Crossair",
        "location": "Niederhasli, near Zurich Airport (LSZH), Switzerland",
        "atc_facility": "ZURICH DEPARTURE // 125.95 MHz",
        "atc_msg_1": 'CRX498: "Zurich Departure, Crossair 498 climbing through 3,000 feet."',
        "atc_msg_2": 'DEPARTURE: "Crossair 498, radar contact, turn left heading 220."',
        "atc_msg_3": 'DEPARTURE: "Crossair 498, confirm turning left? You are turning right!"',
        "atc_radar_tag": "CRX498 // FL045 -> GND",
        "radar_sub": "DEPARTURE CLIMB // FATAL SPATIAL DISORIENTATION SPIRAL",
        "dist_info_header": "SPATIAL DISORIENTATION IN INSTRUMENT METEOROLOGICAL CONDITIONS:",
        "dist_info_main": "CAPTAIN TURNED RIGHT INSTEAD OF LEFT INTO A 137° HARD ROLL",
        "dist_info_sub": "CONFLICTING ATTITUDE INDICATOR SYMBOLOGY: SOVIET VS WESTERN GYROS",
        "cvr_warning": "BANK ANGLE // SPIRAL DIVE",
        "cvr_sub_warning": "ATTITUDE DIRECTOR INDICATOR CONFUSION",
        "telemetry": "ALT: 3,200 FT // IAS: 285 KT // ROLL: 137° RIGHT // SINK: -12,000 FPM",
        "bank_angle_base": 48.0,
        "maint_header": "HUMAN FACTORS & INSTRUMENT DISPLAY INTERFACE ANALYSIS",
        "maint_box1_title": "ATTITUDE INDICATOR: WESTERN EADI",
        "maint_box1_part": "COLLINS ELECTRONIC FLIGHT DISPLAY",
        "maint_box1_val": "HORIZON ROLLS WITH AIRCRAFT",
        "maint_box1_bullets": [
            "• Western display shows fixed aircraft symbol over moving horizon",
            "• Captain trained on Soviet aircraft with moving aircraft over fixed horizon",
            "• Under stress in clouds, captain reverted to early muscle memory!"
        ],
        "maint_box2_title": "FLIGHT CREW COORDINATION BREAKDOWN",
        "maint_box2_part": "FIRST OFFICER TIMELY INTERVENTION",
        "maint_box2_val": "FAILED TO TAKE DUAL CONTROL",
        "maint_box2_bullets": [
            "• FO observed right turn but did not assertively seize flight controls",
            "• Aircraft rolled past 90° into inverted dive within 15 seconds",
            "• High-speed ground impact occurred 2 minutes after takeoff!"
        ],
        "maint_footer_title": "SWISS AIRCRAFT ACCIDENT INVESTIGATION BUREAU (BFU):",
        "maint_footer_main": "PILOT TRAINING DISCREPANCY & SPATIAL DISORIENTATION AUDIT",
        "maint_footer_sub": "RESULT: STRICT TYPE-RATING STANDARDIZATION FOR CREWS TRANSITIONING FROM EASTERN BLOC AVIONICS",
        "investigation_agency": "BFU (SWITZERLAND) ACCIDENT INVESTIGATION DOSSIER",
        "probable_cause": "The flight crew lost spatial orientation and entered an unrecoverable spiral dive.",
        "cause_sub": "Captain reverted to ingrained Soviet-style attitude indicator interpretation under stress in dense cloud.",
        "findings": [
            ("1. SPATIAL DISORIENTATION", "Captain lost situational awareness immediately after entering overcast cloud ceiling."),
            ("2. GYRO DISPLAY CONFLICT", "Reversal error in reading western attitude director indicator due to previous Soviet training."),
            ("3. CRM HIERARCHY FAILURE", "First officer failed to recognize the severity of the bank and take over control."),
            ("4. STRICT AIRLINE COCKPIT ERGONOMICS", "EASA mandated cognitive ergonomic checks for pilots converting from Eastern Bloc aircraft.")
        ],
        "cvr_dialogues": [
            ("17:55:10", "ZURICH TOWER", '"Crossair 498, cleared for takeoff runway 28."', (234, 179, 8), (255, 255, 255)),
            ("17:56:00", "ZURICH DEP", '"Crossair 498, turn left heading 220."', (234, 179, 8), (255, 255, 255)),
            ("17:56:15", "ZURICH DEP", '"Crossair 498, confirm turning left? You are turning right!"', (239, 68, 68), (255, 230, 230)),
            ("17:56:22", "CRX498 (FO)", '"Left, left, left! Turn left!"', (239, 68, 68), (255, 255, 255)),
            ("17:56:27", "CRX498 (CVR)", '[BANK ANGLE AUDIO ALERT // ROLL REACHES 137° INVERTED]', (239, 68, 68), (255, 200, 200))
        ],
        "crm_nodes": [
            ("1. OVERCAST ENTRY", "Loss of Visual Horizon", "Aircraft entered freezing drizzle and clouds 30 seconds after departure.", (234, 179, 8)),
            ("2. ERGONOMIC GYRO CLASH", "Soviet vs Western Horizon", "Captain reverted to Soviet mental model where horizon bar remains stationary.", (239, 68, 68)),
            ("3. INVERTED ROLL SPIRAL", "Turned Right into 137° Roll", "Attempting to level wings, captain commanded opposite roll, putting plane on its back.", (239, 68, 68)),
            ("4. LATE INTERVENTION", "First Officer Hesitation", "Subordinate copilot verbally warned but did not assertively seize the control column.", (239, 68, 68))
        ],
        "speech_bubble_triggers": [
            (["soviet", "horizon", "gyro", "eadi", "indicator"], "SPATIAL DISORIENTATION // GYRO CONFUSION!", "left", (234, 179, 8), "SPATIAL DISORIENTATION"),
            (["bank", "roll", "spiral", "137", "right"], "137° HARD BANK // ROLL INVERSION!", "right", (220, 38, 38), "CRX498 [FO HOEFER]"),
            (["turn left", "left", "confirm"], "TURN LEFT! TURN LEFT!", "right", (220, 38, 38), "CRX498 [FO HOEFER]")
        ]
    },
    "sas_751": {
        "key": "sas_751",
        "is_ground_incident": False,
        "flight_no": "SK751",
        "squawk": "2132",
        "aircraft": "McDonnell Douglas MD-81",
        "operator": "Scandinavian Airlines (SAS)",
        "location": "Gottröra, Sweden (near Stockholm Arlanda Airport)",
        "atc_facility": "STOCKHOLM APPROACH // 122.50 MHz",
        "atc_msg_1": 'SK751: "Stockholm, Scandinavian 751 climbing through 2,500 feet."',
        "atc_msg_2": 'SK751: "Scandinavian 751, Mayday! We have lost both engines!"',
        "atc_msg_3": 'APPROACH: "Scandinavian 751, roger, turn heading 180, return Arlanda."',
        "atc_radar_tag": "SK751 // FL032 -> GND",
        "radar_sub": "CLEAR ICE INGESTION // DUAL ENGINE FAILURE // FORCED GLIDE LANDING",
        "dist_info_header": "UNNOTICED CLEAR ICE INGESTION & AUTOMATIC THRUST RESTORATION:",
        "dist_info_main": "CLEAR ICE BROKE OFF WINGS INTO BOTH REAR ENGINES AT 3,000 FT",
        "dist_info_sub": "AUTOMATIC THRUST RESTORATION (ATR) SYSTEM OVERRODE PILOT THROTTLE RETRACTION",
        "cvr_warning": "DUAL ENGINE SURGE // COMPRESSOR STALL",
        "cvr_sub_warning": "COMPLETE LOSS OF THRUST AT 3,200 FT",
        "telemetry": "ALT: 3,200 FT -> 0 FT // IAS: 160 KT // DUAL FLAMEOUT // GLIDE DISTANCE: 4 NM",
        "bank_angle_base": 12.0,
        "maint_header": "DE-ICING OVERSIGHT & UNDISCLOSED AUTOMATION LOGIC",
        "maint_box1_title": "CLEAR ICE ACCRETION ON WINGS",
        "maint_box1_part": "COLD-SOAKED WING UPPER SURFACE",
        "maint_box1_val": "CLEAR TRANSPARENT ICE SHEET",
        "maint_box1_bullets": [
            "• Overnight freezing precipitation chilled fuel in wing tanks to -10°C",
            "• Ground de-icing crew did not physically feel for invisible clear ice",
            "• Flexing wing upon liftoff broke ice sheets directly into aft JT8D engines!"
        ],
        "maint_box2_title": "AUTOMATIC THRUST RESTORATION (ATR)",
        "maint_box2_part": "UNDISCLOSED MD-81 COMPUTER SYSTEM",
        "maint_box2_val": "AUTOMATICALLY ADVANCED THROTTLES",
        "maint_box2_bullets": [
            "• Captain throttled back to stop violent engine surges and bangs",
            "• Unknown ATR computer system auto-pushed throttles back to full power",
            "• Repeated compressor surges disintegrated both engines completely!"
        ],
        "maint_footer_title": "SHK (SWEDISH ACCIDENT INVESTIGATION AUTHORITY):",
        "maint_footer_main": "AIRLINE DE-ICING REVISION & HIDDEN AVIONICS MANDATES",
        "maint_footer_sub": "RESULT: ZERO FATALITIES // CAPTAIN RASMUSSEN MASTERFUL MEADOW GLIDE LANDING",
        "investigation_agency": "SHK (SWEDEN) ACCIDENT INVESTIGATION DOSSIER",
        "probable_cause": "Dual engine failure caused by clear ice ingestion compounded by undisclosed ATR system logic.",
        "cause_sub": "SAS operations and maintenance failed to detect clear ice; ATR increased power into destroyed engines.",
        "findings": [
            ("1. UNDETECTED CLEAR ICE", "Invisible ice formed on cold-soaked wings was ingested by aft-mounted engines at liftoff."),
            ("2. SECRET ATR AUTOMATION", "Pilots were never trained on the ATR system, which overrode throttle pull-back."),
            ("3. ASSISTING OFF-DUTY CAPTAIN", "Off-duty captain Per Holmberg entered cockpit to assist with emergency glide checklist."),
            ("4. MIRACLE AT GOTTRÖRA", "Masterful deadstick forced landing in a snow-covered forest clearing; all 129 aboard survived.")
        ],
        "cvr_dialogues": [
            ("08:48:15", "STOCKHOLM TOWER", '"Scandinavian 751, cleared for takeoff runway 08."', (234, 179, 8), (255, 255, 255)),
            ("08:48:40", "SK751 (FO)", '"Rotate. We are airborne."', (56, 189, 248), (255, 255, 255)),
            ("08:49:05", "SK751 (CVR)", '[LOUD BANGS // REPEATED COMPRESSOR SURGES // ENGINE 2 VIBRATION]', (239, 68, 68), (255, 220, 220)),
            ("08:49:30", "SK751 (CAPT RASMUSSEN)", '"Both engines are failing! Throttle back! What is pushing the thrust?!"', (239, 68, 68), (255, 255, 255)),
            ("08:50:10", "SK751 (CAPT RASMUSSEN)", '"Flaps down! Looking for a field ahead! Brace for impact!"', (34, 197, 94), (255, 255, 255))
        ],
        "crm_nodes": [
            ("1. COLD-SOAKED WINGS", "Undetected Clear Ice", "Sub-zero fuel formed transparent ice on upper wings that broke loose upon liftoff.", (239, 68, 68)),
            ("2. DUAL INGESTION SURGE", "Aft Engines Damaged", "Ice slabs sucked into rear JT8D engines, breaking fan blades and triggering loud surges.", (239, 68, 68)),
            ("3. SECRET ATR OVERRIDE", "Automation Pushed Throttles", "Undisclosed computer auto-advanced throttles, destroying damaged engines completely.", (239, 68, 68)),
            ("4. HEROIC GLIDE LANDING", "Gottröra Meadow Miracle", "Captain Rasmussen glided the glider-like airliner through trees into a clearing. 0 deaths.", (34, 197, 94))
        ],
        "speech_bubble_triggers": [
            (["ice", "clear ice", "cold-soaked", "de-icing"], "CLEAR ICE BROKE OFF WINGS!", "left", (234, 179, 8), "MD-81 ICE SURGE"),
            (["surge", "compressor", "bang", "thrust", "atr"], "ATR AUTO-PUSHED THROTTLES!", "right", (220, 38, 38), "SK751 [CAPT RASMUSSEN]"),
            (["field", "meadow", "gottrora", "brace", "deadstick"], "DEADSTICK GLIDE TO GOTTRÖRA!", "right", (34, 197, 94), "SK751 [CAPT RASMUSSEN]")
        ]
    },
    "tuninter_1153": {
        "key": "tuninter_1153",
        "is_ground_incident": False,
        "flight_no": "TNI1153",
        "squawk": "1153",
        "aircraft": "ATR 72-202",
        "operator": "Tuninter",
        "location": "Mediterranean Sea, off coast of Palermo, Sicily",
        "atc_facility": "PALERMO APPROACH // 118.10 MHz",
        "atc_msg_1": 'TNI1153: "Palermo Approach, Tuninter 1153, declaring emergency, both engines flamed out!"',
        "atc_msg_2": 'APPROACH: "Tuninter 1153, roger, runway 25 available, distance 18 miles, can you make it?"',
        "atc_msg_3": 'TNI1153: "Negative, we cannot maintain altitude, we are ditching into the sea!"',
        "atc_radar_tag": "TNI1153 // FL040 -> SEA",
        "radar_sub": "DUAL FLAMEOUT // FUEL EXHAUSTION",
        "dist_info_header": "EMERGENCY DITCHING PROFILE:",
        "dist_info_main": "PALERMO SECTOR // 18 NM NORTH OF PUNTA RAISI",
        "dist_info_sub": "ATR 72 GLIDE RATIO DEGRADED DUE TO UNFEATHERED PROPELLERS",
        "cvr_warning": "DUAL FLAMEOUT // FUEL EMPTY",
        "cvr_sub_warning": "ATR 42 FUEL GAUGE MISFIT IN ATR 72",
        "telemetry": "ALT: 1,800 FT // IAS: 115 KT // SINK: -1,200 FPM // PUNTA RAISI 18 NM",
        "bank_angle_base": 15.0,
        "maint_header": "MAINTENANCE BLUNDER // FUEL QUANTITY INDICATOR SWAP",
        "maint_box1_title": "INSTALLED: ATR 42 GAUGE",
        "maint_box1_part": "P/N: 730-001-201 (ATR 42 ONLY)",
        "maint_box1_val": "INDICATED: 2,700 KG",
        "maint_box1_bullets": [
            "• Maintenance technician swapped gauge without verifying part catalog",
            "• ATR 42 gauge calibrated for shallower fuel tank profile",
            "• Indicated 1,800 kg 'ghost fuel' when tanks were nearly dry!"
        ],
        "maint_box2_title": "REQUIRED: ATR 72 GAUGE",
        "maint_box2_part": "P/N: 730-001-301 (ATR 72 MANDATE)",
        "maint_box2_val": "ACTUAL FUEL: 305 KG",
        "maint_box2_bullets": [
            "• Both engines starved of fuel at FL230 over open ocean",
            "• Crew did not feather propellers, drastically cutting glide distance",
            "• Forced ditching into Mediterranean waves 18 miles offshore!"
        ],
        "maint_footer_title": "ANSV (ITALY) OFFICIAL ACCIDENT AUDIT:",
        "maint_footer_main": "INCORRECT AVIONICS PART REPLACEMENT WITHOUT INDEPENDENT VERIFICATION",
        "maint_footer_sub": "RESULT: COMPLETE IN-FLIGHT FUEL STARVATION & MEDITERRANEAN DITCHING",
        "investigation_agency": "ANSV (ITALY) ACCIDENT INVESTIGATION DOSSIER",
        "probable_cause": "Both engines stopped due to fuel exhaustion caused by incorrect fuel quantity indicator.",
        "cause_sub": "ATR 42 fuel gauge was installed in an ATR 72, showing 1,800 kg fuel when tanks were empty.",
        "findings": [
            ("1. GAUGE SWAP ERROR", "Maintenance mechanics fitted ATR 42 fuel gauge into ATR 72, causing phantom fuel reading."),
            ("2. INADEQUATE PART TRACKING", "Stockroom lacked mechanical keying or color-coding to prevent cross-fitting between variants."),
            ("3. PROPELLER FEATHERING FAILURE", "Crew failed to feather unpowered propellers, cutting gliding distance by half."),
            ("4. STRICT AIRLINE AVIONICS AUDIT", "Mandated visual part verification and independent sign-off on all fuel sensor units.")
        ],
        "cvr_dialogues": [
            ("15:20:15", "TNI1153 (CAPT)", '"Right engine flamed out! Starting fuel crossfeed!"', (239, 68, 68), (255, 230, 230)),
            ("15:21:40", "TNI1153 (FO)", '"Left engine flamed out too! Both engines are dead!"', (239, 68, 68), (255, 220, 220)),
            ("15:23:05", "TNI1153 (CAPT)", '"Mayday! Mayday! Tuninter 1153, dual flameout, ditching into sea!"', (56, 189, 248), (255, 255, 255)),
            ("15:23:18", "PALERMO APP", '"Tuninter 1153, runway 25 distance 18 miles, can you reach?"', (234, 179, 8), (255, 255, 255)),
            ("15:24:00", "TNI1153 (CAPT)", '"Negative, we cannot make the runway. We are in the water!"', (239, 68, 68), (255, 255, 255))
        ],
        "crm_nodes": [
            ("1. PART CATALOGUE MIXUP", "ATR 42 Gauge in ATR 72", "Mechanic grabbed physically identical ATR 42 indicator calibrated for different tank shape.", (239, 68, 68)),
            ("2. GHOST FUEL PHANTOM", "Showed 1,800 kg Extra Fuel", "Flight crew saw full fuel bars on display; neither crew nor fueling team noticed discrepancy.", (239, 68, 68)),
            ("3. MID-MEDITERRANEAN OUTAGE", "Dual Flameout at FL230", "Both turboprops flamed out sequentially as fuel feed line sucked air over open ocean.", (239, 68, 68)),
            ("4. UNFEATHERED PROPELLERS", "Windmilling Drag Penalty", "Crew focused on engine restart; unfeathered blades acted like airbrakes, forcing sea ditching.", (234, 179, 8))
        ],
        "speech_bubble_triggers": [
            (["gauge", "indicator", "part", "misfit", "swap"], "ATR 42 GAUGE IN ATR 72!", "left", (220, 38, 38), "MAINTENANCE ERROR"),
            (["fuel", "empty", "exhaustion", "starvation", "ghost fuel"], "1,800 KG GHOST FUEL!", "left", (220, 38, 38), "FUEL QUANTITY SYSTEM"),
            (["flameout", "dead", "engines out"], "DUAL FLAMEOUT IN CLOUD!", "right", (220, 38, 38), "TNI1153 [CAPT GHARBI]"),
            (["ditch", "water", "sea", "palermo"], "MAYDAY! DITCHING OFF PALERMO!", "right", (239, 68, 68), "TNI1153 [CAPT GHARBI]")
        ]
    }
}


def resolve_aviation_incident(text: str = "", vehicle_name: str = "", title: str = "") -> dict:
    query = (str(text) + " " + str(vehicle_name) + " " + str(title)).lower()
    
    if any(k in query for k in ("spanair", "5022", "jk5022", "barajas", "madrid", "undeployed flaps", "silent wingtip", "tocw", "r2-5")):
        return AVIATION_INCIDENTS["spanair_5022"]
    if any(k in query for k in ("fine air", "101", "fjn101", "tail-heavy", "five tons missing", "aft cg", "mac", "dc-8", "miami")):
        return AVIATION_INCIDENTS["fine_air_101"]
    if any(k in query for k in ("tenerife", "klm", "pan am", "los rodeos", "4805", "1736", "runway collision", "we gaan", "fog catastrophe", "van zanten", "meurs", "grubbs", "bragg", "clipper 1736")):
        return AVIATION_INCIDENTS["tenerife"]
    if any(k in query for k in ("qantas", "72", "qf72", "adiru", "uncommanded pitch-down", "pitch down", "learmonth", "sullivan", "a330")):
        return AVIATION_INCIDENTS["qantas_72"]
    if any(k in query for k in ("crossair", "498", "crx498", "saab 340", "zurich", "sixty seconds", "spatial disorientation", "niederhasli", "eadi", "spiral dive")):
        return AVIATION_INCIDENTS["crossair_498"]
    if any(k in query for k in ("scandinavian", "sas", "751", "sk751", "dana viking", "clear ice", "meadow", "gottröra", "arlanda", "miracle of gottrora", "four minutes to clear")):
        return AVIATION_INCIDENTS["sas_751"]
    if any(k in query for k in ("tuninter", "1153", "tni1153", "palermo", "punta raisi", "ditching", "atr 42", "atr 72")):
        return AVIATION_INCIDENTS["tuninter_1153"]
        
    # Dynamic synthesis for unknown flight
    flight_match = re.search(r'\b([A-Z]{2,3}\s*\d{2,4}|flight\s*\d{2,4})\b', query, re.I)
    fl_name = flight_match.group(0).upper() if flight_match else (vehicle_name.upper() if vehicle_name else "COMMERCIAL FLIGHT")
    return {
        "flight_no": fl_name,
        "squawk": "7700",
        "aircraft": vehicle_name or "Commercial Airliner",
        "operator": "Civilian Aviation",
        "location": "En Route Airspace",
        "atc_facility": "AREA AIR TRAFFIC CONTROL // 121.50 MHz",
        "atc_msg_1": f'{fl_name}: "MAYDAY, MAYDAY, MAYDAY! Declaring flight emergency."',
        "atc_msg_2": f'ATC: "{fl_name}, radar contact, squawk 7700, turn heading 270."',
        "atc_msg_3": f'{fl_name}: "Roger, descending to maintain control, emergency in progress."',
        "atc_radar_tag": f"{fl_name} // SQUAWK 7700",
        "radar_sub": "EMERGENCY DESCENT // AVIONICS FAILURE",
        "dist_info_header": "EMERGENCY FLIGHT RECONSTRUCTION:",
        "dist_info_main": f"{fl_name} COCKPIT CALLOUT INTERCEPT",
        "dist_info_sub": "FLIGHT CREW INITIATED EMERGENCY PROTOCOL UNDER ADVERSE CONDITIONS",
        "cvr_warning": "MASTER WARNING // FLIGHT FAULT",
        "cvr_sub_warning": "AVIONICS ANOMALY DETECTED IN FLIGHT",
        "telemetry": "ALT: 8,000 FT // IAS: 210 KT // PITCH: -4° // SQUAWK: 7700",
        "bank_angle_base": 25.0,
        "maint_header": "TECHNICAL FAILURE & AVIONICS INVESTIGATION",
        "maint_box1_title": "INDICATED ANOMALY // SENSOR FAULT",
        "maint_box1_part": "SYSTEM: PRIMARY AVIONICS",
        "maint_box1_val": "CRITICAL DISCREPANCY DETECTED",
        "maint_box1_bullets": [
            "• Flight data recorded unexpected system deviation",
            "• Sensor inputs diverged from actual flight dynamics",
            "• Emergency checklists executed under extreme stress!"
        ],
        "maint_box2_title": "OPERATIONAL IMPACT // CREW RESPONSE",
        "maint_box2_part": "FLIGHT CONTROL SURFACES",
        "maint_box2_val": "MANUAL CONTROL ENGAGED",
        "maint_box2_bullets": [
            "• Crew disconnected automation to regain manual control",
            "• Flight vectors managed under severe system degradation",
            "• Radio communications coordinated with air traffic control!"
        ],
        "maint_footer_title": "SAFETY INVESTIGATION AGENCY OFFICIAL AUDIT:",
        "maint_footer_main": "ACCIDENT INVESTIGATION & FDR TELEMETRY RECONSTRUCTION",
        "maint_footer_sub": "RESULT: OFFICIAL INQUIRY INTO CAUSAL FACTORS AND REGULATORY SAFETY MANDATES",
        "investigation_agency": "CIVIL AVIATION SAFETY INVESTIGATION DOSSIER",
        "probable_cause": "System failure resulting in degraded flight envelope and control challenges.",
        "cause_sub": "Uncommanded deviation compounded by critical environmental and technical factors.",
        "findings": [
            ("1. TECHNICAL DIVERGENCE", "Telemetry recorded divergence in flight control and instrument readings."),
            ("2. COCKPIT WORKLOAD", "High workload during emergency phase challenged crew resource management."),
            ("3. AIR TRAFFIC COORDINATION", "ATC radar vectoring supported descent to nearest suitable landing site."),
            ("4. SAFETY RECOMMENDATIONS", "Comprehensive directives issued to prevent recurring technical failures.")
        ]
    }



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

    k = (_CURRENT_CHANNEL_ID, name, target_h)
    if k not in _CACHED_POSES:
        is_av = is_aviation_context() or any(w in _CURRENT_CHANNEL_ID for w in ("blackbox", "aviation", "flight"))
        cand_dirs = [BOSKAFA_DIR, BASE_DIR / "assets/characters/aviation"] if is_av else [CHAR_DIR, BOSKAFA_DIR]
        p = None
        for cdir in cand_dirs:
            for fname in [f"host_{name}.png", f"crayon_{name}.png", f"{name}.png", f"{name}_open.png", "pointing.png"]:
                if (cdir / fname).exists():
                    p = cdir / fname
                    break
            if p:
                break
        if p and p.exists():
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
    is_av_chan = is_aviation_context() or any(w in _CURRENT_CHANNEL_ID for w in ("blackbox", "aviation", "flight"))
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
        "HOST": "pointing.png" if is_av_chan else "host_smug.png",
        "PILOT": "captain_calm.png" if is_av_chan else "test_pilot.png",
        "GENERAL": "ntsb_investigator.png" if is_av_chan else "crayon_pentagon_general.png",
        "CEO": "aircraft_mechanic.png" if is_av_chan else "crayon_defense_ceo.png",
        "SPY": "atc_controller.png" if is_av_chan else "foreign_spy.png",
        "FOUNDER": "aircraft_mechanic.png" if is_av_chan else "crayon_tech_founder.png",
        "TRADER": "aircraft_mechanic.png" if is_av_chan else "crayon_wall_street_trader.png",
        "SCIENTIST": "aircraft_mechanic.png" if is_av_chan else "crayon_tech_founder.png"
    }
    target_file = "pointing.png" if is_av_chan else "host_smug.png"
    for k, v in file_map.items():
        if k in role_u:
            target_file = v
            break

    if is_av_chan:
        search_dirs = [
            BASE_DIR / "assets/characters/aviation",
            BASE_DIR / "assets/boskafa",
            BASE_DIR / "assets/characters",
        ]
    else:
        search_dirs = [
            CHAR_DIR,
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
    bg_p = scene_data.get("topic_bg") or TECH_BG
    bg = get_cached_bg(Path(bg_p), (W, H)).copy()
    if str(bg_p) != str(TECH_BG):
        dimmed = Image.new("RGBA", (W, H), (15, 23, 42, 140))
        bg = Image.alpha_composite(bg, dimmed)
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
    bg_p = scene_data.get("topic_bg") or WAR_ROOM_BG
    bg = get_cached_bg(Path(bg_p)).copy()
    if bg_p != WAR_ROOM_BG:
        dimmed = Image.new("RGBA", (W, H), (15, 23, 42, 120))
        bg = Image.alpha_composite(bg, dimmed)
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
    
    is_av = is_aviation_context(scene_data, text=sub_title)
    if is_av:
        inc = resolve_aviation_incident(sub_title + " " + str(scene_data.get("narration", "")), vehicle_name=scene_data.get("vehicle_name", ""))
        # Civil Primary & Secondary Radar Target Blips
        b1 = (cx + 140, cy - 120)
        draw.rectangle([(b1[0]-10, b1[1]-10), (b1[0]+10, b1[1]+10)], outline=(239, 68, 68), width=3)
        draw.text((b1[0] + 16, b1[1] - 8), f"{inc['flight_no']} // SQUAWK {inc['squawk']}", font=get_font_safe(16, mono=True, bold=True), fill=(239, 68, 68))
        draw.text((b1[0] + 16, b1[1] + 12), inc['radar_sub'][:32], font=get_font_safe(13, mono=True), fill=(234, 179, 8))
        
        b2 = (cx - 200, cy + 90)
        draw.rectangle([(b2[0]-8, b2[1]-8), (b2[0]+8, b2[1]+8)], outline=(34, 197, 94), width=2)
        draw.text((b2[0] + 14, b2[1] - 6), f"CIVIL AIRLINE // {inc['aircraft'][:22]}", font=get_font_safe(14, mono=True), fill=(34, 197, 94))
        
        # Telemetry Card
        draw.rounded_rectangle([(80, 160), (480, 460)], radius=12, fill=(15, 23, 42, 230), outline=(34, 197, 94), width=2)
        draw.text((100, 180), "ATC SURVEILLANCE RADAR", font=get_pop_font(24), fill=(34, 197, 94))
        draw.text((100, 225), f"FACILITY: {inc['atc_facility'][:25]}", font=get_font_safe(15, mono=True), fill=(203, 213, 225))
        draw.text((100, 260), f"BEARING: {int(math.degrees(ang)):03d}° // SWEEP 30 RPM", font=get_font_safe(15, mono=True), fill=(34, 197, 94))
        draw.text((100, 295), f"FLIGHT: {inc['flight_no']}", font=get_font_safe(16, mono=True, bold=True), fill=(239, 68, 68))
        draw.text((100, 330), f"ALTITUDE: {inc.get('telemetry', 'FL180')[:26]}", font=get_font_safe(14, mono=True), fill=(234, 179, 8))
        draw.text((100, 365), f"SECTOR: {inc['location'][:28]}", font=get_font_safe(14, mono=True), fill=(203, 213, 225))
    else:
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
    text = (sub_title + " " + scene_data.get("narration", "") + " " + scene_data.get("chapter", "")).lower()
    is_arctic = any(w in text for w in ["norway", "arctic", "cold response", "sub-zero", "scandinavia", "minus thirty", "frozen"])

    if is_arctic and ARCTIC_MAP_BG.exists():
        bg = get_cached_bg(ARCTIC_MAP_BG).copy()
        frame.paste(bg, (0, 0))
        # Flight path from Southern logistics base (Oslo/Ramstein) to Arctic Norway (Tromso/Bodo, 69°N)
        p1, p2 = (880, 780), (1380, 260)
        mid_x, mid_y = 1060, 480
    else:
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
        
        if is_arctic:
            draw.text((pin_x - 120, pin_y - 75), "BODØ / TROMSØ (69°14'N)", font=get_font_safe(18, bold=True, mono=True), fill=(234, 179, 8))
            draw.text((pin_x - 120, pin_y - 55), "TEST TEMP: -30°C ARCTIC", font=get_font_safe(16, mono=True), fill=(56, 189, 248))
    
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
    is_av = is_aviation_context(scene_data, text=sub_title)
    if is_av:
        inc = resolve_aviation_incident(text + " " + sub_title, vehicle_name=scene_data.get("vehicle_name", ""))
        bp_title = f"AVIONICS SCHEMATIC // {inc['aircraft'].upper()}"
        fp_text = f"CRITICAL ANOMALY: {inc['maint_box1_title'][:30]}"
        card_hdr = f"{inc['flight_no']} AVIONICS & SYSTEM INTEGRITY:"
        specs = [
            f"• Airframe: {inc['aircraft']} ({inc['operator']})",
            f"• Sector: {inc['location'][:38]}",
            f"• System Malfunction: {inc['maint_box1_val'][:36]}",
            f"• Flight Response: {inc['maint_box2_val'][:36]}",
            f"• Telemetry State: {inc.get('telemetry', '')[:38]}"
        ]
        partner_role = "MECHANIC"
    elif any(k in text for k in ["symbol", "entry", "breach", "fema", "x-mark", "quadrant", "chevron", "marking", "chalk", "shorthand"]):
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
        partner_role = "GENERAL"
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
        partner_role = "GENERAL"
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
        partner_role = "GENERAL"
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
        partner_role = "GENERAL"

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
        if any(w in sp for w in ["Damage", "Degraded", "Error", "Stall", "Failed"]):
            sp_col = (239, 68, 68)
        elif any(w in sp for w in ["Fix", "Intact", "Cost", "Normal"]):
            sp_col = (34, 197, 94)
        else:
            sp_col = (255, 255, 255)
        draw.text((bx + 685, by + 175 + s_i * 48), sp, font=get_font_safe(20), fill=sp_col)
    
    frame.alpha_composite(host_shock, (30, H - host_shock.height - 20))
    side_char = load_character_sprite(partner_role, 540)
    frame.alpha_composite(side_char, (W - side_char.width - 25, H - side_char.height - 20))
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
    is_av = is_aviation_context(scene_data, text=sub_title)
    if is_av:
        inc = resolve_aviation_incident(text + " " + sub_title, vehicle_name=scene_data.get("vehicle_name", ""))
        warn_title = f"COCKPIT EMERGENCY ALERT // {inc['cvr_warning'][:40]}"
        bullets = [
            f"• Emergency Event: {inc['dist_info_main'][:60]}",
            f"• Primary Malfunction: {inc['cvr_sub_warning'][:60]}",
            f"• Flight Telemetry: {inc.get('telemetry', '')[:60]}",
            f"• Sector / Impact: {inc['location'][:60]}"
        ]
        alert_tag = f"CRITICAL INCIDENT // SQUAWK {inc['squawk']} EMERGENCY DECLARATION"
    elif any(k in text for k in ["spray", "aerosol", "can", "paint", "shrapnel", "fume", "flame"]):
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
    elif any(k in text for k in ["cockpit", "avionics", "altitude", "display", "clutter", "radial", "approach", "flight"]):
        warn_title = "AVIONICS OCCLUSION // FLIGHT DISPLAY CLUTTER HAZARD"
        bullets = [
            "• Thick grease wax lines obscure critical primary flight displays",
            "• High-workload instrument approach: Pilot misreads runway heading",
            "• Multi-layer chart clutter causes spatial disorientation",
            "• Flight Safety Board: Clean glass cockpit protocol enforced"
        ]
        alert_tag = "FLIGHT SAFETY HAZARD // INSTRUMENT OCCLUSION RISK"
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
        clean_sub = sub_title
        for prefix in ["PROJECT SCRAPPED: ", "CRITICAL HAZARD: ", "TACTICAL ALERT: ", "MISSION ABORT: "]:
            if clean_sub.startswith(prefix):
                clean_sub = clean_sub[len(prefix):]
        if "REVERT TO" in clean_sub or "$0.85" in clean_sub:
            lead_bullet = "• High operational friction: Troops revert to $0.85 wax"
        else:
            lead_bullet = f"• High operational friction: {clean_sub}"
            test_bbox = draw.textbbox((0, 0), lead_bullet, font=get_pop_font(23))
            if (test_bbox[2] - test_bbox[0]) > 860:
                lead_bullet = textwrap.shorten(lead_bullet, width=56, placeholder="...")

        bullets = [
            lead_bullet,
            "• Frontline tactical marking protocol compromised",
            "• Analog backup demanded by frontline combat leaders",
            "• Pentagon oversight notified of procedural deviation"
        ]
        alert_tag = "TACTICAL ALERT // IMMEDIATE REVIEW MANDATE"

    # Central Warning Badge
    cx, cy, bw, bh = 960, 500, 1020, 430
    bx, by = cx - bw // 2, cy - bh // 2
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=20, fill=(15, 23, 42, 245), outline=(239, 68, 68), width=5)
    
    draw.text((bx + 50, by + 50), warn_title, font=get_pop_font(28), fill=(239, 68, 68))
    for i, b in enumerate(bullets):
        if i == 2:
            b_c = (234, 179, 8)
        elif i == 3:
            b_c = (34, 197, 94)
        else:
            b_c = (255, 255, 255)
        draw.text((bx + 50, by + 115 + i * 50), b, font=get_pop_font(23), fill=b_c)
    draw.text((bx + 50, by + 325), alert_tag, font=get_pop_font(26), fill=(239, 68, 68))
    
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
    topic_bg_p = scene_data.get("topic_bg")
    if topic_bg_p and Path(topic_bg_p).is_file():
        bg = get_cached_bg(Path(topic_bg_p), (W, H)).copy()
        dimmed = Image.new("RGBA", (W, H), (10, 16, 26, 180))
        bg = Image.alpha_composite(bg, dimmed)
        frame.paste(bg, (0, 0))
    else:
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
    topic_bg_p = scene_data.get("topic_bg")
    if topic_bg_p and Path(topic_bg_p).is_file():
        bg = get_cached_bg(Path(topic_bg_p), (W, H)).copy()
        dimmed = Image.new("RGBA", (W, H), (15, 23, 42, 180))
        bg = Image.alpha_composite(bg, dimmed)
        frame.paste(bg, (0, 0))
    else:
        draw.rectangle([(0, 0), (W, H)], fill=(15, 23, 42))
    for gx in range(0, W, 80): draw.line([(gx, 0), (gx, H)], fill=(24, 36, 60), width=1)
    for gy in range(0, H, 80): draw.line([(0, gy), (W, gy)], fill=(24, 36, 60), width=1)
    
    text = (scene_data.get("narration", "") + " " + scene_data.get("chapter", "") + " " + sub_title).lower()
    is_av = is_aviation_context(scene_data, text=sub_title)
    if is_av:
        inc = resolve_aviation_incident(text + " " + sub_title, vehicle_name=scene_data.get("vehicle_name", ""))
        table_hdr = f"{inc['investigation_agency'][:42]} // OFFICIAL BRIEFING"
        lesson_title = f"{inc['flight_no']} INVESTIGATION & CAUSAL ANALYSIS"
        b1 = f"• Causal Event: {inc['probable_cause'][:60]}"
        b2 = f"• Latent Failure: {inc['cause_sub'][:60]}"
        b3 = f"• FDR Telemetry: {inc.get('telemetry', '')[:60]}"
        verdict = f"SAFETY MANDATE: {inc['findings'][3][1][:62]}"
        partner_role = "NTSB"
    elif any(k in text for k in ["symbol", "entry", "breach", "fema", "x-mark", "quadrant", "chevron", "marking", "shorthand"]):
        table_hdr = "TACTICAL URBAN DOCTRINE // COMBAT SYMBOLOGY BRIEFING"
        lesson_title = "DOCTRINE #1: STANDARDIZED MARKING SAVES LIVES"
        b1 = "• Room-to-room CQB requires immediate, unmistakable entry status."
        b2 = "• 4-Quadrant Door Matrix communicates time, unit, hazards, and victims."
        b3 = "• Single wax stroke prevents friendly squads from double-clearing."
        verdict = "VERDICT: CRITICAL SURVIVAL SHORTCUT ACROSS ALL CQB SECTORS"
        partner_role = "GENERAL"
    elif any(k in text for k in ["wand", "procurement", "overengineer", "patent", "shield", "drill", "bolt"]):
        table_hdr = "DEFENSE PROCUREMENT AUDIT // SIMPLICITY VS GADGETS"
        lesson_title = "LESSON #2: COMPLEX HARDWARE DITCHED ON FRONTLINE"
        b1 = "• 8-lb pneumatic wands and titanium stencils fail in battlefield dust."
        b2 = "• Batteries die, mechanical seals freeze, and electronics glitch."
        b3 = "• Troops invariably revert to the $0.85 pocket wax marker."
        verdict = "VERDICT: COMMON SENSE TRUMPS OVER-ENGINEERED DEFENSE GEAR"
        partner_role = "GENERAL"
    else:
        table_hdr = "STRATEGIC DEFENSE DOCTRINE & LESSONS LEARNED"
        lesson_title = "LESSON #1: ANALOG IS ESSENTIAL WHEN TECH FAILS"
        b1 = "• Satellite datalinks and digital GPS go dark under EW jamming."
        b2 = "• Analog grease markings remain the only failsafe combat channel."
        b3 = "• Yet $68B procurement waste cripples frontline readiness."
        verdict = "VERDICT: PENTAGON AUDIT DEMANDS DOCTRINAL REALITY CHECK"
        partner_role = "GENERAL"

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
    table_partner = load_character_sprite(partner_role, 550)
    frame.alpha_composite(table_partner, (W - table_partner.width - 25, H - table_partner.height - 20))
    draw_pop_title(draw, sub_title)


def render_crt_mainframe(frame: Image.Image, draw: ImageDraw.ImageDraw, t_sub: float, sub_title: str, scene_data: dict):
    draw.rectangle([(0, 0), (W, H)], fill=(8, 16, 12))
    for y in range(0, H, 6): draw.line([(0, y), (W, y)], fill=(12, 28, 18), width=2)
    
    draw.rectangle([(100, 160), (W - 100, H - 120)], outline=(0, 255, 120), width=3)
    draw.rectangle([(100, 160), (W - 100, 220)], fill=(0, 255, 120))
    chapter = scene_data.get("chapter", "").strip().upper()
    draw.text((120, 175), f"PENTAGON SECURE TERMINAL // {chapter[:48]}", font=get_pop_font(24), fill=(8, 16, 12))
    
    narr = scene_data.get("narration", "").strip()
    wrapped_narr = textwrap.wrap(narr, width=72)
    n1 = wrapped_narr[0] if len(wrapped_narr) > 0 else ""
    n2 = wrapped_narr[1] if len(wrapped_narr) > 1 else ""
    
    log_lines = [
        f"> AUDIT CHAPTER: {chapter}",
        f"> TRANSCRIPT: {n1}",
    ]
    if n2:
        log_lines.append(f"> LOG: {n2}")
    log_lines.extend([
        "> VERDICT: MIL-STD 810H PROTOCOL VIOLATION DETECTED",
        "> CLASSIFICATION: TOP SECRET // DOD OVERSIGHT ONLY"
    ])
    
    typing_speed = 120
    t_chars = int(t_sub * typing_speed)
    curr_chars = 0
    y_pos = 260
    font_term = get_pop_font(24)
    active_cursor_y = y_pos
    active_cursor_x = 140
    for line in log_lines:
        line_len = len(line)
        if t_chars >= curr_chars + line_len:
            draw.text((140, y_pos), line, font=font_term, fill=(0, 255, 120))
            line_bbox = draw.textbbox((140, y_pos), line, font=font_term)
            active_cursor_y = y_pos
            active_cursor_x = line_bbox[2]
        elif t_chars > curr_chars:
            visible_chars = t_chars - curr_chars
            visible = line[:visible_chars]
            draw.text((140, y_pos), visible, font=font_term, fill=(0, 255, 120))
            line_bbox = draw.textbbox((140, y_pos), visible, font=font_term)
            active_cursor_y = y_pos
            active_cursor_x = line_bbox[2]
        curr_chars += line_len
        y_pos += 58

    if int(t_sub * 4) % 2 == 0:
        cx = min(active_cursor_x + 8, W - 140)
        draw.rectangle([(cx, active_cursor_y + 2), (cx + 14, active_cursor_y + 28)], fill=(0, 255, 120))
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
    topic_bg_p = scene_data.get("topic_bg")
    if topic_bg_p and Path(topic_bg_p).is_file():
        bg = get_cached_bg(Path(topic_bg_p), (W, H)).copy()
        dimmed = Image.new("RGBA", (W, H), (*background, 190))
        bg = Image.alpha_composite(bg, dimmed)
        frame.paste(bg, (0, 0))
    else:
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
    footer_brand = "BLACK BOX AUDIO  //  FLIGHT INVESTIGATION DOSSIER" if is_aviation_context(scene_data) else "TACTICAL CRAYON  //  EDITORIAL BREAKDOWN"
    draw.text(
        (panel[0] + 40, panel[3] - 72),
        footer_brand,
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


# ═════════════════════════════════════════════════════════════════════════════
# BESPOKE AVIATION DOCUMENTARY RECONSTRUCTION ARCHETYPES (@blackboxaudioo)
# ═════════════════════════════════════════════════════════════════════════════

def render_aviation_cockpit_cvr(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    captain_img: Image.Image,
    fo_img: Image.Image,
    scene_data: dict,
    inc: dict = None
):
    if not inc:
        inc = resolve_aviation_incident(
            str(scene_data.get("narration", "")) + " " + str(sub_title),
            vehicle_name=str(scene_data.get("vehicle_name", ""))
        )
    pulse_warn = (math.sin(t_sub * 4.0) + 1.0) * 0.5
    for y in range(0, H, 4):
        ratio = y / H
        r = int(10 + pulse_warn * 26 + ratio * 12)
        g = int(14 * (1.0 - pulse_warn * 0.45) + ratio * 8)
        b = int(26 * (1.0 - pulse_warn * 0.4) + ratio * 14)
        draw.rectangle([(0, y), (W, y + 4)], fill=(r, g, b, 255))

    horiz_y = H // 2 - 20
    draw.line([(0, horiz_y), (W, horiz_y)], fill=(32, 46, 68), width=1)
    cx = W // 2
    draw.polygon([(cx - 24, 0), (cx + 24, 0), (cx + 36, horiz_y + 80), (cx - 36, horiz_y + 80)], fill=(18, 26, 38))
    draw.polygon([(0, 0), (80, 0), (130, horiz_y + 80), (0, horiz_y + 80)], fill=(18, 26, 38))
    draw.polygon([(W - 80, 0), (W, 0), (W, horiz_y + 80), (W - 130, horiz_y + 80)], fill=(18, 26, 38))

    dash_y = H - 230
    draw.polygon([(0, dash_y), (W, dash_y), (W, H), (0, H)], fill=(12, 17, 26))
    draw.line([(0, dash_y), (W, dash_y)], fill=(38, 54, 78), width=4)
    for i, lx in enumerate(range(160, W - 160, 65)):
        l_col = (255, 45, 45) if (int(t_sub * 5) + i) % 2 == 0 else (0, 220, 255)
        draw.ellipse([(lx, dash_y + 22), (lx + 8, dash_y + 30)], fill=l_col)

    aic_x, aic_y = cx, H // 2 - 25
    rad_r = 130
    draw.ellipse([(aic_x - rad_r - 8, aic_y - rad_r - 8), (aic_x + rad_r + 8, aic_y + rad_r + 8)], fill=(14, 22, 34), outline=(0, 160, 220), width=3)
    draw.ellipse([(aic_x - rad_r, aic_y - rad_r), (aic_x + rad_r, aic_y + rad_r)], fill=(10, 15, 25), outline=(0, 220, 255), width=2)
    is_ground = inc.get("is_ground_incident", False) or any(w in (sub_title + " " + scene_data.get("narration", "")).lower() for w in ["taxi", "runway", "ground", "backtaxi", "hold", "takeoff roll", "line up", "lining up"])
    if is_ground:
        bank_angle = math.sin(t_sub * 4.0) * 0.4  # Level runway centerline with slight surface rumble
        rad = math.radians(bank_angle)
        dx = int(math.cos(rad) * rad_r)
        dy = int(math.sin(rad) * rad_r)
        draw.line([(aic_x - dx, aic_y - dy), (aic_x + dx, aic_y + dy)], fill=(255, 210, 0), width=5)
        draw.ellipse([(aic_x - 6, aic_y - 6), (aic_x + 6, aic_y + 6)], fill=(255, 50, 50))
        ias_roll = 110 + int(t_sub * 15) if "takeoff" in sub_title.lower() or "roll" in sub_title.lower() else 15
        draw.text((aic_x - 160, aic_y + rad_r + 18), f"RUNWAY CENTERLINE // IAS: {ias_roll} KT // {inc.get('flight_no', '')}", font=get_font_safe(18, bold=True), fill=(0, 220, 255))
    else:
        bank_base = inc.get("bank_angle_base", 32.0)
        bank_angle = bank_base + math.sin(t_sub * 2.5) * 8.0
        rad = math.radians(bank_angle)
        dx = int(math.cos(rad) * rad_r)
        dy = int(math.sin(rad) * rad_r)
        draw.line([(aic_x - dx, aic_y - dy), (aic_x + dx, aic_y + dy)], fill=(255, 210, 0), width=5)
        draw.ellipse([(aic_x - 6, aic_y - 6), (aic_x + 6, aic_y + 6)], fill=(255, 50, 50))
        draw.text((aic_x - 120, aic_y + rad_r + 18), f"BANK ANGLE: {bank_angle:.0f}° ROLL // {inc.get('flight_no', '')}", font=get_font_safe(18, bold=True), fill=(255, 60, 60))

    is_flash = (int(t_sub * 3.0) % 2 == 0)
    w_col = (220, 38, 38) if is_flash else (180, 25, 25)
    draw.rounded_rectangle([(aic_x - 160, aic_y - rad_r - 70), (aic_x + 160, aic_y - rad_r - 20)], radius=8, fill=w_col, outline=(255, 255, 255), width=2)
    draw.text((aic_x - 140, aic_y - rad_r - 56), inc.get("cvr_warning", "MASTER WARNING")[:28], font=get_pop_font(20), fill=(255, 255, 255))
    draw.text((aic_x - 145, aic_y - rad_r - 35), inc.get("cvr_sub_warning", "AVIONICS FAULT")[:36], font=get_font_safe(14, mono=True), fill=(255, 230, 230))

    hud_box = [(cx - 460, H - 75), (cx + 460, H - 20)]
    draw.rounded_rectangle(hud_box, radius=8, fill=(15, 23, 42, 230), outline=(0, 180, 216), width=2)
    draw.text((cx - 440, H - 60), inc.get("telemetry", "ALT: 4,000 FT // SINK: -3,200 FPM")[:70], font=get_font_safe(17, mono=True), fill=(0, 240, 255))

    vib_y = int(math.sin(t_sub * 16.0) * 3.0)
    frame.alpha_composite(captain_img, (60, H - captain_img.height - 20 + vib_y))
    frame.alpha_composite(fo_img, (W - fo_img.width - 60, H - fo_img.height - 20 - vib_y))
    draw_pop_title(draw, sub_title)


def render_aviation_maintenance_blunder(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    mechanic_img: Image.Image,
    host_img: Image.Image,
    scene_data: dict,
    inc: dict = None
):
    if not inc:
        inc = resolve_aviation_incident(
            str(scene_data.get("narration", "")) + " " + str(sub_title),
            vehicle_name=str(scene_data.get("vehicle_name", ""))
        )
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=(24, 34, 52), width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=(24, 34, 52), width=1)

    draw.polygon([(0, H - 200), (W, H - 200), (W, H), (0, H)], fill=(18, 26, 40))
    draw.line([(0, H - 200), (W, H - 200)], fill=(0, 180, 216), width=4)

    card_x, card_y, card_w, card_h = 440, 160, 1040, 580
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=16, fill=(15, 23, 42, 245), outline=(239, 68, 68), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 60)], radius=16, fill=(185, 28, 28, 255))
    draw.text((card_x + 30, card_y + 14), inc.get("maint_header", "CRITICAL MAINTENANCE BLUNDER")[:58], font=get_pop_font(22), fill=(255, 255, 255))

    col_w = (card_w - 90) // 2
    box1_x = card_x + 30
    draw.rounded_rectangle([(box1_x, card_y + 80), (box1_x + col_w, card_y + 400)], radius=12, fill=(30, 41, 59), outline=(239, 68, 68), width=2)
    draw.text((box1_x + 20, card_y + 95), inc.get("maint_box1_title", "COMPONENT FAILED")[:28], font=get_pop_font(19), fill=(239, 68, 68))
    draw.text((box1_x + 20, card_y + 135), inc.get("maint_box1_part", "")[:32], font=get_font_safe(15, mono=True), fill=(148, 163, 184))
    draw.text((box1_x + 20, card_y + 175), inc.get("maint_box1_val", "")[:30], font=get_pop_font(19), fill=(234, 179, 8))
    for b_idx, bullet in enumerate(inc.get("maint_box1_bullets", [])):
        b_col = (239, 68, 68) if b_idx == 2 else (226, 232, 240)
        draw.text((box1_x + 20, card_y + 215 + b_idx * 30), bullet[:40], font=get_font_safe(15), fill=b_col)

    box2_x = box1_x + col_w + 30
    draw.rounded_rectangle([(box2_x, card_y + 80), (box2_x + col_w, card_y + 400)], radius=12, fill=(30, 41, 59), outline=(34, 197, 94), width=2)
    draw.text((box2_x + 20, card_y + 95), inc.get("maint_box2_title", "ACTUAL STATE")[:28], font=get_pop_font(19), fill=(34, 197, 94))
    draw.text((box2_x + 20, card_y + 135), inc.get("maint_box2_part", "")[:32], font=get_font_safe(15, mono=True), fill=(148, 163, 184))
    draw.text((box2_x + 20, card_y + 175), inc.get("maint_box2_val", "")[:30], font=get_pop_font(19), fill=(239, 68, 68))
    for b_idx, bullet in enumerate(inc.get("maint_box2_bullets", [])):
        b_col = (239, 68, 68) if b_idx == 2 else (226, 232, 240)
        draw.text((box2_x + 20, card_y + 215 + b_idx * 30), bullet[:40], font=get_font_safe(15), fill=b_col)

    draw.rounded_rectangle([(card_x + 30, card_y + 420), (card_x + card_w - 30, card_y + 550)], radius=12, fill=(24, 34, 52), outline=(234, 179, 8), width=2)
    draw.text((card_x + 50, card_y + 435), inc.get("maint_footer_title", "OFFICIAL AUDIT:")[:58], font=get_pop_font(19), fill=(234, 179, 8))
    draw.text((card_x + 50, card_y + 470), inc.get("maint_footer_main", "")[:58], font=get_pop_font(21), fill=(255, 255, 255))
    draw.text((card_x + 50, card_y + 510), inc.get("maint_footer_sub", "")[:72], font=get_font_safe(15, mono=True), fill=(239, 68, 68))

    stamp_img = get_cached_stamp("FATAL BLUNDER", -10)
    frame.alpha_composite(stamp_img, (card_x + card_w - 380, card_y + 320))

    frame.alpha_composite(mechanic_img, (60, H - mechanic_img.height - 20))
    frame.alpha_composite(host_img, (W - host_img.width - 40, H - host_img.height - 20))
    draw_pop_title(draw, sub_title)


def render_aviation_atc_tower(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    atc_img: Image.Image,
    scene_data: dict,
    inc: dict = None
):
    if not inc:
        inc = resolve_aviation_incident(
            str(scene_data.get("narration", "")) + " " + str(sub_title),
            vehicle_name=str(scene_data.get("vehicle_name", ""))
        )
    horiz_y = H // 2 - 40
    for y in range(0, H, 4):
        ratio = y / H
        draw.rectangle([(0, y), (W, y + 4)], fill=(int(6 + ratio * 8), int(10 + ratio * 14), int(20 + ratio * 20), 255))

    draw.line([(0, horiz_y), (W, horiz_y)], fill=(20, 35, 50), width=1)
    vanish_x = W // 2 - 100
    for offset, p_col in [(-220, (0, 255, 120)), (0, (255, 255, 255)), (220, (0, 255, 120))]:
        for step in range(1, 10):
            lx = int(vanish_x + (offset * (step / 10.0) * 1.8))
            ly = int(horiz_y + (step * 24))
            draw.ellipse([(lx - 2, ly - 2), (lx + 2, ly + 2)], fill=p_col)

    desk_y = H - 240
    draw.polygon([(0, desk_y), (W, desk_y), (W, H), (0, H)], fill=(11, 19, 30))
    draw.line([(0, desk_y), (W, desk_y)], fill=(0, 160, 220), width=3)

    rx, ry, rr = W - 440, H // 2 + 10, 230
    draw.ellipse([(rx - rr, ry - rr), (rx + rr, ry + rr)], fill=(4, 18, 12), outline=(16, 200, 130), width=3)
    for r_step in [55, 110, 165, 220]:
        draw.ellipse([(rx - r_step, ry - r_step), (rx + r_step, ry + r_step)], outline=(16, 180, 120), width=1)
    draw.line([(rx - rr, ry), (rx + rr, ry)], fill=(16, 180, 120), width=1)
    draw.line([(rx, ry - rr), (rx, ry + rr)], fill=(16, 180, 120), width=1)
    sweep_angle = (t_sub * 120.0) % 360.0
    s_rad = math.radians(sweep_angle)
    sx = int(rx + math.cos(s_rad) * rr)
    sy = int(ry + math.sin(s_rad) * rr)
    draw.line([(rx, ry), (sx, sy)], fill=(0, 255, 170), width=3)
    tx, ty = rx - 75, ry + 60
    draw.ellipse([(tx - 6, ty - 6), (tx + 6, ty + 6)], fill=(255, 60, 60))
    draw.text((tx + 12, ty - 18), inc.get("atc_radar_tag", "SQUAWK 7700")[:28], font=get_font_safe(14, bold=True), fill=(255, 60, 60))
    draw.text((tx + 12, ty + 2), inc.get("radar_sub", "EMERGENCY DESCENT")[:28], font=get_font_safe(13, mono=True), fill=(255, 200, 0))

    card_x, card_y, card_w, card_h = 460, 170, 740, 500
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=16, fill=(15, 23, 42, 245), outline=(16, 200, 130), width=3)
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + 55)], radius=16, fill=(16, 140, 90, 255))
    draw.text((card_x + 25, card_y + 14), f"📡 {inc.get('atc_facility', 'AIR TRAFFIC CONTROL')}"[:48], font=get_pop_font(20), fill=(255, 255, 255))

    draw.text((card_x + 30, card_y + 75), f"RADIO TRANSMISSION // {inc.get('location', '')[:40]}:", font=get_pop_font(17), fill=(16, 240, 130))
    wave_y = card_y + 120
    for wx in range(card_x + 30, card_x + card_w - 30, 4):
        amp = math.sin((wx + t_sub * 80) * 0.12) * 12
        draw.line([(wx, wave_y - amp), (wx, wave_y + amp)], fill=(16, 240, 130), width=2)
    draw.ellipse([(card_x + card_w - 80, card_y + 70), (card_x + card_w - 60, card_y + 90)], fill=(16, 240, 130))
    draw.text((card_x + card_w - 55, card_y + 72), "TX", font=get_font_safe(14, bold=True), fill=(16, 240, 130))

    draw.rounded_rectangle([(card_x + 25, card_y + 150), (card_x + card_w - 25, card_y + 340)], radius=12, fill=(24, 34, 52), outline=(239, 68, 68), width=2)
    draw.text((card_x + 35, card_y + 165), 'CVR / ATC RECORDED CALLOUTS:', font=get_font_safe(15, mono=True), fill=(239, 68, 68))
    m1 = inc.get("atc_msg_1", "")
    m2 = inc.get("atc_msg_2", "")
    m3 = inc.get("atc_msg_3", "")
    draw.text((card_x + 35, card_y + 195), m1[:52], font=get_pop_font(19), fill=(255, 255, 255))
    draw.text((card_x + 35, card_y + 235), m2[:52], font=get_pop_font(19), fill=(255, 210, 0))
    draw.text((card_x + 35, card_y + 285), m3[:56], font=get_font_safe(14), fill=(148, 163, 184))

    draw.rounded_rectangle([(card_x + 25, card_y + 355), (card_x + card_w - 25, card_y + 480)], radius=12, fill=(30, 41, 59), outline=(234, 179, 8), width=2)
    draw.text((card_x + 35, card_y + 370), inc.get("dist_info_header", "STATUS:")[:52], font=get_pop_font(18), fill=(234, 179, 8))
    draw.text((card_x + 35, card_y + 400), inc.get("dist_info_main", "")[:48], font=get_pop_font(21), fill=(255, 255, 255))
    draw.text((card_x + 35, card_y + 440), inc.get("dist_info_sub", "")[:58], font=get_font_safe(14, mono=True), fill=(239, 68, 68))

    frame.alpha_composite(atc_img, (30, H - atc_img.height - 20))
    draw_pop_title(draw, sub_title)


def render_aviation_investigation_fdr(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    ntsb_img: Image.Image,
    scene_data: dict,
    inc: dict = None
):
    if not inc:
        inc = resolve_aviation_incident(
            str(scene_data.get("narration", "")) + " " + str(sub_title),
            vehicle_name=str(scene_data.get("vehicle_name", ""))
        )
    for y in range(0, H, 4):
        ratio = y / H
        draw.rectangle([(0, y), (W, y + 4)], fill=(int(8 + ratio * 8), int(12 + ratio * 12), int(20 + ratio * 16), 255))

    draw.polygon([(480, 0), (620, 0), (740, H - 200), (320, H - 200)], fill=(16, 28, 42, 255))

    table_y = H - 230
    draw.polygon([(0, table_y), (W, table_y), (W, H), (0, H)], fill=(15, 22, 32))
    draw.line([(0, table_y), (W, table_y)], fill=(40, 60, 85), width=3)

    box_x, box_y, box_w, box_h = 340, H - 320, 180, 110
    draw.rectangle([(box_x, box_y), (box_x + box_w, box_y + box_h)], fill=(249, 115, 22), outline=(255, 255, 255), width=2)
    draw.rectangle([(box_x + 8, box_y + 8), (box_x + box_w - 8, box_y + box_h - 8)], fill=(234, 88, 12))
    draw.text((box_x + 22, box_y + 24), "FLIGHT RECORDER", font=get_font_safe(14, bold=True), fill=(255, 255, 255))
    draw.text((box_x + 22, box_y + 48), "DO NOT OPEN", font=get_font_safe(13, bold=True), fill=(255, 255, 255))
    draw.rectangle([(box_x + box_w - 34, box_y + 16), (box_x + box_w - 12, box_y + 80)], fill=(220, 220, 220), outline=(50, 50, 50), width=1)

    mag_cx, mag_cy, mag_r = 440, H - 275, 42
    draw.ellipse([(mag_cx - mag_r, mag_cy - mag_r), (mag_cx + mag_r, mag_cy + mag_r)], outline=(255, 215, 0), width=4)
    draw.line([(mag_cx + int(mag_r * 0.7), mag_cy + int(mag_r * 0.7)), (mag_cx + mag_r + 30, mag_cy + mag_r + 30)], fill=(180, 140, 20), width=7)

    panel_x, panel_y, panel_w, panel_h = 580, 160, 1260, 750
    draw.rounded_rectangle([(panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h)], radius=16, fill=(12, 19, 32, 245), outline=(0, 200, 255), width=2)
    draw.rounded_rectangle([(panel_x, panel_y), (panel_x + panel_w, panel_y + 60)], radius=16, fill=(0, 140, 190, 255))
    draw.text((panel_x + 25, panel_y + 16), inc.get("investigation_agency", "OFFICIAL ACCIDENT INVESTIGATION DOSSIER")[:62], font=get_pop_font(21), fill=(255, 255, 255))

    draw.rounded_rectangle([(panel_x + panel_w - 210, panel_y + 12), (panel_x + panel_w - 20, panel_y + 48)], radius=6, fill=(220, 38, 38))
    draw.text((panel_x + panel_w - 195, panel_y + 20), "OFFICIAL FINDINGS", font=get_font_safe(13, bold=True), fill=(255, 255, 255))

    draw.text((panel_x + 35, panel_y + 85), "PRIMARY PROBABLE CAUSE:", font=get_pop_font(20), fill=(255, 200, 0))
    draw.text((panel_x + 35, panel_y + 120), inc.get("probable_cause", "")[:75], font=get_pop_font(22), fill=(255, 255, 255))
    draw.text((panel_x + 35, panel_y + 160), inc.get("cause_sub", "")[:85], font=get_font_safe(16, mono=True), fill=(239, 68, 68))

    factors = inc.get("findings", [])
    for idx, (head, desc) in enumerate(factors[:4]):
        cy = panel_y + 210 + idx * 115
        draw.rounded_rectangle([(panel_x + 35, cy), (panel_x + panel_w - 35, cy + 95)], radius=10, fill=(20, 29, 46), outline=(0, 180, 216), width=2)
        draw.text((panel_x + 55, cy + 16), head[:60], font=get_pop_font(18), fill=(0, 220, 255))
        draw.text((panel_x + 55, cy + 50), desc[:85], font=get_font_safe(15), fill=(226, 232, 240))

    stamp_img = get_cached_stamp("FINAL REPORT", -8)
    frame.alpha_composite(stamp_img, (panel_x + panel_w - 360, panel_y + 160))

    frame.alpha_composite(ntsb_img, (40, H - ntsb_img.height - 20))
    draw_pop_title(draw, sub_title)



# ─────────────────────────────────────────────────────────────────────────────
# BESPOKE AVIATION RECONSTRUCTION ENGINE: 5 NEW BROADCAST ARCHETYPES
# ─────────────────────────────────────────────────────────────────────────────

def render_aviation_runway_map(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    scene_data: dict = None,
    inc: dict = None
):
    if not inc:
        inc = resolve_aviation_incident(sub_title)
    
    # Airfield tarmac backdrop
    draw.rectangle([(0, 0), (W, H)], fill=(11, 16, 26))

    # Grid
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=(20, 30, 48), width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=(20, 30, 48), width=1)

    # Compass Rose / North Indicator
    comp_x, comp_y = W - 140, 110
    draw.ellipse([(comp_x - 45, comp_y - 45), (comp_x + 45, comp_y + 45)], outline=(56, 189, 248), width=2)
    draw.polygon([(comp_x, comp_y - 40), (comp_x - 12, comp_y), (comp_x + 12, comp_y)], fill=(239, 68, 68))
    draw.polygon([(comp_x, comp_y + 40), (comp_x - 12, comp_y), (comp_x + 12, comp_y)], fill=(148, 163, 184))
    draw.text((comp_x - 7, comp_y - 65), "N", font=get_pop_font(18), fill=(239, 68, 68))

    # Airport Header Badge
    draw.rounded_rectangle([(60, 120), (780, 230)], radius=12, fill=(15, 23, 42, 230), outline=(56, 189, 248), width=2)
    draw.text((85, 138), f"{inc.get('location', 'AIRPORT RUNWAY GEOMETRY')[:48].upper()}", font=get_pop_font(21), fill=(56, 189, 248))
    draw.text((85, 172), f"• Runway Profile: {inc.get('atc_radar_tag', 'ACTIVE RUNWAY')[:55]}", font=get_font_safe(16), fill=(226, 232, 240))
    draw.text((85, 196), f"• Surface Advisory: {inc.get('radar_sub', 'LOW VISIBILITY GROUND TRAFFIC')[:55]}", font=get_font_safe(16), fill=(234, 179, 8))

    # Main Runway Strip
    r_left, r_right = 160, W - 160
    r_top, r_bot = 480, 600
    r_mid = (r_top + r_bot) // 2

    draw.rectangle([(r_left, r_top), (r_right, r_bot)], fill=(24, 30, 42), outline=(100, 116, 139), width=3)

    # Threshold Zebra Stripes
    for i in range(12):
        draw.rectangle([(r_left + 15, r_top + 10 + i * 9), (r_left + 65, r_top + 16 + i * 9)], fill=(240, 240, 240))
        draw.rectangle([(r_right - 65, r_top + 10 + i * 9), (r_right - 15, r_top + 16 + i * 9)], fill=(240, 240, 240))

    r_num_1 = "12" if inc.get("key") == "tenerife" else ("36L" if inc.get("key") == "spanair_5022" else "27R")
    r_num_2 = "30" if inc.get("key") == "tenerife" else ("18R" if inc.get("key") == "spanair_5022" else "09L")
    draw.text((r_left + 85, r_mid - 25), r_num_1, font=get_pop_font(40), fill=(255, 255, 255))
    draw.text((r_right - 145, r_mid - 25), r_num_2, font=get_pop_font(40), fill=(255, 255, 255))

    for cx in range(r_left + 160, r_right - 160, 70):
        draw.line([(cx, r_mid), (cx + 40, r_mid)], fill=(255, 255, 255), width=4)

    # Turnaround loop
    pad_cx, pad_cy = r_right + 30, r_mid
    draw.ellipse([(pad_cx - 65, pad_cy - 85), (pad_cx + 65, pad_cy + 85)], fill=(24, 30, 42), outline=(100, 116, 139), width=3)
    draw.text((pad_cx - 50, pad_cy - 105), "180° LOOP", font=get_font_safe(14, bold=True), fill=(56, 189, 248))

    # Parallel Taxiway
    tax_top, tax_bot = 730, 800
    draw.rectangle([(r_left, tax_top), (r_right, tax_bot)], fill=(18, 24, 36), outline=(71, 85, 105), width=2)
    draw.text((r_left + 40, tax_top + 22), "PARALLEL TAXIWAY: BLOCKED BY DIVERTED AIRCRAFT (PARKED JETS)", font=get_font_safe(16, bold=True), fill=(234, 179, 8))

    taxiways = [
        ("C-1", r_left + 260, False),
        ("C-2", r_left + 520, False),
        ("C-3 (135°)", r_left + 820, True),
        ("C-4 (45° TARGET)", r_left + 1140, False),
    ]
    for tag, tx, is_c3 in taxiways:
        if is_c3:
            draw.polygon([(tx - 35, r_bot), (tx + 35, r_bot), (tx + 10, tax_top), (tx - 60, tax_top)], fill=(20, 26, 38), outline=(239, 68, 68), width=2)
            draw.text((tx - 70, tax_top - 42), "❌ C-3 (MISSED 135° TURN)", font=get_font_safe(15, bold=True), fill=(239, 68, 68))
        elif "C-4" in tag:
            draw.polygon([(tx - 35, r_bot), (tx + 35, r_bot), (tx + 75, tax_top), (tx + 5, tax_top)], fill=(20, 26, 38), outline=(34, 197, 94), width=2)
            draw.text((tx - 40, tax_top - 42), "🎯 C-4 (PAN AM TARGET)", font=get_font_safe(15, bold=True), fill=(34, 197, 94))
        else:
            draw.rectangle([(tx - 30, r_bot), (tx + 30, tax_top)], fill=(18, 24, 36), outline=(71, 85, 105), width=2)
            draw.text((tx - 15, tax_top - 35), tag, font=get_font_safe(15), fill=(148, 163, 184))

    # Moving markers
    paa_x = r_left + 940 + int(math.sin(t_sub * 1.5) * 20)
    paa_y = r_mid
    draw.ellipse([(paa_x - 22, paa_y - 22), (paa_x + 22, paa_y + 22)], fill=(234, 179, 8), outline=(255, 255, 255), width=3)
    draw.polygon([(paa_x - 30, paa_y), (paa_x - 10, paa_y - 14), (paa_x - 10, paa_y + 14)], fill=(234, 179, 8))
    draw.text((paa_x - 110, paa_y - 58), "PAA 1736 (CLIPPER)", font=get_pop_font(18), fill=(234, 179, 8))
    draw.text((paa_x - 110, paa_y - 36), "Taxiing down runway toward C-4", font=get_font_safe(14), fill=(255, 255, 255))

    klm_dist = min(380, int(t_sub * 85))
    klm_x = (r_right - 60) - klm_dist
    klm_y = r_mid
    draw.ellipse([(klm_x - 24, klm_y - 24), (klm_x + 24, klm_y + 24)], fill=(239, 68, 68), outline=(255, 255, 255), width=3)
    draw.polygon([(klm_x - 32, klm_y), (klm_x - 12, klm_y - 16), (klm_x - 12, klm_y + 16)], fill=(239, 68, 68))
    draw.line([(klm_x + 24, klm_y), (min(r_right, klm_x + 140), klm_y)], fill=(239, 68, 68), width=5)
    draw.text((klm_x - 40, klm_y + 35), "KLM 4805 (TAKEOFF ROLL)", font=get_pop_font(18), fill=(239, 68, 68))
    draw.text((klm_x - 40, klm_y + 57), f"Speed: {110 + int(t_sub * 12)} KT // Blind in Fog", font=get_font_safe(14), fill=(255, 255, 255))

    coll_x = r_left + 990
    p_rad = int(35 + abs(math.sin(t_sub * 6.0)) * 25.0)
    draw.ellipse([(coll_x - p_rad, r_mid - p_rad), (coll_x + p_rad, r_mid + p_rad)], outline=(239, 68, 68), width=3)
    draw.text((coll_x - 90, r_mid + 60), "⚠️ COLLISION POINT", font=get_pop_font(18), fill=(239, 68, 68))

    # Fog overlay
    fog_alpha = int(70 + math.sin(t_sub * 2.0) * 25)
    fog_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f_draw = ImageDraw.Draw(fog_layer)
    for fy in range(r_top - 60, r_bot + 60, 40):
        fx_off = int(math.sin(t_sub + fy * 0.05) * 60)
        f_draw.ellipse([(r_left + fx_off, fy), (r_right + fx_off, fy + 80)], fill=(220, 230, 245, fog_alpha))
    frame.alpha_composite(fog_layer)

    draw.rounded_rectangle([(r_left, H - 110), (r_right, H - 40)], radius=10, fill=(15, 23, 42, 245), outline=(56, 189, 248), width=2)
    draw.text((r_left + 35, H - 95), f"{inc.get('atc_facility', 'TOWER')} // VISIBILITY ZERO: CONTROLLERS CANNOT SEE RUNWAY", font=get_pop_font(18), fill=(234, 179, 8))
    draw.text((r_left + 35, H - 70), "Both aircraft unaware of mutual proximity on single active runway due to dense cloud bank", font=get_font_safe(15), fill=(255, 255, 255))

    draw_pop_title(draw, sub_title)


def render_aviation_aircraft_profile(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    scene_data: dict = None,
    inc: dict = None
):
    if not inc:
        inc = resolve_aviation_incident(sub_title)
        
    draw.rectangle([(0, 0), (W, H)], fill=(10, 16, 28))

    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill=(18, 28, 48), width=1)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=(18, 28, 48), width=1)

    bx, by, bw, bh = 80, 120, W - 160, 880
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=16, fill=(13, 20, 36, 240), outline=(56, 189, 248), width=2)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=16, fill=(15, 76, 129))
    draw.text((bx + 35, by + 16), f"AIRCRAFT PROFILE & TECHNICAL ANATOMY // {inc.get('aircraft', 'COMMERCIAL AIRLINER')[:50].upper()}", font=get_pop_font(23), fill=(255, 255, 255))

    cx, cy = W // 2 - 40, by + 260
    nose_x = cx - 440
    tail_x = cx + 440
    fuse_y = cy
    
    # Check if 747 (upper deck hump) or twin-jet/T-tail
    is_747 = "747" in inc.get("aircraft", "")
    is_ttail = any(w in inc.get("aircraft", "").upper() for w in ["MD-8", "DC-9", "727"])
    
    if is_747:
        fuse_points = [
            (nose_x, fuse_y + 10),
            (nose_x + 40, fuse_y - 25),
            (nose_x + 110, fuse_y - 65),
            (nose_x + 160, fuse_y - 75),
            (nose_x + 290, fuse_y - 75),
            (nose_x + 360, fuse_y - 45),
            (tail_x - 120, fuse_y - 45),
            (tail_x, fuse_y - 200),
            (tail_x + 25, fuse_y - 190),
            (tail_x - 30, fuse_y + 10),
            (tail_x - 60, fuse_y + 25),
            (nose_x + 80, fuse_y + 25),
            (nose_x + 20, fuse_y + 18),
        ]
    elif is_ttail:
        fuse_points = [
            (nose_x, fuse_y + 10),
            (nose_x + 50, fuse_y - 30),
            (tail_x - 120, fuse_y - 30),
            (tail_x - 40, fuse_y - 170),
            (tail_x + 20, fuse_y - 170),
            (tail_x - 10, fuse_y + 10),
            (nose_x + 60, fuse_y + 20),
        ]
    else:
        fuse_points = [
            (nose_x, fuse_y + 10),
            (nose_x + 50, fuse_y - 35),
            (tail_x - 100, fuse_y - 35),
            (tail_x, fuse_y - 180),
            (tail_x + 25, fuse_y - 170),
            (tail_x - 20, fuse_y + 10),
            (nose_x + 60, fuse_y + 20),
        ]

    draw.polygon(fuse_points, fill=(28, 44, 72), outline=(56, 189, 248), width=2)

    wing_points = [
        (cx - 100, fuse_y + 10),
        (cx + 80, fuse_y + 90),
        (cx + 140, fuse_y + 80),
        (cx - 20, fuse_y + 5),
    ]
    draw.polygon(wing_points, fill=(35, 55, 90), outline=(56, 189, 248), width=2)

    for eng_x, eng_y in [(cx - 30, fuse_y + 60), (cx + 50, fuse_y + 95)]:
        draw.ellipse([(eng_x - 35, eng_y - 15), (eng_x + 35, eng_y + 15)], fill=(15, 23, 42), outline=(234, 179, 8), width=2)
        draw.text((eng_x - 22, eng_y - 8), "ENG", font=get_font_safe(12, bold=True), fill=(234, 179, 8))

    for wx in range(nose_x + 90, tail_x - 120, 22):
        draw.rectangle([(wx, fuse_y - 25), (wx + 11, fuse_y - 14)], fill=(226, 232, 240))

    draw.line([(nose_x, cy + 130), (tail_x, cy + 130)], fill=(148, 163, 184), width=2)
    draw.text((cx - 140, cy + 140), f"AIRCRAFT SPECIFICATION: {inc.get('aircraft', 'COMMERCIAL FLIGHT')}", font=get_pop_font(16), fill=(148, 163, 184))

    # 4 Cards
    if inc.get("key") == "tenerife":
        cards = [
            ("AIRCRAFT DISPLACEMENT", "MTOW: 377,800 KG", "Combined Weight: 750+ Tons", "583 Fatalities (Deadliest in History)", (56, 189, 248)),
            ("FATAL FUEL DECISION", "KLM TOPPED UP 55,000L", "Added +50 Tons Fuel at Tenerife!", "Made Plane Too Heavy to Clear Pan Am", (239, 68, 68)),
            ("PROPULSION & THRUST", "4x P&W JT9D-7A TURBOFANS", "Takeoff Thrust: 43,500 LBF Each", "Engines Tore Pan Am Upper Deck", (234, 179, 8)),
            ("ROTATION DYNAMICS", "VR: 154 KNOTS IN FOG", "20-Meter Tail Strike Asphalt Scrape", "Failed to Gain Enough Climb Altitude", (239, 68, 68)),
        ]
    else:
        cards = [
            ("AIRCRAFT SPECIFICATION", inc.get("aircraft", "Airliner")[:24], f"Operator: {inc.get('operator', 'Airlines')[:24]}", f"Squawk: {inc.get('squawk', '7700')}", (56, 189, 248)),
            ("CRITICAL PARAMETER", inc.get("cvr_warning", "Warning")[:24], inc.get("dist_info_main", "Primary Event")[:32], "Systemic Investigation", (239, 68, 68)),
            ("PROPULSION & SYSTEMS", inc.get("maint_box1_title", "Avionics")[:24], inc.get("maint_box1_val", "Component Fault")[:32], "Emergency Checklist Executed", (234, 179, 8)),
            ("OFFICIAL AUDIT", inc.get("investigation_agency", "Safety Board")[:24], inc.get("probable_cause", "Probable Cause")[:32], "Regulatory Directives Enforced", (34, 197, 94)),
        ]
        
    card_w = (bw - 100) // 4
    for i, (hdr, val, b1, b2, col) in enumerate(cards):
        c_x = bx + 40 + i * (card_w + 20)
        c_y = by + 470
        draw.rounded_rectangle([(c_x, c_y), (c_x + card_w, c_y + 350)], radius=12, fill=(15, 23, 42), outline=col, width=2)
        draw.text((c_x + 20, c_y + 25), hdr, font=get_pop_font(16), fill=col)
        draw.text((c_x + 20, c_y + 65), val, font=get_pop_font(18), fill=(255, 255, 255))
        draw.text((c_x + 20, c_y + 120), f"• {b1}", font=get_font_safe(15), fill=(226, 232, 240))
        draw.text((c_x + 20, c_y + 185), f"• {b2}", font=get_font_safe(15), fill=col)

    draw_pop_title(draw, sub_title)


def render_aviation_cvr_transcript(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    scene_data: dict = None,
    inc: dict = None
):
    if not inc:
        inc = resolve_aviation_incident(sub_title)

    draw.rectangle([(0, 0), (W, H)], fill=(12, 17, 29))

    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=(18, 25, 40), width=1)

    bx, by, bw, bh = 80, 110, W - 160, 900
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=16, fill=(15, 23, 42, 250), outline=(56, 189, 248), width=2)

    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=16, fill=(17, 24, 39))
    draw.text((bx + 35, by + 18), f"COCKPIT VOICE RECORDER (CVR) // MULTI-CHANNEL AUDIO DECODE // {inc.get('flight_no', '')}", font=get_pop_font(22), fill=(56, 189, 248))
    
    rec_flash = (int(t_sub * 3.0) % 2 == 0)
    rec_col = (239, 68, 68) if rec_flash else (100, 30, 30)
    draw.ellipse([(bx + bw - 220, by + 22), (bx + bw - 195, by + 47)], fill=rec_col)
    draw.text((bx + bw - 180, by + 20), "● REC CVR", font=get_pop_font(20), fill=rec_col)

    wave_y = by + 85
    draw.rectangle([(bx + 30, wave_y), (bx + bw - 30, wave_y + 100)], fill=(8, 14, 26), outline=(30, 41, 59), width=2)
    draw.line([(bx + 30, wave_y + 50), (bx + bw - 30, wave_y + 50)], fill=(51, 65, 85), width=1)
    for wx in range(bx + 40, bx + bw - 40, 6):
        amp = math.sin((wx * 0.04) + (t_sub * 12.0)) * 32.0 * math.sin(wx * 0.01)
        w_col = (239, 68, 68) if (t_sub > 1.0 and abs(amp) > 18) else (56, 189, 248)
        draw.line([(wx, wave_y + 50 - int(amp)), (wx, wave_y + 50 + int(amp))], fill=w_col, width=3)
    draw.text((bx + 50, wave_y + 12), f"{inc.get('atc_facility', 'VHF FREQUENCY')} // AUDIO SPECTRUM ANALYZER", font=get_font_safe(14, bold=True), fill=(148, 163, 184))

    dialogues = inc.get("cvr_dialogues", [
        ("00:00:15", "PILOT", '"Executing emergency checklist, monitoring flight attitude."', (56, 189, 248), (255, 255, 255)),
        ("00:00:28", "COPILOT", '"Instruments cross-checked, system warning active."', (234, 179, 8), (255, 255, 255)),
        ("00:00:45", "TOWER", '"Radar contact established, verify intentions."', (56, 189, 248), (255, 255, 255)),
        ("00:00:58", "CVR", '[AUDIBLE WARNING TONES CONFIRMED ON RECORDING]', (239, 68, 68), (255, 220, 220))
    ])

    for i, (t_stamp, spk, text, s_col, t_col) in enumerate(dialogues[:5]):
        row_y = wave_y + 120 + i * 85
        draw.rounded_rectangle([(bx + 30, row_y), (bx + bw - 30, row_y + 75)], radius=8, fill=(18, 26, 44), outline=(30, 41, 59), width=1)
        draw.rectangle([(bx + 30, row_y), (bx + 140, row_y + 75)], fill=(24, 34, 58))
        draw.text((bx + 45, row_y + 26), t_stamp, font=get_pop_font(18), fill=(148, 163, 184))
        draw.text((bx + 160, row_y + 12), spk, font=get_pop_font(16), fill=s_col)
        draw.text((bx + 160, row_y + 40), text[:80], font=get_font_safe(16), fill=t_col)

    # Alert Box
    het_y = by + bh - 130
    h_flash = (int(t_sub * 4.0) % 2 == 0)
    h_bg = (185, 28, 28) if h_flash else (120, 20, 20)
    draw.rounded_rectangle([(bx + 30, het_y), (bx + bw - 30, het_y + 105)], radius=10, fill=h_bg, outline=(255, 255, 255), width=3)
    draw.text((bx + 55, het_y + 18), f"⚠️ CVR PROTOCOL // {inc.get('cvr_warning', 'EMERGENCY PROTOCOL')[:55]}", font=get_pop_font(21), fill=(255, 255, 255))
    draw.text((bx + 55, het_y + 54), inc.get("cvr_sub_warning", "Official CVR audio recording registered vital callouts.")[:85], font=get_font_safe(16), fill=(255, 230, 230))
    draw.text((bx + 55, het_y + 76), inc.get("telemetry", "Cockpit telemetry confirmed flight parameters at moment of event.")[:90], font=get_font_safe(16, bold=True), fill=(255, 255, 255))

    draw_pop_title(draw, sub_title)


def render_aviation_crm_decision_tree(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    scene_data: dict = None,
    inc: dict = None
):
    if not inc:
        inc = resolve_aviation_incident(sub_title)

    draw.rectangle([(0, 0), (W, H)], fill=(11, 16, 28))

    bx, by, bw, bh = 80, 110, W - 160, 900
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=16, fill=(15, 23, 42, 240), outline=(234, 179, 8), width=2)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=16, fill=(120, 53, 15))
    draw.text((bx + 35, by + 18), f"HUMAN FACTORS & SYSTEMIC ROOT CAUSE // {inc.get('flight_no', '')}", font=get_pop_font(23), fill=(255, 255, 255))

    steps = inc.get("crm_nodes", [
        ("1. SYSTEM DEVIATION", "Initial Latent Anomaly", "Unscheduled flight conditions increased operational stress on flight crew.", (234, 179, 8)),
        ("2. COGNITIVE DEMAND", "High-Stress Workload", "Multiple alarms and conflicting data complicated emergency decision tree.", (239, 68, 68)),
        ("3. CREW COORDINATION", "Communication & Crosscheck", "Flight crew attempted manual recovery while troubleshooting degraded systems.", (56, 189, 248)),
        ("4. SYSTEMIC REFORM", "Global Safety Mandates", "Accident investigation led to binding international pilot training updates.", (34, 197, 94))
    ])

    card_h = 140
    for i, (title, sub, detail, col) in enumerate(steps[:4]):
        s_y = by + 95 + i * (card_h + 40)
        draw.rounded_rectangle([(bx + 80, s_y), (bx + bw - 80, s_y + card_h)], radius=12, fill=(20, 28, 48), outline=col, width=3)
        draw.ellipse([(bx + 110, s_y + 25), (bx + 160, s_y + 75)], fill=col)
        draw.text((bx + 128, s_y + 35), str(i + 1), font=get_pop_font(28), fill=(15, 23, 42))

        draw.text((bx + 185, s_y + 24), title, font=get_pop_font(22), fill=col)
        draw.text((bx + 185, s_y + 58), sub, font=get_font_safe(18, bold=True), fill=(255, 255, 255))
        draw.text((bx + 185, s_y + 92), detail[:95], font=get_font_safe(16), fill=(203, 213, 225))

        if i < len(steps) - 1:
            arr_y = s_y + card_h + 12
            draw.polygon([(W // 2 - 15, arr_y), (W // 2 + 15, arr_y), (W // 2, arr_y + 18)], fill=col)

    draw_pop_title(draw, sub_title)


def render_aviation_approach_chart(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    scene_data: dict = None,
    inc: dict = None
):
    if not inc:
        inc = resolve_aviation_incident(sub_title)

    draw.rectangle([(0, 0), (W, H)], fill=(10, 22, 38))

    for x in range(0, W, 100):
        draw.line([(x, 0), (x, H)], fill=(16, 35, 60), width=1)
    for y in range(0, H, 100):
        draw.line([(0, y), (W, y)], fill=(16, 35, 60), width=1)

    bx, by, bw, bh = 80, 110, W - 160, 900
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=16, fill=(12, 25, 45, 240), outline=(56, 189, 248), width=2)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=16, fill=(14, 116, 144))
    draw.text((bx + 35, by + 18), f"AERONAUTICAL ROUTE CHART & REGIONAL AIRSPACE // {inc.get('location', 'TERMINAL AIRSPACE')[:48].upper()}", font=get_pop_font(21), fill=(255, 255, 255))

    lp_cx, lp_cy = W // 2 + 350, by + 460
    draw.ellipse([(lp_cx - 160, lp_cy - 120), (lp_cx + 160, lp_cy + 120)], fill=(30, 48, 70), outline=(56, 189, 248), width=2)
    draw.text((lp_cx - 80, lp_cy - 30), "DEPARTURE SECTOR", font=get_pop_font(20), fill=(255, 255, 255))
    draw.text((lp_cx - 110, lp_cy + 5), f"{inc.get('atc_facility', 'DEPARTURE CONTROL')[:26]}", font=get_font_safe(15, bold=True), fill=(234, 179, 8))
    draw.text((lp_cx - 120, lp_cy + 30), f"RADAR TAG: {inc.get('atc_radar_tag', 'SQUAWK 7000')[:26]}", font=get_font_safe(14, bold=True), fill=(239, 68, 68))

    tnf_cx, tnf_cy = W // 2 - 350, by + 420
    draw.ellipse([(tnf_cx - 200, tnf_cy - 140), (tnf_cx + 200, tnf_cy + 140)], fill=(30, 48, 70), outline=(56, 189, 248), width=2)
    draw.text((tnf_cx - 70, tnf_cy - 60), "DESTINATION", font=get_pop_font(22), fill=(255, 255, 255))
    draw.text((tnf_cx - 130, tnf_cy - 20), f"{inc.get('location', 'TERMINAL AREA')[:28]}", font=get_pop_font(18), fill=(56, 189, 248))
    draw.text((tnf_cx - 140, tnf_cy + 12), f"• Squawk Code: {inc.get('squawk', '7700')}", font=get_font_safe(14), fill=(203, 213, 225))
    draw.text((tnf_cx - 140, tnf_cy + 35), f"• Telemetry: {inc.get('telemetry', 'FLIGHT LEVEL')[:35]}", font=get_font_safe(14, bold=True), fill=(239, 68, 68))
    draw.text((tnf_cx - 140, tnf_cy + 58), f"• Operator: {inc.get('operator', 'COMMERCIAL')[:30]}", font=get_font_safe(14), fill=(226, 232, 240))

    draw.line([(lp_cx - 160, lp_cy - 40), (tnf_cx + 180, tnf_cy - 10)], fill=(239, 68, 68), width=4)
    p_frac = (t_sub * 0.4) % 1.0
    px = int((lp_cx - 160) * (1.0 - p_frac) + (tnf_cx + 180) * p_frac)
    py = int((lp_cy - 40) * (1.0 - p_frac) + (tnf_cy - 10) * p_frac)
    draw.ellipse([(px - 10, py - 10), (px + 10, py + 10)], fill=(255, 255, 255), outline=(239, 68, 68), width=3)
    draw.text(((lp_cx + tnf_cx) // 2 - 120, (lp_cy + tnf_cy) // 2 - 70), "REGIONAL FLIGHT CORRIDOR", font=get_pop_font(16), fill=(234, 179, 8))

    draw.rounded_rectangle([(bx + 40, by + bh - 120), (bx + bw - 40, by + bh - 35)], radius=10, fill=(15, 23, 42, 230), outline=(56, 189, 248), width=1)
    draw.text((bx + 60, by + bh - 105), f"RADIO NAVAIDS: {inc.get('atc_facility', 'CONTROL FREQUENCY')} // IFR CORRIDOR MONITORING", font=get_font_safe(16, bold=True), fill=(56, 189, 248))
    draw.text((bx + 60, by + bh - 78), f"Flight tracking data recorded by civil aviation oversight authorities // {inc.get('flight_no', '')}", font=get_font_safe(15), fill=(226, 232, 240))

    draw_pop_title(draw, sub_title)


def render_aviation_historical_archive(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    t_sub: float,
    sub_title: str,
    scene_data: dict = None,
    inc: dict = None,
    photo_tuple: tuple = None
):
    if not inc:
        inc = resolve_aviation_incident(sub_title)

    draw.rectangle([(0, 0), (W, H)], fill=(8, 13, 22))
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=(15, 23, 40), width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=(15, 23, 40), width=1)

    bx, by, bw, bh = 80, 100, W - 160, 920
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=16, fill=(12, 18, 30, 240), outline=(56, 189, 248), width=2)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 65)], radius=16, fill=(14, 116, 144))
    draw.text((bx + 35, by + 18), f"HISTORICAL ARCHIVE & EVIDENCE // {inc.get('aircraft', 'OFFICIAL AIR SAFETY RECORD').upper()}", font=get_pop_font(21), fill=(255, 255, 255))
    draw.text((bx + bw - 380, by + 22), "DECLASSIFIED DOCUMENTARY ASSET", font=get_font_safe(15, bold=True), fill=(234, 179, 8))

    pv_x, pv_y, pv_w, pv_h = bx + 50, by + 90, bw - 100, 640
    photo_drawn = False

    photo_path = None
    photo_caption = ""
    photo_sub = ""
    if photo_tuple:
        if isinstance(photo_tuple, (tuple, list)):
            photo_path = photo_tuple[0]
            if len(photo_tuple) > 1:
                photo_caption = str(photo_tuple[1])
            if len(photo_tuple) > 2:
                photo_sub = str(photo_tuple[2])
        elif isinstance(photo_tuple, (str, Path)):
            photo_path = photo_tuple

    if photo_path and Path(photo_path).is_file():
        try:
            with Image.open(photo_path) as im:
                p_img = im.convert("RGBA")
                zoom = 1.0 + min(0.08, t_sub * 0.015)
                img_aspect = p_img.width / p_img.height
                tgt_aspect = pv_w / pv_h
                if img_aspect > tgt_aspect:
                    crop_w = int(p_img.height * tgt_aspect)
                    crop_x = (p_img.width - crop_w) // 2
                    cropped = p_img.crop((crop_x, 0, crop_x + crop_w, p_img.height))
                else:
                    crop_h = int(p_img.width / tgt_aspect)
                    crop_y = (p_img.height - crop_h) // 2
                    cropped = p_img.crop((0, crop_y, p_img.width, crop_y + crop_h))

                scaled = cropped.resize((pv_w, pv_h), Image.Resampling.LANCZOS)
                frame.alpha_composite(scaled, (pv_x, pv_y))
                photo_drawn = True
        except Exception:
            photo_drawn = False

    if not photo_drawn:
        draw.rectangle([(pv_x, pv_y), (pv_x + pv_w, pv_y + pv_h)], fill=(15, 23, 42), outline=(30, 41, 59), width=2)
        for gx in range(pv_x, pv_x + pv_w, 40):
            draw.line([(gx, pv_y), (gx, pv_y + pv_h)], fill=(24, 34, 58), width=1)
        for gy in range(pv_y, pv_y + pv_h, 40):
            draw.line([(pv_x, gy), (pv_x + pv_w, gy)], fill=(24, 34, 58), width=1)
        cx, cy = pv_x + pv_w // 2, pv_y + pv_h // 2
        draw.ellipse([(cx - 380, cy - 35), (cx + 380, cy + 35)], fill=(30, 58, 138), outline=(56, 189, 248), width=3)
        draw.polygon([(cx - 80, cy), (cx - 240, cy - 220), (cx - 160, cy - 220), (cx + 60, cy)], fill=(30, 58, 138), outline=(56, 189, 248))
        draw.polygon([(cx - 80, cy), (cx - 240, cy + 220), (cx - 160, cy + 220), (cx + 60, cy)], fill=(30, 58, 138), outline=(56, 189, 248))
        draw.polygon([(cx - 360, cy), (cx - 420, cy - 110), (cx - 380, cy - 110), (cx - 310, cy)], fill=(30, 58, 138), outline=(56, 189, 248))
        draw.text((cx - 220, cy - 260), f"AIRCRAFT BLUEPRINT // {inc.get('aircraft', 'COMMERCIAL AIRLINER').upper()}", font=get_pop_font(22), fill=(56, 189, 248))
        draw.text((cx - 180, cy + 245), f"OPERATOR: {inc.get('operator', '').upper()} // REG: {inc.get('flight_no', '')}", font=get_font_safe(16, bold=True), fill=(234, 179, 8))

    cw = 24
    for cx_corner, cy_corner, dx, dy in [
        (pv_x, pv_y, 1, 1),
        (pv_x + pv_w, pv_y, -1, 1),
        (pv_x, pv_y + pv_h, 1, -1),
        (pv_x + pv_w, pv_y + pv_h, -1, -1)
    ]:
        draw.line([(cx_corner, cy_corner), (cx_corner + dx * cw, cy_corner)], fill=(56, 189, 248), width=3)
        draw.line([(cx_corner, cy_corner), (cx_corner + dy * cw, cy_corner)], fill=(56, 189, 248), width=3)

    cap_box_y = pv_y + pv_h - 75
    draw.rectangle([(pv_x, cap_box_y), (pv_x + pv_w, pv_y + pv_h)], fill=(10, 15, 26, 210))
    draw.line([(pv_x, cap_box_y), (pv_x + pv_w, cap_box_y)], fill=(56, 189, 248), width=2)
    disp_caption = photo_caption if photo_caption else f"ARCHIVAL RECORD: {inc.get('aircraft', '')} // {inc.get('operator', '')}"
    disp_sub = photo_sub if photo_sub else f"HISTORICAL PHOTOGRAPH // {inc.get('location', '')}"
    draw.text((pv_x + 25, cap_box_y + 12), f"📷 {disp_caption[:70]}", font=get_pop_font(18), fill=(255, 255, 255))
    draw.text((pv_x + 25, cap_box_y + 42), f"SOURCE: WIKIMEDIA COMMONS & OFFICIAL ACCIDENT DOSSIER // {disp_sub[:65]}", font=get_font_safe(14), fill=(203, 213, 225))
    draw.text((pv_x + pv_w - 240, cap_box_y + 24), "● VERIFIED HISTORICAL", font=get_font_safe(14, bold=True), fill=(34, 197, 94))

    fot_y = by + bh - 110
    draw.rounded_rectangle([(bx + 50, fot_y), (bx + bw - 50, fot_y + 85)], radius=10, fill=(15, 23, 42, 230), outline=(56, 189, 248), width=1)
    draw.text((bx + 70, fot_y + 16), f"ACCIDENT INVESTIGATION DOSSIER // {inc.get('flight_no', '')} ({inc.get('aircraft', '')})", font=get_pop_font(18), fill=(56, 189, 248))
    draw.text((bx + 70, fot_y + 48), f"Investigation oversight conducted by {inc.get('investigation_agency', 'Official Aviation Authorities')} // {inc.get('location', '')}", font=get_font_safe(15), fill=(226, 232, 240))

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
    # Scene 08: Congress Grills the Budget / Sponge Hearing
    (["PENTAGON_AUDIT", "FINANCIAL_AUDIT", "SPLIT_CIVIL", "DESK_BRIEFING"],
     ["CONGRESS GRILLED US OVER THE SPONGE BUDGET!", "TAXPAYER OUTRAGE: $4,800 AUTOMOTIVE SPONGE", "PENTAGON AUDIT CROSS-EXAMINATION!", "SENATE ARMED SERVICES COMMITTEE HEARING"]),
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
    narr = str(scene_data.get("narration") or "").strip()
    ch = str(scene_data.get("chapter") or "").strip()
    text = (narr + " " + ch).lower()

    is_crayon_capital = _CURRENT_TOPIC_CATEGORY in ("crayon_capital", "tech_finance_essay")
    if is_crayon_capital:
        modes = ["FINANCIAL_AUDIT", "TICKING_BUDGET", "CRT_MAINFRAME", "PENTAGON_AUDIT"]
        shot_count = max(2, int(math.ceil(dur / 4.0)))
        offset = idx % len(modes)
        shots = [modes[(offset + shot_idx) % len(modes)] for shot_idx in range(shot_count)]
        return shots, shots

    is_aviation = is_aviation_context(scene_data, text=text, vehicle_name=vehicle_name)
    if is_aviation:
        inc = resolve_aviation_incident(text, vehicle_name=vehicle_name, title=str(scene_data.get("video_title") or ""))
        target_count = max(2, int(math.ceil(dur / 4.0)))

        # 1. Investigation, Safety Boards, Legacy, CRM Reform & Phraseology Mandates
        if re.search(r'\b(investigat|ntsb|shk|atsb|ciaiac|bfu|ansv|black box|fdr|cvr|probable cause|findings|reform|legacy|revolution|mandat|phraseology|outlaw|break deadly)\b', text):
            shots = ["AVIATION_INVESTIGATION_FDR", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_CRM_DECISION", "AVIATION_AIRCRAFT_PROFILE"]
            titles = [
                f"{inc['investigation_agency'][:40]}",
                f"OFFICIAL ARCHIVAL EVIDENCE // {inc['flight_no']}",
                "CRM SYSTEMIC REFORM & INDUSTRY MANDATES",
                f"TECHNICAL LESSONS: {inc['aircraft'][:32]}"
            ]
            return shots[:target_count], titles[:target_count]

        # 2. Tower hearing explosions through fog & rescue chaos
        if re.search(r'\b(controllers in the tower|tower hear|muffled explosions|rescue crews rush to klm|smoke for critical|blinded|secondary explosions)\b', text):
            shots = ["AVIATION_ATC_TOWER", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_RUNWAY_MAP", "AVIATION_COCKPIT_CVR"]
            titles = [
                f"{inc['atc_facility'][:38]}: EMERGENCY ALARM",
                "CRASH SITE // AIRPORT RESCUE DISPATCH",
                f"{inc['location'][:36]}: RUNWAY SECTOR",
                "COCKPIT AUDIO RECORDER STATUS"
            ]
            return shots[:target_count], titles[:target_count]

        # 3. Survivors on intact wing & shattered wreckage
        if re.search(r'\b(survivors|scramble onto|intact left wing|gaping holes|shattered pan am|fog-bound ruins)\b', text):
            shots = ["AVIATION_HISTORICAL_ARCHIVE", "AVIATION_RUNWAY_MAP", "AVIATION_COCKPIT_CVR", "AVIATION_INVESTIGATION_FDR"]
            titles = [
                f"SURVIVOR RECONSTRUCTION // {inc['aircraft'][:32]}",
                f"{inc['location'][:36]}: DEBRIS FIELD",
                "CREW EVACUATION & IMPACT SITE",
                "ACCIDENT DOSSIER // OFFICIAL RECORD"
            ]
            return shots[:target_count], titles[:target_count]

        # 4. Crash, Fireball, 150 meters, All perish
        if re.search(r'\b(fireball|crashes back onto|perish instantly|exploding into|belly before exploding)\b', text):
            shots = ["AVIATION_HISTORICAL_ARCHIVE", "AVIATION_RUNWAY_MAP", "AVIATION_AIRCRAFT_PROFILE", "AVIATION_COCKPIT_CVR"]
            titles = [
                f"IMPACT & EXPLOSION // {inc['aircraft'][:32]}",
                f"RUNWAY 12/30 CRASH TIMELINE",
                f"STRUCTURAL DESTRUCTION // {inc['aircraft'][:32]}",
                "FINAL RECORDED IMPACT TELEMETRY"
            ]
            return shots[:target_count], titles[:target_count]

        # 5. Mid-Runway Collision & Impact Slice
        if re.search(r'\b(violently slice|shearing off|upper deck of pan am|achieves liftoff|heavy with fuel)\b', text):
            shots = ["AVIATION_RUNWAY_MAP", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_AIRCRAFT_PROFILE", "AVIATION_COCKPIT_CVR"]
            titles = [
                "COLLISION INTERSECTION // RUNWAY 12/30",
                f"HISTORICAL EVIDENCE // {inc['flight_no']}",
                f"AIRCRAFT MASS & FUEL LOAD // {inc['aircraft'][:30]}",
                "CRITICAL FLIGHT ATTITUDE PROFILE"
            ]
            return shots[:target_count], titles[:target_count]

        # 6. Tail strike & Drag Dynamics
        if re.search(r'\b(tail strike|dragging the 747|control column|premature attempt|sixty feet along)\b', text):
            shots = ["AVIATION_AIRCRAFT_PROFILE", "AVIATION_COCKPIT_CVR", "AVIATION_RUNWAY_MAP", "AVIATION_HISTORICAL_ARCHIVE"]
            titles = [
                "TAILSTRIKE DYNAMICS // MAXIMUM ELEVATOR DEFLECTION",
                f"{inc['flight_no']} COCKPIT // EMERGENCY ROTATION",
                "RUNWAY CENTERLINE GROUND CONTACT",
                f"AERODYNAMIC PROFILE // {inc['aircraft'][:32]}"
            ]
            return shots[:target_count], titles[:target_count]

        # 7. Collision visual panic & Evasive Turn
        if re.search(r'\b(look at him|goddamn|son of a bitch|coming|emergency power|wrenching the nose|hard left into the grass)\b', text):
            shots = ["AVIATION_COCKPIT_CVR", "AVIATION_RUNWAY_MAP", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_CVR_TRANSCRIPT"]
            titles = [
                "PAN AM COCKPIT // EVASIVE MANEUVER",
                "COLLISION VECTOR // GRASS EVASION",
                f"RECORD: {inc['location'][:36]}",
                "CVR RECORDING: FINAL SECONDS"
            ]
            return shots[:target_count], titles[:target_count]

        # 8. Landing lights & 'There he is'
        if re.search(r'\b(there he is|landing lights piercing|piercing the fog|firewalled|eleven seconds later)\b', text):
            shots = ["AVIATION_COCKPIT_CVR", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_RUNWAY_MAP", "AVIATION_ATC_TOWER"]
            titles = [
                "ZERO-VISIBILITY FOG BREAK // VISUAL CONTACT",
                f"ARCHIVAL EVIDENCE // {inc['aircraft'][:32]}",
                "CLOSING SPEED // 146 KNOTS INCURSION",
                f"{inc['atc_facility'][:36]}"
            ]
            return shots[:target_count], titles[:target_count]

        # 9. Radio Heterodyne Squeal & VHF Clash
        if re.search(r'\b(heterodyne|squeal|shrill|piercing two-second|audio squeal|simultaneous signals|exact same split-second|exact same vhf frequency)\b', text):
            shots = ["AVIATION_MAINTENANCE_BLUNDER", "AVIATION_CVR_TRANSCRIPT", "AVIATION_ATC_TOWER", "AVIATION_COCKPIT_CVR"]
            titles = [
                "VHF HETERODYNE // AUDIO CANCELLATION",
                "CVR AUDIO DECODE // SIMULTANEOUS TRANSMISSION",
                f"{inc['atc_facility'][:38]}",
                "COCKPIT AUDIO BLINDSPOT"
            ]
            return shots[:target_count], titles[:target_count]

        # 10. Pan Am Backtrack & CVR transmission clash
        if re.search(r'\b(hearing klm rolling|still taxiing down the runway|clipper 1736|both transmissions)\b', text):
            shots = ["AVIATION_CVR_TRANSCRIPT", "AVIATION_COCKPIT_CVR", "AVIATION_ATC_TOWER", "AVIATION_RUNWAY_MAP"]
            titles = [
                "CVR DUAL TRANSMISSION // CLIPPER 1736",
                "PAN AM COCKPIT // TAXI BROADCAST",
                f"{inc['atc_facility'][:38]}",
                "ACTIVE RUNWAY 12/30 INCURSION"
            ]
            return shots[:target_count], titles[:target_count]

        # 11. Readback Ambiguity & 'Stand by for takeoff'
        if re.search(r'\b(stand by for takeoff|we are now at takeoff|ambiguous phrase|surprised, replies)\b', text):
            shots = ["AVIATION_CVR_TRANSCRIPT", "AVIATION_ATC_TOWER", "AVIATION_CRM_DECISION", "AVIATION_RUNWAY_MAP"]
            titles = [
                "ATC PHRASEOLOGY ERROR // 'AT TAKEOFF'",
                f"{inc['atc_facility'][:38]}: STAND BY CALL",
                "CRM AMBIGUOUS READBACK BREAKDOWN",
                "TAKEOFF ROLL INITIATION GEOMETRY"
            ]
            return shots[:target_count], titles[:target_count]

        # 12. Capt van Zanten 'We gaan' & 24,000 lbs thrust
        if re.search(r'\b(we gaan|we are going|twenty-four thousand|pratt & whitney|releases the brakes|unleashes)\b', text):
            shots = ["AVIATION_COCKPIT_CVR", "AVIATION_AIRCRAFT_PROFILE", "AVIATION_CRM_DECISION", "AVIATION_RUNWAY_MAP"]
            titles = [
                "KLM COCKPIT // 'WE GAAN!' THROTTLE ADVANCE",
                "PRATT & WHITNEY JT9D TAKEOFF THRUST",
                "CRM AUTHORITY GRADIENT FAILURE",
                "TAKEOFF ACCELERATION DOWN RUNWAY 12"
            ]
            return shots[:target_count], titles[:target_count]

        # 13. Route clearance vs Takeoff clearance
        if re.search(r'\b(route clearance|papa beacon|fl nine-zero|en-route atc clearance|not an authorization)\b', text):
            shots = ["AVIATION_ATC_TOWER", "AVIATION_APPROACH_CHART", "AVIATION_CRM_DECISION", "AVIATION_HISTORICAL_ARCHIVE"]
            titles = [
                f"{inc['atc_facility'][:38]}: ROUTE CLEARANCE",
                "DEPARTURE CORRIDOR // PAPA BEACON FL90",
                "CRITICAL DISTINCTION: ROUTE VS TAKEOFF",
                f"HISTORICAL EVIDENCE // {inc['operator'][:28]}"
            ]
            return shots[:target_count], titles[:target_count]

        # 14. First Officer Meurs intervention & No clearance
        if re.search(r'\b(wait a minute|no clearance|don\'t have an atc clearance|throttles back|intervenes)\b', text):
            shots = ["AVIATION_CRM_DECISION", "AVIATION_COCKPIT_CVR", "AVIATION_ATC_TOWER", "AVIATION_CVR_TRANSCRIPT"]
            titles = [
                "FIRST OFFICER INTERVENTION // CLEARANCE CHECK",
                "KLM COCKPIT // JUNIOR COPILOT HESITATION",
                f"{inc['atc_facility'][:38]}",
                "CVR RECORDING: CLEARANCE REQUEST"
            ]
            return shots[:target_count], titles[:target_count]

        # 15. Duty time regulations & Dutch law pressure
        if re.search(r'\b(duty-time|strict dutch|flight will be canceled|stranding passengers|immense pressure)\b', text):
            shots = ["AVIATION_CRM_DECISION", "AVIATION_AIRCRAFT_PROFILE", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_COCKPIT_CVR"]
            titles = [
                "HUMAN FACTORS // STRICT DUTY TIME EXPIRATION",
                f"AIRCRAFT OPERATION PROFILE // {inc['aircraft'][:32]}",
                f"OFFICIAL ARCHIVE // {inc['operator'][:28]}",
                "FLIGHT DECK CREW PSYCHOLOGY"
            ]
            return shots[:target_count], titles[:target_count]

        # 16. Radio clarification with controller: 'The third one, sir'
        if re.search(r'\b(clarification|confirm that you want us to turn off|the third one, sir|one, two, three)\b', text):
            shots = ["AVIATION_ATC_TOWER", "AVIATION_CVR_TRANSCRIPT", "AVIATION_RUNWAY_MAP", "AVIATION_HISTORICAL_ARCHIVE"]
            titles = [
                f"{inc['atc_facility'][:38]}: CLEARANCE CLARIFICATION",
                "CVR RECORDING // INTERSECTION TURN INSTRUCTION",
                "RUNWAY TAXIWAY GEOMETRY",
                f"HISTORICAL ARCHIVE // {inc['aircraft'][:32]}"
            ]
            return shots[:target_count], titles[:target_count]

        # 17. Charlie-4 vs Charlie-3 runway confusion
        if re.search(r'\b(charlie-4|charlie-3|45-degree angle|135-degree turns|wet grass|nearly impossible)\b', text):
            shots = ["AVIATION_RUNWAY_MAP", "AVIATION_COCKPIT_CVR", "AVIATION_ATC_TOWER", "AVIATION_HISTORICAL_ARCHIVE"]
            titles = [
                "TAXIWAY GEOMETRY // CHARLIE-3 VS CHARLIE-4",
                "PAN AM FLIGHT DECK // 135° TURN CONFUSION",
                f"{inc['atc_facility'][:38]}: TAXI DIRECTIVE",
                f"ARCHIVE EVIDENCE // {inc['aircraft'][:32]}"
            ]
            return shots[:target_count], titles[:target_count]

        # 18. Tower instructions to Pan Am (third taxiway)
        if re.search(r'\b(leave the runway by the third|instructions? pan am|third taxiway|clear the runway)\b', text):
            shots = ["AVIATION_ATC_TOWER", "AVIATION_RUNWAY_MAP", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_COCKPIT_CVR"]
            titles = [
                f"{inc['atc_facility'][:38]}: RUNWAY EXIT DIRECTIVE",
                "LOS RODEOS // TAXIWAY CHARLIE-3 INSTRUCTION",
                f"DOCUMENTARY RECORD // {inc['aircraft'][:32]}",
                "PAN AM COCKPIT // VISIBILITY SCAN"
            ]
            return shots[:target_count], titles[:target_count]

        # 19. Pan Am trailing KLM on same strip
        if re.search(r'\b(180-degree turn|behind him, pan american|exact same strip|captained by veteran)\b', text):
            shots = ["AVIATION_RUNWAY_MAP", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_COCKPIT_CVR", "AVIATION_ATC_TOWER"]
            titles = [
                "SEQUENTIAL RUNWAY BACKTRACK // KLM & PAN AM",
                f"HISTORICAL ARCHIVE // {inc['flight_no']}",
                "FLIGHT DECK SITUATIONAL AWARENESS",
                f"{inc['atc_facility'][:36]}"
            ]
            return shots[:target_count], titles[:target_count]

        # 20. Fog rolling down Anaga slopes
        if re.search(r'\b(anaga slopes|orographic clouds|shifting fog|three hundred meters|blinding both)\b', text):
            shots = ["AVIATION_RUNWAY_MAP", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_ATC_TOWER", "AVIATION_APPROACH_CHART"]
            titles = [
                "OROGRAPHIC WEATHER // ANAGA CLOUD INTRUSION",
                "DENSE FOG BANK // VISIBILITY < 300 METERS",
                f"{inc['atc_facility'][:38]}: BLIND TOWER",
                "LOS RODEOS MOUNTAIN PLATEAU TOPOGRAPHY"
            ]
            return shots[:target_count], titles[:target_count]

        # 21. Backtrack down active runway sequentially
        if re.search(r'\b(single runway and a parallel|backtrack down the active|weather conditions deteriorate)\b', text):
            shots = ["AVIATION_RUNWAY_MAP", "AVIATION_AIRCRAFT_PROFILE", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_ATC_TOWER"]
            titles = [
                f"{inc['location'][:36]}: SINGLE RUNWAY BOTTLENECK",
                f"BOEING 747 DIMENSIONS & WINGSPAN // {inc['aircraft'][:28]}",
                "APRON CONGESTION // PARKED DIVERTED AIRCRAFT",
                f"{inc['atc_facility'][:36]}"
            ]
            return shots[:target_count], titles[:target_count]

        # 22. Las Palmas bombing & Apron diversion
        if re.search(r'\b(las palmas|terrorist bombing|divert to los rodeos|unprepared regional apron)\b', text):
            shots = ["AVIATION_APPROACH_CHART", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_AIRCRAFT_PROFILE", "AVIATION_ATC_TOWER"]
            titles = [
                "LAS PALMAS BOMBING DIVERSION // CANARY AIRSPACE",
                f"REGIONAL APRON CONGESTION // {inc['location'][:32]}",
                f"JUMBO JET FLEET PROFILE // {inc['aircraft'][:32]}",
                f"{inc['atc_facility'][:36]}"
            ]
            return shots[:target_count], titles[:target_count]

        # Default Aviation Suite: Non-Repeating Cyclic Rotation
        cycle = [
            ["AVIATION_RUNWAY_MAP", "AVIATION_HISTORICAL_ARCHIVE", "AVIATION_COCKPIT_CVR"],
            ["AVIATION_ATC_TOWER", "AVIATION_CVR_TRANSCRIPT", "AVIATION_AIRCRAFT_PROFILE"],
            ["AVIATION_CRM_DECISION", "AVIATION_RUNWAY_MAP", "AVIATION_HISTORICAL_ARCHIVE"],
            ["AVIATION_APPROACH_CHART", "AVIATION_COCKPIT_CVR", "AVIATION_ATC_TOWER"]
        ]
        pick = cycle[idx % len(cycle)]
        return pick[:target_count], [f"{inc['location'][:36]} // RECORD", f"HISTORICAL ARCHIVE // {inc['aircraft'][:32]}", "FLIGHT RECONSTRUCTION"][:target_count]
    # ─────────────────────────────────────────────────────────────
    # CONTEXT-AWARE SEMANTIC TOPIC MATCHER (ZERO HARDCODED MISMATCH)
    # ─────────────────────────────────────────────────────────────
    target_count = max(4, int(math.ceil(dur / 4.0)))
    
    # 1. NATO Urban Warfare Door Markings / FEMA X Matrix
    if re.search(r'\b(nato infantry standardized door|room clearance|diagonal slash|x-mark|fema|door marking|quadrant|breaching)\b', text):
        shots = ["SYMBOL_X", "SYMBOL_SLASH", "BLUEPRINT_SYMBOL_HUD", "DESK_BRIEFING"]
        titles = [
            "NATO URBAN WARFARE: STANDARDIZED DOOR MARKINGS",
            "FEMA 4-QUADRANT ENTRY MATRIX: ROOM CLEARED",
            "DIAGONAL SLASH: SEARCH IN PROGRESS // HAZARD LOG",
            "TACTICAL SYMOLOGY PROTOCOL & SQUAD DOCTRINE"
        ]
        return shots[:target_count], titles[:target_count]

    # 2. Red Cockpit Illumination & NVG Disappearing Ink
    if re.search(r'\b(red lighting|red light|red ink|disappearing red ink|nvg|night vision goggles)\b', text):
        shots = ["COCKPIT_HUD", "EMERGENCY_LOCKDOWN", "MACRO_BLUEPRINT", "DESK_BRIEFING"]
        titles = [
            "RED NIGHT ILLUMINATION: COCKPIT AVIONICS HAZARD",
            "RED WAX PIGMENT VANISHES UNDER RED FILTER!",
            "SPECTRAL WAVELENGTH FAILURE IN NIGHT OPS",
            "NAVY AVIONICS BULLETIN: USE CONTRASTING WAX"
        ]
        return shots[:target_count], titles[:target_count]

    # 3. Carrier Flight Deck & High Winds / Tractor Windshields
    if re.search(r'\b(carrier flight deck|flight deck officers|tractor|fifty-knot|jet exhaust)\b', text):
        shots = ["COCKPIT_HUD", "KEN_BURNS", "MACRO_BLUEPRINT", "EDITORIAL_BRIEFING"]
        titles = [
            "CARRIER FLIGHT DECK OPERATIONS // 50-KNOT WINDS",
            "TRACTOR CANOPY & BULKHEAD FUEL LOGGING",
            "HIGH-VELOCITY JET EXHAUST ENVIRONMENT",
            "ANALOG WAX SURVIVES HARSH MARITIME CONDITIONS"
        ]
        return shots[:target_count], titles[:target_count]

    # 4. M1 Abrams Tank & Fort Irwin Desert Heat
    if re.search(r'\b(fort irwin|m1 abrams|tank turrets|gunner)\b', text):
        shots = ["TANK_SIGHT", "KEN_BURNS", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"]
        titles = [
            "FORT IRWIN DESERT TRIALS: 55°C TURRET INTERIOR",
            "M1A2 ABRAMS GUNNER DAY & THERMAL OPTICS",
            "TURRET ELECTRONICS OVERHEAT: ANALOG RETICLE",
            "ARMORED CAVALRY COMBAT READINESS AUDIT"
        ]
        return shots[:target_count], titles[:target_count]

    # 5. FLIR Thermal Imaging & Fallujah Bakery Incident
    if re.search(r'\b(flir|bakery|fallujah|thermal bloom|friendly platoon)\b', text):
        shots = ["FLIR_BAKERY_INCIDENT", "COCKPIT_HUD", "COMM_SPLIT_SCREEN", "DESK_BRIEFING"]
        titles = [
            "FLIR THERMAL IMAGING OPTICS // TARGET ACQUISITION",
            "CEASE FIRE! CEASE FIRE! IT'S A BAKERY!",
            "BLUE WAX MARKING ON SILL SAVED 12 LIVES!",
            "IR LASER & THERMAL IDENTIFICATION PROTOCOL"
        ]
        return shots[:target_count], titles[:target_count]

    # 6. Autonomous Robot Dog & Razor Wire Fiasco
    if re.search(r'\b(robot dog|autonomous robot|concertina|razor wire)\b', text):
        shots = ["ROBOT_DOG", "LAB_RND", "FINANCIAL_AUDIT", "DESK_BRIEFING"]
        titles = [
            "$16 BILLION AUTONOMOUS ROBOT DOG PLATFORM!",
            "ROBOT DOG LEGS TANGLED IN CONCERTINA WIRE!",
            "SOLDIERS RISK LIVES TO RESCUE $450K DRONE!",
            "LESSON: ROBOTICS CANNOT REPLACE A $0.15 CRAYON"
        ]
        return shots[:target_count], titles[:target_count]

    # 7. Submarine Sonar Control & Vertical Plot Boards
    if re.search(r'\b(submarine|sonar|plot board|vertical glass)\b', text):
        shots = ["TACTICAL_RADAR", "MACRO_BLUEPRINT", "CRT_MAINFRAME", "DESK_BRIEFING"]
        titles = [
            "SUBMARINE SONAR CONTROL: VERTICAL PLOT BOARD",
            "ACOUSTIC JAMMING: DIGITAL SCREENS GO DARK",
            "GREASE PENCIL ON GLASS REMAINS PRIMARY CHANNEL",
            "UNDERSEA WARFARE ANALOG DOCTRINE"
        ]
        return shots[:target_count], titles[:target_count]

    # 8. Titanium Holder Over-Engineering & Exploded Patent
    if re.search(r'\b(titanium holders?|titanium tactical|titanium|peelable paper string)\b', text):
        shots = ["EXPLODED_PATENT", "LAB_RND", "PENTAGON_AUDIT", "DESK_BRIEFING"]
        titles = [
            "OVER-ENGINEERED: $850 TITANIUM WAX HOLDER",
            "EXPLODED SCHEMATIC: 14 PRECISION MACHINED PARTS",
            "SOLDIERS DISCARD TITANIUM: TAPE WAX TO VESTS",
            "PENTAGON PROCUREMENT LESSON: COMPLEXITY FAILS"
        ]
        return shots[:target_count], titles[:target_count]

    # 9. Battlefield Triage & Mass Casualty Protocol
    if re.search(r'\b(triage|mass casualty|tourniquet)\b', text):
        shots = ["SYMBOL_TRIAGE", "BLUEPRINT_SYMBOL_HUD", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"]
        titles = [
            "BATTLEFIELD TRIAGE: COLOR-CODED SURVIVAL",
            "RAPID CASUALTY ASSESSMENT: IMMEDIATE VS DELAYED",
            "WAX MARKINGS ENDURE IN BLOOD, DIRT AND SHOCK",
            "MEDEVAC FLIGHT PRIORITY PROTOCOL"
        ]
        return shots[:target_count], titles[:target_count]

    # 10. Foreign Espionage & Paraffin Spectrograph / Dossier
    if re.search(r'\b(foreign intelligence|kgb|dossier|spectrograph|foreign chemical|paraffin|infiltrate|easton)\b', text):
        shots = ["FOREIGN_INTEL_DOSSIER", "FOREIGN_INTELLIGENCE", "LAB_RND", "DESK_BRIEFING"]
        titles = [
            "FOREIGN INTELLIGENCE DOSSIER: THE SECRET CRAYON",
            "SPECTROGRAPH TEST: 100% COMMERCIAL PARAFFIN WAX",
            "'DO NOT REPLICATE: ALLOW THEM TO SPEND BILLIONS'",
            "KGB CONCLUSION: PENTAGON SCAMMED BY CONTRACTORS"
        ]
        return shots[:target_count], titles[:target_count]

    # 11. Cyber-Crayon & Battle Networks Jamming
    if re.search(r'\b(cyber-crayon|rfid|bluetooth|digital battle networks?|atak|blue force tracker)\b', text):
        shots = ["CRT_MAINFRAME", "TACTICAL_RADAR", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"]
        titles = [
            "THE $42M CYBER-CRAYON: BLUETOOTH EMBEDDED WAX",
            "EW JAMMING SCRAMBLES MICROCHIPS ON FRONTLINE",
            "PROJECT SCRAPPED: TROOPS REVERT TO $0.85 WAX",
            "CYBER DEFENSE INITIATIVE RETROSPECTIVE"
        ]
        return shots[:target_count], titles[:target_count]

    # 12. Senate Armed Services Hearing & Sponge Budget Audit
    if re.search(r'\b(senate armed services|committee|auditors discovered|sponge budget|congress)\b', text):
        shots = ["PENTAGON_AUDIT", "FINANCIAL_AUDIT", "TICKING_BUDGET", "DESK_BRIEFING"]
        titles = [
            "SENATE ARMED SERVICES COMMITTEE HEARING",
            "AUDIT DISASTER: $640 SPONGE & $4,800 CRAYON",
            "PENTAGON OFFICIALS GRILLED OVER SPENDING",
            "CONGRESSIONAL OVERSIGHT DEMANDS ANSWERS"
        ]
        return shots[:target_count], titles[:target_count]

    # 13. Crayola vs Mil-Spec Markup (Only when specifically contrasting $0.15 vs $4,800)
    if re.search(r'\b(32,000x|markup|crayola|commercial civilian|\$4,800|\$0\.15)\b', text) and idx in (0, 4, 30):
        shots = ["SPLIT_CIVIL", "TICKING_BUDGET", "PENTAGON_AUDIT", "DESK_BRIEFING"]
        titles = [
            "CIVILIAN HARDWARE VS MIL-SPEC CRAYON!",
            "32,000x MARKUP: TAXPAYER BILLIONS SPENT!",
            "PENTAGON CONTRACTOR MARGINS EXPOSED",
            "COMMERCIAL OFF-THE-SHELF ALTERNATIVE"
        ]
        return shots[:target_count], titles[:target_count]

    # 14. Marine Corps Barracks Folklore
    if re.search(r'\b(marine infantry folklore|barracks culture|eating crayons|eat crayons)\b', text):
        shots = ["HANGAR_WALK", "KEN_BURNS", "URBAN_STREET", "DESK_BRIEFING"]
        titles = [
            "MARINE CORPS FOLKLORE: THE BARRACKS WAX LEGEND",
            "50 YEARS OF INFANTRY SURVIVAL CULTURE",
            "NON-TOXIC CERTIFIED: PENTAGON SAFETY REVIEW",
            "WARFARE REALITY: THE UNBREAKABLE ANALOG TRADITION"
        ]
        return shots[:target_count], titles[:target_count]

    # 15. Naval Aviation Salt Spray
    if re.search(r'\b(salt spray|corrodes delicate|maritime deployment)\b', text):
        shots = ["COCKPIT_HUD", "MACRO_BLUEPRINT", "KEN_BURNS", "EDITORIAL_BRIEFING"]
        titles = [
            "NAVAL AVIATION: SALT SPRAY CORROSION AUDIT",
            "TOUCHSCREEN SCREENS FAIL IN 48 HOURS AT SEA",
            "ANALOG GREASE WAX REMAINS FAILSAFE ON CANOPY",
            "MARITIME DEPLOYMENT LESSONS LEARNED"
        ]
        return shots[:target_count], titles[:target_count]

    # 16. Arctic Testing & Frozen Ballpoint Pens (1968)
    if re.search(r'\b(ballpoint pens freeze|arctic|minus thirty|freeze in arctic)\b', text):
        shots = ["TACTICAL_MAP", "MACRO_BLUEPRINT", "EMERGENCY_LOCKDOWN", "DESK_BRIEFING"]
        titles = [
            "1968 ARCTIC DEPLOYMENT: MINUS 30°C TESTING",
            "BALLPOINT PEN INK FREEZES SOLID IN MINUTES",
            "CRITICAL PROTOCOL: ANALOG WAX NEVER GLITCHES",
            "SUB-ZERO COMBAT MARKING VERDICT"
        ]
        return shots[:target_count], titles[:target_count]

    # 17. Wax Chemical Formulation
    if re.search(r'\b(grease pencil|wax-bound pigment|pigment matrix)\b', text):
        shots = ["LAB_RND", "MACRO_BLUEPRINT", "CRT_MAINFRAME", "EDITORIAL_BRIEFING"]
        titles = [
            "THE CHEMICAL MATRIX: 100% PARAFFIN & PIGMENT",
            "PEELABLE STRING PACKAGING: 19th CENTURY GENIUS",
            "ZERO ELECTRONICS: ZERO JAMMING RISK",
            "ANALOG SIMPLICITY IN ADVANCED WARFARE"
        ]
        return shots[:target_count], titles[:target_count]

    # 18. Persian Gulf Cockpit Heat & Melting Sludge
    if re.search(r'\b(carrier strike operations|persian gulf|canopy vents|solar greenhouse)\b', text):
        shots = ["COCKPIT_HUD", "EMERGENCY_LOCKDOWN", "MACRO_BLUEPRINT", "DESK_BRIEFING"]
        titles = [
            "PERSIAN GULF STRIKE OPS: 62°C COCKPIT HEAT",
            "SOLAR GREENHOUSE EFFECT MELTS MIL-SPEC WAX!",
            "WAX SLUDGE CLOGS CRITICAL AVIONICS VENTS",
            "FLIGHT SAFETY ADVISORY // CANOPY REVISION"
        ]
        return shots[:target_count], titles[:target_count]

    # 19. Wet Weather Combat Exercises
    if re.search(r'\b(wet-weather|paper maps dissolved|waterproof wax)\b', text):
        shots = ["TACTICAL_MAP", "MACRO_BLUEPRINT", "KEN_BURNS", "DESK_BRIEFING"]
        titles = [
            "WET-WEATHER COMBAT: PAPER MAPS DISSOLVE IN RAIN",
            "ACETATE MAP OVERLAYS & GREASE PENCIL TRUTH",
            "WATERPROOF WAX REMAINS HIGH-CONTRAST UNDER WATER",
            "INFANTRY READINESS ADVISORY BULLETIN"
        ]
        return shots[:target_count], titles[:target_count]

    # 20. Phosphor-Wax-2000 R&D Lab
    if re.search(r'\b(phosphor-wax-2000|luminescent isotopes|glowing)\b', text):
        shots = ["LAB_RND", "MACRO_BLUEPRINT", "CRT_MAINFRAME", "DESK_BRIEFING"]
        titles = [
            "PHOSPHOR-WAX-2000: SYNTHETIC ISOTOPE R&D",
            "GLOW-IN-THE-DARK WAX ATTRACTS ENEMY SNIPERS!",
            "ANOTHER $120M DEFENSE CONTRACTOR FAILURE",
            "TROOPS REVERT TO DIM WHITE CHALK"
        ]
        return shots[:target_count], titles[:target_count]

    # 21. Special Forces Peeling Ritual
    if re.search(r'\b(astonishing ritual|peeling|strings of wax)\b', text):
        shots = ["MACRO_BLUEPRINT", "KEN_BURNS", "DESK_BRIEFING", "EDITORIAL_BRIEFING"]
        titles = [
            "SPECIAL FORCES DEPLOYMENT: STRING PEELING RITUAL",
            "REMOVING PAPER WRAP IN SILENCE BEFORE DAWN",
            "ANALOG TOOLS EXCEL IN COVERT NIGHT OPERATIONS",
            "THE PSYCHOLOGY OF COMBAT PREPARATION"
        ]
        return shots[:target_count], titles[:target_count]

    # 22. Joint Chiefs Study: Simplicity Wins
    if re.search(r'\b(joint chiefs of staff|comprehensive study|survival rates higher)\b', text):
        shots = ["PENTAGON_AUDIT", "FINANCIAL_AUDIT", "TICKING_BUDGET", "DESK_BRIEFING"]
        titles = [
            "JOINT CHIEFS OF STAFF COMPREHENSIVE STUDY",
            "HIGHER SURVIVAL RATES WITH $0.15 ANALOG WAX",
            "LESSON: OVER-ENGINEERED TECH KILLS IN COMBAT",
            "FINAL VERDICT: DEFENSE DOCTRINE REALITY CHECK"
        ]
        return shots[:target_count], titles[:target_count]

    # ─────────────────────────────────────────────────────────────
    # DYNAMIC HIGH-VARIETY BALANCED POOL (ZERO REPETITION)
    # ─────────────────────────────────────────────────────────────
    high_variety_suites = [
        (["HANGAR_WALK", "TACTICAL_RADAR", "KEN_BURNS", "DESK_BRIEFING"],
         ["TACTICAL COMBAT READINESS INSPECTION", "SENSOR & TELEMETRY SWEEP", "DECLASSIFIED ARCHIVAL RECORD", "STRATEGIC DOCTRINE DEBRIEF"]),
        (["LAB_RND", "MACRO_BLUEPRINT", "PENTAGON_AUDIT", "EDITORIAL_BRIEFING"],
         ["DEFENSE R&D ENGINEERING FACILITY", "CAD STRUCTURAL SPECIFICATION", "CONGRESSIONAL OVERSIGHT AUDIT", "ANALYTICAL DOCTRINE SUMMARY"]),
        (["URBAN_STREET", "BLUEPRINT_SYMBOL_HUD", "COMM_SPLIT_SCREEN", "DESK_BRIEFING"],
         ["URBAN RECONNAISSANCE PATROL", "TACTICAL BLUEPRINT HUD OVERLAY", "TRI-BRANCH VIDEO CONFERENCE DEBRIEF", "LESSONS LEARNED BRIEFING"]),
        (["FOREIGN_INTELLIGENCE", "FOREIGN_INTEL_DOSSIER", "TACTICAL_RADAR", "DESK_BRIEFING"],
         ["FOREIGN INTELLIGENCE ANALYSIS", "TOP SECRET CLASSIFIED DOSSIER", "SIGNAL INTELLIGENCE SWEEP", "COUNTER-MEASURE PROTOCOL"]),
        (["FINANCIAL_AUDIT", "TICKING_BUDGET", "PENTAGON_AUDIT", "DESK_BRIEFING"],
         ["DEFENSE PROCUREMENT EXPENDITURE AUDIT", "ROLLING TAXPAYER COST ESTIMATE", "PENTAGON HEARING COMMITTEE", "CONTRACTOR ACCOUNTABILITY REVIEW"]),
        (["COCKPIT_HUD", "EMERGENCY_LOCKDOWN", "KEN_BURNS", "EDITORIAL_BRIEFING"],
         ["TACTICAL AVIONICS TELEMETRY CHECK", "CRITICAL CAUTION PROTOCOL", "DECLASS HISTORIC FLIGHT TEST", "AVIONICS DOCTRINE REPORT"]),
    ]
    suite_idx = idx % len(high_variety_suites)
    shots, titles = high_variety_suites[suite_idx]
    return shots[:target_count], titles[:target_count]


def _short_visual_phrase(text: str, max_words: int = 6) -> str:
    words = re.findall(r"[A-Za-z0-9$€£%.,'-]+", str(text or ""))
    return " ".join(words[:max_words]).strip(" ,.-")


def _crayon_visual_kind(asset_id: object, asset_type: object = "") -> str:
    value = f"{asset_id or ''} {asset_type or ''}".lower()
    if any(word in value for word in ("marker", "pencil", "wax", "stylus")):
        return "marker"
    if any(word in value for word in ("document", "report", "filing", "record", "source")):
        return "document"
    if any(word in value for word in ("chart", "data", "metric", "graph")):
        return "chart"
    if "timeline" in value:
        return "timeline"
    if any(word in value for word in ("aircraft", "airplane", "fighter", "jet", "cockpit", "f16", "f-16")):
        return "aircraft"
    if any(word in value for word in ("vehicle", "tank", "ship", "destroyer")):
        return "vehicle"
    if any(word in value for word in ("comparison", "versus", "tradeoff")):
        return "comparison"
    if any(word in value for word in ("character", "reaction")):
        return "character"
    return "component"


def _crayon_story_family(scene_data: dict) -> str:
    visual = scene_data.get("visual") or {}
    primary = visual.get("primary_asset") or {}
    b_roll = visual.get("b_roll") or {}
    text = " ".join(
        str(value or "")
        for value in (
            scene_data.get("narration"),
            scene_data.get("chapter"),
            primary.get("asset_id"),
            primary.get("highlight"),
            b_roll.get("asset_id"),
            b_roll.get("text_badge"),
        )
    ).lower()

    if re.search(r"\b(f-?16|cockpit|rudder|flight stick|pilot|fighter jet)\b", text):
        return "cockpit"
    if re.search(r"\b(fallujah|abrams|tank|bakery|blue arrow|thermal sight)\b", text):
        return "tank"
    if re.search(r"\b(symbol|marking|door|wall|chevron|triage|breach|corridor)\b", text):
        return "marking"
    if re.search(r"\b(wax|crayon|grease pencil|marker|melting|melted)\b", text):
        return "wax"
    if re.search(r"\b(pneumatic|ultrasonic|stylus|freez|temperature|engineering|prototype)\b", text):
        return "lab"
    if re.search(r"\b(cost|contract|budget|billion|million|procurement|price|dollar)\b", text):
        return "cost"
    return "object"


def _crayon_story_subshots(scene_data: dict, duration: float, idx: int) -> List[str]:
    family = _crayon_story_family(scene_data)
    sequences = {
        "cockpit": ["CRAYON_STORY_COCKPIT", "CRAYON_STORY_WAX", "CRAYON_STORY_REACTION"],
        "tank": ["CRAYON_STORY_TANK", "CRAYON_STORY_MARKING", "CRAYON_STORY_REACTION"],
        "marking": ["CRAYON_STORY_MARKING", "CRAYON_STORY_WAX", "CRAYON_STORY_REACTION"],
        "wax": ["CRAYON_STORY_WAX", "CRAYON_STORY_COCKPIT", "CRAYON_STORY_REACTION"],
        "lab": ["CRAYON_STORY_LAB", "CRAYON_STORY_WAX", "CRAYON_STORY_REACTION"],
        "cost": ["CRAYON_STORY_COST", "CRAYON_STORY_LAB", "CRAYON_STORY_REACTION"],
        "object": ["CRAYON_STORY_LAB", "CRAYON_STORY_MARKING", "CRAYON_STORY_REACTION"],
    }
    sequence = sequences[family]
    count = max(1, int(math.ceil(duration / 4.0)))
    offset = idx % len(sequence)
    return [sequence[(offset + subshot_idx) % len(sequence)] for subshot_idx in range(count)]


def render_crayon_story_shot(
    frame: Image.Image,
    draw: ImageDraw.ImageDraw,
    scene_data: dict,
    shot_type: str,
    t_sub: float,
    duration: float,
    speaker_img: Image.Image,
) -> None:
    progress = min(1.0, max(0.0, t_sub / max(duration, 0.1)))
    pulse = 0.5 + 0.5 * math.sin(t_sub * 5.0)
    family = shot_type.removeprefix("CRAYON_STORY_").lower()
    visual = scene_data.get("visual") or {}
    primary = visual.get("primary_asset") or {}
    b_roll = visual.get("b_roll") or {}
    story_text = " ".join(
        str(value or "")
        for value in (
            scene_data.get("narration"),
            scene_data.get("chapter"),
            primary.get("asset_id"),
            primary.get("highlight"),
            b_roll.get("asset_id"),
            b_roll.get("text_badge"),
        )
    ).lower()
    fictional = bool(scene_data.get("fictional_satire"))
    topic_bg_path = scene_data.get("topic_bg") or scene_data.get("custom_image") or scene_data.get("image_path")
    if topic_bg_path and Path(topic_bg_path).exists():
        custom_bg_img = get_cached_bg(Path(topic_bg_path), (W, H)).copy()
        dimmed = Image.new("RGBA", (W, H), (15, 23, 42, 110))
        custom_bg_img = Image.alpha_composite(custom_bg_img, dimmed)
        frame.paste(custom_bg_img, (0, 0))
    else:
        background = {
            "cockpit": COCKPIT_BG,
            "tank": None,
            "marking": None,
            "lab": TECH_BG,
            "wax": TECH_BG,
            "cost": WAR_ROOM_BG,
            "reaction": WAR_ROOM_BG,
        }.get(family, TECH_BG)
        if background:
            frame.paste(get_cached_bg(background), (0, 0))
        else:
            draw.rectangle((0, 0, W, H), fill=(24, 34, 41, 255))

    accent = (255, 187, 54, 255)
    pale = (246, 245, 230, 255)
    dark = (13, 25, 38, 230)
    chapter = str(scene_data.get("chapter") or "TACTICAL CRAYON").strip().upper()[:48]
    draw.rounded_rectangle((58, 48, 900, 116), radius=18, fill=dark, outline=accent, width=3)
    draw.text((86, 67), chapter, font=get_font_safe(30, bold=True), fill=pale)

    if family in {"cockpit", "wax"}:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_radius = 170 + int(42 * pulse)
        glow_draw.ellipse((920 - glow_radius, 475 - glow_radius, 920 + glow_radius, 475 + glow_radius), fill=(255, 108, 27, 60))
        frame.alpha_composite(glow)
        draw.rounded_rectangle((280, 610, 1640, 1030), radius=48, fill=(15, 27, 34, 245), outline=(117, 140, 145, 255), width=10)
        for panel_x in (420, 760, 1100, 1420):
            draw.rounded_rectangle((panel_x - 105, 700, panel_x + 105, 905), radius=20, fill=(20, 48, 55, 255), outline=(56, 189, 248, 255), width=5)
            draw.ellipse((panel_x - 32, 764, panel_x + 32, 828), outline=(82, 223, 166, 255), width=5)
            draw.line((panel_x - 65, 858, panel_x + 65, 858), fill=(82, 223, 166, 255), width=5)
        if fictional or any(term in story_text for term in ("wax", "crayon", "grease pencil", "marker")):
            x = 950 + int(38 * math.sin(t_sub * 2.8))
            draw.rounded_rectangle((x - 250, 390, x + 215, 472), radius=38, fill=(42, 104, 116, 255), outline=accent, width=7)
            draw.polygon(((x + 215, 390), (x + 340, 431), (x + 215, 472)), fill=(223, 211, 168, 255), outline=accent)
            draw.ellipse((x + 306, 418, x + 354, 468), fill=(234, 105, 56, 255))
            drip_y = 486 + int(progress * 65)
            draw.line((x - 80, 470, x - 82, drip_y), fill=(255, 122, 62, 255), width=14)
            draw.line((x + 50, 470, x + 54, drip_y - 18), fill=(255, 122, 62, 255), width=12)
        if any(term in story_text for term in ("jam", "melt", "lock")):
            draw.rounded_rectangle((685, 512, 1195, 585), radius=18, fill=(141, 35, 35, 230), outline=(255, 203, 93, 255), width=4)
            draw.text((742, 528), "CONTROL INPUT JAMMED", font=get_font_safe(27, bold=True), fill=pale)
        if family == "wax":
            draw.text((575, 300), "THE MELTING-POINT MOMENT", font=get_pop_font(45), fill=accent)

    elif family == "tank":
        draw.rectangle((0, 0, W, 625), fill=(40, 49, 58, 255))
        draw.ellipse((1430, 110, 1590, 270), fill=(190, 193, 174, 255))
        for smoke_idx in range(7):
            smoke_x = 240 + smoke_idx * 210 + int(18 * math.sin(t_sub * 1.2 + smoke_idx))
            smoke_y = 210 + (smoke_idx % 3) * 85
            draw.ellipse((smoke_x, smoke_y, smoke_x + 180, smoke_y + 90), fill=(59, 65, 65, 180))
        draw.rectangle((0, 625, W, H), fill=(29, 35, 33, 255))
        for building_x, width, height in ((90, 330, 400), (490, 260, 520), (1300, 430, 450), (1660, 220, 555)):
            top = 625 - height
            draw.rectangle((building_x, top, building_x + width, 625), fill=(55, 59, 54, 255), outline=(128, 120, 97, 255), width=5)
            for wx in range(building_x + 35, building_x + width - 24, 85):
                draw.rectangle((wx, top + 55, wx + 40, top + 105), fill=(23, 32, 35, 255), outline=(172, 150, 102, 255), width=3)
        has_arrow = "arrow" in story_text
        if has_arrow:
            sill_x, sill_y = 1030, 535
            draw.rectangle((sill_x - 130, sill_y, sill_x + 165, sill_y + 34), fill=(186, 166, 130, 255), outline=pale, width=3)
            draw.line((sill_x - 52, sill_y - 90, sill_x + 45, sill_y - 25), fill=(63, 161, 231, 255), width=20)
            draw.polygon(((sill_x + 45, sill_y - 25), (sill_x + 5, sill_y - 35), (sill_x + 31, sill_y - 72)), fill=(63, 161, 231, 255))
        tank_x = 790 + int(26 * math.sin(t_sub * 1.5))
        draw.rounded_rectangle((tank_x - 260, 820, tank_x + 230, 920), radius=34, fill=(76, 91, 65, 255), outline=(185, 193, 149, 255), width=5)
        draw.polygon(((tank_x - 100, 820), (tank_x - 50, 745), (tank_x + 95, 745), (tank_x + 155, 820)), fill=(82, 101, 73, 255), outline=(185, 193, 149, 255))
        for wheel_x in range(tank_x - 190, tank_x + 190, 75):
            draw.ellipse((wheel_x - 30, 885, wheel_x + 30, 945), fill=(30, 37, 33, 255), outline=(170, 178, 145, 255), width=4)
        draw.text(
            (1100, 695),
            "A BLUE-ARROW STORY" if has_arrow else "ILLUSTRATED TANK SCENE",
            font=get_pop_font(38),
            fill=accent,
        )

    elif family == "marking":
        draw.rectangle((0, 0, W, 900), fill=(63, 68, 67, 255))
        draw.rectangle((0, 900, W, H), fill=(48, 46, 43, 255))
        for wall_y in (270, 460, 650, 840):
            draw.line((80, wall_y, W - 80, wall_y), fill=(78, 82, 79, 255), width=3)
        draw.rounded_rectangle((485, 220, 1430, 1015), radius=22, fill=(78, 56, 43, 255), outline=(218, 190, 140, 255), width=12)
        for y in range(285, 980, 82):
            draw.arc((520, y, 1380, y + 75), 180, 350, fill=(119, 84, 59, 255), width=3)
        draw.ellipse((1325, 612, 1365, 652), fill=(225, 190, 97, 255))
        draw.line((710, 585, 870, 430, 1030, 585, 870, 740), fill=(84, 207, 255, 255), width=22, joint="curve")
        draw.arc((960, 410, 1230, 680), 30, 320, fill=(255, 194, 72, 255), width=18)
        draw.ellipse((1110, 405, 1180, 475), outline=(255, 116, 93, 255), width=12)
        icon_caption = "FICTIONAL, NON-STANDARD ICONS" if fictional else "NON-OPERATIONAL GENERIC MARKS"
        draw.text((630, 270), icon_caption, font=get_font_safe(29, bold=True), fill=pale)
        crayon_y = 810 - int(progress * 75)
        draw.rounded_rectangle((1080, crayon_y, 1370, crayon_y + 52), radius=24, fill=(54, 109, 179, 255), outline=pale, width=4)

    elif family == "lab":
        draw.rounded_rectangle((270, 725, 1660, 980), radius=32, fill=(31, 42, 49, 255), outline=(120, 147, 156, 255), width=8)
        for ring in range(3):
            radius = 110 + ring * 95 + int(progress * 24)
            draw.arc((910 - radius, 390 - radius, 910 + radius, 390 + radius), 210, 330, fill=(87, 218, 239, 220), width=8)
        pen_x = 690 + int(progress * 430)
        draw.rounded_rectangle((pen_x - 210, 445, pen_x + 200, 510), radius=30, fill=(115, 128, 136, 255), outline=pale, width=5)
        draw.polygon(((pen_x + 200, 445), (pen_x + 300, 478), (pen_x + 200, 510)), fill=(209, 202, 180, 255), outline=pale)
        draw.polygon(((pen_x - 45, 448), (pen_x + 18, 448), (pen_x + 62, 510), (pen_x - 72, 510)), fill=(239, 87, 74, 235))
        for spark_idx in range(7):
            spark_x = 1080 + int(28 * math.sin(t_sub * 6 + spark_idx))
            spark_y = 475 + spark_idx * 20
            draw.line((spark_x, spark_y, spark_x + 22, spark_y - 18), fill=(255, 218, 119, 255), width=5)
        draw.text((660, 300), "OVER-ENGINEERED. STILL A PEN.", font=get_pop_font(42), fill=accent)

    elif family == "cost":
        draw.rounded_rectangle((480, 285, 1370, 870), radius=26, fill=(229, 222, 199, 255), outline=accent, width=8)
        file_caption = "FICTIONAL CONTRACT FILE" if fictional else "ENGINEERING TRADE-OFF FILE"
        draw.text((585, 345), file_caption, font=get_font_safe(38, bold=True), fill=(42, 53, 56, 255))
        for row in range(5):
            width = 620 - row * 45 + int(25 * math.sin(t_sub * 3 + row))
            y = 440 + row * 64
            draw.rounded_rectangle((590, y, 590 + width, y + 19), radius=8, fill=(92, 104, 104, 255))
        stamp_x = 1125 + int(14 * math.sin(t_sub * 4))
        draw.rounded_rectangle((stamp_x - 155, 665, stamp_x + 155, 765), radius=12, fill=(157, 45, 39, 235), outline=(255, 219, 190, 255), width=5)
        draw.text((stamp_x - 123, 690), "MORE PAPERWORK", font=get_font_safe(26, bold=True), fill=pale)
        draw.ellipse((380, 720, 660, 1000), fill=(196, 153, 68, 255), outline=(255, 224, 147, 255), width=10)
        draw.text((458, 804), "?", font=get_pop_font(120), fill=(58, 53, 44, 255))

    else:
        for ray_idx in range(14):
            angle = math.tau * ray_idx / 14 + t_sub * 0.4
            x0, y0 = 960 + int(math.cos(angle) * 140), 510 + int(math.sin(angle) * 120)
            x1, y1 = 960 + int(math.cos(angle) * (260 + 22 * pulse)), 510 + int(math.sin(angle) * (225 + 20 * pulse))
            draw.line((x0, y0, x1, y1), fill=accent, width=9)
        draw.text((885, 405), "!", font=get_pop_font(230), fill=pale, stroke_width=5, stroke_fill=(24, 36, 43, 255))
        draw.text((600, 740), "THAT ESCALATED QUICKLY", font=get_pop_font(45), fill=accent)

    scene_label = (
        "SATIRICAL RE-CREATION"
        if scene_data.get("fictional_satire")
        else "ILLUSTRATIVE RE-CREATION"
    )
    # Elegant top-left documentary badge to keep bottom area 100% clean for subtitles
    draw.rounded_rectangle((56, 38, 480, 78), radius=10, fill=(10, 18, 26, 220), outline=(195, 204, 207, 160), width=1)
    draw.text((72, 48), scene_label, font=get_font_safe(18, mono=True), fill=pale)

    if scene_data.get("character_active") and scene_data.get("character_dialogue"):
        actor = speaker_img.copy()
        actor.thumbnail((250, 340), Image.Resampling.LANCZOS)
        on_left = str(scene_data.get("character_position") or "bottom_right").endswith("left")
        actor_x = 72 if on_left else W - actor.width - 72
        frame.alpha_composite(actor, (actor_x, H - actor.height - 105))
        bubble = str(scene_data["character_dialogue"]).strip()
        bubble_box = (340, 150, 790, 294) if on_left else (W - 800, 150, W - 350, 294)
        draw.rounded_rectangle(bubble_box, radius=22, fill=(247, 247, 235, 250), outline=accent, width=4)
        for line_idx, line in enumerate(textwrap.wrap(bubble, width=24)[:2]):
            draw.text((bubble_box[0] + 24, bubble_box[1] + 34 + line_idx * 48), line, font=get_pop_font(32), fill=(24, 35, 43, 255))


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
    if shot_type.startswith("CRAYON_STORY_"):
        render_crayon_story_shot(frame, draw, scene_data, shot_type, t_sub, duration, speaker_img)
        return

    is_finance = topic_category in ("crayon_capital", "tech_finance_essay")
    accent = (255, 190, 55) if is_finance else (69, 211, 190)
    pale = (235, 243, 250)
    muted = (145, 164, 184)
    progress = min(1.0, max(0.0, t_sub / max(duration, 0.1)))
    chapter = str(scene_data.get("chapter") or "THE QUESTION").strip()
    visual = scene_data.get("visual") or {}
    primary_asset = visual.get("primary_asset") or {}
    b_roll = visual.get("b_roll") or {}
    primary_kind = _crayon_visual_kind(primary_asset.get("asset_id"), primary_asset.get("type"))
    b_roll_kind = _crayon_visual_kind(b_roll.get("asset_id"), b_roll.get("source"))
    asset_variant = sum(ord(char) for char in str(primary_asset.get("asset_id") or "")) % 5
    callout = str(b_roll.get("text_badge") or primary_asset.get("highlight") or "").strip()
    callout = " ".join(callout.split()[:7]).upper()
    source_refs = scene_data.get("source_refs") or []
    sources = scene_data.get("sources") or []
    source = next((item for item in sources if item.get("source_id") in source_refs), {})
    heading_font = get_font_safe(31, mono=True)
    phrase_font = get_pop_font(52)

    draw.rectangle((50, 45, W - 50, H - 45), fill=(12, 20, 34, 255), outline=(56, 73, 93), width=2)
    draw.text((94, 78), chapter[:48].upper(), font=heading_font, fill=accent)
    draw.line((90, 132, W - 90, 132), fill=(54, 70, 89), width=2)
    draw.text((W - 330, 78), "ILLUSTRATIVE", font=get_font_safe(19, mono=True), fill=muted)
    if source:
        draw.text(
            (95, 153),
            f"SOURCE: {str(source.get('name') or '').upper()[:72]}",
            font=get_font_safe(18, mono=True),
            fill=muted,
        )

    if shot_type == "CRAYON_HOOK":
        # A moving, generic illustration opens the story without inventing a real event.
        center_x, center_y = 860, 510
        sway = int(34 * math.sin(t_sub * 2.8))
        if primary_kind in {"document", "chart"}:
            draw.rounded_rectangle((360, 255, 1370, 720), radius=12, fill=(231, 237, 240), outline=accent, width=5)
            heading = "SOURCE DATA RECORD" if primary_kind == "chart" else "SOURCE DOCUMENT"
            draw.text((420, 310), heading, font=heading_font, fill=(39, 54, 68))
            draw.line((420, 365, 1300, 365), fill=(99, 116, 131), width=3)
            for row in range(3 + asset_variant % 3):
                y = 425 + row * 58
                draw.rounded_rectangle((420, y, 420 + int(600 + 180 * progress), y + 12), radius=6, fill=(103, 119, 133))
        elif primary_kind == "marker":
            pencil_x = center_x + sway
            draw.rounded_rectangle((pencil_x - 360, center_y - 70, pencil_x + 250, center_y + 70), radius=52, fill=(46, 107, 120), outline=accent, width=6)
            draw.polygon([(pencil_x + 250, center_y - 70), (pencil_x + 390, center_y), (pencil_x + 250, center_y + 70)], fill=(208, 199, 163), outline=accent)
            draw.ellipse((pencil_x + 325, center_y + 62, pencil_x + 355, center_y + 110), fill=(239, 128, 85), outline=accent, width=3)
            for stripe in range(1 + asset_variant):
                stripe_x = pencil_x - 250 + stripe * 88
                draw.line((stripe_x, center_y - 48, stripe_x, center_y + 48), fill=pale, width=3)
        elif primary_kind == "aircraft":
            points = [(center_x - 330 + sway, center_y), (center_x - 60 + sway, center_y - 45), (center_x + 15 + sway, center_y - 230), (center_x + 110 + sway, center_y - 230), (center_x + 85 + sway, center_y - 50), (center_x + 330 + sway, center_y - 5), (center_x + 330 + sway, center_y + 42), (center_x + 74 + sway, center_y + 22), (center_x + 22 + sway, center_y + 190), (center_x - 55 + sway, center_y + 190), (center_x - 100 + sway, center_y + 15), (center_x - 330 + sway, center_y + 42)]
            draw.polygon(points, fill=(48, 76, 98), outline=accent)
            draw.line((center_x - 410, center_y + 230, center_x + 400, center_y + 230), fill=(95, 120, 139), width=3)
            for rivet in range(3 + asset_variant):
                rivet_x = center_x - 170 + rivet * 65
                draw.ellipse((rivet_x - 5, center_y - 12, rivet_x + 5, center_y - 2), fill=pale)
        else:
            radius = 130 + int(18 * math.sin(t_sub * 3))
            draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline=accent, width=8)
            draw.ellipse((center_x - 55, center_y - 55, center_x + 55, center_y + 55), fill=(48, 76, 98), outline=pale, width=5)
            tooth_count = 6 + asset_variant
            for tooth in range(tooth_count):
                angle = math.pi * 2 * tooth / tooth_count + t_sub * 0.2
                x0 = center_x + int(math.cos(angle) * 60)
                y0 = center_y + int(math.sin(angle) * 60)
                x1 = center_x + int(math.cos(angle) * radius)
                y1 = center_y + int(math.sin(angle) * radius)
                draw.line((x0, y0, x1, y1), fill=accent, width=8)
        if callout:
            draw.text((120, 760), callout, font=phrase_font, fill=pale)
        pulse = int(15 + 12 * abs(math.sin(t_sub * 4)))
        draw.ellipse((center_x + 365 - pulse, center_y - 320 - pulse, center_x + 365 + pulse, center_y - 320 + pulse), outline=accent, width=5)
    elif shot_type == "CRAYON_VISUAL":
        center_x, center_y = 900, 520
        sway = int(25 * math.sin(t_sub * 2.5))
        if primary_kind == "timeline":
            points = [(245, 560), (1640, 560)]
            draw.line(points, fill=accent, width=8)
            marker_count = 4 + asset_variant
            for marker in range(marker_count):
                x_pos = 270 + marker * (1370 // (marker_count - 1))
                radius = 18 + int(5 * abs(math.sin(t_sub * 3 + marker)))
                draw.ellipse((x_pos - radius, 560 - radius, x_pos + radius, 560 + radius), fill=pale, outline=accent, width=4)
        elif primary_kind == "component":
            draw.ellipse((center_x - 310 + sway, center_y - 150, center_x - 10 + sway, center_y + 150), outline=accent, width=8)
            draw.ellipse((center_x + 110 + sway, center_y - 150, center_x + 410 + sway, center_y + 150), outline=pale, width=8)
            draw.line((center_x - 5 + sway, center_y, center_x + 105 + sway, center_y), fill=accent, width=12)
            for radius in (44, 82, 120):
                draw.arc((center_x - radius + sway, center_y - radius, center_x + radius + sway, center_y + radius), 20 + asset_variant * 6, 300 + asset_variant * 6, fill=muted, width=3)
            for tooth in range(5 + asset_variant):
                angle = math.pi * 2 * tooth / (5 + asset_variant) + t_sub * 0.2
                point_x = center_x + int(math.cos(angle) * 310) + sway
                point_y = center_y + int(math.sin(angle) * 150)
                draw.ellipse((point_x - 8, point_y - 8, point_x + 8, point_y + 8), fill=accent)
        elif primary_kind == "marker":
            pencil_x = center_x + sway
            draw.rounded_rectangle((pencil_x - 350, center_y - 70, pencil_x + 235, center_y + 70), radius=48, fill=(48, 101, 112), outline=accent, width=5)
            draw.polygon([(pencil_x + 235, center_y - 70), (pencil_x + 365, center_y), (pencil_x + 235, center_y + 70)], fill=(208, 199, 163), outline=accent)
            draw.line((pencil_x - 250, center_y - 52, pencil_x - 250, center_y + 52), fill=pale, width=4)
            for stripe in range(1 + asset_variant):
                stripe_x = pencil_x - 160 + stripe * 75
                draw.line((stripe_x, center_y - 45, stripe_x, center_y + 45), fill=pale, width=3)
        elif primary_kind == "document":
            draw.rounded_rectangle((520, 265, 1280, 730), radius=12, fill=(231, 237, 240), outline=accent, width=4)
            draw.text((590, 315), "SOURCE DOCUMENT", font=heading_font, fill=(39, 54, 68))
            draw.line((590, 370, 1210, 370), fill=(99, 116, 131), width=3)
            for row in range(5):
                reveal = max(90, min(520, int(140 + 380 * progress - row * 45)))
                draw.rounded_rectangle((590, 420 + row * 44, 590 + reveal, 432 + row * 44), radius=6, fill=(103, 119, 133))
        elif primary_kind == "aircraft":
            points = [(center_x - 350 + sway, center_y), (center_x - 60 + sway, center_y - 48), (center_x + 10 + sway, center_y - 230), (center_x + 110 + sway, center_y - 230), (center_x + 82 + sway, center_y - 45), (center_x + 350 + sway, center_y), (center_x + 82 + sway, center_y + 36), (center_x + 22 + sway, center_y + 188), (center_x - 58 + sway, center_y + 188), (center_x - 98 + sway, center_y + 36)]
            draw.polygon(points, fill=(48, 76, 98), outline=accent)
            draw.ellipse((center_x - 280 + sway, center_y + 90, center_x - 200 + sway, center_y + 170), outline=pale, width=5)
            draw.ellipse((center_x + 200 + sway, center_y + 90, center_x + 280 + sway, center_y + 170), outline=pale, width=5)
        elif primary_kind == "vehicle":
            draw.rounded_rectangle((center_x - 350 + sway, center_y - 30, center_x + 330 + sway, center_y + 160), radius=42, fill=(65, 80, 70), outline=accent, width=6)
            draw.rectangle((center_x - 170 + sway, center_y - 140, center_x + 160 + sway, center_y + 5), fill=(83, 101, 87), outline=accent, width=5)
            draw.line((center_x + sway, center_y - 88, center_x + 350 + sway, center_y - 88), fill=pale, width=18)
            for wheel_idx in range(4 + asset_variant):
                wheel_x = center_x - 230 + sway + wheel_idx * (460 // max(1, 3 + asset_variant))
                draw.ellipse((wheel_x - 42, center_y + 110, wheel_x + 42, center_y + 190), fill=(22, 30, 31), outline=accent, width=4)
        else:
            left_x, right_x = 480, 1390
            for x_pos, color in ((left_x, accent), (right_x, pale)):
                draw.rounded_rectangle((x_pos - 240, 370, x_pos + 240, 665), radius=25, fill=(21, 35, 51), outline=color, width=5)
                draw.line((x_pos - 165, 445, x_pos + 165, 445), fill=color, width=8)
                draw.line((x_pos - 125, 515, x_pos + 125, 515), fill=muted, width=6)
                draw.line((x_pos - 80, 585, x_pos + 80, 585), fill=muted, width=6)
            draw.line((left_x + 255, 520, right_x - 255, 520), fill=accent, width=10)
            arrow_x = int(left_x + 255 + progress * (right_x - left_x - 510))
            draw.ellipse((arrow_x - 15, 505, arrow_x + 15, 535), fill=pale)
        if callout:
            draw.text((170, 770), callout, font=phrase_font, fill=accent)
    elif shot_type == "CRAYON_EVIDENCE":
        draw.rounded_rectangle((220, 220, 1310, 780), radius=10, fill=(231, 237, 240), outline=accent, width=4)
        if primary_kind == "comparison":
            draw.text((280, 265), "DOCUMENTED TRADE-OFF", font=heading_font, fill=(39, 54, 68))
            for x_pos, color in ((430, accent), (1050, (83, 123, 150))):
                draw.rounded_rectangle((x_pos - 155, 400, x_pos + 155, 650), radius=18, fill=(216, 225, 230), outline=color, width=4)
                for row in range(3 + asset_variant % 3):
                    draw.line((x_pos - 90, 465 + row * 48, x_pos + 90, 465 + row * 48), fill=(99, 116, 131), width=5)
            draw.line((590, 525, 890, 525), fill=accent, width=8)
        else:
            draw.text((280, 265), "SOURCE DOCUMENT", font=heading_font, fill=(39, 54, 68))
            draw.line((280, 325, 1240, 325), fill=(99, 116, 131), width=3)
            source_name = str(source.get("name") or "PUBLIC SOURCE").upper()
            for line_no, line in enumerate(textwrap.wrap(source_name, width=43)[:2]):
                draw.text((290, 365 + line_no * 44), line, font=get_font_safe(28, bold=True), fill=(32, 46, 60))
            date_label = str(source.get("published_at") or "")
            if date_label:
                draw.text((290, 470), date_label[:20], font=get_font_safe(22, mono=True), fill=(67, 86, 103))
            for row in range(3):
                y = 545 + row * 50
                reveal = max(30, min(820, int((progress * 3 - row + 1) * 280)))
                draw.rounded_rectangle((290, y, 290 + reveal, y + 14), radius=6, fill=(103, 119, 133))
        if callout:
            draw.text((285, 725), callout, font=get_font_safe(27, bold=True), fill=(32, 46, 60))
    else:
        for ray_idx in range(8):
            angle = (math.pi * 2 * ray_idx / 8) + t_sub
            x_pos = 880 + int(math.cos(angle) * 255)
            y_pos = 520 + int(math.sin(angle) * 185)
            draw.ellipse((x_pos - 8, y_pos - 8, x_pos + 8, y_pos + 8), fill=accent)
        draw.text((610, 780), callout or "THE EVIDENCE", font=phrase_font, fill=pale)

    if b_roll_kind != primary_kind and b_roll_kind in {"marker", "document"}:
        draw.rounded_rectangle((105, 235, 345, 465), radius=18, fill=(19, 32, 48), outline=muted, width=3)
        if b_roll_kind == "marker":
            draw.rounded_rectangle((150, 320, 300, 370), radius=22, fill=(46, 107, 120), outline=accent, width=4)
            draw.polygon([(300, 320), (325, 345), (300, 370)], fill=(208, 199, 163), outline=accent)
        elif b_roll_kind == "document":
            draw.rectangle((165, 275, 285, 425), fill=(231, 237, 240), outline=accent, width=3)
            for row in range(4):
                draw.line((180, 305 + row * 25, 270, 305 + row * 25), fill=(99, 116, 131), width=3)

    if scene_data.get("character_active") and scene_data.get("character_dialogue"):
        actor = speaker_img.copy()
        actor.thumbnail((270, 360), Image.Resampling.LANCZOS)
        position = str(scene_data.get("character_position") or "bottom_right")
        on_left = position.endswith("left")
        actor_x = 90 if on_left else W - actor.width - 90
        actor_y = H - actor.height - 220
        frame.alpha_composite(actor, (actor_x, actor_y))
        bubble = str(scene_data["character_dialogue"]).strip()
        bubble_box = (380, 185, 840, 345) if on_left else (W - 850, 185, W - 390, 345)
        draw.rounded_rectangle(bubble_box, radius=24, fill=(241, 245, 249, 248), outline=accent, width=4)
        bubble_lines = textwrap.wrap(bubble, width=25)[:2]
        bubble_font = get_pop_font(36)
        for line_no, line in enumerate(bubble_lines):
            draw.text((bubble_box[0] + 28, bubble_box[1] + 42 + line_no * 52), line, font=bubble_font, fill=(26, 40, 52))
        draw.polygon([(bubble_box[2] - 24, bubble_box[3] - 8), (bubble_box[2] + 28, bubble_box[3] + 30), (bubble_box[2] - 80, bubble_box[3] - 8)], fill=(241, 245, 249, 248), outline=accent)


def mix_scene_audio(narration_wav: Path, sfx_events: list, output_wav: Path, speaker_side: str = "CENTER"):
    dur = get_audio_duration(str(narration_wav))
    fade_out_st = max(0.0, dur - 0.035)
    pan_str = f"pan=stereo|c0=0.707*c0|c1=0.707*c0,afade=t=in:ss=0:d=0.035,afade=t=out:st={fade_out_st:.3f}:d=0.035"
    valid_sfx = [(p, d, v) for p, d, v in sfx_events if p.exists()]
    if not valid_sfx:
        cmd = [FFMPEG_BIN, "-y", "-i", str(narration_wav), "-af", pan_str, "-c:a", "pcm_s16le", str(output_wav)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Crayon audio mix failed: {result.stderr[-2000:]}")
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Crayon SFX mix failed: {result.stderr[-2000:]}")


def _get_aviation_speech_bubble(scene_data: dict, sub_type: str, s_i: int) -> Optional[Tuple[str, str, tuple, str]]:
    if s_i not in (0, 1):
        return None
    # Speech bubbles only belong on character/cockpit/tower dialogue shots, not technical specification blueprints
    if sub_type not in ("AVIATION_COCKPIT_CVR", "AVIATION_ATC_TOWER", "AVIATION_CVR_TRANSCRIPT"):
        return None

    narr = str(scene_data.get("narration") or "").lower()
    ch = str(scene_data.get("chapter") or "").lower()
    text = f"{narr} {ch}"
    inc = resolve_aviation_incident(text, vehicle_name=str(scene_data.get("vehicle_name") or ""))

    triggers = inc.get("speech_bubble_triggers", [])
    for item in triggers:
        if len(item) == 5:
            kw_list, quote, side, col, badge = item
        else:
            kw_list, quote, side, col = item
            badge = ""
        if any(w in text for w in kw_list):
            badge_upper = badge.upper()
            # STRICT Character matching: Tower controller must never shout pilot panics!
            if sub_type == "AVIATION_ATC_TOWER" and ("TOWER" not in badge_upper and "ATC" not in badge_upper):
                continue
            if sub_type == "AVIATION_COCKPIT_CVR" and ("TOWER" in badge_upper or "ATC" in badge_upper):
                continue
            return (quote, side, col, badge)

    return None


def _get_punchy_speech_bubble(scene_data: dict, sub_type: str, s_i: int) -> Optional[tuple]:
    if s_i not in (0, 1):
        return None
    if is_aviation_context(scene_data, "", ""):
        return _get_aviation_speech_bubble(scene_data, sub_type, s_i)
    narr = str(scene_data.get("narration") or "").lower()
    ch = str(scene_data.get("chapter") or "").lower()
    text = f"{narr} {ch}"
    
    if sub_type == "AVIATION_COCKPIT_CVR":
        return ("DUAL FLAMEOUT!", "right", (220, 38, 38))
    if sub_type == "AVIATION_MAINTENANCE_BLUNDER":
        return ("WRONG GAUGE!", "left", (220, 38, 38))
    if sub_type == "AVIATION_ATC_TOWER":
        return ("MAYDAY RECEIVED!", "left", (234, 179, 8))
    if sub_type == "AVIATION_INVESTIGATION_FDR":
        return ("1,800 KG GHOST FUEL!", "left", (220, 38, 38))
    if sub_type == "FLIR_BAKERY_INCIDENT":
        return ("IT'S A BAKERY!", "right", (220, 38, 38))
    if sub_type == "ROBOT_DOG":
        return ("TANGLED IN WIRE!", "left", (220, 38, 38))
    if sub_type == "SYMBOL_X":
        return ("ROOM CLEARED!", "left", (34, 197, 94))
    if sub_type == "SYMBOL_SLASH":
        return ("SEARCH IN PROGRESS!", "left", (234, 179, 8))
    if sub_type == "PENTAGON_AUDIT":
        return ("AUDIT REJECTED!", "right", (220, 38, 38))
    if sub_type == "SPLIT_CIVIL" and s_i == 0:
        return ("$4,800 FOR WAX?!", "left", (220, 38, 38))
    if sub_type == "EMERGENCY_LOCKDOWN":
        return ("IT MELTED!", "left", (220, 38, 38))
    if sub_type == "EXPLODED_PATENT":
        return ("OVER-ENGINEERED!", "left", (220, 38, 38))
    if sub_type == "FOREIGN_INTEL_DOSSIER":
        return ("ZERO DEFENSE VALUE!", "right", (234, 179, 8))
    if sub_type == "TANK_SIGHT":
        return ("SIGHTS OVERHEATING!", "right", (220, 38, 38))
    if "freeze" in text and sub_type in ("MACRO_BLUEPRINT", "TACTICAL_MAP"):
        return ("THE INK FROZE!", "left", (56, 189, 248))
    if "red lighting" in text and sub_type in ("COCKPIT_HUD", "EMERGENCY_LOCKDOWN"):
        return ("IT'S INVISIBLE!", "right", (220, 38, 38))
    return None


def draw_punchy_speech_bubble(frame: Image.Image, draw: ImageDraw.ImageDraw, bubble_info: tuple, sub_type: str):
    if len(bubble_info) == 4:
        text, side, text_color, speaker_badge = bubble_info
    else:
        text, side, text_color = bubble_info[:3]
        speaker_badge = ""

    bubble_font = get_pop_font(27)
    badge_font = get_font_safe(14, bold=True)
    
    bbox = bubble_font.getbbox(text)
    tw = bbox[2] - bbox[0]
    bw = max(320, tw + 50)
    bh = 85 if speaker_badge else 80

    is_atc_scene = (sub_type == "AVIATION_ATC_TOWER")
    is_tower_speaking = any(k in speaker_badge.upper() for k in ("ATC", "TOWER", "CONTROLLER"))

    if is_atc_scene and not is_tower_speaking:
        rx_w = max(420, tw + 70)
        rx_h = 95
        rx_x = W - rx_w - 70
        rx_y = 170
        draw.rounded_rectangle([(rx_x, rx_y), (rx_x + rx_w, rx_y + rx_h)], radius=14, fill=(15, 23, 42, 245), outline=text_color, width=2)
        draw.rounded_rectangle([(rx_x, rx_y), (rx_x + rx_w, rx_y + 34)], radius=14, fill=(30, 41, 59))
        draw.rectangle([(rx_x, rx_y + 20), (rx_x + rx_w, rx_y + 34)], fill=(30, 41, 59))
        draw.ellipse([(rx_x + 14, rx_y + 11), (rx_x + 26, rx_y + 23)], fill=(239, 68, 68))
        badge_title = f"📻 INCOMING RADIO // {speaker_badge.upper()}" if speaker_badge else "📻 INCOMING RADIO TRANSMISSION"
        draw.text((rx_x + 34, rx_y + 8), badge_title[:45], font=badge_font, fill=(56, 189, 248))
        draw.text((rx_x + 20, rx_y + 46), f'"{text}"', font=bubble_font, fill=text_color)
        return

    if side == "left":
        bx = 240
        by = 690 if is_atc_scene else H - 540
        draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=18, fill=(255, 255, 255), outline=(15, 23, 42), width=3)
        draw.polygon([(bx + 30, by + bh - 2), (bx + 10, by + bh + 24), (bx + 55, by + bh - 2)], fill=(255, 255, 255))
        draw.line([(bx + 30, by + bh - 2), (bx + 10, by + bh + 24), (bx + 55, by + bh - 2)], fill=(15, 23, 42), width=3)
        
        if speaker_badge:
            badge_bbox = badge_font.getbbox(speaker_badge)
            badge_w = badge_bbox[2] - badge_bbox[0] + 18
            draw.rounded_rectangle([(bx + 16, by - 12), (bx + 16 + badge_w, by + 14)], radius=6, fill=(15, 23, 42))
            draw.text((bx + 25, by - 10), speaker_badge, font=badge_font, fill=(56, 189, 248))
            draw.text((bx + 25, by + 28), text, font=bubble_font, fill=text_color)
        else:
            draw.text((bx + 25, by + 22), text, font=bubble_font, fill=text_color)
    else:
        bx = W - bw - 240
        by = H - 540
        draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=18, fill=(255, 255, 255), outline=(15, 23, 42), width=3)
        draw.polygon([(bx + bw - 55, by + bh - 2), (bx + bw - 15, by + bh + 24), (bx + bw - 35, by + bh - 2)], fill=(255, 255, 255))
        draw.line([(bx + bw - 55, by + bh - 2), (bx + bw - 15, by + bh + 24), (bx + bw - 35, by + bh - 2)], fill=(15, 23, 42), width=3)
        
        if speaker_badge:
            badge_bbox = badge_font.getbbox(speaker_badge)
            badge_w = badge_bbox[2] - badge_bbox[0] + 18
            draw.rounded_rectangle([(bx + 16, by - 12), (bx + 16 + badge_w, by + 14)], radius=6, fill=(15, 23, 42))
            draw.text((bx + 25, by - 10), speaker_badge, font=badge_font, fill=(56, 189, 248))
            draw.text((bx + 25, by + 28), text, font=bubble_font, fill=text_color)
        else:
            draw.text((bx + 25, by + 22), text, font=bubble_font, fill=text_color)


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

    if scene_data.get("_structured_timeline"):
        for cue_idx, cue_name in enumerate(scene_data.get("sfx") or []):
            cue_file = SFX_DIR / SFX_ASSETS[cue_name]
            if not cue_file.is_file():
                raise FileNotFoundError(f"Required Crayon SFX asset not found: {cue_file}")
            cue_delay = min(0.12 + 0.35 * cue_idx, max(0.12, dur - 0.2))
            sfx_events.append((cue_file, cue_delay, 0.26))
        visual_sfx = {
            "CRAYON_STORY_COCKPIT": "warning_beep",
            "CRAYON_STORY_WAX": "marker_scribble",
            "CRAYON_STORY_TANK": "radio_click",
            "CRAYON_STORY_MARKING": "marker_scribble",
            "CRAYON_STORY_LAB": "impact",
            "CRAYON_STORY_COST": "cash_register",
            "CRAYON_STORY_REACTION": "comic_boing",
        }
        for subshot_idx, subshot_type in enumerate(subshots):
            cue_name = visual_sfx.get(subshot_type)
            if cue_name:
                cue_file = SFX_DIR / SFX_ASSETS[cue_name]
                if not cue_file.is_file():
                    raise FileNotFoundError(f"Required Crayon SFX asset not found: {cue_file}")
                sfx_events.append((cue_file, min(0.35 + subshot_idx * sub_dur, dur - 0.1), 0.24))
            if subshot_idx:
                whoosh_file = SFX_DIR / SFX_ASSETS["whoosh"]
                if not whoosh_file.is_file():
                    raise FileNotFoundError(f"Required Crayon SFX asset not found: {whoosh_file}")
                sfx_events.append((whoosh_file, min(subshot_idx * sub_dur, dur - 0.1), 0.18))
    else:
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

    mixed_wav = wav_path.parent / f"mixed_{wav_path.stem}.wav"
    try:
        mix_scene_audio(wav_path, sfx_events, mixed_wav, speaker_side="CENTER")
    except Exception:
        if scene_data.get("_structured_timeline"):
            raise
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

    is_aviation = is_aviation_context(scene_data, vehicle_name=vehicle_name)
    inc = resolve_aviation_incident(str(scene_data.get("narration", "")) + " " + str(vehicle_name), vehicle_name=vehicle_name, title=str(scene_data.get("video_title") or "")) if is_aviation else None
    if is_aviation:
        captain_img = load_character_sprite("CAPTAIN", 580)
        fo_img = load_character_sprite("FIRST_OFFICER", 540)
        atc_img = load_character_sprite("ATC", 580)
        mechanic_img = load_character_sprite("MECHANIC", 580)
        ntsb_img = load_character_sprite("NTSB", 600)
    else:
        captain_img = pilot_img
        fo_img = pilot_img
        atc_img = general_img
        mechanic_img = founder_img
        ntsb_img = general_img

    # Topic-specific bespoke visual resolver
    topic_bg_file = None
    if scene_data.get("custom_image") and Path(str(scene_data["custom_image"])).is_file():
        topic_bg_file = Path(scene_data["custom_image"])
    elif scene_data.get("image_path") and Path(str(scene_data["image_path"])).is_file():
        topic_bg_file = Path(scene_data["image_path"])
    elif wav_path and wav_path.parent:
        m_dir = wav_path.parent
        for cand in [
            m_dir / "media" / f"scene_{idx:02d}_topic_bg.jpg",
            m_dir / "media" / f"scene_{idx:02d}_topic_bg.png",
            m_dir / "media" / f"scene_{idx}_topic_bg.jpg",
            m_dir / "media" / f"scene_{idx:02d}.jpg",
            m_dir / "media" / f"scene_{idx:02d}.png",
            m_dir / "images" / f"{idx}.jpg",
            m_dir / "images" / f"{idx}.png",
        ]:
            if cand.is_file() and cand.stat().st_size > 1000:
                topic_bg_file = cand
                break
    if topic_bg_file:
        scene_data["topic_bg"] = str(topic_bg_file)

    # Photos pool: STRICT segregation between Aviation documentaries and Military hardware
    if is_aviation and inc:
        photos_pool = []
        if topic_bg_file:
            photos_pool.append((topic_bg_file, f"DOCUMENTARY // {inc['flight_no']}", f"SECTOR: {inc['location'][:38]}", "OFFICIAL ARCHIVE"))

        cand_media_dirs = []
        if scene_data.get("_mat_dir"):
            cand_media_dirs.append(Path(scene_data["_mat_dir"]) / "media")
        if wav_path and wav_path.parent:
            cand_media_dirs.append(wav_path.parent / "media")
            if wav_path.parent.name == "temp_animated_scenes":
                cand_media_dirs.append(wav_path.parent.parent / "media")
                f_name = wav_path.parent.parent.name
                for b_root in [BASE_DIR, Path("/home/ubuntu/yt-remote-worker"), Path("/Users/alienes/yt-oto-video/files")]:
                    cand_media_dirs.append(b_root / "materials" / "blackboxaudioo" / f_name / "media")
                    cand_media_dirs.append(b_root / "output" / "blackboxaudioo" / "Üretim Metaryalleri" / f_name / "media")

        found_media_d = None
        for cmd_dir in cand_media_dirs:
            if cmd_dir.exists() and any(cmd_dir.glob("*.*")):
                found_media_d = cmd_dir
                break

        if found_media_d:
            for wp in sorted(found_media_d.glob("*wiki*.*")):
                if wp.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and wp.stat().st_size > 1000:
                    photos_pool.append((wp, f"HISTORICAL ARCHIVE // {inc['aircraft'][:32]}", f"RECORD: {inc['location'][:38]}", "OFFICIAL EVIDENCE"))
            if not photos_pool:
                for sp in sorted(found_media_d.glob("scene_*.*")):
                    if sp.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and not sp.name.endswith("_card.png") and not sp.name.endswith("_map.png") and not sp.name.endswith("_gauge.png") and sp.stat().st_size > 5000:
                        photos_pool.append((sp, f"DOCUMENTARY RECORD // {inc['flight_no']}", f"LOCATION: {inc['location'][:38]}", "ARCHIVAL EVIDENCE"))
        # Strict Aviation Barrier: Never load sci-fi cockpit or B-21 military hangar into aviation!
    else:
        photos_pool = [
            (B21_FLIGHT_REAL, "USAF FLIGHT TEST ARCHIVE // EDWARDS AFB", "AIRCRAFT: B-21 RAIDER SERIAL AF-21-001", "TOP SECRET"),
            (M1A2_ABRAMS_REAL, "US ARMY ARMORED CAVALRY // MAIN BATTLE TANK", "COMBAT VEHICLE: M1A2 ABRAMS 120mm SMOOTHBORE", "DECLASSIFIED"),
            (HUMVEE_ARCTIC_REAL, "NATO EXERCISE COLD RESPONSE // ARCTIC NORWAY", "TACTICAL CONVOY: HMMWV EXTREME SUB-ZERO (-30°C)", "FIELD REPORT"),
            (B21_ROLLOUT_REAL, "PALMDALE PLANT 42 ROLLOUT SPECIFICATION", "AUDIT: RADAR ABSORBENT COATING ADHESION", "DECLASSIFIED"),
            (F16_COCKPIT_REAL, "USAF TACTICAL AIR COMMAND // KNEEBOARD CHECK", "COCKPIT AVIONICS: F-16C MULTI-FUNCTION DISPLAY", "OPERATIONAL"),
            (B21_BLUEPRINT_IMG, "TECHNICAL BLUEPRINT DRAFTING ARCHIVE", "SCHEMATIC: MIL-STD 810H THERMAL SPEC", "SPEC FAILED"),
        ]
        if topic_bg_file:
            scene_caption = str(scene_data.get("chapter") or "TACTICAL ARCHIVE").upper()
            scene_sub = str(scene_data.get("narration") or vehicle_name)[:42].upper()
            photos_pool.insert(0, (topic_bg_file, f"DECLASS // {scene_caption}", f"REF: {scene_sub}", "TOP SECRET"))

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

        # Aviation Guardrail: Force complete segregation from any rogue combat subshots
        if is_aviation:
            combat_map = {
                "HANGAR_WALK": "AVIATION_COCKPIT_CVR",
                "PENTAGON_AUDIT": "AVIATION_INVESTIGATION_FDR",
                "LAB_RND": "AVIATION_MAINTENANCE_BLUNDER",
                "ROBOT_DOG": "AVIATION_RUNWAY_MAP",
                "TANK_SIGHT": "AVIATION_ATC_TOWER",
                "SYMBOL_X": "AVIATION_RUNWAY_MAP",
                "SYMBOL_SLASH": "AVIATION_ATC_TOWER",
                "SYMBOL_HAZARD": "AVIATION_CVR_TRANSCRIPT",
                "SYMBOL_TRIAGE": "AVIATION_CRM_DECISION",
                "SYMBOL_BREACH": "AVIATION_MAINTENANCE_BLUNDER",
                "BLUEPRINT_SYMBOL_HUD": "AVIATION_AIRCRAFT_PROFILE",
                "FINANCIAL_AUDIT": "AVIATION_CRM_DECISION",
                "CRT_MAINFRAME": "AVIATION_CVR_TRANSCRIPT",
                "SPLIT_CIVIL": "AVIATION_AIRCRAFT_PROFILE",
                "URBAN_STREET": "AVIATION_APPROACH_CHART",
                "FOREIGN_INTELLIGENCE": "AVIATION_INVESTIGATION_FDR",
                "COCKPIT_HUD": "AVIATION_COCKPIT_CVR",
                "EMERGENCY_LOCKDOWN": "AVIATION_RUNWAY_MAP",
                "TACTICAL_MAP": "AVIATION_APPROACH_CHART",
                "EDITORIAL_BRIEFING": "AVIATION_CVR_TRANSCRIPT",
                "KEN_BURNS": "AVIATION_AIRCRAFT_PROFILE",
                "DESK_BRIEFING": "AVIATION_CRM_DECISION",
                "MACRO_BLUEPRINT": "AVIATION_MAINTENANCE_BLUNDER",
                "TACTICAL_RADAR": "AVIATION_ATC_TOWER",
            }
            if sub_type in combat_map:
                sub_type = combat_map[sub_type]

        # Character poses: for aviation, enforce authentic pilot and NTSB inspector sprites
        if is_aviation:
            host_walk = captain_img
            host_point = ntsb_img
            host_shock = fo_img
            host_smug = captain_img
        else:
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
        elif sub_type == "AVIATION_COCKPIT_CVR":
            render_aviation_cockpit_cvr(frame, draw, t_sub, sub_title, captain_img, fo_img, scene_data, inc=inc)
        elif sub_type == "AVIATION_MAINTENANCE_BLUNDER":
            render_aviation_maintenance_blunder(frame, draw, t_sub, sub_title, mechanic_img, host_point, scene_data, inc=inc)
        elif sub_type == "AVIATION_ATC_TOWER":
            render_aviation_atc_tower(frame, draw, t_sub, sub_title, atc_img, scene_data, inc=inc)
        elif sub_type == "AVIATION_INVESTIGATION_FDR":
            render_aviation_investigation_fdr(frame, draw, t_sub, sub_title, ntsb_img, scene_data, inc=inc)
        elif sub_type == "AVIATION_RUNWAY_MAP":
            render_aviation_runway_map(frame, draw, t_sub, sub_title, scene_data, inc=inc)
        elif sub_type == "AVIATION_AIRCRAFT_PROFILE":
            render_aviation_aircraft_profile(frame, draw, t_sub, sub_title, scene_data, inc=inc)
        elif sub_type == "AVIATION_CVR_TRANSCRIPT":
            render_aviation_cvr_transcript(frame, draw, t_sub, sub_title, scene_data, inc=inc)
        elif sub_type == "AVIATION_CRM_DECISION":
            render_aviation_crm_decision_tree(frame, draw, t_sub, sub_title, scene_data, inc=inc)
        elif sub_type == "AVIATION_APPROACH_CHART":
            render_aviation_approach_chart(frame, draw, t_sub, sub_title, scene_data, inc=inc)
        elif sub_type == "AVIATION_HISTORICAL_ARCHIVE":
            p_tuple = None
            if photos_pool:
                # Prioritize exact scene asset match (e.g., scene_04_wiki_... for idx=4)
                exact_matches = [p for p in photos_pool if f"scene_{idx:02d}" in str(p[0]) or f"scene_{idx}_" in str(p[0])]
                if exact_matches:
                    p_tuple = exact_matches[0]
                else:
                    p_tuple = photos_pool[(idx + s_i) % len(photos_pool)]
            render_aviation_historical_archive(frame, draw, t_sub, sub_title, scene_data, inc=inc, photo_tuple=p_tuple)
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
            p_tuple = photos_pool[0] if (topic_bg_file and s_i == 0) else photos_pool[(idx + s_i) % len(photos_pool)]
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

        # Character punchy comic reaction bubble
        bubble_info = _get_punchy_speech_bubble(scene_data, sub_type, s_i)
        if bubble_info and 0.5 <= t_sub <= (sub_dur - 0.4):
            draw_punchy_speech_bubble(frame, draw, bubble_info, sub_type)

        # Narration captions: When ASS subtitles are burned in post-production, DO NOT draw PIL subtitles!
        burn_ass = scene_data.get("burn_ass_subtitles", True)
        narr_str = scene_data.get("narration", "")
        if narr_str and not burn_ass and not scene_data.get("_structured_timeline"):
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
Style: CrayonDoc,Arial,36,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.2,1.2,2,60,60,42,1
Style: CrayonSpeaker,Arial,28,&H001ED760,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.8,1.0,2,60,60,110,1

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
        # Single-line responsive chunking: max 4 words or max 30 characters
        chunks = []
        cur = []
        for w in words:
            if len(cur) >= 4 or (sum(len(x) for x in cur) + len(w) + len(cur)) > 30:
                if cur:
                    chunks.append(" ".join(cur))
                    cur = []
            cur.append(w)
        if cur:
            chunks.append(" ".join(cur))
        if not chunks:
            chunks = [narration]

        chunk_dur = dur / float(len(chunks))

        for c_idx, chunk in enumerate(chunks):
            st = current_time + (c_idx * chunk_dur)
            et = st + chunk_dur
            st_str = format_ass_time(st)
            et_str = format_ass_time(et)

            text_clean = chunk.replace('"', '\"').upper()
            text_styled = f"{{\\fade(80,80)}}{text_clean}"
            events.append(f"Dialogue: 0,{st_str},{et_str},CrayonDoc,,0,0,0,,{text_styled}")

        current_time += dur

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))


def _render_single_scene_task(args):
    sc, wav_path, scene_mp4, vehicle_name, idx, total_scenes, chan_id, topic_category = args
    set_current_channel_id(chan_id, topic_category)
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
    topic_category = str(mat_data.get("topic_category") or "").lower()
    set_current_channel_id(chan_id, topic_category)

    scenes = mat_data.get("scenes") or (mat_data.get("script", {}).get("scenes") if isinstance(mat_data.get("script"), dict) else [])
    vehicle_name = mat_data.get("vehicle_name") or mat_data.get("flight_name") or mat_data.get("title") or "Commercial Flight"
    total_scenes = len(scenes)

    print(f"🎬 [Bespoke Non-Repeating Documentary Engine] '{mat_data.get('title', 'Video')}' starting 16-archetype non-repeating production ({total_scenes} sahne)...")

    # Ensure TTS generator is ready for missing scene audio
    tts_gen = None
    lang = mat_data.get("language") or "en"

    video_title_str = str(mat_data.get("title") or mat_dir.name or "")
    total_vid_dur = 0.0
    tasks = []
    for idx, sc in enumerate(scenes):
        sc["_mat_dir"] = str(mat_dir)
        sc["video_title"] = video_title_str
        scene_mp4 = temp_dir / f"scene_{idx:02d}_anim.mp4"
        wav_path = mat_dir / f"scene_{idx}_audio.wav"
        if not wav_path.exists():
            wav_path = mat_dir / f"scene_{idx+1:02d}.wav"
        if not wav_path.exists():
            wav_path = mat_dir / f"scene_{idx}_kokoro.wav"
        if not wav_path.exists():
            wav_path = mat_dir / f"scene_{idx}_audio.mp3"
        if not wav_path.exists():
            # Generate missing audio (Kokoro-TTS native or Edge-TTS fallback)
            wav_fallback = temp_dir / f"scene_{idx}_tts.wav"
            if not wav_fallback.exists() or wav_fallback.stat().st_size < 1000:
                narration = sc.get("narration") or sc.get("text") or vehicle_name
                generated = False
                try:
                    from kokoro_onnx import Kokoro
                    import soundfile as sf
                    k_paths = [
                        BASE_DIR / "models" / "kokoro",
                        Path("/home/ubuntu/yt-remote-worker/models/kokoro"),
                    ]
                    for kp in k_paths:
                        m_p = kp / "kokoro-v1.0.onnx"
                        v_p = kp / "voices-v1.0.bin"
                        if m_p.exists() and v_p.exists():
                            k_inst = Kokoro(str(m_p), str(v_p))
                            k_voice = "am_michael" if lang == "en" else "af_sarah"
                            samples, sample_rate = k_inst.create(narration, voice=k_voice, speed=1.05, lang="en-us")
                            sf.write(str(wav_fallback), samples, sample_rate)
                            generated = True
                            break
                except Exception as k_err:
                    pass

                if not generated:
                    if tts_gen is None:
                        try:
                            from video_generator import AudioGenerator
                            tts_gen = AudioGenerator()
                        except ImportError:
                            try:
                                from src.video_generator import AudioGenerator
                                tts_gen = AudioGenerator()
                            except ImportError:
                                tts_gen = None
                    if tts_gen:
                        tts_gen.generate_sync(narration, lang, str(wav_fallback))

            if wav_fallback.exists():
                wav_path = wav_fallback

        dur = get_audio_duration(str(wav_path)) if wav_path.exists() else 5.0
        total_vid_dur += dur
        tasks.append((sc, wav_path, scene_mp4, vehicle_name, idx, total_scenes, chan_id, topic_category))

    print(f"⏱️ Total Video Duration: {total_vid_dur:.1f}s ({total_vid_dur/60.0:.2f} dakika)")

    from concurrent.futures import ThreadPoolExecutor
    workers = min(4, os.cpu_count() or 2)
    print(f"🚀 Multithreaded scene rendering enabled ({workers} concurrent workers)...")
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for res in executor.map(_render_single_scene_task, tasks):
            results.append(res)

    results.sort(key=lambda x: x[0])
    rendered_scene_mp4s = [r[1] for r in results]

    # Concat
    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in rendered_scene_mp4s:
            f.write(f"file '{p.resolve()}'\n")

    # Direct Stream Concat with Background Music Mix (bgm_timeline & Smart BGM Selection)
    bgm_timeline = mat_data.get("bgm_timeline") or (mat_data.get("script", {}).get("bgm_timeline") if isinstance(mat_data.get("script"), dict) else None)
    timeline_mixed_bgm = None
    if bgm_timeline and isinstance(bgm_timeline, list) and len(bgm_timeline) > 0:
        try:
            try:
                from audio_library import build_timeline_bgm_track
            except ImportError:
                from src.audio_library import build_timeline_bgm_track
            timeline_mixed_bgm = build_timeline_bgm_track(
                bgm_timeline=bgm_timeline,
                total_duration=total_vid_dur,
                work_dir=temp_dir,
                base_volume=0.08
            )
        except Exception as b_err:
            print(f"[CRAYON-RENDER] bgm_timeline derleme hatası: {b_err}")

    if timeline_mixed_bgm and timeline_mixed_bgm.is_file():
        bgm_path = timeline_mixed_bgm
        bgm_filter_vol = "1.0"
        print(f"🎵 [BGM-TIMELINE] Çoklu telifsiz müzik akışı başarıyla bağlandı: {bgm_path.name}")
    else:
        req_track = mat_data.get("bgm_track") or (mat_data.get("script", {}).get("bgm_track") if isinstance(mat_data.get("script"), dict) else None)
        bgm_path = None
        if req_track:
            try:
                try:
                    from audio_library import download_track
                except ImportError:
                    from src.audio_library import download_track
                bgm_path = download_track(req_track, BASE_DIR / "assets/music")
            except Exception:
                pass

        if not bgm_path or not bgm_path.exists():
            if topic_category == "aviation" or chan_id == "blackboxaudioo":
                candidates = ["borderless.mp3", "underworld.mp3", "dramatic_suspense.mp3", "space_walk.mp3"]
            elif topic_category == "defense_finance" or chan_id == "tacticallcrayon":
                candidates = ["schizo.mp3", "sneaky_snitch.mp3", "desert_caravan.mp3", "action_tense.mp3"]
            else:
                candidates = ["lofi_storyteller.mp3", "reddit_official_bgm.mp3", "sunny_days.mp3"]

            for c in candidates:
                p = BASE_DIR / "assets/music" / c
                if p.exists():
                    bgm_path = p
                    break

        if not bgm_path or not bgm_path.exists():
            bgm_candidates = list((BASE_DIR / "assets/music").glob("*.mp3")) if (BASE_DIR / "assets/music").exists() else []
            bgm_path = bgm_candidates[0] if bgm_candidates else None

        bgm_filter_vol = "0.08"
        if bgm_path:
            print(f"🎵 [BGM] Tekli fon müziği seçildi: {bgm_path.name} (Vol={bgm_filter_vol})")

    # Generate single-layer broadcast ASS subtitles
    ass_file = temp_dir / "subtitles.ass"
    generate_broadcast_ass_subtitles(scenes, mat_dir, ass_file)

    final_output = dest_dir / "final.mp4"
    print("🎵 Mixing audio, SFX, background music, and burning broadcast subtitles into final cut...")

    if bgm_path and bgm_path.exists():
        cmd_final = [
            FFMPEG_BIN, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
            "-stream_loop", "-1", "-i", str(bgm_path),
            "-filter_complex", (
                f"[0:v]ass={str(ass_file)}[vout];"
                f"[1:a]volume={bgm_filter_vol}[bgm];"
                "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
            ),
            "-map", "[vout]",
            "-map", "[a_out]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(final_output)
        ]
    else:
        cmd_final = [
            FFMPEG_BIN, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
            "-vf", f"ass={str(ass_file)}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-c:a", "copy",
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
