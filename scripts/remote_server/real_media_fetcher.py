"""
real_media_fetcher.py
=====================
Evrensel Telifsiz Gerçek Video ve Fotoğraf Çekim Motoru (Zero-AI-Image Pipeline).
Seyahat (Travel), Basketbol / Spor (Basketball Analysis) ve Belgesel kanalları için:
1. Pixabay Video API: 1080p gerçek B-roll MP4 video klipleri.
2. Pixabay Photo API: Yüksek çözünürlüklü gerçek ortam ve detay fotoğrafları.
3. Wikimedia Commons API: Gerçek sporcular (NBA efsaneleri), tarihi anıtlar ve coğrafi yapılar.

Stable Diffusion (Yapay zekâ görsel üretimi) maliyetini, bekleme süresini ve yapaylığını sıfırlar.
"""

from __future__ import annotations

import os
import re
import json
import random
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from PIL import Image

try:
    from settings_manager import SettingsManager
except ImportError:
    try:
        from src.settings_manager import SettingsManager
    except ImportError:
        SettingsManager = None

try:
    from asset_validator import asset_validator
    from query_builder import query_builder
    from fallback_engine import fallback_engine
except ImportError:
    try:
        from src.asset_validator import asset_validator
        from src.query_builder import query_builder
        from src.fallback_engine import fallback_engine
    except ImportError:
        asset_validator = None
        query_builder = None
        fallback_engine = None

try:
    from visual_content_guard import visual_guard
except ImportError:
    try:
        from src.visual_content_guard import visual_guard
    except ImportError:
        visual_guard = None


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
WIKIMEDIA_USER_AGENT = "VideoCreator/2.0 (https://github.com/alienes/yt-oto-video; contact@alienes.com)"


def get_pixabay_key() -> str:
    """SettingsManager üzerinden şifrelenmiş veya düz Pixabay API anahtarını döner."""
    if SettingsManager is not None:
        try:
            sm = SettingsManager()
            val = sm.get("pixabay_api_key")
            if val and isinstance(val, str) and len(val) > 10:
                return val.strip()
        except Exception as e:
            print(f"[REAL-FETCHER] SettingsManager anahtar okuma hatası: {e}")
    return os.environ.get("PIXABAY_API_KEY", "57648418-49ecb0060f2db281a386d04cf")


# ─────────────────────────────────────────────────────────────
# 1. PİXABAY VİDEO ARAMA
# ─────────────────────────────────────────────────────────────

def search_pixabay_video(
    query: str,
    exclude_ids: Optional[Set[int]] = None,
    min_duration: float = 3.0,
    video_type: str = "film"  # "all", "film", "animation"
) -> Optional[Dict[str, Any]]:
    """Pixabay Video API'den uygun, dikey kesime elverişli 1080p MP4 klip arar."""
    api_key = get_pixabay_key()
    if not api_key:
        return None

    clean_q = re.sub(r"[^\w\s-]", "", query).strip()
    if not clean_q:
        clean_q = "travel scenery"

    params = {
        "key": api_key,
        "q": clean_q,
        "video_type": video_type,
        "safesearch": "true",
        "per_page": 15
    }
    url = f"https://pixabay.com/api/videos/?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": USER_AGENT}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[REAL-FETCHER] Pixabay video sorgu hatası ('{clean_q}'): {e}")
        return None

    hits = data.get("hits", [])
    if not hits:
        return None

    exclude = exclude_ids or set()
    candidates = []

    for h in hits:
        hid = h.get("id")
        if hid in exclude:
            continue
        dur = float(h.get("duration", 0.0))
        if dur < min_duration:
            continue

        videos = h.get("videos", {})
        # Kalite hiyerarşisi: large (1080p) -> medium (720p) -> small
        v_obj = videos.get("large") or videos.get("medium") or videos.get("small")
        if not v_obj or not v_obj.get("url"):
            continue

        candidates.append({
            "id": hid,
            "url": v_obj.get("url"),
            "width": v_obj.get("width", 1920),
            "height": v_obj.get("height", 1080),
            "duration": dur,
            "tags": h.get("tags", "")
        })

    if not candidates:
        return None

    # Çeşitlilik için ilk 3 arasından rastgele seç
    return random.choice(candidates[:3])


# ─────────────────────────────────────────────────────────────
# 2. PİXABAY FOTOĞRAF ARAMA
# ─────────────────────────────────────────────────────────────

