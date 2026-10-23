"""Persistent queue for Instagram uploads performed by the browser extension."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEDULE_FILE = Path("config/instagram_schedules.json")


class InstagramScheduleStore:
    def __init__(self, path: Path = SCHEDULE_FILE):
        self.path = Path(path)
        self.lock = threading.RLock()

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Instagram planlama kuyruğu okunamadı: {exc}") from exc
        if not isinstance(data, list):
            raise RuntimeError("Instagram planlama dosyasının biçimi geçersiz.")
        return data

    def _write(self, entries: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self.path)

    def list(self, channel_id: str | None = None) -> list[dict[str, Any]]:
        with self.lock:
            entries = self._read()
            if channel_id:
                entries = [item for item in entries if item.get("channel_id") == channel_id]
            return sorted(entries, key=lambda item: item.get("scheduled_at", ""))

    def create(self, entry: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            entries = self._read()
            active_statuses = {"scheduled", "publishing", "published", "needs_review"}
            if any(
                item.get("channel_id") == entry.get("channel_id")
                and item.get("folder") == entry.get("folder")
                and item.get("status") in active_statuses
                for item in entries
            ):
                raise ValueError("Bu video için Instagram planı zaten mevcut.")
            item = {
                **entry,
                "id": uuid.uuid4().hex,
                "status": "scheduled",
                "attempts": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_error": None,
                "published_at": None,
            }
            entries.append(item)
            self._write(entries)
            return item

    def update(self, schedule_id: str, **updates: Any) -> dict[str, Any] | None:
        with self.lock:
            entries = self._read()
            item = next((row for row in entries if row.get("id") == schedule_id), None)
            if not item:
                return None
            item.update(updates)
            self._write(entries)
            return item

    def claim_due(self, now: datetime | None = None) -> dict[str, Any] | None:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with self.lock:
            entries = self._read()
            for item in entries:
                if item.get("status") not in ("scheduled", "publishing"):
                    continue
                if item.get("status") == "publishing":
                    started_at = item.get("attempt_started_at")
                    if not started_at or current - datetime.fromisoformat(started_at).astimezone(timezone.utc) < timedelta(hours=2):
                        continue
                    if int(item.get("attempts", 0)) >= 3:
                        item["status"] = "failed"
                        item["last_error"] = "Eklenti yükleme sonucunu zamanında bildirmedi."
                        item["attempt_started_at"] = None
                        self._write(entries)
                        continue
                scheduled_at = datetime.fromisoformat(item["scheduled_at"]).astimezone(timezone.utc)
                retry_at = item.get("retry_at")
                due_at = datetime.fromisoformat(retry_at).astimezone(timezone.utc) if retry_at else scheduled_at
                if due_at <= current:
                    item["status"] = "publishing"
                    item["attempts"] = int(item.get("attempts", 0)) + 1
                    item["retry_at"] = None
                    item["attempt_started_at"] = current.isoformat()
                    self._write(entries)
                    return dict(item)
        return None

    def cancel(self, schedule_id: str) -> bool:
        with self.lock:
            entries = self._read()
            filtered = [
                item for item in entries
                if not (item.get("id") == schedule_id and item.get("status") == "scheduled")
            ]
            if len(filtered) == len(entries):
                return False
            self._write(filtered)
            return True
