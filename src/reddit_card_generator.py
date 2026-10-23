"""
reddit_card_generator.py
========================
Reddit soru ve hikaye videoları için modern, karanlık mod (dark theme) Reddit soru kartı üretici.
Videonun başında (soru okunurken) arka plan ASMR videosu üzerine bindirilmek üzere şeffaf PNG üretir.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter


# macOS / Linux / Windows Font Yolları
FONT_BOLD_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

FONT_REGULAR_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _get_font(bold: bool = True, size: int = 32) -> ImageFont.FreeTypeFont:
    candidates = FONT_BOLD_CANDIDATES if bold else FONT_REGULAR_CANDIDATES
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Metni verilen genişliği aşmayacak şekilde satırlara böler."""
    words = text.split()
    if not words:
        return []

    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                # Tek bir kelime genişlikten büyükse mecbur ekle
                lines.append(word)
                current_line = []

    if current_line:
        lines.append(" ".join(current_line))

    return lines


LOCALIZED_REDDIT_CONFIG = {
    "tr": {
        "subreddit": "r/SorReddit",
        "posted_by": "Gönderen",
        "time_ago": "9 sa. önce",
        "comments": "Yorum",
        "default_usernames": [
            "u/merakli_genc",
            "u/gece_anlatisi",
            "u/anonim_yolcu",
            "u/itirafci_99",
            "u/kahve_molasi",
            "u/dilsiz_kalem",
            "u/karanlik_oda",
            "u/sehir_efsanesi",
            "u/sorgulayan_biri",
            "u/gizli_gunluk"
        ]
    },
    "de": {
        "subreddit": "r/FragReddit",
        "posted_by": "Gepostet von",
        "time_ago": "vor 9 Std.",
        "comments": "Kommentare",
        "default_usernames": [
            "u/nacht_erzaehler",
            "u/kuriose_geschichten",
            "u/fragensteller_de",
            "u/geheimnisvoller_mann",
            "u/zeitzeuge_99",
            "u/alltags_wahnsinn",
            "u/beobachter_berlin",
            "u/nachdenklicher_typ"
        ]
    },
    "es": {
        "subreddit": "r/PreguntasReddit",
        "posted_by": "Publicado por",
        "time_ago": "hace 9 h",
        "comments": "Comentarios",
        "default_usernames": [
            "u/historias_reales",
            "u/confesiones_anonimas",
            "u/el_curioso_es",
            "u/relato_nocturno",
            "u/ojo_critico",
            "u/cronista_callejero",
            "u/pensador_solitario",
            "u/voces_anonimas"
        ]
    },
    "en": {
        "subreddit": "r/AskReddit",
        "posted_by": "Posted by",
        "time_ago": "9h ago",
        "comments": "Comments",
        "default_usernames": [
            "u/StoryTeller",
            "u/CuriousThinker",
            "u/MidnightConfessor",
            "u/RealLifeOddities",
            "u/WanderingMind_99",
            "u/DailyObserver_X",
            "u/QuietReflections"
        ]
    }
}