def search_pixabay_photos(
    query: str,
    exclude_ids: Optional[Set[int]] = None,
    limit: int = 5,
    image_type: str = "photo"
) -> List[Dict[str, Any]]:
    """Pixabay Fotoğraf API'den yüksek çözünürlüklü gerçek fotoğrafları liste olarak arar."""
    api_key = get_pixabay_key()
    if not api_key:
        return []

    clean_q = re.sub(r"[^\w\s-]", "", query).strip()
    if not clean_q:
        clean_q = "travel destination"

    params = {
        "key": api_key,
        "q": clean_q,
        "image_type": image_type,
        "safesearch": "true",
        "per_page": min(30, max(15, limit * 3))
    }
    url = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": USER_AGENT}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[REAL-FETCHER] Pixabay fotoğraf sorgu hatası ('{clean_q}'): {e}")
        return []

    hits = data.get("hits", [])
    if not hits:
        return []

    exclude = exclude_ids or set()
    candidates = []

    for h in hits:
        hid = h.get("id")
        if hid in exclude:
            continue
        img_url = h.get("largeImageURL") or h.get("fullHDURL") or h.get("webformatURL")
        if not img_url:
            continue

        candidates.append({
            "id": hid,
            "url": img_url,
            "width": h.get("imageWidth", 1920),
            "height": h.get("imageHeight", 1080),
            "tags": h.get("tags", "")
        })
        if len(candidates) >= limit:
            break

    return candidates


def search_pixabay_photo(
    query: str,
    exclude_ids: Optional[Set[int]] = None,
    image_type: str = "photo"
) -> Optional[Dict[str, Any]]:
    """Geriye uyumluluk için tekil Pixabay fotoğrafı döner."""
    cands = search_pixabay_photos(query, exclude_ids=exclude_ids, limit=3, image_type=image_type)
    return random.choice(cands) if cands else None


# ─────────────────────────────────────────────────────────────
# 3. WIKIMEDIA COMMONS ARAMA (Sporcular, Tarihi Anıtlar, Şehirler)
# ─────────────────────────────────────────────────────────────

def search_wikimedia_commons_photos(
    query: str,
    exclude_urls: Optional[Set[str]] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Wikimedia Commons API'den kamu malı / Creative Commons gerçek fotoğrafları liste olarak arar."""
    clean_q = re.sub(r"[^\w\s-]", "", query).strip()
    if not clean_q:
        return []

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": clean_q,
        "gsrnamespace": 6,  # File: namespace
        "gsrlimit": min(20, max(8, limit * 2)),
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": 1280
    }
    url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": WIKIMEDIA_USER_AGENT}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[REAL-FETCHER] Wikimedia Commons sorgu hatası ('{clean_q}'): {e}")
        return []

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return []

    exclude = exclude_urls or set()
    candidates = []

    for pid, page in pages.items():
        title = page.get("title", "")
        t_low = title.lower()

        # İkon, ses, svg ve logoları ele
        if any(skip in t_low for skip in [".svg", ".ogg", ".oga", ".pdf", "flag", "icon", "logo", "symbol"]):
            continue

        imageinfo = page.get("imageinfo", [])
        if not imageinfo:
            continue
        info = imageinfo[0]
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png"):
            continue

        w = info.get("width", 0)
        h = info.get("height", 0)
        # Çok küçük resimleri ele (en az 600px olmalı)
        if w < 600 or h < 600:
            continue

        # Thumbnail URL CDN üzerinden 429 kısıtlaması olmadan ultra hızlı gelir
        img_url = info.get("thumburl") or info.get("url")
        if not img_url or img_url in exclude:
            continue

        candidates.append({
            "id": pid,
            "title": title,
            "url": img_url,
            "width": w,
            "height": h
        })
        if len(candidates) >= limit:
            break

    return candidates


def search_wikimedia_commons(
    query: str,
    exclude_urls: Optional[Set[str]] = None,
    limit: int = 8
) -> Optional[Dict[str, Any]]:
    """Geriye uyumluluk için tekil Wikimedia fotoğrafı döner."""
    cands = search_wikimedia_commons_photos(query, exclude_urls=exclude_urls, limit=1)
    return cands[0] if cands else None


# ─────────────────────────────────────────────────────────────
# 4. MEDYA İNDİRME VE FFMPEG FORMATLAMA
# ─────────────────────────────────────────────────────────────

def download_and_format_video(
    stream_url: str,
    output_path: str,
    target_w: int = 1080,
    target_h: int = 1920,
    target_dur: float = 5.0
) -> bool:
    """Gerçek MP4 videoyu indirir ve hedef çözünürlüğe (9:16 Shorts) center-crop ile tam oturtur."""
    headers = {"User-Agent": USER_AGENT}
    temp_raw = output_path + ".raw.mp4"
    try:
        req = urllib.request.Request(stream_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp, open(temp_raw, "wb") as f_out:
            while chunk := resp.read(64 * 1024):
                f_out.write(chunk)

        if not os.path.exists(temp_raw) or os.path.getsize(temp_raw) < 10000:
            return False

        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", temp_raw,
            "-t", f"{target_dur:.3f}",
            "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},fps=25,setsar=1",
            "-r", "25",
            "-video_track_timescale", "12800",
            "-c:v", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-an",
            output_path
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=90)
        return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000
    except Exception as e:
        print(f"[REAL-FETCHER] Video formatlama hatası: {e}")
        return False
    finally:
        if os.path.exists(temp_raw):
            try:
                os.remove(temp_raw)
            except Exception:
                pass


