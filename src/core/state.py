"""
Execution state manager.
Thread-safe and persistent status tracking for background video generation runs.
"""
import os
import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ExecutionManager:
    def __init__(self, persistence_file: str = "config/executions.json"):
        self.persistence_file = Path(persistence_file)
        self.lock = threading.Lock()
        self._executions: Dict[str, Any] = {}
        self._load()

    def _load(self):
        try:
            if self.persistence_file.exists():
                data = json.loads(self.persistence_file.read_text(encoding="utf-8"))
                self._executions = data
        except Exception as e:
            print(f"[STATE] Error loading execution state: {e}")
            self._executions = {}

    def _save(self):
        try:
            self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
            self.persistence_file.write_text(json.dumps(self._executions, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[STATE] Error saving execution state: {e}")

    def create(self, exec_id: str, channel_id: str, total_steps: int = 4, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self.lock:
            entry = {
                "exec_id": exec_id,
                "channel_id": channel_id,
                "status": "running",
                "progress": 0,
                "step": 0,
                "total_steps": total_steps,
                "current_step": "Başlatılıyor...",
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "error": None,
                "result": None,
                "metadata": metadata or {}
            }
            self._executions[exec_id] = entry
            self._save()
            return entry

    def update(self, exec_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        with self.lock:
            if exec_id not in self._executions:
                return None
            self._executions[exec_id].update(kwargs)
            self._save()
            return self._executions[exec_id]

    def complete(self, exec_id: str, result: Any = None) -> Optional[Dict[str, Any]]:
        with self.lock:
            if exec_id not in self._executions:
                return None
            self._executions[exec_id]["status"] = "completed"
            self._executions[exec_id]["progress"] = 100
            self._executions[exec_id]["completed_at"] = datetime.now().isoformat()
            self._executions[exec_id]["result"] = result
            self._save()
            return self._executions[exec_id]

    def fail(self, exec_id: str, error: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            if exec_id not in self._executions:
                return None
            self._executions[exec_id]["status"] = "failed"
            self._executions[exec_id]["completed_at"] = datetime.now().isoformat()
            self._executions[exec_id]["error"] = str(error)
            self._save()
            return self._executions[exec_id]

    def get(self, exec_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self._executions.get(exec_id)

    def list_all(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self._executions)


# Global singleton
execution_manager = ExecutionManager()
