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
WIKIMEDIA_USER_AGENT = "TravelShortsBot/3.1 (https://github.com/alieneseren/video-designer; contact@alieneseren.com) Python-urllib/3.10"


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
# ─────────────────────────────────────────────────────────────
# 2. PİXABAY VE WIKIMEDIA NEGATİF FİLTRELERİ
# ─────────────────────────────────────────────────────────────

UNWANTED_PHOTO_KEYWORDS = [
    # Tabela, reklam panosu, otopark, vitrin yazıları (Pancho Villa vb. hataları önler)
    "billboard", "parking lot", "car park", "signboard", "road sign",
    "restaurant & bar sign", "storefront sign", "advertisement", "ad sign",
    "neon sign", "building sign", "street sign", "highway sign", "traffic sign",
    "facade sign", "commercial sign", "parking", "pancho villa",
    "business sign", "store sign", "shop sign", "retail sign",
    # Telefon kamera filigranları & tarih damgaları (Redmi, Xiaomi, Mi Note, kamera stamp)
    "shot on", "mi note", "redmi", "xiaomi", "watermark", "datestamp", "timestamp",
    "copyright", "alamy", "getty", "stock photo", "shutterstock", "depositphotos",
    "dreamstime", "istock", "camera model",
    # Havacılıkta müze balon kapsülleri, tarihi arşiv & siyah-beyaz (Modern uçuş güvenliğinde elenir)
    "gondola", "capsule", "breitling", "orbiter", "museum display", "museum exhibit",
    "vintage 19", "black and white", "bw photo", "monochrome", "balloon", "hot air balloon",
    "glider", "propeller plane", "biplane", "model plane", "toy plane", "miniature",
    # Ofis, masa, plastik bardak, paket yemek, ev yemeği
    "office", "desk", "cubicle", "keyboard", "computer", "laptop",
    "plastic cup", "disposable cup", "paper cup", "water cup", "coffee cup",
    "styrofoam", "takeout", "takeaway", "cafeteria", "canteen", "lunchbox",
    "bento", "indoor meal", "dining room table", "homemade", "recipe",
    # Düşük kalite, şemalar, haritalar, vektörler
    "diagram", "infographic", "drawing", "clipart", "illustration", "vector",
    "map of", "floor plan", "logo", "icon", "symbol", "thumbnail", "banner",
    "low resolution", "blurry", "scan", "cctv", "vendor by night", "6962509412",
    "stool", "red stool", "plastic stool"
]

def is_unwanted_asset(title: str, tags: str = "") -> bool:
    """İstenmeyen reklam panoları, tabelalar veya şemaları filtreler."""
    text = f"{title} {tags}".lower()
    return any(bad in text for bad in UNWANTED_PHOTO_KEYWORDS)


# ─────────────────────────────────────────────────────────────
# 3. PİXABAY FOTOĞRAF ARAMA
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
        tags = h.get("tags", "")
        if is_unwanted_asset("", tags):
            continue
        img_url = h.get("largeImageURL") or h.get("fullHDURL") or h.get("webformatURL")
        if not img_url:
            continue

        candidates.append({
            "id": hid,
            "url": img_url,
            "width": h.get("imageWidth", 1920),
            "height": h.get("imageHeight", 1080),
            "tags": tags
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
    import time
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
        "iiurlwidth": 1920
    }
    url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": WIKIMEDIA_USER_AGENT}

    data = {}
    time.sleep(0.35)
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(1.2)
                continue
            print(f"[REAL-FETCHER] Wikimedia Commons sorgu hatası ('{clean_q}'): {e}")
            return []
        except Exception as e:
            print(f"[REAL-FETCHER] Wikimedia Commons sorgu hatası ('{clean_q}'): {e}")
            return []

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return []

    exclude = exclude_urls or set()
    candidates = []
    seen_base_titles = set()

    for pid, page in pages.items():
        title = page.get("title", "")
        t_low = title.lower()

        # İkon, ses, svg ve logoları ele
        if any(skip in t_low for skip in [".svg", ".ogg", ".oga", ".pdf", "flag", "icon", "logo", "symbol"]):
            continue

        # Tabela, reklam panoları, ofis/masa ve otopark görsellerini ele
        if is_unwanted_asset(title, ""):
            continue

        # Seri çekim yüklemelerini tekilleştir (örn. Pad Thai (1).jpg vs Pad Thai (2).jpg)
        base_stem = re.sub(r"[\s_-]*\(\d+\)|[\s_-]*\d+$", "", title, flags=re.IGNORECASE).strip().lower()
        if base_stem in seen_base_titles:
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
        # Minimum 720p/1080p kalite standardı (en az 1280x720 ve 1.2MP)
        if w < 1280 or h < 720 or (w * h < 1_200_000):
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
        seen_base_titles.add(base_stem)
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


def calculate_sharpness(pil_img: Image.Image) -> float:
    """Calculates Laplacian edge intensity variance to reject blurry/low-res photos."""
    try:
        import numpy as np
        from PIL import ImageFilter
        im = pil_img.convert("L")
        kernel = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=0)
        lap = im.filter(kernel)
        arr = np.array(lap, dtype=np.float32)
        return float(arr.var())
    except Exception:
        from PIL import ImageFilter, ImageStat
        im = pil_img.convert("L")
        edges = im.filter(ImageFilter.FIND_EDGES)
        return float(ImageStat.Stat(edges).var[0])


