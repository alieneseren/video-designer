"""
src/connectome/lm_studio.py
LM Studio Yerel Yapay Zeka Bağlantısı (Sinek Beyni Biyo-AI Müzik Metin Yazarı)
- 139.255 Drosophila nöronunun piyano/senfoni simülasyonu için:
  1. Başlık (Title)
  2. İlk 3 saniye kanca cümlesi (Hook Caption)
  3. YouTube & Sosyal Medya Açıklaması (Description)
  4. Etiketler & Hashtagler (Tags)
- LM Studio (http://localhost:1234/v1) üzerinden çalışır; kapalıysa akıllı şablonlara veya Gemini'ye düşer.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

DEFAULT_LM_STUDIO_URL = "http://localhost:1234/v1"


def get_active_lm_studio_model(base_url: str = DEFAULT_LM_STUDIO_URL) -> Tuple[bool, Optional[str]]:
    """LM Studio'nun açık olup olmadığını kontrol eder ve yüklü model adını döner."""
    try:
        req = urllib.request.Request(f"{base_url}/models", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", [])
                if models and len(models) > 0:
                    return True, models[0].get("id")
                return True, "default"
    except Exception:
        pass
    return False, None


def call_lm_studio_chat(
    prompt: str,
    system_prompt: str = "",
    base_url: str = DEFAULT_LM_STUDIO_URL,
    model: Optional[str] = None,
    max_tokens: int = 600,
    temperature: float = 0.7
) -> Optional[str]:
    """LM Studio chat completions uç noktasına istek atar."""
    is_online, active_model = get_active_lm_studio_model(base_url)
    if not is_online:
        return None

    target_model = model or active_model or "google/gemma-3-12b"

    payload = {
        "model": target_model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt or "You are an avant-garde bio-music creative director, neuroscientist, and viral YouTube/TikTok copywriter."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            choices = res_data.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "").strip()
    except Exception as e:
        print(f"[LM-STUDIO] İstek hatası: {e}")
    return None


def generate_music_copywriting(
    track_info: Dict[str, Any],
    language: str = "tr",
    base_url: str = DEFAULT_LM_STUDIO_URL
) -> Dict[str, Any]:
    """
    Parça bilgilerine ve hedef dile göre viral başlık, açıklama ve etiketler üretir.
    """
    lang = (language or "tr").lower().strip()
    lang_name = "Turkish" if lang == "tr" else ("German" if lang == "de" else ("Spanish" if lang == "es" else "English"))

    title = track_info.get("title", "Synaptic Resonance")
    genre_name = track_info.get("genre_name", "Emotional & Melancholic (Nocturne)")
    scale = track_info.get("scale", "F Minor")
    bpm = track_info.get("bpm", 88)
    spikes = track_info.get("totalSpikes", 450)
    duration = track_info.get("durationSec", 180)

    prompt = f"""We generated a bio-AI music and video clip where real biological action potentials of 139,255 Drosophila melanogaster (fruit fly) brain neurons directly trigger neo-classical grand piano, warm cello, and orchestral harmonics.

Track Details:
- Working Title: "{title}"
- Genre: "{genre_name}"
- Musical Scale: "{scale}"
- Tempo: {bpm} BPM
- Total Biological Neural Spikes: {spikes}
- Duration: {duration:.0f} seconds
- Dataset: Princeton FlyWire Consortium (Whole-brain Drosophila connectome)

TASK:
Write captivating, viral YouTube & social media publishing copy strictly in {lang_name} ({lang.upper()}).
Return ONLY a valid JSON object matching this schema (NO explanation outside JSON):
{{
  "recommended_title": "High CTR viral YouTube title in {lang_name} (max 70 characters)",
  "alternative_titles": [
    "Catchy alternative title 1 in {lang_name}",
    "Catchy alternative title 2 in {lang_name}"
  ],
  "hook_caption": "1 compelling on-screen sentence in {lang_name} for the first 3 seconds",
  "description": "Engaging, scientific and artistic description in {lang_name} formatted with emojis, mentioning the 139,255 fruit fly neurons and FlyWire project, with a call to subscribe",
  "tags": ["Tag1", "Tag2", "Tag3", "Tag4", "Tag5", "Tag6", "Tag7", "Tag8"]
}}"""

    response = call_lm_studio_chat(prompt, base_url=base_url)

    if response:
        try:
            clean_json = response
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean_json)
            if parsed.get("recommended_title") and parsed.get("description"):
                print(f"[LM-STUDIO] ✅ Yapay Zeka Metinleri Üretti: '{parsed.get('recommended_title')}'")
                return {
                    "title": parsed["recommended_title"],
                    "hook": parsed.get("hook_caption", ""),
                    "description": parsed["description"],
                    "tags": parsed.get("tags", []),
                    "alternative_titles": parsed.get("alternative_titles", []),
                    "ai_source": "lm_studio"
                }
        except Exception as parse_err:
            print(f"[LM-STUDIO] Yanıt parse hatası ({parse_err}), şablona geçiliyor.")

    # Fallback Curated Templates by Language
    print(f"[LM-STUDIO] Çevrimdışı/Şablon modu devrede (Dil: {lang}).")
    if lang == "tr":
        rec_title = f"139.000 Canlı Beyin Hücresi Piyano Çalarsa 🧠🎹 ({title})"
        desc = f"""Bu eser, Drosophila melanogaster (meyve sineği) beyninin 139.255 nöronluk gerçek konnektom haritasındaki biyolojik sinaps ateşlemelerinden üretilmiştir. Duyduğunuz her piyano notası ve çello harmonisi, gerçek bir nöronun aksiyon potansiyeline karşılık gelmektedir.

🔬 SİMÜLASYON VERİLERİ:
• Parça: {title}
• Tür: {genre_name}
• Müzik Skalası: {scale}
• Tempo: {bpm} BPM
• Ateşlenen Sinaps: {spikes} Nöral Spike
• Süre: {duration:.0f} saniye
• Konnektom Kaynağı: Princeton FlyWire Konsorsiyumu

Bilim ve avangart sanatın buluştuğu bu eşsiz biyo-yapay zeka deneyimini beğendiyseniz abone olmayı ve bildirimleri açmayı unutmayın! 🔔

#Müzik #YapayZeka #Nörobilim #Piyano #BiyoAI #Drosophila #Connectome #FlyWire #Shorts #Viral #KlasikMüzik"""
        tags = ["Müzik", "Piyano", "YapayZeka", "Nörobilim", "BiyoAI", "Drosophila", "Connectome", "FlyWire", "Shorts", "Viral", "KlasikMüzik"]
        hook = "Bu müzik yapay zeka bestesi değil; 139.255 canlı beyin nöronunun sinaptik ateşlemeleridir."
    else:
        rec_title = f"What 139,000 Insect Neurons Sound Like Playing Piano 🧠🎹 ({title})"
        desc = f"""This composition was synthesized directly from the real whole-brain connectome of Drosophila melanogaster (fruit fly). Every acoustic piano strike and cello swell corresponds to genuine biological action potentials recorded across 139,255 living neurons.

🔬 SIMULATION TELEMETRY:
• Track: {title}
• Genre: {genre_name}
• Musical Key: {scale}
• Tempo: {bpm} BPM
• Neural Spikes: {spikes} Biological Spikes
• Duration: {duration:.0f}s
• Connectome Dataset: Princeton FlyWire Consortium

What does biological brain music make you feel? Drop a comment below and subscribe for daily bio-AI releases! 🔔

#Music #BioAI #Neuroscience #Piano #AI #Connectome #FlyWire #Drosophila #Ambient #Classical #Shorts #Viral"""
        tags = ["Music", "Piano", "BioAI", "Neuroscience", "AI", "Connectome", "FlyWire", "Drosophila", "Ambient", "Classical", "Shorts", "Viral"]
        hook = "This music isn't AI-composed—it's generated live from the real synaptic spikes of 139,255 fruit fly brain neurons."

    return {
        "title": rec_title,
        "hook": hook,
        "description": desc,
        "tags": tags,
        "alternative_titles": [rec_title],
        "ai_source": "template_fallback"
    }
