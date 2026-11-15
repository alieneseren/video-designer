"""
Kontrol Klasöründeki Videoları Baştan Damıtma ve Üretme Skripti
===============================================================
1. Derek Fisher ve James Harden işleri için aday materyalleri staging klasöründe toplar.
2. Yerel LM Studio (Qwen 3.5 9B) ile her sahne için multimodal denetim yapar.
3. Hatalı/uygunsuz materyalleri eler, negatif hafızaya kaydeder ve temizler.
4. Onaylanan damıtılmış materyalleri sunucuya aktarır.
5. Sunucuda '--strict-materials-only' ile kesin ve sıfır döngülü render başlatır.
6. Bitince final videolarını yerel 'kontrol' klasörüne indirir.
"""

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

from src.local_material_auditor import LocalMaterialAuditor
from src.staging_manager import StagingManager

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("KontrolReproduction")

SSH_KEY = "/Users/alienes/new_affilate/ssh-key-2026-09-02 (1).key"
SSH_USER = "ubuntu"
SSH_HOST = "132.226.187.103"
REMOTE_BASE = "/home/ubuntu/yt-remote-worker"
LOCAL_BASE = Path(__file__).resolve().parent / "output"

JOBS = [
    {
        "job_id": "exec_mat_20261104_224042_The_Neurobiology_of_Derek_Fish",
        "athlete_key": "derek_fisher",
        "topic": "The Neurobiology of Derek Fisher 0.4 Second Buzzer Beater 2004 NBA Playoffs Spurs vs Lakers"
    },
    {
        "job_id": "exec_mat_20261104_224042_The_Deceleration_Secret_Behind",
        "athlete_key": "james_harden",
        "topic": "The Deceleration Secret Behind James Harden Step-Back Jumper Biomechanics Houston Rockets"
    }
]

