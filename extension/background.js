/* background.js — Service Worker */

let instagramSchedulePollRunning = false;

async function pollDueInstagramSchedule() {
  if (instagramSchedulePollRunning) return;
  instagramSchedulePollRunning = true;
  let claimedSchedule = null;
  try {
    const saved = await chrome.storage.local.get(["apiUrl", "instagram_active_schedule"]);
    const active = saved.instagram_active_schedule;
    if (active && Date.now() - active.claimedAt < 2 * 60 * 60 * 1000) return;
    if (active) await chrome.storage.local.remove("instagram_active_schedule");

    const apiUrl = (saved.apiUrl || "http://127.0.0.1:8000").replace(/\/$/, "");
    const response = await fetch(`${apiUrl}/api/instagram/schedules/claim`, { method: "POST" });
    if (!response.ok) throw new Error(`Plan kuyruğu alınamadı (HTTP ${response.status})`);
    const { schedule } = await response.json();
    if (!schedule) return;
    claimedSchedule = schedule;

    await chrome.storage.local.set({
      instagram_active_schedule: { ...schedule, claimedAt: Date.now() }
    });
    const matchingTabs = await chrome.tabs.query({ url: "https://www.instagram.com/*" });
    const tab = matchingTabs[0] || await chrome.tabs.create({
      url: "https://www.instagram.com/",
      active: true
    });
    if (matchingTabs.length) {
      await chrome.tabs.update(tab.id, { active: true });
    } else {
      await waitForInstagramTab(tab.id, schedule, 0);
      return;
    }
    setTimeout(() => sendInstagramSchedule(tab.id, schedule, 0), 500);
  } catch (error) {
    console.error("[YT-OTO] Instagram zamanlayıcı hatası:", error);
    if (claimedSchedule) {
      reportInstagramScheduleResult(
        claimedSchedule.id,
        false,
        error.message || "Instagram zamanlayıcısı sekmeyi hazırlayamadı."
      );
    }
  } finally {
    instagramSchedulePollRunning = false;
  }
}

function waitForInstagramTab(tabId, schedule, attempts) {
  if (attempts > 40) {
    reportInstagramScheduleResult(schedule.id, false, "Instagram sekmesi yüklenemedi.");
    return;
  }
  chrome.tabs.get(tabId, tab => {
    if (chrome.runtime.lastError || !tab) {
      reportInstagramScheduleResult(schedule.id, false, "Instagram sekmesi bulunamadı.");
      return;
    }
    if (tab.status === "complete") {
      sendInstagramSchedule(tabId, schedule, 0);
    } else {
      setTimeout(() => waitForInstagramTab(tabId, schedule, attempts + 1), 500);
    }
  });
}

function sendInstagramSchedule(tabId, schedule, attempts) {
  chrome.tabs.sendMessage(tabId, { type: "RUN_INSTAGRAM_SCHEDULE", schedule }, response => {
    if (chrome.runtime.lastError) {
      if (attempts < 5) {
        setTimeout(() => sendInstagramSchedule(tabId, schedule, attempts + 1), 1500);
      } else {
        reportInstagramScheduleResult(schedule.id, false, "Instagram eklenti betiğine ulaşılamadı; sayfayı yenileyip planı tekrar deneyin.");
      }
      return;
    }
    if (response?.ok === false) {
      reportInstagramScheduleResult(schedule.id, false, response.error || "Instagram yüklemesi başlatılamadı.");
    }
  });
}

async function reportInstagramScheduleResult(scheduleId, success, error = "", uncertain = false) {
  try {
    const { apiUrl = "http://127.0.0.1:8000" } = await chrome.storage.local.get("apiUrl");
    const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/instagram/schedules/${encodeURIComponent(scheduleId)}/result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ success, error, uncertain })
    });
    if (!response.ok) throw new Error(`Plan sonucu kaydedilemedi (HTTP ${response.status})`);
    await chrome.storage.local.remove("instagram_active_schedule");
    pollDueInstagramSchedule();
  } catch (reportError) {
    console.error("[YT-OTO] Instagram sonucu kaydedilemedi:", reportError);
  }
}

chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === "instagram-schedule-poll") pollDueInstagramSchedule();
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("instagram-schedule-poll", { periodInMinutes: 1 });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create("instagram-schedule-poll", { periodInMinutes: 1 });
  pollDueInstagramSchedule();
});

