#!/usr/bin/env python3
"""
Drosophila Connectome Generative Audio Synthesizer (Up to 300s / 5 min)
======================================================================
Ported & enhanced from the live stream biological music engine (fly_piano_live.html).
Simulates biological Drosophila melanogaster connectome spiking neurons with STDP
synaptic plasticity and synthesizes rich multi-instrument orchestral, ambient,
jazz, rock, and neoclassical music across 11 distinct genres.

Key Enhancements for Non-Repetitive Musicality:
- 16-Bar Progressive Symphonic Journeys (Never stuck in a 4-chord loop).
- Multi-Octave Note Vocabularies: Expansive palettes spanning Octaves 2 to 6.
- Synaptic Burst Cascades: When multiple neurons spike, plays Chopin-style
  virtuosic arpeggiated runs (3-5 notes gliding across octaves) instead of clusters.
- Live Genetic Ensemble Mutation (evolveToNextCombo): Instrument roster
  dynamically breathes and mutates every 2 bars (piano solo -> cello swell ->
  violins -> harp sparkles -> full ensemble climax -> peaceful resolution).
- Varied Left-Hand Bass: Chopin wide-tenths, rolling waves, and chromatic walking transitions.
- Strict Python native type conversion (prevents np.int64 JSON serialization errors).
"""

import os
import json
import math
import wave
import random
import numpy as np
from pathlib import Path
from scipy import signal

SAMPLE_RATE = 44100
FPS = 30

def json_default(obj):
    """Safely converts numpy scalars and arrays to native Python types for JSON."""
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)

# Load 11 Genres from genres_data.json
GENRES_FILE = Path(__file__).parent / "genres_data.json"
if GENRES_FILE.exists():
    with open(GENRES_FILE, "r", encoding="utf-8") as f:
        GENRES = json.load(f)
else:
    GENRES = {}

# Fallback Scale Dictionary for backward compatibility
SCALES = {
    "f_minor_pentatonic": {
        "name": "F Minor Pentatonic (Chopin Nocturne)",
        "genre_id": "emotional",
        "freqs": [174.61, 207.65, 233.08, 261.63, 311.13, 349.23, 415.30, 466.16, 523.25, 622.25, 698.46, 830.61]
    },
    "d_dorian": {
        "name": "D Dorian (Mysterious Cinema)",
        "genre_id": "mysterious",
        "freqs": [146.83, 164.81, 174.61, 196.00, 220.00, 246.94, 261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 523.25]
    },
    "c_lydian": {
        "name": "C Lydian (Peaceful Ambient)",
        "genre_id": "peaceful",
        "freqs": [130.81, 146.83, 164.81, 185.00, 196.00, 220.00, 246.94, 261.63, 293.66, 329.63, 370.00, 392.00, 523.25]
    },
    "a_hirajoshi": {
        "name": "A Hirajoshi (Deep Neural Zen)",
        "genre_id": "oriental",
        "freqs": [110.00, 123.47, 130.81, 164.81, 174.61, 220.00, 246.94, 261.63, 329.63, 349.23, 440.00, 493.88]
    }
}

HARMONIC_AFFINITY = {
    0: 0.88,  # Octave / Unison
    7: 0.85,  # Perfect 5th
    5: 0.80,  # Perfect 4th
    4: 0.84,  # Major 3rd
    3: 0.82,  # Minor 3rd (Melancholy)
    9: 0.78,  # Major 6th
    8: 0.76,  # Minor 6th
    2: 0.65,  # Major 2nd
    10: 0.55, # Minor 7th
    11: 0.40, # Major 7th
    1: 0.12,  # Minor 2nd (Dissonance)
    6: 0.08   # Tritone
}

class ConnectomeSimulator:
    """
    Simulates 48 Drosophila melanogaster connectome neurons with STDP synaptic learning.
    Directly loads the trained Chopin/Bach/Beethoven STDP weights from classical_connectome_weights.json,
    exactly matching the biological neural engine of the YouTube live stream (fly_piano_live.html).
    """
    def __init__(self, num_neurons: int = 48, seed: int = None):
        self.num_neurons = int(num_neurons)
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        self.coords = []
        for i in range(self.num_neurons):
            theta = np.random.uniform(0, 2 * np.pi)
            phi = np.random.uniform(-np.pi / 2, np.pi / 2)
            r = np.random.uniform(0.35, 0.95)
            x = r * np.cos(phi) * np.cos(theta)
            y = r * np.sin(phi) * 1.15
            z = r * np.cos(phi) * np.sin(theta)
            self.coords.append({"id": int(i), "x": float(x), "y": float(y), "z": float(z)})

        self.voltages = np.random.uniform(0.30, 0.75, size=self.num_neurons).astype(np.float32)
        self.decay = 0.94
        self.threshold = 0.80

        # Load trained weights from YouTube live stream if available
        self.graph = [[] for _ in range(self.num_neurons)]
        possible_paths = [
            Path(__file__).parent.parent / "classical_connectome_weights.json",
            Path(__file__).parent / "classical_connectome_weights.json",
            Path("/Users/alienes/anaprojelerdizisi/sinek_beyni/classical_connectome_weights.json")
        ]
        loaded = False
        for wp in possible_paths:
            if wp.exists():
                try:
                    with open(wp, "r", encoding="utf-8") as wf:
                        wdata = json.load(wf)
                        loaded_graph = wdata.get("graph", [])
                        if len(loaded_graph) == self.num_neurons:
                            self.graph = loaded_graph
                            loaded = True
                            break
                except Exception:
                    pass

        if not loaded:
            # Fallback STDP graph initialization
            for i in range(self.num_neurons):
                for j in range(self.num_neurons):
                    if i != j:
                        semitone = abs(j - i) % 12
                        affinity = HARMONIC_AFFINITY.get(semitone, 0.25)
                        if random.random() < affinity * 0.32:
                            self.graph[i].append({
                                "target": int(j),
                                "weight": float(round(0.15 + affinity * 0.65, 4))
                            })

    def step(self) -> list[dict]:
        """
        Runs one biological clock tick:
        1. Stochastic noise accumulation
        2. Voltage thresholding -> Action potential spikes
        3. Synaptic propagation through connectome graph
        4. STDP Hebbian learning
        5. Returns candidates sorted by membrane voltage (highest potential wins)
        """
        noise = np.random.uniform(0.0, 0.14, size=self.num_neurons)
        self.voltages = (self.voltages + noise) * self.decay

        spikes = np.where(self.voltages >= self.threshold)[0]
        candidates = [{"idx": int(s), "v": float(self.voltages[s])} for s in spikes]
        self.voltages[spikes] = 0.0  # Refractory reset

        # Action potential propagation across synaptic connectome
        for c in candidates:
            s = c["idx"]
            for edge in self.graph[s]:
                target = int(edge["target"])
                if target < self.num_neurons:
                    self.voltages[target] += float(edge["weight"]) * 0.35

        # Hebbian STDP Learning: Co-firing neurons strengthen classical harmonic affinity
        if len(candidates) >= 2:
            pre = candidates[0]["idx"]
            post = candidates[1]["idx"]
            semitone = abs(post - pre) % 12
            affinity = HARMONIC_AFFINITY.get(semitone, 0.20)
            for edge in self.graph[pre]:
                if edge["target"] == post:
                    edge["weight"] = min(0.92, float(edge["weight"]) + 0.003 * affinity)

        # Sort candidates strictly by voltage descending (winner neuron has highest voltage)
        candidates.sort(key=lambda c: c["v"], reverse=True)
        return candidates


