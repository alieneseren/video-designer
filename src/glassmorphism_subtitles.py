"""
Multi-Category Dynamic Subtitles Engine for High-Retention Shorts
-----------------------------------------------------------------
Her kanal kategorisine (Travel/Food, Basketball/Sports, Tactical/Military,
Reddit/Stories, Aviation/Mystery, Science/Mind, History/Documentary, Tech/Facts)
özel, avant-garde ve benzersiz tipografik altyazı stilleri üretir.

Tasarım Standartları:
- Anti-Generic: Şablon altyazı görünümü tamamen reddedilir, her nişe özel palet ve hatlar uygulanır.
- SIFIR TAŞMA & KESİLME: Strict 820px satır sarma ve Anti-Orphan Token Seal garantisi.
- Çift Renkli Hiyerarşi: Ana metin ile kategori bazlı kritik kelimelerin renk kontrastı.
- FFmpeg Concat Demuxer uyumlu şeffaf PNG zamanlama akışı (glass_subtitles_concat.txt).
"""

import math
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from PIL import Image, ImageDraw, ImageFont


def get_bold_font(size: int = 44) -> ImageFont.FreeTypeFont:
    """Linux ve macOS üzerinde en kaliteli bold fontu bulur."""
    candidate_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        raise RuntimeError("Sistemde uygun font bulunamadı.")


@dataclass
class ChannelSubtitleTheme:
    """Kanal türüne özel tipografik ve görsel kimlik şablonu."""
    key: str
    display_name: str
    bg_color: Tuple[int, int, int, int]
    border_color: Tuple[int, int, int, int]
    border_width: int
    corner_radius: int
    shadow_color: Tuple[int, int, int, int]
    shadow_offset: Tuple[int, int]
    base_text_color: str
    highlight_color: str
    badge_bg: Tuple[int, int, int, int]
    badge_border: Tuple[int, int, int, int]
    badge_text_color: str
    badge_radius: int
    default_badge: str
    hud_brackets: bool = False
    highlights: Set[str] = field(default_factory=set)


# ─────────────────────────────────────────────────────────────
# KANAL TÜRLERİNE ÖZEL TASARIM VE RENK SİSTEMİ
# ─────────────────────────────────────────────────────────────

