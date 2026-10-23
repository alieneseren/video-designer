"""
Remotion Video Renderer Bridge for yt-oto-video.
Provides high-fidelity, React-based programmatic video rendering
for WhatsApp Conversations and Reddit Stories.
"""

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REMOTION_DIR = PROJECT_ROOT / "remotion"
PUBLIC_MEDIA_DIR = REMOTION_DIR / "public" / "media"


def is_remotion_available() -> bool:
    """Checks if Node.js and Remotion environment are installed and ready."""
    if not (REMOTION_DIR / "package.json").exists():
        return False
    if not (REMOTION_DIR / "node_modules").exists():
        return False
    if not shutil.which("node"):
        return False
    return True


def _link_media_asset(abs_path: str, media_dir: Path, prefix: str = "asset") -> Optional[str]:
    """
    Copies a local file into remotion/public/media/
    Returns the relative path 'media/<name>' for Remotion staticFile().
    """
    if not abs_path or not os.path.exists(abs_path):
        return None

    media_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(abs_path).suffix or ".bin"
    unique_name = f"{prefix}_{uuid.uuid4().hex[:8]}{ext}"
    target_path = media_dir / unique_name

    try:
        if target_path.exists() or target_path.is_symlink():
            target_path.unlink()
        shutil.copy2(os.path.abspath(abs_path), target_path)
        return f"media/{unique_name}"
    except Exception as copy_err:
        print(f"[REMOTION] Varlık kopyalama hatası: {copy_err}")
        return None


