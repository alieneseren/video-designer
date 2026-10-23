"""
aviation_stickman_composite.py
==============================
Havacılık belgeselleri için Crayon Capital / MinutePhysics Tarzı Dinamik 2D Çizgi Karakter Motoru:
- 1. Kokpit CVR Sahnesi: Sinematik kokpit arka planı, Master Warning alarm flaşı, yapay ufuk (Attitude Indicator),
  lövyeli Kaptan ve panikleyen/terleyen F/O, yaylanan (elastic pop-in) çizgi roman konuşma balonları.
- 2. Kule ATC Sahnesi: Gece pist ışıklarına bakan panoramik kule camı, 360° dönen fosforlu radar skopu,
  yeşil TX flaşı ve ses dalgasıyla telsiz mandalına basan Kule Kontrolörü.
- 3. Kaza Kırım İnceleme Sahnesi: Hangarda projektör ışığı altında turuncu Kara Kutu (FDR) üzerinde gezinen büyüteç,
  NTSB/resmi müfettiş ve kademeli aydınlanan resmi rapor dosya paneli.
"""

import os
import math
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps

W = 1920
H = 1080

candidates_dir = [
    Path(__file__).resolve().parent / "assets" / "characters" / "aviation",
    Path(__file__).resolve().parent.parent / "assets" / "characters" / "aviation",
    Path("assets/characters/aviation"),
    Path("/home/ubuntu/yt-remote-worker/assets/characters/aviation")
]
ASSETS_DIR = next((p for p in candidates_dir if p.exists()), candidates_dir[0])


def get_font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap_text(text: str, max_chars: int = 34) -> list:
    words = (text or "").split()
    lines = []
    cur = []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) >= max_chars:
            lines.append(" ".join(cur))
            cur = []
    if cur:
        lines.append(" ".join(cur))
    return lines


def _draw_comic_bubble(
    draw: ImageDraw.Draw,
    x: int, y: int, w: int, h: int,
    tail_target: tuple,
    badge_title: str,
    badge_bg: tuple,
    quote_text: str,
    pop_scale: float = 1.0,
    max_chars_line: int = 32
):
    """Crayon Capital tarzı kalın siyah konturlu, yaylanarak açılan çizgi roman konuşma balonu."""
    if pop_scale <= 0.05:
        return

    cx, cy = x + w // 2, y + h // 2
    sw, sh = int(w * pop_scale), int(h * pop_scale)
    sx, sy = cx - sw // 2, cy - sh // 2

    # Yumuşak gölge
    draw.rounded_rectangle([(sx + 5, sy + 5), (sx + sw + 5, sy + sh + 5)], radius=16, fill=(0, 0, 0, 140))
    # Balon gövdesi
    draw.rounded_rectangle([(sx, sy), (sx + sw, sy + sh)], radius=16, fill=(255, 255, 255), outline=(15, 23, 42), width=4)

    # Kısa üçgen kuyruk (Karakterin ağzına doğru)
    tx, ty = tail_target
    if tx < cx:
        # Sol kuyruk
        draw.polygon([(sx + 35, sy + sh - 2), (sx + 65, sy + sh - 2), (sx + 20, sy + sh + 24)], fill=(255, 255, 255))
        draw.line([(sx + 35, sy + sh), (sx + 20, sy + sh + 24)], fill=(15, 23, 42), width=4)
        draw.line([(sx + 65, sy + sh), (sx + 20, sy + sh + 24)], fill=(15, 23, 42), width=4)
    else:
        # Sağ kuyruk
        draw.polygon([(sx + sw - 65, sy + sh - 2), (sx + sw - 35, sy + sh - 2), (sx + sw - 20, sy + sh + 24)], fill=(255, 255, 255))
        draw.line([(sx + sw - 65, sy + sh), (sx + sw - 20, sy + sh + 24)], fill=(15, 23, 42), width=4)
        draw.line([(sx + sw - 35, sy + sh), (sx + sw - 20, sy + sh + 24)], fill=(15, 23, 42), width=4)

    if pop_scale > 0.75:
        # Renkli hap rozet (Badge)
        badge_w = min(sw - 36, int(len(badge_title) * 9.5) + 30)
        draw.rounded_rectangle([(sx + 16, sy + 14), (sx + 16 + badge_w, sy + 42)], radius=7, fill=badge_bg)
        draw.text((sx + 24, sy + 18), badge_title, font=get_font(13, True), fill=(255, 255, 255))

        # Metin satırları (Vurgulu kelimeler kırmızı)
        lines = _wrap_text(quote_text, max_chars_line)
        for idx, line in enumerate(lines[:3]):
            is_urgent = any(kw in line.upper() for kw in ["PULL UP", "STALL", "BANK", "ALARM", "MAYDAY", "WARNING", "SINK", "CRITICAL"])
            col = (220, 20, 20) if is_urgent else (15, 23, 42)
            draw.text((sx + 20, sy + 50 + idx * 26), line, font=get_font(18, True), fill=col)