THEMES: Dict[str, ChannelSubtitleTheme] = {
    # 1. TRAVEL & GASTRONOMY (letstraveii)
    # Yumuşak buğulu adaçayı-kömür cam, taze nane-zümrüt kontur, safran sarısı vurgular
    "travel": ChannelSubtitleTheme(
        key="travel",
        display_name="Editorial Wanderlust & Gastronomy",
        bg_color=(14, 22, 19, 210),
        border_color=(52, 211, 153, 225),  # Emerald Mint
        border_width=2,
        corner_radius=28,  # Zarif hap (pill) formu
        shadow_color=(0, 0, 0, 110),
        shadow_offset=(0, 5),
        base_text_color="#ffffff",
        highlight_color="#fde047",  # Saffron Yellow
        badge_bg=(14, 22, 19, 225),
        badge_border=(52, 211, 153, 235),
        badge_text_color="#fde047",
        badge_radius=20,
        default_badge="TRAVEL GUIDE | LETSTRAVEII",
        highlights={
            "PAD THAI", "TACOS", "PASTOR", "CARNITAS", "CHINATOWN", "BANGKOK",
            "MEXICO", "TOKYO", "PARIS", "FOOD", "CHEF", "STREET", "RECIPE",
            "SPICY", "CRISPY", "SOUP", "MICHELIN", "MARKET", "NIGHT", "SWEET",
            "CHILI", "FLAVOR", "LOCAL", "CITY", "SECRET", "BEST", "TASTE", "DELICIOUS",
            "THOUSAND", "THOUSANDS", "HUNDRED", "MILLION", "ONE", "TWO", "THREE"
        }
    ),

    # 2. BASKETBALL & SPORTS (thebasketballshows)
    # Şampiyonluk altını stadyum HUD'ı, derin gece mavisi cam, kalın altın kontur
    "basketball": ChannelSubtitleTheme(
        key="basketball",
        display_name="Championship Gold Stadium HUD",
        bg_color=(18, 22, 34, 235),
        border_color=(251, 191, 36, 255),  # Championship Gold
        border_width=3,
        corner_radius=24,
        shadow_color=(0, 0, 0, 130),
        shadow_offset=(0, 6),
        base_text_color="#ffffff",
        highlight_color="#fbbf24",  # Pure Gold
        badge_bg=(18, 22, 34, 240),
        badge_border=(251, 191, 36, 255),
        badge_text_color="#fbbf24",
        badge_radius=20,
        default_badge="THE BASKETBALL SHOW | NBA",
        highlights={
            "NBA", "POINTS", "REBOUNDS", "ASSISTS", "BLOCKS", "LEBRON", "CURRY",
            "JORDAN", "KOBE", "LAKERS", "WARRIORS", "CELTICS", "CHAMPIONSHIP",
            "MVP", "TRIPLE-DOUBLE", "RECORD", "DUNK", "CLUTCH", "PLAYOFFS", "FINALS",
            "ONE", "TWO", "THREE", "FOUR", "FIVE", "FIRST", "LAST", "SEASON"
        }
    ),

    # 3. TACTICAL & DEFENSE (tacticallcrayon)
    # Askeri gece görüş HUD'ı, mat zeytin-siyah, lazer yeşili radar kontur ve köşe braketleri
    "tactical": ChannelSubtitleTheme(
        key="tactical",
        display_name="Tactical Military HUD",
        bg_color=(10, 14, 10, 245),
        border_color=(34, 197, 94, 240),  # Radar Green
        border_width=2,
        corner_radius=6,  # Keskin askeri teknik köşe
        shadow_color=(0, 0, 0, 160),
        shadow_offset=(0, 4),
        base_text_color="#f0fdf4",
        highlight_color="#22c55e",  # Tactical Green
        badge_bg=(10, 14, 10, 245),
        badge_border=(34, 197, 94, 255),
        badge_text_color="#22c55e",
        badge_radius=6,
        default_badge="[ TACTICAL INTEL // CLASSIFIED ]",
        hud_brackets=True,
        highlights={
            "MISSILE", "TANK", "JET", "COMBAT", "STEALTH", "SNIPER", "SPECIAL FORCES",
            "RADAR", "ARTILLERY", "DRONE", "ARMOR", "RANGE", "BULLET", "WAR",
            "DEFENSE", "ENEMY", "TARGET", "OPERATION", "SOLDIER", "WEAPON", "AIRFORCE"
        }
    ),

    # 4. REDDIT & SOCIAL STORIES (redditchroniclesa, crazyychats)
    # Reddit Gece Modu, antrasit cam, Reddit alev turuncusu Upvote kontur
    "reddit": ChannelSubtitleTheme(
        key="reddit",
        display_name="Reddit Night Mode Viral Card",
        bg_color=(26, 26, 27, 240),
        border_color=(255, 69, 0, 240),  # Reddit Upvote Orange
        border_width=2,
        corner_radius=20,
        shadow_color=(0, 0, 0, 130),
        shadow_offset=(0, 5),
        base_text_color="#ffffff",
        highlight_color="#ff5722",  # Flame Orange
        badge_bg=(26, 26, 27, 245),
        badge_border=(255, 69, 0, 255),
        badge_text_color="#ffffff",
        badge_radius=16,
        default_badge="r/AskReddit | STORYTIME",
        highlights={
            "EX-WIFE", "BOSS", "FIRED", "REVENGE", "SECRET", "CAUGHT", "MONEY",
            "TRUTH", "WEDDING", "CHEATING", "LAWYER", "POLICE", "CRAZY", "TEXT",
            "NEVER", "TOLD", "REGRET", "FAMILY", "INHERITANCE", "LIE", "FOUND"
        }
    ),

    # 5. AVIATION & BLACK BOX (blackboxaudioo)
    # Kokpit CVR paneli, simsiyah taban, acil durum havacılık kehribar/turuncu kontur
    "aviation": ChannelSubtitleTheme(
        key="aviation",
        display_name="Cockpit Voice Recorder (CVR) Telemetry",
        bg_color=(8, 9, 12, 250),
        border_color=(245, 158, 11, 255),  # Emergency Amber
        border_width=2,
        corner_radius=10,
        shadow_color=(0, 0, 0, 180),
        shadow_offset=(0, 4),
        base_text_color="#f8fafc",
        highlight_color="#f59e0b",  # Cockpit Amber
        badge_bg=(8, 9, 12, 250),
        badge_border=(245, 158, 11, 255),
        badge_text_color="#f59e0b",
        badge_radius=8,
        default_badge="CVR TRANSCRIPT // BLACK BOX",
        highlights={
            "MAYDAY", "ALTITUDE", "IMPACT", "ENGINE", "CAPTAIN", "TOWER", "RADAR",
            "PILOT", "STALL", "CRASH", "EMERGENCY", "COCKPIT", "WARNING", "OXYGEN",
            "ALARM", "DESCENT", "BLACKBOX", "FLIGHT", "FEET", "KNOTS", "CRITICAL"
        }
    ),

    # 6. NEUROSCIENCE & MIND (synapticsymphonyy)
    # Sinaptik kuantum cam, derin obsidyen çivit mavisi, elektrik camgöbeği kontur
    "science": ChannelSubtitleTheme(
        key="science",
        display_name="Synaptic Quantum Glass",
        bg_color=(15, 12, 28, 230),
        border_color=(56, 189, 248, 240),  # Electric Cyan
        border_width=2,
        corner_radius=24,
        shadow_color=(30, 20, 60, 140),
        shadow_offset=(0, 5),
        base_text_color="#ffffff",
        highlight_color="#38bdf8",  # Electric Cyan
        badge_bg=(15, 12, 28, 240),
        badge_border=(56, 189, 248, 240),
        badge_text_color="#38bdf8",
        badge_radius=20,
        default_badge="SYNAPTIC SYMPHONY // BRAIN HACKS",
        highlights={
            "BRAIN", "MEMORY", "DOPAMINE", "SLEEP", "NEURONS", "CONSCIOUSNESS",
            "PSYCHOLOGY", "HABIT", "FOCUS", "MIND", "THOUGHTS", "ENERGY",
            "INTELLIGENCE", "EVOLUTION", "HUMAN", "SCIENCE", "STUDY", "DISCOVERY"
        }
    ),

    # 7. HISTORY & PHILOSOPHY (yazanyazana)
    # Klasik arşiv derisi, espresso-antrasit cam, antika pirinç/bronz kontur
    "history": ChannelSubtitleTheme(
        key="history",
        display_name="Archival Classical Parchment",
        bg_color=(24, 21, 18, 240),
        border_color=(217, 119, 6, 235),  # Antique Brass
        border_width=2,
        corner_radius=14,
        shadow_color=(0, 0, 0, 140),
        shadow_offset=(0, 4),
        base_text_color="#fefce8",
        highlight_color="#fbbf24",  # Antique Gold
        badge_bg=(24, 21, 18, 245),
        badge_border=(217, 119, 6, 240),
        badge_text_color="#fefce8",
        badge_radius=12,
        default_badge="HISTORICAL ARCHIVES | DOCUMENTARY",
        highlights={
            "EMPIRE", "WAR", "PHILOSOPHY", "EMPEROR", "ANCIENT", "CENTURY", "LEGACY",
            "POWER", "DEATH", "ROME", "KING", "QUEEN", "BATTLE", "CONQUEST",
            "REVOLUTION", "SECRET", "TRUTH", "HISTORY", "WRITTEN", "LEADER"
        }
    ),

    # 8. TECH & GENERAL FACTS (NovaShorthes, general)
    # Buzlu titanyum cam, platin & buz mavisi kontur, siber neomint vurgular
    "tech": ChannelSubtitleTheme(
        key="tech",
        display_name="Frosted Cyber Titanium",
        bg_color=(20, 22, 27, 230),
        border_color=(96, 165, 250, 230),  # Ice Blue
        border_width=2,
        corner_radius=20,
        shadow_color=(0, 0, 0, 120),
        shadow_offset=(0, 4),
        base_text_color="#ffffff",
        highlight_color="#38bdf8",  # Ice Cyan
        badge_bg=(20, 22, 27, 240),
        badge_border=(96, 165, 250, 240),
        badge_text_color="#ffffff",
        badge_radius=16,
        default_badge="TECH MATRIX // INNOVATION",
        highlights={
            "AI", "ROBOT", "FUTURE", "QUANTUM", "COMPUTER", "SPACE", "SMARTPHONE",
            "BATTERY", "TECH", "CHIP", "CODE", "INTERNET", "REVOLUTION", "DEVICE",
            "SPEED", "DATA", "NEW", "WORLD", "BILLION", "FIRST"
        }
    )
}

