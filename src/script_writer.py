"""
script_writer.py
Çoklu AI provider desteği ile video senaryosu üretir.
Desteklenen modeller: Claude (Anthropic), Gemini (Google), Ollama (yerel).
"""

from __future__ import annotations
import json
import random
import time
from datetime import datetime


def _retry(callable_, *, attempts: int = 4, base_delay: float = 2.0):
    """
    Geçici API hataları (503, 429, timeout) için üstel geri çekilme veya sunucu tarafından
    belirtilen bekleme süresi ile yeniden dener. Günlük limit aşımında hemen hata fırlatır.
    """
    import re
    last_err = None
    for i in range(attempts):
        try:
            return callable_()
        except Exception as e:
            last_err = e
            msg = str(e)
            
            # Günlük limit aşımı kontrolü (Free Tier limits)
            if any(k in msg for k in ("GenerateRequestsPerDay", "free_tier_requests", "limit: 20", "RESOURCE_EXHAUSTED")):
                if "limit: 20" in msg or "RequestsPerDay" in msg or "RESOURCE_EXHAUSTED" in msg:
                    raise RuntimeError(
                        "Gemini API Günlük İstek Limitine Ulaşıldı (Free Tier günlük 20 istek sınırı aşılmıştır).\n"
                        "Lütfen Google AI Studio adresinden API anahtarınız için faturalandırmayı açıp Kullandıkça Öde (Pay-as-you-go) planına geçin "
                        "veya Ayarlar menüsünden Claude/LM Studio/Ollama gibi alternatif bir yapay zeka modeline geçiş yapın."
                    ) from e
            
            transient = any(k in msg for k in (
                "503", "429", "500", "502", "504",
                "UNAVAILABLE", "RATE_LIMIT", "deadline", "timeout",
                "overloaded", "temporarily", "Connection",
            ))
            if not transient or i == attempts - 1:
                raise
            
            # Dinamik bekleme süresi tespiti
            delay = base_delay * (2 ** i) + random.uniform(0, 1)
            retry_match = re.search(r"retry in (\d+\.?\d*)s", msg)
            if retry_match:
                delay = float(retry_match.group(1)) + 0.5
                print(f"[RETRY] Sunucu {delay:.2f}s beklememizi istedi.")
            else:
                retry_json_match = re.search(r"retryDelay':\s*'(\d+)s'", msg)
                if retry_json_match:
                    delay = float(retry_json_match.group(1)) + 1.0
                    print(f"[RETRY] Sunucu {delay:.2f}s beklememizi istedi (JSON).")
                    
            print(f"[RETRY] Geçici hata ({msg[:80]}), {delay:.1f}s sonra tekrar denenecek ({i+1}/{attempts})...")
            time.sleep(delay)
    raise last_err


SYSTEM_PROMPT = """You are an expert YouTube scriptwriter specializing in space, astronomy, and science content.
Your task is to write engaging, educational video scripts.

STRICT OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown, no extra text:
{
  "title": "YouTube video title (in the requested language, SEO-optimized, max 100 chars)",
  "description": "YouTube video description (in the requested language, 150-300 words, with hashtags)",
  "keywords": ["overall_keyword1", "overall_keyword2"],
  "tags": ["tag1", "tag2", "tag3"],
  "style_prompt": "A consistent visual style prompt in English (e.g. 'cinematic photorealistic space photography, highly detailed, NASA style, 8k resolution')",
  "scenes": [
    {
      "narration": "Narration text for this scene (in the requested language, matching the requested word count, engaging and scientifically accurate)",
      "nasa_keywords": "A specific English search term for NASA image search (e.g. 'jupiter red spot close up', 'mars colony')",
      "image_prompt": "A detailed Stable Diffusion style image prompt in English for this scene",
      "emotion": "The emotional tone of this scene narration (choose from: neutral, excited, dramatic, mysterious, happy, sad)"
    }
  ]
}

Guidelines:
- Write title, description, tags, and scene narration ENTIRELY in the requested language
- Each scene's nasa_keywords and image_prompt MUST be in English
- Ensure the scientific facts are accurate and engaging
- DO NOT use retro, cartoon, drawing, line-art, or illustrative styles. All visual descriptions and styles MUST be scientific, photorealistic, high-detail astrophotography, NASA-style space images.
"""


STORY_SYSTEM_PROMPT = """You are an expert storyteller and visual designer specializing in fantasy, adventure, mystery, and historical stories.
Your task is to write engaging, beautifully narration-driven stories with a list of scenes and consistent visual prompts.

STRICT OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown, no extra text:
{
  "title": "Story video title (in the requested language, SEO-optimized, max 100 chars)",
  "description": "Story video description (in the requested language, 150-300 words, with hashtags)",
  "keywords": ["overall_keyword1", "overall_keyword2"],
  "tags": ["tag1", "tag2", "tag3"],
  "style_prompt": "A consistent visual style prompt that applies to all images (in English, e.g., 'cinematic fairytale illustration, digital art, warm lighting, style of Pixar, 8k resolution')",
  "scenes": [
    {
      "narration": "Narration text for this scene (in the requested language, matching the requested word count, engaging and flowing)",
      "image_prompt": "Detailed Stable Diffusion image prompt for this scene (in English, describing the character, action, and setting, e.g., 'A young boy with brown messy hair and a green jacket looking at a glowing ancient map in a dusty library')",
      "emotion": "The emotional tone of this scene narration (choose from: neutral, excited, dramatic, mysterious, happy, sad)"
    }
  ]
}

Guidelines:
- Write title, description, tags, and scene narration ENTIRELY in the requested language.
- The style_prompt and each scene's image_prompt MUST be in English (since Stable Diffusion is trained on English).
- Keep the style_prompt consistent (for style coherence) and describe details like character features, lighting, and rendering style in it.
- Ensure the story flows beautifully across scenes. Generate exactly the requested number of scenes.
- Total narration length across all scenes should match the requested word count.
"""


TRAVEL_SYSTEM_PROMPT = """You are an expert travel guide, documentary scriptwriter, and visual designer.
Your task is to write engaging, informational travel guide scripts with a list of scenes and consistent visual prompts for image generation.

STRICT OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown, no extra text:
{
  "title": "Travel video title (in the requested language, SEO-optimized, max 100 chars)",
  "description": "Travel video description (in the requested language, 150-300 words, with hashtags)",
  "keywords": ["overall_keyword1", "overall_keyword2"],
  "tags": ["tag1", "tag2", "tag3"],
  "style_prompt": "A consistent visual style prompt that applies to all images (in English, e.g., 'cinematic realistic travel photography, high detail, colorful, 8k resolution')",
  "scenes": [
    {
      "narration": "Narration text for this scene (in the requested language, matching the requested word count, introducing the destination with passion)",
      "image_prompt": "Detailed Stable Diffusion image prompt for this scene (in English, describing the scenery, lighting, and elements, e.g., 'Eiffel tower in Paris during sunset, warm orange glow, tourists walking along the Seine river, highly detailed realistic photography')",
      "emotion": "The emotional tone of this scene narration (choose from: neutral, excited, dramatic, mysterious, happy, sad)"
    }
  ]
}

Guidelines:
- Write title, description, tags, and scene narration ENTIRELY in the requested language.
- The style_prompt and each scene's image_prompt MUST be in English.
- Ensure the travel facts are accurate and engaging.
- Total narration length across all scenes should match the requested word count.
"""


AVIATION_SYSTEM_PROMPT = """You are an expert AI Video Essay Scriptwriter & Aviation Safety Analyst specializing in "Black Box Audio & Incident Breakdown" documentaries in the style of Mentour Pilot and Crayon Combat (combining authentic cockpit voice recorder transcripts, FDR telemetry data, and NTSB findings with engaging 2D stickman character reactions and technical schematics).

STRICT OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown, no extra text:
{
  "title": "Aviation incident documentary title (in the requested language, catchy, max 100 chars)",
  "description": "Aviation video description (in the requested language, 150-300 words, with hashtags #Aviation #BlackBox #AirCrashInvestigation #CockpitAudio)",
  "keywords": ["aviation incident", "black box audio", "cvr transcript", "pilot emergency", "ntsb report"],
  "tags": ["Aviation", "BlackBox", "CockpitAudio", "AirCrash", "FlightSafety", "ATC", "Pilot", "NTSB"],
  "flight_name": "Aircraft model and flight identifier (e.g., 'Boeing 767 - Gimli Glider', 'DC-10 - United 232', 'A320 - US Airways 1549')",
  "liveatc_icao": "4-letter ICAO airport code in lowercase (e.g. 'kjfk', 'cywg', 'kden'). If cruise/ocean, use 'unknown'.",
  "scenes": [
    {
      "narration": "Narration text for this scene (in the requested language, matching the requested word count, highly engaging, suspenseful, educational, breaking down the exact cockpit drama and physics)",
      "active_character": "One of ['CAPTAIN', 'FIRST_OFFICER', 'ATC', 'NTSB', 'MECHANIC']",
      "character_dialogue": "Authentic CVR transcript quote or sharp character reaction in the requested language (e.g. 'Mayday Mayday, we lost all hydraulic pressure!', 'Radar contact lost, squawk 7700')",
      "visual_type": "One of ['cockpit_hud', 'atc_radar', 'emergency_lockdown', 'dossier_investigation', 'flow_chain', 'blueprint_spec', 'stickman_reaction']",
      "image_prompt": "Technical schematic or cockpit instrument prompt in English (e.g. 'Boeing 767 ram air turbine deployment schematic, hydraulic pressure drop, warning alert lights')",
      "emotion": "One of ['dramatic', 'shocked', 'serious', 'tense', 'analytical']"
    }
  ]
}

Guidelines:
- Write title, description, tags, scene narrations, and character_dialogue in the requested language.
- Realism & Technical Depth: Explain why the incident happened (e.g., fuel metric unit conversion error, frozen pitot probes, rudder servo valve thermal shock, engine fan disk fatigue crack).
- Character Dynamics:
  * [CAPTAIN]: The experienced Pilot-in-Command managing the emergency checklists.
  * [FIRST_OFFICER]: The co-pilot cross-checking instruments, flying the aircraft, or calling out warnings.
  * [ATC]: The calm air traffic controller providing emergency vectors and terrain clearance.
  * [NTSB]: The accident investigator inspecting the flight data recorder and revealing the root cause.
  * [MECHANIC]: The ground maintenance specialist explaining the mechanical failure point.
- Pacing: Start with the cruise/departure context, build tension towards the sudden malfunction/alarm, walk through the CRM (Crew Resource Management) emergency actions, and conclude with the NTSB verdict and modern aviation safety improvements.
"""

REDDIT_STORIES_SYSTEM_PROMPT = """You are an elite viral Reddit Story scriptwriter and narrator specializing in high-retention, algorithm-dominating Shorts (in the high-viewership style of top Reddit story channels).
Your task is to write captivating, first-person storytelling video scripts engineered for maximum audience retention (>90%), minimal swipe-away rate in the first 3 seconds, and massive comment engagement.

CRITICAL HOOK MANDATE ("KANCAYI BAŞA ÇEKİN" — IN MEDIA RES):
1. ZERO SLOW CHRONOLOGICAL INTROS:
   - It is STRICTLY FORBIDDEN to open with slow, peaceful, chronological backstories (e.g. NEVER start with: "Çocukken her pazar babamla yürürdük...", "Ben küçük bir kasabada büyüdüm...", "3 yıl önce eşimle tanıştım..."). Slow introductions cause an immediate 70% swipe-away rate!
2. IN MEDIA RES OPENING (SCENE 1 — FIRST 3 SECONDS):
   - The very first sentence spoken in Scene 1 MUST hit the viewer like a shockwave with the ultimate climax teaser, scandalous betrayal, or jaw-dropping moral dilemma!
   - FORMULA: [Turning Point / Age of Revelation] + [The Shocking Realization / Crime / Betrayal] + [Absurd Stakes].
   - Examples of Viral Hooks:
     * "22 yaşımda hukuk okurken öğrendim ki, çocukluğumda babamla yaptığımız o masum pazar yürüyüşleri meğer organize bir kaçakçılık rotasıymış..."
     * "3 yıldır yemeyip içmeyip ev peşinatı için biriktirdiğimiz 250 bin liranın banka hesabından buharlaştığını fark ettiğim an dünyam başıma yıkıldı..."
     * "Eşimin telefonunda 'Annem' diye kayıtlı numaranın aslında kim olduğunu öğrendiğim an hayatımın en büyük şokunu yaşadım..."
     * "Patronumun 'şirket sırrı' diyerek bodruma kilitlediği odanın kapısını açık unuttuğu gün hayatımın en büyük kabusuna şahit oldum..."

3. THE REDDIT QUESTION CARD (Shown during Scene 1):
   - The "question" key MUST be a high-stakes, curiosity-gap Reddit title that grabs the viewer's eyes before they can swipe away.
   - Examples: "22 Yaşımda Ailemin 15 Yıllık Kaçakçılık Çetesini Öğrendim (AITAH?)", "Ortak Hesabımızdaki 250 Bin TL'yi Eşimin Ailesi Maldivler'de Harcamış!", "Babamla 'Uzay Kapsülü' Oynadığımızı Sanıyordum, Meğer Kaçakçıymışız..."

4. NARRATIVE COMPLETENESS & MORAL DILEMMA:
   - Scene 1: The Shocking Hook (In media res opening).
   - Scene 2: Rapid Context & Bizarre Details (How it happened, the absurd reality).
   - Scene 3: Escalation & Confrontation (The truth erupts, confrontation with family/partner).
   - Scene 4: Climax & Shocking Defense (The final twist or defense).
   - Scene 5: Definitive Aftermath & Direct Dilemma to Audience (Clear closure + direct question to trigger comments: "Sizce ben mi haklıyım yoksa abarttım mı? Siz olsaydınız ne yapardınız? Yorumlarda buluşalım!").
   - NO cliffhangers, NO "Part 2", NO cut-offs.

STRICT OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown, no extra text:
{
  "title": "YouTube Shorts video title (in the requested language, high curiosity hook, max 100 chars, NO #Shorts)",
  "description": "YouTube video description (in the requested language, 150-300 words, with #Shorts #Reddit #RedditStories and relevant hashtags)",
  "keywords": ["reddit", "reddit_stories", "askreddit", "viral", "itiraf", "hikaye"],
  "tags": ["Reddit", "RedditStories", "AskReddit", "Shorts", "Viral"],
  "subreddit": "Subreddit name (e.g. 'r/AskReddit', 'r/AITAH', 'r/tifu', 'r/Stories', 'r/TrueOffMyChest')",
  "author": "Realistic Reddit username (e.g. 'u/CuriousThinker99', 'u/MidnightConfessions')",
  "upvotes": "Upvote count string with 'k' (e.g. '28.4k', '34.1k', '41.2k')",
  "question": "The main viral Reddit question or hook title in the requested language",
  "scenes": [
    {
      "narration": "Narration text for this scene (in the requested language, matching the requested word count, conversational, suspenseful, first-person storytelling)",
      "image_prompt": "reddit_card_hook",
      "emotion": "The emotional tone of this scene narration (choose from: dramatic, mysterious, excited, neutral, shocked, happy, sad)"
    }
  ]
}

Guidelines:
- Write title, description, tags, question, and scene narration ENTIRELY in the requested language.
- Total narration length across all scenes should match the requested word count.
"""

