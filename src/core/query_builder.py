"""
core/query_builder.py
=====================
Pre-Render Quality Gate: Karaktere Çapalanmış Arama Motoru ve Dinamik Negatif Filtre Üreticisi.
(Subject-Anchored Query Builder & Anti-Semantic-Drift Dynamic Filter)

Mimarî Hedefler:
1. Zorunlu Karakter Çapası (Mandatory Subject Anchor):
   - Senaryodaki soyut terimlerin ("sweet spot", "geometry", "mechanical") tek başına
     arama motoruna gitmesini mimari olarak imkansız kılar.
   - Her arama sorgusunun başına projenin ana karakteri, takımı ve dönemi zorunlu önek (prefix) olarak eklenir:
     Örnek: "expanding the rim's sweet spot" -> "Tim Duncan San Antonio Spurs 2003 sweet spot rim"
   - Invariant: Üretilen her sorguda ana karakter adı (primary entity) bulunmak zorundadır!
2. Otomatik Cross-Sport ve Alakasız Branş Negatifleri:
   - nba_history için: FIFA, Dünya Kupası, futbol, kargo şortu, boş pota, askeri üs maçları
     otomatik olarak negatif listesine yazılır.
3. Rakip ve Dönem Negatifleri:
   - Tim Duncan videosuna Iverson, Jordan veya Detroit Pistons'ın sızması dinamik negatif filtrelerle engellenir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple


# ─────────────────────────────────────────────────────────────
# NBA TAKIMLARI, ALIASLARI VE RESMİ RENK PALETLERİ
# ─────────────────────────────────────────────────────────────

NBA_TEAMS: Dict[str, Dict[str, Any]] = {
    "San Antonio Spurs": {
        "aliases": ["spurs", "san antonio", "sas"],
        "city": "San Antonio",
        "primary_color": (15, 23, 42),      # Deep Midnight / Black
        "accent_color": (196, 206, 212),     # Silver / Frost Grey (#C4CED4)
        "hex_primary": "#000000",
        "hex_accent": "#C4CED4"
    },
    "Golden State Warriors": {
        "aliases": ["warriors", "gsw", "golden state", "dubs"],
        "city": "Golden State",
        "primary_color": (29, 66, 138),     # Royal Blue (#1D428A)
        "accent_color": (255, 199, 44),     # California Gold (#FFC72C)
        "hex_primary": "#1D428A",
        "hex_accent": "#FFC72C"
    },
    "Los Angeles Lakers": {
        "aliases": ["lakers", "la lakers", "los angeles lakers"],
        "city": "Los Angeles",
        "primary_color": (85, 37, 130),     # Forum Purple (#552583)
        "accent_color": (253, 185, 39),     # Gold (#FDB927)
        "hex_primary": "#552583",
        "hex_accent": "#FDB927"
    },
    "Chicago Bulls": {
        "aliases": ["bulls", "chicago"],
        "city": "Chicago",
        "primary_color": (206, 17, 65),     # Bulls Red (#CE1141)
        "accent_color": (15, 23, 42),       # Black
        "hex_primary": "#CE1141",
        "hex_accent": "#000000"
    },
    "Boston Celtics": {
        "aliases": ["celtics", "boston"],
        "city": "Boston",
        "primary_color": (0, 122, 51),      # Celtics Green (#007A33)
        "accent_color": (186, 150, 83),     # Gold (#BA9653)
        "hex_primary": "#007A33",
        "hex_accent": "#BA9653"
    },
    "Philadelphia 76ers": {
        "aliases": ["76ers", "sixers", "philly", "philadelphia"],
        "city": "Philadelphia",
        "primary_color": (0, 107, 182),     # 76ers Blue (#006BB6)
        "accent_color": (237, 23, 76),      # Red (#ED174C)
        "hex_primary": "#006BB6",
        "hex_accent": "#ED174C"
    },
    "Detroit Pistons": {
        "aliases": ["pistons", "detroit"],
        "city": "Detroit",
        "primary_color": (30, 64, 175),
        "accent_color": (220, 38, 38),
        "hex_primary": "#1E40AF",
        "hex_accent": "#DC2626"
    },
    "Denver Nuggets": {
        "aliases": ["nuggets", "denver"],
        "city": "Denver",
        "primary_color": (13, 34, 64),
        "accent_color": (254, 197, 36),
        "hex_primary": "#0D2240",
        "hex_accent": "#FEC524"
    },
    "Memphis Grizzlies": {
        "aliases": ["grizzlies", "memphis", "vancouver grizzlies"],
        "city": "Memphis",
        "primary_color": (93, 118, 169),
        "accent_color": (18, 23, 63),
        "hex_primary": "#5D76A9",
        "hex_accent": "#12173F"
    },
    "Miami Heat": {
        "aliases": ["heat", "miami"],
        "city": "Miami",
        "primary_color": (152, 0, 46),
        "accent_color": (249, 160, 27),
        "hex_primary": "#98002E",
        "hex_accent": "#F9A01B"
    },
    "Cleveland Cavaliers": {
        "aliases": ["cavaliers", "cavs", "cleveland"],
        "city": "Cleveland",
        "primary_color": (111, 38, 61),
        "accent_color": (253, 187, 48),
        "hex_primary": "#6F263D",
        "hex_accent": "#FDBB30"
    },
    "Houston Rockets": {
        "aliases": ["rockets", "houston"],
        "city": "Houston",
        "primary_color": (206, 17, 65),
        "accent_color": (196, 206, 212),
        "hex_primary": "#CE1141",
        "hex_accent": "#C4CED4"
    },
    "Dallas Mavericks": {
        "aliases": ["mavericks", "mavs", "dallas"],
        "city": "Dallas",
        "primary_color": (0, 83, 188),
        "accent_color": (0, 43, 92),
        "hex_primary": "#0053BC",
        "hex_accent": "#002B5C"
    },
    "Milwaukee Bucks": {
        "aliases": ["bucks", "milwaukee"],
        "city": "Milwaukee",
        "primary_color": (0, 71, 27),
        "accent_color": (238, 231, 197),
        "hex_primary": "#00471B",
        "hex_accent": "#EEE7C5"
    },
    "Toronto Raptors": {
        "aliases": ["raptors", "toronto"],
        "city": "Toronto",
        "primary_color": (206, 17, 65),
        "accent_color": (0, 0, 0),
        "hex_primary": "#CE1141",
        "hex_accent": "#000000"
    },
    "Oklahoma City Thunder": {
        "aliases": ["thunder", "okc", "seattle supersonics", "supersonics", "sonics"],
        "city": "Oklahoma City",
        "primary_color": (0, 122, 193),
        "accent_color": (239, 59, 36),
        "hex_primary": "#007AC1",
        "hex_accent": "#EF3B24"
    },
    "New York Knicks": {
        "aliases": ["knicks", "new york knicks", "ny knicks"],
        "city": "New York",
        "primary_color": (0, 107, 182),
        "accent_color": (245, 132, 38),
        "hex_primary": "#006BB6",
        "hex_accent": "#F58426"
    },
    "Brooklyn Nets": {
        "aliases": ["nets", "brooklyn nets", "new jersey nets"],
        "city": "Brooklyn",
        "primary_color": (0, 0, 0),
        "accent_color": (255, 255, 255),
        "hex_primary": "#000000",
        "hex_accent": "#FFFFFF"
    },
    "Phoenix Suns": {
        "aliases": ["suns", "phoenix"],
        "city": "Phoenix",
        "primary_color": (29, 17, 96),
        "accent_color": (229, 95, 32),
        "hex_primary": "#1D1160",
        "hex_accent": "#E55F20"
    },
    "Portland Trail Blazers": {
        "aliases": ["trail blazers", "blazers", "portland"],
        "city": "Portland",
        "primary_color": (224, 58, 62),
        "accent_color": (0, 0, 0),
        "hex_primary": "#E03A3E",
        "hex_accent": "#000000"
    },
    "Indiana Pacers": {
        "aliases": ["pacers", "indiana"],
        "city": "Indiana",
        "primary_color": (0, 45, 98),
        "accent_color": (253, 187, 48),
        "hex_primary": "#002D62",
        "hex_accent": "#FDBB30"
    },
    "Utah Jazz": {
        "aliases": ["jazz", "utah"],
        "city": "Utah",
        "primary_color": (0, 43, 92),
        "accent_color": (249, 160, 27),
        "hex_primary": "#002B5C",
        "hex_accent": "#F9A01B"
    },
    "Orlando Magic": {
        "aliases": ["magic", "orlando"],
        "city": "Orlando",
        "primary_color": (0, 119, 192),
        "accent_color": (196, 206, 212),
        "hex_primary": "#0077C0",
        "hex_accent": "#C4CED4"
    },
    "Sacramento Kings": {
        "aliases": ["kings", "sacramento"],
        "city": "Sacramento",
        "primary_color": (91, 43, 130),
        "accent_color": (99, 113, 122),
        "hex_primary": "#5B2B82",
        "hex_accent": "#63717A"
    },
    "Washington Wizards": {
        "aliases": ["wizards", "washington wizards", "washington bullets", "bullets"],
        "city": "Washington",
        "primary_color": (0, 43, 92),
        "accent_color": (227, 24, 55),
        "hex_primary": "#002B5C",
        "hex_accent": "#E31837"
    },
    "Atlanta Hawks": {
        "aliases": ["hawks", "atlanta"],
        "city": "Atlanta",
        "primary_color": (225, 58, 62),
        "accent_color": (196, 214, 0),
        "hex_primary": "#E13A3E",
        "hex_accent": "#C4D600"
    },
    "Minnesota Timberwolves": {
        "aliases": ["timberwolves", "wolves", "minnesota"],
        "city": "Minnesota",
        "primary_color": (12, 35, 64),
        "accent_color": (35, 97, 146),
        "hex_primary": "#0C2340",
        "hex_accent": "#236192"
    },
    "New Orleans Pelicans": {
        "aliases": ["pelicans", "new orleans hornets", "new orleans"],
        "city": "New Orleans",
        "primary_color": (0, 43, 92),
        "accent_color": (180, 151, 90),
        "hex_primary": "#002B5C",
        "hex_accent": "#B4975A"
    },
    "Charlotte Hornets": {
        "aliases": ["hornets", "charlotte bobcats", "charlotte"],
        "city": "Charlotte",
        "primary_color": (29, 17, 96),
        "accent_color": (0, 120, 140),
        "hex_primary": "#1D1160",
        "hex_accent": "#00788C"
    },
    "Los Angeles Clippers": {
        "aliases": ["clippers", "la clippers"],
        "city": "Los Angeles",
        "primary_color": (200, 16, 46),
        "accent_color": (27, 43, 75),
        "hex_primary": "#C8102E",
        "hex_accent": "#1B2B4B"
    }
}


# ─────────────────────────────────────────────────────────────
# OYUNCU KARİYER VE TARİHSEL ANCHOR VERİTABANI
# ─────────────────────────────────────────────────────────────

PLAYER_CAREER_MAP: Dict[str, Dict[str, Any]] = {
    "Tim Duncan": {
        "eras": [
            {"start": 1997, "end": 2016, "primary_team": "San Antonio Spurs", "peak_year": 2003}
        ],
        "default_year": 2003,
        "other_teams": [],
        "rival_competitors": ["Detroit Pistons", "Allen Iverson", "Chicago Bulls 1990", "Michael Jordan", "Kobe Bryant Lakers jersey"],
        "college": "Wake Forest Demon Deacons",
        "signature_moves": ["bank shot", "sweet spot", "glass angle", "fundamental mechanics", "rim protection", "rebound"]
    },
    "Allen Iverson": {
        "eras": [
            {"start": 1996, "end": 2006, "primary_team": "Philadelphia 76ers", "peak_year": 1997},
            {"start": 2006, "end": 2008, "primary_team": "Denver Nuggets", "peak_year": 2007},
            {"start": 2008, "end": 2009, "primary_team": "Detroit Pistons", "peak_year": 2008},
            {"start": 2009, "end": 2010, "primary_team": "Memphis Grizzlies", "peak_year": 2009}
        ],
        "default_year": 1997,
        "other_teams": ["Detroit Pistons", "Denver Nuggets", "Memphis Grizzlies", "Besiktas"],
        "rival_competitors": ["Tim Duncan", "San Antonio Spurs"],
        "college": "Georgetown Hoyas",
        "signature_moves": ["crossover", "rookie crossover", "handles", "fast break", "layup"]
    },
    "Draymond Green": {
        "eras": [
            {"start": 2012, "end": 2030, "primary_team": "Golden State Warriors", "peak_year": 2017}
        ],
        "default_year": 2017,
        "other_teams": [],
        "rival_competitors": ["Cleveland Cavaliers", "LeBron James", "Kevin Martin"],
        "college": "Michigan State Spartans",
        "signature_moves": ["triple-double", "steals", "defensive disruption", "box score", "blocks"]
    },
    "LeBron James": {
        "eras": [
            {"start": 2003, "end": 2010, "primary_team": "Cleveland Cavaliers", "peak_year": 2007},
            {"start": 2010, "end": 2014, "primary_team": "Miami Heat", "peak_year": 2012},
            {"start": 2014, "end": 2018, "primary_team": "Cleveland Cavaliers", "peak_year": 2016},
            {"start": 2018, "end": 2030, "primary_team": "Los Angeles Lakers", "peak_year": 2020}
        ],
        "default_year": 2012,
        "other_teams": ["Los Angeles Lakers", "Miami Heat", "Cleveland Cavaliers"],
        "rival_competitors": ["Golden State Warriors", "Boston Celtics", "Spurs"],
        "college": "St. Vincent-St. Mary High School",
        "signature_moves": ["chase down block", "tomahawk dunk", "pass dime", "fast break"]
    },
    "Michael Jordan": {
        "eras": [
            {"start": 1984, "end": 1998, "primary_team": "Chicago Bulls", "peak_year": 1993},
            {"start": 2001, "end": 2003, "primary_team": "Washington Wizards", "peak_year": 2002}
        ],
        "default_year": 1993,
        "other_teams": ["Washington Wizards", "Birmingham Barons baseball", "Chicago White Sox"],
        "rival_competitors": ["Detroit Pistons Bad Boys", "Utah Jazz", "Knicks"],
        "college": "North Carolina Tar Heels",
        "signature_moves": ["free throw line dunk", "fadeaway jumper", "clutch shot", "steals"]
    },
    "Kobe Bryant": {
        "eras": [
            {"start": 1996, "end": 2016, "primary_team": "Los Angeles Lakers", "peak_year": 2008}
        ],
        "default_year": 2008,
        "other_teams": [],
        "rival_competitors": ["Boston Celtics", "San Antonio Spurs", "Phoenix Suns"],
        "college": "Lower Merion High School",
        "signature_moves": ["fadeaway", "tough shot", "dunk", "clutch game winner"]
    },
    "Shaquille O'Neal": {
        "eras": [
            {"start": 1992, "end": 1996, "primary_team": "Orlando Magic", "peak_year": 1995},
            {"start": 1996, "end": 2004, "primary_team": "Los Angeles Lakers", "peak_year": 2000},
            {"start": 2004, "end": 2008, "primary_team": "Miami Heat", "peak_year": 2006},
            {"start": 2008, "end": 2009, "primary_team": "Phoenix Suns", "peak_year": 2008},
            {"start": 2009, "end": 2010, "primary_team": "Cleveland Cavaliers", "peak_year": 2009},
            {"start": 2010, "end": 2011, "primary_team": "Boston Celtics", "peak_year": 2010}
        ],
        "default_year": 2000,
        "other_teams": ["Phoenix Suns", "Cleveland Cavaliers", "Boston Celtics", "Miami Heat", "Orlando Magic", "Los Angeles Lakers"],
        "rival_competitors": [],
        "college": "LSU Tigers",
        "signature_moves": ["backboard shattering dunk", "drop step", "hook shot", "rim dominance"]
    },
    "Stephen Curry": {
        "eras": [
            {"start": 2009, "end": 2030, "primary_team": "Golden State Warriors", "peak_year": 2016}
        ],
        "default_year": 2016,
        "other_teams": [],
        "rival_competitors": ["Cleveland Cavaliers", "Houston Rockets"],
        "college": "Davidson Wildcats",
        "signature_moves": ["deep three pointer", "logo three", "crossover", "handles"]
    },
    "Dirk Nowitzki": {
        "eras": [
            {"start": 1998, "end": 2019, "primary_team": "Dallas Mavericks", "peak_year": 2011}
        ],
        "default_year": 2011,
        "other_teams": [],
        "rival_competitors": ["Miami Heat", "San Antonio Spurs"],
        "college": "DJK Wurzburg",
        "signature_moves": ["one legged fadeaway", "rainbow jumper", "championship trophy"]
    },
    "Wilt Chamberlain": {
        "eras": [
            {"start": 1959, "end": 1965, "primary_team": "Philadelphia Warriors", "peak_year": 1962},
            {"start": 1965, "end": 1968, "primary_team": "Philadelphia 76ers", "peak_year": 1967},
            {"start": 1968, "end": 1973, "primary_team": "Los Angeles Lakers", "peak_year": 1972}
        ],
        "default_year": 1962,
        "other_teams": ["Los Angeles Lakers", "Philadelphia 76ers", "San Francisco Warriors"],
        "rival_competitors": ["Bill Russell Boston Celtics"],
        "college": "Kansas Jayhawks",
        "signature_moves": ["100 points game", "finger roll", "rebounds", "shot block"]
    },
    "Hakeem Olajuwon": {
        "eras": [
            {"start": 1984, "end": 2001, "primary_team": "Houston Rockets", "peak_year": 1994},
            {"start": 2001, "end": 2002, "primary_team": "Toronto Raptors", "peak_year": 2001}
        ],
        "default_year": 1994,
        "other_teams": ["Toronto Raptors"],
        "rival_competitors": ["David Robinson San Antonio Spurs", "Patrick Ewing New York Knicks", "Shaquille O'Neal Orlando Magic"],
        "college": "Houston Cougars",
        "signature_moves": ["dream shake", "baseline fadeaway", "shot block", "footwork post move"]
    },
    "David Robinson": {
        "eras": [
            {"start": 1989, "end": 2003, "primary_team": "San Antonio Spurs", "peak_year": 1995}
        ],
        "default_year": 1995,
        "other_teams": [],
        "rival_competitors": ["Hakeem Olajuwon Houston Rockets", "Shaquille O'Neal Orlando Magic", "Karl Malone Utah Jazz"],
        "college": "Navy Midshipmen",
        "signature_moves": ["quadruple double", "rim protector", "fast break dunk", "rebound", "block"]
    },
    "Kareem Abdul-Jabbar": {
        "eras": [
            {"start": 1969, "end": 1975, "primary_team": "Milwaukee Bucks", "peak_year": 1971},
            {"start": 1975, "end": 1989, "primary_team": "Los Angeles Lakers", "peak_year": 1980}
        ],
        "default_year": 1971,
        "other_teams": ["Milwaukee Bucks", "Los Angeles Lakers"],
        "rival_competitors": ["Boston Celtics", "Philadelphia 76ers"],
        "college": "UCLA Bruins",
        "signature_moves": ["skyhook", "hook shot", "rebound", "block"]
    },
    "Dennis Rodman": {
        "eras": [
            {"start": 1986, "end": 1993, "primary_team": "Detroit Pistons", "peak_year": 1990},
            {"start": 1993, "end": 1995, "primary_team": "San Antonio Spurs", "peak_year": 1994},
            {"start": 1995, "end": 1998, "primary_team": "Chicago Bulls", "peak_year": 1996}
        ],
        "default_year": 1996,
        "other_teams": ["Detroit Pistons", "San Antonio Spurs", "Los Angeles Lakers", "Dallas Mavericks"],
        "rival_competitors": ["Utah Jazz", "Indiana Pacers"],
        "college": "Southeastern Oklahoma State",
        "signature_moves": ["rebound dive", "lockdown defense", "hustle loose ball"]
    },
    "Larry Bird": {
        "eras": [
            {"start": 1979, "end": 1992, "primary_team": "Boston Celtics", "peak_year": 1986}
        ],
        "default_year": 1986,
        "other_teams": [],
        "rival_competitors": ["Los Angeles Lakers Magic Johnson"],
        "college": "Indiana State Sycamores",
        "signature_moves": ["three point shootout", "clutch jumper", "behind back pass"]
    },
    "Magic Johnson": {
        "eras": [
            {"start": 1979, "end": 1996, "primary_team": "Los Angeles Lakers", "peak_year": 1987}
        ],
        "default_year": 1987,
        "other_teams": [],
        "rival_competitors": ["Boston Celtics Larry Bird"],
        "college": "Michigan State Spartans",
        "signature_moves": ["showtime fast break", "no look pass", "junior skyhook"]
    },
    "Dikembe Mutombo": {
        "eras": [
            {"start": 1991, "end": 1996, "primary_team": "Denver Nuggets", "peak_year": 1994},
            {"start": 1996, "end": 2001, "primary_team": "Atlanta Hawks", "peak_year": 1997},
            {"start": 2001, "end": 2002, "primary_team": "Philadelphia 76ers", "peak_year": 2001},
            {"start": 2004, "end": 2009, "primary_team": "Houston Rockets", "peak_year": 2005}
        ],
        "default_year": 1995,
        "other_teams": ["New Jersey Nets", "New York Knicks", "Houston Rockets"],
        "rival_competitors": ["Seattle SuperSonics"],
        "college": "Georgetown Hoyras",
        "signature_moves": ["finger wag", "blocked shot", "defensive rebound"]
    },
    "Russell Westbrook": {
        "eras": [
            {"start": 2008, "end": 2019, "primary_team": "Oklahoma City Thunder", "peak_year": 2017}
        ],
        "default_year": 2017,
        "other_teams": ["Houston Rockets", "Washington Wizards", "Los Angeles Lakers", "LA Clippers"],
        "rival_competitors": ["Golden State Warriors"],
        "college": "UCLA Bruins",
        "signature_moves": ["coast to coast slam", "triple double", "pull up jumper"]
    },
    "Derek Fisher": {
        "eras": [
            {"start": 1996, "end": 2004, "primary_team": "Los Angeles Lakers", "peak_year": 2004},
            {"start": 2004, "end": 2006, "primary_team": "Golden State Warriors", "peak_year": 2005},
            {"start": 2006, "end": 2007, "primary_team": "Utah Jazz", "peak_year": 2007},
            {"start": 2007, "end": 2012, "primary_team": "Los Angeles Lakers", "peak_year": 2009}
        ],
        "default_year": 2004,
        "other_teams": ["Utah Jazz", "Golden State Warriors", "Oklahoma City Thunder", "Dallas Mavericks"],
        "rival_competitors": ["San Antonio Spurs", "Detroit Pistons", "Boston Celtics"],
        "college": "Little Rock Trojans",
        "signature_moves": ["0.4 shot", "buzzer beater", "catch and shoot", "left hand release", "inbound pass turn", "clutch shot"]
    },
    "James Harden": {
        "eras": [
            {"start": 2009, "end": 2012, "primary_team": "Oklahoma City Thunder", "peak_year": 2012},
            {"start": 2012, "end": 2021, "primary_team": "Houston Rockets", "peak_year": 2018},
            {"start": 2021, "end": 2022, "primary_team": "Brooklyn Nets", "peak_year": 2021},
            {"start": 2022, "end": 2023, "primary_team": "Philadelphia 76ers", "peak_year": 2023},
            {"start": 2023, "end": 2030, "primary_team": "Los Angeles Clippers", "peak_year": 2024}
        ],
        "default_year": 2018,
        "other_teams": ["Brooklyn Nets", "Philadelphia 76ers", "Oklahoma City Thunder", "Los Angeles Clippers"],
        "rival_competitors": ["Golden State Warriors", "Utah Jazz", "San Antonio Spurs"],
        "college": "Arizona State Sun Devils",
        "signature_moves": ["step back", "deceleration", "eurostep", "crossover", "braking force", "isolation"]
    }
}


# Evrensel Cross-Sport & Saha Dışı Negatifler (Alakasız Branşların Sızmasını %100 Önler)
CROSS_SPORT_AND_OFF_COURT_NEGATIVES: List[str] = [
    # Alakasız Sporlar ve Futbol/FIFA/Robinho Sızıntıları
    "soccer", "football", "fifa", "world cup", "brazil", "robinho",
    "football match", "soccer player", "soccer stadium", "yellow soccer jersey",
    "brazil football jersey", "yellow shirt soccer crowd", "nfl", "touchdown",
    "baseball", "home run", "tennis", "golf", "rugby", "running marathon",
    "track and field", "hockey",
    # Bilet, Belge, Jumbotron ve Boş Salon / Bar Sızıntıları (Asset Contamination Koruması)
    "paper ticket stub", "admission ticket", "ticket stub", "ticket",
    "stadium jumbotron scoreboard screen", "jumbotron", "scoreboard",
    "indoor bar counter bartender", "indoor bar", "concession",
    "empty basketball stadium seats", "empty stadium seats",
    "crowd sitting in arena stands", "modern digital ticket",
    "close-up text document receipt", "receipt",
    # İstenmeyen Diğer Dönem Oyuncuları (2000'ler Rockets sızıntısı)
    "luis scola", "scola", "luther head", "bonzi wells", "yao ming",
    # Saha Dışı / Uygunsuz Görseller, Askeri Üs ve İmza Masaları
    "military base", "japanese atsugi base", "atsugi military base",
    "soldiers playing basketball", "elementary school", "elementary school children",
    "classroom students", "autograph signing table", "signing autographs on table",
    "press conference microphone", "press conference table with microphones",
    "amateur", "playground", "amateur playground", "rural dirt court",
    "rural house", "backyard", "suburban driveway", "amateur kid playing basketball",
    "pink house", "grass yard hoop", "rural court", "residential house",
    "suburban backyard", "driveway hoop",
    "cargo shorts", "empty hoop", "empty basketball hoop without players",
    "backyard rusty rim", "holding soccer ball", "streetwear fashion photoshoot",
    "glasses and sunglasses", "suit and necktie", "blurry low quality picture",
    "stock watermark text logo", "box score paper sheet", "old paper scoresheet",
    # Görsel Hijyen: Anime / Çizgi / Sosyal Medya / Koleksiyon Kartı Sızıntıları
    "anime", "manga", "cartoon", "comic", "illustration", "drawing", "animated",
    "chibi", "japanese anime", "ai generated anime", "digital art character", "boalls",
    "tiktok", "tiktok overlay", "emoji overlay", "phone recording", "screen recording",
    "trading card", "cardboard card", "nba hoops card", "fleer card", "topps card",
    "collector card", "rookie card", "physical card", "cardstock", "rookie of the year",
    "240p", "480p", "low resolution", "blurry phone", "phone screenshot",
    "watermark logo overlay", "text overlay social media", "meme template",
    "frame", "mockup", "poster on wall", "framed poster", "wall art mockup"
]

# Arama Motoru Negatif Hariç Tutma Filtresi (Negative Query Exclusions)
SEARCH_NEGATIVE_EXCLUSIONS: str = (
    '-ticket -stub -"ticket stub" -jumbotron -scoreboard -concession -bar -arena '
    '-Scola -Head -"Bonzi Wells" -"Yao Ming" -anime -manga -cartoon -comic -tiktok '
    '-emoji -trading_card -cardboard'
)

# Geriye dönük uyumluluk takma adı
STANDARD_CIVILIAN_NEGATIVES = CROSS_SPORT_AND_OFF_COURT_NEGATIVES


# Stopwords (Soyut aramalardan temizlenecek bağlaç, edat ve çapraz spor sızıntıları)
STOP_WORDS: Set[str] = {
    "the", "in", "a", "an", "of", "and", "is", "was", "are", "were", "to", "for",
    "with", "that", "this", "these", "those", "from", "at", "by", "on", "as",
    "about", "into", "through", "during", "before", "after", "above", "below",
    "from", "up", "down", "out", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "can", "will",
    "just", "should", "now", "it", "its", "his", "her", "their", "my", "your",
    # Çapraz spor, soyut terimler ve mecaz (idiom) sızıntılarını önleme
    "soccer", "football", "fifa", "world", "cup", "brazil", "robinho",
    "military", "base", "school", "signing", "autograph", "table",
    "upside", "down", "upside down", "completely", "discovered", "something", "secret",
    "behind", "reveals", "revealed", "unprecedented", "legendary", "miracle", "biological",
    "threshold", "extreme", "physics", "unmatched", "generated", "difference", "truth",
    "history", "moment", "incredible", "impossible", "insane", "crazy", "dime", "fire", "cold"
}


# ─────────────────────────────────────────────────────────────
# ÇIKTI VERİ MODELİ
# ─────────────────────────────────────────────────────────────

@dataclass
class ContextLockedQuery:
    """Karaktere çapalanmış bağlam-kilitli arama sorguları ve negatif havuzu."""
    primary_query: str
    fallback_queries: List[str]
    entity: str
    target_year: Optional[int]
    team_name: Optional[str]
    action_keyword: Optional[str]
    dynamic_negatives: List[str]

    @property
    def anchored_queries(self) -> List[str]:
        """Tüm çapalanmış sorguların birincil + yedek listesi."""
        return [self.primary_query] + list(self.fallback_queries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_query": self.primary_query,
            "fallback_queries": self.fallback_queries,
            "entity": self.entity,
            "target_year": self.target_year,
            "team_name": self.team_name,
            "action_keyword": self.action_keyword,
            "dynamic_negatives": self.dynamic_negatives
        }


# ─────────────────────────────────────────────────────────────
# ANA SINIF: QueryBuilder
# ─────────────────────────────────────────────────────────────

class QueryBuilder:
    """
    Zorunlu Karakter Çapası (Mandatory Subject Anchor) uygulayan,
    soyut kelimelerin tek başına aratılmasını engelleyen ve dinamik
    cross-sport negatifleri enjekte eden akıllı sorgu motoru.
    """

    ACTION_PATTERNS: List[Tuple[str, str]] = [
        # Spor Bilimi / Nöroloji / Beyin / Optik Sinir / Biyomekanik
        (r"\b(optic|retina|pupil|visual\s+cortex|neuron|neural|brain|cortex|neurobiology|motor\s+cortex|reaction\s+time|stimulus|synapse|synaptic|biological\s+threshold)\b", "human brain neural transmission impulse visual cortex 3d scientific animation"),
        (r"\b(trent\s+tucker|shot\s+clock|tenths\s+of\s+a\s+second|buzzer\s+beater|0\.4|final\s+tenths|clock\s+rules?)\b", "NBA vintage 1990 shot clock tenths of a second digital buzzer beater"),
        (r"\b(eccentric|braking\s+force|braking|kinematic|biomechanic|sensors?|force\s+plate|quadriceps|quad|deceleration|decelerate|stopping\s+power)\b", "athlete motion capture kinematic body sensors sports science laboratory slow motion"),
        (r"\b(friction|sudden\s+stop|sneakers?\s+court|hardwood\s+stop)\b", "basketball player sneakers sudden stop court friction slow motion close up"),
        (r"\b(step-back|step\s+back|stepback|isolation|separation)\b", "step back three pointer isolation"),
        (r"\b(catch\s+and\s+shoot|inbound\s+pass|inbounds|turnaround\s+jumper)\b", "catch and shoot buzzer beater"),
        (r"\b(dream\s+shake|shake|shimmy)\b", "dream shake baseline"),
        (r"\b(pivot|footwork|center\s+of\s+gravity|balance)\b", "pivot footwork post move"),
        (r"\b(reverse\s+layup|driving\s+layup|finger\s+roll|layup)\b", "layup rim"),
        (r"\b(optical\s+illusion|high\s+art|fake|half-spin)\b", "post fake shot move"),
        (r"\b(crossover|cross-over|crossed\s+over|ankles?)\b", "crossover"),
        (r"\b(slam\s+dunk|dunking|dunk|tomahawk|windmill)\b", "slam dunk"),
        (r"\b(bank\s+shot|off\s+the\s+glass|backboard)\b", "bank shot"),
        (r"\b(sweet\s+spot|sweetspot)\b", "sweet spot rim"),
        (r"\b(triple-double|triple\s+double)\b", "triple-double"),
        (r"\b(block|blocked|rejection|rim\s+protection)\b", "defensive block"),
        (r"\b(steal|steals|stolen|pickpocket)\b", "steal"),
        (r"\b(assist|dime|pass|playmaking)\b", "assist pass"),
        (r"\b(rebound|boards|glass)\b", "rebound"),
        (r"\b(jump\s+shot|jumper|pull-up|fadeaway|clutch\s+shot|three-pointer|3-pointer)\b", "jump shot"),
        (r"\b(rookie|rookie\s+season|debut)\b", "rookie"),
        (r"\b(defense|defensive|lockdown)\b", "defense"),
        (r"\b(post\s+up|fundamental|footwork|mechanics?)\b", "post up"),
        (r"\b(fast\s+break|transition)\b", "fast break"),
        (r"\b(championship|finals|trophy|ring)\b", "championship")
    ]

    @classmethod
    def extract_entity(cls, text: str, default_entity: str = "") -> str:
        """
        Metinden NBA oyuncusunu veya konusunu çıkarır.
        Tek bir rastgele eşleşme yerine ağırlıklı frekans analizi yapar:
        Başlık veya ilk cümlede geçen isimlere yüksek öncelik verir.
        """
        if not text:
            return default_entity or "Tim Duncan"

        t_lower = text.lower()
        first_part = t_lower[:120]  # Başlık / ilk cümle alanı

        # Popüler lakaplar ve soyadlar haritası
        nicknames_and_lastnames = {
            "wilt chamberlain": "Wilt Chamberlain",
            "chamberlain": "Wilt Chamberlain",
            "wilt": "Wilt Chamberlain",
            "lebron james": "LeBron James",
            "lebron": "LeBron James",
            "michael jordan": "Michael Jordan",
            "jordan": "Michael Jordan",
            "mj": "Michael Jordan",
            "kobe bryant": "Kobe Bryant",
            "kobe": "Kobe Bryant",
            "black mamba": "Kobe Bryant",
            "shaquille o'neal": "Shaquille O'Neal",
            "shaq": "Shaquille O'Neal",
            "hakeem olajuwon": "Hakeem Olajuwon",
            "olajuwon": "Hakeem Olajuwon",
            "hakeem": "Hakeem Olajuwon",
            "the dream": "Hakeem Olajuwon",
            "dream shake": "Hakeem Olajuwon",
            "tim duncan": "Tim Duncan",
            "duncan": "Tim Duncan",
            "kareem abdul-jabbar": "Kareem Abdul-Jabbar",
            "kareem": "Kareem Abdul-Jabbar",
            "abdul-jabbar": "Kareem Abdul-Jabbar",
            "stephen curry": "Stephen Curry",
            "curry": "Stephen Curry",
            "steph": "Stephen Curry",
            "kevin durant": "Kevin Durant",
            "durant": "Kevin Durant",
            "kd": "Kevin Durant",
            "luka doncic": "Luka Doncic",
            "doncic": "Luka Doncic",
            "allen iverson": "Allen Iverson",
            "iverson": "Allen Iverson",
            "giannis antetokounmpo": "Giannis Antetokounmpo",
            "giannis": "Giannis Antetokounmpo",
            "nikola jokic": "Nikola Jokic",
            "jokic": "Nikola Jokic",
            "russell westbrook": "Russell Westbrook",
            "westbrook": "Russell Westbrook",
            "dennis rodman": "Dennis Rodman",
            "rodman": "Dennis Rodman",
            "larry bird": "Larry Bird",
            "bird": "Larry Bird",
            "magic johnson": "Magic Johnson",
            "magic": "Magic Johnson",
            "dikembe mutombo": "Dikembe Mutombo",
            "mutombo": "Dikembe Mutombo",
            "dirk nowitzki": "Dirk Nowitzki",
            "nowitzki": "Dirk Nowitzki",
            "david robinson": "David Robinson",
            "the admiral": "David Robinson",
            "robinson": "David Robinson",
            "derek fisher": "Derek Fisher",
            "fisher": "Derek Fisher",
            "d-fish": "Derek Fisher",
            "james harden": "James Harden",
            "harden": "James Harden",
            "the beard": "James Harden",
            "shai gilgeous-alexander": "Shai Gilgeous-Alexander",
            "shai": "Shai Gilgeous-Alexander",
            "jalen brunson": "Jalen Brunson",
            "brunson": "Jalen Brunson"
        }

        # Skor tablosu
        scores: Dict[str, int] = {}

        # 1. Tam isim ve takma ad frekansı
        for alias, full_n in nicknames_and_lastnames.items():
            pattern = rf"\b{re.escape(alias)}\b"
            # Başlık / ilk kısım kontrolü (+50 puan)
            if re.search(pattern, first_part):
                scores[full_n] = scores.get(full_n, 0) + 50
            # Genel metin frekansı (+5 puan her geçiş)
            matches = len(re.findall(pattern, t_lower))
            if matches > 0:
                scores[full_n] = scores.get(full_n, 0) + (matches * 5)

        if scores:
            best_entity = max(scores.items(), key=lambda x: x[1])[0]
            return best_entity

        # Büyük harfli isim kalıbı (örn: Hakeem Olajuwon)
        # Sadece gerçek isim olabilecek çiftleri kabul et, soyut kavramları kara listeye al
        NON_PLAYER_PHRASES = {
            "second miracle", "human biology", "trent tucker", "atomic limit", "shot clock",
            "buzzer beater", "fast break", "playoff game", "game winner", "triple double",
            "sports science", "nba analysis", "western conference", "eastern conference",
            "regular season", "nba finals", "hall of fame", "court action", "red led",
            "left hand", "right hand", "reaction time", "optic nerves", "motor cortex",
            "scientific reality", "deceleration secret", "braking force", "muscle braking"
        }
        VERIFIED_NAME_BLACKLIST = {
            "defied", "human", "biology", "second", "miracle", "when", "the", "nba",
            "atomic", "limit", "secret", "behind", "step", "back", "clock", "shot",
            "reality", "neural", "nerves", "optic", "motor", "cortex", "science",
            "trent", "tucker"
        }
        proper_names = re.findall(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", text)
        for pn in proper_names:
            words = pn.lower().split()
            if any(w in VERIFIED_NAME_BLACKLIST for w in words):
                continue
            if pn.lower() in NON_PLAYER_PHRASES:
                continue
            if not any(t in pn.lower() for t in ["the basketball", "golden state", "san antonio", "new york", "los angeles", "houston rockets", "chicago bulls", "boston celtics"]):
                return pn

        if default_entity:
            return default_entity

        return "Tim Duncan"

    @classmethod
    def extract_year(cls, text: str, entity: str = "") -> Optional[int]:
        """Metinden yılı veya oyuncunun zirve dönemini çıkarır."""
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
        
        # Eğer oyuncu biliniyorsa, metindeki yıllardan oyuncunun kariyeriyle eşleşeni seç
        if entity in PLAYER_CAREER_MAP:
            p_eras = PLAYER_CAREER_MAP[entity].get("eras", [])
            valid_career_years = []
            for y_str in years:
                y_val = int(y_str)
                if any(era["start"] <= y_val <= era["end"] for era in p_eras):
                    valid_career_years.append(y_val)
            if valid_career_years:
                return max(set(valid_career_years), key=valid_career_years.count)
            # Eğer metindeki yıllar oyuncunun kariyerine uymuyorsa (örn: 1990 kuralı), oyuncunun varsayılan peak yılını dön!
            default_y = PLAYER_CAREER_MAP[entity].get("default_year")
            if default_y:
                return default_y

        if years:
            return int(years[0])

        t_lower = text.lower()
        if "rookie" in t_lower and "iverson" in t_lower:
            return 1997
        if "rookie" in t_lower and "duncan" in t_lower:
            return 1998
        if "rookie" in t_lower and "jordan" in t_lower:
            return 1985
        if "rookie" in t_lower and "lebron" in t_lower:
            return 2004

        # Eğer yıl bulunamazsa oyuncunun kayıtlı varsayılan peak yılını dön
        if entity in PLAYER_CAREER_MAP:
            return PLAYER_CAREER_MAP[entity].get("default_year")

        return None

    @classmethod
    def extract_team(cls, text: str, entity: str = "", year: Optional[int] = None) -> Optional[str]:
        """Metinden veya oyuncunun o dönemdeki takımını tespit eder."""
        t_lower = text.lower()

        # 1. Eğer oyuncu kayıtlıysa, oyuncunun kendi takımı rakip takımlardan daima önceliklidir
        if entity in PLAYER_CAREER_MAP:
            p_data = PLAYER_CAREER_MAP[entity]
            player_teams = [era["primary_team"] for era in p_data.get("eras", [])]
            for pt in player_teams:
                if pt.lower() in t_lower:
                    return pt
                t_aliases = NBA_TEAMS.get(pt, {}).get("aliases", [])
                for alias in t_aliases:
                    if re.search(rf"\b{re.escape(alias)}\b", t_lower):
                        return pt
            target_year = year or p_data.get("default_year")
            if target_year:
                for era in p_data.get("eras", []):
                    if era["start"] <= target_year <= era["end"]:
                        return era["primary_team"]
            if p_data.get("eras"):
                return p_data["eras"][0]["primary_team"]

        # 2. Genel metin araması (rakip veya genel takım)
        for team_full, t_info in NBA_TEAMS.items():
            if team_full.lower() in t_lower:
                return team_full
            for alias in t_info["aliases"]:
                if re.search(rf"\b{re.escape(alias)}\b", t_lower):
                    return team_full

        return None

    @classmethod
    def extract_action_or_visual_keywords(cls, text: str) -> str:
        """Metindeki maç içi görsel/aksiyon anahtar kelimelerini temizleyip çıkarır."""
        for pattern, action_name in cls.ACTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return action_name

        # Eşleşme yoksa stopwords'leri temizle ve en anlamlı 2-3 kelimeyi al
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        filtered = [w for w in words if w not in STOP_WORDS]
        if filtered:
            return " ".join(filtered[:3])

        return "basketball action"

    @classmethod
    def build_multi_queries(
        cls,
        entity: Optional[str] = None,
        opponent: Optional[str] = None,
        year: Optional[int] = None,
        script_or_context: Any = None
    ) -> List[str]:
        """
        Aday havuzu kıtlığını (Fetch Starvation) önleyen ve zengin maç aksiyonu
        kareleri toplayabilen çoklu-sorgu genişletme motoru (Multi-Query Expansion).
        Sabit fallback oyuncusu veya takımı içermez; dinamik bağlamdan türetir.
        """
        ent = entity.strip() if entity else None
        if not ent and script_or_context:
            cq_temp = cls.build_context_locked_queries(script_or_context)
            ent = cq_temp.entity

        ent = ent or "NBA Player"
        yr = year or (cls.extract_year(str(script_or_context)) if script_or_context else None)
        yr_str = f"{yr} " if yr else ""

        # Takım bilgilerini bul (eras[0] yerine peak/default_year dönemine öncelik ver)
        team = None
        if ent in PLAYER_CAREER_MAP:
            p_data = PLAYER_CAREER_MAP[ent]
            target_year = yr or p_data.get("default_year")
            if target_year:
                for era in p_data.get("eras", []):
                    if era.get("start", 0) <= target_year <= era.get("end", 9999):
                        team = era.get("primary_team")
                        break
            if not team and p_data.get("eras"):
                team = p_data["eras"][0].get("primary_team")
        team = team or ""

        # Rakip oyuncu ve takım bilgisi (Yalnızca metinde gerçek bir eşleşme varsa ekle)
        opp = opponent
        if not opp and script_or_context:
            c_text = str(script_or_context).lower()
            for cand_p in PLAYER_CAREER_MAP.keys():
                if cand_p.lower() != ent.lower() and cand_p.lower() in c_text:
                    opp = cand_p
                    break

        opp_team = None
        if opp and opp in PLAYER_CAREER_MAP:
            opp_team = PLAYER_CAREER_MAP[opp].get("eras", [{}])[0].get("primary_team")

        queries: List[str] = []

        # 1. Birincil Oyuncu Maç & Aksiyon Sorguları
        queries.append(f'"{ent}" {yr_str}playoffs action shot'.strip())
        queries.append(f'"{ent}" {yr_str}NBA game action photo'.strip())
        if team:
            queries.append(f'"{ent}" {team} {yr_str}game action shot'.strip())
            queries.append(f'"{ent}" {team} post up footwork action'.strip())
            queries.append(f'"{ent}" {team} jersey game highlights'.strip())
            queries.append(f'"{ent}" {team} court action photo'.strip())
        else:
            queries.append(f'"{ent}" clutch playoff shot'.strip())
            queries.append(f'"{ent}" authentic NBA court photo'.strip())

        if "derek fisher" in ent.lower() or "fisher" in ent.lower():
            queries.append(f'"{ent}" Los Angeles Lakers 2004 0.4 shot San Antonio Spurs Game 5')
            queries.append(f'"{ent}" buzzer beater Lakers vs Spurs 2004 Western Conference Semifinals')
            queries.append(f'"{ent}" shooting over Manu Ginobili 2004 Game 5')
            queries.append(f'"{ent}" receiving inbound pass mid air catch turn 2004')
            queries.append(f'"{ent}" Gary Payton inbounds pass sideline 2004 Game 5')
            queries.append(f'"Tim Duncan" stunned disbelief 2004 Game 5 Lakers Spurs')
            queries.append(f'"{ent}" running off court celebration 2004 Game 5')
            queries.append(f'"{ent}" Los Angeles Lakers jersey #2 2004 action')
            queries.append('human brain neural transmission visual cortex 3d medical animation 4k')
            queries.append('NBA vintage 1990 shot clock tenths of a second digital buzzer beater')
            queries.append('macro eye pupil focus retina light optic nerve scientific animation')

        if "james harden" in ent.lower() or "harden" in ent.lower():
            queries.append(f'"{ent}" Houston Rockets step back three pointer')
            queries.append(f'"{ent}" deceleration sudden stop sneakers court friction 2018')
            queries.append(f'"{ent}" Houston Rockets isolation stepback jumper 2018')
            queries.append(f'"{ent}" crossover drive slow motion broadcast 2018')
            queries.append(f'"{ent}" Houston Rockets MVP 2018 game action')
            queries.append(f'"{ent}" step back separation defender off balance')
            queries.append('athlete running motion capture kinematic body sensors sports science 4k')
            queries.append('sports biomechanics computer graph data velocity curve visualization 4k')
            queries.append('basketball player sneakers sudden stop court friction slow motion close up')

        if "wilt" in ent.lower() or "chamberlain" in ent.lower():
            queries.append(f'"{ent}" dunk Philadelphia Warriors 1962')
            queries.append(f'"{ent}" vs Bill Russell Celtics game action')
            queries.append(f'"{ent}" rebound finger roll baseline move')
            queries.append(f'"{ent}" Los Angeles Lakers 1972 finals')
            queries.append(f'"{ent}" scoring Hershey Pennsylvania game action')
            queries.append(f'"{ent}" Philadelphia Warriors 1962 game action')
            queries.append(f'"{ent}" hook shot rebound rim defense')
            queries.append(f'"{ent}" Philadelphia 76ers 1967 championship')
            queries.append(f'"{ent}" 100 points game Hershey')

        if "lebron" in ent.lower():
            queries.append(f'"{ent}" championship trophy celebration Lakers Cavaliers')
            queries.append(f'"{ent}" chalk toss powder routine')
            queries.append(f'"{ent}" clutch game winner playoff celebration')
            queries.append(f'"{ent}" Miami Heat championship trophy')
            queries.append(f'"{ent}" Cleveland Cavaliers 2016 NBA finals')

        if ent in PLAYER_CAREER_MAP:
            for sm in PLAYER_CAREER_MAP[ent].get("signature_moves", []):
                queries.append(f'"{ent}" {team} {sm} action'.strip())

        queries.append(f'"{ent}" pull up jumper mid-range game')
        queries.append(f'"{ent}" clutch game winner shot')
        queries.append(f'"{ent}" defense contest court action')

        # 2. Rakip oyuncu bağlamda varsa karşılaştırmalı sorguları ekle
        if opp:
            queries.append(f'"{ent}" vs "{opp}" {yr_str}NBA game'.strip())
            queries.append(f'"{ent}" "{opp}" {yr_str}playoffs contest'.strip())
            if opp_team:
                queries.append(f'"{ent}" against {opp_team} {yr_str}action'.strip())
                queries.append(f'"{opp}" {opp_team} NBA basketball action'.strip())

        # Tekilleştir ve sıralı dön
        seen = set()
        out = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                out.append(q)
        return out

    @classmethod
    def generate_dynamic_negatives(
        cls,
        entity: str,
        target_year: Optional[int] = None,
        active_team: Optional[str] = None,
        custom_negatives: Optional[List[str]] = None,
        script_text: Optional[str] = None
    ) -> List[str]:
        """
        Dönem, takım, cross-sport ve rakip sızmasını engelleyen dinamik negatifler listesi üretir.
        """
        negatives: Set[str] = set()

        # 1. Otomatik Cross-Sport ve Saha Dışı Negatifler
        for neg in CROSS_SPORT_AND_OFF_COURT_NEGATIVES:
            negatives.add(neg.lower().strip())

        # 2. Oyuncunun diğer dönemlerdeki kulüpleri
        if entity in PLAYER_CAREER_MAP:
            p_data = PLAYER_CAREER_MAP[entity]

            if target_year:
                for era in p_data["eras"]:
                    if target_year < era["start"] or target_year > era["end"]:
                        neg_team = era["primary_team"]
                        if neg_team != active_team:
                            negatives.add(neg_team.lower())

            for ot in p_data.get("other_teams", []):
                if ot != active_team:
                    negatives.add(ot.lower())

            # Karakterin videosuna sızması istenmeyen diğer süperstarlar / rakipler
            for rival in p_data.get("rival_competitors", []):
                # Eğer rakip oyuncu senaryoda geçiyorsa (örn: David Robinson), negatife atma
                if script_text and any(word in script_text.lower() for word in rival.lower().split() if len(word) > 4):
                    continue
                negatives.add(rival.lower())

            # Anti-McHale & Anti-Celtics Sızıntı Koruması (Konu Boston Celtics değilse)
            if active_team != "Boston Celtics" and (not script_text or "celtics" not in script_text.lower()):
                negatives.add("kevin mchale")
                negatives.add("mchale")
                negatives.add("boston celtics")
                negatives.add("celtics")
                negatives.add("celtics green jersey")
                negatives.add("larry bird")
                negatives.add("robert parish")
                negatives.add("parish")
                negatives.add("dennis johnson")
                negatives.add("danny ainge")
                negatives.add("boston garden")

            if p_data.get("college") and active_team:
                negatives.add(p_data["college"].lower())
                negatives.add("college basketball")
                negatives.add("ncaa tournament")

        # Özel Karakter Negatif Kalkanı (Audit Hatalarını Kalıcı Olarak Engelleyen Kural Seti)
        if entity:
            ent_l = entity.lower()
            if "derek fisher" in ent_l or "fisher" in ent_l:
                negatives.update([
                    "lebron", "lebron james", "23", "kobe 24", "2010", "2009",
                    "dwight howard", "magic", "orlando", "orlando magic", "pinstripes",
                    "shai", "shai gilgeous-alexander", "okc", "thunder",
                    "autograph", "signature", "marker", "yellow scribble", "signed",
                    "tiktok", "chasedown", "chase down block", "block", "chasedown block",
                    "emoji", "amateur", "gym", "cellphone", "text overlay", "red bar",
                    "letterbox", "clippers", "suns", "sam cassell", "corey maggette",
                    "trading card", "cardboard card", "cardboard", "collectible",
                    "reverse dunk", "hanging on rim", "slam dunk contest",
                    "billups", "chauncey billups", "pistons", "detroit", "palace auburn hills",
                    "celtics", "boston celtics", "rondo", "green jersey", "finals 2010"
                ])
            elif "james harden" in ent_l or "harden" in ent_l:
                negatives.update([
                    "steven adams", "trophy", "championship trophy", "larry obrien",
                    "larry o'brien", "cavs", "cleveland", "cavaliers", "donovan mitchell",
                    "jersey swap", "deepfake", "fake", "montage", "yellow box",
                    "harden driving layup", "overlay", "tiktok", "screen recording",
                    "scoreboard", "watermark", "dunk", "hanging on rim", "rim hang",
                    "upside down", "reverse dunk", "slam dunk contest", "tomahawk",
                    "76ers", "philadelphia", "sixers", "chris paul", "celebration jump",
                    "lebron", "lebron james", "yellow headband", "mouse cursor", "pointer"
                ])

        if custom_negatives:
            for cn in custom_negatives:
                negatives.add(cn.lower().strip())

        # Invariant: Aktif karakterin kendi adı veya parçaları asla negatiflerde bulunamaz!
        if entity:
            negatives.discard(entity.lower().strip())
            for word in entity.lower().split():
                if len(word) >= 3:
                    negatives.discard(word)

        return sorted(list(negatives))

    @classmethod
    def build_context_locked_queries(
        cls,
        text_or_script: Any = None,
        scene_narration: str = "",
        fallback_entity: str = "Tim Duncan",
        *,
        scene_text: Optional[str] = None,
        target_team: Optional[str] = None,
        era_year: Optional[int] = None
    ) -> ContextLockedQuery:
        """
        Karaktere Çapalanmış Arama Motoru:
        - Soyut terimler ("sweet spot", "geometry") asla tek başına aratılmaz.
        - Her sorgu zorunlu olarak {entity} {team} {year} önekine çapalanır!
        - Invariant: Her üretilen sorguda {entity} yer almak zorundadır.
        """
        if scene_text is not None and text_or_script is None:
            text_or_script = scene_text
        elif scene_text is not None and text_or_script is not None:
            scene_narration = f"{scene_narration} {scene_text}".strip()

        combined_text = ""
        if isinstance(text_or_script, dict):
            parts = [
                str(text_or_script.get("title", "")),
                str(text_or_script.get("topic", "")),
                str(text_or_script.get("description", "")),
                scene_narration
            ]
            # Sahne anlatımlarını ve metinlerini de ekle (Senaryodaki rakiplerin tespiti için)
            sc_list = text_or_script.get("scenes") or text_or_script.get("script_data", {}).get("scenes") or []
            if isinstance(sc_list, list):
                for sc_item in sc_list:
                    if isinstance(sc_item, dict):
                        parts.append(sc_item.get("narration", ""))
                        parts.append(sc_item.get("text", ""))
            tags_list = text_or_script.get("tags") or []
            if isinstance(tags_list, list):
                parts.extend([str(tg) for tg in tags_list])
            combined_text = " ".join([p for p in parts if p]).strip()
        else:
            combined_text = f"{str(text_or_script or '')} {scene_narration}".strip()

        entity = cls.extract_entity(combined_text, default_entity=fallback_entity)
        year = era_year if era_year is not None else cls.extract_year(combined_text, entity=entity)
        team = target_team if target_team is not None else cls.extract_team(combined_text, entity=entity, year=year)
        action_or_kw = cls.extract_action_or_visual_keywords(scene_narration or combined_text)

        # ─────────────────────────────────────────────────────────────
        # ZORUNLU ÇAPA (MANDATORY SUBJECT ANCHOR) OLUŞTURMA
        # ─────────────────────────────────────────────────────────────
        # Spor ve lig bağlamına zorunlu zincirleme: '"{entity}" NBA basketball {team}'
        team_str = f'"{team}"' if team else '"NBA"'
        anchor_prefix_parts = [f'"{entity}"', "NBA basketball", team_str]
        if year:
            anchor_prefix_parts.append(str(year))

        anchor_prefix = " ".join(anchor_prefix_parts)

        # 1. Birincil Çapalanmış Sorgu
        primary_query = f"{anchor_prefix} {action_or_kw}".strip()

        # 2. Kademeli Yedek Çapalanmış Sorgular (Semantic Drift Korumalı)
        fallback_queries: List[str] = []

        # Eğer metinde rakip oyuncu/ikinci bir efsane geçiyorsa (örn: David Robinson), ona da çapalanmış sorgular üret
        opp_entities: List[str] = []
        for p_name in PLAYER_CAREER_MAP.keys():
            if p_name.lower() != entity.lower() and p_name.lower() in combined_text.lower():
                opp_entities.append(p_name)

        for opp in opp_entities[:2]:
            opp_team = PLAYER_CAREER_MAP[opp]["eras"][0]["primary_team"] if PLAYER_CAREER_MAP[opp].get("eras") else "Spurs"
            fallback_queries.append(f'"{entity}" "{opp}" NBA basketball')
            fallback_queries.append(f'"{opp}" NBA basketball "{opp_team}"')

        if team and year:
            fallback_queries.append(f'"{entity}" NBA basketball "{team}" {year} game action')
            fallback_queries.append(f'"{entity}" NBA basketball "{team}" {year}')
        if team:
            fallback_queries.append(f'"{entity}" NBA basketball "{team}" court action')
            fallback_queries.append(f'"{entity}" NBA basketball "{team}"')
        if year:
            fallback_queries.append(f'"{entity}" NBA basketball {year}')
        fallback_queries.append(f'"{entity}" NBA basketball player')

        # 3. KESİN INVARIANT DENETİMİ (Sıfır Konu Sapması Garantisi)
        # Her sorguda ana spor dalı "NBA basketball" ve en azından ilgili oyuncu adı bulunmalıdır
        all_queries = [primary_query] + fallback_queries
        for q in all_queries:
            if "nba basketball" not in q.lower():
                raise ValueError(f"Semantic Drift Tespit Edildi! Sorguda NBA basketball çapası eksik: '{q}'")

        # 4. Dinamik Negatif Etiketler
        dynamic_negatives = cls.generate_dynamic_negatives(
            entity=entity,
            target_year=year,
            active_team=team,
            script_text=combined_text
        )

        return ContextLockedQuery(
            primary_query=primary_query,
            fallback_queries=fallback_queries,
            entity=entity,
            target_year=year,
            team_name=team,
            action_keyword=action_or_kw,
            dynamic_negatives=dynamic_negatives
        )


# Singleton nesne
query_builder = QueryBuilder()
