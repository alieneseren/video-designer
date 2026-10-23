#!/usr/bin/env python3
"""
scripts/agy_video_qa.py
Terminal Tabanlı Video İnceleme, Hata Teşhis, In-Place Yama & Onay CLI Aracı

Kullanım:
    python3 scripts/agy_video_qa.py list
    python3 scripts/agy_video_qa.py extract 1 [--every 15]
    python3 scripts/agy_video_qa.py audit 1
    python3 scripts/agy_video_qa.py patch 1 --critique "04:20-04:48 Flash Airlines kadrani yerine Air Florida EPR kadrani..."
    python3 scripts/agy_video_qa.py approve 1 --notes "Onaylandi"
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Proje ana dizinini sys.path'e ekle
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ANSI Renkleri
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_DARK = "\033[48;5;235m"

def get_kontrol_videos() -> List[Dict[str, Any]]:
    """output/*/kontrol/* altındaki tüm videoları listeler."""
    output_dir = BASE_DIR / "output"
    videos = []
    
    if not output_dir.exists():
        return videos

    for channel_path in sorted(output_dir.iterdir()):
        if not channel_path.is_dir() or channel_path.name.startswith("."):
            continue
        kontrol_dir = channel_path / "kontrol"
        if not kontrol_dir.exists() or not kontrol_dir.is_dir():
            continue

        for item in sorted(kontrol_dir.iterdir()):
            if not item.is_dir() or item.name.startswith("."):
                continue

            video_file = None
            for cand in ["final.mp4", "video.mp4"]:
                vf = item / cand
                if vf.exists() and vf.stat().st_size > 100000:
                    video_file = vf
                    break

            if not video_file:
                continue

            # metadata.json oku
            meta_file = item / "metadata.json"
            meta_data = {}
            if meta_file.exists():
                try:
                    meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            vinfo_file = item / "video_info.json"
            vinfo_data = {}
            if vinfo_file.exists():
                try:
                    vinfo_data = json.loads(vinfo_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            # SRT kontrol
            srt_file = item / "subtitles.srt"
            has_subtitles = srt_file.exists() and srt_file.stat().st_size > 50

            dur = meta_data.get("duration") or vinfo_data.get("duration")
            if not dur:
                try:
                    cmd_d = [
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(video_file)
                    ]
                    r_d = subprocess.run(cmd_d, capture_output=True, text=True, timeout=5)
                    dur = float(r_d.stdout.strip()) if r_d.returncode == 0 else 0.0
                except Exception:
                    dur = 0.0

            title = meta_data.get("title") or vinfo_data.get("title") or item.name
            size_mb = round(video_file.stat().st_size / (1024 * 1024), 2)

            # QA onay durumu
            is_approved = (item / "qa_approved.json").exists() or (item / "qa_gemini_approved.json").exists()
            has_audit = (item / "qa_audit_report.json").exists() or (item / "qa_audit_findings.json").exists()

            videos.append({
                "channel": channel_path.name,
                "folder_name": item.name,
                "folder_path": str(item),
                "video_path": str(video_file),
                "title": title,
                "duration": round(float(dur), 1),
                "duration_formatted": f"{int(dur)//60:02d}:{int(dur)%60:02d}",
                "size_mb": size_mb,
                "has_subtitles": has_subtitles,
                "is_approved": is_approved,
                "has_audit": has_audit,
                "metadata": meta_data
            })

    return videos


def resolve_target(target_arg: str, videos: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Sayısal indeks (1, 2, 3...) veya klasör adından hedef videoyu çözer."""
    if videos is None:
        videos = get_kontrol_videos()

    if not videos:
        print(f"{C.RED}❌ 'kontrol/' klasöründe incelenecek video bulunamadı!{C.RESET}")
        sys.exit(1)

    # 1. Sayısal indeks kontrolü
    if target_arg.isdigit():
        idx = int(target_arg) - 1
        if 0 <= idx < len(videos):
            return videos[idx]
        print(f"{C.RED}❌ Geçersiz video numarası: {target_arg}. Mevcut: 1 - {len(videos)}{C.RESET}")
        sys.exit(1)

    # 2. Klasör adı veya yol eşleşmesi
    target_clean = target_arg.lower().strip()
    for v in videos:
        if target_clean in v["folder_name"].lower() or target_clean in v["folder_path"].lower() or target_clean in v["title"].lower():
            return v

    print(f"{C.RED}❌ Belirtilen video bulunamadı: '{target_arg}'{C.RESET}")
    print(f"{C.YELLOW}Mevcut videoları görmek için:{C.RESET} python3 scripts/agy_video_qa.py list")
    sys.exit(1)


# ═════════════════════════════════════════════════════════════════════════════
# KOMUT 1: LIST
# ═════════════════════════════════════════════════════════════════════════════
def cmd_list(args):
    """Kuyrukta kontrol bekleyen videoları listeler."""
    videos = get_kontrol_videos()
    print(f"\n{C.BOLD}{C.CYAN}═════════════════════════════════════════════════════════════════════════════════════════{C.RESET}")
    print(f"{C.BOLD}{C.WHITE} 🎬 KONTROL BEKLEYEN VİDEOLAR ({len(videos)} Adet){C.RESET}")
    print(f"{C.BOLD}{C.CYAN}═════════════════════════════════════════════════════════════════════════════════════════{C.RESET}")

    if not videos:
        print(f"{C.YELLOW}  (Şu anda kontrol klasöründe bekleyen video yok. Hepsi onaylanmış veya henüz gelmedi.){C.RESET}\n")
        return

    print(f" {C.BOLD}{'#':<3} {'KANAL':<16} {'SÜRE':<8} {'BOYUT':<10} {'DURUM':<12} {'BAŞLIK'}{C.RESET}")
    print(f" {'-'*3} {'-'*16} {'-'*8} {'-'*10} {'-'*12} {'-'*40}")

    for idx, v in enumerate(videos, 1):
        status = f"{C.GREEN}✓ Onaylı{C.RESET}" if v["is_approved"] else (f"{C.YELLOW}🔍 Denetlendi{C.RESET}" if v["has_audit"] else f"{C.CYAN}⏳ Bekliyor{C.RESET}")
        title_disp = v["title"][:42] + "..." if len(v["title"]) > 42 else v["title"]
        print(f" {C.BOLD}{idx:<3}{C.RESET} {v['channel']:<16} {v['duration_formatted']:<8} {str(v['size_mb']) + ' MB':<10} {status:<20} {title_disp}")

    print(f"{C.BOLD}{C.CYAN}═════════════════════════════════════════════════════════════════════════════════════════{C.RESET}")
    print(f"{C.DIM}💡 Bir videoyu incelemek için kareleri çıkartın:{C.RESET} python3 scripts/agy_video_qa.py extract 1")
    print(f"{C.DIM}💡 Otomatik kural denetimi çalıştırmak için:{C.RESET}     python3 scripts/agy_video_qa.py audit 1\n")


# ═════════════════════════════════════════════════════════════════════════════
# KOMUT 2: EXTRACT (Kare Çıkarma & Zaman Damgası İnceleme)
# ═════════════════════════════════════════════════════════════════════════════
def cmd_extract(args):
    """Videodan belirli aralıklarla veya sahne geçişlerinde zaman damgalı kareler çıkartır."""
    target = resolve_target(args.target)
    v_path = Path(target["video_path"])
    f_path = Path(target["folder_path"])
    frames_dir = f_path / "_qa_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{C.BOLD}{C.CYAN}📸 [Kare Çıkarma] Video inceleniyor:{C.RESET} {target['title']}")
    print(f"{C.DIM}Hedef Dizin:{C.RESET} {frames_dir}\n")

    # Mevcut eski kareleri temizle
    for old in frames_dir.glob("*.jpg"):
        try:
            old.unlink()
        except Exception:
            pass

    every_sec = getattr(args, "every", 10) or 10
    total_dur = target["duration"]

    print(f"⚡ FFmpeg ile her {every_sec} saniyede bir yüksek çözünürlüklü ve zaman damgalı kareler alınıyor...")

    # Zaman damgasını video üzerine yakarak kare çıkart
    # drawtext filtresi ile tam saniye ve mm:ss damgası
    vf_filter = (
        f"fps=1/{every_sec},"
        f"drawtext=text='VİDEO ZAMAN: %{{pts\\:hms}} (%{{pts\\:flt}}s)':"
        f"x=30:y=30:fontsize=32:fontcolor=white:box=1:boxcolor=black@0.75:boxborderw=8"
    )

    cmd_extract = [
        "ffmpeg", "-y",
        "-i", str(v_path),
        "-vf", f"fps=1/{every_sec}",
        "-q:v", "2",
        str(frames_dir / "frame_%04d.jpg")
    ]

    subprocess.run(cmd_extract, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Çıkarılan kareleri yeniden adlandır ve üzerine PIL ile zaman damgası bas
    from PIL import Image, ImageDraw, ImageFont
    try:
        font_stamp = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
    except Exception:
        font_stamp = ImageFont.load_default()

    extracted = sorted(list(frames_dir.glob("frame_*.jpg")))
    frame_manifest = []

    for idx, f_file in enumerate(extracted):
        sec = round(idx * every_sec, 1)
        m = int(sec) // 60
        s = int(sec) % 60
        ts_str = f"{m:02d}:{s:02d}"
        new_name = f"sec_{m:02d}_{s:02d}.jpg"
        target_file = frames_dir / new_name

        try:
            im = Image.open(f_file).convert("RGB")
            draw = ImageDraw.Draw(im)
            badge_text = f"⏱️ {ts_str} ({sec:.1f}s) // {target['title'][:35]}"
            draw.rectangle([(20, 20), (620, 75)], fill=(15, 20, 30))
            draw.rectangle([(20, 20), (620, 75)], outline=(0, 200, 255), width=2)
            draw.text((35, 30), badge_text, font=font_stamp, fill=(255, 255, 255))
            im.save(target_file, "JPEG", quality=90)
            f_file.unlink()
        except Exception:
            f_file.rename(target_file)

        frame_manifest.append({
            "timestamp": ts_str,
            "seconds": sec,
            "file": str(target_file),
            "filename": new_name
        })

    # SRT Timeline Dökümü
    srt_file = f_path / "subtitles.srt"
    timeline_txt = frames_dir / "transcript_timeline.txt"
    if srt_file.exists():
        srt_raw = srt_file.read_text(encoding="utf-8", errors="ignore")
        # Basit SRT ayrıştırıcı
        blocks = srt_raw.strip().split("\n\n")
        lines_out = []
        lines_out.append(f"=== TRANSKRİPT & ALTYAZI ZAMAN ÇİZELGESİ: {target['title']} ===\n")
        for b in blocks:
            b_lines = b.strip().split("\n")
            if len(b_lines) >= 3:
                time_range = b_lines[1]
                sub_text = " ".join(b_lines[2:])
                lines_out.append(f"[{time_range[:8]}] -> {sub_text}")
        timeline_txt.write_text("\n".join(lines_out), encoding="utf-8")
        print(f"📝 {C.GREEN}Altyazı zaman çizelgesi çıkarıldı:{C.RESET} {timeline_txt.name}")

    manifest_file = frames_dir / "manifest.json"
    manifest_file.write_text(json.dumps(frame_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ {C.BOLD}{C.GREEN}Toplam {len(frame_manifest)} kare çıkarıldı.{C.RESET}")
    print(f"\n{C.BOLD}🔍 AI İnceleme Talimatı:{C.RESET}")
    print(f"Bu kareleri incelemek için doğrudan 'view_file' veya görsel araçlarını kullanabilirsiniz:")
    for sample in frame_manifest[:6]:
        print(f"  • {sample['timestamp']} -> {sample['file']}")
    if len(frame_manifest) > 6:
        print(f"  ... ve {len(frame_manifest)-6} kare daha ({frames_dir})")
    print()


# ═════════════════════════════════════════════════════════════════════════════
# KOMUT 3: AUDIT (Otomatik Tutarlılık & Semantik Hata Denetimi)
# ═════════════════════════════════════════════════════════════════════════════
def cmd_audit(args):
    """Altyazı, başlık ve zaman çizelgesini havacılık ve stok görsel kurallarına göre denetler."""
    target = resolve_target(args.target)
    f_path = Path(target["folder_path"])
    meta = target["metadata"]
    title = target["title"]

    print(f"\n{C.BOLD}{C.CYAN}🔬 [Otomatik Denetim] Video analiz ediliyor:{C.RESET} {title}")

    issues = []
    warnings = []

    # 1. Uçuş Bilgisi Çıkarımı
    from src.aviation_telemetry_engine import extract_incident_metadata
    incident_meta = extract_incident_metadata(title)
    fl_name = incident_meta.get("flight_name", title)
    airline = incident_meta.get("airline", "")
    prohibited_airlines = incident_meta.get("prohibited_airlines", [])
    prohibited_keywords = incident_meta.get("prohibited_keywords", [])
    climate = incident_meta.get("climate", "NEUTRAL")

    print(f"📋 Tespit Edilen Olay: {C.BOLD}{fl_name}{C.RESET} (Havayolu: {airline}, İklim: {climate})")

    # 2. Altyazı Kontrolü
    srt_file = f_path / "subtitles.srt"
    srt_text = ""
    if srt_file.exists():
        srt_text = srt_file.read_text(encoding="utf-8", errors="ignore").lower()
    else:
        warnings.append("Altyazı dosyası (subtitles.srt) bulunamadı.")

    # Yasaklı Havayolu taraması
    for p_air in prohibited_airlines:
        if p_air.lower() in srt_text:
            issues.append(f"Altyazıda alakasız rakip havayolu adı geçiyor: '{p_air}' (Bu video {airline} olayıdır).")

    # 3. İklim Uyuşmazlığı Taraması
    if climate == "WINTER":
        # Kış fırtınası / Kar kazası
        warm_keywords = ["cherry blossom", "sakura", "sunny sky", "palm tree", "blistering heat", "sahil", "güneşli", "pembe çiçek"]
        for wk in warm_keywords:
            if wk in srt_text:
                issues.append(f"Kış fırtınası olayında ({fl_name}) tezat sıcak hava/çiçek ifadesi geçiyor: '{wk}'")

    # 4. CVR Pilot Rol Kontrolü (Air Florida için Larry kontrolü)
    if "florida" in fl_name.lower():
        # Kaptan Larry Wheaton'dır. Altyazıda veya CVR'da Larry diyen kişi FO olmalıdır.
        if "larry" in srt_text:
            print(f"✓ CVR İsim Kontrolü: Larry (Kaptan Wheaton) referansı doğrulandı.")

    # 5. Video Süresi ve Bölümler
    total_dur = target["duration"]
    if total_dur < 60:
        issues.append(f"Video çok kısa ({total_dur:.1f}s), YouTube yatay belgesel standartlarına uymuyor.")

    # Raporu kaydet
    audit_report = {
        "audited_at": datetime.now().isoformat(),
        "flight_name": fl_name,
        "airline": airline,
        "climate": climate,
        "total_duration": total_dur,
        "issues_found": issues,
        "warnings": warnings,
        "status": "NEEDS_PATCH" if issues else "CLEAN"
    }
    (f_path / "qa_audit_findings.json").write_text(json.dumps(audit_report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{C.BOLD}📊 DENETİM SONUCU:{C.RESET}")
    if issues:
        print(f"{C.RED}{C.BOLD}⚠️  {len(issues)} Kritik Uyuşmazlık Tespit Edildi:{C.RESET}")
        for iss in issues:
            print(f"  {C.RED}• {iss}{C.RESET}")
    else:
        print(f"{C.GREEN}{C.BOLD}✅ Otomatik kural kontrolünden temiz geçti.{C.RESET}")

    if warnings:
        for w in warnings:
            print(f"  {C.YELLOW}⚠️  {w}{C.RESET}")

    print(f"\n{C.DIM}Ayrıntılı rapor yazıldı:{C.RESET} {f_path / 'qa_audit_findings.json'}\n")


# ═════════════════════════════════════════════════════════════════════════════
# KOMUT 4: PATCH (In-Place Video Yama Uygulama)
# ═════════════════════════════════════════════════════════════════════════════
def cmd_patch(args):
    """Eleştiri metnindeki zaman aralıklarını kesip yerel olarak yamalar."""
    target = resolve_target(args.target)
    v_path = Path(target["video_path"])
    f_path = Path(target["folder_path"])

    if not args.critique:
        print(f"{C.RED}❌ Lütfen uygulanacak eleştiri metnini --critique parametresi ile belirtin.{C.RESET}")
        print(f"Örnek: python3 scripts/agy_video_qa.py patch 1 --critique '04:20-04:48 Flash Airlines yerine Air Florida EPR kadrani'")
        sys.exit(1)

    print(f"\n{C.BOLD}{C.CYAN}🛠️  [In-Place Yama Uygulama] Video:{C.RESET} {target['title']}")
    print(f"{C.DIM}Girilen Eleştiri/Talimat:{C.RESET}\n{args.critique}\n")

    from src.video_scene_patcher import analyze_critique_text, apply_local_video_patch

    # Orijinal videoyu yedekle (eğer daha önce yedeklenmediyse)
    backup_file = f_path / "final_original_backup.mp4"
    if not backup_file.exists():
        print(f"📦 Orijinal video yedekleniyor -> {backup_file.name}...")
        shutil.copy2(str(v_path), str(backup_file))

    # Eleştiri metnini ayrıştır
    patches = analyze_critique_text(
        critique_text=args.critique,
        video_duration=target["duration"],
        video_title=target["title"]
    )

    if not patches:
        print(f"{C.RED}❌ Eleştiri metninde değiştirilecek geçerli bir zaman aralığı tespit edilemedi!{C.RESET}")
        print(f"{C.YELLOW}Zaman formatı '04:20 – 04:48' veya '05:00 - 05:06' şeklinde olmalıdır.{C.RESET}")
        sys.exit(1)

    print(f"⚡ {C.BOLD}{len(patches)} Sahne Yaması Belirlendi:{C.RESET}")
    for p in patches:
        print(f"  • {C.YELLOW}[{p['start_time']} - {p['end_time']}]{C.RESET} ({p['duration']}s): {C.BOLD}{p['issue_title']}{C.RESET} -> Tip: {p['replacement_type']}")

    print(f"\n🚀 {C.CYAN}Video sahne montajı ve in-place yama başlatılıyor...{C.RESET}")
    start_t = time.time()
    res = apply_local_video_patch(video_path=str(v_path), patches=patches)
    elapsed = time.time() - start_t

    print(f"✅ {C.BOLD}{C.GREEN}Yama işlemi başarıyla tamamlandı!{C.RESET} ({elapsed:.1f} saniye)")
    print(f"🎬 {C.BOLD}Güncellenen Video:{C.RESET} {v_path}")

    # Yama logunu kaydet
    patch_log = {
        "applied_at": datetime.now().isoformat(),
        "critique_text": args.critique,
        "patches": patches,
        "result": res,
        "elapsed_seconds": round(elapsed, 1)
    }
    (f_path / "qa_patches_applied.json").write_text(json.dumps(patch_log, ensure_ascii=False, indent=2), encoding="utf-8")

    # Yamalanan bölümleri otomatik olarak çıkar ve doğrula
    print(f"\n📸 {C.CYAN}Yamalanan yeni bölümler doğrulanmak üzere kare kare çıkartılıyor...{C.RESET}")
    cmd_extract(args)


# ═════════════════════════════════════════════════════════════════════════════
# KOMUT 5: APPROVE (Onaylama & Yüklenecek Klasörüne Taşıma)
# ═════════════════════════════════════════════════════════════════════════════
def cmd_approve(args):
    """Videoyu onaylar ve 'kontrol/' klasöründen 'yuklenecek/' klasörüne taşır."""
    target = resolve_target(args.target)
    f_path = Path(target["folder_path"])
    channel_dir = f_path.parent.parent
    yuklenecek_dir = channel_dir / "yuklenecek"
    yuklenecek_dir.mkdir(parents=True, exist_ok=True)

    dest_folder = yuklenecek_dir / f_path.name
    if dest_folder.exists():
        backup_name = f"{dest_folder.name}_replaced_{int(time.time())}"
        shutil.move(str(dest_folder), str(yuklenecek_dir / backup_name))

    # Onay raporunu yaz
    approval_data = {
        "status": "APPROVED",
        "approved_by": "AGY Terminal QA CLI",
        "approved_at": datetime.now().isoformat(),
        "channel": target["channel"],
        "folder_name": target["folder_name"],
        "notes": args.notes or "Terminal üzerinden incelendi ve kusursuz onaylandı."
    }
    (f_path / "qa_approved.json").write_text(json.dumps(approval_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{C.BOLD}{C.GREEN}═════════════════════════════════════════════════════════════════════════════════════════{C.RESET}")
    print(f"{C.BOLD}{C.WHITE} 🎉 VİDEO BAŞARIYLA ONAYLANDI & TAŞINDI!{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}═════════════════════════════════════════════════════════════════════════════════════════{C.RESET}")
    print(f"🎬 Video:       {target['title']}")
    print(f"📁 Kaynak:      {f_path}")
    print(f"🚀 Hedef Dizin: {dest_folder}")
    print(f"📝 Not:         {approval_data['notes']}\n")

    # Klasörü taşı
    shutil.move(str(f_path), str(dest_folder))


# ═════════════════════════════════════════════════════════════════════════════
# ANA GİRİŞ NOKTASI
# ═════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="AGY Video QA & Splicer - Terminal Tabanlı Akıllı Video Denetleme Aracı",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Çalıştırılacak komut")

    # list
    p_list = subparsers.add_parser("list", help="Kontrol klasöründeki videoları listeler")
    p_list.set_defaults(func=cmd_list)

    # extract
    p_ext = subparsers.add_parser("extract", help="Videodan zaman damgalı kareler çıkartır")
    p_ext.add_argument("target", help="Video indeks numarası (1, 2, ...) veya klasör adı")
    p_ext.add_argument("--every", type=int, default=10, help="Kaç saniyede bir kare alınacağı (varsayılan: 10s)")
    p_ext.set_defaults(func=cmd_extract)

    # audit
    p_aud = subparsers.add_parser("audit", help="Video ve altyazı tutarlılığını otomatik denetler")
    p_aud.add_argument("target", help="Video indeks numarası (1, 2, ...) veya klasör adı")
    p_aud.set_defaults(func=cmd_audit)

    # patch
    p_pat = subparsers.add_parser("patch", help="Eleştiri metnine göre videoya in-place yama uygular")
    p_pat.add_argument("target", help="Video indeks numarası (1, 2, ...) veya klasör adı")
    p_pat.add_argument("--critique", required=True, help="Uygulanacak eleştiri veya yama metni")
    p_pat.set_defaults(func=cmd_patch)

    # approve
    p_app = subparsers.add_parser("approve", help="Videoyu onaylar ve yuklenecek/ dizinine taşır")
    p_app.add_argument("target", help="Video indeks numarası (1, 2, ...) veya klasör adı")
    p_app.add_argument("--notes", default="", help="Onay notu")
    p_app.set_defaults(func=cmd_approve)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
