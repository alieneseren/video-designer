import { Component, useState, useEffect, useCallback, useMemo } from "react";
import {
  LayoutDashboard,
  Film,
  Smartphone,
  MessageSquare,
  Settings as SettingsIcon,
  Plus,
  Play,
  CheckCircle2,
  AlertCircle,
  Clock,
  Calendar,
  RefreshCw,
  Trash2,
  Edit3,
  Upload,
  Folder,
  Eye,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Loader2,
  Sparkles,
  Tv,
  Users,
  Activity,
  Layers,
  Volume2,
  ArrowRight,
  Video,
  Scissors,
  Send,
  Archive,
  RotateCcw,
  Copy,
  Check,
  X,
  Radio,
  Download,
  Server,
  Music,
  Zap,
  Bell,
  Coffee,
  Search,
  CalendarDays,
  Camera,
  CheckSquare,
  BookOpen
} from "lucide-react";
import CasperCompanion from "./components/CasperCompanion";
import CasperTerminalModal from "./components/CasperTerminalModal";
import AutomationPage from "./components/AutomationPage";
import VoiceCloneStudio from "./components/VoiceCloneStudio";
import VideoVoiceClonePage from "./components/VideoVoiceClonePage";
import VideoScenePatcherModal from "./components/VideoScenePatcherModal";
import KontrolVideosPage from "./components/KontrolVideosPage";
import StoryStudio from "./components/StoryStudio";
import StoryStudioPage from "./components/StoryStudioPage";
// import VideoEditorPage from "./components/VideoEditorPage"; // Shelved

/* ══════════════════════════════════════════════════════════════════
   CONSTANTS
   ══════════════════════════════════════════════════════════════════ */

const LANGUAGES = [
  { code: "tr", name: "Türkçe",     flag: "🇹🇷" },
  { code: "en", name: "English",    flag: "🇺🇸" },
  { code: "de", name: "Deutsch",    flag: "🇩🇪" },
  { code: "fr", name: "Français",   flag: "🇫🇷" },
  { code: "es", name: "Español",    flag: "🇪🇸" },
  { code: "it", name: "Italiano",   flag: "🇮🇹" },
  { code: "pt", name: "Português",  flag: "🇧🇷" },
  { code: "ru", name: "Русский",    flag: "🇷🇺" },
  { code: "ja", name: "日本語",     flag: "🇯🇵" },
  { code: "ko", name: "한국어",     flag: "🇰🇷" },
  { code: "zh", name: "中文",       flag: "🇨🇳" },
  { code: "ar", name: "العربية",    flag: "🇸🇦" },
  { code: "hi", name: "हिन्दी",    flag: "🇮🇳" },
  { code: "nl", name: "Nederlands", flag: "🇳🇱" },
  { code: "pl", name: "Polski",     flag: "🇵🇱" },
  { code: "sv", name: "Svenska",    flag: "🇸🇪" },
  { code: "da", name: "Dansk",      flag: "🇩🇰" },
  { code: "fi", name: "Suomi",      flag: "🇫🇮" },
  { code: "no", name: "Norsk",      flag: "🇳🇴" },
  { code: "cs", name: "Čeština",    flag: "🇨🇿" },
  { code: "hu", name: "Magyar",     flag: "🇭🇺" },
  { code: "ro", name: "Română",     flag: "🇷🇴" },
  { code: "uk", name: "Українська", flag: "🇺🇦" },
  { code: "el", name: "Ελληνικά",  flag: "🇬🇷" },
  { code: "id", name: "Indonesia",  flag: "🇮🇩" },
  { code: "th", name: "ภาษาไทย",   flag: "🇹🇭" },
  { code: "vi", name: "Tiếng Việt", flag: "🇻🇳" },
];

const TOPICS = ["basketball_analysis", "aviation", "crayon_combat", "tech_finance_essay", "reddit_stories", "whatsapp_stories", "music", "space", "story", "travel", "planets", "astronomy", "cosmos", "science"];

const CATEGORY_LABELS = {
  basketball_analysis: "🏀 Basketbol Analizi (The Basketball Show & NBA)",
  aviation: "✈️ Havacılık (Black Box & ATC)",
  crayon_combat: "🖍️ Askeri Araçlar & Çöp Adam Hicvi (Crayon Combat)",
  tech_finance_essay: "📈 Teknoloji & Finans Belgeseli (Crayon Capital)",
  reddit_stories: "🤖 Reddit Hikayeleri (ASMR + Altyazı)",
  whatsapp_stories: "💬 WhatsApp Mesajlaşma (Bi' Dublaj & Komedi)",
  music: "🎵 Biyo-AI Müzik (Sinek Beyni - Connectome)",
  story: "📖 Hikaye & Masal",
  travel: "🌍 Seyahat & Gezi",
  space: "🚀 Uzay & Bilim",
  planets: "🪐 Gezegenler & Uzay",
  astronomy: "🔭 Astronomi",
  cosmos: "✨ Kozmos & Evren",
  science: "🔬 Bilim",
};

const NAV = [
  { id: "dashboard", icon: LayoutDashboard,  label: "Dashboard" },
  { id: "automation", icon: Zap,             label: "Otomasyon" },
  { id: "materials", icon: Layers,           label: "Üretim Materyalleri" },
  { id: "story_studio", icon: BookOpen,      label: "Hikaye & Masal Atölyesi" },
  { id: "kontrol_videos", icon: CheckSquare, label: "Kontroldeki Videolar" },
  { id: "routines",  icon: Clock,            label: "Rutinler" },
  { id: "server_render", icon: Server,       label: "Sunucu Render" },
  { id: "youtube_upload", icon: Upload,      label: "YouTube Yükle" },
  { id: "instagram_schedule", icon: Camera, label: "Instagram Planla" },
  { id: "video_voiceover", icon: Volume2, label: "Klon Ses Uygula" },
  { id: "videos",    icon: Film,             label: "Videolar" },
  // { id: "editor",    icon: Scissors,         label: "Video Düzenleyici" }, // Rafa kaldırıldı
  { id: "shorts_creator", icon: Smartphone,  label: "Uzundan Shorts" },
  { id: "chat",      icon: MessageSquare,    label: "AI Sohbet" },
  { id: "settings",  icon: SettingsIcon,     label: "Ayarlar" },
];

const AI_PROVIDERS = [
  { id: "claude",   name: "Claude (Anthropic)",  desc: "En yüksek kalite senaryo üretimi" },
  { id: "gemini",   name: "Gemini (Google)",      desc: "Hızlı ve ücretsiz seçenek" },
  { id: "lmstudio", name: "LM Studio (Yerel)",   desc: "LM Studio ile yüklenen modeller" },
  { id: "ollama",   name: "Ollama (Yerel)",       desc: "Ollama ile çalışan modeller" },
];

/* ── Helpers ─────────────────────────────────────────────────── */
const getLang = (code) => LANGUAGES.find(l => l.code === code);
function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

const WEEKDAY_LABELS = {
  mon: "Pzt",
  tue: "Sal",
  wed: "Çar",
  thu: "Per",
  fri: "Cum",
  sat: "Cmt",
  sun: "Paz",
};

function getNextRoutineRun(routine) {
  if (!routine.active) return "Zamanlama duraklatıldı";
  const weekdays = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
  const scheduledTime = routine.schedule_time || "10:00";
  const [hours, minutes] = scheduledTime.split(":").map(Number);
  const now = new Date();
  const next = new Date(now);

  for (let offset = 0; offset < 7; offset += 1) {
    const candidate = new Date(now);
    candidate.setDate(now.getDate() + offset);
    candidate.setHours(hours, minutes, 0, 0);
    const day = weekdays[candidate.getDay()];
    const matchesDay = (routine.days || ["all"]).includes("all") || (routine.days || []).includes(day);
    if (matchesDay && candidate >= next) {
      const dayLabel = offset === 0 ? "Bugün" : offset === 1 ? "Yarın" : candidate.toLocaleDateString("tr-TR", { weekday: "long" });
      return `${dayLabel}, ${scheduledTime}`;
    }
  }
  return `Gelecek hafta, ${scheduledTime}`;
}

/* ══════════════════════════════════════════════════════════════════
   SHARED UI
   ══════════════════════════════════════════════════════════════════ */

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="card" style={{ padding: 24, margin: "16px 0", border: "1px solid rgba(239, 68, 68, 0.3)", background: "rgba(239, 68, 68, 0.05)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--danger, #ef4444)", marginBottom: 12 }}>
            <AlertCircle size={20} />
            <span style={{ fontWeight: 600, fontSize: 15 }}>{this.props.fallbackTitle || "Bileşen yüklenirken bir hata oluştu"}</span>
          </div>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>
            {this.state.error?.message || "Bilinmeyen bir hata meydana geldi."}
          </p>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
          >
            <RefreshCw size={13} /> Yeniden Dene
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function Toggle({ checked, onChange }) {
  return (
    <label className="toggle-wrap" style={{ cursor: "pointer" }}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      <span className="toggle-track" />
      <span className="toggle-thumb" />
    </label>
  );
}

function Modal({ open, onClose, title, children }) {
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-panel">
        <div className="modal-header">
          <span className="modal-title">{title}</span>
          <button className="modal-close" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

function StatusDot({ active, size = 6 }) {
  return (
    <span style={{
      width: size, height: size, borderRadius: "50%", display: "inline-block", flexShrink: 0,
      background: active ? "var(--success)" : "var(--text-muted)",
      boxShadow: active ? "0 0 6px rgba(52,211,153,0.5)" : "none",
      animation: active ? "pulse-dot 2.5s ease-in-out infinite" : "none",
    }} />
  );
}

/* ══════════════════════════════════════════════════════════════════
   CHANNEL FORM
   ══════════════════════════════════════════════════════════════════ */

function FileUploader({ label, value, onChange, category, placeholder }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError("");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        onChange(data.file_path);
      } else {
        const data = await res.json();
        setError(data.detail || "Yükleme hatası");
      }
    } catch (err) {
      setError("Bağlantı hatası");
    } finally {
      setUploading(false);
    }
  };

  const basename = value ? value.split("/").pop() : "";

  return (
    <div className="form-group" style={{ marginBottom: 12 }}>
      <label className="form-label" style={{ display: "flex", justifyContent: "space-between" }}>
        <span>{label}</span>
        {error && <span style={{ color: "var(--danger)", fontSize: 10.5 }}>{error}</span>}
      </label>
      <div className="card" style={{
        padding: "10px 14px",
        background: "var(--bg-primary)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-sm)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 10
      }}>
        {value ? (
          <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 0 }}>
            <span style={{ fontSize: 16 }}>📄</span>
            <span style={{ fontSize: 12, color: "var(--text-primary)", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap", flex: 1 }}>
              {basename}
            </span>
            <button className="btn btn-ghost btn-sm" style={{ padding: "2px 6px", fontSize: 11, color: "var(--danger)" }} onClick={() => onChange(null)}>
              Kaldır
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1 }}>
            <input
              type="file"
              onChange={handleFileChange}
              style={{ display: "none" }}
              id={"upload-" + category + "-" + label.length}
              accept={category === "bgm" ? "audio/*" : category === "watermark" ? "image/*" : "video/*"}
            />
            <label
              htmlFor={"upload-" + category + "-" + label.length}
              className="btn btn-ghost btn-sm"
              style={{ margin: 0, cursor: "pointer" }}
            >
              {uploading ? "Yükleniyor..." : "Dosya Seç"}
            </label>
            <span style={{ fontSize: 11.5, color: "var(--text-muted)", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
              {uploading ? "Dosya sunucuya gönderiliyor..." : (placeholder || "Dosya seçilmedi")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function ChannelForm({ initial, onSave, onClose }) {
  const TRANSITIONS = [
    { id: "fade",  label: "Fade",  desc: "Yumuşak solma", icon: "🌅" },
    { id: "zoom",  label: "Zoom",  desc: "Ken Burns",     icon: "🔍" },
    { id: "parallax", label: "Parallax", desc: "3D Parallax", icon: "🌌" },
    { id: "slide", label: "Slide", desc: "Kayarak geçiş", icon: "➡" },
    { id: "none",  label: "Yok",   desc: "Kesme",         icon: "⬛" },
  ];

  const defaultEditOptions = {
    subtitle_preset: null,
    subtitle_animation: null,
    bgm_path: null,
    bgm_volume: null,
    watermark_path: null,
    watermark_text: null,
    watermark_position: null,
    intro_clip_path: null,
    outro_clip_path: null,
    kenburns_intensity: null,
    transition_dur: null,
    video_duration: null,
    censor_faces: null,
    auto_editor: null,
    censor_logo_path: null,
    reddit_avatar_path: null,
    reddit_username: null,
    enable_i2v: false,
    i2v_model_quality: "distilled_q4",
    i2v_fps_multiplier: 4,
    enable_hyperframes_hook: false,
    hyperframes_hook_badge: "YENİ VİDEO",
    auto_ai_qa_enabled: false,
    voice_clone_id: null,
  };


  const [form, setForm] = useState(initial ? {
    channel_id: initial.channel_id, name: initial.name,
    language: initial.language, topic_category: initial.topic_category,
    schedule_hour: initial.schedule_hour, active: initial.active,
    shorts_mode: initial.shorts_mode || false,
    voice_clone_id: initial.voice_clone_id || initial.edit_options?.voice_clone_id || "",
    instagram: initial.instagram || false,
    instagram_username: initial.instagram_username || "",
    transition: initial.transition || "fade",
    auto_ai_qa_enabled: initial.auto_ai_qa_enabled ?? initial.edit_options?.auto_ai_qa_enabled ?? false,
    custom_topics_text: (initial.custom_topics || []).join(", ")
  } : {
    channel_id: "", name: "", language: "tr",
    topic_category: "space", schedule_hour: 9,
    active: true, shorts_mode: false, transition: "fade",
    voice_clone_id: "",
    instagram: false, instagram_username: "",
    auto_ai_qa_enabled: false,
    custom_topics_text: ""
  });

  const [voiceClones, setVoiceClones] = useState([]);
  const [activeCloneId, setActiveCloneId] = useState("");

  useEffect(() => {
    fetch("/api/voice-clones")
      .then(res => res.json())
      .then(data => {
        if (data && data.clones) {
          setVoiceClones(data.clones);
          setActiveCloneId(data.active_id || "");
        }
      })
      .catch(() => {});
  }, []);

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [editOptions, setEditOptions] = useState(() => {
    if (initial && initial.edit_options) {
      return { ...defaultEditOptions, ...initial.edit_options };
    }
    return defaultEditOptions;
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const valid = form.channel_id.trim() && form.name.trim();

  const handleSave = () => {
    if (!valid) return;
    const effVoiceClone = form.voice_clone_id || null;
    onSave({
      channel_id: form.channel_id, name: form.name,
      language: form.language, topic_category: form.topic_category,
      schedule_hour: form.schedule_hour, active: form.active,
      shorts_mode: form.shorts_mode, transition: form.transition,
      voice_clone_id: effVoiceClone,
      instagram: form.instagram,
      instagram_username: form.instagram_username.trim().replace(/^@/, ""),
      auto_ai_qa_enabled: !!form.auto_ai_qa_enabled,
      custom_topics: form.custom_topics_text.split(",").map(t => t.trim()).filter(Boolean),
      edit_options: {
        ...editOptions,
        voice_clone_id: effVoiceClone,
        auto_ai_qa_enabled: !!form.auto_ai_qa_enabled
      }
    });
    onClose();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div className="form-group">
          <label className="form-label">Kanal ID</label>
          <input className="form-input" placeholder="ch_uzay_tr" value={form.channel_id}
            disabled={!!initial} onChange={e => set("channel_id", e.target.value.toLowerCase().replace(/\s/g, "_"))} />
        </div>
        <div className="form-group">
          <label className="form-label">Kanal Adı</label>
          <input className="form-input" placeholder="Uzay Keşifleri TR" value={form.name}
            onChange={e => set("name", e.target.value)} />
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div className="form-group">
          <label className="form-label">Yayın Dili</label>
          <select className="form-input" value={form.language} onChange={e => set("language", e.target.value)}>
            {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.flag} {l.name}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>🎙️ Ses Klonu Modeli</span>
            {form.voice_clone_id ? (
              <span style={{ fontSize: 10, color: "var(--accent-primary)", background: "var(--accent-muted)", padding: "1px 6px", borderRadius: 4 }}>
                Özel Klon
              </span>
            ) : (
              <span style={{ fontSize: 10, color: "var(--text-muted)" }}>Varsayılan</span>
            )}
          </label>
          <select
            className="form-input"
            value={form.voice_clone_id || ""}
            onChange={e => set("voice_clone_id", e.target.value)}
          >
            <option value="">
              🌐 Sistem Varsayılanı (Aktif Klon{activeCloneId ? `: ${activeCloneId}` : ""})
            </option>
            {voiceClones.map(vc => (
              <option key={vc.id} value={vc.id}>
                {vc.name} {vc.id === activeCloneId ? "⭐ (Global Aktif)" : ""}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div className="form-group">
          <label className="form-label">Konu Kategorisi</label>
          <select className="form-input" value={form.topic_category} onChange={e => set("topic_category", e.target.value)}>
            {TOPICS.map(t => (
              <option key={t} value={t}>
                {CATEGORY_LABELS[t] || t}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Zamanlayıcı</label>
          <select className="form-input" value={form.schedule_hour} onChange={e => set("schedule_hour", Number(e.target.value))}>
            {Array.from({ length: 24 }, (_, i) => i).map(h => (
              <option key={h} value={h}>{String(h).padStart(2, "0")}:00</option>
            ))}
          </select>
        </div>
      </div>

      {/* Shorts modu */}
      <div className="card" style={{
        padding: "14px 16px", display: "flex", alignItems: "center",
        justifyContent: "space-between", gap: 12,
        background: form.shorts_mode ? "rgba(239,68,68,0.06)" : "var(--bg-secondary)",
        border: form.shorts_mode ? "1px solid rgba(239,68,68,0.25)" : "1px solid var(--border-subtle)",
        transition: "all 0.2s",
      }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
            <span>📱</span> YouTube Shorts Modu
          </div>
          <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 2 }}>
            9:16 dikey format — maks. 59 saniye
          </div>
        </div>
        <Toggle checked={form.shorts_mode} onChange={v => set("shorts_mode", v)} />
      </div>

      <div className="card" style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 7 }}>
              <Camera size={16} color="#c13584" /> Instagram Reels paylaşımı
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 3 }}>
              Video seçtiğiniz tarihe kuyruğa alınır; zamanında eklenti yükler.
            </div>
          </div>
          <Toggle checked={form.instagram} onChange={value => set("instagram", value)} />
        </div>
        {form.instagram && (
          <>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Instagram kullanıcı adı</label>
            <input
              className="form-input"
              placeholder="ornek_hesap"
              value={form.instagram_username}
              onChange={event => set("instagram_username", event.target.value.replace(/^@/, ""))}
            />
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              Instagram uygulamasında giriş yapacağınız hesapla eşleşmeli.
            </div>
          </div>
          </>
        )}
      </div>

      {/* Yerel I2V Animasyonu */}
      <div className="card" style={{
        padding: "14px 16px", display: "flex", flexDirection: "column", gap: 10,
        background: editOptions.enable_i2v ? "rgba(16,185,129,0.06)" : "var(--bg-secondary)",
        border: editOptions.enable_i2v ? "1px solid rgba(16,185,129,0.3)" : "1px solid var(--border-subtle)",
        transition: "all 0.2s",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
              <span>🎬</span> Görsel Animasyonu (Yerel I2V Modülü)
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 2 }}>
              Durağan görselleri AI ile hareketlendirir (LTX 2.3 + RIFE/FILM Interpolasyon)
            </div>
          </div>
          <Toggle
            checked={!!editOptions.enable_i2v}
            onChange={v => setEditOptions(eo => ({ ...eo, enable_i2v: v }))}
          />
        </div>

        {editOptions.enable_i2v && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 4, paddingTop: 10, borderTop: "1px solid var(--border-subtle)" }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" style={{ fontSize: 11 }}>Model Kalitesi</label>
              <select
                className="form-input"
                style={{ padding: "6px 10px", fontSize: 12 }}
                value={editOptions.i2v_model_quality || "distilled_q4"}
                onChange={e => setEditOptions(eo => ({ ...eo, i2v_model_quality: e.target.value }))}
              >
                <option value="distilled_q4">Distilled Q4 (Hızlı M4 - 3s)</option>
                <option value="distilled_q8">Distilled Q8 (Yüksek Kalite)</option>
                <option value="full">Full FP16 (Maksimum Detay)</option>
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" style={{ fontSize: 11 }}>Interpolasyon Çarpanı</label>
              <select
                className="form-input"
                style={{ padding: "6px 10px", fontSize: 12 }}
                value={editOptions.i2v_fps_multiplier || 4}
                onChange={e => setEditOptions(eo => ({ ...eo, i2v_fps_multiplier: Number(e.target.value) }))}
              >
                <option value={4}>4x Yavaşlatma (Varsayılan - Akıcı 12s)</option>
                <option value={2}>2x Yavaşlatma (Orta)</option>
                <option value={8}>8x Yavaşlatma (Süper Ağır Çekim)</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* 🔍 Otomatik Yerel AI Kalite Kontrolü & Akıllı Sahne Düzeltme (LM Studio Gemma-4-12B) */}
      <div className="card" style={{
        padding: "14px 16px", display: "flex", flexDirection: "column", gap: 10,
        background: form.auto_ai_qa_enabled ? "rgba(6,182,212,0.08)" : "var(--bg-secondary)",
        border: form.auto_ai_qa_enabled ? "1px solid rgba(6,182,212,0.4)" : "1px solid var(--border-subtle)",
        transition: "all 0.2s",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
              <span>🔍</span> Otomatik Yerel AI Kalite Kontrolü & Akıllı Sahne Düzeltme
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 2 }}>
              Videolar 'kontrol' klasörüne alınır; LM Studio Gemma-4-12B Vision ile incelenip hatalı sahneler otomatik düzeltilir (max 3 tur) ve onaylanınca 'yuklenecek'e aktarılır.
            </div>
          </div>
          <Toggle
            checked={!!form.auto_ai_qa_enabled}
            onChange={v => {
              set("auto_ai_qa_enabled", v);
              setEditOptions(eo => ({ ...eo, auto_ai_qa_enabled: v }));
            }}
          />
        </div>
      </div>

      {/* Geçiş animasyonu */}
      <div className="form-group">
        <label className="form-label" style={{ marginBottom: 8, display: "block" }}>Görsel Geçiş Animasyonu</label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {TRANSITIONS.map(t => (
            <label key={t.id} style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "10px 12px", borderRadius: "var(--radius-md)",
              background: form.transition === t.id ? "var(--accent-muted)" : "var(--bg-primary)",
              border: `1px solid ${form.transition === t.id ? "var(--accent-border)" : "var(--border-subtle)"}`,
              cursor: "pointer", transition: "all 0.15s",
            }}>
              <input type="radio" name="transition" value={t.id}
                checked={form.transition === t.id}
                onChange={() => set("transition", t.id)}
                style={{ accentColor: "var(--accent-primary)" }} />
              <span style={{ fontSize: 16 }}>{t.icon}</span>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{t.label}</div>
                <div style={{ fontSize: 10.5, color: "var(--text-muted)" }}>{t.desc}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Özel Konular <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(virgülle)</span></label>
        <input className="form-input" placeholder="kara delikler, mars kolonizasyonu"
          value={form.custom_topics_text} onChange={e => set("custom_topics_text", e.target.value)} />
      </div>

      {/* Reddit Hikayeleri Kart & Avatar Ayarları */}
      {form.topic_category === "reddit_stories" && (
        <div className="card" style={{
          padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12,
          background: "rgba(255, 69, 0, 0.05)",
          border: "1px solid rgba(255, 69, 0, 0.25)",
        }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#ff4500", display: "flex", alignItems: "center", gap: 6 }}>
              <span>🤖</span> Reddit Başlık Kartı & Avatar Ayarları
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 2 }}>
              Videonun başında beliren Reddit kartındaki yazar adı ve profil fotoğrafı.
            </div>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: 12 }}>Reddit Kullanıcı Adı (Yazar)</label>
            <input
              className="form-input"
              placeholder={`Varsayılan: ${form.language.toUpperCase()} diline özel rastgele yazar`}
              value={editOptions.reddit_username || ""}
              onChange={e => setEditOptions(eo => ({ ...eo, reddit_username: e.target.value.trim() || null }))}
            />
          </div>

          <div>
            <FileUploader
              label="Reddit Profil Fotoğrafı (Avatar)"
              value={editOptions.reddit_avatar_path}
              category="watermark"
              placeholder="Profil resmi yükleyin (Boş bırakılırsa resmi Reddit logosu kullanılır)"
              onChange={val => setEditOptions(eo => ({ ...eo, reddit_avatar_path: val }))}
            />
          </div>
        </div>
      )}

      {/* Sinek Beyni Biyo-AI Müzik Ayarları */}
      {(form.topic_category === "music" || form.topic_category === "connectome") && (
        <div className="card" style={{
          padding: "16px", display: "flex", flexDirection: "column", gap: 14,
          background: "rgba(0, 240, 255, 0.05)",
          border: "1px solid rgba(0, 240, 255, 0.3)",
        }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#00f0ff", display: "flex", alignItems: "center", gap: 6 }}>
              <span>🪰</span> Sinek Beyni (Connectome) Biyo-AI Müzik Ayarları
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 2 }}>
              139.255 Drosophila nöronunun biyolojik ateşlemeleri ile 3-5 dakikalık müzik klipleri ve Shorts türetimi.
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" style={{ fontSize: 12 }}>Klip Süresi (Varsayılan)</label>
              <select
                className="form-input"
                value={editOptions.music_duration || 180}
                onChange={e => setEditOptions(eo => ({ ...eo, music_duration: Number(e.target.value) }))}
              >
                <option value={180}>3 Dakika (180 saniye)</option>
                <option value={240}>4 Dakika (240 saniye)</option>
                <option value={300}>5 Dakika (300 saniye)</option>
                <option value={60}>1 Dakika (Shorts - 60 sn)</option>
              </select>
            </div>

            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" style={{ fontSize: 12 }}>Müzik Türü (Canlı Yayın Skalası)</label>
              <select
                className="form-input"
                value={editOptions.music_genre || "emotional"}
                onChange={e => setEditOptions(eo => ({ ...eo, music_genre: e.target.value }))}
              >
                <option value="emotional">Chopin Nocturne (Duygusal & Melankolik)</option>
                <option value="mysterious">D Dorian (Gizemli & Sinematik)</option>
                <option value="peaceful">C Lydian (Huzurlu Ambient)</option>
                <option value="oriental">A Hirajoshi (Derin Zen)</option>
                <option value="epic">Epik & Dramatik Senfoni</option>
                <option value="neoclassical">Neo-Klasik Piyano</option>
                <option value="lofi">Lo-Fi Biyo Vuruşlar</option>
                <option value="cyberpunk">Cyberpunk Sinaps</option>
                <option value="jazz">Nöral Caz & Blues</option>
                <option value="ambient">Kozmik Boşluk Ambient</option>
              </select>
            </div>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: 12 }}>Görsel 3D Teması</label>
            <select
              className="form-input"
              value={editOptions.music_theme || "cosmic"}
              onChange={e => setEditOptions(eo => ({ ...eo, music_theme: e.target.value }))}
            >
              <option value="cosmic">Kozmik Uzay (Obsidyen & Safir Mavi)</option>
              <option value="cyberpunk">Cyberpunk Neon (Camgöbeği & Macenta)</option>
              <option value="biophilic">Biyofilik Doğa (Zümrüt Yeşil & Turkuaz)</option>
            </select>
          </div>
        </div>
      )}

      {/* HyperFrames Kinetik Tipografi Hook Seçeneği */}
      <div className="card" style={{
        padding: "12px 14px",
        background: editOptions.enable_hyperframes_hook ? "rgba(0, 245, 212, 0.05)" : "var(--bg-secondary)",
        border: `1px solid ${editOptions.enable_hyperframes_hook ? "rgba(0, 245, 212, 0.35)" : "var(--border-subtle)"}`,
        borderRadius: "var(--radius-md)",
        display: "flex", flexDirection: "column", gap: 10,
        transition: "all 0.2s ease"
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 16 }}>⚡</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: editOptions.enable_hyperframes_hook ? "#00f5d4" : "var(--text-primary)" }}>
                HyperFrames Kinetik Hook
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                Videonun başına 3-4 saniyelik sinematik animasyonlu başlık girişi ekler.
              </div>
            </div>
          </div>
          <Toggle
            checked={Boolean(editOptions.enable_hyperframes_hook)}
            onChange={v => setEditOptions(eo => ({ ...eo, enable_hyperframes_hook: v }))}
          />
        </div>

        {editOptions.enable_hyperframes_hook && (
          <div style={{ display: "flex", gap: 10, marginTop: 4, alignItems: "center" }}>
            <label className="form-label" style={{ margin: 0, fontSize: 11, minWidth: 85 }}>Rozet Metni:</label>
            <input
              className="form-input"
              style={{ height: 32, fontSize: 12 }}
              placeholder="Örn: YENİ VİDEO, SHORTS, ÖZEL BÖLÜM"
              value={editOptions.hyperframes_hook_badge || ""}
              onChange={e => setEditOptions(eo => ({ ...eo, hyperframes_hook_badge: e.target.value }))}
            />
          </div>
        )}
      </div>

      {/* Gelişmiş Ayarlar Butonu */}
      <button

        type="button"
        className="btn btn-ghost"
        style={{
          width: "100%",
          justifyContent: "space-between",
          padding: "10px 14px",
          border: "1px dashed var(--border-subtle)",
          background: showAdvanced ? "rgba(255,255,255,0.02)" : "transparent"
        }}
        onClick={() => setShowAdvanced(!showAdvanced)}
      >
        <span>⚙ Gelişmiş Video Tasarım Ayarları (Özel)</span>
        <span>{showAdvanced ? "▲" : "▼"}</span>
      </button>

      {showAdvanced && (
        <div style={{
          display: "flex",
          flexDirection: "column",
          gap: 14,
          padding: "14px 16px",
          background: "rgba(255,255,255,0.01)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-md)",
          maxHeight: "350px",
          overflowY: "auto"
        }}>
          <p style={{ fontSize: 11.5, color: "var(--text-muted)", margin: 0 }}>
            Bu kanala özel ayarları yapılandırın. Boş bırakılan alanlar global ayarları devralır.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Video Süresi (Saniye)</label>
              <input
                type="number"
                className="form-input"
                placeholder="Global Varsayılan"
                value={editOptions.video_duration || ""}
                onChange={e => setEditOptions(eo => ({ ...eo, video_duration: e.target.value ? String(e.target.value) : null }))}
              />
              {form.shorts_mode && (
                <div style={{ fontSize: 10.5, color: "var(--warning)", marginTop: 4 }}>
                  Shorts modunda maks. 60 saniye sınırı uygulanır.
                </div>
              )}
            </div>
            <div className="form-group">
              <label className="form-label">Geçiş Süresi (Saniye)</label>
              <input
                type="number"
                step="0.1"
                className="form-input"
                placeholder="Global Varsayılan"
                value={editOptions.transition_dur || ""}
                onChange={e => setEditOptions(eo => ({ ...eo, transition_dur: e.target.value ? String(e.target.value) : null }))}
              />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Altyazı Stili (Preset)</label>
              <select
                className="form-input"
                value={editOptions.subtitle_preset || ""}
                onChange={e => setEditOptions(eo => ({ ...eo, subtitle_preset: e.target.value || null }))}
              >
                <option value="">Global Varsayılan</option>
                <option value="minimal">Minimal (İnce Yazı)</option>
                <option value="bold">Bold (Kalın Gölgeli)</option>
                <option value="tiktok">Tiktok Style (Sarı Vurgulu)</option>
                <option value="youtube-classic">YouTube Klasik (Siyah Bantlı)</option>
                <option value="news">Haber Kanalı (Alt Şerit)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Altyazı Animasyonu</label>
              <select
                className="form-input"
                value={editOptions.subtitle_animation || ""}
                onChange={e => setEditOptions(eo => ({ ...eo, subtitle_animation: e.target.value || null }))}
              >
                <option value="">Global Varsayılan</option>
                <option value="none">Yok (Statik)</option>
                <option value="fade">Fade (Yavaşça belirme)</option>
                <option value="pop">Pop (Zıplama)</option>
                <option value="typewriter">Daktilo</option>
                <option value="word-highlight">Vurgulu</option>
              </select>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Ken Burns (Zoom) Yoğunluğu</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                placeholder="Global Varsayılan"
                value={editOptions.kenburns_intensity || ""}
                onChange={e => setEditOptions(eo => ({ ...eo, kenburns_intensity: e.target.value ? String(e.target.value) : null }))}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Yüz Sansürleme</label>
              <select
                className="form-input"
                value={editOptions.censor_faces === null || editOptions.censor_faces === undefined ? "" : String(editOptions.censor_faces)}
                onChange={e => {
                  const val = e.target.value;
                  setEditOptions(eo => ({
                    ...eo,
                    censor_faces: val === "" ? null : (val === "true")
                  }));
                }}
              >
                <option value="">Global Varsayılan</option>
                <option value="true">Aktif (Yüzleri Bulanıklaştır)</option>
                <option value="false">Pasif (Sansürleme)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Auto-Editor (Sessizlik Silme)</label>
              <select
                className="form-input"
                value={editOptions.auto_editor === null || editOptions.auto_editor === undefined ? "" : String(editOptions.auto_editor)}
                onChange={e => {
                  const val = e.target.value;
                  setEditOptions(eo => ({
                    ...eo,
                    auto_editor: val === "" ? null : (val === "true")
                  }));
                }}
              >
                <option value="">Global Varsayılan</option>
                <option value="true">Aktif (Sessiz Alanları Kes)</option>
                <option value="false">Pasif (Sessiz Alanları Koruma)</option>
              </select>
            </div>
          </div>

          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 10 }}>
            <FileUploader
              label="Özel Arka Plan Müziği (BGM)"
              value={editOptions.bgm_path}
              category="bgm"
              placeholder="Global Varsayılan BGM"
              onChange={val => setEditOptions(eo => ({ ...eo, bgm_path: val }))}
            />
            
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 8 }}>
              <div className="form-group">
                <label className="form-label">BGM Ses Seviyesi (0.0 - 1.0)</label>
                <input
                  type="number"
                  step="0.05"
                  className="form-input"
                  placeholder="Global Varsayılan"
                  value={editOptions.bgm_volume || ""}
                  onChange={e => setEditOptions(eo => ({ ...eo, bgm_volume: e.target.value ? String(e.target.value) : null }))}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Filigran Pozisyonu</label>
                <select
                  className="form-input"
                  value={editOptions.watermark_position || ""}
                  onChange={e => setEditOptions(eo => ({ ...eo, watermark_position: e.target.value || null }))}
                >
                  <option value="">Global Varsayılan</option>
                  <option value="top-left">Sol Üst</option>
                  <option value="top-right">Sağ Üst</option>
                  <option value="bottom-left">Sol Alt</option>
                  <option value="bottom-right">Sağ Alt</option>
                  <option value="bottom-center">Alt Orta</option>
                </select>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 8 }}>
              <div className="form-group" style={{ gridColumn: "span 2" }}>
                <label className="form-label">Filigran Yazısı</label>
                <input
                  className="form-input"
                  placeholder="Global Varsayılan Yazı"
                  value={editOptions.watermark_text || ""}
                  onChange={e => setEditOptions(eo => ({ ...eo, watermark_text: e.target.value || null }))}
                />
              </div>
            </div>

            <div style={{ marginTop: 8 }}>
              <FileUploader
                label="Özel Logo / Filigran Görseli"
                value={editOptions.watermark_path}
                category="watermark"
                placeholder="Global Varsayılan Logo"
                onChange={val => setEditOptions(eo => ({ ...eo, watermark_path: val }))}
              />
            </div>

            <div style={{ marginTop: 8 }}>
              <FileUploader
                label="NASA Logo Sansür Görseli"
                value={editOptions.censor_logo_path}
                category="watermark"
                placeholder="Sansür için kullanılacak görsel (örn. Sansür bandı)"
                onChange={val => setEditOptions(eo => ({ ...eo, censor_logo_path: val }))}
              />
            </div>
          </div>

          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 10 }}>
            <FileUploader
              label="Özel Intro Klibi"
              value={editOptions.intro_clip_path}
              category="intro"
              placeholder="Global Varsayılan Intro"
              onChange={val => setEditOptions(eo => ({ ...eo, intro_clip_path: val }))}
            />
            <FileUploader
              label="Özel Outro Klibi"
              value={editOptions.outro_clip_path}
              category="outro"
              placeholder="Global Varsayılan Outro"
              onChange={val => setEditOptions(eo => ({ ...eo, outro_clip_path: val }))}
            />
          </div>
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Toggle checked={form.active} onChange={v => set("active", v)} />
        <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Aktif olarak başlat</span>
      </div>
      <div style={{ display: "flex", gap: 8, paddingTop: 8, borderTop: "1px solid var(--border-subtle)", marginTop: 4 }}>
        <button className="btn btn-ghost" style={{ flex: 1 }} onClick={onClose}>İptal</button>
        <button className="btn btn-primary" style={{ flex: 1, opacity: valid ? 1 : 0.45 }}
          onClick={handleSave} disabled={!valid}>{initial ? "Kaydet" : "Oluştur"}</button>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   GROUP FORM & MODAL
   ══════════════════════════════════════════════════════════════════ */

function GroupForm({ initial, channels, onSave, onClose }) {
  const [name, setName] = useState(initial ? initial.name : "");
  const [topicCategory, setTopicCategory] = useState(initial ? initial.topic_category : "reddit_stories");
  const [selectedIds, setSelectedIds] = useState(initial ? initial.channel_ids || [] : []);
  const [redditAvatarPath, setRedditAvatarPath] = useState(initial ? initial.reddit_avatar_path || null : null);
  const [redditUsername, setRedditUsername] = useState(initial ? initial.reddit_username || "" : "");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  // Sadece seçili kategoriyle uyumlu kanalları filtrele
  const compatibleChannels = channels.filter(
    c => (c.topic_category || "").toLowerCase().trim() === topicCategory.toLowerCase().trim()
  );

  const toggleChannelSelection = (cid) => {
    setError(null);
    setSelectedIds(prev =>
      prev.includes(cid) ? prev.filter(id => id !== cid) : [...prev, cid]
    );
  };

  const handleCategoryChange = (newCat) => {
    setTopicCategory(newCat);
    // Kategori değiştiğinde uyumsuz seçilmiş kanalları temizle
    setSelectedIds(prev => {
      const validForNewCat = channels
        .filter(c => (c.topic_category || "").toLowerCase().trim() === newCat.toLowerCase().trim())
        .map(c => c.channel_id);
      return prev.filter(id => validForNewCat.includes(id));
    });
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Lütfen bir grup adı girin.");
      return;
    }
    if (selectedIds.length < 1) {
      setError("Lütfen gruba en az bir kanal dahil edin.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSave({
        name: name.trim(),
        topic_category: topicCategory,
        channel_ids: selectedIds,
        reddit_avatar_path: redditAvatarPath || null,
        reddit_username: redditUsername.trim() || null,
        id: initial ? initial.id : undefined,
      });
    } catch (err) {
      setError(err.message || "Grup kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {error && (
        <div style={{
          padding: "10px 14px", background: "rgba(239,68,68,0.15)",
          border: "1px solid rgba(239,68,68,0.3)", borderRadius: "var(--radius-md)",
          color: "#f87171", fontSize: 12.5, lineHeight: 1.5
        }}>
          ⚠️ {error}
        </div>
      )}

      <div style={{
        padding: "10px 14px", background: "rgba(124,110,242,0.08)",
        border: "1px solid rgba(124,110,242,0.2)", borderRadius: "var(--radius-md)",
        fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5
      }}>
        💡 <strong>Kanal Gruplama Kuralı:</strong> Bir gruptaki kanalların tamamı <em>aynı konu kategorisine</em> sahip olmalı ve gruba eklenmeden önce bireysel içerik planları boş olmalıdır. Grup üyeleri tek bir ortak içerik planı ve çok dilli üretim motoru paylaşır.
      </div>

      <div className="form-group">
        <label className="form-label">Grup Adı *</label>
        <input
          className="form-input"
          placeholder="Örn: Reddit Hikayeleri Global Grubu"
          value={name}
          onChange={e => setName(e.target.value)}
          required
        />
      </div>

      <div className="form-group">
        <label className="form-label">Konu Kategorisi *</label>
        <select
          className="form-input"
          value={topicCategory}
          onChange={e => handleCategoryChange(e.target.value)}
          disabled={!!initial}
        >
          <option value="basketball_analysis">Basketbol Analizi (The Basketball Show & NBA)</option>
          <option value="music">Biyo-AI Müzik - Sinek Beyni (music)</option>
          <option value="reddit_stories">Reddit Hikayeleri (reddit_stories)</option>
          <option value="whatsapp_stories">WhatsApp Mesajlaşma (whatsapp_stories)</option>
          <option value="space">Uzay ve Astronomi (space)</option>
          <option value="aviation">Havacılık Olayları (aviation)</option>
          <option value="crayon_combat">Askeri Araçlar & Çöp Adam Hicvi (crayon_combat)</option>
          <option value="tech_finance_essay">Teknoloji & Finans Belgeseli (tech_finance_essay)</option>
          <option value="travel">Seyahat ve Keşif (travel)</option>
          <option value="story">Masal & Hikaye (story)</option>
        </select>
        {initial && (
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
            Mevcut grubun konusu değiştirilemez.
          </span>
        )}
      </div>

      {topicCategory === "reddit_stories" && (
        <div style={{
          padding: "14px 16px", background: "rgba(255, 69, 0, 0.05)",
          border: "1px solid rgba(255, 69, 0, 0.25)", borderRadius: "var(--radius-md)",
          display: "flex", flexDirection: "column", gap: 12
        }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#ff4500", display: "flex", alignItems: "center", gap: 6 }}>
              <span>🤖</span> Reddit Başlık Kartı & Avatar Ayarları (Grup Ortak)
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 2 }}>
              Gruptaki tüm kanalların videolarında kullanılacak profil fotoğrafı ve kullanıcı adı.
            </div>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: 12 }}>Reddit Kullanıcı Adı (Yazar)</label>
            <input
              className="form-input"
              placeholder="Boş bırakılırsa her kanalın diline özel otomatik yazar atanır (örn. u/Ahmet, u/Hans)"
              value={redditUsername}
              onChange={e => setRedditUsername(e.target.value)}
            />
          </div>

          <div>
            <FileUploader
              label="Reddit Profil Fotoğrafı (Avatar)"
              value={redditAvatarPath}
              category="watermark"
              placeholder="Grup geneli profil fotoğrafı (Boş ise resmi Reddit logosu)"
              onChange={val => setRedditAvatarPath(val)}
            />
          </div>
        </div>
      )}

      <div className="form-group">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <label className="form-label" style={{ margin: 0 }}>Gruba Eklenecek Kanallar *</label>
          <span style={{ fontSize: 11.5, color: "var(--text-muted)" }}>
            {selectedIds.length} kanal seçildi
          </span>
        </div>

        {compatibleChannels.length === 0 ? (
          <div style={{
            padding: "16px", textAlign: "center", background: "rgba(255,255,255,0.02)",
            border: "1px dashed var(--border-subtle)", borderRadius: "var(--radius-md)",
            fontSize: 12.5, color: "var(--text-muted)"
          }}>
            Bu kategoriye ({topicCategory}) sahip kayıtlı kanal bulunamadı. Önce bu kategoride kanallar oluşturun.
          </div>
        ) : (
          <div style={{
            display: "flex", flexDirection: "column", gap: 8,
            maxHeight: 220, overflowY: "auto", padding: "4px"
          }}>
            {compatibleChannels.map(ch => {
              const isChecked = selectedIds.includes(ch.channel_id);
              const lang = getLang(ch.language);
              return (
                <div
                  key={ch.channel_id}
                  onClick={() => toggleChannelSelection(ch.channel_id)}
                  style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "8px 12px", borderRadius: "var(--radius-md)",
                    background: isChecked ? "var(--accent-muted)" : "rgba(255,255,255,0.02)",
                    border: isChecked ? "1px solid var(--accent-primary)" : "1px solid var(--border-subtle)",
                    cursor: "pointer", transition: "all 0.12s ease"
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => {}}
                    style={{ accentColor: "var(--accent-primary)", cursor: "pointer" }}
                  />
                  <span style={{ fontSize: 15 }}>{lang?.flag || "🌍"}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: isChecked ? "var(--text-primary)" : "var(--text-secondary)" }}>
                      {ch.name}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {ch.channel_id} · Dil: {ch.language.toUpperCase()}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8, paddingTop: 14, borderTop: "1px solid var(--border-subtle)" }}>
        <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>
          İptal
        </button>
        <button type="submit" className="btn btn-primary" disabled={saving || compatibleChannels.length === 0}>
          {saving ? "Kaydediliyor..." : initial ? "Grubu Güncelle" : "Grup Oluştur"}
        </button>
      </div>
    </form>
  );
}


/* ══════════════════════════════════════════════════════════════════
   TASK TOAST
   ══════════════════════════════════════════════════════════════════ */

function TaskToast({ task, onDismiss }) {
  const isRunning = task.status === "pending" || task.status === "running";
  const isSuccess = task.status === "success";
  const isPartial = task.status === "partial";
  const isFailed  = task.status === "failed";
  return (
    <div className="task-toast">
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {isRunning ? (
            <Loader2 size={16} className="spin" style={{ color: "var(--accent-primary)", flexShrink: 0 }} />
          ) : isSuccess ? (
            <CheckCircle2 size={16} style={{ color: "var(--success)", flexShrink: 0 }} />
          ) : isPartial ? (
            <AlertCircle size={16} style={{ color: "#f59e0b", flexShrink: 0 }} />
          ) : (
            <AlertCircle size={16} style={{ color: "var(--danger)", flexShrink: 0 }} />
          )}
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>
              {isRunning ? "Video üretiliyor…" : isSuccess ? "Tamamlandı" : isPartial ? "Kısmen Tamamlandı" : "Başarısız"}
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-muted)" }}>{task.channelId}</div>
          </div>
        </div>
        {(isSuccess || isFailed || isPartial) && (
          <button className="modal-close" onClick={onDismiss} style={{ padding: 2 }}>
            <X size={14} />
          </button>
        )}
      </div>
      {task.message && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.4 }}>{task.message}</div>}
      <div className={`progress-bar-track ${isRunning ? "progress-bar-indeterminate" : ""}`} style={{ marginTop: 8 }}>
        <div className="progress-bar-fill" style={{
          width: isRunning ? "45%" : "100%",
          background: isFailed ? "var(--danger)" : isPartial ? "#f59e0b" : isSuccess ? "var(--success)" : undefined
        }} />
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   SETTINGS PAGE
   ══════════════════════════════════════════════════════════════════ */

function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/settings").then(r => r.json()).then(data => {
      setSettings(data);
      setForm({
        anthropic_api_key: "", gemini_api_key: "", nasa_api_key: "",
        ai_provider: data.ai_provider || "claude",
        ai_model: data.ai_model || "",
        ollama_url: data.ollama_url || "http://localhost:11434",
        ollama_model: data.ollama_model || "llama3",
        lmstudio_url: data.lmstudio_url || "http://localhost:1234/v1",
        lmstudio_model: data.lmstudio_model || "",
        output_dir: data.output_dir || "output",
        tts_engine: data.tts_engine || "edge-tts",
        chatterbox_voice: data.chatterbox_voice || "",
        remote_tts_engine: data.remote_tts_engine || "chatterbox",
        kokoro_voice: data.kokoro_voice || "am_michael",
        kokoro_speed: data.kokoro_speed || "0.94",
        subtitle_preset: data.subtitle_preset || "bold",
        subtitle_animation: data.subtitle_animation || "fade",
        bgm_path: data.bgm_path || "",
        bgm_volume: data.bgm_volume || "0.15",
        watermark_path: data.watermark_path || "",
        watermark_text: data.watermark_text || "",
        watermark_position: data.watermark_position || "top-right",
        intro_clip_path: data.intro_clip_path || "",
        censor_logo_path: data.censor_logo_path || "",
        outro_clip_path: data.outro_clip_path || "",
        kenburns_intensity: data.kenburns_intensity || "0.04",
        transition_dur: data.transition_dur || "0.5",
        video_duration: data.video_duration || "120",
        censor_faces: data.censor_faces !== undefined ? data.censor_faces : true,
        auto_editor: data.auto_editor !== undefined ? data.auto_editor : false,
        censor_custom_landscape_enabled: data.censor_custom_landscape_enabled !== undefined ? data.censor_custom_landscape_enabled : false,
        censor_custom_landscape_x: data.censor_custom_landscape_x !== undefined ? data.censor_custom_landscape_x : 0,
        censor_custom_landscape_y: data.censor_custom_landscape_y !== undefined ? data.censor_custom_landscape_y : 0,
        censor_custom_landscape_w: data.censor_custom_landscape_w !== undefined ? data.censor_custom_landscape_w : 0,
        censor_custom_landscape_h: data.censor_custom_landscape_h !== undefined ? data.censor_custom_landscape_h : 0,
        censor_custom_landscape_image_path: data.censor_custom_landscape_image_path || "",
        censor_custom_portrait_enabled: data.censor_custom_portrait_enabled !== undefined ? data.censor_custom_portrait_enabled : false,
        censor_custom_portrait_x: data.censor_custom_portrait_x !== undefined ? data.censor_custom_portrait_x : 0,
        censor_custom_portrait_y: data.censor_custom_portrait_y !== undefined ? data.censor_custom_portrait_y : 0,
        censor_custom_portrait_w: data.censor_custom_portrait_w !== undefined ? data.censor_custom_portrait_w : 0,
        censor_custom_portrait_h: data.censor_custom_portrait_h !== undefined ? data.censor_custom_portrait_h : 0,
        censor_custom_portrait_image_path: data.censor_custom_portrait_image_path || "",
      });
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true); setSaved(false);
    const payload = {};
    for (const [k, v] of Object.entries(form)) {
      if (v !== "" || !["anthropic_api_key", "gemini_api_key", "nasa_api_key"].includes(k)) {
        payload[k] = v;
      }
    }
    // Boş API key'leri gönderme
    ["anthropic_api_key", "gemini_api_key", "nasa_api_key"].forEach(k => {
      if (!form[k]) delete payload[k];
    });
    try {
      const res = await fetch("/api/settings", {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
        setForm(f => ({ ...f, anthropic_api_key: "", gemini_api_key: "", nasa_api_key: "",
          ai_provider: data.ai_provider, ai_model: data.ai_model || "",
          ollama_url: data.ollama_url, ollama_model: data.ollama_model,
          lmstudio_url: data.lmstudio_url || "http://localhost:1234/v1",
          lmstudio_model: data.lmstudio_model || "",
          output_dir: data.output_dir,
          tts_engine: data.tts_engine,
          chatterbox_voice: data.chatterbox_voice || "",
          remote_tts_engine: data.remote_tts_engine || "chatterbox",
          kokoro_voice: data.kokoro_voice || "am_michael",
          kokoro_speed: data.kokoro_speed || "0.94",
          subtitle_preset: data.subtitle_preset || "bold",
          subtitle_animation: data.subtitle_animation || "fade",
          bgm_path: data.bgm_path || "",
          bgm_volume: data.bgm_volume || "0.15",
          watermark_path: data.watermark_path || "",
          watermark_text: data.watermark_text || "",
          watermark_position: data.watermark_position || "top-right",
          intro_clip_path: data.intro_clip_path || "",
          censor_logo_path: data.censor_logo_path || "",
          outro_clip_path: data.outro_clip_path || "",
          kenburns_intensity: data.kenburns_intensity || "0.04",
          transition_dur: data.transition_dur || "0.5",
          video_duration: data.video_duration || "120",
          censor_faces: data.censor_faces !== undefined ? data.censor_faces : true,
          auto_editor: data.auto_editor !== undefined ? data.auto_editor : false,
          censor_custom_landscape_enabled: data.censor_custom_landscape_enabled !== undefined ? data.censor_custom_landscape_enabled : false,
          censor_custom_landscape_x: data.censor_custom_landscape_x !== undefined ? data.censor_custom_landscape_x : 0,
          censor_custom_landscape_y: data.censor_custom_landscape_y !== undefined ? data.censor_custom_landscape_y : 0,
          censor_custom_landscape_w: data.censor_custom_landscape_w !== undefined ? data.censor_custom_landscape_w : 0,
          censor_custom_landscape_h: data.censor_custom_landscape_h !== undefined ? data.censor_custom_landscape_h : 0,
          censor_custom_landscape_image_path: data.censor_custom_landscape_image_path || "",
          censor_custom_portrait_enabled: data.censor_custom_portrait_enabled !== undefined ? data.censor_custom_portrait_enabled : false,
          censor_custom_portrait_x: data.censor_custom_portrait_x !== undefined ? data.censor_custom_portrait_x : 0,
          censor_custom_portrait_y: data.censor_custom_portrait_y !== undefined ? data.censor_custom_portrait_y : 0,
          censor_custom_portrait_w: data.censor_custom_portrait_w !== undefined ? data.censor_custom_portrait_w : 0,
          censor_custom_portrait_h: data.censor_custom_portrait_h !== undefined ? data.censor_custom_portrait_h : 0,
          censor_custom_portrait_image_path: data.censor_custom_portrait_image_path || "",
        }));
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch {}
    setSaving(false);
  };

  if (!settings) return <div style={{ padding: 40, color: "var(--text-muted)" }}>Yükleniyor…</div>;

  const providerNeedsKey = {
    claude: "anthropic_api_key",
    gemini: "gemini_api_key",
    ollama: null,
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Ayarlar</h2>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 5 }}>
          API anahtarları şifreli olarak saklanır. Mevcut değeri korumak için alanı boş bırakın.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

        {/* ── AI Provider Selection ────────────────────────── */}
        <div className="card" style={{ padding: "18px 20px" }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>
            Yapay Zeka Modeli
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {AI_PROVIDERS.map(p => (
              <label key={p.id} style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "12px 14px", borderRadius: "var(--radius-md)",
                background: form.ai_provider === p.id ? "var(--accent-muted)" : "var(--bg-primary)",
                border: `1px solid ${form.ai_provider === p.id ? "var(--accent-border)" : "var(--border-subtle)"}`,
                cursor: "pointer", transition: "all 0.15s",
              }}>
                <input type="radio" name="provider" value={p.id}
                  checked={form.ai_provider === p.id}
                  onChange={() => setForm(f => ({ ...f, ai_provider: p.id }))}
                  style={{ accentColor: "var(--accent-primary)" }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{p.name}</div>
                  <div style={{ fontSize: 11.5, color: "var(--text-muted)" }}>{p.desc}</div>
                </div>
                {providerNeedsKey[p.id] && settings[`${providerNeedsKey[p.id]}_set`] && (
                  <span className="chip chip-success" style={{ fontSize: 10, marginLeft: "auto" }}>Key Var</span>
                )}
              </label>
            ))}
          </div>
        </div>

        {/* ── LM Studio Settings (conditional) ────────────── */}
        {form.ai_provider === "lmstudio" && (
          <div className="card" style={{ padding: "18px 20px" }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 10 }}>
              LM Studio Yapılandırması
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12, lineHeight: 1.6 }}>
              LM Studio'yu açın → <strong>Local Server</strong> sekmesi → <strong>Start Server</strong> butonuna basın.
              Model listesinden bir model seçin ve
              <code style={{ background: "var(--bg-primary)", padding: "1px 5px", borderRadius: 3, fontSize: 11, color: "var(--text-accent)" }}> Load Model</code>
              butonuna tıklayın.
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Sunucu URL</label>
                <input className="form-input" value={form.lmstudio_url}
                  onChange={e => setForm(f => ({ ...f, lmstudio_url: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Model ID (opsiyonel)</label>
                <input className="form-input" placeholder="Boş bırak = aktif model"
                  value={form.lmstudio_model}
                  onChange={e => setForm(f => ({ ...f, lmstudio_model: e.target.value }))} />
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                  LM Studio arayüzünde görünen model ID'sini girin.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Ollama Settings (conditional) ──────────────────── */}
        {form.ai_provider === "ollama" && (
          <div className="card" style={{ padding: "18px 20px" }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 10 }}>
              Ollama Yapılandırması
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Sunucu URL</label>
                <input className="form-input" value={form.ollama_url}
                  onChange={e => setForm(f => ({ ...f, ollama_url: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Model Adı</label>
                <input className="form-input" placeholder="llama3, mistral, gemma2..."
                  value={form.ollama_model}
                  onChange={e => setForm(f => ({ ...f, ollama_model: e.target.value }))} />
              </div>
            </div>
          </div>
        )}

        {/* ── Custom Model Override ──────────────────────────── */}
        {form.ai_provider !== "ollama" && (
          <div className="card" style={{ padding: "18px 20px" }}>
            <div className="form-group">
              <label className="form-label">Model Adı (opsiyonel)</label>
              <input className="form-input" placeholder="Boş bırakın = varsayılan model"
                value={form.ai_model}
                onChange={e => setForm(f => ({ ...f, ai_model: e.target.value }))} />
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                Claude: claude-sonnet-4-20250514 · Gemini: gemini-2.5-flash
              </div>
            </div>
          </div>
        )}

        {/* ── API Keys ──────────────────────────────────────── */}
        {[
          { key: "anthropic_api_key", label: "Anthropic API Key", desc: "Claude modelleri için — console.anthropic.com", show: true },
          { key: "gemini_api_key", label: "Gemini API Key", desc: "Google Gemini için — aistudio.google.com", show: true },
          { key: "nasa_api_key", label: "NASA API Key", desc: "Uzay görselleri için — api.nasa.gov", show: true },
        ].map(f => (
          <div key={f.key} className="card" style={{ padding: "18px 20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{f.label}</label>
              {settings[`${f.key}_set`] && <span className="chip chip-success" style={{ fontSize: 10 }}>Ayarlanmış</span>}
            </div>
            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 10px", lineHeight: 1.5 }}>{f.desc}</p>
            {settings[`${f.key}_set`] && (
              <div style={{
                fontSize: 11.5, fontFamily: "'JetBrains Mono', monospace",
                color: "var(--text-muted)", marginBottom: 8,
                padding: "4px 8px", background: "var(--bg-primary)",
                borderRadius: 4, display: "inline-block", border: "1px solid var(--border-subtle)"
              }}>{settings[f.key]}</div>
            )}
            <input type="password" className="form-input" placeholder="Yeni değer girin…"
              value={form[f.key]} autoComplete="off"
              onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))} />
          </div>
        ))}

        {/* ── Output Dir ────────────────────────────────────── */}
        <div className="card" style={{ padding: "18px 20px" }}>
          <div className="form-group">
            <label className="form-label">Çıktı Dizini</label>
            <input className="form-input" value={form.output_dir}
              onChange={e => setForm(f => ({ ...f, output_dir: e.target.value }))} />
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              Her video için ayrı klasör oluşturulur: output/kanal_id_tarih/
            </div>
          </div>
        </div>

        {/* ── Gerçekçi Yerel Ses Klonlama Stüdyosu ───────────────── */}
        <VoiceCloneStudio
          onVoiceActivated={(newVoiceId) => {
            fetch("/api/settings")
              .then((r) => r.json())
              .then((data) => {
                setSettings(data);
                setForm((f) => ({
                  ...f,
                  tts_engine: data.tts_engine || "chatterbox",
                  chatterbox_voice: data.chatterbox_voice || "",
                  active_voice_clone_id: data.active_voice_clone_id || newVoiceId,
                }));
              })
              .catch(() => {});
          }}
        />

        {/* ── TTS Engine ────────────────────────────────────── */}
        <div className="card" style={{ padding: "18px 20px" }}>
          <div className="form-group">
            <label className="form-label">Seslendirme (TTS) Sistemi</label>
            <select className="form-input" value={form.tts_engine}
              onChange={e => setForm(f => ({ ...f, tts_engine: e.target.value }))}>
              <option value="chatterbox">Chatterbox / Yerel Klonlanmış Ses (Önerilen - Sıfır Maliyet)</option>
              <option value="edge-tts">Edge TTS (Bulut / Ücretsiz)</option>
            </select>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              {form.tts_engine === "chatterbox"
                ? "Apple Silicon MPS ile yerelde yüksek gerçekçilikte ses üretilir. Yukarıda seçtiğiniz klon ses tüm video üretimlerinde konuşur."
                : "Microsoft Edge bulut sesleri kullanılır."}
            </div>
          </div>

          {form.tts_engine === "chatterbox" && (
            <div className="form-group" style={{ marginTop: 14 }}>
              <label className="form-label">Aktif Klon Dosya Yolu</label>
              <input className="form-input" placeholder="Yukarıdaki stüdyodan bir ses seçtiğinizde otomatik doldurulur"
                value={form.chatterbox_voice || ""}
                onChange={e => setForm(f => ({ ...f, chatterbox_voice: e.target.value }))} />
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                Sistem yukarıdaki ses klonlama stüdyosunda seçtiğiniz <code>.pt</code> / <code>.wav</code> profilini kullanır.
              </div>
            </div>
          )}
        </div>

        <div className="card" style={{ padding: "18px 20px", marginTop: 12 }}>
          <div className="form-group">
            <label className="form-label">Uzak Sunucu Seslendirmesi</label>
            <select className="form-input" value={form.remote_tts_engine || "chatterbox"}
              onChange={e => setForm(f => ({ ...f, remote_tts_engine: e.target.value }))}>
              <option value="chatterbox">Chatterbox (iyileştirilmiş anlatım ayarları)</option>
              <option value="kokoro">Kokoro-TTS (doğal anlatıcı sesi)</option>
            </select>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              Bundan sonra kuyruğa gönderilecek sunucu videolarında kullanılır. Kokoro İngilizce, İspanyolca, Fransızca, Hintçe, İtalyanca, Japonca, Portekizce ve Çinceyi destekler; desteklenmeyen diller havacılık işlerinde Chatterbox'a, diğer video işlerinde Edge TTS'e döner.
            </div>
          </div>

          {form.remote_tts_engine === "kokoro" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label className="form-label">İngilizce Anlatıcı Sesi</label>
                <select className="form-input" value={form.kokoro_voice || "am_michael"}
                  onChange={e => setForm(f => ({ ...f, kokoro_voice: e.target.value }))}>
                  <option value="am_michael">Michael — erkek, belgesel anlatımı</option>
                  <option value="am_fenrir">Fenrir — erkek, tok ton</option>
                  <option value="af_bella">Bella — kadın, net anlatım</option>
                  <option value="af_heart">Heart — kadın, sıcak ton</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Konuşma Hızı ({form.kokoro_speed || "0.94"}×)</label>
                <input type="number" className="form-input" min="0.8" max="1.2" step="0.01"
                  value={form.kokoro_speed || "0.94"}
                  onChange={e => setForm(f => ({ ...f, kokoro_speed: e.target.value }))} />
              </div>
            </div>
          )}
        </div>

        {/* ── Video Tasarımı ve Süresi ──────────────────────── */}
        <div className="card" style={{ padding: "18px 20px" }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>
            Video Tasarımı ve Süresi
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Varsayılan Video Süresi (Saniye)</label>
              <input type="number" className="form-input" min="5" max="3600"
                value={form.video_duration || ""}
                onChange={e => setForm(f => ({ ...f, video_duration: e.target.value }))} />
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                Shorts videolarında otomatik olarak maks 60 saniyeye çekilir.
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Görsel Geçiş Süresi (Saniye)</label>
              <input type="number" step="0.1" className="form-input" min="0.1" max="5.0"
                value={form.transition_dur || ""}
                onChange={e => setForm(f => ({ ...f, transition_dur: e.target.value }))} />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
            <div className="form-group">
              <label className="form-label">Altyazı Stili (Preset)</label>
              <select className="form-input" value={form.subtitle_preset || ""}
                onChange={e => setForm(f => ({ ...f, subtitle_preset: e.target.value }))}>
                <option value="minimal">Minimal (İnce Yazı)</option>
                <option value="bold">Bold (Kalın Gölgeli)</option>
                <option value="tiktok">Tiktok Style (Sarı Vurgulu)</option>
                <option value="youtube-classic">YouTube Klasik (Siyah Bantlı)</option>
                <option value="news">Haber Kanalı (Alt Şerit)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Altyazı Animasyonu</label>
              <select className="form-input" value={form.subtitle_animation || ""}
                onChange={e => setForm(f => ({ ...f, subtitle_animation: e.target.value }))}>
                <option value="none">Yok (Statik)</option>
                <option value="fade">Fade (Yavaşça belirme)</option>
                <option value="pop">Pop (Zıplama efekti)</option>
                <option value="typewriter">Daktilo (Karakter karakter)</option>
                <option value="word-highlight">Vurgulu (Sırayla kelime boyama)</option>
              </select>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
            <div className="form-group">
              <label className="form-label">Ken Burns (Zoom) Yoğunluğu</label>
              <input type="number" step="0.01" className="form-input" min="0.0" max="0.2"
                value={form.kenburns_intensity || ""}
                onChange={e => setForm(f => ({ ...f, kenburns_intensity: e.target.value }))} />
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                0.00: Pasif, 0.04: Normal, 0.10: Yüksek Zoom
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Yüz Sansürleme (Global)</label>
              <div style={{ display: "flex", alignItems: "center", gap: 10, height: "38px" }}>
                <Toggle checked={!!form.censor_faces} onChange={v => setForm(f => ({ ...f, censor_faces: v }))} />
                <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  Görsellerdeki insan yüzlerini otomatik sansürle (blur)
                </span>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Auto-Editor (Sessizlik Silme - Global)</label>
              <div style={{ display: "flex", alignItems: "center", gap: 10, height: "38px" }}>
                <Toggle checked={!!form.auto_editor} onChange={v => setForm(f => ({ ...f, auto_editor: v }))} />
                <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  Videolardaki sessiz/ölü alanları otomatik temizle
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Medya & Müzik Ayarları ─────────────────────────── */}
        <div className="card" style={{ padding: "18px 20px" }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>
            Arka Plan Müzik ve Filigran
          </div>
          <FileUploader
            label="Varsayılan Arka Plan Müziği (BGM)"
            value={form.bgm_path}
            category="bgm"
            onChange={val => setForm(f => ({ ...f, bgm_path: val }))}
          />
          {form.bgm_path && (
            <div className="form-group">
              <label className="form-label">BGM Ses Seviyesi</label>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input type="range" min="0" max="1" step="0.05"
                  value={form.bgm_volume || "0.15"}
                  onChange={e => setForm(f => ({ ...f, bgm_volume: e.target.value }))}
                  style={{ flex: 1, accentColor: "var(--accent-primary)" }} />
                <span style={{ fontSize: 12, fontFamily: "monospace", width: 35 }}>
                  {Math.round((form.bgm_volume || 0.15) * 100)}%
                </span>
              </div>
            </div>
          )}

          <div style={{ borderTop: "1px solid var(--border-subtle)", margin: "14px 0", paddingTop: 14 }}>
            <FileUploader
              label="Varsayılan Logo / Filigran Görseli"
              value={form.watermark_path}
              category="watermark"
              onChange={val => setForm(f => ({ ...f, watermark_path: val }))}
            />
            <div style={{ marginTop: 12 }}>
              <FileUploader
                label="Varsayılan NASA Logo Sansür Görseli"
                value={form.censor_logo_path}
                category="watermark"
                onChange={val => setForm(f => ({ ...f, censor_logo_path: val }))}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label className="form-label">Filigran Yazısı (Görsel yoksa)</label>
                <input className="form-input" placeholder="Ör: @kanalismi"
                  value={form.watermark_text || ""}
                  onChange={e => setForm(prev => ({ ...prev, watermark_text: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Filigran Pozisyonu</label>
                <select className="form-input" value={form.watermark_position || "top-right"}
                  onChange={e => setForm(prev => ({ ...prev, watermark_position: e.target.value }))}>
                  <option value="top-left">Sol Üst</option>
                  <option value="top-right">Sağ Üst</option>
                  <option value="bottom-left">Sol Alt</option>
                  <option value="bottom-right">Sağ Alt</option>
                  <option value="bottom-center">Alt Orta</option>
                </select>
              </div>
            </div>
          </div>
        </div>



        {/* ── Giriş & Çıkış Videoları ────────────────────────── */}
        <div className="card" style={{ padding: "18px 20px" }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>
            Kanal Giriş ve Çıkış Videoları (Intro & Outro)
          </div>
          <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 14px", lineHeight: 1.5 }}>
            Shorts videolarında intro ve outro video süreleri toplam 60 saniyelik sınırdan otomatik olarak düşülür ve senaryo süresi kalan süreye göre ayarlanır.
          </p>
          <FileUploader
            label="Varsayılan Intro Klibi"
            value={form.intro_clip_path}
            category="intro"
            onChange={val => setForm(f => ({ ...f, intro_clip_path: val }))}
          />
          <FileUploader
            label="Varsayılan Outro Klibi"
            value={form.outro_clip_path}
            category="outro"
            onChange={val => setForm(f => ({ ...f, outro_clip_path: val }))}
          />
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}
            style={{ opacity: saving ? 0.6 : 1 }}>
            {saving ? "Kaydediliyor…" : "Ayarları Kaydet"}
          </button>
          {saved && <span style={{ fontSize: 12, color: "var(--success)" }}>✓ Başarıyla kaydedildi</span>}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   SİNEK BEYNİ (DROSOPHILA CONNECTOME) BİYO-AI MÜZİK STÜDYOSU
   ══════════════════════════════════════════════════════════════════ */

const SINEK_GENRES = [
  { id: "emotional", name: "Emotional & Melancholic", sub: "Nocturne • F Minor • 90 BPM", icon: "🎹" },
  { id: "romantic", name: "Romantic & Passionate", sub: "Symphony • C Minor • 96 BPM", icon: "🎻" },
  { id: "epic", name: "Epic & Triumphant", sub: "Anthem • D Minor • 110 BPM", icon: "⚔️" },
  { id: "peaceful", name: "Peaceful & Meditative", sub: "Ambient • C Major • 72 BPM", icon: "🌿" },
  { id: "mysterious", name: "Mysterious & Cinematic", sub: "Suspense • D Minor • 82 BPM", icon: "🔮" },
  { id: "jazz", name: "Midnight Jazz & Neo-Soul", sub: "Neo-Soul • Eb Major • 85 BPM", icon: "🎷" },
  { id: "baroque", name: "Baroque & Polyphonic", sub: "Bach Polyphony • G Minor • 100 BPM", icon: "🎼" },
  { id: "oriental", name: "Mystical Orient", sub: "Hijaz Harmonics • A Phrygian • 88 BPM", icon: "🏜️" },
  { id: "rock", name: "Hard Rock & Distortion", sub: "Kinetic Rock • E Minor • 128 BPM", icon: "🎸" },
  { id: "rap", name: "808 Trap & Hip-Hop", sub: "Urban Flow • C Minor • 136 BPM", icon: "🔥" },
  { id: "pop", name: "Synthpop & Modern Groove", sub: "Synthwave • A Minor • 120 BPM", icon: "🪩" },
];

const SINEK_THEMES = [
  { id: "cosmic", name: "🌌 Kozmik Nebula", desc: "Mor/mavi nöral ağ derinliği ve yıldız parçacıkları" },
  { id: "cyberpunk", name: "⚡ Siberpunk Neon", desc: "Camgöbeği & macenta yüksek kontrastlı sinaps ışımaları" },
  { id: "biophilic", name: "🌿 Biyofilik Doku", desc: "Zümrüt tonlarında organik canlı sinir dokusu ve lifler" },
];

function SinekBeyniStudio({ channel, onProduceConnectome, runningTask }) {
  const [genre, setGenre] = useState(channel.edit_options?.music_genre || "emotional");
  const [isVertical, setIsVertical] = useState(Boolean(channel.shorts_mode));
  const [duration, setDuration] = useState(
    channel.edit_options?.music_duration 
      ? Number(channel.edit_options.music_duration) 
      : (channel.shorts_mode ? 45 : 180)
  );
  const [theme, setTheme] = useState(channel.edit_options?.music_theme || "cosmic");

  const isCurrentTaskRunning = runningTask && runningTask.channelId === channel.channel_id;

  const handleFormatSelect = (vertical) => {
    setIsVertical(vertical);
    if (vertical && duration > 60) {
      setDuration(45);
    } else if (!vertical && duration < 120) {
      setDuration(180);
    }
  };

  const handleTriggerProduce = () => {
    if (onProduceConnectome) {
      onProduceConnectome(channel.channel_id, {
        genre,
        duration: Number(duration),
        theme,
        is_vertical: isVertical
      });
    }
  };

  const formatMinSec = (sec) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m > 0 ? `${m} dk ` : ""}${s > 0 ? `${s} sn` : (m > 0 ? "" : "0 sn")}`;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Studio Header Card */}
      <div className="card" style={{
        padding: "18px 20px",
        background: "linear-gradient(135deg, rgba(168, 85, 247, 0.09) 0%, rgba(59, 130, 246, 0.05) 100%)",
        border: "1px solid rgba(168, 85, 247, 0.25)",
        borderRadius: "var(--radius-lg, 12px)",
        position: "relative",
        overflow: "hidden"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: 20 }}>🧠</span>
              <span style={{
                fontSize: 14,
                fontWeight: 700,
                letterSpacing: "0.04em",
                color: "#f3e8ff",
                textTransform: "uppercase"
              }}>
                SİNEK BEYNİ // BİYO-AI MÜZİK STÜDYOSU
              </span>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0, lineHeight: 1.5 }}>
              139.255 canlı nöronlu Drosophila Connectome simülasyonu ile 3-5 dakikalık avangart akustik piyano & senfonik klipler üretin.
            </p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
            <span className="chip" style={{
              background: "rgba(168, 85, 247, 0.2)",
              color: "#d8b4fe",
              border: "1px solid rgba(168, 85, 247, 0.4)",
              fontSize: 10,
              padding: "2px 8px",
              fontWeight: 600,
              letterSpacing: "0.03em"
            }}>
              ⚡ LM STUDIO AI HAZIR
            </span>
            <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "monospace" }}>
              Princeton FlyWire
            </span>
          </div>
        </div>
      </div>

      {/* Müzik Türü Seçimi */}
      <div className="card" style={{ padding: "16px 18px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
            🎵 Biyolojik Müzik Türü (11 Akustik Ensemble)
          </span>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Seçilen: <strong style={{ color: "#d8b4fe" }}>{SINEK_GENRES.find(g => g.id === genre)?.name}</strong>
          </span>
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: 8,
          maxHeight: 250,
          overflowY: "auto",
          paddingRight: 4
        }}>
          {SINEK_GENRES.map(g => {
            const isSelected = genre === g.id;
            return (
              <button
                key={g.id}
                type="button"
                onClick={() => setGenre(g.id)}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "flex-start",
                  padding: "9px 11px",
                  background: isSelected ? "rgba(168, 85, 247, 0.16)" : "var(--bg-secondary, rgba(255,255,255,0.02))",
                  border: isSelected ? "1px solid #a855f7" : "1px solid var(--border-subtle, rgba(255,255,255,0.06))",
                  borderRadius: "var(--radius-md, 8px)",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.15s ease",
                  boxShadow: isSelected ? "0 0 10px rgba(168, 85, 247, 0.25)" : "none",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                  <span style={{ fontSize: 14 }}>{g.icon}</span>
                  <span style={{
                    fontSize: 12,
                    fontWeight: isSelected ? 700 : 600,
                    color: isSelected ? "#f3e8ff" : "var(--text-primary)"
                  }}>
                    {g.name}
                  </span>
                </div>
                <span style={{ fontSize: 10, color: isSelected ? "#d8b4fe" : "var(--text-muted)", fontFamily: "monospace" }}>
                  {g.sub}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Video Formatı & Klip Süresi */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Format */}
        <div className="card" style={{ padding: "16px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
          <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>
            📐 Video Formatı
          </span>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <button
              type="button"
              onClick={() => handleFormatSelect(false)}
              style={{
                padding: "10px 8px",
                fontSize: 11.5,
                fontWeight: !isVertical ? 700 : 500,
                borderRadius: "var(--radius-sm, 6px)",
                border: !isVertical ? "1px solid var(--accent-primary)" : "1px solid var(--border-subtle)",
                background: !isVertical ? "rgba(99, 102, 241, 0.16)" : "transparent",
                color: !isVertical ? "#e0e7ff" : "var(--text-secondary)",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 4
              }}
            >
              <span style={{ fontSize: 16 }}>🖥️</span>
              <span>16:9 Yatay Klip</span>
              <span style={{ fontSize: 9.5, color: "var(--text-muted)" }}>1920x1080 (3-5 dk)</span>
            </button>

            <button
              type="button"
              onClick={() => handleFormatSelect(true)}
              style={{
                padding: "10px 8px",
                fontSize: 11.5,
                fontWeight: isVertical ? 700 : 500,
                borderRadius: "var(--radius-sm, 6px)",
                border: isVertical ? "1px solid var(--accent-primary)" : "1px solid var(--border-subtle)",
                background: isVertical ? "rgba(99, 102, 241, 0.16)" : "transparent",
                color: isVertical ? "#e0e7ff" : "var(--text-secondary)",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 4
              }}
            >
              <span style={{ fontSize: 16 }}>📱</span>
              <span>9:16 Dikey Shorts</span>
              <span style={{ fontSize: 9.5, color: "var(--text-muted)" }}>1080x1920 (&lt;60 sn)</span>
            </button>
          </div>
        </div>

        {/* Duration */}
        <div className="card" style={{ padding: "16px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>
              ⏱️ Klip Süresi
            </span>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-primary)", fontFamily: "monospace" }}>
              {duration} sn ({formatMinSec(duration)})
            </span>
          </div>

          <div style={{ display: "flex", gap: 6 }}>
            {!isVertical ? (
              <>
                {[
                  { sec: 180, label: "3 dk" },
                  { sec: 240, label: "4 dk" },
                  { sec: 300, label: "5 dk" },
                ].map(p => (
                  <button
                    key={p.sec}
                    type="button"
                    onClick={() => setDuration(p.sec)}
                    style={{
                      flex: 1,
                      padding: "6px 4px",
                      fontSize: 11,
                      fontWeight: duration === p.sec ? 700 : 500,
                      borderRadius: "var(--radius-sm, 6px)",
                      border: duration === p.sec ? "1px solid #a855f7" : "1px solid var(--border-subtle)",
                      background: duration === p.sec ? "rgba(168, 85, 247, 0.2)" : "transparent",
                      color: duration === p.sec ? "#f3e8ff" : "var(--text-secondary)",
                      cursor: "pointer"
                    }}
                  >
                    {p.label}
                  </button>
                ))}
              </>
            ) : (
              <>
                {[
                  { sec: 30, label: "30 sn" },
                  { sec: 45, label: "45 sn" },
                  { sec: 60, label: "60 sn" },
                ].map(p => (
                  <button
                    key={p.sec}
                    type="button"
                    onClick={() => setDuration(p.sec)}
                    style={{
                      flex: 1,
                      padding: "6px 4px",
                      fontSize: 11,
                      fontWeight: duration === p.sec ? 700 : 500,
                      borderRadius: "var(--radius-sm, 6px)",
                      border: duration === p.sec ? "1px solid #a855f7" : "1px solid var(--border-subtle)",
                      background: duration === p.sec ? "rgba(168, 85, 247, 0.2)" : "transparent",
                      color: duration === p.sec ? "#f3e8ff" : "var(--text-secondary)",
                      cursor: "pointer"
                    }}
                  >
                    {p.label}
                  </button>
                ))}
              </>
            )}
          </div>

          <input
            type="range"
            min={isVertical ? 15 : 60}
            max={isVertical ? 60 : 300}
            step={5}
            value={duration}
            onChange={e => setDuration(Number(e.target.value))}
            style={{ width: "100%", accentColor: "#a855f7", cursor: "pointer", marginTop: 2 }}
          />
        </div>
      </div>

      {/* 3D Görsel Tema */}
      <div className="card" style={{ padding: "16px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
        <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>
          🎨 3D Nöron Görsel Teması (Remotion Synaptic Visualizer)
        </span>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
          {SINEK_THEMES.map(t => {
            const isSel = theme === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setTheme(t.id)}
                style={{
                  padding: "10px 10px",
                  fontSize: 11.5,
                  fontWeight: isSel ? 700 : 500,
                  borderRadius: "var(--radius-sm, 6px)",
                  border: isSel ? "1px solid #38bdf8" : "1px solid var(--border-subtle)",
                  background: isSel ? "rgba(56, 189, 248, 0.12)" : "transparent",
                  color: isSel ? "#e0f2fe" : "var(--text-secondary)",
                  cursor: "pointer",
                  textAlign: "left",
                  display: "flex",
                  flexDirection: "column",
                  gap: 3
                }}
              >
                <span>{t.name}</span>
                <span style={{ fontSize: 9.5, color: "var(--text-muted)", lineHeight: 1.3 }}>
                  {t.desc}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* LM Studio Bilgi Kutusu */}
      <div style={{
        padding: "12px 16px",
        background: "rgba(16, 185, 129, 0.08)",
        border: "1px solid rgba(16, 185, 129, 0.25)",
        borderRadius: "var(--radius-md, 8px)",
        display: "flex",
        alignItems: "center",
        gap: 12
      }}>
        <span style={{ fontSize: 20 }}>🤖</span>
        <div style={{ fontSize: 11.5, color: "#a7f3d0", lineHeight: 1.4 }}>
          <strong>LM Studio (Gemma-3 / Gemma-4) Yayına Hazırlama:</strong> Üretim tamamlandığında hedef dilde ({channel.language.toUpperCase()}) viral başlık, ilk 3 sn kanca cümlesi, YouTube/TikTok hazır açıklama ve hashtag'ler otomatik hazırlanıp <code>publishing_info.txt</code> ve <code>video_info.json</code> olarak kaydedilecektir.
        </div>
      </div>

      {/* Action Button & Running Status */}
      {isCurrentTaskRunning ? (
        <div className="card" style={{
          padding: "16px 20px",
          background: "linear-gradient(135deg, rgba(168, 85, 247, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%)",
          border: "1px solid rgba(168, 85, 247, 0.4)",
          display: "flex",
          flexDirection: "column",
          gap: 10
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#f3e8ff", display: "flex", alignItems: "center", gap: 6 }}>
              <span className="spinner" style={{ width: 14, height: 14 }} />
              Sinek Beyni Biyo-AI Üretimi Devam Ediyor...
            </span>
            <span style={{ fontSize: 12, color: "#d8b4fe", fontFamily: "monospace" }}>
              {runningTask?.status || "Çalışıyor"}
            </span>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
            {runningTask?.message || "Drosophila nöronları ateşleniyor & Remotion video oluşturuluyor..."}
          </p>
        </div>
      ) : (
        <button
          type="button"
          className="btn w-full"
          onClick={handleTriggerProduce}
          style={{
            padding: "16px 24px",
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: "0.03em",
            background: "linear-gradient(135deg, #9333ea 0%, #6366f1 100%)",
            color: "#ffffff",
            border: "none",
            borderRadius: "var(--radius-md, 8px)",
            cursor: "pointer",
            boxShadow: "0 4px 20px rgba(147, 51, 234, 0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            transition: "all 0.2s ease"
          }}
        >
          <span>⚡</span>
          <span>SİNEK BEYNİ İLE KLİP ÜRET ({formatMinSec(duration)} • {isVertical ? "Shorts" : "16:9"})</span>
        </button>
      )}

      <div style={{
        fontSize: 11,
        color: "var(--text-muted)",
        textAlign: "center",
        marginTop: 2
      }}>
        💡 Üretilen uzun klibi dilediğiniz zaman <strong>"Uzundan Shorts Türet"</strong> sayfasından tek tıkla istediğiniz sayıda dikey Shorts'a dönüştürebilirsiniz.
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   CHANNEL DETAIL
   ══════════════════════════════════════════════════════════════════ */

function ChannelDetail({ channel, onEdit, onDelete, onRun, onReproduce, onStartShorts, onRecompose, onProduceConnectome, runningTask, onNavigateMaterials }) {
  const lang = getLang(channel.language);
  const videoCount = channel.video_count || 0;
  const progress = Math.min(100, videoCount * 5);

  const [planData, setPlanData] = useState(null);
  const [selectedRowIds, setSelectedRowIds] = useState([]);
  const [audioLibrary, setAudioLibrary] = useState([]);
  const [planCount, setPlanCount] = useState(10);
  const [mindMap, setMindMap] = useState(null);
  const [syncingMindMap, setSyncingMindMap] = useState(false);
  const [loadingMindMap, setLoadingMindMap] = useState(false);
  const [syncingPlan, setSyncingPlan] = useState(false);
  const [uploadingRowId, setUploadingRowId] = useState(null);
  const isMusicChannel = channel?.topic_category === "music" || channel?.topic_category === "connectome" || channel?.topic_category === "muzik" || channel?.topic_category === "sinek_beyni";
  const isStoryChannel = channel?.topic_category === "story" || channel?.topic_category === "masal" || channel?.channel_id === "ch_story_tr";

  const unproducedRows = useMemo(() => {
    return (planData?.plan || []).filter(row => {
      const isProduced = row.uretildi?.toLowerCase() === "evet" || row.uretildi === "yes" || row.uretildi === "true" || row.uretildi === "1";
      return !isProduced;
    });
  }, [planData?.plan]);

  const allUnproducedSelected = unproducedRows.length > 0 && unproducedRows.every(r => selectedRowIds.includes(r.id));

  const handleSelectUnproduced = () => {
    if (allUnproducedSelected) {
      const unproducedIdSet = new Set(unproducedRows.map(r => r.id));
      setSelectedRowIds(prev => prev.filter(id => !unproducedIdSet.has(id)));
    } else {
      const unproducedIds = unproducedRows.map(r => r.id);
      setSelectedRowIds(prev => Array.from(new Set([...prev, ...unproducedIds])));
    }
  };

  useEffect(() => {
    fetch("/api/audio-library")
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setAudioLibrary(data.tracks || []);
        }
      }).catch(() => {});
  }, []);

  const [voiceClonesList, setVoiceClonesList] = useState([]);
  const [activeVoiceCloneId, setActiveVoiceCloneId] = useState("");

  useEffect(() => {
    fetch("/api/voice-clones")
      .then(res => res.json())
      .then(data => {
        if (data && data.clones) {
          setVoiceClonesList(data.clones);
          setActiveVoiceCloneId(data.active_id || "");
        }
      }).catch(() => {});
  }, []);

  const getSelectedCloneName = () => {
    const cid = channel.voice_clone_id || channel.edit_options?.voice_clone_id;
    if (!cid) {
      const activeObj = voiceClonesList.find(c => c.id === activeVoiceCloneId);
      return activeObj ? `Sistem Varsayılanı (${activeObj.name})` : "Sistem Varsayılanı (Aktif Klon)";
    }
    const found = voiceClonesList.find(c => c.id === cid);
    return found ? found.name : cid;
  };
  const [planning, setPlanning] = useState(false);
  const [loopCount, setLoopCount] = useState(1);
  const [loopDelay, setLoopDelay] = useState(10);

  const [showEditVideoModal, setShowEditVideoModal] = useState(false);
  const [editingVideoRow, setEditingVideoRow] = useState(null);
  const [editVideoTransition, setEditVideoTransition] = useState("fade");
  const [editVideoSubPreset, setEditVideoSubPreset] = useState("bold");
  const [editVideoSubAnim, setEditVideoSubAnim] = useState("fade");
  const [editVideoBgmVolume, setEditVideoBgmVolume] = useState(0.15);
  const [editVideoWatermarkText, setEditVideoWatermarkText] = useState("");
  const [editVideoCensorFaces, setEditVideoCensorFaces] = useState(false);
  const [editVideoAutoEditor, setEditVideoAutoEditor] = useState(false);
  const [editVideoEnableI2V, setEditVideoEnableI2V] = useState(false);
  const [recompiling, setRecompiling] = useState(false);

  const handleOpenVideoEdit = (row) => {
    setEditingVideoRow(row);
    setEditVideoTransition(row.transition || "fade");
    setEditVideoSubPreset(row.subtitle_preset || "bold");
    setEditVideoSubAnim(row.subtitle_animation || "fade");
    setEditVideoBgmVolume(row.bgm_volume !== undefined ? row.bgm_volume : 0.15);
    setEditVideoWatermarkText(row.watermark_text || "");
    setEditVideoCensorFaces(row.censor_faces || false);
    setEditVideoAutoEditor(row.auto_editor || false);
    setEditVideoEnableI2V(row.enable_i2v || false);
    setShowEditVideoModal(true);
  };

  const handleSaveVideoEdit = async () => {
    if (!editingVideoRow?.video_folder) return;
    setRecompiling(true);
    try {
      const response = await fetch("/api/output/edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          folder: editingVideoRow.video_folder,
          transition: editVideoTransition,
          transition_dur: 0.5,
          subtitle_preset: editVideoSubPreset,
          subtitle_animation: editVideoSubAnim,
          bgm_volume: parseFloat(editVideoBgmVolume),
          watermark_text: editVideoWatermarkText,
          censor_faces: editVideoCensorFaces,
          auto_editor: editVideoAutoEditor,
          enable_i2v: editVideoEnableI2V,
        })
      });
      const data = await response.json();
      if (response.ok && data.success) {
        alert("Video başarıyla yeniden derlendi!");
        setShowEditVideoModal(false);
        fetchPlan();
      } else {
        alert("Video derleme hatası: " + (data.detail || "Bilinmeyen Hata"));
      }
    } catch (err) {
      alert("Hata: " + err.message);
    } finally {
      setRecompiling(false);
    }
  };

  const handleReproduceVideo = async (row) => {
    if (!window.confirm("Bu videoyu tekrar üretmek istediğinize emin misiniz? Varolan video arşiv klasörüne taşınacaktır.")) return;
    if (onReproduce) {
      await onReproduce(channel.channel_id, row.id);
    }
  };

  const handleRecomposeVideo = async (row) => {
    if (!window.confirm("Mevcut görsel ve ses dosyaları kullanılarak videolaştırma (render) işlemi başlatılacaktır. Devam etmek istiyor musunuz?")) return;
    if (onRecompose) {
      await onRecompose(channel.channel_id, row.id);
    }
  };

  const handleCreateShorts = async (row) => {
    if (!window.confirm("Bu uzun videodan (4 dk+) otomatik Shorts senaryosu üretilip plana eklenecektir. Devam etmek istiyor musunuz?")) return;
    try {
      const res = await fetch(`/api/channels/${channel.channel_id}/plan/${row.id}/create-shorts`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok && data.success) {
        if (onStartShorts) {
          onStartShorts(channel.channel_id, data.exec_id);
        }
        fetchPlan();
      } else {
        alert("Shorts oluşturma hatası: " + (data.detail || "Bilinmeyen Hata"));
      }
    } catch (err) {
      alert("Hata: " + err.message);
    }
  };

  const handleUploadVideo = async (row) => {
    if (!window.confirm(`"${row.baslik || row.konu}" videosunu doğrudan YouTube'a yüklemek ve planlamak (19:00) istiyor musunuz?`)) {
      return;
    }
    setUploadingRowId(row.id);
    try {
      const res = await fetch(`/api/channels/${channel.channel_id}/plan/${row.id}/upload`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok && data.success) {
        if (data.api_upload) {
          alert(`🎉 Video Başarıyla Doğrudan YouTube'a Yüklendi ve Planlandı!\n\nVideo ID: ${data.video_id}\nBaşlık: ${data.title || row.baslik}\nLink: ${data.url}\nPlanlanan Yayım: ${data.scheduled_for || '19:00'}`);
          fetchPlan();
          return;
        }

        const payload = data.payload || (data.queue && data.queue[0]);
        if (payload) {
          const fullPayload = {
            ...payload,
            timestamp: Date.now(),
          };

          if (fullPayload.video_path) {
            try {
              await navigator.clipboard.writeText(fullPayload.video_path);
            } catch (e) {}
          }

          localStorage.setItem("yt_studio_pending", JSON.stringify(fullPayload));
          window.postMessage({ type: "YT_STUDIO_SEND", payload: fullPayload }, "*");
          window.open("https://studio.youtube.com", "_blank");

          alert(`🚀 YouTube Studio Açılıyor...\n\nKanal: ${fullPayload.channel_name || channel.name}\nBaşlık: ${fullPayload.title}\nPlanlanan Yayım: ${fullPayload.display_summary || ''}\n\nEklenti mevcut oturumunuz üzerinden videoyu yükleyip 19:00 yerel saatine göre planlayacaktır.`);
          fetchPlan();
        } else {
          alert("Yükleme Hatası: Geçersiz yanıt alındı.");
        }
      } else {
        alert("Yükleme Hatası: " + (data.detail || data.error || "Video yüklenemedi"));
      }
    } catch (err) {
      alert("Hata: " + err.message);
    } finally {
      setUploadingRowId(null);
    }
  };

  const handleUpdateMusic = async (rowId, trackId) => {
    try {
      const res = await fetch(`/api/channels/${channel.channel_id}/plan/${rowId}/music`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secilen_muzik: trackId })
      });
      if (res.ok) {
        fetchPlan();
      } else {
        alert("Müzik seçimi kaydedilemedi.");
      }
    } catch (err) {
      alert("Hata: " + err.message);
    }
  };

  const handleDeletePlanRow = async (rowId) => {
    if (!confirm("Bu içerik planlamasını tamamen silmek istediğinize emin misiniz?")) {
      return;
    }
    
    // Optimistic Update: UI'ı anında güncelle
    const previousPlanData = planData;
    if (planData && planData.plan) {
      const filtered = planData.plan.filter(row => String(row.id) !== String(rowId));
      const deletedRow = planData.plan.find(row => String(row.id) === String(rowId));
      const wasProduced = deletedRow && (deletedRow.uretildi?.toLowerCase() === "evet" || deletedRow.uretildi === "yes" || deletedRow.uretildi === "true" || deletedRow.uretildi === "1");
      
      const newStats = planData.stats ? {
        total: Math.max(0, planData.stats.total - 1),
        produced: Math.max(0, planData.stats.produced - (wasProduced ? 1 : 0)),
        remaining: Math.max(0, (planData.stats.total - 1) - (planData.stats.produced - (wasProduced ? 1 : 0)))
      } : null;

      setPlanData({
        ...planData,
        plan: filtered,
        stats: newStats
      });
      setSelectedRowIds(prev => prev.filter(id => String(id) !== String(rowId)));
    }

    try {
      const res = await fetch(`/api/channels/${channel.channel_id}/plan/${rowId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        fetchPlan();
        fetchMindMap();
      } else {
        alert("Plan silinemedi.");
        setPlanData(previousPlanData);
      }
    } catch (err) {
      alert("Hata: " + err.message);
      setPlanData(previousPlanData);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowIds.length === 0) return;
    if (!confirm(`Seçilen ${selectedRowIds.length} içerik planlamasını toplu olarak silmek istediğinize emin misiniz?`)) {
      return;
    }

    // Optimistic Update: UI'ı anında güncelle
    const previousPlanData = planData;
    const idsToRemove = selectedRowIds.map(String);
    if (planData && planData.plan) {
      const filtered = planData.plan.filter(row => !idsToRemove.includes(String(row.id)));
      
      let producedCountDiff = 0;
      selectedRowIds.forEach(id => {
        const row = planData.plan.find(r => String(r.id) === String(id));
        if (row) {
          const isProduced = row.uretildi?.toLowerCase() === "evet" || row.uretildi === "yes" || row.uretildi === "true" || row.uretildi === "1";
          if (isProduced) producedCountDiff++;
        }
      });

      const newStats = planData.stats ? {
        total: Math.max(0, planData.stats.total - idsToRemove.length),
        produced: Math.max(0, planData.stats.produced - producedCountDiff),
        remaining: Math.max(0, (planData.stats.total - idsToRemove.length) - (planData.stats.produced - producedCountDiff))
      } : null;

      setPlanData({
        ...planData,
        plan: filtered,
        stats: newStats
      });
      setSelectedRowIds([]);
    }

    try {
      const res = await fetch(`/api/channels/${channel.channel_id}/plan/batch-delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ row_ids: idsToRemove })
      });
      if (res.ok) {
        fetchPlan();
        fetchMindMap();
      } else {
        alert("Toplu silme işlemi başarısız oldu.");
        setPlanData(previousPlanData);
        setSelectedRowIds(idsToRemove);
      }
    } catch (err) {
      alert("Hata: " + err.message);
      setPlanData(previousPlanData);
      setSelectedRowIds(idsToRemove);
    }
  };

  const fetchMindMap = useCallback(async () => {
    setLoadingMindMap(true);
    try {
      const r = await fetch(`/api/channels/${channel.channel_id}/mind-map`);
      if (r.ok) {
        const d = await r.json();
        if (d.success) {
          setMindMap(d.mind_map || { themes: {} });
        }
      }
    } catch (e) {
      console.error("Mind map yükleme hatası:", e);
    } finally {
      setLoadingMindMap(false);
    }
  }, [channel.channel_id]);

  const handleSyncMindMap = async () => {
    setSyncingMindMap(true);
    try {
      const r = await fetch(`/api/channels/${channel.channel_id}/mind-map/sync`, { method: "POST" });
      if (r.ok) {
        const d = await r.json();
        if (d.success) {
          setMindMap(d.mind_map || { themes: {} });
          alert("Zihin haritası başarıyla güncellendi/senkronize edildi!");
        } else {
          alert("Hata: " + (d.error || "Zihin haritası güncellenemedi."));
        }
      }
    } catch (e) {
      alert("Hata: " + e.message);
    } finally {
      setSyncingMindMap(false);
    }
  };

  const fetchPlan = useCallback(async () => {
    try {
      const r = await fetch(`/api/channels/${channel.channel_id}/plan`);
      if (r.ok) {
        const d = await r.json();
        setPlanData(d);
      }
    } catch (e) {
      console.error("Plan yükleme hatası:", e);
    }
  }, [channel.channel_id]);

  useEffect(() => {
    setPlanData(null);
    setSelectedRowIds([]);
    setMindMap(null);
    fetchPlan();
    fetchMindMap();
  }, [channel.channel_id, fetchPlan, fetchMindMap]);

  // Props güncellendiğinde (örn. video üretildiğinde) planı yenile
  useEffect(() => {
    fetchPlan();
  }, [channel, fetchPlan]);

  const handlePlan = async () => {
    setPlanning(true);
    try {
      const r = await fetch(`/api/channels/${channel.channel_id}/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ count: planCount })
      });
      if (r.ok) {
        fetchPlan();
        fetchMindMap();
      }
    } catch (e) {
      console.error("Planlama hatası:", e);
    }
    setPlanning(false);
  };

  const handleSyncPlan = async () => {
    setSyncingPlan(true);
    try {
      const r = await fetch(`/api/channels/${channel.channel_id}/plan/sync`, {
        method: "POST"
      });
      if (r.ok) {
        const res = await r.json();
        alert(`Tazeleme Başarılı!\nÜretildi yapılan: ${res.updated_to_produced?.length || 0}\nÜretilmedi yapılan: ${res.updated_to_unproduced?.length || 0}`);
        fetchPlan();
      } else {
        alert("Eşitleme sırasında bir hata oldu.");
      }
    } catch (e) {
      console.error("Eşitleme hatası:", e);
      alert("Eşitleme hatası: " + e.message);
    }
    setSyncingPlan(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 20 }}>{lang?.flag || "🌍"}</span>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{channel.name}</h2>
            <span className="chip chip-accent" style={{ fontSize: 11.5, fontWeight: 600 }}>
              {CATEGORY_LABELS[channel.topic_category] || `📂 ${channel.topic_category || "Genel"}`}
            </span>
          </div>
          <code style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "'JetBrains Mono', monospace" }}>{channel.channel_id}</code>
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          {isStoryChannel && (
            <a
              href="#story-studio-anchor"
              className="btn btn-primary btn-sm"
              style={{ display: "inline-flex", alignItems: "center", gap: 5, textDecoration: "none" }}
            >
              <BookOpen size={14} /> Hikaye Atölyesine Git
            </a>
          )}
          <button className="btn btn-ghost btn-sm" onClick={onEdit}>Düzenle</button>
          <button className="btn btn-danger btn-sm" onClick={onDelete}>Sil</button>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", borderBottom: "1px solid var(--border-subtle)" }}>
          {[
            { label: "Konu Kategorisi", value: CATEGORY_LABELS[channel.topic_category] || channel.topic_category || "Genel" },
            { label: "Dil", value: `${lang?.flag} ${lang?.name || channel.language}` },
            { label: "Zamanlayıcı", value: `${String(channel.schedule_hour).padStart(2, "0")}:00` },
            { label: "Geçiş", value: ({ fade: "🌅 Fade", zoom: "🔍 Zoom", slide: "➡ Slide", parallax: "🌌 Parallax", none: "⬛ Yok" })[channel.transition] || "🌅 Fade" },
          ].map((item, i) => (
            <div key={i} style={{ padding: "16px 20px", borderRight: i < 3 ? "1px solid var(--border-subtle)" : "none" }}>
              <div className="stat-label" style={{ marginBottom: 6 }}>{item.label}</div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{item.value}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)" }}>
          {[
            { label: "Durum", badge: channel.active ? "success" : "muted", value: channel.active ? "Aktif" : "Pasif" },
            { label: "Mod", value: channel.shorts_mode ? "📱 Shorts" : "🖥 Normal" },
            { label: "Son Üretim", value: formatDate(channel.last_run) },
          ].map((item, i) => (
            <div key={i} style={{ padding: "16px 20px", borderRight: i < 2 ? "1px solid var(--border-subtle)" : "none" }}>
              <div className="stat-label" style={{ marginBottom: 6 }}>{item.label}</div>
              {item.badge ? <span className={`chip chip-${item.badge}`}>{item.value}</span>
                : <div style={{ fontSize: 13.5, fontWeight: 500, color: "var(--text-primary)" }}>{item.value}</div>}
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ padding: "18px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
          <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)" }}>Üretim İlerlemesi</span>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "monospace" }}>{videoCount}/20</span>
        </div>
        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {isMusicChannel ? (
        <SinekBeyniStudio
          channel={channel}
          onProduceConnectome={onProduceConnectome}
          runningTask={runningTask}
        />
      ) : (
        <>
          {isStoryChannel && (
            <div id="story-studio-anchor">
              <StoryStudio channel={channel} />
            </div>
          )}

          {/* Intro / Outro & Video Süresi Bilgisi */}
      <div className="card" style={{ padding: "14px 16px" }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
          <span>🎬</span> Intro / Outro & Süre Ayarları
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 12px", fontSize: 12 }}>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Süre: </span>
            <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>
              {channel.edit_options?.video_duration ? `${channel.edit_options.video_duration} sn (Kanal Özel)` : "Varsayılan (Global)"}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Geçiş: </span>
            <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>
              {channel.edit_options?.transition_dur ? `${channel.edit_options.transition_dur} sn (Kanal Özel)` : "Varsayılan (Global)"}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Intro Klibi: </span>
            <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>
              {channel.edit_options?.intro_clip_path ? "✓ Aktif (Kanal Özel)" : "Global / Yok"}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Outro Klibi: </span>
            <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>
              {channel.edit_options?.outro_clip_path ? "✓ Aktif (Kanal Özel)" : "Global / Yok"}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Altyazı Stili: </span>
            <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>
              {channel.edit_options?.subtitle_preset ? `${channel.edit_options.subtitle_preset}` : "Global"}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>NASA Görsel: </span>
            <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>
              {channel.shorts_mode ? "✓ Sığdır (Bulanık Kenar)" : "Normal"}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>🎙️ Ses Klonu: </span>
            <span style={{ fontWeight: 600, color: (channel.voice_clone_id || channel.edit_options?.voice_clone_id) ? "var(--accent-primary)" : "var(--text-secondary)" }}>
              {getSelectedCloneName()}
            </span>
          </div>
        </div>
      </div>

      {/* İçerik Planlama Bölümü */}
      <div className="card" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>📋 İçerik Planı</span>
          {planData?.stats && (
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
              {planData.stats.produced} / {planData.stats.total} üretildi
            </span>
          )}
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <input
            type="number"
            min="1"
            max="50"
            className="form-input"
            style={{ width: 80, padding: "6px 10px", fontSize: 12 }}
            value={planCount}
            onChange={e => setPlanCount(Math.max(1, Number(e.target.value)))}
            placeholder="Adet"
          />
          <button
            className="btn btn-primary"
            style={{ flex: 1, minWidth: 120, padding: "8px 12px", fontSize: 12 }}
            onClick={handlePlan}
            disabled={planning}
          >
            {planning ? "Planlanıyor..." : "İçerik Planla"}
          </button>

          {planData?.plan?.length > 0 && unproducedRows.length > 0 && (
            <button
              type="button"
              className="btn"
              onClick={handleSelectUnproduced}
              style={{
                padding: "8px 12px",
                fontSize: 12,
                background: allUnproducedSelected ? "rgba(99, 102, 241, 0.18)" : "rgba(255, 255, 255, 0.05)",
                color: allUnproducedSelected ? "#818cf8" : "var(--text-primary)",
                border: allUnproducedSelected ? "1px solid rgba(99, 102, 241, 0.4)" : "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                cursor: "pointer",
                transition: "all 0.2s ease"
              }}
              title="Üretilmeyen (bekleyen) tüm plan konularını seçer veya seçimi kaldırır"
            >
              {allUnproducedSelected ? "✓ Üretilmeyenler Seçildi" : `⚡ Üretilmeyen Tüm Planları Seç (${unproducedRows.length})`}
            </button>
          )}
          
          {selectedRowIds.length > 0 && (
            <button
              className="btn"
              onClick={handleBatchDelete}
              style={{
                padding: "8px 12px",
                fontSize: 12,
                background: "rgba(239, 68, 68, 0.15)",
                color: "#f87171",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "var(--radius-sm)",
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                cursor: "pointer",
                transition: "all 0.2s ease"
              }}
            >
              🗑️ Seçilenleri Sil ({selectedRowIds.length})
            </button>
          )}
          
          {planData?.plan?.length > 0 && (
            <>
              <button
                className="btn btn-ghost"
                style={{ padding: "8px 12px", fontSize: 12, display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}
                onClick={handleSyncPlan}
                disabled={syncingPlan}
              >
                {syncingPlan ? "🔄..." : "🔄 Tazele"}
              </button>
              <a
                href={`/api/channels/${channel.channel_id}/plan/download`}
                className="btn btn-ghost"
                style={{ padding: "8px 12px", fontSize: 12, display: "flex", alignItems: "center", textDecoration: "none" }}
                download
              >
                📥 İndir
              </a>
              <button
                type="button"
                className="btn btn-ghost"
                style={{ padding: "8px 12px", fontSize: 12, display: "inline-flex", alignItems: "center", gap: 5, color: "#22d3ee", border: "1px solid rgba(6,182,212,0.35)", borderRadius: "var(--radius-sm)" }}
                onClick={() => onNavigateMaterials && onNavigateMaterials(channel.channel_id)}
                title="Bu kanal için kaydedilmiş üretim materyallerini aç"
              >
                <Layers size={13} /> Materyaller
              </button>
            </>
          )}
        </div>

        {planData?.plan?.length > 0 && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11.5, color: "var(--text-muted)", padding: "2px 2px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span>Seçim:</span>
              <button
                type="button"
                style={{ background: "none", border: "none", color: "var(--accent-primary)", cursor: "pointer", padding: 0, fontSize: 11.5, textDecoration: "underline" }}
                onClick={() => setSelectedRowIds(planData.plan.map(r => r.id))}
              >
                Tümünü Seç ({planData.plan.length})
              </button>
              {unproducedRows.length > 0 && (
                <>
                  <span>•</span>
                  <button
                    type="button"
                    style={{ background: "none", border: "none", color: allUnproducedSelected ? "#818cf8" : "var(--accent-primary)", cursor: "pointer", padding: 0, fontSize: 11.5, textDecoration: "underline", fontWeight: 600 }}
                    onClick={handleSelectUnproduced}
                  >
                    {allUnproducedSelected ? "Üretilmeyenlerin Seçimini Kaldır" : `Üretilmeyen Tüm Planları Seç (${unproducedRows.length})`}
                  </button>
                </>
              )}
              {selectedRowIds.length > 0 && (
                <>
                  <span>•</span>
                  <button
                    type="button"
                    style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: 0, fontSize: 11.5, textDecoration: "underline" }}
                    onClick={() => setSelectedRowIds([])}
                  >
                    Seçimi Temizle
                  </button>
                </>
              )}
            </div>
            {selectedRowIds.length > 0 && (
              <span style={{ color: "var(--accent-primary)", fontWeight: 600 }}>
                {selectedRowIds.length} plan seçildi
              </span>
            )}
          </div>
        )}

        {planData?.plan?.length > 0 ? (<>
          <div style={{
            maxHeight: 200,
            overflowY: "auto",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            background: "var(--bg-primary)"
          }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5, textAlign: "left" }}>
              <thead>
                <tr style={{ background: "rgba(255,255,255,0.02)", borderBottom: "1px solid var(--border-subtle)" }}>
                  <th style={{ padding: "6px 10px", width: 35, textAlign: "center" }}>
                    <input
                      type="checkbox"
                      style={{ cursor: "pointer", width: 13, height: 13, accentColor: "var(--accent-primary)" }}
                      checked={planData?.plan?.length > 0 && selectedRowIds.length === planData.plan.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedRowIds(planData.plan.map(row => row.id));
                        } else {
                          setSelectedRowIds([]);
                        }
                      }}
                    />
                  </th>
                  <th style={{ padding: "6px 10px", color: "var(--text-muted)", fontWeight: 600, width: 30 }}>ID</th>
                  <th style={{ padding: "6px 10px", color: "var(--text-muted)", fontWeight: 600 }}>Konu / Başlık</th>
                  <th style={{ padding: "6px 10px", color: "var(--text-muted)", fontWeight: 600, width: 170 }}>Fon Müziği</th>
                  <th style={{ padding: "6px 10px", color: "var(--text-muted)", fontWeight: 600, width: 65, textAlign: "center" }}>Üretim</th>
                  <th style={{ padding: "6px 10px", color: "var(--text-muted)", fontWeight: 600, width: 110, textAlign: "center" }}>Yükleme Durumu</th>
                  <th style={{ padding: "6px 10px", color: "var(--text-muted)", fontWeight: 600, width: 140, textAlign: "center" }}>Aksiyonlar</th>
                </tr>
              </thead>
              <tbody>
                {planData.plan.map((row, i) => {
                  const isProduced = row.uretildi?.toLowerCase() === "evet" || row.uretildi === "yes" || row.uretildi === "true" || row.uretildi === "1";
                  const isUploaded = row.yuklendi?.toLowerCase() === "evet" || row.yuklendi === "yes" || row.yuklendi === "true" || row.yuklendi === "1";
                  return (
                    <tr key={i} style={{ borderBottom: i < planData.plan.length - 1 ? "1px solid var(--border-subtle)" : "none" }}>
                      <td style={{ padding: "8px 10px", textAlign: "center" }}>
                        <input
                          type="checkbox"
                          style={{ cursor: "pointer", width: 13, height: 13, accentColor: "var(--accent-primary)" }}
                          checked={selectedRowIds.includes(row.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedRowIds(prev => [...prev, row.id]);
                            } else {
                              setSelectedRowIds(prev => prev.filter(id => id !== row.id));
                            }
                          }}
                        />
                      </td>
                      <td style={{ padding: "8px 10px", color: "var(--text-muted)", fontFamily: "monospace" }}>{row.id}</td>
                      <td style={{ padding: "8px 10px" }}>
                        <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{row.baslik || row.konu}</div>
                        {row.baslik && <div style={{ fontSize: 10.5, color: "var(--text-muted)", marginTop: 2 }}>{row.konu}</div>}
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        <select
                          className="form-input"
                          style={{
                            padding: "4px 8px",
                            fontSize: "11px",
                            height: "auto",
                            border: "1px solid var(--border-subtle)",
                            background: "var(--bg-secondary)",
                            borderRadius: "var(--radius-sm)",
                            width: "100%",
                            maxWidth: "165px",
                            color: "var(--text-primary)",
                            cursor: "pointer"
                          }}
                          value={row.secilen_muzik || ""}
                          onChange={(e) => handleUpdateMusic(row.id, e.target.value)}
                        >
                          <option value="">Varsayılan (Global BGM)</option>
                          {audioLibrary.map(t => (
                            <option key={t.id} value={t.id}>
                              🎵 {t.title} ({t.artist})
                            </option>
                          ))}
                        </select>
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "center" }}>
                        {isProduced ? (
                          <span className="chip chip-success" style={{ fontSize: 9.5, padding: "1px 5px" }}>Üretildi</span>
                        ) : (row.uretildi === "Materyaller Hazır" || row.uretildi === "materyaller_hazir") ? (
                          <span className="chip" style={{ fontSize: 9.5, padding: "1px 5px", background: "rgba(6,182,212,0.18)", color: "#22d3ee", border: "1px solid rgba(6,182,212,0.35)" }}>📦 Materyal Hazır</span>
                        ) : row.recompose_available ? (
                          <span className="chip chip-warning" style={{ fontSize: 9.5, padding: "1px 5px", background: "rgba(245,158,11,0.2)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.3)" }}>Yarım Kaldı</span>
                        ) : (
                          <span className="chip chip-muted" style={{ fontSize: 9.5, padding: "1px 5px" }}>Bekliyor</span>
                        )}
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "center" }}>
                        {isUploaded ? (
                          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                            <span className="chip chip-success" style={{ fontSize: 9.5, padding: "1px 5px" }}>📤 Yüklendi</span>
                            {row.yayim_tarihi && (
                              <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "monospace" }}>
                                {row.yayim_tarihi}
                              </span>
                            )}
                          </div>
                        ) : isProduced ? (
                          <span className="chip chip-warning" style={{ fontSize: 9.5, padding: "1px 5px" }}>⏳ Yüklenmedi</span>
                        ) : (
                          <span style={{ color: "var(--text-muted)", fontSize: 11 }}>-</span>
                        )}
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "center" }}>
                        <div style={{ display: "flex", gap: 6, justifyContent: "center", flexWrap: "wrap" }}>
                          {isProduced && !isUploaded && (
                            <button
                              className="btn btn-primary"
                              style={{ padding: "2px 8px", fontSize: 10, display: "inline-flex", alignItems: "center", gap: 3, background: "linear-gradient(135deg, #6366f1, #8b5cf6)", border: "none" }}
                              onClick={() => handleUploadVideo(row)}
                              disabled={uploadingRowId === row.id}
                              title="Doğrudan YouTube'a Yükle ve 19:00 için Planla"
                            >
                              {uploadingRowId === row.id ? "⏳ Yükleniyor..." : "📤 Yükle"}
                            </button>
                          )}
                          {isProduced && (
                            <>
                              <button
                                className="btn btn-ghost"
                                style={{ padding: "2px 6px", fontSize: 10, display: "inline-flex", alignItems: "center", gap: 3, border: "1px solid var(--border-subtle)" }}
                                onClick={() => handleOpenVideoEdit(row)}
                              >
                                ⚙️ Ayarla
                              </button>
                              <select
                                style={{
                                  padding: "2px 6px",
                                  fontSize: "10px",
                                  height: "auto",
                                  border: "1px solid var(--border-subtle)",
                                  background: "var(--bg-secondary)",
                                  borderRadius: "var(--radius-sm)",
                                  color: "var(--text-primary)",
                                  cursor: "pointer"
                                }}
                                value=""
                                onChange={(e) => {
                                  if (e.target.value === "reproduce") {
                                    handleReproduceVideo(row);
                                  } else if (e.target.value === "recompose") {
                                    handleRecomposeVideo(row);
                                  }
                                }}
                              >
                                <option value="" disabled hidden>🔄 Yeniden Üret</option>
                                <option value="reproduce">🔄 Yeniden Üret (Sıfırdan)</option>
                                {row.recompose_available && (
                                  <option value="recompose">✨ Varolan Verilerle Yeniden Üret</option>
                                )}
                              </select>
                              {row.duration_sec > 240 && (
                                <button
                                  className="btn btn-ghost"
                                  style={{ padding: "2px 6px", fontSize: 10, display: "inline-flex", alignItems: "center", gap: 3, border: "1px solid #c084fc", color: "#c084fc" }}
                                  onClick={() => handleCreateShorts(row)}
                                >
                                  🎬 Shorts Oluştur
                                </button>
                              )}
                            </>
                          )}
                          {!isProduced && (row.uretildi === "Materyaller Hazır" || row.uretildi === "materyaller_hazir") && (
                            <button
                              className="btn btn-primary"
                              style={{ padding: "2px 7px", fontSize: 10, display: "inline-flex", alignItems: "center", gap: 3, background: "linear-gradient(135deg, #06b6d4, #6366f1)", border: "none", color: "#fff", cursor: "pointer", borderRadius: 4 }}
                              onClick={() => onNavigateMaterials && onNavigateMaterials(channel.channel_id)}
                              title="Bu konunun senaryo ve üretim materyallerini aç / videoya dönüştür"
                            >
                              <Layers size={11} /> Materyal
                            </button>
                          )}
                          {!isProduced && row.recompose_available && (
                            <button
                              className="btn btn-success"
                              style={{ padding: "2px 6px", fontSize: 10, display: "inline-flex", alignItems: "center", gap: 3, background: "rgba(16,185,129,0.2)", color: "#10b981", border: "1px solid rgba(16,185,129,0.3)" }}
                              onClick={() => handleRecomposeVideo(row)}
                            >
                              ✨ Videoyu Tamamla
                            </button>
                          )}
                          <button
                            className="btn btn-ghost"
                            style={{ padding: "2px 6px", fontSize: 10, display: "inline-flex", alignItems: "center", gap: 3, border: "1px solid rgba(239, 68, 68, 0.2)", color: "#f87171" }}
                            onClick={() => handleDeletePlanRow(row.id)}
                          >
                            🗑️ Sil
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <Modal open={showEditVideoModal} onClose={() => setShowEditVideoModal(false)} title="Üretilen Videoyu Düzenle">
            <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "10px 0" }}>
              <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginBottom: 5 }}>
                <strong>Başlık:</strong> {editingVideoRow?.baslik || editingVideoRow?.konu}
              </div>
              
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ fontSize: 11, marginBottom: 3 }}>Geçiş Efekti</label>
                <select
                  className="form-input"
                  style={{ padding: "6px", fontSize: 12 }}
                  value={editVideoTransition}
                  onChange={e => setEditVideoTransition(e.target.value)}
                >
                  <option value="none">Yok (None)</option>
                  <option value="fade">Karartma (Fade)</option>
                  <option value="slide">Kaydırma (Slide)</option>
                  <option value="zoom">Yakınlaşma (Zoom)</option>
                  <option value="kenburns">Kenburns Efekti</option>
                  <option value="parallax">Paralaks (3D)</option>
                </select>
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ fontSize: 11, marginBottom: 3 }}>Alt Yazı Stili</label>
                <select
                  className="form-input"
                  style={{ padding: "6px", fontSize: 12 }}
                  value={editVideoSubPreset}
                  onChange={e => setEditVideoSubPreset(e.target.value)}
                >
                  <option value="bold">Kalın (Bold)</option>
                  <option value="regular">Normal (Regular)</option>
                  <option value="classic">Klasik (Classic)</option>
                  <option value="yellow">Sarı Kontur (Yellow)</option>
                </select>
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ fontSize: 11, marginBottom: 3 }}>Alt Yazı Animasyonu</label>
                <select
                  className="form-input"
                  style={{ padding: "6px", fontSize: 12 }}
                  value={editVideoSubAnim}
                  onChange={e => setEditVideoSubAnim(e.target.value)}
                >
                  <option value="none">Yok (None)</option>
                  <option value="fade">Karartma (Fade)</option>
                  <option value="slide">Kaydırma (Slide)</option>
                  <option value="letter">Harf Harf (Letter)</option>
                  <option value="pop">Kelime Kelime Pop (Word Pop)</option>
                </select>
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ fontSize: 11, marginBottom: 3 }}>Arka Plan Müzik Sesi ({editVideoBgmVolume})</label>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  style={{ width: "100%" }}
                  value={editVideoBgmVolume}
                  onChange={e => setEditVideoBgmVolume(parseFloat(e.target.value))}
                />
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ fontSize: 11, marginBottom: 3 }}>Filigran Metni (Watermark)</label>
                <input
                  type="text"
                  className="form-input"
                  style={{ padding: "6px", fontSize: 12 }}
                  placeholder="@kanalismi"
                  value={editVideoWatermarkText}
                  onChange={e => setEditVideoWatermarkText(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 5 }}>
                <input
                  type="checkbox"
                  id="editVideoCensorFaces"
                  checked={editVideoCensorFaces}
                  onChange={e => setEditVideoCensorFaces(e.target.checked)}
                />
                <label htmlFor="editVideoCensorFaces" style={{ fontSize: 12, cursor: "pointer", userSelect: "none" }}>
                  Yüzleri sansürle (Censor Faces)
                </label>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 5 }}>
                <input
                  type="checkbox"
                  id="editVideoAutoEditor"
                  checked={editVideoAutoEditor}
                  onChange={e => setEditVideoAutoEditor(e.target.checked)}
                />
                <label htmlFor="editVideoAutoEditor" style={{ fontSize: 12, cursor: "pointer", userSelect: "none" }}>
                  Sessizlikleri Kaldır (Auto-Editor)
                </label>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 5 }}>
                <input
                  type="checkbox"
                  id="editVideoEnableI2V"
                  checked={editVideoEnableI2V}
                  onChange={e => setEditVideoEnableI2V(e.target.checked)}
                />
                <label htmlFor="editVideoEnableI2V" style={{ fontSize: 12, cursor: "pointer", userSelect: "none", color: "var(--accent-primary)", fontWeight: 600 }}>
                  🎬 Görselleri Yapay Zeka ile Hareketlendir (Yerel I2V)
                </label>
              </div>

              <div style={{ display: "flex", gap: 10, marginTop: 15 }}>
                <button
                  className="btn btn-muted"
                  style={{ flex: 1, padding: "8px", fontSize: 12 }}
                  onClick={() => setShowEditVideoModal(false)}
                  disabled={recompiling}
                >
                  İptal
                </button>
                <button
                  className="btn btn-primary"
                  style={{ flex: 2, padding: "8px", fontSize: 12 }}
                  onClick={handleSaveVideoEdit}
                  disabled={recompiling}
                >
                  {recompiling ? "Yeniden Derleniyor..." : "Kaydet ve Yeniden Derle"}
                </button>
              </div>
            </div>
          </Modal></>
        ) : (
          <div style={{
            padding: "20px 10px",
            textAlign: "center",
            fontSize: 12,
            color: "var(--text-muted)",
            border: "1px dashed var(--border-subtle)",
            borderRadius: "var(--radius-md)"
          }}>
            Henüz planlanmış içerik yok. Konu sayısı girip "İçerik Planla" butonuna basarak oluşturun.
          </div>
        )}
      </div>

      {/* Zihin Haritası Bölümü */}
      <div className="card" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>🧠 AI İçerik Zihin Haritası (Mind Map)</span>
            <span style={{ fontSize: 10, color: "var(--text-muted)", background: "rgba(255,255,255,0.05)", padding: "1px 5px", borderRadius: 4 }}>
              AI Odaklı Tekrar Önleme
            </span>
          </div>
          <button
            className="btn btn-ghost"
            style={{ padding: "4px 8px", fontSize: 11, border: "1px solid var(--border-subtle)" }}
            onClick={handleSyncMindMap}
            disabled={syncingMindMap || loadingMindMap}
          >
            {syncingMindMap ? "🔄 Eşitleniyor..." : "🔄 Yeniden Derle / Sync"}
          </button>
        </div>

        {loadingMindMap ? (
          <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
            Zihin haritası yükleniyor...
          </div>
        ) : mindMap && Object.keys(mindMap.themes || {}).length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {Object.keys(mindMap.themes).map((themeName) => {
              const topicsList = mindMap.themes[themeName] || [];
              return (
                <details
                  key={themeName}
                  open
                  style={{
                    background: "rgba(255, 255, 255, 0.01)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-md)",
                    padding: "8px 12px",
                    transition: "all 0.2s ease"
                  }}
                >
                  <summary style={{
                    fontWeight: 600,
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    outline: "none",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    userSelect: "none"
                  }}>
                    <span>📁 {themeName}</span>
                    <span className="chip chip-muted" style={{ fontSize: 9.5, padding: "0px 6px" }}>{topicsList.length} Video</span>
                  </summary>
                  <div style={{
                    marginTop: 8,
                    paddingLeft: 16,
                    borderLeft: "1px dashed var(--border-subtle)",
                    display: "flex",
                    flexDirection: "column",
                    gap: 6
                  }}>
                    {topicsList.map((topicTitle, idx) => (
                      <div key={idx} style={{
                        fontSize: 11.5,
                        color: "var(--text-muted)",
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 6,
                        lineHeight: "1.4"
                      }}>
                        <span style={{ color: "var(--text-secondary)" }}>•</span>
                        <span>{topicTitle}</span>
                      </div>
                    ))}
                  </div>
                </details>
              );
            })}
          </div>
        ) : (
          <div style={{
            padding: "20px 10px",
            textAlign: "center",
            fontSize: 12,
            color: "var(--text-muted)",
            border: "1px dashed var(--border-subtle)",
            borderRadius: "var(--radius-md)"
          }}>
            Henüz zihin haritası oluşturulmamış. İçerik planınız varsa "Yeniden Derle / Sync" butonuna tıklayarak oluşturun.
          </div>
        )}
      </div>

      {channel.custom_topics?.length > 0 && (
        <div>
          <div className="section-title" style={{ marginBottom: 10 }}>Özel Konular</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {channel.custom_topics.map((t, i) => <span key={i} className="chip chip-muted">{t}</span>)}
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" style={{ fontSize: 11, marginBottom: 4 }}>Döngü Sayısı</label>
          <input
            type="number"
            className="form-input"
            min="1"
            max="100"
            value={loopCount}
            onChange={e => setLoopCount(Math.max(1, parseInt(e.target.value) || 1))}
            style={{ padding: "6px 10px", fontSize: 12 }}
          />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" style={{ fontSize: 11, marginBottom: 4 }}>Bekleme (Saniye)</label>
          <input
            type="number"
            className="form-input"
            min="0"
            max="3600"
            value={loopDelay}
            onChange={e => setLoopDelay(Math.max(0, parseInt(e.target.value) || 0))}
            style={{ padding: "6px 10px", fontSize: 12 }}
          />
        </div>
      </div>

      <button className="btn btn-run w-full" onClick={() => onRun(channel.channel_id, loopCount, loopDelay)}
        style={{ padding: "12px 0", fontSize: 13, marginTop: 12 }}>
        ▶ Video Üret {channel.shorts_mode ? "📱" : ""}
      </button>
        </>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   GROUP DETAIL
   ══════════════════════════════════════════════════════════════════ */

function GroupDetail({ group, channels, onEdit, onDelete }) {
  const [planData, setPlanData] = useState(null);
  const [selectedRowIds, setSelectedRowIds] = useState([]);
  const [planCount, setPlanCount] = useState(10);
  const [planning, setPlanning] = useState(false);
  const [showAddTopicModal, setShowAddTopicModal] = useState(false);
  const [newTopicTitle, setNewTopicTitle] = useState("");
  const [newTopicNotes, setNewTopicNotes] = useState("");
  const [addingTopic, setAddingTopic] = useState(false);

  const unproducedRows = useMemo(() => {
    return (planData?.plan || []).filter(row => {
      const isProduced = row.uretildi?.toLowerCase() === "evet" || row.uretildi === "yes" || row.uretildi === "true" || row.uretildi === "1";
      return !isProduced;
    });
  }, [planData?.plan]);

  const allUnproducedSelected = unproducedRows.length > 0 && unproducedRows.every(r => selectedRowIds.includes(r.id));

  const handleSelectUnproduced = () => {
    if (allUnproducedSelected) {
      const unproducedIdSet = new Set(unproducedRows.map(r => r.id));
      setSelectedRowIds(prev => prev.filter(id => !unproducedIdSet.has(id)));
    } else {
      const unproducedIds = unproducedRows.map(r => r.id);
      setSelectedRowIds(prev => Array.from(new Set([...prev, ...unproducedIds])));
    }
  };

  const memberChannels = (group.channel_ids || []).map(cid => (channels || []).find(c => c.channel_id === cid)).filter(Boolean);

  const fetchPlan = useCallback(async () => {
    try {
      const r = await fetch(`/api/groups/${group.id}/plan`);
      if (r.ok) {
        const d = await r.json();
        setPlanData(d);
      }
    } catch (e) {
      console.error("Grup planı yükleme hatası:", e);
    }
  }, [group.id]);

  useEffect(() => {
    setPlanData(null);
    setSelectedRowIds([]);
    fetchPlan();
  }, [group.id, fetchPlan]);

  const handlePlan = async () => {
    setPlanning(true);
    try {
      const r = await fetch(`/api/groups/${group.id}/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ count: planCount })
      });
      if (r.ok) {
        fetchPlan();
      } else {
        const err = await r.json();
        alert("Grup planlama hatası: " + (err.detail || "Bilinmeyen hata"));
      }
    } catch (e) {
      alert("Hata: " + e.message);
    } finally {
      setPlanning(false);
    }
  };

  const handleManualAddTopic = async (e) => {
    e?.preventDefault();
    if (!newTopicTitle.trim()) return;
    setAddingTopic(true);
    try {
      const r = await fetch(`/api/groups/${group.id}/plan/manual-add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          baslik: newTopicTitle.trim(),
          notlar: newTopicNotes.trim()
        })
      });
      if (r.ok) {
        setNewTopicTitle("");
        setNewTopicNotes("");
        setShowAddTopicModal(false);
        fetchPlan();
      } else {
        const err = await r.json();
        alert("Konu eklenemedi: " + (err.detail || "Bilinmeyen hata"));
      }
    } catch (err) {
      alert("Hata: " + err.message);
    } finally {
      setAddingTopic(false);
    }
  };

  const [uploadingRowId, setUploadingRowId] = useState(null);

  const handleUploadGroupVideo = async (row) => {
    if (!window.confirm(`"${row.baslik || row.konu}" konusunun videolarını gruptaki tüm kanalların YouTube Studio hesaplarına (ilgili ülkenin 19:00 saatine) yüklemek istiyor musunuz?`)) {
      return;
    }
    setUploadingRowId(row.id);
    try {
      const res = await fetch(`/api/groups/${group.id}/plan/${row.id}/upload`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok && data.success) {
        let payloads = [];
        if (Array.isArray(data.queue) && data.queue.length > 0) {
          payloads = data.queue;
        } else if (Array.isArray(data.results) && data.results.length > 0) {
          payloads = data.results.map(r => r.payload || r).filter(Boolean);
        } else if (data.payload) {
          payloads = [data.payload];
        }

        if (payloads.length > 0) {
          const formattedPayloads = payloads.map(p => ({ ...p, timestamp: Date.now() }));
          
          if (formattedPayloads[0].video_path) {
            try {
              await navigator.clipboard.writeText(formattedPayloads[0].video_path);
            } catch (e) {}
          }

          window.postMessage({ type: "YT_STUDIO_GROUP_SEND", payloads: formattedPayloads }, "*");

          alert(`🚀 Grup YouTube Studio Yüklemesi Başlatıldı!\n\nToplam ${formattedPayloads.length} kanal aynı anda yeni bir pencerede açılacaktır.`);
        } else {
          alert("Gruptaki kanallar için üretilmiş video bulunamadı.");
        }
        fetchPlan();
      } else {
        alert("Grup Yükleme Hatası: " + (data.detail || data.error || "Bilinmeyen hata"));
      }
    } catch (err) {
      alert("Hata: " + err.message);
    } finally {
      setUploadingRowId(null);
    }
  };

  const handleDeletePlanRow = async (rowId) => {
    if (!confirm("Bu grup içerik planlamasını silmek istediğinize emin misiniz?")) return;
    
    // Optimistic Update
    if (planData && planData.plan) {
      setPlanData({
        ...planData,
        plan: planData.plan.filter(row => String(row.id) !== String(rowId))
      });
      setSelectedRowIds(prev => prev.filter(id => String(id) !== String(rowId)));
    }

    try {
      const res = await fetch(`/api/groups/${group.id}/plan/${rowId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        fetchPlan();
      } else {
        alert("Satır silinemedi.");
        fetchPlan();
      }
    } catch (err) {
      alert("Hata: " + err.message);
      fetchPlan();
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowIds.length === 0) return;
    if (!confirm(`Seçilen ${selectedRowIds.length} grup planlamasını toplu silmek istediğinize emin misiniz?`)) return;

    const idsToRemove = selectedRowIds.map(String);
    if (planData && planData.plan) {
      setPlanData({
        ...planData,
        plan: planData.plan.filter(row => !idsToRemove.includes(String(row.id)))
      });
      setSelectedRowIds([]);
    }

    try {
      const res = await fetch(`/api/groups/${group.id}/plan/batch-delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ row_ids: idsToRemove })
      });
      if (res.ok) {
        fetchPlan();
      } else {
        alert("Toplu silme işlemi başarısız oldu.");
        fetchPlan();
      }
    } catch (err) {
      alert("Hata: " + err.message);
      fetchPlan();
    }
  };

  const totalTopics = planData?.plan?.length || 0;
  const producedTopics = planData?.plan?.filter(r => r.uretildi?.toLowerCase() === "evet" || r.uretildi === "yes" || r.uretildi === "true" || r.uretildi === "1").length || 0;
  const progress = totalTopics > 0 ? Math.round((producedTopics / totalTopics) * 100) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 24 }}>👥</span>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>{group.name}</h2>
            <span className="chip chip-primary" style={{ fontSize: 11 }}>Kanal Grubu</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 8 }}>
            <code>ID: {group.id}</code>
            <span>•</span>
            <span>📂 {group.topic_category}</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          <a
            href={`/api/groups/${group.id}/plan/download`}
            download
            className="btn btn-ghost btn-sm"
            style={{ textDecoration: "none" }}
            title="İçerik Planını CSV Olarak İndir"
          >
            📥 CSV İndir
          </a>
          <button className="btn btn-ghost btn-sm" onClick={onEdit}>Düzenle</button>
          <button className="btn btn-danger btn-sm" onClick={onDelete}>Sil</button>
        </div>
      </div>

      {/* Info Cards */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", borderBottom: "1px solid var(--border-subtle)" }}>
          <div style={{ padding: "16px 20px", borderRight: "1px solid var(--border-subtle)" }}>
            <div className="stat-label" style={{ marginBottom: 6 }}>Kategori</div>
            <div style={{ fontSize: 13.5, fontWeight: 500, color: "var(--text-primary)" }}>
              💬 {group.topic_category || "reddit_stories"}
            </div>
          </div>
          <div style={{ padding: "16px 20px", borderRight: "1px solid var(--border-subtle)" }}>
            <div className="stat-label" style={{ marginBottom: 6 }}>Üye Kanallar</div>
            <div style={{ fontSize: 13.5, fontWeight: 500, color: "var(--text-primary)" }}>
              {memberChannels.length} Kanal ({memberChannels.map(c => (c.language || "").toUpperCase()).join(", ")})
            </div>
          </div>
          <div style={{ padding: "16px 20px" }}>
            <div className="stat-label" style={{ marginBottom: 6 }}>Format & Mod</div>
            <div style={{ fontSize: 13.5, fontWeight: 500, color: "var(--text-primary)" }}>
              📱 9:16 Shorts (Çok Dilli ASMR)
            </div>
          </div>
        </div>

        {/* Member Channels List */}
        <div style={{ padding: "14px 20px", background: "rgba(255,255,255,0.015)" }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
            Grup Üyesi Kanallar:
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10 }}>
            {memberChannels.map(ch => {
              const lang = getLang(ch.language);
              return (
                <div
                  key={ch.channel_id}
                  style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "8px 12px", background: "var(--bg-secondary)",
                    border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)"
                  }}
                >
                  <span style={{ fontSize: 18 }}>{lang?.flag || "🌍"}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }} className="truncate">
                      {ch.name}
                    </div>
                    <div style={{ fontSize: 10.5, color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {(ch.language || "").toUpperCase()} · {ch.channel_id}
                    </div>
                  </div>
                  <span className={`chip chip-${ch.active ? "success" : "muted"}`} style={{ fontSize: 10, padding: "1px 6px" }}>
                    {ch.active ? "Aktif" : "Pasif"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {group.topic_category === "reddit_stories" && (group.reddit_avatar_path || group.reddit_username) && (
          <div style={{ padding: "10px 20px", background: "rgba(255, 69, 0, 0.04)", borderTop: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{ fontSize: 11.5, color: "#ff4500", fontWeight: 600 }}>Reddit Özelleştirme:</span>
            {group.reddit_username && (
              <span style={{ fontSize: 11.5, color: "var(--text-secondary)" }}>
                Yazar: <strong>{group.reddit_username}</strong>
              </span>
            )}
            {group.reddit_avatar_path && (
              <span style={{ fontSize: 11.5, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 6 }}>
                Avatar: <code>{group.reddit_avatar_path.split("/").pop()}</code>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Progress Card */}
      <div className="card" style={{ padding: "18px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)" }}>Ortak Üretim İlerlemesi</span>
            <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 8 }}>({progress}%)</span>
          </div>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "monospace" }}>
            {producedTopics} / {totalTopics} Konu Üretildi
          </span>
        </div>
        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${progress}%`, background: "linear-gradient(90deg, #6366f1, #a855f7)" }} />
        </div>
      </div>

      {/* Content Plan Section */}
      <div className="card" style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>📋 Grup İçerik Planı</span>
            {planData && (
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                ({totalTopics} konu, {producedTopics} üretildi, {totalTopics - producedTopics} bekliyor)
              </span>
            )}
          </div>
          
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            {planData?.plan?.length > 0 && unproducedRows.length > 0 && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{
                  fontSize: 11,
                  background: allUnproducedSelected ? "rgba(99, 102, 241, 0.18)" : undefined,
                  color: allUnproducedSelected ? "#818cf8" : undefined,
                  border: allUnproducedSelected ? "1px solid rgba(99, 102, 241, 0.4)" : "1px solid var(--border-subtle)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4
                }}
                onClick={handleSelectUnproduced}
                title="Üretilmeyen (bekleyen) tüm plan konularını seçer veya seçimi kaldırır"
              >
                {allUnproducedSelected ? "✓ Üretilmeyenler Seçildi" : `⚡ Üretilmeyen Tüm Planları Seç (${unproducedRows.length})`}
              </button>
            )}
            {selectedRowIds.length > 0 && (
              <button
                className="btn btn-danger btn-sm"
                style={{ fontSize: 11 }}
                onClick={handleBatchDelete}
              >
                🗑️ Seçilenleri Sil ({selectedRowIds.length})
              </button>
            )}
            <button
              className="btn btn-ghost btn-sm"
              style={{ fontSize: 11 }}
              onClick={() => setShowAddTopicModal(true)}
            >
              + Manuel Ekle
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <input
                type="number"
                min="1"
                max="50"
                value={planCount}
                onChange={e => setPlanCount(Math.max(1, parseInt(e.target.value) || 1))}
                style={{
                  width: 50, padding: "4px 6px", fontSize: 11,
                  background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)", color: "var(--text-primary)"
                }}
              />
              <button
                className="btn btn-primary btn-sm"
                style={{ fontSize: 11 }}
                onClick={handlePlan}
                disabled={planning}
              >
                {planning ? "⏳ Planlanıyor..." : "✨ AI ile Planla"}
              </button>
            </div>
            <button className="btn btn-ghost btn-sm" style={{ fontSize: 11 }} onClick={fetchPlan}>
              ↻
            </button>
          </div>
        </div>

        {/* Gemini Extension Prompt Banner */}
        <div style={{
          padding: "10px 14px", background: "rgba(99,102,241,0.08)",
          border: "1px solid rgba(99,102,241,0.2)", borderRadius: "var(--radius-md)",
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-primary)" }}>
            <span style={{ fontSize: 16 }}>🤖</span>
            <span>
              <strong>Gemini Web AI Asistanı:</strong> Chrome eklentisini açıp sol üstten <strong>"👥 {group.name}"</strong> seçerek tüm diller için tek tıkla çok dilli video üretebilirsiniz.
            </span>
          </div>
        </div>

        {planData?.plan?.length > 0 && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11.5, color: "var(--text-muted)", padding: "2px 2px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span>Seçim:</span>
              <button
                type="button"
                style={{ background: "none", border: "none", color: "var(--accent-primary)", cursor: "pointer", padding: 0, fontSize: 11.5, textDecoration: "underline" }}
                onClick={() => setSelectedRowIds(planData.plan.map(r => r.id))}
              >
                Tümünü Seç ({planData.plan.length})
              </button>
              {unproducedRows.length > 0 && (
                <>
                  <span>•</span>
                  <button
                    type="button"
                    style={{ background: "none", border: "none", color: allUnproducedSelected ? "#818cf8" : "var(--accent-primary)", cursor: "pointer", padding: 0, fontSize: 11.5, textDecoration: "underline", fontWeight: 600 }}
                    onClick={handleSelectUnproduced}
                  >
                    {allUnproducedSelected ? "Üretilmeyenlerin Seçimini Kaldır" : `Üretilmeyen Tüm Planları Seç (${unproducedRows.length})`}
                  </button>
                </>
              )}
              {selectedRowIds.length > 0 && (
                <>
                  <span>•</span>
                  <button
                    type="button"
                    style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: 0, fontSize: 11.5, textDecoration: "underline" }}
                    onClick={() => setSelectedRowIds([])}
                  >
                    Seçimi Temizle
                  </button>
                </>
              )}
            </div>
            {selectedRowIds.length > 0 && (
              <span style={{ color: "var(--accent-primary)", fontWeight: 600 }}>
                {selectedRowIds.length} plan seçildi
              </span>
            )}
          </div>
        )}

        {/* Table */}
        {planData?.plan && planData.plan.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table className="plan-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left", color: "var(--text-muted)" }}>
                  <th style={{ width: 32, padding: "8px 6px" }}>
                    <input
                      type="checkbox"
                      checked={planData.plan.length > 0 && selectedRowIds.length === planData.plan.length}
                      onChange={e => {
                        if (e.target.checked) setSelectedRowIds(planData.plan.map(r => r.id));
                        else setSelectedRowIds([]);
                      }}
                    />
                  </th>
                  <th style={{ width: 45, padding: "8px 6px" }}>#ID</th>
                  <th style={{ padding: "8px 10px" }}>Konu / Başlık</th>
                  <th style={{ width: 130, padding: "8px 10px" }}>Hedef Diller</th>
                  <th style={{ width: 65, padding: "8px 10px", textAlign: "center" }}>Üretim</th>
                  <th style={{ width: 110, padding: "8px 10px", textAlign: "center" }}>Yükleme Durumu</th>
                  <th style={{ width: 130, padding: "8px 6px", textAlign: "center" }}>İşlem</th>
                </tr>
              </thead>
              <tbody>
                {planData.plan.map(row => {
                  const isProduced = row.uretildi?.toLowerCase() === "evet" || row.uretildi === "yes" || row.uretildi === "true" || row.uretildi === "1";
                  const isUploaded = row.yuklendi?.toLowerCase() === "evet" || row.yuklendi === "yes" || row.yuklendi === "true" || row.yuklendi === "1";
                  const isSelected = selectedRowIds.includes(row.id);
                  return (
                    <tr
                      key={row.id}
                      style={{
                        borderBottom: "1px solid rgba(255,255,255,0.03)",
                        background: isSelected ? "var(--accent-muted)" : isProduced ? "rgba(52,211,153,0.03)" : "transparent"
                      }}
                    >
                      <td style={{ padding: "8px 6px" }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={e => {
                            if (e.target.checked) setSelectedRowIds(p => [...p, row.id]);
                            else setSelectedRowIds(p => p.filter(id => id !== row.id));
                          }}
                        />
                      </td>
                      <td style={{ padding: "8px 6px", fontFamily: "monospace", color: "var(--text-muted)" }}>
                        #{row.id}
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        <div style={{ fontWeight: 500, color: "var(--text-primary)" }}>
                          {row.baslik || row.konu}
                        </div>
                        {row.notlar && (
                          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                            {row.notlar}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                          {memberChannels.map(mc => (
                            <span
                              key={mc.channel_id}
                              style={{
                                fontSize: 10, padding: "1px 5px", borderRadius: 3,
                                background: "rgba(124,110,242,0.15)", color: "#a5b4fc", fontWeight: 600
                              }}
                            >
                              {(mc.language || "").toUpperCase()}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "center" }}>
                        <span className={`chip chip-${isProduced ? "success" : "warning"}`} style={{ fontSize: 10 }}>
                          {isProduced ? "✅ Üretildi" : "⏳ Bekliyor"}
                        </span>
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "center" }}>
                        {isUploaded ? (
                          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                            <span className="chip chip-success" style={{ fontSize: 9.5, padding: "1px 5px" }}>📤 Yüklendi</span>
                            {row.yayim_tarihi && (
                              <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "monospace" }}>
                                {row.yayim_tarihi}
                              </span>
                            )}
                          </div>
                        ) : isProduced ? (
                          <span className="chip chip-warning" style={{ fontSize: 9.5, padding: "1px 5px" }}>⏳ Yüklenmedi</span>
                        ) : (
                          <span style={{ color: "var(--text-muted)", fontSize: 11 }}>-</span>
                        )}
                      </td>
                      <td style={{ padding: "8px 6px", textAlign: "center" }}>
                        <div style={{ display: "flex", gap: 4, justifyContent: "center", alignItems: "center" }}>
                          {isProduced && !isUploaded && (
                            <button
                              className="btn btn-primary btn-sm"
                              style={{ padding: "2px 8px", fontSize: 10, display: "inline-flex", alignItems: "center", gap: 3, background: "linear-gradient(135deg, #6366f1, #8b5cf6)", border: "none" }}
                              onClick={() => handleUploadGroupVideo(row)}
                              disabled={uploadingRowId === row.id}
                              title="Tüm üye kanallara akıllı zamanlama ile YouTube Studio'ya yükle"
                            >
                              {uploadingRowId === row.id ? "⏳..." : "📤 Yükle"}
                            </button>
                          )}
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ color: "var(--danger)", padding: "2px 6px", fontSize: 11 }}
                            onClick={() => handleDeletePlanRow(row.id)}
                            title="Plan Satırını Sil"
                          >
                            🗑
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{
            padding: "24px 12px", textAlign: "center", fontSize: 12,
            color: "var(--text-muted)", border: "1px dashed var(--border-subtle)",
            borderRadius: "var(--radius-md)"
          }}>
            Henüz grup için planlanmış içerik yok. "✨ AI ile Planla" veya "+ Manuel Ekle" butonuna basarak ortak konular oluşturun.
          </div>
        )}
      </div>

      {/* Manuel Konu Ekleme Modalı */}
      <Modal open={showAddTopicModal} onClose={() => setShowAddTopicModal(false)} title="Gruba Manuel Konu Ekle">
        <form onSubmit={handleManualAddTopic} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="form-group">
            <label className="form-label">Konu / Başlık</label>
            <input
              type="text"
              className="form-input"
              placeholder="Örn: Komşunuzun evinde gördüğünüz en garip şey neydi?"
              value={newTopicTitle}
              onChange={e => setNewTopicTitle(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label className="form-label">Yönergeler / Notlar (Opsiyonel)</label>
            <textarea
              className="form-input"
              rows={3}
              placeholder="Senaryo için özel direktifler veya Reddit soru detayları..."
              value={newTopicNotes}
              onChange={e => setNewTopicNotes(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
            <button type="button" className="btn btn-ghost" onClick={() => setShowAddTopicModal(false)}>
              İptal
            </button>
            <button type="submit" className="btn btn-primary" disabled={addingTopic || !newTopicTitle.trim()}>
              {addingTopic ? "Ekleniyor..." : "Gruba Ekle"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   COPY BUTTON
   ══════════════════════════════════════════════════════════════════ */

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false);
  return (
    <button className="btn btn-ghost btn-sm"
      style={{ fontSize: 11, padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: 5, opacity: copied ? 0.75 : 1 }}
      onClick={() => navigator.clipboard.writeText(text || "").then(() => {
        setCopied(true); setTimeout(() => setCopied(false), 2000);
      })}>
      {copied ? <><Check size={12} style={{ color: "var(--success)" }} /> Kopyalandı</> : <><Copy size={12} /> {label}</>}
    </button>
  );
}

/* ══════════════════════════════════════════════════════════════════
   VIDEO CARD
   ══════════════════════════════════════════════════════════════════ */

function VideoCard({ video, onArchive, onOpenPatcher }) {
  const [expanded, setExpanded] = useState(false);

  const openStudio = () => {
    const payload = {
      title: video.title,
      description: video.description,
      tags: video.tags,
      folder: video.folder,
      video_path: video.video_path,
      plan_id: video.plan_id || "",
      language: video.language || "en",
      timestamp: Date.now(),
    };

    if (video.video_path) {
      navigator.clipboard.writeText(video.video_path)
        .then(() => console.log("[YT-OTO] Video path copied to clipboard:", video.video_path))
        .catch(err => console.error("[YT-OTO] Clipboard error:", err));
    }

    window.postMessage({ type: "YT_STUDIO_SEND", payload }, "*");
    localStorage.setItem("yt_studio_pending", JSON.stringify(payload));
    window.open("https://studio.youtube.com", "_blank");
  };

  return (
    <div className="card" style={{ opacity: video.archived ? 0.55 : 1, transition: "opacity 0.2s" }}>
      <div style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 10 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 8, flexShrink: 0,
            background: video.shorts_mode ? "rgba(244, 63, 94, 0.12)" : "var(--accent-muted)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: video.shorts_mode ? "var(--danger)" : "var(--accent-primary)"
          }}>
            {video.shorts_mode ? <Smartphone size={20} /> : <Film size={20} />}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)",
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", marginBottom: 3 }}>
              {video.title || "(Başlık yok)"}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
              <code style={{ fontSize: 10.5, color: "var(--text-muted)", fontFamily: "monospace" }}>{video.folder}</code>
              {video.shorts_mode && (
                <span className="chip" style={{ fontSize: 9.5, padding: "2px 6px",
                  background: "rgba(244, 63, 94, 0.15)", color: "var(--danger)", border: "1px solid rgba(244, 63, 94, 0.3)" }}>SHORTS</span>
              )}
              {video.resolution && <span className="chip chip-muted" style={{ fontSize: 9.5 }}>{video.resolution}</span>}
              {video.archived && (
                <span className="chip" style={{ fontSize: 9.5,
                  background: "rgba(16, 185, 129, 0.12)", color: "var(--success)", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                  <Check size={10} style={{ marginRight: 3 }} /> Arşivlendi
                </span>
              )}
            </div>
          </div>
          <button onClick={() => setExpanded(x => !x)}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 13, padding: "4px", display: "inline-flex", alignItems: "center" }}>
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        {video.tags?.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
            {video.tags.slice(0, 7).map((tag, i) => <span key={i} className="chip chip-muted" style={{ fontSize: 10 }}>#{tag}</span>)}
            {video.tags.length > 7 && <span className="chip chip-muted" style={{ fontSize: 10 }}>+{video.tags.length - 7}</span>}
          </div>
        )}

        {expanded && (
          <div style={{ marginBottom: 12, borderTop: "1px solid var(--border-subtle)", paddingTop: 12, display: "flex", flexDirection: "column", gap: 10 }}>
            {video.description && (
              <div>
                <div style={{ fontSize: 10.5, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Açıklama</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6,
                  maxHeight: 100, overflowY: "auto", background: "var(--bg-primary)", borderRadius: 6, padding: "8px 10px" }}>
                  {video.description}
                </div>
              </div>
            )}
            {video.tags?.length > 0 && (
              <div>
                <div style={{ fontSize: 10.5, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Tüm Etiketler</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", background: "var(--bg-primary)", borderRadius: 6, padding: "8px 10px" }}>
                  {video.tags.join(", ")}
                </div>
              </div>
            )}
          </div>
        )}

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <CopyButton text={video.title} label="Başlık" />
          <CopyButton text={video.description} label="Açıklama" />
          <CopyButton text={(video.tags || []).join(", ")} label="Etiketler" />
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => onOpenPatcher && onOpenPatcher(video)}
              style={{
                fontSize: 11,
                padding: "5px 10px",
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                color: "#38bdf8",
                background: "rgba(56, 189, 248, 0.08)",
                border: "1px solid rgba(56, 189, 248, 0.3)"
              }}
              title="Hatalı sahneleri AI ile saniyeler içinde değiştir"
            >
              <Scissors size={12} /> AI Sahne Düzenle
            </button>
            <button className="btn btn-primary btn-sm" onClick={openStudio}
              style={{ fontSize: 11, padding: "5px 12px", display: "inline-flex", alignItems: "center", gap: 5 }}>
              <ExternalLink size={12} /> Studio'ya Gönder
            </button>
            {!video.archived
              ? <button className="btn btn-ghost btn-sm" onClick={() => onArchive(video.folder, false)} style={{ fontSize: 11, display: "inline-flex", alignItems: "center", gap: 5 }}>
                  <Archive size={12} /> Arşivle
                </button>
              : <button className="btn btn-ghost btn-sm" onClick={() => onArchive(video.folder, true)} style={{ fontSize: 11, display: "inline-flex", alignItems: "center", gap: 5 }}>
                  <RotateCcw size={12} /> Geri Al
                </button>}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   AI CHAT PAGE (Kanal Zeka & Zihin Haritası)
   ══════════════════════════════════════════════════════════════════ */

function ProductionAssistant({ selectedChannelId }) {
  const [command, setCommand] = useState("");
  const [job, setJob] = useState(() => {
    try {
      const savedJob = localStorage.getItem("lmstudio-production-assistant-job");
      return savedJob ? JSON.parse(savedJob) : null;
    } catch (error) {
      console.warn("Önceki asistan görevi geri yüklenemedi:", error);
      return null;
    }
  });
  const [submitting, setSubmitting] = useState(false);
  const [requestError, setRequestError] = useState("");
  const active = job && (job.status === "pending" || job.status === "running");

  useEffect(() => {
    if (!job) return;
    try {
      localStorage.setItem("lmstudio-production-assistant-job", JSON.stringify(job));
    } catch (error) {
      console.warn("Asistan görevi bu tarayıcıda kaydedilemedi:", error);
    }
  }, [job]);

  useEffect(() => {
    if (!job?.exec_id || !active) return undefined;
    const poll = async () => {
      try {
        const response = await fetch(`/api/run/status/${job.exec_id}`);
        const data = await response.json();
        if (response.ok) setJob(current => current?.exec_id === job.exec_id ? data : current);
      } catch (error) {
        console.error("Üretim durumu alınamadı:", error);
      }
    };
    poll();
    const intervalId = setInterval(poll, 2000);
    return () => clearInterval(intervalId);
  }, [job?.exec_id, job?.status, active]);

  const submitCommand = async (event) => {
    event.preventDefault();
    const message = command.trim();
    if (!message || submitting || active) return;
    setSubmitting(true);
    setRequestError("");
    try {
      const response = await fetch("/api/assistant/produce", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, selected_channel_id: selectedChannelId || null })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Komut işlenemedi.");
      setJob(data);
      setCommand("");
    } catch (error) {
      setRequestError(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  const progress = Math.max(0, Math.min(100, Number(job?.progress || 0)));
  const statusLabel = {
    pending: "Kuyruğa alındı",
    running: "Çalışıyor",
    success: "Tamamlandı",
    failed: "Hata"
  }[job?.status] || "";

  return (
    <div style={{ maxWidth: 920, margin: "0 auto", display: "flex", flexDirection: "column", gap: 18 }}>
      <section style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: 16, padding: 24 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
          <div style={{ width: 42, height: 42, borderRadius: 12, display: "grid", placeItems: "center", color: "var(--accent-primary)", background: "var(--accent-muted, #eff6ff)" }}>
            <Sparkles size={21} />
          </div>
          <div>
            <h2 style={{ margin: 0, color: "var(--text-primary)", fontSize: 19, fontWeight: 700 }}>LM Studio Üretim Asistanı</h2>
            <p style={{ margin: "6px 0 0", color: "var(--text-muted)", fontSize: 13, lineHeight: 1.6 }}>
              İsteğinizi LM Studio yorumlar; seçtiğiniz sağlayıcı içerik planını gerektiğinde tamamlar ve videoları sırayla üretir.
            </p>
          </div>
        </div>
        <form onSubmit={submitCommand} style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 10 }}>
          <textarea
            className="form-input"
            value={command}
            onChange={event => setCommand(event.target.value)}
            placeholder="Örn. Reddit hikâyeleri için Gemini API ile 3 video üret"
            rows={3}
            disabled={active || submitting}
            aria-label="Video üretim komutu"
            style={{ resize: "vertical", minHeight: 84, lineHeight: 1.5 }}
          />
          {requestError && <div role="alert" style={{ color: "var(--danger, #b91c1c)", fontSize: 13 }}>{requestError}</div>}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ color: "var(--text-muted)", fontSize: 12 }}>Tek komutta en fazla 20 video • Mevcut plan korunur</span>
            <button className="btn btn-primary" type="submit" disabled={!command.trim() || submitting || active}>
              {submitting ? <><Loader2 size={15} className="spin" /> Komut yorumlanıyor...</> : <><Send size={15} /> Üretimi başlat</>}
            </button>
          </div>
        </form>
      </section>

      {job && (
        <section aria-live="polite" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: 16, padding: 22 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9, color: job.status === "failed" ? "var(--danger, #b91c1c)" : "var(--text-primary)" }}>
            {job.status === "failed" ? <AlertCircle size={18} /> : job.status === "success" ? <CheckCircle2 size={18} /> : <Loader2 size={18} className="spin" />}
            <strong style={{ fontSize: 14 }}>{statusLabel}</strong>
          </div>
          {job.intent && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
              {[job.intent.provider, job.intent.category, `${job.intent.count} video`, ...(job.intent.channels || [])].filter(Boolean).map((item, index) => (
                <span key={`${item}-${index}`} style={{ color: "var(--text-secondary)", background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)", padding: "4px 9px", borderRadius: 20, fontSize: 11 }}>
                  {item}
                </span>
              ))}
            </div>
          )}
          <p style={{ color: "var(--text-secondary)", fontSize: 13, lineHeight: 1.6, margin: "14px 0 10px" }}>{job.message}</p>
          {(job.status === "running" || job.status === "pending") && (
            <div style={{ height: 6, background: "var(--bg-primary)", borderRadius: 8, overflow: "hidden" }}>
              <div style={{ width: `${progress}%`, height: "100%", background: "var(--accent-primary)", transition: "width 250ms ease" }} />
            </div>
          )}
          {job.error && <p role="alert" style={{ color: "var(--danger, #b91c1c)", fontSize: 12, whiteSpace: "pre-wrap" }}>{job.error}</p>}
          {Array.isArray(job.result) && job.result.length > 0 && (
            <div style={{ display: "grid", gap: 8, marginTop: 14 }}>
              {job.result.map((video, index) => (
                <div key={`${video.channel_id}-${video.plan_id}-${index}`} style={{ display: "flex", alignItems: "center", gap: 9, padding: "10px 12px", borderRadius: 9, background: "var(--bg-primary)", color: "var(--text-primary)", fontSize: 12 }}>
                  <Video size={15} color="var(--accent-primary)" />
                  <span><strong>{video.title || `Video ${index + 1}`}</strong> · {video.channel_name}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function ChatPage({ selectedChannelId, channels }) {
  const channel = channels.find(c => c.channel_id === selectedChannelId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mindMap, setMindMap] = useState(null);
  const [loadingMindMap, setLoadingMindMap] = useState(false);
  const [assistantMode, setAssistantMode] = useState(true);

  const modeSwitch = (
    <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
      <button className={`btn ${assistantMode ? "btn-primary" : "btn-ghost"}`} onClick={() => setAssistantMode(true)}>
        <Sparkles size={15} /> Üretim Asistanı
      </button>
      <button className={`btn ${!assistantMode ? "btn-primary" : "btn-ghost"}`} onClick={() => setAssistantMode(false)}>
        <MessageSquare size={15} /> Kanal Sohbeti
      </button>
    </div>
  );

  // Load mind map and initial welcome message when channel changes
  useEffect(() => {
    if (!channel) {
      setMessages([]);
      setMindMap(null);
      return;
    }

    setMessages([
      {
        role: "model",
        content: `Merhaba! Ben **Kanal Zeka AI**. **${channel.name}** kanalı için büyüme, içerik ve zihin haritası danışmanıyım. 
        
İnternet erişimim sayesinde son trendleri arayabilir, YouTube videolarının detaylarını çekebilir, zihin haritanızı ve içerik planınızı doğrudan güncelleyebilirim. 

Nasıl yardımcı olabilirim? Aşağıdaki hızlı şablonları kullanabilir veya bana dilediğinizi sorabilirsiniz.`
      }
    ]);

    fetchMindMap();
  }, [selectedChannelId]);

  const fetchMindMap = async () => {
    if (!selectedChannelId) return;
    setLoadingMindMap(true);
    try {
      const res = await fetch(`/api/channels/${selectedChannelId}/mind-map`);
      const data = await res.json();
      setMindMap(data.mind_map || { themes: {} });
    } catch (e) {
      console.error("Mind map loading error:", e);
    } finally {
      setLoadingMindMap(false);
    }
  };

  const handleSend = async (customMsg = "") => {
    const textToSend = (customMsg || input).trim();
    if (!textToSend || loading || !selectedChannelId) return;

    setInput("");
    const userMsg = { role: "user", content: textToSend };
    const newMsgs = [...messages, userMsg];
    setMessages(newMsgs);
    setLoading(true);

    try {
      const history = newMsgs.slice(1, -1);
      
      const res = await fetch(`/api/channels/${selectedChannelId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: textToSend, history: history })
      });
      const data = await res.json();
      
      if (data.success) {
        setMessages(prev => [...prev, { role: "model", content: data.response }]);
        fetchMindMap();
      } else {
        setMessages(prev => [...prev, { role: "model", content: `Hata: ${data.detail || "Bilinmeyen bir hata oldu."}` }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: "model", content: `Bağlantı hatası: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  if (assistantMode) {
    return (
      <div>
        {modeSwitch}
        <ProductionAssistant selectedChannelId={selectedChannelId} />
      </div>
    );
  }

  if (!selectedChannelId) {
    return (
      <div>
        {modeSwitch}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "70vh", color: "var(--text-muted)", gap: 12 }}>
          <span style={{ fontSize: 48 }}>💬</span>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>Aktif Kanal Seçilmedi</h3>
          <p style={{ fontSize: 13, maxWidth: 300, textAlign: "center" }}>Kanal sohbeti için lütfen soldaki kanallar listesinden bir kanal seçin.</p>
        </div>
      </div>
    );
  }

  const templates = [
    { label: "💡 Yeni Video Fikirleri Planla", prompt: "Kanalımın kategorisine uygun 5 adet yeni video konusu fikirleştir, başlık ve anahtar kelimelerini belirle ve bunları içerik planıma eklemek için ACTION_JSON formatında yanıt ver." },
    { label: "🗺️ Zihin Haritasını Listele", prompt: "Zihin haritamı yükle ve kategorileri bana özetle." },
    { label: "🔍 YouTube Trendlerini Ara", prompt: "Kanal kategorimde şu anda dünyada ve Türkiye'de hangi konular trend? Google Search kullanarak araştır ve bana 3 video konusu öner." },
    { label: "📹 YouTube Videosunu Analiz Et", prompt: "Şu YouTube videosunun detaylarını incele ve bana kanalım için nasıl uyarlayabileceğimi söyle: https://www.youtube.com/watch?v=5Ufoxk15RDk" }
  ];

  return (
    <div>
    {modeSwitch}
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, height: "calc(100vh - 160px)", minHeight: 500 }}>
      {/* Sol Panel: Zihin Haritası ve Kanal Bilgileri */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16, background: "rgba(30, 41, 59, 0.3)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: 12, padding: 20, overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", paddingBottom: 12 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>🗺️ Kanal Zihin Haritası</h2>
            <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>Zihin haritası, içerik planındaki tüm konuları hiyerarşik olarak gruplar.</p>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={fetchMindMap} disabled={loadingMindMap} style={{ fontSize: 12 }}>
            {loadingMindMap ? "🔄 Yükleniyor..." : "⚡ Yenile"}
          </button>
        </div>

        {loadingMindMap ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexGrow: 1, color: "var(--text-muted)", fontSize: 13 }}>
            Zihin haritası yükleniyor...
          </div>
        ) : !mindMap || !mindMap.themes || Object.keys(mindMap.themes).length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flexGrow: 1, color: "var(--text-muted)", padding: 40, textAlign: "center", gap: 12 }}>
            <span style={{ fontSize: 32 }}>🗺️</span>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Henüz Zihin Haritası Oluşturulmadı</div>
            <p style={{ fontSize: 11, maxWidth: 260 }}>İçerik planındaki konuları gruplamak için sağdaki AI Sohbet'ten yeni konular planlayabilir veya zihin haritasını senkronize edebilirsiniz.</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {Object.entries(mindMap.themes).map(([themeName, topics]) => (
              <div key={themeName} style={{ background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: 8, padding: 14 }}>
                <h3 style={{ fontSize: 13.5, fontWeight: 700, color: "#38bdf8", borderBottom: "1px dashed rgba(56, 189, 248, 0.2)", paddingBottom: 6, marginBottom: 8, display: "flex", justifyContent: "space-between" }}>
                  <span>📂 {themeName}</span>
                  <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{topics.length} Video</span>
                </h3>
                <ul style={{ display: "flex", flexDirection: "column", gap: 6, margin: 0, paddingLeft: 12 }}>
                  {topics.map((t, idx) => (
                    <li key={idx} style={{ fontSize: 12.5, color: "var(--text-primary)", listStyleType: "disc" }}>
                      {t}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Sağ Panel: AI Sohbet */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14, background: "rgba(30, 41, 59, 0.3)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: 12, padding: 20, height: "100%" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", paddingBottom: 12 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ color: "#38bdf8" }}>🤖</span> Kanal Zeka AI
          </h2>
          <span style={{ background: "rgba(16, 185, 129, 0.1)", color: "#10b981", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 12, border: "1px solid rgba(16, 185, 129, 0.2)" }}>
            Google Grounding Aktif
          </span>
        </div>

        {/* Mesaj Listesi */}
        <div style={{ flexGrow: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14, paddingRight: 4, minHeight: 200 }}>
          {messages.map((m, idx) => (
            <div key={idx} style={{ display: "flex", flexDirection: "column", alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "85%" }}>
              <div style={{
                background: m.role === "user" ? "linear-gradient(135deg, #0284c7, #0369a1)" : "rgba(255, 255, 255, 0.04)",
                border: m.role === "user" ? "none" : "1px solid rgba(255, 255, 255, 0.06)",
                borderRadius: m.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                padding: "10px 14px",
                fontSize: 13,
                color: "#f8fafc",
                lineHeight: 1.5,
                whiteSpace: "pre-wrap"
              }}>
                {m.content}
              </div>
              <span style={{ fontSize: 10, color: "var(--text-muted)", alignSelf: m.role === "user" ? "flex-end" : "flex-start", marginTop: 4, padding: "0 4px" }}>
                {m.role === "user" ? "Siz" : "AI"}
              </span>
            </div>
          ))}
          {loading && (
            <div style={{ display: "flex", alignSelf: "flex-start", gap: 6, alignItems: "center", background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.04)", borderRadius: 12, padding: "10px 14px" }}>
              <span className="spinner-sm" style={{ width: 12, height: 12 }}></span>
              <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>Düşünülüyor ve araçlar çalıştırılıyor...</span>
            </div>
          )}
        </div>

        {/* Hızlı Şablonlar */}
        {messages.length === 1 && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {templates.map((t, idx) => (
              <button key={idx} className="btn btn-ghost btn-sm" onClick={() => handleSend(t.prompt)} style={{ justifyContent: "flex-start", fontSize: 11.5, height: "auto", padding: "8px 10px", textAlign: "left", whiteSpace: "normal", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
                {t.label}
              </button>
            ))}
          </div>
        )}

        {/* Girdi Çubuğu */}
        <div style={{ display: "flex", gap: 8, borderTop: "1px solid rgba(255, 255, 255, 0.08)", paddingTop: 12 }}>
          <input type="text" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSend()} placeholder="Mesajınızı yazın (örn: 'Kanalım için 3 adet uzay konusu öner ve plana ekle')..." style={{ flexGrow: 1, background: "rgba(15, 23, 42, 0.4)", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#f8fafc", outline: "none" }} disabled={loading} />
          <button className="btn btn-primary" onClick={() => handleSend()} disabled={loading || !input.trim()}>
            Gönder
          </button>
        </div>
      </div>
    </div>
    </div>
  );
}

function InstagramSchedulePage({ channels, selectedChannelId }) {
  const instagramChannels = channels.filter(channel => channel.instagram && channel.instagram_username);
  const [channelId, setChannelId] = useState(
    instagramChannels.some(channel => channel.channel_id === selectedChannelId)
      ? selectedChannelId
      : instagramChannels[0]?.channel_id || ""
  );
  const [info, setInfo] = useState(null);
  const [folder, setFolder] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!instagramChannels.some(channel => channel.channel_id === channelId)) {
      setChannelId(instagramChannels[0]?.channel_id || "");
    }
  }, [channels, channelId]);

  const fetchInfo = useCallback(async () => {
    if (!channelId) {
      setInfo(null);
      return;
    }
    setError("");
    try {
      const response = await fetch(`/api/channels/${channelId}/instagram-schedule-info`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Instagram planlama bilgileri alınamadı.");
      setInfo(data);
      setDate(data.suggested_date);
      setTime(data.suggested_time);
    } catch (fetchError) {
      setError(fetchError.message);
      setInfo(null);
    }
  }, [channelId]);

  useEffect(() => { fetchInfo(); }, [fetchInfo]);

  const schedulePost = async (event) => {
    event.preventDefault();
    const video = info?.ready_videos?.find(item => item.folder === folder);
    if (!video || !date || !time) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/instagram/schedules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder, scheduled_date: date, scheduled_time: time, caption: caption || video.description || video.title })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Instagram gönderisi planlanamadı.");
      setNotice(data.message);
      setFolder("");
      setCaption("");
      await fetchInfo();
    } catch (scheduleError) {
      setError(scheduleError.message);
    } finally {
      setBusy(false);
    }
  };

  const cancelPost = async (scheduleId) => {
    try {
      const response = await fetch(`/api/instagram/schedules/${scheduleId}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Plan iptal edilemedi.");
      await fetchInfo();
    } catch (cancelError) {
      setError(cancelError.message);
    }
  };

  if (instagramChannels.length === 0) {
    return (
      <div className="card" style={{ maxWidth: 760, margin: "36px auto", padding: 28 }}>
        <h2 style={{ marginTop: 0, color: "var(--text-primary)" }}>Instagram hesabı ekleyin</h2>
        <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
          Kanalı düzenleyip Instagram paylaşımını açın ve kullanıcı adını yazın. Paylaşım saatinde çalışan Chrome eklentisi, giriş yapılmış Instagram web oturumunu kullanarak videoyu yükler.
        </p>
      </div>
    );
  }

  const statusLabel = { scheduled: "Planlandı", publishing: "Yükleniyor", published: "Paylaşıldı", failed: "Hata", needs_review: "Kontrol gerekli" };

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", display: "grid", gap: 18, paddingBottom: 40 }}>
      <section className="card" style={{ padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 18 }}>
          <div>
            <h2 style={{ margin: 0, color: "var(--text-primary)", fontSize: 20 }}>Instagram Reels Planlama</h2>
            <p style={{ color: "var(--text-muted)", fontSize: 12, margin: "6px 0 0" }}>Gönderi seçtiğiniz saate kadar bekler; Chrome eklentisi zamanı gelince açık Instagram oturumundan yükler.</p>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={fetchInfo}><RefreshCw size={14} /> Yenile</button>
        </div>
        <form onSubmit={schedulePost} style={{ display: "grid", gap: 14 }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Instagram hesabı / kanal</label>
            <select className="form-input" value={channelId} onChange={event => { setChannelId(event.target.value); setFolder(""); }}>
              {instagramChannels.map(channel => <option value={channel.channel_id} key={channel.channel_id}>@{channel.instagram_username} · {channel.name}</option>)}
            </select>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.5fr) repeat(2, minmax(150px, 1fr))", gap: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Hazır video</label>
              <select className="form-input" value={folder} onChange={event => {
                const selected = info?.ready_videos?.find(item => item.folder === event.target.value);
                setFolder(event.target.value);
                setCaption(selected?.description || selected?.title || "");
              }}>
                <option value="">Video seçin…</option>
                {(info?.ready_videos || []).map(video => <option value={video.folder} key={video.folder}>{video.title}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Paylaşım tarihi ({info?.timezone || "hesap saat dilimi"})</label>
              <input className="form-input" type="date" value={date} min={new Date().toISOString().slice(0, 10)} onChange={event => setDate(event.target.value)} required />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Saat</label>
              <input className="form-input" type="time" value={time} onChange={event => setTime(event.target.value)} required />
            </div>
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Açıklama / caption</label>
            <textarea className="form-input" value={caption} rows={3} maxLength={2200} onChange={event => setCaption(event.target.value)} placeholder="Reels açıklaması" />
            <span style={{ fontSize: 11, color: "var(--text-muted)", textAlign: "right" }}>{caption.length}/2200</span>
          </div>
          {error && <div role="alert" style={{ color: "var(--danger)", fontSize: 13 }}>{error}</div>}
          {notice && <div role="status" style={{ color: "var(--success)", fontSize: 13 }}>{notice}</div>}
          {info && <div style={{ background: "var(--accent-muted)", color: "var(--text-secondary)", borderRadius: 8, padding: 12, fontSize: 12 }}>Planlanan saatte paylaşım için bilgisayarınız, sunucu ve Chrome eklentisi açık olmalı; Instagram’da doğru hesaba giriş yapılmış olmalı. Instagram sekmesi otomatik açılabilir.</div>}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button className="btn btn-primary" type="submit" disabled={!folder || busy || !info?.configured}>
              {busy ? <><Loader2 size={14} className="spin" /> Planlanıyor…</> : <><CalendarDays size={14} /> Instagram için planla</>}
            </button>
          </div>
        </form>
      </section>

      <section className="card" style={{ padding: 22 }}>
        <h3 style={{ margin: "0 0 14px", color: "var(--text-primary)" }}>Planlanan gönderiler</h3>
        {!info?.schedules?.length ? <p style={{ color: "var(--text-muted)", fontSize: 13 }}>Bu hesap için henüz gönderi planlanmadı.</p> : (
          <div style={{ display: "grid", gap: 10 }}>
            {info.schedules.map(schedule => (
              <div key={schedule.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, border: "1px solid var(--border-subtle)", borderRadius: 10, padding: 12 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: 13 }}>{schedule.title || schedule.folder}</div>
                  <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 4 }}>@{schedule.instagram_username} · {new Date(schedule.scheduled_at).toLocaleString()} · {statusLabel[schedule.status] || schedule.status}</div>
                  {schedule.last_error && <div style={{ color: "var(--danger)", fontSize: 11, marginTop: 4 }}>{schedule.last_error}</div>}
                </div>
                {schedule.status === "scheduled" && <button className="btn btn-ghost btn-sm" onClick={() => cancelPost(schedule.id)}>İptal</button>}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   SHORTS CREATOR PAGE (Uzundan Shorts Türetme)
   ══════════════════════════════════════════════════════════════════ */

function ShortsCreatorPage({ selectedChannelId, channels, onStartShorts }) {
  const [activeChannelId, setActiveChannelId] = useState(selectedChannelId || (channels[0]?.channel_id || ""));
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState("");
  const [count, setCount] = useState(4);
  const [loadingVideos, setLoadingVideos] = useState(false);
  const [generating, setGenerating] = useState(false);
  
  // Arka plan görevi izleme
  const [execId, setExecId] = useState(null);
  const [execStatus, setExecStatus] = useState(null);
  const [execMessage, setExecMessage] = useState("");

  // Kanal değiştiğinde videoları yeniden yükle
  const fetchLongVideos = useCallback(async (chanId) => {
    if (!chanId) {
      setVideos([]);
      return;
    }
    setLoadingVideos(true);
    setSelectedVideo("");
    try {
      const res = await fetch(`/api/channels/${chanId}/long-videos`);
      if (res.ok) {
        const data = await res.json();
        setVideos(data.videos || []);
      } else {
        setVideos([]);
      }
    } catch (e) {
      console.error("Uzun videolar yüklenirken hata:", e);
      setVideos([]);
    }
    setLoadingVideos(false);
  }, []);

  useEffect(() => {
    fetchLongVideos(activeChannelId);
  }, [activeChannelId, fetchLongVideos]);

  // Arka plan görev takibi
  useEffect(() => {
    if (!execId) return;

    let intervalId = setInterval(async () => {
      try {
        const r = await fetch(`/api/run/status/${execId}`);
        if (r.ok) {
          const statusData = await r.json();
          setExecStatus(statusData.status);
          setExecMessage(statusData.message || "");
          
          if (statusData.status === "success" || statusData.status === "failed") {
            clearInterval(intervalId);
            setGenerating(false);
          }
        }
      } catch (e) {
        console.error("Görev durumu sorgulama hatası:", e);
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [execId]);

  const handleCreateShorts = async () => {
    if (!activeChannelId || !selectedVideo) return;
    
    setGenerating(true);
    setExecStatus("pending");
    setExecMessage("Sıraya alınıyor...");
    setExecId(null);

    try {
      const res = await fetch(`/api/channels/${activeChannelId}/create-shorts-from-folder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder: selectedVideo, count: count })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setExecId(data.exec_id);
          setExecStatus("pending");
          setExecMessage("İşlem sıraya alındı, arka planda başlatılıyor...");
          if (onStartShorts) {
            onStartShorts(activeChannelId, data.exec_id);
          }
        } else {
          alert("Hata: " + (data.message || "Bilinmeyen bir hata oluştu"));
          setGenerating(false);
        }
      } else {
        const errData = await res.json().catch(() => ({ detail: "HTTP Hatası" }));
        alert("Hata: " + (errData.detail || "Sunucu isteği işleyemedi"));
        setGenerating(false);
      }
    } catch (e) {
      console.error("Shorts oluşturulurken hata:", e);
      alert("Hata: " + e.message);
      setGenerating(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 800 }}>
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Uzun Videodan Shorts Türet</h2>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 5 }}>
          Yuklenecek klasöründe yer alan üretilmiş uzun videolardan yapay zeka ile 3 veya 4 adet Shorts videosu kırpıp oluşturun.
        </p>
      </div>

      <div className="card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Kanal Seçimi */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, maxWidth: 400 }}>
          <label style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-muted)" }}>1. Hedef Kanalı Seçin</label>
          <select
            value={activeChannelId}
            onChange={e => setActiveChannelId(e.target.value)}
            className="form-input"
            style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)", cursor: "pointer" }}
            disabled={generating}
          >
            <option value="">Kanal Seçin...</option>
            {channels.map(ch => (
              <option key={ch.channel_id} value={ch.channel_id}>
                {ch.name} ({ch.channel_id})
              </option>
            ))}
          </select>
        </div>

        {/* Video Seçimi */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-muted)" }}>2. Kaynak Uzun Video</label>
          {loadingVideos ? (
            <div style={{ color: "var(--text-muted)", fontSize: 13, padding: "8px 0" }}>🔄 Videolar yükleniyor...</div>
          ) : videos.length === 0 ? (
            <div style={{
              color: "#ef4444", fontSize: 13, padding: "12px 14px",
              background: "rgba(239, 68, 68, 0.06)", borderRadius: 8,
              border: "1px solid rgba(239, 68, 68, 0.15)", marginTop: 4
            }}>
              ⚠️ Bu kanalın "yuklenecek" klasöründe üretilmiş uzun video bulunamadı. Lütfen önce uzun video üretin.
            </div>
          ) : (
            <select
              value={selectedVideo}
              onChange={e => setSelectedVideo(e.target.value)}
              className="form-input"
              style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)", cursor: "pointer" }}
              disabled={generating}
            >
              <option value="">Uzun Video Seçin...</option>
              {videos.map(v => {
                const folderName = v.folder.split('/').pop();
                return (
                  <option key={v.folder} value={v.folder}>
                    {folderName} {v.title ? `(${v.title})` : ""}
                  </option>
                );
              })}
            </select>
          )}
        </div>

        {/* Shorts Adedi Seçimi */}
        {selectedVideo && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-muted)" }}>
                3. Üretilecek Shorts Adedi
              </label>
              <span style={{
                fontSize: 12,
                color: "var(--accent-primary)",
                fontWeight: 700,
                background: "rgba(124, 110, 242, 0.1)",
                padding: "3px 10px",
                borderRadius: 12
              }}>
                🎯 {count} Adet Shorts Türetilecek
              </span>
            </div>

            {/* Hızlı Seçim Butonları */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {[1, 2, 3, 4, 5, 6, 8, 10].map(val => (
                <button
                  key={val}
                  type="button"
                  onClick={() => !generating && setCount(val)}
                  style={{
                    padding: "8px 16px",
                    borderRadius: "8px",
                    fontSize: 13,
                    fontWeight: 600,
                    border: count === val ? "2px solid var(--accent-primary)" : "1px solid var(--border-subtle)",
                    background: count === val ? "rgba(124, 110, 242, 0.15)" : "var(--bg-secondary)",
                    color: count === val ? "var(--accent-primary)" : "var(--text-primary)",
                    cursor: generating ? "not-allowed" : "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  📱 {val} Shorts
                </button>
              ))}
            </div>

            {/* Özel Adet Girişi */}
            <div style={{
              display: "flex", alignItems: "center", gap: 12, marginTop: 4,
              padding: "10px 14px", background: "var(--bg-secondary)", borderRadius: 8,
              border: "1px solid var(--border-subtle)"
            }}>
              <span style={{ fontSize: 12.5, color: "var(--text-secondary)", fontWeight: 500 }}>
                Veya istediğiniz adedi doğrudan yazın:
              </span>
              <input
                type="number"
                min="1"
                max="20"
                value={count}
                disabled={generating}
                onChange={e => setCount(Math.max(1, Math.min(20, parseInt(e.target.value) || 1)))}
                className="form-input"
                style={{ width: 80, textAlign: "center", padding: "6px 8px", fontWeight: 700, fontSize: 14 }}
              />
              <span style={{ fontSize: 11.5, color: "var(--text-muted)" }}>
                (Seçilen uzun müzik/anlatım klibinden {count} farklı 30-50 saniyelik 9:16 dikey Shorts oluşturulur)
              </span>
            </div>
          </div>
        )}

        {/* Aksiyon Butonu */}
        {selectedVideo && (
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 16 }}>
            <button
              className="btn btn-primary"
              style={{ alignSelf: "flex-start", padding: "12px 24px", fontSize: 13.5, fontWeight: 600, cursor: "pointer" }}
              onClick={handleCreateShorts}
              disabled={!activeChannelId || !selectedVideo || generating}
            >
              {generating ? "⚡ Shorts Üretimi Sürüyor..." : "⚡ Shorts Üretimini Başlat"}
            </button>

            {/* Görev Durumu Göstergesi */}
            {execStatus && (
              <div style={{
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid var(--border-subtle)",
                borderRadius: 12,
                padding: "16px 20px",
                display: "flex",
                flexDirection: "column",
                gap: 12,
                marginTop: 10
              }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>Arka Plan Görev Durumu</span>
                  <span className={`status-badge ${
                    execStatus === "success" ? "online" : execStatus === "failed" ? "offline" : "warning"
                  }`}>
                    {execStatus === "success" ? "✓ Tamamlandı" : execStatus === "failed" ? "❌ Hata" : "⏳ Üretiliyor"}
                  </span>
                </div>
                {execId && (
                  <div style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text-muted)" }}>
                    Giriş ID: {execId}
                  </div>
                )}
                <div style={{
                  fontSize: 13,
                  color: "var(--text-primary)",
                  background: "var(--bg-primary)",
                  padding: "12px 16px",
                  borderRadius: 8,
                  border: "1px solid var(--border-subtle)",
                  fontFamily: "monospace",
                  lineHeight: 1.5
                }}>
                  {execMessage || "Sıradaki işlemler hesaplanıyor..."}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   SERVER RENDER PAGE (BULUT VİDEO İŞLEME VE İNDİRME MERKEZİ)
   ══════════════════════════════════════════════════════════════════ */

function ServerRenderPage({ channels, onNavigateUpload }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [serverOnline, setServerOnline] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const [downloadSuccess, setDownloadSuccess] = useState(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [patchJob, setPatchJob] = useState(null);

  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch("/api/server-render/jobs");
      if (res.ok) {
        const d = await res.json();
        setJobs(d.jobs || []);
        setServerOnline(!!d.server_online);
      } else {
        setServerOnline(false);
      }
    } catch (e) {
      setServerOnline(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const handleDownload = async (job) => {
    setDownloadingId(job.job_id);
    setDownloadSuccess(null);
    try {
      const res = await fetch(`/api/server-render/jobs/${job.job_id}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel_id: job.channel_id })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setDownloadSuccess({
          job_id: job.job_id,
          channel_id: job.channel_id,
          message: data.message
        });
        await fetchJobs();
      } else {
        alert("İndirme hatası: " + (data.detail || data.message || "Bilinmeyen hata"));
      }
    } catch (err) {
      alert("Bağlantı hatası: " + err.message);
    } finally {
      setDownloadingId(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    try {
      const res = await fetch("/api/server-render/sync-all", { method: "POST" });
      const data = await res.json();
      if (res.ok && data.success) {
        setDownloadSuccess({ message: data.message });
        await fetchJobs();
      } else {
        alert("Toplu indirme hatası: " + (data.detail || data.message || "Bilinmeyen hata"));
      }
    } catch (err) {
      alert("Bağlantı hatası: " + err.message);
    } finally {
      setSyncingAll(false);
    }
  };

  const handleDelete = async (jobId) => {
    if (!window.confirm("Bu render görevini ve sunucudaki geçici dosyaları silmek istediğinizden emin misiniz?")) return;
    try {
      await fetch(`/api/server-render/jobs/${jobId}`, { method: "DELETE" });
      fetchJobs();
    } catch (e) {
      alert("Silinemedi: " + e.message);
    }
  };

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: 40 }}>
      {/* Sunucu Durum Kartı */}
      <div className="card" style={{ marginBottom: 20, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 12,
            background: serverOnline ? "rgba(16, 185, 129, 0.15)" : "rgba(244, 63, 94, 0.15)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: serverOnline ? "#10b981" : "#f43f5e"
          }}>
            <Server size={22} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Oracle Cloud Render Sunucusu</h2>
              <span style={{
                fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 12,
                background: serverOnline ? "rgba(16, 185, 129, 0.2)" : "rgba(244, 63, 94, 0.2)",
                color: serverOnline ? "#34d399" : "#fb7185",
                display: "inline-flex", alignItems: "center", gap: 5
              }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: serverOnline ? "#10b981" : "#f43f5e" }} />
                {serverOnline ? "Bağlı & Aktif (132.226.187.103)" : "Bağlantı Kesildi"}
              </span>
            </div>
            <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--text-muted)" }}>
              Gemini eklentisinden 'Oracle Cloud Sunucusu' seçildiğinde videolar bu sunucuda arka planda sırayla derlenir.
            </p>
          </div>
        </div>

        <button className="btn btn-ghost btn-sm" onClick={fetchJobs} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <RefreshCw size={13} className={loading ? "spin" : ""} /> Yenile
        </button>
      </div>

      {downloadSuccess && (
        <div style={{
          background: "rgba(16, 185, 129, 0.12)", border: "1px solid rgba(16, 185, 129, 0.3)",
          borderRadius: 12, padding: "14px 18px", marginBottom: 20,
          display: "flex", alignItems: "center", justifyContent: "space-between"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, color: "#34d399", fontSize: 13, fontWeight: 500 }}>
            <CheckCircle2 size={18} />
            <span>{downloadSuccess.message}</span>
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => onNavigateUpload && onNavigateUpload()} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
            <Upload size={13} /> YouTube Yükleme Merkezine Git
          </button>
        </div>
      )}

      {/* Kuyruktaki ve Üretilen Videolar */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <Film size={16} style={{ color: "var(--accent-primary)" }} />
            Sunucudaki Video Görevleri ({jobs.length})
          </h3>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {jobs.some(j => j.status === "completed") && (
              <button
                className="btn btn-primary btn-sm"
                disabled={syncingAll}
                onClick={handleSyncAll}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 600 }}
              >
                {syncingAll ? <Loader2 size={13} className="spin" /> : <Download size={13} />}
                {syncingAll ? "İndiriliyor..." : "Tümünü İndir ve Sunucudan Sil"}
              </button>
            )}
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              Her 4 sn güncellenir
            </span>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
            <Server size={36} style={{ opacity: 0.3, marginBottom: 10 }} />
            <div style={{ fontSize: 14, fontWeight: 500 }}>Şu anda sunucuda bekleyen veya üretilen video yok.</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>
              Gemini eklentisinde <strong>"Sunucu ile Üret"</strong> seçeneğini işaretleyerek videoları doğrudan bulut sunucusuna gönderebilirsiniz.
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {jobs.map((job) => {
              const isCompleted = job.status === "completed";
              const isRendering = job.status === "rendering";
              const isQueued = job.status === "queued";
              const isFailed = job.status === "failed";
              const isDownloading = downloadingId === job.job_id;

              return (
                <div
                  key={job.job_id}
                  style={{
                    background: "rgba(255, 255, 255, 0.02)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: 12,
                    padding: 16,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 16
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 14, minWidth: 0, flex: 1 }}>
                    {/* Status Icon */}
                    <div style={{
                      width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                      background: isCompleted ? "rgba(16, 185, 129, 0.15)" : isRendering ? "rgba(56, 189, 248, 0.15)" : isFailed ? "rgba(244, 63, 94, 0.15)" : "rgba(245, 158, 11, 0.15)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      color: isCompleted ? "#10b981" : isRendering ? "#38bdf8" : isFailed ? "#f43f5e" : "#f59e0b"
                    }}>
                      {isCompleted ? <CheckCircle2 size={20} /> :
                       isRendering ? <Loader2 size={20} className="spin" /> :
                       isFailed ? <AlertCircle size={20} /> :
                       <Clock size={20} />}
                    </div>

                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <span style={{
                          fontSize: 11, fontWeight: 700, padding: "1px 7px", borderRadius: 4,
                          background: "rgba(99, 102, 241, 0.2)", color: "#a5b4fc"
                        }}>
                          {job.channel_id}
                        </span>
                        <h4 style={{ fontSize: 14, fontWeight: 600, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {job.title}
                        </h4>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 11.5, color: "var(--text-muted)" }}>
                        <span>Durum: <strong style={{
                          color: isCompleted ? "#34d399" : isRendering ? "#38bdf8" : isFailed ? "#fb7185" : "#fbbf24"
                        }}>
                          {isCompleted ? "Tamamlandı (İndirmeye Hazır)" : isRendering ? "Render Ediliyor..." : isFailed ? "Hata" : "Kuyrukta"}
                        </strong></span>
                        {isCompleted ? (
                          job.duration ? (
                            <span>
                              Süre: {job.duration >= 60 ? `${Math.floor(job.duration / 60)}dk ${Math.round(job.duration % 60)}sn` : `${Math.round(job.duration)}sn`}
                            </span>
                          ) : null
                        ) : (
                          <span>Süre: {isRendering ? "Hesaplanıyor..." : "Kuyrukta"}</span>
                        )}
                        {job.file_size_mb && <span>Boyut: {job.file_size_mb} MB</span>}
                        {job.created_at && <span>Oluşturulma: {new Date(job.created_at).toLocaleTimeString()}</span>}
                      </div>

                      {job.progress_msg && (
                        <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                          {job.progress_msg}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                    {isCompleted && (
                      <>
                        <button
                          className="btn btn-ghost btn-sm"
                          onClick={() => setPatchJob({
                            title: job.title,
                            folder: `${job.channel_id}/yuklenecek`,
                            video_path: job.file_path,
                            job_id: job.job_id
                          })}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 5,
                            color: "#38bdf8",
                            background: "rgba(56, 189, 248, 0.08)",
                            border: "1px solid rgba(56, 189, 248, 0.25)",
                            fontSize: 11
                          }}
                          title="Bu videodaki hatalı sahneleri AI ile yamala"
                        >
                          <Scissors size={13} /> Sahne Düzelt
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          disabled={isDownloading}
                          onClick={() => handleDownload(job)}
                          style={{ display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 600 }}
                        >
                          {isDownloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
                          {isDownloading ? "İndiriliyor..." : "İndir ve Sunucudan Sil"}
                        </button>
                      </>
                    )}

                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleDelete(job.job_id)}
                      title="Sunucudaki bu görevi sil"
                      style={{ color: "var(--text-muted)", padding: "6px 8px" }}
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

      {patchJob && (
        <VideoScenePatcherModal
          isOpen={!!patchJob}
          video={patchJob}
          onClose={() => setPatchJob(null)}
          onPatched={fetchJobs}
        />
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   YOUTUBE UPLOAD PAGE (API YÜKLEME VE AKILLI ZAMANLAMA MERKEZİ)
   ══════════════════════════════════════════════════════════════════ */

function YouTubeUploadPage({ selectedChannelId, channels, onSelectChannel }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploadingRowId, setUploadingRowId] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [scheduleOverrides, setScheduleOverrides] = useState({});
  const [customTitles, setCustomTitles] = useState({});
  const [previewVideoUrl, setPreviewVideoUrl] = useState(null);

  // Eğer hiçbir kanal seçili değilse ve bağlı kanal varsa (örn: yazanyazana), otomatik seç
  useEffect(() => {
    if (!selectedChannelId && channels && channels.length > 0) {
      const conn = channels.find(c => c.channel_id === "yazanyazana");
      if (conn) {
        onSelectChannel(conn.channel_id);
      }
    }
  }, [selectedChannelId, channels, onSelectChannel]);

  const fetchUploadInfo = useCallback(async () => {
    if (!selectedChannelId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/channels/${selectedChannelId}/youtube-upload-info`);
      if (!res.ok) {
        throw new Error(`Bilgiler alınamadı (${res.status})`);
      }
      const json = await res.json();
      setData(json);

      // Sıradaki varsayılan tarih ve başlıkları ayarla
      const initialOverrides = {};
      const initialTitles = {};
      (json.ready_videos || []).forEach(v => {
        initialOverrides[v.row_id] = {
          date: v.suggested_date,
          time: v.suggested_time,
        };
        initialTitles[v.row_id] = v.title;
      });
      setScheduleOverrides(initialOverrides);
      setCustomTitles(initialTitles);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedChannelId]);

  useEffect(() => {
    fetchUploadInfo();
  }, [fetchUploadInfo]);

  const handleDateChange = (rowId, date) => {
    setScheduleOverrides(prev => ({
      ...prev,
      [rowId]: { ...(prev[rowId] || {}), date },
    }));
  };

  const handleTimeChange = (rowId, time) => {
    setScheduleOverrides(prev => ({
      ...prev,
      [rowId]: { ...(prev[rowId] || {}), time },
    }));
  };

  const handleTitleChange = (rowId, title) => {
    setCustomTitles(prev => ({
      ...prev,
      [rowId]: title,
    }));
  };

  const handleExecuteUpload = async (v) => {
    const override = scheduleOverrides[v.row_id] || {};
    const targetDate = override.date || v.suggested_date;
    const targetTime = override.time || v.suggested_time;
    const targetTitle = customTitles[v.row_id] || v.title;

    const confirmMsg = `"${targetTitle}" videosunu YouTube'a doğrudan yükleyip ${targetDate} saat ${targetTime} için planlamak istiyor musunuz?\n\n(Video gizli olarak yüklenecek ve belirtilen tarihte otomatik herkese açık yayına geçecektir.)`;
    if (!window.confirm(confirmMsg)) {
      return;
    }

    setUploadingRowId(v.row_id);
    setUploadSuccess(null);

    try {
      const res = await fetch(`/api/channels/${selectedChannelId}/youtube-upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          row_id: v.row_id,
          scheduled_date: targetDate,
          scheduled_time: targetTime,
          title: targetTitle,
          description: v.description,
          tags: v.tags,
        }),
      });

      const resData = await res.json();
      if (res.ok && resData.success) {
        setUploadSuccess(resData);
        await fetchUploadInfo();
      } else {
        alert("Yükleme Hatası: " + (resData.detail || resData.error || "Bilinmeyen bir hata oluştu"));
      }
    } catch (err) {
      alert("Hata: " + err.message);
    } finally {
      setUploadingRowId(null);
    }
  };

  // 1. Kanal Seçilmemiş Durumu
  if (!selectedChannelId) {
    return (
      <div style={{ maxWidth: 720, margin: "40px auto", textAlign: "center" }}>
        <div className="card" style={{ padding: 40, border: "1px dashed var(--border-subtle)", borderRadius: 16 }}>
          <div style={{ fontSize: 44, marginBottom: 16 }}>📺</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, color: "var(--text-primary)" }}>
            Lütfen Bir Kanal Seçin
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 24, lineHeight: 1.6 }}>
            YouTube Yükleme Merkezini kullanabilmek için API'ye bağlı bir kanal seçmelisiniz.
          </p>
          <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
            {channels.map(ch => (
              <button
                key={ch.channel_id}
                className="btn btn-ghost"
                onClick={() => onSelectChannel(ch.channel_id)}
                style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
              >
                <span>{ch.name}</span>
                {ch.channel_id === "yazanyazana" && (
                  <span style={{ fontSize: 10, background: "rgba(34,197,94,0.15)", color: "#4ade80", padding: "1px 6px", borderRadius: 4 }}>
                    API Bağlı
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // 2. Yükleniyor Durumu
  if (loading) {
    return (
      <div style={{ padding: 60, textAlign: "center", color: "var(--text-muted)" }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>⏳</div>
        <div>Kanal YouTube API durumu ve videolar kontrol ediliyor...</div>
      </div>
    );
  }

  // 3. API Yetkisi Yok / Bağlı Değil Koruması
  if (!data?.api_connected) {
    return (
      <div style={{ maxWidth: 780, margin: "40px auto" }}>
        <div className="card" style={{
          padding: 36,
          background: "linear-gradient(180deg, rgba(239,68,68,0.06), rgba(17,24,39,0.5))",
          border: "1px solid rgba(239,68,68,0.25)",
          borderRadius: 14,
        }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: 20 }}>
            <div style={{
              width: 48,
              height: 48,
              borderRadius: 10,
              background: "rgba(239,68,68,0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 24,
              flexShrink: 0
            }}>
              🔒
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                <h2 style={{ fontSize: 19, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
                  YouTube API Yetkisi Gerekli
                </h2>
                <span style={{ fontSize: 11, background: "rgba(239,68,68,0.2)", color: "#f87171", padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
                  Erişim Kısıtlı
                </span>
              </div>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
                <strong>{data?.channel_name || selectedChannelId}</strong> kanalı için Google OAuth YouTube yetki anahtarı bulunamadı. Bu yükleme sayfasına yalnızca YouTube API'ye bağlı kanallar erişebilir.
              </p>
            </div>
          </div>

          {data?.connected_channels && data.connected_channels.length > 0 && (
            <div style={{
              background: "rgba(34,197,94,0.08)",
              border: "1px solid rgba(34,197,94,0.25)",
              borderRadius: 10,
              padding: "16px 20px",
              marginBottom: 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 12
            }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#4ade80", marginBottom: 3 }}>
                  ⚡ API'ye Bağlı Aktif Kanal Bulundu
                </div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  <strong>{data.connected_channels[0].name}</strong> kanalı resmi YouTube API ile yetkilendirilmiş durumda.
                </div>
              </div>
              <button
                className="btn btn-primary"
                onClick={() => onSelectChannel(data.connected_channels[0].channel_id)}
                style={{
                  background: "linear-gradient(135deg, #22c55e, #16a34a)",
                  border: "none",
                  padding: "8px 16px",
                  fontSize: 12,
                  fontWeight: 600,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6
                }}
              >
                <span>🚀 {data.connected_channels[0].name} Kanalına Geç</span>
              </button>
            </div>
          )}

          <div style={{ background: "var(--bg-primary)", borderRadius: 10, padding: 18, border: "1px solid var(--border-subtle)" }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)", marginBottom: 8 }}>
              {data?.channel_name || selectedChannelId} kanalını YouTube API'ye nasıl bağlarsınız?
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12 }}>
              Terminalde aşağıdaki komutu çalıştırarak kanalınız için Google izin ekranını onaylayın:
            </div>
            <div style={{
              background: "rgba(0,0,0,0.4)",
              borderRadius: 6,
              padding: "10px 14px",
              fontFamily: "monospace",
              fontSize: 12,
              color: "#a5b4fc",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between"
            }}>
              <code>.venv/bin/python src/auth_channel.py {selectedChannelId}</code>
              <button
                className="btn btn-ghost"
                style={{ padding: "2px 8px", fontSize: 11 }}
                onClick={() => {
                  navigator.clipboard.writeText(`.venv/bin/python src/auth_channel.py ${selectedChannelId}`);
                  alert("Komut kopyalandı!");
                }}
              >
                Kopyala
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 4. API Yetkisi Aktif -> YouTube Yükleme Merkezi (Full Command Center)
  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: 60 }}>
      {/* Üst Başlık & Kanal Rozeti */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
              {data.channel_name}
            </h2>
            <span style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              fontSize: 11,
              fontWeight: 600,
              background: "rgba(239, 68, 68, 0.15)",
              color: "#f87171",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              padding: "2px 8px",
              borderRadius: 6
            }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#ef4444" }}></span>
              YouTube Data API Bağlı
            </span>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
            Zaman Dilimi: <strong>{data.timezone}</strong> · Varsayılan Prime-Time Slot: <strong>{data.next_slot?.time || "19:00"}</strong>
          </div>
        </div>
        <button
          className="btn btn-ghost btn-sm"
          onClick={fetchUploadInfo}
          style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
        >
          <RefreshCw size={13} />
          <span>Yenile</span>
        </button>
      </div>

      {/* Yükleme Başarısı Bildirim Kartı */}
      {uploadSuccess && (
        <div className="card" style={{
          padding: "16px 20px",
          marginBottom: 24,
          background: "linear-gradient(135deg, rgba(34,197,94,0.12), rgba(16,185,129,0.06))",
          border: "1px solid rgba(34,197,94,0.3)",
          borderRadius: 12,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <CheckCircle2 size={24} style={{ color: "#22c55e", flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#4ade80", marginBottom: 2 }}>
                🎉 Video Başarıyla YouTube'a Yüklendi ve Planlandı!
              </div>
              <div style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>
                <strong>{uploadSuccess.title}</strong> · Planlanan Yayın: <strong>{uploadSuccess.scheduled_for}</strong>
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {uploadSuccess.url && (
              <a
                href={uploadSuccess.url}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary btn-sm"
                style={{
                  background: "#22c55e",
                  border: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5
                }}
              >
                <span>YouTube'da Gör</span>
                <ExternalLink size={12} />
              </a>
            )}
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setUploadSuccess(null)}
              style={{ color: "var(--text-muted)" }}
            >
              Kapat
            </button>
          </div>
        </div>
      )}

      {/* 3'lü Metrik Çubuğu */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
        gap: 14,
        marginBottom: 28
      }}>
        <div className="card" style={{ padding: 18, background: "var(--bg-secondary)", borderRadius: 12 }}>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
            <span>📦</span> Yüklenmeyi Bekleyen
          </div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
            {data.ready_videos?.length || 0} <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-muted)" }}>Hazır Video</span>
          </div>
        </div>

        <div className="card" style={{ padding: 18, background: "var(--bg-secondary)", borderRadius: 12 }}>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
            <span>📅</span> Son Planlanan / Yayımlanan
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: data.latest_uploaded_datetime ? "var(--accent-primary)" : "var(--text-muted)" }}>
            {data.latest_uploaded_display || "Henüz video yok"}
          </div>
        </div>

        <div className="card" style={{
          padding: 18,
          background: "linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.05))",
          border: "1px solid rgba(99,102,241,0.25)",
          borderRadius: 12
        }}>
          <div style={{ fontSize: 12, color: "#a5b4fc", marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
            <Clock size={13} /> Sıradaki Planlama Yuvası
          </div>
          <div style={{ fontSize: 17, fontWeight: 800, color: "#fff" }}>
            {data.next_slot?.date} <span style={{ color: "#a5b4fc", fontSize: 14 }}>saat {data.next_slot?.time}</span>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
            Kural: En son yüklenen videonun ertesi günü {data.next_slot?.time || "19:00"}
          </div>
        </div>
      </div>

      {/* Ana Bölüm: Yüklenmeye Hazır Videolar */}
      <div style={{ marginBottom: 36 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <h3 style={{ fontSize: 17, fontWeight: 700, margin: 0, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
            <span>🎬</span> Yüklenmeye Hazır Videolar ({data.ready_videos?.length || 0})
          </h3>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Videolar sırayla ertesi günlere otomatik olarak paylaştırılmıştır
          </span>
        </div>

        {(!data.ready_videos || data.ready_videos.length === 0) ? (
          <div className="card" style={{ padding: 48, textAlign: "center", borderRadius: 14 }}>
            <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.4 }}>🎉</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
              Yüklenmeye Bekleyen Video Yok
            </div>
            <div style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 460, margin: "0 auto" }}>
              Tüm üretilen videolar YouTube'a yüklendi veya planlandı. Dashboard sayfasına dönerek içerik planınızdan yeni videolar üretebilirsiniz.
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {data.ready_videos.map((v, idx) => {
              const override = scheduleOverrides[v.row_id] || {};
              const chosenDate = override.date || v.suggested_date;
              const chosenTime = override.time || v.suggested_time;
              const chosenTitle = customTitles[v.row_id] || v.title;
              const isUploadingThis = uploadingRowId === v.row_id;

              return (
                <div key={v.row_id || v.folder} className="card" style={{
                  padding: 18,
                  borderRadius: 14,
                  display: "flex",
                  gap: 18,
                  alignItems: "stretch",
                  border: isUploadingThis ? "1px solid #ef4444" : "1px solid var(--border-subtle)",
                  transition: "border-color 0.2s ease"
                }}>
                  {/* Thumbnail & Video Preview */}
                  <div style={{ position: "relative", width: 110, flexShrink: 0, borderRadius: 8, overflow: "hidden", background: "#000" }}>
                    {v.thumbnail_url ? (
                      <img
                        src={v.thumbnail_url}
                        alt={v.title}
                        style={{ width: "100%", height: 160, objectFit: "cover", display: "block" }}
                      />
                    ) : (
                      <div style={{ width: "100%", height: 160, display: "flex", alignItems: "center", justifyContent: "center", color: "#666" }}>
                        <Film size={28} />
                      </div>
                    )}
                    {v.video_url && (
                      <button
                        onClick={() => setPreviewVideoUrl(v.video_url)}
                        title="Videoyu Oynat"
                        style={{
                          position: "absolute",
                          inset: 0,
                          background: "rgba(0,0,0,0.35)",
                          border: "none",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "#fff",
                          transition: "background 0.15s"
                        }}
                      >
                        <div style={{
                          width: 36,
                          height: 36,
                          borderRadius: "50%",
                          background: "rgba(255,255,255,0.9)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "#000"
                        }}>
                          <Play size={16} style={{ marginLeft: 2 }} />
                        </div>
                      </button>
                    )}
                    {v.duration_sec > 0 && (
                      <span style={{
                        position: "absolute",
                        bottom: 6,
                        right: 6,
                        background: "rgba(0,0,0,0.75)",
                        color: "#fff",
                        fontSize: 10,
                        padding: "1px 5px",
                        borderRadius: 3,
                        fontWeight: 600
                      }}>
                        {v.duration_sec}s
                      </span>
                    )}
                  </div>

                  {/* Video Bilgileri & Akıllı Planlama Yuvası */}
                  <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                    <div>
                      {/* Üst Rozetler */}
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
                        <span style={{
                          fontSize: 11,
                          fontWeight: 700,
                          background: "var(--bg-primary)",
                          color: "var(--accent-primary)",
                          padding: "2px 7px",
                          borderRadius: 4,
                          border: "1px solid var(--border-subtle)"
                        }}>
                          #{v.row_id || idx + 1}
                        </span>
                        <span style={{ fontSize: 11, color: "var(--text-muted)", background: "var(--bg-primary)", padding: "2px 7px", borderRadius: 4 }}>
                          {v.file_size_mb} MB
                        </span>
                        <span style={{ fontSize: 11, background: "rgba(99,102,241,0.15)", color: "#a5b4fc", padding: "2px 7px", borderRadius: 4, fontWeight: 600 }}>
                          📱 Shorts Formatı
                        </span>
                      </div>

                      {/* Başlık Input */}
                      <div style={{ marginBottom: 12 }}>
                        <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                          YouTube Video Başlığı:
                        </label>
                        <input
                          type="text"
                          value={chosenTitle}
                          onChange={(e) => handleTitleChange(v.row_id, e.target.value)}
                          style={{
                            width: "100%",
                            padding: "6px 10px",
                            fontSize: 13,
                            fontWeight: 600,
                            borderRadius: 6,
                            background: "var(--bg-primary)",
                            border: "1px solid var(--border-subtle)",
                            color: "var(--text-primary)"
                          }}
                        />
                      </div>

                      {/* Akıllı Planlama Kutusu */}
                      <div style={{
                        background: "linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.04))",
                        border: "1px solid rgba(99, 102, 241, 0.25)",
                        borderRadius: 10,
                        padding: "10px 14px",
                        marginBottom: 10
                      }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6, flexWrap: "wrap", gap: 6 }}>
                          <span style={{ fontSize: 12, fontWeight: 700, color: "#c7d2fe", display: "flex", alignItems: "center", gap: 5 }}>
                            <Calendar size={13} />
                            Planlanan Yayın Zamanı:
                          </span>
                          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                            Kural: Son videodan sonraki gün saat {chosenTime}
                          </span>
                        </div>

                        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                          <div>
                            <input
                              type="date"
                              value={chosenDate}
                              onChange={(e) => handleDateChange(v.row_id, e.target.value)}
                              style={{
                                padding: "5px 10px",
                                fontSize: 12,
                                borderRadius: 6,
                                background: "var(--bg-primary)",
                                border: "1px solid var(--border-subtle)",
                                color: "var(--text-primary)",
                                colorScheme: "dark"
                              }}
                            />
                          </div>
                          <div>
                            <input
                              type="time"
                              value={chosenTime}
                              onChange={(e) => handleTimeChange(v.row_id, e.target.value)}
                              style={{
                                padding: "5px 10px",
                                fontSize: 12,
                                borderRadius: 6,
                                background: "var(--bg-primary)",
                                border: "1px solid var(--border-subtle)",
                                color: "var(--text-primary)",
                                colorScheme: "dark"
                              }}
                            />
                          </div>
                          <span style={{ fontSize: 11.5, color: "#a5b4fc" }}>
                            ({data.timezone})
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Alt Aksiyon Butonu */}
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", marginTop: 8 }}>
                      <button
                        className="btn btn-primary"
                        onClick={() => handleExecuteUpload(v)}
                        disabled={uploadingRowId !== null}
                        style={{
                          background: isUploadingThis ? "#475569" : "linear-gradient(135deg, #ef4444, #dc2626)",
                          border: "none",
                          padding: "8px 18px",
                          fontSize: 12.5,
                          fontWeight: 700,
                          borderRadius: 8,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          cursor: uploadingRowId !== null ? "not-allowed" : "pointer",
                          boxShadow: isUploadingThis ? "none" : "0 4px 12px rgba(239, 68, 68, 0.25)"
                        }}
                      >
                        {isUploadingThis ? (
                          <>
                            <Loader2 size={14} className="spin" />
                            <span>YouTube'a Yükleniyor...</span>
                          </>
                        ) : (
                          <>
                            <Upload size={14} />
                            <span>YouTube'a Yükle ve Planla</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Alt Bölüm: Kanalın Yüklenen & Planlanan Arşivi */}
      {data.uploaded_videos && data.uploaded_videos.length > 0 && (
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
            <span>✅</span> Kanalın Yüklenen & Planlanan Arşivi ({data.uploaded_videos.length})
          </h3>
          <div className="card" style={{ padding: 0, borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "rgba(0,0,0,0.2)", borderBottom: "1px solid var(--border-subtle)" }}>
                  <th style={{ padding: "10px 14px", textAlign: "left", color: "var(--text-muted)", fontWeight: 600 }}>Video Başlığı</th>
                  <th style={{ padding: "10px 14px", textAlign: "left", color: "var(--text-muted)", fontWeight: 600 }}>Planlanan Yayın</th>
                  <th style={{ padding: "10px 14px", textAlign: "center", color: "var(--text-muted)", fontWeight: 600 }}>Durum</th>
                  <th style={{ padding: "10px 14px", textAlign: "right", color: "var(--text-muted)", fontWeight: 600 }}>Bağlantı</th>
                </tr>
              </thead>
              <tbody>
                {data.uploaded_videos.map((uv, idx) => (
                  <tr key={idx} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <td style={{ padding: "10px 14px", color: "var(--text-primary)", fontWeight: 600 }}>
                      {uv.title}
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>
                      {uv.yayim_tarihi || "-"}
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "center" }}>
                      <span style={{ fontSize: 11, background: "rgba(34,197,94,0.15)", color: "#4ade80", padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
                        {uv.yayim_tarihi ? "Planlandı" : "Yüklendi"}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "right" }}>
                      {uv.video_url ? (
                        <a
                          href={uv.video_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: "#38bdf8", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 4 }}
                        >
                          <span>İzle</span>
                          <ExternalLink size={12} />
                        </a>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Video Önizleme Modalı */}
      {previewVideoUrl && (
        <Modal open={true} onClose={() => setPreviewVideoUrl(null)} title="Video Önizleme">
          <div style={{ textAlign: "center", padding: "10px 0" }}>
            <video
              src={previewVideoUrl}
              controls
              autoPlay
              style={{ maxHeight: "70vh", maxWidth: "100%", borderRadius: 8 }}
            />
          </div>
        </Modal>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   ROUTINE APPROVAL MODAL & ROUTINES PAGE
   ══════════════════════════════════════════════════════════════════ */

function RoutineApprovalModal({ pendingRoutines, onApprove, onSnooze, onDismiss }) {
  if (!pendingRoutines || pendingRoutines.length === 0) return null;
  const current = pendingRoutines[0];

  return (
    <div style={{
      position: "fixed",
      top: 20,
      right: 20,
      zIndex: 9999,
      maxWidth: 450,
      width: "calc(100vw - 40px)",
      background: "linear-gradient(135deg, rgba(30, 27, 75, 0.96) 0%, rgba(15, 23, 42, 0.98) 100%)",
      border: "1px solid rgba(168, 85, 247, 0.5)",
      borderRadius: "var(--radius-lg, 12px)",
      padding: "18px 20px",
      boxShadow: "0 10px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(168, 85, 247, 0.3)",
      backdropFilter: "blur(12px)",
      animation: "slideInRight 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div style={{
          width: 38,
          height: 38,
          borderRadius: "50%",
          background: "rgba(168, 85, 247, 0.2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#d8b4fe",
          flexShrink: 0
        }}>
          <Bell size={20} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#f3e8ff", letterSpacing: "0.02em" }}>
              🔔 ZAMANLANMIŞ RUTİN ONAYI
            </span>
            <span style={{ fontSize: 11, fontFamily: "monospace", color: "#c084fc", background: "rgba(168,85,247,0.15)", padding: "1px 6px", borderRadius: 4 }}>
              {current.schedule_time}
            </span>
          </div>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: "#ffffff", marginBottom: 4 }}>
            {current.name}
          </div>
          <p style={{ fontSize: 11.5, color: "var(--text-muted)", margin: "0 0 10px", lineHeight: 1.4 }}>
            Planlanan saat geldi. <strong>{current.channel_ids?.length || 0} kanal</strong> için içerik planı taranacak ve {current.rest_minutes || 0} dk CPU dinlenme aralığıyla videolar sırayla üretilecektir.
          </p>

          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button
              className="btn btn-primary"
              style={{
                flex: 2,
                padding: "8px 12px",
                fontSize: 12,
                fontWeight: 600,
                background: "linear-gradient(135deg, #9333ea, #6366f1)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6
              }}
              onClick={() => onApprove(current.id, current.name)}
            >
              <Zap size={13} /> Onayla ve Başlat
            </button>
            <button
              className="btn btn-ghost"
              style={{
                flex: 1,
                padding: "8px 8px",
                fontSize: 11,
                border: "1px solid var(--border-subtle)"
              }}
              onClick={() => onSnooze(current.id)}
              title="15 dakika ertele"
            >
              ⏳ 15 Dk Ertele
            </button>
            <button
              className="btn btn-ghost"
              style={{
                padding: "8px 8px",
                fontSize: 11,
                color: "#f87171",
                border: "1px solid rgba(239, 68, 68, 0.2)"
              }}
              onClick={() => onDismiss(current.id)}
              title="Bugünlük iptal et"
            >
              ✕
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function RoutinesPage({ channels, onTriggerRoutine }) {
  const [routines, setRoutines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [routineFilter, setRoutineFilter] = useState("all");
  const [routineSearch, setRoutineSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingRoutine, setEditingRoutine] = useState(null);

  // Inspect modal
  const [inspectModalOpen, setInspectModalOpen] = useState(false);
  const [inspectLoading, setInspectLoading] = useState(false);
  const [inspectData, setInspectData] = useState(null);

  // Form state
  const [formName, setFormName] = useState("");
  const [formChannels, setFormChannels] = useState([]);
  const [formTime, setFormTime] = useState("10:00");
  const [formDays, setFormDays] = useState(["all"]);
  const [formRestMinutes, setFormRestMinutes] = useState(5);
  const [formRequireApproval, setFormRequireApproval] = useState(true);
  const [formAutoOpenGemini, setFormAutoOpenGemini] = useState(true);
  const [formActive, setFormActive] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchRoutines = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/routines");
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Rutinler yüklenemedi (HTTP ${res.status}).`);
      }
      const d = await res.json();
      setRoutines(Array.isArray(d.routines) ? d.routines : []);
      setLoadError("");
    } catch (e) {
      console.error("Rutin listesi yüklenemedi:", e);
      setLoadError(e.message || "Rutin listesi yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRoutines();
    const interval = setInterval(fetchRoutines, 15000);
    return () => clearInterval(interval);
  }, [fetchRoutines]);

  const openCreateModal = () => {
    setEditingRoutine(null);
    setFormName("Günlük Çoklu Kanal Rutini");
    setFormChannels(channels.slice(0, 3).map(c => c.channel_id));
    setFormTime("10:00");
    setFormDays(["all"]);
    setFormRestMinutes(5);
    setFormRequireApproval(true);
    setFormAutoOpenGemini(true);
    setFormActive(true);
    setShowModal(true);
  };

  const openEditModal = (r) => {
    setEditingRoutine(r);
    setFormName(r.name || "");
    setFormChannels(r.channel_ids || []);
    setFormTime(r.schedule_time || "10:00");
    setFormDays(r.days || ["all"]);
    setFormRestMinutes(r.rest_minutes !== undefined ? r.rest_minutes : 5);
    setFormRequireApproval(r.require_approval !== false);
    setFormAutoOpenGemini(r.auto_open_gemini !== false);
    setFormActive(r.active !== false);
    setShowModal(true);
  };

  const handleSaveRoutine = async () => {
    if (!formName.trim()) {
      alert("Lütfen rutin adı giriniz.");
      return;
    }
    if (formChannels.length === 0) {
      alert("Lütfen en az bir kanal seçiniz.");
      return;
    }

    setSaving(true);
    const payload = {
      name: formName.trim(),
      channel_ids: formChannels,
      schedule_time: formTime,
      days: formDays,
      rest_minutes: Number(formRestMinutes),
      require_approval: Boolean(formRequireApproval),
      auto_open_gemini: Boolean(formAutoOpenGemini),
      active: Boolean(formActive),
    };

    try {
      let res;
      if (editingRoutine) {
        res = await fetch(`/api/routines/${editingRoutine.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch("/api/routines", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      }

      if (res.ok) {
        setShowModal(false);
        fetchRoutines();
      } else {
        const err = await res.json();
        alert("Rutin kaydedilemedi: " + (err.detail || "Bilinmeyen hata"));
      }
    } catch (e) {
      alert("Hata: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRoutine = async (id, name) => {
    if (!window.confirm(`"${name}" rutinini silmek istediğinize emin misiniz?`)) return;
    try {
      const res = await fetch(`/api/routines/${id}`, { method: "DELETE" });
      if (res.ok) fetchRoutines();
    } catch (e) {
      alert("Hata: " + e.message);
    }
  };

  const handleToggleRoutine = async (id) => {
    try {
      const res = await fetch(`/api/routines/${id}/toggle`, { method: "POST" });
      if (res.ok) fetchRoutines();
    } catch (e) {
      alert("Hata: " + e.message);
    }
  };

  const handleInspectPlans = async (r) => {
    setInspectModalOpen(true);
    setInspectLoading(true);
    setInspectData(null);
    try {
      const res = await fetch(`/api/routines/${r.id}/inspect`);
      if (res.ok) {
        setInspectData(await res.json());
      }
    } catch (e) {
      console.error("Inspect error:", e);
    } finally {
      setInspectLoading(false);
    }
  };

  const handleOpenGemini = async (id) => {
    try {
      const res = await fetch(`/api/routines/${id}/open-gemini`, { method: "POST" });
      if (res.ok) {
        alert("Gemini web sayfası tarayıcınızda açıldı.");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const toggleChannelSelection = (cid) => {
    setFormChannels(prev =>
      prev.includes(cid) ? prev.filter(x => x !== cid) : [...prev, cid]
    );
  };

  const selectAllChannels = () => {
    setFormChannels(channels.map(c => c.channel_id));
  };

  const clearChannelSelection = () => {
    setFormChannels([]);
  };

  const toggleDaySelection = (day) => {
    setFormDays(current => {
      if (day === "all") return ["all"];
      const selected = current.includes("all") ? [] : current.filter(value => value !== day);
      if (current.includes("all") || !current.includes(day)) selected.push(day);
      return selected.length ? selected : ["all"];
    });
  };

  const activeRoutinesCount = routines.filter(r => r.active).length;
  const pendingApprovalsCount = routines.filter(r => r.status === "waiting_approval").length;
  const runningRoutinesCount = routines.filter(r => r.status === "running").length;
  const filteredRoutines = routines
    .filter(r => {
      if (routineFilter === "active" && !r.active) return false;
      if (routineFilter === "paused" && r.active) return false;
      if (routineFilter === "pending" && r.status !== "waiting_approval") return false;
      const query = routineSearch.trim().toLocaleLowerCase("tr-TR");
      if (!query) return true;
      const channelNames = (r.channel_ids || [])
        .map(cid => channels.find(c => c.channel_id === cid)?.name || cid)
        .join(" ");
      return `${r.name || ""} ${channelNames}`.toLocaleLowerCase("tr-TR").includes(query);
    })
    .sort((a, b) => {
      const priority = routine => routine.status === "waiting_approval" ? 0 : routine.status === "running" ? 1 : routine.active ? 2 : 3;
      return priority(a) - priority(b) || (a.schedule_time || "").localeCompare(b.schedule_time || "");
    });

  return (
    <div className="routine-page" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Top Banner / Controls */}
      <div className="card routine-hero" style={{
        padding: "20px 24px",
        background: "linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.05) 100%)",
        border: "1px solid rgba(99, 102, 241, 0.2)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 16
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span className="routine-hero-icon"><CalendarDays size={20} /></span>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              Üretim rutinleri
            </h2>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0, lineHeight: 1.5, maxWidth: 640 }}>
            Zamanlanmış çoklu kanal üretimlerini tek yerden yönetin; planları kontrol edin, rutinleri çalıştırın ve onayları takip edin.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={fetchRoutines} disabled={loading} title="Rutin listesini yenile">
            <RefreshCw size={14} className={loading ? "routine-spin" : ""} /> Yenile
          </button>
          <button
            className="btn btn-primary"
            onClick={openCreateModal}
            style={{
              padding: "10px 16px",
              fontSize: 12.5,
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: 6
            }}
          >
            <Plus size={15} /> Yeni rutin
          </button>
        </div>
      </div>

      <div className="routine-stat-grid">
        <div className="routine-stat-card">
          <span className="routine-stat-icon is-active"><CalendarDays size={17} /></span>
          <div><strong>{routines.length}</strong><span>Toplam rutin</span></div>
        </div>
        <div className="routine-stat-card">
          <span className="routine-stat-icon is-enabled"><CheckCircle2 size={17} /></span>
          <div><strong>{activeRoutinesCount}</strong><span>Aktif zamanlama</span></div>
        </div>
        <div className="routine-stat-card">
          <span className="routine-stat-icon is-running"><Activity size={17} /></span>
          <div><strong>{runningRoutinesCount}</strong><span>Şu an çalışıyor</span></div>
        </div>
        <div className="routine-stat-card">
          <span className="routine-stat-icon is-pending"><Bell size={17} /></span>
          <div><strong>{pendingApprovalsCount}</strong><span>Onay bekliyor</span></div>
        </div>
      </div>

      <div className="routine-toolbar">
        <label className="routine-search">
          <Search size={16} />
          <input
            type="search"
            value={routineSearch}
            onChange={event => setRoutineSearch(event.target.value)}
            placeholder="Rutin veya kanal ara..."
            aria-label="Rutin veya kanal ara"
          />
          {routineSearch && <button type="button" onClick={() => setRoutineSearch("")} aria-label="Aramayı temizle"><X size={14} /></button>}
        </label>
        <div className="routine-filters" role="group" aria-label="Rutin filtresi">
          {[
            ["all", "Tümü"],
            ["active", "Aktif"],
            ["pending", "Onay bekliyor"],
            ["paused", "Duraklatıldı"],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={`routine-filter ${routineFilter === value ? "active" : ""}`}
              onClick={() => setRoutineFilter(value)}
              aria-pressed={routineFilter === value}
            >
              {label}
              {value === "all" ? ` ${routines.length}` : value === "active" ? ` ${activeRoutinesCount}` : value === "pending" ? ` ${pendingApprovalsCount}` : ` ${routines.length - activeRoutinesCount}`}
            </button>
          ))}
        </div>
      </div>

      {loadError && (
        <div className="routine-load-error" role="alert">
          <AlertCircle size={17} />
          <span>{loadError}</span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={fetchRoutines}>Tekrar dene</button>
        </div>
      )}

      {/* Routine Cards Grid */}
      {loading && routines.length === 0 ? (
        <div className="routine-empty-state">
          <Loader2 className="animate-spin" size={24} style={{ margin: "0 auto 8px" }} />
          <div>Rutinler yükleniyor...</div>
        </div>
      ) : routines.length === 0 ? (
        <div className="card" style={{ padding: "48px 24px", textAlign: "center", border: "1px dashed var(--border-subtle)" }}>
          <div style={{
            width: 52, height: 52, borderRadius: "50%", background: "rgba(99,102,241,0.08)",
            display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px",
            color: "var(--text-muted)"
          }}>
            <Clock size={26} />
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
            Henüz Tanımlanmış Rutin Yok
          </div>
          <p style={{ fontSize: 12.5, color: "var(--text-muted)", margin: "0 auto 16px", maxWidth: 460 }}>
            Yeni bir zamanlama tanımlayın; çalışma saatini, kanallarını ve onay davranışını siz belirleyin.
          </p>
          <button className="btn btn-primary btn-sm" onClick={openCreateModal}>
            <Plus size={13} /> İlk Rutini Oluştur
          </button>
        </div>
      ) : filteredRoutines.length === 0 ? (
        <div className="routine-empty-state">
          <Search size={22} />
          <strong>Bu filtreye uygun rutin yok</strong>
          <span>Aramanızı değiştirin veya diğer rutin filtrelerini deneyin.</span>
          <button className="btn btn-ghost btn-sm" onClick={() => { setRoutineSearch(""); setRoutineFilter("all"); }}>Filtreleri temizle</button>
        </div>
      ) : (
        <div className="routine-grid">
          {filteredRoutines.map(r => {
            const isRunning = r.status === "running";
            const isWaiting = r.status === "waiting_approval";
            const targetChannels = (r.channel_ids || []).map(cid => channels.find(c => c.channel_id === cid)).filter(Boolean);

            return (
              <div
                key={r.id}
                className={`card routine-card ${isWaiting ? "is-waiting" : ""} ${isRunning ? "is-running" : ""} ${!r.active ? "is-paused" : ""}`}
                style={{
                  padding: "18px 20px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 14,
                  border: isWaiting
                    ? "1px solid rgba(234, 179, 8, 0.6)"
                    : isRunning
                    ? "1px solid rgba(168, 85, 247, 0.6)"
                    : r.active
                    ? "1px solid var(--border-subtle)"
                    : "1px solid rgba(255, 255, 255, 0.04)",
                  boxShadow: isWaiting
                    ? "0 0 15px rgba(234, 179, 8, 0.2)"
                    : isRunning
                    ? "0 0 15px rgba(168, 85, 247, 0.2)"
                    : "none",
                  transition: "all 0.2s ease"
                }}
              >
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 16 }}>⏰</span>
                      <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                        {r.name}
                      </h3>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace" }}>
                      {r.id}
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {isRunning ? (
                      <span className="routine-status is-running">
                        <Activity size={12} /> Çalışıyor
                      </span>
                    ) : isWaiting ? (
                      <span className="routine-status is-waiting">
                        <Bell size={12} /> Onay bekliyor
                      </span>
                    ) : r.active ? (
                      <span className="routine-status is-active">
                        Aktif
                      </span>
                    ) : (
                      <span className="routine-status is-paused">
                        Pasif
                      </span>
                    )}

                    <input
                      type="checkbox"
                      checked={Boolean(r.active)}
                      onChange={() => handleToggleRoutine(r.id)}
                      title={r.active ? "Pasifleştir" : "Aktifleştir"}
                      style={{ cursor: "pointer", width: 14, height: 14, accentColor: "var(--accent-primary)" }}
                    />
                  </div>
                </div>

                {/* Telemetry row */}
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "8px 12px",
                  fontSize: 11.5,
                  padding: "10px 12px",
                  background: "var(--bg-primary, rgba(0,0,0,0.2))",
                  borderRadius: "var(--radius-md, 8px)",
                  border: "1px solid var(--border-subtle, rgba(255,255,255,0.04))"
                }}>
                  <div>
                    <span style={{ color: "var(--text-muted)" }}>Çalışma saati </span>
                    <span style={{ fontWeight: 600, color: "#f3e8ff", fontFamily: "monospace" }}>
                      {r.schedule_time}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)" }}>CPU Dinlenme: </span>
                    <span style={{ fontWeight: 600, color: "#93c5fd" }}>
                      {r.rest_minutes} dk mola
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)" }}>Çalıştırma </span>
                    <span style={{ fontWeight: 500, color: r.require_approval ? "#fde047" : "#86efac" }}>
                      {r.require_approval ? "🔔 Bildirimli" : "⚡ Otomatik"}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)" }}>Gemini </span>
                    <span style={{ fontWeight: 500, color: r.auto_open_gemini ? "#c084fc" : "var(--text-muted)" }}>
                      {r.auto_open_gemini ? "✓ Otomatik Aç" : "Kapalı"}
                    </span>
                  </div>
                </div>

                <div className="routine-next-run">
                  <span className="routine-next-run-icon"><CalendarDays size={15} /></span>
                  <div><span>Sonraki çalışma</span><strong>{getNextRoutineRun(r)}</strong></div>
                </div>

                <div className="routine-days" aria-label="Çalışma günleri">
                  {(r.days || ["all"]).includes("all")
                    ? <span className="routine-day is-selected">Her gün</span>
                    : ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].map(day => (
                      <span key={day} className={`routine-day ${(r.days || []).includes(day) ? "is-selected" : ""}`}>
                        {WEEKDAY_LABELS[day]}
                      </span>
                    ))}
                </div>

                {/* Channels List */}
                <div>
                  <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 6 }}>
                    <Users size={13} /> Hedef kanallar ({targetChannels.length})
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {targetChannels.map(ch => {
                      const chLang = getLang(ch.language);
                      return (
                        <span
                          key={ch.channel_id}
                          className="chip chip-muted"
                          style={{ fontSize: 11, padding: "2px 8px", display: "inline-flex", alignItems: "center", gap: 4 }}
                        >
                          <span>{chLang?.flag || "🌍"}</span>
                          <span>{ch.name}</span>
                          <span style={{ fontSize: 9.5, opacity: 0.6 }}>({ch.topic_category})</span>
                        </span>
                      );
                    })}
                  </div>
                </div>

                {/* Last Run Info */}
                <div style={{ fontSize: 11, color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
                  <span>Son Üretim:</span>
                  <span style={{ fontFamily: "monospace" }}>
                    {r.last_run ? formatDate(r.last_run) : "Henüz yapılmadı"}
                  </span>
                </div>

                {/* Actions */}
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", paddingTop: 4, borderTop: "1px solid var(--border-subtle)" }}>
                  <button
                    className="btn btn-primary"
                    style={{ flex: 2, padding: "6px 10px", fontSize: 11.5, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 4 }}
                    onClick={() => onTriggerRoutine(r.id, r.name)}
                    disabled={isRunning}
                  >
                    <Play size={12} /> Şimdi Çalıştır
                  </button>
                  <button
                    className="btn btn-ghost"
                    style={{ flex: 1, padding: "6px 8px", fontSize: 11, border: "1px solid var(--border-subtle)" }}
                    onClick={() => handleInspectPlans(r)}
                    title="Bu rutindeki kanalların içerik planını incele"
                  >
                    🔍 Planı İncele
                  </button>
                  {r.auto_open_gemini && (
                    <button
                      className="btn btn-ghost"
                      style={{ padding: "6px 8px", fontSize: 11, border: "1px solid var(--border-subtle)", color: "#c084fc" }}
                      onClick={() => handleOpenGemini(r.id)}
                      title="Gemini web sayfasını aç"
                    >
                      🌐 Gemini
                    </button>
                  )}
                  <button
                    className="btn btn-ghost"
                    style={{ padding: "6px 8px", fontSize: 11, border: "1px solid var(--border-subtle)" }}
                    onClick={() => openEditModal(r)}
                  >
                    <Edit3 size={12} />
                  </button>
                  <button
                    className="btn btn-ghost"
                    style={{ padding: "6px 8px", fontSize: 11, border: "1px solid rgba(239,68,68,0.2)", color: "#f87171" }}
                    onClick={() => handleDeleteRoutine(r.id, r.name)}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Routine Modal (Create / Edit) */}
      <Modal open={showModal} onClose={() => setShowModal(false)} title={editingRoutine ? "Rutini Düzenle" : "Yeni Rutin Oluştur"}>
        <div className="routine-form" style={{ display: "flex", flexDirection: "column", gap: 14, padding: "8px 0" }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: 11.5, marginBottom: 4 }}>Rutin Adı</label>
            <input
              type="text"
              className="form-input"
              value={formName}
              onChange={e => setFormName(e.target.value)}
              placeholder="Örn: Günlük Sabah Rutini (Reddit & Uzay)"
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" style={{ fontSize: 11.5, marginBottom: 4 }}>Çalışma Saati (HH:MM)</label>
              <input
                type="time"
                className="form-input"
                value={formTime}
                onChange={e => setFormTime(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ margin: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <label className="form-label" style={{ fontSize: 11.5, margin: 0 }}>İşlemci Dinlenmesi</label>
                <span style={{ fontSize: 11, color: "var(--accent-primary)", fontWeight: 700 }}>
                  {formRestMinutes} dakika
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                step="1"
                value={formRestMinutes}
                onChange={e => setFormRestMinutes(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--accent-primary)" }}
              />
              <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                Her videodan sonra CPU/GPU soğuması için beklenecek süre.
              </span>
            </div>
          </div>

          <section className="routine-form-section">
            <div className="routine-form-section-heading">
              <div><strong>Çalışma günleri</strong><span>Rutin hangi günlerde tetiklensin?</span></div>
              <span className="routine-selection-count">{formDays.includes("all") ? "7 gün" : `${formDays.length} gün`}</span>
            </div>
            <div className="routine-day-picker">
              {[["all", "Her gün"], ...Object.entries(WEEKDAY_LABELS).map(([value, label]) => [value, label])].map(([day, label]) => {
                const selected = day === "all" ? formDays.includes("all") : formDays.includes(day);
                return (
                  <button
                    key={day}
                    type="button"
                    className={`routine-day-choice ${selected ? "selected" : ""}`}
                    onClick={() => toggleDaySelection(day)}
                    aria-pressed={selected}
                  >
                    {selected && <Check size={13} />}
                    {label}
                  </button>
                );
              })}
            </div>
          </section>

          {/* Channel Selector */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <label className="form-label" style={{ fontSize: 11.5, margin: 0 }}>
                Hedef Kanallar ({formChannels.length}/{channels.length})
              </label>
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  type="button"
                  onClick={selectAllChannels}
                  style={{ background: "none", border: "none", color: "var(--accent-primary)", fontSize: 11, cursor: "pointer", textDecoration: "underline" }}
                >
                  Tümünü Seç
                </button>
                <span style={{ color: "var(--text-muted)" }}>•</span>
                <button
                  type="button"
                  onClick={clearChannelSelection}
                  style={{ background: "none", border: "none", color: "var(--text-muted)", fontSize: 11, cursor: "pointer", textDecoration: "underline" }}
                >
                  Temizle
                </button>
              </div>
            </div>

            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 8,
              maxHeight: 180,
              overflowY: "auto",
              padding: "8px",
              background: "var(--bg-primary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)"
            }}>
              {channels.map(c => {
                const isSelected = formChannels.includes(c.channel_id);
                const cLang = getLang(c.language);
                return (
                  <button
                    key={c.channel_id}
                    type="button"
                    onClick={() => toggleChannelSelection(c.channel_id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "6px 8px",
                      background: isSelected ? "rgba(99,102,241,0.18)" : "transparent",
                      border: isSelected ? "1px solid var(--accent-primary)" : "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-sm)",
                      cursor: "pointer",
                      textAlign: "left",
                      color: isSelected ? "#ffffff" : "var(--text-secondary)",
                      fontSize: 11.5
                    }}
                  >
                    <span>{isSelected ? "✓" : "○"}</span>
                    <span>{cLang?.flag || "🌍"}</span>
                    <span style={{ fontWeight: isSelected ? 600 : 400, flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {c.name}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Options Toggles */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer", color: "var(--text-primary)" }}>
              <input
                type="checkbox"
                checked={formRequireApproval}
                onChange={e => setFormRequireApproval(e.target.checked)}
                style={{ width: 14, height: 14, accentColor: "var(--accent-primary)" }}
              />
              <span>🔔 <strong>Başlatmadan önce onay bildirimi ver</strong> (Belirlenen saatte bana sor)</span>
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer", color: "var(--text-primary)" }}>
              <input
                type="checkbox"
                checked={formAutoOpenGemini}
                onChange={e => setFormAutoOpenGemini(e.target.checked)}
                style={{ width: 14, height: 14, accentColor: "var(--accent-primary)" }}
              />
              <span>🌐 <strong>Rutin başlayınca Gemini sayfasını aç</strong> (Eklenti ile senaryo/görsel hazırla)</span>
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer", color: "var(--text-primary)" }}>
              <input
                type="checkbox"
                checked={formActive}
                onChange={e => setFormActive(e.target.checked)}
                style={{ width: 14, height: 14, accentColor: "var(--accent-primary)" }}
              />
              <span>Rutin Aktif</span>
            </label>
          </div>

          {/* Footer buttons */}
          <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
            <button
              className="btn btn-muted"
              style={{ flex: 1, padding: "8px", fontSize: 12 }}
              onClick={() => setShowModal(false)}
              disabled={saving}
            >
              İptal
            </button>
            <button
              className="btn btn-primary"
              style={{ flex: 2, padding: "8px", fontSize: 12 }}
              onClick={handleSaveRoutine}
              disabled={saving}
            >
              {saving ? "Kaydediliyor..." : (editingRoutine ? "Güncellemeleri Kaydet" : "Rutini Oluştur")}
            </button>
          </div>
        </div>
      </Modal>

      {/* Inspect Modal */}
      <Modal open={inspectModalOpen} onClose={() => setInspectModalOpen(false)} title="Rutin Kanallarının İçerik Planı Durumu">
        <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "8px 0" }}>
          {inspectLoading ? (
            <div style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)" }}>
              <Loader2 className="animate-spin" size={20} style={{ margin: "0 auto 6px" }} />
              <div>İçerik planları taranıyor...</div>
            </div>
          ) : inspectData?.channels ? (
            <>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>
                Rutin tetiklendiğinde üretilecek sonraki plan konuları:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 320, overflowY: "auto" }}>
                {inspectData.channels.map((c, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "10px 12px",
                      background: c.has_unproduced ? "rgba(16, 185, 129, 0.08)" : "rgba(245, 158, 11, 0.08)",
                      border: c.has_unproduced ? "1px solid rgba(16, 185, 129, 0.25)" : "1px solid rgba(245, 158, 11, 0.25)",
                      borderRadius: "var(--radius-md)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 10
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
                        <span>{c.channel_name}</span>
                        <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "monospace" }}>({c.channel_id})</span>
                      </div>
                      {c.has_unproduced ? (
                        <div style={{ fontSize: 11.5, color: "#86efac", marginTop: 2 }}>
                          ✓ Sıradaki Konu (#{c.row_id}): <strong>"{c.title}"</strong>
                        </div>
                      ) : (
                        <div style={{ fontSize: 11.5, color: "#fcd34d", marginTop: 2 }}>
                          ⚠️ İçerik planında üretilecek konu kalmamış.
                        </div>
                      )}
                    </div>
                    <div>
                      {c.has_unproduced ? (
                        <span className="chip chip-success" style={{ fontSize: 9.5 }}>Hazır</span>
                      ) : (
                        <span className="chip chip-warning" style={{ fontSize: 9.5 }}>Konu Yok</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 6, display: "flex", justifyContent: "space-between" }}>
                <span>Toplam {inspectData.ready_count} / {inspectData.total_count} kanal üretime hazır</span>
                <span>Dinlenme Aralığı: {inspectData.rest_minutes} dk</span>
              </div>
            </>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: 12 }}>Bilgi alınamadı.</div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10 }}>
            <button className="btn btn-muted btn-sm" onClick={() => setInspectModalOpen(false)}>
              Kapat
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}


/* ══════════════════════════════════════════════════════════════════
   MATERIALS PAGE (ÜRETİM MATERYALLERİ MERKEZİ)
   ══════════════════════════════════════════════════════════════════ */

function MaterialsPage({ channels, groups = [], selectedChannelId, onSelectChannel, onTriggerTask }) {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeChannelId, setActiveChannelId] = useState(selectedChannelId || "");
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedKeys, setSelectedKeys] = useState([]);
  const [remoteEnv, setRemoteEnv] = useState(false);
  const [expandedScenes, setExpandedScenes] = useState({});
  const [inspectMaterial, setInspectMaterial] = useState(null);
  const [inspectTab, setInspectTab] = useState("scenes");
  const [copiedSceneKey, setCopiedSceneKey] = useState(null);
  const [actionLoadingKey, setActionLoadingKey] = useState(null);
  const [notification, setNotification] = useState(null);
  const [pendingPlanStats, setPendingPlanStats] = useState(null);

  const fetchMaterials = useCallback(async () => {
    setLoading(true);
    try {
      const url = activeChannelId ? `/api/materials?channel_id=${encodeURIComponent(activeChannelId)}` : "/api/materials";
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setMaterials(data.materials || []);
      }
    } catch (err) {
      console.error("Materyaller alınamadı:", err);
    } finally {
      setLoading(false);
    }
  }, [activeChannelId]);

  const fetchPendingStats = useCallback(async () => {
    try {
      const res = await fetch("/api/active-channels/pending-plan");
      if (res.ok) {
        const d = await res.json();
        setPendingPlanStats(d);
      }
    } catch {}
  }, []);

  useEffect(() => {
    fetchMaterials();
    fetchPendingStats();
    const interval = setInterval(() => {
      fetchMaterials();
      fetchPendingStats();
    }, 8000);
    return () => clearInterval(interval);
  }, [fetchMaterials, fetchPendingStats]);

  useEffect(() => {
    if (selectedChannelId !== undefined && selectedChannelId !== null) {
      setActiveChannelId(selectedChannelId);
    }
  }, [selectedChannelId]);

  const handleCopyText = (key, text) => {
    navigator.clipboard.writeText(text);
    setCopiedSceneKey(key);
    setTimeout(() => setCopiedSceneKey(null), 2000);
  };

  const toggleSceneExpand = (key) => {
    setExpandedScenes(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleSelectKey = (key) => {
    setSelectedKeys(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const handleSelectAll = (filteredItems) => {
    const allKeys = filteredItems.map(m => `${m.channel_id}::${m.material_id || m.id}`);
    const isAllSelected = allKeys.length > 0 && allKeys.every(k => selectedKeys.includes(k));
    if (isAllSelected) {
      setSelectedKeys(prev => prev.filter(k => !allKeys.includes(k)));
    } else {
      setSelectedKeys(prev => Array.from(new Set([...prev, ...allKeys])));
    }
  };

  const handleProduceSingle = async (m, useRemote) => {
    const matId = m.material_id || m.id;
    if (!matId) {
      alert("Hata: Geçersiz materyal tanımlayıcısı.");
      return;
    }
    const sceneCount = (m.scenes && m.scenes.length) || (m.script?.scenes && m.script.scenes.length) || m.scene_count || 0;
    if (sceneCount === 0) {
      alert("Bu materyal paketinde hiç sahne bulunamadı! Lütfen önce Gemini eklentisinden geçerli bir senaryo oluşturun.");
      return;
    }

    const itemKey = `${m.channel_id}::${matId}`;
    setActionLoadingKey(itemKey);
    setNotification(null);
    try {
      const res = await fetch(`/api/materials/${encodeURIComponent(m.channel_id)}/${encodeURIComponent(matId)}/produce`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          remote: !!useRemote,
          target_env: useRemote ? "remote" : "local",
          auto_sync_mac: true
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setNotification({
          type: "success",
          message: `"${m.title || matId}" için üretim başlatıldı! ${useRemote ? "(Oracle Cloud Bulut Render)" : "(Lokal Mac)"}`
        });
        if (onTriggerTask && data.exec_id) {
          onTriggerTask({
            channelId: m.channel_id,
            status: "pending",
            exec_id: data.exec_id,
            message: `"${m.title || matId}" üretiliyor...`
          });
        }
        fetchMaterials();
      } else {
        setNotification({
          type: "error",
          message: data.detail || data.error || "Üretim başlatılamadı."
        });
      }
    } catch (err) {
      setNotification({ type: "error", message: `Hata: ${err.message}` });
    } finally {
      setActionLoadingKey(null);
    }
  };

  const handleResearchSingle = async (m) => {
    const matId = m.material_id || m.id;
    if (!matId) {
      alert("Hata: Geçersiz materyal tanımlayıcısı.");
      return;
    }
    const itemKey = `${m.channel_id}::${matId}`;
    setActionLoadingKey(`research::${itemKey}`);
    setNotification(null);
    try {
      const res = await fetch(`/api/materials/${encodeURIComponent(m.channel_id)}/${encodeURIComponent(matId)}/research?force=true`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setNotification({
          type: "success",
          message: `🔍 "${m.title || matId}" için medya araştırması tamamlandı! (${data.verified_media_count}/${data.total_scenes} sahne doğrulandı)`
        });
        fetchMaterials();
      } else {
        setNotification({
          type: "error",
          message: data.detail || data.error || "Araştırma başlatılamadı."
        });
      }
    } catch (err) {
      setNotification({ type: "error", message: `Hata: ${err.message}` });
    } finally {
      setActionLoadingKey(null);
    }
  };

  const handleBatchResearch = async () => {
    const chId = activeChannelId || "blackboxaudioo";
    const chObj = channels.find(c => c.channel_id === chId);
    const chName = chObj?.name || chId;

    const ok = window.confirm(
      `"${chName}" kanalındaki tüm üretilmemiş materyaller için tarihi arşiv (Wikimedia), 1080p B-roll ve telemetri grafikleri taranıp doğrulanacaktır.\n\nİşlemi başlatmak istiyor musunuz?`
    );
    if (!ok) return;

    setActionLoadingKey("batch_research");
    setNotification(null);
    try {
      const res = await fetch(`/api/materials/${encodeURIComponent(chId)}/research-all?force=false`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setNotification({
          type: "success",
          message: `🔍 Toplu araştırma tamamlandı! ${data.processed_count} materyal başarıyla işlendi.`
        });
        fetchMaterials();
      } else {
        setNotification({
          type: "error",
          message: data.detail || data.error || "Toplu araştırma başarısız oldu."
        });
      }
    } catch (err) {
      setNotification({ type: "error", message: `Hata: ${err.message}` });
    } finally {
      setActionLoadingKey(null);
    }
  };

  const handleBatchProduce = async (selectedOnly = true) => {
    let targets = [];
    if (selectedOnly) {
      targets = materials.filter(m =>
        selectedKeys.includes(`${m.channel_id}::${m.material_id || m.id}`) &&
        ["ready", "materyaller_hazir"].includes(m.status || "ready")
      );
    } else {
      targets = materials.filter(m => ["ready", "materyaller_hazir"].includes(m.status || "ready") && (!activeChannelId || m.channel_id === activeChannelId));
    }

    const invalidTargets = targets.filter(m => {
      const sc = (m.scenes && m.scenes.length) || (m.script?.scenes && m.script.scenes.length) || m.scene_count || 0;
      return sc === 0;
    });
    if (invalidTargets.length > 0) {
      alert(`Seçilen ${invalidTargets.length} adet materyalin senaryo sahneleri boş (0 sahne). Lütfen yalnızca sahneleri hazır materyalleri seçin.`);
      return;
    }

    if (targets.length === 0) {
      alert("Lütfen kuyruğa eklenecek en az bir materyal seçin.");
      return;
    }

    const envName = remoteEnv ? "☁️ Oracle Cloud Bulut Sunucusu" : "🖥️ Lokal Mac (Apple Silicon)";
    const ok = window.confirm(
      `${targets.length} adet senaryo materyali ${envName} üzerinde sırayla kuyrukta üretilecek.\n\nHer üretim tamamlandıktan sonra bellek ve GPU temizliği otomatik olarak yapılacaktır.\n\nKuyruğu başlatmak istiyor musunuz?`
    );
    if (!ok) return;

    setActionLoadingKey("batch");
    setNotification(null);
    try {
      const payload = {
        material_keys: targets.map(m => ({ channel_id: m.channel_id, material_id: m.material_id || m.id })),
        materials: targets.map(m => ({ channel_id: m.channel_id, material_id: m.material_id || m.id })),
        target_env: remoteEnv ? "remote" : "local",
        remote: !!remoteEnv,
        auto_sync_mac: true
      };
      const res = await fetch("/api/materials/batch-produce", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setNotification({
          type: "success",
          message: `Kuyruk başarıyla başlatıldı! Toplam ${targets.length} içerik sırayla üretiliyor. (Kuyruk ID: ${data.exec_id || data.batch_id})`
        });
        setSelectedKeys([]);
        fetchMaterials();
      } else {
        setNotification({
          type: "error",
          message: data.detail || data.error || "Toplu üretim başlatılamadı."
        });
      }
    } catch (err) {
      setNotification({ type: "error", message: `Hata: ${err.message}` });
    } finally {
      setActionLoadingKey(null);
    }
  };

  const handleDeleteMaterial = async (m) => {
    const matId = m.material_id || m.id;
    const ok = window.confirm(`"${m.title || matId}" senaryo materyalini tamamen silmek istediğinize emin misiniz?`);
    if (!ok) return;
    try {
      const res = await fetch(`/api/materials/${encodeURIComponent(m.channel_id)}/${encodeURIComponent(matId)}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setMaterials(prev => prev.filter(item => !(item.channel_id === m.channel_id && (item.material_id || item.id) === matId)));
        setSelectedKeys(prev => prev.filter(k => k !== `${m.channel_id}::${matId}`));
      } else {
        alert("Materyal silinemedi.");
      }
    } catch (err) {
      alert("Hata: " + err.message);
    }
  };

  const isMatchChannelOrGroup = useCallback((m, selectedId) => {
    if (!selectedId) return true;
    if (m.channel_id === selectedId) return true;
    if (m.is_group) {
      if (m.group_id === selectedId || `group:${m.group_id}` === selectedId) return true;
      if (m.member_channel_ids?.includes(selectedId) || m.member_channels?.includes(selectedId)) return true;
    }
    return false;
  }, []);

  const filteredMaterials = useMemo(() => {
    return materials.filter(m => {
      if (activeChannelId && !isMatchChannelOrGroup(m, activeChannelId)) return false;
      if (statusFilter === "ready" && !["ready", "materyaller_hazir"].includes(m.status || "ready")) return false;
      if (statusFilter === "produced" && !["produced", "downloaded"].includes(m.status)) return false;
      if (statusFilter === "failed" && m.status !== "failed") return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = (m.title || "").toLowerCase().includes(q);
        const matchTopic = (m.topic || "").toLowerCase().includes(q);
        const matchChannel = (m.channel_name || m.channel_id || "").toLowerCase().includes(q);
        const matchTags = (m.tags || []).some(t => t.toLowerCase().includes(q));
        if (!matchTitle && !matchTopic && !matchChannel && !matchTags) return false;
      }
      return true;
    });
  }, [materials, activeChannelId, statusFilter, searchQuery, isMatchChannelOrGroup]);

  const readyCount = useMemo(() => {
    return materials.filter(m => ["ready", "materyaller_hazir"].includes(m.status || "ready") && (!activeChannelId || isMatchChannelOrGroup(m, activeChannelId))).length;
  }, [materials, activeChannelId, isMatchChannelOrGroup]);

  const producedCount = useMemo(() => {
    return materials.filter(m => ["produced", "downloaded"].includes(m.status) && (!activeChannelId || isMatchChannelOrGroup(m, activeChannelId))).length;
  }, [materials, activeChannelId, isMatchChannelOrGroup]);

  const allFilteredSelected = filteredMaterials.length > 0 && filteredMaterials.every(m => selectedKeys.includes(`${m.channel_id}::${m.material_id || m.id}`));

  return (
    <div>
      {/* Üst Başlık ve İpuçları */}
      <div style={{ marginBottom: 20, display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <Layers size={22} className="text-cyan-400" /> Üretim Materyalleri Merkezi
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 5 }}>
            Gemini İçerik Planlayıcı ile hazırlanan senaryo & görsel istemleri paketleri · Tekli üretim veya sırayla toplu kuyruk
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={fetchMaterials} disabled={loading} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Yenile
          </button>
        </div>
      </div>

      {/* Bildirim Alanı */}
      {notification && (
        <div style={{
          padding: "10px 14px",
          marginBottom: 16,
          borderRadius: "var(--radius-md)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: notification.type === "success" ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)",
          border: notification.type === "success" ? "1px solid rgba(16,185,129,0.3)" : "1px solid rgba(239,68,68,0.3)",
          color: notification.type === "success" ? "#34d399" : "#f87171",
          fontSize: 12.5
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {notification.type === "success" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            <span>{notification.message}</span>
          </div>
          <button style={{ background: "none", border: "none", color: "inherit", cursor: "pointer" }} onClick={() => setNotification(null)}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* Aktif Kanalların Bekleyen Planları Bildirimi */}
      {pendingPlanStats && pendingPlanStats.total_pending > 0 && (
        <div style={{
          padding: "10px 16px",
          marginBottom: 16,
          borderRadius: "var(--radius-md)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 10,
          background: "rgba(6, 182, 212, 0.08)",
          border: "1px solid rgba(6, 182, 212, 0.28)",
          color: "#22d3ee",
          fontSize: 12.5
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1 }}>
            <Sparkles size={16} className="text-cyan-400" />
            <span>
              Aktif kanalların mevcut içerik takviminde materyali henüz üretilmemiş <strong>{pendingPlanStats.total_pending} adet konu</strong> bekliyor.
              Gemini eklentisindeki <em>"Geçmişe Dönük Üret"</em> sekmesini kullanarak bu konuların senaryo ve görsel promptlarını tek tıkla üretebilirsiniz.
            </span>
          </div>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            padding: "3px 8px",
            borderRadius: 6,
            background: "rgba(6, 182, 212, 0.2)",
            color: "#fff"
          }}>
            {pendingPlanStats.channels.filter(c => c.pending_count > 0).length} Kanal Bekliyor
          </span>
        </div>
      )}

      {/* Kontrol & Filtre Paneli */}
      <div className="card" style={{ padding: "16px 20px", marginBottom: 20 }}>
        {/* Satır 1: Kanal Seçimi, Arama ve Durum Sekmeleri */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", flex: 1 }}>
            <div style={{ minWidth: 200 }}>
              <select
                className="form-input"
                style={{
                  width: "100%",
                  padding: "7px 10px",
                  fontSize: 12.5,
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-primary)",
                  cursor: "pointer"
                }}
                value={activeChannelId}
                onChange={(e) => {
                  const val = e.target.value;
                  setActiveChannelId(val);
                  if (onSelectChannel) onSelectChannel(val || null);
                }}
              >
                <option value="">🌐 Tüm Kanallar & Gruplar ({materials.length} Materyal)</option>
                {groups && groups.length > 0 && (
                  <optgroup label="📁 Kanal Grupları (Çok Dilli)">
                    {groups.map(g => (
                      <option key={g.id} value={`group:${g.id}`}>
                        📁 [GRUP] {g.name || g.id} ({g.channel_ids?.length || 0} kanal)
                      </option>
                    ))}
                  </optgroup>
                )}
                <optgroup label="📺 Tekil Kanallar">
                  {channels.map(c => {
                    const l = getLang(c.language);
                    return (
                      <option key={c.channel_id} value={c.channel_id}>
                        {l.flag} {c.name || c.channel_id} ({c.topic_category || "genel"})
                      </option>
                    );
                  })}
                </optgroup>
              </select>
            </div>

            <div style={{ position: "relative", minWidth: 220, flex: "1 1 200px" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
              <input
                type="text"
                placeholder="Başlık, etiket, konu ara..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-input"
                style={{
                  width: "100%",
                  padding: "7px 10px 7px 32px",
                  fontSize: 12.5,
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-primary)"
                }}
              />
            </div>
          </div>

          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {[
              { id: "all", label: `Tümü (${materials.length})` },
              { id: "ready", label: `📦 Hazır (${readyCount})` },
              { id: "produced", label: `✅ Üretildi (${producedCount})` },
              { id: "failed", label: `❌ Hata (${materials.filter(m => m.status === "failed").length})` },
            ].map(tab => (
              <button
                key={tab.id}
                className={`btn btn-sm ${statusFilter === tab.id ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setStatusFilter(tab.id)}
                style={{ fontSize: 11.5, padding: "5px 10px" }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Satır 2: Kuyruk / Üretim Ortamı ve Toplu Aksiyonlar */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
          paddingTop: 14,
          borderTop: "1px solid var(--border-subtle)"
        }}>
          {/* Ortam Seçimi */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500 }}>Üretim Hedefi:</span>
            <div style={{
              display: "inline-flex",
              background: "var(--bg-secondary)",
              borderRadius: "var(--radius-sm)",
              padding: 2,
              border: "1px solid var(--border-subtle)"
            }}>
              <button
                type="button"
                onClick={() => setRemoteEnv(false)}
                style={{
                  padding: "4px 10px",
                  fontSize: 11.5,
                  fontWeight: !remoteEnv ? 600 : 400,
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  background: !remoteEnv ? "linear-gradient(135deg, #06b6d4, #3b82f6)" : "transparent",
                  color: !remoteEnv ? "#fff" : "var(--text-muted)",
                  transition: "all 0.2s"
                }}
              >
                🖥️ Lokal (Mac)
              </button>
              <button
                type="button"
                onClick={() => setRemoteEnv(true)}
                style={{
                  padding: "4px 10px",
                  fontSize: 11.5,
                  fontWeight: remoteEnv ? 600 : 400,
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  background: remoteEnv ? "linear-gradient(135deg, #8b5cf6, #6366f1)" : "transparent",
                  color: remoteEnv ? "#fff" : "var(--text-muted)",
                  transition: "all 0.2s"
                }}
              >
                ☁️ Oracle Cloud (aarch64)
              </button>
            </div>
          </div>

          {/* Toplu İşlem Butonları */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn"
              onClick={() => handleSelectAll(filteredMaterials)}
              disabled={filteredMaterials.length === 0}
              style={{
                padding: "6px 12px",
                fontSize: 12,
                background: allFilteredSelected ? "rgba(99,102,241,0.18)" : "rgba(255,255,255,0.05)",
                color: allFilteredSelected ? "#818cf8" : "var(--text-primary)",
                border: allFilteredSelected ? "1px solid rgba(99,102,241,0.4)" : "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                display: "inline-flex",
                alignItems: "center",
                gap: 5
              }}
            >
              {allFilteredSelected ? "✓ Seçimi Kaldır" : `Tümünü Seç (${filteredMaterials.length})`}
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleBatchProduce(true)}
              disabled={selectedKeys.length === 0 || actionLoadingKey === "batch"}
              style={{
                padding: "6px 14px",
                fontSize: 12,
                background: selectedKeys.length > 0 ? "linear-gradient(135deg, #06b6d4, #6366f1)" : "rgba(255,255,255,0.06)",
                border: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                fontWeight: 600,
                boxShadow: selectedKeys.length > 0 ? "0 2px 10px rgba(6,182,212,0.3)" : "none"
              }}
            >
              {actionLoadingKey === "batch" ? (
                <>
                  <Loader2 size={13} className="animate-spin" /> Kuyruk Başlatılıyor...
                </>
              ) : (
                <>
                  <Zap size={13} /> Seçilenleri Sırayla Üret ({selectedKeys.length})
                </>
              )}
            </button>

            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => handleBatchProduce(false)}
              disabled={readyCount === 0 || actionLoadingKey === "batch"}
              style={{
                padding: "6px 12px",
                fontSize: 12,
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                border: "1px solid rgba(6,182,212,0.3)",
                color: "#22d3ee"
              }}
              title="Bekleyen tüm hazır materyalleri tek tıkla arka arkaya kuyrukta üretir"
            >
              <Play size={12} fill="currentColor" /> Tüm Hazırları Üret ({readyCount})
            </button>

            <button
              type="button"
              className="btn btn-ghost"
              onClick={handleBatchResearch}
              disabled={loading || actionLoadingKey === "batch_research"}
              style={{
                padding: "6px 12px",
                fontSize: 12,
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                border: "1px solid rgba(14,165,233,0.3)",
                color: "#38bdf8"
              }}
              title="Bu kanaldaki tüm üretilmemiş materyalleri otomatik araştırıp görsellerini doğrular"
            >
              {actionLoadingKey === "batch_research" ? (
                <>
                  <Loader2 size={12} className="animate-spin" /> Araştırılıyor...
                </>
              ) : (
                <>
                  <Search size={12} /> Tümünü Araştır
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Materyal Listesi */}
      {loading && materials.length === 0 ? (
        <div style={{ padding: 60, textAlign: "center", color: "var(--text-muted)" }}>
          <Loader2 size={24} className="animate-spin" style={{ margin: "0 auto 12px" }} />
          <div>Materyaller yükleniyor...</div>
        </div>
      ) : filteredMaterials.length === 0 ? (
        <div className="card" style={{ padding: "50px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 36, marginBottom: 12, opacity: 0.4 }}>📦</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
            Kayıtlı Üretim Materyali Bulunamadı
          </div>
          <div style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 520, margin: "0 auto", lineHeight: 1.6 }}>
            Gemini Web sayfasındaki eklentiden <strong>"İçerik Planla"</strong> butonuna basın ve <strong>"Eksiksiz Senaryo & Üretim Materyalleri Üret"</strong> seçeneğini işaretleyin. Senaryolar ve görsel istemleri doğrudan sistem klasörüne (<code>output/&lt;kanal&gt;/Üretim Metaryalleri/</code>) kaydedilecek ve burada listelenecektir.
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {filteredMaterials.map(m => {
            const matId = m.material_id || m.id;
            const itemKey = `${m.channel_id}::${matId}`;
            const isSelected = selectedKeys.includes(itemKey);
            const isExpanded = !!expandedScenes[itemKey];
            const channelObj = channels.find(c => c.channel_id === m.channel_id);
            const channelLang = channelObj ? getLang(channelObj.language) : null;
            const isCurrentlyProducing = actionLoadingKey === itemKey;
            const cardScenes = (m.scenes && m.scenes.length > 0) ? m.scenes : (m.script?.scenes || m.script?.tr?.scenes || m.script?.en?.scenes || []);
            const sceneCount = cardScenes.length || m.scene_count || 0;
            const hasEmptyScenes = sceneCount === 0;

            const isProduced = m.status === "produced" || m.status === "downloaded";
            const isFailed = m.status === "failed";
            const isProcessing = ["processing", "rendering", "producing"].includes(m.status);
            const isCloudQueued = m.status === "in_cloud_queue";
            const canProduce = !isProduced && !isProcessing && !isCloudQueued;

            return (
              <div
                key={itemKey}
                className="card"
                style={{
                  padding: "16px 20px",
                  borderRadius: "var(--radius-md)",
                  border: isSelected ? "1px solid rgba(6,182,212,0.5)" : "1px solid var(--border-subtle)",
                  background: isSelected ? "rgba(6,182,212,0.03)" : "var(--bg-card)",
                  transition: "all 0.2s ease"
                }}
              >
                {/* Kart Başlığı ve Bilgi Rozetleri */}
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, marginBottom: 12 }}>
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 10, flex: 1 }}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectKey(itemKey)}
                      disabled={!canProduce}
                      style={{ marginTop: 4, cursor: "pointer", width: 15, height: 15, accentColor: "var(--accent-primary)" }}
                    />
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
                        <span style={{
                          fontSize: 11,
                          fontWeight: 600,
                          padding: "2px 7px",
                          borderRadius: 4,
                          background: m.is_group ? "rgba(139, 92, 246, 0.18)" : "rgba(255,255,255,0.06)",
                          color: m.is_group ? "#c084fc" : "var(--text-secondary)",
                          border: m.is_group ? "1px solid rgba(139, 92, 246, 0.35)" : "none",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4
                        }}>
                          {m.is_group ? "📁 [GRUP]" : (channelLang?.flag || "📺")} {m.channel_name || channelObj?.name || m.channel_id}
                        </span>

                        {isProduced ? (
                          <span className="chip chip-success" style={{ fontSize: 10, padding: "2px 6px" }}>
                            {m.status === "downloaded" ? "✅ Video Üretildi · İndirildi" : "✅ Video Üretildi"}
                          </span>
                        ) : isCloudQueued ? (
                          <span className="chip chip-warning" style={{ fontSize: 10, padding: "2px 6px" }}>
                            ☁️ Sunucu Kuyruğunda
                          </span>
                        ) : isProcessing ? (
                          <span className="chip chip-warning" style={{ fontSize: 10, padding: "2px 6px", display: "inline-flex", alignItems: "center", gap: 4 }}>
                            <Loader2 size={10} className="animate-spin" /> ⚙️ Üretimde
                          </span>
                        ) : isFailed ? (
                          <span className="chip" style={{ fontSize: 10, padding: "2px 6px", background: "rgba(239,68,68,0.15)", color: "#f87171", border: "1px solid rgba(239,68,68,0.3)" }}>
                            ❌ Hata
                          </span>
                        ) : (
                          <span className="chip" style={{ fontSize: 10, padding: "2px 6px", background: "rgba(6,182,212,0.18)", color: "#22d3ee", border: "1px solid rgba(6,182,212,0.35)" }}>
                            📦 Hazır (Bekliyor)
                          </span>
                        )}

                        {hasEmptyScenes && (
                          <span className="chip" style={{ fontSize: 10, padding: "2px 6px", background: "rgba(245, 158, 11, 0.15)", color: "#fbbf24", border: "1px solid rgba(245, 158, 11, 0.35)" }}>
                            ⚠️ Senaryo Boş (0 Sahne)
                          </span>
                        )}

                        {m.researched ? (
                          <span className="chip" style={{ fontSize: 10, padding: "2px 6px", background: "rgba(16, 185, 129, 0.15)", color: "#34d399", border: "1px solid rgba(16, 185, 129, 0.35)", display: "inline-flex", alignItems: "center", gap: 3 }} title={`Medya doğrulaması tamamlandı (${m.media_coverage || "100%"})`}>
                            <CheckCircle2 size={10} /> 🔍 Araştırıldı ({m.media_coverage || "100%"})
                          </span>
                        ) : (
                          <span className="chip" style={{ fontSize: 10, padding: "2px 6px", background: "rgba(14, 165, 233, 0.12)", color: "#38bdf8", border: "1px solid rgba(14, 165, 233, 0.25)", display: "inline-flex", alignItems: "center", gap: 3 }} title="Medya araştırması bekliyor. Yanındaki 'Araştır' butonuyla başlatabilirsiniz.">
                            <Search size={10} /> Araştırma Bekliyor
                          </span>
                        )}

                        <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace" }}>
                          {matId}
                        </span>
                        {m.created_at && (
                          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                            · {m.created_at.slice(0, 16).replace("T", " ")}
                          </span>
                        )}
                      </div>

                      <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 6px 0", lineHeight: 1.4 }}>
                        {m.title || m.baslik || m.konu || "Başlıksız Senaryo"}
                      </h3>

                      {m.description && (
                        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5, maxWidth: 850 }}>
                          {m.description.length > 200 ? m.description.slice(0, 200) + "..." : m.description}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Sağ Taraf: Aksiyon Butonları */}
                  <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", flexShrink: 0 }}>
                    <button
                      className="btn btn-sm"
                      onClick={() => handleResearchSingle(m)}
                      disabled={actionLoadingKey === `research::${itemKey}` || hasEmptyScenes}
                      style={{
                        padding: "5px 10px",
                        fontSize: 11.5,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                        background: m.researched
                          ? "rgba(14, 165, 233, 0.15)"
                          : "linear-gradient(135deg, #0ea5e9, #0284c7)",
                        border: m.researched ? "1px solid rgba(14, 165, 233, 0.4)" : "none",
                        color: m.researched ? "#38bdf8" : "#fff",
                        cursor: hasEmptyScenes ? "not-allowed" : "pointer"
                      }}
                      title="Tarihi NTSB fotoğrafları, 1080p B-roll ve telemetri grafikleri araştırıp doğrular"
                    >
                      {actionLoadingKey === `research::${itemKey}` ? (
                        <>
                          <Loader2 size={12} className="animate-spin" /> Araştırılıyor...
                        </>
                      ) : (
                        <>
                          <Search size={11} /> {m.researched ? "Yeniden Araştır" : "Araştır"}
                        </>
                      )}
                    </button>

                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleProduceSingle(m, false)}
                      disabled={isCurrentlyProducing || hasEmptyScenes || !canProduce}
                      style={{
                        padding: "5px 10px",
                        fontSize: 11.5,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                        background: hasEmptyScenes ? "var(--bg-secondary)" : "linear-gradient(135deg, #06b6d4, #3b82f6)",
                        border: "none",
                        color: hasEmptyScenes ? "var(--text-muted)" : "#fff",
                        cursor: hasEmptyScenes ? "not-allowed" : "pointer"
                      }}
                      title={hasEmptyScenes ? "Senaryo sahneleri boş olduğu için üretilemez" : "Bu materyali lokal Mac üzerinde render eder"}
                    >
                      {isCurrentlyProducing ? <Loader2 size={12} className="animate-spin" /> : <Play size={11} fill="currentColor" />}
                      Lokal Üret
                    </button>

                    <button
                      className="btn btn-sm"
                      onClick={() => handleProduceSingle(m, true)}
                      disabled={isCurrentlyProducing || hasEmptyScenes || !canProduce}
                      style={{
                        padding: "5px 10px",
                        fontSize: 11.5,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                        background: hasEmptyScenes ? "var(--bg-secondary)" : "linear-gradient(135deg, #8b5cf6, #6366f1)",
                        border: "none",
                        color: hasEmptyScenes ? "var(--text-muted)" : "#fff",
                        cursor: hasEmptyScenes ? "not-allowed" : "pointer"
                      }}
                      title={hasEmptyScenes ? "Senaryo sahneleri boş olduğu için üretilemez" : "Bu materyali Oracle Cloud aarch64 sunucusunda render eder"}
                    >
                      <Server size={11} /> Bulut Üret
                    </button>

                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => setInspectMaterial(m)}
                      style={{ padding: "5px 8px", fontSize: 11.5, display: "inline-flex", alignItems: "center", gap: 4 }}
                      title="Tam senaryoyu, sahneleri ve JSON verisini incele"
                    >
                      <Eye size={12} /> Detay
                    </button>

                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleDeleteMaterial(m)}
                      style={{ padding: "5px 8px", fontSize: 11.5, color: "#f87171" }}
                      title="Materyal klasörünü sil"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>

                {/* Rozetler ve Sahne Aç/Kapa Şeridi */}
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: 8,
                  paddingTop: 10,
                  marginTop: 8,
                  borderTop: "1px dashed var(--border-subtle)",
                  fontSize: 11.5
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ color: "var(--text-muted)", display: "inline-flex", alignItems: "center", gap: 4 }}>
                      <Video size={13} className="text-cyan-400" /> <strong>{sceneCount}</strong> Sahne
                    </span>

                    {m.style_prompt && (
                      <span style={{
                        maxWidth: 260,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        padding: "2px 7px",
                        borderRadius: 4,
                        background: "rgba(147,51,234,0.12)",
                        color: "#c084fc",
                        border: "1px solid rgba(147,51,234,0.25)"
                      }} title={m.style_prompt}>
                        🎨 {m.style_prompt}
                      </span>
                    )}

                    {(m.tags && m.tags.length > 0) && (
                      <span style={{ color: "var(--text-muted)" }}>
                        🏷️ {m.tags.slice(0, 3).join(", ")}
                        {m.tags.length > 3 && ` +${m.tags.length - 3}`}
                      </span>
                    )}

                    {m.has_images && (
                      <span style={{
                        padding: "1px 6px",
                        borderRadius: 4,
                        background: "rgba(16,185,129,0.12)",
                        color: "#34d399",
                        border: "1px solid rgba(16,185,129,0.25)",
                        fontSize: 10.5
                      }}>
                        🖼️ Görseller Dahil
                      </span>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => toggleSceneExpand(itemKey)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--accent-primary)",
                      cursor: "pointer",
                      fontSize: 11.5,
                      fontWeight: 600,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                      padding: "2px 4px"
                    }}
                  >
                    {isExpanded ? (
                      <>
                        <ChevronUp size={13} /> Sahneleri Gizle
                      </>
                    ) : (
                      <>
                        <ChevronDown size={13} /> Sahneleri & İstemleri Göster ({sceneCount})
                      </>
                    )}
                  </button>
                </div>

                {/* Katlanabilir Sahne Listesi */}
                {isExpanded && (
                  <div style={{
                    marginTop: 12,
                    padding: "12px 14px",
                    background: "var(--bg-secondary)",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10
                  }}>
                    {(!cardScenes || cardScenes.length === 0) ? (
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Sahne detayı bulunmuyor.</div>
                    ) : (
                      cardScenes.map((sc, idx) => {
                        const sceneCopyKey = `${itemKey}_sc_${idx}`;
                        const isCopied = copiedSceneKey === sceneCopyKey;

                        return (
                          <div
                            key={idx}
                            style={{
                              padding: "10px 12px",
                              borderRadius: 6,
                              background: "rgba(255,255,255,0.02)",
                              border: "1px solid rgba(255,255,255,0.04)"
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                              <span style={{ fontSize: 11, fontWeight: 700, color: "#22d3ee" }}>
                                Sahne #{sc.scene_num || idx + 1} {sc.emotion && `(${sc.emotion})`}
                              </span>
                              <button
                                type="button"
                                onClick={() => handleCopyText(sceneCopyKey, sc.image_prompt || sc.narration || "")}
                                style={{
                                  background: "none",
                                  border: "none",
                                  color: isCopied ? "#34d399" : "var(--text-muted)",
                                  cursor: "pointer",
                                  fontSize: 11,
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 3
                                }}
                                title="İstemi veya metni kopyala"
                              >
                                {isCopied ? <Check size={11} /> : <Copy size={11} />}
                                {isCopied ? "Kopyalandı" : "İstemi Kopyala"}
                              </button>
                            </div>

                            {sc.narration && (
                              <div style={{ fontSize: 12, color: "var(--text-primary)", marginBottom: 6, fontStyle: "italic", lineHeight: 1.4 }}>
                                "{sc.narration}"
                              </div>
                            )}

                            {sc.image_prompt && (
                              <div style={{
                                fontSize: 11,
                                fontFamily: "monospace",
                                background: "rgba(0,0,0,0.25)",
                                padding: "6px 8px",
                                borderRadius: 4,
                                color: "var(--text-secondary)",
                                lineHeight: 1.4,
                                border: "1px solid rgba(255,255,255,0.03)"
                              }}>
                                <strong style={{ color: "#a78bfa" }}>Prompt:</strong> {sc.image_prompt}
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Detay & İnceleme Modalı */}
      {inspectMaterial && (
        <Modal
          open={!!inspectMaterial}
          onClose={() => setInspectMaterial(null)}
          title={`📦 Materyal Detayı: ${inspectMaterial.title || inspectMaterial.material_id}`}
        >
          <div style={{ minWidth: 500, maxWidth: 750 }}>
            {/* Modal Sekmeleri */}
            <div style={{ display: "flex", gap: 8, marginBottom: 14, borderBottom: "1px solid var(--border-subtle)", paddingBottom: 8 }}>
              <button
                className={`btn btn-sm ${inspectTab === "scenes" ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setInspectTab("scenes")}
                style={{ fontSize: 12 }}
              >
                🎬 Sahneler ({inspectMaterial.scenes?.length || 0})
              </button>
              <button
                className={`btn btn-sm ${inspectTab === "media" ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setInspectTab("media")}
                style={{ fontSize: 12 }}
              >
                🔍 Doğrulanmış Medya ({Object.keys(inspectMaterial.scene_media || inspectMaterial.images || {}).length})
              </button>
              <button
                className={`btn btn-sm ${inspectTab === "metadata" ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setInspectTab("metadata")}
                style={{ fontSize: 12 }}
              >
                ℹ️ Bilgiler & Prompt
              </button>
              <button
                className={`btn btn-sm ${inspectTab === "json" ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setInspectTab("json")}
                style={{ fontSize: 12 }}
              >
                📄 Ham JSON
              </button>
            </div>

            {inspectTab === "scenes" && (() => {
              const modalScenes = (inspectMaterial.scenes && inspectMaterial.scenes.length > 0) ? inspectMaterial.scenes : (inspectMaterial.script?.scenes || inspectMaterial.script?.tr?.scenes || inspectMaterial.script?.en?.scenes || []);
              return (
                <div style={{ maxHeight: 420, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, paddingRight: 4 }}>
                  {modalScenes.length === 0 ? (
                    <div style={{ padding: 20, textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>Sahne verisi bulunamadı.</div>
                  ) : modalScenes.map((sc, i) => (
                  <div key={i} style={{ padding: 12, borderRadius: 6, background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#22d3ee", marginBottom: 4 }}>
                      Sahne {sc.scene_num || i + 1} {sc.emotion && `· ${sc.emotion}`}
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--text-primary)", marginBottom: 8, lineHeight: 1.5 }}>
                      {sc.narration}
                    </div>
                    {sc.image_prompt && (
                      <div style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text-secondary)", background: "rgba(0,0,0,0.3)", padding: 8, borderRadius: 4 }}>
                        <span style={{ color: "#a78bfa" }}>SD Prompt: </span>
                        {sc.image_prompt}
                      </div>
                    )}
                  </div>
                ))}
                </div>
              );
            })()}

            {inspectTab === "media" && (() => {
              const sceneMedia = inspectMaterial.scene_media || {};
              const images = inspectMaterial.images || {};
              const keys = Array.from(new Set([...Object.keys(sceneMedia), ...Object.keys(images)])).sort((a,b) => Number(a) - Number(b));
              if (keys.length === 0) {
                return (
                  <div style={{ padding: 30, textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>
                    Henüz araştırma yapılmamış. "Araştır" butonuna tıklayarak Wikimedia, Pixabay ve telemetri arşivlerinden medyaları otomatik bulup doğrulayabilirsiniz.
                  </div>
                );
              }
              return (
                <div style={{ maxHeight: 420, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, paddingRight: 4 }}>
                  {keys.map((k) => {
                    const sm = sceneMedia[k] || {};
                    const imgPath = images[k] || sm.path || "";
                    const isVid = sm.type === "video" || imgPath.endsWith(".mp4");
                    const fileName = imgPath ? imgPath.split("/").pop() : "";
                    return (
                      <div key={k} style={{ padding: 12, borderRadius: 6, background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                          <span style={{ fontSize: 12, fontWeight: 700, color: "#22d3ee" }}>
                            Sahne {Number(k) + 1} {isVid ? "🎬 Video Klip" : "📷 Görsel"}
                          </span>
                          <div style={{ display: "flex", gap: 6 }}>
                            <span className="chip" style={{ fontSize: 10, padding: "2px 6px", background: "rgba(14,165,233,0.15)", color: "#38bdf8" }}>
                              {sm.source || "Yerel/Harici"}
                            </span>
                            {sm.score && (
                              <span className="chip chip-success" style={{ fontSize: 10, padding: "2px 6px" }}>
                                Skor: %{sm.score}
                              </span>
                            )}
                          </div>
                        </div>
                        <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                          {sm.title || fileName}
                        </div>
                        {sm.reason && (
                          <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 6 }}>
                            💡 {sm.reason}
                          </div>
                        )}
                        <div style={{ fontSize: 10.5, fontFamily: "monospace", color: "var(--text-muted)", wordBreak: "break-all" }}>
                          📁 {imgPath}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}

            {inspectTab === "metadata" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 12.5 }}>
                <div>
                  <strong style={{ color: "var(--text-secondary)" }}>Kanal:</strong> {inspectMaterial.channel_id}
                </div>
                <div>
                  <strong style={{ color: "var(--text-secondary)" }}>Klasör / ID:</strong> <code>{inspectMaterial.material_id}</code>
                </div>
                <div>
                  <strong style={{ color: "var(--text-secondary)" }}>Başlık:</strong> {inspectMaterial.title}
                </div>
                {inspectMaterial.topic && (
                  <div>
                    <strong style={{ color: "var(--text-secondary)" }}>Konu:</strong> {inspectMaterial.topic}
                  </div>
                )}
                {inspectMaterial.style_prompt && (
                  <div>
                    <strong style={{ color: "var(--text-secondary)" }}>Görsel Stil İstemi:</strong>
                    <div style={{ marginTop: 4, padding: 8, background: "var(--bg-secondary)", borderRadius: 4, fontFamily: "monospace", fontSize: 11.5 }}>
                      {inspectMaterial.style_prompt}
                    </div>
                  </div>
                )}
                {inspectMaterial.description && (
                  <div>
                    <strong style={{ color: "var(--text-secondary)" }}>Açıklama:</strong>
                    <div style={{ marginTop: 4, padding: 8, background: "var(--bg-secondary)", borderRadius: 4, fontSize: 12, lineHeight: 1.5 }}>
                      {inspectMaterial.description}
                    </div>
                  </div>
                )}
                {inspectMaterial.tags && (
                  <div>
                    <strong style={{ color: "var(--text-secondary)" }}>Etiketler:</strong> {inspectMaterial.tags.join(", ")}
                  </div>
                )}
              </div>
            )}

            {inspectTab === "json" && (
              <div>
                <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 6 }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: 11 }}
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(inspectMaterial, null, 2));
                      alert("JSON panoya kopyalandı!");
                    }}
                  >
                    <Copy size={11} /> Kopyala
                  </button>
                </div>
                <pre style={{
                  maxHeight: 380,
                  overflowY: "auto",
                  padding: 12,
                  background: "rgba(0,0,0,0.5)",
                  borderRadius: 6,
                  fontSize: 11,
                  fontFamily: "monospace",
                  color: "#34d399",
                  border: "1px solid var(--border-subtle)"
                }}>
                  {JSON.stringify(inspectMaterial, null, 2)}
                </pre>
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", gap: 8 }}>
                {(() => {
                  const targetSc = (inspectMaterial.scenes && inspectMaterial.scenes.length) || (inspectMaterial.script?.scenes && inspectMaterial.script.scenes.length) || inspectMaterial.scene_count || 0;
                  const isTargetEmpty = targetSc === 0;
                  return (
                    <>
                      <button
                        className="btn btn-sm"
                        disabled={isTargetEmpty || actionLoadingKey === `research::${inspectMaterial.channel_id}::${inspectMaterial.material_id || inspectMaterial.id}`}
                        onClick={() => {
                          const target = inspectMaterial;
                          handleResearchSingle(target);
                        }}
                        style={{
                          background: inspectMaterial.researched
                            ? "rgba(14, 165, 233, 0.15)"
                            : "linear-gradient(135deg, #0ea5e9, #0284c7)",
                          border: inspectMaterial.researched ? "1px solid rgba(14, 165, 233, 0.4)" : "none",
                          color: inspectMaterial.researched ? "#38bdf8" : "#fff",
                          cursor: isTargetEmpty ? "not-allowed" : "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4
                        }}
                        title="Tarihi NTSB fotoğrafları, 1080p B-roll ve telemetri grafikleri araştırıp doğrular"
                      >
                        <Search size={12} /> {inspectMaterial.researched ? "Yeniden Araştır" : "Araştır"}
                      </button>
                      <button
                        className="btn btn-primary btn-sm"
                        disabled={isTargetEmpty}
                        onClick={() => {
                          const target = inspectMaterial;
                          setInspectMaterial(null);
                          handleProduceSingle(target, false);
                        }}
                        style={{
                          background: isTargetEmpty ? "var(--bg-secondary)" : "linear-gradient(135deg, #06b6d4, #3b82f6)",
                          border: "none",
                          cursor: isTargetEmpty ? "not-allowed" : "pointer",
                          color: isTargetEmpty ? "var(--text-muted)" : "#fff"
                        }}
                        title={isTargetEmpty ? "Senaryo sahneleri boş olduğu için üretilemez" : "Lokal render"}
                      >
                        <Play size={12} fill="currentColor" /> Lokal Üret
                      </button>
                      <button
                        className="btn btn-sm"
                        disabled={isTargetEmpty}
                        onClick={() => {
                          const target = inspectMaterial;
                          setInspectMaterial(null);
                          handleProduceSingle(target, true);
                        }}
                        style={{
                          background: isTargetEmpty ? "var(--bg-secondary)" : "linear-gradient(135deg, #8b5cf6, #6366f1)",
                          border: "none",
                          cursor: isTargetEmpty ? "not-allowed" : "pointer",
                          color: isTargetEmpty ? "var(--text-muted)" : "#fff"
                        }}
                        title={isTargetEmpty ? "Senaryo sahneleri boş olduğu için üretilemez" : "Oracle Cloud bulut render"}
                      >
                        <Server size={12} /> Bulut Üret
                      </button>
                    </>
                  );
                })()}
              </div>

              <button className="btn btn-ghost btn-sm" onClick={() => setInspectMaterial(null)}>
                Kapat
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   VIDEOS PAGE
   ══════════════════════════════════════════════════════════════════ */

function VideosPage() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("active");
  const [patchModalVideo, setPatchModalVideo] = useState(null);

  const fetchVideos = useCallback(async () => {
    setLoading(true);
    try { const r = await fetch("/api/output"); if (r.ok) setVideos(await r.json()); } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchVideos(); }, [fetchVideos]);

  const handleArchive = async (folder, isCurrentlyArchived) => {
    try {
      const r = await fetch(`/api/output/${folder}/archive`, { method: isCurrentlyArchived ? "DELETE" : "POST" });
      if (r.ok) fetchVideos();
    } catch {}
  };

  const filtered = videos.filter(v => {
    if (filter === "shorts") return v.shorts_mode;
    if (filter === "archived") return v.archived;
    if (filter === "active") return !v.archived;
    return true;
  });

  return (
    <div>
      <div style={{ marginBottom: 24, display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Üretilen Videolar</h2>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 5 }}>YouTube Studio'ya tek tıkla gönder · Metadata kopyala · Arşivle</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={fetchVideos}>↻ Yenile</button>
      </div>

      <div className="card" style={{
        padding: "12px 16px", marginBottom: 20,
        background: "rgba(124,110,242,0.07)", border: "1px solid rgba(124,110,242,0.18)",
        display: "flex", alignItems: "flex-start", gap: 12,
      }}>
        <span style={{ fontSize: 20, flexShrink: 0 }}>🔌</span>
        <div>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)", marginBottom: 3 }}>Chrome Extension ile Otomatik Doldurma</div>
          <div style={{ fontSize: 11.5, color: "var(--text-muted)", lineHeight: 1.6 }}>
            <code style={{ fontSize: 10.5, background: "var(--bg-primary)", padding: "1px 5px", borderRadius: 3 }}>chrome://extensions</code>
            {" → Load unpacked → "}
            <code style={{ fontSize: 10.5, background: "var(--bg-primary)", padding: "1px 5px", borderRadius: 3 }}>extension/</code>
            {" klasörünü seç → \"Studio'ya Gönder\" butonuna bas — başlık/açıklama/etiketler otomatik dolar."}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
        {[
          { id: "active",   label: `Aktif (${videos.filter(v => !v.archived).length})` },
          { id: "all",      label: `Tümü (${videos.length})` },
          { id: "shorts",   label: `📱 Shorts (${videos.filter(v => v.shorts_mode).length})` },
          { id: "archived", label: `Arşiv (${videos.filter(v => v.archived).length})` },
        ].map(tab => (
          <button key={tab.id} className={`btn btn-sm ${filter === tab.id ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setFilter(tab.id)} style={{ fontSize: 12 }}>{tab.label}</button>
        ))}
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>Yükleniyor…</div>
      ) : filtered.length === 0 ? (
        <div className="card" style={{ padding: "40px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 12, opacity: 0.3 }}>🎬</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>Video Yok</div>
          <div style={{ fontSize: 13, color: "var(--text-muted)" }}>Henüz video üretilmedi veya filtre sonuç vermedi.</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {filtered.map(v => (
            <VideoCard
              key={v.folder}
              video={v}
              onArchive={handleArchive}
              onOpenPatcher={(vid) => setPatchModalVideo(vid)}
            />
          ))}
        </div>
      )}

      {patchModalVideo && (
        <VideoScenePatcherModal
          isOpen={!!patchModalVideo}
          video={patchModalVideo}
          onClose={() => setPatchModalVideo(null)}
          onPatched={fetchVideos}
        />
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   DASHBOARD PAGE
   ══════════════════════════════════════════════════════════════════ */

function DashboardPage({
  channels,
  groups,
  logs,
  selectedChannelId,
  selectedGroupId,
  onSelectChannel,
  onSelectGroup,
  onEdit,
  onDelete,
  onRun,
  onReproduce,
  onStartShorts,
  onAddChannel,
  onToggleChannel,
  onToggleSocial,
  onRefreshLogs,
  onRecompose,
  onAddGroup,
  onEditGroup,
  onDeleteGroup,
  onProduceConnectome,
  runningTask,
  onNavigateMaterials,
}) {
  const selectedChannel = channels.find(c => c.channel_id === selectedChannelId);
  const selectedGroup = (groups || []).find(g => g.id === selectedGroupId);
  const activeCount = channels.filter(c => c.active).length;
  const totalVideos = channels.reduce((s, c) => s + (c.video_count || 0), 0);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 24, alignItems: "start" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 20, minWidth: 0 }}>
        {/* Stat Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
          {[
            { label: "Toplam Kanal", value: channels.length, meta: `${activeCount} aktif`, icon: Tv, color: "rgba(99,102,241,0.12)", iconColor: "var(--accent-primary)" },
            { label: "Toplam Video", value: totalVideos, meta: "tüm kanallar", icon: Film, color: "rgba(16,185,129,0.1)", iconColor: "var(--success)" },
            { label: "Kanal Grupları", value: (groups || []).length, meta: "ortak içerik planı", icon: Users, color: "rgba(168,85,247,0.12)", iconColor: "#c084fc" },
          ].map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={i} className="stat-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div className="stat-label">{s.label}</div>
                  <div className="stat-icon" style={{ background: s.color, color: s.iconColor }}>
                    <Icon size={16} />
                  </div>
                </div>
                <div className="stat-value">{s.value}</div>
                <div className="stat-meta">{s.meta}</div>
              </div>
            );
          })}
        </div>

        {selectedGroup ? (
          <div className="card-elevated" style={{ padding: 24 }}>
            <ErrorBoundary fallbackTitle="Kanal grubu yüklenirken bir sorun oluştu">
              <GroupDetail
                group={selectedGroup}
                channels={channels}
                onEdit={() => onEditGroup(selectedGroup)}
                onDelete={() => onDeleteGroup(selectedGroup.id)}
              />
            </ErrorBoundary>
          </div>
        ) : selectedChannel ? (
          <div className="card-elevated" style={{ padding: 24 }}>
            <ErrorBoundary fallbackTitle="Kanal detayları yüklenirken bir sorun oluştu">
              <ChannelDetail channel={selectedChannel}
                onEdit={() => onEdit(selectedChannel)}
                onDelete={() => onDelete(selectedChannel.channel_id)}
                onRun={onRun}
                onReproduce={onReproduce}
                onStartShorts={onStartShorts}
                onRecompose={onRecompose}
                onProduceConnectome={onProduceConnectome}
                runningTask={runningTask}
                onNavigateMaterials={onNavigateMaterials} />
            </ErrorBoundary>
          </div>
        ) : (
          <div className="card" style={{ padding: "48px 24px", textAlign: "center" }}>
            <div style={{
              width: 52, height: 52, borderRadius: "50%", background: "rgba(99,102,241,0.08)",
              display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px",
              color: "var(--text-muted)"
            }}>
              <Tv size={26} />
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
              Kanal veya Grup Seçilmedi
            </div>
            <div style={{ fontSize: 13, color: "var(--text-muted)", lineHeight: 1.6, maxWidth: 450, margin: "0 auto" }}>
              İçerik planını, konuları ve ayarları görüntülemek için sol menüden veya sağ panelden bir <strong>Kanal</strong> ya da <strong>Kanal Grubu</strong> seçin.
            </div>
          </div>
        )}

        {/* Logs */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Activity size={15} style={{ color: "var(--accent-primary)" }} />
                <span>Üretim Logları</span>
              </div>
              <div className="card-subtitle">Video üretim çıktıları</div>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={onRefreshLogs} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
              <RefreshCw size={12} /> Yenile
            </button>
          </div>
          <div style={{ padding: 14 }}>
            {logs.length === 0 ? (
              <div className="log-terminal" style={{ alignItems: "center", justifyContent: "center" }}>
                <span style={{ color: "var(--text-muted)" }}>Henüz log kaydı yok.</span>
              </div>
            ) : (
              <div className="log-terminal">
                {logs.map((l, i) => (
                  <div key={i} className="log-row">
                    <span className="log-time">[{l.date ? `${l.date.slice(4, 6)}-${l.date.slice(6, 8)}` : ""} {l.time}]</span>
                    <span className="log-channel">{l.channel_id}</span>
                    <span className="log-message truncate">{l.title}</span>
                    <span className={l.status === "✅" ? "log-status-ok" : "log-status-warn"} style={{ flexShrink: 0 }}>{l.status}</span>
                    {l.folder && (
                      <span style={{ color: "var(--text-muted)", fontSize: 10, flexShrink: 0, fontFamily: "monospace" }}>📁</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Column: Groups & Channels */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16, position: "sticky", top: 80 }}>
        
        {/* Groups Card */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Users size={15} style={{ color: "var(--accent-primary)" }} />
                <span>Kanal Grupları</span>
              </div>
              <div className="card-subtitle">{(groups || []).length} aktif grup</div>
            </div>
            <button className="btn btn-primary btn-sm" onClick={onAddGroup} style={{ fontSize: 11.5, display: "inline-flex", alignItems: "center", gap: 4 }}>
              <Plus size={12} /> Grup
            </button>
          </div>

          {(groups || []).length === 0 ? (
            <div style={{ padding: "16px", textAlign: "center", fontSize: 12, color: "var(--text-muted)" }}>
              Henüz oluşturulmuş bir grup yok. Aynı kategorideki kanalları birleştirerek çok dilli ortak üretim yapabilirsiniz.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: "10px 14px" }}>
              {(groups || []).map(g => {
                const memberChans = (g.channel_ids || []).map(cid => (channels || []).find(c => c.channel_id === cid)).filter(Boolean);
                const isSelected = selectedGroupId === g.id;
                return (
                  <div
                    key={g.id}
                    onClick={() => onSelectGroup(g.id)}
                    style={{
                      padding: "10px 12px",
                      background: isSelected ? "rgba(99, 102, 241, 0.18)" : "rgba(99, 102, 241, 0.06)",
                      border: isSelected ? "1.5px solid var(--accent-primary)" : "1px solid rgba(99, 102, 241, 0.2)",
                      borderRadius: "var(--radius-md)",
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                      cursor: "pointer",
                      transition: "all 0.15s ease"
                    }}
                    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "rgba(99, 102, 241, 0.12)"; }}
                    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "rgba(99, 102, 241, 0.06)"; }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: isSelected ? "var(--accent-primary)" : "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
                        <Users size={14} style={{ color: "var(--accent-primary)" }} />
                        <span>{g.name}</span>
                        {isSelected && <span style={{ fontSize: 10, padding: "1px 5px", borderRadius: 3, background: "var(--accent-primary)", color: "#fff" }}>Seçili</span>}
                      </div>
                      <div style={{ display: "flex", gap: 4 }} onClick={e => e.stopPropagation()}>
                        <button
                          className="btn btn-ghost btn-sm"
                          style={{ padding: "3px 6px", fontSize: 11 }}
                          onClick={() => onEditGroup(g)}
                          title="Grubu Düzenle"
                        >
                          <Edit3 size={11} />
                        </button>
                        <button
                          className="btn btn-ghost btn-sm"
                          style={{ padding: "3px 6px", fontSize: 11, color: "var(--danger)" }}
                          onClick={() => onDeleteGroup(g.id)}
                          title="Grubu Sil"
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                      <span style={{
                        fontSize: 10.5, padding: "2px 6px", borderRadius: 4,
                        background: "rgba(255,255,255,0.06)", color: "var(--text-secondary)"
                      }}>
                        📂 {g.topic_category}
                      </span>
                      {memberChans.map(mc => {
                        const lang = getLang(mc.language);
                        return (
                          <span
                            key={mc.channel_id}
                            style={{
                              fontSize: 10.5, padding: "2px 6px", borderRadius: 4,
                              background: "var(--accent-muted)", color: "var(--accent-primary)",
                              display: "inline-flex", alignItems: "center", gap: 4
                            }}
                            title={`${mc.name} (${mc.channel_id})`}
                          >
                            <span>{lang?.flag || "🌍"}</span>
                            <span>{(mc.language || "").toUpperCase()}</span>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Channel List */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Tv size={15} style={{ color: "var(--accent-primary)" }} />
                <span>Münferit Kanallar</span>
              </div>
              <div className="card-subtitle">{channels.length} kayıtlı</div>
            </div>
            <button className="btn btn-primary btn-sm" onClick={onAddChannel} style={{ fontSize: 11.5, display: "inline-flex", alignItems: "center", gap: 4 }}>
              <Plus size={12} /> Ekle
            </button>
          </div>
          {channels.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📺</div>
              <div className="empty-title">Kanal Yok</div>
              <div className="empty-desc">Başlamak için ilk kanalınızı ekleyin.</div>
            </div>
          ) : (
            <div style={{ padding: "8px 0" }}>
              {channels.map(ch => {
                const lang = getLang(ch.language);
                const isSelected = selectedChannelId === ch.channel_id;
                const memberGroup = (groups || []).find(g => (g.channel_ids || []).includes(ch.channel_id));

                return (
                  <div key={ch.channel_id}
                    onClick={() => onSelectChannel(ch.channel_id)}
                    style={{
                      display: "flex", alignItems: "center", gap: 12,
                      padding: "10px 16px", cursor: "pointer",
                      background: isSelected ? "var(--accent-muted)" : "transparent",
                      borderLeft: isSelected ? "3px solid var(--accent-primary)" : "3px solid transparent",
                      transition: "all 0.12s ease",
                    }}
                    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "rgba(255,255,255,0.025)"; }}
                    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
                  >
                    <span style={{ fontSize: 16, flexShrink: 0 }}>{lang?.flag || "🌍"}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 13, fontWeight: 500,
                        color: isSelected ? "var(--text-primary)" : "var(--text-secondary)",
                        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                        display: "flex", alignItems: "center", gap: 6
                      }}>
                        <span>{ch.name}</span>
                        {memberGroup && (
                          <span style={{
                            fontSize: 9.5, padding: "1px 5px", borderRadius: 3,
                            background: "rgba(99,102,241,0.2)", color: "#a5b4fc",
                            fontWeight: 600, flexShrink: 0
                          }}>
                            👥 {memberGroup.name}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                        <span style={{ fontFamily: "monospace" }}>{ch.channel_id}</span>
                        <span>•</span>
                        <span style={{ color: "var(--accent-primary)", opacity: 0.85, fontSize: 10.5 }}>{CATEGORY_LABELS[ch.topic_category] || ch.topic_category}</span>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 6, marginRight: 8 }} onClick={e => e.stopPropagation()}>
                      <span style={{ fontSize: 13, cursor: "default", opacity: 1 }} title="YouTube Aktif">🔴</span>
                      <span
                        onClick={() => onToggleSocial(ch.channel_id, "instagram", !ch.instagram)}
                        style={{ fontSize: 13, cursor: "pointer", opacity: ch.instagram ? 1 : 0.25, transition: "opacity 0.15s ease" }}
                        title={ch.instagram ? "Instagram Aktif" : "Instagram Pasif"}
                      >
                        📸
                      </span>
                      <span
                        onClick={() => onToggleSocial(ch.channel_id, "tiktok", !ch.tiktok)}
                        style={{ fontSize: 13, cursor: "pointer", opacity: ch.tiktok ? 1 : 0.25, transition: "opacity 0.15s ease" }}
                        title={ch.tiktok ? "TikTok Aktif" : "TikTok Pasif"}
                      >
                        🎵
                      </span>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}
                      onClick={e => e.stopPropagation()}>
                      <Toggle checked={ch.active} onChange={() => onToggleChannel(ch.channel_id, ch.active)} />
                      <span style={{ fontSize: 10.5, color: "var(--text-muted)", fontFamily: "monospace" }}>{ch.video_count || 0}v</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   ROOT APP
   ══════════════════════════════════════════════════════════════════ */

export default function App() {
  const [channels, setChannels] = useState([]);
  const [groups, setGroups] = useState([]);
  const [logs, setLogs] = useState([]);
  const [selectedChannelId, setSelectedChannelId] = useState(null);
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [activePage, setActivePage] = useState("dashboard");
  const [showAddModal, setShowAddModal] = useState(false);
  const [editChannel, setEditChannel] = useState(null);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editGroup, setEditGroup] = useState(null);
  const [isCasperTerminalOpen, setIsCasperTerminalOpen] = useState(false);
  const [casperSavedCount, setCasperSavedCount] = useState(0);
  const [runningTask, setRunningTask] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const urlExecId = params.get("exec_id");
    if (urlExecId) {
      const url = new URL(window.location);
      url.searchParams.delete("exec_id");
      window.history.replaceState({}, document.title, url.pathname + url.search);
      return { exec_id: urlExecId, status: "pending", message: "Gemini Web otomasyonundan başlatıldı..." };
    }
    return null;
  });

  const fetchChannels = async () => { try { const r = await fetch("/api/channels"); if (r.ok) setChannels(await r.json()); } catch {} };
  const fetchGroups = async () => { try { const r = await fetch("/api/groups"); if (r.ok) setGroups(await r.json()); } catch {} };
  const fetchLogs = async () => { try { const r = await fetch("/api/logs"); if (r.ok) setLogs(await r.json()); } catch {} };
  
  useEffect(() => { fetchChannels(); fetchGroups(); fetchLogs(); }, []);

  // ── Routine pending approvals polling ──────────────────────────
  const [pendingRoutines, setPendingRoutines] = useState([]);

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch("/api/routines/pending-approvals");
        if (r.ok) {
          const d = await r.json();
          setPendingRoutines(Array.isArray(d) ? d : (d.pending || []));
        }
      } catch {}
    };
    poll();
    const iv = setInterval(poll, 30000);
    return () => clearInterval(iv);
  }, []);

  const handleApproveRoutine = async (id, name) => {
    try {
      await fetch(`/api/routines/${id}/approve`, { method: "POST" });
      setPendingRoutines(p => p.filter(r => r.id !== id));
      if (name) setRunningTask({ status: "pending", message: `Rutin başlatıldı: ${name}` });
    } catch {}
  };

  const handleSnoozeRoutine = async (id) => {
    try {
      await fetch(`/api/routines/${id}/snooze`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ minutes: 15 }) });
      setPendingRoutines(p => p.filter(r => r.id !== id));
    } catch {}
  };

  const handleDismissRoutine = async (id) => {
    try {
      await fetch(`/api/routines/${id}/dismiss`, { method: "POST" });
      setPendingRoutines(p => p.filter(r => r.id !== id));
    } catch {}
  };

  const handleTriggerRoutine = async (id, name) => {
    setRunningTask({ channelId: id, status: "pending", message: `Rutin başlatılıyor: ${name}…` });
    try {
      const r = await fetch(`/api/routines/${id}/trigger`, { method: "POST" });
      if (r.ok) {
        const d = await r.json();
        setRunningTask(p => ({ ...p, exec_id: d.exec_id, message: `Rutin çalışıyor: ${name}` }));
      } else {
        const e = await r.json();
        setRunningTask({ status: "failed", message: e.detail || "Rutin başlatılamadı" });
        setTimeout(() => setRunningTask(null), 5000);
      }
    } catch {
      setRunningTask({ status: "failed", message: "Ağ hatası" });
      setTimeout(() => setRunningTask(null), 5000);
    }
  };



  useEffect(() => {
    if (!runningTask?.exec_id) return;
    const iv = setInterval(async () => {
      try {
        const r = await fetch(`/api/run/status/${runningTask.exec_id}`);
        if (r.ok) {
          const d = await r.json();
          setRunningTask(p => ({ ...p, status: d.status, message: d.message }));
          if (d.status === "success" || d.status === "failed" || d.status === "partial") {
            clearInterval(iv); fetchChannels(); fetchGroups(); fetchLogs();
            if (d.status === "success" && d.result) {
              const res = d.result;
              setTimeout(() => {
                const confirmUpload = window.confirm(
                  `"${res.title || 'Video'}" başarıyla üretildi!\n\nYouTube Studio'ya otomatik yüklemek istiyor musunuz?`
                );
                if (confirmUpload) {
                  const payload = {
                    title: res.title,
                    description: res.description,
                    tags: res.tags,
                    folder: res.folder,
                    video_path: res.video_path,
                    plan_id: res.plan_id || "",
                    language: res.language || "en",
                    timestamp: Date.now(),
                  };
                  window.postMessage({ type: "YT_STUDIO_SEND", payload }, "*");
                  window.open("https://studio.youtube.com", "_blank");
                }
              }, 500);
            }
            setTimeout(() => setRunningTask(null), 6000);
          }
        }
      } catch {}
    }, 2000);
    return () => clearInterval(iv);
  }, [runningTask]);

  const saveChannel = async (payload) => {
    const isEdit = !!editChannel;
    try {
      const r = await fetch(isEdit ? `/api/channels/${payload.channel_id}` : "/api/channels", {
        method: isEdit ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
      });
      if (r.ok) { fetchChannels(); fetchGroups(); setShowAddModal(false); setEditChannel(null); }
    } catch {}
  };

  const saveGroup = async (payload) => {
    const isEdit = !!payload.id;
    const url = isEdit ? `/api/groups/${payload.id}` : "/api/groups";
    const res = await fetch(url, {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: "Hata" }));
      throw new Error(data.detail || "Grup kaydedilemedi.");
    }
    fetchGroups();
    fetchChannels();
    setShowGroupModal(false);
    setEditGroup(null);
  };

  const deleteGroup = async (id) => {
    if (!window.confirm("Bu grubu silmek istediğinize emin misiniz? (Gruptaki kanallar silinmez, bağımsız hale gelir)")) return;
    try {
      const r = await fetch(`/api/groups/${id}`, { method: "DELETE" });
      if (r.ok) {
        fetchGroups();
        fetchChannels();
        if (selectedGroupId === id) setSelectedGroupId(null);
      }
    } catch {}
  };

  const toggleChannel = async (id, active) => {
    try {
      const r = await fetch(`/api/channels/${id}/toggle`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ active: !active }) });
      if (r.ok) fetchChannels();
    } catch {}
  };

  const handleToggleSocial = async (id, platform, value) => {
    try {
      const payload = {};
      payload[platform] = value;
      const r = await fetch(`/api/channels/${id}/social`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (r.ok) {
        fetchChannels();
      }
    } catch (e) {
      console.error("Sosyal medya ayarı değiştirilemedi:", e);
    }
  };

  const deleteChannel = async (id) => {
    if (!window.confirm("Bu kanalı silmek istediğinize emin misiniz?")) return;
    try {
      const r = await fetch(`/api/channels/${id}`, { method: "DELETE" });
      if (r.ok) { fetchChannels(); fetchGroups(); if (selectedChannelId === id) setSelectedChannelId(null); }
    } catch {}
  };

  const handleRun = async (channelId, loopCount = 1, loopDelay = 10) => {
    setRunningTask({ channelId, status: "pending", message: "Görev kuyruğa alınıyor…" });
    try {
      const r = await fetch(`/api/run/${channelId}?loop_count=${loopCount}&loop_delay=${loopDelay}`, { method: "POST" });
      if (r.ok) { const d = await r.json(); setRunningTask(p => ({ ...p, exec_id: d.exec_id })); }
      else { const e = await r.json(); setRunningTask({ channelId, status: "failed", message: e.detail || "Hata" }); setTimeout(() => setRunningTask(null), 5000); }
    } catch {
      setRunningTask({ channelId, status: "failed", message: "Ağ hatası" });
      setTimeout(() => setRunningTask(null), 5000);
    }
  };

  const handleReproduce = async (channelId, rowId) => {
    setRunningTask({ channelId, status: "pending", message: `Sıra #${rowId} tekrar üretiliyor…` });
    try {
      const r = await fetch(`/api/channels/${channelId}/plan/${rowId}/reproduce`, { method: "POST" });
      if (r.ok) {
        const d = await r.json();
        setRunningTask(p => ({ ...p, exec_id: d.exec_id }));
      } else {
        const e = await r.json();
        setRunningTask({ channelId, status: "failed", message: e.detail || "Hata" });
        setTimeout(() => setRunningTask(null), 5000);
      }
    } catch {
      setRunningTask({ channelId, status: "failed", message: "Ağ hatası" });
      setTimeout(() => setRunningTask(null), 5000);
    }
  };

  const handleRecompose = async (channelId, rowId) => {
    setRunningTask({ channelId, status: "pending", message: `Sıra #${rowId} montajı tekrarlanıyor (Recompose)…` });
    try {
      const r = await fetch(`/api/channels/${channelId}/plan/${rowId}/recompose`, { method: "POST" });
      if (r.ok) {
        const d = await r.json();
        setRunningTask(p => ({ ...p, exec_id: d.exec_id }));
      } else {
        const e = await r.json();
        setRunningTask({ channelId, status: "failed", message: e.detail || "Hata" });
        setTimeout(() => setRunningTask(null), 5000);
      }
    } catch {
      setRunningTask({ channelId, status: "failed", message: "Ağ hatası" });
      setTimeout(() => setRunningTask(null), 5000);
    }
  };

  const handleStartShorts = (chanId) => {
    if (chanId) {
      setSelectedChannelId(chanId);
      setSelectedGroupId(null);
    }
    setActivePage("shorts_creator");
  };

  const handleProduceConnectome = async (channelId, payload) => {
    setRunningTask({ channelId, status: "pending", message: "Sinek Beyni Biyo-AI Klip üretimi başlatılıyor…" });
    try {
      const r = await fetch(`/api/channels/${channelId}/produce-connectome`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (r.ok) {
        const d = await r.json();
        setRunningTask(p => ({ ...p, exec_id: d.exec_id }));
      } else {
        const e = await r.json();
        setRunningTask({ channelId, status: "failed", message: e.detail || "Hata" });
        setTimeout(() => setRunningTask(null), 5000);
      }
    } catch {
      setRunningTask({ channelId, status: "failed", message: "Ağ hatası" });
      setTimeout(() => setRunningTask(null), 5000);
    }
  };

  const activeCount = (channels || []).filter(c => c.active).length;

  return (
    <div className="app-bg">
      <div className="layout-shell">
        <aside className="sidebar">
          <div className="sidebar-logo">
            <div className="logo-mark">
              <Sparkles size={18} color="#fff" />
            </div>
            <div className="logo-text"><h1>Video Üretici</h1><p>AI Pipeline v3</p></div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-label">Menü</div>
            {NAV.map(item => {
              const Icon = item.icon;
              return (
                <button key={item.id}
                  className={`nav-item ${activePage === item.id ? "active" : ""}`}
                  onClick={() => setActivePage(item.id)}>
                  <Icon className="nav-icon" size={16} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>

          {/* Sidebar Kanal Grupları */}
          <div style={{ padding: "8px 12px 4px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 8px", marginBottom: 6 }}>
              <div className="sidebar-label" style={{ margin: 0 }}>Kanal Grupları</div>
              <button style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "2px 4px", borderRadius: 4, display: "inline-flex", alignItems: "center" }}
                onClick={() => { setEditGroup(null); setShowGroupModal(true); }} title="Yeni Grup Oluştur">
                <Plus size={14} />
              </button>
            </div>
          </div>
          <div className="sidebar-channels" style={{ maxHeight: 150, overflowY: "auto", marginBottom: 8 }}>
            {(groups || []).length === 0 ? (
              <div style={{ padding: "8px 10px", fontSize: 11.5, color: "var(--text-muted)" }}>Henüz grup yok.</div>
            ) : groups.map(g => {
              const isSelected = selectedGroupId === g.id;
              return (
                <div key={g.id}
                  className={`channel-nav-item ${isSelected ? "selected" : ""}`}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", paddingRight: 8, cursor: "pointer" }}
                  onClick={() => { setSelectedGroupId(g.id); setSelectedChannelId(null); setActivePage("dashboard"); }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, flex: 1 }}>
                    <Users size={13} style={{ color: "var(--accent-primary)", flexShrink: 0 }} />
                    <span className="channel-nav-name" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{g.name}</span>
                  </div>
                  <span style={{ fontSize: 10, padding: "1px 5px", borderRadius: 3, background: "rgba(99,102,241,0.2)", color: "#a5b4fc", fontWeight: 600 }}>
                    {(g.channel_ids || []).length}k
                  </span>
                </div>
              );
            })}
          </div>

          {/* Sidebar Kanallar */}
          <div style={{ padding: "8px 12px 4px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 8px", marginBottom: 6 }}>
              <div className="sidebar-label" style={{ margin: 0 }}>Kanallar</div>
              <button style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "2px 4px", borderRadius: 4, display: "inline-flex", alignItems: "center" }}
                onClick={() => { setEditChannel(null); setShowAddModal(true); }} title="Yeni Kanal Ekle">
                <Plus size={14} />
              </button>
            </div>
          </div>
          <div className="sidebar-channels">
            {channels.length === 0 ? (
              <div style={{ padding: "12px 10px", fontSize: 12, color: "var(--text-muted)" }}>Henüz kanal yok.</div>
            ) : channels.map(ch => {
              const isSelected = selectedChannelId === ch.channel_id;
              return (
                <div key={ch.channel_id}
                  className={`channel-nav-item ${isSelected ? "selected" : ""}`}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", paddingRight: 8, cursor: "pointer" }}
                  onClick={() => { setSelectedChannelId(ch.channel_id); setSelectedGroupId(null); setActivePage("dashboard"); }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, flex: 1 }}>
                    <StatusDot active={ch.active} />
                    <span className="channel-nav-name" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{ch.name}</span>
                  </div>
                  <div style={{ display: "flex", gap: 4, flexShrink: 0 }} onClick={e => e.stopPropagation()}>
                    <span style={{ fontSize: 11, cursor: "default", opacity: 1 }} title="YouTube Aktif">🔴</span>
                    <span
                      onClick={() => handleToggleSocial(ch.channel_id, "instagram", !ch.instagram)}
                      style={{ fontSize: 11, cursor: "pointer", opacity: ch.instagram ? 1 : 0.25, transition: "opacity 0.15s ease" }}
                      title={ch.instagram ? "Instagram Aktif" : "Instagram Pasif"}
                    >
                      📸
                    </span>
                    <span
                      onClick={() => handleToggleSocial(ch.channel_id, "tiktok", !ch.tiktok)}
                      style={{ fontSize: 11, cursor: "pointer", opacity: ch.tiktok ? 1 : 0.25, transition: "opacity 0.15s ease" }}
                      title={ch.tiktok ? "TikTok Aktif" : "TikTok Pasif"}
                    >
                      🎵
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="sidebar-footer">
            <span className={`status-badge ${activeCount > 0 ? "online" : "offline"}`}>
              {activeCount > 0 ? `${activeCount} kanal aktif` : "Pasif"}
            </span>
          </div>
        </aside>

        <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
          <header className="topbar">
            <div>
              <div className="topbar-title">
                {activePage === "dashboard" ? "Dashboard" : 
                 activePage === "automation" ? "Otomasyon & Bulut Kuyruk Merkezi" :
                 activePage === "materials" ? "Üretim Materyalleri Merkezi" :
                 activePage === "story_studio" ? "Hikaye & Masal Atölyesi" :
                 activePage === "kontrol_videos" ? "Kontroldeki Videolar" :
                 activePage === "server_render" ? "Bulut Sunucu Video Üretim Merkezi" :
                 activePage === "youtube_upload" ? "YouTube Yükleme Merkezi" :
                 activePage === "instagram_schedule" ? "Instagram Planlama" :
                 activePage === "video_voiceover" ? "Videoyu Klon Sesle Seslendir" :
                 activePage === "videos" ? "Videolar" : 
                 activePage === "shorts_creator" ? "Uzundan Shorts Türet" : 
                 activePage === "chat" ? "AI Sohbet" : 
                 activePage === "routines" ? "Rutinler" : "Ayarlar"}
              </div>
              <div className="topbar-subtitle">
                {activePage === "dashboard"
                  ? `${channels.length} kanal · ${groups.length} grup · ${channels.reduce((s, c) => s + (c.video_count || 0), 0)} video üretildi`
                  : activePage === "automation"
                  ? "Seçilen planları tek tıkla Oracle Cloud sunucusuna aktarın, Mac'inizi kapatın. Videolar sunucuda sırayla derlenir ve saklanır."
                  : activePage === "materials"
                  ? "Gemini tarafından oluşturulan video senaryoları, görsel istemleri ve tekli/kuyruk üretim yönetimi"
                  : activePage === "story_studio"
                  ? "Kullanıcı hikaye taslakları, Gemini ile senaryolaştırma ve partlara bölünmüş sinematik kod animasyonları"
                  : activePage === "kontrol_videos"
                  ? "Kanalların kontrol klasöründeki videoları inceleyin, önizleyin ve onaylayarak yüklenecek klasörüne aktarın."
                  : activePage === "server_render"
                  ? "Oracle Cloud aarch64 sunucusunda derlenen videolar ve yerel klasöre indirme"
                  : activePage === "youtube_upload"
                  ? "YouTube Data API doğrudan yükleyici ve ertesi güne akıllı zamanlama"
                  : activePage === "instagram_schedule"
                  ? "Instagram Reels içeriklerini seçtiğiniz tarihe planlayın"
                  : activePage === "video_voiceover"
                  ? "Bir video ve kayıtlı klon ses seçerek konuşmayı klon sesle yeniden üretin"
                  : activePage === "videos"
                  ? "Üretilen videoların listesi ve yönetimi"
                  : activePage === "shorts_creator"
                  ? "Uzun videolardan 3 veya 4 adet Shorts videosu türetin"
                  : activePage === "chat"
                  ? "AI asistanı ile zihin haritası ve içerik yönetimi"
                  : activePage === "routines"
                  ? "Zamanlanmış içerik üretim rutinleri ve onay yönetimi"
                  : "AI modeli ve API anahtarları"}
              </div>
            </div>
            <div className="topbar-actions" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="status-badge online">API Bağlı</span>

              {/* Casper Fikirleri Uygula Butonu */}
              <button
                className={`btn btn-sm ${casperSavedCount > 0 ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setIsCasperTerminalOpen(true)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 10,
                  fontSize: 12,
                  fontWeight: 600,
                  background: casperSavedCount > 0 ? "linear-gradient(135deg, #06b6d4, #6366f1)" : "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(99, 102, 241, 0.4)",
                  color: "#fff",
                  boxShadow: casperSavedCount > 0 ? "0 0 14px rgba(6, 182, 212, 0.45)" : "none",
                  cursor: "pointer",
                  transition: "all 0.2s ease"
                }}
                title="Casper AI'ın geliştirmelerini Gemini'ye uygulatmak için terminali aç"
              >
                <Sparkles size={13} className={casperSavedCount > 0 ? "animate-spin text-cyan-200" : "text-cyan-400"} />
                Fikirleri Uygula {casperSavedCount > 0 && `(${casperSavedCount})`}
              </button>

              {activePage === "dashboard" && (
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => { setEditGroup(null); setShowGroupModal(true); }} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                    <Users size={13} /> Yeni Grup
                  </button>
                  <button className="btn btn-primary btn-sm" onClick={() => { setEditChannel(null); setShowAddModal(true); }} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                    <Plus size={13} /> Yeni Kanal
                  </button>
                </div>
              )}
            </div>
          </header>

          <main className="main-content">
            <ErrorBoundary fallbackTitle="Sayfa yüklenirken bir sorun oluştu">
              {activePage === "settings" ? <SettingsPage /> :
               activePage === "automation" ? (
                 <AutomationPage
                   channels={channels}
                   groups={groups}
                   onNavigateServerRender={() => setActivePage("server_render")}
                 />
               ) :
               activePage === "materials" ? (
                 <MaterialsPage
                   channels={channels}
                   groups={groups}
                   selectedChannelId={selectedChannelId}
                   onSelectChannel={setSelectedChannelId}
                   onTriggerTask={setRunningTask}
                 />
               ) :
               activePage === "story_studio" ? (
                 <StoryStudioPage
                   channels={channels}
                   selectedChannelId={selectedChannelId}
                   onSelectChannel={setSelectedChannelId}
                 />
               ) :
               activePage === "kontrol_videos" ? (
                 <KontrolVideosPage
                   onNavigateUpload={() => setActivePage("youtube_upload")}
                 />
               ) :
               activePage === "server_render" ? (
                 <ServerRenderPage
                   channels={channels}
                   onNavigateUpload={() => setActivePage("youtube_upload")}
                 />
               ) :
               activePage === "youtube_upload" ? (
                 <YouTubeUploadPage
                   selectedChannelId={selectedChannelId}
                   channels={channels}
                   onSelectChannel={setSelectedChannelId}
                 />
               ) :
               activePage === "instagram_schedule" ? (
                 <InstagramSchedulePage channels={channels} selectedChannelId={selectedChannelId} />
               ) :
               activePage === "video_voiceover" ? <VideoVoiceClonePage /> :
               activePage === "videos"   ? <VideosPage /> :
               activePage === "shorts_creator" ? <ShortsCreatorPage selectedChannelId={selectedChannelId} channels={channels} onStartShorts={handleStartShorts} /> :
               activePage === "chat"     ? <ChatPage selectedChannelId={selectedChannelId} channels={channels} /> :
               activePage === "routines" ? <RoutinesPage channels={channels} onTriggerRoutine={handleTriggerRoutine} /> : (
                <DashboardPage
                  channels={channels}
                  groups={groups}
                  logs={logs}
                  selectedChannelId={selectedChannelId}
                  selectedGroupId={selectedGroupId}
                  onSelectChannel={id => {
                    setSelectedChannelId(prev => prev === id ? null : id);
                    setSelectedGroupId(null);
                  }}
                  onSelectGroup={id => {
                    setSelectedGroupId(prev => prev === id ? null : id);
                    setSelectedChannelId(null);
                  }}
                  onEdit={ch => { setEditChannel(ch); setShowAddModal(true); }}
                  onDelete={deleteChannel}
                  onRun={handleRun}
                  onReproduce={handleReproduce}
                  onStartShorts={handleStartShorts}
                  onAddChannel={() => { setEditChannel(null); setShowAddModal(true); }}
                  onToggleChannel={toggleChannel}
                  onToggleSocial={handleToggleSocial}
                  onRefreshLogs={fetchLogs}
                  onRecompose={handleRecompose}
                  onAddGroup={() => { setEditGroup(null); setShowGroupModal(true); }}
                  onEditGroup={g => { setEditGroup(g); setShowGroupModal(true); }}
                  onDeleteGroup={deleteGroup}
                  onProduceConnectome={handleProduceConnectome}
                  runningTask={runningTask}
                  onNavigateMaterials={id => {
                    setSelectedChannelId(id);
                    setActivePage("materials");
                  }}
                />
              )}
            </ErrorBoundary>
          </main>
        </div>
      </div>

      {/* Kanal Modal */}
      <Modal open={showAddModal} onClose={() => { setShowAddModal(false); setEditChannel(null); }}
        title={editChannel ? "Kanalı Düzenle" : "Yeni Kanal Ekle"}>
        <ChannelForm initial={editChannel} onSave={saveChannel}
          onClose={() => { setShowAddModal(false); setEditChannel(null); }} />
      </Modal>

      {/* Grup Modal */}
      <Modal open={showGroupModal} onClose={() => { setShowGroupModal(false); setEditGroup(null); }}
        title={editGroup ? "Kanal Grubunu Düzenle" : "Yeni Kanal Grubu Oluştur"}>
        <GroupForm initial={editGroup} channels={channels} onSave={saveGroup}
          onClose={() => { setShowGroupModal(false); setEditGroup(null); }} />
      </Modal>

      {runningTask && <TaskToast task={runningTask} onDismiss={() => setRunningTask(null)} />}

      {/* Rutin Onay Modalları */}
      {pendingRoutines.length > 0 && (
        <RoutineApprovalModal
          pendingRoutines={pendingRoutines}
          onApprove={(id, name) => handleApproveRoutine(id, name)}
          onSnooze={(id) => handleSnoozeRoutine(id)}
          onDismiss={(id) => handleDismissRoutine(id)}
        />
      )}

      {/* Casper AI Proaktif Asistan & Terminal */}
      <CasperCompanion
        onOpenTerminal={() => setIsCasperTerminalOpen(true)}
        savedCount={casperSavedCount}
        setSavedCount={setCasperSavedCount}
      />
      <CasperTerminalModal
        isOpen={isCasperTerminalOpen}
        onClose={() => setIsCasperTerminalOpen(false)}
        onIdeaApplied={() => setCasperSavedCount(0)}
      />
    </div>
  );
}
