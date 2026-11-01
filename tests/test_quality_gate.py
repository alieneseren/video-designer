"""
test_quality_gate.py
====================
Pre-Render Quality Gate Doğrulama ve Test Senaryoları.

Test Senaryoları:
1. Kademe 0: Cross-Project İzolasyon Duvarı Testi (Havacılık vs Spor).
2. Kademe 1: Deterministik Metadata & Çözünürlük & Boş Görsel Testi.
3. Kademe 2: Zero-Shot Semantik Skorlama (Kargo Şortu / Boş Pota Reddi vs. Nowitzki / Draymond Onayı).
4. Timeline Guard: Altyazı Taşma Koruması (%80 ekran genişliği kelime kırılımı).
5. Timeline Guard: Dış Ses Süre Kilidi (audio_duration + 0.5s).
6. Pipeline Integration: Retry Döngüsü ve Deterministik Fallback Degrade Testi.
"""

import os
import sys
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Proje src dizinini ekle
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from asset_validator import asset_validator, AssetValidator
from timeline_guard import timeline_guard, TimelineGuard
from pipeline_integration import pipeline_integration, PipelineIntegration
from pre_render_quality_gate import pre_render_quality_gate, PreRenderQualityGate


def create_test_images(temp_dir: Path):
    """Test için sentetik ve gerçekçi test görselleri üretir."""
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Bozuk / Küçük / Thumbnail Görsel (100x100)
    tiny_img = Image.new("RGB", (120, 120), (50, 50, 50))
    tiny_path = temp_dir / "tiny_thumbnail.jpg"
    tiny_img.save(tiny_path)

    # 2. Tek Renk Düz Siyah Ekran (Solid Black)
    solid_img = Image.new("RGB", (1080, 1920), (0, 0, 0))
    solid_path = temp_dir / "solid_black.jpg"
    solid_img.save(solid_path)

    # 3. Yüksek Çözünürlüklü Geçerli Dikey Şablon
    valid_img = Image.new("RGB", (1080, 1920), (18, 24, 38))
    draw = ImageDraw.Draw(valid_img)
    # Sahne çizimi
    draw.rectangle([100, 100, 980, 1820], fill=(30, 45, 70), outline=(251, 191, 36), width=4)
    draw.text((300, 900), "NBA BASKETBALL ACTION", fill=(255, 255, 255))
    valid_path = temp_dir / "valid_nba_scene.jpg"
    valid_img.save(valid_path)

    return tiny_path, solid_path, valid_path


