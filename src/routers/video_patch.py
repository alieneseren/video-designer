"""
routers/video_patch.py
Hızlı Video Sahne Düzenleme & AI In-Place Yama API Router'ı
"""

import os
import json
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Body, Header, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from src.settings_manager import SettingsManager
from src.video_scene_patcher import (
    PATCH_PRESETS,
    analyze_critique_text,
    apply_local_video_patch,
    format_seconds_to_timestamp,
    parse_timestamp_to_seconds,
)

router = APIRouter(prefix="/api/video-patch", tags=["video-patch"])
settings_mgr = SettingsManager()


class AnalyzeCritiquePayload(BaseModel):
    video_folder: Optional[str] = None
    video_path: Optional[str] = None
    critique_text: str


class PatchItem(BaseModel):
    id: str
    start_sec: float
    end_sec: float
    start_time: str
    end_time: str
    duration: float
    issue_title: str
    replacement_type: str
    description: str
    enabled: bool = True


class ApplyPatchPayload(BaseModel):
    video_folder: Optional[str] = None
    video_path: Optional[str] = None
    patches: List[Dict[str, Any]]


def _get_project_output_dir() -> Path:
    """Proje kök dizinindeki output klasörünü güvenilir şekilde döner."""
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    cfg_out = settings_mgr.get("output_dir", "output")
    p = Path(cfg_out)
    if p.is_absolute() and p.exists():
        return p
    if (BASE_DIR / cfg_out).exists():
        return (BASE_DIR / cfg_out).resolve()
    return (BASE_DIR / "output").resolve()


def _resolve_video_file(folder: Optional[str], direct_path: Optional[str]) -> Path:
    """Verilen klasör veya direkt yoldan final.mp4 dosyasını bulur."""
    if direct_path:
        p = Path(direct_path).resolve()
        if p.exists():
            return p

    output_dir = _get_project_output_dir()
    if folder:
        # 1. output_dir / folder / final.mp4
        cand1 = output_dir / folder / "final.mp4"
        if cand1.exists():
            return cand1
        cand2 = output_dir / folder / "video.mp4"
        if cand2.exists():
            return cand2
        cand3 = Path(folder).resolve()
        if cand3.is_file() and cand3.exists():
            return cand3
        if cand3.is_dir():
            for f in ["final.mp4", "video.mp4"]:
                if (cand3 / f).exists():
                    return cand3 / f

    raise HTTPException(status_code=404, detail=f"Hedef video dosyası bulunamadı (Klasör: {folder}, Yol: {direct_path}).")


@router.get("/presets")
def get_patch_presets():
    """Kullanılabilir havacılık telemetri ve kokpit yama hazır şablonlarını listeler."""
    return {"presets": PATCH_PRESETS}


@router.post("/analyze")
def analyze_video_critique(payload: AnalyzeCritiquePayload):
    """
    Kullanıcının girdiği eleştiri veya sahne düzeltme komutunu analiz ederek
    değiştirilecek zaman aralıklarını ve önerilen görsel şablonlarını çıkarır.
    """
    v_file = _resolve_video_file(payload.video_folder, payload.video_path)
    
    # ffprobe ile tam süre
    ffprobe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(v_file)
    ]
    res_dur = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
    duration = float(res_dur.stdout.strip()) if res_dur.returncode == 0 else 0.0

    meta_file = v_file.parent / "metadata.json"
    title = v_file.parent.name
    scenes = []
    if meta_file.exists():
        try:
            m_data = json.loads(meta_file.read_text(encoding="utf-8"))
            title = m_data.get("title", title)
            scenes = m_data.get("scenes", [])
        except Exception:
            pass

    patches = analyze_critique_text(
        critique_text=payload.critique_text,
        video_duration=duration,
        video_title=title,
        scenes_meta=scenes
    )

    return {
        "success": True,
        "video_path": str(v_file),
        "video_title": title,
        "duration": duration,
        "duration_str": format_seconds_to_timestamp(duration),
        "detected_patches": patches,
        "count": len(patches)
    }


