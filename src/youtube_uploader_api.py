"""
youtube_uploader_api.py
Resmi YouTube Data API v3 Entegrasyonu, Akıllı Zamanlama ve Sunucu Temizliği Motoru.

Özellikler:
1. YouTube Data API v3 OAuth2 Yetkilendirmesi (Kanal bazlı veya genel token).
2. Akıllı Zamanlayıcı: Kanalda en son yüklenen veya planlanan videonun gün ve saatini
   YouTube API (veya içerik planı fallback) üzerinden tespit eder ve ertesi güne zamanlar.
3. Otomatik Video Yükleme (Resumable upload, chunked, thumbnail, tags, category).
4. Başarılı yükleme sonrası sunucudaki video dosyasını otomatik silme (Zero disk waste).
"""

from __future__ import annotations
import os
import re
import json
import time
import shutil
import zoneinfo
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

try:
    from src.youtube_scheduler import calculate_channel_next_schedule_slot, parse_date_string, get_channel_timezone
except ImportError:
    from youtube_scheduler import calculate_channel_next_schedule_slot, parse_date_string, get_channel_timezone

# Scopes needed for upload and reading channel video status/scheduling/comments
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CATEGORY_IDS = {
    "science": "28",
    "education": "27",
    "entertainment": "24",
    "news": "25",
    "comedy": "23",
    "people": "22",
    "blogs": "22",
    "people_and_blogs": "22",
}


class YouTubeAPIError(Exception):
    pass


