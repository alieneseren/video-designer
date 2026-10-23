import json
from pathlib import Path
from typing import Optional, Dict, List, Any

MIND_MAP_FILENAME = "zihin_haritasi.json"

# ═══════════════════════════════════════════════════════════════
# KATEGORİYE ÖZEL ZİHİN HARİTASI PROMPTLARI
# ═══════════════════════════════════════════════════════════════

WHATSAPP_MIND_MAP_SYSTEM_PROMPT = """You are a senior YouTube content growth strategist specializing in viral simulated WhatsApp conversation Shorts (such as family banter, roommate chaos, landlord disputes, sports squad pranks).
Your task is to organize WhatsApp dialogue video titles into a structured hierarchical mind map with 4 to 6 compelling comedy themes/pillars.

STRICT ISLAMIC & HALAL COMPLIANCE MANDATE:
- All themes and topics MUST strictly comply with Islamic and halal principles: absolutely NO dating, boyfriends/girlfriends, romance, flirting, cheating, alcohol, gambling, or vulgarity.
- Humor, absurdity, and witty banter are strongly encouraged under ethical family, friend, and community pillars.

Recommended Themes (in Turkish or the channel's target language):
- "Komşuluk & Apartman Dinamikleri" — apartman yöneticisi aidat atışmaları, robot süpürge kaçışları, otopark yeri krizleri, komşuluk dayanışması
- "Troll & Kanka Muhabbetleri" — sahte düğün davetiyeleri, halısaha yalanları, grup sohbeti trolleri, oyun itirafları
- "Aile & Akraba Diyalogları" — borç isteyen akrabalar, anne terliği & kütüphane yalanları, baba korkusu, miras telaşı
- "Açgözlü Ev Sahibi & Günlük Absürtlükler" — açgözlü ev sahibi & kira artışı, ikinci el absürt pazarlıklar, diyetisyen kaçamakları
- "Esnaf, Çırak & İş Hayatı" — sanayide usta-çırak diyalogları, abartılan CV & mülakat komedisi, sınav sabahı yalanları

Provide the output as a valid JSON object:
{
  "themes": {
    "Komşuluk & Apartman Dinamikleri": ["Title 1", "Title 2"],
    "Troll & Kanka Muhabbetleri": ["Title 3"],
    "Aile & Akraba Diyalogları": ["Title 4"],
    "Açgözlü Ev Sahibi & Günlük Absürtlükler": ["Title 5"],
    "Esnaf, Çırak & İş Hayatı": ["Title 6"]
  }
}
Return ONLY a valid JSON object. No other text."""

WHATSAPP_MIND_MAP_UPDATE_SYSTEM_PROMPT = """You are an expert content strategist for a viral WhatsApp comedy Shorts YouTube channel.
Your task is to update the channel's mind map with newly planned WhatsApp chat topics.
Classify each new topic into one of the existing themes (e.g., "Komşuluk & Apartman Dinamikleri", "Troll & Kanka Muhabbetleri", "Aile & Akraba Diyalogları", "Açgözlü Ev Sahibi & Günlük Absürtlükler", "Esnaf, Çırak & İş Hayatı"), or create a new fitting comedy theme if it represents a distinctly new comedic angle. All topics must be 100% halal and free of dating/romance elements.

Provide the output as a valid JSON object:
{
  "themes": {
    "Theme Name": ["existing title", "new title"],
    ...
  }
}
Return ONLY the updated JSON object. No other text."""

AVIATION_MIND_MAP_SYSTEM_PROMPT = """You are an expert content strategist for the "Black Box Audio" YouTube channel — a dramatic aviation documentary channel that analyzes real-world flight emergency incidents using ATC (Air Traffic Control) radio transcripts and black box recordings.

Your task is to organize the channel's video topics into a structured hierarchical mind map based on aviation incident categories.

Organize topics ONLY into the following aviation sub-themes (use these exact names as theme keys):
- "Engine Failures & Fires" — topics about engine malfunctions, cockpit fires, TCAS alerts, forced landings
- "Severe Weather & Go-Arounds" — topics about storms, microbursts, wind shear, fog, fuel exhaustion in bad weather
- "Near Misses & Runway Incursions" — topics about collision avoidance, GPWS alerts, airport runway incursions, approach errors
- "Medical Emergencies & Diversions" — topics about crew incapacitation, passenger health crises, emergency diversions
- "Structural Failures & Decompression" — topics about explosive decompression, fuselage damage, landing gear failures
- "Navigation & Communication Loss" — topics about lost communication, GPS failures, CFIT (Controlled Flight Into Terrain)
- "Bird Strikes & FOD" — topics about bird strikes, foreign object damage, wildlife incidents
- "Historic Disasters & Investigation" — topics about major historical aviation disasters and NTSB/ICAO investigation findings

If a topic does not fit any of the above, place it under the closest matching theme.

Provide the output as a valid JSON object:
{
  "themes": {
    "Engine Failures & Fires": ["Title 1"],
    "Severe Weather & Go-Arounds": ["Title 2"]
  }
}
Return ONLY a valid JSON object. No other text."""