@router.post("/apply")
def apply_video_patches(payload: ApplyPatchPayload):
    """
    Seçilen yama kurallarını videoya uygular.
    Tüm video baştan render edilmez; yalnızca ilgili sahneler değiştirilip saniyeler içinde geri dikilir.
    """
    v_file = _resolve_video_file(payload.video_folder, payload.video_path)

    if not payload.patches:
        raise HTTPException(status_code=400, detail="Uygulanacak yama listesi boş.")

    try:
        res = apply_local_video_patch(
            video_path=str(v_file),
            patches=payload.patches
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yama uygulama hatası: {str(e)}")


class FolderActionPayload(BaseModel):
    folder_path: str
    critique_text: Optional[str] = None


@router.get("/kontrol-videos")
def list_kontrol_videos():
    """Tüm kanalların 'kontrol' klasörlerinde bekleyen videoları listeler."""
    output_dir = _get_project_output_dir()
    videos = []
    
    if not output_dir.exists():
        return {"success": True, "videos": [], "count": 0}

    for ch_dir in sorted(output_dir.iterdir()):
        if not ch_dir.is_dir() or ch_dir.name.startswith("."):
            continue
        kontrol_dir = ch_dir / "kontrol"
        if not kontrol_dir.exists() or not kontrol_dir.is_dir():
            continue

        for item in sorted(kontrol_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not item.is_dir() or item.name.startswith("."):
                continue

            v_file = item / "final.mp4"
            if not v_file.exists():
                v_file = item / "video.mp4"
            if not v_file.exists():
                continue

            size_mb = round(v_file.stat().st_size / (1024 * 1024), 2)
            meta_file = item / "metadata.json"
            title = item.name
            flight_name = ""
            desc = ""
            if meta_file.exists():
                try:
                    m = json.loads(meta_file.read_text(encoding="utf-8"))
                    title = m.get("title") or m.get("flight_name") or title
                    flight_name = m.get("flight_name") or ""
                    desc = m.get("description") or ""
                except Exception:
                    pass

            duration = 0.0
            try:
                cmd_dur = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(v_file)
                ]
                r = subprocess.run(cmd_dur, capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and r.stdout.strip():
                    duration = round(float(r.stdout.strip()), 1)
            except Exception:
                pass

            has_subtitles = (item / "subtitles.srt").exists()

            videos.append({
                "channel_id": ch_dir.name,
                "folder_name": item.name,
                "folder_path": str(item),
                "video_file": v_file.name,
                "video_path": str(v_file),
                "title": title,
                "flight_name": flight_name,
                "description": desc,
                "size_mb": size_mb,
                "duration": duration,
                "duration_str": format_seconds_to_timestamp(duration) if duration > 0 else "—",
                "has_subtitles": has_subtitles,
                "created_at": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
            })

    return {"success": True, "videos": videos, "count": len(videos)}


@router.api_route("/stream", methods=["GET", "HEAD"])
@router.api_route("/stream-file", methods=["GET", "HEAD"])
def stream_video_file(request: Request, path: str, range: Optional[str] = Header(None)):
    """Belirtilen video dosyasını binary stream olarak, HEAD ve HTTP Range (206) desteğiyle sunar."""
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")
    
    if p.suffix.lower() not in [".mp4", ".mkv", ".webm", ".mov", ".srt", ".json", ".wav", ".mp3"]:
        raise HTTPException(status_code=403, detail="Yalnızca medya dosyaları indirilebilir.")

    media_type = "video/mp4" if p.suffix.lower() == ".mp4" else "audio/mpeg" if p.suffix.lower() == ".mp3" else "application/octet-stream"
    file_size = p.stat().st_size

    # HEAD isteği: video oynatıcı meta ve boyut kontrolü
    if request.method == "HEAD":
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": media_type,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
        return Response(status_code=200, headers=headers, media_type=media_type)

    if range:
        try:
            range_str = range.replace("bytes=", "").strip()
            parts = range_str.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
            start = max(0, min(start, file_size - 1))
            end = max(start, min(end, file_size - 1))
            content_length = end - start + 1

            def iterfile(file_path, offset, length, chunk_size=1024 * 512):
                with open(file_path, "rb") as f:
                    f.seek(offset)
                    remaining = length
                    while remaining > 0:
                        read_bytes = min(remaining, chunk_size)
                        data = f.read(read_bytes)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
            return StreamingResponse(
                iterfile(str(p), start, content_length),
                status_code=206,
                headers=headers,
                media_type=media_type,
            )
        except Exception as e:
            print(f"[STREAM-RANGE] Uyarısı: {e}")

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }
    return FileResponse(str(p), media_type=media_type, filename=p.name, headers=headers)


@router.post("/approve-video")
def approve_video_to_upload(payload: FolderActionPayload):
    """
    Videoyu onaylar ve 'kontrol/' klasöründen 'yuklenecek/' klasörüne taşır.
    """
    f_path = Path(payload.folder_path).resolve()
    if not f_path.exists() or not f_path.is_dir():
        raise HTTPException(status_code=404, detail="Hedef klasör bulunamadı.")

    ch_dir = f_path.parent.parent
    yuklenecek_dir = ch_dir / "yuklenecek"
    yuklenecek_dir.mkdir(parents=True, exist_ok=True)

    dest = yuklenecek_dir / f_path.name
    if dest.exists():
        backup_name = f"{dest.name}_replaced_{int(time.time())}"
        shutil.move(str(dest), str(yuklenecek_dir / backup_name))

    # Onay raporu yaz
    report = {
        "status": "APPROVED",
        "approved_by": "Gemini Web Extension",
        "approved_at": datetime.now().isoformat(),
        "critique_notes": payload.critique_text or "Kusursuz onaylandı."
    }
    (f_path / "qa_gemini_approved.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Klasörü taşı
    shutil.move(str(f_path), str(dest))
    return {
        "success": True,
        "message": "Video başarıyla onaylandı ve 'yuklenecek' klasörüne taşındı.",
        "destination": str(dest)
    }


@router.post("/apply-critique-local")
def apply_critique_local(payload: FolderActionPayload):
    """
    Gemini'den gelen eleştiri metnini analiz eder ve in-place yama uygular.
    """
    f_path = Path(payload.folder_path).resolve()
    v_file = f_path / "final.mp4"
    if not v_file.exists():
        v_file = f_path / "video.mp4"
    if not v_file.exists():
        raise HTTPException(status_code=404, detail="Videoya ulaşılamadı.")

    if not payload.critique_text:
        raise HTTPException(status_code=400, detail="Eleştiri metni belirtilmedi.")

    cmd_dur = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(v_file)
    ]
    res_dur = subprocess.run(cmd_dur, capture_output=True, text=True)
    duration = float(res_dur.stdout.strip()) if res_dur.returncode == 0 else 0.0

    meta_file = f_path / "metadata.json"
    title = f_path.name
    scenes = []
    if meta_file.exists():
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8"))
            title = m.get("title", title)
            scenes = m.get("scenes", [])
        except Exception:
            pass

    patches = analyze_critique_text(
        critique_text=payload.critique_text,
        video_duration=duration,
        video_title=title,
        scenes_meta=scenes
    )

    if not patches:
        return {"success": False, "message": "Eleştiri metninde somut bir saniye veya yama bulunamadı.", "patches": []}

    res_patch = apply_local_video_patch(video_path=str(v_file), patches=patches)
    
    log_data = {
        "applied_at": datetime.now().isoformat(),
        "critique_text": payload.critique_text,
        "patches": patches,
        "result": res_patch
    }
    (f_path / "gemini_critique_patches.json").write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "success": True,
        "message": f"{len(patches)} sahne başarıyla yamalandı.",
        "patches": patches,
        "video_path": str(v_file)
    }


