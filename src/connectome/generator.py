"""
src/connectome/generator.py
Drosophila Connectome Bio-AI Müzik & Video Klip Üreticisi
139.255 nöron simülasyonu ile 3-5 dakikalık (180-300s) avangart piyano & senfonik klipler
veya 9:16 dikey Shorts üretir.
"""

import os
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from connectome.synth import synthesize_audio_and_spikes, json_default, GENRES
from remotion_renderer import render_connectome_video_remotion, is_remotion_available
from channel_manager import get_localized_metadata


def generate_connectome_clip(
    output_folder: Path,
    duration_sec: float = 180.0,
    genre: str = "emotional",
    theme: str = "cosmic",
    is_vertical: bool = False,
    language: str = "tr",
    scale_override: Optional[str] = None,
    bpm_override: Optional[float] = None,
    writer = None,
    progress_callback = None,
) -> Dict[str, Any]:
    """
    3-5 dakika (180s - 300s) veya Shorts uzunluğunda Sinek Beyni müzik videosu üretir.
    """
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    def log(pct: int, msg: str):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[CONNECTOME] [{pct}%] {msg}")

    log(5, "Biyo-AI Konnektom Müzik Motoru başlatılıyor...")

    # 1. Müzik türünü belirle
    target_genre = genre if genre in GENRES else random.choice(list(GENRES.keys()))
    genre_data = GENRES.get(target_genre, {})
    genre_name = genre_data.get("name", "Emotional & Melancholic (Nocturne)")

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    track_title = f"Synaptic Resonance #{timestamp_str[-4:]}"

    # 2. Sesi ve nöron spike verilerini üret
    duration_val = float(max(15.0, min(300.0, duration_sec)))
    log(20, f"Drosophila konnektom nöron simülasyonu yapılıyor ({duration_val:.1f}s, {genre_name})...")

    track_info = synthesize_audio_and_spikes(
        duration_sec=duration_val,
        genre_id=target_genre,
        scale_name=scale_override if scale_override != "auto" else None,
        bpm=bpm_override,
        output_dir=output_folder,
        track_title=track_title
    )
    track_info["theme"] = theme
    track_info["is_vertical"] = is_vertical
    track_info["genre_name"] = genre_name

    # Spikes verisini oku
    spikes_file = output_folder / "spikes_data.json"
    spikes_data = {}
    if spikes_file.exists():
        try:
            spikes_data = json.loads(spikes_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 3. LM Studio ile Başlık, Kanca ve Açıklama Metinlerini Üret (Hedef dilde)
    log(45, f"LM Studio ile viral başlık ve sosyal medya yayın metinleri hazırlanıyor (Dil: {language})...")
    try:
        from connectome.lm_studio import generate_music_copywriting
        copy_result = generate_music_copywriting(track_info, language=language)
    except Exception as copy_err:
        print(f"[CONNECTOME] Copywriting hatası: {copy_err}")
        copy_result = {}

    meta_title = copy_result.get("title") or f"Drosophila Connectome - {track_info.get('title', 'Axonal Symphony')}"
    if is_vertical and "#shorts" not in meta_title.lower():
        meta_title += " #Shorts"

    desc = copy_result.get("description") or ""
    tags = copy_result.get("tags") or []
    hook = copy_result.get("hook") or ""
    if not desc or not tags:
        loc_desc, loc_tags = get_localized_metadata(meta_title, language=language, category="music")
        if not desc:
            desc = loc_desc
        if not tags:
            tags = loc_tags

    track_info["hook"] = hook
    track_info["title"] = meta_title
    
    # 4. Remotion ile Render Yap
    log(55, f"Remotion ile {'Shorts (9:16)' if is_vertical else 'Yatay Klip (16:9)'} render başlatılıyor...")
    final_video_path = output_folder / "final.mp4"
    audio_path = str(output_folder / "audio.wav")

    rendered = False
    if is_remotion_available():
        rendered = render_connectome_video_remotion(
            track_info=track_info,
            spikes_data=spikes_data,
            audio_path=audio_path,
            output_path=str(final_video_path),
            is_vertical=is_vertical,
            theme=theme,
            fps=30
        )

    if not rendered:
        log(70, "Remotion render tamamlanamadı veya kullanılamıyor, FFmpeg fallback devreye giriyor...")
        # Fallback: Generate dynamic visualization via ffmpeg
        w, h = (1080, 1920) if is_vertical else (1920, 1080)
        import subprocess
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-filter_complex",
            f"[0:a]showwaves=s={w}x{h}:mode=cline:colors=0x00f0ff|0xa855f7:scale=sqrt,format=yuv420p[v]",
            "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
            str(final_video_path)
        ]
        sub = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if sub.returncode != 0 or not final_video_path.exists():
            raise RuntimeError(f"Video üretimi başarısız: {sub.stderr}")

    # Thumbnail oluştur (Dashboard kartlarında görünmesi için)
    thumb_path = output_folder / "thumbnail.jpg"
    try:
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-ss", "00:00:02", "-i", str(final_video_path),
            "-frames:v", "1", "-q:v", "2", str(thumb_path)
        ], capture_output=True, check=False)
    except Exception as e:
        print(f"[CONNECTOME] Thumbnail oluşturma uyarısı: {e}")

    log(90, "Meta veriler ve yayın paketi kaydediliyor...")

    # Sosyal Medya Yayın Kiti (Copy-Paste Ready)
    publishing_txt = f"""===============================================================
🎬 SİNEK BEYNİ // SOSYAL MEDYA YAYIN PAKETİ
===============================================================

📌 ÖNERİLEN VİRAL BAŞLIK:
{meta_title}

⚡ İLK 3 SANİYE EKRAN KANCA CÜMLESİ:
"{hook}"

📝 AÇIKLAMA (YOUTUBE / TIKTOK / REELS İÇİN HAZIR METİN):
{desc}

🏷️ ETİKETLER & HASHTAGLER:
{' '.join(['#' + t.replace(' ', '') for t in tags])}

📊 PARÇA TELEMETRİSİ:
• Müzik Türü: {track_info.get('genre_name')}
• Müzik Skalası: {track_info.get('scale')}
• Tempo: {track_info.get('bpm')} BPM
• Ateşlenen Canlı Nöron Sayısı: {track_info.get('neuronsSimulated', 48)}
• Toplam Sinaps Ateşlemesi: {track_info.get('totalSpikes')} Spike
• Çözünürlük: {'1080x1920 (9:16 Shorts)' if is_vertical else '1920x1080 (16:9 Yatay)'}
• Model Kaynağı: Princeton FlyWire Drosophila Connectome
===============================================================
"""
    (output_folder / "publishing_info.txt").write_text(publishing_txt, encoding="utf-8")

    # Kayıtlar
    metadata_json = {
        "title": meta_title,
        "description": desc,
        "tags": tags,
        "keywords": tags,
        "language": language,
        "category": "music",
        "topic": "music",
        "hook": hook,
        "narration": track_info.get("concept", ""),
        "scenes": [],
        "track_info": track_info,
        "ai_source": copy_result.get("ai_source", "lm_studio"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    (output_folder / "metadata.json").write_text(
        json.dumps(metadata_json, ensure_ascii=False, indent=2, default=json_default),
        encoding="utf-8"
    )

    video_info_json = {
        "shorts_mode": is_vertical,
        "transition": "none",
        "resolution": "1080x1920" if is_vertical else "1920x1080",
        "duration_sec": duration_val,
        "title": meta_title,
        "description": desc,
        "desc": desc,
        "tags": tags,
        "keywords": tags,
        "topic_category": "music",
        "hook": hook,
        "track_info": track_info
    }
    (output_folder / "video_info.json").write_text(
        json.dumps(video_info_json, ensure_ascii=False, indent=2, default=json_default),
        encoding="utf-8"
    )

    log(100, f"Sinek Beyni Biyo-AI Müzik Videosu hazır! ({final_video_path.name})")

    return {
        "success": True,
        "video_path": str(final_video_path),
        "folder": str(output_folder),
        "duration_sec": duration_val,
        "title": meta_title,
        "track_info": track_info
    }
