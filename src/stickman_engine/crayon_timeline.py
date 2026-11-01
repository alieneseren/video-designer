import re
from datetime import date
from urllib.parse import urlparse


MIN_DURATION_SEC = 360.0
MAX_DURATION_SEC = 420.0
MAX_SHOT_DURATION_SEC = 5.0
MIN_VOICEOVER_WORDS = 850
MAX_VOICEOVER_WORDS = 950

VISUAL_ASSETS = {
    "documentary_object",
    "simple_schematic",
    "material_closeup",
    "public_document",
    "sourced_data_chart",
    "timeline",
    "engineering_comparison",
    "character_reaction",
}

SFX_ASSETS = {
    "impact": "impact.mp3",
    "marker_scribble": "marker_scribble.wav",
    "document_stamp": "stamp.wav",
    "cash_register": "cash_register.wav",
    "radio_click": "click.mp3",
    "comic_boing": "cartoon_boing.wav",
    "whoosh": "whoosh.mp3",
    "warning_beep": "error.mp3",
    "ping": "ping.mp3",
}

MUSIC_ASSETS = {
    "lofi_storyteller": "lofi_storyteller.mp3",
    "reddit_official_bgm": "reddit_official_bgm.mp3",
}


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w$€£'-]+\b", text, flags=re.UNICODE))


def _valid_source_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return False
    if (
        host in {"example.com", "example.org", "example.net", "localhost"}
        or host.endswith((".example", ".invalid", ".test", ".localhost"))
        or host.endswith((".example.com", ".example.org", ".example.net"))
    ):
        return False
    return "." in host and not host.endswith(".invalid")