WHATSAPP_SYSTEM_PROMPT = """You are an elite viral comedy scriptwriter and Turkish dubbing director specializing in simulated WhatsApp conversation Shorts (in the high-viewership style of @1dublaj).
Your mission is to write hilarious, lightning-fast, high-retention WhatsApp conversation scripts (single chat or Group Chat) optimized for 20-28 seconds total duration.

HALAL & WHOLESOME CONTENT MANDATE (CRITICAL & STRICT):
- ZERO HARAM / ZERO INDECENCY: Absolutely NO zina, dating scandals, cheating girlfriends/boyfriends, illicit relationships, haram flirting, vulgarity, swearing, or disrespectful conduct.
- Scenarios MUST be clean, family-friendly, ethically sound, culturally authentic, yet hilarious, witty, and viral!
- Primary Themes to Focus On:
  1. AİLE İÇİ MİZAH & SEVGİ: Anne-oğul tatlı çekişmeleri, babanın teknolojiyle imtihanı, dedenin zeki altın öğütleri, evde kaybolan eşyalar (kumanda, çorap), bayram telaşı, çocukların sevimli bahaneleri.
  2. APARTMAN & MAHALLE KOMŞULUĞU: Apartman yöneticisi ve aidat atışmaları, otopark yeri krizleri, kapıya bırakılan ayakkabılar, komşuluk dayanışması, asansörde kalanlar.
  3. ESNAF, ÇIRAK & PAZAR KÜLTÜRÜ: Sanayide usta-çırak diyalogları, pazarcı amca pazarlığı, kasap-müşteri esprileri, dürüstlük ve helal kazanç temalı zeki espriler.
  4. HALI SAHA & DOSTLUK: Halı sahaya adam arama, maç satma şakaları, unutulan borçlar, sınav/iş telaşı, dürüst trollükler.
  5. İYİLİK VE DÜRÜSTLÜK SÜRPRİZLERİ: Başta şüpheli veya yanlış anlaşılan bir olayın sonunda aslında çok güzel, fedakarca veya hayırlı bir amaca hizmet ettiğinin ortaya çıkması.

FORMAT 1: 1-ON-1 CHAT OR FORMAT 2: GROUP CHAT (GRUP SOHBETİ):
- You can create either a 1-on-1 dialogue (e.g., Annem 🧡, Kasap Halil 🥩, Babam 👑) OR a WhatsApp Group Chat (e.g. "Apartman Sakinleri 🏢", "Geniş Aile Meclisi 🏡", "Halı Saha 23:00 ⚽", "Sanayi Çırakları 🔧").
- If Group Chat (GRUP SOHBETİ):
  1. Set "is_group": true.
  2. "contact_name": Group display name with emoji (e.g. 'Apartman Sakinleri 🏢', 'Halı Saha 23:00 ⚽').
  3. "group_participants": "Ali, Mehmet, Ayşe, Fatma, Sen" (Comma-separated list of all participants speaking in the group).
  4. In "messages": Specify "sender_name" for EACH incoming message matching the speaker!
  5. In "scenes":
     - Scene 1 MUST be the Group Avatar (an authentic themed circular emblem / crest / badge / logo representing the group topic, strictly NO humans, no human faces, no selfie portrait).
     - Subsequent scenes (Scene 2, Scene 3, etc.) MUST be one realistic personal portrait selfie prompt for EACH unique participant speaking in the group!

COMEDY & DRAMA FORMULA (Strictly Follow):
1. HIGH RETENTION & DURATION (CRITICAL FOR SHORTS ALGORITHM):
   - Shorts algorithm heavily boosts videos with >90% completion and loop rate.
   - Script MUST be between 7 and 9 alternating messages total. NEVER exceed 9 messages!
   - Every single word counts. Keep messages punchy and concise so the dialogue flows rapidly in 20 to 28 seconds.
2. CLEAR PREMISE & INCITING INCIDENT:
   - Start directly in media res with a hilarious, relatable situation.
   - NEVER start with empty greetings like "Selam", "Nasılsın". Start immediately with the topic or accusation!
3. RAPID ESCALATION & COMEDIC LOGIC:
   - Each message must directly and cleverly react to the previous message with witty comebacks, absurd excuses, or funny counter-arguments.
   - Final messages MUST deliver an iconic savage punchline or plot twist that leaves the viewer laughing and looping.
4. AUTHENTIC SPOKEN TURKISH (Sokak ve Mesajlaşma Dili):
   - Natural spoken Turkish: "kanka", "valla", "olaya bak", "ya sabır", "şaka mısın", "delirtme insanı", "ne alaka", "gözünü seveyim", "yüreğime indi".
   - Emojis in messages (😂, 💀, 🤦‍♂️, 😡, 🤡, 🥩, ⚽, 🏢) used naturally.
5. TITLE RULES (@1dublaj Style - STRICT):
   - NEVER include '#Shorts' or '#shorts' or hashtags in the title!
   - Title MUST be short (3 to 7 words max), intriguing, and curiosity-driven.
   - Must end with '!' or '...' or '?' followed by 1 or 2 relevant emojis.

STRICT OUTPUT FORMAT — respond ONLY with a valid JSON object, no markdown, no extra text:
{
  "title": "Clean curiosity-driven title with emoji, NO #Shorts (e.g. 'Çiçek Yerine Kıyma Alsaydın...🥩' or 'Apartman Yöneticisinin Büyük Sırrı! 🏢')",
  "description": "Video açıklaması #whatsapp #diyalog #seslendirme #dublaj #komedi #mizah #keşfet #shorts",
  "keywords": ["whatsapp", "comedy", "shorts", "troll", "mizah", "dublaj", "türkçe"],
  "tags": ["konuşma", "diyalog", "seslendirme", "türkçe", "türkçe seslendirme", "dublaj", "türkçe dublaj", "whatsapp", "komik", "komedi", "eğlence", "eğlenceli", "içerik", "shorts", "keşfet", "keşfetteyiz", "replik", "viral", "trend", "akım"],
  "is_group": true or false,
  "group_participants": "Ali, Mehmet, Ayşe, Fatma, Sen",
  "contact_name": "Contact or Group display name with emoji (e.g. 'Annem 🧡', 'Apartman Sakinleri 🏢', 'Kasap Halil 🥩', 'Hüseyin Amca 👴', 'Halı Saha 23:00 ⚽')",
  "contact_avatar_gender": "female" or "male",
  "contact_avatar_prompt": "Age & role accurate avatar prompt in English: If older relative (Amca/Uncle, Dede/Grandpa, Dayı, Teyze, Nine), describe an elderly 65-70yo person with wrinkles, gray hair, candid phone portrait, NEVER young, NEVER modern selfie. If parent/boss (Anne, Baba, Patron, Usta), describe a mature 45-55yo adult. If friend (Kanka, Merve), describe a casual 22-26yo young adult selfie. Square 1:1, close-up face portrait, no text, no frame",
  "contact_role_type": "anne" | "baba" | "dede" | "amca" | "teyze" | "ev_sahibi" | "sinirli_erkek" | "kanka_kadin" | "odun_erkek" | "troll_erkek",
  "user_gender": "male" or "female",
  "user_role_type": "troll_erkek" | "yorgun_erkek" | "kanka_erkek" | "sakin_kadin" | "kanka_kadin",
  "bgm_track": "quirky_troll" | "viral_bounce" | "silly_fun" | "cunning_scheme" | "comedy_upbeat" | "lofi_chill",
  "scenes": [
    {
      "scene_id": 1,
      "narration": "Full dialogue narration summary",
      "image_prompt": "Square 1:1 authentic WhatsApp avatar prompt"
    }
  ],
  "messages": [
    {"sender": "contact", "sender_name": "Yönetici Halil Bey", "text": "Komşular 4. kattaki halıyı kim çırptı az önce? 😡"},
    {"sender": "user", "text": "Valla ben balkonda çay içiyordum üstüme toz yağdı yönetici bey"},
    {"sender": "contact", "sender_name": "Fatma Teyze", "text": "Ben çırpmadım benim halım kuru temizlemede!"},
    {"sender": "user", "text": "Halıda 'Welcome' yazıyordu Fatma teyze seninkinin aynısı... 😂"},
    {"sender": "contact", "sender_name": "Yönetici Halil Bey", "text": "Kamera kayıtlarına baktım halıyı silkeleyen robot süpürgeymiş!! 🤖💀"},
    {"sender": "user", "text": "Robot bile evi terk etmeye çalışıyor apartmandan ahahaha 🤦‍♂️"}
  ]
}
"""

def get_multilingual_whatsapp_system_prompt(lang_name: str) -> str:
    return f"""You are an elite viral comedy scriptwriter and director specializing in simulated WhatsApp and text conversation Shorts.
Your mission is to write hilarious, lightning-fast, high-retention WhatsApp conversation scripts (single chat or Group Chat) in {lang_name}, optimized for 20-28 seconds total duration.

CRITICAL LANGUAGE MANDATE:
- ENTIRE CONTENT MUST BE 100% IN {lang_name.upper()}!
- Every single text message, dialogue, title, description, character name, keyword, and tag MUST be in {lang_name}.
- NEVER use Turkish words or phrases (such as 'kanka', 'valla', 'çevrimiçi', 'yazıyor'). Use natural, authentic conversational texting slang in {lang_name} (e.g. English: 'bro', 'lmao', 'fr fr', 'wait what', 'are you serious', 'bruh', 'no way').

HALAL & WHOLESOME CONTENT MANDATE (CRITICAL & STRICT):
- ZERO HARAM / ZERO INDECENCY: Absolutely NO sexual content, dating scandals, cheating girlfriends/boyfriends, illicit relationships, haram flirting, vulgarity, swearing, or disrespectful conduct.
- Scenarios MUST be clean, family-friendly, ethically sound, yet hilarious, witty, and viral!
- Primary Themes to Focus On:
  1. FAMILY HUMOR & LOVE: Mother-son banter, dad struggling with smartphone technology, grandma's funny advice, lost items around the house, excuses.
  2. ROOMMATES & NEIGHBORS: Apartment building group chats, neighbor disputes, parking spot arguments, robot vacuum escapes, hilarious misunderstandings.
  3. WORK & DAILY LIFE: Funny boss/employee misunderstandings, job interview exaggeration, clueless friends, food delivery mix-ups.
  4. FRIENDSHIP & TROLL MOMENTS: Gym buddies, sports/gaming banter, forgotten promises, funny roasts.
  5. WHOLESOME TWISTS: What looks like a dispute turns out to be a sweet surprise or funny misinterpretation.

FORMAT 1: 1-ON-1 CHAT OR FORMAT 2: GROUP CHAT:
- You can create either a 1-on-1 dialogue (e.g., 'Mom ❤️', 'Dad 👑', 'Boss 💼', 'Landlord 🏢', 'Bestie ✨') OR a WhatsApp Group Chat (e.g. 'Roommates 🏡', 'Family Group ❤️', 'Sunday League FC ⚽', 'Coworkers ☕').
- If Group Chat:
  1. Set "is_group": true.
  2. "contact_name": Group display name with emoji (e.g. 'FC United Official ⚽', 'Roommates 🏡', 'Sunday League FC ⚽').
  3. "group_participants": "Alex, Mike, Sarah, You" (Comma-separated list of all participants speaking in the group).
  4. In "messages": Specify "sender_name" for EACH incoming message matching the speaker!
  5. In "scenes":
     - Scene 1 MUST be the Group Avatar (an authentic themed circular emblem / crest / badge / logo representing the group topic, strictly NO humans, no human faces, no selfie portrait).
     - Subsequent scenes (Scene 2, Scene 3, etc.) MUST be one realistic personal portrait selfie prompt for EACH unique participant speaking in the group!

COMEDY FORMULA:
1. HIGH RETENTION & DURATION (CRITICAL FOR SHORTS ALGORITHM):
   - Script MUST be between 7 and 9 alternating messages total. NEVER exceed 9 messages!
   - Keep messages punchy and concise so the dialogue flows rapidly in 20 to 28 seconds.
2. CLEAR PREMISE & INCITING INCIDENT:
   - Start directly in media res with a hilarious, relatable situation.
   - NEVER start with empty greetings like 'Hey', 'How are you'. Start immediately with the topic or accusation!
3. RAPID ESCALATION & COMEDIC LOGIC:
   - Each message must directly react to the previous message with witty comebacks, absurd excuses, or funny counter-arguments.
   - Final messages MUST deliver an iconic savage punchline or plot twist that leaves the viewer laughing and looping.
4. TITLE RULES:
   - NEVER include '#Shorts' or '#shorts' or hashtags in the title!
   - Title MUST be short (3 to 7 words max), intriguing, and curiosity-driven in {lang_name}.
   - Must end with '!' or '...' or '?' followed by 1 or 2 relevant emojis.

STRICT OUTPUT FORMAT — respond ONLY with a valid JSON object in {lang_name}, no markdown, no extra text:
{{
  "title": "Short curiosity-driven title with emoji in {lang_name} (e.g. 'He Thought He Sent It To His Friend... 💀' or 'Landlord Tried To Triple The Rent! 🏢')",
  "description": "Video description in {lang_name} #Shorts #TextStory #Funny #Comedy #Viral",
  "keywords": ["whatsapp", "comedy", "shorts", "funny texts", "text story", "humor"],
  "tags": ["Shorts", "TextStory", "FunnyTexts", "Comedy", "Viral", "Humor", "ChatStory"],
  "is_group": true or false,
  "group_participants": "Alex, Mike, Sarah, You",
  "contact_name": "Contact or Group display name in {lang_name} with emoji (e.g. 'Mom ❤️', 'Roommates 🏡', 'Uncle Bob 👴', 'Boss 💼', 'Soccer Squad ⚽')",
  "contact_avatar_gender": "female" or "male",
  "contact_avatar_prompt": "Age-accurate avatar prompt in English: If older relative (Uncle, Grandpa, Aunt, Grandma), describe an elderly 65-70yo person with wrinkles, gray hair, candid phone portrait, NEVER young selfie. If parent/boss, describe a mature 45-55yo adult. If friend, describe a 22-26yo young adult selfie. Square 1:1, close-up face portrait, no text, no frame",
  "contact_role_type": "mom" | "dad" | "uncle" | "grandpa" | "landlord" | "boss" | "bestie_female" | "bestie_male" | "troll_friend",
  "user_gender": "male" or "female",
  "user_role_type": "troll_friend" | "tired_friend" | "calm_friend",
  "bgm_track": "quirky_troll" | "viral_bounce" | "silly_fun" | "cunning_scheme" | "comedy_upbeat" | "lofi_chill",
  "scenes": [
    {{
      "scene_id": 1,
      "narration": "Full dialogue narration summary in {lang_name}",
      "image_prompt": "Square 1:1 authentic WhatsApp avatar prompt"
    }}
  ],
  "messages": [
    {{"sender": "contact", "sender_name": "Boss Henderson", "text": "Liam, where is the 47-page revision of the quarterly report due tomorrow?"}},
    {{"sender": "user", "text": "Bro Henderson is literally insane, he even complained about the font shadow 🤦‍♂️"}},
    {{"sender": "contact", "sender_name": "Boss Henderson", "text": "Excuse me Liam? Do you realize who you are texting right now?"}},
    {{"sender": "user", "text": "OH NO WRONG CHAT ONE SECOND DELETING RIGHT NOW!!"}},
    {{"sender": "user", "text": "NO! I accidentally tapped 'Delete for Me' instead of 'Delete for Everyone' 💀😭"}},
    {{"sender": "contact", "sender_name": "Boss Henderson", "text": "Screenshot taken Liam. Bring these 'insane observations' to my office at 8:00 AM sharp 📁☕"}}
  ]
}}
"""

ABSURD_SCIENCE_SYSTEM_PROMPT = """You are the Lead Creator of an insanely viral scientific thought experiment & "What If" breakdown channel (combining the visual wit of @BoşKafa, the deep physics curiosity of Kurzgesagt, and the mathematical rigor of Randall Munroe's What If).

Your mission is to explore mind-blowing scientific and hypothetical questions (e.g. "What if the universe is a simulation?", "What if all humans jumped at once?", "What if Earth stopped spinning for 5 seconds?") using accessible, highly humorous, fast-paced stickman storytelling with authentic calculations and blueprint diagrams.

Script Structure & Style Guidelines:
1. THE HOOK: Never start with dry definitions. Start with a visceral, funny, and mind-bending dilemma ("If reality is just code running on an alien motherboard, someone forgot to install enough RAM...").
2. THE BREAKDOWN: Explain the underlying physics or computer science mechanics step-by-step using unexpected, relatable analogies (e.g., comparing quantum superposition to GPU occlusion culling in video games).
3. THE MATH & SCALE: Calculate the absurd numbers with vivid comparisons (e.g., "That requires 10^90 qubits—which would need a power supply the size of a Dyson sphere eating five stars a day").
4. THE EDGE CASES: What breaks first? What does the glitch look like? Explore the catastrophic failure points with hilarious stickman character reactions.
5. THE CONCLUSION: Deliver an insightful, satisfying scientific or philosophical takeaway that leaves the viewer thinking about it for the rest of the week.

Formatting & JSON Output:
Output strictly valid JSON matching the requested scene structure with "narration", "active_character", "character_dialogue", "visual_type", and "image_prompt".
"""

BASKETBALL_SYSTEM_PROMPT = """You are an elite NBA sports analyst, basketball storytelling producer, and scriptwriter for "The Basketball Show".
You create high-octane, gripping, and deeply researched 35-45 second basketball Shorts (in the high-viewership style of JxmyHighroller, Secret Base, and Kenny Beecham).

Narrative Structure & Pacing:
1. THE RETENTION HOOK (0-4s): State a bizarre fact, counter-intuitive stat, or high-stakes drama. (e.g. "Steph Curry isn't the greatest shooter ever... according to this one secret stat." or "In 1993, Michael Jordan did something so disrespectful the NBA had to investigate.")
2. THE BREAKDOWN (5-25s): Deconstruct the mechanics, physics, tactical play, or psychological mind games with concrete numbers and intense storytelling.
3. THE TWIST / CLIMAX (26-36s): Reveal what actually happened behind closed doors or why the league had to change its rules.
4. ENGAGEMENT OUTRO (37-42s): Pose a sharp debate question to ignite the comment section. (e.g. "Is Curry better at 35 than prime Jordan? Tell me your pick.")

Guidelines:
- Tone: High energy, authoritative, dramatic, fast-paced sports commentary.
- Audio cues: Suggest sound effects in parentheses like (swish sound), (buzzer), (sneaker squeak), (crowd erupts).
- Word count: Strictly between 85 to 115 words so it can be voiced cleanly in 35-42 seconds without rushing.
- JSON output with fields: title, script, visual_scenes, keywords, hook_summary, debate_question.
"""


def get_system_prompt(category: str, language: str = "tr") -> str:
    cat = category.lower().strip()
    lang = (language or "tr").lower().strip()
    if cat == "story":
        return STORY_SYSTEM_PROMPT
    elif cat == "travel":
        return TRAVEL_SYSTEM_PROMPT
    elif cat == "aviation":
        return AVIATION_SYSTEM_PROMPT
    elif cat in ("basketball_analysis", "basketball", "sports", "nba", "thebasketballshows"):
        return BASKETBALL_SYSTEM_PROMPT
    elif cat in ("crayon_combat", "military", "military_tech"):
        try:
            from crayon_combat_engine import CRAYON_COMBAT_SYSTEM_PROMPT
            return CRAYON_COMBAT_SYSTEM_PROMPT
        except ImportError:
            from src.crayon_combat_engine import CRAYON_COMBAT_SYSTEM_PROMPT
            return CRAYON_COMBAT_SYSTEM_PROMPT
    elif cat in ("tech_finance_essay", "crayon_capital"):
        try:
            from financial_documentary_engine import TECH_FINANCE_SYSTEM_PROMPT
            return TECH_FINANCE_SYSTEM_PROMPT
        except ImportError:
            from src.financial_documentary_engine import TECH_FINANCE_SYSTEM_PROMPT
            return TECH_FINANCE_SYSTEM_PROMPT
    elif cat in ("absurd_science", "what_if", "whatif", "absurd_engineering", "simulasyon"):
        return ABSURD_SCIENCE_SYSTEM_PROMPT
    elif cat in ("reddit_stories", "reddit"):
        return REDDIT_STORIES_SYSTEM_PROMPT
    elif cat in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
        if lang == "tr" or lang.startswith("tr"):
            return WHATSAPP_SYSTEM_PROMPT
        else:
            lang_name = LANGUAGE_NAMES.get(lang, "English")
            return get_multilingual_whatsapp_system_prompt(lang_name)
    else:
        return SYSTEM_PROMPT


