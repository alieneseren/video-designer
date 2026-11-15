import React, { useMemo } from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BasketballShortsProps, BasketballCutItem } from "../types";
import { resolveMediaSrc } from "../utils/media";

// ── KELİME DÜZEYİNDE KARAOKE ALTYAZI BİLEŞENİ (PUNCHY CHUNKED KARAOKE) ──
function chunkWordsSmart<T extends { word: string }>(words: T[]): T[][] {
  if (words.length === 0) return [];
  if (words.length <= 4) return [words];

  const compoundPatterns = [
    ["SAN", "ANTONIO"],
    ["DEREK", "FISHER"],
    ["JAMES", "HARDEN"],
    ["TRENT", "TUCKER"],
    ["SPORTS", "SCIENCE"],
    ["POINT", "FOUR"],
    ["ZERO", "POINT"],
    ["99TH", "PERCENTILE"],
    ["RED", "BACKBOARD"],
    ["BUZZER", "BEATER"],
    ["BODY", "WEIGHT"],
  ];

  function cannotSplitAfter(index: number): boolean {
    if (index >= words.length - 1) return false;
    const currentWord = words[index].word.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    const nextWord = words[index + 1].word.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    return compoundPatterns.some(
      ([first, second]) => currentWord === first && nextWord === second
    );
  }

  const chunks: T[][] = [];
  let currentChunk: T[] = [];

  for (let i = 0; i < words.length; i++) {
    currentChunk.push(words[i]);
    const remaining = words.length - 1 - i;

    const mustKeep = cannotSplitAfter(i);
    const reachedIdeal = currentChunk.length >= 3;
    const reachedMax = currentChunk.length >= 4;

    if (remaining === 1 && currentChunk.length < 4 && !reachedMax) {
      continue;
    }

    if (!mustKeep && (reachedMax || (reachedIdeal && remaining >= 2))) {
      chunks.push(currentChunk);
      currentChunk = [];
    }
  }

  if (currentChunk.length > 0) {
    if (currentChunk.length === 1 && chunks.length > 0) {
      chunks[chunks.length - 1].push(currentChunk[0]);
    } else {
      chunks.push(currentChunk);
    }
  }

  return chunks;
}

const BasketballSubtitles: React.FC<{
  sentences: BasketballShortsProps["sentences"];
}> = ({ sentences }) => {
  const frame = useCurrentFrame();

  const currentSentence = sentences.find(
    (s) => frame >= s.startFrame && frame < s.startFrame + s.durationInFrames
  );

  if (!currentSentence) return null;

  const words = currentSentence.words || [];

  // YouTube Shorts altın kuralı: Tek seferde 2-4 kelime (Punchy, odaklı ve ferah)
  let displayWords = words;
  if (words.length > 0) {
    const chunks = chunkWordsSmart(words);
    displayWords = chunks[0];
    for (const chunk of chunks) {
      const startF = chunk[0].startFrame;
      const endF = chunk[chunk.length - 1].endFrame;
      if (frame >= startF && frame <= endF) {
        displayWords = chunk;
        break;
      }
      if (frame >= startF) {
        displayWords = chunk;
      }
    }
  }

  return (
    <div
      style={{
        position: "absolute",
        bottom: 260,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "0 36px",
        zIndex: 50,
      }}
    >
      <div
        style={{
          background: "rgba(10, 12, 18, 0.90)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          border: "1.5px solid rgba(255, 255, 255, 0.22)",
          borderRadius: 22,
          padding: "16px 32px",
          maxWidth: "88%",
          boxShadow: "0 18px 50px rgba(0, 0, 0, 0.8)",
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          gap: "8px 12px",
          textAlign: "center",
        }}
      >
        {displayWords.length > 0 ? (
          displayWords.map((w, wIdx) => {
            const isActive = frame >= w.startFrame && frame < w.endFrame;
            const isPast = frame >= w.endFrame;

            return (
              <span
                key={`${w.startFrame}_${wIdx}`}
                style={{
                  fontFamily:
                    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                  fontSize: 44,
                  fontWeight: 900,
                  textTransform: "uppercase",
                  letterSpacing: "1px",
                  color: isActive
                    ? "#FFD700"
                    : isPast
                    ? "#FFFFFF"
                    : "rgba(255, 255, 255, 0.65)",
                  textShadow: isActive
                    ? "0 3px 10px rgba(0,0,0,0.9), 0 0 12px rgba(255, 215, 0, 0.7)"
                    : "0 2px 8px rgba(0, 0, 0, 0.8)",
                  display: "inline-block",
                  margin: "0 8px",
                  transition: "color 0.06s ease",
                }}
              >
                {w.word}
              </span>
            );
          })
        ) : (
          <span
            style={{
              fontFamily:
                "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
              fontSize: 40,
              fontWeight: 900,
              textTransform: "uppercase",
              letterSpacing: "1px",
              color: "#FFFFFF",
              textShadow: "0 2px 10px rgba(0,0,0,0.9)",
            }}
          >
            {currentSentence.text}
          </span>
        )}
      </div>
    </div>
  );
};

