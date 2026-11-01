"""
aviation_media_fetcher.py
=========================
Havacılık (aviation / blackbox) belgesel kanalları için telifsiz, filigransız ve ticari
kullanıma uygun gerçek video klipleri (Pixabay Video API) ve tarihi olay/uçak fotoğrafları
(Wikimedia Commons API / NTSB Kamu Malı Arşivi) çekme motoru.

ÖZELLİKLER:
1. Pixabay Video API: 1080p MP4 kokpit, bulut, fırtına, kule ve pist B-roll video klipleri.
2. Wikimedia Commons API: Gerçek kazaların uçak fotoğrafları (N-number), rota haritaları ve NTSB inceleme kareleri.
3. Sahne Bağlamı & Faz Koruması:
   - Faz 1 (0-%25): SADECE ilgili havayolu/gövde (başka havayolu sızıntısı KESİNLİKLE yasak)
   - Faz 2 (%25-%60): Kokpit, göstergeler, tırmanış
   - Faz 3 (%60-%80): NTSB diyagramları ve radar kurgusu
   - Faz 4 (%80-%100): Gerçek enkaz, kaza mahalli ve kaza kırım raporları (Savaş gemileri/alakasız stoklar yasak)
4. Çeşitlilik & Anti-Repetition: Aynı video içinde aynı klip veya fotoğraf asla tekrarlanmaz.
5. Otomatik Boyutlandırma: ffmpeg ile 1920x1080 (veya dikey) çözünürlüğe ve sahne süresine tam oturtulur.
"""

from __future__ import annotations

import os
import re
import json
import random
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image, ImageStat

try:
    from aviation_telemetry_engine import extract_incident_metadata
except ImportError:
    from src.aviation_telemetry_engine import extract_incident_metadata

try:
    from aviation_stickman_composite import (
        generate_animated_cvr_video,
        generate_animated_atc_video,
        generate_animated_investigation_video,
        render_cockpit_cvr_reconstruction,
        render_atc_tower_reconstruction,
        render_investigation_reconstruction
    )
except ImportError:
    try:
        from src.aviation_stickman_composite import (
            generate_animated_cvr_video,
            generate_animated_atc_video,
            generate_animated_investigation_video,
            render_cockpit_cvr_reconstruction,
            render_atc_tower_reconstruction,
            render_investigation_reconstruction
        )
    except ImportError:
        generate_animated_cvr_video = None
        generate_animated_atc_video = None
        generate_animated_investigation_video = None
        render_cockpit_cvr_reconstruction = None
        render_atc_tower_reconstruction = None
        render_investigation_reconstruction = None

# Varsayılan Pixabay API Anahtarı
DEFAULT_PIXABAY_KEY = "57648418-49ecb0060f2db281a386d04cf"


def get_pixabay_key() -> str:
    """Aktif Pixabay API anahtarını settings veya çevreden alır."""
    try:
        from settings_manager import SettingsManager
        sm = SettingsManager()
        val = sm.get("pixabay_api_key")
        if val and str(val).strip():
            return str(val).strip()
    except Exception:
        pass
    return os.environ.get("PIXABAY_API_KEY", DEFAULT_PIXABAY_KEY)