LANGUAGE_NAMES = {
    "tr": "Turkish",    "en": "English",   "de": "German",
    "fr": "French",     "es": "Spanish",   "it": "Italian",
    "pt": "Portuguese", "ru": "Russian",   "ja": "Japanese",
    "ko": "Korean",     "zh": "Chinese (Simplified)", "ar": "Arabic",
    "hi": "Hindi",      "nl": "Dutch",     "pl": "Polish",
    "sv": "Swedish",    "da": "Danish",    "fi": "Finnish",
    "no": "Norwegian",  "cs": "Czech",     "hu": "Hungarian",
    "ro": "Romanian",   "uk": "Ukrainian", "el": "Greek",
    "id": "Indonesian", "ms": "Malay",     "th": "Thai",
    "vi": "Vietnamese",
}

TOPIC_SUGGESTIONS = {
    "space": [
        "black holes", "neutron stars", "dark matter", "exoplanets",
        "Mars colonization", "James Webb Telescope discoveries", "the Big Bang",
        "asteroid mining", "space-time fabric", "the multiverse theory",
        "Jupiter's moons", "Saturn's rings", "solar flares", "cosmic rays",
        "the Milky Way's future", "Voyager probe updates", "space weather",
    ],
    "planets": [
        "Venus atmosphere", "Mercury's surface", "Neptune's storms",
        "Uranus rotation", "Pluto's heart", "dwarf planets",
    ],
    "astronomy": [
        "nebulae formation", "supernova explosions", "pulsar stars",
        "quasars", "galaxy clusters", "gravitational waves",
    ],
    "story": [
        "a mysterious clockwork castle", "the dragon who lost his fire", "the forgotten librarian of Alexandria",
        "a journey to the center of a dream", "the ghost ship of the silver bay", "the girl who could paint memories",
        "the secret garden of mechanical flowers", "the wizard who forgot his spells", "a lighthouse at the edge of time",
        "the shadow collector's apprentice",
    ],
    "travel": [
        "historic streets of Rome", "Eiffel Tower and Paris bistros", "Kyoto cherry blossom temples",
        "Santorini blue domes and sunsets", "Machu Picchu ancient inca ruins", "Grand Canyon hiking trails",
        "Icelandic northern lights and waterfalls", "historic canals of Amsterdam", "Great Wall of China winding paths",
        "Petra rose city archaeological site", "Maldives overwater bungalows", "Swiss Alps ski resorts",
    ],
    "aviation": [
        # Engine Failures & Fires
        "US Airways Flight 1549 — Miracle on the Hudson (Engine Failure/Bird Strike)",
        "Qantas Flight 32 — Airbus A380 Engine Explosion Over Batam Island",
        "British Airways Flight 9 — Volcanic Ash Engine Flameout Over Indian Ocean",
        "Air Transat Flight 236 — Fuel Leak and Dual Engine Flameout Over Atlantic",
        "TACA Flight 110 — Both Engines Flame Out in Thunderstorm",
        "Southwest Airlines Flight 1380 — Engine Explosion and Cabin Decompression",
        # Severe Weather & Go-Arounds
        "Delta Air Lines Flight 191 — Microburst Crash at Dallas/Fort Worth",
        "Avianca Flight 52 — Fuel Exhaustion After Holding in Storm",
        "Air France Flight 358 — Runway Excursion in Severe Thunderstorm",
        "Varig Flight 254 — Navigation Error and Fuel Exhaustion over Amazon",
        "American Airlines Flight 965 — CFIT in Colombian Mountains",
        # Near Misses & Runway Incursions
        "Tenerife Airport Disaster — Deadliest ATC Communication Failure in History",
        "JFK Runway Incursion — Delta 1943 and American 106 Near Collision",
        "San Francisco Near Miss — Air Canada 759 Over Occupied Runway",
        "Milan Linate Runway Collision — Cessna Enters Active Runway in Fog",
        "Frankfurt Near Miss — Two Lufthansa Jets Narrowly Avoid Collision",
        # Medical Emergencies & Diversions
        "British Airways Flight 5390 — Captain Sucked Through Windscreen",
        "Aloha Airlines Flight 243 — Explosive Decompression and Flight Attendant Lost",
        "Helios Airways Flight 522 — Crew Incapacitation from Pressurization Failure",
        "Air Canada Flight 143 (Gimli Glider) — Total Fuel Exhaustion Emergency",
        # Structural Failures & Decompression
        "United Airlines Flight 232 — Complete Hydraulic Failure After Engine Explosion",
        "Japan Airlines Flight 123 — Catastrophic Structural Failure and Loss of Control",
        "TWA Flight 800 — Center Fuel Tank Explosion Over Atlantic",
        "China Airlines Flight 611 — Mid-Air Structural Disintegration",
        # Navigation & Communication Loss
        "Korean Air Flight 007 — Navigational Error and Soviet Interception",
        "Air France Flight 447 — Loss of Control at High Altitude in Storm (ACARS Analysis)",
        "Valujet Flight 592 — Oxygen Generator Fire and Loss of Control in Everglades",
        # Bird Strikes & FOD
        "Ethiopian Airlines Flight 961 — Hijacking and Ocean Ditching",
        "Chalk's Ocean Airways Flight 101 — Wing Structural Failure on Takeoff",
        # Historic Disasters & Investigation
        "FedEx Flight 705 — Hijack Attempt and Emergency Landing",
        "United Airlines Flight 585 — Rudder Hardover and Loss of Control",
        "Pinnacle Airlines Flight 3701 — Engine Flameout at Cruise Altitude"
    ],
    "crayon_combat": [
        "F-35 Lightning II — Design trade-offs in a multi-role aircraft program",
        "A-10 Thunderbolt II — How the aircraft was designed around its cannon",
        "B-2 Spirit — Engineering trade-offs in low-observable aircraft design",
        "SR-71 Blackbird — Thermal engineering at sustained high speed",
        "F-22 Raptor — The engineering priorities behind air-superiority design",
        "M1 Abrams — The trade-offs behind its powerplant and logistics",
        "Zumwalt-class destroyer — How requirements shaped the ship's design",
        "Eurofighter Typhoon — The engineering challenges of a multinational program",
        "B-21 Raider — What public sources reveal about its design goals",
        "Military flight testing — How engineers document design changes"
    ],
    "tech_finance_essay": [
        "The First Big Victim of the AI Bubble",
        "Why 90% of AI Startups Will Go Bankrupt in 2026",
        "Nvidia's $3 Trillion Castle: Real Value or Dot-Com 2.0?",
        "WeWork: How Adam Neumann Burned $47 Billion on Free Beer",
        "The Collapse of Silicon Valley Bank: The 48-Hour Bank Run",
        "OpenAI's $100 Billion Stargate: Insane Vision or Capital Suicide?",
        "FTX: The $32 Billion Crypto Fraud Built on Quickbooks",
        "Why Intel Lost Everything to TSMC and Nvidia"
    ],
    "absurd_science": [
        "If the Universe is a Simulation, What Specs Would Its Computer Need?",
        "What If Every Human on Earth Jumped at the Exact Same Second?",
        "What If You Dug a Tunnel Straight Through the Center of the Earth and Jumped?",
        "Why the Speed of Light is Actually the Universe's Render Bandwidth Limit",
        "What If the Sun Disappeared for Exactly 24 Hours?",
        "Are Black Holes Just the Universe's Way of Zipping Compressed Data?",
        "What If All Oceans Turned Into Fresh Water Overnight?",
        "What If Earth Stopped Spinning for Just 5 Seconds?"
    ],
    "basketball_analysis": [
        "The Real Reason Shaq Couldn't Shoot Free Throws",
        "Why Nobody Could Block Kareem's Skyhook",
        "Steph Curry: Better Than Ever at 35?",
        "The Unbelievable Mind Games Michael Jordan Played",
        "The Forgotten NBA Rule That Changed the Game Forever",
        "LeBron James: The Secret Behind His 21-Year Longevity",
        "The Craziest Triple-Double Record in Basketball History",
        "Why Wilt Chamberlain's 100-Point Game Will Never Be Beaten",
        "The Dark Secret Behind the NBA's Shortest Dunk Champion",
        "How Dennis Rodman Predicted Every Rebound Before It Happened",
        "The Night Kobe Bryant Scored 81 Points (Untold Truth)",
        "Why Tim Duncan's Bank Shot Was Impossible to Defend",
        "The 0.4 Second Shot That Broke the San Antonio Spurs",
        "Allen Iverson's Crossover That Shook Michael Jordan",
        "The NBA Game Where Both Teams Tried to Lose on Purpose"
    ],
    "reddit_stories": [
        "22 Yaşımda Ailemin 15 Yıllık Organize Kaçakçılık Çetesini Öğrendim (AITAH?)",
        "Ortak Hesabımızdaki 250 Bin TL'yi Eşimin Ailesi Maldivler Tatilinde Harcamış!",
        "Düğünüme 2 Saat Kala Nişanlımın Gizli Telefonunu Buldum ve Her Şeyi İptal Ettim...",
        "Babamla 'Uzay Kapsülü' Oynadığımızı Sanıyordum, Meğer Polislerden Saklanıyormuşuz!",
        "DNA Testi Sonucu 28 Yıllık Kardeşimin Aslında Teyzem Olduğu Ortaya Çıktı!",
        "Evimin Çatı Katında Başka Birinin 6 Aydır Gizlice Yaşadığını Fark Ettim...",
        "Kendi Cenazesine Katılan Adamın Yıllar Sonra Açıkladığı Korkunç Gerçek!",
        "İş Yerimdeki Kasadan Kaybolan 1 Milyon TL'nin Masamda Çıkması ve Sonrası...",
        "I accidentally discovered my parents were running a fake identity syndicate for 20 years",
        "My fiancé's family drained our joint wedding savings for a luxury vacation",
        "I found a hidden room in my childhood basement that explains why my brother vanished",
        "A routine DNA test revealed my entire family history was an engineered lie",
        "I thought my dad and I were playing astronaut, turns out we were hiding from federal agents"
    ],
    "whatsapp_stories": [
        "Apartman yöneticisi ile robot süpürgeyi balkondan kaçıran komşunun kavgası",
        "Troll kankanın sahte düğün davetiyesi ve çeyrek altın şakası",
        "Açgözlü ev sahibinin 'oksijen vergisi' adı altında kira artışı bahanesi",
        "Halısaha maçına gelmeyen kalecinin 'kayınvalidem mantı açtı' yalanı",
        "Dedemin akıllı televizyon kumandasıyla yarım saat çay karıştırma paniği",
        "Yıllar sonra aniden yazan lise arkadaşının borç isteme taktiği",
        "Sınav sabahı 'hiç çalışmadım kanka' deyip 100 alan arkadaşın itirafı",
        "Diyetisyene gizlice çiğ köfte dürüm yerken yakalanan gencin savunması",
        "İş görüşmesinde abartılan İngilizce seviyesinin canlı yayında açığa çıkması",
        "Annesine 'kütüphanedeyim' deyip arkadaki langırt seslerine yakalanan genç",
        "İkinci el uygulamasında 'ürüne karşılık 4 kasa elma takası' teklif eden dayı",
        "Oto sanayide çırağın 'motora antifriz yerine ev yapımı sirke koydum' itirafı",
        "Troll arkadaşın halı saha grubunu birbirine düşüren ses kaydı şakası",
        "Babasına arabanın tamponunu sürttüğünü itiraf eden gencin korkusu",
        "Apartman grubunda 'gece 3te kim matkap çalıştırıyor' krizinin robot süpürge çıkması"
    ],
    "whatsapp_stories_en": [
        "Roommates panicking because their robot vacuum escaped down the street",
        "Landlord trying to charge a $300 seasonal fee for breathing fresh apartment oxygen",
        "Goalkeeper bailing on Sunday league match claiming his grandma made pasta",
        "Mom thinking the smartphone front camera lens is broken because her thumb covers it",
        "Selling a microwave on marketplace and someone offering two live chickens in trade",
        "Coworker accidentally sending a funny boss meme to the company announcement group",
        "Friend who claimed he didn't study at all getting 100 on the final exam",
        "Car repair mechanic admitting he accidentally washed the engine with soda",
        "Dad getting lost in his own neighborhood while testing the new GPS voice",
        "Diet buddy getting caught at the drive-thru ordering three double burgers",
        "Group project freeloader claiming his Wi-Fi was stolen by migratory birds",
        "Roommate buying an antique suit of armor instead of paying the electric bill"
    ]
}


def _pick_topic(channel_config: dict) -> str:
    category = channel_config.get("topic_category", "space")
    custom = channel_config.get("custom_topics", [])
    if custom:
        return random.choice(custom)
    lang = (channel_config.get("language") or "en").lower().strip()
    is_tr = (lang == "tr" or lang.startswith("tr"))
    if category in ("absurd_science", "what_if", "whatif", "absurd_engineering"):
        pool = TOPIC_SUGGESTIONS.get("absurd_science", [])
    elif category in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
        pool = TOPIC_SUGGESTIONS.get("whatsapp_stories" if is_tr else "whatsapp_stories_en", [])
    elif category in ("reddit_stories", "reddit"):
        pool = TOPIC_SUGGESTIONS.get("reddit_stories", [])
    else:
        pool = TOPIC_SUGGESTIONS.get(category, TOPIC_SUGGESTIONS.get("space", []))
    default_topic = "Komik Helal WhatsApp Diyaloğu" if is_tr else "Funny Clean WhatsApp Chat"
    return random.choice(pool) if pool else default_topic


