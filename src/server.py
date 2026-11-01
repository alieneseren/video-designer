"""
server.py
FastAPI backend — Video üretim API + Dashboard statik hosting.
Google auth kaldırıldı. Çoklu AI provider desteği.
"""

import os
import sys
import re
import json
import time
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import shutil
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, Form, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# src/ modüllerini import edebilmek için src dizinini path'e ekle
_PROJECT_ROOT = Path(__file__).resolve().parent.parent  # files/
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from channel_manager import ChannelManager, get_localized_metadata
from script_writer import ScriptWriter
from video_generator import VideoGenerator
from settings_manager import SettingsManager
from main import run_channel
from instagram_scheduler import InstagramScheduleStore

app = FastAPI(title="Video Üretim API")

class AutoGCWatchdog:
    """
    Casper AI: Akıllı GPU & Bellek Temizleyici (Auto-GC Nöbetçisi).
    Graphify analizindeki alt modüllerin, PyTorch, NumPy ve moviepy nesnelerinin
    arka planda bıraktığı bellek kalıntılarını render aralarında ve periyodik olarak temizler.
    """
    _running: bool = False
    _last_cleanup: float = 0.0
    _total_cleanups: int = 0
    _last_gc_collected: int = 0
    _last_trigger: str = "init"
    _history: List[Dict[str, Any]] = []
    _lock = threading.Lock()

    @classmethod
    def clean(cls, trigger: str = "manual") -> dict:
        import gc
        import time
        now = time.time()
        freed_details = {
            "trigger": trigger,
            "timestamp": now,
            "gc_collected": 0,
            "gpu_cleared": False,
            "cuda_cleared": False,
            "mps_cleared": False,
        }
        with cls._lock:
            try:
                # 1. Python GC döngüsel referans temizliği (tüm jenerasyonlar)
                collected = gc.collect()
                freed_details["gc_collected"] = collected

                # 2. PyTorch GPU VRAM Temizliği (CUDA & Apple Silicon MPS)
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        if hasattr(torch.cuda, "ipc_collect"):
                            torch.cuda.ipc_collect()
                        freed_details["gpu_cleared"] = True
                        freed_details["cuda_cleared"] = True
                    if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache") and torch.backends.mps.is_available():
                        torch.mps.empty_cache()
                        freed_details["gpu_cleared"] = True
                        freed_details["mps_cleared"] = True
                except (ImportError, Exception):
                    pass

                # 3. C-level heap trim (NumPy / Pillow / FFmpeg kalıntılarını işletim sistemine iade et)
                try:
                    import ctypes
                    ctypes.CDLL("libc.so.6").malloc_trim(0)
                except Exception:
                    pass

                cls._last_cleanup = now
                cls._total_cleanups += 1
                cls._last_gc_collected = collected
                cls._last_trigger = trigger

                # Son 20 temizlik kaydını tut
                cls._history.append({
                    "timestamp": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S"),
                    "trigger": trigger,
                    "gc_collected": collected,
                    "gpu_cleared": freed_details["gpu_cleared"],
                })
                if len(cls._history) > 20:
                    cls._history.pop(0)

                print(f"[AUTO-GC] 🧹 Akıllı bellek & GPU temizliği tamamlandı (Tetikleyici: {trigger}, Toplanan: {collected}, GPU: {freed_details['gpu_cleared']})")
            except Exception as e:
                print(f"[AUTO-GC] Temizlik uyarısı: {e}")
        return freed_details

    @classmethod
    def clean_async(cls, trigger: str = "async_trigger"):
        """Render bitiminde ana akışı bekletmeden arka planda temizlik tetikler."""
        t = threading.Thread(target=cls.clean, kwargs={"trigger": trigger}, daemon=True, name=f"AutoGCAsync-{trigger}")
        t.start()
        return t

    @classmethod
    def start_sentinel(cls, interval_sec: int = 300):
        if cls._running:
            return
        cls._running = True

        def _sentinel_loop():
            while cls._running:
                time.sleep(interval_sec)
                # Son temizlikten bu yana en az 180 saniye geçmişse koruma temizliği yap
                if time.time() - cls._last_cleanup >= 180:
                    cls.clean(trigger="sentinel_timer")

        t = threading.Thread(target=_sentinel_loop, daemon=True, name="AutoGCSentinelThread")
        t.start()
        print(f"[AUTO-GC] 🛡️ Akıllı bellek nöbetçisi arka planda başlatıldı (Periyot: {interval_sec}s).")

    @classmethod
    def get_status(cls) -> dict:
        gpu_info = {"cuda_available": False, "mps_available": False}
        try:
            import torch
            gpu_info["cuda_available"] = bool(torch.cuda.is_available())
            gpu_info["mps_available"] = bool(hasattr(torch, "mps") and torch.backends.mps.is_available())
        except Exception:
            pass

        return {
            "running": cls._running,
            "last_cleanup": cls._last_cleanup,
            "last_cleanup_iso": datetime.fromtimestamp(cls._last_cleanup).isoformat() if cls._last_cleanup else None,
            "total_cleanups": cls._total_cleanups,
            "last_trigger": cls._last_trigger,
            "last_gc_collected": cls._last_gc_collected,
            "gpu_info": gpu_info,
            "recent_history": list(cls._history),
        }


def _clear_memory(trigger: str = "render_step"):
    """Video üretimleri ve render sonrasında RAM/VRAM kalıntılarını temizler."""
    return AutoGCWatchdog.clean(trigger=trigger)


@contextmanager
def auto_gc_scope(trigger: str = "render_scope"):
    """Video render bloğunda hata oluşsa dahi blok bitiminde GPU ve RAM temizliğini garanti eder."""
    try:
        yield
    finally:
        _clear_memory(trigger=f"{trigger}_scope_exit")


AutoGCWatchdog.start_sentinel(interval_sec=300)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://studio.youtube.com",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings_mgr = SettingsManager()
instagram_schedule_store = InstagramScheduleStore()
from core.state import execution_manager
executions = execution_manager.list_all()

def _get_configured_script_writer():
    from script_writer import ScriptWriter
    provider = settings_mgr.get("ai_provider", "gemini")
    api_key = settings_mgr.get(f"{provider}_api_key", "")
    if not api_key and provider == "gemini":
        api_key = settings_mgr.get("gemini_api_key", "")
    elif not api_key and provider == "claude":
        api_key = settings_mgr.get("anthropic_api_key", "")
    ai_model = settings_mgr.get(f"{provider}_model", "") or settings_mgr.get("ai_model", "")
    return ScriptWriter(
        provider=provider,
        api_key=api_key,
        model=ai_model,
        ollama_url=settings_mgr.get("ollama_url", "http://localhost:11434"),
        lmstudio_url=settings_mgr.get("lmstudio_url", "http://localhost:1234/v1"),
    )

from routers import (
    settings_router,
    channels_router,
    media_router,
    browser_router,
    outputs_router,
    video_patch_router,
    procedural_video_router,
)

app.include_router(settings_router)
app.include_router(channels_router)
app.include_router(media_router)
app.include_router(browser_router)
app.include_router(outputs_router)
app.include_router(video_patch_router)
app.include_router(procedural_video_router)




# ── Schemas ────────────────────────────────────────────────────

class ChannelSchema(BaseModel):
    channel_id: str
    name: str
    language: str
    topic_category: str = "space"
    custom_topics: List[str] = []
    schedule_hour: int = 9
    active: bool = True
    shorts_mode: bool = False
    transition: str = "fade"   # fade | zoom | slide | none | kenburns
    edit_options: Optional[dict] = None
    instagram: Optional[bool] = None
    instagram_username: Optional[str] = None
    instagram_user_id: Optional[str] = None

class ToggleSchema(BaseModel):
    active: bool

class SocialSchema(BaseModel):
    instagram: Optional[bool] = None
    instagram_username: Optional[str] = None
    tiktok: Optional[bool] = None

class TopicImportItem(BaseModel):
    baslik: Optional[str] = None
    title: Optional[str] = None
    konu: Optional[str] = None
    topic: Optional[str] = None
    name: Optional[str] = None
    
    yonergeler: Optional[str] = None
    instructions: Optional[str] = None
    yönerge: Optional[str] = None
    instruction: Optional[str] = None
    description: Optional[str] = None
    script: Optional[dict] = None
    images: Optional[dict] = None
    notes: Optional[str] = None

    class Config:
        extra = "allow"

class ImportTopicsRequest(BaseModel):
    topics: List[TopicImportItem]

class SettingsUpdate(BaseModel):
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    nasa_api_key: Optional[str] = None
    instagram_access_token: Optional[str] = None
    instagram_user_id: Optional[str] = None
    instagram_public_base_url: Optional[str] = None
    instagram_graph_api_version: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    lmstudio_url: Optional[str] = None
    lmstudio_model: Optional[str] = None
    output_dir: Optional[str] = None
    tts_engine: Optional[str] = None
    chatterbox_voice: Optional[str] = None
    # Video edit (v3)
    subtitle_preset: Optional[str] = None
    subtitle_animation: Optional[str] = None
    bgm_path: Optional[str] = None
    bgm_volume: Optional[str] = None
    watermark_path: Optional[str] = None
    watermark_text: Optional[str] = None
    watermark_position: Optional[str] = None
    intro_clip_path: Optional[str] = None
    outro_clip_path: Optional[str] = None
    kenburns_intensity: Optional[str] = None
    transition_dur: Optional[str] = None
    video_duration: Optional[str] = None
    censor_faces: Optional[bool] = None


# ═══════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/settings")
def get_settings():
    return settings_mgr.get_masked()

@app.put("/api/settings")
def update_settings(payload: SettingsUpdate):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    return settings_mgr.update(updates)

@app.post("/api/upload")
def upload_file(
    file: UploadFile = File(...),
    category: str = Form("assets") # bgm, watermark, intro, outro, etc.
):
    try:
        allowed_categories = {"bgm", "watermark", "intro", "outro", "assets"}
        if category not in allowed_categories:
            category = "assets"
            
        assets_dir = Path("config/assets") / category
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean file name
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


# ═══════════════════════════════════════════════════════════════
# VOICE CLONING (RVC / CHATTERBOX / NEURAL STUDIO)
# ═══════════════════════════════════════════════════════════════

class StartVoiceCloneRequest(BaseModel):
    name: str
    temp_path: str
    description: Optional[str] = ""

class TestVoiceCloneRequest(BaseModel):
    text: str
    lang: Optional[str] = "tr"
    pitch: Optional[int] = 0
    formant: Optional[float] = 1.0

@app.get("/api/voice-clones")
def get_voice_clones():
    from voice_clone_manager import VoiceCloneManager
    mgr = VoiceCloneManager()
    active_clone = mgr.get_active_clone()
    clones = mgr.list_clones()
    for clone in clones:
        prompts = [clone.get("voice_pt_path"), clone.get("voice_wav_path")]
        clone["voice_prompt_available"] = any(prompt and Path(prompt).is_file() for prompt in prompts)
    return {
        "clones": clones,
        "active_id": active_clone.get("id") if active_clone else "",
        "device": mgr.get_device()
    }

@app.post("/api/voice-clones/upload")
def upload_voice_clone_sample(file: UploadFile = File(...)):
    try:
        from voice_clone_manager import TEMP_DIR
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename).suffix.lower() or ".wav"
        temp_name = f"sample_{int(time.time()*1000)}{ext}"
        target_path = TEMP_DIR / temp_name
        with open(target_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)

        size_kb = round(target_path.stat().st_size / 1024, 1)
        return {
            "success": True,
            "filename": file.filename,
            "temp_path": str(target_path.resolve()),
            "size_kb": size_kb
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ses yükleme hatası: {str(e)}")

@app.post("/api/voice-clones/start")
def start_voice_clone(req: StartVoiceCloneRequest):
    try:
        from voice_clone_manager import VoiceCloneManager
        mgr = VoiceCloneManager()
        job_id = mgr.start_cloning_job(
            name=req.name,
            temp_audio_path=req.temp_path,
            description=req.description or ""
        )
        return {"success": True, "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voice-clones/jobs/{job_id}")
def get_voice_clone_job_status(job_id: str):
    from voice_clone_manager import VoiceCloneManager
    mgr = VoiceCloneManager()
    status = mgr.get_job_status(job_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Klonlama işi bulunamadı")
    return status

@app.post("/api/voice-clones/{clone_id}/activate")
def activate_voice_clone(clone_id: str):
    from voice_clone_manager import VoiceCloneManager
    mgr = VoiceCloneManager()
    found = mgr.get_clone(clone_id)
    if not found:
        raise HTTPException(status_code=404, detail="Ses profili bulunamadı")
    ok = mgr.activate_clone(clone_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Ses profili aktif edilemedi")

    voice_path = found.get("voice_pt_path") or found.get("voice_wav_path") or ""
    settings_mgr.update({
        "tts_engine": "chatterbox",
        "chatterbox_voice": str(voice_path),
        "active_voice_clone_id": clone_id,
        "rvc_pth_path": str(found.get("rvc_pth_path") or ""),
        "rvc_index_path": str(found.get("rvc_index_path") or "")
    })
    return {"success": True, "active_id": clone_id}

@app.delete("/api/voice-clones/{clone_id}")
def delete_voice_clone(clone_id: str):
    from voice_clone_manager import VoiceCloneManager
    mgr = VoiceCloneManager()
    ok = mgr.delete_clone(clone_id)
    return {"success": ok}

@app.get("/api/voice-clones/{clone_id}/preview")
def get_voice_clone_preview(clone_id: str):
    from voice_clone_manager import CLONES_DIR
    target_dir = CLONES_DIR / clone_id
    preview_file = target_dir / "preview.wav"
    if not preview_file.exists():
        preview_file = target_dir / "voice.wav"
    if not preview_file.exists():
        raise HTTPException(status_code=404, detail="Önizleme ses dosyası bulunamadı")
    return FileResponse(str(preview_file), media_type="audio/wav")

@app.post("/api/voice-clones/{clone_id}/test")
def test_voice_clone(clone_id: str, req: TestVoiceCloneRequest):
    from voice_clone_manager import VoiceCloneManager
    mgr = VoiceCloneManager()
    audio_path = mgr.synthesize_custom_test(
        clone_id,
        req.text,
        req.lang or "tr",
        pitch=req.pitch or 0,
        formant=req.formant if req.formant is not None else 1.0
    )
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=500, detail="Test sesi sentezlenemedi")
    return FileResponse(audio_path, media_type="audio/wav")


@app.post("/api/watermark/verify")
async def verify_watermark_endpoint(file: UploadFile = File(...)):
    """Yüklenen ses veya video dosyasında Ali Enes ultrasonik telif filigranını denetler."""
    temp_path = None
    try:
        from audio_watermark import AudioWatermarker
        suffix = Path(file.filename or "media.wav").suffix or ".wav"
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        res = AudioWatermarker.verify(temp_path)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            try: os.unlink(temp_path)
            except Exception: pass



# ═══════════════════════════════════════════════════════════════
# CHANNELS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/channels")
def get_channels():
    return ChannelManager().all_channels()

@app.post("/api/channels")
def add_channel(channel: ChannelSchema):
    try:
        new_ch = ChannelManager().add_channel(
            channel_id=channel.channel_id, name=channel.name,
            language=channel.language, topic_category=channel.topic_category,
            custom_topics=channel.custom_topics, schedule_hour=channel.schedule_hour,
            active=channel.active,
            shorts_mode=channel.shorts_mode,
            transition=channel.transition,
            edit_options=channel.edit_options,
            instagram=bool(channel.instagram),
            instagram_username=channel.instagram_username,
            instagram_user_id=channel.instagram_user_id,
        )
        try:
            from mind_map import MindMapManager
            output_dir = settings_mgr.get("output_dir", "output")
            channel_dir = Path(output_dir) / channel.channel_id
            mm_mgr = MindMapManager(channel_dir)
            if not mm_mgr.exists():
                writer = _get_configured_script_writer()
                mm_mgr.bootstrap_or_load(writer, channel_config=new_ch)
        except Exception as b_err:
            print(f"[MIND MAP] Kanal oluşturma sırasında zihin haritası başlatma uyarısı: {b_err}")

        return new_ch
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/channels/{channel_id}/toggle")
def toggle_channel(channel_id: str, payload: ToggleSchema):
    mgr = ChannelManager()
    if not mgr.get_channel(channel_id):
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    mgr.set_active(channel_id, payload.active)
    return {"success": True, "active": payload.active}


@app.put("/api/channels/{channel_id}/social")
def toggle_channel_social(channel_id: str, payload: SocialSchema):
    mgr = ChannelManager()
    channel = mgr.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    
    if payload.instagram is not None:
        channel["instagram"] = payload.instagram
    if payload.instagram_username is not None:
        channel["instagram_username"] = payload.instagram_username.strip().lstrip("@")
    if payload.tiktok is not None:
        channel["tiktok"] = payload.tiktok
        
    mgr._save()
    return {
        "success": True,
        "channel_id": channel_id,
        "instagram": channel.get("instagram", False),
        "instagram_username": channel.get("instagram_username", ""),
        "instagram_user_id": channel.get("instagram_user_id", ""),
        "tiktok": channel.get("tiktok", False)
    }

@app.put("/api/channels/{channel_id}")
def update_channel(channel_id: str, channel: ChannelSchema):
    mgr = ChannelManager()
    existing = mgr.get_channel(channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    return mgr.add_channel(
        channel_id=channel.channel_id, name=channel.name,
        language=channel.language, topic_category=channel.topic_category,
        custom_topics=channel.custom_topics, schedule_hour=channel.schedule_hour,
        active=channel.active,
        shorts_mode=channel.shorts_mode,
        transition=channel.transition,
        edit_options=channel.edit_options,
        instagram=channel.instagram if channel.instagram is not None else existing.get("instagram", False),
        instagram_username=channel.instagram_username,
        instagram_user_id=channel.instagram_user_id,
    )

@app.delete("/api/channels/{channel_id}")
def delete_channel(channel_id: str):
    mgr = ChannelManager()
    if not mgr.get_channel(channel_id):
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    mgr.remove_channel(channel_id)
    return {"success": True, "deleted": channel_id}


@app.post("/api/channels/{channel_id}/apply-preset")
def apply_channel_category_preset(channel_id: str, overwrite: bool = False):
    """Kanalın konu kategorisine (topic_category) göre en ideal viral YouTube & Shorts ayarlarını uygular."""
    mgr = ChannelManager()
    res = mgr.apply_category_preset(channel_id, overwrite_custom=overwrite)
    if not res:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    return {"success": True, "channel": res}


@app.post("/api/channels/apply-all-presets")
def apply_all_channels_category_presets(overwrite: bool = False):
    """Sistemdeki tüm kanalları konu kategorilerine göre otomatik optimize eder."""
    mgr = ChannelManager()
    updated = mgr.apply_all_category_presets(overwrite_custom=overwrite)
    return {"success": True, "count": len(updated), "channels": updated}


# ═══════════════════════════════════════════════════════════════
# KANAL GRUPLARI & ÇOK DİLLİ ORTAK PLANLAMA
# ═══════════════════════════════════════════════════════════════

class GroupSchema(BaseModel):
    name: str
    topic_category: str
    channel_ids: list[str]
    reddit_avatar_path: Optional[str] = None
    reddit_username: Optional[str] = None

@app.get("/api/groups")
def get_groups():
    mgr = ChannelManager()
    groups = mgr.all_groups()
    res = []
    for g in groups:
        member_channels = []
        for cid in g.get("channel_ids", []):
            ch = mgr.get_channel(cid)
            if ch:
                member_channels.append({
                    "channel_id": ch["channel_id"],
                    "name": ch["name"],
                    "language": ch["language"],
                    "topic_category": ch["topic_category"],
                    "active": ch.get("active", True),
                })
        res.append({
            **g,
            "channels": member_channels,
            "languages": list({ch["language"] for ch in member_channels}),
        })
    return res

@app.post("/api/groups")
def create_group(payload: GroupSchema):
    mgr = ChannelManager()
    try:
        group = mgr.add_group(
            name=payload.name,
            topic_category=payload.topic_category,
            channel_ids=payload.channel_ids,
            reddit_avatar_path=payload.reddit_avatar_path,
            reddit_username=payload.reddit_username,
        )
        return {"success": True, "group": group}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/groups/{group_id}")
def update_group(group_id: str, payload: GroupSchema):
    mgr = ChannelManager()
    try:
        group = mgr.update_group(
            group_id=group_id,
            name=payload.name,
            channel_ids=payload.channel_ids,
            reddit_avatar_path=payload.reddit_avatar_path,
            reddit_username=payload.reddit_username,
        )
        return {"success": True, "group": group}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/groups/{group_id}")
def delete_group(group_id: str):
    mgr = ChannelManager()
    mgr.delete_group(group_id)
    return {"success": True}

@app.get("/api/channels-and-groups")
def get_channels_and_groups():
    """
    Eklenti ve Dashboard için birleşik liste.
    Gruplara dahil olan münferit kanallar gizlenir, sadece Gruplar ve Bağımsız Kanallar listelenir.
    Kanal ve grupların içerik planı ve kalan üretilmemiş konu sayıları da eklenir.
    """
    from content_planner import ContentPlanner
    mgr = ChannelManager()
    all_chans = mgr.all_channels()
    groups = mgr.all_groups()
    grouped_ids = mgr.get_grouped_channel_ids()
    output_dir = settings_mgr.get("output_dir", "output")

    items = []
    # 1. Grupları ekle
    for g in groups:
        member_channels = [mgr.get_channel(cid) for cid in g.get("channel_ids", []) if mgr.get_channel(cid)]
        langs = [ch["language"] for ch in member_channels]
        lang_str = "/".join(langs).upper() if langs else ""
        grp_dir = Path(output_dir) / "groups" / g["id"]
        grp_rows = []
        try:
            grp_planner = ContentPlanner(grp_dir)
            grp_rows = grp_planner.get_plan()
        except Exception:
            pass
        grp_unproduced = sum(1 for r in grp_rows if r.get("uretildi") != "Evet")
        has_plan = len(grp_rows) > 0

        items.append({
            "type": "group",
            "id": g["id"],
            "group_id": g["id"],
            "name": f"👥 [Grup] {g['name']} ({lang_str})",
            "raw_name": g["name"],
            "topic_category": g["topic_category"],
            "channel_ids": g.get("channel_ids", []),
            "languages": langs,
            "shorts_mode": any(ch.get("shorts_mode", False) for ch in member_channels) if member_channels else True,
            "has_plan": has_plan,
            "unproduced_count": grp_unproduced,
            "total_plan_count": len(grp_rows),
        })

    # 2. Yalnızca bağımsız (gruba dahil olmayan) kanalları ekle
    for ch in all_chans:
        if ch["channel_id"] not in grouped_ids:
            ch_dir = Path(output_dir) / ch["channel_id"]
            ch_rows = []
            try:
                ch_planner = ContentPlanner(ch_dir)
                ch_rows = ch_planner.get_plan()
            except Exception:
                pass
            ch_unproduced = sum(1 for r in ch_rows if r.get("uretildi") != "Evet")
            has_plan = len(ch_rows) > 0

            items.append({
                "type": "channel",
                "id": ch["channel_id"],
                "channel_id": ch["channel_id"],
                "name": f"{ch['name']} ({ch.get('language', 'en').upper()})",
                "raw_name": ch["name"],
                "topic_category": ch.get("topic_category", "space"),
                "channel_ids": [ch["channel_id"]],
                "languages": [ch.get("language", "en")],
                "shorts_mode": ch.get("shorts_mode", False),
                "has_plan": has_plan,
                "unproduced_count": ch_unproduced,
                "total_plan_count": len(ch_rows),
            })

    return items


# ═══════════════════════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/logs")
def get_logs():
    output_dir = settings_mgr.get("output_dir", "output")
    out_path = Path(output_dir)
    logs = []
    if out_path.exists():
        for file in out_path.glob("run_*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                for entry in data:
                    filename_ts = file.stem.replace("run_", "")
                    try:
                        time_part = datetime.strptime(filename_ts, "%Y%m%d_%H%M%S").strftime("%H:%M")
                    except:
                        time_part = "-"
                    logs.append({
                        "time": time_part,
                        "date": filename_ts[:8],
                        "channel_id": entry.get("channel_id"),
                        "title": entry.get("title") or entry.get("error") or "-",
                        "folder": entry.get("folder"),
                        "status": "✅" if entry.get("success") else "❌",
                    })
            except Exception as e:
                print(f"Error reading log: {file}: {e}")
    logs.sort(key=lambda x: (x["date"], x["time"]), reverse=True)
    return logs


# ═══════════════════════════════════════════════════════════════
# VIDEO GENERATION
# ═══════════════════════════════════════════════════════════════

def _heuristically_extract_shorts_script(original_data: dict, index: int, lang: str) -> dict:
    original_scenes = original_data.get("scenes", [])
    if not original_scenes:
        original_scenes = [{
            "narration": original_data.get("narration", "No narration available."),
            "image_prompt": "cinematic dramatic flight safety"
        }]

    n_scenes = len(original_scenes)
    num_chunks = 4
    chunk_size = max(1, n_scenes // num_chunks)
    
    start_idx = index * chunk_size
    if index == num_chunks - 1:
        end_idx = n_scenes
    else:
        end_idx = min(n_scenes, (index + 1) * chunk_size)
        
    chunk_scenes = original_scenes[start_idx:end_idx]
    if not chunk_scenes:
        chunk_scenes = original_scenes
        start_idx = 0

    selected_scenes = chunk_scenes[:4]
    
    scenes_list = []
    total_words = 0
    
    for idx, sc in enumerate(selected_scenes):
        narration = sc.get("narration", "")
        words = narration.split()
        if total_words + len(words) > 130 and len(scenes_list) >= 2:
            break
            
        total_words += len(words)
        scenes_list.append({
            "narration": narration,
            "image_prompt": sc.get("image_prompt", "cinematic"),
            "emotion": sc.get("emotion", "dramatic"),
            "original_scene_index": start_idx + idx
        })

    title = original_data.get("title", "Aviation")
    if " | " in title:
        title = title.split(" | ")[0]
    
    section_names = ["Intro", "Rising", "Climax", "Ending"]
    section_name = section_names[index] if index < len(section_names) else f"Part {index+1}"
    shorts_title = f"{title} - {section_name}"
    if len(shorts_title) > 80:
        shorts_title = shorts_title[:77] + "..."

    description = original_data.get("description", "")
    if len(description) > 200:
        description = description[:200] + "..."
    if "#Shorts" not in description:
        description += " #Shorts #Aviation"

    return {
        "title": shorts_title,
        "description": description,
        "keywords": original_data.get("keywords", ["aviation"]),
        "tags": original_data.get("tags", ["aviation"]),
        "style_prompt": original_data.get("style_prompt", "cinematic"),
        "scenes": scenes_list
    }


def _slice_narrative_video_to_shorts(
    video_folder: Path,
    channel_id: str,
    channel_config: dict,
    original_data: dict,
    count: int,
    exec_id: str,
    plan_id: str,
    planner,
    total_dur: float
) -> bool:
    import subprocess
    import shutil
    import os
    from PIL import Image, ImageDraw, ImageFont

    final_mp4 = video_folder / "final.mp4"
    if not final_mp4.exists():
        return False

    def get_best_ffmpeg() -> str:
        try:
            from video_editor import find_ffmpeg
            return find_ffmpeg(require_subtitles=True)
        except Exception:
            pass
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                return exe
        except Exception:
            pass
        return shutil.which("ffmpeg") or "ffmpeg"

    ffmpeg_bin = get_best_ffmpeg()

    base_title = (original_data.get("title", "") or "Video").split(" | ")[0].strip()
    tags = original_data.get("tags") or ["Shorts", "Viral"]
    if "Shorts" not in tags:
        tags.insert(0, "Shorts")

    lang = channel_config.get("language", "tr")
    ch_name = channel_config.get("name") or channel_id

    # 1. Altyazı veya konuşma transcript verisini yükle / otomatik çıkar
    transcript_file = video_folder / "transcription.json"
    segments = []
    if transcript_file.exists():
        try:
            segments = json.loads(transcript_file.read_text(encoding="utf-8"))
        except Exception:
            segments = []

    if not segments:
        try:
            from faster_whisper import WhisperModel
            audio_tmp = video_folder / "_temp_shorts_audio.wav"
            cmd_ext = [ffmpeg_bin, "-y", "-i", str(final_mp4), "-vn", "-ar", "16000", "-ac", "1", str(audio_tmp)]
            subprocess.run(cmd_ext, capture_output=True, timeout=60)
            if audio_tmp.exists() and audio_tmp.stat().st_size > 1000:
                w_model = WhisperModel("base", device="cpu", compute_type="int8")
                w_segs, _ = w_model.transcribe(str(audio_tmp), word_timestamps=True, language=lang if lang in ["tr", "en"] else None)
                parsed_segs = []
                for s in w_segs:
                    w_list = []
                    if s.words:
                        for w in s.words:
                            w_list.append({"word": w.word, "start": w.start, "end": w.end})
                    parsed_segs.append({
                        "start": s.start,
                        "end": s.end,
                        "text": s.text.strip(),
                        "words": w_list
                    })
                if parsed_segs:
                    segments = parsed_segs
                    transcript_file.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
                try:
                    audio_tmp.unlink()
                except Exception:
                    pass
        except Exception as whisper_err:
            print(f"[AUTO-SHORTS] Otomatik deşifre uyarısı: {whisper_err}")

    SW, SH = 1080, 1920
    panel_w, panel_h = 1080, 608
    panel_y = (SH - panel_h) // 2

    # Shorts hedef süresi (45 - 55 sn)
    target_seg_dur = min(54.0, max(35.0, (total_dur / max(1, count)) * 0.85))

    def make_title_overlay(tag: str, title: str, subtitle: str, out_path: Path):
        height = 240
        img = Image.new("RGBA", (SW, height), (0, 0, 0, 0))
        bg = Image.new("RGBA", (SW, height), (10, 14, 26, 220))
        for y in range(height):
            alpha = int(220 * (1.0 - (y / height) * 0.25))
            for x in range(0, SW, 4):
                bg.putpixel((x, y), (10, 14, 26, alpha))
        img = Image.alpha_composite(img, bg)
        draw = ImageDraw.Draw(img)

        # Gradient üst çizgi
        for x in range(SW):
            frac = x / SW
            r = int(239 + (244 - 239) * frac)
            g = int(68 + (114 - 68) * frac)
            b = int(68 + (182 - 68) * frac)
            draw.point((x, 0), fill=(r, g, b, 255))
            draw.point((x, 1), fill=(r, g, b, 210))
            draw.point((x, 2), fill=(r, g, b, 130))

        try:
            fnt_tag = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
            fnt_main = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            fnt_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except Exception:
            try:
                fnt_tag = ImageFont.truetype("Arial.ttf", 22)
                fnt_main = ImageFont.truetype("Arial.ttf", 36)
                fnt_sub = ImageFont.truetype("Arial.ttf", 24)
            except Exception:
                fnt_tag = fnt_main = fnt_sub = ImageFont.load_default()

        draw.text((SW // 2, 44), tag.upper(), font=fnt_tag, fill=(248, 113, 113, 240), anchor="mm")
        disp_main = (title[:42] + "…") if len(title) > 42 else title
        draw.text((SW // 2, 98), disp_main, font=fnt_main, fill=(255, 255, 255, 255), anchor="mm")
        if subtitle:
            disp_sub = (subtitle[:54] + "…") if len(subtitle) > 54 else subtitle
            draw.text((SW // 2, 148), disp_sub, font=fnt_sub, fill=(203, 213, 225, 210), anchor="mm")

        img.save(str(out_path), "PNG")

    def generate_shorts_ass(segs: list, start_offset: float, duration: float, out_ass_path: Path):
        ass_lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            # Mobil ekranlar için büyük sarı altyazı: &H0000FFFF (Sarı), 64px, Kalın, 5.0 siyah kontur, MarginV=520
            "Style: ShortsYellow,Arial,64,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5.0,2.5,2,80,80,520,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        def fmt_ts(s: float) -> str:
            s = max(0.0, s)
            hrs = int(s // 3600)
            mins = int((s % 3600) // 60)
            secs = int(s % 60)
            cs = int(round((s - int(s)) * 100))
            if cs >= 100:
                cs = 99
            return f"{hrs:d}:{mins:02d}:{secs:02d}.{cs:02d}"

        end_offset = start_offset + duration

        for seg in segs:
            words = seg.get("words", [])
            if words:
                chunk_words = []
                chunk_start = None
                chunk_end = None

                for w in words:
                    w_start = w.get("start", 0.0)
                    w_end = w.get("end", 0.0)

                    if w_end < start_offset or w_start > end_offset:
                        continue

                    if chunk_start is None:
                        chunk_start = max(0.0, w_start - start_offset)

                    raw_word = str(w.get("word", "")).strip()
                    if not raw_word:
                        continue

                    if raw_word.startswith((",", ".")) and chunk_words:
                        chunk_words[-1] += raw_word
                    else:
                        chunk_words.append(raw_word)

                    chunk_end = max(chunk_start + 0.3, w_end - start_offset)

                    text_so_far = " ".join(chunk_words)
                    if len(chunk_words) >= 4 or len(text_so_far) >= 24 or text_so_far.endswith((".", "!", "?")):
                        rel_start = fmt_ts(chunk_start)
                        rel_end = fmt_ts(chunk_end)
                        text_clean = text_so_far.upper()
                        ass_lines.append(f"Dialogue: 0,{rel_start},{rel_end},ShortsYellow,,0,0,0,,{text_clean}")
                        chunk_words = []
                        chunk_start = None
                        chunk_end = None

                if chunk_words and chunk_start is not None:
                    rel_start = fmt_ts(chunk_start)
                    rel_end = fmt_ts(chunk_end or (chunk_start + 0.8))
                    text_clean = " ".join(chunk_words).upper()
                    ass_lines.append(f"Dialogue: 0,{rel_start},{rel_end},ShortsYellow,,0,0,0,,{text_clean}")

            else:
                seg_s = seg.get("start", 0.0)
                seg_e = seg.get("end", 0.0)
                if seg_e < start_offset or seg_s > end_offset:
                    continue
                rel_start = fmt_ts(max(0.0, seg_s - start_offset))
                rel_end = fmt_ts(min(duration, seg_e - start_offset))
                text_clean = str(seg.get("text", "")).strip().upper()
                if text_clean:
                    ass_lines.append(f"Dialogue: 0,{rel_start},{rel_end},ShortsYellow,,0,0,0,,{text_clean}")

        out_ass_path.write_text("\n".join(ass_lines), encoding="utf-8")

    def is_valid_short_video(v_file: Path) -> bool:
        if not v_file.exists() or v_file.stat().st_size < 100000:
            return False
        try:
            dur_out = subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(v_file)],
                timeout=5
            ).decode().strip()
            return float(dur_out) >= 15.0
        except Exception:
            return False

    success_count = 0
    part_labels_tr = ["Giriş ve Başlangıç", "Gelişme ve Kriz", "Doruk Noktası", "Final ve Sonuç"]
    part_labels_en = ["Opening & Setup", "Rising Action", "Climax & Crisis", "Finale & Aftermath"]
    part_labels = part_labels_tr if lang == "tr" else part_labels_en

    for i in range(1, count + 1):
        target_shorts_dir = video_folder / f"shorts_{i}"
        target_shorts_dir.mkdir(parents=True, exist_ok=True)
        shorts_final = target_shorts_dir / "final.mp4"
        overlay_png = target_shorts_dir / "title_overlay.png"
        subs_ass = target_shorts_dir / "shorts_subs.ass"

        if is_valid_short_video(shorts_final) and (target_shorts_dir / "metadata.json").exists() and subs_ass.exists():
            print(f"[AUTO-SHORTS] shorts_{i} zaten geçerli ve mevcut ({shorts_final}). Atlanıyor.")
            success_count += 1
            continue

        if exec_id and exec_id in executions:
            executions[exec_id]["message"] = f"Dikey Shorts {i}/{count} sarı kalın altyazılarla derleniyor..."

        if segments:
            target_start = ((i - 1) / max(1, count)) * (total_dur - target_seg_dur)
            best_idx = min(range(len(segments)), key=lambda idx: abs(segments[idx]["start"] - target_start))
            seg_start = segments[best_idx]["start"]
            curr_end = seg_start
            chosen_texts = []
            for s in segments[best_idx:]:
                chosen_texts.append(s["text"].strip())
                curr_end = s["end"]
                dur = curr_end - seg_start
                if dur >= 44.0:
                    if s["text"].strip().endswith((".", "!", "?")) or dur >= 55.0:
                        break
            actual_dur = round(curr_end - seg_start, 2)
            actual_start = round(seg_start, 2)
            snippet = " ".join(chosen_texts)
        else:
            step = max(0.0, (total_dur - target_seg_dur) / max(1, count - 1)) if count > 1 else 0.0
            actual_start = round((i - 1) * step, 1)
            actual_dur = round(target_seg_dur, 1)
            snippet = f"Part {i} - {base_title}"

        part_tag = f"{ch_name.upper()} • BÖLÜM {i}/{count}" if lang == "tr" else f"{ch_name.upper()} • PART {i}/{count}"
        part_sub = part_labels[min(i - 1, len(part_labels) - 1)]
        part_title = f"{base_title} (Part {i})"

        make_title_overlay(part_tag, part_title, part_sub, overlay_png)
        generate_shorts_ass(segments, start_offset=actual_start, duration=actual_dur, out_ass_path=subs_ass)

        src_trim = f"trim=start={actual_start}:duration={actual_dur},setpts=PTS-STARTPTS"
        fade_out_start = max(0.1, actual_dur - 0.5)
        ass_esc = str(subs_ass).replace("\\", "/").replace("'", r"\'").replace(":", r"\:")

        filter_complex_subs = (
            f"[0:v]{src_trim},scale={SW}:{SH}:force_original_aspect_ratio=increase,crop={SW}:{SH},gblur=sigma=22,eq=brightness=-0.35:saturation=1.25[bg];"
            f"[0:v]{src_trim},scale={panel_w}:{panel_h}:force_original_aspect_ratio=decrease,pad={panel_w}:{panel_h}:(ow-iw)/2:(oh-ih)/2,drawbox=x=0:y=560:w=1080:h=48:color=black@0.95:t=fill[vid];"
            f"[0:a]atrim=start={actual_start}:duration={actual_dur},asetpts=PTS-STARTPTS,afade=t=in:ss=0:d=0.3,afade=t=out:st={fade_out_start}:d=0.5[aout];"
            f"[bg][vid]overlay=x=0:y={panel_y}:format=auto[v1];"
            f"[v1][1:v]overlay=x=0:y=60:format=auto[v2];"
            f"[v2]subtitles='{ass_esc}'[vsub];"
            f"[vsub]drawbox=x=0:y={SH-6}:w='iw*t/{actual_dur}':h=6:color=0xef4444@0.9:t=fill[vout]"
        )

        filter_complex_fallback = (
            f"[0:v]{src_trim},scale={SW}:{SH}:force_original_aspect_ratio=increase,crop={SW}:{SH},gblur=sigma=22,eq=brightness=-0.35:saturation=1.25[bg];"
            f"[0:v]{src_trim},scale={panel_w}:{panel_h}:force_original_aspect_ratio=decrease,pad={panel_w}:{panel_h}:(ow-iw)/2:(oh-ih)/2,drawbox=x=0:y=560:w=1080:h=48:color=black@0.95:t=fill[vid];"
            f"[0:a]atrim=start={actual_start}:duration={actual_dur},asetpts=PTS-STARTPTS,afade=t=in:ss=0:d=0.3,afade=t=out:st={fade_out_start}:d=0.5[aout];"
            f"[bg][vid]overlay=x=0:y={panel_y}:format=auto[v1];"
            f"[v1][1:v]overlay=x=0:y=60:format=auto[v2];"
            f"[v2]drawbox=x=0:y={SH-6}:w='iw*t/{actual_dur}':h=6:color=0xef4444@0.9:t=fill[vout]"
        )

        slice_cmd = [
            ffmpeg_bin, "-y",
            "-i", str(final_mp4),
            "-i", str(overlay_png),
            "-filter_complex", filter_complex_subs,
            "-map", "[vout]",
            "-map", "[aout]",
            "-t", str(actual_dur),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            str(shorts_final)
        ]

        try:
            res = subprocess.run(slice_cmd, capture_output=True, text=True, timeout=300)
            if res.returncode != 0:
                print(f"[AUTO-SHORTS] Altyazılı FFmpeg uyarısı, altyazısız yedeğe geçiliyor: {res.stderr[-400:]}")
                slice_cmd[6] = filter_complex_fallback
                res = subprocess.run(slice_cmd, capture_output=True, text=True, timeout=300)
                if res.returncode != 0:
                    print(f"[AUTO-SHORTS] FFmpeg hata verdi: {res.stderr[-400:]}")
                    continue
        except Exception as slice_err:
            print(f"[AUTO-SHORTS] FFmpeg çalıştırma hatası: {slice_err}")
            continue

        shutil.copy2(str(shorts_final), str(target_shorts_dir / "video.mp4"))

        short_title = f"{base_title} - Part {i}/{count} #Shorts"
        s_meta = {
            "title": short_title,
            "description": f"{snippet}\n\n#Shorts #{channel_id}",
            "tags": tags,
            "keywords": tags,
            "language": lang,
            "shorts_section_idx": i - 1,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": actual_dur
        }
        (target_shorts_dir / "metadata.json").write_text(json.dumps(s_meta, ensure_ascii=False, indent=2), encoding="utf-8")

        s_info = {
            "shorts_mode": True,
            "resolution": "1080x1920",
            "duration_sec": actual_dur,
            "title": short_title,
            "description": f"{snippet}\n\n#Shorts"
        }
        (target_shorts_dir / "video_info.json").write_text(json.dumps(s_info, ensure_ascii=False, indent=2), encoding="utf-8")

        try:
            planner.add_plan_row(
                konu=f"[SHORTS] {short_title}",
                odak_noktasi=f"Uzun Videodan Dikey Kırpma ({part_sub})",
                gorsel_stili="Dikey 9:16 - Blur Arka Plan & Master Ses",
                plan_tarihi=time.strftime("%Y-%m-%d"),
                plan_saati="12:00",
                is_shorts=True,
                parent_plan_id=plan_id
            )
        except Exception as e:
            print(f"[AUTO-SHORTS] Planner row ekleme uyarısı: {e}")

        success_count += 1
        if exec_id and exec_id in executions:
            executions[exec_id]["message"] = f"Dikey Shorts {i}/{count} tamamlandı!"

    if success_count > 0:
        if exec_id and exec_id in executions:
            executions[exec_id]["status"] = "success"
            executions[exec_id]["message"] = f"{success_count} adet dikey Shorts başarıyla üretildi!"
        print(f"[AUTO-SHORTS] ✅ Toplam {success_count}/{count} adet dikey Shorts üretildi.")
        return True
    return False


def _auto_generate_shorts_batch(
    channel_id: str,
    plan_id: str,
    video_result: dict,
    exec_id: str,
    writer,
    generator,
    output_dir: str,
    channel_config: dict,
    mgr,
    count: int = 4,
):
    """
    Başarıyla üretilmiş uzun bir videodan (4 dk+) otomatik olarak `count` adet
    Shorts senaryosu türetip her birini tam video pipeline'ından geçirir.

    Akış:
      1. Üretilen videonun metadata.json'unu oku.
      2. ScriptWriter ile farklı bölümlerden (başlangıç / orta / final) Shorts senaryo üret.
      3. Her senaryo için run_channel(custom_script=..., shorts_mode=True) ile video üret.
      4. İçerik planına '[SHORTS]' etiketi ile yeni satır ekle.
    """
    from main import run_channel
    from content_planner import ContentPlanner
    from script_writer import _parse_json

    # Üretilen video klasörünü ve metadata'sını bul
    video_path = video_result.get("video_path", "")
    if not video_path:
        return

    video_folder = Path(video_path).parent
    metadata_file = video_folder / "metadata.json"
    original_data = {}
    if metadata_file.exists():
        try:
            original_data = json.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[AUTO-SHORTS] metadata.json okunamadı: {e}")
            
    # metadata.json bulunamadıysa veya boşsa metadata.txt'den yedek okuma yap (eski videolar için)
    if not original_data or not original_data.get("narration"):
        meta_parsed = _parse_metadata(video_folder)
        original_data = {
            "title": meta_parsed.get("title", ""),
            "description": meta_parsed.get("description", ""),
            "tags": meta_parsed.get("tags", []),
            "narration": meta_parsed.get("narration", ""),
            "language": meta_parsed.get("language", "en")
        }

    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)

    lang = channel_config.get("language", "en")
    lang_name = "Turkish" if lang == "tr" else "English"

    # Müzik videosu kontrolü (Sinek Beyni Biyo-AI Connectome)
    cat = (channel_config.get("topic_category") or original_data.get("category") or "").lower().strip()
    is_music = cat in ("music", "muzik", "connectome", "sinek_beyni") or (video_folder / "spikes_data.json").exists()

    if is_music:
        print(f"[AUTO-SHORTS] Sinek Beyni Müzik videosu tespit edildi ({video_folder.name}). {count} adet dikey Shorts klibi türetiliyor...")
        final_mp4 = video_folder / "final.mp4"
        if not final_mp4.exists():
            print(f"[AUTO-SHORTS] Hata: final.mp4 bulunamadı: {final_mp4}")
            return

        import subprocess
        from PIL import Image, ImageDraw, ImageFont
        import textwrap

        # ── Süre ve çözünürlük ──────────────────────────────────────
        dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", str(final_mp4)]
        try:
            total_dur = float(subprocess.check_output(dur_cmd).decode().strip())
        except Exception:
            total_dur = float(original_data.get("track_info", {}).get("durationSec") or 180.0)

        res_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(final_mp4)]
        try:
            res_str = subprocess.check_output(res_cmd).decode().strip()
            w, h = [int(x) for x in res_str.split("x")]
        except Exception:
            w, h = (1920, 1080)

        is_already_vertical = (w < h)
        seg_dur = min(50.0, max(25.0, total_dur / max(1, count)))

        # ── Track bilgisi ────────────────────────────────────────────
        track_title = original_data.get("title", "").split(" | ")[0].strip() or "Synaptic Symphony"
        track_sub   = original_data.get("title", "").split(" | ")[-1].strip() if " | " in original_data.get("title", "") else ""

        # ── PIL ile title overlay PNG üret (700x220) ─────────────────
        def _make_title_overlay(title: str, subtitle: str, out_path: Path, width=1080):
            """Yarı-şeffaf modern başlık kartı üretir."""
            card_h = 240
            img = Image.new("RGBA", (width, card_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Koyu cam efekti arka plan (gradient değil, flat dark)
            bg = Image.new("RGBA", (width, card_h), (10, 8, 20, 210))
            # Üstten gradient şeffaflık
            for y in range(card_h):
                alpha = int(210 * (y / card_h))
                for x in range(0, width, 4):
                    if bg.getpixel((x, y))[3] > 0:
                        bg.putpixel((x, y), (10, 8, 20, min(alpha, 210)))
            img = Image.alpha_composite(img, bg)
            draw = ImageDraw.Draw(img)

            # Mor–mavi accent çizgisi (üst)
            for x in range(width):
                frac = x / width
                r = int(99 + (168 - 99) * frac)
                g = int(102 + (85 - 102) * frac)
                b = int(241 + (247 - 241) * frac)
                draw.point((x, 0), fill=(r, g, b, 255))
                draw.point((x, 1), fill=(r, g, b, 200))
                draw.point((x, 2), fill=(r, g, b, 120))

            # Font yükle
            try:
                fnt_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
                fnt_sub   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
            except Exception:
                fnt_title = ImageFont.load_default()
                fnt_sub   = fnt_title

            # Başlık text (truncate)
            display_title = (title[:38] + "…") if len(title) > 38 else title
            draw.text((width // 2, 70), display_title, font=fnt_title,
                      fill=(255, 255, 255, 255), anchor="mm")

            # Alt yazı / kategori
            if subtitle:
                display_sub = (subtitle[:52] + "…") if len(subtitle) > 52 else subtitle
                draw.text((width // 2, 125), display_sub, font=fnt_sub,
                          fill=(180, 160, 255, 200), anchor="mm")

            # Müzik notu ikonları
            draw.text((60, 85), "♪", font=fnt_title, fill=(168, 85, 247, 180), anchor="mm")
            draw.text((width - 60, 85), "♪", font=fnt_title, fill=(99, 102, 241, 180), anchor="mm")

            img.save(str(out_path), "PNG")

        # ── Her Shorts segmenti ──────────────────────────────────────
        for i in range(1, count + 1):
            target_shorts_dir = video_folder / f"shorts_{i}"
            target_shorts_dir.mkdir(parents=True, exist_ok=True)
            shorts_final = target_shorts_dir / "final.mp4"
            title_overlay_png = target_shorts_dir / "title_overlay.png"

            if count == 1:
                start_sec = max(0.0, (total_dur - seg_dur) / 2.0)
            else:
                step = max(0.0, (total_dur - seg_dur) / (count - 1))
                start_sec = round((i - 1) * step, 1)

            # Title overlay PNG her seferinde yenile
            _make_title_overlay(track_title, track_sub, title_overlay_png)

            # ── FFMPEG Modern Müzik Shorts Pipeline ──────────────────
            SW, SH = 1080, 1920
            panel_w = SW
            panel_h = ((SW * 9 // 16 + 1) // 2) * 2

            panel_y = (SH - panel_h) // 2 - 60
            wave_h  = 280
            wave_y  = SH - wave_h - 80
            title_y = 0

            # trim filtresi: her iki yönlü video için ortak
            src_trim = f"trim=start={start_sec}:duration={seg_dur},setpts=PTS-STARTPTS"

            filter_complex = (
                # BG: blurlu + karartılmış 1080x1920
                f"[0:v]{src_trim},"
                f"scale={SW}:{SH}:force_original_aspect_ratio=increase,"
                f"crop={SW}:{SH},"
                f"gblur=sigma=18,"
                f"eq=brightness=-0.35:saturation=1.4[bg];"
                # VID: temiz orta panel
                f"[0:v]{src_trim},"
                f"scale={panel_w}:{panel_h}:force_original_aspect_ratio=decrease,"
                f"pad={panel_w}:{panel_h}:(ow-iw)/2:(oh-ih)/2[vid];"
                # Split the trimmed audio so the waveform and output audio stay in sync.
                f"[0:a]atrim=start={start_sec}:duration={seg_dur},asetpts=PTS-STARTPTS,"
                f"asplit=2[aout][awave];"
                f"[awave]showwaves=s={SW}x{wave_h}:mode=cline:rate=30:"
                f"colors=0x6366f1@0.9|0xa855f7@0.9|0xc084fc@0.7:scale=cbrt,"
                f"format=yuva420p[wave];"
                # Composite
                f"[bg][vid]overlay=x=0:y={panel_y}:format=auto[v1];"
                f"[v1][wave]overlay=x=0:y={wave_y}:format=auto[v2];"
                f"[v2][1:v]overlay=x=0:y={title_y}:format=auto[v3];"
                f"[v3]drawbox=x=0:y={SH-6}:w='iw*t/{seg_dur}':h=6:color=0x9333ea@0.9:t=fill[vout]"
            )

            import tempfile
            with tempfile.NamedTemporaryFile(
                prefix=".shorts-", suffix=".mp4", dir=target_shorts_dir, delete=False
            ) as temp_video:
                temp_video_path = Path(temp_video.name)
            try:
                slice_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(final_mp4),
                    "-i", str(title_overlay_png),
                    "-filter_complex", filter_complex,
                    "-map", "[vout]",
                    "-map", "[aout]",
                    "-t", str(seg_dur),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    str(temp_video_path)
                ]
                result = subprocess.run(slice_cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg Shorts render failed: {result.stderr[-1200:]}")
                os.replace(temp_video_path, shorts_final)
            except subprocess.TimeoutExpired as e:
                raise RuntimeError("FFmpeg Shorts render timed out after 300 seconds.") from e
            finally:
                temp_video_path.unlink(missing_ok=True)


            short_title = f"{track_title} - Part {i}/{count} #Shorts"
            short_desc, short_tags = get_localized_metadata(short_title, language=lang, category="music")

            s_meta = {
                "title": short_title,
                "description": short_desc,
                "tags": short_tags,
                "keywords": short_tags,
                "language": lang,
                "category": "music",
                "topic": "music",
                "plan_id": f"{plan_id}_shorts_{i}" if plan_id else f"shorts_{i}",
                "shorts_section_idx": i,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            (target_shorts_dir / "metadata.json").write_text(json.dumps(s_meta, ensure_ascii=False, indent=2), encoding="utf-8")

            s_info = {
                "shorts_mode": True,
                "resolution": "1080x1920",
                "duration_sec": seg_dur,
                "title": short_title,
                "description": short_desc,
                "tags": short_tags,
                "keywords": short_tags,
                "topic_category": "music"
            }
            (target_shorts_dir / "video_info.json").write_text(json.dumps(s_info, ensure_ascii=False, indent=2), encoding="utf-8")

            try:
                planner.add_plan_row(
                    konu=f"[SHORTS] {short_title}",
                    odak_noktasi="Sinek Beyni Biyo-AI Müzik Shorts",
                    gorsel_stili="Modern Music Player - Neon Waveform",
                    plan_tarihi=datetime.now().strftime("%Y-%m-%d"),
                    plan_saati="12:00",
                    is_shorts=True,
                    parent_plan_id=plan_id
                )
            except Exception as e:
                print(f"[AUTO-SHORTS] Planner row add warning: {e}")

            if exec_id and exec_id in executions:
                executions[exec_id]["message"] = f"Müzik Shorts {i}/{count} oluşturuldu!"

        print(f"[AUTO-SHORTS] Sinek Beyni videosundan {count} adet modern müzik Shorts başarıyla üretildi.")
        return


    # ── 2. NARRATİF / GENEL UZUN VİDEODAN SHORTS KIRPMA (MASTER SLICE PIPELINE) ──
    # Eğer klasörde üretilmiş final.mp4 mevcutsa, AI yeniden üretim yapmak yerine doğrudan
    # orijinal videoyu en dramatik 45-55 sn'lik dikey 9:16 Shorts kliplerine böler.
    final_mp4 = video_folder / "final.mp4"
    if final_mp4.exists():
        import subprocess
        dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", str(final_mp4)]
        try:
            total_dur = float(subprocess.check_output(dur_cmd).decode().strip())
        except Exception:
            total_dur = 0.0

        if total_dur >= 30.0:
            print(f"[AUTO-SHORTS] {total_dur:.1f}s uzunluğunda final.mp4 tespit edildi. Doğrudan dikey master kırpma motoru çalıştırılıyor...")
            ok = _slice_narrative_video_to_shorts(
                video_folder=video_folder,
                channel_id=channel_id,
                channel_config=channel_config,
                original_data=original_data,
                count=count,
                exec_id=exec_id,
                plan_id=plan_id,
                planner=planner,
                total_dur=total_dur
            )
            if ok:
                return


    # Bölüm etiketleri — her Shorts farklı kısımdan türetilir
    section_labels = [
        "başlangıç (ilk sahneler)",
        "giriş ve gelişme (ilgi çekici kısımlar)",
        "doruk noktası (en dramatik/heyecanlı sahne)",
        "final ve sonuç (son sahneler)"
    ]
    section_labels_en = [
        "opening (first scenes)",
        "rising action (engaging build-up)",
        "climax (most dramatic/exciting scene)",
        "finale and aftermath (last scenes)"
    ]

    shorts_sys_prompt_template = """You are an expert YouTube editor and script writer for Shorts.
Your task is to extract a high-tension, dramatic 50-60 second YouTube Shorts script from the provided long-form video script.
Focus SPECIFICALLY on the {section} of the original script.
- Select 3 to 5 key consecutive scenes from that section.
- The total narration word count must be around 110-130 words in {lang_name} to fit 50-60 seconds.
- Keep the visual style and image prompts consistent with the original.
- Title, description, tags, and narration MUST be in {lang_name}. Image prompts MUST be in English.

Output ONLY a valid JSON object:
{{
  "title": "Clickbaity Shorts title in {lang_name} (max 80 chars)",
  "description": "Shorts description in {lang_name} with hashtags",
  "keywords": ["keyword1", "keyword2"],
  "tags": ["tag1", "tag2"],
  "style_prompt": "Consistent cinematic style prompt (English)",
  "scenes": [
    {{
      "narration": "~25 word narration in {lang_name}",
      "image_prompt": "Cinematic SD image prompt in English",
      "emotion": "neutral | excited | dramatic | mysterious | sad",
      "original_scene_index": 0-based integer index of the scene from the original long-form script that this narration corresponds to
    }}
  ]
}}
Return ONLY valid JSON, no markdown fences."""

    edit_options = mgr.get_resolved_edit_options(channel_id)
    success_count = 0
    last_error = None

    # Orijinal uzun videonun klasöründeki mevcut görselleri tespit et
    original_scene_indices = []
    existing_imgs = list(video_folder.glob("scene_*.jpg"))
    for img in existing_imgs:
        name = img.stem
        parts = name.split("_")
        if len(parts) == 2 and parts[1].isdigit():
            original_scene_indices.append(int(parts[1]))
    original_scene_indices.sort()

    # İhtiyaç duyulan kısımları belirle (Herhangi bir count adedi için dinamik)
    required_sections = {}
    for i in range(1, count + 1):
        rel_pos = (i - 1) / max(1, count - 1)
        if rel_pos <= 0.25:
            lbl = section_labels[0]
            lbl_en = section_labels_en[0]
            idx = 0
        elif rel_pos <= 0.55:
            lbl = section_labels[1]
            lbl_en = section_labels_en[1]
            idx = 1
        elif rel_pos <= 0.8:
            lbl = section_labels[2]
            lbl_en = section_labels_en[2]
            idx = 2
        else:
            lbl = section_labels[3]
            lbl_en = section_labels_en[3]
            idx = 3
        required_sections[i] = {"idx": idx, "name": f"{lbl} (Bölüm {i}/{count})", "name_en": f"{lbl_en} (Part {i}/{count})"}

    # Klasördeki mevcut Shorts klasörlerini tara
    existing_shorts_folders = []
    if video_folder.exists() and video_folder.is_dir():
        for subfolder in video_folder.iterdir():
            if subfolder.is_dir() and subfolder.name.startswith("shorts_"):
                existing_shorts_folders.append(subfolder)
                
    has_any_existing_shorts = len(existing_shorts_folders) > 0

    if has_any_existing_shorts:
        print("[AUTO-SHORTS] Klasörde önceden üretilmiş Shorts tespit edildi. Akıllı denetim başlatılıyor...")
        
        # Özel Durum: count == 3 iken shorts_4 klasörü varsa ve shorts_3 sonuç videosu değilse:
        shorts_4_dir = video_folder / "shorts_4"
        shorts_3_dir = video_folder / "shorts_3"
        
        if count == 3 and shorts_4_dir.exists() and (shorts_4_dir / "final.mp4").exists():
            shorts_3_is_conclusion = False
            shorts_3_meta = shorts_3_dir / "metadata.json"
            if shorts_3_meta.exists():
                try:
                    m_data = json.loads(shorts_3_meta.read_text(encoding="utf-8"))
                    if m_data.get("shorts_section_idx") == 3:
                        shorts_3_is_conclusion = True
                    else:
                        text = (str(m_data.get("title", "")) + " " +
                                str(m_data.get("description", "")) + " " +
                                str(m_data.get("narration", ""))).lower()
                        conclusion_keywords = ["sonuç", "final", "conclusion", "finale", "ending", "aftermath", "özetle", "son olarak"]
                        if any(kw in text for kw in conclusion_keywords):
                            shorts_3_is_conclusion = True
                except Exception:
                    pass
            
            if not shorts_3_is_conclusion:
                print("[AUTO-SHORTS] shorts_3 sonuç videosu değil ve shorts_4 mevcut. shorts_4 (sonuç videosu) shorts_3 olarak taşınıyor...")
                import shutil
                if shorts_3_dir.exists():
                    shutil.rmtree(shorts_3_dir)
                shutil.move(str(shorts_4_dir), str(shorts_3_dir))
                
                # metadata.json güncelle
                if shorts_3_meta.exists():
                    try:
                        m_data = json.loads(shorts_3_meta.read_text(encoding="utf-8"))
                        m_data["shorts_section_idx"] = 3
                        shorts_3_meta.write_text(json.dumps(m_data, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass
            else:
                # shorts_3 zaten sonuç videosu ise shorts_4'ü silebiliriz
                print("[AUTO-SHORTS] shorts_3 zaten sonuç videosu. Fazlalık shorts_4 siliniyor...")
                import shutil
                shutil.rmtree(str(shorts_4_dir))

    # Shorts üretme/atlama döngüsü
    for folder_num, sec_info in required_sections.items():
        target_shorts_dir = video_folder / f"shorts_{folder_num}"
        video_file = target_shorts_dir / "final.mp4"
        meta_json = target_shorts_dir / "metadata.json"
        
        need_generate = True
        
        if has_any_existing_shorts and video_file.exists() and meta_json.exists():
            try:
                m_data = json.loads(meta_json.read_text(encoding="utf-8"))
                
                # Eğer shorts_section_idx eşleşiyorsa
                if m_data.get("shorts_section_idx") == sec_info["idx"]:
                    need_generate = False
                    print(f"[AUTO-SHORTS] shorts_{folder_num} zaten mevcut ve doğru kısım ({sec_info['name_en']}) için üretilmiş. Atlanıyor.")
                else:
                    # Eski üretimler için heuristic/dosya kontrolü
                    if folder_num == count:
                        text = (str(m_data.get("title", "")) + " " +
                                str(m_data.get("description", "")) + " " +
                                str(m_data.get("narration", ""))).lower()
                        conclusion_keywords = ["sonuç", "final", "conclusion", "finale", "ending", "aftermath", "özetle", "son olarak"]
                        if any(kw in text for kw in conclusion_keywords):
                            need_generate = False
                            m_data["shorts_section_idx"] = sec_info["idx"]
                            meta_json.write_text(json.dumps(m_data, ensure_ascii=False, indent=2), encoding="utf-8")
                            print(f"[AUTO-SHORTS] shorts_{folder_num} sonuç videosu olarak doğrulandı. Atlanıyor.")
                    elif folder_num == 1:
                        need_generate = False
                        m_data["shorts_section_idx"] = sec_info["idx"]
                        meta_json.write_text(json.dumps(m_data, ensure_ascii=False, indent=2), encoding="utf-8")
                        print(f"[AUTO-SHORTS] shorts_1 başlangıç videosu olarak işaretlendi. Atlanıyor.")
                    else:
                        need_generate = False
                        m_data["shorts_section_idx"] = sec_info["idx"]
                        meta_json.write_text(json.dumps(m_data, ensure_ascii=False, indent=2), encoding="utf-8")
                        print(f"[AUTO-SHORTS] shorts_{folder_num} mevcut kabul ediliyor. Atlanıyor.")
            except Exception:
                pass

        if not need_generate:
            success_count += 1
            continue

        try:
            section = sec_info["name"]
            section_en = sec_info["name_en"]
            sec_idx = sec_info["idx"]

            if exec_id in executions:
                executions[exec_id]["message"] = f"Otomatik Shorts {folder_num}/{count} üretiliyor... ({section})"

            sys_prompt = shorts_sys_prompt_template.format(
                section=section_en,
                lang_name=lang_name
            )
            user_prompt = (
                f"Original long-form video script:\n"
                f"{json.dumps(original_data, ensure_ascii=False, indent=2)}\n\n"
                f"Generate a Shorts version focused on the {section_en} in {lang_name}."
            )

            try:
                raw_response = writer.run_prompt(sys_prompt, user_prompt)
                shorts_script = _parse_json(raw_response)
            except Exception as llm_err:
                print(f"[AUTO-SHORTS] AI ile senaryo üretilemedi ({llm_err}). Algoritmik çıkarma sistemi (heuristic fallback) devreye giriyor...")
                shorts_script = _heuristically_extract_shorts_script(original_data, sec_idx, lang)
            print(f"[AUTO-SHORTS] Shorts {folder_num} senaryosu hazırlandı: {shorts_script.get('title', '')}")

            # Sahneleri orijinal uzun videonun görselleriyle eşleştir
            shorts_custom_images = {}
            for j, sc in enumerate(shorts_script.get("scenes", [])):
                orig_idx = sc.get("original_scene_index")
                if orig_idx is None or not isinstance(orig_idx, int) or orig_idx not in original_scene_indices:
                    if original_scene_indices:
                        idx_in_list = int((j / max(1, len(shorts_script.get("scenes", [1])) - 1)) * len(original_scene_indices))
                        orig_idx = original_scene_indices[min(idx_in_list, len(original_scene_indices) - 1)]
                    else:
                        orig_idx = 0
                
                orig_img_path = video_folder / f"scene_{orig_idx}.jpg"
                if orig_img_path.exists():
                    shorts_custom_images[str(j)] = str(orig_img_path)
                    print(f"[AUTO-SHORTS] Sahne {j} için orijinal scene_{orig_idx}.jpg seçildi.")

            shorts_result = run_channel(
                channel_config=channel_config,
                writer=writer,
                generator=generator,
                manager=mgr,
                output_dir=output_dir,
                shorts_mode=True,
                transition="fade",
                edit_options=edit_options,
                force_row_id="no_plan",
                custom_script=shorts_script,
                custom_images=shorts_custom_images,
            )
            if shorts_result.get("success"):
                import shutil
                shorts_video_path = shorts_result.get("video_path")
                shorts_folder_path = Path(shorts_video_path).parent
                
                if target_shorts_dir.exists():
                    shutil.rmtree(str(target_shorts_dir))
                    
                shutil.move(str(shorts_folder_path), str(target_shorts_dir))
                
                # metadata.json güncelle ve shorts_section_idx ekle
                new_meta_json = target_shorts_dir / "metadata.json"
                if new_meta_json.exists():
                    try:
                        m_data = json.loads(new_meta_json.read_text(encoding="utf-8"))
                        m_data["shorts_section_idx"] = sec_idx
                        new_meta_json.write_text(json.dumps(m_data, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                
                # Sonuç yollarını güncelle
                new_video_path = target_shorts_dir / "final.mp4"
                shorts_result["video_path"] = str(new_video_path)
                shorts_result["folder"] = f"{channel_id}/yuklenecek/{video_folder.name}/shorts_{folder_num}"
                print(f"[AUTO-SHORTS] ✅ Shorts {folder_num}/{count} hazır ve taşındı: {new_video_path}")
                success_count += 1
            else:
                err_text = shorts_result.get('error') or "Bilinmeyen Üretim Hatası"
                print(f"[AUTO-SHORTS] ❌ Shorts {folder_num}/{count} başarısız: {err_text}")
                last_error = RuntimeError(f"Shorts {folder_num} videosu üretilemedi: {err_text}")

        except Exception as e:
            print(f"[AUTO-SHORTS] Shorts {folder_num} üretimi sırasında hata: {e}")
            last_error = e
            import traceback
            traceback.print_exc()

        # Her Shorts üretimi sonunda GPU ve bellek kalıntılarını merkezi nöbetçide temizle
        _clear_memory(trigger=f"shorts_render_{folder_num}")

    # Toplu shorts üretimi bittiğinde nihai temizlik yap
    _clear_memory(trigger="shorts_batch_complete")

    if success_count == 0:
        if last_error:
            raise last_error
        else:
            raise RuntimeError("Hiçbir Shorts videosu üretilemedi.")



def render_past_shorts_background_task(channel_id: str, row_id: str, video_result: dict, exec_id: str):
    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = "Shorts senaryoları hazırlanıyor..."
    try:
        mgr = ChannelManager()
        ch = mgr.get_channel(channel_id)
        if not ch:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = "Kanal bulunamadı."
            _clear_memory(trigger="past_shorts_not_found")
            return

        provider = settings_mgr.get("ai_provider", "claude")
        ai_model = settings_mgr.get("ai_model", "")
        nasa_key = settings_mgr.get("nasa_api_key", "DEMO_KEY")
        output_dir = settings_mgr.get("output_dir", "output")
        ollama_url = settings_mgr.get("ollama_url", "http://localhost:11434")
        lmstudio_url = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")

        api_key = ""
        if provider == "claude":
            api_key = settings_mgr.get("anthropic_api_key")
        elif provider == "gemini":
            api_key = settings_mgr.get("gemini_api_key")

        from script_writer import ScriptWriter
        writer = ScriptWriter(
            provider=provider,
            api_key=api_key,
            model=ai_model,
            ollama_url=ollama_url,
            lmstudio_url=lmstudio_url,
        )
        from video_generator import VideoGenerator
        generator = VideoGenerator(nasa_api_key=nasa_key)

        _auto_generate_shorts_batch(
            channel_id=channel_id,
            plan_id=row_id,
            video_result=video_result,
            exec_id=exec_id,
            writer=writer,
            generator=generator,
            output_dir=output_dir,
            channel_config=ch,
            mgr=mgr,
            count=4,
        )

        executions[exec_id]["status"] = "success"
        executions[exec_id]["message"] = "4 Shorts başarıyla oluşturuldu ve video klasörüne eklendi!"
        _clear_memory(trigger="past_shorts_task_complete")
    except Exception as e:
        _clear_memory(trigger="past_shorts_task_error")
        executions[exec_id]["status"] = "failed"
        err_msg = str(e)
        if "Connection refused" in err_msg or "Connection error" in err_msg or "ConnectError" in err_msg:
            executions[exec_id]["message"] = "Yapay Zeka Bağlantı Hatası: Yerel modeliniz (LM Studio / Ollama) kapalı! Lütfen yerel yapay zeka uygulamanızı başlatın ve modeli yükleyin."
        elif "API key not valid" in err_msg or "400 INVALID_ARGUMENT" in err_msg:
            executions[exec_id]["message"] = "Geçersiz API Anahtarı: Ayarlar menüsünden geçerli bir Gemini API Anahtarı girdiğinizden emin olun."
        elif "Boş AI yanıtı" in err_msg:
            executions[exec_id]["message"] = "Yapay Zekadan boş yanıt döndü: Yerel modelinizde bir yükleme veya bellek sınırı hatası oluşmuş olabilir. Lütfen LM Studio / Ollama konsolunu kontrol edin."
        else:
            executions[exec_id]["message"] = f"Shorts üretimi sırasında hata oluştu: {err_msg}"


def run_automation_task(channel_id: str, exec_id: str, loop_count: int = 1, loop_delay: int = 10, force_row_id: str = None):

    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = "Başlatılıyor..."

    try:
        mgr = ChannelManager()
        ch = mgr.get_channel(channel_id)
        if not ch:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = "Kanal bulunamadı."
            return

        provider      = settings_mgr.get("ai_provider", "claude")
        ai_model      = settings_mgr.get("ai_model", "")
        nasa_key      = settings_mgr.get("nasa_api_key", "DEMO_KEY")
        output_dir    = settings_mgr.get("output_dir", "output")
        ollama_url    = settings_mgr.get("ollama_url", "http://localhost:11434")
        lmstudio_url  = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")

        # API key kontrolü
        if provider == "claude":
            api_key = settings_mgr.get("anthropic_api_key")
            if not api_key:
                executions[exec_id]["status"] = "failed"
                executions[exec_id]["message"] = "Anthropic API key eksik. Ayarlar'dan girin."
                return
        elif provider == "gemini":
            api_key = settings_mgr.get("gemini_api_key")
            if not api_key:
                executions[exec_id]["status"] = "failed"
                executions[exec_id]["message"] = "Gemini API key eksik. Ayarlar'dan girin."
                return
        else:
            api_key = ""

        # Provider-specific model override
        if provider == "ollama":
            ai_model = ai_model or settings_mgr.get("ollama_model", "llama3")
        elif provider == "lmstudio":
            ai_model = ai_model or settings_mgr.get("lmstudio_model", "")

        writer = ScriptWriter(
            provider=provider,
            api_key=api_key,
            model=ai_model,
            ollama_url=ollama_url,
            lmstudio_url=lmstudio_url,
        )
        generator = VideoGenerator(nasa_api_key=nasa_key)

        # Kanal-bazlı edit_options merge
        edit_options = mgr.get_resolved_edit_options(channel_id)
        edit_options["exec_id"] = exec_id

        import time
        results = []
        for i in range(1, loop_count + 1):
            if loop_count > 1:
                executions[exec_id]["message"] = f"Video {i}/{loop_count} üretiliyor..."
            else:
                executions[exec_id]["message"] = f"{provider.upper()} ile senaryo yazılıyor..."

            result = run_channel(
                channel_config=ch,
                writer=writer,
                generator=generator,
                manager=mgr,
                output_dir=output_dir,
                shorts_mode=ch.get("shorts_mode", False),
                transition=ch.get("transition", "fade"),
                edit_options=edit_options,
                force_row_id=force_row_id,
            )

            results.append(result)

            # Log kaydet
            log_path = Path(output_dir) / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            log_path.parent.mkdir(exist_ok=True)
            log_path.write_text(json.dumps([result], ensure_ascii=False, indent=2))

            if not result["success"]:
                executions[exec_id]["status"] = "failed"
                executions[exec_id]["message"] = f"Döngü durduruldu. Video {i}/{loop_count} Hata: {result.get('error')}"
                _clear_memory(trigger=f"automation_video_{i}_failed")
                return

            # ── OTOMATİK SHORTS ÜRETİMİ ─────────────────────────────────────────
            # Üretilen video 4 dakikadan uzunsa (duration_sec > 240), sistem
            # otomatik olarak 3 Shorts senaryosu türetip her birini üretir.
            # Shorts üretimi başarısız olsa bile ana video akışı devam eder.
            try:
                video_path = result.get("video_path", "")
                if video_path:
                    video_folder_path = Path(video_path).parent
                    video_info_file = video_folder_path / "video_info.json"
                    if video_info_file.exists():
                        video_info = json.loads(video_info_file.read_text(encoding="utf-8"))
                        duration_sec = float(video_info.get("duration_sec", 0.0))
                        # Kanal shorts_mode'da değilse VE video 4dk+'ise
                        if duration_sec > 240.0 and not ch.get("shorts_mode", False):
                            executions[exec_id]["message"] = (
                                f"Video {i}/{loop_count} tamamlandı ({duration_sec:.0f}s). "
                                f"Otomatik 4 Shorts üretimi başlatılıyor..."
                            )
                            print(f"[AUTO-SHORTS] {duration_sec:.1f}s video tespit edildi. 4 Shorts üretiliyor...")
                            _auto_generate_shorts_batch(
                                channel_id=channel_id,
                                plan_id=result.get("plan_id", ""),
                                video_result=result,
                                exec_id=exec_id,
                                writer=writer,
                                generator=generator,
                                output_dir=output_dir,
                                channel_config=ch,
                                mgr=mgr,
                                count=4,
                            )
                            print("[AUTO-SHORTS] Otomatik Shorts üretimi tamamlandı.")
            except Exception as shorts_err:
                print(f"[AUTO-SHORTS] Uyarı: Otomatik Shorts üretimi başarısız: {shorts_err}")
            # ────────────────────────────────────────────────────────────────────
            
            # Her ana video üretimi ve Shorts döngüsü sonunda bellek temizle
            _clear_memory(trigger=f"automation_video_{i}_complete")

            if i < loop_count:
                for remaining in range(loop_delay, 0, -1):
                    executions[exec_id]["message"] = f"Video {i}/{loop_count} tamamlandı. Sonraki video için {remaining} saniye bekleniyor..."
                    time.sleep(1)

        # Success of the entire loop
        executions[exec_id]["status"] = "success"
        executions[exec_id]["message"] = f"Başarıyla tamamlandı. Toplam {loop_count} video üretildi."
        executions[exec_id]["result"] = results[-1]
        _clear_memory(trigger="automation_all_loops_complete")
    except Exception as e:
        _clear_memory(trigger="automation_task_error")
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Sistem Hatası: {str(e)}"


@app.post("/api/run/{channel_id}")
def run_channel_endpoint(
    channel_id: str,
    background_tasks: BackgroundTasks,
    loop_count: int = 1,
    loop_delay: int = 10
):
    mgr = ChannelManager()
    if not mgr.get_channel(channel_id):
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")

    exec_id = f"exec_{channel_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    executions[exec_id] = {
        "channel_id": channel_id,
        "status": "pending",
        "message": "Kuyruğa alındı...",
        "timestamp": datetime.now().isoformat(),
    }
    background_tasks.add_task(run_automation_task, channel_id, exec_id, loop_count, loop_delay)
    return {"exec_id": exec_id, "status": "pending"}


@app.post("/api/channels/{channel_id}/plan/{row_id}/reproduce")
def reproduce_planned_video(
    channel_id: str,
    row_id: str,
    background_tasks: BackgroundTasks
):
    import shutil
    import time
    from content_planner import ContentPlanner

    mgr = ChannelManager()
    if not mgr.get_channel(channel_id):
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    # 1. Satırı bul
    row = planner.get_row_by_id(row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plan satırı bulunamadı.")
        
    # 2. Varolan video klasörünü tara ve taşı (arsiv klasörüne)
    all_videos = list_output_videos()
    channel_videos = [v for v in all_videos if v.get("channel_id") == channel_id]
    
    # Eşleşen video klasörü var mı?
    matching_video = None
    for v in channel_videos:
        if str(v.get("plan_id")) == str(row_id):
            matching_video = v
            break
            
    if matching_video:
        old_folder = Path(output_dir) / matching_video.get("folder")
        if old_folder.exists() and old_folder.is_dir():
            # Arşiv klasörünü belirle: output/{channel_id}/arsiv
            archive_dir = Path(output_dir) / channel_id / "arsiv"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Hedef klasör yolu: output/{channel_id}/arsiv/{folder_name}
            dest_folder = archive_dir / old_folder.name
            
            # Eğer arşivde aynı isimde klasör varsa çakışmayı önlemek için sonuna timestamp ekle
            if dest_folder.exists():
                dest_folder = archive_dir / f"{old_folder.name}_{int(time.time())}"
                
            try:
                print(f"[REPRODUCE] Arşivleniyor: {old_folder} -> {dest_folder}")
                shutil.move(str(old_folder), str(dest_folder))
            except Exception as e:
                print(f"[REPRODUCE] Taşıma hatası: {e}")
                
    # 3. Arka planda yeni üretim görevini başlat
    exec_id = f"exec_{channel_id}_reproduce_{row_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    executions[exec_id] = {
        "channel_id": channel_id,
        "status": "pending",
        "message": f"Konu #{row_id} tekrar üretiliyor...",
        "timestamp": datetime.now().isoformat(),
    }
    background_tasks.add_task(run_automation_task, channel_id, exec_id, 1, 10, row_id)
    return {"exec_id": exec_id, "status": "pending"}


def run_recompose_task(channel_id: str, exec_id: str, row_id: str, recompose_folder: str):
    """Mevcut resim ve sesleri birleştirerek videolaştırmayı tamamlayan arka plan görevi."""
    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = "Mevcut görseller ve ses birleştiriliyor (Recompose)..."

    try:
        from main import run_channel
        from script_writer import ScriptWriter
        from video_generator import VideoGenerator
        from channel_manager import ChannelManager

        mgr = ChannelManager()
        ch = mgr.get_channel(channel_id)
        if not ch:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = "Kanal bulunamadı."
            return

        provider      = settings_mgr.get("ai_provider", "claude")
        ai_model      = settings_mgr.get("ai_model", "")
        nasa_key      = settings_mgr.get("nasa_api_key", "DEMO_KEY")
        output_dir    = settings_mgr.get("output_dir", "output")
        ollama_url    = settings_mgr.get("ollama_url", "http://localhost:11434")
        lmstudio_url  = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")

        api_key = settings_mgr.get("anthropic_api_key") or settings_mgr.get("gemini_api_key") or ""
        writer = ScriptWriter(
            provider=provider,
            api_key=api_key,
            model=ai_model,
            ollama_url=ollama_url,
            lmstudio_url=lmstudio_url,
        )
        generator = VideoGenerator(nasa_api_key=nasa_key)
        edit_options = mgr.get_resolved_edit_options(channel_id)

        result = run_channel(
            channel_config=ch,
            writer=writer,
            generator=generator,
            manager=mgr,
            output_dir=output_dir,
            shorts_mode=ch.get("shorts_mode", False),
            transition=ch.get("transition", "fade"),
            edit_options=edit_options,
            force_row_id=row_id,
            recompose_folder=recompose_folder,
        )

        if not result["success"]:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = f"Hata: {result.get('error')}"
            _clear_memory(trigger="recompose_failed")
            return

        # Başarılı
        executions[exec_id]["status"] = "success"
        executions[exec_id]["message"] = "Videolaştırma başarıyla tamamlandı!"
        executions[exec_id]["result"] = result
        _clear_memory(trigger="recompose_success")
    except Exception as e:
        _clear_memory(trigger="recompose_error")
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Recompose Sistem Hatası: {str(e)}"


@app.post("/api/channels/{channel_id}/plan/{row_id}/recompose")
def recompose_planned_video(
    channel_id: str,
    row_id: str,
    background_tasks: BackgroundTasks
):
    """Mevcut klasörden doğrudan video birleştirme işlemini tetikler."""
    from content_planner import ContentPlanner

    mgr = ChannelManager()
    if not mgr.get_channel(channel_id):
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    row = planner.get_row_by_id(row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plan satırı bulunamadı.")

    # 1. Klasörü tara ve bul
    recompose_folder = None
    yuklenecek_dir = channel_dir / "yuklenecek"
    yuklenen_dir = channel_dir / "yuklenen"
    search_dirs = [channel_dir]
    if yuklenecek_dir.exists() and yuklenecek_dir.is_dir():
        search_dirs.append(yuklenecek_dir)
    if yuklenen_dir.exists() and yuklenen_dir.is_dir():
        search_dirs.append(yuklenen_dir)

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for folder in s_dir.iterdir():
            if not folder.is_dir() or folder.name.startswith("."):
                continue

            p_id = None
            meta_json = folder / "metadata.json"
            if meta_json.exists():
                try:
                    meta_data = json.loads(meta_json.read_text(encoding="utf-8"))
                    p_id = str(meta_data.get("plan_id", ""))
                except Exception:
                    pass

            if not p_id:
                try:
                    parts = folder.name.split("_")
                    if parts[0].isdigit() and len(parts[0]) == 4:
                        p_id = str(int(parts[0]))
                except Exception:
                    pass

            if p_id and str(p_id) == str(row_id):
                # Klasörün gerekli dosyalara sahip olduğundan emin ol
                images = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png") and f.name.startswith("scene_")]
                audios = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in (".wav", ".mp3") and f.name.startswith("narration")]
                if images and audios:
                    recompose_folder = str(folder)
                    break
        if recompose_folder:
            break

    if not recompose_folder:
        raise HTTPException(
            status_code=400, 
            detail="Gerekli resim ve ses dosyalarına sahip yarım kalmış bir proje klasörü bulunamadı."
        )

    # 2. Görevi başlat
    exec_id = f"exec_{channel_id}_recompose_{row_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    executions[exec_id] = {
        "channel_id": channel_id,
        "status": "pending",
        "message": f"Konu #{row_id} mevcut dosyalardan birleştiriliyor...",
        "timestamp": datetime.now().isoformat(),
    }
    background_tasks.add_task(run_recompose_task, channel_id, exec_id, row_id, recompose_folder)
    return {"exec_id": exec_id, "status": "pending"}


@app.get("/api/run/status/{exec_id}")
def get_run_status(exec_id: str):
    if exec_id not in executions:
        raise HTTPException(status_code=404, detail="Çalıştırma kaydı bulunamadı.")
    return executions[exec_id]


# ═══════════════════════════════════════════════════════════════
# OUTPUT BROWSER
# ═══════════════════════════════════════════════════════════════

def _parse_metadata(folder: Path, channel_id: str = "", category: str = "") -> dict:
    """metadata.json veya metadata.txt dosyasını parse eder."""
    result = {"title": "", "description": "", "tags": [], "narration": "", "plan_id": "", "language": "en", "created_at": ""}
    
    json_path = folder / "metadata.json"
    txt_path = folder / "metadata.txt"
    info_path = folder / "video_info.json"
    
    # 1. JSON kontrolü
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            result["title"] = data.get("title", "")
            result["description"] = data.get("description", "") or data.get("desc", "")
            result["tags"] = data.get("tags", [])
            result["narration"] = data.get("narration", "")
            result["plan_id"] = data.get("plan_id", "")
            result["language"] = data.get("language", "en")
            result["created_at"] = data.get("created_at", "")
        except Exception as e:
            print(f"[META] JSON Parse hatası ({json_path}): {e}")
            
    # 2. video_info.json kontrolü (eksik alanları tamamla)
    if info_path.exists():
        try:
            vinfo = json.loads(info_path.read_text(encoding="utf-8"))
            if not result["title"]:
                result["title"] = vinfo.get("title", "")
            if not result["description"]:
                result["description"] = vinfo.get("description", "") or vinfo.get("desc", "")
            if not result["tags"]:
                result["tags"] = vinfo.get("tags", [])
        except Exception:
            pass

    # 3. Eski TXT formatı fallback
    if (not result["title"] or not result["description"]) and txt_path.exists():
        try:
            content = txt_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            
            sections = {}
            current_section = None
            section_lines = []
            
            for line in lines:
                line_str = line.strip()
                if not line_str:
                    if current_section:
                        section_lines.append(line)
                    continue
                if line_str.startswith("#") and not current_section:
                    continue
                if line_str.startswith("═"):
                    continue
                
                upper_line = line_str.upper()
                if "BAŞLIK" in upper_line or "TITLE" in upper_line:
                    if current_section and section_lines:
                        sections[current_section] = "\n".join(section_lines).strip()
                    current_section = "TITLE"
                    section_lines = []
                elif "AÇIKLAMA" in upper_line or "DESCRIPTION" in upper_line:
                    if current_section and section_lines:
                        sections[current_section] = "\n".join(section_lines).strip()
                    current_section = "DESCRIPTION"
                    section_lines = []
                elif "ETIKETLER" in upper_line or "TAGS" in upper_line:
                    if current_section and section_lines:
                        sections[current_section] = "\n".join(section_lines).strip()
                    current_section = "TAGS"
                    section_lines = []
                elif "SESLENDIRME" in upper_line or "NARRATION" in upper_line:
                    if current_section and section_lines:
                        sections[current_section] = "\n".join(section_lines).strip()
                    current_section = "NARRATION"
                    section_lines = []
                elif "ANAHTAR" in upper_line or "KEYWORDS" in upper_line:
                    if current_section and section_lines:
                        sections[current_section] = "\n".join(section_lines).strip()
                    current_section = "KEYWORDS"
                    section_lines = []
                else:
                    if current_section:
                        section_lines.append(line)
                        
            if current_section and section_lines:
                sections[current_section] = "\n".join(section_lines).strip()
                
            if not result["title"]:
                result["title"] = sections.get("TITLE", "")
            if not result["description"]:
                result["description"] = sections.get("DESCRIPTION", "")
            if not result["tags"]:
                tags_raw = sections.get("TAGS", "")
                result["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]
            if not result["narration"]:
                result["narration"] = sections.get("NARRATION", "")
        except Exception as e:
            print(f"[META] TXT Parse hatası ({txt_path}): {e}")

    # 4. Son Kontrol: Başlık, açıklama ve etiketlerin asla boş kalmamasını sağla (Kategoriye ve Dile Duyarlı)
    if not result["title"]:
        result["title"] = folder.name

    eff_cid = channel_id
    if not eff_cid:
        for p in folder.parents:
            if p.name not in ("output", "yuklenecek", "yuklenen", "arsiv", "files", ""):
                eff_cid = p.name
                break

    try:
        from channel_manager import get_localized_metadata, is_bogus_fallback, ChannelManager
        ch_info = ChannelManager().get_channel(eff_cid) or {} if eff_cid else {}
        lang = ch_info.get("language") or result.get("language") or "tr"
        cat = category or ch_info.get("topic_category") or "reddit_stories"

        if is_bogus_fallback(result["description"], result["tags"], language=lang, category=cat):
            loc_desc, loc_tags = get_localized_metadata(result["title"], language=lang, category=cat)
            result["description"] = loc_desc
            result["tags"] = loc_tags

        if not result["description"] or not result["tags"]:
            loc_desc, loc_tags = get_localized_metadata(result["title"], language=lang, category=cat)
            if not result["description"]:
                result["description"] = loc_desc
            if not result["tags"]:
                result["tags"] = loc_tags
    except Exception:
        if not result["description"]:
            result["description"] = f"{result['title']}\n\n#Shorts #Viral"
        if not result["tags"]:
            result["tags"] = ["Shorts", "Viral"]

    return result



def _parse_video_folder(folder: Path, channel_id: str, category: str, out_path: Path, channel_map: dict, parent_folder_name: str = None):
    video_file = folder / "final.mp4"
    meta_parsed = _parse_metadata(folder, channel_id=channel_id, category=category)
    
    extra = {}
    info_file = folder / "video_info.json"
    if info_file.exists():
        try:
            extra = json.loads(info_file.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    archived = (category == "yuklenen") or (folder / ".archived").exists()
    uploaded_youtube = extra.get("uploaded_youtube", archived)
    uploaded_instagram = extra.get("uploaded_instagram", archived)
    uploaded_tiktok = extra.get("uploaded_tiktok", archived)
    
    try:
        rel_folder = folder.relative_to(out_path)
        folder_name = str(rel_folder)
    except Exception:
        if parent_folder_name:
            folder_name = f"{channel_id}/{category}/{parent_folder_name}/{folder.name}"
        else:
            folder_name = f"{channel_id}/{category}/{folder.name}"
        
    folder_basename = folder.name
    try:
        to_parse = parent_folder_name if parent_folder_name else folder_basename
        parts = to_parse.rsplit("_", 2)
        ts_str = f"{parts[-2]}_{parts[-1].split('_shorts')[0]}"
        created_dt = datetime.strptime(ts_str[:15], "%Y%m%d_%H%M%S").isoformat()
    except Exception:
        created_dt = ""
        
    created_at = meta_parsed.get("created_at") or created_dt
    
    return {
        "folder": folder_name,
        "folder_path": str(folder),
        "video_path": str(video_file),
        "title": meta_parsed["title"],
        "description": meta_parsed["description"],
        "tags": meta_parsed["tags"],
        "narration": meta_parsed["narration"],
        "plan_id": meta_parsed["plan_id"],
        "language": meta_parsed["language"],
        "channel_id": channel_id,
        "channel_name": channel_map.get(channel_id, channel_id),
        "shorts_mode": extra.get("shorts_mode", False) or (parent_folder_name is not None) or ("shorts_" in folder.name),
        "transition": extra.get("transition", "fade"),
        "resolution": extra.get("resolution", ""),
        "duration_sec": extra.get("duration_sec", 0.0),
        "created_at": created_at,
        "archived": archived,
        "uploaded_youtube": uploaded_youtube,
        "uploaded_instagram": uploaded_instagram,
        "uploaded_tiktok": uploaded_tiktok,
    }


@app.get("/api/video-file")
def stream_video_file(path: str):
    """Verilen video_path dosyasını doğrudan döner."""
    from fastapi.responses import FileResponse
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")
    return FileResponse(str(p), media_type="video/mp4")


@app.get("/api/output")
def list_output_videos():
    """output/ klasöründeki tüm video klasörlerini listeler (yeni ve eski yapı, alt klasörler dahil)."""
    output_dir = settings_mgr.get("output_dir", "output")
    out_path   = Path(output_dir)
    videos     = []

    if not out_path.exists():
        return []

    mgr = ChannelManager()
    channel_map = {ch["channel_id"]: ch.get("name", ch["channel_id"]) for ch in mgr.all_channels()}

    # 1. Yeni yapıyı tara: output/<channel_id>/yuklenecek/ ve output/<channel_id>/yuklenen/
    for channel_folder in out_path.iterdir():
        if not channel_folder.is_dir() or channel_folder.name.startswith("."):
            continue
        for category in ["yuklenecek", "yuklenen"]:
            cat_dir = channel_folder / category
            if cat_dir.exists() and cat_dir.is_dir():
                for folder in cat_dir.iterdir():
                    if not folder.is_dir() or folder.name.startswith("."):
                        continue
                    
                    video_file = folder / "final.mp4"
                    if video_file.exists():
                        videos.append(_parse_video_folder(folder, channel_folder.name, category, out_path, channel_map))
                        
                    # Uzun videonun altındaki alt Shorts klasörlerini (shorts_*) tara
                    for subfolder in folder.iterdir():
                        if subfolder.is_dir() and subfolder.name.startswith("shorts_"):
                            sub_video_file = subfolder / "final.mp4"
                            if sub_video_file.exists():
                                videos.append(_parse_video_folder(subfolder, channel_folder.name, category, out_path, channel_map, parent_folder_name=folder.name))

    # 2. Eski yapıyı tara (doğrudan output/ altındaki video klasörleri)
    for folder in out_path.iterdir():
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        if (folder / "yuklenecek").exists() or (folder / "yuklenen").exists():
            continue
            
        video_file = folder / "final.mp4"
        if not video_file.exists():
            continue

        meta_parsed = _parse_metadata(folder)

        extra = {}
        info_file = folder / "video_info.json"
        if info_file.exists():
            try:
                extra = json.loads(info_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        archived = (folder / ".archived").exists()
        uploaded_youtube = extra.get("uploaded_youtube", archived)
        uploaded_instagram = extra.get("uploaded_instagram", archived)
        uploaded_tiktok = extra.get("uploaded_tiktok", archived)
        
        folder_name = folder.name
        try:
            parts = folder_name.rsplit("_", 2)
            ts_str = f"{parts[-2]}_{parts[-1].split('_shorts')[0]}"
            created_dt = datetime.strptime(ts_str[:15], "%Y%m%d_%H%M%S").isoformat()
        except Exception:
            created_dt = ""
            
        created_at = meta_parsed.get("created_at") or created_dt

        channel_id_guess = ""
        try:
            name_parts = folder_name.split("_")
            if name_parts[0].isdigit() and len(name_parts[0]) == 4 and len(name_parts) > 1:
                channel_id_guess = name_parts[1]
            else:
                channel_id_guess = name_parts[0]
        except Exception:
            pass

        videos.append({
            "folder": folder_name,
            "folder_path": str(folder),
            "video_path": str(video_file),
            "title": meta_parsed["title"],
            "description": meta_parsed["description"],
            "tags": meta_parsed["tags"],
            "narration": meta_parsed["narration"],
            "plan_id": meta_parsed["plan_id"],
            "language": meta_parsed["language"],
            "channel_id": channel_id_guess,
            "shorts_mode": extra.get("shorts_mode", False),
            "transition": extra.get("transition", "fade"),
            "resolution": extra.get("resolution", ""),
            "duration_sec": extra.get("duration_sec", 0.0),
            "created_at": created_at,
            "archived": archived,
            "uploaded_youtube": uploaded_youtube,
            "uploaded_instagram": uploaded_instagram,
            "uploaded_tiktok": uploaded_tiktok,
        })

    videos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return videos


@app.post("/api/output/{folder_name:path}/archive")
def archive_video(folder_name: str):
    """Video klasörünü yuklenecek/ altından yuklenen/ altına taşır."""
    output_dir = settings_mgr.get("output_dir", "output")
    folder     = Path(output_dir) / folder_name
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Klasör bulunamadı.")
    
    parts = Path(folder_name).parts
    if len(parts) >= 3 and parts[1] == "yuklenecek":
        channel_id = parts[0]
        folder_basename = parts[2]
        dest_parent = Path(output_dir) / channel_id / "yuklenen"
        dest_parent.mkdir(parents=True, exist_ok=True)
        dest_folder = dest_parent / folder_basename
        
        if dest_folder.exists():
            import shutil
            shutil.rmtree(dest_folder)
            
        folder.rename(dest_folder)
        try:
            from retention_manager import tag_archived_folder
            tag_archived_folder(dest_folder, retention_days=20)
        except Exception:
            pass
        new_folder_name = f"{channel_id}/yuklenen/{folder_basename}"
        return {"success": True, "folder": new_folder_name, "archived": True}
    else:
        (folder / ".archived").touch()
        try:
            from retention_manager import tag_archived_folder
            tag_archived_folder(folder, retention_days=20)
        except Exception:
            pass
        return {"success": True, "folder": folder_name, "archived": True}


@app.delete("/api/output/{folder_name:path}/archive")
def unarchive_video(folder_name: str):
    """Arşivlenmiş videoyu yuklenen/ altından yuklenecek/ altına geri taşır."""
    output_dir = settings_mgr.get("output_dir", "output")
    folder     = Path(output_dir) / folder_name
    
    parts = Path(folder_name).parts
    if len(parts) >= 3 and parts[1] == "yuklenen":
        channel_id = parts[0]
        folder_basename = parts[2]
        dest_parent = Path(output_dir) / channel_id / "yuklenecek"
        dest_parent.mkdir(parents=True, exist_ok=True)
        dest_folder = dest_parent / folder_basename
        
        if folder.exists():
            if dest_folder.exists():
                import shutil
                shutil.rmtree(dest_folder)
            folder.rename(dest_folder)
            new_folder_name = f"{channel_id}/yuklenecek/{folder_basename}"
            return {"success": True, "folder": new_folder_name, "archived": False}
        raise HTTPException(status_code=404, detail="Klasör bulunamadı.")
    else:
        flag_file = folder / ".archived"
        if flag_file.exists():
            flag_file.unlink()
        return {"success": True, "folder": folder_name, "archived": False}


@app.post("/api/output/{folder_name:path}/status")
def update_upload_status(folder_name: str, payload: dict):
    """Videonun platform yükleme durumlarını günceller ve hepsi yüklendi ise otomatik arşivler; değilse geri taşır."""
    output_dir = settings_mgr.get("output_dir", "output")
    folder     = Path(output_dir) / folder_name
    if not folder.exists():
        from urllib.parse import unquote
        folder = Path(output_dir) / unquote(folder_name)
        if not folder.exists():
            raise HTTPException(status_code=404, detail=f"Klasör bulunamadı: {folder_name}")
        
    info_file = folder / "video_info.json"
    extra = {}
    if info_file.exists():
        try:
            extra = json.loads(info_file.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    if "youtube" in payload:
        extra["uploaded_youtube"] = bool(payload["youtube"])
    if "instagram" in payload:
        extra["uploaded_instagram"] = bool(payload["instagram"])
    if "tiktok" in payload:
        extra["uploaded_tiktok"] = bool(payload["tiktok"])
        
    try:
        info_file.write_text(json.dumps(extra, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Durum kaydedilemedi: {e}")
        
    # Eğer aktif sosyal medya platformlarının tamamı yüklendi (True) ise otomatik arşivle
    archived = False
    new_folder_name = folder_name
    
    parts = Path(folder_name).parts
    channel_id = parts[0] if len(parts) >= 1 else ""
    
    # Parent klasör yolunu bul (eğer alt Shorts ise)
    if len(parts) >= 4 and parts[3].startswith("shorts_"):
        parent_folder = Path(output_dir) / parts[0] / parts[1] / parts[2]
    else:
        parent_folder = folder
        
    from channel_manager import ChannelManager
    ch_mgr = ChannelManager()
    channel = ch_mgr.get_channel(channel_id)
    if not channel and channel_id:
        for c in ch_mgr.all_channels():
            if c.get("channel_id", "").lower() == channel_id.lower():
                channel = c
                break
    
    def is_item_all_uploaded(info_file_path: Path):
        if not info_file_path.exists():
            return False
        try:
            item_extra = json.loads(info_file_path.read_text(encoding="utf-8"))
        except Exception:
            return False
            
        if channel:
            need_yt = channel.get("youtube", True)
            if need_yt and not item_extra.get("uploaded_youtube"):
                return False
            if channel.get("instagram", False) and not item_extra.get("uploaded_instagram"):
                return False
            if channel.get("tiktok", False) and not item_extra.get("uploaded_tiktok"):
                return False
        else:
            if not (item_extra.get("uploaded_youtube") or item_extra.get("uploaded_instagram") or item_extra.get("uploaded_tiktok")):
                return False
        return True

    # Bütün grubu kontrol et
    is_group_completed = False
    if len(parts) >= 3 and parts[1] == "yuklenecek":
        # 1. Asıl videoyu kontrol et
        parent_info = parent_folder / "video_info.json"
        if is_item_all_uploaded(parent_info):
            # 2. Tüm alt Shorts'ları kontrol et
            all_shorts_done = True
            for sub in parent_folder.iterdir():
                if sub.is_dir() and sub.name.startswith("shorts_"):
                    if not is_item_all_uploaded(sub / "video_info.json"):
                        all_shorts_done = False
                        break
            if all_shorts_done:
                is_group_completed = True

    if is_group_completed:
        # Tüm grup bitti! Parent klasörünü 'yuklenen' altına taşı
        folder_basename = parts[2]
        dest_parent = Path(output_dir) / channel_id / "yuklenen"
        dest_parent.mkdir(parents=True, exist_ok=True)
        dest_folder = dest_parent / folder_basename
        
        if dest_folder.exists():
            import shutil
            shutil.rmtree(dest_folder)
            
        try:
            parent_folder.rename(dest_folder)
            try:
                from retention_manager import tag_archived_folder
                tag_archived_folder(dest_folder, retention_days=20)
            except Exception:
                pass
            print(f"[STATUS] Incident group archived successfully: {parent_folder.name}")
            
            # folder_name'i yeni konuma göre güncelle
            if len(parts) >= 4:
                new_folder_name = f"{channel_id}/yuklenen/{folder_basename}/{parts[3]}"
            else:
                new_folder_name = f"{channel_id}/yuklenen/{folder_basename}"
            archived = True
        except Exception as e:
            print(f"[STATUS] Taşıma hatası: {e}")

    if extra.get("uploaded_youtube") and channel_id:
        try:
            from content_planner import ContentPlanner
            planner = ContentPlanner(Path(output_dir) / channel_id)
            plan_id = extra.get("plan_id")
            if not plan_id:
                meta_file = parent_folder / "metadata.json"
                if meta_file.exists():
                    try:
                        mdata = json.loads(meta_file.read_text(encoding="utf-8"))
                        plan_id = mdata.get("plan_id")
                    except Exception:
                        pass
            if not plan_id:
                folder_pfx = parent_folder.name.split("_")[0]
                if folder_pfx.isdigit():
                    plan_id = str(int(folder_pfx))
            if plan_id:
                planner.mark_as_uploaded(plan_id)
                print(f"[STATUS] Plan sync: row #{plan_id} marked as uploaded in icerik_plani.csv")
        except Exception as plan_sync_err:
            print(f"[STATUS] Plan sync warning: {plan_sync_err}")

    return {
        "success": True,
        "folder": new_folder_name,
        "archived": archived,
        "uploaded_youtube": extra.get("uploaded_youtube", False),
        "uploaded_instagram": extra.get("uploaded_instagram", False),
        "uploaded_tiktok": extra.get("uploaded_tiktok", False)
    }


# ═══════════════════════════════════════════════════════════════
# İÇERİK PLANLAMA API
# ═══════════════════════════════════════════════════════════════

class PlanRequest(BaseModel):
    count: int = 10


class AssistantProduceRequest(BaseModel):
    message: str
    selected_channel_id: Optional[str] = None


class AssistantProductionIntent(BaseModel):
    action: str
    provider: Optional[str] = None
    category: Optional[str] = None
    channel_id: Optional[str] = None
    count: int = 1
    clarification: Optional[str] = None


class IdeaItem(BaseModel):
    title: str
    topic: str
    description: Optional[str] = None


class ScrapedIdeasPayload(BaseModel):
    ideas: List[IdeaItem]


from content_planner import ContentPlanner


def _normalize_assistant_category(category: Optional[str]) -> str:
    normalized = (category or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized == "reddit":
        return "reddit_stories"
    return normalized


def _interpret_assistant_command(message: str, channels: list[dict], selected_channel_id: Optional[str]) -> AssistantProductionIntent:
    """LM Studio ile doğal dil komutunu sınırlı ve doğrulanabilir bir üretim niyetine dönüştürür."""
    from script_writer import LMStudioWriter, _parse_json

    active_channels = [ch for ch in channels if ch.get("active", True)]
    channel_options = [
        {
            "channel_id": ch["channel_id"],
            "name": ch.get("name", ch["channel_id"]),
            "category": _normalize_assistant_category(ch.get("topic_category")),
        }
        for ch in active_channels
    ]
    preferred_channel = next(
        (item for item in channel_options if item["channel_id"] == selected_channel_id),
        None,
    )
    lm_url = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")
    lm_model = settings_mgr.get("lmstudio_model", "")
    assistant = LMStudioWriter(base_url=lm_url, model=lm_model)

    system_prompt = (
        "Sen video üretim sisteminin Türkçe komut ayrıştırıcısısın. "
        "Yalnızca istenen alanları içeren tek bir JSON nesnesi döndür; markdown veya açıklama ekleme. "
        "Desteklenen action değerleri: generate_videos, clarify. "
        "provider yalnızca gemini, claude, ollama veya lmstudio olabilir; komutta sağlayıcı yoksa null kullan. "
        "category mevcut kategori değerlerinden biri olmalı; kategori anlaşılamıyorsa null kullan. "
        "channel_id yalnızca verilen aktif kanal kimliklerinden biri olmalı; belirli kanal istenmiyorsa null kullan. "
        "count istenen toplam video sayısıdır; belirtilmemişse 1 kullan. "
        "Gerekli hedef anlaşılmıyorsa action=clarify seç ve kısa Türkçe clarification yaz. "
        "Şema: {\"action\":\"generate_videos|clarify\",\"provider\":\"gemini|claude|ollama|lmstudio|null\","
        "\"category\":null,\"channel_id\":null,\"count\":1,\"clarification\":null}"
    )
    user_prompt = json.dumps(
        {
            "command": message,
            "active_channels": channel_options,
            "selected_channel_preference": preferred_channel,
            "allowed_categories": sorted({item["category"] for item in channel_options}),
        },
        ensure_ascii=False,
    )
    try:
        response = assistant.client.chat.completions.create(
            model=assistant._get_model(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
            temperature=0.1,
        )
        parsed = _parse_json(response.choices[0].message.content or "")
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LM Studio komutu yorumlayamadı. Yerel sunucuyu/modeli kontrol edin: {exc}",
        ) from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="LM Studio geçerli bir komut JSON'u döndürmedi.")
    try:
        return AssistantProductionIntent(**parsed)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LM Studio komut biçimi geçersiz: {exc}") from exc


def _assistant_production_task(
    exec_id: str,
    channels: list[dict],
    intent: AssistantProductionIntent,
    provider: str,
    api_key: str,
    model: str,
):
    """Planı gerektiği kadar tamamlar ve istenen videoları sırayla üretir."""
    entry = executions[exec_id]
    entry["status"] = "running"
    entry["message"] = "Üretim için içerik planı kontrol ediliyor..."
    try:
        output_dir = settings_mgr.get("output_dir", "output")
        ollama_url = settings_mgr.get("ollama_url", "http://localhost:11434")
        lmstudio_url = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")
        manager = ChannelManager()
        provider_model = model or settings_mgr.get(f"{provider}_model", "") or settings_mgr.get("ai_model", "")
        writer = ScriptWriter(
            provider=provider,
            api_key=api_key,
            model=provider_model,
            ollama_url=ollama_url,
            lmstudio_url=lmstudio_url,
        )
        if writer.provider != provider:
            raise RuntimeError(
                f"İstenen {provider} sağlayıcısı kullanılamıyor; sistem başka bir sağlayıcıya geçmek istedi. "
                "İstenen sağlayıcıya geçmeden üretim durduruldu."
            )

        generator = VideoGenerator(nasa_api_key=settings_mgr.get("nasa_api_key", "DEMO_KEY"))
        planned_work = []
        channel_totals = {}
        for index in range(intent.count):
            channel = channels[index % len(channels)]
            channel_totals[channel["channel_id"]] = channel_totals.get(channel["channel_id"], 0) + 1
            planned_work.append(channel)

        reserved_rows = {}
        for channel in channels:
            channel_id = channel["channel_id"]
            required = channel_totals.get(channel_id, 0)
            if not required:
                continue
            planner = ContentPlanner(Path(output_dir) / channel_id)
            selected_rows = []
            excluded_ids = []
            while len(selected_rows) < required:
                row = planner.get_next_unproduced(exclude_ids=excluded_ids)
                if not row:
                    break
                selected_rows.append(row)
                excluded_ids.append(str(row.get("id", "")))

            missing = required - len(selected_rows)
            if missing:
                entry["message"] = f"{channel.get('name', channel_id)} için {missing} plan konusu oluşturuluyor..."
                existing_topics = [
                    row.get("konu") or row.get("baslik", "")
                    for row in planner.get_plan()
                    if row.get("konu") or row.get("baslik")
                ]
                topics = writer.generate_topic_list(
                    channel,
                    count=missing,
                    existing_topics=existing_topics,
                )
                if len(topics) < missing:
                    raise RuntimeError(
                        f"{channel.get('name', channel_id)} için {missing} yeni plan konusu istendi, "
                        f"ancak AI yalnızca {len(topics)} konu üretti."
                    )
                planner.add_topics(topics[:missing])
                while len(selected_rows) < required:
                    row = planner.get_next_unproduced(exclude_ids=excluded_ids)
                    if not row:
                        break
                    selected_rows.append(row)
                    excluded_ids.append(str(row.get("id", "")))
            if len(selected_rows) != required:
                raise RuntimeError(f"{channel.get('name', channel_id)} kanalında üretilecek plan satırları hazırlanamadı.")
            reserved_rows[channel_id] = iter(selected_rows)

        results = []
        for index, channel in enumerate(planned_work, start=1):
            channel_id = channel["channel_id"]
            row = next(reserved_rows[channel_id])
            entry["progress"] = int((index - 1) * 100 / intent.count)
            entry["message"] = (
                f"Video {index}/{intent.count} üretiliyor: "
                f"{channel.get('name', channel_id)} — {row.get('konu') or row.get('baslik', '')}"
            )
            result = run_channel(
                channel_config=channel,
                writer=writer,
                generator=generator,
                manager=manager,
                output_dir=output_dir,
                shorts_mode=channel.get("shorts_mode", False),
                transition=channel.get("transition", "fade"),
                edit_options=manager.get_resolved_edit_options(channel_id),
                force_row_id=str(row["id"]),
            )
            if not result.get("success"):
                raise RuntimeError(
                    f"Video {index}/{intent.count} başarısız oldu "
                    f"({channel.get('name', channel_id)}): {result.get('error') or 'Bilinmeyen üretim hatası'}"
                )
            results.append(
                {
                    "channel_id": channel_id,
                    "channel_name": channel.get("name", channel_id),
                    "title": result.get("title", ""),
                    "folder": result.get("folder", ""),
                    "plan_id": result.get("plan_id", ""),
                }
            )
            entry["result"] = results
            _clear_memory(trigger=f"assistant_step_{index}")

        entry["status"] = "success"
        entry["progress"] = 100
        entry["message"] = f"{len(results)} video başarıyla sırayla üretildi."
        _clear_memory(trigger="assistant_production_complete")
    except Exception as exc:
        _clear_memory(trigger="assistant_production_error")
        entry["status"] = "failed"
        entry["error"] = str(exc)
        entry["message"] = f"Üretim durduruldu: {exc}"


@app.post("/api/assistant/produce")
def start_assistant_production(payload: AssistantProduceRequest, background_tasks: BackgroundTasks):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Üretim komutu boş olamaz.")

    manager = ChannelManager()
    channels = manager.get_active_channels()
    if not channels:
        raise HTTPException(status_code=400, detail="Üretilebilecek aktif kanal bulunamadı.")

    intent = _interpret_assistant_command(message, channels, payload.selected_channel_id)
    if intent.action != "generate_videos":
        raise HTTPException(
            status_code=422,
            detail=intent.clarification or "Komut hedefini anlayamadım. Bir kanal/kategori ve üretilecek video sayısını belirtin.",
        )
    provider = intent.provider or settings_mgr.get("ai_provider", "gemini")
    if provider not in ("gemini", "claude", "ollama", "lmstudio"):
        raise HTTPException(status_code=422, detail="Desteklenmeyen AI sağlayıcısı istendi.")
    if not 1 <= intent.count <= 20:
        raise HTTPException(status_code=422, detail="Tek komutta 1–20 video üretilebilir.")

    category = _normalize_assistant_category(intent.category)
    if intent.channel_id:
        target = next((ch for ch in channels if ch["channel_id"] == intent.channel_id), None)
        if not target:
            raise HTTPException(status_code=422, detail="Komutta belirtilen kanal aktif değil veya bulunamadı.")
        if category and _normalize_assistant_category(target.get("topic_category")) != category:
            raise HTTPException(status_code=422, detail="Seçilen kanal belirtilen kategoriyle eşleşmiyor.")
        target_channels = [target]
    elif category:
        target_channels = [
            ch for ch in channels
            if _normalize_assistant_category(ch.get("topic_category")) == category
        ]
        if not target_channels:
            raise HTTPException(status_code=422, detail=f"'{category}' kategorisinde aktif kanal bulunamadı.")
    elif payload.selected_channel_id:
        target = next((ch for ch in channels if ch["channel_id"] == payload.selected_channel_id), None)
        if not target:
            raise HTTPException(status_code=422, detail="Seçili kanal artık aktif değil.")
        target_channels = [target]
    else:
        raise HTTPException(status_code=422, detail="Aktif bir kanal veya kategori belirtilmedi.")

    target_channels = target_channels[:intent.count]
    api_key = settings_mgr.get("anthropic_api_key", "") if provider == "claude" else (
        settings_mgr.get("gemini_api_key", "") if provider == "gemini" else ""
    )
    if provider in ("gemini", "claude") and not api_key:
        provider_name = "Gemini" if provider == "gemini" else "Claude"
        raise HTTPException(status_code=400, detail=f"{provider_name} API anahtarı ayarlarda bulunamadı.")
    model = settings_mgr.get(f"{provider}_model", "") or settings_mgr.get("ai_model", "")

    exec_id = f"assistant_{uuid.uuid4().hex}"
    selected_categories = sorted({_normalize_assistant_category(ch.get("topic_category")) for ch in target_channels})
    executions[exec_id] = {
        "exec_id": exec_id,
        "channel_id": target_channels[0]["channel_id"],
        "status": "pending",
        "message": "Komut anlaşıldı, üretim kuyruğa alındı...",
        "progress": 0,
        "timestamp": datetime.now().isoformat(),
        "intent": {
            "provider": provider,
            "category": selected_categories[0] if len(selected_categories) == 1 else category,
            "count": intent.count,
            "channels": [ch.get("name", ch["channel_id"]) for ch in target_channels],
        },
    }
    background_tasks.add_task(
        _assistant_production_task,
        exec_id,
        target_channels,
        intent,
        provider,
        api_key,
        model,
    )
    return {"exec_id": exec_id, **executions[exec_id]}


@app.post("/api/channels/{channel_id}/plan")
def create_channel_plan(channel_id: str, payload: PlanRequest):
    """Kanal için AI ile toplu konu planı üretir ve CSV'ye kaydeder."""
    mgr = ChannelManager()
    ch = mgr.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    provider = settings_mgr.get("ai_provider", "claude")
    api_key = ""
    if provider == "claude":
        api_key = settings_mgr.get("anthropic_api_key")
    elif provider == "gemini":
        api_key = settings_mgr.get("gemini_api_key")
        
    ai_model = settings_mgr.get(f"{provider}_model", "")
    ollama_url = settings_mgr.get("ollama_url", "http://localhost:11434")
    lmstudio_url = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")
    
    writer = ScriptWriter(
        provider=provider,
        api_key=api_key,
        model=ai_model,
        ollama_url=ollama_url,
        lmstudio_url=lmstudio_url,
    )
    
    try:
        from mind_map import MindMapManager
        mm_mgr = MindMapManager(channel_dir)
        
        # Load or sync mind map
        category = ch.get("topic_category", "space")
        if not mm_mgr.exists():
            print("[SERVER] Zihin haritası bulunamadı. Oluşturuluyor...")
            mind_map = mm_mgr.sync_from_csv(writer, planner, category=category, channel_config=ch)
        else:
            mind_map = mm_mgr.load()

        existing_rows = planner.get_plan()
        existing_titles = [r.get("baslik") for r in existing_rows if r.get("baslik")]
        
        topics = writer.generate_topic_list(ch, count=payload.count, existing_topics=existing_titles, mind_map=mind_map)
        new_rows = planner.add_topics(topics)
        
        # Update mind map with new topics
        mm_mgr.update_with_new_topics(writer, new_rows, category=category, channel_config=ch)
        
        return {"success": True, "count": len(new_rows), "topics": new_rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Konu planlama hatası: {str(e)}")


@app.get("/api/channels/{channel_id}/plan")
def get_channel_plan(channel_id: str):
    """Kanalın içerik planını listeler."""
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    plan = planner.get_plan()
    
    # Tüm videoları tara
    all_videos = list_output_videos()
    channel_videos = [v for v in all_videos if v.get("channel_id") == channel_id]
    
    # Video plan_id eşleştirme
    video_map = {str(v.get("plan_id")): v for v in channel_videos if v.get("plan_id")}
    
    # ── YARIM KALMIŞ VEYA TAMAMLANMIŞ TÜM PROJELERİ TARA ──
    incomplete_map = {}
    yuklenecek_dir = channel_dir / "yuklenecek"
    yuklenen_dir = channel_dir / "yuklenen"
    search_dirs = [channel_dir]
    if yuklenecek_dir.exists() and yuklenecek_dir.is_dir():
        search_dirs.append(yuklenecek_dir)
    if yuklenen_dir.exists() and yuklenen_dir.is_dir():
        search_dirs.append(yuklenen_dir)
        
    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for folder in s_dir.iterdir():
            if not folder.is_dir() or folder.name.startswith("."):
                continue
                
            p_id = None
            meta_json = folder / "metadata.json"
            if meta_json.exists():
                try:
                    meta_data = json.loads(meta_json.read_text(encoding="utf-8"))
                    p_id = str(meta_data.get("plan_id", ""))
                except Exception:
                    pass
            
            # Klasör adından row_id tahmin et (örn: 0016_blackboxaudioo_...)
            if not p_id:
                try:
                    parts = folder.name.split("_")
                    if parts[0].isdigit() and len(parts[0]) == 4:
                        p_id = str(int(parts[0]))
                except Exception:
                    pass
                    
            if p_id:
                images = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png") and f.name.startswith("scene_")]
                audios = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in (".wav", ".mp3") and f.name.startswith("narration")]
                
                if images and audios:
                    incomplete_map[p_id] = {
                        "folder": folder.name,
                        "folder_path": str(folder),
                        "images_count": len(images),
                        "audio_file": audios[0].name
                    }
                    
    from audio_library import get_recommendation
    from browser_uploader import find_planned_video_folder
    resolved_plan = []
    for row in plan:
        row_id = str(row.get("id"))
        row_copy = dict(row)
        if not row_copy.get("secilen_muzik"):
            row_copy["secilen_muzik"] = get_recommendation(row_copy.get("konu", ""), row_copy.get("baslik", ""))

        vinfo = find_planned_video_folder(channel_id, row_id, output_base_dir=output_dir)
        if vinfo and vinfo.get("is_produced"):
            row_copy["uretildi"] = "Evet"
            row_copy["video_folder"] = vinfo.get("folder")
            row_copy["video_path"] = vinfo.get("video_path")
            row_copy["video_url"] = vinfo.get("video_url")
            row_copy["yuklendi"] = "Evet" if vinfo.get("is_uploaded") else "Hayır"
        
        if row_id in video_map:
            v = video_map[row_id]
            if not row_copy.get("video_folder"):
                row_copy["video_folder"] = v.get("folder")
            if not row_copy.get("video_path"):
                row_copy["video_path"] = v.get("video_path")
            row_copy["transition"] = v.get("transition")
            row_copy["shorts_mode"] = v.get("shorts_mode")
            row_copy["duration_sec"] = v.get("duration_sec", 0.0)
            row_copy["subtitle_preset"] = v.get("subtitle_preset", "bold")
            row_copy["subtitle_animation"] = v.get("subtitle_animation", "fade")
            row_copy["bgm_volume"] = v.get("bgm_volume", 0.15)
            row_copy["watermark_text"] = v.get("watermark_text", "")
            row_copy["censor_faces"] = v.get("censor_faces", False)
            
        if row_id in incomplete_map:
            inc = incomplete_map[row_id]
            row_copy["recompose_available"] = True
            row_copy["recompose_folder"] = inc["folder_path"]
            row_copy["recompose_images_count"] = inc["images_count"]
            row_copy["recompose_audio"] = inc["audio_file"]
            
        resolved_plan.append(row_copy)
        
    total = len(resolved_plan)
    produced = sum(1 for r in resolved_plan if r.get("uretildi") == "Evet")
    uploaded = sum(1 for r in resolved_plan if r.get("yuklendi") == "Evet")
    unproduced = total - produced

    stats = {
        "total": total,
        "produced": produced,
        "unproduced": unproduced,
        "uploaded": uploaded,
    }

    return {
        "success": True,
        "plan": resolved_plan,
        "stats": stats,
    }


# ── Gemini Web Automation Endpoints ──────────────────────────────

@app.get("/api/channels/{channel_id}/plan/next-unproduced")
def get_next_unproduced_topic(channel_id: str, exclude_ids: Optional[str] = Query(default=None)):
    """Sıradaki üretilmemiş içerik konusunu ve kanal ayarlarını döner."""
    mgr = ChannelManager()
    channel = mgr.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    parsed_exclude = [x.strip() for x in exclude_ids.split(",") if x.strip()] if exclude_ids else None
    item = planner.get_next_unproduced(exclude_ids=parsed_exclude)
    if not item:
        return {"success": True, "has_unproduced": False}
        
    return {
        "success": True,
        "has_unproduced": True,
        "item": item,
        "channel": {
            "channel_id": channel.get("channel_id"),
            "name": channel.get("name"),
            "language": channel.get("language", "en"),
            "topic_category": channel.get("topic_category", "space"),
            "shorts_mode": channel.get("shorts_mode", False),
        }
    }


@app.post("/api/channels/{channel_id}/plan/{row_id}/gemini-prompt")
def get_gemini_prompt(channel_id: str, row_id: str):
    """Gemini Web için senaryo üretme promptunu oluşturur."""
    mgr = ChannelManager()
    channel = mgr.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    row = planner.get_row_by_id(row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plan satırı bulunamadı.")
        
    # Check if a pre-generated Shorts script exists for this row
    custom_script_file = channel_dir / f"shorts_script_{row_id}.json"
    custom_script = None
    if custom_script_file.exists():
        try:
            custom_script = json.loads(custom_script_file.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    from script_writer import _build_prompt, get_system_prompt
    import re
    
    topic = row.get("konu", "")
    notes = row.get("notlar", "")
    lang = (channel.get("language") or "en").lower().strip()
    is_tr = (lang == "tr" or lang.startswith("tr"))
    category = channel.get("topic_category", "space")

    if category in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
        clean_notes = notes or ""
        # Temizle: eski ilişki / flört anahtar kelimelerini temiz aile/arkadaş dinamiğine dönüştür
        for w in ["sevgilisi", "sevgilimin", "sevgili", "flörtü", "flört", "aşkım", "girlfriend", "boyfriend", "dating"]:
            clean_notes = re.sub(rf'\b{w}\b', 'arkadaşı' if is_tr else 'friend', clean_notes, flags=re.IGNORECASE)
        full_topic = f"{topic} (Detaylar ve Karakterler: {clean_notes})" if clean_notes else topic
    else:
        full_topic = f"{topic} (Detaylar ve Karakterler: {notes})" if notes else topic

    prompt_text, resolved_topic, lang_name = _build_prompt(channel, planned_topic=full_topic)
    
    sys_prompt = get_system_prompt(category, language=lang)
    
    if category in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
        halal_mandate = (
            "\n\n[KESİN VE TAVİZSİZ İSLAMİ KURAL]: Bu senaryo %100 İslami & helal ilkelere uygun olmalıdır. "
            "Kesinlikle sevgili, flört, aldatma, zina, gayrimeşru ilişki, küfür, argo, müstehcenlik, alkol veya kumar OLMAMALIDIR. "
            "Karakterler sadece aile (anne, baba, kardeş), apartman/komşu, esnaf/çırak, halı saha veya ev arkadaşı olmalıdır. "
            "Absürt komedi, zekice şakalar ve beklenmedik ters köşe serbest ve teşvik edilir."
            if is_tr else
            "\n\n[MANDATORY ISLAMIC & HALAL VALUES DIRECTIVE]: This script MUST be 100% clean, ethical, family-friendly, and halal under Islamic principles. "
            "Strictly ZERO dating, boyfriends/girlfriends, romance, flirting, cheating, alcohol, gambling, vulgarity, or profanity. "
            "Characters must be family (mom, dad, siblings), roommates, neighbors/landlords, tradesmen/mechanics, or sports buddies. "
            "Absurd comedy, hilarious misunderstandings, witty roasts, and shocking plot twists are strongly encouraged."
        )
        combined_prompt = f"{sys_prompt}\n\nTask:\n{prompt_text}\n{halal_mandate}"
    else:
        combined_prompt = f"{sys_prompt}\n\nTask:\n{prompt_text}"
    
    return {
        "success": True,
        "prompt": combined_prompt,
        "category": category,
        "language": channel.get("language", "en"),
        "shorts_mode": True if custom_script else channel.get("shorts_mode", False),
        "topic": topic,
        "custom_script": custom_script
    }


@app.post("/api/channels/{channel_id}/plan/{row_id}/create-shorts")
def create_shorts_from_longform(channel_id: str, row_id: str, background_tasks: BackgroundTasks):
    """Üretilmiş uzun videodan (4 dk+) AI ile 3 adet Shorts türetip arka planda otomatik üretir."""
    mgr = ChannelManager()
    channel = mgr.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    row = planner.get_row_by_id(row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plan satırı bulunamadı.")
        
    # Eşleşen üretilmiş videoyu bul
    all_videos = list_output_videos()
    video = None
    for v in all_videos:
        if str(v.get("plan_id")) == str(row_id):
            video = v
            break
            
    # Eski videolar veya plan_id'si boş olan kayıtlar için başlık/konu/klasör bazlı yedek eşleştirme
    if not video:
        def clean_str(s):
            if not s: return ""
            return "".join(c.lower() for c in s if c.isalnum())
            
        row_title_clean = clean_str(row.get("baslik", ""))
        row_konu_clean = clean_str(row.get("konu", ""))
        
        for v in all_videos:
            if v.get("channel_id") != channel_id:
                continue
            v_title_clean = clean_str(v.get("title", ""))
            v_folder_clean = clean_str(v.get("folder", ""))
            
            if (row_title_clean and row_title_clean == v_title_clean) or \
               (row_konu_clean and row_konu_clean in v_folder_clean) or \
               (row_title_clean and row_title_clean in v_folder_clean):
                video = v
                break
                
    if not video:
        raise HTTPException(status_code=400, detail="Bu konuya ait üretilmiş bir video bulunamadı.")
        
    # _auto_generate_shorts_batch için video_result nesnesini hazırla
    video_result = {
        "video_path": video["video_path"],
        "plan_id": row_id
    }
    
    # İzleme için benzersiz bir exec_id oluştur
    exec_id = f"exec_shorts_{channel_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    executions[exec_id] = {
        "channel_id": channel_id,
        "status": "pending",
        "message": "Geçmiş video için Shorts üretim sırasına alındı...",
        "timestamp": datetime.now().isoformat(),
    }
    
    # Arka planda Shorts üretme işini başlat
    background_tasks.add_task(
        render_past_shorts_background_task,
        channel_id=channel_id,
        row_id=row_id,
        video_result=video_result,
        exec_id=exec_id
    )
    
    return {
        "success": True,
        "exec_id": exec_id,
        "message": "4 adet Shorts üretimi arka planda başarıyla başlatıldı! Tamamlandığında video klasöründe görünecektir."
    }


def render_past_shorts_custom_count_task(channel_id: str, row_id: str, video_result: dict, exec_id: str, count: int):
    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = f"{count} adet Shorts senaryoları hazırlanıyor..."
    try:
        mgr = ChannelManager()
        ch = mgr.get_channel(channel_id)
        if not ch:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = "Kanal bulunamadı."
            return

        provider = settings_mgr.get("ai_provider", "claude")
        ai_model = settings_mgr.get("ai_model", "")
        nasa_key = settings_mgr.get("nasa_api_key", "DEMO_KEY")
        output_dir = settings_mgr.get("output_dir", "output")
        ollama_url = settings_mgr.get("ollama_url", "http://localhost:11434")
        lmstudio_url = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")

        api_key = ""
        if provider == "claude":
            api_key = settings_mgr.get("anthropic_api_key")
        elif provider == "gemini":
            api_key = settings_mgr.get("gemini_api_key")

        from script_writer import ScriptWriter
        writer = ScriptWriter(
            provider=provider,
            api_key=api_key,
            model=ai_model,
            ollama_url=ollama_url,
            lmstudio_url=lmstudio_url,
        )
        from video_generator import VideoGenerator
        generator = VideoGenerator(nasa_api_key=nasa_key)

        _auto_generate_shorts_batch(
            channel_id=channel_id,
            plan_id=row_id,
            video_result=video_result,
            exec_id=exec_id,
            writer=writer,
            generator=generator,
            output_dir=output_dir,
            channel_config=ch,
            mgr=mgr,
            count=count,
        )
        executions[exec_id]["status"] = "success"
        executions[exec_id]["message"] = f"{count} Shorts başarıyla oluşturuldu ve video klasörüne eklendi!"
        _clear_memory(trigger="past_shorts_custom_count_success")
    except Exception as e:
        _clear_memory(trigger="past_shorts_custom_count_error")
        executions[exec_id]["status"] = "failed"
        err_msg = str(e)
        if "Connection refused" in err_msg or "Connection error" in err_msg or "ConnectError" in err_msg:
            executions[exec_id]["message"] = "Yapay Zeka Bağlantı Hatası: Yerel modeliniz (LM Studio / Ollama) kapalı! Lütfen yerel yapay zeka uygulamanızı başlatın ve modeli yükleyin."
        elif "API key not valid" in err_msg or "400 INVALID_ARGUMENT" in err_msg:
            executions[exec_id]["message"] = "Geçersiz API Anahtarı: Ayarlar menüsünden geçerli bir Gemini API Anahtarı girdiğinizden emin olun."
        elif "Boş AI yanıtı" in err_msg:
            executions[exec_id]["message"] = "Yapay Zekadan boş yanıt döndü: Yerel modelinizde bir yükleme veya bellek sınırı hatası oluşmuş olabilir. Lütfen LM Studio / Ollama konsolunu kontrol edin."
        else:
            executions[exec_id]["message"] = f"Shorts üretimi sırasında hata oluştu: {err_msg}"


class CreateShortsFromFolderPayload(BaseModel):
    folder: str
    count: int = 4


@app.get("/api/channels/{channel_id}/long-videos")
def get_channel_long_videos(channel_id: str):
    """Kanalın yuklenecek klasöründeki uzun (shorts olmayan) videolarını listeler."""
    all_videos = list_output_videos()
    long_videos = []
    for v in all_videos:
        if (v.get("channel_id") == channel_id and 
            "/yuklenecek/" in v.get("folder", "") and 
            not v.get("shorts_mode")):
            long_videos.append(v)
    return {"success": True, "videos": long_videos}


@app.post("/api/channels/{channel_id}/create-shorts-from-folder")
def create_shorts_from_folder(channel_id: str, payload: CreateShortsFromFolderPayload, background_tasks: BackgroundTasks):
    """Klasör ismi belirtilen uzun videodan AI ile 3 veya 4 adet Shorts türetip arka planda otomatik üretir."""
    mgr = ChannelManager()
    channel = mgr.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    out_path = Path(output_dir)
    
    # Hedef klasörü bul
    target_folder = out_path / payload.folder
    if not target_folder.exists() or not target_folder.is_dir():
        # Fallback
        target_folder = out_path / channel_id / "yuklenecek" / payload.folder
        if not target_folder.exists():
            raise HTTPException(status_code=400, detail="Belirtilen video klasörü bulunamadı.")
            
    video_file = target_folder / "final.mp4"
    if not video_file.exists():
        raise HTTPException(status_code=400, detail="Bu klasörde üretilmiş final.mp4 videosu bulunamadı.")
        
    meta_parsed = _parse_metadata(target_folder)
    row_id = str(meta_parsed.get("plan_id") or "0")
    
    video_result = {
        "video_path": str(video_file),
        "plan_id": row_id
    }
    
    exec_id = f"exec_shorts_{channel_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    executions[exec_id] = {
        "channel_id": channel_id,
        "status": "pending",
        "message": f"Seçilen klasörden {payload.count} adet Shorts üretim sırasına alındı...",
        "timestamp": datetime.now().isoformat(),
    }
    
    background_tasks.add_task(
        render_past_shorts_custom_count_task,
        channel_id=channel_id,
        row_id=row_id,
        video_result=video_result,
        exec_id=exec_id,
        count=payload.count
    )
    
    return {
        "success": True,
        "exec_id": exec_id,
        "message": f"{payload.count} adet Shorts üretimi arka planda başarıyla başlatıldı! Tamamlandığında video klasöründe görünecektir."
    }


# ═══════════════════════════════════════════════════════════════
# SİNEK BEYNİ (DROSOPHILA CONNECTOME) BİYO-AI MÜZİK VE VİDEO ÜRETİMİ
# ═══════════════════════════════════════════════════════════════

class ProduceConnectomePayload(BaseModel):
    genre: str = "emotional"
    duration: float = 180.0
    theme: str = "cosmic"
    is_vertical: bool = False
    scale: Optional[str] = None
    bpm: Optional[float] = None


def run_connectome_production_task(
    channel_id: str,
    exec_id: str,
    genre: str,
    duration: float,
    theme: str,
    is_vertical: bool,
    scale: Optional[str] = None,
    bpm: Optional[float] = None
):
    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = "Sinek Beyni Biyo-AI Konnektom motoru başlatılıyor..."

    try:
        from connectome.generator import generate_connectome_clip
    except ImportError:
        from src.connectome.generator import generate_connectome_clip

    try:
        mgr = ChannelManager()
        ch = mgr.get_channel(channel_id)
        lang = ch.get("language", "tr") if ch else "tr"

        output_dir = settings_mgr.get("output_dir", "output")
        channel_yuklenecek = Path(output_dir) / channel_id / "yuklenecek"
        channel_yuklenecek.mkdir(parents=True, exist_ok=True)

        existing_indices = []
        for d in [channel_yuklenecek, Path(output_dir) / channel_id / "yuklenen"]:
            if d.exists():
                for item in d.iterdir():
                    if item.is_dir():
                        parts = item.name.split("_", 1)
                        if parts[0].isdigit() and len(parts[0]) == 4:
                            existing_indices.append(int(parts[0]))
        next_idx = max(existing_indices) + 1 if existing_indices else 1
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "_shorts" if is_vertical else ""
        folder_name = f"{next_idx:04d}_{channel_id}_{ts}{suffix}"
        work_dir = channel_yuklenecek / folder_name
        work_dir.mkdir(parents=True, exist_ok=True)

        def progress_cb(pct: int, msg: str):
            executions[exec_id]["message"] = f"[{pct}%] {msg}"
            executions[exec_id]["progress"] = pct

        result = generate_connectome_clip(
            output_folder=work_dir,
            duration_sec=duration,
            genre=genre,
            theme=theme,
            is_vertical=is_vertical,
            language=lang,
            scale_override=scale,
            bpm_override=bpm,
            progress_callback=progress_cb
        )

        executions[exec_id]["status"] = "success"
        executions[exec_id]["message"] = f"Klip üretimi tamamlandı: {result.get('title')}"
        executions[exec_id]["video_path"] = result.get("video_path")
        executions[exec_id]["folder"] = f"{channel_id}/yuklenecek/{folder_name}"
        executions[exec_id]["result"] = {
            "title": result.get("title"),
            "folder": f"{channel_id}/yuklenecek/{folder_name}",
            "video_path": result.get("video_path"),
            "language": lang
        }
        _clear_memory(trigger="connectome_clip_success")

    except Exception as e:
        _clear_memory(trigger="connectome_clip_error")
        import traceback
        traceback.print_exc()
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Üretim hatası: {str(e)}"


@app.get("/api/connectome/genres")
def get_connectome_genres():
    """Sinek Beyni Biyo-AI müzik türlerini listeler."""
    try:
        from connectome.synth import GENRES
    except ImportError:
        from src.connectome.synth import GENRES
    
    genres_list = []
    for gid, gdata in GENRES.items():
        genres_list.append({
            "id": gid,
            "name": gdata.get("name", gid),
            "bpm": gdata.get("bpm", 90),
            "instruments": gdata.get("instruments", []),
            "scales": list(gdata.get("scales", {}).keys())
        })
    return {"success": True, "genres": genres_list}


@app.post("/api/channels/{channel_id}/produce-connectome")
def produce_connectome_video(
    channel_id: str,
    payload: ProduceConnectomePayload,
    background_tasks: BackgroundTasks
):
    mgr = ChannelManager()
    channel = mgr.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")

    exec_id = f"exec_{channel_id}_connectome_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    executions[exec_id] = {
        "channel_id": channel_id,
        "status": "pending",
        "message": "Sinek Beyni Biyo-AI müzik ve video üretimi sıraya alındı...",
        "timestamp": datetime.now().isoformat(),
    }

    background_tasks.add_task(
        run_connectome_production_task,
        channel_id=channel_id,
        exec_id=exec_id,
        genre=payload.genre,
        duration=payload.duration,
        theme=payload.theme,
        is_vertical=payload.is_vertical,
        scale=payload.scale,
        bpm=payload.bpm
    )

    return {
        "success": True,
        "exec_id": exec_id,
        "message": "Sinek Beyni Biyo-AI video üretimi arka planda başlatıldı."
    }


class GeminiProducePayload(BaseModel):
    script: dict
    images: Optional[dict] = None
    target_env: Optional[str] = "local"
    auto_youtube_upload: Optional[bool] = False
    auto_sync_mac: Optional[bool] = True


def run_remote_web_automation_task(
    channel_id: str,
    exec_id: str,
    row_id: str,
    custom_script: dict,
    custom_images: Optional[dict] = None,
    youtube_upload: bool = False,
    auto_sync_mac: bool = True
):
    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = "Oracle Cloud sunucusuna bağlanılıyor (132.226.187.103)..."

    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            raise RuntimeError("Oracle Cloud sunucusuna (132.226.187.103) SSH üzerinden ulaşılamadı.")

        mgr = ChannelManager()
        ch = mgr.get_channel(channel_id) or {"channel_id": channel_id}

        executions[exec_id]["message"] = "Senaryo ve görsel veriler sunucuya aktarılıyor..."
        runner.dispatch_job(
            job_id=exec_id,
            channel_id=channel_id,
            channel_config=ch,
            row_id=row_id,
            script_data=custom_script,
            custom_images=custom_images,
            youtube_upload=youtube_upload
        )

        executions[exec_id]["message"] = "Sunucuda video üretimi başlatıldı (nice 19)..."

        # Poll status
        max_wait = 900  # 15 dakika
        interval = 4
        elapsed = 0
        consecutive_poll_errors = 0

        while elapsed < max_wait:
            time.sleep(interval)
            elapsed += interval
            
            try:
                st = runner.get_job_status(exec_id)
                consecutive_poll_errors = 0
            except Exception as poll_e:
                consecutive_poll_errors += 1
                print(f"[RemoteRunner] Polling geçici hata ({consecutive_poll_errors}/10): {poll_e}")
                if consecutive_poll_errors >= 10:
                    raise poll_e
                continue

            srv_status = st.get("status")

            if srv_status == "running":
                executions[exec_id]["message"] = f"Sunucu: {st.get('message', 'Hazırlanıyor...')}"
            elif srv_status == "rendering":
                executions[exec_id]["message"] = f"Sunucu: Render ediliyor (%{st.get('progress', 30)})..."
            elif srv_status == "uploading":
                executions[exec_id]["message"] = "Sunucu: Video işleniyor..."
            elif srv_status == "completed":
                if auto_sync_mac:
                    executions[exec_id]["message"] = "Video sunucuda tamamlandı. Mac 'yuklenecek' klasörüne aktarılıyor..."

                    # Sunucudan Mac'e indir ve sunucudan sil (Auto Sync & Clean)
                    try:
                        dl_res = runner.download_and_cleanup_job(channel_id=channel_id, job_id=exec_id, delete_remote=True)
                        local_vid = dl_res.get("video_path")
                        executions[exec_id]["status"] = "success"
                        executions[exec_id]["message"] = f"Video başarıyla Mac 'yuklenecek' klasörüne indirildi ve sunucudan silindi ({dl_res.get('size_mb', 0)} MB)."
                        executions[exec_id]["result"] = dl_res

                        # İçerik planında durumu 'hazir' olarak güncelle
                        try:
                            from src.content_planner import ContentPlanner
                            planner = ContentPlanner(Path(_PROJECT_ROOT) / "output" / channel_id)
                            if row_id:
                                planner.mark_as_produced(row_id)
                            print(f"[REMOTE] Kanal #{channel_id} planı güncellendi (hazır): {local_vid}")
                        except Exception as plan_err:
                            print(f"[REMOTE] Plan güncelleme uyarısı: {plan_err}")
                    except Exception as dl_err:
                        executions[exec_id]["status"] = "success"
                        executions[exec_id]["message"] = f"Video sunucuda üretildi fakat Mac'e aktarma uyarısı: {dl_err}"
                else:
                    executions[exec_id]["status"] = "success"
                    executions[exec_id]["message"] = "Video sunucuda başarıyla üretildi. Dilediğiniz zaman 'Sunucu Render' sayfasından veya eklentiden Mac'e indirebilirsiniz."
                return
            elif srv_status == "failed":
                executions[exec_id]["status"] = "failed"
                executions[exec_id]["message"] = f"Sunucu hatası: {st.get('message')}"
                return

        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = "Sunucu işlem süresi zaman aşımına uğradı (15 dk)."

    except Exception as e:
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Uzak Sunucu Hatası: {str(e)}"


def run_gemini_web_automation_task(
    channel_id: str,
    exec_id: str,
    row_id: str,
    custom_script: dict,
    custom_images: Optional[dict] = None
):
    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = "Başlatılıyor..."

    try:
        mgr = ChannelManager()
        ch = mgr.get_channel(channel_id)
        if not ch:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = "Kanal bulunamadı."
            return

        provider      = settings_mgr.get("ai_provider", "claude")
        ai_model      = settings_mgr.get("ai_model", "")
        nasa_key      = settings_mgr.get("nasa_api_key", "DEMO_KEY")
        output_dir    = settings_mgr.get("output_dir", "output")
        ollama_url    = settings_mgr.get("ollama_url", "http://localhost:11434")
        lmstudio_url  = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")

        # In this mode, we don't call the ScriptWriter API directly because the script is already supplied!
        # But we still initialize ScriptWriter to keep run_channel signature happy.
        writer = ScriptWriter(
            provider=provider,
            api_key="",
            model=ai_model,
            ollama_url=ollama_url,
            lmstudio_url=lmstudio_url,
        )
        generator = VideoGenerator(nasa_api_key=nasa_key)
        edit_options = mgr.get_resolved_edit_options(channel_id)

        executions[exec_id]["message"] = "Video editöründen video dosyası üretiliyor..."

        # Call run_channel with custom_script and custom_images
        result = run_channel(
            channel_config=ch,
            writer=writer,
            generator=generator,
            manager=mgr,
            output_dir=output_dir,
            shorts_mode=ch.get("shorts_mode", False),
            transition=ch.get("transition", "fade"),
            edit_options=edit_options,
            force_row_id=row_id,
            custom_script=custom_script,
            custom_images=custom_images,
        )

        # Log kaydet
        log_path = Path(output_dir) / f"run_gemini_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_path.parent.mkdir(exist_ok=True)
        log_path.write_text(json.dumps([result], ensure_ascii=False, indent=2))

        if not result["success"]:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = f"Video üretimi Hata: {result.get('error')}"
            _clear_memory(trigger="gemini_web_render_failed")
            return

        executions[exec_id]["status"] = "success"
        executions[exec_id]["message"] = "Başarıyla tamamlandı. Video üretildi."
        executions[exec_id]["result"] = result

        # Otomatik YouTube yükleme ve akıllı zamanlama başlat
        try:
            from browser_uploader import execute_channel_upload_and_mark
            upload_res = execute_channel_upload_and_mark(channel_id, row_id, output_base_dir=output_dir)
            result["upload_result"] = upload_res
            executions[exec_id]["upload_result"] = upload_res
            print(f"[AUTO-UPLOAD] {channel_id} #{row_id} başarıyla YouTube için hazırlandı ve planlandı: {upload_res.get('slot', {}).get('display_summary')}")
        except Exception as upload_err:
            print(f"[AUTO-UPLOAD] Otomatik yükleme hazırlık uyarısı: {upload_err}")

        _clear_memory(trigger="gemini_web_render_success")
    except Exception as e:
        _clear_memory(trigger="gemini_web_render_error")
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Sistem Hatası: {str(e)}"


@app.post("/api/channels/{channel_id}/plan/{row_id}/produce-gemini")
def produce_planned_video_gemini(
    channel_id: str,
    row_id: str,
    payload: GeminiProducePayload,
    background_tasks: BackgroundTasks
):
    mgr = ChannelManager()
    if not mgr.get_channel(channel_id):
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    exec_id = f"exec_{channel_id}_gemini_{row_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    target_env = (payload.target_env or "local").lower()
    auto_yt = bool(payload.auto_youtube_upload)
    auto_sync = bool(payload.auto_sync_mac if payload.auto_sync_mac is not None else True)

    executions[exec_id] = {
        "channel_id": channel_id,
        "status": "pending",
        "message": f"{'Oracle Cloud sunucusunda (nice 19)' if target_env == 'remote' else 'Lokal'} video üretiliyor...",
        "timestamp": datetime.now().isoformat(),
        "target_env": target_env,
        "auto_youtube_upload": auto_yt,
        "auto_sync_mac": auto_sync
    }
    
    if target_env == "remote":
        background_tasks.add_task(
            run_remote_web_automation_task,
            channel_id,
            exec_id,
            row_id,
            payload.script,
            payload.images,
            auto_yt,
            auto_sync
        )
    else:
        background_tasks.add_task(
            run_gemini_web_automation_task, 
            channel_id, 
            exec_id, 
            row_id, 
            payload.script, 
            payload.images
        )
    return {"exec_id": exec_id, "status": "pending", "target_env": target_env}



# ═══════════════════════════════════════════════════════════════
# GRUP İÇERİK PLANI & ÇOK DİLLİ GEMINI ÜRETİMİ
# ═══════════════════════════════════════════════════════════════

def run_gemini_group_web_automation_task(
    group_id: str,
    exec_id: str,
    row_id: str,
    payload_script: dict | list,
    custom_images: Optional[dict] = None,
    target_env: str = "local",
    auto_youtube_upload: bool = False,
    auto_sync_mac: bool = True
):
    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = f"Grup video üretimi başlatılıyor ({'Oracle Cloud sunucusunda' if target_env == 'remote' else 'lokalde'})..."

    try:
        mgr = ChannelManager()
        group = mgr.get_group(group_id)
        if not group:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = "Grup bulunamadı."
            return

        member_cids = group.get("channel_ids", [])
        if not member_cids:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = "Grupta kanal bulunamadı."
            return

        provider = settings_mgr.get("ai_provider", "claude")
        ai_model = settings_mgr.get("ai_model", "")
        nasa_key = settings_mgr.get("nasa_api_key", "DEMO_KEY")
        output_dir = settings_mgr.get("output_dir", "output")
        ollama_url = settings_mgr.get("ollama_url", "http://localhost:11434")
        lmstudio_url = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")

        writer = ScriptWriter(
            provider=provider,
            api_key="",
            model=ai_model,
            ollama_url=ollama_url,
            lmstudio_url=lmstudio_url,
        )
        generator = VideoGenerator(nasa_api_key=nasa_key)

        channel_results = []
        
        # Çok dilli senaryo ayrıştırması
        multi_scripts = {}
        if isinstance(payload_script, dict):
            has_lang_keys = any(k in payload_script for k in ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko"])
            if has_lang_keys:
                multi_scripts = payload_script
            elif "scripts" in payload_script and isinstance(payload_script["scripts"], dict):
                multi_scripts = payload_script["scripts"]
            else:
                main_lang = payload_script.get("language", "tr")
                multi_scripts[main_lang] = payload_script
        elif isinstance(payload_script, list):
            for sc in payload_script:
                if isinstance(sc, dict) and "language" in sc:
                    multi_scripts[sc["language"]] = sc

        for idx, cid in enumerate(member_cids):
            ch = mgr.get_channel(cid)
            if not ch:
                continue
            lang = ch.get("language", "en")
            executions[exec_id]["message"] = f"[{idx+1}/{len(member_cids)}] '{ch['name']}' ({lang.upper()}) kanalı için video üretiliyor ({'Oracle Cloud sunucusunda' if target_env == 'remote' else 'lokalde'})..."

            # Bu kanal için uygun dildeki senaryoyu bul veya otomatik yerelleştir
            ch_script = multi_scripts.get(lang)
            if not ch_script:
                base_s = next(iter(multi_scripts.values())) if multi_scripts else payload_script
                try:
                    try:
                        from src.localization_helper import ensure_localized_script
                    except ImportError:
                        from localization_helper import ensure_localized_script
                    ch_script = ensure_localized_script(base_s, lang)
                except Exception as e_loc:
                    print(f"[GroupAutomation] Yerelleştirme hatası: {e_loc}")
                    ch_script = base_s

            if target_env == "remote":
                sub_ch_exec_id = f"{exec_id}_{cid}"
                executions[sub_ch_exec_id] = {
                    "status": "running",
                    "message": f"'{ch['name']}' ({lang.upper()}) Oracle Cloud sunucusunda üretiliyor...",
                    "channel_id": cid,
                    "title": f"[{group.get('name')}] {ch['name']} ({lang.upper()}) - #{row_id}",
                    "target_env": "remote",
                    "timestamp": datetime.now().isoformat()
                }
                run_remote_web_automation_task(
                    channel_id=cid,
                    exec_id=sub_ch_exec_id,
                    row_id=row_id,
                    custom_script=ch_script,
                    custom_images=custom_images,
                    youtube_upload=auto_youtube_upload,
                    auto_sync_mac=auto_sync_mac
                )
                res_sub = executions.get(sub_ch_exec_id, {})
                channel_results.append({
                    "channel_id": cid,
                    "success": res_sub.get("status") == "success",
                    "result": res_sub.get("result"),
                    "error": res_sub.get("message") if res_sub.get("status") != "success" else None
                })
            else:
                edit_options = mgr.get_resolved_edit_options(cid)

                # run_channel çağır (videoyu doğrudan output/<cid>/yuklenecek/ altına kaydeder)
                res = run_channel(
                    channel_config=ch,
                    writer=writer,
                    generator=generator,
                    manager=mgr,
                    output_dir=output_dir,
                    shorts_mode=ch.get("shorts_mode", True),
                    transition=ch.get("transition", "none" if group.get("topic_category") == "reddit_stories" else "fade"),
                    edit_options=edit_options,
                    force_row_id="no_plan",
                    custom_script=ch_script,
                    custom_images=custom_images,
                    explicit_plan_id=row_id,
                )
                channel_results.append(res)
            _clear_memory(trigger=f"gemini_group_channel_{cid}")

        success_results = [r for r in channel_results if r.get("success")]
        failed_results = [r for r in channel_results if not r.get("success")]
        
        if len(failed_results) == 0:
            executions[exec_id]["status"] = "success"
            executions[exec_id]["message"] = f"Grup video üretimi başarıyla tamamlandı. {len(channel_results)} kanal için videolar üretildi."
            # Grup içerik planındaki satırı üretildi olarak işaretle
            grp_dir = Path(output_dir) / "groups" / group_id
            grp_planner = ContentPlanner(grp_dir)
            if grp_planner.plan_exists() and row_id:
                grp_planner.mark_as_produced(row_id)
        elif len(success_results) > 0:
            executions[exec_id]["status"] = "partial"
            failed_msgs = "; ".join(f"{r['channel_id']}: {r.get('error')}" for r in failed_results)
            executions[exec_id]["message"] = f"Grup video üretimi kısmen tamamlandı ({len(success_results)}/{len(channel_results)} kanal başarılı). Hatalar: {failed_msgs}"
        else:
            executions[exec_id]["status"] = "failed"
            failed_msgs = "; ".join(f"{r['channel_id']}: {r.get('error')}" for r in failed_results)
            executions[exec_id]["message"] = f"Grup video üretimi başarısız oldu: {failed_msgs}"

        executions[exec_id]["result"] = {
            "group_id": group_id,
            "channel_results": channel_results
        }
        
        # Log kaydet
        try:
            log_path = Path(output_dir) / f"run_gemini_group_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            log_path.parent.mkdir(exist_ok=True)
            log_path.write_text(json.dumps(channel_results, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"[LOG ERROR] {e}")

        # Gruptaki tüm kanallar için otomatik YouTube yükleme ve akıllı zamanlama başlat
        try:
            from browser_uploader import execute_group_upload_and_mark
            grp_upload_res = execute_group_upload_and_mark(group_id, row_id, output_base_dir=output_dir)
            executions[exec_id]["group_upload_result"] = grp_upload_res
            print(f"[AUTO-UPLOAD] Grup '{group_id}' #{row_id} tüm üye kanallar için YouTube'a planlandı.")
        except Exception as grp_upload_err:
            print(f"[AUTO-UPLOAD] Grup otomatik yükleme hazırlık uyarısı: {grp_upload_err}")

        _clear_memory(trigger="gemini_group_task_complete")
    except Exception as e:
        _clear_memory(trigger="gemini_group_task_error")
        import traceback
        traceback.print_exc()
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Grup Üretim Hatası: {str(e)}"


# ═══════════════════════════════════════════════════════════════
# GEMINI ÇOKLU VİDEO SIRALI ÜRETİM & DİSK STAGING MOTORU
# ═══════════════════════════════════════════════════════════════

class GeminiBatchItem(BaseModel):
    is_group: bool = False
    channel_id: Optional[str] = None
    group_id: Optional[str] = None
    target_id: Optional[str] = None
    row_id: str
    script: dict | list
    images: Optional[dict] = None
    title: Optional[str] = ""
    target_env: Optional[str] = "local"
    auto_youtube_upload: Optional[bool] = False
    auto_sync_mac: Optional[bool] = True

class GeminiBatchPayload(BaseModel):
    items: List[GeminiBatchItem]
    target_env: Optional[str] = "local"
    auto_youtube_upload: Optional[bool] = False
    auto_sync_mac: Optional[bool] = True


def run_gemini_sequential_batch_task(exec_id: str, items: List[dict]):
    """
    Gemini eklentisinden gelen birden fazla video paketini TEK TEK SIRAYLA (sequential) üretir.
    Böylece bilgisayar aynı anda birden fazla video render ile kilitlenmez,
    her video sırayla bitirilir ve ilerleme anlık raporlanır.
    """
    total = len(items)
    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = f"Toplu üretim başlatılıyor (0/{total})..."
    executions[exec_id]["total"] = total
    executions[exec_id]["completed"] = 0
    executions[exec_id]["results"] = []

    success_count = 0
    staging_dir = _PROJECT_ROOT / "scratch" / "gemini_staging"

    for idx, item in enumerate(items):
        item_num = idx + 1
        is_group = bool(item.get("is_group", False))
        target_id = item.get("target_id") or item.get("channel_id") or item.get("group_id")
        row_id = str(item.get("row_id", ""))
        custom_script = item.get("script") or {}
        custom_images = item.get("images") or {}
        video_title = item.get("title") or (custom_script.get("title") if isinstance(custom_script, dict) else f"Video #{row_id}")

        executions[exec_id]["message"] = f"Video {item_num}/{total} üretiliyor: '{video_title}'..."
        executions[exec_id]["current_index"] = idx

        try:
            sub_exec_id = f"{exec_id}_item_{item_num}"
            target_env = (item.get("target_env") or "local").lower()
            auto_yt = bool(item.get("auto_youtube_upload", False))
            auto_sync = bool(item.get("auto_sync_mac", True))

            if is_group:
                executions[sub_exec_id] = {
                    "status": "running",
                    "message": f"Grup video {item_num}/{total} ({'Oracle Cloud sunucusunda' if target_env == 'remote' else 'lokalde'}) hazırlanıyor..."
                }
                run_gemini_group_web_automation_task(
                    group_id=target_id,
                    exec_id=sub_exec_id,
                    row_id=row_id,
                    payload_script=custom_script,
                    custom_images=custom_images,
                    target_env=target_env,
                    auto_youtube_upload=auto_yt,
                    auto_sync_mac=auto_sync
                )
            else:
                if target_env == "remote":
                    executions[sub_exec_id] = {"status": "running", "message": f"Kanal videosu {item_num}/{total} Oracle Cloud sunucusunda üretiliyor..."}
                    run_remote_web_automation_task(
                        channel_id=target_id,
                        exec_id=sub_exec_id,
                        row_id=row_id,
                        custom_script=custom_script,
                        custom_images=custom_images,
                        youtube_upload=auto_yt,
                        auto_sync_mac=auto_sync
                    )
                else:
                    executions[sub_exec_id] = {"status": "running", "message": f"Kanal videosu {item_num}/{total} üretiliyor..."}
                    run_gemini_web_automation_task(
                        channel_id=target_id,
                        exec_id=sub_exec_id,
                        row_id=row_id,
                        custom_script=custom_script,
                        custom_images=custom_images
                    )

            sub_res = executions.get(sub_exec_id, {})
            if sub_res.get("status") == "success":
                success_count += 1
                if sub_res.get("result"):
                    executions[exec_id]["results"].append(sub_res["result"])
            else:
                print(f"[BATCH-GEMINI] Video {item_num} uyarısı: {sub_res.get('message')}")

            executions[exec_id]["completed"] = item_num

            # Staged dosyasını diskten temizle
            try:
                staged_file = staging_dir / f"staged_item_{row_id}.json"
                if staged_file.exists():
                    staged_file.unlink()
            except Exception:
                pass

        except Exception as e:
            print(f"[BATCH-GEMINI] Video {item_num} hatası: {e}")

        # Her batch öğesi sonrasında bellek ve GPU temizliği
        _clear_memory(trigger=f"gemini_batch_item_{item_num}")

    if success_count > 0:
        executions[exec_id]["status"] = "success"
        executions[exec_id]["message"] = f"Toplu üretim tamamlandı! Toplam {success_count}/{total} video başarıyla üretildi."
        if executions[exec_id]["results"]:
            executions[exec_id]["result"] = executions[exec_id]["results"][-1]
    else:
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Toplu üretim başarısız oldu (0/{total} video üretilebildi)."

    _clear_memory(trigger="gemini_batch_all_finished")


@app.post("/api/staging/gemini-item")
def stage_gemini_item(payload: dict = Body(...)):
    """Gemini'da üretilen senaryo ve görselleri diskte güvenle saklar (veri kaybını önler)."""
    staging_dir = _PROJECT_ROOT / "scratch" / "gemini_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    row_id = str(payload.get("row_id") or int(time.time()))
    file_path = staging_dir / f"staged_item_{row_id}.json"
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "saved_file": str(file_path), "row_id": row_id}


@app.get("/api/staging/gemini-items")
def list_staged_gemini_items():
    """Diskte bekleyen staged video paketlerini listeler."""
    staging_dir = _PROJECT_ROOT / "scratch" / "gemini_staging"
    if not staging_dir.exists():
        return {"items": []}
    items = []
    for f in staging_dir.glob("staged_item_*.json"):
        try:
            items.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return {"items": items}


@app.delete("/api/staging/gemini-items")
def clear_staged_gemini_items():
    """Staged dosyaları temizler."""
    staging_dir = _PROJECT_ROOT / "scratch" / "gemini_staging"
    if staging_dir.exists():
        for f in staging_dir.glob("staged_item_*.json"):
            try:
                f.unlink()
            except Exception:
                pass
# ═══════════════════════════════════════════════════════════════
# ÜRETİM METARYALLERİ YÖNETİMİ & KUYRUK ÜRETİM MOTORU
# ═══════════════════════════════════════════════════════════════

from materials_manager import MaterialsManager

class MaterialProduceSinglePayload(BaseModel):
    target_env: Optional[str] = "local"
    remote: Optional[bool] = False
    auto_youtube_upload: Optional[bool] = False
    auto_sync_mac: Optional[bool] = True

class MaterialBatchProducePayload(BaseModel):
    material_keys: Optional[List[Dict[str, str]]] = None
    materials: Optional[List[Dict[str, str]]] = None
    target_env: Optional[str] = "local"
    remote: Optional[bool] = False
    auto_youtube_upload: Optional[bool] = False
    auto_sync_mac: Optional[bool] = True

class PlanAndMaterialItem(BaseModel):
    baslik: str
    konu: Optional[str] = ""
    yonergeler: Optional[str] = ""
    script: Optional[dict] = None
    images: Optional[dict] = None
    notes: Optional[str] = ""

class PlanAndMaterialsPayload(BaseModel):
    topics: Optional[List[Any]] = []
    materials: Optional[List[Any]] = []


def run_material_produce_single_task(
    channel_id: str,
    material_id: str,
    exec_id: str,
    target_env: str = "local",
    auto_youtube_upload: bool = False,
    auto_sync_mac: bool = True
):
    mat_mgr = MaterialsManager()
    mat = mat_mgr.get_material(channel_id, material_id)
    if not mat:
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Materyal bulunamadı ({material_id})."
        return

    is_group, clean_id, _ = mat_mgr._resolve_target(channel_id)
    mat_mgr.update_material_status(channel_id, material_id, "producing")
    row_id = mat.get("row_id") or material_id
    custom_script = mat.get("script") or {}
    custom_images = mat.get("images") or {}

    try:
        if is_group:
            executions[exec_id]["status"] = "running"
            executions[exec_id]["message"] = f"Grup video üretimi {'Oracle Cloud sunucusunda' if target_env == 'remote' else 'lokalde'} başlatılıyor..."
            run_gemini_group_web_automation_task(
                group_id=clean_id,
                exec_id=exec_id,
                row_id=row_id,
                payload_script=custom_script,
                custom_images=custom_images,
                target_env=target_env,
                auto_youtube_upload=auto_youtube_upload,
                auto_sync_mac=auto_sync_mac
            )
        elif target_env == "remote":
            executions[exec_id]["status"] = "running"
            executions[exec_id]["message"] = f"Video Oracle Cloud sunucusunda üretiliyor..."
            run_remote_web_automation_task(
                channel_id=clean_id,
                exec_id=exec_id,
                row_id=row_id,
                custom_script=custom_script,
                custom_images=custom_images,
                youtube_upload=auto_youtube_upload,
                auto_sync_mac=auto_sync_mac
            )
        else:
            executions[exec_id]["status"] = "running"
            executions[exec_id]["message"] = f"Video lokal arka uç ile üretiliyor..."
            run_gemini_web_automation_task(
                channel_id=clean_id,
                exec_id=exec_id,
                row_id=row_id,
                custom_script=custom_script,
                custom_images=custom_images
            )

        status = executions.get(exec_id, {}).get("status")
        if status in ("success", "partial"):
            mat_mgr.update_material_status(channel_id, material_id, "produced")
        else:
            mat_mgr.update_material_status(channel_id, material_id, "ready")
    except Exception as e:
        mat_mgr.update_material_status(channel_id, material_id, "ready")
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Üretim hatası: {str(e)}"


@app.get("/api/materials")
def get_all_materials(channel_id: Optional[str] = Query(None)):
    """Tüm kanalların veya belirli bir kanalın Üretim Metaryalleri paketlerini listeler."""
    mgr = MaterialsManager()
    items = mgr.list_materials(channel_id=channel_id)
    from material_status_sync import sync_materials_with_generated_videos
    sync_materials_with_generated_videos(mgr, items)
    return {"success": True, "count": len(items), "materials": items}


@app.get("/api/materials/{channel_id}/{material_id}")
def get_single_material(channel_id: str, material_id: str):
    """Belirli bir materyal paketinin tüm detaylarını (senaryo, görseller vb.) döndürür."""
    mgr = MaterialsManager()
    item = mgr.get_material(channel_id, material_id)
    if not item:
        raise HTTPException(status_code=404, detail="Materyal bulunamadı.")
    return {"success": True, "material": item}


@app.post("/api/materials")
def save_custom_material(payload: dict = Body(...)):
    """Doğrudan yeni bir materyal paketi kaydeder."""
    ch_id = payload.get("channel_id")
    if not ch_id:
        raise HTTPException(status_code=400, detail="channel_id gereklidir.")
    mgr = MaterialsManager()
    saved = mgr.save_material(
        channel_id=ch_id,
        script=payload.get("script") or {},
        title=payload.get("title"),
        topic=payload.get("topic") or payload.get("konu"),
        row_id=payload.get("row_id"),
        images=payload.get("images"),
        target_env=payload.get("target_env", "local"),
        notes=payload.get("notes", "")
    )
    return {"success": True, "material": saved}


@app.delete("/api/materials/{channel_id}/{material_id}")
def delete_single_material(channel_id: str, material_id: str):
    """Materyali 'Üretim Metaryalleri' klasöründen siler."""
    mgr = MaterialsManager()
    ok = mgr.delete_material(channel_id, material_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Materyal bulunamadı veya silinemedi.")
    return {"success": True, "message": "Materyal başarıyla silindi."}


@app.post("/api/materials/{channel_id}/{material_id}/research")
def research_single_material_endpoint(
    channel_id: str,
    material_id: str,
    force: bool = Query(False)
):
    """
    Belirli bir materyal için Akıllı Araştırma Motorunu çalıştırır.
    Tarihi arşivleri (Wikimedia), 1080p B-roll (Pixabay) ve telemetri infografiklerini
    araştırır, sahnelerle doğrular ve material.json'ı günceller.
    """
    from aviation_research_engine import AviationResearchEngine
    engine = AviationResearchEngine()
    result = engine.research_material(channel_id=channel_id, material_id=material_id, force=force)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Araştırma başarısız oldu."))
    return result


@app.post("/api/materials/{channel_id}/research-all")
def research_all_materials_endpoint(
    channel_id: str,
    force: bool = Query(False),
    limit: Optional[int] = Query(None)
):
    """
    Kanalın bekleyen tüm üretilmemiş materyalleri için toplu araştırma motorunu çalıştırır.
    """
    from aviation_research_engine import AviationResearchEngine
    engine = AviationResearchEngine()
    results = engine.research_all_unproduced(channel_id=channel_id, force=force, max_count=limit)
    return {
        "success": True,
        "channel_id": channel_id,
        "processed_count": len(results),
        "results": results
    }


@app.post("/api/groups/{group_id}/plan-and-materials")
def import_group_plan_and_materials(group_id: str, payload: PlanAndMaterialsPayload):
    """
    Gemini Eklentisinden gelen konuları ve üretilmiş senaryoları grup için
    hem groups/{group_id}/icerik_plani.csv'ye ekler hem de grubun 'Üretim Metaryalleri' klasörüne kaydeder.
    """
    return import_plan_and_materials(channel_id=f"group:{group_id}", payload=payload)


@app.post("/api/channels/{channel_id}/plan-and-materials")
def import_plan_and_materials(channel_id: str, payload: PlanAndMaterialsPayload):
    """
    Gemini Eklentisinden gelen konuları ve üretilmiş senaryoları tek seferde hem
    icerik_plani.csv'ye ekler hem de 'Üretim Metaryalleri' klasörüne kaydeder.
    Kanal gruplarını (group:<id>) ve normal kanalları destekler.
    """
    output_dir = settings_mgr.get("output_dir", "output")
    mat_mgr = MaterialsManager(output_dir)
    is_group, clean_id, target_dir = mat_mgr._resolve_target(channel_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    planner = ContentPlanner(target_dir)
    
    saved_list = []
    
    raw_items = payload.topics or payload.materials or []
    for item in raw_items:
        if isinstance(item, str):
            topic_title = item.strip()
            topic_subject = topic_title
            item_script = None
            item_images = None
            item_notes = ""
        elif isinstance(item, dict):
            topic_title = (item.get("baslik") or item.get("title") or item.get("konu") or "").strip()
            topic_subject = (item.get("konu") or topic_title).strip()
            item_script = item.get("script")
            item_images = item.get("images")
            item_notes = item.get("yonergeler") or item.get("notes") or ""
            # Eğer doğrudan materyal formatında geldiyse:
            if not item_script and item.get("scenes"):
                item_script = item
        else:
            topic_title = getattr(item, "baslik", getattr(item, "title", "")).strip()
            topic_subject = (getattr(item, "konu", "") or topic_title).strip()
            item_script = getattr(item, "script", None)
            item_images = getattr(item, "images", None)
            item_notes = getattr(item, "yonergeler", "") or getattr(item, "notes", "") or ""
            if not item_script and getattr(item, "scenes", None):
                item_script = item.dict() if hasattr(item, "dict") else vars(item)

        if not topic_title:
            continue

        # 1. İçerik planına satır ekle
        topic_entry = {
            "konu": topic_subject,
            "baslik": topic_title,
            "notlar": item_notes
        }
        new_rows = planner.add_topics([topic_entry])
        assigned_row_id = new_rows[0]["id"] if new_rows else ""
        
        # 2. Eğer senaryo (script) mevcutsa VE gerçek sahneleri varsa materyal olarak kaydet
        has_real_scenes = False
        if item_script and isinstance(item_script, dict):
            if item_script.get("scenes") and len(item_script["scenes"]) > 0:
                has_real_scenes = True
            else:
                for lk in ("tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko"):
                    if lk in item_script and isinstance(item_script[lk], dict) and item_script[lk].get("scenes"):
                        has_real_scenes = True
                        break

        if has_real_scenes:
            target_cid = f"group:{clean_id}" if is_group else channel_id
            saved_mat = mat_mgr.save_material(
                channel_id=target_cid,
                script=item_script,
                title=topic_title,
                topic=topic_subject,
                row_id=assigned_row_id,
                images=item_images,
                notes=item_notes
            )
            saved_list.append(saved_mat)
        else:
            saved_list.append({"row_id": assigned_row_id, "title": topic_title})

    # Zihin haritasını da güncelle (yalnızca tekil kanal ise)
    if not is_group:
        try:
            from mind_map import MindMap
            mm = MindMap(target_dir)
            for s in saved_list:
                mm.add_node(s.get("title", ""), category="plan")
            mm.save()
        except Exception:
            pass

    return {
        "success": True,
        "count": len(saved_list),
        "materials_count": len([m for m in saved_list if "folder_path" in m]),
        "materials": saved_list,
        "message": f"{len(saved_list)} adet içerik planı ve materyali başarıyla kaydedildi!"
    }


@app.get("/api/active-channels/pending-plan")
def get_active_channels_pending_plan(limit: Optional[int] = None):
    """Aktif kanalların ve grupların henüz videosu üretilmemiş ve materyali bulunmayan plan satırlarını döner."""
    mat_mgr = MaterialsManager()
    return mat_mgr.get_all_active_channels_pending_plans(limit_per_channel=limit)


@app.get("/api/groups/{group_id}/pending-plan")
def get_group_pending_plan(group_id: str, limit: Optional[int] = None):
    """Grup içerik planında henüz materyali hazırlanmamış satırları döner."""
    mat_mgr = MaterialsManager()
    rows = mat_mgr.get_pending_plan_rows(f"group:{group_id}", limit=limit)
    return {
        "success": True,
        "group_id": group_id,
        "channel_id": f"group:{group_id}",
        "pending_count": len(rows),
        "pending_rows": rows
    }


@app.get("/api/channels/{channel_id}/pending-plan")
def get_channel_pending_plan(channel_id: str, limit: Optional[int] = None):
    """Belirli bir kanalın veya grubun henüz materyali hazırlanmamış plan satırlarını döner."""
    mat_mgr = MaterialsManager()
    rows = mat_mgr.get_pending_plan_rows(channel_id, limit=limit)
    return {
        "success": True,
        "channel_id": channel_id,
        "pending_count": len(rows),
        "pending_rows": rows
    }


class ExistingPlanMaterialsPayload(BaseModel):
    materials: List[Dict[str, Any]]


@app.post("/api/groups/{group_id}/materials-for-existing-plan")
def save_group_materials_for_existing_plan(group_id: str, payload: ExistingPlanMaterialsPayload):
    """Grup için geçmişe dönük üretilen çok dilli materyalleri kaydeder."""
    return save_materials_for_existing_plan(channel_id=f"group:{group_id}", payload=payload)


@app.post("/api/channels/{channel_id}/materials-for-existing-plan")
def save_materials_for_existing_plan(channel_id: str, payload: ExistingPlanMaterialsPayload):
    """
    Geçmişe dönük olarak mevcut içerik planındaki satırlar için üretilen
    senaryo ve materyalleri kaydeder ve CSV'deki ilgili satır durumunu 'Materyaller Hazır' yapar.
    Kanal gruplarını da destekler (output/groups/<group_id>/ altına yazar).
    """
    output_dir = settings_mgr.get("output_dir", "output")
    mat_mgr = MaterialsManager(output_dir)
    is_group, clean_id, target_dir = mat_mgr._resolve_target(channel_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    saved_list = []
    
    for item in payload.materials:
        row_id = str(item.get("row_id") or item.get("id") or "").strip()
        title = item.get("baslik") or item.get("title") or item.get("konu") or ""
        topic = item.get("konu") or title
        script = item.get("script") or (item if item.get("scenes") else None)
        images = item.get("images")
        notes = item.get("yonergeler") or item.get("notes") or ""

        if not script or not isinstance(script, dict):
            continue

        # Eğer başlık jenerik veya boşsa, içerik planındaki gerçek satırdan otomatik kurtar
        if (not title or title == "Otomatik Üretilen Senaryo") and row_id:
            try:
                planner = ContentPlanner(target_dir)
                p_row = planner.get_row_by_id(row_id)
                if p_row:
                    title = p_row.get("baslik") or p_row.get("konu") or title
                    topic = p_row.get("konu") or title
                    if isinstance(script, dict) and script.get("title") in ("", "Otomatik Üretilen Senaryo"):
                        script["title"] = title
            except Exception:
                pass
            
        saved_mat = mat_mgr.save_material(
            channel_id=channel_id,
            script=script,
            title=title,
            topic=topic,
            row_id=row_id,
            images=images,
            notes=notes
        )
        saved_list.append(saved_mat)
        
    return {
        "success": True,
        "saved_count": len(saved_list),
        "materials": saved_list,
        "message": f"{len(saved_list)} adet mevcut plan konusu için üretim materyali kaydedildi!"
    }


@app.post("/api/materials/{channel_id}/{material_id}/produce")
def produce_single_material(
    channel_id: str,
    material_id: str,
    payload: MaterialProduceSinglePayload,
    background_tasks: BackgroundTasks
):
    """Sistem sayfasından tek bir materyalin videosunu üretmeyi başlatır."""
    mgr = MaterialsManager()
    mat = mgr.get_material(channel_id, material_id)
    if not mat:
        raise HTTPException(status_code=404, detail="Üretilecek materyal bulunamadı.")

    safe_chan_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(channel_id))
    exec_id = f"exec_mat_{safe_chan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    target_env = "remote" if (payload.remote or (payload.target_env or "").lower() == "remote") else "local"
    auto_yt = bool(payload.auto_youtube_upload)
    auto_sync = bool(payload.auto_sync_mac)

    scenes = mat.get("scenes") or (mat.get("script") or {}).get("scenes") or []
    if not scenes and isinstance(mat.get("script"), dict):
        for lk in ("tr", "en", "es", "de"):
            if lk in mat["script"] and isinstance(mat["script"][lk], dict) and mat["script"][lk].get("scenes"):
                scenes = mat["script"][lk]["scenes"]
                break
    if not scenes:
        raise HTTPException(status_code=400, detail="Bu materyalin senaryo sahneleri boş. Lütfen geçerli bir senaryo oluşturun.")

    executions[exec_id] = {
        "status": "pending",
        "message": f"'{mat.get('title')}' videosu {'Oracle Cloud sunucusunda' if target_env == 'remote' else 'lokalde'} üretime hazırlanıyor...",
        "timestamp": datetime.now().isoformat(),
        "channel_id": channel_id,
        "material_id": material_id,
        "title": mat.get("title") or material_id,
        "target_env": target_env
    }

    background_tasks.add_task(
        run_material_produce_single_task,
        channel_id=channel_id,
        material_id=material_id,
        exec_id=exec_id,
        target_env=target_env,
        auto_youtube_upload=auto_yt,
        auto_sync_mac=auto_sync
    )

    return {
        "success": True,
        "exec_id": exec_id,
        "channel_id": channel_id,
        "material_id": material_id,
        "message": f"'{mat.get('title')}' video üretimi arka planda başlatıldı."
    }


@app.post("/api/materials/batch-produce")
def produce_batch_materials(
    payload: MaterialBatchProducePayload,
    background_tasks: BackgroundTasks
):
    """Sistem sayfasından seçilen materyalleri sırayla (kuyrukta) üretir."""
    keys = payload.material_keys or payload.materials or []
    if not keys:
        raise HTTPException(status_code=400, detail="Kuyruğa eklenecek materyal seçilmedi.")

    mgr = MaterialsManager()
    raw_items = []
    target_env = "remote" if (payload.remote or (payload.target_env or "").lower() == "remote") else "local"
    auto_yt = bool(payload.auto_youtube_upload)
    auto_sync = bool(payload.auto_sync_mac)

    for k in keys:
        ch_id = k.get("channel_id")
        m_id = k.get("material_id") or k.get("id")
        if not ch_id or not m_id:
            continue
        mat = mgr.get_material(ch_id, m_id)
        if not mat:
            continue
        is_grp, clean_id, _ = mgr._resolve_target(ch_id)
        raw_items.append({
            "is_group": is_grp,
            "channel_id": None if is_grp else clean_id,
            "group_id": clean_id if is_grp else None,
            "target_id": clean_id,
            "row_id": str(mat.get("row_id") or m_id),
            "script": mat.get("script") or {},
            "images": mat.get("images") or {},
            "title": mat.get("title") or mat.get("topic") or "Video",
            "target_env": target_env,
            "auto_youtube_upload": auto_yt,
            "auto_sync_mac": auto_sync
        })

    if not raw_items:
        raise HTTPException(status_code=400, detail="Geçerli materyal bulunamadı.")

    exec_id = f"exec_batch_mats_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    total = len(raw_items)
    executions[exec_id] = {
        "status": "pending",
        "message": f"{total} adet materyal sırayla üretilmek üzere kuyruğa alındı...",
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "completed": 0,
        "results": []
    }

    background_tasks.add_task(run_gemini_sequential_batch_task, exec_id, raw_items)

    return {
        "success": True,
        "exec_id": exec_id,
        "count": total,
        "message": f"{total} adet materyal kuyrukta sırayla üretilmek üzere başlatıldı!"
    }


# ═══════════════════════════════════════════════════════════════
# OTOMASYON (AUTONOMOUS CLOUD QUEUE) ENDPOINT'LERİ
# ═══════════════════════════════════════════════════════════════

class AutomationDispatchPayload(BaseModel):
    material_keys: List[Dict[str, str]]
    youtube_upload: Optional[bool] = False

class AutomationDownloadPayload(BaseModel):
    channel_id: str
    job_id: str
    delete_remote: Optional[bool] = False

class AutomationDeleteServerPayload(BaseModel):
    channel_id: str
    job_id: str

class AutomationRegenerateServerPayload(BaseModel):
    channel_id: str
    job_id: str


@app.get("/api/automation/unproduced-plans")
def get_automation_unproduced_plans():
    """
    Üretim materyalleri hazır olan ve henüz üretilmemiş (veya bulut kuyruğunda bekleyen)
    tüm planları ve materyalleri listeler.
    """
    mgr = MaterialsManager()
    all_mats = mgr.list_materials()
    from material_status_sync import sync_materials_with_generated_videos
    sync_materials_with_generated_videos(mgr, all_mats)
    unproduced = []
    for m in all_mats:
        st = m.get("status", "ready")

        if st in ("ready", "in_cloud_queue", "producing"):
            scenes_val = m.get("script", {}).get("scenes", [])
            s_count = m.get("scene_count") or (len(scenes_val) if isinstance(scenes_val, list) else 0)
            images_dict = m.get("images") or {}
            unproduced.append({
                "id": m.get("id"),
                "material_id": m.get("material_id") or m.get("id"),
                "channel_id": m.get("channel_id"),
                "channel_name": m.get("channel_name") or m.get("channel_id"),
                "channel_category": m.get("channel_category", "general"),
                "row_id": m.get("row_id", ""),
                "title": m.get("title") or m.get("topic") or "Başlıksız Plan",
                "topic": m.get("topic", ""),
                "status": st,
                "scene_count": s_count,
                "has_images": bool(images_dict),
                "images_count": len(images_dict),
                "created_at": m.get("created_at"),
                "folder_path": m.get("folder_path")
            })
    return {
        "success": True,
        "count": len(unproduced),
        "plans": unproduced
    }


@app.post("/api/automation/dispatch-queue")
def dispatch_automation_queue(payload: AutomationDispatchPayload):
    """
    Seçilen planları ve tüm materyallerini (senaryo, görseller, ayarlar)
    Oracle Cloud kuyruğuna aktarır, sunucu üzerinde varlıklarını doğrular ve
    bağımsız çalışan kuyruk sürecini (queue_runner.py) tetikler.
    """
    keys = payload.material_keys
    if not keys:
        raise HTTPException(status_code=400, detail="Üretime gönderilecek plan seçilmedi.")

    mgr = MaterialsManager()
    selected_items = []
    for k in keys:
        ch_id = k.get("channel_id")
        m_id = k.get("material_id") or k.get("id")
        if not ch_id or not m_id:
            continue
        mat = mgr.get_material(ch_id, m_id)
        if mat:
            mat["youtube_upload"] = payload.youtube_upload
            selected_items.append(mat)

    if not selected_items:
        raise HTTPException(status_code=404, detail="Seçilen materyaller diskte bulunamadı.")

    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            raise RuntimeError("Oracle Cloud sunucusuna (132.226.187.103) SSH üzerinden ulaşılamadı.")

        dispatch_result = runner.dispatch_batch_to_cloud_queue(selected_items)

        # Başarıyla kuyruğa aktarıldıysa lokal durumları "in_cloud_queue" yap
        for item in selected_items:
            ch_id = item.get("channel_id")
            m_id = item.get("material_id") or item.get("id")
            row_id = item.get("row_id")
            mgr.update_material_status(ch_id, m_id, "in_cloud_queue")
            if row_id:
                try:
                    planner = ContentPlanner(Path(mgr.output_dir) / ch_id)
                    planner.update_row_status(row_id, "Bulut Kuyruğunda")
                except Exception:
                    pass

        return dispatch_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kuyruk aktarım hatası: {str(e)}")


@app.get("/api/automation/queue-status")
def get_automation_queue_status():
    """Sunucudaki sıralı kuyruğun anlık durumunu döndürür."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            return {"connected": False, "is_running": False, "queue_count": 0, "jobs_count": 0}
        st = runner.get_queue_status()
        st["connected"] = True
        return st
    except Exception as e:
        return {"connected": False, "error": str(e), "is_running": False, "queue_count": 0}


@app.get("/api/automation/server-videos")
def get_automation_server_videos(channel_id: Optional[str] = Query(None)):
    """Sunucuda üretilmiş ve Mac'e indirilmeye hazır tüm videoları listeler."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            return {"connected": False, "videos": []}
        videos = runner.list_server_videos(channel_id)
        return {"connected": True, "videos": videos}
    except Exception as e:
        return {"connected": False, "error": str(e), "videos": []}


@app.post("/api/automation/download-video")
def download_automation_video(payload: AutomationDownloadPayload):
    """Sunucuda üretilen videoyu Mac'in ilgili kanal 'yuklenecek' klasörüne indirir."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        res = runner.download_and_cleanup_job(
            channel_id=payload.channel_id,
            job_id=payload.job_id,
            delete_remote=bool(payload.delete_remote)
        )

        # Materyal durumunu ve plan satırını güncelle (Bulut Kuyruğundan çıkart)
        try:
            mat_id = payload.job_id[5:] if payload.job_id.startswith("exec_") else payload.job_id
            mgr = MaterialsManager()
            mgr.update_material_status(payload.channel_id, mat_id, "downloaded")

            mat = mgr.get_material(payload.channel_id, mat_id)
            row_id = mat.get("row_id") if mat else None
            if row_id:
                planner = ContentPlanner(Path(mgr.output_dir) / payload.channel_id)
                planner.update_row_status(row_id, "Evet")
        except Exception as e_mat:
            print(f"[DOWNLOAD-SYNC] Materyal durum güncelleme uyarısı: {e_mat}")

        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video indirme hatası: {str(e)}")


@app.post("/api/automation/delete-server-video")
def delete_automation_server_video(payload: AutomationDeleteServerPayload):
    """Sunucudaki video klasörünü siler."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        ok = runner.delete_remote_job(payload.job_id, payload.channel_id)
        return {"success": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sunucudan silme hatası: {str(e)}")


@app.post("/api/automation/regenerate-server-video")
def regenerate_automation_server_video(payload: AutomationRegenerateServerPayload):
    """Sunucuda hazır olan tek bir videoyu güncel worker koduyla yeniden kuyruğa alır."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            raise HTTPException(status_code=503, detail="Oracle Cloud sunucusuna erişilemiyor.")
        result = runner.regenerate_server_video(payload.channel_id, payload.job_id)
        return {"success": True, **result}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except RuntimeError as error:
        message = str(error)
        status_code = 404 if "bulunamadı" in message.lower() else 500
        raise HTTPException(status_code=status_code, detail=message)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Video yeniden üretim hatası: {str(error)}")


@app.post("/api/produce-gemini-batch")
def produce_gemini_batch(
    payload: GeminiBatchPayload,
    background_tasks: BackgroundTasks
):
    """Gemini eklentisinden gelen toplu video paketlerini sırayla üretmek üzere kuyruğa alır."""
    if not payload.items:
        raise HTTPException(status_code=400, detail="Üretilecek video öğesi bulunamadı.")

    exec_id = f"exec_batch_gemini_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    total = len(payload.items)
    executions[exec_id] = {
        "status": "pending",
        "message": f"{total} adet video sırayla üretilmek üzere hazırlandı...",
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "completed": 0,
        "results": []
    }

    batch_env = (payload.target_env or "local").lower()
    raw_items = []
    for item in payload.items:
        d = item.dict()
        if not d.get("target_env") or d.get("target_env") == "local":
            if batch_env != "local":
                d["target_env"] = batch_env
        raw_items.append(d)
    background_tasks.add_task(run_gemini_sequential_batch_task, exec_id, raw_items)

    return {
        "success": True,
        "exec_id": exec_id,
        "status": "pending",
        "count": total,
        "message": f"{total} video sıralı üretim için başlatıldı."
    }


# ═══════════════════════════════════════════════════════════════
# UZAK ORACLE CLOUD SUNUCU YÖNETİMİ
# ═══════════════════════════════════════════════════════════════

@app.get("/api/remote/status")
def get_remote_server_status():
    """Oracle Cloud sunucusu bağlantı durumunu kontrol eder."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        reachable = runner.is_reachable()
        return {
            "success": True,
            "reachable": reachable,
            "host": runner.host,
            "user": runner.user,
            "remote_dir": runner.remote_dir,
            "message": "Oracle Cloud sunucusu aktif ve erişilebilir." if reachable else "Sunucuya ulaşılamıyor."
        }
    except Exception as e:
        return {"success": False, "reachable": False, "error": str(e)}


@app.post("/api/remote/sync-credentials")
def sync_remote_credentials():
    """Lokal YouTube API kimlik bilgilerini sunucuya kopyalar."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            raise HTTPException(status_code=503, detail="Oracle Cloud sunucusuna erişilemiyor.")
        ok = runner.sync_credentials()
        return {"success": ok, "message": "Kimlik bilgileri sunucuya başarıyla aktarıldı." if ok else "Kimlik bilgileri aktarılamadı."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/remote/videos")
def list_remote_videos():
    """Oracle Cloud sunucusunda hazır olan videoları listeler."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        videos = runner.list_server_videos()
        return {"success": True, "videos": videos}
    except Exception as e:
        return {"success": False, "error": str(e), "videos": []}


@app.post("/api/channels/{channel_id}/sync-from-server")
def sync_channel_videos_from_server(channel_id: str):
    """Kanal için sunucudaki tüm hazır videoları Mac 'yuklenecek' klasörüne indirir ve sunucudan siler."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            raise HTTPException(status_code=503, detail="Oracle Cloud sunucusuna bağlanılamadı.")
        downloaded = runner.download_all_pending_for_channel(channel_id)
        return {
            "success": True,
            "channel_id": channel_id,
            "count": len(downloaded),
            "downloaded": downloaded,
            "message": f"{len(downloaded)} adet video başarıyla Mac'e indirildi ve sunucudan silindi."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/channels/{channel_id}/sync-from-server/{job_id}")
def sync_single_video_from_server(channel_id: str, job_id: str):
    """Belirli bir görevin videosunu sunucudan Mac'e indirir ve sunucudan siler."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            raise HTTPException(status_code=503, detail="Oracle Cloud sunucusuna bağlanılamadı.")
        res = runner.download_and_cleanup_job(channel_id=channel_id, job_id=job_id, delete_remote=True, force=True)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Sunucu Render Sayfası (Dashboard & On-Demand İndirme) ──────────

@app.get("/api/server-render/jobs")
def get_server_render_jobs():
    """Dashboard ServerRenderPage için sunucudaki tüm işleri (tamamlanan, render edilen, kuyruktaki) listeler."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        reachable = runner.is_reachable()
        if not reachable:
            return {"server_online": False, "jobs": []}

        videos = runner.list_server_videos()
        completed_ids = set()
        formatted = []

        # 1. Tamamlanan ve indirilmeye hazır nihai videolar
        for v in videos:
            jid = v.get("job_id")
            completed_ids.add(jid)
            formatted.append({
                "job_id": jid,
                "channel_id": v.get("channel_id"),
                "title": v.get("title") or f"{v.get('channel_id')} - {jid}",
                "status": "completed",
                "file_size_mb": v.get("size_mb", 0),
                "duration": v.get("duration", 45),
                "created_at": v.get("created_at"),
                "progress_msg": "Sunucuda hazır, Mac 'yuklenecek' klasörüne indirilmeye hazır."
            })

        # 2. Şu anda aktif çalışan / render edilen arka plan görevleri
        for ex_id, ex in list(executions.items()):
            if not isinstance(ex, dict):
                continue
            st = ex.get("status")
            if st in ("running", "pending"):
                is_remote = (
                    ex.get("target_env") == "remote" or
                    "Oracle Cloud" in str(ex.get("message", "")) or
                    "Sunucu" in str(ex.get("message", ""))
                )
                if is_remote and ex_id not in completed_ids:
                    formatted.append({
                        "job_id": ex_id,
                        "channel_id": ex.get("channel_id", "general"),
                        "title": ex.get("title") or f"Bulut Render #{ex_id[-8:]}",
                        "status": "rendering",
                        "file_size_mb": 0,
                        "duration": 45,
                        "created_at": ex.get("timestamp", datetime.now().isoformat()),
                        "progress_msg": ex.get("message", "Sunucuda render ediliyor...")
                    })

        # 3. Sunucudaki sıralı kuyrukta bekleyen işler
        try:
            q_status = runner.get_queue_status()
            q_files = q_status.get("queue_files", [])
            for q_f in q_files:
                q_id = q_f.replace(".json", "")
                if q_id not in completed_ids and not any(j["job_id"] == q_id for j in formatted):
                    formatted.append({
                        "job_id": q_id,
                        "channel_id": "queue",
                        "title": f"Kuyruk Görevi: {q_id}",
                        "status": "queued",
                        "file_size_mb": 0,
                        "duration": 45,
                        "created_at": datetime.now().isoformat(),
                        "progress_msg": "Oracle Cloud sıralı görev kuyruğunda bekliyor (FIFO)."
                    })
        except Exception:
            pass

        return {"server_online": True, "jobs": formatted}
    except Exception as e:
        return {"server_online": False, "jobs": [], "error": str(e)}


class ServerRenderDownloadPayload(BaseModel):
    channel_id: Optional[str] = "default"


@app.post("/api/server-render/jobs/{job_id}/download")
def download_server_render_job(job_id: str, payload: ServerRenderDownloadPayload = Body(default=ServerRenderDownloadPayload())):
    """Sunucudaki videoyu Mac 'yuklenecek' klasörüne indirir ve sunucudan siler."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            raise HTTPException(status_code=503, detail="Oracle Cloud sunucusuna ulaşılamadı.")

        ch_id = payload.channel_id or "default"
        if ch_id == "default":
            all_vids = runner.list_server_videos()
            for v in all_vids:
                if v.get("job_id") == job_id:
                    ch_id = v.get("channel_id")
                    break

        res = runner.download_and_cleanup_job(channel_id=ch_id, job_id=job_id, delete_remote=True, force=True)
        clone_note = " (🎙️ RVC Klon Ses Giydirildi)" if res.get("voice_clone_applied") else ""
        return {
            "success": True,
            "job_id": job_id,
            "channel_id": ch_id,
            "voice_clone_applied": res.get("voice_clone_applied", False),
            "voice_clone_info": res.get("voice_clone_info", {}),
            "message": f"Video başarıyla Mac '{ch_id}/yuklenecek' klasörüne indirildi{clone_note} ve sunucudan silindi ({res.get('size_mb', 0)} MB)."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/server-render/jobs/{job_id}")
def delete_server_render_job(job_id: str):
    """Sunucudaki işi ve geçici dosyalarını siler."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        ok = runner.delete_remote_job(job_id)
        return {"success": ok, "message": f"{job_id} sunucudan silindi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/server-render/sync-all")
def sync_all_from_server():
    """Sunucudaki tüm hazır videoları kanalların 'yuklenecek' klasörlerine indirir ve sunucudan siler."""
    try:
        from src.remote_runner import RemoteRunner
        runner = RemoteRunner()
        if not runner.is_reachable():
            raise HTTPException(status_code=503, detail="Oracle Cloud sunucusuna bağlanılamadı.")
        downloaded = runner.download_all_pending()
        cloned_count = sum(1 for d in downloaded if d.get("voice_clone_applied"))
        clone_note = f" ({cloned_count} videoya RVC ses klonu giydirildi)" if cloned_count > 0 else ""
        return {
            "success": True,
            "count": len(downloaded),
            "cloned_count": cloned_count,
            "downloaded": downloaded,
            "message": f"{len(downloaded)} adet video başarıyla Mac'e indirildi{clone_note} ve sunucudan silindi."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ApplyVoiceClonePayload(BaseModel):
    video_path: str
    clone_id: Optional[str] = None
    pitch: Optional[int] = 0
    formant: Optional[float] = 1.0


class VideoVoiceoverRequest(BaseModel):
    video_path: str
    clone_id: str


@app.post("/api/video-voiceover/videos")
def upload_video_for_voiceover(file: UploadFile = File(...)):
    allowed_extensions = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
    original_name = Path(file.filename or "").name
    extension = Path(original_name).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen video biçimi. İzin verilenler: {', '.join(sorted(allowed_extensions))}",
        )

    output_root = Path(settings_mgr.get("output_dir", "output")).resolve()
    upload_dir = output_root / "_voiceover_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(original_name).stem).strip("_")[:100] or "video"
    video_path = upload_dir / f"{uuid.uuid4().hex}_{safe_stem}{extension}"
    try:
        with video_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)
        if video_path.stat().st_size == 0:
            video_path.unlink()
            raise HTTPException(status_code=400, detail="Seçilen video dosyası boş.")
    except HTTPException:
        raise
    except OSError as exc:
        video_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Video sunucuya kaydedilemedi.") from exc
    finally:
        file.file.close()

    return {"success": True, "video_path": str(video_path), "filename": original_name}


@app.post("/api/video-voiceover/jobs")
def start_video_voiceover(payload: VideoVoiceoverRequest):
    output_root = Path(settings_mgr.get("output_dir", "output")).resolve()
    video_path = Path(payload.video_path).resolve()
    try:
        video_path.relative_to(output_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Yalnızca çıktı klasörünüzdeki videolar işlenebilir.") from exc
    if not video_path.is_file() or video_path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}:
        raise HTTPException(status_code=404, detail="Seçilen video bulunamadı veya desteklenmiyor.")

    from voice_clone_manager import VoiceCloneManager
    clone = VoiceCloneManager().get_clone(payload.clone_id)
    if not clone:
        raise HTTPException(status_code=404, detail="Seçilen klon ses bulunamadı.")
    voice_prompt = next(
        (Path(prompt) for prompt in (clone.get("voice_pt_path"), clone.get("voice_wav_path")) if prompt and Path(prompt).is_file()),
        None,
    )
    if not voice_prompt:
        raise HTTPException(status_code=400, detail="Seçilen klon sesin Chatterbox ses profili bulunamadı.")

    from video_voiceover import VideoVoiceoverManager
    try:
        job_id = VideoVoiceoverManager().start_job(
            video_path=video_path,
            clone_id=payload.clone_id,
            clone_name=clone.get("name") or payload.clone_id,
            voice_prompt_path=voice_prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"success": True, "job_id": job_id}


@app.get("/api/video-voiceover/jobs/{job_id}")
def get_video_voiceover_job(job_id: str):
    from video_voiceover import VideoVoiceoverManager
    job = VideoVoiceoverManager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ses klonlama işi bulunamadı.")
    return job


@app.get("/api/video-voiceover/jobs/{job_id}/video")
def get_video_voiceover_output(job_id: str):
    from video_voiceover import VideoVoiceoverManager
    job = VideoVoiceoverManager().get_job(job_id)
    if not job or job.get("status") != "completed" or not job.get("result", {}).get("video_path"):
        raise HTTPException(status_code=404, detail="Seslendirilmiş video çıktısı bulunamadı.")
    video_path = Path(job["result"]["video_path"]).resolve()
    output_root = Path(settings_mgr.get("output_dir", "output")).resolve()
    try:
        video_path.relative_to(output_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Çıktı dosyası video klasörünüzün dışında.") from exc
    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Seslendirilmiş video dosyası silinmiş.")
    return FileResponse(video_path, media_type="video/mp4", filename=video_path.name)


@app.post("/api/videos/apply-voice-clone")
def api_apply_voice_clone(payload: ApplyVoiceClonePayload):
    """Mevcut bir yerel videoya aktif veya seçilen RVC ses klonunu giydirir ve ultrasonik telif filigranı ekler."""
    try:
        from voice_clone_manager import VoiceCloneManager
        mgr = VoiceCloneManager()
        res = mgr.apply_voice_clone_to_video(
            video_path=payload.video_path,
            clone_id=payload.clone_id,
            pitch=payload.pitch,
            formant=payload.formant
        )
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Klon ses giydirilemedi."))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# HEYGEN HYPERFRAMES (HTML/CSS/GSAP VIDEO MOTORU)
# ═══════════════════════════════════════════════════════════════

class HyperframesHookPayload(BaseModel):
    title: str
    subtitle: Optional[str] = ""
    badge: Optional[str] = "ÖZEL BÖLÜM"

@app.get("/api/hyperframes/status")
def get_hyperframes_status():
    from hyperframes_renderer import is_hyperframes_available, TEMPLATES_DIR, HYPERFRAMES_DIR
    available = is_hyperframes_available()
    templates = []
    if TEMPLATES_DIR.exists():
        templates = [p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir()]
    return {
        "available": available,
        "templates": templates,
        "path": str(HYPERFRAMES_DIR)
    }

@app.post("/api/hyperframes/render-hook")
def render_hyperframes_hook(payload: HyperframesHookPayload):
    from hyperframes_renderer import is_hyperframes_available, render_kinetic_hook
    if not is_hyperframes_available():
        raise HTTPException(status_code=503, detail="HyperFrames CLI kurulu değil.")
    
    out_dir = _PROJECT_ROOT / "output" / "hyperframes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"hook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    
    res = render_kinetic_hook(
        title=payload.title,
        subtitle=payload.subtitle or "",
        badge=payload.badge or "ÖZEL BÖLÜM",
        output_path=out_path
    )
    if not res or not res.exists():
        _clear_memory(trigger="hyperframes_render_failed")
        raise HTTPException(status_code=500, detail="HyperFrames hook render başarısız oldu.")

    _clear_memory(trigger="hyperframes_render_success")
    return {
        "success": True,
        "video_path": str(res),
        "video_url": f"/files/output/hyperframes/{res.name}",
        "duration": 4.0
    }


# ═══════════════════════════════════════════════════════════════
# RUTİNLER & ZAMANLANMIŞ ÇOKLU KANAL OTOMASYONU
# ═══════════════════════════════════════════════════════════════

class RoutinePayload(BaseModel):
    name: str
    channel_ids: List[str]
    schedule_time: str = "10:00"
    days: List[str] = ["all"]
    rest_minutes: int = 5
    require_approval: bool = True
    auto_open_gemini: bool = True
    active: bool = True


def run_routine_task(routine_id: str, exec_id: str):
    """
    Rutin içindeki kanalların içerik planlarını kontrol eder,
    gerekli senaryo ve materyalleri sağlar ve videoları
    her üretim arasında belirlenen x dakika dinlenme süresi vererek sırayla üretir.
    """
    executions[exec_id]["status"] = "running"
    executions[exec_id]["message"] = "Rutin başlatılıyor, kanalların içerik planları taranıyor..."

    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager

    rm = RoutineManager()
    routine = rm.get_routine(routine_id)
    if not routine:
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = "Rutin bulunamadı."
        return

    rm.set_routine_status(routine_id, "running")

    # 1. Kanalların içerik planlarını incele
    inspected = rm.inspect_routine_plans(routine_id)
    channels_to_run = [c for c in inspected.get("channels", []) if c.get("has_unproduced")]

    if not channels_to_run:
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = "Rutin kanallarında içerik planı veya üretilecek konu bulunamadı. Lütfen önce ilgili kanalların içerik planını oluşturun."
        rm.set_routine_status(routine_id, "idle", {"last_run": datetime.now().isoformat()})
        return

    total_videos = len(channels_to_run)
    rest_minutes = max(0, int(routine.get("rest_minutes", 5)))
    executions[exec_id]["total"] = total_videos
    executions[exec_id]["completed"] = 0
    executions[exec_id]["results"] = []

    success_count = 0
    staging_dir = _PROJECT_ROOT / "scratch" / "gemini_staging"

    from main import run_channel
    from video_generator import VideoGenerator
    from content_planner import ContentPlanner
    from channel_manager import ChannelManager

    cm = ChannelManager()
    output_dir = settings_mgr.get("output_dir", "output")
    generator = VideoGenerator()

    for idx, c_info in enumerate(channels_to_run):
        item_num = idx + 1
        cid = c_info["channel_id"]
        row_id = c_info["row_id"]
        topic_title = c_info["title"] or f"Konu #{row_id}"
        ch_name = c_info["channel_name"]

        executions[exec_id]["message"] = f"[{item_num}/{total_videos}] '{ch_name}' kanalı için '{topic_title}' üretiliyor..."
        executions[exec_id]["current_index"] = idx

        try:
            # Staged gemini verisi var mı kontrol et
            custom_script = None
            custom_images = None
            staged_file = staging_dir / f"staged_item_{row_id}.json"
            if staged_file.exists():
                try:
                    s_data = json.loads(staged_file.read_text(encoding="utf-8"))
                    custom_script = s_data.get("script")
                    custom_images = s_data.get("images")
                    print(f"[ROUTINE] Staged Gemini verisi bulundu ve kullanılıyor: {staged_file.name}")
                except Exception as s_err:
                    print(f"[ROUTINE] Staged veri okuma uyarısı: {s_err}")

            writer = _get_configured_script_writer()
            planner = ContentPlanner(Path(output_dir) / cid)

            result = run_channel(
                channel_id=cid,
                writer=writer,
                generator=generator,
                planner=planner,
                output_dir=output_dir,
                force_row_id=row_id,
                custom_script=custom_script,
                custom_images=custom_images
            )

            if result.get("success"):
                success_count += 1
                executions[exec_id]["results"].append(result)
                if staged_file.exists():
                    try:
                        staged_file.unlink()
                    except Exception:
                        pass
            else:
                print(f"[ROUTINE] Kanal {cid} video {row_id} uyarısı: {result.get('error')}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ROUTINE] Üretim hatası ({cid}): {e}")

        # Her rutin kanalı render bitiminde GPU ve bellek temizliği yap
        _clear_memory(trigger=f"routine_step_{cid}")

        executions[exec_id]["completed"] = item_num

        # ── İŞLEMCİ DİNLENMESİ (COOLDOWN) ──
        # Son video değilse ve rest_minutes > 0 ise işlemcinin soğuması için bekle
        if idx < total_videos - 1 and rest_minutes > 0:
            rest_seconds = int(rest_minutes * 60)
            print(f"[ROUTINE] İşlemcinin dinlenmesi başlatıldı: {rest_minutes} dakika...")
            start_wait = time.time()
            while time.time() - start_wait < rest_seconds:
                elapsed = int(time.time() - start_wait)
                remaining = max(0, rest_seconds - elapsed)
                rem_m = remaining // 60
                rem_s = remaining % 60
                executions[exec_id]["message"] = (
                    f"💤 Video {item_num}/{total_videos} tamamlandı. "
                    f"İşlemcinin soğuması için {rest_minutes} dk dinlenme modunda "
                    f"({rem_m:02d}:{rem_s:02d} kaldı)..."
                )
                time.sleep(2)

    now_iso = datetime.now().isoformat()
    if success_count > 0:
        executions[exec_id]["status"] = "success"
        executions[exec_id]["message"] = f"Rutin tamamlandı! Toplam {success_count}/{total_videos} video başarıyla üretildi."
        if executions[exec_id]["results"]:
            executions[exec_id]["result"] = executions[exec_id]["results"][-1]
        rm.set_routine_status(routine_id, "completed", {"last_run": now_iso})
        # Casper AI: Webhook Bildirimi (Tamamlandı)
        try:
            rm.send_webhook_notification("completed", {
                "routine_id": routine_id,
                "routine_name": routine.get("name"),
                "success_count": success_count,
                "total_videos": total_videos,
                "message": executions[exec_id]["message"]
            })
        except Exception as wh_err:
            print(f"[ROUTINE] Webhook bildirim uyarısı: {wh_err}")
    else:
        executions[exec_id]["status"] = "failed"
        executions[exec_id]["message"] = f"Rutin başarısız oldu (0/{total_videos} video üretilebildi)."
        rm.set_routine_status(routine_id, "error", {"last_run": now_iso})
        # Casper AI: Webhook Bildirimi (Başarısız)
        try:
            rm.send_webhook_notification("failed", {
                "routine_id": routine_id,
                "routine_name": routine.get("name"),
                "total_videos": total_videos,
                "message": executions[exec_id]["message"]
            })
        except Exception as wh_err:
            print(f"[ROUTINE] Webhook bildirim uyarısı: {wh_err}")

    _clear_memory(trigger="routine_task_finished")


@app.get("/api/routines")
def list_routines():
    """Tüm rutinleri listeler ve zamanlanmış durumları kontrol eder."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    rm.check_scheduled_routines()
    return {"success": True, "routines": rm.all_routines()}


@app.post("/api/routines")
def create_routine(payload: RoutinePayload):
    """Yeni rutin oluşturur."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    new_r = rm.add_routine(payload.dict())
    return {"success": True, "routine": new_r}


@app.post("/api/routines/{routine_id}/test-webhook")
def test_routine_webhook(routine_id: str, payload: dict = None):
    """Casper AI: Rutinin webhook & Telegram entegrasyonunu test eder."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    routine = rm.get_routine(routine_id) or {"id": routine_id, "name": "Test Rutini"}
    custom_url = (payload or {}).get("webhook_url")
    result = rm.send_webhook_notification("test", routine, custom_webhook_url=custom_url)
    return {"success": True, "result": result}


@app.get("/api/routines/pending-approvals")
def get_pending_routine_approvals():
    """Kullanıcıdan onay bekleyen zamanlanmış rutinleri döner."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    pending = rm.get_pending_approvals()
    return {"success": True, "pending": pending}


@app.get("/api/routines/{routine_id}")
def get_routine_detail(routine_id: str):
    """Rutin detayını döner."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    r = rm.get_routine(routine_id)
    if not r:
        raise HTTPException(status_code=404, detail="Rutin bulunamadı.")
    return {"success": True, "routine": r}


@app.put("/api/routines/{routine_id}")
def update_routine_endpoint(routine_id: str, payload: RoutinePayload):
    """Rutini günceller."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    updated = rm.update_routine(routine_id, payload.dict())
    if not updated:
        raise HTTPException(status_code=404, detail="Rutin bulunamadı.")
    return {"success": True, "routine": updated}


@app.delete("/api/routines/{routine_id}")
def delete_routine_endpoint(routine_id: str):
    """Rutini siler."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    deleted = rm.delete_routine(routine_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rutin bulunamadı.")
    return {"success": True, "message": "Rutin silindi."}


@app.post("/api/routines/{routine_id}/toggle")
def toggle_routine_endpoint(routine_id: str):
    """Rutini aktif/pasif yapar."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    toggled = rm.toggle_routine(routine_id)
    if not toggled:
        raise HTTPException(status_code=404, detail="Rutin bulunamadı.")
    return {"success": True, "routine": toggled}


@app.get("/api/routines/{routine_id}/inspect")
def inspect_routine_endpoint(routine_id: str):
    """Rutin içerisindeki kanalların içerik planı durumunu ve sıradaki konularını inceler."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    res = rm.inspect_routine_plans(routine_id)
    return res


@app.post("/api/routines/{routine_id}/approve")
def approve_routine_endpoint(routine_id: str, background_tasks: BackgroundTasks):
    """Kullanıcı bildirimi onayladığında rutini hemen arka planda başlatır."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    routine = rm.get_routine(routine_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Rutin bulunamadı.")

    exec_id = f"exec_routine_{routine_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    executions[exec_id] = {
        "status": "pending",
        "message": f"Rutin onaylandı, üretim sıraya alındı: {routine.get('name')}",
        "timestamp": datetime.now().isoformat(),
        "routine_id": routine_id
    }

    # Status'u running yap
    rm.set_routine_status(routine_id, "running")

    # Eğer auto_open_gemini aktifse Gemini sayfasını da tarayıcıda aç
    if routine.get("auto_open_gemini", True):
        try:
            import webbrowser
            webbrowser.open("https://gemini.google.com/app")
        except Exception:
            pass

    background_tasks.add_task(run_routine_task, routine_id, exec_id)
    return {"success": True, "exec_id": exec_id, "message": "Rutin onaylandı ve başlatıldı."}


@app.post("/api/routines/{routine_id}/trigger")
def trigger_routine_manual(routine_id: str, background_tasks: BackgroundTasks):
    """Rutini manuel olarak hemen çalıştırır."""
    return approve_routine_endpoint(routine_id, background_tasks)


@app.post("/api/routines/{routine_id}/snooze")
def snooze_routine_endpoint(routine_id: str, minutes: int = 15):
    """Rutini 15 dakika erteler."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    snoozed = rm.snooze_routine(routine_id, minutes=minutes)
    return {"success": True, "routine": snoozed, "message": f"Rutin {minutes} dakika ertelendi."}


@app.post("/api/routines/{routine_id}/dismiss")
def dismiss_routine_endpoint(routine_id: str):
    """Rutini bugünlük iptal eder."""
    try:
        from routine_manager import RoutineManager
    except ImportError:
        from src.routine_manager import RoutineManager
    rm = RoutineManager()
    dismissed = rm.dismiss_routine(routine_id)
    return {"success": True, "routine": dismissed, "message": "Rutin bugünlük iptal edildi."}


@app.post("/api/routines/{routine_id}/open-gemini")
def open_gemini_endpoint(routine_id: str):
    """Gemini web sayfasını açar."""
    import webbrowser
    webbrowser.open("https://gemini.google.com/app")
    return {"success": True, "message": "Gemini sayfası açıldı."}


@app.on_event("startup")
def start_routine_scheduler_background_thread():
    """Arka planda dakikada bir rutinlerin saatini kontrol eden cron motoru."""
    import threading
    def _routine_scheduler_loop():
        while True:
            try:
                from routine_manager import RoutineManager
                rm = RoutineManager()
                triggered = rm.check_scheduled_routines()
                for r in triggered:
                    # require_approval False ise doğrudan çalıştır
                    if not r.get("require_approval", True):
                        rid = r["id"]
                        exec_id = f"exec_routine_{rid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        executions[exec_id] = {
                            "status": "pending",
                            "message": f"Otomatik rutin başlatılıyor: {r.get('name')}",
                            "timestamp": datetime.now().isoformat(),
                            "routine_id": rid
                        }
                        threading.Thread(target=run_routine_task, args=(rid, exec_id), daemon=True).start()
            except Exception as e:
                print(f"[SCHEDULER] Zamanlanmış görev kontrolü başarısız: {e}")
            time.sleep(30)

    t = threading.Thread(target=_routine_scheduler_loop, daemon=True)
    t.start()

    try:
        from retention_manager import start_retention_daemon
        start_retention_daemon(interval_hours=12)
    except Exception as e:
        print(f"[RETENTION] Saklama denetçisi başlatma hatası: {e}")



@app.get("/api/groups/{group_id}/plan")
def get_group_plan(group_id: str):
    """Grup içerik planını döndürür; üretim ve yükleme durumlarını üye kanalların gerçek video dosyalarıyla senkronize eder."""
    from content_planner import ContentPlanner
    from browser_uploader import find_planned_video_folder
    output_dir = settings_mgr.get("output_dir", "output")
    grp_dir = Path(output_dir) / "groups" / group_id
    planner = ContentPlanner(grp_dir)
    raw_plan = planner.get_plan()

    mgr = ChannelManager()
    group = mgr.get_group(group_id)
    member_cids = group.get("channel_ids", []) if group else []

    resolved_plan = []
    for row in raw_plan:
        row_copy = dict(row)
        row_id = str(row.get("id"))

        if member_cids:
            member_vinfos = [find_planned_video_folder(cid, row_id, output_base_dir=output_dir) for cid in member_cids]
            all_produced = all(v is not None and v.get("is_produced") for v in member_vinfos)
            all_uploaded = all(v is not None and v.get("is_uploaded") for v in member_vinfos) if all_produced else False
            any_produced = any(v is not None and v.get("is_produced") for v in member_vinfos)

            if all_produced:
                row_copy["uretildi"] = "Evet"
                row_copy["yuklendi"] = "Evet" if all_uploaded else "Hayır"
            elif any_produced:
                row_copy["uretildi"] = "Kısmi"
                row_copy["yuklendi"] = "Hayır"
            else:
                row_copy["uretildi"] = "Hayır"
                row_copy["yuklendi"] = "Hayır"
        resolved_plan.append(row_copy)

    # Güncel istatistikler
    total = len(resolved_plan)
    produced = sum(1 for r in resolved_plan if r.get("uretildi") == "Evet")
    uploaded = sum(1 for r in resolved_plan if r.get("yuklendi") == "Evet")
    unproduced = total - produced

    stats = {
        "total": total,
        "produced": produced,
        "unproduced": unproduced,
        "uploaded": uploaded,
    }

    return {
        "success": True,
        "group_id": group_id,
        "plan": resolved_plan,
        "stats": stats,
    }


@app.get("/api/groups/{group_id}/plan/next-unproduced")
def get_group_next_unproduced(group_id: str, exclude_ids: Optional[str] = Query(default=None)):
    """Grup içerik planındaki sıradaki üretilmemiş konuyu döndürür."""
    from content_planner import ContentPlanner
    output_dir = settings_mgr.get("output_dir", "output")
    grp_dir = Path(output_dir) / "groups" / group_id
    planner = ContentPlanner(grp_dir)
    parsed_exclude = [x.strip() for x in exclude_ids.split(",") if x.strip()] if exclude_ids else None
    item = planner.get_next_unproduced(exclude_ids=parsed_exclude)
    if not item:
        return {"success": True, "has_unproduced": False, "message": "Üretilecek konu kalmadı."}

    mgr = ChannelManager()
    group = mgr.get_group(group_id)
    # Grup üyesi kanalların kategori bilgisini döndür (reddit kontrolü için)
    category = "reddit_stories"
    if group:
        category = group.get("topic_category", "reddit_stories")

    return {
        "success": True,
        "has_unproduced": True,
        "item": item,
        "channel": {
            "topic_category": category,
            "shorts_mode": True,
        }
    }


@app.post("/api/groups/{group_id}/plan/import")
def import_group_plan(group_id: str, payload: ImportTopicsRequest):
    """Gemini eklentisinden gruba toplu içerik planı satırları ekler."""
    from content_planner import ContentPlanner
    output_dir = settings_mgr.get("output_dir", "output")
    grp_dir = Path(output_dir) / "groups" / group_id
    planner = ContentPlanner(grp_dir)
    
    existing = planner.get_plan()
    existing_titles = {r.get("baslik", "").strip().lower() for r in existing if r.get("baslik")}

    new_items = []
    for topic_item in payload.topics:
        title = getattr(topic_item, "baslik", None) or getattr(topic_item, "title", None) or getattr(topic_item, "konu", "")
        instructions = getattr(topic_item, "yonergeler", "") or getattr(topic_item, "instructions", "") or getattr(topic_item, "notlar", "")
        if not title or not title.strip():
            continue
        title_val = title.strip()
        if title_val.lower() not in existing_titles:
            new_items.append({
                "konu": title_val,
                "baslik": title_val,
                "notlar": instructions.strip(),
            })
            existing_titles.add(title_val.lower())

    if not new_items:
        return {"success": True, "added_count": 0, "message": "Eklenen yeni konu yok."}

    added = planner.add_topics(new_items)
    
    # Eğer topic_item içinde senaryo (script) materyalleri de varsa 'Üretim Metaryalleri'ne de kaydet
    try:
        from materials_manager import MaterialsManager
        mat_mgr = MaterialsManager(output_dir)
        for topic_item in payload.topics:
            title = getattr(topic_item, "baslik", None) or getattr(topic_item, "title", None) or getattr(topic_item, "konu", "")
            script = getattr(topic_item, "script", None)
            notes = getattr(topic_item, "yonergeler", "") or getattr(topic_item, "notes", "") or ""
            images = getattr(topic_item, "images", None)
            if not title or not script or not isinstance(script, dict):
                continue
            has_scenes = bool(script.get("scenes") or any(isinstance(script.get(k), dict) and script[k].get("scenes") for k in ("tr", "en", "es", "de")))
            if has_scenes:
                # Eşleşen satır id'sini bul
                matched_row = next((r for r in added if r.get("baslik") == title.strip()), None)
                r_id = matched_row.get("id") if matched_row else ""
                mat_mgr.save_material(
                    channel_id=f"group:{group_id}",
                    script=script,
                    title=title.strip(),
                    topic=title.strip(),
                    row_id=r_id,
                    images=images,
                    notes=notes
                )
    except Exception as e_mat:
        print(f"[GROUP-PLAN-IMPORT] Materyal kaydetme uyarısı: {e_mat}")

    return {"success": True, "added_count": len(added), "group_id": group_id}


@app.post("/api/groups/{group_id}/plan")
def create_group_plan(group_id: str, payload: PlanRequest):
    """Grup için AI ile toplu konu planı üretir ve grup CSV'sine kaydeder."""
    mgr = ChannelManager()
    group = mgr.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grup bulunamadı.")

    output_dir = settings_mgr.get("output_dir", "output")
    grp_dir = Path(output_dir) / "groups" / group_id
    planner = ContentPlanner(grp_dir)

    provider = settings_mgr.get("ai_provider", "claude")
    api_key = ""
    if provider == "claude":
        api_key = settings_mgr.get("anthropic_api_key")
    elif provider == "gemini":
        api_key = settings_mgr.get("gemini_api_key")

    ai_model = settings_mgr.get(f"{provider}_model", "")
    ollama_url = settings_mgr.get("ollama_url", "http://localhost:11434")
    lmstudio_url = settings_mgr.get("lmstudio_url", "http://localhost:1234/v1")

    writer = ScriptWriter(
        provider=provider,
        api_key=api_key,
        model=ai_model,
        ollama_url=ollama_url,
        lmstudio_url=lmstudio_url,
    )

    try:
        category = group.get("topic_category", "reddit_stories")
        dummy_channel = {
            "name": group.get("name", "Grup"),
            "language": "tr",
            "topic_category": category,
            "shorts_mode": True
        }
        existing_rows = planner.get_plan()
        existing_titles = [r.get("baslik") for r in existing_rows if r.get("baslik")]

        topics = writer.generate_topic_list(dummy_channel, count=payload.count, existing_topics=existing_titles)
        new_rows = planner.add_topics(topics)
        return {"success": True, "count": len(new_rows), "topics": new_rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grup konu planlama hatası: {str(e)}")


@app.post("/api/groups/{group_id}/plan/manual-add")
def manual_add_group_topic(group_id: str, payload: dict):
    """Grup planına manuel tekil konu ekler."""
    from content_planner import ContentPlanner
    title = (payload.get("baslik") or payload.get("konu") or "").strip()
    notes = (payload.get("notlar") or payload.get("yonergeler") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Konu/Başlık alanı boş olamaz.")

    output_dir = settings_mgr.get("output_dir", "output")
    grp_dir = Path(output_dir) / "groups" / group_id
    planner = ContentPlanner(grp_dir)

    added = planner.add_topics([{
        "konu": title,
        "baslik": title,
        "notlar": notes
    }])
    return {"success": True, "added": added}


@app.post("/api/groups/{group_id}/plan/batch-delete")
def batch_delete_group_plan_rows(group_id: str, payload: dict):
    """Seçilen birden fazla grup plan satırını tek seferde siler."""
    from content_planner import ContentPlanner
    row_ids = payload.get("row_ids", [])
    if not row_ids:
        raise HTTPException(status_code=400, detail="row_ids parametresi zorunludur.")

    output_dir = settings_mgr.get("output_dir", "output")
    grp_dir = Path(output_dir) / "groups" / group_id
    planner = ContentPlanner(grp_dir)

    deleted_count = planner.delete_topics(row_ids)
    return {"success": True, "deleted_count": deleted_count}


@app.get("/api/groups/{group_id}/plan/download")
def download_group_plan(group_id: str):
    """Grup plan CSV dosyasını indirir."""
    from content_planner import ContentPlanner
    output_dir = settings_mgr.get("output_dir", "output")
    grp_dir = Path(output_dir) / "groups" / group_id
    planner = ContentPlanner(grp_dir)
    if not planner.plan_exists():
        raise HTTPException(status_code=404, detail="Grup planı bulunamadı.")
    return FileResponse(
        path=str(planner.plan_path),
        media_type="text/csv",
        filename=f"grup_{group_id}_icerik_plani.csv"
    )


@app.delete("/api/groups/{group_id}/plan/{row_id}")
def delete_group_plan_row(group_id: str, row_id: str):
    """Grup planından tekil satır siler."""
    from content_planner import ContentPlanner
    output_dir = settings_mgr.get("output_dir", "output")
    grp_dir = Path(output_dir) / "groups" / group_id
    planner = ContentPlanner(grp_dir)
    deleted = planner.delete_topic(row_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Plan satırı bulunamadı.")
    return {"success": True}


@app.get("/api/browser-agent/status")
def get_browser_agent_status_endpoint():
    """Browser Agent canlı durumunu ve işlem günlüklerini döner."""
    from browser_agent import browser_agent
    return browser_agent.get_status()


@app.post("/api/browser-agent/start")
def start_browser_agent_endpoint(payload: dict):
    """LM Studio AI ve Browser MCP destekli yükleme görevini başlatır."""
    from browser_agent import browser_agent
    output_dir = settings_mgr.get("output_dir", "output")
    channel_id = payload.get("channel_id")
    group_id = payload.get("group_id")
    row_id = payload.get("row_id")

    res = browser_agent.plan_and_execute_upload(
        channel_id=channel_id,
        group_id=group_id,
        row_id=row_id,
        output_base_dir=output_dir,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Görev başlatılamadı."))
    return res


@app.post("/api/browser-agent/log")
def log_browser_agent_endpoint(payload: dict):
    """Tarayıcı eklentisi veya frontend'den canlı işlem günlüğü kaydeder."""
    from browser_agent import browser_agent
    msg = payload.get("message", "")
    lvl = payload.get("level", "info")
    details = payload.get("details")
    browser_agent.log(msg, level=lvl, details=details)
    return {"success": True}


_global_pending_upload = {}

@app.get("/api/extension/pending-upload")
def get_extension_pending_upload():
    """Chrome Eklentisi YouTube Studio'yu açtığında sıradaki yüklenecek video/kuyruk bilgisini alır."""
    global _global_pending_upload
    if _global_pending_upload and (time.time() - _global_pending_upload.get("timestamp", 0) < 600):
        return _global_pending_upload
    return {"payload": None, "queue": []}


@app.post("/api/extension/pending-upload")
def set_extension_pending_upload(data: dict):
    """Chrome Eklentisi için yüklenecek video kuyruğunu ayarlar."""
    global _global_pending_upload
    _global_pending_upload = {
        "payload": data.get("payload"),
        "queue": data.get("queue", []),
        "timestamp": time.time(),
    }
    return {"success": True, "pending": _global_pending_upload}


@app.post("/api/extension/pending-upload/clear")
def clear_extension_pending_upload():
    """Bekleyen yükleme kuyruğunu temizler."""
    global _global_pending_upload
    _global_pending_upload = {}
    return {"success": True}


class YouTubeUploadRequest(BaseModel):
    row_id: str
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class InstagramScheduleRequest(BaseModel):
    folder: str
    scheduled_date: str
    scheduled_time: str
    caption: Optional[str] = None


def _instagram_schedule_store():
    return instagram_schedule_store


@app.get("/api/channels/{channel_id}/instagram-schedule-info")
def get_instagram_schedule_info(channel_id: str):
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    from youtube_scheduler import get_channel_timezone

    channel = ChannelManager().get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
    if not channel.get("instagram"):
        raise HTTPException(status_code=400, detail="Bu kanal için Instagram paylaşımı etkin değil.")

    timezone_name = get_channel_timezone(channel.get("language", "tr"))
    zone = ZoneInfo(timezone_name)
    suggested = datetime.now(zone) + timedelta(days=1)
    suggested = suggested.replace(
        hour=int(channel.get("schedule_hour", 19)),
        minute=0,
        second=0,
        microsecond=0,
    )
    if suggested <= datetime.now(zone):
        suggested += timedelta(days=1)

    scheduled_folders = {
        schedule.get("folder")
        for schedule in _instagram_schedule_store().list(channel_id)
        if schedule.get("status") in ("scheduled", "publishing", "published", "needs_review")
    }
    videos = [
        {
            "folder": item.get("folder"),
            "title": item.get("title") or item.get("folder", "").split("/")[-1],
            "description": item.get("description", ""),
            "video_url": item.get("video_url", ""),
            "uploaded_instagram": item.get("uploaded_instagram", False),
            "archived": item.get("archived", False),
        }
        for item in list_output_videos()
        if item.get("channel_id") == channel_id
        and not item.get("uploaded_instagram")
        and not item.get("archived")
        and item.get("video_path")
        and Path(item["video_path"]).is_file()
        and item.get("folder") not in scheduled_folders
    ]
    return {
        "channel_id": channel_id,
        "channel_name": channel.get("name", channel_id),
        "instagram_username": channel.get("instagram_username", ""),
        "timezone": timezone_name,
        "suggested_date": suggested.strftime("%Y-%m-%d"),
        "suggested_time": suggested.strftime("%H:%M"),
        "configured": True,
        "publisher": "chrome_extension",
        "ready_videos": videos,
        "schedules": _instagram_schedule_store().list(channel_id),
    }


@app.get("/api/instagram/schedules")
def get_instagram_schedules(channel_id: Optional[str] = None):
    return {"schedules": _instagram_schedule_store().list(channel_id)}


@app.post("/api/instagram/schedules")
def create_instagram_schedule(payload: InstagramScheduleRequest):
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    from youtube_scheduler import get_channel_timezone

    channel_manager = ChannelManager()
    folder = payload.folder.strip().strip("/")
    output_dir = Path(settings_mgr.get("output_dir", "output")).resolve()
    channel_id = folder.split("/", 1)[0]
    channel = channel_manager.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Video klasörüne ait kanal bulunamadı.")
    if not channel.get("instagram") or not channel.get("instagram_username"):
        raise HTTPException(status_code=400, detail="Kanala Instagram seçeneği ve kullanıcı adı ekleyin.")

    folder_path = (output_dir / folder).resolve()
    try:
        folder_path.relative_to((output_dir / channel_id).resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Video klasörü kanal dizininin dışında olamaz.") from exc
    if not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Seçilen video klasörü bulunamadı.")
    video_file = folder_path / "final.mp4"
    if not video_file.is_file():
        video_file = folder_path / "base.mp4"
    if not video_file.is_file():
        raise HTTPException(status_code=404, detail="Seçilen klasörde MP4 video bulunamadı.")

    try:
        local_datetime = datetime.strptime(
            f"{payload.scheduled_date} {payload.scheduled_time}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Geçersiz planlama tarihi veya saati.") from exc
    local_zone = ZoneInfo(get_channel_timezone(channel.get("language", "tr")))
    scheduled_at = local_datetime.replace(tzinfo=local_zone)
    now = datetime.now(local_zone)
    if scheduled_at <= now + timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="Instagram paylaşımı en az 5 dakika ileri bir zamana planlanmalı.")

    caption = payload.caption if payload.caption is not None else ""
    if len(caption) > 2200:
        raise HTTPException(status_code=400, detail="Instagram açıklaması en fazla 2.200 karakter olabilir.")
    try:
        entry = _instagram_schedule_store().create(
            {
                "channel_id": channel_id,
                "instagram_username": channel["instagram_username"].lstrip("@"),
                "folder": str(folder_path.relative_to(output_dir)),
                "video_path": str(video_file),
                "title": video_file.parent.name,
                "caption": caption,
                "scheduled_at": scheduled_at.isoformat(),
                "timezone": str(local_zone),
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "success": True,
        "message": f"@{entry['instagram_username']} için gönderi planlandı. Paylaşım saatinde Chrome eklentisi, Instagram’da açık oturum üzerinden yükleyecek.",
        "schedule": entry,
    }


@app.delete("/api/instagram/schedules/{schedule_id}")
def cancel_instagram_schedule(schedule_id: str):
    if not _instagram_schedule_store().cancel(schedule_id):
        raise HTTPException(status_code=404, detail="Bekleyen plan bulunamadı veya işlem başlamış.")
    return {"success": True}


@app.post("/api/instagram/schedules/claim")
def claim_due_instagram_schedule():
    """Claim one due item for the installed browser extension."""
    store = _instagram_schedule_store()
    entry = store.claim_due()
    return {"schedule": entry}


@app.get("/api/instagram/schedules/{schedule_id}/video")
def get_instagram_schedule_video(schedule_id: str):
    entry = next(
        (item for item in _instagram_schedule_store().list() if item.get("id") == schedule_id),
        None,
    )
    if not entry or entry.get("status") != "publishing":
        raise HTTPException(status_code=404, detail="Yükleme için video bulunamadı.")
    video_file = Path(entry["video_path"]).resolve()
    output_dir = Path(settings_mgr.get("output_dir", "output")).resolve()
    try:
        video_file.relative_to(output_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Video yolu çıktı klasörünün dışında.") from exc
    if not video_file.is_file():
        raise HTTPException(status_code=404, detail="Planlanan video dosyası bulunamadı.")
    return FileResponse(video_file, media_type="video/mp4", filename=video_file.name)


class InstagramScheduleResult(BaseModel):
    success: bool
    error: Optional[str] = None
    uncertain: bool = False


@app.post("/api/instagram/schedules/{schedule_id}/result")
def finish_instagram_schedule(schedule_id: str, payload: InstagramScheduleResult):
    from datetime import timedelta, timezone

    store = _instagram_schedule_store()
    entry = next(
        (item for item in store.list() if item.get("id") == schedule_id),
        None,
    )
    if not entry or entry.get("status") != "publishing":
        raise HTTPException(status_code=409, detail="Plan yükleme durumunda değil.")

    if not payload.success:
        error = (payload.error or "Instagram yüklemesi başarısız oldu.")[:1000]
        attempts = int(entry.get("attempts", 1))
        if payload.uncertain:
            status = "needs_review"
            store.update(
                schedule_id,
                status=status,
                last_error=error,
                attempt_started_at=None,
            )
        elif attempts < 3:
            status = "scheduled"
            store.update(
                schedule_id,
                status=status,
                retry_at=(datetime.now(timezone.utc) + timedelta(minutes=5 * attempts)).isoformat(),
                last_error=error,
                attempt_started_at=None,
            )
        else:
            status = "failed"
            store.update(schedule_id, status="failed", last_error=error, attempt_started_at=None)
        return {"success": False, "status": status}

    published_at = datetime.now().astimezone().isoformat()
    store.update(
        schedule_id,
        status="published",
        published_at=published_at,
        last_error=None,
        attempt_started_at=None,
    )
    try:
        video_info_path = Path(entry["video_path"]).parent / "video_info.json"
        video_info = {}
        if video_info_path.exists():
            video_info = json.loads(video_info_path.read_text(encoding="utf-8"))
        video_info.update(
            {
                "uploaded_instagram": True,
                "instagram_username": entry["instagram_username"],
                "instagram_published_at": published_at,
                "instagram_scheduled_at": entry["scheduled_at"],
            }
        )
        video_info_path.write_text(json.dumps(video_info, ensure_ascii=False, indent=2), encoding="utf-8")

        # Kontrol: Eğer YouTube ve diğer platformlar da yüklendiyse yuklenen'e taşı
        channel_id = entry.get("channel_id", "")
        ch_mgr = ChannelManager()
        channel = ch_mgr.get_channel(channel_id) if channel_id else None
        
        yt_done = bool(video_info.get("uploaded_youtube"))
        tt_done = True
        if channel and channel.get("tiktok", False):
            tt_done = bool(video_info.get("uploaded_tiktok"))

        sub_folder = video_info_path.parent
        if yt_done and tt_done and "yuklenecek" in str(sub_folder):
            output_dir = settings_mgr.get("output_dir", "output")
            dest_parent = Path(output_dir) / channel_id / "yuklenen"
            dest_parent.mkdir(parents=True, exist_ok=True)
            dest_folder = dest_parent / sub_folder.name
            if not dest_folder.exists():
                import shutil
                shutil.move(str(sub_folder), str(dest_folder))
                print(f"[INSTAGRAM] Tüm platformlar tamamlandı, video 'yuklenen' klasörüne taşındı: {sub_folder.name}")
        else:
            print(f"[INSTAGRAM] Video Instagram'a yüklendi ancak YouTube henüz yüklenmedi (YouTube: {yt_done}). 'yuklenecek' klasöründe saklanıyor.")
    except (OSError, json.JSONDecodeError) as metadata_error:
        print(f"[INSTAGRAM-SCHEDULE] Yayın başarılı, video metadata güncellenemedi: {metadata_error}")
    return {"success": True, "status": "published"}


@app.get("/api/channels/{channel_id}/youtube-upload-info")
def get_channel_youtube_upload_info(channel_id: str):
    """
    YouTube Yükleme Merkezi için:
    - API bağlantı durumu
    - Son yüklenen video tarihi
    - Bir sonraki planlama yuvası (son videonun ertesi günü aynı saat)
    - Yüklenmeye hazır videolar ve her biri için otomatik artan planlama tarihi
    - Daha önce yüklenmiş videolar
    """
    output_dir = settings_mgr.get("output_dir", "output")
    token_file = Path("credentials") / f"{channel_id}_token.json"
    api_connected = token_file.exists()

    ch_mgr = ChannelManager()
    all_channels = ch_mgr.all_channels()
    connected_channels = []
    for c in all_channels:
        cid = c.get("channel_id")
        if (Path("credentials") / f"{cid}_token.json").exists():
            connected_channels.append({
                "channel_id": cid,
                "name": c.get("name", cid),
                "language": c.get("language", "tr")
            })

    channel = ch_mgr.get_channel(channel_id) or {"channel_id": channel_id, "name": channel_id, "language": "tr"}
    
    from content_planner import ContentPlanner
    from youtube_scheduler import calculate_channel_next_schedule_slot, get_channel_timezone
    from browser_uploader import find_planned_video_folder
    from datetime import timedelta

    planner = ContentPlanner(Path(output_dir) / channel_id)
    plan_rows = planner.get_plan()

    # Slot ve en son tarih
    slot = calculate_channel_next_schedule_slot(channel, plan_rows=plan_rows)
    latest_uploaded_str = slot.get("latest_date_str")
    
    next_base_dt = slot.get("scheduled_datetime")
    tz_name = slot.get("timezone", "Europe/Istanbul")
    hour = int(slot.get("target_time_str", "19:00").split(":")[0])

    ready_videos = []
    current_slot_offset = 0

    # 1. İçerik planında üretilmiş ama henüz yüklenmemiş videolar
    for row in plan_rows:
        is_produced = row.get("uretildi", "").strip().lower() == "evet"
        is_uploaded = row.get("yuklendi", "").strip().lower() == "evet"
        r_id = str(row.get("id"))
        if is_produced and not is_uploaded:
            v_match = find_planned_video_folder(channel_id, r_id, output_base_dir=output_dir)
            if v_match:
                if v_match.get("is_uploaded"):
                    continue
                v_file_str = v_match.get("video_file") or v_match.get("video_path")
                if not v_file_str or not Path(v_file_str).exists():
                    continue
                v_file = Path(v_file_str)
                if "yuklenen" in v_file.parts or "arsiv" in v_file.parts:
                    continue
                vinfo_p = v_file.parent / "video_info.json"
                if vinfo_p.exists():
                    try:
                        with open(vinfo_p, "r", encoding="utf-8") as vf:
                            if json.load(vf).get("uploaded_youtube"):
                                continue
                    except Exception:
                        pass

                    size_mb = round(v_file.stat().st_size / (1024 * 1024), 1)
                    vid_dt = next_base_dt + timedelta(days=current_slot_offset) if next_base_dt else None
                    sug_date = vid_dt.strftime("%Y-%m-%d") if vid_dt else slot["target_date_str"]
                    sug_time = f"{hour:02d}:00"
                    sug_display = f"{sug_date} {sug_time}"
                    current_slot_offset += 1

                    duration = 0
                    vinfo_p = v_file.parent / "video_info.json"
                    if vinfo_p.exists():
                        try:
                            with open(vinfo_p, "r", encoding="utf-8") as vf:
                                duration = round(json.load(vf).get("duration", 0), 1)
                        except Exception:
                            pass

                    thumb_file = v_file.parent / "thumbnail.jpg"
                    thumb_url = f"/output/{v_match.get('folder')}/thumbnail.jpg" if thumb_file.exists() else ""

                    ready_videos.append({
                        "row_id": r_id,
                        "folder": v_match.get("folder", ""),
                        "title": v_match.get("title") or row.get("baslik") or row.get("konu"),
                        "description": v_match.get("description", ""),
                        "tags": v_match.get("tags", []),
                        "video_url": v_match.get("video_url", ""),
                        "video_path": str(v_file),
                        "thumbnail_url": thumb_url,
                        "duration_sec": duration,
                        "file_size_mb": size_mb,
                        "suggested_date": sug_date,
                        "suggested_time": sug_time,
                        "suggested_display": sug_display,
                    })

    # 2. Planda olmayan fakat yuklenecek dizininde duran ek videolar
    yuklenecek_dir = Path(output_dir) / channel_id / "yuklenecek"
    if yuklenecek_dir.exists():
        ready_folders = set(v["folder"] for v in ready_videos)
        candidate_dirs = []
        for sub in sorted(yuklenecek_dir.iterdir()):
            if sub.is_dir():
                candidate_dirs.append((sub, f"{channel_id}/yuklenecek/{sub.name}"))
                for child in sorted(sub.iterdir()):
                    if child.is_dir() and child.name.startswith("shorts_"):
                        candidate_dirs.append((child, f"{channel_id}/yuklenecek/{sub.name}/{child.name}"))

        for item, rel_folder in candidate_dirs:
            if rel_folder in ready_folders or item.name in set(v["folder"].split("/")[-1] for v in ready_videos):
                continue
            v_file = item / "final.mp4"
            if not v_file.exists():
                v_file = item / "video.mp4"
            if not v_file.exists():
                v_file = item / "base.mp4"
            if v_file.exists():
                meta_p = item / "metadata.json"
                vinfo_p = item / "video_info.json"
                title = item.name
                desc = "#Shorts"
                tags = ["Shorts"]
                duration = 0
                is_shorts = item.name.startswith("shorts_")
                if meta_p.exists():
                    try:
                        with open(meta_p, "r", encoding="utf-8") as mf:
                            mdata = json.load(mf)
                            title = mdata.get("title") or title
                            desc = mdata.get("description") or desc
                            tags = mdata.get("tags") or tags
                    except Exception:
                        pass
                if vinfo_p.exists():
                    try:
                        with open(vinfo_p, "r", encoding="utf-8") as vf:
                            vdata = json.load(vf)
                            duration = round(vdata.get("duration", vdata.get("duration_sec", 0)), 1)
                            if vdata.get("shorts_mode"):
                                is_shorts = True
                    except Exception:
                        pass

                size_mb = round(v_file.stat().st_size / (1024 * 1024), 1)
                vid_dt = next_base_dt + timedelta(days=current_slot_offset) if next_base_dt else None
                sug_date = vid_dt.strftime("%Y-%m-%d") if vid_dt else slot["target_date_str"]
                sug_time = f"{hour:02d}:00"
                sug_display = f"{sug_date} {sug_time}"
                current_slot_offset += 1

                thumb_file = item / "thumbnail.jpg"
                thumb_url = f"/output/{rel_folder}/thumbnail.jpg" if thumb_file.exists() else ""

                ready_videos.append({
                    "row_id": item.name.split("_")[0] if "_" in item.name else "",
                    "folder": rel_folder,
                    "title": title,
                    "description": desc,
                    "tags": tags,
                    "video_url": f"/output/{rel_folder}/{v_file.name}",
                    "video_path": str(v_file),
                    "thumbnail_url": thumb_url,
                    "duration_sec": duration,
                    "file_size_mb": size_mb,
                    "is_shorts": is_shorts,
                    "suggested_date": sug_date,
                    "suggested_time": sug_time,
                    "suggested_display": sug_display,
                })

    # Yüklenmiş videolar arşivi
    uploaded_videos = []
    for row in plan_rows:
        if row.get("yuklendi", "").strip().lower() == "evet":
            r_id = str(row.get("id"))
            v_match = find_planned_video_folder(channel_id, r_id, output_base_dir=output_dir)
            thumb_url = ""
            if v_match:
                t_str = v_match.get("thumbnail_file") or v_match.get("thumbnail_path")
                if t_str and Path(t_str).exists():
                    thumb_url = f"/output/{v_match.get('folder')}/thumbnail.jpg"

            uploaded_videos.append({
                "row_id": r_id,
                "title": (v_match.get("title") if v_match else None) or row.get("baslik") or row.get("konu"),
                "yayim_tarihi": row.get("yayim_tarihi", ""),
                "video_url": row.get("video_url", ""),
                "thumbnail_url": thumb_url,
                "source": "plan"
            })
    
    yuklenen_dir = Path(output_dir) / channel_id / "yuklenen"
    if yuklenen_dir.exists():
        for sub in sorted(yuklenen_dir.iterdir(), reverse=True):
            if sub.is_dir():
                sub_row_id = sub.name.split("_")[0] if "_" in sub.name else ""
                already = False
                try:
                    s_int = int(sub_row_id)
                    already = any(int(u.get("row_id") or -1) == s_int for u in uploaded_videos)
                except Exception:
                    already = any(u.get("title") == sub.name for u in uploaded_videos)

                if already:
                    continue

                vinfo_p = sub / "video_info.json"
                title = sub.name
                yt_url = ""
                sched = ""
                if vinfo_p.exists():
                    try:
                        with open(vinfo_p, "r", encoding="utf-8") as vf:
                            vdata = json.load(vf)
                            title = vdata.get("title") or title
                            yt_url = vdata.get("youtube_url") or ""
                            sched = vdata.get("scheduled_for") or ""
                    except Exception:
                        pass
                thumb_file = sub / "thumbnail.jpg"
                uploaded_videos.append({
                    "row_id": sub_row_id,
                    "title": title,
                    "yayim_tarihi": sched,
                    "video_url": yt_url,
                    "thumbnail_url": f"/output/{channel_id}/yuklenen/{sub.name}/thumbnail.jpg" if thumb_file.exists() else "",
                    "source": "folder"
                })

    return {
        "channel_id": channel_id,
        "channel_name": channel.get("name", channel_id),
        "language": channel.get("language", "tr"),
        "timezone": tz_name,
        "schedule_hour": hour,
        "api_connected": api_connected,
        "connected_channels": connected_channels,
        "latest_uploaded_datetime": latest_uploaded_str,
        "latest_uploaded_display": f"{latest_uploaded_str} ({tz_name})" if latest_uploaded_str else "Henüz planlı video yok",
        "next_slot": {
            "date": slot["target_date_str"],
            "time": slot["target_time_str"],
            "datetime_str": slot["target_datetime_str"],
            "display": slot["display_summary"],
        },
        "ready_videos": ready_videos,
        "uploaded_videos": uploaded_videos,
    }


@app.post("/api/channels/{channel_id}/youtube-upload")
def youtube_direct_upload_endpoint(channel_id: str, req: YouTubeUploadRequest):
    """
    YouTube Upload sayfasından doğrudan YouTube API'ye video yükler ve planlar.
    En son yüklenen videodan sonraki günün saatine (veya kullanıcının seçtiği zamana) ayarlar.
    """
    output_dir = settings_mgr.get("output_dir", "output")
    token_file = Path("credentials") / f"{channel_id}_token.json"
    if not token_file.exists():
        raise HTTPException(
            status_code=403,
            detail=f"'{channel_id}' kanalı için YouTube API yetki anahtarı bulunamadı. Lütfen önce kanalı yetkilendirin."
        )

    from browser_uploader import find_planned_video_folder
    from youtube_uploader import YouTubeUploader
    from youtube_scheduler import calculate_channel_next_schedule_slot, get_channel_timezone
    from content_planner import ContentPlanner
    import shutil
    import zoneinfo
    from datetime import timezone

    video_match = find_planned_video_folder(channel_id, req.row_id, output_base_dir=output_dir)
    if not video_match:
        raise HTTPException(status_code=404, detail=f"Satır #{req.row_id} için klasör bulunamadı.")

    video_file_str = video_match.get("video_file") or video_match.get("video_path")
    if not video_file_str or not Path(video_file_str).exists():
        raise HTTPException(status_code=404, detail=f"Satır #{req.row_id} için hazır video dosyası bulunamadı.")

    video_file = Path(video_file_str)
    title = req.title or video_match.get("title") or video_file.parent.name
    description = req.description or video_match.get("description", "#Shorts")
    tags = req.tags if req.tags is not None else video_match.get("tags", ["Shorts"])
    thumb_file_str = video_match.get("thumbnail_file") or video_match.get("thumbnail_path")
    thumb_file = Path(thumb_file_str) if thumb_file_str and Path(thumb_file_str).exists() else None

    ch_mgr = ChannelManager()
    channel = ch_mgr.get_channel(channel_id) or {"channel_id": channel_id, "language": "tr"}
    tz_name = get_channel_timezone(channel.get("language", "tr"))
    tz = zoneinfo.ZoneInfo(tz_name)

    planner = ContentPlanner(Path(output_dir) / channel_id)
    plan_rows = planner.get_plan()

    if req.scheduled_date and req.scheduled_time:
        try:
            dt_local = datetime.strptime(f"{req.scheduled_date} {req.scheduled_time}", "%Y-%m-%d %H:%M")
            target_date_str = req.scheduled_date
            target_time_str = req.scheduled_time
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Geçersiz tarih/saat: {e}")
    else:
        slot = calculate_channel_next_schedule_slot(channel, plan_rows=plan_rows)
        dt_local = slot.get("scheduled_datetime")
        target_date_str = slot.get("target_date_str")
        target_time_str = slot.get("target_time_str")

    publish_at_iso = None
    if dt_local:
        dt_utc = dt_local.replace(tzinfo=tz).astimezone(timezone.utc)
        publish_at_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    uploader = YouTubeUploader()
    try:
        upload_res = uploader.upload(
            channel_id=channel_id,
            video_path=str(video_file),
            title=title,
            description=description,
            tags=tags,
            category="entertainment" if ("yazan" in channel_id or "whatsapp" in channel_id) else "education",
            privacy="private" if publish_at_iso else "public",
            thumbnail_path=str(thumb_file) if thumb_file else None,
            publish_at=publish_at_iso,
        )
    except Exception as up_err:
        print(f"[YOUTUBE-API] Upload Hatası: {up_err}")
        raise HTTPException(status_code=500, detail=f"YouTube API yükleme hatası: {str(up_err)}")

    scheduled_display = f"{target_date_str} {target_time_str}"
    
    # 1. İçerik planında yüklendi olarak işaretle
    try:
        planner.mark_as_uploaded(
            req.row_id,
            yayim_tarihi=scheduled_display,
            video_url=upload_res.get("url", ""),
        )
    except Exception as pe:
        print(f"[YOUTUBE-API] Plan güncelleme uyarısı: {pe}")

    # 2. video_info.json'ı güncelle
    sub_folder = video_file.parent
    vinfo_p = sub_folder / "video_info.json"
    if vinfo_p.exists():
        try:
            with open(vinfo_p, "r", encoding="utf-8") as vf:
                vdata = json.load(vf)
            vdata["uploaded_youtube"] = True
            vdata["scheduled_for"] = scheduled_display
            vdata["youtube_url"] = upload_res.get("url", "")
            vdata["youtube_id"] = upload_res.get("video_id", "")
            with open(vinfo_p, "w", encoding="utf-8") as vf:
                json.dump(vdata, vf, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # 3. Klasörü yuklenecek -> yuklenen taşı (YALNIZCA tüm aktif platformlar yüklendiyse)
    try:
        from channel_manager import ChannelManager
        ch_mgr = ChannelManager()
        ch = ch_mgr.get_channel(channel_id)
        need_instagram = ch and ch.get("instagram", False) and not (vdata and vdata.get("uploaded_instagram", False))
        need_tiktok = ch and ch.get("tiktok", False) and not (vdata and vdata.get("uploaded_tiktok", False))

        if not (need_instagram or need_tiktok):
            if "yuklenecek" in str(sub_folder):
                dest_parent = Path(output_dir) / channel_id / "yuklenen"
                dest_parent.mkdir(parents=True, exist_ok=True)
                dest_folder = dest_parent / sub_folder.name
                if not dest_folder.exists():
                    shutil.move(str(sub_folder), str(dest_folder))
                    print(f"[YOUTUBE-API] Tüm platformlar tamamlandı, video 'yuklenen'e taşındı: {sub_folder.name}")
        else:
            print(f"[YOUTUBE-API] Video YouTube'a yüklendi ancak diğer platformlar bekleniyor (Instagram: {need_instagram}, TikTok: {need_tiktok}). 'yuklenecek' klasöründe tutuldu.")
    except Exception as move_err:
        print(f"[YOUTUBE-API] Klasör taşıma uyarısı: {move_err}")

    return {
        "success": True,
        "video_id": upload_res.get("video_id"),
        "url": upload_res.get("url"),
        "title": title,
        "scheduled_for": scheduled_display,
        "publish_at_iso": publish_at_iso,
    }


@app.post("/api/channels/{channel_id}/plan/{row_id}/upload")
def upload_channel_planned_video_endpoint(channel_id: str, row_id: str, direct: bool = False):
    """Münferit kanal planı satırındaki videoyu akıllı zamanlama (19:00 yerel saat) ile YouTube'a yükler/planlar."""
    global _global_pending_upload
    output_dir = settings_mgr.get("output_dir", "output")
    token_file = Path("credentials") / f"{channel_id}_token.json"

    # 1. Kanala ait resmi YouTube API token'ı mevcutsa, doğrudan API üzerinden arka planda yükle
    if token_file.exists():
        try:
            from browser_uploader import find_planned_video_folder
            from youtube_uploader import YouTubeUploader
            from youtube_scheduler import calculate_channel_next_schedule_slot
            from content_planner import ContentPlanner
            import shutil
            import zoneinfo
            from datetime import timezone

            video_match = find_planned_video_folder(channel_id, row_id, output_base_dir=output_dir)
            if not video_match:
                raise HTTPException(status_code=404, detail=f"Satır #{row_id} için klasör bulunamadı.")

            video_file_str = video_match.get("video_file") or video_match.get("video_path")
            if not video_file_str or not Path(video_file_str).exists():
                raise HTTPException(status_code=404, detail=f"Satır #{row_id} için hazır video dosyası bulunamadı.")

            video_file = Path(video_file_str)
            title = video_match.get("title") or video_file.parent.name
            description = video_match.get("description", "#Shorts")
            tags = video_match.get("tags", ["Shorts"])
            thumb_file_str = video_match.get("thumbnail_file") or video_match.get("thumbnail_path")
            thumb_file = Path(thumb_file_str) if thumb_file_str and Path(thumb_file_str).exists() else None

            # Akıllı zamanlama yuvasını hesapla
            ch_mgr = ChannelManager()
            channel = ch_mgr.get_channel(channel_id) or {"channel_id": channel_id, "language": "tr"}
            planner = ContentPlanner(Path(output_dir) / channel_id)
            plan_rows = planner.get_plan()
            slot = calculate_channel_next_schedule_slot(channel, plan_rows=plan_rows)
            dt_local = slot.get("scheduled_datetime")
            publish_at_iso = None
            if dt_local:
                tz_name = slot.get("timezone", "Europe/Istanbul")
                tz = zoneinfo.ZoneInfo(tz_name)
                dt_utc = dt_local.replace(tzinfo=tz).astimezone(timezone.utc)
                publish_at_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            uploader = YouTubeUploader()
            upload_res = uploader.upload(
                channel_id=channel_id,
                video_path=str(video_file),
                title=title,
                description=description,
                tags=tags,
                category="entertainment" if ("yazan" in channel_id or "whatsapp" in channel_id) else "education",
                privacy="private" if publish_at_iso else "public",
                thumbnail_path=str(thumb_file) if thumb_file else None,
                publish_at=publish_at_iso,
            )

            # İçerik planında yüklendi işaretle
            planner.mark_as_uploaded(
                row_id,
                yayim_tarihi=slot.get("target_datetime_str", ""),
                video_url=upload_res.get("url", ""),
            )

            # Klasörü yuklenecek -> yuklenen taşı (YALNIZCA tüm aktif platformlar yüklendiyse)
            try:
                sub_folder = video_file.parent
                vinfo_file = sub_folder / "video_info.json"
                vinfo = {}
                if vinfo_file.exists():
                    try:
                        vinfo = json.loads(vinfo_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                need_instagram = channel and channel.get("instagram", False) and not vinfo.get("uploaded_instagram", False)
                need_tiktok = channel and channel.get("tiktok", False) and not vinfo.get("uploaded_tiktok", False)

                if not (need_instagram or need_tiktok):
                    if "yuklenecek" in str(sub_folder):
                        dest_parent = Path(output_dir) / channel_id / "yuklenen"
                        dest_parent.mkdir(parents=True, exist_ok=True)
                        dest_folder = dest_parent / sub_folder.name
                        if not dest_folder.exists():
                            shutil.move(str(sub_folder), str(dest_folder))
                            print(f"[API-UPLOAD] Tüm platformlar tamamlandı, video 'yuklenen'e taşındı: {sub_folder.name}")
                else:
                    print(f"[API-UPLOAD] Video YouTube'a yüklendi ancak diğer platformlar bekleniyor (Instagram: {need_instagram}, TikTok: {need_tiktok}). 'yuklenecek' klasöründe tutuldu.")
            except Exception as move_err:
                print(f"[API-UPLOAD] Klasör taşıma uyarısı: {move_err}")

            return {
                "success": True,
                "api_upload": True,
                "video_id": upload_res.get("video_id"),
                "url": upload_res.get("url"),
                "title": title,
                "scheduled_for": slot.get("display_summary") or slot.get("target_datetime_str"),
            }
        except HTTPException:
            raise
        except Exception as api_err:
            print(f"[API-UPLOAD] YouTube Data API hatası ({api_err}), fallback deneniyor...")

    # 2. Token yoksa veya API hata verdiyse tarayıcı yükleyicisine (Playwright/Studio) geç
    try:
        from browser_agent import browser_agent
        if direct:
            res = browser_agent.execute_autonomous_upload(
                channel_id=channel_id,
                row_id=row_id,
                output_base_dir=output_dir,
            )
        else:
            res = browser_agent.plan_and_execute_upload(
                channel_id=channel_id,
                row_id=row_id,
                output_base_dir=output_dir,
            )
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error"))
            
        if not direct:
            first_payload = res.get("payload") or (res.get("queue") and res["queue"][0])
            queue = res.get("queue", [])[1:] if (res.get("queue") and len(res["queue"]) > 1) else []
            _global_pending_upload = {
                "payload": first_payload,
                "queue": queue,
                "timestamp": time.time(),
            }
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube yükleme hatası: {str(e)}")


@app.post("/api/groups/{group_id}/plan/{row_id}/upload")
def upload_group_planned_video_endpoint(group_id: str, row_id: str, direct: bool = False):
    """Grup içerik planındaki satırı tüm üye kanallar için dillerine ve hedef ülkelerine özel (19:00) YouTube Studio'ya yükler/planlar."""
    global _global_pending_upload
    try:
        from browser_agent import browser_agent
        output_dir = settings_mgr.get("output_dir", "output")
        if direct:
            res = browser_agent.execute_autonomous_upload(
                group_id=group_id,
                row_id=row_id,
                output_base_dir=output_dir,
            )
        else:
            res = browser_agent.plan_and_execute_upload(
                group_id=group_id,
                row_id=row_id,
                output_base_dir=output_dir,
            )
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error"))
            
        if not direct:
            first_payload = res.get("first_payload") or res.get("payload") or (res.get("queue") and res["queue"][0])
            queue = res.get("queue", [])[1:] if (res.get("queue") and len(res["queue"]) > 1) else []
            _global_pending_upload = {
                "payload": first_payload,
                "queue": queue,
                "timestamp": time.time(),
            }
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grup YouTube yükleme hatası: {str(e)}")


@app.post("/api/groups/{group_id}/plan/{row_id}/upload-direct")
def upload_group_planned_video_direct_endpoint(group_id: str, row_id: str):
    """Eklentiye ihtiyaç duymadan doğrudan AI Tarayıcı Motoru (Playwright) ile yüklemeyi başlatır."""
    return upload_group_planned_video_endpoint(group_id=group_id, row_id=row_id, direct=True)


@app.post("/api/channels/{channel_id}/plan/{row_id}/upload-direct")
def upload_channel_planned_video_direct_endpoint(channel_id: str, row_id: str):
    """Eklentiye ihtiyaç duymadan doğrudan AI Tarayıcı Motoru (Playwright) ile yüklemeyi başlatır."""
    return upload_channel_planned_video_endpoint(channel_id=channel_id, row_id=row_id, direct=True)


@app.post("/api/channels/{channel_id}/plan/{row_id}/mark-uploaded")
def mark_channel_plan_uploaded_endpoint(channel_id: str, row_id: str, payload: dict = None):
    """Kanal planı satırını manuel olarak yüklendi işaretler."""
    from content_planner import ContentPlanner
    output_dir = settings_mgr.get("output_dir", "output")
    planner = ContentPlanner(Path(output_dir) / channel_id)
    yayim = (payload or {}).get("yayim_tarihi", "")
    video_url = (payload or {}).get("video_url", "")
    ok = planner.mark_as_uploaded(row_id, yayim_tarihi=yayim, video_url=video_url)
    if not ok:
        raise HTTPException(status_code=404, detail="Plan satırı bulunamadı.")
    return {"success": True}


@app.post("/api/groups/{group_id}/plan/{row_id}/mark-uploaded")
def mark_group_plan_uploaded_endpoint(group_id: str, row_id: str, payload: dict = None):
    """Grup planı satırını manuel olarak yüklendi işaretler."""
    from content_planner import ContentPlanner
    output_dir = settings_mgr.get("output_dir", "output")
    planner = ContentPlanner(Path(output_dir) / "groups" / group_id)
    yayim = (payload or {}).get("yayim_tarihi", "")
    video_url = (payload or {}).get("video_url", "")
    ok = planner.mark_as_uploaded(row_id, yayim_tarihi=yayim, video_url=video_url)
    if not ok:
        raise HTTPException(status_code=404, detail="Grup plan satırı bulunamadı.")
    return {"success": True}


@app.post("/api/groups/{group_id}/plan/{row_id}/gemini-prompt")
def get_group_gemini_prompt(group_id: str, row_id: str):
    """Gruptaki tüm diller için ortak çok dilli senaryo promptu hazırlar."""
    mgr = ChannelManager()
    group = mgr.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grup bulunamadı.")

    member_channels = [mgr.get_channel(cid) for cid in group.get("channel_ids", []) if mgr.get_channel(cid)]
    if not member_channels:
        raise HTTPException(status_code=400, detail="Grupta tanımlı kanal bulunamadı.")

    languages = list({ch["language"] for ch in member_channels})

    output_dir = settings_mgr.get("output_dir", "output")
    grp_dir = Path(output_dir) / "groups" / group_id
    planner = ContentPlanner(grp_dir)
    row = planner.get_row_by_id(row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Grup plan satırı bulunamadı.")

    from script_writer import get_system_prompt
    category = group.get("topic_category", "reddit_stories")
    sys_prompt = get_system_prompt(category)
    topic = row.get("konu", "")
    title = row.get("baslik", topic)

    langs_upper = ", ".join([l.upper() for l in languages])

    if category in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
        prompt_text = f"""
SEN ÇOK DİLLİ VİRAL WHATSAPP DUBLAJ & KOMEDİ SENARİSTİSİN.
Aşağıdaki konu hakkında gruptaki HER DİL ({langs_upper}) için WhatsApp mesajlaşma komedi senaryosu oluşturmalısın.

KONU: {topic}
BAŞLIK: {title}
HEDEF DİLLER: {languages}

İSLAMİ VE HELAL İÇERİK KURALI (TÜM DİLLER İÇİN KESİN VE TAVİZSİZ):
- SIFIR HARAM / SIFIR GAYRİMEŞRU İLİŞKİ: Kesinlikle sevgili, flört, aldatma, zina, gayrimeşru kız-erkek ilişkisi, küfür, argo, müstehcenlik, alkol veya kumar unsuru BULUNMAMALIDIR.
- MİZAH VE ABSÜRTLÜK: Kahkaha attıran durum komedileri, absürt bahaneler, zekice ters köşeler, aile (anne, baba, kardeş), apartman/komşuluk, esnaf/çırak, halı saha ve ev arkadaşlığı dinamikleri kullanılmalıdır.

HER DİL İÇİN KURALLAR:
1. İki kişi arasında geçen komik, ters köşe ve sürükleyici bir WhatsApp mesajlaşması yaz (contact = sol taraf, user = sağ taraf).
2. "contact_name" alanına gerçekçi ve helal bir kişi adı koy (örneğin 'Annem ❤️', 'Babam 👑', 'Hüseyin Amca 👴', 'Ev Sahibi Halil 🏢', 'Kaptan Burak ⚽', 'Roommate Dave 🍕'). Kesinlikle sevgili/flört isimleri KULLANMA.
3. "contact_avatar_prompt" ve scenes[0]["image_prompt"] alanına o kişinin yaşına ve rolüne tam uyan gerçekçi 1:1 kare avatar promptu yaz. KRİTİK YAŞ KURALI: Kişi amca, dede, dayı, teyze, nine veya yaşlı biriyse (ör. 'Hüseyin Amca') MUTLAKA 'A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish uncle with wrinkled weathered face, receding gray hair and mustache, square 1:1' yaz, KESİNLİKLE genç adam veya genç selfie yazma! Anne/Baba/Patron için olgun 48-50 yaş, arkadaş için 23-25 yaş yaz.
4. YouTube Shorts dikey 9:16 formatında, yaklaşık 20-30 saniye sürecek 7-9 adet mesajdan oluşan hızlı tempolu bir diyalog yaz.

JSON FORMATI:
Yanıtında YALNIZCA geçerli bir JSON döndür:
{{
"""
        for l in languages:
            prompt_text += f"""  "{l}": {{
    "title": "{l.upper()} dilinde ilgi çekici başlık #Shorts",
    "description": "{l.upper()} dilinde YouTube video açıklaması ve o dildeki hashtagler (ör. #{l.upper()}Shorts #WhatsApp #Viral)",
    "tags": ["{l.upper()} dilinde 6-8 etiket", "WhatsApp", "Shorts", "Viral"],
    "contact_name": "Kişi adı (ör. Annem ❤️)",
    "contact_avatar_prompt": "Age-accurate portrait prompt matching character (e.g. elderly 68yo with wrinkles/gray mustache for uncle/dede, mature 50yo for parent, young adult for friend), authentic WhatsApp profile avatar, square 1:1",
    "contact_avatar_gender": "female",
    "bgm_track": "comedy_upbeat",
    "scenes": [
      {{
        "scene_id": 1,
        "narration": "Diyalog özeti",
        "image_prompt": "Age-accurate portrait prompt matching character (e.g. elderly 68yo with wrinkles/gray mustache for uncle/dede, mature 50yo for parent, young adult for friend), authentic WhatsApp profile avatar, square 1:1"
      }}
    ],
    "messages": [
      {{"sender": "contact", "text": "İlk mesaj..."}},
      {{"sender": "user", "text": "Cevap..."}},
      {{"sender": "contact", "text": "Ters köşe / punchline..."}},
      {{"sender": "user", "text": "Tepki..."}}
    ]
  }},
"""
        prompt_text += "}\n\nLütfen hiçbir markdown veya selamlama eklemeden SADECE yukarıdaki JSON formatını döndür."
    elif category in ("reddit_stories", "reddit"):
        prompt_text = f"""
SEN ÇOK DİLLİ VİRAL REDDİT HİKAYE VE ANLATI SENARİSTİSİN.
Aşağıdaki konu hakkında gruptaki HER DİL ({langs_upper}) için KESİNTİSİZ, EKSİKSİZ ve TAM BİR HİKAYE ARKI içeren senaryolar oluşturmalısın.

KONU: {topic}
BAŞLIK: {title}
HEDEF DİLLER: {languages}

HİKAYE KURALLARI (ÇOK KRİTİK):
1. HİKAYE ASLA YARIDA KESİLMEMELİDİR:
   - "Devamı 2. partta", "to be continued", cliffhanger veya belirsiz yarım kalan sonlar KESİNLİKLE YASAKTIR.
   - Olay baştan sona tam bir bütünlükle anlatılmalı, gizem çözülmeli, yüzleşme gerçekleşmeli ve net bir sonuç/çıkarım ile bitirilmelidir.
   - İzleyici videoyu izlediğinde hikayenin tüm detaylarını ve nasıl bittiğini eksiksiz öğrenmelidir.
2. DİLE ÖZEL AÇIKLAMA VE ETİKETLER (ÇOK KRİTİK):
   - Her dilin "description" alanı KESİNLİKLE O DİLDE ({langs_upper}) yazılmalıdır; asla başka bir dil veya varsayılan Türkçe metin yazılmamalıdır!
   - Her dilin "tags" dizisindeki etiketler KESİNLİKLE O DİLDE ({langs_upper}) yazılmalıdır (ör. İngilizce kanal için İngilizce etiketler, Almanca kanal için Almanca etiketler).
3. SAHNE SAYISI VE YAPISI (HER DİLDE BİREBİR AYNI - TAM 7 VEYA 8 SAHNE):
   - TÜM DİLLERDE BİREBİR AYNI SAYIDA (TAM 7 VEYA 8 SAHNE) OLMALIDIR.
   - Sahne 1 (Hook / Giriş): Reddit soru kartı metnini ve ilk merak uyandıran cümleyi söyle ("image_prompt": "reddit_card_hook").
   - Sahne 2-3 (Gelişme / Olayın Başlangıcı): Olayın arka planı, ilk tuhaflık veya şüphe ("image_prompt": "asmr_satisfying_background").
   - Sahne 4-5 (Gerilim & Doruk Noktası / Yüzleşme): Olayın tırmanışı, kritik an, gerilim zirvesi ve yüzleşme ("image_prompt": "asmr_satisfying_background").
   - Sahne 6-7 (Çözülme / Gerçeğin Ortaya Çıkışı): Gizemin veya sırrın tamamen açığa çıkması, ne olduğu net olarak anlatılır ("image_prompt": "asmr_satisfying_background").
   - Son Sahne (Nihai Sonuç & Kapanış): Olaydan sonra ne oldu, son durum, ders veya vurucu kapanış cümlesi ("image_prompt": "asmr_satisfying_background").
4. ANLATIM UZUNLUĞU VE DOĞALLIĞI:
   - Her dilde her sahne 25-35 kelimelik akıcı, sürükleyici, birinci tekil şahıs ("ben") ağzından konuşma diliyle yazılmalıdır.
   - Toplam video süresi 120-160 saniye sürecek zenginlikte olmalıdır.

JSON FORMATI:
Yanıtında YALNIZCA geçerli bir JSON döndür:
{{
"""
        for l in languages:
            prompt_text += f"""  "{l}": {{
    "title": "{l.upper()} dilinde merak uyandırıcı viral başlık #Shorts",
    "description": "{l.upper()} dilinde 1-2 paragraflık çekici YouTube video açıklaması ve o dildeki hashtagler (ör. #{l.upper()}Shorts #Reddit #RedditStories #AskReddit)",
    "tags": ["{l.upper()} dilinde etiket 1", "{l.upper()} dilinde etiket 2", "Reddit", "RedditStories", "Shorts", "Viral"],
    "question": "{l.upper()} dilinde Reddit soru kartı metni (ör. Hayatınızda tamamen tesadüfen öğrendiğiniz en korkunç sır neydi?)",
    "subreddit": "r/AskReddit",
    "author": "u/StoryTeller99",
    "upvotes": "38.4k",
    "scenes": [
      {{
        "scene_id": 1,
        "narration": "{l.upper()} dilinde 1. sahne (Reddit sorusu ve çarpıcı giriş)...",
        "image_prompt": "reddit_card_hook",
        "emotion": "dramatic"
      }},
      {{
        "scene_id": 2,
        "narration": "{l.upper()} dilinde 2. sahne (Olayın başlangıcı)...",
        "image_prompt": "asmr_satisfying_background",
        "emotion": "mysterious"
      }},
      {{
        "scene_id": 3,
        "narration": "{l.upper()} dilinde 3. sahne (Şüphenin büyümesi)...",
        "image_prompt": "asmr_satisfying_background",
        "emotion": "mysterious"
      }},
      {{
        "scene_id": 4,
        "narration": "{l.upper()} dilinde 4. sahne (Tırmanma ve yüzleşme anı)...",
        "image_prompt": "asmr_satisfying_background",
        "emotion": "shocked"
      }},
      {{
        "scene_id": 5,
        "narration": "{l.upper()} dilinde 5. sahne (Doruk noktası, zirve gerilim)...",
        "image_prompt": "asmr_satisfying_background",
        "emotion": "shocked"
      }},
      {{
        "scene_id": 6,
        "narration": "{l.upper()} dilinde 6. sahne (Sırrın çözülmesi, gerçeğin tam ortaya çıkışı)...",
        "image_prompt": "asmr_satisfying_background",
        "emotion": "dramatic"
      }},
      {{
        "scene_id": 7,
        "narration": "{l.upper()} dilinde 7. sahne (Nihai sonuç, olaydan sonra ne olduğu ve tam kapanış)...",
        "image_prompt": "asmr_satisfying_background",
        "emotion": "neutral"
      }}
    ]
  }},
"""
        prompt_text += "}\n\nLütfen hiçbir markdown selamlama veya açıklama eklemeden SADECE yukarıdaki JSON formatını döndür."
    else:
        prompt_text = f"""
SEN ÇOK DİLLİ VİRAL İÇERİK SENARİSTİSİN.
Aşağıdaki konu hakkında gruptaki HER DİL ({langs_upper}) için birebir uyumlu senaryolar oluşturmalısın.

KONU: {topic}
BAŞLIK: {title}
HEDEF DİLLER: {languages}

HER DİL İÇİN KURALLAR:
1. Sahne sayısı ve anlatılan olayın aşamaları TÜM DİLLERDE BİREBİR AYNI olmalıdır (ör. 6-8 sahne).
2. Her dilin senaryosu, "description" (açıklama) ve "tags" (etiketler) KESİNLİKLE O DİLİN ({langs_upper}) doğal diline göre yazılmalıdır.
3. YouTube Shorts dikey 9:16 formatında, 120-180 saniye sürecek detaylı ve sürükleyici bir anlatım oluştur.

JSON FORMATI:
Yanıtında YALNIZCA geçerli bir JSON döndür. Kök nesnede her dilin kodu bir anahtar olmalıdır:
{{
"""
        for l in languages:
            prompt_text += f"""  "{l}": {{
    "title": "{l.upper()} dilinde ilgi çekici başlık",
    "description": "{l.upper()} dilinde YouTube video açıklaması ve o dildeki hashtagler",
    "tags": ["{l.upper()} dilinde etiket 1", "{l.upper()} dilinde etiket 2", "Shorts", "Viral"],
    "question": "{l.upper()} dilinde soru kartı metni (Reddit için)",
    "subreddit": "r/AskReddit",
    "author": "u/StoryTeller99",
    "upvotes": "45.2k",
    "scenes": [
      {{
        "scene_id": 1,
        "narration": "{l.upper()} dilinde 1. sahne anlatımı...",
        "image_prompt": "reddit_card_hook",
        "emotion": "dramatic"
      }},
      {{
        "scene_id": 2,
        "narration": "{l.upper()} dilinde 2. sahne anlatımı...",
        "image_prompt": "asmr_satisfying_background",
        "emotion": "mysterious"
      }}
    ]
  }},
"""
        prompt_text += "}\n\nLütfen hiçbir markdown selamlama veya açıklama eklemeden SADECE yukarıdaki JSON formatını döndür."

    combined_prompt = f"{sys_prompt}\n\nTask:\n{prompt_text}"

    return {
        "success": True,
        "prompt": combined_prompt,
        "category": category,
        "languages": languages,
        "group_id": group_id,
        "group_name": group.get("name"),
        "topic": topic,
        "shorts_mode": True,
    }


@app.post("/api/groups/{group_id}/plan/{row_id}/produce-gemini")
def produce_group_planned_video_gemini(
    group_id: str,
    row_id: str,
    payload: GeminiProducePayload,
    background_tasks: BackgroundTasks
):
    """Gruptaki tüm diller için çok dilli video üretimini başlatır."""
    mgr = ChannelManager()
    group = mgr.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grup bulunamadı.")

    exec_id = f"exec_grp_{group_id}_gemini_{row_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    target_env = (payload.target_env or "local").lower()
    auto_yt = bool(payload.auto_youtube_upload)
    auto_sync = bool(payload.auto_sync_mac if payload.auto_sync_mac is not None else True)

    executions[exec_id] = {
        "group_id": group_id,
        "channel_id": f"group_{group_id}",
        "status": "pending",
        "message": f"Grup '{group.get('name')}' için {'Oracle Cloud sunucusunda' if target_env == 'remote' else 'lokalde'} çok dilli video üretimi başlatılıyor...",
        "timestamp": datetime.now().isoformat(),
        "target_env": target_env,
        "auto_youtube_upload": auto_yt,
        "auto_sync_mac": auto_sync
    }

    background_tasks.add_task(
        run_gemini_group_web_automation_task,
        group_id,
        exec_id,
        row_id,
        payload.script,
        payload.images,
        target_env,
        auto_yt,
        auto_sync
    )
    return {"exec_id": exec_id, "status": "pending", "target_env": target_env}


@app.get("/api/audio-library")
def get_audio_library():
    """Ses kitaplığındaki tüm parçaları döndürür."""
    from audio_library import TRACKS
    return {"success": True, "tracks": TRACKS}

class UpdateMusicPayload(BaseModel):
    secilen_muzik: str

@app.put("/api/channels/{channel_id}/plan/{row_id}/music")
def update_plan_row_music(channel_id: str, row_id: str, payload: UpdateMusicPayload):
    """İçerik planındaki satırın fon müziğini günceller."""
    from content_planner import ContentPlanner
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    
    if not channel_dir.exists():
        raise HTTPException(status_code=404, detail="Kanal klasörü bulunamadı.")
        
    planner = ContentPlanner(channel_dir)
    success = planner.update_music(row_id, payload.secilen_muzik)
    if not success:
        raise HTTPException(status_code=404, detail="Plan satırı bulunamadı.")
        
    return {"success": True}


@app.get("/api/channels/{channel_id}/plan/download")
def download_channel_plan(channel_id: str):
    """Kanalın plan CSV dosyasını indirir."""
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    if not planner.plan_exists():
        raise HTTPException(status_code=404, detail="Plan bulunamadı.")
    return FileResponse(
        path=str(planner.plan_path),
        media_type="text/csv",
        filename=f"{channel_id}_icerik_plani.csv"
    )


@app.get("/api/channels/{channel_id}/mind-map")
def get_channel_mind_map(channel_id: str):
    """Kanalın zihin haritasını listeler. Yoksa veya boşsa otomatik bootstrap eder."""
    from mind_map import MindMapManager
    from content_planner import ContentPlanner
    
    mgr = ChannelManager()
    ch = mgr.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    
    mm_mgr = MindMapManager(channel_dir)
    planner = ContentPlanner(channel_dir)
    
    try:
        writer = _get_configured_script_writer()
    except Exception:
        writer = None
        
    try:
        data = mm_mgr.bootstrap_or_load(writer=writer, channel_config=ch)
        return {"success": True, "mind_map": data}
    except Exception as e:
        return {"success": False, "error": str(e), "mind_map": {"themes": {}}}


@app.post("/api/channels/{channel_id}/mind-map/sync")
def sync_channel_mind_map(channel_id: str):
    """Kanalın zihin haritasını CSV dosyasından sıfırdan derler."""
    from mind_map import MindMapManager
    from content_planner import ContentPlanner
    
    mgr = ChannelManager()
    ch = mgr.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    
    planner = ContentPlanner(channel_dir)
    if not planner.plan_exists():
        raise HTTPException(status_code=400, detail="Önce içerik planı oluşturulmalıdır.")
        
    try:
        writer = _get_configured_script_writer()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Yapay zeka başlatılamadı: {str(e)}")
    
    mm_mgr = MindMapManager(channel_dir)
    try:
        category = ch.get("topic_category", "space")
        data = mm_mgr.sync_from_csv(writer, planner, category=category, channel_config=ch)
        return {"success": True, "mind_map": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Zihin haritası senkronizasyon hatası: {str(e)}")
def clean_ideas_batch_with_ai(writer, ideas: list) -> list[dict]:
    """Yapay zeka ile tüm fikirleri tek bir batch halinde temizler ve optimize eder."""
    if not ideas:
        return []
        
    ideas_formatted = []
    for idx, idea in enumerate(ideas):
        desc = idea.description.strip() if idea.description else ""
        desc_str = desc if desc else "Açıklama bulunamadı."
        ideas_formatted.append(f"""--- FİKİR #{idx+1} ---
- Başlık: {idea.title}
- Kategori: {idea.topic}
- Açıklama: {desc_str}""")
        
    ideas_block = "\n\n".join(ideas_formatted)
    
    prompt = f"""
Sana YouTube Studio'dan kazınmış içerik fikirleri listesi veriyorum. Görevin bu fikirleri süzüp temizlemek, gereksiz/promosyonel kelimeleri ayıklamak ve video üretim sistemimiz için en yüksek retention (izleyici tutma) ve arama performansı sağlayan "konu" (topic description), "baslik" (polished title) ve "anahtar_kelimeler" (searchable keywords) alanlarını üretmektir.

Fikirler Listesi:
{ideas_block}

Format ve Algoritma Kalite Kuralları:
1. Her fikir için:
   - "konu": Videonun ana temasını ve merak uyandıran çatışmasını anlatan, gereksiz giriş süslemelerinden arındırılmış, 2-3 cümlelik net ve zengin bir özet.
   - "baslik": Dikkat çekici, tıklama oranı yüksek (CTR odaklı), temiz bir YouTube video başlığı (içinde '#Shorts' olmasın, yanıltıcı spam clickbait olmasın).
   - "anahtar_kelimeler": Konuyla birebir alakalı, izleyicilerin doğrudan YouTube arama çubuğuna yazdığı en önemli 4-6 adet aranabilir anahtar kelimeyi virgülle ayrılmış olarak yaz. KESİNLİKLE 'shorts', 'viral', 'keşfet', 'fyp', 'trend' gibi jenerik/spam kelimeler KULLANMA.

Yanıtını SADECE aşağıdaki JSON formatında bir liste olarak ver. Başka hiçbir açıklama veya metin ekleme. JSON yapısı şu şekilde olmalıdır:
[
  {{
    "konu": "temizlenmiş açıklama metni...",
    "baslik": "optimize edilmiş başlık...",
    "anahtar_kelimeler": "özel_anahtar1, özel_anahtar2, ..."
  }},
  ...
]
"""
    try:
        res_text = writer.run_prompt(prompt)
        import json
        import re
        match = re.search(r'\[\s*\{.*\}\s*\]', res_text, re.DOTALL)
        if match:
            cleaned_list = json.loads(match.group(0))
            if isinstance(cleaned_list, list) and len(cleaned_list) == len(ideas):
                return cleaned_list
    except Exception as e:
        print(f"[SERVER] Batch fikir temizleme yapay zeka hatası: {e}")
        
    # Fallback if batch parsing fails
    result = []
    for idea in ideas:
        desc = idea.description.strip() if idea.description else ""
        result.append({
            "konu": desc if desc else idea.topic,
            "baslik": idea.title,
            "anahtar_kelimeler": idea.topic
        })
    return result


@app.post("/api/channels/{channel_id}/plan/ideas")
def add_scraped_ideas(channel_id: str, payload: ScrapedIdeasPayload):
    """YouTube Studio'dan kazınan fikirleri kanalın içerik planına ekler."""
    mgr = ChannelManager()
    ch = mgr.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    # Filtrele: Sadece başlık mevcut planlarda yoksa ekle (tekrarlanmasın)
    existing = planner.get_plan()
    filtered_ideas = [idea for idea in payload.ideas if not any(r.get("baslik") == idea.title for r in existing)]
    
    if not filtered_ideas:
        return {"success": True, "added_count": 0, "message": "Hiç yeni fikir eklenmedi (hepsi zaten mevcut)."}
        
    # AI nesnesi oluştur
    provider = settings_mgr.get("ai_provider", "claude")
    api_key = settings_mgr.get("anthropic_api_key") if provider == "claude" else settings_mgr.get("gemini_api_key")
    ai_model = settings_mgr.get(f"{provider}_model", "")
    from script_writer import ScriptWriter
    writer = ScriptWriter(
        provider=provider,
        api_key=api_key,
        model=ai_model,
        ollama_url=settings_mgr.get("ollama_url", "http://localhost:11434"),
        lmstudio_url=settings_mgr.get("lmstudio_url", "http://localhost:1234/v1"),
    )
    
    # Tüm fikirleri tek bir yapay zeka çağrısıyla süzüp temizle
    cleaned_ideas = clean_ideas_batch_with_ai(writer, filtered_ideas)
    
    new_topics = []
    from audio_library import get_recommendation
    
    skipped_count = 0
    added_titles = []
    skipped_titles = []
    
    for idea, cleaned in zip(filtered_ideas, cleaned_ideas):
        cleaned_baslik = cleaned["baslik"].strip()
        cleaned_konu = cleaned["konu"].strip()
        
        # Hem başlık hem de konu bazında mükerrerlik kontrolü (case-insensitive & trimmed)
        is_duplicate = False
        import re
        norm_cleaned_baslik = re.sub(r'[^\w\s]', '', cleaned_baslik.lower()).strip()
        norm_cleaned_baslik = re.sub(r'\s+', ' ', norm_cleaned_baslik)
        
        for r in existing:
            ext_baslik = (r.get("baslik") or "").strip()
            ext_konu = (r.get("konu") or "").strip()
            
            # Birebir eşleşme
            if cleaned_baslik.lower() == ext_baslik.lower() or cleaned_konu.lower() == ext_konu.lower():
                is_duplicate = True
                break
                
            # Noktalamadan arındırılmış başlık eşleşmesi
            norm_ext_baslik = re.sub(r'[^\w\s]', '', ext_baslik.lower()).strip()
            norm_ext_baslik = re.sub(r'\s+', ' ', norm_ext_baslik)
            if norm_cleaned_baslik == norm_ext_baslik:
                is_duplicate = True
                break
                
            # Alt dize/içerme eşleşmesi (kısmi çakışmaları engellemek için)
            if len(norm_cleaned_baslik) > 10 and len(norm_ext_baslik) > 10:
                if norm_cleaned_baslik in norm_ext_baslik or norm_ext_baslik in norm_cleaned_baslik:
                    is_duplicate = True
                    break
                    
        if is_duplicate:
            print(f"[SERVER] Fikir atlandı (Mevcut konu/başlık ile çakışıyor): {cleaned_baslik}")
            skipped_count += 1
            skipped_titles.append(cleaned_baslik)
            continue
            
        rec_music = get_recommendation(idea.topic, cleaned_baslik)
        new_topics.append({
            "konu": cleaned_konu,
            "baslik": cleaned_baslik,
            "anahtar_kelimeler": [k.strip() for k in cleaned["anahtar_kelimeler"].split(",") if k.strip()],
            "secilen_muzik": rec_music,
            "notlar": "YouTube Studio İlham Kaynağı"
        })
        added_titles.append(cleaned_baslik)
        
    added_rows = planner.add_topics(new_topics) if new_topics else []
    
    # Zihin haritası varsa yeni konularla güncelle
    try:
        from mind_map import MindMapManager
        mm_mgr = MindMapManager(channel_dir)
        if mm_mgr.exists() and added_rows:
            ch_category = ch.get("topic_category", "space") if ch else "space"
            mm_mgr.update_with_new_topics(writer, added_rows, category=ch_category, channel_config=ch)
    except Exception as e:
        print(f"[SERVER] Zihin haritası güncellenirken hata: {e}")
        
    pre_skipped_titles = [idea.title for idea in payload.ideas if not any(r.get("baslik") == idea.title for r in existing)]
    actual_pre_skipped = [idea.title for idea in payload.ideas if idea.title not in [f.title for f in filtered_ideas]]
        
    return {
        "success": True, 
        "added_count": len(added_rows), 
        "skipped_count": skipped_count + len(actual_pre_skipped),
        "added_titles": added_titles,
        "skipped_titles": skipped_titles + actual_pre_skipped,
        "topics": added_rows
    }


@app.post("/api/channels/{channel_id}/plan/import")
def import_planned_topics(channel_id: str, payload: ImportTopicsRequest):
    """Gemini web otomasyonundan gelen planlanmış konuları doğrudan içerik planına ve zihin haritasına ekler."""
    mgr = ChannelManager()
    ch = mgr.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    # Mevcut planı al
    existing = planner.get_plan()
    existing_titles = {r.get("baslik", "").strip().lower() for r in existing if r.get("baslik")}
    
    # Eşleşmeyenleri filtrele (mükerrer olmasın)
    new_items = []
    for item in payload.topics:
        title = item.baslik or item.title or item.konu or item.topic or item.name
        instructions = item.yonergeler or item.instructions or item.yönerge or item.instruction or item.description or ""
        
        if not title or not title.strip():
            continue
            
        title_val = title.strip()
        title_clean = title_val.lower()
        
        if title_clean not in existing_titles:
            new_items.append({
                "konu": title_val,  # Konuyu başlık ile aynı yapıyoruz
                "baslik": title_val,
                "notlar": instructions.strip()  # Yönergeleri notlar sütununa kaydediyoruz
            })
            
    if not new_items:
        return {"success": True, "added_count": 0, "message": "Eklenen yeni konu yok (hepsi zaten mevcut veya alanlar eşleşmedi)."}
        
    # Planlayıcıya ekle
    added_rows = planner.add_topics(new_items)
    
    # Zihin haritasını yapay zeka olmadan güncelle
    try:
        from mind_map import MindMapManager
        mm_mgr = MindMapManager(channel_dir)
        if mm_mgr.exists():
            mind_map = mm_mgr.load()
            nodes = mind_map.get("nodes", [])
            existing_ids = {n.get("id") for n in nodes}
            
            # Root node bul veya oluştur
            root_id = "root"
            root_node = next((n for n in nodes if n.get("type") == "root"), None)
            if not root_node and nodes:
                root_node = nodes[0]
                root_id = root_node.get("id")
            elif not root_node:
                root_node = {"id": "root", "topic": ch.get("name", "Channel"), "type": "root", "color": "#7c6ef2"}
                nodes.append(root_node)
                
            for row in added_rows:
                node_id = f"node_{row['id']}"
                if node_id not in existing_ids:
                    nodes.append({
                        "id": node_id,
                        "parent": root_id,
                        "topic": row["baslik"],
                        "type": "topic",
                        "color": "#10b981",
                        "instructions": row.get("notlar", "")
                    })
            mind_map["nodes"] = nodes
            mm_mgr.save(mind_map)
    except Exception as e:
        print(f"[IMPORT] Zihin haritası güncellenirken hata: {e}")
        
    return {"success": True, "added_count": len(added_rows), "topics": added_rows}

@app.post("/api/channels/{channel_id}/plan/sync")
def sync_channel_plan(channel_id: str):
    """Kanalın içerik planını yuklenecek/yuklenen klasörlerindeki videolar ile karşılaştırıp durumlarını günceller."""
    mgr = ChannelManager()
    ch = mgr.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    # 1. Klasörleri tara ve plan_id'leri tespit et
    produced_ids = set()
    inprogress_ids = set()
    
    # Yeni yapıyı tara: output/<channel_id>/yuklenecek/ ve output/<channel_id>/yuklenen/
    for category in ["yuklenecek", "yuklenen"]:
        cat_dir = channel_dir / category
        if cat_dir.exists() and cat_dir.is_dir():
            for folder in cat_dir.iterdir():
                if not folder.is_dir() or folder.name.startswith("."):
                    continue
                
                # Metadata kontrol et
                p_id = None
                meta_json = folder / "metadata.json"
                if meta_json.exists():
                    try:
                        meta_data = json.loads(meta_json.read_text(encoding="utf-8"))
                        p_id = str(meta_data.get("plan_id", "")).strip()
                    except Exception:
                        pass
                
                # Klasör adından row_id tahmin et (örn: 0016_...)
                if not p_id:
                    try:
                        parts = folder.name.split("_")
                        if parts[0].isdigit() and len(parts[0]) == 4:
                            p_id = str(int(parts[0])).strip()
                    except Exception:
                        pass
                        
                if p_id:
                    video_file = folder / "final.mp4"
                    if video_file.exists():
                        produced_ids.add(p_id)
                    else:
                        inprogress_ids.add(p_id)
                        
                # Uzun videonun altındaki alt Shorts klasörlerini (shorts_*) tara
                for subfolder in folder.iterdir():
                    if subfolder.is_dir() and subfolder.name.startswith("shorts_"):
                        sub_p_id = None
                        sub_meta_json = subfolder / "metadata.json"
                        if sub_meta_json.exists():
                            try:
                                sub_meta_data = json.loads(sub_meta_json.read_text(encoding="utf-8"))
                                sub_p_id = str(sub_meta_data.get("plan_id", "")).strip()
                            except Exception:
                                pass
                        
                        if sub_p_id:
                            sub_video_file = subfolder / "final.mp4"
                            if sub_video_file.exists():
                                produced_ids.add(sub_p_id)
                            else:
                                inprogress_ids.add(sub_p_id)
                                
    # output/<channel_id>/ altındaki doğrudan klasörleri de tara (eski veya özel yapılar)
    for folder in channel_dir.iterdir():
        if not folder.is_dir() or folder.name.startswith(".") or folder.name in ["yuklenecek", "yuklenen"]:
            continue
        
        p_id = None
        meta_json = folder / "metadata.json"
        if meta_json.exists():
            try:
                meta_data = json.loads(meta_json.read_text(encoding="utf-8"))
                p_id = str(meta_data.get("plan_id", "")).strip()
            except Exception:
                pass
        
        if not p_id:
            try:
                parts = folder.name.split("_")
                if parts[0].isdigit() and len(parts[0]) == 4:
                    p_id = str(int(parts[0])).strip()
            except Exception:
                pass
                
        if p_id:
            video_file = folder / "final.mp4"
            if video_file.exists():
                produced_ids.add(p_id)
            else:
                inprogress_ids.add(p_id)
                                
    # 2. Plan CSV'sini oku ve güncelle
    rows = planner._read_all()
    updated_to_produced = []
    updated_to_unproduced = []
    
    has_changes = False
    for row in rows:
        row_id = str(row.get("id", "")).strip()
        current_status = row.get("uretildi", "Hayır").strip().lower() in ("evet", "yes", "true", "1")
        
        # Eğer video üretilmişse ve şu an "Hayır" ise
        if row_id in produced_ids:
            if not current_status:
                row["uretildi"] = "Evet"
                if not row.get("uretim_tarihi"):
                    row["uretim_tarihi"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated_to_produced.append(row_id)
                has_changes = True
        # Eğer video yarım kalmışsa (klasör var ama final.mp4 yok) ve şu an "Evet" ise
        elif row_id in inprogress_ids:
            if current_status:
                row["uretildi"] = "Hayır"
                row["uretim_tarihi"] = ""
                updated_to_unproduced.append(row_id)
                has_changes = True
                
    if has_changes:
        planner._write_all(rows)
        
    return {
        "success": True,
        "updated_to_produced": updated_to_produced,
        "updated_to_unproduced": updated_to_unproduced,
        "produced_ids_found": list(produced_ids),
        "inprogress_ids_found": list(inprogress_ids)
    }

@app.post("/api/channels/{channel_id}/plan/{row_id}/produce")
def mark_row_as_produced(channel_id: str, row_id: str):
    """Plan tablosundaki satırı üretildi olarak işaretler."""
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    success = planner.mark_as_produced(row_id)
    if not success:
        raise HTTPException(status_code=404, detail="Satır bulunamadı.")
    return {"success": True}


@app.delete("/api/channels/{channel_id}/plan/{row_id}")
def delete_planned_row(channel_id: str, row_id: str):
    """Plan tablosundaki satırı tamamen siler."""
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    # Silmeden önce başlığı alalım ki zihin haritasından da silebilelim
    row = planner.get_row_by_id(row_id)
    title_to_remove = None
    if row:
        title_to_remove = row.get("baslik") or row.get("konu")
        
    success = planner.delete_topic(row_id)
    if not success:
        raise HTTPException(status_code=404, detail="Satır bulunamadı veya silinemedi.")
        
    # Zihin haritasından yerel olarak (AI çağırmadan) kaldıralım
    if title_to_remove:
        try:
            from mind_map import MindMapManager
            mm_mgr = MindMapManager(channel_dir)
            if mm_mgr.exists():
                mm_mgr.remove_titles([title_to_remove])
        except Exception as e:
            print(f"[SERVER] Zihin haritasından silinirken hata: {e}")
        
    return {"success": True}


@app.post("/api/channels/{channel_id}/plan/batch-delete")
def batch_delete_planned_rows(channel_id: str, payload: dict):
    """Seçilen birden fazla satırı tek seferde hızlıca siler."""
    row_ids = payload.get("row_ids", [])
    if not row_ids:
        raise HTTPException(status_code=400, detail="row_ids parametresi zorunludur.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    titles_to_remove = []
    
    # 1. Silinecek başlıkları topla
    for r_id in row_ids:
        row = planner.get_row_by_id(r_id)
        if row:
            title = row.get("baslik") or row.get("konu")
            if title:
                titles_to_remove.append(title)
                
    # 2. Toplu silme işlemini yap (tek I/O)
    deleted_count = planner.delete_topics(row_ids)
                
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Seçilen satırlardan hiçbiri silinemedi.")
        
    # Zihin haritasından toplu olarak kaldıralım
    if titles_to_remove:
        try:
            from mind_map import MindMapManager
            mm_mgr = MindMapManager(channel_dir)
            if mm_mgr.exists():
                mm_mgr.remove_titles(titles_to_remove)
        except Exception as e:
            print(f"[SERVER] Toplu silmede zihin haritasından kaldırılırken hata: {e}")
            
    return {"success": True, "deleted_count": deleted_count}


@app.post("/api/channels/{channel_id}/chat")
def channel_ai_chat(channel_id: str, payload: dict):
    """
    Kanal odaklı yapay zeka sohbeti.
    Yerel (Ollama, LM Studio) ve bulut (Gemini, Claude) modelleri destekler.
    İnternet arama grounding ve kanal zihin haritası/planı yönetebilen RAG yapısına sahiptir.
    """
    message = payload.get("message")
    history = payload.get("history", []) # [{"role": "user"/"model", "content": "..."}]
    
    if not message:
        raise HTTPException(status_code=400, detail="Mesaj boş olamaz.")
        
    mgr = ChannelManager()
    ch = mgr.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    
    provider = settings_mgr.get("ai_provider", "claude")
    api_key = settings_mgr.get("anthropic_api_key") if provider == "claude" else settings_mgr.get("gemini_api_key")
    ai_model = settings_mgr.get(f"{provider}_model", "")
    
    # Yerel modeller için anahtar zorunluluğu yok, bulut modelleri için kontrol et
    if provider in ["claude", "gemini"] and not api_key:
        raise HTTPException(
            status_code=400, 
            detail=f"{provider.upper()} API Anahtarı eksik. Ayarlar menüsünden API Key girin veya yerel modele (Ollama/LM Studio) geçin."
        )
        
    from script_writer import ScriptWriter
    writer = ScriptWriter(
        provider=provider,
        api_key=api_key,
        model=ai_model,
        ollama_url=settings_mgr.get("ollama_url", "http://localhost:11434"),
        lmstudio_url=settings_mgr.get("lmstudio_url", "http://localhost:1234/v1"),
    )
    
    # ── Helper Tools ──
    def get_youtube_video_details(url_or_id: str) -> str:
        video_id = url_or_id.strip()
        if "youtube.com" in video_id or "youtu.be" in video_id:
            url = video_id
        else:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
        try:
            import urllib.request
            import urllib.parse
            oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json"
            req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                return f"Video Title: {data.get('title')}\nAuthor: {data.get('author_name')}\nProvider: {data.get('provider_name')}"
        except Exception as e:
            return f"Error fetching YouTube video details: {str(e)}"

    def web_search(query: str) -> str:
        import urllib.request
        import urllib.parse
        import re
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode('utf-8', errors='ignore')
                results = []
                links = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
                titles = re.findall(r'<a class="result__url"[^>]*>(.*?)</a>', html, re.DOTALL)
                
                for t, l in zip(titles[:4], links[:4]):
                    clean_t = re.sub(r'<[^>]*>', '', t).strip()
                    clean_l = re.sub(r'<[^>]*>', '', l).strip()
                    results.append(f"- {clean_t}: {clean_l}")
                    
                if results:
                    return "\n".join(results)
                return "No search results found."
        except Exception as e:
            return f"Search error: {str(e)}"

    # ── Context Enrichment (YouTube Details + Web Search RAG) ──
    import re
    youtube_urls = re.findall(r'(https?://(?:www\.)?youtu(?:be\.com|\.be)/(?:watch\?v=)?([a-zA-Z0-9_-]{11}))', message)
    video_contexts = []
    for url, video_id in youtube_urls:
        details = get_youtube_video_details(video_id)
        video_contexts.append(f"YouTube Video Detayları ({url}):\n{details}")
        
    search_contexts = []
    if any(k in message.lower() for k in ["ara", "trend", "nedir", "search", "haber", "gündem", "bilgi"]):
        search_query = message
        search_res = web_search(search_query)
        search_contexts.append(f"İnternet Arama Sonuçları (Konu: '{search_query}'):\n{search_res}")
        
    context_prefix = ""
    if video_contexts:
        context_prefix += "\n\n".join(video_contexts) + "\n\n"
    if search_contexts:
        context_prefix += "\n\n".join(search_contexts) + "\n\n"
        
    enriched_message = message
    if context_prefix:
        enriched_message = f"[GÜNCEL BİLGİ/ARAMA VERİLERİ]\n{context_prefix}[KULLANICI MESAJI]\n{message}"

    # ── Load local files for context ──
    from mind_map import MindMapManager
    from content_planner import ContentPlanner
    mm_mgr = MindMapManager(channel_dir)
    planner = ContentPlanner(channel_dir)
    
    current_mind_map = json.dumps(mm_mgr.load(), ensure_ascii=False)
    current_plan = json.dumps(planner.get_plan()[:25], ensure_ascii=False)
    
    system_instruction = (
        f"You are 'Kanal Zeka AI', a senior YouTube content growth strategist, channel advisor, and autonomous optimizer for the channel named '{ch.get('name', 'Bilinmeyen Kanal')}' (ID: {channel_id}, Category: {ch.get('topic_category', 'space')}, Language: {ch.get('language', 'tr')}).\n\n"
        f"Current Hierarchical Mind Map Themes:\n{current_mind_map}\n\n"
        f"Current Content Plan Calendar (Partial):\n{current_plan}\n\n"
        "Your Goals:\n"
        "1. Answer user strategy questions, analyze trending topics, and provide actionable strategic recommendations in Turkish.\n"
        "2. Help the user plan new content.\n\n"
        "HOW TO PERFORM ACTIONS:\n"
        "If you want to add new video topics to the channel's planner, output a JSON block at the very end of your response starting with 'ACTION_JSON:' like this:\n"
        "ACTION_JSON: {\"action\": \"add_topics\", \"topics\": [{\"konu\": \"topic details\", \"baslik\": \"video title\", \"anahtar_kelimeler\": \"keywords\"}]}\n"
        "If you want to update the channel's mind map themes, output a JSON block at the very end of your response like this:\n"
        "ACTION_JSON: {\"action\": \"update_mind_map\", \"themes\": {\"Theme Name\": [\"Topic 1\", \"Topic 2\"]}}\n"
        "Do not include any extra text after the ACTION_JSON line. Always respond in Turkish."
    )
    
    # Construct conversation prompt from history
    conversation_history = ""
    for h in history:
        role_label = "Kullanıcı" if h.get("role") == "user" else "Yapay Zeka"
        conversation_history += f"{role_label}: {h.get('content')}\n"
        
    user_prompt = f"{conversation_history}Kullanıcı: {enriched_message}\nYapay Zeka:"
    
    try:
        raw_response = writer.run_prompt(system_instruction, user_prompt)
        
        # ── Parse and execute JSON actions ──
        action_message = ""
        response_text = raw_response
        if "ACTION_JSON:" in raw_response:
            parts = raw_response.split("ACTION_JSON:", 1)
            response_text = parts[0].strip()
            json_str = parts[1].strip()
            try:
                json_str = re.sub(r'^```json\s*|```$', '', json_str, flags=re.MULTILINE).strip()
                action_data = json.loads(json_str)
                action = action_data.get("action")
                if action == "add_topics":
                    topics = action_data.get("topics", [])
                    added = planner.add_topics(topics)
                    category = ch.get("topic_category", "space")
                    mm_mgr.sync_from_csv(writer, planner, category=category, channel_config=ch)
                    action_message = f"\n\n*(Sistem: Yapay zeka talebiyle {len(added)} adet yeni konu içerik planına eklendi ve zihin haritası senkronize edildi.)*"
                elif action == "update_mind_map":
                    themes = action_data.get("themes", {})
                    mm_mgr.save({"themes": themes})
                    action_message = "\n\n*(Sistem: Yapay zeka talebiyle zihin haritası kategorileri güncellendi.)*"
            except Exception as e:
                print(f"[ACTION ERROR] {str(e)}")
                action_message = f"\n\n*(Sistem Hatası: Yapay zeka eylemi gerçekleştirilemedi: {str(e)})*"
                
        final_response = response_text + action_message
        
        new_history = history + [
            {"role": "user", "content": message},
            {"role": "model", "content": final_response}
        ]
        
        return {
            "success": True,
            "response": final_response,
            "history": new_history
        }
    except Exception as e:
        print(f"[CHAT ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sohbet hatası: {str(e)}")


def _get_video_segments_and_audio(folder_path: Path) -> tuple[list[dict], str]:
    info_file = folder_path / "video_info.json"
    meta_file = folder_path / "metadata.json"
    
    # Locate audio file (final.mp4 uses narration.wav or narration.mp3)
    audio_path = ""
    for ext in ["wav", "mp3"]:
        p = folder_path / f"narration.{ext}"
        if p.exists():
            audio_path = str(p)
            break
            
    # Try to load from video_info.json first
    if info_file.exists():
        try:
            info = json.loads(info_file.read_text(encoding="utf-8"))
            if "segments" in info and info["segments"]:
                # Correct image paths in case folder was moved
                segments = info["segments"]
                # Skip fallback empty single segment to allow proper reconstruction
                first_seg = segments[0] if segments else {}
                is_fallback_empty = len(segments) == 1 and not first_seg.get("text")
                if not is_fallback_empty:
                    for seg in segments:
                        if seg.get("image_path"):
                            img_name = Path(seg["image_path"]).name
                            seg["image_path"] = str(folder_path / img_name)
                    return segments, audio_path
        except Exception as e:
            print(f"[RECONSTRUCT] Failed to read segments from info_file: {e}")
            
    # Reconstruct fallback
    segments = []
    if meta_file.exists() and audio_path:
        try:
            import re
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            
            # Measure audio duration
            from moviepy import AudioFileClip as AFC
            audio_clip = AFC(audio_path)
            real_duration = audio_clip.duration
            audio_clip.close()
            
            scenes = meta.get("scenes", [])
            images = sorted(list(folder_path.glob("scene_*.jpg")), key=lambda p: int(re.search(r"scene_(\d+)", p.name).group(1)) if re.search(r"scene_(\d+)", p.name) else 99)
            
            if scenes:
                word_counts = [len(s.get("narration", "").split()) for s in scenes]
                total_words = sum(word_counts)
                for idx, scene in enumerate(scenes):
                    wc = word_counts[idx]
                    dur_each = real_duration * (wc / total_words) if total_words > 0 else real_duration / len(scenes)
                    img_path = str(images[idx % len(images)]) if images else ""
                    
                    # Split scene narration into sub-segments for subtitles (max 6 words)
                    words = scene.get("narration", "").split()
                    sub_parts = []
                    if words:
                        max_words = 6
                        chunks = []
                        current_chunk = []
                        for w in words:
                            current_chunk.append(w)
                            if len(current_chunk) >= max_words:
                                chunks.append(" ".join(current_chunk))
                                current_chunk = []
                        if current_chunk:
                            chunks.append(" ".join(current_chunk))
                        total_chars = sum(len(c) for c in chunks)
                        for c in chunks:
                            c_dur = dur_each * (len(c) / total_chars) if total_chars > 0 else dur_each / len(chunks)
                            sub_parts.append((c, c_dur))
                    else:
                        sub_parts = [("", dur_each)]
                        
                    for sub_text, sub_dur in sub_parts:
                        segments.append({
                            "text": sub_text,
                            "duration": sub_dur,
                            "image_path": img_path
                        })
            else:
                narration = meta.get("narration", "")
                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narration) if s.strip()]
                if not sentences:
                    sentences = [narration]
                word_counts = [len(s.split()) for s in sentences]
                total_words = sum(word_counts)
                
                for idx, (sent, wc) in enumerate(zip(sentences, word_counts)):
                    dur_each = real_duration * (wc / total_words) if total_words > 0 else real_duration / len(sentences)
                    img_path = str(images[idx % len(images)]) if images else ""
                    
                    # Split into max 6 words subtitle chunks
                    words = sent.split()
                    sub_parts = []
                    if words:
                        max_words = 6
                        chunks = []
                        current_chunk = []
                        for w in words:
                            current_chunk.append(w)
                            if len(current_chunk) >= max_words:
                                chunks.append(" ".join(current_chunk))
                                current_chunk = []
                        if current_chunk:
                            chunks.append(" ".join(current_chunk))
                        total_chars = sum(len(c) for c in chunks)
                        for c in chunks:
                            c_dur = dur_each * (len(c) / total_chars) if total_chars > 0 else dur_each / len(chunks)
                            sub_parts.append((c, c_dur))
                    else:
                        sub_parts = [("", dur_each)]
                        
                    for sub_text, sub_dur in sub_parts:
                        segments.append({
                            "text": sub_text,
                            "duration": sub_dur,
                            "image_path": img_path
                        })
        except Exception as e:
            print(f"[RECONSTRUCT] Failed to reconstruct segments: {e}")
            
    # Final fallback if still empty
    if not segments:
        try:
            from moviepy import AudioFileClip as AFC
            audio_clip = AFC(audio_path)
            real_duration = audio_clip.duration
            audio_clip.close()
        except:
            real_duration = 10.0
        images = sorted(list(folder_path.glob("scene_*.jpg")), key=lambda p: int(re.search(r"scene_(\d+)", p.name).group(1)) if re.search(r"scene_(\d+)", p.name) else 99)
        img_path = str(images[0]) if images else ""
        segments = [{
            "text": "",
            "duration": real_duration,
            "image_path": img_path
        }]
            
    return segments, audio_path


class EditVideoPayload(BaseModel):
    folder: str
    transition: Optional[str] = None
    transition_dur: Optional[float] = None
    subtitle_preset: Optional[str] = None
    subtitle_animation: Optional[str] = None
    bgm_path: Optional[str] = None
    bgm_volume: Optional[float] = None
    watermark_text: Optional[str] = None
    censor_faces: Optional[bool] = None
    auto_editor: Optional[bool] = None
    enable_i2v: Optional[bool] = None
    i2v_model_quality: Optional[str] = None
    i2v_fps_multiplier: Optional[int] = None


@app.post("/api/output/edit")
def edit_output_video(payload: EditVideoPayload):
    """Üretilmiş videonun görsel geçiş ve alt yazı ayarlarını günceller ve videoyu yeniden derler."""
    output_dir = settings_mgr.get("output_dir", "output")
    folder_path = Path(output_dir) / payload.folder
    
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Video klasörü bulunamadı.")
        
    info_file = folder_path / "video_info.json"
    if not info_file.exists():
        # Basic fallback creation
        meta_extra = {
            "shorts_mode": "shorts" in payload.folder.lower(),
            "transition": "fade",
            "resolution": "1080x1920" if "shorts" in payload.folder.lower() else "1920x1080",
        }
        info_file.write_text(json.dumps(meta_extra, ensure_ascii=False, indent=2))

    try:
        info = json.loads(info_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"video_info.json okuma hatası: {str(e)}")

    # Update info parameters
    if payload.transition is not None:
        info["transition"] = payload.transition
    
    # Get segments and audio path
    segments, audio_path = _get_video_segments_and_audio(folder_path)
    if not segments:
        raise HTTPException(status_code=400, detail="Segment bilgisi alınamadı veya oluşturulamadı.")
    if not audio_path:
        raise HTTPException(status_code=400, detail="Ses dosyası bulunamadı.")
        
    shorts_mode = info.get("shorts_mode", False)
    W = 1080 if shorts_mode else 1920
    H = 1920 if shorts_mode else 1080
    
    # Identify channel settings
    parts = payload.folder.split("/")
    channel_id = parts[0] if parts else ""
    ch_mgr = ChannelManager()
    channel = ch_mgr.get_channel(channel_id)
    
    edit_options = ch_mgr.get_resolved_edit_options(channel_id) if channel else {}
    
    transition = payload.transition if payload.transition is not None else info.get("transition", edit_options.get("transition", "fade"))
    transition_dur = payload.transition_dur if payload.transition_dur is not None else edit_options.get("transition_dur", 0.5)
    subtitle_preset = payload.subtitle_preset if payload.subtitle_preset is not None else edit_options.get("subtitle_preset", "bold")
    subtitle_animation = payload.subtitle_animation if payload.subtitle_animation is not None else edit_options.get("subtitle_animation", "fade")
    bgm_path = payload.bgm_path if payload.bgm_path is not None else edit_options.get("bgm_path")
    bgm_volume = payload.bgm_volume if payload.bgm_volume is not None else edit_options.get("bgm_volume", 0.15)
    watermark_text = payload.watermark_text if payload.watermark_text is not None else edit_options.get("watermark_text")
    censor_faces = payload.censor_faces if payload.censor_faces is not None else edit_options.get("censor_faces", False)
    auto_editor = payload.auto_editor if payload.auto_editor is not None else edit_options.get("auto_editor", False)

    # Face Censorship if requested
    if censor_faces:
        from video_generator import VideoGenerator
        generator = VideoGenerator()
        for seg in segments:
            img = seg.get("image_path")
            if img and Path(img).exists():
                generator._censor_faces(img)

    try:
        from video_editor import EditConfig, VideoEditor
    except ImportError:
        from src.video_editor import EditConfig, VideoEditor

    edit_cfg = EditConfig(
        transition=transition,
        transition_dur=float(transition_dur),
        kenburns_intensity=float(edit_options.get("kenburns_intensity", 0.04)),
        fps=24,
        width=W,
        height=H,
        shorts_mode=shorts_mode,
        bgm_path=bgm_path,
        bgm_volume=float(bgm_volume),
        watermark_path=edit_options.get("watermark_path"),
        watermark_text=watermark_text,
        watermark_position=edit_options.get("watermark_position", "top-right"),
        intro_clip_path=edit_options.get("intro_clip_path"),
        outro_clip_path=edit_options.get("outro_clip_path"),
        subtitle_preset=subtitle_preset,
        subtitle_animation=subtitle_animation,
    )

    video_path = str(folder_path / "final.mp4")
    editor = VideoEditor(edit_cfg)
    edit_log = editor.compose(
        segments=segments,
        audio_path=audio_path,
        output_path=video_path,
        work_dir=str(folder_path),
    )

    if not edit_log.get("success"):
        raise HTTPException(status_code=500, detail=f"Yeniden derleme başarısız: {edit_log.get('error')}")

    # Auto-Editor post-processing if enabled
    if isinstance(auto_editor, str):
        auto_editor_enabled = auto_editor.lower() in ("true", "1", "yes")
    else:
        auto_editor_enabled = bool(auto_editor)

    if auto_editor_enabled:
        print(f"[AUTO-EDITOR] Silence removal is enabled during recompile. Processing {video_path}...")
        import subprocess
        project_root = Path(__file__).resolve().parent.parent
        auto_editor_bin = project_root / ".venv" / "bin" / "auto-editor"
        temp_video_path = str(folder_path / "final_cut.mp4")
        cmd = [
            str(auto_editor_bin),
            video_path,
            "--output",
            temp_video_path
        ]
        try:
            print(f"[AUTO-EDITOR] Running command: {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if res.returncode == 0 and os.path.exists(temp_video_path):
                shutil.move(temp_video_path, video_path)
                print("[AUTO-EDITOR] Silence removal completed successfully during recompile!")
            else:
                print(f"[AUTO-EDITOR] Error running auto-editor: {res.stderr}")
        except Exception as ae_err:
            print(f"[AUTO-EDITOR] Failed to execute auto-editor: {ae_err}")

    # Update metadata files
    info["transition"] = transition
    info["edit_log"] = {
        "groups": edit_log.get("groups"),
        "captions": edit_log.get("captions"),
        "ass_path": edit_log.get("ass_path"),
        "base_path": edit_log.get("base_path"),
    }
    info["segments"] = segments
    info_file.write_text(json.dumps(info, ensure_ascii=False, indent=2))

    _clear_memory(trigger="video_editor_recompose")

    return {
        "success": True,
        "video_path": video_path,
        "transition": transition,
    }


@app.post("/api/channels/{channel_id}/analyze-history")
def analyze_channel_history(channel_id: str, payload: dict):
    """
    Kanalın geçmiş videolarını (görüntülenme sayılarını) analiz eder,
    en az/en çok izlenen konuları çıkarır ve zihin haritasını günceller.
    """
    scraped_videos = payload.get("videos", [])
    if not scraped_videos:
        raise HTTPException(status_code=400, detail="Video listesi boş olamaz.")
        
    mgr = ChannelManager()
    ch = mgr.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    
    try:
        writer = _get_configured_script_writer()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    from mind_map import MindMapManager
    mm_mgr = MindMapManager(channel_dir)
    mind_map_data = mm_mgr.load()
    
    sorted_videos = sorted(scraped_videos, key=lambda x: x.get("views", 0), reverse=True)
    top_videos = sorted_videos[:5]
    bottom_videos = sorted_videos[-5:] if len(sorted_videos) > 5 else []
    
    top_str = "\n".join([f"- {v.get('title')} ({v.get('viewsText')} izlenme)" for v in top_videos])
    bottom_str = "\n".join([f"- {v.get('title')} ({v.get('viewsText')} izlenme)" for v in bottom_videos])
    
    system_prompt = (
        "You are an expert YouTube performance analyst and channel growth strategist.\n"
        "Your task is to analyze the performance of the channel's published videos (top performing vs bottom performing) "
        "and determine why certain topics perform better than others. Then, you will optimize and restructure the channel's mind map "
        "categories to favor high-performing angles and suggest 3 new high-growth topic themes.\n\n"
        "STRICT JSON OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown, no other text:\n"
        "{\n"
        "  \"analysis\": \"A detailed analysis report in Turkish. Summarize why top videos succeeded and why bottom videos failed, and outline the strategic recommendations.\",\n"
        "  \"themes\": {\n"
        "     \"Theme Name 1\": [\"Topic 1\", \"Topic 2\", \"Topic 3\"],\n"
        "     ...\n"
        "  }\n"
        "}"
    )
    
    user_prompt = (
        f"Channel Name: {ch.get('name', 'Bilinmeyen Kanal')}\n"
        f"Category: {ch.get('topic_category', 'space')}\n\n"
        f"Top Performing Videos:\n{top_str}\n\n"
        f"Bottom Performing Videos:\n{bottom_str}\n\n"
        f"Current Hierarchical Mind Map Themes:\n{json.dumps(mind_map_data, ensure_ascii=False)}"
    )
    
    try:
        raw_json = writer.run_prompt(system_prompt, user_prompt)
        from script_writer import _parse_json
        cleaned = _parse_json(raw_json)
        
        if not isinstance(cleaned, dict) or "analysis" not in cleaned or "themes" not in cleaned:
            raise ValueError("Yapay zeka geçerli bir analiz raporu üretemedi.")
            
        updated_mind_map = {"themes": cleaned.get("themes", {})}
        mm_mgr.save(updated_mind_map)
        
        return {
            "success": True,
            "analysis": cleaned.get("analysis"),
            "mind_map": updated_mind_map
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geçmiş analiz hatası: {str(e)}")


@app.post("/api/inspiration/generate")
def generate_inspiration_topic(payload: dict):
    """
    YouTube'daki bir videodan esinlenerek özgün bir içerik planı satırı oluşturur.
    """
    channel_id = payload.get("channel_id")
    source_title = payload.get("source_title")
    source_url = payload.get("source_url", "")
    
    if not channel_id or not source_title:
        raise HTTPException(status_code=400, detail="channel_id ve source_title parametreleri zorunludur.")
        
    mgr = ChannelManager()
    ch = mgr.get_channel(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Kanal bulunamadı.")
        
    output_dir = settings_mgr.get("output_dir", "output")
    channel_dir = Path(output_dir) / channel_id
    planner = ContentPlanner(channel_dir)
    
    try:
        writer = _get_configured_script_writer()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    system_prompt = (
        "You are an expert YouTube growth assistant. The user wants to get inspired by an existing YouTube video title "
        "and generate a completely original, non-duplicate, highly engaging video idea for their own channel.\n"
        f"Target Channel Category: {ch.get('topic_category', 'space')}\n"
        f"Target Channel Language: {ch.get('language', 'tr')}\n\n"
        "STRICT JSON OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown, no other text:\n"
        "{\n"
        "  \"konu\": \"Original, fresh scientific/story angle in the target language\",\n"
        "  \"baslik\": \"Engaging SEO-friendly video title in the target language\",\n"
        "  \"anahtar_kelimeler\": \"keyword1, keyword2, keyword3\"\n"
        "}"
    )
    
    user_prompt = f"Existing source video title to get inspired by: '{source_title}'"
    
    try:
        raw_json = writer.run_prompt(system_prompt, user_prompt)
        from script_writer import _parse_json
        cleaned = _parse_json(raw_json)
        
        if not isinstance(cleaned, dict) or "baslik" not in cleaned:
            raise ValueError("Yapay zeka geçerli bir içerik üretemedi.")
            
        new_topic = {
            "konu": cleaned.get("konu", source_title),
            "baslik": cleaned.get("baslik", f"Özgün: {source_title}"),
            "anahtar_kelimeler": cleaned.get("anahtar_kelimeler", ""),
            "secilen_muzik": "",
            "notlar": f"Esinlenilen Kaynak: {source_title} ({source_url})" if source_url else f"Esinlenilen: {source_title}"
        }
        
        added_rows = planner.add_topics([new_topic])
        
        try:
            from mind_map import MindMapManager
            mm_mgr = MindMapManager(channel_dir)
            category = ch.get("topic_category", "space")
            mm_mgr.sync_from_csv(writer, planner, category=category, channel_config=ch)
        except Exception as e:
            print(f"[INSPIRATION] Zihin haritası güncellenirken hata: {e}")
            
        return {"success": True, "topic": added_rows[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İlham üretim hatası: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# RAG — Karakter & Kanal Evreni Hafızası (Lore Memory) Endpoints
# ═══════════════════════════════════════════════════════════════

try:
    from character_rag import CharacterRAGManager, get_rag_context_for_prompt
except ImportError:
    from src.character_rag import CharacterRAGManager, get_rag_context_for_prompt

@app.get("/api/rag/characters")
def list_rag_characters(channel_id: Optional[str] = Query(None)):
    """Kayıtlı karakterleri listeler."""
    try:
        return {"characters": CharacterRAGManager.list_characters(channel_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/characters")
def upsert_rag_character(payload: dict = Body(...)):
    """Karakter ekler veya günceller."""
    try:
        char_id = CharacterRAGManager.upsert_character(payload)
        return {"success": True, "id": char_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/rag/characters/{char_id}")
def delete_rag_character(char_id: int):
    """Karakteri siler."""
    try:
        ok = CharacterRAGManager.delete_character(char_id)
        return {"success": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/memories")
def list_rag_memories(channel_id: Optional[str] = Query(None), limit: int = 50):
    """Geçmiş hikaye / lore hafızasını listeler."""
    try:
        return {"memories": CharacterRAGManager.list_memories(channel_id, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/memories")
def add_rag_memory(payload: dict = Body(...)):
    """Yeni hikaye / olay hafızası ekler."""
    try:
        mem_id = CharacterRAGManager.add_memory(
            channel_id=payload.get("channel_id") or "global",
            title=payload.get("title", "Olay"),
            summary=payload.get("summary", ""),
            topic=payload.get("topic", ""),
            characters_involved=payload.get("characters_involved") or [],
            key_events=payload.get("key_events", "")
        )
        return {"success": True, "id": mem_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/rag/memories/{memory_id}")
def delete_rag_memory(memory_id: int):
    """Hikaye hafızasını siler."""
    try:
        ok = CharacterRAGManager.delete_memory(memory_id)
        return {"success": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/seed")
def seed_rag_defaults(payload: dict = Body(default={})):
    """Varsayılan Türk apartman/mizah karakterlerini yükler."""
    try:
        channel_id = payload.get("channel_id") or "global"
        CharacterRAGManager.seed_defaults(channel_id)
        return {"success": True, "message": "Varsayılan karakterler ve lore hafızası yüklendi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/query")
def test_rag_query(payload: dict = Body(...)):
    """Konu başlığına göre RAG'in bulduğu karakter ve hafızayı test eder."""
    try:
        topic = payload.get("topic", "")
        channel_id = payload.get("channel_id") or "global"
        lore = CharacterRAGManager.retrieve_relevant_lore(channel_id, topic)
        context = CharacterRAGManager.get_prompt_context(channel_id, topic)
        return {
            "characters": lore.get("characters", []),
            "memories": lore.get("memories", []),
            "prompt_context": context
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# CASPER AI — Canlı Danışman & agy Terminal Endpoints
# ═══════════════════════════════════════════════════════════════

try:
    from casper_advisor import CasperAdvisor
    from casper_terminal import terminal_session
except ImportError:
    from src.casper_advisor import CasperAdvisor
    from src.casper_terminal import terminal_session

@app.get("/api/casper/pending")
def list_casper_pending_ideas():
    """Bekleyen tüm Casper fikirlerini listeler."""
    try:
        ideas = CasperAdvisor.list_pending_ideas()
        saved_count = CasperAdvisor.get_saved_count()
        return {
            "ideas": ideas,
            "total": len(ideas),
            "saved_count": saved_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/casper/tip")
def get_casper_current_tip():
    """Casper'ın ekranda anlık önereceği fikri ve kayıtlı fikir sayısını döndürür."""
    try:
        tip = CasperAdvisor.get_current_tip()
        saved_count = CasperAdvisor.get_saved_count()
        return {
            "tip": tip,
            "saved_count": saved_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/casper/ideas")
def list_casper_ideas(status: Optional[str] = Query(None)):
    """Tüm veya belirli durumdaki Casper fikirlerini listeler."""
    try:
        ideas = CasperAdvisor.list_ideas(status=status)
        saved_count = CasperAdvisor.get_saved_count()
        return {
            "ideas": ideas,
            "saved_count": saved_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/casper/ideas/{idea_id}/save")
def save_casper_idea(idea_id: int):
    """Fikri kullanıcının hafızasına kaydeder."""
    try:
        ok = CasperAdvisor.set_idea_status(idea_id, "saved")
        return {"success": ok, "saved_count": CasperAdvisor.get_saved_count()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/casper/ideas/{idea_id}")
def delete_casper_idea(idea_id: int):
    """Beğenilmeyen fikri veritabanından tamamen siler."""
    try:
        ok = CasperAdvisor.delete_idea(idea_id)
        return {
            "success": ok,
            "deleted_id": idea_id,
            "saved_count": CasperAdvisor.get_saved_count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/casper/ideas/{idea_id}/delete")
def post_delete_casper_idea(idea_id: int):
    """Beğenilmeyen fikri veritabanından tamamen siler (POST fallback)."""
    try:
        ok = CasperAdvisor.delete_idea(idea_id)
        return {
            "success": ok,
            "deleted_id": idea_id,
            "saved_count": CasperAdvisor.get_saved_count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/casper/ideas/{idea_id}/dismiss")
def dismiss_casper_idea(idea_id: int):
    """Fikri göz ardı eder."""
    try:
        ok = CasperAdvisor.set_idea_status(idea_id, "dismissed")
        return {"success": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/casper/generate")
def generate_casper_ideas():
    """LM Studio veya Graphify analizi ile tam 10 yeni fikir dalgası üretir."""
    try:
        new_ideas = CasperAdvisor.generate_10_ideas()
        return {"success": True, "ideas": new_ideas, "count": len(new_ideas)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/casper/apply-payload")
def get_casper_apply_payload():
    """Kaydedilen fikirlerle oluşturulan agy komutunu ve promptunu döndürür."""
    try:
        return CasperAdvisor.build_agy_prompt_payload()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/casper/terminal/start")
def start_casper_terminal_apply():
    """Kaydedilen fikirleri agy oturumuna göndererek Gemini geliştirmesini başlatır."""
    try:
        payload = CasperAdvisor.build_agy_prompt_payload()
        res = terminal_session.run_agy_command(
            prompt=payload["prompt"],
            conversation_id=payload.get("conversation_id", "b918ee66-9d53-472c-8ab2-0a10132b0a6f")
        )
        return {
            "status": "started",
            "ideas_count": payload["ideas_count"],
            "command": payload["command"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/casper/terminal/status")
def get_casper_terminal_status(since_index: int = Query(0)):
    """Terminalin canlı loglarını ve durumunu döndürür."""
    try:
        logs = terminal_session.get_logs(since_index=since_index)
        return {
            "is_running": terminal_session.is_running,
            "exit_code": terminal_session.exit_code,
            "logs": logs,
            "total_logs": len(terminal_session.logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/casper/terminal/stop")
def stop_casper_terminal():
    """Çalışan terminal oturumunu durdurur."""
    try:
        terminal_session.stop()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/gc")
def api_trigger_system_gc():
    """Casper AI: Manuel veya sistem tarafından tetiklenen GPU ve RAM temizliği."""
    details = AutoGCWatchdog.clean(trigger="manual_api")
    return {"status": "ok", "details": details}


@app.get("/api/system/gc-status")
def api_get_gc_status():
    """Casper AI: Nöbetçi bellek temizleyicisi durumunu ve GPU metriklerini döner."""
    return AutoGCWatchdog.get_status()


class StoryVideoRequest(BaseModel):
    topic: str
    style: str = "cinematic_fantasy"
    author: Optional[str] = "HikayeDiyari"
    bgm_path: Optional[str] = None


@app.post("/api/story-video/generate")
def api_generate_story_video(payload: StoryVideoRequest, background_tasks: BackgroundTasks):
    """
    Remotion + AI Çizim Tabanlı Sinematik Hikaye Videosu Üretimi.
    """
    exec_id = f"story_{uuid.uuid4().hex[:8]}"
    executions[exec_id] = {
        "status": "pending",
        "message": f"'{payload.topic}' hikayesi ve özel çizimleri hazırlanıyor...",
        "timestamp": datetime.now().isoformat(),
    }

    def _task():
        executions[exec_id]["status"] = "running"
        try:
            from story_illustrated_generator import StoryIllustratedGenerator
            gen = StoryIllustratedGenerator()
            res = gen.create_illustrated_story_video(
                topic=payload.topic,
                style=payload.style,
                author=payload.author or "HikayeDiyari",
                bgm_path=payload.bgm_path,
            )
            if res.get("success"):
                executions[exec_id]["status"] = "completed"
                executions[exec_id]["video_path"] = res.get("output_path")
                executions[exec_id]["message"] = f"Hikaye videosu başarıyla üretildi: {Path(res['output_path']).name}"
            else:
                executions[exec_id]["status"] = "failed"
                executions[exec_id]["message"] = "Remotion render işlemi başarısız oldu."
        except Exception as ex:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = f"Hata: {ex}"

    background_tasks.add_task(_task)
    return {
        "success": True,
        "exec_id": exec_id,
        "message": f"'{payload.topic}' hikaye videosu üretimi arka planda başlatıldı."
    }


# ═══════════════════════════════════════════════════════════════
# VOICE ENGINE — OpenAI-compatible Local Audio API (/v1)
# ═══════════════════════════════════════════════════════════════
try:
    from voice_engine import router as voice_router
    app.include_router(voice_router)
    print("[VOICE-ENGINE] 🎙️ OpenAI-compatible Local Audio API mounted at /v1")
except Exception as _ve_err:
    print(f"[VOICE-ENGINE] ⚠️ Could not mount voice_engine router: {_ve_err}")


# ═══════════════════════════════════════════════════════════════
# STORY DRAFTS & MULTI-PART PROCEDURAL ANIMATION API
# ═══════════════════════════════════════════════════════════════

try:
    from story_manager import StoryManager
except ImportError:
    StoryManager = None


class StoryDraftCreateRequest(BaseModel):
    channel_id: str
    title: str
    raw_text: str
    target_language: Optional[str] = "tr"
    genre: Optional[str] = "sci_fi_mystery"
    plot_notes: Optional[str] = ""
    author: Optional[str] = "Antigravity Storyteller"
    developed_story: Optional[dict] = None


@app.get("/api/stories")
def api_list_stories(channel_id: Optional[str] = Query(None)):
    """Hikaye taslaklarını listeler."""
    if not StoryManager:
        raise HTTPException(status_code=500, detail="StoryManager yüklenemedi.")
    mgr = StoryManager()
    stories = mgr.list_stories(channel_id=channel_id)
    return {"success": True, "count": len(stories), "stories": stories}


@app.get("/api/stories/{story_id}")
def api_get_story(story_id: str):
    """Tekil bir hikaye taslağını getirir."""
    if not StoryManager:
        raise HTTPException(status_code=500, detail="StoryManager yüklenemedi.")
    mgr = StoryManager()
    story = mgr.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Hikaye taslağı bulunamadı.")
    return {"success": True, "story": story}


@app.post("/api/stories")
def api_create_story(payload: StoryDraftCreateRequest):
    """Yeni bir kullanıcı hikaye taslağı oluşturur."""
    if not StoryManager:
        raise HTTPException(status_code=500, detail="StoryManager yüklenemedi.")
    mgr = StoryManager()
    created = mgr.create_story(
        channel_id=payload.channel_id,
        title=payload.title,
        raw_text=payload.raw_text,
        target_language=payload.target_language or "tr",
        genre=payload.genre or "sci_fi_mystery",
        plot_notes=payload.plot_notes or "",
        developed_story=payload.developed_story,
        author=payload.author
    )
    return {"success": True, "story": created}


@app.put("/api/stories/{story_id}")
def api_update_story(story_id: str, payload: dict = Body(...)):
    """Mevcut bir hikaye taslağını günceller."""
    if not StoryManager:
        raise HTTPException(status_code=500, detail="StoryManager yüklenemedi.")
    mgr = StoryManager()
    updated = mgr.update_story(story_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Hikaye taslağı bulunamadı.")
    return {"success": True, "story": updated}


@app.delete("/api/stories/{story_id}")
def api_delete_story(story_id: str):
    """Hikaye taslağını siler."""
    if not StoryManager:
        raise HTTPException(status_code=500, detail="StoryManager yüklenemedi.")
    mgr = StoryManager()
    ok = mgr.delete_story(story_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Hikaye taslağı bulunamadı.")
    return {"success": True, "message": "Hikaye taslağı silindi."}


@app.post("/api/stories/{story_id}/convert-to-material")
def api_convert_story_to_material(story_id: str):
    """Geliştirilen hikayeyi çok bölümlü üretim materyallerine dönüştürür."""
    if not StoryManager:
        raise HTTPException(status_code=500, detail="StoryManager yüklenemedi.")
    mgr = StoryManager()
    try:
        res = mgr.convert_to_materials(story_id)
        return {"success": True, "data": res}
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@app.post("/api/stories/{story_id}/produce")
def api_produce_story_video(story_id: str, background_tasks: BackgroundTasks, payload: dict = Body({})):
    """Kodla çizilen prosedürel Aurora animasyon motoru ile Shorts bölümleri üretir."""
    if not StoryManager:
        raise HTTPException(status_code=500, detail="StoryManager yüklenemedi.")
    mgr = StoryManager()
    story = mgr.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Hikaye taslağı bulunamadı.")

    exec_id = f"story_anim_{uuid.uuid4().hex[:8]}"
    executions[exec_id] = {
        "status": "pending",
        "message": f"'{story.get('title')}' prosedürel animasyon Shorts bölümleri hazırlanıyor...",
        "timestamp": datetime.now().isoformat(),
        "channel_id": story.get("channel_id"),
    }

    def _task():
        executions[exec_id]["status"] = "running"
        try:
            from story_animation_engine import StoryAnimationEngine
            engine = StoryAnimationEngine()
            results = engine.render_all_parts_for_story(
                story_id=story_id,
                channel_id=story.get("channel_id"),
                bgm_path=payload.get("bgm_path")
            )
            executions[exec_id]["status"] = "completed"
            executions[exec_id]["results"] = results
            executions[exec_id]["message"] = f"Toplam {len(results)} Shorts bölümü başarıyla üretildi!"
        except Exception as ex:
            executions[exec_id]["status"] = "failed"
            executions[exec_id]["message"] = f"Üretim hatası: {ex}"

    background_tasks.add_task(_task)
    return {
        "success": True,
        "exec_id": exec_id,
        "message": f"'{story.get('title')}' hikaye animasyonu üretimi arka planda başlatıldı."
    }


# Output klasörünü statik olarak bağla (uzantı videoyu Blob olarak indirebilsin)
output_dir = settings_mgr.get("output_dir", "output")
output_path = _PROJECT_ROOT / output_dir
if output_path.exists():
    app.mount("/output", StaticFiles(directory=str(output_path)), name="output-files")


# ═══════════════════════════════════════════════════════════════
# DASHBOARD — Statik dosya serving (SPA)
# ═══════════════════════════════════════════════════════════════

_DASHBOARD_DIST = _PROJECT_ROOT / "dashboard" / "dist"

if _DASHBOARD_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_DASHBOARD_DIST / "assets")), name="dashboard-assets")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(str(_DASHBOARD_DIST / "index.html"))

    # SPA catch-all: bilinmeyen yolları index.html'e yönlendir
    @app.get("/{path:path}")
    def serve_spa(path: str):
        requested = _DASHBOARD_DIST / path
        if requested.is_file():
            return FileResponse(str(requested))
        return FileResponse(str(_DASHBOARD_DIST / "index.html"))
else:
    @app.get("/")
    def home():
        return {"message": "Video Üretim API çalışıyor. /docs adresinden API dokümantasyonuna ulaşabilirsiniz. (Dashboard build bulunamadı.)"}