def render_whatsapp_video_remotion(
    contact_name: str,
    contact_avatar: Optional[str],
    audio_path: str,
    messages_data: List[Dict[str, Any]],
    output_path: str,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.12,
    fps: int = 30,
    status_text: str = "çevrimiçi",
    bg_video_path: Optional[str] = None,
    layout: str = "dublaj_style",
    watermark_text: Optional[str] = None,
    instagram_username: Optional[str] = None,
    theme: str = "light",
    wallpaper_path: Optional[str] = None,
    is_group: bool = False,
    group_participants: Optional[str] = None,
    language: str = "tr",
) -> bool:
    """
    Renders an ultra-realistic WhatsApp Conversation Shorts video using Remotion.
    Supports dublaj_style (@1dublaj signature layout with letterboxing, light theme,
    message avatars, sender name colors, floral pastel wallpaper, and channel watermarks),
    as well as compact_top and fullscreen layouts.
    """
    if not is_remotion_available():
        print("[REMOTION] Remotion kurulu veya hazır değil, fallback kullanılacak.")
        return False

    temp_links = []
    scratch_dir = PROJECT_ROOT / "scratch"
    scratch_dir.mkdir(exist_ok=True)
    props_file = scratch_dir / f"remotion_wa_props_{uuid.uuid4().hex[:8]}.json"

    try:
        # Measure audio duration
        duration_sec = 60.0
        try:
            from moviepy import AudioFileClip
            with AudioFileClip(audio_path) as a_clip:
                duration_sec = a_clip.duration
        except Exception:
            pass

        duration_frames = int(duration_sec * fps) + int(0.5 * fps) # 0.5s padding

        # Ensure standard SFX exist in remotion/public/media
        sfx_dir = PROJECT_ROOT / "config" / "assets" / "whatsapp" / "assets" / "sfx"
        for sfx_name in ["pop.wav", "whoosh.wav", "swoosh.wav"]:
            src_sfx = sfx_dir / sfx_name
            target_sfx = PUBLIC_MEDIA_DIR / sfx_name
            if src_sfx.exists() and not target_sfx.exists():
                shutil.copy2(src_sfx, target_sfx)
        if (PUBLIC_MEDIA_DIR / "swoosh.wav").exists() and not (PUBLIC_MEDIA_DIR / "whoosh.wav").exists():
            shutil.copy2(PUBLIC_MEDIA_DIR / "swoosh.wav", PUBLIC_MEDIA_DIR / "whoosh.wav")

        # Link media files into remotion/public/media
        rel_audio = _link_media_asset(audio_path, PUBLIC_MEDIA_DIR, prefix="audio")
        if rel_audio:
            temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_audio).name)

        rel_avatar = None
        if contact_avatar and os.path.exists(contact_avatar):
            rel_avatar = _link_media_asset(contact_avatar, PUBLIC_MEDIA_DIR, prefix="avatar")
            if rel_avatar:
                temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_avatar).name)
        elif contact_avatar and (PUBLIC_MEDIA_DIR / Path(contact_avatar).name).exists():
            rel_avatar = f"/media/{Path(contact_avatar).name}"
        elif contact_avatar and contact_avatar.startswith("data:"):
            rel_avatar = contact_avatar

        rel_bgm = None
        if bgm_path and os.path.exists(bgm_path):
            rel_bgm = _link_media_asset(bgm_path, PUBLIC_MEDIA_DIR, prefix="bgm")
            if rel_bgm:
                temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_bgm).name)

        rel_bg_video = None
        if bg_video_path and os.path.exists(bg_video_path):
            rel_bg_video = _link_media_asset(bg_video_path, PUBLIC_MEDIA_DIR, prefix="bg_wa")
            if rel_bg_video:
                temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_bg_video).name)

        # Link custom wallpaper or select dynamic aesthetic wallpaper from gallery
        rel_wallpaper = ""
        if wallpaper_path and os.path.exists(wallpaper_path):
            linked_wp = _link_media_asset(wallpaper_path, PUBLIC_MEDIA_DIR, prefix="wallpaper")
            if linked_wp:
                rel_wallpaper = linked_wp
                temp_links.append(PUBLIC_MEDIA_DIR / Path(linked_wp).name)
        elif wallpaper_path and (PUBLIC_MEDIA_DIR / Path(wallpaper_path).name).exists():
            rel_wallpaper = f"/media/{Path(wallpaper_path).name}"

        if not rel_wallpaper:
            # Dynamic wallpaper rotation based on contact_name + message count seed
            wp_pool = [
                "doodle_beige.jpg",
                "botanical_shadow.jpg",
                "pastel_gradient.jpg",
                "cozy_wood.jpg",
                "dark_slate.jpg",
                "floral_pastel.jpg",
                "urban_wall.jpg",
            ]
            valid_wps = [w for w in wp_pool if (PUBLIC_MEDIA_DIR / w).exists()]
            if valid_wps:
                seed = abs(hash((contact_name or "") + str(len(messages_data))))
                chosen_wp = valid_wps[seed % len(valid_wps)]
                rel_wallpaper = f"/media/{chosen_wp}"
            else:
                rel_wallpaper = "/media/floral_pastel.jpg"

        # Build message timeline
        remotion_messages = []
        for i, m in enumerate(messages_data):
            # Calculate timing in frames
            start_sec = m.get("start_time", 0.0)
            dur_sec = m.get("duration", 2.0)
            start_frame = int(start_sec * fps)
            dur_frames = max(30, int(dur_sec * fps))

            sender_avatar = m.get("sender_avatar") or m.get("senderAvatar")
            rel_sender_avatar = ""
            if sender_avatar and os.path.exists(sender_avatar):
                rel_sender_avatar = _link_media_asset(sender_avatar, PUBLIC_MEDIA_DIR, prefix=f"s_avatar_{i}")
                if rel_sender_avatar:
                    temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_sender_avatar).name)
            elif sender_avatar and (PUBLIC_MEDIA_DIR / Path(sender_avatar).name).exists():
                rel_sender_avatar = f"/media/{Path(sender_avatar).name}"

            remotion_messages.append({
                "id": m.get("id", i + 1),
                "sender": m.get("sender", "contact"),
                "text": m.get("text", ""),
                "time": m.get("time", "14:24"),
                "senderName": m.get("sender_name") or m.get("senderName") or "",
                "senderAvatar": rel_sender_avatar,
                "senderColor": m.get("sender_color") or m.get("senderColor") or "",
                "startFrame": start_frame,
                "durationInFrames": dur_frames,
            })

        props = {
            "contactName": contact_name,
            "contactAvatar": rel_avatar or "",
            "statusText": status_text,
            "audioPath": rel_audio or "",
            "bgmPath": rel_bgm or "",
            "bgmVolume": bgm_volume,
            "bgVideoPath": rel_bg_video or "",
            "layout": layout,
            "theme": theme,
            "watermarkText": watermark_text or "",
            "instagramUsername": (instagram_username or "").strip().lstrip("@") if instagram_username else "",
            "wallpaperPath": rel_wallpaper,
            "isGroup": is_group,
            "groupParticipants": group_participants or "",
            "language": language,
            "messages": remotion_messages,
            "fps": fps,
            "durationInFrames": duration_frames,
        }

        props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REMOTION] WhatsApp Chat render başlatılıyor: {len(remotion_messages)} mesaj, {duration_sec:.1f}s ({duration_frames} kare)")

        # Execute Remotion CLI
        cmd = [
            "npx", "remotion", "render",
            "src/index.ts",
            "WhatsAppChat",
            os.path.abspath(output_path),
            f"--props={str(props_file.resolve())}",
            f"--public-dir={str((REMOTION_DIR / 'public').resolve())}",
            "--overwrite",
        ]

        proc = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )

        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
            print(f"[REMOTION] WhatsApp Chat render başarılı: {output_path} ({os.path.getsize(output_path) / 1024 / 1024:.1f} MB)")
            return True
        else:
            print(f"[REMOTION] Render hatası (Kod {proc.returncode}):\n{proc.stderr}\n{proc.stdout}")
            return False

    except Exception as e:
        import traceback
        print(f"[REMOTION] Beklenmeyen hata: {e}\n{traceback.format_exc()}")
        return False
    finally:
        # Cleanup temporary files
        if props_file.exists():
            try:
                props_file.unlink()
            except Exception:
                pass
        for link in temp_links:
            if link.exists() or link.is_symlink():
                try:
                    link.unlink()
                except Exception:
                    pass


