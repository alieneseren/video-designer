import json
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
from types import ModuleType
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def _assert_raises(exception_type, expected_message, callback):
    try:
        callback()
    except exception_type as exc:
        assert expected_message in str(exc)
    else:
        raise AssertionError(f"Expected {exception_type.__name__}: {expected_message}")

from crayon_combat_engine import CURATED_CRAYON_COMBAT_TOPICS
from channel_manager import get_category_preset
from crayon_combat_engine import CRAYON_COMBAT_SYSTEM_PROMPT
from financial_documentary_engine import TECH_FINANCE_SYSTEM_PROMPT
from script_writer import _build_prompt, _crayon_timeline_response_schema, _enrich_script_metadata
from stickman_engine.crayon_animation_pipeline import (
    H,
    W,
    _crayon_story_family,
    _crayon_story_subshots,
    _crayon_visual_kind,
    _short_visual_phrase,
    render_crayon_kinetic_shot,
    render_crayon_story_shot,
    select_scene_subshots,
    set_current_channel_id,
)
from stickman_engine.crayon_generator import (
    _create_crayon_thumbnail,
    _is_valid_rendered_clip,
    _timeline_music_volume_expression,
)
from stickman_engine.crayon_timeline import normalize_crayon_timeline


def test_tactical_crayon_duration_and_fact_safe_topics():
    channels = json.loads((PROJECT_ROOT / "config" / "channels.json").read_text(encoding="utf-8"))["channels"]
    channel = next(item for item in channels if item.get("channel_id") == "tacticallcrayon")
    assert channel["edit_options"]["video_duration"] == "390"
    preset = get_category_preset("crayon_combat", language="en", channel_name="Tactical Crayon")
    assert preset["edit_options"]["video_duration"] == "390"
    finance_preset = get_category_preset("crayon_capital", language="en")
    assert finance_preset["edit_options"]["video_duration"] == "420"
    assert all("cost" not in topic for topic in CURATED_CRAYON_COMBAT_TOPICS)
    assert all(topic.get("investigation_angle") for topic in CURATED_CRAYON_COMBAT_TOPICS)
    assert "390 seconds" in CRAYON_COMBAT_SYSTEM_PROMPT
    assert "850-950 narration words" in CRAYON_COMBAT_SYSTEM_PROMPT
    assert "fictional satire" in CRAYON_COMBAT_SYSTEM_PROMPT
    assert "procurement databases" in CRAYON_COMBAT_SYSTEM_PROMPT
    assert "6-8 minutes" in TECH_FINANCE_SYSTEM_PROMPT
    assert "4-6 seconds" in TECH_FINANCE_SYSTEM_PROMPT
    assert ".example" not in CRAYON_COMBAT_SYSTEM_PROMPT


def _valid_crayon_timeline():
    source = {
        "source_id": "src_1",
        "name": "U.S. Government Accountability Office",
        "url": "https://www.gao.gov/",
        "published_at": "2024-01-31",
    }
    shots = []
    for idx in range(78):
        shots.append({
            "scene_id": f"SCENE_{idx + 1:02d}",
            "shot_id": f"SHOT_{idx + 1:02d}",
            "chapter": "EVIDENCE",
            "duration_sec": 5.0,
            "narration_script": (
                "This source documents the engineering choice and explains its public context clearly."
            ),
            "source_refs": ["src_1"],
            "visual": {
                "engine": "pillow_ffmpeg",
                "layout": "full_frame_editorial",
                "primary_asset": {
                    "type": "documentary_object",
                    "asset_id": f"abstract_aircraft_detail_{idx}",
                    "animation": "slow_zoom_in",
                },
                "b_roll": {
                    "source": "vector_illustration",
                    "asset_id": f"engineering_detail_{idx}",
                    "text_badge": "PUBLIC RECORD",
                },
            },
            "character_layer": {
                "active": True,
                "character_id": ["PILOT", "GENERAL", "DEFENSE_CEO", "SPY"][idx % 4],
                "pose": "concerned",
                "bubble_dialogue": "Budget says try again!",
                "screen_position": "bottom_right",
            },
            "audio_cues": {
                "sfx": ["impact"],
                "music_track": "lofi_storyteller" if idx % 2 == 0 else "reddit_official_bgm",
                "music_cut": idx == 2,
                "music_cut_duration_sec": 1.5,
            },
        })
    return {
        "project_meta": {
            "category": "Crayon Combat",
            "title": "A Source-Grounded Engineering Story",
            "target_duration_sec": 390,
            "total_words": 936,
            "sources": [source],
        },
        "timeline_scenes": shots,
    }


