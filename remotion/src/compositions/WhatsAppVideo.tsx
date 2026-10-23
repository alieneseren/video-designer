import React, { useMemo } from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Video,
} from "remotion";
import {
  Phone,
  Video as VideoCamIcon,
  MoreVertical,
  ArrowLeft,
  Check,
  CheckCheck,
  Smile,
  Paperclip,
  Camera,
  Mic,
  Wifi,
} from "lucide-react";
import { WhatsAppVideoProps } from "../types";
import { resolveMediaSrc } from "../utils/media";

const SENDER_COLORS = [
  "#d32f2f", // Red
  "#e67e22", // Warm Orange
  "#d97706", // Amber
  "#8b5cf6", // Purple
  "#0ea5e9", // Sky Blue
  "#10b981", // Emerald
  "#ec4899", // Pink
];

function getSenderColor(name?: string, explicitColor?: string): string {
  if (explicitColor) return explicitColor;
  if (!name) return "#d32f2f";
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % SENDER_COLORS.length;
  return SENDER_COLORS[index];
}

function extractReactionEmoji(text: string): string | null {
  if (!text) return null;
  const emojis = text.match(/\p{Extended_Pictographic}/gu);
  if (emojis && emojis.length > 0) {
    return emojis[emojis.length - 1];
  }
  return null;
}

interface EmotionAnalysis {
  hasShock: boolean;
  hasAnger: boolean;
  hasHumor: boolean;
  isClimax: boolean;
  isVoiceNote: boolean;
}

function analyzeMessageEmotion(text: string, isNearEnd: boolean): EmotionAnalysis {
  if (!text) {
    return { hasShock: false, hasAnger: false, hasHumor: false, isClimax: false, isVoiceNote: false };
  }
  const lower = text.toLowerCase();
  const isVoiceNote = text.startsWith("[SES") || text.startsWith("[VOICE") || text.includes("🎙️");

  const shockKeywords = [
    "arkandaydım",
    "arkandaydim",
    "ifşa",
    "yakaladım",
    "yakalandın",
    "öldü",
    "ölmüş",
    "polisi",
    "baban",
    "story",
    "gerizekalı",
    "yalan",
    "kiminle",
    "ayrılalım",
    "bitti",
    "sen mi",
    "senmişsin",
  ];
  const shockEmojis = ["💀", "😱", "😳", "🤡", "👀", "🔪"];
  const hasShock =
    shockEmojis.some((e) => text.includes(e)) ||
    shockKeywords.some((k) => lower.includes(k)) ||
    text.includes("?!") ||
    text.includes("!?");

  const angerKeywords = [
    "kim",
    "kime",
    "neredesin",
    "beğendin",
    "delirtme",
    "hesap",
    "saçmalama",
    "ne alaka",
    "sus",
    "çıldır",
  ];
  const angerEmojis = ["😡", "😤", "🤬", "👊"];
  const hasAnger = angerEmojis.some((e) => text.includes(e)) || angerKeywords.some((k) => lower.includes(k));

  const humorEmojis = ["😂", "🤣", "😆"];
  const humorKeywords = ["ahah", "jsjs", "tövbe", "troll"];
  const hasHumor = humorEmojis.some((e) => text.includes(e)) || humorKeywords.some((k) => lower.includes(k));

  const isClimax = isNearEnd && (hasShock || hasAnger || text.length > 55);

  return { hasShock, hasAnger, hasHumor, isClimax, isVoiceNote };
}

