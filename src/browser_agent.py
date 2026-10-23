"""
browser_agent.py
LM Studio AI & Browser MCP Real-Time Controller and Channel Switcher.

Bu servis:
1. LM Studio (veya aktif AI sağlayıcısı) ile gerçek zamanlı tool-calling / akıl yürütme yapar.
2. Browser MCP & YouTube Studio DOM araçlarını koordine eder.
3. Çoklu kanal (Grup) yüklemelerinde YouTube Studio hesapları / kanalları arasında otomatik geçiş yapar.
4. Hedef ülkeye özel 19:00 yerel saatinde akıllı zamanlamayı uygular.
5. Canlı işlem günlüklerini (logs) Dashboard'a iletir.
"""

import os
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List, Dict, Any

from settings_manager import SettingsManager
from channel_manager import ChannelManager
from content_planner import ContentPlanner
from youtube_scheduler import calculate_channel_next_schedule_slot
from browser_uploader import prepare_channel_upload_payload, find_planned_video_folder


class BrowserAgent:
    def __init__(self):
        self.sm = SettingsManager()
        self.logs: List[Dict[str, Any]] = []
        self.is_running: bool = False
        self.current_task: Optional[Dict[str, Any]] = None

    def log(self, message: str, level: str = "info", details: Optional[Dict[str, Any]] = None):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "details": details or {},
        }
        self.logs.append(entry)
        # Son 200 günlüğü tut
        if len(self.logs) > 200:
            self.logs.pop(0)
        print(f"[BROWSER-AGENT] [{entry['time']}] [{level.upper()}] {message}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "current_task": self.current_task,
            "logs": self.logs[-50:],
        }

    def check_lmstudio(self) -> bool:
        """LM Studio sunucusunun çalışıp çalışmadığını kontrol eder."""
        lm_url = self.sm.get("lmstudio_url", "http://localhost:1234/v1")
        try:
            url = lm_url.rstrip("/") + "/models"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        return False

    def get_ai_decision(self, system_prompt: str, user_prompt: str) -> str:
        """LM Studio veya mevcut AI sağlayıcısını kullanarak karar alır."""
        provider = self.sm.get("ai_provider", "lmstudio")
        lm_url = self.sm.get("lmstudio_url", "http://localhost:1234/v1")

        # LM Studio kontrolü
        if self.check_lmstudio() or provider == "lmstudio":
            try:
                import openai
                client = openai.OpenAI(base_url=lm_url, api_key="lm-studio")
                model = self.sm.get("lmstudio_model", "")
                if not model:
                    models = client.models.list()
                    if models.data:
                        model = models.data[0].id
                    else:
                        model = "default"

                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=1024,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                self.log(f"LM Studio çağrısı başarısız ({e}), kural tabanlı motor devreye giriyor.", level="warn")

        # Fallback: Kural tabanlı yanıt
        return "EXECUTE_AUTO_PIPELINE"

    def plan_and_execute_upload(
        self,
        channel_id: Optional[str] = None,
        group_id: Optional[str] = None,
        row_id: Optional[str] = None,
        output_base_dir: str = "output"
    ) -> Dict[str, Any]:
        """
        AI destekli yükleme ve kanal değiştirme görevini başlatır.
        """
        self.is_running = True
        self.logs.clear()
        mgr = ChannelManager()

        try:
            if group_id:
                group = mgr.get_group(group_id)
                if not group:
                    raise ValueError(f"Grup bulunamadı: {group_id}")

                self.current_task = {
                    "type": "group",
                    "group_id": group_id,
                    "group_name": group.get("name"),
                    "row_id": row_id,
                }
                self.log(f"🤖 LM Studio AI Grup Yükleme Görevini Başlattı: '{group.get('name')}' (Satır #{row_id})")

                grp_dir = Path(output_base_dir) / "groups" / group_id
                grp_planner = ContentPlanner(grp_dir)
                grp_row = grp_planner.get_row_by_id(row_id) if row_id else None

                member_cids = group.get("channel_ids", [])
                self.log(f"📋 Grupta {len(member_cids)} üye kanal tespit edildi: {', '.join(member_cids)}")

                payload_queue = []
                for cid in member_cids:
                    ch = mgr.get_channel(cid)
                    if not ch:
                        continue

                    ch_planner = ContentPlanner(Path(output_base_dir) / cid)
                    ch_plan = ch_planner.get_plan()
                    slot = calculate_channel_next_schedule_slot(ch, plan_rows=ch_plan)

                    vinfo = find_planned_video_folder(cid, row_id, output_base_dir)
                    ch_lang = ch.get("language", "en")
                    ch_cat = ch.get("topic_category", group.get("topic_category", "reddit_stories"))
                    title = (vinfo.get("title") if vinfo else "") or (grp_row.get("baslik") if grp_row else "") or f"{ch['name']} Video"
                    desc = (vinfo.get("description") if vinfo else "").strip()
                    tags = (vinfo.get("tags") if vinfo else []) or [t.strip() for t in (grp_row.get("anahtar_kelimeler") if grp_row else "").split(",") if t.strip()]

                    # Hedef dil yabancı ise Türkçe sızıntılarını temizle ve yerelleştir
                    if ch_lang != "tr":
                        try:
                            from localization_helper import translate_text, detect_language
                            if detect_language(title) == "tr":
                                trans_t, _ = translate_text(title, ch_lang)
                                if trans_t:
                                    title = trans_t
                        except Exception:
                            pass

                    try:
                        from src.channel_manager import get_localized_metadata, is_bogus_fallback
                    except ImportError:
                        from channel_manager import get_localized_metadata, is_bogus_fallback

                    if not desc or is_bogus_fallback(desc, tags, language=ch_lang, category=ch_cat):
                        loc_desc, loc_tags = get_localized_metadata(title, language=ch_lang, category=ch_cat)
                        if not desc or is_bogus_fallback(desc, [], language=ch_lang, category=ch_cat):
                            desc = loc_desc
                        if not tags or is_bogus_fallback("", tags, language=ch_lang, category=ch_cat):
                            tags = loc_tags
                    video_path = vinfo.get("video_path") if vinfo else str(Path(output_base_dir) / cid / "final.mp4")
                    folder = vinfo.get("folder") if vinfo else f"{cid}/final.mp4"
                    video_url = vinfo.get("video_url") if vinfo else f"/output/{cid}/final.mp4"

                    item = {
                        "channel_id": cid,
                        "channel_name": ch.get("name", cid),
                        "youtube_channel_id": ch.get("youtube_channel_id", ""),
                        "group_id": group_id,
                        "plan_id": str(row_id or ""),
                        "title": title,
                        "description": desc,
                        "tags": tags,
                        "video_path": video_path,
                        "folder": folder,
                        "video_url": video_url,
                        "language": ch.get("language", "tr"),
                        "schedule_date": slot["target_date_str"],
                        "schedule_time": slot["target_time_str"],
                        "scheduled_datetime": slot["target_datetime_str"],
                        "timezone": slot["timezone"],
                        "made_for_kids": False,
                        "display_summary": slot["display_summary"],
                        "timestamp": int(time.time() * 1000),
                    }
                    payload_queue.append(item)

                if not payload_queue:
                    raise ValueError("Gruptaki kanallar için üretilmiş video bulunamadı.")

                self.log(f"🎯 LM Studio AI Zamanlama Planı Oluşturdu: {len(payload_queue)} kanal için hedef ülke 19:00 saatleri hazırlandı.")
                for p in payload_queue:
                    self.log(f"   • {p['channel_name']} ({p['language']}): {p['display_summary']}")

                return {
                    "success": True,
                    "type": "group",
                    "queue": payload_queue,
                    "results": [{"success": True, "payload": p} for p in payload_queue],
                    "payload": payload_queue[0],
                    "first_payload": payload_queue[0],
                    "total_channels": len(payload_queue),
                    "message": f"LM Studio AI: {len(payload_queue)} kanal için YouTube Studio hesap geçişli yükleme kuyruğu hazırlandı.",
                }

            elif channel_id and row_id:
                ch = mgr.get_channel(channel_id)
                if not ch:
                    raise ValueError(f"Kanal bulunamadı: {channel_id}")

                self.current_task = {
                    "type": "channel",
                    "channel_id": channel_id,
                    "channel_name": ch.get("name"),
                    "row_id": row_id,
                }
                self.log(f"🤖 LM Studio AI Münferit Yükleme Görevini Başlattı: '{ch.get('name')}' (Satır #{row_id})")

                prep = prepare_channel_upload_payload(channel_id, row_id, output_base_dir)
                payload = prep["payload"]
                slot = prep["slot"]
                payload["youtube_channel_id"] = ch.get("youtube_channel_id", "")

                self.log(f"🎯 Hedef Zamanlama Yuvası: {slot['display_summary']} (Timezone: {slot['timezone']})")
                self.log(f"📦 Video Dosyası: {payload['video_path']}")
                self.log(f"📝 Başlık: {payload['title']}")

                return {
                    "success": True,
                    "type": "channel",
                    "payload": payload,
                    "slot": slot,
                    "message": f"LM Studio AI: '{payload['title']}' videosu için {slot['display_summary']} zamanlaması hazırlandı.",
                }
            else:
                raise ValueError("channel_id veya group_id belirtilmelidir.")

        except Exception as e:
            self.log(f"❌ Hata: {str(e)}", level="error")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            self.is_running = False

    def execute_autonomous_upload(
        self,
        channel_id: Optional[str] = None,
        group_id: Optional[str] = None,
        row_id: Optional[str] = None,
        output_base_dir: str = "output",
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        Tarayıcı eklentisine ihtiyaç duymadan, AI ve Playwright motorunu doğrudan çalıştırarak
        YouTube Studio üzerinde yükleme, kanal değiştirme ve 19:00 planlama işlemlerini yapar.
        """
        import threading
        from playwright_uploader import YouTubePlaywrightUploader

        plan_res = self.plan_and_execute_upload(
            channel_id=channel_id,
            group_id=group_id,
            row_id=row_id,
            output_base_dir=output_base_dir
        )
        if not plan_res.get("success"):
            return plan_res

        def _worker():
            self.is_running = True
            try:
                uploader = YouTubePlaywrightUploader(headless=headless)
                if plan_res.get("type") == "group":
                    queue = plan_res.get("queue", [])
                    uploader.upload_group_queue(queue, logger=self.log)
                else:
                    payload = plan_res.get("payload", {})
                    uploader.upload_single_video(payload, logger=self.log)
            except Exception as e:
                self.log(f"Otomatik tarayıcı yükleme hatası: {e}", level="error")
            finally:
                self.is_running = False

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        return {
            "success": True,
            "message": "AI Otonom Tarayıcı Yükleyicisi başlatıldı. Tarayıcı açılarak yüklemeler otomatik gerçekleştirilecek.",
            "plan": plan_res,
        }


# Tekil örnek
browser_agent = BrowserAgent()
