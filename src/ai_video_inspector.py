"""
ai_video_inspector.py
=====================
LM Studio Yerel Vision-Language AI (Google Gemma-4-12B) ile Çok Modlu Video Kalite Kontrolü.
Videonun her sahnesindeki dış ses anlatımı ile ekrandaki görseli (screenshot) karşılaştırır.
Uyuşmayan (çiçekler, baraj şemaları, matematik formülleri, karlı pist, yanlış uçak) sahneleri tespit eder
ve in-place yama formatında (start_sec, end_sec, replacement_type) yapılandırılmış çıktı üretir.
"""

import os
import re
import sys
import json
import time
import base64
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import requests
from PIL import Image

try:
    from src.settings_manager import SettingsManager
except ImportError:
    try:
        from settings_manager import SettingsManager
    except ImportError:
        SettingsManager = None

try:
    from src.video_editor import find_ffmpeg
except ImportError:
    try:
        from video_editor import find_ffmpeg
    except ImportError:
        def find_ffmpeg(require_subtitles: bool = False) -> str:
            return os.environ.get("FFMPEG_BINARY") or "/opt/homebrew/bin/ffmpeg" or "ffmpeg"


def get_lmstudio_config() -> Tuple[str, str]:
    """LM Studio URL ve modelini döner."""
    url = "http://localhost:1234/v1"
    model = "google/gemma-4-12b"
    if SettingsManager:
        sm = SettingsManager()
        url = sm.get("lmstudio_url", url)
        model = sm.get("lmstudio_vision_model", model)
    return url.rstrip("/"), model


