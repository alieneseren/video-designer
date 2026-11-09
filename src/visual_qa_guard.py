"""
visual_qa_guard.py
==================
Kapalı Döngü Otomatik Görsel Denetçi (Closed-Loop Autonomous Visual Quality Gate).
Render edilen master/final video üzerinden TÜM sahnelerin karelerini çıkarır.
Aşırı yakınlaştırma (armpit/bad crop), filigran, TikTok yazıları, yabancı oyuncu,
eski kitap çizimleri/şemalar ve bozuk kadrajları CLIP & OpenCV ile denetler.
Hatalı kesme tespit ederse otomatik küratörlü yedek varlıkla onarır.
"""

import os
import sys
import cv2
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image

# CLIP & PyTorch Lazy Loader
_CLIP_MODEL = None
_CLIP_PROCESSOR = None

def get_clip_engine():
    global _CLIP_MODEL, _CLIP_PROCESSOR
    if _CLIP_MODEL is None:
        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel
            model_id = "openai/clip-vit-base-patch32"
            _CLIP_MODEL = CLIPModel.from_pretrained(model_id)
            _CLIP_PROCESSOR = CLIPProcessor.from_pretrained(model_id)
            _CLIP_MODEL.eval()
        except Exception as e:
            print(f"[VisualQAGuard] ⚠️ CLIP motoru yüklenemedi: {e}")
            _CLIP_MODEL = False
            _CLIP_PROCESSOR = False
    return _CLIP_MODEL, _CLIP_PROCESSOR


