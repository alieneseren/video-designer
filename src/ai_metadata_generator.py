"""
ai_metadata_generator.py
========================
Yerel AI (LM Studio / Ollama / Fallback) ile Otonom YouTube Metadata Optimizasyonu.
Reddit hikayeleri, WhatsApp diyalogları ve diğer tüm kanallar için:
- Yüksek CTR (Tıklanma Oranı) sağlayan merak uyandırıcı viral başlıklar
- YouTube arama motoru (SEO) ve algoritmasına tam uyumlu zengin açıklamalar
- Popüler ve hedefe yönelik etiketler (tags) ile hashtagler
- İzleyici etkileşimini (yorum sayısını) maksimize eden sabit yorum (pinned comment)

Aktifleştirme veya ayar gerektirmeden her video üretiminde otomatik olarak çalışır,
video klasöründeki metadata.json ve video_info.json dosyalarını günceller.
"""

import os
import sys
import re
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

import requests

# Proje kök dizinini sys.path'e ekle
PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

try:
    from src.settings_manager import SettingsManager
    from src.channel_manager import ChannelManager, get_localized_metadata
except ImportError:
    from settings_manager import SettingsManager
    from channel_manager import ChannelManager, get_localized_metadata


def _clean_json_response(raw_text: str) -> str:
    """Markdown bloklarından veya serbest metinden geçerli JSON bloğunu ayıklar."""
    text = (raw_text or "").strip()
    # 1. ```json ... ``` bloğu
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        return m.group(1).strip()
    # 2. En dıştaki { ... } bloğu
    m2 = re.search(r"(\{[\s\S]*\})", text)
    if m2:
        return m2.group(1).strip()
    return text


# YouTube Algoritma Koruması: Kanala zarar veren, kitleyi zehirleyen jenerik & spam etiketler
BANNED_TAGS_SET = {
    "shorts", "short", "viral", "trend", "trending", "kesfet", "keşfet",
    "kesfetteyiz", "keşfetteyiz", "fyp", "foryou", "foryoupage", "video",
    "reels", "tiktok", "akim", "akım", "explore"
}


def sanitize_tags(tags: Union[List[str], str]) -> List[str]:
    """Jenerik ve spam etiketleri ayıklar, sadece konuya özel kaliteli ve aranabilir etiketleri korur."""
    if isinstance(tags, str):
        tags_raw = [t.strip() for t in tags.split(",") if t.strip()]
    elif isinstance(tags, list):
        tags_raw = [str(t).strip() for t in tags if str(t).strip()]
    else:
        return []

    cleaned = []
    seen = set()
    for t in tags_raw:
        tag_val = t.replace("#", "").strip()
        norm = tag_val.lower().replace(" ", "")
        if not tag_val or len(tag_val) < 2 or norm in BANNED_TAGS_SET:
            continue
        if norm not in seen:
            seen.add(norm)
            cleaned.append(tag_val)
    return cleaned


def sanitize_hashtags(hashtags: List[str]) -> List[str]:
    """#Shorts, #Viral, #Keşfet gibi kanala zarar veren jenerik hashtagleri temizler."""
    cleaned = []
    seen = set()
    for h in hashtags:
        h_str = str(h).strip()
        if not h_str:
            continue
        if not h_str.startswith("#"):
            h_str = f"#{h_str}"
        norm = h_str.lower().replace("#", "").replace(" ", "")
        if norm in BANNED_TAGS_SET:
            continue
        if norm not in seen:
            seen.add(norm)
            cleaned.append(h_str)
    return cleaned


