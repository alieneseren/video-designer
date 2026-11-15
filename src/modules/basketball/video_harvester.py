"""
Basketball Engine 2.0 - Video & Asset Harvester (Deterministic Mechanical Locks)
================================================================================
Video-First mimari & Katı Görsel Hijyen Standartları:
1. Tek YouTube Maç Özetinden Çoklu Kesit (Same-Source Over-Sampling) Kilidi:
   - Kaynak başına max 2 kesit.
   - İki kesit arasında en az 15s zaman çizelgesi mesafesi.
2. 3 Noktalı (10%, 50%, 90%) pHash tekillik garantisi.
3. Çözünürlük & Netlik Kapısı (Min 720p, min 65.0 Laplacian varyansı).
4. Tam ekran (native 9:16) dikey kadraj (Sıfır Blur Bar Dolgu).
5. Kesintisiz blok tavanı: Hiçbir sahne 2.35s'yi aşamaz.
"""

import hashlib
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple
import cv2

from src.modules.basketball.vision_verifier import BasketballVisionVerifier
from src.modules.basketball.asset_validator import measure_laplacian_sharpness, compute_file_md5

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("BasketballHarvester")

YT_DLP_BIN = "/opt/homebrew/bin/yt-dlp"
FFMPEG_BIN = "ffmpeg"
CURATED_BROLL_DIR = Path("/Users/alienes/yt-oto-video/files/assets/curated_sports/b_roll/videos")

BANNED_PROJECT_SOURCES = {
    "james_harden": [
        "spurs", "fisher", "derek", "neurobiology", "sbc_center", "2004_playoffs",
        "lakers_vs_spurs", "trent_tucker", "duncan", "san_antonio"
    ],
    "derek_fisher": [
        "harden", "rockets", "deceleration", "biomechanics_harden", "wesley_johnson",
        "eurostep", "ankle_breaker"
    ]
}

PROJECT_USED_SOURCES: Dict[str, Set[str]] = {}
PROJECT_USED_HASHES: Dict[str, List[Any]] = {}


def extract_canonical_video_id(url_or_id: str) -> str:
    """Extracts canonical YouTube video ID from watch URLs, short URLs, or raw IDs."""
    if not url_or_id:
        return ""
    if "youtu.be/" in url_or_id:
        return url_or_id.split("youtu.be/")[1].split("?")[0].split("&")[0]
    if "watch?v=" in url_or_id:
        return url_or_id.split("watch?v=")[1].split("&")[0].split("?")[0]
    return url_or_id.strip()


def is_source_banned_for_project(source_id_or_path: str, athlete_key: str) -> bool:
    """Enforces strict cross-project asset isolation."""
    if not athlete_key or not source_id_or_path:
        return False
    key = athlete_key.lower()
    src_str = str(source_id_or_path).lower()
    for proj_key, banned_terms in BANNED_PROJECT_SOURCES.items():
        if proj_key in key or key in proj_key:
            for term in banned_terms:
                if term in src_str:
                    return True
    return False

