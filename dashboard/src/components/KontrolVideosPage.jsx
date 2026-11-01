import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  CheckCircle2,
  Clock,
  HardDrive,
  Film,
  Tv,
  Check,
  FolderOpen,
  Copy,
  ExternalLink,
  RefreshCw,
  Search,
  Filter,
  Play,
  Pause,
  ArrowRight,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronUp,
  Tag,
  AlertCircle
} from "lucide-react";

export default function KontrolVideosPage({ onNavigateUpload }) {
  const [channelsData, setChannelsData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedChannelFilter, setSelectedChannelFilter] = useState("all");
  const [actionLoadingFolder, setActionLoadingFolder] = useState(null);
  const [channelApprovingId, setChannelApprovingId] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [expandedDescriptions, setExpandedDescriptions] = useState({});
  const [activeVideoPlayer, setActiveVideoPlayer] = useState({});

  const showToast = (msg, type = "success") => {
    setToastMessage({ text: msg, type });
    setTimeout(() => setToastMessage(null), 3500);
  };

  const fetchKontrolVideos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/kontrol/videos");
      if (!res.ok) throw new Error("Kontrol videoları yüklenemedi.");
      const data = await res.json();
      if (data.success) {
        setChannelsData(data.channels || []);
      } else {
        throw new Error(data.message || "Bilinmeyen bir hata oluştu.");
      }
    } catch (err) {
      console.error("[KontrolVideosPage] Hata:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKontrolVideos();
  }, [fetchKontrolVideos]);

  // Tekil videoyu 'yuklenecek' klasörüne aktar
  const handleApproveVideo = async (channelId, folderName, videoTitle) => {
    const key = `${channelId}/${folderName}`;
    setActionLoadingFolder(key);
    try {
      const res = await fetch("/api/kontrol/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel_id: channelId, folder_name: folderName })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(`"${videoTitle || folderName}" başarıyla 'yuklenecek' klasörüne aktarıldı!`);
        // State'ten doğrudan çıkar
        setChannelsData(prev =>
          prev
            .map(ch => {
              if (ch.channel_id === channelId) {
                const remaining = ch.videos.filter(v => v.folder_name !== folderName);
                return { ...ch, videos: remaining, video_count: remaining.length };
              }
              return ch;
            })
            .filter(ch => ch.video_count > 0)
        );
      } else {
        throw new Error(data.detail || data.message || "Aktarım başarısız oldu.");
      }
    } catch (err) {
      console.error("[Approve Video] Hata:", err);
      showToast(err.message, "error");
    } finally {
      setActionLoadingFolder(null);
    }
  };

  // Kanalın tüm videolarını 'yuklenecek' klasörüne aktar
  const handleApproveAllForChannel = async (channelId, channelName) => {
    if (!window.confirm(`"${channelName}" kanalındaki tüm kontroldeki videolar 'yuklenecek' klasörüne aktarılsın mı?`)) {
      return;
    }
    setChannelApprovingId(channelId);
    try {
      const res = await fetch("/api/kontrol/approve-all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel_id: channelId })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(data.message || "Tüm videolar aktarıldı!");
        setChannelsData(prev => prev.filter(ch => ch.channel_id !== channelId));
      } else {
        throw new Error(data.detail || data.message || "Toplu onay başarısız oldu.");
      }
    } catch (err) {
      console.error("[Approve All] Hata:", err);
      showToast(err.message, "error");
    } finally {
      setChannelApprovingId(null);
    }
  };

  // Klasörü yerel Finder'da aç
  const handleOpenFolder = async (folderPath) => {
    try {
      await fetch("/api/kontrol/open-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder_path: folderPath })
      });
    } catch (e) {
      console.warn("Klasör açılamadı:", e);
    }
  };

  // Kopyalama fonksiyonu
  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    showToast(`${label || "Metin"} panoya kopyalandı.`);
  };

  // İstatistikler
  const totalVideosCount = useMemo(() => {
    return channelsData.reduce((acc, ch) => acc + (ch.videos ? ch.videos.length : 0), 0);
  }, [channelsData]);

  const totalSizeMB = useMemo(() => {
    let mb = 0;
    channelsData.forEach(ch => {
      (ch.videos || []).forEach(v => {
        mb += (v.size_mb || 0);
      });
    });
    return mb.toFixed(1);
  }, [channelsData]);

  // Filtreleme
  const filteredChannels = useMemo(() => {
    return channelsData
      .filter(ch => {
        if (selectedChannelFilter !== "all" && ch.channel_id !== selectedChannelFilter) {
          return false;
        }
        return true;
      })
      .map(ch => {
        if (!searchQuery.trim()) return ch;
        const q = searchQuery.toLowerCase();
        const filteredVids = (ch.videos || []).filter(v =>
          (v.title || "").toLowerCase().includes(q) ||
          (v.folder_name || "").toLowerCase().includes(q) ||
          (v.description || "").toLowerCase().includes(q)
        );
        return { ...ch, videos: filteredVids, video_count: filteredVids.length };
      })
      .filter(ch => ch.videos.length > 0);
  }, [channelsData, selectedChannelFilter, searchQuery]);

  const formatDuration = (sec) => {
    if (!sec || isNaN(sec)) return "00:00";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const getCategoryBadge = (cat) => {
    const c = (cat || "").toLowerCase();
    if (c.includes("basket") || c.includes("nba") || c.includes("sport")) {
      return { label: "🏀 Basketbol Analiz", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.12)", border: "rgba(245, 158, 11, 0.25)" };
    }
    if (c.includes("aviation") || c.includes("blackbox") || c.includes("flight")) {
      return { label: "✈️ Havacılık Belgeseli", color: "#0ea5e9", bg: "rgba(14, 165, 233, 0.12)", border: "rgba(14, 165, 233, 0.25)" };
    }
    if (c.includes("crayon") || c.includes("military")) {
      return { label: "🖍️ Tactical Crayon", color: "#ef4444", bg: "rgba(239, 68, 68, 0.12)", border: "rgba(239, 68, 68, 0.25)" };
    }
    if (c.includes("reddit")) {
      return { label: "🤖 Reddit Hikayeleri", color: "#f97316", bg: "rgba(249, 115, 22, 0.12)", border: "rgba(249, 115, 22, 0.25)" };
    }
    if (c.includes("whatsapp")) {
      return { label: "💬 WhatsApp Dublaj", color: "#22c55e", bg: "rgba(34, 197, 94, 0.12)", border: "rgba(34, 197, 94, 0.25)" };
    }
    return { label: `📁 ${cat || "Genel"}`, color: "#818cf8", bg: "rgba(129, 140, 248, 0.12)", border: "rgba(129, 140, 248, 0.25)" };
  };

  return (
    <div style={{ paddingBottom: 60 }}>
      {/* Toast Bildirimi */}
      {toastMessage && (
        <div style={{
          position: "fixed",
          bottom: 28,
          right: 28,
          zIndex: 9999,
          padding: "12px 20px",
          borderRadius: "10px",
          background: toastMessage.type === "error" ? "rgba(244, 63, 94, 0.95)" : "rgba(16, 185, 129, 0.95)",
          color: "#fff",
          fontSize: "13.5px",
          fontWeight: 600,
          boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
          backdropFilter: "blur(8px)",
          display: "flex",
          alignItems: "center",
          gap: 10,
          animation: "fadeIn 0.2s ease-out"
        }}>
          {toastMessage.type === "error" ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Üst Başlık & İstatistik Paneli */}
      <div style={{
        marginBottom: 24,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 16
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 38,
              height: 38,
              borderRadius: 10,
              background: "linear-gradient(135deg, rgba(16,185,129,0.2), rgba(99,102,241,0.2))",
              border: "1px solid rgba(16,185,129,0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}>
              <CheckCircle2 size={22} color="#10b981" />
            </div>
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0, letterSpacing: "-0.02em" }}>
                Kontroldeki Videolar
              </h2>
              <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 3 }}>
                Tüm kanallardaki kontrol bekleyen videoları inceleyin, önizleyin ve tek tıkla yüklenecek klasörüne aktarın.
              </p>
            </div>
          </div>
        </div>

        {/* Aksiyonlar & Sayaçlar */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            padding: "8px 16px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: 10
          }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Kanal</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>{channelsData.length}</div>
            </div>
            <div style={{ width: 1, height: 22, background: "var(--border-default)" }} />
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Bekleyen Video</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#10b981" }}>{totalVideosCount}</div>
            </div>
            <div style={{ width: 1, height: 22, background: "var(--border-default)" }} />
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>Toplam Hacim</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#a5b4fc" }}>{totalSizeMB} MB</div>
            </div>
          </div>

          <button
            className="btn btn-ghost btn-sm"
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px" }}
            onClick={fetchKontrolVideos}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>Yenile</span>
          </button>
        </div>
      </div>

      {/* Arama ve Filtreleme Çubuğu */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 12,
        marginBottom: 22
      }}>
        {/* Kanal Seçici Haplar */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <button
            onClick={() => setSelectedChannelFilter("all")}
            className={`btn btn-sm ${selectedChannelFilter === "all" ? "btn-primary" : "btn-ghost"}`}
            style={{ fontSize: 12, borderRadius: 20 }}
          >
            Tüm Kanallar ({totalVideosCount})
          </button>
          {channelsData.map(ch => (
            <button
              key={ch.channel_id}
              onClick={() => setSelectedChannelFilter(ch.channel_id)}
              className={`btn btn-sm ${selectedChannelFilter === ch.channel_id ? "btn-primary" : "btn-ghost"}`}
              style={{ fontSize: 12, borderRadius: 20 }}
            >
              {ch.channel_name} ({ch.video_count})
            </button>
          ))}
        </div>

        {/* Metin Arama */}
        <div style={{ position: "relative", minWidth: 260 }}>
          <Search size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
          <input
            type="text"
            className="input input-sm"
            style={{ paddingLeft: 34, width: "100%", borderRadius: 20, fontSize: 12.5 }}
            placeholder="Başlık veya klasör ara..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Yükleniyor / Hata Durumu */}
      {loading ? (
        <div className="card" style={{ padding: "60px 20px", textAlign: "center" }}>
          <RefreshCw size={28} className="spin" style={{ margin: "0 auto 14px", color: "var(--accent-primary)" }} />
          <div style={{ fontSize: 14, color: "var(--text-muted)" }}>Kontroldeki videolar taranıyor...</div>
        </div>
      ) : error ? (
        <div className="card" style={{ padding: "30px 20px", textAlign: "center", borderColor: "rgba(244,63,94,0.3)" }}>
          <AlertCircle size={28} style={{ margin: "0 auto 10px", color: "#f43f5e" }} />
          <div style={{ fontSize: 15, fontWeight: 600, color: "#f43f5e" }}>Hata Oluştu</div>
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>{error}</div>
          <button className="btn btn-sm btn-ghost" style={{ marginTop: 14 }} onClick={fetchKontrolVideos}>Tekrar Dene</button>
        </div>
      ) : filteredChannels.length === 0 ? (
        <div className="card" style={{ padding: "70px 24px", textAlign: "center" }}>
          <div style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            background: "rgba(16, 185, 129, 0.1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 16px"
          }}>
            <Check size={28} color="#10b981" />
          </div>
          <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
            Kontrol Bekleyen Video Yok
          </div>
          <p style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 440, margin: "0 auto 18px", lineHeight: 1.6 }}>
            Harika! Tüm kanalların kontrol klasörleri temizlendi. Yeni üretilen videolar onay beklediğinde bu ekranda otomatik olarak listelenecektir.
          </p>
        </div>
      ) : (
        /* Kanal Kategorilerine Göre Gruplanmış Liste */
        <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
          {filteredChannels.map(channel => {
            const badge = getCategoryBadge(channel.topic_category);
            const isApprovingAll = channelApprovingId === channel.channel_id;

            return (
              <div
                key={channel.channel_id}
                className="channel-group-container"
                style={{
                  background: "var(--bg-secondary)",
                  borderRadius: "14px",
                  border: "1px solid var(--border-default)",
                  overflow: "hidden"
                }}
              >
                {/* Kanal Başlık Şeridi */}
                <div style={{
                  padding: "16px 20px",
                  background: "rgba(255, 255, 255, 0.02)",
                  borderBottom: "1px solid var(--border-default)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: 12
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{
                      padding: "6px 12px",
                      borderRadius: 8,
                      background: badge.bg,
                      border: `1px solid ${badge.border}`,
                      color: badge.color,
                      fontSize: 12,
                      fontWeight: 700,
                      letterSpacing: "0.01em"
                    }}>
                      {badge.label}
                    </div>

                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                          {channel.channel_name}
                        </span>
                        <code style={{ fontSize: 11, color: "var(--text-muted)", background: "rgba(255,255,255,0.04)", padding: "1px 6px", borderRadius: 4 }}>
                          {channel.channel_id}
                        </code>
                        <span style={{ fontSize: 11, padding: "1px 6px", borderRadius: 4, background: "rgba(99,102,241,0.15)", color: "#a5b4fc", fontWeight: 600 }}>
                          {channel.language ? channel.language.toUpperCase() : "TR"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Kanal Aksiyonu: Tümünü Onayla */}
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500 }}>
                      {channel.videos.length} video kontrolde
                    </span>
                    <button
                      className="btn btn-sm btn-ghost"
                      style={{
                        background: "rgba(16, 185, 129, 0.08)",
                        border: "1px solid rgba(16, 185, 129, 0.25)",
                        color: "#10b981",
                        fontWeight: 600,
                        fontSize: 12,
                        padding: "6px 14px",
                        borderRadius: 8
                      }}
                      onClick={() => handleApproveAllForChannel(channel.channel_id, channel.channel_name)}
                      disabled={isApprovingAll}
                    >
                      {isApprovingAll ? (
                        <>
                          <RefreshCw size={13} className="spin" />
                          <span>Aktarılıyor...</span>
                        </>
                      ) : (
                        <>
                          <Check size={14} />
                          <span>Bu Kanalın Tümünü Onayla ({channel.videos.length})</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Kanalın Video Kartları */}
                <div style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
                  {channel.videos.map(video => {
                    const isApproving = actionLoadingFolder === `${channel.channel_id}/${video.folder_name}`;
                    const isPlayerActive = activeVideoPlayer[video.folder_name];
                    const isDescExpanded = expandedDescriptions[video.folder_name];

                    return (
                      <div
                        key={video.folder_name}
                        className="video-kontrol-card"
                        style={{
                          background: "var(--bg-surface)",
                          borderRadius: 12,
                          border: "1px solid var(--border-subtle)",
                          padding: "16px 18px",
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 18,
                          transition: "all 0.2s ease"
                        }}
                      >
                        {/* Video Oynatıcı / Küçük Önizleme Alanı */}
                        <div style={{
                          width: video.is_shorts ? 110 : 160,
                          flexShrink: 0,
                          borderRadius: 10,
                          overflow: "hidden",
                          background: "#000",
                          border: "1px solid var(--border-default)",
                          position: "relative"
                        }}>
                          {isPlayerActive ? (
                            <video
                              src={video.video_url}
                              controls
                              autoPlay
                              playsInline
                              style={{
                                width: "100%",
                                height: video.is_shorts ? 195 : 95,
                                objectFit: "cover",
                                display: "block"
                              }}
                            />
                          ) : (
                            <div
                              style={{
                                width: "100%",
                                height: video.is_shorts ? 195 : 95,
                                position: "relative",
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                background: "linear-gradient(180deg, #182030 0%, #0d121c 100%)"
                              }}
                              onClick={() => setActiveVideoPlayer(prev => ({ ...prev, [video.folder_name]: true }))}
                            >
                              {video.thumbnail_url ? (
                                <img
                                  src={video.thumbnail_url}
                                  alt=""
                                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                                />
                              ) : (
                                <Film size={26} color="var(--text-muted)" style={{ opacity: 0.5 }} />
                              )}

                              {/* Play Rozeti */}
                              <div style={{
                                position: "absolute",
                                width: 34,
                                height: 34,
                                borderRadius: "50%",
                                background: "rgba(0,0,0,0.65)",
                                border: "1px solid rgba(255,255,255,0.2)",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                backdropFilter: "blur(4px)"
                              }}>
                                <Play size={14} color="#fff" style={{ marginLeft: 2 }} />
                              </div>

                              {/* Süre Rozeti */}
                              <div style={{
                                position: "absolute",
                                bottom: 6,
                                right: 6,
                                padding: "2px 6px",
                                borderRadius: 4,
                                background: "rgba(0,0,0,0.75)",
                                color: "#fff",
                                fontSize: 10,
                                fontWeight: 600,
                                fontFamily: "monospace"
                              }}>
                                {formatDuration(video.duration)}
                              </div>

                              {/* Shorts Rozeti */}
                              {video.is_shorts && (
                                <div style={{
                                  position: "absolute",
                                  top: 6,
                                  left: 6,
                                  padding: "2px 5px",
                                  borderRadius: 4,
                                  background: "rgba(239, 68, 68, 0.8)",
                                  color: "#fff",
                                  fontSize: 9,
                                  fontWeight: 700
                                }}>
                                  SHORTS
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Bilgi & İçerik Alanı */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
                            <div>
                              <h3 style={{
                                fontSize: 15,
                                fontWeight: 700,
                                color: "var(--text-primary)",
                                margin: 0,
                                lineHeight: 1.4
                              }}>
                                {video.title}
                              </h3>

                              <div style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 12,
                                marginTop: 6,
                                flexWrap: "wrap",
                                fontSize: 11.5,
                                color: "var(--text-muted)"
                              }}>
                                <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                                  <Clock size={12} />
                                  {formatDuration(video.duration)}
                                </span>
                                <span>•</span>
                                <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                                  <HardDrive size={12} />
                                  {video.size_mb} MB
                                </span>
                                <span>•</span>
                                <span>{video.created_at ? new Date(video.created_at).toLocaleDateString("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : ""}</span>

                                {video.voice_clone_name && (
                                  <>
                                    <span>•</span>
                                    <span style={{
                                      padding: "1px 6px",
                                      borderRadius: 4,
                                      background: "rgba(16,185,129,0.12)",
                                      color: "#34d399",
                                      fontWeight: 600,
                                      fontSize: 10.5
                                    }}>
                                      🎙️ {video.voice_clone_name}
                                    </span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Klasör Yolu Etiketi */}
                          <div style={{ marginTop: 8 }}>
                            <code
                              style={{
                                fontSize: 11,
                                color: "var(--text-muted)",
                                background: "rgba(0,0,0,0.25)",
                                padding: "2px 8px",
                                borderRadius: 4,
                                display: "inline-block",
                                maxWidth: "100%",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap"
                              }}
                              title={video.folder_path}
                            >
                              📁 kontrol/{video.folder_name}
                            </code>
                          </div>

                          {/* Açıklama & Etiketler (Akordeon) */}
                          {video.description && (
                            <div style={{ marginTop: 10 }}>
                              <button
                                style={{
                                  background: "none",
                                  border: "none",
                                  color: "var(--accent-primary)",
                                  fontSize: 11.5,
                                  cursor: "pointer",
                                  padding: 0,
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 4,
                                  fontWeight: 500
                                }}
                                onClick={() => setExpandedDescriptions(prev => ({ ...prev, [video.folder_name]: !isDescExpanded }))}
                              >
                                {isDescExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                                <span>{isDescExpanded ? "Açıklamayı Gizle" : "Açıklamayı & Etiketleri Göster"}</span>
                              </button>

                              {isDescExpanded && (
                                <div style={{
                                  marginTop: 8,
                                  padding: 10,
                                  borderRadius: 8,
                                  background: "rgba(0,0,0,0.2)",
                                  border: "1px solid var(--border-subtle)",
                                  fontSize: 11.5,
                                  color: "var(--text-secondary)",
                                  lineHeight: 1.5,
                                  whiteSpace: "pre-wrap"
                                }}>
                                  <div>{video.description}</div>

                                  {video.tags && video.tags.length > 0 && (
                                    <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginTop: 8 }}>
                                      {video.tags.map((t, tidx) => (
                                        <span
                                          key={tidx}
                                          style={{
                                            fontSize: 10.5,
                                            padding: "1px 6px",
                                            borderRadius: 4,
                                            background: "rgba(255,255,255,0.05)",
                                            color: "var(--text-muted)"
                                          }}
                                        >
                                          #{t.replace(/^#/, "")}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Sağ Aksiyon Alanı: 'Kontrolden Geçti' Butonu */}
                        <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0, alignItems: "flex-end" }}>
                          <button
                            className="btn btn-sm"
                            style={{
                              background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                              border: "none",
                              color: "#fff",
                              fontWeight: 700,
                              fontSize: 12.5,
                              padding: "8px 16px",
                              borderRadius: 8,
                              boxShadow: "0 4px 14px rgba(16, 185, 129, 0.35)",
                              display: "flex",
                              alignItems: "center",
                              gap: 7,
                              cursor: "pointer"
                            }}
                            onClick={() => handleApproveVideo(channel.channel_id, video.folder_name, video.title)}
                            disabled={isApproving}
                            title="Bu videoyu onayla ve doğrudan yüklenecek/ klasörüne taşı"
                          >
                            {isApproving ? (
                              <>
                                <RefreshCw size={14} className="spin" />
                                <span>Aktarılıyor...</span>
                              </>
                            ) : (
                              <>
                                <CheckCircle2 size={16} />
                                <span>Kontrolden Geçti</span>
                              </>
                            )}
                          </button>

                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <button
                              className="btn btn-xs btn-ghost"
                              style={{ fontSize: 11, padding: "4px 8px", color: "var(--text-muted)" }}
                              onClick={() => handleOpenFolder(video.folder_path)}
                              title="Klasörü Finder'da Aç"
                            >
                              <FolderOpen size={12} />
                              <span>Klasör</span>
                            </button>

                            <button
                              className="btn btn-xs btn-ghost"
                              style={{ fontSize: 11, padding: "4px 8px", color: "var(--text-muted)" }}
                              onClick={() => copyToClipboard(video.video_path, "Video Dosya Yolu")}
                              title="Video Dosya Yolunu Kopyala"
                            >
                              <Copy size={12} />
                              <span>Yol</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
