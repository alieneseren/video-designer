import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Zap,
  Server,
  Cloud,
  CheckCircle2,
  Clock,
  Download,
  Trash2,
  RefreshCw,
  Search,
  Filter,
  Layers,
  Film,
  Sparkles,
  AlertCircle,
  Laptop,
  Check,
  ChevronRight,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Power
} from "lucide-react";

export default function AutomationPage({ channels = [], groups = [], onNavigateServerRender }) {
  const [plans, setPlans] = useState([]);
  const [serverVideos, setServerVideos] = useState([]);
  const [queueStatus, setQueueStatus] = useState({ is_running: false, queue_count: 0, jobs_count: 0, connected: false });
  const [loading, setLoading] = useState(true);
  const [selectedChannelId, setSelectedChannelId] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedKeys, setSelectedKeys] = useState([]);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchModal, setDispatchModal] = useState(null);
  const [downloadingJobId, setDownloadingJobId] = useState(null);
  const [downloadMessage, setDownloadMessage] = useState(null);
  const [autoYoutubeUpload, setAutoYoutubeUpload] = useState(false);

  // Verileri çek
  const fetchData = useCallback(async () => {
    try {
      const [resPlans, resQueue, resVideos] = await Promise.all([
        fetch("/api/automation/unproduced-plans"),
        fetch("/api/automation/queue-status"),
        fetch("/api/automation/server-videos")
      ]);

      if (resPlans.ok) {
        const dPlans = await resPlans.json();
        setPlans(dPlans.plans || []);
      }
      if (resQueue.ok) {
        const dQueue = await resQueue.json();
        setQueueStatus(dQueue);
      }
      if (resVideos.ok) {
        const dVideos = await resVideos.json();
        setServerVideos(dVideos.videos || []);
      }
    } catch (err) {
      console.error("Otomasyon verileri alınamadı:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Filtreleme
  const filteredPlans = useMemo(() => {
    return plans.filter((p) => {
      const matchesChannel = !selectedChannelId || p.channel_id === selectedChannelId;
      const matchesSearch =
        !searchQuery ||
        (p.title || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        (p.channel_name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        (p.topic || "").toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "ready" && p.status === "ready") ||
        (statusFilter === "in_cloud_queue" && p.status === "in_cloud_queue");
      return matchesChannel && matchesSearch && matchesStatus;
    });
  }, [plans, selectedChannelId, searchQuery, statusFilter]);

  // Tümünü seç / kaldır
  const handleToggleSelectAll = () => {
    const visibleKeys = filteredPlans
      .filter((p) => p.status === "ready")
      .map((p) => `${p.channel_id}::${p.material_id || p.id}`);
    const isAllSelected = visibleKeys.length > 0 && visibleKeys.every((k) => selectedKeys.includes(k));
    if (isAllSelected) {
      setSelectedKeys((prev) => prev.filter((k) => !visibleKeys.includes(k)));
    } else {
      setSelectedKeys((prev) => Array.from(new Set([...prev, ...visibleKeys])));
    }
  };

  const handleToggleKey = (key) => {
    setSelectedKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  // Seçilenleri Bulut Kuyruğuna Gönder
  const handleDispatchQueue = async (targetItems = null) => {
    const itemsToDispatch = targetItems
      ? targetItems.filter((item) => item.status === "ready")
      : plans.filter((p) =>
          p.status === "ready" &&
          selectedKeys.includes(`${p.channel_id}::${p.material_id || p.id}`)
        );

    if (itemsToDispatch.length === 0) {
      alert("Lütfen en az bir plan seçin.");
      return;
    }

    setDispatching(true);
    try {
      const payload = {
        material_keys: itemsToDispatch.map((p) => ({
          channel_id: p.channel_id,
          material_id: p.material_id || p.id
        })),
        youtube_upload: autoYoutubeUpload
      };

      const res = await fetch("/api/automation/dispatch-queue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setDispatchModal({
          total_queued: data.total_queued || itemsToDispatch.length,
          feedback_message: data.feedback_message,
          jobs: data.jobs || []
        });
        setSelectedKeys([]);
        await fetchData();
      } else {
        alert("Kuyruğa gönderme hatası: " + (data.detail || data.message || "Bilinmeyen hata"));
      }
    } catch (err) {
      alert("Bağlantı hatası: " + err.message);
    } finally {
      setDispatching(false);
    }
  };

  // Sunucudan Mac'e indir
  const handleDownloadVideo = async (video) => {
    setDownloadingJobId(video.job_id);
    setDownloadMessage(null);
    try {
      const res = await fetch("/api/automation/download-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel_id: video.channel_id,
          job_id: video.job_id,
          delete_remote: true
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setDownloadMessage({
          job_id: video.job_id,
          text: `Video Mac'e indirildi: output/${video.channel_id}/yuklenecek/ (${data.size_mb} MB)`
        });
        setTimeout(() => setDownloadMessage(null), 8000);
        await fetchData();
      } else {
        alert("İndirme hatası: " + (data.detail || data.message || "Bilinmeyen hata"));
      }
    } catch (err) {
      alert("Bağlantı hatası: " + err.message);
    } finally {
      setDownloadingJobId(null);
    }
  };

  // Sunucudan Sil
  const handleDeleteServerVideo = async (video) => {
    if (!window.confirm(`'${video.title || video.job_id}' videosunu sunucudan silmek istediğinize emin misiniz?`)) {
      return;
    }
    try {
      const res = await fetch("/api/automation/delete-server-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel_id: video.channel_id,
          job_id: video.job_id
        })
      });
      if (res.ok) {
        await fetchData();
      } else {
        alert("Silinemedi.");
      }
    } catch (err) {
      alert("Silme hatası: " + err.message);
    }
  };

  const isVideoMatchingPlan = useCallback((v, p) => {
    if (!v || !p) return false;
    const targetMatId = p.material_id || p.id;
    if (v.job_id === `exec_${targetMatId}` || v.job_id === targetMatId) return true;
    if (targetMatId && v.job_id.includes(targetMatId)) return true;
    if (p.row_id && v.job_id.includes(`_${p.row_id}_`)) {
      const cleanPChan = (p.channel_id || "").replace("group:", "").toLowerCase();
      if ((v.channel_id || "").toLowerCase() === cleanPChan || (v.job_id || "").toLowerCase().includes(cleanPChan)) {
        return true;
      }
    }
    return false;
  }, []);

  const readyCount = plans.filter((p) => p.status === "ready").length;
  const inQueueCount = plans.filter((p) => {
    if (p.status !== "in_cloud_queue") return false;
    const isReady = serverVideos.some((v) => isVideoMatchingPlan(v, p));
    return !isReady;
  }).length;

  return (
    <div style={{ maxWidth: 1240, margin: "0 auto", paddingBottom: 60 }}>
      {/* ── ÜST İSTATİSTİK KARTLARI ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: 16,
          marginBottom: 24
        }}
      >
        {/* Kart 1: Üretime Hazır Planlar */}
        <div
          className="card"
          style={{
            padding: "18px 20px",
            background: "linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)",
            border: "1px solid rgba(148, 163, 184, 0.15)",
            borderRadius: 16
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 600 }}>Üretime Hazır Planlar</span>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: "rgba(59, 130, 246, 0.15)",
                color: "#60a5fa",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
            >
              <Layers size={18} />
            </div>
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, marginTop: 10, color: "#f8fafc" }}>{readyCount}</div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
            Senaryo & materyalleri hazır bekleyen içerikler
          </div>
        </div>

        {/* Kart 2: Bulut Kuyruğu Durumu */}
        <div
          className="card"
          style={{
            padding: "18px 20px",
            background: "linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)",
            border: "1px solid rgba(245, 158, 11, 0.2)",
            borderRadius: 16
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 600 }}>Bulut Sıralı Kuyruk</span>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: "rgba(245, 158, 11, 0.15)",
                color: "#fbbf24",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
            >
              <Clock size={18} />
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 10 }}>
            <span style={{ fontSize: 28, fontWeight: 800, color: "#f8fafc" }}>
              {queueStatus.connected ? (queueStatus.queue_count ?? 0) : inQueueCount}
            </span>
            <span style={{ fontSize: 12, color: queueStatus.is_running ? "#34d399" : "#94a3b8", fontWeight: 600 }}>
              {queueStatus.is_running ? "⚡ Sırayla Üretiliyor" : "Beklemede"}
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
            Sunucuda sırasını bekleyen render görevleri
          </div>
        </div>

        {/* Kart 3: Sunucuda Hazır Videolar */}
        <div
          className="card"
          style={{
            padding: "18px 20px",
            background: "linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)",
            border: "1px solid rgba(16, 185, 129, 0.2)",
            borderRadius: 16
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 600 }}>Sunucuda Hazır Videolar</span>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: "rgba(16, 185, 129, 0.15)",
                color: "#34d399",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
            >
              <Film size={18} />
            </div>
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, marginTop: 10, color: "#f8fafc" }}>{serverVideos.length}</div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
            Mac'e indirilmeye hazır tamamlanmış videolar
          </div>
        </div>

        {/* Kart 4: Sunucu Durumu */}
        <div
          className="card"
          style={{
            padding: "18px 20px",
            background: "linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)",
            border: "1px solid rgba(99, 102, 241, 0.2)",
            borderRadius: 16
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 600 }}>Oracle Cloud Sunucusu</span>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: queueStatus.connected ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                color: queueStatus.connected ? "#34d399" : "#f87171",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
            >
              <Server size={18} />
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10 }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: queueStatus.connected ? "#10b981" : "#ef4444",
                boxShadow: queueStatus.connected ? "0 0 10px #10b981" : "none"
              }}
            />
            <span style={{ fontSize: 16, fontWeight: 700, color: "#f8fafc" }}>
              {queueStatus.connected ? "132.226.187.103" : "Bağlantı Yok"}
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
            Düşük öncelik (nice 19) · Otonom Arka Plan
          </div>
        </div>
      </div>

      {/* ── İNDİRME BİLDİRİMİ ── */}
      {downloadMessage && (
        <div
          style={{
            marginBottom: 20,
            padding: "14px 18px",
            borderRadius: 12,
            background: "rgba(16, 185, 129, 0.15)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            color: "#34d399",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: 13,
            fontWeight: 600
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <CheckCircle2 size={18} />
            <span>{downloadMessage.text}</span>
          </div>
          <button
            onClick={() => setDownloadMessage(null)}
            style={{ background: "none", border: "none", color: "#34d399", cursor: "pointer", fontSize: 16 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* ── BÖLÜM 1: ÜRETİLMEMİŞ PLANLAR VE BULUT KUYRUĞUNA GÖNDERME ── */}
      <div
        className="card"
        style={{
          borderRadius: 16,
          padding: 24,
          background: "var(--card-bg, #1e293b)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          marginBottom: 32
        }}
      >
        {/* Başlık ve Eylemler Barı */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            marginBottom: 20
          }}
        >
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 10 }}>
              <Zap size={20} color="#38bdf8" />
              Üretim Materyalleri Hazır Planlar
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: 20,
                  background: "rgba(56, 189, 248, 0.15)",
                  color: "#38bdf8"
                }}
              >
                {filteredPlans.length} Adet
              </span>
            </h2>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-muted)" }}>
              İstediğiniz planları seçip tek tıkla Oracle Cloud sunucusuna aktarın. Gönderim tamamlandıktan sonra
              bilgisayarınızı kapatabilirsiniz.
            </p>
          </div>

          {/* Ana Eylem Butonu */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button
              className="btn btn-primary"
              disabled={selectedKeys.length === 0 || dispatching}
              onClick={() => handleDispatchQueue()}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "10px 22px",
                borderRadius: 12,
                fontSize: 14,
                fontWeight: 700,
                background:
                  selectedKeys.length > 0
                    ? "linear-gradient(135deg, #0284c7 0%, #6366f1 100%)"
                    : "rgba(255, 255, 255, 0.1)",
                border: "none",
                boxShadow: selectedKeys.length > 0 ? "0 4px 20px rgba(2, 132, 199, 0.4)" : "none",
                cursor: selectedKeys.length > 0 ? "pointer" : "not-allowed",
                transition: "all 0.2s ease"
              }}
            >
              {dispatching ? (
                <>
                  <RefreshCw size={16} className="spin" />
                  Sunucuya Aktarılıyor ve Doğrulanıyor...
                </>
              ) : (
                <>
                  <Cloud size={16} />
                  ☁️ Seçilenleri Üretime Gönder ({selectedKeys.length})
                </>
              )}
            </button>
          </div>
        </div>

        {/* Filtre ve Arama Çubuğu */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            padding: "12px 16px",
            background: "rgba(0, 0, 0, 0.2)",
            borderRadius: 12,
            marginBottom: 16
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, minWidth: 280 }}>
            {/* Kanal Seçimi */}
            <select
              value={selectedChannelId}
              onChange={(e) => setSelectedChannelId(e.target.value)}
              style={{
                padding: "8px 12px",
                borderRadius: 8,
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                color: "#f8fafc",
                fontSize: 13,
                outline: "none"
              }}
            >
              <option value="">Tüm Kanallar ({channels.length + (groups ? groups.length : 0)})</option>
              {groups && groups.length > 0 && (
                <optgroup label="📁 Kanal Grupları (Çok Dilli)">
                  {groups.map((g) => {
                    const gid = g.group_id || g.id;
                    return (
                      <option key={gid} value={`group:${gid}`}>
                        📁 {g.name || g.group_name || gid} ({g.channel_ids?.length || 0} Kanal)
                      </option>
                    );
                  })}
                </optgroup>
              )}
              <optgroup label="📺 Tekil Kanallar">
                {channels.map((c) => (
                  <option key={c.channel_id} value={c.channel_id}>
                    📺 {c.name || c.channel_id}
                  </option>
                ))}
              </optgroup>
            </select>

            {/* Arama Inputu */}
            <div style={{ position: "relative", flex: 1 }}>
              <Search
                size={14}
                style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#64748b" }}
              />
              <input
                type="text"
                placeholder="Başlık, konu veya kanal ara..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px 8px 32px",
                  borderRadius: 8,
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  color: "#f8fafc",
                  fontSize: 13,
                  outline: "none"
                }}
              />
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* Tümünü Seç Butonu */}
            <button
              onClick={handleToggleSelectAll}
              className="btn btn-ghost btn-sm"
              style={{
                fontSize: 12,
                fontWeight: 600,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 12px",
                borderRadius: 8,
                background: "rgba(255, 255, 255, 0.05)"
              }}
            >
              <Check size={14} />
              {filteredPlans.length > 0 &&
              filteredPlans.every((p) => selectedKeys.includes(`${p.channel_id}::${p.material_id || p.id}`))
                ? "Seçimi Kaldır"
                : `Tümünü Seç (${filteredPlans.length})`}
            </button>

            <button
              onClick={fetchData}
              className="btn btn-ghost btn-sm"
              title="Yenile"
              style={{ padding: "6px 10px", borderRadius: 8 }}
            >
              <RefreshCw size={14} className={loading ? "spin" : ""} />
            </button>
          </div>
        </div>

        {/* Tablo Listesi */}
        {loading && plans.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
            <RefreshCw size={24} className="spin" style={{ margin: "0 auto 12px", display: "block" }} />
            Materyaller yükleniyor...
          </div>
        ) : filteredPlans.length === 0 ? (
          <div
            style={{
              padding: 48,
              textAlign: "center",
              color: "var(--text-muted)",
              background: "rgba(0,0,0,0.1)",
              borderRadius: 12
            }}
          >
            <Layers size={36} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f8fafc", margin: "0 0 6px" }}>
              Üretime Hazır Plan Bulunamadı
            </h3>
            <p style={{ fontSize: 13, margin: 0 }}>
              {searchQuery || selectedChannelId
                ? "Arama kriterlerine uygun materyal bulunamadı."
                : "Tüm mevcut materyaller üretilmiş durumda veya henüz Gemini'den senaryo kaydedilmemiş."}
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.1)", color: "#94a3b8", textAlign: "left" }}>
                  <th style={{ width: 44, padding: "12px 10px", textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={
                        filteredPlans.some((p) => p.status === "ready") &&
                        filteredPlans
                          .filter((p) => p.status === "ready")
                          .every((p) => selectedKeys.includes(`${p.channel_id}::${p.material_id || p.id}`))
                      }
                      onChange={handleToggleSelectAll}
                      style={{ cursor: "pointer", width: 16, height: 16 }}
                    />
                  </th>
                  <th style={{ padding: "12px 10px" }}>Kanal</th>
                  <th style={{ padding: "12px 10px" }}>Satır</th>
                  <th style={{ padding: "12px 10px" }}>Video Başlığı & Senaryo</th>
                  <th style={{ padding: "12px 10px" }}>Detaylar</th>
                  <th style={{ padding: "12px 10px" }}>Durum</th>
                  <th style={{ padding: "12px 10px", textAlign: "right" }}>Eylem</th>
                </tr>
              </thead>
              <tbody>
                {filteredPlans.map((p) => {
                  const itemKey = `${p.channel_id}::${p.material_id || p.id}`;
                  const isSelected = selectedKeys.includes(itemKey);
                  const matchedVideo = serverVideos.find((v) => isVideoMatchingPlan(v, p));
                  const isReadyOnServer = Boolean(matchedVideo);
                  const isQueued = p.status === "in_cloud_queue" && !isReadyOnServer;

                  return (
                    <tr
                      key={itemKey}
                      style={{
                        borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                        background: isSelected ? "rgba(2, 132, 199, 0.08)" : "transparent",
                        transition: "background 0.15s ease"
                      }}
                    >
                      <td style={{ padding: "12px 10px", textAlign: "center" }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          disabled={p.status !== "ready" || isReadyOnServer || isQueued}
                          onChange={() => handleToggleKey(itemKey)}
                          style={{ cursor: "pointer", width: 16, height: 16 }}
                        />
                      </td>
                      <td style={{ padding: "12px 10px" }}>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: 6,
                            background: p.channel_id?.startsWith("group:")
                              ? "rgba(139, 92, 246, 0.18)"
                              : "rgba(255, 255, 255, 0.08)",
                            color: p.channel_id?.startsWith("group:")
                              ? "#c084fc"
                              : "#e2e8f0",
                            border: p.channel_id?.startsWith("group:")
                              ? "1px solid rgba(139, 92, 246, 0.35)"
                              : "none"
                          }}
                        >
                          {p.channel_name || p.channel_id}
                        </span>
                      </td>
                      <td style={{ padding: "12px 10px", color: "#64748b", fontWeight: 600 }}>
                        #{p.row_id || "—"}
                      </td>
                      <td style={{ padding: "12px 10px", maxWidth: 440 }}>
                        <div style={{ fontWeight: 600, color: "#f8fafc", lineHeight: 1.4 }}>{p.title}</div>
                        {p.topic && p.topic !== p.title && (
                          <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{p.topic}</div>
                        )}
                      </td>
                      <td style={{ padding: "12px 10px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span
                            style={{
                              fontSize: 11,
                              padding: "2px 6px",
                              borderRadius: 4,
                              background: "rgba(59, 130, 246, 0.1)",
                              color: "#60a5fa"
                            }}
                          >
                            {p.scene_count} Sahne
                          </span>
                          {p.has_images && (
                            <span
                              style={{
                                fontSize: 11,
                                padding: "2px 6px",
                                borderRadius: 4,
                                background: "rgba(168, 85, 247, 0.1)",
                                color: "#c084fc"
                              }}
                            >
                              Görseller Hazır
                            </span>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: "12px 10px" }}>
                        {isReadyOnServer ? (
                          <span
                            style={{
                              fontSize: 11,
                              fontWeight: 600,
                              padding: "3px 8px",
                              borderRadius: 12,
                              background: "rgba(16, 185, 129, 0.15)",
                              color: "#34d399",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4
                            }}
                          >
                            <CheckCircle2 size={11} /> Sunucuda Hazır
                          </span>
                        ) : isQueued ? (
                          <span
                            style={{
                              fontSize: 11,
                              fontWeight: 600,
                              padding: "3px 8px",
                              borderRadius: 12,
                              background: "rgba(245, 158, 11, 0.15)",
                              color: "#fbbf24",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4
                            }}
                          >
                            <Clock size={11} /> Bulut Kuyruğunda
                          </span>
                        ) : (
                          <span
                            style={{
                              fontSize: 11,
                              fontWeight: 600,
                              padding: "3px 8px",
                              borderRadius: 12,
                              background: "rgba(59, 130, 246, 0.15)",
                              color: "#60a5fa",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4
                            }}
                          >
                            <CheckCircle2 size={11} /> Üretime Hazır
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "12px 10px", textAlign: "right" }}>
                        {isReadyOnServer && matchedVideo ? (
                          <button
                            className="btn btn-ghost btn-sm"
                            disabled={downloadingJobId === matchedVideo.job_id}
                            onClick={() => handleDownloadVideo(matchedVideo)}
                            style={{
                              fontSize: 12,
                              padding: "4px 10px",
                              borderRadius: 8,
                              color: "#34d399",
                              background: "rgba(16, 185, 129, 0.15)",
                              fontWeight: 600
                            }}
                          >
                            {downloadingJobId === matchedVideo.job_id ? "⏳ İndiriliyor..." : "📥 İndir"}
                          </button>
                        ) : (
                          <button
                            className="btn btn-ghost btn-sm"
                            disabled={dispatching || isQueued}
                            onClick={() => handleDispatchQueue([p])}
                            style={{
                              fontSize: 12,
                              padding: "4px 10px",
                              borderRadius: 8,
                              color: isQueued ? "#94a3b8" : "#38bdf8",
                              background: isQueued ? "rgba(148, 163, 184, 0.1)" : "rgba(56, 189, 248, 0.1)"
                            }}
                          >
                            {isQueued ? "⏳ Kuyrukta" : "☁️ Gönder"}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── BÖLÜM 2: SUNUCUDA ÜRETİLMİŞ VİDEOLAR (İNDİRME MERKEZİ) ── */}
      <div
        className="card"
        style={{
          borderRadius: 16,
          padding: 24,
          background: "var(--card-bg, #1e293b)",
          border: "1px solid rgba(255, 255, 255, 0.08)"
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            marginBottom: 20
          }}
        >
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 10 }}>
              <Film size={20} color="#34d399" />
              Sunucuda Üretilmiş Videolar (İndirme Merkezi)
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: 20,
                  background: "rgba(16, 185, 129, 0.15)",
                  color: "#34d399"
                }}
              >
                {serverVideos.length} Hazır
              </span>
            </h2>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-muted)" }}>
              Oracle Cloud sunucusunda üretilen videolar sunucuda saklanır. İstediğiniz zaman ilgili kanalın 'yuklenecek'
              klasörüne tek tıkla indirebilirsiniz.
            </p>
          </div>

          <button
            onClick={fetchData}
            className="btn btn-ghost btn-sm"
            style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
          >
            <RefreshCw size={13} className={loading ? "spin" : ""} /> Videoları Tara
          </button>
        </div>

        {serverVideos.length === 0 ? (
          <div
            style={{
              padding: 40,
              textAlign: "center",
              color: "var(--text-muted)",
              background: "rgba(0,0,0,0.1)",
              borderRadius: 12
            }}
          >
            <Film size={32} style={{ margin: "0 auto 10px", opacity: 0.3 }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: "#f8fafc" }}>Sunucuda Henüz Üretilmiş Video Yok</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>
              Kuyruğa gönderilen planlar derlendikçe videolar burada listelenecektir.
            </div>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
              gap: 16
            }}
          >
            {serverVideos.map((v) => {
              const isDownloading = downloadingJobId === v.job_id;

              return (
                <div
                  key={v.file_path || `${v.channel_id}_${v.job_id}`}
                  style={{
                    padding: 18,
                    borderRadius: 14,
                    background: "rgba(0, 0, 0, 0.25)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    gap: 14
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: 6,
                          background: "rgba(56, 189, 248, 0.15)",
                          color: "#38bdf8"
                        }}
                      >
                        {v.channel_id}
                      </span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: "#34d399" }}>
                        {v.size_mb} MB
                      </span>
                    </div>

                    <h4
                      style={{
                        margin: "10px 0 4px",
                        fontSize: 14,
                        fontWeight: 700,
                        color: "#f8fafc",
                        lineHeight: 1.4
                      }}
                    >
                      {v.title || `${v.channel_id} - ${v.job_id}`}
                    </h4>
                    <div style={{ fontSize: 11, color: "#64748b" }}>
                      İş ID: {v.job_id} {v.created_at && `· ${new Date(v.created_at).toLocaleDateString("tr-TR")}`}
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 10,
                      paddingTop: 12,
                      borderTop: "1px solid rgba(255, 255, 255, 0.06)"
                    }}
                  >
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={isDownloading}
                      onClick={() => handleDownloadVideo(v)}
                      style={{
                        flex: 1,
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 6,
                        padding: "8px 14px",
                        borderRadius: 10,
                        fontSize: 13,
                        fontWeight: 600,
                        background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                        border: "none",
                        color: "#fff",
                        cursor: isDownloading ? "not-allowed" : "pointer"
                      }}
                    >
                      {isDownloading ? (
                        <>
                          <RefreshCw size={13} className="spin" />
                          Mac'e İndiriliyor...
                        </>
                      ) : (
                        <>
                          <Download size={13} />
                          Mac'e İndir (yuklenecek/)
                        </>
                      )}
                    </button>

                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleDeleteServerVideo(v)}
                      title="Sunucudan Sil"
                      style={{
                        padding: "8px 10px",
                        borderRadius: 10,
                        color: "#f87171",
                        background: "rgba(239, 68, 68, 0.1)"
                      }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── GÜVENLE BİLGİSAYARI KAPATABİLİRSİNİZ MODALI ── */}
      {dispatchModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: 20
          }}
        >
          <div
            style={{
              background: "#0f172a",
              border: "1px solid rgba(56, 189, 248, 0.3)",
              borderRadius: 20,
              maxWidth: 580,
              width: "100%",
              padding: 32,
              boxShadow: "0 20px 50px rgba(0, 0, 0, 0.8)",
              textAlign: "center"
            }}
          >
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 20,
                background: "linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(56, 189, 248, 0.2) 100%)",
                border: "1px solid rgba(56, 189, 248, 0.4)",
                color: "#38bdf8",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 20px"
              }}
            >
              <ShieldCheck size={36} color="#34d399" />
            </div>

            <h3 style={{ fontSize: 20, fontWeight: 800, color: "#f8fafc", margin: "0 0 10px" }}>
              Tüm Materyaller Sunucuya Aktarıldı ve Doğrulandı!
            </h3>

            <p style={{ fontSize: 14, color: "#94a3b8", lineHeight: 1.6, margin: "0 0 20px" }}>
              Seçilen <strong style={{ color: "#38bdf8" }}>{dispatchModal.total_queued} adet video planı</strong>, senaryoları ve tüm görsel materyalleriyle birlikte Oracle Cloud sunucusuna aktarıldı, dosya bütünlüğü doğrulandı ve sıralı üretim motoru başlatıldı.
            </p>

            {/* Vurgulu Kapatma Kartı */}
            <div
              style={{
                background: "linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.7) 100%)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                borderRadius: 14,
                padding: "16px 20px",
                textAlign: "left",
                marginBottom: 24,
                display: "flex",
                gap: 14,
                alignItems: "flex-start"
              }}
            >
              <Laptop size={28} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <h5 style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 700, color: "#34d399" }}>
                  Yerel Bilgisayarınızı (Mac) Güvenle Kapatabilirsiniz
                </h5>
                <p style={{ margin: 0, fontSize: 12, color: "#cbd5e1", lineHeight: 1.5 }}>
                  Oracle Cloud sunucusu arka planda tüm videoları tek tek (FIFO, nice 19) üretecektir. Mac'inizi kapatsanız dahi sunucudaki üretim kesintisiz devam eder. Videolar hazır olduğunda sunucuda saklanacaktır.
                </p>
              </div>
            </div>

            <button
              className="btn btn-primary"
              onClick={() => setDispatchModal(null)}
              style={{
                width: "100%",
                padding: "12px 24px",
                borderRadius: 12,
                fontSize: 15,
                fontWeight: 700,
                background: "linear-gradient(135deg, #0284c7 0%, #6366f1 100%)",
                border: "none",
                cursor: "pointer"
              }}
            >
              Harika, Anladım
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
