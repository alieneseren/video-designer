import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Download, Loader2, Mic, RefreshCw, Volume2 } from "lucide-react";

export default function VideoVoiceClonePage() {
  const [videos, setVideos] = useState([]);
  const [clones, setClones] = useState([]);
  const [videoPath, setVideoPath] = useState("");
  const [uploadedVideoName, setUploadedVideoName] = useState("");
  const [cloneId, setCloneId] = useState("");
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [uploadingVideo, setUploadingVideo] = useState(false);
  const [error, setError] = useState("");

  const selectedClone = useMemo(
    () => clones.find(clone => clone.id === cloneId),
    [clones, cloneId]
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [videoResponse, cloneResponse] = await Promise.all([
        fetch("/api/output"),
        fetch("/api/voice-clones"),
      ]);
      const [videoData, cloneData] = await Promise.all([
        videoResponse.json(),
        cloneResponse.json(),
      ]);
      if (!videoResponse.ok) throw new Error(videoData.detail || "Videolar alınamadı.");
      if (!cloneResponse.ok) throw new Error(cloneData.detail || "Klon sesler alınamadı.");

      const availableVideos = (Array.isArray(videoData) ? videoData : [])
        .filter(video => video.video_path)
        .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
      const availableClones = (cloneData.clones || []).filter(clone => clone.voice_prompt_available);
      setVideos(availableVideos);
      setClones(availableClones);
      setVideoPath(current => current || availableVideos[0]?.video_path || "");
      setCloneId(current => availableClones.some(clone => clone.id === current)
        ? current
        : cloneData.active_id && availableClones.some(clone => clone.id === cloneData.active_id)
          ? cloneData.active_id
          : availableClones[0]?.id || "");
    } catch (fetchError) {
      setError(fetchError.message || "Veriler yüklenirken hata oluştu.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const uploadVideo = async event => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setUploadingVideo(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/api/video-voiceover/videos", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Video yüklenemedi.");
      setVideoPath(data.video_path);
      setUploadedVideoName(data.filename || file.name);
    } catch (uploadError) {
      setError(uploadError.message || "Video yüklenemedi.");
    } finally {
      setUploadingVideo(false);
    }
  };

  useEffect(() => {
    if (!jobId) return undefined;
    let active = true;
    const poll = async () => {
      try {
        const response = await fetch(`/api/video-voiceover/jobs/${encodeURIComponent(jobId)}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "İş durumu alınamadı.");
        if (!active) return;
        setJob(data);
        if (data.status === "completed" || data.status === "failed") setBusy(false);
      } catch (pollError) {
        if (active) {
          setError(pollError.message || "Seslendirme durumu alınamadı.");
          setBusy(false);
        }
      }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [jobId]);

  const applyVoice = async event => {
    event.preventDefault();
    if (!videoPath || !cloneId || busy) return;
    setBusy(true);
    setError("");
    setJob(null);
    setJobId("");
    try {
      const response = await fetch("/api/video-voiceover/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_path: videoPath, clone_id: cloneId }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Ses klonlama başlatılamadı.");
      setJobId(data.job_id);
    } catch (requestError) {
      setError(requestError.message || "Ses klonlama başlatılamadı.");
      setBusy(false);
    }
  };

  const resultVideoUrl = job?.result?.video_path
    ? `/api/video-voiceover/jobs/${encodeURIComponent(jobId)}/video`
    : "";
  const statusText = {
    queued: "Sırada",
    processing: job?.stage || "İşleniyor",
    completed: "Tamamlandı",
    failed: "Başarısız",
  };

  return (
    <div style={{ maxWidth: 1050, margin: "0 auto", display: "grid", gap: 18, paddingBottom: 40 }}>
      <section className="card" style={{ padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 18 }}>
          <div>
            <h2 style={{ margin: 0, color: "var(--text-primary)", fontSize: 20 }}>Videoyu Klon Sesle Seslendir</h2>
            <p style={{ color: "var(--text-muted)", fontSize: 12, lineHeight: 1.6, margin: "7px 0 0" }}>
              Bir video ve kayıtlı klon ses seçin. Konuşma otomatik çözümlenir, seçilen Chatterbox sesiyle yeniden üretilir ve yeni dosyaya eklenir. Orijinal video korunur.
            </p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={refresh} disabled={loading}>
            <RefreshCw size={14} /> Yenile
          </button>
        </div>

        <form onSubmit={applyVoice} style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14 }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Video</label>
            <select className="form-input" value={videoPath} onChange={event => {
              setVideoPath(event.target.value);
              setUploadedVideoName("");
            }} disabled={loading || busy || uploadingVideo}>
              <option value="">Video seçin</option>
              {videos.map(video => (
                <option key={video.video_path} value={video.video_path}>
                  {video.title || video.folder} · {video.channel_name || video.channel_id || "Video"}
                </option>
              ))}
            </select>
            <label
              className="btn btn-ghost btn-sm"
              style={{ display: "inline-flex", marginTop: 8, cursor: uploadingVideo || busy ? "not-allowed" : "pointer" }}
            >
              {uploadingVideo ? <><Loader2 size={14} className="spin" /> Video yükleniyor…</> : "Bilgisayarımdan video seç"}
              <input
                type="file"
                accept="video/mp4,video/quicktime,video/x-matroska,video/webm,video/x-msvideo,video/x-m4v,.mp4,.mov,.mkv,.webm,.avi,.m4v"
                onChange={uploadVideo}
                disabled={loading || busy || uploadingVideo}
                style={{ display: "none" }}
              />
            </label>
            {uploadedVideoName && (
              <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 6 }}>
                Seçilen dosya: {uploadedVideoName}
              </div>
            )}
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Klon ses</label>
            <select className="form-input" value={cloneId} onChange={event => setCloneId(event.target.value)} disabled={loading || busy}>
              <option value="">Klon ses seçin</option>
              {clones.map(clone => (
                <option key={clone.id} value={clone.id}>
                  {clone.name}{clone.is_active ? " · Aktif" : ""}
                </option>
              ))}
            </select>
          </div>
          <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "flex-end" }}>
            <button type="submit" className="btn btn-primary" disabled={loading || busy || !videoPath || !cloneId}>
              {busy ? <><Loader2 size={14} className="spin" /> Seslendiriliyor…</> : <><Volume2 size={14} /> Sesi Uygula</>}
            </button>
          </div>
        </form>

        {!loading && videos.length === 0 && (
          <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 14 }}>Listede video yoksa bilgisayarınızdan bir video seçebilirsiniz. Desteklenen biçimler: MP4, MOV, MKV, WebM, AVI ve M4V.</div>
        )}
        {!loading && clones.length === 0 && (
          <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 14 }}>Kullanılabilir klon ses bulunamadı. Önce Ayarlar içindeki Ses Klonlama Stüdyosu'ndan bir ses profili oluşturun.</div>
        )}
        <div style={{ color: "var(--text-muted)", fontSize: 11, lineHeight: 1.5, marginTop: 12 }}>
          Konuşma Whisper zamanlarıyla parçalara ayrılır; klon ses bu zamanlara ve mevcut altyazılara hizalanır. Gömülü altyazılar korunur; eşleşen SRT/ASS/VTT dosyaları da çıktının yanına kopyalanır. Video süresi ve görüntü değişmez.
        </div>
      </section>

      {error && (
        <div role="alert" className="card" style={{ padding: 14, display: "flex", gap: 8, alignItems: "center", color: "var(--danger)" }}>
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {job && (
        <section className="card" style={{ padding: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
            <div style={{ display: "flex", gap: 9, alignItems: "center", color: "var(--text-primary)", fontWeight: 650 }}>
              {job.status === "completed" ? <CheckCircle2 size={17} color="var(--success)" /> : job.status === "failed" ? <AlertCircle size={17} color="var(--danger)" /> : <Mic size={17} />}
              {statusText[job.status] || job.stage}
            </div>
            {job.status === "completed" && job.result && (
              <a className="btn btn-ghost btn-sm" href={resultVideoUrl} download>
                <Download size={14} /> Klon sesli videoyu indir
              </a>
            )}
          </div>
          <div style={{ height: 7, background: "var(--bg-secondary)", borderRadius: 99, margin: "14px 0 8px", overflow: "hidden" }}>
            <div style={{ width: `${job.progress || 0}%`, height: "100%", background: "var(--accent-primary)", transition: "width 0.3s ease" }} />
          </div>
          <div style={{ color: "var(--text-muted)", fontSize: 11 }}>{job.stage}{selectedClone ? ` · ${selectedClone.name}` : ""}</div>
          {job.error && <div style={{ color: "var(--danger)", fontSize: 12, marginTop: 10 }}>{job.error}</div>}
          {job.result?.transcript && (
            <details style={{ marginTop: 12 }}>
              <summary style={{ cursor: "pointer", color: "var(--text-secondary)", fontSize: 12 }}>Algılanan konuşmayı gör</summary>
              <p style={{ color: "var(--text-muted)", fontSize: 12, lineHeight: 1.6 }}>{job.result.transcript}</p>
            </details>
          )}
          {resultVideoUrl && (
            <video
              controls
              preload="metadata"
              src={resultVideoUrl}
              style={{ display: "block", width: "100%", maxHeight: 460, marginTop: 14, background: "#000", borderRadius: 8 }}
            />
          )}
        </section>
      )}
    </div>
  );
}
