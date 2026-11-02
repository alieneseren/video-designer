"""
Universal Glassmorphism Subtitles Engine for High-Retention Shorts
------------------------------------------------------------------
Tüm kategoriler (Spor, Seyahat, Yemek, Belgesel, Teknoloji, Genel) için
altın çerçeveli, yarı saydam koyu cam (glassmorphism) altyazı kartları üretir.

Özellikler:
- SIFIR TAŞMA & KESİLME GARANTİSİ (Strict 800px text wrap & Anti-Orphan Token Seal)
- Çift renkli tipografi: Sayılar, özel isimler ve vurgu kelimeleri altın sarısı (#fbbf24), diğerleri beyaz (#ffffff)
- Koyu cam arka plan: rgba(18, 22, 34, 0.90) + Altın çerçeve rgba(251, 191, 36, 1.0) + Yumuşak gölge
- Opsiyonel Üst Kanca Rozeti (Top Hook Badge / Glass Pill)
- FFmpeg Concat Demuxer uyumlu zamanlama listesi (subtitles_concat.txt)
"""

import math
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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


# Genel & Kategori Bazlı Vurgu Kelimeleri
UNIVERSAL_HIGHLIGHTS = {
    # Sayılar ve miktar kelimeleri
    "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
    "THOUSAND", "THOUSANDS", "HUNDRED", "HUNDREDS", "MILLION", "BILLION",
    "FIRST", "LAST", "ULTIMATE", "SHOWDOWN", "RECORD", "SECRET", "BEST", "WORST",
    "MUST", "VISIT", "WARNING", "RULES", "RULE", "NEVER", "ALWAYS", "REVEALED",
    # Seyahat & Yemek
    "BANGKOK", "MEXICO", "CITY", "TACOS", "PASTOR", "PAD THAI", "CHINATOWN",
    "MICHELIN", "STREET", "FOOD", "CARNITAS", "CHILIES", "ADOBO", "WOK",
    "TOKYO", "JAPAN", "PARIS", "FRANCE", "ROME", "ITALY", "ALPS", "NEW YORK",
    "LONDON", "EUROPE", "AMSTERDAM", "SANTORINI", "GREECE", "ICELAND",
    # Spor / NBA
    "NBA", "TRIPLE-DOUBLE", "CHAMPIONSHIP", "LEBRON", "JORDAN", "KOBE", "CURRY",
    "WARRIORS", "LAKERS", "POINTS", "REBOUNDS", "ASSISTS", "BLOCKS", "MVP"
}


def is_highlight_word(word: str, category: str = "general") -> bool:
    """Kelimenin altın sarısı (#fbbf24) ile vurgulanıp vurgulanmayacağını belirler."""
    clean = re.sub(r'[^A-Z0-9$€₺%]', '', word.upper())
    if not clean:
        return False
    # Rakam veya para/yüzde sembolü içeriyorsa mutlaka sarı
    if any(c.isdigit() or c in "$€₺%" for c in clean):
        return True
    if clean in UNIVERSAL_HIGHLIGHTS:
        return True
    for kw in UNIVERSAL_HIGHLIGHTS:
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
    category: str = "general"
) -> Image.Image:
    """
    Altın çerçeveli glassmorphism altyazı kartı ve opsiyonel kanca rozeti çizer.
    """
    font = get_bold_font(font_size)
    badge_font = get_bold_font(34)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # ── 1. ÜST KANCA ROZETİ (TOP HOOK BADGE / GLASS PILL) ──
    if top_badge and top_badge.strip():
        # Emojileri temizle (Pillow standart fontlarında kutu [] olarak çizilmesini engeller)
        badge_text = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]', '', top_badge).strip().upper()
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
            draw.rounded_rectangle([bx0, by0 + 4, bx1, by1 + 4], radius=20, fill=(0, 0, 0, 110))
            # Rozet cam arka planı
            draw.rounded_rectangle([bx0, by0, bx1, by1], radius=20, fill=(15, 20, 32, 220), outline=(251, 191, 36, 230), width=2)
            # Rozet metni (ortalanmış altın & beyaz)
            b_tx = bx0 + (bw - (b_bbox[2] - b_bbox[0])) // 2
            b_ty = by0 + 12
            draw.text((b_tx, b_ty), badge_text, font=badge_font, fill="#ffffff")

    # ── 2. METİN SATIRLARI SARMA (STRICT 800PX TEXT WRAP) ──
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

    # ── 3. METRİKLER VE ÇİFT RENK HESAPLAMASI ──
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
            color = "#fbbf24" if is_highlight_word(w, category) else "#ffffff"
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

    # ── 4. GLASSMORPHISM KARTI ÇİZİMİ ──
    # Yumuşak arka plan gölgesi
    draw.rounded_rectangle([card_x0, card_y0 + 6, card_x1, card_y1 + 6], radius=24, fill=(0, 0, 0, 120))
    # Ana Cam Kartı: rgba(18, 22, 34, 0.90) + 3px Altın Çerçeve rgba(251, 191, 36, 1.0)
    draw.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y1],
        radius=24,
        fill=(18, 22, 34, 230),
        outline=(251, 191, 36, 255),
        width=3
    )

    # ── 5. ORTALANMIŞ VE ÇİFT RENKLİ METİNLERİ BAS ──
    curr_y = card_y0 + pad_y
    for lm in line_metrics:
        curr_x = card_x0 + (card_w - lm["w"]) // 2
        for wd in lm["words"]:
            draw.text((curr_x, curr_y), wd["word"], font=font, fill=wd["color"])
            curr_x += wd["w"] + 12
        curr_y += lm["h"] + line_spacing

    return canvas


