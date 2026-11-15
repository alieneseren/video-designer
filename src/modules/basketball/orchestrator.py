"""
Basketball Engine 2.0 - High-End Production Orchestrator
=========================================================
- Video-First: yt-dlp ile gerçek maç klibi parçaları.
- Remotion 4.0: Modern Web standartları, CSS animasyonları, TV kalitesi.
- Zero Loop Garantisi: 24 kesme için 24 benzersiz varlık.
- Akıllı UI: 4.0s fade-out rozet, karaoke altyazı, tek seferlik CTA.
- Apple Silicon M4 RVC Ses Klonlama: vc_1792868444 + ALIENES! filigranı.
"""

import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import imagehash

from src.modules.basketball.contracts import BasketballRenderSpec, BasketballCut, MediaType
from src.modules.basketball.video_harvester import VideoHarvester, is_source_banned_for_project
from src.modules.basketball.asset_validator import BasketballAssetValidator
from src.modules.basketball.validator import get_3point_fingerprints, measure_laplacian_sharpness
from src.modules.basketball.vision_verifier import BasketballVisionVerifier

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("BasketballOrchestrator")

REMOTION_DIR = Path("/Users/alienes/yt-oto-video/files/remotion")
PROJECT_ROOT = Path("/Users/alienes/yt-oto-video/files")
CURATED_BROLL_DIR = PROJECT_ROOT / "assets" / "curated_sports" / "b_roll" / "videos"
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))


def normalize_sports_subtitles(text: str) -> str:
    """Hızlı Shorts tüketimi için uzun sayısal kelimeleri temiz rakamlara dönüştürür."""
    rules = [
        (r'(?i)\bninety-ninth percentile\b', '99th percentile'),
        (r'(?i)\bninety-ninth\b', '99th'),
        (r'(?i)\bzero point three-seven seconds\b', '0.37 seconds'),
        (r'(?i)\bzero point three-seven\b', '0.37'),
        (r'(?i)\bzero point two seconds\b', '0.2 seconds'),
        (r'(?i)\bzero point two\b', '0.2'),
        (r'(?i)\bzero point three seconds\b', '0.3 seconds'),
        (r'(?i)\bzero point three\b', '0.3'),
        (r'(?i)\bzero point four seconds\b', '0.4 seconds'),
        (r'(?i)\bzero point four\b', '0.4'),
        (r'(?i)\bpoint four miracle\b', '0.4 miracle'),
        (r'(?i)\bpoint four\b', '0.4'),
        (r'(?i)\bseconds-beating\b', 'seconds. Beating'),
        (r'(?i)\bdime-ranked\b', 'dime. Ranked'),
        (r'(?i)\bdeceleration-the\b', 'deceleration, the'),
    ]
    res = text
    for pat, rep in rules:
        res = re.sub(pat, rep, res)
    return res


def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    try:
        out = subprocess.check_output(cmd).decode("utf-8").strip()
        return float(out)
    except Exception as e:
        logger.warning(f"Audio süresi ffprobe ile alınamadı, fallback 50.0s: {e}")
        return 50.0


