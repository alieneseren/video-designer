"""
asmr_manager.py
===============
Reddit Hikayeleri, WhatsApp Sohbetleri ve benzeri formatlar için telifsiz, logosuz ve filigransız
ASMR / Satisfying arka plan videolarının Pixabay API ile dinamik yönetimi.

ÖZELLİKLER:
1. Pixabay API Entegrasyonu: Tamamen telifsiz, filigransız, logosuz ve kullanıcı adsız temiz stok ASMR videoları.
2. Zengin Kategori Havuzu: Kinetic sand, sand cutting, soap cutting, acrylic paint pouring, liquid abstract, 3D satisfying loop, pottery.
3. Tek Kullanımlık Yaşam Döngüsü (Consume-Once): Bir video üretilirken kullanılan ASMR videoları işlem sonunda diskten SİLİNİR.
4. Asla Tekrarlamama (Anti-Repetition History): İndirilen Pixabay video ID'leri tarihçeye kaydedilir ve bir daha asla aynı video indirilmez.
5. Dinamik & Kesintisiz 9:16 Dikey Birleştirme (Multi-Chunk Concatenation): Hedef süre boyunca farklı estetik kesitleri birleştirir.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict, Any


def _find_asmr_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "config" / "assets" / "asmr",
        Path(__file__).resolve().parent / "assets" / "asmr",
        Path("config/assets/asmr").resolve(),
        Path("assets/asmr").resolve(),
    ]
    for c in candidates:
        if c.exists():
            return c
    default_dir = Path(__file__).resolve().parent.parent / "config" / "assets" / "asmr"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


ASMR_DIR = _find_asmr_dir()
PIXABAY_HISTORY_FILE = ASMR_DIR / "pixabay_history.json"
USAGE_HISTORY_FILE = ASMR_DIR / "usage_history.json"

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

# Telifsiz ve filigransız zengin ASMR & Satisfying arama terimleri
PIXABAY_ASMR_QUERIES = [
    "kinetic sand",
    "sand cutting",
    "soap cutting",
    "acrylic paint pouring",
    "liquid abstract",
    "satisfying loop",
    "loop 3d",
    "pottery clay",
    "colorful fluid",
    "satisfying craft",
    "sand zen",
    "asmr cutting",
]


def find_ffmpeg() -> str:
    """Sistemdeki veya .venv içindeki ffmpeg ikilisini bulur."""
    for p in ["ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        try:
            res = subprocess.run([p, "-version"], capture_output=True)
            if res.returncode == 0:
                return p
        except Exception:
            continue
    return "ffmpeg"


def get_video_duration(video_path: str | Path) -> float:
    """ffprobe ile video süresini saniye olarak ölçer."""
    ffmpeg = find_ffmpeg()
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe") if "ffmpeg" in ffmpeg else "ffprobe"
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return float(res.stdout.strip())
    except Exception:
        return 20.0


def _load_pixabay_history() -> List[int]:
    """Daha önce indirilmiş Pixabay video ID'lerini yükler."""
    if PIXABAY_HISTORY_FILE.exists():
        try:
            return json.loads(PIXABAY_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_pixabay_history(history: List[int]):
    """İndirilen Pixabay video ID'lerini kaydeder."""
    try:
        ASMR_DIR.mkdir(parents=True, exist_ok=True)
        PIXABAY_HISTORY_FILE.write_text(json.dumps(history[-2000:], indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[PIXABAY-HISTORY] Tarihçe kaydetme hatası: {e}")


def fetch_fresh_pixabay_asmr_clip(preferred_query: Optional[str] = None) -> Optional[Path]:
    """
    Pixabay API'den daha önce HİÇ KULLANILMAMIŞ, %100 telifsiz, filigransız ve kullanıcı adsız
    yeni bir ASMR / Satisfying videosu indirir.
    """
    ASMR_DIR.mkdir(parents=True, exist_ok=True)
    history = set(_load_pixabay_history())

    queries = list(PIXABAY_ASMR_QUERIES)
    if preferred_query:
        queries = [preferred_query] + [q for q in queries if q != preferred_query]
    random.shuffle(queries)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    api_key = get_pixabay_key()
    if not api_key:
        print("[ASMR] ⚠️ Pixabay API anahtarı tanımlanmamış. Arama atlanıyor.")
        return []

    for query in queries[:5]:
        try:
            params = {
                "key": api_key,
                "q": query,
                "video_type": "film",
                "per_page": 25,
            }
            api_url = f"https://pixabay.com/api/videos/?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            hits = data.get("hits", [])
            # Daha önce indirilmemiş olanları filtrele (tercihen 10 saniye ve üzeri)
            new_hits = [h for h in hits if h["id"] not in history]
            new_hits_long = [h for h in new_hits if h.get("duration", 0) >= 10]
            candidate_hits = new_hits_long if new_hits_long else new_hits

            if not candidate_hits:
                continue

            chosen_hit = random.choice(candidate_hits)
            hit_id = chosen_hit["id"]
            videos = chosen_hit.get("videos", {})

            # En uygun video akışını seç (large veya medium)
            stream_obj = videos.get("large") or videos.get("medium") or videos.get("small")
            if not stream_obj or not stream_obj.get("url"):
                continue

            stream_url = stream_obj["url"]
            cat_slug = query.replace(" ", "_")
            target_path = ASMR_DIR / f"pixabay_{hit_id}_{cat_slug}.mp4"

            print(f"[PIXABAY-ASMR] 📥 Temiz ve logosuz ASMR indiriliyor: '{query}' (ID: {hit_id}, Süre: {chosen_hit.get('duration')}s)...")

            # Doğrudan indirme (Browser User-Agent ile)
            v_req = urllib.request.Request(stream_url, headers=headers)
            with urllib.request.urlopen(v_req, timeout=40) as v_resp, open(target_path, "wb") as f_out:
                f_out.write(v_resp.read())

            if target_path.exists() and target_path.stat().st_size > 500 * 1024:
                # Başarılı indirme! Tarihçeye ekle ve kaydet
                history.add(hit_id)
                _save_pixabay_history(list(history))
                print(f"[PIXABAY-ASMR] ✅ Başarıyla indirildi: {target_path.name} ({target_path.stat().st_size / 1024 / 1024:.1f} MB)")
                return target_path
            else:
                if target_path.exists():
                    target_path.unlink()
        except Exception as err:
            print(f"[PIXABAY-ASMR] Arama/indirme hatası ('{query}'): {err}")

    return None


def _detect_video_category(filename: str) -> str:
    """Dosya adından ASMR kategorisini tespit eder."""
    fn = filename.lower()
    if "sand" in fn or "kinetic" in fn:
        return "sand"
    if "soap" in fn:
        return "soap"
    if "acrylic" in fn or "paint" in fn or "liquid" in fn or "fluid" in fn:
        return "liquid"
    if "pottery" in fn or "clay" in fn:
        return "pottery"
    if "craft" in fn:
        return "craft"
    if "loop" in fn or "3d" in fn:
        return "loop3d"
    return "asmr"


def _create_synthetic_satisfying_video(output_path: Path, duration: float = 30.0, W: int = 1080, H: int = 1920):
    """İnternet bağlantısı yoksa ffmpeg lavfi ile estetik renk geçişli tatmin edici dikey video üretir."""
    ffmpeg = find_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"mptestsrc=rate=30:duration={duration:.1f}",
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},hue=s=1.5:H='2*PI*t/10',gblur=sigma=20",
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
        print(f"[ASMR-FALLBACK] Sentetik tatmin edici video üretildi: {output_path}")
    except Exception as e:
        print(f"[ASMR-FALLBACK] Sentetik video hatası: {e}")


def purge_legacy_watermarked_asmr():
    """Eski, kullanıcı adı veya logo içeren YouTube videolarını kütüphaneden temizler."""
    legacy_prefixes = ["minecraft_parkour", "subway_surfers", "gta5_car_stunts", "marble_run", "soap_cutting_asmr.mp4", "kinetic_sand_asmr.mp4"]
    for f in ASMR_DIR.iterdir():
        if not f.is_file():
            continue
        fn = f.name.lower()
        if any(lp in fn for lp in legacy_prefixes) and not fn.startswith("pixabay_"):
            try:
                print(f"[ASMR-PURGE] Logolu/Eski ASMR videosu temizlendi: {f.name}")
                f.unlink()
            except Exception:
                pass


def ensure_asmr_library(target_duration: float = 60.0) -> List[Path]:
    """
    ASMR kütüphanesini kontrol eder.
    Mevcut temiz Pixabay videolarının toplam süresi hedef süreyi karşılamıyorsa
    Pixabay API'sinden taze, daha önce hiç kullanılmamış temiz videolar çeker.
    """
    ASMR_DIR.mkdir(parents=True, exist_ok=True)
    purge_legacy_watermarked_asmr()

    existing = [
        p for p in ASMR_DIR.iterdir()
        if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm")
        and not p.name.endswith(".part")
        and p.stat().st_size > 500 * 1024
        and "synthetic" not in p.name.lower()
    ]

    total_dur = sum(get_video_duration(p) for p in existing)
    needed_dur = target_duration + 2.0

    # Yeterli süre yoksa Pixabay'den taze ASMR videoları indir (gerektiği kadar tek tek çeker)
    attempts = 0
    while total_dur < needed_dur and attempts < 4:
        attempts += 1
        print(f"[ASMR-MANAGER] Pixabay'den taze ve logosuz ASMR videosu çekiliyor (Mevcut: {total_dur:.1f}s / Hedef: {needed_dur:.1f}s)...")
        downloaded = fetch_fresh_pixabay_asmr_clip()
        if downloaded:
            existing.append(downloaded)
            total_dur += get_video_duration(downloaded)
        else:
            break

    if not existing:
        # Son çare: Sentetik estetik video üret
        fallback_vid = ASMR_DIR / "synthetic_satisfying_particles.mp4"
        if not fallback_vid.exists() or fallback_vid.stat().st_size < 1000:
            _create_synthetic_satisfying_video(fallback_vid, duration=30.0)
        existing = [fallback_vid]

    return existing


def prepare_asmr_background(
    target_duration: float,
    output_path: str | Path,
    asmr_video_path: Optional[str | Path] = None,
    width: int = 1080,
    height: int = 1920,
    fps: int = 24
) -> Path:
    """
    ASMR arka plan videosunu hedef süre boyunca 1080x1920 veya 1080x960 formatında hazırlar.
    
    YENİ YAŞAM DÖNGÜSÜ:
    1. Hedef süre için Pixabay'den %100 temiz ve yeni ASMR videoları çeker.
    2. Gerekli kesitleri kırpıp birleştirerek çıktıyı oluşturur.
    3. Kullanılan kaynak ASMR videolarını DİSKTEN SİLER; böylece disk şişmez ve
       bir sonraki video üretiminde her zaman yeni ve farklı ASMR videoları çekilir.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_path.parent / "asmr_temp_chunks"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Taze ASMR kaynaklarını garantile
    available = ensure_asmr_library(target_duration=target_duration)
    real_videos = [v for v in available if "synthetic" not in v.name.lower()]
    pool = list(real_videos if real_videos else available)
    random.shuffle(pool)

    ffmpeg = find_ffmpeg()
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"fps={fps},"
        f"format=yuv420p"
    )

    chunk_paths = []
    actual_used_source_files = set()
    accumulated_dur = 0.0
    used_categories: List[str] = []

    # Parça parça kesitleri oluştur
    while accumulated_dur < target_duration:
        remaining = target_duration - accumulated_dur

        chosen_vid = None
        last_category = used_categories[-1] if used_categories else None

        # Farklı kategori tercih et
        for cand in pool:
            cat = _detect_video_category(cand.name)
            if cat != last_category or len(pool) == 1:
                chosen_vid = cand
                break

        if not chosen_vid:
            chosen_vid = random.choice(pool)

        chosen_cat = _detect_video_category(chosen_vid.name)
        used_categories.append(chosen_cat)
        src_dur = get_video_duration(chosen_vid)

        chunk_len = min(remaining, random.uniform(15.0, 35.0))
        if remaining < 20.0 or src_dur <= chunk_len:
            chunk_len = min(remaining, src_dur)

        start_off = 0.0
        if src_dur > chunk_len + 3.0:
            start_off = random.uniform(0.0, src_dur - chunk_len - 1.0)

        chunk_file = temp_dir / f"chunk_{len(chunk_paths):03d}.mp4"
        cmd = [
            ffmpeg, "-y",
            "-ss", f"{start_off:.2f}",
            "-i", str(chosen_vid),
            "-t", f"{chunk_len:.2f}",
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-an",
            "-pix_fmt", "yuv420p",
            str(chunk_file)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode == 0 and chunk_file.exists() and os.path.getsize(chunk_file) > 1000:
            chunk_paths.append(chunk_file)
            accumulated_dur += chunk_len
            actual_used_source_files.add(chosen_vid)
            print(f"[ASMR-MULTI] Temiz ASMR kesiti eklendi: [{chosen_cat.upper()}] {chosen_vid.name} (Süre: {chunk_len:.1f}s | Toplam: {accumulated_dur:.1f}/{target_duration:.1f}s)")
        else:
            print(f"[ASMR-MULTI] Uyarı: {chosen_vid.name} kesiti alınamadı, sonraki video deneniyor.")
            if len(chunk_paths) == 0 and len(pool) == 1:
                break

    if not chunk_paths:
        raise RuntimeError("ASMR parçaları oluşturulamadı.")

    # Parçaları birleştir (ffmpeg concat demuxer)
    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in chunk_paths:
            f.write(f"file '{p.resolve()}'\n")

    concat_cmd = [
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(output_path)
    ]
    res = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise RuntimeError(f"ASMR parçaları birleştirilemedi: {res.stderr[-500:]}")

    # Geçici parçaları temizle
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    # ── KULLANICI TALEBİ: KULLANILAN ASMR VİDEOLARINI DİSKTEN SİL ──
    # Her video üretildiğinde kullanılan ASMR dosyaları silinir.
    # Bir dahaki video üretiminde Pixabay'den tamamen yeni ASMR videoları çekilir.
    for vid_path in actual_used_source_files:
        try:
            if vid_path.exists() and "synthetic" not in vid_path.name.lower():
                print(f"[ASMR-LIFECYCLE] 🗑️ Kullanılan ASMR videosu silindi (sonraki üretimde Pixabay'den yenisi çekilecek): {vid_path.name}")
                vid_path.unlink()
        except Exception as del_err:
            print(f"[ASMR-LIFECYCLE] Dosya silme hatası ({vid_path}): {del_err}")

    print(f"[ASMR-RENDER] ✅ Temiz ve logosuz ASMR arka planı hazırlandı: {output_path} ({width}x{height}, {accumulated_dur:.1f}s)")
    return output_path