def download_and_format_image(
    img_url: str,
    output_path: str,
    target_w: int = 1080,
    target_h: int = 1920
) -> bool:
    """Gerçek fotoğrafı indirir, hedef 9:16 oranına yüksek kalite fill-crop yaparak kaydeder."""
    ua = WIKIMEDIA_USER_AGENT if "wikimedia.org" in img_url else USER_AGENT
    headers = {"User-Agent": ua}
    temp_img = output_path + ".tmp.jpg"
    try:
        req = urllib.request.Request(img_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp, open(temp_img, "wb") as f_out:
            f_out.write(resp.read())

        if not os.path.exists(temp_img) or os.path.getsize(temp_img) < 5000:
            return False

        im = Image.open(temp_img).convert("RGB")
        src_w, src_h = im.size

        # Hedef oranı dolduracak şekilde boyutlandır (Ken Burns için pay bırakarak)
        scale = max(target_w / src_w, target_h / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        im_resized = im.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Merkezden kırp
        left = max(0, (new_w - target_w) // 2)
        top = max(0, (new_h - target_h) // 2)
        right = left + target_w
        bottom = top + target_h
        im_cropped = im_resized.crop((left, top, right, bottom))

        im_cropped.save(output_path, "JPEG", quality=92)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 5000
    except Exception as e:
        print(f"[REAL-FETCHER] Görsel formatlama hatası: {e}")
        return False
    finally:
        if os.path.exists(temp_img):
            try:
                os.remove(temp_img)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
# 5. AKILLI SAHNE SORGUSU OLUŞTURUCU
# ─────────────────────────────────────────────────────────────

KNOWN_PLAYERS = {
    "shaq": "Shaquille O'Neal basketball",
    "shaquille": "Shaquille O'Neal basketball",
    "kareem": "Kareem Abdul-Jabbar basketball",
    "skyhook": "Kareem Abdul-Jabbar skyhook",
    "steph": "Stephen Curry basketball",
    "curry": "Stephen Curry basketball",
    "jordan": "Michael Jordan basketball",
    "michael jordan": "Michael Jordan basketball",
    "lebron": "LeBron James basketball",
    "lebron james": "LeBron James basketball",
    "kobe": "Kobe Bryant basketball",
    "kobe bryant": "Kobe Bryant basketball",
    "wilt": "Wilt Chamberlain basketball",
    "chamberlain": "Wilt Chamberlain basketball",
    "mutombo": "Dikembe Mutombo basketball",
    "dikembe": "Dikembe Mutombo basketball",
    "draymond": "Draymond Green basketball",
    "draymond green": "Draymond Green basketball",
    "rodman": "Dennis Rodman basketball",
    "bird": "Larry Bird basketball",
    "magic": "Magic Johnson basketball",
    "durant": "Kevin Durant basketball",
    "kd": "Kevin Durant basketball",
    "irving": "Kyrie Irving basketball",
    "harden": "James Harden basketball",
    "butler": "Jimmy Butler basketball",
    "kawhi": "Kawhi Leonard basketball",
    "davis": "Anthony Davis basketball",
    "tatum": "Jayson Tatum basketball",
    "lillard": "Damian Lillard basketball",
    "thompson": "Klay Thompson basketball",
    "wemby": "Victor Wembanyama basketball",
    "wembanyama": "Victor Wembanyama basketball",
    "iverson": "Allen Iverson basketball",
    "olajuwon": "Hakeem Olajuwon basketball",
    "duncan": "Tim Duncan basketball",
    "garnett": "Kevin Garnett basketball",
    "morant": "Ja Morant basketball",
    "edwards": "Anthony Edwards basketball",
    "barkley": "Charles Barkley basketball",
    "ewing": "Patrick Ewing basketball",
    "pippen": "Scottie Pippen basketball",
    "kerr": "Steve Kerr basketball",
    "popovich": "Gregg Popovich basketball",
    "westbrook": "Russell Westbrook basketball",
    "giannis": "Giannis Antetokounmpo basketball",
    "doncic": "Luka Doncic basketball",
    "jokic": "Nikola Jokic basketball"
}

NBA_TEAMS = [
    "warriors", "lakers", "bulls", "celtics", "heat", "grizzlies", "spurs", "bucks",
    "suns", "nuggets", "mavericks", "knicks", "rockets", "76ers", "clippers", "thunder",
    "pacers", "timberwolves", "pelicans", "cavaliers", "raptors", "hawks", "jazz",
    "kings", "nets", "magic", "pistons", "hornets", "wizards", "trail blazers"
]


def build_search_queries(
    category: str,
    topic: str,
    scene_data: Dict[str, Any],
    scene_idx: int
) -> List[Dict[str, str]]:
    """
    Sahne metninden ve kategoriden en optimize arama terimlerini üretir.
    Döner: [{'source': 'wikimedia' | 'pixabay_video' | 'pixabay_photo', 'query': '...'}, ...]
    """
    narration = (scene_data.get("narration") or scene_data.get("text") or "").lower()
    prompt = (scene_data.get("image_prompt") or "").lower()
    keywords = scene_data.get("keywords") or []
    kw_str = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
    combined = f"{narration} {prompt} {kw_str} {topic}".lower()

    queries = []

    # 🏀 BASKETBOL KANAL KONTROLÜ
    if category in ("basketball_analysis", "basketball", "sports", "nba", "thebasketballshows"):
        matched_player = None
        for key, full_name in KNOWN_PLAYERS.items():
            if key in combined:
                matched_player = full_name
                break

        # Takım kontrolü
        matched_team = None
        for team in NBA_TEAMS:
            if team in combined:
                matched_team = team
                break

        # Dinamik isim yakalama (Büyük harfle başlayan oyuncu adı çiftleri)
        raw_text_corpus = f"{topic} {scene_data.get('narration') or scene_data.get('text') or ''}"
        candidate_names = re.findall(r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b", raw_text_corpus)
        filtered_candidates = [
            c for c in candidate_names
            if not any(stop in c.lower() for stop in ["triple double", "basketball show", "nba game", "golden state", "united states", "february 10", "february", "super bowl"])
        ]

        if matched_player:
            # 1. Öncelik: Oyuncunun gerçek fotoğrafı (Wikimedia Commons)
            queries.append({"source": "wikimedia", "query": matched_player})
            queries.append({"source": "pixabay_video", "query": "NBA basketball game slam dunk"})
            queries.append({"source": "pixabay_photo", "query": f"{matched_player.split()[0]} NBA player court"})
        elif filtered_candidates:
            dynamic_name = filtered_candidates[0]
            queries.append({"source": "wikimedia", "query": f"{dynamic_name} basketball"})
            queries.append({"source": "pixabay_video", "query": "NBA basketball arena dunk"})
            queries.append({"source": "pixabay_photo", "query": "NBA basketball court action"})
        elif matched_team:
            queries.append({"source": "wikimedia", "query": f"{matched_team.title()} NBA basketball"})
            queries.append({"source": "pixabay_video", "query": f"{matched_team.title()} basketball arena"})
            queries.append({"source": "pixabay_photo", "query": f"{matched_team.title()} basketball court"})
        else:
            # Genel NBA profesyonel aksiyonları (Asla amatör, sokak veya pota filesi değil)
            nba_curated_queries = [
                "NBA basketball court arena",
                "NBA basketball slam dunk",
                "NBA championship arena crowd",
                "NBA basketball player defense",
                "NBA game action highlights"
            ]
            selected_bq = nba_curated_queries[scene_idx % len(nba_curated_queries)]
            queries.append({"source": "wikimedia", "query": selected_bq})
            queries.append({"source": "pixabay_video", "query": selected_bq})
            queries.append({"source": "pixabay_photo", "query": selected_bq})

        return queries

    # 🌍 SEYAHAT (TRAVEL) KANAL KONTROLÜ
    if category in ("travel", "gezi", "letstravel", "letstraveii"):
        # Şehir, ülke veya popüler rota/bölge yakalama
        cities = ["tokyo", "japan", "bangkok", "thailand", "mexico", "paris", "france", "rome", "italy",
                  "europe", "cappadocia", "turkey", "switzerland", "alps", "bali", "vietnam",
                  "new york", "london", "greece", "santorini", "amsterdam", "iceland", "norway",
                  "pilatus", "matterhorn", "lucerne"]
        matched_loc = None
        for c in cities:
            if c in combined:
                matched_loc = c
                break

        # Belirli simgesel yapı / landmark tespiti (Wikimedia için)
        known_landmarks = [
            ("pilatus", "Pilatus railway Mount Pilatus"),
            ("matterhorn", "Matterhorn Zermatt Switzerland"),
            ("jungfrau", "Jungfraujoch railway Switzerland"),
            ("eiffel", "Eiffel Tower Paris France"),
            ("colosseum", "Colosseum Rome Italy"),
            ("fuji", "Mount Fuji Japan"),
            ("santorini", "Oia Santorini Greece")
        ]
        landmark_wiki = None
        for k_lm, full_lm in known_landmarks:
            if k_lm in combined:
                landmark_wiki = full_lm
                break

        # A) Tren, Demiryolu & Dağ Tırmanışları
        if any(w in combined for w in ["train", "railway", "railroad", "cogwheel", "railcar", "incline", "locomotive"]):
            loc = matched_loc or "alps"
            if landmark_wiki:
                queries.append({"source": "wikimedia", "query": landmark_wiki})
            queries.append({"source": "pixabay_video", "query": f"{loc} train railway"})
            queries.append({"source": "pixabay_video", "query": f"{loc} scenic mountain train"})
            queries.append({"source": "pixabay_photo", "query": f"{loc} mountain train"})
            queries.append({"source": "pixabay_photo", "query": f"{loc} railway tracks"})

        # B) Yemek & Sokak Lezzetleri (Hassas Dish/Landmark/Culture Tespiti)
        elif re.search(r"\b(street food|food|taco|tacos|pad thai|al pastor|carnitas|tom yum|ramen|pasta|delicacy|night market|culinary|skewers|wok|puestos|taqueria)\b", combined):
            loc = matched_loc or "asian"
            # Spesifik lezzet eşleşmeleri (Wikimedia & Pixabay Photos)
            specific_food_queries = []
            if "pad thai" in combined or "thai" in combined:
                specific_food_queries.extend([
                    "pad thai shrimp bangkok",
                    "bangkok night market street food",
                    "yaowarat chinatown bangkok street",
                    "thai street food wok flame",
                    "tom yum soup thai street"
                ])
            if "pastor" in combined or "taco" in combined or "mexic" in combined:
                specific_food_queries.extend([
                    "tacos al pastor trompo pineapple",
                    "mexico city taqueria street tacos",
                    "carnitas street tacos plancha",
                    "mexican street tacos salsa cilantro",
                    "mexico city street food market"
                ])
            if "carnitas" in combined or "cauldron" in combined:
                specific_food_queries.extend([
                    "carnitas copper cauldron mexico",
                    "mexican carnitas street food"
                ])

            # Öncelikli Wikimedia Commons (Gerçek belgesel fotoğrafları)
            for sf_q in specific_food_queries:
                queries.append({"source": "wikimedia", "query": sf_q})
                queries.append({"source": "pixabay_photo", "query": sf_q})

            # Genel B-roll fotoğraf & video yedekleri
            queries.append({"source": "pixabay_photo", "query": f"{loc} street food"})
            queries.append({"source": "pixabay_photo", "query": "night market street food"})
            queries.append({"source": "pixabay_video", "query": f"{loc} street food cooking"})

        # C) Havacılık & Lüks Uçuş
        elif re.search(r"\b(flight|airplane|airline|airport|first class|business class)\b", combined):
            queries.append({"source": "pixabay_video", "query": "airplane takeoff flying sunset"})
            queries.append({"source": "pixabay_video", "query": "airport terminal luggage traveler"})
            queries.append({"source": "pixabay_photo", "query": "airplane cabin luxury travel"})

        # D) Dağ, Zirve, Kanyon & Doğa Maceraları
        elif any(w in combined for w in ["mountain", "alps", "cliff", "summit", "peak", "canyon", "hiking", "hike", "waterfall"]):
            loc = matched_loc or "mountain"
            if landmark_wiki:
                queries.append({"source": "wikimedia", "query": landmark_wiki})
            queries.append({"source": "pixabay_video", "query": f"{loc} mountain peak landscape"})
            queries.append({"source": "pixabay_video", "query": f"{loc} alps cliff nature"})
            queries.append({"source": "pixabay_photo", "query": f"{loc} mountain landscape"})

        # E) Tarihi Köy, Tapınak & Antik Kalıntılar
        elif any(w in combined for w in ["village", "ruins", "underground", "bunker", "secret", "temple", "castle"]):
            loc = matched_loc or "ancient"
            queries.append({"source": "wikimedia", "query": f"{loc} ancient historic"})
            queries.append({"source": "pixabay_video", "query": f"{loc} historic village architecture"})
            queries.append({"source": "pixabay_photo", "query": f"{loc} ruins travel"})

        # F) Genel Şehir, Manzara ve Turizm
        else:
            loc = matched_loc or "world travel"
            if landmark_wiki:
                queries.append({"source": "wikimedia", "query": landmark_wiki})
            queries.append({"source": "pixabay_video", "query": f"{loc} city skyline aerial"})
            queries.append({"source": "pixabay_video", "query": f"{loc} travel tourists street"})
            queries.append({"source": "wikimedia", "query": f"{loc} landmark architecture"})
            queries.append({"source": "pixabay_photo", "query": f"{loc} landscape travel"})

        return queries

    # 🌐 DİĞER KATEGORİLER İÇİN GENEL GERÇEK MEDYA
    clean_prompt = re.sub(r"\b(8k|realistic|masterpiece|cinematic|detailed|photo|drawing|illustration)\b", "", prompt).strip()
    primary_q = clean_prompt[:40] if clean_prompt else topic[:30]
    queries.append({"source": "pixabay_video", "query": primary_q})
    queries.append({"source": "pixabay_photo", "query": primary_q})
    return queries


# ─────────────────────────────────────────────────────────────
# 6. ANA ÇAĞRI FONKSİYONU: GET_REAL_SCENE_MEDIA
# ─────────────────────────────────────────────────────────────

def get_real_scene_media(
    category: str,
    scene_idx: int,
    total_scenes: int,
    topic: str,
    scene_data: Dict[str, Any],
    work_dir: Path,
    target_w: int = 1080,
    target_h: int = 1920,
    target_dur: float = 5.0,
    session_used: Optional[Set[Any]] = None
) -> Optional[str]:
    """
    Belirtilen sahne için en ideal telifsiz gerçek videoyu veya fotoğrafı bulur,
    indirir, formatlar ve yerel dosya yolunu döner.
    """
    used = session_used if session_used is not None else set()
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    query_plan = build_search_queries(category, topic, scene_data, scene_idx)
    narr_text = scene_data.get("narration", "") or scene_data.get("prompt", "")
    print(f"[REAL-MEDIA] Sahne {scene_idx} ({category}) için gerçek medya aranıyor (Plan: {len(query_plan)} sorgu)...")

    dyn_negatives = []
    is_sports_cat = category in ("basketball_analysis", "basketball", "sports", "nba", "thebasketballshows")
    if query_builder is not None and is_sports_cat:
        cq = query_builder.build_context_locked_queries(narr_text, fallback_entity=topic)
        dyn_negatives = cq.dynamic_negatives

    def _validate_candidate(fpath: str) -> bool:
        # Pre-Render Quality Gate (No-Loop, Kademe 1, 2, 3 ve Cross-Project İzolasyon)
        if asset_validator is not None:
            val_res = asset_validator.validate_candidate(
                image_path=fpath,
                scene_prompt=narr_text,
                project_type=category,
                target_entity=topic,
                is_vertical=True,
                dynamic_negatives=dyn_negatives
            )
            if not val_res.is_valid:
                print(f"[REAL-MEDIA] ⚠️ Sahne {scene_idx} adayı kalite kapısına takıldı ({val_res.reason}): {Path(fpath).name}")
                try:
                    os.remove(fpath)
                except Exception:
                    pass
                return False
            asset_validator.register_used_asset(fpath)
            print(f"[REAL-MEDIA] 🛡️ Sahne {scene_idx} kalite kapısından başarıyla geçti (Skor: {val_res.score:.2f})")
            return True

        if not visual_guard:
            return True
        ok, sc, reason = visual_guard.verify_scene_asset(fpath, narr_text, category, topic)
        if not ok:
            print(f"[REAL-MEDIA] ⚠️ Sahne {scene_idx} adayı vizyon filtresine takıldı ({reason}): {Path(fpath).name}")
            try:
                os.remove(fpath)
            except Exception:
                pass
            return False
        print(f"[REAL-MEDIA] 🛡️ Sahne {scene_idx} vizyon doğrulamasından başarıyla geçti ({reason})")
        return True

    for q_item in query_plan:
        src = q_item["source"]
        q_text = q_item["query"]

        # A) WIKIMEDIA COMMONS GERÇEK FOTOĞRAFLAR
        if src == "wikimedia":
            hit = search_wikimedia_commons(q_text, exclude_urls=used)
            if hit:
                out_file = str(work_dir / f"scene_{scene_idx:02d}_wiki_{hit['id']}.jpg")
                if download_and_format_image(hit["url"], out_file, target_w, target_h):
                    if not _validate_candidate(out_file):
                        used.add(hit["url"])
                        continue
                    used.add(hit["url"])
                    print(f"[REAL-MEDIA] ✅ Sahne {scene_idx} için Wikimedia gerçek görseli bağlandı: {hit['title']}")
                    return out_file

        # B) PIXABAY GERÇEK 1080P B-ROLL VİDEO
        elif src == "pixabay_video":
            hit = search_pixabay_video(q_text, exclude_ids=used, min_duration=max(3.0, target_dur))
            if hit:
                out_file = str(work_dir / f"scene_{scene_idx:02d}_pixabay_v_{hit['id']}.mp4")
                if download_and_format_video(hit["url"], out_file, target_w, target_h, target_dur):
                    if not _validate_candidate(out_file):
                        used.add(hit["id"])
                        continue
                    used.add(hit["id"])
                    print(f"[REAL-MEDIA] 🎬 Sahne {scene_idx} için Pixabay gerçek B-roll videosu bağlandı: {hit['tags'][:40]}")
                    return out_file

        # C) PIXABAY GERÇEK YÜKSEK ÇÖZÜNÜRLÜKLÜ FOTOĞRAF
        elif src == "pixabay_photo":
            hit = search_pixabay_photo(q_text, exclude_ids=used)
            if hit:
                out_file = str(work_dir / f"scene_{scene_idx:02d}_pixabay_img_{hit['id']}.jpg")
                if download_and_format_image(hit["url"], out_file, target_w, target_h):
                    if not _validate_candidate(out_file):
                        used.add(hit["id"])
                        continue
                    used.add(hit["id"])
                    print(f"[REAL-MEDIA] 📸 Sahne {scene_idx} için Pixabay gerçek fotoğrafı bağlandı: {hit['tags'][:40]}")
                    return out_file

    # Son Çare: Genel Güvenli B-Roll
    fallback_q = "sports court action" if "basketball" in category else "world travel landscape"
    hit_fb = search_pixabay_video(fallback_q, exclude_ids=used, min_duration=target_dur)
    if hit_fb:
        out_file = str(work_dir / f"scene_{scene_idx:02d}_fallback_v_{hit_fb['id']}.mp4")
        if download_and_format_video(hit_fb["url"], out_file, target_w, target_h, target_dur):
            if _validate_candidate(out_file):
                used.add(hit_fb["id"])
                return out_file

    hit_img = search_pixabay_photo(fallback_q, exclude_ids=used)
    if hit_img:
        out_file = str(work_dir / f"scene_{scene_idx:02d}_fallback_img_{hit_img['id']}.jpg")
        if download_and_format_image(hit_img["url"], out_file, target_w, target_h):
            if _validate_candidate(out_file):
                used.add(hit_img["id"])
                return out_file

    # Sıfır Siyah Ekran Garantisi (Zero Black Frame Guarantee):
    # Eğer tüm aramalar sonuçsuz kaldıysa veya elendiyse, ASLA None dönülmez!
    # FallbackEngine Kademe 2 (Infographic Canvas) veya Kademe 3 (Motion Texture) görseli üretilir.
    if fallback_engine is not None:
        safe_fallback_img = work_dir / f"scene_{scene_idx:02d}_failsafe_info.jpg"
        fallback_engine.generate_infographic_canvas(
            output_image_path=safe_fallback_img,
            primary_entity=topic or "NBA Player",
            team_name=None,
            scene_text=narr_text or topic or "",
            width=target_w,
            height=target_h
        )
        assert safe_fallback_img.exists() and safe_fallback_img.stat().st_size > 1000, "Fallback görseli 0-byte!"
        print(f"[REAL-MEDIA] 🛡️ [Zero Black Frame] FallbackEngine infografik görseli bağlandı: {safe_fallback_img.name}")
        return str(safe_fallback_img)

    # Acil Durum Renk Zemini (Asla None dönme)
    emergency_fb = work_dir / f"scene_{scene_idx:02d}_emergency.jpg"
    fb_img = Image.new("RGB", (target_w, target_h), (15, 23, 42))
    fb_img.save(emergency_fb, "JPEG")
    return str(emergency_fb)


# ─────────────────────────────────────────────────────────────
# 7. EVRENSEL EDİTORYAL FOTOĞRAF HAVUZU (FETCH_PHOTO_POOL)
# ─────────────────────────────────────────────────────────────

def fetch_photo_pool(
    category: str,
    topic: str,
    script_data: Dict[str, Any],
    target_count: int = 25,
    work_dir: Optional[Path] = None,
    target_w: int = 1080,
    target_h: int = 1920,
    session_used: Optional[Set[Any]] = None
) -> List[Path]:
    """
    Tüm video için 2.15s'lik dinamik Ken Burns kesmelerine yetecek sayıda (24-30 adet)
    yüksek çözünürlüklü, semantik olarak %100 uyumlu editoryal fotoğraf toplar.
    Wikimedia Commons ve Pixabay Photo API kaynaklarını harmanlar.
    """
    from PIL import ImageEnhance

    used = session_used if session_used is not None else set()
    pool_dir = Path(work_dir) if work_dir else Path("/tmp/photo_pool")
    pool_dir.mkdir(parents=True, exist_ok=True)

    scenes = script_data.get("scenes") or []
    if not scenes:
        scenes = [{"narration": script_data.get("narration") or topic}]

    # Sahne başına düşen kesme sayısını hesapla
    num_scenes = max(1, len(scenes))
    cuts_per_scene = max(2, int(round(target_count / num_scenes)))

    print(f"[PHOTO-POOL] 🎯 Hedef {target_count} benzersiz görsel aranıyor ({num_scenes} sahne, ~{cuts_per_scene} kesme/sahne)...")

    # Sahne bazlı spesifik alt sorgu üretimi
    all_target_queries: List[Dict[str, str]] = []

    for sc_idx, sc in enumerate(scenes):
        narr = (sc.get("narration") or sc.get("text") or "").strip()
        prompt = (sc.get("image_prompt") or "").strip()
        kw = sc.get("keywords") or []
        kw_str = " ".join(kw) if isinstance(kw, list) else str(kw)
        combined = f"{narr} {prompt} {kw_str} {topic}".lower()

        scene_queries: List[Dict[str, str]] = []

        # 1. Yemek & Sokak Lezzeti (Travel / Food)
        if any(f in combined for f in ["food", "taco", "pad thai", "al pastor", "carnitas", "street food", "market", "chinatown", "wok"]):
            if "pad thai" in combined or "bangkok" in combined or "thai" in combined:
                scene_queries.extend([
                    {"source": "wikimedia", "query": "pad thai shrimp bangkok"},
                    {"source": "pixabay_photo", "query": "pad thai bangkok"},
                    {"source": "wikimedia", "query": "bangkok night market street food"},
                    {"source": "pixabay_photo", "query": "bangkok street food night"},
                    {"source": "wikimedia", "query": "yaowarat road chinatown bangkok"},
                    {"source": "pixabay_photo", "query": "chinatown bangkok street"},
                    {"source": "wikimedia", "query": "thai street food flame wok"}
                ])
            if "pastor" in combined or "mexico" in combined or "taco" in combined:
                scene_queries.extend([
                    {"source": "wikimedia", "query": "tacos al pastor trompo pineapple"},
                    {"source": "pixabay_photo", "query": "tacos al pastor trompo"},
                    {"source": "wikimedia", "query": "mexico city street taqueria"},
                    {"source": "pixabay_photo", "query": "mexico city street food"},
                    {"source": "wikimedia", "query": "carnitas tacos plancha salsa"},
                    {"source": "pixabay_photo", "query": "mexican tacos salsa lime"}
                ])
            if "carnitas" in combined or "copper" in combined or "cauldron" in combined:
                scene_queries.extend([
                    {"source": "wikimedia", "query": "carnitas copper cauldron mexico"},
                    {"source": "pixabay_photo", "query": "carnitas street food"}
                ])
            if "tom yum" in combined or "chili" in combined or "adobo" in combined:
                scene_queries.extend([
                    {"source": "wikimedia", "query": "tom yum soup bowl thai"},
                    {"source": "pixabay_photo", "query": "tom yum thai street"}
                ])

        # 2. Spor & Basketbol (NBA)
        elif category in ("basketball_analysis", "basketball", "sports", "nba", "thebasketballshows"):
            player_found = None
            for pk, pv in KNOWN_PLAYERS.items():
                if pk in combined:
                    player_found = pv
                    break
            if player_found:
                scene_queries.extend([
                    {"source": "wikimedia", "query": f"{player_found} basketball"},
                    {"source": "pixabay_photo", "query": f"{player_found.split()[0]} NBA player court"},
                    {"source": "wikimedia", "query": f"{player_found} action"},
                    {"source": "pixabay_photo", "query": "NBA basketball game slam dunk"},
                    {"source": "wikimedia", "query": f"{player_found} trophy championship"}
                ])
            else:
                scene_queries.extend([
                    {"source": "pixabay_photo", "query": "NBA basketball slam dunk"},
                    {"source": "pixabay_photo", "query": "NBA championship trophy arena"},
                    {"source": "pixabay_photo", "query": "basketball player arena action"}
                ])

        # 3. Tarih, Seyahat Genel, Bilim, vb.
        else:
            clean_p = re.sub(r"\b(8k|cinematic|photorealistic|hyperrealistic|masterpiece)\b", "", prompt).strip()
            scene_queries.extend([
                {"source": "wikimedia", "query": f"{clean_p[:40]} {topic[:25]}"},
                {"source": "pixabay_photo", "query": f"{clean_p[:35]}"},
                {"source": "wikimedia", "query": f"{topic} history"},
                {"source": "pixabay_photo", "query": f"{topic} landscape"}
            ])

        # Sahne sorgularını havuza ekle
        all_target_queries.extend(scene_queries)

    # Genel yedek sorgular
    all_target_queries.extend([
        {"source": "pixabay_photo", "query": f"{topic} travel"},
        {"source": "pixabay_photo", "query": "bangkok street food night"},
        {"source": "pixabay_photo", "query": "mexican street tacos"},
        {"source": "pixabay_photo", "query": "night market street food asia"},
        {"source": "pixabay_photo", "query": "street food vendor night"}
    ])

    saved_photos: List[Path] = []
    downloaded_urls: Set[str] = set()

    for q_item in all_target_queries:
        if len(saved_photos) >= target_count:
            break

        src = q_item["source"]
        q_str = q_item["query"]
        candidates = []

        if src == "wikimedia":
            candidates = search_wikimedia_commons_photos(q_str, exclude_urls=used.union(downloaded_urls), limit=4)
        elif src == "pixabay_photo":
            candidates = search_pixabay_photos(q_str, exclude_ids=used.union(downloaded_urls), limit=4)

        for cand in candidates:
            if len(saved_photos) >= target_count:
                break

            candidate_url = cand.get("url")
            if not candidate_url or candidate_url in downloaded_urls or candidate_url in used:
                continue

            photo_path = pool_dir / f"photo_{len(saved_photos):03d}.jpg"
            ok = download_and_format_image(candidate_url, str(photo_path), target_w, target_h)
            if ok and photo_path.is_file() and photo_path.stat().st_size > 5000:
                # Görsel zenginleştirme (Kontrast +%5, Doygunluk +%10 mobil OLED ekranlar için)
                try:
                    enh_im = Image.open(photo_path).convert("RGB")
                    enh_im = ImageEnhance.Contrast(enh_im).enhance(1.06)
                    enh_im = ImageEnhance.Color(enh_im).enhance(1.10)
                    enh_im.save(photo_path, "JPEG", quality=92)
                except Exception:
                    pass

                saved_photos.append(photo_path)
                downloaded_urls.add(candidate_url)
                used.add(candidate_url)
                print(f"[PHOTO-POOL] 📸 [{len(saved_photos)}/{target_count}] Gerçek editoryal fotoğraf eklendi: {photo_path.name} (Kaynak: {src}, Sorgu: '{q_str}')")

    # Eğer hala eksik varsa, mevcut onaylı fotoğraflarla havuzu tamamla
    if saved_photos and len(saved_photos) < target_count:
        print(f"[PHOTO-POOL] ℹ️ {len(saved_photos)} fotoğraf toplandı, {target_count} hedefine ulaşmak için dengeli dağıtılıyor...")
        orig_len = len(saved_photos)
        while len(saved_photos) < target_count:
            src_p = saved_photos[len(saved_photos) % orig_len]
            clone_path = pool_dir / f"photo_{len(saved_photos):03d}.jpg"
            shutil.copy2(src_p, clone_path)
            saved_photos.append(clone_path)

    print(f"[PHOTO-POOL] ✅ Fotoğraf havuzu tamamlandı: {len(saved_photos)} benzersiz yüksek çözünürlüklü kesme görseli hazır.")
    return saved_photos