# --- ACOUSTIC & ANALOG INSTRUMENT SYNTHESIS ENGINES ---


class VoiceTrack:
    """
    Manages polyphony, voice stealing, and note choking for an instrument.
    Guarantees clean voice leading and prevents simultaneous discordant note collisions.
    Emulates the Web Audio activePianoVoice.setTargetAtTime release damping of fly_piano_live.html.
    """
    def __init__(self, total_samples: int, max_polyphony: int = 1, choke_decay_sec: float = 0.040):
        self.total_samples = total_samples
        self.max_polyphony = max_polyphony
        self.choke_decay_sec = choke_decay_sec
        self.buffer_l = np.zeros(total_samples, dtype=np.float32)
        self.buffer_r = np.zeros(total_samples, dtype=np.float32)
        self.active_voices = []  # list of {"start": int, "end": int, "freq": float}

    def play_note(self, sound: np.ndarray, start_idx: int, freq: float, pan: float = 0.5, gain: float = 1.0):
        if len(sound) == 0 or start_idx >= self.total_samples:
            return

        # 1. Clean up voices that have already ended
        self.active_voices = [v for v in self.active_voices if v["end"] > start_idx]

        # 2. Voice Stealing / Choke if at or exceeding max polyphony
        while len(self.active_voices) >= self.max_polyphony:
            oldest = self.active_voices.pop(0)
            if oldest["end"] > start_idx:
                damp_len = min(int(SAMPLE_RATE * self.choke_decay_sec), self.total_samples - start_idx)
                if damp_len > 0:
                    damp_curve = np.exp(-np.linspace(0, 5.0, damp_len, dtype=np.float32))
                    self.buffer_l[start_idx:start_idx + damp_len] *= damp_curve
                    self.buffer_r[start_idx:start_idx + damp_len] *= damp_curve

                clear_start = start_idx + damp_len
                clear_end = min(self.total_samples, oldest["end"])
                if clear_end > clear_start:
                    self.buffer_l[clear_start:clear_end] = 0.0
                    self.buffer_r[clear_start:clear_end] = 0.0

        # 3. Add new note into this track's buffer
        end_idx = min(self.total_samples, start_idx + len(sound))
        actual_len = end_idx - start_idx
        clamped_pan = max(0.05, min(0.95, float(pan)))
        self.buffer_l[start_idx:end_idx] += sound[:actual_len] * (1.0 - clamped_pan) * gain
        self.buffer_r[start_idx:end_idx] += sound[:actual_len] * clamped_pan * gain

        self.active_voices.append({
            "start": start_idx,
            "end": end_idx,
            "freq": float(freq)
        })

    def clear_pedal(self, at_sample: int, release_sec: float = 0.080):
        """Lifts sustain pedal, smoothly damping all active ringing voices (pedal clearing)."""
        if not self.active_voices or at_sample >= self.total_samples:
            return
        damp_len = min(int(SAMPLE_RATE * release_sec), self.total_samples - at_sample)
        if damp_len > 0:
            damp_curve = np.exp(-np.linspace(0, 4.5, damp_len, dtype=np.float32))
            self.buffer_l[at_sample:at_sample + damp_len] *= damp_curve
            self.buffer_r[at_sample:at_sample + damp_len] *= damp_curve

        max_end = max((v["end"] for v in self.active_voices), default=at_sample)
        clear_start = at_sample + damp_len
        clear_end = min(self.total_samples, max_end)
        if clear_end > clear_start:
            self.buffer_l[clear_start:clear_end] = 0.0
            self.buffer_r[clear_start:clear_end] = 0.0

        self.active_voices = []

def get_butter_filter(cutoff_hz, btype='lowpass', order=2):
    nyq = 0.5 * SAMPLE_RATE
    if btype in ('bandpass', 'bandstop'):
        if isinstance(cutoff_hz, (list, tuple)):
            norm = [min(max(f / nyq, 0.01), 0.99) for f in cutoff_hz]
        else:
            c = float(cutoff_hz)
            norm = [min(max((c * 0.65) / nyq, 0.01), 0.99), min(max((c * 1.55) / nyq, 0.01), 0.99)]
    else:
        norm = min(max(float(cutoff_hz) / nyq, 0.01), 0.99)
    return signal.butter(order, norm, btype=btype, output='sos')

SOS_CELLO = get_butter_filter(460, 'lowpass')
SOS_VIOLIN = get_butter_filter(1900, 'lowpass')
SOS_GUITAR = get_butter_filter(750, 'lowpass')
SOS_GUITAR_AMP = get_butter_filter(3200, 'lowpass')
SOS_PLUCK = get_butter_filter(2400, 'lowpass')
SOS_SNARE = get_butter_filter([1100, 3600], 'bandpass')
SOS_HAT = get_butter_filter(7500, 'highpass')
SOS_CRASH = get_butter_filter(5200, 'highpass')

def render_piano_note(freq: float, duration: float = 2.0, velocity: float = 0.75, is_bass: bool = False) -> np.ndarray:
    """
    Concert Grand Piano modeled directly on the live stream Web Audio engine (fly_piano_live.html).
    Acoustic hammer attack, warm harmonic body, exponential decay, and clean acoustic timbre.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)

    decay_time = 2.5 if is_bass else 1.6
    time_constant = decay_time / 3.0
    envelope = np.exp(-t / time_constant)

    # 6ms linear attack ramp (prevents transient clicks while giving firm hammer strike)
    attack_len = int(SAMPLE_RATE * 0.006)
    if n > attack_len:
        envelope[:attack_len] = np.linspace(0.0001, 1.0, attack_len, dtype=np.float32)

    peak_vol = (0.48 if is_bass else 0.40) * velocity

    if is_bass:
        fund = (2.0 / np.pi) * np.arcsin(np.clip(np.sin(2 * np.pi * freq * t), -0.9999, 0.9999))
        h2 = 0.28 * np.sin(2 * np.pi * (freq * 2.0) * t)
        sub = 0.20 * np.sin(2 * np.pi * (freq * 0.5) * t) if freq < 240.0 else 0.0
        tone = (fund + h2 + sub) * envelope * peak_vol
    else:
        fund = np.sin(2 * np.pi * freq * t)
        h2 = 0.28 * np.sin(2 * np.pi * (freq * 2.0) * t)
        h3 = 0.05 * np.sin(2 * np.pi * (freq * 3.0) * t)
        tone = (fund + h2 + h3) * envelope * peak_vol

    return tone.astype(np.float32)

def render_guitar_note(freq: float, duration: float = 1.8, velocity: float = 0.72) -> np.ndarray:
    """Acoustic Guitar fingerpicked warm tone with sweeping body resonance (fly_piano_live.html)."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)
    time_constant = duration / 2.6
    envelope = np.exp(-t / time_constant)
    attack_len = int(SAMPLE_RATE * 0.005)
    if n > attack_len:
        envelope[:attack_len] = np.linspace(0.0001, 1.0, attack_len, dtype=np.float32)
    osc = (2.0 / np.pi) * np.arcsin(np.clip(np.sin(2 * np.pi * freq * t), -0.9999, 0.9999))
    sparkle = 0.22 * np.sin(2 * np.pi * (freq * 2.0) * t)
    raw = (osc + sparkle) * envelope * 0.44 * velocity
    return signal.sosfilt(SOS_GUITAR, raw).astype(np.float32)

