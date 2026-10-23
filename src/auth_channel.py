"""
auth_channel.py
YouTube Kanalı OAuth2 Yetkilendirme Aracı
Google Cloud Console'dan indirilen client_secret.json dosyasını kullanarak
seçilen kanal için kalıcı token (credentials/{channel_id}_token.json) üretir.
"""

import sys
import os
from pathlib import Path

# Proje kök dizinini ekle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.youtube_uploader import YouTubeUploader
import json

def list_channels():
    channels_path = Path("config/channels.json")
    if channels_path.exists():
        try:
            data = json.loads(channels_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [c.get("channel_id") for c in data if c.get("channel_id")]
        except Exception:
            pass
    return ["yazanyazana", "tr1_reddithikayeleri"]

def authorize(channel_id: str):
    print(f"\n[AUTH] '{channel_id}' kanalı için Google OAuth yetkilendirmesi başlatılıyor...")
    print(f"[AUTH] Tarayıcınızda Google giriş ekranı açılacak.")
    print(f"[AUTH] Lütfen kanalınızın bağlı olduğu Google hesabını seçin ve izin verin.\n")
    
    uploader = YouTubeUploader()
    try:
        uploader._get_service(channel_id)
        token_file = Path(f"credentials/{channel_id}_token.json")
        if token_file.exists():
            print(f"\n🎉 TEBRİKLER! '{channel_id}' kanalı başarıyla bağlandı!")
            print(f"📁 Token dosyası hazır: {token_file.resolve()}")
            print(f"🚀 Artık bu kanala doğrudan video yükleyebilirsiniz.")
        else:
            print(f"\n⚠️ Token dosyası oluşturulamadı.")
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")

if __name__ == "__main__":
    channels = list_channels()
    target_channel = sys.argv[1] if len(sys.argv) > 1 else "yazanyazana"
    authorize(target_channel)
