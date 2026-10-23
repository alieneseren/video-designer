import os
import asyncio
import subprocess
import re
from pathlib import Path
import edge_tts
from .models import Scenario, Message, Character
from .voice_profiles import (
    VOICE_PROFILES,
    VOICE_PROFILES_EN,
    get_voice_profiles,
    get_default_voice,
    SCENARIO_VOICE_MAP,
    HYBRID_MALE_SAMPLE,
    HYBRID_FEMALE_SAMPLE,
    ELDERLY_MALE_SAMPLE,
    ELDERLY_FEMALE_SAMPLE,
)
try:
    from text_normalizer import normalize_turkish_tts_text
except ImportError:
    from src.text_normalizer import normalize_turkish_tts_text

EMOJI_REGEX = re.compile(
    r'['
    r'\U0001F600-\U0001F64F'  # Emoticons
    r'\U0001F300-\U0001F5FF'  # Misc Symbols and Pictographs
    r'\U0001F680-\U0001F6FF'  # Transport and Map
    r'\U0001F1E0-\U0001F1FF'  # Flags
    r'\U0001F900-\U0001F9FF'  # Supplemental Symbols and Pictographs
    r'\U0001FA00-\U0001FA6F'  # Symbols and Pictographs Extended-A
    r'\U0001FA70-\U0001FAFF'  # Symbols and Pictographs Extended-B
    r'\u2702-\u27B0'          # Dingbats
    r'\u24C2-\u25FF'          # Enclosed & geometric
    r'\u2600-\u26FF'          # Misc Symbols (❤️, ⚡, ⚠️ vb.)
    r'\u2300-\u23FF'          # Technical
    r'\u2B00-\u2BFF'          # Arrows & misc
    r'\u200D'                  # Zero-width joiner
    r'\uFE0E-\uFE0F'          # Variation selectors
    r'\U0001F3FB-\U0001F3FF'  # Skin tones
    r']+',
    flags=re.UNICODE
)

def prepare_speech_text_and_tone(raw_text: str, lang: str = "tr") -> tuple[str, str, str]:
    raw_str = str(raw_text or "").strip()
    low_text = raw_str.lower()
    is_tr = (lang == "tr" or lang.startswith("tr"))

    rate_offset = 0
    pitch_offset = 0
    emoji_fallback = "Efendim?" if is_tr else "Yes?"

    if any(e in raw_str for e in ["😂", "🤣", "😆", "😹", "💀"]) or any(w in low_text for w in ["haha", "koptum", "öldüm gülmekten", "çatladım", "lmao", "lol"]):
        rate_offset = 10
        pitch_offset = 6
        emoji_fallback = "Haha!"
    elif any(e in raw_str for e in ["😱", "😲", "🤯", "🔥", "⚡", "🎉", "🚀"]) or any(w in low_text for w in ["oha", "yuh", "çüş", "inanamıyorum", "ciddi misin", "omg", "wow"]):
        rate_offset = 12
        pitch_offset = 10
        emoji_fallback = "Yok artık!" if is_tr else "No way!"
    elif any(e in raw_str for e in ["😍", "🥰", "😘", "❤️", "💕", "💖", "💘", "🌹"]) or any(w in low_text for w in ["aşkım", "canım", "birtanem", "sevgilim", "honey", "darling"]):
        rate_offset = -2
        pitch_offset = 4
        emoji_fallback = "Canım benim!" if is_tr else "My love!"
    elif any(e in raw_str for e in ["😢", "😭", "🥺", "😔", "💔", "😞", "😿"]) or any(w in low_text for w in ["üzüldüm", "off ya", "yapma ya", "yazık", "sad"]):
        rate_offset = -6
        pitch_offset = -4
        emoji_fallback = "Off ya..." if is_tr else "Oh no..."
    elif any(e in raw_str for e in ["😡", "😠", "🤬", "😤", "👿"]) or any(w in low_text for w in ["yeter", "saçmalama", "deli etme", "bıktım", "sinir"]):
        rate_offset = 6
        pitch_offset = -3
        emoji_fallback = "İnanmıyorum ya!" if is_tr else "Unbelievable!"
    elif any(e in raw_str for e in ["👍", "👌", "👏", "🙌", "✅"]):
        rate_offset = 4
        pitch_offset = 2
        emoji_fallback = "Tamamdır!" if is_tr else "Got it!"

    spoken_text = EMOJI_REGEX.sub("", raw_str).strip()
    spoken_text = re.sub(r'\s+', ' ', spoken_text)
    spoken_text = re.sub(r'([!?.])\1+', r'\1', spoken_text)

    if not spoken_text or not re.search(r'[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]', spoken_text):
        spoken_text = emoji_fallback

    rate_str = f"{rate_offset:+d}%" if rate_offset != 0 else "+0%"
    pitch_str = f"{pitch_offset:+d}Hz" if pitch_offset != 0 else "+0Hz"
    return spoken_text, rate_str, pitch_str

