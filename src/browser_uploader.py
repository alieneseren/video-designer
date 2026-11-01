"""
browser_uploader.py
Browser MCP & YouTube Studio Otomatik Yükleme ve Akıllı Zamanlama Motoru.

Bu servis:
1. İlgili kanalın veya grubun üretilen video dosyasını (yuklenecek / yuklenen) tespit eder.
2. Hedef ülkenin saat dilimine göre 19:00 zamanlama yuvasını (slot) hesaplar.
3. YouTube Studio otomatik yükleme paketini hazırlar.
4. Günlük yükleme limiti kontrolü yapar.
5. Yükleme tamamlandığında içerik planı CSV'sini günceller.
"""

from __future__ import annotations
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from content_planner import ContentPlanner
from youtube_scheduler import calculate_channel_next_schedule_slot
from channel_manager import ChannelManager, get_localized_metadata, is_bogus_fallback


def find_planned_video_folder(channel_id: str, row_id: str, output_base_dir: str = "output", auto_ai: bool = False) -> dict | None:
    """
    Kanal dizininde (yuklenecek, yuklenen, arsiv, kök) verilen row_id (plan_id) ile eşleşen videoyu arar.
    1. metadata.json ve video_info.json içindeki plan_id eşleşmesi
    2. Klasör adının 0001_, 001_, 1_ gibi satır id ön ekiyle başlaması
    3. final.mp4 / base.mp4 varlığı

    NOT: Yalnızca ilgili kanalın kendi dizini taranır. Başka kanalların
    videoları kesinlikle döndürülmez (cross-channel karışıklığı önlenir).
    """
    base_path = Path(output_base_dir)
    out_dir = base_path / channel_id

    # Kanal dizini yoksa None dön — global fallback kullanma!
    if not out_dir.exists():
        return None

    # YALNIZCA bu kanala ait alt dizinleri ara (global yuklenecek/yuklenen yok)
    search_dirs = [
        out_dir / "yuklenecek",
        out_dir / "yuklenen",
        out_dir / "arsiv",
        out_dir,
    ]

    prefix_candidates = []
    try:
        r_int = int(row_id)
        prefix_candidates = [f"{r_int:04d}_", f"{r_int:03d}_", f"{r_int:02d}_", f"{r_int}_"]
    except Exception:
        prefix_candidates = [f"{row_id}_"]

    # 1. Tam eşleşen klasörleri ara
    for sdir in search_dirs:
        if not sdir.exists():
            continue
        for sub in sdir.iterdir():
            if not sub.is_dir():
                continue

            # Güvenlik: bulunan klasörün bu kanalın dizini altında olduğunu doğrula
            try:
                sub.relative_to(out_dir)
            except ValueError:
                # Başka kanalın dizinine denk gelinirse atla
                continue

            matched = False
            meta_data = {}
            vinfo_data = {}

            # metadata.json oku
            meta_path = sub / "metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta_data = json.load(f)
                        if str(meta_data.get("plan_id") or meta_data.get("row_id") or "") == str(row_id):
                            matched = True
                except Exception:
                    pass

            # video_info.json oku
            vinfo_path = sub / "video_info.json"
            if vinfo_path.exists():
                try:
                    with open(vinfo_path, "r", encoding="utf-8") as f:
                        vinfo_data = json.load(f)
                        if str(vinfo_data.get("plan_id") or vinfo_data.get("row_id") or "") == str(row_id):
                            matched = True
                except Exception:
                    pass

            # Ön ek kontrolü (0001_...)
            for pfix in prefix_candidates:
                if sub.name.startswith(pfix):
                    matched = True
                    break

            if matched:
                video_file = next(
                    (
                        sub / filename
                        for filename in ("final.mp4", "final_video.mp4", "video.mp4", "base.mp4")
                        if (sub / filename).is_file()
                    ),
                    sub / "final.mp4",
                )

                if video_file.exists():
                    try:
                        rel_folder = str(sub.relative_to(base_path))
                    except Exception:
                        rel_folder = sub.name

                    thumb_file = sub / "thumbnail.jpg"
                    if not thumb_file.exists():
                        thumb_file = sub / "reddit_card_overlay.png"
                    if not thumb_file.exists():
                        thumb_file = sub / "scene_0.jpg"

                    is_uploaded = ("yuklenen" in sub.parts) or bool(vinfo_data.get("uploaded_youtube"))
                    title = meta_data.get("title") or meta_data.get("topic") or vinfo_data.get("title") or sub.name
                    ch_info = ChannelManager().get_channel(channel_id) or {}
                    lang = meta_data.get("language") or vinfo_data.get("language") or ch_info.get("language") or "tr"
                    cat = ch_info.get("topic_category") or "reddit_stories"

                    desc = (
                        meta_data.get("description") or 
                        meta_data.get("desc") or 
                        vinfo_data.get("description") or 
                        vinfo_data.get("desc") or 
                        ""
                    ).strip()

                    tags = (
                        meta_data.get("tags") or 
                        meta_data.get("keywords") or 
                        vinfo_data.get("tags") or 
                        vinfo_data.get("keywords") or 
                        []
                    )
                    if isinstance(tags, str):
                        tags = [t.strip() for t in tags.split(",") if t.strip()]

                    if auto_ai and (not desc or is_bogus_fallback(desc, tags, language=lang, category=cat) or not meta_data.get("ai_metadata_generated")):
                        try:
                            from src.ai_metadata_generator import auto_generate_and_apply_metadata
                            ai_res = auto_generate_and_apply_metadata(sub, channel_id=channel_id)
                            if ai_res.get("success") and ai_res.get("title"):
                                title = ai_res.get("title", title)
                                desc = ai_res.get("description", desc)
                                tags = ai_res.get("tags", tags)
                        except Exception:
                            pass

                    if not desc or is_bogus_fallback(desc, tags, language=lang, category=cat):
                        loc_desc, loc_tags = get_localized_metadata(title, language=lang, category=cat)
                        if not desc or is_bogus_fallback(desc, [], language=lang, category=cat):
                            desc = loc_desc
                        if not tags or is_bogus_fallback("", tags, language=lang, category=cat):
                            tags = loc_tags

                    # Spam/Jenerik etiket filtresi
                    try:
                        from ai_metadata_generator import sanitize_tags
                        tags = sanitize_tags(tags)
                    except Exception:
                        pass

                    return {
                        "folder": rel_folder,
                        "folder_path": str(sub),
                        "video_url": f"/output/{rel_folder}/{video_file.name}",
                        "video_path": str(video_file),
                        "video_file": str(video_file),
                        "thumbnail_path": str(thumb_file) if thumb_file.exists() else "",
                        "thumbnail_file": str(thumb_file) if thumb_file.exists() else "",
                        "title": title,
                        "description": desc,
                        "tags": tags,
                        "language": lang,
                        "plan_id": str(row_id),
                        "channel_id": channel_id,
                        "is_uploaded": is_uploaded,
                        "is_produced": True,
                    }

    # Eşleşen klasör bulunamadıysa None dön
    return None