class YouTubeUploaderAPI:
    def __init__(self, credentials_dir: Optional[str] = None):
        """
        credentials_dir: Token ve client_secret dosyalarının aranacağı dizin.
        """
        if credentials_dir:
            self.credentials_dir = Path(credentials_dir).resolve()
        else:
            # Check local or server standard paths
            server_cred = Path("/home/ubuntu/yt-remote-worker/credentials")
            local_cred = Path(__file__).resolve().parent.parent / "credentials"
            if server_cred.exists():
                self.credentials_dir = server_cred
            else:
                self.credentials_dir = local_cred

        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        self._services: Dict[str, Any] = {}

    def get_token_path(self, channel_id: str) -> Path:
        """Kanal için özel veya varsayılan token dosyasını döndürür."""
        ch_token = self.credentials_dir / f"{channel_id}_token.json"
        if ch_token.exists():
            return ch_token
        default_token = self.credentials_dir / "token.json"
        if default_token.exists():
            return default_token
        return ch_token

    def get_client_secret_path(self, channel_id: str) -> Path:
        """Kanal için özel veya varsayılan client_secret dosyasını döndürür."""
        ch_secret = self.credentials_dir / f"{channel_id}_client_secret.json"
        if ch_secret.exists():
            return ch_secret
        default_secret = self.credentials_dir / "client_secret.json"
        if default_secret.exists():
            return default_secret
        return ch_secret

    def is_channel_authenticated(self, channel_id: str) -> bool:
        """Kanalın geçerli bir OAuth tokenı olup olmadığını kontrol eder (asla takılmaz / non-blocking)."""
        token_path = self.get_token_path(channel_id)
        if not token_path.exists():
            return False
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            if not creds:
                return False
            if creds.valid:
                return True
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(token_path, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                    return True
                except Exception:
                    return False
        except Exception:
            pass
        return False

    def get_service(self, channel_id: str, interactive: bool = False):
        """Kanal için YouTube Data API v3 service nesnesini oluşturur/önbellekten getirir."""
        if channel_id in self._services:
            return self._services[channel_id]

        token_file = self.get_token_path(channel_id)
        secret_file = self.get_client_secret_path(channel_id)

        if not secret_file.exists():
            raise FileNotFoundError(
                f"[YouTube API] '{channel_id}' için client_secret.json bulunamadı ({secret_file}).\n"
                "Google Cloud Console → Credentials → OAuth 2.0 Client IDs → JSON indirip buraya yükleyin."
            )

        creds = None
        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
            except Exception as e:
                print(f"[YouTube API] Token okuma hatası ({channel_id}): {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(token_file, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                    print(f"[YouTube API] '{channel_id}' OAuth tokenı başarıyla yenilendi.")
                except Exception as ref_err:
                    print(f"[YouTube API] Token yenileme başarısız: {ref_err}")
                    creds = None

            if not creds or not creds.valid:
                if not interactive:
                    raise YouTubeAPIError(
                        f"[YouTube API] '{channel_id}' için geçerli OAuth tokenı yok veya süresi dolmuş. "
                        f"Yetkilendirmek için terminalden: python3 -m src.youtube_uploader_api auth {channel_id}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
                creds = flow.run_local_server(port=0)
                with open(token_file, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())

        service = build("youtube", "v3", credentials=creds, cache_discovery=False)
        self._services[channel_id] = service
        return service

    def get_latest_video_datetime_from_youtube(self, channel_id: str) -> Optional[datetime]:
        """
        YouTube Data API v3 üzerinden kanalın EN SON yayımlanmış veya planlanmış videosunun tarihini bulur.
        1 quota birimi harcayarak uploads playlist'ini ve video status'unu inceler.
        """
        try:
            service = self.get_service(channel_id)
            # 1. Kanalın 'uploads' çalma listesini bul
            ch_res = service.channels().list(mine=True, part="contentDetails").execute()
            items = ch_res.get("items", [])
            if not items:
                return None

            uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
            if not uploads_playlist_id:
                return None

            # 2. Son 10 videoyu listele
            pl_res = service.playlistItems().list(
                playlistId=uploads_playlist_id,
                part="snippet,contentDetails",
                maxResults=10
            ).execute()

            video_items = pl_res.get("items", [])
            if not video_items:
                return None

            video_ids = [v["contentDetails"]["videoId"] for v in video_items if "contentDetails" in v]
            if not video_ids:
                return None

            # 3. Videoların durumlarını ve zamanlama (publishAt) tarihlerini sorgula
            v_res = service.videos().list(
                id=",".join(video_ids),
                part="snippet,status"
            ).execute()

            candidate_dates: List[datetime] = []
            for v in v_res.get("items", []):
                snippet = v.get("snippet", {})
                status = v.get("status", {})

                # Planlanmış tarih varsa önceliklidir
                publish_at_str = status.get("publishAt")
                if publish_at_str:
                    try:
                        # e.g. "2026-10-10T16:00:00Z"
                        dt = datetime.fromisoformat(publish_at_str.replace("Z", "+00:00"))
                        candidate_dates.append(dt)
                        continue
                    except Exception:
                        pass

                # Normal yayımlanma tarihi
                published_at_str = snippet.get("publishedAt")
                if published_at_str:
                    try:
                        dt = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                        candidate_dates.append(dt)
                    except Exception:
                        pass

            if candidate_dates:
                latest = max(candidate_dates)
                return latest

        except Exception as e:
            print(f"[YouTube API] Canlı video listesi sorgulama uyarısı ({channel_id}): {e}")

        return None

    def calculate_auto_schedule_slot(
        self,
        channel_id: str,
        channel_config: Optional[dict] = None,
        plan_rows: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Kullanıcı Direktifi:
        "youtube'a yüklenen en son videonun günü ve saatinin ertesi gününe otomatik yükleyip..."
        
        1. Önce YouTube API üzerinden kanaldaki en son (yayımlanmış veya planlanmış) videoyu tespit eder.
        2. YouTube API erişilemezse içerik planındaki (plan_rows / CSV) en ileri tarihi kullanır.
        3. En son videonun gününün ERTESİ GÜNÜNE, kanalın standart saatine zamanlama hesaplar.
        """
        config = channel_config or {}
        lang = (config.get("language") or "tr").lower()
        tz_name = get_channel_timezone(lang)
        tz = zoneinfo.ZoneInfo(tz_name)

        now_in_tz = datetime.now(tz)
        today_in_tz = now_in_tz.date()
        tomorrow_in_tz = today_in_tz + timedelta(days=1)

        # 1. YouTube canlı API'sinden en son videoyu al
        yt_latest_dt_utc = None
        if self.is_channel_authenticated(channel_id):
            yt_latest_dt_utc = self.get_latest_video_datetime_from_youtube(channel_id)

        target_date = None
        target_hour = int(config.get("schedule_hour") or 19)
        if target_hour == 9 and ("shorts" in str(config.get("topic_category", "")) or "whatsapp" in str(config.get("topic_category", "")) or "yazan" in channel_id.lower()):
            target_hour = 19
        target_minute = 0

        latest_info = "Yok"

        if yt_latest_dt_utc:
            latest_local = yt_latest_dt_utc.astimezone(tz)
            latest_info = f"YouTube API: {latest_local.strftime('%Y-%m-%d %H:%M')} ({tz_name})"
            # Ertesi gün kuralı:
            if latest_local.date() < today_in_tz:
                target_date = tomorrow_in_tz
            else:
                target_date = latest_local.date() + timedelta(days=1)
            target_hour = latest_local.hour if latest_local.hour > 0 else target_hour
            target_minute = latest_local.minute
        else:
            # Fallback to local plan calculation
            slot_fallback = calculate_channel_next_schedule_slot(config, plan_rows=plan_rows)
            target_date = parse_date_string(slot_fallback.get("target_date_str")).date() if slot_fallback.get("target_date_str") else tomorrow_in_tz
            target_hour = int(slot_fallback.get("target_time_str", "19:00").split(":")[0])
            latest_info = f"İçerik Planı: {slot_fallback.get('latest_date_str') or 'İlk Video'}"

        target_local_dt = datetime(target_date.year, target_date.month, target_date.day, target_hour, target_minute, tzinfo=tz)

        # YouTube kuralı: Zamanlanan video şu andan en az 15 dakika sonra olmalıdır
        if target_local_dt <= (now_in_tz + timedelta(minutes=15)):
            target_local_dt = now_in_tz + timedelta(hours=1)

        # ISO 8601 UTC dizgisi (YouTube Data API v3 publishAt için zorunludur)
        target_utc_dt = target_local_dt.astimezone(timezone.utc)
        publish_at_iso = target_utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        return {
            "channel_id": channel_id,
            "target_date_str": target_local_dt.strftime("%Y-%m-%d"),
            "target_time_str": target_local_dt.strftime("%H:%M"),
            "target_local_dt": target_local_dt,
            "publish_at_iso": publish_at_iso,
            "timezone": tz_name,
            "latest_detected": latest_info,
            "summary": f"{target_local_dt.strftime('%d.%m.%Y %H:%M')} ({tz_name}) [Kaynak: {latest_info}]"
        }

    def add_pinned_comment(self, channel_id: str, video_id: str, comment_text: str) -> Optional[Dict[str, Any]]:
        """
        Casper AI: Videonun altına etkileşim anketini / ilk yorumu yazar ve sabitler.
        """
        if not comment_text or not video_id:
            return None
        try:
            service = self.get_service(channel_id, interactive=False)
            body = {
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text.strip()
                        }
                    }
                }
            }
            res = service.commentThreads().insert(
                part="snippet",
                body=body
            ).execute()
            thread_id = res.get("id")
            print(f"[YouTube API] 💬 Otomatik izleyici anketi / ilk yorum paylaşıldı (Thread ID: {thread_id})")
            return res
        except Exception as comment_err:
            print(f"[YouTube API] Otomatik yorum ekleme uyarısı (İzin veya kanal ayarı): {comment_err}")
            return None

    def upload_and_schedule(
        self,
        channel_id: str,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        category: str = "entertainment",
        publish_at_iso: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
        auto_cleanup: bool = True,
        privacy: str = "private",
        channel_config: Optional[dict] = None,
        pinned_comment: Optional[str] = None,
        seo_hashtags: Optional[list[str]] = None,
        search_optimized_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Videoyu belirtilen kanala yükler, zamanlar ve başarılı olursa sunucudaki dosyayı siler.
        Casper AI: seo_hashtags ve search_optimized_description ile arama ve Shorts algoritmasına tam uyum sağlar.
        """
        video_p = Path(video_path).resolve()
        if not video_p.exists() or not video_p.is_file():
            raise FileNotFoundError(f"[YouTube API] Video dosyası bulunamadı: {video_path}")

        # Eğer publish_at_iso verilmemişse akıllı hesaplama yap
        if not publish_at_iso:
            slot = self.calculate_auto_schedule_slot(channel_id, channel_config=channel_config)
            publish_at_iso = slot["publish_at_iso"]
            print(f"[YouTube API] Akıllı zamanlama yuvası belirlendi: {slot['summary']}")

        service = self.get_service(channel_id)
        cat_id = CATEGORY_IDS.get(category.lower(), "24")

        # Casper AI: Otomatik YouTube Etiket & Açıklama SEO Entegrasyonu (Spam/Jenerik Filtreli)
        try:
            from ai_metadata_generator import sanitize_tags, sanitize_hashtags
        except ImportError:
            try:
                from src.ai_metadata_generator import sanitize_tags, sanitize_hashtags
            except ImportError:
                sanitize_tags = lambda x: list(x) if x else []
                sanitize_hashtags = lambda x: list(x) if x else []

        final_description = search_optimized_description or description or ""
        # Jenerik hashtagleri temizle
        for bad_h in ["#Shorts", "#shorts", "#Viral", "#viral", "#Keşfet", "#keşfet", "#FYP", "#fyp", "#Trending", "#trending"]:
            final_description = final_description.replace(bad_h, "").strip()

        final_tags = sanitize_tags(list(tags or []))
        if seo_hashtags:
            clean_seo_hashtags = sanitize_hashtags(seo_hashtags)
            # Açıklamada hashtag yoksa sonuna ekle
            tags_text = " ".join(clean_seo_hashtags)
            if tags_text and tags_text not in final_description:
                final_description = f"{final_description.rstrip()}\n\n{tags_text}".strip()
            # YouTube video tags listesine de ekle (# işaretlerini temizleyerek)
            for h in clean_seo_hashtags:
                clean_tag = h.lstrip("#").strip()
                if clean_tag and clean_tag.lower() not in [t.lower() for t in final_tags]:
                    final_tags.append(clean_tag)
        final_tags = sanitize_tags(final_tags)

        status_body = {
            "privacyStatus": "private" if publish_at_iso else privacy,
            "selfDeclaredMadeForKids": False,
        }
        if publish_at_iso:
            status_body["publishAt"] = publish_at_iso

        body = {
            "snippet": {
                "title": title[:100],
                "description": final_description[:5000],
                "tags": final_tags[:30],
                "categoryId": cat_id,
                "defaultLanguage": "tr" if "tr" in channel_id.lower() or "yazan" in channel_id.lower() else "en",
            },
            "status": status_body,
        }

        media = MediaFileUpload(
            str(video_p),
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5,  # 5 MB chunk
        )

        print(f"[YouTube API] '{channel_id}' kanalına yükleniyor: '{title[:50]}'...")
        if publish_at_iso:
            print(f"[YouTube API] Yayın zamanı (UTC): {publish_at_iso}")

        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"[YouTube API] İlerleme: %{pct}")

        video_id = response.get("id", "")
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"[YouTube API] ✅ Video başarıyla yüklendi ve zamanlandı → {video_url} (ID: {video_id})")

        # Thumbnail yükle (varsa veya Casper AI otomatik kapak üretimi)
        if not thumbnail_path or not Path(thumbnail_path).exists():
            try:
                from src.video_editor import generate_clickbait_thumbnail
                auto_thumb = generate_clickbait_thumbnail(str(video_p), custom_title=title)
                if auto_thumb and Path(auto_thumb).exists():
                    thumbnail_path = auto_thumb
                    print(f"[YouTube API] 🎨 Casper AI: Otomatik clickbait thumbnail oluşturuldu: {thumbnail_path}")
            except Exception as auto_thumb_err:
                print(f"[YouTube API] Otomatik thumbnail üretilemedi (atlanıyor): {auto_thumb_err}")

        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path),
                ).execute()
                print(f"[YouTube API] Thumbnail başarıyla yüklendi: {os.path.basename(thumbnail_path)}")
            except Exception as thumb_err:
                print(f"[YouTube API] Thumbnail yükleme uyarısı: {thumb_err}")

        # Otomatik Sabit Yorum & İzleyici Anketi (Pinned Comment)
        pinned_comment_res = None
        if pinned_comment:
            try:
                pinned_comment_res = self.add_pinned_comment(channel_id, video_id, pinned_comment)
            except Exception as pin_err:
                print(f"[YouTube API] Sabit yorum uyarısı: {pin_err}")

        # Otomatik Sunucu Temizliği (Auto-Cleanup):
        # Kullanıcı kuralı: "sunucuda üretim yapıldıktan sonra otomatik olarak sistem youtube'a yüklenen... dosyayı silsin"
        deleted_files = []
        if auto_cleanup:
            try:
                parent_dir = video_p.parent
                if video_p.exists():
                    video_p.unlink()
                    deleted_files.append(str(video_p))
                    print(f"[YouTube API] 🧹 Yüklenen video sunucudan başarıyla silindi: {video_p.name}")

                # Klasördeki geçici ses/resim dosyalarını ve dizini temizle
                if parent_dir.name != "output" and parent_dir.name != "yuklenecek":
                    shutil.rmtree(parent_dir, ignore_errors=True)
                    print(f"[YouTube API] 🧹 Geçici iş klasörü temizlendi: {parent_dir}")
            except Exception as clean_err:
                print(f"[YouTube API] Temizlik uyarısı: {clean_err}")

        return {
            "success": True,
            "channel_id": channel_id,
            "video_id": video_id,
            "url": video_url,
            "publish_at": publish_at_iso,
            "cleaned_up": auto_cleanup,
            "deleted_files": deleted_files,
        }


def sys_has_interactive_terminal() -> bool:
    try:
        import sys
        return sys.stdin.isatty()
    except Exception:
        return False


# ── CLI & Test Arayüzü ───────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        cid = sys.argv[2] if len(sys.argv) > 2 else "yazanyazana"
        print(f"🔑 '{cid}' kanalı için YouTube OAuth yetkilendirmesi başlatılıyor...")
        uploader = YouTubeUploaderAPI()
        svc = uploader.get_service(cid, interactive=True)
        print(f"✅ Yetkilendirme başarılı! Token kaydedildi: {uploader.get_token_path(cid)}")
    elif len(sys.argv) > 1 and sys.argv[1] == "schedule-check":
        cid = sys.argv[2] if len(sys.argv) > 2 else "yazanyazana"
        uploader = YouTubeUploaderAPI()
        slot = uploader.calculate_auto_schedule_slot(cid)
        print(f"📅 Zamanlama Yuvası: {json.dumps(slot, default=str, ensure_ascii=False, indent=2)}")
    else:
        print("Kullanım:")
        print("  python -m src.youtube_uploader_api auth <channel_id>")
        print("  python -m src.youtube_uploader_api schedule-check <channel_id>")
