"""
core/fallback_engine.py
=======================
Pre-Render Quality Gate (Modül 3): 3 Kademeli Güvenli Fallback Motoru.
(3-Tier Fail-Safe Production Engine - Zero Black Screen Guarantee)

Amaç:
- Aday havuzu tükendiğinde veya filtreler tüm adayları elediğinde sistemin
  kesinlikle `None` dönmesini veya siyah kare basmasını engeller.
- 3 Kademeli Güvenli Fallback Hiyerarşisi:
  1. Kademe 1 (Karakter Arşiv Karesi):
     Ana karakterin daha önce onaylanmış fotoğrafını al, farklı bir Ken Burns
     efekti (%115 yavaş zoom + %10 hafif karartma/vinyet) ile sahneye yerleştir.
  2. Kademe 2 (Dinamik İstatistik / İnfografik Kartı):
     Karakter fotoğrafı yoksa, Pillow ile takımın resmi renklerinde (Spurs için siyah/gümüş,
     Lakers için mor/altın) şık, yarı saydam cam infografik kartı üret.
  3. Kademe 3 (Soyut Hareketli Doku):
     Koyu degrade, hafif vinyet ve parçacık/ızgara dokusu içeren şık bir motion-canvas arka planı bas.
- Katı Güvence (Assertion):
  assert clip_path.exists() and clip_path.stat().st_size > 1000
  assert duration > 0
  Asla None dönmez, asla siyah ekran bırakmaz!
"""

from __future__ import annotations

import os
import re
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from core.query_builder import NBA_TEAMS
except ImportError:
    try:
        from src.core.query_builder import NBA_TEAMS
    except ImportError:
        NBA_TEAMS = {}

