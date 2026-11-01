"""
tests/test_pipeline_fixes.py
============================
Pre-Render Quality Gate: 3 Kritik Düzeltme Birim Testleri.

Test Senaryoları:
1. Test 1: Bağlam-Kilitli Sorgu ve Dinamik Dönem/Takım Negatifleri (Context-Locked Querying & Era Filter)
   - Allen Iverson 1997 rookie sezonu için:
     - Şablon: {entity} {target_year} {team_name} {action_keyword}
     - Dinamik Negatifler: Detroit Pistons, Denver Nuggets, press conference, streetwear, glasses
   - Draymond Green 2017 triple-double için:
     - Şablon: Draymond Green 2017 Golden State Warriors triple-double
     - Dinamik Negatifler: Michigan State, college basketball, suit, podcast
2. Test 2: Mükerrer Görsel Reddi & No-Loop Kaydı (Deduplication / No-Loop Registry)
   - Onaylanan bir görsel used_assets kümesine kaydedildiğinde, ikinci denemede %100 deterministik olarak reddedilir.
3. Test 3: Dış Ses ve Süre Kilidi (+0.60s Tampon Payı)
   - Net ses süresi milisaniyesine kadar okunur.
   - final_video_duration = audio_duration + 0.60s eşitliği doğrulanır.
4. Test 4: 2 Satırlı Altyazı Taşma Koruması (Line Wrap & Bounding Box)
   - Ekran genişliğinin %80'ini aşmayan, kart başına maksimum 2 satırlı kusursuz bölme denetlenir.
"""

import sys
import wave
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Proje src dizinini ekle
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from query_builder import query_builder, QueryBuilder
from asset_validator import asset_validator, AssetValidator
from timeline_guard import timeline_guard, TimelineGuard
from pipeline_integration import pipeline_integration, PipelineIntegration


