"""
materials_manager.py
====================
Kanalların "Üretim Metaryalleri" klasörünü yönetir.
Gemini eklentisinden veya sistemden gelen senaryo, prompt ve görsel
üretim paketlerini saklar, listeler ve video üretim kuyruğuna besler.
"""

from __future__ import annotations
import base64
import json
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from settings_manager import SettingsManager
settings_mgr = SettingsManager()
from channel_manager import ChannelManager
from content_planner import ContentPlanner

MATERIALS_FOLDER_NAME = "Üretim Metaryalleri"
ALT_MATERIALS_FOLDER_NAME = "Üretim Materyalleri"


def _slugify(text: str, max_len: int = 30) -> str:
    """Türkçe karakterleri ve özel işaretleri dosya adı dostu hale getirir."""
    if not text:
        return "icerik"
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ ", "cgiosuCGIOSU_")
    cleaned = text.translate(tr_map)
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_len] or "icerik"


class MaterialsManager:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or settings_mgr.get("output_dir", "output"))

    def _resolve_target(self, channel_id: str) -> tuple[bool, str, Path]:
        """
        Kanal veya grup kimliğini çözer:
        (is_group, clean_id, target_base_dir) döndürür.
        """
        if not channel_id:
            return False, "", self.output_dir
            
        cid = str(channel_id).strip()
        mgr = ChannelManager()
        known_group_ids = {g["id"] for g in mgr.all_groups()}
        
        # 1. group: prefix kontrolü
        if cid.startswith("group:"):
            clean_grp_id = cid[6:].strip()
            return True, clean_grp_id, self.output_dir / "groups" / clean_grp_id
            
        # 2. Doğrudan grup ID'si kontrolü
        if cid in known_group_ids or (self.output_dir / "groups" / cid).exists():
            return True, cid, self.output_dir / "groups" / cid
            
        # 3. Normal kanal
        return False, cid, self.output_dir / cid

    def get_channel_materials_dir(self, channel_id: str) -> Path:
        """Kanalın veya grubun Üretim Metaryalleri klasör yolunu döner, yoksa oluşturur."""
        is_group, clean_id, base_dir = self._resolve_target(channel_id)
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Önceden alternatif isimle oluşturulmuşsa onu koru, yoksa standart klasörü aç
        alt_dir = base_dir / ALT_MATERIALS_FOLDER_NAME
        target_dir = base_dir / MATERIALS_FOLDER_NAME
        if alt_dir.exists() and not target_dir.exists():
            return alt_dir
            
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def save_material(
        self,
        channel_id: str,
        script: dict,
        title: Optional[str] = None,
        topic: Optional[str] = None,
        row_id: Optional[str] = None,
        images: Optional[dict] = None,
        target_env: str = "local",
        notes: str = ""
    ) -> dict:
        """
        Yeni bir video üretim materyali paketi oluşturur ve diske kaydeder.
        Görseller base64 ise dosya olarak çözülüp klasöre yazılır.
        Kanal grupları için output/groups/<group_id>/Üretim Metaryalleri altına kaydeder.
        """
        is_group, clean_id, target_base_dir = self._resolve_target(channel_id)
        mat_dir = self.get_channel_materials_dir(channel_id)
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        video_title = title or script.get("title") or topic or f"Video_{now_str}"
        title_slug = _slugify(video_title)
        
        folder_name = f"mat_{now_str}_{title_slug}"
        item_dir = mat_dir / folder_name
        item_dir.mkdir(parents=True, exist_ok=True)

        # Görselleri diske kaydet
        saved_images = {}
        if images and isinstance(images, dict):
            for k, val in images.items():
                if not val:
                    continue
                val_str = str(val).strip()
                if val_str.startswith("data:image/") or (len(val_str) > 200 and not os.path.exists(val_str)):
                    try:
                        # Base64 çöz ve kaydet
                        if "," in val_str:
                            b64_data = val_str.split(",", 1)[1]
                        else:
                            b64_data = val_str
                        img_bytes = base64.b64decode(b64_data)
                        img_filename = f"scene_{k}.jpg"
                        img_path = item_dir / img_filename
                        img_path.write_bytes(img_bytes)
                        saved_images[str(k)] = str(img_path)
                    except Exception as e:
                        print(f"[MATERIALS] Görsel çözme uyarısı ({k}): {e}")
                        saved_images[str(k)] = val_str
                else:
                    # Var olan dosya yolu
                    saved_images[str(k)] = val_str

        # Sahneleri ve sahne sayısını tespit et (hem tekil hem çok dilli gruplar için)
        scenes = []
        if isinstance(script, dict):
            if "scenes" in script and isinstance(script["scenes"], list):
                scenes = script["scenes"]
            else:
                for lk in ("tr", "en", "es", "de"):
                    if lk in script and isinstance(script[lk], dict) and "scenes" in script[lk]:
                        scenes = script[lk]["scenes"]
                        break
        scenes_count = len(scenes) if isinstance(scenes, list) else 0

        material_payload = {
            "id": folder_name,
            "material_id": folder_name,
            "channel_id": f"group:{clean_id}" if is_group else channel_id,
            "group_id": clean_id if is_group else None,
            "is_group": is_group,
            "row_id": str(row_id or ""),
            "title": video_title,
            "topic": topic or video_title,
            "created_at": datetime.now().isoformat(),
            "status": "ready",  # ready | producing | in_cloud_queue | produced | downloaded | failed
            "target_env": target_env,
            "notes": notes,
            "script": script,
            "scenes": scenes,
            "images": saved_images,
            "scene_count": scenes_count,
            "folder_path": str(item_dir)
        }

        meta_file = item_dir / "material.json"
        meta_file.write_text(json.dumps(material_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        # İlgili satır içerik planında varsa durumunu güncelle
        if row_id:
            try:
                planner = ContentPlanner(target_base_dir)
                planner.update_row_status(row_id, "Materyaller Hazır")
            except Exception as e:
                print(f"[MATERIALS] İçerik planı güncelleme uyarısı: {e}")

        return material_payload

    def list_materials(self, channel_id: Optional[str] = None) -> list[dict]:
        """Kanalın, grubun veya tüm sistemin Üretim Metaryalleri klasöründeki paketleri listeler."""
        mgr = ChannelManager()
        channels = {c["channel_id"]: c for c in mgr.all_channels()}
        groups = {g["id"]: g for g in mgr.all_groups()}

        targets_to_scan = []  # List of tuples: (is_group, target_id, display_name, lang, cat, target_dir)

        if channel_id:
            is_group, clean_id, target_dir = self._resolve_target(channel_id)
            if is_group:
                grp = groups.get(clean_id, {})
                targets_to_scan.append((
                    True,
                    clean_id,
                    f"📁 [GRUP] {grp.get('name') or clean_id}",
                    "multi",
                    grp.get("topic_category", "general"),
                    target_dir
                ))
            else:
                ch_info = channels.get(clean_id, {})
                targets_to_scan.append((
                    False,
                    clean_id,
                    ch_info.get("name") or clean_id,
                    ch_info.get("language", "tr"),
                    ch_info.get("topic_category", "general"),
                    target_dir
                ))
                # Eğer bu bireysel kanal bir gruba dahilse, o grubun materyallerini de ekle!
                parent_group = mgr.get_channel_group(clean_id)
                if parent_group:
                    pg_id = parent_group["id"]
                    targets_to_scan.append((
                        True,
                        pg_id,
                        f"📁 [GRUP] {parent_group.get('name') or pg_id}",
                        "multi",
                        parent_group.get("topic_category", "general"),
                        self.output_dir / "groups" / pg_id
                    ))
        else:
            # 1. Tüm kanalları tara
            all_cids = list(channels.keys())
            if self.output_dir.exists():
                for d in self.output_dir.iterdir():
                    if d.is_dir() and d.name not in all_cids and not d.name.startswith(".") and d.name != "groups":
                        all_cids.append(d.name)
            
            for cid in all_cids:
                ch_info = channels.get(cid, {})
                targets_to_scan.append((
                    False,
                    cid,
                    ch_info.get("name") or cid,
                    ch_info.get("language", "tr"),
                    ch_info.get("topic_category", "general"),
                    self.output_dir / cid
                ))
            
            # 2. VE TÜM KANAL GRUPLARINI DA TARA!
            all_gids = list(groups.keys())
            groups_base = self.output_dir / "groups"
            if groups_base.exists():
                for d in groups_base.iterdir():
                    if d.is_dir() and d.name not in all_gids and not d.name.startswith("."):
                        all_gids.append(d.name)
            
            for gid in all_gids:
                grp = groups.get(gid, {})
                targets_to_scan.append((
                    True,
                    gid,
                    f"📁 [GRUP] {grp.get('name') or gid}",
                    "multi",
                    grp.get("topic_category", "general"),
                    groups_base / gid
                ))

        all_materials = []
        scanned_paths = set()

        for is_grp, tid, d_name, d_lang, d_cat, base_path in targets_to_scan:
            # Hem standart hem alternatif klasör isimlerini tara
            candidate_dirs = [
                base_path / MATERIALS_FOLDER_NAME,
                base_path / ALT_MATERIALS_FOLDER_NAME,
            ]
            for mat_dir in candidate_dirs:
                if not mat_dir.exists() or not mat_dir.is_dir():
                    continue

                for sub in mat_dir.iterdir():
                    if not sub.is_dir() or sub.name.startswith("."):
                        continue
                    if str(sub) in scanned_paths:
                        continue
                    scanned_paths.add(str(sub))

                    meta_file = sub / "material.json"
                    if meta_file.exists():
                        try:
                            data = json.loads(meta_file.read_text(encoding="utf-8"))
                            mat_id = data.get("id") or data.get("material_id") or sub.name
                            data["id"] = mat_id
                            data["material_id"] = mat_id
                            data["folder_name"] = sub.name
                            data["folder_path"] = str(sub)

                            # scenes ve scene_count garantisi
                            if not data.get("scenes"):
                                script_obj = data.get("script") or {}
                                if isinstance(script_obj, dict):
                                    if "scenes" in script_obj and isinstance(script_obj["scenes"], list):
                                        data["scenes"] = script_obj["scenes"]
                                    else:
                                        for lk in ("tr", "en", "es", "de"):
                                            if lk in script_obj and isinstance(script_obj[lk], dict) and "scenes" in script_obj[lk]:
                                                data["scenes"] = script_obj[lk]["scenes"]
                                                break
                            if not data.get("scene_count") and data.get("scenes"):
                                data["scene_count"] = len(data["scenes"])

                            if is_grp:
                                grp_meta = groups.get(tid, {})
                                data["is_group"] = True
                                data["group_id"] = tid
                                data["channel_id"] = f"group:{tid}"
                                data["channel_name"] = d_name
                                data["channel_language"] = d_lang
                                data["channel_category"] = d_cat
                                data["member_channel_ids"] = grp_meta.get("channel_ids", [])
                            else:
                                data["is_group"] = False
                                data["channel_id"] = tid
                                data["channel_name"] = d_name
                                data["channel_language"] = d_lang
                                data["channel_category"] = d_cat

                            all_materials.append(data)
                        except Exception as e:
                            print(f"[MATERIALS] Okuma hatası {meta_file}: {e}")

        # En yeni oluşturulana göre sırala
        all_materials.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return all_materials

    def get_material(self, channel_id: str, material_id: str) -> Optional[dict]:
        """Tek bir materyal paketinin detaylarını döner."""
        is_group, clean_id, target_base_dir = self._resolve_target(channel_id)
        mat_dir = self.get_channel_materials_dir(channel_id)
        item_dir = mat_dir / material_id

        if not item_dir.exists():
            # Alternatif isim dene
            alt_dir = target_base_dir / ALT_MATERIALS_FOLDER_NAME / material_id
            if alt_dir.exists():
                item_dir = alt_dir
            else:
                # Eğer bireysel kanalsa ve bir gruba aitse, grubun altında ara
                mgr = ChannelManager()
                parent_grp = mgr.get_channel_group(clean_id)
                if parent_grp:
                    grp_base = self.output_dir / "groups" / parent_grp["id"]
                    cand1 = grp_base / MATERIALS_FOLDER_NAME / material_id
                    cand2 = grp_base / ALT_MATERIALS_FOLDER_NAME / material_id
                    if cand1.exists():
                        item_dir = cand1
                    elif cand2.exists():
                        item_dir = cand2
                    else:
                        return None
                else:
                    return None

        meta_file = item_dir / "material.json"
        if not meta_file.exists():
            return None

        try:
            res = json.loads(meta_file.read_text(encoding="utf-8"))
            mat_id = res.get("id") or res.get("material_id") or item_dir.name
            res["id"] = mat_id
            res["material_id"] = mat_id
            res["folder_path"] = str(item_dir)
            if is_group:
                res["is_group"] = True
                res["group_id"] = clean_id
                res["channel_id"] = f"group:{clean_id}"
            return res
        except Exception:
            return None

    def delete_material(self, channel_id: str, material_id: str) -> bool:
        """Materyal paketini diskten siler."""
        is_group, clean_id, target_base_dir = self._resolve_target(channel_id)
        mat_dir = self.get_channel_materials_dir(channel_id)
        item_dir = mat_dir / material_id

        if not item_dir.exists():
            item_dir = target_base_dir / ALT_MATERIALS_FOLDER_NAME / material_id
            if not item_dir.exists():
                return False

        try:
            # Plan satırı varsa uretildi durumunu sıfırla
            meta_file = item_dir / "material.json"
            if meta_file.exists():
                try:
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                    row_id = data.get("row_id")
                    if row_id and data.get("status") not in ("produced", "downloaded"):
                        planner = ContentPlanner(target_base_dir)
                        planner.update_row_status(row_id, "Hayır")
                except Exception:
                    pass

            shutil.rmtree(str(item_dir))
            return True
        except Exception as e:
            print(f"[MATERIALS] Silme hatası {item_dir}: {e}")
            return False

    def update_material_status(self, channel_id: str, material_id: str, status: str) -> bool:
        """Materyal durumunu günceller (ready, producing, in_cloud_queue, produced, downloaded, failed)."""
        mat = self.get_material(channel_id, material_id)
        if not mat:
            return False
        mat["status"] = status
        item_dir = Path(mat.get("folder_path") or (self.get_channel_materials_dir(channel_id) / material_id))
        meta_file = item_dir / "material.json"
        try:
            meta_file.write_text(json.dumps(mat, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def get_pending_plan_rows(self, channel_id: str, limit: Optional[int] = None) -> list[dict]:
        """
        Kanalın veya grubun içerik planında yer alan ancak henüz videosu üretilmemiş VE
        materyalleri hazırlanmamış olan satırları döndürür.
        """
        is_group, clean_id, target_dir = self._resolve_target(channel_id)

        # Eğer bireysel kanalsa ama planı yoksa/boşsa ve bir gruba aitse, grubun planına bak
        if not is_group:
            planner = ContentPlanner(target_dir)
            if not planner.plan_exists() or len(planner.get_plan()) == 0:
                mgr = ChannelManager()
                parent_group = mgr.get_channel_group(clean_id)
                if parent_group:
                    return self.get_pending_plan_rows(f"group:{parent_group['id']}", limit=limit)
        else:
            planner = ContentPlanner(target_dir)

        plan = planner.get_plan()
        
        # Önceden hazırlanmış materyallerin row_id'lerini topla (SADECE sahnesi dolu olan gerçek materyaller)
        existing_materials = self.list_materials(channel_id)
        existing_row_ids = {
            str(m.get("row_id", "")).strip()
            for m in existing_materials
            if m.get("row_id") and (len(m.get("scenes") or []) > 0 or m.get("scene_count", 0) > 0)
        }
        
        pending = []
        for r in plan:
            rid = str(r.get("id", "")).strip()
            title = (r.get("baslik") or r.get("konu") or "").strip()
            if not title:
                continue
            
            u = (r.get("uretildi") or "").strip().lower()
            if u in ("evet", "yes", "true", "1"):
                continue
            # Eğer "materyaller hazır" işaretli olsa bile diskte materyal klasörü yoksa (silinmişse) tekrar bekleyen say
            if u in ("materyaller hazır", "materyaller_hazir") and rid in existing_row_ids:
                continue
            if rid in existing_row_ids:
                continue
                
            pending.append(r)
            if limit and len(pending) >= limit:
                break
                
        return pending

    def get_all_active_channels_pending_plans(self, limit_per_channel: Optional[int] = None) -> dict:
        """
        Şu anda aktif olan tüm kanalların ve kanal gruplarının henüz materyali
        üretilmemiş olan plan satırlarını ve istatistiklerini döndürür.
        """
        mgr = ChannelManager()
        active_channels = mgr.get_active_channels()
        all_groups = mgr.all_groups()
        grouped_channel_ids = mgr.get_grouped_channel_ids()
        
        channels_result = []
        total_pending = 0
        
        # 1. Önce aktif kanal gruplarını ekle
        for g in all_groups:
            gid = g.get("id")
            if not gid:
                continue
            pending_rows = self.get_pending_plan_rows(f"group:{gid}", limit=limit_per_channel)
            p_count = len(pending_rows)
            total_pending += p_count
            
            member_cids = g.get("channel_ids", [])
            channels_result.append({
                "type": "group",
                "is_group": True,
                "group_id": gid,
                "channel_id": f"group:{gid}",
                "name": f"📁 [GRUP] {g.get('name') or gid}",
                "raw_name": g.get("name") or gid,
                "language": "multi",
                "topic_category": g.get("topic_category") or "general",
                "custom_topics": [],
                "shorts_mode": True,
                "member_channels": member_cids,
                "pending_count": p_count,
                "pending_rows": pending_rows
            })
            
        # 2. Sonra bağımsız (herhangi bir gruba dahil olmayan) aktif kanalları ekle
        for c in active_channels:
            cid = c.get("channel_id")
            if not cid:
                continue
            # Eğer kanal bir gruba dahilse, planı grup tarafından yönetiliyor demektir
            if cid in grouped_channel_ids:
                own_planner = ContentPlanner(self.output_dir / cid)
                if own_planner.plan_exists() and len(own_planner.get_plan()) > 0:
                    pending_rows = self.get_pending_plan_rows(cid, limit=limit_per_channel)
                    if len(pending_rows) > 0:
                        p_count = len(pending_rows)
                        total_pending += p_count
                        channels_result.append({
                            "type": "channel",
                            "is_group": False,
                            "channel_id": cid,
                            "name": c.get("name") or cid,
                            "raw_name": c.get("name") or cid,
                            "language": c.get("language") or "tr",
                            "topic_category": c.get("topic_category") or "general",
                            "custom_topics": c.get("custom_topics") or [],
                            "shorts_mode": c.get("shorts_mode", False),
                            "edit_options": c.get("edit_options") or {},
                            "pending_count": p_count,
                            "pending_rows": pending_rows
                        })
                continue

            pending_rows = self.get_pending_plan_rows(cid, limit=limit_per_channel)
            p_count = len(pending_rows)
            total_pending += p_count
            
            channels_result.append({
                "type": "channel",
                "is_group": False,
                "channel_id": cid,
                "name": c.get("name") or cid,
                "raw_name": c.get("name") or cid,
                "language": c.get("language") or "tr",
                "topic_category": c.get("topic_category") or "general",
                "custom_topics": c.get("custom_topics") or [],
                "shorts_mode": c.get("shorts_mode", False),
                "edit_options": c.get("edit_options") or {},
                "pending_count": p_count,
                "pending_rows": pending_rows
            })

        # Bekleyen konu sayısı çoktan aza göre sırala
        channels_result.sort(key=lambda x: (x.get("pending_count", 0) > 0, x.get("pending_count", 0)), reverse=True)

        return {
            "total_pending": total_pending,
            "channels_count": len(channels_result),
            "channels": channels_result
        }

