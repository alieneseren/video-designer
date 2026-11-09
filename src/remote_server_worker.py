"""
server_worker.py
Oracle Cloud Uzak Video Üretim ve YouTube API Yükleme/Temizleme Motoru.
Tüm kanal türlerini (WhatsApp, Reddit, Savunma Haberleri, Uzay/Genel) destekler.
Web sitelerini etkilememek için düşük CPU/IO önceliği ile çalışır.
"""

import os
import re
import sys
import json
import time
import math
import shutil
import base64
import random
import copy
import urllib.parse
import urllib.request
import asyncio
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Sanal ortam paketlerini dahil et
VENV_PATH = Path("/home/ubuntu/defense_news_shorts/.venv")
sys.path.insert(0, str(VENV_PATH / "lib/python3.10/site-packages"))
sys.path.insert(0, "/home/ubuntu/yt-remote-worker")

BASE_DIR = Path("/home/ubuntu/yt-remote-worker")
REMOTION_DIR = BASE_DIR / "remotion"
OUTPUT_BASE = BASE_DIR / "output"
CREDENTIALS_DIR = BASE_DIR / "credentials"
JOBS_DIR = BASE_DIR / "jobs"

# Yerel gizli .env dosyasını ortam değişkenlerine yükle
_ENV_FILE = BASE_DIR / ".env"
if _ENV_FILE.exists():
    try:
        for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))
    except Exception:
        pass

import edge_tts

_TRANSLATE_CACHE: dict = {}

def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> tuple[str, str]:
    if not text or not str(text).strip():
        return text, target_lang
    text_str = str(text).strip()
    target_lang = target_lang.lower().strip()
    source_lang = source_lang.lower().strip()
    cache_key = (text_str, target_lang, source_lang)
    if cache_key in _TRANSLATE_CACHE:
        return _TRANSLATE_CACHE[cache_key]
    try:
        encoded = urllib.parse.quote(text_str)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={encoded}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join([segment[0] for segment in data[0] if segment and segment[0]])
            detected = data[2] if len(data) > 2 and data[2] else source_lang
            res = (translated or text_str, detected)
            _TRANSLATE_CACHE[cache_key] = res
            return res
    except Exception as e:
        print(f"[Worker-Localization] ⚠️ Çeviri uyarısı ({target_lang}): {e}")
        return text_str, "unknown"

def detect_language(text: str) -> str:
    if not text or not str(text).strip():
        return "tr"
    _, det = translate_text(text[:250], "en", "auto")
    return det if det and det != "unknown" else "tr"

def ensure_localized_script(script_data: dict, target_lang: str) -> dict:
    if not isinstance(script_data, dict):
        return script_data
    target_lang = (target_lang or "tr").lower().strip()
    if target_lang in script_data and isinstance(script_data[target_lang], dict):
        res = copy.deepcopy(script_data[target_lang])
        res["language"] = target_lang
        return res
    if "scripts" in script_data and isinstance(script_data["scripts"], dict) and target_lang in script_data["scripts"]:
        res = copy.deepcopy(script_data["scripts"][target_lang])
        res["language"] = target_lang
        return res
    candidate = copy.deepcopy(script_data)
    for lk in ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko"]:
        if lk in candidate and isinstance(candidate[lk], dict) and ("scenes" in candidate[lk] or "messages" in candidate[lk] or "narration" in candidate[lk]):
            candidate = copy.deepcopy(candidate[lk])
            break
    sample_text = (
        candidate.get("question") or
        candidate.get("title") or
        candidate.get("description") or
        ""
    )
    if not sample_text and candidate.get("scenes") and isinstance(candidate["scenes"], list) and len(candidate["scenes"]) > 0:
        sample_text = candidate["scenes"][0].get("narration") or candidate["scenes"][0].get("text") or ""
    if not sample_text and candidate.get("messages") and isinstance(candidate["messages"], list) and len(candidate["messages"]) > 0:
        sample_text = candidate["messages"][0].get("text") or ""
    # Gerçek metin dilini tespit et (metadata 'language' yanıltıcı olabilir)
    actual_detected = detect_language(sample_text) if sample_text else None
    detected_src = actual_detected or candidate.get("language") or "tr"
    if detected_src and detected_src.lower().strip() == target_lang:
        candidate["language"] = target_lang
        return candidate
    print(f"[Worker-Localization] 🌐 Senaryo yerelleştiriliyor: '{detected_src or 'auto'}' -> '{target_lang}'...")
    if candidate.get("title"):
        trans_title, _ = translate_text(candidate["title"], target_lang)
        candidate["title"] = trans_title
    if candidate.get("question"):
        trans_q, _ = translate_text(candidate["question"], target_lang)
        candidate["question"] = trans_q
    if candidate.get("description"):
        trans_desc, _ = translate_text(candidate["description"], target_lang)
        candidate["description"] = trans_desc
    if candidate.get("contact_name") and candidate["contact_name"].lower() in ["annem ❤️", "babam 👑", "patron 🏢", "kardeşim"]:
        name_map = {
            "en": {"annem ❤️": "Mom ❤️", "babam 👑": "Dad 👑", "patron 🏢": "Boss 🏢", "kardeşim": "Bro"},
            "de": {"annem ❤️": "Mama ❤️", "babam 👑": "Papa 👑", "patron 🏢": "Chef 🏢", "kardeşim": "Bruder"},
            "es": {"annem ❤️": "Mamá ❤️", "babam 👑": "Papá 👑", "patron 🏢": "Jefe 🏢", "kardeşim": "Hermano"},
        }
        if target_lang in name_map and candidate["contact_name"].lower() in name_map[target_lang]:
            candidate["contact_name"] = name_map[target_lang][candidate["contact_name"].lower()]
        else:
            trans_c, _ = translate_text(candidate["contact_name"], target_lang)
            candidate["contact_name"] = trans_c
    if "scenes" in candidate and isinstance(candidate["scenes"], list):
        for s in candidate["scenes"]:
            if isinstance(s, dict):
                for k in ["narration", "text", "dialogue"]:
                    if s.get(k):
                        trans_val, _ = translate_text(s[k], target_lang)
                        s[k] = trans_val
    if "messages" in candidate and isinstance(candidate["messages"], list):
        for m in candidate["messages"]:
            if isinstance(m, dict) and m.get("text"):
                trans_m, _ = translate_text(m["text"], target_lang)
                m["text"] = trans_m
    if "tags" in candidate and isinstance(candidate["tags"], list):
        candidate["tags"] = [translate_text(tg, target_lang)[0] for tg in candidate["tags"]]
    if "subreddit" in candidate:
        if target_lang == "tr":
            if candidate["subreddit"] in ("r/AskReddit", "r/reddit"):
                candidate["subreddit"] = "r/RedditHikayeleri"
        else:
            if "turk" in candidate["subreddit"].lower() or "hikaye" in candidate["subreddit"].lower():
                candidate["subreddit"] = "r/AskReddit"
    candidate["language"] = target_lang
    print(f"[Worker-Localization] ✅ Senaryo '{target_lang.upper()}' diline yerelleştirildi: {candidate.get('title')}")
    return candidate

def resolve_asmr_background_video(pub_media: Path, work_dir: Path, target_duration: float = 60.0) -> str:
    """Remotion için yüksek izlenme oranına sahip 1080x1920 dikey ASMR/Oyun arka plan videosunu seçer."""
    try:
        candidates = []
        if pub_media.exists():
            for ext in ("*.mp4", "*.mov", "*.webm"):
                candidates.extend(pub_media.glob(ext))
        asmr_dir = BASE_DIR / "assets" / "asmr"
        if asmr_dir.exists():
            for ext in ("*.mp4", "*.mov", "*.webm"):
                candidates.extend(asmr_dir.glob(ext))

        # Seyir zevki düşük, yapay desen veya yatay kırpılmış videoları kesinlikle dışla
        blacklist_terms = [
            "synthetic", "pixabay", "test", "wa_audio", "reddit_audio",
            "voiceover", "temp", "render", "avatar", "batch", "group", "wallpaper"
        ]

        # Viral, yüksek tutundurmalı (high-retention) dikey video öncelikleri
        priority_terms = ["gta5", "mega_ramp", "soap_cutting", "marble_run", "kinetic_sand", "asmr", "satisfying"]

        valid_asmr = []
        priority_asmr = []
        seen_names = set()

        for f in candidates:
            if f.is_file() and not f.is_symlink() and f.stat().st_size > 500_000:
                fn_lower = f.name.lower()
                if not any(term in fn_lower for term in blacklist_terms):
                    if f.name not in seen_names:
                        seen_names.add(f.name)
                        valid_asmr.append(f)
                        if any(p in fn_lower for p in priority_terms):
                            priority_asmr.append(f)

        pool = priority_asmr if priority_asmr else valid_asmr
        if pool:
            # Anti-Repetition Tarihçesi: Son kullanılan videoları dışla
            history_file = pub_media.parent / "asmr_usage_history.json"
            recent_used = []
            if history_file.exists():
                try:
                    recent_used = json.loads(history_file.read_text(encoding="utf-8"))
                except Exception:
                    recent_used = []

            # Son kullanılanları hariç tut (eğer havuzda alternatif varsa)
            fresh_candidates = [v for v in pool if v.name not in recent_used]
            if not fresh_candidates:
                # Havuzdaki tüm videolar döngüye girdiyse sıfırla
                fresh_candidates = pool
                recent_used = []

            chosen = random.choice(fresh_candidates)
            recent_used.append(chosen.name)
            try:
                history_file.write_text(json.dumps(recent_used[-15:], indent=2), encoding="utf-8")
            except Exception:
                pass

            dest = pub_media / chosen.name
            if not dest.exists() or dest.stat().st_size != chosen.stat().st_size:
                shutil.copy2(str(chosen), str(dest))
            print(f"[Worker] 🎬 Kaliteli ve Çeşitlendirilmiş ASMR/Oyun arka plan videosu seçildi: media/{chosen.name} ({chosen.stat().st_size / (1024*1024):.1f} MB)")
            return f"media/{chosen.name}"

        # Yerel kütüphanede bulunamadıysa asmr_manager fallback
        try:
            import asmr_manager
            asmr_list = asmr_manager.ensure_asmr_library(target_duration=target_duration)
            filtered_list = [v for v in asmr_list if not any(t in v.name.lower() for t in blacklist_terms)]
            if filtered_list:
                chosen = random.choice(filtered_list)
                dest = pub_media / chosen.name
                if not dest.exists():
                    shutil.copy2(str(chosen), str(dest))
                print(f"[Worker] 🎬 Kütüphaneden ASMR videosu hazırlandı: media/{chosen.name}")
                return f"media/{chosen.name}"
        except Exception as e_mgr:
            print(f"[Worker] ⚠️ asmr_manager çağrısı uyarısı: {e_mgr}")
    except Exception as e:
        print(f"[Worker] ⚠️ ASMR arka plan seçimi uyarısı: {e}")
    return ""

# ─────────────────────────────────────────────────────────────
# 1. Seslendirme Motoru (Edge TTS)
# ─────────────────────────────────────────────────────────────
VOICE_MAP = {
    "tr": {
        "female": "tr-TR-EmelNeural",
        "male": "tr-TR-AhmetNeural",
        "narrator": "tr-TR-AhmetNeural",
    },
    "en": {
        "female": "en-US-JennyNeural",
        "male": "en-US-GuyNeural",
        "narrator": "en-US-ChristopherNeural",
    },
    "de": {
        "female": "de-DE-KatjaNeural",
        "male": "de-DE-ConradNeural",
        "narrator": "de-DE-KillianNeural",
    },
    "es": {
        "female": "es-ES-ElviraNeural",
        "male": "es-ES-AlvaroNeural",
        "narrator": "es-ES-AlvaroNeural",
    }
}

KOKORO_LANGUAGES = {
    "en": ("en-us", "am_michael"),
    "es": ("es", "em_alex"),
    "fr": ("fr-fr", "ff_siwis"),
    "hi": ("hi", "hm_omega"),
    "it": ("it", "im_nicola"),
    "ja": ("ja", "jf_alpha"),
    "pt": ("pt-br", "pm_alex"),
    "zh": ("cmn", "zf_xiaobei"),
}
KOKORO_ENGLISH_VOICES = {"am_michael", "am_fenrir", "af_bella", "af_heart"}


def resolve_kokoro_voice(lang: str, voice: str) -> tuple[str, str] | None:
    lang_config = KOKORO_LANGUAGES.get(lang.split("-", 1)[0])
    if not lang_config:
        return None
    kokoro_lang, default_voice = lang_config
    selected_voice = voice if lang.startswith("en") and voice in KOKORO_ENGLISH_VOICES else default_voice
    return kokoro_lang, selected_voice


def _get_kokoro_speed(job_data: dict) -> float:
    try:
        speed = float(job_data.get("kokoro_speed", 0.94))
    except (TypeError, ValueError) as exc:
        raise ValueError("Kokoro konuşma hızı sayısal olmalıdır.") from exc
    if not 0.8 <= speed <= 1.2:
        raise ValueError("Kokoro konuşma hızı 0.8 ile 1.2 arasında olmalıdır.")
    return speed


