"""
audio_library.py
YouTube Kitaplığı popüler müzikleri kataloğu ve indirme yönetimi.
"""

from __future__ import annotations
import os
import subprocess
from pathlib import Path

# Popüler YouTube Audio Library parçaları kataloğu
TRACKS = [
    {
        "id": "space_walk",
        "title": "Space Walk",
        "artist": "Silent Partner",
        "url": "https://www.youtube.com/watch?v=2vmdZ9dF0Yg",
        "mood": "Cinematic / Sci-Fi",
        "desc": "Gizemli ve uzay temalı",
        "keywords": ["uzay", "space", "mars", "yıldız", "kara delik", "ışık hızı", "nasa", "ay", "nebula", "galaksi", "gökada", "astronomi"]
    },
    {
        "id": "lunar_landing",
        "title": "Lunar Landing",
        "artist": "Silent Partner",
        "url": "https://www.youtube.com/watch?v=vVj_nB4J2rU",
        "mood": "Sci-Fi / Ambient",
        "desc": "Sakin ve kozmik",
        "keywords": ["bilim", "fizik", "kuantum", "zaman", "bükülme", "görelilik", "solucan deliği", "yerçekimi"]
    },
    {
        "id": "desert_caravan",
        "title": "Desert Caravan",
        "artist": "Aaron Kenny",
        "url": "https://www.youtube.com/watch?v=R9Z8X_qP5_U",
        "mood": "Cinematic / Travel",
        "desc": "Macera ve keşif temalı",
        "keywords": ["gezi", "travel", "mısır", "çöl", "macera", "kültür", "tarih", "antik", "piramit", "şehir", "müze", "rota"]
    },
    {
        "id": "oceanside",
        "title": "Oceanside",
        "artist": "Scandinavianz",
        "url": "https://www.youtube.com/watch?v=sM3G3rN_kCg",
        "mood": "Tropical / Upbeat",
        "desc": "Enerjik ve yaz temalı",
        "keywords": ["deniz", "plaj", "beach", "yaz", "tatil", "otel", "kumsal", "tropikal", "ada", "güneş"]
    },
    {
        "id": "schizo",
        "title": "Schizo",
        "artist": "Anno Domini Beats",
        "url": "https://www.youtube.com/watch?v=jSFvU-D0w54",
        "mood": "Hip Hop / Dramatic",
        "desc": "Gergin ve tempolu",
        "keywords": ["gizem", "korku", "gerilim", "tehlike", "suç", "katil", "esrarengiz", "sır", "karanlık"]
    },
    {
        "id": "crock_pot",
        "title": "Crock Pot",
        "artist": "Diamond Ortiz",
        "url": "https://www.youtube.com/watch?v=Nn1R_vP4h3M",
        "mood": "Upbeat / Funk",
        "desc": "Neşeli ve hareketli",
        "keywords": ["eğlence", "komik", "oyun", "çocuk", "şaka", "kedi", "köpek", "hayvan"]
    },
    {
        "id": "sunny_days",
        "title": "Sunny Days",
        "artist": "Anno Domini Beats",
        "url": "https://www.youtube.com/watch?v=mD0klyy7kZk",
        "mood": "Hip Hop / Chill",
        "desc": "Sakin ve havalı",
        "keywords": ["günlük", "blog", "sohbet", "yaşam", "yemek", "kahve", "rutin"]
    },
    {
        "id": "reddit_official_bgm",
        "title": "From Russia With Love",
        "artist": "Huma-Huma",
        "url": "https://www.youtube.com/watch?v=2z5rMNH_yTI",
        "mood": "Story / Acoustic Drama",
        "desc": "Reddit hikayeleri resmi arka plan müziği (Huma-Huma - From Russia With Love)",
        "keywords": ["reddit", "askreddit", "hikaye", "story", "itiraf", "confession", "aitah", "tifu", "anlatı", "sır", "olay", "tuhaf", "huma huma", "russia"]
    },
    {
        "id": "lofi_storyteller",
        "title": "Reddit Chill Lo-Fi Background",
        "artist": "Official Story Music",
        "url": "https://www.youtube.com/watch?v=2z5rMNH_yTI",
        "mood": "Lo-Fi / Chill Story",
        "desc": "Reddit hikayeleri ve akıcı anlatımlar için arka plan müziği",
        "keywords": ["reddit", "askreddit", "hikaye", "story", "itiraf", "confession", "aitah", "tifu", "anlatı", "sır", "olay", "tuhaf"]
    },
    {
        "id": "dramatic_suspense",
        "title": "Eyes of Glory",
        "artist": "Aakash Gandhi",
        "url": "https://www.youtube.com/watch?v=8mG_JjL1P7A",
        "mood": "Dramatic / Tension",
        "desc": "Gerilimli, merak uyandırıcı Reddit hikayeleri için arka plan",
        "keywords": ["gizemli", "gerilim", "korkunç", "şok", "korku", "creepy", "paranormal", "karanlık sır"]
    }
]

