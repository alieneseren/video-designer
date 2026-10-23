import math
import os
import subprocess
import time
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
FPS = 25

BASE_DIR = Path("/Users/alienes/yt-oto-video/files")
ASSETS_DIR = BASE_DIR / "assets"
BOSKAFA_DIR = ASSETS_DIR / "boskafa"
SFX_DIR = ASSETS_DIR / "sfx/crayon"
MUSIC_DIR = ASSETS_DIR / "music"
OUTPUT_DIR = BASE_DIR / "output/boskafa_sample"
AUDIO_DIR = OUTPUT_DIR / "audio"
TEMP_DIR = OUTPUT_DIR / "temp_scenes"

B21_CUTOUT = ASSETS_DIR / "vehicles/real/b21_real_cutout.png"
BGM_PATH = MUSIC_DIR / "lofi_storyteller.mp3"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def get_pop_font(size: int = 38):
    for p in [
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_font_safe(size: int = 24, bold: bool = False):
    for p in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_audio_duration(file_path: Path) -> float:
    try:
        with wave.open(str(file_path), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 6.0


# ── PRE-RENDERED RAZOR-SHARP 2D SPRITES (ZERO RUNTIME SEAMS / ZERO ROTATION BLUR) ──
_SPRITE_CACHE = {}

def get_clean_boskafa_sprite(pose: str, t: float, is_speaking: bool = False, target_h: int = 680) -> Image.Image:
    # 1. Natural blinking: blinks every 3.0s for exactly 0.12s (3 frames)
    blink_cycle = t % 3.0
    is_blinking = (blink_cycle < 0.12)

    # 2. Speaking lip-sync: alternates open and closed mouth in rhythm with speech
    if is_speaking:
        mouth_open = (int(t * 7.5) % 3 != 0)
    else:
        mouth_open = False  # mouth stays closed in natural smile when not speaking

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

    cache_key = (fname, target_h)
    if cache_key in _SPRITE_CACHE:
        return _SPRITE_CACHE[cache_key]

    p = BOSKAFA_DIR / fname
    if not p.exists():
        p = BOSKAFA_DIR / f"{pose}.png"

    img = Image.open(p).convert("RGBA")
    ratio = target_h / float(img.height)
    new_w = max(10, int(img.width * ratio))
    scaled = img.resize((new_w, target_h), Image.Resampling.LANCZOS)
    _SPRITE_CACHE[cache_key] = scaled
    return scaled


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
        t = i / 10.0
        px = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t ** 2 * x2
        py = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t ** 2 * y2
        pts.append((px, py))
    draw.line(pts, fill=color, width=width)
    angle = math.atan2(y2 - cy, x2 - cx)
    al = 22
    a1 = angle + math.pi * 0.8
    a2 = angle - math.pi * 0.8
    draw.line([(x2, y2), (x2 + al * math.cos(a1), y2 + al * math.sin(a1))], fill=color, width=width)
    draw.line([(x2, y2), (x2 + al * math.cos(a2), y2 + al * math.sin(a2))], fill=color, width=width)


def draw_doodle_circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, rx: int, ry: int, progress: float = 1.0, color=(220, 38, 38), width: int = 5):
    pts = []
    total_steps = 36
    draw_steps = int(total_steps * min(1.0, max(0.0, progress)))
    if draw_steps < 2:
        return
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
    # rough edges
    rotated = tape.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=True)
    return rotated


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