AVIATION_MIND_MAP_UPDATE_SYSTEM_PROMPT = """You are an expert content strategist for the "Black Box Audio" YouTube channel — a dramatic aviation documentary channel.

Your task is to update the channel's structured aviation mind map with newly planned topics.
Classify each new topic into one of the existing aviation themes:
- "Engine Failures & Fires"
- "Severe Weather & Go-Arounds"
- "Near Misses & Runway Incursions"
- "Medical Emergencies & Diversions"
- "Structural Failures & Decompression"
- "Navigation & Communication Loss"
- "Bird Strikes & FOD"
- "Historic Disasters & Investigation"

If a topic fits an existing theme, add it there. If it's a genuinely different type of incident, create a new theme.

Provide the output as a valid JSON object:
{
  "themes": {
    "Engine Failures & Fires": ["existing title", "new title"]
  }
}
Return ONLY the updated JSON object. No other text."""

REDDIT_STORIES_MIND_MAP_SYSTEM_PROMPT = """You are an expert content strategist for a viral "Reddit Stories" YouTube Shorts channel.
Your task is to organize the channel's viral Reddit story questions, confession prompts, mystery topics, and AITA relationship drama into a structured hierarchical mind map.

Organize topics into the following core themes (use these names or similar compelling theme names):
- "Unbelievable Secrets & Revelations" — accidentally discovered deep secrets, hidden identities, shocking truths
- "Relationship Drama & AITAH" — wedding disasters, partner betrayals, moral dilemmas, boundary crossing
- "Creepy Encounters & Glitches" — eerie unexplainable occurrences, creepy houses, matrix glitches, close calls
- "Workplace & Career Confessions" — office scandals, fake credentials, corporate revenge, crazy boss stories
- "Instant Karma & Revenge" — petty/pro revenge, narcissist downfalls, satisfying karma moments

Provide the output as a valid JSON object:
{
  "themes": {
    "Unbelievable Secrets & Revelations": ["Title 1", "Title 2"],
    "Relationship Drama & AITAH": ["Title 3"]
  }
}
Return ONLY a valid JSON object. No other text."""

REDDIT_STORIES_MIND_MAP_UPDATE_SYSTEM_PROMPT = """You are an expert content strategist for a viral "Reddit Stories" YouTube channel.
Your task is to update the channel's structured mind map with newly planned Reddit story topics and questions.
Classify each new topic into one of the existing themes, or create an appropriate new theme if needed.
Provide the output as a valid JSON object:
{
  "themes": {
    "Unbelievable Secrets & Revelations": ["existing title", "new title"]
  }
}
Return ONLY the updated JSON object. No other text."""


