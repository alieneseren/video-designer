"""
channel_manager.py
Birden fazla kanalın yapılandırmasını yönetir.
channels.json dosyasını okur/yazar.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime


DEFAULT_CHANNELS_FILE = "config/channels.json"


# Kanal başına ayarlanabilen edit alanları ve varsayılanları
DEFAULT_EDIT_OPTIONS = {
    "subtitle_preset": None,        # None → global settings'ten al
    "subtitle_animation": None,
    "bgm_path": None,
    "bgm_volume": None,
    "watermark_path": None,
    "watermark_text": None,
    "watermark_position": None,
    "intro_clip_path": None,
    "outro_clip_path": None,
    "kenburns_intensity": None,
    "transition_dur": None,
    "video_duration": None,
    "censor_faces": None,
    "auto_editor": None,
    "censor_logo_path": None,
    "reddit_avatar_path": None,
    "reddit_username": None,
    "enable_i2v": False,
    "i2v_model_quality": "distilled_q4",
    "i2v_fps_multiplier": 4,
    "music_genre": "emotional",
    "music_theme": "cosmic",
    "music_duration": 180,
    "enable_hyperframes_hook": False,
    "hyperframes_hook_badge": "YENİ VİDEO",
    "auto_ai_qa_enabled": False,
    "voice_clone_id": None,          # None → global aktif ses klonu kullanılır
}

# ── Konu Kategorilerine Göre İdeal Kanal & Video Ayar Profilleri ──
CATEGORY_PRESETS: dict[str, dict] = {
    "whatsapp_stories": {
        "shorts_mode": True,
        "schedule_hour": 19,
        "transition": "fade",
        "edit_options": {
            "video_duration": "40",
            "hook_intro_effect": True,
            "normalize_audio_loudness": True,
            "enable_hyperframes_hook": True,
            "hyperframes_hook_badge": "WHATSAPP SHORTS",
            "youtube_category": "comedy",
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "reddit_stories": {
        "shorts_mode": True,
        "schedule_hour": 19,
        "transition": "fade",
        "edit_options": {
            "video_duration": "48",
            "hook_intro_effect": True,
            "normalize_audio_loudness": True,
            "enable_hyperframes_hook": False,
            "youtube_category": "entertainment",
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "aviation": {
        "shorts_mode": False,
        "schedule_hour": 19,
        "transition": "parallax",
        "edit_options": {
            "video_duration": "600",
            "kenburns_intensity": "0.04",
            "hook_intro_effect": True,
            "normalize_audio_loudness": True,
            "youtube_category": "entertainment",
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "music": {
        "shorts_mode": False,
        "schedule_hour": 19,
        "transition": "parallax",
        "edit_options": {
            "video_duration": "180",
            "music_duration": 180,
            "music_genre": "emotional",
            "music_theme": "cosmic",
            "normalize_audio_loudness": True,
            "youtube_category": "music",
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "space": {
        "shorts_mode": True,
        "schedule_hour": 19,
        "transition": "kenburns",
        "edit_options": {
            "video_duration": "50",
            "kenburns_intensity": "0.05",
            "hook_intro_effect": True,
            "normalize_audio_loudness": True,
            "youtube_category": "science",
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "story": {
        "shorts_mode": True,
        "schedule_hour": 19,
        "transition": "fade",
        "edit_options": {
            "video_duration": "50",
            "hook_intro_effect": True,
            "normalize_audio_loudness": True,
            "youtube_category": "entertainment",
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "travel": {
        "shorts_mode": True,
        "schedule_hour": 19,
        "transition": "fade",
        "edit_options": {
            "video_duration": "42",
            "subtitle_preset": "tiktok_bold_yellow",
            "subtitle_animation": "pop",
            "kenburns_intensity": "0.08",
            "transition_dur": "0.4",
            "hook_intro_effect": True,
            "enable_hyperframes_hook": True,
            "hyperframes_hook_badge": "🌍 MUST VISIT",
            "normalize_audio_loudness": True,
            "youtube_category": "travel",
            "music_genre": "travel_acoustic",
            "music_theme": "inspiring",
            "music_duration": 45,
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "crayon_combat": {
        "shorts_mode": False,
        "schedule_hour": 19,
        "transition": "parallax",
        "edit_options": {
            "video_duration": "390",
            "kenburns_intensity": "0.03",
            "hook_intro_effect": True,
            "normalize_audio_loudness": True,
            "youtube_category": "entertainment",
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "tech_finance_essay": {
        "shorts_mode": False,
        "schedule_hour": 19,
        "transition": "fade",
        "edit_options": {
            "video_duration": "420",
            "kenburns_intensity": "0.02",
            "hook_intro_effect": True,
            "normalize_audio_loudness": True,
            "youtube_category": "education",
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "absurd_science": {
        "shorts_mode": False,
        "schedule_hour": 18,
        "transition": "parallax",
        "edit_options": {
            "video_duration": "600",
            "kenburns_intensity": "0.02",
            "hook_intro_effect": True,
            "normalize_audio_loudness": True,
            "youtube_category": "education",
            "intro_clip_path": None,
            "outro_clip_path": None,
        }
    },
    "basketball_analysis": {
        "shorts_mode": True,
        "schedule_hour": 19,
        "transition": "fade",
        "edit_options": {
            "video_duration": "42",
            "hook_intro_effect": True,
            "normalize_audio_loudness": True,
            "enable_hyperframes_hook": True,
            "hyperframes_hook_badge": "🏀 MUST WATCH",
            "youtube_category": "sports",
            "intro_clip_path": None,
            "outro_clip_path": None,
            "kenburns_intensity": "0.08",
            "bgm_volume": "0.18",
            "music_genre": "hiphop_sports",
            "music_theme": "energetic",
            "music_duration": 45,
            "auto_ai_qa_enabled": True,
        }
    }
}


def normalize_category_name(category: str) -> str:
    """Kategori eş anlamlılarını ve varyasyonlarını standart formata çevirir."""
    c = (category or "").lower().strip()
    if c in ("basketball", "basketball_analysis", "nba", "sports", "basketbol", "thebasketballshows"):
        return "basketball_analysis"
    if c in ("whatsapp", "whatsapp_chat", "whatsapp_stories"):
        return "whatsapp_stories"
    if c in ("reddit", "reddit_stories"):
        return "reddit_stories"
    if c in ("aviation", "blackbox", "havacilik", "flight", "flight_disaster", "air_crash", "kara_kutu", "cvr", "atc"):
        return "aviation"
    if c in ("crayon_combat", "military", "military_tech", "askeri", "savunma", "crayon_military", "stickman", "copadam", "cop_adam", "boskafa", "bos_kafa"):
        return "crayon_combat"
    if c in ("tech_finance_essay", "crayon_capital", "finans", "finance", "ekonomi", "tech_essay"):
        return "tech_finance_essay"
    if c in ("absurd_science", "what_if", "whatif", "eger_olsaydi", "simulasyon", "simulation", "absurd_engineering", "fizik", "bilim_deneyi"):
        return "absurd_science"
    if c in ("music", "muzik", "connectome", "sinek_beyni"):
        return "music"
    if c in ("space", "uzay", "cosmos"):
        return "space"
    if c in ("travel", "gezi", "letstravel", "letstraveii"):
        return "travel"
    if c in ("story", "hikaye"):
        return "story"
    return c or "space"


def get_category_preset(topic_category: str, language: str = "tr", channel_name: str = "") -> dict:
    """Konu kategorisine göre en ideal kanal ve video ayarlarını döner."""
    import copy
    norm_cat = normalize_category_name(topic_category)
    preset = copy.deepcopy(CATEGORY_PRESETS.get(norm_cat, CATEGORY_PRESETS["space"]))
    
    is_tr = (language or "tr").lower().startswith("tr")
    if norm_cat == "whatsapp_stories":
        preset["edit_options"]["hyperframes_hook_badge"] = "YAZANYAZANA" if is_tr else "WAIT FOR IT 💀"
    
    clean_watermark = "".join([c for c in (channel_name or "").title() if c.isalnum()])
    if clean_watermark:
        preset["edit_options"]["watermark_text"] = clean_watermark
        
    return preset




def get_localized_metadata(title: str, language: str = "tr", category: str = "reddit_stories", hook_summary: str = "") -> tuple[str, list[str]]:
    """Kanal diline ve video kategorisine göre yerelleştirilmiş YouTube açıklama ve etiketlerini üretir."""
    lang = (language or "tr").lower().strip()
    cat = (category or "reddit_stories").lower().strip()
    clean_title = (title or "Shorts").strip()
    hook_part = f"{hook_summary.strip()}...\n\n" if (hook_summary and len(hook_summary.strip()) > 20) else ""

    # 1. Reddit Hikayeleri
    if cat in ("reddit_stories", "reddit"):
        if lang == "en":
            desc = (
                f"{clean_title}\n\n"
                f"{hook_part}"
                "Unbelievable Reddit confessions, true mysteries, and compelling life stories. What would you have done in this situation? Let us know in the comments below! 👇\n\n"
                "Don't forget to like, subscribe, and hit the bell for authentic daily Reddit stories! 🔔\n\n"
                "#Reddit #RedditStories #AskReddit #Storytime #RedditConfessions #AITAH #TrueStories"
            )
            tags = [
                "Reddit", "RedditStories", "AskReddit", "RedditConfessions", "Storytime",
                "Confessions", "AITAH", "TrueStories", "LifeStories", "CrazyStories"
            ]
        elif lang == "de":
            desc = f"{clean_title}\n\n{hook_part}Unglaubliche Reddit-Geschichten, Beichten und spannende Erlebnisse direkt aus der Community! Was hättest du getan? Schreib es in die Kommentare! 👇\n\nVergiss nicht zu abonnieren für tägliche Geschichten! 🔔\n\n#Reddit #RedditGeschichten #AskRedditDeutsch #Geschichten #Beichte #Storytime"
            tags = ["Reddit", "RedditGeschichten", "AskRedditDeutsch", "Geschichten", "Beichte", "Storytime", "Erlebnisse"]
        elif lang == "es":
            desc = f"{clean_title}\n\n{hook_part}¡Historias increíbles de Reddit, confesiones y anécdotas impactantes! ¿Qué habrías hecho tú? ¡Cuéntanos en los comentarios! 👇\n\n¡No olvides suscribirte para más historias reales! 🔔\n\n#Reddit #HistoriasDeReddit #AskRedditEspanol #Historias #Confesiones #Relatos"
            tags = ["Reddit", "HistoriasDeReddit", "AskRedditEspanol", "Historias", "Confesiones", "Storytime", "Relatos"]
        elif lang == "fr":
            desc = f"{clean_title}\n\n{hook_part}Histoires incroyables de Reddit, confessions et mystères captivants! Qu'auriez-vous fait? Dites-le nous en commentaire! 👇\n\nN'oubliez pas de vous abonner pour ne rien manquer! 🔔\n\n#Reddit #HistoiresReddit #AskRedditFR #Histoires #Confessions #Mystere"
            tags = ["Reddit", "HistoiresReddit", "AskRedditFR", "Histoires", "Confessions", "Temoignage"]
        else:
            desc = (
                f"{clean_title}\n\n"
                f"{hook_part}"
                "En popüler Reddit itirafları, gizemli sırlar ve şaşırtıcı hayat hikayeleri bu anlatımda bir araya geliyor. Siz bu durumda kalsaydınız ne yapardınız? Yorumlarda buluşalım! 👇\n\n"
                "Gerçek Reddit itirafları ve sürükleyici hikayeler için abone olmayı ve bildirimleri açmayı unutmayın! 🔔\n\n"
                "#Reddit #RedditHikayeleri #AskReddit #RedditTR #İtiraf #HikayeZamanı #GerçekHikayeler"
            )
            tags = ["Reddit", "RedditHikayeleri", "AskReddit", "RedditTR", "İtiraf", "HikayeZamanı", "GerçekHikayeler", "YaşanmışOlaylar", "AileSırları"]

    # 2. WhatsApp Hikayeleri / Mesajlaşma
    elif cat in ("whatsapp_stories", "whatsapp", "whatsapp_chat"):
        if lang == "en":
            desc = f"{clean_title}\n\nHilarious text messages and funny chat stories that went completely off the rails! Send this to someone who texts like this 😂👇\n\nDon't forget to like, subscribe, and turn on notifications! 🔔\n\n#TextStory #FunnyTexts #ChatStory #Comedy #Humor #WhatsAppStories"
            tags = ["TextStory", "FunnyTexts", "ChatStory", "Comedy", "Humor", "WhatsAppStories", "FunnyMessages"]
        elif lang == "de":
            desc = f"{clean_title}\n\nLustige WhatsApp-Chats und humorvolle Momente! Teile das mit deinen Freunden 😂👇\n\nAbonniere den Kanal und aktiviere die Glocke für mehr Unterhaltung! 🔔\n\n#WhatsApp #Lustig #Humor #Komödie #ChatGeschichten"
            tags = ["WhatsApp", "Lustig", "Humor", "Komödie", "ChatGeschichten", "Nachrichten"]
        elif lang == "es":
            desc = f"{clean_title}\n\n¡Mensajes divertidos de WhatsApp y momentos cómicos! Compártelo con ese amigo que siempre responde así 😂👇\n\n¡Suscríbete para más comedia diaria! 🔔\n\n#WhatsApp #Comedia #Humor #MensajesDivertidos #ChatStories"
            tags = ["WhatsApp", "Comedia", "Humor", "MensajesDivertidos", "ChatStories"]
        elif lang == "fr":
            desc = f"{clean_title}\n\nMessages WhatsApp hilarants et conversations amusantes! Partagez avec vos amis 😂👇\n\nAbonnez-vous et activez la cloche! 🔔\n\n#WhatsApp #Drole #Humour #MessagesDrole #ChatStory"
            tags = ["WhatsApp", "Drole", "Humour", "MessagesDrole", "ChatStory"]
        else:
            desc = (
                f"{clean_title}\n\n"
                "Merhaba! Bu kanalda kendi yazmış ve seslendirmiş olduğumuz özgün ve eğlenceli mesajlaşma diyaloglarını paylaşıyoruz. "
                "Konuşmaların ve dublajların hepsi gerçek olaylardan esinlenilmiş ve tarafımıza aittir. "
                "Bu durumu yaşayan arkadaşına göndermeyi unutma! Herkese iyi seyirler! 😊👇\n\n"
                "#WhatsApp #Diyalog #Seslendirme #Dublaj #Komedi #Mizah #EğlenceliMesajlar"
            )
            tags = [
                "konuşma", "diyalog", "seslendirme", "türkçe", "türkçe dublaj",
                "whatsapp", "komik", "komedi", "mizah", "mesaj hikayeleri", "eğlenceli sohbet"
            ]

    # 3. Havacılık (Aviation)
    elif cat in ("aviation", "blackbox"):
        if lang == "en":
            desc = f"{clean_title}\n\nReal cockpit voice recorder (CVR) audio and ATC radio transcripts analyzing critical aviation incidents and flight safety investigations. Subscribe for weekly aviation breakdowns! 🔔\n\n#Aviation #ATC #AirCrash #CockpitAudio #FlightSafety #NTSB"
            tags = ["Aviation", "ATC", "Pilot", "Cockpit", "EmergencyLanding", "Boeing", "Airbus", "FlightSafety", "BlackBox"]
        else:
            desc = f"{clean_title}\n\nGerçek kokpit kayıtları ve kule telsiz görüşmeleri ile havacılık olayları ve uçuş güvenliği incelemesi. Daha fazlası için abone olun! 🔔\n\n#Havacılık #Uçak #Pilot #ATC #KaraKutu #UçuşGüvenliği"
            tags = ["Havacılık", "Uçak", "Pilot", "Kokpit", "Kule", "ATC", "KaraKutu", "UçuşGüvenliği"]

    # 4. Sinek Beyni Biyo-AI Müzik (Music / Connectome)
    elif cat in ("music", "muzik", "connectome", "sinek_beyni"):
        if lang == "en":
            desc = f"{clean_title}\n\nHarmonic neo-classical piano and orchestral music synthesized directly from biological synapse firings of 139,255 Drosophila melanogaster brain neurons. The intersection of neuroscience, bio-AI, and musical art! Don't forget to like and subscribe! 🔔\n\n#Music #BioAI #Neuroscience #Piano #AI #Connectome #FlyWire #Drosophila #Ambient #Classical"
            tags = ["Music", "Piano", "BioAI", "Neuroscience", "AI", "Connectome", "FlyWire", "Drosophila", "Ambient", "Classical"]
        elif lang == "de":
            desc = f"{clean_title}\n\nHarmonische neoklassische Klaviermusik, synthetisiert aus den biologischen Synapsenfeuerungen von 139.255 Neuronen des Drosophila-Gehirns. Bio-KI trifft Neurowissenschaften und Kunst! 🔔\n\n#Musik #BioKI #Neurowissenschaften #Klavier #KI #Connectome #FlyWire"
            tags = ["Musik", "Klavier", "BioKI", "Neurowissenschaften", "KI", "Connectome", "FlyWire"]
        elif lang == "es":
            desc = f"{clean_title}\n\nMúsica neoclásica de piano y orquesta sintetizada a partir de los disparos sinápticos biológicos de 139.255 neuronas de Drosophila. ¡Ciencia y arte unidos por bio-IA! 🔔\n\n#Música #Piano #BioIA #Neurociencia #IA #Connectome #FlyWire"
            tags = ["Música", "Piano", "BioIA", "Neurociencia", "IA", "Connectome", "FlyWire"]
        elif lang == "fr":
            desc = f"{clean_title}\n\nMusique de piano néoclassique et symphonique générée à partir des connexions synaptiques de 139 255 neurones de drosophile. La rencontre de la bio-IA et des neurosciences! 🔔\n\n#Musique #Piano #BioIA #Neurosciences #IA #Connectome #FlyWire"
            tags = ["Musique", "Piano", "BioIA", "Neurosciences", "IA", "Connectome", "FlyWire"]
        else:
            desc = f"{clean_title}\n\nDrosophila melanogaster (meyve sineği) beyninin 139.255 nöronluk konnektom haritasındaki biyolojik sinaps ateşlemelerinden üretilen armonik neo-klasik piyano ve senfoni müziği. Bilim ve sanatın buluştuğu biyo-yapay zeka deneyimi! Beğenmeyi ve abone olmayı unutmayın! 🔔\n\n#Müzik #YapayZeka #Nörobilim #Piyano #BiyoAI #Drosophila #Connectome #FlyWire"
            tags = ["Müzik", "Piyano", "YapayZeka", "Nörobilim", "BiyoAI", "Drosophila", "Connectome", "FlyWire", "Avangart", "KlasikMüzik"]

    # 5. Askeri Araçlar & Çöp Adam Hicvi (Crayon Combat)
    elif cat in ("crayon_combat", "military", "military_tech"):
        if lang == "en":
            desc = f"{clean_title}\n\nSatirical military tech breakdown and defense contractor reality check featuring tactical blueprint schematics and stickman animations. Don't forget to like, subscribe, and hit the bell for weekly military exposes! 🔔\n\n#Military #FighterJet #Defense #Aviation #TechBreakdown #Documentary #Warfare"
            tags = ["Military", "FighterJet", "DefenseTech", "Aviation", "Documentary", "CrayonCombat", "Engineering", "Stealth", "Warfare"]
        else:
            desc = f"{clean_title}\n\nSavaş uçakları, tanklar, askeri donanımlar ve savunma bütçelerinin perde arkası! Çöp adam hicvi ve taktik blueprint teknik analizleri. Abone olmayı ve bildirimleri açmayı unutmayın! 🔔\n\n#Askeri #SavaşUçağı #SavunmaSanayii #Mühendislik #Belgesel #Hiciv"
            tags = ["Askeri", "SavaşUçağı", "SavunmaSanayii", "Mühendislik", "Havacılık", "Belgesel", "Hiciv"]

    # 6. Teknoloji & Finans Belgeseli (Crayon Capital)
    elif cat in ("tech_finance_essay", "crayon_capital"):
        if lang == "en":
            desc = f"{clean_title}\n\nForensic financial breakdowns, tech bubble exposes, and corporate autopsies with data-driven charts and forensic analysis. Subscribe for weekly deep-dive business essays! 🔔\n\n#Finance #Tech #Documentary #AI #VentureCapital #Economy #VideoEssay"
            tags = ["Finance", "Tech", "Business", "Documentary", "VideoEssay", "Economy", "AI", "VentureCapital", "SiliconValley"]
        else:
            desc = f"{clean_title}\n\nTeknoloji devlerinin çöküşleri, yapay zekâ balonu ve borsa skandallarının perde arkası. Derinlemesine araştırılmış finans ve teknoloji belgeselleri için abone olun! 🔔\n\n#Finans #Teknoloji #Ekonomi #Belgesel #YapayZeka #Girişimcilik #VideoEssay"
            tags = ["Finans", "Teknoloji", "Ekonomi", "Borsa", "YapayZeka", "Belgesel", "Girişimcilik", "VideoEssay"]

    # 7. Absürt Fizik & "Eğer Gerçek Olsaydı" (Absurd Science & What If)
    elif cat in ("absurd_science", "what_if", "whatif", "absurd_engineering"):
        if lang == "en":
            desc = f"{clean_title}\n\nWhat if the universe is a simulation? What if everyone jumped at once? Mind-bending scientific thought experiments, mathematical breakdowns, and physics anomalies animated with stickman diagrams and blueprint schematics. Subscribe and hit the bell for weekly deep dives! 🔔\n\n#Physics #Science #WhatIf #Simulation #ThoughtExperiment #DeepDive #Documentary"
            tags = ["Physics", "Science", "WhatIf", "SimulationTheory", "ThoughtExperiment", "QuantumPhysics", "Engineering", "KurzgesagtStyle", "VideoEssay"]
        else:
            desc = f"{clean_title}\n\nEvren bir simülasyonsa kaç GB RAM gerekirdi? Tüm insanlık aynı anda zıplarsa ne olur? Bilimsel düşünce deneyleri, absürt fizik ve mühendislik hesaplamaları çöp adam animasyonları ve infografiklerle karşınızda! Abone olup zili açmayı unutmayın! 🔔\n\n#Bilim #Fizik #EğerOlsaydı #Simülasyon #DüşünceDeneyi #Mühendislik #Belgesel #BoşKafa"
            tags = ["Bilim", "Fizik", "EğerOlsaydı", "Simülasyon", "DüşünceDeneyi", "Kuantum", "Mühendislik", "Belgesel", "BoşKafa"]

    # 8. Basketbol & Spor Hikayeleri (Basketball Analysis)
    elif cat in ("basketball_analysis", "basketball", "sports", "nba"):
        if lang == "en":
            desc = (
                f"{clean_title}\n\n"
                f"{hook_part}"
                "Unbelievable NBA moments, tactical play breakdowns, and untold basketball stories that changed the game forever.\n\n"
                "🏀 Subscribe to The Basketball Show for daily deep-dive basketball shorts, mind-blowing records, and clutch highlights!\n\n"
                "Which player or play should we break down next? Drop your thoughts in the comments below! 👇\n\n"
                "#Basketball #NBA #TheBasketballShow #NBAShorts #BasketballAnalysis #Hoops #ClutchPlays #NBAHistory"
            )
            tags = [
                "Basketball", "NBA", "TheBasketballShow", "NBAShorts", "BasketballAnalysis",
                "NBAHighlights", "Hoops", "ClutchPlays", "NBAHistory", "BasketballStories"
            ]
        else:
            desc = (
                f"{clean_title}\n\n"
                f"{hook_part}"
                "Tarihin en akıl almaz NBA anları, taktiksel oyun kırılımları ve basketbol tarihini değiştiren gizli hikayeler!\n\n"
                "🏀 Günlük basketbol analizleri, rekorlar ve efsanevi anlar için The Basketball Show kanalına abone olmayı unutmayın! 🔔\n\n"
                "Sizce bir sonraki videoda hangi oyuncuyu veya pozisyonu inceleyelim? Yorumlarda belirtin! 👇\n\n"
                "#Basketbol #NBA #TheBasketballShow #BasketbolAnaliz #NBATürkiye #EfsaneAnlar #SporHaberleri"
            )
            tags = [
                "Basketbol", "NBA", "TheBasketballShow", "BasketbolAnaliz", "NBATürkiye",
                "EfsaneAnlar", "SporHaberleri", "BasketbolHikayeleri", "KobeBryant", "LeBronJames"
            ]

    # 9. Seyahat & Şehir Keşifleri (Travel Guide & Exploration)
    elif cat in ("travel", "gezi", "letstravel", "letstraveii"):
        if lang == "en":
            desc = (
                f"{clean_title}\n\n"
                f"{hook_part}"
                "Discover the world's most incredible travel destinations, hidden gems, and authentic street food!\n\n"
                "✈️ Subscribe to Let's Travel for weekly immersive city guides, budget travel hacks, and breathtaking cultural experiences! 🔔\n\n"
                "Which destination should we explore next? Let us know in the comments! 👇\n\n"
                "#Travel #TravelShorts #ExploreTheWorld #LetsTravel #Wanderlust #StreetFood #HiddenGems #CityGuide #TravelHacks"
            )
            tags = [
                "Travel", "TravelShorts", "ExploreTheWorld", "LetsTravel", "Wanderlust",
                "StreetFood", "HiddenGems", "CityGuide", "TravelHacks", "Vacation", "WorldTour"
            ]
        else:
            desc = (
                f"{clean_title}\n\n"
                f"{hook_part}"
                "Dünyanın en büyüleyici seyahat rotaları, gizli kalmış cennetleri ve eşsiz sokak lezzetleri!\n\n"
                "✈️ Haftalık şehir rehberleri, bütçe dostu seyahat tüyoları ve maceralar için Let's Travel kanalına abone olun! 🔔\n\n"
                "Bir sonraki rotamız neresi olsun? Yorumlarda buluşalım! 👇\n\n"
                "#Seyahat #GeziRehberi #DünyaTuru #Tatil #SokakLezzetleri #Gezgin #LetsTravel #Keşfet"
            )
            tags = [
                "Seyahat", "GeziRehberi", "DünyaTuru", "Tatil", "SokakLezzetleri",
                "Gezgin", "LetsTravel", "Keşfet", "SeyahatTüyoları", "ŞehirRehberi"
            ]

    # 10. Genel / Uzay / Diğer
    else:
        if lang == "en":
            desc = f"{clean_title}\n\nDetailed breakdown and educational insights. Don't forget to like, subscribe, and turn on notifications for more content! 🔔\n\n#Education #Documentary #DeepDive"
            tags = ["Education", "Documentary", "DeepDive", "Knowledge"]
        elif lang == "de":
            desc = f"{clean_title}\n\nAbonniere den Kanal und aktiviere die Glocke für weitere spannende Videos! 🔔\n\n#Wissen #Dokumentation #Recherche"
            tags = ["Wissen", "Dokumentation", "Recherche", "Bildung"]
        elif lang == "es":
            desc = f"{clean_title}\n\n¡Suscríbete y activa las notificaciones para más videos interesantes! 🔔\n\n#Documental #Educacion #Historia"
            tags = ["Documental", "Educacion", "Historia", "Investigacion"]
        elif lang == "fr":
            desc = f"{clean_title}\n\nAbonnez-vous et activez la cloche pour plus de vidéos passionnantes! 🔔\n\n#Documentaire #Histoire #Savoir"
            tags = ["Documentaire", "Histoire", "Savoir", "Decouverte"]
        else:
            desc = f"{clean_title}\n\nDaha fazla kaliteli ve sürükleyici içerik için abone olmayı ve bildirimleri açmayı unutmayın! 🔔\n\n#Belgesel #İnceleme #Eğitim #Bilgi"
            tags = ["Belgesel", "İnceleme", "Eğitim", "Bilgi", "DetaylıAnaliz"]

    return desc, tags


def is_bogus_fallback(desc: str, tags: list, language: str = "tr", category: str = "reddit_stories") -> bool:
    """
    Verilen açıklama veya etiketlerin kanalın diline ve kategorisine uymayan, 
    karışık veya eski hardcoded varsayılan içerip içermediğini kontrol eder.
    """
    desc_str = str(desc or "")
    tags_list = tags if isinstance(tags, list) else []
    tags_str = " ".join([str(t) for t in tags_list]).lower()
    desc_lower = desc_str.lower()
    lang = (language or "tr").lower().strip()
    cat = (category or "reddit_stories").lower().strip()

    # 1. Kategori WhatsApp değilse ama açıklamada WhatsApp geçiyorsa hatalıdır
    if cat not in ("whatsapp_stories", "whatsapp", "whatsapp_chat"):
        if "whatsapp" in desc_lower or "gülmekten kırıp geçiren" in desc_lower or "#whatsapp" in desc_lower:
            return True
        if any(str(t).lower() in ("bidublaj", "whatsapp", "diyalog") for t in tags_list):
            return True

    # 2. Dil Türkçe DEĞİLSE (örn: en, de, es, fr kanallarında):
    if lang != "tr":
        # Türkçe'ye özgü harfler (ç, ğ, ı, ş, İ, Ğ, Ş, Ç; İngilizce için ö, ü dahil)
        tr_exclusive_chars = ["ç", "ğ", "ı", "ş", "İ", "Ğ", "Ş", "Ç"]
        if lang == "en":
            tr_exclusive_chars += ["ö", "ü", "Ö", "Ü"]
            
        if any(c in desc_str for c in tr_exclusive_chars):
            return True
        if any(any(c in str(t) for c in tr_exclusive_chars) for t in tags_list):
            return True

        # Açıklamada belirgin Türkçe kalıplar, sorular, bağlaçlar veya Türkçe hashtagler varsa kesinlikle hatalıdır:
        tr_phrases = [
            "abone ol", "unutmayın", "yorumlar", "itiraf", "hikaye", "hikayeler",
            "gülmekten", "kırıp geçiren", "siz aileniz", "ne yapardınız", "buluşalım",
            "konuşma", "seslendirme", "dublaj", "öğrendiğiniz", "en tuhaf sır",
            "bu durumda", "olaylar", "merhaba", "herkese iyi", "kurgusal", "gerçek olaylar",
            "bize aittir", "tarafımızca", "seslendirmiş", "izleyin", "göz atın",
            "#reddittr", "#reddithikayeleri", "#itiraf", "#hikayezamanı", "#keşfet", "#keşfetteyiz"
        ]
        if any(p in desc_lower for p in tr_phrases):
            return True

        # Türkçe yaygın bağlaç ve kelimeler (boşluklu arama)
        tr_common_words = [
            " ve ", " bir ", " bu ", " için ", " ile ", " gibi ", " çok ", " kadar ", 
            " ama ", " fakat ", " çünkü ", " ancak ", " sonra ", " önce ", " siz ", 
            " biz ", " ben ", " veya ", " ya da ", " yok ", " var ", " olan ", 
            " olduğunu ", " olarak ", " benim ", " senin ", " onun ", " yorum ", 
            " takip ", " beğen ", " paylaş ", " olay "
        ]
        padded_desc = f" {desc_lower} "
        if any(w in padded_desc for w in tr_common_words):
            return True

        # Etiketlerde Türkçe anahtar kelimeler varsa hatalıdır:
        tr_tags = [
            "hikayeleri", "türkiye", "itiraflar", "sırları", "türkçe", "seslendirme",
            "dublaj", "keşfet", "keşfetteyiz", "komedi", "mizah", "troll", "bidublaj",
            "konuşma", "diyalog", "eğlence", "itiraf", "gerçek hikayeler", "hikaye",
            "gizem", "korku", "gerilim", "olay", "olaylar", "aile", "sır", "sırlar",
            "hayat", "anılar", "takip", "beğen"
        ]
        for tg in tags_list:
            tg_clean = str(tg).lower().strip()
            if tg_clean in tr_tags or any(w in tg_clean for w in ["hikaye", "itiraf", "türk"]):
                return True

    # 3. Dil Türkçe İSE ama açıklamada açıkça yabancı dilde fallback/hashtag kalmışsa:
    elif lang == "tr":
        if "unbelievable reddit confessions" in desc_lower or "what would you have done" in desc_lower or "#redditstories" in desc_lower or "don't forget to like, subscribe" in desc_lower:
            return True

    return False


class ChannelManager:
    def __init__(self, config_path: str = DEFAULT_CHANNELS_FILE):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path) as f:
                data = json.load(f)
                if "channels" not in data:
                    data["channels"] = []
                if "groups" not in data:
                    data["groups"] = []
                return data
        return {"channels": [], "groups": []}

    def _save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ── CRUD (Kanallar) ──────────────────────────────────

    def add_channel(
        self,
        channel_id: str,
        name: str,
        language: str,
        topic_category: str = "space",
        custom_topics: list = None,
        schedule_hour: int = 9,
        privacy: str = "public",
        active: bool = True,
        shorts_mode: bool = False,
        transition: str = "fade",
        edit_options: dict = None,
        voice_clone_id: str | None = None,
        instagram: bool | None = None,
        instagram_username: str = None,
        instagram_user_id: str = None,
    ) -> dict:
        """Yeni kanal ekler. edit_options kanal-bazlı video edit override'ları içerir."""
        existing_channel = self.get_channel(channel_id) or {}
        
        # Konu kategorisi profiline göre en ideal ayarları çek
        preset = get_category_preset(topic_category, language=language, channel_name=name)
        eff_shorts_mode = shorts_mode if (shorts_mode is True or shorts_mode is False and not existing_channel) else preset["shorts_mode"]
        eff_schedule_hour = schedule_hour if schedule_hour != 9 else preset.get("schedule_hour", 19)
        eff_transition = transition if (transition and transition != "fade") else preset.get("transition", "fade")
        
        merged_edit_opts = {**DEFAULT_EDIT_OPTIONS, **preset.get("edit_options", {}), **(existing_channel.get("edit_options") or {}), **(edit_options or {})}
        if voice_clone_id is not None:
            merged_edit_opts["voice_clone_id"] = voice_clone_id or None
        eff_voice_clone_id = merged_edit_opts.get("voice_clone_id") or existing_channel.get("voice_clone_id")

        channel = {
            "channel_id": channel_id,
            "name": name,
            "language": language,
            "topic_category": topic_category,
            "custom_topics": custom_topics or [],
            "schedule_hour": eff_schedule_hour,
            "privacy": privacy,
            "active": active,
            "shorts_mode": eff_shorts_mode,
            "transition": eff_transition,
            "voice_clone_id": eff_voice_clone_id,
            "edit_options": merged_edit_opts,
            "instagram": bool(existing_channel.get("instagram", False) if instagram is None else instagram),
            "instagram_username": (instagram_username or "").strip().lstrip("@") or existing_channel.get("instagram_username", ""),
            "instagram_user_id": (instagram_user_id or "").strip() or existing_channel.get("instagram_user_id", ""),
            "created_at": existing_channel.get("created_at") or datetime.now().isoformat(),
            "last_run": existing_channel.get("last_run"),
            "video_count": existing_channel.get("video_count", 0),
        }
        # Var mı kontrol et
        self._data["channels"] = [
            c for c in self._data["channels"] if c["channel_id"] != channel_id
        ]
        self._data["channels"].append(channel)
        self._save()
        print(f"[MANAGER] Kanal eklendi: {name} ({channel_id})")

        # Çöp adam veya infografik kanalları için özel anlatıcı ve profil avatarını otomatik oluştur
        norm_cat = normalize_category_name(topic_category)
        if norm_cat in ("crayon_combat", "tech_finance_essay", "stickman", "boskafa") or any(k in channel_id.lower() for k in ("crayon", "stickman", "boskafa", "copadam")):
            try:
                from stickman_engine.channel_narrator_factory import ChannelNarratorFactory
                narrator_profile = ChannelNarratorFactory.ensure_channel_narrator(
                    channel_id=channel_id,
                    topic_category=topic_category,
                    channel_name=name
                )
                channel["narrator_profile"] = narrator_profile
                self._save()
            except Exception as e_fac:
                print(f"[MANAGER] Narrator factory note: {e_fac}")

        return channel

    def remove_channel(self, channel_id: str):
        # Kanal silinirse bulunduğu gruptan da çıkar
        for g in self._data.get("groups", []):
            if channel_id in g.get("channel_ids", []):
                g["channel_ids"].remove(channel_id)
        self._data["channels"] = [
            c for c in self._data["channels"] if c["channel_id"] != channel_id
        ]
        self._save()

    def get_channel(self, channel_id: str) -> dict | None:
        for c in self._data["channels"]:
            if c["channel_id"] == channel_id:
                return c
        return None

    def get_active_channels(self) -> list[dict]:
        return [c for c in self._data["channels"] if c.get("active", True)]

    def all_channels(self) -> list[dict]:
        return self._data["channels"]

    def update_last_run(self, channel_id: str):
        for c in self._data["channels"]:
            if c["channel_id"] == channel_id:
                c["last_run"] = datetime.now().isoformat()
                c["video_count"] = c.get("video_count", 0) + 1
        self._save()

    def set_active(self, channel_id: str, active: bool):
        for c in self._data["channels"]:
            if c["channel_id"] == channel_id:
                c["active"] = active
        self._save()

    def get_resolved_edit_options(self, channel_id: str) -> dict:
        """
        Kanal-bazlı edit_options + global settings birleşimini döner.
        Kanal None olan alanlar için global SettingsManager'a düşer.
        """
        from settings_manager import SettingsManager
        settings = SettingsManager()
        channel = self.get_channel(channel_id) or {}
        merged = {}
        for k, default in DEFAULT_EDIT_OPTIONS.items():
            chan_val = channel.get("edit_options", {}).get(k)
            if chan_val is not None and chan_val != "":
                merged[k] = chan_val
            else:
                merged[k] = settings.get(k, default or "")

        # Grup ayarlarından devralma (özellikle Reddit / WhatsApp ayarları)
        grp = self.get_channel_group(channel_id)
        if grp:
            if not merged.get("reddit_avatar_path") and grp.get("reddit_avatar_path"):
                merged["reddit_avatar_path"] = grp.get("reddit_avatar_path")
            if not merged.get("reddit_username") and grp.get("reddit_username"):
                merged["reddit_username"] = grp.get("reddit_username")

        # Avatar hala boşsa kanalın logo veya filigran yolunu avatar olarak kullan
        if not merged.get("reddit_avatar_path"):
            merged["reddit_avatar_path"] = merged.get("censor_logo_path") or merged.get("watermark_path")

        return merged

    def apply_category_preset(self, channel_id: str, overwrite_custom: bool = False) -> dict | None:
        """
        Kanalın konu kategorisine (topic_category) göre en ideal viral YouTube & Shorts
        ayarlarını (shorts_mode, süre, yayın saati, ses standardı, hook, kategori vb.) otomatik uygular.
        """
        channel = self.get_channel(channel_id)
        if not channel:
            return None

        cat = channel.get("topic_category", "space")
        lang = channel.get("language", "tr")
        ch_name = channel.get("name") or channel_id
        preset = get_category_preset(cat, language=lang, channel_name=ch_name)

        channel["shorts_mode"] = preset["shorts_mode"]
        channel["schedule_hour"] = preset["schedule_hour"]
        if preset.get("transition") and (overwrite_custom or not channel.get("transition")):
            channel["transition"] = preset["transition"]

        if "edit_options" not in channel or not isinstance(channel["edit_options"], dict):
            channel["edit_options"] = {}

        for k, v in preset.get("edit_options", {}).items():
            if overwrite_custom or channel["edit_options"].get(k) is None or channel["edit_options"].get(k) == "":
                channel["edit_options"][k] = v
            # Outro ve süre kritik kuralları: Shorts ise ve outro varsa temizle
            if k == "outro_clip_path" and preset["shorts_mode"]:
                channel["edit_options"]["outro_clip_path"] = None
            if k == "video_duration" and preset["shorts_mode"]:
                curr_dur = channel["edit_options"].get("video_duration")
                try:
                    if not curr_dur or float(curr_dur) > 60.0:
                        channel["edit_options"]["video_duration"] = v
                except Exception:
                    channel["edit_options"]["video_duration"] = v

        # Filigran yoksa otomatik temiz isim ekle
        if not channel["edit_options"].get("watermark_text") and preset.get("edit_options", {}).get("watermark_text"):
            channel["edit_options"]["watermark_text"] = preset["edit_options"]["watermark_text"]

        self._save()
        print(f"[MANAGER] '{channel.get('name')}' ({channel_id}) kanalı '{cat}' kategorisine göre optimize edildi.")
        return channel

    def apply_all_category_presets(self, overwrite_custom: bool = False) -> list[dict]:
        """Sistemdeki tüm kanalları kendi konu kategorilerine göre optimize eder."""
        updated = []
        for ch in list(self._data.get("channels", [])):
            res = self.apply_category_preset(ch["channel_id"], overwrite_custom=overwrite_custom)
            if res:
                updated.append(res)
        return updated

    # ── CRUD (Kanal Grupları) ────────────────────────────

    def all_groups(self) -> list[dict]:
        """Tüm kanal gruplarını döner."""
        return self._data.get("groups", [])

    def get_group(self, group_id: str) -> dict | None:
        """Belirtilen ID'ye sahip grubu döner."""
        for g in self._data.get("groups", []):
            if g.get("id") == group_id:
                return g
        return None

    def get_grouped_channel_ids(self) -> set[str]:
        """Herhangi bir gruba dahil olan kanal ID'leri kümesini döner."""
        grouped = set()
        for g in self._data.get("groups", []):
            for cid in g.get("channel_ids", []):
                grouped.add(cid)
        return grouped

    def get_channel_group(self, channel_id: str) -> dict | None:
        """Belirtilen kanalın üyesi olduğu grubu döner."""
        for g in self._data.get("groups", []):
            if channel_id in g.get("channel_ids", []):
                return g
        return None

    def add_group(
        self,
        name: str,
        topic_category: str,
        channel_ids: list[str],
        group_id: str = None,
        reddit_avatar_path: str = None,
        reddit_username: str = None,
    ) -> dict:
        """
        Yeni kanal grubu oluşturur.
        Kural 1: Tüm kanalların topic_category değeri aynı olmalıdır.
        Kural 2: Gruba eklenecek kanalların bireysel içerik planı boş olmalıdır (üretilmemiş konu olmamalıdır).
        """
        if not name or not name.strip():
            raise ValueError("Grup adı boş olamaz.")
        
        if not channel_ids or len(channel_ids) < 1:
            raise ValueError("Grupta en az 1 kanal bulunmalıdır.")

        if not group_id:
            import re
            import time
            slug = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower().strip())
            group_id = f"grp_{slug}_{int(time.time())}"

        # 1. Kategori kontrolü
        category_norm = topic_category.strip().lower()
        selected_channels = []
        for cid in channel_ids:
            ch = self.get_channel(cid)
            if not ch:
                raise ValueError(f"Kanal bulunamadı: {cid}")
            ch_cat = (ch.get("topic_category") or "").strip().lower()
            if ch_cat != category_norm:
                raise ValueError(
                    f"Kanal '{ch.get('name')}' ({ch_cat}) grup kategorisi ({category_norm}) ile eşleşmiyor! "
                    f"Bir gruba yalnızca aynı konu kategorisine sahip kanallar eklenebilir."
                )
            selected_channels.append(ch)

        # 2. Boş içerik planı kontrolü
        from content_planner import ContentPlanner
        from settings_manager import SettingsManager
        settings = SettingsManager()
        out_base = Path(settings.get("output_dir", "output"))

        for ch in selected_channels:
            cid = ch["channel_id"]
            chan_dir = out_base / cid
            planner = ContentPlanner(chan_dir)
            if planner.plan_exists():
                plan_rows = planner.get_plan()
                unproduced = [
                    r for r in plan_rows 
                    if str(r.get("uretildi", "")).strip().lower() not in ("evet", "true", "1")
                ]
                if len(unproduced) > 0:
                    raise ValueError(
                        f"'{ch.get('name')}' kanalının mevcut içerik planında {len(unproduced)} adet üretilmemiş konu bulunmaktadır. "
                        f"Kanalı ortak bir gruba eklemek için bireysel içerik planı boş olmalıdır. "
                        f"Lütfen önce kanalın içerik planını temizleyin."
                    )

        # Grubu oluştur / güncelle
        if "groups" not in self._data:
            self._data["groups"] = []

        # Eğer kanallar başka gruptaysa oradan çıkar
        for g in self._data["groups"]:
            if g.get("id") != group_id:
                g["channel_ids"] = [cid for cid in g.get("channel_ids", []) if cid not in channel_ids]

        group = {
            "id": group_id,
            "name": name.strip(),
            "topic_category": category_norm,
            "channel_ids": channel_ids,
            "reddit_avatar_path": reddit_avatar_path,
            "reddit_username": reddit_username,
            "created_at": datetime.now().isoformat(),
        }

        self._data["groups"] = [g for g in self._data["groups"] if g.get("id") != group_id]
        self._data["groups"].append(group)
        self._save()

        # Ortak grup klasörünü ve boş CSV'sini oluştur
        grp_dir = out_base / "groups" / group_id
        grp_dir.mkdir(parents=True, exist_ok=True)
        grp_planner = ContentPlanner(grp_dir)
        if not grp_planner.plan_exists():
            grp_planner._write_all([])

        print(f"[MANAGER] Kanal grubu oluşturuldu: {name} ({group_id}) - {len(channel_ids)} kanal")
        return group

    def update_group(
        self,
        group_id: str,
        name: str,
        channel_ids: list[str],
        reddit_avatar_path: str = None,
        reddit_username: str = None,
    ) -> dict:
        """Mevcut grubu günceller."""
        grp = self.get_group(group_id)
        if not grp:
            raise ValueError("Grup bulunamadı.")
        return self.add_group(
            name=name,
            topic_category=grp.get("topic_category", "reddit_stories"),
            channel_ids=channel_ids,
            group_id=group_id,
            reddit_avatar_path=reddit_avatar_path if reddit_avatar_path is not None else grp.get("reddit_avatar_path"),
            reddit_username=reddit_username if reddit_username is not None else grp.get("reddit_username"),
        )

    def delete_group(self, group_id: str):
        """Grubu siler."""
        if "groups" in self._data:
            self._data["groups"] = [g for g in self._data["groups"] if g.get("id") != group_id]
            self._save()
            print(f"[MANAGER] Kanal grubu silindi: {group_id}")

    def summary(self) -> str:
        lines = ["=" * 60, "KANAL VE GRUP ÖZETİ", "=" * 60]
        for c in self._data["channels"]:
            status = "✅ Aktif" if c.get("active") else "⏸ Pasif"
            grp = self.get_channel_group(c["channel_id"])
            grp_str = f" [Grup: {grp['name']}]" if grp else ""
            lines.append(
                f"{status}  {c['name']} [{c['channel_id']}]{grp_str}\n"
                f"       Dil: {c['language']}  |  Konu: {c['topic_category']}\n"
                f"       Toplam video: {c.get('video_count', 0)}  |  Son çalışma: {c.get('last_run', '-')}"
            )
        lines.append("=" * 60)
        return "\n".join(lines)
