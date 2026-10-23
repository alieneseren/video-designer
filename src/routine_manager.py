"""
src/routine_manager.py
Rutinler & Zamanlanmış Çoklu Kanal Otomasyon Yöneticisi
- Günlük / Belirli günlerde saatlik rutinler tanımlar.
- Belirlenen saatte onay bildirimi üretir (veya doğrudan çalıştırır).
- Kanalların içerik planını kontrol eder.
- Gemini / AI senaryolarını ve görsellerini sırayla üretir.
- Her video üretimi arasında CPU dinlenmesi (cooldown) sağlar.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DEFAULT_ROUTINES_FILE = Path("config/routines.json")


class RoutineManager:
    def __init__(self, file_path: Path = DEFAULT_ROUTINES_FILE):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self):
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_all([])

    def _load_all(self) -> List[Dict[str, Any]]:
        try:
            if not self.file_path.exists():
                return []
            content = self.file_path.read_text(encoding="utf-8")
            if not content.strip():
                return []
            return json.loads(content)
        except Exception as e:
            print(f"[ROUTINE-MGR] Okuma hatası: {e}")
            return []

    def _save_all(self, routines: List[Dict[str, Any]]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(routines, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def all_routines(self) -> List[Dict[str, Any]]:
        return self._load_all()

    def get_routine(self, routine_id: str) -> Optional[Dict[str, Any]]:
        for r in self._load_all():
            if r.get("id") == routine_id:
                return r
        return None

    def add_routine(self, data: Dict[str, Any]) -> Dict[str, Any]:
        routines = self._load_all()
        now = datetime.now()
        routine_id = data.get("id") or f"routine_{now.strftime('%Y%m%d_%H%M%S')}"

        new_routine = {
            "id": routine_id,
            "name": (data.get("name") or "Yeni Rutin").strip(),
            "channel_ids": data.get("channel_ids", []),
            "schedule_time": (data.get("schedule_time") or "10:00").strip(),
            "days": data.get("days", ["all"]),
            "rest_minutes": max(0, int(data.get("rest_minutes", 5))),
            "require_approval": bool(data.get("require_approval", True)),
            "auto_open_gemini": bool(data.get("auto_open_gemini", True)),
            "active": bool(data.get("active", True)),
            "status": "idle",
            "last_run": None,
            "last_notified_date": None,
            "snoozed_until": None,
            "created_at": now.isoformat(),
        }

        routines.append(new_routine)
        self._save_all(routines)
        return new_routine

    def update_routine(self, routine_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        routines = self._load_all()
        target = None
        for r in routines:
            if r.get("id") == routine_id:
                target = r
                break
        if not target:
            return None

        if "name" in data and data["name"] is not None:
            target["name"] = str(data["name"]).strip()
        if "channel_ids" in data and data["channel_ids"] is not None:
            target["channel_ids"] = list(data["channel_ids"])
        if "schedule_time" in data and data["schedule_time"] is not None:
            target["schedule_time"] = str(data["schedule_time"]).strip()
        if "days" in data and data["days"] is not None:
            target["days"] = list(data["days"])
        if "rest_minutes" in data and data["rest_minutes"] is not None:
            target["rest_minutes"] = max(0, int(data["rest_minutes"]))
        if "require_approval" in data and data["require_approval"] is not None:
            target["require_approval"] = bool(data["require_approval"])
        if "auto_open_gemini" in data and data["auto_open_gemini"] is not None:
            target["auto_open_gemini"] = bool(data["auto_open_gemini"])
        if "active" in data and data["active"] is not None:
            target["active"] = bool(data["active"])
        if "status" in data and data["status"] is not None:
            target["status"] = str(data["status"])

        self._save_all(routines)
        return target

    def delete_routine(self, routine_id: str) -> bool:
        routines = self._load_all()
        orig_len = len(routines)
        routines = [r for r in routines if r.get("id") != routine_id]
        if len(routines) < orig_len:
            self._save_all(routines)
            return True
        return False

    def toggle_routine(self, routine_id: str) -> Optional[Dict[str, Any]]:
        routine = self.get_routine(routine_id)
        if not routine:
            return None
        return self.update_routine(routine_id, {"active": not routine.get("active", True)})

    def set_routine_status(self, routine_id: str, status: str, extra: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        routines = self._load_all()
        target = None
        for r in routines:
            if r.get("id") == routine_id:
                target = r
                break
        if not target:
            return None

        target["status"] = status
        if extra:
            target.update(extra)

        self._save_all(routines)
        return target

    def check_scheduled_routines(self) -> List[Dict[str, Any]]:
        """
        Şu anki saat ve günü kontrol eder. Zamanı gelen aktif rutinleri tespit eder.
        require_approval=True ise status='waiting_approval' yapar ve bekletir.
        require_approval=False ise tetiklenmeye hazır olarak döner.
        """
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")
        weekday_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        current_weekday = weekday_map[now.weekday()]

        routines = self._load_all()
        triggered = []
        updated = False

        for r in routines:
            if not r.get("active", True):
                continue

            days = r.get("days", ["all"])
            if "all" not in days and current_weekday not in days:
                continue

            # Erteleme kontrolü (snooze)
            snoozed_until = r.get("snoozed_until")
            if snoozed_until:
                try:
                    snooze_dt = datetime.fromisoformat(snoozed_until)
                    if now < snooze_dt:
                        continue
                    else:
                        r["snoozed_until"] = None
                        updated = True
                except Exception:
                    r["snoozed_until"] = None

            sched_time = r.get("schedule_time", "10:00")
            last_notified = r.get("last_notified_date")
            status = r.get("status", "idle")

            # Eğer bugün zaten tamamlandı veya onay bekliyor/çalışıyorsa tekrar bildirme
            if last_notified == today_str and status in ("completed", "waiting_approval", "running"):
                continue

            # Saat eşleşmesi kontrolü
            if sched_time == current_time_str:
                r["last_notified_date"] = today_str
                if r.get("require_approval", True):
                    r["status"] = "waiting_approval"
                    r["pending_since"] = now.isoformat()
                    # Casper AI: Zamanlanmış Rutin Bildirimi & Webhook
                    try:
                        self.send_webhook_notification("waiting_approval", r)
                    except Exception as wb_err:
                        print(f"[ROUTINE-MGR] Webhook gönderme uyarısı: {wb_err}")
                else:
                    r["status"] = "ready_to_run"
                triggered.append(r)
                updated = True

        if updated:
            self._save_all(routines)

        return triggered

    def send_webhook_notification(
        self,
        event: str,
        data: Dict[str, Any],
        custom_webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Casper AI: Zamanlanmış İçerik Rutinlerinde Akıllı Bildirim & Slack/Telegram/Generic Webhook.
        event: 'waiting_approval' | 'completed' | 'failed' | 'test'
        data: Rutin bilgileri, kanal özetleri veya video çıktıları.
        """
        import requests

        try:
            from settings_manager import SettingsManager
        except ImportError:
            from src.settings_manager import SettingsManager

        settings_mgr = SettingsManager()
        routine_name = data.get("name") or data.get("routine_name") or "İçerik Rutini"
        routine_id = data.get("id") or data.get("routine_id") or "bilinmiyor"
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

        # Hedef URL ve kimlik bilgileri
        target_webhook = (
            custom_webhook_url
            or data.get("webhook_url")
            or settings_mgr.get("routine_webhook_url")
            or settings_mgr.get("slack_webhook_url")
        )
        telegram_token = settings_mgr.get("telegram_bot_token") or data.get("telegram_bot_token")
        telegram_chat = settings_mgr.get("telegram_chat_id") or data.get("telegram_chat_id")

        results = {
            "success": False,
            "dispatched_to": [],
            "errors": []
        }

        # Bildirim Başlığı ve Mesajı Oluşturma
        if event == "waiting_approval":
            title = f"⏰ Rutin Onay Bekliyor: {routine_name}"
            msg_text = (
                f"🚨 *Zamanlanmış Rutin Onay Bekliyor!*\n\n"
                f"📌 *Rutin:* {routine_name} (`{routine_id}`)\n"
                f"🕒 *Saat:* {now_str}\n"
                f"Kanalların video üretimi için onayınız bekleniyor. Sisteme girerek veya onay vererek başlatabilirsiniz."
            )
        elif event == "completed":
            s_count = data.get("success_count", 0)
            t_count = data.get("total_videos", 0)
            title = f"✅ Rutin Tamamlandı: {routine_name}"
            msg_text = (
                f"🎉 *Rutin Başarıyla Tamamlandı!*\n\n"
                f"📌 *Rutin:* {routine_name}\n"
                f"🎬 *Üretilen Video:* {s_count}/{t_count}\n"
                f"🕒 *Tarih:* {now_str}\n"
                f"Detay: {data.get('message', 'Tüm içerikler başarıyla render edildi.')}"
            )
        elif event == "failed":
            title = f"❌ Rutin Başarısız: {routine_name}"
            msg_text = (
                f"⚠️ *Rutin Hatası!*\n\n"
                f"📌 *Rutin:* {routine_name}\n"
                f"🕒 *Tarih:* {now_str}\n"
                f"Hata detayı: {data.get('message', 'Video üretimi sırasında hata oluştu.')}"
            )
        else: # test
            title = f"🔔 Webhook Test Bildirimi: {routine_name}"
            msg_text = (
                f"🔔 *Rutin Webhook Testi Başarılı!*\n\n"
                f"📌 *Rutin:* {routine_name}\n"
                f"🕒 *Test Zamanı:* {now_str}\n"
                f"Otomasyon webhook ve haberci sistemi sorunsuz çalışıyor."
            )

        payload_generic = {
            "event": event,
            "routine_id": routine_id,
            "routine_name": routine_name,
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": msg_text,
            "data": data
        }

        # 1. Telegram Entegrasyonu
        if telegram_token and telegram_chat:
            try:
                tg_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                tg_payload = {
                    "chat_id": telegram_chat,
                    "text": msg_text,
                    "parse_mode": "Markdown"
                }
                r = requests.post(tg_url, json=tg_payload, timeout=8)
                if r.status_code in (200, 201):
                    results["dispatched_to"].append("telegram")
                    results["success"] = True
                else:
                    results["errors"].append(f"Telegram ({r.status_code}): {r.text[:120]}")
            except Exception as tg_err:
                results["errors"].append(f"Telegram hatası: {tg_err}")

        # 2. Slack veya Standart Webhook Entegrasyonu
        if target_webhook:
            try:
                is_slack = "hooks.slack.com" in target_webhook or "slack" in target_webhook.lower()
                if is_slack:
                    webhook_body = {
                        "text": f"{title}\n{msg_text}",
                        "blocks": [
                            {
                                "type": "header",
                                "text": {"type": "plain_text", "text": title[:150]}
                            },
                            {
                                "type": "section",
                                "text": {"type": "mrkdwn", "text": msg_text}
                            }
                        ]
                    }
                else:
                    webhook_body = payload_generic

                r = requests.post(target_webhook, json=webhook_body, timeout=8)
                if r.status_code in (200, 201, 204):
                    results["dispatched_to"].append("slack" if is_slack else "generic_webhook")
                    results["success"] = True
                else:
                    results["errors"].append(f"Webhook ({r.status_code}): {r.text[:120]}")
            except Exception as wh_err:
                results["errors"].append(f"Webhook hatası: {wh_err}")

        # Eğer webhook ya da telegram tanımlı değilse en azından log tut ve testte belirt
        if not target_webhook and not (telegram_token and telegram_chat):
            results["errors"].append("Webhook URL veya Telegram kimlik bilgisi ayarlanmamış.")
            results["payload"] = payload_generic

        return results

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Kullanıcı onayı bekleyen rutinleri döner."""
        self.check_scheduled_routines()
        routines = self._load_all()
        return [r for r in routines if r.get("status") == "waiting_approval" and r.get("active", True)]

    def snooze_routine(self, routine_id: str, minutes: int = 15) -> Optional[Dict[str, Any]]:
        """Rutini belirtilen dakika kadar erteler."""
        snooze_until = datetime.now() + timedelta(minutes=minutes)
        return self.set_routine_status(
            routine_id,
            "idle",
            {"snoozed_until": snooze_until.isoformat()}
        )

    def dismiss_routine(self, routine_id: str) -> Optional[Dict[str, Any]]:
        """Rutini bugünlük iptal eder / sıfırlar."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        return self.set_routine_status(
            routine_id,
            "idle",
            {"last_notified_date": today_str, "snoozed_until": None}
        )

    def inspect_routine_plans(self, routine_id: str) -> Dict[str, Any]:
        """
        Rutin içindeki kanalların içerik planlarını tarar.
        Her kanalın üretilecek sonraki konusunu, sırasını ve durumunu döner.
        """
        routine = self.get_routine(routine_id)
        if not routine:
            return {"success": False, "error": "Rutin bulunamadı"}

        try:
            from channel_manager import ChannelManager
            from content_planner import ContentPlanner
            from settings_manager import SettingsManager
        except ImportError:
            from src.channel_manager import ChannelManager
            from src.content_planner import ContentPlanner
            from src.settings_manager import SettingsManager

        settings = SettingsManager()
        output_dir = settings.get("output_dir", "output")
        cm = ChannelManager()

        channel_plans = []
        for cid in routine.get("channel_ids", []):
            ch = cm.get_channel(cid)
            ch_name = ch.get("name", cid) if ch else cid
            ch_lang = ch.get("language", "tr") if ch else "tr"
            ch_cat = ch.get("topic_category", "space") if ch else "space"

            channel_dir = Path(output_dir) / cid
            planner = ContentPlanner(channel_dir)

            item = planner.get_next_unproduced()
            if item:
                channel_plans.append({
                    "channel_id": cid,
                    "channel_name": ch_name,
                    "language": ch_lang,
                    "topic_category": ch_cat,
                    "has_unproduced": True,
                    "row_id": str(item.get("id")),
                    "title": item.get("baslik") or item.get("konu"),
                    "topic": item.get("konu"),
                    "planned_item": item
                })
            else:
                channel_plans.append({
                    "channel_id": cid,
                    "channel_name": ch_name,
                    "language": ch_lang,
                    "topic_category": ch_cat,
                    "has_unproduced": False,
                    "row_id": None,
                    "title": None,
                    "topic": None,
                    "message": "Üretilecek konu kalmadı (İçerik planı boş)"
                })

        return {
            "success": True,
            "routine_id": routine_id,
            "routine_name": routine.get("name"),
            "rest_minutes": routine.get("rest_minutes", 5),
            "channels": channel_plans,
            "ready_count": sum(1 for c in channel_plans if c["has_unproduced"]),
            "total_count": len(channel_plans)
        }
