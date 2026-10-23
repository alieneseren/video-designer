import os
import re
import json
import time
import shutil
import subprocess
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

from .models import Scenario
from .script_generator import ScriptGenerator
from .tts_engine import TTSEngine
from .audio_mixer import AudioMixer
from .video_renderer import VideoRenderer
from .voice_profiles import BASE_ASSETS

def generate_whatsapp_video(
    channel_config: dict,
    planned_row: Optional[dict] = None,
    custom_prompt: Optional[str] = None,
    work_dir: Optional[Path] = None,
    script_data: Optional[dict] = None,
    output_dir: Optional[str] = None,
    edit_options: Optional[dict] = None,
    custom_images: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    WhatsApp Shorts tam otonom üretim boru hattı (BirDublaj / Hamza Dublaj tarzı).
    - AI ile diyalog ve senaryo üretir (veya içerik planından / hazır senaryodan alır)
    - Karakter bazlı neural TTS seslendirmesi ve milisaniyelik zamanlama hesabı yapar
    - Pop/Swoosh SFX ve neşeli komedi BGM'i FFmpeg ile miksler
    - Playwright Chromium ile 1080x1920 (9:16) compact_top video kaydeder
    - Video bilgilerini ve metadata.json'u hazırlar
    """
    language = (channel_config.get("language") or "tr").lower().strip()
    is_tr = (language == "tr" or language.startswith("tr"))
    channel_id = channel_config.get("channel_id") or channel_config.get("id") or ("yazanyazana" if is_tr else "crazyychats")
    channel_name = channel_config.get("name") or channel_id or ("YazanYazana" if is_tr else "Crazy Chats")

    # 1. Klasör yapısını hazırla
    if work_dir is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base = Path(output_dir) if output_dir else Path("output") / channel_id / "yuklenecek"
        work_dir = base / timestamp
        work_dir.mkdir(parents=True, exist_ok=True)
    else:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

    audio_dir = str(work_dir / "audio")
    os.makedirs(audio_dir, exist_ok=True)

    # 2. Senaryoyu hazırla
    has_msgs = script_data.get("messages") or script_data.get("dialogue") if (script_data and isinstance(script_data, dict)) else None
    if has_msgs and len(has_msgs) >= 2:
        print(f"[WhatsApp] Önceden hazırlanmış senaryo kullanılıyor: '{script_data.get('title', 'WhatsApp Sohbeti')}' ({language})...")
        scenario = ScriptGenerator.build_scenario_from_dict(script_data, channel_name=channel_id or channel_name, language=language)
        prompt_to_use = script_data.get("topic") or scenario.title
    else:
        prompt_to_use = custom_prompt
        if not prompt_to_use and script_data and isinstance(script_data, dict):
            prompt_to_use = script_data.get("topic") or script_data.get("title")
        if not prompt_to_use and planned_row:
            prompt_to_use = planned_row.get("konu") or planned_row.get("baslik")

        if not prompt_to_use:
            prompt_to_use = "ev arkadaşı ile troll dostun komik, helal ve ters köşe diyalogu" if is_tr else "hilarious and clean misunderstanding between funny roommates or family members"

        print(f"[WhatsApp] Senaryo üretiliyor ({language}): '{prompt_to_use}'...")
        scenario = ScriptGenerator.generate_ai_scenario(prompt=prompt_to_use, channel_name=channel_id or channel_name, language=language)

    # Kanal ayarlarından avatar / layout özelleştirmesi varsa uygula
    merged_edit_opts = edit_options or channel_config.get("edit_options", {}) or {}
    # Layout seçimi (viral_chat, fullscreen veya compact_top)
    chosen_layout = merged_edit_opts.get("layout") or merged_edit_opts.get("whatsapp_layout") or getattr(scenario, "layout", "compact_top")
    scenario.layout = chosen_layout or "compact_top"

    # Senaryodan kişi adını güncelle
    if script_data and isinstance(script_data, dict) and script_data.get("contact_name"):
        scenario.contact_name = script_data["contact_name"]
        scenario.whatsapp_username = script_data["contact_name"]
        if "contact" in scenario.characters:
            scenario.characters["contact"].name = script_data["contact_name"]

    # YouTube filigranı / watermark: Kanal adı yerine channel_id kullanılmalıdır
    watermark_name = merged_edit_opts.get("watermark_text") or channel_id or channel_name or "YazanYazana"
    if watermark_name.lower() in ("bidublaj", "birdublaj"):
        watermark_name = channel_id or "YazanYazana"
    scenario.watermark_username = watermark_name

    # Gemini veya Perchance tarafından üretilen profil fotoğrafını (avatar) ve katılımcı avatarlarını işle
    participant_avatars = {}
    if custom_images and isinstance(custom_images, dict):
        avatar_raw = custom_images.get("0") or custom_images.get("group") or custom_images.get("avatar") or next(iter(custom_images.values()), None)
        if avatar_raw and isinstance(avatar_raw, str):
            avatar_path = work_dir / "contact_avatar.png"
            try:
                import base64
                raw_b64 = avatar_raw.split("base64,")[1] if "base64," in avatar_raw else avatar_raw
                if len(raw_b64) > 100:  # Base64 string
                    img_bytes = base64.b64decode(raw_b64)
                    avatar_path.write_bytes(img_bytes)
                    scenario.contact_avatar = str(avatar_path)
                    scenario.profile_avatar = str(avatar_path)
                    print(f"[WhatsApp] Gemini profil fotoğrafı başarıyla ayarlandı: {avatar_path}")
                elif os.path.exists(avatar_raw):
                    import shutil
                    shutil.copyfile(avatar_raw, avatar_path)
                    scenario.contact_avatar = str(avatar_path)
                    scenario.profile_avatar = str(avatar_path)
                    print(f"[WhatsApp] Profil fotoğrafı dosyadan kopyalandı: {avatar_path}")
            except Exception as av_err:
                print(f"[WhatsApp] Avatar görsel işleme hatası: {av_err}")

        # Katılımcı avatarlarını ayrıştır
        for k, v in custom_images.items():
            if str(k) not in ["0", "avatar", "group"] and isinstance(v, str):
                p_path = work_dir / f"p_avatar_{k}.png"
                try:
                    import base64
                    raw_b64 = v.split("base64,")[1] if "base64," in v else v
                    if len(raw_b64) > 100:
                        p_path.write_bytes(base64.b64decode(raw_b64))
                        participant_avatars[str(k).lower()] = str(p_path)
                    elif os.path.exists(v):
                        participant_avatars[str(k).lower()] = str(v)
                except Exception as p_err:
                    print(f"[WhatsApp] Katılımcı avatarı ayrıştırma hatası ({k}): {p_err}")

    # Fallback to gender avatar if custom_images didn't provide one or invalid path
    avatar_exists = False
    if scenario.contact_avatar:
        if os.path.isabs(scenario.contact_avatar) and os.path.exists(scenario.contact_avatar):
            avatar_exists = True
        elif os.path.exists(scenario.contact_avatar):
            scenario.contact_avatar = str(os.path.abspath(scenario.contact_avatar))
            avatar_exists = True
        else:
            cand = BASE_ASSETS / "avatars" / scenario.contact_avatar
            if cand.exists():
                scenario.contact_avatar = str(cand)
                avatar_exists = True

    if not avatar_exists:
        if getattr(scenario, "is_group", False):
            # Grup profil resmi şahıs fotoğrafı değil; tematik nötr arkaplan olmalı
            thematic_wps = ["doodle_beige.jpg", "urban_wall.jpg", "cozy_wood.jpg", "botanical_shadow.jpg"]
            for tw in thematic_wps:
                cand = BASE_ASSETS / "wallpapers" / tw
                if cand.exists():
                    scenario.contact_avatar = str(cand)
                    scenario.profile_avatar = str(cand)
                    break
        else:
            gender = getattr(scenario, "contact_avatar_gender", None) or (script_data.get("contact_avatar_gender") if script_data else None)
            if not gender:
                cname = (scenario.contact_name or "").lower()
                if any(w in cname for w in ["anne", "merve", "ayşe", "zeynep", "fatma", "aşkım", "prenses", "sevgili", "kız", "valide", "abla", "kaynana", "hatun", "karım", "bayan", "hanım"]):
                    gender = "female"
                else:
                    gender = "male"
            def_avatar = str(BASE_ASSETS / "avatars" / f"{gender}.png")
            if os.path.exists(def_avatar):
                scenario.contact_avatar = def_avatar
                scenario.profile_avatar = def_avatar

    # BGM Ayarları - Senaryoya uygun akıllı viral komedi fon müziği
    if not scenario.bgm_track or scenario.bgm_track in ("none", ""):
        scenario.bgm_track = "auto"
    scenario.bgm_enabled = True
    scenario.bgm_volume = 0.20

    # 3. TTS Seslendirme (Chatterbox veya Edge-TTS)
    tts_pref = merged_edit_opts.get("tts_engine") or channel_config.get("tts_engine") or "auto"
    print(f"[WhatsApp] Dublaj seslendirmesi üretiliyor ({len(scenario.messages)} replik, Motor: {tts_pref})...")
    tts_engine = TTSEngine(output_dir=audio_dir, backend=tts_pref, language=language)
    scenario = tts_engine.run_sync(scenario)

    # 4. Ses Miksajı (Sesler + SFX + BGM)
    master_audio_path = str(work_dir / "master_audio.wav")
    mixer = AudioMixer(output_path=master_audio_path)
    norm_loudness = merged_edit_opts.get("normalize_audio_loudness", True)
    if isinstance(norm_loudness, str):
        norm_loudness = norm_loudness.lower() in ("true", "1", "yes")
    master_audio, total_duration = mixer.mix_scenario_audio(scenario, normalize_loudness=bool(norm_loudness))
    print(f"[WhatsApp] Ses miksajı tamamlandı (EBU R128: {bool(norm_loudness)}). Süre: {total_duration:.1f}sn")

    # 5. 1080x1920 Video Render (Remotion veya Fallback: Playwright)
    output_video_path = str(work_dir / "final.mp4")
    render_temp_dir = str(work_dir / "render_temp")
    
    # Layout seçimi: Varsayılan olarak @1dublaj tarzı dublaj_style
    req_layout = merged_edit_opts.get("layout") or getattr(scenario, "layout", None) or "dublaj_style"
    scenario.layout = req_layout

    # compact_top seçilirse ASMR arka planı hazırla (dublaj_style modunda ASMR gerekmez)
    asmr_bg_file = None
    if scenario.layout == "compact_top":
        try:
            try:
                from asmr_manager import prepare_asmr_background
            except ImportError:
                from src.asmr_manager import prepare_asmr_background

            candidate_asmr = str(work_dir / "bottom_asmr.mp4")
            print(f"[WhatsApp] ASMR/Gameplay arka planı hazırlanıyor (Süre: {total_duration + 3.0:.1f}s)...")
            prepare_asmr_background(
                target_duration=total_duration + 3.0,
                output_path=candidate_asmr,
                width=1080,
                height=960,
                fps=30
            )
            if os.path.exists(candidate_asmr) and os.path.getsize(candidate_asmr) > 1000:
                asmr_bg_file = candidate_asmr
        except Exception as asmr_err:
            print(f"[WhatsApp] ASMR arka plan hazırlama uyarısı: {asmr_err}")

    rendered_with_remotion = False
    try:
        try:
            from remotion_renderer import is_remotion_available, render_whatsapp_video_remotion
        except ImportError:
            from src.remotion_renderer import is_remotion_available, render_whatsapp_video_remotion

        if is_remotion_available():
            print(f"[WhatsApp] Avant-garde Remotion React motoru ile 1080x1920 video render ediliyor (Layout: {scenario.layout})...")
            base_avatars_dir = Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets" / "avatars"
            female_kw = ["anne", "valide", "mami", "mom", "teyze", "hala", "kaynana", "ayşe", "fatma", "merve", "zeynep", "kız", "abla"]
            dad_kw = ["baba", "dede", "ev sahibi", "hacı", "dayı", "amca", "patron", "usta", "yönetici", "halil", "bey"]

            messages_data = []
            for idx, m in enumerate(scenario.messages):
                s_name = getattr(m, "sender_name", None)
                s_avatar = getattr(m, "sender_avatar", None)
                
                # ── AVATAR TUTARLILIK MOTORU (Zero Mismatch Guarantee) ──
                if m.sender != "user":
                    if not getattr(scenario, "is_group", False):
                        # Birebir sohbette gelen tüm mesajlar ve yazıyor ikonu kesinlikle senaryo avatarı ile eşleşmeli
                        s_avatar = scenario.contact_avatar
                    else:
                        # Grup sohbetinde gönderenin avatarı: önce custom_images eşleşmesine bak
                        clean_name = re.sub(r'[^\w\s]', '', s_name or '').strip().lower()
                        first_name = clean_name.split()[0] if clean_name else ''
                        matched_custom = (
                            participant_avatars.get((s_name or "").lower()) or
                            participant_avatars.get(clean_name) or
                            participant_avatars.get(first_name) or
                            participant_avatars.get(str(idx + 1))
                        )
                        if matched_custom and os.path.exists(matched_custom):
                            s_avatar = matched_custom
                        elif not s_avatar or not os.path.exists(s_avatar):
                            low_name = (s_name or "").lower()
                            if any(w in low_name for w in female_kw):
                                if any(w in low_name for w in ["anne", "valide", "teyze", "hala"]) and (base_avatars_dir / "mom.jpg").exists():
                                    s_avatar = str(base_avatars_dir / "mom.jpg")
                                elif (base_avatars_dir / "girl.jpg").exists():
                                    s_avatar = str(base_avatars_dir / "girl.jpg")
                                else:
                                    s_avatar = ""
                            elif any(w in low_name for w in dad_kw):
                                if (base_avatars_dir / "dad.jpg").exists():
                                    s_avatar = str(base_avatars_dir / "dad.jpg")
                                else:
                                    s_avatar = ""
                            else:
                                if (base_avatars_dir / "boy.jpg").exists():
                                    s_avatar = str(base_avatars_dir / "boy.jpg")
                                else:
                                    s_avatar = ""
                    m.sender_avatar = s_avatar

                messages_data.append({
                    "id": idx + 1,
                    "sender": m.sender,
                    "text": m.text,
                    "time": getattr(m, "timestamp", None) or getattr(m, "time", None) or getattr(m, "time_str", None) or "14:24",
                    "sender_name": s_name,
                    "sender_avatar": s_avatar,
                    "sender_color": getattr(m, "sender_color", None),
                    "start_time": getattr(m, "start_time", 0.0),
                    "duration": getattr(m, "duration", 2.0)
                })

            # Instagram hesabı: Yalnızca kanalda açıkça tanımlıysa gönderilir; yoksa boş kalır
            raw_insta = channel_config.get("instagram_username") or merged_edit_opts.get("instagram_username") or ""
            insta_user = str(raw_insta).strip().lstrip("@") if raw_insta else ""

            # Dinamik ve Çeşitli WhatsApp Sohbet Arka Planı (Wallpaper Variety)
            base_wallpapers_dir = Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets" / "wallpapers"
            available_wallpapers = sorted([str(p) for p in base_wallpapers_dir.glob("*.jpg")])

            wp_path = getattr(scenario, "wallpaper_path", None)
            # Eğer arka plan verilmemişse veya eski statik floral_pastel ise çeşitlilik sağla
            if not wp_path or not os.path.exists(wp_path) or wp_path.endswith("floral_pastel.jpg"):
                if available_wallpapers:
                    seed_str = f"{scenario.title}_{len(scenario.messages)}_{getattr(scenario, 'contact_name', '')}"
                    wp_idx = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16) % len(available_wallpapers)
                    wp_path = available_wallpapers[wp_idx]
                else:
                    def_wp = base_wallpapers_dir / "floral_pastel.jpg"
                    if def_wp.exists():
                        wp_path = str(def_wp)

            default_status = "çevrimiçi" if is_tr else "online"
            rendered_with_remotion = render_whatsapp_video_remotion(
                contact_name=scenario.contact_name,
                contact_avatar=scenario.contact_avatar,
                audio_path=master_audio,
                messages_data=messages_data,
                output_path=output_video_path,
                fps=30,
                status_text=getattr(scenario, "contact_status", default_status) or default_status,
                bg_video_path=asmr_bg_file,
                layout=scenario.layout or "dublaj_style",
                watermark_text=scenario.watermark_username or channel_id or channel_name or ("yazanyazana" if is_tr else "crazyychats"),
                instagram_username=insta_user,
                theme=getattr(scenario, "theme", "light") or "light",
                wallpaper_path=wp_path,
                is_group=getattr(scenario, "is_group", False),
                group_participants=getattr(scenario, "group_participants", ""),
                language=language,
            )
    except Exception as rem_err:
        print(f"[WhatsApp] Remotion render istisnası ({rem_err}), Playwright'a geçiliyor...")

    if not rendered_with_remotion:
        print(f"[WhatsApp] Fallback: Playwright 1080x1920 video kaydı başlatılıyor...")
        renderer = VideoRenderer(temp_dir=render_temp_dir)
        renderer.render_video(
            scenario=scenario,
            master_audio_path=master_audio,
            total_duration=total_duration,
            output_mp4_path=output_video_path
        )

    # ── Post-processing: HyperFrames Kinetik Hook, Özel Intro ve Outro Klipleri ──
    merged_opts = edit_options or channel_config.get("edit_options", {}) or {}

    # 1. HyperFrames Kinetik Hook (videonun en başına dinamik animasyonlu başlık kartı ekle)
    enable_hf_hook = merged_opts.get("enable_hyperframes_hook", False)
    if isinstance(enable_hf_hook, str):
        enable_hf_hook = enable_hf_hook.lower() in ("true", "1", "yes")
    else:
        enable_hf_hook = bool(enable_hf_hook)

    if enable_hf_hook:
        try:
            try:
                from hyperframes_renderer import is_hyperframes_available, render_kinetic_hook, prepend_hook_to_video
            except ImportError:
                from src.hyperframes_renderer import is_hyperframes_available, render_kinetic_hook, prepend_hook_to_video

            if is_hyperframes_available():
                print(f"[HYPERFRAMES] WhatsApp videosu için kinetik hook üretiliyor: '{scenario.title[:35]}...'")
                hook_badge = merged_opts.get("hyperframes_hook_badge") or "WHATSAPP SHORTS"
                hook_out = work_dir / "hyperframes_hook.mp4"
                first_msg_text = scenario.messages[0].text if scenario.messages else ""
                rendered_hook = render_kinetic_hook(
                    title=scenario.title,
                    subtitle=first_msg_text[:75],
                    badge=hook_badge,
                    output_path=hook_out
                )
                if rendered_hook and rendered_hook.exists():
                    merged_target = work_dir / "final_with_hook.mp4"
                    if prepend_hook_to_video(rendered_hook, output_video_path, merged_target):
                        import shutil
                        shutil.move(str(merged_target), output_video_path)
                        print("[HYPERFRAMES] Kinetik hook WhatsApp videosunun başına başarıyla eklendi!")
        except Exception as hf_err:
            print(f"[HYPERFRAMES] WhatsApp hook ekleme uyarısı: {hf_err}")

    # 1.5 YouTube Shorts Thumb-Stop Hook Zoom Efekti (İlk 1.5s %105 -> %100)
    enable_hook_zoom = merged_opts.get("hook_intro_effect", False)
    if isinstance(enable_hook_zoom, str):
        enable_hook_zoom = enable_hook_zoom.lower() in ("true", "1", "yes")
    if bool(enable_hook_zoom) and os.path.exists(output_video_path):
        try:
            try:
                from hyperframes_renderer import apply_hook_zoom_filter
            except ImportError:
                from src.hyperframes_renderer import apply_hook_zoom_filter
            hook_zoom_target = work_dir / "final_with_zoom.mp4"
            print("[WhatsApp] 🎯 YouTube Shorts Thumb-stop hook zoom efekti uygulanıyor...")
            if apply_hook_zoom_filter(output_video_path, hook_zoom_target, hook_duration=1.5, start_scale=1.05):
                if hook_zoom_target.exists() and hook_zoom_target.stat().st_size > 1000:
                    import shutil
                    shutil.move(str(hook_zoom_target), output_video_path)
                    print("[WhatsApp] Thumb-stop hook zoom efekti başarıyla eklendi!")
        except Exception as hook_zoom_err:
            print(f"[WhatsApp] Hook zoom filtresi uyarısı: {hook_zoom_err}")

    # 2. Özel Intro ve Outro Klipleri (Varsa videoya ekle)
    intro_clip = merged_opts.get("intro_clip_path")
    outro_clip = merged_opts.get("outro_clip_path")
    if intro_clip or outro_clip:
        def _resolve_clip(p):
            if not p:
                return None
            pp = Path(p)
            if not pp.is_absolute():
                pp = Path(__file__).resolve().parent.parent.parent / p
            return str(pp) if pp.exists() else None

        res_intro = _resolve_clip(intro_clip)
        res_outro = _resolve_clip(outro_clip)
        if res_intro or res_outro:
            try:
                try:
                    from video_editor import VideoEditor, EditConfig
                except ImportError:
                    from src.video_editor import VideoEditor, EditConfig

                print(f"[WhatsApp] Intro/Outro klibi ekleniyor (intro={res_intro}, outro={res_outro})...")
                editor = VideoEditor(EditConfig(width=1080, height=1920, fps=30))
                tmp_io_target = str(work_dir / "final_with_intro_outro.mp4")
                if editor.burner.concat_with_intro_outro(res_intro, output_video_path, res_outro, tmp_io_target):
                    if os.path.exists(tmp_io_target) and os.path.getsize(tmp_io_target) > 1000:
                        import shutil
                        shutil.move(tmp_io_target, output_video_path)
                        print("[WhatsApp] Intro/Outro klipleri başarıyla eklendi!")
            except Exception as io_err:
                print(f"[WhatsApp] Intro/Outro birleştirme hatası: {io_err}")

    # Geriye dönük uyumluluk için video.mp4 kopyası
    legacy_video_path = str(work_dir / "video.mp4")
    if os.path.exists(output_video_path):
        try:
            import shutil
            shutil.copyfile(output_video_path, legacy_video_path)
        except Exception:
            pass


    # 6. Küçük Resim (Thumbnail) Çıkar (Videonun ortasından bir kare al)
    thumb_path = str(work_dir / "thumbnail.jpg")
    try:
        thumb_time = min(total_duration / 2.0, 5.0)
        cmd_thumb = [
            "ffmpeg", "-y",
            "-ss", str(thumb_time),
            "-i", output_video_path,
            "-vframes", "1",
            "-q:v", "2",
            thumb_path
        ]
        subprocess.run(cmd_thumb, capture_output=True, check=True)
    except Exception as e:
        print(f"[WhatsApp] Thumbnail çıkarma uyarısı: {e}")

    # 7. Metadata Hazırla
    raw_title = scenario.title or ("WhatsApp Konuşmaları" if is_tr else "WhatsApp Chats")
    clean_title = re.sub(r'#\w+', '', raw_title).strip()
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    title = clean_title if clean_title else ("Komik WhatsApp Konuşması 😂" if is_tr else "Funny WhatsApp Chat 😂")

    clean_channel_brand = channel_name if channel_name and channel_name.lower() not in ("bidublaj", "birdublaj") else ("Kanalımız" if is_tr else "Our Channel")
    channel_tag = f" #{clean_channel_brand.replace(' ', '')}" if clean_channel_brand not in ("Kanalımız", "Our Channel") else ""

    text_corpus = " ".join([scenario.title] + [m.text for m in scenario.messages]).lower()

    if is_tr:
        description = (
            f"{title}\n\n"
            "Merhaba! Bu kanalda kendi yazmış ve seslendirmiş olduğumuz eğlenceli konuşmaları paylaşıyoruz. "
            "Konuşmaların ve seslendirmelerin hepsi özgün ve bize aittir. "
            "Hepsi gerçek olaylardan ilham alınarak, tarafımızca yazılmakta ve seslendirilmektedir. "
            "Videodaki filigran hariç videoyu herhangi bir sayfada görürseniz, orijinalinin bu kanala ait olduğunu lütfen hatırlayınız. "
            "Onun haricinde herkese iyi seyirler dileriz! 😊\n\n"
            f"#whatsapp #diyalog #seslendirme #dublaj #komedi #mizah #keşfet #shorts #eğlence #türkçe{channel_tag}"
        )
        tags = [
            "konuşma", "diyalog", "seslendirme", "türkçe", "türkçe seslendirme", "dublaj",
            "türkçe dublaj", "whatsapp", "komik", "komedi", "eğlence", "eğlenceli", "içerik",
            "shorts", "keşfet", "keşfetteyiz", "kesfet", "kesfetteyiz", "replik", "viral", "trend", "akım"
        ]
        if any(w in text_corpus for w in ["anne", "baba", "aile", "evlat", "oğul", "kızım", "dede"]):
            tags.extend(["aile", "anne", "baba", "evlat"])
        if any(w in text_corpus for w in ["ev sahibi", "apartman", "kira", "yönetici", "komşu"]):
            tags.extend(["apartman", "komşu", "evsahibi", "mizah"])
        if any(w in text_corpus for w in ["kanka", "arkadaş", "troll", "dostum"]):
            tags.extend(["kanka", "arkadaş", "troll"])
    else:
        description = (
            f"{title}\n\n"
            "Welcome! On this channel we share hilarious, original text conversations and chat stories. "
            "All conversations and voiceovers are original creations produced by our team. "
            "Inspired by funny, awkward, and relatable everyday moments. "
            "If you see this video elsewhere without our watermark, remember it originated right here. "
            "Enjoy watching and subscribe for more daily chats! 😊\n\n"
            f"#whatsapp #texts #textstory #funny #comedy #humor #shorts #viral #chatstory{channel_tag}"
        )
        tags = [
            "whatsapp", "text story", "funny texts", "chat story", "comedy", "funny",
            "shorts", "viral", "humor", "relatable", "trending", "animation", "entertainment",
            "chat", "texting", "story", "parody"
        ]
        if any(w in text_corpus for w in ["mom", "dad", "family", "son", "daughter", "grandpa", "parents"]):
            tags.extend(["family", "mom", "dad", "parents"])
        if any(w in text_corpus for w in ["boss", "work", "job", "office", "fired"]):
            tags.extend(["work", "office", "boss", "job"])
        if any(w in text_corpus for w in ["friend", "bro", "bestie", "roommate"]):
            tags.extend(["bestie", "friends", "roommate", "bro"])

    if clean_channel_brand not in ("Kanalımız", "Our Channel"):
        tags.append(clean_channel_brand)

    # Benzersiz etiketler listesi
    seen_tags = set()
    unique_tags = []
    for t in tags:
        if t.lower() not in seen_tags and t.lower() not in ("bidublaj", "birdublaj", "hamzadublaj"):
            seen_tags.add(t.lower())
            unique_tags.append(t)
    tags = unique_tags

    narration_text = " ".join(m.text for m in scenario.messages)
    scenes_list = [{"narration": narration_text, "image_prompt": "whatsapp_chat"}]
    script_obj = {
        "title": title,
        "description": description,
        "tags": tags,
        "keywords": ["whatsapp", "comedy", "shorts", "mizah", "dublaj", "türkçe"] if is_tr else ["whatsapp", "comedy", "shorts", "funny texts", "text story", "humor"],
        "narration": narration_text,
        "scenes": scenes_list,
        "messages": [m.__dict__ for m in scenario.messages],
        "category": "whatsapp_stories"
    }

    # Casper AI SEO & A/B Metadata Zenginleştirmesi
    try:
        try:
            from script_writer import _enrich_script_metadata
        except ImportError:
            from src.script_writer import _enrich_script_metadata
        script_obj = _enrich_script_metadata(script_obj, channel_config)
    except Exception as enrich_err:
        print(f"[WhatsApp] Metadata zenginleştirme uyarısı: {enrich_err}")

    final_desc = script_obj.get("search_optimized_description") or description
    seo_hashtags = script_obj.get("seo_hashtags") or []
    pinned_comment = (script_obj.get("pinned_comment_poll") or {}).get("full_text")

    metadata = {
        "title": title,
        "description": final_desc,
        "search_optimized_description": final_desc,
        "seo_hashtags": seo_hashtags,
        "pinned_comment": pinned_comment,
        "tags": script_obj.get("tags") or tags,
        "keywords": ["whatsapp", "comedy", "shorts", "mizah"] if is_tr else ["whatsapp", "comedy", "shorts", "funny texts"],
        "channel_id": channel_id,
        "channel_name": channel_name,
        "topic": prompt_to_use,
        "narration": narration_text,
        "scenes": scenes_list,
        "script": script_obj,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration": total_duration,
        "video_path": output_video_path,
        "thumbnail_path": thumb_path if os.path.exists(thumb_path) else None,
        "shorts_mode": True,
        "plan_id": planned_row.get("id") if planned_row else ""
    }

    metadata_file = work_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    video_info = {
        "title": title,
        "description": final_desc,
        "desc": final_desc,
        "search_optimized_description": final_desc,
        "seo_hashtags": seo_hashtags,
        "pinned_comment": pinned_comment,
        "tags": script_obj.get("tags") or tags,
        "keywords": ["whatsapp", "comedy", "shorts", "mizah"] if is_tr else ["whatsapp", "comedy", "shorts", "funny texts"],
        "duration": total_duration,
        "shorts_mode": True,
        "format": "1080x1920",
        "category": "whatsapp_stories"
    }
    (work_dir / "video_info.json").write_text(json.dumps(video_info, ensure_ascii=False, indent=2), encoding="utf-8")

    # Otomatik Yerel AI ile Viral Başlık, Açıklama ve Etiket Optimizasyonu
    try:
        from src.ai_metadata_generator import auto_generate_and_apply_metadata
        auto_generate_and_apply_metadata(work_dir, channel_id=channel_id)
    except Exception as meta_ai_err:
        try:
            from ai_metadata_generator import auto_generate_and_apply_metadata
            auto_generate_and_apply_metadata(work_dir, channel_id=channel_id)
        except Exception:
            pass

    return {
        "video_path": output_video_path,
        "title": title,
        "description": description,
        "tags": tags,
        "shorts_mode": True,
        "transition": "whatsapp_chat",
        "work_dir": str(work_dir),
        "folder": str(work_dir),
    }
