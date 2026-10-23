import { useState } from "react";

const LANGUAGES = [
  { code: "tr", name: "Türkçe", flag: "🇹🇷" },
  { code: "en", name: "English", flag: "🇺🇸" },
  { code: "de", name: "Deutsch", flag: "🇩🇪" },
  { code: "fr", name: "Français", flag: "🇫🇷" },
  { code: "es", name: "Español", flag: "🇪🇸" },
  { code: "it", name: "Italiano", flag: "🇮🇹" },
  { code: "pt", name: "Português", flag: "🇧🇷" },
  { code: "ru", name: "Русский", flag: "🇷🇺" },
  { code: "ja", name: "日本語", flag: "🇯🇵" },
  { code: "ko", name: "한국어", flag: "🇰🇷" },
  { code: "zh", name: "中文", flag: "🇨🇳" },
  { code: "ar", name: "العربية", flag: "🇸🇦" },
  { code: "hi", name: "हिन्दी", flag: "🇮🇳" },
  { code: "nl", name: "Nederlands", flag: "🇳🇱" },
  { code: "pl", name: "Polski", flag: "🇵🇱" },
  { code: "sv", name: "Svenska", flag: "🇸🇪" },
  { code: "da", name: "Dansk", flag: "🇩🇰" },
  { code: "fi", name: "Suomi", flag: "🇫🇮" },
  { code: "no", name: "Norsk", flag: "🇳🇴" },
  { code: "cs", name: "Čeština", flag: "🇨🇿" },
  { code: "hu", name: "Magyar", flag: "🇭🇺" },
  { code: "ro", name: "Română", flag: "🇷🇴" },
  { code: "uk", name: "Українська", flag: "🇺🇦" },
  { code: "el", name: "Ελληνικά", flag: "🇬🇷" },
  { code: "id", name: "Indonesia", flag: "🇮🇩" },
  { code: "th", name: "ภาษาไทย", flag: "🇹🇭" },
  { code: "vi", name: "Tiếng Việt", flag: "🇻🇳" },
];

const TOPICS = ["space", "planets", "astronomy"];

const INITIAL_CHANNELS = [
  {
    id: "ch_uzay_tr", name: "Uzay Keşifleri TR",
    lang: "tr", topic: "space", hour: 9, active: true,
    videoCount: 14, lastRun: "2026-06-12 09:02", status: "success",
  },
  {
    id: "ch_space_en", name: "Space Discoveries EN",
    lang: "en", topic: "space", hour: 10, active: true,
    videoCount: 14, lastRun: "2026-06-12 10:01", status: "success",
  },
  {
    id: "ch_weltraum_de", name: "Weltraum Entdeckungen DE",
    lang: "de", topic: "astronomy", hour: 11, active: false,
    videoCount: 7, lastRun: "2026-06-09 11:00", status: "paused",
  },
];

const LOGS = [
  { time: "09:02", channel: "Uzay Keşifleri TR", title: "Kara Deliklerin Sırları", status: "✅", url: "#" },
  { time: "10:01", channel: "Space Discoveries EN", title: "James Webb's Greatest Discoveries", status: "✅", url: "#" },
  { time: "11:00", channel: "Weltraum DE", title: "-", status: "⏸", url: null },
];