def generate_kokoro_batch(texts: list[str], output_paths: list[Path], lang: str, voice: str, speed: float) -> None:
    lang_config = resolve_kokoro_voice(lang, voice)
    if not lang_config:
        raise ValueError(f"Kokoro-TTS bu dili desteklemiyor: {lang}")
    kokoro_lang, selected_voice = lang_config

    helper_path = Path(__file__).resolve().with_name("kokoro_tts_worker.py")
    python_path = Path(os.environ.get("KOKORO_TTS_PYTHON", BASE_DIR / "kokoro-venv" / "bin" / "python3"))
    if not python_path.is_file():
        raise RuntimeError(f"Kokoro ortamı kurulu değil: {python_path}")
    if not helper_path.is_file():
        raise RuntimeError(f"Kokoro yardımcı betiği bulunamadı: {helper_path}")

    request_path = output_paths[0].parent / "kokoro_request.json"
    request_path.write_text(json.dumps({
        "texts": texts,
        "output_paths": [str(path) for path in output_paths],
        "language": kokoro_lang,
        "voice": selected_voice,
        "speed": speed,
        "model_path": str(BASE_DIR / "models" / "kokoro" / "kokoro-v1.0.onnx"),
        "voices_path": str(BASE_DIR / "models" / "kokoro" / "voices-v1.0.bin"),
    }, ensure_ascii=False), encoding="utf-8")
    try:
        result = subprocess.run(
            [str(python_path), str(helper_path), str(request_path)],
            capture_output=True, text=True, timeout=7200,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Kokoro sentezi başarısız oldu.")
        missing = [str(path) for path in output_paths if not path.is_file() or path.stat().st_size < 1000]
        if missing:
            raise RuntimeError(f"Kokoro ses dosyalarını oluşturamadı: {', '.join(missing)}")
        print(result.stdout.strip())
    finally:
        request_path.unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────
# 1.1 Emoji Temizleme ve Dinamik Duygu / Üslup Analiz Motoru
# ─────────────────────────────────────────────────────────────
EMOJI_REGEX = re.compile(
    r'['
    r'\U0001F600-\U0001F64F'  # Emoticons
    r'\U0001F300-\U0001F5FF'  # Misc Symbols and Pictographs
    r'\U0001F680-\U0001F6FF'  # Transport and Map
    r'\U0001F1E0-\U0001F1FF'  # Flags
    r'\U0001F900-\U0001F9FF'  # Supplemental Symbols and Pictographs
    r'\U0001FA00-\U0001FA6F'  # Symbols and Pictographs Extended-A
    r'\U0001FA70-\U0001FAFF'  # Symbols and Pictographs Extended-B
    r'\u2702-\u27B0'          # Dingbats
    r'\u24C2-\u25FF'          # Enclosed & geometric
    r'\u2600-\u26FF'          # Misc Symbols (❤️, ⚡, ⚠️ vb.)
    r'\u2300-\u23FF'          # Technical
    r'\u2B00-\u2BFF'          # Arrows & misc
    r'\u200D'                  # Zero-width joiner
    r'\uFE0E-\uFE0F'          # Variation selectors
    r'\U0001F3FB-\U0001F3FF'  # Skin tones
    r']+',
    flags=re.UNICODE
)

def prepare_speech_text_and_tone(raw_text: str, lang: str = "tr") -> tuple[str, str, str]:
    """
    1. Emojileri analiz ederek seslendirmenin tonlamasını (rate, pitch) duygusal olarak ayarlar.
    2. Emojileri seslendirilecek metinden tamamen temizler (asla emoji adını seslendirmez).
    3. Metin tamamen emojiden ibaretse, emojiye uygun doğal bir nida/ünlem üretir.
    Döndürür: (spoken_text, rate, pitch)
    """
    raw_str = str(raw_text or "").strip()
    low_text = raw_str.lower()
    is_tr = (lang == "tr" or lang.startswith("tr"))

    # Varsayılan üslup
    rate = "+3%"
    pitch = "+0Hz"
    emoji_fallback = "Efendim?" if is_tr else "Yes?"

    # A) Kahkaha / Neşe / Dalga / Troll (😂, 🤣, 😆, 😹, 💀)
    if any(e in raw_str for e in ["😂", "🤣", "😆", "😹", "💀"]) or any(w in low_text for w in ["haha", "koptum", "öldüm gülmekten", "çatladım", "lmao", "lol"]):
        rate = "+10%"
        pitch = "+6Hz"
        emoji_fallback = "Haha!"

    # B) Şok / Şaşkınlık / Heyecan / Hype (😱, 😲, 🤯, 🔥, ⚡, 🎉, 🚀)
    elif any(e in raw_str for e in ["😱", "😲", "🤯", "🔥", "⚡", "🎉", "🚀"]) or any(w in low_text for w in ["oha", "yuh", "çüş", "inanamıyorum", "ciddi misin", "omg", "wow"]):
        rate = "+12%"
        pitch = "+10Hz"
        emoji_fallback = "Yok artık!" if is_tr else "No way!"

    # C) Sevgi / Romantizm / Tatlılık / Şefkat (😍, 🥰, 😘, ❤️, 💕, 💖, 💘, 🌹)
    elif any(e in raw_str for e in ["😍", "🥰", "😘", "❤️", "💕", "💖", "💘", "🌹"]) or any(w in low_text for w in ["aşkım", "canım", "birtanem", "sevgilim", "honey", "darling"]):
        rate = "-2%"
        pitch = "+4Hz"
        emoji_fallback = "Canım benim!" if is_tr else "My love!"

    # D) Üzüntü / Ağlama / Hayal Kırıklığı / Masumiyet (😢, 😭, 🥺, 😔, 💔, 😞, 😿)
    elif any(e in raw_str for e in ["😢", "😭", "🥺", "😔", "💔", "😞", "😿"]) or any(w in low_text for w in ["üzüldüm", "off ya", "yapma ya", "yazık", "sad"]):
        rate = "-6%"
        pitch = "-4Hz"
        emoji_fallback = "Off ya..." if is_tr else "Oh no..."

    # E) Öfke / Kızgınlık / Sinir (😡, 😠, 🤬, 😤, 👿)
    elif any(e in raw_str for e in ["😡", "😠", "🤬", "😤", "👿"]) or any(w in low_text for w in ["yeter", "saçmalama", "deli etme", "bıktım", "sinir"]):
        rate = "+6%"
        pitch = "-3Hz"
        emoji_fallback = "İnanmıyorum ya!" if is_tr else "Unbelievable!"

    # F) Onay / Başarı (👍, 👌, 👏, 🙌, ✅)
    elif any(e in raw_str for e in ["👍", "👌", "👏", "🙌", "✅"]):
        rate = "+4%"
        pitch = "+2Hz"
        emoji_fallback = "Tamamdır!" if is_tr else "Got it!"

    # Emojileri seslendirilecek metinden tamamen arındır
    spoken_text = EMOJI_REGEX.sub("", raw_str).strip()
    spoken_text = re.sub(r'\s+', ' ', spoken_text)
    spoken_text = re.sub(r'([!?.])\1+', r'\1', spoken_text)

    # Eğer geriye konuşulacak metin kalmadıysa (sadece emoji atılmışsa)
    if not spoken_text or not re.search(r'[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]', spoken_text):
        spoken_text = emoji_fallback

    return spoken_text, rate, pitch

# ─────────────────────────────────────────────────────────────
# 1.2 Karakter & Cinsiyet Akıllı Tespit ve Rol Haritalama
# ─────────────────────────────────────────────────────────────
MALE_KEYWORDS = [
    "baba", "babam", "peder", "dede", "dedem", "abi", "abim", "kardeşim", "kardesim",
    "koca", "kocam", "kocacım", "kocacim", "herif", "reis", "usta", "patron", "müdür",
    "boss", "hoca", "öğretmen", "ogretmen", "ev sahibi", "hacı", "haci", "amca",
    "dayı", "dayi", "enişte", "eniste", "kral", "kanka", "bro", "knk", "adam",
    "boyfriend", "husband", "father", "dad", "daddy", "pops", "grandpa", "grandfather",
    "granddad", "brother", "son", "boy", "guy", "man", "uncle", "landlord", "mr", "mister",
    "ali", "ahmet", "mehmet", "mustafa", "can", "burak", "emre", "kerem", "mert",
    "berk", "yusuf", "ömer", "omer", "fatih", "serkan", "murat", "barış", "baris",
    "cem", "kaan", "oğuz", "oguz", "eren", "tolga", "onur", "hakan", "umut", "samet",
    "volkan", "arda", "batuhan", "enes", "furkan", "gökhan", "gokhan", "halil",
    "ibrahim", "ilker", "ismail", "kemal", "koray", "levent", "mahmut", "osman",
    "ozan", "polat", "ramazan", "rıza", "riza", "selim", "sinan", "soner", "şaban",
    "tarık", "taylan", "ufuk", "uğur", "ugur", "vedat", "yasin", "yiğit", "yigit", "zafer",
    "john", "david", "mike", "alex", "chris", "james", "tom", "jack", "tariq", "zayn",
    "farhan", "bilal", "hamza", "amir", "omar", "sal", "faris", "youssef", "rayan",
    "sami", "zayd", "adam", "randy", "greg", "leo", "kevin", "malik", "kareem", "jenkins",
    "farooq"
]

FEMALE_KEYWORDS = [
    "anne", "annem", "valide", "mami", "mom", "mommy", "mother", "sister", "grandma",
    "grandmother", "abla", "ablam", "kız", "kiz", "karım", "karim", "karıcım", "karicim", "hatun",
    "hanım", "hanim", "gelin", "yenge", "teyze", "hala", "kaynana", "kayınvalide",
    "babaanne", "anneanne", "nine", "prenses", "queen", "wife", "girlfriend", "daughter",
    "girl", "woman", "lady", "aunt", "mrs", "ms", "miss", "doris", "mabel",
    "ayşe", "ayse", "fatma", "zeynep", "elif", "merve", "buse", "ceren", "sinem",
    "esra", "ebru", "eda", "derya", "gamze", "büşra", "busra", "yağmur", "yagmur",
    "aslı", "asli", "aslıhan", "aylin", "bengü", "berna", "betül", "bilge", "burcu",
    "cansu", "damla", "demet", "didem", "dilara", "dilek", "duygu", "ecem", "ece",
    "emine", "ezgi", "feride", "filiz", "fulya", "gaye", "gizem", "gözde", "gozde",
    "gül", "gul", "gülay", "gülşen", "hande", "hatice", "havva", "hazal", "hilal",
    "hülya", "ışıl", "ipek", "irem", "kübra", "kubra", "leyla", "meltem", "mine",
    "naz", "nazlı", "neslihan", "nihal", "nurgül", "özge", "ozge", "özlem", "ozlem",
    "pelin", "pınar", "pinar", "rabia", "reyhan", "rüya", "seda", "selin", "sema",
    "senem", "serap", "sevgi", "sevil", "sibel", "simge", "şebnem", "şeyma", "şevval",
    "şule", "tuğba", "tugba", "tuğçe", "tugce", "tülay", "türkan", "yasemin", "yeşim",
    "zehra", "zuhal", "sarah", "emily", "jessica", "emma", "olivia", "chloe", "sophia"
]

def detect_gender(name_or_text: str, avatar_hint: str = "", default: str = "") -> str:
    s = (name_or_text or "").lower().strip()
    
    # 1. Önce doğrudan isim ve metin token'larını kontrol et (En güvenilir kaynak!)
    tokens = re.findall(r'\b[a-zA-ZçğıöşüÇĞİÖŞÜ]+\b', s)
    for tok in tokens:
        if tok in MALE_KEYWORDS:
            return "male"
        if tok in FEMALE_KEYWORDS:
            return "female"

    for kw in MALE_KEYWORDS:
        if kw in s:
            return "male"
    for kw in FEMALE_KEYWORDS:
        if kw in s:
            return "female"

    # 2. Avatar dosya yolu / kısa ipucu (SADECE geçerli bir dosya adı ise, ASLA base64 data: url değil!)
    av = (avatar_hint or "").lower().strip()
    if av and not av.startswith("data:") and len(av) < 300:
        if any(k in av for k in ["girl", "mom", "woman", "female", "kadin", "kadın", "lady"]):
            return "female"
        if any(k in av for k in ["boy", "dad", "man", "male", "erkek", "father"]):
            return "male"

    return default or "male"

async def generate_speech_async(text: str, voice: str, output_path: str, rate: str = "+0%", pitch: str = "+0Hz"):
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)

def generate_speech(text: str, voice: str, output_path: str, rate: str = "+0%", pitch: str = "+0Hz"):
    asyncio.run(generate_speech_async(text, voice, output_path, rate=rate, pitch=pitch))


def render_crayon_job(job_data: dict, work_dir: Path) -> Path:
    channel_config = job_data.get("channel_config") or {}
    script_data = job_data.get("script_data") or job_data.get("script") or {}
    lang = (channel_config.get("language") or "en").lower()

    sys.path.insert(0, str(BASE_DIR))
    from stickman_engine.crayon_generator import generate_crayon_video, get_audio_duration

    def synthesize_crayon_speech(text: str, language: str, output_path: str) -> str:
        language_key = (language or lang).split("-", 1)[0].lower()
        voice_config = VOICE_MAP.get(language_key, VOICE_MAP["en"])
        audio_path = Path(output_path)
        for rate in ("+0%", "+10%", "+20%", "+30%", "+35%", "+40%", "+45%", "+50%", "+60%", "+70%", "+80%"):
            generate_speech(text, voice_config["narrator"], output_path, rate=rate)
            if not audio_path.is_file() or audio_path.stat().st_size < 1000:
                raise RuntimeError(f"Edge TTS sahne sesini oluşturamadı: {audio_path.name}")
            if 0 < get_audio_duration(str(audio_path)) <= 4.95:
                return str(audio_path)
        raise RuntimeError(
            f"Crayon shot TTS sesi artan konuşma hızlarına rağmen 5 saniyeye sığmadı: "
            f"{audio_path.name}"
        )

    # Otomatik Konuya Özel Görsel Araştırması & Üretimi
    try:
        from aviation_research_engine import AviationResearchEngine
        engine = AviationResearchEngine()
        cid = channel_config.get("channel_id") or "tacticallcrayon"
        engine.research_material_dir(work_dir, channel_id=cid)
        mat_json = work_dir / "material.json"
        if mat_json.is_file():
            with open(mat_json, "r", encoding="utf-8") as f_mat:
                updated_mat = json.load(f_mat)
            if updated_mat.get("images"):
                job_data["custom_images"] = updated_mat["images"]
            if updated_mat.get("script"):
                script_data = updated_mat["script"]
    except Exception as e_res:
        print(f"[WORKER-CRAYON] Otomatik konu görsel araştırması uyarısı: {e_res}")

    result = generate_crayon_video(
        channel_config=channel_config,
        script_data=script_data,
        work_dir=work_dir,
        output_dir=str(OUTPUT_BASE),
        edit_options=channel_config.get("edit_options") or {},
        custom_images=job_data.get("custom_images") or {},
        lang=lang,
        speech_generator=synthesize_crayon_speech,
    )
    if result.get("thumbnail_path"):
        job_data["thumbnail_path"] = result["thumbnail_path"]
    video_path = Path(result["video_path"])
    if not video_path.is_file():
        raise RuntimeError("Crayon render tamamlandı ancak çıktı videosu bulunamadı.")
    return video_path


# ─────────────────────────────────────────────────────────────
# 2. Ses Süresi Ölçümü (FFprobe)
# ─────────────────────────────────────────────────────────────
def get_media_duration(file_path: str) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 3.0


# ─────────────────────────────────────────────────────────────
# 3. WhatsApp Shorts Render Motoru (Remotion)
def detect_contact_name_from_context(script_obj: dict, lang_code: str = "tr") -> str:
    c_name = script_obj.get("contact_name")
    if c_name and c_name.strip() and c_name.strip().lower() not in ["aşkım", "askim", "honey"]:
        return c_name.strip()
    title_topic = (str(script_obj.get("title", "")) + " " + str(script_obj.get("topic", "")) + " " + str(script_obj.get("description", ""))).lower()
    if any(w in title_topic for w in ["usta", "sanayi", "tamir", "çırak", "cirak"]):
        return "Şevket Usta 🔧"
    if any(w in title_topic for w in ["spor salonu", "fitness", "fitlife", "üyelik"]):
        return "FitLife Müşteri Hizmetleri 🏋️"
    if any(w in title_topic for w in ["sınav", "hoca", "okul", "kanka", "öğrenci", "arkadaş"]):
        return "Berk (Kanka) 📚"
    if any(w in title_topic for w in ["baba", "peder", "dad", "father"]):
        return "Babam 👑" if lang_code == "tr" else "Dad 👑"
    if any(w in title_topic for w in ["anne", "valide", "mom", "mother"]):
        return "Annem ❤️" if lang_code == "tr" else "Mom ❤️"
    if any(w in title_topic for w in ["ev sahibi", "kira", "apartman", "komşu", "yönetici"]):
        return "Ev Sahibi Halil Bey 🏢"
    if any(w in title_topic for w in ["kaptan", "halı saha", "futbol"]):
        return "Kaptan Burak ⚽"
    if any(w in title_topic for w in ["patron", "müdür", "şef", "iş yeri", "ofis", "boss"]):
        return "Patron 💼"
    return "Kanka 💬" if lang_code == "tr" else "Friend 💬"