def render_reddit_video_remotion(
    question: str,
    subreddit: str,
    author: str,
    upvotes: str,
    audio_path: str,
    bg_video_path: Optional[str],
    captions_data: List[Dict[str, Any]],
    output_path: str,
    avatar_path: Optional[str] = None,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.18,
    fps: int = 30,
    card_duration_sec: float = 2.8,
) -> bool:
    """
    Renders an avant-garde Reddit Story Shorts video using Remotion.
    """
    if not is_remotion_available():
        print("[REMOTION] Remotion kurulu veya hazır değil, fallback kullanılacak.")
        return False

    temp_links = []
    scratch_dir = PROJECT_ROOT / "scratch"
    scratch_dir.mkdir(exist_ok=True)
    props_file = scratch_dir / f"remotion_reddit_props_{uuid.uuid4().hex[:8]}.json"

    try:
        # Measure audio duration
        duration_sec = 60.0
        try:
            from moviepy import AudioFileClip
            with AudioFileClip(audio_path) as a_clip:
                duration_sec = a_clip.duration
        except Exception:
            pass

        duration_frames = int(duration_sec * fps) + int(0.5 * fps)
        card_duration_frames = min(int(card_duration_sec * fps), 90)

        # Link media files
        rel_audio = _link_media_asset(audio_path, PUBLIC_MEDIA_DIR, prefix="audio")
        if rel_audio:
            temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_audio).name)

        rel_bg_vid = None
        if bg_video_path and os.path.exists(bg_video_path):
            rel_bg_vid = _link_media_asset(bg_video_path, PUBLIC_MEDIA_DIR, prefix="bgvid")
            if rel_bg_vid:
                temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_bg_vid).name)

        rel_avatar = None
        if avatar_path and os.path.exists(avatar_path):
            rel_avatar = _link_media_asset(avatar_path, PUBLIC_MEDIA_DIR, prefix="avatar")
            if rel_avatar:
                temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_avatar).name)
        elif avatar_path and avatar_path.startswith("data:"):
            rel_avatar = avatar_path

        rel_bgm = None
        if bgm_path and os.path.exists(bgm_path):
            rel_bgm = _link_media_asset(bgm_path, PUBLIC_MEDIA_DIR, prefix="bgm")
            if rel_bgm:
                temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_bgm).name)

        # Format captions
        remotion_captions = []
        for c in captions_data:
            start_f = int(c.get("offset", c.get("start", 0.0)) * fps)
            dur_f = max(10, int(c.get("duration", 1.0) * fps))
            remotion_captions.append({
                "text": c.get("text", ""),
                "startFrame": start_f,
                "durationInFrames": dur_f,
            })

        props = {
            "question": question,
            "subreddit": subreddit,
            "author": author,
            "upvotes": upvotes,
            "avatarPath": rel_avatar or "",
            "bgVideoPath": rel_bg_vid or "",
            "cardDurationFrames": card_duration_frames,
            "audioPath": rel_audio or "",
            "bgmPath": rel_bgm or "",
            "bgmVolume": bgm_volume,
            "captions": remotion_captions,
            "fps": fps,
            "durationInFrames": duration_frames,
        }

        props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REMOTION] Reddit Story render başlatılıyor: {len(remotion_captions)} altyazı segmenti, {duration_sec:.1f}s ({duration_frames} kare)")

        cmd = [
            "npx", "remotion", "render",
            "src/index.ts",
            "RedditStory",
            os.path.abspath(output_path),
            f"--props={str(props_file.resolve())}",
            f"--public-dir={str((REMOTION_DIR / 'public').resolve())}",
            "--overwrite",
        ]

        proc = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )

        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
            print(f"[REMOTION] Reddit Story render başarılı: {output_path} ({os.path.getsize(output_path) / 1024 / 1024:.1f} MB)")
            return True
        else:
            print(f"[REMOTION] Render hatası (Kod {proc.returncode}):\n{proc.stderr}\n{proc.stdout}")
            return False

    except Exception as e:
        import traceback
        print(f"[REMOTION] Beklenmeyen hata: {e}\n{traceback.format_exc()}")
        return False
    finally:
        if props_file.exists():
            try:
                props_file.unlink()
            except Exception:
                pass
        for link in temp_links:
            if link.exists() or link.is_symlink():
                try:
                    link.unlink()
                except Exception:
                    pass


