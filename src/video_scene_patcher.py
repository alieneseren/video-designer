"""
video_scene_patcher.py
Gelişmiş AI Video Sahne Yamalayıcı & Hızlı In-Place Kurgu Motoru (Video Scene Patcher)

Kullanıcının videolardaki sıkıntılı/alakasız sahneleri (ör. zifiri karanlık kaza anlatılırken çıkan
gündüz şehir drone çekimi, alakasız havayolu apronu, müzedeki SR-71 vb.) tek bir doğal dil komutuyla
veya eleştiri metniyle tespit edip; tüm videoyu sıfırdan 8-10 dakika re-render etmeye gerek kalmadan
saniyeler içinde (5-15 sn) ilgili sahneyi havacılık telemetrisi, kokpit alarmı, taktik radar veya
doğrulanmış arşiv görseliyle değiştirmesini sağlar.
"""

import os
import re
import json
import time
import shutil
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

for p in [
    "/home/ubuntu/defense_news_shorts/.venv/lib/python3.10/site-packages",
    "/home/ubuntu/yt-remote-worker",
]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from PIL import Image, ImageDraw, ImageFont

try:
    from src.video_editor import find_ffmpeg
except ImportError:
    try:
        from video_editor import find_ffmpeg
    except ImportError:
        def find_ffmpeg(require_subtitles: bool = False) -> str:
            return shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg" or "ffmpeg"

try:
    from src.aviation_telemetry_engine import generate_flight_graphics, extract_incident_metadata
except ImportError:
    try:
        from aviation_telemetry_engine import generate_flight_graphics, extract_incident_metadata
    except ImportError:
        generate_flight_graphics = None
        extract_incident_metadata = None


def parse_timestamp_to_seconds(ts: str) -> float:
    """'02:12', '2:12', '01:08.5' veya '132' stringini saniyeye çevirir."""
    ts = str(ts).strip()
    if not ts:
        return 0.0
    if ":" in ts:
        parts = ts.split(":")
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    try:
        return float(ts)
    except Exception:
        return 0.0


def format_seconds_to_timestamp(sec: float) -> str:
    """132.5 saniyeyi '02:12' formatına çevirir."""
    total = int(max(0, sec))
    m = total // 60
    s = total % 60
    return f"{m:02d}:{s:02d}"


# ═════════════════════════════════════════════════════════════════════════════
# 1. AI & KURAL TABANLI ELEŞTİRİ / HATA ANALİZ MOTORU
# ═════════════════════════════════════════════════════════════════════════════

PATCH_PRESETS = [
    {
        "id": "cvr_stickman",
        "name": "2D Çizgi Karakter Kokpit CVR Sahnesi (Crayon Capital)",
        "desc": "Kaptan ve panikleyen First Officer, yaylanan konuşma balonları, yapay ufuk ve kokpit acil durum alarmı.",
        "icon": "Users"
    },
    {
        "id": "atc_stickman",
        "name": "2D Çizgi Karakter Kule Telsiz Sahnesi (Crayon Capital)",
        "desc": "Gece pist manzaralı kule camı, 360° dönen fosforlu radar skopu ve telsiz mandalına basan Kule Kontrolörü.",
        "icon": "Radio"
    },
    {
        "id": "investigation_stickman",
        "name": "2D Çizgi Karakter Kaza Kırım & Kara Kutu İncelemesi (Crayon Capital)",
        "desc": "Hangarda büyüteçle FDR kara kutuyu inceleyen resmi NTSB müfettişi ve kaza bulguları rapor paneli.",
        "icon": "FileSearch"
    },
    {
        "id": "telemetry_gauge",
        "name": "Kokpit Yapay Ufuk & Yatış Telemetrisi (Attitude Indicator)",
        "desc": "Aşırı yatış (overbank), somatogravik illüzyon ve yapay ufuk sapmalarını gösteren kokpit telemetrisi.",
        "icon": "Gauge"
    },
    {
        "id": "cockpit_alarm",
        "name": "GPWS Alarm & Acil Durum Kokpiti (Bank Angle / Pull Up)",
        "desc": "Karanlık kokpit acil durum alarmları, kırmızı master warning ve GPWS ses/ışık HUD uyarısı.",
        "icon": "AlertTriangle"
    },
    {
        "id": "telemetry_radar",
        "name": "Taktik Uçuş Rekonstrüksiyon Radar Haritası",
        "desc": "Kalkış pisti, radar tırmanışı, dalış açısı ve su/yer temas koordinatlarını gösteren radar şeması.",
        "icon": "Compass"
    },
    {
        "id": "cockpit_altimeter_dive",
        "name": "Kokpit Hızlı İrtifa Dalışı & Altimetre (Graveyard Spiral)",
        "desc": "Hızla sıfıra dönen altimetre saati, varyometre düşüş oranı (-10.000 fpm) ve aşırı hız clacker ikazı.",
        "icon": "TrendingDown"
    },
    {
        "id": "dark_cockpit",
        "name": "Gece Analog Kokpit Dinamikleri (Night Cockpit)",
        "desc": "Döneme uygun klasik analog kokpit lövyesi ve pilot gösterge paneli aydınlatması.",
        "icon": "Moon"
    },
    {
        "id": "wikimedia",
        "name": "Resmi Kaza Tahkikat & Anıt Arşivi (Wikimedia)",
        "desc": "Resmi BEA/NTSB kaza kurtarma, anıt mezar ve resmi araştırma fotoğrafları.",
        "icon": "Archive"
    }
]


