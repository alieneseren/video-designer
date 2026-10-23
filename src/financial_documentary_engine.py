"""
financial_documentary_engine.py
Crayon Capital / MagnatesMedia Tarzı Teknoloji & Finans Video Essay Motoru

Özellikler:
1. "Tech & Business Video Essay" senaryo promptları ve konu şablonları.
2. Dinamik Finansal Hareketli Grafik Üreticisi:
   - Hisse / Borsa Çöküş Grafiği (Stock Market Crash Graph - Neon Red Glowing Line & Stats)
   - Gazete Manşeti & SEC Belgesi Fosforlu Vurgu (Document Highlighter & Confidential Stamp)
   - Sermaye Harcaması & Kasa Erimesi Karşılaştırması (Capex vs Revenue Cash Burn Infographic)
3. Bağımsız, modüler ve mevcut sistemle %100 uyumlu.
"""

import os
import sys
import json
import time
import math
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

# Font yardımcıları (macOS ve Linux uyumlu)
def get_font(size: int, font_type: str = "sans") -> ImageFont.ImageFont:
    """Sistemde bulunan en kaliteli fontu seçer (Helvetica / SF Pro / DejaVu / Courier)."""
    candidates = []
    if font_type == "mono":
        candidates = [
            "/System/Library/Fonts/Courier.dfont",
            "/System/Library/Fonts/SFNSMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    elif font_type == "serif":
        candidates = [
            "/System/Library/Fonts/Times.ttc",
            "/System/Library/Fonts/NewYork.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
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
# 1. SENARYO ŞABLONLARI VE İÇERİK MİMARİSİ (PROMPTS)
# ═════════════════════════════════════════════════════════════════════════════

TECH_FINANCE_SYSTEM_PROMPT = """You are an elite Tech, Economics, and Business Investigative Documentary Scriptwriter (in the distinct style of Crayon Capital, MagnatesMedia, ColdFusion, and Moon).

Your mission is to produce cinematic, gripping, numbers-driven video essays about the high-stakes collisions of artificial intelligence, venture capital hype, corporate hubris, and catastrophic financial collapses.

STRICT TONE & PACING GUIDELINES:
- Cold, investigative, cynical realism mixed with suspenseful narrative momentum.
- Use numbers only when supported by cited filings or reputable reporting; include the source and date. Never invent or extrapolate a valuation, burn rate, insider sale, or percentage drop.
- Open with the most compelling verified paradox in the first 5-10 seconds, state the central question, and create one evidence-backed open loop that is resolved before the verdict.
- Change the visual beat every 4-6 seconds using short callouts, documents, comparisons, and animated diagrams rather than long text panels or a static chart.
- Keep the finished video to 6-8 minutes; shorten it when the available evidence cannot support that duration.
- Structure the documentary into 4-5 thematic CHAPTERS:
  1. THE HOOK: The multi-billion dollar paradox or the first domino falling.
  2. CHAPTER 1 (THE GOLD RUSH): Astronomical valuations, FOMO, blind venture capital pouring into hype.
  3. CHAPTER 2 (THE HIDDEN SINKHOLE): The unit economics math that doesn't add up (compute costs, electricity, lack of monetization).
  4. CHAPTER 3 (THE TIPPING POINT & CRASH): The insider panic, SEC filings, whistleblower revelations, and catastrophic stock collapse.
  5. CHAPTER 4 (THE CONTAGION): Who is left holding the bag, and what this signals for the wider tech ecosystem.

OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown codeblocks, no preamble:
{
  "title": "Documentary Title (Punchy, curiosity-inducing, e.g. 'The First Big Victim of the AI Bubble')",
  "description": "Engaging 2-paragraph YouTube description with hashtags (#Tech #Economics #Finance #AI)",
  "keywords": ["ai bubble", "venture capital", "silicon valley", "nvidia", "tech crash"],
  "tags": ["AI", "Finance", "TechDocumentary", "Economics", "StockMarket", "SiliconValley"],
  "company_focus": "Name of the primary company or sector analyzed (e.g. 'CoreWeave', 'Inflection AI', 'Stability AI')",
  "ticker_symbol": "Stock ticker if public or estimated identifier (e.g. 'NVDA', 'INTC', 'AI_INDEX')",
  "financial_stats": {
    "peak_valuation": null,
    "current_valuation": null,
    "total_wipeout_pct": null,
    "capex_burn_annual": null
  },
  "sources": [{"name": "Source organization or publication", "url": "https://example.org/source", "date": "YYYY-MM-DD"}],
  "fact_check_notes": ["Separate verified facts, estimates, and claims omitted for lack of evidence."],
  "scenes": [
    {
      "scene_id": 1,
      "chapter": "THE HOOK",
      "narration": "Documentary script narration for this scene in the requested language. Serious, analytical, engaging, and evidence-backed.",
      "audio_cue": "impact",
      "visual_type": "stock_crash_chart",
      "visual_prompt": "Cinematic dark-mode stock crash chart showing 86% plunge, red glowing line, glowing stats on dark slate grid, 8k resolution",
      "emotion": "dramatic"
    }
  ]
}
"""

CURATED_TECH_FINANCE_TOPICS = [
    {
        "id": "ai_bubble_victim_1",
        "title": "The First Big Victim of the AI Bubble: How an $80B Empire Ran Out of Cash",
        "focus": "Stability AI & Generative Compute Startups",
        "ticker": "AI_CRASH",
        "stats": {"peak": "$85B", "current": "$9B", "loss": "-89%", "burn": "$12B"}
    },
    {
        "id": "asml_secret_monopoly",
        "title": "The Dutch Monopoly Nobody Talks About: Why ASML Controls the World Economy",
        "focus": "ASML & Semiconductor Lithography",
        "ticker": "ASML",
        "stats": {"peak": "$420B", "current": "$280B", "loss": "-33%", "burn": "$5B"}
    },
    {
        "id": "nvidia_trillion_mirage",
        "title": "Why Wall Street Secretly Fears Nvidia's 3-Trillion Dollar Valuation",
        "focus": "Nvidia GPU Capex Circular Revenue Loop",
        "ticker": "NVDA",
        "stats": {"peak": "$3.4T", "current": "$2.8T", "loss": "-18%", "burn": "$40B"}
    },
    {
        "id": "intel_fall_from_grace",
        "title": "The 50-Year Tech Empire in Ruin: How Intel Lost Everything",
        "focus": "Intel Corporation Foundry Collapse",
        "ticker": "INTC",
        "stats": {"peak": "$290B", "current": "$85B", "loss": "-71%", "burn": "$16B"}
    },
    {
        "id": "ai_energy_blackout",
        "title": "The Nuclear Secret: Why AI Data Centers Are Running Out of Electricity",
        "focus": "Big Tech Nuclear & Power Grid Scramble",
        "ticker": "PWR_GRID",
        "stats": {"peak": "100 GW Demand", "current": "22 GW Available", "loss": "Deficit: 78 GW", "burn": "$60B"}
    }
]


# ═════════════════════════════════════════════════════════════════════════════
# 2. HAREKETLİ FİNANSAL GRAFİK & DOKÜMAN MOTORU (RENDERERS)
# ═════════════════════════════════════════════════════════════════════════════

def render_stock_crash_chart(
    title: str = "GLOBAL TECH CAPITAL // MARKET CAP PLUNGE",
    ticker: str = "AI_INDEX",
    start_price: float = 240.0,
    end_price: float = 38.0,
    loss_pct: str = "-84.2%",
    loss_dollars: str = "-$128.5 BILLION",
    output_path: str = "/tmp/stock_crash_chart.png"
) -> str:
    """
    Crayon Capital / Bloomberg Terminal tarzı şık, koyu antrasit renk paletinde
    kırmızı parlak düşüş eğrisi ve dev metrik rozetleri içeren borsa grafiği üretir.
    """
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (10, 14, 22)) # Deep Charcoal Slate
    draw = ImageDraw.Draw(img)

    # 1. Izgara Çizgileri (Subtle Grid)
    grid_col = (20, 28, 42)
    for x in range(120, W - 120, 120):
        draw.line([(x, 180), (x, H - 160)], fill=grid_col, width=1)
    for y in range(180, H - 160, 90):
        draw.line([(120, y), (W - 120, y)], fill=grid_col, width=1)

    # 2. Üst Terminal Başlığı (Top Header Bar)
    draw.rectangle([(120, 80), (W - 120, 150)], fill=(15, 21, 33), outline=(35, 48, 70), width=1)
    font_mono_sm = get_font(18, "mono")
    font_bold_md = get_font(26, "bold")
    font_bold_lg = get_font(42, "bold")
    font_mono_lg = get_font(34, "mono")

    draw.text((150, 102), f"TICKER: {ticker.upper()}", font=font_mono_sm, fill=(0, 220, 255))
    draw.text((360, 98), title.upper(), font=font_bold_md, fill=(240, 245, 255))
    draw.text((W - 380, 102), "TIMEFRAME: 24 MONTH CYCLE", font=font_mono_sm, fill=(140, 155, 175))

    # 3. Gerçekçi Çöküş Eğrisi Noktalarını Hesapla (Realistic Plunge Points)
    chart_x0 = 160
    chart_x1 = W - 160
    chart_y_top = 240
    chart_y_bottom = H - 220
    plot_width = chart_x1 - chart_x0
    plot_height = chart_y_bottom - chart_y_top

    # 80 adımlı eğri (Hype zirvesi -> Plunge)
    random.seed(42) # Tutarlı estetik
    curve_points = []
    num_steps = 70

    for i in range(num_steps):
        t = i / (num_steps - 1)
        px = chart_x0 + (t * plot_width)

        # Matematiksel Hype & Crash profili
        if t < 0.25:
            # Erken yükseliş (Euphoria)
            norm_val = 0.65 + (t / 0.25) * 0.35 + random.uniform(-0.03, 0.03)
        elif t < 0.40:
            # Zirvede yatay dalgalanma (Peak plateau)
            norm_val = 0.98 + random.uniform(-0.04, 0.02)
        elif t < 0.65:
            # İlk kırılma ve sert düşüş (Freefall)
            fall_ratio = (t - 0.40) / 0.25
            norm_val = 0.98 - (fall_ratio ** 1.3) * 0.70 + random.uniform(-0.02, 0.02)
        else:
            # Dipte sürünme ve iflas (Bottom washout)
            norm_val = 0.28 - ((t - 0.65) / 0.35) * 0.20 + random.uniform(-0.015, 0.015)

        norm_val = max(0.05, min(1.0, norm_val))
        py = chart_y_bottom - (norm_val * plot_height)
        curve_points.append((px, py))

    # 4. Kırmızı Gradient Dolgu (Translucent Fill beneath curve)
    fill_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fill_draw = ImageDraw.Draw(fill_overlay)
    poly_points = [(chart_x0, chart_y_bottom)] + curve_points + [(chart_x1, chart_y_bottom)]
    fill_draw.polygon(poly_points, fill=(244, 63, 94, 35))
    img = Image.alpha_composite(img.convert("RGBA"), fill_overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 5. Parlak Kırmızı Çizgi (Glowing Crash Line)
    line_col = (255, 60, 85)
    for i in range(len(curve_points) - 1):
        pt1 = curve_points[i]
        pt2 = curve_points[i + 1]
        draw.line([pt1, pt2], fill=line_col, width=4)

    # Zirve Noktası (Peak Marker)
    peak_pt = max(curve_points[:30], key=lambda pt: -pt[1])
    draw.ellipse([(peak_pt[0] - 8, peak_pt[1] - 8), (peak_pt[0] + 8, peak_pt[1] + 8)], fill=(0, 220, 255), outline=(255, 255, 255), width=2)
    draw.text((peak_pt[0] - 60, peak_pt[1] - 38), f"${start_price:.0f} (PEAK)", font=font_mono_sm, fill=(0, 220, 255))

    # Dip Çöküş Noktası (Crash Bottom Marker)
    bottom_pt = curve_points[-1]
    draw.ellipse([(bottom_pt[0] - 9, bottom_pt[1] - 9), (bottom_pt[0] + 9, bottom_pt[1] + 9)], fill=(255, 60, 85), outline=(255, 255, 255), width=2)
    draw.text((bottom_pt[0] - 110, bottom_pt[1] + 18), f"${end_price:.0f} (COLLAPSE)", font=font_mono_sm, fill=(255, 80, 100))

    # 6. Büyük İstatistik Rozetleri (Overlay Impact Cards)
    # Sol Alt Kart: Yüzdelik Çöküş
    card1_x0, card1_y0 = 150, H - 380
    draw.rectangle([(card1_x0, card1_y0), (card1_x0 + 380, card1_y0 + 150)], fill=(16, 20, 30), outline=(244, 63, 94), width=2)
    draw.text((card1_x0 + 24, card1_y0 + 20), "TOTAL VALUE DESTRUCTION", font=font_mono_sm, fill=(160, 175, 195))
    draw.text((card1_x0 + 24, card1_y0 + 55), loss_pct, font=font_bold_lg, fill=(255, 60, 85))
    draw.text((card1_x0 + 24, card1_y0 + 115), "VALUATION COMPRESSION", font=font_mono_sm, fill=(244, 63, 94))

    # Sağ Üst Kart: Silinen Piyasa Değeri
    card2_x0, card2_y0 = W - 560, 210
    draw.rectangle([(card2_x0, card2_y0), (card2_x0 + 400, card2_y0 + 140)], fill=(16, 20, 30), outline=(255, 200, 0), width=2)
    draw.text((card2_x0 + 24, card2_y0 + 20), "CAPITAL WIPEOUT ESTIMATE", font=font_mono_sm, fill=(160, 175, 195))
    draw.text((card2_x0 + 24, card2_y0 + 55), loss_dollars, font=font_mono_lg, fill=(255, 215, 0))

    # 7. Alt Hacim Barları (Volume Breakdown Bars)
    for idx, (px, py) in enumerate(curve_points[::2]):
        v_height = random.randint(15, 65) if idx < 15 else random.randint(40, 110)
        v_col = (244, 63, 94, 180) if idx >= 15 else (0, 180, 220, 140)
        draw.rectangle([(px - 4, H - 150 - v_height), (px + 4, H - 150)], fill=v_col)

    # Alt Zaman Ekseni (Timeline Axis)
    draw.line([(120, H - 150), (W - 120, H - 150)], fill=(60, 75, 100), width=2)
    quarters = ["Q1 2024 (HYPE)", "Q3 2024", "Q1 2025 (CRACKS)", "Q3 2025", "Q4 2026 (CRASH)"]
    for q_idx, q_label in enumerate(quarters):
        qx = 160 + q_idx * ((W - 320) // (len(quarters) - 1))
        draw.text((qx - 40, H - 135), q_label, font=font_mono_sm, fill=(140, 155, 175))

    img.save(output_path)
    return output_path


def render_headline_highlighter_document(
    source_name: str = "FINANCIAL TIMES // INVESTIGATIVE REPORT",
    date_str: str = "OCTOBER 14, 2026",
    headline: str = "INTERNAL AUDIT EXPOSES 85% REVENUE HOLE IN TOP AI UNICORN",
    subheadline: str = "Confidential filings reveal venture-backed compute startup burned $1.8B with under $60M annualized revenue.",
    highlight_text: str = "burned $1.8B with under $60M annualized revenue",
    stamp_text: str = "CONFIDENTIAL // LEAKED",
    output_path: str = "/tmp/financial_document.png"
) -> str:
    """
    Belgesel tarzı resmi sızıntı belge, Financial Times manşeti ve
    animasyonlu fosforlu kalemle (neon highlighter) çizilmiş metin sahnesi üretir.
    """
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (14, 16, 22))
    draw = ImageDraw.Draw(img)

    # 1. Doküman Kartı (Center Paper Document Effect)
    doc_w, doc_h = 1400, 800
    doc_x0 = (W - doc_w) // 2
    doc_y0 = (H - doc_h) // 2

    # Hafif gölge ve belge zemini
    draw.rectangle([(doc_x0 + 8, doc_y0 + 8), (doc_x0 + doc_w + 8, doc_y0 + doc_h + 8)], fill=(5, 7, 10))
    draw.rectangle([(doc_x0, doc_y0), (doc_x0 + doc_w, doc_y0 + doc_h)], fill=(245, 244, 238), outline=(200, 195, 185), width=2)

    # 2. Belge Üst Bilgisi (Newspaper Masthead / SEC Header)
    font_serif_lg = get_font(42, "serif")
    font_serif_md = get_font(26, "serif")
    font_mono_sm = get_font(18, "mono")
    font_bold_title = get_font(38, "bold")
    font_stamp = get_font(36, "bold")

    # Gazete başlığı
    draw.line([(doc_x0 + 60, doc_y0 + 50), (doc_x0 + doc_w - 60, doc_y0 + 50)], fill=(40, 40, 40), width=3)
    draw.text((doc_x0 + 70, doc_y0 + 60), source_name.upper(), font=font_serif_lg, fill=(20, 20, 20))
    draw.text((doc_x0 + doc_w - 280, doc_y0 + 75), date_str, font=font_mono_sm, fill=(80, 80, 80))
    draw.line([(doc_x0 + 60, doc_y0 + 120), (doc_x0 + doc_w - 60, doc_y0 + 120)], fill=(40, 40, 40), width=1)

    # 3. Ana Manşet (Headline)
    draw.text((doc_x0 + 70, doc_y0 + 160), headline, font=font_bold_title, fill=(15, 23, 42))

    # 4. Alt Açıklama ve Fosforlu Vurgu (Subheadline with Neon Yellow Highlighter)
    sub_y = doc_y0 + 260
    draw.text((doc_x0 + 70, sub_y), subheadline, font=font_serif_md, fill=(50, 55, 65))

    # Fosforlu kalem vurgusu (Neon Yellow/Green Highlighter)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    # Vurgu kutusu koordinatları
    hl_box = [(doc_x0 + 60, sub_y - 6), (doc_x0 + 880, sub_y + 38)]
    ov_draw.rectangle(hl_box, fill=(255, 240, 0, 130)) # Fluorescent Yellow Overlay
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 5. Doküman Gövdesi (Simulated Article Columns)
    col_y = doc_y0 + 340
    col_w = (doc_w - 180) // 2
    try:
        font_body = get_font(18, "serif")
    except Exception:
        font_body = ImageFont.load_default()

    sample_col1 = [
        "According to forensic balance sheet reviews obtained by reporters,",
        "the company’s compute commitments exceeded total cash reserves by",
        "a factor of four. The circular reliance on vendor credits allowed",
        "unprecedented capital expenditure while real enterprise revenue",
        "stagnated below sustainable unit economic margins.",
        "",
        "\"The entire valuation model was predicated on infinite zero-cost",
        "liquidity,\" noted one former senior director of enterprise sales.",
        "\"When compute depreciation hit the P&L, there was no customer base",
        "willing to pay cost-recovery pricing for automated inference.\""
    ]

    sample_col2 = [
        "Major venture backers quietly began hedging their exposure through",
        "secondary market discounts of up to 75% as early as Q2 2025.",
        "Internal email archives reveal frantic negotiations with Tier-1",
        "cloud providers attempting to offload non-cancellable GPU leases.",
        "",
        "With insolvency filings imminent, industry analysts warn of a",
        "domino contagion across third-party data center operators who",
        "leveraged billions in asset-backed debt against now-stranded hardware."
    ]

    for idx, line in enumerate(sample_col1):
        draw.text((doc_x0 + 70, col_y + idx * 26), line, font=font_body, fill=(35, 40, 50))

    for idx, line in enumerate(sample_col2):
        draw.text((doc_x0 + 70 + col_w + 40, col_y + idx * 26), line, font=font_body, fill=(35, 40, 50))

    # 6. Kırmızı Resmi Kaşe (Red Rubber Stamp: CONFIDENTIAL / LEAKED)
    stamp_img = Image.new("RGBA", (450, 120), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(stamp_img)
    s_draw.rectangle([(10, 10), (430, 105)], outline=(220, 30, 40, 220), width=6)
    s_draw.rectangle([(16, 16), (424, 99)], outline=(220, 30, 40, 140), width=2)
    s_draw.text((36, 32), stamp_text, font=font_stamp, fill=(220, 30, 40, 240))

    # Kaşeyi 14 derece eğ
    rotated_stamp = stamp_img.rotate(14, expand=True, resample=Image.BICUBIC)
    img_rgba = img.convert("RGBA")
    img_rgba.paste(rotated_stamp, (doc_x0 + doc_w - 480, doc_y0 + 200), rotated_stamp)

    img = img_rgba.convert("RGB")
    img.save(output_path)
    return output_path


def render_capex_burn_infographic(
    company_name: str = "HYPERSCALE AI LABS",
    capex_amount_str: str = "$52.4 BILLION",
    revenue_amount_str: str = "$3.1 BILLION",
    ratio_str: str = "17x DEFICIT SPREAD",
    output_path: str = "/tmp/capex_burn.png"
) -> str:
    """
    Yapay Zeka ekonomisindeki en büyük çelişkiyi (Devasa Altyapı Harcaması vs Yetersiz Gelir)
    gösteren yüksek etkili karşılaştırma infografiği üretir.
    """
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (10, 13, 20))
    draw = ImageDraw.Draw(img)

    font_title = get_font(36, "bold")
    font_sub = get_font(20, "mono")
    font_big_num = get_font(52, "bold")
    font_label = get_font(24, "bold")

    # Üst Başlık
    draw.text((120, 90), "CAPITAL ALLOCATION DISCONNECT // THE AI CASH SINKHOLE", font=font_title, fill=(245, 248, 255))
    draw.text((120, 145), f"COMPANY/SECTOR AUDIT: {company_name.upper()}   |   ANNUALIZED HARDWARE RUN-RATE", font=font_sub, fill=(0, 220, 255))

    # 1. Sol Sütun (CAPEX / GPU Infrastructure Spend) - Dev Kırmızı Sütun
    col1_x = 240
    col1_y_base = H - 240
    col1_h = 480
    draw.rectangle([(col1_x, col1_y_base - col1_h), (col1_x + 360, col1_y_base)], fill=(244, 63, 94), outline=(255, 120, 140), width=2)
    draw.text((col1_x + 20, col1_y_base - col1_h - 60), "GPU & DATA CENTER CAPEX", font=font_label, fill=(255, 100, 120))
    draw.text((col1_x + 20, col1_y_base - col1_h + 30), capex_amount_str, font=font_big_num, fill=(255, 255, 255))
    draw.text((col1_x + 20, col1_y_base - col1_h + 100), "CASH OUTFLOW (EQUIPMENT & POWER)", font=font_sub, fill=(255, 220, 230))

    # 2. Sağ Sütun (REAL ENTERPRISE REVENUE) - Ufak Yeşil Sütun
    col2_x = 800
    col2_h = 80 # Capex'in neredeyse onda biri
    draw.rectangle([(col2_x, col1_y_base - col2_h), (col2_x + 360, col1_y_base)], fill=(16, 185, 129), outline=(52, 211, 153), width=2)
    draw.text((col2_x + 20, col1_y_base - col2_h - 50), "ACTUAL MONETIZED REVENUE", font=font_label, fill=(52, 211, 153))
    draw.text((col2_x + 20, col1_y_base - col2_h + 15), revenue_amount_str, font=font_title, fill=(255, 255, 255))

    # 3. Sağ Taraf: Uçurum Oranı Kartı (Deficit Spread Badge)
    card_x = 1300
    card_y = 300
    draw.rectangle([(card_x, card_y), (card_x + 480, card_y + 280)], fill=(18, 23, 35), outline=(255, 200, 0), width=3)
    draw.text((card_x + 30, card_y + 35), "UNSUSTAINABLE MULTIPLE", font=font_sub, fill=(255, 215, 0))
    draw.text((card_x + 30, card_y + 80), ratio_str, font=font_big_num, fill=(255, 215, 0))
    draw.text((card_x + 30, card_y + 160), "Every $1 in customer revenue", font=font_label, fill=(220, 225, 235))
    draw.text((card_x + 30, card_y + 195), "requires $17 in capital expenditure.", font=font_label, fill=(244, 63, 94))

    # Alt Çizgi
    draw.line([(120, col1_y_base), (W - 120, col1_y_base)], fill=(60, 75, 100), width=3)
    draw.text((120, col1_y_base + 30), "SOURCE: VENTURE CAPITAL SEC FILINGS & HISTORICAL TECH RUN-RATE MODELS", font=font_sub, fill=(130, 145, 165))

    img.save(output_path)
    return output_path


# ═════════════════════════════════════════════════════════════════════════════
# 3. YEREL TEST ÇALIŞTIRICISI
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    out_dir = Path("/tmp/financial_engine_test")
    out_dir.mkdir(parents=True, exist_ok=True)

    f1 = render_stock_crash_chart(output_path=str(out_dir / "stock_crash.png"))
    f2 = render_headline_highlighter_document(output_path=str(out_dir / "document_headline.png"))
    f3 = render_capex_burn_infographic(output_path=str(out_dir / "capex_burn.png"))

    print("✅ Financial Documentary Engine testleri başarıyla üretildi:")
    print(" - Stock Crash Chart:", f1)
    print(" - Document Headline:", f2)
    print(" - Capex vs Revenue:", f3)