def _http_get_json(url: str, timeout: int = 12) -> Optional[Dict[str, Any]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[AVIATION-FETCHER] HTTP isteği başarısız ({url[:70]}...): {e}")
        return None


ALLOWED_AVIATION_TAGS = {
    'cockpit', 'airplane', 'aircraft', 'aeroplane', 'pilot', 'aviation',
    'flight', 'boeing', 'airbus', 'runway', 'airliner', 'jet engine',
    'tarmac', 'airport', 'turbofan', 'jet', 'radar', 'plane', 'sky', 'clouds'
}

# Doğrudan yasaklı klip ID'leri (Havacılık belgesellerini bozan hatalı veya alakasız klipler)
FORBIDDEN_PIXABAY_IDS = {
    2860,    # Hong Kong sahil ve gökdelen gece drone klibi (Asian illuminated city skyline)
    282,     # United Airlines yağmurlu apron ve servis kamyoneti klibi
    283,     # United Airlines apron klibi
    32975,   # Günlük güneşlik gökyüzünde modern winglet ve beyaz bulutlar (Daylight sunny clouds winglet)
    212404,  # Şanghay Bund gece şehir ışıkları ve gökdelenler
    231994,  # Otoyol gece trafik ve ışık şeritleri
    21116,   # Seul gece sokak ve neon araba trafiği
    21118,   # Seul gece şehir trafiği
    2142,    # Qatar Airways A350/787 kanadı (airplane flying in clouds - başka havayolu sızıntısı)
    200439,  # Geniş gövde modern jet kanadı (commercial jet sky - turboprop uçuşlarda sızıntı)
    47333,   # Madeira / Funchal sahil yaklaşması (Madeira Portugal pilot view)
    371940,  # Plastik maket boyama / model hobby klip
    276047,  # Alakasız simülasyon / hatalı klip
    51016,   # Güneş gözlüklü tek motorlu Cessna pervaneli kokpit lövyesi
    14590,   # İngiltere banliyö döner kavşağı (roundabout) drone çekimi
    142802,  # Otomobil hız ve devir göstergesi (car dashboard speedometer)
    131655,  # Tekrarlayan model uçak/yanlış gösterge klibi
    131656,  # Tekrarlayan model uçak/yanlış gösterge klibi
    6416,    # Yeşil ekran 3D askeri kargo/gunship (AC-130 chroma key)
    29806,   # Sakin meydanda park halinde bekleyen sarı-beyaz Piper eğitim uçağı
    81945,   # Tekrarlayan analog kokpit göstergesi
    23857,   # Yanlış gösterge klibi
    313422,  # Alakasız helikopter
}

BASE_FORBIDDEN_TAGS = {
    'fountain', 'guitar', 'music', 'instrument', 'musician', 'dog',
    'cat', 'pet', 'animal', 'flower', 'poppy', 'garden', 'park', 'candle',
    'fireplace', 'wood', 'clock', 'watch', 'alarm', 'office', 'laptop',
    'meeting', 'desk', 'room', 'manga', 'comic', 'metro', 'subway', 'train',
    'railroad', 'coffee', 'couch', 'sofa', 'field', 'farm', 'drone',
    'cow', 'sheep', 'signboard', 'placard', 'museum display',
    'escalator', 'travelator', 'moving walkway', 'fuse panel', 'rotating fan',
    # Şehir, Otoyol, Gökdelen & Kara Trafiği Korumaları (Havacılık belgeselinde şehir drone klibi KESİNLİKLE yasak)
    'city', 'skyscrapers', 'skyline', 'traffic', 'highway', 'buildings', 'neon', 'urban',
    'downtown', 'bridge', 'street', 'cars', 'road', 'metropolis', 'suburb', 'pedestrian',
    'architecture', 'town', 'night view', 'cityscape', 'city lights', 'traffic jam', 'freeway',
    # Müze, Statik Sergi & Hangar Korumaları (Havadaki uçuş anlatılırken müze fotoğrafları KESİNLİKLE yasak)
    'museum', 'exhibit', 'display', 'static display', 'air and space', 'museum display',
    'hangar', 'aviation museum', 'exhibition', 'preserved', 'tarmac museum',
    # Metro, Tren & Raylı Sistem Korumaları (Havacılık belgeseline metro asla sızamaz)
    'metro', 'subway', 'train', 'underground', 'railway', 'railroad', 'commuter train',
    'train station', 'metro station', 'passengers walking in metro',
    # Slayt, Yazılım & Devre Şemaları (Üniversite slaytları ve akış şemaları yasak)
    'diagram', 'flow chart', 'data flow', 'schematic', 'circuit', 'presentation',
    'slide', 'whiteboard', 'infographic diagram', 'flowchart', 'slide presentation',
    # Akrobasi ve Gösteri Uçakları
    'aerobatic', 'acrobatic', 'airshow stunt', 'stunt plane',
    # Yeşil Ekran / Chroma Key Korumaları
    'green screen', 'greenscreen', 'chroma', 'chromakey', 'keying', 'green background',
    # Maket, Oyuncak & Hobi Korumaları
    'toy', 'toys', 'model', 'models', 'miniature', 'scale model', 'rc plane', 'rc',
    'plastic model', 'diorama', 'figurine', 'hobby',
    # 2. Dünya Savaşı / Floatplane / Deniz Uçağı Korumaları
    'ww2', 'warbird', 'floatplane', 'seaplane', 'flying boat', 'arado', 'stuka',
    'spitfire', 'messerschmitt', 'luftwaffe',
    # Tek Motorlu Küçük Pervaneli Uçaklar (Yolcu uçağı belgesellerinde Cessna/Piper KESİNLİKLE yasak)
    'cessna', 'piper', 'beechcraft bonanza', 'single engine', 'light aircraft', 'general aviation',
    'ultralight', 'glider', 'biplane', 'crop duster', 'n14465p', 'n171cb', 'skyhawk',
    # Askeri Savaş Uçağı & HUD Korumaları
    'hud', 'head-up', 'fighter', 'f-16', 'f-18', 'f-15', 'f-22', 'f-35',
    'jet fighter', 'combat', 'military display', 'warplane', 'bomber', 'ac-130', 'gunship',
    # Tek motorlu pervaneli uçaklar & Tarihi DC-3 (Yolcu jeti/bölgesel uçak belgesellerinde kesinlikle yasak)
    'cessna', 'single engine', 'light aircraft', 'general aviation',
    'glider', 'ultralight', 'biplane', 'piper', 'dc-3', 'dc3', 'dakota', 'ph-pba',
    # Kuşlar, martılar & hayvan sürüleri
    'bird', 'birds', 'seagull', 'seagulls', 'flock', 'pigeon', 'wildlife',
    # Tatil, sahil & Madeira
    'madeira', 'funchal', 'resort', 'beach', 'yacht', 'island vacation',
    # Donanma gemileri & askeri gemiler
    'ship', 'warship', 'navy', 'combat ship', 'frigate', 'corvette', 'cutter', 'uss',
    # Alakasız kara trafiği ve kavşaklar
    'roundabout', 'traffic circle', 'business park', 'shopping mall',
    # Bölgesel Jetler
    'regional jet', 'crj', 'erj',
    # Otomobil, Araba & Kara Araçları
    'car', 'automobile', 'automotive', 'speedometer', 'tachometer', 'odometer',
    'dashboard', 'steering wheel', 'vehicle', 'driving', 'driver', 'motor',
    'engine bay', 'asphalt road', 'truck', 'lorry', 'bus', 'mercedes', 'bmw', 'audi',
    'porsche', 'ferrari', 'toyota', 'volkswagen', 'sedan', 'suv', 'auto'
}

# Wikimedia Commons Başlık & Semantik Kara Listesi (Havacılık belgesellerini bozan yanıltıcı içerikler)
WIKIMEDIA_TITLE_EXCLUSIONS = {
    # Müze sergileri, Casus Uçaklar & Statik Parklar (Uçuş/kaza esnasında müze çıkması KESİNLİKLE yasak)
    "museum", "m-21", "d-21", "sr-71", "blackbird", "intrepide", "display", "exhibit",
    "static display", "air and space", "museum of flight", "aerospace museum", "preserved",
    "fuselage", "mockup", "usair", "united airlines", "hangar", "exhibition",
    # Raylı Sistem & Metro
    "metro", "subway", "train", "underground", "railway",
    # Şemalar & Slaytlar
    "diagram", "flow chart", "schematic", "circuit", "presentation", "slide",
    # Donanma ve savaş gemileri
    "uss ", "navy", "combat ship", "lcs ", "destroyer", "frigate", "corvette",
    "cutter", "maritime exercise", "coast guard cutter", "sailors from uss",
    # Coğrafi / Turistik Yanılsamalar
    "everest", "himalaya", "nepal", "buddha air", "yeti airlines",
    # Yanlış / Alakasız Kaza Haritaları & Yabancı Dilli Grafikler
    "marília", "mendonça", "marilia mendonca", "mapa accident", "accident marilia",
    "carte", "absturz", "acidente", "carte de", "mapa del",
    # Tarihi Askeri Bombardıman / 1940-50'ler Eğitmen Uçakları
    "c-45", "model 18", "t-29", "t-28", "convair", "negative image", "skymaster",
    "f-106", "nara -", "usaf", "bomber", "military trainer",
    # Yanlış / Piksel Paneller & Göstergeler
    "selector de ils", "ils selector",
    # Alakasız Havayolu Logoları & Sızıntılar
    "qatar", "emirates", "etihad", "ryanair", "easyjet", "martinair", "buzz", "colgan",
    # İlgisiz / Yanıltıcı uçak modelleri & Oyuncaklar
    "737 max", "737-max", "arado", "piper", "cessna", "ac-130", "scale model", "plastic model"
}

# Deniz / Donanma / Savaş Gemisi Filtresi (Geriye dönük uyumluluk)
NAVAL_SHIP_EXCLUSIONS = WIKIMEDIA_TITLE_EXCLUSIONS


def _get_subject_key(title: str) -> str:
    """Wikimedia başlığından albüm/konu kökünü çıkarır (tekrarı engellemek için)."""
    t = re.sub(r'\(.*?\)|\[.*?\]', '', str(title)).lower()
    t = re.sub(r'\.(jpg|jpeg|png|webp|mp4)$', '', t)
    t = re.sub(r'\b(flickr|aero icarus|an\d+|file:)\b', '', t)
    words = [w for w in re.split(r'[^a-z0-9]+', t) if len(w) > 2]
    return " ".join(words[:4]) if words else t[:30]


def detect_climate_mode(text: str, default_climate: str = "NEUTRAL") -> str:
    """Metindeki bağlamdan uçuşun kış/kar, sıcak yaz, fırtına, tropikal veya standart iklimde olduğunu hassas saptar."""
    if default_climate in ["HOT", "WINTER", "TROPICAL", "STORMY", "FOG"]:
        return default_climate

    t = str(text).lower()
    if any(k in t for k in ["30-degree", "scorching", "blistering", "heat", "summer", "sunny", "30 derece", "kavurucu"]):
        return "HOT"
    if any(k in t for k in ['blizzard', 'snowstorm', 'snowfall', 'de-icing truck', 'de-icing fluid', 'kar fırtınası', 'tipi']) or ('snow' in t and 'airport' in t):
        return 'WINTER'
    if any(k in t for k in ['typhoon', 'hurricane', 'microburst', 'thunderstorm', 'tornado', 'kasırga']):
        return 'STORMY'
    if any(k in t for k in ['dense fog', 'heavy fog', 'thick fog', 'yoğun sis']):
        return 'FOG'
    if any(k in t for k in ['tropical island', 'caribbean', 'bali', 'tropikal']):
        return 'TROPICAL'
    return 'NEUTRAL'


CORE_AVIATION_TAGS = {
    'cockpit', 'airplane', 'aircraft', 'aeroplane', 'pilot', 'aviation',
    'boeing', 'airbus', 'runway', 'airliner', 'jet engine',
    'tarmac', 'airport', 'turbofan', 'jet', 'radar'
}

PEACEFUL_CALM_TAGS = {
    'sunny', 'sunshine', 'sun', 'blue sky', 'peaceful', 'calm', 'relaxing',
    'relax', 'beach', 'summer', 'summer day', 'vacation', 'resort', 'holiday',
    'serene', 'nature', 'green grass', 'meadow', 'park', 'flowers',
    'bright sky', 'clear day', 'birds', 'gentle', 'smooth flight', 'tranquil',
    'leisure', 'traveler', 'happy', 'smiling', 'enjoying', 'paradise', 'tropical',
    'island', 'tourism', 'tourist', 'sunny day', 'blue water', 'swimming', 'clouds timelapse'
}


def detect_scene_tension_mood(text: str) -> str:
    """
    Sahne metnindeki dramatik tansiyon ve duygusal atmosferi saptar:
    - DISASTER: Çarpışma, alev topu, enkaz, patlama, ölüm, can pazarı, facia
    - HIGH_TENSION: Kontrol kaybı, stall, dalış, yangın alarmı, panik, çığlık, mayday
    - TACTICAL_GROUND: Pist, taksi, sis, kule, telsiz, kalkış onayı
    - INVESTIGATION: Kara kutu, NTSB, bulgular, kaza kırım raporu
    - NORMAL_CRUISE: Standart seyir / nötr
    """
    t = str(text).lower()
    disaster_keys = [
        "crash", "collision", "impact", "erupt", "explosion", "flames", "fireball",
        "inferno", "wreckage", "debris", "burned", "fatal", "casualties", "killed",
        "died", "deadliest", "perished", "paramparça", "alev", "patlama", "ölüm",
        "can verdi", "can pazarı", "enkaz", "çakıldı", "yangın", "facia", "katliam",
        "lifeless", "bodies", "destroy", "wreck", "disaster"
    ]
    if any(k in t for k in disaster_keys):
        return "DISASTER"
        
    high_tension_keys = [
        "stall", "pull up", "dive", "overbank", "uncommanded", "mayday", "emergency",
        "alarm", "warning", "scream", "pan pan", "critical", "lost control", "pitch down",
        "spiral", "flameout", "engine failure", "düşüş", "irtifa kaybı", "panik", "çığlık",
        "kontrolden çıktı", "kurtarılamaz", "burnu aşağı", "tehlike", "sink rate", "terrain"
    ]
    if any(k in t for k in high_tension_keys):
        return "HIGH_TENSION"

    investigation_keys = [
        "investigation", "ntsb", "bfu", "ciaiac", "black box", "fdr", "cvr", "probable cause",
        "findings", "safety board", "soruşturma", "kara kutu", "rapor", "tahkikat", "kaza kırım heyeti"
    ]
    if any(k in t for k in investigation_keys):
        return "INVESTIGATION"
        
    ground_keys = [
        "taxi", "runway", "holding point", "tower", "clearance", "fog", "visibility",
        "taksi", "pist", "bekleme", "kule", "telsiz", "sis", "görüş mesafesi"
    ]
    if any(k in t for k in ground_keys):
        return "TACTICAL_GROUND"
        
    return "NORMAL_CRUISE"


def get_conflicting_aircraft_tags(target_aircraft: str) -> set:
    """
    Hedef uçak tipine (örn: Boeing 747) doğrudan çelişen/alakasız uçak modellerini döndürür.
    Böylece '747 anlatılırken A320 veya Cessna çıkması' engellenir.
    """
    tgt = str(target_aircraft).lower()
    conflicts = set()
    
    # 1. Hedef Boeing 747 (Dört motorlu dev Jumbo Jet)
    if "747" in tgt:
        conflicts |= {
            "airbus", "a320", "a319", "a321", "a330", "a350", "a380",
            "cessna", "piper", "propeller", "turboprop", "atr", "saab",
            "f-16", "f-18", "f-22", "f-35", "fighter jet", "b-21", "b-2", "concorde",
            "twin turboprop", "single engine", "private jet"
        }
    # 2. Hedef Turboprop (ATR 42/72, Saab 340, Dash 8)
    elif any(k in tgt for k in ["atr", "saab", "dash", "turboprop", "propeller"]):
        conflicts |= {
            "boeing", "airbus", "747", "777", "787", "737", "a320", "a330", "a350", "a380",
            "jumbo", "turbofan", "jet engine", "commercial jet", "contrail", "f-16", "fighter jet"
        }
    # 3. Hedef McDonnell Douglas / Douglas (DC-8, DC-9, MD-80, MD-82, DC-10)
    elif any(k in tgt for k in ["md-8", "md-9", "dc-8", "dc-9", "dc-10", "md-11", "spanair", "fine air"]):
        conflicts |= {
            "747", "jumbo", "a380", "a350", "turboprop", "propeller", "cessna", "piper",
            "fighter jet", "f-16", "f-22", "b-21"
        }
    # 4. Hedef Airbus (A330, A320)
    elif "airbus" in tgt or "a330" in tgt or "a320" in tgt:
        conflicts |= {
            "747", "jumbo", "turboprop", "propeller", "cessna", "piper", "fighter jet"
        }
    # 5. Hedef Boeing 737 / 757
    elif "737" in tgt or "757" in tgt:
        conflicts |= {
            "airbus", "a320", "a380", "747", "jumbo", "turboprop", "propeller", "cessna"
        }
        
    return conflicts


def is_aviation_media(
    tags_str: str, 
    climate: str = "NEUTRAL", 
    aircraft_category: str = "jet",
    target_aircraft: str = "",
    scene_mood: str = "NORMAL_CRUISE"
) -> bool:
    """Medya etiketlerinin kesinlikle havacılık konusu, uçak kategorisi, spesifik model ve sahne tansiyonuyla uyumlu olduğunu doğrular."""
    tags = set([t.strip().lower() for t in str(tags_str).split(',')])
    
    # 1. Genel yasaklı nesneler, şehir/otoyol ve filtreler
    if any(f in tags for f in BASE_FORBIDDEN_TAGS):
        return False

    # 2. Tansiyon ve Felaket Anı Koruması (Huzurlu/Güneşli Doğa Videolarını Engelleme)
    if scene_mood in ("DISASTER", "HIGH_TENSION"):
        if any(p in tags for p in PEACEFUL_CALM_TAGS):
            return False
        # Felaket/panik anında sadece genel bulut/gökyüzü olan tatil stoklarını engelle
        if ('clouds' in tags or 'sky' in tags) and not any(k in tags for k in ['fire', 'smoke', 'dark', 'storm', 'radar', 'cockpit', 'crash', 'wreckage', 'alert']):
            return False

    # 3. Model Çelişkisi Denetimi (X uçağı anlatılırken Z uçağı çıkmasını engelleme)
    if target_aircraft:
        conflicts = get_conflicting_aircraft_tags(target_aircraft)
        if any(c in tags for c in conflicts):
            return False

    # 4. İklim & Gece Uyumu
    if climate == 'NIGHT':
        night_forbidden = {
            'sunny', 'daylight', 'blue sky', 'sun', 'bright', 'summer', 'beach',
            'sunset clouds', 'cloudy day', 'cumulus', 'white clouds', 'winglet',
            'morning', 'afternoon', 'city', 'skyline', 'traffic', 'highway', 'street'
        }
        if any(f in tags for f in night_forbidden):
            return False
        if ('clouds' in tags or 'sky' in tags) and not any(n in tags for n in ['night', 'dark', 'cockpit', 'lightning', 'thunderstorm']):
            return False
    else:
        # Gündüz uçuşlarında gece sahneleri ve gece kokpiti YASAKTIR!
        daytime_forbidden = {'night flight', 'night sky', 'darkness', 'midnight', 'night cockpit'}
        if any(f in tags for f in daytime_forbidden):
            return False

    if climate == 'WINTER':
        winter_forbidden = {'beach', 'swimming', 'summer', 'tropical', 'palm tree', 'palms', 'resort', 'yacht', 'bikini', 'madeira'}
        if any(f in tags for f in winter_forbidden):
            return False
        winter_allowed = {'snow', 'winter', 'ice', 'blizzard', 'frost', 'de-icing'}
        if any(w in tags for w in winter_allowed) or any(a in tags for a in CORE_AVIATION_TAGS):
            return True
    else:
        # Kış dışındaki TÜM iklimlerde (HOT, TROPICAL, STORMY, FOG, NEUTRAL):
        # Kar, buz, kış, kar küreme makineleri KESİNLİKLE YASAKTIR!
        non_winter_banned = {'snow', 'winter', 'ice', 'blizzard', 'frost', 'snowplow', 'snowblower', 'snow clearing', 'ski', 'frozen', 'cold winter'}
        if any(f in tags for f in non_winter_banned):
            return False

    # 5. Motor & Uçak Tipi Uyumu (Turboprop vs Jet)
    if aircraft_category == 'turboprop':
        turboprop_forbidden = {'jet', 'turbofan', 'jet engine', 'commercial jet', 'winglet', 'jumbo', 'airbus', 'boeing', 'contrail', 'passenger jet'}
        if any(j in tags for j in turboprop_forbidden) and 'propeller' not in tags and 'turboprop' not in tags:
            return False

    # 6. İzin verilen havacılık etiketleri (Sadece 'flight' tek başına yetersizdir, havacılık öznesi şarttır)
    if any(c in tags for c in CORE_AVIATION_TAGS):
        return True
    if 'flight' in tags and any(sub in tags for sub in ['clouds', 'sky', 'turboprop', 'propeller']):
        return True
    return False


def validate_aviation_media(
    media_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    scene_data: Optional[Dict[str, Any]] = None,
    scene_idx: int = 0
) -> tuple[bool, str]:
    """
    Render Öncesi Görsel Denetçi (Pre-Render Vision QA Guard):
    1. Kaza Metadata Çapraz Denetimi (Gece, Deniz, Yasaklı Havayolları).
    2. Piksel Düzeyinde Parlaklık / Luminance Analizi (Gece uçuşlarında gündüz karelerini eler).
    3. Absürt stok videoları (şehir silüeti, otoyol, casus uçağı, müze) derhal engeller.
    """
    if not media_path or not os.path.exists(media_path):
        return False, "Dosya mevcut değil"

    meta = metadata or {}
    sc = scene_data or {}
    climate = meta.get("climate", "NEUTRAL")
    prohibited_airlines = [a.lower() for a in meta.get("prohibited_airlines", [])]
    impact_point = str(meta.get("radar", {}).get("impact_point", "")).lower()
    flight_name = str(meta.get("flight_name", "")).lower()

    # 1. Metin ve Başlık Düzeyinde Denetim
    filename = Path(media_path).name.lower()
    prompt = str(sc.get("image_prompt", "")).lower()
    narration = str(sc.get("narration", "")).lower()

    # Yasaklı havayolları sızıntı denetimi (Örn: Flash 604 için United, Turkish 981 için Lufthansa)
    for p_air in prohibited_airlines:
        if p_air in filename or p_air in prompt:
            return False, f"Vision QA Guard: Yasaklı havayolu tespit edildi ('{p_air}')"

    # Özel Kaza Yasaklı Kelimeleri (prohibited_keywords) Denetimi
    prohibited_keywords = [k.lower() for k in meta.get("prohibited_keywords", [])]
    for pk in prohibited_keywords:
        if pk in filename or pk in prompt:
            return False, f"Vision QA Guard: Yasaklı kaza bağlam kelimesi tespit edildi ('{pk}')"

    # Absürt ve Alakasız Stok İçerikleri (Müze, Tren/Metro, Şema, Slayt, Akrobasi)
    absurd_forbidden = [
        "museum", "exhibit", "hangar", "metro", "subway", "train",
        "diagram", "flow chart", "schematic", "circuit", "slide", "presentation",
        "whiteboard", "acrobatic", "aerobatic", "stunt plane"
    ]
    if any(a in prompt or a in filename for a in absurd_forbidden):
        return False, "Vision QA Guard: Absürt/alakasız stok içeriği (müze/metro/şema/akrobasi) reddedildi"

    # Deniz / Okyanus kazası denetimi (Red Sea, Atlantic, Ocean vb.)
    is_water_accident = any(w in impact_point or w in flight_name for w in ["red sea", "ocean", "sea", "gulf", "water", "potomac", "atlantic", "pacific"])
    if is_water_accident:
        urban_forbidden = ["skyline", "skyscrapers", "city lights", "traffic jam", "highway", "downtown", "buildings"]
        if any(u in prompt or u in filename for u in urban_forbidden):
            return False, "Vision QA Guard: Deniz/su kazasında şehir/gökdelen öğeleri reddedildi"

    # Casus uçağı / Askeri avcı denetimi
    military_forbidden = ["sr-71", "blackbird", "u-2", "b-2", "stealth bomber", "f-16", "f-35", "f-22"]
    if any(m in prompt or m in filename for m in military_forbidden):
        return False, "Vision QA Guard: Absürt askeri casus uçağı veya savaş uçağı reddedildi"

    # 2. Uçak Modeli Çelişki Denetimi (X uçağı anlatılırken Z uçağı çıkmasını engelleme)
    target_aircraft = str(meta.get("aircraft_type") or meta.get("aircraft_short") or meta.get("flight_name", "")).lower()
    if target_aircraft:
        conflicts = get_conflicting_aircraft_tags(target_aircraft)
        for c in conflicts:
            if c in filename or c in prompt:
                return False, f"Vision QA Guard: Hedef uçak '{target_aircraft}' iken çelişen uçak modeli ('{c}') tespit edildi."

    # 3. Duygu ve Tansiyon Denetimi (Felaket söylenirken sakin doğa/güneşli klibi engelleme)
    comb_text = f"{narration} {prompt} {sc.get('emotion', '')}".lower()
    scene_mood = detect_scene_tension_mood(comb_text)
    if scene_mood in ("DISASTER", "HIGH_TENSION"):
        for p in PEACEFUL_CALM_TAGS:
            if p in filename or p in prompt:
                return False, f"Vision QA Guard: Felaket/panik sahnesinde (Tansiyon: {scene_mood}) sakin/güneşli/huzurlu içerik ('{p}') reddedildi."
        if scene_mood == "DISASTER" and any(g in filename for g in ["flying in clouds", "airport runway", "clouds aerial", "sunny"]):
            return False, "Vision QA Guard: Kaza ve facia anında genel sakin bulut/pist stok videosu reddedildi."

    # Sıcak Yaz İkliminde Kar/Buz Denetimi (30 Derece Madrid vs Karlı Apron)
    if climate == "HOT":
        if any(w in prompt or w in filename for w in ["snow", "winter", "ice", "blizzard", "frost", "snowplow"]):
            return False, "Vision QA Guard: 30 derece sıcak iklimde karlı meydan klibi reddedildi"

    # 2. Piksel ve Kare Düzeyinde Parlaklık (Luminance) Denetimi
    if climate == "NIGHT":
        try:
            im = None
            if media_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                im = Image.open(media_path).convert("L")
            elif media_path.lower().endswith(".mp4"):
                cmd = [
                    "ffmpeg", "-y", "-ss", "0.8", "-i", media_path,
                    "-vframes", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "-"
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
                if res.returncode == 0 and res.stdout:
                    import io
                    im = Image.open(io.BytesIO(res.stdout)).convert("L")

            if im:
                stat = ImageStat.Stat(im)
                mean_lum = stat.mean[0]
                sky_box = (0, 0, im.width, int(im.height * 0.35))
                sky_stat = ImageStat.Stat(im.crop(sky_box))
                sky_lum = sky_stat.mean[0]

                if mean_lum > 135 or sky_lum > 145:
                    return False, f"Vision QA Guard: Gece uçuşunda gündüz sahnesi saptandı (Ort. Parlaklık: {mean_lum:.1f})"
        except Exception as e_lum:
            print(f"[VISION-QA-GUARD] Luminance denetim uyarısı: {e_lum}")

    return True, "Passed"


def search_pixabay_video(
    query: str, 
    exclude_ids: Optional[set] = None, 
    min_duration: float = 4.0, 
    climate: str = "NEUTRAL",
    aircraft_category: str = "jet",
    target_aircraft: str = "",
    scene_mood: str = "NORMAL_CRUISE"
) -> Optional[Dict[str, Any]]:
    """Pixabay Video API üzerinden sorguya uygun %100 havacılık MP4 videosu arar (KESİNLİKLE YATAY 16:9)."""
    api_key = get_pixabay_key()
    params = {
        "key": api_key,
        "q": query,
        "video_type": "film",
        "per_page": 25
    }
    url = f"https://pixabay.com/api/videos/?{urllib.parse.urlencode(params)}"
    data = _http_get_json(url)
    if not data or not data.get("hits"):
        return None

    hits = data["hits"]
    exclude = (exclude_ids or set()) | FORBIDDEN_PIXABAY_IDS
    
    # KESİNLİKLE YATAY (width >= height) ve havacılık uyumu filtresi
    valid_hits = []
    for h in hits:
        if h.get("id") in exclude:
            continue
        if not is_aviation_media(h.get("tags", ""), climate=climate, aircraft_category=aircraft_category, target_aircraft=target_aircraft, scene_mood=scene_mood):
            continue
        
        videos = h.get("videos", {})
        stream = videos.get("medium") or videos.get("large") or videos.get("small")
        if not stream:
            continue
            
        w = stream.get("width", 0)
        h_val = stream.get("height", 0)
        
        # Dikey telefon / Shorts / Reels videolarını (1080x1920) KESİNLİKLE ELE!
        if w < h_val or h_val == 0 or (w / h_val) < 1.3:
            continue
            
        if h.get("duration", 0) >= min_duration:
            valid_hits.append(h)

    if not valid_hits:
        return None

    chosen = random.choice(valid_hits[:5])
    videos = chosen.get("videos", {})
    stream = videos.get("medium") or videos.get("large") or videos.get("small")
    if not stream or not stream.get("url"):
        return None

    return {
        "id": chosen["id"],
        "url": stream["url"],
        "duration": chosen.get("duration", 0),
        "width": stream.get("width", 1920),
        "height": stream.get("height", 1080)
    }


def search_pixabay_photo(
    query: str, 
    exclude_ids: Optional[set] = None, 
    climate: str = "NEUTRAL", 
    aircraft_category: str = "jet",
    target_aircraft: str = "",
    scene_mood: str = "NORMAL_CRUISE"
) -> Optional[Dict[str, Any]]:
    """Pixabay Fotoğraf API üzerinden sorguya uygun yüksek çözünürlüklü yatay görsel arar."""
    api_key = get_pixabay_key()
    params = {
        "key": api_key,
        "q": query,
        "image_type": "photo",
        "per_page": 20
    }
    url = f"https://pixabay.com/api/?{urllib.parse.urlencode(params)}"
    data = _http_get_json(url)
    if not data or not data.get("hits"):
        return None

    hits = data["hits"]
    exclude = (exclude_ids or set()) | FORBIDDEN_PIXABAY_IDS
    valid_hits = [
        h for h in hits 
        if h.get("id") not in exclude 
        and is_aviation_media(h.get("tags", ""), climate=climate, aircraft_category=aircraft_category, target_aircraft=target_aircraft, scene_mood=scene_mood)
        and h.get("imageWidth", 1920) >= h.get("imageHeight", 1080)
    ]
    if not valid_hits:
        return None

    chosen = random.choice(valid_hits[:5])
    img_url = chosen.get("largeImageURL") or chosen.get("webformatURL")
    if not img_url:
        return None

    return {
        "id": chosen["id"],
        "url": img_url,
        "width": chosen.get("imageWidth", 1920),
        "height": chosen.get("imageHeight", 1080)
    }


def search_wikimedia_commons(query: str, limit: int = 8, prohibited_terms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Wikimedia Commons üzerinden gerçek uçak/olay görsellerini arar (Public Domain/CC)."""
    headers = {
        "User-Agent": "AviationDocApp/3.0 (contact: blackbox@production.aero)"
    }
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,  # File namespace
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|mime"
    }
    url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[AVIATION-FETCHER] Wikimedia sorgu hatası ({query}): {e}")
        return []

    pages = data.get("query", {}).get("pages", {})
    results = []
    proh = [p.lower() for p in (prohibited_terms or [])]

    for pid, page in pages.items():
        title = page.get("title", "")
        t_low = title.lower()

        # İkon, bayrak, audio, logoları filtrele
        if any(skip in t_low for skip in [".svg", ".ogg", ".oga", ".pdf", "flag", "icon", "logo", "symbol"]):
            continue

        # Semantik / coğrafi / donanma / yanıltıcı görsel filtresi
        if any(ex in t_low for ex in WIKIMEDIA_TITLE_EXCLUSIONS):
            continue

        # Başka havayolu sızıntılarını ele
        if any(pr in t_low for pr in proh):
            continue

        imageinfo = page.get("imageinfo", [])
        if not imageinfo:
            continue
        ii = imageinfo[0]
        mime = ii.get("mime", "")
        if mime not in ("image/jpeg", "image/png"):
            continue
            
        w_ii = ii.get("width", 0)
        h_ii = ii.get("height", 0)
        # Dikey veya çok düşük çözünürlüklü görselleri ele
        if w_ii < h_ii or (w_ii > 0 and w_ii < 700):
            continue
            
        img_url = ii.get("url")
        if img_url:
            results.append({
                "title": title,
                "url": img_url,
                "width": w_ii,
                "height": h_ii
            })
    return results


def download_and_format_video(
    stream_url: str,
    output_path: str,
    target_w: int = 1920,
    target_h: int = 1080,
    target_dur: float = 5.0
) -> bool:
    """Video akışını indirir ve ffmpeg ile tam hedef süre/çözünürlüğe ayarlar (Dikey/rotasyon korumalı)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    temp_raw = output_path + ".raw.mp4"
    try:
        req = urllib.request.Request(stream_url, headers=headers)
        with urllib.request.urlopen(req, timeout=40) as resp, open(temp_raw, "wb") as f_out:
            while chunk := resp.read(64 * 1024):
                f_out.write(chunk)

        if not os.path.exists(temp_raw) or os.path.getsize(temp_raw) < 10000:
            return False

        # ffprobe ile rotasyon ve gerçek en/boy oranını doğrula
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height:stream_tags=rotate",
            "-of", "json",
            temp_raw
        ]
        try:
            p_res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=8)
            if p_res.returncode == 0:
                p_data = json.loads(p_res.stdout)
                streams = p_data.get("streams", [])
                if streams:
                    s0 = streams[0]
                    raw_w = s0.get("width", 1920)
                    raw_h = s0.get("height", 1080)
                    rot = int(s0.get("tags", {}).get("rotate", 0) or 0)
                    if abs(rot) in (90, 270):
                        raw_w, raw_h = raw_h, raw_w
                    if raw_w < raw_h:
                        print(f"[AVIATION-FETCHER] 🚫 Dikey video tespit edildi ({raw_w}x{raw_h}), elendi!")
                        return False
        except Exception:
            pass

        # ffmpeg ile loop + scale + center-crop + süre kısıtı (KESİNLİKLE 25 FPS ve standart timescale)
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", temp_raw,
            "-t", f"{target_dur:.3f}",
            "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},fps=25,setsar=1",
            "-r", "25",
            "-video_track_timescale", "12800",
            "-c:v", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-an",
            output_path
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=120)
        return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000
    except Exception as e:
        print(f"[AVIATION-FETCHER] Video dönüştürme hatası: {e}")
        return False
    finally:
        if os.path.exists(temp_raw):
            try:
                os.remove(temp_raw)
            except Exception:
                pass