def get_recommendation(topic: str, title: str = "") -> str:
    """Konu ve başlık kelimelerine göre en uygun müzik ID'sini döndürür."""
    text = f"{topic} {title}".lower()
    best_track = "lofi_storyteller" if any(k in text for k in ["reddit", "askreddit", "hikaye", "itiraf", "tifu", "aitah", "sır"]) else "sunny_days"
    max_matches = 0
    
    # Reddit hikayeleri öncelikli algılama
    for keyword in ["reddit", "askreddit", "itiraf", "aitah", "tifu", "hikaye", "confession", "sır"]:
        if keyword in text:
            return "lofi_storyteller"

    # Varsayılan uzay teması algılama
    for keyword in ["uzay", "space", "mars", "yıldız", "kara delik", "ışık hızı", "nasa"]:
        if keyword in text:
            best_track = "space_walk"
            break
            
    # Seyahat algılama
    for keyword in ["gezi", "travel", "tatil", "şehir", "macera"]:
        if keyword in text:
            best_track = "desert_caravan"
            break

    # Detaylı kelime eşleştirme
    for track in TRACKS:
        matches = 0
        for kw in track["keywords"]:
            if kw in text:
                matches += 1
        if matches > max_matches:
            max_matches = matches
            best_track = track["id"]
            
    return best_track

def get_track_by_id(track_id: str) -> dict | None:
    for t in TRACKS:
        if t["id"] == track_id:
            return t
    return None

def download_track(track_id: str, target_dir: Path) -> Path | None:
    """yt-dlp kullanarak parçayı mp3 olarak indirir veya yerel önbellekten döndürür."""
    track = get_track_by_id(track_id)
    if not track:
        # Bilinmeyen ID ise default lofi_storyteller'a dön
        track = get_track_by_id("lofi_storyteller")
        if not track:
            return None

    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"{track_id}.mp3"
    
    if out_file.exists() and out_file.stat().st_size > 10240:
        return out_file

    project_root = Path(__file__).resolve().parent.parent
    
    # 1. Önce proje içindeki hazır klasörleri kontrol et
    candidate_dirs = [
        project_root / "audio_cache",
        project_root / "assets" / "music",
        project_root / "assets" / "audio",
        Path("config/bgm"),
        Path("assets/music"),
        Path("audio_cache"),
    ]
    for d in candidate_dirs:
        for fname in [f"{track_id}.mp3", "lofi_storyteller.mp3", f"{track_id}.wav"]:
            cand = d / fname
            if cand.exists() and cand.stat().st_size > 10240:
                print(f"[AUDIO-LIBRARY] Yerel önbellek bulundu: {cand}")
                return cand
        
    yt_dlp_bin = project_root / ".venv" / "bin" / "yt-dlp"
    if not yt_dlp_bin.exists():
        yt_dlp_bin = "yt-dlp" # Fallback to global
        
    # İndirme kaynakları: önce doğrudan arama terimi, sonra URL
    search_query = f"ytsearch1:No copyright {track.get('title', '')} {track.get('mood', 'lofi')} background music story"
    sources_to_try = [search_query, track.get("url", "")]
    
    for source in sources_to_try:
        if not source:
            continue
        print(f"[AUDIO-LIBRARY] İndiriliyor: {track['title']} ({source}) -> {out_file}")
        cmd = [
            str(yt_dlp_bin),
            source,
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", str(target_dir / f"{track_id}.%(ext)s"),
            "--no-playlist"
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if res.returncode == 0 and out_file.exists() and out_file.stat().st_size > 10240:
                print(f"[AUDIO-LIBRARY] İndirme başarılı: {out_file}")
                return out_file
        except Exception as e:
            print(f"[AUDIO-LIBRARY] İndirme deneme hatası ({source}): {e}")

    # Son çare: audio_cache veya assets/music içinde herhangi bir mp3 ara
    for d in candidate_dirs:
        if d.exists():
            for any_mp3 in d.glob("*.mp3"):
                if any_mp3.stat().st_size > 10240:
                    print(f"[AUDIO-LIBRARY] Son çare alternatif müzik: {any_mp3}")
                    return any_mp3
        
    return None