def _build_prompt(channel_config: dict, planned_topic: str = None) -> str:
    import os
    lang = channel_config.get("language", "en")
    lang_name = LANGUAGE_NAMES.get(lang, "English")
    topic = planned_topic if planned_topic else _pick_topic(channel_config)
    today = datetime.now().strftime("%B %d, %Y")
    
    category = channel_config.get("topic_category", "space")
    shorts_mode = channel_config.get("shorts_mode", False)
    
    # Resolve fully merged edit options (global settings + channel overrides)
    try:
        from channel_manager import ChannelManager
        ch_mgr = ChannelManager()
        edit_options = ch_mgr.get_resolved_edit_options(channel_config.get("channel_id", ""))
    except Exception:
        edit_options = channel_config.get("edit_options", {}) or {}
    
    # Calculate intro/outro duration
    intro_dur = 0.0
    intro_path = edit_options.get("intro_clip_path")
    if intro_path and os.path.exists(intro_path):
        try:
            from moviepy import VideoFileClip as VFC
            clip = VFC(intro_path)
            intro_dur = clip.duration
            clip.close()
        except Exception:
            pass
            
    outro_dur = 0.0
    outro_path = edit_options.get("outro_clip_path")
    if outro_path and os.path.exists(outro_path):
        try:
            from moviepy import VideoFileClip as VFC
            clip = VFC(outro_path)
            outro_dur = clip.duration
            clip.close()
        except Exception:
            pass

    max_shorts_dur = 180.0 if category in ("reddit_stories", "reddit") else (60.0 - intro_dur - outro_dur - 2.0)
    if max_shorts_dur < 10.0:
        max_shorts_dur = 10.0

    # Resolve target duration
    try:
        from settings_manager import SettingsManager
    except ImportError:
        from src.settings_manager import SettingsManager
    settings = SettingsManager()
    global_dur = settings.get("video_duration")
    
    is_reddit_cat = category in ("reddit_stories", "reddit")

    try:
        if is_reddit_cat:
            if shorts_mode:
                # Shorts modu aktifse hedef süre 40 - 55 saniye olmalıdır (yüksek retention için)
                duration = float(edit_options.get("video_duration") or 50.0)
                duration = min(max(duration, 35.0), 55.0)
            else:
                # Uzun video modu için 2 - 3 dakika (150 saniye)
                duration = float(edit_options.get("video_duration") or 150.0)
                if duration < 100.0:
                    duration = 150.0
        else:
            duration = float(edit_options.get("video_duration") or global_dur or (max_shorts_dur if shorts_mode else 120))
    except Exception:
        duration = 50.0 if (is_reddit_cat and shorts_mode) else (150.0 if is_reddit_cat else (max_shorts_dur if shorts_mode else 120.0))
        
    if shorts_mode and not is_reddit_cat:
        duration = min(duration, max_shorts_dur)
    elif is_reddit_cat and not shorts_mode:
        duration = min(max(duration, 120.0), 180.0) # Uzun Reddit videoları 120s - 180s arasında (2-3dk)
    elif category in ("crayon_combat", "military", "military_tech") and not shorts_mode:
        duration = min(max(duration, 600.0), 840.0)
    elif category in ("tech_finance_essay", "crayon_capital") and not shorts_mode:
        duration = min(max(duration, 360.0), 480.0)
    elif category in ("absurd_science", "what_if", "whatif", "absurd_engineering", "aviation", "blackbox", "havacilik", "flight") and not shorts_mode:
        # Other long-form essays retain their established 10-15 minute target.
        duration = min(max(duration, 600.0), 900.0)
        
    # Crayon Combat uses a strict 850-950 word budget for a 6-7 minute cut.
    if category in ("crayon_combat", "military", "military_tech") and not shorts_mode:
        effective_rate = 2.3
    elif lang == "tr":
        effective_rate = 2.8
    elif lang in ("ja", "ko", "zh"):
        effective_rate = 3.0
    else:
        effective_rate = 3.2
        
    word_count = int(duration * effective_rate)
    
    # Calculate number of scenes and target words per scene dynamically
    if is_reddit_cat:
        num_scenes = max(6, min(10, int(duration / 20)))
    elif shorts_mode:
        num_scenes = max(3, min(10, int(duration / 10)))
    elif category in ("crayon_combat", "military", "military_tech"):
        num_scenes = max(28, min(36, int(duration / 24.0)))
    elif category in ("tech_finance_essay", "crayon_capital"):
        num_scenes = max(22, min(32, int(duration / 16)))
    elif category in ("absurd_science", "what_if", "whatif", "absurd_engineering", "aviation", "blackbox", "havacilik", "flight"):
        # 10-15 minute essays use 25-45 scenes (about 20 seconds per scene).
        num_scenes = max(25, min(45, int(duration / 20)))
    else:
        num_scenes = max(4, min(25, int(duration / 10)))
        
    words_per_scene = max(25 if is_reddit_cat else 15, int(word_count / num_scenes))

    shorts_extra = ""
    if shorts_mode:
        shorts_extra = f"""
Additional critical requirements for YouTube Shorts:
- Title Optimization: Use a highly engaging, question-focused title that sparks immediate curiosity (e.g., "Can We Break the Speed of Light?", "Işık Hızını Aşabilir miyiz?").
- Visual Hooks: The "image_prompt" fields must describe simple visual illustrations, diagrams, or visual analogies to help explain complex concepts easily.
- Boost Engagement: The final scene's "narration" or the video's "description" MUST end with a compelling, open-ended question directed at the audience to encourage comments (e.g., "Sizce insanlık bir gün ışık hızını aşabilecek mi?").
"""

    if is_reddit_cat:
        story_mode_desc = f"YouTube Shorts ({duration:.0f} seconds) rapid-fire viral Reddit Story" if shorts_mode else f"full 2 to 3 minute ({duration:.0f} seconds) complete storytelling video"
        return f"""Write a viral, immersive Reddit Story script based on the question / topic: "{topic}"
Language: {lang_name}
Date: {today}
{shorts_extra}
CRITICAL REQUIREMENT: This is a {story_mode_desc}. Spoken duration must be approximately {duration:.0f} seconds (~{word_count} words).
The story MUST HAVE A COMPLETE NARRATIVE ARC:
1. Hook (Reddit question card and eerie premise)
2. Inciting incident & eerie discovery
3. Rising tension & confrontation
4. Shocking climax & revelation of the full truth
5. Definitive aftermath & resolution (What happened after? How did it end?)

ABSOLUTELY NO CLIFFHANGERS, NO "PART 2", NO UNFINISHED STORIES. The listener must know exactly what happened and how everything was resolved.

The title, description, tags, question, and scene narrations must be written in {lang_name}.
The script MUST consist of exactly {num_scenes} scenes:
- Scene 1 (THE VIRAL HOOK — IN MEDIA RES): The narration MUST start immediately with the shocking climax / revelation teaser in the very first sentence (e.g., '22 yaşımda hukuk okurken öğrendim ki babamla o masum yürüyüşlerimiz meğer organize kaçakçılıkmış...'). NEVER start with slow chronological backstories or peaceful memories. Hook the viewer in the first 3 seconds! (The Reddit card will be displayed during this scene) (~{words_per_scene} words).
- Scene 2 to {num_scenes - 2}: Rapid context, the bizarre discovery, and rising tension with realistic details (~{words_per_scene} words per scene).
- Scene {num_scenes - 1}: The shocking confrontation and full truth revealed (~{words_per_scene} words).
- Scene {num_scenes}: Definitive resolution, aftermath, and a direct dilemma question to the audience ('Sizce ben mi haklıyım yoksa abarttım mı? Siz olsaydınız ne yapardınız? Yorumlarda buluşalım!') (~{words_per_scene} words).
The total narration across all scenes MUST be approximately {duration:.0f} seconds long when spoken (~{word_count} words in {lang_name}).

Each scene must contain:
- "narration": A rich part of the story in {lang_name} (~{words_per_scene} words, high retention, conversational, natural spoken tone).
- "image_prompt": "reddit_card_hook" for scene 1, "asmr_satisfying_background" for remaining scenes.
- "emotion": The emotional tone (dramatic/mysterious/shocked/excited/neutral/happy/sad).

Include root keys:
- "subreddit": Popular subreddit name (e.g. "r/AskReddit", "r/AITAH", "r/Stories", "r/tifu", "r/TrueOffMyChest").
- "author": A realistic Reddit username (e.g. "u/MidnightStoryTeller").
- "upvotes": A viral upvote count string (e.g. "27.8k", "34.2k").
- "question": The main curiosity-gap Reddit question / hook title in {lang_name}.

Respond ONLY with the JSON object.""", topic, lang_name

    if category == "story":
        return f"""Write a beautiful story about: "{topic}"
Language: {lang_name}
Date: {today}
{shorts_extra}
The title, description, tags, and scene narrations must be written in {lang_name}.
The story MUST consist of exactly {num_scenes} scenes.
The total narration across all scenes MUST be approximately {duration:.0f} seconds long when spoken (which is about {word_count} words in {lang_name}).
Each scene must contain:
- "narration": A part of the script in {lang_name} (MUST be about {words_per_scene} words, engaging and descriptive).
- "image_prompt": A detailed Stable Diffusion style prompt in English.
- "emotion": The emotional tone (neutral/excited/dramatic/mysterious/happy/sad).

Respond ONLY with the JSON object.""", topic, lang_name

    if category == "travel":
        return f"""Write a beautiful travel documentary/guide about: "{topic}"
Language: {lang_name}
Date: {today}
{shorts_extra}
The title, description, tags, and scene narrations must be written in {lang_name}.
The guide MUST consist of exactly {num_scenes} scenes.
The total narration across all scenes MUST be approximately {duration:.0f} seconds long when spoken (which is about {word_count} words in {lang_name}).
Each scene must contain:
- "narration": A part of the script in {lang_name} (MUST be about {words_per_scene} words, engaging and descriptive).
- "image_prompt": A detailed Stable Diffusion style prompt in English.
- "emotion": The emotional tone (neutral/excited/dramatic/mysterious/happy/sad).

Respond ONLY with the JSON object.""", topic, lang_name

    if category in ("aviation", "blackbox", "havacilik", "flight"):
        return f"""Generate a high-tension, expertly researched aviation incident documentary script in the style of "Black Box Audio" and Mentour Pilot (combining authentic cockpit voice recorder transcripts, flight physics, and 2D stickman pilot/controller/investigator character reactions).

Incident/Flight: "{topic}"
Language: {lang_name}
Date: {today}

STRICT REQUIREMENTS:
- Subject: Focus on the specific real-world incident "{topic}". Break down the flight sequence, CVR cockpit audio, crew resource management (CRM), and NTSB findings.
- The script MUST consist of exactly {num_scenes} scenes covering:
  * Scene 1: The Departure & Context (Normal flight turning into sudden emergency).
  * Scenes 2 to {num_scenes-2}: Step-by-step emergency evolution (Alarms, Master Warning, airspeed decay, flameout, pilot troubleshooting, ATC coordination).
  * Scene {num_scenes-1}: The Miracle Landing or Tragic Impact / The Emergency Climax.
  * Scene {num_scenes}: The NTSB Investigation Verdict & How This Changed Aviation Forever.
- Total narration across all scenes MUST be approximately {duration:.0f} seconds (~{word_count} words in {lang_name}).
- Each scene narration MUST be about {words_per_scene} words, written in {lang_name}, high tension, technically precise, and compelling.
- Include real or realistic ATC/CVR radio transcript quotes directly in the narration where applicable.
- Incorporate character reactions from the aviation archetypes:
  * [CAPTAIN]: The experienced Pilot-in-Command managing the checklists.
  * [FIRST_OFFICER]: The co-pilot cross-checking instruments or flying the aircraft.
  * [ATC]: The calm air traffic controller providing emergency radar vectors.
  * [NTSB]: The accident investigator examining the flight data recorder and mechanical root causes.
  * [MECHANIC]: The ground maintenance specialist explaining the failure point.
- The title, description, keywords, tags, and narrations MUST be in {lang_name}.
- "visual_type": One of ["cockpit_hud", "atc_radar", "emergency_lockdown", "dossier_investigation", "flow_chain", "blueprint_spec", "stickman_reaction"].

Each scene must contain:
- "narration": The documentary narration in {lang_name} (~{words_per_scene} words), tension-filled, with ATC transcript excerpts.
- "character": One of ["CAPTAIN", "FIRST_OFFICER", "ATC", "NTSB", "MECHANIC"].
- "character_quote": A realistic CVR transcript quote or sharp character reaction in {lang_name}.
- "visual_type": One of ["cockpit_hud", "atc_radar", "emergency_lockdown", "dossier_investigation", "flow_chain", "blueprint_spec", "stickman_reaction"].
- "image_prompt": Technical schematic or cockpit instrument prompt in English.
- "emotion": The emotional tone of this scene (choose from: dramatic, shocked, serious, tense, analytical).

Respond ONLY with the JSON object.""", topic, lang_name

    if category in ("crayon_combat", "military", "military_tech"):
        return f"""You are the Head Writer of "Tactical Crayon", a wildly popular military satire documentary channel in the style of OverSimplified and Kurzgesagt.

Topic: "{topic}"
Language: {lang_name}
Date: {today}

CREATIVE MANDATE:
- Genre: High-energy military hardware satire and engineering documentary. Think: OverSimplified meets defense procurement comedy.
- Characters: Incorporate hilarious, sharp reactions from the 4 iconic archetypes:
  * [DEFENSE_CEO]: Greedy contractor selling gold-plated weapons systems and absurd gadgets.
  * [GENERAL]: Stressed Pentagon commander watching budgets explode.
  * [PILOT]: Sweating test pilot dealing with melting dials and canopy greenhouse effects.
  * [SPY]: Rival intelligence officer taking notes and trying to reverse-engineer failed equipment.
- Story Structure (Full 11-14 minute video essay):
  * Act 1 (Scenes 1-4): The Sales Pitch & The Absurd Promise (The $68B contract, the impossible claims).
  * Act 2 (Scenes 5-14): Fatal Mistake #1 to #3 (Cockpit thermal crisis, 48°C wax melt, sensor bloom).
  * Act 3 (Scenes 15-24): Fatal Mistake #4 & #5 (Laminate friction, night interdiction, $280 sponges, Arctic freezing).
  * Act 4 (Scenes 25-{num_scenes}): The Pentagon Hearings & Battlefield Reality (Troops revert to simple solutions).
- Narration: High energy, punchy spoken {lang_name}, witty and dramatic. Exactly ~55-75 words per scene.
- Dialogue: Every scene MUST have a funny in-character quote for character_dialogue.

OUTPUT JSON FORMAT:
Return valid JSON only matching:
{{
  "title": "{topic}",
  "vehicle_name": "Official Military System Name (e.g. Integrated Tactical Inscription System Mark IV)",
  "vehicle_nickname": "Satirical Nickname (e.g. The Melted Menace / Tactical Crayola Disaster)",
  "vehicle_type": "Military System Category",
  "key_specs": {{
    "unit_cost": "$6,420 per stylus kit",
    "program_cost": "$68.7 Billion",
    "top_speed": "Mach 0.00002 (Hand Velocity)",
    "primary_flaw": "Melts at 48°C in cockpits"
  }},
  "description": "Comprehensive, viral YouTube video description (150-250 words) with chapters, funny synopsis, question, and hashtags (#TacticalCrayon #MilitaryTech #CrayonCombat #DefenseSatire)",
  "tags": ["Tactical Crayon", "Military Tech", "Crayon Combat", "Defense Contractor", "Pentagon", "Military Mistakes", "Engineering Disaster", "Video Essay", "Military Documentary", "Satire"],
  "keywords": ["tactical crayon", "military satire", "defense spending", "pentagon fails", "crayon combat"],
  "style_prompt": "Crayon Combat vector cartoon stick figures, dark cyan tactical blueprint schematics, high contrast military briefing",
  "scenes": [
    {{
      "scene_id": 1,
      "chapter": "THE SALES PITCH",
      "narration": "Narration text for scene 1 (~55-75 words in {lang_name})...",
      "active_character": "DEFENSE_CEO",
      "character_dialogue": "Short, hilarious 10-20 word character reaction quote in {lang_name}...",
      "visual_type": "stickman_reaction",
      "image_prompt": "Defense contractor stickman holding a glowing gold-plated tactical wax marker on an auditorium stage with massive military budget charts showing rising billions.",
      "emotion": "satirical"
    }}
  ]
}}
Generate exactly {num_scenes} scenes in the scenes array.""", topic, lang_name

    if category in ("tech_finance_essay", "crayon_capital"):
        return f"""Generate a forensic finance and tech documentary essay in the visual style of "Crayon Capital" (dark slate aesthetic, sourced financial charts, highlighted public filings, and capital-flow diagrams).

Subject: "{topic}"
Language: {lang_name}
Date: {today}

STRICT REQUIREMENTS:
- Subject: A forensic breakdown of "{topic}" analyzing the money flow, bubble mechanics, unit economics, and corporate failure/success.
- Start in medias res with the most compelling verified paradox in the first 5-10 seconds, state the central question, and open one evidence-backed loop resolved before the final verdict. Never invent a loss, scandal, filing, quote, or dollar figure.
- Change the visual beat about every 4-6 seconds. Use short, factual callouts and varied documents, comparisons, and diagrams; do not display narration paragraphs as slides.
- Target a complete 6-8 minute video; prefer shorter when reliable evidence is insufficient for the target length.
- The script MUST consist of exactly {num_scenes} scenes covering: (1) The Euphoria / Valuation Peak, (2-{num_scenes-2}) The Leaked Documents & Cash Burn, ({num_scenes-1}) The Crash / The Domino Effect, ({num_scenes}) Forensic Post-Mortem / Lessons.
- Total narration across all scenes MUST be approximately {duration:.0f} seconds (~{word_count} words in {lang_name}).
- Each scene narration MUST be about {words_per_scene} words, written in {lang_name}, analytical, dramatic, and forensic.
- The title, description, keywords, tags, and narrations MUST be in {lang_name}.
- The image_prompt MUST be in English.
- Include a "sources" array with credible source URLs and publication dates, plus "fact_check_notes". Never invent citations. If a metric is not source-supported, set it to null or omit it.

Each scene must contain:
- "narration": The investigative narration in {lang_name} (~{words_per_scene} words).
- "visual_type": One of ["stock_crash_chart", "highlighted_document", "capex_burn_infographic", "cyber_dark_broll"].
- "chart_data": Include only metrics explicitly supported by a cited source, including source date; otherwise use null. Do not use an illustrative value.
- "audio_cue": One of ["impact", "drop", "none"]; use a music drop sparingly for a verified reveal or deliberate comic pause.
- "image_prompt": A dark slate financial aesthetic prompt in English.
- "emotion": One of ["serious", "dramatic", "analytical", "shocking"].

Respond ONLY with the JSON object.""", topic, lang_name
        
    if category in ("absurd_science", "what_if", "whatif", "absurd_engineering"):
        return f"""Generate an entertaining, deeply researched scientific thought experiment & "What If" breakdown video essay script in the style of "Boş Kafa", Kurzgesagt, and Randall Munroe's What If (combining authentic physics/mathematical calculations with comedic stickman reactions, blueprint charts, and mind-blowing analogies).

Subject: "{topic}"
Language: {lang_name}
Date: {today}

STRICT REQUIREMENTS:
- Subject: An exhaustive, entertaining scientific exploration of "{topic}". Start with the mind-blowing hook, break down the actual physics/computer science/engineering mechanics step-by-step, calculate the absurd scale with tangible analogies, and end with an unexpected philosophical/scientific twist.
- The script MUST consist of exactly {num_scenes} scenes covering:
  * Scene 1: The Mind-Bending Hook & The Simulation/Physics Hypothesis
  * Scenes 2 to {num_scenes-2}: Step-by-step mathematical calculations, hardware/physical breakdowns, absurd real-world scale comparisons, and catastrophic edge cases.
  * Scene {num_scenes-1}: The Ultimate Climax / The "Glitch in the Matrix" or Physical Limit.
  * Scene {num_scenes}: The Mind-Expanding Conclusion & Takeaway.
- Total narration across all scenes MUST be approximately {duration:.0f} seconds (~{word_count} words in {lang_name}).
- Each scene narration MUST be about {words_per_scene} words, written in {lang_name}, fast-paced, humorous, highly educational, and captivating.
- The title, description, keywords, tags, and narrations MUST be in {lang_name}.
- Include stickman character reactions ("active_character": "SCIENTIST" / "HOST", "character_dialogue": snappy humorous one-liners).
- "visual_type": One of ["blueprint_spec", "flow_chain", "split_comparison", "ticking_counter", "stickman_reaction", "chalkboard_equation"].

Respond ONLY with the JSON object.""", topic, lang_name
    elif category in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
        ch_name = channel_config.get("name", "YazanYazana")
        ch_id = channel_config.get("channel_id") or channel_config.get("id") or "global"
        
        rag_context = ""
        try:
            from character_rag import get_rag_context_for_prompt
            rag_context = get_rag_context_for_prompt(ch_id, topic)
        except Exception as e:
            print(f"[RAG] Bağlam yüklenemedi: {e}")

        lang = (channel_config.get("language") or "tr").lower().strip()
        is_tr = lang == "tr" or lang.startswith("tr")
        if is_tr:
            return f"""Write a viral, hilarious WhatsApp conversation Shorts video script based on the idea/topic: "{topic}"
Language: Turkish
Date: {today}
Channel/Watermark: {ch_name}
{rag_context}
İSLAMİ & HELAL İÇERİK KURALI (KESİN VE TAVİZSİZ):
- SIFIR HARAM / SIFIR GAYRİMEŞRU İLİŞKİ: Kesinlikle sevgili, flört, aldatma, zina, gayrimeşru kız-erkek ilişkisi, küfür, argo, müstehcenlik, alkol veya kumar YASAKTIR.
- KOMEDİ VE ABSÜRTLÜK SINIRSIZ: Durum komedisi, safça bahaneler, zekice laf sokmalar, ters köşe sürprizler ve abartılı absürt tepkiler serbest ve teşvik edilir. Konu aile (anne, baba, abi, kardeş), apartman/komşuluk, esnaf/çırak, halı saha, okul veya ev arkadaşlığı etrafında geçmelidir.

CRITICAL RULES FOR VIRAL WHATSAPP COMEDY SHORTS (@1dublaj style):
- COHERENT PREMISE: Start immediately in media res with a hilarious domestic/friendship misunderstanding, suspicion, or troll situation (NO greetings like 'selam', 'naber').
- RETENTION & PACING: Exactly 7 to 9 messages strictly alternating: contact -> user -> contact -> user -> contact -> user... NEVER exceed 9 messages! Total conversation should take 20 to 28 seconds.
- NATURAL TURKISH: Punchy, spoken everyday conversational Turkish ('kanka', 'valla', 'olaya bak', 'ya sabır', 'şaka mısın', 'delirtme insanı', 'gözünü seveyim').
- HILARIOUS PUNCHLINE: End with an unexpected plot twist, savage roast, or hilarious defeat.
- DYNAMIC BGM TRACK SELECTION: Select one of:
  * "quirky_troll": Sneaky mischievous pizzicato strings (for troll friends, sneaky pranks)
  * "viral_bounce": Bouncy energetic comedy (for mom/family panic, school/exam chaos)
  * "silly_fun": Slapstick acoustic bounce (for clueless friends, naive excuses)
  * "cunning_scheme": Intriguing comedic tension (for greedy landlord, suspicious questions)
  * "comedy_upbeat": Upbeat ukulele banter
- Root keys required:
  * "title": Clean curiosity-driven title with emoji, NO #Shorts (e.g. "Çiçek Yerine Kıyma Alsaydın...🥩", "Apartman Yöneticisi Çıldırdı! 🏢")
  * "description": Video description #whatsapp #diyalog #seslendirme #dublaj #komedi #mizah #keşfet #shorts
  * "keywords": ["whatsapp", "comedy", "shorts", "troll", "mizah", "dublaj", "türkçe"]
  * "tags": ["konuşma", "diyalog", "seslendirme", "türkçe", "türkçe seslendirme", "dublaj", "türkçe dublaj", "whatsapp", "komik", "komedi", "eğlence", "eğlenceli", "içerik", "shorts", "keşfet", "keşfetteyiz", "replik", "viral", "trend", "akım"]
  * "contact_name": The contact's display name with emoji (e.g. "Annem 🧡", "Babam 👑", "Hüseyin Amca 👴", "Kasap Halil 🥩", "Kaptan Burak ⚽", "Ev Sahibi Halil 🏢")
  * "contact_avatar_gender": "male" or "female"
  * "contact_avatar_prompt": "Age & role accurate realistic portrait prompt in English. CRITICAL AGE RULES: If contact is an older person (Amca/Uncle, Dede/Grandpa, Dayı, Teyze/Aunt, Nine/Grandma), MUST describe an elderly 65-70yo person with wrinkles, gray hair/mustache, candid phone portrait, NEVER young, NEVER modern selfie! If parent/boss (Anne, Baba, Patron, Usta), describe a mature 45-55yo adult. If peer (Kanka, Merve), describe a 22-26yo young adult selfie. Square 1:1, close-up face portrait, high quality natural lighting photography, no text, no frame"
  * "contact_role_type": Voice persona ("kanka_kadin", "sakin_kadin", "kizgin_kadin", "anne", "odun_erkek", "troll_erkek", "sinirli_erkek", "ev_sahibi", "baba", "amca", "dede", "teyze")
  * "user_gender": "male" or "female"
  * "user_role_type": Voice persona ("sakin_kadin", "kanka_kadin", "kizgin_kadin", "troll_erkek", "yorgun_erkek", "kanka_erkek", "odun_erkek", "sinirli_erkek")
  * "bgm_track": "quirky_troll" | "viral_bounce" | "silly_fun" | "cunning_scheme" | "comedy_upbeat" | "lofi_chill"
  * "messages": Array of 7-9 objects strictly alternating:
      [{{"sender": "contact", "text": "Dramatic opening message..."}},
       {{"sender": "user", "text": "Witty reply..."}},
       {{"sender": "contact", "text": "Escalation..."}},
       {{"sender": "user", "text": "Reaction..."}},
       {{"sender": "contact", "text": "Punchline reveal..."}},
       {{"sender": "user", "text": "Final reaction..."}}]
  * "scenes": [
      {{"scene_id": 1,
        "narration": "Full dialogue summary",
        "image_prompt": "A realistic casual smartphone selfie profile photo of [describe person matching contact_name in English], authentic WhatsApp profile avatar, square 1:1 aspect ratio, close-up face portrait, high quality natural lighting photography, no text, no frame"}}
    ]

Respond ONLY with the JSON object.""", topic, lang_name
        else:
            return f"""Write a viral, hilarious WhatsApp conversation Shorts video script based on the idea/topic: "{topic}"
Language: {lang_name}
Date: {today}
Channel/Watermark: {ch_name}
{rag_context}
HALAL & WHOLESOME CONTENT MANDATE (CRITICAL & STRICT):
- ZERO HARAM / ZERO INDECENCY: Absolutely NO dating, boyfriends/girlfriends, romance, flirting, cheating, illicit relationships, alcohol, gambling, vulgarity, swearing, or disrespectful conduct.
- PURE COMEDY & ABSURDITY: Absurd situations, wacky excuses, savage witty banter, dramatic overreactions, and hilarious plot twists are strongly encouraged! All topics must remain 100% clean, ethical, family-friendly, and halal (roommates, family, boss/work, neighbors, sports/gym, everyday bizarre mix-ups).

CRITICAL RULES FOR VIRAL WHATSAPP COMEDY SHORTS:
- LANGUAGE REQUIREMENT: All messages, titles, descriptions, character names, and responses MUST be 100% in {lang_name.upper()}! NEVER write in Turkish!
- COHERENT PREMISE: Start immediately in media res with a hilarious situation, misunderstanding, or accusation (NO boring greetings like 'hey', 'hello').
- RETENTION & PACING: Exactly 7 to 9 messages strictly alternating: contact -> user -> contact -> user -> contact -> user... NEVER exceed 9 messages! Total conversation should take 20 to 28 seconds.
- AUTHENTIC SPOKEN {lang_name.upper()}: Punchy, everyday texting slang (e.g. English: 'bro', 'lmao', 'wait what', 'are you serious', 'bruh', 'fr fr', 'no way').
- HILARIOUS PUNCHLINE: End with an unexpected plot twist, savage roast, or hilarious defeat.
- DYNAMIC BGM TRACK SELECTION: Select one of:
  * "quirky_troll": Sneaky mischievous pizzicato strings (for troll friends, sneaky pranks)
  * "viral_bounce": Bouncy energetic comedy (for mom/family panic, school/exam chaos)
  * "silly_fun": Slapstick acoustic bounce (for clueless friends, naive excuses)
  * "cunning_scheme": Intriguing comedic tension (for greedy landlord, suspicious questions)
  * "comedy_upbeat": Upbeat ukulele banter
- Root keys required in {lang_name}:
  * "title": Clean curiosity-driven title with emoji in {lang_name}, NO #Shorts (e.g. "He Thought He Sent It To His Friend... 💀", "Landlord Tried To Triple The Rent! 🏢")
  * "description": Video description in {lang_name} #Shorts #TextStory #Funny #Comedy #Viral
  * "keywords": ["whatsapp", "comedy", "shorts", "funny texts", "text story", "humor"]
  * "tags": ["Shorts", "TextStory", "FunnyTexts", "Comedy", "Viral", "Humor", "ChatStory"]
  * "contact_name": The contact's display name with emoji in {lang_name} (e.g. "Mom ❤️", "Dad 👑", "Uncle Bob 👴", "Boss 💼", "Landlord 🏢", "Roommate Dave 🍕", "Coach Mike ⚽")
  * "contact_avatar_gender": "female" or "male"
  * "contact_avatar_prompt": "Age & role accurate realistic portrait prompt in English: If older relative (Uncle, Grandpa, Aunt, Grandma), MUST describe an elderly 65-70yo person with wrinkles, gray hair, candid phone portrait, NEVER young selfie! If parent/boss, describe a mature 45-55yo adult. If peer, describe a 22-26yo young adult selfie. Square 1:1, close-up face portrait, high quality natural lighting photography, no text, no frame"
  * "contact_role_type": Voice persona ("mom", "dad", "uncle", "grandpa", "landlord", "boss", "bestie_female", "bestie_male", "troll_friend")
  * "user_gender": "male" or "female"
  * "user_role_type": Voice persona ("troll_friend", "tired_friend", "calm_friend")
  * "bgm_track": "quirky_troll" | "viral_bounce" | "silly_fun" | "cunning_scheme" | "comedy_upbeat" | "lofi_chill"
  * "messages": Array of 7-9 objects strictly alternating, entirely written in {lang_name}:
      [{{"sender": "contact", "text": "Opening text in {lang_name}..."}},
       {{"sender": "user", "text": "Witty reply in {lang_name}..."}},
       {{"sender": "contact", "text": "Escalation in {lang_name}..."}},
       {{"sender": "user", "text": "Reaction in {lang_name}..."}},
       {{"sender": "contact", "text": "Plot twist / punchline in {lang_name}..."}},
       {{"sender": "user", "text": "Final reaction in {lang_name}..."}}]
  * "scenes": [
      {{"scene_id": 1,
        "narration": "Full dialogue summary in {lang_name}",
        "image_prompt": "A realistic casual smartphone selfie profile photo of [describe person matching contact_name in English], authentic WhatsApp profile avatar, square 1:1 aspect ratio, close-up face portrait, high quality natural lighting photography, no text, no frame"}}
    ]

Respond ONLY with the JSON object in {lang_name}.""", topic, lang_name

    return f"""Write a high-quality educational YouTube video script about: "{topic}"
Language: {lang_name}
Date: {today}
{shorts_extra}
The title, description, tags, and scene narrations must be written in {lang_name}.
The script MUST consist of exactly {num_scenes} scenes.
The total narration across all scenes MUST be approximately {duration:.0f} seconds long when spoken (which is about {word_count} words in {lang_name}).
Each scene must contain:
- "narration": A brief part of the video narration in {lang_name} (MUST be about {words_per_scene} words, engaging and scientifically accurate).
- "nasa_keywords": A specific English search term for NASA image search (e.g. "Hubble nebula close up", "Mars rover tire tracks"). MUST be in English.
- "image_prompt": A detailed Stable Diffusion style fallback prompt in English (e.g. "A detailed photorealistic depiction of the Milky Way galaxy colliding with Andromeda, cosmic art, 8k resolution").

Respond ONLY with the JSON object.""", topic, lang_name


