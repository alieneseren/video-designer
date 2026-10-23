"""
Browser Agent and Chrome Extension router.
"""
import time
from fastapi import APIRouter, HTTPException
from browser_agent import browser_agent
from settings_manager import SettingsManager

router = APIRouter(tags=["Browser"])
settings_mgr = SettingsManager()
_global_pending_upload = {}


@router.get("/api/browser-agent/status")
def get_browser_agent_status_endpoint():
    """Browser Agent canlı durumunu ve işlem günlüklerini döner."""
    return browser_agent.get_status()


@router.post("/api/browser-agent/start")
def start_browser_agent_endpoint(payload: dict):
    """LM Studio AI ve Browser MCP destekli yükleme görevini başlatır."""
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


@router.post("/api/browser-agent/log")
def log_browser_agent_endpoint(payload: dict):
    """Tarayıcı eklentisi veya frontend'den canlı işlem günlüğü kaydeder."""
    msg = payload.get("message", "")
    lvl = payload.get("level", "info")
    details = payload.get("details")
    browser_agent.log(msg, level=lvl, details=details)
    return {"success": True}


@router.get("/api/extension/pending-upload")
def get_extension_pending_upload():
    """Chrome Eklentisi YouTube Studio'yu açtığında sıradaki yüklenecek video/kuyruk bilgisini alır."""
    global _global_pending_upload
    if _global_pending_upload and (time.time() - _global_pending_upload.get("timestamp", 0) < 600):
        return _global_pending_upload
    return {"payload": None, "queue": []}


@router.post("/api/extension/pending-upload")
def set_extension_pending_upload(data: dict):
    """Chrome Eklentisi için yüklenecek video kuyruğunu ayarlar."""
    global _global_pending_upload
    _global_pending_upload = {
        "payload": data.get("payload"),
        "queue": data.get("queue", []),
        "timestamp": time.time(),
    }
    return {"success": True, "pending": _global_pending_upload}


@router.post("/api/extension/pending-upload/clear")
def clear_extension_pending_upload():
    """Bekleyen yükleme kuyruğunu temizler."""
    global _global_pending_upload
    _global_pending_upload = {}
    return {"success": True}
