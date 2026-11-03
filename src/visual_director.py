"""
visual_director.py
──────────────────
Lead Visual Director & Scene Architect for Autonomous Vertical Short-Form Engine
(YouTube Shorts, Instagram Reels, TikTok).

Transforms audio scripts and word-level timings into frame-by-frame visual timeline
schemas enforcing:
1. Strict Domain Locking (Zero cross-domain leaks)
2. Rhythm & Pacing (1.6s - 2.4s cuts, standard 2.15s)
3. Anti-Clustering & Diversity (max_consecutive_same_entity: 1)
4. Zero Queue-Desync (0-indexed absolute time mapping)
5. Visual Hygiene & Negative Filtering (OCR, tourist, cctv, modern clutter blocks)
6. Subtitle & Typography Integrity (2-4 words, anti-orphan, unbroken compounds)
"""

import os
import re
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

VISUAL_DIRECTOR_SYSTEM_PROMPT = """You are the "Lead Visual Director & Scene Architect" for an autonomous vertical short-form video engine (Shorts, Reels, TikTok).
Your core mission is to convert an audio script and its Whisper word-level timestamps into an immaculate, frame-by-frame visual timeline schema (JSON).

Your output directly drives stock asset downloaders (Pexels, Storyblocks, Pixabay) and the rendering engine (Remotion / FFmpeg). Flawless semantic matching, visual hygiene, and rhythm are non-negotiable.

---

### CORE RULES & ENGINE CONSTRAINTS

#### 1. STRICT DOMAIN LOCKING (Zero Cross-Domain Semantic Bleed)
- Every visual query MUST include the global channel anchor (e.g., if topic is "Aviation", NEVER search just "cabin", search "commercial airliner cabin interior night flight").
- Queries must be strictly contextual:
  * NO cross-domain leaks: Never allow trains, buses, or subways into aviation; never allow suburban backyards into luxury tropical resorts; never allow surface gates into ancient underground bunkers.
  * Negative terms are mandatory for EVERY individual scene to proactively block unwanted domains.

#### 2. RHYTHM & PACING (The 2.0s - 2.4s Rule)
- Vertical video attention spans require rapid visual cuts.
- Maximum duration for ANY visual asset is 2.4 seconds. Minimum is 1.6 seconds.
- If a sentence lasts 6 seconds, you MUST split it into 3 distinct, sequential visual beats with different camera angles, perspectives, or subjects. Never stretch one clip across a full long sentence.

#### 3. ANTI-CLUSTERING & DIVERSITY (Zero Asset Sticking)
- Maximum consecutive clips with the same category/entity tag is 1 (max_consecutive_same_entity: 1).
- Prohibited:
  * Never show repeated food/dish items (e.g., 3 consecutive salmon/sushi shots).
  * Never show the same mechanical feature twice in a row (e.g., rolling stone doors).
- If the audio talks about a broad concept (e.g., "hospitality", "subterranean society"), diversify across actions: wide exterior -> human interaction -> technical detail -> atmospheric shot.

#### 4. ZERO QUEUE-DESYNC (Absolute Time Mapping)
- Each scene's `start_sec` and `end_sec` must match the EXACT timestamps of the corresponding spoken phrase.
- Ensure 0-indexed alignment: The asset at index N MUST visually depict the exact words spoken at index N. Off-by-one queue latency is a fatal pipeline failure.

#### 5. VISUAL HYGIENE & OCR PREVENTION
- Stock footage often contains ugly elements. You must inject strict negative keywords into every query:
  * Always block: "text, watermark, signboard, poster, modern clothes, wires, cctv, amateur, flash photography, mouse cursor, screen recording".
  * For historical/ancient topics, additionally block: "tourist, modern lighting, cables, railing, concrete, graffiti".
  * For night/emergency topics, block: "bright sunlight, day, blue sky, smiling passengers".

#### 6. SUBTITLE & TYPOGRAPHY INTEGRITY
- Words in subtitles must be grouped into 2 to 4 words per frame.
- NEVER split compound adjectives across lines: keep "five-star", "high-end", "well-known" intact with non-breaking hyphens.
- Proper nouns must remain unfragmented (e.g., "Sri Lanka's", "Derinkuyu").
- Enable anti-orphan rule: Never leave a single trailing word on a subtitle card.

---

### OUTPUT JSON SCHEMA CONTRACT

You must respond ONLY with a valid JSON object strictly matching this schema. No markdown conversational chatter outside the JSON:

{
  "project_meta": {
    "topic": "string",
    "category_badge": "ANCIENT MYSTERIES | AVIATION SECRETS | BUDGET LUXURY GUIDE | TECH CRIME",
    "badge_display_window": {"start_sec": 0.0, "end_sec": 4.5},
    "global_domain_prefix": "string (e.g., 'commercial aviation aircraft')",
    "global_negative_keywords": "string"
  },
  "timeline_scenes": [
    {
      "scene_index": 0,
      "start_sec": 0.00,
      "end_sec": 2.10,
      "audio_phrase": "exact transcript text for this beat",
      "visual_entity_category": "landscape | interior | action | macro | person",
      "primary_search_query": "specific, descriptive query anchored to domain (e.g., 'Boeing 787 dim cabin night landing approach 4k')",
      "fallback_search_query": "alternative high-quality query",
      "negative_keywords": "string of excluded terms (e.g., 'daylight, train, bus, vintage, propeller, cartoon')",
      "camera_motion": "slow_zoom_in | slow_zoom_out | subtle_pan_right",
      "subtitle_display": {
        "text": "DAYTIME OR NIGHTTIME",
        "highlight_word": "NIGHTTIME"
      }
    }
  ],
  "ui_elements": {
    "cta_button": {
      "type": "subscribe",
      "start_sec": 45.0,
      "end_sec": 47.0,
      "position_y": 0.82
    }
  }
}
"""