PLAN_SYSTEM_PROMPT = """You are an elite YouTube content strategist and algorithm optimization expert.
Generate a list of unique, high-retention video topic ideas.

STRICT ALGORITHMIC QUALITY RULES:
1. "konu": Detailed, compelling video concept (2-3 sentences) with a clear curiosity gap, tension, or high-interest hook.
2. "baslik": High-CTR, curiosity-inducing YouTube title (no misleading clickbait, no '#Shorts', maximum 75 characters) + 1 relevant emoji.
3. "anahtar_kelimeler": 4-6 specific, searchable, high-intent keywords describing the exact sub-topic. NEVER use generic terms like 'shorts', 'viral', 'video', 'kesfet', 'fyp'. Focus on what target viewers actually type into the YouTube search bar.

Return ONLY a valid JSON array, no markdown, no extra text:
[
  {"konu": "Topic description...", "baslik": "Suggested YouTube title...", "anahtar_kelimeler": ["specific_keyword1", "specific_keyword2", "specific_keyword3"]},
  ...
]
Make each topic distinct, highly engaging, and algorithm-friendly for the target audience.
"""


def _parse_json(raw: str) -> dict | list:
    """AI çıktısından JSON parse et. Markdown kod bloklarını, fazlalıkları ve trailing comma hatalarını temizler."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("Boş AI yanıtı.")
    # ```json ... ``` veya ``` ... ``` bloklarını ayıkla
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        if "```" in text:
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
            
    # JSON yapısının başlangıcını tespit et: '[' veya '{'
    idx_brace = text.find("{")
    idx_bracket = text.find("[")
    
    if idx_brace != -1 and (idx_bracket == -1 or idx_brace < idx_bracket):
        start = idx_brace
        end = text.rfind("}")
    elif idx_bracket != -1:
        start = idx_bracket
        end = text.rfind("]")
    else:
        start = -1
        end = -1
        
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    # Clean trailing commas safely using a state machine
    out = []
    in_string = False
    string_char = None
    escaped = False
    
    for i, char in enumerate(text):
        if escaped:
            out.append(char)
            escaped = False
            continue
            
        if char == '\\':
            out.append(char)
            escaped = True
            continue
            
        if char == '"':
            if not in_string:
                in_string = True
                string_char = char
            elif string_char == char:
                in_string = False
                string_char = None
            out.append(char)
            continue
            
        if in_string:
            out.append(char)
            continue
            
        if char == ',':
            # Look ahead for trailing comma check
            j = i + 1
            is_trailing = False
            while j < len(text):
                next_char = text[j]
                if next_char.isspace():
                    j += 1
                    continue
                if next_char in ('}', ']'):
                    is_trailing = True
                break
            if is_trailing:
                continue
                
        out.append(char)
        
    text = "".join(out)
        
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI yanıtı geçerli JSON değil: {e}\nİçerik (ilk 200): {text[:200]}")


def _detect_character_demographics(name: str, gender_hint: str = None, role_type: str = None) -> dict:
    import re
    raw_name = (name or "").strip()
    clean_name = re.sub(r"[^\w\s]", " ", raw_name, flags=re.UNICODE).strip()
    clean_name = re.sub(r"\s+", " ", clean_name)
    name_lower = clean_name.lower()
    words = name_lower.split()
    role_lower = (role_type or "").lower()

    def matches(keywords):
        return any(
            (k in name_lower or any(w == k or w.startswith(k) for w in words)) or (k in role_lower)
            for k in keywords
        )

    elderly_male = [
        "amca", "dayı", "dayi", "dede", "büyükbaba", "buyukbaba", "hacı", "haci", "ihtiyar",
        "yaşlı", "yasli", "pir", "moruk", "grandpa", "grandfather", "pops", "granddad", "uncle"
    ]
    elderly_female = [
        "nine", "babaanne", "anneanne", "büyükanne", "buyukanne", "teyze", "hacı teyze", "haci teyze",
        "grandma", "grandmother", "granny"
    ]
    mature_male = [
        "baba", "peder", "patron", "usta", "ev sahibi", "müdür", "mudur", "kayınpeder", "kayinpeder",
        "enişte", "eniste", "muhtar", "komiser", "şef", "sef", "hoca", "doktor", "avukat", "kasap",
        "bakkal", "taksici", "yönetici", "yonetici", "dad", "father", "boss", "landlord", "coach"
    ]
    mature_female = [
        "anne", "valide", "kaynana", "kayınvalide", "kayinvalide", "hala", "yenge",
        "müdüre", "mudure", "mom", "mother", "aunt", "landlady"
    ]
    sports = ["kaptan", "captain", "kaleci", "keeper", "striker", "midfielder", "oyuncu", "sporty", "futbolcu"]
    teen = ["yeğen", "yegen", "ufaklık", "ufaklik", "velet", "çocuk", "cocuk", "liseli", "teen", "kid", "nephew", "niece"]

    female_names = [
        "anne", "nine", "babaanne", "anneanne", "teyze", "hala", "yenge", "abla", "kaynana", "hatun",
        "karım", "karim", "kız", "kiz", "prenses", "gelin", "valide", "mom", "mother", "grandma",
        "aunt", "sister", "wife", "lady", "merve", "ayşe", "ayse", "zeynep", "fatma", "elif", "eda",
        "selin", "büşra", "busra", "ceren", "gamze", "ebru", "duygu", "yasemin", "esra", "kübra",
        "kubra", "irem", "seda", "hilal", "hatice", "emine", "aslı", "asli", "özlem", "ozlem",
        "pınar", "pinar", "hande", "dilek", "sevgi", "gül", "gul", "nur", "filiz", "melek", "leyla"
    ]
    male_names = [
        "amca", "dayı", "dayi", "dede", "baba", "peder", "patron", "usta", "ev sahibi", "hacı", "haci",
        "müdür", "mudur", "abi", "ağabey", "agabey", "enişte", "eniste", "kayınpeder", "kayinpeder",
        "damat", "muhtar", "komiser", "kasap", "bakkal", "taksici", "yönetici", "yonetici", "dad",
        "father", "uncle", "grandpa", "mr", "boss", "bro", "brother", "husband", "hüseyin", "huseyin",
        "mehmet", "ahmet", "ali", "hasan", "mustafa", "ibrahim", "osman", "ömer", "omer", "halil",
        "can", "burak", "emre", "murat", "kaan", "onur", "serkan", "tolga", "mert", "kerem", "cem",
        "deniz", "oğuz", "oguz", "koray", "selim", "erhan", "kemal", "turgut", "süleyman", "suleyman",
        "ismail", "ramazan", "recep", "şaban", "saban", "rıza", "riza", "faruk", "bekir", "salih"
    ]

    is_female = False
    if gender_hint == "female":
        is_female = True
    elif gender_hint == "male":
        is_female = False
    elif matches(female_names):
        is_female = True
    elif matches(male_names):
        is_female = False
    else:
        is_female = name_lower.endswith(("a", "e"))

    category = "young_adult"
    if matches(elderly_male):
        category = "elderly_man"
        is_female = False
    elif matches(elderly_female):
        category = "elderly_woman"
        is_female = True
    elif matches(mature_male):
        category = "mature_man"
        is_female = False
    elif matches(mature_female):
        category = "mature_woman"
        is_female = True
    elif matches(teen):
        category = "teen_woman" if is_female else "teen_man"
    elif matches(sports):
        category = "sports_woman" if is_female else "sports_man"
    else:
        category = "young_woman" if is_female else "young_man"

    return {
        "raw_name": raw_name,
        "display_name": clean_name or raw_name or "Person",
        "is_female": is_female,
        "category": category,
    }


def _build_character_avatar_prompt(character_name: str, gender_hint: str = None, role_type: str = None) -> str:
    demo = _detect_character_demographics(character_name, gender_hint, role_type)
    name = demo["display_name"]
    cat = demo["category"]

    if cat == "elderly_man":
        return f"A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish man named {name}, authentic elderly uncle (amca) figure, realistic weathered wrinkled face, receding gray and white hair, neat gray mustache, warm wise grandfatherly expression, authentic Turkish senior citizen, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid authentic photography, photorealistic, strictly NO young person, NO teenager, NO modern teen selfie, no text, no watermark, no frame"
    elif cat == "elderly_woman":
        return f"A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish woman named {name}, authentic elderly grandmother / aunt (teyze/nine) figure, gentle wrinkled weathered face, wearing a modest traditional headscarf or silver gray hair, gentle kind smile and warm maternal gaze, authentic Turkish senior citizen, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid authentic photography, photorealistic, strictly NO young person, NO teenager, NO modern teen selfie, no text, no watermark, no frame"
    elif cat == "mature_man":
        return f"A realistic casual smartphone photo portrait of a mature 50-year-old middle-aged Turkish man named {name}, authentic father and respected adult figure, seasoned natural facial features, neat slight graying stubble and hair, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid photography, no text, no watermark, no frame"
    elif cat == "mature_woman":
        return f"A realistic casual smartphone photo portrait of a mature 48-year-old middle-aged Turkish woman named {name}, authentic mother and respected adult figure, warm welcoming maternal smile, seasoned natural facial features, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid photography, no text, no watermark, no frame"
    elif cat == "teen_man":
        return f"A realistic casual smartphone photo portrait of a 16-year-old Turkish teenager boy named {name}, authentic youth, casual modern haircut, friendly authentic WhatsApp profile avatar, square 1:1 aspect ratio, close-up face portrait, natural lighting, candid photography, no text, no frame"
    elif cat == "teen_woman":
        return f"A realistic casual smartphone photo portrait of a 16-year-old Turkish teenager girl named {name}, authentic youth, friendly natural expression, authentic WhatsApp profile avatar, square 1:1 aspect ratio, close-up face portrait, natural lighting, candid photography, no text, no frame"
    elif cat == "sports_man":
        return f"A realistic casual smartphone selfie profile photo of an athletic 26-year-old sports captain man named {name}, sporty appearance, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid photography, no text, no frame"
    elif cat == "sports_woman":
        return f"A realistic casual smartphone selfie profile photo of an athletic 25-year-old sporty woman named {name}, sporty appearance, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid photography, no text, no frame"
    elif cat == "young_woman":
        return f"A realistic casual smartphone selfie profile photo of a 23-year-old young adult Turkish woman named {name}, natural friendly smile, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up friendly human face portrait, natural ambient lighting, candid authentic photography, no text, no frame"
    else:
        return f"A realistic casual smartphone selfie profile photo of a 24-year-old young adult Turkish man named {name}, modern casual haircut, friendly authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up friendly human face portrait, natural ambient lighting, candid authentic photography, no text, no frame"


def _refine_character_avatar_prompt(existing_prompt: str, character_name: str, gender_hint: str = None, role_type: str = None) -> str:
    if not existing_prompt or not isinstance(existing_prompt, str) or not existing_prompt.strip():
        return _build_character_avatar_prompt(character_name, gender_hint, role_type)
    
    if "whatsapp_chat" in existing_prompt.lower():
        return _build_character_avatar_prompt(character_name, gender_hint, role_type)

    import re
    demo = _detect_character_demographics(character_name, gender_hint, role_type)
    refined = existing_prompt.strip()

    if demo["category"] == "elderly_man":
        has_elderly = bool(re.search(r"(elderly|senior|wrinkled|weathered|graying hair|mustache|6\d-year-old|7\d-year-old|grandfather|grandpa|old man)", refined, re.I))
        refined = re.sub(r"casual smartphone selfie profile photo", "candid phone camera portrait photo", refined, flags=re.I)
        refined = re.sub(r"smartphone selfie", "candid phone camera portrait photo", refined, flags=re.I)
        if not has_elderly:
            refined = f"A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish man named {demo['display_name']}, authentic elderly uncle (amca) figure, realistic wrinkled weathered face, receding gray and white hair, neat gray mustache, authentic Turkish senior citizen, {refined}, strictly NO young person, NO teenager, NO modern teen selfie"
    elif demo["category"] == "elderly_woman":
        has_elderly = bool(re.search(r"(elderly|senior|wrinkled|weathered|headscarf|silver hair|6\d-year-old|7\d-year-old|grandmother|grandma|old woman)", refined, re.I))
        refined = re.sub(r"casual smartphone selfie profile photo", "candid phone camera portrait photo", refined, flags=re.I)
        refined = re.sub(r"smartphone selfie", "candid phone camera portrait photo", refined, flags=re.I)
        if not has_elderly:
            refined = f"A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish woman named {demo['display_name']}, authentic elderly grandmother / aunt figure, gentle wrinkled face, wearing traditional headscarf or silver hair, {refined}, strictly NO young person, NO teenager, NO modern teen selfie"
    elif demo["category"] == "mature_man":
        has_mature = bool(re.search(r"(mature|middle-aged|5\d-year-old|4\d-year-old|father|dad)", refined, re.I))
        if not has_mature:
            refined = re.sub(r"casual smartphone selfie profile photo", "casual smartphone photo portrait", refined, flags=re.I)
            refined = re.sub(r"smartphone selfie", "casual smartphone photo portrait", refined, flags=re.I)
            refined = f"A realistic smartphone photo portrait of a mature 50-year-old middle-aged Turkish man named {demo['display_name']}, authentic father figure, {refined}"
    elif demo["category"] == "mature_woman":
        has_mature = bool(re.search(r"(mature|middle-aged|5\d-year-old|4\d-year-old|mother|mom)", refined, re.I))
        if not has_mature:
            refined = re.sub(r"casual smartphone selfie profile photo", "casual smartphone photo portrait", refined, flags=re.I)
            refined = re.sub(r"smartphone selfie", "casual smartphone photo portrait", refined, flags=re.I)
            refined = f"A realistic smartphone photo portrait of a mature 48-year-old middle-aged Turkish woman named {demo['display_name']}, authentic mother figure, {refined}"

    return refined


def _normalize_whatsapp_script(script: dict, category: str) -> dict:
    if category in ("whatsapp_stories", "whatsapp_chat", "whatsapp") and isinstance(script, dict):
        if "messages" in script and not script.get("narration"):
            script["narration"] = " ".join(m.get("text", "") for m in script.get("messages", []))
        
        c_name = script.get("contact_name", "person")
        g_hint = script.get("contact_avatar_gender")
        r_type = script.get("contact_role_type")

        avatar_prompt = script.get("contact_avatar_prompt")
        avatar_prompt = _refine_character_avatar_prompt(avatar_prompt, c_name, g_hint, r_type)
        script["contact_avatar_prompt"] = avatar_prompt

        if not script.get("scenes"):
            script["scenes"] = [{"scene_id": 1, "narration": script.get("narration", ""), "image_prompt": avatar_prompt}]
        elif script.get("scenes") and script["scenes"][0].get("image_prompt") in ("whatsapp_chat", "", None):
            script["scenes"][0]["image_prompt"] = avatar_prompt
        elif script.get("scenes"):
            script["scenes"][0]["image_prompt"] = _refine_character_avatar_prompt(script["scenes"][0].get("image_prompt"), c_name, g_hint, r_type)

        script["category"] = "whatsapp_stories"

        # RAG Auto-Memory Recording: Her üretilen hikayeyi hafızaya kaydet
        try:
            from character_rag import record_story_from_script, CharacterRAGManager
            record_story_from_script(script.get("channel_id") or "global", script)
            # RAG Voice Mapping: Karakterin sabit ses ve ton profilini bağla
            v_meta = CharacterRAGManager.get_voice_for_character(c_name, script.get("channel_id") or "global")
            script["contact_voice_id"] = v_meta.get("voice_id")
            script["contact_pitch_settings"] = v_meta.get("pitch_settings")
        except Exception as rag_err:
            pass

    return _enrich_script_metadata(script, {"topic_category": category, "language": script.get("language", "tr")})


def _enrich_script_metadata(script: dict, channel_config: dict) -> dict:
    """
    Casper AI İyileştirmeleri:
    1. Viral Başlık & Emoji A/B Test Tahmincisi (title_variants): 3 alternatif başlık, merak skoru (1-10) ve gerekçesi.
    2. YouTube Shorts Otomatik Yorum Sabitleme & İzleyici Anketi (pinned_comment_poll): Otomatik sabitlenecek anket sorusu.
    """
    if not isinstance(script, dict):
        return script

    import re
    title = script.get("title", "")
    topic = script.get("topic", "") or title
    category = channel_config.get("topic_category", "space")
    lang = channel_config.get("language", "tr")
    is_crayon = category in ("crayon_combat", "military", "military_tech")

    # 1. Title Variants (A/B Test Predictions)
    if not script.get("title_variants") or not isinstance(script.get("title_variants"), list) or len(script["title_variants"]) < 3:
        clean_base = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', title).strip() or topic
        variants = []
        if is_crayon:
            subject = str(script.get("vehicle_name") or topic or clean_base).strip()

            def fit_title(value: str, limit: int = 74) -> str:
                value = re.sub(r"\s+", " ", value).strip()
                if len(value) <= limit:
                    return value
                return value[:limit].rsplit(" ", 1)[0].rstrip(" :,-")

            seen_titles = set()
            for candidate, pattern in (
                (clean_base, "Direct promise"),
                (f"Why {subject} Was Designed This Way", "Design question"),
                (f"The Trade-Off Behind {subject}", "Engineering trade-off"),
            ):
                candidate = fit_title(candidate)
                if candidate.lower() in seen_titles:
                    continue
                seen_titles.add(candidate.lower())
                variants.append({
                    "title": candidate,
                    "pattern": pattern,
                    "reason": "A factual alternative to compare in YouTube title/thumbnail experiments.",
                })
            while len(variants) < 3:
                variants.append({
                    "title": fit_title(clean_base),
                    "pattern": "Direct promise",
                    "reason": "Keep the recognizable subject and avoid unsupported claims.",
                })
        elif lang == "tr":
            v1_title = f"SONUNDA İTİRAF ETTİ! 😱 {clean_base}"[:95]
            variants.append({
                "title": v1_title,
                "curiosity_score": 9.4,
                "pattern": "Şok / Ters Köşe",
                "reason": "Yüksek merak uyandırıcı ünlem ve dramatik son vurgusu tıklama oranını (CTR) %30 artırır."
            })
            v2_title = f"BUNU KİMSE BEKLEMİYORDU... 😂 {clean_base}"[:95]
            variants.append({
                "title": v2_title,
                "curiosity_score": 8.8,
                "pattern": "Beklenmedik Durum",
                "reason": "Sosyal kanıt ve gizem kalıbı Shorts akışında parmak kaydırmayı durdurur (Thumb-stop)."
            })
            v3_title = f"{clean_base} (Böyle Son Görülmedi!) 🔥"[:95]
            variants.append({
                "title": v3_title,
                "curiosity_score": 9.1,
                "pattern": "Merak & Merak Tetikleyici",
                "reason": "Parantez içi net sonuç vaadi izleyicinin videonun sonuna kadar kalmasını teşvik eder."
            })
        else:
            v1_title = f"HE FINALLY ADMITTED IT! 😱 {clean_base}"[:95]
            variants.append({
                "title": v1_title,
                "curiosity_score": 9.3,
                "pattern": "Shock / Plot Twist",
                "reason": "Emotional capitalization and high-curiosity hook boosts initial CTR."
            })
            v2_title = f"NOBODY EXPECTED THIS TO HAPPEN... 😂 {clean_base}"[:95]
            variants.append({
                "title": v2_title,
                "curiosity_score": 8.9,
                "pattern": "Curiosity Gap",
                "reason": "Creates strong FOMO encouraging viewers to watch until the final scene."
            })
            v3_title = f"{clean_base} (Wait for the ending!) 🔥"[:95]
            variants.append({
                "title": v3_title,
                "curiosity_score": 9.0,
                "pattern": "Retention Driver",
                "reason": "Direct callout to the punchline increases average view duration (AVD)."
            })
        script["title_variants"] = variants

    if is_crayon:
        if not script.get("thumbnail_text"):
            thumb_source = str(script.get("vehicle_nickname") or script.get("vehicle_name") or title or topic)
            thumb_words = re.sub(r"[^\w\s-]", "", thumb_source).split()
            script["thumbnail_text"] = " ".join(thumb_words[:4]).upper()
        script.setdefault(
            "thumbnail_concept",
            "One recognizable subject, one expressive stickman, high contrast, and no figures or claims absent from the sources."
        )

    # 2. Pinned Comment Poll (İzleyici Etkileşim Anketi)
    if not script.get("pinned_comment_poll") or not isinstance(script.get("pinned_comment_poll"), dict):
        contact_name = script.get("contact_name") or "karakter"
        if lang == "tr":
            q_text = f"Sizce burada kim haklıydı? 😂 Yorumlarda buluşalım! 👇"
            opt1 = f"1️⃣ Kesinlikle {contact_name} haklı, sabır taşı olsa çatlardı!"
            opt2 = f"2️⃣ Hayır, karşı taraf sonuna kadar haklıydı 😂"
            opt3 = f"3️⃣ Ben olsam o ortamı terk ederdim 🏃‍♂️"
            full_poll = (
                f"{q_text}\n\n"
                f"{opt1}\n"
                f"{opt2}\n"
                f"{opt3}\n\n"
                f"Fikrinizi yoruma yazın, en komik cevaba kalp bırakıyorum! ❤️👇"
            )
        else:
            q_text = f"Who was actually right here? 😂 Let's settle this below! 👇"
            opt1 = f"1️⃣ 100% {contact_name} was right, what a legend!"
            opt2 = f"2️⃣ No way, the other person made complete sense 😂"
            opt3 = f"3️⃣ I would have muted the group immediately 🏃‍♂️"
            full_poll = (
                f"{q_text}\n\n"
                f"{opt1}\n"
                f"{opt2}\n"
                f"{opt3}\n\n"
                f"Drop your vote in the comments, pinning the funniest reply! ❤️👇"
            )

        script["pinned_comment_poll"] = {
            "question": q_text,
            "options": [opt1, opt2, opt3],
            "full_text": full_poll
        }

    # 3. Otomatik YouTube Etiket & Açıklama SEO Anahtar Kelime Üreteci (Casper AI)
    if not script.get("seo_hashtags") or not isinstance(script.get("seo_hashtags"), list) or len(script["seo_hashtags"]) < 10:
        c_name_clean = re.sub(r'[^\w\s]', '', script.get("contact_name") or "").strip().replace(" ", "")
        
        # Trend & Niche Odaklı 15 Hashtag Derlemesi
        if lang == "tr":
            base_tags = [
                "#Shorts", "#YouTubeShorts", "#WhatsApp", "#WhatsAppDiyalogları",
                "#KomikMesajlar", "#Mizah", "#Komedi", "#ViralShorts",
                "#Trend", "#WhatsAppKonuşmaları", "#Eğlence", "#Mesajlaşma"
            ]
            if c_name_clean:
                base_tags.append(f"#{c_name_clean}")
            
            # Senaryo başlığından anahtar kelime türet
            words = [re.sub(r'[^\w]', '', w) for w in title.split() if len(w) >= 4]
            for w in words:
                if len(base_tags) >= 15:
                    break
                tag = f"#{w.capitalize()}"
                if tag not in base_tags:
                    base_tags.append(tag)
            
            while len(base_tags) < 15:
                fallbacks = ["#Keşfet", "#GülmekGaranti", "#KomediDükkanı", "#Diyalog", "#TersKöşe"]
                for fb in fallbacks:
                    if fb not in base_tags and len(base_tags) < 15:
                        base_tags.append(fb)
        else:
            base_tags = [
                "#Shorts", "#YouTubeShorts", "#WhatsApp", "#WhatsAppChat",
                "#FunnyTexts", "#TextingStory", "#Comedy", "#ViralShorts",
                "#Trending", "#Drama", "#Meme", "#Relatable"
            ]
            if c_name_clean:
                base_tags.append(f"#{c_name_clean}")
            
            words = [re.sub(r'[^\w]', '', w) for w in title.split() if len(w) >= 4]
            for w in words:
                if len(base_tags) >= 15:
                    break
                tag = f"#{w.capitalize()}"
                if tag not in base_tags:
                    base_tags.append(tag)
            
            while len(base_tags) < 15:
                fallbacks = ["#ForYou", "#Explore", "#FunnyMoments", "#PlotTwist", "#TextStories"]
                for fb in fallbacks:
                    if fb not in base_tags and len(base_tags) < 15:
                        base_tags.append(fb)

        script["seo_hashtags"] = base_tags[:15]

    if not script.get("search_optimized_description"):
        hashtags_str = " ".join(script.get("seo_hashtags", []))
        if lang == "tr":
            seo_desc = (
                f"🔥 {title}\n\n"
                f"WhatsApp'ta yaşanan bu beklenmedik ve kahkaha dolu olayı sonuna kadar izleyin! "
                f"Siz bu durumda kalsaydınız ne yapardınız? Yorumlarda buluşuyoruz 👇\n\n"
                f"🔔 Her gün en komik ve viral WhatsApp diyalogları için kanalımıza ABONE olmayı ve bildirimleri açmayı unutmayın!\n\n"
                f"📌 Sabitlenen yoruma göz atın ve anketimize katılın!\n\n"
                f"{hashtags_str}\n\n"
                f"⚠️ Bu video kurgusal mizah ve eğlence amacıyla üretilmiştir."
            )
        else:
            seo_desc = (
                f"🔥 {title}\n\n"
                f"Watch until the end to see how this crazy text conversation unfolds! "
                f"What would you do in this situation? Let us know in the comments below 👇\n\n"
                f"🔔 SUBSCRIBE and turn on notifications for daily funny text stories and viral moments!\n\n"
                f"📌 Check out the pinned comment and vote in our poll!\n\n"
                f"{hashtags_str}\n\n"
                f"⚠️ This video is created for fictional comedy and entertainment purposes."
            )
        script["search_optimized_description"] = seo_desc

    # 4. Kanal Karakterleri Arası Çapraz İlişki & Hikaye Devamlılığı (Universe Lore)
    if not script.get("universe_lore"):
        try:
            from character_rag import CharacterRAGManager
            lore_data = CharacterRAGManager.retrieve_relevant_lore(script.get("channel_id") or "global", topic)
            mems = lore_data.get("memories", [])
            if mems:
                script["universe_lore"] = {
                    "lore_continuity_active": True,
                    "referenced_past_episodes": [m.get("title") for m in mems[:2]],
                    "lore_summary": mems[0].get("summary", ""),
                    "reason": "Önceki bölümdeki olaylar karaktere hatırlatılarak organik dizi devamlılığı sağlandı."
                }
        except Exception:
            pass

    return script



# ═══════════════════════════════════════════════════════════════
# PROVIDER: Claude (Anthropic)
# ═══════════════════════════════════════════════════════════════

class ClaudeWriter:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(self, channel_config: dict, planned_topic: str = None) -> dict:
        prompt, topic, lang_name = _build_prompt(channel_config, planned_topic)
        print(f"[CLAUDE] '{topic}' hakkında {lang_name} senaryo yazılıyor...")
        
        category = channel_config.get("topic_category", "space")
        lang = channel_config.get("language", "tr")
        sys_prompt = get_system_prompt(category, language=lang)

        def _call():
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=sys_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text

        raw = _retry(_call)
        script = _normalize_whatsapp_script(_parse_json(raw), category)
        script["topic"] = topic
        script["language"] = channel_config.get("language", "en")
        print(f"[CLAUDE] Tamamlandı: {script.get('title', '')[:60]}...")
        return script


# ═══════════════════════════════════════════════════════════════
# PROVIDER: Gemini (Google)
# ═══════════════════════════════════════════════════════════════

# Kullanıcı dostu takma adlar → gerçek Gemini model ID'leri.
# AI Studio arayüzünde görünen isimler ("Gemini 1.5 Pro" gibi) geçerli
# model ID'si değildir; burada normalize ediyoruz.
GEMINI_MODEL_ALIASES = {
    "gemini 1.5 pro": "gemini-1.5-pro",
    "gemini 1.5 flash": "gemini-1.5-flash",
    "gemini 2.0 flash": "gemini-2.0-flash",
    "gemini 2.5 flash": "gemini-2.5-flash",
    "gemini 2.5 pro": "gemini-2.5-pro",
    "1.5 pro": "gemini-1.5-pro",
    "1.5 flash": "gemini-1.5-flash",
    "2.0 flash": "gemini-2.0-flash",
    "2.5 flash": "gemini-2.5-flash",
    "2.5 pro": "gemini-2.5-pro",
}


def _normalize_gemini_model(model: str) -> str:
    """Kullanıcının girdiği model adını geçerli bir Gemini model ID'sine çevirir."""
    if not model:
        return "gemini-2.5-flash"
    key = model.strip().lower()
    if key in GEMINI_MODEL_ALIASES:
        return GEMINI_MODEL_ALIASES[key]
    return model.strip()