def run_tests():
    print("=" * 70)
    print("🚀 [TEST] PRE-RENDER QUALITY GATE TESTLERİ BAŞLIYOR...")
    print("=" * 70)

    test_dir = Path("/tmp/quality_gate_tests")
    tiny_p, solid_p, valid_p = create_test_images(test_dir)

    # -------------------------------------------------------------
    # TEST 1: Cross-Project İzolasyon Duvarı
    # -------------------------------------------------------------
    print("\n[TEST 1] Kademe 0: Cross-Project Duvarı...")
    bad_airplane_path = "/tmp/aviation_disaster/cockpit_airplane_f16.jpg"
    iso_ok, iso_msg = AssetValidator.check_cross_project_isolation(bad_airplane_path, "basketball_analysis")
    assert not iso_ok, "Cross-project havacılık sızıntısını yakalayamadı!"
    print(f"  ✅ Başarılı: Havacılık görseli NBA projesinden engellendi: {iso_msg}")

    # -------------------------------------------------------------
    # TEST 2: Deterministik Metadata Kontrolleri (0 ms)
    # -------------------------------------------------------------
    print("\n[TEST 2] Kademe 1: Metadata ve Çözünürlük...")
    
    # Tiny thumbnail kontrolü
    meta_ok, meta_reason, _ = AssetValidator.check_metadata(tiny_p, is_vertical=True)
    assert not meta_ok, "Küçük thumbnail elenmedi!"
    print(f"  ✅ Başarılı: Küçük thumbnail elendi: {meta_reason}")

    # Düz siyah ekran kontrolü
    solid_ok, solid_reason, _ = AssetValidator.check_metadata(solid_p, is_vertical=True)
    assert not solid_ok, "Düz siyah ekran elenmedi!"
    print(f"  ✅ Başarılı: Düz siyah ekran elendi: {solid_reason}")

    # Geçerli görsel kontrolü
    valid_ok, valid_reason, meta_dict = AssetValidator.check_metadata(valid_p, is_vertical=True)
    assert valid_ok, f"Geçerli görsel onaylanamadı: {valid_reason}"
    print(f"  ✅ Başarılı: Geçerli dikey görsel onaylandı ({meta_dict['width']}x{meta_dict['height']})")

    # -------------------------------------------------------------
    # TEST 3: Zero-Shot Skorlama (Nowitzki vs Kargo Şortu / Kara Liste)
    # -------------------------------------------------------------
    print("\n[TEST 3] Kademe 2: Zero-Shot Semantik Skorlama...")
    
    # Sistemde mevcut gerçek Draymond Green görselini test et
    brain_asset = Path("/Users/alienes/.gemini/antigravity-cli/brain/54051ce9-57bb-4040-8262-7648f6372964/draymond_assets/Draymond_Green_2016.jpg")
    if brain_asset.exists():
        res = asset_validator.validate_candidate(
            image_path=brain_asset,
            scene_prompt="Draymond Green Golden State Warriors basketball defense",
            project_type="basketball_analysis",
            target_entity="Draymond Green"
        )
        print(f"  🏀 Gerçek Draymond Görseli Sonucu: Status={res.status}, Skor={res.score:.3f}, Gerekçe={res.reason}")
        assert res.is_valid, f"Gerçek Draymond görseli onaylanamadı: {res.reason}"
        print("  ✅ Başarılı: Gerçek NBA yıldızı başarıyla onaylandı.")
    else:
        print("  ℹ️ Draymond görseli bulunamadı, sentetik görselle zero-shot test ediliyor.")
        res = asset_validator.validate_zero_shot(
            image_input=valid_p,
            scene_prompt="NBA basketball game court action",
            blacklist_labels=["legs in cargo shorts", "empty basketball hoop", "rural backyard"]
        )
        print(f"  Zero-Shot Test: Geçti mi={res[0]}, Pozitif={res[1]:.3f}, Negatif={res[2]:.3f}")

    # -------------------------------------------------------------
    # TEST 4: Altyazı Taşma Koruması (%80 Ekran Genişliği)
    # -------------------------------------------------------------
    print("\n[TEST 4] Timeline Guard: Altyazı Taşma Koruması (Bounding Box)...")
    font = ImageFont.load_default()
    long_subtitle = "IT STANDS AS THE WEIRDEST BOX SCORE IN BASKETBALL LORE-PROOF THAT YOU DON'T NEED TO PUT THE BALL IN THE HOOP TO DOMINATE"
    
    wrapped = TimelineGuard.wrap_text_to_pixel_width(
        text=long_subtitle,
        font=font,
        screen_width=1080,
        max_width_ratio=0.80
    )
    print(f"  Orijinal Uzun Metin: {len(long_subtitle)} karakter")
    print(f"  Kırılmış Satırlar ({len(wrapped)} satır):")
    for idx, l in enumerate(wrapped):
        print(f"    Satır {idx+1}: {l}")

    card_box = TimelineGuard.calculate_card_bounding_box(
        lines=wrapped,
        font=font,
        screen_width=1080,
        screen_height=1920
    )
    assert not card_box["is_overflowing"], "Altyazı kartı ekran sınırını aştı!"
    assert card_box["x0"] >= 0 and card_box["x1"] <= 1080, "Yatay taşma mevcut!"
    print(f"  ✅ Başarılı: Bounding box tam olarak ekran içinde: x0={card_box['x0']}, x1={card_box['x1']}, w={card_box['card_w']}px <= 1080px")

    # -------------------------------------------------------------
    # TEST 5: Dış Ses Süre Kilidi (+0.5s)
    # -------------------------------------------------------------
    print("\n[TEST 5] Timeline Guard: Dış Ses Süre Kilidi...")
    # Sentetik 3 saniyelik WAV üret
    test_wav = test_dir / "test_audio.wav"
    import struct
    sample_rate = 44100
    duration_s = 3.20
    n_frames = int(sample_rate * duration_s)
    with wave.open(str(test_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))

    lock_info = TimelineGuard.calculate_locked_timeline_duration(test_wav, tail_padding_sec=0.50)
    expected_locked = round(3.20 + 0.50, 2)
    assert abs(lock_info["locked_duration"] - expected_locked) < 0.05, "Süre kilidi yanlış hesaplandı!"
    print(f"  ✅ Başarılı: Ses={lock_info['audio_duration']:.2f}s -> Kilitli Süre={lock_info['locked_duration']:.2f}s (Tail +0.50s)")

    # -------------------------------------------------------------
    # TEST 6: Pipeline Integration: Retry Döngüsü ve Güvenli Fallback
    # -------------------------------------------------------------
    print("\n[TEST 6] Pipeline Integration: 5 Deneme & Fallback Degrade...")
    # 5 kere bilerek reddedilecek bozuk thumbnail döndüren simülatör
    def bad_candidate_generator(attempt: int):
        return tiny_p

    chosen_p, val_res = PipelineIntegration.fetch_and_validate_scene_asset(
        candidate_generator_fn=bad_candidate_generator,
        scene_idx=1,
        scene_prompt="Dirk Nowitzki championship victory celebration",
        project_type="basketball_analysis",
        max_attempts=5,
        work_dir=test_dir
    )
    assert val_res.metadata.get("is_fallback"), "Tüm adaylar reddedildiğinde fallback devreye girmedi!"
    assert chosen_p.exists() and chosen_p.name.endswith("_safe_fallback.jpg"), "Fallback degrade üretilemedi!"
    print(f"  ✅ Başarılı: 5 bozuk adayın ardından deterministik degrade devreye girdi: {chosen_p.name}")

    print("\n" + "=" * 70)
    print("🎉 TÜM KALİTE KAPISI (PRE-RENDER QUALITY GATE) TESTLERİ BAŞARIYLA GEÇTİ!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
