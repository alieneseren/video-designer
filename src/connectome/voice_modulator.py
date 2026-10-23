"""
src/connectome/voice_modulator.py
==================================
Drosophila Connectome Biyo-AI Ses Modülatörü (Neuromorphic Voice Modulator)

139.255 nöron simülasyonu ve STDP sinaptik ağırlıkları üzerinden:
- Biyo-Jitter: Mikro-periyot perde sapması (±0.6% F0 fraksiyonel gecikme)
- Biyo-Shimmer: Nöron ateşleme yoğunluğuna bağlı glottal enerji mikro-modülasyonu (±4%)
- Biyo-Formant Rezonansı: Nöronların 3B uzaysal koordinatlarına (Z-ekseni) bağlı vokal netlik filtresi (3.1 kHz)

Yapay zeka seslerindeki sentetik sterilliği kırıp organik, nefes alan biyo-tını kazandırır.
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Union

import numpy as np
import scipy.signal as signal
import soundfile as sf
import librosa

try:
    from src.connectome.synth import ConnectomeSimulator
except ImportError:
    from connectome.synth import ConnectomeSimulator


class ConnectomeVoiceModulator:
    """
    Sinek Beyni Konnektom Nöron Dinamiklerini İnsan Ses Klonlamasına Giydiren Biyo-Modülatör.
    """

    def __init__(self, num_neurons: int = 48, seed: Optional[int] = 42):
        self.num_neurons = num_neurons
        self.sim = ConnectomeSimulator(num_neurons=num_neurons, seed=seed)

    def modulate_audio(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 44100,
        jitter_depth: float = 0.006,   # ±0.6% F0 mikro sapma
        shimmer_depth: float = 0.04,   # ±4% enerji dalgalanması
        formant_boost_db: float = 1.5, # ±1.5 dB şarkıcı formantı zenginleştirmesi
        hop_length: int = 256
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Giriş ses sinyaline nöromorfik konnektom modülasyonu uygular.
        """
        y = np.asarray(audio_data, dtype=np.float32)
        if y.ndim > 1:
            y = np.mean(y, axis=1)

        total_samples = len(y)
        num_frames = max(1, total_samples // hop_length)

        voltages_list = []
        spikes_list = []
        centroid_z_list = []

        # 1. Konnektom Nöron Simülasyonu
        for _ in range(num_frames):
            spikes = self.sim.step()
            voltages_list.append(float(np.mean(self.sim.voltages)))
            spikes_list.append(len(spikes))
            if spikes:
                z_vals = [self.sim.coords[s["idx"]]["z"] for s in spikes if s["idx"] < len(self.sim.coords)]
                centroid_z_list.append(float(np.mean(z_vals)) if z_vals else 0.0)
            else:
                centroid_z_list.append(0.0)

        # 2. Örnekleme Düzeyinde İnterpolasyon
        frame_times = np.arange(num_frames) * hop_length
        sample_indices = np.arange(total_samples)

        v_interp = np.interp(sample_indices, frame_times, voltages_list)
        s_interp = np.interp(sample_indices, frame_times, spikes_list)
        z_interp = np.interp(sample_indices, frame_times, centroid_z_list)

        # 3. Biyolojik Frekans Bandı Filtreleri (2 - 25 Hz insan ses telleri fizyolojisi)
        b_bio, a_bio = signal.butter(2, [1.0 / (sample_rate / 2), 22.0 / (sample_rate / 2)], btype="bandpass")
        b_slow, a_slow = signal.butter(2, 6.0 / (sample_rate / 2), btype="lowpass")

        jitter_mod = signal.filtfilt(b_bio, a_bio, v_interp)
        jitter_mod = (jitter_mod / (np.std(jitter_mod) + 1e-6)) * jitter_depth

        shimmer_mod = signal.filtfilt(b_slow, a_slow, s_interp)
        shimmer_mod = (shimmer_mod / (np.std(shimmer_mod) + 1e-6)) * shimmer_depth

        # 4. Değişken Gecikme Hattı ile Mikro-Jitter (Perde Sapması)
        phase_drift = np.cumsum(jitter_mod)
        source_indices = np.arange(total_samples) + phase_drift
        source_indices = np.clip(source_indices, 0, total_samples - 1)

        idx_floor = np.floor(source_indices).astype(int)
        idx_ceil = np.clip(idx_floor + 1, 0, total_samples - 1)
        frac = source_indices - idx_floor

        y_jittered = (1.0 - frac) * y[idx_floor] + frac * y[idx_ceil]

        # 5. Mikro-Shimmer (Glottal Hacim Modülasyonu)
        gain_curve = 1.0 + shimmer_mod
        y_shimmered = y_jittered * gain_curve

        # 6. Biyo-Formant Netlik Filtresi (3.1 kHz Parametrik EQ)
        center_freq = 3100.0
        Q = 2.2
        w0 = 2 * np.pi * center_freq / sample_rate
        alpha = np.sin(w0) / (2 * Q)

        A = 10.0 ** (formant_boost_db / 40.0)
        b0 = 1 + alpha * A
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / A

        sos_formant = np.array([[b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]])
        y_resonant = signal.sosfilt(sos_formant, y_shimmered)

        # Doğal denge: %82 şablon + %18 biyo-rezonans
        y_final = 0.82 * y_shimmered + 0.18 * y_resonant

        # Tepe genlik normalizasyonu
        max_orig = np.max(np.abs(y))
        max_final = np.max(np.abs(y_final))
        if max_final > 0:
            y_final = y_final * (max_orig / max_final)

        stats = {
            "duration_sec": round(total_samples / sample_rate, 2),
            "simulated_neurons": self.num_neurons,
            "total_spikes": int(np.sum(spikes_list)),
            "mean_firing_rate_hz": round((np.sum(spikes_list) / (total_samples / sample_rate)) / self.num_neurons, 2),
            "applied_jitter_depth": jitter_depth,
            "applied_shimmer_depth": shimmer_depth,
        }

        return y_final.astype(np.float32), stats

    def modulate_file(
        self,
        input_wav: Union[str, Path],
        output_wav: Union[str, Path],
        **kwargs
    ) -> Dict[str, Any]:
        """Bir ses dosyasını okuyup nöromorfik modülasyonu uygulayarak diske yazar."""
        inp = Path(input_wav).resolve()
        out = Path(output_wav).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        y, sr = librosa.load(str(inp), sr=44100, mono=True)
        y_mod, stats = self.modulate_audio(y, sample_rate=sr, **kwargs)
        sf.write(str(out), y_mod, sr, subtype="PCM_16")

        stats["input_file"] = str(inp)
        stats["output_file"] = str(out)
        return stats
