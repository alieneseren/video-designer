"""
casper_terminal.py
Casper AI Terminal Yöneticisi.
Kullanıcı 'Fikirleri Uygula' butonuna tıkladığında:
1. Kaydedilen fikirleri alır.
2. 'agy --dangerously-skip-permissions -p "..."' otonom oturumunu başlatır.
3. Çıktıyı canlı olarak Web terminaline akıtır.
4. Kilit çakışmalarını önlemek için bağımsız otonom çalıştırma bayrağını kullanır.
"""

from __future__ import annotations
import os
import sys
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
try:
    from casper_advisor import CasperAdvisor, CONVERSATION_ID
except ImportError:
    from src.casper_advisor import CasperAdvisor, CONVERSATION_ID

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# agy binary yolu
AGY_BIN = "/Users/alienes/.local/bin/agy"
if not os.path.exists(AGY_BIN):
    AGY_BIN = "agy"


class CasperTerminalSession:
    """Tekil bir agy terminal oturumunu yönetir ve çıktılarını depolar."""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.logs: List[str] = []
        self.is_running: bool = False
        self.exit_code: Optional[int] = None
        self._lock = threading.Lock()

    def add_log(self, text: str):
        with self._lock:
            self.logs.append(text)
            if len(self.logs) > 2000:
                self.logs.pop(0)

    def get_logs(self, since_index: int = 0) -> List[str]:
        with self._lock:
            return self.logs[since_index:]

    def run_agy_command(self, prompt: str, conversation_id: str = CONVERSATION_ID):
        """agy komutunu çalıştırır ve çıktıları canlı toplar."""
        if self.is_running:
            return {"error": "Zaten çalışan bir oturum var."}

        self.logs = []
        self.is_running = True
        self.exit_code = None

        # Not: Aktif oturum lock çakışmasını engellemek için -p bayrağı doğrudan verilir
        cmd = [
            AGY_BIN,
            "--dangerously-skip-permissions",
            "-p",
            prompt
        ]

        def _worker():
            self.add_log("$ agy --dangerously-skip-permissions -p [Casper Direktifleri]")
            self.add_log(f"[CASPER TERMINAL] Gemini bağlantısı kuruluyor... (Aktif Workspace: {_PROJECT_ROOT.name})")
            self.add_log("[CASPER TERMINAL] Otonom geliştirici motoru hazırlandı.")
            self.add_log("─" * 60)

            try:
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(_PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env
                )

                # Yanıt gelene kadar kalp atışı (heartbeat) gösteren mini iş parçacığı
                stop_heartbeat = threading.Event()
                first_line_received = threading.Event()

                def _heartbeat():
                    elapsed = 0
                    while not stop_heartbeat.is_set() and not first_line_received.is_set():
                        time.sleep(3)
                        elapsed += 3
                        if not first_line_received.is_set() and self.is_running:
                            self.add_log(f"[CASPER TERMINAL] Gemini istekleri inceliyor ve kodu planlıyor ({elapsed}s)...")

                hb_thread = threading.Thread(target=_heartbeat, daemon=True)
                hb_thread.start()

                for line in iter(self.process.stdout.readline, ''):
                    first_line_received.set()
                    clean_line = line.rstrip()
                    if clean_line:
                        self.add_log(clean_line)

                stop_heartbeat.set()
                self.process.stdout.close()
                self.exit_code = self.process.wait()

                if self.exit_code == 0:
                    self.add_log("─" * 60)
                    self.add_log("✅ [CASPER TERMINAL] Geliştirmeler Gemini tarafından başarıyla uygulandı!")
                    # Kaydedilen fikirleri 'applied' olarak işaretle
                    for idea in CasperAdvisor.list_ideas(status="saved"):
                        CasperAdvisor.set_idea_status(idea["id"], "applied")
                else:
                    self.add_log(f"⚠️ [CASPER TERMINAL] Oturum {self.exit_code} koduyla tamamlandı.")

            except Exception as e:
                self.add_log(f"❌ [CASPER TERMINAL HATA]: {str(e)}")
            finally:
                self.is_running = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return {"status": "started", "conversation_id": conversation_id}

    def stop(self):
        if self.process and self.is_running:
            try:
                self.process.terminate()
                self.add_log("🛑 [CASPER TERMINAL] Oturum kullanıcı tarafından durduruldu.")
            except Exception:
                pass
            self.is_running = False


# Global tekil oturum
terminal_session = CasperTerminalSession()
