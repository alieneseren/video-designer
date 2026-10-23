/* popup.js — YT Otomasyon Extension */

let videos = [];
let selectedVideo = null;
let channels = [];
let activeChannelInfo = null;
let isPlatformActive = true;
let currentPlatform = "youtube";
let matchedInstagramChannel = null;
let instagramScheduleConfigured = false;
let instagramScheduledFolders = new Set();

const apiUrlInput  = document.getElementById("apiUrl");
const fetchBtn     = document.getElementById("fetchBtn");
const videoList    = document.getElementById("videoList");
const fillBtn      = document.getElementById("fillBtn");
const archiveBtn   = document.getElementById("archiveBtn");
const statusMsg    = document.getElementById("statusMsg");
const metaPreview  = document.getElementById("metaPreview");

/* ── Helpers ─────────────────────────────────────────────────── */

function showStatus(msg, type = "info") {
  statusMsg.textContent = msg;
  statusMsg.className = `status ${type}`;
  if (type !== "info") {
    setTimeout(() => { statusMsg.className = "status"; }, 4000);
  }
}

function getApiUrl() {
  return (apiUrlInput.value || "http://127.0.0.1:8000").replace(/\/$/, "");
}

function normalizeChannelName(str) {
  if (!str) return "";
  return String(str)
    .replace(/[\u0131\u0130]/g, "i") // ı, İ -> i
    .replace(/[\u015f\u015e]/g, "s") // ş, Ş -> s
    .replace(/[\u011f\u011e]/g, "g") // ğ, Ğ -> g
    .replace(/[\u00e7\u00c7]/g, "c") // ç, Ç -> c
    .replace(/[\u00f6\u00d6]/g, "o") // ö, Ö -> o
    .replace(/[\u00fc\u00dc]/g, "u") // ü, Ü -> u
    .replace(/[\u00df]/g, "ss")       // ß -> ss
    .replace(/[\u00f1\u00d1]/g, "n") // ñ, Ñ -> n
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function matchChannelObj(detected, ch) {
  if (!detected || !ch) return false;
  const detNorm = normalizeChannelName(detected);
  if (!detNorm) return false;

  const nameNorm = normalizeChannelName(ch.name || "");
  const idNorm = normalizeChannelName(ch.channel_id || "");

  // 1. Direct exact match with name or channel_id
  if (detNorm === nameNorm || detNorm === idNorm) return true;

  // 2. Base ID match (e.g. tr1_reddithikayeleri -> reddithikayeleri, ch_story_tr -> story, etc.)
  const detBase = detNorm.replace(/^@/, "").replace(/^(tr[0-9]*|ch|grp|es|en|de)/, "").replace(/(tr|en|de|es)$/, "").replace(/[sa]+$/, "");
  const idBase = idNorm.replace(/^@/, "").replace(/^(tr[0-9]*|ch|grp|es|en|de)/, "").replace(/(tr|en|de|es)$/, "").replace(/[sa]+$/, "");
  const nameBase = nameNorm.replace(/^@/, "").replace(/^(tr[0-9]*|ch|grp|es|en|de)/, "").replace(/(tr|en|de|es)$/, "").replace(/[sa]+$/, "");

  if (detBase && nameBase && detBase === nameBase && detBase.length >= 3) {
    return true;
  }
  if (detBase && idBase && detBase === idBase && detBase.length >= 3) {
    return true;
  }

  // 3. Substring match
  if (nameNorm.length >= 4 && (detNorm.includes(nameNorm) || nameNorm.includes(detNorm))) {
    return true;
  }
  if (idNorm.length >= 4 && (detNorm.includes(idNorm) || idNorm.includes(detNorm))) {
    return true;
  }

  // 4. Token overlap match
  const cleanTokens = (s) => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 2);
  const wDet = cleanTokens(detected);
  const wName = cleanTokens(ch.name || "");
  const common = wDet.filter(w => wName.includes(w));
  if (common.length >= 1 && common.length >= Math.min(wDet.length, wName.length) * 0.5) {
    return true;
  }

  return false;
}

/* ── Video Listesi ───────────────────────────────────────────── */

