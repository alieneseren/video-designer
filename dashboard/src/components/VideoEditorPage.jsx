import { useState, useEffect, useRef, useMemo } from "react";
import {
  Scissors,
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Music,
  Layers,
  Sparkles,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Search,
  Filter,
  Film,
  FastForward,
  Rewind,
  Split,
  Download,
  Type,
  Sliders,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Smartphone,
  Monitor,
  Grid,
  Wand2,
  Plus,
  Copy,
  Undo2,
  Redo2,
  Check,
  Settings,
  Folder,
  Video,
  Mic,
  Palette,
  Gauge,
  Zap,
  Square,
  Crosshair,
  Eye,
  EyeOff,
  Lock,
  Unlock,
  Radio,
  Headphones
} from "lucide-react";

export default function VideoEditorPage() {
  // Video & Project State
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedChannelFilter, setSelectedChannelFilter] = useState("all");

  // Player & Timeline State
  const videoRef = useRef(null);
  const bgmAudioRef = useRef(null); // Dedicated live synchronized BGM audio element
  const timelineRef = useRef(null);
  const isDraggingPlayhead = useRef(false);
  const isDraggingInHandle = useRef(false);
  const isDraggingOutHandle = useRef(false);

  const [videoKey, setVideoKey] = useState(Date.now());
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1.0);
  const [isMuted, setIsMuted] = useState(false);

  // In / Out Trim Markers
  const [inPoint, setInPoint] = useState(0);
  const [outPoint, setOutPoint] = useState(0);

  // Track Specific Adjustment States (Alt Kısım Ayarları)
  const [selectedTimelineTrack, setSelectedTimelineTrack] = useState("a2"); // Default to a2 so BGM controls are visible immediately!
  const [v1Visibility, setV1Visibility] = useState(true);
  const [v1Locked, setV1Locked] = useState(false);

  const [a1Muted, setA1Muted] = useState(false);
  const [a1Volume, setA1Volume] = useState(1.0); // 0.0 to 1.5

  const [a2Muted, setA2Muted] = useState(false);
  const [bgmVolume, setBgmVolume] = useState(0.12); // 0.0 to 0.35
  const [autoDucking, setAutoDucking] = useState(true);
  const [selectedTrackId, setSelectedTrackId] = useState("space_walk");
  const [muteOriginalVideoAudio, setMuteOriginalVideoAudio] = useState(false); // Helps isolate new BGM testing

  const [t1Visibility, setT1Visibility] = useState(true);

  // Clipchamp Canvas Overlays & Aspect Ratio
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [showSafeAreas, setShowSafeAreas] = useState(false);
  const [showGrid, setShowGrid] = useState(false);
  const [showVUMeter, setShowVUMeter] = useState(true);
  const [vuLevelLeft, setVuLevelLeft] = useState(0);
  const [vuLevelRight, setVuLevelRight] = useState(0);

  // Left Clipchamp Navigation Rail
  const [activeLeftTab, setActiveLeftTab] = useState("audio"); // Open audio by default
  const [isDrawerOpen, setIsDrawerOpen] = useState(true);

  // Timeline Navigation & Tracks
  const [timelineZoom, setTimelineZoom] = useState(1.0);
  const [magneticSnap, setMagneticSnap] = useState(true);
  const [markers, setMarkers] = useState([
    { time: 10.0, label: "Giriş Kancası", color: "#38bdf8" },
    { time: 35.0, label: "Ana Olay", color: "#818cf8" }
  ]);

  // Operation States
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Color Grading / Filters State
  const [filterPreset, setFilterPreset] = useState("none");
  const [filterBrightness, setFilterBrightness] = useState(0.0);
  const [filterContrast, setFilterContrast] = useState(1.0);
  const [filterSaturation, setFilterSaturation] = useState(1.0);
  const [filterVignette, setFilterVignette] = useState(false);

  // Speed State
  const [videoSpeed, setVideoSpeed] = useState(1.0);

  // BGM Catalog
  const [musicCatalog, setMusicCatalog] = useState([]);

  // Scene Replace Preset (AI Patch)
  const [replaceType, setReplaceType] = useState("TACTICAL_RADAR");
  const [replaceTitle, setReplaceTitle] = useState("");
  const [replaceDesc, setReplaceDesc] = useState("");

  // 1. Sync Volume & Mute with Video (A1 Voiceover track)
  useEffect(() => {
    if (videoRef.current) {
      if (isMuted || a1Muted || muteOriginalVideoAudio) {
        videoRef.current.volume = 0;
      } else {
        const effectiveVol = volume * a1Volume;
        videoRef.current.volume = Math.max(0, Math.min(1, effectiveVol));
      }
    }
  }, [volume, a1Volume, isMuted, a1Muted, muteOriginalVideoAudio]);

  // 2. LIVE BGM AUDIO CONTROLLER (A2 BGM Track Synchronization)
  useEffect(() => {
    if (bgmAudioRef.current) {
      if (isMuted || a2Muted || bgmVolume <= 0.005) {
        bgmAudioRef.current.muted = true;
        bgmAudioRef.current.volume = 0;
      } else {
        bgmAudioRef.current.muted = false;
        // Scale 0.02 - 0.35 to full audible desktop dynamic range (0.0 to 1.0)
        const audibleGain = Math.min(1.0, bgmVolume * 3.5);
        bgmAudioRef.current.volume = audibleGain * volume;
      }
    }
  }, [bgmVolume, a2Muted, volume, isMuted]);

  // 3. Update BGM Audio Source when selectedTrackId changes
  useEffect(() => {
    if (bgmAudioRef.current && selectedTrackId) {
      const wasPlaying = isPlaying;
      bgmAudioRef.current.src = `/api/video-patch/stream-audio?track_id=${encodeURIComponent(selectedTrackId)}`;
      bgmAudioRef.current.load();
      if (wasPlaying && !a2Muted && bgmVolume > 0.005) {
        if (videoRef.current) {
          bgmAudioRef.current.currentTime = videoRef.current.currentTime % 120;
        }
        bgmAudioRef.current.play().catch(() => {});
      }
    }
  }, [selectedTrackId]);

  // Live Stereo VU Meter animation
  useEffect(() => {
    let animId;
    if (isPlaying && showVUMeter) {
      const updateMeter = () => {
        const base = 0.55 + Math.sin(Date.now() / 90) * 0.25;
        const jitterL = Math.random() * 0.18;
        const jitterR = Math.random() * 0.18;
        setVuLevelLeft(Math.min(1.0, Math.max(0.05, base + jitterL)));
        setVuLevelRight(Math.min(1.0, Math.max(0.05, base + jitterR)));
        animId = requestAnimationFrame(updateMeter);
      };
      animId = requestAnimationFrame(updateMeter);
    } else {
      setVuLevelLeft(0.0);
      setVuLevelRight(0.0);
    }
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, showVUMeter]);

  // Fetch Videos
  const fetchVideos = async (preferredPath = null) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch("/api/video-patch/editable-videos");
      if (res.ok) {
        const data = await res.json();
        const list = data.videos || [];
        setVideos(list);

        const targetPath = preferredPath || (selectedVideo ? selectedVideo.video_path : null);
        if (targetPath) {
          const found = list.find((v) => v.video_path === targetPath);
          if (found) {
            setSelectedVideo(found);
          } else if (list.length > 0) {
            setSelectedVideo(list[0]);
          }
        } else if (list.length > 0) {
          setSelectedVideo(list[0]);
        }
      } else {
        setErrorMessage("Videolar yüklenemedi.");
      }
    } catch (err) {
      setErrorMessage("Bağlantı hatası: " + err.message);
    }
    setLoading(false);
  };

  // Fetch BGM Catalog
  const fetchMusicCatalog = async () => {
    try {
      const res = await fetch("/api/video-patch/music-catalog");
      if (res.ok) {
        const data = await res.json();
        setMusicCatalog(data.tracks || []);
        if (data.tracks && data.tracks.length > 0) {
          setSelectedTrackId(data.tracks[0].id);
        }
      }
    } catch (err) {
      console.error("Müzik kataloğu yüklenemedi:", err);
    }
  };

  useEffect(() => {
    fetchVideos();
    fetchMusicCatalog();
  }, []);

  // Update on Video Selection
  useEffect(() => {
    if (selectedVideo) {
      setCurrentTime(0);
      setInPoint(0);
      setOutPoint(selectedVideo.duration || 10);
      setIsPlaying(false);
      setStatusMessage(null);
      setErrorMessage(null);
      setFilterPreset("none");
      setFilterBrightness(0.0);
      setFilterContrast(1.0);
      setFilterSaturation(1.0);
      setFilterVignette(false);
      setVideoSpeed(1.0);
      setVideoKey(Date.now());
      if (bgmAudioRef.current) {
        bgmAudioRef.current.pause();
        bgmAudioRef.current.currentTime = 0;
      }
    }
  }, [selectedVideo?.video_path]);

  // Filtered Channels
  const channels = useMemo(() => {
    const set = new Set();
    videos.forEach((v) => {
      if (v.channel_id) set.add(v.channel_id);
    });
    return Array.from(set);
  }, [videos]);

  // Search & Channel Filter
  const filteredVideos = useMemo(() => {
    return videos.filter((v) => {
      const matchesChannel =
        selectedChannelFilter === "all" || v.channel_id === selectedChannelFilter;
      const matchesSearch =
        !searchQuery.trim() ||
        v.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        v.folder_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        v.channel_id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesChannel && matchesSearch;
    });
  }, [videos, selectedChannelFilter, searchQuery]);

  // SMPTE Timecode Formatter
  const formatSMPTE = (seconds) => {
    if (!seconds || isNaN(seconds)) return "00:00:00:00";
    const s = Math.floor(seconds);
    const m = Math.floor(s / 60);
    const h = Math.floor(m / 60);
    const remM = m % 60;
    const remS = s % 60;
    const frames = Math.floor((seconds - s) * 24);
    return `${String(h).padStart(2, "0")}:${String(remM).padStart(2, "0")}:${String(remS).padStart(2, "0")}:${String(frames).padStart(2, "0")}`;
  };

  const formatShortTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return "00:00";
    const s = Math.floor(seconds);
    const m = Math.floor(s / 60);
    const h = Math.floor(m / 60);
    const remM = m % 60;
    const remS = s % 60;
    if (h > 0) {
      return `${String(h).padStart(2, "0")}:${String(remM).padStart(2, "0")}:${String(remS).padStart(2, "0")}`;
    }
    return `${String(remM).padStart(2, "0")}:${String(remS).padStart(2, "0")}`;
  };

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (["input", "textarea"].includes(e.target.tagName.toLowerCase())) return;

      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.code === "KeyS" || e.code === "KeyC") {
        e.preventDefault();
        handleRazorSplit();
      } else if (e.code === "KeyI") {
        e.preventDefault();
        handleSetIn();
      } else if (e.code === "KeyO") {
        e.preventDefault();
        handleSetOut();
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        stepFrames(-1);
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        stepFrames(1);
      } else if (e.code === "KeyJ") {
        e.preventDefault();
        stepTime(-2.0);
      } else if (e.code === "KeyK") {
        e.preventDefault();
        if (videoRef.current) {
          videoRef.current.pause();
          if (bgmAudioRef.current) bgmAudioRef.current.pause();
          setIsPlaying(false);
        }
      } else if (e.code === "KeyL") {
        e.preventDefault();
        stepTime(2.0);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentTime, inPoint, outPoint, isPlaying, duration]);

  // Synchronized Player Actions (Video + Live BGM)
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      if (bgmAudioRef.current) bgmAudioRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      if (bgmAudioRef.current && !a2Muted && bgmVolume > 0.005) {
        if (bgmAudioRef.current.duration) {
          bgmAudioRef.current.currentTime = videoRef.current.currentTime % bgmAudioRef.current.duration;
        }
        bgmAudioRef.current.play().catch(() => {});
      }
      setIsPlaying(true);
    }
  };

  const stepTime = (delta) => {
    if (!videoRef.current) return;
    const newTime = Math.max(0, Math.min(duration || 9999, videoRef.current.currentTime + delta));
    videoRef.current.currentTime = newTime;
    setCurrentTime(newTime);
    if (bgmAudioRef.current && bgmAudioRef.current.duration) {
      bgmAudioRef.current.currentTime = newTime % bgmAudioRef.current.duration;
    }
  };

  const stepFrames = (frames) => {
    if (!videoRef.current) return;
    const delta = frames * (1 / 24);
    const newTime = Math.max(0, Math.min(duration || 9999, videoRef.current.currentTime + delta));
    videoRef.current.currentTime = newTime;
    setCurrentTime(newTime);
    if (bgmAudioRef.current && bgmAudioRef.current.duration) {
      bgmAudioRef.current.currentTime = newTime % bgmAudioRef.current.duration;
    }
  };

  const jumpTo = (time) => {
    if (!videoRef.current) return;
    const target = Math.max(0, Math.min(duration || 9999, time));
    videoRef.current.currentTime = target;
    setCurrentTime(target);
    if (bgmAudioRef.current && bgmAudioRef.current.duration) {
      bgmAudioRef.current.currentTime = target % bgmAudioRef.current.duration;
    }
  };

  const handleSetIn = () => {
    const t = Math.round(currentTime * 24) / 24;
    setInPoint(t);
    if (outPoint <= t) {
      setOutPoint(Math.min(duration, t + 3));
    }
    setStatusMessage(`Giriş [In] noktası ayarlandı: ${formatShortTime(t)}`);
  };

  const handleSetOut = () => {
    const t = Math.round(currentTime * 24) / 24;
    setOutPoint(t);
    if (inPoint >= t) {
      setInPoint(Math.max(0, t - 3));
    }
    setStatusMessage(`Çıkış [Out] noktası ayarlandı: ${formatShortTime(t)}`);
  };

  const handleAddMarker = () => {
    const newM = {
      time: currentTime,
      label: `İşaretçi @ ${formatShortTime(currentTime)}`,
      color: "#a855f7"
    };
    setMarkers((prev) => [...prev, newM].sort((a, b) => a.time - b.time));
    setStatusMessage(`İşaretçi eklendi: ${formatShortTime(currentTime)}`);
  };

  // Continuous Timeline Mouse Scrubbing
  const calculateTargetTime = (clientX) => {
    if (!timelineRef.current || !duration) return 0;
    const rect = timelineRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const pct = Math.max(0, Math.min(1, x / rect.width));
    let target = pct * duration;

    if (magneticSnap) {
      const snapThreshold = 1.2;
      if (Math.abs(target - inPoint) < snapThreshold) target = inPoint;
      else if (Math.abs(target - outPoint) < snapThreshold) target = outPoint;
      else {
        for (const m of markers) {
          if (Math.abs(target - m.time) < snapThreshold) {
            target = m.time;
            break;
          }
        }
      }
    }
    return Math.max(0, Math.min(duration, target));
  };

  const handleTimelineMouseDown = (e) => {
    if (isDraggingInHandle.current || isDraggingOutHandle.current) return;
    e.preventDefault();
    isDraggingPlayhead.current = true;
    const t = calculateTargetTime(e.clientX);
    jumpTo(t);

    const handleMouseMove = (ev) => {
      if (!isDraggingPlayhead.current) return;
      ev.preventDefault();
      const newT = calculateTargetTime(ev.clientX);
      jumpTo(newT);
    };

    const handleMouseUp = () => {
      isDraggingPlayhead.current = false;
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

  // Interactive Clip Trim Handles
  const handleInHandleMouseDown = (e) => {
    e.stopPropagation();
    e.preventDefault();
    isDraggingInHandle.current = true;

    const onMouseMove = (ev) => {
      if (!isDraggingInHandle.current || !timelineRef.current || !duration) return;
      const rect = timelineRef.current.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
      const newIn = Math.min(outPoint - 1.0, Math.max(0, pct * duration));
      const rounded = Math.round(newIn * 24) / 24;
      setInPoint(rounded);
      jumpTo(rounded);
    };

    const onMouseUp = () => {
      isDraggingInHandle.current = false;
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  };

  const handleOutHandleMouseDown = (e) => {
    e.stopPropagation();
    e.preventDefault();
    isDraggingOutHandle.current = true;

    const onMouseMove = (ev) => {
      if (!isDraggingOutHandle.current || !timelineRef.current || !duration) return;
      const rect = timelineRef.current.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
      const newOut = Math.max(inPoint + 1.0, Math.min(duration, pct * duration));
      const rounded = Math.round(newOut * 24) / 24;
      setOutPoint(rounded);
      jumpTo(rounded);
    };

    const onMouseUp = () => {
      isDraggingOutHandle.current = false;
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  };

  // Live CSS Filter String
  const computeVideoFilter = () => {
    let filters = [];
    if (filterBrightness !== 0) {
      filters.push(`brightness(${1 + filterBrightness})`);
    }
    if (filterContrast !== 1) {
      filters.push(`contrast(${filterContrast})`);
    }
    if (filterSaturation !== 1) {
      filters.push(`saturate(${filterSaturation})`);
    }

    if (filterPreset === "teal_orange") {
      filters.push("sepia(0.2) hue-rotate(180deg) saturate(1.3)");
    } else if (filterPreset === "tactical_cyan") {
      filters.push("hue-rotate(150deg) saturate(1.4) contrast(1.15)");
    } else if (filterPreset === "night_vision") {
      filters.push("sepia(1) hue-rotate(85deg) saturate(2.5) contrast(1.3)");
    } else if (filterPreset === "bw_noir") {
      filters.push("grayscale(1) contrast(1.4) brightness(0.95)");
    } else if (filterPreset === "retro_crt") {
      filters.push("contrast(1.2) saturate(1.1)");
    }

    return filters.join(" ") || "none";
  };

  // 1. KES & SİL
  const handleTrimOperation = async (mode) => {
    if (!selectedVideo) return;
    if (outPoint <= inPoint) {
      setErrorMessage("Çıkış noktası [Out], Giriş noktasından [In] büyük olmalıdır.");
      return;
    }
    setIsProcessing(true);
    setStatusMessage(mode === "keep_range" ? "Seçili aralık kırpılıyor..." : "Aralık silinip video birleştiriliyor...");
    setErrorMessage(null);

    try {
      const res = await fetch("/api/video-patch/trim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: selectedVideo.video_path,
          start_sec: inPoint,
          end_sec: outPoint,
          mode: mode
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMessage(`İşlem tamamlandı: ${data.message}`);
        setVideoKey(Date.now());
        fetchVideos(selectedVideo.video_path);
      } else {
        setErrorMessage(data.detail || data.message || "İşlem başarısız.");
      }
    } catch (err) {
      setErrorMessage("Hata: " + err.message);
    }
    setIsProcessing(false);
  };

  // 2. BIÇAKLA BÖLME
  const handleRazorSplit = async () => {
    if (!selectedVideo) return;
    if (currentTime <= 1.0 || currentTime >= (duration - 1.0)) {
      setErrorMessage("Bölme noktası videonun en başında veya en sonunda olamaz.");
      return;
    }
    setIsProcessing(true);
    setStatusMessage(`Klip ${formatShortTime(currentTime)} noktasından ikiye bölünüyor...`);
    setErrorMessage(null);

    try {
      const res = await fetch("/api/video-patch/split-razor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: selectedVideo.video_path,
          split_sec: currentTime
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMessage(`Klip bölündü: ${data.message}`);
        setVideoKey(Date.now());
        fetchVideos();
      } else {
        setErrorMessage(data.detail || data.message || "Bölme başarısız.");
      }
    } catch (err) {
      setErrorMessage("Bıçak hatası: " + err.message);
    }
    setIsProcessing(false);
  };

  // 3. FİLTRE VE RENK YAKMA
  const handleBurnColorGrade = async () => {
    if (!selectedVideo) return;
    setIsProcessing(true);
    setStatusMessage(`Seçilen filtre (${filterPreset}) videoya kalıcı olarak işleniyor...`);
    setErrorMessage(null);

    try {
      const res = await fetch("/api/video-patch/color-grade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: selectedVideo.video_path,
          preset: filterPreset,
          brightness: filterBrightness,
          contrast: filterContrast,
          saturation: filterSaturation,
          vignette: filterVignette
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMessage(`Filtre başarıyla uygulandı: ${data.message}`);
        setVideoKey(Date.now());
        fetchVideos(selectedVideo.video_path);
      } else {
        setErrorMessage(data.detail || data.message || "Filtre uygulanamadı.");
      }
    } catch (err) {
      setErrorMessage("Filtre hatası: " + err.message);
    }
    setIsProcessing(false);
  };

  // 4. HIZ DEĞİŞTİRME
  const handleApplySpeed = async (speed) => {
    if (!selectedVideo) return;
    setIsProcessing(true);
    setStatusMessage(`Video hızı ${speed}x olarak işleniyor...`);
    setErrorMessage(null);

    try {
      const res = await fetch("/api/video-patch/speed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: selectedVideo.video_path,
          speed: speed
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMessage(`Hız güncellendi: ${data.message}`);
        setVideoSpeed(speed);
        setVideoKey(Date.now());
        fetchVideos(selectedVideo.video_path);
      } else {
        setErrorMessage(data.detail || data.message || "Hızlandırma başarısız.");
      }
    } catch (err) {
      setErrorMessage("Hız hatası: " + err.message);
    }
    setIsProcessing(false);
  };

  // 5. FON MÜZİĞİNİ VİDEOYA YAZ / MİKLE (2 SANİYEDE KALICI RENDER)
  const handleSwapBgm = async () => {
    if (!selectedVideo) return;
    setIsProcessing(true);
    setStatusMessage(`Atıf gerektirmeyen ${selectedTrackId} fon müziği videoya 2 saniyede miksleniyor...`);
    setErrorMessage(null);

    try {
      const res = await fetch("/api/video-patch/swap-bgm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: selectedVideo.video_path,
          track_id: selectedTrackId,
          volume: a2Muted ? 0.0 : bgmVolume
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMessage(`Müzik başarıyla videoya işlendi: ${data.message}`);
        setVideoKey(Date.now());
        fetchVideos(selectedVideo.video_path);
      } else {
        setErrorMessage(data.detail || data.message || "Müzik değiştirilemedi.");
      }
    } catch (err) {
      setErrorMessage("Hata: " + err.message);
    }
    setIsProcessing(false);
  };

  // 6. AI SAHNE YAMALAMA
  const handleReplaceScene = async () => {
    if (!selectedVideo) return;
    if (outPoint <= inPoint) {
      setErrorMessage("Geçerli bir giriş ve çıkış aralığı seçiniz.");
      return;
    }
    setIsProcessing(true);
    setStatusMessage(`${replaceType} sahnesi ${formatShortTime(inPoint)} - ${formatShortTime(outPoint)} aralığına yerleştiriliyor...`);
    setErrorMessage(null);

    try {
      const res = await fetch("/api/video-patch/apply-patch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: selectedVideo.video_path,
          patches: [
            {
              id: "patch_manual_" + Date.now(),
              start_sec: inPoint,
              end_sec: outPoint,
              start_time: formatShortTime(inPoint),
              end_time: formatShortTime(outPoint),
              duration: outPoint - inPoint,
              issue_title: replaceTitle || `${replaceType} Sahnesi`,
              replacement_type: replaceType,
              description: replaceDesc || "Clipchamp stüdyosundan yerleştirildi",
              enabled: true
            }
          ]
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMessage(`Sahne başarıyla yamalandı: ${data.message}`);
        setVideoKey(Date.now());
        fetchVideos(selectedVideo.video_path);
      } else {
        setErrorMessage(data.detail || data.message || "Sahne yamalama başarısız.");
      }
    } catch (err) {
      setErrorMessage("Hata: " + err.message);
    }
    setIsProcessing(false);
  };

  // 7. YEDEKTEN GERİ YÜKLE
  const handleRestoreBackup = async () => {
    if (!selectedVideo) return;
    if (!confirm("Orijinal yedek video geri yüklenecektir. Emin misiniz?")) return;

    setIsProcessing(true);
    setStatusMessage("Orijinal video yedeği geri yükleniyor...");
    setErrorMessage(null);

    try {
      const res = await fetch("/api/video-patch/restore-backup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_path: selectedVideo.video_path })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMessage("Orijinal video başarıyla geri yüklendi!");
        setVideoKey(Date.now());
        fetchVideos(selectedVideo.video_path);
      } else {
        setErrorMessage(data.detail || data.message || "Geri yükleme başarısız.");
      }
    } catch (err) {
      setErrorMessage("Hata: " + err.message);
    }
    setIsProcessing(false);
  };

  const inPct = duration ? (inPoint / duration) * 100 : 0;
  const outPct = duration ? (outPoint / duration) * 100 : 100;
  const currentPct = duration ? (currentTime / duration) * 100 : 0;

  // Aspect ratio calculations
  const canvasAspectRatio = aspectRatio === "9:16" ? "9 / 16" : aspectRatio === "1:1" ? "1 / 1" : "16 / 9";
  const canvasMaxWidth = aspectRatio === "9:16" ? "380px" : aspectRatio === "1:1" ? "480px" : "100%";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 75px)",
        background: "#090c15",
        color: "#e2e8f0",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
        overflow: "hidden"
      }}
    >
      {/* ══════════════════════════════════════════════════════════════════════════════
          1. CLIPCHAMP TOPBAR (Header & Global Actions)
          ══════════════════════════════════════════════════════════════════════════════ */}
      <header
        style={{
          height: 48,
          background: "#0f1422",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 16px",
          zIndex: 20
        }}
      >
        {/* Left: Branding & Title */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 2px 8px rgba(99,102,241,0.4)"
              }}
            >
              <Film size={15} color="#fff" />
            </div>
            <span style={{ fontSize: 14, fontWeight: 700, color: "#fff", letterSpacing: "-0.2px" }}>
              Clipchamp Studio
            </span>
          </div>

          <div style={{ height: 16, width: 1, background: "rgba(255,255,255,0.12)" }} />

          {selectedVideo && (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#cbd5e1", maxWidth: 320, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {selectedVideo.title}
              </span>
              <span
                style={{
                  fontSize: 10,
                  padding: "1px 6px",
                  borderRadius: 4,
                  background: "rgba(255,255,255,0.08)",
                  color: "#94a3b8"
                }}
              >
                {selectedVideo.duration_str}
              </span>
              <span
                style={{
                  fontSize: 10,
                  padding: "1px 6px",
                  borderRadius: 4,
                  background: "rgba(99,102,241,0.15)",
                  color: "#a5b4fc",
                  fontWeight: 600
                }}
              >
                1080p Full HD
              </span>
            </div>
          )}
        </div>

        {/* Right: Aspect Ratio Switcher, Backup & Export Button */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Aspect Ratio Selector Pill */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              background: "#161c2e",
              borderRadius: 7,
              padding: 2,
              border: "1px solid rgba(255,255,255,0.08)"
            }}
          >
            {[
              { id: "16:9", label: "16:9 Yatay", icon: Monitor },
              { id: "9:16", label: "9:16 Shorts", icon: Smartphone },
              { id: "1:1", label: "1:1 Kare", icon: Square }
            ].map((ar) => {
              const isSelected = aspectRatio === ar.id;
              const IconComp = ar.icon;
              return (
                <button
                  key={ar.id}
                  onClick={() => setAspectRatio(ar.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "4px 8px",
                    borderRadius: 5,
                    border: "none",
                    background: isSelected ? "#6366f1" : "transparent",
                    color: isSelected ? "#fff" : "#94a3b8",
                    fontSize: 11,
                    fontWeight: isSelected ? 700 : 500,
                    cursor: "pointer",
                    transition: "all 0.15s ease"
                  }}
                  title={`En-Boy Oranı: ${ar.label}`}
                >
                  <IconComp size={12} />
                  <span>{ar.id}</span>
                </button>
              );
            })}
          </div>

          {/* Restore Original Backup */}
          {selectedVideo && selectedVideo.has_backup && (
            <button
              onClick={handleRestoreBackup}
              disabled={isProcessing}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "6px 10px",
                borderRadius: 6,
                background: "rgba(244,63,94,0.12)",
                border: "1px solid rgba(244,63,94,0.3)",
                color: "#fda4af",
                fontSize: 11,
                fontWeight: 600,
                cursor: "pointer"
              }}
              title="Değişiklikleri geri alıp orijinal videoyu geri yükle"
            >
              <RotateCcw size={12} />
              Orijinale Dön
            </button>
          )}

          {/* Export MP4 Button */}
          {selectedVideo && (
            <a
              href={`/api/video-patch/stream?path=${encodeURIComponent(selectedVideo.video_path)}`}
              download={`${(selectedVideo.title || "video").replace(/[^a-zA-Z0-9_\-]/g, "_")}.mp4`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 14px",
                borderRadius: 7,
                background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                border: "none",
                color: "#fff",
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
                textDecoration: "none",
                boxShadow: "0 2px 10px rgba(99,102,241,0.4)"
              }}
              title="Düzenlenmiş videoyu 1080p MP4 olarak indir"
            >
              <Download size={13} />
              Dışa Aktar (MP4)
            </a>
          )}
        </div>
      </header>

      {/* ══════════════════════════════════════════════════════════════════════════════
          2. CLIPCHAMP BODY (Left Rail + Drawer + Canvas / Viewport)
          ══════════════════════════════════════════════════════════════════════════════ */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* ── LEFT VERTICAL ICON RAIL ─────────────────────────────────────────── */}
        <aside
          style={{
            width: 68,
            background: "#0c0f18",
            borderRight: "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "10px 0",
            gap: 6,
            zIndex: 10
          }}
        >
          {[
            { id: "audio", label: "Müzik", icon: Music },
            { id: "media", label: "Medyam", icon: Folder },
            { id: "filter", label: "Filtreler", icon: Palette },
            { id: "speed", label: "Hız", icon: Gauge },
            { id: "ai_patch", label: "AI Yama", icon: Sparkles },
            { id: "text", label: "Metin", icon: Type }
          ].map((item) => {
            const isActive = activeLeftTab === item.id && isDrawerOpen;
            const IconComp = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => {
                  if (activeLeftTab === item.id) {
                    setIsDrawerOpen(!isDrawerOpen);
                  } else {
                    setActiveLeftTab(item.id);
                    setIsDrawerOpen(true);
                  }
                }}
                style={{
                  width: 56,
                  height: 52,
                  borderRadius: 8,
                  border: "none",
                  background: isActive ? "rgba(99,102,241,0.18)" : "transparent",
                  color: isActive ? "#a5b4fc" : "#94a3b8",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 4,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  position: "relative"
                }}
                title={item.label}
              >
                {isActive && (
                  <div
                    style={{
                      position: "absolute",
                      left: 0,
                      top: 10,
                      bottom: 10,
                      width: 3,
                      background: "#6366f1",
                      borderRadius: "0 3px 3px 0"
                    }}
                  />
                )}
                <IconComp size={18} />
                <span style={{ fontSize: 9, fontWeight: 600 }}>{item.label}</span>
              </button>
            );
          })}
        </aside>

        {/* ── COLLAPSIBLE SECONDARY DRAWER ────────────────────────────────────── */}
        {isDrawerOpen && (
          <aside
            style={{
              width: 300,
              background: "#111625",
              borderRight: "1px solid rgba(255,255,255,0.08)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              animation: "slideIn 0.15s ease-out"
            }}
          >
            {/* Drawer Header */}
            <div
              style={{
                padding: "12px 14px",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between"
              }}
            >
              <span style={{ fontSize: 13, fontWeight: 700, color: "#fff" }}>
                {activeLeftTab === "audio" && "🎵 Telifsiz Fon Müziği"}
                {activeLeftTab === "media" && "📁 Medya Kitaplığı"}
                {activeLeftTab === "filter" && "🎨 Filtreler & Renk"}
                {activeLeftTab === "speed" && "⚡ Oynatma Hızı"}
                {activeLeftTab === "ai_patch" && "✨ AI Sahne Yamalama"}
                {activeLeftTab === "text" && "🔤 Metin & Altyazı"}
              </span>
              <button
                onClick={() => setIsDrawerOpen(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#64748b",
                  cursor: "pointer",
                  fontSize: 16,
                  padding: "0 4px"
                }}
                title="Paneli Kapat"
              >
                ×
              </button>
            </div>

            {/* Drawer Body Content */}
            <div style={{ flex: 1, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
              {/* TAB 1: AUDIO (BGM) */}
              {activeLeftTab === "audio" && (
                <>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 11, color: "#94a3b8" }}>Canlı Müzik Seçimi:</span>
                    <span style={{ fontSize: 10, color: "#34d399", fontWeight: 700, display: "flex", alignItems: "center", gap: 3 }}>
                      <Headphones size={11} /> Canlı Dinleme Aktif
                    </span>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 220, overflowY: "auto" }}>
                    {musicCatalog.map((track) => {
                      const isSelected = selectedTrackId === track.id;
                      return (
                        <div
                          key={track.id}
                          onClick={() => {
                            setSelectedTrackId(track.id);
                            setStatusMessage(`Çalan müzik değiştirildi: ${track.title}`);
                          }}
                          style={{
                            padding: 8,
                            borderRadius: 6,
                            background: isSelected ? "rgba(99,102,241,0.2)" : "#182032",
                            border: `1px solid ${isSelected ? "#6366f1" : "rgba(255,255,255,0.06)"}`,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between"
                          }}
                        >
                          <div>
                            <div style={{ fontSize: 11, fontWeight: 600, color: isSelected ? "#a5b4fc" : "#fff" }}>
                              {track.title}
                            </div>
                            <div style={{ fontSize: 10, color: "#64748b" }}>
                              {track.artist} · {track.mood}
                            </div>
                          </div>
                          {isSelected && <Check size={14} color="#a5b4fc" />}
                        </div>
                      );
                    })}
                  </div>

                  <div style={{ background: "#161b2a", padding: 10, borderRadius: 6, display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#94a3b8" }}>
                      <span>Fon Müziği Ses Düzeyi</span>
                      <strong style={{ color: "#a5b4fc" }}>{Math.round(bgmVolume * 100)}%</strong>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="0.35"
                      step="0.01"
                      value={a2Muted ? 0 : bgmVolume}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value);
                        setBgmVolume(val);
                        if (a2Muted && val > 0) setA2Muted(false);
                      }}
                      style={{ width: "100%", accentColor: "#6366f1" }}
                    />

                    <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "#cbd5e1", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={muteOriginalVideoAudio}
                        onChange={(e) => setMuteOriginalVideoAudio(e.target.checked)}
                        style={{ accentColor: "#6366f1" }}
                      />
                      Orijinal gömülü sesi sustur (Sadece yeni müziği dinle)
                    </label>

                    <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "#cbd5e1", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={autoDucking}
                        onChange={(e) => setAutoDucking(e.target.checked)}
                        style={{ accentColor: "#6366f1" }}
                      />
                      Dış ses algılandığında müziği kıs (Ducking)
                    </label>
                  </div>

                  <button
                    onClick={handleSwapBgm}
                    disabled={isProcessing}
                    style={{
                      padding: "10px",
                      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                      border: "none",
                      borderRadius: 6,
                      color: "#fff",
                      fontWeight: 700,
                      fontSize: 12,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                      boxShadow: "0 2px 8px rgba(99,102,241,0.4)"
                    }}
                  >
                    <Music size={14} />
                    Müziği Videoya Kalıcı Olarak Yaz (2s)
                  </button>
                </>
              )}

              {/* TAB 2: MEDIA */}
              {activeLeftTab === "media" && (
                <>
                  <div style={{ position: "relative" }}>
                    <Search size={13} style={{ position: "absolute", left: 8, top: 8, color: "#64748b" }} />
                    <input
                      type="text"
                      placeholder="Video ara..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "6px 8px 6px 26px",
                        background: "#182032",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: 6,
                        color: "#fff",
                        fontSize: 11
                      }}
                    />
                  </div>

                  <select
                    value={selectedChannelFilter}
                    onChange={(e) => setSelectedChannelFilter(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "5px 8px",
                      background: "#182032",
                      border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 6,
                      color: "#cbd5e1",
                      fontSize: 11
                    }}
                  >
                    <option value="all">Tüm Kanallar ({videos.length})</option>
                    {channels.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>

                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
                    {loading ? (
                      <div style={{ textAlign: "center", padding: 20, color: "#64748b", fontSize: 11 }}>
                        Klipler taranıyor...
                      </div>
                    ) : filteredVideos.length === 0 ? (
                      <div style={{ textAlign: "center", padding: 20, color: "#64748b", fontSize: 11 }}>
                        Video bulunamadı.
                      </div>
                    ) : (
                      filteredVideos.map((v) => {
                        const isSelected = selectedVideo && selectedVideo.video_path === v.video_path;
                        return (
                          <div
                            key={v.video_path}
                            onClick={() => setSelectedVideo(v)}
                            style={{
                              padding: 9,
                              borderRadius: 7,
                              background: isSelected ? "rgba(99,102,241,0.2)" : "#161b2a",
                              border: `1px solid ${isSelected ? "#6366f1" : "rgba(255,255,255,0.06)"}`,
                              cursor: "pointer",
                              transition: "all 0.15s ease"
                            }}
                          >
                            <div style={{ fontSize: 11, fontWeight: 600, color: isSelected ? "#a5b4fc" : "#e2e8f0", lineHeight: 1.3, marginBottom: 4 }}>
                              {v.title}
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, color: "#64748b" }}>
                              <span style={{ color: "#818cf8", fontWeight: 700 }}>{v.duration_str}</span>
                              <span>·</span>
                              <span>{v.size_mb} MB</span>
                              <span>·</span>
                              <span>{v.folder_name.split("_")[0]}</span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </>
              )}

              {/* TAB 3: FILTERS & LUTS */}
              {activeLeftTab === "filter" && (
                <>
                  <p style={{ fontSize: 11, color: "#94a3b8", margin: 0 }}>Sinematik Renk Filtreleri:</p>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                    {[
                      { id: "none", name: "Orijinal" },
                      { id: "teal_orange", name: "Teal & Orange" },
                      { id: "tactical_cyan", name: "Tactical Cyan" },
                      { id: "night_vision", name: "Night Vision" },
                      { id: "bw_noir", name: "B&W Noir" },
                      { id: "retro_crt", name: "Retro CRT" }
                    ].map((p) => (
                      <button
                        key={p.id}
                        onClick={() => setFilterPreset(p.id)}
                        style={{
                          padding: "8px 6px",
                          background: filterPreset === p.id ? "rgba(99,102,241,0.25)" : "#182032",
                          border: `1px solid ${filterPreset === p.id ? "#6366f1" : "rgba(255,255,255,0.08)"}`,
                          borderRadius: 6,
                          color: filterPreset === p.id ? "#a5b4fc" : "#cbd5e1",
                          fontSize: 11,
                          fontWeight: 600,
                          cursor: "pointer"
                        }}
                      >
                        {p.name}
                      </button>
                    ))}
                  </div>

                  <div style={{ background: "#161b2a", padding: 10, borderRadius: 6, display: "flex", flexDirection: "column", gap: 8 }}>
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#94a3b8" }}>
                        <span>Parlaklık</span>
                        <span>{Math.round(filterBrightness * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min="-0.4"
                        max="0.4"
                        step="0.05"
                        value={filterBrightness}
                        onChange={(e) => setFilterBrightness(parseFloat(e.target.value))}
                        style={{ width: "100%", accentColor: "#6366f1" }}
                      />
                    </div>
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#94a3b8" }}>
                        <span>Kontrast</span>
                        <span>{filterContrast.toFixed(2)}x</span>
                      </div>
                      <input
                        type="range"
                        min="0.6"
                        max="1.6"
                        step="0.05"
                        value={filterContrast}
                        onChange={(e) => setFilterContrast(parseFloat(e.target.value))}
                        style={{ width: "100%", accentColor: "#6366f1" }}
                      />
                    </div>
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#94a3b8" }}>
                        <span>Doygunluk</span>
                        <span>{filterSaturation.toFixed(2)}x</span>
                      </div>
                      <input
                        type="range"
                        min="0.0"
                        max="2.0"
                        step="0.1"
                        value={filterSaturation}
                        onChange={(e) => setFilterSaturation(parseFloat(e.target.value))}
                        style={{ width: "100%", accentColor: "#6366f1" }}
                      />
                    </div>
                    <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#cbd5e1", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={filterVignette}
                        onChange={(e) => setFilterVignette(e.target.checked)}
                        style={{ accentColor: "#6366f1" }}
                      />
                      Kenar Karartması (Vinyet)
                    </label>
                  </div>

                  <button
                    onClick={handleBurnColorGrade}
                    disabled={isProcessing}
                    style={{
                      padding: "9px",
                      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                      border: "none",
                      borderRadius: 6,
                      color: "#fff",
                      fontWeight: 700,
                      fontSize: 11,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6
                    }}
                  >
                    <Palette size={13} />
                    Filtreyi Kalıcı Uygula (Render)
                  </button>
                </>
              )}

              {/* TAB 4: SPEED */}
              {activeLeftTab === "speed" && (
                <>
                  <p style={{ fontSize: 11, color: "#94a3b8", margin: 0 }}>Oynatma Hızı Ayarları:</p>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
                    {[0.5, 0.75, 1.0, 1.25, 1.5, 2.0].map((s) => (
                      <button
                        key={s}
                        onClick={() => handleApplySpeed(s)}
                        disabled={isProcessing}
                        style={{
                          padding: "10px 4px",
                          background: videoSpeed === s ? "rgba(99,102,241,0.25)" : "#182032",
                          border: `1px solid ${videoSpeed === s ? "#6366f1" : "rgba(255,255,255,0.08)"}`,
                          borderRadius: 6,
                          color: videoSpeed === s ? "#a5b4fc" : "#cbd5e1",
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: "pointer"
                        }}
                      >
                        {s}x
                      </button>
                    ))}
                  </div>
                  <p style={{ fontSize: 10, color: "#64748b", lineHeight: 1.4, margin: "6px 0 0" }}>
                    💡 Ses tonu ve perdesi (pitch) bozulmadan FFmpeg <code>atempo</code> ve <code>setpts</code> ile işlenir.
                  </p>
                </>
              )}

              {/* TAB 5: AI PATCH */}
              {activeLeftTab === "ai_patch" && (
                <>
                  <label style={{ fontSize: 11, color: "#94a3b8" }}>Sahne Şablonu:</label>
                  <select
                    value={replaceType}
                    onChange={(e) => setReplaceType(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "6px 8px",
                      background: "#182032",
                      border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 6,
                      color: "#fff",
                      fontSize: 11
                    }}
                  >
                    <option value="TACTICAL_RADAR">Taktik Radar & HUD</option>
                    <option value="FLIGHT_SIM_COCKPIT">Simülatör Kokpit PFD</option>
                    <option value="STICKMAN_BREAKDOWN">Çöp Adam İnceleme</option>
                    <option value="MAINTENANCE_LOG">Kara Kutu Bakım Raporu</option>
                  </select>

                  <input
                    type="text"
                    placeholder="Başlık (Örn: ENGINE STALL)"
                    value={replaceTitle}
                    onChange={(e) => setReplaceTitle(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "6px 8px",
                      background: "#182032",
                      border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: 6,
                      color: "#fff",
                      fontSize: 11
                    }}
                  />

                  <button
                    onClick={handleReplaceScene}
                    disabled={isProcessing}
                    style={{
                      padding: "9px",
                      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                      border: "none",
                      borderRadius: 6,
                      color: "#fff",
                      fontWeight: 700,
                      fontSize: 11,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6
                    }}
                  >
                    <Sparkles size={13} />
                    Seçili Aralığa Sahne Bas ({formatShortTime(inPoint)} - {formatShortTime(outPoint)})
                  </button>
                </>
              )}

              {/* TAB 6: TEXT */}
              {activeLeftTab === "text" && (
                <div style={{ textAlign: "center", padding: "20px 10px", color: "#64748b", fontSize: 11 }}>
                  <Type size={32} style={{ opacity: 0.3, marginBottom: 8 }} />
                  <p style={{ margin: 0 }}>Altyazı ve metin katmanları otomatik timeline T1 izine bağlıdır.</p>
                </div>
              )}
            </div>
          </aside>
        )}

        {/* ── CENTER: CLIPCHAMP STAGE (CANVAS & PLAYER) ───────────────────────── */}
        <main
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            background: "#080b12"
          }}
        >
          {/* Canvas Viewport Area */}
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
              padding: 16,
              overflow: "hidden"
            }}
          >
            {selectedVideo ? (
              <div
                style={{
                  position: "relative",
                  maxWidth: canvasMaxWidth,
                  maxHeight: "100%",
                  aspectRatio: canvasAspectRatio,
                  boxShadow: "0 12px 40px rgba(0,0,0,0.8)",
                  borderRadius: 8,
                  overflow: "hidden",
                  background: "#000",
                  border: "1px solid rgba(255,255,255,0.12)",
                  transition: "aspect-ratio 0.2s ease, max-width 0.2s ease"
                }}
              >
                {/* HTML5 Video Element */}
                <video
                  key={`${selectedVideo.video_path}_${videoKey}`}
                  ref={videoRef}
                  src={`/api/video-patch/stream?path=${encodeURIComponent(selectedVideo.video_path)}&t=${videoKey}`}
                  onTimeUpdate={() => {
                    if (videoRef.current) {
                      setCurrentTime(videoRef.current.currentTime);
                      // Keep BGM in lockstep sync
                      if (bgmAudioRef.current && bgmAudioRef.current.duration && !bgmAudioRef.current.paused) {
                        const targetAudioTime = videoRef.current.currentTime % bgmAudioRef.current.duration;
                        if (Math.abs(bgmAudioRef.current.currentTime - targetAudioTime) > 0.4) {
                          bgmAudioRef.current.currentTime = targetAudioTime;
                        }
                      }
                    }
                  }}
                  onLoadedMetadata={() => {
                    if (videoRef.current) {
                      const d = videoRef.current.duration;
                      setDuration(d);
                      setOutPoint(d);
                    }
                  }}
                  onEnded={() => {
                    setIsPlaying(false);
                    if (bgmAudioRef.current) bgmAudioRef.current.pause();
                  }}
                  onPause={() => {
                    setIsPlaying(false);
                    if (bgmAudioRef.current) bgmAudioRef.current.pause();
                  }}
                  onPlay={() => {
                    setIsPlaying(true);
                    if (bgmAudioRef.current && !a2Muted && bgmVolume > 0.005) {
                      if (bgmAudioRef.current.duration) {
                        bgmAudioRef.current.currentTime = videoRef.current.currentTime % bgmAudioRef.current.duration;
                      }
                      bgmAudioRef.current.play().catch(() => {});
                    }
                  }}
                  style={{
                    width: "100%",
                    height: "100%",
                    display: "block",
                    objectFit: aspectRatio === "9:16" ? "cover" : "contain",
                    filter: computeVideoFilter(),
                    opacity: v1Visibility ? 1 : 0
                  }}
                />

                {/* Synchronized Background Music Audio Element */}
                <audio
                  ref={bgmAudioRef}
                  src={selectedTrackId ? `/api/video-patch/stream-audio?track_id=${encodeURIComponent(selectedTrackId)}` : ""}
                  loop
                  preload="auto"
                />

                {/* Processing Overlay */}
                {isProcessing && (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      background: "rgba(9,12,21,0.85)",
                      backdropFilter: "blur(4px)",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 10,
                      zIndex: 30
                    }}
                  >
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        border: "3px solid rgba(99,102,241,0.2)",
                        borderTop: "3px solid #6366f1",
                        borderRadius: "50%",
                        animation: "spin 0.8s linear infinite"
                      }}
                    />
                    <div style={{ color: "#a5b4fc", fontSize: 12, fontWeight: 700 }}>
                      {statusMessage || "İşleniyor..."}
                    </div>
                  </div>
                )}

                {/* Safe Areas Overlay */}
                {showSafeAreas && (
                  <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
                    <div style={{ position: "absolute", inset: "5%", border: "1px dashed rgba(99,102,241,0.4)", borderRadius: 4 }} />
                    <div style={{ position: "absolute", inset: "10%", border: "1px dashed rgba(168,85,247,0.4)", borderRadius: 4 }} />
                  </div>
                )}

                {/* 1/3 Rule Grid Overlay */}
                {showGrid && (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      pointerEvents: "none",
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr 1fr",
                      gridTemplateRows: "1fr 1fr 1fr"
                    }}
                  >
                    {[...Array(9)].map((_, i) => (
                      <div key={i} style={{ border: "1px solid rgba(255,255,255,0.12)" }} />
                    ))}
                  </div>
                )}

                {/* Vignette Preview Overlay */}
                {filterVignette && (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      pointerEvents: "none",
                      boxShadow: "inset 0 0 100px rgba(0,0,0,0.8)"
                    }}
                  />
                )}
              </div>
            ) : (
              <div style={{ textAlign: "center", color: "#64748b" }}>
                <Film size={48} style={{ opacity: 0.3, marginBottom: 10 }} />
                <p style={{ fontSize: 13 }}>Başlamak için sol kütüphaneden bir video seçin</p>
              </div>
            )}

            {/* Stereo Decibel Peak VU Meter */}
            {showVUMeter && selectedVideo && (
              <div
                style={{
                  position: "absolute",
                  right: 18,
                  top: "50%",
                  transform: "translateY(-50%)",
                  width: 22,
                  height: 160,
                  background: "rgba(15,20,34,0.85)",
                  backdropFilter: "blur(6px)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 6,
                  padding: "4px 3px",
                  display: "flex",
                  gap: 3,
                  boxShadow: "0 4px 14px rgba(0,0,0,0.5)"
                }}
                title="Stereo VU Meter"
              >
                <div style={{ flex: 1, background: "#182032", borderRadius: 2, overflow: "hidden", display: "flex", flexDirection: "column-reverse" }}>
                  <div
                    style={{
                      height: `${vuLevelLeft * 100}%`,
                      width: "100%",
                      background: "linear-gradient(to top, #10b981 60%, #eab308 85%, #ef4444 100%)",
                      transition: "height 0.08s ease"
                    }}
                  />
                </div>
                <div style={{ flex: 1, background: "#182032", borderRadius: 2, overflow: "hidden", display: "flex", flexDirection: "column-reverse" }}>
                  <div
                    style={{
                      height: `${vuLevelRight * 100}%`,
                      width: "100%",
                      background: "linear-gradient(to top, #10b981 60%, #eab308 85%, #ef4444 100%)",
                      transition: "height 0.08s ease"
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Quick Floating Transport Bar */}
          <div
            style={{
              height: 44,
              background: "#0d111d",
              borderTop: "1px solid rgba(255,255,255,0.06)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 18px"
            }}
          >
            {/* Left: SMPTE Timecode */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div
                style={{
                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
                  fontSize: 13,
                  fontWeight: 700,
                  color: "#a5b4fc",
                  background: "#141a2a",
                  padding: "3px 8px",
                  borderRadius: 5,
                  border: "1px solid rgba(99,102,241,0.3)"
                }}
              >
                {formatSMPTE(currentTime)}
              </div>
              <span style={{ fontSize: 11, color: "#64748b" }}>/ {formatShortTime(duration)}</span>
            </div>

            {/* Center: Play, Pause & Stepper */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                onClick={() => stepFrames(-1)}
                style={{ padding: "5px 7px", background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer" }}
                title="-1 Kare (←)"
              >
                <Rewind size={14} />
              </button>

              <button
                onClick={togglePlay}
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: isPlaying ? "#f43f5e" : "#6366f1",
                  border: "none",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  boxShadow: "0 2px 8px rgba(99,102,241,0.4)"
                }}
                title="Oynat / Duraklat (Space)"
              >
                {isPlaying ? <Pause size={14} /> : <Play size={14} fill="#fff" style={{ marginLeft: 2 }} />}
              </button>

              <button
                onClick={() => stepFrames(1)}
                style={{ padding: "5px 7px", background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer" }}
                title="+1 Kare (→)"
              >
                <FastForward size={14} />
              </button>
            </div>

            {/* Right: In/Out Buttons, Volume & Overlays */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <button
                onClick={handleSetIn}
                style={{
                  padding: "4px 8px",
                  borderRadius: 4,
                  background: "rgba(99,102,241,0.15)",
                  border: "1px solid rgba(99,102,241,0.3)",
                  color: "#a5b4fc",
                  fontSize: 10,
                  fontWeight: 700,
                  cursor: "pointer"
                }}
                title="Giriş Noktası Belirle (I)"
              >
                [In]
              </button>

              <button
                onClick={handleSetOut}
                style={{
                  padding: "4px 8px",
                  borderRadius: 4,
                  background: "rgba(99,102,241,0.15)",
                  border: "1px solid rgba(99,102,241,0.3)",
                  color: "#a5b4fc",
                  fontSize: 10,
                  fontWeight: 700,
                  cursor: "pointer"
                }}
                title="Çıkış Noktası Belirle (O)"
              >
                [Out]
              </button>

              <div style={{ height: 14, width: 1, background: "rgba(255,255,255,0.1)" }} />

              {/* Master Volume Slider */}
              <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  style={{ background: "transparent", border: "none", color: isMuted ? "#f43f5e" : "#94a3b8", cursor: "pointer", padding: 2 }}
                >
                  {isMuted || volume === 0 ? <VolumeX size={14} /> : <Volume2 size={14} />}
                </button>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={isMuted ? 0 : volume}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value);
                    setVolume(v);
                    if (isMuted && v > 0) setIsMuted(false);
                  }}
                  style={{ width: 50, height: 3, accentColor: "#6366f1", cursor: "pointer" }}
                  title={`Ana Ses: ${Math.round((isMuted ? 0 : volume) * 100)}%`}
                />
              </div>

              {/* Overlay Toggles */}
              <button
                onClick={() => setShowGrid(!showGrid)}
                style={{ background: "transparent", border: "none", color: showGrid ? "#6366f1" : "#64748b", cursor: "pointer", padding: 2 }}
                title="Izgara Aç / Kapat"
              >
                <Grid size={14} />
              </button>

              <button
                onClick={() => setShowSafeAreas(!showSafeAreas)}
                style={{ background: "transparent", border: "none", color: showSafeAreas ? "#6366f1" : "#64748b", cursor: "pointer", padding: 2 }}
                title="Safe Area Aç / Kapat"
              >
                <Crosshair size={14} />
              </button>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════════════════════════════════
              3. CLIPCHAMP TIMELINE (Action Bar + Quick Property Ribbon + Tracks)
              ══════════════════════════════════════════════════════════════════════════════ */}
          <div
            style={{
              height: 275,
              background: "#0a0d16",
              borderTop: "1px solid rgba(255,255,255,0.08)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden"
            }}
          >
            {/* Timeline Action Bar (Scissors, Trash, Snap, Zoom) */}
            <div
              style={{
                height: 32,
                background: "#0f1423",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 12px"
              }}
            >
              {/* Left Edit Tools: Split, Ripple Delete, Keep */}
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {/* Split Button */}
                <button
                  onClick={handleRazorSplit}
                  disabled={isProcessing}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "3px 8px",
                    borderRadius: 5,
                    background: "rgba(99,102,241,0.18)",
                    border: "1px solid rgba(99,102,241,0.4)",
                    color: "#a5b4fc",
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: "pointer"
                  }}
                  title="Playhead noktasından klibi ikiye böl (S / C)"
                >
                  <Scissors size={12} />
                  Böl (S)
                </button>

                {/* Ripple Delete (Sil & Birleştir) */}
                <button
                  onClick={() => handleTrimOperation("cut_segment")}
                  disabled={isProcessing}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "3px 8px",
                    borderRadius: 5,
                    background: "rgba(244,63,94,0.15)",
                    border: "1px solid rgba(244,63,94,0.35)",
                    color: "#fda4af",
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: "pointer"
                  }}
                  title="Seçili aralığı silip kalanları birleştir"
                >
                  <Trash2 size={12} />
                  Aralığı Sil
                </button>

                {/* Keep Range */}
                <button
                  onClick={() => handleTrimOperation("keep_range")}
                  disabled={isProcessing}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "3px 8px",
                    borderRadius: 5,
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    color: "#e2e8f0",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: "pointer"
                  }}
                  title="Sadece seçili aralığı sakla"
                >
                  Kırp (Sakla)
                </button>

                {/* Add Marker */}
                <button
                  onClick={handleAddMarker}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    padding: "3px 8px",
                    borderRadius: 5,
                    background: "transparent",
                    border: "none",
                    color: "#94a3b8",
                    fontSize: 11,
                    cursor: "pointer"
                  }}
                  title="İşaretçi ekle (M)"
                >
                  <Plus size={11} />
                  İşaretçi
                </button>
              </div>

              {/* Right: Magnet Snap & Zoom Slider */}
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <button
                  onClick={() => setMagneticSnap(!magneticSnap)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    padding: "2px 7px",
                    borderRadius: 5,
                    background: magneticSnap ? "rgba(99,102,241,0.15)" : "transparent",
                    border: `1px solid ${magneticSnap ? "#6366f1" : "rgba(255,255,255,0.08)"}`,
                    color: magneticSnap ? "#a5b4fc" : "#64748b",
                    fontSize: 10,
                    fontWeight: 600,
                    cursor: "pointer"
                  }}
                  title="Manyetik Kenetlenme"
                >
                  <Zap size={11} />
                  Snap
                </button>

                <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <ZoomOut size={11} color="#64748b" />
                  <input
                    type="range"
                    min="1"
                    max="4"
                    step="0.5"
                    value={timelineZoom}
                    onChange={(e) => setTimelineZoom(parseFloat(e.target.value))}
                    style={{ width: 60, height: 3, accentColor: "#6366f1", cursor: "pointer" }}
                  />
                  <ZoomIn size={11} color="#64748b" />
                </div>
              </div>
            </div>

            {/* ══════════════════════════════════════════════════════════════════════
                ✨ ALT KISIM HIZLI AYAR ŞERİDİ (QUICK PROPERTY ADJUSTMENT RIBBON)
                ══════════════════════════════════════════════════════════════════════ */}
            <div
              style={{
                height: 42,
                background: "#121829",
                borderBottom: "1px solid rgba(255,255,255,0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 12px",
                gap: 10
              }}
            >
              {/* Left: Active Track Selector Pill */}
              <div style={{ display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
                {[
                  { id: "a2", label: "🎵 A2 Müzik", color: "#c084fc" },
                  { id: "a1", label: "🎙️ A1 Dış Ses", color: "#34d399" },
                  { id: "v1", label: "🎬 V1 Görüntü", color: "#818cf8" },
                  { id: "t1", label: "🔤 T1 Metin", color: "#38bdf8" }
                ].map((t) => {
                  const isSel = selectedTimelineTrack === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setSelectedTimelineTrack(t.id)}
                      style={{
                        padding: "4px 8px",
                        borderRadius: 5,
                        border: isSel ? `1px solid ${t.color}` : "1px solid transparent",
                        background: isSel ? "rgba(255,255,255,0.1)" : "transparent",
                        color: isSel ? "#fff" : "#94a3b8",
                        fontSize: 10,
                        fontWeight: isSel ? 700 : 500,
                        cursor: "pointer",
                        transition: "all 0.15s ease"
                      }}
                    >
                      {t.label}
                    </button>
                  );
                })}
              </div>

              {/* Center: Contextual Quick Adjustments */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
                {/* 1. FON MÜZİĞİ (A2) DOĞRUDAN CANLI VE KALICI KONTROLÜ */}
                {selectedTimelineTrack === "a2" && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, width: "100%" }}>
                    {/* Track Picker */}
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{ fontSize: 10, color: "#94a3b8" }}>Parça:</span>
                      <select
                        value={selectedTrackId}
                        onChange={(e) => setSelectedTrackId(e.target.value)}
                        style={{
                          padding: "3px 6px",
                          borderRadius: 4,
                          background: "#1e293b",
                          border: "1px solid rgba(255,255,255,0.12)",
                          color: "#cbd5e1",
                          fontSize: 10,
                          maxWidth: 130
                        }}
                      >
                        {musicCatalog.map((t) => (
                          <option key={t.id} value={t.id}>{t.title} ({t.mood})</option>
                        ))}
                      </select>
                    </div>

                    {/* Live BGM Volume Slider */}
                    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <button
                        onClick={() => setA2Muted(!a2Muted)}
                        style={{ background: "transparent", border: "none", color: a2Muted ? "#f43f5e" : "#c084fc", cursor: "pointer", padding: 2 }}
                        title={a2Muted ? "Müziği Aç" : "Müziği Sustur"}
                      >
                        {a2Muted ? <VolumeX size={12} /> : <Volume2 size={12} />}
                      </button>
                      <input
                        type="range"
                        min="0.0"
                        max="0.35"
                        step="0.01"
                        value={a2Muted ? 0 : bgmVolume}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value);
                          setBgmVolume(val);
                          if (a2Muted && val > 0) setA2Muted(false);
                        }}
                        style={{ width: 65, height: 3, accentColor: "#c084fc", cursor: "pointer" }}
                        title={`Müzik Ses Düzeyi: ${Math.round(bgmVolume * 100)}%`}
                      />
                      <span style={{ fontSize: 10, color: "#c084fc", fontWeight: 700, minWidth: 26 }}>
                        {Math.round((a2Muted ? 0 : bgmVolume) * 100)}%
                      </span>
                    </div>

                    {/* Mute Baked Audio Toggle */}
                    <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: "#cbd5e1", cursor: "pointer" }} title="Videonun içine önceden kaydedilmiş sesi susturur, sadece yeni seçtiğiniz fon müziğini canlı çalar">
                      <input
                        type="checkbox"
                        checked={muteOriginalVideoAudio}
                        onChange={(e) => setMuteOriginalVideoAudio(e.target.checked)}
                        style={{ accentColor: "#c084fc" }}
                      />
                      Eski Sesi Sustur
                    </label>

                    {/* Ducking Toggle */}
                    <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: "#cbd5e1", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={autoDucking}
                        onChange={(e) => setAutoDucking(e.target.checked)}
                        style={{ accentColor: "#c084fc" }}
                      />
                      Ducking
                    </label>

                    {/* Burn BGM to MP4 Permanently */}
                    <button
                      onClick={handleSwapBgm}
                      disabled={isProcessing}
                      style={{
                        padding: "4px 10px",
                        borderRadius: 5,
                        background: "linear-gradient(135deg, #8b5cf6, #d946ef)",
                        border: "none",
                        color: "#fff",
                        fontSize: 10,
                        fontWeight: 700,
                        cursor: "pointer",
                        marginLeft: "auto",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        boxShadow: "0 2px 6px rgba(139,92,246,0.4)"
                      }}
                      title="Seçili fon müziğini ve ses seviyesini videoya kalıcı olarak işle (2 sn)"
                    >
                      <Music size={11} />
                      Videoya Kalıcı Olarak Yaz (2s)
                    </button>
                  </div>
                )}

                {/* 2. DIŞ SES (A1) AYARLARI */}
                {selectedTimelineTrack === "a1" && (
                  <div style={{ display: "flex", alignItems: "center", gap: 12, width: "100%" }}>
                    <button
                      onClick={() => setA1Muted(!a1Muted)}
                      style={{
                        padding: "3px 6px",
                        borderRadius: 4,
                        background: a1Muted ? "#f43f5e" : "#1e293b",
                        border: "none",
                        color: "#fff",
                        fontSize: 10,
                        fontWeight: 700,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: 4
                      }}
                    >
                      {a1Muted ? <VolumeX size={11} /> : <Volume2 size={11} />}
                      {a1Muted ? "Sessiz" : "Ses Açık"}
                    </button>

                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontSize: 10, color: "#94a3b8" }}>Dış Ses Düzeyi:</span>
                      <input
                        type="range"
                        min="0"
                        max="1.5"
                        step="0.05"
                        value={a1Muted ? 0 : a1Volume}
                        onChange={(e) => {
                          setA1Volume(parseFloat(e.target.value));
                          if (a1Muted) setA1Muted(false);
                        }}
                        style={{ width: 80, height: 3, accentColor: "#34d399", cursor: "pointer" }}
                      />
                      <span style={{ fontSize: 10, color: "#34d399", fontWeight: 700 }}>
                        {Math.round((a1Muted ? 0 : a1Volume) * 100)}%
                      </span>
                    </div>

                    <span style={{ fontSize: 10, color: "#64748b", marginLeft: "auto" }}>
                      🎙️ Anlatıcı Master Kanalı (48kHz Stereo)
                    </span>
                  </div>
                )}

                {/* 3. GÖRÜNTÜ (V1) AYARLARI */}
                {selectedTimelineTrack === "v1" && (
                  <div style={{ display: "flex", alignItems: "center", gap: 10, width: "100%" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{ fontSize: 10, color: "#94a3b8" }}>Hız:</span>
                      {[0.5, 1.0, 1.5, 2.0].map((s) => (
                        <button
                          key={s}
                          onClick={() => handleApplySpeed(s)}
                          disabled={isProcessing}
                          style={{
                            padding: "2px 6px",
                            borderRadius: 4,
                            background: videoSpeed === s ? "#6366f1" : "#1e293b",
                            border: "none",
                            color: "#fff",
                            fontSize: 10,
                            fontWeight: 700,
                            cursor: "pointer"
                          }}
                        >
                          {s}x
                        </button>
                      ))}
                    </div>

                    <div style={{ height: 14, width: 1, background: "rgba(255,255,255,0.1)" }} />

                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{ fontSize: 10, color: "#94a3b8" }}>Filtre:</span>
                      <select
                        value={filterPreset}
                        onChange={(e) => setFilterPreset(e.target.value)}
                        style={{
                          padding: "2px 6px",
                          borderRadius: 4,
                          background: "#1e293b",
                          border: "1px solid rgba(255,255,255,0.1)",
                          color: "#cbd5e1",
                          fontSize: 10
                        }}
                      >
                        <option value="none">Orijinal (Doğal)</option>
                        <option value="teal_orange">Teal & Orange</option>
                        <option value="tactical_cyan">Tactical Cyan</option>
                        <option value="night_vision">Night Vision</option>
                        <option value="bw_noir">B&W Noir</option>
                        <option value="retro_crt">Retro CRT</option>
                      </select>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{ fontSize: 10, color: "#94a3b8" }}>Parlaklık:</span>
                      <input
                        type="range"
                        min="-0.3"
                        max="0.3"
                        step="0.05"
                        value={filterBrightness}
                        onChange={(e) => setFilterBrightness(parseFloat(e.target.value))}
                        style={{ width: 45, height: 3, accentColor: "#6366f1" }}
                      />
                    </div>

                    <button
                      onClick={handleBurnColorGrade}
                      disabled={isProcessing}
                      style={{
                        padding: "3px 8px",
                        borderRadius: 4,
                        background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                        border: "none",
                        color: "#fff",
                        fontSize: 10,
                        fontWeight: 700,
                        cursor: "pointer",
                        marginLeft: "auto"
                      }}
                    >
                      Uygula (Render)
                    </button>
                  </div>
                )}

                {/* 4. METİN (T1) AYARLARI */}
                {selectedTimelineTrack === "t1" && (
                  <div style={{ display: "flex", alignItems: "center", gap: 12, width: "100%" }}>
                    <button
                      onClick={() => setT1Visibility(!t1Visibility)}
                      style={{
                        padding: "3px 6px",
                        borderRadius: 4,
                        background: t1Visibility ? "rgba(56,189,248,0.2)" : "#1e293b",
                        border: "none",
                        color: t1Visibility ? "#38bdf8" : "#64748b",
                        fontSize: 10,
                        fontWeight: 700,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: 4
                      }}
                    >
                      {t1Visibility ? <Eye size={11} /> : <EyeOff size={11} />}
                      Altyazı {t1Visibility ? "Açık" : "Kapalı"}
                    </button>

                    <span style={{ fontSize: 10, color: "#64748b" }}>
                      🔤 Dış sesle otomatik senkronize font şablonu (1080p Safe Area)
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Multi-Track Body */}
            <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
              {/* Left Track Headers (Labels & Quick Controls) */}
              <div
                style={{
                  width: 130,
                  background: "#0c101c",
                  borderRight: "1px solid rgba(255,255,255,0.08)",
                  display: "flex",
                  flexDirection: "column"
                }}
              >
                <div style={{ height: 20, borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "3px 8px", fontSize: 9, color: "#64748b", fontWeight: 700 }}>
                  İZ DENETİMLERİ
                </div>

                {/* Track 1: Text Header */}
                <div
                  onClick={() => setSelectedTimelineTrack("t1")}
                  style={{
                    height: 34,
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    padding: "0 8px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "#38bdf8",
                    background: selectedTimelineTrack === "t1" ? "rgba(56,189,248,0.12)" : "transparent",
                    cursor: "pointer"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <Type size={12} />
                    <span>T1 Metin</span>
                  </div>
                  <Eye
                    size={11}
                    color={t1Visibility ? "#38bdf8" : "#475569"}
                    onClick={(e) => {
                      e.stopPropagation();
                      setT1Visibility(!t1Visibility);
                    }}
                  />
                </div>

                {/* Track 2: Video Header */}
                <div
                  onClick={() => setSelectedTimelineTrack("v1")}
                  style={{
                    height: 44,
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    padding: "0 8px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "#a5b4fc",
                    background: selectedTimelineTrack === "v1" ? "rgba(99,102,241,0.15)" : "transparent",
                    cursor: "pointer"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <Video size={12} />
                    <span>V1 Video</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <Eye
                      size={11}
                      color={v1Visibility ? "#a5b4fc" : "#475569"}
                      onClick={(e) => {
                        e.stopPropagation();
                        setV1Visibility(!v1Visibility);
                      }}
                      title="Görüntüyü Gizle/Göster"
                    />
                    <Lock
                      size={11}
                      color={v1Locked ? "#f43f5e" : "#475569"}
                      onClick={(e) => {
                        e.stopPropagation();
                        setV1Locked(!v1Locked);
                      }}
                    />
                  </div>
                </div>

                {/* Track 3: Voiceover Header */}
                <div
                  onClick={() => setSelectedTimelineTrack("a1")}
                  style={{
                    height: 34,
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    padding: "0 8px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "#34d399",
                    background: selectedTimelineTrack === "a1" ? "rgba(52,211,153,0.12)" : "transparent",
                    cursor: "pointer"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <Mic size={12} />
                    <span>A1 Ses</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setA1Muted(!a1Muted);
                    }}
                    style={{ background: "transparent", border: "none", color: a1Muted ? "#f43f5e" : "#34d399", cursor: "pointer", padding: 0 }}
                  >
                    {a1Muted ? <VolumeX size={11} /> : <Volume2 size={11} />}
                  </button>
                </div>

                {/* Track 4: Music Header */}
                <div
                  onClick={() => setSelectedTimelineTrack("a2")}
                  style={{
                    flex: 1,
                    padding: "0 8px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "#c084fc",
                    background: selectedTimelineTrack === "a2" ? "rgba(192,132,252,0.12)" : "transparent",
                    cursor: "pointer"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <Music size={12} />
                    <span>A2 Müzik</span>
                  </div>
                  <span style={{ fontSize: 9, opacity: 0.8 }}>{Math.round(bgmVolume * 100)}%</span>
                </div>
              </div>

              {/* Right Tracks Container (Clips, Ruler, Playhead) */}
              <div
                ref={timelineRef}
                onMouseDown={handleTimelineMouseDown}
                style={{
                  flex: 1,
                  position: "relative",
                  overflowX: "auto",
                  overflowY: "hidden",
                  cursor: "crosshair",
                  background: "#080b12",
                  userSelect: "none"
                }}
              >
                {/* Time Ruler (Seconds) */}
                <div
                  style={{
                    height: 20,
                    background: "#0e1320",
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                    position: "relative"
                  }}
                >
                  {duration > 0 &&
                    [...Array(11)].map((_, i) => {
                      const pct = i * 10;
                      const timeAt = (duration * pct) / 100;
                      return (
                        <div
                          key={i}
                          style={{
                            position: "absolute",
                            left: `${pct}%`,
                            top: 0,
                            bottom: 0,
                            display: "flex",
                            alignItems: "flex-end",
                            fontSize: 9,
                            color: "#64748b",
                            paddingBottom: 2
                          }}
                        >
                          <div style={{ height: 4, width: 1, background: "rgba(255,255,255,0.2)", marginRight: 2 }} />
                          {formatShortTime(timeAt)}
                        </div>
                      );
                    })}
                </div>

                {/* Selection Range In/Out Highlight */}
                {duration > 0 && (
                  <div
                    style={{
                      position: "absolute",
                      left: `${inPct}%`,
                      width: `${Math.max(0, outPct - inPct)}%`,
                      top: 20,
                      bottom: 0,
                      background: "rgba(99,102,241,0.12)",
                      borderLeft: "2px solid #6366f1",
                      borderRight: "2px solid #6366f1",
                      pointerEvents: "none",
                      zIndex: 4
                    }}
                  >
                    <div style={{ position: "absolute", top: 2, left: 4, fontSize: 8, fontWeight: 800, color: "#a5b4fc" }}>
                      SEÇİM ({formatShortTime(outPoint - inPoint)})
                    </div>
                  </div>
                )}

                {/* Left Drag Trim Handle */}
                {duration > 0 && (
                  <div
                    onMouseDown={handleInHandleMouseDown}
                    style={{
                      position: "absolute",
                      left: `${inPct}%`,
                      top: 20,
                      bottom: 0,
                      width: 8,
                      background: "#6366f1",
                      borderRadius: "4px 0 0 4px",
                      cursor: "ew-resize",
                      zIndex: 8,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 0 8px rgba(99,102,241,0.6)"
                    }}
                    title={`Başlangıç Kırp: ${formatShortTime(inPoint)}`}
                  >
                    <div style={{ width: 2, height: 16, background: "#fff", borderRadius: 1 }} />
                  </div>
                )}

                {/* Right Drag Trim Handle */}
                {duration > 0 && (
                  <div
                    onMouseDown={handleOutHandleMouseDown}
                    style={{
                      position: "absolute",
                      left: `calc(${outPct}% - 8px)`,
                      top: 20,
                      bottom: 0,
                      width: 8,
                      background: "#6366f1",
                      borderRadius: "0 4px 4px 0",
                      cursor: "ew-resize",
                      zIndex: 8,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 0 8px rgba(99,102,241,0.6)"
                    }}
                    title={`Bitiş Kırp: ${formatShortTime(outPoint)}`}
                  >
                    <div style={{ width: 2, height: 16, background: "#fff", borderRadius: 1 }} />
                  </div>
                )}

                {/* Track 1: Text Overlay Pill */}
                <div
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedTimelineTrack("t1");
                  }}
                  style={{ height: 34, borderBottom: "1px solid rgba(255,255,255,0.03)", position: "relative", padding: "3px 0", cursor: "pointer" }}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: "4%",
                      width: "88%",
                      top: 3,
                      bottom: 3,
                      background: "linear-gradient(90deg, rgba(6,182,212,0.2), rgba(56,189,248,0.25))",
                      borderRadius: 5,
                      border: `1px solid ${selectedTimelineTrack === "t1" ? "#38bdf8" : "rgba(56,189,248,0.3)"}`,
                      display: "flex",
                      alignItems: "center",
                      padding: "0 8px",
                      fontSize: 10,
                      color: "#38bdf8",
                      fontWeight: 600,
                      opacity: t1Visibility ? 1 : 0.3
                    }}
                  >
                    T1 Altyazı & Başlık Katmanı
                  </div>
                </div>

                {/* Track 2: Video V1 */}
                <div
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedTimelineTrack("v1");
                  }}
                  style={{ height: 44, borderBottom: "1px solid rgba(255,255,255,0.03)", position: "relative", padding: "3px 0", cursor: "pointer" }}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: 0,
                      width: "100%",
                      top: 3,
                      bottom: 3,
                      background: "linear-gradient(90deg, #4338ca, #6366f1)",
                      borderRadius: 6,
                      border: `1.5px solid ${selectedTimelineTrack === "v1" ? "#c7d2fe" : "rgba(165,180,252,0.3)"}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "0 10px",
                      fontSize: 11,
                      color: "#fff",
                      fontWeight: 600,
                      boxShadow: selectedTimelineTrack === "v1" ? "0 0 10px rgba(99,102,241,0.5)" : "none",
                      opacity: v1Visibility ? 1 : 0.3
                    }}
                  >
                    <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {selectedVideo ? `${selectedVideo.title} [V1 GÖRÜNTÜ - ${videoSpeed}x]` : "V1 Video"}
                    </span>
                    <span style={{ fontSize: 9, opacity: 0.8 }}>{selectedVideo?.duration_str}</span>
                  </div>
                </div>

                {/* Track 3: Voiceover A1 */}
                <div
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedTimelineTrack("a1");
                  }}
                  style={{ height: 34, borderBottom: "1px solid rgba(255,255,255,0.03)", position: "relative", padding: "3px 0", cursor: "pointer" }}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: 0,
                      width: "100%",
                      top: 3,
                      bottom: 3,
                      background: "#064e3b",
                      borderRadius: 5,
                      border: `1.5px solid ${selectedTimelineTrack === "a1" ? "#6ee7b7" : "rgba(52,211,153,0.3)"}`,
                      display: "flex",
                      alignItems: "center",
                      padding: "0 8px",
                      overflow: "hidden",
                      boxShadow: selectedTimelineTrack === "a1" ? "0 0 10px rgba(52,211,153,0.4)" : "none",
                      opacity: a1Muted || muteOriginalVideoAudio ? 0.3 : 1
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 2, opacity: 0.75, width: "100%" }}>
                      {[...Array(60)].map((_, i) => (
                        <div
                          key={i}
                          style={{
                            flex: 1,
                            height: `${10 + Math.sin(i * 0.7) * 9 + (i % 3) * 4}px`,
                            background: "#34d399",
                            borderRadius: 1
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Track 4: Music A2 */}
                <div
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedTimelineTrack("a2");
                  }}
                  style={{ flex: 1, position: "relative", padding: "3px 0", cursor: "pointer" }}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: 0,
                      width: "100%",
                      top: 3,
                      bottom: 3,
                      background: "linear-gradient(90deg, #581c87, #7e22ce)",
                      borderRadius: 5,
                      border: `1.5px solid ${selectedTimelineTrack === "a2" ? "#e9d5ff" : "rgba(192,132,252,0.3)"}`,
                      display: "flex",
                      alignItems: "center",
                      padding: "0 8px",
                      fontSize: 10,
                      color: "#e9d5ff",
                      fontWeight: 600,
                      boxShadow: selectedTimelineTrack === "a2" ? "0 0 10px rgba(192,132,252,0.4)" : "none",
                      opacity: a2Muted ? 0.3 : 1
                    }}
                  >
                    <Music size={11} style={{ marginRight: 6 }} />
                    BGM: {selectedTrackId} ({Math.round(bgmVolume * 100)}% Ses)
                  </div>
                </div>

                {/* Draggable Clipchamp Playhead Needle */}
                <div
                  style={{
                    position: "absolute",
                    left: `${currentPct}%`,
                    top: 0,
                    bottom: 0,
                    width: 2,
                    background: "#6366f1",
                    zIndex: 10,
                    pointerEvents: "none"
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      left: -5,
                      width: 12,
                      height: 12,
                      background: "#6366f1",
                      borderRadius: "50% 50% 50% 0",
                      transform: "rotate(-45deg)",
                      boxShadow: "0 2px 6px rgba(0,0,0,0.5)"
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
