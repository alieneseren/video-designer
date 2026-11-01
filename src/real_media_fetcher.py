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

def search_pixabay_photo(
    query: str,
    exclude_ids: Optional[Set[int]] = None,
    image_type: str = "photo"
) -> Optional[Dict[str, Any]]:
    """Pixabay Fotoğraf API'den yüksek çözünürlüklü gerçek fotoğraf arar."""
    api_key = get_pixabay_key()
    if not api_key:
        return None

    clean_q = re.sub(r"[^\w\s-]", "", query).strip()
    if not clean_q:
        clean_q = "travel destination"

    params = {
        "key": api_key,
        "q": clean_q,
        "image_type": image_type,
        "safesearch": "true",
        "per_page": 15
    }
    url = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": USER_AGENT}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[REAL-FETCHER] Pixabay fotoğraf sorgu hatası ('{clean_q}'): {e}")
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

    if not candidates:
        return None

    return random.choice(candidates[:3])


# ─────────────────────────────────────────────────────────────
# 3. WIKIMEDIA COMMONS ARAMA (Sporcular, Tarihi Anıtlar, Şehirler)
# ─────────────────────────────────────────────────────────────

def search_wikimedia_commons(
    query: str,
    exclude_urls: Optional[Set[str]] = None,
    limit: int = 8
) -> Optional[Dict[str, Any]]:
    """Wikimedia Commons API'den kamu malı / Creative Commons gerçek fotoğraf arar."""
    clean_q = re.sub(r"[^\w\s-]", "", query).strip()
    if not clean_q:
        return None

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": clean_q,
        "gsrnamespace": 6,  # File: namespace
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|mime"
    }
    url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": USER_AGENT}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[REAL-FETCHER] Wikimedia Commons sorgu hatası ('{clean_q}'): {e}")
        return None

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None

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

        img_url = info.get("url")
        if not img_url or img_url in exclude:
            continue

        candidates.append({
            "id": pid,
            "title": title,
            "url": img_url,
            "width": w,
            "height": h
        })

    if not candidates:
        return None

    return candidates[0]  # En alakalı ilk sonuç


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
    headers = {"User-Agent": USER_AGENT}
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

        # B) Yemek & Sokak Lezzetleri (Kelime sınırları ile hassas kontrol - 'seats' ile karışmaz)
        elif re.search(r"\b(street food|food|taco|pad thai|ramen|pasta|delicacy|night market|culinary)\b", combined):
            loc = matched_loc or "asian"
            queries.append({"source": "pixabay_video", "query": f"{loc} street food cooking"})
            queries.append({"source": "pixabay_video", "query": "night market street food"})
            queries.append({"source": "pixabay_photo", "query": f"{loc} food market"})

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
    if query_builder is not None:
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
