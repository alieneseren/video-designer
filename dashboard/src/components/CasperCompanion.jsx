import { useState, useEffect } from "react";
import { Heart, X, RefreshCw, Terminal, Check, Lightbulb, ChevronRight, ChevronLeft, ThumbsDown, Sparkles } from "lucide-react";
import "./Casper.css";

export default function CasperCompanion({ onOpenTerminal, savedCount, setSavedCount }) {
  const [ideas, setIdeas] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [deleteSuccess, setDeleteSuccess] = useState(false);

  const fetchPendingIdeas = async () => {
    try {
      const res = await fetch("/api/casper/pending");
      const data = await res.json();
      if (data.ideas) {
        setIdeas(data.ideas);
        if (data.saved_count !== undefined && setSavedCount) {
          setSavedCount(data.saved_count);
        }
      }
    } catch (err) {
      console.error("Casper bekleyen fikirler alınamadı:", err);
    }
  };

  useEffect(() => {
    fetchPendingIdeas();
    // 60 saniyede bir kontrol (sıfır CPU yükü)
    const interval = setInterval(fetchPendingIdeas, 60000);
    return () => clearInterval(interval);
  }, []);

  const currentIdea = ideas.length > 0 ? ideas[currentIndex % ideas.length] : null;

  const handleNext = () => {
    if (ideas.length <= 1) return;
    setCurrentIndex((prev) => (prev + 1) % ideas.length);
  };

  const handlePrev = () => {
    if (ideas.length <= 1) return;
    setCurrentIndex((prev) => (prev - 1 + ideas.length) % ideas.length);
  };

  const handleSave = async (id) => {
    if (!id) return;
    try {
      const res = await fetch(`/api/casper/ideas/${id}/save`, { method: "POST" });
      const data = await res.json();
      if (data.saved_count !== undefined && setSavedCount) {
        setSavedCount(data.saved_count);
      }
      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        // Beğenilen fikri pending listesinden çıkar ve sıradakine geç
        setIdeas((prev) => {
          const updated = prev.filter((item) => item.id !== id);
          if (currentIndex >= updated.length) {
            setCurrentIndex(Math.max(0, updated.length - 1));
          }
          return updated;
        });
      }, 900);
    } catch (err) {
      console.error("Fikir kaydedilemedi:", err);
    }
  };

  const handleDelete = async (id) => {
    if (!id) return;
    try {
      setDeleteSuccess(true);
      await fetch(`/api/casper/ideas/${id}`, { method: "DELETE" });
      setTimeout(() => {
        setDeleteSuccess(false);
        setIdeas((prev) => {
          const updated = prev.filter((item) => item.id !== id);
          if (currentIndex >= updated.length) {
            setCurrentIndex(Math.max(0, updated.length - 1));
          }
          return updated;
        });
      }, 400);
    } catch (err) {
      console.error("Fikir silinemedi:", err);
      setDeleteSuccess(false);
    }
  };

  const handleGenerate10New = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/casper/generate", { method: "POST" });
      const data = await res.json();
      if (data.ideas && data.ideas.length > 0) {
        setIdeas(data.ideas);
        setCurrentIndex(0);
      } else {
        await fetchPendingIdeas();
      }
    } catch (err) {
      console.error("Yeni fikirler üretilemedi:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="casper-float-container">
      {/* Konuşma Balonu (Speech Bubble) */}
      {isOpen && (
        <div className="casper-bubble">
          <div className="casper-bubble-header">
            <div className="casper-bubble-title">
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#38bdf8", display: "inline-block", boxShadow: "0 0 8px #38bdf8" }} />
              <Lightbulb size={14} style={{ color: "#38bdf8" }} />
              <span>Casper AI Danışmanı</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              {ideas.length > 0 && (
                <span className="casper-nav-pill">
                  {currentIndex + 1} / {ideas.length}
                </span>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="casper-icon-btn"
                style={{ padding: "4px 8px" }}
                title="Kapat"
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {loading ? (
            <div style={{ padding: "30px 10px", textAlign: "center", color: "#38bdf8", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <RefreshCw size={24} className="animate-spin" />
              <span style={{ fontSize: 12, fontWeight: 500, color: "#e2e8f0" }}>
                LM Studio & Graphify mimari analiziyle 10 yeni fikir üretiliyor...
              </span>
            </div>
          ) : currentIdea ? (
            <div className="casper-tip-content">
              <div className="casper-tip-heading">
                <h4>{currentIdea.title}</h4>
                <span className="casper-impact-tag">{currentIdea.impact}</span>
              </div>

              <p className="casper-tip-desc">
                {currentIdea.description}
              </p>

              {currentIdea.target_modules && (
                <div className="casper-tip-modules">
                  <span style={{ color: "#64748b" }}>Modüller: </span>
                  <span>{currentIdea.target_modules}</span>
                </div>
              )}

              {/* Aksiyon Butonları */}
              <div className="casper-tip-actions">
                {/* 1. Beğen / Hafızaya Al */}
                <button
                  onClick={() => handleSave(currentIdea.id)}
                  disabled={savedSuccess || deleteSuccess}
                  className={`casper-btn-save ${savedSuccess ? "saved" : ""}`}
                  title="Fikri hafızaya kaydet (Terminal ile uygulatılabilir)"
                >
                  {savedSuccess ? (
                    <>
                      <Check size={14} /> Hafızaya Alındı
                    </>
                  ) : (
                    <>
                      <Heart size={14} fill="currentColor" /> Fikri Beğen
                    </>
                  )}
                </button>

                {/* 2. Beğenme / Sil */}
                <button
                  onClick={() => handleDelete(currentIdea.id)}
                  disabled={savedSuccess || deleteSuccess}
                  className="casper-btn-dislike"
                  title="Fikri Beğenme (Listeden ve veritabanından sil)"
                >
                  <ThumbsDown size={13} />
                  <span>{deleteSuccess ? "Silindi" : "Beğenme"}</span>
                </button>

                {/* 3. Önceki & Sıradaki Gezinme */}
                <div className="casper-nav-group">
                  <button
                    onClick={handlePrev}
                    disabled={ideas.length <= 1}
                    className="casper-icon-btn"
                    title="Önceki Fikir"
                    style={{ opacity: ideas.length <= 1 ? 0.4 : 1 }}
                  >
                    <ChevronLeft size={16} />
                  </button>

                  <button
                    onClick={handleNext}
                    disabled={ideas.length <= 1}
                    className="casper-icon-btn"
                    title="Sıradaki Fikir"
                    style={{ opacity: ideas.length <= 1 ? 0.4 : 1 }}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>

              {/* 10 Yeni Fikir Üretme Çubuğu */}
              <button
                onClick={handleGenerate10New}
                disabled={loading}
                className="casper-btn-generate"
                title="LM Studio / Graphify üzerinden 10 yeni mimari fikir dalgası üret"
              >
                <Sparkles size={13} style={{ color: "#38bdf8" }} />
                <span>Yeni Fikir Dalgası Üret (10 Adet)</span>
              </button>
            </div>
          ) : (
            <div style={{ padding: "20px 0", textAlign: "center", fontSize: 12, color: "#94a3b8", display: "flex", flexDirection: "column", gap: 12 }}>
              <p style={{ margin: 0 }}>Şu anda beklemede fikir kalmadı.</p>
              <button
                onClick={handleGenerate10New}
                disabled={loading}
                className="casper-btn-generate"
              >
                <Sparkles size={13} style={{ color: "#38bdf8" }} />
                <span>10 Yeni Fikir Dalgası Üret</span>
              </button>
            </div>
          )}

          {/* Alt Kısım: Terminale Yönlendirme */}
          <div className="casper-bubble-footer">
            <span style={{ color: "#94a3b8" }}>
              Hafızada: <strong style={{ color: "#38bdf8" }}>{savedCount || 0}</strong> onaylı fikir
            </span>
            <button
              onClick={() => {
                setIsOpen(false);
                if (onOpenTerminal) onOpenTerminal();
              }}
              style={{
                background: "transparent",
                border: "none",
                color: "#38bdf8",
                fontSize: 11,
                fontWeight: 600,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                padding: "2px 6px"
              }}
            >
              <Terminal size={12} /> Terminali Aç & Uygula
            </button>
          </div>
        </div>
      )}

      {/* Casper Canlı Maskot Butonu */}
      <div className="casper-avatar-wrap">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="casper-avatar-btn"
          title="Casper AI Danışmanı"
        >
          {/* Casper Ghost / Ethereal SVG Avatar */}
          <svg
            style={{ width: 32, height: 32, color: "#ffffff", filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.4))" }}
            viewBox="0 0 24 24"
            fill="currentColor"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M12 2C7.58172 2 4 5.58172 4 10C4 13.5 4.5 17 6 19.5C6.5 20.3333 7.5 20.5 8 19.5C8.6 18.3 9.4 18 10 19.5C10.6 21 11.4 21 12 19.5C12.6 18 13.4 18.3 14 19.5C14.6 20.7 15.5 20.3 16 19.5C17.5 17 18 13.5 18 10C18 5.58172 14.4183 2 12 2Z" />
            <circle cx="9" cy="9.5" r="1.5" fill="#090b10" />
            <circle cx="15" cy="9.5" r="1.5" fill="#090b10" />
            <circle cx="9.5" cy="9" r="0.5" fill="#38bdf8" />
            <circle cx="15.5" cy="9" r="0.5" fill="#38bdf8" />
            <circle cx="7.5" cy="11.5" r="0.8" fill="#f43f5e" fillOpacity="0.75" />
            <circle cx="16.5" cy="11.5" r="0.8" fill="#f43f5e" fillOpacity="0.75" />
          </svg>

          {/* Rozet: Kaydedilen Fikir Sayısı */}
          {savedCount > 0 && (
            <span className="casper-badge">
              {savedCount}
            </span>
          )}
        </button>

        {/* Hover Fısıltı İpucu */}
        {!isOpen && (
          <div className="casper-hover-hint">
            {ideas.length > 0 ? `${ideas.length} yeni fikir seni bekliyor ✨` : "Casper'dan bir tavsiye var ✨"}
          </div>
        )}
      </div>
    </div>
  );
}
