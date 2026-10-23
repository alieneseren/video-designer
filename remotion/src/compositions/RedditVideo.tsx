import React, { useMemo } from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Video,
} from "remotion";
import { ArrowBigUp, MessageSquare, Share2, Award } from "lucide-react";
import { RedditVideoProps } from "../types";
import { resolveMediaSrc } from "../utils/media";

export const RedditVideo: React.FC<RedditVideoProps> = ({
  question,
  subreddit,
  author,
  upvotes,
  avatarPath,
  bgVideoPath,
  cardDurationFrames = 180, // Default 6 seconds for intro card
  audioPath,
  bgmPath,
  bgmVolume = 0.18,
  captions = [],
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const resolvedAvatar = resolveMediaSrc(avatarPath);
  const resolvedBgVideo = resolveMediaSrc(bgVideoPath);
  const resolvedAudio = resolveMediaSrc(audioPath);
  const resolvedBgm = resolveMediaSrc(bgmPath);

  // Kancayı Başa Çekme & İlk 3 Saniye Kuralı:
  // Kart ekranda asla 6-8 saniye kalarak videoyu boğmamalı.
  // En fazla 2.8 saniye (85 kare) kalarak kancayı verir ve hızlıca videoya yol açar!
  const effectiveCardDuration = Math.min(cardDurationFrames, 85);

  // Reddit card appearance spring (hızlı, vurucu yay animasyonu)
  const cardEntrance = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 140 },
  });

  // Card exit animation (2.5 - 2.8s arasında dinamik yukarı süzülme ve küçülme)
  const cardExitProgress = interpolate(
    frame,
    [effectiveCardDuration - 18, effectiveCardDuration],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const cardScale = interpolate(cardEntrance, [0, 1], [0.75, 1]) * (1 - cardExitProgress * 0.18);
  const cardOpacity = interpolate(cardEntrance, [0, 1], [0, 1]) * (1 - cardExitProgress);
  const cardTranslateY = interpolate(cardEntrance, [0, 1], [80, 0]) - (cardExitProgress * 70);

  // Arka plan videosu için sürekli hafif dinamik zoom (izleyiciyi hipnotize eden mikro-hareket)
  const bgScale = interpolate(frame, [0, 450], [1.02, 1.08], {
    extrapolateRight: "clamp",
  });

  // Subtle floating levitation
  const floatY = Math.sin(frame / 20) * 6;

  // Active caption segment
  const activeCaption = useMemo(() => {
    return captions.find(
      (c) => frame >= c.startFrame && frame < c.startFrame + c.durationInFrames
    );
  }, [captions, frame]);

  // Caption spring
  const captionSpring = activeCaption
    ? spring({
        frame: frame - activeCaption.startFrame,
        fps,
        config: { damping: 13, stiffness: 200 },
      })
    : 1;

  const captionScale = interpolate(captionSpring, [0, 1], [0.82, 1.04]);
  const captionOpacity = interpolate(captionSpring, [0, 1], [0, 1]);

  // Altyazı konumu: Kart ekrandayken altta, kart çıktıktan sonra odak noktası olan dikey merkeze (%36) geçiş
  const captionBottomPercent = interpolate(
    frame,
    [effectiveCardDuration - 15, effectiveCardDuration + 5],
    [18, 36],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000", overflow: "hidden" }}>
      {/* ── BACKGROUND ASMR VIDEO LAYER ── */}
      {resolvedBgVideo ? (
        <AbsoluteFill>
          <Video
            src={resolvedBgVideo}
            loop
            muted
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              filter: "brightness(0.85) contrast(1.05)",
              transform: `scale(${bgScale})`,
            }}
          />
          {/* Subtle cinematic vignette */}
          <AbsoluteFill
            style={{
              background:
                "radial-gradient(circle at center, transparent 40%, rgba(0, 0, 0, 0.5) 100%)",
            }}
          />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill
          style={{
            background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)",
          }}
        />
      )}

      {/* ── INTRO REDDIT QUESTION CARD (Hızlı Kanca: Max 2.8s) ── */}
      {frame < effectiveCardDuration && (
        <div
          style={{
            position: "absolute",
            top: "24%",
            left: 54,
            right: 54,
            zIndex: 40,
            opacity: cardOpacity,
            transform: `translateY(${cardTranslateY + floatY}px) scale(${cardScale})`,
            transformOrigin: "center center",
          }}
        >
          <div
            style={{
              backgroundColor: "rgba(18, 18, 18, 0.94)",
              backdropFilter: "blur(20px)",
              borderRadius: 36,
              border: "2px solid rgba(255, 255, 255, 0.14)",
              padding: "40px 44px",
              boxShadow: "0 24px 60px rgba(0, 0, 0, 0.7), 0 0 40px rgba(255, 69, 0, 0.15)",
              display: "flex",
              flexDirection: "column",
              gap: 24,
            }}
          >
            {/* Header: Subreddit & Author */}
            <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: "50%",
                  overflow: "hidden",
                  backgroundColor: "#ff4500",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 4px 14px rgba(255, 69, 0, 0.4)",
                  border: "2px solid rgba(255, 255, 255, 0.2)",
                }}
              >
                {resolvedAvatar ? (
                  <img
                    src={resolvedAvatar}
                    alt={author}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                ) : (
                  <span style={{ fontSize: 34, fontWeight: "bold", color: "#fff" }}>
                    r/
                  </span>
                )}
              </div>

              <div style={{ display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span
                    style={{
                      fontSize: 32,
                      fontWeight: 800,
                      color: "#ffffff",
                      letterSpacing: "-0.5px",
                    }}
                  >
                    {subreddit}
                  </span>
                  <span
                    style={{
                      fontSize: 20,
                      color: "#818384",
                      fontWeight: 500,
                    }}
                  >
                    • 3 hr. ago
                  </span>
                </div>
                <span style={{ fontSize: 24, color: "#818384", fontWeight: 500 }}>
                  Posted by {author}
                </span>
              </div>
            </div>

            {/* Question / Hook Title */}
            <h1
              style={{
                margin: 0,
                fontSize: 44,
                lineHeight: 1.3,
                fontWeight: 800,
                color: "#f8fafc",
                letterSpacing: "-0.5px",
                fontFamily:
                  "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
              }}
            >
              {question}
            </h1>

            {/* Footer: Upvotes, Comments, Share */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 20,
                paddingTop: 12,
                borderTop: "1px solid rgba(255, 255, 255, 0.08)",
                color: "#818384",
              }}
            >
              {/* Upvote Pill */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  backgroundColor: "rgba(255, 255, 255, 0.08)",
                  padding: "10px 20px",
                  borderRadius: 24,
                }}
              >
                <ArrowBigUp size={32} color="#ff4500" fill="#ff4500" />
                <span style={{ fontSize: 26, fontWeight: 700, color: "#f8fafc" }}>
                  {upvotes}
                </span>
              </div>

              {/* Comments Pill */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  backgroundColor: "rgba(255, 255, 255, 0.08)",
                  padding: "10px 20px",
                  borderRadius: 24,
                }}
              >
                <MessageSquare size={26} color="#818384" />
                <span style={{ fontSize: 24, fontWeight: 600 }}>2.4k</span>
              </div>

              {/* Award Pill */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  backgroundColor: "rgba(255, 255, 255, 0.08)",
                  padding: "10px 18px",
                  borderRadius: 24,
                }}
              >
                <Award size={26} color="#ffd700" />
              </div>

              {/* Share Pill */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  backgroundColor: "rgba(255, 255, 255, 0.08)",
                  padding: "10px 18px",
                  borderRadius: 24,
                  marginLeft: "auto",
                }}
              >
                <Share2 size={26} color="#818384" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── KINETIC TIKTOK-STYLE SUBTITLES (OVERLAY) ── */}
      {activeCaption && (
        <div
          style={{
            position: "absolute",
            bottom: `${captionBottomPercent}%`,
            left: 36,
            right: 36,
            zIndex: 45,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            textAlign: "center",
            opacity: captionOpacity,
            transform: `scale(${captionScale})`,
          }}
        >
          <div
            style={{
              backgroundColor: "rgba(0, 0, 0, 0.75)",
              backdropFilter: "blur(12px)",
              padding: "16px 36px",
              borderRadius: 30,
              border: "2px solid rgba(255, 235, 59, 0.35)",
              boxShadow: "0 12px 35px rgba(0, 0, 0, 0.8), 0 0 25px rgba(255, 235, 59, 0.2)",
            }}
          >
            <span
              style={{
                fontSize: 54,
                fontWeight: 900,
                color: "#FFE500",
                letterSpacing: "-0.5px",
                textShadow: "0 3px 12px rgba(0, 0, 0, 0.95), 0 0 20px rgba(255, 229, 0, 0.5)",
                fontFamily:
                  "-apple-system, BlinkMacSystemFont, 'Impact', 'Segoe UI', Roboto, sans-serif",
                textTransform: "uppercase",
              }}
            >
              {activeCaption.text}
            </span>
          </div>
        </div>
      )}

      {/* ── AUDIO TRACKS ── */}
      {resolvedAudio && <Audio src={resolvedAudio} />}
      {resolvedBgm && <Audio src={resolvedBgm} volume={bgmVolume} loop />}
    </AbsoluteFill>
  );
};