def prepare_channel_upload_payload(
    channel_id: str,
    row_id: str,
    output_base_dir: str = "output"
) -> dict:
    """
    Münferit kanal için YouTube Studio otomatik yükleme paketini hazırlar.
    Akıllı zamanlama (19:00, ertesi gün/son tarih + 1 gün) uygular.
    """
    mgr = ChannelManager()
    channel = mgr.get_channel(channel_id)
    if not channel:
        raise ValueError(f"Kanal bulunamadı: {channel_id}")

    planner = ContentPlanner(Path(output_base_dir) / channel_id)
    plan_rows = planner.get_plan()
    row = planner.get_row_by_id(row_id)
    if not row:
        raise ValueError(f"İçerik planında #{row_id} numaralı satır bulunamadı.")

    # 1. Video dosya paketini bul
    video_info = find_planned_video_folder(channel_id, row_id, output_base_dir, auto_ai=True)
    ch_lang = channel.get("language", "tr")
    ch_cat = channel.get("topic_category", "reddit_stories")
    title = (video_info.get("title") if video_info else "") or row.get("baslik") or row.get("konu") or "Yeni Video"
    description = (video_info.get("description") if video_info else "").strip()
    tags = (video_info.get("tags") if video_info else []) or [t.strip() for t in (row.get("anahtar_kelimeler") or "").split(",") if t.strip()]

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

    if not description or is_bogus_fallback(description, tags, language=ch_lang, category=ch_cat):
        loc_desc, loc_tags = get_localized_metadata(title, language=ch_lang, category=ch_cat)
        if not description or is_bogus_fallback(description, [], language=ch_lang, category=ch_cat):
            description = loc_desc
        if not tags or is_bogus_fallback("", tags, language=ch_lang, category=ch_cat):
            tags = loc_tags

    # Spam/Jenerik etiket filtresi
    try:
        from ai_metadata_generator import sanitize_tags
        tags = sanitize_tags(tags)
    except Exception:
        pass
    video_path = video_info.get("video_path") if video_info else str(Path(output_base_dir) / channel_id / "final.mp4")
    folder = video_info.get("folder") if video_info else f"{channel_id}/final.mp4"
    video_url = video_info.get("video_url") if video_info else f"/output/{channel_id}/final.mp4"

    # 2. Akıllı zamanlama yuvasını hesapla (Hedef ülke saatiyle 19:00)
    slot = calculate_channel_next_schedule_slot(channel, plan_rows=plan_rows)

    payload = {
        "channel_id": channel_id,
        "channel_name": channel.get("name", ""),
        "plan_id": str(row_id),
        "title": title,
        "description": description,
        "tags": tags,
        "video_path": video_path,
        "folder": folder,
        "video_url": video_url,
        "language": channel.get("language", "tr"),
        "schedule_date": slot["target_date_str"],
        "schedule_time": slot["target_time_str"],
        "scheduled_datetime": slot["target_datetime_str"],
        "timezone": slot["timezone"],
        "made_for_kids": False,
        "display_summary": slot["display_summary"],
        "timestamp": int(time.time() * 1000),
    }

    return {
        "success": True,
        "payload": payload,
        "slot": slot,
    }