def extract_video_narration_and_context(video_folder: Path, channel_id: str = "") -> Dict[str, Any]:
    """
    Video klasöründen hikaye/diyalog metnini, sahne bilgilerini ve kanal bağlamını çıkarır.
    Eğer metadata.json içinde metin yoksa, hızlı yerel faster-whisper ile videodan transkribe eder.
    """
    folder = Path(video_folder).resolve()
    meta_path = folder / "metadata.json"
    vinfo_path = folder / "video_info.json"
    srt_path = folder / "subtitles.srt"

    meta_data = {}
    if meta_path.exists():
        try:
            meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    vinfo_data = {}
    if vinfo_path.exists():
        try:
            vinfo_data = json.loads(vinfo_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Kanal ve kategori tespiti
    ch_id = channel_id or meta_data.get("channel_id") or vinfo_data.get("channel_id") or ""
    ch_mgr = ChannelManager()
    all_registered = {c["channel_id"].lower(): c for c in ch_mgr.all_channels()}

    if not ch_id:
        # Klasör yolundaki parçaları kayıtlı kanallarla eşleştir
        parts = [p.lower() for p in folder.parts]
        for p in parts:
            if p in all_registered:
                ch_id = p
                break

    if not ch_id:
        # Klasör yolundaki parçaları kayıtlı kanallarla esnek eşleştir
        parts = [p.lower() for p in folder.parts]
        for p in parts:
            for reg_cid in all_registered.keys():
                if reg_cid in p:
                    ch_id = reg_cid
                    break
            if ch_id:
                break

    if not ch_id:
        # Bilinen prefix/anahtar kelimelerden tahmin et
        parts = [p.lower() for p in folder.parts]
        for p in parts:
            if "redditchronicle" in p:
                ch_id = "redditchroniclesa"
                break
            elif "tr1_reddit" in p or "reddithikayeleri" in p:
                ch_id = "tr1_reddithikayeleri"
                break
            elif "yazan" in p or "wa" in p or "chat" in p:
                ch_id = "yazanyazana"
                break
            elif "blackbox" in p or "aviation" in p:
                ch_id = "blackboxaudio"
                break
            elif "nova" in p:
                ch_id = "novashorthes"
                break

    channel_info = all_registered.get(ch_id.lower()) or ch_mgr.get_channel(ch_id) or {}
    category = (
        meta_data.get("topic_category") or 
        meta_data.get("category") or 
        channel_info.get("topic_category") or 
        ("reddit_stories" if "reddit" in str(ch_id).lower() else 
         "whatsapp_stories" if ("yazan" in str(ch_id).lower() or "wa" in str(ch_id).lower()) else 
         "general")
    )
    language = (
        channel_info.get("language") or 
        meta_data.get("language") or 
        vinfo_data.get("language") or 
        ("tr" if ("tr" in str(ch_id).lower() or "yazan" in str(ch_id).lower() or "hikaye" in str(ch_id).lower()) else "en")
    )

    # 1. Metni metadata'dan topla
    narration = meta_data.get("narration", "")
    scenes = meta_data.get("scenes", [])
    if not narration and scenes:
        narration = " ".join([s.get("narration", "") for s in scenes if isinstance(s, dict)])

    # WhatsApp script formatı
    script_obj = meta_data.get("script") or {}
    if not narration and script_obj and isinstance(script_obj, dict):
        messages = script_obj.get("messages", [])
        if messages:
            dialogue_lines = []
            for m in messages:
                sender = m.get("sender_name") or ("Gelen" if m.get("incoming") else "Sen")
                txt = m.get("text", "")
                dialogue_lines.append(f"{sender}: {txt}")
            narration = "\n".join(dialogue_lines)

    # 2. Altyazı (SRT) dosyasından topla
    if not narration and srt_path.exists():
        try:
            srt_content = srt_path.read_text(encoding="utf-8")
            # Basit srt temizleyici
            lines = [line.strip() for line in srt_content.splitlines() if line.strip() and not line.strip().isdigit() and "-->" not in line]
            narration = " ".join(lines)
        except Exception:
            pass

    # 3. Eğer hala metin yoksa, videonun sesini yerel faster-whisper ile transkribe et
    video_file = folder / "final.mp4"
    if not video_file.exists():
        video_file = folder / "video.mp4"

    if (not narration or len(narration.strip()) < 20) and video_file.exists():
        try:
            from faster_whisper import WhisperModel
            w_model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = w_model.transcribe(str(video_file), language=language)
            transcribed = " ".join([s.text.strip() for s in segments])
            if transcribed:
                narration = transcribed
                print(f"[AI-Metadata] 🎙️ Videodan transkripsiyon çıkarıldı ({len(narration)} karakter)")
        except Exception as whisper_err:
            print(f"[AI-Metadata] Whisper transkripsiyon uyarısı: {whisper_err}")

    raw_title = (
        meta_data.get("title") or 
        vinfo_data.get("title") or 
        meta_data.get("topic") or 
        folder.name
    )

    return {
        "folder": folder,
        "channel_id": ch_id,
        "category": category,
        "language": language,
        "title": raw_title,
        "narration": narration.strip(),
        "existing_meta": meta_data,
        "existing_vinfo": vinfo_data,
        "video_file": str(video_file) if video_file.exists() else None,
    }


def _query_local_ai_completion(prompt: str, system_prompt: str, settings: dict) -> Optional[str]:
    """LM Studio veya Ollama yerel sunucusuna HTTP isteği gönderir."""
    lmstudio_url = settings.get("lmstudio_url", "http://localhost:1234/v1").rstrip("/")
    
    # 1. LM Studio Denemesi
    try:
        # Aktif veya tercih edilen modeli bul
        model_id = "qwen/qwen2.5-coder-14b"
        try:
            m_res = requests.get(f"{lmstudio_url}/models", timeout=3)
            if m_res.status_code == 200:
                available_ids = [m.get("id") for m in m_res.json().get("data", [])]
                # Qwen, Gemma-3, Dolphin gibi hızlı modelleri önceliklendir
                for cand in ["qwen/qwen2.5-coder-14b", "google/gemma-3-12b", "dolphin3-cyber-8b", "google/gemma-4-12b"]:
                    if cand in available_ids:
                        model_id = cand
                        break
                else:
                    if available_ids:
                        model_id = available_ids[0]
        except Exception:
            pass

        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000,
            "reasoning_effort": "none"  # Düşünme modellerinde zaman aşımını engeller
        }

        resp = requests.post(f"{lmstudio_url}/chat/completions", json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content")
            if content and len(content.strip()) > 10:
                return content.strip()
    except Exception as lm_err:
        print(f"[AI-Metadata] LM Studio sorgu uyarısı: {lm_err}")

    # 2. Ollama Fallback
    ollama_url = settings.get("ollama_url", "http://localhost:11434").rstrip("/")
    try:
        ollama_model = settings.get("ollama_model", "llama3")
        payload_ollama = {
            "model": ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 800}
        }
        resp = requests.post(f"{ollama_url}/api/chat", json=payload_ollama, timeout=45)
        if resp.status_code == 200:
            content = resp.json().get("message", {}).get("content", "")
            if content and len(content.strip()) > 10:
                return content.strip()
    except Exception as ol_err:
        print(f"[AI-Metadata] Ollama fallback sorgu uyarısı: {ol_err}")

    # 3. Gemini Fallback (Eğer yerel modeller kapalıysa ve API anahtarı varsa)
    gemini_key = settings.get("gemini_api_key", "")
    if gemini_key:
        try:
            # Şifreli key çözme
            try:
                from settings_manager import decrypt_value
                gemini_key = decrypt_value(gemini_key)
            except Exception:
                pass
            if gemini_key:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                full_p = f"{system_prompt}\n\n{prompt}"
                g_resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_p
                )
                if g_resp and g_resp.text:
                    return g_resp.text.strip()
        except Exception as gem_err:
            print(f"[AI-Metadata] Gemini fallback uyarısı: {gem_err}")

    return None


