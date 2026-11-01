#!/usr/bin/env python3
"""
crayon_generator.py
===================
Specialized generator for Crayon Combat and military/tech satire channels.
Directly invoked by VideoGenerator when channel topic_category is crayon_combat.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageOps

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if not (BASE_DIR / "assets").exists():
    BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

from stickman_engine.crayon_animation_pipeline import (
    render_animated_scene,
    generate_broadcast_ass_subtitles,
    get_audio_duration,
    get_pop_font,
    FFMPEG_BIN,
    RENDER_CACHE_VERSION,
    W, H, FPS
)
from stickman_engine.crayon_timeline import (
    MAX_DURATION_SEC,
    MAX_SHOT_DURATION_SEC,
    MIN_DURATION_SEC,
    MUSIC_ASSETS,
    SFX_ASSETS,
    normalize_crayon_timeline,
)


def _create_crayon_thumbnail(video_path: Path, output_path: Path, text: str) -> Path:
    frame_path = output_path.with_name("thumbnail_frame.jpg")
    subprocess.run(
        [
            FFMPEG_BIN, "-y", "-ss", "0.5", "-i", str(video_path),
            "-frames:v", "1", "-q:v", "2", str(frame_path),
        ],
        capture_output=True,
        check=True,
    )
    try:
        with Image.open(frame_path) as frame:
            image = ImageOps.fit(frame.convert("RGB"), (1280, 720))
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rounded_rectangle((30, 28, 420, 92), radius=14, fill=(12, 22, 40, 220))
        draw.rounded_rectangle((34, 532, 1246, 690), radius=22, fill=(8, 15, 28, 205))
        image = Image.alpha_composite(image.convert("RGBA"), overlay)
        draw = ImageDraw.Draw(image)
        draw.text((52, 60), "TACTICAL CRAYON", font=get_pop_font(34), fill=(245, 211, 92, 255), anchor="lm")

        words = re.sub(r"[^A-Za-z0-9' -]", "", text).split()[:4]
        if not words:
            words = ["TACTICAL", "BREAKDOWN"]
        midpoint = (len(words) + 1) // 2
        lines = [" ".join(words[:midpoint])]
        if words[midpoint:]:
            lines.append(" ".join(words[midpoint:]))
        font_size = 76 if max(map(len, lines)) < 15 else 62
        font = get_pop_font(font_size)
        line_y = 582 if len(lines) == 1 else 566
        for line in lines:
            draw.text((640, line_y), line.upper(), font=font, fill=(255, 255, 255, 255), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 210))
            line_y += 66
        image.convert("RGB").save(output_path, "JPEG", quality=92, optimize=True)
    finally:
        frame_path.unlink(missing_ok=True)
    return output_path


def _timeline_music_volume_expression(scenes: list, track: str, volume: float) -> str:
    expression = "0"
    for item in reversed(scenes):
        start = float(item["start_time"])
        end = start + float(item["duration"])
        gain = 1 if item.get("music_track") == track else 0
        expression = (
            f"if(between(t\\,{start:.3f}\\,{end:.3f})\\,{gain}\\,{expression})"
        )

    for item in reversed(scenes):
        if not item.get("music_cut"):
            continue
        shot_start = float(item["start_time"])
        cut_start = max(
            0.0,
            shot_start - float(item.get("music_cut_duration_sec") or 1.5),
        )
        if shot_start > cut_start:
            expression = f"if(between(t\\,{cut_start:.3f}\\,{shot_start:.3f})\\,0\\,{expression})"

    return f"{float(volume):.4f}*({expression})"


def _is_valid_rendered_clip(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 1024:
        return False
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip()) > 0.5
    except (OSError, subprocess.SubprocessError, ValueError):
        return False


def generate_crayon_video(
    channel_config: dict,
    script_data: dict,
    work_dir: Path,
    output_dir: str,
    edit_options: Optional[dict] = None,
    custom_images: Optional[dict] = None,
    lang: str = "en",
    speech_generator=None,
) -> dict:
    """
    Produces broadcast-quality animated Crayon Combat video with animated stickmen,
    tactical blueprints, synchronized ASS subtitles, and background music.
    """
    edit_options = edit_options or {}
    chan_id = channel_config.get("channel_id") or ""
    cat = channel_config.get("topic_category", "crayon_combat")
    is_combat = cat in ("crayon_combat", "military", "military_tech")
    scenes = script_data.get("scenes") or []
    if is_combat and not scenes and "timeline_scenes" in script_data:
        script_data = normalize_crayon_timeline(script_data)
        scenes = script_data.get("scenes") or []
    title = script_data.get("title") or channel_config.get("name") or "Crayon Combat"
    vehicle_name = script_data.get("vehicle_name") or script_data.get("flight_name") or script_data.get("incident_name") or title

    if not scenes:
        raise ValueError("Senaryoda sahne listesi bulunamadı.")
    try:
        from stickman_engine.crayon_animation_pipeline import set_current_channel_id
        set_current_channel_id(chan_id, cat)
    except ImportError:
        from src.stickman_engine.crayon_animation_pipeline import set_current_channel_id
        set_current_channel_id(chan_id, cat)
    if chan_id:
        try:
            from stickman_engine.channel_narrator_factory import ChannelNarratorFactory
            ChannelNarratorFactory.ensure_channel_narrator(
                channel_id=chan_id,
                topic_category=cat,
                channel_name=channel_config.get("name", chan_id)
            )
        except Exception as e_narr:
            print(f"[CRAYON-GEN] Narrator init error: {e_narr}")

    print(f"[CRAYON-GEN] 🎨 Crayon Combat Animasyon Hattı devrede: '{title}' ({len(scenes)} sahne)")
    t0 = time.time()

    # 1. Ses Dosyalarını Kontrol Et veya Üret
    scenes_info = []
    cumulative_time = 0.0

    for i, sc in enumerate(scenes):
        audio_f = work_dir / f"scene_{i}_audio.mp3"
        if not audio_f.exists():
            wav_f = work_dir / f"scene_{i}_audio.wav"
            if wav_f.exists():
                audio_f = wav_f

        # Eğer ses dosyası henüz yoksa TTS ile üret
        if not audio_f.exists() or audio_f.stat().st_size < 1000:
            narration = sc.get("narration") or sc.get("text") or vehicle_name
            produced = False
            if speech_generator:
                generated_path = speech_generator(narration, lang, str(audio_f))
                audio_f = Path(generated_path or audio_f)
                produced = audio_f.exists() and audio_f.stat().st_size >= 1000
            else:
                try:
                    from voice_clone_manager import VoiceCloneManager
                    vcm = VoiceCloneManager()
                    active = vcm.get_active_clone()
                    chosen_clone = (
                        channel_config.get("voice_clone_id")
                        or edit_options.get("voice_clone_id")
                        or (active.get("id") if active else None)
                    )
                    if chosen_clone or active:
                        audio_wav = work_dir / f"scene_{i}_audio.wav"
                        ok = vcm.synthesize_speech(
                            text=narration,
                            output_path=str(audio_wav),
                            lang=lang,
                            pitch=0,
                            formant=1.0,
                            clone_id=chosen_clone
                        )
                        if ok and audio_wav.exists() and audio_wav.stat().st_size >= 1000:
                            audio_f = audio_wav
                            produced = True
                except Exception as e_vc:
                    print(f"[CRAYON-GEN] Klon ses uyarısı: {e_vc}")

                if not produced:
                    from video_generator import TTSGenerator
                    tts_gen = TTSGenerator()
                    audio_f = work_dir / f"scene_{i}_audio.mp3"
                    ok, error = tts_gen.generate_sync(narration, lang, str(audio_f))
                    if not ok or not audio_f.exists() or audio_f.stat().st_size < 1000:
                        raise RuntimeError(f"Sahne {i + 1} için ses üretilemedi: {error}")

            if not produced and (not audio_f.exists() or audio_f.stat().st_size < 1000):
                raise RuntimeError(f"Sahne {i + 1} için geçerli ses dosyası üretilemedi.")

        dur = get_audio_duration(str(audio_f))
        if dur <= 0.5 and not is_combat:
            dur = 4.0
        elif dur <= 0.5:
            raise RuntimeError(f"{sc.get('shot_id', f'Sahne {i + 1}')}: seslendirme süresi geçersiz.")
# Removed 5-second max shot constraint

        default_char = "CAPTAIN" if cat in ("aviation", "blackbox", "havacilik", "flight") else "DEFENSE_CEO"
        char_val = sc.get("active_character") or sc.get("character") or default_char
        diag_val = sc.get("character_dialogue") or sc.get("dialogue") or sc.get("character_quote") or ""

        scenes_info.append({
            "idx": i,
            "chapter": sc.get("chapter", ""),
            "char": char_val,
            "active_character": char_val,
            "type": sc.get("visual_type", "blueprint_spec"),
            "dialogue": diag_val,
            "character_dialogue": diag_val,
            "narration": sc.get("narration", ""),
            "audio_cue": sc.get("audio_cue", "none"),
            "audio_cues": sc.get("audio_cues") or {},
            "sfx": sc.get("sfx") or [],
            "music_track": sc.get("music_track"),
            "music_cut": bool(sc.get("music_cut")),
            "music_cut_duration_sec": float(sc.get("music_cut_duration_sec") or 1.5),
            "visual": sc.get("visual") or {},
            "source_refs": sc.get("source_refs") or [],
            "sources": sc.get("sources") or [],
            "fictional_satire": bool(sc.get("fictional_satire")),
            "burn_ass_subtitles": True,
            "custom_image": sc.get("custom_image") or (custom_images.get(str(i)) if custom_images else None),
            "image_path": sc.get("image_path"),
            "character_active": bool(sc.get("character_active", False)),
            "character_position": sc.get("character_position") or "bottom_right",
            "_structured_timeline": bool(sc.get("_structured_timeline")),
            "shot_id": sc.get("shot_id") or f"SHOT_{i + 1:02d}",
            "wav_path": audio_f,
            "duration": dur,
            "start_time": cumulative_time
        })
        cumulative_time += dur

    total_duration = cumulative_time
    print(f"[CRAYON-GEN] ⏱️ Toplam ses süresi: {total_duration:.1f}s ({total_duration/60:.2f} dk)")
# Removed strict 360-420s duration constraint

    # 2. Her Sahneyi Animasyonlu Olarak Render Et
    segment_files = []
    render_cache_marker = work_dir / ".crayon_render_cache_version"
    can_reuse_clips = (
        render_cache_marker.is_file()
        and render_cache_marker.read_text(encoding="utf-8").strip() == RENDER_CACHE_VERSION
    )
    for item in scenes_info:
        idx = item["idx"]
        dur = item["duration"]
        clip_mp4 = work_dir / f"clip_{idx:02d}.mp4"
        is_bp = (item["type"] == "blueprint_spec" or idx % 2 == 1)

        t_clip = time.time()
        if not can_reuse_clips or not _is_valid_rendered_clip(clip_mp4):
            render_animated_scene(
                scene_data=item,
                wav_path=item["wav_path"],
                output_mp4=clip_mp4,
                vehicle_name=vehicle_name,
                idx=idx,
                is_blueprint=is_bp
            )
        else:
            print(f"  ♻️ Mevcut geçerli sahne klibi yeniden kullanılıyor: {clip_mp4.name}")
        segment_files.append(clip_mp4)
        print(f"  ✨ Sahne {idx+1}/{len(scenes_info)} tamamlandı ({dur:.1f}s, render: {time.time()-t_clip:.2f}s)")
    render_cache_marker.write_text(RENDER_CACHE_VERSION, encoding="utf-8")

    # 3. Klipleri Birlestir
    concat_list = work_dir / "concat_list.txt"
    concat_list.write_text("\n".join([f"file '{p.resolve()}'" for p in segment_files]), encoding="utf-8")
    merged_raw = work_dir / "merged_raw.mp4"

    cmd_concat = [FFMPEG_BIN, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(merged_raw)]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 4. Altyazılar (ASS)
    ass_file = work_dir / "subtitles.ass"
    generate_broadcast_ass_subtitles(scenes_info, work_dir, ass_file)

    # 5. Final Pass: Altyazı & BGM Miks
    final_output = work_dir / "final_video.mp4"
    bgm_vol = float(edit_options.get("bgm_volume") or 0.04)
    bgm_timeline = script_data.get("bgm_timeline")
    timeline_mixed_bgm = None
    if bgm_timeline and isinstance(bgm_timeline, list) and len(bgm_timeline) > 0:
        try:
            try:
                from audio_library import build_timeline_bgm_track
            except ImportError:
                from src.audio_library import build_timeline_bgm_track
            timeline_mixed_bgm = build_timeline_bgm_track(
                bgm_timeline=bgm_timeline,
                total_duration=total_duration,
                work_dir=work_dir,
                base_volume=bgm_vol
            )
        except Exception as b_err:
            print(f"[CRAYON-GEN] bgm_timeline mixleme hatası: {b_err}")

    if timeline_mixed_bgm and timeline_mixed_bgm.is_file():
        bgm_path = timeline_mixed_bgm
        music_transition_path = None
        music_one_expression = "1.0"
        music_two_expression = ""
    else:
        timeline_music_paths = {
            track: BASE_DIR / "assets" / "music" / filename
            for track, filename in MUSIC_ASSETS.items()
        }
        music_transition_path = None
        if is_combat:
            missing_tracks = [path for path in timeline_music_paths.values() if not path.is_file()]
            if missing_tracks:
                raise FileNotFoundError(
                    "Required Crayon music assets not found: "
                    + ", ".join(str(path) for path in missing_tracks)
                )
            bgm_path = timeline_music_paths["lofi_storyteller"]
            music_transition_path = timeline_music_paths["reddit_official_bgm"]
        else:
            bgm_path = Path(edit_options["bgm_path"]) if edit_options.get("bgm_path") else None
            if not bgm_path or not bgm_path.is_file():
                default_bgm = BASE_DIR / "assets" / "music" / "lofi_storyteller.mp3"
                bgm_path = default_bgm if default_bgm.is_file() else None

    if bgm_path:
        if not timeline_mixed_bgm:
            if not is_combat and cat in ("crayon_capital", "tech_finance_essay") and not edit_options.get("bgm_path"):
                alternate_bgm = BASE_DIR / "assets" / "music" / "reddit_official_bgm.mp3"
                if alternate_bgm.is_file() and alternate_bgm.resolve() != bgm_path.resolve():
                    music_transition_path = alternate_bgm

            switch_at = total_duration / 2.0
            crossfade_duration = 0.8
            if is_combat:
                music_one_base = _timeline_music_volume_expression(
                    scenes_info, "lofi_storyteller", bgm_vol
                )
                music_two_base = _timeline_music_volume_expression(
                    scenes_info, "reddit_official_bgm", bgm_vol
                )
                music_one_expression = music_one_base
                music_two_expression = music_two_base
            elif music_transition_path:
                music_one_base = (
                    f"{bgm_vol:.4f}*if(lt(t\\,{switch_at:.3f})\\,1\\,"
                    f"if(lt(t\\,{switch_at + crossfade_duration:.3f})\\,"
                    f"({switch_at + crossfade_duration:.3f}-t)/{crossfade_duration:.3f}\\,0))"
                )
                music_two_base = (
                    f"{bgm_vol:.4f}*if(lt(t\\,{switch_at:.3f})\\,0\\,"
                    f"if(lt(t\\,{switch_at + crossfade_duration:.3f})\\,"
                    f"(t-{switch_at:.3f})/{crossfade_duration:.3f}\\,1))"
                )
            else:
                music_one_base = f"{bgm_vol:.4f}"
                music_two_base = ""

            if not is_combat:
                music_one_expression = music_one_base
                music_two_expression = music_two_base
                for item in reversed(scenes_info):
                    if item.get("audio_cue") == "drop":
                        cue_start = max(0.0, float(item["start_time"]))
                        cue_end = cue_start + 0.8
                        music_two_expression = (
                            f"if(between(t\\,{cue_start:.3f}\\,{cue_end:.3f})\\,0\\,{music_two_expression})"
                            if music_two_expression else ""
                        )
                        music_one_expression = (
                            f"if(between(t\\,{cue_start:.3f}\\,{cue_end:.3f})\\,0\\,{music_one_expression})"
                        )

        bgm_inputs = ""
        bgm_mix = f"[1:a]volume='{music_one_expression}':eval=frame[bgm1];"
        if music_transition_path:
            final_cmd_bgm_input = ["-stream_loop", "-1", "-i", str(music_transition_path)]
            bgm_inputs = (
                f"[2:a]volume='{music_two_expression}':eval=frame[bgm2];"
                "[bgm1][bgm2]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[bgm];"
            )
            bgm_mix += bgm_inputs
        else:
            final_cmd_bgm_input = []
            bgm_mix += "[bgm1]anull[bgm];"

        final_cmd = [
            FFMPEG_BIN, "-y",
            "-i", str(merged_raw),
            "-stream_loop", "-1", "-i", str(bgm_path),
            *final_cmd_bgm_input,
            "-filter_complex", (
                f"[0:v]ass={str(ass_file)}[vout];"
                f"[0:a]loudnorm=I=-15:TP=-1.5:LRA=9[vocal];"
                f"{bgm_mix}"
                f"[vocal][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
            ),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(final_output)
        ]
    else:
        final_cmd = [
            FFMPEG_BIN, "-y",
            "-i", str(merged_raw),
            "-vf", f"ass={str(ass_file)}",
            "-af", "loudnorm=I=-15:TP=-1.5:LRA=9",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(final_output)
        ]
    final_render = subprocess.run(final_cmd, capture_output=True, text=True)
    if final_render.returncode != 0:
        raise RuntimeError(f"Crayon final render failed: {final_render.stderr[-3000:]}")

    file_size_mb = round(final_output.stat().st_size / (1024 * 1024), 2)
    print(f"[CRAYON-GEN] 🎉 Video başarıyla üretildi: {final_output.name} ({file_size_mb} MB, {time.time()-t0:.1f}s)")
    thumbnail_text = script_data.get("thumbnail_text") or vehicle_name
    thumbnail_path = _create_crayon_thumbnail(
        final_output,
        work_dir / "thumbnail.jpg",
        thumbnail_text,
    )

    # Chapters
    chapter_lines = []
    c_time = 0.0
    for item in scenes_info:
        ch = item["chapter"] or item["narration"][:40]
        m = int(c_time // 60)
        s = int(c_time % 60)
        chapter_lines.append(f"{m:02d}:{s:02d} - {ch}")
        c_time += item["duration"]

    (work_dir / "youtube_chapters.txt").write_text("\n".join(chapter_lines), encoding="utf-8")

    return {
        "video_path": str(final_output),
        "title": title,
        "description": script_data.get("description", ""),
        "tags": script_data.get("tags", []),
        "duration": round(total_duration, 1),
        "file_size_mb": file_size_mb,
        "thumbnail_path": str(thumbnail_path),
    }