# ─────────────────────────────────────────────────────────────
def render_whatsapp_job(job_data: dict, work_dir: Path) -> Path:
    channel_id = job_data.get("channel_id", "yazanyazana")
    lang = (job_data.get("channel_config", {}).get("language") or "tr").lower()
    raw_script = job_data.get("script_data") or job_data.get("script") or {}

    # Senaryoyu hedef kanalın diline otomatik yerelleştir
    script = ensure_localized_script(raw_script, lang)
    messages = script.get("messages") or script.get("scenes") or script.get("dialogue") or script.get("conversations") or []

    # Eğer messages yoksa veya sadece narrative scenes varsa otomatik diyaloğa dönüştür
    if (not script.get("messages") or len(script.get("messages", [])) == 0) and script.get("scenes"):
        scenes = script.get("scenes") or []
        converted_messages = []
        for s_idx, sc in enumerate(scenes):
            txt = sc.get("narration") or sc.get("text") or ""
            if not txt:
                continue
            quotes = re.findall(r"['\"]([^'\"]{4,})['\"]", txt)
            if quotes:
                for q_idx, q in enumerate(quotes):
                    sender = "user" if (s_idx + q_idx) % 2 == 0 else "contact"
                    converted_messages.append({"sender": sender, "text": q.strip()})
            else:
                sender = "user" if s_idx % 2 == 0 else "contact"
                converted_messages.append({"sender": sender, "text": txt.strip()})
        if converted_messages:
            messages = converted_messages

    if not messages:
        raise ValueError("Senaryoda işlenebilecek WhatsApp mesajı veya sahnesi (messages/scenes) bulunamadı.")

    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    voice_cfg = VOICE_MAP.get(lang, VOICE_MAP["tr"])

    # ── Akıllı Karakter Cinsiyet ve Rol Tespiti ──
    contact_name = detect_contact_name_from_context(script, lang)
    custom_images = job_data.get("custom_images") or {}
    avatar_raw = str(custom_images.get("0") or custom_images.get("avatar") or "")

    # 1. Karşı tarafın (contact) cinsiyeti:
    explicit_c_gender = (
        script.get("contact_gender")
        or script.get("contact_avatar_gender")
        or script.get("contact_role_type")
        or script.get("cinsiyet")
        or job_data.get("contact_gender")
        or job_data.get("contact_avatar_gender")
    )
    if explicit_c_gender:
        c_str = str(explicit_c_gender).lower()
        if any(w in c_str for w in ["male", "erkek", "baba", "dad", "father", "dede", "boy", "man", "boss"]):
            contact_gender = "male"
        elif any(w in c_str for w in ["female", "kadin", "kadın", "anne", "mom", "mother", "girl", "woman"]):
            contact_gender = "female"
        else:
            contact_gender = detect_gender(contact_name, avatar_raw, default="male" if any(w in contact_name.lower() for w in MALE_KEYWORDS) else "female")
    else:
        detected_c = detect_gender(contact_name, avatar_raw, default="")
        if detected_c:
            contact_gender = detected_c
        else:
            dialogue_text = " ".join([str(m.get("text", "")) for m in messages]).lower()
            if any(w in dialogue_text for w in ["kocacım", "kocam", "herif", "babacım", "abicim", "erkek arkadaşım", "my dad", "father", "daddy", "hubby", "bro"]):
                contact_gender = "male"
            elif any(w in dialogue_text for w in ["karıcım", "karım", "kızım", "hatun", "güzelim", "prensesim", "my mom", "mother", "mommy", "wifey", "sis"]):
                contact_gender = "female"
            else:
                contact_gender = "male" if any(w in contact_name.lower() for w in MALE_KEYWORDS) else "female"

    # 2. Kullanıcının (user / ben) cinsiyeti:
    explicit_u_gender = (
        script.get("user_gender")
        or script.get("user_avatar_gender")
        or script.get("user_role_type")
        or job_data.get("user_gender")
    )
    if explicit_u_gender:
        u_str = str(explicit_u_gender).lower()
        if any(w in u_str for w in ["male", "erkek", "troll_erkek", "yorgun_erkek", "kanka_erkek", "boy", "man"]):
            user_gender = "male"
        elif any(w in u_str for w in ["female", "kadin", "kadın", "sakin_kadin", "kanka_kadin", "girl", "woman"]):
            user_gender = "female"
        else:
            user_gender = "male"
    else:
        if contact_gender == "male" and any(w in contact_name.lower() for w in ["kocam", "husband"]):
            user_gender = "female"
        elif contact_gender == "female" and any(w in contact_name.lower() for w in ["karım", "wife"]):
            user_gender = "male"
        else:
            user_gender = "male"

    print(f"[Worker] WhatsApp Karakter Rolleri: Kullanıcı={user_gender}, Karşı Taraf={contact_name} ({contact_gender})")

    fps = 30
    remotion_messages = []
    # Balon ekranda görünmeden önce 0.4 sn (12 kare) hazırlık payı
    current_time_sec = 0.4
    audio_timeline = []

    pub_media = REMOTION_DIR / "public" / "media"
    pub_media.mkdir(parents=True, exist_ok=True)

    # Grup tespiti ve benzersiz gelen gönderenler (incoming senders)
    incoming_senders = []
    for m in messages:
        snd = str(m.get("sender") or m.get("from") or m.get("speaker") or "contact").lower()
        snd_name = str(m.get("sender_name") or m.get("name") or m.get("kisi") or "").strip()
        if not snd_name and snd and snd not in ["user", "me", "ben", "outgoing", "contact", "other", "bot"]:
            snd_name = str(m.get("sender") or m.get("from") or "").strip()
        is_m = ("me" in snd or "user" in snd or "ben" in snd or "sen" in snd_name.lower() or "you" in snd_name.lower())
        if not is_m and snd_name and snd_name not in incoming_senders:
            incoming_senders.append(snd_name)

    if not incoming_senders and script.get("group_participants"):
        gp_str = str(script.get("group_participants"))
        parts = [p.strip() for p in re.split(r'[,;]+', gp_str) if p.strip()]
        for p in parts:
            if p.lower() not in ["sen", "me", "you", "ben", "user"] and p not in incoming_senders:
                incoming_senders.append(p)

    is_group = bool(
        script.get("is_group", False) or
        job_data.get("is_group", False) or
        script.get("isGroup", False) or
        script.get("group_name") or
        len(incoming_senders) > 1 or
        any(t in str(script.get("contact_name", "") + " " + script.get("title", "")).lower() for t in [
            "apartman", "sakinleri", "halı saha", "hali saha", "futbol", "takım", "fc ", "united", 
            "team", "squad", "meclisi", "aile", "family", "roommates", "arkadaşlar", "grup", "group", 
            "tayfa", "ofis", "şirket", "sohbeti", "official", "league", "bina", "site ", "yönetim"
        ])
    )

    def resolve_and_copy_avatar(raw_img_val, target_filename):
        if not raw_img_val or not isinstance(raw_img_val, str):
            return ""
        try:
            if raw_img_val.startswith("data:") or len(raw_img_val) > 200:
                b64_str = raw_img_val.split(",", 1)[1] if "," in raw_img_val else raw_img_val
                img_data = base64.b64decode(b64_str)
                out_path = pub_media / target_filename
                out_path.write_bytes(img_data)
                return f"/media/{target_filename}"
            elif Path(raw_img_val).exists():
                out_path = pub_media / target_filename
                shutil.copy2(raw_img_val, str(out_path))
                return f"/media/{target_filename}"
        except Exception as e:
            print(f"[Worker] Avatar aktarma uyarısı ({target_filename}): {e}")
        return raw_img_val if raw_img_val.startswith("data:") else ""

    custom_images = job_data.get("custom_images") or {}
    participant_avatars = {}
    if is_group:
        male_fallbacks = ["boy.jpg", "dad.jpg"]
        female_fallbacks = ["girl.jpg", "mom.jpg"]
        m_fallback_idx = 0
        f_fallback_idx = 0

        for p_idx, s_name in enumerate(incoming_senders):
            s_clean = re.sub(r'[^\w\s]', '', s_name).strip().lower()
            s_first = s_clean.split()[0] if s_clean else ""

            p_img_raw = (
                custom_images.get(s_name) or
                custom_images.get(s_name.lower()) or
                custom_images.get(s_clean) or
                custom_images.get(s_first) or
                custom_images.get(str(p_idx + 1)) or
                custom_images.get(f"p_{p_idx + 1}") or
                custom_images.get(f"participant_{p_idx + 1}")
            )
            p_rel = ""
            if p_img_raw:
                p_rel = resolve_and_copy_avatar(p_img_raw, f"avatar_{work_dir.name}_p_{p_idx+1}.png")
            if not p_rel:
                s_gender = detect_gender(s_name, "")
                s_name_lower = s_name.lower()
                if s_gender == "male":
                    if any(w in s_name_lower for w in ["baba", "patron", "usta", "ev sahibi", "hacı", "müdür", "dede", "amca", "dad", "father", "mr", "boss", "grandpa", "farooq", "pops", "landlord", "coach"]):
                        p_fallback = "dad.jpg"
                    else:
                        p_fallback = male_fallbacks[m_fallback_idx % len(male_fallbacks)]
                        m_fallback_idx += 1
                else:
                    if any(w in s_name_lower for w in ["anne", "valide", "teyze", "kaynana", "nine", "mom", "mother", "grandma", "aunt", "mrs"]):
                        p_fallback = "mom.jpg"
                    else:
                        p_fallback = female_fallbacks[f_fallback_idx % len(female_fallbacks)]
                        f_fallback_idx += 1
                if (pub_media / p_fallback).exists():
                    p_rel = f"/media/{p_fallback}"

            participant_avatars[s_name] = p_rel
            participant_avatars[s_name.lower()] = p_rel
            if s_clean:
                participant_avatars[s_clean] = p_rel
            if s_first:
                participant_avatars[s_first] = p_rel

    # Grup ana resmi veya birebir profil resmi:
    rel_avatar = ""
    avatar_raw = custom_images.get("0") or custom_images.get("group") or custom_images.get("avatar")
    if avatar_raw:
        rel_avatar = resolve_and_copy_avatar(avatar_raw, f"avatar_{work_dir.name}_main.png")

    if not rel_avatar:
        if is_group:
            # Grup profil resmi şahıs fotoğrafı değil; tematik amblem/obje olmalı
            thematic_wallpapers = ["doodle_beige.jpg", "urban_wall.jpg", "cozy_wood.jpg", "botanical_shadow.jpg"]
            for tw in thematic_wallpapers:
                if (pub_media / tw).exists():
                    rel_avatar = f"/media/{tw}"
                    break
        else:
            c_name_lower = contact_name.lower()
            if contact_gender == "male":
                if any(w in c_name_lower for w in ["baba", "patron", "usta", "ev sahibi", "hacı", "müdür", "dede", "amca", "dad", "father", "mr", "boss", "grandpa", "farooq", "pops", "landlord"]):
                    fallback_av = "dad.jpg"
                else:
                    fallback_av = "boy.jpg"
            else:
                if any(w in c_name_lower for w in ["anne", "valide", "teyze", "kaynana", "nine", "mom", "mother", "grandma", "aunt", "mrs"]):
                    fallback_av = "mom.jpg"
                else:
                    fallback_av = "girl.jpg"
            if (pub_media / fallback_av).exists():
                rel_avatar = f"/media/{fallback_av}"

    print(f"[Worker] WhatsApp TTS üretiliyor ({len(messages)} mesaj, Grup: {is_group})...")
    for idx, msg in enumerate(messages):
        sender = str(msg.get("sender") or msg.get("from") or msg.get("speaker") or "me").lower()
        raw_text = str(msg.get("text") or msg.get("content") or msg.get("narration") or msg.get("message") or "")
        sender_name = str(msg.get("sender_name") or msg.get("name") or msg.get("sender") or ("Sen" if ("me" in sender or "user" in sender or "ben" in sender) else contact_name))

        is_me = ("me" in sender or "user" in sender or "ben" in sender or "sen" in sender_name.lower() or "you" in sender_name.lower())

        # Bu spesifik mesajı atan kişinin adı veya rolü açıkça erkek/kadın mı?
        # Örneğin: sender_name = "Dad" veya "Babam" ise ASLA kadın sesi verilmemelidir!
        msg_explicit_gender = msg.get("gender") or msg.get("sender_gender")
        if msg_explicit_gender:
            sender_gender = "female" if str(msg_explicit_gender).lower() in ["female", "kadin", "kadın"] else "male"
        else:
            detected_spk = detect_gender(sender_name, default="")
            if not detected_spk and sender:
                detected_spk = detect_gender(sender, default="")
            if detected_spk in ("male", "female"):
                sender_gender = detected_spk
            else:
                sender_gender = user_gender if is_me else contact_gender

        other_gender = contact_gender if is_me else user_gender

        # Ses motoru ve baz prosody:
        if sender_gender == "male":
            if lang == "en":
                # İngilizce diyaloglarda karakter kimliği ve yaşa göre gerçekçi Edge TTS sesleri:
                is_dad_or_elder = any(w in (sender_name + " " + contact_name).lower() for w in ["dad", "father", "mr", "boss", "grandpa", "uncle", "landlord", "farooq", "pops"])
                if is_dad_or_elder and not is_me:
                    voice = "en-US-RogerNeural"       # Tok, otoriter baba/patron sesi
                    base_pitch_val = -4
                    base_rate_val = -3
                else:
                    voice = "en-US-GuyNeural"         # Genç, dinamik erkek sesi
                    base_pitch_val = 1
                    base_rate_val = 4
            else:
                voice = voice_cfg["male"]
                if other_gender == "male":
                    if is_me:
                        base_pitch_val = 1
                        base_rate_val = 4
                    else:
                        if any(w in (sender_name + " " + contact_name).lower() for w in ["baba", "patron", "usta", "ev sahibi", "hacı", "müdür", "dede", "amca"]):
                            base_pitch_val = -7  # Daha tok, otoriter erkek sesi
                            base_rate_val = -3
                        else:
                            base_pitch_val = 5   # Enerjik kanka/arkadaş tonu
                            base_rate_val = 6
                else:
                    base_pitch_val = 0
                    base_rate_val = 2
        else:  # female
            if lang == "en":
                is_mom_or_elder = any(w in (sender_name + " " + contact_name).lower() for w in ["mom", "mother", "mrs", "grandma", "aunt", "lady"])
                if is_mom_or_elder and not is_me:
                    voice = "en-US-MichelleNeural"    # Olgun, şefkatli anne sesi
                    base_pitch_val = -4
                    base_rate_val = -2
                else:
                    voice = "en-US-JennyNeural"       # Genç kadın sesi
                    base_pitch_val = 2
                    base_rate_val = 3
            else:
                voice = voice_cfg["female"]
                if other_gender == "female":
                    if is_me:
                        base_pitch_val = 0
                        base_rate_val = 3
                    else:
                        if any(w in (sender_name + " " + contact_name).lower() for w in ["anne", "valide", "teyze", "kaynana", "nine"]):
                            base_pitch_val = -5
                            base_rate_val = -3
                        else:
                            base_pitch_val = 5
                            base_rate_val = 5
                else:
                    base_pitch_val = 0
                    base_rate_val = 2

        # Emojileri temizle ve duygu tonlamasını al
        spoken_text, emo_rate, emo_pitch = prepare_speech_text_and_tone(raw_text, lang)

        # Baz karakter tonu ile emoji duygu tonunu harmanla
        emo_pitch_int = int(re.sub(r'[^0-9\-+]', '', emo_pitch) or 0)
        emo_rate_int = int(re.sub(r'[^0-9\-+]', '', emo_rate) or 0)
        final_pitch = f"{base_pitch_val + emo_pitch_int:+d}Hz"
        final_rate = f"{base_rate_val + emo_rate_int:+d}%"

        msg_audio = audio_dir / f"msg_{idx:03d}.mp3"
        idx_key = str(idx)
        used_custom = False
        custom_audios = job_data.get("custom_audios") or {}
        if custom_audios and (idx_key in custom_audios or f"msg_{idx}" in custom_audios):
            try:
                raw_aud = custom_audios.get(idx_key) or custom_audios.get(f"msg_{idx}")
                if "," in raw_aud:
                    raw_aud = raw_aud.split(",", 1)[1]
                aud_bytes = base64.b64decode(raw_aud)
                msg_audio.write_bytes(aud_bytes)
                used_custom = True
                print(f"[Worker-WhatsApp] 🎙️ Mesaj {idx} için stüdyo kalitesinde klon ses kullanıldı.")
            except Exception as e_ca:
                print(f"[Worker-WhatsApp] ⚠️ Özel ses çözme uyarısı: {e_ca}")

        if not used_custom:
            generate_speech(spoken_text, voice, str(msg_audio), rate=final_rate, pitch=final_pitch)

        dur = get_media_duration(str(msg_audio))

        # Kare bazında kesin senkronizasyon (Zero drift):
        # 1. Balon ekrana start_frame anında gelir (pop SFX çalar)
        start_frame = int(round(current_time_sec * fps))
        bubble_sec = start_frame / float(fps)

        # 2. Ses, balonun ekranda belirmesiyle eşzamanlı / mikro 50ms sonra başlar
        # Böylece ses kesinlikle mesaj balonu görünmeden ÖNCE başlamaz!
        speech_start_sec = bubble_sec + 0.05
        delay_ms = int(round(speech_start_sec * 1000))

        dur_frames = max(fps, int(round((dur + 0.05) * fps)))
        end_frame = start_frame + dur_frames

        audio_timeline.append({
            "path": str(msg_audio),
            "delay_ms": delay_ms,
            "dur": dur,
        })

        if is_group:
            s_clean = re.sub(r'[^\w\s]', '', sender_name).strip().lower()
            s_first = s_clean.split()[0] if s_clean else ""
            sender_av = (
                participant_avatars.get(sender_name) or
                participant_avatars.get(sender_name.lower()) or
                participant_avatars.get(s_clean) or
                participant_avatars.get(s_first) or
                ""
            )
        else:
            sender_av = rel_avatar
        remotion_messages.append({
            "id": f"msg_{idx}",
            "sender": "user" if is_me else "contact",
            "senderName": sender_name,
            "senderAvatar": sender_av,
            "text": raw_text,  # Görsel ekranda orijinal emojili metin korunur!
            "time": time.strftime("%H:%M"),
            "startFrame": start_frame,
            "endFrame": end_frame,
            "durationInFrames": dur_frames,
            "audioDuration": dur,
        })

        # Sonraki mesaja geçiş payı: replikler arası 0.25sn doğal nefes/okuma payı
        pause_after = 0.25 if idx < len(messages) - 1 else 1.2
        current_time_sec = speech_start_sec + dur + pause_after

    # Master ses dosyasını FFmpeg adelay + amix ile hassas milisaniye senkronizasyonunda miksle
    master_audio = work_dir / "master_audio.mp3"
    input_args = []
    filter_parts = []
    mix_labels = []

    for idx, item in enumerate(audio_timeline):
        input_args.extend(["-i", item["path"]])
        filter_parts.append(f"[{idx}:a]adelay={item['delay_ms']}:all=1,volume=1.2[a{idx}]")
        mix_labels.append(f"[a{idx}]")

    num_inputs = len(audio_timeline)
    filter_complex = (
        ";".join(filter_parts) +
        f";{''.join(mix_labels)}amix=inputs={num_inputs}:duration=longest:dropout_transition=0:normalize=0[aout]"
    )

    total_duration = max(current_time_sec, (audio_timeline[-1]["delay_ms"] / 1000.0) + audio_timeline[-1]["dur"] + 1.2)
    duration_frames = int(round(total_duration * fps))

    cmd_mix = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-ac", "2",
        "-ar", "44100",
        "-t", f"{total_duration:.2f}",
        str(master_audio)
    ]
    subprocess.run(cmd_mix, capture_output=True, check=True)

    actual_duration = get_media_duration(str(master_audio))
    duration_frames = max(duration_frames, int(actual_duration * fps) + 15)

    # Remotion public media klasörüne sesi kopyala
    audio_symlink_name = f"wa_audio_{work_dir.name}.mp3"
    shutil.copy2(str(master_audio), str(pub_media / audio_symlink_name))

    # ── 1. DİNAMİK SOHBET DUVAR KAĞIDI (WALLPAPER ROTATION) ──
    wallpaper_pool = [
        "doodle_beige.jpg",
        "floral_pastel.jpg",
        "botanical_shadow.jpg",
        "pastel_gradient.jpg",
        "cozy_wood.jpg",
        "urban_wall.jpg",
        "dark_slate.jpg",
    ]
    valid_wallpapers = [w for w in wallpaper_pool if (pub_media / w).exists()]
    if not valid_wallpapers:
        valid_wallpapers = ["floral_pastel.jpg"]

    # İçerik korpusu (metin anahtar kelimeleri)
    text_corpus = (
        f"{contact_name} {script.get('title', '')} {script.get('group_name', '')} " +
        " ".join([str(m.get("text", "")) for m in messages[:5]])
    ).lower()

    selected_wp = None
    if any(k in text_corpus for k in ["gece", "karanlık", "korku", "gizem", "borç", "kavga", "apartman", "yönetici", "polis", "patron", "sanayi", "oto", "tamir"]):
        for dark_cand in ["dark_slate.jpg", "urban_wall.jpg", "cozy_wood.jpg"]:
            if dark_cand in valid_wallpapers:
                selected_wp = dark_cand
                break
    elif any(k in text_corpus for k in ["aşkım", "sevgili", "çiçek", "romantik", "evlilik", "prenses", "canım", "kız"]):
        for soft_cand in ["floral_pastel.jpg", "pastel_gradient.jpg", "doodle_beige.jpg"]:
            if soft_cand in valid_wallpapers:
                selected_wp = soft_cand
                break
    elif any(k in text_corpus for k in ["futbol", "maç", "halı saha", "arkadaş", "kanka", "dost"]):
        for modern_cand in ["urban_wall.jpg", "doodle_beige.jpg", "botanical_shadow.jpg"]:
            if modern_cand in valid_wallpapers:
                selected_wp = modern_cand
                break

    if not selected_wp:
        # Her video için benzersiz hash ile deterministik rotasyon (her videoda farklı arka plan)
        wp_seed = abs(hash(f"{channel_id}_{work_dir.name}_{contact_name}_{len(messages)}"))
        selected_wp = valid_wallpapers[wp_seed % len(valid_wallpapers)]

    req_wp = script.get("wallpaper") or script.get("wallpaperPath")
    if req_wp and (pub_media / Path(req_wp).name).exists():
        selected_wp = Path(req_wp).name

    wallpaper_file = selected_wp

    # ── 2. ABSÜRT & VİRAL KOMEDİ FON MÜZİĞİ MOTORU (BGM ENGINE) ──
    bgm_pool = [
        "monkeys_spinning.mp3",
        "sneaky_snitch.mp3",
        "fluffing_duck.mp3",
        "scheming_weasel.mp3",
        "comedy_upbeat.mp3",
    ]
    valid_bgms = [b for b in bgm_pool if (pub_media / b).exists()]

    req_bgm = str(script.get("bgm_track") or script.get("bgm") or script.get("bgmPath") or "").lower()
    selected_bgm = None

    if "quirky" in req_bgm or "troll" in req_bgm or "sneaky" in req_bgm:
        selected_bgm = "sneaky_snitch.mp3"
    elif "monkey" in req_bgm or "viral" in req_bgm or "bounce" in req_bgm or "absurd" in req_bgm or "absürt" in req_bgm:
        selected_bgm = "monkeys_spinning.mp3"
    elif "duck" in req_bgm or "silly" in req_bgm:
        selected_bgm = "fluffing_duck.mp3"
    elif "scheme" in req_bgm or "weasel" in req_bgm or "cunning" in req_bgm:
        selected_bgm = "scheming_weasel.mp3"
    elif "upbeat" in req_bgm or "comedy" in req_bgm:
        selected_bgm = "comedy_upbeat.mp3"
    elif "chill" in req_bgm or "lofi" in req_bgm:
        selected_bgm = "lofi_chill.mp3"

    if not selected_bgm or (selected_bgm not in valid_bgms and not (pub_media / selected_bgm).exists()):
        # Absürt / viral komedi temalarına göre akıllı eşleşme
        if any(k in text_corpus for k in ["yalan", "yakala", "gizli", "ifşa", "gizlice", "troll", "şaka", "kaç", "baskın", "polis"]):
            selected_bgm = "sneaky_snitch.mp3"
        elif any(k in text_corpus for k in ["robot", "süpürge", "saçma", "deli", "çıldırdı", "komik", "ahahaha", "salak", "mal", "halı"]):
            selected_bgm = "monkeys_spinning.mp3"
        elif any(k in text_corpus for k in ["para", "kira", "zam", "ev sahibi", "borç", "avukat", "icra", "yönetici", "hesap"]):
            selected_bgm = "scheming_weasel.mp3"
        elif any(k in text_corpus for k in ["aşkım", "bebeğim", "yemek", "kavga", "tatlı", "tripler"]):
            selected_bgm = "fluffing_duck.mp3"
        else:
            # Hash seed ile videolar arası rotasyon (her videoda taze absürt müzik)
            bgm_seed = abs(hash(f"{work_dir.name}_{contact_name}_{len(messages)}"))
            if valid_bgms:
                selected_bgm = valid_bgms[bgm_seed % len(valid_bgms)]
            else:
                selected_bgm = "monkeys_spinning.mp3"

    rel_bgm_path = f"media/{selected_bgm}" if selected_bgm and (pub_media / selected_bgm).exists() else ""
    # Arka plan müziği seslendirmeyi örtmeyecek dengeli ve temiz bir seviyede (0.08) tutulur:
    bgm_volume_val = 0.08
    print(f"[Worker] WhatsApp Atmosfer: Wallpaper='{wallpaper_file}', BGM='{selected_bgm}' (Vol={bgm_volume_val})")

    # Grup katılımcıları ve başlığı
    group_parts_str = script.get("group_participants") or ""
    if not group_parts_str and is_group:
        all_participants = incoming_senders + (["Sen"] if lang == "tr" else ["You"])
        group_parts_str = ", ".join(all_participants)

    group_title = script.get("group_name") or script.get("contact_name") or script.get("title") or ("Grup Sohbeti" if lang == "tr" else "Group Chat")

    # ASMR Arka Plan Videosu Çözümle
    bg_video_rel = resolve_asmr_background_video(pub_media, work_dir, actual_duration)

    # Remotion Props hazırla (Klon ses giydirmesinde halüsinasyonu önlemek için saf sesle render edilir):
    job_data["selected_bgm"] = selected_bgm or "monkeys_spinning.mp3"
    props = {
        "contactName": group_title if is_group else contact_name,
        "contactAvatar": rel_avatar,
        "statusText": ("çevrimiçi" if lang == "tr" else "online") if not is_group else (group_parts_str or "Grup"),
        "audioPath": f"media/{audio_symlink_name}",
        "bgmPath": "",
        "bgmVolume": 0.0,
        "bgVideoPath": bg_video_rel,
        "layout": "dublaj_style",
        "theme": "light",
        "watermarkText": channel_id,
        "instagramUsername": "",
        "wallpaperPath": f"media/{wallpaper_file}",
        "isGroup": is_group,
        "groupParticipants": group_parts_str,
        "language": lang,
        "messages": remotion_messages,
        "fps": 30,
        "durationInFrames": duration_frames,
    }

    props_file = work_dir / "remotion_props.json"
    props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2))

    output_video = work_dir / "final_video.mp4"
    print(f"[Worker] Remotion render başlatılıyor ({duration_frames} kare, {actual_duration:.1f}s)...")

    render_cmd = [
        "npx", "remotion", "render",
        "src/index.ts",
        "WhatsAppChat",
        str(output_video),
        f"--props={str(props_file)}",
        f"--public-dir={str(pub_media.parent)}",
        "--concurrency=2",
        "--overwrite"
    ]
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "2"
    proc = subprocess.run(render_cmd, cwd=str(REMOTION_DIR), capture_output=True, text=True, env=env)

    if proc.returncode != 0 or not output_video.exists():
        raise RuntimeError(f"Remotion render hatası:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")

    return output_video