# ═════════════════════════════════════════════════════════════════════════════
# DEDICATED VIDEO EDITOR ENDPOINTS (Kes / Kırp / Sahne Değiştir / Müzik Değiştir)
# ═════════════════════════════════════════════════════════════════════════════

class TrimVideoPayload(BaseModel):
    video_path: str
    start_sec: float
    end_sec: float
    mode: str = "cut_segment"  # "keep_range" (kırp) veya "cut_segment" (aralığı sil ve birleştir)


class SwapBgmPayload(BaseModel):
    video_path: str
    track_id: str
    volume: float = 0.08


class RestoreBackupPayload(BaseModel):
    video_path: str


class ColorGradePayload(BaseModel):
    video_path: str
    preset: Optional[str] = "none"
    brightness: Optional[float] = 0.0
    contrast: Optional[float] = 1.0
    saturation: Optional[float] = 1.0
    vignette: Optional[bool] = False


class SpeedPayload(BaseModel):
    video_path: str
    speed: float = 1.0


class SplitRazorPayload(BaseModel):
    video_path: str
    split_sec: float


@router.get("/editable-videos")
def list_editable_videos():
    """Tüm kanallardaki düzenlenebilir video dosyalarını (yuklenecek, kontrol, tamamlanan) listeler."""
    output_dir = _get_project_output_dir()
    videos = []

    if not output_dir.exists():
        return {"success": True, "videos": [], "count": 0}

    # output altındaki tüm klasörleri tara
    scan_subdirs = ["yuklenecek", "kontrol", "yuklenen", ""]
    
    for ch_dir in sorted(output_dir.iterdir()):
        if not ch_dir.is_dir() or ch_dir.name.startswith("."):
            continue

        for sub in scan_subdirs:
            target_parent = (ch_dir / sub) if sub else ch_dir
            if not target_parent.exists() or not target_parent.is_dir():
                continue

            for item in sorted(target_parent.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if not item.is_dir() or item.name.startswith("."):
                    continue

                v_file = item / "final.mp4"
                if not v_file.exists():
                    v_file = item / "video.mp4"
                if not v_file.exists():
                    continue

                size_mb = round(v_file.stat().st_size / (1024 * 1024), 2)
                meta_file = item / "metadata.json"
                if not meta_file.exists():
                    meta_file = item / "video_info.json"

                title = item.name
                desc = ""
                channel_name = ch_dir.name
                if meta_file.exists():
                    try:
                        m = json.loads(meta_file.read_text(encoding="utf-8"))
                        title = m.get("title") or title
                        desc = m.get("description") or m.get("desc") or ""
                        channel_name = m.get("channel_id") or channel_name
                    except Exception:
                        pass

                duration = 0.0
                try:
                    cmd_dur = [
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(v_file)
                    ]
                    r = subprocess.run(cmd_dur, capture_output=True, text=True, timeout=5)
                    if r.returncode == 0 and r.stdout.strip():
                        duration = round(float(r.stdout.strip()), 1)
                except Exception:
                    pass

                has_backup = (item / "final_backup.mp4").exists() or (item / f"{v_file.stem}_backup.mp4").exists()
                thumb_file = item / "thumbnail.jpg"
                if not thumb_file.exists():
                    thumb_file = item / "thumbnail.png"

                videos.append({
                    "id": f"{ch_dir.name}_{item.name}",
                    "channel_id": channel_name,
                    "folder_name": item.name,
                    "folder_path": str(item),
                    "video_file": v_file.name,
                    "video_path": str(v_file),
                    "title": title,
                    "description": desc,
                    "size_mb": size_mb,
                    "duration": duration,
                    "duration_str": format_seconds_to_timestamp(duration) if duration > 0 else "—",
                    "has_backup": has_backup,
                    "has_thumbnail": thumb_file.exists(),
                    "thumbnail_path": str(thumb_file) if thumb_file.exists() else "",
                    "created_at": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })

    return {"success": True, "videos": videos, "count": len(videos)}


@router.get("/music-catalog")
def get_music_catalog():
    """Atıf gerektirmeyen (YouTube Audio Library No-Attribution) telifsiz müzik kataloğunu döner."""
    try:
        from src.audio_library import get_attribution_free_tracks
        tracks = get_attribution_free_tracks()
    except Exception:
        tracks = []
    return {"success": True, "tracks": tracks, "count": len(tracks)}


@router.api_route("/stream-audio", methods=["GET", "HEAD"])
def stream_music_track(track_id: str):
    """
    Belirtilen telifsiz müzik parçasını (track_id) canlı dinleme ve tarayıcıda senkron çalma için binary stream olarak sunar.
    Gerekirse otomatik indirir ve önbellekten sunar.
    """
    try:
        from src.audio_library import download_track
        project_root = Path(__file__).resolve().parent.parent.parent
        music_dir = project_root / "assets" / "music"
        music_dir.mkdir(parents=True, exist_ok=True)
        audio_file = download_track(track_id, music_dir)
        if not audio_file or not Path(audio_file).exists():
            raise HTTPException(status_code=404, detail=f"Müzik dosyası bulunamadı: {track_id}")
        p = Path(audio_file).resolve()
        return FileResponse(
            path=str(p),
            media_type="audio/mpeg",
            filename=p.name,
            headers={"Accept-Ranges": "bytes", "Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Müzik akış hatası: {str(e)}")


@router.post("/trim")
def trim_video_segment(payload: TrimVideoPayload):
    """
    Videoyu keser veya belirtilen aralığı videodan çıkarıp kalan kısımları birleştirir.
    Orijinal videoyu otomatik olarak final_backup.mp4 olarak saklar.
    """
    v_path = Path(payload.video_path).resolve()
    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")

    # Toplam süreyi al
    cmd_dur = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(v_path)
    ]
    r = subprocess.run(cmd_dur, capture_output=True, text=True, timeout=5)
    if r.returncode != 0 or not r.stdout.strip():
        raise HTTPException(status_code=500, detail="Video süresi okunamadı.")
    total_dur = float(r.stdout.strip())

    start_sec = max(0.0, float(payload.start_sec))
    end_sec = min(total_dur, float(payload.end_sec))

    if end_sec <= start_sec:
        raise HTTPException(status_code=400, detail="Bitiş süresi başlangıç süresinden büyük olmalıdır.")

    # Otomatik Yedekleme
    parent_dir = v_path.parent
    backup_file = parent_dir / "final_backup.mp4"
    if not backup_file.exists():
        shutil.copy2(v_path, backup_file)
    ts_backup = parent_dir / f"{v_path.stem}_backup_{int(time.time())}.mp4"
    shutil.copy2(v_path, ts_backup)

    temp_out = parent_dir / f"temp_trim_{int(time.time())}.mp4"

    try:
        if payload.mode == "keep_range":
            # Yalnızca seçili aralığı tut
            dur_keep = end_sec - start_sec
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-to", str(end_sec),
                "-i", str(v_path),
                "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                "-c:a", "aac", "-b:a", "192k",
                str(temp_out)
            ]
        else:
            # cut_segment: Seçilen aralığı videodan sil ve iki ucu birleştir
            fc = (
                f"[0:v]trim=0:{start_sec:.3f},setpts=PTS-STARTPTS[v1];"
                f"[0:a]atrim=0:{start_sec:.3f},asetpts=PTS-STARTPTS[a1];"
                f"[0:v]trim={end_sec:.3f}:{total_dur:.3f},setpts=PTS-STARTPTS[v2];"
                f"[0:a]atrim={end_sec:.3f}:{total_dur:.3f},asetpts=PTS-STARTPTS[a2];"
                f"[v1][a1][v2][a2]concat=n=2:v=1:a=1[vout][aout]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", str(v_path),
                "-filter_complex", fc,
                "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                "-c:a", "aac", "-b:a", "192k",
                str(temp_out)
            ]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg trim hatası: {res.stderr[-1000:]}")

        # Orijinal dosyanın yerine geçir
        shutil.move(temp_out, v_path)
        if v_path.name == "final.mp4":
            other = parent_dir / "video.mp4"
            if other.exists():
                shutil.copy2(v_path, other)

        # Yeni süreyi al
        r_new = subprocess.run(cmd_dur, capture_output=True, text=True, timeout=5)
        new_dur = float(r_new.stdout.strip()) if r_new.returncode == 0 else 0.0

        return {
            "success": True,
            "mode": payload.mode,
            "new_duration": round(new_dur, 1),
            "new_duration_str": format_seconds_to_timestamp(new_dur),
            "message": f"Video başarıyla düzenlendi. Yeni süre: {format_seconds_to_timestamp(new_dur)}"
        }
    except Exception as e:
        if temp_out.exists():
            temp_out.unlink()
        raise HTTPException(status_code=500, detail=f"Kesme işlemi başarısız: {str(e)}")


