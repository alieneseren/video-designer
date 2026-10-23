"""
ai_qa_watcher.py
================
Otonom AI Kalite Kontrolü & Klasör İzleyici (Autonomous Watcher Daemon)
'output/*/kontrol/' klasörüne yeni video ve materyal geldiğinde anında algılar.
LM Studio Gemma-4-12B ile denetler, uyuşmayan sahneleri video_scene_patcher ile otomatik yamalar (max 3 tur).
Tutarlı ve onaylı hale gelen videoları otomatik olarak 'output/<channel_id>/yuklenecek/' klasörüne taşır.
"""

import os
import sys
import re
import time
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Proje kök dizinini ekle
PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

try:
    from src.ai_video_inspector import audit_video_folder
    from src.video_scene_patcher import apply_local_video_patch
    from src.channel_manager import ChannelManager
except ImportError:
    from ai_video_inspector import audit_video_folder
    from video_scene_patcher import apply_local_video_patch
    from channel_manager import ChannelManager

MAX_CORRECTION_PASSES = 3


def is_file_ready(file_path: Path, wait_seconds: float = 2.0) -> bool:
    """Dosyanın diske yazımının tamamen bittiğini boyutunun sabitliği ile kontrol eder."""
    if not file_path.exists():
        return False
    size1 = file_path.stat().st_size
    if size1 < 100000:  # En az 100 KB olmalı
        return False
    time.sleep(wait_seconds)
    size2 = file_path.stat().st_size
    return size1 == size2


def process_kontrol_folder(folder_path: Path, max_passes: int = MAX_CORRECTION_PASSES) -> Dict[str, Any]:
    """
    Tek bir 'kontrol' klasörünü denetler, gerekirse yamalar ve onaylanınca 'yuklenecek'e taşır.
    """
    folder_path = Path(folder_path).resolve()
    final_video = folder_path / "final.mp4"
    if not final_video.exists():
        final_video = folder_path / "video.mp4"
    if not final_video.exists():
        return {"status": "SKIPPED", "message": "Video dosyası henüz hazır değil."}

    if not is_file_ready(final_video, wait_seconds=1.5):
        return {"status": "WAITING", "message": "Video dosyası diske yazılmaya devam ediyor."}

    channel_dir = folder_path.parent.parent
    channel_id = channel_dir.name
    yuklenecek_dir = channel_dir / "yuklenecek"
    yuklenecek_dir.mkdir(parents=True, exist_ok=True)

    lock_file = folder_path / ".qa_in_progress.lock"
    if lock_file.exists():
        return {"status": "LOCKED", "message": "Bu klasör şu an başka bir süreç tarafından inceleniyor."}

    lock_file.write_text(f"PID: {os.getpid()} - {datetime.now().isoformat()}", encoding="utf-8")
    patch_history = []

    try:
        current_pass = 1
        target_scenes = None
        while current_pass <= max_passes:
            print(f"\n==================================================================")
            mode_label = f"Delta Modu: {target_scenes}" if target_scenes else "Tam Video Taraması"
            print(f"[AI-QA-Watcher] 🔍 {folder_path.name} | Tur {current_pass}/{max_passes} ({mode_label}) Başlatılıyor...")
            print(f"==================================================================")

            audit_res = audit_video_folder(folder_path, target_scenes=target_scenes)
            if not audit_res.get("success"):
                print(f"[AI-QA-Watcher] ⚠️ Denetim başarısız: {audit_res.get('message')}")
                break

            is_consistent = audit_res.get("is_consistent", False)
            patches = audit_res.get("patches", [])
            passed_scenes = audit_res.get("passed_scenes", 0)
            total_scenes = max(1, audit_res.get("total_scenes_checked", 1))
            pass_ratio = passed_scenes / total_scenes

            print(f"[AI-QA-Watcher] 📊 Sonuç: {passed_scenes} Onay / {len(patches)} Hata (Uyum Oranı: %{int(pass_ratio*100)})")

            # Onay Kriterleri:
            # 1. Hata yoksa / tam tutarlıysa
            # 2. VEYA tur >= 2 iken sadece 1 sahne kaldıysa ve uyum oranı >= %88 ise (Görsel akışı bozmayacak minör tolerans)
            should_approve = is_consistent or not patches or (current_pass >= 2 and len(patches) <= 1 and pass_ratio >= 0.88)

            if should_approve:
                if not is_consistent and patches:
                    print(f"[AI-QA-Watcher] ✨ YÜKSEK UYUMLULUK ONAYI: %{int(pass_ratio*100)} uyum ve sadece {len(patches)} minör sahne ile video onaylandı!")
                else:
                    print(f"[AI-QA-Watcher] ✨ VİDEO TAMAMEN TUTARLI VE ONAYLANDI!")
                
                # Başarı raporu oluştur
                report_data = {
                    "audit_status": "APPROVED",
                    "channel_id": channel_id,
                    "folder_name": folder_path.name,
                    "total_passes_applied": current_pass - 1,
                    "approved_at": datetime.now().isoformat(),
                    "total_duration": audit_res.get("total_duration"),
                    "passed_scenes_count": passed_scenes,
                    "pass_ratio": round(pass_ratio, 2),
                    "patch_history": patch_history
                }
                report_file = folder_path / "qa_audit_report.json"
                report_file.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")

                # Kilidi kaldır ve 'yuklenecek' klasörüne taşı
                if lock_file.exists():
                    lock_file.unlink()

                dest_folder = yuklenecek_dir / folder_path.name
                if dest_folder.exists():
                    # Eski versiyon varsa yedekle
                    backup_name = f"{dest_folder.name}_replaced_{int(time.time())}"
                    shutil.move(str(dest_folder), str(yuklenecek_dir / backup_name))

                shutil.move(str(folder_path), str(dest_folder))

                # Otonom Yerel AI ile Viral Başlık, Açıklama ve Etiket Optimizasyonu
                try:
                    from src.ai_metadata_generator import auto_generate_and_apply_metadata
                    auto_generate_and_apply_metadata(dest_folder, channel_id=channel_id)
                except Exception:
                    try:
                        from ai_metadata_generator import auto_generate_and_apply_metadata
                        auto_generate_and_apply_metadata(dest_folder, channel_id=channel_id)
                    except Exception:
                        pass

                print(f"[AI-QA-Watcher] 🚀 Video başarıyla onaylandı ve 'yuklenecek' klasörüne aktarıldı:")
                print(f"               -> {dest_folder}")
                return {"status": "APPROVED", "destination": str(dest_folder)}

            # Hatalar var ve düzeltme hakkımız kaldıysa yamala
            if current_pass < max_passes:
                print(f"[AI-QA-Watcher] 🛠️ {len(patches)} hatalı sahne tespit edildi. In-Place AI Patcher uygulanıyor...")
                try:
                    patch_res = apply_local_video_patch(
                        video_path=str(final_video),
                        patches=patches,
                        output_path=str(final_video)  # In-place üzerine yazar
                    )
                    patch_history.append({
                        "pass": current_pass,
                        "patches_count": len(patches),
                        "patched_items": [p.get("issue_title") for p in patches],
                        "applied_at": datetime.now().isoformat()
                    })
                    print(f"[AI-QA-Watcher] ✅ Sahne yamaları başarıyla uygulandı ({len(patches)} sahne).")
                    
                    # Sonraki tur için sadece yamalanan sahneleri hedefle (Delta Kontrol Modu)
                    target_scenes = [
                        p.get("scene_idx") or int(re.search(r'\d+', p.get("id", "")).group(0))
                        for p in patches if (p.get("scene_idx") or re.search(r'\d+', p.get("id", "")))
                    ]
                    print(f"[AI-QA-Watcher] ⚡ Delta Modu Devrede: Tur {current_pass + 1} yalnızca {target_scenes} numaralı sahneleri denetleyecek.")
                except Exception as e_patch:
                    print(f"[AI-QA-Watcher] ❌ Yama uygulama hatası: {e_patch}")
                    break

            current_pass += 1

        # Max tura ulaşıldı ama hala hata varsa
        print(f"[AI-QA-Watcher] ⚠️ {max_passes} düzeltme turundan sonra bazı sahneler hala onaylanamadı.")
        report_data = {
            "audit_status": "NEEDS_MANUAL_REVIEW",
            "channel_id": channel_id,
            "folder_name": folder_path.name,
            "total_passes_applied": max_passes,
            "updated_at": datetime.now().isoformat(),
            "remaining_issues": patches,
            "patch_history": patch_history
        }
        (folder_path / "qa_audit_report.json").write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "NEEDS_REVIEW", "folder": str(folder_path)}

    finally:
        if lock_file.exists():
            try:
                lock_file.unlink()
            except Exception:
                pass


