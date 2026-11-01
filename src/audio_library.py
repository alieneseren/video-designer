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
        "desc": "Gerilimli, merak uyandırıcı hava ve hikaye anlatımları için arka plan",
        "keywords": ["gizemli", "gerilim", "korkunç", "şok", "korku", "creepy", "paranormal", "karanlık sır", "kriz", "acil durum"],
        "attribution_free": True
    },
    {
        "id": "timeturner",
        "title": "Timeturner",
        "artist": "Patrick Patrikios",
        "url": "https://www.youtube.com/watch?v=5z6yA8h3R1U",
        "mood": "Ticking Clock / Countdown Urgency",
        "desc": "Zamanla yarış, acil durum ve sayaç sahneleri için YouTube Audio Library atıf gerektirmeyen parça",
        "keywords": ["sayaç", "countdown", "zaman", "dakika", "hız", "alarm", "ticking", "urgent", "kriz", "flameout"],
        "attribution_free": True
    },
    {
        "id": "underworld",
        "title": "Underworld",
        "artist": "Myuu",
        "url": "https://www.youtube.com/watch?v=kY7wV2Y8mNo",
        "mood": "Dark Mystery / Disaster / Catastrophe",
        "desc": "Karanlık, kaza kırım ve dramatik felaket sahneleri için atıf gerektirmeyen atmosferik müzik",
        "keywords": ["felaket", "kaza", "düşüş", "ölüm", "enkaz", "karanlık", "gizem", "disaster", "crash"],
        "attribution_free": True
    },
    {
        "id": "borderless",
        "title": "Borderless",
        "artist": "Aakash Gandhi",
        "url": "https://www.youtube.com/watch?v=r3_7zZ5b2wQ",
        "mood": "Deep Investigative / Documentary",
        "desc": "Resmi kaza tahkikatı, NTSB raporları ve derin teknik analizler için sakin piyano & yaylılar",
        "keywords": ["tahkikat", "ntsb", "ansv", "kara kutu", "rapor", "analiz", "inceleme", "investigation"],
        "attribution_free": True
    },
    {
        "id": "sneaky_snitch",
        "title": "Sneaky Snitch",
        "artist": "Kevin MacLeod",
        "url": "https://www.youtube.com/watch?v=-SjOkb3kVgI",
        "mood": "Satirical / Cunning Humor",
        "desc": "Askeri ihale hicvi, şirket kurnazlığı ve çöp adam esprileri için telifsiz eğlenceli parça",
        "keywords": ["hiciv", "komik", "para", "ceo", "skandal", "ihale", "cunning", "satire", "stealth"],
        "attribution_free": True
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

def get_attribution_free_tracks() -> list[dict]:
    """Tüm atıf gerektirmeyen (YouTube Audio Library No-Attribution) müzikleri listeler."""
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "artist": t["artist"],
            "mood": t["mood"],
            "desc": t.get("desc", ""),
            "attribution": "No attribution required (Atıf gerekmez)",
            "attribution_free": True
        }
        for t in TRACKS
    ]

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
        for fname in [f"{track_id}.mp3", f"{track_id}.wav"]:
            cand = d / fname
            if cand.exists() and cand.stat().st_size > 10240:
                print(f"[AUDIO-LIBRARY] Yerel önbellek bulundu: {cand}")
                return cand
        
    yt_dlp_bin = project_root / ".venv" / "bin" / "yt-dlp"
    if not yt_dlp_bin.exists():
        yt_dlp_bin = "yt-dlp" # Fallback to global
        
    # İndirme kaynakları: önce doğrudan resmi Audio Library URL'si, sonra arama
    direct_url = track.get("url", "")
    search_query = f"ytsearch1:No copyright {track.get('title', '')} {track.get('mood', 'lofi')} background music"
    sources_to_try = [direct_url, search_query]
    
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


def parse_time_seconds(time_val) -> float:
    """Parses '03:30', '03:30.5', 210, etc. into seconds as float."""
    if time_val is None:
        return 0.0
    if isinstance(time_val, (int, float)):
        return max(0.0, float(time_val))
    val_str = str(time_val).strip()
    if not val_str:
        return 0.0
    parts = val_str.split(":")
    try:
        if len(parts) == 1:
            return max(0.0, float(parts[0]))
        elif len(parts) == 2:
            return max(0.0, int(parts[0]) * 60 + float(parts[1]))
        elif len(parts) == 3:
            return max(0.0, int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2]))
    except Exception:
        pass
    return 0.0


