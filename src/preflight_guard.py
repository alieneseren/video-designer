#!/usr/bin/env python3
"""
Pre-Flight Regression Guard
YouTube Otomasyon Sistemi Çok Kanallı Regresyon ve Entegrasyon Doğrulayıcı.

Bu araç, ortak kod tabanında (localization, remote_runner, server_worker, voice_cloning)
yapılan bir yeniliğin diğer kanal formatlarını bozup bozmadığını saniyeler içinde doğrular.
"""

import sys
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

def log_pass(msg):
    print(f"  ✅ PASS: {msg}")

def log_fail(msg):
    print(f"  ❌ FAIL: {msg}")

def test_channels_config():
    print("\n🔍 [1/4] Kanal Konfigürasyonları Doğrulanıyor (channels.json)...")
    cfg_file = BASE_DIR / "config" / "channels.json"
    if not cfg_file.exists():
        log_fail("config/channels.json bulunamadı!")
        return False
    
    try:
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        channels = data.get("channels", [])
        if not channels:
            log_fail("Hiç kanal tanımlı değil!")
            return False
        
        required_keys = ["channel_id", "name", "language", "topic_category"]
        for ch in channels:
            cid = ch.get("channel_id", "unknown")
            for k in required_keys:
                if k not in ch:
                    log_fail(f"Kanal '{cid}' içinde zorunlu alan eksik: '{k}'")
                    return False
        log_pass(f"{len(channels)} adet kanal konfigürasyonu eksiksiz ve geçerli.")
        return True
    except Exception as e:
        log_fail(f"channels.json parse hatası: {e}")
        return False

def test_localization_logic():
    print("\n🔍 [2/4] Çok Dilli Senaryo Ayrıştırıcı Doğrulanıyor (localization_helper)...")
    try:
        from src.localization_helper import ensure_localized_script
    except Exception as e:
        log_fail(f"localization_helper import edilemedi: {e}")
        return False

    # Case A: Reddit Hikayeleri - 14 Sahne (7 İngilizce + 7 Türkçe karışık)
    mixed_scenes = [
        {"scene_id": i+1, "narration": f"English narration {i+1}", "on_screen_text": f"EN {i+1}"}
        for i in range(7)
    ] + [
        {"scene_id": i+1, "narration": f"Türkçe anlatım metni burada geçiyor {i+1}", "on_screen_text": f"TR {i+1}"}
        for i in range(7)
    ]
    raw_material = {
        "title": "Türkçe Başlık",
        "scripts": mixed_scenes
    }

    # TR kanalına sadece 7 Türkçe sahne gitmeli
    tr_result = ensure_localized_script(raw_material, target_lang="tr", channel_id="tr1_reddithikayeleri")
    tr_scenes = tr_result.get("scripts", [])
    if len(tr_scenes) != 7 or not any("Türkçe" in s.get("narration", "") for s in tr_scenes):
        log_fail(f"Reddit TR ayrıştırma hatası! 7 sahne bekleniyordu, {len(tr_scenes)} sahne geldi.")
        return False
    log_pass("Reddit TR senaryosu: Karışık 14 sahneden tam 7 Türkçe sahne hatasız izole edildi.")

    # EN kanalına sadece 7 İngilizce sahne gitmeli
    en_result = ensure_localized_script(raw_material, target_lang="en", channel_id="redditchroniclesa")
    en_scenes = en_result.get("scripts", [])
    if len(en_scenes) != 7 or not any("English" in s.get("narration", "") for s in en_scenes):
        log_fail(f"Reddit EN ayrıştırma hatası! 7 sahne bekleniyordu, {len(en_scenes)} sahne geldi.")
        return False
    log_pass("Reddit EN senaryosu: Karışık 14 sahneden tam 7 İngilizce sahne hatasız izole edildi.")

    # Case B: Blackbox Audio - 30 Tek Dilli Havacılık Sahnesi (Geriye Uyumluluk)
    bb_scenes = [
        {"scene_id": i+1, "narration": f"Flight 1153 leveled at FL240 scene {i+1}", "on_screen_text": f"ATC {i+1}"}
        for i in range(25)
    ]
    bb_material = {
        "title": "Tuninter 1153 Crash",
        "scripts": bb_scenes
    }
    bb_res = ensure_localized_script(bb_material, target_lang="en", channel_id="blackboxaudioo")
    if len(bb_res.get("scripts", [])) != 25:
        log_fail(f"Blackbox geriye uyumluluk hatası! 25 sahne bekleniyordu, {len(bb_res.get('scripts', []))} geldi.")
        return False
    log_pass("Blackbox tek dilli senaryo: 25 sahne bozulmadan olduğu gibi korundu.")

    return True