// ── KATEGORİ ROZETİ (TAM 4.0 SANİYEDE FADE-OUT İLE KAYBOLUR) ──
const CategoryBadge: React.FC<{
  badgeText: string;
  maxDurationFrames: number;
}> = ({ badgeText, maxDurationFrames }) => {
  const frame = useCurrentFrame();

  // 4 saniyeden (120 kare) sonra kesinlikle render etme!
  if (frame > maxDurationFrames) {
    return null;
  }

  // Giriş: 0 - 15 kare (fade in & slide down)
  // Sabit: 15 - 105 kare (tam görünür)
  // Çıkış: 105 - 120 kare (fade out & slide up)
  const opacity = interpolate(
    frame,
    [0, 15, maxDurationFrames - 15, maxDurationFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const translateY = interpolate(
    frame,
    [0, 15, maxDurationFrames - 15, maxDurationFrames],
    [-25, 0, 0, -25],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        position: "absolute",
        top: 130,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        zIndex: 60,
        opacity,
        transform: `translateY(${translateY}px)`,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          background: "rgba(12, 14, 20, 0.85)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1.5px solid rgba(255, 215, 0, 0.45)",
          borderRadius: 999,
          padding: "12px 34px",
          boxShadow:
            "0 10px 30px rgba(0, 0, 0, 0.6), inset 0 0 15px rgba(255, 215, 0, 0.15)",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span
          style={{
            fontFamily:
              "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            fontSize: 24,
            fontWeight: 900,
            letterSpacing: "2.5px",
            color: "#FFD700",
            textTransform: "uppercase",
            textShadow: "0 0 12px rgba(255, 215, 0, 0.5)",
          }}
        >
          {badgeText}
        </span>
      </div>
    </div>
  );
};

// ── SOSYAL CTA BUTONU (TEK SEFERLİK, 2 SANİYE GÖRÜNÜR) ──
const SocialCTAButton: React.FC<{
  totalDurationFrames: number;
}> = ({ totalDurationFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Bitişten 5 saniye önce başlar (total - 150), 2 saniye sürer (60 kare)
  const startFrame = Math.max(0, totalDurationFrames - 150);
  const endFrame = startFrame + 60;

  if (frame < startFrame || frame > endFrame) {
    return null;
  }

  const localFrame = frame - startFrame;

  // Spring animasyonu ile zıplayarak giriş
  const scale = spring({
    frame: localFrame,
    fps,
    config: { damping: 12, stiffness: 150 },
  });

  const opacity = interpolate(
    localFrame,
    [0, 10, 50, 60],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // İlk 20 kare kırmızı SUBSCRIBE, sonraki karelerde gri SUBSCRIBED
  const isSubscribed = localFrame > 22;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 480,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        zIndex: 55,
        opacity,
        transform: `scale(${scale})`,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          background: isSubscribed ? "#272727" : "#FF0000",
          border: isSubscribed ? "1px solid #444" : "1px solid rgba(255,255,255,0.4)",
          borderRadius: 999,
          padding: "14px 38px",
          display: "flex",
          alignItems: "center",
          gap: 12,
          boxShadow: "0 10px 30px rgba(0, 0, 0, 0.8)",
          transition: "background 0.2s ease",
        }}
      >
        <span
          style={{
            fontFamily:
              "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            fontSize: 26,
            fontWeight: 800,
            color: "#FFFFFF",
            letterSpacing: "1px",
          }}
        >
          {isSubscribed ? "✓ SUBSCRIBED" : "SUBSCRIBE"}
        </span>
      </div>
    </div>
  );
};

// ── ANA BASKETBALL SHORTS BİLEŞENİ ──
export const BasketballShorts: React.FC<BasketballShortsProps> = ({
  topic,
  categoryBadgeText = "🏀 SPORTS SCIENCE",
  badgeDurationFrames = 120, // 4.0 saniye
  audioPath,
  bgmPath,
  bgmVolume = 0.12,
  cuts,
  sentences,
  durationInFrames,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000", overflow: "hidden" }}>
      {/* 1. DİNAMİK KESMELER (GERÇEK MAÇ VİDEOLARI & HD FOTOĞRAFLAR) */}
      {cuts.map((cut, idx) => (
        <Sequence
          key={`${cut.id}_${idx}`}
          from={cut.startFrame}
          durationInFrames={cut.durationInFrames}
        >
          <CutRenderer cut={cut} />
        </Sequence>
      ))}

      {/* 2. SİNEMATİK VİGNETTE VE KONTRAST FİLTRESİ */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.65) 100%)",
          pointerEvents: "none",
          zIndex: 20,
        }}
      />

      {/* 3. KATEGORİ ROZETİ (TAM 4. SANİYEDE FADE-OUT OLUR) */}
      <CategoryBadge
        badgeText={categoryBadgeText}
        maxDurationFrames={badgeDurationFrames}
      />

      {/* 4. SOSYAL CTA BUTONU (TEK SEFERLİK, 2 SANİYE) */}
      <SocialCTAButton totalDurationFrames={durationInFrames} />

      {/* 5. KARAOKE ALTYAZILAR (SAF ZAMANLAMA, KESİNTİSİZ ÇIKIŞ) */}
      <BasketballSubtitles sentences={sentences} />

      {/* 6. SES KANALLARI */}
      {audioPath && <Audio src={resolveMediaSrc(audioPath) || audioPath} />}
      {bgmPath && <Audio src={resolveMediaSrc(bgmPath) || bgmPath} volume={bgmVolume} />}
    </AbsoluteFill>
  );
};

// ── TEKİL KESME RENDERER (VIDEO VEYA KEN BURNS PHOTO) ──
const CutRenderer: React.FC<{ cut: BasketballCutItem }> = ({ cut }) => {
  const frame = useCurrentFrame();
  const mediaSrc = resolveMediaSrc(cut.mediaPath) || cut.mediaPath;

  if (cut.mediaType === "video") {
    return (
      <AbsoluteFill>
        <OffthreadVideo
          src={mediaSrc}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </AbsoluteFill>
    );
  }

  // Fotoğraflar için pürüzsüz micro-zoom (Ken Burns)
  const scale = interpolate(
    frame,
    [0, cut.durationInFrames],
    [1.0, 1.08],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Img
        src={mediaSrc}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale})`,
        }}
      />
    </AbsoluteFill>
  );
};