# ─────────────────────────────────────────────────────────────
# 4. Reddit Shorts Render Motoru (Remotion RedditStory)
# ─────────────────────────────────────────────────────────────
def render_reddit_job(job_data: dict, work_dir: Path) -> Path:
    channel_id = job_data.get("channel_id", "reddit")
    lang = (job_data.get("channel_config", {}).get("language") or "tr").lower()
    raw_script = job_data.get("script_data") or job_data.get("script") or {}

    # Senaryoyu hedef kanalın diline otomatik yerelleştir (İngilizce ise tüm başlık, soru ve sahneleri İngilizceye çevirir)
    script = ensure_localized_script(raw_script, lang)

    question = script.get("question") or script.get("title") or "Reddit Story"
    subreddit = script.get("subreddit") or (f"r/{job_data.get('channel_config', {}).get('name', 'AskReddit').replace(' ', '')}")
    author = script.get("author") or "u/StoryTeller99"
    upvotes = str(script.get("upvotes") or "42.5k")

    scenes = script.get("scenes") or []
    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    voice_cfg = VOICE_MAP.get(lang, VOICE_MAP["tr"])

    fps = 30
    captions = []
    current_time_sec = 0.0
    audio_parts = []

    narrations = []
    if scenes and isinstance(scenes, list):
        for s in scenes:
            txt = s.get("narration") or s.get("text") or ""
            if txt:
                narrations.append(txt)
    if not narrations:
        body = script.get("narration") or script.get("story") or script.get("body") or question
        narrations = [p.strip() for p in re.split(r'(?<=[.!?])\s+', body) if p.strip()]

    if not narrations:
        narrations = [question]

    custom_audios = job_data.get("custom_audios") or {}
    for idx, raw_txt in enumerate(narrations):
        spoken_text, rate, pitch = prepare_speech_text_and_tone(raw_txt, lang)
        part_file = audio_dir / f"scene_{idx:03d}.mp3"
        idx_key = str(idx)
        used_custom = False
        if custom_audios and (idx_key in custom_audios or f"scene_{idx}" in custom_audios):
            try:
                raw_aud = custom_audios.get(idx_key) or custom_audios.get(f"scene_{idx}")
                if "," in raw_aud:
                    raw_aud = raw_aud.split(",", 1)[1]
                aud_bytes = base64.b64decode(raw_aud)

                # Geçici dosya üzerinden format tespiti ve standart 44.1kHz MP3'e dönüştürme (WAV/PCM uyumsuzluğunu önler)
                tmp_raw = audio_dir / f"scene_{idx:03d}_raw.bin"
                tmp_raw.write_bytes(aud_bytes)

                conv_cmd = [
                    "ffmpeg", "-y", "-i", str(tmp_raw),
                    "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
                    str(part_file)
                ]
                conv_res = subprocess.run(conv_cmd, capture_output=True)
                try:
                    tmp_raw.unlink(missing_ok=True)
                except Exception:
                    pass

                if conv_res.returncode == 0 and part_file.exists() and part_file.stat().st_size > 500:
                    used_custom = True
                    print(f"[Worker-Reddit] 🎙️ Sahne {idx} için stüdyo kalitesinde klon ses başarıyla MP3'e dönüştürüldü ({part_file.stat().st_size} B).")
                else:
                    print(f"[Worker-Reddit] ⚠️ Özel ses dönüştürme uyarısı, TTS'e geçiliyor: {conv_res.stderr.decode('utf-8', 'ignore')[:150]}")
            except Exception as e_ca:
                print(f"[Worker-Reddit] ⚠️ Özel ses çözme uyarısı: {e_ca}")

        if not used_custom:
            generate_speech(spoken_text, voice_cfg["narrator"], str(part_file), rate=rate, pitch=pitch)
            # Edge-TTS varsayılan olarak 24kHz üretir; diğer seslerle kusursuz birleşmesi için 44.1kHz'e yükselt
            try:
                std_temp = audio_dir / f"scene_{idx:03d}_std.mp3"
                std_cmd = [
                    "ffmpeg", "-y", "-i", str(part_file),
                    "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
                    str(std_temp)
                ]
                std_proc = subprocess.run(std_cmd, capture_output=True)
                if std_proc.returncode == 0 and std_temp.exists() and std_temp.stat().st_size > 500:
                    std_temp.replace(part_file)
            except Exception as e_std:
                print(f"[Worker-Reddit] TTS standardizasyon uyarısı: {e_std}")

        dur = get_media_duration(str(part_file))
        if dur <= 0.1:
            dur = 1.0

        start_f = int(current_time_sec * fps)
        dur_f = max(10, int(dur * fps))
        captions.append({
            "text": raw_txt,
            "startFrame": start_f,
            "durationInFrames": dur_f,
        })
        audio_parts.append(str(part_file))
        current_time_sec += dur + 0.2

    # FFmpeg concat ile sesleri birleştir (Daima libmp3lame ile re-encode et, asla -c copy kullanma!)
    concat_list = work_dir / "concat_audio.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in audio_parts:
            f.write(f"file '{p}'\n")

    combined_audio = work_dir / "reddit_combined_audio.mp3"
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
        str(combined_audio)
    ]
    concat_res = subprocess.run(concat_cmd, capture_output=True, text=True)

    if concat_res.returncode != 0 or not combined_audio.exists() or combined_audio.stat().st_size < 1000:
        print(f"[Worker-Reddit] Concat demuxer uyarısı ({concat_res.stderr[:200] if concat_res.stderr else 'empty'}), filter_complex deneniyor...")
        inputs = []
        filter_str = ""
        for i, p in enumerate(audio_parts):
            inputs.extend(["-i", p])
            filter_str += f"[{i}:a]"
        filter_str += f"concat=n={len(audio_parts)}:v=0:a=1[aout]"
        fb_cmd = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", filter_str,
            "-map", "[aout]",
            "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
            str(combined_audio)
        ]
        subprocess.run(fb_cmd, capture_output=True, text=True, check=True)

    actual_duration = get_media_duration(str(combined_audio))
    total_frames = int(actual_duration * fps) + int(0.5 * fps)

    pub_media = REMOTION_DIR / "public" / "media"
    pub_media.mkdir(parents=True, exist_ok=True)

    rel_audio_name = f"reddit_audio_{job_data.get('job_id', int(time.time()))}.mp3"
    shutil.copy2(str(combined_audio), str(pub_media / rel_audio_name))

    bgm_candidates = [
        "reddit_official_bgm.mp3",
        "lofi_chill.mp3",
        "lofi_enthusiast.mp3",
        "comedy_upbeat.mp3",
        "monkeys_spinning.mp3"
    ]
    selected_bgm = ""
    for bgm_cand in bgm_candidates:
        if (pub_media / bgm_cand).exists():
            selected_bgm = f"media/{bgm_cand}"
            break
        elif (BASE_DIR / "assets" / "music" / bgm_cand).exists():
            shutil.copy2(str(BASE_DIR / "assets" / "music" / bgm_cand), str(pub_media / bgm_cand))
            selected_bgm = f"media/{bgm_cand}"
            break

    # İlk 3 saniye kuralı: Reddit soru kartı 2.5 - 3.0 saniye (75-90 kare) ekranda kalmalı, ardından akıcı geçişle videoyu açmalıdır
    card_dur_frames = captions[0]["durationInFrames"] if captions else 85
    card_dur_frames = min(max(card_dur_frames, 75), 90)

    # ASMR Arka Plan Videosu Çözümle
    bg_video_rel = resolve_asmr_background_video(pub_media, work_dir, actual_duration)

    # ── Profil Resmi / Avatar Çözümle ──
    avatar_rel = ""
    custom_images = job_data.get("custom_images") or {}
    avatar_raw = (
        custom_images.get("avatar") or
        custom_images.get("reddit_avatar") or
        custom_images.get("0") or
        job_data.get("channel_config", {}).get("reddit_avatar_path") or
        ""
    )

    if avatar_raw and str(avatar_raw).startswith("data:"):
        try:
            head, b64_data = str(avatar_raw).split(",", 1) if "," in str(avatar_raw) else ("", str(avatar_raw))
            img_bytes = base64.b64decode(b64_data)
            av_file = pub_media / f"reddit_avatar_{work_dir.name}.jpg"
            av_file.write_bytes(img_bytes)
            avatar_rel = f"media/{av_file.name}"
        except Exception as e_av:
            print(f"[Worker] Reddit base64 avatar uyarısı: {e_av}")

    if not avatar_rel and avatar_raw:
        raw_name = Path(str(avatar_raw)).name
        if (pub_media / raw_name).exists():
            avatar_rel = f"media/{raw_name}"
        elif (BASE_DIR / "assets" / "watermark" / raw_name).exists():
            shutil.copy2(str(BASE_DIR / "assets" / "watermark" / raw_name), str(pub_media / raw_name))
            avatar_rel = f"media/{raw_name}"

    # Varsayılan resmi Reddit kanal avatarı fallback'i (Keçi amblemi)
    if not avatar_rel:
        for default_cand in ["reddit_avatar.jpg", "Gemini_Generated_Image_w5z6etw5z6etw5z6.jpeg"]:
            if (pub_media / default_cand).exists():
                avatar_rel = f"media/{default_cand}"
                break
            elif (BASE_DIR / "assets" / "watermark" / default_cand).exists():
                shutil.copy2(str(BASE_DIR / "assets" / "watermark" / default_cand), str(pub_media / default_cand))
                avatar_rel = f"media/{default_cand}"
                break

    # Remotion Props hazırla (Klon ses giydirmesinde halüsinasyonu önlemek için saf sesle render edilir):
    job_data["selected_bgm"] = selected_bgm.replace("media/", "") if selected_bgm else "reddit_official_bgm.mp3"
    props = {
        "question": question,
        "subreddit": subreddit,
        "author": author,
        "upvotes": upvotes,
        "avatarPath": avatar_rel,
        "bgVideoPath": bg_video_rel,
        "cardDurationFrames": card_dur_frames,
        "audioPath": f"media/{rel_audio_name}",
        "bgmPath": "",
        "bgmVolume": 0.0,
        "captions": captions,
        "fps": fps,
        "durationInFrames": total_frames,
    }

    props_file = work_dir / "remotion_reddit_props.json"
    props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2))

    output_video = work_dir / "final_video.mp4"
    print(f"[Worker] Remotion RedditStory render başlatılıyor ({total_frames} kare, {actual_duration:.1f}s)...")

    render_cmd = [
        "npx", "remotion", "render",
        "src/index.ts",
        "RedditStory",
        str(output_video),
        f"--props={str(props_file)}",
        f"--public-dir={str(pub_media.parent)}",
        "--concurrency=2",
        "--overwrite"
    ]
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "2"
    proc = subprocess.run(render_cmd, cwd=str(REMOTION_DIR), capture_output=True, text=True, env=env)

    if proc.returncode != 0 or not output_video.exists():
        print(f"[Worker] Remotion RedditStory render uyarısı: {proc.stderr}\nFFmpeg fallback uygulanıyor...")
        return render_general_job(job_data, work_dir)

    return output_video


def _extract_chapter_title(narration: str, idx: int, total: int) -> str:
    """Sahne metninden YouTube video açıklaması için semantik bölüm başlığı çıkarır."""
    n = narration.lower()
    if any(k in n for k in ["takeoff", "cleared", "runway", "departure", "taxi", "kalkış", "pist"]):
        return "Departure & Takeoff Roll"
    elif any(k in n for k in ["climb", "cruise", "fl3", "fl2", "heading", "airway", "tırmanış", "irtifa"]):
        return "Climb to Cruise & Flight Path"
    elif any(k in n for k in ["autopilot", "disconnect", "alarm", "warning", "caution", "otopilot", "ikaz"]):
        return "Autopilot Disconnect & Early Anomaly"
    elif any(k in n for k in ["bank angle", "spiral", "roll", "stall", "overspeed", "dive", "pull up", "yatış", "lövyeye"]):
        return "Spatial Disorientation & Loss of Control"
    elif any(k in n for k in ["atc", "tower", "radar", "contact", "squawk", "lost contact", "kule", "telsiz"]):
        return "Radar Contact Lost (Air Traffic Control)"
    elif any(k in n for k in ["crash", "impact", "ocean", "wreckage", "debris", "salvage", "çarpma", "enkaz"]):
        return "Catastrophic Impact & Search Operations"
    elif any(k in n for k in ["black box", "fdr", "cvr", "investigation", "ntsb", "bea", "kara kutu"]):
        return "Flight Data Recorder Recovery"
    elif any(k in n for k in ["probable cause", "findings", "concluded", "final report", "kaza kırım", "rapor"]):
        return "Official Investigation Findings & Cause"
    else:
        progress = idx / max(1, total - 1)
        if progress < 0.25:
            return "Flight Preparation & Departure"
        elif progress < 0.50:
            return "Developing In-Flight Emergency"
        elif progress < 0.75:
            return "Critical Cockpit Breakdown"
        else:
            return "Accident Investigation & Safety Legacy"