def create_synthetic_wav(file_path: Path, duration_sec: float = 3.5, sample_rate: int = 44100):
    """Milisaniyesi tam bilinen sentetik bir WAV ses dosyası üretir."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Sessiz/hafif sinüs dalgası
        data = bytearray(num_samples * 2)
        wf.writeframes(data)
    return file_path


def create_valid_test_image(file_path: Path, width: int = 1080, height: int = 1920):
    """Kademe 1 ve Kademe 2'yi başarıyla geçen otantik basketbol sahası test görseli üretir."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), (30, 45, 75))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(25 + 30 * (y / height))
        g = int(35 + 40 * (y / height))
        b = int(55 + 60 * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    # Saha çizgileri
    draw.ellipse([(100, 400), (width - 100, height - 400)], outline=(220, 220, 220), width=8)
    draw.line([(0, height // 2), (width, height // 2)], fill=(220, 220, 220), width=8)
    img.save(file_path, "JPEG", quality=95)
    return file_path


def run_pipeline_fixes_tests():
    print("=" * 75)
    print("🚀 [TEST SUITE] PRE-RENDER QUALITY GATE - 3 KRİTİK DÜZELTME TESTLERİ")
    print("=" * 75)

    test_dir = Path("/tmp/pipeline_fixes_tests")
    test_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────────────────────
    # TEST 1: Bağlam-Kilitli Sorgu & Dinamik Dönem Negatifleri
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 1] Bağlam-Kilitli Sorgu ve Dinamik Dönem/Takım Negatifleri...")
    
    # 1A: Allen Iverson 1997 Senaryosu
    iverson_narration = (
        "In 1997, rookie sensation Allen Iverson shook the basketball world with his "
        "legendary crossover against Michael Jordan playing for the Philadelphia 76ers."
    )
    cq_iverson = query_builder.build_context_locked_queries(iverson_narration)
    print(f"  🏀 Iverson Birincil Sorgu: {cq_iverson.primary_query}")
    print(f"     Oyuncu: {cq_iverson.entity} | Yıl: {cq_iverson.target_year} | Takım: {cq_iverson.team_name} | Aksiyon: {cq_iverson.action_keyword}")

    assert cq_iverson.entity == "Allen Iverson", f"Oyuncu tespit edilemedi: {cq_iverson.entity}"
    assert cq_iverson.target_year == 1997, f"Yıl tespit edilemedi: {cq_iverson.target_year}"
    assert cq_iverson.team_name == "Philadelphia 76ers", f"Takım tespit edilemedi: {cq_iverson.team_name}"
    assert cq_iverson.action_keyword == "crossover", f"Aksiyon tespit edilemedi: {cq_iverson.action_keyword}"
    assert '"Allen Iverson"' in cq_iverson.primary_query
    assert "1997" in cq_iverson.primary_query
    assert '"Philadelphia 76ers"' in cq_iverson.primary_query

    # Negatifleri denetle: 1997 için Detroit Pistons, Denver Nuggets, streetwear, glasses olmalı
    neg_lower = [n.lower() for n in cq_iverson.dynamic_negatives]
    print(f"     Dinamik Negatifler ({len(neg_lower)} etiket): {neg_lower[:6]}...")
    assert any("detroit" in n for n in neg_lower), "Detroit Pistons dinamik negatiflerde bulunamadı!"
    assert any("denver" in n for n in neg_lower), "Denver Nuggets dinamik negatiflerde bulunamadı!"
    assert any("streetwear" in n for n in neg_lower), "Sivil kıyafet 'streetwear' negatiflerde bulunamadı!"
    assert any("press conference" in n for n in neg_lower), "Basın toplantısı negatiflerde bulunamadı!"
    print("  ✅ [BAŞARILI] 1997 Allen Iverson bağlam sorgusu ve dinamik dönem negatifleri doğrulandı.")

    # 1B: Draymond Green 2017 Senaryosu
    draymond_narration = (
        "In 2017, Draymond Green recorded the most bizarre triple-double in NBA history "
        "for the Golden State Warriors without scoring 10 points."
    )
    cq_draymond = query_builder.build_context_locked_queries(draymond_narration)
    print(f"  🏀 Draymond Birincil Sorgu: {cq_draymond.primary_query}")
    assert cq_draymond.entity == "Draymond Green"
    assert cq_draymond.target_year == 2017
    assert cq_draymond.team_name == "Golden State Warriors"
    assert cq_draymond.action_keyword == "triple-double"
    
    dray_negs = [n.lower() for n in cq_draymond.dynamic_negatives]
    assert any("michigan state" in n or "college basketball" in n for n in dray_negs), "Kolej negatif etiketi eklenemedi!"
    print("  ✅ [BAŞARILI] 2017 Draymond Green bağlam sorgusu ve negatifleri doğrulandı.")

    # ─────────────────────────────────────────────────────────────
    # TEST 2: Mükerrer Görsel Reddi & No-Loop Kaydı (Deduplication)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 2] Mükerrer Görsel Reddi & No-Loop Kaydı...")
    real_asset = Path("/Users/alienes/.gemini/antigravity-cli/brain/54051ce9-57bb-4040-8262-7648f6372964/draymond_assets/Draymond_Green_2016.jpg")
    if real_asset.exists():
        test_img = real_asset
        test_prompt = "Draymond Green Golden State Warriors basketball game action defense"
    else:
        test_img = test_dir / "nba_candidate_action_01.jpg"
        create_valid_test_image(test_img)
        test_prompt = "authentic basketball court arena floor with lines"

    asset_validator.reset_used_assets()
    assert not asset_validator.is_asset_used(test_img), "Sıfırlama sonrası used_assets boş olmalıydı!"

    # 1. Deneme: Görsel henüz kullanılmadı -> Kabul edilmeli
    val_1 = asset_validator.validate_candidate(
        image_path=test_img,
        scene_prompt=test_prompt,
        project_type="basketball_analysis"
    )
    assert val_1.is_valid, f"İlk kullanımda geçerli görsel onaylanamadı: {val_1.reason}"
    print(f"  1. Kullanım: Kabul edildi ({val_1.status}) - {test_img.name}")

    # Görseli used_assets'e kaydet (Zaman çizgisine eklendi)
    asset_validator.register_used_asset(test_img)
    assert asset_validator.is_asset_used(test_img), "Varlık used_assets'e kaydedilemedi!"

    # 2. Deneme: Aynı görsel ikinci kez timeline'a sokulmak istendiğinde -> REDDEDİLMELİ
    val_2 = asset_validator.validate_candidate(
        image_path=test_img,
        scene_prompt=test_prompt,
        project_type="basketball_analysis"
    )
    print(f"  2. Kullanım: {val_2.status} (Gerekçe: {val_2.reason})")
    assert not val_2.is_valid, "Mükerrer görsel No-Loop filtresi tarafından yakalanamadı!"
    assert val_2.tier_failed == -1 or "Mükerrer" in val_2.reason, f"Hata gerekçesi mükerrer varlığı belirtmiyor: {val_2.reason}"
    print("  ✅ [BAŞARILI] No-Loop kuralı mükerrer görsel kullanımını kesin olarak engelledi.")

    # ─────────────────────────────────────────────────────────────
    # TEST 3: Dış Ses ve Süre Kilidi (+0.60s Tampon Payı)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 3] Dış Ses ve Süre Kilidi (+0.60s Tampon Payı)...")
    exact_duration = 4.250  # 4.25 saniye
    test_audio = test_dir / "voiceover_exact_4250ms.wav"
    create_synthetic_wav(test_audio, duration_sec=exact_duration)

    read_duration = TimelineGuard.get_exact_audio_duration(test_audio)
    print(f"  Okunan Net Dış Ses Süresi: {read_duration:.4f}s (Beklenen: {exact_duration:.4f}s)")
    assert abs(read_duration - exact_duration) < 0.01, f"Ses süresi milisaniyesine kadar doğru okunamadı: {read_duration}"

    # +0.60s tampon payı kilidi
    locked_info = TimelineGuard.calculate_locked_timeline_duration(test_audio, tail_padding_sec=0.60)
    expected_locked = round(exact_duration + 0.60, 3)
    print(f"  Hesaplanan Kilitli Video Süresi: {locked_info['locked_duration']:.3f}s (Beklenen: {expected_locked:.3f}s)")
    assert locked_info["locked_duration"] == expected_locked, "Süre kilidi formülü (+0.60s) uyuşmuyor!"

    render_params = TimelineGuard.prepare_render_duration_params(test_audio, tail_padding_sec=0.60, fadeout_duration=0.40)
    assert render_params["final_video_duration"] == expected_locked
    assert "apad=whole_dur=" in render_params["ffmpeg_audio_pad_filter"]
    print(f"  FFmpeg Ses Pad & Fadeout Filtresi: {render_params['ffmpeg_audio_pad_filter']}")
    print("  ✅ [BAŞARILI] Dış ses süresi +0.60s tampon ile kesin olarak kilitlendi.")

    # ─────────────────────────────────────────────────────────────
    # TEST 4: 2 Satırlı Altyazı Taşma Koruması
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 4] 2 Satırlı Altyazı Taşma Koruması (Line Wrap & Bounding Box)...")
    font = ImageFont.load_default()
    long_narration = (
        "IT STANDS AS THE WEIRDEST BOX SCORE IN BASKETBALL LORE-PROOF THAT "
        "YOU DON'T NEED TO PUT THE BALL IN THE HOOP TO COMPLETELY DOMINATE"
    )

    cards = TimelineGuard.split_text_to_2line_cards(
        text=long_narration,
        font=font,
        screen_width=1080,
        max_width_ratio=0.80
    )
    print(f"  Toplam Üretilen Kart Bloğu: {len(cards)}")
    for idx, card_lines in enumerate(cards):
        print(f"    Kart #{idx+1} ({len(card_lines)} satır): {card_lines}")
        assert len(card_lines) <= 2, f"Kart #{idx+1} satır sınırı (2) aşıldı: {len(card_lines)}"

        card_bbox = TimelineGuard.calculate_card_bounding_box(
            lines=card_lines,
            font=font,
            screen_width=1080,
            screen_height=1920
        )
        assert not card_bbox["is_overflowing"], f"Kart #{idx+1} ekrandan taştı!"
        assert card_bbox["x0"] >= 20 and card_bbox["x1"] <= 1060, f"Kart #{idx+1} yatay güvenlik marjını ihlal etti!"

    print("  ✅ [BAŞARILI] 2 satırlı kusursuz altyazı bölme ve ekran taşma koruması doğrulandı.")

    print("\n" + "=" * 75)
    print("🎉 TÜM PRE-RENDER KALİTE KAPISI DÜZELTME TESTLERİ EKSİKSİZ GEÇTİ!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    success = run_pipeline_fixes_tests()
    sys.exit(0 if success else 1)