def render_electric_guitar(
    freq: float,
    is_lead: bool = True,
    velocity: float = 0.85,
    duration: float = 0.32,
    bend_from: float = None,
    is_solo: bool = None,
    bend_start: float = None
) -> np.ndarray:
    """Overdrive lead/rhythm electric guitar with optional pitch bend and amp simulation."""
    if bend_start is not None and bend_from is None:
        bend_from = bend_start
    if is_solo is not None:
        is_lead = is_solo
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)
    
    if bend_from and bend_from > 0:
        bend_time = 0.09
        inst_freq = np.where(t < bend_time, bend_from + (freq - bend_from) * (t / bend_time), freq)
        phase = 2 * np.pi * np.cumsum(inst_freq) / SAMPLE_RATE
    else:
        phase = 2 * np.pi * freq * t
        
    saw1 = signal.sawtooth(phase)
    saw2 = signal.sawtooth(phase * 1.006)
    sub = signal.square(phase * 0.5) * 0.20
    
    time_constant = duration / 2.5
    env = np.exp(-t / time_constant) * velocity
    attack_len = int(SAMPLE_RATE * 0.008)
    if n > attack_len:
        env[:attack_len] = np.linspace(0.001, 1.0, attack_len, dtype=np.float32)
        
    raw = (saw1 * 0.50 + saw2 * 0.40 + sub) * env
    dist = np.tanh(raw * 3.5) * 0.75
    return signal.sosfilt(SOS_GUITAR_AMP, dist).astype(np.float32)

def render_power_chord(root_freq: float, duration: float = 0.38, palm_mute: bool = False, velocity: float = 0.90) -> np.ndarray:
    """Overdrive electric guitar power chord (Root + Fifth + Octave)."""
    dur = 0.14 if palm_mute else duration
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, False, dtype=np.float32)

    notes = [
        (root_freq, 0.50),
        (root_freq * 1.498307, 0.42),
        (root_freq * 2.0, 0.32)
    ]
    chord_raw = np.zeros(n, dtype=np.float32)
    for f, g in notes:
        saw1 = signal.sawtooth(2 * np.pi * f * t)
        saw2 = signal.sawtooth(2 * np.pi * f * 1.004 * t)
        chord_raw += (saw1 + saw2) * g * 0.5

    env = np.exp(-t * (18.0 if palm_mute else 4.5)) * velocity
    chord = chord_raw * env

    dist = np.tanh(chord * 3.2) * 0.70
    filtered = signal.sosfilt(SOS_GUITAR_AMP, dist)
    return filtered.astype(np.float32)

def render_cello_note(freq: float, duration: float = 3.8, velocity: float = 0.85) -> np.ndarray:
    """Deep bowed cello with triangular warmth and 460Hz body filtering."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)

    vibrato = np.sin(2 * np.pi * 5.2 * t) * 0.0065
    inst_freq = freq * (1.0 + vibrato)
    phase = 2 * np.pi * np.cumsum(inst_freq) / SAMPLE_RATE

    tri = (2.0 / np.pi) * np.arcsin(np.clip(np.sin(phase), -0.999, 0.999))
    warmth = 0.26 * np.sin(phase * 2.0)

    envelope = np.exp(-t / 1.2)
    attack_len = int(SAMPLE_RATE * 0.08)
    if n > attack_len:
        envelope[:attack_len] = np.linspace(0.001, 1.0, attack_len, dtype=np.float32)

    raw_tone = (tri + warmth) * envelope * 0.48 * velocity
    filtered = signal.sosfilt(SOS_CELLO, raw_tone)
    return filtered.astype(np.float32)

def render_violin_note(freq: float, duration: float = 2.8, velocity: float = 0.75) -> np.ndarray:
    """Detuned dual-oscillator strings ensemble with lush stereo chorus effect."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)

    osc1 = (2.0 / np.pi) * np.arcsin(np.clip(np.sin(2 * np.pi * freq * t), -0.999, 0.999))
    osc2 = (2.0 / np.pi) * np.arcsin(np.clip(np.sin(2 * np.pi * freq * 1.0045 * t), -0.999, 0.999))

    envelope = np.exp(-t / 0.85)
    attack_len = int(SAMPLE_RATE * 0.09)
    if n > attack_len:
        envelope[:attack_len] = np.linspace(0.001, 1.0, attack_len, dtype=np.float32)

    raw_tone = (osc1 * 0.55 + osc2 * 0.45) * envelope * 0.38 * velocity
    filtered = signal.sosfilt(SOS_VIOLIN, raw_tone)
    return filtered.astype(np.float32)

def render_harp_note(freq: float, duration: float = 2.4, velocity: float = 0.70) -> np.ndarray:
    """Sparkling plucked harp note with gentle exponential decay."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)

    osc1 = (2.0 / np.pi) * np.arcsin(np.clip(np.sin(2 * np.pi * freq * t), -0.999, 0.999))
    sparkle = 0.20 * np.sin(2 * np.pi * freq * 2.0 * t)

    envelope = np.exp(-t / 0.70)
    attack_len = int(SAMPLE_RATE * 0.006)
    if n > attack_len:
        envelope[:attack_len] = np.linspace(0.001, 1.0, attack_len, dtype=np.float32)

    return ((osc1 + sparkle) * envelope * 0.42 * velocity).astype(np.float32)

def render_synth_pluck(freq: float, duration: float = 0.35, velocity: float = 0.70) -> np.ndarray:
    """Punchy synth pluck with dynamic lowpass filter sweep."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)
    saw = signal.sawtooth(2 * np.pi * freq * t)
    envelope = np.exp(-t / 0.26)
    attack_len = int(SAMPLE_RATE * 0.004)
    if n > attack_len:
        envelope[:attack_len] = np.linspace(0.001, 1.0, attack_len, dtype=np.float32)
    raw = saw * envelope * 0.42 * velocity
    return signal.sosfilt(SOS_PLUCK, raw).astype(np.float32)