// Popup veya Content Script'ten gelen mesajları dinle
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "FETCH_API") {
    let fetchOptions = {};
    try {
      if (msg.options) {
        fetchOptions = JSON.parse(JSON.stringify(msg.options));
      }
    } catch (e) {
      fetchOptions = msg.options || {};
    }

    // İstek gövdesi (body) varsa Content-Type: application/json başlığını garanti et
    // Bu sayede FastAPI sunucusu istek gövdesini doğru okur ve 422 Unprocessable Content hatası vermez.
    if (fetchOptions.body) {
      if (!fetchOptions.headers) {
        fetchOptions.headers = {};
      }
      const hasContentType = Object.keys(fetchOptions.headers).some(k => k.toLowerCase() === "content-type");
      if (!hasContentType) {
        fetchOptions.headers["Content-Type"] = "application/json";
      }
    }

    fetch(msg.url, fetchOptions)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("video/") || msg.asArrayBuffer) {
          const buf = await res.arrayBuffer();
          // Convert ArrayBuffer to Base64
          const bytes = new Uint8Array(buf);
          let binary = '';
          const len = bytes.byteLength;
          const chunkSize = 8192;
          for (let i = 0; i < len; i += chunkSize) {
            binary += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + chunkSize, len)));
          }
          const base64 = btoa(binary);
          
          // Store in chrome.storage.local to bypass 64MB messaging limit
          const storageKey = "temp_video_upload_" + Date.now();
          return new Promise((resolve, reject) => {
            chrome.storage.local.set({ [storageKey]: base64 }, () => {
              if (chrome.runtime.lastError) {
                reject(new Error(`Video geçici depoya yazılamadı: ${chrome.runtime.lastError.message}`));
                return;
              }
              resolve({ ok: true, storageKey: storageKey, isBinary: true });
            });
          });
        } else {
          const text = await res.text();
          try {
            const json = JSON.parse(text);
            return { ok: true, data: json, isJson: true };
          } catch (e) {
            return { ok: true, data: text, isJson: false };
          }
        }
      })
      .then(result => sendResponse(result))
      .catch(err => {
        console.error("[YT-OTO] Background fetch error:", err);
        sendResponse({ ok: false, error: err.message });
      });
    return true; // async yanıt için kanalı açık tut
  }

  // Büyük JSON body (base64 görseller) için özel handler
  // body string olarak ayrıca gönderilir, structuredClone sınırını aşmaz
  if (msg.type === "PRODUCE_API") {
    const fetchOptions = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: msg.bodyStr  // string olarak gönderilir
    };
    fetch(msg.url, fetchOptions)
      .then(async (res) => {
        const text = await res.text();
        if (!res.ok) {
          return { ok: false, error: `HTTP ${res.status}: ${text.slice(0, 200)}` };
        }
        try {
          const json = JSON.parse(text);
          return { ok: true, data: json, isJson: true };
        } catch (e) {
          return { ok: true, data: text, isJson: false };
        }
      })
      .then(result => sendResponse(result))
      .catch(err => {
        console.error("[YT-OTO] Produce fetch error:", err);
        sendResponse({ ok: false, error: err.message });
      });
    return true;
  }

  if (msg.type === "GET_TABS") {
    chrome.tabs.query({ url: "https://studio.youtube.com/*" }, (tabs) => {
      sendResponse({ tabs });
    });
    return true; // async
  }

  if (msg.type === "OPEN_GROUP_TABS") {
    const payloads = msg.payloads;
    if (payloads && payloads.length > 0) {
      chrome.windows.create({
        url: `https://studio.youtube.com/?yt_oto_target=${encodeURIComponent(payloads[0].channel_id)}`,
        state: "maximized"
      }, (win) => {
        if (!win) return;
        const firstTab = win.tabs?.[0];
        if (firstTab) {
          chrome.storage.local.set({ [`yt_tab_target_${firstTab.id}`]: payloads[0].channel_id });
        }
        for (let i = 1; i < payloads.length; i++) {
          chrome.tabs.create({
            windowId: win.id,
            url: `https://studio.youtube.com/?yt_oto_target=${encodeURIComponent(payloads[i].channel_id)}`
          }, (newTab) => {
            if (newTab) {
              chrome.storage.local.set({ [`yt_tab_target_${newTab.id}`]: payloads[i].channel_id });
            }
          });
        }
      });
    }
    sendResponse({ ok: true });
    return true;
  }

  if (msg.type === "GET_TAB_TARGET") {
    const tabId = sender.tab?.id;
    if (tabId) {
      chrome.storage.local.get([`yt_tab_target_${tabId}`], (res) => {
        sendResponse({ targetId: res[`yt_tab_target_${tabId}`] || null });
      });
      return true; // async
    }
    sendResponse({ targetId: null });
    return false;
  }

  if (msg.type === "ENABLE_INSTAGRAM_SCHEDULER") {
    const apiUrl = (msg.apiUrl || "http://127.0.0.1:8000").replace(/\/$/, "");
    chrome.storage.local.set({ apiUrl }, () => {
      chrome.alarms.create("instagram-schedule-poll", { periodInMinutes: 1 });
      pollDueInstagramSchedule();
      sendResponse({ ok: true });
    });
    return true;
  }

  if (msg.type === "INSTAGRAM_SCHEDULE_FINISHED") {
    chrome.storage.local.remove("instagram_active_schedule");
    pollDueInstagramSchedule();
    sendResponse({ ok: true });
    return false;
  }

  // ── Perchance Text-to-Image Plugin API Çağrısı ─────────────────────
  if (msg.type === "GENERATE_PERCHANCE_IMAGE") {
    const prompt = msg.prompt || "";
    const isShorts = !!msg.isShorts;
    const isAvatar = !!msg.isAvatar;
    const resolution = isAvatar ? "512x512" : (isShorts ? "512x768" : "768x512");
    const negativePrompt = msg.negativePrompt || "";
    const seed = (typeof msg.seed === "number") ? msg.seed : -1;

    (async () => {
      try {
        const BASE_URL = "https://image-generation.perchance.org";

        // 1. verifyUser
        const verifyRes = await fetch(`${BASE_URL}/api/verifyUser?thread=0&__cacheBust=${Math.random()}`);
        if (!verifyRes.ok) throw new Error(`verifyUser failed (HTTP ${verifyRes.status})`);
        const verifyJson = await verifyRes.json();
        const userKey = verifyJson.userKey;
        if (!userKey) throw new Error("Perchance userKey doğrulanamadı.");

        // 2. generate
        const genUrl = `${BASE_URL}/api/generate?userKey=${userKey}&requestId=aiImageCompletion${Math.floor(Math.random() * 1e9)}&__cacheBust=${Math.random()}`;
        const genBody = {
          generatorName: "text-to-image-plugin",
          channel: "ai-text-to-image-generator",
          subChannel: "public",
          prompt: prompt,
          negativePrompt: negativePrompt,
          seed: seed,
          resolution: resolution,
          guidanceScale: 7
        };

        const genRes = await fetch(genUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(genBody)
        });

        if (!genRes.ok) throw new Error(`generate failed (HTTP ${genRes.status})`);
        const genData = await genRes.json();

        let downloadPath = genData.imageDownloadUrl;
        if (!downloadPath && genData.imageId) {
          downloadPath = `/api/downloadTemporaryImageViaProxy?imageId=${genData.imageId}`;
        }
        if (!downloadPath) throw new Error("Görsel indirme URL'si alınamadı.");

        const fullImgUrl = downloadPath.startsWith("http") ? downloadPath : (BASE_URL + downloadPath);

        // 3. download image
        const imgRes = await fetch(fullImgUrl);
        if (!imgRes.ok) throw new Error(`Görsel indirme hatası (HTTP ${imgRes.status})`);
        const buf = await imgRes.arrayBuffer();

        // Convert ArrayBuffer to Base64 safely
        const bytes = new Uint8Array(buf);
        const len = bytes.byteLength;
        const chunkSize = 8192;
        let binary = '';
        for (let i = 0; i < len; i += chunkSize) {
          binary += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + chunkSize, len)));
        }
        const base64Data = `data:image/jpeg;base64,${btoa(binary)}`;
        sendResponse({ ok: true, base64: base64Data, resolution: resolution });
      } catch (err) {
        console.error("[YT-OTO] Perchance API Hatası:", err);
        sendResponse({ ok: false, error: err.message });
      }
    })();
    return true; // async
  }
});

