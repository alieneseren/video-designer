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
    W, H, FPS
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
    scenes = script_data.get("scenes") or []
    title = script_data.get("title") or channel_config.get("name") or "Crayon Combat"
    vehicle_name = script_data.get("vehicle_name") or script_data.get("flight_name") or script_data.get("incident_name") or title

    if not scenes:
        raise ValueError("Senaryoda sahne listesi bulunamadı.")

    chan_id = channel_config.get("channel_id") or ""
    cat = channel_config.get("topic_category", "crayon_combat")
    cat = channel_config.get("topic_category", "crayon_combat")
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
                    if active:
                        audio_wav = work_dir / f"scene_{i}_audio.wav"
                        ok = vcm.synthesize_speech(
                            text=narration,
                            output_path=str(audio_wav),
                            lang=lang,
                            pitch=0,
                            formant=1.0,
                            clone_id=active.get("id")
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
        if dur <= 0.5:
            dur = 4.0

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
            "wav_path": audio_f,
            "duration": dur,
            "start_time": cumulative_time
        })
        cumulative_time += dur

    total_duration = cumulative_time
    print(f"[CRAYON-GEN] ⏱️ Toplam ses süresi: {total_duration:.1f}s ({total_duration/60:.2f} dk)")

    # 2. Her Sahneyi Animasyonlu Olarak Render Et
    segment_files = []
    for item in scenes_info:
        idx = item["idx"]
        dur = item["duration"]
        clip_mp4 = work_dir / f"clip_{idx:02d}.mp4"
        is_bp = (item["type"] == "blueprint_spec" or idx % 2 == 1)

        t_clip = time.time()
        render_animated_scene(
            scene_data=item,
            wav_path=item["wav_path"],
            output_mp4=clip_mp4,
            vehicle_name=vehicle_name,
            idx=idx,
            is_blueprint=is_bp
        )
        segment_files.append(clip_mp4)
        print(f"  ✨ Sahne {idx+1}/{len(scenes_info)} tamamlandı ({dur:.1f}s, render: {time.time()-t_clip:.2f}s)")

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
    bgm_path = Path(edit_options["bgm_path"]) if edit_options.get("bgm_path") else None
    if not bgm_path or not bgm_path.is_file():
        default_bgm = BASE_DIR / "assets" / "music" / "lofi_storyteller.mp3"
        bgm_path = default_bgm if default_bgm.is_file() else None

    bgm_vol = float(edit_options.get("bgm_volume") or 0.04)
    if bgm_path:
        music_transition_path = None
        if cat in ("crayon_combat", "crayon_capital", "tech_finance_essay") and not edit_options.get("bgm_path"):
            alternate_bgm = BASE_DIR / "assets" / "music" / "reddit_official_bgm.mp3"
            if alternate_bgm.is_file() and alternate_bgm.resolve() != bgm_path.resolve():
                music_transition_path = alternate_bgm

        switch_at = total_duration / 2.0
        crossfade_duration = 0.8
        if music_transition_path:
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

        music_one_expression = music_one_base
        music_two_expression = music_two_base
        for item in reversed(scenes_info):
            if item.get("audio_cue") == "drop":
                cue_start = max(0.0, float(item["start_time"]))
                cue_end = cue_start + 0.8
                music_one_expression = (
                    f"if(between(t\\,{cue_start:.3f}\\,{cue_end:.3f})\\,0\\,{music_one_expression})"
                )
                if music_two_expression:
                    music_two_expression = (
                        f"if(between(t\\,{cue_start:.3f}\\,{cue_end:.3f})\\,0\\,{music_two_expression})"
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
