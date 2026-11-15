"""
tests/test_deterministic_gates.py
==================================
Comprehensive Unit Test Suite for the 6 Hard Mechanical Gates:
1. Gate 1: Decouple Search Recall From Visual Precision (No Pool Starvation, <= 4 words, no negative '-' words to search APIs)
2. Gate 2: Post-Slice Visual Verification Gate (SigLIP/CLIP cosine >= 0.26, 9-label negative domain classification)
3. Gate 3: Strict Source Quota (max_slices_per_source_id = 1) & 3-Point pHash at 0.2s, 1.0s, 1.8s (Hamming < 10 rejection)
4. Gate 4: Technical Quality Hard Caps (width < 720 rejection, Laplacian < 75.0 rejection, max_cut_duration <= 2.40s)
5. Gate 5: Concrete Visual Queries in Scenario Generator (LLM Schema & physical camera framing + subject + environment)
6. Gate 6: Immutable locked_segments in /api/video-patch (freezing locked == True scenes, validating replacements)
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from PIL import Image, ImageDraw
import cv2
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.core.query_builder import QueryBuilder
from src.core.asset_fetcher import AssetFetcher
from src.core.scenario_generator import (
    validate_concrete_visual_query,
    ScenarioGenerator,
    ScenarioScene,
    ABSTRACT_TERMS_BLACKLIST
)
from src.modules.basketball.vision_verifier import (
    BasketballVisionVerifier,
    NEGATIVE_DOMAIN_LABELS,
    POSITIVE_ANCHORS_BASKETBALL
)
from src.modules.basketball.validator import (
    BasketballAssetValidator,
    measure_laplacian_sharpness,
    get_3point_fingerprints,
    extract_3point_frames
)
from src.modules.basketball.orchestrator import BasketballOrchestrator
from src.routers.video_patch import apply_video_patches, ApplyPatchPayload, parse_qa_patch_instruction
from src.modules.basketball.video_harvester import VideoHarvester


class TestDeterministicGates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="test_gates_"))
        cls.vision_verifier = BasketballVisionVerifier()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # ─────────────────────────────────────────────────────────────
    # GATE 1: DECOUPLE SEARCH RECALL FROM VISUAL PRECISION
    # ─────────────────────────────────────────────────────────────
    def test_gate1_broad_search_query_no_pool_starvation(self):
        """Arama API'lerine 3-4 kelimelik temiz geniş sorgu gider, negatif '-' kelimeler zincirlenmez."""
        broad_q = QueryBuilder.build_broad_search_query(
            entity="James Harden",
            action_keyword="step back three pointer mechanics",
            max_words=4
        )
        words = broad_q.split()
        self.assertLessEqual(len(words), 4, f"Sorgu 4 kelimeyi aşmamalı: {broad_q}")
        self.assertNotIn("-", broad_q, f"Arama motoruna negatif kelime zincirlenmemeli: {broad_q}")
        self.assertEqual(broad_q, "James Harden step back")

        # Wikimedia temizleme kontrolü
        variants = AssetFetcher.clean_query_for_wikimedia("James Harden -ticket -stub -scoreboard")
        for v in variants:
            self.assertNotIn("-ticket", v, f"Negatif filtre Wikimedia arama API'sine gönderilmemeli: {v}")

    # ─────────────────────────────────────────────────────────────
    # GATE 2: POST-SLICE VISUAL VERIFICATION (SigLIP / CLIP)
    # ─────────────────────────────────────────────────────────────
    def test_gate2_exact_negative_domain_labels(self):
        """Negatif domain listesi şartnamedeki katı etiketlerle birebir eşleşmelidir."""
        expected_labels = [
            "amateur gym with brick wall",
            "empty basketball gym wall or floor without players",
            "close up sneakers on floor",
            "outdoor asphalt streetball court",
            "outdoor painted concrete basketball court",
            "outdoor streetball court",
            "close up sneakers on outdoor court",
            "football or soccer stadium",
            "athletics running track",
            "players standing on bench dead ball",
            "free throw lineup",
            "static portrait interview",
            "heavy motion blur whip pan",
            "unrelated infographic chart"
        ]
        self.assertEqual(NEGATIVE_DOMAIN_LABELS, expected_labels)

    def test_gate2_middle_frame_extraction_and_negative_rejection(self):
        """Orta kare (t = 1.0s) çıkarılır ve negatif domain skoru pozitif çapayı geçerse reddedilir."""
        # arena_10.mp4 (futbol stadyumu) kontrolü
        arena_vid = PROJECT_ROOT / "assets/curated_sports/b_roll/videos/arena_10.mp4"
        if arena_vid.exists():
            res = self.vision_verifier.verify_slice(
                media_path=arena_vid,
                concrete_visual_query="wide angle shot of packed NBA arena with hardwood basketball court"
            )
            self.assertFalse(res["passed"], "Futbol stadyumu (arena_10.mp4) negatif domain kilidi ile reddedilmeli!")
            reasons_str = " ".join(res["reasons"])
            self.assertTrue(
                "football or soccer stadium" in reasons_str or "Görsel Eşleşme Yetersiz" in reasons_str,
                f"Futbol stadyumu hatası bekleniyordu, gelen: {reasons_str}"
            )

    def test_gate2_cosine_similarity_floor_26(self):
        """Kosinüs benzerliği 0.26 altındaysa görsel yetersiz olarak elenmelidir."""
        # Sentetik alakasız görsel oluştur
        unrelated_img_path = self.temp_dir / "unrelated_nature.jpg"
        img = Image.new("RGB", (720, 1280), (34, 139, 34))  # Orman yeşili
        img.save(unrelated_img_path)

        res = self.vision_verifier.verify_slice(
            media_path=unrelated_img_path,
            concrete_visual_query="James Harden step back three pointer in NBA arena",
            min_cosine_similarity=0.26
        )
        self.assertFalse(res["passed"])
        self.assertLess(res["query_score"], 0.26)

    # ─────────────────────────────────────────────────────────────
    # GATE 3: STRICT SOURCE QUOTA & 3-POINT pHash LOCK
    # ─────────────────────────────────────────────────────────────
    def test_gate3_max_slices_per_source_id_equals_1(self):
        """max_slices_per_source_id = 1: Aynı kaynaktan 1'den fazla klip kullanılamaz."""
        validator = BasketballAssetValidator(max_same_source_clips=1)
        self.assertEqual(validator.max_same_source_clips, 1)

        # 2 sahnenin aynı source_video_id kullanmasını simüle et
        fixture_video = self.temp_dir / "fixture_source_video.mp4"
        if not fixture_video.exists():
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            vw = cv2.VideoWriter(str(fixture_video), fourcc, 30.0, (720, 1280))
            frame = np.full((1280, 720, 3), 120, dtype=np.uint8)
            for _ in range(60):
                vw.write(frame)
            vw.release()

        mock_cuts = [
            {
                "id": "cut_0",
                "media_path": str(fixture_video),
                "source_video_id": "youtube_shared_game_id_123",
                "duration": 2.10,
                "start_time": 0.0,
                "concrete_visual_query": "slam dunk on NBA hardwood court"
            },
            {
                "id": "cut_1",
                "media_path": str(fixture_video),
                "source_video_id": "youtube_shared_game_id_123",
                "duration": 2.10,
                "start_time": 2.10,
                "concrete_visual_query": "slam dunk on NBA hardwood court"
            }
        ]
        valid, errors = validator.validate_timeline(mock_cuts, self.temp_dir)
        self.assertFalse(valid, "Aynı source_video_id birden fazla kez kullanıldığında hata vermeli!")
        self.assertTrue(any("Same-Source" in e for e in errors), f"Hata listesi Same-Source içermeli: {errors}")

    def test_gate3_3point_phash_hamming_rejection(self):
        """0.2s, 1.0s, 1.8s 3-noktalı pHash çıkarılır; Hamming mesafesi < 10 olan ikizler reddedilir."""
        # 2 farklı isimli ama birebir aynı görsel
        img_a = self.temp_dir / "hash_a.jpg"
        img_b = self.temp_dir / "hash_b.jpg"
        im = Image.new("RGB", (720, 1280), (100, 150, 200))
        im.save(img_a)
        # Çok minik bir piksel farkı ile kopyala (Hamming distance < 10)
        im_copy = im.copy()
        im_copy.putpixel((10, 10), (101, 151, 201))
        im_copy.save(img_b)

        validator = BasketballAssetValidator(min_hamming_distance=10)
        mock_cuts = [
            {"id": "c0", "media_path": str(img_a), "source_video_id": "src_a", "duration": 2.0, "start_time": 0.0},
            {"id": "c1", "media_path": str(img_b), "source_video_id": "src_b", "duration": 2.0, "start_time": 2.0}
        ]
        valid, errors = validator.validate_timeline(mock_cuts, self.temp_dir)
        self.assertFalse(valid, "pHash Hamming < 10 olan ikiz görseller reddedilmeli!")
        self.assertTrue(any("pHash" in e for e in errors), f"Hata listesi pHash içermeli: {errors}")

    # ─────────────────────────────────────────────────────────────
    # GATE 4: TECHNICAL QUALITY, MOTION & DURATION HARD CAPS
    # ─────────────────────────────────────────────────────────────
    def test_gate4_reject_low_resolution_under_720p(self):
        """width < 720 veya height < 720 olan içerikler deterministik olarak reddedilir."""
        low_res_img = self.temp_dir / "low_res_360p.jpg"
        im = Image.new("RGB", (360, 640), (200, 200, 200))
        im.save(low_res_img)

        validator = BasketballAssetValidator(min_width=720, min_height=720)
        mock_cuts = [
            {"id": "c0", "media_path": str(low_res_img), "source_video_id": "src_low", "duration": 2.0, "start_time": 0.0}
        ]
        valid, errors = validator.validate_timeline(mock_cuts, self.temp_dir)
        self.assertFalse(valid)
        self.assertTrue(any("Düşük Çözünürlük" in e for e in errors))

    def test_gate4_reject_blurry_laplacian_under_75(self):
        """cv2.Laplacian(gray, cv2.CV_64F).var() < 75.0 olan bulanık içerikler elenir."""
        # Aşırı bulanık / tek düze görsel üret
        blurry_img = self.temp_dir / "blurry_uniform.jpg"
        arr = np.full((1280, 720, 3), 128, dtype=np.uint8)
        cv2.imwrite(str(blurry_img), arr)

        w, h, lap = measure_laplacian_sharpness(blurry_img)
        self.assertLess(lap, 75.0, f"Bulanık görsel varyansı < 75 olmalı: {lap}")

        validator = BasketballAssetValidator(min_laplacian_variance=75.0)
        mock_cuts = [
            {"id": "c0", "media_path": str(blurry_img), "source_video_id": "src_blur", "duration": 2.0, "start_time": 0.0}
        ]
        valid, errors = validator.validate_timeline(mock_cuts, self.temp_dir)
        self.assertFalse(valid)
        self.assertTrue(any("Bulanık" in e for e in errors))

    def test_gate4_enforce_max_scene_duration_240(self):
        """max_scene_duration = 2.4s kuralı: 2.4s üzerindeki sahneler deterministik olarak bölünür."""
        orch = BasketballOrchestrator()
        cuts = [
            {
                "id": "long_scene_0",
                "mediaPath": "media/clip_0.mp4",
                "media_path": "/tmp/clip_0.mp4",
                "mediaType": "video",
                "startFrame": 0,
                "durationInFrames": 150,  # 5.0 saniye @ 30fps (> 2.4s)
                "locked": True
            }
        ]
        backup_pool = [
            {"mediaPath": "media/broll.mp4", "media_path": "/tmp/broll.mp4", "type": "video", "source_video_id": "src_broll"}
        ]
        enforced = orch.enforce_hard_pacing_limits(cuts, backup_pool, max_cut_duration=2.40, fps=30)
        self.assertGreater(len(enforced), 1, "Uzun sahne bölünmeli!")
        for c in enforced:
            dur_sec = c["durationInFrames"] / 30.0
            self.assertLessEqual(dur_sec, 2.40, f"Hiçbir kesme 2.40s'yi aşamaz: {dur_sec}s")

    # ─────────────────────────────────────────────────────────────
    # GATE 5: CONCRETE VISUAL QUERIES (LLM SCHEMA)
    # ─────────────────────────────────────────────────────────────
    def test_gate5_concrete_visual_query_validator(self):
        """Soyut kavramlar (eccentric quad braking vb.) reddedilir; somut kadraj + eylem + ortam onaylanır."""
        # 1. Yasaklı soyut kavramlar
        bad_queries = [
            "eccentric quad braking mechanics during stepback",
            "the power of deceleration and kinetic force dissipation",
            "neurobiological superiority and brain synapse firing",
            "psychological mind games and defensive pressure"
        ]
        for bq in bad_queries:
            valid, reason = validate_concrete_visual_query(bq)
            self.assertFalse(valid, f"'{bq}' soyut kavramı reddedilmeli!")
            self.assertIn("Soyut Kavram", reason)

        # 2. Onaylı somut sorgular (kamera açısı + eylem + çevre)
        good_queries = [
            "close up basketball sneakers stopping on NBA hardwood floor slow motion",
            "James Harden explosive crossover step back dribble shaking defender in NBA arena",
            "wide angle shot of packed NBA arena with hardwood basketball court and arena lighting",
            "vintage red digital 7-segment LED shot clock displaying 0.3 seconds",
            "macro close up eye iris dilating and visual cortex optical nerve connection"
        ]
        for gq in good_queries:
            valid, reason = validate_concrete_visual_query(gq)
            self.assertTrue(valid, f"'{gq}' geçerli somut sorgusu onaylanmalı: {reason}")

    # ─────────────────────────────────────────────────────────────
    # GATE 6: IMMUTABLE locked_segments IN /api/video-patch
    # ─────────────────────────────────────────────────────────────
    def test_gate6_immutable_locked_segments(self):
        """locked == True olan sahneler dondurulur; /api/video-patch çağrısında yalnızca locked == False kesitler açılır."""
        test_job_dir = self.temp_dir / "test_patch_job"
        test_job_dir.mkdir(parents=True, exist_ok=True)
        test_video = test_job_dir / "final.mp4"
        test_video.write_bytes(b"dummy video data for router resolve")

        manifest_file = test_job_dir / "timeline_manifest.json"
        manifest_data = {
            "job_id": "test_patch_job",
            "athlete_key": "james_harden",
            "topic": "The Deceleration Secret Behind",
            "fps": 30,
            "cuts": [
                {
                    "cut_index": 0,
                    "id": "cut_0",
                    "media_path": str(self.temp_dir / "locked_scene.mp4"),
                    "media_type": "video",
                    "source_video_id": "src_locked_source_0",
                    "start_frame": 0,
                    "duration_frames": 60,
                    "locked": True
                },
                {
                    "cut_index": 1,
                    "id": "cut_1",
                    "media_path": str(self.temp_dir / "unlocked_scene.mp4"),
                    "media_type": "video",
                    "source_video_id": "src_unlocked_source_1",
                    "start_frame": 60,
                    "duration_frames": 60,
                    "locked": False
                }
            ]
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        mock_rep_path = self.temp_dir / "mock_replacement.mp4"
        mock_rep_path.write_bytes(b"mock replacement data")

        payload = ApplyPatchPayload(
            video_path=str(test_video),
            scenes=[
                {"cut_index": 0, "locked": True},
                {"cut_index": 1, "locked": False, "media_path": str(mock_rep_path)}
            ]
        )

        with patch.object(BasketballOrchestrator, "patch_video") as mock_patch:
            mock_patch.return_value = test_video
            response = apply_video_patches(payload)

            self.assertTrue(response["success"])
            self.assertEqual(response["video_path"], str(test_video))
            # Verify patch_video was called with unlock_indices=[1] (Cut 0 must NOT be unlocked!)
            mock_patch.assert_called_once()
            call_kwargs = mock_patch.call_args[1]
            self.assertEqual(call_kwargs.get("job_id"), "test_patch_job")
            self.assertEqual(call_kwargs.get("athlete_key"), "james_harden")
            self.assertEqual(call_kwargs.get("unlock_indices"), [1])
            self.assertIn(1, call_kwargs.get("patch_segments", {}))
            self.assertEqual(call_kwargs["patch_segments"][1]["path"], str(mock_rep_path))

    def test_gate6_replacement_rejects_source_quota_collision(self):
        """Kilitli olmayan sahne için aday seçilirken, kilitli sahnelerdeki source_video_id kesinlikle reddedilir."""
        orch = BasketballOrchestrator()
        locked_sources = {"src_locked_youtube_123"}
        
        # Aday kilitli kaynaktan geliyor
        candidate_pool = [
            {
                "type": "video",
                "path": str(PROJECT_ROOT / "assets/curated_sports/b_roll/videos/defense_14.mp4"),
                "source_video_id": "src_locked_youtube_123"  # Aynı kaynak!
            }
        ]
        
        rep = orch.select_replacement_asset(
            athlete_key="james_harden",
            target_query="James Harden step back three pointer in NBA arena",
            target_type="video",
            locked_source_ids=locked_sources,
            locked_hashes=[],
            candidate_pool=candidate_pool,
            work_dir=self.temp_dir
        )
        self.assertIsNone(rep, "Kilitli source_video_id ile çakışan aday seçilmemelidir!")

    def test_gate6_replacement_rejects_phash_collision(self):
        """Kilitli olmayan sahne için aday seçilirken, kilitli sahnelerle Hamming mesafesi < 10 olan ikizler elenir."""
        import imagehash
        orch = BasketballOrchestrator()
        
        # Test görseli oluştur
        locked_img = self.temp_dir / "locked_frame.jpg"
        im = Image.new("RGB", (720, 1280), (120, 80, 40))
        im.save(locked_img)
        locked_h = imagehash.phash(im)
        
        # İkiz aday oluştur (küçük fark)
        cand_img = self.temp_dir / "cand_twin.jpg"
        im_twin = im.copy()
        im_twin.putpixel((5, 5), (121, 81, 41))
        im_twin.save(cand_img)
        
        candidate_pool = [
            {
                "type": "image",
                "path": str(cand_img),
                "source_video_id": "src_new_unique_id"
            }
        ]
        
        rep = orch.select_replacement_asset(
            athlete_key="james_harden",
            target_query="James Harden portrait in NBA arena",
            target_type="image",
            locked_source_ids=set(),
            locked_hashes=[(0, "locked_frame.jpg", [locked_h])],
            candidate_pool=candidate_pool,
            work_dir=self.temp_dir
        )
        self.assertIsNone(rep, "Kilitli sahnelerle Hamming mesafesi < 10 olan pHash ikizi reddedilmelidir!")

    def test_gate6_video_patch_router_resolves_nested_folder(self):
        """routers/video_patch.py leaf klasör adıyla çağrıldığında 404 vermeden hedef videoyu bulmalıdır."""
        from src.routers.video_patch import _resolve_video_file
        job_id = "exec_mat_20261104_224042_The_Deceleration_Secret_Behind"
        resolved = _resolve_video_file(folder=job_id, direct_path=None)
        self.assertTrue(resolved.exists(), f"Video dosyası bulunmalı: {resolved}")
        self.assertEqual(resolved.name, "final.mp4")

    def test_gate6_orchestrator_patch_video_preserves_locked_scenes(self):
        """BasketballOrchestrator.patch_video kilitli sahnelerin dosya yolu ve karelerini 100% korur."""
        mock_job_id = "test_orchestrator_patch_job"
        mock_job_dir = PROJECT_ROOT / "output" / "thebasketballshows" / "kontrol" / mock_job_id
        mock_job_dir.mkdir(parents=True, exist_ok=True)
        work_dir = mock_job_dir / "basketball_v2_work"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Ses dosyası
            orig_vo = PROJECT_ROOT / "output" / "thebasketballshows" / "kontrol" / "exec_mat_20261104_224042_The_Deceleration_Secret_Behind" / "voiceover.mp3"
            if not orig_vo.exists():
                orig_vo = PROJECT_ROOT / "output" / "thebasketballshows" / "yuklenen" / "exec_mat_20261104_224042_The_Deceleration_Secret_Behind" / "voiceover.mp3"
            if not orig_vo.exists():
                orig_vo = PROJECT_ROOT / "remotion" / "public" / "media" / "basketball" / "exec_mat_20261104_224042_The_Deceleration_Secret_Behind" / "voiceover.mp3"
            shutil.copy2(str(orig_vo), str(mock_job_dir / "voiceover.mp3"))

            # 2. Gerçek küratörlü fotoğraflardan kopyala (CLIP Gate 2 ve Laplacian Gate 4 onaylı)
            harden_assets_dir = PROJECT_ROOT / "assets" / "curated_sports" / "athletes" / "james_harden"
            img0 = self.temp_dir / "scene0_frozen.jpg"
            img1_old = self.temp_dir / "scene1_to_replace.jpg"
            img1_new = self.temp_dir / "scene1_new_replacement.jpg"

            shutil.copy2(str(harden_assets_dir / "photo_001_harden_sprint_fullspeed.jpg"), str(img0))
            shutil.copy2(str(harden_assets_dir / "photo_002_harden_dribble_drive.jpg"), str(img1_old))
            shutil.copy2(str(harden_assets_dir / "photo_005_stepback_three.jpg"), str(img1_new))

            # 3. İlk manifest
            initial_manifest = {
                "job_id": mock_job_id,
                "athlete_key": "james_harden",
                "topic": "The Deceleration Secret Behind James Harden",
                "total_frames": 120,
                "fps": 30,
                "cuts": [
                    {
                        "cut_index": 0,
                        "id": "cut_0",
                        "media_path": str(img0),
                        "media_type": "image",
                        "source_video_id": "src_scene0_immutable",
                        "concrete_visual_query": "James Harden running fast sprint in Houston Rockets red jersey on basketball court",
                        "start_frame": 0,
                        "duration_frames": 60,
                        "duration_sec": 2.0,
                        "locked": True
                    },
                    {
                        "cut_index": 1,
                        "id": "cut_1",
                        "media_path": str(img1_old),
                        "media_type": "image",
                        "source_video_id": "src_scene1_replaceable",
                        "concrete_visual_query": "James Harden low dribble drive penetration past defender on hardwood court",
                        "start_frame": 60,
                        "duration_frames": 60,
                        "duration_sec": 2.0,
                        "locked": False
                    }
                ]
            }
            manifest_file = mock_job_dir / "timeline_manifest.json"
            manifest_file.write_text(json.dumps(initial_manifest, indent=2), encoding="utf-8")

            # 4. Patch segment ile cut 1'i güncelle
            patch_seg = {
                1: {
                    "type": "image",
                    "path": str(img1_new),
                    "source_video_id": "src_scene1_new_replacement",
                    "concrete_visual_query": "James Harden elevated step back three point jump shot release over defender on court"
                }
            }

            orch = BasketballOrchestrator(channel_id="thebasketballshows")

            # Remotion render ve RVC adımlarını mock'la
            raw_out = work_dir / "remotion_raw_output.mp4"
            with patch("subprocess.run") as mock_sub:
                def fake_run(cmd, *args, **kwargs):
                    if "remotion" in cmd:
                        raw_out.write_bytes(b"dummy remotion mp4 render output" * 50000)
                    return MagicMock(returncode=0, stdout="", stderr="")

                mock_sub.side_effect = fake_run

                with patch("src.voice_clone_manager.VoiceCloneManager.apply_voice_clone_to_video") as mock_vc:
                    mock_vc.return_value = {"success": True, "clone_name": "vc_1792868444", "processing_time_sec": 1.0}

                    patched_final = orch.patch_video(
                        job_id=mock_job_id,
                        athlete_key="james_harden",
                        topic="The Deceleration Secret Behind",
                        unlock_indices=[1],
                        patch_segments=patch_seg
                    )

            # 5. Doğrulama: Manifest güncellendi mi?
            updated_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            cuts = updated_manifest["cuts"]
            self.assertEqual(len(cuts), 2)

            # Cut 0: TAMAMEN DONDURULMUŞ (start_frame=0, duration_frames=60, media_path=img0)
            self.assertEqual(cuts[0]["start_frame"], 0)
            self.assertEqual(cuts[0]["duration_frames"], 60)
            self.assertEqual(cuts[0]["source_video_id"], "src_scene0_immutable")
            self.assertTrue(cuts[0]["locked"])

            # Cut 1: YENİLENMİŞ (start_frame=60, duration_frames=60, source_video_id=src_scene1_new_replacement)
            self.assertEqual(cuts[1]["start_frame"], 60)
            self.assertEqual(cuts[1]["duration_frames"], 60)
            self.assertEqual(cuts[1]["source_video_id"], "src_scene1_new_replacement")
            self.assertTrue(cuts[1]["locked"])

        finally:
            shutil.rmtree(mock_job_dir, ignore_errors=True)
            public_mock = PROJECT_ROOT / "remotion" / "public" / "media" / "basketball" / mock_job_id
            shutil.rmtree(public_mock, ignore_errors=True)

    def test_gate6_parse_qa_plain_text_instruction(self):
        """QA raporundan gelen düz metin yama talimatı doğru indeks, zaman damgası ve bayraklara ayrıştırılmalıdır."""
        qa_text = (
            "[VIDEO PATCH & RE-RENDER INSTRUCTION]\n"
            "Job ID: exec_mat_20261104_224042_The_Deceleration_Secret_Behind\n"
            "Target: James Harden\n"
            "Cut 3 (00:06 – 00:08): Amatör salon ve tuğla duvarı kaldır. Replace with 'James Harden step back three point'.\n"
            "Cut 7 (00:14 – 00:16): Statik serbest atış sırasını yenile.\n"
            "Unlock Indices: 3, 7\n"
            "BYPASS_CACHE=True\n"
        )
        parsed = parse_qa_patch_instruction(qa_text)
        self.assertEqual(parsed["job_id"], "exec_mat_20261104_224042_The_Deceleration_Secret_Behind")
        self.assertEqual(parsed["athlete_key"], "james_harden")
        self.assertEqual(parsed["unlock_indices"], [3, 7])
        self.assertTrue(parsed["bypass_cache"])
        self.assertIn(3, parsed["patch_segments"])
        self.assertIn("James Harden step back", parsed["patch_segments"][3]["concrete_visual_query"])

    def test_gate6_apply_video_patch_plain_text_body(self):
        """/api/video-patch düz metin (plain text) QA talimatını aldığında no-op yapmadan hedef sahneleri çözer ve orkestratöre iletir."""
        job_id = "exec_mat_20261104_224042_The_Deceleration_Secret_Behind"
        qa_text = (
            f"[VIDEO PATCH & RE-RENDER INSTRUCTION]\n"
            f"Job ID: {job_id}\n"
            f"Cut 3 (00:06 – 00:08): Amateur gym with brick wall. Replace with NBA game action.\n"
            f"Unlock Indices: 3\n"
            f"BYPASS_CACHE=True"
        )
        with patch.object(BasketballOrchestrator, "patch_video") as mock_patch:
            mock_video = PROJECT_ROOT / "output" / "thebasketballshows" / "kontrol" / job_id / "final.mp4"
            mock_patch.return_value = mock_video

            res = apply_video_patches(payload=None, body_text=qa_text)

            self.assertTrue(res["success"])
            self.assertEqual(res["video_path"], str(mock_video))
            self.assertIn(3, res["unlocked_indices"])
            self.assertTrue(res["bypass_cache"])
            mock_patch.assert_called_once()
            call_kw = mock_patch.call_args[1]
            self.assertEqual(call_kw["job_id"], job_id)
            self.assertEqual(call_kw["unlock_indices"], [3])
            self.assertTrue(call_kw["bypass_cache"])

    def test_gate2_and_3_auto_requery_loop_eliminates_bad_fallback(self):
        """Aday havuzu boş olduğunda veya elendiğinde, eski bozuk klibe fallback yapılmaz; re-query döngüsü çalışır ve yoksa hata fırlatır."""
        orch = BasketballOrchestrator()
        # Tüm kilitli kaynaklar dolu simülasyonu
        locked_sources = {"src_espn_sport_science", "src_clippers_wesley_2018", "src_warriors_winner_broadcast"}

        # Boş başlangıç havuzu verildiğinde otomatik re-query çalışmalı
        rep = orch.select_replacement_asset(
            athlete_key="james_harden",
            target_query="James Harden playing basketball in red uniform on hardwood court",
            target_type="image",
            locked_source_ids=set(),
            locked_hashes=[],
            candidate_pool=[],  # Boş havuz!
            work_dir=self.temp_dir
        )
        self.assertIsNotNone(rep, "Otomatik re-query havuz boşken küratörlü arşivden onaylı aday bulmalıdır!")
        self.assertEqual(rep["type"], "image")
        self.assertGreaterEqual(rep["laplacian_variance"], 75.0)

    def test_cache_invalidation_bypass_cache(self):
        """BYPASS_CACHE=True olduğunda eski dilim ve doğrulama klasörleri sıfırlanmalıdır."""
        work_sub = self.temp_dir / "test_cache_work"
        work_sub.mkdir(parents=True, exist_ok=True)
        test_clips = work_sub / "action_clips"
        test_clips.mkdir(parents=True, exist_ok=True)
        stale_file = test_clips / "stale_old_slice.mp4"
        stale_file.write_bytes(b"stale data")
        self.assertTrue(stale_file.exists())

        # bypass_cache=True ile VideoHarvester başlatıldığında temizlenmeli
        harvester = VideoHarvester(work_dir=work_sub, bypass_cache=True)
        self.assertFalse(stale_file.exists(), "stale_old_slice.mp4 bypass_cache=True ile silinmelidir!")

    def test_gate_verification_explicit_scores_logged(self):
        """verify_slice çıktısı SigLIP_score ve negative_label_score değerlerini konsola açıkça sunmalıdır."""
        harden_img = PROJECT_ROOT / "assets/curated_sports/athletes/james_harden/photo_001_harden_sprint_fullspeed.jpg"
        if harden_img.exists():
            res = self.vision_verifier.verify_slice(
                media_path=harden_img,
                concrete_visual_query="James Harden running fast sprint in Houston Rockets red jersey on basketball court",
                target_subject="james_harden"
            )
            self.assertTrue(res["passed"])
            self.assertIn("SigLIP_score", res)
            self.assertIn("negative_label_score", res)
            self.assertIn("negative_label", res)
            self.assertGreaterEqual(res["SigLIP_score"], 0.26)
            self.assertLessEqual(res["negative_label_score"], res["pos_score"])

    def test_gate6_apply_video_patch_json_body_with_job_id(self):
        """JSON payload ile job_id veya folder gönderildiğinde 404 vermeden çözümlenmelidir."""
        job_id = "exec_mat_20261104_224042_The_Deceleration_Secret_Behind"
        json_body = json.dumps({
            "job_id": job_id,
            "unlock_indices": [1],
            "bypass_cache": True
        })
        with patch.object(BasketballOrchestrator, "patch_video") as mock_patch:
            mock_video = PROJECT_ROOT / "output" / "thebasketballshows" / "kontrol" / job_id / "final.mp4"
            mock_patch.return_value = mock_video

            res = apply_video_patches(payload=None, body_text=json_body)
            self.assertTrue(res["success"])
            self.assertEqual(res["video_path"], str(mock_video))
            self.assertIn(1, res["unlocked_indices"])
            self.assertTrue(res["bypass_cache"])

    def test_gate6_parse_qa_instruction_athlete_to_job_id_fallback(self):
        """Job ID belirtilmeyen fakat sporcu adı geçen QA metninde ilgili kontrol işi otomatik bağlanmalıdır."""
        qa_text_harden = (
            "Son yüklediğin videonun (final_11.mp4) amatör salon kesitini kaldır.\n"
            "James Harden için Cut 3 yenilensin.\n"
            "Unlock Indices: 3\n"
            "BYPASS_CACHE=True"
        )
        parsed = parse_qa_patch_instruction(qa_text_harden)
        self.assertEqual(parsed["athlete_key"], "james_harden")
        self.assertEqual(parsed["job_id"], "exec_mat_20261104_224042_The_Deceleration_Secret_Behind")
        self.assertIn(3, parsed["unlock_indices"])
        self.assertTrue(parsed["bypass_cache"])

        qa_text_fisher = "Derek Fisher 0.4s buzzer beater videosundaki sahneyi yenile. Cut 5."
        parsed_f = parse_qa_patch_instruction(qa_text_fisher)
        self.assertEqual(parsed_f["athlete_key"], "derek_fisher")
        self.assertEqual(parsed_f["job_id"], "exec_mat_20261104_224042_The_Neurobiology_of_Derek_Fish")
        self.assertIn(5, parsed_f["unlock_indices"])

    def test_gate4_pacing_splitter_never_duplicates_cut_on_pool_exhaustion(self):
        """Pacing splitter havuz boşaldığında asla aynı klibi (cut) tekrar etmez; hata fırlatarak kalkanı korur."""
        orch = BasketballOrchestrator()
        cuts = [
            {
                "id": "long_scene_exhausted",
                "mediaPath": "media/nonexistent.mp4",
                "media_path": "/tmp/nonexistent_unique_12345.mp4",
                "mediaType": "video",
                "startFrame": 0,
                "durationInFrames": 150,  # 5.0 saniye @ 30fps
                "locked": True
            }
        ]
        # select_replacement_asset'in None dönmesini simüle et (tüm havuz tüketilmiş)
        with patch.object(BasketballOrchestrator, "select_replacement_asset", return_value=None):
            with self.assertRaises(RuntimeError) as cm:
                orch.enforce_hard_pacing_limits(cuts, backup_pool=[], max_cut_duration=2.40, fps=30)
            self.assertIn("Aynı klibe", str(cm.exception))
            self.assertIn("fallback yapılması ve ikiz sahne üretilmesi engellendi", str(cm.exception))

    def test_gate1_produce_video_bypass_cache_unlinks_stale_manifest(self):
        """produce_video bypass_cache=True ile çağrıldığında eski manifest dosyasını deterministik olarak temizlemelidir."""
        mock_job_id = "test_bypass_cache_manifest_cleanup"
        mock_job_dir = PROJECT_ROOT / "output" / "thebasketballshows" / "kontrol" / mock_job_id
        mock_job_dir.mkdir(parents=True, exist_ok=True)
        work_dir = mock_job_dir / "basketball_v2_work"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Sahte voiceover ve stale manifest oluştur
            vo_file = mock_job_dir / "voiceover.mp3"
            orig_vo = PROJECT_ROOT / "output" / "thebasketballshows" / "kontrol" / "exec_mat_20261104_224042_The_Deceleration_Secret_Behind" / "voiceover.mp3"
            if not orig_vo.exists():
                orig_vo = PROJECT_ROOT / "output" / "thebasketballshows" / "yuklenen" / "exec_mat_20261104_224042_The_Deceleration_Secret_Behind" / "voiceover.mp3"
            if not orig_vo.exists():
                orig_vo = PROJECT_ROOT / "remotion" / "public" / "media" / "basketball" / "exec_mat_20261104_224042_The_Deceleration_Secret_Behind" / "voiceover.mp3"
            shutil.copy2(str(orig_vo), str(vo_file))

            manifest_file = mock_job_dir / "timeline_manifest.json"
            manifest_file.write_text(json.dumps({"job_id": mock_job_id, "cuts": [{"id": "stale_cut_0"}]}))
            self.assertTrue(manifest_file.exists())

            # 2. produce_video'yu bypass_cache=True ile çağır (harvester ve remotion adımlarını mock'la)
            orch = BasketballOrchestrator(channel_id="thebasketballshows")
            raw_out = work_dir / "remotion_raw_output.mp4"

            def fake_run(cmd, *args, **kwargs):
                if "remotion" in cmd:
                    raw_out.write_bytes(b"dummy remotion mp4 render output" * 50000)
                return MagicMock(returncode=0, stdout="", stderr="")

            with patch.object(VideoHarvester, "build_unique_asset_pool") as mock_pool, \
                 patch("src.modules.basketball.orchestrator.get_audio_duration", return_value=2.0), \
                 patch.object(BasketballAssetValidator, "validate_timeline", return_value=(True, [])), \
                 patch("subprocess.run", side_effect=fake_run), \
                 patch("src.voice_clone_manager.VoiceCloneManager.apply_voice_clone_to_video", return_value={"success": True, "clone_name": "vc_test", "processing_time_sec": 0.5}):
                
                # Mock bir geçerli varlık dön
                harden_img = PROJECT_ROOT / "assets/curated_sports/athletes/james_harden/photo_001_harden_sprint_fullspeed.jpg"
                mock_pool.return_value = [{
                    "type": "image",
                    "path": str(harden_img),
                    "name": harden_img.name,
                    "source_video_id": "src_fresh_unique_0",
                    "concrete_visual_query": "fresh unique action",
                    "target_subject": "james_harden"
                }]

                orch.produce_video(
                    job_id=mock_job_id,
                    athlete_key="james_harden",
                    topic="Fresh Topic",
                    voice_clone_id="vc_1792868444",
                    force_rebuild=False,
                    bypass_cache=True
                )

                # Yeni manifest yazıldı mı ve eski "stale_cut_0" temizlendi mi kontrol et
                updated_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                cut_ids = [c["id"] for c in updated_manifest["cuts"]]
                self.assertNotIn("stale_cut_0", cut_ids, "Eski bayat manifest kesiti sıfırlanmalıdır!")
        finally:
            shutil.rmtree(mock_job_dir, ignore_errors=True)
            public_mock = PROJECT_ROOT / "remotion" / "public" / "media" / "basketball" / mock_job_id
            shutil.rmtree(public_mock, ignore_errors=True)

    def test_gate1_project_isolation_lock_enforcement(self):
        """Project Isolation Lock: Spurs/Fisher varlıkları Harden havuzuna, Harden varlıkları Fisher havuzuna ASLA sızamaz."""
        from src.modules.basketball.video_harvester import is_source_banned_for_project, VideoHarvester

        harvester = VideoHarvester(work_dir=Path("/tmp/test_harv_iso"), project_id="exec_test_harden")
        self.assertTrue(harvester.project_isolation_lock, "project_isolation_lock aktif olmalıdır!")

        # Harden için Fisher/Spurs varlıkları yasaklıdır
        self.assertTrue(is_source_banned_for_project("src_spurs_game5_2004", "james_harden"))
        self.assertTrue(is_source_banned_for_project("photo_003_sbc_center.jpg", "james_harden"))
        self.assertTrue(is_source_banned_for_project("derek_fisher_01.mp4", "james_harden"))
        self.assertTrue(is_source_banned_for_project("trent_tucker_rule", "james_harden"))

        # Fisher için Harden/Rockets varlıkları yasaklıdır
        self.assertTrue(is_source_banned_for_project("harden_nba_stepbacks.mp4", "derek_fisher"))
        self.assertTrue(is_source_banned_for_project("houston_rockets_drive", "derek_fisher"))
        self.assertTrue(is_source_banned_for_project("wesley_johnson_anklebreaker", "derek_fisher"))

        # Meşru ve tarafsız varlıklar yasaklanmaz
        self.assertFalse(is_source_banned_for_project("nba_neutral_action.mp4", "james_harden"))
        self.assertFalse(is_source_banned_for_project("nba_neutral_action.mp4", "derek_fisher"))


if __name__ == "__main__":
    unittest.main()