@router.post("/swap-bgm")
def swap_video_bgm(payload: SwapBgmPayload):
    """
    Videonun arka plan müziğini (BGM) YouTube Audio Library atıf gerektirmeyen seçilen müzikle değiştirir.
    Görsel yeniden encode edilmez (-c:v copy), 2-3 saniyede tamamlanır!
    """
    v_path = Path(payload.video_path).resolve()
    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")

    try:
        from src.audio_library import download_track, get_track_by_id
    except ImportError:
        import audio_library as _al
        download_track = _al.download_track
        get_track_by_id = _al.get_track_by_id

    project_root = Path(__file__).resolve().parent.parent.parent
    music_dir = project_root / "assets" / "music"
    music_dir.mkdir(parents=True, exist_ok=True)

    bgm_file = download_track(payload.track_id, music_dir)
    if not bgm_file or not Path(bgm_file).exists():
        raise HTTPException(status_code=500, detail=f"Müzik dosyası indirilemedi/bulunamadı: {payload.track_id}")

    parent_dir = v_path.parent
    backup_file = parent_dir / "final_backup.mp4"
    if not backup_file.exists():
        shutil.copy2(v_path, backup_file)

    temp_out = parent_dir / f"temp_bgm_{int(time.time())}.mp4"
    vol = max(0.0, min(0.40, float(payload.volume or 0.08)))

    # 1. Temiz dış ses dosyası var mı kontrol et (narration.wav vb.)
    clean_voice = None
    for cand_name in ["narration.wav", "narration.mp3", "voice.wav", "voiceover.wav", "clean_voice.wav"]:
        cand = parent_dir / cand_name
        if cand.exists() and cand.stat().st_size > 1000:
            clean_voice = cand
            break

    try:
        # Eğer ses seviyesi 0 veya çok düşükse müziği tamamen kapat
        if vol <= 0.005:
            if clean_voice:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(v_path),
                    "-i", str(clean_voice),
                    "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(temp_out)
                ]
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(v_path),
                    "-an",
                    "-c:v", "copy",
                    str(temp_out)
                ]
        else:
            if clean_voice:
                fc = f"[1:a]volume={vol:.3f}[bgm];[2:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(v_path),
                    "-stream_loop", "-1", "-i", str(bgm_file),
                    "-i", str(clean_voice),
                    "-filter_complex", fc,
                    "-map", "0:v", "-map", "[aout]",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(temp_out)
                ]
            else:
                fc = f"[1:a]volume={vol:.3f}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(v_path),
                    "-stream_loop", "-1", "-i", str(bgm_file),
                    "-filter_complex", fc,
                    "-map", "0:v", "-map", "[aout]",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(temp_out)
                ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg BGM miks hatası: {res.stderr[-1000:]}")

        shutil.move(temp_out, v_path)
        if v_path.name == "final.mp4":
            other = parent_dir / "video.mp4"
            if other.exists():
                shutil.copy2(v_path, other)

        track_info = get_track_by_id(payload.track_id) or {"title": payload.track_id}
        return {
            "success": True,
            "track_id": payload.track_id,
            "track_name": track_info.get("title"),
            "volume": vol,
            "message": f"Arka plan müziği başarıyla değiştirildi: {track_info.get('title')}"
        }
    except Exception as e:
        if temp_out.exists():
            temp_out.unlink()
        raise HTTPException(status_code=500, detail=f"Müzik değiştirme hatası: {str(e)}")