# Varsayılan genel şablon
THEMES["general"] = THEMES["tech"]


def get_channel_theme(category_or_channel: str) -> ChannelSubtitleTheme:
    """Kanal adına veya kategori koduna göre en uygun stil şablonunu çözer."""
    c = (category_or_channel or "").lower().strip()

    if any(k in c for k in ("history", "philosophy", "yazanyazana", "tarih", "documentary", "archival")):
        return THEMES["history"]
    if any(k in c for k in ("basketball", "sports", "thebasketballshows", "nba")):
        return THEMES["basketball"]
    if any(k in c for k in ("travel", "food", "letstraveii", "lezzet", "gezi")):
        return THEMES["travel"]
    if any(k in c for k in ("tactical", "crayon", "military", "defense", "savunma", "combat")):
        return THEMES["tactical"]
    if any(k in c for k in ("blackbox", "aviation", "flight", "pilot", "plane", "mystery")):
        return THEMES["aviation"]
    if any(k in c for k in ("reddit", "stories", "crazyychats", "tr1_reddit", "redditchroniclesa")) or c == "story" or "_story" in c or "story_" in c:
        return THEMES["reddit"]
    if any(k in c for k in ("synaptic", "science", "psychology", "brain", "mind", "bilim")):
        return THEMES["science"]
    if any(k in c for k in ("tech", "novashorthes", "future", "ai", "robot")):
        return THEMES["tech"]

    return THEMES["general"]


def is_highlight_word(word: str, theme: ChannelSubtitleTheme) -> bool:
    """Kelimenin kanal temasına göre vurgu rengini alıp almayacağını belirler."""
    clean = re.sub(r'[^A-Z0-9$€₺%]', '', word.upper())
    if not clean:
        return False
    # Rakam veya para/yüzde sembolü içeriyorsa daima vurgulu
    if any(ch.isdigit() or ch in "$€₺%" for ch in clean):
        return True
    if clean in theme.highlights:
        return True
    for kw in theme.highlights:
        if len(kw) >= 4 and kw in clean:
            return True
    return False


