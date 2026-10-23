"""
Voice Profiles - Karakter Sesi & Ton Tasarımı
==============================================
"""

import os
from pathlib import Path

def _resolve_whatsapp_assets_dir() -> Path:
    candidates = [
        Path("/home/ubuntu/yt-render-server/assets/whatsapp/assets"),
        Path(__file__).resolve().parent.parent / "assets" / "whatsapp" / "assets",
        Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets",
        Path("config/assets/whatsapp/assets").resolve()
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets"

BASE_ASSETS = _resolve_whatsapp_assets_dir()
BGM_DIR = BASE_ASSETS / "bgm"
VOICE_SAMPLES_DIR = BASE_ASSETS / "voice_samples"
HYBRID_MALE_SAMPLE = str(VOICE_SAMPLES_DIR / "hybrid_male.wav")
HYBRID_FEMALE_SAMPLE = str(VOICE_SAMPLES_DIR / "hybrid_female.wav")
ELDERLY_MALE_SAMPLE = str(VOICE_SAMPLES_DIR / "elderly_male.wav")
ELDERLY_FEMALE_SAMPLE = str(VOICE_SAMPLES_DIR / "elderly_female.wav")

VOICE_PROFILES = {
    # ─── ERKEK KARAKTERLER (Hibrit Erkek Sesi) ───────────────────────────
    "kanka_erkek": {
        "voice": "tr-TR-AhmetNeural",
        "pitch": "+0Hz",
        "rate": "+8%",
        "audio_prompt_path": HYBRID_MALE_SAMPLE,
        "style_note": "Normal genç erkek arkadaş sesi. Rahat, sohbet tonu.",
        "ffmpeg_eq": "equalizer=f=3000:width_type=o:width=2:g=2,volume=1.1"
    },
    "odun_erkek": {
        "voice": "tr-TR-AhmetNeural",
        "pitch": "-8Hz",
        "rate": "-5%",
        "audio_prompt_path": HYBRID_MALE_SAMPLE,
        "style_note": "Biraz aptal, saf, naif erkek. Yavaş ve düz tonda konuşur.",
        "ffmpeg_eq": "equalizer=f=250:width_type=o:width=2:g=4,equalizer=f=4000:width_type=o:width=2:g=-3,volume=1.0"
    },
    "troll_erkek": {
        "voice": "tr-TR-AhmetNeural",
        "pitch": "+18Hz",
        "rate": "+20%",
        "audio_prompt_path": HYBRID_MALE_SAMPLE,
        "style_note": "Dalga geçen, eğlenceli troll. Hızlı ve yüksek perdeli.",
        "ffmpeg_eq": "equalizer=f=2000:width_type=o:width=2:g=4,equalizer=f=6000:width_type=o:width=1:g=3,volume=1.2"
    },
    "yorgun_erkek": {
        "voice": "tr-TR-AhmetNeural",
        "pitch": "-15Hz",
        "rate": "-12%",
        "audio_prompt_path": HYBRID_MALE_SAMPLE,
        "style_note": "Yorgun, bıkkın, üzgün erkek. Ağır ağır konuşur.",
        "ffmpeg_eq": "equalizer=f=200:width_type=o:width=2:g=5,equalizer=f=3500:width_type=o:width=2:g=-4,volume=0.95"
    },
    "sinirli_erkek": {
        "voice": "tr-TR-AhmetNeural",
        "pitch": "+10Hz",
        "rate": "+15%",
        "audio_prompt_path": HYBRID_MALE_SAMPLE,
        "style_note": "Sinirli, ağzı bozuk, keskin. Hızlı ve orta perdeli.",
        "ffmpeg_eq": "equalizer=f=1500:width_type=o:width=2:g=5,overdrive=gain=5,volume=1.15"
    },
    "baba": {
        "voice": "tr-TR-AhmetNeural",
        "pitch": "-20Hz",
        "rate": "-18%",
        "audio_prompt_path": ELDERLY_MALE_SAMPLE,
        "style_note": "Otoriter, derin sesli baba figürü. Ağır ve net.",
        "ffmpeg_eq": "equalizer=f=180:width_type=o:width=2:g=6,equalizer=f=5000:width_type=o:width=2:g=-5,volume=1.1"
    },
    "ev_sahibi": {
        "voice": "tr-TR-AhmetNeural",
        "pitch": "-12Hz",
        "rate": "-10%",
        "audio_prompt_path": ELDERLY_MALE_SAMPLE,
        "style_note": "Yaşlı, mağrur ev sahibi. Orta yaş derin sesi.",
        "ffmpeg_eq": "equalizer=f=220:width_type=o:width=2:g=5,equalizer=f=4500:width_type=o:width=2:g=-3,volume=1.05"
    },
    "dede": {
        "voice": "tr-TR-AhmetNeural",
        "pitch": "-22Hz",
        "rate": "-14%",
        "audio_prompt_path": ELDERLY_MALE_SAMPLE,
        "style_note": "Yaşlı, huysuz veya tonton dede sesi. Yavaş ve oturaklı.",
        "ffmpeg_eq": "equalizer=f=180:width_type=o:width=1.5:g=6,equalizer=f=3500:width_type=o:width=2:g=-3,volume=1.1"
    },
    "ihtiyar_erkek": {
        "voice": "tr-TR-AhmetNeural",
        "pitch": "-24Hz",
        "rate": "-15%",
        "audio_prompt_path": ELDERLY_MALE_SAMPLE,
        "style_note": "İhtiyar, yaşlı amca / dede sesi.",
        "ffmpeg_eq": "equalizer=f=180:width_type=o:width=1.5:g=6,equalizer=f=3500:width_type=o:width=2:g=-3,volume=1.1"
    },

    # ─── KADIN KARAKTERLER (Hibrit Kadın Sesi) ───────────────────────────
    "kanka_kadin": {
        "voice": "tr-TR-EmelNeural",
        "pitch": "+0Hz",
        "rate": "+5%",
        "audio_prompt_path": HYBRID_FEMALE_SAMPLE,
        "style_note": "Normal genç kadın arkadaş sesi. Doğal, rahat.",
        "ffmpeg_eq": "equalizer=f=3000:width_type=o:width=2:g=2,volume=1.1"
    },
    "kiskanclik_kadin": {
        "voice": "tr-TR-EmelNeural",
        "pitch": "+15Hz",
        "rate": "+22%",
        "audio_prompt_path": HYBRID_FEMALE_SAMPLE,
        "style_note": "Kıskanç, panik halinde, hızlı konuşan kadın.",
        "ffmpeg_eq": "equalizer=f=2500:width_type=o:width=2:g=5,equalizer=f=5000:width_type=o:width=1:g=3,volume=1.25"
    },
    "sakin_kadin": {
        "voice": "tr-TR-EmelNeural",
        "pitch": "-5Hz",
        "rate": "-8%",
        "audio_prompt_path": HYBRID_FEMALE_SAMPLE,
        "style_note": "Sakin, güvenen, dingin kadın sesi.",
        "ffmpeg_eq": "equalizer=f=400:width_type=o:width=2:g=3,equalizer=f=5000:width_type=o:width=2:g=-2,volume=1.0"
    },
    "kizgin_kadin": {
        "voice": "tr-TR-EmelNeural",
        "pitch": "+20Hz",
        "rate": "+25%",
        "audio_prompt_path": HYBRID_FEMALE_SAMPLE,
        "style_note": "Çok sinirli, bağıran kadın. Yüksek perde + hızlı.",
        "ffmpeg_eq": "equalizer=f=2000:width_type=o:width=2:g=6,overdrive=gain=4,volume=1.3"
    },
    "anne": {
        "voice": "tr-TR-EmelNeural",
        "pitch": "-8Hz",
        "rate": "-5%",
        "audio_prompt_path": HYBRID_FEMALE_SAMPLE,
        "style_note": "Orta yaş anne sesi. Kontrollü, otoriter.",
        "ffmpeg_eq": "equalizer=f=350:width_type=o:width=2:g=4,equalizer=f=4500:width_type=o:width=2:g=-2,volume=1.05"
    },
    "nine": {
        "voice": "tr-TR-EmelNeural",
        "pitch": "-14Hz",
        "rate": "-10%",
        "audio_prompt_path": ELDERLY_FEMALE_SAMPLE,
        "style_note": "Tonton nine / yaşlı teyze sesi. Yavaş, çatallı ve sevecen.",
        "ffmpeg_eq": "equalizer=f=320:width_type=o:width=1.5:g=5,equalizer=f=4000:width_type=o:width=2:g=-2,volume=1.05"
    },
    "ihtiyar_kadin": {
        "voice": "tr-TR-EmelNeural",
        "pitch": "-16Hz",
        "rate": "-12%",
        "audio_prompt_path": ELDERLY_FEMALE_SAMPLE,
        "style_note": "İhtiyar kadın / yaşlı nine / huysuz kaynana sesi.",
        "ffmpeg_eq": "equalizer=f=320:width_type=o:width=1.5:g=5,equalizer=f=4000:width_type=o:width=2:g=-2,volume=1.05"
    },
    "teyze": {
        "voice": "tr-TR-EmelNeural",
        "pitch": "-10Hz",
        "rate": "-8%",
        "audio_prompt_path": ELDERLY_FEMALE_SAMPLE,
        "style_note": "Dedikoducu, meraklı komşu teyze sesi.",
        "ffmpeg_eq": "equalizer=f=350:width_type=o:width=1.5:g=4,equalizer=f=4200:width_type=o:width=2:g=-2,volume=1.1"
    },
}

# ─── TELİFSİZ MÜZİK KÜTÜPHANESİ ────────────────────────────────────
BGM_TRACKS = {
    "quirky_troll": {
        "path": str(BGM_DIR / "sneaky_snitch.mp3"),
        "description": "Kevin MacLeod - Sneaky Snitch. Mizahi, gizli trollük, afacan ve ters köşe diyaloglar için en popüler fon müziği.",
        "tempo": "medium_fast",
        "license": "CC-BY 3.0 Kevin MacLeod"
    },
    "viral_bounce": {
        "path": str(BGM_DIR / "monkeys_spinning.mp3"),
        "description": "Kevin MacLeod - Monkeys Spinning Monkeys. TikTok/Shorts'un en viral komedi ve absürt diyalog müziği.",
        "tempo": "fast",
        "license": "CC-BY 3.0 Kevin MacLeod"
    },
    "silly_fun": {
        "path": str(BGM_DIR / "fluffing_duck.mp3"),
        "description": "Kevin MacLeod - Fluffing a Duck. Odun sevgili, saflık ve absürt komik cevaplar için eğlenceli müzik.",
        "tempo": "medium",
        "license": "CC-BY 3.0 Kevin MacLeod"
    },
    "cunning_scheme": {
        "path": str(BGM_DIR / "scheming_weasel.mp3"),
        "description": "Kevin MacLeod - Scheming Weasel. Açgözlü ev sahibi, kıskanç sevgili ve entrikalı planlar için kurnaz komedi müziği.",
        "tempo": "fast",
        "license": "CC-BY 3.0 Kevin MacLeod"
    },
    "comedy_upbeat": {
        "path": str(BGM_DIR / "comedy_upbeat.mp3"),
        "description": "Hızlı tempo komedi/ukulele hissi. Genel hafif neşeli komedi için.",
        "tempo": "fast",
        "license": "CC-BY - Tours / Free Music Archive"
    },
    "lofi_chill": {
        "path": str(BGM_DIR / "lofi_chill.mp3"),
        "description": "Yavaş, rahat lofi hissi. Hüzünlü, gece veya sarkastik sahneler için.",
        "tempo": "slow",
        "license": "CC-BY - Tours / Free Music Archive"
    },
    "lofi_enthusiast": {
        "path": str(BGM_DIR / "lofi_enthusiast.mp3"),
        "description": "Orta tempo, canlı lofi. Genel amaçlı kullanım.",
        "tempo": "medium",
        "license": "CC-BY - Tours / Free Music Archive"
    },
    "synthetic_comedy": {
        "path": str(BGM_DIR / "comedy_vibe.wav"),
        "description": "Sentetik lofi akord müzik. Fallback olarak kullanılır.",
        "tempo": "medium",
        "license": "Özgün sentez (telif yok)"
    },
}

# ─── SENARYO → OTOMATİK SES PROFİLİ EŞLEMESİ ────────────────────────
SCENARIO_VOICE_MAP = {
    "odun_sevgili": {
        "contact": "odun_erkek",    # Selim
        "user": "troll_erkek",      # Ben
        "bgm": "silly_fun"
    },
    "kiskanclik_krizi": {
        "contact": "kiskanclik_kadin",
        "user": "yorgun_erkek",
        "bgm": "cunning_scheme"
    },
    "ev_sahibi": {
        "contact": "ev_sahibi",
        "user": "sinirli_erkek",
        "bgm": "cunning_scheme"
    },
    "troll_kanka": {
        "contact": "troll_erkek",
        "user": "kanka_erkek",
        "bgm": "quirky_troll"
    },
    "anne_teknoloji": {
        "contact": "anne",
        "user": "troll_erkek",
        "bgm": "viral_bounce"
    },
    "patron_mesai": {
        "contact": "sinirli_erkek",
        "user": "yorgun_erkek",
        "bgm": "cunning_scheme"
    },
    "default": {
        "contact": "odun_erkek",
        "user": "troll_erkek",
        "bgm": "quirky_troll"
    }
}

# ─── İNGİLİZCE VE ÇOK DİLLİ SES PROFİLLERİ (English Neural Voices) ────────
VOICE_PROFILES_EN = {
    # ── MALE ─────────────────────────────────────────────────────────────
    "kanka_erkek": {
        "voice": "en-US-ChristopherNeural",
        "pitch": "+0Hz",
        "rate": "+6%",
        "style_note": "Natural young male buddy voice.",
        "ffmpeg_eq": "equalizer=f=3000:width_type=o:width=2:g=2,volume=1.1"
    },
    "odun_erkek": {
        "voice": "en-US-EricNeural",
        "pitch": "-6Hz",
        "rate": "-4%",
        "style_note": "Deadpan, blunt, naive male.",
        "ffmpeg_eq": "equalizer=f=250:width_type=o:width=2:g=4,equalizer=f=4000:width_type=o:width=2:g=-3,volume=1.0"
    },
    "troll_erkek": {
        "voice": "en-US-GuyNeural",
        "pitch": "+10Hz",
        "rate": "+15%",
        "style_note": "Playful, sarcastic, comedic troll male.",
        "ffmpeg_eq": "equalizer=f=2000:width_type=o:width=2:g=4,equalizer=f=6000:width_type=o:width=1:g=3,volume=1.2"
    },
    "yorgun_erkek": {
        "voice": "en-US-EricNeural",
        "pitch": "-12Hz",
        "rate": "-10%",
        "style_note": "Tired, sighing, stressed male.",
        "ffmpeg_eq": "equalizer=f=200:width_type=o:width=2:g=5,equalizer=f=3500:width_type=o:width=2:g=-4,volume=0.95"
    },
    "sinirli_erkek": {
        "voice": "en-US-RogerNeural",
        "pitch": "+4Hz",
        "rate": "+10%",
        "style_note": "Angry, authoritative boss or annoyed friend.",
        "ffmpeg_eq": "equalizer=f=1500:width_type=o:width=2:g=5,overdrive=gain=3,volume=1.15"
    },
    "baba": {
        "voice": "en-US-RogerNeural",
        "pitch": "-10Hz",
        "rate": "-10%",
        "style_note": "Authoritative dad figure.",
        "ffmpeg_eq": "equalizer=f=180:width_type=o:width=2:g=6,equalizer=f=5000:width_type=o:width=2:g=-5,volume=1.1"
    },
    "ev_sahibi": {
        "voice": "en-US-RogerNeural",
        "pitch": "-8Hz",
        "rate": "-8%",
        "style_note": "Grumpy landlord / boss.",
        "ffmpeg_eq": "equalizer=f=220:width_type=o:width=2:g=5,equalizer=f=4500:width_type=o:width=2:g=-3,volume=1.05"
    },
    "dede": {
        "voice": "en-US-RogerNeural",
        "pitch": "-16Hz",
        "rate": "-14%",
        "style_note": "Grandpa / elderly man.",
        "ffmpeg_eq": "equalizer=f=180:width_type=o:width=1.5:g=6,equalizer=f=3500:width_type=o:width=2:g=-3,volume=1.1"
    },
    "ihtiyar_erkek": {
        "voice": "en-US-RogerNeural",
        "pitch": "-18Hz",
        "rate": "-15%",
        "style_note": "Elderly man.",
        "ffmpeg_eq": "equalizer=f=180:width_type=o:width=1.5:g=6,equalizer=f=3500:width_type=o:width=2:g=-3,volume=1.1"
    },

    # ── FEMALE ───────────────────────────────────────────────────────────
    "kanka_kadin": {
        "voice": "en-US-JennyNeural",
        "pitch": "+0Hz",
        "rate": "+5%",
        "style_note": "Young female bestie.",
        "ffmpeg_eq": "equalizer=f=3000:width_type=o:width=2:g=2,volume=1.1"
    },
    "kiskanclik_kadin": {
        "voice": "en-US-AriaNeural",
        "pitch": "+12Hz",
        "rate": "+18%",
        "style_note": "Jealous / panicked girlfriend.",
        "ffmpeg_eq": "equalizer=f=2500:width_type=o:width=2:g=5,equalizer=f=5000:width_type=o:width=1:g=3,volume=1.25"
    },
    "sakin_kadin": {
        "voice": "en-US-JennyNeural",
        "pitch": "-4Hz",
        "rate": "-6%",
        "style_note": "Calm, composed female.",
        "ffmpeg_eq": "equalizer=f=400:width_type=o:width=2:g=3,equalizer=f=5000:width_type=o:width=2:g=-2,volume=1.0"
    },
    "kizgin_kadin": {
        "voice": "en-US-AriaNeural",
        "pitch": "+15Hz",
        "rate": "+20%",
        "style_note": "Angry, shouting female.",
        "ffmpeg_eq": "equalizer=f=2000:width_type=o:width=2:g=6,overdrive=gain=4,volume=1.3"
    },
    "anne": {
        "voice": "en-US-MichelleNeural",
        "pitch": "-6Hz",
        "rate": "-4%",
        "style_note": "Mature mom voice.",
        "ffmpeg_eq": "equalizer=f=350:width_type=o:width=2:g=4,equalizer=f=4500:width_type=o:width=2:g=-2,volume=1.05"
    },
    "nine": {
        "voice": "en-US-MichelleNeural",
        "pitch": "-12Hz",
        "rate": "-10%",
        "style_note": "Grandma / elderly female.",
        "ffmpeg_eq": "equalizer=f=320:width_type=o:width=1.5:g=5,equalizer=f=4000:width_type=o:width=2:g=-2,volume=1.05"
    },
    "ihtiyar_kadin": {
        "voice": "en-US-MichelleNeural",
        "pitch": "-14Hz",
        "rate": "-12%",
        "style_note": "Elderly woman.",
        "ffmpeg_eq": "equalizer=f=320:width_type=o:width=1.5:g=5,equalizer=f=4000:width_type=o:width=2:g=-2,volume=1.05"
    },
    "teyze": {
        "voice": "en-US-MichelleNeural",
        "pitch": "-8Hz",
        "rate": "-6%",
        "style_note": "Curious neighbor / aunt.",
        "ffmpeg_eq": "equalizer=f=350:width_type=o:width=1.5:g=4,equalizer=f=4200:width_type=o:width=2:g=-2,volume=1.1"
    }
}

# English Role Aliases (so LLM can output "mom", "dad", "boss", "landlord", "troll_friend")
VOICE_PROFILES_EN["mom"] = VOICE_PROFILES_EN["anne"]
VOICE_PROFILES_EN["mother"] = VOICE_PROFILES_EN["anne"]
VOICE_PROFILES_EN["dad"] = VOICE_PROFILES_EN["baba"]
VOICE_PROFILES_EN["father"] = VOICE_PROFILES_EN["baba"]
VOICE_PROFILES_EN["grandpa"] = VOICE_PROFILES_EN["dede"]
VOICE_PROFILES_EN["grandma"] = VOICE_PROFILES_EN["nine"]
VOICE_PROFILES_EN["landlord"] = VOICE_PROFILES_EN["ev_sahibi"]
VOICE_PROFILES_EN["boss"] = VOICE_PROFILES_EN["sinirli_erkek"]
VOICE_PROFILES_EN["bestie_male"] = VOICE_PROFILES_EN["kanka_erkek"]
VOICE_PROFILES_EN["bestie_female"] = VOICE_PROFILES_EN["kanka_kadin"]
VOICE_PROFILES_EN["troll_friend"] = VOICE_PROFILES_EN["troll_erkek"]
VOICE_PROFILES_EN["tired_friend"] = VOICE_PROFILES_EN["yorgun_erkek"]
VOICE_PROFILES_EN["calm_friend"] = VOICE_PROFILES_EN["sakin_kadin"]

LANGUAGE_DEFAULT_VOICES = {
    "tr": {"male": "tr-TR-AhmetNeural", "female": "tr-TR-EmelNeural"},
    "en": {"male": "en-US-ChristopherNeural", "female": "en-US-JennyNeural"},
    "de": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural"},
    "es": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural"},
    "fr": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural"},
    "it": {"male": "it-IT-DiegoNeural", "female": "it-IT-ElsaNeural"},
    "pt": {"male": "pt-BR-AntonioNeural", "female": "pt-BR-FranciscaNeural"},
    "ru": {"male": "ru-RU-DmitryNeural", "female": "ru-RU-SvetlanaNeural"},
}

def get_voice_profiles(language: str = "tr") -> dict:
    lang = (language or "tr").lower().strip()
    if lang == "tr" or lang.startswith("tr"):
        return VOICE_PROFILES
    return VOICE_PROFILES_EN

def get_default_voice(gender: str = "male", language: str = "tr") -> str:
    lang = (language or "tr").lower().strip()
    g = "female" if str(gender).lower() in ("female", "kadin", "kadın") else "male"
    mapping = LANGUAGE_DEFAULT_VOICES.get(lang, LANGUAGE_DEFAULT_VOICES["en"])
    return mapping.get(g, "en-US-ChristopherNeural")