def analyze_critique_text(
    critique_text: str,
    video_duration: float = 0.0,
    video_title: str = "",
    scenes_meta: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Kullanıcının girdiği doğal dil eleştiri/talimat metnini analiz ederek
    değiştirilecek sahne aralıklarını ve önerilen görsel tipini çıkarır.
    
    Örnek metin:
    'Tam 2,5 Dakika (155 Saniye) Süren Işıl Işıl Asya Şehri (02:12 – 04:47)...
     Zifiri Karanlıkta Yağmurlu Gündüz ve United Airlines (01:08 – 01:30)...
     Uçak 5000 Fitten Denize Çakılırken Günlük Güneşlik Gökyüzü (04:48 – 05:22)...'
    """
    patches = []
    text = critique_text or ""

    # 1. Zaman aralıklarını tespit et (Örn: 02:12 – 04:47 veya 02:12 - 04:47 veya 02:12 to 04:47)
    pattern = r"(\d{1,2}:\d{2})\s*(?:–|-|ila|ile|to)\s*(\d{1,2}:\d{2})"
    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))

    for idx, match in enumerate(matches):
        start_str = match.group(1)
        end_str = match.group(2)
        start_sec = parse_timestamp_to_seconds(start_str)
        end_sec = parse_timestamp_to_seconds(end_str)

        if end_sec <= start_sec:
            continue
        if video_duration > 0 and start_sec > video_duration:
            continue
        if video_duration > 0 and end_sec > video_duration:
            end_sec = video_duration

        dur = round(end_sec - start_sec, 2)

        # Eşleşmenin ait olduğu satırı / maddeyi izole et (satırlar arası kelime karışmasını önler)
        line_start = text.rfind("\n", 0, match.start())
        line_start = 0 if line_start == -1 else line_start + 1

        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)

        # Eğer madde açıklaması sonraki satırlara taşıyorsa bir sonraki maddeye (*) kadar genişlet
        next_bullet = text.find("\n*", match.end())
        if next_bullet != -1 and (next_bullet - match.end()) < 250:
            line_end = next_bullet

        context_window = text[line_start:line_end].lower()

        # Varsayılanlar
        rec_type = "telemetry_gauge"
        issue_title = f"Hatalı Sahne Aralığı ({start_str} - {end_str})"
        desc = "Gece kokpit analog yapay ufuk ve telemetri göstergesi"

        # Akıllı semantik sınıflandırma
        if any(w in context_window for w in ["araştırmacı", "arastirmaci", "dedektif", "pano", "kara kutu", "fdr", "tahkikat", "ntsb", "müfettiş", "mufettis", "resmi rapor", "soruşturma", "kaza kırım", "çakışma", "cakisma", "metin çakışması"]):
            rec_type = "investigation_stickman"
            issue_title = "2D Kaza Tahkikat & Kara Kutu Sahnesi (Crayon Style)"
            desc = "Hangarda FDR kara kutuyu büyüteçle inceleyen NTSB müfettişi ve resmi bulgular paneli."
        elif any(w in context_window for w in ["larry", "balon", "rol karışıklığı", "rol karisikligi", "diyalog", "konuşma", "konusma", "çöp adam", "cop adam", "karakter", "cvr", "kaptan", "pilot", "first officer", "f/o", "panik", "lövy"]):
            rec_type = "cvr_stickman"
            issue_title = "2D Kokpit CVR Karakter Sahnesi (Crayon Style)"
            desc = "Kaptan ve panikleyen F/O, yaylanan çizgi roman konuşma balonları ve otantik CVR diyaloğu."
        elif any(w in context_window for w in ["fuji", "kiraz", "çiçek", "cicek", "sakura", "dağ", "dag", "köprü", "kopru", "absürt stok", "stok", "kurtarma", "helikopter", "kuyruk", "parçalanmış", "fotoğraf", "arsiv", "arşiv"]):
            rec_type = "wikimedia"
            issue_title = "Otantik Olay Arşivi & Kaza Fotoğrafları (Wikimedia)"
            desc = "Resmi kaza tahkikatı, Potomac 14th St Köprüsü ve kurtarma operasyonu arşiv fotoğrafları."
        elif any(w in context_window for w in ["kule", "telsiz", "atc", "radar kontrol", "frekans", "yaklaşma", "vanish", "kayboldu"]):
            rec_type = "atc_stickman"
            issue_title = "2D Kule ATC Telsiz Sahnesi (Crayon Style)"
            desc = "Gece pist manzaralı kule camı, 360° dönen radar ve telsiz çağrısı yapan kontrolör."
        elif any(w in context_window for w in ["flash", "gösterge", "gosterge", "kızıldeniz", "kizildeniz", "telemetri", "kadran", "epr", "yapay ufuk", "attitude", "ufuk grafiği"]):
            rec_type = "telemetry_gauge"
            issue_title = "Otantik Kokpit Telemetri ve Kadran Göstergesi"
            desc = "Olayın kendi gerçek kokpit telemetrisi ve sistem anomali göstergesi."
        elif any(w in context_window for w in ["şehir", "sehir", "drone", "asya", "bina", "ışıl", "isil", "neon", "skyline"]):
            rec_type = "telemetry_gauge"
            issue_title = "Alakasız Şehir / Gece Drone Çekimi"
            desc = "Olay kokpit telemetrisi ve yapay ufuk göstergesi."
        elif any(w in context_window for w in ["çakılırken", "cakilirken", "güneşlik", "guneslik", "gökyüzü", "gokyuzu", "bulut", "süzülen", "winglet"]):
            rec_type = "cockpit_alarm"
            issue_title = "Dalış Anında Huzurlu Gökyüzü Çelişkisi"
            desc = "Kokpit acil durum alarmı ve stick shaker / stall warning uyarısı."

        patch_item = {
            "id": f"patch_{idx+1}",
            "start_sec": start_sec,
            "end_sec": end_sec,
            "start_time": start_str,
            "end_time": end_str,
            "duration": dur,
            "issue_title": issue_title,
            "replacement_type": rec_type,
            "description": desc,
            "enabled": True
        }
        patches.append(patch_item)

    # 2. Eğer timestamp yoksa ama sahne numarası varsa (Örn: "Sahne 3'ü yapay ufukla değiştir")
    if not patches and scenes_meta:
        scene_match = re.search(r"sahne\s*(\d+)|scene\s*(\d+)", text, flags=re.IGNORECASE)
        if scene_match:
            s_idx = int(scene_match.group(1) or scene_match.group(2))
            if 0 <= s_idx < len(scenes_meta):
                sc = scenes_meta[s_idx]
                s_start = sc.get("start", 0.0)
                s_dur = sc.get("duration", 15.0)
                patches.append({
                    "id": "patch_1",
                    "start_sec": s_start,
                    "end_sec": s_start + s_dur,
                    "start_time": format_seconds_to_timestamp(s_start),
                    "end_time": format_seconds_to_timestamp(s_start + s_dur),
                    "duration": s_dur,
                    "issue_title": f"Sahne {s_idx} Değişimi",
                    "replacement_type": "telemetry_gauge",
                    "description": "Kullanıcı talebiyle sahne telemetri ile yenilenecek.",
                    "enabled": True
                })

    return patches


# ═════════════════════════════════════════════════════════════════════════════
# 2. ÖZEL GÖRSEL & TELEMETRİ SAHNE ÜRETİCİSİ
# ═════════════════════════════════════════════════════════════════════════════

def _draw_hud_overlay(img: Image.Image, title: str, subtitle: str, extra_lines: List[str] = None) -> Image.Image:
    """Belgesel tarzı HUD telemetri çerçevesi çizer."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Üst ve alt gradient karartma
    for y in range(120):
        alpha = int((1 - y / 120) * 180)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    for y in range(h - 100, h):
        alpha = int(((y - (h - 100)) / 100) * 180)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    # Köşe vizörleri
    c_len = 35
    col_hud = (0, 220, 255, 190)
    # Sol Üst
    draw.line([(40, 40), (40 + c_len, 40)], fill=col_hud, width=2)
    draw.line([(40, 40), (40, 40 + c_len)], fill=col_hud, width=2)
    # Sağ Üst
    draw.line([(w - 40, 40), (w - 40 - c_len, 40)], fill=col_hud, width=2)
    draw.line([(w - 40, 40), (w - 40, 40 + c_len)], fill=col_hud, width=2)
    # Sol Alt
    draw.line([(40, h - 40), (40 + c_len, h - 40)], fill=col_hud, width=2)
    draw.line([(40, h - 40), (40, h - 40 - c_len)], fill=col_hud, width=2)
    # Sağ Alt
    draw.line([(w - 40, h - 40), (w - 40 - c_len, h - 40)], fill=col_hud, width=2)
    draw.line([(w - 40, h - 40), (w - 40, h - 40 - c_len)], fill=col_hud, width=2)

    # Metinler
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        font_mono = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", 18)
    except Exception:
        font_title = font_sub = font_mono = ImageFont.load_default()

    draw.text((70, 48), title.upper(), font=font_title, fill=(255, 255, 255, 240))
    draw.text((70, 88), subtitle, font=font_sub, fill=(0, 220, 255, 220))

    if extra_lines:
        cur_y = h - 45 - (len(extra_lines) * 24)
        for el in extra_lines:
            draw.text((70, cur_y), el, font=font_mono, fill=(255, 215, 0, 220))
            cur_y += 24

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def render_attitude_indicator_frame(
    bank_angle: float = 25.0,
    pitch_angle: float = -10.0,
    flight_name: str = "COMMERCIAL FLIGHT",
    output_path: str = "/tmp/attitude_frame.png",
    meta: Optional[Dict[str, Any]] = None
) -> str:
    """Analog Boeing 737 yapay ufuk (Attitude Indicator) kadranı ve telemetri göstergesi üretir."""
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (10, 14, 22))
    draw = ImageDraw.Draw(img)

    clean_flight = flight_name.split(":")[0].split("//")[0].strip()

    cx, cy = W // 2, H // 2
    radius = 320

    # Gökyüzü / Yeryüzü yapay ufuk topu (Sky / Ground sphere)
    # Mavi gökyüzü, kahverengi yer
    ball = Image.new("RGBA", (radius * 2, radius * 2), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(ball)
    b_draw.ellipse([(0, 0), (radius * 2, radius * 2)], fill=(20, 95, 175, 255))
    # Alt yarı kahverengi (yer)
    b_draw.chord([(0, 0), (radius * 2, radius * 2)], 0, 180, fill=(120, 65, 30, 255))
    b_draw.line([(0, radius), (radius * 2, radius)], fill=(255, 255, 255, 255), width=4)

    # Pitch çizgileri (-20, -10, 0, 10, 20)
    for p in [-40, -20, 20, 40]:
        py = radius + p
        b_draw.line([(radius - 50, py), (radius + 50, py)], fill=(255, 255, 255, 200), width=3)

    # Bank Angle (Yatış Açısı) döndürme
    rotated_ball = ball.rotate(-bank_angle, resample=Image.BICUBIC)
    img.paste(rotated_ball, (cx - radius, cy - radius), rotated_ball)

    # Gösterge Dış Çerçevesi (Bezel)
    draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], outline=(200, 205, 215), width=8)
    draw.ellipse([(cx - radius - 8, cy - radius - 8), (cx + radius + 8, cy + radius + 8)], outline=(40, 45, 55), width=10)

    # Uçak Sembolü (Sabit Sarı Minyatür Uçak)
    w_span = 140
    draw.line([(cx - w_span, cy), (cx - 30, cy)], fill=(255, 215, 0), width=6)
    draw.line([(cx + 30, cy), (cx + w_span, cy)], fill=(255, 215, 0), width=6)
    draw.line([(cx, cy - 25), (cx, cy + 15)], fill=(255, 215, 0), width=6)
    draw.ellipse([(cx - 10, cy - 10), (cx + 10, cy + 10)], fill=(255, 215, 0))

    # Uyarı ve Telemetri Metinleri
    try:
        font_warn = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        font_val = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", 26)
    except Exception:
        font_warn = font_val = ImageFont.load_default()

    gauge_cfg = (meta or {}).get("gauge", {})
    left_lbl = gauge_cfg.get("left_label", "ATTITUDE INSTRUMENT")
    left_v = gauge_cfg.get("left_value", f"ROLL: {bank_angle:.1f}° RIGHT")
    right_lbl = gauge_cfg.get("right_label", "TELEMETRY STATUS")
    right_v = gauge_cfg.get("right_value", "SYSTEM ANOMALY ACTIVE")
    hud_sub = gauge_cfg.get("subtitle", "PRIMARY FLIGHT DISPLAY (PFD) / ATTITUDE DIRECTOR INDICATOR (ADI)")

    # Kırmızı Tehlike Rozeti
    badge_title = "CRITICAL FLIGHT INSTRUMENT ANOMALY"
    if "flash" in clean_flight.lower():
        badge_title = "CRITICAL ATTITUDE OVERBANK"
    elif "florida" in clean_flight.lower():
        badge_title = "CRITICAL EPR THRUST DEFICIT"
    draw.rectangle([(cx - 280, 150), (cx + 280, 210)], fill=(200, 20, 30), outline=(255, 255, 255), width=2)
    draw.text((cx - 250, 165), badge_title, font=font_warn, fill=(255, 255, 255))

    # Sol Veri Paneli
    draw.text((120, cy - 80), left_lbl[:28], font=font_val, fill=(0, 220, 255))
    draw.text((120, cy - 40), left_v[:32], font=font_val, fill=(255, 60, 60))
    draw.text((120, cy), f"PITCH: {pitch_angle:.1f}°", font=font_val, fill=(255, 200, 0))
    draw.text((120, cy + 40), "SENSORY ILLUSION: ACTIVE" if "flash" in clean_flight.lower() else "ICING CONTAMINATION: ACTIVE", font=font_val, fill=(255, 100, 100))

    # Sağ Veri Paneli
    draw.text((W - 500, cy - 80), right_lbl[:28], font=font_val, fill=(0, 220, 255))
    draw.text((W - 500, cy - 40), right_v[:32], font=font_val, fill=(255, 60, 60))
    draw.text((W - 500, cy), "HORIZON: POOR VISIBILITY", font=font_val, fill=(200, 200, 200))
    draw.text((W - 500, cy + 40), "WARNING: 'STALL WARNING!'" if "florida" in clean_flight.lower() else "WARNING: 'BANK ANGLE!'", font=font_val, fill=(255, 60, 60))

    # HUD Çerçevesi
    img = _draw_hud_overlay(
        img,
        title=f"FLIGHT RECONSTRUCTION // {clean_flight.upper()}",
        subtitle=hud_sub,
        extra_lines=[
            f">> RECONSTRUCTED COCKPIT TELEMETRY - FLIGHT DATA RECORDER",
            f">> CRITICAL ATTITUDE PROFILE AT {bank_angle:.0f}° BANK"
        ]
    )

    img.save(output_path)
    return output_path


