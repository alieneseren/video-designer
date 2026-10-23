"""
upload_video.py
Üretilen bir videoyu doğrudan YouTube kanalına yükleme ve zamanlama aracı.
Kullanım:
    .venv/bin/python src/upload_video.py <video_klasoru> [--channel <kanal_id>] [--publish-at <tarih>] [--public]
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.youtube_uploader import YouTubeUploader
from src.youtube_scheduler import calculate_channel_next_schedule_slot

def upload_folder(folder_path: str, channel_id: str = None, privacy: str = "private", schedule: bool = True):
    f_path = Path(folder_path).resolve()
    if not f_path.exists() or not f_path.is_dir():
        print(f"❌ Klasör bulunamadı: {folder_path}")
        return False

    # 1. Video dosyasını bul (final.mp4 veya video.mp4)
    video_file = f_path / "final.mp4"
    if not video_file.exists():
        video_file = f_path / "video.mp4"
    if not video_file.exists():
        mp4s = list(f_path.glob("*.mp4"))
        if mp4s:
            video_file = mp4s[0]
        else:
            print(f"❌ Klasör içinde MP4 video bulunamadı: {f_path}")
            return False

    # 2. Kanal tespit et (klasör yolundan veya argümandan)
    detected_channel = channel_id
    if not detected_channel:
        if "yazan" in str(f_path).lower():
            detected_channel = "yazanyazana"
        elif "reddit" in str(f_path).lower():
            detected_channel = "tr1_reddithikayeleri"
        else:
            detected_channel = "yazanyazana"

    # 2.1. Otonom Yerel AI Metadata Kontrolü (Eğer generic kalmışsa veya yoksa üret)
    meta_path = f_path / "metadata.json"
    v_info_path = f_path / "video_info.json"
    needs_ai_meta = True
    if meta_path.exists():
        try:
            m_check = json.loads(meta_path.read_text(encoding="utf-8"))
            chk_desc = m_check.get("description", "")
            chk_tags = m_check.get("tags", [])
            from src.channel_manager import ChannelManager, is_bogus_fallback
            ch_obj = ChannelManager().get_channel(detected_channel) or {}
            chk_lang = ch_obj.get("language") or m_check.get("language") or ("tr" if "tr" in str(detected_channel).lower() else "en")
            chk_cat = ch_obj.get("topic_category") or m_check.get("topic_category") or "reddit_stories"
            if not is_bogus_fallback(chk_desc, chk_tags, language=chk_lang, category=chk_cat) and m_check.get("ai_metadata_generated") and len(chk_desc) > 80:
                needs_ai_meta = False
        except Exception:
            pass

    if needs_ai_meta:
        try:
            from src.ai_metadata_generator import auto_generate_and_apply_metadata
            auto_generate_and_apply_metadata(f_path, channel_id=detected_channel)
        except Exception:
            try:
                from ai_metadata_generator import auto_generate_and_apply_metadata
                auto_generate_and_apply_metadata(f_path, channel_id=detected_channel)
            except Exception:
                pass

    # 2.2. Metadata / Video Info oku
    title = f_path.name
    description = ""
    tags = []
    thumbnail_file = f_path / "thumbnail.jpg"

    if meta_path.exists():
        try:
            m_data = json.loads(meta_path.read_text(encoding="utf-8"))
            title = m_data.get("title", title)
            description = m_data.get("description", m_data.get("desc", ""))
            tags = m_data.get("tags", [])
        except Exception:
            pass

    if v_info_path.exists():
        try:
            data = json.loads(v_info_path.read_text(encoding="utf-8"))
            if not title or title == f_path.name:
                title = data.get("title", title)
            if not description:
                description = data.get("description", data.get("desc", ""))
            if not tags:
                tags = data.get("tags", [])
        except Exception:
            pass

    if not description:
        description = "#Shorts #Viral"
    if not tags:
        tags = ["Shorts", "Viral"]

    # 3. Yayımlama Zamanlaması (Scheduling)
    publish_at_iso = None
    if schedule:
        try:
            slot = calculate_channel_next_schedule_slot({"channel_id": detected_channel, "language": "tr"})
            dt_local = slot.get("scheduled_datetime")
            if dt_local:
                # ISO 8601 UTC formatına çevir
                import zoneinfo
                tz_ist = zoneinfo.ZoneInfo("Europe/Istanbul")
                dt_utc = dt_local.replace(tzinfo=tz_ist).astimezone(timezone.utc)
                publish_at_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                print(f"📅 Otomatik Zamanlama: {slot.get('formatted_date_time')} (İstanbul saati)")
        except Exception as e:
            print(f"⚠️ Zamanlama hesaplanırken hata oluştu ({e}), hemen gizli yüklenecek.")

    # 4. YouTube'a Yükle
    print(f"\n🚀 YouTube'a yükleme başlatılıyor:")
    print(f"   Kanal: {detected_channel}")
    print(f"   Başlık: {title}")
    print(f"   Video Dosyası: {video_file.name} ({video_file.stat().st_size / 1024 / 1024:.1f} MB)")
    if publish_at_iso:
        print(f"   Zamanlanmış Yayın Tarihi: {publish_at_iso}")

    uploader = YouTubeUploader()
    res = uploader.upload(
        channel_id=detected_channel,
        video_path=str(video_file),
        title=title,
        description=description,
        tags=tags,
        category="entertainment" if ("yazan" in str(detected_channel).lower() or "whatsapp" in str(detected_channel).lower()) else "education",
        privacy="private" if publish_at_iso else privacy,
        thumbnail_path=str(thumbnail_file) if thumbnail_file.exists() else None,
        publish_at=publish_at_iso
    )

    print(f"\n🎉 VİDEO YÜKLENDİ!")
    print(f"   Link: {res.get('url')}")
    print(f"   Video ID: {res.get('video_id')}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Video Yükleme ve Zamanlama")
    parser.add_argument("folder", help="Yüklenecek video klasörünün yolu")
    parser.add_argument("--channel", help="Hedef kanal ID'si (örn: yazanyazana)", default=None)
    parser.add_argument("--public", action="store_true", help="Zamanlama yapmadan doğrudan herkese açık yükle")
    args = parser.parse_args()

    upload_folder(args.folder, channel_id=args.channel, privacy="public" if args.public else "private", schedule=not args.public)