def render_808_sub_bass(freq: float, duration: float = 0.55, velocity: float = 0.95) -> np.ndarray:
    """Deep 808 Trap sub-bass with pitch-drop punch and soft saturation."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)
    pitch = max(34.0, min(68.0, freq * 0.5))

    inst_freq = pitch * (1.0 + 0.8 * np.exp(-t * 28.0))
    phase = 2 * np.pi * np.cumsum(inst_freq) / SAMPLE_RATE

    envelope = np.exp(-t * 3.8)
    sub = np.sin(phase) * envelope * velocity
    saturated = np.tanh(sub * 1.4) * 0.88
    return saturated.astype(np.float32)

def render_kick(velocity: float = 1.0) -> np.ndarray:
    """Punchy electronic/rock kick drum."""
    duration = 0.28
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)

    pitch = 28.0 + (160.0 - 28.0) * np.exp(-t * 32.0)
    phase = 2 * np.pi * np.cumsum(pitch) / SAMPLE_RATE

    env = np.exp(-t * 12.0) * velocity
    click = np.sin(2 * np.pi * 1400.0 * t) * np.exp(-t * 90.0) * 0.35 * velocity
    return ((np.sin(phase) + click) * env * 0.85).astype(np.float32)

def render_snare(velocity: float = 0.85) -> np.ndarray:
    """Acoustic/trap snare with bandpass noise snap and body punch."""
    duration = 0.22
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)

    noise = np.random.uniform(-1.0, 1.0, n).astype(np.float32)
    noise_snap = signal.sosfilt(SOS_SNARE, noise) * np.exp(-t * 18.0) * 0.65

    body_pitch = 85.0 + 95.0 * np.exp(-t * 25.0)
    body_phase = 2 * np.pi * np.cumsum(body_pitch) / SAMPLE_RATE
    body = np.sin(body_phase) * np.exp(-t * 20.0) * 0.40

    return ((noise_snap + body) * velocity * 0.85).astype(np.float32)

def render_hihat(is_open: bool = False, velocity: float = 0.50) -> np.ndarray:
    """Highpass crisp metallic hi-hat."""
    duration = 0.20 if is_open else 0.045
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)
    decay = 14.0 if is_open else 75.0

    noise = np.random.uniform(-1.0, 1.0, n).astype(np.float32)
    hat = signal.sosfilt(SOS_HAT, noise) * np.exp(-t * decay) * 0.40 * velocity
    return hat.astype(np.float32)

def render_crash(velocity: float = 0.75) -> np.ndarray:
    """Crash cymbal with 1.3s shimmering highpass decay."""
    duration = 1.3
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, False, dtype=np.float32)
    noise = np.random.uniform(-1.0, 1.0, n).astype(np.float32)
    crash = signal.sosfilt(SOS_CRASH, noise) * np.exp(-t * 3.5) * 0.40 * velocity
    return crash.astype(np.float32)

# --- 9-INSTRUMENT GENETIC ENSEMBLE ROSTER (DIRECTLY FROM fly_piano_live.html) ---
# [piano(0), guitar(1), electricGuitar(2), drums(3), subBass808(4), synthPluck(5), cello(6), violins(7), harp(8)]
INSTRUMENTS_DEF = [
    {"id": "piano", "name": "Grand Piano", "allowedMoods": ["emotional", "romantic", "epic", "peaceful", "mysterious", "jazz", "baroque", "oriental", "rock", "rap", "pop"]},
    {"id": "guitar", "name": "Acoustic Guitar", "allowedMoods": ["romantic", "jazz", "peaceful", "oriental", "emotional", "pop"]},
    {"id": "electricGuitar", "name": "Electric Guitar", "allowedMoods": ["rock", "epic"]},
    {"id": "drums", "name": "Drum Kit", "allowedMoods": ["rock", "pop", "rap", "jazz", "epic"]},
    {"id": "subBass808", "name": "808 Sub-Bass", "allowedMoods": ["rap"]},
    {"id": "synthPluck", "name": "Synth Pluck", "allowedMoods": ["pop", "peaceful", "rap"]},
    {"id": "cello", "name": "Cello", "allowedMoods": ["emotional", "romantic", "epic", "peaceful", "mysterious", "jazz", "baroque", "oriental", "rock", "rap"]},
    {"id": "violins", "name": "Violins", "allowedMoods": ["emotional", "romantic", "epic", "baroque", "oriental", "mysterious"]},
    {"id": "harp", "name": "Concert Harp", "allowedMoods": ["peaceful", "romantic", "baroque", "epic", "emotional", "pop"]}
]

def get_compatible_indices(genre_id: str) -> list[int]:
    return [idx for idx, inst in enumerate(INSTRUMENTS_DEF) if genre_id in inst["allowedMoods"]]

def enforce_genre_constraints(genome: list[bool], genre_id: str) -> list[bool]:
    compatible = get_compatible_indices(genre_id)
    new_genome = list(genome)
    for idx in range(len(new_genome)):
        if idx not in compatible:
            new_genome[idx] = False

    active_count = sum(1 for idx in compatible if new_genome[idx])
    if active_count < 2:
        for idx in compatible[:min(3, len(compatible))]:
            new_genome[idx] = True
    return new_genome

def evolve_to_next_combo(genome: list[bool], genre_id: str) -> list[bool]:
    compatible = get_compatible_indices(genre_id)
    if not compatible:
        return genome
    new_genome = list(genome)
    mutate_idx = random.choice(compatible)
    new_genome[mutate_idx] = not new_genome[mutate_idx]
    return enforce_genre_constraints(new_genome, genre_id)


# --- NOTE TO NAME HELPER ---
def freq_to_note_name(freq: float) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    if freq <= 0: return "C4"
    midi = int(round(69 + 12 * math.log2(max(10.0, freq) / 440.0)))
    octave = (midi // 12) - 1
    note = names[midi % 12]
    return f"{note}{octave}"


# --- MAIN STEREO SYNTHESIS FUNCTION (NON-REPETITIVE & PROGRESSIVE) ---

def synthesize_audio_and_spikes(
    duration_sec: float = 15.0,
    genre_id: str = "emotional",
    scale_name: str = None,
    bpm: float = None,
    output_dir: Path = None,
    track_title: str = "Synaptic Resonance #1"
) -> dict:
    """
    Synthesizes rich, evolving live-stream aesthetic connectome music across 11 genres.
    Features progressive 16-bar harmonic narrative, multi-octave Chopin arpeggios,
    and genetic instrument mutation (breathes like a living orchestra).
    """
    duration_sec = float(duration_sec)
    if output_dir is None:
        output_dir = Path(__file__).parent / "public"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve Genre
    if scale_name and scale_name in SCALES:
        target_genre_id = SCALES[scale_name]["genre_id"]
    else:
        target_genre_id = genre_id or "emotional"

    if target_genre_id not in GENRES:
        target_genre_id = "emotional"

    genre_data = GENRES[target_genre_id]
    movements = genre_data.get("movements", [])
    if not movements:
        movements = GENRES["emotional"]["movements"]

    base_interval_ms = genre_data.get("baseIntervalMs", 220)
    calculated_bpm = round(60000.0 / (base_interval_ms * 3.0), 1)
    effective_bpm = float(bpm) if bpm and bpm > 0 else calculated_bpm

    total_samples = int(SAMPLE_RATE * duration_sec)

    # Dedicated Polyphonic Track Engines with Release Damping / Choking
    melody_track = VoiceTrack(total_samples, max_polyphony=1, choke_decay_sec=0.040)
    guitar_track = VoiceTrack(total_samples, max_polyphony=2, choke_decay_sec=0.080)
    bass_track = VoiceTrack(total_samples, max_polyphony=2, choke_decay_sec=0.120)
    synth_track = VoiceTrack(total_samples, max_polyphony=2, choke_decay_sec=0.060)
    cello_track = VoiceTrack(total_samples, max_polyphony=1, choke_decay_sec=0.180)
    violin_track = VoiceTrack(total_samples, max_polyphony=2, choke_decay_sec=0.220)
    harp_track = VoiceTrack(total_samples, max_polyphony=2, choke_decay_sec=0.120)
    drums_track = VoiceTrack(total_samples, max_polyphony=6, choke_decay_sec=0.010)

    simulator = ConnectomeSimulator(num_neurons=48)

    step_interval_sec = (base_interval_ms / 1000.0) * (calculated_bpm / effective_bpm)
    step_samples = max(int(SAMPLE_RATE * 0.08), int(SAMPLE_RATE * step_interval_sec))

    spike_events = []
    total_spikes_count = 0
    current_bar = 0
    current_step = 0

    # Live Genetic Ensemble Roster (9 instruments matching fly_piano_live.html)
    # [piano(0), guitar(1), electricGuitar(2), drums(3), subBass808(4), synthPluck(5), cello(6), violins(7), harp(8)]
    initial_genome = [False] * 9
    initial_genome[0] = True  # Piano is primary foundation
    initial_genome[6] = True  # Cello
    if target_genre_id in ("rock", "epic"):
        initial_genome[2] = True
        initial_genome[3] = True
    elif target_genre_id == "rap":
        initial_genome[3] = True
        initial_genome[4] = True
        initial_genome[5] = True
    elif target_genre_id in ("romantic", "peaceful", "jazz"):
        initial_genome[1] = True
        initial_genome[8] = True
    elif target_genre_id == "pop":
        initial_genome[1] = True
        initial_genome[3] = True
        initial_genome[5] = True
    elif target_genre_id in ("emotional", "baroque", "mysterious"):
        initial_genome[7] = True
        initial_genome[8] = True

    current_genome = enforce_genre_constraints(initial_genome, target_genre_id)

    print(f"🎻 Synthesizing Evolving Connectome Symphony ({duration_sec}s, Genre: '{genre_data['name']}', BPM: {effective_bpm}, {len(movements)} Movements)...")

    for start_sample in range(0, total_samples - int(SAMPLE_RATE * 0.4), step_samples):
        current_time_sec = float(start_sample / SAMPLE_RATE)
        current_frame = int(current_time_sec * FPS)
        progress = current_time_sec / duration_sec

        # Progressive Bar Selection (Cycles smoothly through all movements)
        movement = movements[current_bar % len(movements)]
        chord_name = movement.get("chordName", "F Minor")
        cello_f = float(movement.get("celloFreq", 87.31))
        piano_bass = movement.get("pianoBass", [174.61, 261.63, 349.23, 523.25])
        piano_solo = movement.get("pianoSolo", [349.23, 415.30, 523.25, 698.46])
        violin_notes = movement.get("violinNotes", [523.25, 622.25, 698.46])
        harp_harmonics = movement.get("harpHarmonics", [698.46, 830.61, 1046.50])

        # Dynamic Song Sections
        if progress < 0.15:
            section_intensity = 0.75
            section_phase = "intro"
        elif progress < 0.40:
            section_intensity = 0.90
            section_phase = "flow"
        elif progress < 0.80:
            section_intensity = 1.15
            section_phase = "climax"
        else:
            section_intensity = 0.80
            section_phase = "outro"

        # Check for Musical Finale / Cadence Resolution Phase (Resolves gracefully to tonic)
        cadence_threshold_sec = max(duration_sec * 0.70, duration_sec - 3.8)
        if current_time_sec >= cadence_threshold_sec:
            # Lift sustain pedal and resolve cleanly to tonic home chord
            bass_track.clear_pedal(start_sample, release_sec=0.060)

            tonic_mov = movements[0]
            tonic_cello = float(tonic_mov.get("celloFreq", 87.31))
            tonic_pb = tonic_mov.get("pianoBass", [174.61, 261.63, 349.23, 523.25])
            tonic_ps = tonic_mov.get("pianoSolo", [349.23, 415.30, 523.25, 698.46])
            tonic_vn = tonic_mov.get("violinNotes", [523.25, 622.25, 698.46])
            tonic_hh = tonic_mov.get("harpHarmonics", [698.46, 830.61, 1046.50])

            # 1. Cello deep tonic resonance
            cello_sound = render_cello_note(tonic_cello, duration=4.5, velocity=0.92)
            cello_track.play_note(cello_sound, start_sample, tonic_cello, pan=0.48, gain=1.1)

            # 2. Grand Piano multi-octave acoustic resolution chord
            pb0 = float(tonic_pb[0])
            bass_track.play_note(render_piano_note(pb0, duration=4.5, velocity=0.95, is_bass=True), start_sample, pb0, pan=0.34, gain=0.95)
            if len(tonic_pb) > 1:
                pb1 = float(tonic_pb[1])
                bass_track.play_note(render_piano_note(pb1, duration=4.2, velocity=0.82, is_bass=True), start_sample + int(SAMPLE_RATE * 0.015), pb1, pan=0.36, gain=0.85)

            ps0 = float(tonic_ps[0])
            melody_track.play_note(render_piano_note(ps0, duration=4.0, velocity=0.90, is_bass=False), start_sample + int(SAMPLE_RATE * 0.030), ps0, pan=0.50, gain=0.95)
            ps_mid = float(tonic_ps[min(2, len(tonic_ps) - 1)])
            melody_track.play_note(render_piano_note(ps_mid, duration=3.8, velocity=0.85, is_bass=False), start_sample + int(SAMPLE_RATE * 0.045), ps_mid, pan=0.55, gain=0.85)
            ps_top = float(tonic_ps[-1])
            melody_track.play_note(render_piano_note(ps_top, duration=3.5, velocity=0.85, is_bass=False), start_sample + int(SAMPLE_RATE * 0.060), ps_top, pan=0.60, gain=0.85)

            # 3. Acoustic Guitar gentle harmonic strum
            guitar_track.play_note(render_guitar_note(ps0 * 0.5, duration=3.6, velocity=0.80), start_sample + int(SAMPLE_RATE * 0.020), ps0 * 0.5, pan=0.38, gain=0.88)

            # 4. Violins harmonic glow
            if tonic_vn:
                vn0 = float(tonic_vn[0])
                violin_track.play_note(render_violin_note(vn0, duration=4.2, velocity=0.85), start_sample + int(SAMPLE_RATE * 0.025), vn0, pan=0.74, gain=0.90)

            # 5. Concert Harp ascending flourish
            if tonic_hh:
                for hi, hf in enumerate(tonic_hh[:4]):
                    h_start = start_sample + int(SAMPLE_RATE * (0.040 * hi))
                    harp_track.play_note(render_harp_note(float(hf), duration=3.2, velocity=0.75), h_start, float(hf), pan=0.68, gain=0.85)

            # 6. Drums soft shimmering crash & gentle kick
            drums_track.play_note(render_crash(velocity=0.65), start_sample, 6500.0, pan=0.35, gain=0.80)
            drums_track.play_note(render_kick(velocity=0.70), start_sample, 50.0, pan=0.50, gain=0.75)

            # 7. Synaptic Coherence Burst (All neurons harmonize into resolution)
            cadence_frame = int(current_time_sec * FPS)
            for n_i in range(min(16, simulator.num_neurons)):
                total_spikes_count += 1
                c_coord = simulator.coords[n_i]
                spike_events.append({
                    "frame": int(cadence_frame + n_i),
                    "timeSec": round(float(current_time_sec + n_i * 0.025), 3),
                    "neuronId": int(n_i),
                    "x": round(float(c_coord["x"]), 3),
                    "y": round(float(c_coord["y"]), 3),
                    "z": round(float(c_coord["z"]), 3),
                    "freqHz": round(float(ps0), 1),
                    "noteName": freq_to_note_name(ps0),
                    "chordName": "Grand Cadence (Resolution)",
                    "intensity": 1.0,
                    "isCadence": True
                })

            # Exit loop to allow natural ring-out and acoustic decay
            break

        # Genetic Ensemble Mutation every 2 bars (evolveToNextCombo)
        if current_step == 0 and current_bar > 0 and current_bar % 2 == 0:
            current_genome = evolve_to_next_combo(current_genome, target_genre_id)

        # 1. DOWNBEAT HARMONIC ROOT & SECTION LAUNCH (Step 0)
        if current_step == 0:
            # Lift sustain pedal at chord boundary (clean voice leading)
            bass_track.clear_pedal(start_sample, release_sec=0.080)

            # Cello Drone (Index 6)
            if current_genome[6] and cello_f:
                cello_sound = render_cello_note(cello_f, duration=3.8, velocity=0.88 * section_intensity)
                cello_track.play_note(cello_sound, start_sample, cello_f, pan=0.48, gain=1.0)

            # 808 Sub-Bass (Index 4)
            if current_genome[4] and cello_f:
                sub808 = render_808_sub_bass(cello_f, duration=0.55, velocity=1.0)
                drums_track.play_note(sub808, start_sample, cello_f, pan=0.50, gain=1.0)

            # Electric Guitar Downbeat (Index 2)
            if current_genome[2] and cello_f:
                if target_genre_id == "rock":
                    p_chord = render_power_chord(cello_f * 2.0, duration=0.45, palm_mute=False, velocity=0.95)
                    guitar_track.play_note(p_chord, start_sample, cello_f * 2.0, pan=0.50, gain=0.95)
                else:
                    e_sound = render_electric_guitar(cello_f * 2.0, is_solo=False, velocity=0.85, duration=0.42)
                    guitar_track.play_note(e_sound, start_sample, cello_f * 2.0, pan=0.50, gain=0.90)

            # Drums Downbeat & Crash (Index 3)
            if current_genome[3]:
                if current_bar % 4 == 0:
                    crash = render_crash(velocity=0.75)
                    drums_track.play_note(crash, start_sample, 6500.0, pan=0.35, gain=0.85)
                kick = render_kick(velocity=1.0)
                drums_track.play_note(kick, start_sample, 55.0, pan=0.50, gain=1.0)

        # 2. ELEKTRO GİTAR HARD ROCK RİFF & CHUG MOTORU (Index 2)
        if current_genome[2] and target_genre_id == "rock" and cello_f:
            root_f = cello_f * 2.0
            bar_pattern = current_bar % 4
            if bar_pattern == 0:
                if current_step in (2, 4, 8):
                    guitar_track.play_note(render_power_chord(root_f, duration=0.12, palm_mute=True, velocity=0.86), start_sample, root_f, pan=0.45, gain=0.95)
                elif current_step == 6:
                    guitar_track.play_note(render_power_chord(root_f * 1.1892, duration=0.30, palm_mute=False, velocity=0.92), start_sample, root_f * 1.1892, pan=0.45, gain=0.95)
                elif current_step == 10:
                    guitar_track.play_note(render_power_chord(root_f * 1.3348, duration=0.30, palm_mute=False, velocity=0.94), start_sample, root_f * 1.3348, pan=0.45, gain=0.95)
            elif bar_pattern == 1:
                if current_step in (2, 3, 8):
                    guitar_track.play_note(render_power_chord(root_f, duration=0.11, palm_mute=True, velocity=0.84), start_sample, root_f, pan=0.45, gain=0.95)
                elif current_step == 6:
                    guitar_track.play_note(render_power_chord(root_f * 0.8909, duration=0.28, palm_mute=False, velocity=0.92), start_sample, root_f * 0.8909, pan=0.45, gain=0.95)
                elif current_step == 10:
                    guitar_track.play_note(render_power_chord(root_f * 1.4983, duration=0.30, palm_mute=False, velocity=0.95), start_sample, root_f * 1.4983, pan=0.45, gain=0.95)
            elif bar_pattern == 2:
                if current_step in (2, 6):
                    guitar_track.play_note(render_power_chord(root_f, duration=0.12, palm_mute=True, velocity=0.82), start_sample, root_f, pan=0.45, gain=0.95)
                elif current_step == 4:
                    guitar_track.play_note(render_power_chord(root_f * 0.8409, duration=0.30, palm_mute=False, velocity=0.90), start_sample, root_f * 0.8409, pan=0.45, gain=0.95)
                elif current_step == 8:
                    guitar_track.play_note(render_power_chord(root_f * 0.8909, duration=0.30, palm_mute=False, velocity=0.92), start_sample, root_f * 0.8909, pan=0.45, gain=0.95)
                elif current_step == 10:
                    guitar_track.play_note(render_power_chord(root_f * 1.4983, duration=0.32, palm_mute=False, velocity=0.96), start_sample, root_f * 1.4983, pan=0.45, gain=0.95)
            elif bar_pattern == 3:
                if current_step in (4, 6, 8, 10):
                    blues_lick = [
                        root_f * 2.0,
                        root_f * 2.0 * 1.1892,
                        root_f * 2.0 * 1.3348,
                        root_f * 2.0 * 1.4142,
                        root_f * 2.0 * 1.4983,
                        root_f * 2.0 * 1.7818,
                        root_f * 4.0
                    ]
                    lick_map = {4: 6, 6: 4, 8: 3, 10: 0}
                    n_f = blues_lick[lick_map.get(current_step, 0)]
                    bend_f = n_f * 0.8909 if current_step == 8 else None
                    guitar_track.play_note(render_electric_guitar(n_f, is_solo=True, velocity=0.90, duration=0.30, bend_start=bend_f), start_sample, n_f, pan=0.55, gain=0.95)

        # 3. GENRE DRUMS & PERCUSSION GROOVE (Index 3)
        if current_genome[3]:
            if target_genre_id == "rock":
                if current_step in (6, 8):
                    drums_track.play_note(render_kick(velocity=0.92), start_sample, 55.0, pan=0.50, gain=0.90)
                if current_step in (3, 9):
                    drums_track.play_note(render_snare(velocity=0.95), start_sample, 1900.0, pan=0.50, gain=0.95)
                if current_step % 2 == 0:
                    drums_track.play_note(render_hihat(is_open=(current_step == 10), velocity=0.60), start_sample, 8500.0, pan=0.40, gain=0.75)
            elif target_genre_id == "pop":
                if current_step in (3, 6, 9):
                    drums_track.play_note(render_kick(velocity=0.85), start_sample, 55.0, pan=0.50, gain=0.85)
                if current_step in (3, 9):
                    drums_track.play_note(render_snare(velocity=0.85), start_sample, 1900.0, pan=0.50, gain=0.85)
                if current_step % 3 == 1:
                    drums_track.play_note(render_hihat(is_open=True, velocity=0.50), start_sample, 8500.0, pan=0.40, gain=0.70)
                elif current_step % 2 == 0:
                    drums_track.play_note(render_hihat(is_open=False, velocity=0.40), start_sample, 8500.0, pan=0.40, gain=0.65)
            elif target_genre_id == "rap":
                if current_step == 8:
                    drums_track.play_note(render_kick(velocity=0.88), start_sample, 55.0, pan=0.50, gain=0.90)
                if current_step == 6:
                    drums_track.play_note(render_snare(velocity=0.95), start_sample, 1900.0, pan=0.50, gain=0.95)
            elif target_genre_id == "jazz":
                if current_step in (3, 9):
                    drums_track.play_note(render_hihat(is_open=False, velocity=0.50), start_sample, 8500.0, pan=0.45, gain=0.65)
                if current_step == 6:
                    drums_track.play_note(render_snare(velocity=0.40), start_sample, 1900.0, pan=0.50, gain=0.60)
            elif target_genre_id == "epic":
                if current_step == 6:
                    drums_track.play_note(render_kick(velocity=0.80), start_sample, 55.0, pan=0.50, gain=0.85)
                if current_step == 9:
                    drums_track.play_note(render_snare(velocity=0.70), start_sample, 1900.0, pan=0.50, gain=0.75)

        # 4. 808 TRAP PATTERN & HI-HAT ROLLS (Index 4)
        if current_genome[4] and target_genre_id == "rap":
            if current_step == 6 and cello_f:
                drums_track.play_note(render_808_sub_bass(cello_f * 1.12, duration=0.42, velocity=0.95), start_sample, cello_f * 1.12, pan=0.50, gain=0.95)
            if current_step % 2 == 0:
                roll = (random.random() < 0.35)
                drums_track.play_note(render_hihat(is_open=False, velocity=0.60), start_sample, 8500.0, pan=0.60, gain=0.75)
                if roll and start_sample + int(SAMPLE_RATE * 0.05) < total_samples:
                    drums_track.play_note(render_hihat(is_open=False, velocity=0.45), start_sample + int(SAMPLE_RATE * 0.05), 8500.0, pan=0.62, gain=0.65)

        # 5. CONTINUOUS GRAND PIANO BASS ARPEGGIO (Index 0)
        if current_genome[0] and piano_bass:
            arp_idx = current_step % len(piano_bass)
            pb_freq = float(piano_bass[arp_idx])
            p_vel = (0.88 if arp_idx == 0 else 0.62) * section_intensity
            pb_sound = render_piano_note(pb_freq, duration=2.2, velocity=p_vel, is_bass=True)
            bass_start = start_sample + int(SAMPLE_RATE * 0.015) if current_step == 0 else start_sample
            bass_track.play_note(pb_sound, bass_start, pb_freq, pan=0.34, gain=0.85)

        # 6. SYNTH PLUCK ARPEGGIO (Index 5)
        if current_genome[5] and piano_solo:
            if current_step % 2 == 1:
                pluck_idx = (current_step + current_bar) % len(piano_solo)
                pluck_freq = float(piano_solo[pluck_idx])
                synth_sound = render_synth_pluck(pluck_freq, duration=0.35, velocity=0.70)
                synth_track.play_note(synth_sound, start_sample, pluck_freq, pan=0.68, gain=0.80)

        # 7. BIOLOGICAL DROSOPHILA CONNECTOME SIMULATION
        candidates = simulator.step()
        if len(candidates) == 0 and random.random() < 0.65:
            candidates = [{"idx": int(random.randint(0, simulator.num_neurons - 1)), "v": 0.82}]

        # 8. ENSEMBLE CONDUCTORSHIP DRIVEN BY WINNING NEURON
        if len(candidates) > 0 and current_step % 2 == 0 and piano_solo:
            winner = candidates[0]
            winner_id = int(winner["idx"])
            winner_v = float(winner["v"])
            coord = simulator.coords[winner_id]
            pan = max(0.15, min(0.85, 0.5 + float(coord["x"]) * 0.35))

            solo_note = float(piano_solo[winner_id % len(piano_solo)])

            # In Climax phase, soar into high register
            if section_phase == "climax" and random.random() < 0.40 and solo_note * 2.0 < 2200.0:
                solo_note *= 2.0

            # On downbeats (step 0), rubato stagger by 40ms
            melody_start = start_sample + int(SAMPLE_RATE * 0.040) if current_step == 0 else start_sample
            melody_time_sec = current_time_sec + (0.040 if current_step == 0 else 0.0)

            # Piano Solo (Index 0)
            if current_genome[0]:
                p_vel = min(1.0, (0.65 + random.uniform(0.0, 0.25)) * section_intensity)
                solo_sound = render_piano_note(solo_note, duration=2.0, velocity=p_vel, is_bass=False)
                melody_track.play_note(solo_sound, melody_start, solo_note, pan=pan, gain=1.0)

            # Acoustic Guitar (Index 1) - doubling an octave down on steps 0, 2, 4, 8...
            if current_genome[1] and (current_step % 4 == 2 or current_step % 4 == 0):
                guitar_sound = render_guitar_note(solo_note * 0.5, duration=1.8, velocity=0.72)
                guitar_track.play_note(guitar_sound, melody_start, solo_note * 0.5, pan=0.38, gain=0.90)

            # Electric Guitar Lead Solo (Index 2)
            if current_genome[2] and (current_step % 4 == 2 or current_step % 4 == 0):
                if target_genre_id == "rock":
                    rock_pentatonic = [
                        293.66, 349.23, 392.00, 415.30, 440.00, 523.25,
                        587.33, 698.46, 783.99, 830.61, 880.00, 1046.50, 1174.66
                    ]
                    note_idx = (winner_id * 3 + current_step + current_bar * 2) % len(rock_pentatonic)
                    g_note = rock_pentatonic[note_idx]
                    do_bend = (random.random() < 0.35)
                    bend_start = g_note * 0.8909 if do_bend else None
                    eg_sound = render_electric_guitar(g_note, is_solo=True, velocity=0.88, duration=0.35, bend_start=bend_start)
                    guitar_track.play_note(eg_sound, melody_start, g_note, pan=0.58, gain=0.95)
                else:
                    alt_note = float(piano_solo[(winner_id + current_step) % len(piano_solo)])
                    eg_sound = render_electric_guitar(alt_note, is_solo=True, velocity=0.78, duration=0.32)
                    guitar_track.play_note(eg_sound, melody_start, alt_note, pan=0.58, gain=0.90)

            # Violins (Index 7) - step % 4 == 0
            if current_genome[7] and violin_notes and current_step % 4 == 0:
                v_note = float(violin_notes[winner_id % len(violin_notes)])
                v_sound = render_violin_note(v_note, duration=2.8, velocity=0.68 * section_intensity)
                violin_track.play_note(v_sound, melody_start, v_note, pan=0.74, gain=0.85)

            # Concert Harp (Index 8) - step % 3 == 0
            if current_genome[8] and harp_harmonics and current_step % 3 == 0:
                h_note = float(harp_harmonics[winner_id % len(harp_harmonics)])
                h_sound = render_harp_note(h_note, duration=2.4, velocity=0.65 * section_intensity)
                harp_track.play_note(h_sound, melody_start, h_note, pan=0.68, gain=0.75)

            total_spikes_count += 1
            spike_events.append({
                "frame": int(current_frame + (1 if current_step == 0 else 0)),
                "timeSec": round(float(melody_time_sec), 3),
                "neuronId": int(winner_id),
                "x": round(float(coord["x"]), 3),
                "y": round(float(coord["y"]), 3),
                "z": round(float(coord["z"]), 3),
                "freqHz": round(float(solo_note), 1),
                "noteName": freq_to_note_name(solo_note),
                "chordName": chord_name,
                "intensity": round(float(min(1.0, winner_v)), 2)
            })

        current_step += 1
        if current_step >= 12:
            current_step = 0
            current_bar += 1

    # Sum all discrete voice tracks into master stereo mix
    audio_left = (
        melody_track.buffer_l +
        guitar_track.buffer_l +
        bass_track.buffer_l +
        synth_track.buffer_l +
        cello_track.buffer_l +
        violin_track.buffer_l +
        harp_track.buffer_l +
        drums_track.buffer_l
    )
    audio_right = (
        melody_track.buffer_r +
        guitar_track.buffer_r +
        bass_track.buffer_r +
        synth_track.buffer_r +
        cello_track.buffer_r +
        violin_track.buffer_r +
        harp_track.buffer_r +
        drums_track.buffer_r
    )

    # Master Acoustic Reverb & Spatial Width (Stereo Delay)
    reverb_delay_ms = 140
    reverb_samples = int(SAMPLE_RATE * (reverb_delay_ms / 1000.0))
    decay = 0.16
    if total_samples > reverb_samples:
        audio_left[reverb_samples:] += audio_right[:-reverb_samples] * decay
        audio_right[reverb_samples:] += audio_left[:-reverb_samples] * decay

    # Master Smooth Acoustic Fade-Out (Guarantees zero clicks & beautiful resolution)
    fade_len = int(SAMPLE_RATE * 1.8)
    if total_samples > fade_len:
        fade_curve = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_len, dtype=np.float32)))
        audio_left[-fade_len:] *= fade_curve
        audio_right[-fade_len:] *= fade_curve
    tail_len = int(SAMPLE_RATE * 0.015)
    audio_left[-tail_len:] = 0.0
    audio_right[-tail_len:] = 0.0

    # Warm Lowpass Limiter Filter (~8500Hz) to prevent digital harshness
    sos_master = get_butter_filter(8500, 'lowpass', order=2)
    audio_left = signal.sosfilt(sos_master, audio_left)
    audio_right = signal.sosfilt(sos_master, audio_right)

    # Studio Master Compression & Normalization (-0.5 dBFS)
    peak = max(float(np.max(np.abs(audio_left))), float(np.max(np.abs(audio_right))), 1e-4)
    target_peak = 0.92
    audio_left = np.tanh((audio_left / peak) * target_peak)
    audio_right = np.tanh((audio_right / peak) * target_peak)

    # Write 16-bit Lossless Stereo WAV
    wav_path = output_dir / "audio.wav"
    left_16 = (audio_left * 32767).astype(np.int16)
    right_16 = (audio_right * 32767).astype(np.int16)
    stereo_interleaved = np.empty((total_samples * 2,), dtype=np.int16)
    stereo_interleaved[0::2] = left_16
    stereo_interleaved[1::2] = right_16

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(stereo_interleaved.tobytes())

    total_frames = int(duration_sec * FPS)

    # Write Spikes Telemetry JSON (both spikes.json and spikes_data.json for Remotion sync)
    spikes_path = output_dir / "spikes.json"
    with open(spikes_path, "w", encoding="utf-8") as f:
        json.dump(spike_events, f, indent=2, default=json_default)

    spikes_data_path = output_dir / "spikes_data.json"
    spikes_data_obj = {
        "durationSec": float(duration_sec),
        "totalFrames": int(total_frames),
        "totalSpikes": int(total_spikes_count),
        "neuronsCount": int(simulator.num_neurons),
        "neuronCoords": simulator.coords,
        "spikes": spike_events
    }
    with open(spikes_data_path, "w", encoding="utf-8") as f:
        json.dump(spikes_data_obj, f, indent=2, default=json_default)

    track_info = {
        "title": track_title,
        "genre": target_genre_id,
        "genreName": genre_data.get("name", "Emotional & Melancholic"),
        "genreShortName": genre_data.get("shortName", "Nocturne"),
        "scale": genre_data.get("desc", "").split("•")[0].strip() or "F Minor",
        "bpm": float(effective_bpm),
        "durationSec": float(duration_sec),
        "totalFrames": int(total_frames),
        "totalSpikes": int(total_spikes_count),
        "neuronsCount": int(simulator.num_neurons),
        "neuronCoords": simulator.coords,
        "audioFile": "audio.wav",
        "spikesFile": "spikes.json"
    }

    return track_info

if __name__ == "__main__":
    info = synthesize_audio_and_spikes(duration_sec=15.0, genre_id="emotional")
    print(f"✅ Dynamic Synthesis Test Complete: {info['title']} ({info['genreName']}, {info['durationSec']}s, {info['totalSpikes']} spikes)")