def scan_all_kontrol_folders(base_output_dir: Path = None, max_passes: int = MAX_CORRECTION_PASSES) -> List[Dict[str, Any]]:
    """Tüm kanalların 'kontrol' klasörlerini tarar."""
    if not base_output_dir:
        base_output_dir = PROJ_ROOT / "output"

    results = []
    if not base_output_dir.exists():
        return results

    # output/<channel_id>/kontrol/<folder_name>
    for ch_dir in base_output_dir.iterdir():
        if not ch_dir.is_dir() or ch_dir.name.startswith("."):
            continue
        kontrol_dir = ch_dir / "kontrol"
        if not kontrol_dir.exists() or not kontrol_dir.is_dir():
            continue

        for item in sorted(kontrol_dir.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                # İçinde video olan klasörü işle
                if (item / "final.mp4").exists() or (item / "video.mp4").exists():
                    res = process_kontrol_folder(item, max_passes=max_passes)
                    results.append({"folder": item.name, "result": res})

    return results


def run_daemon(poll_interval: int = 10, max_passes: int = MAX_CORRECTION_PASSES):
    """Sürekli arka plan izleyici döngüsü."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 👁️ AI QA Watcher Daemon başlatıldı (Kontrol Limiti: {max_passes} tur, Yoklama: {poll_interval}s)")
    while True:
        try:
            scan_all_kontrol_folders(max_passes=max_passes)
        except Exception as e:
            print(f"[AI-QA-Watcher] ⚠️ Tarama döngüsü uyarısı: {e}")
        time.sleep(poll_interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Video Quality Assurance Watcher & Patcher")
    parser.add_argument("--once", action="store_true", help="Tek bir tarama yapar ve çıkar.")
    parser.add_argument("--daemon", action="store_true", help="Arka planda sürekli dinler.")
    parser.add_argument("--folder", type=str, help="Yalnızca belirtilen klasörü denetler ve yamalar.")
    parser.add_argument("--max-passes", type=int, default=MAX_CORRECTION_PASSES, help="Maksimum sahne düzeltme turu (Varsayılan: 3)")
    args = parser.parse_args()

    if args.folder:
        res = process_kontrol_folder(Path(args.folder), max_passes=args.max_passes)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.once:
        res = scan_all_kontrol_folders(max_passes=args.max_passes)
        print(f"Tarama tamamlandı: {len(res)} işlendi.")
    else:
        run_daemon(max_passes=args.max_passes)
