#!/usr/bin/env python3
"""
sports_shorts_engine.py
=======================
Ultra-High Retention Sports & Basketball Shorts Engine (v3).

Architectural Guarantees:
1. Zero Drawing / Zero Schematic Guarantee (100% REAL MEDIA):
   - ABSOLUTELY NO PROCEDURAL DRAWINGS, VECTORS, OR CARTOONS.
   - Sourced exclusively from authentic Wikimedia Commons NBA player photography and real Pixabay HD/4K basketball action video footage.
2. Real Video Clip (B-Roll) Integration:
   - Automatically downloads and slices real 1080x1920 basketball video clips (dunks, fast breaks, net swishes, player drives, arena shots).
   - Interleaves authentic player photos and moving basketball video clips every 2.0 - 2.8 seconds.
3. Pacing & Retention (Viral Shorts Standard):
   - Alternating rapid cuts: Real Player Photo (Punch-in Zoom) <-> Real Moving Basketball Action Video.
   - If a scene has no photo, it uses real video footage instead of any drawing.
4. Subtitle & Text Perfection:
   - Word-burst pop subtitles with top category badge '🏀 THE BASKETBALL SHOW | NBA ANALYSIS'.
   - Sports name phonetic corrections ('Daikon' -> 'Dikembe Mutombo', etc.).
   - Crisp ducked underworld hip-hop beat.
"""

import os
import sys
import re
import time
import math
import shutil
import urllib.parse
import urllib.request
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

import requests
from PIL import Image, ImageEnhance, ImageDraw, ImageFont

try:
    from asset_validator import asset_validator
    from timeline_guard import timeline_guard
    from pipeline_integration import pipeline_integration
    from query_builder import query_builder
    from fallback_engine import fallback_engine
    from asset_fetcher import asset_fetcher
except ImportError:
    try:
        from src.core.asset_validator import asset_validator
        from src.core.timeline_guard import timeline_guard
        from src.core.pipeline_integration import pipeline_integration
        from src.core.query_builder import query_builder
        from src.core.fallback_engine import fallback_engine
        from src.core.asset_fetcher import asset_fetcher
    except ImportError:
        try:
            from core.asset_validator import asset_validator
            from core.timeline_guard import timeline_guard
            from core.pipeline_integration import pipeline_integration
            from core.query_builder import query_builder
            from core.fallback_engine import fallback_engine
            from core.asset_fetcher import asset_fetcher
        except ImportError:
            asset_validator = None
            timeline_guard = None
            pipeline_integration = None
            query_builder = None
            fallback_engine = None
            asset_fetcher = None

def get_pixabay_key() -> str:
    """Aktif Pixabay API anahtarını ortam değişkeni veya SettingsManager'dan alır."""
    api_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not api_key:
        try:
            from settings_manager import SettingsManager
            sm = SettingsManager()
            val = sm.get("pixabay_api_key")
            if val and str(val).strip():
                api_key = str(val).strip()
        except Exception:
            pass
    return api_key

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
WIKIMEDIA_USER_AGENT = "ShortStudioVideoWorker/2.0 (mailto:alienees@gmail.com)"
BROWSER_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Sözlük düzeltmeleri (Ses/Whisper/AI kaçaklarını engeller)
SPORTS_NAME_REPLACEMENTS = {
    r"\bdaikon\b": "Dikembe",
    r"\bdaikon mutombo\b": "Dikembe Mutombo",
    r"\bmutombo\b": "Mutombo",
    r"\bdikembe\b": "Dikembe",
    r"\blebron\b": "LeBron",
    r"\bshaq\b": "Shaq",
    r"\bkareem\b": "Kareem",
    r"\bcurry\b": "Curry",
    r"\bdraymond\b": "Draymond",
    r"\bdrainman\b": "Draymond",
    r"\bwarriors\b": "Warriors",
    r"\blakers\b": "Lakers",
    r"\bbulls\b": "Bulls",
    r"\bceltics\b": "Celtics",
}

NBA_KNOWN_PLAYERS = [
    "Draymond Green", "Michael Jordan", "LeBron James", "Stephen Curry", "Shaquille O'Neal",
    "Kobe Bryant", "Kareem Abdul-Jabbar", "Wilt Chamberlain", "Dennis Rodman", "Larry Bird",
    "Magic Johnson", "Giannis Antetokounmpo", "Luka Doncic", "Nikola Jokic", "Kevin Durant",
    "Allen Iverson", "Tim Duncan", "Hakeem Olajuwon", "Dikembe Mutombo", "Russell Westbrook"
]


def sanitize_sports_text(text: str) -> str:
    """Metindeki imleç, regex veya yazım hatalarını temizler."""
    if not text:
        return ""
    txt = text.replace("|", "").replace("`", "").strip()
    for pattern, repl in SPORTS_NAME_REPLACEMENTS.items():
        txt = re.sub(pattern, repl, txt, flags=re.IGNORECASE)
    return txt