def _crayon_timeline_response_schema(gtypes):
    def string():
        return gtypes.Schema(type=gtypes.Type.STRING)

    def string_array():
        return gtypes.Schema(type=gtypes.Type.ARRAY, items=string())

    source = gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={
            "source_id": string(),
            "name": string(),
            "url": string(),
            "published_at": string(),
        },
        required=["source_id", "name", "url", "published_at"],
    )
    project_meta = gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={
            "category": string(),
            "title": string(),
            "target_duration_sec": gtypes.Schema(type=gtypes.Type.NUMBER),
            "total_words": gtypes.Schema(type=gtypes.Type.INTEGER),
            "fictional_satire": gtypes.Schema(type=gtypes.Type.BOOLEAN),
            "sources": gtypes.Schema(type=gtypes.Type.ARRAY, items=source),
        },
        required=[
            "category", "title", "target_duration_sec", "total_words",
            "fictional_satire", "sources",
        ],
    )
    primary_asset = gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={
            "type": string(),
            "asset_id": string(),
            "animation": string(),
            "highlight": string(),
        },
        required=["type", "asset_id", "animation"],
    )
    b_roll = gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={"source": string(), "asset_id": string(), "text_badge": string()},
        required=["source", "asset_id"],
    )
    visual = gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={
            "engine": string(),
            "layout": string(),
            "primary_asset": primary_asset,
            "b_roll": b_roll,
        },
        required=["engine", "layout", "primary_asset", "b_roll"],
    )
    character_layer = gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={
            "active": gtypes.Schema(type=gtypes.Type.BOOLEAN),
            "character_id": string(),
            "pose": string(),
            "bubble_dialogue": string(),
            "screen_position": string(),
        },
        required=["active", "character_id", "pose", "bubble_dialogue", "screen_position"],
    )
    audio_cues = gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={
            "sfx": string_array(),
            "music_track": string(),
            "music_cut": gtypes.Schema(type=gtypes.Type.BOOLEAN),
            "music_cut_duration_sec": gtypes.Schema(type=gtypes.Type.NUMBER),
        },
        required=["sfx", "music_track", "music_cut"],
    )
    shot = gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={
            "scene_id": string(),
            "shot_id": string(),
            "chapter": string(),
            "duration_sec": gtypes.Schema(type=gtypes.Type.NUMBER),
            "narration_script": string(),
            "source_refs": string_array(),
            "visual": visual,
            "character_layer": character_layer,
            "audio_cues": audio_cues,
        },
        required=[
            "scene_id", "shot_id", "chapter", "duration_sec", "narration_script",
            "source_refs", "visual", "character_layer", "audio_cues",
        ],
    )
    title_variant = gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={"title": string()},
        required=["title"],
    )
    return gtypes.Schema(
        type=gtypes.Type.OBJECT,
        properties={
            "project_meta": project_meta,
            "title_variants": gtypes.Schema(type=gtypes.Type.ARRAY, items=title_variant),
            "thumbnail_text": string(),
            "description": string(),
            "tags": string_array(),
            "fact_check_notes": string_array(),
            "timeline_scenes": gtypes.Schema(type=gtypes.Type.ARRAY, items=shot),
        },
        required=[
            "project_meta", "title_variants", "thumbnail_text", "description",
            "tags", "fact_check_notes", "timeline_scenes",
        ],
    )