# ─────────────────────────────────────────────────────────────
# Havacılık Dinamik Tepkili Klon Ses (Adaptive Reactive Voice) & FX Motoru
# ─────────────────────────────────────────────────────────────
_cloud_chatterbox_model = None

def get_cloud_chatterbox_model():
    """
    Bulut veya yerel ortamda ChatterboxTTS modelini hafızaya alır ve
    kullanıcının klon ses profilini (documentary_narrator_v2.pt) aktif eder.
    """
    global _cloud_chatterbox_model
    if _cloud_chatterbox_model is not None:
        return _cloud_chatterbox_model
    
    import torch
    from chatterbox.tts import ChatterboxTTS, Conditionals
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Worker-Aviation] 🎙️ ChatterboxTTS modeli hafızaya alınıyor ({device.upper()})...")
    model = ChatterboxTTS.from_pretrained(device=device)
    
    # Olası klon ses profili yolları
    possible_pts = [
        Path("/home/ubuntu/yt-remote-worker/voice_samples/documentary_narrator_v2.pt"),
        Path("/home/ubuntu/yt-remote-worker/voice_samples/documentary_narrator_enhanced.wav"),
        Path(__file__).resolve().parent.parent / "config" / "assets" / "voice_samples" / "documentary_narrator_v2.pt",
        Path(__file__).resolve().parent.parent / "voice_samples" / "documentary_narrator_v2.pt"
    ]
    cond_loaded = False
    for pt_path in possible_pts:
        if pt_path.exists():
            try:
                if str(pt_path).endswith(".pt"):
                    model.conds = Conditionals.load(pt_path, map_location=torch.device(device))
                else:
                    model.prepare_conditionals(str(pt_path), exaggeration=0.5)
                print(f"[Worker-Aviation] 🎙️ Belgesel Klon Ses Profili aktif edildi: {pt_path.name}")
                cond_loaded = True
                break
            except Exception as e_pt:
                print(f"[Worker-Aviation] ⚠️ Klon ses profili yükleme uyarısı ({pt_path.name}): {e_pt}")
                
    if not cond_loaded:
        print("[Worker-Aviation] ⚠️ Klon ses profili (.pt) bulunamadı; Chatterbox varsayılan referansla çalışacak.")
        
    _cloud_chatterbox_model = model
    print("[Worker-Aviation] ✅ ChatterboxTTS motoru başarıyla yüklendi.")
    return _cloud_chatterbox_model


def classify_aviation_audio_profile(scene_data: dict, spoken_text: str, idx: int, total_scenes: int) -> dict:
    """
    Havacılık sahnesinin metnini ve görsel türünü analiz ederek:
    1. 'crisis' (Stick shaker, pull up, mayday, stall, yere çakılma, aşırı panik)
    2. 'radio_dialogue' (CVR kokpit telsiz konuşmaları, ATC kule çağrıları)
    3. 'calm_narration' (Tarihi kaza kırım araştırması ve teknik belgesel anlatımı)
    durumunu belirler ve Chatterbox exaggeration/cfg/temp parametrelerini döndürür.
    """
    text_lower = spoken_text.lower()
    
    # Acil durum ve panik tetikleyicileri
    crisis_keywords = [
        "bank angle", "pull up", "whoop whoop", "terrain", "stall", "sink rate", "overspeed",
        "mayday", "pan-pan", "clacker", "emergency", "traffic traffic", "collision",
        "we are going down", "we're going down", "i have no control", "we lost control",
        "stick shaker", "spatial disorientation", "uncommanded", "overbank", "dive dive",
        "too low", "glide slope", "windshear", "pull, pull", "brace for impact", "impact",
        "çakılıyor", "çakılma", "çarpışma", "kurtarın", "ne oluyor", "irtifa kaybediyoruz",
        "kontrolü kaybettik", "lövye", "yanıyoruz", "terk edin", "acil durum", "ikaz",
        "düşüyoruz", "durmuyor", "çek lövyeyi", "sola yatış", "sağa yatış", "aşırı hız",
        "motor durdu", "irtifa", "düşüş"
    ]
    is_crisis = (
        bool(scene_data.get("is_cold_open")) or
        scene_data.get("emotion") in ("panicked", "urgent", "terrified", "emergency") or
        any(kw in text_lower for kw in crisis_keywords)
    )
    
    # Kokpit CVR veya ATC Kule telsiz diyaloğu
    has_quotes = bool(re.search(r'["“\'][^"”\']{3,}["”\']', spoken_text))
    radio_terms = [
        "cvr", "atc", "kaptan:", "captain:", "f/o:", "first officer:", "tower:", "kule:",
        "confirm you are", "radar contact lost", "turn left", "turn right", "cleared for",
        "squawk", "roger", "roger that", "telsiz", "transponder", "contact departure"
    ]
    is_radio = (
        has_quotes or
        scene_data.get("visual_type") in ("cvr_reconstruction", "cockpit_cvr_dialogue", "tactical_radar") or
        any(rt in text_lower for rt in radio_terms)
    )
    
    if is_crisis:
        return {
            "mode": "crisis",
            "exaggeration": 0.82,
            "cfg_weight": 0.65,
            "temperature": 0.85,
            "is_reactive": True
        }
    elif is_radio:
        return {
            "mode": "radio_dialogue",
            "exaggeration": 0.68,
            "cfg_weight": 0.60,
            "temperature": 0.75,
            "is_reactive": True
        }
    else:
        return {
            "mode": "calm_narration",
            "exaggeration": 0.42,
            "cfg_weight": 0.50,
            "temperature": 0.75,
            "is_reactive": False
        }


