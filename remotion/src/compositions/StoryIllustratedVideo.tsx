import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { StoryIllustratedVideoProps, StoryScene } from "../types";

// ─────────────────────────────────────────────────────────────
// Tekil Sahne Bileşeni: Sinematik Ken Burns + Çizim + Altyazı
// ─────────────────────────────────────────────────────────────

const SceneView: React.FC<{
  scene: StoryScene;
  theme: StoryIllustratedVideoProps["theme"];
}> = ({ scene, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const duration = Math.max(1, scene.durationInFrames);
  const progress = Math.min(1, Math.max(0, frame / duration));

  // 1. Giriş ve Çıkış Opaklık / Scale Geçişleri
  const enterSpring = spring({
    frame,
    fps,
    config: { damping: 20, stiffness: 120 },
  });

  const exitOpacity = interpolate(
    frame,
    [duration - 8, duration],
    [1, 0.3],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // 2. Kamera Hareketi (Ken Burns / Pan / Zoom)
  const effect = scene.cameraEffect || "ken_burns";
  let scale = 1.05;
  let translateX = 0;
  let translateY = 0;

  if (effect === "zoom_in") {
    scale = interpolate(progress, [0, 1], [1.02, 1.18]);
    translateY = interpolate(progress, [0, 1], [0, -15]);
  } else if (effect === "zoom_out") {
    scale = interpolate(progress, [0, 1], [1.2, 1.03]);
    translateY = interpolate(progress, [0, 1], [-15, 0]);
  } else if (effect === "pan_left") {
    scale = 1.12;
    translateX = interpolate(progress, [0, 1], [30, -30]);
  } else if (effect === "pan_right") {
    scale = 1.12;
    translateX = interpolate(progress, [0, 1], [-30, 30]);
  } else if (effect === "shake") {
    scale = 1.08;
    translateX = Math.sin(frame * 0.45) * 4;
    translateY = Math.cos(frame * 0.35) * 3;
  } else {
    // Default ken_burns
    scale = interpolate(progress, [0, 1], [1.04, 1.16]);
    translateX = interpolate(progress, [0, 1], [-12, 12]);
    translateY = interpolate(progress, [0, 1], [8, -14]);
  }

  // 3. Tema Renkleri & Çerçeve Stilleri
  const themeStyles = {
    cinematic_dark: {
      filter: "contrast(106%) saturate(108%) brightness(96%)",
      vignetteColor: "rgba(0, 0, 0, 0.75)",
      badgeBg: "rgba(18, 20, 26, 0.85)",
      badgeBorder: "rgba(255, 215, 0, 0.35)",
      badgeText: "#FFE600",
      textColor: "#FFFFFF",
      accentColor: "#F59E0B",
    },
    comic_ink: {
      filter: "contrast(115%) saturate(110%)",
      vignetteColor: "rgba(10, 10, 15, 0.85)",
      badgeBg: "rgba(0, 0, 0, 0.9)",
      badgeBorder: "#EF4444",
      badgeText: "#EF4444",
      textColor: "#FFFFFF",
      accentColor: "#EF4444",
    },
    fairytale: {
      filter: "contrast(102%) saturate(120%) brightness(102%)",
      vignetteColor: "rgba(20, 10, 30, 0.65)",
      badgeBg: "rgba(30, 20, 45, 0.85)",
      badgeBorder: "rgba(192, 132, 252, 0.5)",
      badgeText: "#E879F9",
      textColor: "#FAF5FF",
      accentColor: "#C084FC",
    },
    cozy_vintage: {
      filter: "sepia(18%) contrast(104%) saturate(95%) brightness(98%)",
      vignetteColor: "rgba(25, 18, 12, 0.7)",
      badgeBg: "rgba(35, 25, 18, 0.85)",
      badgeBorder: "rgba(217, 119, 6, 0.4)",
      badgeText: "#FBBF24",
      textColor: "#FEF3C7",
      accentColor: "#D97706",
    },
  }[theme || "cinematic_dark"];

  // 4. Altyazı Kelime Vurgusu
  const captionWords = (scene.captionText || "").split(" ");
  const isHighlight = (word: string) => {
    const clean = word.toLowerCase().replace(/[^a-z0-9ğüşıöç]/g, "");
    if (scene.highlightWords && scene.highlightWords.length > 0) {
      return scene.highlightWords.some((hw) => hw.toLowerCase().includes(clean));
    }
    return word.length > 6 || word.includes("!") || word.includes("?");
  };

  return (
    <AbsoluteFill
      style={{
        opacity: Math.min(enterSpring, exitOpacity),
        backgroundColor: "#050508",
        overflow: "hidden",
      }}
    >
      {/* ─── Ana Çizim Görseli (Ken Burns Hareketli) ─── */}
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `scale(${scale}) translate3d(${translateX}px, ${translateY}px, 0)`,
          transformOrigin: "center center",
          willChange: "transform",
        }}
      >
        <Img
          src={staticFile(scene.imagePath)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: themeStyles.filter,
          }}
        />
      </div>

      {/* ─── Sinematik Vignette & Gölge Geçişi ─── */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse at center, transparent 45%, ${themeStyles.vignetteColor} 100%)`,
          pointerEvents: "none",
        }}
      />

      {/* ─── Üst ve Alt Sinematik Letterbox Gradyanı ─── */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 240,
          background: "linear-gradient(to bottom, rgba(0,0,0,0.85) 0%, transparent 100%)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 480,
          background: "linear-gradient(to top, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.6) 50%, transparent 100%)",
          pointerEvents: "none",
        }}
      />

      {/* ─── Sahne Altyazı Kartı (Avant-Garde Glassmorphism) ─── */}
      {scene.captionText && (
        <div
          style={{
            position: "absolute",
            bottom: 140,
            left: 48,
            right: 48,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              padding: "24px 32px",
              borderRadius: 24,
              backgroundColor: themeStyles.badgeBg,
              backdropFilter: "blur(18px)",
              border: `1.5px solid ${themeStyles.badgeBorder}`,
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.15)",
              maxWidth: "92%",
              textAlign: "center",
              transform: `translateY(${interpolate(enterSpring, [0, 1], [30, 0])}px)`,
            }}
          >
            <p
              style={{
                margin: 0,
                fontSize: 38,
                fontWeight: 700,
                lineHeight: 1.35,
                color: themeStyles.textColor,
                fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                letterSpacing: "-0.01em",
                textShadow: "0 2px 8px rgba(0, 0, 0, 0.8)",
              }}
            >
              {captionWords.map((word, wIdx) => {
                const highlighted = isHighlight(word);
                return (
                  <span
                    key={wIdx}
                    style={{
                      display: "inline-block",
                      marginRight: 8,
                      color: highlighted ? themeStyles.badgeText : themeStyles.textColor,
                      fontWeight: highlighted ? 900 : 700,
                      transform: highlighted ? "scale(1.05)" : "none",
                      transition: "all 0.2s ease",
                    }}
                  >
                    {word}
                  </span>
                );
              })}
            </p>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────
// Ana Kompozisyon: StoryIllustratedVideo
// ─────────────────────────────────────────────────────────────

export const StoryIllustratedVideo: React.FC<StoryIllustratedVideoProps> = ({
  title,
  author,
  scenes = [],
  audioPath,
  bgmPath,
  bgmVolume = 0.15,
  theme = "cinematic_dark",
  watermarkText,
}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {/* ─── Sahne Dizilimi (Sequences) ─── */}
      {scenes.map((scene) => (
        <Sequence
          key={scene.id}
          from={scene.startFrame}
          durationInFrames={scene.durationInFrames}
        >
          <SceneView scene={scene} theme={theme} />
        </Sequence>
      ))}

      {/* ─── Üst Başlık Rozeti (Sabit UI Katmanı) ─── */}
      <div
        style={{
          position: "absolute",
          top: 72,
          left: 48,
          right: 48,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 50,
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 12,
            padding: "10px 22px",
            borderRadius: 999,
            backgroundColor: "rgba(10, 10, 15, 0.75)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(255, 255, 255, 0.15)",
          }}
        >
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              backgroundColor: "#10B981",
              boxShadow: "0 0 10px #10B981",
            }}
          />
          <span
            style={{
              color: "#FFFFFF",
              fontSize: 22,
              fontWeight: 800,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
              fontFamily: "system-ui, sans-serif",
            }}
          >
            {title || "HİKAYE DİYARI"}
          </span>
        </div>

        {(author || watermarkText) && (
          <div
            style={{
              padding: "8px 18px",
              borderRadius: 999,
              backgroundColor: "rgba(0, 0, 0, 0.5)",
              backdropFilter: "blur(8px)",
              color: "rgba(255, 255, 255, 0.7)",
              fontSize: 18,
              fontWeight: 600,
              fontFamily: "system-ui, sans-serif",
            }}
          >
            {author ? `@${author}` : watermarkText}
          </div>
        )}
      </div>

      {/* ─── İlerleme Çubuğu (Shorts Scrubber) ─── */}
      <div
        style={{
          position: "absolute",
          bottom: 12,
          left: 24,
          right: 24,
          height: 4,
          borderRadius: 2,
          backgroundColor: "rgba(255, 255, 255, 0.2)",
          overflow: "hidden",
          zIndex: 60,
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${(frame / Math.max(1, scenes.reduce((acc, s) => Math.max(acc, s.startFrame + s.durationInFrames), 30))) * 100}%`,
            backgroundColor: "#F59E0B",
            borderRadius: 2,
            boxShadow: "0 0 8px #F59E0B",
          }}
        />
      </div>

      {/* ─── Ses Parçaları (Anlatıcı TTS + BGM) ─── */}
      {audioPath && (
        <Audio
          src={staticFile(audioPath)}
          volume={1.0}
        />
      )}

      {bgmPath && (
        <Audio
          src={staticFile(bgmPath)}
          volume={bgmVolume}
          loop
        />
      )}
    </AbsoluteFill>
  );
};