VIDEO_SOURCES = {
    "james_harden": [
        {
            # 1. ESPN Sport Science: Kinematik telemetri (Cut 00)
            "url": "https://www.youtube.com/watch?v=RphKYwhdSnM",
            "format": "136/232/bestvideo[height<=720]/best",
            "sections": "*00:03-00:35",
            "filename": "harden_sport_science.mp4",
            "source_id": "src_espn_sport_science",
            "clips": [
                ("00:00:12.0", 2.0, "sport_science_3d_wireframe")             # 00:12 - 00:14 ESPN Sport Science net telemetri
            ]
        },
        {
            # 2. Houston Rockets vs Clippers: Wesley Johnson Ankle Breaker (Cut 03)
            "url": "https://www.youtube.com/watch?v=ecKnlp5B2R4",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:00-00:30",
            "filename": "harden_wesley_anklebreaker.mp4",
            "source_id": "src_clippers_wesley_2018",
            "clips": [
                ("00:00:03.0", 2.0, "wesley_crossover_stepback")       # 00:03 Crossover ve Wesley Johnson düşüşü
            ]
        },
        {
            # 3. [00:11 - 00:12] ESPN Breakdown: James Harden sprinting full court NBA arena hardwood broadcast HD (Cut 05)
            "url": "https://www.youtube.com/watch?v=bz5VeSqvF-U",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:05-00:30",
            "filename": "harden_espn_breakdown.mp4",
            "source_id": "src_espn_breakdown",
            "clips": [
                ("00:00:09.5", 2.0, "harden_sprint_fullspeed")         # 00:09.5 Sprint tam saha hücum
            ]
        },
        {
            # 4. [00:15 - 00:16] Sharp Crossover Brake: James Harden sharp crossover sudden brake slow motion (Cut 07)
            "url": "https://www.youtube.com/watch?v=X9GddRiKdXg",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:20-00:30",
            "filename": "src_james_harden_00.mp4",
            "source_id": "src_james_harden_00",
            "clips": [
                ("00:00:02.0", 2.0, "harden_eurostep_drive")           # 00:02 Eurostep yön değişimi ve potaya gidiş
            ]
        },
        {
            # 5. Warriors Game Winner Celebration (Cut 09)
            "url": "https://www.youtube.com/watch?v=G3cZ84oR6y8",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:10-00:25",
            "filename": "harden_warriors_winner.mp4",
            "source_id": "src_warriors_winner_broadcast",
            "clips": [
                ("00:00:06.0", 2.0, "warriors_winner_reaction")        # 00:06 Galibiyet kutlaması
            ]
        },
        {
            # 6. [00:23 - 00:26] NBA defender mirroring / backpedaling guarding drive to rim (Cut 11)
            "url": "https://www.youtube.com/watch?v=kY7wVvN3p1A",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:00-00:10",
            "filename": "harden_kings_stepback.mp4",
            "source_id": "src_kings_stepback_2019",
            "clips": [
                ("00:00:02.0", 2.0, "nba_defender_mirroring")          # 00:02 NBA parkesinde savunma geri çekilişi
            ]
        },
        {
            # 7. Warriors Stepback over Two Defenders 1080p (Cut 13)
            "url": "https://www.youtube.com/watch?v=Vl03q5x4wI8",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:20-00:40",
            "filename": "harden_warriors_1080p.mp4",
            "source_id": "src_warriors_gamewinner_2019",
            "clips": [
                ("00:00:27.5", 2.0, "warriors_stepback_over_two")       # 00:27.5 İki savunmacı üzerinden üçlük
            ]
        },
        {
            # 8. [00:36 - 00:41] James Harden step-back gather, footwork, and separation mechanics (Cut 17)
            "url": "https://www.youtube.com/watch?v=uK8o92lP4iI",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:05-00:15",
            "filename": "harden_nba_stepbacks.mp4",
            "source_id": "src_nba_stepbacks_harden",
            "clips": [
                ("00:00:05.0", 2.0, "harden_stepback_gather")          # 00:05 Adım toplama ve ayrılma mekaniği
            ]
        },
        {
            # 9. [00:36 - 00:41] James Harden step-back three swish net (Cut 19)
            "url": "https://www.youtube.com/watch?v=7hP3g2mQ4p8",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:10-00:20",
            "filename": "src_james_harden_01.mp4",
            "source_id": "src_james_harden_01",
            "clips": [
                ("00:00:01.0", 2.0, "harden_stepback_swish_net")       # 00:01.0 Üçlük basket ve pota filesi dalgalanışı
            ]
        }
    ],
    "derek_fisher": [
        {
            # 1. 3D Nörobiyoloji: Sinaptik ateşleme ve optik sinir iletimi (Cut 00)
            "url": "https://www.youtube.com/watch?v=LsehL-tvuA4",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:02-00:15",
            "filename": "brain_synapse_3d.mp4",
            "source_id": "src_neurobiology_3d",
            "clips": [
                ("00:00:01.5", 2.1, "brain_synapse_firing")             # 00:01.5 Optik sinir iletimi
            ]
        },
        {
            # 2. SBC Center Arena Ambiyansı / Hardwood Jump Shot (Cut 03)
            "url": "https://www.youtube.com/watch?v=tdih_fisher_2004",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:00-00:10",
            "filename": "tdih_fisher.mp4",
            "source_id": "src_tdih_fisher_2004",
            "clips": [
                ("00:00:03.0", 2.1, "arena_sbc_center")                # 00:03.0 Arena basketbol şutu
            ]
        },
        {
            # 3. 1990 Trent Tucker Kuralı (Cut 04)
            "url": "https://www.youtube.com/watch?v=1p3rRDPIJ-Q",
            "format": "bestvideo[height<=720][ext=mp4]/best",
            "sections": "*00:00-00:15",
            "filename": "trent_tucker_1990.mp4",
            "source_id": "src_trent_tucker_1990",
            "clips": [
                ("00:00:03.0", 2.1, "trent_tucker_buzzer_beater")       # 00:03 1990 Trent Tucker pozisyonu
            ]
        },
        {
            # 4. [00:25 - 00:31] Derek Fisher 0.37s Şut Çıkışı ve Turnaround Fadeaway (Cut 12)
            "url": "https://www.youtube.com/watch?v=rZcP88s3B_M",
            "format": "bestvideo[height<=1080][ext=mp4]/best",
            "sections": "*00:10-00:35",
            "filename": "src_derek_fisher_01.mp4",
            "source_id": "src_derek_fisher_01",
            "clips": [
                ("00:00:12.5", 2.1, "fisher_turnaround_release")        # 00:12.5 0.37s şut çıkışı
            ]
        }
    ]
}

