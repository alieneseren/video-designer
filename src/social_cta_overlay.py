"""
social_cta_overlay.py
======================
Evrensel Sosyal Medya Çağrı Katmanı (Universal Transparent Social CTA Overlay).
Tüm Kanallar (Seyahat, Crayon Combat, Havacılık, Belgesel, Spor):

1. Video devam ederken arka planı %100 transparan (Alpha Channel) olacak şekilde:
   - Kanal diline göre "Abone Ol" / "Subscribe" buton animasyonu
   - Beğenme (Like / Thumbs-up) tıklama animasyonu
   - Bildirim Çanı (Bell) çalma/titreme animasyonu
   - Hareketli imleç ve dokunma/tıklama dalgası (click ripple)
2. Videonun süresini 1 milisaniye bile bozmaz (uzatmaz / kısaltmaz).
3. Hem videonun başında (3.0s - 7.5s, Hook sonrası) hem de sonunda (son 5 saniye)
   en yüksek dönüşüm sağlayacak şekilde iki kez devreye girer.
4. Önbellekleme (Cache) sistemi sayesinde dili ve çözünürlüğü bir kez render eder,
   sonraki tüm videolarda anında (0 gecikmeyle) overlay olarak giydirir.
"""

from __future__ import annotations

import os
import math
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple
from PIL import Image, ImageDraw, ImageFont


# Çok dilli metin sözlüğü (Kanalın diline göre otomatik seçilir)
LOCALIZED_CTA: Dict[str, Dict[str, str]] = {
    "en": {"subscribe": "SUBSCRIBE", "subscribed": "SUBSCRIBED"},
    "tr": {"subscribe": "ABONE OL", "subscribed": "ABONE OLUNDU"},
    "de": {"subscribe": "ABONNIEREN", "subscribed": "ABONNIERT"},
    "es": {"subscribe": "SUSCRÍBETE", "subscribed": "SUSCRITO"},
    "fr": {"subscribe": "S'ABONNER", "subscribed": "ABONNÉ"},
    "it": {"subscribe": "ISCRIVITI", "subscribed": "ISCRITTO"},
    "pt": {"subscribe": "INSCREVER-SE", "subscribed": "INSCRITO"},
    "ru": {"subscribe": "ПОДПИСАТЬСЯ", "subscribed": "ВЫ ПОДПИСАНЫ"},
    "ja": {"subscribe": "チャンネル登録", "subscribed": "登録済み"},
    "ar": {"subscribe": "اشتراك", "subscribed": "مشترك"}
}