# ==============================================================================
# 1. HAREKETLİ KOKPİT CVR VİDEO MOTORU (CRAYON CAPITAL STYLE)
# ==============================================================================
def generate_animated_cvr_video(
    flight_name: str = "COMMERCIAL AIRLINER FLIGHT",
    situation_title: str = "COCKPIT EMERGENCY // CRITICAL CRM BREAKDOWN",
    captain_quote: str = "Aircraft is banking! Watch the airspeed!",
    fo_quote: str = "Bank angle! Stick shaker active! PULL UP!",
    bank_angle: float = 45.0,
    sink_rate: str = "-3,200 FT/MIN",
    duration: float = 5.0,
    output_path: str = "/tmp/animated_cvr.mp4"
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fps = 25
    total_frames = max(25, int(duration * fps))

    cap_file = ASSETS_DIR / "captain_calm.png"
    fo_file = ASSETS_DIR / "first_officer_panicked.png"
    cap_img, fo_img = None, None

    if cap_file.exists():
        c_raw = Image.open(cap_file)
        ratio = 650 / c_raw.height
        cap_img = c_raw.resize((int(c_raw.width * ratio), 650), Image.Resampling.LANCZOS)
        cap_img = ImageOps.mirror(cap_img)

    if fo_file.exists():
        f_raw = Image.open(fo_file)
        ratio = 590 / f_raw.height
        fo_img = f_raw.resize((int(f_raw.width * ratio), 590), Image.Resampling.LANCZOS)

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{W}x{H}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        for f in range(total_frames):
            t_sec = f / fps
            canvas = Image.new("RGB", (W, H), (8, 14, 24))
            draw = ImageDraw.Draw(canvas)

            # 1. Sinematik Kokpit Arka Planı (Karanlık gökyüzü, acil durum kırmızı flaş yansıması)
            pulse_warn = (math.sin(f * 0.45) + 1.0) * 0.5
            for y in range(0, H, 4):
                ratio = y / H
                r = int(10 + pulse_warn * 24 + ratio * 12)
                g = int(14 * (1.0 - pulse_warn * 0.45) + ratio * 8)
                b = int(26 * (1.0 - pulse_warn * 0.4) + ratio * 14)
                draw.rectangle([(0, y), (W, y + 4)], fill=(r, g, b))

            # Ufuk çizgisi ve kokpit ön cam direkleri
            horiz_y = H // 2 - 20
            draw.line([(0, horiz_y), (W, horiz_y)], fill=(32, 46, 68), width=1)
            cx = W // 2
            draw.polygon([(cx - 24, 0), (cx + 24, 0), (cx + 36, horiz_y + 80), (cx - 36, horiz_y + 80)], fill=(18, 26, 38))
            draw.polygon([(0, 0), (80, 0), (130, horiz_y + 80), (0, horiz_y + 80)], fill=(18, 26, 38))
            draw.polygon([(W - 80, 0), (W, 0), (W, horiz_y + 80), (W - 130, horiz_y + 80)], fill=(18, 26, 38))

            # Gösterge Paneli Alt Tablası & Parlayan Gösterge Işıkları
            dash_y = H - 230
            draw.polygon([(0, dash_y), (W, dash_y), (W, H), (0, H)], fill=(12, 17, 26))
            draw.line([(0, dash_y), (W, dash_y)], fill=(38, 54, 78), width=4)
            for i, lx in enumerate(range(160, W - 160, 65)):
                l_col = (255, 45, 45) if (f // 5) % 2 == 0 else [(0, 220, 255), (0, 255, 130), (255, 190, 0)][i % 3]
                draw.ellipse([(lx, dash_y + 22), (lx + 8, dash_y + 30)], fill=l_col)

            # Acil durum hafif kamera titreşimi
            shake_x = int(math.sin(f * 1.8) * 2.5)
            shake_y = int(math.cos(f * 2.1) * 2.0)

            # 2. Orta: Canlı Yapay Ufuk (Attitude Indicator)
            aic_x, aic_y = cx + shake_x, H // 2 - 25 + shake_y
            rad_r = 125
            draw.ellipse([(aic_x - rad_r - 8, aic_y - rad_r - 8), (aic_x + rad_r + 8, aic_y + rad_r + 8)], fill=(14, 22, 34), outline=(0, 160, 220), width=3)
            draw.ellipse([(aic_x - rad_r, aic_y - rad_r), (aic_x + rad_r, aic_y + rad_r)], fill=(10, 15, 25), outline=(0, 220, 255), width=2)

            anim_bank = float(bank_angle) + math.sin(f * 0.28) * 5.0
            rad = math.radians(anim_bank)
            dx = int(math.cos(rad) * rad_r)
            dy = int(math.sin(rad) * rad_r)
            draw.line([(aic_x - dx, aic_y - dy), (aic_x + dx, aic_y + dy)], fill=(255, 210, 0), width=5)
            draw.ellipse([(aic_x - 6, aic_y - 6), (aic_x + 6, aic_y + 6)], fill=(255, 50, 50))
            draw.text((aic_x - 95, aic_y + rad_r + 18), f"BANK ANGLE: {anim_bank:.0f}° ROLL", font=get_font(18, True), fill=(255, 60, 60))

            # Master Warning Flaşı
            blink_warn = (f // 5) % 2 == 0
            warn_bg = (220, 38, 38) if blink_warn else (75, 15, 15)
            draw.rounded_rectangle([(aic_x - 110, aic_y - rad_r - 65), (aic_x + 110, aic_y - rad_r - 18)], radius=8, fill=warn_bg, outline=(255, 255, 255), width=2)
            draw.text((aic_x - 90, aic_y - rad_r - 50), "MASTER WARNING", font=get_font(17, True), fill=(255, 255, 255))

            # 3. Sol Karakter: Kaptan Pilot (Nefes alma / Squashing)
            if cap_img:
                cap_breath = int(math.sin(f * 0.18) * 3.5)
                cap_y = H - cap_img.height + 25 + cap_breath + shake_y
                canvas.paste(cap_img, (70 + shake_x, cap_y), cap_img)

            # 4. Sağ Karakter: Panikleyen F/O (Titreme + Şakaktan Kayan Mavi Ter Damlası)
            if fo_img:
                fo_jitter_x = int(math.sin(f * 1.6) * 3)
                fo_jitter_y = int(math.cos(f * 1.9) * 2)
                fo_x = W - fo_img.width - 80 + fo_jitter_x + shake_x
                fo_y = H - fo_img.height + 35 + fo_jitter_y + shake_y
                canvas.paste(fo_img, (fo_x, fo_y), fo_img)

                # Ter damlası
                drop_step = (f % 26) / 26.0
                drop_x = fo_x + 98
                drop_y = fo_y + 112 + int(drop_step * 38)
                draw.ellipse([(drop_x - 3, drop_y - 4), (drop_x + 4, drop_y + 7)], fill=(0, 220, 255))

            # 5. Yaylanan Çizgi Roman Konuşma Balonları (Elastic Pop-in)
            pop_cap = min(1.0, 1.0 + 0.28 * math.exp(-7 * t_sec) * math.sin(16 * t_sec)) if t_sec < 0.45 else 1.0
            _draw_comic_bubble(
                draw, 100, 150, 470, 145,
                (220, H - 420),
                "🔴 CAPTAIN (CVR TRANSCRIPT)", (220, 38, 38),
                captain_quote,
                pop_scale=pop_cap,
                max_chars_line=30
            )

            t_fo = max(0.0, t_sec - 0.14)
            pop_fo = min(1.0, 1.0 + 0.28 * math.exp(-7 * t_fo) * math.sin(16 * t_fo)) if t_fo < 0.45 else 1.0
            _draw_comic_bubble(
                draw, W - 580, 150, 480, 145,
                (W - 220, H - 420),
                "🎙️ FIRST OFFICER (CVR TRANSCRIPT)", (37, 99, 235),
                fo_quote,
                pop_scale=pop_fo,
                max_chars_line=30
            )

            # Üst Bant Başlık (Metin Çakışması Engellenir)
            clean_cvr_fl = flight_name.split(":")[0].split("//")[0].strip().upper()
            if len(clean_cvr_fl) > 34:
                clean_cvr_fl = clean_cvr_fl[:32] + "..."
            draw.text((90, 48), f"TACTICAL CVR RECONSTRUCTION // {clean_cvr_fl}", font=get_font(22, True), fill=(255, 215, 0))
            draw.text((W - 480, 52), f"SINK RATE: {sink_rate}", font=get_font(16, True), fill=(255, 75, 75))

            proc.stdin.write(canvas.tobytes())

    finally:
        proc.stdin.close()
        proc.wait()

    return output_path


# ==============================================================================
# 2. HAREKETLİ ATC KULE VİDEO MOTORU (CRAYON CAPITAL STYLE)
# ==============================================================================
def generate_animated_atc_video(
    flight_name: str = "COMMERCIAL AIRLINER FLIGHT",
    atc_station: str = "AIRPORT TOWER // DEPARTURE RADAR",
    atc_call: str = "Radar contact lost. Turn immediately!",
    altitude_reported: str = "40 FT -> NO CLIMB",
    squawk_code: str = "SQUAWK 7700 (EMERGENCY)",
    duration: float = 5.0,
    output_path: str = "/tmp/animated_atc.mp4"
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fps = 25
    total_frames = max(25, int(duration * fps))

    atc_file = ASSETS_DIR / "atc_controller.png"
    atc_img = None
    if atc_file.exists():
        a_raw = Image.open(atc_file)
        ratio = 600 / a_raw.height
        atc_img = a_raw.resize((int(a_raw.width * ratio), 600), Image.Resampling.LANCZOS)

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{W}x{H}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        for f in range(total_frames):
            t_sec = f / fps
            canvas = Image.new("RGB", (W, H), (6, 12, 20))
            draw = ImageDraw.Draw(canvas)

            # 1. Kule Panoramik Camı ve Gece Pisti Işıkları
            horiz_y = H // 2 - 40
            for y in range(0, H, 4):
                ratio = y / H
                draw.rectangle([(0, y), (W, y + 4)], fill=(int(6 + ratio * 8), int(10 + ratio * 14), int(20 + ratio * 20)))

            # Dışarıdaki Gece Pist & Taksiyolu Işıkları
            draw.line([(0, horiz_y), (W, horiz_y)], fill=(20, 35, 50), width=1)
            # Pist merkezi perspektif çizgisi ve yeşil/beyaz apron lambaları
            for offset, p_col in [(-220, (0, 255, 120)), (0, (255, 255, 255)), (220, (0, 255, 120))]:
                vanish_x = W // 2 + 100
                for step in range(1, 10):
                    lx = int(vanish_x + (offset * (step / 10.0) * 1.8))
                    ly = int(horiz_y + (step * 24))
                    draw.ellipse([(lx - 2, ly - 2), (lx + 2, ly + 2)], fill=p_col)

            # Kule Konsolu Ön Masası
            desk_y = H - 240
            draw.polygon([(0, desk_y), (W, desk_y), (W, H), (0, H)], fill=(11, 19, 30))
            draw.line([(0, desk_y), (W, desk_y)], fill=(0, 160, 220), width=3)

            # 2. Sol Karakter: Kuleci
            if atc_img:
                atc_breath = int(math.sin(f * 0.18) * 3)
                canvas.paste(atc_img, (80, H - 610 + atc_breath), atc_img)

            # 3. Sol Üst Yaylanan Çizgi Roman Balonu
            pop_atc = min(1.0, 1.0 + 0.28 * math.exp(-7 * t_sec) * math.sin(16 * t_sec)) if t_sec < 0.45 else 1.0
            _draw_comic_bubble(
                draw, 110, 140, 680, 155,
                (260, H - 430),
                f"📡 {atc_station.upper()} (118.10 MHz)", (16, 140, 90),
                atc_call,
                pop_scale=pop_atc,
                max_chars_line=44
            )

            # Canlı Osiloskop Ses Dalgası (Audio Waveform)
            if pop_atc > 0.8:
                wave_y = 140 + 155 - 22
                for wx in range(140, 140 + 620, 4):
                    amp = math.sin((wx + f * 22) * 0.08) * 8 * math.sin(f * 0.16)
                    draw.line([(wx, wave_y - amp), (wx, wave_y + amp)], fill=(16, 220, 140), width=2)

            # Kule Konsolu TX / PTT Yanıp Sönen Yeşil LED
            tx_blink = (f // 5) % 2 == 0
            tx_col = (16, 240, 130) if tx_blink else (6, 80, 45)
            draw.ellipse([(730, 155), (748, 173)], fill=tx_col, outline=(255, 255, 255), width=1)
            draw.text((755, 156), "TX", font=get_font(14, True), fill=tx_col)

            # 4. Sağ Taraf: Fosforlu Radar Skopu
            rx, ry, rr = W - 470, H // 2 + 20, 250
            draw.ellipse([(rx - rr, ry - rr), (rx + rr, ry + rr)], fill=(4, 18, 12), outline=(16, 200, 130), width=3)
            for r_step in [60, 120, 180, 240]:
                draw.ellipse([(rx - r_step, ry - r_step), (rx + r_step, ry + r_step)], outline=(16, 180, 120), width=1)
            draw.line([(rx - rr, ry), (rx + rr, ry)], fill=(16, 180, 120), width=1)
            draw.line([(rx, ry - rr), (rx, ry + rr)], fill=(16, 180, 120), width=1)

            # 360° Dönen Tarama Kolu
            sweep_angle = (f * 7.5) % 360
            s_rad = math.radians(sweep_angle)
            sx = int(rx + math.cos(s_rad) * rr)
            sy = int(ry + math.sin(s_rad) * rr)
            draw.line([(rx, ry), (sx, sy)], fill=(0, 255, 170), width=2)

            # Uçak Hedefi (Blip) & İrtifa Kaybı İzi
            target_x = rx + 80
            target_y = ry + 85
            draw.line([(rx - 100, ry - 60), (rx - 20, ry - 25), (target_x, target_y)], fill=(255, 215, 0), width=3)
            draw.ellipse([(target_x - 8, target_y - 8), (target_x + 8, target_y + 8)], fill=(255, 50, 50), outline=(255, 255, 255), width=2)

            # Radar Veri Bloğu
            draw.rectangle([(target_x + 15, target_y - 30), (target_x + 225, target_y + 40)], fill=(8, 24, 16), outline=(16, 200, 130), width=1)
            draw.text((target_x + 22, target_y - 24), flight_name[:16].upper(), font=get_font(14, True), fill=(255, 255, 255))
            draw.text((target_x + 22, target_y - 5), altitude_reported, font=get_font(13, True), fill=(255, 200, 0))
            draw.text((target_x + 22, target_y + 14), squawk_code[:19], font=get_font(12, True), fill=(255, 50, 50))

            # Üst Bant Başlık
            draw.text((90, 45), f"AIR TRAFFIC CONTROL AUDIO LOG // {atc_station.upper()}", font=get_font(24, True), fill=(0, 220, 255))
            draw.text((W - 500, 50), squawk_code, font=get_font(18, True), fill=(255, 60, 60))

            proc.stdin.write(canvas.tobytes())

    finally:
        proc.stdin.close()
        proc.wait()

    return output_path


# ==============================================================================
# 3. HAREKETLİ KAZA KIRIM İNCELEME VİDEO MOTORU (CRAYON CAPITAL STYLE)
# ==============================================================================
def generate_animated_investigation_video(
    flight_name: str = "COMMERCIAL AIRLINER FLIGHT",
    investigating_agency: str = "NATIONAL TRANSPORTATION SAFETY BOARD (NTSB)",
    primary_finding: str = "Unconfigured takeoff and critical warning horn system failure.",
    critical_factors: list = None,
    duration: float = 6.0,
    output_path: str = "/tmp/animated_investigation.mp4"
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fps = 25
    total_frames = max(25, int(duration * fps))

    ntsb_file = ASSETS_DIR / "ntsb_investigator.png"
    ntsb_img = None
    if ntsb_file.exists():
        n_raw = Image.open(ntsb_file)
        ratio = 600 / n_raw.height
        ntsb_img = n_raw.resize((int(n_raw.width * ratio), 600), Image.Resampling.LANCZOS)

    if not critical_factors:
        critical_factors = [
            ("FLIGHT CONTROL STATUS", "Primary control surfaces and configuration prior to incident"),
            ("COCKPIT PROCEDURES", "Crew checklist execution and human factors CRM communication"),
            ("SYSTEM WARNING INTEGRITY", "Audio-visual warning alerts and avionics system responses"),
            ("BLACK BOX RECOVERY", "Flight Data Recorder (FDR) and CVR audio successfully recovered")
        ]

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{W}x{H}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        for f in range(total_frames):
            p = f / max(1, total_frames - 1)
            canvas = Image.new("RGB", (W, H), (8, 14, 22))
            draw = ImageDraw.Draw(canvas)

            # 1. Hangar Projektör Işığı Efekti (Floodlight cone)
            for y in range(0, H, 4):
                ratio = y / H
                draw.rectangle([(0, y), (W, y + 4)], fill=(int(8 + ratio * 8), int(12 + ratio * 12), int(20 + ratio * 16)))
            # Tepe projektör ışığı konisi (Hangar spotlight)
            draw.polygon([(480, 0), (620, 0), (740, H - 200), (320, H - 200)], fill=(16, 28, 42))

            # İnceleme Masası
            table_y = H - 230
            draw.polygon([(0, table_y), (W, table_y), (W, H), (0, H)], fill=(15, 22, 32))
            draw.line([(0, table_y), (W, table_y)], fill=(40, 60, 85), width=3)

            # 2. Sol Karakter: Müfettiş
            if ntsb_img:
                canvas.paste(ntsb_img, (80, H - 610), ntsb_img)

            # Turuncu Kara Kutu (FDR/CVR)
            box_x, box_y, box_w, box_h = 390, H - 320, 170, 105
            draw.rectangle([(box_x, box_y), (box_x + box_w, box_y + box_h)], fill=(249, 115, 22), outline=(255, 255, 255), width=2)
            draw.rectangle([(box_x + 8, box_y + 8), (box_x + box_w - 8, box_y + box_h - 8)], fill=(234, 88, 12))
            draw.text((box_x + 18, box_y + 24), "FLIGHT RECORDER", font=get_font(12, True), fill=(255, 255, 255))
            draw.text((box_x + 18, box_y + 44), "DO NOT OPEN", font=get_font(11, True), fill=(255, 255, 255))
            # Sualtı Sinyal Verici Silindiri (ULB)
            draw.rectangle([(box_x + box_w - 32, box_y + 16), (box_x + box_w - 12, box_y + 75)], fill=(220, 220, 220), outline=(50, 50, 50), width=1)

            # Büyüteç Akıcı Gezinme Hareketi
            mag_cx = 455 + int(math.sin(f * 0.12) * 36)
            mag_cy = H - 275 + int(math.cos(f * 0.12) * 12)
            mag_r = 40
            draw.ellipse([(mag_cx - mag_r, mag_cy - mag_r), (mag_cx + mag_r, mag_cy + mag_r)], outline=(255, 215, 0), width=4)
            draw.line([(mag_cx + int(mag_r * 0.7), mag_cy + int(mag_r * 0.7)), (mag_cx + mag_r + 28, mag_cy + mag_r + 28)], fill=(180, 140, 20), width=6)
            draw.arc([(mag_cx - mag_r + 4, mag_cy - mag_r + 4), (mag_cx + mag_r - 4, mag_cy + mag_r - 4)], start=200, end=270, fill=(255, 255, 255), width=3)

            # 3. Sağ Taraf: Resmi Rapor & Bulgular Paneli (Dossier Panel)
            panel_x, panel_y, panel_w, panel_h = W - 930, 160, 850, 750
            draw.rectangle([(panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h)], fill=(12, 19, 32), outline=(0, 200, 255), width=2)
            draw.rectangle([(panel_x, panel_y), (panel_x + panel_w, panel_y + 60)], fill=(0, 140, 190))
            draw.text((panel_x + 25, panel_y + 16), "OFFICIAL INVESTIGATION DOSSIER & FINDINGS", font=get_font(20, True), fill=(255, 255, 255))

            # Damga (CONFIDENTIAL STAMP)
            draw.rectangle([(panel_x + panel_w - 210, panel_y + 14), (panel_x + panel_w - 25, panel_y + 46)], fill=(220, 38, 38))
            draw.text((panel_x + panel_w - 195, panel_y + 20), "OFFICIAL REPORT", font=get_font(13, True), fill=(255, 255, 255))

            # Birincil Tespit
            draw.text((panel_x + 30, panel_y + 80), "PRIMARY INVESTIGATION FINDING:", font=get_font(15, True), fill=(255, 200, 0))
            p_lines = _wrap_text(primary_finding, 54)
            for idx, pl in enumerate(p_lines[:2]):
                draw.text((panel_x + 30, panel_y + 108 + idx * 26), pl, font=get_font(18, True), fill=(240, 245, 255))

            # 4 Kritik Faktör Kartı (Kademeli Açılış)
            card_y = panel_y + 185
            for c_i, (title, desc) in enumerate(critical_factors[:4]):
                card_unlocked = p >= (c_i * 0.18)
                c_border = (0, 180, 240) if card_unlocked else (30, 45, 65)
                c_bg = (16, 28, 48) if card_unlocked else (10, 16, 26)
                t_color = (0, 220, 255) if card_unlocked else (80, 100, 120)

                draw.rectangle([(panel_x + 25, card_y), (panel_x + panel_w - 25, card_y + 110)], fill=c_bg, outline=c_border, width=1)
                draw.text((panel_x + 40, card_y + 12), f"FACTOR #{c_i+1}: {title}", font=get_font(15, True), fill=t_color)
                d_lines = _wrap_text(desc, 60)
                for d_idx, dl in enumerate(d_lines[:2]):
                    draw.text((panel_x + 40, card_y + 40 + d_idx * 24), dl, font=get_font(14, False), fill=(200, 215, 235) if card_unlocked else (60, 75, 90))
                card_y += 130

            # Üst Bant Başlık (Metin Çakışması Kesinlikle Engellenir)
            clean_fl_name = flight_name.split(":")[0].split("//")[0].strip().upper()
            if len(clean_fl_name) > 36:
                clean_fl_name = clean_fl_name[:34] + "..."
            title_str = f"OFFICIAL ACCIDENT INVESTIGATION // {clean_fl_name}"
            
            font_title = get_font(22, True)
            font_agency = get_font(16, True)
            agency_str = f"AGENCY: {investigating_agency[:36]}"
            
            # Agency'yi sağa yasla, title'ı solda tut
            draw.text((90, 48), title_str, font=font_title, fill=(255, 215, 0))
            try:
                a_bbox = font_agency.getbbox(agency_str)
                a_w = a_bbox[2] - a_bbox[0]
            except Exception:
                a_w = len(agency_str) * 10
            draw.text((W - a_w - 90, 52), agency_str, font=font_agency, fill=(0, 220, 255))

            proc.stdin.write(canvas.tobytes())

    finally:
        proc.stdin.close()
        proc.wait()

    return output_path


# ==============================================================================
# STATİK GÖRSEL ÜRETİCİLER (BACKWARD & FAST FALLBACK COMPATIBILITY)
# ==============================================================================
def render_cockpit_cvr_reconstruction(
    flight_name: str = "COMMERCIAL AIRLINER FLIGHT",
    situation_title: str = "COCKPIT EMERGENCY // CRITICAL CRM BREAKDOWN",
    captain_quote: str = "Aircraft is banking! Watch the airspeed!",
    fo_quote: str = "Bank angle! Stick shaker active! PULL UP!",
    bank_angle: float = 45.0,
    sink_rate: str = "-3,200 FT/MIN",
    output_path: str = "/tmp/cvr_static.png"
) -> str:
    """Tek kare yüksek çözünürlüklü CVR rekonstrüksiyon PNG görseli üretir."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fps = 25
    f = 12
    t_sec = 0.5

    cap_file = ASSETS_DIR / "captain_calm.png"
    fo_file = ASSETS_DIR / "first_officer_panicked.png"
    cap_img, fo_img = None, None

    if cap_file.exists():
        c_raw = Image.open(cap_file)
        ratio = 650 / c_raw.height
        cap_img = c_raw.resize((int(c_raw.width * ratio), 650), Image.Resampling.LANCZOS)
        cap_img = ImageOps.mirror(cap_img)

    if fo_file.exists():
        f_raw = Image.open(fo_file)
        ratio = 590 / f_raw.height
        fo_img = f_raw.resize((int(f_raw.width * ratio), 590), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (W, H), (8, 14, 24))
    draw = ImageDraw.Draw(canvas)

    pulse_warn = (math.sin(f * 0.45) + 1.0) * 0.5
    for y in range(0, H, 4):
        ratio = y / H
        r = int(10 + pulse_warn * 24 + ratio * 12)
        g = int(14 * (1.0 - pulse_warn * 0.45) + ratio * 8)
        b = int(26 * (1.0 - pulse_warn * 0.4) + ratio * 14)
        draw.rectangle([(0, y), (W, y + 4)], fill=(r, g, b))

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
        l_col = (255, 45, 45) if (f // 5) % 2 == 0 else [(0, 220, 255), (0, 255, 130), (255, 190, 0)][i % 3]
        draw.ellipse([(lx, dash_y + 22), (lx + 8, dash_y + 30)], fill=l_col)

    aic_x, aic_y = cx, H // 2 - 25
    rad_r = 125
    draw.ellipse([(aic_x - rad_r - 8, aic_y - rad_r - 8), (aic_x + rad_r + 8, aic_y + rad_r + 8)], fill=(14, 22, 34), outline=(0, 160, 220), width=3)
    draw.ellipse([(aic_x - rad_r, aic_y - rad_r), (aic_x + rad_r, aic_y + rad_r)], fill=(10, 15, 25), outline=(0, 220, 255), width=2)

    rad = math.radians(float(bank_angle))
    dx = int(math.cos(rad) * rad_r)
    dy = int(math.sin(rad) * rad_r)
    draw.line([(aic_x - dx, aic_y - dy), (aic_x + dx, aic_y + dy)], fill=(255, 210, 0), width=5)
    draw.ellipse([(aic_x - 6, aic_y - 6), (aic_x + 6, aic_y + 6)], fill=(255, 50, 50))
    draw.text((aic_x - 95, aic_y + rad_r + 18), f"BANK ANGLE: {bank_angle:.0f}° ROLL", font=get_font(18, True), fill=(255, 60, 60))

    draw.rounded_rectangle([(aic_x - 110, aic_y - rad_r - 65), (aic_x + 110, aic_y - rad_r - 18)], radius=8, fill=(220, 38, 38), outline=(255, 255, 255), width=2)
    draw.text((aic_x - 90, aic_y - rad_r - 50), "MASTER WARNING", font=get_font(17, True), fill=(255, 255, 255))

    if cap_img:
        cap_y = H - cap_img.height + 25
        canvas.paste(cap_img, (70, cap_y), cap_img)

    if fo_img:
        fo_x = W - fo_img.width - 80
        fo_y = H - fo_img.height + 35
        canvas.paste(fo_img, (fo_x, fo_y), fo_img)
        draw.ellipse([(fo_x + 98 - 3, fo_y + 120 - 4), (fo_x + 98 + 4, fo_y + 120 + 7)], fill=(0, 220, 255))

    _draw_comic_bubble(
        draw, 100, 150, 470, 145,
        (220, H - 420),
        "🔴 CAPTAIN (CVR TRANSCRIPT)", (220, 38, 38),
        captain_quote,
        pop_scale=1.0,
        max_chars_line=30
    )

    _draw_comic_bubble(
        draw, W - 580, 150, 480, 145,
        (W - 220, H - 420),
        "🎙️ FIRST OFFICER (CVR TRANSCRIPT)", (37, 99, 235),
        fo_quote,
        pop_scale=1.0,
        max_chars_line=30
    )

    clean_cvr_fl = flight_name.split(":")[0].split("//")[0].strip().upper()
    if len(clean_cvr_fl) > 34:
        clean_cvr_fl = clean_cvr_fl[:32] + "..."
    draw.text((90, 48), f"TACTICAL CVR RECONSTRUCTION // {clean_cvr_fl}", font=get_font(22, True), fill=(255, 215, 0))
    draw.text((W - 480, 52), f"SINK RATE: {sink_rate}", font=get_font(16, True), fill=(255, 75, 75))

    canvas.save(output_path)
    return output_path


def render_atc_tower_reconstruction(
    flight_name: str = "COMMERCIAL AIRLINER FLIGHT",
    atc_station: str = "AIRPORT TOWER // DEPARTURE RADAR",
    atc_call: str = "Radar contact lost. Turn immediately!",
    altitude_reported: str = "40 FT -> NO CLIMB",
    squawk_code: str = "SQUAWK 7700 (EMERGENCY)",
    output_path: str = "/tmp/atc_static.png"
) -> str:
    """Tek kare yüksek çözünürlüklü ATC Kule rekonstrüksiyon PNG görseli üretir."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    atc_file = ASSETS_DIR / "atc_controller.png"
    atc_img = None
    if atc_file.exists():
        a_raw = Image.open(atc_file)
        ratio = 600 / a_raw.height
        atc_img = a_raw.resize((int(a_raw.width * ratio), 600), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (W, H), (6, 12, 20))
    draw = ImageDraw.Draw(canvas)

    horiz_y = H // 2 - 40
    for y in range(0, H, 4):
        ratio = y / H
        draw.rectangle([(0, y), (W, y + 4)], fill=(int(6 + ratio * 8), int(10 + ratio * 14), int(20 + ratio * 20)))

    draw.line([(0, horiz_y), (W, horiz_y)], fill=(20, 35, 50), width=1)
    vanish_x = W // 2 + 100
    for offset, p_col in [(-220, (0, 255, 120)), (0, (255, 255, 255)), (220, (0, 255, 120))]:
        for step in range(1, 10):
            lx = int(vanish_x + (offset * (step / 10.0) * 1.8))
            ly = int(horiz_y + (step * 24))
            draw.ellipse([(lx - 2, ly - 2), (lx + 2, ly + 2)], fill=p_col)

    desk_y = H - 240
    draw.polygon([(0, desk_y), (W, desk_y), (W, H), (0, H)], fill=(11, 19, 30))
    draw.line([(0, desk_y), (W, desk_y)], fill=(0, 160, 220), width=3)

    if atc_img:
        canvas.paste(atc_img, (80, H - 610), atc_img)

    _draw_comic_bubble(
        draw, 110, 140, 680, 155,
        (260, H - 430),
        f"📡 {atc_station.upper()} (118.10 MHz)", (16, 140, 90),
        atc_call,
        pop_scale=1.0,
        max_chars_line=44
    )

    wave_y = 140 + 155 - 22
    for wx in range(140, 140 + 620, 4):
        amp = math.sin(wx * 0.08) * 8
        draw.line([(wx, wave_y - amp), (wx, wave_y + amp)], fill=(16, 220, 140), width=2)

    draw.ellipse([(730, 155), (748, 173)], fill=(16, 240, 130), outline=(255, 255, 255), width=1)
    draw.text((755, 156), "TX", font=get_font(14, True), fill=(16, 240, 130))

    rx, ry, rr = W - 470, H // 2 + 20, 250
    draw.ellipse([(rx - rr, ry - rr), (rx + rr, ry + rr)], fill=(4, 18, 12), outline=(16, 200, 130), width=3)
    for r_step in [60, 120, 180, 240]:
        draw.ellipse([(rx - r_step, ry - r_step), (rx + r_step, ry + r_step)], outline=(16, 180, 120), width=1)
    draw.line([(rx - rr, ry), (rx + rr, ry)], fill=(16, 180, 120), width=1)
    draw.line([(rx, ry - rr), (rx, ry + rr)], fill=(16, 180, 120), width=1)

    s_rad = math.radians(45)
    sx = int(rx + math.cos(s_rad) * rr)
    sy = int(ry + math.sin(s_rad) * rr)
    draw.line([(rx, ry), (sx, sy)], fill=(0, 255, 170), width=2)

    target_x = rx + 80
    target_y = ry + 85
    draw.line([(rx - 100, ry - 60), (rx - 20, ry - 25), (target_x, target_y)], fill=(255, 215, 0), width=3)
    draw.ellipse([(target_x - 8, target_y - 8), (target_x + 8, target_y + 8)], fill=(255, 50, 50), outline=(255, 255, 255), width=2)

    draw.rectangle([(target_x + 15, target_y - 30), (target_x + 225, target_y + 40)], fill=(8, 24, 16), outline=(16, 200, 130), width=1)
    draw.text((target_x + 22, target_y - 24), flight_name[:16].upper(), font=get_font(14, True), fill=(255, 255, 255))
    draw.text((target_x + 22, target_y - 5), altitude_reported, font=get_font(13, True), fill=(255, 200, 0))
    draw.text((target_x + 22, target_y + 14), squawk_code[:19], font=get_font(12, True), fill=(255, 50, 50))

    draw.text((90, 45), f"AIR TRAFFIC CONTROL AUDIO LOG // {atc_station.upper()}", font=get_font(24, True), fill=(0, 220, 255))
    draw.text((W - 500, 50), squawk_code, font=get_font(18, True), fill=(255, 60, 60))

    canvas.save(output_path)
    return output_path


def render_investigation_reconstruction(
    flight_name: str = "COMMERCIAL AIRLINER FLIGHT",
    investigating_agency: str = "NATIONAL TRANSPORTATION SAFETY BOARD (NTSB)",
    primary_finding: str = "Unconfigured takeoff and critical warning horn system failure.",
    critical_factors: list = None,
    output_path: str = "/tmp/inv_static.png"
) -> str:
    """Tek kare yüksek çözünürlüklü kaza tahkikat PNG görseli üretir."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ntsb_file = ASSETS_DIR / "ntsb_investigator.png"
    ntsb_img = None
    if ntsb_file.exists():
        n_raw = Image.open(ntsb_file)
        ratio = 600 / n_raw.height
        ntsb_img = n_raw.resize((int(n_raw.width * ratio), 600), Image.Resampling.LANCZOS)

    if not critical_factors:
        critical_factors = [
            ("FLIGHT CONTROL STATUS", "Primary control surfaces and configuration prior to incident"),
            ("COCKPIT PROCEDURES", "Crew checklist execution and human factors CRM communication"),
            ("SYSTEM WARNING INTEGRITY", "Audio-visual warning alerts and avionics system responses"),
            ("BLACK BOX RECOVERY", "Flight Data Recorder (FDR) and CVR audio successfully recovered")
        ]

    canvas = Image.new("RGB", (W, H), (8, 14, 22))
    draw = ImageDraw.Draw(canvas)

    for y in range(0, H, 4):
        ratio = y / H
        draw.rectangle([(0, y), (W, y + 4)], fill=(int(8 + ratio * 8), int(12 + ratio * 12), int(20 + ratio * 16)))
    draw.polygon([(480, 0), (620, 0), (740, H - 200), (320, H - 200)], fill=(16, 28, 42))

    table_y = H - 230
    draw.polygon([(0, table_y), (W, table_y), (W, H), (0, H)], fill=(15, 22, 32))
    draw.line([(0, table_y), (W, table_y)], fill=(40, 60, 85), width=3)

    if ntsb_img:
        canvas.paste(ntsb_img, (80, H - 610), ntsb_img)

    box_x, box_y, box_w, box_h = 390, H - 320, 170, 105
    draw.rectangle([(box_x, box_y), (box_x + box_w, box_y + box_h)], fill=(249, 115, 22), outline=(255, 255, 255), width=2)
    draw.rectangle([(box_x + 8, box_y + 8), (box_x + box_w - 8, box_y + box_h - 8)], fill=(234, 88, 12))
    draw.text((box_x + 18, box_y + 24), "FLIGHT RECORDER", font=get_font(12, True), fill=(255, 255, 255))
    draw.text((box_x + 18, box_y + 44), "DO NOT OPEN", font=get_font(11, True), fill=(255, 255, 255))
    draw.rectangle([(box_x + box_w - 32, box_y + 16), (box_x + box_w - 12, box_y + 75)], fill=(220, 220, 220), outline=(50, 50, 50), width=1)

    mag_cx, mag_cy, mag_r = 455, H - 275, 40
    draw.ellipse([(mag_cx - mag_r, mag_cy - mag_r), (mag_cx + mag_r, mag_cy + mag_r)], outline=(255, 215, 0), width=4)
    draw.line([(mag_cx + int(mag_r * 0.7), mag_cy + int(mag_r * 0.7)), (mag_cx + mag_r + 28, mag_cy + mag_r + 28)], fill=(180, 140, 20), width=6)
    draw.arc([(mag_cx - mag_r + 4, mag_cy - mag_r + 4), (mag_cx + mag_r - 4, mag_cy + mag_r - 4)], start=200, end=270, fill=(255, 255, 255), width=3)

    panel_x, panel_y, panel_w, panel_h = W - 930, 160, 850, 750
    draw.rectangle([(panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h)], fill=(12, 19, 32), outline=(0, 200, 255), width=2)
    draw.rectangle([(panel_x, panel_y), (panel_x + panel_w, panel_y + 60)], fill=(0, 140, 190))
    draw.text((panel_x + 25, panel_y + 16), "OFFICIAL INVESTIGATION DOSSIER & FINDINGS", font=get_font(20, True), fill=(255, 255, 255))

    draw.rectangle([(panel_x + panel_w - 210, panel_y + 14), (panel_x + panel_w - 25, panel_y + 46)], fill=(220, 38, 38))
    draw.text((panel_x + panel_w - 195, panel_y + 20), "OFFICIAL REPORT", font=get_font(13, True), fill=(255, 255, 255))

    draw.text((panel_x + 30, panel_y + 80), "PRIMARY INVESTIGATION FINDING:", font=get_font(15, True), fill=(255, 200, 0))
    p_lines = _wrap_text(primary_finding, 54)
    for idx, pl in enumerate(p_lines[:2]):
        draw.text((panel_x + 30, panel_y + 108 + idx * 26), pl, font=get_font(18, True), fill=(240, 245, 255))

    card_y = panel_y + 185
    for c_i, (title, desc) in enumerate(critical_factors[:4]):
        draw.rectangle([(panel_x + 25, card_y), (panel_x + panel_w - 25, card_y + 110)], fill=(16, 28, 48), outline=(0, 180, 240), width=1)
        draw.text((panel_x + 40, card_y + 12), f"FACTOR #{c_i+1}: {title}", font=get_font(15, True), fill=(0, 220, 255))
        d_lines = _wrap_text(desc, 60)
        for d_idx, dl in enumerate(d_lines[:2]):
            draw.text((panel_x + 40, card_y + 40 + d_idx * 24), dl, font=get_font(14, False), fill=(200, 215, 235))
        card_y += 130

    # Üst Bant Başlık (Metin Çakışması Kesinlikle Engellenir)
    clean_fl_name = flight_name.split(":")[0].split("//")[0].strip().upper()
    if len(clean_fl_name) > 36:
        clean_fl_name = clean_fl_name[:34] + "..."
    title_str = f"OFFICIAL ACCIDENT INVESTIGATION // {clean_fl_name}"

    font_title = get_font(22, True)
    font_agency = get_font(16, True)
    agency_str = f"AGENCY: {investigating_agency[:36]}"

    draw.text((90, 48), title_str, font=font_title, fill=(255, 215, 0))
    try:
        a_bbox = font_agency.getbbox(agency_str)
        a_w = a_bbox[2] - a_bbox[0]
    except Exception:
        a_w = len(agency_str) * 10
    draw.text((W - a_w - 90, 52), agency_str, font=font_agency, fill=(0, 220, 255))

    canvas.save(output_path)
    return output_path
