"""
localization_helper.py
======================
Çok dilli kanal grupları ve video üretimleri için otomatik senaryo yerelleştirme (localization) ve çeviri motoru.
Google Translate altyapısı ile harici API anahtarına ihtiyaç duymadan sıfır gecikmeyle çalışır.
"""

from __future__ import annotations

import copy
import json
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

_TRANSLATE_CACHE: Dict[Tuple[str, str, str], Tuple[str, str]] = {}


def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> Tuple[str, str]:
    """
    Verilen metni hedef dile çevirir.
    Dönüş: (çevrilen_metin, tespit_edilen_kaynak_dil)
    """
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
        print(f"[Localization] ⚠️ Çeviri uyarısı ({target_lang}): {e}")
        return text_str, "unknown"


def detect_language(text: str) -> str:
    """Verilen metnin dilini otomatik tespit eder."""
    if not text or not str(text).strip():
        return "tr"
    _, det = translate_text(text[:250], "en", "auto")
    return det if det and det != "unknown" else "tr"


def ensure_localized_script(script_data: Dict[str, Any], target_lang: str, channel_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Verilen senaryoyu hedef kanala (target_lang) göre yerelleştirir.
    - Eğer senaryo zaten çok dilli bir harita ise (ör: {"tr": {...}, "en": {...}}), hedef dili döndürür.
    - Eğer tek dilli ise ve hedef dil ile uyuşmuyorsa başlık, soru, sahneler ve mesajları hedef dile çevirir.
    """
    if not isinstance(script_data, dict):
        return script_data

    target_lang = (target_lang or "tr").lower().strip()

    # 1. Senaryo zaten çok dilli sözlük mü?
    if target_lang in script_data and isinstance(script_data[target_lang], dict):
        res = copy.deepcopy(script_data[target_lang])
        res["language"] = target_lang
        return res

    if "scripts" in script_data and isinstance(script_data["scripts"], dict) and target_lang in script_data["scripts"]:
        res = copy.deepcopy(script_data["scripts"][target_lang])
        res["language"] = target_lang
        return res

    # 2. Tek dilli veya karışık sahneli senaryo çözümlemesi
    candidate = copy.deepcopy(script_data)

    # Eğer tek dilli ama dil anahtarları varsa (örneğin sadece 'tr' var ama 'en' isteniyor)
    for lk in ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko"]:
        if lk in candidate and isinstance(candidate[lk], dict) and ("scenes" in candidate[lk] or "messages" in candidate[lk] or "narration" in candidate[lk]):
            candidate = copy.deepcopy(candidate[lk])
            break

    # 2.1 Sahnelerde çok dilli / ardışık dilli blok kontrolü (ör: 7 İngilizce + 7 Türkçe sahne)
    raw_scenes = candidate.get("scenes")
    scenes_key = "scenes"
    if not raw_scenes and isinstance(candidate.get("scripts"), list):
        raw_scenes = candidate["scripts"]
        scenes_key = "scripts"

    if raw_scenes and isinstance(raw_scenes, list) and len(raw_scenes) > 0:
        matching_scenes = [
            s for s in raw_scenes
            if isinstance(s, dict) and detect_language(s.get("narration") or s.get("text") or "") == target_lang
        ]
        # Eğer sahneler içinde hedef dile tam uyan bir grup varsa (ör: 14 sahnenin 7'si hedef dildeyse)
        if len(matching_scenes) >= 3 and len(matching_scenes) < len(raw_scenes):
            print(f"[Localization] 🎯 Karışık sahnelerden '{target_lang}' diline ait {len(matching_scenes)} sahne başarıyla ayrıştırıldı.")
            for idx, s in enumerate(matching_scenes):
                s["scene_id"] = idx + 1
            candidate[scenes_key] = matching_scenes
            if scenes_key == "scripts":
                candidate["scenes"] = matching_scenes

    # Örnek metin üzerinden dil tespiti yap
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

    # Eğer ana metin dili hedef dil ile aynıysa ve sahneler de hedef dildeyse döndür
    scenes_clean = True
    if candidate.get("scenes") and isinstance(candidate["scenes"], list) and len(candidate["scenes"]) > 0:
        first_sc_lang = detect_language(candidate["scenes"][0].get("narration") or candidate["scenes"][0].get("text") or "")
        if first_sc_lang != target_lang:
            scenes_clean = False

    if detected_src and detected_src.lower().strip() == target_lang and scenes_clean:
        candidate["language"] = target_lang
        return candidate

    print(f"[Localization] 🌐 Senaryo yerelleştiriliyor: '{detected_src or 'auto'}' -> '{target_lang}'...")

    # 3. Başlık, Soru, Açıklama ve Kişi Adı çevirileri
    if candidate.get("title"):
        trans_title, _ = translate_text(candidate["title"], target_lang)
        candidate["title"] = trans_title

    if candidate.get("question"):
        trans_q, _ = translate_text(candidate["question"], target_lang)
        candidate["question"] = trans_q

    if candidate.get("description"):
        trans_desc, _ = translate_text(candidate["description"], target_lang)
        candidate["description"] = trans_desc

    if candidate.get("search_optimized_description"):
        trans_sdesc, _ = translate_text(candidate["search_optimized_description"], target_lang)
        candidate["search_optimized_description"] = trans_sdesc

    if candidate.get("contact_name") and candidate["contact_name"].lower() in ["annem ❤️", "babam 👑", "patron 🏢", "kardeşim"]:
        # Tanıdık hitapları doğal yerelleştir
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

    # 4. Sahneler (Reddit veya Genel video)
    if "scenes" in candidate and isinstance(candidate["scenes"], list):
        for s in candidate["scenes"]:
            if isinstance(s, dict):
                for k in ["narration", "text", "dialogue"]:
                    if s.get(k):
                        trans_val, _ = translate_text(s[k], target_lang)
                        s[k] = trans_val

    # 5. Mesajlar (WhatsApp)
    if "messages" in candidate and isinstance(candidate["messages"], list):
        for m in candidate["messages"]:
            if isinstance(m, dict) and m.get("text"):
                trans_m, _ = translate_text(m["text"], target_lang)
                m["text"] = trans_m

    # 6. Etiketler (Tags)
    if "tags" in candidate and isinstance(candidate["tags"], list):
        localized_tags = []
        for tg in candidate["tags"]:
            trans_tg, _ = translate_text(tg, target_lang)
            localized_tags.append(trans_tg)
        candidate["tags"] = localized_tags

    # Subreddit ayarı
    if "subreddit" in candidate:
        if target_lang == "tr":
            if candidate["subreddit"] in ("r/AskReddit", "r/reddit"):
                candidate["subreddit"] = "r/RedditHikayeleri"
        else:
            if "turk" in candidate["subreddit"].lower() or "hikaye" in candidate["subreddit"].lower():
                candidate["subreddit"] = "r/AskReddit"

    candidate["language"] = target_lang
    print(f"[Localization] ✅ Senaryo '{target_lang.upper()}' diline başarıyla yerelleştirildi. Başlık: {candidate.get('title')}")
    return candidate