async function fetchVideos() {
  videoList.innerHTML = "<div class='empty'><div class='empty-icon'>⏳</div><div>Yükleniyor…</div></div>";
  
  // 1. Fetch local channels first
  try {
    const channelsRes = await fetch(`${getApiUrl()}/api/channels`);
    if (channelsRes.ok) {
      channels = await channelsRes.json();
    }
  } catch (e) {
    console.warn("[YT-OTO] Kanallar yüklenemedi:", e);
  }

  // 2. Query active tab for channel/profile name and identify platform
  currentPlatform = "youtube";
  let activeTabUrl = "";
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url) {
      activeTabUrl = tab.url;
      if (tab.url.includes("studio.youtube.com")) {
        currentPlatform = "youtube";
        activeChannelInfo = await chrome.tabs.sendMessage(tab.id, { type: "GET_ACTIVE_CHANNEL" }).catch(() => null);
      } else if (tab.url.includes("instagram.com")) {
        currentPlatform = "instagram";
        activeChannelInfo = await chrome.tabs.sendMessage(tab.id, { type: "GET_ACTIVE_INSTAGRAM" }).catch(() => null);
      } else if (tab.url.includes("tiktok.com")) {
        currentPlatform = "tiktok";
      }
    }
  } catch (e) {
    console.warn("[YT-OTO] Aktif kanal sorgulama hatası:", e);
  }

  // Dinamik buton ismini güncelle ve aktiflik kontrolü yap
  const fillBtn = document.getElementById("fillBtn");
  isPlatformActive = true;
  if (currentPlatform === "instagram") {
    const activeName = activeChannelInfo ? activeChannelInfo.channelName : "";
    const activeUsername = normalizeChannelName(activeName);
    matchedInstagramChannel = channels.find(c =>
      c.instagram && normalizeChannelName(c.instagram_username) === activeUsername
    ) || null;
    document.getElementById("youtubeScheduleOptions").style.display = "none";
    document.getElementById("instagramScheduleOptions").style.display = "block";
    document.getElementById("instagramAccountName").textContent = matchedInstagramChannel
      ? `Hesap: @${matchedInstagramChannel.instagram_username}`
      : "Bu Instagram profili kanallarda kayıtlı değil.";
    const isSchedule = document.getElementById("instagramScheduleCheck")?.checked;
    fillBtn.textContent = isSchedule ? "📅 Instagram'a Planla" : "▶ Instagram'a Yükle (Reel Paylaş)";
    if (!matchedInstagramChannel || !matchedInstagramChannel.instagram_username) {
      fillBtn.disabled = true;
      isPlatformActive = false;
    } else {
      await fetchInstagramScheduleDefaults(matchedInstagramChannel.channel_id);
      isPlatformActive = true;
      fillBtn.disabled = false;
    }
  } else if (currentPlatform === "tiktok") {
    document.getElementById("youtubeScheduleOptions").style.display = "block";
    document.getElementById("instagramScheduleOptions").style.display = "none";
    const activeName = activeChannelInfo ? activeChannelInfo.channelName : "";
    const matched = channels.find(c => matchChannelObj(activeName, c));
    if (matched && !matched.tiktok) {
      fillBtn.textContent = "▶ TikTok Aktif Değil";
      isPlatformActive = false;
    } else {
      fillBtn.textContent = "▶ TikTok'a Gönder";
    }
  } else {
    matchedInstagramChannel = null;
    document.getElementById("youtubeScheduleOptions").style.display = "block";
    document.getElementById("instagramScheduleOptions").style.display = "none";
    fillBtn.textContent = "▶ Studio'ya Gönder";
  }

  // 3. Fetch and render videos
  try {
    const res = await fetch(`${getApiUrl()}/api/output`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    videos = await res.json();
    
    let filtered = videos.filter(v => {
      if (v.archived) return false;
      if (currentPlatform === "youtube" && v.uploaded_youtube) return false;
      if (currentPlatform === "instagram" && v.uploaded_instagram) return false;
      if (currentPlatform === "tiktok" && v.uploaded_tiktok) return false;
      return true;
    });
    
    // Apply channel filtering if on YouTube Studio or Instagram
    if (currentPlatform === "instagram" && matchedInstagramChannel) {
      filtered = filtered.filter(v =>
        v.channel_id === matchedInstagramChannel.channel_id ||
        v.folder.startsWith(`${matchedInstagramChannel.channel_id}/`)
      ).filter(v => !instagramScheduledFolders.has(v.folder));
      showStatus(`Instagram hesabı: @${matchedInstagramChannel.instagram_username}`, "info");
    } else if (activeChannelInfo && activeChannelInfo.channelName) {
      const activeName = activeChannelInfo.channelName;
      
      // Find matching local channel using smart matchChannelObj
      const matchedLocalChannel = channels.find(c => matchChannelObj(activeName, c));
      
      if (matchedLocalChannel) {
        if (matchedLocalChannel.shorts_mode) {
          // Bu bir Shorts kanalı: bu kanalın kendi videolarını ve diğer tüm kanalların Shorts'larını göster
          filtered = filtered.filter(v => 
            v.shorts_mode || (v.folder && v.folder.startsWith(matchedLocalChannel.channel_id + "/")) || v.channel_id === matchedLocalChannel.channel_id
          );
        } else {
          // Bu bir uzun video kanalı: sadece bu kanala ait olan ve Shorts OLMAYAN videoları göster
          filtered = filtered.filter(v => 
            !v.shorts_mode && ((v.folder && v.folder.startsWith(matchedLocalChannel.channel_id + "/")) || v.channel_id === matchedLocalChannel.channel_id)
          );
        }
        showStatus(`Filtrelendi: ${matchedLocalChannel.name} (${(matchedLocalChannel.language || '').toUpperCase()})`, "info");
      } else {
        // Fallback: direct folder prefix match
        const activeNameNorm = normalizeChannelName(activeName);
        const tempFiltered = filtered.filter(v => 
          normalizeChannelName(v.folder.split('/')[0]) === activeNameNorm ||
          normalizeChannelName(v.channel_id) === activeNameNorm
        );
        if (tempFiltered.length > 0) {
          filtered = tempFiltered;
          showStatus(`Filtrelendi (Klasör eşleşmesi): ${activeName}`, "info");
        } else {
          filtered = [];
          showStatus(`Kanal eşleşmesi bulunamadı: ${activeName}`, "error");
        }
      }
    }
    
    // Sort videos by created_at (ascending) to get oldest first
    const sortedByAge = [...filtered].sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at) : new Date(0);
      const dateB = b.created_at ? new Date(b.created_at) : new Date(0);
      return dateA - dateB;
    });

    // Auto-select the oldest video not uploaded to the current platform
    let autoSelected = null;
    if (isPlatformActive) {
      if (currentPlatform === "instagram") {
        autoSelected = sortedByAge.find(v => !v.uploaded_instagram);
      } else if (currentPlatform === "tiktok") {
        autoSelected = sortedByAge.find(v => !v.uploaded_tiktok);
      } else {
        autoSelected = sortedByAge.find(v => !v.uploaded_youtube);
      }
    }

    if (!autoSelected && sortedByAge.length > 0) {
      autoSelected = sortedByAge[0];
    }
    
    renderVideoList(filtered, autoSelected);
  } catch (e) {
    videoList.innerHTML = `<div class='empty'><div class='empty-icon'>⚠️</div><div>Backend'e bağlanılamadı.<br><small>${e.message}</small></div></div>`;
    showStatus("Backend çalışmıyor — uvicorn src.server:app --port 8000", "error");
  }
}

