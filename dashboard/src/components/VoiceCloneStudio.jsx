import React, { useState, useEffect, useRef } from "react";
import {
  Mic,
  Upload,
  Play,
  Pause,
  CheckCircle2,
  AlertCircle,
  Clock,
  Trash2,
  Sparkles,
  Zap,
  Volume2,
  RefreshCw,
  Sliders,
  FileAudio,
  Check
} from "lucide-react";

const PERSONA_PRESETS = [
  { id: "male", name: "👨 Yetişkin Erkek (Orijinal)", pitch: 0, formant: 1.0 },
  { id: "female", name: "👩 Yetişkin Kadın", pitch: 12, formant: 1.12 },
  { id: "boy", name: "👦 Erkek Çocuk (8-12 Yaş)", pitch: 14, formant: 1.20 },
  { id: "girl", name: "👧 Kız Çocuk (6-10 Yaş)", pitch: 17, formant: 1.25 },
  { id: "elder_male", name: "👴 Yaşlı Erkek (Dede)", pitch: -3, formant: 0.92 },
  { id: "elder_female", name: "👵 Yaşlı Kadın (Nine)", pitch: 8, formant: 1.06 },
];

export default function VoiceCloneStudio({ onVoiceActivated }) {
  const [clones, setClones] = useState([]);
  const [activeId, setActiveId] = useState("");
  const [device, setDevice] = useState("mps");
  const [loading, setLoading] = useState(true);

  // Form state
  const [voiceName, setVoiceName] = useState("");
  const [voiceDesc, setVoiceDesc] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Job / progress state
  const [currentJobId, setCurrentJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [liveDuration, setLiveDuration] = useState("00:00.0");
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  // Custom test synthesis state
  const [testCloneId, setTestCloneId] = useState(null);
  const [testText, setTestText] = useState("Bugün havacılık tarihinin en büyük gizemlerinden birini inceliyoruz.");
  const [testLang, setTestLang] = useState("auto");
  const [testPersona, setTestPersona] = useState("male");
  const [testingAudio, setTestingAudio] = useState(false);
  const [testAudioUrl, setTestAudioUrl] = useState(null);

  // Fetch existing voice clones
  const fetchClones = async () => {
    try {
      const res = await fetch("/api/voice-clones");
      if (res.ok) {
        const data = await res.json();
        setClones(data.clones || []);
        setActiveId(data.active_id || "");
        setDevice(data.device || "mps");
      }
    } catch (err) {
      console.error("Ses klonları alınamadı:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClones();
  }, []);

  // Live timer while processing
  useEffect(() => {
    if (jobStatus && (jobStatus.status === "processing" || jobStatus.status === "queued")) {
      if (!startTimeRef.current) {
        startTimeRef.current = Date.now();
      }
      timerRef.current = setInterval(() => {
        const diffMs = Date.now() - startTimeRef.current;
        const totalSec = diffMs / 1000;
        const mins = Math.floor(totalSec / 60);
        const secs = (totalSec % 60).toFixed(1);
        setLiveDuration(
          `${mins.toString().padStart(2, "0")}:${secs.padStart(4, "0")}`
        );
      }, 100);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      startTimeRef.current = null;
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [jobStatus]);

  // Poll job status
  useEffect(() => {
    if (!currentJobId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/voice-clones/jobs/${currentJobId}`);
        if (res.ok) {
          const data = await res.json();
          setJobStatus(data);
          if (data.status === "completed" || data.status === "failed") {
            clearInterval(interval);
            fetchClones();
            if (onVoiceActivated && data.result?.id) {
              onVoiceActivated(data.result.id);
            }
          }
        }
      } catch (err) {
        console.error("İş durumu sorgulama hatası:", err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [currentJobId]);

  // Handle start clone
  const handleStartClone = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      alert("Lütfen önce bir ses dosyası (.wav, .mp3, .m4a) seçin.");
      return;
    }
    if (!voiceName.trim()) {
      alert("Lütfen klonlanacak ses profiline bir isim verin.");
      return;
    }

    setUploading(true);
    setJobStatus({ status: "processing", progress: 10, current_stage: "Ses dosyası yükleniyor..." });

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const upRes = await fetch("/api/voice-clones/upload", {
        method: "POST",
        body: formData,
      });

      if (!upRes.ok) {
        const errJson = await upRes.json();
        throw new Error(errJson.detail || "Ses yüklenemedi");
      }

      const upData = await upRes.json();
      setJobStatus({ status: "processing", progress: 20, current_stage: "Klonlama işlemi başlatılıyor..." });

      const startRes = await fetch("/api/voice-clones/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: voiceName.trim(),
          temp_path: upData.temp_path,
          description: voiceDesc.trim(),
        }),
      });

      if (!startRes.ok) {
        const errJson = await startRes.json();
        throw new Error(errJson.detail || "Klonlama başlatılamadı");
      }

      const startData = await startRes.json();
      setCurrentJobId(startData.job_id);
    } catch (err) {
      alert("Hata: " + err.message);
      setJobStatus({ status: "failed", current_stage: "Hata: " + err.message });
    } finally {
      setUploading(false);
    }
  };

  // Handle activate
  const handleActivate = async (cloneId) => {
    try {
      const res = await fetch(`/api/voice-clones/${cloneId}/activate`, {
        method: "POST",
      });
      if (res.ok) {
        setActiveId(cloneId);
        fetchClones();
        if (onVoiceActivated) onVoiceActivated(cloneId);
      }
    } catch (err) {
      console.error("Ses aktif edilemedi:", err);
    }
  };

  // Handle delete
  const handleDelete = async (cloneId, name) => {
    if (!window.confirm(`"${name}" ses profilini silmek istediğinize emin misiniz?`)) return;
    try {
      const res = await fetch(`/api/voice-clones/${cloneId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        fetchClones();
      }
    } catch (err) {
      console.error("Ses silinemedi:", err);
    }
  };

  // Handle custom test synthesis
  const handleRunTest = async (cloneId) => {
    if (!testText.trim()) return;
    setTestingAudio(true);
    setTestAudioUrl(null);

    const activePersona = PERSONA_PRESETS.find((p) => p.id === testPersona) || PERSONA_PRESETS[0];

    try {
      const res = await fetch(`/api/voice-clones/${cloneId}/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: testText.trim(),
          lang: testLang,
          pitch: activePersona.pitch,
          formant: activePersona.formant,
        }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        setTestAudioUrl(url);
      } else {
        alert("Test sesi sentezlenemedi.");
      }
    } catch (err) {
      console.error("Test hatası:", err);
      alert("Hata: " + err.message);
    } finally {
      setTestingAudio(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {/* ── Header Card ────────────────────────── */}
      <div
        className="card"
        style={{
          padding: "22px 24px",
          background: "linear-gradient(135deg, rgba(168, 85, 247, 0.08) 0%, rgba(59, 130, 246, 0.05) 100%)",
          border: "1px solid rgba(168, 85, 247, 0.25)",
          borderRadius: "var(--radius-lg, 12px)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  background: "linear-gradient(135deg, #a855f7 0%, #6366f1 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#fff",
                }}
              >
                <Mic size={18} />
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                Gerçekçi Yerel Ses Klonlama Stüdyosu
              </h3>
            </div>
            <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 6, marginBottom: 0, maxWidth: 650, lineHeight: 1.5 }}>
              Kendi sesinizi (5–10 saniyelik temiz bir ses kaydı) sisteme verin. Yerel yapay zeka sinir ağı sesinizin tınısını, tonlamasını ve speaker embedding'ini çıkarıp <strong>tüm video ve YouTube projelerinizde kullanılabilir</strong> hale getirir.
            </p>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span
              className="chip chip-accent"
              style={{
                fontSize: 11,
                padding: "4px 10px",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                background: "rgba(168, 85, 247, 0.15)",
                color: "#c084fc",
                border: "1px solid rgba(168, 85, 247, 0.3)",
              }}
            >
              <Zap size={12} />
              {device === "mps" ? "Apple M4 (MPS Hızlandırılmış)" : "Yerel AI Motoru"}
            </span>
            <span
              className="chip chip-success"
              style={{
                fontSize: 11,
                padding: "4px 10px",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              <CheckCircle2 size={12} />
              Sıfır API Maliyeti
            </span>
          </div>
        </div>
      </div>

      {/* ── Create / Clone Card ────────────────── */}
      <div className="card" style={{ padding: "20px 22px" }}>
        <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text-primary)", marginBottom: 14 }}>
          🎙️ Yeni Ses Klonu Oluştur
        </div>

        <form onSubmit={handleStartClone}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
            <div className="form-group">
              <label className="form-label" style={{ fontSize: 12, fontWeight: 500 }}>
                Ses Profili Adı *
              </label>
              <input
                type="text"
                className="form-input"
                placeholder="Örn: Ali Enes — Orijinal Sesim"
                value={voiceName}
                onChange={(e) => setVoiceName(e.target.value)}
                disabled={uploading || (jobStatus && jobStatus.status === "processing")}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontSize: 12, fontWeight: 500 }}>
                Açıklama / Ton (Opsiyonel)
              </label>
              <input
                type="text"
                className="form-input"
                placeholder="Örn: Belgesel ve hikaye anlatımları için tok ton"
                value={voiceDesc}
                onChange={(e) => setVoiceDesc(e.target.value)}
                disabled={uploading || (jobStatus && jobStatus.status === "processing")}
              />
            </div>
          </div>

          {/* File Dropzone */}
          <div
            style={{
              border: "2px dashed var(--border-subtle, rgba(255,255,255,0.15))",
              borderRadius: "var(--radius-md, 8px)",
              padding: "20px 16px",
              textAlign: "center",
              background: selectedFile ? "rgba(59, 130, 246, 0.04)" : "var(--bg-primary)",
              cursor: "pointer",
              transition: "all 0.15s ease",
              marginBottom: 16,
            }}
            onClick={() => document.getElementById("voice-file-input").click()}
          >
            <input
              id="voice-file-input"
              type="file"
              accept=".wav,.mp3,.m4a,.flac,.ogg"
              style={{ display: "none" }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                  if (!voiceName) {
                    const clean = e.target.files[0].name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
                    setVoiceName(clean.charAt(0).toUpperCase() + clean.slice(1));
                  }
                }
              }}
            />

            {selectedFile ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
                <FileAudio size={24} color="#3b82f6" />
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                    {selectedFile.name}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    {(selectedFile.size / 1024).toFixed(1)} KB · Değiştirmek için tıklayın
                  </div>
                </div>
              </div>
            ) : (
              <div>
                <Upload size={24} style={{ margin: "0 auto 8px", color: "var(--text-muted)" }} />
                <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                  Ses Örneği Yükleyin veya Sürükleyin
                </div>
                <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 4 }}>
                  5–15 saniyelik temiz bir konuşma kaydı (.wav, .mp3, .m4a) yeterlidir.
                </div>
              </div>
            )}
          </div>

          {/* Action Button */}
          <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 12 }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!selectedFile || !voiceName.trim() || uploading || (jobStatus && jobStatus.status === "processing")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "9px 18px",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              <Sparkles size={15} />
              {jobStatus && jobStatus.status === "processing" ? "Klonlanıyor..." : "Sesi Yerelde Klonla ve Profili Eğit"}
            </button>
          </div>
        </form>

        {/* ── Active Cloning Live Progress & Timer ── */}
        {jobStatus && (
          <div
            style={{
              marginTop: 18,
              padding: "16px 18px",
              borderRadius: "var(--radius-md, 8px)",
              background:
                jobStatus.status === "completed"
                  ? "rgba(34, 197, 94, 0.08)"
                  : jobStatus.status === "failed"
                  ? "rgba(239, 68, 68, 0.08)"
                  : "rgba(59, 130, 246, 0.08)",
              border: `1px solid ${
                jobStatus.status === "completed"
                  ? "rgba(34, 197, 94, 0.3)"
                  : jobStatus.status === "failed"
                  ? "rgba(239, 68, 68, 0.3)"
                  : "rgba(59, 130, 246, 0.3)"
              }`,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {jobStatus.status === "processing" && (
                  <span
                    style={{
                      display: "inline-block",
                      width: 9,
                      height: 9,
                      borderRadius: "50%",
                      background: "#3b82f6",
                      boxShadow: "0 0 8px #3b82f6",
                      animation: "pulse 1.2s infinite",
                    }}
                  />
                )}
                {jobStatus.status === "completed" && <CheckCircle2 size={16} color="#22c55e" />}
                {jobStatus.status === "failed" && <AlertCircle size={16} color="#ef4444" />}
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                  {jobStatus.current_stage || "İşleniyor..."}
                </span>
              </div>

              {/* Exact duration indicator */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12,
                  fontWeight: 600,
                  color: jobStatus.status === "completed" ? "#22c55e" : "var(--text-primary)",
                  background: "var(--bg-primary)",
                  padding: "3px 10px",
                  borderRadius: 6,
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <Clock size={12} />
                {jobStatus.status === "completed"
                  ? `Toplam Süre: ${jobStatus.total_duration || jobStatus.elapsed_seconds} sn`
                  : `Geçen Süre: ${liveDuration}`}
              </div>
            </div>

            {/* Progress bar */}
            <div
              style={{
                width: "100%",
                height: 6,
                background: "rgba(255, 255, 255, 0.1)",
                borderRadius: 3,
                overflow: "hidden",
                marginTop: 8,
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${jobStatus.progress || 0}%`,
                  background:
                    jobStatus.status === "completed"
                      ? "linear-gradient(90deg, #22c55e, #10b981)"
                      : jobStatus.status === "failed"
                      ? "#ef4444"
                      : "linear-gradient(90deg, #6366f1, #a855f7)",
                  transition: "width 0.4s ease",
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Cloned Voices Library ────────────────── */}
      <div className="card" style={{ padding: "20px 22px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text-primary)" }}>
              📚 Kayıtlı Klon Sesler Kütüphanesi ({clones.length})
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 2 }}>
              Aşağıdaki seslerden birini <strong>Aktif Ses Yap</strong> butonuna basarak tüm YouTube üretimlerinde varsayılan ses olarak belirleyebilirsiniz.
            </div>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={fetchClones}
            style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12 }}
          >
            <RefreshCw size={12} />
            Yenile
          </button>
        </div>

        {loading ? (
          <div style={{ padding: "24px 0", textAlign: "center", color: "var(--text-muted)", fontSize: 12.5 }}>
            Ses profilleri yükleniyor…
          </div>
        ) : clones.length === 0 ? (
          <div
            style={{
              padding: "32px 16px",
              textAlign: "center",
              background: "var(--bg-primary)",
              borderRadius: "var(--radius-md, 8px)",
              border: "1px dashed var(--border-subtle)",
            }}
          >
            <Mic size={28} style={{ color: "var(--text-muted)", margin: "0 auto 8px" }} />
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              Henüz klonlanmış bir sesiniz yok
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
              Yukarıdaki formdan 5–10 saniyelik bir ses kaydınızı yükleyerek ilk klon sesinizi saniyeler içinde oluşturun.
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {clones.map((c) => (
              <div
                key={c.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  padding: "14px 16px",
                  borderRadius: "var(--radius-md, 8px)",
                  background: c.is_active ? "rgba(34, 197, 94, 0.05)" : "var(--bg-primary)",
                  border: `1px solid ${c.is_active ? "rgba(34, 197, 94, 0.35)" : "var(--border-subtle)"}`,
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div
                      style={{
                        width: 34,
                        height: 34,
                        borderRadius: "50%",
                        background: c.is_active ? "#22c55e" : "var(--accent-muted, #3b82f6)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                      }}
                    >
                      <Volume2 size={16} />
                    </div>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)" }}>
                          {c.name}
                        </span>
                        {c.is_active && (
                          <span
                            className="chip chip-success"
                            style={{
                              fontSize: 10,
                              padding: "2px 8px",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4,
                            }}
                          >
                            <Check size={10} />
                            Aktif Ses (Projelerde Kullanılıyor)
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                        {c.description || "Özel Ses Profili"} · {c.created_at}
                      </div>
                    </div>
                  </div>

                  {/* Metadata Chips */}
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {c.processing_time_sec && (
                      <span
                        className="chip"
                        style={{
                          fontSize: 10.5,
                          fontFamily: "'JetBrains Mono', monospace",
                          background: "var(--bg-secondary, rgba(255,255,255,0.05))",
                          border: "1px solid var(--border-subtle)",
                        }}
                      >
                        ⚡ Klon Süresi: {c.processing_time_sec} sn
                      </span>
                    )}
                    {c.audio_duration_sec && (
                      <span
                        className="chip"
                        style={{
                          fontSize: 10.5,
                          background: "var(--bg-secondary, rgba(255,255,255,0.05))",
                          border: "1px solid var(--border-subtle)",
                        }}
                      >
                        ⏱️ Örnek: {c.audio_duration_sec} sn
                      </span>
                    )}
                  </div>
                </div>

                {/* Audio preview player & actions */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10, marginTop: 4 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 260 }}>
                    <span style={{ fontSize: 11, color: "var(--text-muted)", whiteSpace: "nowrap" }}>Örnek Ses:</span>
                    <audio
                      controls
                      src={`/api/voice-clones/${c.id}/preview`}
                      style={{ height: 32, width: "100%", maxWidth: 380 }}
                    />
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <button
                      type="button"
                      className="btn btn-sm btn-ghost"
                      onClick={() => {
                        setTestCloneId(testCloneId === c.id ? null : c.id);
                        setTestAudioUrl(null);
                      }}
                      style={{ fontSize: 11.5, display: "inline-flex", alignItems: "center", gap: 5 }}
                    >
                      <Sliders size={12} />
                      {testCloneId === c.id ? "Testi Kapat" : "Cümle Test Et"}
                    </button>

                    {!c.is_active ? (
                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => handleActivate(c.id)}
                        style={{ fontSize: 11.5, display: "inline-flex", alignItems: "center", gap: 5 }}
                      >
                        <CheckCircle2 size={12} />
                        Aktif Ses Yap
                      </button>
                    ) : (
                      <span style={{ fontSize: 11.5, color: "#22c55e", fontWeight: 600, padding: "4px 8px" }}>
                        ✓ Seçildi
                      </span>
                    )}

                    <button
                      type="button"
                      className="btn btn-sm btn-ghost"
                      onClick={() => handleDelete(c.id, c.name)}
                      style={{ color: "#ef4444", padding: 6 }}
                      title="Profili Sil"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Inline Custom Sentence Test Box */}
                {testCloneId === c.id && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: "12px 14px",
                      borderRadius: 6,
                      background: "var(--bg-secondary, rgba(0,0,0,0.2))",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                      🎙️ Özel Cümle Testi — {c.name}
                    </div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <select
                        value={testLang}
                        onChange={(e) => setTestLang(e.target.value)}
                        className="form-input"
                        style={{ width: 125, fontSize: 11.5, padding: "6px 8px", background: "rgba(15, 23, 42, 0.6)" }}
                        disabled={testingAudio}
                      >
                        <option value="auto">🌐 Otomatik</option>
                        <option value="tr">🇹🇷 Türkçe</option>
                        <option value="en">🇬🇧 İngilizce</option>
                        <option value="de">🇩🇪 Almanca</option>
                        <option value="fr">🇫🇷 Fransızca</option>
                        <option value="es">🇪🇸 İspanyolca</option>
                        <option value="it">🇮🇹 İtalyanca</option>
                        <option value="ru">🇷🇺 Rusça</option>
                        <option value="ar">🇸🇦 Arapça</option>
                        <option value="ja">🇯🇵 Japonca</option>
                      </select>
                      <select
                        value={testPersona}
                        onChange={(e) => setTestPersona(e.target.value)}
                        className="form-input"
                        style={{ width: 175, fontSize: 11.5, padding: "6px 8px", background: "rgba(15, 23, 42, 0.6)" }}
                        disabled={testingAudio}
                        title="Karakter, yaş ve cinsiyet tonlaması"
                      >
                        {PERSONA_PRESETS.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                      </select>
                      <input
                        type="text"
                        className="form-input"
                        style={{ flex: 1, fontSize: 12, padding: "6px 10px" }}
                        value={testText}
                        onChange={(e) => setTestText(e.target.value)}
                        placeholder="Klonlanan sesin okumasını istediğiniz cümleyi yazın..."
                        disabled={testingAudio}
                      />
                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => handleRunTest(c.id)}
                        disabled={testingAudio || !testText.trim()}
                        style={{ whiteSpace: "nowrap", fontSize: 11.5 }}
                      >
                        {testingAudio ? "Sentezleniyor..." : "Konuştur / Dinle"}
                      </button>
                    </div>

                    {testAudioUrl && (
                      <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 11, color: "#22c55e", fontWeight: 600 }}>Test Çıktısı:</span>
                        <audio controls autoPlay src={testAudioUrl} style={{ height: 30, width: "100%", maxWidth: 360 }} />
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