def get_mind_map_system_prompt(category: str, channel_config: Optional[dict] = None) -> str:
    """
    Kanal kategorisine özel dinamik zihin haritası promptu üretir.
    Gelecekte eklenecek yeni kategorileri (yemek, tarih, oyun, fitness vb.) yereldeki
    yapay zekanın (LM Studio / Ollama vb.) otonom olarak anlamasını ve yapılandırmasını sağlar.
    """
    cat = (category or "space").lower().strip()
    ch_name = (channel_config.get("name") if channel_config else "") or "YouTube Channel"
    lang = (channel_config.get("language") if channel_config else "tr") or "tr"
    lang_name = "Turkish" if lang == "tr" else "English"
    custom_topics = channel_config.get("custom_topics", []) if channel_config else []
    custom_hint = f"\nChannel Focus Keywords / Topics: {', '.join(custom_topics)}" if custom_topics else ""

    if cat in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
        return WHATSAPP_MIND_MAP_SYSTEM_PROMPT
    elif cat == "aviation":
        return AVIATION_MIND_MAP_SYSTEM_PROMPT
    elif cat in ("reddit_stories", "reddit"):
        return REDDIT_STORIES_MIND_MAP_SYSTEM_PROMPT
    elif cat == "travel":
        return f"""You are an expert YouTube content strategist for a Travel & Discovery channel named "{ch_name}".
Your task is to organize travel video titles into a structured hierarchical mind map with 4 to 6 thematic pillars in {lang_name} (e.g. "Tarihi Şehirler & Kültür", "Doğa & Macera Rotaları", "Bütçe Dostu Gezi Rehberleri", "Gizli Cennetler & Keşifler").
Provide the output as a valid JSON object:
{{
  "themes": {{
    "Theme Name 1": ["Title 1", "Title 2"],
    "Theme Name 2": ["Title 3"]
  }}
}}
Return ONLY a valid JSON object. No other text."""
    elif cat == "story":
        return f"""You are an expert YouTube content strategist for a Storytelling channel named "{ch_name}".
Your task is to organize storytelling video titles into a structured hierarchical mind map with 4 to 6 thematic pillars in {lang_name} (e.g. "Gizem & Gerilim Hikayeleri", "Mitoloji & Efsaneler", "Korku & Paranormal Olaylar", "Tarihi & Felsefi Hikayeler").
Provide the output as a valid JSON object:
{{
  "themes": {{
    "Theme Name 1": ["Title 1", "Title 2"],
    "Theme Name 2": ["Title 3"]
  }}
}}
Return ONLY a valid JSON object. No other text."""
    elif cat in ("space", "planets", "astronomy", "cosmos", "science"):
        return f"""You are an expert content strategist for a Space & Science YouTube channel named "{ch_name}".
Your task is to organize space/science video titles into a structured hierarchical mind map with 4 to 6 thematic pillars in {lang_name} (e.g. "Kara Delikler & Kozmos", "Gezegenler & Uydular", "Uzay Keşifleri & Teleskoplar", "Teorik Fizik & Evren").
Provide the output as a valid JSON object:
{{
  "themes": {{
    "Theme Name 1": ["Title 1", "Title 2"],
    "Theme Name 2": ["Title 3"]
  }}
}}
Return ONLY a valid JSON object. No other text."""
    else:
        # UNIVERSAL / DYNAMIC ENGINE FOR ANY PRESENT OR FUTURE TOPIC CATEGORY!
        return f"""You are a senior YouTube content strategist and niche growth advisor for the channel "{ch_name}".
Category / Niche: "{cat}"{custom_hint}
Target Language: {lang_name}

Your task is to analyze this channel's unique niche ("{cat}") and organize the video titles into a structured hierarchical mind map.
INSTRUCTIONS FOR THE AI:
1. Determine 4 to 6 core strategic thematic pillars that are directly tailored, authentic, and high-retention for the "{cat}" niche.
2. Group the provided video titles logically and neatly under these thematic pillars.
3. If a title doesn't fit neatly into existing pillars, either place it under the closest match or establish a relevant new pillar.
4. All theme/pillar names must be in {lang_name}, clear, engaging, and professional.

STRICT JSON OUTPUT FORMAT — respond ONLY with a valid JSON object:
{{
  "themes": {{
    "Thematic Pillar 1 in {lang_name}": ["Video Title 1", "Video Title 2"],
    "Thematic Pillar 2 in {lang_name}": ["Video Title 3"],
    ...
  }}
}}
Return ONLY a valid JSON object. No markdown, no commentary."""


def get_mind_map_update_system_prompt(category: str, channel_config: Optional[dict] = None) -> str:
    """Yeni üretilen konuları zihin haritasına eklemek için dinamik prompt."""
    cat = (category or "space").lower().strip()
    ch_name = (channel_config.get("name") if channel_config else "") or "YouTube Channel"
    lang = (channel_config.get("language") if channel_config else "tr") or "tr"
    lang_name = "Turkish" if lang == "tr" else "English"

    if cat in ("whatsapp_stories", "whatsapp_chat", "whatsapp"):
        return WHATSAPP_MIND_MAP_UPDATE_SYSTEM_PROMPT
    elif cat == "aviation":
        return AVIATION_MIND_MAP_UPDATE_SYSTEM_PROMPT
    elif cat in ("reddit_stories", "reddit"):
        return REDDIT_STORIES_MIND_MAP_UPDATE_SYSTEM_PROMPT
    else:
        return f"""You are an expert content strategist for the YouTube channel "{ch_name}" in the "{cat}" niche.
Target Language: {lang_name}

Your task is to update the channel's hierarchical mind map with newly planned video topics.
Classify each new topic into the most suitable existing thematic pillar, or introduce a new pillar in {lang_name} if a topic covers a distinctly new angle of "{cat}".

Provide the output as a valid JSON object:
{{
  "themes": {{
    "Theme Name 1": ["existing title", "new title"],
    ...
  }}
}}
Return ONLY the updated JSON object. No other text."""


# ═══════════════════════════════════════════════════════════════
# KANITLANMIŞ VARSAYILAN TEMALAR (Çevrimdışı / Başlangıç Havuzu)
# ═══════════════════════════════════════════════════════════════

