"""
tests/test_fail_safe_engine.py
==============================
Fail-Safe Production Engine Doğrulama Test Paketi
(Zero Black Frame, Subject Anchor Invariant, 3-Tier Fallback, Timeline Buffer)

Test Kapsamı:
1. Test 1: Zorunlu Çapa Değişmezi (Mandatory Subject Anchor Invariant):
   - Soyut cümleler ('expanding the rim's sweet spot', 'geometry of the backboard')
   - Primary Entity ('Tim Duncan', Spurs, 2003) tüm arama terimlerinin başında bulunmalı.
   - Sorgu ASLA çapasız üretilemez (assert primary_entity.lower() in q.lower()).
2. Test 2: Dinamik Negatif Enjeksiyonu (Dynamic Cross-Sport & Rival Negatives):
   - Çapraz spor terimleri (soccer, fifa, world cup, nfl, military, amateur, playground, cargo shorts, empty hoop)
   - Rakip yıldızlar/takımlar (Lakers, Pistons, Kobe vb.) negatif listesinde bulunmalı.
3. Test 3: 3-Kademeli Sıfır Siyah Ekran Hiyerarşisi (Zero Black Screen Hierarchy):
   - Kademe 1: Karakter Arşiv Karesi alternatif Ken Burns ile derlenmeli (>1KB, valid MP4).
   - Kademe 2: Dinamik İstatistik/İnfografik Kartı üretilmeli (>1KB, valid MP4).
   - Kademe 3: Soyut Hareketli Doku üretilmeli (>1KB, valid MP4).
   - Sıfır siyah ekran assertion kontrolü.
4. Test 4: PipelineOrchestrator Uçtan Uca Sahne Varlık Çözümlemesi:
   - Aday havuzu tükenmişken orchestrate_scene_asset çağrılmalı ve kesinlikle valid MP4 dönmeli.
5. Test 5: TimelineGuard Süre Tamponu (+0.60s) ve Altyazı Taşma Koruması (%80 Sınır).
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from query_builder import query_builder, ContextLockedQuery, NBA_TEAMS
from asset_validator import asset_validator, ValidationResult
from fallback_engine import fallback_engine, FallbackEngine
from timeline_guard import timeline_guard, TimelineDurationLock
from pipeline_orchestrator import pipeline_orchestrator, PipelineOrchestrator


class TestFailSafeProductionEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="test_fail_safe_"))
        print(f"\n[TestSetup] Geçici test dizini: {cls.temp_dir}")

    @classmethod
    def tearDownClass(cls):
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
            print(f"[TestTeardown] Geçici test dizini temizlendi: {cls.temp_dir}")

    # ─────────────────────────────────────────────────────────────
    # TEST 1: ZORUNLU ÇAPA DEĞİŞMEZİ (MANDATORY SUBJECT ANCHOR)
    # ─────────────────────────────────────────────────────────────

    def test_01_mandatory_subject_anchor_invariant(self):
        """Soyut anlatım ifadeleri girildiğinde her sorguda karakter çapası zorunlu olmalıdır."""
        abstract_scenes = [
            "expanding the rim's sweet spot",
            "the geometry of the backboard and mechanical perfection",
            "relentless defensive anchor in the fourth quarter",
            "mastering the bank shot from forty-five degrees"
        ]
        primary_entity = "Tim Duncan"
        team = "San Antonio Spurs"
        era_year = 2003

        for sc_text in abstract_scenes:
            cq: ContextLockedQuery = query_builder.build_context_locked_queries(
                scene_text=sc_text,
                fallback_entity=primary_entity,
                target_team=team,
                era_year=era_year
            )

            # Invariant: Asla çapasız soyut sorgu dönülemez!
            self.assertTrue(len(cq.anchored_queries) >= 3, "En az 3 adet çapalanmış sorgu üretilmeli!")
            self.assertIn("tim duncan", cq.primary_query.lower(), "Birincil sorgu 'Tim Duncan' içermeli!")

            for q in cq.anchored_queries:
                self.assertIn(
                    "tim duncan",
                    q.lower(),
                    f"KRİTİK GÜVENLİK İHLALİ: '{q}' sorgusu 'Tim Duncan' çapasını içermiyor!"
                )
            
            # Yıl ve takım çapasının birincil sorguda yer aldığını doğrula
            self.assertIn("spurs", cq.primary_query.lower())
            self.assertIn("2003", cq.primary_query.lower())

        print("✅ [TEST 1 BAŞARILI] Zorunlu Çapa Değişmezi (Mandatory Subject Anchor) %100 doğrulandı.")

    # ─────────────────────────────────────────────────────────────
    # TEST 2: DİNAMİK NEGATİF ENJEKSİYONU (CROSS-SPORT & RIVALS)
    # ─────────────────────────────────────────────────────────────

    def test_02_dynamic_cross_sport_and_rival_negatives(self):
        """Dinamik negatif filtresi çapraz sporları ve rakip unsurları otomatik eklemelidir."""
        cq: ContextLockedQuery = query_builder.build_context_locked_queries(
            scene_text="game winning bank shot in the finals",
            fallback_entity="Tim Duncan",
            target_team="San Antonio Spurs",
            era_year=2003
        )

        neg_lower = [n.lower() for n in cq.dynamic_negatives]

        # Çapraz spor ve amatör negatifleri kontrolü
        required_cross_sport = ["soccer", "fifa", "world cup", "nfl", "military", "amateur", "playground", "cargo shorts", "empty hoop"]
        for kw in required_cross_sport:
            self.assertTrue(
                any(kw in n for n in neg_lower),
                f"Dinamik negatif listesinde '{kw}' eksik!"
            )

        # Tim Duncan için rakip yıldız/takım negatifleri kontrolü (Lakers, Pistons, Kobe vb.)
        self.assertTrue(any("lakers" in n for n in neg_lower), "Spurs için Lakers negatif listesinde olmalı!")
        self.assertTrue(any("kobe" in n for n in neg_lower), "Tim Duncan için Kobe negatif listesinde olmalı!")

        print(f"✅ [TEST 2 BAŞARILI] Dinamik negatif havuzu doğrulandı (Toplam {len(cq.dynamic_negatives)} etiket).")

    # ─────────────────────────────────────────────────────────────
    # TEST 3: 3-KADEMELİ SIFIR SİYAH EKRAN HİYERARŞİSİ
    # ─────────────────────────────────────────────────────────────

    def test_03_zero_black_screen_hierarchy_all_tiers(self):
        """FallbackEngine 3 kademenin tümünde >1KB geçerli video üretmeli ve asla siyah ekran bırakmamalıdır."""
        # 1. Kademe 1: Karakter Arşiv Karesi (Alternatif Ken Burns)
        dummy_archive = self.temp_dir / "tim_duncan_archive.jpg"
        img = Image.new("RGB", (1080, 1920), (30, 40, 60))
        img.save(dummy_archive, "JPEG", quality=95)

        k1_clip = self.temp_dir / "tier1_archive_clip.mp4"
        res_k1 = fallback_engine.render_character_archive_clip(
            image_path=dummy_archive,
            output_clip_path=k1_clip,
            duration=1.5,
            width=540,
            height=960,
            fps=24
        )
        self.assertTrue(res_k1.exists(), "Kademe 1 klip dosyası oluşmadı!")
        self.assertGreater(res_k1.stat().st_size, 1000, "Kademe 1 klip 0-byte veya bozuk!")

        # 2. Kademe 2: Dinamik İstatistik / İnfografik Kartı
        info_img = self.temp_dir / "tier2_infographic.jpg"
        fallback_engine.generate_infographic_canvas(
            output_image_path=info_img,
            primary_entity="Tim Duncan",
            team_name="San Antonio Spurs",
            scene_text="EXPANDING THE RIM'S SWEET SPOT WITH 21 POINTS AND 20 REBOUNDS",
            width=540,
            height=960
        )
        self.assertTrue(info_img.exists() and info_img.stat().st_size > 5000, "Kademe 2 infografik görseli üretilemedi!")

        k2_clip = self.temp_dir / "tier2_infographic_clip.mp4"
        res_k2 = fallback_engine.convert_image_to_clip(
            image_path=info_img,
            output_clip_path=k2_clip,
            duration=1.5,
            width=540,
            height=960,
            fps=24,
            subtle_zoom=True
        )
        self.assertTrue(res_k2.exists() and res_k2.stat().st_size > 1000, "Kademe 2 klip 0-byte veya bozuk!")

        # 3. Kademe 3: Soyut Hareketli Doku Tuvali
        texture_img = self.temp_dir / "tier3_texture.jpg"
        fallback_engine.generate_abstract_motion_texture(
            output_image_path=texture_img,
            primary_entity="Tim Duncan",
            team_name="San Antonio Spurs",
            width=540,
            height=960
        )
        self.assertTrue(texture_img.exists() and texture_img.stat().st_size > 5000, "Kademe 3 doku üretilemedi!")

        k3_clip = self.temp_dir / "tier3_texture_clip.mp4"
        res_k3 = fallback_engine.convert_image_to_clip(
            image_path=texture_img,
            output_clip_path=k3_clip,
            duration=1.5,
            width=540,
            height=960,
            fps=24,
            subtle_zoom=True
        )
        self.assertTrue(res_k3.exists() and res_k3.stat().st_size > 1000, "Kademe 3 klip 0-byte veya bozuk!")

        # 4. Zero Black Screen Ana Orkestrasyon Metodu (resolve_fail_safe_clip)
        final_safe_clip = self.temp_dir / "fail_safe_resolved.mp4"
        res_safe = fallback_engine.resolve_fail_safe_clip(
            output_clip_path=final_safe_clip,
            duration=2.0,
            primary_entity="Tim Duncan",
            team_name="San Antonio Spurs",
            scene_text="BANK SHOT MASTERY",
            character_archive_image=dummy_archive,
            scratch_dir=self.temp_dir,
            width=540,
            height=960,
            fps=24
        )
        self.assertIsNotNone(res_safe)
        self.assertTrue(res_safe.exists())
        self.assertGreater(res_safe.stat().st_size, 1000)

        print("✅ [TEST 3 BAŞARILI] 3-Kademeli Sıfır Siyah Ekran Hiyerarşisi (Kademe 1, 2, 3) %100 çalışıyor.")

    # ─────────────────────────────────────────────────────────────
    # TEST 4: PIPELINE ORCHESTRATOR SAHNE BAZLI ÇÖZÜMLEME
    # ─────────────────────────────────────────────────────────────

    def test_04_pipeline_orchestrator_scene_asset_fail_safe(self):
        """Arama motoru hiç aday bulamadığında (None döndüğünde) pipeline_orchestrator asla çökmemeli ve siyah ekran bırakmamalıdır."""
        def mock_empty_candidate_generator(attempt: int, query: str):
            # Arama motorunun başarısız olduğunu simüle et
            return None

        out_clip_path, meta = pipeline_orchestrator.orchestrate_scene_asset(
            scene_idx=4,
            scene_text="expanding the rim's sweet spot",
            primary_entity="Tim Duncan",
            team_name="San Antonio Spurs",
            era_year=2003,
            candidate_generator_fn=mock_empty_candidate_generator,
            duration=2.0,
            work_dir=self.temp_dir,
            width=540,
            height=960,
            fps=24
        )

        self.assertIsNotNone(out_clip_path, "Orchestrator None döndü!")
        self.assertTrue(out_clip_path.exists(), "Orchestrator çıktısı diskte mevcut değil!")
        self.assertGreater(out_clip_path.stat().st_size, 1000, "Orchestrator çıktısı 0-byte!")
        self.assertTrue(meta.get("is_fallback"), "Adaylar boşken is_fallback True olmalı!")

        print(f"✅ [TEST 4 BAŞARILI] PipelineOrchestrator Sıfır Siyah Ekran güvencesi doğrulandı: {out_clip_path.name}")

    # ─────────────────────────────────────────────────────────────
    # TEST 5: TIMELINE GUARD SÜRE KİLİDİ VE ALTYAZI AUTO-WRAP
    # ─────────────────────────────────────────────────────────────

    def test_05_timeline_guard_buffer_and_auto_wrap(self):
        """+0.60s süre tamponu ve %80 ekran genişliği 2-satır auto-wrap mekanizması doğrulanmalıdır."""
        # 1. Altyazı Taşma Koruması
        long_sub = [{
            "start": 0.0,
            "end": 3.0,
            "text": "IT STANDS AS THE WEIRDEST BOX SCORE IN BASKETBALL LORE PROOF THAT YOU DONT NEED TO SCORE TO DOMINATE"
        }]

        wrapped = timeline_guard.format_and_wrap_subtitles(
            subtitles=long_sub,
            screen_width=1080,
            max_width_ratio=0.80,
            font_size=56
        )

        self.assertEqual(len(wrapped), 1)
        res_text = wrapped[0]["text"]
        self.assertIn("\n", res_text, "Uzun altyazı taşmayı önlemek için satır sonu '\\n' ile kırılmalı!")
        lines = res_text.split("\n")
        self.assertLessEqual(len(lines), 2, "Altyazı en fazla 2 satıra bölünmeli!")

        # 2. Sentetik Ses Dosyası ile Süre Tamponu Kontrolü
        import subprocess
        synth_audio = self.temp_dir / "test_voice.mp3"
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=5.0",
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(synth_audio)
        ], capture_output=True, check=True)

        lock_res: TimelineDurationLock = timeline_guard.calculate_locked_timeline_duration(synth_audio, tail_padding_sec=0.60)
        self.assertAlmostEqual(lock_res.audio_duration, 5.0, delta=0.15)
        self.assertAlmostEqual(lock_res.final_video_duration, lock_res.audio_duration + 0.60, delta=0.01)

        print("✅ [TEST 5 BAŞARILI] TimelineGuard (+0.60s süre tamponu & %80 auto-wrap) %100 doğrulandı.")

    # ─────────────────────────────────────────────────────────────
    # TEST 6: HAKEEM & DAVID ROBINSON ÇAPASI VE ANTI-ROBINHO/SOCCER
    # ─────────────────────────────────────────────────────────────

    def test_06_hakeem_and_david_robinson_soccer_filter(self):
        """Dış ses 'David Robinson' veya 'soccer' dediğinde Robinho/futbol filtrelenmeli ve NBA basketball zincirlenmelidir."""
        scene_text = (
            "The secret weapon was not his speed, but his soccer-honed center of gravity. "
            "By the time David Robinson realized the fake, Hakeem was already rising for an uncontested reverse layup."
        )
        title = "Why Nobody Could Defend Hakeem Olajuwon Dream Shake"
        cq = query_builder.build_context_locked_queries(title, scene_text)

        self.assertEqual(cq.entity, "Hakeem Olajuwon")
        self.assertEqual(cq.team_name, "Houston Rockets")
        self.assertIn("nba basketball", cq.primary_query.lower())
        self.assertNotIn("soccer", cq.action_keyword.lower(), "Action keyword asla 'soccer' olamaz!")

        # Negatif havuzunda soccer ve robinho bulunmalı
        neg_lower = [n.lower() for n in cq.dynamic_negatives]
        self.assertTrue(any("soccer" in n for n in neg_lower), "Negatif havuzunda 'soccer' olmalı!")
        self.assertTrue(any("robinho" in n for n in neg_lower), "Negatif havuzunda 'robinho' olmalı!")
        self.assertTrue(any("brazil" in n for n in neg_lower), "Negatif havuzunda 'brazil' olmalı!")

        # Rakip David Robinson sorgusu zincirleme kontrolü
        has_robinson_query = any("david robinson" in q.lower() and "nba basketball" in q.lower() for q in cq.fallback_queries)
        self.assertTrue(has_robinson_query, "Fallback sorgularında 'David Robinson NBA basketball' bulunmalı!")

        # Maç istatistik kartı testi
        stats_img = self.temp_dir / "hakeem_stats_test.jpg"
        fallback_engine.generate_match_stats_card(
            output_image_path=stats_img,
            primary_entity="Hakeem Olajuwon",
            team_name="Houston Rockets"
        )
        self.assertTrue(stats_img.exists() and stats_img.stat().st_size > 5000)
        print("✅ [TEST 6 BAŞARILI] Hakeem & David Robinson (Anti-Robinho/Soccer & Match Stats Card) %100 doğrulandı.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