def build_timeline_bgm_track(
    bgm_timeline: list[dict],
    total_duration: float,
    work_dir: Path,
    base_volume: float = 0.08
) -> Path | None:
    """
    Given a bgm_timeline list of segments (start_time, end_time, track_id),
    downloads/loads each attribution-free track, creates faded audio segments,
    and concatenates them into a single seamless wav file matching total_duration.
    """
    if not bgm_timeline or not isinstance(bgm_timeline, list) or total_duration <= 1.0:
        return None

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    project_root = Path(__file__).resolve().parent.parent
    cache_dir = project_root / "audio_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    segment_wavs = []
    current_time = 0.0

    for idx, seg in enumerate(bgm_timeline):
        if not isinstance(seg, dict):
            continue
        start = parse_time_seconds(seg.get("start_time", current_time))
        end = parse_time_seconds(seg.get("end_time", 0.0))

        # If end is 0 or less than start, estimate from next or remaining
        if end <= start:
            if idx + 1 < len(bgm_timeline) and "start_time" in bgm_timeline[idx + 1]:
                end = parse_time_seconds(bgm_timeline[idx + 1]["start_time"])
            else:
                end = total_duration

        dur = max(1.0, end - start)
        track_id = seg.get("track_id") or "lofi_storyteller"

        track_path = download_track(track_id, cache_dir)
        if not track_path or not Path(track_path).is_file():
            track_path = download_track("lofi_storyteller", cache_dir)
            if not track_path or not Path(track_path).is_file():
                continue

        seg_file = work_dir / f"bgm_seg_{idx:02d}.wav"
        fade_dur = min(1.2, dur / 2.0)
        fade_out_start = max(0.0, dur - fade_dur)

        # Generate looped, faded segment
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(track_path),
            "-t", f"{dur:.3f}",
            "-af", f"afade=t=in:ss=0:d={fade_dur:.2f},afade=t=out:st={fade_out_start:.3f}:d={fade_dur:.2f},volume={base_volume:.4f}",
            "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2",
            str(seg_file)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if seg_file.is_file() and seg_file.stat().st_size > 1024:
                segment_wavs.append(seg_file)
                current_time = end
        except Exception as e:
            print(f"[AUDIO-LIBRARY] BGM segment {idx} failed: {e}")

    if not segment_wavs:
        return None

    # Check if we covered up to total_duration
    if current_time < total_duration - 0.5 and segment_wavs:
        remaining = total_duration - current_time
        last_seg = bgm_timeline[-1] if bgm_timeline else {}
        track_id = last_seg.get("track_id") or "borderless"
        track_path = download_track(track_id, cache_dir)
        if track_path and Path(track_path).is_file():
            tail_file = work_dir / "bgm_seg_tail.wav"
            fade_dur = min(1.2, remaining / 2.0)
            fade_out_start = max(0.0, remaining - fade_dur)
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", str(track_path),
                "-t", f"{remaining:.3f}",
                "-af", f"afade=t=in:ss=0:d={fade_dur:.2f},afade=t=out:st={fade_out_start:.3f}:d={fade_dur:.2f},volume={base_volume:.4f}",
                "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2",
                str(tail_file)
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if tail_file.is_file() and tail_file.stat().st_size > 1024:
                    segment_wavs.append(tail_file)
            except Exception:
                pass

    # Concat all segments into bgm_timeline_mixed.wav
    concat_list = work_dir / "bgm_seg_list.txt"
    concat_list.write_text("\n".join([f"file '{p.resolve()}'" for p in segment_wavs]), encoding="utf-8")
    out_mixed = work_dir / "bgm_timeline_mixed.wav"

    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:a", "pcm_s16le",
        str(out_mixed)
    ]
    try:
        subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if out_mixed.is_file() and out_mixed.stat().st_size > 4096:
            print(f"[AUDIO-LIBRARY] ✓ bgm_timeline başarıyla derlendi: {out_mixed} ({len(segment_wavs)} segment)")
            return out_mixed
    except Exception as e:
        print(f"[AUDIO-LIBRARY] bgm_timeline concat failed: {e}")

    return None