DEFAULT_THEMES = {
    "whatsapp_stories": {
        "Komşuluk & Apartman Dinamikleri": [
            "Apartman yöneticisi ile robot süpürgeyi balkondan kaçıran komşunun kavgası",
            "Açgözlü ev sahibinin 'oksijen vergisi' adı altında kira artışı bahanesi",
            "Apartman grubunda 'gece 3te kim matkap çalıştırıyor' krizinin robot süpürge çıkması",
            "Otopark yerine saksı koyan yöneticiye karşı komşuların birlik olması"
        ],
        "Troll & Kanka Muhabbetleri": [
            "Troll kankanın sahte düğün davetiyesi ve çeyrek altın şakası",
            "Halısaha maçına gelmeyen kalecinin 'kayınvalidem mantı açtı' yalanı",
            "Troll arkadaşın halı saha grubunu birbirine düşüren ses kaydı",
            "Kankasına yanlışlıkla patronun taklidini ses kaydı atan genç"
        ],
        "Aile & Akraba Diyalogları": [
            "Dedemin akıllı televizyon kumandasıyla yarım saat çay karıştırma paniği",
            "Annesine 'kütüphanedeyim' deyip arkadaki langırt seslerine yakalanan genç",
            "Babasına arabanın tamponunu sürttüğünü itiraf eden gencin korkusu",
            "Akraba WhatsApp grubuna yanlışlıkla komik video atan gencin vedası"
        ],
        "Açgözlü Ev Sahibi & Günlük Absürtlükler": [
            "Açgözlü ev sahibinin akılalmaz kira artışı bahanesi",
            "İkinci el uygulamasında 'ürüne karşılık 4 kasa elma takası' teklif eden dayı",
            "Diyetisyene gizlice çiğ köfte dürüm yerken yakalanan gencin savunması",
            "Spor salonu üyeliğini iptal ettirmeye çalışan gencin psikolojik savaşı"
        ],
        "Esnaf, Çırak & İş Hayatı": [
            "Oto sanayide çırağın 'motora antifriz yerine ev yapımı sirke koydum' itirafı",
            "Sınav sabahı 'hiç çalışmadım kanka' deyip 100 alan arkadaşın itirafı",
            "İş görüşmesinde abartılan İngilizce seviyesinin canlı yayında açığa çıkması",
            "Patrona yanlışlıkla arkadaş grubuna atılacak komik caps'i atan çalışan"
        ]
    },
    "whatsapp": {
        "Komşuluk & Apartman Dinamikleri": [
            "Apartman yöneticisi ile robot süpürgeyi balkondan kaçıran komşunun kavgası",
            "Açgözlü ev sahibinin 'oksijen vergisi' adı altında kira artışı bahanesi"
        ],
        "Troll & Kanka Muhabbetleri": [
            "Troll kankanın sahte düğün davetiyesi ve çeyrek altın şakası",
            "Halısaha maçına gelmeyen kalecinin ürettiği devasa yalanlar"
        ],
        "Aile & Akraba Diyalogları": [
            "Dedemin akıllı televizyon kumandasıyla çay karıştırma paniği"
        ],
        "Açgözlü Ev Sahibi & Günlük Absürtlükler": [
            "Açgözlü ev sahibinin akılalmaz kira artışı bahanesi"
        ],
        "Esnaf, Çırak & İş Hayatı": [
            "Sınav sabahı 'hiç çalışmadım kanka' deyip 100 alan arkadaş"
        ]
    },
    "whatsapp_chat": {
        "Komşuluk & Apartman Dinamikleri": [
            "Apartman yöneticisi ile robot süpürgeyi balkondan kaçıran komşunun kavgası",
            "Açgözlü ev sahibinin akılalmaz kira artışı bahanesi"
        ],
        "Troll & Kanka Muhabbetleri": [
            "Troll kankanın sahte düğün davetiyesi ve çeyrek altın şakası"
        ],
        "Aile & Akraba Diyalogları": [
            "Dedemin akıllı televizyon kumandasıyla çay karıştırma paniği"
        ],
        "Açgözlü Ev Sahibi & Günlük Absürtlükler": [
            "Açgözlü ev sahibinin akılalmaz kira artışı bahanesi"
        ],
        "Esnaf, Çırak & İş Hayatı": [
            "Sınav sabahı 'hiç çalışmadım kanka' deyip 100 alan arkadaş"
        ]
    },
    "reddit_stories": {
        "Unbelievable Secrets & Revelations": [
            "Hayatınızda tamamen tesadüfen öğrendiğiniz en tuhaf ve gizli gerçek neydi?",
            "Birisiyle konuşurken 'Bu kişinin kesinlikle gizli bir hayatı var' dediğiniz an neydi?",
            "İş yerinizde herkesin bildiği ama kimsenin açıkça konuşamadığı en büyük sır neydi?"
        ],
        "Confessions & Family Secrets": [
            "Ailenizin yıllarca sizden sakladığı ve tesadüfen ortaya çıkan en büyük sır?",
            "Bir komşunuz hakkında sonradan öğrendiğiniz ve sizi şoke eden en ürkütücü gerçek?"
        ],
        "Relationship Drama & AITAH": [
            "Düğünden hemen önce iptal edilmesine sebep olan en saçma veya şok edici olay?",
            "En yakın arkadaşınızın gerçek yüzünü gösterdiği o kırılma anı neydi?"
        ],
        "Creepy Encounters & Glitches": [
            "Girdiğiniz bir evde gördüğünüz ve anında oradan kaçmak istemenize sebep olan şey neydi?",
            "Açıklayamadığınız ve mantığınızın almadığı en tuhaf déjà vu veya paralel evren anı?"
        ],
        "Instant Karma & Revenge": [
            "Gördüğünüz en tatmin edici ve anlık karma veya intikam olayı neydi?"
        ]
    },
    "reddit": {
        "Unbelievable Secrets & Revelations": [
            "Hayatınızda tamamen tesadüfen öğrendiğiniz en tuhaf ve gizli gerçek neydi?",
            "Birisiyle konuşurken 'Bu kişinin kesinlikle gizli bir hayatı var' dediğiniz an neydi?"
        ],
        "Confessions & Family Secrets": [
            "Ailenizin yıllarca sizden sakladığı ve tesadüfen ortaya çıkan en büyük sır?"
        ],
        "Relationship Drama & AITAH": [
            "Düğünden hemen önce iptal edilmesine sebep olan en saçma veya şok edici olay?"
        ],
        "Creepy Encounters & Glitches": [
            "Girdiğiniz bir evde gördüğünüz ve anında oradan kaçmak istemenize sebep olan şey neydi?"
        ],
        "Instant Karma & Revenge": [
            "Gördüğünüz en tatmin edici ve anlık karma veya intikam olayı neydi?"
        ]
    },
    "aviation": {
        "Engine Failures & Fires": [
            "US Airways Flight 1549 — Miracle on the Hudson",
            "Qantas Flight 32 — Airbus A380 Engine Explosion",
            "British Airways Flight 9 — Volcanic Ash Engine Flameout"
        ],
        "Severe Weather & Go-Arounds": [
            "Delta Air Lines Flight 191 — Microburst Crash",
            "Avianca Flight 52 — Fuel Exhaustion in Storm",
            "Air France Flight 358 — Runway Excursion in Storm"
        ],
        "Near Misses & Runway Incursions": [
            "Tenerife Airport Disaster — ATC Analysis",
            "JFK Runway Incursion — Delta 1943 and American 106",
            "San Francisco Near Miss — Air Canada 759"
        ],
        "Medical Emergencies & Diversions": [
            "British Airways Flight 5390 — Pilot Sucked Out Emergency",
            "Aloha Airlines Flight 243 — Explosive Decompression"
        ],
        "Structural Failures & Decompression": [
            "United Airlines Flight 232 — Engine Failure & Hydraulic Loss",
            "Air Canada Flight 797 — Cockpit and Cabin Fire"
        ],
        "Navigation & Communication Loss": [
            "Gimli Glider — Boeing 767 Fuel Exhaustion Emergency"
        ],
        "Bird Strikes & FOD": [
            "Ethiopian Airlines Flight 961 — Emergency Ditching"
        ],
        "Historic Disasters & Investigation": [
            "FedEx Flight 705 — Hijack Emergency Landing",
            "KAL Flight 007 — Soviet Interception Tragedy"
        ]
    },
    "space": {
        "Kara Delikler & Kozmik Uçlar": [
            "Süper kütleli kara deliklerin gizemi",
            "Olay ufkunun ötesinde ne var?"
        ],
        "Gezegenler & Uydular": [
            "Mars'ta su ve yaşam izleri",
            "Jüpiter'in gizemli uydusu Europa"
        ],
        "Uzay Keşifleri & Teleskoplar": [
            "James Webb Teleskobunun en büyük keşifleri",
            "Voyager sondalarının sonsuz yolculuğu"
        ],
        "Teorik Fizik & Evrenin Sonu": [
            "Büyük Patlama öncesinde ne vardı?",
            "Paralel evrenler teorisi gerçek olabilir mi?"
        ]
    },
    "planets": {
        "Güneş Sistemi": ["Venüs'ün cehennemi andıran yüzeyi", "Merkür'ün ekstrem sıcaklıkları"],
        "Ötegezegenler": ["Yaşama elverişli Goldilocks gezegenleri"],
        "Kolonileşme": ["Mars ve Ay üsleri projeleri"]
    },
    "astronomy": {
        "Nebulalar ve Yıldızlar": ["Süpernova patlamaları ve nötron yıldızları"],
        "Galaksiler": ["Samanyolu ve Andromeda çarpışması"],
        "Kozmik Fenomenler": ["Gama ışını patlamaları ve kuasarlar"]
    },
    "story": {
        "Gizem & Gerilim": ["Kayıp deniz fenerinin gizemi", "Zamanın durduğu kasaba"],
        "Mitoloji & Efsaneler": ["Atlantis'in kayıp krallığı"],
        "Masallar & Fabllar": ["Ateşini kaybeden ejderha"]
    },
    "travel": {
        "Tarihi Şehirler & Kültür": ["Roma'nın gizli sokakları ve antik kalıntılar", "Kyoto tapınakları"],
        "Doğa & Macera Rotaları": ["İzlanda kuzey ışıkları ve şelaleleri"],
        "Bütçe Dostu Geziler": ["Avrupa'yı trenle gezme rehberi"],
        "Lüks & Egzotik Tatiller": ["Maldivler su üstü villaları"]
    }
}


