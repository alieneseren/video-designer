"""
settings_manager.py
Fernet şifreleme ile API anahtarlarını ve uygulama ayarlarını yönetir.
"""

import json
import os
from pathlib import Path
from cryptography.fernet import Fernet

CONFIG_DIR = Path("config")
SETTINGS_FILE = CONFIG_DIR / "settings.json"
SECRET_KEY_FILE = CONFIG_DIR / ".secret_key"

SENSITIVE_FIELDS = {
    "anthropic_api_key",
    "gemini_api_key",
    "nasa_api_key",
    "pixabay_api_key",
    "instagram_access_token",
}

DEFAULT_SETTINGS = {
    "anthropic_api_key": "",
    "gemini_api_key": "",
    "nasa_api_key": "",
    "pixabay_api_key": "57648418-49ecb0060f2db281a386d04cf",
    "instagram_access_token": "",
    "instagram_user_id": "",
    "instagram_public_base_url": "",
    "instagram_graph_api_version": "v22.0",
    "ai_provider": "claude",          # claude | gemini | ollama | lmstudio
    "ai_model": "",                    # Boş = provider varsayılanı
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3",
    "lmstudio_url": "http://localhost:1234/v1",
    "lmstudio_model": "",              # Boş = LM Studio aktif modeli
    "output_dir": "output",
    "tts_engine": "edge-tts",          # edge-tts | chatterbox
    "chatterbox_voice": "",            # Klonlama için referans wav dosyasının yolu
    "active_voice_clone_id": "",       # Seçili yerel klon ses kimliği
    "rvc_pth_path": "",                # Applio RVC .pth model dosyasının yolu
    "rvc_index_path": "",              # Applio RVC .index dosyasının yolu
    "rvc_pitch": 0,                    # Ses perdesi: 0 = Erkek orijinal, 12 = Kadın versiyonu
    "auto_apply_voice_clone_on_download": True, # İndirilen videolara yerel RVC ses klonunu otomatik giydir
    "remote_tts_engine": "chatterbox", # chatterbox | kokoro
    "kokoro_voice": "am_michael",
    "kokoro_speed": "0.94",

    # ── Video Edit (v3) ──
    "subtitle_preset": "bold",         # minimal | bold | tiktok | youtube-classic | news
    "subtitle_animation": "fade",      # none | fade | pop | typewriter | word-highlight
    "bgm_path": "",                    # arka plan müzik dosyası (mp3/wav)
    "bgm_volume": "0.15",              # 0.0 - 1.0
    "watermark_path": "",              # opsiyonel PNG/JPG
    "watermark_text": "",              # opsiyonel metin (logo yoksa bunu kullan)
    "watermark_position": "top-right", # top-left | top-right | bottom-left | bottom-right | bottom-center
    "intro_clip_path": "",             # video başına eklenecek intro
    "outro_clip_path": "",             # video sonuna eklenecek outro
    "kenburns_intensity": "0.04",      # 0.0 - 0.10
    "transition_dur": "0.5",           # saniye
    "video_duration": "120",           # saniye
    "censor_faces": True,
    "auto_editor": False,
    "censor_logo_path": "",
    "censor_custom_landscape_enabled": False,
    "censor_custom_landscape_x": 0,
    "censor_custom_landscape_y": 0,
    "censor_custom_landscape_w": 0,
    "censor_custom_landscape_h": 0,
    "censor_custom_landscape_image_path": "",
    "censor_custom_portrait_enabled": False,
    "censor_custom_portrait_x": 0,
    "censor_custom_portrait_y": 0,
    "censor_custom_portrait_w": 0,
    "censor_custom_portrait_h": 0,
    "censor_custom_portrait_image_path": "",
}

# Tüm izin verilen ayar anahtarları (update whitelist)
ALLOWED_KEYS = set(DEFAULT_SETTINGS.keys())


class SettingsManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._fernet = self._load_or_create_key()
        self._data = self._load()

    def _load_or_create_key(self) -> Fernet:
        if SECRET_KEY_FILE.exists():
            key = SECRET_KEY_FILE.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            SECRET_KEY_FILE.write_bytes(key)
            os.chmod(SECRET_KEY_FILE, 0o600)
        return Fernet(key)

    def _encrypt(self, value: str) -> str:
        if not value: return ""
        return self._fernet.encrypt(value.encode()).decode()

    def _decrypt(self, token: str) -> str:
        if not token: return ""
        try: return self._fernet.decrypt(token.encode()).decode()
        except: return ""

    def _load(self) -> dict:
        if SETTINGS_FILE.exists():
            try:
                raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                result = {}
                for k, v in raw.items():
                    result[k] = self._decrypt(v) if k in SENSITIVE_FIELDS else v
                for k, v in DEFAULT_SETTINGS.items():
                    if k not in result:
                        result[k] = v
                return result
            except:
                return dict(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    def _save(self):
        encrypted = {}
        for k, v in self._data.items():
            encrypted[k] = self._encrypt(v) if k in SENSITIVE_FIELDS and v else v
        SETTINGS_FILE.write_text(json.dumps(encrypted, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_all(self) -> dict:
        return dict(self._data)

    def get_masked(self) -> dict:
        result = {}
        for k, v in self._data.items():
            if k in SENSITIVE_FIELDS and v:
                if len(v) > 10:
                    result[k] = v[:4] + "•" * (len(v) - 8) + v[-4:]
                else:
                    result[k] = "•" * len(v)
                result[f"{k}_set"] = True
            else:
                result[k] = v
                if k in SENSITIVE_FIELDS:
                    result[f"{k}_set"] = bool(v)
        return result

    def get(self, key: str, default: str = "") -> str:
        return self._data.get(key, default)

    def update(self, updates: dict):
        for k, v in updates.items():
            if k in ALLOWED_KEYS:
                if k in SENSITIVE_FIELDS and not v:
                    continue
                self._data[k] = v
        self._save()
        return self.get_masked()