def normalize_crayon_timeline(script_data: dict) -> dict:
    if not isinstance(script_data, dict):
        raise ValueError("Crayon Combat senaryosu JSON nesnesi olmalıdır.")

    timeline = script_data.get("timeline_scenes")
    if not isinstance(timeline, list) or not timeline:
        raise ValueError(
            "Crayon Combat için eski scenes biçimi kabul edilmiyor. "
            "Kaynaklı timeline_scenes senaryosunu yeniden oluşturun."
        )

    meta = script_data.get("project_meta")
    if not isinstance(meta, dict):
        raise ValueError("project_meta alanı zorunludur.")
    if str(meta.get("category") or "").strip().lower() not in {"crayon combat", "crayon_combat"}:
        raise ValueError("project_meta.category Crayon Combat olarak belirtilmelidir.")

    target_duration = meta.get("target_duration_sec")
    try:
        target_duration = float(target_duration)
    except (TypeError, ValueError) as exc:
        raise ValueError("project_meta.target_duration_sec sayısal olmalıdır.") from exc
    if not MIN_DURATION_SEC <= target_duration <= MAX_DURATION_SEC:
        raise ValueError("Hedef süre 360-420 saniye arasında olmalıdır.")

    fictional_satire = meta.get("fictional_satire", False)
    if not isinstance(fictional_satire, bool):
        raise ValueError("project_meta.fictional_satire boolean olmalıdır.")
    sources = meta.get("sources")
    if not isinstance(sources, list) or (not sources and not fictional_satire):
        raise ValueError("Gerçek bilgi için project_meta.sources zorunludur; kurgu açıkça işaretlenmelidir.")

    source_ids = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Her kaynak bir JSON nesnesi olmalıdır.")
        source_id = str(source.get("source_id") or "").strip()
        if not source_id or source_id in source_ids:
            raise ValueError("Kaynak source_id değerleri benzersiz ve zorunludur.")
        if not source.get("name") or not _valid_source_url(source.get("url")):
            raise ValueError(f"Kaynak {source_id!r} geçerli bir HTTPS URL ve ad içermelidir.")
        try:
            date.fromisoformat(str(source.get("published_at") or ""))
        except ValueError as exc:
            raise ValueError(f"Kaynak {source_id!r} published_at YYYY-MM-DD biçiminde olmalıdır.") from exc
        source_ids.add(source_id)

    normalized_scenes = []
    total_words = 0
    planned_duration = 0.0
    shot_ids = set()
    scene_ids = set()
    asset_ids = set()
    character_ids = []

    for index, shot in enumerate(timeline):
        if not isinstance(shot, dict):
            raise ValueError(f"timeline_scenes[{index}] nesne olmalıdır.")

        shot_id = str(shot.get("shot_id") or "").strip()
        if not shot_id or shot_id in shot_ids:
            raise ValueError(f"timeline_scenes[{index}].shot_id benzersiz ve zorunludur.")
        shot_ids.add(shot_id)
        scene_id = str(shot.get("scene_id") or f"SCENE_{index + 1:02d}").strip()
        if scene_id in scene_ids:
            raise ValueError(f"{shot_id}: scene_id benzersiz olmalıdır.")
        scene_ids.add(scene_id)

        try:
            duration = float(shot.get("duration_sec"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{shot_id}: duration_sec sayısal olmalıdır.") from exc
        if not 0 < duration <= MAX_SHOT_DURATION_SEC:
            raise ValueError(f"{shot_id}: her görsel kesit 0-5 saniye arasında olmalıdır.")

        narration = str(shot.get("narration_script") or "").strip()
        words = _word_count(narration)
        if not narration or words == 0:
            raise ValueError(f"{shot_id}: narration_script boş olamaz.")
        total_words += words

        source_refs = shot.get("source_refs")
        if not isinstance(source_refs, list) or (not source_refs and not fictional_satire):
            raise ValueError(f"{shot_id}: olgusal anlatım en az bir source_refs içermelidir.")
        if any(source_ref not in source_ids for source_ref in source_refs):
            raise ValueError(f"{shot_id}: source_refs içinde tanımsız kaynak var.")

        visual = shot.get("visual")
        primary_asset = visual.get("primary_asset") if isinstance(visual, dict) else None
        if not isinstance(primary_asset, dict) or primary_asset.get("type") not in VISUAL_ASSETS:
            raise ValueError(f"{shot_id}: izin verilen bir primary_asset.type belirtilmelidir.")
        primary_asset_id = str(primary_asset.get("asset_id") or "").strip()
        if not primary_asset_id:
            raise ValueError(f"{shot_id}: primary_asset.asset_id zorunludur.")
        if primary_asset_id in asset_ids:
            raise ValueError(f"{shot_id}: her görsel varlığın asset_id değeri benzersiz olmalıdır.")
        asset_ids.add(primary_asset_id)
        if visual.get("engine") != "pillow_ffmpeg":
            raise ValueError(f"{shot_id}: visual.engine pillow_ffmpeg olmalıdır.")
        b_roll = visual.get("b_roll")
        if not isinstance(b_roll, dict) or not b_roll.get("source") or not b_roll.get("asset_id"):
            raise ValueError(f"{shot_id}: visual.b_roll için source ve asset_id zorunludur.")
        b_roll_asset_id = str(b_roll["asset_id"]).strip()
        if b_roll_asset_id in asset_ids:
            raise ValueError(f"{shot_id}: her görsel varlığın asset_id değeri benzersiz olmalıdır.")
        asset_ids.add(b_roll_asset_id)
        text_badge = str(b_roll.get("text_badge") or "").strip()
        if text_badge and _word_count(text_badge) > 7:
            raise ValueError(f"{shot_id}: ekrandaki kısa görsel metni en fazla 7 kelime olabilir.")

        character_layer = shot.get("character_layer")
        if not isinstance(character_layer, dict):
            raise ValueError(f"{shot_id}: character_layer zorunludur.")
        if character_layer.get("active") is not True:
            raise ValueError(f"{shot_id}: her kesitte karakter ve konuşma balonu etkin olmalıdır.")
        character_id = str(character_layer.get("character_id") or "PILOT").strip().upper()
        if (
            fictional_satire
            and len(character_ids) >= 2
            and character_ids[-1] == character_id
            and character_ids[-2] == character_id
        ):
            raise ValueError(
                f"{shot_id}: fictional satire için aynı karakter art arda üç kesitte kullanılamaz."
            )
        character_ids.append(character_id)
        bubble = str(character_layer.get("bubble_dialogue") or "").strip()
        bubble_words = _word_count(bubble)
        if not 3 <= bubble_words <= 8:
            raise ValueError(f"{shot_id}: konuşma balonu 3-8 kelime olmalıdır.")
        if bubble.lower() in narration.lower() or narration.lower() in bubble.lower():
            raise ValueError(f"{shot_id}: konuşma balonu anlatım metnini tekrar edemez.")

        audio_cues = shot.get("audio_cues")
        if not isinstance(audio_cues, dict):
            raise ValueError(f"{shot_id}: audio_cues zorunludur.")
        sfx = audio_cues.get("sfx")
        if not isinstance(sfx, list) or not sfx:
            raise ValueError(f"{shot_id}: her kesitte en az bir desteklenen SFX tetikleyicisi olmalıdır.")
        unknown_sfx = [cue for cue in sfx if cue not in SFX_ASSETS]
        if unknown_sfx:
            raise ValueError(f"{shot_id}: desteklenmeyen SFX: {', '.join(map(str, unknown_sfx))}.")

        music_track = audio_cues.get("music_track")
        if music_track not in MUSIC_ASSETS:
            raise ValueError(f"{shot_id}: music_track yerel müzik varlıklarından biri olmalıdır.")
        music_cut = audio_cues.get("music_cut")
        if not isinstance(music_cut, bool):
            raise ValueError(f"{shot_id}: music_cut boolean olmalıdır.")
        cut_duration = audio_cues.get("music_cut_duration_sec", 1.5)
        try:
            cut_duration = float(cut_duration)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{shot_id}: music_cut_duration_sec sayısal olmalıdır.") from exc
        if music_cut and not 1.0 <= cut_duration <= 2.0:
            raise ValueError(f"{shot_id}: müzik kesintisi 1-2 saniye olmalıdır.")
        if music_cut and "music_cut_duration_sec" not in audio_cues:
            raise ValueError(f"{shot_id}: music_cut true ise music_cut_duration_sec belirtilmelidir.")

        normalized_scenes.append({
            "scene_id": scene_id,
            "shot_id": shot_id,
            "chapter": shot.get("chapter") or "",
            "narration": narration,
            "character": character_id,
            "character_dialogue": bubble,
            "character_active": bool(character_layer.get("active", False)),
            "character_position": character_layer.get("screen_position") or "bottom_right",
            "visual_type": primary_asset["type"],
            "visual": visual,
            "source_refs": source_refs,
            "sources": sources,
            "fictional_satire": fictional_satire,
            "audio_cues": audio_cues,
            "sfx": sfx,
            "music_track": music_track,
            "music_cut": music_cut,
            "music_cut_duration_sec": cut_duration,
            "duration_sec": duration,
            "_structured_timeline": True,
        })
        planned_duration += duration

    if abs(planned_duration - target_duration) > 0.5:
        raise ValueError(
            f"Kesit süreleri toplamı {planned_duration:.1f}s; "
            f"project_meta hedefi {target_duration:.1f}s ile eşleşmiyor."
        )

    if not MIN_VOICEOVER_WORDS <= total_words <= MAX_VOICEOVER_WORDS:
        raise ValueError(f"Seslendirme 850-950 kelime olmalıdır; mevcut: {total_words}.")
    declared_words = meta.get("total_words")
    if not isinstance(declared_words, int) or abs(declared_words - total_words) > 2:
        raise ValueError(
            f"project_meta.total_words gerçek seslendirme kelime sayısıyla eşleşmiyor "
            f"({total_words})."
        )

    result = dict(script_data)
    result["title"] = meta.get("title") or script_data.get("title") or "Crayon Combat"
    result["project_meta"] = meta
    result["scenes"] = normalized_scenes
    result["_structured_timeline"] = True
    result["_planned_duration_sec"] = planned_duration
    result["_voiceover_words"] = total_words
    return result