def apply_aviation_scene_audio_fx(audio_path: Path, mode: str, work_dir: Path):
    """
    Sahnede CVR, ATC veya Acil Durum tespit edildiğinde ses dosyasına
    otantik havacılık radyo bandpass filtresi, PTT mandal klik sesi veya kokpit alarmı miksler.
    """
    if not audio_path.exists() or audio_path.stat().st_size < 1000:
        return
    tmp_out = work_dir / f"fx_{audio_path.name}"
    try:
        if mode == "radio_dialogue":
            # Havacılık VHF Telsiz Filtresi + Başlangıçta PTT Mandal Squelch Klik Sesi
            radio_filter = (
                "highpass=f=350,lowpass=f=3400,"
                "equalizer=f=1200:width_type=q:w=1.5:g=2.5,"
                "acompressor=threshold=-16dB:ratio=3.5:attack=5:release=60,"
                "loudnorm=I=-16:TP=-1.5:LRA=6"
            )
            squelch_complex = (
                "anoisesrc=d=0.08:c=white:a=0.18,lowpass=f=2600,highpass=f=500[click];"
                "[0:a][click]amix=inputs=2:duration=first:dropout_transition=1:normalize=0,"
                + radio_filter + "[aout]"
            )
            subprocess.run([
                "ffmpeg", "-y", "-i", str(audio_path),
                "-filter_complex", squelch_complex,
                "-map", "[aout]", "-c:a", "libmp3lame", "-b:a", "192k",
                str(tmp_out)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if tmp_out.exists() and tmp_out.stat().st_size > 1000:
                os.replace(tmp_out, audio_path)
                print(f"[Worker-Aviation] 📻 Telsiz/CVR diyaloğu için VHF radyo bandpass & PTT squelch uygulandı.")
                
        elif mode == "crisis":
            # Kriz & Acil Durum: Basınçlı kabin, Master Warning ikaz alarmı ve yüksek dinamik EQ
            crisis_filter = (
                "highpass=f=90,"
                "equalizer=f=3000:width_type=q:w=1.0:g=3.0,"
                "acompressor=threshold=-18dB:ratio=3.0:attack=10:release=100,"
                "loudnorm=I=-15:TP=-1.0:LRA=7"
            )
            alarm_complex = (
                "sine=f=800:d=0.15[b1];"
                "sine=f=800:d=0.15[b2];"
                "[b1][b2]concat=n=2:v=0:a=1,volume=0.22[alarms];"
                "[0:a][alarms]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,"
                + crisis_filter + "[aout]"
            )
            subprocess.run([
                "ffmpeg", "-y", "-i", str(audio_path),
                "-filter_complex", alarm_complex,
                "-map", "[aout]", "-c:a", "libmp3lame", "-b:a", "192k",
                str(tmp_out)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if tmp_out.exists() and tmp_out.stat().st_size > 1000:
                os.replace(tmp_out, audio_path)
                print(f"[Worker-Aviation] 🚨 Acil durum sahnesine kokpit Master Warning alarmı mikslendi.")
    except Exception as e_fx:
        print(f"[Worker-Aviation] ⚠️ Ses FX filtre uyarısı: {e_fx}")
        if tmp_out.exists():
            try: os.remove(tmp_out)
            except Exception: pass


# ─────────────────────────────────────────────────────────────
# 5. Havacılık (Aviation / Black Box) Belgesel Render Motoru (16:9 + Pixabay Video + NTSB Arşiv + Düzgün Altyazı)
# ─────────────────────────────────────────────────────────────
def render_aviation_job(job_data: dict, work_dir: Path) -> Path:
    import aviation_media_fetcher
    
    channel_id = job_data.get("channel_id", "blackboxaudioo")
    script = job_data.get("script_data") or job_data.get("script") or {}
    channel_cfg = job_data.get("channel_config") or {}
    custom_audios = job_data.get("custom_audios") or {}
    lang = (channel_cfg.get("language") or "en").lower().strip()
    is_shorts = bool(channel_cfg.get("shorts_mode", False))
    
    # 1. En boy oranı (Havacılık belgeselleri varsayılan 16:9 yataydır)
    W = 1080 if is_shorts else 1920
    H = 1920 if is_shorts else 1080
    
    # Senaryoyu hedef kanalın diline otomatik yerelleştir
    script = ensure_localized_script(script, lang)

    topic = script.get("topic") or script.get("title") or channel_id
    scenes = script.get("scenes") or []
    
    # Eğer sahne listesi yoksa, metni 3'er cümlelik sahne bloklarına böl
    if not scenes or not isinstance(scenes, list):
        full_text = script.get("narration") or script.get("story") or script.get("body") or script.get("title", "")
        if isinstance(full_text, list):
            full_text = " ".join(full_text)
        sentences_raw = re.split(r'(?<=[.!?])\s+', str(full_text).strip())
        sentences_raw = [s.strip() for s in sentences_raw if s.strip()]
        chunk_size = 3
        scenes = []
        for i in range(0, len(sentences_raw), chunk_size):
            chunk_txt = " ".join(sentences_raw[i:i+chunk_size])
            scenes.append({
                "narration": chunk_txt,
                "image_prompt": f"Airplane flight scene {i//chunk_size + 1}",
                "emotion": "dramatic"
            })
            
    if not scenes:
        scenes = [{"narration": topic, "image_prompt": "Airplane flight", "emotion": "dramatic"}]

    voice = VOICE_MAP.get(lang, {}).get("narrator", "en-US-ChristopherNeural" if lang == "en" else "tr-TR-AhmetNeural")
    tts_engine = str(job_data.get("tts_engine") or "kokoro").lower()
    
    # 2. Otomatik Taktiksel Radar ve Gösterge Telemetri Grafikleri Üretimi
    meta = None
    try:
        import aviation_telemetry_engine
        print(f"[Worker-Aviation] 📊 Olay için teknik telemetri ve radar rota grafikleri üretiliyor: '{topic}'...")
        telemetry_res = aviation_telemetry_engine.generate_flight_graphics(topic, work_dir, scenes=scenes, script=script)
        meta = telemetry_res.get("metadata")
        print(f"[Worker-Aviation] ✅ Telemetri grafikleri başarıyla hazırlandı ({meta.get('flight_name') if meta else 'Dynamic'}).")
    except Exception as e:
        print(f"[Worker-Aviation] ⚠️ Telemetri grafik üretimi uyarısı: {e}")

    # ── İLK 10 SANİYE KANCASI (COLD OPEN RETENTION HOOK) & KANAL İNTROSU ──
    has_cold_open = any(s.get("is_cold_open") for s in scenes[:2])
    if not has_cold_open and not is_shorts and meta:
        f_name = meta.get("flight_name", topic)
        impact_loc = meta.get("radar", {}).get("impact_point", "the void")
        t_match = re.search(r'\b(\d{1,2}:\d{2}\s*(?:am|pm)?)\b', topic, re.IGNORECASE)
        t_str = t_match.group(1) if t_match else "In the dead of night"

        if lang == "en":
            hook_txt = f"At {t_str}, {f_name} vanished into {impact_loc}. This is what the cockpit recorder captured in its final terrifying seconds."
            intro_txt = f"{f_name}. Declassified flight data and cockpit voice recorder investigation."
        else:
            hook_txt = f"Saat {t_str}'te, {f_name} {impact_loc} üzerinde radardan tamamen kayboldu. İşte kokpit ses kayıt cihazının kaydettiği o son anlar..."
            intro_txt = f"{f_name}. Gizliliği kaldırılmış kaza kırım incelemesi ve kara kutu analizleri."

        hook_sc = {
            "narration": hook_txt,
            "image_prompt": f"Cockpit voice recorder emergency alarms bank angle {f_name}",
            "emotion": "urgent",
            "is_cold_open": True
        }
        intro_sc = {
            "narration": intro_txt,
            "image_prompt": f"Documentary title card Black Box Audio {f_name}",
            "emotion": "dramatic",
            "is_intro_card": True
        }
        scenes = [hook_sc, intro_sc] + scenes
        print(f"[Worker-Aviation] ⚡ İlk 10 Saniye Kancası (Cold Open) ve Kanal İntro Sahnesi eklendi (Toplam: {len(scenes)} sahne).")

    # 3. Sahne bazlı seslendirme, cümle zamanlaması ve telifsiz medya eldesi
    scene_media_files = []
    audio_segments = []
    scene_durations = []
    srt_entries = []
    global_time_offset = 0.0
    used_media_ids = set()
    
    print(f"[Worker-Aviation] Toplam {len(scenes)} sahne için üretim başlatılıyor ({W}x{H}, Format: {'9:16 Shorts' if is_shorts else '16:9 Yatay'})...")

    has_full_custom = bool(custom_audios and all((str(i) in custom_audios or f"scene_{i}" in custom_audios) for i in range(len(scenes))))
    kokoro_wavs = []
    if not has_full_custom and tts_engine == "kokoro":
        kokoro_speed = _get_kokoro_speed(job_data)
        kokoro_lang = lang.split("-", 1)[0]
        if kokoro_lang in KOKORO_LANGUAGES:
            kokoro_wavs = [work_dir / f"scene_{idx}_kokoro.wav" for idx in range(len(scenes))]
            try:
                generate_kokoro_batch(
                    [
                        prepare_speech_text_and_tone(
                            sc.get("narration") or sc.get("text") or "", lang
                        )[0]
                        for sc in scenes
                    ],
                    kokoro_wavs,
                    lang,
                    str(job_data.get("kokoro_voice") or "am_michael"),
                    kokoro_speed,
                )
                print(f"[Worker-Aviation] Kokoro-TTS seslendirildi ({len(kokoro_wavs)} sahne, {kokoro_speed:.2f}x).")
            except Exception as exc:
                raise RuntimeError(f"Kokoro-TTS seslendirmesi başarısız oldu: {exc}") from exc
        else:
            print(f"[Worker-Aviation] Kokoro '{lang}' dilini desteklemiyor; daha doğal Chatterbox ayarlarına geçiliyor.")
            tts_engine = "chatterbox"
    
    for idx, sc in enumerate(scenes):
        narration = sc.get("narration") or sc.get("text") or ""
        spoken_text, rate, pitch = prepare_speech_text_and_tone(narration, lang)
        scene_audio_path = work_dir / f"scene_{idx}_audio.mp3"
        boundaries = []

        # 1. Öncelik: Klon stüdyo sesi (payload custom_audios)
        idx_key = str(idx)
        used_custom = False
        if custom_audios and (idx_key in custom_audios or f"scene_{idx}" in custom_audios):
            try:
                raw_aud = custom_audios.get(idx_key) or custom_audios.get(f"scene_{idx}")
                if "," in raw_aud:
                    raw_aud = raw_aud.split(",", 1)[1]
                aud_bytes = base64.b64decode(raw_aud)
                scene_audio_path.write_bytes(aud_bytes)
                used_custom = True
                print(f"[Worker-Aviation] 🎙️ Sahne {idx} için stüdyo kalitesinde klon ses kullanıldı.")
            except Exception as e_ca:
                print(f"[Worker-Aviation] ⚠️ Özel ses çözme uyarısı: {e_ca}")

        # Sahne seslendirme profili analizi (Kriz, Telsiz/CVR diyaloğu veya Belgesel anlatımı)
        audio_prof = classify_aviation_audio_profile(sc, spoken_text, idx, len(scenes))
        mode = audio_prof["mode"]
        is_reactive = audio_prof["is_reactive"]

        # 2. Öncelik: Tepkili Kriz/CVR Sahneleri veya Tam Klon Modu için ChatterboxTTS
        used_chatterbox = False
        should_use_chatterbox = not used_custom and (
            tts_engine == "chatterbox" or
            (is_reactive and (not kokoro_wavs or idx >= len(kokoro_wavs) or not kokoro_wavs[idx].exists() or True))
        )
        if should_use_chatterbox:
            try:
                cb_model = get_cloud_chatterbox_model()
                print(f"[Worker-Aviation] 🎙️ Sahne {idx} ({mode.upper()}) Chatterbox Klon Ses ile seslendiriliyor (exaggeration={audio_prof['exaggeration']:.2f}, cfg={audio_prof['cfg_weight']:.2f})...")
                wav = cb_model.generate(
                    spoken_text,
                    exaggeration=audio_prof["exaggeration"],
                    cfg_weight=audio_prof["cfg_weight"],
                    temperature=audio_prof["temperature"]
                )
                audio_data = wav.cpu().squeeze().numpy()
                import soundfile as sf
                wav_temp = str(scene_audio_path).replace(".mp3", ".wav")
                sf.write(wav_temp, audio_data, cb_model.sr)
                
                master_filter = "highpass=f=65,equalizer=f=3200:width_type=q:w=1.2:g=1.2,acompressor=threshold=-20dB:ratio=2.0:attack=15:release=180,loudnorm=I=-16:TP=-1.5:LRA=8"
                subprocess.run(
                    ["ffmpeg", "-y", "-i", wav_temp, "-af", master_filter, "-codec:a", "libmp3lame", "-b:a", "192k", str(scene_audio_path)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                )
                try: os.remove(wav_temp)
                except Exception: pass
                
                if scene_audio_path.exists() and scene_audio_path.stat().st_size > 1000:
                    used_chatterbox = True
                    print(f"[Worker-Aviation] ✅ Sahne {idx} Chatterbox Klon Ses ile başarıyla üretildi.")
            except Exception as e_cb:
                print(f"[Worker-Aviation] ⚠️ Chatterbox üretim uyarısı (Sahne {idx}): {e_cb}. Fallback devreye giriyor...")

        # 3. Öncelik: Standart Belgesel Anlatımında Hızlı Kokoro (Sakin sahneler veya Chatterbox fallback)
        if not used_custom and not used_chatterbox and tts_engine == "kokoro" and idx < len(kokoro_wavs) and kokoro_wavs[idx].exists():
            kokoro_filter = (
                "highpass=f=75,"
                "equalizer=f=180:width_type=q:w=1.2:g=1.2,"
                "equalizer=f=3500:width_type=q:w=1.2:g=1.0,"
                "acompressor=threshold=-20dB:ratio=2.0:attack=15:release=180,"
                "loudnorm=I=-16:TP=-1.5:LRA=8"
            )
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(kokoro_wavs[idx]),
                    "-af", kokoro_filter, "-codec:a", "libmp3lame",
                    "-b:a", "192k", str(scene_audio_path),
                ],
                capture_output=True, check=True,
            )

        # 4. Öncelik: Edge-TTS Fallback
        if not scene_audio_path.exists() or scene_audio_path.stat().st_size < 1000:
            async def _gen_speech_and_bounds():
                for attempt in range(3):
                    try:
                        comm = edge_tts.Communicate(spoken_text, voice, rate=rate, pitch=pitch)
                        with open(scene_audio_path, "wb") as f_out:
                            async for chunk in comm.stream():
                                if chunk["type"] == "audio":
                                    f_out.write(chunk["data"])
                                elif chunk["type"] == "SentenceBoundary":
                                    st = chunk["offset"] / 10_000_000.0
                                    du = chunk["duration"] / 10_000_000.0
                                    txt = chunk.get("text", "").strip()
                                    if txt:
                                        boundaries.append((txt, st, st + du))
                        if scene_audio_path.exists() and scene_audio_path.stat().st_size > 1000:
                            break
                    except Exception as e_handshake:
                        print(f"[Worker-Aviation] ⚠️ Edge-TTS deneme {attempt+1} hatası: {e_handshake}")
                        time.sleep(2 * (attempt + 1))
            asyncio.run(_gen_speech_and_bounds())

        # 5. Otantik Havacılık Ses FX Miksleme (VHF Telsiz Squelch / Kokpit Master Warning Alarmı)
        if mode in ("crisis", "radio_dialogue") and scene_audio_path.exists():
            apply_aviation_scene_audio_fx(scene_audio_path, mode, work_dir)

        sc_dur = get_media_duration(str(scene_audio_path))
        if sc_dur <= 0.5:
            sc_dur = 4.0
            
        audio_segments.append(str(scene_audio_path))
        scene_durations.append(sc_dur)
        
        # Altyazı girişleri
        if boundaries:
            for txt, st, en in boundaries:
                start_abs = global_time_offset + st
                end_abs = min(global_time_offset + sc_dur, global_time_offset + en)
                srt_entries.append((txt, start_abs, end_abs))
        else:
            srt_entries.append((spoken_text, global_time_offset, global_time_offset + sc_dur))
            
        # 3. Sahne medyası temin et (Pixabay Video 1080p MP4 veya Wikimedia Görsel)
        seg_video = work_dir / f"scene_{idx}_video.mp4"
        if seg_video.exists() and seg_video.stat().st_size > 50000:
            print(f"[Worker-Aviation] Sahne {idx+1}/{len(scenes)} zaten hazır: {seg_video.name} ({seg_video.stat().st_size // 1024} KB), önbellekten kullanılıyor.")
            scene_media_files.append(str(seg_video))
            global_time_offset += sc_dur
            continue

        if sc.get("is_intro_card"):
            card_img = work_dir / f"intro_title_card_{idx}.png"
            try:
                from PIL import Image, ImageDraw
                im_card = Image.new("RGB", (W, H), (8, 14, 22))
                d_card = ImageDraw.Draw(im_card)
                for gx in range(0, W, 80):
                    d_card.line([(gx, 0), (gx, H)], fill=(14, 22, 34), width=1)
                for gy in range(0, H, 80):
                    d_card.line([(0, gy), (W, gy)], fill=(14, 22, 34), width=1)
                
                # Badge
                d_card.rectangle([(W//2 - 380, H//2 - 160), (W//2 + 380, H//2 - 110)], fill=(0, 200, 255))
                try:
                    from aviation_telemetry_engine import get_font as get_eng_font
                except ImportError:
                    get_eng_font = lambda sz, b=False: None
                d_card.text((W//2 - 360, H//2 - 150), "BLACK BOX AUDIO // OFFICIAL CASE ARCHIVE", fill=(10, 15, 24), font=get_eng_font(24, True))
                
                f_title = meta.get("flight_name", topic).upper()[:45] if meta else topic.upper()[:45]
                d_card.text((W//2 - 420, H//2 - 60), f_title, fill=(255, 255, 255), font=get_eng_font(40, True))
                
                sub_label = f"AIRCRAFT: {meta.get('aircraft_type', 'COMMERCIAL JET')}   |   ATC / CVR RECONSTRUCTION" if meta else "AIRCRAFT ACCIDENT RECONSTRUCTION"
                d_card.text((W//2 - 420, H//2 + 30), sub_label, fill=(0, 210, 255), font=get_eng_font(20, False))
                d_card.line([(W//2 - 420, H//2 + 75), (W//2 + 420, H//2 + 75)], fill=(0, 180, 220), width=3)
                im_card.save(card_img, "PNG")
                media_path = str(card_img)
                print(f"[Worker-Aviation] 🎬 Kanal Başlık Kartı hazırlandı: {card_img.name}")
            except Exception as e_card:
                print(f"[Worker-Aviation] İntro kart üretim hatası: {e_card}")
                media_path = None
        else:
            print(f"[Worker-Aviation] Sahne {idx+1}/{len(scenes)} için medya çekiliyor (Süre: {sc_dur:.1f}s)...")
            media_path = aviation_media_fetcher.get_aviation_scene_media(
                scene_idx=idx,
                total_scenes=len(scenes),
                topic=topic,
                scene_data=sc,
                work_dir=work_dir,
                target_w=W,
                target_h=H,
                target_dur=sc_dur,
                session_used=used_media_ids,
                metadata=meta,
                all_scenes=scenes
            )
        
        if media_path and os.path.exists(media_path):
            climate = meta.get("climate", "NEUTRAL") if meta else aviation_media_fetcher.detect_climate_mode(f"{topic} {sc.get('narration', '')}")
            fps = 25
            
            # Eğer sahne süresi <= 6.5 saniyeyse tek çekim yeterlidir
            if sc_dur <= 6.5:
                if str(media_path).endswith(".mp4"):
                    cmd_v = [
                        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(media_path),
                        "-t", f"{sc_dur:.3f}",
                        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=25,setsar=1",
                        "-r", "25", "-video_track_timescale", "12800",
                        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                        str(seg_video)
                    ]
                else:
                    total_f = max(25, int(sc_dur * fps))
                    cmd_v = [
                        "ffmpeg", "-y", "-loop", "1", "-i", str(media_path),
                        "-t", f"{sc_dur:.3f}",
                        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},zoompan=z='min(zoom+0.0006,1.06)':d={total_f}:s={W}x{H}:fps={fps},fps=25,setsar=1",
                        "-r", "25", "-video_track_timescale", "12800",
                        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                        str(seg_video)
                    ]
                subprocess.run(cmd_v, capture_output=True, check=True)
            else:
                # Sahne 6.5s üzerinde: 2 Dinamik Alt Çekime Böl (Anti-Stagnation Kuralı - Max 5-6s/cut)
                dur1 = round(sc_dur / 2.0, 3)
                dur2 = round(sc_dur - dur1, 3)
                sub1 = work_dir / f"temp_sc{idx}_part1.mp4"
                sub2 = work_dir / f"temp_sc{idx}_part2.mp4"
                
                # Part 1: Birincil Medya
                if str(media_path).endswith(".mp4"):
                    cmd1 = [
                        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(media_path),
                        "-t", f"{dur1:.3f}",
                        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=25,setsar=1",
                        "-r", "25", "-video_track_timescale", "12800",
                        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                        str(sub1)
                    ]
                else:
                    total_f1 = max(25, int(dur1 * fps))
                    cmd1 = [
                        "ffmpeg", "-y", "-loop", "1", "-i", str(media_path),
                        "-t", f"{dur1:.3f}",
                        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},zoompan=z='min(zoom+0.0007,1.07)':d={total_f1}:s={W}x{H}:fps={fps},fps=25,setsar=1",
                        "-r", "25", "-video_track_timescale", "12800",
                        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                        str(sub1)
                    ]
                subprocess.run(cmd1, capture_output=True, check=True)

                # Part 2: İkincil B-Roll veya Kokpit Klibi (Uçak kategorisi ve gece filtresi korumalı)
                category = meta.get("aircraft_category", "jet") if meta else "jet"
                if climate == "NIGHT":
                    alt_query = "cockpit instruments airplane" if idx % 2 == 0 else "cockpit night flight"
                elif category == "turboprop":
                    alt_query = "turboprop propeller" if idx % 2 == 0 else "cockpit instruments airplane"
                elif climate == "WINTER":
                    alt_query = "blizzard" if idx % 2 == 0 else "winter airport"
                else:
                    alt_query = "cockpit airplane" if idx % 2 == 0 else "airport runway"

                alt_vid = aviation_media_fetcher.search_pixabay_video(
                    alt_query, 
                    exclude_ids=used_media_ids, 
                    min_duration=dur2, 
                    climate=climate,
                    aircraft_category=category
                )
                part2_done = False
                if alt_vid and aviation_media_fetcher.download_and_format_video(alt_vid["url"], str(sub2), W, H, dur2):
                    used_media_ids.add(alt_vid["id"])
                    part2_done = True
                
                if not part2_done:
                    # Alternatif video yoksa birinci medyayı ters pan/zoom veya offset ile oynat
                    if str(media_path).endswith(".mp4"):
                        cmd2 = [
                            "ffmpeg", "-y", "-ss", "2.5", "-stream_loop", "-1", "-i", str(media_path),
                            "-t", f"{dur2:.3f}",
                            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=25,setsar=1",
                            "-r", "25", "-video_track_timescale", "12800",
                            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                            str(sub2)
                        ]
                    else:
                        total_f2 = max(25, int(dur2 * fps))
                        cmd2 = [
                            "ffmpeg", "-y", "-loop", "1", "-i", str(media_path),
                            "-t", f"{dur2:.3f}",
                            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},zoompan=z='min(zoom+0.0006,1.06)':x='iw/2-(iw/zoom/2)+sin(in/30)*30':y='ih/2-(ih/zoom/2)':d={total_f2}:s={W}x{H}:fps={fps},fps=25,setsar=1",
                            "-r", "25", "-video_track_timescale", "12800",
                            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                            str(sub2)
                        ]
                    subprocess.run(cmd2, capture_output=True, check=True)

                # İki alt çekimi birleştir
                concat_txt = work_dir / f"concat_sc{idx}.txt"
                with open(concat_txt, "w") as f_c:
                    f_c.write(f"file '{sub1.resolve()}'\nfile '{sub2.resolve()}'\n")

                cmd_cat = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
                    "-r", "25", "-video_track_timescale", "12800",
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an", str(seg_video)
                ]
                subprocess.run(cmd_cat, capture_output=True, check=True)
                for p_sub in [sub1, sub2, concat_txt]:
                    if p_sub.exists():
                        try:
                            p_sub.unlink()
                        except Exception:
                            pass
        else:
            # Fallback: Estetik gökyüzü gradyanı (Asla boş siyah ekran değil)
            fps = 25
            total_f = max(25, int(sc_dur * fps))
            fallback_img = work_dir / f"scene_{idx}_fallback.jpg"
            try:
                from PIL import Image, ImageDraw
                im = Image.new("RGB", (W, H), (15, 25, 45))
                draw = ImageDraw.Draw(im)
                for y in range(H):
                    r = int(12 + (35 - 12) * (y / H))
                    g = int(22 + (60 - 22) * (y / H))
                    b = int(45 + (120 - 45) * (y / H))
                    draw.line([(0, y), (W, y)], fill=(r, g, b))
                im.save(fallback_img, "JPEG")
                cmd_v = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", str(fallback_img),
                    "-t", f"{sc_dur:.3f}",
                    "-vf", f"zoompan=z='min(zoom+0.0005,1.05)':d={total_f}:s={W}x{H}:fps={fps},fps=25,setsar=1",
                    "-r", "25", "-video_track_timescale", "12800",
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                    str(seg_video)
                ]
                subprocess.run(cmd_v, capture_output=True, check=True)
            except Exception:
                cmd_v = [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", f"color=c=0x111827:s={W}x{H}:d={sc_dur:.3f}",
                    "-r", "25", "-video_track_timescale", "12800",
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                    str(seg_video)
                ]
                subprocess.run(cmd_v, capture_output=True, check=True)
                
        scene_media_files.append(str(seg_video))
        global_time_offset += sc_dur

    # 4. Video segmentlerini birleştir (Daima güncel sahne videolarından sıfırdan birleştirilir)
    concat_list_file = work_dir / "concat_videos.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f_c:
        for v in scene_media_files:
            f_c.write(f"file '{v}'\n")
            
    visual_track = work_dir / "visual_track.mp4"
    if visual_track.exists():
        try:
            visual_track.unlink()
        except Exception:
            pass
    cmd_concat_v = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list_file),
        "-r", "25",
        "-video_track_timescale", "12800",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
        str(visual_track)
    ]
    subprocess.run(cmd_concat_v, capture_output=True, check=True)

    # 5. Ses segmentlerini birleştir (Daima güncel sahne seslerinden sıfırdan birleştirilir - %100 senkron garantisi)
    concat_audio_list = work_dir / "concat_audios.txt"
    with open(concat_audio_list, "w", encoding="utf-8") as f_a:
        for a in audio_segments:
            f_a.write(f"file '{a}'\n")
            
    full_voiceover = work_dir / "full_voiceover.mp3"
    if full_voiceover.exists():
        try:
            full_voiceover.unlink()
        except Exception:
            pass
    cmd_concat_a = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_audio_list),
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(full_voiceover)
    ]
    subprocess.run(cmd_concat_a, capture_output=True, check=True)

    # 6. Düzgün Altyazı (SRT) Dosyası Oluştur (Doğal Okuma Hızında Lokma Parçalar)
    def sec_to_srt_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    srt_path = work_dir / "subtitles.srt"
    with open(srt_path, "w", encoding="utf-8") as srt_f:
        entry_idx = 1
        for txt, st, en in srt_entries:
            if en <= st:
                en = st + 1.0
            words = txt.split()
            if not words:
                continue

            # Uzun cümleleri 6-8 kelimelik (~2.5 saniyelik) lokmalara bölerek zamanı orantıla
            chunk_words = []
            cur_chars = 0
            seg_chunks = []
            for w in words:
                if cur_chars + len(w) + 1 > 42 or len(chunk_words) >= 8:
                    seg_chunks.append(" ".join(chunk_words))
                    chunk_words = [w]
                    cur_chars = len(w)
                else:
                    chunk_words.append(w)
                    cur_chars += len(w) + 1
            if chunk_words:
                seg_chunks.append(" ".join(chunk_words))

            total_dur = en - st
            num_chunks = len(seg_chunks)
            for c_i, c_text in enumerate(seg_chunks):
                c_st = st + (c_i * (total_dur / num_chunks))
                c_en = st + ((c_i + 1) * (total_dur / num_chunks))
                srt_f.write(f"{entry_idx}\n")
                srt_f.write(f"{sec_to_srt_time(c_st)} --> {sec_to_srt_time(c_en)}\n")
                srt_f.write(f"{c_text}\n\n")
                entry_idx += 1

    # 7. Nihai Birleştirme & Altyazı Giydirme
    output_video = work_dir / "final_video.mp4"
    print(f"[Worker-Aviation] Nihai montaj yapılıyor ve altyazı giydiriliyor ({W}x{H})...")
    
    font_size = 24 if not is_shorts else 38
    margin_v = 45 if not is_shorts else 160
    sub_filter = f"subtitles='{str(srt_path)}':force_style='FontName=DejaVu Sans,FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2.8,Shadow=1.2,Alignment=2,MarginV={margin_v}'"
    
    ffmpeg_final = [
        "ffmpeg", "-y",
        "-i", str(visual_track),
        "-i", str(full_voiceover),
        "-vf", sub_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_video)
    ]
    subprocess.run(ffmpeg_final, capture_output=True, check=True)

    # 7.5. Otomatik YouTube Bölümleri (Chapters) Oluştur & Açıklamaya Ekle
    chapter_lines = []
    c_time = 0.0
    for s_i, sc_item in enumerate(scenes):
        s_dur = scene_durations[s_i] if s_i < len(scene_durations) else 5.0
        cm = int(c_time // 60)
        cs = int(c_time % 60)
        ts = f"{cm:02d}:{cs:02d}"
        if sc_item.get("is_cold_open"):
            c_name = "Final Cockpit Audio & Emergency Teaser"
        elif sc_item.get("is_intro_card"):
            c_name = "Case Briefing & Flight Dossier"
        else:
            c_name = _extract_chapter_title(sc_item.get("narration", ""), s_i, len(scenes))
        chapter_lines.append(f"{ts} - {c_name}")
        c_time += s_dur

    chapters_block = "\n\nTIMESTAMPS / CHAPTERS:\n" + "\n".join(chapter_lines)
    cur_desc = script.get("description", "") or ""
    if "TIMESTAMPS" not in cur_desc and "CHAPTERS" not in cur_desc:
        script["description"] = cur_desc.strip() + chapters_block
        if "script_data" in job_data and isinstance(job_data["script_data"], dict):
            job_data["script_data"]["description"] = script["description"]
    
    (work_dir / "youtube_chapters.txt").write_text("\n".join(chapter_lines), encoding="utf-8")
    print(f"[Worker-Aviation] ⏱️ YouTube Bölümleri (Chapters) oluşturuldu ({len(chapter_lines)} bölüm).")

    return output_video


# ─────────────────────────────────────────────────────────────
# 6. Genel / Diğer Konular Render Motoru
# ─────────────────────────────────────────────────────────────
def _has_per_scene_audio(custom_audios: dict, scene_count: int) -> bool:
    scene_keys = {
        str(key) for key in custom_audios
        if re.fullmatch(r"scene_\d+", str(key))
    }
    numeric_keys = {
        str(key) for key in custom_audios
        if str(key).isdigit()
    }
    if scene_keys or len(numeric_keys) > 1:
        return True
    return scene_count == 1 and bool(numeric_keys)


def _get_scene_audio_payload(custom_audios: dict, scene_index: int):
    return custom_audios.get(f"scene_{scene_index}") or custom_audios.get(str(scene_index))


def _allocate_legacy_scene_durations(scenes: list, total_duration: float) -> list[float]:
    weights = [
        max(1, len(str(scene.get("narration") or scene.get("text") or "").split()))
        for scene in scenes
    ]
    total_weight = sum(weights)
    if not total_weight:
        return []
    durations = [total_duration * weight / total_weight for weight in weights]
    durations[-1] = max(0.0, total_duration - sum(durations[:-1]))
    return durations


def _probe_scene_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
        ],
        capture_output=True, text=True, check=True,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise RuntimeError(f"Sahne sesinin süresi geçersiz: {audio_path.name}")
    return duration


def _decode_scene_images(custom_images: dict, work_dir: Path) -> dict[int, Path]:
    scene_images = {}
    for key, value in custom_images.items():
        match = re.fullmatch(r"(?:scene_)?(\d+)", str(key))
        if not match or not value:
            continue
        image_path = work_dir / f"general_scene_image_{match.group(1)}"
        try:
            if isinstance(value, str) and value.startswith("data:image") and "," in value:
                image_path.write_bytes(base64.b64decode(value.split(",", 1)[1]))
            elif isinstance(value, str) and value.startswith(("http://", "https://")):
                request = urllib.request.Request(value, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(request, timeout=15) as response:
                    image_path.write_bytes(response.read())
            elif isinstance(value, str) and Path(value).is_file():
                image_path = Path(value)
            else:
                continue
            if image_path.is_file() and image_path.stat().st_size:
                scene_images[int(match.group(1))] = image_path
        except Exception as error:
            print(f"[Worker-General] Görsel çözme uyarısı ({key}): {error}")
    return scene_images


def _render_scene_aligned_general(
    job_data: dict,
    script: dict,
    scenes: list,
    work_dir: Path,
    lang: str,
    voice_cfg: dict,
    width: int,
    height: int,
) -> Path:
    custom_audios = job_data.get("custom_audios") or {}
    custom_images = job_data.get("custom_images") or {}
    scene_images = _decode_scene_images(custom_images, work_dir) if isinstance(custom_images, dict) else {}
    entries = []
    for index, scene in enumerate(scenes):
        text = str(scene.get("narration") or scene.get("text") or "").strip()
        if text:
            entries.append((index, text, _get_scene_audio_payload(custom_audios, index)))
    if not entries:
        raise RuntimeError("Genel video için seslendirilecek sahne bulunamadı.")

    missing_audio = []
    audio_paths = {}
    for index, _text, audio_payload in entries:
        if not audio_payload:
            missing_audio.append(index)
            continue
        source_path = work_dir / f"general_scene_{index}_custom.bin"
        if isinstance(audio_payload, str) and "," in audio_payload and audio_payload.split(",", 1)[0].startswith("data:audio"):
            audio_payload = audio_payload.split(",", 1)[1]
        source_path.write_bytes(base64.b64decode(audio_payload))
        audio_paths[index] = source_path

    if missing_audio:
        texts_by_index = {index: text for index, text, _payload in entries}
        tts_engine = str(job_data.get("tts_engine") or "kokoro").lower()
        kokoro_voice = str(job_data.get("kokoro_voice") or "am_michael")
        use_kokoro = tts_engine == "kokoro" and resolve_kokoro_voice(lang, kokoro_voice)
        if use_kokoro:
            wav_paths = [work_dir / f"general_scene_{index}.wav" for index in missing_audio]
            spoken_texts = [prepare_speech_text_and_tone(texts_by_index[index], lang)[0] for index in missing_audio]
            generate_kokoro_batch(
                spoken_texts, wav_paths, lang, kokoro_voice, _get_kokoro_speed(job_data),
            )
            for index, wav_path in zip(missing_audio, wav_paths):
                audio_paths[index] = wav_path
        else:
            if tts_engine == "kokoro":
                print(f"[Worker-General] Kokoro '{lang}' dilini desteklemiyor; Edge TTS kullanılacak.")
            for index in missing_audio:
                text, rate, pitch = prepare_speech_text_and_tone(texts_by_index[index], lang)
                edge_path = work_dir / f"general_scene_{index}.mp3"
                generate_speech(text, voice_cfg["narrator"], str(edge_path), rate=rate, pitch=pitch)
                audio_paths[index] = edge_path

    normalized_audio = {}
    for index, source_path in audio_paths.items():
        output_path = work_dir / f"general_scene_{index}.mp3"
        if source_path != output_path:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(source_path),
                    "-ar", "48000", "-ac", "2", "-codec:a", "libmp3lame",
                    "-b:a", "192k", str(output_path),
                ],
                capture_output=True, check=True,
            )
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError(f"Sahne ses dosyası oluşturulamadı: {output_path.name}")
        normalized_audio[index] = output_path

    width_height_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1"
    )

    channel_cfg = job_data.get("channel_config") or {}
    category = str(channel_cfg.get("topic_category") or job_data.get("topic_category") or "travel").lower()
    topic = script.get("title") or job_data.get("title") or "Travel"
    edit_opts = channel_cfg.get("edit_options") or {}
    is_shorts = bool(channel_cfg.get("shorts_mode", True))
    used_media_registry = set()

    # 1. Saf Dış Ses Kanalını Birleştir (Clean Voiceover Track)
    audio_concat_file = work_dir / "general_audio_concat.txt"
    scene_timeline = []  # [(index, text, start_time, end_time), ...]
    current_time = 0.0

    with audio_concat_file.open("w", encoding="utf-8") as acf:
        for index, text, _payload in entries:
            audio_path = normalized_audio[index]
            dur = _probe_scene_audio_duration(audio_path)
            scene_timeline.append((index, text, current_time, current_time + dur))
            current_time += dur
            acf.write(f"file '{audio_path.resolve()}'\n")

    clean_voiceover = work_dir / "clean_voiceover.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(audio_concat_file),
            "-ar", "48000", "-ac", "2", str(clean_voiceover),
        ],
        capture_output=True, check=True,
    )
    total_audio_dur = _probe_scene_audio_duration(clean_voiceover)
    print(f"[Worker-General] 🎙️ Saf dış ses hazırlandı: {total_audio_dur:.2f} sn ({len(entries)} sahne)")

    # 2. 2.15s Tavanlı Jump-Cut Slicing & Editoryal Fotoğraf Havuzu
    cut_duration = 2.15  # Max 2.4s kuralı gereğince 2.15s standart ritim
    num_cuts = max(1, int(math.ceil(total_audio_dur / cut_duration)))
    print(f"[Worker-General] ✂️ 2.15s Tavanı: {total_audio_dur:.2f} sn süre için {num_cuts} adet dinamik kesme yapılacak.")

    # VisualDirector 6 Kural Sözleşmesi ile Plan Derleme
    try:
        from visual_director import visual_director
    except ImportError:
        try:
            from src.visual_director import visual_director
        except ImportError:
            visual_director = None

    visual_plan = None
    if visual_director is not None:
        try:
            visual_plan = visual_director.generate_visual_timeline(
                topic=topic,
                category=category,
                script_data=script,
                total_duration=total_audio_dur,
            )
            print(f"[Worker-General] 🎬 VisualDirector zaman çizelgesi devrede ({len(visual_plan.get('timeline_scenes', []))} kesme, rozet: '{visual_plan.get('project_meta', {}).get('category_badge')}').")
        except Exception as e_vd:
            print(f"[Worker-General] ⚠️ VisualDirector derleme uyarısı: {e_vd}")

    from real_media_fetcher import fetch_photo_pool
    photo_pool_dir = work_dir / "photo_pool"
    photo_assets = fetch_photo_pool(
        category=category,
        topic=topic,
        script_data=script,
        target_count=num_cuts,
        work_dir=photo_pool_dir,
        target_w=width,
        target_h=height,
        session_used=used_media_registry,
        scene_timeline=scene_timeline,
        cut_duration=cut_duration,
        visual_plan=visual_plan,
    )

    if not photo_assets:
        raise RuntimeError("Fotoğraf havuzundan hiçbir görsel temin edilemedi.")

    # 3. Ken Burns Dinamik Kesmelerini Üret (4 Alternatif Kamera Hareketi)
    cuts_dir = work_dir / "cuts"
    cuts_dir.mkdir(parents=True, exist_ok=True)
    cut_segments = []
    cuts_concat_file = work_dir / "cuts_concat.txt"

    for cut_idx in range(num_cuts):
        seg_dur = min(cut_duration, max(0.5, total_audio_dur - (cut_idx * cut_duration)))
        seg_path = cuts_dir / f"cut_{cut_idx:03d}.mp4"
        photo_path = photo_assets[cut_idx % len(photo_assets)]
        frames = int(round(seg_dur * 25))

        # 4 Farklı Ken Burns Kamera Hareketi:
        # 0: Merkeze Yakınlaşma (ZoomIn 1.0 -> 1.15)
        # 1: Merkezden Uzaklaşma (ZoomOut 1.15 -> 1.0)
        # 2: Soldan Sağa Kayma (PanLeftToRight)
        # 3: Sağdan Sola Kayma (PanRightToLeft)
        mode = cut_idx % 4
        if mode == 0:
            vf_kb = (
                f"scale={width}*1.15:{height}*1.15:force_original_aspect_ratio=increase,"
                f"crop={width}*1.15:{height}*1.15,"
                f"zoompan=z='min(zoom+0.0028,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=25,fps=25,setsar=1"
            )
        elif mode == 1:
            vf_kb = (
                f"scale={width}*1.15:{height}*1.15:force_original_aspect_ratio=increase,"
                f"crop={width}*1.15:{height}*1.15,"
                f"zoompan=z='if(lte(zoom,1.0),1.15,max(1.001,zoom-0.0028))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=25,fps=25,setsar=1"
            )
        elif mode == 2:
            vf_kb = (
                f"scale={width}*1.15:{height}*1.15:force_original_aspect_ratio=increase,"
                f"crop={width}*1.15:{height}*1.15,"
                f"zoompan=z='1.12':x='if(lte(on,1),0,min(x+2.0,iw-iw/zoom))':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=25,fps=25,setsar=1"
            )
        else:
            vf_kb = (
                f"scale={width}*1.15:{height}*1.15:force_original_aspect_ratio=increase,"
                f"crop={width}*1.15:{height}*1.15,"
                f"zoompan=z='1.12':x='if(lte(on,1),iw-iw/zoom,max(0,x-2.0))':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=25,fps=25,setsar=1"
            )

        cmd_cut = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "25", "-i", str(photo_path),
            "-vf", vf_kb,
            "-t", f"{seg_dur:.6f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", "-r", "25", "-an",
            str(seg_path)
        ]
        subprocess.run(cmd_cut, capture_output=True, check=True)
        cut_segments.append(seg_path)

    with cuts_concat_file.open("w", encoding="utf-8") as f_cuts:
        for seg in cut_segments:
            f_cuts.write(f"file '{seg.resolve()}'\n")

    raw_visuals = work_dir / "raw_visuals.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(cuts_concat_file),
            "-c", "copy", "-movflags", "+faststart", str(raw_visuals),
        ],
        capture_output=True, check=True,
    )
    print(f"[Worker-General] 🎞️ {len(cut_segments)} kesmelik görsel master hazırlandı: {raw_visuals.name}")

    # 4. Kategoriye Özel Dinamik Altyazı Motorunu Bağla
    from glassmorphism_subtitles import generate_glassmorphism_subtitles
    enable_hook = bool(edit_opts.get("enable_hyperframes_hook", True))
    hook_badge = edit_opts.get("hyperframes_hook_badge")  # None ise kanal teması otomatik seçer

    sub_concat_txt = generate_glassmorphism_subtitles(
        script=script,
        total_dur=total_audio_dur,
        scratch_dir=work_dir,
        top_badge=hook_badge if enable_hook else None,
        category=category,
        visual_plan=visual_plan,
    )

    subtitled_visuals = work_dir / "subtitled_visuals.mp4"
    print(f"[Worker-General] ✨ Glassmorphism altyazı katmanı videoya işleniyor...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(raw_visuals),
            "-f", "concat", "-safe", "0", "-i", str(sub_concat_txt),
            "-filter_complex", "[0:v][1:v]overlay=0:0:eof_action=pass[v_out]",
            "-map", "[v_out]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            str(subtitled_visuals)
        ],
        capture_output=True, check=True,
    )

    # 5. Fon Müziği (BGM) & Ses Miksajı (0.5s Smooth Fadeout)
    bgm_file = None
    music_dir = BASE_DIR / "assets" / "music"
    bgm_tl = script.get("bgm_timeline") or []
    if bgm_tl and isinstance(bgm_tl, list) and len(bgm_tl) > 0:
        t_id = bgm_tl[0].get("track_id")
        if t_id:
            cand = music_dir / f"{t_id}.mp3"
            if cand.is_file():
                bgm_file = cand
    if not bgm_file:
        genre = str(edit_opts.get("music_genre") or "").lower()
        if "travel" in genre or "acoustic" in genre:
            cand = music_dir / "sunny_days.mp3"
            if cand.is_file():
                bgm_file = cand

    output_video = work_dir / "final_video.mp4"
    fade_start = max(0.0, total_audio_dur - 0.5)

    if bgm_file and bgm_file.is_file():
        bgm_vol = float(edit_opts.get("bgm_volume") or 0.12)
        print(f"[Worker-General] 🎵 Dış ses + BGM miksleniyor ({bgm_file.name}, vol={bgm_vol:.2f}, fade_start={fade_start:.2f}s)...")
        sub_cmd = [
            "ffmpeg", "-y",
            "-i", str(subtitled_visuals),
            "-i", str(clean_voiceover),
            "-stream_loop", "-1", "-i", str(bgm_file),
            "-filter_complex", (
                f"[1:a]volume=1.0[v_aud];"
                f"[2:a]volume={bgm_vol:.2f},afade=t=out:st={fade_start:.2f}:d=0.5[b_aud];"
                f"[v_aud][b_aud]amix=inputs=2:duration=first:dropout_transition=2,afade=t=out:st={fade_start:.2f}:d=0.5[a_out]"
            ),
            "-map", "0:v",
            "-map", "[a_out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total_audio_dur:.3f}",
            "-movflags", "+faststart",
            str(output_video)
        ]
    else:
        print(f"[Worker-General] 🎙️ Sadece saf dış ses miksleniyor...")
        sub_cmd = [
            "ffmpeg", "-y",
            "-i", str(subtitled_visuals),
            "-i", str(clean_voiceover),
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total_audio_dur:.3f}",
            "-movflags", "+faststart",
            str(output_video)
        ]

    subprocess.run(sub_cmd, capture_output=True, check=True)

    if not output_video.is_file() or output_video.stat().st_size == 0:
        raise RuntimeError("Sahne eşlemeli genel video üretilemedi.")
    return output_video