def calculate_dhash(image: Image.Image, hash_size: int = 8) -> int:
    """Computes a 64-bit difference hash (dHash) for visual perceptual comparison."""
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.get_flattened_data() if hasattr(resized, "get_flattened_data") else resized.getdata())
    val = 0
    idx = 0
    for row in range(hash_size):
        for col in range(hash_size):
            p_left = pixels[row * (hash_size + 1) + col]
            p_right = pixels[row * (hash_size + 1) + col + 1]
            if p_left > p_right:
                val |= (1 << idx)
            idx += 1
    return val


def hamming_distance(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count("1")


def download_and_format_image(
    img_url: str,
    output_path: str,
    target_w: int = 1080,
    target_h: int = 1920
) -> bool:
    """Gerçek fotoğrafı indirir, çözünürlük ve netlik testlerinden geçirip hedef 9:16 oranına yüksek kalite fill-crop yaparak kaydeder."""
    if "wikimedia.org" in img_url:
        headers = {"User-Agent": WIKIMEDIA_USER_AGENT}
    elif "pixabay.com" in img_url:
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://pixabay.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        }
    else:
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://www.google.com/"
        }

    import time
    time.sleep(0.3)
    temp_img = output_path + ".tmp.jpg"
    for attempt in range(3):
        try:
            req = urllib.request.Request(img_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp, open(temp_img, "wb") as f_out:
                f_out.write(resp.read())

            if not os.path.exists(temp_img) or os.path.getsize(temp_img) < 30000:
                continue

            im = Image.open(temp_img).convert("RGB")
            src_w, src_h = im.size

            # En az 1000px genişlik veya yükseklik olmalı, minimum 0.8MP
            if (src_w < 1000 and src_h < 1000) or (src_w * src_h < 800_000):
                continue

            # Ham görsel bulanıklık filtresi (Laplacian variance >= 32.0; gerçek 240p bulanıklığı elenir, gece/atmosfer korunur)
            sharpness_raw = calculate_sharpness(im)
            if sharpness_raw < 32.0:
                print(f"[REAL-FETCHER] ⚠️ Düşük netlik/bulanık ham görsel elendi (sharpness={sharpness_raw:.1f} < 32): {img_url[:60]}")
                continue

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

            # Dikey 9:16 kırpım alanı netlik denetimi (240p ve aşırı bulanık crop'ları eler)
            sharpness_crop = calculate_sharpness(im_cropped)
            if sharpness_crop < 32.0:
                print(f"[REAL-FETCHER] ⚠️ Dikey 9:16 kırpım sonrası düşük netlik elendi (sharpness={sharpness_crop:.1f} < 32): {img_url[:60]}")
                continue

            im_cropped.save(output_path, "JPEG", quality=92)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
                return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2.0)
            elif attempt == 2:
                print(f"[REAL-FETCHER] Görsel indirme HTTP hatası ({img_url[:60]}...): {e}")
        except Exception as e:
            if attempt == 2:
                print(f"[REAL-FETCHER] Görsel formatlama hatası ({img_url[:60]}...): {e}")
        finally:
            if os.path.exists(temp_img):
                try:
                    os.remove(temp_img)
                except Exception:
                    pass
    return False


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
    session_used: Optional[Set[Any]] = None,
    scene_timeline: Optional[List[Tuple[int, str, float, float]]] = None,
    cut_duration: float = 2.15
) -> List[Path]:
    """
    Tüm video için 2.15s'lik dinamik Ken Burns kesmelerine yetecek sayıda (24-30 adet)
    yüksek çözünürlüklü, semantik olarak %100 uyumlu editoryal fotoğraf toplar.
    Zaman çizgisi (scene_timeline) ile senkronize çalışır; her kesmeye o an anlatılan
    sahnenin tam semantik görselini (Chinatown, Al Pastor trompo, bakır kazan carnitas) atar.
    """
    from PIL import ImageEnhance

    used = session_used if session_used is not None else set()
    pool_dir = Path(work_dir) if work_dir else Path("/tmp/photo_pool")
    pool_dir.mkdir(parents=True, exist_ok=True)

    scenes = script_data.get("scenes") or []
    if not scenes and isinstance(script_data, dict):
        scenes = (script_data.get("script_data") or {}).get("scenes") or (script_data.get("script") or {}).get("scenes") or []
    if not scenes:
        scenes = [{"narration": script_data.get("narration") or topic}]

    num_scenes = max(1, len(scenes))

    # 1. Her kesmenin (cut) zaman çizelgesindeki aktif sahnesini tespit et
    cut_to_scene: List[int] = []
    if scene_timeline and len(scene_timeline) >= num_scenes:
        for cut_i in range(target_count):
            cut_mid = cut_i * cut_duration + (cut_duration / 2.0)
            assigned_sc = 0
            for sc_i, _text, sc_start, sc_end in scene_timeline:
                if sc_start <= cut_mid < sc_end:
                    assigned_sc = sc_i
                    break
            else:
                assigned_sc = min(num_scenes - 1, int(cut_i * num_scenes / target_count))
            cut_to_scene.append(assigned_sc)
    else:
        for cut_i in range(target_count):
            assigned_sc = min(num_scenes - 1, int(cut_i * num_scenes / target_count))
            cut_to_scene.append(assigned_sc)

    print(f"[PHOTO-POOL] 🎯 Hedef {target_count} benzersiz editoryal görsel aranıyor ({num_scenes} sahne, ~{cut_duration}s kesme temposu)...")

    # 2. Sahne bazlı hedef görsel sayıları
    scene_needed_counts = {sc_i: max(1, cut_to_scene.count(sc_i)) for sc_i in range(num_scenes)}
    scene_photos: Dict[int, List[Path]] = {sc_i: [] for sc_i in range(num_scenes)}
    downloaded_urls: Set[str] = set()
    all_downloaded_photos: List[Path] = []
    accepted_video_hashes: List[int] = []

    # 3. Her sahne için özel semantik arama sorguları üret
    for sc_idx, sc in enumerate(scenes):
        needed = scene_needed_counts.get(sc_idx, 4)
        narr = (sc.get("narration") or sc.get("text") or "").strip()
        prompt = (sc.get("image_prompt") or "").strip()
        kw = sc.get("keywords") or []
        kw_str = " ".join(kw) if isinstance(kw, list) else str(kw)
        scene_corpus = f"{narr} {prompt} {kw_str}".lower()
        combined = f"{scene_corpus} {topic}".lower()

        scene_queries: List[Dict[str, str]] = []

        # A) HAVACILIK & UÇAK KABİNİ (Aviation / Flight Safety) - ÖNCELİKLİ KONTROL
        if any(w in combined for w in ["airplane", "airline", "aircraft", "cockpit", "flight", "cabin", "landing", "runway", "plane", "aviation", "evacuate", "takeoff"]):
            if any(w in scene_corpus for w in ["dim", "cabin", "aisle", "light", "interior", "descend", "dark"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "airplane cabin interior night"},
                    {"source": "wikimedia", "query": "aircraft cabin passenger seats"},
                    {"source": "wikimedia", "query": "commercial airplane cabin interior"},
                    {"source": "pixabay_photo", "query": "airplane cabin night"},
                    {"source": "pixabay_photo", "query": "airplane cabin interior"},
                    {"source": "pixabay_photo", "query": "aircraft cabin passenger"}
                ])
            elif any(w in scene_corpus for w in ["takeoff", "landing", "wing", "engine", "runway", "window"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "airplane window night wing"},
                    {"source": "wikimedia", "query": "cockpit night landing runway"},
                    {"source": "wikimedia", "query": "airport runway night"},
                    {"source": "pixabay_photo", "query": "airplane runway lights night"},
                    {"source": "pixabay_photo", "query": "airplane wing sunset flying"},
                    {"source": "pixabay_photo", "query": "airplane takeoff night"}
                ])
            elif any(w in scene_corpus for w in ["eye", "vision", "adapt", "pupil"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "human eye pupil close up"},
                    {"source": "wikimedia", "query": "airplane emergency lighting cabin"},
                    {"source": "pixabay_photo", "query": "eye pupil macro close up"},
                    {"source": "pixabay_photo", "query": "airplane cabin dark night"}
                ])
            elif any(w in scene_corpus for w in ["evacuate", "emergency", "exit", "escape", "obstacle", "slide"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "airplane emergency exit lights cabin"},
                    {"source": "wikimedia", "query": "aircraft passenger emergency door"},
                    {"source": "pixabay_photo", "query": "airplane emergency lighting"},
                    {"source": "pixabay_photo", "query": "airplane cabin dark aisle"}
                ])
            elif any(w in scene_corpus for w in ["attendant", "crew", "overhead", "passenger", "procedure"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "flight attendant cabin aircraft"},
                    {"source": "wikimedia", "query": "passenger aircraft cabin aisle"},
                    {"source": "pixabay_photo", "query": "flight attendant airplane interior"},
                    {"source": "pixabay_photo", "query": "air hostess cabin service"}
                ])
            else:
                scene_queries.extend([
                    {"source": "wikimedia", "query": "airplane cabin interior night"},
                    {"source": "pixabay_photo", "query": "airplane window night wing"},
                    {"source": "wikimedia", "query": "cockpit night landing runway"},
                    {"source": "pixabay_photo", "query": "airplane flight night"}
                ])

        # B) LÜKS SEYAHAT, RESORT & VİLLA (5 Countries / Budget Luxury)
        elif any(w in combined for w in ["live like royalty", "50/day", "fifty dollars", "resort", "resorts", "luxury", "villa", "bali", "vietnam", "sri lanka", "budget"]):
            if sc_idx == 0 or any(w in scene_corpus for w in ["infinity pool", "routine", "fifty dollars", "paradise", "five-star"]):
                scene_queries.extend([
                    {"source": "pixabay_photo", "query": "infinity pool tropical resort luxury"},
                    {"source": "wikimedia", "query": "infinity pool tropical resort"},
                    {"source": "pixabay_photo", "query": "luxury resort swimming pool tropical"},
                    {"source": "pixabay_photo", "query": "luxury villa pool tropical"},
                    {"source": "wikimedia", "query": "tropical resort pool luxury"}
                ])
            elif any(w in scene_corpus for w in ["bali", "vietnam", "villa", "carved", "massage"]):
                scene_queries.extend([
                    {"source": "pixabay_photo", "query": "bali luxury resort villa pool"},
                    {"source": "wikimedia", "query": "bali luxury villa pool"},
                    {"source": "pixabay_photo", "query": "traditional spa herbal massage therapy"},
                    {"source": "pixabay_photo", "query": "vietnam tropical resort beach"},
                    {"source": "pixabay_photo", "query": "ubud bali luxury resort"}
                ])
            elif any(w in scene_corpus for w in ["thailand", "sri lanka", "balcony", "palm", "plantation", "colonial"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "sri lanka tropical resort beach"},
                    {"source": "pixabay_photo", "query": "sri lanka palm beach resort"},
                    {"source": "pixabay_photo", "query": "thailand luxury resort ocean view"},
                    {"source": "pixabay_photo", "query": "phuket luxury resort balcony sea"},
                    {"source": "wikimedia", "query": "sri lanka tea plantation hillside"}
                ])
            elif any(w in scene_corpus for w in ["dining", "hospitality", "beachfront", "pennies", "seafood"]):
                scene_queries.extend([
                    {"source": "pixabay_photo", "query": "luxury beachfront dining table sunset"},
                    {"source": "pixabay_photo", "query": "tropical resort beachfront restaurant dinner"},
                    {"source": "wikimedia", "query": "beachfront restaurant luxury tropical"},
                    {"source": "pixabay_photo", "query": "candlelight beach dinner tropical"}
                ])
            else:
                scene_queries.extend([
                    {"source": "pixabay_photo", "query": "tropical resort sunset panorama traveler"},
                    {"source": "pixabay_photo", "query": "luxury travel destination tropical viewpoint"},
                    {"source": "wikimedia", "query": "tropical beach resort sunset landscape"},
                    {"source": "pixabay_photo", "query": "wooden deck ocean sunset traveler"}
                ])

        # C) BANGKOK VS MEXICO CITY SOKAK LEZZETLERİ (Yalnızca bu konuya özel)
        elif ("bangkok" in topic and "mexico" in topic) or any(w in topic for w in ["pad thai", "al pastor", "carnitas", "yaowarat"]):
            # 0. SCENE 0: HOOK / GİRİŞ ESTABLISHING (İki dev şehir, 8000 mil, showdown)
            if sc_idx == 0 or any(h_word in scene_corpus for h_word in ["eight thousand miles", "8000 miles", "two legendary", "ultimate clash", "crown of the world", "showdown"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "yaowarat road bangkok night"},
                    {"source": "wikimedia", "query": "mexico city historic center night street"},
                    {"source": "wikimedia", "query": "bangkok chinatown night"},
                    {"source": "wikimedia", "query": "mexico city street market night"},
                    {"source": "pixabay_photo", "query": "bangkok night street"},
                    {"source": "pixabay_photo", "query": "mexico city night street"}
                ])
            # 3. SCENE 3: MICHELIN / CARNITAS SIMMERED IN COPPER CAULDRONS (Bakır kazan ve Michelin vurgusu)
            elif any(c_word in scene_corpus for c_word in ["carnitas", "copper", "cauldron", "cazo", "simmered", "michelin"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "carnitas michoacan"},
                    {"source": "wikimedia", "query": "carnitas mexico"},
                    {"source": "wikimedia", "query": "michelin street food bangkok"},
                    {"source": "wikimedia", "query": "carnitas tacos"},
                    {"source": "pixabay_photo", "query": "mexican street food cooking"}
                ])
            # 1. SCENE 1: BANGKOK / MIDNIGHT MARKETS / PAD THAI / JUMBO PRAWNS / 1000 DEGREES WOK
            elif any(b_word in scene_corpus for b_word in ["bangkok", "pad thai", "prawn", "wok", "roar", "thousand degrees", "thai"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "thai street food wok"},
                    {"source": "wikimedia", "query": "bangkok street food night"},
                    {"source": "wikimedia", "query": "bangkok night market street food"},
                    {"source": "wikimedia", "query": "pad thai shrimp"},
                    {"source": "pixabay_photo", "query": "bangkok street food wok flame"}
                ])
            # 2. SCENE 2: MEXICO CITY / AL PASTOR / TENDER PORK / ROASTED PINEAPPLE / SALSAS
            elif any(m_word in scene_corpus for m_word in ["mexico", "pastor", "pineapple", "tortilla", "puestos", "salsa"]):
                scene_queries.extend([
                    {"source": "wikimedia", "query": "tacos al pastor trompo"},
                    {"source": "wikimedia", "query": "mexican street tacos"},
                    {"source": "wikimedia", "query": "mexico city street market"},
                    {"source": "pixabay_photo", "query": "tacos al pastor trompo"},
                    {"source": "wikimedia", "query": "carnitas tacos"}
                ])
            # 4. SCENE 4: SHOWDOWN / THAI CHILIES / SMOKY ADOBO / CLOSING CHOICE
            else:
                scene_queries.extend([
                    {"source": "wikimedia", "query": "thai street food night market"},
                    {"source": "wikimedia", "query": "mexican street tacos"},
                    {"source": "wikimedia", "query": "tacos al pastor trompo"},
                    {"source": "wikimedia", "query": "bangkok night market street food"},
                    {"source": "pixabay_photo", "query": "street food night market"}
                ])

        # D) DAĞLAR, TRENLER & DOĞA (Mountains / Scenic Trains)
        elif any(w in combined for w in ["mountain", "alps", "train", "railway", "cliff", "switzerland", "incline", "cogwheel", "steepest"]):
            scene_queries.extend([
                {"source": "wikimedia", "query": "pilatus railway switzerland"},
                {"source": "wikimedia", "query": "matterhorn zermatt switzerland"},
                {"source": "pixabay_photo", "query": "scenic mountain train alps"},
                {"source": "pixabay_photo", "query": "mountain peak landscape alps"},
                {"source": "wikimedia", "query": "jungfraujoch railway switzerland"}
            ])

        # E) SPOR & BASKETBOL (NBA)
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

        # F) DİĞER TÜM KONULAR (Evrensel Prompt Çıkarıcı - Asla Bangkok/Mexico/Paris enjekte etmez)
        else:
            clean_p = re.sub(r"\b(8k|cinematic|photorealistic|hyperrealistic|masterpiece)\b", "", prompt, flags=re.IGNORECASE).strip()
            clean_p = re.sub(r"[^\w\s-]", " ", clean_p).strip()
            clean_p = re.sub(r"\s+", " ", clean_p)
            words = clean_p.split()
            short_q = " ".join(words[:4]) if words else topic
            scene_queries.extend([
                {"source": "wikimedia", "query": short_q},
                {"source": "pixabay_photo", "query": short_q},
                {"source": "wikimedia", "query": f"{topic[:30]}"},
                {"source": "pixabay_photo", "query": f"{topic[:30]}"}
            ])

        # Sahneye ait fotoğrafları Round-Robin yöntemiyle (her sorgudan en fazla 1 adet) indir ve algısal dHash ile tekilleştir
        q_idx = 0
        max_attempts = len(scene_queries) * 3
        while len(scene_photos[sc_idx]) < needed + 2 and q_idx < max_attempts:
            q_item = scene_queries[q_idx % len(scene_queries)]
            q_idx += 1

            src = q_item["source"]
            q_str = q_item["query"]
            candidates = []
            if src == "wikimedia":
                candidates = search_wikimedia_commons_photos(q_str, exclude_urls=used.union(downloaded_urls), limit=3)
            elif src == "pixabay_photo":
                candidates = search_pixabay_photos(q_str, exclude_ids=used.union(downloaded_urls), limit=3)

            for cand in candidates:
                if len(scene_photos[sc_idx]) >= needed + 2:
                    break
                c_url = cand.get("url")
                if not c_url or c_url in downloaded_urls or c_url in used:
                    continue

                photo_p = pool_dir / f"scene_{sc_idx:02d}_photo_{len(scene_photos[sc_idx]):02d}.jpg"
                ok = download_and_format_image(c_url, str(photo_p), target_w, target_h)
                if not ok or not photo_p.is_file() or photo_p.stat().st_size <= 10000:
                    continue

                # Algısal dHash Benzerlik Testi (Tüm video genelinde hamming_distance < 14 olanlar elenir)
                try:
                    cand_im = Image.open(photo_p).convert("RGB")
                    cand_hash = calculate_dhash(cand_im)
                    if any(hamming_distance(cand_hash, prev_h) < 14 for prev_h in accepted_video_hashes):
                        print(f"[PHOTO-POOL] ⚠️ Algısal görsel tekrarı (dHash dist < 14) engellendi: {photo_p.name} [{cand.get('title', '')[:30]}]")
                        if photo_p.is_file():
                            photo_p.unlink()
                        continue

                    # Canlılık ve kontrast zenginleştirme
                    enh_im = ImageEnhance.Contrast(cand_im).enhance(1.06)
                    enh_im = ImageEnhance.Color(enh_im).enhance(1.10)
                    enh_im.save(photo_p, "JPEG", quality=92)
                    accepted_video_hashes.append(cand_hash)
                except Exception as ex:
                    print(f"[PHOTO-POOL] Görsel işleme uyarısı: {ex}")

                scene_photos[sc_idx].append(photo_p)
                all_downloaded_photos.append(photo_p)
                downloaded_urls.add(c_url)
                used.add(c_url)
                print(f"[PHOTO-POOL] 📸 Sahne {sc_idx} editoryal görseli bağlandı ({len(scene_photos[sc_idx])}/{needed}): {photo_p.name} [{src}: '{q_str}']")
                # Her sorgudan en fazla 1 görsel al ve bir sonraki farklı sorguya geç
                break

    # ── 3.5 POOL QUOTA BARRIER (HAVUZ KOTA VE BENZERSİZLİK BARAJI) ──
    # Toplam indirilen benzersiz fotoğraf sayısı hedef kesme sayısından (target_count) az ise,
    # ASLA DÖNGÜYE GİRME / FOTOĞRAFLARI TEKRARLAMA!
    # Bunun yerine ek genişletilmiş semantik sorgularla havuz target_count sayısına ulaşana kadar aranır.
    if len(all_downloaded_photos) < target_count:
        needed_extra = target_count - len(all_downloaded_photos)
        print(f"[PHOTO-POOL] ⚠️ Havuz kotası eksik ({len(all_downloaded_photos)}/{target_count}, +{needed_extra} gerekli). Ek genişletilmiş semantik arama başlatılıyor...")
        
        fallback_queries: List[Dict[str, str]] = []
        is_aviation = any(w in topic.lower() for w in ["airplane", "airline", "aircraft", "cockpit", "flight", "cabin", "aviation"])
        is_luxury = any(w in topic.lower() for w in ["royalty", "50", "luxury", "villa", "resort", "hotel"])

        if is_aviation:
            fallback_queries.extend([
                {"source": "wikimedia", "query": "commercial aircraft cabin night"},
                {"source": "pixabay_photo", "query": "airplane cabin interior seats"},
                {"source": "wikimedia", "query": "airplane interior dark night"},
                {"source": "pixabay_photo", "query": "aircraft cabin passenger seats"},
                {"source": "wikimedia", "query": "cockpit aircraft dashboard night"},
                {"source": "pixabay_photo", "query": "airplane flying sunset sky"},
                {"source": "wikimedia", "query": "airport runway lights night"},
                {"source": "pixabay_photo", "query": "airplane window cloud view"}
            ])
        elif is_luxury:
            fallback_queries.extend([
                {"source": "pixabay_photo", "query": "luxury villa infinity pool tropical"},
                {"source": "wikimedia", "query": "tropical beach resort sunset"},
                {"source": "pixabay_photo", "query": "luxury resort hotel bedroom suite"},
                {"source": "pixabay_photo", "query": "tropical island palm beach"},
                {"source": "wikimedia", "query": "bali luxury resort tropical"},
                {"source": "pixabay_photo", "query": "luxury beachfront villa sunset"},
                {"source": "wikimedia", "query": "sri lanka beach palm resort"},
                {"source": "pixabay_photo", "query": "tropical resort pool landscape"}
            ])
        else:
            for sc in scenes:
                s_narr = sc.get("narration") or ""
                s_prompt = sc.get("image_prompt") or ""
                clean_s = re.sub(r"\b(8k|cinematic|photorealistic|hyperrealistic|masterpiece)\b", "", f"{s_narr} {s_prompt}", flags=re.IGNORECASE).strip()
                tokens = [t for t in re.sub(r"[^\w\s]", "", clean_s).split() if len(t) > 3 and t.lower() not in UNWANTED_PHOTO_KEYWORDS]
                if len(tokens) >= 2:
                    q_phrase = " ".join(tokens[:3])
                    fallback_queries.append({"source": "pixabay_photo", "query": q_phrase})
                    fallback_queries.append({"source": "wikimedia", "query": q_phrase})

        fb_idx = 0
        max_fb_attempts = max(24, len(fallback_queries) * 4)
        while len(all_downloaded_photos) < target_count and fb_idx < max_fb_attempts and fallback_queries:
            q_item = fallback_queries[fb_idx % len(fallback_queries)]
            fb_idx += 1
            src = q_item["source"]
            q_str = q_item["query"]
            
            cand_list = []
            if src == "wikimedia":
                cand_list = search_wikimedia_commons_photos(q_str, exclude_urls=used.union(downloaded_urls), limit=4)
            elif src == "pixabay_photo":
                cand_list = search_pixabay_photos(q_str, exclude_ids=used.union(downloaded_urls), limit=4)

            for cand in cand_list:
                if len(all_downloaded_photos) >= target_count:
                    break
                c_url = cand.get("url")
                if not c_url or c_url in downloaded_urls or c_url in used:
                    continue

                photo_p = pool_dir / f"extra_quota_photo_{len(all_downloaded_photos):02d}.jpg"
                ok = download_and_format_image(c_url, str(photo_p), target_w, target_h)
                if not ok or not photo_p.is_file() or photo_p.stat().st_size <= 10000:
                    continue

                try:
                    cand_im = Image.open(photo_p).convert("RGB")
                    cand_hash = calculate_dhash(cand_im)
                    if any(hamming_distance(cand_hash, prev_h) < 14 for prev_h in accepted_video_hashes):
                        if photo_p.is_file():
                            photo_p.unlink()
                        continue

                    enh_im = ImageEnhance.Contrast(cand_im).enhance(1.06)
                    enh_im = ImageEnhance.Color(enh_im).enhance(1.10)
                    enh_im.save(photo_p, "JPEG", quality=92)
                    accepted_video_hashes.append(cand_hash)
                except Exception:
                    pass

                all_downloaded_photos.append(photo_p)
                downloaded_urls.add(c_url)
                used.add(c_url)
                print(f"[PHOTO-POOL] ➕ Ek kota editoryal görseli bağlandı ({len(all_downloaded_photos)}/{target_count}): {photo_p.name} [{src}: '{q_str}']")
                break

    # 4. Zaman Çizgisi Senkronizasyonu ile Kesme Listesini Oluştur (%100 Benzersiz)
    final_cut_photos: List[Path] = []
    used_cut_photo_paths: Set[Path] = set()

    for cut_i in range(target_count):
        assigned_sc = cut_to_scene[cut_i]
        sc_pool = [p for p in scene_photos.get(assigned_sc, []) if p not in used_cut_photo_paths]
        
        if sc_pool:
            chosen = sc_pool[0]
        else:
            # Sahne havuzu bittiyse, genel indirilmiş havuzdan henüz KULLANILMAMIŞ bir fotoğraf seç
            unused_global = [p for p in all_downloaded_photos if p not in used_cut_photo_paths]
            if unused_global:
                chosen = unused_global[0]
            else:
                # Emniyet: havuz biterse bile failsafe benzersiz dosya üretilir ama ASLA eski kesmeler tekrarlanmaz!
                chosen = pool_dir / f"unique_failsafe_{cut_i:03d}.jpg"
                if not chosen.is_file():
                    Image.new("RGB", (target_w, target_h), (24, 24, 27)).save(chosen, "JPEG")
        
        used_cut_photo_paths.add(chosen)
        final_cut_photos.append(chosen)
        print(f"[PHOTO-POOL] ✂️ Kesme {cut_i:02d} ({cut_i * cut_duration:.1f}s) -> Sahne {assigned_sc} benzersiz görsel: {chosen.name}")

    unique_count = len(set(final_cut_photos))
    print(f"[PHOTO-POOL] ✅ Fotoğraf havuzu tamamlandı: {len(final_cut_photos)} kesme için {unique_count} adet %100 benzersiz ve sahne uyumlu editoryal görsel hazırlandı.")
    return final_cut_photos