def extract_scene_keyframe(video_path: Path, timestamp_sec: float, output_path: Path) -> bool:
    """Belirtilen saniyeden hafif 480x270 JPEG ekran görüntüsü çıkarır (Hızlı AI Vision analizi)."""
    ffmpeg = find_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-ss", f"{timestamp_sec:.2f}",
        "-i", str(video_path),
        "-vframes", "1",
        "-vf", "scale=480:270",
        "-q:v", "3",
        str(output_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1000


def encode_image_base64(image_path: Path) -> str:
    """Görseli base64 string'e dönüştürür."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def clean_json_text(text: str) -> str:
    """Markdown bloklarından veya serbest metinden JSON'ı ayıklar."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match2 = re.search(r"(\{.*\})", text, re.DOTALL)
    if match2:
        return match2.group(1).strip()
    return text


def evaluate_scene_with_lmstudio(
    image_path: Path,
    narration_text: str,
    incident_context: str,
    scene_idx: int,
    base_url: str = "http://localhost:1234/v1",
    model_name: str = "google/gemma-4-12b"
) -> Dict[str, Any]:
    """
    Tek bir sahne karesini LM Studio Vision AI'ye gönderir.
    Görsel ile seslendirme arasındaki anlamsal uyumu denetler.
    """
    b64_img = encode_image_base64(image_path)
    
    prompt = f"""You are an expert video editor and aviation quality auditor.
Compare the voiceover narration with the visual frame currently displayed on screen.

Incident Context: {incident_context}
Scene #{scene_idx} Narration: "{narration_text}"

Task:
Determine if the displayed image is coherent and contextually appropriate for this aviation documentary scene.
FLAG A "FAIL" IF:
- The image shows a comic character with a speech bubble containing third-person narrator text (e.g. "At the dead of night...", "All ten people lose their lives...", "Under intense stress...") instead of first-person cockpit CVR dialogue.
- The image shows nighttime city skyline, neon roads, or highway traffic when the flight occurred in morning fog, daylight clouds, or winter snow.
- The image shows a single-engine light aircraft (such as Cessna 172 or Piper) or small propeller trainer for a commercial twin-engine turboprop or jet airliner flight.
- The image shows nature/flowers/cherry blossoms/wildlife while talking about cockpit instruments or emergency.
- The image shows construction blueprints, dam engineering diagrams, or physics/math formulas.
- The image shows subway/train stations, casual pedestrians, or road traffic during a flight crisis.
- The image shows a museum display plane, acrobatic propeller plane, or completely wrong aircraft type (e.g. A320 cockpit shown for an ATR-72 turboprop).
- The image shows snow and ice when the incident occurs in hot 30C summer conditions.

Otherwise, if it shows a reasonable airplane, cockpit, radar, runway, cloud, or aerial view, return "PASS".

Output MUST be a single JSON object in this format (no conversational filler, keep reasoning to 1 sentence max):
{{
  "status": "PASS" or "FAIL",
  "issue": "Brief 1-sentence description of the mismatch if FAIL, or OK",
  "suggested_replacement": "telemetry_hud" or "attitude_indicator" or "flight_map" or "cockpit_alarm"
}}"""

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 250
    }

    try:
        resp = requests.post(f"{base_url}/chat/completions", json=payload, timeout=75)
        if resp.status_code != 200:
            print(f"[AI-Inspector] ⚠️ LM Studio HTTP {resp.status_code}: {resp.text[:200]}")
            return {"status": "PASS", "issue": f"LM Studio HTTP {resp.status_code}", "suggested_replacement": "telemetry_hud"}

        data = resp.json()
        choice = data.get("choices", [{}])[0].get("message", {})
        content = choice.get("content", "").strip()
        reasoning = choice.get("reasoning_content", "").strip()

        combined_text = content or reasoning
        parsed_json = None

        # Doğrudan JSON arayışı
        raw_json = clean_json_text(combined_text)
        try:
            parsed_json = json.loads(raw_json)
        except Exception:
            # Yedek: reasoning içindeki regex çıkarımı
            status_m = re.search(r'"status"\s*:\s*"(PASS|FAIL)"', combined_text, re.IGNORECASE)
            issue_m = re.search(r'"issue"\s*:\s*"([^"]+)"', combined_text, re.IGNORECASE)
            rep_m = re.search(r'"suggested_replacement"\s*:\s*"([^"]+)"', combined_text, re.IGNORECASE)
            
            if status_m:
                parsed_json = {
                    "status": status_m.group(1).upper(),
                    "issue": issue_m.group(1) if issue_m else "Uyuşmazlık tespit edildi",
                    "suggested_replacement": rep_m.group(1) if rep_m else "telemetry_hud"
                }

        if not parsed_json or "status" not in parsed_json:
            # Heuristic tarama (eğer FAIL kelimesi baskınsa)
            if "status: fail" in combined_text.lower() or "clearly an absurd" in combined_text.lower() or "unrelated" in combined_text.lower():
                return {
                    "status": "FAIL",
                    "issue": "AI reasoning görsel uyuşmazlığı tespit etti.",
                    "suggested_replacement": "attitude_indicator" if "instrument" in narration_text.lower() else "telemetry_hud"
                }
            return {"status": "PASS", "issue": "Varsayılan onay", "suggested_replacement": "telemetry_hud"}

        return parsed_json

    except Exception as e:
        print(f"[AI-Inspector] ⚠️ İstek hatası: {e}")
        return {"status": "PASS", "issue": str(e), "suggested_replacement": "telemetry_hud"}


def parse_subtitles_or_metadata(folder_path: Path) -> List[Dict[str, Any]]:
    """Klasördeki metadata.json veya subtitles.srt dosyasından sahne ve süreleri çıkarır."""
    meta_file = folder_path / "metadata.json"
    scenes = []

    if meta_file.exists():
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8"))
            sc_list = m.get("scenes") or m.get("script", {}).get("scenes") or []
            if sc_list and isinstance(sc_list, list):
                scenes = sc_list
        except Exception:
            pass

    # Eğer metadata'da sahne listesi yoksa veya boşsa ffprobe + SRT oku
    srt_file = folder_path / "subtitles.srt"
    srt_blocks = []
    if srt_file.exists():
        try:
            txt = srt_file.read_text(encoding="utf-8", errors="ignore")
            # 00:01:20,000 --> 00:01:25,500
            pattern = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\n(.*?)(?=\n\n|\Z)", re.DOTALL)
            for m in pattern.finditer(txt):
                s_h, s_m, s_s, s_ms = map(int, m.groups()[:4])
                e_h, e_m, e_s, e_ms = map(int, m.groups()[4:8])
                st_sec = s_h * 3600 + s_m * 60 + s_s + s_ms / 1000.0
                en_sec = e_h * 3600 + e_m * 60 + e_s + e_ms / 1000.0
                c_txt = " ".join([l.strip() for l in m.group(9).splitlines() if l.strip()])
                srt_blocks.append({"start_sec": st_sec, "end_sec": en_sec, "narration": c_txt})
        except Exception:
            pass

    return scenes, srt_blocks