def render_general_job(job_data: dict, work_dir: Path) -> Path:
    channel_id = job_data.get("channel_id", "general")
    script = job_data.get("script_data") or job_data.get("script") or {}
    channel_cfg = job_data.get("channel_config") or {}
    lang = (channel_cfg.get("language") or "tr").lower()
    voice_cfg = VOICE_MAP.get(lang, VOICE_MAP["tr"])
    is_shorts = bool(channel_cfg.get("shorts_mode", True))
    
    W = 1080 if is_shorts else 1920
    H = 1920 if is_shorts else 1080

    # Senaryoyu hedef kanalın diline otomatik yerelleştir
    script = ensure_localized_script(script, lang)

    scenes = script.get("scenes") or []
    if scenes and isinstance(scenes, list):
        narrations = [s.get("narration") or s.get("text") or "" for s in scenes if s.get("narration") or s.get("text")]
        content_text = " ".join(narrations)
    else:
        content_text = script.get("narration") or script.get("story") or script.get("body") or script.get("title", "")

    if isinstance(content_text, list):
        content_text = " ".join(content_text)
    if not content_text:
        content_text = script.get("title") or channel_id

    custom_audios = job_data.get("custom_audios") or {}
    legacy_full_track = any(key in custom_audios for key in ("voiceover", "main"))
    if not legacy_full_track and scenes and not _has_per_scene_audio(custom_audios, len(scenes)):
        numeric_audio_keys = {str(key) for key in custom_audios if str(key).isdigit()}
        legacy_full_track = numeric_audio_keys == {"0"}
    if scenes and not legacy_full_track:
        return _render_scene_aligned_general(
            job_data, script, scenes, work_dir, lang, voice_cfg, W, H,
        )

    audio_file = work_dir / "voiceover.mp3"
    used_custom = False
    if custom_audios:
        for k in ["0", "voiceover", "scene_0", "main"]:
            if k in custom_audios:
                try:
                    raw_aud = custom_audios[k]
                    if "," in raw_aud:
                        raw_aud = raw_aud.split(",", 1)[1]
                    aud_bytes = base64.b64decode(raw_aud)
                    audio_file.write_bytes(aud_bytes)
                    used_custom = True
                    print(f"[Worker-General] 🎙️ Stüdyo kalitesinde klon seslendirmesi kullanıldı.")
                    break
                except Exception as e_ca:
                    print(f"[Worker-General] ⚠️ Özel ses çözme uyarısı: {e_ca}")

    if not used_custom:
        spoken_text, rate, pitch = prepare_speech_text_and_tone(content_text, lang)
        tts_engine = str(job_data.get("tts_engine") or "kokoro").lower()
        if tts_engine == "kokoro":
            if resolve_kokoro_voice(lang, str(job_data.get("kokoro_voice") or "am_michael")):
                print(f"[Worker] Kokoro-TTS ile seslendiriliyor ({lang}, {job_data.get('kokoro_voice') or 'am_michael'})...")
                generate_kokoro_batch(
                    [spoken_text],
                    [work_dir / "voiceover.wav"],
                    lang,
                    str(job_data.get("kokoro_voice") or "am_michael"),
                    _get_kokoro_speed(job_data),
                )
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(work_dir / "voiceover.wav"), "-codec:a", "libmp3lame", "-b:a", "192k", str(audio_file)],
                    capture_output=True, check=True,
                )
            else:
                print(f"[Worker] Kokoro '{lang}' dilini desteklemiyor; Edge TTS kullanılıyor.")
                generate_speech(spoken_text, voice_cfg["narrator"], str(audio_file), rate=rate, pitch=pitch)
        else:
            print(f"[Worker] Seslendirme üretiliyor ({voice_cfg['narrator']}, rate={rate}, pitch={pitch})...")
            generate_speech(spoken_text, voice_cfg["narrator"], str(audio_file), rate=rate, pitch=pitch)

    dur = get_media_duration(str(audio_file))
    output_video = work_dir / "final_video.mp4"
    title_text = (script.get("title") or channel_id).replace("'", "").replace(":", "")[:60]

    # 1. Custom Images (Materyal görselleri) varsa decode et ve kullan
    custom_images = job_data.get("custom_images") or {}
    image_files = []
    if custom_images and isinstance(custom_images, dict):
        for k in sorted(custom_images.keys(), key=lambda x: int(x) if str(x).isdigit() else 999):
            if k == "avatar":
                continue
            val = custom_images[k]
            if not val:
                continue
            out_img = work_dir / f"scene_img_{k}.jpg"
            if isinstance(val, str) and "data:image" in val and "," in val:
                try:
                    b64_data = val.split(",", 1)[1]
                    out_img.write_bytes(base64.b64decode(b64_data))
                    image_files.append(out_img)
                except Exception as e_im:
                    print(f"[Worker-General] Görsel çözme uyarısı ({k}): {e_im}")
            elif isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
                try:
                    import urllib.request
                    req = urllib.request.Request(val, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        out_img.write_bytes(resp.read())
                    image_files.append(out_img)
                except Exception as e_dl:
                    print(f"[Worker-General] Görsel indirme uyarısı ({k}): {e_dl}")
            elif isinstance(val, str) and os.path.exists(val):
                image_files.append(Path(val))

    # 2. Eğer görseller mevcutsa gerçek slideshow oluştur (Ken Burns & dikey 9:16)
    if image_files:
        print(f"[Worker-General] 🖼️ {len(image_files)} adet materyal görseli ile video montajı yapılıyor...")
        if scenes and legacy_full_track:
            scene_durations = _allocate_legacy_scene_durations(scenes, dur)
            segment_images = [
                image_files[min(index, len(image_files) - 1)]
                for index in range(len(scene_durations))
            ]
            segment_durations = scene_durations
        else:
            segment_images = image_files
            segment_durations = [dur / len(image_files)] * len(image_files)
        seg_list = []
        concat_file = work_dir / "general_concat.txt"
        for idx_img, (img_p, sc_dur) in enumerate(zip(segment_images, segment_durations)):
            seg_out = work_dir / f"gen_seg_{idx_img}.ts"
            frames = int(round(sc_dur * 25))
            cmd_s = [
                "ffmpeg", "-y", "-loop", "1", "-i", str(img_p),
                "-t", f"{sc_dur:.2f}",
                "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},zoompan=z='min(zoom+0.0006,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=25,fps=25,setsar=1",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                "-an", str(seg_out)
            ]
            res_s = subprocess.run(cmd_s, capture_output=True)
            if res_s.returncode == 0 and seg_out.exists():
                seg_list.append(seg_out)

        if seg_list:
            with open(concat_file, "w") as f_c:
                for s_item in seg_list:
                    f_c.write(f"file '{s_item.name}'\n")

            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_file),
                "-i", str(audio_file),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest", str(output_video)
            ]
            subprocess.run(ffmpeg_cmd, capture_output=True, check=True, cwd=str(work_dir))
            for s_item in seg_list:
                try: s_item.unlink()
                except Exception: pass
            try: concat_file.unlink()
            except Exception: pass
            return output_video

    # 3. Görsel yoksa fallback (solid arka plan)
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x0f172a:s={W}x{H}:d={dur + 1.0}",
        "-i", str(audio_file),
        "-vf", f"drawtext=text='{title_text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.6:boxborderw=20",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(output_video)
    ]
    subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
    return output_video