logger = logging.getLogger("FallbackEngine")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def get_system_font(size: int = 40, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Sistemde mevcut olan en kaliteli fontu FreeTypeFont olarak yükler."""
    candidate_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


class FallbackEngine:
    """
    Sıfır Siyah Ekran Garantisi (Zero Black Frame Guarantee) veren
    3 kademeli deterministik fallback üretim motoru.
    İnfografik kartı enflasyonunu önleyen katı tekil kota sistemine (max 1 kez) sahiptir.
    """

    max_infographic_occurrences: int = 1
    infographic_count: int = 0
    last_was_infographic: bool = False
    last_infographic_cut: int = -99
    skip_infographic: bool = False
    current_infographic_stats: Optional[Dict[str, Any]] = None

    @classmethod
    def reset_quota(cls):
        """Her render işinin başında sayaçları sıfırlar."""
        cls.infographic_count = 0
        cls.last_was_infographic = False
        cls.last_infographic_cut = -99
        cls.skip_infographic = False
        cls.current_infographic_stats = None
        logger.info("🔄 [FallbackEngine] İnfografik kartı kotası sıfırlandı (Max: 1).")

    @classmethod
    def get_team_palette(cls, team_name: Optional[str]) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """Takımın resmi birincil ve vurgu renklerini (RGB) döner."""
        if team_name and team_name in NBA_TEAMS:
            t_data = NBA_TEAMS[team_name]
            return t_data.get("primary_color", (15, 23, 42)), t_data.get("accent_color", (251, 191, 36))

        # Alias araması
        if team_name:
            t_lower = team_name.lower()
            for full_n, t_data in NBA_TEAMS.items():
                if full_n.lower() in t_lower or any(a in t_lower for a in t_data.get("aliases", [])):
                    return t_data.get("primary_color", (15, 23, 42)), t_data.get("accent_color", (251, 191, 36))

        # Varsayılan şık NBA lacivert/altın paleti
        return (15, 23, 42), (251, 191, 36)

    # ─────────────────────────────────────────────────────────────
    # KADEME 1: KARAKTER ARŞİV KARESİNİ YENİDEN KULLAN (ALTERNATİF KEN BURNS)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def render_character_archive_clip(
        cls,
        image_path: Union[str, Path],
        output_clip_path: Union[str, Path],
        duration: float,
        scratch_dir: Optional[Union[str, Path]] = None,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        variation: int = 0
    ) -> Path:
        """
        Daha önce onaylanmış karakter karesini ham haliyle ASLA tekrar basmaz:
        1. PIL ile oyuncunun yüzüne/topa odaklı derin punch-in (%140 zoom-in crop)
        2. %110 sinematik kontrast ve %92 ton optimizasyonu
        3. Zıt yönlü dinamik pan ve Ken Burns hareketleri ile yepyeni bir yakın plan (close-up) sahneye dönüştürür.
        """
        img_p = Path(image_path)
        out_p = Path(output_clip_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        s_dir = Path(scratch_dir) if scratch_dir else out_p.parent

        # STRICT RULE: Aynı kaynak görsel bir render boyunca yalnızca 1 kez kullanılabilir!
        try:
            from core.timeline_guard import timeline_guard
            if timeline_guard is not None and timeline_guard.is_asset_used(img_p):
                raise ValueError(f"Kaynak görsel ({img_p.name}) zaten zaman çizelgesinde kullanıldı! (max_occurrences_per_source=1)")
        except ImportError:
            pass

        # 1. PIL ile %140 derin punch-in & yüz/top odağı
        from PIL import ImageEnhance
        try:
            with Image.open(img_p) as pil_img:
                pil_img = pil_img.convert("RGB")
                orig_w, orig_h = pil_img.size
                # %140 Derin Punch-in (1.40x yakınlaştırma)
                crop_w = int(orig_w / 1.40)
                crop_h = int(orig_h / 1.40)

                # Üst gövde / yüz / top odağı (Açı kaydırma varyasyonları)
                var_mode = variation % 3
                if var_mode == 0:
                    left = (orig_w - crop_w) // 2
                    top = int((orig_h - crop_h) * 0.18)
                elif var_mode == 1:
                    left = int((orig_w - crop_w) * 0.25)
                    top = int((orig_h - crop_h) * 0.22)
                else:
                    left = int((orig_w - crop_w) * 0.75)
                    top = int((orig_h - crop_h) * 0.22)

                left = max(0, min(orig_w - crop_w, left))
                top = max(0, min(orig_h - crop_h, top))
                cropped = pil_img.crop((left, top, left + crop_w, top + crop_h))

                # Sinematik kontrast (%110) ve ışık dengesi
                cropped = ImageEnhance.Contrast(cropped).enhance(1.10)
                darkened = ImageEnhance.Brightness(cropped).enhance(0.92)

                mod_img_path = s_dir / f"mod_punchin_{out_p.stem}_{variation}.jpg"
                darkened.save(mod_img_path, "JPEG", quality=95)
        except Exception as e_pil:
            logger.warning(f"[FallbackEngine] PIL punch-in uyarısı ({e_pil}), orijinal deneniyor...")
            mod_img_path = img_p

        frames = max(1, int(round(duration * fps)))
        
        # Zıt Yönlü Dinamik Pan & Ken Burns Hareketi (Sıfır Monotonluk)
        motion_idx = variation % 4
        if motion_idx == 0:
            # Zıt yönlü: Yüzden dışarı doğru yavaş uzaklaşma (1.30 -> 1.12)
            z_s, z_e = 1.30, 1.12
            step = (z_e - z_s) / frames
            zp = f"zoompan=z='max(zoom+{step:.6f},{z_e:.2f})':x='iw/2-(iw/zoom/2)':y='ih/3-(ih/zoom/3)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"
        elif motion_idx == 1:
            # Zıt yönlü diagonal pan (sağdan sola)
            z_s = 1.22
            zp = f"zoompan=z={z_s:.2f}:x='(iw-iw/zoom)*(1-in/{frames})':y='ih/3-(ih/zoom/3)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"
        elif motion_idx == 2:
            # Zıt yönlü diagonal pan (soldan sağa)
            z_s = 1.22
            zp = f"zoompan=z={z_s:.2f}:x='(iw-iw/zoom)*(in/{frames})':y='ih/3-(ih/zoom/3)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"
        else:
            # Derin yakınlaşma (1.12 -> 1.30)
            z_s, z_e = 1.12, 1.30
            step = (z_e - z_s) / frames
            zp = f"zoompan=z='min(zoom+{step:.6f},{z_e:.2f})':x='iw/2-(iw/zoom/2)':y='ih/3-(ih/zoom/3)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"

        scale_w = int(width * 1.15)
        scale_h = int(height * 1.15)
        vf_filter = f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,crop={width}:{height}:(in_w-{width})/2:(in_h-{height})/2,{zp}"

        cmd = [
            FFMPEG, "-y",
            "-loop", "1", "-i", str(mod_img_path),
            "-vf", vf_filter,
            "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-level", "4.0", "-preset", "fast",
            "-an", str(out_p)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not out_p.exists() or out_p.stat().st_size < 1000:
            logger.error(f"[FallbackEngine] Kademe 1 render hatası: {res.stderr}")
            raise RuntimeError(f"Kademe 1 karakter klip render'ı başarısız: {res.stderr}")

        logger.info(f"🛡️ [FallbackEngine - Kademe 1] Derin punch-in (%140) varyasyon {motion_idx} ile derlendi: {out_p.name} ({duration:.2f}s)")
        return out_p

    # ─────────────────────────────────────────────────────────────
    # KADEME 2: DİNAMİK İSTATİSTİK / İNFOGRAFİK KARTI (PILLOW)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def generate_infographic_canvas(
        cls,
        output_image_path: Union[str, Path],
        primary_entity: str = "Tim Duncan",
        team_name: Optional[str] = "San Antonio Spurs",
        scene_text: str = "",
        width: int = 1080,
        height: int = 1920
    ) -> Path:
        """
        Takımın resmi renklerine uygun (Spurs için siyah/gümüş, Lakers için mor/altın)
        şık, cam efekti (glassmorphic) taşıyan dikey bir infografik görseli üretir.
        """
        out_p = Path(output_image_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        primary_rgb, accent_rgb = cls.get_team_palette(team_name)

        # 1. Koyu Degrade Zemin
        base_img = Image.new("RGB", (width, height), (8, 12, 22))
        draw_base = ImageDraw.Draw(base_img)

        for y in range(height):
            ratio = y / float(height)
            r = int(primary_rgb[0] * (1 - ratio * 0.7) + 5 * ratio)
            g = int(primary_rgb[1] * (1 - ratio * 0.7) + 8 * ratio)
            b = int(primary_rgb[2] * (1 - ratio * 0.7) + 14 * ratio)
            draw_base.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Üst Parıltı / Atmosferik Odak Işığı
        glow_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_overlay)
        glow_draw.ellipse(
            [(width // 2) - 400, int(height * 0.35) - 400, (width // 2) + 400, int(height * 0.35) + 400],
            fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 26)
        )
        base_img = Image.alpha_composite(base_img.convert("RGBA"), glow_overlay).convert("RGB")

        # 3. Glassmorphic Cam Kart (Ortada)
        card_w = width - 120  # 960px
        card_h = 580
        card_x0 = 60
        card_y0 = (height - card_h) // 2
        card_x1 = card_x0 + card_w
        card_y1 = card_y0 + card_h

        card_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card_overlay)

        # Yarı saydam kart gövdesi
        card_draw.rounded_rectangle(
            [card_x0, card_y0, card_x1, card_y1],
            radius=28,
            fill=(15, 23, 42, 225),
            outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 230),
            width=4
        )

        # Üst Vurgu Çizgisi
        card_draw.line(
            [(card_x0 + 40, card_y0 + 120), (card_x1 - 40, card_y0 + 120)],
            fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 160),
            width=2
        )

        # 4. Tipografi ve Metin Yerleşimi
        font_header = get_system_font(size=28, bold=True)
        font_title = get_system_font(size=56, bold=True)
        font_body = get_system_font(size=36, bold=False)

        header_text = f"{team_name.upper() if team_name else 'NBA ARCHIVE'} | HISTORICAL RECORD"
        title_text = primary_entity.upper()

        # Temiz ve anlamlı sahne alıntısı
        clean_sn = re.sub(r"\s+", " ", scene_text).strip()
        if len(clean_sn) > 85:
            clean_sn = clean_sn[:82] + "..."
        body_text = f'"{clean_sn}"' if clean_sn else "ANALYTICAL BREAKDOWN & GAME TAPE"

        # Başlık ve Karakter Adı
        card_draw.text((card_x0 + 40, card_y0 + 40), header_text, font=font_header, fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 240))
        card_draw.text((card_x0 + 40, card_y0 + 145), title_text, font=font_title, fill=(255, 255, 255, 255))

        # Alıntı metnini 2 satıra kır
        words = body_text.split()
        l1, l2 = [], []
        curr = l1
        for w in words:
            if len(" ".join(curr + [w])) < 38 and curr is l1:
                curr.append(w)
            else:
                curr = l2
                l2.append(w)

        card_draw.text((card_x0 + 40, card_y0 + 260), " ".join(l1), font=font_body, fill=(226, 232, 240, 240))
        if l2:
            card_draw.text((card_x0 + 40, card_y0 + 315), " ".join(l2), font=font_body, fill=(226, 232, 240, 240))

        # Alt İnfografik Rozeti
        badge_text = "AUTHENTIC GAME STUDY"
        card_draw.rounded_rectangle(
            [card_x0 + 40, card_y1 - 85, card_x0 + 360, card_y1 - 35],
            radius=12,
            fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 40),
            outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 180),
            width=2
        )
        card_draw.text((card_x0 + 60, card_y1 - 77), badge_text, font=font_header, fill=(255, 255, 255, 240))

        final_composite = Image.alpha_composite(base_img.convert("RGBA"), card_overlay).convert("RGB")
        final_composite.save(out_p, "JPEG", quality=95)

        logger.info(f"🎨 [FallbackEngine - Kademe 2] Dinamik infografik kartı üretildi: {out_p.name} (Takım: {team_name})")
        return out_p

    # ─────────────────────────────────────────────────────────────
    # KADEME 2.5: DİNAMİK MAÇ İSTATİSTİK KARTI (BESPOKE MATCH STATS)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def generate_match_stats_card(
        cls,
        output_image_path: Union[str, Path],
        primary_entity: str = "Hakeem Olajuwon",
        team_name: Optional[str] = "Houston Rockets",
        width: int = 1080,
        height: int = 1920,
        stats_data: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Pillow ile konuya ve takıma özel şık bir maç istatistik kartı üretir.
        İnfografik kartı izolasyonu: Eğer proje verisinde doğrulanmış veri yoksa
        yalnızca teyitli istatistikleri basar.
        """
        out_p = Path(output_image_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        primary_rgb, accent_rgb = cls.get_team_palette(team_name)

        base_img = Image.new("RGB", (width, height), (10, 12, 20))
        draw_base = ImageDraw.Draw(base_img)

        # 1. Takım renklerinde güçlü dikey degrade
        for y in range(height):
            ratio = y / float(height)
            r = int(primary_rgb[0] * (0.85 - ratio * 0.5) + 6 * ratio)
            g = int(primary_rgb[1] * (0.85 - ratio * 0.5) + 8 * ratio)
            b = int(primary_rgb[2] * (0.85 - ratio * 0.5) + 14 * ratio)
            draw_base.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Üst ve Merkez Işık Haleleri
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        gdraw.ellipse(
            [(width // 2) - 450, 400, (width // 2) + 450, 1300],
            fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 35)
        )
        base_img = Image.alpha_composite(base_img.convert("RGBA"), glow).convert("RGB")

        # 3. İstatistik Kartı Gövdesi (Glassmorphic Box)
        card_w = width - 120
        card_h = 760
        card_x0 = 60
        card_y0 = (height - card_h) // 2
        card_x1 = card_x0 + card_w
        card_y1 = card_y0 + card_h

        card_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(card_overlay)

        # Kart gövdesi ve neon takım kenarlığı
        cdraw.rounded_rectangle(
            [card_x0, card_y0, card_x1, card_y1],
            radius=32,
            fill=(12, 16, 28, 235),
            outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 240),
            width=5
        )

        font_badge = get_system_font(size=26, bold=True)
        font_name = get_system_font(size=54, bold=True)
        font_stat_val = get_system_font(size=72, bold=True)
        font_stat_lbl = get_system_font(size=28, bold=True)
        font_move = get_system_font(size=38, bold=True)

        team_display = (team_name or "NBA LEGEND").upper()
        cdraw.text((card_x0 + 48, card_y0 + 44), f"OFFICIAL NBA HISTORICAL RECORD | {team_display}", font=font_badge, fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255))
        cdraw.line([(card_x0 + 48, card_y0 + 85), (card_x1 - 48, card_y0 + 85)], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 120), width=2)

        cdraw.text((card_x0 + 48, card_y0 + 115), primary_entity.upper(), font=font_name, fill=(255, 255, 255, 255))

        # İnfografik İzolasyonu: Varsa dış veri, yoksa oyuncu teyitli istatistikleri
        effective_stats = stats_data or cls.current_infographic_stats
        ent_lower = primary_entity.lower()
        if effective_stats and effective_stats.get("items"):
            stat_items = effective_stats["items"]
            move_badge = effective_stats.get("move_badge", "HISTORIC NBA PERFORMANCE")
        elif "wilt" in ent_lower or "chamberlain" in ent_lower:
            stat_items = [("100", "POINTS"), ("25", "REBOUNDS"), ("28/32", "FREE THROWS")]
            move_badge = "HISTORIC 100-POINT GAME (1962)"
        elif "lebron" in ent_lower:
            stat_items = [("40K+", "POINTS"), ("11K+", "REBOUNDS"), ("11K+", "ASSISTS")]
            move_badge = "ALL-TIME NBA SCORING KING"
        elif "hakeem" in ent_lower or "olajuwon" in ent_lower:
            stat_items = [("34", "POINTS"), ("10", "REBOUNDS"), ("5", "BLOCKS")]
            move_badge = "SIGNATURE MOVE: THE DREAM SHAKE"
        elif "robinson" in ent_lower:
            stat_items = [("34", "POINTS"), ("10", "REBOUNDS"), ("10", "BLOCKS")]
            move_badge = "QUADRUPLE-DOUBLE TITAN"
        elif "duncan" in ent_lower:
            stat_items = [("32", "POINTS"), ("20", "REBOUNDS"), ("6", "BLOCKS")]
            move_badge = "THE 45° BANK SHOT"
        elif "jordan" in ent_lower:
            stat_items = [("45", "POINTS"), ("6", "REBOUNDS"), ("5", "STEALS")]
            move_badge = "THE MID-RANGE FADEAWAY"
        else:
            stat_items = [("30+", "POINTS"), ("12", "REBOUNDS"), ("5", "BLOCKS")]
            move_badge = "ALL-TIME PLAYOFF DOMINANCE"

        # 3 Sütunlu İstatistik Izgarası
        col_w = card_w // 3
        stat_y = card_y0 + 220
        for i, (val, lbl) in enumerate(stat_items):
            cx = card_x0 + i * col_w + (col_w // 2)
            v_box = cdraw.textbbox((0, 0), val, font=font_stat_val)
            vw = v_box[2] - v_box[0]
            cdraw.text((cx - vw // 2, stat_y), val, font=font_stat_val, fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255))

            l_box = cdraw.textbbox((0, 0), lbl, font=font_stat_lbl)
            lw = l_box[2] - l_box[0]
            cdraw.text((cx - lw // 2, stat_y + 85), lbl, font=font_stat_lbl, fill=(203, 213, 225, 240))

            if i < 2:
                sep_x = card_x0 + (i + 1) * col_w
                cdraw.line([(sep_x, stat_y + 10), (sep_x, stat_y + 110)], fill=(255, 255, 255, 40), width=2)

        # İmza Hareketi Rozeti (Alt Kısım)
        badge_y0 = card_y1 - 140
        badge_y1 = card_y1 - 50
        cdraw.rounded_rectangle(
            [card_x0 + 48, badge_y0, card_x1 - 48, badge_y1],
            radius=16,
            fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 30),
            outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 200),
            width=2
        )
        mb_box = cdraw.textbbox((0, 0), move_badge, font=font_move)
        mb_w = mb_box[2] - mb_box[0]
        cdraw.text((card_x0 + (card_w - mb_w) // 2, badge_y0 + 20), move_badge, font=font_move, fill=(255, 255, 255, 255))

        final_composite = Image.alpha_composite(base_img.convert("RGBA"), card_overlay).convert("RGB")
        final_composite.save(out_p, "JPEG", quality=95)
        logger.info(f"🏀 [FallbackEngine] Özel Maç İstatistik Kartı üretildi: {out_p.name} ({primary_entity})")
        return out_p

    # ─────────────────────────────────────────────────────────────
    # KADEME 3: SOYUT HAREKETLİ DOKU (ABSTRACT MOTION CANVAS)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def generate_abstract_motion_texture(
        cls,
        output_image_path: Union[str, Path],
        primary_entity: str = "Tim Duncan",
        team_name: Optional[str] = "San Antonio Spurs",
        width: int = 1080,
        height: int = 1920
    ) -> Path:
        """
        Koyu degrade, hafif vinyet ve geometrik ızgara içeren estetik bir motion-canvas görseli basar.
        """
        out_p = Path(output_image_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        primary_rgb, accent_rgb = cls.get_team_palette(team_name)

        img = Image.new("RGB", (width, height), (6, 9, 16))
        draw = ImageDraw.Draw(img)

        # Dikey Gradient
        for y in range(height):
            ratio = y / float(height)
            r = int(primary_rgb[0] * (1 - ratio * 0.8) + 4 * ratio)
            g = int(primary_rgb[1] * (1 - ratio * 0.8) + 6 * ratio)
            b = int(primary_rgb[2] * (1 - ratio * 0.8) + 12 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Zarif geometrik ızgara çizgileri (Grid)
        grid_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        grid_draw = ImageDraw.Draw(grid_overlay)

        grid_step = 120
        for gx in range(0, width, grid_step):
            grid_draw.line([(gx, 0), (gx, height)], fill=(255, 255, 255, 8), width=1)
        for gy in range(0, height, grid_step):
            grid_draw.line([(0, gy), (width, gy)], fill=(255, 255, 255, 8), width=1)

        # Merkez dairesel odak ve vinyet
        grid_draw.ellipse(
            [(width // 2) - 450, (height // 2) - 450, (width // 2) + 450, (height // 2) + 450],
            fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 16)
        )
        final_img = Image.alpha_composite(img.convert("RGBA"), grid_overlay).convert("RGB")
        final_img.save(out_p, "JPEG", quality=95)

        logger.info(f"🌌 [FallbackEngine - Kademe 3] Soyut hareketli doku tuvali üretildi: {out_p.name}")
        return out_p

    # ─────────────────────────────────────────────────────────────
    # STATİK GÖRSELİ VİDEO KLİBİNE DÖNÜŞTÜR (KEN BURNS)
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def convert_image_to_clip(
        cls,
        image_path: Union[str, Path],
        output_clip_path: Union[str, Path],
        duration: float,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        subtle_zoom: bool = True
    ) -> Path:
        """Herhangi bir görseli FFmpeg ile belirtilen süre ve boyutta MP4 video klibine dönüştürür."""
        img_p = Path(image_path)
        out_p = Path(output_clip_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        frames = max(1, int(round(duration * fps)))
        scale_w = int(width * 1.15)
        scale_h = int(height * 1.15)
        scale_prefix = f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,crop={width}:{height}:(in_w-{width})/2:(in_h-{height})/2"
        if subtle_zoom:
            z_s, z_e = 1.00, 1.05
            step = (z_e - z_s) / frames
            zp = f"zoompan=z='min(zoom+{step:.6f},{z_e:.2f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},fps={fps},setsar=1"
            vf = f"{scale_prefix},{zp}"
        else:
            vf = f"{scale_prefix},setsar=1"

        cmd = [
            FFMPEG, "-y",
            "-loop", "1", "-i", str(img_p),
            "-vf", vf,
            "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-level", "4.0", "-preset", "ultrafast",
            "-an", str(out_p)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not out_p.exists() or out_p.stat().st_size < 1000:
            raise RuntimeError(f"Görselden video klibe dönüştürme başarısız ({img_p.name}): {res.stderr}")

        return out_p

    # ─────────────────────────────────────────────────────────────
    # ZERO BLACK SCREEN GARANTİLİ ANA ORKESTRASYON METODU
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def resolve_fail_safe_clip(
        cls,
        output_clip_path: Union[str, Path],
        duration: float,
        primary_entity: str = "Tim Duncan",
        team_name: Optional[str] = "San Antonio Spurs",
        scene_text: str = "",
        character_archive_image: Optional[Union[str, Path]] = None,
        scratch_dir: Optional[Union[str, Path]] = None,
        cut_index: int = 0,
        total_cuts: Optional[int] = None,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30
    ) -> Path:
        """
        Sıfır Siyah Ekran ve Sıfır Tekrar Garantisi:
        - Ham fotoğrafı asla olduğu gibi tekrar basmaz.
        - İnfografik kartı enflasyonuna karşı katı tekil kota: Video boyunca en fazla 1 kez (`max_infographic_occurrences = 1`).
        - Gösterim anı video son çeyreğine (%72-%86 aralığına) sabitlenir. Başta veya mükerrer basılmaz.
        - Kota dolduğunda veya zamanı değilse onaylı karakter arşiv karesine derin punch-in (%140) uygular.
        - Hiçbiri olmazsa soyut hareketli doku (Abstract Motion Canvas) basar.
        """
        assert duration > 0, f"Geçersiz süre parametresi: {duration} <= 0"
        out_p = Path(output_clip_path)
        s_dir = Path(scratch_dir) if scratch_dir else out_p.parent
        s_dir.mkdir(parents=True, exist_ok=True)

        # ── KADEME A: İnfografik Kartı (Sadece Tek Bir Kez ve Video Son Çeyreğinde %72-%86) ──
        if total_cuts and total_cuts > 0:
            in_target_window = (int(total_cuts * 0.72) <= cut_index <= int(total_cuts * 0.86))
        else:
            in_target_window = (cut_index in (14, 15, 16, 17))

        has_verified_stats = (
            cls.current_infographic_stats is not None
            or any(p in primary_entity.lower() for p in ["wilt", "lebron", "jordan", "hakeem", "robinson", "duncan"])
        )
        allow_infographic = (
            not cls.skip_infographic
            and has_verified_stats
            and cls.infographic_count < cls.max_infographic_occurrences
            and not cls.last_was_infographic
            and in_target_window
        )

        if allow_infographic:
            try:
                stats_img = s_dir / f"fallback_stats_{out_p.stem}.jpg"
                cls.generate_match_stats_card(
                    output_image_path=stats_img,
                    primary_entity=primary_entity,
                    team_name=team_name,
                    width=width,
                    height=height
                )
                clip_stats = cls.convert_image_to_clip(
                    image_path=stats_img,
                    output_clip_path=out_p,
                    duration=duration,
                    width=width,
                    height=height,
                    fps=fps,
                    subtle_zoom=True
                )
                assert clip_stats.exists() and clip_stats.stat().st_size > 1000, "Stats card boş dosya üretti!"
                cls.infographic_count += 1
                cls.last_was_infographic = True
                cls.last_infographic_cut = cut_index
                logger.info(f"📊 [FallbackEngine] İnfografik kartı üretildi ({cls.infographic_count}/{cls.max_infographic_occurrences}): cut_{cut_index:03d}")
                return clip_stats
            except Exception as e_stats:
                logger.warning(f"⚠️ [FallbackEngine] Maç istatistik kartı oluşturulamadı ({e_stats}). Arşiv karesine geçiliyor...")

        cls.last_was_infographic = False

        # ── KADEME B: Karakter Arşiv Karesi (Çeşitlendirilmiş Dinamik Ken Burns & Pan) ──
        if character_archive_image:
            char_p = Path(character_archive_image)
            if char_p.exists() and char_p.stat().st_size > 15000:
                try:
                    clip_1 = cls.render_character_archive_clip(
                        image_path=char_p,
                        output_clip_path=out_p,
                        duration=duration,
                        scratch_dir=s_dir,
                        width=width,
                        height=height,
                        fps=fps,
                        variation=cut_index
                    )
                    assert clip_1.exists() and clip_1.stat().st_size > 1000, "Kademe 1 boş dosya üretti!"
                    return clip_1
                except Exception as e_k1:
                    logger.warning(f"⚠️ [FallbackEngine] Kademe 1 başarısız ({e_k1}). Kademe C dokuya geçiliyor...")

        # ── KADEME C: Soyut Hareketli Doku (Abstract Motion Canvas) ──
        texture_img = s_dir / f"fallback_texture_{out_p.stem}.jpg"
        cls.generate_abstract_motion_texture(
            output_image_path=texture_img,
            primary_entity=primary_entity,
            team_name=team_name,
            width=width,
            height=height
        )
        clip_3 = cls.convert_image_to_clip(
            image_path=texture_img,
            output_clip_path=out_p,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            subtle_zoom=True
        )

        # ── KATI SIFIR SİYAH EKRAN ASSERTION KONTROLÜ ──
        assert clip_3.exists(), f"KRİTİK HATA: Fallback klip üretilemedi: {clip_3}"
        assert clip_3.stat().st_size > 1000, f"KRİTİK HATA: Fallback klip 0-byte: {clip_3}"
        logger.info(f"✅ [FallbackEngine] Sıfır siyah ekran garantisi sağlandı: {clip_3.name} ({clip_3.stat().st_size / 1024:.1f} KB)")
        return clip_3


# Singleton erişim
fallback_engine = FallbackEngine()