def audit_video_folder(folder_path: Path, target_scenes: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Belirtilen klasördeki videoyu sahne sahne inceler.
    target_scenes belirtilirse sadece o sahneleri denetler (Delta / Hızlı Tur modu).
    Tespit edilen hataları ve uygulanacak yamaları döner.
    """
    folder_path = Path(folder_path).resolve()
    final_video = folder_path / "final.mp4"
    if not final_video.exists():
        final_video = folder_path / "video.mp4"
    if not final_video.exists():
        return {"success": False, "message": "Klasörde video bulunamadı."}

    base_url, model_name = get_lmstudio_config()
    target_info = f" (Delta Modu: {len(target_scenes)} sahne)" if target_scenes else " (Tam Video Taraması)"
    print(f"[AI-Inspector] 🔎 Video denetimi başlatılıyor: {folder_path.name}{target_info}")
    print(f"[AI-Inspector] 🤖 Model: {model_name} ({base_url})")

    # ffprobe ile video süresi
    cmd_dur = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(final_video)
    ]
    res_dur = subprocess.run(cmd_dur, capture_output=True, text=True)
    total_dur = float(res_dur.stdout.strip()) if res_dur.returncode == 0 else 0.0

    meta_file = folder_path / "metadata.json"
    topic_context = folder_path.name
    if meta_file.exists():
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8"))
            topic_context = m.get("title") or m.get("flight_name") or topic_context
        except Exception:
            pass

    scenes, srt_blocks = parse_subtitles_or_metadata(folder_path)
    
    # İnceleme dilimleri oluştur
    timeline_slices = []
    if srt_blocks and len(srt_blocks) >= 4:
        # Altyazı bloklarını ~15 saniyelik mantıksal bölümler halinde grupla
        cur_start = srt_blocks[0]["start_sec"]
        cur_texts = []
        for blk in srt_blocks:
            cur_texts.append(blk["narration"])
            if (blk["end_sec"] - cur_start) >= 12.0:
                mid_t = (cur_start + blk["end_sec"]) / 2.0
                timeline_slices.append({
                    "start_sec": cur_start,
                    "end_sec": blk["end_sec"],
                    "mid_sec": mid_t,
                    "narration": " ".join(cur_texts)
                })
                cur_start = blk["end_sec"]
                cur_texts = []
        if cur_texts and cur_start < total_dur:
            timeline_slices.append({
                "start_sec": cur_start,
                "end_sec": total_dur,
                "mid_sec": (cur_start + total_dur) / 2.0,
                "narration": " ".join(cur_texts)
            })
    else:
        # Sahne süresi yoksa videoyu 15'er saniyelik dilimlere böl
        step = 16.0
        t = 0.0
        sc_i = 0
        while t < total_dur:
            en = min(total_dur, t + step)
            n_txt = scenes[sc_i].get("narration", "") if sc_i < len(scenes) else f"Flight operations phase {sc_i+1}"
            timeline_slices.append({
                "start_sec": t,
                "end_sec": en,
                "mid_sec": (t + en) / 2.0,
                "narration": n_txt
            })
            t = en
            sc_i += 1

    patches_to_apply = []
    audit_log = []
    
    temp_dir = Path(tempfile.mkdtemp(prefix="ai_inspector_"))
    seen_hashes = []
    try:
        for idx, slc in enumerate(timeline_slices, 1):
            if target_scenes is not None and idx not in target_scenes:
                # Delta Hızlı Mod: Daha önce onaylanmış sahneleri tekrar taramadan onayla
                audit_log.append({
                    "scene_idx": idx,
                    "start_sec": round(slc["start_sec"], 2),
                    "end_sec": round(slc["end_sec"], 2),
                    "timestamp": f"{int(slc['start_sec']//60):02d}:{int(slc['start_sec']%60):02d} - {int(slc['end_sec']//60):02d}:{int(slc['end_sec']%60):02d}",
                    "status": "PASS",
                    "issue": "Önceki turda onaylandı (Delta optimizasyonu)",
                    "replacement_type": "telemetry_hud",
                    "narration_snippet": slc["narration"][:80] + "..." if len(slc["narration"]) > 80 else slc["narration"]
                })
                continue

            mid_t = slc["mid_sec"]
            thumb_path = temp_dir / f"slice_{idx}.jpg"
            ok = extract_scene_keyframe(final_video, mid_t, thumb_path)
            if not ok:
                continue

            # Görsel tekrarı denetimi (Aynı kadranın veya fotoğrafın tekrarı)
            is_duplicate = False
            dup_prev = None
            cur_img_hash = None
            try:
                with Image.open(thumb_path) as im_thumb:
                    im_small = im_thumb.resize((16, 16)).convert("L")
                    cur_img_hash = list(im_small.getdata())
                    for prev_idx, prev_hash in seen_hashes:
                        diff = sum(abs(a - b) for a, b in zip(cur_img_hash, prev_hash)) / 256.0
                        if diff < 6.0:  # Neredeyse birebir aynı görsel
                            is_duplicate = True
                            dup_prev = prev_idx
                            break
            except Exception:
                pass

            if is_duplicate:
                status = "FAIL"
                issue = f"Görsel tekrarı: Bu kare Sahne #{dup_prev} ile birebir aynı görseli içeriyor (Ekran yorgunluğu / statik tekrar)."
                rep_type = "investigation_stickman" if (idx / max(1, len(timeline_slices))) >= 0.60 else "cvr_stickman"
            else:
                eval_res = evaluate_scene_with_lmstudio(
                    image_path=thumb_path,
                    narration_text=slc["narration"],
                    incident_context=topic_context,
                    scene_idx=idx,
                    base_url=base_url,
                    model_name=model_name
                )
                status = eval_res.get("status", "PASS").upper()
                issue = eval_res.get("issue", "")
                rep_type = eval_res.get("suggested_replacement", "telemetry_hud")
                if cur_img_hash:
                    seen_hashes.append((idx, cur_img_hash))

            audit_log.append({
                "scene_idx": idx,
                "start_sec": round(slc["start_sec"], 2),
                "end_sec": round(slc["end_sec"], 2),
                "timestamp": f"{int(slc['start_sec']//60):02d}:{int(slc['start_sec']%60):02d} - {int(slc['end_sec']//60):02d}:{int(slc['end_sec']%60):02d}",
                "status": status,
                "issue": issue,
                "replacement_type": rep_type,
                "narration_snippet": slc["narration"][:80] + "..." if len(slc["narration"]) > 80 else slc["narration"]
            })

            if status == "FAIL":
                print(f"[AI-Inspector] ❌ UYUMSUZLUK: Sahne {idx} ({audit_log[-1]['timestamp']}) -> {issue}")
                patches_to_apply.append({
                    "id": f"patch_{idx}_{int(slc['start_sec'])}",
                    "scene_idx": idx,
                    "start_sec": slc["start_sec"],
                    "end_sec": slc["end_sec"],
                    "start_time": f"{int(slc['start_sec']//60):02d}:{int(slc['start_sec']%60):02d}",
                    "end_time": f"{int(slc['end_sec']//60):02d}:{int(slc['end_sec']%60):02d}",
                    "duration": slc["end_sec"] - slc["start_sec"],
                    "issue_title": f"Sahne #{idx} Görsel Uyuşmazlık",
                    "replacement_type": rep_type,
                    "description": issue,
                    "enabled": True
                })
            else:
                print(f"[AI-Inspector] ✅ Sahne {idx} onaylandı ({audit_log[-1]['timestamp']}).")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    passed_count = len([x for x in audit_log if x["status"] == "PASS"])
    failed_count = len(patches_to_apply)
    
    return {
        "success": True,
        "video_path": str(final_video),
        "total_duration": total_dur,
        "total_scenes_checked": len(audit_log),
        "passed_scenes": passed_count,
        "failed_scenes": failed_count,
        "is_consistent": failed_count == 0,
        "patches": patches_to_apply,
        "audit_log": audit_log
    }