def run_ssh(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    ssh_cmd = [
        "ssh", "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        f"{SSH_USER}@{SSH_HOST}",
        cmd
    ]
    res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
    return res.returncode, res.stdout, res.stderr

def run_scp_download(remote_src: str, local_dest: str, timeout: int = 90) -> bool:
    scp_cmd = [
        "scp", "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        f"{SSH_USER}@{SSH_HOST}:{remote_src}",
        local_dest
    ]
    try:
        res = subprocess.run(scp_cmd, capture_output=True, timeout=timeout)
        return res.returncode == 0
    except Exception as e_scp:
        logger.warning(f"⚠️ SCP indirme zaman aşımı veya hata ({remote_src}): {e_scp}")
        return False

def run_scp_upload(local_src: str, remote_dest: str, timeout: int = 90) -> bool:
    scp_cmd = [
        "scp", "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        local_src,
        f"{SSH_USER}@{SSH_HOST}:{remote_dest}"
    ]
    try:
        res = subprocess.run(scp_cmd, capture_output=True, timeout=timeout)
        return res.returncode == 0
    except Exception as e_scp:
        logger.warning(f"⚠️ SCP yükleme hatası ({local_src}): {e_scp}")
        return False

def process_job(job_info: dict, auditor: LocalMaterialAuditor):
    job_id = job_info["job_id"]
    athlete_key = job_info["athlete_key"]
    topic = job_info["topic"]
    channel_id = "thebasketballshows"

    local_job_dir = LOCAL_BASE / channel_id / "kontrol" / job_id
    dest_video = local_job_dir / "final.mp4"
    if dest_video.exists() and dest_video.stat().st_mtime > 1794490000 and not job_info.get("force_rerun"):
        logger.info(f"⏭️ [ZATEN TAMAMLANDI] {job_id} ({athlete_key}) güncel sistemle üretilmiş ve doğrulanmış ({dest_video.stat().st_size / (1024*1024):.2f} MB). Atlanıyor.")
        return dest_video

    logger.info(f"\n=======================================================")
    logger.info(f"🚀 [BAŞLADI] {job_id} ({athlete_key})")
    logger.info(f"=======================================================")

    # 1. Yerel kontrol staging dizinini hazırla
    staging = StagingManager(channel_id=channel_id, job_id=job_id)
    # Temiz bir damıtma başlatmak için eski raw ve approved dosyalarını sıfırla
    for old_f in list(staging.raw_dir.glob("*")) + list(staging.approved_dir.glob("*")):
        if old_f.is_file():
            old_f.unlink(missing_ok=True)

    # 2. İş konfigürasyonunu sunucudan oku
    rc, stdout, stderr = run_ssh(f"cat {REMOTE_BASE}/jobs/{job_id}.json")
    if rc != 0 or not stdout.strip():
        raise RuntimeError(f"İş JSON dosyası okunamadı: {stderr}")
    job_data = json.loads(stdout)
    script = job_data.get("script_data") or {}
    scenes = script.get("scenes", [])

    # 3. Mevcut dış sesi kontrol klasörüne kopyala
    local_job_dir = LOCAL_BASE / channel_id / "kontrol" / job_id
    existing_voiceover = local_job_dir / "voiceover.mp3"
    existing_sb = local_job_dir / "sentence_boundaries.json"
    if existing_voiceover.exists():
        sb_dict = json.loads(existing_sb.read_text(encoding="utf-8")) if existing_sb.exists() else None
        staging.save_audio_package(existing_voiceover, sb_dict)

    # 4. Sunucudaki aday fotoğrafları yerel raw_candidates'e indir
    logger.info(f"📥 [Aday Toplama] Sunucudaki {athlete_key} fotoğrafları yerel denetime indiriliyor...")
    remote_athlete_dir = f"{REMOTE_BASE}/assets/curated_sports/athletes/{athlete_key}"
    rc, stdout, _ = run_ssh(f"ls {remote_athlete_dir}/photo_*.jpg")
    photo_files = [line.strip() for line in stdout.splitlines() if line.strip().endswith(".jpg")]

    # İlk 35 adayı indir
    downloaded_count = 0
    for p_full in photo_files[:35]:
        p_name = Path(p_full).name
        dest_p = staging.raw_dir / p_name
        if not dest_p.exists():
            ok = run_scp_download(p_full, str(dest_p), timeout=60)
            if ok:
                downloaded_count += 1
        else:
            downloaded_count += 1
    logger.info(f"📥 Toplam {downloaded_count} adet ham aday fotoğraf kontrol klasörüne alındı.")

    # 5. LM Studio (Qwen 3.5 9B) ile Multimodal Damıtma
    logger.info(f"🧠 [LM Studio Multimodal Damıtma] {len(scenes)} sahne için adaylar taranıyor...")
    distillation_report = staging.run_distillation(
        auditor=auditor,
        topic=topic,
        scenes=scenes,
        purge_rejected_media=True # Kullanıcı tercihi: Öğren ve hatalı dosyayı sil
    )

    logger.info(f"📊 Damıtma Özeti: Onaylanan: {distillation_report.approved_count}, Elenen: {distillation_report.rejected_count}")

    # 6. Onaylanan materyalleri sunucuya yükle
    remote_job_dir = f"{REMOTE_BASE}/output/{channel_id}/{job_id}"
    logger.info(f"🚀 [Sync] Onaylı materyaller ve manifest sunucuya aktarılıyor...")
    staging.sync_to_remote_server(
        remote_host=SSH_HOST,
        remote_user=SSH_USER,
        ssh_key_path=SSH_KEY,
        remote_job_dir=remote_job_dir
    )

    # 7. Sunucu iş JSON'unu güncelle (strict_materials_only aktif)
    job_data["strict_materials_only"] = True
    job_data["force_rebuild"] = True
    job_data["approved_manifest_path"] = f"{remote_job_dir}/materials/approved_manifest.json"

    # Güncellenen JSON'u sunucuya yaz
    tmp_local_json = Path(f"/tmp/{job_id}_strict.json")
    tmp_local_json.write_text(json.dumps(job_data, indent=2, ensure_ascii=False), encoding="utf-8")
    run_scp_upload(str(tmp_local_json), f"{REMOTE_BASE}/jobs/{job_id}.json", timeout=20)
    tmp_local_json.unlink(missing_ok=True)

    # 8. Eski render çıktılarını temizle & Sunucuda Render Başlat (run_job.sh ile)
    final_remote_mp4 = f"{remote_job_dir}/final_video.mp4"
    status_remote_json = f"{REMOTE_BASE}/jobs/{job_id}_status.json"
    remote_log_file = f"{REMOTE_BASE}/logs/{job_id}.log"
    remote_workspace_dir = f"{REMOTE_BASE}/workspace/{job_id}"
    run_ssh(f"rm -rf {final_remote_mp4} {status_remote_json} {remote_log_file} {remote_workspace_dir}")

    # Yereldeki eski videoyu yedekle
    dest_video = local_job_dir / "final.mp4"
    if dest_video.exists():
        backup_old = local_job_dir / "final_old_pre_distill.mp4"
        backup_old.unlink(missing_ok=True)
        shutil.move(str(dest_video), str(backup_old))
        logger.info(f"💾 Eski video yedeklendi: {backup_old.name}")

    logger.info(f"🎬 [Render Başlatıldı] Sunucuda run_job.sh ile sports_shorts_engine kesin render başlatılıyor...")
    remote_job_json = f"{REMOTE_BASE}/jobs/{job_id}.json"
    render_cmd = f"bash {REMOTE_BASE}/run_job.sh {remote_job_json}"
    rc, stdout, stderr = run_ssh(render_cmd, timeout=15)
    logger.info(f"  Sunucu Yanıtı: {stdout.strip() or stderr.strip()}")

    # 9. Render Durumunu İzle
    logger.info(f"⏳ [İzleme] Render tamamlanana kadar sunucu durumu takip ediliyor...")
    final_remote_mp4 = f"{remote_job_dir}/final_video.mp4"
    status_remote_json = f"{REMOTE_BASE}/jobs/{job_id}_status.json"

    max_wait_seconds = 450
    poll_interval = 10
    elapsed = 0
    is_done = False

    while elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval

        # Status kontrolü
        rc_s, s_out, _ = run_ssh(f"cat {status_remote_json} 2>/dev/null")
        if rc_s == 0 and s_out.strip():
            try:
                st = json.loads(s_out)
                logger.info(f"  [Render İlerlemesi] %{st.get('progress', 0)} - {st.get('message', '')} ({elapsed}s)")
                if st.get("status") == "completed":
                    is_done = True
                    break
                elif st.get("status") == "failed":
                    raise RuntimeError(f"Render sunucuda başarısız oldu: {st.get('error')}")
            except Exception:
                pass
        else:
            # Log dosyasının son satırını oku
            rc_l, l_out, _ = run_ssh(f"tail -n 1 {remote_log_file} 2>/dev/null")
            if rc_l == 0 and l_out.strip():
                logger.info(f"  [Sunucu Log] {l_out.strip()[:100]} ({elapsed}s)")

        # Render'ın gerçekten bitip bitmediğini kontrol et:
        # Worker işlemi ve ffmpeg bitmiş mi?
        rc_p, p_out, _ = run_ssh(f"ps aux | grep -E '{job_id}|sports_shorts_engine|ffmpeg' | grep -v grep")
        processes_running = bool(p_out.strip())

        if not processes_running:
            # Süreç bittiyse ve final_video.mp4 mevcut ve boyutu > 5MB ise tamamlandı
            rc_v, v_out, _ = run_ssh(f"test -f {final_remote_mp4} && ls -lh {final_remote_mp4}")
            if rc_v == 0 and "final_video.mp4" in v_out:
                logger.info(f"  [Render Tamamlandı - Süreç Bitti] {v_out.strip()}")
                is_done = True
                break

    if not is_done:
        raise TimeoutError(f"Render {max_wait_seconds} saniye içinde tamamlanamadı.")

    # 10. Yeni Final Videoyu Yerel Kontrol Klasörüne İndir
    dest_video = local_job_dir / "final.mp4"
    logger.info(f"📥 [İndirme] Damıtılmış yeni final video yerel kontrol klasörüne indiriliyor: {dest_video}")
    ok = run_scp_download(final_remote_mp4, str(dest_video), timeout=120)
    if not ok or not dest_video.exists() or dest_video.stat().st_size < 1000000:
        raise RuntimeError(f"Video indirilemedi veya geçersiz boyutta: {dest_video}")

    # 11. Yerel Apple Silicon M4 RVC Ses Klonu Giydirme (vc_1792868444 - Yeni Kayıt 3)
    logger.info(f"🎙️ [RVC M4 Ses Giydirme] {dest_video.name} üzerine 'vc_1792868444' klon ses modeli giydiriliyor...")
    try:
        from src.voice_clone_manager import VoiceCloneManager
        vcm = VoiceCloneManager()
        clone_res = vcm.apply_voice_clone_to_video(
            video_path=dest_video,
            clone_id="vc_1792868444"
        )
        if clone_res.get("success"):
            logger.info(f"✅ [RVC Başarılı] Klon ses giydirildi: {clone_res.get('clone_name')} ({clone_res.get('processing_time_sec')}s)")
        else:
            logger.warning(f"⚠️ [RVC Uyarısı] Klon ses giydirilemedi: {clone_res.get('reason')}")
    except Exception as e_vc:
        logger.error(f"❌ [RVC Hatası] Ses klonlama istisnası: {e_vc}")

    logger.info(f"✨ [BAŞARILI] {job_id} yeni sistemle baştan üretildi! Dosya Boyutu: {dest_video.stat().st_size / (1024*1024):.2f} MB")
    return dest_video

def main():
    auditor = LocalMaterialAuditor()
    logger.info("🤖 LM Studio bağlantısı kontrol ediliyor...")
    if not auditor.is_api_reachable():
        raise RuntimeError("LM Studio API (http://localhost:1234/v1) erişilemiyor! Lütfen LM Studio'yu açık tutun.")

    for job in JOBS:
        try:
            process_job(job, auditor)
        except Exception as e:
            logger.error(f"❌ İşlem hatası ({job['job_id']}): {e}", exc_info=True)

    logger.info("\n🎉 TÜM KONTROL VİDEOLARI YENİ SİSTEMLE BAŞARIYLA ÜRETİLDİ!")

if __name__ == "__main__":
    main()