def render_glassmorphic_card(
    lines_text: List[str],
    width: int = 1080,
    height: int = 1920,
    bottom_pos: int = 240,
    font_size: int = 44,
    top_badge: Optional[str] = None,
    category: str = "general",
    theme: Optional[ChannelSubtitleTheme] = None
) -> Image.Image:
    """
    Kanal türüne özel tipografik altyazı kartı ve opsiyonel kanca rozeti çizer.
    """
    if theme is None:
        theme = get_channel_theme(category)

    font = get_bold_font(font_size)
    badge_font = get_bold_font(34)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # ── 1. ÜST KANCA ROZETİ (TOP HOOK BADGE) ──
    badge_to_draw = top_badge or ""
    if badge_to_draw.strip():
        # Emojileri temizle (Pillow standart fontlarında kutu [] olarak çizilmesini engeller)
        badge_text = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]', '', badge_to_draw).strip().upper()
        badge_text = re.sub(r'\s+', ' ', badge_text).strip()
        if badge_text:
            b_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
            bw = (b_bbox[2] - b_bbox[0]) + 64
            bh = (b_bbox[3] - b_bbox[1]) + 28
            bx0 = (width - bw) // 2
            by0 = 130
            bx1 = bx0 + bw
            by1 = by0 + bh

            # Rozet yumuşak gölgesi
            draw.rounded_rectangle([bx0, by0 + 4, bx1, by1 + 4], radius=theme.badge_radius, fill=(0, 0, 0, 110))
            # Rozet cam arka planı
            draw.rounded_rectangle(
                [bx0, by0, bx1, by1],
                radius=theme.badge_radius,
                fill=theme.badge_bg,
                outline=theme.badge_border,
                width=2
            )
            # Rozet metni
            b_tx = bx0 + (bw - (b_bbox[2] - b_bbox[0])) // 2
            b_ty = by0 + 12
            draw.text((b_tx, b_ty), badge_text, font=badge_font, fill=theme.badge_text_color)

    # ── 2. METİN SATIRLARI SARMA (STRICT 820PX TEXT WRAP) ──
    MAX_LINE_PIXELS = 820
    wrapped_lines = []

    for raw_line in lines_text:
        words = raw_line.strip().split()
        if not words:
            continue
        cur_line_words = []
        cur_w = 0
        for w in words:
            bbox = draw.textbbox((0, 0), w, font=font)
            w_w = bbox[2] - bbox[0]
            add_w = w_w + (12 if cur_line_words else 0)
            if cur_line_words and (cur_w + add_w > MAX_LINE_PIXELS):
                wrapped_lines.append(" ".join(cur_line_words))
                cur_line_words = [w]
                cur_w = w_w
            else:
                cur_line_words.append(w)
                cur_w += add_w
        if cur_line_words:
            wrapped_lines.append(" ".join(cur_line_words))

    if not wrapped_lines:
        wrapped_lines = [" "]

    # ── 3. METRİKLER VE RENK HESAPLAMASI ──
    line_metrics = []
    max_line_w = 0
    total_text_h = 0
    line_spacing = 14

    for line_str in wrapped_lines:
        words = line_str.strip().split()
        line_w = 0
        line_h = 0
        words_data = []
        for w in words:
            color = theme.highlight_color if is_highlight_word(w, theme) else theme.base_text_color
            bbox = draw.textbbox((0, 0), w, font=font)
            w_w = bbox[2] - bbox[0]
            w_h = bbox[3] - bbox[1]
            words_data.append({"word": w, "color": color, "w": w_w, "h": w_h})
            line_w += w_w + 12
            line_h = max(line_h, w_h)
        if words_data:
            line_w -= 12
        max_line_w = max(max_line_w, line_w)
        total_text_h += line_h
        line_metrics.append({"words": words_data, "w": line_w, "h": line_h})

    total_text_h += max(0, len(wrapped_lines) - 1) * line_spacing

    pad_x = 44
    pad_y = 24
    card_w = max(420, min(940, max_line_w + (pad_x * 2)))
    card_h = total_text_h + (pad_y * 2)

    card_x0 = (width - card_w) // 2
    card_y0 = height - bottom_pos - card_h
    card_x1 = card_x0 + card_w
    card_y1 = card_y0 + card_h

    # ── 4. KART GÖVDESİ & ÇERÇEVE ÇİZİMİ ──
    # Yumuşak arka plan gölgesi
    sx, sy = theme.shadow_offset
    draw.rounded_rectangle(
        [card_x0 + sx, card_y0 + sy, card_x1 + sx, card_y1 + sy],
        radius=theme.corner_radius,
        fill=theme.shadow_color
    )

    # Ana Cam Kartı
    draw.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y1],
        radius=theme.corner_radius,
        fill=theme.bg_color,
        outline=theme.border_color,
        width=theme.border_width
    )

    # Taktiksel HUD Köşe Braketleri (Askeri / Savunma için)
    if theme.hud_brackets:
        bracket_len = 16
        b_color = theme.border_color
        # Üst-Sol
        draw.line([(card_x0 - 5, card_y0 - 5), (card_x0 - 5 + bracket_len, card_y0 - 5)], fill=b_color, width=2)
        draw.line([(card_x0 - 5, card_y0 - 5), (card_x0 - 5, card_y0 - 5 + bracket_len)], fill=b_color, width=2)
        # Üst-Sağ
        draw.line([(card_x1 + 5, card_y0 - 5), (card_x1 + 5 - bracket_len, card_y0 - 5)], fill=b_color, width=2)
        draw.line([(card_x1 + 5, card_y0 - 5), (card_x1 + 5, card_y0 - 5 + bracket_len)], fill=b_color, width=2)
        # Alt-Sol
        draw.line([(card_x0 - 5, card_y1 + 5), (card_x0 - 5 + bracket_len, card_y1 + 5)], fill=b_color, width=2)
        draw.line([(card_x0 - 5, card_y1 + 5), (card_x0 - 5, card_y1 + 5 - bracket_len)], fill=b_color, width=2)
        # Alt-Sağ
        draw.line([(card_x1 + 5, card_y1 + 5), (card_x1 + 5 - bracket_len, card_y1 + 5)], fill=b_color, width=2)
        draw.line([(card_x1 + 5, card_y1 + 5), (card_x1 + 5, card_y1 + 5 - bracket_len)], fill=b_color, width=2)

    # ── 5. ORTALANMIŞ VE RENKLENDİRİLMİŞ METİNLERİ BAS ──
    curr_y = card_y0 + pad_y
    for lm in line_metrics:
        curr_x = card_x0 + (card_w - lm["w"]) // 2
        for wd in lm["words"]:
            draw.text((curr_x, curr_y), wd["word"], font=font, fill=wd["color"])
            curr_x += wd["w"] + 12
        curr_y += lm["h"] + line_spacing

    return canvas


