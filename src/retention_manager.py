"""
retention_manager.py
====================
Otomatik Yüklenen Video Saklama ve TTL Temizleyici (20 Günlük Saklama Politikası).
Tüm kanalların 'output/<channel_id>/yuklenen/' klasörüne taşınan video paketlerine
20 günlük saklama süresi (TTL) tanımlar ve süresi dolan klasörleri otonom olarak temizler.
"""

import os
import time
import json
import shutil
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

DEFAULT_RETENTION_DAYS = 20
META_FILENAME = ".retention_meta.json"


def _get_output_path(base_dir: Optional[Path] = None) -> Path:
    if base_dir:
        return Path(base_dir).resolve()
    return Path(__file__).resolve().parent.parent / "output"


def tag_archived_folder(folder_path: Path, retention_days: int = DEFAULT_RETENTION_DAYS) -> Dict[str, Any]:
    """
    Bir klasör 'yuklenen/' altına taşındığında saklama meta verisini damgalar.
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return {}

    now = datetime.now()
    expires_at = now + timedelta(days=retention_days)
    meta = {
        "archived_at": now.isoformat(),
        "retention_days": retention_days,
        "expires_at": expires_at.isoformat(),
        "archived_timestamp": int(now.timestamp()),
        "expires_timestamp": int(expires_at.timestamp())
    }

    try:
        meta_file = folder / META_FILENAME
        meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[RetentionManager] Meta damgalama hatası ({folder.name}): {e}")

    return meta


def get_folder_retention_info(folder_path: Path, default_days: int = DEFAULT_RETENTION_DAYS) -> Dict[str, Any]:
    """
    Klasörün saklama durumunu, kalan gününü ve süresinin dolup dolmadığını hesaplar.
    """
    folder = Path(folder_path)
    meta_file = folder / META_FILENAME

    now_ts = time.time()
    archived_ts = None
    retention_days = default_days

    if meta_file.exists():
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            archived_ts = data.get("archived_timestamp")
            retention_days = data.get("retention_days", default_days)
        except Exception:
            pass

    # Meta yoksa mtime (son taşınma/değişiklik) veya video_info.json/metadata.json fallback
    if not archived_ts:
        for info_name in ("video_info.json", "metadata.json", "approval.json"):
            info_file = folder / info_name
            if info_file.exists():
                try:
                    info_data = json.loads(info_file.read_text(encoding="utf-8"))
                    dt_str = info_data.get("uploaded_at") or info_data.get("archived_at") or info_data.get("created_at")
                    if dt_str:
                        archived_ts = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).timestamp()
                        break
                except Exception:
                    pass

    if not archived_ts:
        try:
            archived_ts = folder.stat().st_mtime
        except Exception:
            archived_ts = now_ts

    age_seconds = max(0.0, now_ts - archived_ts)
    age_days = age_seconds / 86400.0
    ttl_seconds = retention_days * 86400.0
    remaining_seconds = max(0.0, ttl_seconds - age_seconds)
    remaining_days = remaining_seconds / 86400.0
    is_expired = age_seconds >= ttl_seconds

    return {
        "folder_name": folder.name,
        "folder_path": str(folder),
        "age_days": round(age_days, 2),
        "retention_days": retention_days,
        "remaining_days": round(remaining_days, 2),
        "is_expired": is_expired,
        "archived_at": datetime.fromtimestamp(archived_ts).isoformat()
    }


def clean_expired_yuklenen_folders(
    output_dir: Optional[Path] = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Tüm kanalların 'yuklenen/' klasörünü tarar ve retention_days gününü dolduran klasörleri siler.
    """
    out_root = _get_output_path(output_dir)
    if not out_root.exists():
        return {"success": False, "deleted_count": 0, "freed_mb": 0.0, "deleted_folders": []}

    deleted_folders = []
    freed_bytes = 0

    for channel_dir in out_root.iterdir():
        if not channel_dir.is_dir():
            continue
        yuklenen_dir = channel_dir / "yuklenen"
        if not yuklenen_dir.exists() or not yuklenen_dir.is_dir():
            continue

        for folder in list(yuklenen_dir.iterdir()):
            if not folder.is_dir() or folder.name.startswith("."):
                continue

            info = get_folder_retention_info(folder, default_days=retention_days)
            if info["is_expired"]:
                folder_bytes = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
                if not dry_run:
                    try:
                        shutil.rmtree(folder)
                        deleted_folders.append({
                            "channel_id": channel_dir.name,
                            "folder_name": folder.name,
                            "age_days": info["age_days"],
                            "size_mb": round(folder_bytes / (1024 * 1024), 2)
                        })
                        freed_bytes += folder_bytes
                        print(f"[RetentionManager] 🗑️ Süresi dolan klasör silindi: {channel_dir.name}/yuklenen/{folder.name} (Yaş: {info['age_days']} gün, Boyut: {folder_bytes/(1024*1024):.1f} MB)")
                    except Exception as e:
                        print(f"[RetentionManager] ❌ Klasör silme hatası ({folder.name}): {e}")
                else:
                    deleted_folders.append({
                        "channel_id": channel_dir.name,
                        "folder_name": folder.name,
                        "age_days": info["age_days"],
                        "size_mb": round(folder_bytes / (1024 * 1024), 2),
                        "dry_run": True
                    })
                    freed_bytes += folder_bytes

    return {
        "success": True,
        "retention_days": retention_days,
        "deleted_count": len(deleted_folders),
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        "deleted_folders": deleted_folders
    }


_daemon_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _retention_worker_loop(interval_hours: int = 12):
    print(f"[RetentionManager] 🛡️ 20 Günlük Saklama Politikası Denetçisi aktif (Denetim aralığı: {interval_hours} saat).")
    while not _stop_event.is_set():
        try:
            clean_expired_yuklenen_folders(retention_days=DEFAULT_RETENTION_DAYS)
        except Exception as e:
            print(f"[RetentionManager] Periyodik denetim hatası: {e}")

        # Bekleme
        _stop_event.wait(timeout=interval_hours * 3600)


def start_retention_daemon(interval_hours: int = 12):
    global _daemon_thread
    if _daemon_thread and _daemon_thread.is_alive():
        return
    _stop_event.clear()
    _daemon_thread = threading.Thread(target=_retention_worker_loop, args=(interval_hours,), daemon=True)
    _daemon_thread.start()