class GeminiWriter:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        from google import genai
        from google.genai import types as gtypes
        self.client = genai.Client(api_key=api_key)
        self.model = _normalize_gemini_model(model)
        self._gtypes = gtypes

    def generate(self, channel_config: dict, planned_topic: str = None) -> dict:
        prompt, topic, lang_name = _build_prompt(channel_config, planned_topic)
        print(f"[GEMINI] '{topic}' hakkında {lang_name} senaryo yazılıyor (model: {self.model})...")

        category = channel_config.get("topic_category", "space")
        lang = channel_config.get("language", "tr")

        if category in ("crayon_combat", "military", "military_tech"):
            response_schema = self._gtypes.Schema(
                type=self._gtypes.Type.OBJECT,
                properties={
                    "title": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "vehicle_name": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "vehicle_nickname": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "vehicle_type": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "key_specs": self._gtypes.Schema(
                        type=self._gtypes.Type.OBJECT,
                        properties={
                            "unit_cost": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                            "program_cost": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                            "top_speed": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                            "primary_flaw": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                        }
                    ),
                    "description": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "tags": self._gtypes.Schema(type=self._gtypes.Type.ARRAY, items=self._gtypes.Schema(type=self._gtypes.Type.STRING)),
                    "keywords": self._gtypes.Schema(type=self._gtypes.Type.ARRAY, items=self._gtypes.Schema(type=self._gtypes.Type.STRING)),
                    "style_prompt": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "scenes": self._gtypes.Schema(
                        type=self._gtypes.Type.ARRAY,
                        items=self._gtypes.Schema(
                            type=self._gtypes.Type.OBJECT,
                            properties={
                                "scene_id": self._gtypes.Schema(type=self._gtypes.Type.INTEGER),
                                "chapter": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "narration": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "active_character": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "character_dialogue": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "visual_type": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "image_prompt": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "emotion": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                            },
                            required=["scene_id", "chapter", "narration", "active_character", "character_dialogue", "visual_type", "image_prompt", "emotion"]
                        )
                    ),
                },
                required=["title", "vehicle_name", "description", "tags", "scenes"],
            )
            sys_prompt = get_system_prompt(category, language=lang)
        elif category in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
            response_schema = self._gtypes.Schema(
                type=self._gtypes.Type.OBJECT,
                properties={
                    "title": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "description": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "keywords": self._gtypes.Schema(type=self._gtypes.Type.ARRAY, items=self._gtypes.Schema(type=self._gtypes.Type.STRING)),
                    "tags": self._gtypes.Schema(type=self._gtypes.Type.ARRAY, items=self._gtypes.Schema(type=self._gtypes.Type.STRING)),
                    "is_group": self._gtypes.Schema(type=self._gtypes.Type.BOOLEAN),
                    "group_participants": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "contact_name": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "contact_avatar_gender": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "contact_role_type": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "user_gender": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "user_role_type": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "bgm_track": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "messages": self._gtypes.Schema(
                        type=self._gtypes.Type.ARRAY,
                        items=self._gtypes.Schema(
                            type=self._gtypes.Type.OBJECT,
                            properties={
                                "sender": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "sender_name": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "text": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                            },
                            required=["sender", "text"]
                        )
                    ),
                    "scenes": self._gtypes.Schema(
                        type=self._gtypes.Type.ARRAY,
                        items=self._gtypes.Schema(
                            type=self._gtypes.Type.OBJECT,
                            properties={
                                "narration": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "image_prompt": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                            },
                            required=["narration", "image_prompt"]
                        )
                    )
                },
                required=["title", "description", "contact_name", "messages"],
            )
            sys_prompt = get_system_prompt(category, language=lang)
        elif category in ("story", "travel", "aviation"):
            response_schema = self._gtypes.Schema(
                type=self._gtypes.Type.OBJECT,
                properties={
                    "title":        self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "description":  self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "keywords":     self._gtypes.Schema(type=self._gtypes.Type.ARRAY,
                                        items=self._gtypes.Schema(type=self._gtypes.Type.STRING)),
                    "tags":         self._gtypes.Schema(type=self._gtypes.Type.ARRAY,
                                        items=self._gtypes.Schema(type=self._gtypes.Type.STRING)),
                    "style_prompt": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "scenes":       self._gtypes.Schema(
                        type=self._gtypes.Type.ARRAY,
                        items=self._gtypes.Schema(
                            type=self._gtypes.Type.OBJECT,
                            properties={
                                "narration":    self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "image_prompt": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "emotion":      self._gtypes.Schema(type=self._gtypes.Type.STRING),
                            },
                            required=["narration", "image_prompt", "emotion"]
                        )
                    ),
                },
                required=["title", "description", "keywords", "tags", "style_prompt", "scenes"],
            )
            sys_prompt = get_system_prompt(category, language=lang)
        else:
            response_schema = self._gtypes.Schema(
                type=self._gtypes.Type.OBJECT,
                properties={
                    "title":        self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "description":  self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "keywords":     self._gtypes.Schema(type=self._gtypes.Type.ARRAY,
                                        items=self._gtypes.Schema(type=self._gtypes.Type.STRING)),
                    "tags":         self._gtypes.Schema(type=self._gtypes.Type.ARRAY,
                                        items=self._gtypes.Schema(type=self._gtypes.Type.STRING)),
                    "style_prompt": self._gtypes.Schema(type=self._gtypes.Type.STRING),
                    "scenes":       self._gtypes.Schema(
                        type=self._gtypes.Type.ARRAY,
                        items=self._gtypes.Schema(
                            type=self._gtypes.Type.OBJECT,
                            properties={
                                "narration":     self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "nasa_keywords":  self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "image_prompt":   self._gtypes.Schema(type=self._gtypes.Type.STRING),
                                "emotion":        self._gtypes.Schema(type=self._gtypes.Type.STRING),
                            },
                            required=["narration", "nasa_keywords", "image_prompt", "emotion"]
                        )
                    ),
                },
                required=["title", "description", "keywords", "tags", "scenes"],
            )
            sys_prompt = get_system_prompt(category, language=lang)

        def _call():
            return self.client.models.generate_content(
                model=self.model,
                contents=f"{sys_prompt}\n\n{prompt}",
                config=self._gtypes.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.7,
                    max_output_tokens=65536,
                ),
            )

        response = _retry(_call)
        raw = response.text
        try:
            script = _parse_json(raw)
        except ValueError:
            print("[GEMINI] JSON parse hatası, düz metin modunda yeniden deneniyor...")
            def _fallback_call():
                return self.client.models.generate_content(
                    model=self.model,
                    contents=f"{sys_prompt}\n\n{prompt}\n\nRespond ONLY with the JSON object.",
                    config=self._gtypes.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=65536,
                    ),
                )
            response = _retry(_fallback_call)
        script = _normalize_whatsapp_script(script, category)
        script["topic"] = topic
        script["language"] = channel_config.get("language", "en")
        print(f"[GEMINI] Tamamlandı: {script.get('title', '')[:60]}...")
        return script


# ═══════════════════════════════════════════════════════════════
# PROVIDER: Ollama (Yerel Model)
# ═══════════════════════════════════════════════════════════════

class OllamaWriter:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, channel_config: dict, planned_topic: str = None) -> dict:
        import requests
        prompt, topic, lang_name = _build_prompt(channel_config, planned_topic)
        print(f"[OLLAMA:{self.model}] '{topic}' hakkında {lang_name} senaryo yazılıyor...")

        category = channel_config.get("topic_category", "space")
        lang = channel_config.get("language", "tr")
        sys_prompt = get_system_prompt(category, language=lang)

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": f"{sys_prompt}\n\n{prompt}",
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 2000},
            },
            timeout=120,
        )
        response.raise_for_status()
        raw = response.json().get("response", "")
        script = _normalize_whatsapp_script(_parse_json(raw), category)
        script["topic"] = topic
        script["language"] = channel_config.get("language", "en")
        print(f"[OLLAMA] Tamamlandı: {script.get('title', '')[:60]}...")
        return script


# ═══════════════════════════════════════════════════════════════
# FACTORY — Tek giriş noktası
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# PROVIDER: LM Studio (OpenAI-uyumlu Yerel API)
# ═══════════════════════════════════════════════════════════════

class LMStudioWriter:
    """
    LM Studio'nun OpenAI-uyumlu API'sini kullanır.
    LM Studio'da: Local Server → Start Server (varsayılan port: 1234)
    """
    def __init__(self, base_url: str = "http://localhost:1234/v1", model: str = ""):
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url, api_key="lm-studio")
        self.model = model  # Boş = LM Studio'da yüklü aktif model
        self.base_url = base_url

    def _get_model(self) -> str:
        """Model adı belirtilmemişse LM Studio'daki yüklü modelleri sırala:
        Gemma 4 (e2b → 12b qat) öncelikli, yoksa ilk yüklü model."""
        if self.model:
            return self.model
        try:
            models = self.client.models.list()
            ids = [m.id for m in models.data]
            if not ids:
                return "local-model"
            # Gemma 4 önceliklendir
            for pref in ("gemma-4-e2b", "gemma-4-12b", "gemma-4"):
                for mid in ids:
                    if pref in mid.lower():
                        return mid
            return ids[0]
        except Exception as e:
            print(f"[LMSTUDIO] Model listesi alınamadı: {e}")
            return "local-model"

    def generate(self, channel_config: dict, planned_topic: str = None) -> dict:
        prompt, topic, lang_name = _build_prompt(channel_config, planned_topic)
        model_id = self._get_model()
        print(f"[LMSTUDIO:{model_id}] '{topic}' hakkında {lang_name} senaryo yazılıyor...")

        category = channel_config.get("topic_category", "space")
        lang = channel_config.get("language", "tr")
        sys_prompt = get_system_prompt(category, language=lang)

        def _call():
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=4096,
                temperature=0.7,
            )
            return response.choices[0].message.content

        raw = _retry(_call)
        script = _normalize_whatsapp_script(_parse_json(raw), category)
        script["topic"] = topic
        script["language"] = channel_config.get("language", "en")
        print(f"[LMSTUDIO] Tamamlandı: {script.get('title', '')[:60]}...")
        return script