def execute_channel_upload_and_mark(
    channel_id: str,
    row_id: str,
    output_base_dir: str = "output"
) -> dict:
    """
    Münferit kanal yüklemesini hazırlar ve frontend / eklenti için yükleme paketini döndürür.
    (Satır, Studio yüklemeyi bitirip backend'e bildirdiğinde otomatik yüklendi olarak işaretlenir).
    """
    prep = prepare_channel_upload_payload(channel_id, row_id, output_base_dir)
    payload = prep["payload"]
    slot = prep["slot"]

    return {
        "success": True,
        "message": f"'{payload['title']}' videosu {slot['display_summary']} için YouTube Studio'ya gönderilmeye hazırlandı.",
        "payload": payload,
        "slot": slot,
    }


def execute_group_upload_and_mark(
    group_id: str,
    row_id: str,
    output_base_dir: str = "output"
) -> dict:
    """
    Grup içerik planındaki konuyu gruptaki tüm üye kanallar için tek tek
    kendi dillerindeki hedef ülkeye göre (19:00) YouTube Studio yükleme paketini hazırlar.
    """
    mgr = ChannelManager()
    group = mgr.get_group(group_id)
    if not group:
        raise ValueError(f"Grup bulunamadı: {group_id}")

    grp_dir = Path(output_base_dir) / "groups" / group_id
    grp_planner = ContentPlanner(grp_dir)
    grp_row = grp_planner.get_row_by_id(row_id)
    if not grp_row:
        raise ValueError(f"Grup planında #{row_id} numaralı satır bulunamadı.")

    results = []
    member_channel_ids = group.get("channel_ids", [])

    for cid in member_channel_ids:
        ch = mgr.get_channel(cid)
        if not ch:
            continue
        try:
            ch_planner = ContentPlanner(Path(output_base_dir) / cid)
            ch_plan = ch_planner.get_plan()
            slot = calculate_channel_next_schedule_slot(ch, plan_rows=ch_plan)
            
            # Kanal video dosyasını bul
            vinfo = find_planned_video_folder(cid, row_id, output_base_dir)
            ch_lang = ch.get("language", "en")
            ch_cat = ch.get("topic_category", group.get("topic_category", "reddit_stories"))
            title = (vinfo.get("title") if vinfo else "") or grp_row.get("baslik") or grp_row.get("konu") or f"{ch['name']} Video"
            description = (vinfo.get("description") if vinfo else "").strip()
            tags = (vinfo.get("tags") if vinfo else []) or [t.strip() for t in (grp_row.get("anahtar_kelimeler") or "").split(",") if t.strip()]

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

            if not description or is_bogus_fallback(description, tags, language=ch_lang, category=ch_cat):
                loc_desc, loc_tags = get_localized_metadata(title, language=ch_lang, category=ch_cat)
                if not description or is_bogus_fallback(description, [], language=ch_lang, category=ch_cat):
                    description = loc_desc
                if not tags or is_bogus_fallback("", tags, language=ch_lang, category=ch_cat):
                    tags = loc_tags
            video_path = vinfo.get("video_path") if vinfo else str(Path(output_base_dir) / cid / "final.mp4")
            folder = vinfo.get("folder") if vinfo else f"{cid}/final.mp4"
            video_url = vinfo.get("video_url") if vinfo else f"/output/{cid}/final.mp4"

            item_payload = {
                "channel_id": cid,
                "channel_name": ch.get("name", ""),
                "group_id": group_id,
                "plan_id": str(row_id),
                "title": title,
                "description": description,
                "tags": tags,
                "video_path": video_path,
                "folder": folder,
                "video_url": video_url,
                "language": ch.get("language", "en"),
                "schedule_date": slot["target_date_str"],
                "schedule_time": slot["target_time_str"],
                "scheduled_datetime": slot["target_datetime_str"],
                "timezone": slot["timezone"],
                "made_for_kids": False,
                "display_summary": slot["display_summary"],
                "timestamp": int(time.time() * 1000),
            }

            results.append({
                "channel_id": cid,
                "channel_name": ch.get("name"),
                "language": ch.get("language"),
                "slot": slot,
                "payload": item_payload,
                "success": True,
            })
        except Exception as e:
            results.append({
                "channel_id": cid,
                "channel_name": ch.get("name") if ch else cid,
                "success": False,
                "error": str(e),
            })

    return {
        "success": True,
        "group_id": group_id,
        "group_name": group.get("name", ""),
        "row_id": str(row_id),
        "results": results,
        "message": f"Gruptaki {len([r for r in results if r.get('success')])} kanal için YouTube Studio yükleme paketi hazırlandı.",
    }