function Badge({ color, children }) {
  const colors = {
    green: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    red: "bg-red-500/20 text-red-300 border-red-500/30",
    yellow: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
    blue: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    gray: "bg-slate-600/40 text-slate-400 border-slate-600/40",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${colors[color]}`}>
      {children}
    </span>
  );
}

function Modal({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,10,0.85)" }}>
      <div className="w-full max-w-lg rounded-2xl border border-slate-700 shadow-2xl overflow-hidden"
        style={{ background: "#0f1117" }}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/60">
          <span className="font-bold text-white text-lg">{title}</span>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">×</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

function ChannelCard({ ch, onToggle, onDelete, onEdit }) {
  const lang = LANGUAGES.find(l => l.code === ch.lang);
  return (
    <div className="rounded-xl border border-slate-700/60 p-5 flex flex-col gap-3 hover:border-indigo-500/40 transition-all"
      style={{ background: "#131720" }}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold text-white text-base leading-snug">{ch.name}</div>
          <div className="text-xs text-slate-500 mt-0.5 font-mono">{ch.id}</div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {ch.active ? <Badge color="green">Aktif</Badge> : <Badge color="gray">Pasif</Badge>}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-sm">
        <span className="text-slate-300">{lang?.flag} {lang?.name}</span>
        <span className="text-slate-500">·</span>
        <span className="text-slate-400 capitalize">{ch.topic}</span>
        <span className="text-slate-500">·</span>
        <span className="text-slate-400">⏰ {String(ch.hour).padStart(2,"0")}:00</span>
      </div>

      <div className="flex items-center gap-3 text-xs text-slate-500 border-t border-slate-700/40 pt-3 mt-1">
        <span>📹 {ch.videoCount} video</span>
        <span>🕐 {ch.lastRun || "—"}</span>
      </div>

      <div className="flex gap-2 mt-1">
        <button onClick={() => onToggle(ch.id)}
          className={`flex-1 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
            ch.active
              ? "border-yellow-500/40 text-yellow-400 hover:bg-yellow-500/10"
              : "border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
          }`}>
          {ch.active ? "⏸ Durdur" : "▶ Başlat"}
        </button>
        <button onClick={() => onEdit(ch)}
          className="flex-1 py-1.5 rounded-lg text-xs font-medium border border-indigo-500/40 text-indigo-400 hover:bg-indigo-500/10 transition-colors">
          ✏️ Düzenle
        </button>
        <button onClick={() => onDelete(ch.id)}
          className="py-1.5 px-3 rounded-lg text-xs font-medium border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors">
          🗑
        </button>
      </div>
    </div>
  );
}

function AddChannelForm({ initial, onSave, onClose }) {
  const [form, setForm] = useState(initial || {
    id: "", name: "", lang: "tr", topic: "space", hour: 9, active: true, videoCount: 0, lastRun: null,
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const label = "block text-xs text-slate-400 mb-1 font-medium";
  const inp = "w-full bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors";

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={label}>Kanal ID</label>
          <input className={inp} placeholder="ch_uzay_tr" value={form.id}
            onChange={e => set("id", e.target.value.toLowerCase().replace(/\s/g,"_"))} />
        </div>
        <div>
          <label className={label}>Kanal Adı</label>
          <input className={inp} placeholder="Uzay Keşifleri TR" value={form.name}
            onChange={e => set("name", e.target.value)} />
        </div>
      </div>

      <div>
        <label className={label}>Dil</label>
        <select className={inp} value={form.lang} onChange={e => set("lang", e.target.value)}>
          {LANGUAGES.map(l => (
            <option key={l.code} value={l.code}>{l.flag} {l.name}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={label}>Konu Kategorisi</label>
          <select className={inp} value={form.topic} onChange={e => set("topic", e.target.value)}>
            {TOPICS.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className={label}>Yayın Saati</label>
          <select className={inp} value={form.hour} onChange={e => set("hour", Number(e.target.value))}>
            {Array.from({length:24},(_,i)=>i).map(h => (
              <option key={h} value={h}>{String(h).padStart(2,"0")}:00</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-1">
        <button
          onClick={() => set("active", !form.active)}
          className={`w-10 h-5 rounded-full transition-colors relative ${form.active ? "bg-emerald-500" : "bg-slate-600"}`}>
          <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-all shadow ${form.active ? "left-5" : "left-0.5"}`}/>
        </button>
        <span className="text-sm text-slate-300">Aktif olarak başlat</span>
      </div>

      <div className="flex gap-2 pt-2 border-t border-slate-700/50 mt-1">
        <button onClick={onClose}
          className="flex-1 py-2 rounded-lg border border-slate-600 text-slate-400 hover:text-white text-sm transition-colors">
          İptal
        </button>
        <button
          onClick={() => { if(form.id && form.name) { onSave(form); onClose(); }}}
          className="flex-1 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors"
          disabled={!form.id || !form.name}>
          Kaydet
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [channels, setChannels] = useState(INITIAL_CHANNELS);
  const [logs] = useState(LOGS);
  const [showAdd, setShowAdd] = useState(false);
  const [editCh, setEditCh] = useState(null);
  const [tab, setTab] = useState("channels");

  const addChannel = (ch) => setChannels(prev => [...prev.filter(c=>c.id!==ch.id), ch]);
  const toggleChannel = (id) => setChannels(prev => prev.map(c => c.id===id ? {...c, active:!c.active} : c));
  const deleteChannel = (id) => setChannels(prev => prev.filter(c => c.id!==id));

  const active = channels.filter(c=>c.active).length;
  const total  = channels.reduce((s,c)=>s+c.videoCount, 0);

  return (
    <div className="min-h-screen text-white" style={{
      background: "linear-gradient(135deg, #07080f 0%, #0c0e1a 50%, #080c14 100%)",
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Stars bg */}
      <div className="fixed inset-0 pointer-events-none" style={{
        backgroundImage: "radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,0.15) 0%, transparent 100%), radial-gradient(1px 1px at 80% 10%, rgba(255,255,255,0.1) 0%, transparent 100%), radial-gradient(1px 1px at 60% 70%, rgba(255,255,255,0.08) 0%, transparent 100%)",
      }} />

      <div className="relative max-w-5xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-3xl">🛸</span>
            <h1 className="text-2xl font-bold" style={{
              background: "linear-gradient(90deg, #a78bfa, #60a5fa)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent"
            }}>
              YouTube Space Automation
            </h1>
          </div>
          <p className="text-slate-400 text-sm ml-12">Çoklu kanal · Çoklu dil · Günlük otomatik yayın</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { label: "Aktif Kanal", value: active, icon: "📺", color: "#a78bfa" },
            { label: "Toplam Video", value: total, icon: "🎬", color: "#60a5fa" },
            { label: "Desteklenen Dil", value: "27", icon: "🌍", color: "#34d399" },
          ].map(s => (
            <div key={s.label} className="rounded-xl border border-slate-700/50 px-5 py-4"
              style={{ background: "#131720" }}>
              <div className="text-2xl mb-1">{s.icon}</div>
              <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
              <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 p-1 rounded-xl border border-slate-700/40"
          style={{ background: "#0c0e18", width: "fit-content" }}>
          {[["channels","📺 Kanallar"], ["logs","📋 Log"], ["setup","⚙️ Kurulum"]].map(([t,label]) => (
            <button key={t} onClick={()=>setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                tab===t ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
              }`}>
              {label}
            </button>
          ))}
        </div>

        {/* CHANNELS TAB */}
        {tab === "channels" && (
          <div>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-white">Kanallar</h2>
              <button onClick={() => setShowAdd(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors">
                <span>+</span> Yeni Kanal
              </button>
            </div>

            {channels.length === 0 ? (
              <div className="text-center py-16 text-slate-500">
                <div className="text-4xl mb-3">🛸</div>
                <div>Henüz kanal eklenmedi.</div>
                <button onClick={() => setShowAdd(true)}
                  className="mt-4 px-5 py-2 rounded-xl bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 text-sm hover:bg-indigo-600/50 transition-colors">
                  İlk kanalı ekle
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {channels.map(ch => (
                  <ChannelCard key={ch.id} ch={ch}
                    onToggle={toggleChannel}
                    onDelete={deleteChannel}
                    onEdit={(c) => { setEditCh(c); setShowAdd(true); }} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* LOGS TAB */}
        {tab === "logs" && (
          <div>
            <h2 className="text-lg font-semibold text-white mb-5">Son Çalışma Logları</h2>
            <div className="rounded-xl border border-slate-700/50 overflow-hidden" style={{ background: "#131720" }}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50">
                    {["Saat","Kanal","Video Başlığı","Durum"].map(h=>(
                      <th key={h} className="text-left px-4 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {logs.map((l,i) => (
                    <tr key={i} className="border-b border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-slate-400 text-xs">{l.time}</td>
                      <td className="px-4 py-3 text-slate-300">{l.channel}</td>
                      <td className="px-4 py-3 text-white">{l.title}</td>
                      <td className="px-4 py-3">{l.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* SETUP TAB */}
        {tab === "setup" && (
          <div className="flex flex-col gap-5">
            <h2 className="text-lg font-semibold text-white">Kurulum Adımları</h2>
            {[
              {
                n:"1", title:"Anthropic API Anahtarı",
                desc:"console.anthropic.com → API Keys → Create Key",
                code:"export ANTHROPIC_API_KEY=sk-ant-xxx",
                badge:"Gerekli"
              },
              {
                n:"2", title:"NASA API Anahtarı (Ücretsiz)",
                desc:"api.nasa.gov → Generate API Key (anında, ücretsiz)",
                code:"export NASA_API_KEY=YOUR_NASA_KEY",
                badge:"Ücretsiz"
              },
              {
                n:"3", title:"YouTube Data API (Her Kanal İçin)",
                desc:"Google Cloud Console → APIs → YouTube Data API v3 → OAuth 2.0 Client → Desktop App → JSON İndir",
                code:"mv downloaded.json credentials/ch_001_client_secret.json",
                badge:"Her kanal"
              },
              {
                n:"4", title:"Bağımlılıkları Yükle",
                desc:"Python 3.11+ ve FFmpeg gerekli",
                code:"pip install -r requirements.txt\nsudo apt install ffmpeg",
                badge:"Tek seferlik"
              },
              {
                n:"5", title:"İlk Kanal Ekle & Token Al",
                desc:"Sihirbaz sizi yönlendirir, tarayıcıda Google'a giriş yapın",
                code:"cd src\npython main.py --setup\npython main.py --channel ch_001 --dry-run",
                badge:"Her kanal"
              },
              {
                n:"6", title:"GitHub Actions ile Otomatize Et",
                desc:"Secrets ekle, workflow dosyasını .github/workflows/ klasörüne kopyala",
                code:"cp github-actions/youtube_automation.yml .github/workflows/",
                badge:"Son adım"
              },
            ].map(step => (
              <div key={step.n} className="rounded-xl border border-slate-700/50 p-5" style={{ background:"#131720" }}>
                <div className="flex items-center gap-3 mb-2">
                  <span className="w-7 h-7 rounded-full bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 text-xs font-bold flex items-center justify-center">{step.n}</span>
                  <span className="font-semibold text-white">{step.title}</span>
                  <Badge color="blue">{step.badge}</Badge>
                </div>
                <p className="text-sm text-slate-400 mb-3 ml-10">{step.desc}</p>
                <pre className="ml-10 bg-slate-900/60 border border-slate-700/50 rounded-lg px-4 py-3 text-xs text-emerald-300 font-mono overflow-x-auto">
                  {step.code}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ADD/EDIT MODAL */}
      <Modal open={showAdd} onClose={() => { setShowAdd(false); setEditCh(null); }}
        title={editCh ? "Kanalı Düzenle" : "Yeni Kanal Ekle"}>
        <AddChannelForm
          initial={editCh}
          onSave={addChannel}
          onClose={() => { setShowAdd(false); setEditCh(null); }} />
      </Modal>
    </div>
  );
}