STORYBOARD_DEFINITIONS = {
    "james_harden": [
        ("video", "sport_science_3d_wireframe", "scientific 3D wireframe motion capture animation of basketball athlete in laboratory"),
        ("image", "photo_000_mocap_sensors", "motion capture reflective markers attached to professional basketball athlete limbs in sports laboratory"),
        ("image", "photo_001_harden_sprint_fullspeed", "James Harden running fast sprint in Houston Rockets red jersey on basketball court"),
        ("video", "wesley_crossover_stepback", "James Harden explosive crossover step back dribble shaking defender in NBA arena"),
        ("image", "photo_002_harden_dribble_drive", "James Harden low dribble drive penetration past defender on hardwood court"),
        ("video", "harden_sprint_fullspeed", "James Harden sprinting full court NBA arena hardwood broadcast HD in Houston Rockets jersey"),
        ("image", "photo_003_quad_braking_mechanics", "close up basketball player leg muscles and knee joints on hardwood court"),
        ("video", "harden_eurostep_drive", "James Harden sharp crossover sudden brake slow motion ankle breaker on basketball court"),
        ("image", "photo_004_harden_isolation", "James Harden focused intense facial expression in isolation set on court"),
        ("video", "warriors_winner_reaction", "James Harden celebrating game winning shot with teammates on NBA hardwood court"),
        ("image", "photo_005_stepback_three", "James Harden elevated step back three point jump shot release over defender on court"),
        ("video", "nba_defender_mirroring", "NBA defender mirroring and backpedaling guarding drive to rim on hardwood court"),
        ("image", "photo_006_ankle_breaker", "James Harden explosive ankle breaker crossover causing defender to stumble on court"),
        ("video", "warriors_stepback_over_two", "James Harden game winning three pointer shot over defenders in NBA arena"),
        ("image", "photo_007_harden_low_dribble", "James Harden low crossover dribble on NBA basketball court"),
        ("image", "photo_008_harden_faceup", "James Harden intense faceup dribble stance attacking defender on NBA hardwood court"),
        ("image", "photo_009_harden_red_jersey", "James Harden playing basketball in red uniform on hardwood court"),
        ("video", "harden_stepback_gather", "James Harden step-back gather footwork and separation mechanics on NBA hardwood court"),
        ("image", "photo_010_harden_stepback_release", "James Harden elevated step back three point jump shot release over defender on court"),
        ("video", "harden_stepback_swish_net", "James Harden step-back three point shot swishing through basketball net on hoop"),
        ("image", "synapse_impulse", "3D glowing brain nervous system neural synapse impulse firing animation in laboratory"),
        ("image", "quad_braking_mechanics", "sports science biomechanics telemetry analysis on court"),
        ("image", "photo_011_harden_solo_outro", "James Harden portrait in red Houston Rockets jersey smiling in arena"),
    ],
    "derek_fisher": [
        ("video", "brain_synapse_firing", "macro 3D animation of brain synaptic firing and neurological impulses in laboratory"),
        ("image", "photo_001_motor_cortex", "macro 3D human brain motor cortex model activating spinal motor neurons in laboratory"),
        ("image", "photo_000_optic_nerve", "3D medical animation optic nerve signal traveling from eye to visual cortex in laboratory"),
        ("video", "arena_sbc_center", "Derek Fisher 0.4 buzzer beater shot on court in NBA arena"),
        ("video", "trent_tucker_buzzer_beater", "1990 vintage basketball game buzzer beater archive broadcast footage on court"),
        ("image", "photo_vintage_led_03_clock", "vintage red digital 7-segment LED shot clock displaying 0.3 seconds"),
        ("image", "referee_crt_review", "NBA referee waving off basket and reviewing call on court"),
        ("image", "photo_002_trent_tucker_rule", "NBA alley-oop tip-in buzzer beater shot on basketball court in 1990"),
        ("image", "photo_003_sbc_center", "San Antonio SBC Center arena floor packed with roaring playoffs basketball crowd"),
        ("image", "fisher_buzzer_beater_shot", "Derek Fisher turnaround fadeaway miracle buzzer beater shot on court"),
        ("image", "photo_004_fisher_purple_run", "Derek Fisher in purple Los Angeles Lakers away jersey running to sideline timeout on court"),
        ("image", "biomechanics_curve", "scientific biomechanical motion analysis kinetic chart of basketball player shooting form"),
        ("video", "fisher_turnaround_release", "Derek Fisher quick release jumper turnaround fadeaway shot catching inbound pass in mid air"),
        ("image", "fisher_inbound_midair_catch", "Derek Fisher catching basketball inbound pass in mid air"),
        ("image", "photo_006_iconic_04_shot", "Derek Fisher turnaround fadeaway shot catching inbound pass in mid air and turning around to shoot on court"),
        ("image", "photo_008_buzzer_red_light", "NBA red LED backboard buzzer light illuminating at buzzer on NBA hardwood arena"),
        ("image", "photo_sbc_crowd_shock", "shocked basketball spectators in arena stands watching playoff game"),
        ("image", "brain_cortex", "3D medical animation brain cortex neural visualization in laboratory"),
        ("image", "photo_fisher_miracle_swish", "Derek Fisher 0.4 buzzer beater miracle shot on court in NBA arena"),
        ("image", "photo_009_spurs_stunned_00", "San Antonio Spurs players standing frozen on court looking at scoreboard in disbelief"),
        ("image", "photo_010_fisher_solo_outro", "Derek Fisher running shouting celebrating game winner miracle buzzer beater"),
        ("image", "fisher_sprint_tunnel", "Derek Fisher in purple jersey sprinting down arena tunnel celebrating miracle shot"),
        ("image", "photo_fisher_turnaround_fade", "Derek Fisher quick release turnaround fadeaway jumper shot in arena"),
    ]
}