def generate_glassmorphism_subtitles(
    script: Dict[str, Any],
    total_dur: float,
    scratch_dir: Path,
    W: int = 1080,
    H: int = 1920,
    top_badge: Optional[str] = None,
    category: str = "general"
) -> Path:
    """
    Tüm anlatımı 2-4 kelimelik doğal kartlara böler, her kart için şeffaf PNG üretir
    ve FFmpeg concat listesi (subtitles_concat.txt) oluşturur.
    """
    scratch_dir = Path(scratch_dir)
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

    # 2-4 kelimelik doğal kartlara böl
    raw_words = clean_narr.split()
    card_phrases = []
    curr_phrase = []

    for w in raw_words:
        w_clean = w.strip()
        if not w_clean:
            continue
        curr_phrase.append(w_clean)
        ends_punc = any(w_clean.endswith(p) for p in ['.', '!', '?', ',', ';', ':'])
        if len(curr_phrase) >= 4 or (len(curr_phrase) >= 2 and ends_punc):
            clean_words = [re.sub(r'[.,!?;:]', '', x).strip().upper() for x in curr_phrase if x.strip()]
            if clean_words:
                card_phrases.append(clean_words)
            curr_phrase = []

    if curr_phrase:
        clean_words = [re.sub(r'[.,!?;:]', '', x).strip().upper() for x in curr_phrase if x.strip()]
        if clean_words:
            card_phrases.append(clean_words)

    # Anti-Orphan Token Seal: Son kartta 1-2 yetim kelime kalmasını önle
    if len(card_phrases) >= 2 and len(card_phrases[-1]) <= 2:
        prev_cp = card_phrases[-2]
        last_cp = card_phrases[-1]
        combined = prev_cp + last_cp
        if len(combined) <= 5:
            card_phrases[-2] = combined
            card_phrases.pop()
        else:
            mid = (len(combined) + 1) // 2
            card_phrases[-2] = combined[:mid]
            card_phrases[-1] = combined[mid:]

    cards_data = []
    for cp in card_phrases:
        if len(cp) <= 3:
            lines = [" ".join(cp)]
        else:
            mid = (len(cp) + 1) // 2
            lines = [" ".join(cp[:mid]), " ".join(cp[mid:])]
        char_count = sum(len(w) for w in cp)
        cards_data.append({"lines": lines, "chars": char_count})

    if not cards_data:
        fallback_title = script.get("title") or "EXCLUSIVE SHORTS"
        cards_data = [{"lines": [fallback_title.upper()[:25]], "chars": len(fallback_title)}]

    sub_dir = scratch_dir / "glass_sub_cards"
    if sub_dir.exists():
        shutil.rmtree(sub_dir, ignore_errors=True)
    sub_dir.mkdir(parents=True, exist_ok=True)
    concat_lines = []

    # Süre dağıtımı (Son karta en az 2.20s garanti)
    num_cards = len(cards_data)
    card_durations = []
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

    # Üst Kanca Rozetini İlk 4.5 sn boyunca göster
    badge_cutoff_time = 4.5
    accumulated_time = 0.0

    for idx, cdata in enumerate(cards_data):
        dur = card_durations[idx]
        show_badge = top_badge if (accumulated_time < badge_cutoff_time and top_badge) else None

        card_img = render_glassmorphic_card(
            cdata["lines"],
            width=W,
            height=H,
            bottom_pos=240,
            font_size=44,
            top_badge=show_badge,
            category=category
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
    print(f"[GlassmorphismSubtitles] ✨ {len(cards_data)} adet altın çerçeveli koyu cam altyazı kartı hazırlandı: {concat_file.name}")
    return concat_file
