"""
main.py
Ana orkestratör — video üretir, her video için ayrı klasör + metadata.txt oluşturur.
YouTube yükleme yapılmaz, sadece yerel dosya üretimi.

Kullanım:
  python main.py                    # Tüm aktif kanalları çalıştır
  python main.py --channel ch_001   # Sadece belirli bir kanal
  python main.py --provider gemini  # Gemini ile üret
  python main.py --setup            # Kanal kurulum sihirbazı
"""

import os
import sys
import json
import argparse
import traceback
from datetime import datetime
from pathlib import Path

from channel_manager import ChannelManager
from script_writer import ScriptWriter
from video_generator import VideoGenerator


# ── Ortam değişkenleri ve Ayarlar (fallback) ───────────────────
from settings_manager import SettingsManager
_settings = SettingsManager()

ANTHROPIC_API_KEY = _settings.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY    = _settings.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
NASA_API_KEY      = _settings.get("nasa_api_key") or os.environ.get("NASA_API_KEY", "DEMO_KEY")
OUTPUT_DIR        = _settings.get("output_dir") or os.environ.get("OUTPUT_DIR", "output")


def save_metadata(folder: Path, script: dict, video_path: str, plan_id: str = "", channel_config: dict = None):
    """Video metadata'sını json dosyasına yazar (Dile ve kategoriye özel açıklamaları korur ve boş kalmamasını garanti eder)."""
    import json
    from channel_manager import get_localized_metadata, is_bogus_fallback

    existing_meta = {}
    meta_path = folder / "metadata.json"
    if meta_path.exists():
        try:
            existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    existing_vinfo = {}
    vinfo_path = folder / "video_info.json"
    if vinfo_path.exists():
        try:
            existing_vinfo = json.loads(vinfo_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    lang = (
        script.get("language") or 
        (channel_config.get("language") if channel_config else None) or 
        existing_meta.get("language") or 
        "tr"
    )
    cat = (
        (channel_config.get("topic_category") if channel_config else None) or 
        script.get("category") or 
        existing_meta.get("category") or 
        "reddit_stories"
    )

    # Sahneleri birleştirerek tam narration'ı oluştur (boşsa)
    narration = script.get("narration", "")
    scenes = script.get("scenes", [])
    if not narration and scenes:
        narration = " ".join(s.get("narration", "") for s in scenes)
    if not narration:
        narration = existing_meta.get("narration", "")

    title = (
        script.get("title") or 
        existing_meta.get("title") or 
        existing_vinfo.get("title") or 
        folder.name
    )

    desc = (
        script.get("description") or 
        existing_meta.get("description") or 
        existing_vinfo.get("description") or 
        existing_vinfo.get("desc") or 
        ""
    ).strip()

    tags = (
        script.get("tags") or 
        existing_meta.get("tags") or 
        existing_vinfo.get("tags") or 
        []
    )
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    # Açıklama veya etiket boşsa ya da eski hardcoded Türkçe WhatsApp varsayılanı kalmışsa dile uygun oluştur
    if not desc or is_bogus_fallback(desc, tags, language=lang, category=cat):
        loc_desc, loc_tags = get_localized_metadata(title, language=lang, category=cat)
        if not desc or is_bogus_fallback(desc, [], language=lang, category=cat):
            desc = loc_desc
        if not tags or is_bogus_fallback("", tags, language=lang, category=cat):
            tags = loc_tags

    if not tags:
        _, loc_tags = get_localized_metadata(title, language=lang, category=cat)
        tags = loc_tags

    keywords = (
        script.get("keywords") or 
        existing_meta.get("keywords") or 
        existing_vinfo.get("keywords") or 
        tags
    )

    meta_data = {
        "title": title,
        "description": desc,
        "tags": tags,
        "language": lang,
        "topic": script.get("topic") or existing_meta.get("topic") or "",
        "narration": narration,
        "keywords": keywords,
        "scenes": scenes or existing_meta.get("scenes", []),
        "script": script,
        "plan_id": plan_id or existing_meta.get("plan_id", ""),
        "created_at": existing_meta.get("created_at") or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    meta_path.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[META] Metadata kaydedildi → {meta_path} (Açıklama: {len(desc)} kr, Etiketler: {len(tags)} adet)")

    # video_info.json'u da senkronize et
    try:
        vinfo_data = dict(existing_vinfo)
        vinfo_data["title"] = title
        vinfo_data["description"] = desc
        vinfo_data["desc"] = desc
        vinfo_data["tags"] = tags
        vinfo_data["keywords"] = keywords
        vinfo_path.write_text(json.dumps(vinfo_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    # Otomatik Yerel AI ile Viral Başlık, Açıklama ve Etiket Optimizasyonu
    try:
        from ai_metadata_generator import auto_generate_and_apply_metadata
        ch_id = channel_config.get("id") if channel_config else ""
        auto_generate_and_apply_metadata(folder, channel_id=ch_id)
    except Exception as meta_ai_err:
        print(f"[META] ⚠️ Otomatik AI metadata üretimi uyarısı: {meta_ai_err}")


def run_channel(
    channel_config: dict,
    writer: ScriptWriter,
    generator: VideoGenerator,
    manager: ChannelManager,
    output_dir: str = "output",
    shorts_mode: bool = False,
    transition: str = "fade",
    edit_options: dict = None,
    force_row_id: str = None,
    custom_script: dict = None,
    custom_images: dict = None,
    recompose_folder: Optional[str] = None,
    explicit_plan_id: str = None,
) -> dict:
    """Tek bir kanal için video üretim pipeline'ı çalıştırır."""
    channel_id  = channel_config["channel_id"]
    lang        = channel_config.get("language", "en")
    shorts_mode = shorts_mode or channel_config.get("shorts_mode", False)
    transition  = channel_config.get("transition", transition)

    # Kanal-bazlı edit_options merge (kanal override + global settings)
    if edit_options is None:
        edit_options = manager.get_resolved_edit_options(channel_id)

    print(f"\n{'='*60}")
    print(f"📺 Kanal: {channel_config['name']} ({channel_id})")
    print(f"   Dil: {lang}  |  Shorts: {shorts_mode}  |  Geçiş: {transition}")
    sub_preset = edit_options.get("subtitle_preset", "bold")
    sub_anim   = edit_options.get("subtitle_animation", "fade")
    print(f"   Subtitle: {sub_preset} / {sub_anim}")
    if edit_options.get("bgm_path"):
        print(f"   BGM: {os.path.basename(edit_options['bgm_path'])}")
    if edit_options.get("watermark_text") or edit_options.get("watermark_path"):
        print(f"   Watermark: {edit_options.get('watermark_text') or os.path.basename(edit_options.get('watermark_path', ''))}")
    print(f"{'='*60}")

    result = {
        "channel_id": channel_id,
        "success": False,
        "video_path": None,
        "folder": None,
        "error": None,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Plan kontrolü
        from content_planner import ContentPlanner
        out_path = Path(output_dir)
        channel_dir = out_path / channel_id
        planner = ContentPlanner(channel_dir)
        planned_item = None
        planned_topic = None
        if planner.plan_exists():
            if force_row_id == "no_plan":
                planned_item = None
            elif force_row_id:
                planned_item = planner.get_row_by_id(force_row_id)
            else:
                planned_item = planner.get_next_unproduced()
                
            if planned_item:
                planned_topic = planned_item.get("konu", "")
                print(f"[RUN] Planlanmış konu kullanılacak: '{planned_topic}' (Sıra ID: {planned_item.get('id')})")
                
                secilen_muzik = planned_item.get("secilen_muzik")
                if secilen_muzik:
                    from audio_library import get_track_by_id, download_track
                    track_info = get_track_by_id(secilen_muzik)
                    if track_info:
                        print(f"[RUN] Seçilen fon müziği indiriliyor/hazırlanıyor: {track_info['title']}...")
                        downloaded_path = download_track(secilen_muzik, Path("config/bgm"))
                        if downloaded_path and downloaded_path.exists():
                            edit_options["bgm_path"] = str(downloaded_path)
                            print(f"[RUN] BGM başarıyla güncellendi: {downloaded_path}")
                        else:
                            print(f"[RUN] Uyarı: Seçilen müzik indirilemedi, varsayılan müzik kullanılacak.")
        
        # 1. Senaryo yaz
        if recompose_folder:
            meta_path = Path(recompose_folder) / "metadata.json"
            if meta_path.exists():
                try:
                    script = json.loads(meta_path.read_text(encoding="utf-8"))
                    print(f"[RUN] Recompose modu: Mevcut senaryo metadata.json dosyasından yüklendi.")
                except Exception as e:
                    raise RuntimeError(f"Recompose senaryo okuma hatası: {e}")
            else:
                # Fallback to planned item / default if metadata.json doesn't exist
                if custom_script:
                    script = custom_script
                elif planned_topic:
                    script = writer.write(channel_config, planned_topic=planned_topic)
                else:
                    script = writer.write(channel_config)
        else:
            if custom_script:
                script = custom_script
                print(f"[RUN] Gemini Web araciligiyla gelen hazir senaryo kullaniliyor.")
            elif planned_topic:
                script = writer.write(channel_config, planned_topic=planned_topic)
            else:
                script = writer.write(channel_config)

        # 2. Video üret (Kanal AI QA aktifse 'kontrol', değilse 'yuklenecek' klasörüne)
        is_auto_qa = bool(
            channel_config.get("auto_ai_qa_enabled") or
            channel_config.get("auto_ai_qa", {}).get("enabled") or
            (channel_config.get("edit_options") or {}).get("auto_ai_qa_enabled")
        )
        target_sub = "kontrol" if is_auto_qa else "yuklenecek"
        channel_target_dir = channel_dir / target_sub
        channel_target_dir.mkdir(parents=True, exist_ok=True)

        video_result = generator.run(
            script=script,
            lang=lang,
            output_dir=str(channel_target_dir),
            channel_id=channel_id,
            shorts_mode=shorts_mode,
            transition=transition,
            edit_options=edit_options,
            custom_images=custom_images,
            recompose_folder=recompose_folder,
        )

        # 3. Metadata dosyasını video klasörüne yaz
        video_folder = Path(video_result["video_path"]).parent
        plan_id = planned_item.get("id", "") if planned_item else ""
        if explicit_plan_id:
            plan_id = explicit_plan_id
        save_metadata(video_folder, script, video_result["video_path"], plan_id=plan_id, channel_config=channel_config)

        # Planı üretildi olarak işaretle
        if planned_item:
            planner.mark_as_produced(planned_item["id"])

        # Klasörün relative yolunu (örn. ch_uzay/yuklenecek/folder_name) folder olarak kaydet
        try:
            rel_folder = video_folder.relative_to(out_path)
            folder_str = str(rel_folder)
        except Exception:
            folder_str = str(video_folder)

        result["success"] = True
        result["video_path"] = video_result["video_path"]
        result["folder"] = folder_str
        result["title"] = video_result["title"]
        result["description"] = video_result.get("description", "")
        result["tags"] = video_result.get("tags", [])
        result["language"] = lang
        result["plan_id"] = plan_id
        result["shorts_mode"] = shorts_mode
        result["transition"] = transition

        # 4. Son çalışma zamanını güncelle
        manager.update_last_run(channel_id)
        print(f"✅ Video hazır: {video_result['video_path']}")
        print(f"   Klasör: {folder_str}")

    except Exception as e:
        import io
        tb_buf = io.StringIO()
        traceback.print_exc(file=tb_buf)
        tb_str = tb_buf.getvalue()
        result["error"] = f"{e}\n\nTraceback:\n{tb_str}"
        print(f"❌ Hata [{channel_id}]: {e}")
        print(tb_str)

    return result



def setup_wizard(manager: ChannelManager):
    """Etkileşimli kanal kurulum sihirbazı."""
    print("\n🚀 YENİ KANAL KURULUM SİHİRBAZI")
    print("─" * 40)

    channel_id = input("Kanal ID (benzersiz, ör: ch_uzay_tr): ").strip()
    name       = input("Kanal adı (ör: Uzay Keşifleri): ").strip()
    language   = input("Dil kodu (ör: tr, en, de, fr, es, ja ...): ").strip()
    topic_cat  = input("Konu kategorisi [space/planets/astronomy] (varsayılan: space): ").strip() or "space"
    sched      = input("Günlük yayın saati (0-23, varsayılan: 9): ").strip() or "9"

    custom_raw = input("Özel konular (virgülle ayır, boş bırak = otomatik): ").strip()
    custom_topics = [t.strip() for t in custom_raw.split(",") if t.strip()] if custom_raw else []

    channel = manager.add_channel(
        channel_id=channel_id,
        name=name,
        language=language,
        topic_category=topic_cat,
        custom_topics=custom_topics,
        schedule_hour=int(sched),
    )

    print(f"\n✅ Kanal eklendi: {name} ({channel_id})")
    return channel


def main():
    from settings_manager import SettingsManager
    sm = SettingsManager()
    
    default_provider = sm.get("ai_provider", "claude")
    default_model = sm.get("ai_model", "")
    default_ollama_url = sm.get("ollama_url", "http://localhost:11434")
    default_lmstudio_url = sm.get("lmstudio_url", "http://localhost:1234/v1")

    parser = argparse.ArgumentParser(description="YouTube Video Üretim Sistemi")
    parser.add_argument("--channel",    help="Sadece bu kanal ID'sini çalıştır")
    parser.add_argument("--provider",   default=default_provider, choices=["claude", "gemini", "ollama", "lmstudio"],
                        help="AI provider: claude, gemini, ollama, lmstudio")
    parser.add_argument("--model",      default=default_model, help="Kullanılacak model adı (opsiyonel)")
    parser.add_argument("--ollama-url", default=default_ollama_url, help="Ollama sunucu URL'i")
    parser.add_argument("--lmstudio-url", default=default_lmstudio_url, help="LM Studio sunucu URL'i")
    parser.add_argument("--setup",      action="store_true", help="Yeni kanal kurulum sihirbazı")
    parser.add_argument("--list",       action="store_true", help="Kanalları listele")
    args = parser.parse_args()

    manager = ChannelManager()

    if args.setup:
        setup_wizard(manager)
        return

    if args.list:
        print(manager.summary())
        return

    # AI provider seçimi
    api_key = ""
    if args.provider == "claude":
        api_key = ANTHROPIC_API_KEY
        if not api_key:
            print("HATA: ANTHROPIC_API_KEY ortam değişkeni veya ayarı bulunamadı.")
            sys.exit(1)
    elif args.provider == "gemini":
        api_key = GEMINI_API_KEY
        if not api_key:
            print("HATA: GEMINI_API_KEY ortam değişkeni veya ayarı bulunamadı.")
            sys.exit(1)

    # Model fallback: argüman boşsa provider'a özel ayara bak
    model_to_use = args.model
    if not model_to_use:
        if args.provider == "ollama":
            model_to_use = sm.get("ollama_model", "llama3")
        elif args.provider == "lmstudio":
            model_to_use = sm.get("lmstudio_model", "")
        else:
            model_to_use = sm.get("ai_model", "")

    writer = ScriptWriter(
        provider=args.provider,
        api_key=api_key,
        model=model_to_use,
        ollama_url=args.ollama_url,
        lmstudio_url=args.lmstudio_url,
    )
    generator = VideoGenerator(nasa_api_key=NASA_API_KEY)

    # Kanal seçimi
    if args.channel:
        channel = manager.get_channel(args.channel)
        if not channel:
            print(f"Kanal bulunamadı: {args.channel}")
            sys.exit(1)
        channels = [channel]
    else:
        channels = manager.get_active_channels()
        if not channels:
            print("Aktif kanal yok. 'python main.py --setup' ile ekleyin.")
            sys.exit(0)

    print(f"\n🎬 {len(channels)} kanal için video üretimi başlıyor...")
    print(f"   AI Provider: {args.provider.upper()}")
    print(f"   Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []
    for ch in channels:
        r = run_channel(ch, writer, generator, manager, output_dir=OUTPUT_DIR)
        results.append(r)

    # Özet
    success = sum(1 for r in results if r["success"])
    fail    = len(results) - success

    print(f"\n{'='*60}")
    print(f"📊 ÖZET: {success} başarılı, {fail} başarısız / {len(results)} toplam")
    for r in results:
        icon = "✅" if r["success"] else "❌"
        info = r.get("folder") or r.get("error") or "-"
        print(f"  {icon} {r['channel_id']}: {info}")
    print(f"{'='*60}\n")

    # JSON log
    log_path = Path(OUTPUT_DIR) / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_path.parent.mkdir(exist_ok=True)
    log_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Log kaydedildi → {log_path}")


if __name__ == "__main__":
    main()