def test_crayon_timeline_enforces_duration_words_sources_and_bubbles():
    normalized = normalize_crayon_timeline(_valid_crayon_timeline())
    assert normalized["_planned_duration_sec"] == 390
    assert normalized["_voiceover_words"] == 936
    assert len(normalized["scenes"]) == 78
    assert normalized["scenes"][0]["character_active"] is True

    invalid = _valid_crayon_timeline()
    invalid["timeline_scenes"][0]["duration_sec"] = 5.1
    _assert_raises(
        ValueError,
        "0-5 saniye",
        lambda: normalize_crayon_timeline(invalid),
    )

    invalid = _valid_crayon_timeline()
    invalid["timeline_scenes"][0]["character_layer"]["bubble_dialogue"] = (
        "This bubble has nine words and exceeds the allowed limit"
    )
    _assert_raises(
        ValueError,
        "3-8 kelime",
        lambda: normalize_crayon_timeline(invalid),
    )

    invalid = _valid_crayon_timeline()
    invalid["timeline_scenes"][0]["source_refs"] = ["missing"]
    _assert_raises(
        ValueError,
        "tanımsız kaynak",
        lambda: normalize_crayon_timeline(invalid),
    )

    invalid = _valid_crayon_timeline()
    invalid["timeline_scenes"][1]["visual"]["primary_asset"]["asset_id"] = (
        invalid["timeline_scenes"][0]["visual"]["primary_asset"]["asset_id"]
    )
    _assert_raises(
        ValueError,
        "asset_id değeri benzersiz",
        lambda: normalize_crayon_timeline(invalid),
    )

    _assert_raises(
        ValueError,
        "eski scenes biçimi",
        lambda: normalize_crayon_timeline({"scenes": [{"narration": "legacy"}]}),
    )

    fictional = _valid_crayon_timeline()
    fictional["project_meta"]["fictional_satire"] = True
    fictional["project_meta"]["sources"] = []
    for shot in fictional["timeline_scenes"]:
        shot["source_refs"] = []
    assert normalize_crayon_timeline(fictional)["_voiceover_words"] == 936

    repeated_character = _valid_crayon_timeline()
    repeated_character["project_meta"]["fictional_satire"] = True
    for shot in repeated_character["timeline_scenes"][:3]:
        shot["character_layer"]["character_id"] = "PILOT"
    _assert_raises(
        ValueError,
        "art arda üç kesitte",
        lambda: normalize_crayon_timeline(repeated_character),
    )

    factual_without_sources = _valid_crayon_timeline()
    factual_without_sources["project_meta"]["sources"] = []
    _assert_raises(
        ValueError,
        "project_meta.sources",
        lambda: normalize_crayon_timeline(factual_without_sources),
    )


def test_crayon_audio_cues_use_shot_tracks_and_pre_reveal_cut():
    scenes = [
        {"start_time": 0, "duration": 5, "music_track": "lofi_storyteller"},
        {
            "start_time": 5,
            "duration": 5,
            "music_track": "reddit_official_bgm",
            "music_cut": True,
            "music_cut_duration_sec": 1.5,
        },
    ]
    expression = _timeline_music_volume_expression(scenes, "lofi_storyteller", 0.04)
    assert "between(t\\,3.500\\,5.000)\\,0" in expression
    assert "between(t\\,0.000\\,5.000)\\,1" in expression


def test_crayon_generator_reuses_only_valid_rendered_clips():
    with tempfile.TemporaryDirectory(prefix="crayon-clip-resume-") as temp:
        valid_clip = Path(temp) / "valid.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x123456:s=160x90:d=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(valid_clip),
            ],
            capture_output=True,
            check=True,
        )
        invalid_clip = Path(temp) / "invalid.mp4"
        invalid_clip.write_bytes(b"not a video file" * 200)

        assert _is_valid_rendered_clip(valid_clip)
        assert not _is_valid_rendered_clip(invalid_clip)
        assert not _is_valid_rendered_clip(Path(temp) / "missing.mp4")