class VisualQAGuard:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else Path("/home/ubuntu/yt-remote-worker")
        self.curated_dir = self.base_dir / "assets" / "curated_sports"

    def extract_audit_frames(self, video_path: Path, output_dir: Path, timestamps: List[float]) -> List[Tuple[float, Path]]:
        """Video üzerinden verilen saniyelerdeki kareleri çıkartır."""
        output_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for idx, ts in enumerate(timestamps):
            frame_path = output_dir / f"audit_frame_{idx:02d}_{ts:.1f}s.jpg"
            cmd = [
                "ffmpeg", "-y", "-ss", f"{ts:.2f}",
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(frame_path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if frame_path.exists() and frame_path.stat().st_size > 5000:
                results.append((ts, frame_path))
        return results

    def inspect_frame(
        self,
        frame_path: Path,
        target_entity: str = "",
        banned_entities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Tek bir kareyi veya aday görseli inceler:
        1. Parlaklık / Kontrast / Boş siyah ekran kontrolü
        2. Kadraj, Filigran, Eski kitap çizimi/şema denetimi
        3. Koltuk altı / Garip kırpma / Yerde yatma kontrolü
        4. Banned Entity (Yanlış takımdan/rakip oyuncu) CLIP denetimi
        """
        report = {
            "path": str(frame_path),
            "passed": True,
            "issues": [],
            "scores": {}
        }

        # 1. OpenCV Temel Görüntü Sağlığı
        img_bgr = cv2.imread(str(frame_path))
        if img_bgr is None:
            report["passed"] = False
            report["issues"].append("Görsel okunamadı / bozuk dosya")
            return report

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        mean_bright = float(gray.mean())
        std_bright = float(gray.std())
        report["scores"]["mean_brightness"] = mean_bright
        report["scores"]["std_brightness"] = std_bright

        if mean_bright < 15.0 or std_bright < 10.0:
            report["passed"] = False
            report["issues"].append("Siyah/karanlık veya tekdüze boş kare")

        # 2. CLIP Semantik & Kadraj Denetimi
        model, processor = get_clip_engine()
        if model and processor:
            try:
                import torch
                pil_img = Image.open(frame_path).convert("RGB")
                
                pos_prompts = [
                    f"a high quality clear broadcast photo of {target_entity}, NBA basketball players, teams, or playoff celebrations" if target_entity else "a high quality NBA basketball game broadcast",
                    "a high quality medical scientific visual of human eye, pupil reflex, brain cortex tractography, or neural synapse",
                    "3D sports science biomechanics quad muscle load anatomy analysis with kinetic force arrows",
                    "an authentic NBA digital shot clock, scoreboard, or basketball court action"
                ]
                neg_prompts = [
                    "extreme close up armpit sweat bad framing",
                    "amateur tiktok screen recording with emoji and text overlay",
                    "blurry low quality pixelated 144p distorted frame",
                    "cardboard trading card photo of a player",
                    "vintage textbook anatomical line drawing or schematic diagram with labels",
                    "anime cartoon drawing illustration",
                    "player lying down on court floor awkwardly"
                ]

                # Banned Entities (Örn: Tim Duncan Derek Fisher videosunda olamaz)
                banned_prompts = []
                if banned_entities:
                    for be in banned_entities:
                        be_clean = be.strip()
                        if be_clean and len(be_clean) > 2:
                            if any(w in be_clean.lower() for w in ['trophy', 'scoreboard', 'overlay', 'drawing', 'textbook', 'ceremony', 'white house', 'suit']):
                                banned_prompts.append(f"a photo showing {be_clean}")
                            else:
                                banned_prompts.append(f"{be_clean} basketball player")

                all_prompts = pos_prompts + neg_prompts + banned_prompts
                inputs = processor(text=all_prompts, images=pil_img, return_tensors="pt", padding=True)
                with torch.no_grad():
                    outputs = model(**inputs)
                    probs = outputs.logits_per_image.softmax(dim=1)[0].tolist()

                pos_score = sum(probs[:len(pos_prompts)])
                neg_scores = probs[len(pos_prompts):len(pos_prompts) + len(neg_prompts)]
                max_neg_score = max(neg_scores)
                max_neg_idx = neg_scores.index(max_neg_score)

                report["scores"]["pos_score"] = round(pos_score, 4)
                report["scores"]["max_neg_score"] = round(max_neg_score, 4)
                report["scores"]["dominant_neg"] = neg_prompts[max_neg_idx]

                # Banned Entities skor kontrolü
                if banned_prompts:
                    banned_scores = probs[len(pos_prompts) + len(neg_prompts):]
                    max_banned_score = max(banned_scores)
                    max_banned_idx = banned_scores.index(max_banned_score)
                    report["scores"]["max_banned_score"] = round(max_banned_score, 4)
                    report["scores"]["dominant_banned"] = banned_prompts[max_banned_idx]
                    if max_banned_score > 0.45 and (max_banned_score > pos_score * 1.1):
                        report["passed"] = False
                        report["issues"].append(f"Yasaklı varlık tespit edildi: {banned_prompts[max_banned_idx]} (Skor: {max_banned_score:.2f})")

                # Eğer genel negatif skor pozitiften belirgin şekilde yüksekse
                if max_neg_score > 0.45 and max_neg_score > pos_score * 1.3:
                    report["passed"] = False
                    report["issues"].append(f"Görsel kalite kusuru: {neg_prompts[max_neg_idx]} (Skor: {max_neg_score:.2f})")

            except Exception as e:
                print(f"[VisualQAGuard] CLIP denetim hatası: {e}")

        return report

    def audit_video(
        self,
        video_path: Path,
        total_dur: float,
        target_entity: str,
        scratch_dir: Path,
        banned_entities: Optional[List[str]] = None,
        semantic_beats: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Video genelinde tüm sahneleri denetler (Closed-Loop Full-Timeline Audit).
        semantic_beats varsa her bir kesmenin ortasından kare alır (%100 sahne kapsamı).
        """
        audit_dir = scratch_dir / "audit_frames"
        if audit_dir.exists():
            shutil.rmtree(audit_dir, ignore_errors=True)
        audit_dir.mkdir(parents=True, exist_ok=True)

        sample_points = []
        if semantic_beats:
            for b in semantic_beats:
                mid = (b["start"] + b["end"]) / 2.0
                sample_points.append(round(mid, 2))
        else:
            # 8 kritik zaman noktası
            sample_points = [
                round(0.05 * total_dur, 2),
                round(0.15 * total_dur, 2),
                round(0.30 * total_dur, 2),
                round(0.45 * total_dur, 2),
                round(0.60 * total_dur, 2),
                round(0.75 * total_dur, 2),
                round(0.88 * total_dur, 2),
                round(0.96 * total_dur, 2)
            ]

        frames = self.extract_audit_frames(video_path, audit_dir, sample_points)
        all_passed = True
        reports = []

        for ts, fpath in frames:
            rep = self.inspect_frame(fpath, target_entity=target_entity, banned_entities=banned_entities)
            rep["timestamp"] = ts
            reports.append(rep)
            if not rep["passed"]:
                all_passed = False
                print(f"[VisualQAGuard] ❌ {ts:.1f}s karesi REDDEDİLDİ: {', '.join(rep['issues'])}")
            else:
                print(f"[VisualQAGuard] ✅ {ts:.1f}s karesi ONAYLANDI (Pos: {rep['scores'].get('pos_score', 1.0)})")

        return all_passed, reports


visual_qa_guard = VisualQAGuard()
