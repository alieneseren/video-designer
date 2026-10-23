"""
youtube_uploader.py
Çoklu kanal desteğiyle YouTube'a video yükler.
Her kanal kendi OAuth token dosyasına sahiptir.
"""

import os
import json
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

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

PRIVACY_OPTIONS = ["public", "unlisted", "private"]


class YouTubeUploader:
    def __init__(self, credentials_dir: str = "credentials"):
        """
        credentials_dir: Her kanal için OAuth dosyalarının bulunduğu klasör.
        Yapı:
          credentials/
            ch_001_client_secret.json   ← Google Cloud'dan indirilen
            ch_001_token.json           ← İlk girişte otomatik oluşur
            ch_002_client_secret.json
            ch_002_token.json
            ...
        """
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(exist_ok=True)
        self._services = {}   # cache: channel_id → youtube service

    def _get_service(self, channel_id: str):
        if channel_id in self._services:
            return self._services[channel_id]

        secret_file = self.credentials_dir / f"{channel_id}_client_secret.json"
        token_file  = self.credentials_dir / f"{channel_id}_token.json"

        if not secret_file.exists():
            default_secret = self.credentials_dir / "client_secret.json"
            if default_secret.exists():
                secret_file = default_secret
            else:
                raise FileNotFoundError(
                    f"[YT] '{channel_id}' için client_secret.json bulunamadı: {secret_file}\n"
                    "Google Cloud Console → OAuth 2.0 → İndir → Dosyayı buraya kaydet."
                )

        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_file, "w") as f:
                f.write(creds.to_json())

        service = build("youtube", "v3", credentials=creds)
        self._services[channel_id] = service
        return service

    def upload(
        self,
        channel_id: str,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        category: str = "science",
        privacy: str = "public",
        thumbnail_path: str = None,
        publish_at: str = None,
    ) -> dict:
        """
        Videoyu belirtilen kanala yükler.
        publish_at: ISO 8601 UTC tarih dizgisi (örn: '2026-09-28T16:00:00.000Z') verildiğinde video zamanlanır.
        Döndürür: {"video_id": ..., "url": ..., "status": ...}
        """
        service = self._get_service(channel_id)

        cat_id = CATEGORY_IDS.get(category, "28")
        priv   = privacy if privacy in PRIVACY_OPTIONS else "public"

        status_body = {
            "privacyStatus": priv,
            "selfDeclaredMadeForKids": False,
        }
        if publish_at:
            status_body["privacyStatus"] = "private"
            status_body["publishAt"] = publish_at

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:30],
                "categoryId": cat_id,
                "defaultLanguage": "tr" if "tr" in channel_id or "yazan" in channel_id else "en",
            },
            "status": status_body,
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5,  # 5 MB chunk
        )

        print(f"[YT] '{channel_id}' kanalına yükleniyor: {title[:50]}...")

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
                print(f"[YT] Yükleme: %{pct}")

        video_id  = response.get("id", "")
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Thumbnail yükle (opsiyonel)
        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path),
                ).execute()
                print("[YT] Thumbnail yüklendi.")
            except Exception as e:
                print(f"[YT] Thumbnail hatası: {e}")

        print(f"[YT] ✅ Yüklendi → {video_url}")
        return {"video_id": video_id, "url": video_url, "status": priv}

    def list_channel_videos(self, channel_id: str, max_results: int = 10) -> list:
        """Kanalın son videolarını listeler."""
        service = self._get_service(channel_id)
        response = service.search().list(
            forMine=True,
            part="snippet",
            maxResults=max_results,
            type="video",
            order="date",
        ).execute()
        return response.get("items", [])
