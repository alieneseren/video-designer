"""
crayon_combat_engine.py
Crayon Combat: Askeri Araçlar, Savunma Sanayii & Çöp Adam Kurgu Motoru

Özellikler:
1. "Crayon Combat" (Askeri Araçlar + Çöp Adam Hicvi) senaryo promptları ve konu havuzu.
2. 4 İkonik Vektörel Çöp Adam Karakter Çizim Motoru (PIL tabanlı, bağımsız, anında 0.01 sn üretim):
   - 💰 CEO (Takım elbiseli, para çantalı, açgözlü savunma sanayii yöneticisi)
   - 🎖️ General (Madalyalı, subay şapkalı, bütçe tablosundan saçını yolan Pentagon komutanı)
   - 🪖 Pilot (Devasa kasklı, terleyen zavallı test pilotu)
   - 🕵️ Casus (Dürbünlü, fötr şapkalı rakip ülke mühendisi/ajanı)
3. Taktik Blueprint & Askeri Kartvizit Üreticisi (1920x1080, teknik veri HUD + konuşma balonu).
4. Diğer ajanların çalıştığı dosyalara kesinlikle müdahale etmeden izole çalışır.
"""

import os
import sys
import json
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

# Font Seçici
def get_font(size: int, font_type: str = "sans") -> ImageFont.ImageFont:
    candidates = []
    if font_type == "mono":
        candidates = [
            "/System/Library/Fonts/Courier.dfont",
            "/System/Library/Fonts/SFNSMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    elif font_type == "bold":
        candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFProDisplay-Bold.otf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFProText-Regular.otf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ═════════════════════════════════════════════════════════════════════════════
# 1. SENARYO PROMPTLARI VE ASKERİ ÇÖP ADAM KONULARI
# ═════════════════════════════════════════════════════════════════════════════

CRAYON_COMBAT_SYSTEM_PROMPT = """You are the Lead Creator of "Tactical Crayon", an entertaining military technology and satire channel. Combine accessible engineering explanations, dry procurement humor, and clear stickman visuals without sacrificing factual accuracy.

Cover publicly documented military aircraft, vehicles, programs, and engineering trade-offs. Do not present fictional procurement scandals, invented program names, invented tests, or invented statistics as real. If a detail cannot be tied to a credible source, omit it or clearly label it as a hypothetical joke. Keep operational details high-level and non-instructional.

OPENING & RETENTION:
- Start on the first spoken frame with a specific, verified surprise or contradiction and its stakes. No greeting, channel introduction, or slow historical preamble.
- In the first 5-10 seconds, state the verified surprise and the central question; if the strongest detail is uncertain, do not invent one to make the hook more dramatic.
- Open one evidence-backed question in the hook, promise when it will be answered, and resolve it before the final verdict.
- Pay off the opening early, then add a useful reveal, visual change, or short on-screen callout every 20-30 seconds. Avoid repeating the same cost joke or premise.
- Write each scene as a sequence of concrete visual beats (object, diagram, comparison, source detail, or character reaction); narration must not simply describe a static slide.
- Build a clear arc: hook and promise; how the system works; the real trade-offs and evidence; what the evidence does and does not prove; concise verdict.
- Target 6-8 minutes. If the evidence cannot sustain that length, prefer a shorter complete video over padding. Remove any scene that does not add evidence, explanation, or a fresh visual idea.

TITLE & THUMBNAIL:
- Provide three distinct, factual title options, each under 75 characters. Lead with the recognizable subject and a real curiosity gap; avoid unsupported superlatives, fake dollar figures, and vague listicle framing.
- Provide a thumbnail_text of 2-4 words and a thumbnail_concept describing one clear focal object, one expressive character, and strong contrast. Do not repeat the full title on the thumbnail.
- Titles and thumbnails must promise only what the video actually demonstrates.

KEY CHARACTER ARCHETYPES IN SCRIPTS:
- [DEFENSE_CEO]: The defense contractor executive with dollar signs in his eyes, always justifying outrageous budget overruns ("General, the stealth paint needs to be hand-brushed with crushed diamonds!").
- [GENERAL]: The stressed Pentagon general holding massive bills, having panic attacks over cost overruns.
- [PILOT]: The sweating test pilot dealing with software glitches and complex flight manuals.
- [SPY]: The rival foreign engineer trying to copy blueprints with binoculars.

DURATION & SCENE REQUIREMENTS:
- Provide concise scenes for a total of 6-8 minutes. Each scene should support visual cuts about every 4-6 seconds; keep narration varied and avoid padding.
- The first scene must carry the cold-open hook; do not create a separate intro.
- Use short on-screen callouts, not full narration paragraphs. Include "audio_cue" as "impact", "drop", or "none"; use "drop" only for a genuine reveal or comedic pause.
- Provide a concise, useful description and 8-12 relevant searchable tags.
- Include a sources array with credible source names and URLs for factual claims. Separate confirmed facts from estimates and clearly flag uncertainty. Never invent a citation.

OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown codeblocks:
{
  "title": "One accurate, curiosity-led title",
  "title_variants": [{"title": "Alternative title 1"}, {"title": "Alternative title 2"}, {"title": "Alternative title 3"}],
  "thumbnail_text": "2-4 WORDS",
  "thumbnail_concept": "One clear focal object, one expressive character, high contrast; no unsupported claim.",
  "description": "Concise summary of the subject, the evidence covered, and a question for viewers.",
  "tags": ["Tactical Crayon", "Military Technology", "Engineering", "Documentary", "Satire"],
  "keywords": ["subject designation", "engineering trade-offs", "military technology"],
  "vehicle_name": "Official designation, if applicable",
  "vehicle_nickname": "Only a documented or clearly identified editorial nickname",
  "vehicle_type": "Verified general type",
  "sources": [{"name": "Source organization or publication", "url": "https://example.org/source"}],
  "fact_check_notes": ["Separate confirmed facts, estimates, and unresolved claims."],
  "scenes": [
    {
      "scene_id": 1,
      "chapter": "COLD OPEN",
      "active_character": "DEFENSE_CEO",
      "narration": "A concise, source-grounded cold open that states the real surprise and the question the video will answer.",
      "character_dialogue": "A short satirical reaction that does not introduce a new factual claim.",
      "visual_type": "editorial_briefing",
      "audio_cue": "impact",
      "emotion": "satirical"
    }
  ]
}
"""

CURATED_CRAYON_COMBAT_TOPICS = [
    {
        "id": "f35_flying_iphone",
        "title": "F-35 Lightning II: The Trade-Offs Behind One Jet for Every Mission",
        "vehicle": "Lockheed Martin F-35 Lightning II",
        "investigation_angle": "Explain the documented helmet-mounted display and verify any program-cost figure from a dated public source.",
        "primary_character": "DEFENSE_CEO"
    },
    {
        "id": "a10_brrrrt_titan",
        "title": "A-10 Warthog: Why the Airframe Was Built Around Its Cannon",
        "vehicle": "Fairchild Republic A-10 Thunderbolt II",
        "investigation_angle": "Explain the documented relationship between the GAU-8/A and the aircraft's design, with a credible source.",
        "primary_character": "PILOT"
    },
    {
        "id": "b2_billion_dollar_parking",
        "title": "B-2 Spirit: The Engineering Trade-Offs of a Stealth Bomber",
        "vehicle": "Northrop Grumman B-2 Spirit Stealth Bomber",
        "investigation_angle": "Examine documented low-observable maintenance trade-offs; omit cost claims unless source and year are provided.",
        "primary_character": "GENERAL"
    },
    {
        "id": "su57_russia_ghost",
        "title": "Su-57: What Public Evidence Says About Russia's Stealth Fighter",
        "vehicle": "Sukhoi Su-57 Felon",
        "investigation_angle": "Separate independently verified public information from official claims and clearly label uncertainty.",
        "primary_character": "SPY"
    },
    {
        "id": "sr71_mach3_leaker",
        "title": "SR-71 Blackbird: Why Its Fuel Tanks Sealed in Flight",
        "vehicle": "Lockheed SR-71 Blackbird",
        "investigation_angle": "Explain the documented effects of thermal expansion on the aircraft, citing a credible historical source.",
        "primary_character": "PILOT"
    }
]


# ═════════════════════════════════════════════════════════════════════════════
# 2. VEKTÖREL ÇÖP ADAM ÇİZİM MOTORU (STICKMAN RENDERER)
# ═════════════════════════════════════════════════════════════════════════════

def draw_stickman_character(
    role: str = "CEO",
    mood: str = "happy",
    scale: float = 1.0
) -> Image.Image:
    """
    4 farklı ikonik çöp adam arketipini şeffaf (RGBA) katmanda çizer.
    Roller: 'CEO', 'GENERAL', 'PILOT', 'SPY'
    """
    size = int(600 * scale)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = size // 2
    head_r = int(72 * scale)
    head_y = int(140 * scale)

    line_w = max(4, int(7 * scale))
    outline_col = (248, 250, 252, 255) # Beyaz/aydınlık çöp adam çizgisi (#f8fafc)
    skin_fill = (254, 243, 199, 255) # Sıcak hafif krem karikatür teni

    # 1. Kafa (Round Cartoon Head)
    head_box = [(cx - head_r, head_y - head_r), (cx + head_r, head_y + head_r)]
    draw.ellipse(head_box, fill=skin_fill, outline=outline_col, width=line_w)

    # 2. Gövde (Spine)
    body_top = head_y + head_r
    body_bottom = int(head_y + head_r + 175 * scale)
    draw.line([(cx, body_top), (cx, body_bottom)], fill=outline_col, width=line_w)

    # 3. Bacaklar (Stick Legs)
    leg_len = int(155 * scale)
    draw.line([(cx, body_bottom), (cx - int(75 * scale), body_bottom + leg_len)], fill=outline_col, width=line_w)
    draw.line([(cx, body_bottom), (cx + int(75 * scale), body_bottom + leg_len)], fill=outline_col, width=line_w)

    # 4. Role Göre Özel Çizimler ve Aksesuarlar
    role_u = role.upper()

    if "CEO" in role_u:
        # Takım Elbise / Yakalık
        collar_w = int(32 * scale)
        draw.polygon([(cx - collar_w, body_top + int(15 * scale)), (cx, body_top + int(45 * scale)), (cx + collar_w, body_top + int(15 * scale))], fill=(30, 41, 59, 255), outline=outline_col, width=2)
        
        # Parlak Kırmızı Kravat
        neck_y = body_top + int(18 * scale)
        tie_len = int(95 * scale)
        draw.polygon([
            (cx, neck_y),
            (cx - int(16 * scale), neck_y + tie_len),
            (cx, neck_y + tie_len + int(20 * scale)),
            (cx + int(16 * scale), neck_y + tie_len)
        ], fill=(239, 68, 68, 255), outline=(185, 28, 28, 255), width=2)

        # Gözler: Yeşil Dolar İşaretleri ($)
        font_dolar = get_font(int(32 * scale), "bold")
        draw.text((cx - int(48 * scale), head_y - int(30 * scale)), "$", font=font_dolar, fill=(34, 197, 94, 255))
        draw.text((cx + int(18 * scale), head_y - int(30 * scale)), "$", font=font_dolar, fill=(34, 197, 94, 255))

        # Sinsi / Açgözlü Sırıtış
        draw.arc([(cx - int(42 * scale), head_y - int(10 * scale)), (cx + int(42 * scale), head_y + int(45 * scale))], 20, 160, fill=(30, 41, 59), width=line_w)

        # Kollar: Sol kolda kocaman yeşil para çantası
        hand_l = (cx - int(130 * scale), body_top + int(90 * scale))
        draw.line([(cx, body_top + int(40 * scale)), hand_l], fill=outline_col, width=line_w)
        # Sağ kol havada para saçıyor veya tokalaşmaya uzanıyor
        draw.line([(cx, body_top + int(40 * scale)), (cx + int(115 * scale), body_top + int(65 * scale))], fill=outline_col, width=line_w)

        # Yeşil Para Çantası (Big Dollar Sack)
        bag_x, bag_y = hand_l[0] - int(55 * scale), hand_l[1] - int(10 * scale)
        draw.ellipse([(bag_x, bag_y), (bag_x + int(100 * scale), bag_y + int(110 * scale))], fill=(22, 163, 74, 255), outline=(248, 250, 252, 255), width=line_w)
        draw.text((bag_x + int(36 * scale), bag_y + int(26 * scale)), "$", font=font_dolar, fill=(255, 255, 255, 255))

    elif "GENERAL" in role_u:
        # General Şapkası (Four-star peaked military cap)
        cap_w = int(head_r * 2.3)
        cap_h = int(65 * scale)
        cap_x0 = cx - cap_w // 2
        cap_y0 = head_y - head_r - int(30 * scale)
        draw.rectangle([(cap_x0, cap_y0), (cap_x0 + cap_w, cap_y0 + cap_h)], fill=(75, 85, 99, 255), outline=outline_col, width=line_w)
        # Altın Şapka Bandı & Yıldızlar
        draw.rectangle([(cap_x0, cap_y0 + cap_h - int(18 * scale)), (cap_x0 + cap_w, cap_y0 + cap_h)], fill=(234, 179, 8, 255))
        # Siperlik (Visor)
        draw.arc([(cap_x0 - int(10 * scale), cap_y0 + cap_h - int(20 * scale)), (cap_x0 + cap_w + int(10 * scale), cap_y0 + cap_h + int(30 * scale))], 0, 180, fill=(20, 20, 20), width=line_w + 3)

        # Gözler: Dehşet ve Panik (Göz bebekleri küçülmüş)
        draw.ellipse([(cx - int(48 * scale), head_y - int(32 * scale)), (cx - int(14 * scale), head_y + int(2 * scale))], fill=(255, 255, 255), outline=(20, 20, 20), width=3)
        draw.ellipse([(cx - int(33 * scale), head_y - int(17 * scale)), (cx - int(25 * scale), head_y - int(9 * scale))], fill=(20, 20, 20))

        draw.ellipse([(cx + int(14 * scale), head_y - int(32 * scale)), (cx + int(48 * scale), head_y + int(2 * scale))], fill=(255, 255, 255), outline=(20, 20, 20), width=3)
        draw.ellipse([(cx + int(27 * scale), head_y - int(17 * scale)), (cx + int(35 * scale), head_y - int(9 * scale))], fill=(20, 20, 20))

        # Bağıran Panik Ağzı (Büyük açık 'O' ağız)
        draw.ellipse([(cx - int(24 * scale), head_y + int(16 * scale)), (cx + int(24 * scale), head_y + int(56 * scale))], fill=(220, 38, 38), outline=(20, 20, 20), width=3)

        # Göğüste Madalyalar (Medal Ribbons)
        med_y = body_top + int(35 * scale)
        draw.rectangle([(cx - int(45 * scale), med_y), (cx - int(10 * scale), med_y + int(18 * scale))], fill=(59, 130, 246), outline=outline_col, width=1)
        draw.rectangle([(cx + int(10 * scale), med_y), (cx + int(45 * scale), med_y + int(18 * scale))], fill=(239, 68, 68), outline=outline_col, width=1)

        # Kollar: Kafasını İki Elinin Arasına Almış Panik Hali
        draw.line([(cx, body_top + int(50 * scale)), (cx - int(115 * scale), head_y + int(10 * scale))], fill=outline_col, width=line_w)
        draw.line([(cx - int(115 * scale), head_y + int(10 * scale)), (cx - head_r, head_y - int(15 * scale))], fill=outline_col, width=line_w)
        draw.line([(cx, body_top + int(50 * scale)), (cx + int(115 * scale), head_y + int(10 * scale))], fill=outline_col, width=line_w)
        draw.line([(cx + int(115 * scale), head_y + int(10 * scale)), (cx + head_r, head_y - int(15 * scale))], fill=outline_col, width=line_w)

    elif "PILOT" in role_u:
        # F-35 Gen III Karbon Kask
        helmet_r = int(head_r * 1.3)
        draw.ellipse([(cx - helmet_r, head_y - helmet_r), (cx + helmet_r, head_y + helmet_r)], fill=(30, 41, 59), outline=outline_col, width=line_w)
        # Zümrüt Yeşili HUD Vizör (Geniş Reflektif)
        draw.rounded_rectangle([(cx - int(65 * scale), head_y - int(25 * scale)), (cx + int(65 * scale), head_y + int(28 * scale))], radius=int(12 * scale), fill=(16, 185, 129), outline=(255, 255, 255), width=2)
        # Oksijen Hortumu
        draw.arc([(cx - int(30 * scale), head_y + int(25 * scale)), (cx + int(40 * scale), body_top + int(70 * scale))], 30, 180, fill=(148, 163, 184), width=int(8 * scale))

        # Terleme Damlaları (Büyük mavi panik damlası)
        sw_x, sw_y = cx + helmet_r + int(10 * scale), head_y - int(30 * scale)
        draw.polygon([(sw_x, sw_y), (sw_x - int(12 * scale), sw_y + int(24 * scale)), (sw_x + int(12 * scale), sw_y + int(24 * scale))], fill=(56, 189, 248))
        draw.ellipse([(sw_x - int(12 * scale), sw_y + int(12 * scale)), (sw_x + int(12 * scale), sw_y + int(36 * scale))], fill=(56, 189, 248))

        # Kollar: Titreyerek İki Eliyle Lövyeyi Tutan
        draw.line([(cx, body_top + int(45 * scale)), (cx - int(65 * scale), body_top + int(115 * scale))], fill=outline_col, width=line_w)
        draw.line([(cx, body_top + int(45 * scale)), (cx + int(65 * scale), body_top + int(115 * scale))], fill=outline_col, width=line_w)

    elif "SPY" in role_u:
        # Fötr Şapka
        draw.rectangle([(cx - int(110 * scale), head_y - head_r - int(12 * scale)), (cx + int(110 * scale), head_y - head_r + int(6 * scale))], fill=(15, 23, 42), outline=outline_col, width=2)
        draw.rectangle([(cx - int(70 * scale), head_y - head_r - int(55 * scale)), (cx + int(70 * scale), head_y - head_r - int(10 * scale))], fill=(30, 41, 59), outline=outline_col, width=2)

        # Dürbün (Binoculars Glowing Cyan)
        bino_y = head_y - int(10 * scale)
        draw.ellipse([(cx - int(60 * scale), bino_y), (cx - int(10 * scale), bino_y + int(45 * scale))], fill=(15, 23, 42), outline=(0, 220, 255), width=4)
        draw.ellipse([(cx + int(10 * scale), bino_y), (cx + int(60 * scale), bino_y + int(45 * scale))], fill=(15, 23, 42), outline=(0, 220, 255), width=4)
        draw.line([(cx - int(10 * scale), bino_y + int(22 * scale)), (cx + int(10 * scale), bino_y + int(22 * scale))], fill=(0, 220, 255), width=4)

        # Şaşkın / Ağzı Açık
        draw.ellipse([(cx - int(14 * scale), head_y + int(32 * scale)), (cx + int(14 * scale), head_y + int(52 * scale))], fill=(20, 20, 20), outline=outline_col, width=2)

        # Kollar: Dürbünü Gözüne Bastıran
        draw.line([(cx, body_top + int(50 * scale)), (cx - int(45 * scale), head_y + int(20 * scale))], fill=outline_col, width=line_w)
        draw.line([(cx, body_top + int(50 * scale)), (cx + int(45 * scale), head_y + int(20 * scale))], fill=outline_col, width=line_w)

    return img

    return img


# ═════════════════════════════════════════════════════════════════════════════
# 3. BLUEPRINT & ÇÖP ADAM TEKNİK VİTRİN ÜRETİCİSİ (1920x1080)
# ═════════════════════════════════════════════════════════════════════════════

def render_blueprint_spec_sheet(
    vehicle_name: str = "LOCKHEED MARTIN F-35 LIGHTNING II",
    nickname: str = "THE $1.7 TRILLION FLYING IPHONE",
    specs: Dict[str, str] = None,
    stickman_role: str = "DEFENSE_CEO",
    speech_text: str = "Don't look at the bill, General! Look at the stealth paint!",
    output_path: str = "/tmp/blueprint_spec.png"
) -> str:
    """
    Koyu Blueprint laciverti teknik çizim zemininde, sol tarafta uçağın teknik veri kartını,
    sağ tarafta ise esprili konuşma balonuyla reaksiyon veren çöp adamı içeren sahne üretir.
    """
    W, H = 1920, 1080
    # Koyu Blueprint Lacivert Zemin (#0a192f)
    img = Image.new("RGB", (W, H), (10, 25, 47))
    draw = ImageDraw.Draw(img)

    # 1. Blueprint Teknik Izgarası (Grid)
    grid_col = (20, 48, 85)
    for x in range(80, W - 80, 60):
        draw.line([(x, 60), (x, H - 60)], fill=grid_col, width=1)
    for y in range(60, H - 60, 60):
        draw.line([(80, y), (W - 80, y)], fill=grid_col, width=1)

    # Çerçeve
    draw.rectangle([(80, 60), (W - 80, H - 60)], outline=(0, 200, 255), width=2)
    draw.rectangle([(90, 70), (W - 90, H - 70)], outline=(0, 120, 180), width=1)

    # 2. Başlık Alanı
    font_title = get_font(42, "bold")
    font_sub = get_font(24, "mono")
    font_spec_label = get_font(20, "mono")
    font_spec_val = get_font(28, "bold")
    font_speech = get_font(22, "bold")

    draw.text((130, 100), vehicle_name.upper(), font=font_title, fill=(255, 255, 255))
    draw.text((130, 155), f"DESIGNATION: {nickname.upper()}", font=font_sub, fill=(0, 220, 255))

    # 3. Sol Taraf: Teknik Veri Kartları (Spec Cards)
    if not specs:
        specs = {
            "REFERENCE NOTE": "Add only values verified by the script's cited sources."
        }

    card_y = 220
    for label, val in specs.items():
        # Kutu
        draw.rectangle([(130, card_y), (850, card_y + 90)], fill=(15, 34, 64), outline=(0, 180, 230), width=1)
        draw.text((155, card_y + 14), label.upper(), font=font_spec_label, fill=(140, 180, 220))
        draw.text((155, card_y + 44), val, font=font_spec_val, fill=(255, 215, 0))
        card_y += 105

    # 4. Sağ Taraf: Çöp Adam Karakteri (Stickman Composite)
    scale = 1.35
    stickman = draw_stickman_character(role=stickman_role, scale=scale)
    char_w, char_h = stickman.size
    char_x = W - char_w - 40
    char_y = H - char_h - 70

    img_rgba = img.convert("RGBA")
    img_rgba.paste(stickman, (char_x, char_y), stickman)

    # 5. Konuşma Balonu (Speech Bubble)
    b_draw = ImageDraw.Draw(img_rgba)
    head_cx = char_x + (char_w // 2)
    head_cy = char_y + int(140 * scale)

    bub_w, bub_h = 540, 150
    bub_x = head_cx - bub_w - int(80 * scale)
    bub_y = max(180, head_cy - int(110 * scale))

    # Balon kutusu (Beyaz zemin, kalın koyu lacivert sınır)
    b_draw.rounded_rectangle([(bub_x, bub_y), (bub_x + bub_w, bub_y + bub_h)], radius=18, fill=(255, 255, 255, 250), outline=(15, 23, 42), width=3)
    
    # Balon kuyruğu (Çöp adamın ağzına doğru yönelen)
    tail_tip = (head_cx - int(70 * scale), head_cy + int(20 * scale))
    tail_base1 = (bub_x + bub_w - 15, bub_y + bub_h - 40)
    tail_base2 = (bub_x + bub_w - 5, bub_y + bub_h - 10)
    b_draw.polygon([tail_base1, tail_tip, tail_base2], fill=(255, 255, 255, 250))
    b_draw.line([tail_base1, tail_tip], fill=(15, 23, 42), width=3)
    b_draw.line([tail_tip, tail_base2], fill=(15, 23, 42), width=3)

    # Balon içi metni
    lines = []
    words = speech_text.split()
    cur = []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) > 32:
            lines.append(" ".join(cur))
            cur = []
    if cur:
        lines.append(" ".join(cur))

    for idx, l in enumerate(lines[:3]):
        b_draw.text((bub_x + 28, bub_y + 24 + idx * 32), l, font=font_speech, fill=(15, 23, 42))

    # Alt Bilgilendirme
    b_draw.text((130, H - 95), "TACTICAL SPECIFICATION AUDIT // CLASSIFIED MIL-STD 810H", font=font_sub, fill=(100, 145, 190))

    img_final = img_rgba.convert("RGB")
    img_final.save(output_path)
    return output_path


# ═════════════════════════════════════════════════════════════════════════════
# 4. YEREL TEST ÇALIŞTIRICISI
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_dir = Path("/tmp/crayon_combat_test")
    test_dir.mkdir(parents=True, exist_ok=True)

    f1 = render_blueprint_spec_sheet(
        vehicle_name="LOCKHEED MARTIN F-35 LIGHTNING II",
        nickname="THE $1.7 TRILLION FLYING IPHONE",
        stickman_role="DEFENSE_CEO",
        speech_text="Don't look at the $1.7T bill, General! The helmet has custom laser-mapping!",
        output_path=str(test_dir / "f35_ceo_blueprint.png")
    )

    f2 = render_blueprint_spec_sheet(
        vehicle_name="NORTHROP GRUMMAN B-2 SPIRIT",
        nickname="THE $2.1 BILLION STEALTH BAT",
        stickman_role="GENERAL",
        speech_text="WE ARE PAYING $150,000 PER HOUR JUST TO PARK IT IN AIR CONDITIONING?!",
        output_path=str(test_dir / "b2_general_blueprint.png")
    )

    print("✅ Crayon Combat Motoru başarıyla test edildi:")
    print(" - F-35 Blueprint (CEO):", f1)
    print(" - B-2 Blueprint (General):", f2)
