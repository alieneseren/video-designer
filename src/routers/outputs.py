"""
Outputs router: List output videos, archiving/unarchiving, status updates, and video editing.
"""
import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException

from channel_manager import ChannelManager, get_localized_metadata, is_bogus_fallback
from settings_manager import SettingsManager
from models.video import EditVideoPayload

router = APIRouter(tags=["Outputs"])
settings_mgr = SettingsManager()


def _parse_metadata(folder: Path) -> dict:
    """metadata.json veya metadata.txt dosyasını parse eder."""
    result = {"title": "", "description": "", "tags": [], "narration": "", "plan_id": "", "language": "en", "created_at": ""}
    json_path = folder / "metadata.json"
    txt_path = folder / "metadata.txt"
    
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            result["title"] = data.get("title", "")
            result["description"] = data.get("description", "")
            result["tags"] = data.get("tags", [])
            result["narration"] = data.get("narration", "")
            result["plan_id"] = data.get("plan_id", "")
            result["language"] = data.get("language", "en")
            result["created_at"] = data.get("created_at", "")
            return result
        except Exception as e:
            print(f"[META] JSON Parse hatası ({json_path}): {e}")
            
    if txt_path.exists():
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
                
            result["title"] = sections.get("TITLE", "")
            result["description"] = sections.get("DESCRIPTION", "")
            tags_raw = sections.get("TAGS", "")
            result["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]
            result["narration"] = sections.get("NARRATION", "")
        except Exception as e:
            print(f"[META] TXT Parse hatası ({txt_path}): {e}")
            
    return result


def _parse_video_folder(folder: Path, channel_id: str, category: str, out_path: Path, channel_map: dict, parent_folder_name: str = None, channel_config: dict = None):
    video_file = folder / "final.mp4"
    meta_parsed = _parse_metadata(folder)
    
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
    
    # Yerel meta verileri (açıklama ve etiketler) kanala ve dile uygun hale getir
    ch_lang = (channel_config.get("language") if channel_config else None) or meta_parsed.get("language") or "en"
    ch_cat = (channel_config.get("topic_category") if channel_config else None) or "reddit_stories"
    meta_parsed["language"] = ch_lang

    desc = meta_parsed.get("description", "")
    tags = meta_parsed.get("tags", [])
    if not desc or not tags or is_bogus_fallback(desc, tags, ch_lang, ch_cat):
        clean_desc, clean_tags = get_localized_metadata(meta_parsed.get("title", ""), ch_lang, ch_cat)
        meta_parsed["description"] = clean_desc
        meta_parsed["tags"] = clean_tags
    
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


def _get_video_segments_and_audio(folder_path: Path) -> tuple[list[dict], str]:
    info_file = folder_path / "video_info.json"
    meta_file = folder_path / "metadata.json"
    
    audio_path = ""
    for ext in ["wav", "mp3"]:
        p = folder_path / f"narration.{ext}"
        if p.exists():
            audio_path = str(p)
            break
            
    if info_file.exists():
        try:
            info = json.loads(info_file.read_text(encoding="utf-8"))
            if "segments" in info and info["segments"]:
                segments = info["segments"]
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
            
    segments = []
    if meta_file.exists() and audio_path:
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
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


@router.get("/api/output")
def list_output_videos():
    """output/ klasöründeki tüm video klasörlerini listeler."""
    output_dir = settings_mgr.get("output_dir", "output")
    out_path   = Path(output_dir)
    videos     = []

    if not out_path.exists():
        return []

    mgr = ChannelManager()
    channels = mgr.all_channels()
    channel_map = {ch["channel_id"]: ch.get("name", ch["channel_id"]) for ch in channels}
    channel_obj_map = {ch["channel_id"]: ch for ch in channels}

    # 1. Yeni yapıyı tara: output/<channel_id>/yuklenecek/ ve output/<channel_id>/yuklenen/
    for channel_folder in out_path.iterdir():
        if not channel_folder.is_dir() or channel_folder.name.startswith("."):
            continue
        ch_cfg = channel_obj_map.get(channel_folder.name)
        for category in ["yuklenecek", "yuklenen"]:
            cat_dir = channel_folder / category
            if cat_dir.exists() and cat_dir.is_dir():
                for folder in cat_dir.iterdir():
                    if not folder.is_dir() or folder.name.startswith("."):
                        continue
                    
                    video_file = folder / "final.mp4"
                    if video_file.exists():
                        videos.append(_parse_video_folder(folder, channel_folder.name, category, out_path, channel_map, channel_config=ch_cfg))
                        
                    for subfolder in folder.iterdir():
                        if subfolder.is_dir() and subfolder.name.startswith("shorts_"):
                            sub_video_file = subfolder / "final.mp4"
                            if sub_video_file.exists():
                                videos.append(_parse_video_folder(subfolder, channel_folder.name, category, out_path, channel_map, parent_folder_name=folder.name, channel_config=ch_cfg))

    # 2. Eski yapıyı tara
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

        ch_cfg = channel_obj_map.get(channel_id_guess, {})
        ch_lang = ch_cfg.get("language") or meta_parsed.get("language") or "en"
        ch_cat = ch_cfg.get("topic_category") or "reddit_stories"
        meta_parsed["language"] = ch_lang
        desc = meta_parsed.get("description", "")
        tags = meta_parsed.get("tags", [])
        if not desc or not tags or is_bogus_fallback(desc, tags, ch_lang, ch_cat):
            clean_desc, clean_tags = get_localized_metadata(meta_parsed.get("title", ""), ch_lang, ch_cat)
            meta_parsed["description"] = clean_desc
            meta_parsed["tags"] = clean_tags

        videos.append({
            "folder": folder_name,
            "folder_path": str(folder),
            "video_path": str(video_file),
            "title": meta_parsed["title"],
            "description": meta_parsed["description"],
            "tags": meta_parsed["tags"],
            "narration": meta_parsed.get("narration", ""),
            "plan_id": meta_parsed.get("plan_id", ""),
            "language": meta_parsed.get("language", "en"),
            "channel_id": channel_id_guess,
            "channel_name": channel_map.get(channel_id_guess, channel_id_guess),
            "shorts_mode": extra.get("shorts_mode", False) or ("shorts_" in folder_name),
            "transition": extra.get("transition", "fade"),
            "resolution": extra.get("resolution", ""),
            "duration_sec": extra.get("duration_sec", 0.0),
            "created_at": created_at,
            "archived": archived,
            "uploaded_youtube": uploaded_youtube,
            "uploaded_instagram": uploaded_instagram,
            "uploaded_tiktok": uploaded_tiktok,
        })

    videos.sort(key=lambda x: x["created_at"], reverse=True)
    return videos


@router.post("/api/output/{folder_name:path}/archive")
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
            shutil.rmtree(dest_folder)
            
        folder.rename(dest_folder)
        new_folder_name = f"{channel_id}/yuklenen/{folder_basename}"
        return {"success": True, "folder": new_folder_name, "archived": True}
    else:
        (folder / ".archived").touch()
        return {"success": True, "folder": folder_name, "archived": True}


@router.delete("/api/output/{folder_name:path}/archive")
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


@router.post("/api/output/{folder_name:path}/status")
def update_upload_status(folder_name: str, payload: dict):
    """Videonun platform yükleme durumlarını günceller ve hepsi yüklendi ise otomatik arşivler."""
    output_dir = settings_mgr.get("output_dir", "output")
    folder     = Path(output_dir) / folder_name
    if not folder.exists():
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
        
    archived = False
    new_folder_name = folder_name
    parts = Path(folder_name).parts
    channel_id = parts[0] if len(parts) >= 1 else ""
    
    if len(parts) >= 4 and parts[3].startswith("shorts_"):
        parent_folder = Path(output_dir) / parts[0] / parts[1] / parts[2]
    else:
        parent_folder = folder
        
    ch_mgr = ChannelManager()
    channel = ch_mgr.get_channel(channel_id)
    
    def is_item_all_uploaded(info_file_path: Path):
        if not info_file_path.exists():
            return False
        try:
            item_extra = json.loads(info_file_path.read_text(encoding="utf-8"))
        except Exception:
            return False
            
        if channel:
            if not item_extra.get("uploaded_youtube"):
                return False
            if channel.get("instagram", False) and not item_extra.get("uploaded_instagram"):
                return False
            if channel.get("tiktok", False) and not item_extra.get("uploaded_tiktok"):
                return False
        else:
            if not (item_extra.get("uploaded_youtube") and item_extra.get("uploaded_instagram") and item_extra.get("uploaded_tiktok")):
                return False
        return True

    is_group_completed = False
    if len(parts) >= 3 and parts[1] == "yuklenecek":
        parent_info = parent_folder / "video_info.json"
        if is_item_all_uploaded(parent_info):
            all_shorts_done = True
            for sub in parent_folder.iterdir():
                if sub.is_dir() and sub.name.startswith("shorts_"):
                    if not is_item_all_uploaded(sub / "video_info.json"):
                        all_shorts_done = False
                        break
            if all_shorts_done:
                is_group_completed = True

    if is_group_completed:
        folder_basename = parts[2]
        dest_parent = Path(output_dir) / channel_id / "yuklenen"
        dest_parent.mkdir(parents=True, exist_ok=True)
        dest_folder = dest_parent / folder_basename
        
        if dest_folder.exists():
            shutil.rmtree(dest_folder)
            
        try:
            parent_folder.rename(dest_folder)
            print(f"[STATUS] Incident group archived successfully: {parent_folder.name}")
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
            if plan_id:
                planner.mark_as_uploaded(plan_id)
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


@router.post("/api/output/edit")
def edit_output_video(payload: EditVideoPayload):
    """Üretilmiş videonun görsel geçiş ve alt yazı ayarlarını günceller ve videoyu yeniden derler."""
    output_dir = settings_mgr.get("output_dir", "output")
    folder_path = Path(output_dir) / payload.folder
    
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Video klasörü bulunamadı.")
        
    info_file = folder_path / "video_info.json"
    if not info_file.exists():
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

    if payload.transition is not None:
        info["transition"] = payload.transition
    
    segments, audio_path = _get_video_segments_and_audio(folder_path)
    if not segments:
        raise HTTPException(status_code=400, detail="Segment bilgisi alınamadı veya oluşturulamadı.")
    if not audio_path:
        raise HTTPException(status_code=400, detail="Ses dosyası bulunamadı.")
        
    shorts_mode = info.get("shorts_mode", False)
    W = 1080 if shorts_mode else 1920
    H = 1920 if shorts_mode else 1080
    
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

    if censor_faces:
        from video_generator import VideoGenerator
        generator = VideoGenerator()
        for seg in segments:
            img = seg.get("image_path")
            if img and Path(img).exists():
                generator._censor_faces(img)

    from video_editor import EditConfig, VideoEditor
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

    info["transition"] = transition
    info["edit_log"] = {
        "groups": edit_log.get("groups"),
        "captions": edit_log.get("captions"),
        "ass_path": edit_log.get("ass_path"),
        "base_path": edit_log.get("base_path"),
    }
    info["segments"] = segments
    info_file.write_text(json.dumps(info, ensure_ascii=False, indent=2))

    return {
        "success": True,
        "video_path": video_path,
        "transition": transition,
    }