// Kinetic intelligent keyword highlighter for punchlines & emotional words
const renderHighlightedText = (
  text: string,
  isUser: boolean,
  isBubbleActive: boolean = false,
  elapsedFrames: number = 99
) => {
  if (!text) return null;
  const words = text.split(" ");
  return words.map((word, wIdx) => {
    const cleanWord = word.replace(/[.,/#!$%^&*;:{}=\-_`~()?"'’]/g, "");
    const lower = cleanWord.toLowerCase();

    // 1. ALL CAPS words (minimum 2 chars)
    const isAllCaps =
      cleanWord.length >= 2 && cleanWord === cleanWord.toUpperCase() && !/^\d+$/.test(cleanWord);

    // 2. Capitalized proper nouns in the middle of sentences
    const isCapitalizedProperNoun =
      wIdx > 0 &&
      cleanWord.length >= 3 &&
      /^[A-ZÇĞİÖŞÜ][a-zçğıöşü]+$/.test(cleanWord) &&
      !["Ben", "Sen", "Biz", "Ama", "Fakat", "Oysa"].includes(cleanWord);

    // 3. Numbers, currencies, or values
    const isNumberOrValue =
      /^\d+$/.test(cleanWord) ||
      ["bin", "milyon", "tl", "euro", "dolar"].includes(lower);

    // 4. Emotional high-impact dramatic keywords
    const isDramaticKeyword = [
      "berk",
      "merve",
      "iskoçyalı",
      "mini",
      "etekli",
      "kilt",
      "boğa",
      "meydanında",
      "gayda",
      "mendebur",
      "story",
      "arkandaydım",
      "yalan",
      "ifşa",
      "aldattın",
      "yakaladım",
      "sevgili",
      "ayrılalım",
      "delirtme",
      "saçmalama",
      "kanıt",
      "video",
      "fotoğraf",
      "rezil",
      "engellemiş",
      "engelleyeyim",
    ].includes(lower);

    const shouldHighlight = isAllCaps || isCapitalizedProperNoun || isNumberOrValue || isDramaticKeyword;

    if (shouldHighlight) {
      // Dynamic micro-pop scale on entrance when this bubble is active
      const popScale = isBubbleActive && elapsedFrames < 14
        ? 1.0 + Math.sin(Math.min(1, elapsedFrames / 10) * Math.PI) * 0.08
        : 1.0;

      return (
        <span
          key={wIdx}
          style={{
            display: "inline-block",
            transform: `scale(${popScale})`,
            transformOrigin: "center center",
            background: isUser
              ? "linear-gradient(135deg, rgba(167, 243, 208, 0.95) 0%, rgba(110, 231, 183, 1) 100%)"
              : "linear-gradient(135deg, rgba(254, 240, 138, 0.95) 0%, rgba(250, 204, 21, 1) 100%)",
            color: "#0f172a",
            fontWeight: 800,
            padding: "2px 7px",
            borderRadius: 7,
            margin: "0 2px",
            boxShadow: "0 2px 5px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.6)",
            border: isUser
              ? "1px solid rgba(5, 150, 105, 0.25)"
              : "1px solid rgba(217, 119, 6, 0.25)",
            letterSpacing: "-0.2px",
          }}
        >
          {word}{" "}
        </span>
      );
    }
    return word + " ";
  });
};

export const WhatsAppVideo: React.FC<WhatsAppVideoProps> = ({
  contactName,
  contactAvatar,
  statusText,
  audioPath,
  bgmPath,
  bgmVolume = 0.12,
  bgVideoPath,
  layout = "dublaj_style",
  watermarkText,
  instagramUsername = "",
  wallpaperPath,
  isGroup = false,
  groupParticipants = "",
  language = "tr",
  messages = [],
}) => {
  const isTr = language === "tr" || language.startsWith("tr");
  const effectiveStatusText = statusText || (isTr ? "çevrimiçi" : "online");
  const effectiveWatermark = (watermarkText && watermarkText.trim()) ? watermarkText.trim() : (isTr ? "yazanyazana" : "crazyychats");
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const resolvedAvatar = resolveMediaSrc(contactAvatar);
  const resolvedAudio = resolveMediaSrc(audioPath);
  const resolvedBgm = resolveMediaSrc(bgmPath);
  const resolvedBgVideo = resolveMediaSrc(bgVideoPath);

  // Dynamic aesthetic wallpaper fallback to ensure distinct backgrounds across videos
  const defaultWp = useMemo(() => {
    const wallpapers = [
      "/media/doodle_beige.jpg",
      "/media/botanical_shadow.jpg",
      "/media/pastel_gradient.jpg",
      "/media/cozy_wood.jpg",
      "/media/floral_pastel.jpg",
      "/media/urban_wall.jpg",
    ];
    let hash = 0;
    const key = contactName || "chat";
    for (let i = 0; i < key.length; i++) {
      hash = key.charCodeAt(i) + ((hash << 5) - hash);
    }
    return wallpapers[Math.abs(hash) % wallpapers.length];
  }, [contactName]);

  const resolvedWallpaper = resolveMediaSrc(wallpaperPath || defaultWp);

  const isDublaj = layout === "dublaj_style" || !layout;
  const isCompact = layout === "compact_top";

  // Accurate height calculation of each message bubble for pixel-perfect dynamic scrolling
  const messageHeights = useMemo(() => {
    return messages.map((m) => {
      const isIncoming = m.sender !== "user";
      const isVoice =
        (m.text || "").startsWith("[SES") ||
        (m.text || "").startsWith("[VOICE") ||
        (m.text || "").includes("🎙️");

      if (isVoice) {
        const senderHeader = isIncoming ? 32 : 0;
        return 96 + senderHeader + 18;
      }

      const text = m.text || "";
      // Account for explicit newlines as well as natural wrap (~36 chars per line on 34px font)
      const textLines = text.split("\n");
      let totalLines = 0;
      for (const tLine of textLines) {
        totalLines += Math.max(1, Math.ceil((tLine.trim().length || 1) / 36));
      }

      const senderHeader = isIncoming ? 32 : 0;
      const textHeight = totalLines * 44; // 34px font * 1.3 line-height
      const timestampHeight = 22;
      const bubblePadding = 24; // 14px top + 10px bottom
      const bubbleMargin = 18; // 18px marginBottom
      const reactionExtra = extractReactionEmoji(text) ? 14 : 0;

      return senderHeader + textHeight + timestampHeight + bubblePadding + bubbleMargin + reactionExtra;
    });
  }, [messages]);

  // Safe viewport height: in dublaj_style, the scroll container is 1200px (y=140 to 1340).
  // Total usable inner height is ~1160px. With 75px reserved for the typing indicator
  // bubble and 35px bottom padding, messages comfortably fill up to 1050px before
  // needing any scroll. This keeps 5-7 full messages visible on screen simultaneously!
  const safeViewportHeight = isDublaj ? 1050 : isCompact ? 710 : 1600;
  const DATE_CHIP_HEIGHT = 68;

  const targetScrollPerMessage = useMemo(() => {
    let cumulative = DATE_CHIP_HEIGHT;
    return messageHeights.map((h) => {
      cumulative += h;
      if (cumulative <= safeViewportHeight) {
        return 0;
      }
      return cumulative - safeViewportHeight;
    });
  }, [messageHeights, safeViewportHeight]);

  // Currently active message index
  const activeMessageIndex = useMemo(() => {
    let activeIdx = -1;
    for (let i = 0; i < messages.length; i++) {
      if (frame >= messages[i].startFrame) {
        activeIdx = i;
      }
    }
    return activeIdx;
  }, [frame, messages]);

  // Spring-driven smooth scroll interpolation
  const scrollOffset = useMemo(() => {
    if (activeMessageIndex < 0) return 0;
    const currentTarget = targetScrollPerMessage[activeMessageIndex] || 0;
    const prevTarget =
      activeMessageIndex > 0 ? targetScrollPerMessage[activeMessageIndex - 1] || 0 : 0;

    if (currentTarget === prevTarget) {
      return currentTarget;
    }

    const currentMsg = messages[activeMessageIndex];
    const scrollSpring = spring({
      frame: Math.max(0, frame - currentMsg.startFrame + 2),
      fps,
      config: { damping: 16, stiffness: 120 },
    });

    return prevTarget + (currentTarget - prevTarget) * scrollSpring;
  }, [activeMessageIndex, frame, fps, messages, targetScrollPerMessage]);

  // ── VIRAL SUSPENSE HOOK: CLIMAX PUNCH-IN & SHOCK CAMERA SHAKE ──
  const isNearClimax = activeMessageIndex >= Math.max(0, messages.length - 2);
  const currentMsgObj = activeMessageIndex >= 0 ? messages[activeMessageIndex] : null;
  const climaxProgress = spring({
    frame: isNearClimax && currentMsgObj ? Math.max(0, frame - currentMsgObj.startFrame) : 0,
    fps,
    config: { damping: 14, stiffness: 80 },
  });
  const cameraZoom = isNearClimax ? interpolate(climaxProgress, [0, 1], [1.0, 1.036]) : 1.0;

  const hasShockEmotion = useMemo(() => {
    if (!currentMsgObj) return false;
    const txt = currentMsgObj.text || "";
    return (
      txt.includes("😱") ||
      txt.includes("🤯") ||
      txt.toLowerCase().includes("yok artık") ||
      txt.toLowerCase().includes("oha")
    );
  }, [currentMsgObj]);

  const shockShake =
    hasShockEmotion && currentMsgObj
      ? Math.sin(Math.max(0, frame - currentMsgObj.startFrame) * 1.6) *
        Math.max(0, 3.5 - (frame - currentMsgObj.startFrame) * 0.35)
      : 0;

  // ── DYNAMIC TYPING INDICATOR ENGINE WITH HESITATION PAUSE ──
  const typingInfo = useMemo(() => {
    for (let i = 0; i < messages.length; i++) {
      const m = messages[i];
      const typingDuration = 24;
      const typingStart = Math.max(0, m.startFrame - typingDuration);
      if (frame >= typingStart && frame < m.startFrame) {
        const isNearEnd = i >= messages.length - 2;
        const emotion = analyzeMessageEmotion(m.text, isNearEnd);
        return {
          isTyping: true,
          sender: m.sender,
          senderName: m.senderName || contactName,
          senderAvatar: m.senderAvatar,
          senderColor: m.senderColor,
          typingStart,
          hasHesitation: emotion.hasShock || emotion.hasAnger,
        };
      }
    }
    return { isTyping: false };
  }, [frame, messages, contactName]);

  const dynamicStatusText = useMemo(() => {
    if (typingInfo.isTyping && typingInfo.sender === "contact") {
      const tFrame = frame - (typingInfo.typingStart || 0);
      if (typingInfo.hasHesitation && tFrame >= 11 && tFrame <= 16) {
        return isGroup ? (groupParticipants || (isTr ? "Grup Üyeleri" : "Group Members")) : (isTr ? "çevrimiçi" : "online");
      }
      if (isTr) {
        return isGroup ? `${typingInfo.senderName || "Birisi"} yazıyor...` : "yazıyor...";
      } else {
        return isGroup ? `${typingInfo.senderName || "Someone"} is typing...` : "typing...";
      }
    }
    if (isGroup) {
      return groupParticipants || (isTr ? "Ali, Mehmet, Ayşe, Zehra, Sen" : "Alex, Mike, Sarah, You");
    }
    return effectiveStatusText;
  }, [typingInfo, effectiveStatusText, frame, isGroup, groupParticipants, isTr]);

  // ── REACTIVE EMOTION & DYNAMIC CINEMATIC CAMERA SYSTEM ──
  const activeEmotion = useMemo(() => {
    if (activeMessageIndex < 0) {
      return { hasShock: false, hasAnger: false, hasHumor: false, isClimax: false, isVoiceNote: false };
    }
    const curMsg = messages[activeMessageIndex];
    const isNearEnd = activeMessageIndex >= messages.length - 2;
    return analyzeMessageEmotion(curMsg.text, isNearEnd);
  }, [activeMessageIndex, messages]);

  const activeMessage = activeMessageIndex >= 0 ? messages[activeMessageIndex] : null;
  const framesIntoActive =
    activeMessageIndex >= 0 ? frame - messages[activeMessageIndex].startFrame : 0;

  // 1. Tactile Impact Punch
  const punchSpring = useMemo(() => {
    if (activeMessageIndex < 0) return 1;
    const curMsg = messages[activeMessageIndex];
    return spring({
      frame: Math.max(0, frame - curMsg.startFrame),
      fps,
      config: { damping: 10, stiffness: 220, mass: 0.4 },
    });
  }, [activeMessageIndex, frame, fps, messages]);

  const cameraPunch =
    activeMessageIndex >= 0 ? interpolate(punchSpring, [0, 1], [1.025, 1.0]) : 1.0;

  // 2. Slow continuous ambient zoom
  const totalDuration = useMemo(() => {
    if (messages.length === 0) return 900;
    return messages[messages.length - 1].startFrame + 90;
  }, [messages]);

  const ambientZoom = interpolate(frame, [0, Math.max(1, totalDuration)], [1.0, 1.03], {
    extrapolateRight: "clamp",
  });

  // 3. Reactive Crash Zoom on Shock/Plot Twist
  const crashSpring = useMemo(() => {
    if (!activeEmotion.hasShock || activeMessageIndex < 0) return 1;
    return spring({
      frame: Math.max(0, framesIntoActive),
      fps,
      config: { damping: 12, stiffness: 180, mass: 0.5 },
    });
  }, [activeEmotion.hasShock, activeMessageIndex, framesIntoActive, fps]);

  const shockZoom = activeEmotion.hasShock ? interpolate(crashSpring, [0, 1], [1.0, 1.08]) : 1.0;

  // 4. Heartbeat Climax Pulse on Climax Moments
  const isHeartbeat = activeEmotion.isClimax && framesIntoActive < 45;
  const heartbeatScale = isHeartbeat
    ? 1.0 + Math.sin(framesIntoActive * 0.35) * 0.02 * Math.max(0, 1 - framesIntoActive / 45)
    : 1.0;

  const cameraScale = cameraPunch * ambientZoom * shockZoom * heartbeatScale;

  // 5. Haptic Impact Screen Shake on Anger/Shout
  const shakeDecay = Math.max(0, 1 - framesIntoActive / 9);
  const shakeX =
    (activeEmotion.hasAnger || activeEmotion.hasShock) && framesIntoActive >= 0 && framesIntoActive < 9
      ? Math.sin(framesIntoActive * 2.8) * 8 * shakeDecay
      : 0;
  const shakeY =
    (activeEmotion.hasAnger || activeEmotion.hasShock) && framesIntoActive >= 0 && framesIntoActive < 9
      ? Math.cos(framesIntoActive * 3.2) * 6 * shakeDecay
      : 0;

  // 6. Dynamic Mood Atmosphere Color Overlay
  const moodStyle = useMemo(() => {
    if (activeEmotion.hasAnger) {
      return { color: "#ef4444", opacity: 0.12 };
    }
    if (activeEmotion.hasShock) {
      return { color: "#1e293b", opacity: 0.16 };
    }
    if (activeEmotion.hasHumor) {
      return { color: "#f59e0b", opacity: 0.08 };
    }
    return { color: "transparent", opacity: 0 };
  }, [activeEmotion]);

  // 7. Organic Cinematic Handheld Steadicam Breathing
  const handheldDriftX = Math.sin(frame * 0.032) * 2.4;
  const handheldDriftY = Math.cos(frame * 0.026) * 1.8;
  const handheldTilt = Math.sin(frame * 0.016) * 0.22;

  // 8. 3D Gyroscope Perspective Tilt (Real Physical Phone Effect)
  const gyroRotateX = Math.sin(frame * 0.018) * 1.8;
  const gyroRotateY = Math.cos(frame * 0.024) * 2.2;

  // 9. Shock Moment Chromatic Aberration / RGB Glitch (3-4 frame impact)
  const isShockGlitch = activeEmotion.hasShock && framesIntoActive >= 0 && framesIntoActive < 5;
  const glitchOffset = isShockGlitch ? (5 - framesIntoActive) * 2.5 : 0;
  const glitchFilter = isShockGlitch
    ? `drop-shadow(${glitchOffset}px 0 rgba(239, 68, 68, 0.75)) drop-shadow(-${glitchOffset}px 0 rgba(14, 165, 233, 0.75))`
    : "none";

  // 10. Dynamic BGM Bass Drop / Low-Pass Muffle on Shock/Climax
  const dynamicBgmVolume = activeEmotion.hasShock && framesIntoActive < 45
    ? bgmVolume * 0.15
    : bgmVolume;

  // 11. WhatsApp Incoming Call Interruption Card
  const isCallMoment = activeMessage && (
    activeMessage.text.includes("[ARAMA]") ||
    activeMessage.text.includes("[CALL]") ||
    (activeEmotion.isClimax && activeEmotion.hasShock && framesIntoActive >= 10 && framesIntoActive <= 75)
  );

  const cleanWatermark = effectiveWatermark.replace(/^@/, "");
  const cleanInsta = (instagramUsername && instagramUsername.trim()) ? instagramUsername.trim().replace(/^@/, "") : "";

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000000",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        color: "#111b21",
        overflow: "hidden",
      }}
    >
      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* MODE 1: DUBLAJ_STYLE (@1dublaj Viral Benchmark Montage Format)   */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      {isDublaj && (
        <>
          {/* Top Cinematic Black Letterbox Bar (Height: 260px) */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: 1080,
              height: 260,
              backgroundColor: "#000000",
              zIndex: 30,
            }}
          />

          {/* Top Edge Shadow Vignette (Adds depth between bar and chat) */}
          <div
            style={{
              position: "absolute",
              top: 260,
              left: 0,
              width: 1080,
              height: 20,
              background: "linear-gradient(180deg, rgba(0, 0, 0, 0.45) 0%, transparent 100%)",
              zIndex: 25,
              pointerEvents: "none",
            }}
          />

          {/* Centered WhatsApp Chat Window with Climax Suspense Punch-in & Shake */}
          <div
            style={{
              position: "absolute",
              top: 260,
              left: 0,
              width: 1080,
              height: 1340,
              backgroundColor: "#f7e8ea",
              overflow: "hidden",
              zIndex: 10,
              transform: `scale(${cameraZoom}) translateX(${shockShake}px)`,
              transformOrigin: "center center",
            }}
          >
            {/* Pure White WhatsApp Header with Phone Status Bar (Fixed Navbar) */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: 140,
                backgroundColor: "#ffffff",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                paddingLeft: 24,
                paddingRight: 24,
                paddingTop: 6,
                paddingBottom: 10,
                boxShadow: "0 2px 6px rgba(0, 0, 0, 0.08)",
                borderBottom: "1px solid rgba(0, 0, 0, 0.08)",
                zIndex: 40,
              }}
            >
              {/* Ultra-Realistic Phone Status Bar (Viral 19% Low-Battery Retention Hook) */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  width: "100%",
                  paddingLeft: 6,
                  paddingRight: 6,
                }}
              >
                <span
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: "#111b21",
                    letterSpacing: "-0.2px",
                  }}
                >
                  {messages[activeMessageIndex]?.time || "14:24"}
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 800,
                      color: "#54656f",
                      letterSpacing: "0.5px",
                    }}
                  >
                    5G
                  </span>
                  <Wifi size={17} color="#54656f" strokeWidth={2.5} />
                  <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 800, color: "#ef4444" }}>
                      19%
                    </span>
                    <div
                      style={{
                        width: 22,
                        height: 11,
                        border: "1.5px solid #ef4444",
                        borderRadius: 3,
                        padding: 1,
                        display: "flex",
                        alignItems: "center",
                      }}
                    >
                      <div
                        style={{
                          width: "22%",
                          height: "100%",
                          backgroundColor: "#ef4444",
                          borderRadius: 1,
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* WhatsApp Main Navbar Row */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  width: "100%",
                  justifyContent: "space-between",
                }}
              >
                {/* Left: Back Arrow + Circular Avatar + Contact Name / Status */}
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <ArrowLeft size={34} color="#111b21" strokeWidth={2.6} />

                  {/* Avatar Container with Real-Time Online Radar Pulse */}
                  <div style={{ position: "relative" }}>
                    <div
                      style={{
                        width: 76,
                        height: 76,
                        borderRadius: "50%",
                        overflow: "hidden",
                        backgroundColor: "#e9edef",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        border: "1.5px solid rgba(0, 0, 0, 0.1)",
                        flexShrink: 0,
                        boxShadow: "0 2px 6px rgba(0, 0, 0, 0.1)",
                      }}
                    >
                      {resolvedAvatar ? (
                        <img
                          src={resolvedAvatar}
                          alt={contactName}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        />
                      ) : (
                        <span style={{ fontSize: 32, fontWeight: 700, color: "#111b21" }}>
                          {contactName.charAt(0).toUpperCase()}
                        </span>
                      )}
                    </div>
                    {/* Live Online Indicator Badge */}
                    <div
                      style={{
                        position: "absolute",
                        bottom: 1,
                        right: 1,
                        width: 19,
                        height: 19,
                        borderRadius: "50%",
                        backgroundColor: "#25D366",
                        border: "3px solid #ffffff",
                        boxShadow: "0 1px 4px rgba(0, 0, 0, 0.2)",
                      }}
                    />
                  </div>

                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <span
                      style={{
                        fontSize: 34,
                        fontWeight: 800,
                        color: "#111b21",
                        letterSpacing: "-0.5px",
                        maxWidth: 540,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {contactName}
                    </span>
                    <span
                      style={{
                        fontSize: 21,
                        color: (dynamicStatusText.includes("yazıyor") || dynamicStatusText.includes("typing")) ? "#00a884" : "#54656f",
                        fontWeight: (dynamicStatusText.includes("yazıyor") || dynamicStatusText.includes("typing")) ? 700 : 500,
                        marginTop: 2,
                        maxWidth: 540,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        transition: "color 0.2s ease",
                      }}
                    >
                      {dynamicStatusText}
                    </span>
                  </div>
                </div>

                {/* Right: Phone, Video, and More Icons */}
                <div style={{ display: "flex", alignItems: "center", gap: 26, color: "#111b21" }}>
                  <VideoCamIcon size={32} color="#111b21" strokeWidth={2.2} />
                  <Phone size={28} color="#111b21" strokeWidth={2.2} />
                  <MoreVertical size={30} color="#111b21" strokeWidth={2.4} />
                </div>
              </div>
            </div>

            {/* Sleek Cinematic Story Progress Bar (Retention Booster) */}
            <div
              style={{
                position: "absolute",
                top: 137,
                left: 0,
                right: 0,
                height: 4,
                backgroundColor: "rgba(0, 0, 0, 0.06)",
                zIndex: 45,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${Math.min(100, Math.max(0, (frame / Math.max(1, totalDuration)) * 100))}%`,
                  background: "linear-gradient(90deg, #25D366 0%, #128C7E 50%, #0ea5e9 100%)",
                  boxShadow: "0 0 10px rgba(37, 211, 102, 0.8)",
                }}
              />
            </div>

            {/* ── WHATSAPP INCOMING CALL INTERRUPTION CARD ── */}
            {isCallMoment && (
              <div
                style={{
                  position: "absolute",
                  top: 152,
                  left: 28,
                  right: 28,
                  backgroundColor: "#1f2c34",
                  borderRadius: 24,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "16px 24px",
                  boxShadow: "0 14px 40px rgba(0, 0, 0, 0.65)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  zIndex: 50,
                  transform: `translateY(${Math.sin(frame * 0.45) * 3}px)`,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <div
                    style={{
                      width: 58,
                      height: 58,
                      borderRadius: "50%",
                      overflow: "hidden",
                      border: "2px solid #25D366",
                    }}
                  >
                    {resolvedAvatar ? (
                      <img src={resolvedAvatar} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    ) : (
                      <div style={{ width: "100%", height: "100%", backgroundColor: "#00a884" }} />
                    )}
                  </div>
                  <div>
                    <div style={{ color: "#ffffff", fontSize: 24, fontWeight: 700 }}>{contactName}</div>
                    <div style={{ color: "#25D366", fontSize: 18, fontWeight: 600 }}>{isTr ? "WhatsApp Sesli Arama..." : "WhatsApp Voice Call..."}</div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: "50%",
                      backgroundColor: "#ea4335",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#ffffff",
                      boxShadow: "0 4px 10px rgba(234, 67, 53, 0.4)",
                    }}
                  >
                    <Phone size={24} style={{ transform: "rotate(135deg)" }} />
                  </div>
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: "50%",
                      backgroundColor: "#25D366",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#ffffff",
                      boxShadow: "0 4px 10px rgba(37, 211, 102, 0.4)",
                    }}
                  >
                    <Phone size={24} />
                  </div>
                </div>
              </div>
            )}

            {/* Dynamic Interactive Viewport (Wallpaper & Messages with Reactive Camera, 3D Gyroscope & Glitch) */}
            <div
              style={{
                position: "absolute",
                top: 140,
                bottom: 0,
                left: 0,
                right: 0,
                overflow: "hidden",
                transform: `perspective(1200px) rotateX(${gyroRotateX}deg) rotateY(${gyroRotateY}deg) scale(${cameraScale}) translate(${shakeX + handheldDriftX}px, ${shakeY + handheldDriftY}px) rotate(${handheldTilt}deg)`,
                filter: glitchFilter,
                transformOrigin: "center 40%",
                transition: "transform 0.05s ease-out",
              }}
            >
              {/* Aesthetic Floral Pastel Wallpaper with subtle parallax drift */}
              {resolvedWallpaper ? (
                <img
                  src={resolvedWallpaper}
                  alt="Chat Wallpaper"
                  style={{
                    position: "absolute",
                    inset: 0,
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    transform: `scale(1.05) translateY(${interpolate(
                      frame,
                      [0, Math.max(1, totalDuration)],
                      [0, -20],
                      { extrapolateRight: "clamp" }
                    )}px)`,
                  }}
                />
              ) : (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    backgroundColor: "#efeae2",
                    backgroundImage: "radial-gradient(#d1d7db 1px, transparent 1px)",
                    backgroundSize: "24px 24px",
                  }}
                />
              )}

              {/* Dynamic Mood Shift Color Overlay */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  backgroundColor: moodStyle.color,
                  opacity: moodStyle.opacity,
                  mixBlendMode: "multiply",
                  transition: "opacity 0.25s ease, background-color 0.25s ease",
                  pointerEvents: "none",
                  zIndex: 15,
                }}
              />

            {/* Chat Messages Scroll Area with Smooth Header Fade Mask */}
            <div
              style={{
                position: "absolute",
                top: 140,
                bottom: 0,
                left: 0,
                right: 0,
                overflow: "hidden",
                WebkitMaskImage:
                  scrollOffset > 6
                    ? "linear-gradient(to bottom, transparent 0px, black 32px, black 100%)"
                    : undefined,
                maskImage:
                  scrollOffset > 6
                    ? "linear-gradient(to bottom, transparent 0px, black 32px, black 100%)"
                    : undefined,
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "flex-start",
                  alignItems: "stretch",
                  paddingLeft: 26,
                  paddingRight: 26,
                  paddingTop: 16,
                  paddingBottom: 24,
                  transform: `translateY(-${scrollOffset}px)`,
                  willChange: "transform",
                }}
              >
                {/* WhatsApp "BUGÜN" Date Chip */}
                <div
                  style={{
                    alignSelf: "center",
                    margin: "12px auto 22px auto",
                    backgroundColor: "#ffffff",
                    color: "#54656f",
                    padding: "7px 22px",
                    borderRadius: 12,
                    fontSize: 20,
                    fontWeight: 600,
                    boxShadow: "0 1px 3px rgba(0, 0, 0, 0.12)",
                    letterSpacing: "0.5px",
                    textTransform: "uppercase",
                  }}
                >
                  BUGÜN
                </div>

                {/* Render Messages Sequentially */}
                {messages.map((msg, index) => {
                  if (frame < msg.startFrame) return null;

                  const isLastVisible = index === activeMessageIndex;
                  const elapsedSinceMsg = frame - msg.startFrame;

                  // High-craftsmanship energetic spring with slight overshoot bounce
                  const progress = spring({
                    frame: elapsedSinceMsg,
                    fps,
                    config: { damping: 12, stiffness: 180, mass: 0.6 },
                  });

                  const scale = interpolate(progress, [0, 1], [0.84, 1]);
                  const entranceOpacity = interpolate(progress, [0, 1], [0, 1]);
                  const translateY = interpolate(progress, [0, 1], [16, 0]);

                  const isUser = msg.sender === "user";
                  const tilt = isUser
                    ? interpolate(progress, [0, 1], [1.8, 0])
                    : interpolate(progress, [0, 1], [-1.8, 0]);

                  // High-Clarity Dialogue: Keep earlier messages crisp at 0.92 opacity so viewer never loses readability
                  const msgDuration = typeof msg.durationInFrames === "number" && !isNaN(msg.durationInFrames) ? msg.durationInFrames : 60;
                  const focusDim = isLastVisible
                    ? 1.0
                    : interpolate(
                        elapsedSinceMsg,
                        [msgDuration, msgDuration + 12],
                        [1.0, 0.92],
                        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                      );

                  const opacity = entranceOpacity * focusDim;

                  const senderColor = getSenderColor(
                    msg.senderName || contactName,
                    msg.senderColor
                  );
                  const msgAvatar = resolveMediaSrc(msg.senderAvatar) || (!isGroup ? resolvedAvatar : "");

                  // Realistic checkmarks timing: single -> double gray -> double blue tick
                  const isDelivered = elapsedSinceMsg >= 6;
                  const isRead = elapsedSinceMsg >= 16;
                  const checkPulse = isRead
                    ? spring({
                        frame: elapsedSinceMsg - 16,
                        fps,
                        config: { damping: 12, stiffness: 220 },
                      })
                    : 1;
                  const checkScale = isRead ? interpolate(checkPulse, [0, 0.5, 1], [1, 1.35, 1]) : 1;

                  // Dynamic floating tapback emoji reaction badge
                  const reactionEmoji = extractReactionEmoji(msg.text);
                  const reactionSpring = reactionEmoji
                    ? spring({
                        frame: Math.max(0, elapsedSinceMsg - 14),
                        fps,
                        config: { damping: 10, stiffness: 200, mass: 0.5 },
                      })
                    : 0;
                  const reactionScale = interpolate(reactionSpring, [0, 1], [0, 1]);

                  const isVoice =
                    msg.text.startsWith("[SES") ||
                    msg.text.startsWith("[VOICE") ||
                    msg.text.includes("🎙️");

                  const bubbleShadow = isLastVisible
                    ? isUser
                      ? "0 10px 24px -4px rgba(0, 168, 132, 0.24), 0 3px 8px rgba(0, 0, 0, 0.08), inset 0 1px 1px rgba(255, 255, 255, 0.6)"
                      : "0 12px 28px -4px rgba(0, 0, 0, 0.18), 0 3px 8px rgba(0, 0, 0, 0.08), inset 0 1px 1px rgba(255, 255, 255, 0.9)"
                    : "0 2px 8px rgba(0, 0, 0, 0.10)";

                  const bubbleBorder = isLastVisible
                    ? isUser
                      ? "1.5px solid rgba(0, 168, 132, 0.3)"
                      : "1.5px solid rgba(0, 0, 0, 0.06)"
                    : "1px solid rgba(0, 0, 0, 0.04)";

                  // ── INCOMING (CONTACT) BUBBLE WITH SENDER AVATAR & NAME ──
                  if (!isUser) {
                    return (
                      <div
                        key={msg.id || index}
                        style={{
                          display: "flex",
                          flexDirection: "row",
                          alignItems: "flex-start",
                          gap: 12,
                          maxWidth: "88%",
                          alignSelf: "flex-start",
                          marginBottom: 18,
                          opacity,
                          transform: `scale(${scale}) translateY(${translateY}px) rotate(${tilt}deg)`,
                          transformOrigin: "top left",
                          position: "relative",
                        }}
                      >
                        {/* Circular Sender Avatar */}
                        <div
                          style={{
                            width: 58,
                            height: 58,
                            borderRadius: "50%",
                            overflow: "hidden",
                            backgroundColor: "#ffffff",
                            boxShadow: "0 2px 6px rgba(0, 0, 0, 0.12)",
                            flexShrink: 0,
                            marginTop: 2,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            border: "1.5px solid rgba(0, 0, 0, 0.08)",
                          }}
                        >
                          {msgAvatar ? (
                            <img
                              src={msgAvatar}
                              alt=""
                              style={{ width: "100%", height: "100%", objectFit: "cover" }}
                            />
                          ) : (
                            <span
                              style={{
                                fontSize: 24,
                                fontWeight: "bold",
                                color: senderColor,
                              }}
                            >
                              {(msg.senderName || contactName).charAt(0).toUpperCase()}
                            </span>
                          )}
                        </div>

                        {/* Pure White Message Bubble with Depth Accent */}
                        <div
                          style={{
                            backgroundColor: "#ffffff",
                            padding: "14px 22px 10px 22px",
                            borderRadius: 22,
                            borderTopLeftRadius: 4,
                            boxShadow: bubbleShadow,
                            border: bubbleBorder,
                            position: "relative",
                            wordBreak: "break-word",
                            transition: "box-shadow 0.2s ease, opacity 0.2s ease",
                          }}
                        >
                          {/* Sender Name in Warm Bold Color */}
                          <div
                            style={{
                              color: senderColor,
                              fontSize: 24,
                              fontWeight: 700,
                              marginBottom: 4,
                              letterSpacing: "-0.2px",
                            }}
                          >
                            {msg.senderName || contactName}
                          </div>

                          {/* Message Content: Voice Note or Highlighted Text */}
                          {isVoice ? (
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 14,
                                minWidth: 280,
                                padding: "8px 2px",
                              }}
                            >
                              {/* Green Circular Play Button with Pulse */}
                              <div
                                style={{
                                  width: 52,
                                  height: 52,
                                  borderRadius: "50%",
                                  backgroundColor: "#00a884",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  color: "#ffffff",
                                  fontSize: 22,
                                  boxShadow: "0 3px 8px rgba(0, 168, 132, 0.35)",
                                  transform: isLastVisible ? `scale(${1 + Math.sin(frame * 0.2) * 0.04})` : "scale(1)",
                                  flexShrink: 0,
                                }}
                              >
                                ▶
                              </div>

                              {/* Dynamic Waveform with Scrubbing Playhead */}
                              <div style={{ flex: 1, position: "relative", display: "flex", flexDirection: "column", gap: 6 }}>
                                <div
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 3,
                                    height: 36,
                                    position: "relative",
                                  }}
                                >
                                  {[14, 26, 18, 34, 16, 28, 22, 38, 18, 28, 34, 22, 14, 30, 20, 36, 18, 24].map((barH, bIdx, arr) => {
                                    const barFraction = bIdx / arr.length;
                                    const voiceProgress = Math.min(1, Math.max(0, elapsedSinceMsg / Math.max(1, msg.durationInFrames)));
                                    const isPlayed = barFraction <= voiceProgress;
                                    const liveWave = isLastVisible && isPlayed
                                      ? Math.sin(frame * 0.35 + bIdx * 0.6) * (barH * 0.3) + barH * 0.7
                                      : barH * 0.7;

                                    return (
                                      <div
                                        key={bIdx}
                                        style={{
                                          width: 4.5,
                                          height: Math.max(6, liveWave),
                                          backgroundColor: isPlayed ? "#00a884" : "#94a3b8",
                                          borderRadius: 3,
                                          transition: "background-color 0.15s ease",
                                        }}
                                      />
                                    );
                                  })}

                                  {isLastVisible && (
                                    <div
                                      style={{
                                        position: "absolute",
                                        left: `${Math.min(96, Math.max(0, (elapsedSinceMsg / Math.max(1, msg.durationInFrames)) * 100))}%`,
                                        top: "50%",
                                        transform: "translate(-50%, -50%)",
                                        width: 12,
                                        height: 12,
                                        borderRadius: "50%",
                                        backgroundColor: "#0ea5e9",
                                        boxShadow: "0 0 6px rgba(14, 165, 233, 0.8)",
                                      }}
                                    />
                                  )}
                                </div>

                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                  <span style={{ fontSize: 17, color: "#54656f", fontWeight: 600 }}>
                                    {`0:${Math.min(
                                      Math.floor(msg.durationInFrames / fps),
                                      Math.floor(elapsedSinceMsg / fps)
                                    ).toString().padStart(2, "0")}`}
                                  </span>
                                  <Mic size={16} color="#00a884" />
                                </div>
                              </div>
                            </div>
                          ) : (
                            <p
                              style={{
                                margin: 0,
                                fontSize: 34,
                                lineHeight: 1.35,
                                color: "#111b21",
                                fontWeight: 500,
                                letterSpacing: "-0.2px",
                              }}
                            >
                              {renderHighlightedText(msg.text, false, isLastVisible, elapsedSinceMsg)}
                            </p>
                          )}

                          {/* Timestamp */}
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "flex-end",
                              marginTop: 4,
                            }}
                          >
                            <span style={{ fontSize: 19, color: "#667781", fontWeight: 400 }}>
                              {msg.time || "14:24"}
                            </span>
                          </div>

                          {/* Floating Reaction Tapback Emoji */}
                          {reactionEmoji && elapsedSinceMsg >= 14 && (
                            <div
                              style={{
                                position: "absolute",
                                bottom: -16,
                                right: -10,
                                backgroundColor: "#ffffff",
                                borderRadius: 24,
                                padding: "4px 8px",
                                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.16)",
                                border: "1.5px solid rgba(0, 0, 0, 0.08)",
                                fontSize: 24,
                                lineHeight: 1,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                transform: `scale(${reactionScale}) rotate(-6deg)`,
                                transformOrigin: "center center",
                                zIndex: 15,
                              }}
                            >
                              {reactionEmoji}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  }

                  // ── OUTGOING (USER) BUBBLE WITH LIGHT GREEN ACCENT ──
                  return (
                    <div
                      key={msg.id || index}
                      style={{
                        alignSelf: "flex-end",
                        maxWidth: "84%",
                        marginBottom: 18,
                        opacity,
                        transform: `scale(${scale}) translateY(${translateY}px) rotate(${tilt}deg)`,
                        transformOrigin: "top right",
                        position: "relative",
                      }}
                    >
                      <div
                        style={{
                          backgroundColor: "#d9fdd3",
                          padding: "14px 22px 10px 22px",
                          borderRadius: 22,
                          borderTopRightRadius: 4,
                          boxShadow: bubbleShadow,
                          border: bubbleBorder,
                          position: "relative",
                          wordBreak: "break-word",
                          transition: "box-shadow 0.2s ease, opacity 0.2s ease",
                        }}
                      >
                        {isVoice ? (
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 14,
                              minWidth: 280,
                              padding: "8px 2px",
                            }}
                          >
                            <div
                              style={{
                                width: 52,
                                height: 52,
                                borderRadius: "50%",
                                backgroundColor: "#00a884",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                color: "#ffffff",
                                fontSize: 22,
                                boxShadow: "0 3px 8px rgba(0, 168, 132, 0.35)",
                                transform: isLastVisible ? `scale(${1 + Math.sin(frame * 0.2) * 0.04})` : "scale(1)",
                                flexShrink: 0,
                              }}
                            >
                              ▶
                            </div>
                            <div style={{ flex: 1, position: "relative", display: "flex", flexDirection: "column", gap: 6 }}>
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 3,
                                  height: 36,
                                  position: "relative",
                                }}
                              >
                                {[14, 26, 18, 34, 16, 28, 22, 38, 18, 28, 34, 22, 14, 30, 20, 36, 18, 24].map((barH, bIdx, arr) => {
                                  const barFraction = bIdx / arr.length;
                                  const voiceProgress = Math.min(1, Math.max(0, elapsedSinceMsg / Math.max(1, msg.durationInFrames)));
                                  const isPlayed = barFraction <= voiceProgress;
                                  const liveWave = isLastVisible && isPlayed
                                    ? Math.sin(frame * 0.35 + bIdx * 0.6) * (barH * 0.3) + barH * 0.7
                                    : barH * 0.7;

                                  return (
                                    <div
                                      key={bIdx}
                                      style={{
                                        width: 4.5,
                                        height: Math.max(6, liveWave),
                                        backgroundColor: isPlayed ? "#00a884" : "#94a3b8",
                                        borderRadius: 3,
                                        transition: "background-color 0.15s ease",
                                      }}
                                    />
                                  );
                                })}

                                {isLastVisible && (
                                  <div
                                    style={{
                                      position: "absolute",
                                      left: `${Math.min(96, Math.max(0, (elapsedSinceMsg / Math.max(1, msg.durationInFrames)) * 100))}%`,
                                      top: "50%",
                                      transform: "translate(-50%, -50%)",
                                      width: 12,
                                      height: 12,
                                      borderRadius: "50%",
                                      backgroundColor: "#0ea5e9",
                                      boxShadow: "0 0 6px rgba(14, 165, 233, 0.8)",
                                    }}
                                  />
                                )}
                              </div>

                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <span style={{ fontSize: 17, color: "#54656f", fontWeight: 600 }}>
                                  {`0:${Math.min(
                                    Math.floor(msg.durationInFrames / fps),
                                    Math.floor(elapsedSinceMsg / fps)
                                  ).toString().padStart(2, "0")}`}
                                </span>
                                <Mic size={16} color="#00a884" />
                              </div>
                            </div>
                          </div>
                        ) : (
                          <p
                            style={{
                              margin: 0,
                              fontSize: 34,
                              lineHeight: 1.35,
                              color: "#111b21",
                              fontWeight: 500,
                              letterSpacing: "-0.2px",
                            }}
                          >
                            {renderHighlightedText(msg.text, true, isLastVisible, elapsedSinceMsg)}
                          </p>
                        )}

                        {/* Timestamp & Realistic Checkmarks */}
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "flex-end",
                            gap: 6,
                            marginTop: 4,
                          }}
                        >
                          <span style={{ fontSize: 19, color: "#667781", fontWeight: 400 }}>
                            {msg.time || "14:24"}
                          </span>

                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              transform: `scale(${checkScale})`,
                              transformOrigin: "center center",
                            }}
                          >
                            {isDelivered ? (
                              <CheckCheck
                                size={20}
                                color={isRead ? "#53bdeb" : "#8696a0"}
                                strokeWidth={2.4}
                              />
                            ) : (
                              <Check size={18} color="#8696a0" strokeWidth={2.4} />
                            )}
                          </div>
                        </div>

                        {/* Floating Reaction Tapback Emoji */}
                        {reactionEmoji && elapsedSinceMsg >= 14 && (
                          <div
                            style={{
                              position: "absolute",
                              bottom: -16,
                              left: -10,
                              backgroundColor: "#ffffff",
                              borderRadius: 24,
                              padding: "4px 8px",
                              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.16)",
                              border: "1.5px solid rgba(0, 0, 0, 0.08)",
                              fontSize: 24,
                              lineHeight: 1,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              transform: `scale(${reactionScale}) rotate(6deg)`,
                              transformOrigin: "center center",
                              zIndex: 15,
                            }}
                          >
                            {reactionEmoji}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* ── REALISTIC WHATSAPP "YAZIYOR..." 3-DOT TYPING BUBBLE ── */}
                {typingInfo.isTyping && typingInfo.sender === "contact" && (() => {
                  const typingAvatar = resolveMediaSrc(typingInfo.senderAvatar) || (!isGroup ? resolvedAvatar : "");
                  const typingSenderColor = getSenderColor(
                    typingInfo.senderName || contactName,
                    typingInfo.senderColor
                  );
                  return (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "row",
                        alignItems: "center",
                        gap: 12,
                        alignSelf: "flex-start",
                        marginTop: 4,
                        marginBottom: 16,
                      }}
                    >
                      {/* Avatar strictly identical to incoming message avatar (58x58, shadow, border, initial) */}
                      <div
                        style={{
                          width: 58,
                          height: 58,
                          borderRadius: "50%",
                          overflow: "hidden",
                          backgroundColor: "#ffffff",
                          boxShadow: "0 2px 6px rgba(0, 0, 0, 0.12)",
                          flexShrink: 0,
                          marginTop: 2,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          border: "1.5px solid rgba(0, 0, 0, 0.08)",
                        }}
                      >
                        {typingAvatar ? (
                          <img
                            src={typingAvatar}
                            alt=""
                            style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          />
                        ) : (
                          <span
                            style={{
                              fontSize: 24,
                              fontWeight: "bold",
                              color: typingSenderColor,
                            }}
                          >
                            {((typingInfo.senderName || contactName).charAt(0) || "W").toUpperCase()}
                          </span>
                        )}
                      </div>

                    <div
                      style={{
                        backgroundColor: "#ffffff",
                        padding: "16px 22px",
                        borderRadius: 20,
                        borderTopLeftRadius: 4,
                        boxShadow: "0 2px 8px rgba(0, 0, 0, 0.12)",
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                      }}
                    >
                      {[0, 1, 2].map((dotIdx) => {
                        const bounce = Math.sin(frame * 0.35 - dotIdx * 0.8) * 6;
                        return (
                          <div
                            key={dotIdx}
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: "50%",
                              backgroundColor: "#8696a0",
                              transform: `translateY(${bounce}px)`,
                            }}
                          />
                        );
                      })}
                    </div>
                    </div>
                  );
                })()}
              </div>
            </div>
            </div>
          </div>

          {/* Bottom Edge Shadow Vignette (Adds depth between chat and bottom bar) */}
          <div
            style={{
              position: "absolute",
              top: 1585,
              left: 0,
              width: 1080,
              height: 20,
              background: "linear-gradient(0deg, rgba(0, 0, 0, 0.5) 0%, transparent 100%)",
              zIndex: 25,
              pointerEvents: "none",
            }}
          />

          {/* Bottom Cinematic Black Letterbox Bar (Height: 320px) */}
          <div
            style={{
              position: "absolute",
              top: 1600,
              left: 0,
              width: 1080,
              height: 320,
              backgroundColor: "#000000",
              zIndex: 30,
            }}
          />

          {/* High-Craftsmanship Frosted Glass Dual-Handle Watermark Pill */}
          <div
            style={{
              position: "absolute",
              top: 1675,
              left: 0,
              width: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              zIndex: 35,
              pointerEvents: "none",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                backgroundColor: "rgba(255, 255, 255, 0.07)",
                padding: "10px 30px",
                borderRadius: 40,
                border: "1px solid rgba(255, 255, 255, 0.14)",
                boxShadow: "0 6px 24px rgba(0, 0, 0, 0.65)",
              }}
            >
              <div
                style={{
                  color: "#ffffff",
                  fontSize: 27,
                  fontWeight: 900,
                  fontStyle: "italic",
                  letterSpacing: 2,
                  textTransform: "uppercase",
                  fontFamily:
                    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
                  textShadow: "0 2px 8px rgba(0, 0, 0, 0.9)",
                }}
              >
                YT: @{cleanWatermark}
              </div>
              {cleanInsta && (
                <>
                  <div
                    style={{
                      width: 5,
                      height: 5,
                      borderRadius: "50%",
                      backgroundColor: "rgba(255, 255, 255, 0.4)",
                    }}
                  />
                  <div
                    style={{
                      color: "rgba(255, 255, 255, 0.88)",
                      fontSize: 25,
                      fontWeight: 800,
                      fontStyle: "italic",
                      letterSpacing: 2,
                      textTransform: "uppercase",
                      fontFamily:
                        "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
                      textShadow: "0 2px 8px rgba(0, 0, 0, 0.9)",
                    }}
                  >
                    INSTA: @{cleanInsta}
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* MODE 2: COMPACT_TOP & FULLSCREEN (Legacy Fallbacks)             */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      {!isDublaj && (
        <>
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: 1080,
              height: isCompact ? 960 : 1920,
              backgroundColor: "#0b141a",
              overflow: "hidden",
              borderBottom: isCompact ? "3px solid #222e35" : "none",
              boxShadow: isCompact ? "0 12px 40px rgba(0, 0, 0, 0.9)" : "none",
              zIndex: 10,
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 0,
                opacity: 0.05,
                backgroundImage: "radial-gradient(#ffffff 1px, transparent 1px)",
                backgroundSize: "24px 24px",
                pointerEvents: "none",
              }}
            />

            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: isCompact ? 136 : 180,
                backgroundColor: "#202c33",
                display: "flex",
                alignItems: "center",
                paddingLeft: 24,
                paddingRight: 24,
                boxShadow: "0 2px 10px rgba(0, 0, 0, 0.35)",
                zIndex: 30,
                borderBottom: "1px solid #2a3942",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  width: "100%",
                  justifyContent: "space-between",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <ArrowLeft size={isCompact ? 34 : 38} color="#aebac1" />
                  <div style={{ position: "relative" }}>
                    <div
                      style={{
                        width: isCompact ? 74 : 82,
                        height: isCompact ? 74 : 82,
                        borderRadius: "50%",
                        overflow: "hidden",
                        backgroundColor: "#6b7c85",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        border: "2px solid #00a884",
                      }}
                    >
                      {resolvedAvatar ? (
                        <img
                          src={resolvedAvatar}
                          alt={contactName}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        />
                      ) : (
                        <span style={{ fontSize: 32, fontWeight: "bold", color: "#fff" }}>
                          {contactName.charAt(0).toUpperCase()}
                        </span>
                      )}
                    </div>
                    <div
                      style={{
                        position: "absolute",
                        bottom: 2,
                        right: 2,
                        width: 16,
                        height: 16,
                        borderRadius: "50%",
                        backgroundColor: "#00a884",
                        border: "2.5px solid #202c33",
                      }}
                    />
                  </div>

                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <span
                      style={{
                        fontSize: isCompact ? 32 : 36,
                        fontWeight: 700,
                        color: "#e9edef",
                        letterSpacing: "-0.4px",
                        maxWidth: 480,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {contactName}
                    </span>
                    <span
                      style={{
                        fontSize: isCompact ? 20 : 22,
                        color: "#8696a0",
                        fontWeight: 400,
                        marginTop: 2,
                      }}
                    >
                      {statusText}
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 26,
                    color: "#aebac1",
                  }}
                >
                  <VideoCamIcon size={isCompact ? 32 : 36} />
                  <Phone size={isCompact ? 30 : 34} />
                  <MoreVertical size={isCompact ? 30 : 34} />
                </div>
              </div>
            </div>

            <div
              style={{
                position: "absolute",
                top: isCompact ? 136 : 180,
                bottom: isCompact ? 0 : 160,
                left: 0,
                right: 0,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "flex-start",
                  alignItems: "stretch",
                  paddingLeft: 30,
                  paddingRight: 30,
                  paddingTop: 16,
                  paddingBottom: 24,
                  transform: `translateY(-${scrollOffset}px)`,
                  willChange: "transform",
                }}
              >
                <div
                  style={{
                    alignSelf: "center",
                    margin: "4px auto 18px auto",
                    backgroundColor: "#182229",
                    color: "#8696a0",
                    padding: "6px 18px",
                    borderRadius: 10,
                    fontSize: 19,
                    fontWeight: 500,
                    boxShadow: "0 1px 2px rgba(0, 0, 0, 0.3)",
                    letterSpacing: "0.5px",
                    textTransform: "uppercase",
                  }}
                >
                  BUGÜN
                </div>

                {messages.map((msg, index) => {
                  if (frame < msg.startFrame) return null;

                  const progress = spring({
                    frame: frame - msg.startFrame,
                    fps,
                    config: { damping: 14, stiffness: 140 },
                  });

                  const scale = interpolate(progress, [0, 1], [0.85, 1]);
                  const opacity = interpolate(progress, [0, 1], [0, 1]);
                  const translateY = interpolate(progress, [0, 1], [18, 0]);

                  const isUser = msg.sender === "user";
                  const bubbleColor = isUser ? "#005c4b" : "#202c33";
                  const alignSelf = isUser ? "flex-end" : "flex-start";
                  const isRead = frame >= msg.startFrame + 12;
                  const checkmarkColor = isRead ? "#53bdeb" : "#8696a0";

                  return (
                    <div
                      key={msg.id || index}
                      style={{
                        alignSelf,
                        maxWidth: "80%",
                        marginBottom: 16,
                        opacity,
                        transform: `scale(${scale}) translateY(${translateY}px)`,
                        transformOrigin: isUser ? "top right" : "top left",
                      }}
                    >
                      <div
                        style={{
                          backgroundColor: bubbleColor,
                          padding: "14px 20px 10px 20px",
                          borderRadius: 18,
                          borderTopRightRadius: isUser ? 4 : 18,
                          borderTopLeftRadius: isUser ? 18 : 4,
                          boxShadow: "0 2px 6px rgba(0, 0, 0, 0.25)",
                          position: "relative",
                          wordBreak: "break-word",
                        }}
                      >
                        <p
                          style={{
                            margin: 0,
                            fontSize: 32,
                            lineHeight: 1.35,
                            color: "#e9edef",
                            letterSpacing: "-0.2px",
                          }}
                        >
                          {msg.text}
                        </p>

                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "flex-end",
                            gap: 6,
                            marginTop: 4,
                          }}
                        >
                          <span style={{ fontSize: 18, color: "#8696a0", fontWeight: 400 }}>
                            {msg.time || "14:24"}
                          </span>
                          {isUser && (
                            <CheckCheck size={20} color={checkmarkColor} strokeWidth={2.4} />
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {!isCompact && (
              <div
                style={{
                  position: "absolute",
                  bottom: 0,
                  left: 0,
                  right: 0,
                  height: 160,
                  backgroundColor: "#202c33",
                  padding: "20px 24px",
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  zIndex: 30,
                  borderTop: "1px solid #2a3942",
                }}
              >
                <div
                  style={{
                    flex: 1,
                    height: 86,
                    backgroundColor: "#2a3942",
                    borderRadius: 43,
                    display: "flex",
                    alignItems: "center",
                    padding: "0 24px",
                    gap: 18,
                  }}
                >
                  <Smile size={36} color="#8696a0" />
                  <span style={{ fontSize: 28, color: "#8696a0", flex: 1 }}>{isTr ? "Mesaj" : "Message"}</span>
                  <Paperclip size={34} color="#8696a0" />
                  <Camera size={34} color="#8696a0" />
                </div>

                <div
                  style={{
                    width: 86,
                    height: 86,
                    borderRadius: "50%",
                    backgroundColor: "#00a884",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: "0 4px 14px rgba(0, 168, 132, 0.4)",
                  }}
                >
                  <Mic size={38} color="#ffffff" />
                </div>
              </div>
            )}
          </div>

          {isCompact && (
            <div
              style={{
                position: "absolute",
                top: 960,
                left: 0,
                width: 1080,
                height: 960,
                backgroundColor: "#000000",
                overflow: "hidden",
                zIndex: 5,
              }}
            >
              {resolvedBgVideo ? (
                <Video
                  src={resolvedBgVideo}
                  loop
                  muted
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                  }}
                />
              ) : (
                <div
                  style={{
                    width: "100%",
                    height: "100%",
                    background: "linear-gradient(180deg, #111b21 0%, #000000 100%)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                />
              )}

              {watermarkText && (
                <div
                  style={{
                    position: "absolute",
                    bottom: 60,
                    left: 0,
                    width: "100%",
                    textAlign: "center",
                    color: "rgba(255, 255, 255, 0.45)",
                    fontSize: 26,
                    fontWeight: 700,
                    letterSpacing: 2.5,
                    textTransform: "uppercase",
                    textShadow: "0 2px 8px rgba(0, 0, 0, 0.8)",
                    pointerEvents: "none",
                  }}
                >
                  @{cleanWatermark} &bull; Shorts
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ── AUDIO ELEMENTS ── */}
      {resolvedAudio && <Audio src={resolvedAudio} />}
      {resolvedBgm && <Audio src={resolvedBgm} volume={dynamicBgmVolume} loop />}

      {/* ── HAPTIC AUDIO FX LAYER (TACTILE POP & WHOOSH SFX) ── */}
      {messages.map((m, mIdx) => {
        const emotion = analyzeMessageEmotion(m.text, mIdx >= messages.length - 2);
        return (
          <React.Fragment key={`sfx-${m.id || mIdx}`}>
            {/* Tactile Pop SFX on bubble appearance */}
            <Sequence from={m.startFrame} durationInFrames={18}>
              <Audio
                src={resolveMediaSrc("media/pop.wav")}
                volume={0.34}
                startFrom={0}
                endAt={18}
              />
            </Sequence>
            {/* Cinematic Whoosh SFX on Shock / Climax moments */}
            {emotion.hasShock && (
              <Sequence from={m.startFrame} durationInFrames={28}>
                <Audio
                  src={resolveMediaSrc("media/whoosh.wav")}
                  volume={0.26}
                  startFrom={0}
                  endAt={28}
                />
              </Sequence>
            )}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};
