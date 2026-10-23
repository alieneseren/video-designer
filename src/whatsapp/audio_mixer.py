import os
import subprocess
from pathlib import Path
from .models import Scenario
from .voice_profiles import BGM_TRACKS, SCENARIO_VOICE_MAP

def _resolve_whatsapp_assets_dir() -> Path:
    candidates = [
        Path("/home/ubuntu/yt-render-server/assets/whatsapp/assets"),
        Path(__file__).resolve().parent.parent / "assets" / "whatsapp" / "assets",
        Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets",
        Path("config/assets/whatsapp/assets").resolve()
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets"

BASE_ASSETS = _resolve_whatsapp_assets_dir()
DEFAULT_POP = str(BASE_ASSETS / "sfx" / "pop.wav")
DEFAULT_SWOOSH = str(BASE_ASSETS / "sfx" / "swoosh.wav")

class AudioMixer:
    def __init__(
        self,
        sfx_pop: str = DEFAULT_POP,
        sfx_swoosh: str = DEFAULT_SWOOSH,
        output_path: str = None
    ):
        self.sfx_pop = sfx_pop
        self.sfx_swoosh = sfx_swoosh
        self.output_path = output_path or "/tmp/whatsapp_audio/master_audio.wav"
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def _get_bgm_path(self, scenario: Scenario, scenario_name: str = "") -> str:
        if not scenario.bgm_enabled or getattr(scenario, "bgm_track", None) == "none":
            return None

        # 1. Doğrudan dosya yolu verilmişse
        track_val = getattr(scenario, "bgm_track", None)
        if track_val and os.path.exists(track_val):
            return track_val

        # 2. BGM_TRACKS içinde açık ve özel bir eşleşme (comedy_upbeat haricindeki spesifik seçimler)
        if track_val and track_val in BGM_TRACKS and track_val not in ("comedy_upbeat", "auto", "default"):
            track = BGM_TRACKS.get(track_val)
            if track and os.path.exists(track["path"]):
                return track["path"]

        # 3. Senaryo içeriğine göre akıllı / tematik fon müziği seçimi (Tekdüzeliği kırar)
        text_corpus = (
            f"{getattr(scenario, 'title', '')} "
            f"{getattr(scenario, 'contact_name', '')} "
            f"{scenario_name} "
            + " ".join(getattr(m, 'text', '') for m in (getattr(scenario, 'messages', []) or [])[:4])
        ).lower()

        candidate_key = None
        if any(k in text_corpus for k in ["ev sahibi", "sahip", "kira", "zam", "para", "patron", "müdür", "kıskanç", "merve", "aldat", "yakala"]):
            candidate_key = "cunning_scheme"
        elif any(k in text_corpus for k in ["odun", "romantik", "kız kulesi", "çay", "saf", "yemek", "mangal", "fark etmez"]):
            candidate_key = "silly_fun"
        elif any(k in text_corpus for k in ["anne", "baba", "valide", "peder", "aile", "okul", "sınav", "hoca", "ders", "kütüphane", "araba", "tampon"]):
            candidate_key = "viral_bounce"
        elif any(k in text_corpus for k in ["troll", "şaka", "kanka", "borç", "gizli", "ifşa", "ses kaydı", "grup", "düğün"]):
            candidate_key = "quirky_troll"
        elif any(k in text_corpus for k in ["chill", "lofi", "duygusal", "romantik", "gece", "hüzün"]):
            candidate_key = "lofi_chill"
        else:
            # Deterministic rotasyon: Her video farklı ve neşeli bir müzik alsın
            rotation = ["quirky_troll", "viral_bounce", "silly_fun", "cunning_scheme", "comedy_upbeat"]
            seed_val = abs(hash(getattr(scenario, 'title', 'whatsapp')))
            candidate_key = rotation[seed_val % len(rotation)]

        if candidate_key and candidate_key in BGM_TRACKS:
            cand_track = BGM_TRACKS[candidate_key]
            if cand_track and os.path.exists(cand_track["path"]):
                return cand_track["path"]

        # 4. Açık BGM_TRACKS eşlemesi
        if track_val and track_val in BGM_TRACKS:
            track = BGM_TRACKS.get(track_val)
            if track and os.path.exists(track["path"]):
                return track["path"]

        # 5. Senaryo haritasından alma
        voice_map = SCENARIO_VOICE_MAP.get(scenario_name, SCENARIO_VOICE_MAP.get("default", {}))
        bgm_key = voice_map.get("bgm", "quirky_troll")
        track = BGM_TRACKS.get(bgm_key, {})
        if track and os.path.exists(track.get("path", "")):
            return track["path"]

        # 6. Kütüphanedeki ilk geçerli parçayı fallback olarak kullan
        for key in ["quirky_troll", "viral_bounce", "silly_fun", "cunning_scheme", "comedy_upbeat", "lofi_chill"]:
            t = BGM_TRACKS.get(key)
            if t and os.path.exists(t.get("path", "")):
                return t["path"]

        # 7. BGM_DIR içindeki ilk mp3/wav dosyasını bul
        for cand in [
            BASE_ASSETS / "bgm" / "sneaky_snitch.mp3",
            BASE_ASSETS / "bgm" / "monkeys_spinning.mp3",
            BASE_ASSETS / "bgm" / "fluffing_duck.mp3",
            BASE_ASSETS / "bgm" / "comedy_upbeat.mp3"
        ]:
            if cand.exists():
                return str(cand)

        return None

    def mix_scenario_audio(self, scenario: Scenario, scenario_name: str = "", normalize_loudness: bool = True) -> tuple:
        if not scenario.messages:
            raise ValueError("Scenario has no messages to mix.")

        last_msg = scenario.messages[-1]
        total_duration = last_msg.bubble_appear_time + last_msg.audio_duration + 1.5

        bgm_path = self._get_bgm_path(scenario, scenario_name)

        input_args = []
        filter_parts = []
        mix_labels = []
        stream_idx = 0

        # Voice lines + SFX per message
        for i, msg in enumerate(scenario.messages):
            if not msg.audio_path or not os.path.exists(msg.audio_path):
                continue

            delay_ms = int(msg.bubble_appear_time * 1000)

            # Voice
            input_args += ["-i", msg.audio_path]
            filter_parts.append(
                f"[{stream_idx}:a]adelay={delay_ms}|{delay_ms},volume=1.3[v{i}]"
            )
            mix_labels.append(f"[v{i}]")
            stream_idx += 1

            # SFX
            sfx_file = self.sfx_pop if msg.sender == "contact" else self.sfx_swoosh
            if os.path.exists(sfx_file):
                input_args += ["-i", sfx_file]
                filter_parts.append(
                    f"[{stream_idx}:a]adelay={delay_ms}|{delay_ms},volume=0.7[sfx{i}]"
                )
                mix_labels.append(f"[sfx{i}]")
                stream_idx += 1

        # BGM — ducked under voices, fades out at end
        if scenario.bgm_enabled and bgm_path:
            input_args += ["-stream_loop", "-1", "-i", bgm_path]
            raw_vol = getattr(scenario, 'bgm_volume', 0.20)
            bgm_vol = max(float(raw_vol or 0.20), 0.18)
            
            filter_parts.append(
                f"[{stream_idx}:a]"
                f"atrim=0:{total_duration},"
                f"afade=t=in:st=0:d=1.0,"
                f"afade=t=out:st={max(0, total_duration-2.0)}:d=2.0,"
                f"volume={bgm_vol}"
                f"[bgm]"
            )
            mix_labels.append("[bgm]")
            stream_idx += 1

        n = len(mix_labels)
        loudnorm_str = ",loudnorm=I=-14:LRA=7:tp=-1.5[aout]" if normalize_loudness else "[aout]"
        filter_complex = (
            ";".join(filter_parts)
            + f";{''.join(mix_labels)}amix=inputs={n}:duration=longest:dropout_transition=3{loudnorm_str}"
        )

        cmd = [
            "ffmpeg", "-y",
            *input_args,
            "-filter_complex", filter_complex,
            "-map", "[aout]",
            "-ar", "44100",
            "-ac", "2",
            "-t", str(total_duration),
            self.output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg audio mix failed:\n{result.stderr[-1000:]}")

        return self.output_path, total_duration