def get_cta_font(size: int = 24) -> ImageFont.FreeTypeFont:
    """Sistemde ve ortamda bulunan en uygun kalın sans-serif yazı tipini yükler."""
    candidates = [
        "/System/Library/Fonts/SFPro-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Users/alienes/yt-oto-video/files/.venv/lib/python3.14/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_thumbs_up(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, is_liked: bool = False):
    """Modern YouTube Thumbs-up (Beğeni) vektör ikonunu çizer."""
    c_fill = (62, 166, 255, 255) if is_liked else (255, 255, 255, 240)
    c_outline = (30, 130, 230, 255) if is_liked else (255, 255, 255, 200)

    # Bilek/kuff
    kw = int(8 * scale)
    kh = int(24 * scale)
    draw.rounded_rectangle([x - int(18 * scale), y - int(6 * scale), x - int(18 * scale) + kw, y - int(6 * scale) + kh], radius=int(3 * scale), fill=c_fill)

    # Parmaklar ve Avuç
    body = [
        (x - int(7 * scale), y + int(18 * scale)),
        (x + int(15 * scale), y + int(18 * scale)),
        (x + int(18 * scale), y + int(15 * scale)),
        (x + int(18 * scale), y + int(2 * scale)),
        (x + int(12 * scale), y + int(2 * scale)),
        (x + int(10 * scale), y - int(14 * scale)),
        (x + int(2 * scale), y - int(14 * scale)),
        (x - int(2 * scale), y - int(2 * scale)),
        (x - int(7 * scale), y - int(2 * scale)),
    ]
    draw.polygon(body, fill=c_fill, outline=c_outline)


def draw_bell(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, is_active: bool = False, wobble_angle: float = 0.0):
    """Modern Bildirim Çanı ikonunu çizer (titreme ve çalma açısı destekli)."""
    c_fill = (255, 215, 0, 255) if is_active else (255, 255, 255, 240)

    # Üst halka
    draw.ellipse([x - int(3 * scale), y - int(18 * scale), x + int(3 * scale), y - int(12 * scale)], outline=c_fill, width=int(2 * scale))

    # Çan gövdesi
    sin_a = math.sin(math.radians(wobble_angle))
    cos_a = math.cos(math.radians(wobble_angle))

    def rot(dx, dy):
        return x + int((dx * cos_a - dy * sin_a) * scale), y + int((dx * sin_a + dy * cos_a) * scale)

    pts = [
        rot(0, -12),
        rot(6, -6),
        rot(11, 4),
        rot(15, 10),
        rot(-15, 10),
        rot(-11, 4),
        rot(-6, -6),
    ]
    draw.polygon(pts, fill=c_fill)

    # Alt tokmak
    draw.ellipse([x - int(4 * scale), y + int(10 * scale), x + int(4 * scale), y + int(15 * scale)], fill=c_fill)

    # Eğer aktifse iki yanda titreşim yayları
    if is_active:
        arc_c = (255, 215, 0, 200)
        draw.arc([x - int(26 * scale), y - int(12 * scale), x - int(16 * scale), y + int(10 * scale)], start=120, end=240, fill=arc_c, width=int(2 * scale))
        draw.arc([x + int(16 * scale), y - int(12 * scale), x + int(26 * scale), y + int(10 * scale)], start=300, end=60, fill=arc_c, width=int(2 * scale))


def draw_pointer_hand(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, is_clicking: bool = False):
    """Zarif beyaz imleç / tıklayan el ikonunu çizer."""
    p_scale = scale * (0.88 if is_clicking else 1.0)
    c_fill = (255, 255, 255, 255)
    c_border = (20, 20, 20, 220)

    hand = [
        (x, y),
        (x + int(8 * p_scale), y + int(20 * p_scale)),
        (x + int(3 * p_scale), y + int(20 * p_scale)),
        (x + int(6 * p_scale), y + int(30 * p_scale)),
        (x + int(1 * p_scale), y + int(32 * p_scale)),
        (x - int(2 * p_scale), y + int(22 * p_scale)),
        (x - int(6 * p_scale), y + int(25 * p_scale)),
    ]
    draw.polygon(hand, fill=c_fill, outline=c_border)


def render_cta_frame(
    t: float,
    total_dur: float,
    language: str = "en",
    w: int = 1080,
    h: int = 1920
) -> Image.Image:
    """
    Belirli bir t anı (0.0s - 4.5s) için transparan RGBA animasyon karesi üretir.
    """
    frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    # 1. Giriş ve Çıkış Animasyonu (Fade & Slide)
    alpha_mul = 1.0
    slide_y = 0.0

    if t < 0.4:
        # 0.0s - 0.4s: Yumuşak giriş (ease-out)
        progress = t / 0.4
        alpha_mul = math.sin(progress * (math.pi / 2))
        slide_y = (1.0 - alpha_mul) * 50.0
    elif t > (total_dur - 0.4):
        # 4.1s - 4.5s: Yumuşak çıkış (ease-in)
        progress = (total_dur - t) / 0.4
        alpha_mul = math.sin(max(0.0, progress) * (math.pi / 2))
        slide_y = (1.0 - alpha_mul) * 30.0

    if alpha_mul <= 0.01:
        return frame

    # Konumlandırma: Alt güvenli bölge (Shorts altyazı ve UI'nın hemen üstünde)
    is_shorts = h > w
    
    # Eleman genişlikleri
    badge_w = 48
    badge_h = 38
    btn_w = 210
    btn_h = 46
    sep_pad = 16
    like_w = 42
    bell_w = 42
    pad_x = 20
    
    # Toplam içerik genişliğine göre kapsül boyutlandır
    cw = pad_x * 2 + badge_w + 12 + btn_w + sep_pad * 2 + like_w + sep_pad * 2 + bell_w
    ch = 82
    cx = w // 2
    # Altyazı (y ≈ 1550) üstünde, oyuncunun yüz/göğüs bölgesinden uzakta alt çeyrek güvenli bölge (y ≈ 0.80 * h)
    cy = int(h * 0.80) + int(slide_y) if is_shorts else int(h * 0.82) + int(slide_y)

    x0 = cx - cw // 2
    y0 = cy - ch // 2
    x1 = cx + cw // 2
    y1 = cy + ch // 2

    # Kapsül Arka Planı (Cam / Glassmorphism efekti)
    bg_alpha = int(240 * alpha_mul)
    border_alpha = int(80 * alpha_mul)
    shadow_alpha = int(140 * alpha_mul)

    # Yumuşak gölge
    draw.rounded_rectangle([x0 + 2, y0 + 5, x1 + 2, y1 + 5], radius=28, fill=(0, 0, 0, shadow_alpha))
    # Ana kapsül
    draw.rounded_rectangle([x0, y0, x1, y1], radius=26, fill=(18, 18, 24, bg_alpha), outline=(255, 255, 255, border_alpha), width=2)

    # İç Öğelerin Durum Mantığı:
    # 0.0s - 1.2s: Başlangıç durumu
    # 1.2s: Abone Ol tıklandı
    # 2.3s: Beğen tıklandı
    # 3.3s: Zil tıklandı
    is_subscribed = t >= 1.25
    is_liked = t >= 2.35
    is_bell_active = t >= 3.35

    lang_dict = LOCALIZED_CTA.get(language, LOCALIZED_CTA["en"])
    sub_text = lang_dict["subscribed"] if is_subscribed else lang_dict["subscribe"]

    font = get_cta_font(18)

    # A) Sol: Kırmızı YouTube Logo Rozeti
    cur_x = x0 + pad_x
    badge_x0 = cur_x
    badge_y0 = cy - badge_h // 2
    draw.rounded_rectangle([badge_x0, badge_y0, badge_x0 + badge_w, badge_y0 + badge_h], radius=12, fill=(235, 32, 38, int(255 * alpha_mul)))
    # Beyaz Play Üçgeni
    tri = [(badge_x0 + 20, badge_y0 + 13), (badge_x0 + 20, badge_y0 + 31), (badge_x0 + 36, badge_y0 + 22)]
    draw.polygon(tri, fill=(255, 255, 255, int(255 * alpha_mul)))

    cur_x += badge_w + 14

    # B) Abone Ol Butonu
    btn_x0 = cur_x
    btn_y0 = cy - btn_h // 2
    btn_x1 = btn_x0 + btn_w
    btn_y1 = btn_y0 + btn_h

    # Tıklama anında buton hafif küçülür (press feedback)
    btn_scale = 0.94 if 1.2 <= t <= 1.4 else 1.0

    if is_subscribed:
        btn_color = (39, 39, 44, int(240 * alpha_mul))
        btn_border = (80, 80, 88, int(180 * alpha_mul))
        text_color = (240, 240, 240, int(255 * alpha_mul))
    else:
        btn_color = (235, 32, 38, int(255 * alpha_mul))
        btn_border = (255, 80, 80, int(150 * alpha_mul))
        text_color = (255, 255, 255, int(255 * alpha_mul))

    # Ölçekli buton çizimi
    bx_mid = (btn_x0 + btn_x1) // 2
    by_mid = (btn_y0 + btn_y1) // 2
    cur_bw = int(btn_w * btn_scale)
    cur_bh = int(btn_h * btn_scale)
    b_rect = [bx_mid - cur_bw // 2, by_mid - cur_bh // 2, bx_mid + cur_bw // 2, by_mid + cur_bh // 2]
    draw.rounded_rectangle(b_rect, radius=22, fill=btn_color, outline=btn_border, width=1)

    # Buton Metni & Checkmark hizalama
    bbox = font.getbbox(sub_text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    if is_subscribed:
        tot_w = 20 + 8 + tw
        start_x = bx_mid - tot_w // 2
        # Onay işareti ✓
        draw.line([start_x, by_mid, start_x + 6, by_mid + 7], fill=text_color, width=3)
        draw.line([start_x + 6, by_mid + 7, start_x + 16, by_mid - 6], fill=text_color, width=3)
        draw.text((start_x + 24, by_mid - th // 2 - 2), sub_text, font=font, fill=text_color)
    else:
        draw.text((bx_mid - tw // 2, by_mid - th // 2 - 2), sub_text, font=font, fill=text_color)

    cur_x += btn_w + sep_pad

    # C) Dikey İnce Ayırıcı Çizgi 1
    draw.line([cur_x, cy - 18, cur_x, cy + 18], fill=(255, 255, 255, int(45 * alpha_mul)), width=1)
    cur_x += sep_pad

    # D) Beğen (Like) Butonu
    like_cx = cur_x + like_w // 2
    like_cy = cy
    like_scale = 1.45 if 2.3 <= t <= 2.5 else 1.2
    draw_thumbs_up(draw, like_cx, like_cy, scale=like_scale, is_liked=is_liked)

    # Like Parıltıları (Sparkles)
    if 2.35 <= t <= 2.8:
        sp_prog = (t - 2.35) / 0.45
        sp_r = int(14 + sp_prog * 18)
        sp_a = int((1.0 - sp_prog) * 220 * alpha_mul)
        for ang in [30, 120, 210, 300]:
            sx = like_cx + int(sp_r * math.cos(math.radians(ang)))
            sy = like_cy + int(sp_r * math.sin(math.radians(ang)))
            draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(62, 166, 255, sp_a))

    cur_x += like_w + sep_pad

    # E) Dikey İnce Ayırıcı 2
    draw.line([cur_x, cy - 18, cur_x, cy + 18], fill=(255, 255, 255, int(45 * alpha_mul)), width=1)
    cur_x += sep_pad

    # F) Bildirim Çanı (Bell) Butonu
    bell_cx = cur_x + bell_w // 2
    bell_cy = cy
    wobble = 0.0
    if 3.35 <= t <= 4.0:
        elapsed = t - 3.35
        # Titreme sönümleme formülü
        wobble = 22.0 * math.sin(elapsed * 18.0) * math.exp(-elapsed * 3.5)

    draw_bell(draw, bell_cx, bell_cy, scale=1.2, is_active=is_bell_active, wobble_angle=wobble)

    # G) Tıklama Dalgaları (Click Ripples)
    # 1. Abone ol dalgası
    if 1.25 <= t <= 1.65:
        r_prog = (t - 1.25) / 0.4
        rip_rad = int(r_prog * 45)
        rip_alpha = int((1.0 - r_prog) * 160 * alpha_mul)
        draw.ellipse([bx_mid - rip_rad, by_mid - rip_rad, bx_mid + rip_rad, by_mid + rip_rad], outline=(255, 255, 255, rip_alpha), width=2)

    # 2. Like dalgası
    if 2.35 <= t <= 2.75:
        r_prog = (t - 2.35) / 0.4
        rip_rad = int(r_prog * 36)
        rip_alpha = int((1.0 - r_prog) * 180 * alpha_mul)
        draw.ellipse([like_cx - rip_rad, like_cy - rip_rad, like_cx + rip_rad, like_cy + rip_rad], outline=(62, 166, 255, rip_alpha), width=2)

    # 3. Bell dalgası
    if 3.35 <= t <= 3.75:
        r_prog = (t - 3.35) / 0.4
        rip_rad = int(r_prog * 36)
        rip_alpha = int((1.0 - r_prog) * 180 * alpha_mul)
        draw.ellipse([bell_cx - rip_rad, bell_cy - rip_rad, bell_cx + rip_rad, bell_cy + rip_rad], outline=(255, 215, 0, rip_alpha), width=2)

    # H) İmleç (Pointer Hand) Hareketi: Avant-garde temiz vektör tasarımı gereği sahte fare imleci kaldırıldı.
    # Buton animasyonları (Abone Ol renk geçişi, like ve çan parıltıları) doğal mikroyapıyla çalışır.
    return frame


def generate_transparent_cta_clip(
    output_path: Path,
    language: str = "en",
    w: int = 1080,
    h: int = 1920,
    fps: int = 30,
    duration: float = 4.5
) -> bool:
    """
    Belirtilen dil ve çözünürlükte transparan alpha-kanallı (ProRes 4444 / VP9) video üretir.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_frames = int(duration * fps)
    print(f"[SOCIAL-CTA] 🎬 Transparan CTA animasyonu üretiliyor: {language} ({w}x{h}, {total_frames} kare)...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Kareleri RGBA PNG olarak çiz
        for i in range(total_frames):
            t = i / float(fps)
            img = render_cta_frame(t, duration, language, w, h)
            frame_file = tmp_path / f"frame_{i:04d}.png"
            img.save(frame_file, format="PNG")

        # 2. FFmpeg ile ProRes 4444 veya VP9 WebM alpha kanallı video oluştur
        # ProRes 4444 yuva444p10le hem macOS hem Linux FFmpeg tarafından donanım seviyesinde desteklenir.
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(tmp_path / "frame_%04d.png"),
            "-c:v", "prores_ks",
            "-profile:v", "4444",
            "-pix_fmt", "yuva444p10le",
            str(output_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and output_path.exists():
            print(f"[SOCIAL-CTA] ✅ Transparan CTA klibi başarıyla oluşturuldu: {output_path.name}")
            return True

        # Fallback: VP9 WebM yuva420p
        cmd_webm = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(tmp_path / "frame_%04d.png"),
            "-c:v", "libvpx-vp9",
            "-pix_fmt", "yuva420p",
            str(output_path.with_suffix(".webm"))
        ]
        res_webm = subprocess.run(cmd_webm, capture_output=True, text=True)
        if res_webm.returncode == 0 and output_path.with_suffix(".webm").exists():
            print(f"[SOCIAL-CTA] ✅ Transparan WebM CTA klibi oluşturuldu: {output_path.with_suffix('.webm').name}")
            return True

    print(f"[SOCIAL-CTA] ❌ CTA klibi oluşturulamadı: {res.stderr}")
    return False


def get_cached_cta_clip(
    language: str = "en",
    w: int = 1080,
    h: int = 1920,
    cache_dir: Optional[Path] = None
) -> Optional[Path]:
    """
    Daha önce oluşturulmuş CTA klibini döner, yoksa oluşturup önbelleğe alır.
    """
    if cache_dir is None:
        cache_dir = Path("/Users/alienes/yt-oto-video/files/assets/cta_cache")
        # Eğer sunucudaysak sunucu dizini
        if not cache_dir.parent.exists():
            cache_dir = Path("/home/ubuntu/yt-remote-worker/assets/cta_cache")

    cache_dir.mkdir(parents=True, exist_ok=True)
    clean_lang = language.lower() if language else "en"
    if clean_lang not in LOCALIZED_CTA:
        clean_lang = "en"

    cand_mov = cache_dir / f"cta_{clean_lang}_{w}x{h}.mov"
    cand_webm = cache_dir / f"cta_{clean_lang}_{w}x{h}.webm"

    if cand_mov.exists() and cand_mov.stat().st_size > 1000:
        return cand_mov
    if cand_webm.exists() and cand_webm.stat().st_size > 1000:
        return cand_webm

    # Yoksa oluştur
    if generate_transparent_cta_clip(cand_mov, language=clean_lang, w=w, h=h):
        return cand_mov
    if cand_webm.exists():
        return cand_webm

    return None


def get_video_info(video_path: Path) -> Tuple[float, int, int]:
    """Video süresi, genişliği ve yüksekliğini döner."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=width,height",
        "-of", "default=noprint_wrappers=1", str(video_path)
    ]
    try:
        out = subprocess.check_output(cmd, text=True)
        dur = 0.0
        w = 1080
        h = 1920
        for line in out.splitlines():
            if line.startswith("duration="):
                dur = float(line.split("=")[1])
            elif line.startswith("width="):
                w = int(line.split("=")[1])
            elif line.startswith("height="):
                h = int(line.split("=")[1])
        return dur, w, h
    except Exception as e:
        print(f"[SOCIAL-CTA] ffprobe okuma hatası: {e}")
        return 45.0, 1080, 1920


def apply_social_cta_overlay(
    input_video: Union[str, Path],
    output_video: Union[str, Path],
    language: str = "en",
    show_at_start: bool = False,
    show_at_end: bool = True,
    start_time: Optional[float] = None,
    display_duration: Optional[float] = None
) -> bool:
    """
    Herhangi bir videoya kanalın dilinde hareketli transparan "Abone Ol + Beğen + Bildirim"
    CTA katmanını giydirir.
    
    KURALLAR:
    1. Video süresi asla değişmez (uzamaz / kısalmaz).
    2. Orijinal ses parçası ve senkron %100 korunur (-c:a copy).
    3. Başta 3.0s - 7.5s (Hook sonrası) ve/veya Sonda (Videonun bitimine 5.5 sn kala)
       pürüzsüzce belirip kaybolur.
    """
    in_p = Path(input_video)
    out_p = Path(output_video)
    if not in_p.exists():
        print(f"[SOCIAL-CTA] Hata: Kaynak video mevcut değil: {in_p}")
        return False

    dur, w, h = get_video_info(in_p)
    if dur <= 6.0:
        print(f"[SOCIAL-CTA] Video çok kısa ({dur:.1f}s), CTA atlanıyor.")
        if in_p != out_p:
            shutil.copy2(str(in_p), str(out_p))
        return True

    cta_clip = get_cached_cta_clip(language, w, h)
    if not cta_clip or not cta_clip.exists():
        print("[SOCIAL-CTA] ⚠️ CTA katman klibi hazır değil, orijinal video korunuyor.")
        if in_p != out_p:
            shutil.copy2(str(in_p), str(out_p))
        return False

    # Overlay zamanlama formülü:
    # Sonda (Videonun bitimine ~6.2 sn kala girer veya belirlenen start_time anında başlar)
    # Kapanıştaki tartışma/yorum sorusunun ve başlıkların üzerine binmez.
    tmp_out = out_p if in_p != out_p else out_p.parent / f"_cta_tmp_{out_p.name}"

    if show_at_end and not show_at_start:
        if start_time is not None:
            end_start = max(1.0, float(start_time))
            dur_val = float(display_duration or 2.0)
            end_stop = min(dur, end_start + dur_val)
        else:
            end_start = max(6.0, dur - 6.2)
            dur_val = float(display_duration or 1.8)
            end_stop = min(dur, end_start + dur_val)
        filter_complex = f"[1:v]setpts=PTS-STARTPTS+{end_start:.3f}/TB[ctav];[0:v][ctav]overlay=x=0:y=0:enable='between(t,{end_start:.3f},{end_stop:.3f})':eof_action=pass[outv]"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(in_p),
            "-i", str(cta_clip),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-t", f"{dur:.3f}",
            str(tmp_out)
        ]
        enable_expr = f"gte(t,{end_start:.2f}) [one-shot]"
    else:
        windows = []
        if show_at_start and dur >= 10.0:
            windows.append("between(t,3.0,7.5)")
        if show_at_end and dur >= 15.0:
            end_start = max(8.0, dur - 5.5)
            end_finish = dur - 1.0
            windows.append(f"between(t,{end_start:.2f},{end_finish:.2f})")
        if not windows:
            windows.append("between(t,2.0,6.5)")
        enable_expr = "+".join(windows)
        filter_complex = f"[0:v][1:v]overlay=x=0:y=0:enable='{enable_expr}':eof_action=pass[outv]"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(in_p),
            "-stream_loop", "-1", "-i", str(cta_clip),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-t", f"{dur:.3f}",
            str(tmp_out)
        ]

    print(f"[SOCIAL-CTA] 🚀 Video üzerine CTA katmanı giydiriliyor ({enable_expr})...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and tmp_out.exists():
        if tmp_out != out_p:
            shutil.move(str(tmp_out), str(out_p))
        print(f"[SOCIAL-CTA] ✨ CTA katmanı başarıyla giydirildi: {out_p.name}")
        return True
    else:
        print(f"[SOCIAL-CTA] ❌ FFmpeg overlay hatası: {res.stderr[-500:]}")
        if tmp_out.exists() and tmp_out != out_p:
            tmp_out.unlink()
        return False