def render_connectome_video_remotion(
    track_info: dict,
    spikes_data: dict,
    audio_path: str,
    output_path: str,
    is_vertical: bool = False,
    theme: str = "cosmic",
    fps: int = 30,
) -> bool:
    """
    Renders Drosophila Connectome Bio-AI music video (16:9 Landscape or 9:16 Shorts) using Remotion.
    """
    if not is_remotion_available():
        print("[REMOTION] Hata: Remotion ortamı veya Node.js kurulu değil.")
        return False

    scratch_dir = PROJECT_ROOT / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    props_file = scratch_dir / f"remotion_connectome_props_{uuid.uuid4().hex[:8]}.json"

    duration_sec = float(track_info.get("durationSec") or 180.0)
    duration_frames = int(track_info.get("totalFrames") or int(duration_sec * fps))

    # Link audio file into remotion/public/media/
    rel_audio = None
    if audio_path and os.path.exists(audio_path):
        rel_audio = _link_media_asset(audio_path, PUBLIC_MEDIA_DIR, prefix="audio")

    comp_id = "SinekKlipShort" if is_vertical else "SinekKlipLandscape"

    props = {
        "title": track_info.get("title", "AXONAL RESONANCE"),
        "subtitle": track_info.get("subtitle", "DROSOPHILA MELANOGASTER CONNECTOME SYNTHESIS"),
        "scale": track_info.get("scale", "F Minor Pentatonic"),
        "bpm": float(track_info.get("bpm", 88.0)),
        "concept": track_info.get("concept", "139.255 nöronluk biyolojik konnektom simülasyonu."),
        "hook": track_info.get("hook", "Meyve sineği beynindeki nöronların canlı piyano harmonikleri"),
        "theme": theme or track_info.get("theme", "cosmic"),
        "neuronsCount": int(spikes_data.get("neuronsCount", len(spikes_data.get("neuronCoords", [])) or 48)),
        "neuronCoords": spikes_data.get("neuronCoords", []),
        "spikes": spikes_data.get("spikes", []),
        "isVertical": is_vertical,
        "audioPath": rel_audio or "audio.wav",
        "fps": fps,
        "durationInFrames": duration_frames,
        "totalFrames": duration_frames,
    }

    try:
        props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REMOTION] Sinek Beyni Video render başlatılıyor: {comp_id}, {duration_sec:.1f}s ({duration_frames} kare), Tema: {theme}")

        cmd = [
            "npx", "remotion", "render",
            "src/index.ts",
            comp_id,
            os.path.abspath(output_path),
            f"--props={str(props_file.resolve())}",
            f"--public-dir={str((REMOTION_DIR / 'public').resolve())}",
            "--concurrency=4",
            "--overwrite",
        ]

        timeout_val = max(600, int(duration_sec * 4))

        proc = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_val
        )

        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
            print(f"[REMOTION] Sinek Beyni Video render başarılı: {output_path} ({os.path.getsize(output_path) / 1024 / 1024:.1f} MB)")
            return True
        else:
            print(f"[REMOTION] Render hatası (Kod {proc.returncode}):\n{proc.stderr}\n{proc.stdout}")
            return False

    except Exception as e:
        import traceback
        print(f"[REMOTION] Beklenmeyen hata: {e}\n{traceback.format_exc()}")
        return False
    finally:
        if props_file.exists():
            try:
                props_file.unlink()
            except Exception:
                pass
        if rel_audio:
            target_linked = PUBLIC_MEDIA_DIR / Path(rel_audio).name
            if target_linked.exists():
                try:
                    target_linked.unlink()
                except Exception:
                    pass