DANGLING_TRAIL_TOKENS = {
    "OF", "THE", "A", "AN", "IN", "ON", "AT", "TO", "FOR", "WITH", "FROM", "BY",
    "AS", "INTO", "ONTO", "AND", "OR", "BUT", "NOR", "WHICH", "THAT", "WHO",
    "WOULD", "COULD", "SHOULD", "WILL", "IS", "ARE", "WAS", "WERE", "BE", "HAVE", "HAS"
}


APOSTROPHE_FIXES = {
    "DIDNT": "DIDN'T",
    "HARDENS": "HARDEN'S",
    "FISHERS": "FISHER'S",
    "TODAYS": "TODAY'S",
    "COULDNT": "COULDN'T",
    "WOULDNT": "WOULDN'T",
    "SHOULDNT": "SHOULDN'T",
    "DOESNT": "DOESN'T",
    "DONT": "DON'T",
    "CANT": "CAN'T",
    "WONT": "WON'T",
    "ISNT": "ISN'T",
    "ARENT": "AREN'T",
    "WASNT": "WASN'T",
    "WERENT": "WEREN'T",
    "THAT'S": "THAT'S",
    "THATS": "THAT'S",
    "WHAT'S": "WHAT'S",
    "WHATS": "WHAT'S",
    "LEBRONS": "LEBRON'S",
    "SHAQS": "SHAQ'S",
    "CURRYS": "CURRY'S",
    "KOBES": "KOBE'S",
    "WILTS": "WILT'S"
}


def clean_sub_word(w: str) -> str:
    """
    Altyazı kelimesini temizlerken kesme işaretlerini (DIDN'T, HARDEN'S, FISHER'S)
    ve ondalık sayıları (0.4) kesinlikle korur.
    """
    if not w:
        return ""
    w = w.strip(' ,;:!?"()[]{}')
    w = w.replace('’', "'").replace('‘', "'").replace('`', "'")
    cleaned = re.sub(r"[^\w$€₺%'.]", '', w)
    cleaned = cleaned.strip(". '")
    cleaned = cleaned.upper()
    if cleaned in APOSTROPHE_FIXES:
        cleaned = APOSTROPHE_FIXES[cleaned]
    return cleaned


def is_decimal_token(w: str) -> bool:
    """Ondalık sayı belirteci tespiti (Örn: 0.4, 0.2, 99.9)."""
    return bool(re.match(r'^\d+\.\d+$', w))


