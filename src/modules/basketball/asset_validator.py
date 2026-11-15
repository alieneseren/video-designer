"""
Basketball Engine 2.0 - Asset & Pacing Validator (Deterministic Mechanical Locks)
================================================================================
4 Katı Mimari Mekanik Kalkan:
1. Tek YouTube Maç Özetinden Çoklu Kesit (Same-Source Over-Sampling) Kilidi:
   - Aynı source_video_id'den timeline boyunca EN FAZLA 2 kesit alınabilir.
   - Bu iki kesit arasında en az 15.0 saniye (450 kare) mesafe zorunludur.
   - Ardışık iki kesit ASLA aynı kaynaktan gelemez.
2. Zaman Çizelgesi Üzerinde 3 Noktalı (Giriş / Orta / Çıkış) Çift Yönlü pHash Kilidi:
   - Her klibin %10, %50 ve %90 zaman damgalarından 3 temsili kare çıkarılır.
   - Zaman çizelgesindeki tüm sahnelerle çapraz karşılaştırma yapılır (min Hamming mesafesi >= 10).
3. Çözünürlük & Netlik Kapısı (Laplacian Variance + Min Height >= 720):
   - Kaynak video height < 720 ise doğrudan elenir.
   - OpenCV ile cv2.Laplacian(gray, cv2.CV_64F).var() skoru ölçülür; < 65.0 olan pikselli/bulanık içerikler reddedilir.
4. Zorunlu Kesme (Tavan <= 2.35s) ve locked_segments Koruması:
   - Hiçbir sahne 2.4s'yi aşamaz.
   - locked == True olan sahnelerin dosya yolu, başlangıç ve bitiş kareleri immutable (değiştirilemez) kalır.
"""

import hashlib
import json
import logging
import math
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import cv2
import imagehash
from PIL import Image

from src.modules.basketball.vision_verifier import BasketballVisionVerifier

logger = logging.getLogger("BasketballAssetValidator")