def download_and_format_image(
    img_url: str,
    output_path: str,
    target_w: int = 1920,
    target_h: int = 1080
) -> bool:
    """Görseli indirir, en boy oranını koruyarak doldurur (fill-crop) ve kaydeder."""
    headers = {
        "User-Agent": "AviationDocApp/3.0 (contact: blackbox@production.aero; documentary)"
    }
    temp_img = output_path + ".tmp.jpg"
    try:
        req = urllib.request.Request(img_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp, open(temp_img, "wb") as f_out:
            f_out.write(resp.read())

        im = Image.open(temp_img).convert("RGB")
        src_w, src_h = im.size
        scale = max(target_w / src_w, target_h / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)

        im = im.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        im = im.crop((left, top, left + target_w, top + target_h))
        im.save(output_path, "JPEG", quality=95)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 5000
    except Exception as e:
        print(f"[AVIATION-FETCHER] Görsel indirme/işleme hatası: {e}")
        return False
    finally:
        if os.path.exists(temp_img):
            try:
                os.remove(temp_img)
            except Exception:
                pass


def classify_scene_aviation_query(
    scene_data: Dict[str, Any], 
    scene_idx: int, 
    total_scenes: int, 
    climate: str = "NEUTRAL",
    aircraft_category: str = "jet"
) -> str:
    """Sahne metni ve promptundan sahnenin iklimine, uçak tipine ve aksiyonuna en uygun Pixabay video sorgusunu çıkarır."""
    text = " ".join([
        str(scene_data.get("image_prompt", "")),
        str(scene_data.get("narration", "")),
        str(scene_data.get("emotion", ""))
    ]).lower()

    # 1. Denize Zorunlu İniş / Suya Çakılma (Ditching / Water Crash)
    if any(k in text for k in ["ditching", "ditch", "water landing", "water impact", "mediterranean", "ocean", "sea waves", "suya iniş", "deniz"]):
        if any(r in text for r in ["rescue", "diver", "helicopter", "boat", "kurtarma"]):
            return "helicopter rescue"
        return "ocean waves aerial"

    # 2. Turboprop / Bölgesel Pervaneli Yolcu Uçakları (ATR 72, Saab 340, Dash 8 vb.)
    # ASLA tek motorlu Cessna veya genel gece şehir klibi aramaması için en başta ele alınır!
    if aircraft_category == "turboprop":
        if any(k in text for k in ["propeller", "feather", "flameout", "pervane", "engine failure", "motor"]):
            return "turboprop propeller"
        elif any(k in text for k in ["cockpit", "lövye", "pilot", "instrument", "gauge", "panel", "overhead", "turnbuckle", "cable", "trim", "control", "horizon"]):
            return "cockpit instruments airplane"
        elif any(k in text for k in ["takeoff", "departure", "kalkış", "tırmanış", "climb"]):
            return "turboprop takeoff"
        elif any(k in text for k in ["runway", "taxi", "landing", "pist", "iniş", "commuter"]):
            return "airport commuter plane"
        turboprop_defaults = ["turboprop flight", "propeller aircraft", "cockpit instruments airplane", "airport commuter plane"]
        return turboprop_defaults[scene_idx % len(turboprop_defaults)]

    # 3. Yoğun Sis / Görüş Sıfır (FOG)
    if climate == "FOG":
        if any(k in text for k in ["cockpit", "instrument", "gauge", "horizon", "pilot", "lövye"]):
            return "cockpit instruments airplane"
        elif any(k in text for k in ["takeoff", "runway", "departure", "kalkış", "pist"]):
            return "airport runway"
        elif any(k in text for k in ["cloud", "overcast", "weather", "sis", "bulut"]):
            return "thick clouds aerial"
        return "airport runway"

    # 4. Gece Uçuşları (Sadece iklim açıkça NIGHT ise)
    if climate == "NIGHT":
        if any(k in text for k in ["lightning", "thunderstorm", "fırtına", "şimşek"]):
            return "thunderstorm night clouds"
        elif any(k in text for k in ["cockpit", "lövye", "pilot", "yoke", "stick", "panel", "instrument", "gauge", "horizon", "bank"]):
            return "cockpit instruments night"
        elif any(k in text for k in ["takeoff", "landing", "runway", "approach", "pist", "kalkış", "iniş"]) and scene_idx <= 2:
            return "runway lights night"
        night_defaults = ["cockpit instruments night", "dark clouds night flight", "runway lights night"]
        return night_defaults[scene_idx % len(night_defaults)]

    # 4. Kış / Kar Şartları (Jetler için)
    if climate == "WINTER":
        if any(k in text for k in ["de-icing", "deicing", "glycol", "buz çözme"]):
            return "winter airport"
        elif any(k in text for k in ["blizzard", "snowfall", "snowstorm", "kar fırtınası", "tipi"]):
            return "blizzard"
        elif any(k in text for k in ["traffic", "bridge", "highway", "commuter", "köprü"]):
            return "winter traffic"
        elif any(k in text for k in ["river", "potomac", "frozen river", "nehir"]):
            return "frozen river ice"
        elif any(k in text for k in ["rescue", "helicopter", "helikopter"]):
            return "helicopter rescue"
        elif any(k in text for k in ["glide", "altimeter", "gauge", "dial", "instrument", "panel", "epr", "probe", "sensör", "cockpit", "lövye", "pilot"]):
            return "cockpit airplane"
        elif any(k in text for k in ["takeoff", "departure", "runway", "kalkış", "pist"]):
            return "airport runway"
        winter_defaults = ["blizzard", "cockpit airplane", "winter airport", "airport runway"]
        return winter_defaults[scene_idx % len(winter_defaults)]

    # 5. Fırtına / Yağmur
    if climate == "STORMY":
        if any(k in text for k in ["lightning", "thunderstorm", "fırtına", "şimşek"]):
            return "thunderstorm night clouds"
        elif any(k in text for k in ["rain", "torrential", "yağmur"]):
            return "airport rain"
        return "thunderstorm night clouds"

    if climate == "FOG":
        return "airport runway"

    # 6. Standart Gündüz Jet Uçuş Sorguları (Kesinlikle gece klibi YOK!)
    if any(k in text for k in ["pvd", "calculate", "altimeter", "gauge", "dial", "instrument", "panel", "steam gauge", "gösterge", "ibrel"]):
        return "cockpit airplane"
    elif any(k in text for k in ["taxi", "taxiway", "centerline", "green light", "taksi"]):
        return "airport runway"
    elif any(k in text for k in ["cockpit", "lövye", "pilot", "flight deck", "control wheel"]):
        return "cockpit airplane"
    elif any(k in text for k in ["route", "map", "radar", "atc", "tower", "radio", "frequency", "telsiz", "controller", "kule"]):
        return "air traffic control radar"
    elif any(k in text for k in ["cloud", "weather", "turbulence", "bulut"]):
        return "airplane flying in clouds"
    elif any(k in text for k in ["landing", "runway", "touchdown", "approach", "pist", "iniş"]):
        return "airport runway"
    elif any(k in text for k in ["takeoff", "departure", "kalkış", "tırmanış"]):
        return "airport runway"
    
    defaults = [
        "cockpit airplane",
        "airplane flying in clouds",
        "airport runway",
        "air traffic control radar"
    ]
    return defaults[scene_idx % len(defaults)]


def _extract_cvr_dialogue(meta: Dict[str, Any], scene_data: Dict[str, Any], scene_idx: int, progress: float) -> Optional[Tuple[str, str]]:
    """
    Kokpit CVR konuşma balonları için KESİNLİKLE 3. şahıs dış ses (narrator) metnini KULLANMAZ.
    Sahnede gerçek pilotlar arası CRM diyaloğu veya meta verilerindeki telsiz kayıtlarını döner.
    Uçak çakıldıktan veya can kaybı açıklandıktan sonra (progress >= 0.65) KESİNLİKLE None döner!
    """
    narration_text = (scene_data.get("narration") or "").strip()
    prompt_text = (scene_data.get("image_prompt") or "").strip()
    comb = f"{narration_text} {prompt_text}".lower()

    # Kaza sonrası veya can kaybı/enkaz anlatımında CVR sahnesi AÇILAMAZ
    post_crash_words = [
        "crash", "impact", "lost their lives", "lose their lives", "hayatını", "öldü",
        "çakıldı", "paramparça", "wreckage", "krater", "crater", "died", "casualties",
        "victim", "kaza kırım", "bfu", "ntsb", "aaib", "ciaiac", "atsb", "investigation",
        "soruşturma", "bulgular", "probable cause"
    ]
    if progress >= 0.65 or any(w in comb for w in post_crash_words):
        return None

    # Meta verisinde kayıtlı CVR diyalog setleri var mı?
    meta_dialogues = meta.get("cvr_dialogues") or []
    if meta_dialogues and isinstance(meta_dialogues, list):
        if progress < 0.35 and len(meta_dialogues) >= 1:
            return meta_dialogues[0]
        elif progress < 0.52 and len(meta_dialogues) >= 2:
            return meta_dialogues[1]
        elif len(meta_dialogues) >= 3:
            return meta_dialogues[min(len(meta_dialogues) - 1, scene_idx % len(meta_dialogues))]
        else:
            return meta_dialogues[scene_idx % len(meta_dialogues)]

    # Meta verisi yoksa uçuş fazına göre otantik ve profesyonel kokpit telsiz replikleri
    if progress < 0.35:
        cap_q = "Climb thrust set, passing 2,500 feet. Following departure."
        fo_q = "Airspeed alive, positive climb rate. Instruments checked."
    elif progress < 0.52:
        cap_q = "Check attitude! Why is the attitude indicator rolling?"
        fo_q = "Bank angle! Check horizon, wings level! Level off!"
    else:
        cap_q = "Full power! Level the wings! Controls are heavy!"
        fo_q = "PULL UP! TERRAIN AHEAD! STICK SHAKER ACTIVE!"

    return cap_q, fo_q


def _extract_atc_dialogue(meta: Dict[str, Any], scene_data: Dict[str, Any], scene_idx: int, progress: float) -> Optional[str]:
    """
    Hava Trafik Kontrolörü (ATC) konuşma balonu için dış ses anlatıcı metni yerine otantik telsiz çağrısı döner.
    """
    fl_name = meta.get("flight_name", "Flight")
    atc_dialogues = meta.get("atc_dialogues") or []
    if atc_dialogues and isinstance(atc_dialogues, list):
        return atc_dialogues[scene_idx % len(atc_dialogues)]

    if progress < 0.35:
        return f"{fl_name}, radar contact. Climb and maintain assigned flight level."
    elif progress < 0.55:
        return f"{fl_name}, verify heading. Radar indicates right turn!"
    else:
        return f"{fl_name}, radar contact lost! Turn immediately! Do you read?"


def get_aviation_scene_media(
    scene_idx: int,
    total_scenes: int,
    topic: str,
    scene_data: Dict[str, Any],
    work_dir: Path,
    target_w: int = 1920,
    target_h: int = 1080,
    target_dur: float = 5.0,
    session_used: Optional[set] = None,
    metadata: Optional[Dict[str, Any]] = None,
    all_scenes: Optional[List[Dict[str, Any]]] = None
) -> Optional[str]:
    """
    Havacılık sahnesi için en ideal telifsiz medyayı temin eder:
    - Olay Meta Verileri: Uçak, havayolu ve kaza mahalli %100 senkronize edilir.
    - İklim & Gece Uyumu: Gece uçuşlarında gündüz stokları KESİNLİKLE yasaklanır.
    - Uçak Tipi Kilidi: Turboprop uçaklara asla jet kanatları sızamaz.
    - Havayolu İzolasyonu: Sadece hedeflenen havayolu kullanılır, başka havayolları elenir.
    - Enkaz & Kaza Kırımı: Gerçek kaza mahalli arşivleri çekilir, donanma/savaş gemileri engellenir.
    """
    used = session_used if session_used is not None else set()
    work_dir = Path(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    dest_vid = str(work_dir / f"scene_{scene_idx}.mp4")
    dest_img = str(work_dir / f"scene_{scene_idx}.jpg")

    # Olay Meta Verilerini Al
    meta = metadata
    if not meta:
        meta = extract_incident_metadata(topic, scenes=all_scenes or [scene_data])

    climate = meta.get("climate", "NEUTRAL")
    aircraft_category = meta.get("aircraft_category", "jet")
    progress = scene_idx / max(1, total_scenes - 1)

    narration_text = (scene_data.get("narration") or "").strip()
    prompt_text = (scene_data.get("image_prompt") or "").strip()
    comb_text = f"{narration_text} {prompt_text} {scene_data.get('emotion', '')}".lower()
    scene_mood = detect_scene_tension_mood(comb_text)
    target_aircraft = str(meta.get("aircraft_type") or meta.get("aircraft_short") or meta.get("flight_name", ""))

    DISASTER_TERMS = {
        "crash", "wreckage", "wreck", "debris", "salvage", "recovery", "crane",
        "bodies", "body", "diver", "divers", "destruction", "destroyed",
        "fire", "burning", "burnt", "ruin", "ruins", "aftermath",
        "memorial", "casualty", "victim", "victims", "remains", "submerged", "disaster"
    }

    # ── ÖZEL İNFOGRAFİK VE TAKTİK ANİMASYON ENJEKSİYONU ──
    # 2.5D Animasyonlu Radar Rota & Telemetri Videosu
    animated_radar_file = work_dir / "flight_path_animated.mp4"
    has_route_keyword = any(k in comb_text for k in [
        "departure", "takeoff", "climb", "route", "heading", "radar", "sharm el sheikh",
        "turn", "waypoint", "altitude", "altitude loss", "flight path", "rota", "irtifa", "tırmanış", "kalkış"
    ])
    if (0.15 <= progress <= 0.65 or has_route_keyword) and animated_radar_file.exists():
        if "animated_radar_injected" not in used:
            used.add("animated_radar_injected")
            used.add(f"type_{scene_idx}:vid")
            print(f"[AVIATION-FETCHER] 🗺️🎬 Sahne {scene_idx} için 2.5D ANİMASYONLU TAKTİK RADAR VİDEOSU enjekte edildi: {animated_radar_file.name}")
            return str(animated_radar_file)

    # Faz 2 Ortası (~%30 - %45): Kokpit Gösterge Telemetri Grafiği
    telemetry_gauge_file = work_dir / "flight_telemetry_gauge.png"
    if 0.30 <= progress <= 0.45 and telemetry_gauge_file.exists():
        if "gauge_injected" not in used:
            used.add("gauge_injected")
            used.add(f"type_{scene_idx}:telemetry")
            print(f"[AVIATION-FETCHER] 📊 Sahne {scene_idx} için KOKPİT GÖSTERGE TELEMETRİSİ enjekte edildi: {telemetry_gauge_file.name}")
            return str(telemetry_gauge_file)

    # Faz 3 Ortası (~%60 - %75): Taktiksel Radar Rota & İrtifa Haritası
    trajectory_map_file = work_dir / "flight_trajectory_map.png"
    if 0.60 <= progress <= 0.75 and trajectory_map_file.exists():
        if "map_injected" not in used:
            used.add("map_injected")
            used.add(f"type_{scene_idx}:telemetry")
            print(f"[AVIATION-FETCHER] 🗺️ Sahne {scene_idx} için TAKTİKSEL RADAR ROTA HARİTASI enjekte edildi: {trajectory_map_file.name}")
            return str(trajectory_map_file)

    # Ritim ve Hareket Kuralı: Son 2 sahne ardışık statik görsel olduysa veya Faz 2 tekil sahnelerindeysek videoyu öne al
    prefer_video = (
        (scene_idx >= 2 and f"type_{scene_idx-1}:img" in used and f"type_{scene_idx-2}:img" in used)
        or (0.25 <= progress < 0.60 and scene_idx % 2 == 1)
    )

    def _try_fetch_video() -> Optional[str]:
        # 1. Kaza ve Felaket Anı Koruma Kalkanı:
        # Pixabay'de gerçek kaza/enkaz/facia videosu bulunmaz.
        # Bu aşamada asla rastgele güneşli bulut veya pist klibi aranmaz!
        if scene_mood == "DISASTER":
            print(f"[AVIATION-FETCHER] 🛡️ Sahne {scene_idx} FELAKET/KAZA anı (Tansiyon: DISASTER). Sakin genel stok video araması durduruldu.")
            return None

        video_query = classify_scene_aviation_query(scene_data, scene_idx, total_scenes, climate=climate, aircraft_category=aircraft_category)
        print(f"[AVIATION-FETCHER] 🎬 Sahne {scene_idx} için Pixabay Video aranıyor: '{video_query}' (İklim: {climate}, Model: {target_aircraft[:25]}, Tansiyon: {scene_mood})...")
        vid_hit = search_pixabay_video(
            video_query, 
            exclude_ids=used, 
            min_duration=target_dur, 
            climate=climate, 
            aircraft_category=aircraft_category,
            target_aircraft=target_aircraft,
            scene_mood=scene_mood
        )
        if not vid_hit and scene_mood != "HIGH_TENSION":
            if climate == "NIGHT":
                fallback_query = "cockpit night flight"
            elif aircraft_category == "turboprop":
                fallback_query = "turboprop flight"
            elif climate == "WINTER":
                fallback_query = "blizzard"
            else:
                fallback_query = "cockpit airplane"
            vid_hit = search_pixabay_video(
                fallback_query, 
                exclude_ids=used, 
                min_duration=target_dur, 
                climate=climate, 
                aircraft_category=aircraft_category,
                target_aircraft=target_aircraft,
                scene_mood=scene_mood
            )
        if vid_hit:
            vid_id = vid_hit["id"]
            vid_url = vid_hit["url"]
            print(f"[AVIATION-FETCHER] 📥 Pixabay Video indiriliyor (ID: {vid_id}, Süre: {vid_hit.get('duration')}s)...")
            if download_and_format_video(vid_url, dest_vid, target_w, target_h, target_dur):
                # ── VISION QA GUARD DENETİMİ ──
                ok, reason = validate_aviation_media(dest_vid, metadata=meta, scene_data=scene_data, scene_idx=scene_idx)
                if not ok:
                    print(f"[VISION-QA-GUARD] ⛔ Pixabay Video reddedildi: {reason}")
                    try:
                        os.remove(dest_vid)
                    except Exception:
                        pass
                    return None
                used.add(vid_id)
                used.add(f"type_{scene_idx}:vid")
                print(f"[AVIATION-FETCHER] ✅ Sahne {scene_idx} için 1080p video klip hazırlandı: {dest_vid}")
                return dest_vid
        return None

    def _try_fetch_wikimedia() -> Optional[str]:
        candidate_queries = []
        prohibited_airlines = meta.get("prohibited_airlines", [])

        if progress < 0.25:
            for q in meta.get("wiki_clean_queries", []):
                candidate_queries.append(q)
        elif progress < 0.55:
            candidate_queries.append(f"{meta.get('aircraft_type')} cockpit")
            candidate_queries.append(f"{meta.get('aircraft_short')} cockpit")
            candidate_queries.append(f"{meta.get('aircraft_type')} flight deck")
            if progress < 0.35:
                for q in meta.get("wiki_clean_queries", []):
                    candidate_queries.append(q)
        elif progress < 0.65:
            candidate_queries.append(f"{meta.get('flight_name')} diagram")
            candidate_queries.append(f"{meta.get('aircraft_short')} diagram")
            candidate_queries.append(f"{meta.get('flight_name')} flight path")
            candidate_queries.append(f"{meta.get('flight_name')} radar")
        else:
            # Kaza Mahalli, Enkaz, Tahkikat & Resmi Soruşturma Raporu
            for cq in meta.get("wiki_crash_queries", []):
                candidate_queries.append(cq)
            candidate_queries.append(f"{meta.get('flight_name')} wreckage")
            candidate_queries.append(f"{meta.get('flight_name')} crash")
            candidate_queries.append(f"{meta.get('flight_name')} investigation")
            candidate_queries.append(f"{meta.get('flight_name')} report")

        if candidate_queries:
            for wq in candidate_queries:
                print(f"[AVIATION-FETCHER] 🏛️ Sahne {scene_idx} için Wikimedia aranıyor: '{wq}' (Faz: {progress:.2f}, İklim: {climate}, Tip: {aircraft_category})...")
                wiki_hits = search_wikimedia_commons(wq, limit=8, prohibited_terms=prohibited_airlines)
                for hit in wiki_hits:
                    hit_url = hit["url"]
                    if hit_url in used:
                        continue
                    hit_title = hit.get("title", "").lower()

                    # Konu / Seri fotoğraf tekrarı koruması (Aynı albümden en fazla 2 fotoğraf)
                    subj_key = _get_subject_key(hit_title)
                    subj_count = sum(1 for item in used if isinstance(item, str) and item.startswith(f"subj:{subj_key}:"))
                    if subj_count >= 2:
                        print(f"[AVIATION-FETCHER] ⏭️ Benzer arşiv konusu zaten 2 kez kullanıldı ('{subj_key}'), çeşitlilik için atlanıyor.")
                        continue

                    # Erken aşamalarda kaza enkazı göstermeyi engelle
                    if progress < 0.60 and any(dt in hit_title for dt in DISASTER_TERMS):
                        continue

                    if download_and_format_image(hit_url, dest_img, target_w, target_h):
                        # ── VISION QA GUARD DENETİMİ ──
                        ok, reason = validate_aviation_media(dest_img, metadata=meta, scene_data=scene_data, scene_idx=scene_idx)
                        if not ok:
                            print(f"[VISION-QA-GUARD] ⛔ Wikimedia görseli reddedildi: {reason}")
                            try:
                                os.remove(dest_img)
                            except Exception:
                                pass
                            continue
                        used.add(hit_url)
                        used.add(f"subj:{subj_key}:{subj_count}")
                        used.add(f"type_{scene_idx}:img")
                        print(f"[AVIATION-FETCHER] ✅ Wikimedia'dan doğrulanmış tarihi arşiv görseli temin edildi: {hit.get('title')}")
                        return dest_img
        return None

    # ── STRATEJİ 0: Kokpit İçi CVR, Telsiz & Acil Durum Çöp Adam Canlandırması ──
    narration_text = (scene_data.get("narration") or "").strip()
    prompt_text = (scene_data.get("image_prompt") or "").strip()
    comb_text = f"{narration_text} {prompt_text}".lower()

    # Kaza sonrası güvenlik bariyeri: Uçak çakıldıktan veya can kayıpları açıklandıktan sonra ASLA kokpit CVR veya uçuş içi telsiz açılmaz!
    is_post_crash = (progress >= 0.65) or any(k in comb_text for k in [
        "crash", "impact", "lost their lives", "lose their lives", "hayatını", "öldü",
        "çakıldı", "paramparça", "wreckage", "krater", "crater", "died", "casualties",
        "victim", "kaza kırım", "bfu", "ntsb", "aaib", "ciaiac", "atsb", "investigation",
        "soruşturma", "bulgular", "probable cause"
    ])

    has_cvr_dialogue = (not is_post_crash) and any(k in comb_text for k in [
        "cvr", "bank angle", "pull up", "graveyard spiral", "somatogravic", "disorientation",
        "i have control", "look at the", "ne oluyor", "yatış", "lövyeye", "ufka bak",
        "overbank", "clacker", "overspeed", "stall", "whoop whoop", "sink rate"
    ])
    has_atc = (progress < 0.70) and any(k in comb_text for k in [
        "atc", "tower", "radar contact", "transponder", "squawk", "telsiz", "cairo radar",
        "lost contact", "mayday mayday", "beni duyuyor musunuz"
    ])
    has_investigation = (progress >= 0.60) and any(k in comb_text for k in [
        "investigation", "ntsb", "bea", "bfu", "aaib", "ciaiac", "atsb", "black box",
        "kara kutu", "flight data recorder", "fdr", "probable cause", "bulgular",
        "soruşturma", "kaza kırım", "rapor", "report", "kazanın nedeni", "resmi rapor"
    ])

    # CVR canlandırması
    cvr_dialogue = _extract_cvr_dialogue(meta, scene_data, scene_idx, progress)
    cvr_usage_count = sum(1 for item in used if isinstance(item, str) and item.startswith("cvr_anim_injected"))
    if has_cvr_dialogue and cvr_dialogue and cvr_usage_count < 2 and f"type_{scene_idx-1}:cvr" not in used and f"type_{scene_idx-2}:cvr" not in used:
        try:
            cap_quote, fo_quote = cvr_dialogue
            cvr_vid = str(dest_vid).replace(".mp4", "_cvr_anim.mp4")
            fl_name = meta.get("flight_name", "EMERGENCY FLIGHT")
            if generate_animated_cvr_video:
                cvr_res = generate_animated_cvr_video(
                    flight_name=fl_name,
                    situation_title="COCKPIT EMERGENCY // CRITICAL RECONSTRUCTION",
                    captain_quote=cap_quote,
                    fo_quote=fo_quote,
                    bank_angle=35.0 if "32" in comb_text or "flaps" in comb_text else 48.0,
                    sink_rate="-2,800 FT/MIN",
                    duration=target_dur,
                    output_path=cvr_vid
                )
                used.add(f"cvr_anim_injected_{cvr_usage_count+1}")
                used.add(f"type_{scene_idx}:cvr")
                print(f"[AVIATION-FETCHER] 🎭 Sahne {scene_idx} için HAREKETLİ 2D ÇÖP ADAM KOKPİT CVR VİDEOSU üretildi: {cvr_vid}")
                return cvr_vid
            elif render_cockpit_cvr_reconstruction:
                cvr_img = str(dest_img).replace(".jpg", "_cvr.png")
                render_cockpit_cvr_reconstruction(
                    flight_name=fl_name,
                    captain_quote=cap_quote,
                    fo_quote=fo_quote,
                    bank_angle=45.0,
                    output_path=cvr_img
                )
                used.add(f"cvr_anim_injected_{cvr_usage_count+1}")
                used.add(f"type_{scene_idx}:cvr")
                return cvr_img
        except Exception as e:
            print(f"[AVIATION-FETCHER] CVR sahne üretim hatası: {e}")

    # ATC canlandırması
    atc_usage_count = sum(1 for item in used if isinstance(item, str) and item.startswith("atc_anim_injected"))
    if has_atc and atc_usage_count < 2 and f"type_{scene_idx-1}:atc" not in used:
        try:
            atc_call_text = _extract_atc_dialogue(meta, scene_data, scene_idx, progress)
            atc_vid = str(dest_vid).replace(".mp4", "_atc_anim.mp4")
            fl_name = meta.get("flight_name", "EMERGENCY FLIGHT")
            atc_st = meta.get("atc_station", "AIRPORT TOWER // DEPARTURE RADAR")
            if generate_animated_atc_video:
                atc_res = generate_animated_atc_video(
                    flight_name=fl_name,
                    atc_station=atc_st,
                    atc_call=atc_call_text,
                    altitude_reported="LAST KNOWN: 40 FT -> RAPID DESCENT",
                    duration=target_dur,
                    output_path=atc_vid
                )
                used.add(f"atc_anim_injected_{atc_usage_count+1}")
                used.add(f"type_{scene_idx}:atc")
                print(f"[AVIATION-FETCHER] 📡 Sahne {scene_idx} için HAREKETLİ 2D ÇÖP ADAM ATC KULE VİDEOSU üretildi ({atc_st}): {atc_vid}")
                return atc_vid
            elif render_atc_tower_reconstruction:
                atc_img = str(dest_img).replace(".jpg", "_atc.png")
                render_atc_tower_reconstruction(
                    flight_name=fl_name,
                    atc_station=atc_st,
                    atc_call=atc_call_text,
                    output_path=atc_img
                )
                used.add(f"atc_anim_injected_{atc_usage_count+1}")
                used.add(f"type_{scene_idx}:atc")
                return atc_img
        except Exception as e:
            print(f"[AVIATION-FETCHER] ATC sahne üretim hatası: {e}")

    # İnceleme / Soruşturma canlandırması (Kaza sonrası ve resmi rapor fazı)
    inv_usage_count = sum(1 for item in used if isinstance(item, str) and item.startswith("inv_anim_injected"))
    if has_investigation and inv_usage_count < 2 and f"type_{scene_idx-1}:investigation" not in used:
        try:
            inv_vid = str(dest_vid).replace(".mp4", "_inv_anim.mp4")
            fl_name = meta.get("flight_name", "EMERGENCY FLIGHT")
            agency_name = meta.get("investigating_agency", "NATIONAL TRANSPORTATION SAFETY BOARD (NTSB)")
            cause_text = meta.get("probable_cause", "Aircraft control loss during critical departure phase.")
            factors = meta.get("critical_factors")
            if generate_animated_investigation_video:
                inv_res = generate_animated_investigation_video(
                    flight_name=fl_name,
                    investigating_agency=agency_name,
                    primary_finding=cause_text,
                    critical_factors=factors,
                    duration=target_dur,
                    output_path=inv_vid
                )
                used.add(f"inv_anim_injected_{inv_usage_count+1}")
                used.add(f"type_{scene_idx}:investigation")
                print(f"[AVIATION-FETCHER] 🔍 Sahne {scene_idx} için HAREKETLİ 2D ÇÖP ADAM RESMİ İNCELEME VİDEOSU üretildi ({agency_name[:25]}): {inv_vid}")
                return inv_vid
            elif render_investigation_reconstruction:
                inv_img = str(dest_img).replace(".jpg", "_inv.png")
                render_investigation_reconstruction(
                    flight_name=fl_name,
                    investigating_agency=agency_name,
                    primary_finding=cause_text,
                    critical_factors=factors,
                    output_path=inv_img
                )
                used.add(f"inv_anim_injected_{inv_usage_count+1}")
                used.add(f"type_{scene_idx}:investigation")
                return inv_img
        except Exception as e:
            print(f"[AVIATION-FETCHER] İnceleme sahne üretim hatası: {e}")

    # Eğer prefer_video aktifse Pixabay Video önce denenir
    if prefer_video:
        print(f"[AVIATION-FETCHER] ⚡ Ritim dengesi: Sahne {scene_idx} için dinamik video klibi önceliklendiriliyor.")
        v_res = _try_fetch_video()
        if v_res:
            return v_res

    # ── STRATEJİ 1: Gerçek Tarihi Arşiv Görselleri (Wikimedia Commons) ──
    w_res = _try_fetch_wikimedia()
    if w_res:
        return w_res

    # ── STRATEJİ 2: Dinamik Sahne B-Roll Video Klibi (Pixabay Video API) ──
    if not prefer_video:
        v_res = _try_fetch_video()
        if v_res:
            return v_res

    # ── KRİTİK GÜVENLİK: Kaza / Dalış Fazında (progress >= 0.60) ASLA huzurlu gündüz fotoğrafları çıkmasın ──
    # Kadran ve harita TÜM VİDEO BOYUNCA EN FAZLA 1 KEZ KULLANILIR! (Tekrar YASAKTIR)
    if progress >= 0.60:
        if telemetry_gauge_file.exists() and "gauge_injected" not in used and str(telemetry_gauge_file) not in used and f"type_{scene_idx-1}:telemetry" not in used:
            print(f"[AVIATION-FETCHER] 🛡️ Kaza/dalış anı için KOKPİT GÖSTERGE TELEMETRİSİ kullanıldı.")
            used.add("gauge_injected")
            used.add(str(telemetry_gauge_file))
            used.add(f"type_{scene_idx}:telemetry")
            return str(telemetry_gauge_file)
        if trajectory_map_file.exists() and "map_injected" not in used and str(trajectory_map_file) not in used and f"type_{scene_idx-1}:telemetry" not in used:
            print(f"[AVIATION-FETCHER] 🛡️ Kaza/dalış anı için TAKTİKSEL RADAR HARİTASI kullanıldı.")
            used.add("map_injected")
            used.add(str(trajectory_map_file))
            used.add(f"type_{scene_idx}:telemetry")
            return str(trajectory_map_file)

    # ── STRATEJİ 3: Statik Fotoğraf Fallback (Pixabay Fotoğraf) ──
    # Felaket ve yüksek tansiyon anında genel sakin/güneşli stok fotoğraf aramayı engelle
    if scene_mood in ("DISASTER", "HIGH_TENSION"):
        print(f"[AVIATION-FETCHER] 🛡️ Sahne {scene_idx} (Tansiyon: {scene_mood}) için genel sakin stok fotoğraf atlandı, doğrudan taktik/resmi canlandırmaya yönlendiriliyor.")
    else:
        video_query = classify_scene_aviation_query(scene_data, scene_idx, total_scenes, climate=climate, aircraft_category=aircraft_category)
        print(f"[AVIATION-FETCHER] 📷 Video bulunamadı, Pixabay Fotoğraf deneniyor: '{video_query}' (Model: {target_aircraft[:25]})...")
        photo_hit = search_pixabay_photo(
            video_query, 
            exclude_ids=used, 
            climate=climate, 
            aircraft_category=aircraft_category,
            target_aircraft=target_aircraft,
            scene_mood=scene_mood
        )
        if photo_hit:
            photo_id = photo_hit["id"]
            photo_url = photo_hit["url"]
            if download_and_format_image(photo_url, dest_img, target_w, target_h):
                ok, reason = validate_aviation_media(dest_img, metadata=meta, scene_data=scene_data, scene_idx=scene_idx)
                if not ok:
                    print(f"[VISION-QA-GUARD] ⛔ Pixabay Fotoğraf reddedildi: {reason}")
                    try:
                        os.remove(dest_img)
                    except Exception:
                        pass
                else:
                    used.add(photo_id)
                    used.add(f"type_{scene_idx}:img")
                    print(f"[AVIATION-FETCHER] ✅ Pixabay Fotoğraf temin edildi: {dest_img}")
                    return dest_img

    # ── STRATEJİ 4: Doğrulanmış Wikimedia Fallback ──
    if climate == "NIGHT":
        wiki_fallback = "cockpit night flight instruments"
    elif climate == "FOG":
        wiki_fallback = "airplane fog runway mist"
    elif aircraft_category == "turboprop":
        wiki_fallback = "turboprop airplane flight"
    elif climate == "WINTER":
        wiki_fallback = "airplane winter snow"
    else:
        wiki_fallback = "cockpit flight deck instruments"

    general_wiki_hits = search_wikimedia_commons(wiki_fallback, limit=5, prohibited_terms=meta.get("prohibited_airlines", []))
    for hit in general_wiki_hits:
        hit_url = hit["url"]
        if hit_url in used:
            continue
        if download_and_format_image(hit_url, dest_img, target_w, target_h):
            ok, reason = validate_aviation_media(dest_img, metadata=meta, scene_data=scene_data, scene_idx=scene_idx)
            if not ok:
                print(f"[VISION-QA-GUARD] ⛔ Wikimedia fallback görseli reddedildi: {reason}")
                try:
                    os.remove(dest_img)
                except Exception:
                    pass
                continue
            used.add(hit_url)
            used.add(f"type_{scene_idx}:img")
            print(f"[AVIATION-FETCHER] ✅ Wikimedia genel arşiv görseli temin edildi: {dest_img}")
            return dest_img

    # ── STRATEJİ 5: Son Güvenlik Ağı — Kesinlikle Tekrar Etmeyen Taktik Telemetri, İnceleme ve Canlandırma ──
    # 1. Henüz kullanılmamışsa Radar Haritası veya Telemetri Kadranı (Tekil kullanım)
    if animated_radar_file.exists() and "animated_radar_injected" not in used and str(animated_radar_file) not in used and f"type_{scene_idx-1}:animated_radar" not in used:
        print(f"[AVIATION-FETCHER] 🛡️ Güvenlik Ağı: 2.5D ANİMASYONLU TAKTİK RADAR VİDEOSU devreye alındı.")
        used.add("animated_radar_injected")
        used.add(str(animated_radar_file))
        used.add(f"type_{scene_idx}:animated_radar")
        return str(animated_radar_file)

    if telemetry_gauge_file.exists() and "gauge_injected" not in used and str(telemetry_gauge_file) not in used and f"type_{scene_idx-1}:telemetry" not in used:
        print(f"[AVIATION-FETCHER] 🛡️ Güvenlik Ağı: Doğrulanmış KOKPİT GÖSTERGE TELEMETRİSİ devreye alındı.")
        used.add("gauge_injected")
        used.add(str(telemetry_gauge_file))
        used.add(f"type_{scene_idx}:telemetry")
        return str(telemetry_gauge_file)

    if trajectory_map_file.exists() and "map_injected" not in used and str(trajectory_map_file) not in used and f"type_{scene_idx-1}:telemetry" not in used:
        print(f"[AVIATION-FETCHER] 🛡️ Güvenlik Ağı: Doğrulanmış TAKTİKSEL RADAR HARİTASI devreye alındı.")
        used.add("map_injected")
        used.add(str(trajectory_map_file))
        used.add(f"type_{scene_idx}:telemetry")
        return str(trajectory_map_file)

    # 2. Son 2 dakika (progress >= 0.60): Kaza kırım incelemesi ve kara kutu canlandırması
    if progress >= 0.60:
        inv_cnt = sum(1 for item in used if isinstance(item, str) and item.startswith("inv_anim_injected"))
        if generate_animated_investigation_video and inv_cnt < 2 and f"type_{scene_idx-1}:investigation" not in used:
            try:
                inv_vid = str(dest_vid).replace(".mp4", "_inv_fb.mp4")
                generate_animated_investigation_video(
                    flight_name=meta.get("flight_name", "EMERGENCY FLIGHT"),
                    investigating_agency=meta.get("investigating_agency", "AIRCRAFT ACCIDENT INVESTIGATION BUREAU"),
                    primary_finding=meta.get("probable_cause", "Official investigation finding on loss of control."),
                    critical_factors=meta.get("critical_factors"),
                    duration=target_dur,
                    output_path=inv_vid
                )
                used.add(f"inv_anim_injected_{inv_cnt+1}")
                used.add(f"type_{scene_idx}:investigation")
                print(f"[AVIATION-FETCHER] 🛡️ Güvenlik Ağı: HAREKETLİ RESMİ İNCELEME VİDEOSU devreye alındı: {inv_vid}")
                return inv_vid
            except Exception as e:
                print(f"[AVIATION-FETCHER] İnceleme video üretim hatası: {e}")

        if render_investigation_reconstruction and "inv_static_injected" not in used:
            try:
                inv_img = str(dest_img).replace(".jpg", "_inv_report.png")
                render_investigation_reconstruction(
                    flight_name=meta.get("flight_name", "EMERGENCY FLIGHT"),
                    investigating_agency=meta.get("investigating_agency", "AIRCRAFT ACCIDENT INVESTIGATION BUREAU"),
                    primary_finding=meta.get("probable_cause", "Loss of control due to sensory anomaly."),
                    critical_factors=meta.get("critical_factors"),
                    output_path=inv_img
                )
                used.add("inv_static_injected")
                used.add(f"type_{scene_idx}:investigation")
                print(f"[AVIATION-FETCHER] 🛡️ Güvenlik Ağı: RESMİ İNCELEME RAPOR DOSYASI devreye alındı: {inv_img}")
                return inv_img
            except Exception as e:
                print(f"[AVIATION-FETCHER] İnceleme rapor görsel hatası: {e}")

    # 3. Erken aşamalar (progress < 0.60): CVR Canlandırması (Kaza öncesi)
    elif progress < 0.60 and not is_post_crash:
        cvr_cnt = sum(1 for item in used if isinstance(item, str) and item.startswith("cvr_anim_injected"))
        cvr_dial = _extract_cvr_dialogue(meta, scene_data, scene_idx, progress)
        if cvr_dial and cvr_cnt < 2 and f"type_{scene_idx-1}:cvr" not in used:
            cap_q, fo_q = cvr_dial
            if generate_animated_cvr_video:
                try:
                    cvr_vid = str(dest_vid).replace(".mp4", "_cvr_fb.mp4")
                    generate_animated_cvr_video(
                        flight_name=meta.get("flight_name", "EMERGENCY FLIGHT"),
                        situation_title="COCKPIT INSTRUMENT ALERT // CRM CROSSCHECK",
                        captain_quote=cap_q,
                        fo_quote=fo_q,
                        bank_angle=35.0,
                        sink_rate="-1,500 FT/MIN",
                        duration=target_dur,
                        output_path=cvr_vid
                    )
                    used.add(f"cvr_anim_injected_{cvr_cnt+1}")
                    used.add(f"type_{scene_idx}:cvr")
                    print(f"[AVIATION-FETCHER] 🛡️ Güvenlik Ağı: ÇÖP ADAM KOKPİT CVR VİDEOSU devreye alındı: {cvr_vid}")
                    return cvr_vid
                except Exception:
                    pass

    print(f"[AVIATION-FETCHER] ⚠️ Sahne {scene_idx} için telifsiz medya bulunamadı.")
    return None