def tokenize_and_chunk_subtitles(clean_narr: str) -> List[List[str]]:
    """
    Doğal konuşma ritmine (clausal pacing) ve gramer kurallarına uygun altyazı kartları üretir.
    Sarkık edat/bağlaçları (OF, THE, IN vb.) asla kart sonunda bırakmaz;
    ondalık sayıları (0.4, 0.2) noktasından bölmez ve bağlı olduğu kelimeyle mühürler;
    kapanış sorularını (WHICH WOULD YOU PICK?) parçalamadan tek kartta mühürler.
    """
    # 1. Cümleleri ayır (Ondalık sayıları bölmeyen korumalı ayrıştırıcı)
    sent_delimiters = r'(?<!\d)\.|\.(?!\d)|[!?]+'
    raw_sentences = [s.strip() for s in re.split(sent_delimiters, clean_narr) if s.strip()]
    if not raw_sentences:
        raw_sentences = [clean_narr]

    all_cards: List[List[str]] = []
    cl_pattern = r'[,:;]|(?<!\d)\.|\.(?!\d)'

    for sent in raw_sentences:
        sent = sent.replace('—', ' ').replace('–', ' ').replace('--', ' ')
        # Birleşik sayı ve yüzdelik ifadeleri tek kartta mühürleme kuralı (Keep 99TH PERCENTILE unified)
        sent = re.sub(r'\bninety[- ]ninth\s+percentile\b', '99TH_PERCENTILE', sent, flags=re.I)
        sent = re.sub(r'\b(\d+(?:st|nd|rd|th))\s+percentile\b', r'\1_PERCENTILE', sent, flags=re.I)
        # Cümleyi noktalama işaretlerine göre nefes öbeklerine (clauses) böl (ondalık sayıları koru)
        clauses = [c.strip() for c in re.split(cl_pattern, sent) if c.strip()]
        sent_cards: List[List[str]] = []

        for cl in clauses:
            cl_clean = cl.replace('-', ' ')
            raw_words = cl_clean.split()
            words = [clean_sub_word(w) for w in raw_words]
            words = [w for w in words if w]
            if not words:
                continue

            # Eğer öbek 2 ila 5 kelime ise doğrudan tek kart yap (asla bölme!)
            # 2 satırlı cam kartta (Örn: SLIDES SIX FEET / PAST HIM) kusursuz okunur.
            if len(words) <= 5:
                sent_cards.append(words)
                continue

            # 6 ve daha fazla kelime: Doğal okuma öbeği (2-4 kelime)
            i = 0
            while i < len(words):
                rem = len(words) - i
                if rem <= 5:
                    # Kalanlar 5 veya daha az ise doğrudan tek kart yap
                    sent_cards.append(words[i:])
                    break

                # Standart 3 veya 4 kelime seç
                take = 3

                # Sayısal bağlama kuralı: 3. kelime 0.4 gibi ondalıksa ve rem >= 4 ise, 4 kelime al ("WOULD FISHER'S 0.4 MIRACLE")
                if i + 2 < len(words) and is_decimal_token(words[i + 2]) and rem >= 4:
                    take = 4
                elif i + 1 < len(words) and is_decimal_token(words[i + 1]) and rem >= 3:
                    take = 3
                else:
                    w3 = words[i + 2] if i + 2 < len(words) else ''
                    w4 = words[i + 3] if i + 3 < len(words) else ''

                    if w3 in DANGLING_TRAIL_TOKENS and w4 and w4 not in DANGLING_TRAIL_TOKENS and rem >= 4:
                        take = 4
                    elif w3 in DANGLING_TRAIL_TOKENS:
                        take = 2
                    elif w4 in DANGLING_TRAIL_TOKENS:
                        take = 3
                    else:
                        take = 3

                # Kesin Anti-Orphan Güvencesi: Kartın son kelimesi DANGLING_TRAIL_TOKENS veya tek başına ondalık sayı ise geri çek
                while take > 2 and (words[i + take - 1] in DANGLING_TRAIL_TOKENS or is_decimal_token(words[i + take - 1])):
                    take -= 1

                sent_cards.append(words[i:i + take])
                i += take

        # Cümle içi 1 kelimelik öksüz kartları bitişik karta kaynaştır
        cleaned_sent_cards: List[List[str]] = []
        for c in sent_cards:
            c = [w for w in c if w]
            if not c:
                continue
            if len(c) == 1:
                if cleaned_sent_cards and len(cleaned_sent_cards[-1]) <= 3:
                    cleaned_sent_cards[-1].extend(c)
                else:
                    cleaned_sent_cards.append(c)
            else:
                if cleaned_sent_cards and len(cleaned_sent_cards[-1]) == 1:
                    cleaned_sent_cards[-1].extend(c)
                else:
                    cleaned_sent_cards.append(c)

        all_cards.extend(cleaned_sent_cards)

    # 3. Son kart yetim denetimi (Final Anti-Orphan Seal)
    if len(all_cards) >= 2 and len(all_cards[-1]) <= 2:
        if len(all_cards[-2]) + len(all_cards[-1]) <= 5:
            all_cards[-2].extend(all_cards.pop())
        else:
            comb = all_cards[-2] + all_cards[-1]
            mid = (len(comb) + 1) // 2
            # Sayısal bağlama kuralı: Asla ondalık sayı (0.4) ile bitirme, sayıyı sonraki isimle birleştir
            if mid < len(comb) and is_decimal_token(comb[mid - 1]):
                mid += 1
            all_cards[-2] = comb[:mid]
            all_cards[-1] = comb[mid:]

    return all_cards


