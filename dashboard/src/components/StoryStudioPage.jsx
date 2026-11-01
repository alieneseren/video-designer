import React, { useState, useMemo } from "react";
import {
  BookOpen,
  Sparkles,
  Tv,
  HelpCircle,
  ExternalLink,
  ChevronRight,
  Info
} from "lucide-react";
import StoryStudio from "./StoryStudio";

export default function StoryStudioPage({
  channels = [],
  selectedChannelId,
  onSelectChannel
}) {
  // Find story channels first
  const storyChannels = useMemo(() => {
    return channels.filter(
      c => c.topic_category === "story" || c.topic_category === "masal" || c.channel_id === "ch_story_tr"
    );
  }, [channels]);

  // Default active channel ID: selectedChannelId if valid, else first story channel, else first channel
  const [activeChannelId, setActiveChannelId] = useState(() => {
    if (selectedChannelId && channels.some(c => c.channel_id === selectedChannelId)) {
      return selectedChannelId;
    }
    if (storyChannels.length > 0) {
      return storyChannels[0].channel_id;
    }
    return channels[0]?.channel_id || "";
  });

  const activeChannel = useMemo(() => {
    return channels.find(c => c.channel_id === activeChannelId) || storyChannels[0] || channels[0] || null;
  }, [channels, storyChannels, activeChannelId]);

  const handleChannelChange = (cid) => {
    setActiveChannelId(cid);
    if (onSelectChannel) {
      onSelectChannel(cid);
    }
  };

  return (
    <div className="story-studio-page" style={{ padding: "0 0 40px 0" }}>
      {/* Top Selector Bar */}
      <div
        className="card"
        style={{
          padding: "16px 20px",
          marginBottom: 20,
          background: "linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%)",
          border: "1px solid rgba(168, 85, 247, 0.2)",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              boxShadow: "0 4px 12px rgba(99, 102, 241, 0.25)"
            }}
          >
            <BookOpen size={24} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
              Hikaye & Masal Atölyesi
              <span className="badge badge-purple" style={{ fontSize: 11 }}>Sinematik Kod Animasyonları</span>
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
              Hikayelerinizi yazın, Gemini eklentisiyle geliştirin ve partlara bölünmüş estetik Shorts videoları üretin.
            </div>
          </div>
        </div>

        {/* Channel Switcher */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 4 }}>
            <Tv size={14} /> Aktif Kanal:
          </label>
          <select
            className="form-input"
            value={activeChannel?.channel_id || activeChannelId}
            onChange={(e) => handleChannelChange(e.target.value)}
            style={{
              minWidth: 220,
              padding: "7px 12px",
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 500,
              color: "var(--text-primary)",
              cursor: "pointer"
            }}
          >
            {storyChannels.length > 0 && (
              <optgroup label="📖 Hikaye & Masal Kanalları">
                {storyChannels.map(ch => (
                  <option key={ch.channel_id} value={ch.channel_id}>
                    ⭐ {ch.name} ({ch.channel_id}) - {ch.language?.toUpperCase()}
                  </option>
                ))}
              </optgroup>
            )}
            <optgroup label="📺 Diğer Kanallar">
              {channels.filter(c => !storyChannels.some(s => s.channel_id === c.channel_id)).map(ch => (
                <option key={ch.channel_id} value={ch.channel_id}>
                  {ch.name} ({ch.channel_id})
                </option>
              ))}
            </optgroup>
          </select>
        </div>
      </div>

      {/* Guide Banner */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 12,
          marginBottom: 20
        }}
      >
        <div
          className="card"
          style={{
            padding: "14px 16px",
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-subtle)",
            borderLeft: "3px solid #6366f1"
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
            <Sparkles size={16} color="#6366f1" />
            1. Taslak Oluştur veya Düzenle
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.5 }}>
            Aşağıdaki <strong>"➕ Yeni Hikaye Ekle"</strong> butonuna tıklayarak aklınızdaki hikaye fikrini, notları veya ham metni girin.
          </div>
        </div>

        <div
          className="card"
          style={{
            padding: "14px 16px",
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-subtle)",
            borderLeft: "3px solid #a855f7"
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
            <span>💡</span>
            2. Gemini Chrome Eklentisi ile Genişlet
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.5 }}>
            Gemini sayfasında eklentiyi açın, <strong>'📖 Hikaye Geliştir'</strong> sekmesinden bu taslağı seçip Gemini ile soru-cevap yaparak partlara bölün.
          </div>
        </div>

        <div
          className="card"
          style={{
            padding: "14px 16px",
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-subtle)",
            borderLeft: "3px solid #10b981"
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
            <span>🎬</span>
            3. Materyal Yap & Sinematik Render
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.5 }}>
            Geliştirilen taslağı tek tıkla <strong>Üretim Materyali</strong> yapın ve kadim fener, gotik kule veya kozmik temalı kod animasyonuyla derleyin.
          </div>
        </div>
      </div>

      {/* Main Studio View */}
      {activeChannel ? (
        <StoryStudio channel={activeChannel} />
      ) : (
        <div className="card" style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
          Lütfen yukarıdan bir kanal seçin.
        </div>
      )}
    </div>
  );
}