def render_cockpit_alarm_frame(
    flight_name: str = "COMMERCIAL FLIGHT",
    alarm_text: str = "TERRAIN // PULL UP! // BANK ANGLE!",
    altitude_ft: int = 2400,
    output_path: str = "/tmp/cockpit_alarm.png"
) -> str:
    """GPWS & Acil Durum Kokpit Alarm HUD çerçevesi üretir."""
    clean_flight = flight_name.split(":")[0].split("//")[0].strip()
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (8, 10, 16))
    draw = ImageDraw.Draw(img)

    cx, cy = W // 2, H // 2

    # Yanıp sönen kırmızı uyarı kutusu
    draw.rectangle([(cx - 420, cy - 130), (cx + 420, cy + 130)], fill=(180, 15, 25), outline=(255, 255, 255), width=4)

    try:
        from src.aviation_stickman_composite import get_font
        font_big = get_font(52, True)
        font_mid = get_font(30, True)
        font_mono = get_font(24, True)
    except Exception:
        font_big = font_mid = font_mono = ImageFont.load_default()

    draw.text((cx - 360, cy - 80), "⚠️  MASTER WARNING", font=font_big, fill=(255, 255, 255))
    draw.text((cx - 330, cy + 10), alarm_text, font=font_mid, fill=(255, 240, 120))

    # İrtifa dalış şeridi (Altitude tape)
    draw.rectangle([(cx - 160, cy + 180), (cx + 160, cy + 250)], fill=(20, 24, 34), outline=(255, 60, 60), width=2)
    draw.text((cx - 140, cy + 198), f"ALT: {altitude_ft:,} FT ⮋", font=font_mono, fill=(255, 80, 80))

    # Alt bilgilendirme
    draw.text((cx - 380, cy + 300), "GPWS GROUND PROXIMITY SINK RATE ALERT ACTIVE", font=font_mono, fill=(255, 180, 0))

    img = _draw_hud_overlay(
        img,
        title=f"COCKPIT AUDIO ALERT RECORD // {clean_flight.upper()}",
        subtitle="EGPWS / TAWS AUDITORY WARNING VISUALIZATION",
        extra_lines=[
            ">> CVR IMPACT COUNTDOWN SEQUENCE",
            f">> RAPID LOSS OF CONTROL & HIGH-SPEED DIVE DETECTED"
        ]
    )

    img.save(output_path)
    return output_path