# ── SCENE 1: THE $68B CRAYON REVEAL ──
def render_frame_scene_1(t: float, dur: float) -> Image.Image:
    frame = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(frame)
    draw_notebook_paper(draw)

    # Top yellow highlighter banner
    draw.rounded_rectangle([(320, 45), (1440, 125)], radius=8, fill=(254, 240, 138), outline=(234, 179, 8), width=2)
    draw.text((350, 58), "THE $68 BILLION DEFENSE CRAYON", font=get_pop_font(46), fill=(15, 23, 42))

    # Polaroid drop animation (drops in between 0.8s and 1.4s)
    drop_p = min(1.0, max(0.0, (t - 0.8) / 0.6))
    ease_y = math.sin(drop_p * math.pi * 0.5) if drop_p < 1.0 else 1.0
    # bounce
    if drop_p < 1.0:
        py_cur = int(-400 + (190 - -400) * ease_y)
    else:
        bounce_t = min(1.0, (t - 1.4) / 0.3)
        py_cur = 190 + int(math.sin(bounce_t * math.pi) * 8.0) if bounce_t < 1.0 else 190

    px = 760
    pw, ph = 480, 550

    if t >= 0.8:
        # Polaroid shadow
        draw.rounded_rectangle([(px + 10, py_cur + 12), (px + pw + 10, py_cur + ph + 12)], radius=12, fill=(205, 200, 185, 140))
        # White card
        draw.rounded_rectangle([(px, py_cur), (px + pw, py_cur + ph)], radius=10, fill=(255, 255, 255), outline=(215, 210, 195), width=2)
        # Inner photo area
        ix, iy = px + 25, py_cur + 25
        iw, ih = pw - 50, ph - 135
        draw.rectangle([(ix, iy), (ix + iw, iy + ih)], fill=(244, 240, 226))

        # Crayon drawing inside
        cx_c, cy_c = ix + iw // 2, iy + ih // 2
        # Crayon body
        draw.polygon([(cx_c - 160, cy_c - 28), (cx_c + 90, cy_c - 28), (cx_c + 90, cy_c + 28), (cx_c - 160, cy_c + 28)], fill=(245, 197, 24))
        # Crayon cone tip
        draw.polygon([(cx_c + 90, cy_c - 28), (cx_c + 155, cy_c), (cx_c + 90, cy_c + 28)], fill=(234, 179, 8))
        # Green wrapper
        draw.rectangle([(cx_c - 120, cy_c - 30), (cx_c + 55, cy_c + 30)], fill=(34, 197, 94))
        draw.text((cx_c - 85, cy_c - 15), "CRAYON 64", font=get_pop_font(26), fill=(255, 255, 255))

        # Scotch tape top corner
        tape = draw_scotch_tape(draw, px + 20, py_cur - 15, w=110, h=34, angle_deg=-8.0)
        frame.alpha_composite(tape, (px + 15, py_cur - 15))

        # Polaroid labels
        draw.text((px + 35, py_cur + ph - 95), "SPEC: MIL-STD WAX MARKER", font=get_pop_font(24), fill=(30, 41, 59))
        draw.text((px + 35, py_cur + ph - 62), "RETAIL PRICE: $0.85", font=get_pop_font(26), fill=(220, 38, 38))

    # Animated red doodle circle (appears at t >= 2.2s)
    if t >= 2.2:
        circ_p = min(1.0, (t - 2.2) / 0.5)
        draw_doodle_circle(draw, px + 25 + (pw - 50) // 2 + 125, py_cur + 25 + (ph - 135) // 2, 58, 48, progress=circ_p, color=(220, 38, 38), width=5)

    # Animated doodle arrow + text (appears at t >= 2.8s)
    if t >= 2.8:
        arrow_start = (px + pw - 20, py_cur + 280)
        arrow_end = (px + pw - 90, py_cur + 225)
        draw_doodle_arrow(draw, arrow_start, arrow_end, color=(220, 38, 38), width=5)
        draw.text((arrow_start[0] + 15, arrow_start[1] - 15), "YES, AN ACTUAL CRAYON.", font=get_pop_font(30), fill=(220, 38, 38))

    # Boş Kafa character stands stably and presents cleanly
    if t < 1.2:
        char_img = get_clean_boskafa_sprite("walking", t, is_speaking=False, target_h=660)
        char_x = int(60 + (t / 1.2) * 140)
        char_y = H - char_img.height - 15 + int(math.sin(t * 14.0) * 6.0)
    else:
        # Stands completely stable on floor, mouth flaps cleanly while speaking, eyes blink every 3s
        char_img = get_clean_boskafa_sprite("pointing", t, is_speaking=(t < 5.8), target_h=680)
        char_x = 200
        char_y = H - char_img.height - 15

    frame.alpha_composite(char_img, (char_x, char_y))

    # Subtitles
    if t < 3.2:
        draw_subtitle_pill(draw, "Believe it or not, the Pentagon spent nearly $68 BILLION...")
    else:
        draw_subtitle_pill(draw, "...trying to reinvent a simple wax crayon!")

    return frame


# ── SCENE 2: THE $14,000 PEN & B-21 BOMBER ──
def render_frame_scene_2(t: float, dur: float) -> Image.Image:
    frame = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(frame)
    # Camera punch-in
    draw_notebook_paper(draw, punch_in=True)

    # Top highlight banner
    draw.rounded_rectangle([(300, 45), (1480, 125)], radius=8, fill=(254, 240, 138), outline=(234, 179, 8), width=2)
    draw.text((330, 58), "AEROSPACE CONTRACTOR PROPOSAL", font=get_pop_font(44), fill=(15, 23, 42))

    # B-21 Real Cutout Polaroid on top right (slides in from right at t >= 0.4s)
    b21_p = min(1.0, max(0.0, (t - 0.4) / 0.5))
    bx = int(W - 40 - (420 * b21_p))
    by = 160
    draw.rounded_rectangle([(bx + 8, by + 10), (bx + 400 + 8, by + 280 + 10)], radius=12, fill=(205, 200, 185, 140))
    draw.rounded_rectangle([(bx, by), (bx + 400, by + 280)], radius=10, fill=(255, 255, 255), outline=(215, 210, 195), width=2)
    draw.rectangle([(bx + 15, by + 15), (bx + 385, by + 225)], fill=(20, 30, 45))

    if B21_CUTOUT.exists():
        cut = Image.open(B21_CUTOUT).convert("RGBA")
        cut = cut.resize((350, int(cut.height * (350.0 / cut.width))))
        frame.alpha_composite(cut, (bx + 25, by + 25 + (210 - cut.height) // 2))

    draw.text((bx + 20, by + 240), "AIRCRAFT: B-21 RAIDER ($750M / EACH)", font=get_pop_font(20), fill=(15, 23, 42))
    tape_b21 = draw_scotch_tape(draw, bx + 140, by - 14, w=120, h=32, angle_deg=4.0)
    frame.alpha_composite(tape_b21, (bx + 140, by - 14))

    # Invoice card in center
    cx, cy = 680, 280
    cw, ch = 580, 480
    draw.rounded_rectangle([(cx + 10, cy + 12), (cx + cw + 10, cy + ch + 12)], radius=14, fill=(205, 200, 185, 140))
    draw.rounded_rectangle([(cx, cy), (cx + cw, cy + ch)], radius=12, fill=(255, 255, 255), outline=(59, 130, 246), width=3)
    draw.rectangle([(cx, cy), (cx + cw, cy + 60)], fill=(30, 58, 138))
    draw.text((cx + 25, cy + 15), "DEFENSE PROCUREMENT REQUISITION", font=get_pop_font(26), fill=(255, 255, 255))

    draw.text((cx + 30, cy + 85), "ITEM: High-Enthalpy Marking System", font=get_font_safe(22), fill=(15, 23, 42))
    draw.text((cx + 30, cy + 125), "APPLICATION: Fast Jet Canopy & Hull", font=get_font_safe(20), fill=(71, 85, 105))

    # Glowing Price Tag Badge (pulsates)
    pulse = 1.0 + 0.04 * math.sin(t * 8.0)
    bw, bh = int(480 * pulse), int(95 * pulse)
    bx_tag = cx + (cw - bw) // 2
    by_tag = cy + 180
    draw.rounded_rectangle([(bx_tag, by_tag), (bx_tag + bw, by_tag + bh)], radius=16, fill=(234, 179, 8), outline=(180, 83, 9), width=3)
    draw.text((bx_tag + 30, by_tag + 18), "PRICE: $14,000 PER PEN!", font=get_pop_font(40), fill=(15, 23, 42))

    draw.text((cx + 30, cy + 310), "ANNUAL QUANTITY: 45,000 UNITS", font=get_font_safe(20), fill=(15, 23, 42))
    draw.text((cx + 30, cy + 345), "TOTAL TAXPAYER COST: $630,000,000", font=get_pop_font(24), fill=(220, 38, 38))

    # Red stamp "APPROVED BY CONGRESS"
    if t >= 2.5:
        stamp_img = Image.new("RGBA", (340, 90), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp_img)
        sd.rounded_rectangle([(0, 0), (340, 90)], radius=12, fill=(220, 38, 38, 220), outline=(153, 27, 27), width=3)
        sd.text((18, 22), "APPROVED BY CONGRESS", font=get_pop_font(28), fill=(255, 255, 255))
        stamp_rot = stamp_img.rotate(-12, resample=Image.Resampling.BICUBIC, expand=True)
        frame.alpha_composite(stamp_rot, (cx + cw - 360, cy + ch - 130))

    # Character pointing stably at the $14,000 tag with mouth flapping and blinking
    char_img = get_clean_boskafa_sprite("pointing", t, is_speaking=(t < 6.8), target_h=700)
    char_x = 120
    char_y = H - char_img.height - 15
    frame.alpha_composite(char_img, (120, char_y))

    # Thought Bubble over stickman at t >= 2.0s
    if t >= 2.0:
        tx_b, ty_b = 260, 200
        draw.ellipse([(tx_b, ty_b), (tx_b + 300, ty_b + 110)], fill=(255, 255, 255), outline=(15, 23, 42), width=3)
        draw.text((tx_b + 35, ty_b + 35), "$14,000 FOR A PEN?!", font=get_pop_font(26), fill=(220, 38, 38))
        draw.ellipse([(tx_b - 20, ty_b + 105), (tx_b - 5, ty_b + 120)], fill=(255, 255, 255), outline=(15, 23, 42), width=2)

    # Subtitles
    if t < 3.5:
        draw_subtitle_pill(draw, "Contractors called it an 'Aerospace High-Enthalpy System'...")
    else:
        draw_subtitle_pill(draw, "...and billed taxpayers $14,000 PER PEN!")

    return frame


# ── SCENE 3: DESERT MELTDOWN FIASCO ──
def render_frame_scene_3(t: float, dur: float) -> Image.Image:
    # Screen shake when stamp hits at t >= 4.0s
    shake_x = int(math.sin(t * 50.0) * 6.0) if 4.0 <= t <= 4.5 else 0
    shake_y = int(math.cos(t * 45.0) * 6.0) if 4.0 <= t <= 4.5 else 0

    frame = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(frame)
    draw_notebook_paper(draw, punch_in=False, shake_x=shake_x, shake_y=shake_y)

    # Top highlight banner
    draw.rounded_rectangle([(320, 45), (1440, 125)], radius=8, fill=(254, 202, 202), outline=(220, 38, 38), width=2)
    draw.text((360, 58), "DESERT FIELD TEST: OPERATION MELTDOWN", font=get_pop_font(42), fill=(185, 28, 28))

    # Sun with heat waves
    sx, sy = 1450, 200
    draw.ellipse([(sx - 50, sy - 50), (sx + 50, sy + 50)], fill=(245, 158, 11), outline=(217, 119, 6), width=3)
    for i in range(8):
        angle = (i / 8.0) * 2 * math.pi + (t * 0.5)
        rx1, ry1 = sx + 60 * math.cos(angle), sy + 60 * math.sin(angle)
        rx2, ry2 = sx + 85 * math.cos(angle), sy + 85 * math.sin(angle)
        draw.line([(rx1, ry1), (rx2, ry2)], fill=(245, 158, 11), width=4)

    # Thermometer rising
    tx, ty = 720, 220
    th_w, th_h = 70, 360
    # Bulb & tube
    draw.rounded_rectangle([(tx, ty), (tx + th_w, ty + th_h)], radius=35, fill=(255, 255, 255), outline=(15, 23, 42), width=3)
    # Fill level rising with time
    rise_p = min(1.0, max(0.0, t / 3.0))
    fill_h = int(th_h * 0.85 * rise_p)
    col_t = (34, 197, 94) if rise_p < 0.5 else ((234, 179, 8) if rise_p < 0.8 else (239, 68, 68))
    draw.rounded_rectangle([(tx + 12, ty + th_h - fill_h - 15), (tx + th_w - 12, ty + th_h - 15)], radius=20, fill=col_t)
    draw.ellipse([(tx + 8, ty + th_h - 60), (tx + th_w - 8, ty + th_h - 10)], fill=col_t)

    # Temperature text
    cur_temp = int(20 + rise_p * 28)
    draw.text((tx + th_w + 25, ty + 120), f"{cur_temp}°C", font=get_pop_font(64), fill=col_t)
    draw.text((tx + th_w + 25, ty + 195), f"({int(cur_temp * 1.8 + 32)}°F)", font=get_pop_font(34), fill=(100, 116, 139))
    if rise_p >= 0.9:
        draw.text((tx + th_w + 25, ty + 255), "MELTING POINT EXCEEDED!", font=get_pop_font(28), fill=(220, 38, 38))

    # Melted pink sludge puddle on the desk/notebook
    if t >= 2.5:
        puddle_p = min(1.0, (t - 2.5) / 2.0)
        p_w = int(320 * puddle_p)
        p_h = int(120 * puddle_p)
        px_p, py_p = 1050, 480
        draw.ellipse([(px_p - p_w // 2, py_p - p_h // 2), (px_p + p_w // 2, py_p + p_h // 2)], fill=(236, 72, 153), outline=(190, 24, 93), width=3)
        draw.text((px_p - 110, py_p - 15), "MELTED PINK WAX SLUDGE", font=get_pop_font(20), fill=(255, 255, 255))

    # Giant RED STAMP "TOTAL FAILURE" at t >= 4.0s
    if t >= 4.0:
        stamp_img = Image.new("RGBA", (500, 140), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp_img)
        sd.rounded_rectangle([(0, 0), (500, 140)], radius=18, fill=(220, 38, 38, 240), outline=(153, 27, 27), width=6)
        sd.text((35, 30), "CRITICAL FAILURE", font=get_pop_font(52), fill=(255, 255, 255))
        stamp_rot = stamp_img.rotate(-14, resample=Image.Resampling.BICUBIC, expand=True)
        frame.alpha_composite(stamp_rot, (720, 560))

    # Boş Kafa character SHOCKED: stands firmly on floor with panic eyes & sweat drops
    char_img = get_clean_boskafa_sprite("shocked", t, is_speaking=False, target_h=680)
    char_x = 160
    char_y = H - char_img.height - 15
    frame.alpha_composite(char_img, (char_x, char_y))

    # Animated flying sweat drops
    for i, (dx, dy) in enumerate([(-35, -40), (45, -50), (-50, 20), (55, 30)]):
        drop_v = math.sin(t * 15.0 + i) * 6.0
        draw.ellipse([(280 + dx, char_y + 120 + dy + drop_v), (292 + dx, char_y + 138 + dy + drop_v)], fill=(56, 189, 248), outline=(2, 132, 199), width=2)

    # Subtitles
    if t < 3.4:
        draw_subtitle_pill(draw, "Until day one in the desert, when the temperature hit 48°C...")
    else:
        draw_subtitle_pill(draw, "...and the entire $14,000 marker melted into pink sludge!")

    return frame


# ── SCENE 4: WALMART $0.85 COMMON SENSE ──
def render_frame_scene_4(t: float, dur: float) -> Image.Image:
    frame = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(frame)
    draw_notebook_paper(draw, punch_in=False)

    # Top highlight banner
    draw.rounded_rectangle([(320, 45), (1440, 125)], radius=8, fill=(187, 247, 208), outline=(34, 197, 94), width=2)
    draw.text((360, 58), "THE FRONT-LINE COMMON SENSE SOLUTION", font=get_pop_font(42), fill=(22, 101, 52))

    # Walmart Receipt Card in center
    rx, ry = 720, 200
    rw, rh = 540, 500
    draw.rounded_rectangle([(rx + 10, ry + 12), (rx + rw + 10, ry + rh + 12)], radius=14, fill=(205, 200, 185, 140))
    draw.rounded_rectangle([(rx, ry), (rx + rw, ry + rh)], radius=12, fill=(255, 255, 255), outline=(34, 197, 94), width=3)

    # Top green header
    draw.rectangle([(rx, ry), (rx + rw, ry + 70)], fill=(22, 163, 74))
    draw.text((rx + 30, ry + 20), "WALMART STORE RECEIPT #4402", font=get_pop_font(28), fill=(255, 255, 255))

    # Receipt lines
    draw.text((rx + 40, ry + 110), "ITEM: CRAYOLA 24-PACK CRAYONS", font=get_font_safe(24, bold=True), fill=(15, 23, 42))
    draw.text((rx + 40, ry + 155), "DEPARTMENT: Preschool Supplies", font=get_font_safe(20), fill=(100, 116, 139))
    draw.text((rx + 40, ry + 195), "MELTING RESISTANCE: 58°C (Tested)", font=get_font_safe(20), fill=(22, 101, 52))

    draw.line([(rx + 30, ry + 250), (rx + rw - 30, ry + 250)], fill=(200, 200, 200), width=2)

    draw.text((rx + 40, ry + 280), "TOTAL PRICE:", font=get_pop_font(36), fill=(15, 23, 42))
    draw.text((rx + rw - 180, ry + 275), "$0.85", font=get_pop_font(48), fill=(22, 163, 74))

    # Red pushpin at top of receipt
    draw.ellipse([(rx + rw // 2 - 12, ry - 14), (rx + rw // 2 + 12, ry + 10)], fill=(220, 38, 38), outline=(153, 27, 27), width=2)

    # Big Green Checkmark doodle at t >= 2.0s
    if t >= 2.0:
        chk_p = min(1.0, (t - 2.0) / 0.5)
        pts = [(rx + 60, ry + 390), (rx + 110, ry + 440), (rx + 200, ry + 340)]
        draw.line(pts[: int(3 * chk_p) + 1], fill=(22, 163, 74), width=8)
        draw.text((rx + 160, ry + 380), "MISSION READY: 100%", font=get_pop_font(32), fill=(22, 163, 74))

    # Hand-drawn marker formula box at bottom
    fx, fy = 720, 740
    draw.rounded_rectangle([(fx, fy), (fx + rw, fy + 120)], radius=16, fill=(254, 240, 138), outline=(234, 179, 8), width=3)
    draw.text((fx + 30, fy + 20), "COMMON SENSE > $68,000,000,000", font=get_pop_font(34), fill=(15, 23, 42))
    draw.text((fx + 30, fy + 70), "Simplicity wins every war.", font=get_font_safe(22), fill=(71, 85, 105))

    # Boş Kafa character SMUG: stands firmly on the floor with hands in pockets and smirk
    char_img = get_clean_boskafa_sprite("smug", t, is_speaking=False, target_h=680)
    char_x = 180
    char_y = H - char_img.height - 15
    frame.alpha_composite(char_img, (180, char_y))

    # Subtitles
    if t < 3.0:
        draw_subtitle_pill(draw, "Leaving frontline soldiers to do what they always do...")
    else:
        draw_subtitle_pill(draw, "...buy an $0.85 preschool crayon from Walmart!")

    return frame


# ── AUDIO MIXER FOR SCENE ──
def mix_sample_scene_audio(wav_path: Path, sfx_events: list, output_wav: Path):
    cmd = ["ffmpeg", "-y", "-i", str(wav_path)]
    filter_inputs = ["[0:a]"]
    filter_parts = []

    valid_sfx = [(p, d, v) for p, d, v in sfx_events if Path(p).exists()]
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


# ── MAIN PIPELINE RENDERER ──
def render_full_boskafa_demo():
    print("🎬 [Boş Kafa Style Engine] Rendering 4-scene sample showcase...")
    start_time = time.time()

    scenes_config = [
        (1, "scene_1.wav", render_frame_scene_1, [
            (SFX_DIR / "whoosh.mp3", 0.05, 0.40),
            (SFX_DIR / "pop.mp3", 1.2, 0.50),
            (SFX_DIR / "marker_scribble.wav", 2.2, 0.45)
        ]),
        (2, "scene_2.wav", render_frame_scene_2, [
            (SFX_DIR / "whoosh.mp3", 0.05, 0.35),
            (SFX_DIR / "cash_register.wav", 1.8, 0.50),
            (SFX_DIR / "pop.mp3", 2.5, 0.45)
        ]),
        (3, "scene_3.wav", render_frame_scene_3, [
            (SFX_DIR / "cartoon_boing.wav", 0.1, 0.40),
            (SFX_DIR / "error.mp3", 2.0, 0.40),
            (SFX_DIR / "stamp.wav", 4.0, 0.55)
        ]),
        (4, "scene_4.wav", render_frame_scene_4, [
            (SFX_DIR / "whoosh.mp3", 0.05, 0.35),
            (SFX_DIR / "click.mp3", 0.8, 0.40),
            (SFX_DIR / "pop.mp3", 2.0, 0.45)
        ])
    ]

    rendered_scenes = []

    for sc_id, wav_name, frame_renderer, sfx_list in scenes_config:
        wav_p = AUDIO_DIR / wav_name
        dur = get_audio_duration(wav_p)
        total_frames = max(25, int(dur * FPS))

        mixed_wav = TEMP_DIR / f"mixed_{wav_name}"
        mix_sample_scene_audio(wav_p, sfx_list, mixed_wav)

        scene_mp4 = TEMP_DIR / f"scene_{sc_id:02d}.mp4"
        print(f"  ✨ Rendering Scene {sc_id}/4 ({dur:.2f}s, {total_frames} frames)...")

        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "rgba", "-r", str(FPS),
            "-i", "-",
            "-i", str(mixed_wav),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(scene_mp4)
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        for f_idx in range(total_frames):
            t = f_idx / float(FPS)
            f = frame_renderer(t, dur)
            proc.stdin.write(f.tobytes())

        proc.stdin.close()
        proc.wait()
        rendered_scenes.append(scene_mp4)

    # Concat scenes
    concat_list = TEMP_DIR / "concat_list.txt"
    with open(concat_list, "w") as f:
        for p in rendered_scenes:
            f.write(f"file '{p.resolve()}'\n")

    final_output = OUTPUT_DIR / "boskafa_demo.mp4"
    print("🎵 Mixing final broadcast cut with background music...")

    if BGM_PATH.exists():
        cmd_final = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-stream_loop", "-1", "-i", str(BGM_PATH),
            "-filter_complex", "[1:a]volume=0.10[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]",
            "-map", "0:v",
            "-map", "[a_out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(final_output)
        ]
    else:
        cmd_final = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy",
            str(final_output)
        ]

    subprocess.run(cmd_final, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    dt = time.time() - start_time
    size_mb = final_output.stat().st_size / (1024 * 1024)
    print(f"🎉 [COMPLETED] Boş Kafa Sample Video ready: {final_output.name} ({size_mb:.2f} MB, {dt:.1f}s)")
    return final_output


if __name__ == "__main__":
    render_full_boskafa_demo()
