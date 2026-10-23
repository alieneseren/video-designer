#!/usr/bin/env python3
"""
scripts/patch_air_florida_masterpiece.py
=========================================
Air Florida 90 Nihai ve Kusursuz Kurgu Yamalayıcı.
Kullanıcı incelemesinde tespit edilen 7 kritik hatayı tek hamlede,
sıfır boşluklu (gapless) ve tam otantik arşiv/animasyon ile giderir:

1. 03:48 – 04:12: Kronoloji Hatası -> Uçak pistte hızlanırken erken çıkan kurtarma helikopteri
   ve vinç fotoğrafları kaldırıldı; Boeing 737 kokpit lövye ve gösterge kalkış akışı yerleştirildi.
2. 04:18: 1 Saniyelik Glitch (Flash Frame) -> Önceki projeden kalan Flash Airlines kadranı,
   04:12'den başlatılan Stall Warning / Stick Shaker acil durum HUD'ı ile tamamen yok edildi.
3. 04:20 – 04:48: Yanlış Zamanda Çıkan EPR Grafiği -> Uçak havada stall'a girip düşerken tekrarlanan
   statik motor göstergesi kaldırıldı; DCA Pist 36'dan Potomac Köprüsü'ne FDR irtifa dalış haritası
   (Peak 352 FT -> Suya Çakılma) yerleştirildi.
4. 04:48 – 05:06: Fuji Dağı Hatası -> 14. Cadde Köprüsü yerine çıkan karlı Fuji Dağı kaldırıldı;
   resmi NTSB köprü çarpışma şeması ve karda kilitlenen Washington köprü trafiği yerleştirildi.
5. 05:06 – 05:30: Alpler/Himalayalar Dağı Hatası -> Potomac Nehri anlatılırken çıkan dağ kaldırıldı;
   Rochambeau köprü korkuluğu enkazı ve donmuş Potomac'taki kuyruk arşiv fotoğrafları yerleştirildi.
6. 05:30 – 05:46: Pembe Kiraz Çiçekleri (Sakura) Hatası -> Kar fırtınasında kaybolan uçak aranırken
   çıkan pembe çiçekler kaldırıldı; 2D DCA Washington Kulesi telsiz arama ve radar skopu yerleştirildi.
7. 05:20 ve 05:52 – 06:07: NTSB Başlık Çakışması -> Sarı başlık ile mavi kurum yazısı arasındaki
   üst üste binme giderildi; sağa yaslı temiz NTSB resmi kaza tahkikat paneli yerleştirildi.
"""

import os
import sys
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# imageio_ffmpeg binary yolunu al (libass & subtitles desteği için)
FFMPEG_SUB = BASE_DIR / ".venv/lib/python3.14/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
if not FFMPEG_SUB.exists():
    FFMPEG_SUB = Path(shutil.which("ffmpeg") or "ffmpeg")

FFMPEG = str(FFMPEG_SUB)

VIDEO_DIR = BASE_DIR / "output/blackboxaudioo/kontrol/20261018_Air_Florida_90"
SRC_VIDEO = VIDEO_DIR / "final.mp4"
BACKUP_VIDEO = VIDEO_DIR / "final_original_backup.mp4"
SRT_FILE = VIDEO_DIR / "subtitles.srt"

W, H, FPS = 1920, 1080, 25

from src.aviation_stickman_composite import (
    get_font,
    generate_animated_atc_video,
    generate_animated_investigation_video
)
from src.video_scene_patcher import render_cockpit_alarm_frame, _draw_hud_overlay