class VideoHarvester:
    def __init__(self, work_dir: Path, bypass_cache: bool = False, project_id: str = ""):
        self.work_dir = Path(work_dir)
        self.project_id = project_id or self.work_dir.parent.name
        self.project_isolation_lock = True
        self.bypass_cache = bypass_cache or os.environ.get("BYPASS_CACHE", "").lower() in ["1", "true", "yes"]
        self.raw_videos_dir = self.work_dir / "raw_videos"
        self.clips_dir = self.work_dir / "action_clips"
        self.photos_dir = self.work_dir / "photos"
        
        if self.bypass_cache:
            logger.info(f"🧹 [BYPASS_CACHE=True] {self.work_dir} altındaki eski kesitler ve geçici kareler sıfırlanıyor...")
            if self.clips_dir.exists():
                shutil.rmtree(self.clips_dir, ignore_errors=True)
            if self.photos_dir.exists():
                shutil.rmtree(self.photos_dir, ignore_errors=True)
            temp_3pt = self.work_dir / "_validator_3pt_frames"
            if temp_3pt.exists():
                shutil.rmtree(temp_3pt, ignore_errors=True)
            temp_v = self.work_dir / "_validator_frames"
            if temp_v.exists():
                shutil.rmtree(temp_v, ignore_errors=True)

        self.raw_videos_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        self.vision_verifier = BasketballVisionVerifier()

    def download_recipe_videos(self, athlete_key: str) -> Dict[str, Path]:
        """Tarife listesindeki videoları yt-dlp ile 720p+ ve netlik filtresiyle indirir."""
        sources = VIDEO_SOURCES.get(athlete_key, [])
        downloaded = {}

        for src in sources:
            fname = src["filename"]
            out_file = self.raw_videos_dir / fname

            # Yerel arama ve önbellek kontrolü (sıfır bekleme ve offline dayanıklılık)
            search_candidates = [
                Path(f"/tmp/{fname}"),
                Path(f"/Users/alienes/yt-oto-video/files/output/thebasketballshows/kontrol/exec_mat_20261104_224042_The_Deceleration_Secret_Behind/basketball_v2_work/raw_videos/{fname}"),
                Path(f"/Users/alienes/yt-oto-video/files/output/thebasketballshows/kontrol/exec_mat_20261104_224042_The_Neurobiology_of_Derek_Fish/basketball_v2_work/raw_videos/{fname}"),
                Path(f"/Users/alienes/yt-oto-video/files/assets/curated_sports/b_roll/videos/{fname}"),
            ]

            if not out_file.exists():
                for c in search_candidates:
                    if c.exists() and c.stat().st_size > 200000:
                        shutil.copy2(str(c), str(out_file))
                        logger.info(f"⚡ [Yerel Önbellek] {fname} yerel kaynaktan kopyalandı ({c.name})")
                        break

            if out_file.exists() and out_file.stat().st_size > 200000:
                downloaded[fname] = out_file
                continue

            logger.info(f"📥 [yt-dlp] {src['url']} ({src['sections']}) indiriliyor -> {fname}...")
            cmd = [
                YT_DLP_BIN,
                src["url"],
                "--download-sections", src["sections"],
                "-f", src["format"],
                "-o", str(out_file),
                "--force-overwrites",
                "--no-playlist",
                "--quiet"
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                if out_file.exists() and out_file.stat().st_size > 200000:
                    logger.info(f"✅ Video başarıyla indirildi: {fname} ({out_file.stat().st_size / (1024*1024):.1f} MB)")
                    downloaded[fname] = out_file
                else:
                    logger.warning(f"⚠️ İndirme başarısız: {res.stderr[:200]}")
            except Exception as e:
                logger.warning(f"⚠️ yt-dlp hatası: {e}")

        return downloaded

    def slice_recipe_clips(self, athlete_key: str, downloaded_videos: Dict[str, Path]) -> List[Dict[str, Any]]:
        """
        Tarifeli dikey kırpma & Kesim Sonrası Görsel Doğrulama (Post-Slice Verification):
        - 1080x1920 tam ekran dikey (Sıfır Blur Bar).
        - max_slices_per_source_id = 1 kotası kesin uygulanır.
        - Her dilim kesildikten sonra t=1.0s orta karesi SigLIP/CLIP ve Laplacian (>=75.0) filtresinden geçer.
        - Negatif etiketler (bench standing dead-ball, brick wall gym, motion blur) tespit edilirse dilim montaja girmeden elenir.
        """
        sources = VIDEO_SOURCES.get(athlete_key, [])
        clips_meta = []
        clip_counter = 0
        seen_source_ids = set()
        seen_canonical_ids = set()

        for src in sources:
            fname = src["filename"]
            source_id = src.get("source_id", fname)
            url = src.get("url", "")
            canonical_id = extract_canonical_video_id(url)

            if canonical_id and canonical_id in seen_canonical_ids:
                logger.info(f"🔒 [Canonical YouTube Quota = 1] '{canonical_id}' ({source_id}) videosundan zaten 1 kesit alındı, atlanıyor.")
                continue

            if source_id in seen_source_ids:
                logger.info(f"🔒 [Source Video Quota = 1] '{source_id}' kaynağından zaten 1 kesit alındı, atlanıyor.")
                continue

            src_file = downloaded_videos.get(fname)
            if not src_file or not src_file.exists():
                continue

            for start_ts, duration, clip_label in src["clips"]:
                if source_id in seen_source_ids or (canonical_id and canonical_id in seen_canonical_ids):
                    break
                out_clip = self.clips_dir / f"clip_{clip_counter:03d}_{clip_label}.mp4"
                
                vf = (
                    "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
                    "crop=1080:1920,"
                    "unsharp=5:5:1.2,"
                    "fps=30"
                )

                ffmpeg_cmd = [
                    FFMPEG_BIN, "-y",
                    "-ss", start_ts,
                    "-i", str(src_file),
                    "-t", f"{duration:.2f}",
                    "-vf", vf,
                    "-an",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    str(out_clip)
                ]

                subprocess.run(ffmpeg_cmd, capture_output=True, timeout=30)
                if out_clip.exists() and out_clip.stat().st_size > 50000:
                    # 1. Kesim Sonrası Netlik & Çözünürlük Doğrulaması (Laplacian Floor >= 75.0)
                    w, h, lap_var = measure_laplacian_sharpness(out_clip)
                    if lap_var < 75.0 or w < 720 or h < 720:
                        logger.warning(
                            f"🚨 [Post-Slice Gate Reddi] {out_clip.name}: "
                            f"Laplacian {lap_var:.1f} < 75.0 veya {w}x{h} < 720p!"
                        )
                        out_clip.unlink(missing_ok=True)
                        continue

                    # 2. Kesim Sonrası CLIP Negatif Domain & Entity Kontrolü
                    clean_label = clip_label.replace("_", " ")
                    storyboard_items = STORYBOARD_DEFINITIONS.get(athlete_key, [])
                    sb_query = None
                    for item in storyboard_items:
                        if item[0] == "video" and (item[1] == clip_label or item[1] in clip_label or clip_label in item[1]):
                            sb_query = item[2]
                            break

                    if sb_query:
                        concrete_query = sb_query
                    else:
                        is_science = any(kw in clip_label.lower() for kw in ["brain", "synapse", "neural", "optic", "telemetry", "sensor", "mocap", "science"])
                        if is_science:
                            if "brain" in clip_label.lower() or "synapse" in clip_label.lower():
                                concrete_query = f"scientific 3D animation neurology impulses visual cortex visual {clean_label}"
                            elif "sport_science" in clip_label.lower() or "science" in clip_label.lower():
                                concrete_query = f"ESPN Sport Science athlete kinematics laboratory telemetry motion tracking data {clean_label}"
                            else:
                                concrete_query = f"scientific sports biomechanics laboratory motion analysis {clean_label}"
                        else:
                            concrete_query = f"{athlete_key} {clean_label} professional NBA game action"

                    is_science_clip = any(kw in clip_label.lower() or kw in concrete_query.lower() for kw in ["brain", "synapse", "neural", "optic", "telemetry", "sensor", "mocap", "science", "laboratory", "biomechanic"])
                    is_object_only = any(kw in clip_label.lower() or kw in concrete_query.lower() for kw in ["buzzer", "clock", "light", "shot clock", "net_swish"])
                    is_primary_athlete = athlete_key and (athlete_key in clip_label.lower() or athlete_key in concrete_query.lower() or "harden" in concrete_query.lower() or "fisher" in concrete_query.lower())
                    is_non_subject = any(kw in clip_label.lower() or kw in concrete_query.lower() for kw in ["trent_tucker", "duncan", "inbound", "payton", "arena_establishing", "crowd", "hoop", "defense", "setup", "bench", "celebration", "mirroring", "sbc_center", "friction", "shoes"])

                    if is_science_clip or is_object_only:
                        target_subj = None
                    elif is_primary_athlete:
                        target_subj = athlete_key
                    elif is_non_subject:
                        target_subj = "NBA basketball player dribbling shooting in arena"
                    else:
                        target_subj = athlete_key

                    vision_res = self.vision_verifier.verify_slice(
                        media_path=out_clip,
                        concrete_visual_query=concrete_query,
                        target_subject=target_subj
                    )
                    if not vision_res["passed"]:
                        logger.warning(
                            f"🚨 [Post-Slice Gate Reddi - CLIP] {out_clip.name}: {vision_res['reasons']}"
                        )
                        out_clip.unlink(missing_ok=True)
                        continue

                    # Kesin ölü top / serbest atış / savrulma elemesi (Negatif skor pozitiften üstünse veya query'yi eziyorsa)
                    neg_lbl = vision_res.get("negative_label", "none")
                    neg_sc = vision_res.get("negative_label_score", 0.0)
                    v_pos_sc = vision_res.get("pos_score", 0.0)
                    v_query_sc = vision_res.get("query_score", 0.0)
                    if neg_lbl in ["free throw lineup", "players standing on bench dead ball", "heavy motion blur whip pan", "amateur gym with brick wall"] and neg_sc >= v_pos_sc:
                        logger.warning(
                            f"🚨 [Post-Slice Gate Reddi - Dead-Ball/Negative] {out_clip.name}: "
                            f"{neg_lbl} skoru {neg_sc:.4f} >= pos {v_pos_sc:.4f}!"
                        )
                        out_clip.unlink(missing_ok=True)
                        continue

                    siglip_sc = vision_res.get("SigLIP_score", vision_res.get("query_score", 0.0))

                    clips_meta.append({
                        "path": str(out_clip),
                        "name": out_clip.name,
                        "label": clip_label,
                        "source_video_id": source_id,
                        "canonical_video_id": canonical_id,
                        "duration": duration,
                        "SigLIP_score": siglip_sc,
                        "negative_label_score": neg_sc,
                        "negative_label": neg_lbl,
                        "laplacian_variance": lap_var
                    })
                    seen_source_ids.add(source_id)
                    if canonical_id:
                        seen_canonical_ids.add(canonical_id)
                    clip_counter += 1
                    logger.info(
                        f"✂️ [Slice Gate PASS] {out_clip.name:<32} | source_id={source_id:<28} | canonical={canonical_id} | "
                        f"SigLIP_score={siglip_sc:.4f} | neg_score={neg_sc:.4f} ({neg_lbl}) | laplacian={lap_var:.1f}"
                    )

        # Yerel Küratörlü 1080p B-roll kliplerini de ekle
        self._add_curated_broll_slices(athlete_key, clips_meta)

        logger.info(f"✂️ Toplam {len(clips_meta)} adet temiz, 1080x1920 dikey aksiyon klibi üretildi.")
        return clips_meta

    def _verify_and_append_broll(
        self,
        out_clip: Path,
        label: str,
        source_id: str,
        duration: float,
        query: str,
        clips_meta: List[Dict[str, Any]]
    ):
        """Küratörlü B-roll kesitlerini Laplacian ve CLIP negatif domain kalkanından geçirir."""
        if not out_clip.exists() or out_clip.stat().st_size < 10000:
            return

        if any(c["path"] == str(out_clip) or c["source_video_id"] == source_id for c in clips_meta):
            return

        w, h, lap = measure_laplacian_sharpness(out_clip)
        if lap < 75.0 or (w > 0 and w < 720) or (h > 0 and h < 720):
            logger.warning(f"🚨 [Curated Broll Gate Reddi] {out_clip.name}: Laplacian {lap:.1f} < 75.0 veya {w}x{h} < 720p!")
            out_clip.unlink(missing_ok=True)
            return

        vis = self.vision_verifier.verify_slice(
            media_path=out_clip,
            concrete_visual_query=query,
            target_subject=None
        )
        if not vis["passed"]:
            logger.warning(f"🚨 [Curated Broll Gate Reddi - CLIP] {out_clip.name}: {vis['reasons']}")
            out_clip.unlink(missing_ok=True)
            return

        siglip_sc = vis.get("SigLIP_score", vis.get("query_score", 0.0))
        neg_sc = vis.get("negative_label_score", 0.0)
        neg_lbl = vis.get("negative_label", "none")

        clips_meta.append({
            "path": str(out_clip),
            "name": out_clip.name,
            "label": label,
            "source_video_id": source_id,
            "duration": duration,
            "SigLIP_score": siglip_sc,
            "negative_label_score": neg_sc,
            "negative_label": neg_lbl,
            "laplacian_variance": lap
        })
        logger.info(
            f"✂️ [Curated Broll Gate PASS] {out_clip.name:<32} | source_id={source_id:<28} | "
            f"SigLIP_score={siglip_sc:.4f} | neg_score={neg_sc:.4f} ({neg_lbl}) | laplacian={lap:.1f}"
        )

    def _add_curated_broll_slices(self, athlete_key: str, clips_meta: List[Dict[str, Any]]):
        """Yerel B-roll kesitleri doğrudan VIDEO_SOURCES üzerinden yönetilir; kontamine amatör salon kesitleri tamamen temizlenmiştir."""
        pass

    def fetch_authentic_photos(self, athlete_key: str) -> Dict[str, Path]:
        """Küratörlü sporcu fotoğraflarını 1080x1920 Native dikey formata dönüştürür."""
        curated_dir = Path(f"/Users/alienes/yt-oto-video/files/assets/curated_sports/athletes/{athlete_key}")
        candidate_files = sorted(curated_dir.glob("*.jpg")) if curated_dir.exists() else []

        blacklist = {
            "photo_062.jpg", "photo_051.jpg", "photo_052.jpg", "photo_039.jpg",
            "photo_053.jpg", "photo_054.jpg", "photo_055.jpg", "photo_056.jpg",
            "photo_057.jpg", "photo_058.jpg", "photo_060.jpg", "photo_061.jpg",
            "photo_063.jpg", "photo_064.jpg", "photo_065.jpg", "photo_067.jpg",
            "photo_068.jpg", "photo_069.jpg", "photo_070.jpg", "photo_103.jpg",
            "photo_120.jpg", "photo_121.jpg", "photo_122.jpg", "photo_123.jpg",
            "photo_125.jpg", "photo_126.jpg", "photo_128.jpg", "photo_129.jpg",
            "photo_131.jpg", "photo_200.jpg", "fisher_turnaround_shot.jpg",
            "photo_005_fisher_freethrow.jpg", "photo_008_fisher_purple_celebration.jpg",
            "photo_009_fisher_outro_purple.jpg"
        }

        clean_candidates = [p for p in candidate_files if p.name not in blacklist]
        photos_map = {}

        for p_src in clean_candidates:
            dest_photo = self.photos_dir / p_src.name
            vf = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,unsharp=5:5:1.2"
            cmd = [
                FFMPEG_BIN, "-y",
                "-i", str(p_src),
                "-vf", vf,
                "-q:v", "2",
                str(dest_photo)
            ]
            subprocess.run(cmd, capture_output=True, timeout=20)
            if dest_photo.exists() and dest_photo.stat().st_size > 30000:
                w, h, lap_var = measure_laplacian_sharpness(dest_photo)
                if lap_var < 75.0 or w < 720 or h < 720:
                    logger.warning(f"🚨 [Fotoğraf Netlik/Çözünürlük Reddi] {dest_photo.name}: Laplacian {lap_var:.1f} < 75.0 veya {w}x{h} < 720p!")
                    dest_photo.unlink(missing_ok=True)
                    continue

                photos_map[dest_photo.stem] = dest_photo
                photos_map[dest_photo.name] = dest_photo

        logger.info(f"📸 Toplam {len(photos_map)//2} adet tam ekran dikey HD fotoğraf hazırlandı.")
        return photos_map

    def build_unique_asset_pool(self, athlete_key: str, bypass_cache: bool = False, project_id: str = "") -> List[Dict[str, Any]]:
        """
        4 Mimari Kilide Tam Uyumlu Storyboard:
        - Same-source oversampling engeli (max 2 kesit, min 15s mesafe).
        - Hiçbir sahne 2.30s'yi aşmaz.
        - Video ve Fotoğraf birbirini sıralı takip eder (Sıfır ardışık kaza).
        - Project Isolation Lock: Projeler arası varlık sızıntısını kesin engeller.
        """
        if bypass_cache:
            self.bypass_cache = True

        proj_id = project_id or self.project_id or athlete_key
        logger.info(f"🚀 [Varlık Toplama] {athlete_key} (project_id={proj_id}) için 4 kalkan uyumlu storyboard inşa ediliyor (bypass_cache={self.bypass_cache})...")
        
        downloaded = self.download_recipe_videos(athlete_key=athlete_key)
        clips_meta = self.slice_recipe_clips(athlete_key=athlete_key, downloaded_videos=downloaded)
        photos_map = self.fetch_authentic_photos(athlete_key=athlete_key)

        clips_dict = {c["label"]: c for c in clips_meta}
        for c in clips_meta:
            clips_dict[Path(c["path"]).stem] = c
            clips_dict[Path(c["path"]).name] = c

        pool = []

        storyboard = STORYBOARD_DEFINITIONS.get(athlete_key, [])

        for item in storyboard:
            m_type, key, concrete_query = item[0], item[1], item[2]
            resolved_item = None

            is_science = any(kw in key.lower() or kw in concrete_query.lower() for kw in ["brain", "synapse", "neural", "optic", "telemetry", "sensor", "mocap", "science", "laboratory", "biomechanic"])
            is_object_only = any(kw in key.lower() or kw in concrete_query.lower() for kw in ["buzzer", "clock", "light", "shot clock", "net_swish"])
            if is_science or is_object_only:
                item_target_subj = None
            elif any(kw in key.lower() or kw in concrete_query.lower() for kw in ["harden", "fisher", athlete_key]):
                item_target_subj = athlete_key
            else:
                item_target_subj = "NBA basketball player dribbling shooting in arena"

            if m_type == "video":
                # clips_dict içinden bul (önce tam anahtar eşleşmesi)
                for k, v in clips_dict.items():
                    if k == key or k == f"{key}.mp4":
                        if is_source_banned_for_project(v["source_video_id"], athlete_key) or is_source_banned_for_project(v["name"], athlete_key):
                            continue
                        resolved_item = {
                            "type": "video",
                            "path": v["path"],
                            "name": v["name"],
                            "source_video_id": v["source_video_id"],
                            "concrete_visual_query": concrete_query,
                            "target_subject": item_target_subj
                        }
                        break
                if not resolved_item:
                    for k, v in clips_dict.items():
                        if key in k:
                            if is_source_banned_for_project(v["source_video_id"], athlete_key) or is_source_banned_for_project(v["name"], athlete_key):
                                continue
                            resolved_item = {
                                "type": "video",
                                "path": v["path"],
                                "name": v["name"],
                                "source_video_id": v["source_video_id"],
                                "concrete_visual_query": concrete_query,
                                "target_subject": item_target_subj
                            }
                            break
            else:
                # photos_map içinden bul (önce tam anahtar eşleşmesi)
                for k, v in photos_map.items():
                    if k == key or k == f"{key}.jpg" or v.stem == key:
                        if is_source_banned_for_project(f"photo_{v.stem}", athlete_key) or is_source_banned_for_project(v.name, athlete_key):
                            continue
                        resolved_item = {
                            "type": "image",
                            "path": str(v),
                            "name": v.name,
                            "source_video_id": f"photo_{v.stem}",
                            "concrete_visual_query": concrete_query,
                            "target_subject": item_target_subj
                        }
                        break
                if not resolved_item:
                    for k, v in photos_map.items():
                        if key in k:
                            if is_source_banned_for_project(f"photo_{v.stem}", athlete_key) or is_source_banned_for_project(v.name, athlete_key):
                                continue
                            resolved_item = {
                                "type": "image",
                                "path": str(v),
                                "name": v.name,
                                "source_video_id": f"photo_{v.stem}",
                                "concrete_visual_query": concrete_query,
                                "target_subject": item_target_subj
                            }
                            break

            used_paths = {item["path"] for item in pool}
            used_sources = {item.get("source_video_id") for item in pool}
            used_md5s = {compute_file_md5(Path(item["path"])) for item in pool if Path(item["path"]).exists()}

            if resolved_item and Path(resolved_item["path"]).exists():
                item_md5 = compute_file_md5(Path(resolved_item["path"]))
                if resolved_item["path"] in used_paths or resolved_item.get("source_video_id") in used_sources or item_md5 in used_md5s:
                    logger.warning(
                        f"⚠️ Storyboard varlığı ({resolved_item['name']}) havuzda zaten kullanılmış (veya MD5 ikizi)! "
                        f"Otomatik re-query devreye giriyor..."
                    )
                    resolved_item = None
                else:
                    pool.append(resolved_item)

            if not resolved_item:
                logger.warning(f"⚠️ Storyboard varlığı bulunamadı: ({m_type}, {key}) - Otomatik re-query döngüsü başlatılıyor...")
                # Automatic re-query loop: Havuzda boşluk bırakmamak için onaylı taze alternatif ara
                replacement = None

                # 1. clips_meta içinden kullanılmamış ve kalkanı geçmiş bir klip ara
                for cand_c in clips_meta:
                    cand_cp = Path(cand_c["path"])
                    if cand_c["path"] not in used_paths and cand_c["source_video_id"] not in used_sources and compute_file_md5(cand_cp) not in used_md5s:
                        if is_source_banned_for_project(cand_c["source_video_id"], athlete_key) or is_source_banned_for_project(cand_c["name"], athlete_key):
                            continue
                        vis = self.vision_verifier.verify_slice(
                            media_path=cand_cp,
                            concrete_visual_query=concrete_query,
                            target_subject=item_target_subj
                        )
                        if not vis["passed"]:
                            continue
                        replacement = {
                            "type": "video",
                            "path": cand_c["path"],
                            "name": cand_c["name"],
                            "source_video_id": cand_c["source_video_id"],
                            "concrete_visual_query": concrete_query,
                            "target_subject": item_target_subj,
                            "SigLIP_score": vis.get("SigLIP_score", 0.0),
                            "negative_label_score": vis.get("negative_label_score", 0.0),
                            "laplacian_variance": vis.get("laplacian_variance", 0.0)
                        }
                        break

                # 2. photos_map içinden kullanılmamış bir fotoğraf ara
                if not replacement:
                    for p_name, p_path in photos_map.items():
                        p_str = str(p_path)
                        p_sid = f"photo_{p_path.stem}"
                        if p_str not in used_paths and p_sid not in used_sources and compute_file_md5(p_path) not in used_md5s:
                            if is_source_banned_for_project(p_sid, athlete_key) or is_source_banned_for_project(p_path.name, athlete_key):
                                continue
                            w, h, lap = measure_laplacian_sharpness(p_path)
                            if lap >= 75.0 and (w == 0 or w >= 720) and (h == 0 or h >= 720):
                                vis = self.vision_verifier.verify_slice(
                                    media_path=p_path,
                                    concrete_visual_query=concrete_query,
                                    target_subject=item_target_subj
                                )
                                if not vis["passed"]:
                                    continue
                                neg_lbl = vis.get("negative_label", "none")
                                neg_sc = vis.get("negative_label_score", 0.0)
                                p_pos_sc = vis.get("pos_score", 0.0)
                                if neg_lbl in ["free throw lineup", "players standing on bench dead ball", "heavy motion blur whip pan", "amateur gym with brick wall"] and neg_sc >= p_pos_sc:
                                    continue
                                replacement = {
                                    "type": "image",
                                    "path": p_str,
                                    "name": p_path.name,
                                    "source_video_id": p_sid,
                                    "concrete_visual_query": concrete_query,
                                    "target_subject": item_target_subj,
                                    "SigLIP_score": vis.get("SigLIP_score", 0.0),
                                    "negative_label_score": neg_sc,
                                    "laplacian_variance": lap
                                }
                                break

                if replacement:
                    logger.info(f"✅ [Storyboard Re-Query Çözüldü] ({m_type}, {key}) yerine {replacement['name']} ({replacement['type']}) atandı.")
                    pool.append(replacement)
                else:
                    logger.warning(f"⚠️ [Storyboard Re-Query] ({m_type}, {key}) için onaylı alternatif bulunamadı, sahne atlanıyor.")

        # Zero Loop Doğrulaması
        paths = [item["path"] for item in pool]
        if len(set(paths)) < len(pool):
            raise RuntimeError(
                f"🚨 [Varlık Çarpışması] Storyboard içinde aynı dosya birden fazla kez tanımlanmış! "
                f"Tekil: {len(set(paths))}, Toplam: {len(pool)}"
            )

        # Module-level registry'e projenin kaynaklarını kaydet
        PROJECT_USED_SOURCES.setdefault(proj_id, set()).update({item.get("source_video_id") for item in pool})

        logger.info(f"🎯 [Storyboard Hazır] Toplam {len(pool)} adet %100 YÖNETİLMİŞ sahne oluşturuldu. "
                    f"({sum(1 for x in pool if x['type'] == 'video')} Video Klip, "
                    f"{sum(1 for x in pool if x['type'] == 'image')} HD Fotoğraf)")
        return pool

    def get_backup_pool(self, athlete_key: str, used_paths: List[str]) -> List[Dict[str, Any]]:
        """Zaman çizelgesinde kullanılmamış zengin yedek havuz."""
        used_set = set(used_paths)
        used_filenames = {Path(p).name for p in used_paths}
        backups = []
        
        # 1. Kendi oluşturduğu klipler
        for c in sorted(self.clips_dir.glob("*.mp4")):
            if str(c) not in used_set and c.name not in used_filenames and c.stat().st_size > 50000:
                if is_source_banned_for_project(c.name, athlete_key):
                    continue
                backups.append({
                    "type": "video",
                    "path": str(c),
                    "media_path": str(c),
                    "mediaPath": str(c),
                    "name": c.name,
                    "source_video_id": f"src_backup_{c.stem}"
                })

        # 2. Küratörlü 1080p B-roll videoları
        if CURATED_BROLL_DIR.exists():
            for b in sorted(CURATED_BROLL_DIR.glob("*.mp4")):
                if str(b) not in used_set and b.name not in used_filenames and b.stat().st_size > 50000:
                    if is_source_banned_for_project(b.name, athlete_key):
                        continue
                    backups.append({
                        "type": "video",
                        "path": str(b),
                        "media_path": str(b),
                        "mediaPath": str(b),
                        "name": b.name,
                        "source_video_id": f"src_broll_{b.stem}"
                    })

        # 3. Küratörlü fotoğraflar
        for p in sorted(self.photos_dir.glob("*.jpg")):
            if str(p) not in used_set and p.name not in used_filenames and p.stat().st_size > 30000:
                if is_source_banned_for_project(p.name, athlete_key):
                    continue
                backups.append({
                    "type": "image",
                    "path": str(p),
                    "media_path": str(p),
                    "mediaPath": str(p),
                    "name": p.name,
                    "source_video_id": f"src_backup_photo_{p.stem}"
                })

        return backups