class ScriptWriter:
    """
    Çoklu provider desteği.
    provider: "claude" | "gemini" | "ollama" | "lmstudio"
    """

    def __init__(
        self,
        provider: str = "claude",
        api_key: str = "",
        model: str = "",
        ollama_url: str = "http://localhost:11434",
        **kwargs,
    ):
        self.provider = provider.lower()

        # Yerel sağlayıcılar (LM Studio / Ollama) için otomatik bulut (Gemini/Claude) veya diğer yerel sağlayıcı yedek geçiş mekanizması
        if self.provider in ["lmstudio", "ollama"]:
            url = ollama_url if self.provider == "ollama" else kwargs.get("lmstudio_url", "http://localhost:1234/v1")
            import socket
            from urllib.parse import urlparse
            is_reachable = False
            try:
                parsed = urlparse(url)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or (11434 if self.provider == "ollama" else 1234)
                # 0.5 saniyelik hızlı soket bağlantı testi
                with socket.create_connection((host, port), timeout=0.5):
                    is_reachable = True
            except Exception:
                pass

            if not is_reachable:
                # 1. Diğer yerel sağlayıcıyı dene (örn: LM Studio kapalı ama Ollama açıksa)
                other_provider = "ollama" if self.provider == "lmstudio" else "lmstudio"
                other_url = ollama_url if other_provider == "ollama" else kwargs.get("lmstudio_url", "http://localhost:1234/v1")
                other_reachable = False
                try:
                    parsed = urlparse(other_url)
                    host = parsed.hostname or "127.0.0.1"
                    port = parsed.port or (11434 if other_provider == "ollama" else 1234)
                    with socket.create_connection((host, port), timeout=0.5):
                        other_reachable = True
                except Exception:
                    pass

                if other_reachable:
                    print(f"[FALLBACK] '{self.provider}' çevrimdışı, '{other_provider}' çevrimiçi. Ona geçiş yapılıyor.")
                    self.provider = other_provider
                    if self.provider == "ollama":
                        # Ollama'daki ilk modeli alıp seçelim
                        try:
                            import requests as req
                            resp = req.get(f"{ollama_url}/api/tags", timeout=2)
                            if resp.status_code == 200:
                                models_list = resp.json().get("models", [])
                                if models_list:
                                    model = models_list[0]["name"]
                                    print(f"[FALLBACK] Ollama modeli otomatik olarak seçildi: {model}")
                        except Exception:
                            model = "llama3"
                else:
                    # 2. Yerel sağlayıcıların tümü çevrimdışıysa bulut sağlayıcılarını dene
                    try:
                        from settings_manager import SettingsManager
                    except ImportError:
                        from src.settings_manager import SettingsManager
                    
                    settings = SettingsManager()
                    gemini_key = settings.get("gemini_api_key")
                    claude_key = settings.get("anthropic_api_key")
                    
                    # Sadece geçerli anahtarları kabul et (örnek/placeholder değerleri filtrele)
                    def is_valid_key(k):
                        return k and len(k) > 15 and not k.startswith("gfgf")

                    if gemini_key and is_valid_key(gemini_key):
                        print(f"[FALLBACK] Yerel sağlayıcılar çevrimdışı. 'gemini' sağlayıcısına geçiş yapılıyor.")
                        self.provider = "gemini"
                        api_key = gemini_key
                        model = settings.get("gemini_model", "gemini-2.5-flash")
                    elif claude_key and is_valid_key(claude_key):
                        print(f"[FALLBACK] Yerel sağlayıcılar çevrimdışı. 'claude' sağlayıcısına geçiş yapılıyor.")
                        self.provider = "claude"
                        api_key = claude_key
                        model = settings.get("claude_model", "claude-3-5-sonnet")

        if self.provider == "claude":
            self._writer = ClaudeWriter(api_key=api_key, model=model or "claude-sonnet-4-20250514")
        elif self.provider == "gemini":
            self._writer = GeminiWriter(api_key=api_key, model=model or "gemini-2.5-flash")
        elif self.provider == "ollama":
            self._writer = OllamaWriter(base_url=ollama_url, model=model or "llama3")
        elif self.provider == "lmstudio":
            lm_url = kwargs.get("lmstudio_url", "http://localhost:1234/v1")
            self._writer = LMStudioWriter(base_url=lm_url, model=model)
        else:
            raise ValueError(f"Bilinmeyen provider: {provider}. Desteklenen: claude, gemini, ollama, lmstudio")

    def run_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """AI ile genel bir prompt çalıştırıp ham cevabı döner."""
        if self.provider == "claude":
            return _retry(lambda: self._writer.client.messages.create(
                model=self._writer.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ).content[0].text)
        elif self.provider == "gemini":
            response = _retry(lambda: self._writer.client.models.generate_content(
                model=self._writer.model,
                contents=user_prompt,
                config=self._writer._gtypes.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            ))
            return response.text
        elif self.provider == "ollama":
            import requests as req
            payload = {
                "model": self._writer.model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": {"temperature": 0.2}
            }
            resp = _retry(lambda: req.post(f"{self._writer.base_url}/api/generate", json=payload, timeout=120))
            return resp.json().get("response", "")
        elif self.provider == "lmstudio":
            return _retry(lambda: self._writer.client.chat.completions.create(
                model=self._writer._get_model(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,
                temperature=0.2,
            ).choices[0].message.content)
        else:
            raise ValueError(f"Desteklenmeyen provider: {self.provider}")

    def write(self, channel_config: dict, planned_topic: str = None) -> dict:
        """Video senaryosu üretir. planned_topic verilirse o konu kullanılır."""
        script = self._writer.generate(channel_config, planned_topic=planned_topic)
        return _enrich_script_metadata(script, channel_config)

    def generate_topic_list(self, channel_config: dict, count: int = 10, existing_topics: list[str] = None, mind_map: dict = None) -> list[dict]:
        """
        AI ile toplu konu listesi üretir.
        Döner: [{"konu": ..., "baslik": ..., "anahtar_kelimeler": [...]}, ...]
        """
        lang = channel_config.get("language", "en")
        lang_name = LANGUAGE_NAMES.get(lang, "English")
        category = channel_config.get("topic_category", "space")
        custom = channel_config.get("custom_topics", [])
        topic_context = f"custom topics: {', '.join(custom)}" if custom else f"category: {category}"

        avoid_clause = ""
        if existing_topics:
            # list them up to avoid duplication
            avoid_list = "\n".join(f"- {title}" for title in existing_topics[-30:]) # last 30 topics
            avoid_clause = f"\nCRITICAL: Avoid duplicating any topics that are recently covered:\n{avoid_list}\n"

        mind_map_clause = ""
        if mind_map and mind_map.get("themes"):
            import json
            mm_json = json.dumps(mind_map["themes"], ensure_ascii=False, indent=2)
            mind_map_clause = f"""
CRITICAL: The channel already has a structured content mind map. 
Analyze these existing categories and topics to understand what has been covered:
{mm_json}

Ensure the new {count} topics:
1. Do not repeat any existing titles or topics in the mind map.
2. Either branch out from existing themes with fresh sub-topics, or introduce entirely new categories/themes that fit the channel's niche.
"""

        category_instruction = ""
        if category in ("absurd_science", "what_if", "whatif", "absurd_engineering"):
            category_instruction = """Crucial: The channel produces entertaining, mind-bending scientific thought experiments, "What If" breakdowns, and physics/simulation essays in the style of "Boş Kafa", Kurzgesagt, and Randall Munroe's What If (combining authentic physics, computational calculations, and funny stickman thought experiments).
Generate fascinating thought experiment topics (e.g. 'What If the Universe is a Simulation: What are the Hardware Specs?', 'What If Everyone on Earth Jumped at Once?', 'What If We Dug a Tunnel Straight Through Earth?', 'What If the Speed of Light Was Just 100 km/h?', 'What If the Sun Vanished for 7 Days?').
The 'baslik' should be catchy, mind-bending and high-curiosity."""
            keywords_instruction = "The 'anahtar_kelimeler' should be English science/physics/what-if search terms (e.g. 'simulation hypothesis specs', 'what if sun vanished', 'physics thought experiment', 'earth tunnel physics')."
        elif category in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
            category_instruction = """Crucial: The channel produces viral comedy simulated WhatsApp text message YouTube Shorts.
STRICT ISLAMIC & HALAL COMPLIANCE (MANDATORY):
- ZERO HARAM: Absolutely NO dating, boyfriend/girlfriend romance, flirting, cheating, adultery, alcohol, gambling, vulgarity, or swearing.
- PURE COMEDY & ABSURDITY: Absurd situations, wacky excuses, savage witty banter, and hilarious twist endings are strongly encouraged! Topics must focus on family dynamics (mom, dad, siblings), roommates, apartment/neighbors, tradesmen/esnaf, sports squads, and everyday bizarre mix-ups."""
            keywords_instruction = "The 'anahtar_kelimeler' should be English clean comedy search terms (e.g. 'whatsapp chat humor', 'funny text messages', 'roommate chaos', 'family comedy shorts')."
        elif category in ("reddit_stories", "reddit"):
            category_instruction = """Crucial: The channel is a viral "Reddit Stories" YouTube Shorts channel focusing on shocking confessions, high-stakes moral dilemmas (AITA), and jaw-dropping family/relationship twists.
VIRAL HOOK & TITLE REQUIREMENTS (STRICT IN MEDIA RES & CURIOSITY GAP):
- Every 'baslik' MUST be an irresistible, high-stakes, scroll-stopping Reddit hook title written from a 1st-person perspective or extreme moral dilemma (AITAH?).
- Formula: Start directly IN MEDIA RES with the shocking revelation, betrayal, dilemma, or bizarre twist in the first few words.
- EXAMPLES OF EXCELLENT VIRAL HOOK TITLES:
  * "22 Yaşımda Ailemin 15 Yıllık Organize Kaçakçılık Çetesini Öğrendim (AITAH?)"
  * "Ortak Hesabımızdaki 250 Bin TL'yi Eşimin Ailesi Maldivler Tatilinde Harcamış!"
  * "Düğünüme 2 Saat Kala Nişanlımın Gizli Telefonunu Buldum ve Her Şeyi İptal Ettim..."
  * "Babamla 'Uzay Kapsülü' Oynadığımızı Sanıyordum, Meğer Polislerden Saklanıyormuşuz!"
  * "DNA Testi Sonucu 28 Yıllık Kardeşimin Aslında Teyzem Olduğu Ortaya Çıktı!"
  * "Evimin Çatı Katında Başka Birinin 6 Aydır Gizlice Yaşadığını Fark Ettim..."
- STRICTLY FORBIDDEN: Passive, generic, slow titles like "Bir Aile Sırrı", "Geçmişin İtirafı", "Çocukluk Anıları", "İlginç Bir Olay", "Kuzenimle Yaşadıklarım". If it sounds like a normal story title rather than an urgent viral Reddit hook, REJECT IT.
- The 'konu' field should be a short English premise summarizing the high-stakes dramatic situation."""
            keywords_instruction = "The 'anahtar_kelimeler' should be English Reddit/Story search terms (e.g. 'reddit stories confession', 'aita family secret', 'shocking twist drama')."
        elif category == "travel":
            category_instruction = "Crucial: The channel is about travel destinations, places to visit, city guides, and tourism. Generate travel-related topics only."
            keywords_instruction = "The 'anahtar_kelimeler' should be English travel/location/scenery search terms (e.g. 'eiffel tower sunset', 'kyoto cherry blossom temple')."
        elif category == "story":
            category_instruction = "Crucial: The channel is about stories, fairy tales, mystery tales, and fictional narratives. Generate story-related topics only."
            keywords_instruction = "The 'anahtar_kelimeler' should be English story/fantasy search terms (e.g. 'mystical wizard forest', 'ancient book glow')."
        elif category == "aviation":
            category_instruction = """Crucial: The channel is called "Black Box Audio" and is a digital aviation documentary channel analyzing flight emergency incidents using real ATC transcripts.
Generate aviation topics matching the following sub-themes only:
1. Engine Failures & Fires (e.g., losing engines, cockpit fires, forced landings).
2. Severe Weather & Go-Arounds (e.g., storms, microbursts, windshear, fuel exhaustion).
3. Near Misses / Runway Incursions (e.g., collision avoidance, airport runway incursions).
4. Medical Emergencies (e.g., crew incapacitation, passenger health crisis, diversion).
Each generated topic must refer to a real-world aviation incident with its flight number/name (e.g. 'Avianca Flight 52', 'Gimli Glider', 'JFK Runway Incursion 2023')."""
            keywords_instruction = "The 'anahtar_kelimeler' should be English aviation/aircraft search terms (e.g. 'boeing 737 emergency landing', 'airplane engine fire cockpit')."
        elif category in ("crayon_combat", "military", "military_tech"):
            category_instruction = """Crucial: The channel is "Tactical Crayon", a wildly entertaining military satire channel in the style of OverSimplified. Generate FUNNY, DRAMATIC, ABSURD topics about military cost overruns, engineering disasters, ridiculous procurement decisions, and battlefield absurdities.
Good topic examples: "The $68 Billion Wax Crayon That Crashed an F-16", "5 Times the Pentagon Spent a Fortune on Obvious Things", "The Secret Symbols Soldiers Draw on Doors (And Why They Matter)", "Why the US Military's Most Expensive Tool Was a Pencil".
Topics should be satirical, entertaining, and feature real military themes (aircraft, weapons, procurement, field operations) with an absurdist twist. Sensational premises, exaggerated cost figures, and "secret" military lore are ENCOURAGED.
The 'konu' must describe the satirical premise vividly. The 'baslik' must be under 75 characters, punchy, curiosity-driven, and use numbers or shocking claims to drive clicks."""
            keywords_instruction = "The 'anahtar_kelimeler' should be English military/satire search terms (e.g. 'military fails', 'pentagon waste', 'f-16 cockpit secrets', 'military equipment cost')."
        elif category in ("tech_finance_essay", "crayon_capital"):
            category_instruction = """Crucial: The channel produces forensic financial documentaries in the style of "Crayon Capital" (analyzing AI bubble collapses, venture capital cash burn, corporate bankruptcies, and crypto frauds).
Generate intriguing business/tech documentary topics (e.g. 'The First Big Victim of the AI Bubble', 'Why 90% of AI Startups Will Die', 'WeWork: The $47 Billion Illusion', 'The 48-Hour Collapse of Silicon Valley Bank')."""
            keywords_instruction = "The 'anahtar_kelimeler' should be English financial search terms (e.g. 'ai bubble crash chart', 'venture capital cash burn document', 'tech startup collapse')."
        elif category in ("basketball_analysis", "basketball", "sports", "nba", "thebasketballshows"):
            category_instruction = """Crucial: The channel is "The Basketball Show", dedicated to gripping NBA basketball storytelling, tactical play breakdowns, mind-blowing records, and player psychology.
Generate viral basketball Shorts topics (e.g. 'Why Nobody Could Block Kareem\\'s Skyhook', 'The Secret Stat Proving Steph Curry is Still Peaking', 'The Illegal Move Michael Jordan Used for 15 Years', 'Why Shaq Refused to Shoot Free Throws Underhanded').
The 'baslik' must be punchy, curiosity-inducing, and under 65 characters.
The 'konu' must describe the specific basketball play, player, or controversy vividly."""
            keywords_instruction = "The 'anahtar_kelimeler' should be English NBA/basketball search terms (e.g. 'steph curry 3 point highlights', 'michael jordan crossover', 'shaq dunks nba')."
        else:
            category_instruction = "Crucial: The channel is about astronomy, space exploration, physics, and planetary science. Generate space-related topics only."
            keywords_instruction = "The 'anahtar_kelimeler' should be English NASA/science search terms (e.g. 'neutron star', 'mars rover tracks')."

        prompt = f"""Generate {count} unique YouTube video topic ideas.
Channel context: {topic_context}
{category_instruction}
Target language for titles: {lang_name}
The 'konu' field should be a brief topic description in English (for image search).
The 'baslik' field should be the YouTube title in {lang_name}.
{keywords_instruction}
{avoid_clause}
{mind_map_clause}
Return ONLY the JSON array with exactly {count} items."""

        print(f"[PLANNER] {count} adet konu üretiliyor ({lang_name}, {category})...")

        try:
            if self.provider == "claude":
                raw = _retry(lambda: self._writer.client.messages.create(
                    model=self._writer.model,
                    max_tokens=4096,
                    system=PLAN_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                ).content[0].text)
            elif self.provider == "gemini":
                topic_schema = self._writer._gtypes.Schema(
                    type=self._writer._gtypes.Type.OBJECT,
                    properties={
                        "konu": self._writer._gtypes.Schema(type=self._writer._gtypes.Type.STRING),
                        "baslik": self._writer._gtypes.Schema(type=self._writer._gtypes.Type.STRING),
                        "anahtar_kelimeler": self._writer._gtypes.Schema(
                            type=self._writer._gtypes.Type.ARRAY,
                            items=self._writer._gtypes.Schema(type=self._writer._gtypes.Type.STRING)
                        )
                    },
                    required=["konu", "baslik", "anahtar_kelimeler"]
                )
                response_schema = self._writer._gtypes.Schema(
                    type=self._writer._gtypes.Type.ARRAY,
                    items=topic_schema
                )
                response = _retry(lambda: self._writer.client.models.generate_content(
                    model=self._writer.model,
                    contents=prompt,
                    config=self._writer._gtypes.GenerateContentConfig(
                        system_instruction=PLAN_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=0.8,
                    )
                ))
                raw = response.text
            elif self.provider == "ollama":
                import requests as req
                payload = {
                    "model": self._writer.model,
                    "prompt": f"{PLAN_SYSTEM_PROMPT}\n\n{prompt}",
                    "stream": False,
                    "options": {"temperature": 0.8}
                }
                resp = _retry(lambda: req.post(f"{self._writer.base_url}/api/generate", json=payload, timeout=120))
                raw = resp.json().get("response", "")
            elif self.provider == "lmstudio":
                raw = _retry(lambda: self._writer.client.chat.completions.create(
                    model=self._writer._get_model(),
                    messages=[
                        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=4096,
                    temperature=0.8,
                ).choices[0].message.content)
            else:
                raise ValueError(f"Desteklenmeyen provider: {self.provider}")

            topics = _parse_json(raw)
            if isinstance(topics, list):
                print(f"[PLANNER] {len(topics)} konu üretildi.")
                return topics
            elif isinstance(topics, dict) and "topics" in topics:
                return topics["topics"]
            else:
                raise ValueError(f"Beklenmeyen format: {type(topics)}")

        except Exception as e:
            print(f"[PLANNER] Konu üretme hatası: {e}")
            raise