def slice_srt(srt_path: Path, start_sec: float, end_sec: float, out_path: Path) -> bool:
    """Altyazı dosyasından belirtilen zaman aralığını göreceli zaman damgasıyla dilimler."""
    if not srt_path.exists():
        return False
    import re
    raw = srt_path.read_text(encoding="utf-8", errors="ignore")
    blocks = raw.strip().split("\n\n")
    out_blocks = []
    idx = 1

    def fmt_srt(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    for b in blocks:
        lines = b.strip().split("\n")
        if len(lines) >= 3:
            m = re.match(r"(\d+):(\d+):(\d+)[,\.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,\.](\d+)", lines[1])
            if m:
                s = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int(m.group(4))/1000.0
                e = int(m.group(5))*3600 + int(m.group(6))*60 + int(m.group(7)) + int(m.group(8))/1000.0
                if e > start_sec and s < end_sec:
                    rel_s = max(0.0, s - start_sec)
                    rel_e = min(end_sec - start_sec, e - start_sec)
                    if rel_e > rel_s:
                        text = "\n".join(lines[2:])
                        out_blocks.append(f"{idx}\n{fmt_srt(rel_s)} --> {fmt_srt(rel_e)}\n{text}")
                        idx += 1

    if out_blocks:
        out_path.write_text("\n\n".join(out_blocks) + "\n", encoding="utf-8")
        return True
    return False


def make_kenburns_clip(img_path: Path, out_path: Path, duration: float, title_badge: str = "", sub_badge: str = "") -> Path:
    """Görseli Ken Burns kamera hareketi ve HUD etiketi ile videoya dönüştürür."""
    # Önce HUD overlay uygula
    im = Image.open(img_path).convert("RGB")
    im_scaled = im.resize((W, H), Image.Resampling.LANCZOS)
    if title_badge:
        draw = ImageDraw.Draw(im_scaled)
        draw.rectangle([(60, 40), (W - 60, 95)], fill=(10, 16, 26, 220))
        draw.rectangle([(60, 40), (W - 60, 95)], outline=(0, 200, 255), width=2)
        draw.text((80, 52), title_badge, font=get_font(22, True), fill=(255, 215, 0))
        if sub_badge:
            draw.text((W - 600, 56), sub_badge, font=get_font(18, True), fill=(0, 220, 255))

    temp_img = out_path.parent / f"framed_{img_path.name}"
    im_scaled.save(temp_img, "JPEG", quality=95)

    total_f = max(25, int(duration * FPS))
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},zoompan=z='min(zoom+0.0006,1.06)':x='iw/2-(iw/zoom/2)+sin(in/35)*30':y='ih/2-(ih/zoom/2)':d={total_f}:s={W}x{H}:fps={FPS}"
    cmd = [
        FFMPEG, "-y",
        "-loop", "1",
        "-i", str(temp_img),
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
        str(out_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    temp_img.unlink(missing_ok=True)
    return out_path


def format_video_clip(src_video: Path, out_path: Path, duration: float, title_badge: str = "") -> Path:
    """Video dosyasını ölçekleyip belirtilen süreye keser ve HUD ekler."""
    vf_parts = [
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
        f"fps={FPS}"
    ]
    if title_badge:
        # drawtext filtresi
        vf_parts.append(
            f"drawbox=x=60:y=40:w={W-120}:h=55:color=black@0.7:t=fill,"
            f"drawbox=x=60:y=40:w={W-120}:h=55:color=0x00c8ff:t=2,"
            f"drawtext=text='{title_badge}':x=80:y=52:fontsize=22:fontcolor=0xffd700:fontfile='/System/Library/Fonts/Supplemental/Arial Bold.ttf'"
        )

    cmd = [
        FFMPEG, "-y",
        "-stream_loop", "-1",
        "-i", str(src_video),
        "-t", f"{duration:.3f}",
        "-vf", ",".join(vf_parts),
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
        str(out_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def main():
    print("=" * 80)
    print("🚀 AIR FLORIDA 90: MASTER YAMA & KUSURSUZ KURGU İŞLEMİ BAŞLATILIYOR")
    print("=" * 80)

    work_dir = Path(tempfile.mkdtemp(prefix="af90_masterpiece_"))
    print(f"📁 Çalışma Dizini: {work_dir}")

    # Toplam süre kontrolü
    ffprobe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(SRC_VIDEO)
    ]
    total_dur = float(subprocess.run(ffprobe_cmd, capture_output=True, text=True).stdout.strip())
    print(f"⏱️ Video Toplam Süre: {total_dur:.2f} saniye")

    # 1. BÖLÜM: 0.00 -> 225.00s (03:45) Orijinal ve Kusursuz CVR Bölümü (Korunuyor)
    print("\n[BÖLÜM 0] 00:00 - 03:45 Orijinal Video (Düzeltilen CVR ve EPR bölümü) kesiliyor...")
    base_clip = work_dir / "part_00_base.mp4"
    cmd_base = [
        FFMPEG, "-y",
        "-ss", "0",
        "-to", "225.0",
        "-i", str(SRC_VIDEO),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-video_track_timescale", "12800",
        str(base_clip)
    ]
    subprocess.run(cmd_base, check=True, capture_output=True)
    print(f"✓ Part 0 hazır ({base_clip.name})")

    # Yamalanacak 8 Segmente Dair Plan
    segments_plan = [
        # 1. Pistte Hızlanma & Kokpit (03:45 - 04:12 = 27.0s) -> Kronoloji Düzeltildi
        {
            "id": "seg_01_takeoff_roll",
            "start": 225.0,
            "end": 252.0,
            "dur": 27.0,
            "name": "Boeing 737 Kokpit & Pist Hızlanma (V1 / Vr)",
            "type": "custom_composite"
        },
        # 2. Stall Warning & Stick Shaker (04:12 - 04:25 = 13.0s) -> 04:18 Flash frame glitch YOK EDİLDİ
        {
            "id": "seg_02_stall_alarm",
            "start": 252.0,
            "end": 265.0,
            "dur": 13.0,
            "name": "Stall Warning / Stick Shaker Cockpit Master Warning",
            "type": "cockpit_alarm"
        },
        # 3. İrtifa Dalış & Taktik Rota Haritası (04:25 - 04:48 = 23.0s) -> Tekrarlanan EPR kaldırıldı
        {
            "id": "seg_03_trajectory_radar",
            "start": 265.0,
            "end": 288.0,
            "dur": 23.0,
            "name": "DCA Pist 36 -> 14th St Köprüsü FDR İrtifa Dalış Haritası",
            "type": "trajectory_map"
        },
        # 4. 14. Cadde Köprüsü Şeması & Kış Trafiği (04:48 - 05:06 = 18.0s) -> Fuji Dağı YOK EDİLDİ
        {
            "id": "seg_04_bridge_impact",
            "start": 288.0,
            "end": 306.0,
            "dur": 18.0,
            "name": "NTSB 14. Cadde Köprüsü Çarpışma Şeması & Kış Trafiği",
            "type": "bridge_composite"
        },
        # 5. Köprüye Çarpışma & Donmuş Potomac'ta Kuyruk (05:06 - 05:30 = 24.0s) -> Alpler YOK EDİLDİ
        {
            "id": "seg_05_potomac_impact",
            "start": 306.0,
            "end": 330.0,
            "dur": 24.0,
            "name": "Potomac Nehri Buz Kütleleri & Air Florida Kuyruk Enkazı",
            "type": "potomac_tail_composite"
        },
        # 6. Kule Arama & Telsiz Sessizliği (05:30 - 05:46 = 16.0s) -> Pembe Kiraz Çiçekleri YOK EDİLDİ
        {
            "id": "seg_06_atc_tower",
            "start": 330.0,
            "end": 346.0,
            "dur": 16.0,
            "name": "2D DCA Kule Kontrolörü & Radar Temas Kaybı",
            "type": "atc_animation"
        },
        # 7. Park Police Helikopter Kurtarma (05:46 - 05:52 = 6.0s) -> Doğru Zamana Kaydırıldı
        {
            "id": "seg_07_heli_rescue",
            "start": 346.0,
            "end": 352.0,
            "dur": 6.0,
            "name": "US Park Police Potomac Buz Kurtarma Operasyonu",
            "type": "heli_rescue"
        },
        # 8. Resmi NTSB Kaza Raporu (05:52 - 06:07.13 = 15.13s) -> Başlık Çakışması YOK EDİLDİ
        {
            "id": "seg_08_ntsb_final",
            "start": 352.0,
            "end": total_dur,
            "dur": round(total_dur - 352.0, 3),
            "name": "2D NTSB Kaza Tahkikat Rapor Paneli (Temiz Başlık)",
            "type": "ntsb_animation"
        }
    ]

    parts_to_concat = [base_clip]

    for p_idx, plan in enumerate(segments_plan, 1):
        s_time, e_time, dur = plan["start"], plan["end"], plan["dur"]
        print(f"\n[BÖLÜM {p_idx}/8] {plan['name']} ({s_time:.1f}s - {e_time:.1f}s, {dur:.2f}s)...")

        # 1. Sesi orijinal videodan çıkar
        seg_audio = work_dir / f"audio_{plan['id']}.aac"
        cmd_aud = [
            FFMPEG, "-y",
            "-ss", str(s_time),
            "-to", str(e_time),
            "-i", str(SRC_VIDEO),
            "-vn", "-c:a", "aac", "-b:a", "192k",
            str(seg_audio)
        ]
        subprocess.run(cmd_aud, check=True, capture_output=True)

        # 2. İlgili görsel/video varlığını oluştur
        raw_video = work_dir / f"raw_video_{plan['id']}.mp4"

        if plan["type"] == "custom_composite":
            # 03:45 - 04:12 (27s): Kokpit göstergeleri (14s) + Lövye hareketleri (13s)
            c1 = work_dir / "c1_cockpit.mp4"
            make_kenburns_clip(
                BASE_DIR / "scratch/test_af_assets/af_b737_cockpit.jpg",
                c1, 14.0,
                title_badge="COCKPIT FLIGHT INSTRUMENTS // AIR FLORIDA 90",
                sub_badge="TAKEOFF ROLL: DCA RUNWAY 36 // TARGET EPR: 2.04"
            )
            c2 = work_dir / "c2_yoke.mp4"
            format_video_clip(
                BASE_DIR / "scratch/test_af_assets/cockpit_yoke_video.mp4",
                c2, 13.0,
                title_badge="CREW ACCELERATION DOUBTS // V1 - Vr ROTATION ADVANCE"
            )
            # Concat c1 + c2
            sub_concat = work_dir / "takeoff_list.txt"
            sub_concat.write_text(f"file '{c1.resolve()}'\nfile '{c2.resolve()}'\n")
            cmd_c = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(sub_concat), "-c", "copy", str(raw_video)]
            subprocess.run(cmd_c, check=True, capture_output=True)

        elif plan["type"] == "cockpit_alarm":
            # 04:12 - 04:25 (13s): Stall warning HUD (Flashing Alarm)
            alarm_png = work_dir / "stall_alarm_frame.png"
            render_cockpit_alarm_frame(
                flight_name="AIR FLORIDA FLIGHT 90",
                alarm_text="STALL WARNING // STICK SHAKER ACTIVE // PULL UP!",
                altitude_ft=350,
                output_path=str(alarm_png)
            )
            # Yanıp sönen kırmızı uyarı kutusu efekti
            cmd_alarm = [
                FFMPEG, "-y",
                "-loop", "1", "-i", str(alarm_png),
                "-t", f"{dur:.3f}",
                "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                str(raw_video)
            ]
            subprocess.run(cmd_alarm, check=True, capture_output=True)

        elif plan["type"] == "trajectory_map":
            # 04:25 - 04:48 (23s): DCA Runway 36 -> 14th St Bridge FDR Telemetry Map
            make_kenburns_clip(
                BASE_DIR / "scratch/air_florida_trajectory_map.png",
                raw_video, dur,
                title_badge="TACTICAL FDR FLIGHT PATH // PEAK ALTITUDE: 352 FT",
                sub_badge="CRITICAL DESCENT INTO POTOMAC RIVER BASIN"
            )

        elif plan["type"] == "bridge_composite":
            # 04:48 - 05:06 (18s): NTSB köprü şeması (10s) + Kış trafiği (8s)
            b1 = work_dir / "b1_diagram.mp4"
            make_kenburns_clip(
                BASE_DIR / "scratch/test_af_assets/af_bridge_impact_diagram.jpg",
                b1, 10.0,
                title_badge="OFFICIAL NTSB CRASH PROFILE // 14TH STREET BRIDGE",
                sub_badge="COLLISION WITH OCCUPIED VEHICLES ON ROCHAMBEAU SPAN"
            )
            b2 = work_dir / "b2_traffic.mp4"
            format_video_clip(
                BASE_DIR / "scratch/test_af_assets/winter_traffic_video.mp4",
                b2, 8.0,
                title_badge="RUSH-HOUR TRAFFIC STRANDED IN SEVERE SNOWSTORM"
            )
            sub_concat = work_dir / "bridge_list.txt"
            sub_concat.write_text(f"file '{b1.resolve()}'\nfile '{b2.resolve()}'\n")
            cmd_b = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(sub_concat), "-c", "copy", str(raw_video)]
            subprocess.run(cmd_b, check=True, capture_output=True)

        elif plan["type"] == "potomac_tail_composite":
            # 05:06 - 05:30 (24s): Köprü enkazı (12s) + Potomac kuyruk (12s)
            t1 = work_dir / "t1_debris.mp4"
            make_kenburns_clip(
                BASE_DIR / "scratch/test_af_assets/af_bridge_debris_boat.jpg",
                t1, 12.0,
                title_badge="POTOMAC RIVER ROCHAMBEAU SPAN // 40 FT RAILING TORN AWAY",
                sub_badge="AIRCRAFT IMPACT SPEED: 130 KNOTS"
            )
            t2 = work_dir / "t2_tail.mp4"
            make_kenburns_clip(
                BASE_DIR / "scratch/test_af_assets/af_potomac_tail.jpg",
                t2, 12.0,
                title_badge="POTOMAC RIVER WRECKAGE // AIR FLORIDA 90 TAIL SECTION",
                sub_badge="AIRCRAFT SUBMERGED IN 16 FT FREEZING WATER"
            )
            sub_concat = work_dir / "tail_list.txt"
            sub_concat.write_text(f"file '{t1.resolve()}'\nfile '{t2.resolve()}'\n")
            cmd_t = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(sub_concat), "-c", "copy", str(raw_video)]
            subprocess.run(cmd_t, check=True, capture_output=True)

        elif plan["type"] == "atc_animation":
            # 05:30 - 05:46 (16s): 2D DCA Kuleci Animasyonu
            generate_animated_atc_video(
                flight_name="AIR FLORIDA 90",
                atc_station="WASHINGTON NATIONAL TOWER (DCA)",
                atc_call="Palm 90, contact Washington Departure on 118.3. Radar contact lost.",
                altitude_reported="LAST SEEN: 350 FT -> NO CLIMB",
                squawk_code="SQUAWK 7700 (EMERGENCY)",
                duration=dur,
                output_path=str(raw_video)
            )

        elif plan["type"] == "heli_rescue":
            # 05:46 - 05:52 (6s): US Park Police Helikopter Kurtarma
            make_kenburns_clip(
                BASE_DIR / "scratch/test_af_assets/af_heli_search.jpg",
                raw_video, dur,
                title_badge="POTOMAC ICE FLOES // US PARK POLICE HEROIC RESCUE",
                sub_badge="SURVIVORS RESCUED FROM 30-DEGREE WATER"
            )

        elif plan["type"] == "ntsb_animation":
            # 05:52 - 06:07 (15.13s): 2D NTSB Müfettiş Rapor Paneli (Temiz Başlık)
            generate_animated_investigation_video(
                flight_name="AIR FLORIDA 90",
                investigating_agency="NTSB (WASHINGTON DC)",
                primary_finding="Failure to activate engine anti-ice causing iced PT2 pressure probes, false high EPR indications, and premature stall.",
                critical_factors=[
                    ("ENGINE ANTI-ICE DEACTIVATED", "Crew checklist execution failed to activate thermal anti-ice in blizzard"),
                    ("FALSE 2.04 EPR READING", "Blocked PT2 probe indicated target takeoff power at only 70% actual thrust"),
                    ("WING SNOW ACCUMULATION", "Rough snow contamination on leading edge caused premature aerodynamic stall"),
                    ("NO REJECTED TAKEOFF", "Crew failed to reject takeoff despite co-pilot noticing abnormal acceleration")
                ],
                duration=dur,
                output_path=str(raw_video)
            )

        # 3. Altyazıları dilimle ve videoya giydir
        slice_srt_path = work_dir / f"slice_{plan['id']}.srt"
        has_sub = slice_srt(SRT_FILE, s_time, e_time, slice_srt_path)

        final_seg_clip = work_dir / f"final_{plan['id']}.mp4"

        vf_final = [
            f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
            f"fps={FPS}",
            "setsar=1"
        ]
        if has_sub:
            vf_final.append(
                f"subtitles={slice_srt_path}:force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2.5,MarginV=48'"
            )

        cmd_synth = [
            FFMPEG, "-y",
            "-i", str(raw_video),
            "-i", str(seg_audio),
            "-t", f"{dur:.3f}",
            "-vf", ",".join(vf_final),
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-video_track_timescale", "12800",
            "-shortest",
            str(final_seg_clip)
        ]
        subprocess.run(cmd_synth, check=True, capture_output=True)
        parts_to_concat.append(final_seg_clip)
        print(f"✓ {plan['id']} başarıyla derlendi.")

    # 4. Tüm parçaları birleştir (Seamless Concat)
    print("\n🎬 Tüm bölümler (03:45 öncesi + 8 yeni kusursuz bölüm) birleştiriliyor...")
    concat_txt = work_dir / "master_concat.txt"
    concat_txt.write_text("".join([f"file '{p.resolve()}'\n" for p in parts_to_concat]))

    master_out = work_dir / "final_masterpiece.mp4"
    cmd_merge = [
        FFMPEG, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(master_out)
    ]
    subprocess.run(cmd_merge, check=True, capture_output=True)

    # 5. Sonuç Süre ve Doğrulama
    ffprobe_fin = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(master_out)
    ]
    final_dur = float(subprocess.run(ffprobe_fin, capture_output=True, text=True).stdout.strip())
    print(f"✅ Yeni Video Başarıyla Üretildi! Toplam Süre: {final_dur:.2f} saniye (Orijinal: {total_dur:.2f}s)")

    # 6. final.mp4 ve video.mp4 dosyalarını güncelle
    shutil.copy2(str(master_out), str(SRC_VIDEO))
    alt_video = VIDEO_DIR / "video.mp4"
    if alt_video.exists():
        shutil.copy2(str(master_out), str(alt_video))
    print(f"📦 final.mp4 ve video.mp4 güncellendi: {SRC_VIDEO}")

    # 7. Doğrulama karelerini çıkar
    print("\n📸 Doğrulama kareleri çıkarılıyor...")
    verify_dir = VIDEO_DIR / "_qa_frames_verified"
    verify_dir.mkdir(parents=True, exist_ok=True)

    check_timestamps = [
        ("03_50_takeoff_cockpit", "03:50"),
        ("04_02_takeoff_yoke", "04:02"),
        ("04_18_stall_alarm_no_flash", "04:18.5"),
        ("04_30_trajectory_dive_map", "04:30"),
        ("04_58_bridge_impact_no_fuji", "04:58"),
        ("05_15_bridge_debris", "05:15"),
        ("05_24_potomac_tail_no_alps", "05:24"),
        ("05_38_atc_tower_no_sakura", "05:38"),
        ("05_48_heli_rescue_accurate", "05:48"),
        ("05_58_ntsb_clean_no_overlap", "05:58")
    ]

    for name, ts in check_timestamps:
        out_f = verify_dir / f"{name}.jpg"
        cmd_f = [
            FFMPEG, "-y",
            "-ss", ts,
            "-i", str(SRC_VIDEO),
            "-vframes", "1",
            str(out_f)
        ]
        subprocess.run(cmd_f, capture_output=True)
        print(f"  • {ts} -> {out_f.name}")

    # Temizlik
    shutil.rmtree(work_dir, ignore_errors=True)
    print("\n🎉 MASTER YAMA VE KURGU TAMAMLANDI!")


if __name__ == "__main__":
    main()