def test_structured_timeline_selects_the_requested_visual():
    set_current_channel_id("tacticallcrayon", "crayon_combat")
    try:
        shots, labels = select_scene_subshots(
            {
                "_structured_timeline": True,
                "shot_id": "DOC_01",
                "visual": {
                    "primary_asset": {"type": "public_document", "asset_id": "document_page"},
                },
            },
            idx=3,
            dur=5.0,
            vehicle_name="Tactical Crayon",
        )
    finally:
        set_current_channel_id("")
    assert shots == ["CRAYON_STORY_LAB", "CRAYON_STORY_MARKING"]
    assert labels == ["DOC_01", "DOC_01"]

    set_current_channel_id("", "crayon_capital")
    try:
        capital_shots, _ = select_scene_subshots(
            {
                "_structured_timeline": True,
                "shot_id": "CAPITAL_01",
                "visual": {
                    "primary_asset": {"type": "sourced_data_chart", "asset_id": "cash_flow_chart"},
                },
            },
            idx=0,
            dur=5.0,
            vehicle_name="Company cash flow",
        )
    finally:
        set_current_channel_id("")
    assert capital_shots[0] == "CRAYON_HOOK"
    assert all(not shot.startswith("CRAYON_STORY_") for shot in capital_shots)


def test_crayon_gemini_schema_uses_timeline_contract():
    class Type:
        OBJECT = "OBJECT"
        ARRAY = "ARRAY"
        STRING = "STRING"
        NUMBER = "NUMBER"
        INTEGER = "INTEGER"
        BOOLEAN = "BOOLEAN"

    class Schema:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Types:
        pass

    Types.Type = Type
    Types.Schema = Schema

    schema = _crayon_timeline_response_schema(Types)
    assert "timeline_scenes" in schema.properties
    assert "scenes" not in schema.properties
    assert "fictional_satire" in schema.properties["project_meta"].properties
    fake_settings = ModuleType("settings_manager")

    class FakeSettingsManager:
        def get(self, key):
            return None

    fake_settings.SettingsManager = FakeSettingsManager
    with patch.dict(sys.modules, {"settings_manager": fake_settings}):
        prompt, _, _ = _build_prompt(
            {
                "channel_id": "tacticallcrayon",
                "topic_category": "crayon_combat",
                "language": "en",
                "shorts_mode": False,
                "edit_options": {"video_duration": "390"},
            },
            "A sourced military engineering story",
        )
    assert "Exactly 78 timeline_scenes" in prompt
    assert "850-950 words" in prompt
    assert "fictional satire" in prompt
    assert "procurement databases" in prompt
    assert "project_meta.fictional_satire=true" in prompt
    assert _crayon_visual_kind("f16_cockpit_rudder_assembly") == "aircraft"
    assert _crayon_visual_kind("melting_wax_macro") == "marker"


def test_crayon_metadata_and_visual_selection():
    script = _enrich_script_metadata(
        {"title": "Combat Markings: The Detail Everyone Misses", "topic": "Combat Markings"},
        {"topic_category": "crayon_combat", "language": "en"},
    )
    assert len(script["title_variants"]) == 3
    assert all(len(option["title"]) < 75 for option in script["title_variants"])
    assert 2 <= len(script["thumbnail_text"].split()) <= 4

    set_current_channel_id("tacticallcrayon")
    try:
        shots, labels = select_scene_subshots(
            {
                "chapter": "A careful review",
                "narration": "This fictional example mentions a $54.8 billion marker only to test visual selection.",
            },
            idx=0,
            dur=20.0,
            vehicle_name="Tactical Crayon",
        )
    finally:
        set_current_channel_id("")
    assert shots == ["CRAYON_HOOK", "CRAYON_VISUAL", "CRAYON_EVIDENCE", "CRAYON_REACTION"]
    assert labels == shots

    set_current_channel_id("", "crayon_capital")
    try:
        finance_shots, finance_labels = select_scene_subshots(
            {"chapter": "Cash flow", "narration": "Follow the verified cash flow."},
            idx=0,
            dur=15.0,
            vehicle_name="A public company",
        )
    finally:
        set_current_channel_id("")
    assert len(finance_shots) == 3
    assert len(set(finance_shots)) == 3
    assert finance_labels == finance_shots
    assert _short_visual_phrase("One two three four five six seven eight", 6) == "One two three four five six"

    rendered_frames = []
    for shot_type in ("CRAYON_HOOK", "CRAYON_VISUAL", "CRAYON_EVIDENCE", "CRAYON_REACTION"):
        frame = Image.new("RGBA", (W, H), (15, 23, 42, 255))
        render_crayon_kinetic_shot(
            frame,
            ImageDraw.Draw(frame),
            {
                "chapter": "Cold open",
                "narration": "The documented surprise changes the engineering trade-off.",
                "character_dialogue": "That changes the whole argument.",
                "character_active": True,
                "character_position": "bottom_right",
                "visual": {
                    "primary_asset": {"type": "documentary_object", "asset_id": "abstract_aircraft"},
                    "b_roll": {"text_badge": "SOURCED DETAIL"},
                },
            },
            shot_type,
            1.0,
            5.0,
            Image.new("RGBA", (100, 100), (200, 50, 50, 255)),
            "crayon_combat",
        )
        rendered_frames.append(frame)
    assert all(
        ImageChops.difference(rendered_frames[0].convert("RGB"), frame.convert("RGB")).getbbox()
        for frame in rendered_frames[1:]
    )


