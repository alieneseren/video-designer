"""
Staging Manager (Pre-Render Material Staging & Distillation Pipeline)
=====================================================================
Bu modül; video üretiminden önce aday materyalleri ve üretilen ses dosyasını
yerel 'kontrol/{job_id}/materials/' dizininde toplar. LocalMaterialAuditor ile
tüm adayları denetler, onaylananları 'approved/', elenenleri 'rejected/' klasörüne
ayırır ve sunucuya aktarılacak 'approved_manifest.json' dosyasını hazırlar.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.local_material_auditor import AuditResult, LocalMaterialAuditor
except ImportError:
    from local_material_auditor import AuditResult, LocalMaterialAuditor

logger = logging.getLogger("StagingManager")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@dataclass
class DistillationReport:
    """Damıtma sürecinin özet karnesi."""
    job_id: str
    channel_id: str
    passed: bool
    total_candidates: int
    approved_count: int
    rejected_count: int
    scene_coverage_ratio: float
    replacement_requests: List[Dict[str, Any]] = field(default_factory=list)
    approved_manifest_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StagingManager:
    """
    Yerel kontrol klasörü altındaki aday materyal ve seslendirme yaşam döngüsünü yönetir.
    """

    def __init__(
        self,
        channel_id: str,
        job_id: str,
        base_output_dir: Optional[Path | str] = None
    ) -> None:
        self.channel_id = channel_id
        self.job_id = job_id

        if base_output_dir:
            self.base_output_dir = Path(base_output_dir)
        else:
            self.base_output_dir = Path(__file__).resolve().parent.parent / "output"

        # output/{channel_id}/kontrol/{job_id}/materials/
        self.job_dir = self.base_output_dir / self.channel_id / "kontrol" / self.job_id
        self.staging_dir = self.job_dir / "materials"
        self.audio_dir = self.staging_dir / "audio"
        self.raw_dir = self.staging_dir / "raw_candidates"
        self.approved_dir = self.staging_dir / "approved"
        self.rejected_dir = self.staging_dir / "rejected"
        self.manifest_path = self.staging_dir / "approved_manifest.json"

        self.init_directories()

    def init_directories(self) -> None:
        """Gerekli klasör hiyerarşisini oluşturur."""
        for d in [self.audio_dir, self.raw_dir, self.approved_dir, self.rejected_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save_audio_package(
        self,
        audio_source_path: Path | str,
        sentence_boundaries: Optional[Dict[str, Any] | List[Dict[str, Any]]] = None
    ) -> Path:
        """
        Dış ses dosyasını ve zamanlama verilerini kontrol klasörüne kopyalar/kaydeder.
        """
        src = Path(audio_source_path)
        dest_audio = self.audio_dir / src.name
        if src.exists():
            shutil.copy2(str(src), str(dest_audio))
            logger.info(f"🎙️ [Staging Audio] Dış ses kontrol klasörüne kopyalandı: {dest_audio.name}")

        if sentence_boundaries is not None:
            sb_path = self.audio_dir / "sentence_boundaries.json"
            with open(sb_path, "w", encoding="utf-8") as f:
                json.dump(sentence_boundaries, f, indent=2, ensure_ascii=False)
            logger.info(f"⏱️ [Staging Audio] Cümle zamanlamaları kaydedildi: {sb_path.name}")

        return dest_audio

    def add_candidate(self, candidate_path: Path | str, move: bool = False) -> Path:
        """Ham aday materyali raw_candidates klasörüne ekler."""
        src = Path(candidate_path)
        if not src.exists():
            raise FileNotFoundError(f"Aday materyal bulunamadı: {src}")

        dest = self.raw_dir / src.name
        if move:
            shutil.move(str(src), str(dest))
        else:
            shutil.copy2(str(src), str(dest))
        return dest

    def _fetch_wikimedia_candidate_urls(self, query: str, limit: int = 6) -> List[str]:
        """Wikimedia Commons API üzerinden görseller arar."""
        import ssl
        import urllib.parse
        import urllib.request

        ctx = ssl._create_unverified_context()
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "format": "json"
        }
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

        urls = []
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    infos = pdata.get("imageinfo", [])
                    if infos and infos[0].get("url"):
                        u = infos[0]["url"]
                        if any(u.lower().split("?")[0].endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                            urls.append(u)
        except Exception as e:
            logger.warning(f"Wikimedia araması başarısız ({query}): {e}")

        return urls

    def _download_candidate_file(self, url: str, dest_path: Path) -> bool:
        """URL'den görsel dosyasını indirir."""
        import ssl
        import urllib.request

        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                content = resp.read()
                if len(content) > 10000:
                    dest_path.write_bytes(content)
                    return True
        except Exception as e:
            logger.warning(f"Dosya indirilemedi ({url}): {e}")
        return False

    def replenish_for_scene(
        self,
        scene_index: int,
        scene_text: str,
        topic: str,
        auditor: LocalMaterialAuditor,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """Sahne için internetten/arşivden taze ikmal materyali çeker ve denetler."""
        logger.info(f"🔄 [İkmal Başlatıldı] Sahne {scene_index} için materyal ikmali aranıyor...")

        topic_words = topic.split()
        player_candidate = " ".join(topic_words[:2]) if len(topic_words) >= 2 else topic
        query_candidates = [
            f"{player_candidate} basketball",
            f"{topic} NBA",
            f"{player_candidate} NBA game action"
        ]

        approved_items = []
        for q in query_candidates:
            if approved_items:
                break
            urls = self._fetch_wikimedia_candidate_urls(q, limit=limit)
            for u_idx, img_url in enumerate(urls):
                if approved_items:
                    break
                ext = Path(img_url.split("?")[0]).suffix or ".jpg"
                temp_filename = f"replenish_s{scene_index}_{u_idx}{ext}"
                temp_path = self.raw_dir / temp_filename

                if self._download_candidate_file(img_url, temp_path):
                    audit = auditor.audit_visual(
                        file_path=temp_path,
                        topic=topic,
                        scene_sentence=scene_text,
                        scene_index=scene_index,
                        channel_id=self.channel_id
                    )
                    if audit.approved:
                        dest_approved = self.approved_dir / temp_filename
                        shutil.move(str(temp_path), str(dest_approved))
                        entry = {
                            "name": temp_filename,
                            "path": str(dest_approved),
                            "type": "image",
                            "confidence": audit.confidence_score,
                            "detected_subjects": audit.detected_subjects,
                            "audit_notes": f"[İkmal] {audit.audit_notes}"
                        }
                        approved_items.append(entry)
                        logger.info(f"✨ [İkmal Onaylandı] Sahne {scene_index}: {temp_filename} ({audit.confidence_score:.2f})")
                    else:
                        auditor.handle_rejected_file(
                            temp_path,
                            self.rejected_dir,
                            purge_physical_file_after_learning=True
                        )
        return approved_items

    def run_distillation(
        self,
        auditor: LocalMaterialAuditor,
        topic: str,
        scenes: List[Dict[str, Any]],
        purge_rejected_media: bool = False
    ) -> DistillationReport:
        """
        Tüm raw_candidates dosyalarını sahnelerle eşleştirerek LM Studio ile denetler.
        Onaylananları approved/ dizinine, elenenleri rejected/ dizinine taşır.
        Eksik sahneler için otomatik ikmal (replenishment) tetikler.
        """
        raw_files = sorted([f for f in self.raw_dir.iterdir() if f.is_file() and not f.name.startswith(".")])
        total_candidates = len(raw_files)
        approved_count = 0
        rejected_count = 0

        manifest: Dict[str, Any] = {
            "job_id": self.job_id,
            "channel_id": self.channel_id,
            "topic": topic,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scenes": [],
            "approved_assets": []
        }

        replacement_requests: List[Dict[str, Any]] = []
        covered_scene_indices: set = set()

        logger.info(f"🔍 [Damıtma Başladı] Toplam {total_candidates} aday dosya denetlenecek. (Konu: '{topic}')")
        pool: List[Path] = list(raw_files)

        for idx, scene in enumerate(scenes):
            scene_text = scene.get("text") or scene.get("sentence") or scene.get("narration") or ""
            scene_duration = float(scene.get("duration", 4.0))

            scene_entry: Dict[str, Any] = {
                "scene_index": idx,
                "text": scene_text,
                "duration": scene_duration,
                "approved_assets": []
            }

            # 1. Sahneye özel etiketli adayları öne al, yoksa genel havuzu kullan
            scene_tagged = [rf for rf in pool if f"scene_{idx}_" in rf.name.lower() or f"s{idx}_" in rf.name.lower()]
            candidates_to_try = scene_tagged if scene_tagged else list(pool)

            # 2. Sahne için onaylanan materyal bulunana kadar adayları tara (her sahne için 3-4 materyale kadar)
            while candidates_to_try and len(scene_entry["approved_assets"]) < 4:
                candidate = candidates_to_try.pop(0)
                if candidate in pool:
                    pool.remove(candidate)

                audit = auditor.audit_visual(
                    file_path=candidate,
                    topic=topic,
                    scene_sentence=scene_text,
                    scene_index=idx,
                    channel_id=self.channel_id
                )

                if audit.approved:
                    approved_count += 1
                    covered_scene_indices.add(idx)
                    dest_approved = self.approved_dir / candidate.name
                    shutil.move(str(candidate), str(dest_approved))

                    asset_entry = {
                        "name": candidate.name,
                        "path": str(dest_approved),
                        "type": "video" if candidate.suffix.lower() in [".mp4", ".mov", ".webm"] else "image",
                        "confidence": audit.confidence_score,
                        "detected_subjects": audit.detected_subjects,
                        "audit_notes": audit.audit_notes
                    }
                    scene_entry["approved_assets"].append(asset_entry)
                    manifest["approved_assets"].append(asset_entry)
                    logger.info(f"✅ [ONAYLANDI] Sahne {idx}: {candidate.name} (Güven: {audit.confidence_score:.2f})")
                else:
                    # Gerçek sporcu görseli ise başka sahneler için havuzda tut, sadece gerçek çöp/stok ise fiziksel sil
                    is_real_subject = any(s in audit.audit_notes.lower() or s in " ".join(audit.detected_subjects).lower() for s in ["harden", "fisher", "rockets", "lakers", "nba", "basketball"])
                    if is_real_subject and not audit.is_irrelevant_or_stock:
                        pool.append(candidate)
                        logger.info(f"🔄 [Havuzda Tutuldu] {candidate.name} Sahne {idx} ile tam örtüşmedi ancak geçerli sporcu görseli, diğer sahneler için havuzda tutuldu.")
                    else:
                        rejected_count += 1
                        auditor.handle_rejected_file(
                            candidate,
                            self.rejected_dir,
                            purge_physical_file_after_learning=purge_rejected_media
                        )
                        logger.warning(
                            f"❌ [ELENDİ] Sahne {idx}: {candidate.name} -> "
                            f"Neden: {', '.join(audit.rejection_reasons)} | "
                            f"İkmal Önerisi: {audit.replacement_query}"
                        )

                        replacement_requests.append({
                            "scene_index": idx,
                            "rejected_file": candidate.name,
                            "reasons": audit.rejection_reasons,
                            "replacement_query": audit.replacement_query or f"{topic} {scene_text[:30]}"
                        })

            # 3. Eğer sahne hala boş kaldıysa, anında İkmal (Replenishment) yap
            if not scene_entry["approved_assets"]:
                logger.warning(f"⚠️ [Sahne {idx} Boş Kaldı] Hedefe yönelik yeni materyal ikmali yapılıyor...")
                replenished_assets = self.replenish_for_scene(idx, scene_text, topic, auditor)
                if replenished_assets:
                    approved_count += len(replenished_assets)
                    covered_scene_indices.add(idx)
                    scene_entry["approved_assets"].extend(replenished_assets)
                    manifest["approved_assets"].extend(replenished_assets)

            manifest["scenes"].append(scene_entry)

        # 4. Kalan aday materyalleri genel konu ve b-roll bağlamında denetle ve havuza ekle
        if pool:
            logger.info(f"🔍 [Kalan Havuz Denetimi] Sahneler tamamlandı, kalan {len(pool)} aday materyal konu bağlamında taranıyor...")
            while pool:
                cand = pool.pop(0)
                audit = auditor.audit_visual(
                    file_path=cand,
                    topic=topic,
                    scene_sentence=topic,
                    scene_index=-1,
                    channel_id=self.channel_id
                )
                if audit.approved:
                    approved_count += 1
                    dest_approved = self.approved_dir / cand.name
                    shutil.move(str(cand), str(dest_approved))
                    asset_entry = {
                        "name": cand.name,
                        "path": str(dest_approved),
                        "type": "video" if cand.suffix.lower() in [".mp4", ".mov", ".webm"] else "image",
                        "confidence": audit.confidence_score,
                        "detected_subjects": audit.detected_subjects,
                        "audit_notes": audit.audit_notes
                    }
                    manifest["approved_assets"].append(asset_entry)
                    logger.info(f"✅ [ONAYLANDI (Genel Havuz)] {cand.name} (Güven: {audit.confidence_score:.2f})")
                else:
                    rejected_count += 1
                    auditor.handle_rejected_file(
                        cand,
                        self.rejected_dir,
                        purge_physical_file_after_learning=purge_rejected_media
                    )
                    logger.warning(
                        f"❌ [ELENDİ (Genel Havuz)] {cand.name} -> "
                        f"Neden: {', '.join(audit.rejection_reasons)}"
                    )

        # Manifesti kaydet
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        total_scenes = max(1, len(scenes))
        coverage_ratio = len(covered_scene_indices) / total_scenes
        passed = coverage_ratio >= 1.0 and approved_count > 0

        report = DistillationReport(
            job_id=self.job_id,
            channel_id=self.channel_id,
            passed=passed,
            total_candidates=total_candidates,
            approved_count=approved_count,
            rejected_count=rejected_count,
            scene_coverage_ratio=coverage_ratio,
            replacement_requests=replacement_requests,
            approved_manifest_path=str(self.manifest_path)
        )

        logger.info(
            f"📊 [Damıtma Tamamlandı] Kapsama: %{coverage_ratio * 100:.1f} "
            f"({len(covered_scene_indices)}/{total_scenes} Sahne) | "
            f"Onaylanan: {approved_count}, Elenen: {rejected_count}"
        )

        return report

    def sync_to_remote_server(
        self,
        remote_host: str,
        remote_user: str,
        ssh_key_path: str,
        remote_job_dir: str
    ) -> bool:
        """
        Yalnızca onaylanmış materyalleri (approved/), manifesti ve ses dosyalarını
        uzak sunucudaki iş dizinine SCP/Rsync ile aktarır.
        """
        logger.info(f"🚀 [Sync] Onaylı materyaller sunucuya aktarılıyor: {remote_job_dir}")
        remote_mat_dir = f"{remote_job_dir}/materials"

        # 1. Uzak dizini oluştur
        mkdir_cmd = [
            "ssh", "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            f"{remote_user}@{remote_host}",
            f"mkdir -p {remote_mat_dir}/approved {remote_mat_dir}/audio"
        ]
        try:
            subprocess.run(mkdir_cmd, check=True, timeout=15)
        except Exception as e:
            logger.error(f"Uzak dizin oluşturulamadı: {e}")
            return False

        # 2. Approved materyalleri kopyala
        approved_files = list(self.approved_dir.glob("*"))
        if approved_files:
            scp_approved = [
                "scp", "-i", ssh_key_path,
                "-o", "StrictHostKeyChecking=no",
                *[str(f) for f in approved_files],
                f"{remote_user}@{remote_host}:{remote_mat_dir}/approved/"
            ]
            try:
                subprocess.run(scp_approved, check=True, timeout=180)
            except Exception as e:
                logger.error(f"Approved dosyaları kopyalanamadı: {e}")
                return False

        # 3. Manifest ve Audio kopyala
        files_to_copy = [str(self.manifest_path)]
        audio_files = list(self.audio_dir.glob("*"))
        if audio_files:
            files_to_copy.extend([str(a) for a in audio_files])

        scp_meta = [
            "scp", "-i", ssh_key_path,
            "-o", "StrictHostKeyChecking=no",
            *files_to_copy,
            f"{remote_user}@{remote_host}:{remote_mat_dir}/"
        ]
        try:
            subprocess.run(scp_meta, check=True, timeout=60)
            logger.info("✨ [Sync] Tüm onaylı materyaller ve manifest sunucuya başarıyla eşitlendi.")
            return True
        except Exception as e:
            logger.error(f"Manifest ve audio aktarılırken hata: {e}")
            return False