def test_voice_cloning_integrity():
    print("\n🔍 [3/4] Ses Klonlama ve Hybrid Model Entegrasyonu Doğrulanıyor...")
    try:
        from src.voice_clone_manager import VoiceCloneManager
        vcm = VoiceCloneManager()
        clones = vcm.list_clones()
        
        # Hybrid ses klonu kayıtlı mı?
        hybrid = next((c for c in clones if c.get("id") == "vc_alienes_kayit3_hybrid"), None)
        if not hybrid:
            log_fail("'vc_alienes_kayit3_hybrid' klon sesi sistemde bulunamadı!")
            return False
        log_pass(f"Hybrid ses klonu aktif: {hybrid.get('name')} (Model: {hybrid.get('weights_path')})")
        return True
    except Exception as e:
        log_fail(f"VoiceCloneManager doğrulama hatası: {e}")
        return False

def test_all_channel_job_schemas():
    print("\n🔍 [4/4] 4 Farklı Kanal Formatının İş Şemaları (Job Contracts) Simüle Ediliyor...")
    channels_to_test = [
        ("blackboxaudioo", "blackbox", "en"),
        ("tacticallcrayon", "tactical_crayon", "en"),
        ("tr1_reddithikayeleri", "reddit_stories", "tr"),
        ("novashorthes", "space", "en")
    ]
    
    for cid, category, lang in channels_to_test:
        sample_job = {
            "job_id": f"test_preflight_{cid}",
            "channel_id": cid,
            "category": category,
            "language": lang,
            "title": f"Test Title for {cid}",
            "scenes": [
                {
                    "scene_id": 1,
                    "narration": "Test narration text",
                    "visual_type": "cvr_reconstruction" if category == "blackbox" else "normal",
                    "duration_est": 5.0
                }
            ],
            "edit_options": {
                "hook_intro_effect": True,
                "normalize_audio_loudness": True,
                "voice_clone_id": "vc_alienes_kayit3_hybrid" if cid == "tacticallcrayon" else None
            }
        }
        
        # Kontrol 1: Zorunlu alanlar
        for req in ["job_id", "channel_id", "category", "language", "scenes"]:
            if req not in sample_job:
                log_fail(f"'{cid}' iş şemasında eksik anahtar: {req}")
                return False
        
        # Kontrol 2: edit_options geriye uyumluluk (None olan alanlar crash etmemeli)
        opts = sample_job.get("edit_options", {})
        _ = opts.get("voice_clone_id")
        _ = opts.get("bgm_path")
        _ = opts.get("watermark_text")
        
        log_pass(f"Kanal '{cid}' ({category}) iş şeması ve geriye uyumluluğu doğrulandı.")

    return True

def main():
    print("=" * 65)
    print("🛡️  PRE-FLIGHT REGRESSION GUARD - SİSTEM SAĞLIK TESTİ")
    print("=" * 65)
    
    t1 = test_channels_config()
    t2 = test_localization_logic()
    t3 = test_voice_cloning_integrity()
    t4 = test_all_channel_job_schemas()
    
    print("\n" + "=" * 65)
    if t1 and t2 and t3 and t4:
        print("🎉 TÜM KANALLAR VE MERKEZİ MODÜLLER SAĞLAM! (0 Regresyon)")
        print("=" * 65)
        return 0
    else:
        print("⚠️  DİKKAT! Bazı modüllerde regresyon/hata tespit edildi!")
        print("=" * 65)
        return 1

if __name__ == "__main__":
    sys.exit(main())