// Studio sekmesi açıldığında / yenilendiğinde pending payload'u gönder
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete") return;
  if (tab.url && tab.url.includes("instagram.com")) {
    chrome.storage.local.get(["instagram_active_schedule"], result => {
      if (result.instagram_active_schedule?.id) sendInstagramSchedule(tabId, result.instagram_active_schedule, 0);
    });
    return;
  }
  if (!tab.url || !tab.url.includes("studio.youtube.com")) return;

  chrome.storage.local.get(["yt_studio_pending"], (result) => {
    if (!result.yt_studio_pending) return;
    const payload = result.yt_studio_pending;

    // Timeout: 600 saniye (10 dakika) — hesap geçişi + yükleme süreci için yeterli
    if (Date.now() - (payload.timestamp || 0) > 600_000) {
      console.warn("[YT-OTO] Bekleyen yükleme süresi dolmuş (10dk), temizleniyor.");
      chrome.storage.local.remove(["yt_studio_pending"]);
      return;
    }

    // Content script'e START_AUTO_UPLOAD gönder (startAutoUpload() pipeline'ını tetikler)
    // initStudioAutoUpload zaten storage'dan okumuş olabilir, bu mesaj
    // "Studio sekmesi zaten açıkken yeni yükleme" senaryosunu kapatır.
    function sendStartUpload(retryCount) {
      chrome.tabs.sendMessage(tabId, { type: "START_AUTO_UPLOAD", payload }, (response) => {
        if (chrome.runtime.lastError) {
          if (retryCount < 3) {
            const delay = (retryCount + 1) * 1500;
            console.warn(`[YT-OTO] Content script henüz hazır değil, ${delay}ms sonra tekrar deneniyor (${retryCount + 1}/3)`);
            setTimeout(() => sendStartUpload(retryCount + 1), delay);
          } else {
            console.warn("[YT-OTO] START_AUTO_UPLOAD gönderilemedi (content script yok), initStudioAutoUpload storage'dan okuyacak.");
          }
        } else {
          console.log("[YT-OTO] ✅ START_AUTO_UPLOAD başarıyla gönderildi.");
          // Mesaj başarıyla alındı, storage'dan sil ki döngüye girmesin
          chrome.storage.local.remove(["yt_studio_pending"]);
        }
      });
    }

    // İlk denemeden önce kısa bir gecikme (DOM hazır olsun)
    setTimeout(() => sendStartUpload(0), 1500);
  });
});

console.log("[YT-OTO] Background service worker başlatıldı.");