# ─────────────────────────────────────────────────────────────
# 5. YouTube API Yükleme ve Sunucudan Silme Motoru
# ─────────────────────────────────────────────────────────────
def handle_youtube_upload(job_data: dict, video_path: Path) -> dict:
    from youtube_uploader_api import YouTubeUploaderAPI

    channel_id = job_data.get("channel_id", "")
    script = job_data.get("script_data", {})
    title = script.get("title") or f"Shorts #{job_data.get('row_id', '1')}"
    desc = script.get("description") or "#Shorts #Viral #Trending"
    tags = script.get("tags") or ["Shorts", "Viral"]

    uploader = YouTubeUploaderAPI(credentials_dir=str(CREDENTIALS_DIR))
    
    print(f"[Worker] YouTube API yükleme ve akıllı zamanlama başlatılıyor: {channel_id}...")
    res = uploader.upload_and_schedule(
        channel_id=channel_id,
        video_path=str(video_path),
        title=title,
        description=desc,
        tags=tags,
        category="entertainment",
        thumbnail_path=job_data.get("thumbnail_path"),
        auto_cleanup=True, # Sunucudan yüklenen videoyu sil
        channel_config=job_data.get("channel_config")
    )
    return res


# ─────────────────────────────────────────────────────────────
# 6. Ana Görev Yöneticisi (Main Execution)
# ─────────────────────────────────────────────────────────────
def run_job(job_file: Path, force_rebuild: bool = False):
    if not job_file.exists():
        print(f"❌ Görev dosyası bulunamadı: {job_file}")
        sys.exit(1)

    job_data = json.loads(job_file.read_text(encoding="utf-8"))
    job_id = job_data.get("job_id", f"job_{int(time.time())}")
    channel_id = job_data.get("channel_id", "default")
    topic_category = str(job_data.get("channel_config", {}).get("topic_category", "")).lower()
    force_rebuild = force_rebuild or job_data.get("force_rebuild", False)

    status_file = JOBS_DIR / f"{job_id}_status.json"
    
    def update_status(status: str, progress: int, msg: str, extra: dict = None):
        payload = {
            "job_id": job_id,
            "channel_id": channel_id,
            "status": status,
            "progress": progress,
            "message": msg,
            "timestamp": datetime.now().isoformat(),
        }
        if extra:
            payload.update(extra)
        status_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    work_dir = OUTPUT_BASE / channel_id / job_id
    
    # ── PROJE BAZLI ÇALIŞMA ALANI İZOLASYONU (Job-Level Sandboxing) ──
    # Her iş emri için izole çalışma dizini ve alt klasörleri
    workspace_dir = BASE_DIR / "workspace" / job_id
    job_data["workspace_dir"] = str(workspace_dir)

    if force_rebuild:
        print(f"[Worker] 🔄 --force-rebuild aktif: {job_id} çalışma alanı ve eski çıktılar sıfırlanıyor...")
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir, ignore_errors=True)
        if work_dir.exists():
            for sub_d in ["photo_pool", "cuts", "glass_sub_cards", "broll_pool"]:
                target_sub = work_dir / sub_d
                if target_sub.exists():
                    shutil.rmtree(target_sub, ignore_errors=True)
            for f in work_dir.glob("*.mp4"):
                try: f.unlink()
                except Exception: pass
            for f in work_dir.glob("raw_*"):
                try: f.unlink()
                except Exception: pass
            for f in work_dir.glob("*_concat.txt"):
                try: f.unlink()
                except Exception: pass

    work_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "downloads").mkdir(parents=True, exist_ok=True)
    (workspace_dir / "photo_pool").mkdir(parents=True, exist_ok=True)
    (workspace_dir / "cuts").mkdir(parents=True, exist_ok=True)

    try:
        update_status("running", 10, "İşlem başlatıldı, parametreler hazırlandı...")

        # 1. Kategoriye göre video üretimi
        is_whatsapp = (
            "whatsapp" in topic_category or
            "whatsapp" in str(job_data.get("channel_type", "")).lower() or
            "whatsapp" in str(job_data.get("category", "")).lower() or
            "yazan" in channel_id.lower() or
            "crazy" in channel_id.lower() or
            bool(job_data.get("script_data", {}).get("messages")) or
            bool(job_data.get("script", {}).get("messages"))
        )
        is_reddit = (
            "reddit" in topic_category or
            "reddit" in channel_id.lower() or
            "reddit" in str(job_data.get("category", "")).lower() or
            bool(job_data.get("script_data", {}).get("question")) or
            bool(job_data.get("script", {}).get("question"))
        )
        is_aviation = (
            "aviation" in topic_category or
            "blackbox" in topic_category or
            "blackbox" in channel_id.lower() or
            "flight" in channel_id.lower() or
            "aviation" in channel_id.lower()
        )
        is_crayon = (
            topic_category == "crayon_combat" or
            any(key in channel_id.lower() for key in ("tacticallcrayon", "tacticalcrayon"))
        )
        is_sports = (
            "basketball" in topic_category or
            "sports" in topic_category or
            "basketball" in channel_id.lower() or
            "sports" in channel_id.lower() or
            "thebasketballshows" in channel_id.lower()
        )
        if is_whatsapp:
            update_status("rendering", 30, "WhatsApp sohbet sesleri ve Remotion render yapılıyor...")
            video_file = render_whatsapp_job(job_data, work_dir)
        elif is_reddit:
            update_status("rendering", 30, "Reddit hikaye sesleri ve Remotion render yapılıyor...")
            video_file = render_reddit_job(job_data, work_dir)
        elif is_crayon:
            update_status("rendering", 30, "Tactical Crayon animasyonlu video render ediliyor...")
            video_file = render_crayon_job(job_data, work_dir)
        elif is_aviation:
            update_status("rendering", 30, "Havacılık belgeseli, 16:9 Pixabay video/arşiv ve altyazı render yapılıyor...")
            video_file = render_aviation_job(job_data, work_dir)
        elif is_sports:
            update_status("rendering", 30, "🏀 Spor/NBA dinamik jump-cut, gerçek arşiv görselleri ve altyazı render yapılıyor...")
            from sports_shorts_engine import render_sports_shorts_job
            video_file = render_sports_shorts_job(job_data, work_dir, workspace_dir=workspace_dir, force_rebuild=force_rebuild)
        else:
            update_status("rendering", 30, f"{topic_category} formatında video üretiliyor...")
            video_file = render_general_job(job_data, work_dir)

        if not video_file.exists():
            raise RuntimeError("Video dosyası üretilemedi.")

        # Metadata ve video bilgi dosyalarını kaydet (Mac indirmesi ve listeleme için)
        script = job_data.get("script_data") or job_data.get("script") or {}

        # Evrensel Transparan Sosyal CTA (Abone Ol + Beğen + Bildirim) Katmanı
        try:
            from social_cta_overlay import apply_social_cta_overlay
            cta_lang = str(job_data.get("language") or script.get("language") or "en").lower()
            update_status("rendering", 92, f"Transparan Abone Ol & Beğen CTA katmanı ekleniyor ({cta_lang})...")
            
            # Proje bazlı özel CTA zamanlaması (Altyazı ve tartışma kancasını örtmez)
            topic_combined = f"{script.get('title', '')} {job_data.get('title', '')}".lower()
            cta_start = None
            cta_dur = None
            if "fisher" in topic_combined or "0.4" in topic_combined:
                cta_start = 49.0
                cta_dur = 3.0
            elif "harden" in topic_combined or "deceleration" in topic_combined:
                cta_start = 44.5
                cta_dur = 2.5

            apply_social_cta_overlay(
                video_file, video_file,
                language=cta_lang,
                show_at_start=False,
                show_at_end=True,
                start_time=cta_start,
                display_duration=cta_dur
            )
        except Exception as e_cta:
            print(f"[Worker] ⚠️ Social CTA overlay uyarısı: {e_cta}")

        title = script.get("title") or f"Shorts #{job_data.get('row_id', '1')}"
        desc = script.get("description") or "#Shorts #Viral #Trending"
        tags = script.get("tags") or ["Shorts", "Viral"]
        size_mb = round(video_file.stat().st_size / (1024 * 1024), 2)
        vid_dur = round(get_media_duration(str(video_file)), 1)

        meta_obj = {
            "title": title,
            "description": desc,
            "tags": tags,
            "channel_id": channel_id,
            "job_id": job_id,
            "row_id": job_data.get("row_id"),
            "duration": vid_dur,
            "file_size_mb": size_mb,
            "thumbnail_path": job_data.get("thumbnail_path"),
            "bgm_track": job_data.get("selected_bgm", "reddit_official_bgm.mp3" if is_reddit else "monkeys_spinning.mp3" if is_whatsapp else ""),
            "bgm_volume": 0.06 if is_reddit else 0.05,
            "created_at": datetime.now().isoformat()
        }
        (work_dir / "metadata.json").write_text(json.dumps(meta_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        (work_dir / "video_info.json").write_text(json.dumps({
            "title": title,
            "video_path": str(video_file),
            "file_size_mb": size_mb,
            "duration": vid_dur,
            "created_at": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        update_status("rendered", 80, "Video başarıyla üretildi.", {
            "title": title,
            "video_path": str(video_file),
            "video_size_mb": size_mb
        })

        # 2. YouTube Resmi API Yüklemesi & Sunucu Temizliği
        upload_result = None
        if job_data.get("youtube_upload", False):
            # Sunucudan doğrudan yükleme yapılıyorsa fon müziğini videoya miksle
            bgm_track = meta_obj.get("bgm_track")
            if bgm_track:
                bgm_file = pub_media / bgm_track
                if not bgm_file.exists():
                    bgm_file = BASE_DIR / "assets" / "music" / bgm_track
                if bgm_file.exists():
                    temp_mixed = work_dir / "final_with_bgm.mp4"
                    cmd_mix = [
                        "ffmpeg", "-y",
                        "-i", str(video_file),
                        "-stream_loop", "-1", "-i", str(bgm_file),
                        "-filter_complex", (
                            f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[v];"
                            f"[1:a]volume={meta_obj.get('bgm_volume', 0.06)}[b];"
                            f"[v][b]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
                        ),
                        "-c:v", "copy",
                        "-map", "0:v:0",
                        "-map", "[aout]",
                        "-c:a", "aac", "-b:a", "192k",
                        "-shortest",
                        str(temp_mixed)
                    ]
                    subprocess.run(cmd_mix, capture_output=True)
                    if temp_mixed.exists() and temp_mixed.stat().st_size > 1000:
                        shutil.move(str(temp_mixed), str(video_file))

            update_status("uploading", 85, "Resmi YouTube API ile zamanlanıyor ve yükleniyor...")
            upload_result = handle_youtube_upload(job_data, video_file)
            update_status("completed", 100, "Video başarıyla YouTube'a yüklendi, zamanlandı ve sunucudaki dosya silindi.", {
                "upload_result": upload_result
            })
        else:
            update_status("completed", 100, "Video başarıyla sunucuda üretildi.", {
                "title": title,
                "video_path": str(video_file),
                "file_size_mb": size_mb
            })

        print(f"🎉 [Worker] Görev başarıyla tamamlandı: {job_id}")

    except Exception as err:
        import traceback
        tb = traceback.format_exc()
        print(f"❌ [Worker] Hata: {err}\n{tb}")
        update_status("failed", 100, f"Hata: {str(err)}", {"traceback": tb})
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, help="Job JSON dosyası yolu")
    parser.add_argument("--force-rebuild", action="store_true", help="Var olan çıktı ve çalışma alanını sıfırdan yeniden oluşturur")
    args = parser.parse_args()
    run_job(Path(args.job), force_rebuild=args.force_rebuild)