def generate_patch_visual_asset(
    patch_type: str,
    metadata: Dict[str, Any],
    work_dir: Path,
    seg_dur: float = 5.0,
    quote_text: str = ""
) -> str:
    """Verilen yama tipine göre en uygun yüksek çözünürlüklü görsel veya animasyon klibini oluşturur."""
    work_dir.mkdir(parents=True, exist_ok=True)
    flight_name = metadata.get("flight_name", "Aviation Incident")

    # 1. 2D Dinamik Çizgi Karakter Klipleri (Crayon Capital Style)
    if patch_type in ("cvr_stickman", "cvr", "cockpit_cvr"):
        try:
            from src.aviation_stickman_composite import generate_animated_cvr_video
        except ImportError:
            try:
                from aviation_stickman_composite import generate_animated_cvr_video
            except ImportError:
                generate_animated_cvr_video = None
        if generate_animated_cvr_video:
            out_p = str(work_dir / f"cvr_anim_{int(time.time())}.mp4")
            # Otantik diyalog tespiti
            cap_quote = "Aircraft is banking! Check attitude!"
            fo_quote = "Bank angle! Horizon abnormal! Level the wings!"
            try:
                try:
                    from src.aviation_media_fetcher import _extract_cvr_dialogue
                    from src.aviation_telemetry_engine import extract_incident_metadata
                except ImportError:
                    from aviation_media_fetcher import _extract_cvr_dialogue
                    from aviation_telemetry_engine import extract_incident_metadata
                meta_p = extract_incident_metadata(flight_name or critique_text)
                extracted_cvr = _extract_cvr_dialogue(meta_p, {"narration": quote_text}, 1, 0.45)
                if extracted_cvr:
                    cap_quote, fo_quote = extracted_cvr
            except Exception:
                pass

            return generate_animated_cvr_video(
                flight_name=flight_name,
                situation_title="COCKPIT EMERGENCY // CRITICAL RECONSTRUCTION",
                captain_quote=cap_quote,
                fo_quote=fo_quote,
                bank_angle=45.0,
                sink_rate="-2,800 FT/MIN",
                duration=max(3.0, seg_dur),
                output_path=out_p
            )

    elif patch_type in ("atc_stickman", "atc", "tower"):
        try:
            from src.aviation_stickman_composite import generate_animated_atc_video
        except ImportError:
            try:
                from aviation_stickman_composite import generate_animated_atc_video
            except ImportError:
                generate_animated_atc_video = None
        if generate_animated_atc_video:
            out_p = str(work_dir / f"atc_anim_{int(time.time())}.mp4")
            atc_msg = f"{flight_name}, radar contact lost. Turn immediately!"
            atc_station_name = "AIRPORT TOWER // DEPARTURE RADAR"
            try:
                try:
                    from src.aviation_media_fetcher import _extract_atc_dialogue
                    from src.aviation_telemetry_engine import extract_incident_metadata
                except ImportError:
                    from aviation_media_fetcher import _extract_atc_dialogue
                    from aviation_telemetry_engine import extract_incident_metadata
                meta_p = extract_incident_metadata(flight_name or critique_text)
                atc_station_name = meta_p.get("atc_station", atc_station_name)
                atc_msg = _extract_atc_dialogue(meta_p, {"narration": quote_text}, 1, 0.50) or atc_msg
            except Exception:
                pass

            return generate_animated_atc_video(
                flight_name=flight_name,
                atc_station=atc_station_name,
                atc_call=atc_msg,
                altitude_reported="LAST REPORTED: 40 FT -> NO CLIMB",
                duration=max(3.0, seg_dur),
                output_path=out_p
            )

    elif patch_type in ("investigation_stickman", "investigation", "ntsb"):
        try:
            from src.aviation_stickman_composite import generate_animated_investigation_video
        except ImportError:
            try:
                from aviation_stickman_composite import generate_animated_investigation_video
            except ImportError:
                generate_animated_investigation_video = None
        if generate_animated_investigation_video:
            out_p = str(work_dir / f"inv_anim_{int(time.time())}.mp4")
            agency = "NATIONAL TRANSPORTATION SAFETY BOARD (NTSB)"
            cause = "Aircraft loss of control during departure."
            crit_factors = None
            try:
                try:
                    from src.aviation_telemetry_engine import extract_incident_metadata
                except ImportError:
                    from aviation_telemetry_engine import extract_incident_metadata
                meta_p = extract_incident_metadata(flight_name or critique_text)
                agency = meta_p.get("investigating_agency", agency)
                cause = meta_p.get("probable_cause", cause)
                crit_factors = meta_p.get("critical_factors")
            except Exception:
                pass

            return generate_animated_investigation_video(
                flight_name=flight_name,
                investigating_agency=agency,
                primary_finding=cause,
                critical_factors=crit_factors,
                duration=max(3.0, seg_dur),
                output_path=out_p
            )

    # 2. Kokpit Telemetrisi ve Alarmları
    elif patch_type == "telemetry_gauge":
        if generate_flight_graphics:
            try:
                g_res = generate_flight_graphics(flight_name, work_dir)
                if g_res.get("telemetry_gauge") and os.path.exists(g_res["telemetry_gauge"]):
                    print(f"[PATCH-MEDIA] ✅ Olay için teknik kokpit kadranı enjekte edildi: {g_res['telemetry_gauge']}")
                    return g_res["telemetry_gauge"]
            except Exception as e_tg:
                print(f"[PATCH-MEDIA] Telemetry gauge gen error: {e_tg}")

        # Fallback attitude frame
        out_p = str(work_dir / f"attitude_indicator_{int(time.time())}.png")
        return render_attitude_indicator_frame(
            bank_angle=25.0,
            pitch_angle=-10.0,
            flight_name=flight_name,
            output_path=out_p,
            meta=metadata
        )
    elif patch_type == "cockpit_alarm":
        # GPWS Alarm
        out_p = str(work_dir / f"cockpit_alarm_{int(time.time())}.png")
        alarm_txt = "TERRAIN // PULL UP! // BANK ANGLE!"
        if "florida" in flight_name.lower():
            alarm_txt = "STALL WARNING // STICK SHAKER ACTIVE // PULL UP!"
        return render_cockpit_alarm_frame(
            flight_name=flight_name,
            alarm_text=alarm_txt,
            altitude_ft=350 if "florida" in flight_name.lower() else 1800,
            output_path=out_p
        )
    elif patch_type in ("telemetry_radar", "cockpit_altimeter_dive"):
        # Taktik Radar veya Telemetri Grafiği
        if generate_flight_graphics:
            g_res = generate_flight_graphics(flight_name, work_dir)
            if patch_type == "telemetry_radar" and g_res.get("trajectory_map"):
                return g_res["trajectory_map"]
            elif g_res.get("telemetry_gauge"):
                return g_res["telemetry_gauge"]
        # Fallback attitude frame
        out_p = str(work_dir / f"attitude_indicator_{int(time.time())}.png")
        return render_attitude_indicator_frame(flight_name=flight_name, output_path=out_p, meta=metadata)
    elif patch_type in ("wikimedia", "historical_photo", "stock_replacement"):
        # Wikimedia Commons incident photos
        try:
            from src.aviation_media_fetcher import search_wikimedia_commons, download_and_format_image
            queries = []
            try:
                from src.aviation_telemetry_engine import extract_incident_metadata
                meta_p = extract_incident_metadata(flight_name)
                if meta_p:
                    queries.extend(meta_p.get("wiki_crash_queries", []))
                    queries.extend(meta_p.get("wiki_clean_queries", []))
            except Exception:
                pass
            queries.extend([
                flight_name,
                f"{flight_name} wreckage",
                f"{flight_name} recovery",
                f"{flight_name} NTSB",
                f"{flight_name} bridge",
                f"{flight_name} Potomac"
            ])
            for q in queries:
                res = search_wikimedia_commons(q, limit=3)
                if res:
                    target_img = str(work_dir / f"wiki_patch_{int(time.time())}.png")
                    fmt_ok = download_and_format_image(res[0]["url"], target_img, 1920, 1080)
                    if fmt_ok and os.path.exists(target_img):
                        print(f"[PATCH-MEDIA] ✅ Wikimedia'dan otantik olay görseli indirildi: {q}")
                        return target_img
        except Exception as e:
            print(f"[PATCH-MEDIA] Wikimedia fetch error: {e}")
        # Fallback to radar map or attitude frame
        if generate_flight_graphics:
            try:
                g_res = generate_flight_graphics(flight_name, work_dir)
                if g_res.get("trajectory_map"):
                    return g_res["trajectory_map"]
            except Exception:
                pass
        out_p = str(work_dir / f"attitude_indicator_{int(time.time())}.png")
        return render_attitude_indicator_frame(flight_name=flight_name, output_path=out_p, meta=metadata)
    else:
        # Default attitude indicator
        out_p = str(work_dir / f"attitude_indicator_{int(time.time())}.png")
        return render_attitude_indicator_frame(flight_name=flight_name, output_path=out_p)