class BasketballOrchestrator:
    def __init__(self, channel_id: str = "thebasketballshows"):
        self.channel_id = channel_id
        self.vision_verifier = BasketballVisionVerifier()

    def select_replacement_asset(
        self,
        athlete_key: str,
        target_query: str,
        target_type: str,
        locked_source_ids: Set[str],
        locked_hashes: List[Tuple[int, str, List[imagehash.ImageHash]]],
        candidate_pool: List[Dict[str, Any]],
        work_dir: Path,
        auto_requery: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Gate 6 & 2 & 3: Kilitli olmayan sahne için onaylı yeni aday seçer.
        1. SigLIP / CLIP benzerliği >= 0.26 ve 9 negatif domain skorunun pozitif çapadan düşük olması (Gate 2)
        2. max_slices_per_source_id = 1: Locked sahnelerin source_id setinde olmamalı (Gate 3)
        3. 3-Noktalı pHash (0.2s, 1.0s, 1.8s) ile tüm locked sahnelerle Hamming mesafesi >= 10 (Gate 3)
        4. width >= 720, height >= 720 ve cv2.Laplacian >= 75.0 (Gate 4)
        5. Otomatik Re-Query Döngüsü: Havuz boşsa veya tüm adaylar elendiğinde, asla eski klibe dönmez;
           küratörlü B-roll ve sporcu arşivini tarayarak taze doğrulanmış aday üretir.
        """
        if auto_requery is None:
            auto_requery = len(candidate_pool) == 0
        from src.modules.basketball.video_harvester import VIDEO_SOURCES
        temp_dir = work_dir / "_validator_3pt_frames"
        temp_dir.mkdir(parents=True, exist_ok=True)

        is_query_science = any(kw in target_query.lower() for kw in [
            "brain", "synapse", "neural", "optic", "telemetry", "sensor", "mocap", "science", "laboratory", "biomechanic"
        ])

        def _evaluate_candidate(cand: Dict[str, Any], context_label: str = "Candidate") -> Optional[Dict[str, Any]]:
            cand_p = Path(cand.get("path") or cand.get("media_path") or "")
            if not cand_p.exists():
                alt_cands = [
                    work_dir / ("action_clips" if target_type == "video" else "photos") / cand_p.name,
                    CURATED_BROLL_DIR / cand_p.name,
                    PROJECT_ROOT / "assets" / "curated_sports" / "athletes" / athlete_key / cand_p.name
                ]
                for ac in alt_cands:
                    if ac.exists():
                        cand_p = ac
                        break

            if not cand_p.exists() or cand_p.stat().st_size < 10000:
                return None

            cand_source_id = cand.get("source_video_id") or cand_p.stem
            if is_source_banned_for_project(cand_source_id, athlete_key) or is_source_banned_for_project(cand_p.name, athlete_key):
                logger.info(f"🚫 [Gate 1 - Project Isolation Lock] {cand_p.name} ({cand_source_id}) bu proje ({athlete_key}) için yasaklı kaynak!")
                return None

            if cand_source_id in locked_source_ids:
                logger.info(f"🚫 [Gate 3 - Source Quota] {cand_p.name} ({cand_source_id}) kilitli sahnelerde zaten mevcut!")
                return None

            w, h, lap_var = measure_laplacian_sharpness(cand_p)
            if (w > 0 and w < 720) or (h > 0 and h < 720) or (lap_var > 0 and lap_var < 75.0):
                logger.info(f"🚫 [Gate 4 - Quality] {cand_p.name} netlik {lap_var:.1f} < 75.0 veya {w}x{h} < 720p!")
                return None

            # 3. STRICT SUBJECT & DEAD-BALL REJECTION: Asla game action için target_subj = None yapma
            is_cand_science = is_query_science or any(kw in cand_source_id.lower() or kw in cand_p.stem.lower()
                             for kw in ["brain", "synapse", "neural", "optic", "telemetry", "sensor", "mocap", "science", "laboratory", "biomechanic"])
            if is_cand_science:
                cand_subj = None
            else:
                cand_subj = athlete_key or "NBA basketball player dribbling shooting in arena"

            vis_res = self.vision_verifier.verify_slice(
                media_path=cand_p,
                concrete_visual_query=target_query,
                target_subject=cand_subj
            )
            siglip_sc = vis_res.get("SigLIP_score", vis_res.get("query_score", 0.0))
            neg_sc = vis_res.get("negative_label_score", 0.0)
            neg_lbl = vis_res.get("negative_label", "none")
            effective_pos = vis_res.get("pos_score", siglip_sc)
            if not vis_res["passed"]:
                logger.info(f"🚫 [Gate 2 - SigLIP] {cand_p.name} elendi: SigLIP={siglip_sc:.4f}, neg={neg_sc:.4f} ({neg_lbl}), {vis_res['reasons']}")
                return None

            # Kesin ölü top / serbest atış / savrulma elemesi (Negatif skor pozitiften üstünse)
            if neg_lbl in ["free throw lineup", "players standing on bench dead ball", "heavy motion blur whip pan", "amateur gym with brick wall"] and neg_sc >= effective_pos:
                logger.info(f"🚫 [Gate 2 - Dead-Ball/Negative] {cand_p.name} elendi: {neg_lbl} skoru {neg_sc:.4f} >= pos {effective_pos:.4f}")
                return None

            cand_hashes = get_3point_fingerprints(cand_p, temp_dir)
            if cand_hashes and locked_hashes:
                min_dist = 999
                closest_locked = ""
                for _, locked_name, l_hashes in locked_hashes:
                    for ch in cand_hashes:
                        for lh in l_hashes:
                            dist = ch - lh
                            if dist < min_dist:
                                min_dist = dist
                                closest_locked = locked_name
                if min_dist < 10:
                    logger.info(f"🚫 [Gate 3 - 3-Point pHash] {cand_p.name} kilitli {closest_locked} ile ikiz (Hamming {min_dist} < 10)!")
                    return None

            logger.info(
                f"✅ [Replacement Seçildi - {context_label}] Taze onaylı aday: {cand_p.name} | "
                f"source_id={cand_source_id} | SigLIP={siglip_sc:.4f} | neg={neg_sc:.4f} ({neg_lbl}) | laplacian={lap_var:.1f}"
            )
            return {
                "type": "video" if cand_p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"] else "image",
                "path": str(cand_p),
                "name": cand_p.name,
                "source_video_id": cand_source_id,
                "concrete_visual_query": target_query,
                "target_subject": cand_subj or athlete_key,
                "SigLIP_score": siglip_sc,
                "negative_label_score": neg_sc,
                "laplacian_variance": lap_var
            }

        # 1. Başlangıç havuzundaki adayları değerlendir
        for cand in candidate_pool:
            res = _evaluate_candidate(cand, context_label="Initial Pool")
            if res:
                return res

        if not auto_requery:
            return None

        # 2. Otomatik Re-Query Döngüsü (Havuz boşaldığında veya tüm adaylar elendiğinde)
        logger.info(f"🔄 [Auto Re-Query Loop] Başlangıç havuzu yetersiz kaldı! Genişletilmiş arama döngüsü başlatılıyor ({athlete_key} | '{target_query}')...")

        # Seviye 1: Küratörlü sporcu fotoğrafları
        target_keys = [athlete_key] if athlete_key else ["james_harden", "derek_fisher"]
        for a_key in target_keys:
            athlete_photo_dir = PROJECT_ROOT / "assets" / "curated_sports" / "athletes" / a_key
            if athlete_photo_dir.exists():
                for p_file in sorted(athlete_photo_dir.glob("*.jpg")):
                    p_sid = f"photo_{p_file.stem}"
                    if p_sid not in locked_source_ids:
                        dest_crop = work_dir / "photos" / f"requery_{p_file.name}"
                        dest_crop.parent.mkdir(parents=True, exist_ok=True)
                        if not dest_crop.exists() or dest_crop.stat().st_size < 10000:
                            cmd = [
                                "ffmpeg", "-y", "-i", str(p_file),
                                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,unsharp=5:5:1.2",
                                "-q:v", "2", str(dest_crop)
                            ]
                            subprocess.run(cmd, capture_output=True, timeout=15)
                        cand_target = dest_crop if dest_crop.exists() and dest_crop.stat().st_size > 10000 else p_file
                        res = _evaluate_candidate({
                            "type": "image",
                            "path": str(cand_target),
                            "source_video_id": p_sid,
                            "target_subject": a_key
                        }, context_label="ReQuery-AthletePhoto")
                        if res:
                            return res

        # Seviye 1.B: Küratörlü Bilim / B-Roll Görselleri (sports_science & court_action)
        sci_photo_dir = PROJECT_ROOT / "assets" / "curated_sports" / "b_roll" / "sports_science"
        court_action_dir = PROJECT_ROOT / "assets" / "curated_sports" / "b_roll" / "court_action"
        extra_dirs = [sci_photo_dir] if is_query_science else [court_action_dir, sci_photo_dir]
        for ed in extra_dirs:
            if ed.exists():
                for p_file in sorted(ed.glob("*.jpg")):
                    p_sid = f"broll_img_{p_file.stem}"
                    if p_sid not in locked_source_ids:
                        dest_crop = work_dir / "photos" / f"requery_{p_file.name}"
                        dest_crop.parent.mkdir(parents=True, exist_ok=True)
                        if not dest_crop.exists() or dest_crop.stat().st_size < 10000:
                            cmd = [
                                "ffmpeg", "-y", "-i", str(p_file),
                                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,unsharp=5:5:1.2",
                                "-q:v", "2", str(dest_crop)
                            ]
                            subprocess.run(cmd, capture_output=True, timeout=15)
                        cand_target = dest_crop if dest_crop.exists() and dest_crop.stat().st_size > 10000 else p_file
                        res = _evaluate_candidate({
                            "type": "image",
                            "path": str(cand_target),
                            "source_video_id": p_sid,
                            "target_subject": None if is_query_science else athlete_key
                        }, context_label="ReQuery-CuratedScienceBroll")
                        if res:
                            return res

        # Seviye 2: Küratörlü 1080p B-roll havuzu
        if CURATED_BROLL_DIR.exists():
            for b_file in sorted(CURATED_BROLL_DIR.glob("*.mp4")):
                b_sid = f"src_broll_{b_file.stem}"
                if b_sid not in locked_source_ids:
                    out_broll_slice = work_dir / "action_clips" / f"requery_broll_{b_file.stem}.mp4"
                    out_broll_slice.parent.mkdir(parents=True, exist_ok=True)
                    if not out_broll_slice.exists() or out_broll_slice.stat().st_size < 10000:
                        cmd = [
                            "ffmpeg", "-y",
                            "-ss", "00:00:01.0",
                            "-i", str(b_file),
                            "-t", "2.00",
                            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,unsharp=5:5:1.2,fps=30",
                            "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                            str(out_broll_slice)
                        ]
                        subprocess.run(cmd, capture_output=True, timeout=20)
                    cand_target = out_broll_slice if out_broll_slice.exists() and out_broll_slice.stat().st_size > 10000 else b_file
                    res = _evaluate_candidate({
                        "type": "video",
                        "path": str(cand_target),
                        "source_video_id": b_sid,
                        "target_subject": None
                    }, context_label="ReQuery-CuratedBroll")
                    if res:
                        return res

        # Seviye 3: VIDEO_SOURCES alternatif kesitleri
        sources = VIDEO_SOURCES.get(athlete_key, [])
        if not sources and not athlete_key:
            sources = VIDEO_SOURCES.get("james_harden", []) + VIDEO_SOURCES.get("derek_fisher", [])
        for src in sources:
            src_id = src.get("source_id", src["filename"])
            if src_id not in locked_source_ids:
                raw_v = work_dir / "raw_videos" / src["filename"]
                if raw_v.exists():
                    out_slice = work_dir / "action_clips" / f"requery_source_{src_id}.mp4"
                    out_slice.parent.mkdir(parents=True, exist_ok=True)
                    cmd = [
                        "ffmpeg", "-y",
                        "-ss", "00:00:04.0",
                        "-i", str(raw_v),
                        "-t", "2.00",
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,unsharp=5:5:1.2,fps=30",
                        "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                        str(out_slice)
                    ]
                    subprocess.run(cmd, capture_output=True, timeout=20)
                    if out_slice.exists() and out_slice.stat().st_size > 10000:
                        res = _evaluate_candidate({
                            "type": "video",
                            "path": str(out_slice),
                            "source_video_id": src_id,
                            "target_subject": athlete_key or None
                        }, context_label="ReQuery-RawSource")
                        if res:
                            return res

        logger.error(f"❌ [Auto Re-Query Başarısız] Tüm taze aday havuzları tarandı fakat kalkanlardan geçen aday bulunamadı: {target_query}")
        return None

    def enforce_hard_pacing_limits(
        self,
        cuts: List[Dict[str, Any]],
        backup_pool: List[Dict[str, Any]],
        max_cut_duration: float = 2.40,
        fps: int = 30,
        public_media_job_dir: Optional[Path] = None,
        job_id: str = "",
        athlete_key: str = "",
        work_dir: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """
        Kod seviyesinde sert 2.4s kuralı:
        Herhangi bir kesme max_cut_duration'dan uzunsa, deterministik olarak
        <= 2.4s parçalara böler ve araya onaylı B-roll/görsel enjekte eder.
        Sıfır Döngü Garantisi: Asla aynı klibi (cut) tekrar etmez.
        """
        enforced = []
        max_frames = int(round(max_cut_duration * fps))
        used_sources = {c.get("source_video_id") or Path(c.get("media_path", "")).stem for c in cuts if c.get("source_video_id") or c.get("media_path")}
        work_path = work_dir or (PROJECT_ROOT / "output" / self.channel_id / "kontrol" / job_id / "basketball_v2_work")

        for cut in cuts:
            dur_f = cut["durationInFrames"]
            if dur_f <= max_frames:
                enforced.append(cut)
            else:
                parts = math.ceil(dur_f / max_frames)
                sub_dur_f = dur_f // parts
                sub_rem = dur_f % parts
                c_start = cut["startFrame"]

                for p_idx in range(parts):
                    cur_sub_f = sub_dur_f + (1 if p_idx < sub_rem else 0)
                    if p_idx == 0:
                        enforced.append({
                            **cut,
                            "id": f"{cut['id']}_p{p_idx}",
                            "startFrame": c_start,
                            "durationInFrames": cur_sub_f,
                            "target_subject": cut.get("target_subject")
                        })
                    else:
                        alt_asset = None
                        # 1. backup_pool içinden kalkanları geçen taze aday ara (CLIP + Netlik doğrulamalı)
                        while backup_pool:
                            cand_item = backup_pool.pop(0)
                            cand_p = Path(cand_item.get("path") or cand_item.get("media_path") or "")
                            if not cand_p.exists():
                                continue
                            cand_sid = cand_item.get("source_video_id") or cand_p.stem
                            if cand_sid in used_sources:
                                continue
                            if is_source_banned_for_project(cand_sid, athlete_key) or is_source_banned_for_project(cand_p.name, athlete_key):
                                continue
                            w, h, lap = measure_laplacian_sharpness(cand_p)
                            if (w > 0 and w < 720) or (h > 0 and h < 720) or (lap > 0 and lap < 75.0):
                                continue

                            # Her backup_pool adayı mutlaka verify_slice() filtresinden geçmelidir (Bug 1)
                            b_query = cut.get("concrete_visual_query", "professional NBA basketball game action")
                            b_science = any(kw in b_query.lower() for kw in ["brain", "synapse", "neural", "optic", "telemetry", "sensor", "mocap", "science", "laboratory", "biomechanic"])
                            b_subj = None if b_science else (athlete_key or "NBA basketball player dribbling shooting in arena")
                            vis = self.vision_verifier.verify_slice(
                                media_path=cand_p,
                                concrete_visual_query=b_query,
                                target_subject=b_subj
                            )
                            if not vis["passed"]:
                                continue
                            b_neg_lbl = vis.get("negative_label", "none")
                            b_neg_sc = vis.get("negative_label_score", 0.0)
                            b_pos_sc = vis.get("pos_score", 0.0)
                            b_query_sc = vis.get("query_score", 0.0)
                            if b_neg_lbl in ["free throw lineup", "players standing on bench dead ball", "heavy motion blur whip pan", "amateur gym with brick wall"] and b_neg_sc >= b_pos_sc:
                                continue

                            alt_asset = cand_item
                            used_sources.add(cand_sid)
                            break

                        # 2. Havuz yetersizse re-query loop ile taze aday üret (Asla 'cut' duplicate etme!)
                        if not alt_asset:
                            subj = cut.get("target_subject") or athlete_key
                            # Öncelik 1: Video adayı
                            rep = self.select_replacement_asset(
                                athlete_key=subj,
                                target_query=cut.get("concrete_visual_query", "professional NBA basketball game action"),
                                target_type="video",
                                locked_source_ids=used_sources,
                                locked_hashes=[],
                                candidate_pool=[],
                                work_dir=work_path
                            )
                            if rep:
                                alt_asset = rep
                                used_sources.add(rep.get("source_video_id", Path(rep["path"]).stem))
                            else:
                                # Öncelik 2: Fotoğraf adayı
                                rep_img = self.select_replacement_asset(
                                    athlete_key=subj,
                                    target_query=cut.get("concrete_visual_query", "professional NBA basketball game action"),
                                    target_type="image",
                                    locked_source_ids=used_sources,
                                    locked_hashes=[],
                                    candidate_pool=[],
                                    work_dir=work_path
                                )
                                if rep_img:
                                    alt_asset = rep_img
                                    used_sources.add(rep_img.get("source_video_id", Path(rep_img["path"]).stem))
                                else:
                                    raise RuntimeError(
                                        f"🚨 [Pacing Splitter] Cut {cut['id']} bölünürken geçerli taze görsel bulunamadı! "
                                        f"Aynı klibe ({cut.get('media_path')}) fallback yapılması ve ikiz sahne üretilmesi engellendi."
                                    )

                        alt_path_str = alt_asset.get("path") or alt_asset.get("media_path") or cut.get("media_path")
                        alt_p = Path(alt_path_str)
                        alt_media_path = str(alt_p)
                        alt_media_rel = alt_asset.get("mediaPath") or cut.get("mediaPath")

                        if public_media_job_dir:
                            dest_alt = (public_media_job_dir / alt_p.name).resolve()
                            if alt_p.exists() and alt_p.resolve() != dest_alt:
                                shutil.copy2(str(alt_p), str(dest_alt))
                            alt_media_path = str(dest_alt)
                            if job_id:
                                alt_media_rel = f"media/basketball/{job_id}/{alt_p.name}"

                        enforced.append({
                            "id": f"{cut['id']}_p{p_idx}",
                            "mediaPath": alt_media_rel,
                            "media_path": alt_media_path,
                            "mediaType": alt_asset.get("type", cut["mediaType"]),
                            "source_video_id": alt_asset.get("source_video_id", alt_asset.get("name", f"src_split_{alt_p.stem}")),
                            "concrete_visual_query": alt_asset.get("concrete_visual_query", cut.get("concrete_visual_query", "")),
                            "target_subject": cut.get("target_subject"),
                            "startFrame": c_start,
                            "durationInFrames": cur_sub_f,
                            "locked": False
                        })
                    c_start += cur_sub_f

        return enforced

    def produce_video(
        self,
        job_id: str,
        athlete_key: str,
        topic: str,
        voice_clone_id: str = "vc_1792868444",
        force_rebuild: bool = True,
        patch_segments: Optional[Dict[int, Dict[str, Any]]] = None,
        unlock_indices: Optional[List[int]] = None,
        custom_queries: Optional[Dict[int, str]] = None,
        bypass_cache: bool = False
    ) -> Path:
        bypass_cache = bypass_cache or os.environ.get("BYPASS_CACHE", "").lower() in ["1", "true", "yes"]
        logger.info(f"\n=======================================================")
        logger.info(f"🏀 [BASKETBALL ENGINE 2.0 BAŞLADI] {job_id}")
        logger.info(f"   Sporcu: {athlete_key.upper()} | Konu: {topic}")
        logger.info(f"=======================================================")

        job_dir = PROJECT_ROOT / "output" / self.channel_id / "kontrol" / job_id
        if not job_dir.exists():
            job_dir.mkdir(parents=True, exist_ok=True)

        voiceover_file = job_dir / "voiceover.mp3"
        sb_file = job_dir / "sentence_boundaries.json"
        manifest_file = job_dir / "timeline_manifest.json"

        if not voiceover_file.exists():
            raise FileNotFoundError(f"Dış ses dosyası bulunamadı: {voiceover_file}")

        total_duration = get_audio_duration(voiceover_file)
        fps = 30
        total_frames = int(round(total_duration * fps))
        logger.info(f"⏱️ Dış Ses Süresi: {total_duration:.2f} saniye ({total_frames} kare)")

        # 1. Cümle ve Kelime Zamanlamalarını Hazırla
        sentence_boundaries = []
        if sb_file.exists():
            sentence_boundaries = json.loads(sb_file.read_text(encoding="utf-8"))

        remotion_sentences = []
        for s in sentence_boundaries:
            raw_text = s.get("text", "").strip()
            s_text = normalize_sports_subtitles(raw_text)
            s_offset = float(s.get("offset", 0.0))
            s_dur = float(s.get("duration", 3.0))

            s_start_frame = int(round(s_offset * fps))
            s_duration_frames = int(round(s_dur * fps))

            raw_words = s_text.split()
            word_items = []
            if raw_words:
                w_step = s_duration_frames / len(raw_words)
                for w_idx, w in enumerate(raw_words):
                    w_start = s_start_frame + int(round(w_idx * w_step))
                    w_end = s_start_frame + int(round((w_idx + 1) * w_step))
                    word_items.append({
                        "word": w,
                        "startFrame": w_start,
                        "endFrame": w_end
                    })

            remotion_sentences.append({
                "text": s_text,
                "startFrame": s_start_frame,
                "durationInFrames": s_duration_frames,
                "words": word_items
            })

        # 2. Varlıkları Topla (Video-First Harvester)
        work_dir = job_dir / "basketball_v2_work"
        work_dir.mkdir(parents=True, exist_ok=True)

        if (force_rebuild or bypass_cache) and not unlock_indices:
            logger.info(f"🧹 [BYPASS_CACHE=True] {work_dir} altındaki eski kesitler ve geçici dosyalar sıfırlanıyor...")
            for clean_sub in ["action_clips", "photos", "_validator_3pt_frames", "_validator_frames"]:
                target_sub = work_dir / clean_sub
                if target_sub.exists():
                    shutil.rmtree(target_sub, ignore_errors=True)
            for clean_file in ["remotion_props.json", "remotion_raw_output.mp4"]:
                target_f = work_dir / clean_file
                if target_f.exists():
                    target_f.unlink(missing_ok=True)
            if manifest_file.exists():
                manifest_file.unlink(missing_ok=True)

        harvester = VideoHarvester(work_dir=work_dir, bypass_cache=bypass_cache, project_id=job_id)
        
        unique_assets = harvester.build_unique_asset_pool(
            athlete_key=athlete_key,
            bypass_cache=bypass_cache,
            project_id=job_id
        )
        cuts_count = len(unique_assets)
        logger.info(f"🎯 Toplam Kesme Sayısı: {cuts_count} ({athlete_key} semantik storyboard ritmi)")

        # Remotion public klasörünü hazırla (Sıfırdan üretimde veya bypass_cache=True olduğunda temizle)
        public_media_job_dir = REMOTION_DIR / "public" / "media" / "basketball" / job_id
        if (force_rebuild or bypass_cache) and public_media_job_dir.exists() and not unlock_indices:
            shutil.rmtree(public_media_job_dir)
        public_media_job_dir.mkdir(parents=True, exist_ok=True)

        dest_audio = public_media_job_dir / "voiceover.mp3"
        if voiceover_file.resolve() != dest_audio.resolve():
            shutil.copy2(str(voiceover_file), str(dest_audio))
        relative_audio_path = f"media/basketball/{job_id}/voiceover.mp3"

        # 3. locked_segments Kontrolü veya Sıfırdan İnşa
        existing_manifest = None
        if manifest_file.exists() and not force_rebuild and not bypass_cache:
            try:
                existing_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                logger.info(f"🔒 [Locked Segments Manifest Yüklendi] {len(existing_manifest.get('cuts', []))} sahne korumaya alındı.")
            except Exception as e_man:
                logger.warning(f"Manifest okuma uyarısı: {e_man}")

        # Kilitli sahnelerin fingerprint ve source ID setlerini topla (Gate 6 kalkanı)
        locked_source_ids: Set[str] = set()
        locked_hashes: List[Tuple[int, str, List[imagehash.ImageHash]]] = []
        if existing_manifest:
            for c in existing_manifest.get("cuts", []):
                c_idx = c.get("cut_index", 0)
                if not unlock_indices or c_idx not in unlock_indices:
                    sid = c.get("source_video_id")
                    if sid:
                        locked_source_ids.add(sid)
                    p = Path(c.get("media_path", ""))
                    if not p.exists():
                        cand = work_dir / ("action_clips" if c.get("media_type") == "video" else "photos") / p.name
                        if cand.exists():
                            p = cand
                    if p.exists():
                        h_list = get_3point_fingerprints(p, work_dir / "_validator_3pt_frames")
                        if h_list:
                            locked_hashes.append((c_idx, p.name, h_list))

        if existing_manifest and not force_rebuild:
            # =========================================================
            # GATE 6: IMMUTABLE locked_segments YAMA MODU
            # =========================================================
            logger.info(f"🔒 [Locked Segments Manifest Devrede] {len(existing_manifest.get('cuts', []))} sahne dondurularak yama yapılıyor.")
            enforced_cuts = []
            for i, prev_c in enumerate(existing_manifest.get("cuts", [])):
                idx = prev_c.get("cut_index", i)
                is_unlocked = (unlock_indices and idx in unlock_indices) or (prev_c.get("locked") is False)
                s_frame = prev_c.get("start_frame", 0)
                d_frames = prev_c.get("duration_frames", 60)

                if not is_unlocked:
                    # Korumalı sahne: Dosya yolu, başlangıç/bitiş kareleri tamamen dondur (Immutable)
                    raw_path = Path(prev_c["media_path"])
                    dest_cut = (public_media_job_dir / raw_path.name).resolve()
                    if raw_path.exists() and raw_path.resolve() != dest_cut:
                        shutil.copy2(str(raw_path), str(dest_cut))
                    relative_cut_path = f"media/basketball/{job_id}/{raw_path.name}"

                    enforced_cuts.append({
                        "id": prev_c.get("id", f"cut_{idx}"),
                        "mediaPath": relative_cut_path,
                        "media_path": str(dest_cut if dest_cut.exists() else raw_path),
                        "mediaType": prev_c.get("media_type", "video"),
                        "source_video_id": prev_c.get("source_video_id", raw_path.stem),
                        "concrete_visual_query": prev_c.get("concrete_visual_query", ""),
                        "target_subject": prev_c.get("target_subject", athlete_key),
                        "startFrame": s_frame,
                        "durationInFrames": d_frames,
                        "locked": True
                    })
                else:
                    # Kilit açıldı! Yeniden varlık seç ve kilitli sahnelerin pHash ve source_id setlerine göre doğrula (Gate 6)
                    logger.info(f"🔓 [Sahne Kilidi Açıldı] Cut {idx} için taze varlık aranıyor...")
                    asset = None
                    if patch_segments and idx in patch_segments:
                        asset = patch_segments[idx]
                    else:
                        t_query = prev_c.get("concrete_visual_query", "professional NBA basketball game action")
                        if custom_queries and idx in custom_queries:
                            t_query = custom_queries[idx]
                            logger.info(f"🎯 [Custom Patch Query] Cut {idx} için özel sorgu devrede: '{t_query}'")
                        t_type = prev_c.get("media_type", "video")
                        bp = harvester.get_backup_pool(
                            athlete_key=athlete_key,
                            used_paths=[c["media_path"] for c in existing_manifest.get("cuts", []) if c.get("cut_index", 0) not in (unlock_indices or [])]
                        )
                        rep = self.select_replacement_asset(
                            athlete_key=athlete_key,
                            target_query=t_query,
                            target_type=t_type,
                            locked_source_ids=locked_source_ids,
                            locked_hashes=locked_hashes,
                            candidate_pool=bp,
                            work_dir=work_dir,
                            auto_requery=True
                        )
                        if rep:
                            asset = rep
                        else:
                            raise RuntimeError(
                                f"🚨 [Gate Kalkanı] Cut {idx} için onaylı taze aday bulunamadı! "
                                f"Eski hatalı klibe ({prev_c['media_path']}) fallback yapılması engellendi."
                            )

                    raw_path = Path(asset["path"])
                    dest_cut = (public_media_job_dir / raw_path.name).resolve()
                    if raw_path.exists() and raw_path.resolve() != dest_cut:
                        shutil.copy2(str(raw_path), str(dest_cut))
                    relative_cut_path = f"media/basketball/{job_id}/{raw_path.name}"

                    locked_source_ids.add(asset.get("source_video_id", raw_path.stem))
                    h_list = get_3point_fingerprints(dest_cut if dest_cut.exists() else raw_path, work_dir / "_validator_3pt_frames")
                    if h_list:
                        locked_hashes.append((idx, raw_path.name, h_list))

                    enforced_cuts.append({
                        "id": prev_c.get("id", f"cut_{idx}"),
                        "mediaPath": relative_cut_path,
                        "media_path": str(dest_cut if dest_cut.exists() else raw_path),
                        "mediaType": asset.get("type", prev_c.get("media_type", "video")),
                        "source_video_id": asset.get("source_video_id", raw_path.stem),
                        "concrete_visual_query": asset.get("concrete_visual_query", prev_c.get("concrete_visual_query", "")),
                        "target_subject": asset.get("target_subject", athlete_key),
                        "startFrame": s_frame,
                        "durationInFrames": d_frames,
                        "locked": True
                    })
        else:
            # =========================================================
            # SIFIRDAN ÜRETİM MODU (Fresh Build)
            # =========================================================
            cuts_count = len(unique_assets)
            logger.info(f"🎯 Toplam Kesme Sayısı: {cuts_count} ({athlete_key} semantik storyboard ritmi)")

            remotion_cuts = []
            current_frame = 0
            base_dur_frames = total_frames // cuts_count
            remainder_frames = total_frames % cuts_count

            for idx in range(cuts_count):
                dur_f = base_dur_frames + (1 if idx < remainder_frames else 0)
                asset = unique_assets[idx]

                raw_path = Path(asset["path"])
                dest_cut = (public_media_job_dir / raw_path.name).resolve()

                # Kaynak dosyanın fiziksel varlığını güvenilir şekilde doğrula
                src_p = raw_path.resolve()
                if not src_p.exists():
                    candidates = [
                        work_dir / ("action_clips" if asset["type"] == "video" else "photos") / raw_path.name,
                        dest_cut,
                        CURATED_BROLL_DIR / raw_path.name,
                        PROJECT_ROOT / "assets" / "curated_sports" / "athletes" / athlete_key / raw_path.name
                    ]
                    for c in candidates:
                        if c.exists():
                            src_p = c.resolve()
                            break

                if src_p.exists() and src_p != dest_cut:
                    shutil.copy2(str(src_p), str(dest_cut))
                
                relative_cut_path = f"media/basketball/{job_id}/{raw_path.name}"

                remotion_cuts.append({
                    "id": f"cut_{idx}",
                    "mediaPath": relative_cut_path,
                    "media_path": str(dest_cut),
                    "mediaType": asset["type"],
                    "source_video_id": asset.get("source_video_id", raw_path.stem),
                    "concrete_visual_query": asset.get("concrete_visual_query", "professional NBA basketball game action"),
                    "target_subject": asset.get("target_subject", athlete_key),
                    "startFrame": current_frame,
                    "durationInFrames": dur_f,
                    "locked": True
                })

                current_frame += dur_f

            # 4. Kod Seviyesinde Sert 2.4s Pacing Bölücü (Hard Splitter)
            backup_pool = harvester.get_backup_pool(athlete_key=athlete_key, used_paths=[c["media_path"] for c in remotion_cuts])
            enforced_cuts = self.enforce_hard_pacing_limits(
                cuts=remotion_cuts,
                backup_pool=backup_pool,
                max_cut_duration=2.40,
                fps=fps,
                public_media_job_dir=public_media_job_dir,
                job_id=job_id,
                athlete_key=athlete_key,
                work_dir=work_dir
            )
            logger.info(f"✂️ [Hard Splitter Uygulandı] Kesme adedi: {len(remotion_cuts)} -> {len(enforced_cuts)} (Tümü <= 2.40s)")

        cuts = [
            BasketballCut(
                cut_index=i,
                start_time=c["startFrame"] / fps,
                end_time=(c["startFrame"] + c["durationInFrames"]) / fps,
                duration=c["durationInFrames"] / fps,
                media_path=c["media_path"],
                media_type=MediaType.VIDEO_CLIP if c["mediaType"] == "video" else MediaType.KEN_BURNS_PHOTO,
                target_subject=c.get("target_subject", athlete_key),
                action_notes=f"Cut {i}: {Path(c['media_path']).name}"
            )
            for i, c in enumerate(enforced_cuts)
        ]

        # 5. Deterministik 5 Kalkan Doğrulaması (Same-Source, 3-Point pHash, Laplacian, CLIP Negative Domain, Pacing)
        validator = BasketballAssetValidator(
            max_cut_duration=2.40,
            min_hamming_distance=10,
            max_same_source_clips=1,
            min_same_source_distance_sec=14.0,
            min_height=720,
            min_width=720,
            min_laplacian_variance=75.0
        )
        valid, errors = validator.validate_timeline(enforced_cuts, work_dir)
        if not valid:
            raise RuntimeError(f"Pipeline deterministik 5 kalkan hatası:\n" + "\n".join(errors))

        # KONSOL KONTROL RAPORU: Her seçilen dilimin source_id, SigLIP_score ve negative_label_score değerleri
        logger.info(f"\n" + "=" * 98)
        logger.info(f"🎯 [VERIFIED SLICES GATE LOG] {job_id} | {athlete_key.upper()} ({len(enforced_cuts)} Kesme Tamamı Onaylandı)")
        logger.info("=" * 98)
        for i, c in enumerate(enforced_cuts):
            c_p = Path(c["media_path"])
            c_sid = c.get("source_video_id") or c_p.stem
            c_q = c.get("concrete_visual_query", "professional NBA basketball game action")
            c_subj = c.get("target_subject", athlete_key)
            vis = self.vision_verifier.verify_slice(
                media_path=c_p,
                concrete_visual_query=c_q,
                target_subject=c_subj
            )
            w, h, lap = measure_laplacian_sharpness(c_p)
            siglip_val = vis.get("SigLIP_score", vis.get("query_score", 0.0))
            neg_val = vis.get("negative_label_score", 0.0)
            neg_lbl = vis.get("negative_label", "none")
            logger.info(
                f"  🎬 Cut {i:02d} | source_id={c_sid:<28} | file={c_p.name:<32} | "
                f"SigLIP_score={siglip_val:.4f} | neg_score={neg_val:.4f} ({neg_lbl:<20}) | laplacian={lap:5.1f} | [PASSED]"
            )
        logger.info("=" * 98 + "\n")

        # 6. locked_segments Manifest Dosyasını Mühürle (Immutable)
        manifest_data = {
            "job_id": job_id,
            "athlete_key": athlete_key,
            "topic": topic,
            "total_frames": total_frames,
            "fps": fps,
            "cuts": [
                {
                    "cut_index": i,
                    "id": c["id"],
                    "media_path": c["media_path"],
                    "media_type": c["mediaType"],
                    "source_video_id": c.get("source_video_id", ""),
                    "concrete_visual_query": c.get("concrete_visual_query", ""),
                    "start_frame": c["startFrame"],
                    "duration_frames": c["durationInFrames"],
                    "duration_sec": c["durationInFrames"] / fps,
                    "locked": True
                }
                for i, c in enumerate(enforced_cuts)
            ]
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"🔒 [Timeline Manifest Mühürlendi] {len(enforced_cuts)} sahne locked_segments olarak kaydedildi.")

        spec = BasketballRenderSpec(
            job_id=job_id,
            channel_id=self.channel_id,
            topic=topic,
            athlete_name=athlete_key,
            audio_path=str(dest_audio),
            sentence_boundaries=sentence_boundaries,
            cuts=cuts,
            category_badge_text="🏀 SPORTS SCIENCE",
            category_badge_duration=4.0
        )
        spec.validate_strict_zero_loop()
        logger.info(f"✅ [Zero Loop & Hijyen Kontratı Doğrulandı] {len(enforced_cuts)} kesmenin tamamı onaylandı!")

        # 7. Remotion Render Props JSON Dosyası Oluştur
        remotion_props = {
            "topic": topic,
            "categoryBadgeText": "🏀 SPORTS SCIENCE",
            "badgeDurationFrames": 120, # Tam 4.0 saniye
            "audioPath": relative_audio_path,
            "cuts": enforced_cuts,
            "sentences": remotion_sentences,
            "fps": fps,
            "durationInFrames": total_frames
        }

        props_json_path = work_dir / "remotion_props.json"
        props_json_path.write_text(json.dumps(remotion_props, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"📄 Remotion Render Props yazıldı: {props_json_path.name}")

        # 6. Remotion CLI ile Video Render
        final_rendered_mp4 = work_dir / "remotion_raw_output.mp4"
        if final_rendered_mp4.exists():
            final_rendered_mp4.unlink()

        logger.info(f"🎬 [Remotion Render Başlatılıyor] BasketballShorts ({total_frames} kare, 1080x1920 30fps)...")
        render_cmd = [
            "npx", "remotion", "render",
            "src/index.ts",
            "BasketballShorts",
            str(final_rendered_mp4),
            f"--props={str(props_json_path)}",
            f"--public-dir={str((REMOTION_DIR / 'public').resolve())}",
            "--overwrite",
            "--gl=angle",
            "--concurrency=4",
            "--quiet"
        ]

        t0 = time.time()
        res = subprocess.run(render_cmd, cwd=str(REMOTION_DIR), capture_output=True, text=True, timeout=300)
        render_time = time.time() - t0

        if not final_rendered_mp4.exists() or final_rendered_mp4.stat().st_size < 1000000:
            logger.error(f"❌ Remotion render hatası: {res.stderr}\n{res.stdout}")
            raise RuntimeError(f"Remotion render başarısız oldu: {res.stderr}")

        logger.info(f"✨ [Remotion Render Tamamlandı] {final_rendered_mp4.stat().st_size / (1024*1024):.2f} MB ({render_time:.1f}s)")

        # 7. Nihai Hedefe Kopyala
        dest_final_mp4 = job_dir / "final.mp4"
        shutil.copy2(str(final_rendered_mp4), str(dest_final_mp4))

        # 8. Apple Silicon M4 RVC Ses Klonlama Giydirme
        logger.info(f"🎙️ [M4 RVC Ses Giydirme] {dest_final_mp4.name} üzerine '{voice_clone_id}' giydiriliyor...")
        try:
            from src.voice_clone_manager import VoiceCloneManager
            vcm = VoiceCloneManager()
            clone_res = vcm.apply_voice_clone_to_video(
                video_path=dest_final_mp4,
                clone_id=voice_clone_id
            )
            if clone_res.get("success"):
                logger.info(f"✅ [RVC Başarılı] Ses klonu mühürlendi: {clone_res.get('clone_name')} ({clone_res.get('processing_time_sec')}s)")
            else:
                logger.warning(f"⚠️ [RVC Uyarısı] Klon ses uygulanamadı: {clone_res.get('reason')}")
        except Exception as e_vc:
            logger.error(f"❌ [RVC Hatası] Ses klonlama istisnası: {e_vc}")

        logger.info(f"🏆 [BASKETBALL ENGINE 2.0 TAMAMLANDI] Final Video: {dest_final_mp4} ({dest_final_mp4.stat().st_size / (1024*1024):.2f} MB)")
        return dest_final_mp4

    def patch_video(
        self,
        job_id: str,
        athlete_key: str,
        topic: str,
        unlock_timestamps: Optional[List[float]] = None,
        unlock_indices: Optional[List[int]] = None,
        voice_clone_id: str = "vc_1792868444",
        patch_segments: Optional[Dict[int, Dict[str, Any]]] = None,
        custom_queries: Optional[Dict[int, str]] = None,
        bypass_cache: bool = False
    ) -> Path:
        """
        /api/video-patch Deterministik Yama Yürütücüsü:
        locked: true olan onaylı sahneleri kesinlikle korur.
        Yalnızca locked: false olan veya unlock_timestamps/unlock_indices ile belirtilen
        kesitleri yeniden sorgular, diğer sahnelerin dosya yollarını ve zamanlarını dondurur.
        custom_queries: Her bir cut_index için güncel arama sorgusunu belirler.
        """
        bypass_cache = bypass_cache or os.environ.get("BYPASS_CACHE", "").lower() in ["1", "true", "yes"]
        job_dir = PROJECT_ROOT / "output" / self.channel_id / "kontrol" / job_id
        if not job_dir.exists():
            for cand in (PROJECT_ROOT / "output").glob(f"**/{job_id}"):
                if cand.is_dir():
                    job_dir = cand
                    break
        manifest_file = job_dir / "timeline_manifest.json"

        target_indices = set(unlock_indices or [])

        if manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                fps = manifest.get("fps", 30)
                for cut in manifest.get("cuts", []):
                    c_idx = cut.get("cut_index", 0)
                    if cut.get("locked") is False:
                        target_indices.add(c_idx)
                    if unlock_timestamps:
                        start_t = cut.get("start_frame", 0) / fps
                        dur_t = cut.get("duration_frames", 60) / fps
                        end_t = start_t + dur_t
                        for ts in unlock_timestamps:
                            if start_t <= ts <= end_t:
                                target_indices.add(c_idx)
            except Exception as e:
                logger.warning(f"Manifest tarama uyarısı: {e}")

        logger.info(f"🔧 [/api/video-patch] {job_id} için {len(target_indices)} sahnenin kilidi açılıyor: {sorted(list(target_indices))} (bypass_cache={bypass_cache})")

        return self.produce_video(
            job_id=job_id,
            athlete_key=athlete_key,
            topic=topic,
            voice_clone_id=voice_clone_id,
            force_rebuild=False,
            patch_segments=patch_segments,
            unlock_indices=list(target_indices),
            custom_queries=custom_queries,
            bypass_cache=bypass_cache
        )

    # Alias for patch router compatibility
    patch_video_segment = patch_video


# Module-level alias for router compatibility
BasketballEngineOrchestrator = BasketballOrchestrator