UNIVERSAL_NEGATIVES = (
    "text, watermark, signboard, poster, modern clothes, wires, cctv, amateur, "
    "flash photography, mouse cursor, screen recording, blurry, low resolution, bad quality"
)

ENTITY_CATEGORIES = ["landscape", "interior", "action", "macro", "detail", "person", "atmospheric"]
CAMERA_MOTIONS = ["slow_zoom_in", "slow_zoom_out", "subtle_pan_right", "subtle_pan_left"]


class VisualDirector:
    """
    Lead Visual Director & Scene Architect Engine.
    Produces valid JSON timeline schemas adhering to all 6 Core Rules.
    """

    def __init__(self):
        pass

    def detect_domain_profile(self, topic: str, category: str, script_text: str = "") -> Dict[str, Any]:
        """Konu ve metin analizi yaparak global kural ve çapa profilini oluşturur."""
        corpus = f"{topic} {category} {script_text}".lower()

        # 1. Antik Gizemler & Yeraltı Şehirleri (Derinkuyu / Kapadokya / vb.)
        if any(w in corpus for w in ["underground city", "derinkuyu", "kaymakli", "cappadocia", "fairy chimneys", "ancient", "troglodyte", "archaeology", "subterranean"]):
            return {
                "category_badge": "ANCIENT MYSTERIES",
                "badge_display_window": {"start_sec": 0.0, "end_sec": 4.5},
                "global_domain_prefix": "Derinkuyu ancient underground city carved volcanic rock",
                "global_negative_keywords": (
                    f"{UNIVERSAL_NEGATIVES}, tourist, tourists, crowd, guide, modern lighting, electrical cables, "
                    "metal railing, concrete, modern stairs, graffiti, red convertible car, woman in dress, influencer, "
                    "hot air balloons in sky, blue painted door, apartment door, wooden house door, neoclassical entrance, "
                    "iron knocker, red brick cellar, gothic church, european village street, cctv surveillance camera"
                ),
                "domain_type": "ancient_mysteries"
            }

        # 2. Havacılık & Uçuş Gizemleri (Aviation / Cabin / Flight Safety)
        if any(w in corpus for w in ["airplane", "airline", "aircraft", "cockpit", "flight", "cabin", "landing lights", "dim lights", "aviation", "runway"]):
            return {
                "category_badge": "AVIATION SECRETS",
                "badge_display_window": {"start_sec": 0.0, "end_sec": 4.5},
                "global_domain_prefix": "commercial aviation airliner aircraft cabin interior night flight",
                "global_negative_keywords": (
                    f"{UNIVERSAL_NEGATIVES}, train, bus, subway, metro, bright sunlight, day, blue sky, "
                    "smiling passengers, 1950s antique car, vintage propeller cargo plane, museum exhibit, "
                    "flight simulator 3d render, warplane"
                ),
                "domain_type": "aviation"
            }

        # 3. Lüks Seyahat & Bütçe Otelleri (Luxury Travel / Villa / Resort)
        if any(w in corpus for w in ["live like royalty", "50/day", "fifty dollars", "luxury", "villa", "budget luxury", "resort", "bali", "vietnam", "sri lanka"]):
            return {
                "category_badge": "BUDGET LUXURY GUIDE",
                "badge_display_window": {"start_sec": 0.0, "end_sec": 4.5},
                "global_domain_prefix": "tropical luxury resort private pool villa ocean view",
                "global_negative_keywords": (
                    f"{UNIVERSAL_NEGATIVES}, iceland, volcanic crater lake, cold mountains, snow, glacier, "
                    "las vegas casino hotel, neon signs, mandalay bay, eiffel tower paris, cheap motel, "
                    "suburban backyard, indoor swimming pool plastic cover, radiator, dirty street"
                ),
                "domain_type": "luxury_travel"
            }

        # 4. Sokak Lezzetleri (Street Food Showdown)
        if any(w in corpus for w in ["street food", "bangkok vs", "pad thai", "al pastor", "carnitas", "taco", "wok", "culinary"]):
            return {
                "category_badge": "STREET FOOD SHOWDOWN",
                "badge_display_window": {"start_sec": 0.0, "end_sec": 4.5},
                "global_domain_prefix": "authentic street food night market culinary cooking",
                "global_negative_keywords": (
                    f"{UNIVERSAL_NEGATIVES}, mcdonalds, fast food chain, supermarket frozen food, dining table formal"
                ),
                "domain_type": "street_food"
            }

        # Varsayılan
        return {
            "category_badge": category.upper().replace("_", " ") if category else "SPECIAL REPORT",
            "badge_display_window": {"start_sec": 0.0, "end_sec": 4.5},
            "global_domain_prefix": topic,
            "global_negative_keywords": UNIVERSAL_NEGATIVES,
            "domain_type": "general"
        }

    def generate_visual_timeline(
        self,
        topic: str,
        category: str,
        script_data: Dict[str, Any],
        total_duration: float,
        whisper_segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Girdi senaryosu ve dış ses süresinden 1.6s - 2.4s aralığında
        kusursuz, 0-indexed, kural kısıtlamalarına %100 uyan görsel zaman çizelgesi şeması derler.
        """
        domain_meta = self.detect_domain_profile(topic, category, str(script_data))

        # 1. Senaryo sahnelerini normalize et
        scenes = script_data.get("scenes") or []
        if not scenes and isinstance(script_data, dict):
            scenes = (script_data.get("script_data") or {}).get("scenes") or []
        if not scenes:
            raw_text = script_data.get("narration") or script_data.get("text") or topic
            scenes = [{"narration": raw_text}]

        # 2. Hedef kesme temposu: 2.15s ortalama (1.6s - 2.4s kuralı)
        target_cut_duration = 2.15
        total_cuts = max(1, int(math.ceil(total_duration / target_cut_duration)))

        # Sahnelerin süre ağırlıklarını belirle
        total_chars = sum(len((s.get("narration") or s.get("text") or "").strip()) for s in scenes)
        total_chars = max(1, total_chars)

        scene_durations = []
        running_time = 0.0
        for idx, s in enumerate(scenes):
            s_text = (s.get("narration") or s.get("text") or "").strip()
            char_ratio = len(s_text) / total_chars
            s_dur = total_duration * char_ratio
            s_dur = max(2.0, round(s_dur, 2))
            scene_durations.append((running_time, running_time + s_dur, s_text))
            running_time += s_dur

        # Süre düzeltmesi
        if scene_durations:
            last_idx = len(scene_durations) - 1
            st, _, txt = scene_durations[last_idx]
            scene_durations[last_idx] = (st, total_duration, txt)

        timeline_scenes = []
        current_time = 0.0
        scene_idx = 0
        last_entity_category = ""

        # 3. Her kesme beat'ini oluştur
        domain_type = domain_meta["domain_type"]
        global_prefix = domain_meta["global_domain_prefix"]
        global_neg = domain_meta["global_negative_keywords"]

        for cut_i in range(total_cuts):
            beat_end = min(total_duration, round(current_time + target_cut_duration, 2))
            if cut_i == total_cuts - 1:
                beat_end = total_duration

            beat_dur = beat_end - current_time
            if beat_dur < 1.0 and timeline_scenes:
                # Son kesme çok kısaysa bir öncekine ekle
                timeline_scenes[-1]["end_sec"] = total_duration
                break

            # Bu an hangi senaryo cümlesine denk geliyor?
            mid_pt = current_time + (beat_dur / 2.0)
            active_sc_idx = 0
            active_sc_text = ""
            for s_i, (s_start, s_end, s_txt) in enumerate(scene_durations):
                if s_start <= mid_pt <= s_end:
                    active_sc_idx = s_i
                    active_sc_text = s_txt
                    break
            else:
                active_sc_idx = min(len(scenes) - 1, int(cut_i * len(scenes) / total_cuts))
                active_sc_text = (scenes[active_sc_idx].get("narration") or "").strip()

            # Beat için cümle içi alt ifadeyi çıkart
            words = active_sc_text.split()
            beat_phrase = self._extract_beat_phrase(words, cut_i, total_cuts, len(scenes), active_sc_idx)

            # Varlık kategorisi seç (Anti-Clustering: max_consecutive_same_entity: 1)
            avail_cats = [c for c in ENTITY_CATEGORIES if c != last_entity_category]
            entity_cat = avail_cats[(cut_i) % len(avail_cats)]
            last_entity_category = entity_cat

            # Kamera hareketi
            cam_motion = CAMERA_MOTIONS[cut_i % len(CAMERA_MOTIONS)]

            # Altyazı görünümü ve öksüz kelime koruması
            sub_display = self._format_subtitle_display(beat_phrase)

            # Semantik arama sorgusu ve negatif anahtar kelimeleri derle
            prim_q, fall_q, scene_neg = self._compile_scene_queries(
                domain_type=domain_type,
                scene_num=active_sc_idx,
                beat_idx=cut_i,
                beat_phrase=beat_phrase,
                entity_cat=entity_cat,
                global_prefix=global_prefix,
                topic=topic
            )

            timeline_scenes.append({
                "scene_index": cut_i,
                "start_sec": round(current_time, 2),
                "end_sec": round(beat_end, 2),
                "audio_phrase": beat_phrase,
                "visual_entity_category": entity_cat,
                "primary_search_query": prim_q,
                "fallback_search_query": fall_q,
                "negative_keywords": scene_neg,
                "camera_motion": cam_motion,
                "subtitle_display": sub_display
            })

            current_time = beat_end
            if current_time >= total_duration:
                break

        # 4. JSON Schema Sözleşmesi Çıktısı
        cta_start = max(0.0, round(total_duration - 4.5, 2))
        cta_end = round(total_duration, 2)

        schema_payload = {
            "project_meta": {
                "topic": topic,
                "category_badge": domain_meta["category_badge"],
                "badge_display_window": domain_meta["badge_display_window"],
                "global_domain_prefix": global_prefix,
                "global_negative_keywords": global_neg
            },
            "timeline_scenes": timeline_scenes,
            "ui_elements": {
                "cta_button": {
                    "type": "subscribe",
                    "start_sec": cta_start,
                    "end_sec": cta_end,
                    "position_y": 0.82
                }
            }
        }

        return schema_payload

    def _extract_beat_phrase(self, words: List[str], cut_i: int, total_cuts: int, num_scenes: int, sc_idx: int) -> str:
        """Cümleyi ritmik parçalara böler."""
        if not words:
            return "EXCLUSIVE DISCOVERY"
        cuts_per_scene = max(1, total_cuts // max(1, num_scenes))
        intra_idx = cut_i % cuts_per_scene
        words_per_beat = max(3, len(words) // cuts_per_scene)
        w_start = intra_idx * words_per_beat
        w_end = min(len(words), w_start + words_per_beat)
        if intra_idx == cuts_per_scene - 1:
            w_end = len(words)
        chunk = words[w_start:w_end]
        if not chunk:
            chunk = words[-3:]
        return " ".join(chunk)

    def _format_subtitle_display(self, phrase: str) -> Dict[str, str]:
        """Anti-orphan ve birleşik sıfat korumalı altyazı formatlar."""
        words = phrase.strip().split()
        if not words:
            return {"text": "DISCOVER MORE", "highlight_word": "DISCOVER"}

        # 2-4 kelimelik kompakt gösterim
        display_words = words[:4]
        highlight = display_words[-1].upper().replace(",", "").replace(".", "").replace("!", "").replace("?", "")
        text_str = " ".join(display_words).upper()
        return {
            "text": text_str,
            "highlight_word": highlight
        }

    def _compile_scene_queries(
        self,
        domain_type: str,
        scene_num: int,
        beat_idx: int,
        beat_phrase: str,
        entity_cat: str,
        global_prefix: str,
        topic: str
    ) -> Tuple[str, str, str]:
        """Her kesme için çapa garantili sorguları ve sahne bazlı negatifleri üretir."""
        p_lower = beat_phrase.lower()

        # A) Antik Yeraltı Şehirleri (Derinkuyu / Kapadokya)
        if domain_type == "ancient_mysteries":
            negatives = (
                "modern clothes, blue painted door, apartment door, wooden house door, iron knocker, "
                "red convertible car, woman in dress, influencer model, tourist crowd, modern stairs, "
                "cctv camera, surveillance, fluorescent lighting, cables, red brick arch, gothic church"
            )

            # Sahne 0: Peri Bacaları & Volkanik Yeryüzü Açılışı
            if scene_num == 0 or any(w in p_lower for w in ["fairy chimneys", "cappadocia", "bizarre", "secret"]):
                if beat_idx % 2 == 0:
                    return (
                        "Cappadocia fairy chimneys landscape Goreme twilight badlands",
                        "Goreme valley Cappadocia fairy chimneys sunset rock",
                        f"{negatives}, red car, convertible, woman in dress, tourist, balloons"
                    )
                else:
                    return (
                        "Cappadocia rock formations sunset landscape geological valley",
                        "Cappadocia Chimneys Wikimedia Commons landscape",
                        f"{negatives}, influencer, model, dress, city street"
                    )

            # Sahne 1: 2800 Yıl Önce Oyulan Yeraltı Şehri & 20.000 Kişi
            elif scene_num == 1 or any(w in p_lower for w in ["twenty-eight hundred", "derinkuyu", "descended", "twenty thousand", "sheltering"]):
                if beat_idx % 2 == 0:
                    return (
                        "Derinkuyu Underground City carved volcanic rock rooms Türkiye",
                        "ancient subterranean carved rock halls chambers Derinkuyu",
                        f"{negatives}, brick walls, red brick, gothic arch, modern cellar"
                    )
                else:
                    return (
                        "Kaymakli underground city carved rooms tunnels volcanic stone",
                        "Derinkuyu underground city stone halls rooms depth",
                        f"{negatives}, modern cellar, wine bottles, restaurant"
                    )

            # Sahne 2: Dikey Havalandırma Bacaları & Şarap Ezme Alanları
            elif scene_num == 2 or any(w in p_lower for w in ["ventilation", "shafts", "groundwater", "stables", "wine press"]):
                if any(w in p_lower for w in ["ventilation", "shaft"]):
                    return (
                        "Derinkuyu underground city vertical ventilation shaft tunnel depth",
                        "Derinkuyu underground city carved rock shaft well",
                        f"{negatives}, outdoor wooden railing, modern tourist stairs, trees, sky"
                    )
                else:
                    return (
                        "Derinkuyu underground city carved stone wine press room stable",
                        "Kaymakli underground city tunnel corridor carved rock",
                        f"{negatives}, modern wooden barrel, modern machinery"
                    )

            # Sahne 3: 500 Kiloluk Değirmen Taşı Kapılar (Anti-Clustering ile perspektif rotasyonu)
            elif scene_num == 3 or any(w in p_lower for w in ["stone door", "rolling", "five-hundred", "kilo", "sealed", "doors"]):
                beat_offset = beat_idx % 4
                if beat_offset == 0:
                    return (
                        "Derinkuyu rolling stone door underground city circular disc stone",
                        "ancient round stone door derinkuyu millstone wheel",
                        f"{negatives}, blue door, painted door, apartment door, wooden door, neoclassical, glass door, modern handle"
                    )
                elif beat_offset == 1:
                    return (
                        "Kaymakli underground city narrow stone corridor sealed barrier rock",
                        "Derinkuyu underground city carved stone passageway defensive tunnel",
                        f"{negatives}, brick walls, modern cellar, wooden door"
                    )
                elif beat_offset == 2:
                    return (
                        "A circular door at Kaymakli Underground City stone millstone wheel",
                        "Derinkuyu underground city circular stone door defence mechanism",
                        f"{negatives}, blue painted door, apartment door, modern street door"
                    )
                else:
                    return (
                        "ancient subterranean impenetrable fortress carved volcanic chambers",
                        "Derinkuyu underground city defensive halls shelter depth",
                        f"{negatives}, modern cellar, gothic church"
                    )

            # Sahne 4: Gizem & Derin Tüneller Kapanışı (Anti-Clustering ile perspektif rotasyonu)
            else:
                beat_offset = beat_idx % 4
                if beat_offset == 0:
                    return (
                        "Derinkuyu underground city carved stone chambers depth layers",
                        "ancient subterranean carved rock halls chambers Derinkuyu",
                        f"{negatives}, cctv, camera, surveillance, security camera on wall, electric light bulbs"
                    )
                elif beat_offset == 1:
                    return (
                        "underground city stone stairs descending deep cavern darkness",
                        "Derinkuyu underground city descending stone staircase tunnel",
                        f"{negatives}, cctv, security camera, cables, modern lighting"
                    )
                elif beat_offset == 2:
                    return (
                        "Derinkuyu underground city corridor depth carved rock mystery",
                        "underground city cave carved tunnel Cappadocia subterranean passageway",
                        f"{negatives}, cctv, camera, surveillance, modern lighting"
                    )
                else:
                    return (
                        "ancient troglodyte subterranean architecture volcanic rock tunnel",
                        "Kaymakli underground city carved rooms tunnels volcanic stone",
                        f"{negatives}, cctv, security camera, cables"
                    )

        # B) Havacılık & Uçak İçi (Aviation)
        elif domain_type == "aviation":
            negatives = (
                "train, subway, bus, bright sunlight, blue sky, day, smiling passengers, "
                "vintage propeller plane, museum exhibit, flight simulator render, warplane"
            )
            beat_offset = beat_idx % 4
            if scene_num == 0 or any(w in p_lower for w in ["dim", "lights", "landing", "night"]):
                if beat_offset == 0:
                    return (
                        "commercial airplane cabin interior dim lighting night flight",
                        "Boeing 737 cabin night dark landing approach",
                        f"{negatives}, daylight, bright sun"
                    )
                elif beat_offset == 1:
                    return (
                        "commercial airliner passenger cabin darkness night descent",
                        "aircraft cabin dim ambient lighting night approach",
                        f"{negatives}, smiling passengers, daylight"
                    )
                elif beat_offset == 2:
                    return (
                        "airplane window night view runway approach lights descent",
                        "commercial airliner wing night city lights approach",
                        f"{negatives}, blue sky, sunny"
                    )
                else:
                    return (
                        "airport runway night approach lights commercial aviation",
                        "commercial airliner illuminated runway night tarmac",
                        f"{negatives}, daylight, sunny"
                    )
            elif any(w in p_lower for w in ["eyes", "pupil", "adjust", "darkness", "seconds"]):
                if beat_offset == 0:
                    return (
                        "commercial aircraft cabin aisle darkness night",
                        "airplane passenger cabin dim interior night flight",
                        f"{negatives}, eye close up, macro eye, pupil, iris"
                    )
                elif beat_offset == 1:
                    return (
                        "airplane window night flight sky view stars lights",
                        "commercial airliner illuminated night tarmac approach",
                        f"{negatives}, eye close up, macro eye, pupil"
                    )
                else:
                    return (
                        "commercial airplane interior cabin aisle night perspective",
                        "aircraft cabin night lighting passenger rows",
                        f"{negatives}, macro eye, pupil"
                    )
            elif any(w in p_lower for w in ["emergency", "evacuate", "path", "evacuation"]):
                if beat_offset == 0:
                    return (
                        "aircraft emergency exit path lighting dark cabin floor",
                        "commercial airplane floor emergency path light night",
                        f"{negatives}, smoke, burning, crash"
                    )
                elif beat_offset == 1:
                    return (
                        "commercial airplane emergency overwing exit door interior",
                        "aircraft emergency exit row interior night flight",
                        f"{negatives}, exterior crash, fire"
                    )
                else:
                    return (
                        "commercial aircraft aisle floor emergency lighting perspective",
                        "aircraft cabin darkness floor escape path lights",
                        f"{negatives}, smoke, fire"
                    )
            else:
                if beat_offset == 0:
                    return (
                        "commercial airliner illuminated runway night tarmac landing",
                        "airport runway night approach lights commercial aviation",
                        f"{negatives}, daylight, sunny"
                    )
                else:
                    return (
                        "commercial airplane night landing approach runway lights",
                        "commercial airliner wing night descent city lights",
                        f"{negatives}, sunny, blue sky"
                    )

        # C) Lüks Seyahat (Budget Luxury)
        elif domain_type == "luxury_travel":
            negatives = (
                "iceland, crater lake, snow, cold, glacier, nordic, cold mountains, "
                "las vegas, casino, mandalay bay, eiffel tower, paris, cheap motel, "
                "suburban house, radiator, dirty street, winter"
            )
            beat_offset = beat_idx % 4
            if any(w in p_lower for w in ["villa", "pool", "private", "cliffside", "suite"]):
                if beat_offset == 0:
                    return (
                        "bali luxury private pool villa tropical ocean view",
                        "tropical resort infinity pool luxury palm trees",
                        f"{negatives}, indoor pool, plastic cover"
                    )
                elif beat_offset == 1:
                    return (
                        "vietnam hillside luxury villa infinity pool ocean view",
                        "luxury villa balcony tropical lagoon ocean",
                        f"{negatives}, cold, snow"
                    )
                elif beat_offset == 2:
                    return (
                        "sri lanka luxury tea plantation hillside resort balcony view",
                        "tropical mountain luxury suite balcony view jungle",
                        f"{negatives}, snow, iceland"
                    )
                else:
                    return (
                        "tropical island sunset pool villa private veranda ocean",
                        "luxury tropical resort infinity pool twilight",
                        f"{negatives}, cold, city"
                    )
            elif any(w in p_lower for w in ["massage", "spa", "therapy", "relax"]):
                if beat_offset == 0:
                    return (
                        "traditional herbal massage spa therapy luxury wellness",
                        "luxury spa herbal compress ball massage resort",
                        f"{negatives}, medical clinic, hospital"
                    )
                else:
                    return (
                        "bali tropical resort stone path traditional umbrellas garden",
                        "luxury tropical spa wellness retreat pool",
                        f"{negatives}, city, traffic"
                    )
            elif any(w in p_lower for w in ["dinner", "dining", "seafood", "meal", "chef", "gourmet", "restaurant"]):
                if beat_offset == 0:
                    return (
                        "luxury beachfront dining candlelight tropical resort ocean sunset",
                        "candlelight beach dinner tropical resort ocean",
                        f"{negatives}, fast food, hamburger, greasy plate"
                    )
                else:
                    return (
                        "fresh gourmet seafood platter fine dining tropical restaurant",
                        "tropical beachfront restaurant evening dining luxury",
                        f"{negatives}, dirty table, diner"
                    )
            else:
                if beat_offset == 0:
                    return (
                        "tropical luxury resort wooden walkway ocean turquoise water",
                        "wooden deck ocean sunset traveler tropical island",
                        f"{negatives}, cold, snow, iceland"
                    )
                elif beat_offset == 1:
                    return (
                        "vietnam beachfront resort tropical luxury sunset palms",
                        "tropical island turquoise lagoon beach luxury resort",
                        f"{negatives}, cold, snow"
                    )
                elif beat_offset == 2:
                    return (
                        "bali tropical resort stone path traditional umbrellas garden",
                        "luxury tropical resort garden stone path palms",
                        f"{negatives}, cold, snow, iceland"
                    )
                else:
                    return (
                        "tropical resort wooden walkway ocean sunset traveler",
                        "luxury private villa veranda tropical garden view",
                        f"{negatives}, cold, snow"
                    )

        # Varsayılan
        return (
            f"{global_prefix} {beat_phrase}",
            f"{global_prefix} cinematic 4k",
            UNIVERSAL_NEGATIVES
        )


visual_director = VisualDirector()