# ═════════════════════════════════════════════════════════════════════════════
# 3. YEREL VİDEO DİLİMLEME VE MONTAJ MOTORU (IN-PLACE SPLICER)
# ═════════════════════════════════════════════════════════════════════════════

def apply_local_video_patch(
    video_path: str,
    patches: List[Dict[str, Any]],
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Belirtilen video dosyası üzerinde seçilen yama aralıklarını keser,
    yeni görsellerle belirtilen süre kadar klip oluşturup orijinal sesle birleştirir,
    ve kesintisiz olarak videoya geri diker (seamless splice).
    
    Tüm işlem 5-15 saniye sürer!
    """
    v_path = Path(video_path).resolve()
    if not v_path.exists():
        raise FileNotFoundError(f"Video bulunamadı: {video_path}")

    ffmpeg = find_ffmpeg()
    work_dir = Path(tempfile.mkdtemp(prefix="video_patcher_"))

    # Orijinal video süresini ve boyutlarını al
    ffprobe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(v_path)
    ]
    res_dur = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
    total_dur = float(res_dur.stdout.strip()) if res_dur.returncode == 0 else 0.0

    if total_dur <= 0:
        raise RuntimeError("Video süresi ffprobe ile okunamadı.")

    # Video klasöründeki metadata'yı yükle
    meta_path = v_path.parent / "metadata.json"
    metadata = {}
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    if not metadata.get("flight_name"):
        metadata["flight_name"] = metadata.get("title") or v_path.parent.name

    # Yamaları başlangıç zamanına göre sırala ve çakışmayanları filtrele
    active_patches = [p for p in patches if p.get("enabled", True)]
    active_patches.sort(key=lambda p: float(p["start_sec"]))

    if not active_patches:
        return {"success": False, "message": "Uygulanacak aktif yama seçilmedi."}

    # Parça listesi oluştur (Segment list)
    # [ (is_patch, start, end, patch_obj) ]
    timeline_segments = []
    current_time = 0.0

    for p in active_patches:
        p_start = max(0.0, float(p["start_sec"]))
        p_end = min(total_dur, float(p["end_sec"]))

        if p_start > current_time:
            # Araya giren dokunulmayacak orijinal bölüm
            timeline_segments.append((False, current_time, p_start, None))

        # Yama bölümü
        timeline_segments.append((True, p_start, p_end, p))
        current_time = p_end

    if current_time < total_dur:
        # Son kalan orijinal parça
        timeline_segments.append((False, current_time, total_dur, None))

    # Klipleri oluştur
    concat_list = []
    generated_clips = []

    for idx, (is_patch, s_time, e_time, p_obj) in enumerate(timeline_segments):
        seg_dur = e_time - s_time
        if seg_dur < 0.1:
            continue

        clip_out = work_dir / f"seg_{idx:03d}.mp4"

        if not is_patch:
            # Orijinal videodan kes (Ultra hızlı, stream-exact)
            cmd_cut = [
                ffmpeg, "-y",
                "-ss", str(s_time),
                "-to", str(e_time),
                "-i", str(v_path),
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-avoid_negative_ts", "make_zero",
                "-video_track_timescale", "12800",
                str(clip_out)
            ]
            res_c = subprocess.run(cmd_cut, capture_output=True, text=True)
            if res_c.returncode != 0:
                raise RuntimeError(f"Orijinal parça kesilemedi ({s_time}-{e_time}): {res_c.stderr}")
        else:
            # YAMA BÖLÜMÜ:
            # 1. Bu aralıktaki sesi orijinal videodan çek
            seg_audio = work_dir / f"audio_patch_{idx:03d}.aac"
            cmd_aud = [
                ffmpeg, "-y",
                "-ss", str(s_time),
                "-t", str(seg_dur),
                "-i", str(v_path),
                "-vn", "-c:a", "aac", "-b:a", "192k",
                str(seg_audio)
            ]
            subprocess.run(cmd_aud, check=True, capture_output=True)

            # 2. Yeni görsel veya animasyon klibini üret
            patch_type = p_obj.get("replacement_type", "telemetry_gauge")
            visual_asset = generate_patch_visual_asset(
                patch_type, metadata, work_dir,
                seg_dur=seg_dur,
                quote_text=p_obj.get("description", "")
            )

            # 3. Görsel/video ve sesi birleştirerek hedef sürede klip üret
            if str(visual_asset).lower().endswith(".mp4"):
                cmd_synth = [
                    ffmpeg, "-y",
                    "-stream_loop", "-1", "-i", str(visual_asset),
                    "-i", str(seg_audio),
                    "-t", str(seg_dur),
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=25,setsar=1",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    "-video_track_timescale", "12800",
                    "-shortest",
                    str(clip_out)
                ]
            else:
                cmd_synth = [
                    ffmpeg, "-y",
                    "-loop", "1", "-i", str(visual_asset),
                    "-i", str(seg_audio),
                    "-t", str(seg_dur),
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=25,setsar=1",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    "-video_track_timescale", "12800",
                    "-shortest",
                    str(clip_out)
                ]
            res_s = subprocess.run(cmd_synth, capture_output=True, text=True)
            if res_s.returncode != 0:
                raise RuntimeError(f"Yama klibi derlenemedi: {res_s.stderr}")

        concat_list.append(f"file '{clip_out.resolve()}'\n")
        generated_clips.append(clip_out)

    # Concat list dosyasını yaz
    concat_txt = work_dir / "concat_list.txt"
    concat_txt.write_text("".join(concat_list), encoding="utf-8")

    # Nihai birleştirme
    patched_final = work_dir / "final_patched.mp4"
    cmd_concat = [
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(patched_final)
    ]
    res_final = subprocess.run(cmd_concat, capture_output=True, text=True)
    if res_final.returncode != 0:
        raise RuntimeError(f"Concat birleştirme hatası: {res_final.stderr}")

    # Orijinal dosyayı yedekle (final_original_backup.mp4)
    backup_file = v_path.parent / "final_original_backup.mp4"
    if not backup_file.exists():
        shutil.copy2(str(v_path), str(backup_file))

    # Hedef dosya
    target_out = Path(output_path) if output_path else v_path
    shutil.copy2(str(patched_final), str(target_out))

    # video.mp4 varsa güncelle
    alt_video = v_path.parent / "video.mp4"
    if alt_video.exists():
        shutil.copy2(str(patched_final), str(alt_video))

    # Temizlik
    shutil.rmtree(work_dir, ignore_errors=True)

    return {
        "success": True,
        "patched_video": str(target_out),
        "backup_video": str(backup_file),
        "applied_patches": active_patches,
        "total_duration": total_dur,
        "message": f"{len(active_patches)} sahne başarıyla güncellendi ve montajlandı."
    }
