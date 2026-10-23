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
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse

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


def _resolve_video_file(folder: Optional[str], direct_path: Optional[str]) -> Path:
    """Verilen klasör veya direkt yoldan final.mp4 dosyasını bulur."""
    if direct_path:
        p = Path(direct_path).resolve()
        if p.exists():
            return p

    output_dir = Path(settings_mgr.get("output_dir", "output")).resolve()
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
    output_dir = Path(settings_mgr.get("output_dir", "output")).resolve()
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


@router.get("/stream-file")
def stream_video_file(path: str):
    """Belirtilen video dosyasını binary stream olarak sunar (Chrome eklentisi Blob indirmesi için)."""
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")
    
    if p.suffix.lower() not in [".mp4", ".mkv", ".webm", ".mov", ".srt", ".json"]:
        raise HTTPException(status_code=403, detail="Yalnızca medya dosyaları indirilebilir.")

    media_type = "video/mp4" if p.suffix.lower() == ".mp4" else "application/octet-stream"
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
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