def test_tactical_story_visuals_follow_the_narration_and_change_within_four_seconds():
    cockpit_scene = {
        "narration": "The melted wax jams the F-16 rudder pedal in the cockpit.",
        "chapter": "THE COCKPIT MELTDOWN",
        "visual": {
            "primary_asset": {"asset_id": "f16_cockpit_rudder", "type": "documentary_object"},
            "b_roll": {"asset_id": "melting_wax_marker"},
        },
    }
    tank_scene = {
        "narration": "At Fallujah, a blue arrow on a bakery window catches the crew's attention.",
        "chapter": "THE BLUE ARROW",
        "visual": {"primary_asset": {"asset_id": "tank_window_blue_arrow"}},
    }
    assert _crayon_story_family(cockpit_scene) == "cockpit"
    assert _crayon_story_family(tank_scene) == "tank"
    assert _crayon_story_subshots(cockpit_scene, 5.0, 0) == [
        "CRAYON_STORY_COCKPIT",
        "CRAYON_STORY_WAX",
    ]
    assert len(_crayon_story_subshots(cockpit_scene, 4.0, 0)) == 1
    assert len(_crayon_story_subshots(cockpit_scene, 4.01, 0)) == 2

    rendered = []
    for family in ("CRAYON_STORY_COCKPIT", "CRAYON_STORY_TANK"):
        frame = Image.new("RGBA", (W, H), (15, 23, 42, 255))
        render_crayon_story_shot(
            frame,
            ImageDraw.Draw(frame),
            {
                "chapter": "The absurd moment",
                "character_active": True,
                "character_dialogue": "That is not in the manual!",
                "character_position": "bottom_right",
            },
            family,
            1.0,
            2.5,
            Image.new("RGBA", (100, 120), (200, 50, 50, 255)),
        )
        rendered.append(frame)
    assert ImageChops.difference(rendered[0].convert("RGB"), rendered[1].convert("RGB")).getbbox()


def test_crayon_thumbnail_is_upload_ready():
    with tempfile.TemporaryDirectory(prefix="crayon-thumbnail-test-") as temp:
        root = Path(temp)
        source = root / "source.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x123456:s=1280x720:d=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
            ],
            capture_output=True,
            check=True,
        )
        result = _create_crayon_thumbnail(source, root / "thumbnail.jpg", "MARKING MYSTERY")
        from PIL import Image

        with Image.open(result) as image:
            assert image.size == (1280, 720)
        assert result.stat().st_size > 1000


if __name__ == "__main__":
    test_tactical_crayon_duration_and_fact_safe_topics()
    test_crayon_timeline_enforces_duration_words_sources_and_bubbles()
    test_crayon_audio_cues_use_shot_tracks_and_pre_reveal_cut()
    test_crayon_generator_reuses_only_valid_rendered_clips()
    test_structured_timeline_selects_the_requested_visual()
    test_crayon_gemini_schema_uses_timeline_contract()
    test_crayon_metadata_and_visual_selection()
    test_tactical_story_visuals_follow_the_narration_and_change_within_four_seconds()
    test_crayon_thumbnail_is_upload_ready()
    print("CRAYON RETENTION TESTS PASSED")