@router.post("/restore-backup")
def restore_video_backup(payload: RestoreBackupPayload):
    """Yedeklenen orijinal videoyu geri yükler."""
    v_path = Path(payload.video_path).resolve()
    parent_dir = v_path.parent
    backup_file = parent_dir / "final_backup.mp4"

    if not backup_file.exists():
        # Zaman damgalı yedeklerden en sonuncusunu ara
        backups = sorted(parent_dir.glob("*_backup_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            backup_file = backups[0]

    if not backup_file or not backup_file.exists():
        raise HTTPException(status_code=404, detail="Geri yüklenecek orijinal yedek video bulunamadı.")

    try:
        shutil.copy2(backup_file, v_path)
        if v_path.name == "final.mp4":
            other = parent_dir / "video.mp4"
            if other.exists():
                shutil.copy2(backup_file, other)

        return {"success": True, "message": "Orijinal video başarıyla geri yüklendi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geri yükleme hatası: {str(e)}")


@router.post("/color-grade")
def apply_color_grading(payload: ColorGradePayload):
    """
    After Effects kalitesinde renk düzenleme (LUT, Parlaklık, Kontrast, Doygunluk, Vinyet) uygular.
    Orijinal ses kanalına dokunulmaz (-c:a copy).
    """
    v_path = Path(payload.video_path).resolve()
    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")

    parent_dir = v_path.parent
    backup_file = parent_dir / "final_backup.mp4"
    if not backup_file.exists():
        shutil.copy2(v_path, backup_file)

    temp_out = parent_dir / f"temp_grade_{int(time.time())}.mp4"

    filters = []
    b = max(-0.5, min(0.5, float(payload.brightness or 0.0)))
    c = max(0.5, min(2.0, float(payload.contrast or 1.0)))
    s = max(0.0, min(2.0, float(payload.saturation or 1.0)))

    preset = str(payload.preset or "none").lower()
    if preset == "teal_orange":
        filters.append("colorchannelmixer=.4:.5:.1:0:.1:.8:.1:0:0:.2:.8:0,eq=contrast=1.2:saturation=1.25")
    elif preset == "tactical_cyan":
        filters.append("colorchannelmixer=.2:.4:.4:0:.1:.7:.2:0:.1:.2:.9:0,eq=contrast=1.3:saturation=1.35")
    elif preset == "night_vision":
        filters.append("colorchannelmixer=0:0:0:0:0:1:0:0:0:0:0:0,eq=contrast=1.45:brightness=0.04")
    elif preset == "bw_noir":
        filters.append("hue=s=0,eq=contrast=1.4:brightness=-0.02")
    elif preset == "retro_crt":
        filters.append("eq=contrast=1.2:saturation=1.15,drawgrid=w=iw:h=4:t=1:c=black@0.15")
    else:
        if b != 0.0 or c != 1.0 or s != 1.0:
            filters.append(f"eq=brightness={b:.2f}:contrast={c:.2f}:saturation={s:.2f}")

    if payload.vignette:
        filters.append("vignette=PI/4")

    if not filters:
        filters.append("null")

    vf_str = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(v_path),
        "-vf", vf_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "19",
        "-c:a", "copy",
        str(temp_out)
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg Color Grading hatası: {res.stderr[-1000:]}")

        shutil.move(temp_out, v_path)
        if v_path.name == "final.mp4":
            other = parent_dir / "video.mp4"
            if other.exists():
                shutil.copy2(v_path, other)

        return {
            "success": True,
            "preset": preset,
            "message": f"Renk derecelendirme ({preset.replace('_', ' ').title()}) başarıyla uygulandı."
        }
    except Exception as e:
        if temp_out.exists():
            temp_out.unlink()
        raise HTTPException(status_code=500, detail=f"Renk derecelendirme hatası: {str(e)}")


@router.post("/speed")
def apply_speed_change(payload: SpeedPayload):
    """
    Videonun oynatma hızını (0.5x, 0.75x, 1.25x, 1.5x, 2.0x) ses ve görüntü senkronuyla değiştirir.
    """
    v_path = Path(payload.video_path).resolve()
    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")

    speed = max(0.25, min(4.0, float(payload.speed or 1.0)))
    if abs(speed - 1.0) < 0.01:
        return {"success": True, "message": "Hız zaten 1.0x (normal)."}

    parent_dir = v_path.parent
    backup_file = parent_dir / "final_backup.mp4"
    if not backup_file.exists():
        shutil.copy2(v_path, backup_file)

    temp_out = parent_dir / f"temp_speed_{int(time.time())}.mp4"

    pts_factor = 1.0 / speed
    fc = f"[0:v]setpts={pts_factor:.4f}*PTS[v];[0:a]atempo={speed:.4f}[a]"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(v_path),
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k",
        str(temp_out)
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg hızlandırma hatası: {res.stderr[-1000:]}")

        shutil.move(temp_out, v_path)
        if v_path.name == "final.mp4":
            other = parent_dir / "video.mp4"
            if other.exists():
                shutil.copy2(v_path, other)

        return {
            "success": True,
            "speed": speed,
            "message": f"Video hızı başarıyla {speed}x olarak ayarlandı."
        }
    except Exception as e:
        if temp_out.exists():
            temp_out.unlink()
        raise HTTPException(status_code=500, detail=f"Hız değiştirme hatası: {str(e)}")


@router.post("/split-razor")
def split_at_playhead(payload: SplitRazorPayload):
    """
    Playhead noktasında videoyu After Effects Razor Blade gibi 2 parçaya ayırır.
    """
    v_path = Path(payload.video_path).resolve()
    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")

    split_sec = float(payload.split_sec)
    parent_dir = v_path.parent

    cmd_dur = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(v_path)
    ]
    r = subprocess.run(cmd_dur, capture_output=True, text=True, timeout=5)
    total_dur = float(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else 10.0

    if split_sec <= 0.5 or split_sec >= total_dur - 0.5:
        raise HTTPException(status_code=400, detail="Bölme noktası videonun en başında veya en sonunda olamaz.")

    part1_out = parent_dir / f"{v_path.stem}_part1.mp4"
    part2_out = parent_dir / f"{v_path.stem}_part2.mp4"

    cmd1 = [
        "ffmpeg", "-y", "-i", str(v_path),
        "-to", f"{split_sec:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k",
        str(part1_out)
    ]
    cmd2 = [
        "ffmpeg", "-y", "-ss", f"{split_sec:.3f}", "-i", str(v_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k",
        str(part2_out)
    ]

    try:
        subprocess.run(cmd1, capture_output=True, text=True, check=True)
        subprocess.run(cmd2, capture_output=True, text=True, check=True)
        return {
            "success": True,
            "split_sec": split_sec,
            "part1": part1_out.name,
            "part2": part2_out.name,
            "message": f"Klip {format_seconds_to_timestamp(split_sec)} anında 2 parçaya bölündü ({part1_out.name}, {part2_out.name})."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bıçakla bölme hatası: {str(e)}")


