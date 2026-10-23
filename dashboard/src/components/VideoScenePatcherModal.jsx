import { useState, useEffect } from "react";
import {
  Scissors,
  X,
  Play,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Layers,
  RefreshCw,
  Gauge,
  AlertTriangle,
  Compass,
  TrendingDown,
  Moon,
  Archive,
  Film,
  Plus,
  Trash2,
  Check,
  Video
} from "lucide-react";

export default function VideoScenePatcherModal({ isOpen, onClose, video, onPatched }) {
  const [critiqueText, setCritiqueText] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPatching, setIsPatching] = useState(false);
  const [presets, setPresets] = useState([]);
  const [patches, setPatches] = useState([]);
  const [patchResult, setPatchResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [activePresetFilter, setActivePresetFilter] = useState("all");

  // Hazır şablonları yükle
  useEffect(() => {
    if (!isOpen) return;
    document.body.style.overflow = "hidden";
    setErrorMessage("");
    setPatchResult(null);

    fetch("/api/video-patch/presets")
      .then(r => r.json())
      .then(d => {
        if (d.presets) setPresets(d.presets);
      })
      .catch(err => console.error("Presets error:", err));

    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!isOpen || !video) return null;

  const handleAnalyze = async () => {
    if (!critiqueText.trim()) {
      setErrorMessage("Lütfen en az bir zaman aralığı veya sahne eleştirisi yazın/yapıştırın.");
      return;
    }

    setIsAnalyzing(true);
    setErrorMessage("");
    setPatchResult(null);

    try {
      const res = await fetch("/api/video-patch/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_folder: video.folder || "",
          video_path: video.video_path || "",
          critique_text: critiqueText
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setPatches(data.detected_patches || []);
        if (!data.detected_patches || data.detected_patches.length === 0) {
          setErrorMessage("Metin içinde belirgin bir zaman aralığı (Örn: 02:12 - 04:47) tespit edilemedi. Lütfen '02:12 - 04:47' şeklinde belirtin veya elle ekleyin.");
        }
      } else {
        setErrorMessage(data.detail || "Analiz sırasında hata oluştu.");
      }
    } catch (err) {
      setErrorMessage("Bağlantı hatası: " + err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApplyPatches = async () => {
    const activePatches = patches.filter(p => p.enabled);
    if (activePatches.length === 0) {
      setErrorMessage("Lütfen uygulanacak en az bir yama seçin.");
      return;
    }

    setIsPatching(true);
    setErrorMessage("");
    setPatchResult(null);

    try {
      const res = await fetch("/api/video-patch/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_folder: video.folder || "",
          video_path: video.video_path || "",
          patches: activePatches
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setPatchResult(data);
        if (onPatched) onPatched(data);
      } else {
        setErrorMessage(data.detail || data.message || "Yama uygulama başarısız oldu.");
      }
    } catch (err) {
      setErrorMessage("Yama hatası: " + err.message);
    } finally {
      setIsPatching(false);
    }
  };

  const handleTogglePatch = (id) => {
    setPatches(prev => prev.map(p => p.id === id ? { ...p, enabled: !p.enabled } : p));
  };

  const handleTypeChange = (id, newType) => {
    setPatches(prev => prev.map(p => p.id === id ? { ...p, replacement_type: newType } : p));
  };

  const handleDeletePatch = (id) => {
    setPatches(prev => prev.filter(p => p.id !== id));
  };

  const handleAddManualPatch = () => {
    const newId = `patch_${patches.length + 1}`;
    setPatches(prev => [
      ...prev,
      {
        id: newId,
        start_sec: 0,
        end_sec: 15,
        start_time: "00:00",
        end_time: "00:15",
        duration: 15,
        issue_title: "Özel Sahne Değişimi",
        replacement_type: "telemetry_gauge",
        description: "Elle eklenen sahne telemetrisi.",
        enabled: true
      }
    ]);
  };

  const getPresetIcon = (type) => {
    switch (type) {
      case "telemetry_gauge": return <Gauge size={14} style={{ color: "#38bdf8" }} />;
      case "cockpit_alarm": return <AlertTriangle size={14} style={{ color: "#f43f5e" }} />;
      case "telemetry_radar": return <Compass size={14} style={{ color: "#34d399" }} />;
      case "cockpit_altimeter_dive": return <TrendingDown size={14} style={{ color: "#fbbf24" }} />;
      case "dark_cockpit": return <Moon size={14} style={{ color: "#a78bfa" }} />;
      case "wikimedia": return <Archive size={14} style={{ color: "#94a3b8" }} />;
      default: return <Gauge size={14} style={{ color: "#38bdf8" }} />;
    }
  };

  const totalPatchSeconds = patches.filter(p => p.enabled).reduce((sum, p) => sum + (p.duration || 0), 0);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        backgroundColor: "rgba(3, 7, 18, 0.82)",
        backdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20
      }}
      onClick={(e) => { if (e.target === e.currentTarget && !isPatching) onClose(); }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 960,
          maxHeight: "92vh",
          backgroundColor: "#0b0f19",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: 16,
          boxShadow: "0 25px 60px -15px rgba(0, 0, 0, 0.85), 0 0 35px rgba(56, 189, 248, 0.15)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden"
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(180deg, rgba(15, 23, 42, 0.8) 0%, rgba(11, 15, 25, 0.6) 100%)"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                width: 42,
                height: 42,
                borderRadius: 10,
                background: "linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)",
                border: "1px solid rgba(56, 189, 248, 0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#38bdf8"
              }}
            >
              <Scissors size={20} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "#f8fafc" }}>
                  AI Akıllı Sahne Düzenleyici & In-Place Video Yamalayıcı
                </h3>
                <span
                  style={{
                    fontSize: 10.5,
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: 20,
                    background: "rgba(16, 185, 129, 0.15)",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                    color: "#34d399",
                    letterSpacing: "0.04em"
                  }}
                >
                  ⚡ SIFIRDAN RENDER YOK (5-15 SN)
                </span>
              </div>
              <p style={{ margin: "3px 0 0", fontSize: 12, color: "#94a3b8" }}>
                Hedef Video: <strong style={{ color: "#e2e8f0" }}>{video.title || video.folder}</strong>
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            disabled={isPatching}
            style={{
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: 8,
              padding: "6px 8px",
              color: "#94a3b8",
              cursor: isPatching ? "not-allowed" : "pointer",
              transition: "all 0.15s ease"
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: "20px 24px", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: 18 }}>
          {/* Başarı Bildirimi */}
          {patchResult && (
            <div
              style={{
                background: "rgba(16, 185, 129, 0.12)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                borderRadius: 12,
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12, color: "#34d399" }}>
                <CheckCircle2 size={22} />
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>Video Başarıyla Yamalandı!</div>
                  <div style={{ fontSize: 12, color: "#a7f3d0", marginTop: 2 }}>
                    {patchResult.message} Orijinal video yedeklendi ({patchResult.backup_video?.split("/").pop()}).
                  </div>
                </div>
              </div>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => window.open(`file://${patchResult.patched_video}`)}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 600 }}
              >
                <Play size={13} /> Videoyu Aç
              </button>
            </div>
          )}

          {/* Hata Bildirimi */}
          {errorMessage && (
            <div
              style={{
                background: "rgba(244, 63, 94, 0.12)",
                border: "1px solid rgba(244, 63, 94, 0.3)",
                borderRadius: 10,
                padding: "12px 16px",
                display: "flex",
                alignItems: "center",
                gap: 10,
                color: "#fb7185",
                fontSize: 12.5
              }}
            >
              <AlertCircle size={18} />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Doğal Dil Eleştiri ve İstek Kutusu */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid rgba(255, 255, 255, 0.07)",
              borderRadius: 12,
              padding: 16
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9", display: "flex", alignItems: "center", gap: 6 }}>
                <Sparkles size={15} style={{ color: "#38bdf8" }} />
                AI Sahne Eleştirisini / Değişecek Kısımları Girin:
              </label>
              <span style={{ fontSize: 11, color: "#64748b" }}>
                Örn: 02:12 – 04:47 arasındaki şehir drone görüntüsünü yapay ufukla değiştir
              </span>
            </div>

            <textarea
              rows={4}
              value={critiqueText}
              onChange={(e) => setCritiqueText(e.target.value)}
              placeholder="İnceleme metnini buraya yapıştırın veya '02:12 - 04:47 arasına analog kokpit yapay ufuk telemetrisi koy' şeklinde yazın..."
              style={{
                width: "100%",
                background: "#080c14",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                borderRadius: 8,
                padding: "12px 14px",
                color: "#e2e8f0",
                fontSize: 12.5,
                lineHeight: 1.6,
                fontFamily: "inherit",
                resize: "vertical",
                outline: "none"
              }}
            />

            {/* Hızlı Öneri Hapları */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              <span style={{ fontSize: 11, color: "#64748b", fontWeight: 600 }}>Hızlı Şablonlar:</span>
              {[
                { label: "🚨 02:12-04:47 Asya Şehrini Yapay Ufukla Değiştir", text: "Tam 2,5 Dakika Süren Işıl Işıl Asya Şehri (02:12 – 04:47) yerine Boeing 737 yapay ufuk ve overbank telemetrisi koy." },
                { label: "⚠️ 04:48-05:22 Dalışta GPWS Kokpit Alarmı", text: "Uçak denize çakılırken güneşli gökyüzü (04:48 – 05:22) yerine GPWS BANK ANGLE / PULL UP kokpit alarmı yerleştir." },
                { label: "🗺️ 05:24-05:42 SR-71 Müzesini Radar Haritasıyla Değiştir", text: "Havacılık Müzesi ve SR-71 Blackbird (05:24 – 05:42) yerine Taktik Uçuş Rekonstrüksiyon Radar Haritası koy." },
                { label: "📉 06:04-07:18 Altimetre & Hız Dalışı", text: "Son dalışta hareketsiz park fotoğrafları (06:04 – 07:18) yerine hızla sıfıra düşen altimetre ve aşırı hız clacker sahneleri koy." }
              ].map((pill, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setCritiqueText(prev => prev ? prev + "\n\n" + pill.text : pill.text)}
                  style={{
                    background: "rgba(56, 189, 248, 0.08)",
                    border: "1px solid rgba(56, 189, 248, 0.25)",
                    borderRadius: 6,
                    padding: "4px 8px",
                    color: "#7dd3fc",
                    fontSize: 11,
                    cursor: "pointer",
                    transition: "all 0.15s ease"
                  }}
                >
                  {pill.label}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
              <button
                className="btn btn-primary btn-sm"
                disabled={isAnalyzing || !critiqueText.trim()}
                onClick={handleAnalyze}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 16px",
                  fontWeight: 600,
                  fontSize: 12.5
                }}
              >
                {isAnalyzing ? <RefreshCw size={14} className="spin" /> : <Sparkles size={14} />}
                {isAnalyzing ? "AI Sahneleri İnceliyor..." : "🧠 AI ile Analiz Et & Yamaları Çıkar"}
              </button>
            </div>
          </div>

          {/* Tespit Edilen Sahne Yamaları */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <h4 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: "#f8fafc", display: "flex", alignItems: "center", gap: 8 }}>
                <Layers size={16} style={{ color: "#38bdf8" }} />
                Uygulanacak Sahne Yamaları ({patches.length})
              </h4>

              <button
                className="btn btn-ghost btn-sm"
                onClick={handleAddManualPatch}
                style={{ fontSize: 11, display: "inline-flex", alignItems: "center", gap: 5 }}
              >
                <Plus size={13} /> Elle Sahne Ekle
              </button>
            </div>

            {patches.length === 0 ? (
              <div
                style={{
                  border: "1px dashed rgba(255, 255, 255, 0.12)",
                  borderRadius: 12,
                  padding: "30px 20px",
                  textAlign: "center",
                  color: "#64748b"
                }}
              >
                <Scissors size={28} style={{ opacity: 0.3, marginBottom: 8 }} />
                <div style={{ fontSize: 13, fontWeight: 500 }}>Henüz bir yama tespit edilmedi.</div>
                <div style={{ fontSize: 11.5, marginTop: 4 }}>
                  Yukarıdaki kutuya eleştiri metnini yapıştırıp "AI ile Analiz Et" butonuna basın.
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {patches.map((patch) => {
                  return (
                    <div
                      key={patch.id}
                      style={{
                        background: patch.enabled ? "rgba(255, 255, 255, 0.025)" : "rgba(255, 255, 255, 0.008)",
                        border: `1px solid ${patch.enabled ? "rgba(56, 189, 248, 0.25)" : "rgba(255, 255, 255, 0.06)"}`,
                        borderRadius: 10,
                        padding: "12px 16px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 14,
                        opacity: patch.enabled ? 1 : 0.5,
                        transition: "all 0.2s ease"
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0, flex: 1 }}>
                        <input
                          type="checkbox"
                          checked={patch.enabled}
                          onChange={() => handleTogglePatch(patch.id)}
                          style={{ width: 16, height: 16, accentColor: "#38bdf8", cursor: "pointer" }}
                        />

                        <div
                          style={{
                            background: "rgba(56, 189, 248, 0.15)",
                            color: "#38bdf8",
                            padding: "4px 8px",
                            borderRadius: 6,
                            fontSize: 12,
                            fontWeight: 700,
                            fontFamily: "monospace",
                            whiteSpace: "nowrap"
                          }}
                        >
                          {patch.start_time} ➔ {patch.end_time} ({Math.round(patch.duration)}s)
                        </div>

                        <div style={{ minWidth: 0, flex: 1 }}>
                          <div style={{ fontSize: 13, fontWeight: 600, color: "#f8fafc" }}>
                            {patch.issue_title}
                          </div>
                          <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                            {patch.description}
                          </div>
                        </div>
                      </div>

                      {/* Görsel Tipi Seçici */}
                      <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          {getPresetIcon(patch.replacement_type)}
                          <select
                            value={patch.replacement_type}
                            onChange={(e) => handleTypeChange(patch.id, e.target.value)}
                            style={{
                              background: "#080c14",
                              border: "1px solid rgba(255, 255, 255, 0.15)",
                              borderRadius: 6,
                              padding: "5px 10px",
                              color: "#e2e8f0",
                              fontSize: 11.5,
                              outline: "none"
                            }}
                          >
                            {presets.map(pr => (
                              <option key={pr.id} value={pr.id}>
                                {pr.name}
                              </option>
                            ))}
                          </select>
                        </div>

                        <button
                          onClick={() => handleDeletePatch(patch.id)}
                          className="casper-icon-btn"
                          title="Bu yamayı kaldır"
                          style={{ padding: "5px 8px", color: "#64748b" }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "#080c14"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 12, color: "#94a3b8" }}>
              Toplam Seçili: <strong style={{ color: "#38bdf8" }}>{patches.filter(p => p.enabled).length} sahne</strong> (~{Math.round(totalPatchSeconds)} saniye)
            </span>
            <span style={{ fontSize: 11, color: "#64748b" }}>
              ⚡ Tahmini Montaj Süresi: ~5-15 sn
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button
              className="btn btn-ghost btn-sm"
              disabled={isPatching}
              onClick={onClose}
              style={{ fontSize: 12 }}
            >
              Kapat
            </button>

            <button
              className="btn btn-primary"
              disabled={isPatching || patches.filter(p => p.enabled).length === 0}
              onClick={handleApplyPatches}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 20px",
                fontWeight: 700,
                fontSize: 13,
                background: "linear-gradient(135deg, #0284c7 0%, #4f46e5 100%)",
                boxShadow: "0 4px 14px rgba(2, 132, 199, 0.35)"
              }}
            >
              {isPatching ? <RefreshCw size={15} className="spin" /> : <Scissors size={15} />}
              {isPatching ? "Yamalar Uygulanıyor (Kes & Birleştir)..." : "⚡ Yamayı Uygula & Videoyu Güncelle"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
