import { useState, useEffect, useCallback } from "react";
import {
  BookOpen,
  Plus,
  Sparkles,
  Edit3,
  Trash2,
  Play,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight,
  ExternalLink,
  Loader2,
  Film,
  Zap,
  Info
} from "lucide-react";

export default function StoryStudio({ channel }) {
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingStory, setEditingStory] = useState(null);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [producingStoryId, setProducingStoryId] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState(null);

  // Form State
  const [formTitle, setFormTitle] = useState("");
  const [formGenre, setFormGenre] = useState("sci_fi_mystery");
  const [formLang, setFormLang] = useState(channel?.language || "tr");
  const [formRawText, setFormRawText] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const channelId = channel?.channel_id;

  const fetchStories = useCallback(async () => {
    if (!channelId) return;
    try {
      setLoading(true);
      const res = await fetch(`/api/stories?channel_id=${channelId}`);
      if (res.ok) {
        const data = await res.json();
        setStories(data.stories || []);
      }
    } catch (err) {
      console.error("Hikayeler yüklenemedi:", err);
    } finally {
      setLoading(false);
    }
  }, [channelId]);

  useEffect(() => {
    fetchStories();
  }, [fetchStories]);

  const handleOpenNewModal = () => {
    setEditingStory(null);
    setFormTitle("");
    setFormGenre("sci_fi_mystery");
    setFormLang(channel?.language || "tr");
    setFormRawText("");
    setFormNotes("");
    setShowModal(true);
  };

  const handleOpenEditModal = (story) => {
    setEditingStory(story);
    setFormTitle(story.title || "");
    setFormGenre(story.genre || "sci_fi_mystery");
    setFormLang(story.target_language || channel?.language || "tr");
    setFormRawText(story.raw_text || "");
    setFormNotes(story.plot_notes || "");
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!formTitle.trim()) {
      alert("Lütfen bir hikaye başlığı girin.");
      return;
    }
    setSaving(true);
    try {
      if (editingStory) {
        // Güncelle
        const res = await fetch(`/api/stories/${editingStory.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: formTitle.trim(),
            genre: formGenre,
            target_language: formLang,
            raw_text: formRawText.trim(),
            plot_notes: formNotes.trim(),
          }),
        });
        if (res.ok) {
          setFeedbackMsg("✓ Hikaye taslağı başarıyla güncellendi.");
          setShowModal(false);
          fetchStories();
        }
      } else {
        // Yeni Oluştur
        const res = await fetch("/api/stories", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            channel_id: channelId,
            title: formTitle.trim(),
            genre: formGenre,
            target_language: formLang,
            raw_text: formRawText.trim(),
            plot_notes: formNotes.trim(),
          }),
        });
        if (res.ok) {
          setFeedbackMsg("✓ Yeni hikaye taslağı kaydedildi.");
          setShowModal(false);
          fetchStories();
        }
      }
    } catch (err) {
      alert("Kaydetme sırasında hata: " + err.message);
    } finally {
      setSaving(false);
      setTimeout(() => setFeedbackMsg(null), 4000);
    }
  };

  const handleDelete = async (storyId) => {
    if (!confirm("Bu hikaye taslağını silmek istediğinize emin misiniz?")) return;
    try {
      const res = await fetch(`/api/stories/${storyId}`, { method: "DELETE" });
      if (res.ok) {
        setFeedbackMsg("Hikaye taslağı silindi.");
        fetchStories();
      }
    } catch (err) {
      alert("Silme hatası: " + err.message);
    }
  };

  const handleConvertToMaterial = async (storyId) => {
    setActionLoadingId(storyId);
    try {
      const res = await fetch(`/api/stories/${storyId}/convert-to-material`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        const totalP = data.data?.total_parts || 1;
        setFeedbackMsg(`✓ Başarılı! Hikaye ${totalP} bölüm (Part 1, Part 2...) halinde 'Üretim Metaryalleri'ne dönüştürüldü.`);
        fetchStories();
      } else {
        const errData = await res.json();
        alert("Dönüştürme hatası: " + (errData.detail || "Bilinmeyen hata"));
      }
    } catch (err) {
      alert("Hata: " + err.message);
    } finally {
      setActionLoadingId(null);
      setTimeout(() => setFeedbackMsg(null), 5000);
    }
  };

  const handleProduceAnimation = async (storyId, title) => {
    if (!confirm(`'${title}' hikayesi için Aurora kod çizimli prosedürel animasyon üretimini başlatmak istiyor musunuz?`)) return;
    setProducingStoryId(storyId);
    try {
      const res = await fetch(`/api/stories/${storyId}/produce`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        setFeedbackMsg(`🎬 '${title}' animasyon üretimi arka planda başlatıldı! (İşlem ID: ${data.exec_id})`);
      } else {
        const errData = await res.json();
        alert("Üretim hatası: " + (errData.detail || "Hata oluştu"));
      }
    } catch (err) {
      alert("Hata: " + err.message);
    } finally {
      setTimeout(() => setProducingStoryId(null), 2500);
      setTimeout(() => setFeedbackMsg(null), 6000);
    }
  };

  const getGenreLabel = (g) => {
    const map = {
      sci_fi_mystery: "🚀 Uzay & Bilimkurgu",
      dark_mystery: "🌑 Karanlık Gizem & Gerilim",
      ancient_myth: "🏛️ Kadim Efsane & Mitoloji",
      fantasy_fable: "🧚 Fantastik Masal",
      psychological: "🧠 Psikolojik & Dram",
    };
    return map[g] || "📖 Hikaye";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Üst Bilgi Kartı & Ekleme Butonu */}
      <div
        className="card"
        style={{
          padding: "20px 22px",
          background: "linear-gradient(135deg, rgba(245, 158, 11, 0.05), rgba(236, 72, 153, 0.05))",
          border: "1px solid rgba(245, 158, 11, 0.2)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: "linear-gradient(135deg, #f59e0b, #ec4899)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              boxShadow: "0 4px 12px rgba(245, 158, 11, 0.3)",
            }}
          >
            <BookOpen size={22} />
          </div>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
              📖 Hikaye & Masal Atölyesi
              <span className="chip chip-accent" style={{ fontSize: 11, background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b", border: "1px solid rgba(245, 158, 11, 0.3)" }}>
                Aurora Animasyon Motoru
              </span>
            </h3>
            <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: "4px 0 0 0", lineHeight: 1.4 }}>
              Kendi hikaye taslaklarınızı yazın, Gemini ile geliştirin ve Instagram/Shorts uyumlu prosedürel dikey animasyonlara dönüştürün.
            </p>
          </div>
        </div>

        <button
          className="btn"
          onClick={handleOpenNewModal}
          style={{
            background: "linear-gradient(135deg, #f59e0b, #ec4899)",
            color: "#fff",
            border: "none",
            padding: "9px 18px",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: 7,
            boxShadow: "0 4px 14px rgba(245, 158, 11, 0.25)",
            transition: "transform 0.15s ease",
          }}
        >
          <Plus size={16} /> Yeni Hikaye Ekle
        </button>
      </div>

      {/* Bildirim Çubuğu */}
      {feedbackMsg && (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: 8,
            background: "rgba(16, 185, 129, 0.12)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            color: "#34d399",
            fontSize: 12.5,
            fontWeight: 500,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <CheckCircle2 size={16} />
          {feedbackMsg}
        </div>
      )}

      {/* Gemini Eklentisi Entegrasyon İpucu */}
      <div
        style={{
          padding: "12px 16px",
          borderRadius: 10,
          background: "rgba(56, 189, 248, 0.06)",
          border: "1px solid rgba(56, 189, 248, 0.2)",
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
          fontSize: 12,
          lineHeight: 1.45,
          color: "#94a3b8",
        }}
      >
        <Sparkles size={18} style={{ color: "#38bdf8", flexShrink: 0, marginTop: 2 }} />
        <div>
          <strong style={{ color: "#38bdf8" }}>💡 Gemini İçerik Planlayıcı Entegrasyonu:</strong> Buraya kaydettiğiniz taslaklar, Chrome eklentisindeki{" "}
          <strong style={{ color: "#f8fafc" }}>"📖 Hikaye Geliştir"</strong> sekmesinde otomatik listelenir. Gemini'a soru-cevap yaptırabilir veya tek tıkla{" "}
          <strong style={{ color: "#f8fafc" }}>Part 1, Part 2</strong> dikey Shorts senaryosuna dönüştürüp doğrudan Üretim Materyallerine kaydedebilirsiniz.
        </div>
      </div>

      {/* Hikaye Taslakları Listesi */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)", fontSize: 13 }}>
          <Loader2 className="spinner" size={24} style={{ margin: "0 auto 8px" }} />
          Hikaye taslakları yükleniyor...
        </div>
      ) : stories.length === 0 ? (
        <div
          className="card"
          style={{
            padding: "36px 20px",
            textAlign: "center",
            color: "var(--text-muted)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
          }}
        >
          <BookOpen size={36} style={{ opacity: 0.35, color: "#f59e0b" }} />
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>Henüz Kayıtlı Hikaye Taslağı Yok</div>
          <div style={{ fontSize: 12.5, maxWidth: 440, lineHeight: 1.4 }}>
            Bu kanal için henüz bir hikaye taslağı oluşturulmamış. "Yeni Hikaye Ekle" butonuna tıklayarak kendi taslağınızı yazabilir veya düzenleyebilirsiniz.
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleOpenNewModal}
            style={{ marginTop: 6 }}
          >
            <Plus size={14} /> İlk Hikayeyi Ekle
          </button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 14 }}>
          {stories.map((story) => {
            const isConverted = story.status === "converted";
            const isDeveloped = story.status === "developed" || isConverted;
            const parts = story.developed_story?.parts || [];
            const partCount = parts.length;
            const hook = story.developed_story?.hook || "";

            return (
              <div
                key={story.id}
                className="card"
                style={{
                  padding: "16px 18px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gap: 12,
                  border: isConverted
                    ? "1px solid rgba(16, 185, 129, 0.3)"
                    : isDeveloped
                    ? "1px solid rgba(245, 158, 11, 0.3)"
                    : "1px solid var(--border-subtle)",
                  background: isConverted
                    ? "rgba(16, 185, 129, 0.02)"
                    : "var(--surface-card)",
                }}
              >
                {/* Kart Üst Bilgisi */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.3 }}>
                      {story.title}
                    </div>
                    <span
                      className="chip"
                      style={{
                        fontSize: 10.5,
                        fontWeight: 600,
                        padding: "2px 8px",
                        borderRadius: 12,
                        background: isConverted
                          ? "rgba(16, 185, 129, 0.15)"
                          : isDeveloped
                          ? "rgba(245, 158, 11, 0.15)"
                          : "rgba(148, 163, 184, 0.12)",
                        color: isConverted ? "#10b981" : isDeveloped ? "#f59e0b" : "#94a3b8",
                        border: isConverted
                          ? "1px solid rgba(16, 185, 129, 0.3)"
                          : isDeveloped
                          ? "1px solid rgba(245, 158, 11, 0.3)"
                          : "1px solid rgba(148, 163, 184, 0.2)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {isConverted ? "📦 Üretime Hazır" : isDeveloped ? "✓ Geliştirildi" : "📝 Taslak"}
                    </span>
                  </div>

                  <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 11, color: "var(--text-muted)", marginBottom: 10 }}>
                    <span>{getGenreLabel(story.genre)}</span>
                    <span>•</span>
                    <span style={{ textTransform: "uppercase" }}>🌐 {story.target_language || "tr"}</span>
                    {partCount > 0 && (
                      <>
                        <span>•</span>
                        <span style={{ color: "#f59e0b", fontWeight: 600 }}>{partCount} Bölüm</span>
                      </>
                    )}
                  </div>

                  {hook && (
                    <div
                      style={{
                        fontSize: 11.5,
                        fontStyle: "italic",
                        color: "#fbbf24",
                        marginBottom: 8,
                        padding: "4px 8px",
                        background: "rgba(245, 158, 11, 0.08)",
                        borderRadius: 6,
                      }}
                    >
                      "{hook}"
                    </div>
                  )}

                  <p
                    style={{
                      fontSize: 12,
                      color: "var(--text-secondary)",
                      margin: 0,
                      lineHeight: 1.45,
                      display: "-webkit-box",
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {story.raw_text || "(Henüz metin girilmedi)"}
                  </p>
                </div>

                {/* Kart Aksiyonları */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8, paddingTop: 10, borderTop: "1px solid var(--border-subtle)" }}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {/* Materyale Dönüştür Butonu */}
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ flex: 1, minWidth: 130, fontSize: 11.5, padding: "6px 10px" }}
                      onClick={() => handleConvertToMaterial(story.id)}
                      disabled={actionLoadingId === story.id}
                      title="Geliştirilen bölümleri Üretim Materyalleri klasörüne kaydeder"
                    >
                      {actionLoadingId === story.id ? (
                        <Loader2 className="spinner" size={13} />
                      ) : (
                        <Layers size={13} style={{ color: "#38bdf8" }} />
                      )}
                      Materyale Dönüştür
                    </button>

                    {/* Prosedürel Animasyon Üret Butonu */}
                    <button
                      className="btn btn-sm"
                      style={{
                        flex: 1,
                        minWidth: 130,
                        fontSize: 11.5,
                        padding: "6px 10px",
                        background: "linear-gradient(135deg, #10b981, #06b6d4)",
                        color: "#fff",
                        border: "none",
                      }}
                      onClick={() => handleProduceAnimation(story.id, story.title)}
                      disabled={producingStoryId === story.id}
                      title="Instagram Aurora tarzı dikey animasyon videosunu render eder"
                    >
                      {producingStoryId === story.id ? (
                        <Loader2 className="spinner" size={13} />
                      ) : (
                        <Film size={13} />
                      )}
                      Animasyonu Üret
                    </button>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11 }}>
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ padding: "4px 8px", fontSize: 11, color: "var(--text-secondary)" }}
                      onClick={() => handleOpenEditModal(story)}
                    >
                      <Edit3 size={12} /> Düzenle
                    </button>

                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ padding: "4px 8px", fontSize: 11, color: "#f43f5e" }}
                      onClick={() => handleDelete(story.id)}
                    >
                      <Trash2 size={12} /> Sil
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Hikaye Taslağı Ekleme / Düzenleme Modalı */}
      {showModal && (
        <div
          className="modal-backdrop"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 99999,
            padding: 16,
          }}
          onClick={() => setShowModal(false)}
        >
          <div
            className="card"
            style={{
              width: "100%",
              maxWidth: 580,
              maxHeight: "90vh",
              overflowY: "auto",
              padding: "24px 26px",
              background: "#182030",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: 16,
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, borderBottom: "1px solid rgba(255, 255, 255, 0.08)", paddingBottom: 12 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                <BookOpen size={18} style={{ color: "#f59e0b" }} />
                {editingStory ? "Hikaye Taslağını Düzenle" : "Yeni Hikaye Taslağı Yaz"}
              </h3>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", fontSize: 18, cursor: "pointer" }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label className="form-label" style={{ fontSize: 12, marginBottom: 5 }}>
                  Hikaye / Dizi Başlığı <span style={{ color: "#f43f5e" }}>*</span>
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Örn: Zamanın Durduğu Saat Kulesi, Kadim Fener Efsanesi..."
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label className="form-label" style={{ fontSize: 12, marginBottom: 5 }}>Tür / Tema</label>
                  <select
                    className="form-input"
                    value={formGenre}
                    onChange={(e) => setFormGenre(e.target.value)}
                  >
                    <option value="sci_fi_mystery">🚀 Uzay & Bilimkurgu</option>
                    <option value="dark_mystery">🌑 Karanlık Gizem & Gerilim</option>
                    <option value="ancient_myth">🏛️ Kadim Efsane & Mitoloji</option>
                    <option value="fantasy_fable">🧚 Fantastik Masal</option>
                    <option value="psychological">🧠 Psikolojik & Dram</option>
                  </select>
                </div>

                <div>
                  <label className="form-label" style={{ fontSize: 12, marginBottom: 5 }}>Hedef Kanal Dili</label>
                  <select
                    className="form-input"
                    value={formLang}
                    onChange={(e) => setFormLang(e.target.value)}
                  >
                    <option value="tr">🇹🇷 Türkçe (tr)</option>
                    <option value="en">🇺🇸 İngilizce (en)</option>
                    <option value="de">🇩🇪 Almanca (de)</option>
                    <option value="es">🇪🇸 İspanyolca (es)</option>
                    <option value="fr">🇫🇷 Fransızca (fr)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="form-label" style={{ fontSize: 12, marginBottom: 5 }}>
                  Hikaye Taslağınız (Kendi Hikayenizi Buraya Yazın)
                </label>
                <textarea
                  className="form-input"
                  rows={6}
                  placeholder="Hikaye fikrinizi, başlangıcı, karakterleri ve olay örgüsünü aklınıza geldiği gibi yazın. Türkçe yazsanız dahi Gemini bunu kanalınızın hedef diline uyarlayacak ve dikey shorts bölümlerine ayıracaktır..."
                  value={formRawText}
                  onChange={(e) => setFormRawText(e.target.value)}
                  style={{ resize: "vertical", fontFamily: "inherit", lineHeight: 1.45 }}
                />
              </div>

              <div>
                <label className="form-label" style={{ fontSize: 12, marginBottom: 5 }}>
                  Özel Kurgu / Cliffhanger Notları (İsteğe Bağlı)
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Örn: Bölüm 1 sonunda geminin kaptanı şoke edici bir şey keşfetsin..."
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8, borderTop: "1px solid rgba(255, 255, 255, 0.08)", paddingTop: 14 }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setShowModal(false)}
                  disabled={saving}
                >
                  İptal
                </button>
                <button
                  type="submit"
                  className="btn"
                  style={{
                    background: "linear-gradient(135deg, #f59e0b, #ec4899)",
                    color: "#fff",
                    border: "none",
                    padding: "8px 20px",
                    fontWeight: 600,
                  }}
                  disabled={saving}
                >
                  {saving ? (
                    <>
                      <Loader2 className="spinner" size={14} /> Kaydediliyor...
                    </>
                  ) : editingStory ? (
                    "Değişiklikleri Kaydet"
                  ) : (
                    "Taslağı Kaydet"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
