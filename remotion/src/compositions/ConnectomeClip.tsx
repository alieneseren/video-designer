import React, { useMemo } from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  staticFile,
  Audio,
} from "remotion";
import { useAudioData, visualizeAudio } from "@remotion/media-utils";
import { Activity, Radio, Sparkles, Disc, Music, Cpu, Zap, Volume2, ShieldCheck, Compass } from "lucide-react";

export interface NeuronCoord {
  id: number;
  x: number;
  y: number;
  z: number;
}

export interface SpikeEvent {
  frame: number;
  timeSec: number;
  neuronId: number;
  x: number;
  y: number;
  z: number;
  freqHz: number;
  intensity: number;
  chordName?: string;
  noteName?: string;
  isCadence?: boolean;
}

export interface ConnectomeClipProps {
  title?: string;
  subtitle?: string;
  scale?: string;
  bpm?: number;
  concept?: string;
  hook?: string;
  theme?: "cosmic" | "cyberpunk" | "biophilic";
  neuronsCount?: number;
  neuronCoords?: NeuronCoord[];
  spikes?: SpikeEvent[];
  isVertical?: boolean;
  audioPath?: string;
}

export const ConnectomeClip: React.FC<ConnectomeClipProps> = ({
  title = "NEURAL NOCTURNE // SEQUENCE I",
  subtitle = "DROSOPHILA WHOLE-BRAIN CONNECTOME SYNTHESIS",
  scale = "F Minor (Melancholic Nocturne)",
  bpm = 90.9,
  concept = "Biological simulation of 139,255 fruit fly neurons mapped to acoustic grand piano & cello.",
  hook = "What 139,000 biological brain neurons sound like playing a piano & cello",
  theme = "cosmic",
  neuronsCount = 48,
  neuronCoords = [],
  spikes = [],
  isVertical = true,
  audioPath = "audio.wav",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();

  // Load Audio
  const audioSource = staticFile(audioPath || "audio.wav");
  const audioData = useAudioData(audioSource);

  // 64 Frequency Bins
  const visualization = useMemo(() => {
    if (!audioData) return Array(64).fill(0.08);
    return visualizeAudio({
      fps,
      frame,
      audioData,
      numberOfSamples: 64,
    });
  }, [audioData, fps, frame]);

  // Audio Frequency Energy Bands
  const bass = useMemo(() => {
    const slice = visualization.slice(0, 8);
    const avg = slice.reduce((a, b) => a + b, 0) / slice.length;
    return Math.min(2.5, avg * 4.4);
  }, [visualization]);

  const mids = useMemo(() => {
    const slice = visualization.slice(8, 28);
    const avg = slice.reduce((a, b) => a + b, 0) / slice.length;
    return Math.min(2.5, avg * 3.8);
  }, [visualization]);

  const highs = useMemo(() => {
    const slice = visualization.slice(28, 64);
    const avg = slice.reduce((a, b) => a + b, 0) / slice.length;
    return Math.min(2.5, avg * 4.0);
  }, [visualization]);

  // Modern Color Palettes
  const themeColors = useMemo(() => {
    if (theme === "cyberpunk") {
      return {
        accent: "#00f0ff",
        secondary: "#f43f5e",
        tertiary: "#a855f7",
        glow: "rgba(0, 240, 255, 0.4)",
        bgGrad: "radial-gradient(ellipse at 50% 35%, rgba(244, 63, 94, 0.16) 0%, rgba(0, 240, 255, 0.10) 45%, #05060b 85%)",
        ribbonGrad: ["#00f0ff", "#f43f5e", "#a855f7"],
        activeBadge: "#f43f5e",
      };
    } else if (theme === "biophilic") {
      return {
        accent: "#10b981",
        secondary: "#06b6d4",
        tertiary: "#84cc16",
        glow: "rgba(16, 185, 129, 0.4)",
        bgGrad: "radial-gradient(ellipse at 50% 35%, rgba(16, 185, 129, 0.16) 0%, rgba(6, 182, 212, 0.10) 45%, #020704 85%)",
        ribbonGrad: ["#10b981", "#06b6d4", "#84cc16"],
        activeBadge: "#10b981",
      };
    }
    // Cosmic (Default Luxury Obsidian & Sapphire)
    return {
      accent: "#00f0ff",
      secondary: "#8b5cf6",
      tertiary: "#f59e0b",
      glow: "rgba(0, 240, 255, 0.35)",
      bgGrad: "radial-gradient(ellipse at 50% 35%, rgba(139, 92, 246, 0.18) 0%, rgba(0, 240, 255, 0.10) 45%, #030509 85%)",
      ribbonGrad: ["#00f0ff", "#8b5cf6", "#f59e0b"],
      activeBadge: "#00f0ff",
    };
  }, [theme]);

  // Spatial Starfield & Neurotransmitter Bokeh (3D Flow)
  const particles = useMemo(() => {
    const arr = [];
    for (let i = 0; i < 70; i++) {
      arr.push({
        id: i,
        x: ((i * 39) % 100),
        y: ((i * 61) % 100),
        size: (i % 3) + 1.2,
        speed: 0.12 + (i % 5) * 0.07,
        opacity: 0.25 + (i % 6) * 0.12,
      });
    }
    return arr;
  }, []);

  // Connectome Neurons (48 3D somas)
  const nodes = useMemo(() => {
    if (neuronCoords && neuronCoords.length > 0) return neuronCoords;
    const fallback: NeuronCoord[] = [];
    for (let i = 0; i < neuronsCount; i++) {
      const angle = (i / neuronsCount) * Math.PI * 2;
      const r = 0.38 + ((i * 19) % 40) / 75;
      fallback.push({
        id: i,
        x: Math.cos(angle) * r,
        y: Math.sin(angle) * r * 1.1,
        z: Math.sin(angle * 3) * 0.45,
      });
    }
    return fallback;
  }, [neuronCoords, neuronsCount]);

  // Synaptic Axon Edges
  const edges = useMemo(() => {
    const list: { from: NeuronCoord; to: NeuronCoord; id: string }[] = [];
    nodes.forEach((node, i) => {
      const n1 = nodes[(i + 1) % nodes.length];
      const n2 = nodes[(i + 3) % nodes.length];
      list.push({ from: node, to: n1, id: `${i}-${(i + 1) % nodes.length}` });
      if (i % 2 === 0) {
        list.push({ from: node, to: n2, id: `${i}-${(i + 3) % nodes.length}` });
      }
    });
    return list;
  }, [nodes]);

  // Active spikes in the last 20 frames
  const recentSpikes = useMemo(() => {
    return spikes.filter((s) => frame >= s.frame && frame <= s.frame + 20);
  }, [spikes, frame]);

  // Cadence Detection (Last 3.5 seconds)
  const cadenceFrameStart = durationInFrames - Math.round(fps * 3.5);
  const isCadenceActive = frame >= cadenceFrameStart;
  const cadenceProgress = isCadenceActive
    ? Math.min(1.0, (frame - cadenceFrameStart) / (fps * 3.5))
    : 0;

  // Master Fade to Black in final 1.2 seconds
  const fadeOutFrameStart = durationInFrames - Math.round(fps * 1.2);
  const masterFadeOpacity = frame >= fadeOutFrameStart
    ? interpolate(frame, [fadeOutFrameStart, durationInFrames], [1.0, 0.0], { extrapolateRight: "clamp" })
    : 1.0;

  // Motion dynamics
  const gyroSpin = (frame * 0.75) % 360;
  const connectomeRotation = (frame * 0.012) % (Math.PI * 2);
  const cameraZoom = 1.0 + (bass * 0.07) + (isCadenceActive ? cadenceProgress * 0.15 : 0);
  const bassShake = bass > 0.85 ? (Math.sin(frame * 3.0) * (bass - 0.85) * 5) : 0;

  // Geometry
  const centerX = width / 2;
  const centerY = isVertical ? height * 0.40 : height * 0.45;
  const discRadius = isVertical ? width * 0.33 : height * 0.30;

  // Time calculations
  const currentTotalSeconds = Math.floor(frame / fps);
  const curM = String(Math.floor(currentTotalSeconds / 60)).padStart(2, "0");
  const curS = String(currentTotalSeconds % 60).padStart(2, "0");
  const totalTotalSeconds = Math.floor(durationInFrames / fps);
  const totM = String(Math.floor(totalTotalSeconds / 60)).padStart(2, "0");
  const totS = String(totalTotalSeconds % 60).padStart(2, "0");
  const progressRatio = Math.min(1, frame / durationInFrames);

  // Active Chord & Latest Spike Telemetry
  const latestSpike = recentSpikes.length > 0 ? recentSpikes[recentSpikes.length - 1] : null;
  const currentChord = isCadenceActive
    ? "Grand Cadence (Resolution)"
    : (latestSpike?.chordName || scale);
  const currentNote = latestSpike?.noteName || "C4";
  const currentFreq = latestSpike ? Math.round(latestSpike.freqHz) : 440;

  // Real-time Active Instruments Detection
  const isPianoActive = Boolean(latestSpike) || mids > 0.4;
  const isCelloActive = bass > 0.35 || isCadenceActive;
  const isGuitarActive = highs > 0.55;
  const isDrumsActive = bass > 0.75 && !isCadenceActive;
  const isHarpActive = highs > 0.45 || isCadenceActive;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: "#020306",
        backgroundImage: themeColors.bgGrad,
        position: "relative",
        overflow: "hidden",
        fontFamily: "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif",
        color: "#ffffff",
        transform: `translateY(${bassShake}px)`,
        opacity: masterFadeOpacity,
      }}
    >
      <Audio src={audioSource} />

      {/* --- LAYER 1: CYBERNETIC DEPTH GRID & AMBIENT AURORA --- */}
      {/* 3D Horizon Grid Lines */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255,255,255,0.02) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
          maskImage: "radial-gradient(circle at 50% 40%, black 20%, transparent 75%)",
          WebkitMaskImage: "radial-gradient(circle at 50% 40%, black 20%, transparent 75%)",
          opacity: 0.6 + bass * 0.3,
          pointerEvents: "none",
        }}
      />

      {/* Pulsing Central Plasma Spotlight */}
      <div
        style={{
          position: "absolute",
          top: centerY - discRadius * 1.8,
          left: centerX - discRadius * 1.8,
          width: discRadius * 3.6,
          height: discRadius * 3.6,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${themeColors.accent}25 0%, ${themeColors.secondary}12 40%, transparent 70%)`,
          filter: "blur(50px)",
          transform: `scale(${cameraZoom})`,
          pointerEvents: "none",
        }}
      />

      {/* Floating Starlight Bokeh Particles */}
      {particles.map((p) => {
        const py = (p.y - (frame * p.speed)) % 100;
        const adjustedY = py < 0 ? py + 100 : py;
        const glow = bass * 1.8;
        return (
          <div
            key={p.id}
            style={{
              position: "absolute",
              left: `${p.x}%`,
              top: `${adjustedY}%`,
              width: p.size,
              height: p.size,
              borderRadius: "50%",
              backgroundColor: p.id % 2 === 0 ? themeColors.accent : "#ffffff",
              opacity: p.opacity + glow * 0.15,
              boxShadow: `0 0 ${p.size * 3}px ${themeColors.accent}`,
              pointerEvents: "none",
            }}
          />
        );
      })}

      {/* --- LAYER 2: TOP TELEMETRY BAR & LIVE BIO-STATUS --- */}
      <div
        style={{
          position: "absolute",
          top: isVertical ? 55 : 32,
          left: isVertical ? 35 : 60,
          right: isVertical ? 35 : 60,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 40,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 42,
              height: 42,
              borderRadius: 12,
              background: "rgba(255,255,255,0.04)",
              border: `1px solid ${themeColors.accent}40`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backdropFilter: "blur(14px)",
              boxShadow: `0 0 20px ${themeColors.accent}25`,
            }}
          >
            <Radio size={20} style={{ color: themeColors.accent }} />
          </div>
          <div>
            <div
              style={{
                fontSize: 10,
                fontFamily: "'JetBrains Mono', monospace",
                color: themeColors.accent,
                letterSpacing: "0.20em",
                fontWeight: 800,
                textTransform: "uppercase",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: themeColors.accent, display: "inline-block", boxShadow: `0 0 8px ${themeColors.accent}` }} />
              {isCadenceActive ? "SYNAPTIC RESOLUTION CADENCE" : "LIVE CONNECTOME SIMULATION"}
            </div>
            <div style={{ fontSize: isVertical ? 17 : 20, fontWeight: 800, color: "#fff", letterSpacing: "-0.02em" }}>
              FlyWire Whole-Brain Symphony
            </div>
          </div>
        </div>

        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 16px",
            borderRadius: 30,
            background: "rgba(10,14,24,0.75)",
            border: "1px solid rgba(255,255,255,0.12)",
            backdropFilter: "blur(12px)",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
          }}
        >
          <Zap size={13} style={{ color: themeColors.tertiary }} />
          <span style={{ color: "#ffffff", fontWeight: 700 }}>48 NEURON MATRIX</span>
        </div>
      </div>

      {/* --- LAYER 3: VIRAL HOOK CAPSULE (Top Centered) --- */}
      <div
        style={{
          position: "absolute",
          top: isVertical ? 134 : 90,
          left: 0,
          right: 0,
          textAlign: "center",
          zIndex: 35,
          padding: "0 35px",
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            padding: "9px 22px",
            borderRadius: 40,
            backgroundColor: "rgba(10, 14, 24, 0.85)",
            border: `1.5px solid ${themeColors.accent}45`,
            backdropFilter: "blur(20px)",
            boxShadow: `0 10px 35px ${themeColors.accent}20`,
          }}
        >
          <Sparkles size={15} style={{ color: themeColors.tertiary }} />
          <span style={{ fontSize: isVertical ? 13 : 15, fontWeight: 700, color: "#fff", letterSpacing: "0.01em" }}>
            {hook}
          </span>
        </div>
      </div>

      {/* --- LAYER 4: THE CENTERPIECE // 3D HOLOGRAPHIC BIO-CONNECTOME GYROSCOPE --- */}
      <div
        style={{
          position: "absolute",
          top: centerY - discRadius * 1.5,
          left: centerX - discRadius * 1.5,
          width: discRadius * 3.0,
          height: discRadius * 3.0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 20,
        }}
      >
        <svg
          style={{
            width: "100%",
            height: "100%",
            position: "absolute",
            inset: 0,
            overflow: "visible",
          }}
        >
          <defs>
            <linearGradient id="spectrumGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={themeColors.accent} />
              <stop offset="50%" stopColor={themeColors.secondary} />
              <stop offset="100%" stopColor={themeColors.tertiary} />
            </linearGradient>
            <radialGradient id="hologramCore" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#1e2438" stopOpacity="0.9" />
              <stop offset="70%" stopColor="#0a0e18" stopOpacity="0.95" />
              <stop offset="100%" stopColor="#030408" stopOpacity="1" />
            </radialGradient>
          </defs>

          {/* 64-BAND CIRCULAR FREQUENCY SPECTRUM BARS */}
          <g transform={`translate(${discRadius * 1.5}, ${discRadius * 1.5}) scale(${cameraZoom})`}>
            {visualization.map((val, idx) => {
              const angle = (idx / visualization.length) * Math.PI * 2;
              const barLen = Math.max(6, val * (discRadius * 0.48));
              const rInner = discRadius * 0.96;
              const rOuter = rInner + barLen;

              const x1 = Math.cos(angle) * rInner;
              const y1 = Math.sin(angle) * rInner;
              const x2 = Math.cos(angle) * rOuter;
              const y2 = Math.sin(angle) * rOuter;

              const isBassBand = idx < 10;
              return (
                <line
                  key={idx}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={isBassBand ? themeColors.accent : "url(#spectrumGradient)"}
                  strokeWidth={isVertical ? 3.5 : 4.8}
                  strokeLinecap="round"
                  opacity={0.85 + val * 0.15}
                  style={{
                    filter: isBassBand ? `drop-shadow(0 0 8px ${themeColors.accent})` : "none",
                  }}
                />
              );
            })}

            {/* Pulsing Bass Halo Rings */}
            <circle
              r={discRadius * 0.94 + bass * 16}
              fill="none"
              stroke={themeColors.accent}
              strokeWidth="2"
              opacity={0.4 + bass * 0.4}
              style={{ filter: `drop-shadow(0 0 10px ${themeColors.accent})` }}
            />
            <circle
              r={discRadius * 1.18 + mids * 20}
              fill="none"
              stroke={themeColors.secondary}
              strokeWidth="1.5"
              strokeDasharray="6 8"
              opacity={0.3 + mids * 0.3}
            />

            {/* CONNECTOME SYNAPTIC AXON FILAMENTS */}
            {edges.map((edge) => {
              const cos = Math.cos(connectomeRotation);
              const sin = Math.sin(connectomeRotation);

              const scaleR = discRadius * 0.68;
              const x1 = (edge.from.x * cos - edge.from.z * sin) * scaleR;
              const y1 = edge.from.y * scaleR;
              const x2 = (edge.to.x * cos - edge.to.z * sin) * scaleR;
              const y2 = edge.to.y * scaleR;

              const isSpiking = recentSpikes.some(
                (s) => s.neuronId === edge.from.id || s.neuronId === edge.to.id
              );

              return (
                <line
                  key={edge.id}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={isSpiking ? "#00ffff" : "rgba(255, 255, 255, 0.22)"}
                  strokeWidth={isSpiking ? 3.0 : 1.0}
                  opacity={isSpiking ? 1.0 : 0.35 + mids * 0.25}
                  style={{
                    filter: isSpiking ? "drop-shadow(0 0 8px #00ffff)" : "none",
                  }}
                />
              );
            })}

            {/* CONNECTOME NEURON SOMAS WITH EXPANDING CORONA PULSES */}
            {nodes.map((node) => {
              const cos = Math.cos(connectomeRotation);
              const sin = Math.sin(connectomeRotation);

              const scaleR = discRadius * 0.68;
              const rx = (node.x * cos - node.z * sin) * scaleR;
              const ry = node.y * scaleR;

              const activeSpike = recentSpikes.find((s) => s.neuronId === node.id);
              const isFiring = Boolean(activeSpike);

              const spikeAge = activeSpike ? frame - activeSpike.frame : 99;
              const coronaRadius = activeSpike
                ? interpolate(spikeAge, [0, 20], [6, 52], { extrapolateRight: "clamp" })
                : 0;
              const coronaOpacity = activeSpike
                ? interpolate(spikeAge, [0, 20], [1.0, 0.0], { extrapolateRight: "clamp" })
                : 0;

              return (
                <g key={node.id} transform={`translate(${rx}, ${ry})`}>
                  {isFiring && (
                    <circle
                      r={coronaRadius}
                      fill="none"
                      stroke={themeColors.accent}
                      strokeWidth="2.8"
                      opacity={coronaOpacity}
                      style={{ filter: `drop-shadow(0 0 10px ${themeColors.accent})` }}
                    />
                  )}
                  <circle
                    r={isFiring ? 10 : 5.0}
                    fill={isFiring ? "#ffffff" : "rgba(255,255,255,0.45)"}
                    stroke={isFiring ? themeColors.accent : "rgba(255,255,255,0.2)"}
                    strokeWidth={isFiring ? 2.5 : 1}
                    style={{
                      filter: isFiring ? `drop-shadow(0 0 12px ${themeColors.accent})` : "none",
                    }}
                  />
                </g>
              );
            })}
          </g>
        </svg>

        {/* 3D GYROSCOPE ORBITAL RINGS */}
        <div
          style={{
            width: discRadius * 1.85,
            height: discRadius * 1.85,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(16, 22, 36, 0.92) 0%, rgba(6, 9, 15, 0.96) 65%, #020408 100%)",
            border: `2px solid rgba(255,255,255,0.14)`,
            boxShadow: `0 0 60px rgba(0,0,0,0.85), 0 0 35px ${themeColors.accent}30`,
            position: "relative",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transform: `rotate(${gyroSpin}deg) scale(${cameraZoom})`,
            transition: "transform 0.05s ease-out",
          }}
        >
          {/* Orbital Depth Grooves */}
          <div style={{ position: "absolute", inset: 10, borderRadius: "50%", border: `1px dashed ${themeColors.accent}25` }} />
          <div style={{ position: "absolute", inset: 26, borderRadius: "50%", border: "1px solid rgba(255,255,255,0.06)" }} />
          <div style={{ position: "absolute", inset: 46, borderRadius: "50%", border: `1px dashed ${themeColors.secondary}25` }} />

          {/* Central Holographic Drosophila Sensation Sphere */}
          <div
            style={{
              width: discRadius * 0.78,
              height: discRadius * 0.78,
              borderRadius: "50%",
              background: `linear-gradient(135deg, ${themeColors.accent}35, ${themeColors.secondary}45)`,
              border: `2px solid ${themeColors.accent}`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: `0 0 40px ${themeColors.accent}45`,
              backdropFilter: "blur(10px)",
              transform: `rotate(${-gyroSpin}deg)`, // Counter-rotate text so it stays upright!
            }}
          >
            <div style={{ fontSize: isVertical ? 32 : 36, filter: `drop-shadow(0 0 12px ${themeColors.accent})` }}>
              🧠
            </div>
            <div
              style={{
                fontSize: 10,
                fontFamily: "'JetBrains Mono', monospace",
                fontWeight: 900,
                letterSpacing: "0.22em",
                color: "#ffffff",
                marginTop: 4,
              }}
            >
              DROSOPHILA
            </div>
            <div style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: themeColors.accent, fontWeight: 700 }}>
              {Math.round(bpm)} BPM • 48 NEURONS
            </div>
          </div>
        </div>

        {/* Dynamic Firing Note HUD Callout (Pops up when a neuron spikes) */}
        {latestSpike && (
          <div
            style={{
              position: "absolute",
              top: 20,
              right: 20,
              background: "rgba(10, 15, 28, 0.88)",
              border: `1.5px solid ${themeColors.accent}`,
              borderRadius: 12,
              padding: "6px 14px",
              boxShadow: `0 0 20px ${themeColors.accent}40`,
              backdropFilter: "blur(16px)",
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              fontWeight: 800,
              color: "#fff",
              zIndex: 30,
              animation: "fadeIn 0.2s ease",
            }}
          >
            <span style={{ color: themeColors.accent }}>⚡ SPIKE #{latestSpike.neuronId}:</span>
            <span style={{ color: "#fff" }}>{currentNote} ({currentFreq}Hz)</span>
          </div>
        )}
      </div>

      {/* --- LAYER 5: AUDIO-REACTIVE HORIZONTAL SOUNDWAVE RIBBON --- */}
      <div
        style={{
          position: "absolute",
          top: isVertical ? height * 0.65 : height * 0.70,
          left: 0,
          right: 0,
          height: 90,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 25,
          pointerEvents: "none",
        }}
      >
        <svg style={{ width: "100%", height: "100%", overflow: "visible" }}>
          <defs>
            <linearGradient id="ribbonGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={themeColors.ribbonGrad[0]} />
              <stop offset="50%" stopColor={themeColors.ribbonGrad[1]} />
              <stop offset="100%" stopColor={themeColors.ribbonGrad[2]} />
            </linearGradient>
          </defs>
          {/* Dynamic Sine-Wave Ribbon Path */}
          {(() => {
            const points: string[] = [];
            const segments = 48;
            for (let i = 0; i <= segments; i++) {
              const x = (i / segments) * width;
              const sampleVal = visualization[i % visualization.length] || 0.1;
              const amp = sampleVal * 45 * (0.8 + bass * 0.6);
              const waveY = 45 + Math.sin(frame * 0.12 + i * 0.4) * amp;
              points.push(`${i === 0 ? "M" : "L"} ${x} ${waveY}`);
            }
            return (
              <>
                <path
                  d={points.join(" ")}
                  fill="none"
                  stroke="url(#ribbonGrad)"
                  strokeWidth="3.2"
                  strokeLinecap="round"
                  style={{ filter: `drop-shadow(0 0 10px ${themeColors.accent})` }}
                />
                <path
                  d={points.join(" ")}
                  fill="none"
                  stroke="rgba(255,255,255,0.7)"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                />
              </>
            );
          })()}
        </svg>
      </div>

      {/* --- LAYER 6: REAL-TIME ACTIVE INSTRUMENT BADGES --- */}
      <div
        style={{
          position: "absolute",
          bottom: isVertical ? 250 : 190,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: isVertical ? 8 : 14,
          zIndex: 35,
          padding: "0 20px",
          flexWrap: "wrap",
        }}
      >
        {[
          { label: "GRAND PIANO", icon: "🎹", active: isPianoActive },
          { label: "GUITAR", icon: "🎸", active: isGuitarActive },
          { label: "CELLO & STRINGS", icon: "🎻", active: isCelloActive },
          { label: "DRUMS", icon: "🥁", active: isDrumsActive },
          { label: "CONCERT HARP", icon: "🪕", active: isHarpActive },
        ].map((inst, i) => (
          <div
            key={i}
            style={{
              padding: isVertical ? "5px 10px" : "6px 14px",
              borderRadius: 8,
              backgroundColor: inst.active ? "rgba(0, 240, 255, 0.15)" : "rgba(255,255,255,0.03)",
              border: `1px solid ${inst.active ? themeColors.accent : "rgba(255,255,255,0.08)"}`,
              boxShadow: inst.active ? `0 0 15px ${themeColors.accent}35` : "none",
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: isVertical ? 10 : 11,
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 700,
              color: inst.active ? "#ffffff" : "rgba(255,255,255,0.4)",
              transition: "all 0.15s ease",
            }}
          >
            <span>{inst.icon}</span>
            <span>{inst.label}</span>
            {inst.active && (
              <span style={{ width: 5, height: 5, borderRadius: "50%", backgroundColor: themeColors.accent, boxShadow: `0 0 6px ${themeColors.accent}` }} />
            )}
          </div>
        ))}
      </div>

      {/* --- LAYER 7: AVANT-GARDE GLASSMORPHISM MUSIC PLAYER CARD --- */}
      <div
        style={{
          position: "absolute",
          bottom: isVertical ? 45 : 30,
          left: isVertical ? 25 : 80,
          right: isVertical ? 25 : 80,
          zIndex: 40,
        }}
      >
        <div
          style={{
            background: "rgba(11, 15, 25, 0.82)",
            border: "1.5px solid rgba(255, 255, 255, 0.14)",
            borderRadius: 22,
            padding: isVertical ? "20px 24px" : "24px 36px",
            backdropFilter: "blur(28px)",
            boxShadow: "0 25px 70px rgba(0,0,0,0.75), 0 0 30px rgba(0,240,255,0.08)",
          }}
        >
          {/* Card Header Row: Scale & Active Chord */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  padding: "4px 12px",
                  borderRadius: 6,
                  backgroundColor: `${themeColors.accent}18`,
                  border: `1px solid ${themeColors.accent}45`,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10,
                  fontWeight: 800,
                  color: themeColors.accent,
                  letterSpacing: "0.15em",
                }}
              >
                {scale.toUpperCase()}
              </div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.75)", fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}>
                {currentChord}
              </div>
            </div>

            {/* Pulsing Equalizer Bars */}
            <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 18 }}>
              {[0.5, 0.9, 0.6, 1.0, 0.7, 0.95, 0.4].map((h, i) => {
                const dynamicH = Math.max(4, h * 18 * (0.6 + bass * 0.45));
                return (
                  <div
                    key={i}
                    style={{
                      width: 3.5,
                      height: dynamicH,
                      backgroundColor: themeColors.accent,
                      borderRadius: 2,
                      boxShadow: `0 0 6px ${themeColors.accent}`,
                    }}
                  />
                );
              })}
            </div>
          </div>

          {/* Track Title & Play Icon */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ flex: 1, overflow: "hidden" }}>
              <h1
                style={{
                  fontSize: isVertical ? 22 : 26,
                  fontWeight: 900,
                  color: "#ffffff",
                  letterSpacing: "-0.02em",
                  margin: 0,
                  lineHeight: 1.2,
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                  textOverflow: "ellipsis",
                  overflow: "hidden",
                }}
              >
                {title}
              </h1>
              <p
                style={{
                  fontSize: 12,
                  color: "rgba(255,255,255,0.7)",
                  margin: "4px 0 0",
                  letterSpacing: "0.02em",
                  whiteSpace: "nowrap",
                  textOverflow: "ellipsis",
                  overflow: "hidden",
                }}
              >
                {concept}
              </p>
            </div>

            <div
              style={{
                width: 46,
                height: 46,
                borderRadius: "50%",
                backgroundColor: themeColors.accent,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#05060a",
                boxShadow: `0 0 25px ${themeColors.accent}90`,
                flexShrink: 0,
                marginLeft: 16,
              }}
            >
              <Music size={22} />
            </div>
          </div>

          {/* Audio Scrubber & Progress */}
          <div>
            <div
              style={{
                height: 6,
                borderRadius: 4,
                backgroundColor: "rgba(255,255,255,0.12)",
                overflow: "hidden",
                position: "relative",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${progressRatio * 100}%`,
                  background: `linear-gradient(90deg, ${themeColors.accent}, ${themeColors.secondary})`,
                  boxShadow: `0 0 12px ${themeColors.accent}`,
                }}
              />
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: "rgba(255,255,255,0.55)",
                marginTop: 8,
              }}
            >
              <span>{curM}:{curS}</span>
              <span style={{ color: themeColors.accent, fontWeight: 800 }}>
                {isCadenceActive ? "RESOLVING FINALE" : `SYNAPSE FLUX: ${Math.round(bass * 80 + 20)}%`}
              </span>
              <span>{totM}:{totS}</span>
            </div>
          </div>
        </div>
      </div>

      {/* --- LAYER 8: GRAND CADENCE FINALE BANNER (Appears during the resolution chord) --- */}
      {isCadenceActive && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
            pointerEvents: "none",
            opacity: interpolate(cadenceProgress, [0, 0.3, 0.8, 1.0], [0, 1.0, 1.0, 0.3]),
          }}
        >
          <div
            style={{
              padding: "16px 36px",
              borderRadius: 30,
              background: "rgba(6, 8, 15, 0.92)",
              border: `2px solid ${themeColors.accent}`,
              boxShadow: `0 0 60px ${themeColors.accent}60`,
              backdropFilter: "blur(24px)",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 24, marginBottom: 6 }}>✨</div>
            <div
              style={{
                fontSize: isVertical ? 16 : 20,
                fontWeight: 900,
                letterSpacing: "0.15em",
                color: "#ffffff",
                fontFamily: "'JetBrains Mono', monospace",
                textTransform: "uppercase",
              }}
            >
              SYNAPTIC HARMONY RESOLVED
            </div>
            <div style={{ fontSize: 12, color: themeColors.accent, fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
              139,255 Biological Neurons • Final Cadence Complete
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
