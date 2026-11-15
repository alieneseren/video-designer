"""
Basketball Engine 2.0 - Vision Verifier (Slice-Level CLIP / SigLIP & Motion Reranking)
=======================================================================================
Gözü Açık Kurgu Katmanı:
1. Kesim Sonrası Görsel Doğrulama (Slice-Level CLIP):
   - Her adayın orta karesini ('t = 1.0s') yerel CLIP modelinden geçirir.
   - Pozitif semantik eşleşme kosinüs benzerliği >= 0.20 kontrolü.
2. Negatif Domain Kilidi (Zero-Shot Sınıflandırma):
   - ["amateur gym with brick wall", "outdoor asphalt basketball court",
      "static portrait interview", "dead ball inbounds pass",
      "blurry motion smear", "infographic text chart"] etiketleri test edilir.
   - Herhangi bir negatif skor, "professional NBA arena hardwood game action"
     skorunu geçerse klip OTOMATİK REDDEDİLİR.
3. Hareket & Anti-Freeze Kapısı (Frame Difference):
   - 3 ardışık kare arasındaki ortalama piksel farkı (optical flow diff) < 1.5 ise
     donmuş kare / statik slayt olarak reddedilir.
4. Whip-pan & Motion Blur Kapısı:
   - cv2.Laplacian varyansı ve CLIP 'blurry motion smear' skoru ile kamera savrulması engellenir.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import cv2
import numpy as np
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

logger = logging.getLogger("BasketballVisionVerifier")

# Negatif Domain Etiketleri (Asla montaja giremez!)
NEGATIVE_DOMAIN_LABELS = [
    "amateur gym with brick wall",
    "empty basketball gym wall or floor without players",
    "close up sneakers on floor",
    "outdoor asphalt streetball court",
    "outdoor painted concrete basketball court",
    "outdoor streetball court",
    "close up sneakers on outdoor court",
    "NBA 2K video game gameplay with player indicator circle and shot meter HUD",
    "football or soccer stadium",
    "athletics running track",
    "players standing on bench dead ball",
    "free throw lineup",
    "static portrait interview",
    "heavy motion blur whip pan",
    "unrelated infographic chart"
]

POSITIVE_ANCHORS_BASKETBALL = [
    "professional NBA arena hardwood game action",
    "sharp high-definition sports action photography"
]

POSITIVE_ANCHORS_SCIENCE = [
    "scientific 3D animation neurology biomechanics laboratory visualization",
    "sharp high-definition computer generated scientific visualization"
]

SCIENCE_KEYWORDS = [
    "brain", "synapse", "neural", "optic", "telemetry", "mocap",
    "biomechanic", "quad", "vector", "cortex", "kinetic", "muscle",
    "laboratory", "sensor", "pressure plate"
]

BROLL_GENERIC_KEYWORDS = [
    "crowd", "hoop", "scoreboard", "referee", "clock", "fans"
]


def select_positive_anchors(query: str, target_subject: Optional[str] = None) -> List[str]:
    """Sorgunun içeriğine göre en uygun pozitif referans çapalarını seçer."""
    q_lower = query.lower()
    if any(k in q_lower for k in SCIENCE_KEYWORDS):
        anchors = list(POSITIVE_ANCHORS_SCIENCE)
    else:
        anchors = list(POSITIVE_ANCHORS_BASKETBALL)

    if any(k in q_lower for k in ["crowd", "fans", "spectator", "spectators", "shock"]):
        anchors.append("authentic NBA basketball arena crowd spectators in stadium stands")
        anchors.append("shocked basketball fans and spectators in arena crowd")
        anchors.append("roaring basketball crowd in arena stands")
        anchors.append("shocked basketball spectators and fans in arena stands")
    if any(k in q_lower for k in ["scoreboard", "clock", "timer", "buzzer"]):
        anchors.append("digital overhead arena basketball scoreboard timer display")
    if any(k in q_lower for k in ["referee", "review", "monitor"]):
        anchors.append("NBA basketball referee reviewing replay monitor on scorer table")

    detected_subject = target_subject
    if not detected_subject:
        if "harden" in q_lower:
            detected_subject = "james_harden"
        elif "fisher" in q_lower:
            detected_subject = "derek_fisher"

    if detected_subject:
        clean_subj = detected_subject.replace("_", " ").title()
        anchors.append(f"{clean_subj} professional NBA basketball game action on hardwood court")
        anchors.append(f"{clean_subj} basketball action in NBA game")
        anchors.append(f"{clean_subj} portrait smiling proudly after winning basketball game")
        anchors.append(f"{clean_subj} in basketball uniform celebrating victory")

    # Somut görsel sorguyu hedef sahnenin pozitif çapası olarak listeye dahil et (Gate 2 kuralı)
    if query and query not in anchors:
        anchors.append(query)

    return anchors


class BasketballVisionVerifier:
    """Apple Silicon MPS hızlandırmalı yerel CLIP Görsel Doğrulayıcı ve Reranker."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BasketballVisionVerifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_id: str = "openai/clip-vit-base-patch32"):
        if getattr(self, "_initialized", False):
            return

        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"👁️ [Vision Verifier] Yerel CLIP modeli yükleniyor ({model_id}) on {self.device}...")
        try:
            self.processor = CLIPProcessor.from_pretrained(model_id, local_files_only=True)
            self.model = CLIPModel.from_pretrained(model_id, local_files_only=True).to(self.device)
            self.model.eval()
            self._initialized = True
            logger.info("✅ [Vision Verifier] CLIP modeli başarıyla yüklendi!")
        except Exception as e:
            logger.error(f"❌ CLIP yükleme hatası: {e}")
            self._initialized = False

    def extract_middle_frame_image(self, media_path: Path, timestamp: float = 1.0) -> Optional[Image.Image]:
        """Video veya görselin belirtilen karesini PIL.Image olarak döndürür."""
        is_video = media_path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]
        if not is_video:
            try:
                return Image.open(media_path).convert("RGB")
            except Exception:
                return None

        cap = cv2.VideoCapture(str(media_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        if total_frames <= 0:
            cap.release()
            return None

        duration = total_frames / fps
        clamped_time = min(max(0.05, timestamp), max(0.05, duration - 0.05))
        target_frame = int(round(clamped_time * fps))
        target_frame = min(max(0, target_frame), total_frames - 1)

        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb)
        return None

    def check_motion_and_freeze(self, video_path: Path, min_motion_diff: float = 1.5) -> Tuple[bool, float]:
        """
        Ardışık 3 kare arasındaki piksel farkını ölçer.
        diff < 1.5 ise donmuş/statik video olarak işaretler.
        """
        cap = cv2.VideoCapture(str(video_path))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        mid = max(1, total // 2)

        cap.set(cv2.CAP_PROP_POS_FRAMES, mid - 1)
        r1, f1 = cap.read()
        r2, f2 = cap.read()
        r3, f3 = cap.read()
        cap.release()

        if not (r1 and r2 and r3) or f1 is None or f2 is None or f3 is None:
            return True, 10.0

        diff1 = cv2.absdiff(f1, f2).mean()
        diff2 = cv2.absdiff(f2, f3).mean()
        avg_diff = float((diff1 + diff2) / 2.0)

        passed = avg_diff >= min_motion_diff
        return passed, avg_diff

    def check_entity_presence(
        self,
        pil_img: Image.Image,
        target_subject: Optional[str],
        query: str
    ) -> Tuple[bool, str, float, float]:
        """
        Hedef sporcu varlık kontrolü (Entity Presence Check):
        James Harden veya Derek Fisher sahnelerinde hedef sporcunun aktif topla oynama /
        şut aksiyonunu doğrular; geniş açı rol oyuncusu / off-ball sahnelerini eler.
        """
        if not target_subject or not self._initialized:
            return True, "", 0.0, 0.0

        q_lower = query.lower()
        if any(k in q_lower for k in SCIENCE_KEYWORDS) or any(k in q_lower for k in BROLL_GENERIC_KEYWORDS):
            return True, "", 0.0, 0.0

        if "harden" in target_subject.lower():
            athlete_name = "James Harden #13"
        elif "fisher" in target_subject.lower():
            athlete_name = "Derek Fisher #2"
        else:
            athlete_name = target_subject.replace("_", " ").title()

        pos_prompt = f"{athlete_name} actively handling basketball dribbling driving or shooting in NBA game"
        offball_prompt = f"wide basketball arena view without {athlete_name} or off-ball role players standing on court"

        inputs = self.processor(text=[pos_prompt, offball_prompt], images=pil_img, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            img_embeds = outputs.image_embeds / outputs.image_embeds.norm(dim=-1, keepdim=True)
            txt_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
            sims = (img_embeds @ txt_embeds.T)[0]

        on_ball_score = float(sims[0].item())
        off_ball_score = float(sims[1].item())

        if off_ball_score >= on_ball_score:
            return False, f"🚨 [Varlık / Rol Oyuncusu Reddi] {athlete_name} aktif aksiyonda değil (Off-ball skoru: {off_ball_score:.3f} >= On-ball: {on_ball_score:.3f})", on_ball_score, off_ball_score

        return True, "", on_ball_score, off_ball_score

    def verify_slice(
        self,
        media_path: Path,
        concrete_visual_query: str,
        target_subject: Optional[str] = None,
        min_cosine_similarity: float = 0.26,
        min_motion_diff: float = 1.5,
        min_width: int = 720,
        min_laplacian_variance: float = 75.0
    ) -> Dict[str, Any]:
        """
        Dilim seviyesinde görsel denetim (6 Deterministik Mekanik Kalkan):
        1. Teknik Kalite Kapısı: Çözünürlük >= 720px ve cv2.Laplacian varyansı >= 75.0 (Bulanık / Whip-pan / 240p reddi)
        2. Hareket / Anti-Freeze Kapısı: Motion diff >= 1.5
        3. 3 Noktalı (0.2s, 1.0s, 1.8s) Çoklu Kare Örnekleme: Her kare için keskinlik ve negatif domain kalkanı
        4. Katı Tavanlı Negatif Domain Kilidi: max_neg_sim >= 0.245 veya > (pos_anchor_threshold - 0.02) anında eleme
        5. Varlık (Entity Presence) kontrolü: off_ball_score >= on_ball_score sıfır tolerans elemesi
        """
        result = {
            "passed": True,
            "reasons": [],
            "pos_score": 0.0,
            "query_score": 0.0,
            "motion_diff": 0.0,
            "laplacian_variance": 0.0,
            "is_video": media_path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]
        }

        # 1. Çözünürlük ve Hareket Kontrolü (Gate 4)
        if result["is_video"]:
            cap = cv2.VideoCapture(str(media_path))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            if w > 0 and h > 0 and (w < min_width or h < min_width):
                result["passed"] = False
                result["reasons"].append(
                    f"🚨 [Düşük Çözünürlük Reddi] {w}x{h} < Min {min_width}p standardı!"
                )

            passed_motion, m_diff = self.check_motion_and_freeze(media_path, min_motion_diff=min_motion_diff)
            result["motion_diff"] = m_diff
            if not passed_motion:
                result["passed"] = False
                result["reasons"].append(
                    f"🚨 [Donmuş Kare Reddi] Hareket farkı: {m_diff:.2f} < {min_motion_diff} (Statik video!)"
                )

        # 2. Çoklu Kare Örnekleme: Videolar için [0.2s, 1.0s, 1.8s], Görseller için [1.0s]
        sample_timestamps = [0.2, 1.0, 1.8] if result["is_video"] else [1.0]
        sampled_frames = []
        for ts in sample_timestamps:
            f_img = self.extract_middle_frame_image(media_path, timestamp=ts)
            if f_img is None:
                result["passed"] = False
                result["reasons"].append(f"Kare okunamadı ({ts}s): {media_path.name}")
                return result
            sampled_frames.append((ts, f_img))

        # 3. OpenCV Laplacian Variance (Her örnek karede Whip-Pan & Bulanıklık Denetimi)
        mid_img = sampled_frames[1][1] if len(sampled_frames) > 1 else sampled_frames[0][1]
        lap_vars = []
        for ts, f_img in sampled_frames:
            np_frame = np.array(f_img)
            gray_frame = cv2.cvtColor(np_frame, cv2.COLOR_RGB2GRAY)
            if gray_frame.shape[0] != 720 and gray_frame.shape[0] > 0:
                scale = 720.0 / gray_frame.shape[0]
                new_w = max(1, int(gray_frame.shape[1] * scale))
                gray_frame = cv2.resize(gray_frame, (new_w, 720), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR)
            f_lap = float(cv2.Laplacian(gray_frame, cv2.CV_64F).var())
            lap_vars.append(f_lap)
            if f_lap < min_laplacian_variance:
                result["passed"] = False
                result["reasons"].append(
                    f"🚨 [Bulanık / Whip-Pan Reddi @ {ts}s] cv2.Laplacian varyansı {f_lap:.1f} < Min {min_laplacian_variance}!"
                )
        result["laplacian_variance"] = lap_vars[1] if len(lap_vars) > 1 else lap_vars[0]

        if not self._initialized:
            return result

        # 4. CLIP Sıfır-Atış Sınıflandırma ve Negatif Domain Kilidi (Gate 2)
        active_neg_labels = list(NEGATIVE_DOMAIN_LABELS)
        if target_subject and "harden" in target_subject.lower():
            active_neg_labels.append("San Antonio Spurs Lakers 2004 basketball game")

        pos_anchors = select_positive_anchors(concrete_visual_query, target_subject=target_subject)
        prompts = pos_anchors + active_neg_labels + [concrete_visual_query]

        inputs = self.processor(
            text=prompts,
            images=[f_img for _, f_img in sampled_frames],
            return_tensors="pt",
            padding=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            img_embeds = outputs.image_embeds / outputs.image_embeds.norm(dim=-1, keepdim=True)
            txt_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
            sims_matrix = (img_embeds @ txt_embeds.T)  # (num_frames, num_prompts)

        num_anchors = len(pos_anchors)
        mid_idx = 1 if len(sampled_frames) > 1 else 0

        # Her örnek kare için ayrı ayrı negatif kontrolü ve orta kare için skor kaydı
        for idx, (ts, f_img) in enumerate(sampled_frames):
            sims = sims_matrix[idx]
            pos_scores = [float(sims[i].item()) for i in range(num_anchors)]
            query_sim = float(sims[-1].item())
            pos_anchor_threshold = max(pos_scores + [query_sim])
            effective_pos_score = pos_anchor_threshold

            neg_sims = {label: float(sims[num_anchors + i].item()) for i, label in enumerate(active_neg_labels)}
            max_neg_label = max(neg_sims, key=neg_sims.get)
            max_neg_sim = neg_sims[max_neg_label]

            # Orta kare metriklerini ana sonuca yaz
            if idx == mid_idx:
                result["pos_score"] = effective_pos_score
                result["query_score"] = query_sim
                result["SigLIP_score"] = round(query_sim, 4)
                result["negative_label_score"] = round(max_neg_sim, 4)
                result["negative_label"] = max_neg_label

                # Gate 2.A: Cosine similarity >= min_cosine_similarity
                if query_sim < min_cosine_similarity:
                    result["passed"] = False
                    result["reasons"].append(
                        f"🚨 [Görsel Eşleşme Yetersiz] Cosine similarity {query_sim:.3f} < {min_cosine_similarity:.2f}"
                    )

            # Gate 2.B: Negatif Domain Kilidi
            # Sert tavan (>= 0.245): Negatif domain, boş salon duvarı ve alakasız sporlar/nesneler için mutlak tavan.
            # Dinamik kilit: Tüm negatifler için pozitif çapa eşiği - 0.02
            DOMAIN_AND_WALL_LABELS = {
                "amateur gym with brick wall",
                "empty basketball gym wall or floor without players",
                "close up sneakers on floor",
                "outdoor asphalt streetball court",
                "outdoor painted concrete basketball court",
                "outdoor streetball court",
                "close up sneakers on outdoor court",
                "football or soccer stadium",
                "athletics running track",
                "heavy motion blur whip pan",
                "unrelated infographic chart",
                "San Antonio Spurs Lakers 2004 basketball game",
                "static portrait interview"
            }
            is_domain_wall = max_neg_label in DOMAIN_AND_WALL_LABELS
            if is_domain_wall:
                if max_neg_sim >= 0.24 or max_neg_sim > (pos_anchor_threshold - 0.02):
                    result["passed"] = False
                    result["reasons"].append(
                        f"🚨 [Negatif Domain Kilidi @ {ts}s] '{max_neg_label}' skoru ({max_neg_sim:.3f}) >= 0.240 veya > "
                        f"(Pozitif çapa {pos_anchor_threshold:.3f} - 0.02)"
                    )
            else:
                if max_neg_sim >= pos_anchor_threshold:
                    result["passed"] = False
                    result["reasons"].append(
                        f"🚨 [Negatif Durum Kilidi @ {ts}s] '{max_neg_label}' skoru ({max_neg_sim:.3f}) >= "
                        f"Pozitif çapa ({pos_anchor_threshold:.3f})"
                    )

        # 5. Entity Presence Check (Orta kare üzerinden)
        if result["passed"] and target_subject:
            entity_ok, entity_reason, _, _ = self.check_entity_presence(mid_img, target_subject, concrete_visual_query)
            if not entity_ok:
                result["passed"] = False
                result["reasons"].append(entity_reason)

        return result