def generate_reddit_card(
    question: str,
    output_path: str | Path,
    subreddit: str = None,
    author: str = None,
    avatar_path: Optional[str] = None,
    language: str = "tr",
    time_ago: str = None,
    upvotes: str = "24.5k",
    comments_count: str = "3.2k",
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    card_w: int = 940,
    card_bg_color: Tuple[int, int, int, int] = (26, 26, 27, 245),       # Reddit Dark `#1A1A1B`
    border_color: Tuple[int, int, int, int] = (52, 53, 54, 255),        # `#343536`
    text_color: Tuple[int, int, int, int] = (248, 250, 252, 255),       # Beyaz
    meta_color: Tuple[int, int, int, int] = (148, 163, 184, 255),       # `#94A3B8`
    accent_color: Tuple[int, int, int, int] = (255, 69, 0, 255),        # Reddit Turuncusu `#FF4500`
    pill_bg_color: Tuple[int, int, int, int] = (39, 39, 41, 255),       # `#272729`
    center_y: Optional[int] = None,
) -> Path:
    """
    1080x1920 dikey canvas üzerine ortalanmış Reddit soru kartı üretir.
    Dönen Path: Şeffaf RGBA PNG dosyası.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Dil ve Kullanıcı Adı Yerelleştirmesi
    lang_key = (language or "tr").lower().strip()[:2]
    loc = LOCALIZED_REDDIT_CONFIG.get(lang_key, LOCALIZED_REDDIT_CONFIG["en"])

    if not author or author.strip() in ("", "u/StoryTeller", "u/None", "StoryTeller"):
        pool = loc.get("default_usernames", ["u/StoryTeller"])
        import hashlib
        idx = int(hashlib.md5(question.encode("utf-8")).hexdigest(), 16) % len(pool)
        final_author = pool[idx]
    else:
        final_author = author if author.startswith("u/") else f"u/{author}"

    # Subreddit belirleme: Eğer verilmemişse veya genel/İngilizce varsayılan ise dile özel eşdeğerini kullan
    if not subreddit or str(subreddit).strip().lower() in ("", "r/askreddit", "askreddit", "none"):
        final_subreddit = loc.get("subreddit", "r/AskReddit")
    else:
        final_subreddit = subreddit if subreddit.startswith("r/") else f"r/{subreddit}"
    final_time_ago = time_ago or loc.get("time_ago", "9h ago")
    posted_by_label = loc.get("posted_by", "Posted by")
    comments_label = loc.get("comments", "Comments")

    # Fontları yükle
    font_sub = _get_font(bold=True, size=26)
    font_meta = _get_font(bold=False, size=20)
    font_question = _get_font(bold=True, size=38)
    font_pills = _get_font(bold=True, size=22)

    # Geçici draw nesnesi (metin ölçümü için)
    dummy_img = Image.new("RGBA", (100, 100))
    dummy_draw = ImageDraw.Draw(dummy_img)

    # 2. Soru metnini satırlara sar
    padding_x = 36
    padding_y = 32
    max_text_w = card_w - (padding_x * 2)
    lines = _wrap_text(question, font_question, max_text_w, dummy_draw)
    
    # Satır yüksekliklerini hesapla
    line_spacing = 14
    total_text_h = 0
    line_heights = []
    for line in lines:
        bbox = dummy_draw.textbbox((0, 0), line, font=font_question)
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        total_text_h += lh
    total_text_h += max(0, len(lines) - 1) * line_spacing

    # 3. Kartın toplam yüksekliğini hesapla
    header_h = 48
    gap_header_text = 24
    gap_text_footer = 28
    footer_h = 44

    card_h = padding_y + header_h + gap_header_text + total_text_h + gap_text_footer + footer_h + padding_y

    # 4. Kartı çizmek için ayrı bir RGBA resmi oluştur
    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_img)

    # Yuvarlatılmış kart arka planı
    corner_radius = 24
    card_draw.rounded_rectangle(
        [(0, 0), (card_w - 1, card_h - 1)],
        radius=corner_radius,
        fill=card_bg_color,
        outline=border_color,
        width=2
    )

    # ── HEADER: Profil / Subreddit İkonu + İsim + Meta ────────────────
    cur_y = padding_y
    icon_radius = 22
    icon_diam = icon_radius * 2
    icon_cx = padding_x + icon_radius
    icon_cy = cur_y + icon_radius
    icon_x = padding_x
    icon_y = cur_y

    avatar_drawn = False
    if avatar_path and os.path.exists(avatar_path):
        try:
            with Image.open(avatar_path) as av_img:
                av_img = av_img.convert("RGBA")
                # Square crop (center)
                min_dim = min(av_img.width, av_img.height)
                left = (av_img.width - min_dim) // 2
                top = (av_img.height - min_dim) // 2
                av_cropped = av_img.crop((left, top, left + min_dim, top + min_dim))
                
                # 2x Supersampling for crisp anti-aliased circular cut
                ss_size = icon_diam * 2
                av_resized = av_cropped.resize((ss_size, ss_size), Image.Resampling.LANCZOS)
                
                mask = Image.new("L", (ss_size, ss_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, ss_size, ss_size), fill=255)
                
                av_circle = Image.new("RGBA", (ss_size, ss_size), (0, 0, 0, 0))
                av_circle.paste(av_resized, (0, 0), mask)
                av_final = av_circle.resize((icon_diam, icon_diam), Image.Resampling.LANCZOS)
                
                card_img.alpha_composite(av_final, (icon_x, icon_y))
                card_draw.ellipse(
                    [(icon_x, icon_y), (icon_x + icon_diam, icon_y + icon_diam)],
                    outline=(255, 255, 255, 60),
                    width=1
                )
                avatar_drawn = True
        except Exception as av_err:
            print(f"[REDDIT-CARD] Özel avatar yüklenemedi: {av_err}")

    if not avatar_drawn:
        # Standart Reddit Turuncu İkon Dairesi
        card_draw.ellipse(
            [(icon_cx - icon_radius, icon_cy - icon_radius), (icon_cx + icon_radius, icon_cy + icon_radius)],
            fill=accent_color
        )
        icon_font = _get_font(bold=True, size=20)
        card_draw.text((icon_cx - 9, icon_cy - 12), "r/", font=icon_font, fill=(255, 255, 255, 255))

    # Subreddit İsmi
    sub_x = icon_cx + icon_radius + 14
    sub_bbox = card_draw.textbbox((0, 0), final_subreddit, font=font_sub)
    card_draw.text((sub_x, cur_y + 2), final_subreddit, font=font_sub, fill=text_color)

    # Meta Metni (• Gönderen: u/... • 9 sa. önce)
    meta_text = f"• {posted_by_label} {final_author} • {final_time_ago}"
    sub_w = sub_bbox[2] - sub_bbox[0]
    card_draw.text((sub_x + sub_w + 10, cur_y + 6), meta_text, font=font_meta, fill=meta_color)

    # ── QUESTION: Soru Başlığı (Büyük ve Kalın) ───────────────
    cur_y += header_h + gap_header_text
    for i, line in enumerate(lines):
        card_draw.text((padding_x, cur_y), line, font=font_question, fill=text_color)
        cur_y += line_heights[i] + line_spacing

    # ── FOOTER: Upvotes & Comments Pill'leri ─────────────────
    cur_y = padding_y + header_h + gap_header_text + total_text_h + gap_text_footer
    
    # 1. Upvote Pill
    upvote_text = f"⬆  {upvotes}  ⬇"
    upvote_bbox = dummy_draw.textbbox((0, 0), upvote_text, font=font_pills)
    upvote_w = (upvote_bbox[2] - upvote_bbox[0]) + 28
    pill_h = 38
    pill_radius = 19
    
    pill1_x = padding_x
    card_draw.rounded_rectangle(
        [(pill1_x, cur_y), (pill1_x + upvote_w, cur_y + pill_h)],
        radius=pill_radius,
        fill=pill_bg_color,
        outline=border_color,
        width=1
    )
    card_draw.text((pill1_x + 14, cur_y + 8), upvote_text, font=font_pills, fill=text_color)

    # 2. Comment Pill
    comment_text = f"💬  {comments_count} {comments_label}"
    comm_bbox = dummy_draw.textbbox((0, 0), comment_text, font=font_pills)
    comm_w = (comm_bbox[2] - comm_bbox[0]) + 28
    pill2_x = pill1_x + upvote_w + 16

    card_draw.rounded_rectangle(
        [(pill2_x, cur_y), (pill2_x + comm_w, cur_y + pill_h)],
        radius=pill_radius,
        fill=pill_bg_color,
        outline=border_color,
        width=1
    )
    card_draw.text((pill2_x + 14, cur_y + 8), comment_text, font=font_pills, fill=text_color)

    # 5. Drop Shadow (Gölge) ve 1080x1920 Tuvaline Yerleştirme
    final_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # Kartın canvas üzerindeki konumu
    pos_x = (canvas_w - card_w) // 2
    if center_y is not None:
        pos_y = int(center_y - (card_h // 2))
    else:
        # Ekranın üst-orta kısmına yerleştir (Shorts altyazılarıyla çakışmaması için y=520)
        pos_y = 520 - (card_h // 3)

    # Gölge oluştur
    shadow_pad = 20
    shadow_img = Image.new("RGBA", (card_w + shadow_pad * 2, card_h + shadow_pad * 2), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_img)
    shadow_draw.rounded_rectangle(
        [(shadow_pad, shadow_pad), (card_w + shadow_pad, card_h + shadow_pad)],
        radius=corner_radius,
        fill=(0, 0, 0, 160)
    )
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=12))

    # Canvas'a yapıştır: Önce gölge, sonra kart
    final_canvas.alpha_composite(shadow_img, (pos_x - shadow_pad, pos_y - shadow_pad + 6))
    final_canvas.alpha_composite(card_img, (pos_x, pos_y))

    final_canvas.save(output_path, "PNG")
    print(f"[REDDIT-CARD] Soru kartı başarıyla üretildi: {output_path} ({card_w}x{card_h}px)")
    return output_path