async function fetchInstagramScheduleDefaults(channelId) {
  try {
    const response = await fetch(`${getApiUrl()}/api/channels/${encodeURIComponent(channelId)}/instagram-schedule-info`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Instagram planlama bilgisi alınamadı.");
    document.getElementById("instagramScheduleDate").value = data.suggested_date || "";
    document.getElementById("instagramScheduleTime").value = data.suggested_time || "";
    instagramScheduleConfigured = Boolean(data.configured);
    instagramScheduledFolders = new Set(
      (data.schedules || [])
        .filter(schedule => ["scheduled", "publishing", "published", "needs_review"].includes(schedule.status))
        .map(schedule => schedule.folder)
    );
    document.getElementById("instagramAccountName").textContent =
      `Hesap: @${data.instagram_username} · Saat dilimi: ${data.timezone}` +
      " · Planlı yükleme eklenti ile yapılır";
  } catch (error) {
    instagramScheduleConfigured = false;
    showStatus(error.message, "error");
    isPlatformActive = false;
    fillBtn.disabled = true;
  }
}

async function scheduleInstagramVideo() {
  if (!selectedVideo || !matchedInstagramChannel) return;
  const scheduledDate = document.getElementById("instagramScheduleDate").value;
  const scheduledTime = document.getElementById("instagramScheduleTime").value;
  if (!scheduledDate || !scheduledTime) {
    showStatus("Instagram için planlama tarihi ve saati seçin.", "error");
    return;
  }
  fillBtn.disabled = true;
  showStatus("Instagram gönderisi zamanlanıyor…", "info");
  try {
    const response = await fetch(`${getApiUrl()}/api/instagram/schedules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        folder: selectedVideo.folder,
        scheduled_date: scheduledDate,
        scheduled_time: scheduledTime,
        caption: selectedVideo.description || selectedVideo.title || ""
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Instagram gönderisi planlanamadı.");
    showStatus(data.message || "Instagram gönderisi planlandı; şimdi paylaşılmayacak.", "success");
    chrome.runtime.sendMessage({ type: "ENABLE_INSTAGRAM_SCHEDULER", apiUrl: getApiUrl() });
    await fetchVideos();
  } catch (error) {
    showStatus(error.message, "error");
    fillBtn.disabled = !isPlatformActive;
  }
}

async function fillInstagramInstant(tab) {
  if (!selectedVideo || !matchedInstagramChannel) return;
  fillBtn.disabled = true;
  showStatus("Instagram Reels yüklemesi başlatılıyor…", "info");

  const captionText = selectedVideo.description || (selectedVideo.title ? `${selectedVideo.title}\n\n#reels #shorts #viral` : "#reels");

  const payload = {
    title: selectedVideo.title,
    caption: captionText,
    folder: selectedVideo.folder,
    video_path: selectedVideo.video_path || "",
    video_url: selectedVideo.video_url || "",
    instagram_username: matchedInstagramChannel.instagram_username,
    channel_id: matchedInstagramChannel.channel_id,
  };

  chrome.tabs.sendMessage(tab.id, { type: "FILL_INSTAGRAM", video: payload }, response => {
    fillBtn.disabled = false;
    if (chrome.runtime.lastError) {
      showStatus("Instagram sekmesine ulaşılamadı. Lütfen Instagram sayfasını yenileyin.", "error");
      return;
    }
    if (response && response.ok) {
      showStatus("🚀 Instagram yükleme adımları başlatıldı!", "success");
      setTimeout(() => window.close(), 1500);
    } else {
      showStatus(response?.error || "Instagram yüklemesi başlatılamadı.", "error");
    }
  });
}

function renderVideoList(list, autoSelectedVideo = null) {
  if (list.length === 0) {
    videoList.innerHTML = "<div class='empty'><div class='empty-icon'>🎬</div><div>Video bulunamadı.</div></div>";
    fillBtn.disabled = true;
    archiveBtn.style.display = "none";
    metaPreview.className = "metadata-preview";
    return;
  }
  
  videoList.innerHTML = list.map((v, i) => {
    const isSelected = autoSelectedVideo && v.folder === autoSelectedVideo.folder;
    
    // Hangi sosyal medya ikonlarının aktif olduğunu bul
    const channelId = v.folder.split('/')[0];
    const ch = channels.find(c => c.channel_id === channelId);
    const isIgActive = ch ? ch.instagram === true : false;
    const isTtActive = ch ? ch.tiktok === true : false;

    return `
      <div class="video-item ${isSelected ? 'selected' : ''}" data-index="${i}" data-folder="${v.folder}">
        <div class="video-icon">${v.shorts_mode ? "📱" : "🎬"}</div>
        <div class="video-info">
          <div class="video-title">${escHtml(v.title || "(Başlık yok)")}</div>
          <div class="video-meta">${escHtml(v.folder)}</div>
          <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-top: 6px;">
            <span class="tag-pill badge-created" style="background: rgba(255,255,255,0.06); color: #ccc; border: 1px solid rgba(255,255,255,0.1); font-size: 9px; padding: 1px 4px; border-radius: 3px;">
              📅 ${v.created_at ? v.created_at.substring(0, 16).replace('T', ' ') : 'Bilinmiyor'}
            </span>
            <span class="tag-pill badge-yt" data-status="${v.uploaded_youtube}" style="font-size: 9px; padding: 1px 4px; border-radius: 3px; cursor: pointer; user-select: none; background: ${v.uploaded_youtube ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)'}; color: ${v.uploaded_youtube ? '#22c55e' : '#ef4444'}; border: 1px solid ${v.uploaded_youtube ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'};">
              YouTube: ${v.uploaded_youtube ? '✅' : '❌'}
            </span>
            ${isIgActive ? `
            <span class="tag-pill badge-ig" data-status="${v.uploaded_instagram}" style="font-size: 9px; padding: 1px 4px; border-radius: 3px; cursor: pointer; user-select: none; background: ${v.uploaded_instagram ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)'}; color: ${v.uploaded_instagram ? '#22c55e' : '#ef4444'}; border: 1px solid ${v.uploaded_instagram ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'};">
              Instagram: ${v.uploaded_instagram ? '✅' : '❌'}
            </span>` : ''}
            ${isTtActive ? `
            <span class="tag-pill badge-tt" data-status="${v.uploaded_tiktok}" style="font-size: 9px; padding: 1px 4px; border-radius: 3px; cursor: pointer; user-select: none; background: ${v.uploaded_tiktok ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)'}; color: ${v.uploaded_tiktok ? '#22c55e' : '#ef4444'}; border: 1px solid ${v.uploaded_tiktok ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'};">
              TikTok: ${v.uploaded_tiktok ? '✅' : '❌'}
            </span>` : ''}
          </div>
        </div>
        ${v.shorts_mode ? "<div class='badge'>SHORTS</div>" : ""}
      </div>
    `;
  }).join("");

  if (autoSelectedVideo) {
    selectedVideo = autoSelectedVideo;
    showMetaPreview(selectedVideo);
    fillBtn.disabled = !isPlatformActive;
    archiveBtn.style.display = selectedVideo.archived ? "none" : "block";
  } else {
    fillBtn.disabled = true;
  }

  // Tıklama
  videoList.querySelectorAll(".video-item").forEach(el => {
    el.addEventListener("click", () => {
      videoList.querySelectorAll(".video-item").forEach(e => e.classList.remove("selected"));
      el.classList.add("selected");
      const folder = el.dataset.folder;
      selectedVideo = list.find(v => v.folder === folder);
      showMetaPreview(selectedVideo);
      fillBtn.disabled = !isPlatformActive;
      archiveBtn.style.display = selectedVideo.archived ? "none" : "block";
    });
  });

  // Etiketlerin manuel değiştirilmesi (Toggle)
  videoList.querySelectorAll(".tag-pill").forEach(el => {
    el.addEventListener("click", async (e) => {
      if (el.classList.contains("badge-created")) return;
      e.stopPropagation();
      
      const folder = el.closest(".video-item").dataset.folder;
      const video = list.find(v => v.folder === folder);
      if (!video) return;

      let platform = "";
      let newStatus = false;

      if (el.classList.contains("badge-yt")) {
        platform = "youtube";
        newStatus = el.dataset.status !== "true";
      } else if (el.classList.contains("badge-ig")) {
        platform = "instagram";
        newStatus = el.dataset.status !== "true";
      } else if (el.classList.contains("badge-tt")) {
        platform = "tiktok";
        newStatus = el.dataset.status !== "true";
      }

      if (!platform) return;

      try {
        const payload = {};
        payload[platform] = newStatus;
        const res = await fetch(`${getApiUrl()}/api/output/${encodeURIComponent(folder)}/status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          const data = await res.json();
          if (data.archived) {
            showStatus("Video tüm platformlara yüklendi ve arşivlendi! 📦", "success");
          } else {
            showStatus("Durum güncellendi.", "success");
          }
          fetchVideos(); // Listeyi yenile
        } else {
          showStatus("Durum güncellenemedi.", "error");
        }
      } catch (err) {
        showStatus("Bağlantı hatası.", "error");
      }
    });
  });
}

function showMetaPreview(video) {
  if (!video) { metaPreview.className = "metadata-preview"; return; }
  const tags = (video.tags || []).slice(0, 8).map(t => `<span class="tag-pill">#${escHtml(t)}</span>`).join("");
  metaPreview.innerHTML = `
    <strong style="color:#e2e8f0">${escHtml(video.title || "(Başlık yok)")}</strong><br>
    <span style="font-size:10px; color:#64748b">${(video.description || "").slice(0, 120)}…</span><br>
    <div style="margin-top:4px">${tags}</div>
  `;
  metaPreview.className = "metadata-preview show";
}

function escHtml(str) {
  return String(str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

/* ── Studio'ya / Instagram'a Gönder ────────────────────────────────────────── */

async function fillStudio() {
  if (!selectedVideo) return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  if (currentPlatform === "instagram") {
    const isSchedule = document.getElementById("instagramScheduleCheck")?.checked;
    if (isSchedule) {
      await scheduleInstagramVideo();
    } else {
      await fillInstagramInstant(tab);
    }
    return;
  }

  // YouTube Studio Otomasyonu
  showStatus("YouTube Studio açılıyor…", "info");

  const kidsOption = document.getElementById("kidsSelect").value === "true";
  const autoDate = document.getElementById("autoDateCheck").checked;
  const startDate = document.getElementById("startDateInput").value;

  const payload = {
    title:       selectedVideo.title,
    description: selectedVideo.description,
    tags:        selectedVideo.tags,
    folder:      selectedVideo.folder,
    video_path:  selectedVideo.video_path,
    plan_id:     selectedVideo.plan_id || "",
    language:    selectedVideo.language || "en",
    channel_id:  selectedVideo.channel_id || "",
    timestamp:   Date.now(),
    kidsOption:  kidsOption,
    autoDate:    autoDate,
    startDate:   startDate,
  };

  // Uzun videoya ait olan ve henüz yüklenmemiş alt Shorts videolarını bul
  const childShorts = videos.filter(v => 
    v.folder.startsWith(selectedVideo.folder + "/shorts_") && !v.uploaded_youtube
  );
  
  // Klasör adına göre sırala (shorts_1, shorts_2, shorts_3 şeklinde sırayla yüklenmesi için)
  childShorts.sort((a, b) => a.folder.localeCompare(b.folder));
  
  // Kuyruk oluştur: Önce asıl uzun video, ardından alt Shorts videoları
  const queue = [
    { ...payload },
    ...childShorts.map(sv => ({
      title:       sv.title,
      description: sv.description,
      tags:        sv.tags,
      folder:      sv.folder,
      video_path:  sv.video_path,
      plan_id:     sv.plan_id || "",
      language:    sv.language || "en",
      channel_id:  sv.channel_id || "",
      timestamp:   Date.now(),
      kidsOption:  kidsOption,
      autoDate:    autoDate,
      startDate:   startDate,
    }))
  ];

  console.log("[YT-OTO] Yükleme sırası hazırlandı:", queue);
  await chrome.storage.local.set({ yt_upload_queue: queue });
  await chrome.storage.local.set({ yt_studio_pending: payload });

  if (selectedVideo.video_path) {
    try {
      await navigator.clipboard.writeText(selectedVideo.video_path);
      console.log("[YT-OTO] Video yolu panoya kopyalandı:", selectedVideo.video_path);
    } catch (err) {
      console.error("[YT-OTO] Panoya kopyalama hatası:", err);
    }
  }

  if (tab && tab.url && tab.url.includes("studio.youtube.com")) {
    try {
      await chrome.tabs.sendMessage(tab.id, { type: "FILL_STUDIO", payload });
      showStatus("Veriler Studio'ya gönderildi!", "success");
    } catch (err) {
      console.warn("[YT-OTO] Content script is not ready in target tab:", err.message);
      showStatus("Eklenti bağlantısı hazır değil. Lütfen YouTube Studio sayfasını yenileyin (F5).", "error");
    }
  } else {
    await chrome.tabs.create({ url: "https://studio.youtube.com" });
    showStatus("Studio açıldı — upload sayfasına geçince otomatik dolduracak.", "success");
  }
}

/* ── Arşivle ─────────────────────────────────────────────────── */

async function archiveVideo() {
  if (!selectedVideo) return;
  try {
    const res = await fetch(`${getApiUrl()}/api/output/${selectedVideo.folder}/archive`, { method: "POST" });
    if (res.ok) {
      showStatus("Arşivlendi ✓", "success");
      selectedVideo.archived = true;
      archiveBtn.style.display = "none";
      fetchVideos();
    } else {
      showStatus("Arşivleme başarısız.", "error");
    }
  } catch (e) {
    showStatus("Bağlantı hatası.", "error");
  }
}

/* ── Event Listeners ─────────────────────────────────────────── */

fetchBtn.addEventListener("click", fetchVideos);
fillBtn.addEventListener("click", fillStudio);
archiveBtn.addEventListener("click", archiveVideo);

// API URL kaydet/yükle
chrome.storage.local.get(["apiUrl", "kidsOption", "autoDate", "startDate"], (result) => {
  if (result.apiUrl) apiUrlInput.value = result.apiUrl;
  chrome.runtime.sendMessage({ type: "ENABLE_INSTAGRAM_SCHEDULER", apiUrl: getApiUrl() });
  
  const kidsSelect = document.getElementById("kidsSelect");
  const autoDateCheck = document.getElementById("autoDateCheck");
  const startDateGroup = document.getElementById("startDateGroup");
  const startDateInput = document.getElementById("startDateInput");
  
  if (result.kidsOption !== undefined) kidsSelect.value = result.kidsOption;
  if (result.autoDate !== undefined) {
    autoDateCheck.checked = result.autoDate;
    startDateGroup.style.display = result.autoDate ? "none" : "flex";
  } else {
    startDateGroup.style.display = "none";
  }
  if (result.startDate) {
    startDateInput.value = result.startDate;
  } else {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    startDateInput.value = `${yyyy}-${mm}-${dd}`;
  }
  
  kidsSelect.addEventListener("change", () => {
    chrome.storage.local.set({ kidsOption: kidsSelect.value });
  });
  autoDateCheck.addEventListener("change", () => {
    const checked = autoDateCheck.checked;
    startDateGroup.style.display = checked ? "none" : "flex";
    chrome.storage.local.set({ autoDate: checked });
  });
  startDateInput.addEventListener("change", () => {
    chrome.storage.local.set({ startDate: startDateInput.value });
  });
  apiUrlInput.addEventListener("change", () => {
    chrome.storage.local.set({ apiUrl: apiUrlInput.value });
    chrome.runtime.sendMessage({ type: "ENABLE_INSTAGRAM_SCHEDULER", apiUrl: getApiUrl() });
  });

  const igScheduleCheck = document.getElementById("instagramScheduleCheck");
  if (igScheduleCheck) {
    igScheduleCheck.addEventListener("change", (e) => {
      const isChecked = e.target.checked;
      const dtGroup = document.getElementById("instagramScheduleDateTimeGroup");
      if (dtGroup) dtGroup.style.display = isChecked ? "grid" : "none";
      if (currentPlatform === "instagram") {
        fillBtn.textContent = isChecked ? "📅 Instagram'a Planla" : "▶ Instagram'a Yükle (Reel Paylaş)";
      }
    });
  }
});

const syncServerBtn = document.getElementById("syncServerBtn");
if (syncServerBtn) {
  syncServerBtn.addEventListener("click", async () => {
    syncServerBtn.disabled = true;
    syncServerBtn.textContent = "⏳ Çekiliyor...";
    showStatus("Sunucudaki videolar taranıyor ve Mac'e aktarılıyor...", "info");
    try {
      const res = await fetch(`${getApiUrl()}/api/server-render/sync-all`, { method: "POST" });
      const data = await res.json();
      if (res.ok && data.success) {
        if (data.count > 0) {
          showStatus(`✓ ${data.count} video Mac 'yuklenecek' klasörüne indirildi ve sunucudan silindi.`, "success");
        } else {
          showStatus("Sunucuda bekleyen yeni video bulunamadı.", "info");
        }
        await fetchVideos();
      } else {
        showStatus(`İndirme uyarısı: ${data.message || data.detail || 'Hata'}`, "error");
      }
    } catch (err) {
      showStatus(`Bağlantı hatası: ${err.message}`, "error");
    } finally {
      syncServerBtn.disabled = false;
      syncServerBtn.innerHTML = "<span>☁️ Sunucudan Çek</span>";
    }
  });
}

// İlk yükleme
fetchVideos();