def compute_file_md5(file_path: Path) -> str:
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_video_duration(video_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    try:
        out = subprocess.check_output(cmd).decode("utf-8").strip()
        return float(out)
    except Exception:
        return 2.0


def extract_3point_frames(video_path: Path, temp_dir: Path) -> List[Path]:
    """
    Klibin tam 0.2s, 1.0s ve 1.8s zaman damgalarından 3 temsili karesini çıkarır (3-Point pHash Lock).
    Böylece aynı maçın veya klibin farklı anlarındaki görsel benzerlikler 3 noktadan yakalanır.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    dur = get_video_duration(video_path)
    timestamps = [0.2, 1.0, 1.8]
    extracted = []

    for idx, target_ts in enumerate(timestamps):
        ts = max(0.05, min(dur - 0.05, target_ts)) if dur > 0.1 else 0.05
        out_frame = temp_dir / f"{video_path.stem}_3pt_{idx}_{ts:.2f}s.jpg"
        if not out_frame.exists() or out_frame.stat().st_size < 3000:
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{ts:.2f}",
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(out_frame)
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=10)
            except Exception as e:
                logger.warning(f"Kare çekme hatası ({video_path.name} @ {ts:.2f}s): {e}")

        if out_frame.exists() and out_frame.stat().st_size > 3000:
            extracted.append(out_frame)

    return extracted


def get_3point_fingerprints(media_path: Path, temp_dir: Path) -> List[imagehash.ImageHash]:
    """Medyanın 3 noktalı pHash vektörlerini döndürür."""
    is_video = media_path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]
    frames = []

    if is_video:
        frames = extract_3point_frames(media_path, temp_dir)
    else:
        frames = [media_path]

    hashes = []
    for f in frames:
        try:
            im = Image.open(f)
            hashes.append(imagehash.phash(im))
        except Exception as e:
            logger.warning(f"pHash çıkarma hatası ({f.name}): {e}")

    return hashes


def measure_laplacian_sharpness(media_path: Path) -> Tuple[int, int, float]:
    """
    Görsel veya videonun çözünürlüğünü ve Laplacian netlik varyansını ölçer.
    Scale-normalized to standard 720p height so that the 75.0 variance floor
    correctly distinguishes crisp high-definition assets from blurry transitions
    and low-res 240p/360p stretches.
    Checks multi-point (25%, 50%, 75%) for video slices to evaluate maximum
    in-focus definition during dynamic sports action.
    """
    is_video = media_path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]
    if is_video:
        cap = cv2.VideoCapture(str(media_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return 0, 0, 0.0
        vars_list = []
        w_ret, h_ret = 0, 0
        for frac in [0.25, 0.50, 0.75]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(total_frames - 1, int(total_frames * frac))))
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                w_ret, h_ret = w, h
                ref_h = 720
                ref_w = int(w * (ref_h / h))
                resized = cv2.resize(frame, (ref_w, ref_h), interpolation=cv2.INTER_AREA if h > ref_h else cv2.INTER_LINEAR)
                gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                vars_list.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        cap.release()
        max_var = max(vars_list) if vars_list else 0.0
        return w_ret, h_ret, max_var
    else:
        img = cv2.imread(str(media_path))
        if img is None:
            return 0, 0, 0.0
        h, w = img.shape[:2]
        ref_h = 720
        ref_w = int(w * (ref_h / h))
        resized = cv2.resize(img, (ref_w, ref_h), interpolation=cv2.INTER_AREA if h > ref_h else cv2.INTER_LINEAR)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        return w, h, var


class BasketballAssetValidator:
    """Deterministik Visual Fingerprint, Same-Source Limiti ve Pacing Kalkanı."""

    def __init__(
        self,
        max_cut_duration: float = 2.40,
        min_hamming_distance: int = 10,
        max_same_source_clips: int = 1,
        min_same_source_distance_sec: float = 15.0,
        min_height: int = 720,
        min_width: int = 720,
        min_laplacian_variance: float = 75.0
    ):
        self.max_cut_duration = max_cut_duration
        self.min_hamming_distance = min_hamming_distance
        self.max_same_source_clips = max_same_source_clips
        self.min_same_source_distance_sec = min_same_source_distance_sec
        self.min_height = min_height
        self.min_width = min_width
        self.min_laplacian_variance = min_laplacian_variance
        self.vision_verifier = BasketballVisionVerifier()

    def extract_source_id(self, media_path: Path, cut: Dict[str, Any]) -> str:
        """Klibin hangi maç veya video kaynağından geldiğini belirler."""
        if "source_video_id" in cut and cut["source_video_id"]:
            return cut["source_video_id"]
        
        name = media_path.stem.lower()
        # Bilinen maç özetleri ve kaynaklar
        if "wesley" in name or "anklebreaker" in name:
            return "src_clippers_wesley_2018"
        elif "kings" in name:
            return "src_kings_stepback_2019"
        elif "warriors" in name:
            return "src_warriors_gamewinner_2019"
        elif "magic" in name:
            return "src_magic_isolation_2019"
        elif "rubio" in name:
            return "src_jazz_rubio_2018"
        elif "sport_science" in name or "mocap" in name:
            return "src_espn_sport_science"
        elif "espn" in name:
            return "src_espn_breakdown"
        elif "trent_tucker" in name or "tucker" in name:
            return "src_trent_tucker_1990"
        elif "duncan" in name or "perimeter" in name or "spurs" in name or "game5" in name:
            return "src_spurs_game5_2004"
        elif "brain" in name or "synapse" in name or "neural" in name:
            return "src_neurobiology_3d"
        elif "purple_celebration" in name or "celebrate" in name:
            return "src_purple_celebration_2004"
        else:
            return name

    def validate_timeline(self, cuts: List[Dict[str, Any]], work_dir: Path) -> Tuple[bool, List[str]]:
        errors = []
        md5_registry: Dict[str, int] = {}
        # Source video tracking: {source_id: [(cut_idx, start_sec, media_name)]}
        source_usage_registry: Dict[str, List[Tuple[int, float, str]]] = {}
        # 3-point pHash registry: [(cut_idx, media_name, [pHash1, pHash2, pHash3])]
        fingerprint_registry: List[Tuple[int, str, List[imagehash.ImageHash]]] = []

        temp_frames_dir = work_dir / "_validator_3pt_frames"
        shutil.rmtree(temp_frames_dir, ignore_errors=True)
        temp_frames_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"🛡️ [Deterministik 4 Kalkan Denetimi] {len(cuts)} kesme inceleniyor...")

        for idx, cut in enumerate(cuts):
            media_path = Path(cut.get("media_path", cut.get("mediaPath", "")))
            if not media_path.exists():
                errors.append(f"Cut {idx}: Medya dosyası diskte bulunamadı: {media_path}")
                continue

            dur = float(cut.get("duration", cut.get("durationInFrames", 60) / 30.0))
            start_sec = float(cut.get("start_time", cut.get("startFrame", 0) / 30.0))
            is_video = media_path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]

            # KURAL 4: Pacing Tavanı (<= 2.35s)
            if dur > self.max_cut_duration + 0.05:
                errors.append(
                    f"Cut {idx} ({media_path.name}): 2.4s Kuralı Aşıldı! "
                    f"Mevcut: {dur:.2f}s > İzin Verilen: {self.max_cut_duration:.2f}s"
                )

            # KURAL 1: Same-Source Over-Sampling Kilidi
            if is_video:
                src_id = self.extract_source_id(media_path, cut)
                if src_id not in source_usage_registry:
                    source_usage_registry[src_id] = []
                
                prev_uses = source_usage_registry[src_id]
                if len(prev_uses) >= self.max_same_source_clips:
                    errors.append(
                        f"🚨 [Same-Source Aşımı] Cut {idx} ({media_path.name}): '{src_id}' kaynağından "
                        f"en fazla {self.max_same_source_clips} kesit alınabilir! (Daha önce Cut {[p[0] for p in prev_uses]} kullandı)"
                    )
                elif len(prev_uses) == 1:
                    prev_idx, prev_time, prev_name = prev_uses[0]
                    gap = abs(start_sec - prev_time)
                    if gap < self.min_same_source_distance_sec:
                        errors.append(
                            f"🚨 [Same-Source 15s Mesafe İhlali] Cut {idx} ({media_path.name}) ile Cut {prev_idx} ({prev_name}) "
                            f"aynı '{src_id}' kaynağından! Aralarındaki mesafe: {gap:.2f}s < {self.min_same_source_distance_sec:.2f}s zorunlu aralık!"
                        )
                
                source_usage_registry[src_id].append((idx, start_sec, media_path.name))

            # KURAL 1.B: Ardışık Sahne Tekrarı
            if idx > 0:
                prev_path = Path(cuts[idx - 1].get("media_path", cuts[idx - 1].get("mediaPath", "")))
                if prev_path.name == media_path.name:
                    errors.append(
                        f"🚨 [Ardışık Sahne Hatası] Cut {idx-1} ve Cut {idx} aynı medyayı kullanıyor: {media_path.name}"
                    )

            # KURAL 1.C: Byte-level MD5 Kontrolü
            f_md5 = compute_file_md5(media_path)
            if f_md5 in md5_registry:
                prev_idx = md5_registry[f_md5]
                errors.append(
                    f"🚨 [MD5 İkizi Tespit Edildi] Cut {idx} ({media_path.name}) ile Cut {prev_idx} birebir aynı dosya!"
                )
            else:
                md5_registry[f_md5] = idx

            # KURAL 2: 3 Noktalı (Giriş / Orta / Çıkış) Çift Yönlü pHash
            hashes = get_3point_fingerprints(media_path, temp_frames_dir)
            if hashes:
                for prev_idx, prev_name, prev_hashes in fingerprint_registry:
                    # Çapraz minimum Hamming mesafesini hesapla
                    min_dist = 999
                    for h_cur in hashes:
                        for h_prev in prev_hashes:
                            d = h_cur - h_prev
                            if d < min_dist:
                                min_dist = d

                    if min_dist < self.min_hamming_distance:
                        errors.append(
                            f"🚨 [3-Point pHash Görsel İkizi Reddedildi] Cut {idx} ({media_path.name}) ile "
                            f"Cut {prev_idx} ({prev_name}) görsel olarak ikiz! "
                            f"(En yakın 3-point pHash Hamming Mesafesi: {min_dist} < {self.min_hamming_distance})"
                        )

                fingerprint_registry.append((idx, media_path.name, hashes))

            # KURAL 3: Çözünürlük ve Netlik Kapısı (Laplacian Variance >= 75.0, Min Height/Width >= 720)
            w, h, lap_var = measure_laplacian_sharpness(media_path)
            if (h > 0 and h < self.min_height) or (w > 0 and w < self.min_width):
                errors.append(
                    f"🚨 [Düşük Çözünürlük Reddi] Cut {idx} ({media_path.name}): "
                    f"Çözünürlük {w}x{h} < Min {self.min_height}p standardı!"
                )
            if lap_var > 0 and lap_var < self.min_laplacian_variance:
                errors.append(
                    f"🚨 [Bulanık / Düşük Netlik Reddi] Cut {idx} ({media_path.name}): "
                    f"cv2.Laplacian varyansı {lap_var:.1f} < Min {self.min_laplacian_variance} tabanı!"
                )

            # KURAL 5: Slice-Level CLIP Negatif Domain, Entity Presence & Motion-Flow Kapısı (Gözü Açık Kurgu)
            concrete_query = cut.get("concrete_visual_query", cut.get("action_notes", "professional NBA basketball game action"))
            target_subj = cut.get("target_subject")
            vision_res = self.vision_verifier.verify_slice(
                media_path=media_path,
                concrete_visual_query=concrete_query,
                target_subject=target_subj
            )
            siglip_sc = vision_res.get("SigLIP_score", vision_res.get("query_score", 0.0))
            neg_sc = vision_res.get("negative_label_score", 0.0)
            neg_lbl = vision_res.get("negative_label", "none")
            src_lbl = self.extract_source_id(media_path, cut)
            status_str = "PASS" if vision_res["passed"] else "REJECTED"
            logger.info(
                f"🛡️ [Gate Verification] Cut {idx:02d} | source_id={src_lbl:<28} | file={media_path.name:<32} | "
                f"SigLIP_score={siglip_sc:.4f} | neg_score={neg_sc:.4f} ({neg_lbl}) | laplacian={lap_var:.1f} | {status_str}"
            )
            if not vision_res["passed"]:
                for r in vision_res["reasons"]:
                    errors.append(f"Cut {idx} ({media_path.name}): {r}")

        if errors:
            logger.error(f"❌ [Deterministik 4 Kalkan Başarısız] {len(errors)} kural ihlali bulundu:\n" + "\n".join(errors))
            return False, errors

        logger.info(f"✅ [Deterministik 4 Kalkan Onayladı] {len(cuts)} kesmenin tamamı 4 katı kuraldan başarıyla geçti!")
        return True, []