def _fallback_cluster_titles(titles: list[str], category: str) -> dict:
    """Yapay zeka erişilemez olduğunda başlıkları anahtar kelimelere göre akıllıca kümele."""
    cat = (category or "").lower().strip()
    if cat in ("whatsapp_stories", "whatsapp", "whatsapp_chat"):
        clusters = {
            "Komşuluk & Apartman Dinamikleri": [],
            "Troll & Kanka Muhabbetleri": [],
            "Aile & Akraba Diyalogları": [],
            "Açgözlü Ev Sahibi & Günlük Absürtlükler": [],
            "Esnaf, Çırak & İş Hayatı": []
        }
        for t in titles:
            tl = t.lower()
            if any(w in tl for w in ["apartman", "robot süpürge", "yönetici", "komşu", "otopark", "aidat", "bina"]):
                clusters["Komşuluk & Apartman Dinamikleri"].append(t)
            elif any(w in tl for w in ["kanka", "troll", "halısaha", "şaka", "davetiye", "oyun"]):
                clusters["Troll & Kanka Muhabbetleri"].append(t)
            elif any(w in tl for w in ["anne", "baba", "akraba", "borç", "kuzen", "miras", "kütüphane", "kumanda"]):
                clusters["Aile & Akraba Diyalogları"].append(t)
            elif any(w in tl for w in ["ev sahibi", "kira", "pazarlık", "ikinci el", "diyetisyen", "dürüm", "kargo"]):
                clusters["Açgözlü Ev Sahibi & Günlük Absürtlükler"].append(t)
            elif any(w in tl for w in ["sınav", "mülakat", "iş", "cv", "patron", "çalışan", "stajyer", "ofis", "usta", "çırak", "sanayi"]):
                clusters["Esnaf, Çırak & İş Hayatı"].append(t)
            else:
                clusters["Troll & Kanka Muhabbetleri"].append(t)
        return {k: v for k, v in clusters.items() if v} or {"Genel Diyaloglar": titles}

    if len(titles) <= 3:
        return {f"{cat.replace('_', ' ').title()} - Temel Konular": titles}

    chunk_size = max(2, len(titles) // 3)
    return {
        f"{cat.replace('_', ' ').title()} - Bölüm 1": titles[:chunk_size],
        f"{cat.replace('_', ' ').title()} - Bölüm 2": titles[chunk_size:chunk_size*2],
        f"{cat.replace('_', ' ').title()} - Bölüm 3": titles[chunk_size*2:]
    }


# ═══════════════════════════════════════════════════════════════
# MIND MAP MANAGER
# ═══════════════════════════════════════════════════════════════

class MindMapManager:
    def __init__(self, channel_dir: Path):
        self.channel_dir = Path(channel_dir)
        self.path = self.channel_dir / MIND_MAP_FILENAME

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> dict:
        if not self.exists():
            return {"themes": {}}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"themes": {}}
                if "themes" not in data:
                    data["themes"] = {}
                return data
        except Exception as e:
            print(f"[MIND MAP] Yükleme hatası: {e}")
            return {"themes": {}}

    def save(self, data: dict):
        self.channel_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[MIND MAP] Zihin haritası kaydedildi: {self.path}")
        except Exception as e:
            print(f"[MIND MAP] Kaydetme hatası: {e}")

    def bootstrap_or_load(self, writer=None, channel_config: Optional[dict] = None) -> dict:
        """
        Kanalın zihin haritası yoksa, kategorisine özel hazır temalardan veya yerel/aktif AI ile
        otonom olarak 4-6 temalık başlangıç zihin haritası üretir ve kaydeder.
        Böylece ileride eklenebilecek her yeni kategori (tarih, yemek, oyun, kripto vb.) yerel yapay zeka
        tarafından dinamik olarak yapılandırılabilir.
        """
        ch = channel_config or {}
        cat = (ch.get("topic_category") or "space").lower().strip()
        is_space_cat = cat in ("space", "astronomy", "planets", "bilim")

        if self.exists():
            data = self.load()
            themes = data.get("themes", {})
            has_space_pollution = any(k in ("Black Holes & Cosmos", "Planets & Moons", "Space Exploration", "Theoretical Physics") for k in themes.keys())
            if themes and len(themes) > 0 and not (has_space_pollution and not is_space_cat):
                return data
        ch_name = ch.get("name") or "YouTube Kanalı"
        lang = ch.get("language") or "tr"
        lang_name = "Turkish" if lang == "tr" else "English"
        custom_topics = ch.get("custom_topics", [])
        custom_hint = f"\nFocus Topics/Keywords: {', '.join(custom_topics)}" if custom_topics else ""

        # 1. Bilinen kategoriler için DEFAULT_THEMES kontrolü
        if cat in DEFAULT_THEMES:
            themes = DEFAULT_THEMES[cat]
            data = {"themes": themes}
            self.save(data)
            return data

        # 2. Özel veya gelecekte eklenecek yeni kategori: Yereldeki/Aktif Yapay Zeka ile otonom üret
        if writer:
            print(f"[MIND MAP] Yeni kategori ('{cat}') için Yapay Zeka ile otonom zihin haritası yapılandırılıyor...")
            sys_prompt = f"""You are a senior YouTube content strategist and channel growth architect.
Channel Name: "{ch_name}"
Category / Niche: "{cat}"{custom_hint}
Target Language: {lang_name}

Your task is to bootstrap an initial, highly professional, viral content mind map for this YouTube channel.
INSTRUCTIONS:
1. Create 4 to 6 core strategic thematic pillars specific and authentic to the "{cat}" niche.
2. Under each thematic pillar, suggest 2 to 3 viral, engaging video topic titles.
3. All theme names and video titles must be written in {lang_name}.

STRICT JSON OUTPUT FORMAT — respond ONLY with a valid JSON object:
{{
  "themes": {{
    "Thematic Pillar 1 in {lang_name}": ["Title 1", "Title 2", "Title 3"],
    "Thematic Pillar 2 in {lang_name}": ["Title 4", "Title 5"],
    ...
  }}
}}
Return ONLY valid JSON. No markdown commentary."""

            user_prompt = f"Please generate a complete 4-6 pillar content mind map for the channel '{ch_name}' in category '{cat}' with 2-3 viral starter titles per theme in {lang_name}."
            try:
                raw_json = writer.run_prompt(sys_prompt, user_prompt)
                try:
                    from script_writer import _parse_json
                except ImportError:
                    from src.script_writer import _parse_json
                ai_data = _parse_json(raw_json)
                if isinstance(ai_data, dict) and "themes" in ai_data and isinstance(ai_data["themes"], dict) and len(ai_data["themes"]) >= 2:
                    self.save(ai_data)
                    return ai_data
            except Exception as e:
                print(f"[MIND MAP] Otonom AI zihin haritası üretimi uyarısı: {e}")

        # 3. Fallback: Genel temalar
        cat_title = cat.replace("_", " ").title()
        fallback_themes = {
            f"{cat_title} - Temel Konular": [f"{cat_title} Nedir ve Nasıl Başlanır?"],
            f"{cat_title} - Trendler & İpuçları": [f"{cat_title} Alanında En Çok Yapılan Hatalar"],
            f"{cat_title} - Derinlemesine İnceleme": [f"{cat_title} Detaylı Rehberi ve Püf Noktaları"],
            f"{cat_title} - Soru & Cevap & Vaka": [f"{cat_title} Hakkında Bilinmeyen Şaşırtıcı Gerçekler"]
        }
        fallback_data = {"themes": fallback_themes}
        self.save(fallback_data)
        return fallback_data

    def sync_from_csv(
        self,
        writer,
        planner,
        category: str = "space",
        channel_config: Optional[dict] = None
    ) -> dict:
        """
        CSV içerik planındaki tüm başlıkları okur ve zihin haritasını yapay zeka ile sıfırdan derler.
        Eğer plan henüz boşsa, bootstrap_or_load çağrılarak kategorinin başlangıç haritası oluşturulur.
        """
        plan = planner.get_plan() if planner and hasattr(planner, "get_plan") else []
        titles = [row.get("baslik") or row.get("konu") for row in plan if row.get("baslik") or row.get("konu")]

        ch = channel_config or {}
        cat = (category or ch.get("topic_category") or "space").lower().strip()
        ch_name = ch.get("name") or "YouTube Kanalı"
        lang = ch.get("language") or "tr"
        lang_name = "Turkish" if lang == "tr" else "English"

        if not titles:
            return self.bootstrap_or_load(
                writer=writer,
                channel_config=channel_config or {"topic_category": cat, "name": ch_name, "language": lang}
            )

        titles_str = "\n".join(f"- {t}" for t in titles)
        user_prompt = (
            f"Channel: {ch_name}\n"
            f"Category: {cat}\n"
            f"Target Language: {lang_name}\n\n"
            f"Please organize the following {len(titles)} video titles into logical thematic pillars in {lang_name}:\n{titles_str}"
        )

        sys_prompt = get_mind_map_system_prompt(cat, channel_config)

        provider_name = getattr(writer, "provider", "AI")
        print(f"[MIND MAP] {len(titles)} adet başlık ile zihin haritası senkronize ediliyor (kategori: {cat}, sağlayıcı: {provider_name})...")
        try:
            raw_json = writer.run_prompt(sys_prompt, user_prompt)
            try:
                from script_writer import _parse_json
            except ImportError:
                from src.script_writer import _parse_json
            data = _parse_json(raw_json)
            if isinstance(data, dict) and "themes" in data and isinstance(data["themes"], dict) and len(data["themes"]) > 0:
                self.save(data)
                return data
            else:
                print(f"[MIND MAP] Yapay zeka çıktısında 'themes' bulunamadı, fallback kümeleme uygulanıyor.")
        except Exception as e:
            print(f"[MIND MAP] Senkronizasyon hatası: {e}. Fallback kümeleme uygulanıyor.")

        fallback_themes = _fallback_cluster_titles(titles, cat)
        fallback_data = {"themes": fallback_themes}
        self.save(fallback_data)
        return fallback_data

    def update_with_new_topics(
        self,
        writer,
        new_topics: list[dict],
        category: str = "space",
        channel_config: Optional[dict] = None
    ) -> dict:
        """Yeni üretilen konuları zihin haritasına ekler."""
        current = self.load()
        new_titles = [t.get("baslik") or t.get("konu") for t in new_topics if t.get("baslik") or t.get("konu")]
        if not new_titles:
            return current

        ch = channel_config or {}
        cat = (category or ch.get("topic_category") or "space").lower().strip()
        ch_name = ch.get("name") or "YouTube Kanalı"
        lang = ch.get("language") or "tr"
        lang_name = "Turkish" if lang == "tr" else "English"

        user_prompt = (
            f"Channel: {ch_name} (Category: {cat}, Language: {lang_name})\n"
            f"Current Mind Map Themes:\n{json.dumps(current.get('themes', {}), ensure_ascii=False, indent=2)}\n\n"
            f"New video titles to classify and integrate:\n" + "\n".join(f"- {t}" for t in new_titles)
        )

        sys_prompt = get_mind_map_update_system_prompt(cat, channel_config)

        print(f"[MIND MAP] {len(new_titles)} yeni başlık zihin haritasına ekleniyor (kategori: {cat})...")
        try:
            raw_json = writer.run_prompt(sys_prompt, user_prompt)
            try:
                from script_writer import _parse_json
            except ImportError:
                from src.script_writer import _parse_json
            updated_data = _parse_json(raw_json)
            if isinstance(updated_data, dict) and "themes" in updated_data and isinstance(updated_data["themes"], dict) and len(updated_data["themes"]) > 0:
                self.save(updated_data)
                return updated_data
        except Exception as e:
            print(f"[MIND MAP] Güncelleme hatası: {e}")

        # Akıllı yerel yedekleme
        if "themes" not in current or not isinstance(current["themes"], dict) or not current["themes"]:
            current["themes"] = _fallback_cluster_titles(new_titles, cat)
        else:
            clustered = _fallback_cluster_titles(new_titles, cat)
            for cluster_theme, cl_titles in clustered.items():
                matched_theme = None
                for ex_th in current["themes"].keys():
                    if ex_th.lower() in cluster_theme.lower() or cluster_theme.lower() in ex_th.lower():
                        matched_theme = ex_th
                        break
                target_key = matched_theme or next(iter(current["themes"].keys()))
                if not isinstance(current["themes"][target_key], list):
                    current["themes"][target_key] = []
                current["themes"][target_key].extend(cl_titles)

        self.save(current)
        return current

    def remove_titles(self, titles_to_remove: list[str]) -> dict:
        """
        Zihin haritasındaki temalardan belirtilen başlıkları yerel olarak kaldırır.
        Yapay zekaya gitmeden hızlıca ve kaynak tüketmeden temizleme yapar.
        """
        current = self.load()
        themes = current.get("themes", {})

        clean_remove = [t.strip().lower() for t in titles_to_remove if t]

        updated_themes = {}
        for theme_name, topic_list in themes.items():
            if not isinstance(topic_list, list):
                updated_themes[theme_name] = topic_list
                continue

            new_list = []
            for t in topic_list:
                if t and t.strip().lower() not in clean_remove:
                    new_list.append(t)
            updated_themes[theme_name] = new_list

        current["themes"] = updated_themes
        self.save(current)
        return current
