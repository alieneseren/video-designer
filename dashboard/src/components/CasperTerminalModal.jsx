import { useState, useEffect, useRef } from "react";
import { Terminal, X, Play, Square, Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import "./Casper.css";

export default function CasperTerminalModal({ isOpen, onClose, onIdeaApplied }) {
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [savedIdeas, setSavedIdeas] = useState([]);
  const [copied, setCopied] = useState(false);
  const [showPromptPreview, setShowPromptPreview] = useState(false);
  const [promptPayload, setPromptPayload] = useState(null);
  const logsEndRef = useRef(null);

  // Fikirleri ve payload'ı yükle
  const loadPayload = async () => {
    try {
      const res = await fetch("/api/casper/apply-payload");
      const data = await res.json();
      setPromptPayload(data);
      setSavedIdeas(data.ideas || []);
    } catch (err) {
      console.error("Payload yüklenemedi:", err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      loadPayload();
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Terminal loglarını canlı dinle
  useEffect(() => {
    let interval = null;
    if (isOpen) {
      const fetchLogs = async () => {
        try {
          const res = await fetch("/api/casper/terminal/status");
          const data = await res.json();
          setIsRunning(data.is_running);
          if (data.logs && data.logs.length > 0) {
            setLogs(data.logs);
          }
        } catch (err) {
          console.error("Terminal logları alınamadı:", err);
        }
      };

      fetchLogs();
      interval = setInterval(fetchLogs, 1200);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isOpen, isRunning]);

  // Otomatik aşağı kaydır
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  // ESC tuşu ile kapatma
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen && !isRunning) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isRunning, onClose]);

  const handleStartApply = async () => {
    try {
      setLogs(["$ agy --dangerously-skip-permissions -p [Casper Direktifleri]", "[CASPER TERMINAL] Oturum başlatılıyor..."]);
      setIsRunning(true);
      const res = await fetch("/api/casper/terminal/start", { method: "POST" });
      const data = await res.json();
      if (data.status === "started") {
        if (onIdeaApplied) onIdeaApplied();
      }
    } catch (err) {
      console.error("Uygulama başlatılamadı:", err);
      setIsRunning(false);
    }
  };

  const handleStop = async () => {
    try {
      await fetch("/api/casper/terminal/stop", { method: "POST" });
      setIsRunning(false);
    } catch (err) {
      console.error("Oturum durdurulamadı:", err);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(logs.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (!isOpen) return null;

  return (
    <div
      className="casper-terminal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isRunning) {
          onClose();
        }
      }}
    >
      <div className="casper-terminal-window">
        {/* Terminal Header */}
        <div className="casper-term-header">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div className="casper-term-traffic">
              <span className="casper-traffic-dot red" />
              <span className="casper-traffic-dot yellow" />
              <span className="casper-traffic-dot green" />
            </div>
            <div className="casper-term-title">
              <Terminal size={15} style={{ color: "#38bdf8" }} />
              <span>Casper AI Danışman Terminali</span>
              <span style={{ color: "#64748b", fontSize: 11, fontWeight: 400 }}>
                (Gemini Otonom Motoru)
              </span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {isRunning && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "3px 10px",
                  borderRadius: 20,
                  background: "rgba(6, 182, 212, 0.15)",
                  border: "1px solid rgba(6, 182, 212, 0.4)",
                  color: "#38bdf8",
                  fontSize: 11,
                  fontFamily: "'JetBrains Mono', monospace"
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#38bdf8", animation: "pulse-dot 1.5s infinite" }} />
                Gemini Çalışıyor
              </span>
            )}
            <button
              onClick={onClose}
              className="casper-icon-btn"
              style={{ padding: "5px 8px" }}
              title="Kapat (Esc)"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Aksiyon Barı & Fikir Sayısı */}
        <div className="casper-term-toolbar">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ color: "#94a3b8", fontSize: 12 }}>Uygulanacak Onaylı Fikirler:</span>
            <span className="casper-pill-badge">
              {savedIdeas.length} Adet
            </span>
            <button
              onClick={() => setShowPromptPreview(!showPromptPreview)}
              style={{
                background: "transparent",
                border: "none",
                color: "#38bdf8",
                fontSize: 11.5,
                cursor: "pointer",
                textDecoration: "underline",
                display: "inline-flex",
                alignItems: "center",
                gap: 4
              }}
            >
              {showPromptPreview ? "Detayları Gizle" : "İletilecek Komutu Gör"}
              {showPromptPreview ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {isRunning ? (
              <button onClick={handleStop} className="casper-btn-stop">
                <Square size={13} fill="currentColor" /> Durdur
              </button>
            ) : (
              <button
                onClick={handleStartApply}
                disabled={savedIdeas.length === 0}
                className="casper-btn-run"
                title={savedIdeas.length === 0 ? "Önce Casper maskotundan en az 1 fikir beğenin" : "Gemini oturumuna komut gönder"}
              >
                <Play size={13} fill="currentColor" /> Gemini'ye Gönder & Uygulat
              </button>
            )}

            <button
              onClick={copyToClipboard}
              className="casper-icon-btn"
              title="Terminal Loglarını Kopyala"
            >
              {copied ? <Check size={14} style={{ color: "#34d399" }} /> : <Copy size={14} />}
            </button>
          </div>
        </div>

        {/* Prompt Önizleme Çekmecesi */}
        {showPromptPreview && promptPayload && (
          <div className="casper-term-prompt-preview">
            <div style={{ color: "#38bdf8", fontWeight: 600, marginBottom: 6 }}>
              $ {promptPayload.command}
            </div>
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                fontSize: 11,
                lineHeight: 1.5,
                color: "#94a3b8",
                background: "rgba(0, 0, 0, 0.4)",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid rgba(255, 255, 255, 0.08)"
              }}
            >
              {promptPayload.prompt}
            </pre>
          </div>
        )}

        {/* Canlı Terminal Ekranı */}
        <div className="casper-term-body">
          {logs.length === 0 ? (
            <div style={{ padding: "80px 20px", textAlign: "center", color: "#64748b" }}>
              <Terminal size={38} style={{ margin: "0 auto 12px", color: "#334155" }} />
              <p style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 500, color: "#94a3b8" }}>
                Terminal hazır ve beklemede.
              </p>
              <p style={{ margin: 0, fontSize: 11.5, color: "#64748b" }}>
                Yukarıdaki "Gemini'ye Gönder & Uygulat" butonuna basarak, seçtiğiniz mimari iyileştirmeleri doğrudan aktif Gemini oturumuna uygulayabilirsiniz.
              </p>
            </div>
          ) : (
            logs.map((line, idx) => (
              <div
                key={idx}
                className="casper-term-line"
                style={{
                  color: line.startsWith("$")
                    ? "#38bdf8"
                    : line.includes("✅")
                    ? "#34d399"
                    : line.includes("❌")
                    ? "#fb7185"
                    : line.includes("⚠️")
                    ? "#fbbf24"
                    : line.includes("[CASPER")
                    ? "#a5b4fc"
                    : "#cbd5e1"
                }}
              >
                {line}
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>

        {/* Terminal Footer */}
        <div className="casper-term-footer">
          <span>Oturum: b918ee66-9d53-472c-8ab2-0a10132b0a6f</span>
          <span>{isRunning ? "Canlı Log Akışı Aktif..." : "Oturum Hazır (0% CPU Yükü)"}</span>
        </div>
      </div>
    </div>
  );
}
