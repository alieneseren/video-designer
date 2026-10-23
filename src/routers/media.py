"""
Media router: File upload, video file streaming, and audio library.
"""
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from audio_library import TRACKS

router = APIRouter(tags=["Media"])


@router.post("/api/upload")
def upload_file(
    file: UploadFile = File(...),
    category: str = Form("assets")  # bgm, watermark, intro, outro, etc.
):
    try:
        allowed_categories = {"bgm", "watermark", "intro", "outro", "assets"}
        if category not in allowed_categories:
            category = "assets"
            
        assets_dir = Path("config/assets") / category
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._-").strip()
        if not safe_filename:
            safe_filename = "uploaded_file"
            
        file_path = assets_dir / safe_filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "success": True,
            "file_path": str(file_path),
            "filename": safe_filename,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/video-file")
def stream_video_file(path: str):
    """Verilen video_path dosyasını doğrudan döner."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")
    return FileResponse(str(p), media_type="video/mp4")


@router.get("/api/audio-library")
def get_audio_library():
    """Ses kitaplığındaki tüm parçaları döndürür."""
    return {"success": True, "tracks": TRACKS}