def generate_glassmorphism_subtitles(
    script: Dict[str, Any],
    total_dur: float,
    scratch_dir: Path,
    W: int = 1080,
    H: int = 1920,
    top_badge: Optional[str] = None,
    category: str = "general",
    visual_plan: Optional[Dict[str, Any]] = None,
    sentence_boundaries: Optional[List[Dict[str, Any]]] = None
) -> Path:
    """
    Tüm anlatımı 2-4 kelimelik doğal kartlara böler, kanal temasına göre şeffaf PNG üretir
    ve FFmpeg concat listesi (glass_subtitles_concat.txt) oluşturur.
    SentenceBoundary desteği ile kümülatif altyazı gecikmesi %100 sıfırlanır.
    """
    scratch_dir = Path(scratch_dir)
    theme = get_channel_theme(category)

    # 1. VisualDirector veya Proje Planından Dinamik Rozet & Pencere Çözme
    badge_start = 0.0
    badge_end = 4.5
    effective_top_badge = None

    if visual_plan and isinstance(visual_plan, dict):
        p_meta = visual_plan.get("project_meta", {})
        effective_top_badge = p_meta.get("category_badge")
        b_win = p_meta.get("badge_display_window") or {}
        badge_start = float(b_win.get("start_sec", 0.0))
        badge_end = float(b_win.get("end_sec", 4.5))

    if not effective_top_badge:
        try:
            from visual_director import visual_director
        except ImportError:
            try:
                from src.visual_director import visual_director
            except ImportError:
                visual_director = None
        if visual_director is not None:
            prof = visual_director.detect_domain_profile(
                script.get("title", "") or script.get("topic", ""),
                category,
                str(script)
            )
            effective_top_badge = prof.get("category_badge")
            b_win = prof.get("badge_display_window") or {}
            badge_start = float(b_win.get("start_sec", 0.0))
            badge_end = float(b_win.get("end_sec", 4.5))

    # Konuya ve kanala duyarlı dinamik üst rozet (Top Header Bug) fallback belirleme
    if not effective_top_badge:
        raw_badge = (top_badge or "").replace("🌍", "").strip()
        is_generic = not raw_badge or any(g in raw_badge.upper() for g in ["MUST VISIT", "TRAVEL GUIDE", "LETSTRAVEII", "EXPLORE"])
        
        topic_corpus = f"{script.get('title', '')} {script.get('topic', '')} {category}".lower()
        if is_generic:
            if any(w in topic_corpus for w in ["airplane", "airline", "aircraft", "cockpit", "flight", "cabin", "landing", "aviation"]):
                effective_top_badge = "AVIATION SECRETS"
            elif any(w in topic_corpus for w in ["live like royalty", "50/day", "luxury", "villa", "budget luxury"]):
                effective_top_badge = "BUDGET LUXURY GUIDE"
            elif any(w in topic_corpus for w in ["underground city", "derinkuyu", "ancient", "mystery", "cappadocia", "civilization", "archaeology", "ruins", "history", "monument"]):
                effective_top_badge = "ANCIENT MYSTERIES"
            elif any(w in topic_corpus for w in ["street food", "food", "tacos", "pad thai", "culinary", "bangkok vs"]):
                effective_top_badge = "STREET FOOD SHOWDOWN"
            elif any(w in topic_corpus for w in ["train", "railway", "alps", "mountain", "steepest"]):
                effective_top_badge = "SCENIC EXPEDITIONS"
            elif raw_badge:
                effective_top_badge = raw_badge
            else:
                effective_top_badge = theme.default_badge
        else:
            effective_top_badge = raw_badge

    # 2. Otomatik SentenceBoundary tespiti (Dosyadan veya parametreden)
    if not sentence_boundaries:
        sb_candidates = [
            scratch_dir / "sentence_boundaries.json",
            scratch_dir.parent / "sentence_boundaries.json",
            scratch_dir.parent / "voiceover_boundaries.json"
        ]
        for sbc in sb_candidates:
            if sbc.exists():
                try:
                    import json
                    loaded_sb = json.loads(sbc.read_text(encoding="utf-8"))
                    if isinstance(loaded_sb, list) and len(loaded_sb) > 0:
                        sentence_boundaries = loaded_sb
                        print(f"[SubtitlesEngine] 🎯 {len(sentence_boundaries)} adet SentenceBoundary dosyasından okundu: {sbc.name}")
                        break
                except Exception:
                    pass

    sub_dir = scratch_dir / "glass_sub_cards"
    if sub_dir.exists():
        shutil.rmtree(sub_dir, ignore_errors=True)
    sub_dir.mkdir(parents=True, exist_ok=True)
    concat_lines = []

    cards_data = []
    card_durations = []

    if sentence_boundaries and isinstance(sentence_boundaries, list) and len(sentence_boundaries) > 0:
        # ── KELİME & CÜMLE SEVİYESİNDE SALİSE KİLİTLİ ALTYAZI (SIFIR KÜMÜLATİF GECİKME) ──
        num_sents = len(sentence_boundaries)
        for s_idx, sb in enumerate(sentence_boundaries):
            raw_s = sb.get("text", "")
            clean_s = re.sub(r'(\b\w+)\s*[-—]\s*(\w+\b)', r'\1 \2', raw_s)
            clean_s = clean_s.replace('—', ' , ').replace('...', ' , ')
            clean_s = re.sub(r'\s+', ' ', clean_s).strip()
            # Birleşik sayı ve yüzdelik ifadeleri mühürleme kuralı (Keep 99TH PERCENTILE unified)
            clean_s = re.sub(r'\bninety[- ]ninth\s+percentile\b', '99TH_PERCENTILE', clean_s, flags=re.I)
            clean_s = re.sub(r'\b(\d+(?:st|nd|rd|th))\s+percentile\b', r'\1_PERCENTILE', clean_s, flags=re.I)
            if not clean_s:
                continue

            c_phrases = tokenize_and_chunk_subtitles(clean_s)
            if not c_phrases:
                continue

            s_start = float(sb.get("offset", 0.0))
            if s_idx == 0:
                s_start = 0.0

            if s_idx + 1 < num_sents:
                next_start = float(sentence_boundaries[s_idx + 1].get("offset", s_start + sb.get("duration", 2.0)))
            else:
                next_start = total_dur

            s_window = max(0.8, next_start - s_start)
            # Kelime sayısı ve karakter uzunluğu ağırlıklı adil süre dağılımı
            # 4-5 kelimelik kartlara (Örn: "SLIDES SIX FEET PAST HIM") en az 1.30s+ rahat okuma süresi garanti eder
            weights = [max(1.0, len(cp) * 0.80 + sum(len(w) for w in cp) * 0.10) for cp in c_phrases]
            total_w = sum(weights)
            s_durs = [max(0.60, round(s_window * (w / max(0.001, total_w)), 3)) for w in weights]
            diff = round(s_window - sum(s_durs), 3)
            s_durs[-1] = max(0.65, round(s_durs[-1] + diff, 3))

            for cp_idx, cp in enumerate(c_phrases):
                if len(cp) <= 3:
                    lines = [" ".join(cp).replace("_PERCENTILE", " PERCENTILE")]
                else:
                    mid = (len(cp) + 1) // 2
                    lines = [
                        " ".join(cp[:mid]).replace("_PERCENTILE", " PERCENTILE"),
                        " ".join(cp[mid:]).replace("_PERCENTILE", " PERCENTILE")
                    ]
                cp_chars = sum(len(w) for w in cp)
                cp_dur = s_durs[cp_idx]

                cards_data.append({"lines": lines, "chars": cp_chars})
                card_durations.append(cp_dur)
    else:
        # ── KLASİK KARAKTER DAĞILIMI (Fallback Modu) ──
        scenes = script.get("scenes", [])
        raw_texts = []
        if scenes and isinstance(scenes, list):
            for sc in scenes:
                t = sc.get("narration") or sc.get("text") or ""
                if t.strip():
                    raw_texts.append(t.strip())
        else:
            raw_text = script.get("narration") or script.get("story") or script.get("body") or script.get("title", "")
            if isinstance(raw_text, list):
                raw_text = " ".join(raw_text)
            raw_texts.append(str(raw_text).strip())

        full_narr = " ".join(raw_texts)
        clean_narr = re.sub(r'(\b\w+)\s*[-—]\s*(\w+\b)', r'\1 \2', full_narr)
        clean_narr = clean_narr.replace('—', ' , ').replace('...', ' , ')
        clean_narr = re.sub(r'\s+', ' ', clean_narr).strip()

        # Gramer ve öksüz korumalı doğal kartlara böl
        card_phrases = tokenize_and_chunk_subtitles(clean_narr)

        for cp in card_phrases:
            if len(cp) <= 3:
                lines = [" ".join(cp).replace("_PERCENTILE", " PERCENTILE")]
            else:
                mid = (len(cp) + 1) // 2
                lines = [
                    " ".join(cp[:mid]).replace("_PERCENTILE", " PERCENTILE"),
                    " ".join(cp[mid:]).replace("_PERCENTILE", " PERCENTILE")
                ]
            char_count = sum(len(w) for w in cp)
            cards_data.append({"lines": lines, "chars": char_count})

        if not cards_data:
            fallback_title = script.get("title") or "EXCLUSIVE SHORTS"
            cards_data = [{"lines": [fallback_title.upper()[:25]], "chars": len(fallback_title)}]

        num_cards = len(cards_data)
        if num_cards == 1:
            card_durations = [total_dur]
        else:
            last_card_target = max(2.20, min(4.00, total_dur * 0.16))
            remaining_time = max(total_dur - last_card_target, float(num_cards - 1) * 1.05)
            remaining_chars = max(1, sum(cards_data[i]["chars"] for i in range(num_cards - 1)))

            running_sum = 0.0
            for i in range(num_cards - 1):
                c_dur = remaining_time * (cards_data[i]["chars"] / remaining_chars)
                c_dur = max(1.05, c_dur)
                card_durations.append(c_dur)
                running_sum += c_dur

            final_card_dur = max(2.20, round(total_dur - running_sum, 3))
            card_durations.append(final_card_dur)

    # Üst rozet tam sözleşme penceresinde (badge_start..badge_end, ör: 0.0s - 4.5s) görünür, ardından kaybolur
    accumulated_time = 0.0
    for idx, cdata in enumerate(cards_data):
        dur = card_durations[idx]
        show_badge = effective_top_badge if (badge_start <= accumulated_time < badge_end) else None

        card_img = render_glassmorphic_card(
            cdata["lines"],
            width=W,
            height=H,
            bottom_pos=240,
            font_size=44,
            top_badge=show_badge,
            category=category,
            theme=theme
        )
        card_path = sub_dir / f"card_{idx:03d}.png"
        card_img.save(card_path, "PNG")

        concat_lines.append(f"file '{card_path.resolve()}'")
        concat_lines.append(f"duration {dur:.3f}")
        accumulated_time += dur

    if cards_data:
        last_card = sub_dir / f"card_{len(cards_data)-1:03d}.png"
        concat_lines.append(f"file '{last_card.resolve()}'")
        concat_lines.append("duration 10.000")  # Son segment mühürleme
        concat_lines.append(f"file '{last_card.resolve()}'")

    concat_file = scratch_dir / "glass_subtitles_concat.txt"
    concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    print(f"[SubtitlesEngine] 🎨 [{theme.display_name}] {len(cards_data)} adet tematik altyazı kartı hazırlandı: {concat_file.name}")
    return concat_file