def render_story_illustrated_remotion(
    title: str,
    scenes_data: List[Dict[str, Any]],
    audio_path: str,
    output_path: str,
    author: Optional[str] = None,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.15,
    theme: str = "cinematic_dark",
    watermark_text: Optional[str] = None,
    fps: int = 30,
) -> bool:
    """
    Renders an avant-garde Story-driven Illustrated Shorts video using Remotion.
    Combines custom scene illustrations, cinematic Ken Burns camera motions,
    atmospheric lighting, and kinetic subtitles into an ultra-high-definition MP4.
    """
    if not is_remotion_available():
        print("[REMOTION] Remotion kurulu veya hazır değil, işlem iptal edildi.")
        return False

    temp_links = []
    scratch_dir = PROJECT_ROOT / "scratch"
    scratch_dir.mkdir(exist_ok=True)
    props_file = scratch_dir / f"remotion_story_props_{uuid.uuid4().hex[:8]}.json"

    try:
        # 1. Ses Süresini Ölç
        duration_sec = 10.0
        try:
            from moviepy import AudioFileClip
            with AudioFileClip(audio_path) as a_clip:
                duration_sec = float(a_clip.duration)
        except Exception:
            pass

        # 2. Medya Varlıklarını Remotion Public Dizinine Bağla
        rel_audio = _link_media_asset(audio_path, PUBLIC_MEDIA_DIR, prefix="story_narrator")
        if rel_audio:
            temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_audio).name)

        rel_bgm = None
        if bgm_path and os.path.exists(bgm_path):
            rel_bgm = _link_media_asset(bgm_path, PUBLIC_MEDIA_DIR, prefix="story_bgm")
            if rel_bgm:
                temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_bgm).name)

        # 3. Sahne Görsellerini ve Zamanlamalarını Hazırla
        total_scenes = len(scenes_data)
        if total_scenes == 0:
            print("[REMOTION] Hata: En az bir sahne gereklidir.")
            return False

        # Eğer sahnelerin frame zamanlaması verilmemişse eşit böl
        total_audio_frames = max(30, int(duration_sec * fps) + int(0.5 * fps))
        current_frame = 0
        remotion_scenes = []

        for idx, sc in enumerate(scenes_data):
            img_local = sc.get("image_path")
            rel_img = None
            if img_local and os.path.exists(img_local):
                rel_img = _link_media_asset(img_local, PUBLIC_MEDIA_DIR, prefix=f"scene_{idx}")
                if rel_img:
                    temp_links.append(PUBLIC_MEDIA_DIR / Path(rel_img).name)

            # Sahne süresi hesapla
            custom_dur = sc.get("duration_in_frames")
            if custom_dur and custom_dur > 0:
                scene_dur = int(custom_dur)
            else:
                # Eşit paylaştır
                scene_dur = total_audio_frames // total_scenes
                if idx == total_scenes - 1:
                    scene_dur = max(scene_dur, total_audio_frames - current_frame)

            start_f = sc.get("start_frame", current_frame)

            remotion_scenes.append({
                "id": sc.get("id", idx + 1),
                "imagePath": rel_img or "media/sample_story_1.jpg",
                "captionText": sc.get("caption_text", ""),
                "startFrame": start_f,
                "durationInFrames": scene_dur,
                "cameraEffect": sc.get("camera_effect", "ken_burns"),
                "highlightWords": sc.get("highlight_words", []),
            })
            current_frame = start_f + scene_dur

        total_frames = max(total_audio_frames, current_frame)

        # 4. Remotion Props JSON Dosyasını Yaz
        props = {
            "title": title,
            "author": author or "",
            "scenes": remotion_scenes,
            "audioPath": rel_audio or "",
            "bgmPath": rel_bgm or "",
            "bgmVolume": bgm_volume,
            "theme": theme,
            "watermarkText": watermark_text or "",
            "fps": fps,
            "durationInFrames": total_frames,
        }

        props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[REMOTION] 🎬 Story Illustrated Video render başlatılıyor: '{title}', {len(remotion_scenes)} sahne, {duration_sec:.1f}s ({total_frames} kare)")

        # 5. Remotion CLI Çağrısı
        cmd = [
            "npx", "remotion", "render",
            "src/index.ts",
            "StoryIllustrated",
            os.path.abspath(output_path),
            f"--props={str(props_file.resolve())}",
            f"--public-dir={str((REMOTION_DIR / 'public').resolve())}",
            "--overwrite",
        ]

        proc = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR),
            capture_output=True,
            text=True,
            timeout=max(300, int(duration_sec * 6))
        )

        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f"[REMOTION] ✅ Story Illustrated Video render başarılı: {output_path} ({size_mb:.1f} MB)")
            return True
        else:
            print(f"[REMOTION] Render hatası (Kod {proc.returncode}):\n{proc.stderr}\n{proc.stdout}")
            return False

    except Exception as e:
        import traceback
        print(f"[REMOTION] Beklenmeyen hata: {e}\n{traceback.format_exc()}")
        return False
    finally:
        if props_file.exists():
            try:
                props_file.unlink()
            except Exception:
                pass
        for link in temp_links:
            if link.exists() or link.is_symlink():
                try:
                    link.unlink()
                except Exception:
                    pass