def generate_ai_metadata(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Video içeriğini ve kanal bağlamını analiz ederek Yerel AI ile viral YouTube metadata'sı üretir.
    """
    category = context.get("category", "reddit_stories")
    language = context.get("language", "tr")
    raw_title = context.get("title", "")
    narration = context.get("narration", "")

    # Eğer narration yoksa ham başlıktan bağlam üret
    content_text = narration if len(narration) > 20 else raw_title

    settings = {}
    if SettingsManager:
        try:
            settings = SettingsManager().get_all()
        except Exception:
            pass

    # Kategoriye özel sistem direktifleri (Kanal diline %100 uyumlu)
    is_tr = language.lower().strip().startswith("tr")

    if "reddit" in category:
        if not is_tr:
            category_instructions = (
                f"Category: Reddit Confessions & Real Life Stories.\n"
                f"Target Language: {language.upper()} (MUST BE 100% IN {language.upper()} - ZERO TURKISH WORDS OR HASHTAGS).\n"
                "- Title: High-CTR, curiosity gap, emotional shock, ending with a question or exclamation mark, max 75 characters, NO '#Shorts' in title + 1 emoji.\n"
                "- Description:\n"
                f"  Paragraph 1 (Organic SEO): A compelling 1-2 sentence hook that weaves 2-3 natural searchable keywords (e.g. reddit story, confession, true mystery) directly into engaging sentences.\n"
                "  Paragraph 2: Audience engagement question: 'What would you have done in this situation? Let us know in the comments! 👇'\n"
                "  Paragraph 3: 'Subscribe and hit the bell for authentic daily Reddit stories! 🔔'\n"
                "  Paragraph 4: Exactly 4-6 specific, relevant hashtags (e.g. #RedditStories #AskReddit #Storytime #RedditConfessions #AITAH #TrueStories) — NEVER USE #Shorts, #Viral, #FYP, or #Trending.\n"
                "- Tags (tags): 12-18 highly specific, searchable English tags (e.g. reddit stories, askreddit, reddit confessions, storytime, aitah, true stories, crazy stories, confession, drama, life stories). DO NOT include generic spam tags like 'shorts', 'viral', 'fyp', or 'trending'.\n"
                "- Pinned Comment: Engaging discussion question in English for the audience."
            )
        else:
            category_instructions = (
                "Kategori: Reddit İtirafları ve Gerçek Hikayeler.\n"
                "Hedef Dil: TÜRKÇE (%100 TÜRKÇE).\n"
                "- Başlık: Yüksek tıklanma (CTR) odaklı, merak boşluğu (curiosity gap) oluşturan, "
                "aşırı heyecan/şok hissi veren, soru veya ünlemle biten, 75 karakteri geçmeyen, '#Shorts' İÇERMEYEN başlık + 1 emoji.\n"
                "- Açıklama:\n"
                "  1. Paragraf (Doğal SEO): İlk 2 cümlede konunun en can alıcı kancasını (hook) ve izleyicilerin arayabileceği 2-3 anahtar kelimeyi (örn: reddit hikayeleri, gizemli itiraf, gerçek olay) doğal cümle akışında geçir.\n"
                "  2. Paragraf: Hikayeyi merak ettiren kısa özet ve izleyiciye soru: 'Siz olsaydınız bu durumda ne yapardınız? Yorumlarda buluşalım! 👇'\n"
                "  3. Paragraf: 'Gerçek Reddit itirafları ve şok edici hikayeler için abone olmayı ve bildirimleri açmayı unutmayın! 🔔'\n"
                "  4. Paragraf: 4-6 adet konuya %100 özel hashtag (örn: #RedditHikayeleri #RedditTR #İtiraflar #GerçekHikayeler #HikayeZamanı) — KESİNLİKLE #Shorts, #Viral, #Keşfet veya #FYP KULLANMA.\n"
                "- Etiketler (tags): 12-18 adet konuya özel, aranabilir Türkçe etiket (örn: reddit hikayeleri, reddit tr, itiraflar, gerçek hayat hikayeleri, "
                "aile sırları, hikaye zamanı, türkçe dublaj, türkçe seslendirme). 'shorts', 'viral', 'keşfet', 'fyp' gibi jenerik/spam etiketleri KESİNLİKLE EKLEME.\n"
                "- Pinned Comment: İzleyicileri tartışmaya sokup yoruma boğacak tek cümlelik anket/soru."
            )
    elif "whatsapp" in category:
        if not is_tr:
            category_instructions = (
                f"Category: WhatsApp Comedy & Text Dialogues.\n"
                f"Target Language: {language.upper()} (MUST BE 100% IN {language.upper()}).\n"
                "- Title: Funny, catchy messaging dialogue title, 3-7 words, ending with '!' or '...' + emoji, NO '#Shorts'.\n"
                "- Description: Entertaining text summary with naturally woven keywords, send-to-a-friend call to action, and 4-6 comedy hashtags (#TextStory #FunnyTexts #ChatStory #Comedy #WhatsAppStories #Humor) — NO #Shorts or #Viral.\n"
                "- Tags: 12-16 specific comedy tags (text story, chat story, funny texts, whatsapp comedy, humor, messaging dialogue). NO 'shorts' or 'viral'.\n"
                "- Pinned Comment: 'Send this to a friend who would totally text this 😂👇'"
            )
        else:
            category_instructions = (
                "Kategori: WhatsApp Komedi ve Diyalog Shorts (@1dublaj tarzı).\n"
                "- Başlık: Komik, merak uyandırıcı, doğal sokak ve mesajlaşma dili, 3-7 kelimelik, sonu '!' veya '...' ve emoji ile biten, '#Shorts' İÇERMEYEN başlık.\n"
                "- Açıklama: Eğlenceli diyalog özeti, dublaj vurgusu ve konuya özel komedi hashtagleri (#WhatsApp #Diyalog #Seslendirme #Dublaj #Komedi #Mizah #EğlenceliMesajlar) — KESİNLİKLE #keşfet, #shorts, #viral KULLANMA.\n"
                "- Etiketler (tags): 12-16 adet diyalog ve mizah etiketi (konuşma, diyalog, seslendirme, dublaj, türkçe dublaj, whatsapp, komik, mizah, mesaj hikayeleri, eğlenceli sohbet). 'shorts', 'keşfet', 'viral' KULLANMA.\n"
                "- Pinned Comment: 'Bu mesajı arkadaşına gönderseler ne derdin? 😂👇'"
            )
    else:
        category_instructions = (
            f"Category: {category}.\n"
            f"Target Language: {language.upper()}.\n"
            "- Title: Catchy, high-CTR, curiosity-inducing title (< 75 characters, no #Shorts) + 1 emoji.\n"
            "- Description: Organic SEO opening hook integrating primary search terms, video summary, call-to-action question, and 4-6 strictly topic-specific hashtags (NO #Shorts, NO #Viral).\n"
            "- Tags: 12-18 rich and relevant search tags specific to the topic. NO generic tags like 'shorts' or 'viral'.\n"
            "- Pinned Comment: Engaging question for viewers."
        )

    if not is_tr:
        system_prompt = (
            "You are the world's top YouTube algorithm, audience retention, and video SEO expert.\n"
            f"Your task is to analyze the video text and generate the highest CTR, views, and engagement metadata package.\n"
            f"CRITICAL RULES:\n"
            f"1. All generated output MUST be 100% in {language.upper()}. Zero Turkish words or hashtags.\n"
            "2. NEVER use generic viral hashtags (#Shorts, #Viral, #FYP, #Trending). Use ONLY topic-relevant hashtags.\n"
            "3. The description's first paragraph must naturally weave 2-3 searchable keywords into authentic sentences.\n"
            "4. Tags must be 100% specific to the video content. No generic 'shorts' or 'viral' tags.\n"
            "Return ONLY valid JSON. No markdown backticks or extra commentary.\n"
            "Schema:\n"
            "{\n"
            '  "title": "Viral Title + Emoji",\n'
            '  "description": "Rich Description with Natural SEO...",\n'
            '  "tags": ["specific_tag1", "specific_tag2"],\n'
            '  "seo_hashtags": ["#SpecificTopic1", "#SpecificTopic2"],\n'
            '  "pinned_comment": "Pinned Question"\n'
            "}"
        )
        user_prompt = (
            f"{category_instructions}\n"
            f"Channel Language: {language.upper()}\n"
            f"Original Title/Topic: {raw_title}\n"
            f"Video Story / Dialogue Text:\n\"\"\"{content_text[:2500]}\"\"\"\n\n"
            f"Please produce the 100% {language.upper()} JSON output strictly following the rules above:"
        )
    else:
        system_prompt = (
            "Sen YouTube Algoritması, İzleyici Bağlama (Retention) ve Video SEO konusunda dünyanın en iyi uzmanısın.\n"
            "Görevin, verilen video metnini analiz ederek en yüksek izlenme, tıklanma (CTR) ve etkileşim getirecek metadata paketini oluşturmaktır.\n"
            "KRİTİK ALGORİTMA KURALLARI:\n"
            "1. #Shorts, #Viral, #Keşfet, #Keşfetteyiz, #FYP gibi jenerik/spam etiket ve hashtagleri KESİNLİKLE KULLANMA. Bunlar kanala alakasız kitle çekip retention'ı düşürür ve yanıltıcı metaveri riski yaratır.\n"
            "2. Açıklamanın ilk 2 cümlesinde izleyicilerin arayacağı 2-3 anahtar kelimeyi doğal bir cümle içinde geçir (Doğal SEO).\n"
            "3. Etiketler (tags) %100 videodaki olaylara, karakterlere ve konuya özel olmalıdır.\n"
            "Çıktıyı SADECE ve SADECE geçerli bir JSON formatında döndür. Markdown veya ekstra açıklama yazma.\n"
            "Şema:\n"
            "{\n"
            '  "title": "Viral Başlık + Emoji",\n'
            '  "description": "Doğal SEO Cümleleri İçeren Zengin Açıklama Metni...",\n'
            '  "tags": ["özel_etiket1", "özel_etiket2"],\n'
            '  "seo_hashtags": ["#KonuyaÖzel1", "#KonuyaÖzel2"],\n'
            '  "pinned_comment": "Sabitlenecek Yorum Sorusu"\n'
            "}"
        )
        user_prompt = (
            f"{category_instructions}\n"
            f"Kanal Dili: {language.upper()}\n"
            f"Mevcut Başlık/Konu: {raw_title}\n"
            f"Video Hikaye / Diyalog Metni:\n\"\"\"{content_text[:2500]}\"\"\"\n\n"
            "Lütfen yukarıdaki kurallara tam uyarak JSON çıktısını üret:"
        )

    # Yerel AI sorgusu
    raw_ai_output = _query_local_ai_completion(user_prompt, system_prompt, settings)

    parsed_result = None
    if raw_ai_output:
        clean_json = _clean_json_response(raw_ai_output)
        try:
            parsed_result = json.loads(clean_json)
        except Exception as e_json:
            print(f"[AI-Metadata] JSON ayrıştırma hatası ({e_json}), regex ile kurtarılıyor...")
            # Regex ile alanları tek tek yakalama toleransı
            try:
                m_title = re.search(r'"title"\s*:\s*"([^"]+)"', clean_json)
                m_desc = re.search(r'"description"\s*:\s*"([^"]+)"', clean_json)
                m_tags = re.search(r'"tags"\s*:\s*\[(.*?)\]', clean_json, re.DOTALL)
                if m_title and m_desc:
                    tags_list = [t.strip().strip('"').strip("'") for t in m_tags.group(1).split(",") if t.strip()] if m_tags else []
                    parsed_result = {
                        "title": m_title.group(1),
                        "description": m_desc.group(1).replace("\\n", "\n"),
                        "tags": tags_list,
                        "seo_hashtags": [t for t in tags_list if t.startswith("#")],
                        "pinned_comment": ""
                    }
            except Exception:
                pass

    # Başarılı Yerel AI çıktısı varsa doğrula ve zenginleştir
    if parsed_result and isinstance(parsed_result, dict) and parsed_result.get("title"):
        title = parsed_result.get("title", raw_title).strip()
        # Başlıkta istenmeyen #shorts kalmışsa temizle
        title = re.sub(r'#\w+', '', title).strip()
        
        description = (parsed_result.get("description") or "").strip()
        raw_tags = parsed_result.get("tags") or []
        tags = sanitize_tags(raw_tags)

        # Dil Uygunluğu Doğrulaması (Yabancı dildeki kanala Türkçe metin veya etiket sızmışsa AI çıktısını reddet)
        try:
            from src.channel_manager import is_bogus_fallback
        except ImportError:
            from channel_manager import is_bogus_fallback

        if is_bogus_fallback(description, tags, language=language, category=category):
            print(f"[AI-Metadata] ⚠️ AI çıktısında dil karışımı tespit edildi (Hedef Dil: {language.upper()}), deterministik şablona geçiliyor.")
            parsed_result = None
        else:
            raw_hashtags = parsed_result.get("seo_hashtags") or []
            if not raw_hashtags:
                raw_hashtags = re.findall(r'#\w+', description)
            
            seo_hashtags = sanitize_hashtags(raw_hashtags)
            
            # Açıklamadaki jenerik hashtagleri temizle ve temiz hashtagleri ekle
            for bad_h in ["#Shorts", "#shorts", "#Viral", "#viral", "#Keşfet", "#keşfet", "#FYP", "#fyp", "#Trending", "#trending"]:
                description = description.replace(bad_h, "").strip()

            if seo_hashtags and not any(h in description for h in seo_hashtags):
                description = f"{description}\n\n{' '.join(seo_hashtags)}"

            pinned_comment = parsed_result.get("pinned_comment") or ""

            return {
                "title": title,
                "description": description,
                "tags": tags,
                "seo_hashtags": seo_hashtags,
                "pinned_comment": pinned_comment,
                "success": True,
                "source": "local_ai",
                "model": "local_llm"
            }

    # Yerel AI yanıt veremezse Deterministik Akıllı Şablon Fallback (Asla boş veya yetersiz kalmaz)
    print(f"[AI-Metadata] ℹ️ Kural tabanlı zengin SEO şablonu uygulanıyor (Hedef Dil: {language.upper()}).")
    clean_title = raw_title.replace("#Shorts", "").replace("#shorts", "").strip()
    hook_part = f"{content_text[:180]}...\n\n" if (content_text and len(content_text.strip()) > 20) else ""

    if "reddit" in category:
        if not is_tr:
            default_title = f"{clean_title} 😱" if not any(c in clean_title for c in "!?😱🚨💔") else clean_title
            default_desc = (
                f"{default_title}\n\n"
                f"{hook_part}"
                "Unbelievable Reddit confessions, true mysteries, and compelling life stories. What would you have done in this situation? Let us know in the comments below! 👇\n\n"
                "Don't forget to like, subscribe, and hit the bell for authentic daily Reddit stories! 🔔\n\n"
                "#Reddit #RedditStories #AskReddit #Storytime #RedditConfessions #AITAH #TrueStories"
            )
            default_tags = [
                "reddit", "reddit stories", "askreddit", "reddit confessions", "storytime",
                "aitah", "true stories", "life stories", "crazy stories", "confession"
            ]
            pinned = "What would you do if you were in this situation? Let me know in the comments! 👇"
        else:
            default_title = f"{clean_title} 😱" if not any(c in clean_title for c in "!?😱🚨💔") else clean_title
            default_desc = (
                f"{default_title}\n\n"
                f"{hook_part}"
                "En popüler Reddit itirafları, gizemli sırlar ve gerçek hayat hikayeleri bu anlatımda bir araya geliyor. Siz bu durumda kalsaydınız ne yapardınız? Yorumlarda buluşalım! 👇\n\n"
                "Gerçek Reddit itirafları ve sürükleyici hikayeler için abone olmayı ve bildirimleri açmayı unutmayın! 🔔\n\n"
                "#Reddit #RedditHikayeleri #AskReddit #RedditTR #İtiraf #HikayeZamanı #GerçekHikayeler"
            )
            default_tags = [
                "reddit", "reddit hikayeleri", "reddit türkiye", "reddit tr", "itiraflar", 
                "aile sırları", "gerçek hikayeler", "hikaye zamanı", "türkçe dublaj", 
                "türkçe seslendirme", "yaşanmış olaylar"
            ]
            pinned = "Sizin çocukken tamamen normal sandığınız ama büyüyünce şok olduğunuz bir sır var mı? Yorumları okuyorum! 👇"
    elif "whatsapp" in category:
        if not is_tr:
            default_title = f"{clean_title} 😂" if not any(c in clean_title for c in "!?😂💀🥩🏢") else clean_title
            default_desc = (
                f"{default_title}\n\n"
                "Welcome! We share original, hilarious text message conversations and funny chat stories. Don't forget to like and subscribe for daily laughs! 😊\n\n"
                "#TextStory #FunnyTexts #ChatStory #Comedy #WhatsAppStories #Humor"
            )
            default_tags = [
                "text story", "chat story", "funny text", "whatsapp", "funny", "comedy",
                "humor", "memes", "whatsapp stories", "messaging dialogue"
            ]
            pinned = "Send this to a friend who would totally text something like this 😂👇"
        else:
            default_title = f"{clean_title} 😂" if not any(c in clean_title for c in "!?😂💀🥩🏢") else clean_title
            default_desc = (
                f"{default_title}\n\n"
                "Merhaba! Bu kanalda kendi yazmış ve seslendirmiş olduğumuz özgün ve eğlenceli mesajlaşma diyaloglarını paylaşıyoruz. "
                "Konuşmaların ve dublajların hepsi gerçek olaylardan esinlenilmiş ve tarafımıza aittir. Keyifli seyirler! 😊\n\n"
                "#WhatsApp #Diyalog #Seslendirme #Dublaj #Komedi #Mizah #EğlenceliMesajlar"
            )
            default_tags = [
                "konuşma", "diyalog", "seslendirme", "türkçe", "türkçe seslendirme", "dublaj",
                "türkçe dublaj", "whatsapp", "komik", "komedi", "mesaj hikayeleri", "eğlenceli sohbet"
            ]
            pinned = "Bu konuşmayı yaşayan arkadaşına gönder 😂👇"
    else:
        loc_desc, loc_tags = get_localized_metadata(clean_title, language=language, category=category, hook_summary=content_text[:180])
        default_title = clean_title
        default_desc = loc_desc
        default_tags = loc_tags
        pinned = "What did you think of this video? Let us know in the comments! 👇" if not is_tr else "Bu video hakkındaki görüşlerinizi yorumlarda paylaşmayı unutmayın! 👇"

    return {
        "title": default_title,
        "description": default_desc,
        "tags": default_tags,
        "seo_hashtags": re.findall(r'#\w+', default_desc),
        "pinned_comment": pinned,
        "success": False,
        "source": "smart_fallback",
        "model": "template"
    }


def auto_generate_and_apply_metadata(
    video_folder: Union[str, Path],
    channel_id: str = "",
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Belirtilen video klasöründeki metadata.json ve video_info.json dosyalarını 
    Yerel AI ile oluşturulan en iyi başlık, açıklama ve etiketlerle günceller.
    
    Aktifleştirme gerektirmez, doğrudan video klasörüne yazar.
    """
    folder = Path(video_folder).resolve()
    if not folder.exists() or not folder.is_dir():
        print(f"[AI-Metadata] ❌ Video klasörü bulunamadı: {folder}")
        return {"success": False, "error": "Folder not found"}

    meta_file = folder / "metadata.json"
    vinfo_file = folder / "video_info.json"

    # Eğer zaten AI tarafından oluşturulmuşsa ve zorlama yoksa kontrol et (ancak dil karışımı/bogus ise yenile!)
    if not force_refresh and meta_file.exists():
        try:
            curr_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            curr_desc = curr_meta.get("description", "")
            curr_tags = curr_meta.get("tags", [])
            
            # Kanal dilini çöz
            ch_mgr_inst = ChannelManager()
            ch_cid = channel_id or curr_meta.get("channel_id") or ""
            if not ch_cid:
                for p in folder.parts:
                    if ch_mgr_inst.get_channel(p):
                        ch_cid = p
                        break
            ch_obj = ch_mgr_inst.get_channel(ch_cid) or {}
            ch_target_lang = ch_obj.get("language") or curr_meta.get("language") or ("tr" if "tr" in str(ch_cid).lower() else "en")
            ch_target_cat = ch_obj.get("topic_category") or curr_meta.get("topic_category") or "reddit_stories"
            
            # Dil ve kategori doğrulaması
            try:
                from src.channel_manager import is_bogus_fallback
            except ImportError:
                from channel_manager import is_bogus_fallback
            
            has_bogus_content = is_bogus_fallback(curr_desc, curr_tags, language=ch_target_lang, category=ch_target_cat)
            
            if not has_bogus_content and curr_meta.get("ai_metadata_generated") is True and len(curr_desc) > 80:
                print(f"[AI-Metadata] ℹ️ Bu video için AI metadata zaten mevcut ve geçerli ({folder.name}).")
                return {"success": True, "already_generated": True, "title": curr_meta.get("title")}
            elif has_bogus_content:
                print(f"[AI-Metadata] ⚠️ Mevcut metadata kanal diline ({ch_target_lang.upper()}) uymuyor veya karışık dil içeriyor, yenileniyor ({folder.name})...")
        except Exception:
            pass

    print(f"\n[AI-Metadata] 🧠 Yerel AI Video Analiz & Metadata Motoru Devrede: {folder.name}")
    ctx = extract_video_narration_and_context(folder, channel_id=channel_id)
    generated = generate_ai_metadata(ctx)

    new_title = generated.get("title")
    new_desc = generated.get("description")
    new_tags = generated.get("tags")
    new_hashtags = generated.get("seo_hashtags")
    pinned_comment = generated.get("pinned_comment")

    # 1. metadata.json güncelle
    meta_data = dict(ctx.get("existing_meta") or {})
    meta_data["title"] = new_title
    meta_data["description"] = new_desc
    meta_data["tags"] = new_tags
    meta_data["seo_hashtags"] = new_hashtags
    meta_data["pinned_comment"] = pinned_comment
    meta_data["ai_metadata_generated"] = True
    meta_data["ai_metadata_source"] = generated.get("source")
    meta_data["ai_metadata_updated_at"] = datetime.now().isoformat()
    if not meta_data.get("channel_id") and ctx.get("channel_id"):
        meta_data["channel_id"] = ctx.get("channel_id")

    meta_file.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. video_info.json güncelle
    vinfo_data = dict(ctx.get("existing_vinfo") or {})
    vinfo_data["title"] = new_title
    vinfo_data["description"] = new_desc
    vinfo_data["desc"] = new_desc
    vinfo_data["search_optimized_description"] = new_desc
    vinfo_data["tags"] = new_tags
    vinfo_data["seo_hashtags"] = new_hashtags
    vinfo_data["pinned_comment"] = pinned_comment
    vinfo_data["ai_metadata_generated"] = True
    vinfo_data["ai_metadata_updated_at"] = datetime.now().isoformat()
    if not vinfo_data.get("channel_id") and ctx.get("channel_id"):
        vinfo_data["channel_id"] = ctx.get("channel_id")

    vinfo_file.write_text(json.dumps(vinfo_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. İsteğe bağlı YouTube metin dosyası oluştur (Tek tıkla kopyalama kolaylığı)
    try:
        txt_summary = (
            f"=== YOUTUBE VIDEO METADATA ===\n"
            f"Oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Kaynak: {generated.get('source')} ({generated.get('model')})\n\n"
            f"📌 BAŞLIK ({len(new_title)} karakter):\n{new_title}\n\n"
            f"📝 AÇIKLAMA:\n{new_desc}\n\n"
            f"🏷️ ETİKETLER ({len(new_tags)} adet):\n{', '.join(new_tags)}\n\n"
            f"💬 SABİT YORUM (PINNED COMMENT):\n{pinned_comment}\n"
        )
        (folder / "youtube_metadata.txt").write_text(txt_summary, encoding="utf-8")
    except Exception:
        pass

    print(f"[AI-Metadata] ✅ Metadata başarıyla güncellendi:")
    print(f"             Başlık: {new_title}")
    print(f"             Açıklama: {len(new_desc)} karakter, Etiketler: {len(new_tags)} adet")
    print(f"             Sabit Yorum: {pinned_comment}")

    return {
        "success": True,
        "title": new_title,
        "description": new_desc,
        "tags": new_tags,
        "seo_hashtags": new_hashtags,
        "pinned_comment": pinned_comment,
        "folder": str(folder)
    }


if __name__ == "__main__":
    # Münferit test veya doğrudan klasör çalıştırma
    if len(sys.argv) > 1:
        target = sys.argv[1]
        cid = sys.argv[2] if len(sys.argv) > 2 else ""
        auto_generate_and_apply_metadata(target, channel_id=cid, force_refresh=True)
    else:
        print("Kullanım: python3 -m src.ai_metadata_generator <video_klasoru> [kanal_id]")