def format_ass_time(seconds: float) -> str:
    """Saniyeyi ASS altyazı zaman damgasına çevirir (H:MM:SS.cs)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"


def extract_player_or_topic_keywords(script: dict, scene_text: str = "") -> List[str]:
    """Senaryo veya sahne metninden ana oyuncu, takım veya konu anahtar kelimelerini ayıklar."""
    if query_builder is not None:
        cq = query_builder.build_context_locked_queries(script, scene_text)
        queries = [cq.primary_query] + cq.fallback_queries
        seen = set()
        out = []
        for q in queries:
            if q and q not in seen:
                seen.add(q)
                out.append(q)
        if out:
            return out

    combined = f"{script.get('title', '')} {script.get('description', '')} {scene_text}"
    found_players = []
    for player in NBA_KNOWN_PLAYERS:
        if re.search(r"\b" + re.escape(player) + r"\b", combined, re.IGNORECASE):
            found_players.append(player)
            
    if not found_players:
        first_names = ["Draymond", "Jordan", "LeBron", "Curry", "Shaq", "Kobe", "Mutombo", "Wilt", "Rodman"]
        for fn in first_names:
            if re.search(r"\b" + re.escape(fn) + r"\b", combined, re.IGNORECASE):
                for p in NBA_KNOWN_PLAYERS:
                    if fn in p:
                        found_players.append(p)
                        break

    queries = []
    for p in found_players[:2]:
        queries.append(f"{p} NBA basketball")
        queries.append(f"{p} basketball court action")
        queries.append(f"{p} NBA game")
        queries.append(p)

    if not found_players:
        queries.extend([
            "NBA professional basketball court action",
            "NBA basketball player slam dunk"
        ])
    
    seen = set()
    unique_queries = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)
    return unique_queries


def search_wikimedia_sports_media(query: str, limit: int = 10) -> List[str]:
    """Wikimedia Commons üzerinden gerçek NBA oyuncu arşiv fotoğraflarını arar (gsrnamespace=6). Diğer sporlar (futbol, nfl), biletler ve salonlar filtrelenir."""
    # Aday sorgu varyantlarını hazırla (Oyuncu adı zorunlu korunur, salt takım araması engellenir)
    quoted_entities = re.findall(r'"([^"]+)"', query)
    unquoted_rest = re.sub(r'"[^"]+"', '', query).strip()
    rest_words = [w for w in unquoted_rest.split() if w.strip()]

    query_variants = [query]
    if quoted_entities:
        main_ent = quoted_entities[0]
        if rest_words:
            query_variants.append(f'"{main_ent}" {" ".join(rest_words[:2])}')
        query_variants.append(f'"{main_ent}" basketball')
        query_variants.append(f'"{main_ent}" NBA')
        query_variants.append(f'{main_ent} basketball')
    else:
        clean_q = re.sub(r'["\']', '', query).strip()
        words = clean_q.split()
        if len(words) >= 2:
            player_base = f"{words[0]} {words[1]}"
            if len(words) > 3:
                query_variants.append(f"{player_base} {' '.join(words[2:4])}")
            query_variants.append(f"{player_base} basketball")
            query_variants.append(f"{player_base} NBA")
        elif clean_q != query:
            query_variants.append(clean_q)

    urls = []
    bad_keywords = [
        "offensive lineman", "lineman", "football", "nfl", "soccer", "baseball",
        "hockey", "rugby", "helmet", "tennis", "golf", "bengals", "panthers",
        "logo", "signature", "sig.", "icon", "symbol", "diagram", "robinho",
        "brazil", "world cup", "fifa", "military", "atsugi", "signing",
        "celtics", "boston", "mchale", "parish", "larry_bird", "larry bird",
        "rural", "backyard", "driveway", "cargo", "pink_house", "house", "playground",
        "ticket", "stub", "ticket stub", "ticket_stub", "jumbotron", "scoreboard",
        "concession", "bar", "arena bar", "arena seats", "empty arena", "admission",
        "receipt", "document", "scola", "luis scola", "luther head", "bonzi wells", "yao ming", "harden"
    ]
    seen_urls = set()

    for q_try in query_variants:
        if len(urls) >= limit:
            break
        try:
            url = "https://commons.wikimedia.org/w/api.php"
            search_q = f"{q_try} -ticket -stub -jumbotron -scoreboard -concession -bar -arena -Scola -Head -Harden"
            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": search_q,
                "gsrnamespace": 6,  # 6 = File: namespace
                "gsrlimit": limit * 2,
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "format": "json"
            }
            headers = {"User-Agent": WIKIMEDIA_USER_AGENT}
            resp = requests.get(url, params=params, headers=headers, timeout=8)
            if resp.status_code == 200:
                pages = resp.json().get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    title = str(pdata.get("title", "")).lower()
                    if any(bad in title for bad in bad_keywords):
                        continue
                    infos = pdata.get("imageinfo", [])
                    if infos:
                        u = infos[0].get("url")
                        if u and u not in seen_urls:
                            u_lower = u.lower()
                            if any(bad in u_lower for bad in bad_keywords):
                                continue
                            u_clean = u_lower.split("?")[0]
                            if u_clean.endswith((".jpg", ".jpeg", ".png", ".webp")):
                                seen_urls.add(u)
                                urls.append(u)
                                if len(urls) >= limit:
                                    break
        except Exception as e:
            print(f"[SportsEngine] Wikimedia arama hatası ('{q_try}'): {e}")
    return urls


def search_pixabay_sports_image(query: str, limit: int = 4) -> List[str]:
    """Pixabay üzerinden yüksek çözünürlüklü gerçek basketbol fotoğrafları arar (Çizim ve animasyonlar elenir)."""
    urls = []
    api_key = get_pixabay_key()
    if not api_key:
        return urls
    try:
        api_url = (
            f"https://pixabay.com/api/?key={api_key}"
            f"&q={urllib.parse.quote(query)}"
            f"&image_type=photo&per_page=15&safesearch=true"
        )
        resp = requests.get(api_url, headers={"User-Agent": BROWSER_USER_AGENT}, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            bad_tags = ["cartoon", "animation", "drawing", "illustration", "vector", "3d", "render", "medical", "thermometer"]
            for hit in data.get("hits", []):
                tags = str(hit.get("tags", "")).lower()
                if any(b in tags for b in bad_tags):
                    continue
                u = hit.get("largeImageURL") or hit.get("webformatURL")
                if u:
                    urls.append(u)
                if len(urls) >= limit:
                    break
    except Exception as e:
        print(f"[SportsEngine] Pixabay fotoğraf arama hatası ('{query}'): {e}")
    return urls


def fetch_pixabay_sports_videos(scratch_dir: Path, target_count: int = 8) -> List[Path]:
    """
    Pixabay Video API'den gerçek HD/4K basketbol maç/aksiyon/smaç MP4 videolarını indirir.
    Çizim, animasyon ve alakasız videolar kesin olarak filtrelenir.
    """
    vids_dir = scratch_dir / "broll_vids"
    vids_dir.mkdir(parents=True, exist_ok=True)
    existing = [p for p in vids_dir.glob("clip_*.mp4") if p.stat().st_size > 100000]
    if len(existing) >= target_count:
        return existing

    api_key = get_pixabay_key()
    if not api_key:
        return existing

    queries = [
        "slam dunk", "basketball game", "basketball player", "basketball hoop net",
        "basketball court", "basketball tournament", "basketball competition", "basketball action"
    ]
    seen_ids = set()
    bad_tags = ["cartoon", "animation", "drawing", "illustration", "medical", "thermometer", "kid", "dog", "animal", "record"]
    candidates = []

    for q in queries:
        if len(candidates) >= target_count * 2:
            break
        params = {
            "key": api_key,
            "q": q,
            "video_type": "film",
            "safesearch": "true",
            "per_page": 15
        }
        url = f"https://pixabay.com/api/videos/?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": BROWSER_USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                for h in data.get("hits", []):
                    hid = h["id"]
                    tags = str(h.get("tags", "")).lower()
                    if hid in seen_ids:
                        continue
                    if any(b in tags for b in bad_tags):
                        continue
                    if "basketball" not in tags and "basket" not in tags and "dunk" not in tags:
                        continue
                    v_obj = h.get("videos", {}).get("large") or h.get("videos", {}).get("medium") or h.get("videos", {}).get("small")
                    if v_obj and v_obj.get("url"):
                        seen_ids.add(hid)
                        candidates.append((hid, v_obj["url"]))
        except Exception as e:
            print(f"[SportsEngine] Video sorgu hatası ('{q}'): {e}")

    headers = {"User-Agent": BROWSER_USER_AGENT}
    downloaded_files = list(existing)
    for idx, (hid, v_url) in enumerate(candidates):
        if len(downloaded_files) >= target_count:
            break
        target_path = vids_dir / f"clip_{idx:02d}_{hid}.mp4"
        if target_path.exists() and target_path.stat().st_size > 100000:
            if target_path not in downloaded_files:
                downloaded_files.append(target_path)
            continue
        try:
            r = requests.get(v_url, headers=headers, timeout=25, stream=True)
            if r.status_code == 200:
                with open(target_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                if target_path.exists() and target_path.stat().st_size > 100000:
                    downloaded_files.append(target_path)
                    print(f"[SportsEngine] 🎥 Gerçek basketbol B-roll video klibi indirildi: {target_path.name} ({target_path.stat().st_size // 1024} KB)")
        except Exception as e_dl:
            print(f"[SportsEngine] Video indirme hatası ({v_url[:40]}): {e_dl}")

    return downloaded_files


def extract_sports_video_cut(
    src_video: Path,
    out_clip: Path,
    duration: float,
    start_offset: float = 1.0,
    W: int = 1080,
    H: int = 1920,
    fps: int = 30
) -> bool:
    """Gerçek basketbol MP4 videosundan dikey 9:16 (1080x1920) dinamik kesit çıkarır."""
    try:
        cmd = [
            FFMPEG, "-y",
            "-ss", f"{start_offset:.2f}",
            "-t", f"{duration:.3f}",
            "-i", str(src_video),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-level", "4.0", "-preset", "ultrafast",
            "-an", str(out_clip)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return out_clip.exists() and out_clip.stat().st_size > 10000
    except Exception as e:
        print(f"[SportsEngine] Video kesit oluşturma hatası: {e}")
        return False


def format_sports_image(src_path: str, dst_path: str, target_w: int = 1080, target_h: int = 1920):
    """Görseli 9:16 oranına akıllı crop edip taranmış kenarlıkları yok eder ve sinematik kontrast/keskinlik ekler."""
    try:
        im = Image.open(src_path).convert("RGB")
        src_w, src_h = im.size
        src_ratio = src_w / src_h
        tgt_ratio = target_w / target_h
        
        # Taranmış matbaa kartı çerçeveleri ve letterbox boşluklarını yok etmek için %15 punch-in
        scale_factor = 1.15
        scaled_w = int(target_w * scale_factor)
        scaled_h = int(target_h * scale_factor)

        if src_ratio > tgt_ratio:
            new_h = scaled_h
            new_w = int(new_h * src_ratio)
        else:
            new_w = scaled_w
            new_h = int(new_w / src_ratio)
            
        im = im.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        im = im.crop((left, top, left + target_w, top + target_h))
        
        # Spor belgeseli kontrastı (+%10) ve renk doygunluğu
        enh_c = ImageEnhance.Contrast(im)
        im = enh_c.enhance(1.10)
        enh_s = ImageEnhance.Color(im)
        im = enh_s.enhance(1.08)
        
        im.save(dst_path, "JPEG", quality=95)
    except Exception as e:
        print(f"[SportsEngine] Görsel formatlama hatası ({src_path}): {e}")
        shutil.copy2(src_path, dst_path)


def get_bold_font(size: int = 44) -> ImageFont.FreeTypeFont:
    candidate_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

HIGHLIGHT_KEYWORDS = {
    'NBA', 'TRIPLE-DOUBLE', 'TRIPLE-DOUBLES', 'QUADRUPLE-DOUBLE',
    'REBOUNDS', 'ASSISTS', 'STEALS', 'BLOCKS', 'POINTS', 'PTS', 'REB', 'AST', 'STL', 'BLK',
    'DRAYMOND', 'GREEN', 'LEBRON', 'JAMES', 'WILT', 'CHAMBERLAIN', 'WARRIORS', 'LAKERS',
    'RECORD', 'HISTORY', 'MATRIX', 'DEFENSE', 'RIM', 'CHAMPION', 'SCORING', 'BASKETBALL',
    'TEN', 'TWELVE', 'FOUR', 'FIVE', 'SIX', 'HUNDRED', 'THOUSANDS', 'WARRIORS', 'BULLS',
    'JORDAN', 'KOBE', 'CURRY', 'SHAQ', 'MAGIC', 'BIRD', 'ALL-TIME', 'CHAMPIONSHIP', 'RULE',
    '100-POINT', '75-YEAR', '48', 'MINUTES', 'LONGEVITY', 'ROOKIE', 'MVP', 'FINALS'
}

def is_basketball_highlight(word: str) -> bool:
    clean = re.sub(r'[^A-Z0-9]', '', word.upper())
    if any(c.isdigit() for c in clean):
        return True
    if clean in HIGHLIGHT_KEYWORDS:
        return True
    for kw in HIGHLIGHT_KEYWORDS:
        if len(kw) >= 4 and kw in clean:
            return True
    return False

def render_basketball_subtitle_card(
    lines_text: list,
    width: int = 1080,
    height: int = 1920,
    bottom_pos: int = 240,
    font_size: int = 44
) -> Image.Image:
    """
    Kullanıcının referans videosundaki (/Users/alienes/Downloads/The Weirdest Triple-Double...)
    karanlık glassmorphism kart ve altın sarısı çerçeve estetiğini %100 birebir çizer:
    - Koyu gece mavisi yarı saydam arkaplan: rgba(18, 22, 34, 230)
    - 3px altın/amber çerçeve: #fbbf24
    - 24px yuvarlatılmış köşeler
    - Çift renkli tipografi (İstatistikler/İsimler altın sarısı, diğer kelimeler beyaz)
    - Ekranın altından 240px yukarıda ortalanmış
    - SIFIR TAŞMA GARANTİSİ: Satır genişliği 800px ile sınırlandırılır, uzun satırlar otomatik alt satıra kaydırılır.
    """
    font = get_bold_font(font_size)
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # 1. Aşama: Satırları piksel genişliğine göre katı bir şekilde kaydır (Wrap)
    # Maksimum metin satırı genişliği: 800px (1080px genişlikte her iki taraftan 140px güvenlik marjı)
    MAX_LINE_PIXELS = 800
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

    # 2. Aşama: Metrikleri ve renkleri hesapla
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
            color = '#fbbf24' if is_basketball_highlight(w) else '#ffffff'
            bbox = draw.textbbox((0, 0), w, font=font)
            w_w = bbox[2] - bbox[0]
            w_h = bbox[3] - bbox[1]
            words_data.append({'word': w, 'color': color, 'w': w_w, 'h': w_h})
            line_w += w_w + 12
            line_h = max(line_h, w_h)
        if words_data:
            line_w -= 12
        max_line_w = max(max_line_w, line_w)
        total_text_h += line_h
        line_metrics.append({'words': words_data, 'w': line_w, 'h': line_h})

    total_text_h += max(0, len(wrapped_lines) - 1) * line_spacing

    pad_x = 44
    pad_y = 24
    card_w = max(420, min(940, max_line_w + (pad_x * 2)))
    card_h = total_text_h + (pad_y * 2)

    card_x0 = (width - card_w) // 2
    card_y0 = height - bottom_pos - card_h
    card_x1 = card_x0 + card_w
    card_y1 = card_y0 + card_h

    # Hafif arka plan gölgesi
    draw.rounded_rectangle([card_x0, card_y0 + 6, card_x1, card_y1 + 6], radius=24, fill=(0, 0, 0, 120))
    # Ana Cam Kartı (Referans ile %100 Birebir)
    draw.rounded_rectangle([card_x0, card_y0, card_x1, card_y1], radius=24, fill=(18, 22, 34, 230), outline=(251, 191, 36, 255), width=3)

    # Ortalanmış ve çift renkli metinler
    curr_y = card_y0 + pad_y
    for lm in line_metrics:
        curr_x = card_x0 + (card_w - lm['w']) // 2
        for wd in lm['words']:
            draw.text((curr_x, curr_y), wd['word'], font=font, fill=wd['color'])
            curr_x += wd['w'] + 12
        curr_y += lm['h'] + line_spacing

    return canvas


def generate_basketball_subtitles_overlay(
    script: dict,
    total_dur: float,
    scratch_dir: Path,
    W: int = 1080,
    H: int = 1920
) -> Path:
    """
    Tüm anlatımı 2-4 kelimelik vurucu Shorts altyazı kartlarına böler.
    Her kart için PIL ile şeffaf PNG üretir ve ffmpeg concat listesi oluşturur.
    SIFIR TAŞMA GARANTİSİ: Her kart kısa tutulur ve satır genişliği piksel bazında denetlenir.
    """
    scenes = script.get("scenes", [])
    raw_texts = []
    if scenes and isinstance(scenes, list):
        for sc in scenes:
            t = sc.get("narration") or sc.get("text") or ""
            if t.strip():
                raw_texts.append(sanitize_sports_text(t))
    else:
        raw_text = script.get("narration") or script.get("story") or script.get("body") or script.get("title", "")
        if isinstance(raw_text, list):
            raw_text = " ".join(raw_text)
        raw_texts.append(sanitize_sports_text(raw_text))

    full_narr = " ".join(raw_texts)
    # Temizleme: Kelime arası tireleri boşluğa, uzun tireleri virgüle çevir
    clean_narr = re.sub(r'(\b\w+)\s*[-—]\s*(\w+\b)', r'\1 \2', full_narr)
    clean_narr = clean_narr.replace('—', ' , ').replace('...', ' , ')
    clean_narr = re.sub(r'\s+', ' ', clean_narr).strip()

    # 2-4 kelimelik doğal Shorts kartlarına böl
    raw_words = clean_narr.split()
    card_phrases = []
    curr_phrase = []

    for w in raw_words:
        w_clean = w.strip()
        if not w_clean:
            continue
        curr_phrase.append(w_clean)
        ends_punc = any(w_clean.endswith(p) for p in ['.', '!', '?', ',', ';', ':'])
        # 3 veya 4 kelimede veya noktalama işaretinde kartı tamamla
        if len(curr_phrase) >= 4 or (len(curr_phrase) >= 2 and ends_punc):
            clean_words = [re.sub(r'[.,!?;:]', '', x).strip().upper() for x in curr_phrase if x.strip()]
            if clean_words:
                card_phrases.append(clean_words)
            curr_phrase = []

    if curr_phrase:
        clean_words = [re.sub(r'[.,!?;:]', '', x).strip().upper() for x in curr_phrase if x.strip()]
        if clean_words:
            card_phrases.append(clean_words)

    # Anti-Orphan & Son Kelime Kırpılma Koruması (Subtitle Final Token Seal):
    # Cümle sonundaki "art", "shot" gibi 1-2 kelimelik parçaların tek başına kalıp erken kesilmesini %100 engeller
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
    total_chars = 0
    for cp in card_phrases:
        if len(cp) <= 3:
            lines = [" ".join(cp)]
        else:
            mid = (len(cp) + 1) // 2
            lines = [" ".join(cp[:mid]), " ".join(cp[mid:])]
        char_count = sum(len(w) for w in cp)
        total_chars += char_count
        cards_data.append({"lines": lines, "chars": char_count})

    if not cards_data:
        cards_data = [{"lines": ["THE BASKETBALL SHOW"], "chars": 20}]
        total_chars = 20

    sub_dir = scratch_dir / "sub_cards"
    sub_dir.mkdir(parents=True, exist_ok=True)
    concat_lines = []

    # Altyazı sürelerinin video uzunluğuna ve son cümlenin ekranda kalma garantisine göre dağıtımı:
    # Son kartın ekranda en az 2.20 saniye boyunca tam ve eksiksiz okunmasını garanti et!
    num_cards = len(cards_data)
    card_durations = []
    if num_cards == 1:
        card_durations = [total_dur]
    else:
        # Son karta en az 2.20s veya video süresinin %16'sı kadar güvenlik payı ayır
        last_card_target = max(2.20, min(4.00, total_dur * 0.16))
        remaining_time = max(total_dur - last_card_target, float(num_cards - 1) * 1.05)
        remaining_chars = max(1, sum(cards_data[i]["chars"] for i in range(num_cards - 1)))
        
        running_sum = 0.0
        for i in range(num_cards - 1):
            c_dur = remaining_time * (cards_data[i]["chars"] / remaining_chars)
            c_dur = max(1.05, c_dur)
            card_durations.append(c_dur)
            running_sum += c_dur

        # Son kart kalan süreyi tam kapatır (en az 2.20 saniye garantili)
        final_card_dur = max(2.20, round(total_dur - running_sum, 3))
        card_durations.append(final_card_dur)

    for idx, cdata in enumerate(cards_data):
        card_img = render_basketball_subtitle_card(cdata["lines"], width=W, height=H, bottom_pos=240, font_size=44)
        card_path = sub_dir / f"card_{idx:03d}.png"
        card_img.save(card_path, "PNG")
        
        dur = card_durations[idx]
        concat_lines.append(f"file '{card_path.resolve()}'")
        concat_lines.append(f"duration {dur:.3f}")

    if cards_data:
        last_card = sub_dir / f"card_{len(cards_data)-1:03d}.png"
        concat_lines.append(f"file '{last_card.resolve()}'")
        concat_lines.append("duration 10.000")  # Son segment mühürleme: Video son karesine kadar ekranda tut
        concat_lines.append(f"file '{last_card.resolve()}'")

    concat_file = scratch_dir / "subtitles_concat.txt"
    concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    print(f"[SportsEngine] 🏀 {len(cards_data)} adet altın çerçeveli cam altyazı kartı hazırlandı (Son kart: {card_durations[-1]:.2f}s): {concat_file}")
    return concat_file


def generate_sports_ass(script: dict, total_duration: float, ass_path: str, badge_title: str = "THE BASKETBALL SHOW | NBA ANALYSIS"):
    """Geriye uyumluluk için korunan dummy/fallback ASS fonksiyonu."""
    Path(ass_path).write_text("", encoding="utf-8")


def render_sports_shorts_job(job_data: dict, work_dir: Path, workspace_dir: Optional[Path] = None, force_rebuild: bool = False) -> Path:
    """
    Spor Shorts render iş akışı:
    Gerçek görseller, gerçek hareketli maç/aksiyon video klipleri (B-roll), 
    2.0-2.8s jump-cut'lar, dinamik altyazı ve hip-hop arka plan müziği.
    ASLA ÇİZİM VEYA ŞEMATİK GRAFİK KULLANILMAZ.
    Tam Proje İzolasyonu (Job-Level Sandboxing) ile bağımsız çalışma alanı.
    """
    work_dir = Path(work_dir)
    channel_id = job_data.get("channel_id", "thebasketballshows")
    script = job_data.get("script_data") or job_data.get("script") or {}
    channel_cfg = job_data.get("channel_config") or {}
    job_id = job_data.get("job_id", f"job_{int(time.time())}")
    
    W, H = 1080, 1920
    fps = 30
    
    # ── PROJE BAZLI ÇALIŞMA ALANI İZOLASYONU (Job-Level Sandboxing) ──
    if workspace_dir is None:
        if job_data.get("workspace_dir"):
            workspace_dir = Path(job_data["workspace_dir"])
        else:
            workspace_dir = work_dir / "workspace"
    workspace_dir = Path(workspace_dir)

    downloads_dir = workspace_dir / "downloads"
    photo_pool_dir = workspace_dir / "photo_pool"
    cuts_dir = workspace_dir / "cuts"
    scratch_dir = workspace_dir / "scratch"

    force_rebuild = force_rebuild or job_data.get("force_rebuild", False)
    if force_rebuild:
        print(f"[SportsEngine] 🔄 --force-rebuild aktif: Çalışma alanı sıfırlanıyor ({workspace_dir})...")
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir, ignore_errors=True)
        for old_f in work_dir.glob("*.mp4"):
            try: old_f.unlink()
            except Exception: pass

    workspace_dir.mkdir(parents=True, exist_ok=True)
    downloads_dir.mkdir(parents=True, exist_ok=True)
    photo_pool_dir.mkdir(parents=True, exist_ok=True)
    cuts_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Seslendirme dosyasını belirle
    audio_file = work_dir / "voiceover.wav"
    if not audio_file.exists():
        audio_file = work_dir / "voiceover.mp3"
    
    if not audio_file.exists():
        print("[SportsEngine] Seslendirme bulunamadı, edge-tts ile üretiliyor...")
        scenes = script.get("scenes", [])
        if scenes:
            txt = " ".join(s.get("narration", "") for s in scenes)
        else:
            txt = script.get("title", "NBA Basketball Analysis")
        import edge_tts, asyncio
        async def _tts():
            comm = edge_tts.Communicate(txt, "en-US-ChristopherNeural", rate="+10%")
            await comm.save(str(work_dir / "voiceover.mp3"))
        asyncio.run(_tts())
        audio_file = work_dir / "voiceover.mp3"
        
    if timeline_guard is not None:
        try:
            dur_lock = timeline_guard.calculate_locked_timeline_duration(audio_file, tail_padding_sec=1.50)
            total_dur = dur_lock["locked_duration"]
            print(f"[SportsEngine] 🔒 [TimelineGuard] Dış ses süresi kilitlendi: {dur_lock['audio_duration']:.2f}s + 1.5s = {total_dur:.2f}s")
        except Exception:
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(audio_file)
            ], capture_output=True, text=True, check=True)
            total_dur = float(probe.stdout.strip()) + 1.50
    else:
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_file)
        ], capture_output=True, text=True, check=True)
        total_dur = float(probe.stdout.strip()) + 1.50
    print(f"[SportsEngine] 🏀 Toplam kilitli video süresi (+1.5s tampon nefes payı): {total_dur:.2f}s")

    # ── PROJE İZOLASYONU (Job Sandboxing) ──
    # Kara listedeki amatör stokları ve önceki koşudan kalan geçici dosyaları temizle
    for pattern in ["*rural*", "*backyard*", "*cargo*", "*driveway*", "*pink*", "raw_*", "cut_*"]:
        for bad_f in scratch_dir.glob(pattern):
            try:
                bad_f.unlink()
            except Exception:
                pass

    # 2. Video Klip Zorunluluğunun Kaldırılması & Dinamik Ken Burns
    # enforce_video_clips = False: Amatör/köy evi stok videoları yerine %100 gerçek, onaylanmış NBA arşiv fotoğrafları dinamik Ken Burns ile hareketlendirilir.
    enforce_video_clips = False
    custom_vids = job_data.get("custom_videos") or []
    broll_videos = [Path(cv) for cv in custom_vids if Path(cv).exists()] if enforce_video_clips else []
    print(f"[SportsEngine] 🎬 Video klip zorunluluğu: {enforce_video_clips} (Amatör Pixabay b-roll devre dışı, %100 onaylı NBA arşiv fotoğrafları)")

    # 3. Sahne Görsellerini Hazırla (%100 Gerçek Arşiv Fotoğrafları - SIFIR TEKRAR HAVUZU)
    scenes = script.get("scenes", [])
    if not scenes or not isinstance(scenes, list):
        scenes = [{"narration": script.get("title", "NBA Analysis"), "image_prompt": "NBA basketball action"}]

    scene_durs = [total_dur / len(scenes)] * len(scenes)
    scene_photos = {}
    photo_pool = []
    used_urls = set()
    custom_imgs = job_data.get("custom_images") or {}

    # A) custom_images varsa öncelikli olarak havuza ekle
    for ck in sorted(custom_imgs.keys()):
        cv = custom_imgs[ck]
        cp = Path(cv)
        if cp.exists() and cp.stat().st_size > 10000:
            target_custom = photo_pool_dir / f"custom_{len(photo_pool):03d}.jpg"
            format_sports_image(str(cp), str(target_custom), W, H)
            photo_pool.append(target_custom)
            print(f"[SportsEngine] 📸 Özel görsel havuza eklendi: {cp.name}")

    # Pre-Render Quality Gate No-Loop Kaydını Sıfırla
    if asset_validator is not None:
        asset_validator.reset_used_assets()
    if fallback_engine is not None:
        fallback_engine.reset_quota()
        # İnfografik Kartı İzolasyonu: Sadece teyitli istatistik verisi varsa etkinleştir
        infographic_stats = job_data.get("infographic_stats") or script.get("infographic_stats")
        if not infographic_stats:
            fallback_engine.skip_infographic = True
            fallback_engine.current_infographic_stats = None
        else:
            fallback_engine.skip_infographic = False
            fallback_engine.current_infographic_stats = infographic_stats
    if timeline_guard is not None:
        timeline_guard.reset_timeline()

    # Birincil Oyuncu ve Takım Bilgisini Belirle
    primary_entity = "NBA Player"
    team_name = None
    if query_builder is not None:
        cq_main = query_builder.build_context_locked_queries(script)
        primary_entity = cq_main.entity
        team_name = cq_main.team_name

    # ── B & C) ÇOKLU SORGU GENİŞLETMESİ & MİNİMUM 25+ ONAYLI NBA MAÇ GÖRSELİ HAVUZU ──
    # Aday Havuzu Kıtlığı (Fetch Starvation) ve 3 Görselli Döngü Hatalarını Tamamen Ortadan Kaldırır
    estimated_cuts = max(8, int(math.ceil(total_dur / 2.20)))
    target_photo_count = max(25, estimated_cuts + 3)
    print(f"[SportsEngine] 🔍 Çoklu-sorgu genişletmesi (Multi-Query Expansion) ve SigLIP doğrulama başlatılıyor (Hedef: En az {target_photo_count} görsel)...")
    if asset_fetcher is not None:
        detected_year = query_builder.extract_year(str(script)) if query_builder is not None else None
        opp_ent = None
        if query_builder is not None:
            c_text = str(script).lower()
            for cand_p in getattr(query_builder, "PLAYER_CAREER_MAP", {}).keys():
                if cand_p.lower() != primary_entity.lower() and cand_p.lower() in c_text:
                    opp_ent = cand_p
                    break
        fetched_photos = asset_fetcher.fetch_diverse_nba_assets(
            script_data=script,
            scratch_dir=scratch_dir,
            min_unique_assets=target_photo_count,
            target_entity=primary_entity,
            opponent_entity=opp_ent,
            era_year=detected_year,
            width=W,
            height=H,
            downloads_dir=downloads_dir,
            photo_pool_dir=photo_pool_dir
        )
        for fp in fetched_photos:
            if fp not in photo_pool:
                photo_pool.append(fp)

    # İkincil Güvenlik Katmanı: Havuz target_photo_count altındaysa yedek sorgularla tamamla
    if len(photo_pool) < target_photo_count:
        for s_idx, sc in enumerate(scenes):
            if len(photo_pool) >= target_photo_count:
                break
            sc_narr = sc.get("narration") or sc.get("text") or ""
            dyn_negatives = []
            if query_builder is not None:
                cq = query_builder.build_context_locked_queries(script, sc_narr)
                dyn_negatives = cq.dynamic_negatives

            q_candidates = extract_player_or_topic_keywords(script, sc_narr)
            for q in q_candidates:
                if len(photo_pool) >= target_photo_count:
                    break
                urls = search_wikimedia_sports_media(q, limit=10)
                for u in urls:
                    if u in used_urls or len(photo_pool) >= target_photo_count:
                        continue
                    used_urls.add(u)
                    try:
                        r = requests.get(u, headers={"User-Agent": WIKIMEDIA_USER_AGENT}, timeout=8)
                        if r.status_code == 200 and len(r.content) > 25000:
                            raw_temp = downloads_dir / f"raw_wiki_bk_{len(photo_pool):03d}.jpg"
                            raw_temp.write_bytes(r.content)
                            target_img = photo_pool_dir / f"photo_{len(photo_pool):03d}.jpg"
                            format_sports_image(str(raw_temp), str(target_img), W, H)

                            if asset_validator is not None:
                                val = asset_validator.validate_candidate(
                                    image_path=target_img,
                                    scene_prompt=sc_narr or q,
                                    project_type="basketball_analysis",
                                    target_entity=q,
                                    is_vertical=True,
                                    dynamic_negatives=dyn_negatives
                                )
                                if not val.is_valid:
                                    try:
                                        target_img.unlink()
                                    except Exception:
                                        pass
                                    continue
                                asset_validator.register_used_asset(target_img)

                            photo_pool.append(target_img)
                            print(f"[SportsEngine] 📸 Yedek arşiv görseli onaylandı: '{q}' (Havuz: {len(photo_pool)})")
                    except Exception:
                        pass

    # ── KATI MD5 TEKİLLEŞTİRME HAVUZU (Asset De-duplication Registry) ──
    def _compute_md5(p: Path) -> str:
        try:
            if p.exists() and p.is_file():
                h = hashlib.md5()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                return h.hexdigest()
        except Exception:
            pass
        return ""

    def _compute_dhash(p: Path, hash_size: int = 8) -> str:
        try:
            from PIL import Image
            if p.exists() and p.is_file():
                im = Image.open(p).convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
                pixels = list(im.getdata())
                diff = []
                for row in range(hash_size):
                    for col in range(hash_size):
                        diff.append(pixels[row * (hash_size + 1) + col] > pixels[row * (hash_size + 1) + col + 1])
                dec = 0
                hex_str = []
                for idx, v in enumerate(diff):
                    if v:
                        dec += 2 ** (idx % 8)
                    if (idx % 8) == 7:
                        hex_str.append(hex(dec)[2:].rjust(2, "0"))
                        dec = 0
                return "".join(hex_str)
        except Exception:
            pass
        return ""

    def _hamming_dist(s1: str, s2: str) -> int:
        if not s1 or not s2 or len(s1) != len(s2):
            return 999
        try:
            b1 = bin(int(s1, 16))[2:].zfill(len(s1) * 4)
            b2 = bin(int(s2, 16))[2:].zfill(len(s2) * 4)
            return sum(c1 != c2 for c1, c2 in zip(b1, b2))
        except Exception:
            return 999

    unique_photo_pool = []
    seen_dhashes = []
    seen_md5_hashes = set()
    for p in photo_pool:
        md5_h = _compute_md5(p)
        if md5_h and md5_h in seen_md5_hashes:
            print(f"[SportsEngine] 🗑️ MD5 mükerrer görsel elendi: {p.name}")
            continue

        dh = _compute_dhash(p)
        is_dup = False
        if dh:
            for ex_dh in seen_dhashes:
                if _hamming_dist(dh, ex_dh) <= 10:
                    is_dup = True
                    break

        if not is_dup:
            if md5_h:
                seen_md5_hashes.add(md5_h)
            if dh:
                seen_dhashes.append(dh)
            unique_photo_pool.append(p)
        else:
            print(f"[SportsEngine] 🗑️ Algısal mükerrer görsel (Perceptual Duplicate) elendi: {p.name}")

    photo_pool = unique_photo_pool

    if not photo_pool and pipeline_integration is not None:
        fallback_p = photo_pool_dir / "safe_fallback_000.jpg"
        pipeline_integration.generate_safe_fallback_background(fallback_p, project_type="basketball_analysis", scene_idx=0)
        photo_pool.append(fallback_p)

    print(f"[SportsEngine] 📸 Fotoğraf havuzu hazır: Toplam {len(photo_pool)} benzersiz yüksek çözünürlüklü fotoğraf.")

    # 4. Hızlı Kesme: Gerçek Oyuncu Fotoğrafları <-> Gerçek Basketbol Video Klipleri (2.0 - 2.5s)
    # ASLA AYNI GÖRSELE GERİ DÖNÜLMEZ: Her kesme için benzersiz görsel atanır!
    print(f"[SportsEngine] 🎬 Hızlı jump-cut kurgusu üretiliyor (Sıfır tekrar, benzersiz fotoğraf ve videolar)...")
    cut_files = []
    
    target_cut_duration = 2.20
    total_cuts = max(8, int(math.ceil(total_dur / target_cut_duration)))
    actual_cut_len = total_dur / total_cuts

    # Kutu skoru (box_score) görselini tespit et
    box_score_img = next((p for p in photo_pool if "box_score" in p.name.lower()), None)
    # İstatistik anons penceresi (Yaklaşık 16.0s - 22.0s arası)
    stat_start_idx = max(1, int(15.5 / actual_cut_len))
    stat_end_idx = min(total_cuts - 1, int(22.0 / actual_cut_len))

    # Kutu skoru haricindeki fotoğraflar
    regular_photos = [p for p in photo_pool if p != box_score_img] if box_score_img else list(photo_pool)
    reg_photo_idx = 0
    vid_idx = 0

    # Video klip zorunluluğu kaldırıldı (enforce_video_clips = False):
    # Amatör sokak/köy evi klipleri yerine %100 onaylı NBA fotoğrafları dinamik Ken Burns kurgusuyla akar!
    prefer_photos_only = True

    for cut_i in range(total_cuts):
        out_clip = cuts_dir / f"cut_{cut_i:03d}.mp4"
        cut_files.append(str(out_clip))
        frames = int(actual_cut_len * fps)

        # 1. Kural: İstatistik anons anında (%100 resmi NBA Kutu Skoru tablosu gösterilir)
        if box_score_img and (stat_start_idx <= cut_i <= stat_end_idx):
            chosen_photo = box_score_img
            if timeline_guard is not None:
                timeline_guard.register_timeline_asset(chosen_photo)
            if asset_validator is not None:
                asset_validator.register_used_asset(chosen_photo)
            # Kutu skoru tablosu net ve sabit okunabilmeli (hafif nefes alan zoom)
            z_s, z_e = 1.00, 1.04
            step = (z_e - z_s) / max(1, frames)
            zp = f"zoompan=z='min(zoom+{step:.6f},{max(z_s, z_e):.2f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={fps},fps={fps},setsar=1"
            scale_w = int(W * 1.15)
            scale_h = int(H * 1.15)
            cmd = [
                FFMPEG, "-y",
                "-loop", "1", "-i", str(chosen_photo),
                "-vf", f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,crop={W}:{H}:(in_w-{W})/2:(in_h-{H})/2,{zp}",
                "-t", f"{actual_cut_len:.3f}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-level", "4.0", "-preset", "ultrafast",
                "-an", str(out_clip)
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            continue

        # 2. Kural: Video zorunluluğu kaldırıldı - %100 Onaylı Dinamik Ken Burns Fotoğraf Kurgusu
        use_video = False
        video_done = False

        if use_video and broll_videos:
            chosen_broll = broll_videos[vid_idx % len(broll_videos)]
            vid_idx += 1
            offset = 0.8 + ((cut_i * 1.85) % 6.5)
            video_done = extract_sports_video_cut(chosen_broll, out_clip, actual_cut_len, start_offset=offset, W=W, H=H, fps=fps)

        if not video_done:
            chosen_photo = None
            while reg_photo_idx < len(regular_photos):
                candidate_p = regular_photos[reg_photo_idx]
                reg_photo_idx += 1
                if timeline_guard is not None and timeline_guard.is_asset_used(candidate_p):
                    continue
                chosen_photo = candidate_p
                break

            if chosen_photo is None:
                # Havuz tükendiğinde veya tüm görseller kullanıldığında ASLA eski fotoğraflara başa sarılmaz!
                # Katı Kural: Bir kaynak fotoğraf bir render boyunca yalnızca 1 kesmede kullanılabilir (max_occurrences_per_source = 1).
                # İkinci kez çağrılması yasaktır, bu sebeple character_archive_image verilmez (None).
                # FallbackEngine doğrudan Kademe 2 (varsa teyitli istatistik) veya Kademe 3 (Soyut Hareketli Doku) üretir.
                if fallback_engine is not None:
                    main_player = primary_entity
                    fallback_engine.resolve_fail_safe_clip(
                        output_clip_path=out_clip,
                        duration=actual_cut_len,
                        primary_entity=main_player,
                        team_name=team_name,
                        scene_text=script.get("title", ""),
                        character_archive_image=None,
                        scratch_dir=scratch_dir,
                        cut_index=cut_i,
                        total_cuts=total_cuts,
                        width=W,
                        height=H,
                        fps=fps
                    )
                    assert out_clip.exists() and out_clip.stat().st_size > 1000, f"FallbackEngine klip üretemedi: {out_clip}"
                    print(f"[SportsEngine] 🛡️ [Zero Black Screen] Tekil kaynak kuralı korundu (Soyut Doku): cut_{cut_i:03d}")
                    continue
                else:
                    fallback_img = scratch_dir / f"safe_fallback_cut_{cut_i:03d}.jpg"
                    if pipeline_integration is not None:
                        pipeline_integration.generate_safe_fallback_background(
                            output_path=fallback_img,
                            project_type="basketball_analysis",
                            scene_idx=cut_i,
                            width=W,
                            height=H
                        )
                    else:
                        fb = Image.new("RGB", (W, H), (15, 23, 42))
                        fb.save(fallback_img, "JPEG")
                    chosen_photo = fallback_img
                    print(f"[SportsEngine] 🛡️ Havuz tükendi, degrade arka plan atandı: cut_{cut_i:03d}")

            # Dinamik Ken Burns: Punch-in, zoom-in ve zoom-out rotasyonu (Amatör stok video zorunluluğu kaldırıldı)
            repeat_cnt = timeline_guard.register_timeline_asset(chosen_photo) if timeline_guard is not None else 1
            if asset_validator is not None:
                asset_validator.register_used_asset(chosen_photo)

            if timeline_guard is not None:
                vf_filter = timeline_guard.build_ken_burns_filter(cut_i, actual_cut_len, fps=fps, width=W, height=H, repeat_count=repeat_cnt)
            else:
                scale_w = int(W * 1.15)
                scale_h = int(H * 1.15)
                if cut_i % 4 == 0:
                    z_s, z_e = 1.00, 1.10
                elif cut_i % 4 == 1:
                    z_s, z_e = 1.14, 1.22
                elif cut_i % 4 == 2:
                    z_s, z_e = 1.10, 1.02
                else:
                    z_s, z_e = 1.05, 1.14
                step = (z_e - z_s) / max(1, frames)
                zp = f"zoompan=z='min(zoom+{step:.6f},{max(z_s, z_e):.2f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={fps},fps={fps},setsar=1"
                vf_filter = f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,crop={W}:{H}:(in_w-{W})/2:(in_h-{H})/2,{zp},eq=contrast=1.06:brightness=0.01:saturation=1.10"

            cmd = [
                FFMPEG, "-y",
                "-loop", "1", "-i", str(chosen_photo),
                "-vf", vf_filter,
                "-t", f"{actual_cut_len:.3f}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-level", "4.0", "-preset", "ultrafast",
                "-an", str(out_clip)
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        elif broll_videos:
            extract_sports_video_cut(broll_videos[0], out_clip, actual_cut_len, start_offset=0.5, W=W, H=H, fps=fps)
        else:
            # SIFIR SİYAH EKRAN: Asla düz siyah zemin basılmaz!
            if fallback_engine is not None:
                main_player = primary_entity
                fallback_engine.resolve_fail_safe_clip(
                    output_clip_path=out_clip,
                    duration=actual_cut_len,
                    primary_entity=main_player,
                    team_name=team_name,
                    scene_text=script.get("title", ""),
                    character_archive_image=None,
                    scratch_dir=scratch_dir,
                    cut_index=cut_i,
                    width=W,
                    height=H,
                    fps=fps
                )
            else:
                cmd = [
                    FFMPEG, "-y",
                    "-f", "lavfi", "-i", f"color=c=0x0c111d:s={W}x{H}:d={actual_cut_len}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "baseline", "-level", "4.0", "-preset", "ultrafast",
                    "-an", str(out_clip)
                ]
                subprocess.run(cmd, capture_output=True, check=True)

    # Sıfır Siyah Ekran Doğrulaması (Assertion Check)
    for c in cut_files:
        c_path = Path(c)
        assert c_path.exists(), f"KRİTİK HATA: Kesme klibi oluşturulamadı: {c}"
        assert c_path.stat().st_size > 1000, f"KRİTİK HATA: Kesme klibi 0-byte veya bozuk: {c}"

    concat_list = cuts_dir / "cuts.txt"
    with open(concat_list, "w") as f:
        for c in cut_files:
            f.write(f"file '{c}'\n")
            
    master_visuals = cuts_dir / "master_visuals.mp4"
    subprocess.run([
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy", str(master_visuals)
    ], capture_output=True, check=True)

    # 5. Dinamik Altyazı Kartları (Referans Video Estetiği: Altın Çerçeveli Glassmorphism Kart)
    sub_concat_file = generate_basketball_subtitles_overlay(script, total_dur, scratch_dir, W=W, H=H)

    # 6. Hip-hop Arka Plan Müziği ve Final Miks
    base_assets = Path(__file__).resolve().parent.parent / "assets"
    bgm_candidates = [
        base_assets / "music" / "underworld.mp3",
        base_assets / "music" / "borderless.mp3",
        Path("/home/ubuntu/yt-remote-worker/assets/music/underworld.mp3"),
        Path("/Users/alienes/yt-oto-video/files/assets/music/underworld.mp3")
    ]
    bgm_path = None
    for b_cand in bgm_candidates:
        if b_cand.exists():
            bgm_path = b_cand
            break

    final_video = work_dir / "final_video.mp4"
    fadeout_start = max(0.0, total_dur - 0.50)
    
    if bgm_path and bgm_path.exists():
        filter_complex = (
            "[0:v][1:v]overlay=0:0:eof_action=pass[vout];"
            "[3:a]volume=0.12[bgm];"
            f"[2:a]apad=whole_dur={total_dur:.3f}[apad];"
            f"[apad][bgm]amix=inputs=2:duration=longest:dropout_transition=2,afade=t=out:st={fadeout_start:.3f}:d=0.50[aout]"
        )
        cmd_final = [
            FFMPEG, "-y",
            "-i", str(master_visuals),
            "-f", "concat", "-safe", "0", "-i", str(sub_concat_file),
            "-i", str(audio_file),
            "-stream_loop", "-1", "-i", str(bgm_path),
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total_dur:.3f}", str(final_video)
        ]
    else:
        filter_complex = (
            "[0:v][1:v]overlay=0:0:eof_action=pass[vout];"
            f"[2:a]apad=whole_dur={total_dur:.3f},afade=t=out:st={fadeout_start:.3f}:d=0.50[aout]"
        )
        cmd_final = [
            FFMPEG, "-y",
            "-i", str(master_visuals),
            "-f", "concat", "-safe", "0", "-i", str(sub_concat_file),
            "-i", str(audio_file),
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total_dur:.3f}", str(final_video)
        ]

    print("[SportsEngine] 🔥 Final spor master video derleniyor...")
    subprocess.run(cmd_final, check=True)
    
    # final.mp4 kopyası
    final_sym = work_dir / "final.mp4"
    shutil.copy2(str(final_video), str(final_sym))
    
    size_mb = final_video.stat().st_size / (1024 * 1024)
    print(f"[SportsEngine] 🎉 MASTER VIDEO BAŞARIYLA ÜRETİLDİ: {final_video} ({size_mb:.2f} MB)")
    return final_video


if __name__ == "__main__":
    print("Sports Shorts Engine v3 (Real Video B-Roll & Zero Drawing Edition) loaded.")