class TTSEngine:
    def __init__(self, output_dir: str = None, backend: str = "edge-tts", chatterbox_fallback: bool = False, language: str = "tr"):
        self.output_dir = output_dir or "/tmp/whatsapp_audio"
        self.backend = backend.lower()
        self.chatterbox_fallback = chatterbox_fallback
        self.language = (language or "tr").lower().strip()
        os.makedirs(self.output_dir, exist_ok=True)

    def _generate_chatterbox(self, text: str, output_path: str, role: str = "contact", profile: dict = None, is_female: bool = False) -> None:
        try:
            try:
                from chatterbox_generator import ChatterboxAudioGenerator
            except ImportError:
                from src.chatterbox_generator import ChatterboxAudioGenerator

            gen = ChatterboxAudioGenerator()
            model = gen.get_model()

            # WhatsApp komedi dublajı (BirDublaj / Hamza Dublaj) için karakter ekspresyonu
            is_contact = (role == "contact")
            exg = 0.85 if is_contact else 0.70
            tmp = 0.80 if is_contact else 0.75
            cfg = 0.65

            audio_prompt = None
            if profile and profile.get("audio_prompt_path") and os.path.exists(profile["audio_prompt_path"]):
                audio_prompt = profile["audio_prompt_path"]
            elif is_female and os.path.exists(HYBRID_FEMALE_SAMPLE):
                audio_prompt = HYBRID_FEMALE_SAMPLE
            elif os.path.exists(HYBRID_MALE_SAMPLE):
                audio_prompt = HYBRID_MALE_SAMPLE

            norm_text = normalize_turkish_tts_text(text)
            wav = model.generate(
                text=norm_text,
                language_id="tr",
                audio_prompt_path=audio_prompt,
                exaggeration=exg,
                temperature=tmp,
                cfg_weight=cfg
            )

            wav_np = wav.squeeze(0).cpu().numpy()
            import numpy as np
            thresh = 0.005
            abs_w = np.abs(wav_np)
            idx = np.where(abs_w > thresh)[0]
            if len(idx) > 0:
                wav_np = wav_np[max(0, idx[0] - int(model.sr * 0.03)):min(len(wav_np), idx[-1] + int(model.sr * 0.04))]

            import soundfile as sf
            sf.write(output_path, wav_np, model.sr)
        except Exception as exc:
            raise RuntimeError(f"Chatterbox generation failed: {exc}") from exc

    @staticmethod
    def get_audio_duration(file_path: str) -> float:
        cmd = [
            "ffprobe", "-i", file_path,
            "-show_entries", "format=duration",
            "-v", "quiet", "-of", "csv=p=0"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    def _apply_voice_eq(self, raw_mp3: str, final_mp3: str, ffmpeg_eq: str) -> str:
        if not ffmpeg_eq:
            return raw_mp3
        cmd = [
            "ffmpeg", "-y",
            "-i", raw_mp3,
            "-af", ffmpeg_eq,
            final_mp3
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return final_mp3
        return raw_mp3

    async def generate_speech_for_message(
        self,
        message: Message,
        char: Character,
        profile: dict,
        index: int
    ) -> str:
        raw_text = message.text
        speech_text, emo_rate, emo_pitch = prepare_speech_text_and_tone(raw_text, self.language)
        is_tr = (self.language == "tr" or self.language.startswith("tr"))
        if is_tr:
            speech_text = normalize_turkish_tts_text(speech_text)
        if not speech_text:
            speech_text = raw_text

        raw_ext = "wav" if (is_tr and self.backend in {"chatterbox", "auto"}) else "mp3"
        raw_path = os.path.join(self.output_dir, f"raw_{index:03d}_{message.sender}.{raw_ext}")
        final_path = os.path.join(self.output_dir, f"msg_{index:03d}_{message.sender}.mp3")

        is_female = (
            profile.get("gender") == "female"
            or "female" in profile.get("style_note", "").lower()
            or "kadin" in profile.get("style_note", "").lower()
            or "kadın" in profile.get("style_note", "").lower()
            or "anne" in profile.get("style_note", "").lower()
            or "mom" in profile.get("style_note", "").lower()
            or getattr(char, "voice", "") == "tr-TR-EmelNeural"
            or "jenny" in getattr(char, "voice", "").lower()
            or "michelle" in getattr(char, "voice", "").lower()
            or "emel" in getattr(char, "voice", "").lower()
        )

        default_voice = get_default_voice("female" if is_female else "male", self.language)
        voice = profile.get("voice", char.voice or default_voice)
        if not is_tr and voice.startswith("tr-TR-"):
            voice = default_voice

        prof_rate = int(re.sub(r'[^0-9\-+]', '', profile.get("rate", "+0%")) or 0)
        emo_rate_val = int(re.sub(r'[^0-9\-+]', '', emo_rate) or 0)
        rate = f"{prof_rate + emo_rate_val:+d}%"

        prof_pitch = int(re.sub(r'[^0-9\-+]', '', profile.get("pitch", "+0Hz")) or 0)
        emo_pitch_val = int(re.sub(r'[^0-9\-+]', '', emo_pitch) or 0)
        pitch = f"{prof_pitch + emo_pitch_val:+d}Hz"

        used_edge = False
        if is_tr and self.backend in {"chatterbox", "auto"}:
            try:
                await asyncio.to_thread(self._generate_chatterbox, speech_text, raw_path, message.sender, profile, is_female)
            except Exception as cb_err:
                print(f"[WhatsApp-TTS] Chatterbox sentez hatası ({cb_err}), Edge-TTS'e geçiliyor...")
                used_edge = True
                raw_ext = "mp3"
                raw_path = os.path.join(self.output_dir, f"raw_{index:03d}_{message.sender}.mp3")
        else:
            used_edge = True
            raw_ext = "mp3"
            raw_path = os.path.join(self.output_dir, f"raw_{index:03d}_{message.sender}.mp3")

        if used_edge:
            communicate = edge_tts.Communicate(text=speech_text, voice=voice, rate=rate, pitch=pitch)
            await communicate.save(raw_path)

        # Apply character EQ
        eq = profile.get("ffmpeg_eq", "")
        self._apply_voice_eq(raw_path, final_path, eq)
        return final_path if os.path.exists(final_path) else raw_path

    def _resolve_sender_profile(self, sender_name: str, index: int, is_female_hint: bool = None) -> dict:
        is_tr = (self.language == "tr" or self.language.startswith("tr"))
        voice_profiles = get_voice_profiles(self.language)
        s_low = (sender_name or "").lower().strip()
        female_keywords = [
            "anne", "annem", "valide", "mami", "mom", "mommy", "mother", "sister", "grandma", "aunt",
            "abla", "ablam", "kız", "kiz", "teyze", "hala", "kaynana", "kayınvalide", "gelin", "yenge",
            "bayan", "hanım", "merve", "ayşe", "ayse", "fatma", "zeynep", "elif",
            "buse", "ceren", "sinem", "esra", "ebru", "eda", "derya", "gamze",
            "sarah", "emily", "jessica", "emma", "olivia", "chloe", "sophia", "mia", "girlfriend", "wife"
        ]
        is_fem = is_female_hint if is_female_hint is not None else any(w in s_low for w in female_keywords)

        if is_fem:
            if any(w in s_low for w in ["nine", "babaanne", "anneanne", "grandma"]):
                prof_name = "nine" if is_tr else "grandma"
            elif any(w in s_low for w in ["teyze", "hala", "kaynana", "aunt"]):
                prof_name = "teyze" if is_tr else "aunt"
            elif any(w in s_low for w in ["anne", "valide", "mom", "mother"]):
                prof_name = "anne" if is_tr else "mom"
            else:
                fem_pool = ["kanka_kadin", "sakin_kadin", "kiskanclik_kadin", "kizgin_kadin"]
                prof_name = fem_pool[index % len(fem_pool)]
        else:
            if any(w in s_low for w in ["dede", "ihtiyar", "büyükbaba", "grandpa"]):
                prof_name = "dede" if is_tr else "grandpa"
            elif any(w in s_low for w in ["baba", "peder", "dad", "father"]):
                prof_name = "baba" if is_tr else "dad"
            elif any(w in s_low for w in ["ev sahibi", "hacı", "dayı", "amca", "yönetici", "landlord"]):
                prof_name = "ev_sahibi" if is_tr else "landlord"
            elif any(w in s_low for w in ["usta", "patron", "müdür", "boss", "manager"]):
                prof_name = "sinirli_erkek" if is_tr else "boss"
            else:
                male_pool = ["kanka_erkek", "troll_erkek", "odun_erkek", "yorgun_erkek"]
                prof_name = male_pool[index % len(male_pool)]

        default_male_prof = voice_profiles.get("odun_erkek", voice_profiles.get("tired_friend", {}))
        base_prof = dict(voice_profiles.get(prof_name, default_male_prof))
        # Slight pitch variation so distinct speakers with same profile don't sound completely identical
        pitch_val = int(re.sub(r'[^0-9\-+]', '', base_prof.get("pitch", "+0Hz")) or 0)
        pitch_val += (index % 3 - 1) * 3
        base_prof["pitch"] = f"{pitch_val:+d}Hz"
        return base_prof

    async def process_scenario(self, scenario: Scenario, scenario_name: str = "") -> Scenario:
        # Otomatik Karakter & Rol Tespiti
        is_tr = (self.language == "tr" or self.language.startswith("tr"))
        voice_profiles = get_voice_profiles(self.language)
        contact_name_low = (scenario.contact_name or "").lower()
        char_contact = scenario.characters.get("contact") if scenario.characters else None
        female_keywords = [
            "anne", "annem", "valide", "mami", "mom", "mommy", "mother", "sister", "grandma", "aunt",
            "abla", "ablam", "kız", "kiz", "sevgili", "aşkım", "askim", "prenses", "karım", "karim",
            "eşim", "esim", "hatun", "teyze", "hala", "kaynana", "kayınvalide", "gelin", "yenge",
            "bayan", "hanım", "merve", "ayşe", "ayse", "fatma", "zeynep", "elif",
            "buse", "ceren", "sinem", "esra", "ebru", "eda", "derya", "gamze",
            "sarah", "emily", "jessica", "emma", "olivia", "chloe", "sophia", "mia", "girlfriend", "wife"
        ]

        is_contact_female = (
            getattr(scenario, "contact_avatar_gender", None) == "female"
            or (char_contact and "emel" in getattr(char_contact, "voice", "").lower())
            or (char_contact and "jenny" in getattr(char_contact, "voice", "").lower())
            or any(w in contact_name_low for w in female_keywords)
        )

        char_user = scenario.characters.get("user") if scenario.characters else None
        is_user_female = (
            getattr(scenario, "user_gender", None) == "female"
            or (char_user and ("emel" in getattr(char_user, "voice", "").lower()))
            or (char_user and ("jenny" in getattr(char_user, "voice", "").lower()))
            or (scenario.characters.get("user_profile_override") and any(k in str(scenario.characters["user_profile_override"]) for k in ("kadin", "kadın", "anne", "nine", "teyze", "female", "mom")))
        )

        if is_contact_female:
            if any(w in contact_name_low for w in ["nine", "babaanne", "anneanne", "ihtiyar", "grandma"]):
                contact_profile_name = "nine" if is_tr else "grandma"
            elif any(w in contact_name_low for w in ["teyze", "hala", "kaynana", "aunt"]):
                contact_profile_name = "teyze" if is_tr else "aunt"
            elif any(w in contact_name_low for w in ["anne", "valide", "mami", "mom", "mother"]):
                contact_profile_name = "anne" if is_tr else "mom"
            elif any(w in contact_name_low for w in ["aşkım", "askim", "sevgili", "karım", "karim", "prenses", "merve", "girlfriend", "wife"]):
                contact_profile_name = "kiskanclik_kadin"
            else:
                contact_profile_name = "kanka_kadin" if is_tr else "bestie_female"
            user_profile_name = "sakin_kadin" if is_user_female else ("odun_erkek" if is_tr else "tired_friend")
        elif any(w in contact_name_low for w in ["dede", "ihtiyar", "büyükbaba", "dedem", "grandpa"]):
            contact_profile_name = "dede" if is_tr else "grandpa"
            user_profile_name = "kanka_kadin" if is_user_female else ("troll_erkek" if is_tr else "troll_friend")
        elif any(w in contact_name_low for w in ["baba", "peder", "dad", "father"]):
            contact_profile_name = "baba" if is_tr else "dad"
            user_profile_name = "sakin_kadin" if is_user_female else ("troll_erkek" if is_tr else "troll_friend")
        elif any(w in contact_name_low for w in ["ev sahibi", "sahip", "hacı", "rüstem", "dayı", "landlord"]):
            contact_profile_name = "ev_sahibi" if is_tr else "landlord"
            user_profile_name = "kizgin_kadin" if is_user_female else ("sinirli_erkek" if is_tr else "boss")
        elif any(w in contact_name_low for w in ["patron", "müdür", "hoca", "öğretmen", "boss", "manager"]):
            contact_profile_name = "sinirli_erkek" if is_tr else "boss"
            user_profile_name = "sakin_kadin" if is_user_female else ("troll_erkek" if is_tr else "troll_friend")
        else:
            voice_map = SCENARIO_VOICE_MAP.get(scenario_name, SCENARIO_VOICE_MAP["default"])
            contact_profile_name = voice_map.get("contact", "odun_erkek" if is_tr else "tired_friend")
            user_profile_name = "sakin_kadin" if is_user_female else voice_map.get("user", "troll_erkek" if is_tr else "troll_friend")

        if scenario.characters.get("contact_profile_override"):
            override = scenario.characters["contact_profile_override"]
            if is_contact_female and override in ("odun_erkek", "troll_erkek", "baba", "ev_sahibi", "sinirli_erkek", "yorgun_erkek", "kanka_erkek"):
                pass
            else:
                contact_profile_name = override
        if scenario.characters.get("user_profile_override"):
            override_u = scenario.characters["user_profile_override"]
            if override_u in voice_profiles:
                user_profile_name = override_u

        default_contact_prof = voice_profiles.get("odun_erkek", voice_profiles.get("tired_friend", {}))
        default_user_prof = voice_profiles.get("troll_erkek", voice_profiles.get("troll_friend", {}))
        contact_profile = voice_profiles.get(contact_profile_name, default_contact_prof)
        user_profile = voice_profiles.get(user_profile_name, default_user_prof)

        sender_profiles = {}
        participant_counter = 0

        current_time = 0.5  # initial lead time
        for i, msg in enumerate(scenario.messages):
            char = scenario.characters.get(msg.sender)
            if not char:
                char = Character(name=msg.sender, role=msg.sender)
                scenario.characters[msg.sender] = char

            if msg.sender == "user":
                profile = user_profile
            elif scenario.is_group and msg.sender_name:
                s_name = msg.sender_name.strip()
                if s_name not in sender_profiles:
                    sender_profiles[s_name] = self._resolve_sender_profile(
                        s_name, participant_counter
                    )
                    participant_counter += 1
                profile = sender_profiles[s_name]
            else:
                profile = contact_profile

            # Viral dubbing Shorts (Bi' Dublaj / Hamza Dublaj) tarzı:
            # Yazıyor balonu yok, mesaj balonu konuşma başlar başlamaz anında patlar
            msg.typing_duration = 0.0
            msg.start_time = current_time
            msg.bubble_appear_time = current_time

            # Generate speech
            audio_path = await self.generate_speech_for_message(msg, char, profile, i)
            msg.audio_path = audio_path
            dur = self.get_audio_duration(audio_path)
            msg.audio_duration = dur

            # Advance timeline: bubble appears, audio plays, then small reaction pause
            pause_after = 0.15 if i < len(scenario.messages) - 1 else 0.8
            current_time = msg.bubble_appear_time + dur + pause_after

        return scenario

    def run_sync(self, scenario: Scenario, scenario_name: str = "") -> Scenario:
        return asyncio.run(self.process_scenario(scenario, scenario_name))
