/* content.js — YouTube Studio otomatik yükleme ve doldurma */

// ── Localhost'tan (Dashboard) gelen mesajları dinle ───────────
if (location.host.includes("localhost") || location.host.includes("127.0.0.1")) {
  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "YT_STUDIO_SEND") {
      const payload = event.data.payload;
      const queue = event.data.queue || [];
      const toSet = { yt_studio_pending: payload };
      if (Array.isArray(queue) && queue.length > 0) {
        toSet.yt_upload_queue = queue;
      }
      chrome.storage.local.set(toSet, () => {
        console.log("[YT-OTO] ✅ Dashboard'dan video ve grup kuyruğu alındı:", payload, "Kalan kuyruk:", queue.length);
      });
    }
    if (event.data && event.data.type === "YT_STUDIO_GROUP_SEND") {
      const payloads = event.data.payloads;
      chrome.storage.local.set({ yt_group_payloads: payloads }, () => {
        console.log("[YT-OTO] ✅ Dashboard'dan grup yükleme komutu alındı:", payloads);
        chrome.runtime.sendMessage({ type: "OPEN_GROUP_TABS", payloads: payloads });
      });
    }
  });
}

// ── Deep Shadow DOM Arama Yardımcıları ────────────────────────
function findElementsDeep(predicate, root = document) {
  const results = [];
  function walk(node) {
    if (!node) return;
    if (node.nodeType === Node.ELEMENT_NODE) {
      try {
        if (predicate(node)) {
          results.push(node);
        }
      } catch (e) {}
    }
    if (node.shadowRoot) {
      walk(node.shadowRoot);
    }
    const children = node.children || (node.childNodes ? Array.from(node.childNodes) : []);
    for (let i = 0; i < children.length; i++) {
      walk(children[i]);
    }
  }
  walk(root);
  return results;
}

function queryShadow(selector, root = document) {
  try {
    const el = root.querySelector(selector);
    if (el) return el;
  } catch (e) {}

  try {
    if (root.shadowRoot) {
      const found = queryShadow(selector, root.shadowRoot);
      if (found) return found;
    }
  } catch (e) {}

  try {
    const all = root.querySelectorAll('*');
    for (const el of all) {
      try {
        if (el.shadowRoot) {
          const found = queryShadow(selector, el.shadowRoot);
          if (found) return found;
        }
      } catch (e) {}
    }
  } catch (e) {}
  return null;
}

function queryShadowAll(selector, root = document) {
  let results = [];
  try {
    const els = root.querySelectorAll(selector);
    results = results.concat(Array.from(els));
  } catch (e) {}

  try {
    if (root.shadowRoot) {
      results = results.concat(queryShadowAll(selector, root.shadowRoot));
    }
  } catch (e) {}

  try {
    const all = root.querySelectorAll('*');
    for (const el of all) {
      try {
        if (el.shadowRoot) {
          results = results.concat(queryShadowAll(selector, el.shadowRoot));
        }
      } catch (e) {}
    }
  } catch (e) {}
  return results;
}

// ── Sayfa İçi ytcfg / Script Kanal Bilgisi Köprüsü ────────────
let injectedPageChannelName = null;
let injectedPageChannelId = null;

if (location.href.includes("studio.youtube.com")) {
  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "YT_PAGE_CHANNEL_INFO") {
      if (event.data.channelName) injectedPageChannelName = event.data.channelName;
      if (event.data.channelId) injectedPageChannelId = event.data.channelId;
    }
  });

  function requestPageContextChannel() {
    try {
      const script = document.createElement("script");
      script.textContent = `
        try {
          const name = (window.ytcfg && typeof window.ytcfg.get === 'function') 
            ? (window.ytcfg.get('CHANNEL_NAME') || window.ytcfg.get('USER_DISPLAY_NAME') || window.ytcfg.get('DELEGATED_SESSION_ID')) 
            : null;
          const id = (window.ytcfg && typeof window.ytcfg.get === 'function') ? window.ytcfg.get('CHANNEL_ID') : null;
          window.postMessage({ type: 'YT_PAGE_CHANNEL_INFO', channelName: name, channelId: id }, '*');
        } catch (e) {}
      `;
      (document.head || document.documentElement).appendChild(script);
      script.remove();
    } catch (e) {}
  }
  requestPageContextChannel();
}

function normalizeChannelString(str) {
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
    .replace(/[\u0300-\u036f]/g, "") // remove accents
    .toLowerCase()
    .replace(/[^a-z0-9]/g, ""); // keep only alphanumeric
}

function isChannelMatch(name1, name2) {
  if (!name1 || !name2) return false;
  const n1 = normalizeChannelString(name1);
  const n2 = normalizeChannelString(name2);
  if (!n1 || !n2) return false;
  if (n1 === n2) return true;

  // 1. Dil kodu / ön ek temizleme (tr, en, de, es)
  const stripLang = (s) => s.replace(/^@/, "").replace(/^(tr[0-9]*|ch|grp|es|en|de)_?/, "").replace(/_?(tr|en|de|es)$/, "");
  const s1 = stripLang(n1);
  const s2 = stripLang(n2);
  if (s1 && s2 && s1 === s2 && s1.length >= 3) {
    return true;
  }

  // 2. Kelime kümesi tam eşleşmesi (kelime sırası bağımsız: "Reddit Hikayeleri" == "Hikayeleri Reddit")
  // ÖNEMLİ: Sadece 1 kelime tutuyor diye (örn: sadece "Reddit") kanalları AYNI SAYMA!
  const cleanTokens = (s) => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length >= 2);
  const w1 = cleanTokens(name1).filter(w => !['tr', 'en', 'de', 'es', 'channel', 'kanal'].includes(w));
  const w2 = cleanTokens(name2).filter(w => !['tr', 'en', 'de', 'es', 'channel', 'kanal'].includes(w));

  if (w1.length > 0 && w2.length > 0) {
    const set1 = new Set(w1);
    const set2 = new Set(w2);
    // İki tarafın da kelime setleri tamamen eşit olmalı
    if (set1.size === set2.size && [...set1].every(t => set2.has(t))) {
      return true;
    }
  }

  // 3. Küçük harf / boşluksuz handle eşleşmesi (örn: "redditchronicles" vs "redditchroniclesa")
  if (n1.length >= 6 && n2.length >= 6) {
    if (n1.startsWith(n2) || n2.startsWith(n1)) {
      const diff = Math.abs(n1.length - n2.length);
      if (diff <= 2) return true;
    }
  }

  return false;
}

function isGenericChannelWord(text) {
  if (!text) return true;
  const t = text.toLowerCase().trim();
  const generic = [
    "youtube studio", "studio", "pano", "kontrol paneli", "dashboard", "içerik", "icerik",
    "content", "analytics", "istatistikler", "ayarlar", "settings", "özelleştirme", "customization",
    "telif hakkı", "copyright", "altyazılar", "para kazanma", "earn", "monetization",
    "kitaplık", "audio library", "kapat", "aç", "menü", "ara", "yükle", "oluştur", "create", "upload"
  ];
  return generic.some(g => t === g || t === `youtube ${g}`);
}

function getChannelFromScripts() {
  try {
    const scripts = document.querySelectorAll('script');
    for (const s of scripts) {
      const txt = s.textContent || "";
      if (!txt) continue;
      if (txt.includes("CHANNEL_NAME") || txt.includes("USER_DISPLAY_NAME") || txt.includes("channelTitle")) {
        const patterns = [
          /"CHANNEL_NAME"\s*:\s*"([^"]+)"/,
          /"USER_DISPLAY_NAME"\s*:\s*"([^"]+)"/,
          /"channelTitle"\s*:\s*"([^"]+)"/,
          /"channelName"\s*:\s*"([^"]+)"/
        ];
        for (const p of patterns) {
          const m = txt.match(p);
          if (m && m[1] && m[1].trim() && !isGenericChannelWord(m[1])) {
            return m[1].trim();
          }
        }
      }
    }
  } catch (e) {}
  return null;
}

function getActiveChannelName() {
  // 1. Injected ytcfg bridge / page context
  if (injectedPageChannelName && !isGenericChannelWord(injectedPageChannelName)) {
    return injectedPageChannelName;
  }

  // 2. Inline scripts parsing
  const fromScripts = getChannelFromScripts();
  if (fromScripts) return fromScripts;

  // 3. Deep search for #entity-name or class entity-name across ALL Shadow Roots
  const entityEls = findElementsDeep(n => n.id === "entity-name" || (n.className && typeof n.className === "string" && n.className.includes("entity-name")));
  for (const el of entityEls) {
    let text = "";
    if (el.childNodes && el.childNodes.length > 0) {
      for (let child of el.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) {
          text += child.textContent;
        }
      }
    }
    text = text.replace(/[\r\n\t]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
    if (text && text.length >= 2 && !isGenericChannelWord(text)) {
      return text;
    }

    // Fallback on clone stripping badges/tooltips
    try {
      const clone = el.cloneNode(true);
      clone.querySelectorAll('ytcp-tooltip, ytcp-badge, yt-icon, tooltip, svg, style, script').forEach(t => t.remove());
      const cloneText = (clone.innerText || clone.textContent || "").replace(/[\r\n\t]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
      if (cloneText && cloneText.length >= 2 && !isGenericChannelWord(cloneText)) {
        return cloneText;
      }
    } catch (e) {}
  }

  // 4. Deep search for #channel-title, #channel-handle, .channel-title
  const titleEls = findElementsDeep(n => n.id === "channel-title" || n.id === "channel-handle" || (n.className && typeof n.className === "string" && n.className.includes("channel-title")));
  for (const el of titleEls) {
    try {
      const clone = el.cloneNode(true);
      clone.querySelectorAll('ytcp-tooltip, ytcp-badge, yt-icon, tooltip, svg, style, script').forEach(t => t.remove());
      const text = (clone.innerText || clone.textContent || "").replace(/[\r\n\t]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
      if (text && text.length >= 2 && !isGenericChannelWord(text)) {
        return text;
      }
    } catch (e) {}
  }

  // 5. Drawer / Sidebar elements
  const drawerEls = findElementsDeep(n => n.tagName && (n.tagName.toLowerCase() === 'ytcp-navigation-drawer' || n.tagName.toLowerCase() === 'ytcp-sidebar-header'));
  for (const drawer of drawerEls) {
    const nameEl = drawer.querySelector?.('#entity-name, .entity-name, #channel-title') || 
                   (drawer.shadowRoot && drawer.shadowRoot.querySelector?.('#entity-name, .entity-name, #channel-title'));
    if (nameEl) {
      const raw = (nameEl.innerText || nameEl.textContent || "").replace(/[\r\n\t]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
      if (raw && raw.length >= 2 && !isGenericChannelWord(raw)) {
        return raw;
      }
    }
  }

  // 6. Avatar img alt / title
  const imgEls = findElementsDeep(n => (n.id === 'avatar-img' || (n.className && typeof n.className === 'string' && n.className.includes('avatar'))) && (n.alt || n.title));
  for (const img of imgEls) {
    const alt = (img.getAttribute('alt') || img.getAttribute('title') || '').trim();
    if (alt) {
      const cleanAlt = alt.replace(/(için|for|für|del canal|avatar|profil|resmi|image|fotoğrafı|del|canal|channel)/gi, "").replace(/[\s\-_:]+/g, " ").trim();
      if (cleanAlt && cleanAlt.length >= 3 && !isGenericChannelWord(cleanAlt) && !cleanAlt.toLowerCase().includes("google")) {
        return cleanAlt;
      }
    }
  }

  // 7. Document title (e.g. "Crónicas de Reddit - YouTube Studio")
  if (document.title) {
    let t = document.title.trim();
    if (t.includes("- YouTube Studio")) {
      const parsed = t.split("- YouTube Studio")[0].trim();
      if (parsed && !isGenericChannelWord(parsed) && parsed.length < 60) {
        return parsed;
      }
    } else if (t.includes("YouTube Studio - ")) {
      const parsed = t.split("YouTube Studio - ")[1].trim();
      if (parsed && !isGenericChannelWord(parsed) && parsed.length < 60) {
        return parsed;
      }
    }
  }

  return null;
}

async function waitForActiveChannelName(maxAttempts = 15) {
  requestPageContextChannel();
  for (let i = 0; i < maxAttempts; i++) {
    const name = getActiveChannelName();
    if (name) return name;
    if (i % 3 === 0) requestPageContextChannel();
    await new Promise(r => setTimeout(r, 500));
  }
  return null;
}

// ── Extension Popup / Background'dan gelen mesajları dinle ──────
const activeInstagramScheduleIds = new Set();

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "FILL_STUDIO") {
    fillStudioForm(msg.payload);
    sendResponse({ ok: true });
  } else if (msg.type === "START_AUTO_UPLOAD") {
    // background.js'den gelen doğrudan upload tetikleme mesajı
    // (Studio sekmesi zaten açıkken yeni yükleme başlatmak için)
    const payload = msg.payload;
    if (payload) {
      console.log("[YT-OTO] 🚀 START_AUTO_UPLOAD mesajı alındı:", payload.channel_name, payload.title);
      // Storage'dan sil (background.js de siliyor, çift silme zararsız)
      chrome.storage.local.remove(["yt_studio_pending"]);
      safeStartAutoUpload(payload);
    }
    sendResponse({ ok: true });
  } else if (msg.type === "GET_ACTIVE_CHANNEL") {
    const channelName = getActiveChannelName();
    sendResponse({ channelName });
  } else if (msg.type === "FILL_INSTAGRAM") {
    const video = msg.video || msg.payload;
    if (!video) {
      sendResponse({ ok: false, error: "Yüklenecek video bilgisi bulunamadı." });
      return false;
    }
    showNotification("🚀 Instagram Reels yüklemesi başlatılıyor...");
    uploadToInstagram(video, false).then(result => {
      sendResponse({ ok: true, result });
    }).catch(error => {
      console.error("[YT-OTO] Instagram yükleme hatası:", error);
      showNotification(`❌ Instagram Hatası: ${error.message}`);
      sendResponse({ ok: false, error: error.message });
    });
    return true;
  } else if (msg.type === "RUN_INSTAGRAM_SCHEDULE") {
    const schedule = msg.schedule;
    if (!schedule?.id || activeInstagramScheduleIds.has(schedule.id)) {
      sendResponse({ ok: true });
      return false;
    }
    activeInstagramScheduleIds.add(schedule.id);
    runScheduledInstagramUpload(schedule).catch(error => {
      console.error("[YT-OTO] Instagram zamanlanmış yükleme hatası:", error);
      finishScheduledInstagramUpload(schedule.id, {
        success: false,
        error: error.message || "Instagram yüklemesi başarısız oldu.",
        uncertain: Boolean(error.publishAttempted),
      });
    }).finally(() => activeInstagramScheduleIds.delete(schedule.id));
    sendResponse({ ok: true });
    return false;
  } else if (msg.type === "GET_ACTIVE_INSTAGRAM") {
    const channelName = getActiveInstagramProfile();
    sendResponse({ channelName });
  }
});
// ── Yükleme işlemi tekrar tetiklenmesini önleyen global bayrak ──
let ytOtoUploadActive = false;

function safeStartAutoUpload(payload) {
  if (ytOtoUploadActive) {
    console.warn("[YT-OTO] ⚠️ startAutoUpload zaten çalışıyor, tekrar tetikleme engellendi.");
    return;
  }
  ytOtoUploadActive = true;
  startAutoUpload(payload).finally(() => {
    ytOtoUploadActive = false;
  }).catch(() => {
    ytOtoUploadActive = false;
  });
}

if (location.href.includes("studio.youtube.com")) {
  async function initStudioAutoUpload() {
    // Sayfanın ve eklentinin hazır olması için kısa bir gecikme
    await new Promise(r => setTimeout(r, 1200));

    let payload = null;
    let queue = [];

    // 0. Yeni Pencerede Grup Yüklemesi Sekmesi Kontrolü
    const urlParams = new URLSearchParams(window.location.search);
    const targetFromUrl = urlParams.get("yt_oto_target");
    if (targetFromUrl) {
      sessionStorage.setItem("yt_oto_target", targetFromUrl);
    }
    
    let targetId = sessionStorage.getItem("yt_oto_target");
    if (!targetId) {
      try {
        const bgResp = await new Promise(resolve => {
          chrome.runtime.sendMessage({ type: "GET_TAB_TARGET" }, resolve);
        });
        if (bgResp && bgResp.targetId) {
          targetId = bgResp.targetId;
          sessionStorage.setItem("yt_oto_target", targetId);
          console.log("[YT-OTO] 🎯 Background'dan sekme hedefi alındı:", targetId);
        }
      } catch (e) {}
    }

    if (targetId) {
      try {
        const storedGroup = await new Promise(resolve => chrome.storage.local.get(["yt_group_payloads"], resolve));
        if (storedGroup && storedGroup.yt_group_payloads) {
          const groupPayloads = storedGroup.yt_group_payloads;
          const myIndex = groupPayloads.findIndex(p => p.channel_id === targetId);
          const myPayload = myIndex >= 0 ? groupPayloads[myIndex] : null;
          if (myPayload) {
            console.log(`[YT-OTO] 📦 Grup yüklemesi - bu sekmenin hedefi (#${myIndex}): ${targetId}`);
            chrome.storage.local.remove(["yt_studio_pending"]);
            const staggerDelay = (myIndex > 0) ? (myIndex * 2500) : 0;
            setTimeout(() => {
              safeStartAutoUpload(myPayload);
            }, staggerDelay);
            return;
          }
        }
      } catch (e) {
        console.warn("[YT-OTO] Grup payload okuma hatası:", e);
      }
    }

    // 1. Chrome Local Storage'dan oku — YALNIZCA yt_studio_pending kullan
    // GÜVENLİK: yt_upload_queue[0]'ı asla doğrudan payload yapma!
    // Kuyruktan bir sonraki video ancak archiveVideoOnBackend tarafından
    // kasıtlı olarak yt_studio_pending'e yazıldıktan sonra işlenir.
    try {
      const stored = await new Promise(resolve => {
        chrome.storage.local.get(["yt_studio_pending", "yt_upload_queue"], resolve);
      });
      if (stored && stored.yt_studio_pending) {
        payload = stored.yt_studio_pending;
        queue = stored.yt_upload_queue || [];
        console.log("[YT-OTO] 📦 chrome.storage'dan bekleyen yükleme alındı:", payload.channel_name, payload.title);
      }
      // NOT: yt_upload_queue varsa ama yt_studio_pending yoksa BAŞLATMA.
      // Kuyruk yönetimi tamamen archiveVideoOnBackend'e aittir.
    } catch (e) {
      console.warn("[YT-OTO] chrome.storage reading error:", e);
    }

    // 2. Eğer chrome.storage'da yoksa doğrudan Backend API'den çek
    if (!payload) {
      try {
        const bgRes = await fetchFromBackground("http://127.0.0.1:8000/api/extension/pending-upload");
        if (bgRes && bgRes.payload) {
          payload = bgRes.payload;
          queue = bgRes.queue || [];
          console.log("[YT-OTO] 🌐 Backend API'den bekleyen video alındı:", payload.channel_name, payload.title);
          // Önce kuyruğu localStorage'a yaz, sonra backend'i temizle
          if (Array.isArray(queue) && queue.length > 0) {
            await new Promise(r => chrome.storage.local.set({ yt_upload_queue: queue }, r));
          }
          // Backend'deki bekleyeni temizle ki sayfa yenilenirse döngüye girmesin
          fetchFromBackground("http://127.0.0.1:8000/api/extension/pending-upload/clear", { method: "POST" });
        }
      } catch (e) {
        console.warn("[YT-OTO] Backend pending-upload fetch error:", e);
      }
    }

    if (!payload) {
      console.log("[YT-OTO] YouTube Studio açıldı, bekleyen otomatik yükleme görevi yok.");
      return;
    }

    // Zaman aşımı kontrolü (600 saniye = 10 dakika — hesap geçişi için yeterli süre)
    const payloadTime = payload.timestamp || Date.now();
    if (Date.now() - payloadTime > 600_000) {
      console.warn("[YT-OTO] Bekleyen yükleme süresi dolmuş, temizleniyor.");
      chrome.storage.local.remove(["yt_studio_pending"]);
      return;
    }

    console.log("[YT-OTO] 🎬 YouTube Studio otomatik yükleme başlatılıyor:", payload.channel_name, payload.title);
    await new Promise(r => chrome.storage.local.remove(["yt_studio_pending"], r));
    safeStartAutoUpload(payload);
  }

  // DOM ready olduğunda veya load olduğunda tetikle
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initStudioAutoUpload);
  } else {
    initStudioAutoUpload();
  }
}

// ── Görünürlük Yardımcısı ─────────────────────────────────────
function isVisible(el) {
  if (!el) return false;
  try {
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    
    let parent = el.parentElement || (el.parentNode && el.parentNode.host);
    while (parent && parent !== document.body) {
      if (parent.nodeType === Node.ELEMENT_NODE) {
        const pStyle = window.getComputedStyle(parent);
        if (pStyle.display === 'none' || pStyle.visibility === 'hidden') return false;
      }
      parent = parent.parentElement || (parent.parentNode && parent.parentNode.host);
    }
  } catch (e) {
    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  }
  return true;
}


// ── Background Fetch Helper (CORS & Mixed Content Bypass) ───
function fetchFromBackground(url, options = {}, asArrayBuffer = false, timeoutMs = 25000) {
  return new Promise((resolve, reject) => {
    let timer = setTimeout(() => {
      reject(new Error(`İstek zaman aşımına uğradı (${timeoutMs / 1000}s): ${url}`));
    }, timeoutMs);

    chrome.runtime.sendMessage({ type: "FETCH_API", url, options, asArrayBuffer }, (response) => {
      clearTimeout(timer);
      if (chrome.runtime.lastError) {
        const errMsg = chrome.runtime.lastError.message || "";
        if (errMsg.includes("context invalidated") || errMsg.includes("invalidated")) {
          alert("⚠️ Eklenti güncellendiği veya yeniden yüklendiği için bağlantı koptu. Lütfen sayfayı yenileyin (F5) ve işlemi tekrar başlatın.");
          reject(new Error("Extension context invalidated. Please refresh the page."));
        } else {
          reject(new Error(errMsg));
        }
        return;
      }
      if (!response) {
        reject(new Error("No response from background script"));
        return;
      }
      if (!response.ok) {
        reject(new Error(response.error || "Background fetch failed"));
        return;
      }
      // Recreate Response-like interface while keeping direct properties
      const result = {
        ok: true,
        data: response.data,
        success: response.data && response.data.success !== undefined ? response.data.success : response.success,
        added_count: response.data && response.data.added_count,
        skipped_count: response.data && response.data.skipped_count,
        added_titles: response.data && response.data.added_titles,
        skipped_titles: response.data && response.data.skipped_titles,
        json: () => Promise.resolve(response.data),
        text: () => Promise.resolve(typeof response.data === 'object' ? JSON.stringify(response.data) : response.data),
        ...response
      };
      resolve(result);
    });
  });
}

// Büyük JSON body (base64 görseller) için özel mesaj helper'ı
// body string olarak iletilir → structuredClone sınırı aşılmaz
function produceViaBackground(url, payload) {
  return new Promise((resolve, reject) => {
    const bodyStr = JSON.stringify(payload);
    chrome.runtime.sendMessage({ type: "PRODUCE_API", url, bodyStr }, (response) => {
      if (chrome.runtime.lastError) {
        const errMsg = chrome.runtime.lastError.message || "";
        if (errMsg.includes("context invalidated") || errMsg.includes("invalidated")) {
          alert("⚠️ Eklenti güncellendiği veya yeniden yüklendiği için bağlantı koptu. Lütfen sayfayı yenileyin (F5) ve işlemi tekrar başlatın.");
          reject(new Error("Extension context invalidated. Please refresh the page."));
        } else {
          reject(new Error(errMsg));
        }
        return;
      }
      if (!response) {
        reject(new Error("No response from background (PRODUCE_API)"));
        return;
      }
      if (!response.ok) {
        reject(new Error(response.error || "Produce request failed"));
        return;
      }
      resolve({
        ok: true,
        data: response.data,
        json: () => Promise.resolve(response.data),
        text: () => Promise.resolve(typeof response.data === 'object' ? JSON.stringify(response.data) : response.data),
      });
    });
  });
}


// ── Güvenilir Element Tıklama Yardımcısı (Polymer & Shadow DOM) ──
function clickElementReliably(el) {
  if (!el) return false;
  try {
    el.scrollIntoView({ block: 'center', inline: 'center' });
  } catch (e) {}

  const target = (el.shadowRoot && el.shadowRoot.querySelector('button, #button, tp-yt-paper-icon-button, [role="button"], #container')) || el;
  try { target.focus(); } catch (e) {}

  try {
    target.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, view: window }));
    target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
    target.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, view: window }));
    target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
    target.click();
  } catch (e) {
    try { el.click(); } catch (e2) {}
  }
  return true;
}

// ── Sayfa Ortasındaki "Video yükle" Butonunu Bul ───────────────
function findCenterUploadButton() {
  const uploadKeywords = [
    "video yükle", "video yukle", "yükle", "upload videos", "upload video", "upload",
    "subir vídeos", "subir videos", "subir video", "subir", "videos hochladen", "video hochladen", "hochladen",
    "importer des vidéos", "mettre en ligne", "enviar vídeos", "enviar videos", "carica video",
    "добавить видео", "загрузить видео"
  ];
  const buttons = queryShadowAll('ytcp-button, button, a, div[role="button"]');
  for (const btn of buttons) {
    const text = (btn.textContent || '').trim().toLowerCase();
    if (uploadKeywords.some(kw => text === kw || text.includes(kw))) {
      if (isVisible(btn)) return btn;
    }
  }
  return null;
}

// ── Yükleme Akışını Tetikle ──────────────────────────────────
async function triggerUploadWorkflow(maxAttempts = 20) {
  for (let i = 0; i < maxAttempts; i++) {
    // 0. Eğer yükleme diyaloğu zaten açıksa tetiklemeye gerek yok
    if (queryShadow('ytcp-uploads-dialog, ytcp-video-metadata-editor, ytcp-uploads-file-picker')) {
      console.log("[YT-OTO] ✅ Yükleme penceresi zaten açık.");
      return true;
    }

    // 1. Sayfa ortasındaki "Video yükle" butonu
    const centerBtn = findCenterUploadButton();
    if (centerBtn && isVisible(centerBtn)) {
      console.log("[YT-OTO] Sayfa ortasındaki 'Video yükle' butonu tıklandı");
      clickElementReliably(centerBtn);
      await new Promise(r => setTimeout(r, 1500));
      if (queryShadow('ytcp-uploads-dialog, ytcp-video-metadata-editor, ytcp-uploads-file-picker')) return true;
    }

    // 2. Sağ üstteki "Yükle" (Upload) butonu
    const uploadBtn = queryShadow(
      'ytcp-button[id="upload-button"], #upload-button, button[aria-label*="Upload"], button[aria-label*="Yükle"], button[aria-label*="Subir"], button[aria-label*="Hochladen"]'
    );
    if (uploadBtn && isVisible(uploadBtn)) {
      console.log("[YT-OTO] Sağ üstteki 'Yükle / Upload' butonu tıklandı");
      clickElementReliably(uploadBtn);
      await new Promise(r => setTimeout(r, 1500));
      if (queryShadow('ytcp-uploads-dialog, ytcp-video-metadata-editor, ytcp-uploads-file-picker')) return true;
    }

    // 3. Sağ üstteki "Oluştur" (Create / Crear / Erstellen) butonu
    const createBtn = queryShadow(
      'ytcp-button#create-icon, #create-icon, ytcp-button.ytcpAppHeaderCreateIcon, .ytcpAppHeaderCreateIcon, ytcp-icon-button#create-icon, button[aria-label*="Create"], button[aria-label*="Oluştur"], button[aria-label*="Crear"], button[aria-label*="Erstellen"], button[aria-label*="Créer"], [test-id="create-icon"]'
    );
    if (createBtn && isVisible(createBtn)) {
      console.log("[YT-OTO] 'Oluştur / Create / Crear' butonu tıklandı, açılır menü bekleniyor...");
      clickElementReliably(createBtn);
      await new Promise(r => setTimeout(r, 800));

      if (queryShadow('ytcp-uploads-dialog, ytcp-video-metadata-editor, ytcp-uploads-file-picker')) return true;

      const items = queryShadowAll('tp-yt-paper-item, ytd-menu-navigation-item-renderer, paper-item, a[role="menuitem"], ytcp-text-menu-item, [role="menuitem"]');
      if (items.length > 0) {
        console.log(`[YT-OTO] Açılır menüde ${items.length} seçenek bulundu.`);
        const uploadItemKeywords = [
          "video", "upload", "yükle", "subir", "hochladen", "importer", "enviar", "carica", "добавить", "загрузить"
        ];
        let clicked = false;
        for (const item of items) {
          const text = (item.textContent || '').trim().toLowerCase();
          if (uploadItemKeywords.some(kw => text.includes(kw))) {
            console.log(`[YT-OTO] Açılır menüdeki '${text}' seçeneği tıklandı`);
            clickElementReliably(item);
            clicked = true;
            break;
          }
        }
        // Eğer anahtar kelime eşleşmediyse Studio'nun 1. menü maddesi HER ZAMAN Video Yükle'dir
        if (!clicked && items[0] && isVisible(items[0])) {
          console.log("[YT-OTO] 1. sıradaki menü maddesi varsayılan olarak tıklandı.");
          clickElementReliably(items[0]);
        }
        await new Promise(r => setTimeout(r, 1500));
        if (queryShadow('ytcp-uploads-dialog, ytcp-video-metadata-editor, ytcp-uploads-file-picker')) return true;
      }
    }

    console.log(`[YT-OTO] Yükleme butonu aranıyor (Deneme ${i + 1}/${maxAttempts})...`);
    await new Promise(r => setTimeout(r, 1000));
  }

  return !!queryShadow('ytcp-uploads-dialog, ytcp-video-metadata-editor, ytcp-uploads-file-picker');
}

// ── Upload Sayfasına Yönlendirme ve Polling ────────────────────
function waitForUpload(payload, attempts = 0) {
  if (attempts > 30) {
    console.warn("[YT-OTO] Yükleme butonu 30 saniye boyunca bulunamadı.");
    return;
  }

  const triggered = triggerUploadWorkflow();
  if (triggered) {
    waitAndFill(payload);
  } else {
    // Bulamazsa 1 saniye sonra tekrar dene
    setTimeout(() => waitForUpload(payload, attempts + 1), 1000);
  }
}

// ── Form Doldurma Tetikleyicisi ──────────────────────────────
function fillStudioForm(payload) {
  waitAndFill(payload);
}

// ── Form Elemanlarını Bekle ve Doldur ────────────────────────
function waitAndFill(payload, attempt = 0) {
  if (attempt > 90) { // En fazla 90 saniye bekle
    console.warn("[YT-OTO] Doldurulacak form elemanları bulunamadı (Zaman aşımı).");
    removeFloatingInstruction();
    return;
  }

  const titleEl = findTitleInput();
  if (!titleEl) {
    showFloatingInstruction(payload.video_path);
    setTimeout(() => waitAndFill(payload, attempt + 1), 1000);
    return;
  }

  removeFloatingInstruction();
  fillForm(payload);
  chrome.storage.local.remove(["yt_studio_pending"]);
  showNotification("✅ Metadata dolduruldu! Kontrol edip yayımlayabilirsiniz.");
}

// ── Yönlendirici Bilgi Kartı Göster ──────────────────────────
function showFloatingInstruction(videoPath, customText = "") {
  let box = document.getElementById("yt-oto-instruction-box");
  if (!box) {
    box = document.createElement("div");
    box.id = "yt-oto-instruction-box";
    box.style.cssText = `
      position: fixed; top: 12px; left: 50%; transform: translateX(-50%);
      z-index: 1000000; background: rgba(30, 41, 59, 0.95); color: #e2e8f0;
      border: 2px solid #6366f1; border-radius: 12px;
      padding: 16px 24px; font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 13.5px; box-shadow: 0 10px 40px rgba(0,0,0,0.6);
      max-width: 550px; text-align: center;
      backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
      animation: pulseBorder 2.2s infinite;
    `;
    document.body.appendChild(box);
  }
  
  box.innerHTML = `
    <div style="font-weight: 700; font-size: 15px; margin-bottom: 6px; color: #a5b4fc;">⚡ Otomatik Yükleme Devrede</div>
    <div style="margin-bottom: 10px; line-height: 1.5; color: #cbd5e1;">
      ${customText || "Lütfen video dosyasını seçin. Dosya yolu panonuza kopyalanmıştır."}
    </div>
    <div style="background: rgba(15, 23, 42, 0.5); padding: 8px 12px; border-radius: 6px; font-family: monospace; font-size: 11.5px; word-break: break-all; border: 1px solid #4338ca; color: #c7d2fe;">
      ${videoPath}
    </div>
  `;

  if (!document.getElementById("yt-oto-instruction-style")) {
    const style = document.createElement("style");
    style.id = "yt-oto-instruction-style";
    style.textContent = `
      @keyframes pulseBorder {
        0% { border-color: #6366f1; box-shadow: 0 10px 30px rgba(99,102,241,0.25); }
        50% { border-color: #a5b4fc; box-shadow: 0 10px 30px rgba(99,102,241,0.5); }
        100% { border-color: #6366f1; box-shadow: 0 10px 30px rgba(99,102,241,0.25); }
      }
    `;
    document.head.appendChild(style);
  }
}

function removeFloatingInstruction() {
  const box = document.getElementById("yt-oto-instruction-box");
  if (box) box.remove();
  const style = document.getElementById("yt-oto-instruction-style");
  if (style) style.remove();
}

// ── Title input'u bul (Shadow DOM uyumlu) ─────────────────────
function findTitleInput() {
  // 1. Önce title container'ı bul, sonra içindeki textbox'ı al
  const titleContainer = queryShadow('#title-textarea') || 
                         queryShadow('ytcp-social-suggestions-textbox[id*="title"]') ||
                         queryShadow('ytcp-mention-input[id*="title"]') ||
                         queryShadow('ytcp-video-metadata-editor-basics #title-textarea');
  if (titleContainer) {
    const el = queryShadow('#textbox, div[contenteditable="true"], [contenteditable="true"]', titleContainer);
    if (el && isVisible(el)) return el;
  }

  // 2. Fallback: aria-label veya diğer doğrudan seçiciler
  const fallbackSelectors = [
    '#title-textarea [contenteditable="true"]',
    'div[contenteditable="true"][aria-label*="title" i]',
    'div[contenteditable="true"][aria-label*="başlık" i]',
    'div[contenteditable="true"][aria-label*="título" i]',
    'div[contenteditable="true"][aria-label*="titel" i]',
    'ytcp-video-metadata-editor-sidepanel div[contenteditable][id*="title"]',
    '#textbox[contenteditable="true"]'
  ];
  for (const sel of fallbackSelectors) {
    const el = queryShadow(sel);
    if (el && isVisible(el)) return el;
  }
  return null;
}

// ── Description input'u bul (Shadow DOM uyumlu) ───────────────
function findDescInput() {
  // 1. Önce description container'ı bul, sonra içindeki textbox'ı al
  const descContainer = queryShadow('#description-textarea') || 
                        queryShadow('ytcp-video-description') ||
                        queryShadow('ytcp-social-suggestions-textbox[id*="description"]') ||
                        queryShadow('#description-container') ||
                        queryShadow('ytcp-video-metadata-editor-basics #description-textarea');
  if (descContainer) {
    const el = queryShadow('#textbox, div[contenteditable="true"], [contenteditable="true"]', descContainer);
    if (el && isVisible(el)) return el;
  }

  // 2. Fallback: Açıklama alanına özgü aria-label / placeholder'lar (çok dilli)
  const fallbackSelectors = [
    '#description-textarea [contenteditable="true"]',
    'div[contenteditable="true"][aria-label*="description" i]',
    'div[contenteditable="true"][aria-label*="açıklama" i]',
    'div[contenteditable="true"][aria-label*="bahsedin" i]', // "İzleyicilere videonuzdan bahsedin" (TR)
    'div[contenteditable="true"][aria-label*="tell viewers" i]', // "Tell viewers about your video" (EN)
    'div[contenteditable="true"][aria-label*="hable sobre" i]',
    'div[contenteditable="true"][aria-label*="beschreiben" i]'
  ];
  for (const sel of fallbackSelectors) {
    const el = queryShadow(sel);
    if (el && isVisible(el)) return el;
  }
  return null;
}

// ── Tag input'u bul (Shadow DOM uyumlu) ────────────────────────
function findTagsInput() {
  // 1. Önce tags container / chip bar'ı bul, sonra içindeki input'u al
  const tagsContainer = queryShadow('#tags-container') || 
                        queryShadow('ytcp-chip-bar#chip-bar') ||
                        queryShadow('ytcp-chip-bar') ||
                        queryShadow('ytcp-form-input-container#tags-container') ||
                        queryShadow('ytcp-video-metadata-editor-advanced #tags-container');
  if (tagsContainer) {
    const el = queryShadow('#text-input, input[type="text"], input', tagsContainer);
    if (el && isVisible(el)) return el;
  }

  // 2. Fallback: aria-label ile doğrudan arama
  const fallbackSelectors = [
    'input[aria-label*="etiket" i]',
    'input[aria-label*="tag" i]',
    'input[aria-label*="tags" i]',
    'input[aria-label*="balise" i]',
    'input[aria-label*="tegs" i]'
  ];
  for (const sel of fallbackSelectors) {
    const el = queryShadow(sel);
    if (el && isVisible(el)) return el;
  }
  return null;
}

// ── Input'a değer yaz ─────────────────────────────────────────
function setContentEditable(el, text) {
  if (!el) return;
  el.focus();
  
  // Seçimi temizle ve bu elemanı seç
  try {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(el);
    selection.removeAllRanges();
    selection.addRange(range);
  } catch (e) {
    console.warn("[YT-OTO] Seçim oluşturulamadı:", e);
  }

  let success = false;
  try {
    success = document.execCommand("insertText", false, text);
  } catch (e) {
    console.error("[YT-OTO] execCommand insertText hatası:", e);
  }

  if (!success || !el.textContent || el.textContent.trim() === "") {
    console.log("[YT-OTO] execCommand başarısız, doğrudan text ataması yapılıyor.");
    try {
      el.textContent = text;
    } catch (e) {
      el.innerText = text;
    }
  }

  el.dispatchEvent(new InputEvent("input", { bubbles: true, cancelable: true, inputType: "insertText", data: text }));
  el.dispatchEvent(new Event("input", { bubbles: true, cancelable: true }));
  el.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
}

// ── Daha Fazla Göster Butonunu Tıkla (Etiketler vb. için) ──────
function expandMoreOptions() {
  const allToggleButtons = queryShadowAll('ytcp-button#toggle-button, #toggle-button, ytcp-button.ytcpVideoMetadataEditorAdvancedToggleButton');
  for (const toggleBtn of allToggleButtons) {
    const text = (toggleBtn.textContent || '').trim().toLowerCase();
    const lessKeywords = ["daha az", "show less", "mostrar menos", "weniger anzeigen", "moins"];
    if (lessKeywords.some(kw => text.includes(kw))) {
      console.log("[YT-OTO] 'Daha fazla göster' zaten açık.");
      return true;
    }
    const moreKeywords = ["daha fazla", "show more", "mostrar más", "mostrar mas", "mehr anzeigen", "plus", "mostrar mais", "развернуть"];
    if (moreKeywords.some(kw => text.includes(kw))) {
      clickElementReliably(toggleBtn);
      console.log("[YT-OTO] 'Daha fazla göster / Show more' tıklandı.");
      return true;
    }
  }
  return false;
}

// ── Tag ekleme (YouTube Algoritma & Spam Koruma Filtreli) ────────
async function addTags(tags) {
  if (!tags || tags.length === 0) return;
  const tagInput = findTagsInput();
  if (!tagInput) {
    console.warn("[YT-OTO] Etiket giriş alanı bulunamadı.");
    return;
  }

  // YouTube Algoritma Kuralı: Kanala zarar veren, alakasız kitle çeken jenerik/spam etiket kara listesi
  const FORBIDDEN_SPAM_TAGS = new Set([
    "shorts", "short", "viral", "trend", "trending", "kesfet", "keşfet",
    "kesfetteyiz", "keşfetteyiz", "fyp", "foryou", "foryoupage", "video",
    "reels", "tiktok", "akim", "akım", "explore"
  ]);

  console.log("[YT-OTO] Etiketler analiz ediliyor ve filtreleniyor:", tags);
  tagInput.focus();

  // Her etiketi tek tek doğrula ve ekle
  let addedCount = 0;
  for (const tag of tags) {
    let cleanTag = String(tag || "").trim().replace(/,/g, "");
    if (!cleanTag) continue;

    // Etiket başında hashtag varsa temizle
    cleanTag = cleanTag.replace(/^#+/, "").trim();
    const normalized = cleanTag.toLowerCase().replace(/\s+/g, "");

    // Kara listedeki jenerik/spam kelimeleri engelle
    if (FORBIDDEN_SPAM_TAGS.has(normalized) || cleanTag.length < 2) {
      console.log(`[YT-OTO] 🛡️ Algoritma koruması: Jenerik/spam etiket engellendi -> '${cleanTag}'`);
      continue;
    }

    tagInput.focus();

    // 1. execCommand insertText (YouTube Studio Polymer/Lit input handler'ını tetikler)
    let inserted = false;
    try {
      inserted = document.execCommand("insertText", false, cleanTag + ",");
    } catch (e) {}

    if (!inserted) {
      tagInput.value = cleanTag;
      tagInput.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: cleanTag }));
      tagInput.dispatchEvent(new Event("input", { bubbles: true }));
      tagInput.dispatchEvent(new Event("change", { bubbles: true }));
      tagInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }));
      tagInput.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }));
    }
    addedCount++;
    await new Promise(r => setTimeout(r, 120));
  }
  console.log(`[YT-OTO] Toplam ${addedCount} adet niş ve kaliteli etiket eklendi.`);
}

// ── Yerelleştirilmiş Açıklama ve Etiket Üretici (Spamsiz, Niş & Doğal SEO Odaklı) ──
function getLocalizedMetadataFallback(title, language, category) {
  const lang = String(language || "tr").toLowerCase().trim();
  const cat = String(category || "reddit_stories").toLowerCase().trim();
  const cleanTitle = String(title || "Shorts").trim();

  let desc = "";
  let tags = [];

  if (cat.includes("reddit")) {
    if (lang === "en") {
      desc = `${cleanTitle}\n\nUnbelievable Reddit confessions, true mysteries, and captivating life stories revealed in this deep dive! What would you have done in this situation? Let us know in the comments below! 👇\n\nDon't forget to like, subscribe, and hit the bell for authentic daily Reddit stories! 🔔\n\n#Reddit #RedditStories #AskReddit #Storytime #RedditConfessions #AITAH #TrueStories`;
      tags = ["Reddit", "RedditStories", "AskReddit", "Storytime", "RedditConfessions", "AITAH", "TrueStories", "Confessions", "LifeStories"];
    } else if (lang === "de") {
      desc = `${cleanTitle}\n\nUnglaubliche Reddit-Geschichten, Beichten und spannende Erlebnisse direkt aus der Community! Was hättest du in dieser Situation getan? Schreib es in die Kommentare! 👇\n\nVergiss nicht zu abonnieren und die Glocke zu aktivieren für tägliche Geschichten! 🔔\n\n#Reddit #RedditGeschichten #AskRedditDeutsch #Geschichten #Beichte #Storytime`;
      tags = ["Reddit", "RedditGeschichten", "AskRedditDeutsch", "Geschichten", "Beichte", "Erlebnisse", "Storytime"];
    } else if (lang === "es") {
      desc = `${cleanTitle}\n\n¡Historias increíbles de Reddit, confesiones y anécdotas impactantes de la vida real! ¿Qué habrías hecho tú en esta situación? ¡Cuéntanos en los comentarios! 👇\n\n¡No olvides suscribirte y activar la campanita para más historias auténticas! 🔔\n\n#Reddit #HistoriasDeReddit #AskRedditEspanol #Historias #Confesiones #Relatos`;
      tags = ["Reddit", "HistoriasDeReddit", "AskRedditEspanol", "Historias", "Confesiones", "Relatos", "Storytime"];
    } else if (lang === "fr") {
      desc = `${cleanTitle}\n\nHistoires incroyables de Reddit, confessions et mystères captivants de la communauté! Qu'auriez-vous fait dans cette situation? Dites-le nous en commentaire! 👇\n\nN'oubliez pas de vous abonner et d'activer la cloche pour ne rien manquer! 🔔\n\n#Reddit #HistoiresReddit #AskRedditFR #Histoires #Confessions #Mystere`;
      tags = ["Reddit", "HistoiresReddit", "AskRedditFR", "Histoires", "Confessions", "Temoignage"];
    } else {
      desc = `${cleanTitle}\n\nEn popüler Reddit itirafları, gizemli sırlar ve gerçek hayat hikayeleri bu anlatımda bir araya geliyor! Siz bu durumda kalsaydınız nasıl bir tepki verirdiniz? Yorumlarda buluşalım! 👇\n\nDaha fazla sürükleyici Reddit hikayesi ve itiraf için abone olmayı ve bildirimleri açmayı unutmayın! 🔔\n\n#Reddit #RedditHikayeleri #AskReddit #RedditTR #İtiraflar #GerçekHikayeler #HikayeZamanı`;
      tags = ["Reddit", "RedditHikayeleri", "AskReddit", "RedditTR", "İtiraflar", "GerçekHikayeler", "HikayeZamanı", "YaşanmışOlaylar", "AileSırları"];
    }
  } else if (cat.includes("whatsapp")) {
    if (lang === "en") {
      desc = `${cleanTitle}\n\nHilarious text messages and funny chat stories that went completely off the rails! Send this to someone who texts like this 😂👇\n\nDon't forget to like, subscribe, and turn on notifications for daily comedy! 🔔\n\n#TextStory #FunnyTexts #ChatStory #Comedy #Humor #WhatsApp`;
      tags = ["TextStory", "FunnyTexts", "ChatStory", "Comedy", "Humor", "WhatsAppStories", "FunnyMessages"];
    } else if (lang === "de") {
      desc = `${cleanTitle}\n\nLustige WhatsApp-Chats und humorvolle Momente aus dem echten Leben! Teile das mit deinen Freunden 😂👇\n\nAbonniere den Kanal und aktiviere die Glocke für mehr Unterhaltung! 🔔\n\n#WhatsApp #Lustig #Humor #Komödie #ChatGeschichten`;
      tags = ["WhatsApp", "Lustig", "Humor", "Komödie", "ChatGeschichten", "Nachrichten"];
    } else if (lang === "es") {
      desc = `${cleanTitle}\n\n¡Mensajes divertidos de WhatsApp y momentos cómicos inolvidables! Compártelo con ese amigo que siempre responde así 😂👇\n\n¡Suscríbete y activa la campanita para más comedia diaria! 🔔\n\n#WhatsApp #Comedia #Humor #MensajesDivertidos #ChatStories`;
      tags = ["WhatsApp", "Comedia", "Humor", "MensajesDivertidos", "ChatStories", "HistoriasDeChat"];
    } else {
      desc = `${cleanTitle}\n\nGülmekten kırıp geçiren özgün WhatsApp sohbetleri ve eğlenceli diyaloglar! Bu durumu yaşayan arkadaşına göndermeyi unutma 😂👇\n\nAbone olmayı ve bildirim ziline basmayı unutmayın! 🔔\n\n#WhatsApp #Diyalog #Seslendirme #Dublaj #Komedi #Mizah #Eğlence`;
      tags = ["konuşma", "diyalog", "seslendirme", "türkçe dublaj", "whatsapp", "komik", "mizah", "mesaj hikayeleri", "eğlenceli sohbet"];
    }
  } else {
    if (lang === "en") {
      desc = `${cleanTitle}\n\nDetailed breakdown and authentic documentary insights on this topic. Don't forget to like, subscribe, and turn on notifications for more deep-dive investigations! 🔔\n\n#Documentary #Education #Investigation #DeepDive`;
      tags = ["Documentary", "Education", "Investigation", "DeepDive", "Knowledge"];
    } else if (lang === "de") {
      desc = `${cleanTitle}\n\nDetaillierte Dokumentation und faszinierende Einblicke in dieses Thema. Abonniere den Kanal und aktiviere die Glocke für weitere Videos! 🔔\n\n#Dokumentation #Bildung #Wissen #Recherche`;
      tags = ["Dokumentation", "Bildung", "Wissen", "Recherche", "Hintergrund"];
    } else if (lang === "es") {
      desc = `${cleanTitle}\n\nAnálisis detallado e investigación profunda sobre este tema fascinante. ¡Suscríbete y activa las notificaciones para más contenido documental! 🔔\n\n#Documental #Educación #Investigación #Historia`;
      tags = ["Documental", "Educación", "Investigación", "Historia", "Conocimiento"];
    } else {
      desc = `${cleanTitle}\n\nBu konunun tüm detayları, arka planı ve derinlemesine incelemesi bu videoda! Daha fazla eğitici ve sürükleyici içerik için abone olmayı ve bildirimleri açmayı unutmayın! 🔔\n\n#Belgesel #İnceleme #Eğitim #Bilgi`;
      tags = ["Belgesel", "İnceleme", "Eğitim", "Bilgi", "DetaylıAnaliz"];
    }
  }
  return { desc, tags };
}

function isBogusMetadataFallback(desc, tags, language, category) {
  const descStr = String(desc || "");
  const tagsStr = Array.isArray(tags) ? tags.join(" ") : String(tags || "");
  const lang = String(language || "tr").toLowerCase().trim();
  const cat = String(category || "reddit_stories").toLowerCase().trim();

  if (!cat.includes("whatsapp")) {
    if (descStr.includes("WhatsApp") || descStr.includes("Gülmekten kırıp geçiren")) return true;
    if (tagsStr.includes("BiDublaj") || tagsStr.includes("WhatsApp")) return true;
  }
  if (lang !== "tr") {
    if (descStr.includes("Gülmekten kırıp geçiren") || descStr.includes("abone olmayı unutmayın") || descStr.includes("daha fazla video")) return true;
    if (tagsStr.includes("Komedi") || tagsStr.includes("Mizah") || tagsStr.includes("BiDublaj") || tagsStr.includes("Gülmekten")) return true;
  }
  return false;
}

// ── Ana form doldurma (async — description ve tag için DOM bekler) ───────────
async function fillForm(payload) {
  const plLang = payload.language || "tr";
  const plCat = payload.category || (payload.folder && payload.folder.includes("whatsapp") ? "whatsapp_stories" : "reddit_stories");

  // 1. Başlık
  const titleEl = findTitleInput();
  if (titleEl && payload.title) {
    setContentEditable(titleEl, payload.title.slice(0, 100));
    console.log("[YT-OTO] Başlık dolduruldu:", payload.title);
  }

  // 2. Açıklama & 3. Etiketler — dile ve kategoriye duyarlı
  let descriptionText = (payload.description || "").trim();
  let tagsList = Array.isArray(payload.tags) && payload.tags.length > 0 ? payload.tags : null;
  if (!tagsList && payload.keywords && Array.isArray(payload.keywords) && payload.keywords.length > 0) {
    tagsList = payload.keywords;
  }

  if (!descriptionText || !tagsList || isBogusMetadataFallback(descriptionText, tagsList, plLang, plCat)) {
    const loc = getLocalizedMetadataFallback(payload.title, plLang, plCat);
    if (!descriptionText || isBogusMetadataFallback(descriptionText, [], plLang, plCat)) {
      descriptionText = loc.desc;
      console.log(`[YT-OTO] Açıklama yerelleştirildi (${plLang}, ${plCat}):`, descriptionText);
    }
    if (!tagsList || isBogusMetadataFallback("", tagsList, plLang, plCat)) {
      tagsList = loc.tags;
      console.log(`[YT-OTO] Etiketler yerelleştirildi (${plLang}, ${plCat}):`, tagsList);
    }
  }

  let descEl = findDescInput();
  if (!descEl) {
    for (let i = 0; i < 15; i++) {
      await new Promise(r => setTimeout(r, 400));
      descEl = findDescInput();
      if (descEl) break;
    }
  }
  if (descEl) {
    setContentEditable(descEl, descriptionText.slice(0, 5000));
    console.log("[YT-OTO] Açıklama başarıyla dolduruldu.");
  } else {
    console.warn("[YT-OTO] Açıklama alanı 6sn içinde bulunamadı.");
  }

  // 'Daha fazla göster' butonunu aç ve etiket alanını bekle
  expandMoreOptions();

  let tagInput = null;
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 400));
    tagInput = findTagsInput();
    if (tagInput) break;
    if (i === 3 || i === 8 || i === 14) expandMoreOptions();
  }

  if (tagInput) {
    await addTags(tagsList);
  } else {
    console.warn("[YT-OTO] Etiket giriş alanı 8sn içinde bulunamadı.");
  }

  // 4. Çocuklara Özel Seçeneği (Ayrıntılar adımı)
  selectMadeForKidsOption(payload._kidsRating || "VIDEO_MADE_FOR_KIDS_NOT_MFK");
}



// ── Adımları Otomatik İlerletme (Details → Elements → Checks → Visibility) ──
// Her adımdan önce: yükleme %100 olmuş mu ve buton aktif mi diye bekler.
function autoNavigateSteps() {
  console.log("[YT-OTO] Otomatik adım ilerletme başlatıldı...");

  let stepAttempts = 0;
  const MAX_WAIT_PER_STEP = 300; // 300 × 1sn = max 5 dakika bekleme

  function isUploadComplete() {
    // ytcp-video-upload-progress bileşenini ara
    const progressEl = queryShadow('ytcp-video-upload-progress');
    if (progressEl) {
      // "Upload complete" ya da benzeri metin içeriyorsa tamam
      const text = progressEl.textContent.toLowerCase();
      if (text.includes("upload complete") || text.includes("yükleme tamamlandı") ||
          text.includes("processing") || text.includes("işleniyor") ||
          text.includes("100%")) {
        return true;
      }
    }
    // progress-bar doluluk kontrolü
    const bar = queryShadow('ytcp-video-upload-progress tp-yt-paper-progress, ytcp-linear-progress');
    if (bar) {
      const value = parseFloat(bar.getAttribute('value') || bar.style.width || '0');
      if (value >= 100) return true;
    }
    // Eğer hiç progress element yoksa (upload zaten bittiyse) devam et
    const dialog = queryShadow('ytcp-uploads-dialog');
    if (!dialog) return false;
    const hasProgress = queryShadow('ytcp-video-upload-progress');
    if (!hasProgress) return true; // element yok = upload tamamlandı, geçildi
    return false;
  }

  function isNextButtonReady() {
    const nextBtn = queryShadow('#next-button');
    if (!nextBtn || !isVisible(nextBtn)) return false;
    if (nextBtn.hasAttribute('disabled')) return false;
    if (nextBtn.getAttribute('aria-disabled') === 'true') return false;
    return true;
  }

  function tryStep() {
    // Dialog kapandıysa dur
    const dialog = queryShadow('ytcp-uploads-dialog');
    if (!dialog) {
      console.log("[YT-OTO] Yükleme ekranı kapandı.");
      return;
    }

    // Son adım (Görünürlük) geldiyse dur
    const doneBtn = queryShadow('#done-button');
    if (doneBtn && isVisible(doneBtn)) {
      console.log("[YT-OTO] ✅ Son adıma (Görünürlük) ulaşıldı. Kullanıcıya bırakıldı.");
      showNotification("✅ Tüm adımlar tamamlandı! Görünürlük ayarını yapıp yayımlayabilirsiniz.");
      return;
    }

    // Zaman aşımı kontrolü
    if (stepAttempts > MAX_WAIT_PER_STEP) {
      console.warn("[YT-OTO] Adım bekleme zaman aşımı.");
      showNotification("⚠️ YouTube işleme süresi aşıldı. Lütfen devam etmek için manuel tıklayın.");
      return;
    }

    // Çocuklara özel seçeneği (MFK)
    selectMadeForKidsOption("VIDEO_MADE_FOR_KIDS_NOT_MFK");

    // Yükleme tamamlanmadan ve buton hazır olmadan İleri'ye basma
    if (!isUploadComplete()) {
      stepAttempts++;
      console.log(`[YT-OTO] Video işleniyor, bekleniyor... (${stepAttempts}/${MAX_WAIT_PER_STEP})`);
      showFloatingInstruction("", `Video YouTube'a yükleniyor ve işleniyor... Lütfen bekleyin. (${stepAttempts}s)`);
      setTimeout(tryStep, 1000);
      return;
    }

    if (!isNextButtonReady()) {
      stepAttempts++;
      console.log(`[YT-OTO] İleri butonu henüz hazır değil, bekleniyor... (${stepAttempts})`);
      setTimeout(tryStep, 1000);
      return;
    }

    // Her şey hazır — adımı geç
    removeFloatingInstruction();
    stepAttempts = 0; // Sonraki adım için sayacı sıfırla
    const nextBtn = queryShadow('#next-button');
    nextBtn.click();
    console.log("[YT-OTO] ▶ 'İleri' butonuna tıklandı, sonraki adım bekleniyor...");

    // Sonraki adım için bekle (YouTube'un render etmesi için 1.5sn)
    setTimeout(tryStep, 1500);
  }

  // İlk adımı başlat
  setTimeout(tryStep, 3000); // Metadata doldurmaya 3sn süre ver
}



// ── Bildirim banner'ı ─────────────────────────────────────────
function showNotification(msg) {
  const existing = document.getElementById("yt-oto-banner");
  if (existing) existing.remove();

  const banner = document.createElement("div");
  banner.id = "yt-oto-banner";
  banner.style.cssText = `
    position: fixed; top: 20px; right: 20px; z-index: 9999999;
    background: #1e293b; color: #34d399;
    border: 1px solid rgba(52,211,153,0.3);
    border-radius: 10px; padding: 12px 18px;
    font-family: -apple-system, sans-serif; font-size: 13px; font-weight: 600;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    animation: slideIn 0.3s ease;
  `;
  banner.textContent = msg;

  const style = document.createElement("style");
  style.textContent = `
    @keyframes slideIn {
      from { opacity: 0; transform: translateY(-10px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  `;
  document.head.appendChild(style);
  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 6000);
}

// ═══════════════════════════════════════════════════════════════
// ⚡ OTO YÜKLE YENİ GELİŞMİŞ ÖZELLİKLERİ
// ═══════════════════════════════════════════════════════════════

// ── YouTube Studio Kanal Ayarları ve Buton Yönetimi ──────────

function isStudioContentTab() {
  if (!location.href.includes("studio.youtube.com")) return false;
  const path = (location.pathname || "").toLowerCase();
  const hash = (location.hash || "").toLowerCase();
  if (path.includes("/videos") || path.includes("/content") || hash.includes("/videos") || hash.includes("/content")) {
    return true;
  }
  // Alternatif DOM kontrolü (Videolar sekmesi yüklü mü?)
  if (queryShadow('ytcp-video-section, ytcp-content-section, #video-list, ytcp-video-list, ytcp-video-row')) {
    return true;
  }
  return false;
}

function removeOldButtons() {
  const headerBtn = document.getElementById("yt-oto-header-btn");
  if (headerBtn) headerBtn.remove();
  const fab = document.getElementById("yt-oto-fab");
  if (fab) fab.remove();
  const scrapeFab = document.getElementById("yt-oto-scrape-fab");
  if (scrapeFab) scrapeFab.remove();
}

function removeStudioContentActions() {
  const container = document.getElementById("yt-oto-content-actions");
  if (container) container.remove();
  const oldCenter = document.getElementById("yt-oto-center-btn");
  if (oldCenter && !oldCenter.closest("#yt-oto-content-actions")) oldCenter.remove();
}

function getActiveStudioChannelId() {
  const m = window.location.pathname.match(/\/channel\/([^\/]+)/);
  if (m && m[1]) return m[1];
  try {
    if (window.yt && window.yt.config_ && window.yt.config_.CHANNEL_ID) {
      return window.yt.config_.CHANNEL_ID;
    }
  } catch (e) {}
  const name = resolveActiveChannelName();
  if (name) return name.toLowerCase().replace(/[^a-z0-9]/g, '_');
  return "default_channel";
}

async function getChannelSettings(channelId) {
  const cid = channelId || getActiveStudioChannelId();
  const key = `yt_studio_settings_${cid}`;
  return new Promise(resolve => {
    chrome.storage.local.get([key, "yt_studio_settings_default"], res => {
      const saved = res[key] || res["yt_studio_settings_default"] || {};
      const merged = {
        dailyCount: saved.dailyCount !== undefined ? parseInt(saved.dailyCount, 10) : 3,
        publishHours: Array.isArray(saved.publishHours) && saved.publishHours.length > 0 ? saved.publishHours : ["14:00", "18:00", "21:00"],
        kidsRating: saved.kidsRating || "VIDEO_MADE_FOR_KIDS_NOT_MFK"
      };
      resolve(merged);
    });
  });
}

async function saveChannelSettings(channelId, settings) {
  const cid = channelId || getActiveStudioChannelId();
  const key = `yt_studio_settings_${cid}`;
  return new Promise(resolve => {
    chrome.storage.local.set({ [key]: settings, yt_studio_settings_default: settings }, () => {
      console.log(`[YT-OTO] ✅ Kanal ayarları kaydedildi (${key}):`, settings);
      resolve(true);
    });
  });
}

// ── Kanal Yükleme Ayarları Modalı ──────────────────────────────
async function openChannelUploadSettingsModal() {
  const existingModal = document.getElementById("yt-oto-channel-settings-modal");
  if (existingModal) existingModal.remove();

  const channelId = getActiveStudioChannelId();
  const channelName = resolveActiveChannelName() || channelId;
  const currentSettings = await getChannelSettings(channelId);

  const modal = document.createElement("div");
  modal.id = "yt-oto-channel-settings-modal";
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    z-index: 10000005; background: rgba(15, 23, 42, 0.7);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    display: flex; align-items: center; justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  const container = document.createElement("div");
  container.style.cssText = `
    background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px; width: 520px; max-width: 92%; max-height: 85vh;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
    color: #f8fafc; display: flex; flex-direction: column; overflow: hidden;
  `;

  // Render Time Inputs Helper
  let currentHours = [...currentSettings.publishHours];
  let currentCount = currentSettings.dailyCount || currentHours.length || 3;

  const renderHoursList = () => {
    const listEl = container.querySelector("#yt-setting-hours-list");
    if (!listEl) return;
    listEl.innerHTML = currentHours.map((h, idx) => `
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span style="font-size: 12px; color: #94a3b8; font-weight: 600; width: 50px;">Slot ${idx + 1}:</span>
        <input type="time" class="yt-setting-time-input" data-index="${idx}" value="${h}" style="
          background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc;
          border-radius: 6px; padding: 6px 12px; font-size: 13.5px; font-weight: 600; font-family: monospace; outline: none;
        " />
        <button type="button" class="yt-setting-remove-hour-btn" data-index="${idx}" style="
          background: none; border: none; color: #ef4444; font-size: 16px; cursor: pointer; padding: 4px;
        " title="Bu saati kaldır">&times;</button>
      </div>
    `).join("");

    // Bind time changes
    listEl.querySelectorAll(".yt-setting-time-input").forEach(input => {
      input.addEventListener("change", (e) => {
        const idx = parseInt(e.target.dataset.index, 10);
        currentHours[idx] = e.target.value;
      });
    });

    // Bind remove buttons
    listEl.querySelectorAll(".yt-setting-remove-hour-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt(e.currentTarget.dataset.index, 10);
        currentHours.splice(idx, 1);
        currentCount = currentHours.length;
        const countInput = container.querySelector("#yt-setting-daily-count");
        if (countInput) countInput.value = currentCount;
        renderHoursList();
      });
    });
  };

  container.innerHTML = `
    <!-- Header -->
    <div style="padding: 18px 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between; align-items: center;">
      <div>
        <div style="font-weight: 700; font-size: 16px; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
          <span>⚙️</span> Kanal Yükleme & Planlama Ayarları
        </div>
        <div style="font-size: 11.5px; color: #94a3b8; margin-top: 4px;">
          Aktif Kanal: <strong style="color: #38bdf8;">${channelName}</strong> <span style="color: #64748b;">(${channelId})</span>
        </div>
      </div>
      <button id="yt-setting-modal-close" style="background: none; border: none; color: #94a3b8; font-size: 24px; cursor: pointer; line-height: 1;">&times;</button>
    </div>

    <!-- Body -->
    <div style="padding: 20px 24px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 20px;">
      <!-- 1. Günlük Video Sayısı -->
      <div>
        <label style="display: block; font-size: 13px; font-weight: 600; color: #e2e8f0; margin-bottom: 6px;">
          📅 Günlük Yayınlanacak Video Sayısı:
        </label>
        <div style="display: flex; align-items: center; gap: 12px;">
          <input type="number" id="yt-setting-daily-count" min="1" max="24" value="${currentCount}" style="
            background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc;
            border-radius: 8px; padding: 8px 12px; font-size: 14px; font-weight: 700; width: 90px; outline: none;
          " />
          <span style="font-size: 12px; color: #94a3b8;">video / gün</span>
          <button type="button" id="yt-setting-sync-hours-btn" style="
            background: rgba(2, 132, 199, 0.15); border: 1px solid rgba(2, 132, 199, 0.4);
            color: #38bdf8; border-radius: 6px; padding: 6px 12px; font-size: 11.5px; font-weight: 600; cursor: pointer;
          ">⚡ Saatleri Eşitle</button>
        </div>
      </div>

      <!-- 2. Yayın Saatleri -->
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <label style="font-size: 13px; font-weight: 600; color: #e2e8f0;">
            ⏰ Yayın Saatleri (Günlük Slotlar):
          </label>
          <button type="button" id="yt-setting-add-hour-btn" style="
            background: none; border: none; color: #38bdf8; font-size: 12px; font-weight: 600; cursor: pointer;
          ">+ Saat Ekle</button>
        </div>
        <div id="yt-setting-hours-list" style="background: rgba(15, 23, 42, 0.5); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px;"></div>
      </div>

      <!-- 3. Çocuklara Özel Seçeneği -->
      <div>
        <label style="display: block; font-size: 13px; font-weight: 600; color: #e2e8f0; margin-bottom: 8px;">
          👶 Çocuklara Özel Ayarı (Made for Kids):
        </label>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <label style="
            display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border-radius: 8px;
            background: ${currentSettings.kidsRating === 'VIDEO_MADE_FOR_KIDS_NOT_MFK' ? 'rgba(2, 132, 199, 0.12)' : 'rgba(255, 255, 255, 0.03)'};
            border: 1px solid ${currentSettings.kidsRating === 'VIDEO_MADE_FOR_KIDS_NOT_MFK' ? '#0284c7' : 'rgba(255, 255, 255, 0.08)'};
            cursor: pointer;
          ">
            <input type="radio" name="yt-setting-kids" value="VIDEO_MADE_FOR_KIDS_NOT_MFK" ${currentSettings.kidsRating === 'VIDEO_MADE_FOR_KIDS_NOT_MFK' ? 'checked' : ''} style="margin-top: 3px; accent-color: #0284c7;" />
            <div>
              <div style="font-size: 13px; font-weight: 600; color: #f8fafc;">Hayır, çocuklara özel değil (Önerilen)</div>
              <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Standart içerikler için uygundur. Yorumlar, bildirimler ve reklamlar etkindir.</div>
            </div>
          </label>

          <label style="
            display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border-radius: 8px;
            background: ${currentSettings.kidsRating === 'VIDEO_MADE_FOR_KIDS_MFK' ? 'rgba(2, 132, 199, 0.12)' : 'rgba(255, 255, 255, 0.03)'};
            border: 1px solid ${currentSettings.kidsRating === 'VIDEO_MADE_FOR_KIDS_MFK' ? '#0284c7' : 'rgba(255, 255, 255, 0.08)'};
            cursor: pointer;
          ">
            <input type="radio" name="yt-setting-kids" value="VIDEO_MADE_FOR_KIDS_MFK" ${currentSettings.kidsRating === 'VIDEO_MADE_FOR_KIDS_MFK' ? 'checked' : ''} style="margin-top: 3px; accent-color: #0284c7;" />
            <div>
              <div style="font-size: 13px; font-weight: 600; color: #f8fafc;">Evet, çocuklara özel</div>
              <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">COPPA uyumlu çocuk içerikleri. Kişiselleştirilmiş reklamlar kullanılamaz.</div>
            </div>
          </label>
        </div>
      </div>

      <!-- Bilgi Kutusu -->
      <div style="
        background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 8px; padding: 12px; font-size: 11.5px; color: #bae6fd; line-height: 1.5;
      ">
        <strong>💡 Akıllı Planlama Kuralı:</strong> "Otomatik Yükle" tıklandığında sistem YouTube Studio'daki videolarınızı ve shorts'larınızı kontrol eder. En son yüklenen video planlı ise sıradaki saate planlar; en son video herkese açıksa gelecekteki en yakın saate ayarlar.
      </div>
    </div>

    <!-- Footer -->
    <div style="padding: 16px 24px; border-top: 1px solid rgba(255, 255, 255, 0.08); background: rgba(15, 23, 42, 0.4); display: flex; justify-content: flex-end; gap: 10px;">
      <button id="yt-setting-cancel-btn" style="
        background: none; border: 1px solid rgba(255, 255, 255, 0.15); color: #94a3b8;
        border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 600; cursor: pointer;
      ">Vazgeç</button>
      <button id="yt-setting-save-btn" style="
        background: #0284c7; color: white; border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 8px; padding: 8px 20px; font-size: 13px; font-weight: 600; cursor: pointer;
        box-shadow: 0 2px 10px rgba(2, 132, 199, 0.3); transition: all 0.15s ease;
      ">💾 Ayarları Kaydet</button>
    </div>
  `;

  modal.appendChild(container);
  document.body.appendChild(modal);

  renderHoursList();

  // Events
  modal.querySelector("#yt-setting-modal-close").addEventListener("click", () => modal.remove());
  modal.querySelector("#yt-setting-cancel-btn").addEventListener("click", () => modal.remove());
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.remove(); });

  const countInput = modal.querySelector("#yt-setting-daily-count");
  countInput.addEventListener("input", (e) => {
    let val = parseInt(e.target.value, 10);
    if (isNaN(val) || val < 1) val = 1;
    currentCount = val;
    while (currentHours.length < currentCount) {
      const defaultTimes = ["12:00", "15:00", "18:00", "21:00", "10:00", "14:00", "17:00", "20:00"];
      currentHours.push(defaultTimes[currentHours.length % defaultTimes.length]);
    }
    if (currentHours.length > currentCount) {
      currentHours = currentHours.slice(0, currentCount);
    }
    renderHoursList();
  });

  modal.querySelector("#yt-setting-sync-hours-btn").addEventListener("click", () => {
    // Generate evenly spaced hours based on currentCount
    const startHour = 10;
    const endHour = 22;
    const step = currentCount > 1 ? (endHour - startHour) / (currentCount - 1) : 0;
    currentHours = [];
    for (let i = 0; i < currentCount; i++) {
      const h = Math.round(startHour + i * step);
      currentHours.push(`${String(h).padStart(2, '0')}:00`);
    }
    renderHoursList();
  });

  modal.querySelector("#yt-setting-add-hour-btn").addEventListener("click", () => {
    currentHours.push("18:00");
    currentCount = currentHours.length;
    countInput.value = currentCount;
    renderHoursList();
  });

  // Save Settings
  modal.querySelector("#yt-setting-save-btn").addEventListener("click", async () => {
    const selectedKids = modal.querySelector('input[name="yt-setting-kids"]:checked')?.value || "VIDEO_MADE_FOR_KIDS_NOT_MFK";
    
    // Sort and clean hours
    const cleanedHours = currentHours.filter(h => /^\d{1,2}:\d{2}$/.test(h)).sort((a, b) => {
      const [h1, m1] = a.split(':').map(Number);
      const [h2, m2] = b.split(':').map(Number);
      return (h1 * 60 + m1) - (h2 * 60 + m2);
    });

    const newSettings = {
      dailyCount: currentCount,
      publishHours: cleanedHours.length > 0 ? cleanedHours : ["14:00", "18:00", "21:00"],
      kidsRating: selectedKids
    };

    await saveChannelSettings(channelId, newSettings);
    showNotification(`✅ "${channelName}" için kanal ayarları kaydedildi!`);
    modal.remove();
  });
}

// ── Buton Enjeksiyonu (YALNIZCA İçerik Sekmesinde) ─────────────

function injectStudioContentActions() {
  removeOldButtons();

  // YALNIZCA İçerik (Videos/Content) sekmesinde göster
  if (!isStudioContentTab()) {
    removeStudioContentActions();
    return;
  }

  // Eğer zaten DOM'da mevcutsa tekrar ekleme
  const existing = document.getElementById("yt-oto-content-actions");
  if (existing && document.body.contains(existing)) {
    return;
  }

  // Uygun montaj noktasını bul
  let anchor = null;
  let insertMode = "after";

  // 1. Sayfa ortasındaki Video yükle butonu (boş kanal durumu)
  const centerBtn = findCenterUploadButton();
  if (centerBtn && isVisible(centerBtn)) {
    anchor = centerBtn;
    insertMode = "after";
  }

  // 2. Filtre çubuğu (ytcp-filter-bar)
  if (!anchor) {
    const filterBar = queryShadow('ytcp-filter-bar') || queryShadow('#filter-bar');
    if (filterBar && isVisible(filterBar)) {
      anchor = filterBar;
      insertMode = "after";
    }
  }

  // 3. Sekmeler çubuğu (ytcp-navigation-tabs)
  if (!anchor) {
    const navTabs = queryShadow('ytcp-navigation-tabs') || queryShadow('#tabs');
    if (navTabs && isVisible(navTabs)) {
      anchor = navTabs;
      insertMode = "after";
    }
  }

  // 4. Video bölümü konteyneri (ytcp-video-section)
  if (!anchor) {
    const videoSection = queryShadow('ytcp-video-section') || queryShadow('ytcp-content-section');
    if (videoSection && isVisible(videoSection)) {
      anchor = videoSection;
      insertMode = "prepend";
    }
  }

  if (!anchor) return;

  const container = document.createElement("div");
  container.id = "yt-oto-content-actions";
  container.style.cssText = `
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-left: 12px;
    margin-right: 8px;
    vertical-align: middle;
    z-index: 999;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  // "⚡ Otomatik Yükle" Butonu
  const btnUpload = document.createElement("button");
  btnUpload.id = "yt-oto-center-btn";
  btnUpload.innerHTML = `
    <span style="font-size: 15px; margin-right: 4px;">⚡</span>
    <span>Otomatik Yükle</span>
  `;
  btnUpload.style.cssText = `
    background: #0284c7;
    color: #ffffff;
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 8px;
    padding: 8px 18px;
    font-family: inherit;
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 10px rgba(2, 132, 199, 0.3);
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
  `;
  btnUpload.addEventListener("mouseenter", () => {
    btnUpload.style.background = "#0369a1";
    btnUpload.style.transform = "translateY(-1px)";
    btnUpload.style.boxShadow = "0 4px 14px rgba(2, 132, 199, 0.45)";
  });
  btnUpload.addEventListener("mouseleave", () => {
    btnUpload.style.background = "#0284c7";
    btnUpload.style.transform = "none";
    btnUpload.style.boxShadow = "0 2px 10px rgba(2, 132, 199, 0.3)";
  });
  btnUpload.addEventListener("click", openOtoYukleModal);

  // "⚙️" Ayar Butonu
  const btnSettings = document.createElement("button");
  btnSettings.id = "yt-oto-settings-btn";
  btnSettings.innerHTML = "⚙️";
  btnSettings.title = "Kanal Otomatik Yükleme & Planlama Ayarları";
  btnSettings.style.cssText = `
    background: #1e293b;
    color: #f8fafc;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    font-family: inherit;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  `;
  btnSettings.addEventListener("mouseenter", () => {
    btnSettings.style.background = "#334155";
    btnSettings.style.transform = "translateY(-1px)";
    btnSettings.style.borderColor = "rgba(56, 189, 248, 0.4)";
  });
  btnSettings.addEventListener("mouseleave", () => {
    btnSettings.style.background = "#1e293b";
    btnSettings.style.transform = "none";
    btnSettings.style.borderColor = "rgba(255, 255, 255, 0.15)";
  });
  btnSettings.addEventListener("click", () => openChannelUploadSettingsModal());

  container.appendChild(btnUpload);
  container.appendChild(btnSettings);

  if (insertMode === "after" && anchor.parentNode) {
    anchor.parentNode.insertBefore(container, anchor.nextSibling);
  } else if (insertMode === "prepend") {
    anchor.insertBefore(container, anchor.firstChild);
  } else if (anchor.parentNode) {
    anchor.parentNode.appendChild(container);
  }
}

// ── Video Seçim Modalı ────────────────────────────────────────

function openOtoYukleModal() {
  const isInstagram = location.href.includes("instagram.com");
  let modal = document.getElementById("yt-oto-modal");
  if (modal) {
    modal.style.display = "flex";
    const titleSpan = modal.querySelector("#yt-oto-modal-title");
    if (titleSpan) {
      if (isInstagram) {
        titleSpan.innerHTML = `<span style="background: linear-gradient(45deg, #f09433, #dc2743, #bc1888); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">⚡</span> Instagram Reels — Video Seçin`;
      } else {
        titleSpan.innerHTML = `<span style="color: #38bdf8;">⚡</span> Otomatik Yükle — Video Seçin`;
      }
    }
    const scrapeBtn = modal.querySelector("#yt-oto-modal-scrape-ideas");
    if (scrapeBtn) {
      scrapeBtn.style.display = isInstagram ? "none" : "flex";
    }
    loadVideosInModal();
    return;
  }

  modal = document.createElement("div");
  modal.id = "yt-oto-modal";
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    z-index: 10000000; background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    display: flex; align-items: center; justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  const content = document.createElement("div");
  content.style.cssText = `
    background: rgba(30, 41, 59, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px; width: 500px; max-height: 80vh;
    box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    display: flex; flex-direction: column; overflow: hidden;
  `;

  content.innerHTML = `
    <div style="padding: 16px 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between; align-items: center;">
      <div>
        <span id="yt-oto-modal-title" style="font-weight: 700; font-size: 15px; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
          ${isInstagram
            ? '<span style="background: linear-gradient(45deg, #f09433, #dc2743, #bc1888); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">⚡</span> Instagram Reels — Video Seçin'
            : '<span style="color: #38bdf8;">⚡</span> Otomatik Yükle — Video Seçin'}
        </span>
        <div style="font-size: 11px; color: #94a3b8; margin-top: 3px; font-weight: 500;">
          Aktif Kanal: <strong id="yt-oto-active-channel-lbl" style="color: #38bdf8;">-</strong>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <button id="yt-oto-modal-settings" style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #cbd5e1; font-size: 11.5px; border-radius: 6px; padding: 4px 10px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 4px;">⚙️ Ayarlar</button>
        <button id="yt-oto-modal-close" style="background: none; border: none; color: #94a3b8; font-size: 24px; cursor: pointer; padding: 4px; line-height: 1;">&times;</button>
      </div>
    </div>
    <div id="yt-oto-modal-body" style="padding: 16px 24px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 12px; min-height: 200px;">
      <div style="color: #94a3b8; text-align: center; margin-top: 40px;">Videolar yükleniyor...</div>
    </div>
    <div style="padding: 14px 24px; border-top: 1px solid rgba(255, 255, 255, 0.08); background: rgba(15, 23, 42, 0.3); display: flex; justify-content: space-between; align-items: center;">
      <button id="yt-oto-modal-scrape-ideas" style="background: none; border: none; color: #38bdf8; font-size: 12px; cursor: pointer; font-weight: 600; display: ${isInstagram ? "none" : "flex"}; align-items: center; gap: 4px;">💡 Fikirleri Al</button>
      <button id="yt-oto-modal-refresh" style="background: none; border: none; color: #38bdf8; font-size: 12px; cursor: pointer; font-weight: 600;">Listeyi Yenile</button>
    </div>
  `;

  modal.appendChild(content);
  document.body.appendChild(modal);

  document.getElementById("yt-oto-modal-close").addEventListener("click", () => {
    modal.style.display = "none";
  });
  document.getElementById("yt-oto-modal-settings").addEventListener("click", () => {
    openChannelUploadSettingsModal();
  });
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });
  document.getElementById("yt-oto-modal-refresh").addEventListener("click", () => {
    loadVideosInModal();
  });
  document.getElementById("yt-oto-modal-scrape-ideas").addEventListener("click", handleScrapeIdeas);

  loadVideosInModal();
}

async function handleScrapeIdeas() {
  const activeChannelName = getActiveChannelNameFromDOM();
  if (!activeChannelName) {
    alert("Hata: Aktif kanal ismi YouTube Studio'dan alınamadı.");
    return;
  }
  
  const titleSelectors = [
    '.ytciFeedIdeaPreviewTitle',
    '[class*="ytciFeedIdeaPreviewTitle"]'
  ];
  
  let titleEls = [];
  titleSelectors.forEach(sel => {
    try {
      const found = queryShadowAll(sel);
      if (found && found.length > 0) {
        titleEls = titleEls.concat(found);
      }
    } catch (e) {}
  });

  const containerSelectors = [
    'ytci-feed-idea-preview',
    '.ytciFeedIdeaPreviewPreviewContainerWithIllustration',
    '.ytciFeedIdeaPreviewHost',
    '.ytciFeedIdeaPreviewPreviewContainer'
  ];
  
  const containers = [];
  titleEls.forEach(titleEl => {
    let container = null;
    for (const sel of containerSelectors) {
      container = titleEl.closest(sel);
      if (container) break;
    }
    if (!container) {
      container = titleEl.parentElement;
    }
    if (container && !containers.includes(container)) {
      containers.push(container);
    }
  });
                     
  if (containers.length === 0) {
    alert("Hata: Sayfada yüklü fikir bulunamadı. Lütfen YouTube Studio'da Araştırma/İlham Kaynakları sekmesinde olduğunuzdan ve fikirlerin yüklendiğinden emin olun.");
    return;
  }
  
  const scrapeBtn = document.getElementById("yt-oto-modal-scrape-ideas");

  const setScrapeButtonState = (disabled, text) => {
    if (scrapeBtn) {
      scrapeBtn.disabled = disabled;
      scrapeBtn.style.opacity = disabled ? "0.5" : "1";
      scrapeBtn.textContent = text;
    }
  };

  setScrapeButtonState(true, "⏳ Hazırlanıyor...");

  const ideas = [];
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  // Yardımcı Fonksiyonlar: Bekleme ve Durum Kontrolleri
  const descSelectors = [
    '.ytciPitchDialogSummary',
    'ytci-pitch-dialog .ytciPitchDialogSummary',
    'ytcp-ve .ytciPitchDialogSummary',
    '.description',
    'ytci-pitch-dialog .description',
    'ytcp-dialog .description'
  ];

  const disappearSelectors = [
    '.ytciPitchDialogSummary',
    'ytci-pitch-dialog .ytciPitchDialogSummary',
    'ytcp-ve .ytciPitchDialogSummary',
    '.description',
    'ytci-pitch-dialog .description',
    'ytcp-dialog .description',
    'tp-yt-iron-overlay-backdrop',
    'iron-overlay-backdrop',
    'ytcp-dialog-backdrop'
  ];

  // Aktif ve ekranda görünür olan dialog kutusunu döner
  const getActiveDialog = () => {
    const dialogSelectors = [
      'ytci-pitch-dialog',
      'ytcp-dialog',
      'tp-yt-paper-dialog',
      'paper-dialog',
      '.ytcp-dialog',
      '[role="dialog"]'
    ];
    for (const selector of dialogSelectors) {
      const dialogs = queryShadowAll(selector);
      for (const dialog of dialogs) {
        if (dialog && isVisible(dialog)) {
          return dialog;
        }
      }
    }
    return null;
  };

  // Elementin hem var olmasını hem de sayfada gerçekten görünür olmasını bekler
  const waitForNewElementText = async (selectorsList, lastText, timeoutMs = 3000) => {
    const start = Date.now();
    let matchedText = null;
    const normalizeForCompare = str => (str || "").replace(/\s+/g, " ").trim();
    const normLastText = normalizeForCompare(lastText);

    while (Date.now() - start < timeoutMs) {
      const dialog = getActiveDialog();
      if (dialog) {
        for (const sel of selectorsList) {
          const el = queryShadow(sel, dialog);
          if (el && isVisible(el)) {
            const text = el.textContent.trim();
            if (text) {
              const normText = normalizeForCompare(text);
              // Eğer önceki açıklamadan farklıysa yeni veri gelmiştir, hemen dön
              if (normText !== normLastText) {
                return text;
              }
              // Aynıysa yedekte tut ama beklemeye devam et
              matchedText = text;
            }
          }
        }
      }
      await sleep(100);
    }
    return matchedText;
  };

  // Elementlerin tamamen görünmez olmasını bekler
  const waitForElementToDisappear = async (selectorsList, timeoutMs = 3000) => {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const dialog = getActiveDialog();
      // Dialog bulunamazsa veya görünmezse kapanmış demektir
      if (!dialog) {
        return true;
      }
      await sleep(100);
    }
    return false;
  };

  const closeActiveDialog = async () => {
    try {
      const dialog = getActiveDialog();
      if (!dialog) return;

      logGemini("[YT-OTO] Dialog kapatılıyor...", "info");

      // 1. Yol: Polymer dialog ise yerel metotları çağır
      if (typeof dialog.close === 'function') {
        try { dialog.close(); } catch (e) {}
      }
      if (typeof dialog.cancel === 'function') {
        try { dialog.cancel(); } catch (e) {}
      }
      
      // 2. Yol: Kapatma butonuna tıkla
      const closeBtn = queryShadow('#close-button', dialog) || 
                       queryShadow('#close-btn', dialog) ||
                       queryShadow('.close-button', dialog) ||
                       queryShadow('.close-btn', dialog) ||
                       queryShadow('[aria-label*="kapat"]', dialog) ||
                       queryShadow('[aria-label*="close"]', dialog) ||
                       queryShadow('ytcp-button#close-button', dialog);
      if (closeBtn) {
        const nativeBtn = queryShadow('button', closeBtn) || queryShadow('[role="button"]', closeBtn);
        if (nativeBtn) {
          nativeBtn.click();
        } else {
          closeBtn.click();
        }
      } else {
        // 3. Yol: Escape tuşu gönder
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true }));
      }
      
      await sleep(300);
      
      // 3. Yol: Kapanmadıysa tekrar Escape tuşu gönder
      if (getActiveDialog()) {
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true }));
        await sleep(300);
      }
      
      // 4. Yol: Hâlâ kapanmadıysa zorla gizle ve öznitelikleri kaldır (Zorunlu kapatma)
      const finalDialog = getActiveDialog();
      if (finalDialog) {
        logGemini("[YT-OTO] Dialog normal yollarla kapanmadı, zorla gizleniyor...", "warning");
        finalDialog.removeAttribute('opened');
        finalDialog.setAttribute('aria-hidden', 'true');
        finalDialog.style.display = 'none';
        
        // Eşlik eden arka plan perdelerini de gizle
        const backdrops = queryShadowAll('tp-yt-iron-overlay-backdrop') || [];
        backdrops.forEach(b => {
          b.removeAttribute('opened');
          b.style.display = 'none';
        });
      }
      await sleep(400); // Overlay manager'ın durumunu temizlemesi için bekle
    } catch (e) {
      console.warn("Close active dialog error:", e);
    }
  };

  // Benzersiz kapsayıcıları bul
  const uniqueContainers = [];
  const processedTitles = new Set();

  containers.forEach(container => {
    const titleEl = queryShadow('.ytciFeedIdeaPreviewTitle', container) || 
                    queryShadow('[class*="ytciFeedIdeaPreviewTitle"]', container);
    let titleText = titleEl ? titleEl.textContent.trim() : "";
    
    const topicEl = queryShadow('#chip-text', container) || 
                    queryShadow('[class*="ytciFeedIdeaPreviewTopic"] #chip-text', container) ||
                    queryShadow('.ytciFeedIdeaPreviewTopic', container);
    const topicText = topicEl ? topicEl.textContent.trim() : "";
    
    if (titleText) {
      // Clean topic name from title if it got appended
      if (topicText && titleText.endsWith(topicText)) {
        titleText = titleText.substring(0, titleText.length - topicText.length).trim();
      }
      
      if (!processedTitles.has(titleText)) {
        processedTitles.add(titleText);
        uniqueContainers.push({
          container,
          titleText,
          topicText: topicText || "Genel"
        });
      }
    }
  });

  const totalCount = uniqueContainers.length;

  // Başlamadan önce açık dialog varsa kapat ve kapanmasını bekle
  await closeActiveDialog();
  await waitForElementToDisappear(disappearSelectors, 3000);

  let lastDescription = "";

  for (let i = 0; i < totalCount; i++) {
    const { titleText, topicText } = uniqueContainers[i];
    
    setScrapeButtonState(true, `⏳ ${i + 1}/${totalCount} Açıklama alınıyor...`);

    // Sanal kaydırma (virtual scrolling) durumuna karşı kapsayıcıyı canlı olarak yeniden bul
    let container = null;
    const titleSelectors = [
      '.ytciFeedIdeaPreviewTitle',
      '[class*="ytciFeedIdeaPreviewTitle"]'
    ];
    let titleEls = [];
    titleSelectors.forEach(sel => {
      try {
        const found = queryShadowAll(sel);
        if (found && found.length > 0) {
          titleEls = titleEls.concat(found);
        }
      } catch (e) {}
    });

    for (const el of titleEls) {
      let cleanElText = el.textContent.trim();
      if (topicText && cleanElText.endsWith(topicText)) {
        cleanElText = cleanElText.substring(0, cleanElText.length - topicText.length).trim();
      }

      const normElText = cleanElText.toLowerCase().replace(/[^a-z0-9]/g, '');
      const normTargetText = titleText.toLowerCase().replace(/[^a-z0-9]/g, '');

      if (normElText === normTargetText) {
        const containerSelectors = [
          'ytci-feed-idea-preview',
          '.ytciFeedIdeaPreviewPreviewContainerWithIllustration',
          '.ytciFeedIdeaPreviewHost',
          '.ytciFeedIdeaPreviewPreviewContainer'
        ];
        for (const sel of containerSelectors) {
          container = el.closest(sel);
          if (container) break;
        }
        if (!container) {
          container = el.parentElement;
        }
        break;
      }
    }

    if (!container) {
      console.warn(`[YT-OTO] Canlı DOM'da eleman bulunamadı, hafızadaki referans kullanılacak: "${titleText}"`);
      container = uniqueContainers[i].container;
    }

    // 1. Kapsayıcıyı ekranda ortala
    try {
      container.scrollIntoView({ block: 'center' });
    } catch (e) {}
    await sleep(400);

    // 2. Fikrin detay penceresini açmak için tıkla (Öncelikle başlık elemanını hedefle, açılmazsa kapsayıcıya tıklar)
    let dialogOpened = false;
    for (let clickAttempt = 0; clickAttempt < 3; clickAttempt++) {
      if (!geminiRunning) break;
      try {
        const titleLink = queryShadow('.ytciFeedIdeaPreviewTitle', container) || 
                          queryShadow('[class*="ytciFeedIdeaPreviewTitle"]', container);
        if (clickAttempt === 0 && titleLink) {
          logGemini(`[YT-OTO] Tıklanıyor (Başlık Linki): "${titleText}"`, "info");
          titleLink.click();
        } else {
          logGemini(`[YT-OTO] Tıklanıyor (Kapsayıcı Kart): "${titleText}"`, "info");
          container.click();
        }
      } catch (e) {
        console.warn("Click failed for container:", titleText, e);
      }

      // Pencere açıldı mı kontrol et (1.5 saniye bekle)
      const checkStart = Date.now();
      while (Date.now() - checkStart < 1500) {
        const dialog = getActiveDialog();
        if (dialog) {
          dialogOpened = true;
          break;
        }
        await sleep(100);
      }

      if (dialogOpened) break;
      logGemini(`[YT-OTO] Detay penceresi açılmadı, tekrar tıklanıyor (${clickAttempt + 1}/3)...`, "warning");
      await sleep(600); // Overlay manager'ın serbest kalması için bekle
    }

    if (!dialogOpened) {
      logGemini(`[YT-OTO] UYARI: Fikir detay penceresi açılamadı: "${titleText}"`, "error");
    }

    // 3. Fikir detay açıklamasının gelmesini bekle (Ağ gecikmelerine karşı 5 saniyeye yükseltildi)
    const descriptionText = await waitForNewElementText(descSelectors, lastDescription, 5000) || "";
    console.log(`[YT-OTO] [${i + 1}/${totalCount}] Başlık: "${titleText}" | Açıklama: "${descriptionText}"`);
    
    if (descriptionText) {
      lastDescription = descriptionText;
    }

    // 4. Detay penceresini kapat
    await closeActiveDialog();

    // 5. Pencerenin ve arka plan perdesinin tamamen yok olduğunu gör ve bekle
    await waitForElementToDisappear(disappearSelectors, 3000);
    await sleep(300);

    ideas.push({
      title: titleText,
      topic: topicText,
      description: descriptionText
    });
  }

  if (ideas.length === 0) {
    alert("Hata: Sayfadan geçerli bir fikir başlığı okunamadı.");
    setScrapeButtonState(false, "💡 Fikirleri Al");
    return;
  }
  
  try {
    setScrapeButtonState(true, "⏳ Kaydediliyor...");
    const channelsRes = await fetchFromBackground("http://127.0.0.1:8000/api/channels");
    const channels = (channelsRes && channelsRes.data) || [];
    let matchedChannel = channels.find(ch => {
      const cName = (ch.name || "").trim().toLowerCase();
      const cId = (ch.channel_id || "").trim().toLowerCase();
      const target = activeChannelName.trim().toLowerCase();
      return cName === target || cId === target || target.includes(cName) || cName.includes(target);
    });
    
    const channelId = matchedChannel ? matchedChannel.channel_id : activeChannelName.toLowerCase().replace(/[^a-z0-9]/g, "");
    
    console.log(`[YT-OTO] Bulunan ${ideas.length} fikir '${channelId}' kanalına gönderiliyor...`);
    
    const response = await fetchFromBackground(`http://127.0.0.1:8000/api/channels/${channelId}/plan/ideas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ideas: ideas })
    });
    
    if (response && response.success) {
      setScrapeButtonState(false, "✅ Başarılı!");
      await sleep(1000);
      showScrapingSummary(
        response.added_count,
        response.skipped_count,
        response.added_titles,
        response.skipped_titles,
        activeChannelName
      );
    } else {
      alert("Hata: Sunucu fikirleri kaydedemedi.");
    }
  } catch (err) {
    alert("Hata: " + err.message);
  } finally {
    setScrapeButtonState(false, "💡 Fikirleri Al");
  }
}

async function loadVideosInModal() {
  const body = document.getElementById("yt-oto-modal-body");
  body.innerHTML = "<div style='color: #94a3b8; text-align: center; margin-top: 40px;'>Videolar yükleniyor...</div>";

  const isInstagram = location.href.includes("instagram.com");
  const isYouTube = location.href.includes("studio.youtube.com") || location.href.includes("youtube.com");
  const isTikTok = location.href.includes("tiktok.com");

  let activeChannelName = resolveActiveChannelName();
  const lbl = document.getElementById("yt-oto-active-channel-lbl");
  if (lbl) {
    lbl.textContent = activeChannelName || "(Tespit Edilemedi)";
  }

  try {
    const responseData = await fetchFromBackground("http://127.0.0.1:8000/api/output");
    const videos = responseData.data || [];
    
    // Kanallar listesini çekip aktif kanal ID'sini kesinleştir
    let channels = [];
    try {
      const channelsRes = await fetchFromBackground("http://127.0.0.1:8000/api/channels");
      channels = channelsRes.data || [];
    } catch (e) {
      console.warn("[YT-OTO] Kanallar listesi karşılaştırma için alınamadı:", e);
    }
    
    let activeChannelId = "";
    let matchedChannel = null;
    if (activeChannelName) {
      const targetName = activeChannelName.trim().toLowerCase();
      const targetNameAlpha = targetName.replace(/[^a-z0-9]/g, "");
      matchedChannel = channels.find(ch => {
        const cName = (ch.name || "").trim().toLowerCase();
        const cId = (ch.channel_id || "").trim().toLowerCase();
        const igUser = (ch.instagram_username || "").trim().toLowerCase();
        const cNameAlpha = cName.replace(/[^a-z0-9]/g, "");
        const cIdAlpha = cId.replace(/[^a-z0-9]/g, "");
        const igUserAlpha = igUser.replace(/[^a-z0-9]/g, "");
        return (
          cName === targetName || cId === targetName || igUser === targetName ||
          cNameAlpha === targetNameAlpha || cIdAlpha === targetNameAlpha || igUserAlpha === targetNameAlpha ||
          (igUser && (targetName.includes(igUser) || igUser.includes(targetName))) ||
          (cId && (targetName.includes(cId) || cId.includes(targetName)))
        );
      });
      if (matchedChannel) {
        activeChannelId = matchedChannel.channel_id.trim().toLowerCase();
      }
    }

    // Instagram özel eşleşme: Eğer profil sayfasında değilsek veya tek kanal aktifse
    if (isInstagram && !activeChannelId) {
      const igEnabled = channels.filter(ch => ch.instagram === true);
      if (igEnabled.length === 1) {
        matchedChannel = igEnabled[0];
        activeChannelId = matchedChannel.channel_id.trim().toLowerCase();
      }
    }

    if (lbl) {
      if (matchedChannel) {
        lbl.textContent = `${matchedChannel.name || activeChannelName} (@${matchedChannel.instagram_username || activeChannelName})`;
      } else if (activeChannelName) {
        lbl.textContent = activeChannelName;
      } else if (isInstagram) {
        lbl.textContent = "Instagram Kanalı";
      } else {
        lbl.textContent = "(Tespit Edilemedi)";
      }
    }

    const activeVideos = videos.filter(v => {
      if (v.archived) return false;
      if (isYouTube && v.uploaded_youtube) return false;
      if (isInstagram && v.uploaded_instagram) return false;
      if (isTikTok && v.uploaded_tiktok) return false;
      if (!activeChannelName && !activeChannelId && !isInstagram) return false;
      
      const folderParts = (v.folder || "").split("/");
      const folderChanId = folderParts[0] ? folderParts[0].trim().toLowerCase() : "";
      const folderChanIdAlpha = folderChanId.replace(/[^a-z0-9]/g, "");
      
      const vChanName = (v.channel_name || "").trim().toLowerCase();
      const vChanNameAlpha = vChanName.replace(/[^a-z0-9]/g, "");
      
      const vChanId = (v.channel_id || "").trim().toLowerCase();
      const vChanIdAlpha = vChanId.replace(/[^a-z0-9]/g, "");
      
      // 1. Kanal ID eşleşmesi (En kesin yöntem)
      if (activeChannelId) {
        if (folderChanId === activeChannelId || vChanId === activeChannelId || folderChanIdAlpha === activeChannelId || vChanIdAlpha === activeChannelId) {
          return true;
        }
      }
      
      // 2. Kanal Adı tam eşleşmesi
      if (activeChannelName) {
        const targetName = activeChannelName.trim().toLowerCase();
        const targetNameAlpha = targetName.replace(/[^a-z0-9]/g, "");
        if (vChanName === targetName || vChanId === targetName || vChanNameAlpha === targetNameAlpha || vChanIdAlpha === targetNameAlpha) {
          return true;
        }
      }
      
      // 3. Alt dizin ismine göre akıllı eşleşme (örn: ch_test_run... -> Test Run)
      if (activeChannelName) {
        const targetNameAlpha = activeChannelName.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
        if (folderChanIdAlpha && folderChanIdAlpha !== "ch" && folderChanIdAlpha !== "shorts" && folderChanIdAlpha.length >= 3) {
          if (targetNameAlpha.length >= 3) {
            if (folderChanIdAlpha.includes(targetNameAlpha) || targetNameAlpha.includes(folderChanIdAlpha)) {
              return true;
            }
          }
        }
      }

      // 4. Instagram özel fallback: aktif kanal tam filtrelenememişse tüm yüklenmemiş Instagram videolarını listele
      if (isInstagram && !activeChannelId && !activeChannelName) {
        return true;
      }
      
      return false;
    });
    
    if (activeVideos.length === 0) {
      body.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: #94a3b8;">
          <div style="font-size: 32px; margin-bottom: 8px;">🎬</div>
          <div style="font-size: 13.5px; font-weight: 600;">Yüklenecek Video Bulunamadı</div>
          <div style="font-size: 12px; margin-top: 4px; color: #64748b;">
            ${(matchedChannel && matchedChannel.name) || activeChannelName ? `"${(matchedChannel && matchedChannel.name) || activeChannelName}" kanalı` : "Bu kanal"} için üretilmiş aktif video bulunamadı.
          </div>
        </div>
      `;
      return;
    }

    body.innerHTML = activeVideos.map(v => `
      <div class="yt-oto-video-item" style="
        display: flex; align-items: center; justify-content: space-between;
        padding: 12px 14px; background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;
        transition: all 0.15s ease;
      ">
        <div style="flex: 1; min-width: 0; margin-right: 12px;">
          <div style="font-size: 13px; font-weight: 600; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            ${isInstagram ? "📱 " : (v.shorts_mode ? "📱 " : "🎬 ")}${v.title || "(Başlık yok)"}
          </div>
          <div style="font-size: 11px; color: #64748b; font-family: monospace; margin-top: 2px;">
            ${v.folder}
          </div>
        </div>
        <button class="yt-oto-video-load-btn" data-folder="${v.folder}" style="
          background: ${isInstagram ? "linear-gradient(135deg, #f09433, #dc2743, #bc1888)" : "#0284c7"};
          color: white; border: 1px solid ${isInstagram ? "rgba(225, 48, 108, 0.4)" : "rgba(56, 189, 248, 0.35)"}; border-radius: 6px;
          padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer;
          transition: all 0.15s ease; box-shadow: ${isInstagram ? "0 2px 10px rgba(220, 39, 67, 0.35)" : "0 2px 8px rgba(2, 132, 199, 0.25)"};
        ">Yükle</button>
      </div>
    `).join("");

    const items = body.querySelectorAll(".yt-oto-video-item");
    items.forEach(item => {
      item.addEventListener("mouseenter", () => {
        item.style.background = "rgba(255, 255, 255, 0.06)";
        item.style.borderColor = "rgba(255, 255, 255, 0.12)";
      });
      item.addEventListener("mouseleave", () => {
        item.style.background = "rgba(255, 255, 255, 0.03)";
        item.style.borderColor = "rgba(255, 255, 255, 0.06)";
      });
    });

    const buttons = body.querySelectorAll(".yt-oto-video-load-btn");
    buttons.forEach(btn => {
      btn.addEventListener("click", async () => {
        const folder = btn.dataset.folder;
        const video = activeVideos.find(v => v.folder === folder);
        if (video) {
          // ── Instagram Yükleme Akışı ──
          if (isInstagram) {
            const originalHTML = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = "⏳ Yükleniyor...";
            document.getElementById("yt-oto-modal").style.display = "none";
            showNotification(`🚀 "${video.title || video.folder}" Instagram Reels'e yükleniyor...`);
            
            try {
              if (!video.instagram_username && matchedChannel && matchedChannel.instagram_username) {
                video.instagram_username = matchedChannel.instagram_username;
              }
              if (!video.caption && video.description) {
                video.caption = video.description;
              }
              await uploadToInstagram(video, false);
              if (typeof updateInstagramReadyCount === "function") {
                updateInstagramReadyCount();
              }
            } catch (err) {
              console.error("[IG-OTO] Instagram yükleme hatası:", err);
              showNotification(`❌ Instagram yükleme hatası: ${err.message}`);
              alert("Instagram Yükleme Hatası: " + err.message);
            } finally {
              btn.disabled = false;
              btn.innerHTML = originalHTML;
            }
            return;
          }

          // ── YouTube Studio Yükleme Akışı ──
          const originalHTML = btn.innerHTML;
          btn.disabled = true;
          btn.innerHTML = "🔍 Planlanıyor...";
          
          try {
            // 1. Kanal ayarlarını al
            const channelId = getActiveStudioChannelId();
            const settings = await getChannelSettings(channelId);
            
            // 2. Videolar ve Shorts sekmelerini inceleyip planlama slotunu belirle
            const schedulePlan = await determineNextPublishSlot(settings, !!video.shorts_mode);
            console.log("[YT-OTO] 🎯 Hesaplanan Plan:", schedulePlan);
            
            video._schedulePlan = schedulePlan;
            video._kidsRating = settings.kidsRating || "VIDEO_MADE_FOR_KIDS_NOT_MFK";
            
            showNotification(`📅 Planlama: ${schedulePlan.targetDateStr} ${schedulePlan.targetTimeStr} (${schedulePlan.reason})`);

            const conflicts = await checkUploadConflict(video);
            if (conflicts.length > 0) {
              // Mükerrer/çakışan videolar bulunursa uyarı modalını aç
              showConflictWarningModal(video, conflicts, () => {
                document.getElementById("yt-oto-modal").style.display = "none";
                startAutoUpload(video);
              });
            } else {
              // Çakışma yoksa doğrudan yükle
              document.getElementById("yt-oto-modal").style.display = "none";
              startAutoUpload(video);
            }
          } catch (e) {
            console.error("[YT-OTO] Çakışma veya planlama analizi sırasında hata oluştu:", e);
            document.getElementById("yt-oto-modal").style.display = "none";
            startAutoUpload(video);
          } finally {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
          }
        }
      });
    });

  } catch (err) {
    body.innerHTML = `
      <div style="text-align: center; padding: 40px 20px; color: #ef4444;">
        <div style="font-size: 32px; margin-bottom: 8px;">⚠️</div>
        <div style="font-size: 13.5px; font-weight: 600;">Bağlantı Hatası</div>
        <div style="font-size: 12px; margin-top: 4px; color: #94a3b8;">
          Backend API ulaşılamıyor: http://127.0.0.1:8000<br>
          <small style="color: #64748b; margin-top: 4px; display: block;">Detay: ${err.message}</small>
        </div>
      </div>
    `;
  }
}

// ── Canlı Ajan Günlüğü & Hesap Değiştirici ────────────────────────

function logAgent(message, level = "info") {
  console.log(`[BROWSER-AGENT] [${level.toUpperCase()}] ${message}`);
  try {
    fetch("http://127.0.0.1:8000/api/browser-agent/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, level })
    }).catch(() => {});
  } catch (e) {}
}

async function switchYouTubeChannel(targetChannelName, targetChannelId, video) {
  if (!targetChannelName && !targetChannelId) return { ok: false, reason: "Hedef kanal adı veya ID'si belirtilmemiş" };
  logAgent(`🔄 Aktif YouTube kanalı değiştiriliyor -> Hedef: '${targetChannelName || targetChannelId}'`, "info");
  
  try {
    // 1. Sağ üst avatar butonunu bul ve tıkla (20 deneme = 10 saniye boyunca bekle)
    const avatarSelectors = [
      'button#avatar-btn',
      'ytcp-button#avatar-btn',
      '#avatar-btn',
      'ytcp-app-header #avatar-btn',
      'ytcp-header #avatar-btn',
      'ytd-topbar-menu-button-renderer #avatar-btn',
      'ytcp-profile-icon',
      'img#avatar-img',
      '#channel-switcher-button',
      'ytcp-header button'
    ];
    let avatarBtn = null;
    for (let attempt = 0; attempt < 20; attempt++) {
      for (const sel of avatarSelectors) {
        const el = queryShadow(sel);
        if (el) {
          avatarBtn = el;
          break;
        }
      }
      if (avatarBtn) break;
      await new Promise(r => setTimeout(r, 500));
    }

    if (!avatarBtn) {
      // Deep search for avatar
      const allAvatarEls = findElementsDeep(n => n.id && n.id.toLowerCase().includes('avatar'));
      for (const el of allAvatarEls) {
        if (['BUTTON', 'IMG', 'A'].includes(el.tagName?.toUpperCase())) {
          avatarBtn = el;
          break;
        }
      }
    }

    if (!avatarBtn) {
      logAgent("⚠️ Avatar butonu bulunamadı.", "warn");
      return { ok: false, reason: "Sağ üstteki profil avatar butonu bulunamadı (Sayfa tam yüklenmemiş olabilir)" };
    }

    clickElementReliably(avatarBtn);
    logAgent("Sağ üstteki profil menüsü tıklandı.", "info");

    // 2. "Hesap değiştir" seçeneğini bul (15 deneme = 7.5 saniye bekle)
    const switchKeywords = [
      "hesap değiştir",
      "hesap degistir",
      "switch account",
      "konto wechseln",
      "changer de compte",
      "cambiar de cuenta",
      "trocar de conta",
      "cambia account",
      "switch"
    ];

    let switchItem = null;
    for (let attempt = 0; attempt < 15; attempt++) {
      await new Promise(r => setTimeout(r, 500));
      
      const switchLink = queryShadow('a[href*="channel_switcher"]') || queryShadow('a[href*="AccountSwitcherV2"]');
      if (switchLink) {
        switchItem = switchLink;
        break;
      }

      const allMenuItems = queryShadowAll(
        'tp-yt-paper-item, ytd-compact-link-renderer, ytcp-text-menu-item, paper-item, a[role="menuitem"], #items > *, ytd-menu-service-item-renderer, yt-formatted-string'
      );
      for (const item of allMenuItems) {
        const text = (item.textContent || "").toLowerCase().trim();
        const href = (item.getAttribute && item.getAttribute("href")) || "";
        if (switchKeywords.some(kw => text.includes(kw)) || href.includes("channel_switcher")) {
          switchItem = item;
          break;
        }
      }
      if (switchItem) break;
    }

    if (!switchItem) {
      logAgent("⚠️ 'Hesap değiştir' menüsü bulunamadı.", "warn");
      document.body.click();
      return { ok: false, reason: "Profil menüsünde 'Hesap değiştir' seçeneği bulunamadı" };
    }

    clickElementReliably(switchItem);
    logAgent("'Hesap değiştir' tıklandı, kanallar listeleniyor...", "info");

    // 3. Hesap listesinde hedef kanal adını bul (16 deneme = 8 saniye bekle)
    const targetNorm = normalizeChannelString(targetChannelName);
    const targetIdNorm = targetChannelId ? normalizeChannelString(targetChannelId) : "";

    let targetItem = null;
    let targetHref = null;
    let foundChannelNames = [];

    for (let attempt = 0; attempt < 16; attempt++) {
      await new Promise(r => setTimeout(r, 500));
      const accountItems = queryShadowAll(
        'ytd-account-item-renderer, ytcp-account-item, ytd-compact-link-renderer, paper-item, tp-yt-paper-item, #contents > *'
      );
      if (accountItems.length > 0) {
        foundChannelNames = [];
        for (const item of accountItems) {
          const titleEl = queryShadow('#channel-title, #title, #account-name, .channel-title', item);
          const bylineEl = queryShadow('#byline, #handle, .byline, #email', item);
          const titleText = (titleEl ? titleEl.textContent : "").trim();
          const bylineText = (bylineEl ? bylineEl.textContent : "").trim();
          const fullText = (item.textContent || "").trim();
          const itemHref = item.getAttribute?.('href') || queryShadow('a', item)?.getAttribute?.('href') || "";

          const cardName = titleText || fullText.split('\n')[0].trim();
          if (cardName && !foundChannelNames.includes(cardName)) {
            foundChannelNames.push(cardName);
          }

          const titleNorm = normalizeChannelString(titleText);
          const bylineNorm = normalizeChannelString(bylineText);
          const fullNorm = normalizeChannelString(fullText);

          const isMatch = (
            (targetNorm && (titleNorm.includes(targetNorm) || fullNorm.includes(targetNorm) || isChannelMatch(titleText, targetChannelName))) ||
            (targetIdNorm && (bylineNorm.includes(targetIdNorm) || fullNorm.includes(targetIdNorm) || isChannelMatch(bylineText, targetChannelId)))
          );

          if (isMatch) {
            targetItem = item;
            targetHref = itemHref;
            logAgent(`🎯 Eşleşen kanal öğesi bulundu: '${cardName}' (${bylineText}) href=${itemHref}`, "info");
            break;
          }
        }
      }
      if (targetItem) break;
    }

    if (targetItem) {
      logAgent(`✅ Hedef kanal bulundu: '${targetChannelName}', geçiş yapılıyor...`, "info");
      showNotification(`🔄 '${targetChannelName}' kanalına geçiliyor...`);

      const pendingPayload = {
        ...video,
        _switched_account: true,
        timestamp: Date.now()
      };

      await new Promise(r => chrome.storage.local.set({ yt_studio_pending: pendingPayload }, r));
      try {
        await fetch("http://127.0.0.1:8000/api/extension/pending-upload", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ payload: pendingPayload })
        });
      } catch (e) {}

      clickElementReliably(targetItem);

      const fullTargetHref = targetHref ? new URL(targetHref, window.location.origin).href : null;
      if (fullTargetHref && fullTargetHref.includes("/channel/")) {
        logAgent(`🌐 Özel kanal URL'sine navigasyon yapılıyor: ${fullTargetHref}`, "info");
        await new Promise(r => setTimeout(r, 600));
        location.href = fullTargetHref;
      } else {
        logAgent(`🔄 Kanal geçişi tıklandı, 2.5sn sonra Studio yenileniyor...`, "info");
        await new Promise(r => setTimeout(r, 2500));
        location.href = "https://studio.youtube.com";
      }

      return { ok: true };
    } else {
      const listSummary = foundChannelNames.length > 0 ? foundChannelNames.join(', ') : "Hesap listesi boş veya yüklenemedi";
      logAgent(`⚠️ '${targetChannelName}' kanalı listede bulunamadı. Bulunanlar: ${listSummary}`, "warn");
      document.body.click();
      return { ok: false, reason: `'${targetChannelName}' kanalı listede bulunamadı. Menüdeki kanallar: [${listSummary}]` };
    }
  } catch (err) {
    logAgent(`Kanal değiştirme hatası: ${err.message}`, "warn");
    return { ok: false, reason: `Kanal değiştirme istisnası: ${err.message}` };
  }
}

// ── Otomatik Yükleme Pipeline ─────────────────────────────────

async function startAutoUpload(video) {
  logAgent(`🎬 YouTube Studio Otomatik Yükleme Başlatıldı: ${video.title || video.folder}`);

  // 0. Aktif kanal kontrolü ve hesap geçişi
  if (video._switched_account) {
    logAgent(`✅ Hesap geçişi zaten yapıldı (_switched_account=true), kanal kontrolü atlanıyor.`, "info");
  } else {
    const targetChannel = video.channel_name || video.channel_id;
    if (targetChannel) {
      logAgent(`🔍 Hedef kanal doğrulanıyor: '${targetChannel}'...`);
      const activeChannel = await waitForActiveChannelName(15);
      logAgent(`📍 Aktif Kanal: '${activeChannel || "Bilinmiyor"}', Hedef Kanal: '${targetChannel}'`);

      const isMatch = activeChannel && (
        isChannelMatch(activeChannel, targetChannel) ||
        (video.channel_name && isChannelMatch(activeChannel, video.channel_name)) ||
        (video.channel_id && isChannelMatch(activeChannel, video.channel_id))
      );

      if (!isMatch) {
        logAgent(`⚠️ Aktif kanal ('${activeChannel || "Bilinmiyor"}') ile hedef kanal ('${targetChannel}') uyuşmuyor. Kanal değiştiriliyor...`, "warn");
        showNotification(`🔄 '${targetChannel}' kanalına geçiş yapılıyor...`);

        const switchResult = await switchYouTubeChannel(targetChannel, video.channel_id, video);
        if (switchResult && switchResult.ok) {
          logAgent(`✅ Kanal geçişi tıklandı, sayfa yeni kanal ile yenileniyor...`);
          return; // Sayfa yeniden yüklenecek ve startAutoUpload yeni kanalda başlayacak.
        } else {
          // KANAL DEĞİŞTİRİLEMEDİ! YANLIŞ KANALA YÜKLEME KESİNLİKLE YAPILMAMALIDIR!
          const failReason = (switchResult && switchResult.reason) || "Bilinmeyen menü hatası";
          const errMsg = `🛑 HEDEF KANAL GEÇİŞİ YAPILAMADI!\n\nSebep: ${failReason}\n\nVideo: "${video.title}"\nHedef Kanal: "${targetChannel}" (${(video.language || '').toUpperCase()})\nŞu Anda Açık Kanal: "${activeChannel || "Bilinmiyor"}"\n\nYanlış kanala yükleme yapılması sistem tarafından ENGELLENDİ.\nLütfen YouTube Studio'da sağ üstten "${targetChannel}" kanalına manuel geçin.`;
          logAgent(errMsg, "error");
          showNotification(`❌ HATA: '${targetChannel}' kanalına geçilemedi! (${failReason})`);
          alert(errMsg);
          removeFloatingInstruction();
          return; // ASLA YANLIŞ KANALA YÜKLEME YAPMA!
        }
      } else {
        logAgent(`🎯 Kanal doğrulandı: Aktif kanal ('${activeChannel}') hedef kanal ('${targetChannel}') ile tam uyuşuyor.`, "info");
      }
    }
  }

  // Kanal ayarlarını ve planlama saatini garantiye al
  const channelKey = video.channel_id || video.channel_name || getActiveStudioChannelId();
  const chanSettings = await getChannelSettings(channelKey);
  if (!video._kidsRating) {
    video._kidsRating = chanSettings.kidsRating || "VIDEO_MADE_FOR_KIDS_NOT_MFK";
  }
  if (!video._schedulePlan) {
    try {
      video._schedulePlan = await determineNextPublishSlot(chanSettings, !!video.shorts_mode);
      console.log("[YT-OTO] 🎯 Pipeline içi planlama belirlendi:", video._schedulePlan);
    } catch (e) {
      console.warn("[YT-OTO] Pipeline planlama belirleme uyarısı:", e);
    }
  }

  showFloatingInstruction(video.video_path, "Video dosyası indiriliyor ve yüklemeye hazırlanıyor...");

  try {
    // 1. Fetch video as Blob (Direct fetch first to avoid 64MB messaging limit, fallback to Background)
    let videoUrl;
    if (video.video_url) {
      videoUrl = video.video_url.startsWith("http") ? video.video_url : `http://127.0.0.1:8000${video.video_url.startsWith("/") ? "" : "/"}${video.video_url}`;
    } else if (video.folder) {
      const cleanFolder = video.folder.endsWith(".mp4") ? video.folder : `${video.folder}/final.mp4`;
      videoUrl = `http://127.0.0.1:8000/output/${cleanFolder}`;
    } else if (video.video_path) {
      videoUrl = `http://127.0.0.1:8000/api/video-file?path=${encodeURIComponent(video.video_path)}`;
    } else {
      videoUrl = `http://127.0.0.1:8000/output/final.mp4`;
    }
    console.log("[YT-OTO] Fetching video directly first:", videoUrl);
    
    let blob;
    try {
      let res = await fetch(videoUrl);
      if (!res.ok && video.video_path) {
        const altUrl = `http://127.0.0.1:8000/api/video-file?path=${encodeURIComponent(video.video_path)}`;
        console.log("[YT-OTO] Primary fetch failed, trying altUrl:", altUrl);
        res = await fetch(altUrl);
      }
      if (!res.ok) throw new Error(`Direct fetch failed with HTTP ${res.status}`);
      blob = await res.blob();
      console.log("[YT-OTO] Video file successfully fetched directly, size:", blob.size);
    } catch (directErr) {
      console.warn("[YT-OTO] Direct fetch failed, falling back to background fetch:", directErr);
      let fetchTarget = videoUrl;
      if (video.video_path) {
        fetchTarget = `http://127.0.0.1:8000/api/video-file?path=${encodeURIComponent(video.video_path)}`;
      }
      const responseData = await fetchFromBackground(fetchTarget, {}, true);
      let arrayBuffer;
      if (responseData.storageKey) {
        const key = responseData.storageKey;
        const stored = await new Promise((resolve) => {
          chrome.storage.local.get([key], (res) => resolve(res[key]));
        });
        chrome.storage.local.remove([key]);
        if (stored) {
          console.log("[YT-OTO] Decoding Base64 video data from storage...");
          const binaryString = atob(stored);
          const len = binaryString.length;
          const bytes = new Uint8Array(len);
          for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          arrayBuffer = bytes.buffer;
        } else {
          throw new Error("Video verisi yerel depolamadan okunamadı.");
        }
      } else if (responseData.isBinary) {
        console.log("[YT-OTO] Decoding Base64 video data...");
        const binaryString = atob(responseData.data);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        arrayBuffer = bytes.buffer;
      } else {
        arrayBuffer = responseData.data;
      }
      blob = new Blob([arrayBuffer], { type: "video/mp4" });
    }
    
    const file = new File([blob], "final.mp4", { type: "video/mp4" });
    console.log("[YT-OTO] Video file successfully prepared, size:", file.size);

    // 2. Open upload dialog
    const opened = await triggerUploadWorkflow(20);
    if (!opened) {
      throw new Error("Yükleme penceresi açılamadı. Lütfen YouTube Studio'da olduğunuzdan emin olun.");
    }

    // Video yolunu panoya kopyala (güvenlik önlemi/yedek olarak)
    try {
      await navigator.clipboard.writeText(video.video_path);
    } catch (e) {}

    // 3. Wait for the file input and assign the file
    waitForFileInputAndUpload(file, video);

  } catch (err) {
    console.error("[YT-OTO] Yükleme hatası:", err);
    showNotification(`❌ Hata: ${err.message}`);
    removeFloatingInstruction();
  }
}

function waitForFileInputAndUpload(file, video, attempt = 0) {
  if (attempt > 30) {
    showNotification("❌ Hata: Yükleme alanı (file input) bulunamadı.");
    removeFloatingInstruction();
    return;
  }

  const fileInput = queryShadow('ytcp-uploads-dialog input[type="file"], ytcp-uploads-file-picker input[type="file"], input[type="file"]');
  if (!fileInput) {
    setTimeout(() => waitForFileInputAndUpload(file, video, attempt + 1), 1000);
    return;
  }

  console.log("[YT-OTO] File input element found, uploading file...");
  
  try {
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;
    
    fileInput.dispatchEvent(new Event("input", { bubbles: true }));
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    console.log("[YT-OTO] Video file assigned and input/change events dispatched");

    waitAndFillMetadata(video);

  } catch (err) {
    console.error("[YT-OTO] File assignment failed:", err);
    showNotification(`❌ Yükleme hatası: ${err.message}`);
    removeFloatingInstruction();
  }
}

async function waitAndFillMetadata(video, attempt = 0) {
  // 180 saniye = 180 deneme (1s aralıklarla)
  if (attempt > 180) {
    console.warn("[YT-OTO] Metadata form elemanları bulunamadı (Zaman aşımı 3dk).");
    showNotification("⚠️ Form zaman aşımı. Lütfen başlık ve açıklamayı manuel girin.");
    removeFloatingInstruction();
    // Zaman aşımında yine de adım geçmeyi dene
    autoNavigateStepsAndArchive(video);
    return;
  }

  // İlk 5 saniyede dialog açılmasını bekle
  const dialog = queryShadow('ytcp-uploads-dialog');
  if (!dialog) {
    showFloatingInstruction(video.video_path, "YouTube Studio yükleme penceresi açılıyor...");
    setTimeout(() => waitAndFillMetadata(video, attempt + 1), 1000);
    return;
  }

  const titleEl = findTitleInput();
  if (!titleEl) {
    if (attempt % 10 === 0) {
      showFloatingInstruction(video.video_path, `Video yükleniyor... Başlık alanı bekleniyor (${attempt}s)`);
    }
    setTimeout(() => waitAndFillMetadata(video, attempt + 1), 1000);
    return;
  }

  // Başlık alanı bulundu — önce mevcut değeri kontrol et (zaten dolu ise fillForm çift yazmasın)
  removeFloatingInstruction();
  await fillForm(video);
  logAgent(`📝 Form alanları dolduruldu: Başlık="${video.title}", Açıklama ve Etiketler de yazıldı.`);

  showNotification("✅ Başlık, açıklama ve etiketler dolduruldu. Adımlar otomatik geçilecek...");

  // fillForm tamamlandıktan sonra adım geçme başlar (tag yazma bitmeden İleri tıklanmaz)
  autoNavigateStepsAndArchive(video);
}

const LANG_TIMEZONE_MAP = {
  "tr": "Europe/Istanbul",
  "en": "America/New_York",
  "de": "Europe/Berlin",
  "fr": "Europe/Paris",
  "es": "Europe/Madrid",
  "it": "Europe/Rome",
  "pt": "America/Sao_Paulo",
  "ru": "Europe/Moscow",
  "ja": "Asia/Tokyo",
  "ko": "Asia/Seoul",
  "zh": "Asia/Shanghai",
  "ar": "Asia/Riyadh",
  "hi": "Asia/Kolkata",
  "nl": "Europe/Amsterdam",
  "pl": "Europe/Warsaw",
  "sv": "Europe/Stockholm",
  "da": "Europe/Copenhagen",
  "fi": "Europe/Helsinki",
  "no": "Europe/Oslo",
  "cs": "Europe/Prague",
  "hu": "Europe/Budapest",
  "ro": "Europe/Bucharest",
  "uk": "Europe/Kyiv",
  "el": "Europe/Athens",
  "id": "Asia/Jakarta",
  "th": "Asia/Bangkok",
  "vi": "Asia/Ho_Chi_Minh"
};

function getUtcTimeForTarget19(dateStr, targetTz) {
  const baseUtc = new Date(dateStr + "T19:00:00Z");
  const options = {
    timeZone: targetTz,
    year: 'numeric', month: 'numeric', day: 'numeric',
    hour: 'numeric', minute: 'numeric', second: 'numeric',
    hour12: false
  };
  const formatter = new Intl.DateTimeFormat('en-US', options);
  const parts = formatter.formatToParts(baseUtc);
  const partVal = {};
  parts.forEach(p => partVal[p.type] = p.value);
  
  const formattedYear = parseInt(partVal.year);
  const formattedMonth = parseInt(partVal.month) - 1;
  const formattedDay = parseInt(partVal.day);
  const formattedHour = parseInt(partVal.hour);
  const formattedMinute = parseInt(partVal.minute);
  
  const targetTimeAsUtc = Date.UTC(formattedYear, formattedMonth, formattedDay, formattedHour, formattedMinute);
  const baseUtcMs = baseUtc.getTime();
  const offsetMs = targetTimeAsUtc - baseUtcMs;
  
  const target19AsUtcMs = Date.UTC(
    parseInt(dateStr.substring(0, 4)),
    parseInt(dateStr.substring(5, 7)) - 1,
    parseInt(dateStr.substring(8, 10)),
    19, 0, 0
  );
  
  return new Date(target19AsUtcMs - offsetMs);
}

// ── Çocuklara Özel (Made for Kids) Seçici ─────────────────────
function selectMadeForKidsOption(kidsRating) {
  const isMfk = kidsRating === "VIDEO_MADE_FOR_KIDS_MFK" || kidsRating === true || kidsRating === "true";
  const targetName = isMfk ? "VIDEO_MADE_FOR_KIDS_MFK" : "VIDEO_MADE_FOR_KIDS_NOT_MFK";
  const fallbackName = isMfk ? "VIDEO_MADE_FOR_KIDS_TRUE" : "VIDEO_MADE_FOR_KIDS_FALSE";

  // 1. YouTube Studio radio button selector (exact name attribute match)
  const radio = queryShadow(`tp-yt-paper-radio-button[name="${targetName}"], paper-radio-button[name="${targetName}"], [name="${targetName}"]`) ||
                queryShadow(`tp-yt-paper-radio-button[name="${fallbackName}"], paper-radio-button[name="${fallbackName}"], [name="${fallbackName}"]`);

  if (radio) {
    const isChecked = radio.checked || radio.getAttribute('checked') !== null || radio.getAttribute('aria-checked') === 'true';
    if (!isChecked) {
      console.log(`[YT-OTO] Çocuk seçeneği işaretleniyor: ${targetName}`);
      clickElementReliably(radio);
      const radioContainer = queryShadow('#radioContainer', radio) || queryShadow('#onRadio', radio) || queryShadow('#radioLabel', radio);
      if (radioContainer) clickElementReliably(radioContainer);
    }
    return true;
  }

  // 2. Container text search (.made-for-kids-rating-container)
  const container = queryShadow('.made-for-kids-rating-container, ytkc-made-for-kids-select');
  if (container) {
    const radios = queryShadowAll('tp-yt-paper-radio-button, paper-radio-button, [role="radio"]', container);
    for (const r of radios) {
      const text = (r.textContent || '').toLowerCase();
      if (isMfk && (text.includes("evet") || text.includes("yes"))) {
        clickElementReliably(r);
        return true;
      } else if (!isMfk && (text.includes("hayır") || text.includes("hayir") || text.includes("no"))) {
        clickElementReliably(r);
        return true;
      }
    }
  }
  return false;
}

// ── YouTube Studio Tarih ve Saat Ayrıştırıcı ──────────────────
const MONTH_NAMES_STUDIO = {
  // Turkish full & abbr
  ocak: 0, oca: 0, subat: 1, şubat: 1, sub: 1, şub: 1,
  mart: 2, mar: 2, nisan: 3, nis: 3, mayis: 4, mayıs: 4, may: 4,
  haziran: 5, haz: 5, temmuz: 6, tem: 6, agustos: 7, ağustos: 7, agu: 7, ağu: 7,
  eylul: 8, eylül: 8, eyl: 8, ekim: 9, eki: 9, kasim: 10, kasım: 10, kas: 10,
  aralik: 11, aralık: 11, ara: 11,
  // English full & abbr
  january: 0, jan: 0, february: 1, feb: 1, march: 2,
  april: 3, apr: 3, june: 5, jun: 5, july: 6, jul: 6,
  august: 7, aug: 7, september: 8, sep: 8, sept: 8,
  october: 9, oct: 9, november: 10, nov: 10, december: 11, dec: 11
};

function extractStudioDateTime(text) {
  if (!text) return null;
  const raw = text.replace(/[\n\r\t]+/g, ' ').trim();
  const lower = raw.toLowerCase();
  
  // 1. Time extraction: HH:MM with optional AM/PM, or HH.MM (only if not part of a date like 15.10.2026)
  let hour = null;
  let minute = 0;
  const time12Match = raw.match(/\b(\d{1,2}):(\d{2})\s*(am|pm)\b/i);
  if (time12Match) {
    let h = parseInt(time12Match[1], 10);
    minute = parseInt(time12Match[2], 10);
    const ampm = time12Match[3].toUpperCase();
    if (ampm === "PM" && h < 12) h += 12;
    if (ampm === "AM" && h === 12) h = 0;
    hour = h;
  } else {
    const time24Match = raw.match(/\b(\d{1,2}):(\d{2})\b/) || raw.match(/\b(\d{1,2})\.(\d{2})(?!\.\d+)\s*(?:saat|hours?|pm|am)?\b/i);
    if (time24Match) {
      const h = parseInt(time24Match[1], 10);
      const m = parseInt(time24Match[2], 10);
      if (h >= 0 && h <= 23 && m >= 0 && m <= 59) {
        hour = h;
        minute = m;
      }
    }
  }

  // 2. Date extraction:
  let year = null, month = null, day = null;
  
  // Pattern A: Day Month Year (e.g. 15 Eki 2026 or 15 Oct 2026)
  const dmyWords = lower.match(/\b(\d{1,2})\s+([a-zA-ZğüşıöçĞÜŞİÖÇ]+)\s+(\d{4})\b/);
  if (dmyWords && MONTH_NAMES_STUDIO[dmyWords[2]] !== undefined) {
    day = parseInt(dmyWords[1], 10);
    month = MONTH_NAMES_STUDIO[dmyWords[2]];
    year = parseInt(dmyWords[3], 10);
  }
  
  // Pattern B: Month Day, Year (e.g. Oct 15, 2026)
  if (year === null) {
    const mdyWords = lower.match(/\b([a-zA-ZğüşıöçĞÜŞİÖÇ]+)\s+(\d{1,2})[,\s]+(\d{4})\b/);
    if (mdyWords && MONTH_NAMES_STUDIO[mdyWords[1]] !== undefined) {
      month = MONTH_NAMES_STUDIO[mdyWords[1]];
      day = parseInt(mdyWords[2], 10);
      year = parseInt(mdyWords[3], 10);
    }
  }
  
  // Pattern C: DD.MM.YYYY or DD/MM/YYYY
  if (year === null) {
    const numMatch = lower.match(/\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b/);
    if (numMatch) {
      day = parseInt(numMatch[1], 10);
      month = parseInt(numMatch[2], 10) - 1;
      year = parseInt(numMatch[3], 10);
    }
  }

  // Pattern D: YYYY-MM-DD
  if (year === null) {
    const isoMatch = lower.match(/\b(\d{4})[./-](\d{1,2})[./-](\d{1,2})\b/);
    if (isoMatch) {
      year = parseInt(isoMatch[1], 10);
      month = parseInt(isoMatch[2], 10) - 1;
      day = parseInt(isoMatch[3], 10);
    }
  }

  if (year !== null && month !== null && day !== null) {
    const d = new Date(year, month, day);
    if (hour !== null) {
      d.setHours(hour, minute, 0, 0);
    } else {
      d.setHours(0, 0, 0, 0);
    }
    return { date: d, hasTime: hour !== null, hour, minute };
  }
  
  return null;
}

function formatDateISO(date) {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

// ── Tablo Satırlarını İnceleme (Videolar & Shorts) ─────────────
function inspectTableRows(rows) {
  const parsedRows = [];
  if (!rows || rows.length === 0) return parsedRows;

  rows.forEach(row => {
    try {
      const titleEl = queryShadow('#video-title', row) || queryShadow('.video-title', row);
      const visEl = queryShadow('#visibility-column', row) || 
                    queryShadow('.tablecell-visibility', row) || 
                    queryShadow('.visibility-cell', row) || 
                    queryShadow('[id*="visibility"]', row);
      const dateEl = queryShadow('#date-column', row) || 
                     queryShadow('.tablecell-date', row) || 
                     queryShadow('.date-cell', row) || 
                     queryShadow('[id*="date"]', row);
      
      const title = titleEl ? titleEl.textContent.trim() : "";
      const visText = (visEl ? visEl.textContent : "").toLowerCase().trim();
      const dateText = (dateEl ? dateEl.textContent : "").trim();
      const fullText = (row.textContent || "").trim();
      
      const isScheduled = visText.includes("planla") || 
                          visText.includes("schedul") || 
                          visText.includes("geplant") || 
                          visText.includes("programad") ||
                          dateText.toLowerCase().includes("planla") ||
                          dateText.toLowerCase().includes("schedul");
                          
      const isPublic = visText.includes("herkese açık") || 
                       visText.includes("public") || 
                       visText.includes("öffentlich") ||
                       visText.includes("públic");

      const visDt = extractStudioDateTime(visText);
      const dateDt = extractStudioDateTime(dateText);
      const combinedDt = extractStudioDateTime(`${dateText} ${visText}`);
      const fullDt = extractStudioDateTime(fullText);
      
      let dt = null;
      if (combinedDt && combinedDt.hasTime) dt = combinedDt;
      else if (visDt && visDt.hasTime) dt = visDt;
      else if (dateDt && dateDt.hasTime) dt = dateDt;
      else if (combinedDt) dt = combinedDt;
      else if (visDt) dt = visDt;
      else if (dateDt) dt = dateDt;
      else if (fullDt) dt = fullDt;

      parsedRows.push({
        title,
        isScheduled,
        isPublic,
        visText,
        dateText,
        dt
      });
    } catch (e) {
      console.warn("[YT-OTO] Satır analizi hatası:", e);
    }
  });

  return parsedRows;
}

// Hem Videolar hem Shorts sekmelerini kontrol eder
async function inspectStudioContentTables() {
  const currentTabRows = document.querySelectorAll('ytcp-video-row');
  const allParsedRows = [];
  
  if (currentTabRows && currentTabRows.length > 0) {
    allParsedRows.push(...inspectTableRows(currentTabRows));
  }
  
  // Sekmeler arası geçiş yapıp diğer sekmeyi de tara
  const tabs = queryShadowAll('ytcp-navigation-tabs tp-yt-paper-tab, #tabs tp-yt-paper-tab, paper-tab, ytcp-navigation-tabs [role="tab"]');
  let currentActiveTab = null;
  let otherTabToInspect = null;
  
  for (const t of tabs) {
    const isSelected = t.classList.contains('iron-selected') || 
                       t.getAttribute('aria-selected') === 'true';
    if (isSelected) currentActiveTab = t;
  }
  
  for (const t of tabs) {
    const text = (t.textContent || '').trim().toLowerCase();
    const isSelected = t.classList.contains('iron-selected') || 
                       t.getAttribute('aria-selected') === 'true';
    if (!isSelected && (text.includes('short') || text.includes('video'))) {
      otherTabToInspect = t;
      break;
    }
  }
  
  if (otherTabToInspect && currentActiveTab) {
    try {
      console.log(`[YT-OTO] 🔍 Plan analizi için diğer sekme inceleniyor: ${otherTabToInspect.textContent.trim()}...`);
      clickElementReliably(otherTabToInspect);
      await new Promise(r => setTimeout(r, 700));
      const otherTabRows = document.querySelectorAll('ytcp-video-row');
      if (otherTabRows && otherTabRows.length > 0) {
        allParsedRows.push(...inspectTableRows(otherTabRows));
      }
      // Orijinal sekmeye geri dön
      clickElementReliably(currentActiveTab);
      await new Promise(r => setTimeout(r, 500));
    } catch (e) {
      console.warn("[YT-OTO] Sekmeler arası tarama hatası:", e);
      try { clickElementReliably(currentActiveTab); } catch (_) {}
    }
  }
  
  return allParsedRows;
}

// ── Akıllı Slot Hesaplama Motoru ──────────────────────────────
function calculateNextSlotAfter(settings, latestDate) {
  const publishHours = (settings && Array.isArray(settings.publishHours) && settings.publishHours.length > 0)
    ? settings.publishHours
    : ["14:00", "18:00", "21:00"];
    
  const slots = publishHours.map(s => {
    const parts = s.split(':').map(Number);
    return { h: parts[0] || 0, m: parts[1] || 0, str: s };
  }).sort((a, b) => (a.h * 60 + a.m) - (b.h * 60 + b.m));

  const latestMinutes = latestDate.getHours() * 60 + latestDate.getMinutes();
  
  // Aynı gün içerisinde bu saatten sonraki ilk boş slot
  const nextSlotToday = slots.find(s => (s.h * 60 + s.m) > latestMinutes);
  
  if (nextSlotToday) {
    const targetDate = new Date(latestDate.getFullYear(), latestDate.getMonth(), latestDate.getDate(), nextSlotToday.h, nextSlotToday.m, 0);
    return {
      date: targetDate,
      timeStr: nextSlotToday.str,
      dateStr: formatDateISO(targetDate)
    };
  }
  
  // Günlük tüm slotlar dolduysa sonraki günün ilk slotu
  const nextDay = new Date(latestDate.getFullYear(), latestDate.getMonth(), latestDate.getDate() + 1);
  const firstSlot = slots[0];
  const targetDate = new Date(nextDay.getFullYear(), nextDay.getMonth(), nextDay.getDate(), firstSlot.h, firstSlot.m, 0);
  return {
    date: targetDate,
    timeStr: firstSlot.str,
    dateStr: formatDateISO(targetDate)
  };
}

function calculateNearestFutureSlot(settings, now = new Date()) {
  const publishHours = (settings && Array.isArray(settings.publishHours) && settings.publishHours.length > 0)
    ? settings.publishHours
    : ["14:00", "18:00", "21:00"];
    
  const slots = publishHours.map(s => {
    const parts = s.split(':').map(Number);
    return { h: parts[0] || 0, m: parts[1] || 0, str: s };
  }).sort((a, b) => (a.h * 60 + a.m) - (b.h * 60 + b.m));

  // YouTube Studio en az 10-15dk ileriye planlama kabul eder, 15dk güvenlik payı bırak
  const nowMinutes = now.getHours() * 60 + now.getMinutes() + 15;
  const slotToday = slots.find(s => (s.h * 60 + s.m) >= nowMinutes);
  if (slotToday) {
    const targetDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), slotToday.h, slotToday.m, 0);
    return {
      date: targetDate,
      timeStr: slotToday.str,
      dateStr: formatDateISO(targetDate)
    };
  }
  
  // Bugünün tüm saatleri geçtiyse yarının ilk slotu
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const firstSlot = slots[0];
  const targetDate = new Date(tomorrow.getFullYear(), tomorrow.getMonth(), tomorrow.getDate(), firstSlot.h, firstSlot.m, 0);
  return {
    date: targetDate,
    timeStr: firstSlot.str,
    dateStr: formatDateISO(targetDate)
  };
}

// YouTube Studio'daki video listesine bakıp sıradaki planlama slotunu belirler
async function determineNextPublishSlot(channelSettings, isShorts = false) {
  const rows = await inspectStudioContentTables();
  console.log(`[YT-OTO] Toplam incelenen Studio satır sayısı: ${rows.length}`);
  
  const now = new Date();
  
  // 1. Geleceğe planlanmış videoları bul
  const scheduledRows = rows.filter(r => r.isScheduled && r.dt && r.dt.date > now);
  
  if (scheduledRows.length > 0) {
    // Tarihe göre sırala (en ileri tarihteki sonuncudur)
    scheduledRows.sort((a, b) => a.dt.date.getTime() - b.dt.date.getTime());
    const latestRow = scheduledRows[scheduledRows.length - 1];
    const latestDate = latestRow.dt.date;
    console.log(`[YT-OTO] 📅 En son planlanmış video bulundu: "${latestRow.title}" (${latestDate.toLocaleString('tr-TR')})`);
    
    const nextSlot = calculateNextSlotAfter(channelSettings, latestDate);
    return {
      targetDate: nextSlot.date,
      targetTimeStr: nextSlot.timeStr,
      targetDateStr: nextSlot.dateStr,
      reason: `Son planlanan videodan (${latestDate.toLocaleDateString('tr-TR')} ${latestRow.dt.hasTime ? latestDate.toLocaleTimeString('tr-TR', {hour:'2-digit', minute:'2-digit'}) : ''}) sonraki boş saat`
    };
  }
  
  // 2. Planlı video yoksa veya en son video "Herkese açık" ise gelecekteki en yakın saati seç
  const publicOrLatestRows = rows.filter(r => r.isPublic || (r.dt && r.dt.date <= now));
  const latestDesc = publicOrLatestRows.length > 0 ? "Son video herkese açık / yayınlanmış" : "Tabloda planlı video bulunamadı";
  console.log(`[YT-OTO] ℹ️ ${latestDesc}. Gelecekteki en yakın yayın saati hesaplanıyor...`);
  
  const nearestSlot = calculateNearestFutureSlot(channelSettings, now);
  return {
    targetDate: nearestSlot.date,
    targetTimeStr: nearestSlot.timeStr,
    targetDateStr: nearestSlot.dateStr,
    reason: `${latestDesc} → En yakın yayın saati`
  };
}

function scrapeLastScheduledDateFromDOM() {
  const rows = document.querySelectorAll('ytcp-video-row');
  const parsed = inspectTableRows(rows);
  const scheduled = parsed.filter(r => r.isScheduled && r.dt);
  if (scheduled.length > 0) {
    scheduled.sort((a, b) => a.dt.date.getTime() - b.dt.date.getTime());
    return scheduled[scheduled.length - 1].dt.date;
  }
  return null;
}

function parseStudioDateString(dateStr) {
  let s = dateStr.replace(/[\n\r]+/g, " ").trim();
  
  const dmyMatch = s.match(/(\d{1,2})[./-](\d{1,2})[./-](\d{4})/);
  if (dmyMatch) {
    return new Date(parseInt(dmyMatch[3]), parseInt(dmyMatch[2]) - 1, parseInt(dmyMatch[1]));
  }
  
  const ymdMatch = s.match(/(\d{4})[./-](\d{1,2})[./-](\d{1,2})/);
  if (ymdMatch) {
    return new Date(parseInt(ymdMatch[1]), parseInt(ymdMatch[2]) - 1, parseInt(ymdMatch[3]));
  }
  
  const months = {
    // English abbreviations
    jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
    // Turkish full names
    ocak: 0, subat: 1, şubat: 1, mart: 2, nisan: 3, mayis: 4, mayıs: 4, haziran: 5, temmuz: 6, agustos: 7, ağustos: 7, eylul: 8, eylül: 8, ekim: 9, kasim: 10, kasım: 10, aralik: 11, aralık: 11,
    // Turkish 3-letter abbreviations
    oca: 0, sub: 1, şub: 1, mar: 2, nis: 3, may: 4, haz: 5, tem: 6, agu: 7, ağu: 7, eyl: 8, eki: 9, kas: 10, ara: 11
  };
  
  s = s.toLowerCase();
  
  const yearMatch = s.match(/\d{4}/);
  if (!yearMatch) return null;
  const year = parseInt(yearMatch[0]);
  
  const dayMatch = s.match(/\b\d{1,2}\b/);
  if (!dayMatch) return null;
  const day = parseInt(dayMatch[0]);
  
  let month = 0;
  let foundMonth = false;
  for (const [key, val] of Object.entries(months)) {
    if (s.includes(key)) {
      month = val;
      foundMonth = true;
      break;
    }
  }
  
  if (foundMonth) {
    return new Date(year, month, day);
  }
  
  const d = new Date(dateStr);
  if (!isNaN(d.getTime())) return d;
  
  return null;
}

function getStudioCountryCode() {
  try {
    if (window.yt && window.yt.config_ && window.yt.config_.GL) {
      return window.yt.config_.GL.toUpperCase();
    }
  } catch (e) {}
  try {
    if (window.ytcpConfig && window.ytcpConfig.country) {
      return window.ytcpConfig.country.toUpperCase();
    }
  } catch (e) {}
  try {
    const lang = navigator.language || "en-US";
    const parts = lang.split("-");
    if (parts.length > 1) {
      return parts[1].toUpperCase();
    }
  } catch (e) {}
  return "TR";
}

const COUNTRY_TIMEZONE_MAP = {
  "TR": "Europe/Istanbul",
  "DE": "Europe/Berlin",
  "FR": "Europe/Paris",
  "GB": "Europe/London",
  "US": "America/New_York",
  "CA": "America/Toronto",
  "AU": "Australia/Sydney",
  "RU": "Europe/Moscow",
  "JP": "Asia/Tokyo",
  "KR": "Asia/Seoul",
  "IN": "Asia/Kolkata",
  "BR": "America/Sao_Paulo",
  "MX": "America/Mexico_City",
  "ES": "Europe/Madrid",
  "IT": "Europe/Rome",
  "NL": "Europe/Amsterdam",
  "SE": "Europe/Stockholm",
  "NO": "Europe/Oslo",
  "FI": "Europe/Helsinki",
  "DK": "Europe/Copenhagen",
  "UA": "Europe/Kyiv",
  "GR": "Europe/Athens",
  "ID": "Asia/Jakarta",
  "TH": "Asia/Bangkok",
  "VN": "Asia/Ho_Chi_Minh",
  "AZ": "Asia/Baku"
};


function getPageLanguage() {
  let lang = document.documentElement.lang || document.querySelector('html')?.getAttribute('lang');
  if (lang) {
    return lang.split('-')[0].split('_')[0].toLowerCase();
  }
  return navigator.language || 'tr';
}

function formatDateForStudio(date) {
  const pageLang = getPageLanguage();
  return date.toLocaleDateString(pageLang, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

function formatTimeForStudio(date) {
  const pageLang = getPageLanguage();
  const tempStr = date.toLocaleTimeString(pageLang, { hour: '2-digit', minute: '2-digit' });
  const is12Hour = /AM|PM/i.test(tempStr);
  
  let hours = date.getHours();
  let minutes = date.getMinutes();
  
  if (is12Hour) {
    let ampm = hours >= 12 ? 'PM' : 'AM';
    let displayHours = hours % 12;
    displayHours = displayHours ? displayHours : 12;
    let minStr = minutes.toString().padStart(2, '0');
    return `${displayHours}:${minStr} ${ampm}`;
  } else {
    let hrStr = hours.toString().padStart(2, '0');
    let minStr = minutes.toString().padStart(2, '0');
    return `${hrStr}:${minStr}`;
  }
}

function findScheduleRadioButton() {
  const selectors = [
    '#schedule-radio-button',
    '#schedule-button',
    '#second-container-expand-button',
    'tp-yt-paper-radio-button[name="schedule"]',
    'tp-yt-paper-radio-button#schedule-button',
    '#schedule-section',
    '#schedule-container',
    '[name="schedule"]',
    '[id*="schedule"]',
    '[aria-label*="Schedule"]',
    '[aria-label*="Planla"]',
    '[aria-label*="Programar"]',
    '[aria-label*="Planen"]'
  ];
  for (const sel of selectors) {
    const el = queryShadow(sel);
    if (el && isVisible(el)) return el;
  }

  // Fallback: search for elements with multi-language schedule keywords
  const scheduleKeywords = [
    "planlayın", "planla", "schedule", "programar", "programada", "planen", "geplant",
    "programmer", "запланировать", "programado"
  ];
  const allElements = queryShadowAll('tp-yt-paper-radio-button, paper-radio-button, ytcp-radio-button, div[role="radio"], button, div, span');
  for (const el of allElements) {
    const text = (el.textContent || '').trim().toLowerCase();
    if (scheduleKeywords.some(kw => text === kw || text.includes(kw))) {
      if (isVisible(el)) {
        if (el.tagName.includes('BUTTON') || el.tagName.includes('RADIO') || el.getAttribute('role') === 'radio') {
          return el;
        }
        const radio = el.querySelector('tp-yt-paper-radio-button, paper-radio-button, ytcp-radio-button') || 
                      el.closest('tp-yt-paper-radio-button, paper-radio-button, ytcp-radio-button, [role="radio"]');
        if (radio && isVisible(radio)) return radio;
        return el;
      }
    }
  }
  return null;
}

function findDateInput() {
  return queryShadow('ytcp-date-picker input') || 
         queryShadow('ytcp-date-picker #input') || 
         queryShadow('#datepicker-trigger input') ||
         queryShadow('input[aria-label*="date"]') ||
         queryShadow('input[aria-label*="tarih"]') ||
         queryShadow('input[id*="date"]') ||
         queryShadow('input[class*="date"]');
}

function findTimeInput() {
  return queryShadow('ytcp-time-of-day-picker input') || 
         queryShadow('ytcp-time-of-day-picker #input') || 
         queryShadow('#time-of-day-trigger input') ||
         queryShadow('input[aria-label*="time"]') ||
         queryShadow('input[aria-label*="saat"]') ||
         queryShadow('input[id*="time"]') ||
         queryShadow('input[class*="time"]');
}

function getActiveChannelNameFromDOM() {
  const entityNameEl = queryShadow('ytcp-navigation-drawer #entity-name') || 
                       queryShadow('#entity-name') || 
                       document.querySelector('#entity-name') ||
                       queryShadow('.entity-name');
  if (entityNameEl) {
    const text = entityNameEl.innerText || entityNameEl.textContent || "";
    return text.split("\n")[0].trim();
  }
  return null;
}

function setPickerValue(inputEl, value, isTime = false) {
  const parentTag = isTime ? 'ytcp-time-of-day-picker' : 'ytcp-date-picker';
  const parent = inputEl ? (inputEl.closest(parentTag) || inputEl.parentElement) : queryShadow(parentTag);
  
  if (parent) {
    if (isTime) {
      if (parent.value !== undefined) parent.value = value;
      if (parent.time !== undefined) parent.time = value;
      if (parent.timeText !== undefined) parent.timeText = value;
      if (parent.formattedTime !== undefined) parent.formattedTime = value;
    } else {
      if (parent.value !== undefined) parent.value = value;
      if (parent.date !== undefined) parent.date = value;
      if (parent.dateText !== undefined) parent.dateText = value;
      if (parent.formattedDate !== undefined) parent.formattedDate = value;
    }
    
    // Also try setting the properties on the internal trigger component
    const trigger = queryShadow('ytcp-text-dropdown-trigger', parent) || queryShadow('#trigger', parent);
    if (trigger) {
      if (trigger.value !== undefined) trigger.value = value;
      if (trigger.text !== undefined) trigger.text = value;
    }
    
    // Update the visual span text
    const span = queryShadow('.dropdown-trigger-text', parent) || queryShadow('span', parent);
    if (span) {
      span.textContent = value;
    }
    
    parent.dispatchEvent(new Event('change', { bubbles: true }));
    parent.dispatchEvent(new Event('value-changed', { bubbles: true }));
    parent.dispatchEvent(new Event(isTime ? 'time-changed' : 'date-changed', { bubbles: true }));
  }

  if (inputEl) {
    inputEl.focus();
    inputEl.value = value;
    
    inputEl.dispatchEvent(new Event('input', { bubbles: true }));
    inputEl.dispatchEvent(new Event('change', { bubbles: true }));
    inputEl.dispatchEvent(new Event('value-changed', { bubbles: true }));
    
    inputEl.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
    inputEl.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
    inputEl.dispatchEvent(new Event('blur', { bubbles: true }));
  }
  
  if (parent) {
    parent.dispatchEvent(new Event('blur', { bubbles: true }));
  }
}

// archiveVideoOnBackend artık adım navigasyonundan sonra çağrılır
// archiveVideoOnBackend artık adım navigasyonundan sonra çağrılır ve sıradaki kuyruktaki videoyu tetikler
async function archiveVideoOnBackend(folder) {
  try {
    const res = await fetchFromBackground(`http://127.0.0.1:8000/api/output/${encodeURIComponent(folder)}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ youtube: true })
    });
    if (res.ok) {
      const data = typeof res.json === "function" ? await res.json() : res;
      console.log(`[YT-OTO] ✅ YouTube durumu güncellendi:`, data);
      
      // Yükleme kuyruğunu al ve sıradaki videoya geç
      chrome.storage.local.get(["yt_upload_queue"], (result) => {
        let queue = result.yt_upload_queue || [];
        
        // Tamamlanan videoyu kuyruktan çıkar (folder veya channel_id+plan_id ile eşleştir)
        const before = queue.length;
        queue = queue.filter(q => q.folder !== folder);
        console.log(`[YT-OTO] Kuyruktan çıkarıldı: ${before - queue.length} öğe. Kalan: ${queue.length}`);
        
        chrome.storage.local.set({ yt_upload_queue: queue }, () => {
          if (queue.length > 0) {
            const nextVideo = queue[0];
            // GÜVENLİK: nextVideo kendi kanalına ait, timestamp yenile ama
            // _switched_account bayrağını KALDIRMA — startAutoUpload kanal
            // kontrolü yaparak gerekirse hesap geçişi yapacak.
            const pendingNext = {
              ...nextVideo,
              timestamp: Date.now(),
              // _switched_account intentionally NOT set — channel will be verified
            };
            
            chrome.storage.local.set({ yt_studio_pending: pendingNext }, () => {
              showNotification(`🎬 Sıradaki kanala geçiliyor: ${pendingNext.channel_name || pendingNext.channel_id} (${pendingNext.title})`);
              console.log(`[YT-OTO] ➡️ Sıradaki video hazırlandı: ${pendingNext.channel_name} / ${pendingNext.title} / ${pendingNext.video_path}`);
              
              // Backend'deki bekleyen kaydı da senkronize et
              fetchFromBackground("http://127.0.0.1:8000/api/extension/pending-upload", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ payload: pendingNext, queue: queue.slice(1) })
              }).catch(() => {});

              setTimeout(() => {
                location.href = "https://studio.youtube.com";
              }, 3000);
            });
          } else {
            if (data.archived) {
              showNotification("📦 Tüm platformlara yüklendi! Video 'Yüklenen' klasörüne taşındı.");
            } else {
              showNotification("✅ YouTube yükleme durumu güncellendi!");
            }
          }
        });
      });
    }
  } catch (e) {
    console.error("[YT-OTO] YouTube status update failed:", e);
  }
}

// autoNavigateSteps bittikten sonra archive'ı tetikle
function autoNavigateStepsAndArchive(video) {
  const folder = video.folder;
  console.log("[YT-OTO] Otomatik adım ilerletme başlatıldı...");

  let stepAttempts = 0;
  let uploadFailed = false;
  const MAX_WAIT_PER_STEP = 300;

  function checkUploadLimitError() {
    const dialog = queryShadow('ytcp-uploads-dialog');
    if (!dialog) return false;
    const text = dialog.textContent.toLowerCase();
    const errorKeywords = [
      "sınırına ulaşıldı",
      "limit reached",
      "günlük yükleme",
      "daily upload",
      "too many videos",
      "yükleme sınırı",
      "daily limit",
      "günlük sınır"
    ];
    for (const kw of errorKeywords) {
      if (text.includes(kw)) return true;
    }
    const errorArea = queryShadow('.error-area') || queryShadow('#error-message') || queryShadow('.error-message-text');
    if (errorArea) {
      const errText = errorArea.textContent.toLowerCase();
      for (const kw of errorKeywords) {
        if (errText.includes(kw)) return true;
      }
    }
    return false;
  }

  function isUploadComplete() {
    const progressEl = queryShadow('ytcp-video-upload-progress');
    if (progressEl) {
      const text = progressEl.textContent.toLowerCase();
      if (text.includes("upload complete") || text.includes("yükleme tamamlandı") ||
          text.includes("processing") || text.includes("işleniyor") ||
          text.includes("100%")) return true;
    }
    const bar = queryShadow('ytcp-video-upload-progress tp-yt-paper-progress, ytcp-linear-progress');
    if (bar) {
      const value = parseFloat(bar.getAttribute('value') || bar.style.width || '0');
      if (value >= 100) return true;
    }
    const dialog = queryShadow('ytcp-uploads-dialog');
    if (!dialog) return false;
    const hasProgress = queryShadow('ytcp-video-upload-progress');
    if (!hasProgress) return true;
    return false;
  }

  function isNextButtonReady() {
    const nextBtn = queryShadow('#next-button');
    if (!nextBtn || !isVisible(nextBtn)) return false;
    if (nextBtn.hasAttribute('disabled')) return false;
    if (nextBtn.getAttribute('aria-disabled') === 'true') return false;
    return true;
  }

  async function tryStep() {
    const dialog = queryShadow('ytcp-uploads-dialog');
    if (!dialog) {
      if (uploadFailed) {
        console.log("[YT-OTO] Dialog kapandı fakat yükleme limit hatası aldığı için arşivlenmedi.");
        return;
      }
      console.log("[YT-OTO] Dialog kapandı.");
      archiveVideoOnBackend(folder);
      return;
    }

    if (checkUploadLimitError()) {
      uploadFailed = true;
      console.error("[YT-OTO] ⚠️ HATA: YouTube Günlük Yükleme Sınırına Ulaşıldı!");
      showFloatingInstruction("error", "⚠️ YouTube Günlük Yükleme Sınırına Ulaşıldı! Yükleme durduruldu, video arşivlenmedi.");
      showNotification("⚠️ Günlük Yükleme Sınırı Aşıldı! Video arşivlenmedi.");
      return;
    }

    // Son adım: Visibility / Schedule sayfası
    const doneBtn = queryShadow('#done-button');
    const doneBtnVisible = doneBtn && isVisible(doneBtn);

    if (doneBtnVisible) {
      console.log("[YT-OTO] ✅ Son adım (Görünürlük / Visibility) ulaşıldı.");

      // 1. Planlayın radio butonunu bul ve seç
      const scheduleRadio = findScheduleRadioButton();
      if (scheduleRadio) {
        const isAlreadyChecked = scheduleRadio.checked || scheduleRadio.hasAttribute('checked') || scheduleRadio.getAttribute('aria-checked') === 'true';
        if (!isAlreadyChecked) {
          clickElementReliably(scheduleRadio);
          console.log("[YT-OTO] Planlayın seçeneği tıklandı. Date/time picker bekleniyor...");
          // Schedule radio tıklandıktan sonra picker render için daha uzun bekle
          setTimeout(tryStep, 2000);
          return;
        }
      } else {
        console.warn("[YT-OTO] Planlayın seçeneği bulunamadı.");
      }

      // 2. Tarih ve saati ayarla
      const dateInput = findDateInput();
      const timeInput = findTimeInput();

      if (!dateInput || !timeInput) {
        // Schedule radio seçildi ama date/time henüz render olmadı — kısa süre bekle
        if (stepAttempts < MAX_WAIT_PER_STEP) {
          stepAttempts++;
          if (stepAttempts % 5 === 0) {
            console.log(`[YT-OTO] Tarih/saat alanları bekleniyor... (${stepAttempts}s)`);
          }
          setTimeout(tryStep, 1000);
        } else {
          // Zaman aşımı: Done'u doğrudan tıkla
          console.warn("[YT-OTO] Tarih/saat bekleme zaman aşımı — Done/Yayınla butonuna doğrudan tıklanıyor.");
          const freshDone = queryShadow('#done-button');
          if (freshDone && isVisible(freshDone) && !freshDone.hasAttribute('disabled') && freshDone.getAttribute('aria-disabled') !== 'true') {
            clickElementReliably(freshDone);
            showNotification("⚠️ Planlama tarihi ayarlanamadı, video yayınlandı.");
            archiveVideoOnBackend(folder);
          }
        }
        return;
      }

      if (dateInput && timeInput) {
        const channelKey = video.channel_id || video.channel_name || getActiveStudioChannelId();
        
        let targetDate = null;
        if (video._schedulePlan && video._schedulePlan.targetDate) {
          targetDate = new Date(video._schedulePlan.targetDate);
        } else if (video.schedule_date) {
          const [yyyy, mm, dd] = video.schedule_date.split("-").map(Number);
          targetDate = new Date(yyyy, mm - 1, dd, 14, 0, 0);
        } else {
          // Eğer önceden hesaplanmadıysa anlık olarak kanal ayarlarından ve DOM'dan hesapla
          try {
            const chanSettings = await getChannelSettings(channelKey);
            const plan = await determineNextPublishSlot(chanSettings, !!video.shorts_mode);
            targetDate = plan.targetDate;
            video._schedulePlan = plan;
          } catch (e) {
            console.warn("[YT-OTO] Hedef plan belirleme hatası:", e);
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            tomorrow.setHours(14, 0, 0, 0);
            targetDate = tomorrow;
          }
        }

        const dateText = formatDateForStudio(targetDate);
        const timeText = formatTimeForStudio(targetDate);
        
        console.log(`[YT-OTO] Planlama Ayarlanıyor: Tarih="${dateText}", Saat="${timeText}" (Sebep: ${video._schedulePlan?.reason || 'Otomatik'})`);
        
        setPickerValue(dateInput, dateText, false);
        setPickerValue(timeInput, timeText, true);

        // Kaydedilen tarihi hafızaya al
        chrome.storage.local.set({ [`last_scheduled_${channelKey}`]: formatDateISO(targetDate) });
        
        let doneTimeout = null;
        let isAutomationStopped = false;
        
        const stopAutomation = (e) => {
          if (e && e.isTrusted === false) return;
          if (isAutomationStopped) return;
          isAutomationStopped = true;
          if (doneTimeout) {
            clearTimeout(doneTimeout);
            doneTimeout = null;
          }
          console.log("[YT-OTO] Manuel müdahale algılandı (Olay:", e ? e.type : "Bilinmeyen", "). Otomatik planlama durduruldu.");
          showFloatingInstruction("info", "Manuel planlama aktif. Tarih/saat seçip kendiniz kaydedin.");
          
          window.removeEventListener('click', stopAutomation, true);
          window.removeEventListener('keydown', stopAutomation, true);
        };
        
        window.addEventListener('click', stopAutomation, true);
        window.addEventListener('keydown', stopAutomation, true);
        
        doneTimeout = setTimeout(() => {
          if (isAutomationStopped) return;
          const freshDoneBtn = queryShadow('#done-button');
          if (!freshDoneBtn || !isVisible(freshDoneBtn)) {
            console.warn("[YT-OTO] Done butonu artık görünmüyor, yeniden deneniyor...");
            window.removeEventListener('click', stopAutomation, true);
            window.removeEventListener('keydown', stopAutomation, true);
            setTimeout(tryStep, 1000);
            return;
          }
          console.log("[YT-OTO] Planla/Bitti butonuna tıklanıyor...");
          clickElementReliably(freshDoneBtn);
          showNotification(`✅ Video başarıyla planlandı: ${dateText} ${timeText}`);
          archiveVideoOnBackend(folder);
          
          window.removeEventListener('click', stopAutomation, true);
          window.removeEventListener('keydown', stopAutomation, true);
        }, 2500);
      } // end if dateInput && timeInput
      return;
    }

    if (stepAttempts > MAX_WAIT_PER_STEP) {
      console.warn("[YT-OTO] Zaman aşımı.");
      showNotification("⚠️ Zaman aşımı. Manuel devam edin.");
      return;
    }

    // Çocuklara özel seçeneği (MFK)
    selectMadeForKidsOption(video._kidsRating || "VIDEO_MADE_FOR_KIDS_NOT_MFK");

    if (isNextButtonReady()) {
      stepAttempts = 0;
      removeFloatingInstruction();
      const nextBtn = queryShadow('#next-button');
      clickElementReliably(nextBtn);
      console.log("[YT-OTO] ▶ İleri / Next butonu tıklandı.");
      setTimeout(tryStep, 1800);
      return;
    }

    stepAttempts++;
    if (stepAttempts % 5 === 0) {
      console.log(`[YT-OTO] Adım ilerletme bekleniyor... (${stepAttempts}s)`);
    }
    setTimeout(tryStep, 1000);
  }

  // İlk başlamadan önce 5s bekle — YouTube Studio dialog render için zaman tanı
  setTimeout(tryStep, 5000);
}



// ── Polling Başlat ────────────────────────────────────────────

if (location.href.includes("studio.youtube.com")) {
  setInterval(() => {
    injectStudioContentActions();
    updateAnalyzeButtonVisibility();
  }, 2000);
}

if (location.href.includes("instagram.com")) {
  setInterval(() => {
    injectInstagramContentActions();
  }, 2000);
  setTimeout(injectInstagramContentActions, 600);
}

console.log("[YT-OTO] Content script loaded →", location.href);

// ── Fikir Giriş Raporu Modalı ──────────────────────────────────
function showScrapingSummary(addedCount, skippedCount, addedTitles, skippedTitles, channelName) {
  const existing = document.getElementById("yt-oto-summary-modal");
  if (existing) existing.remove();

  const modal = document.createElement("div");
  modal.id = "yt-oto-summary-modal";
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(12px);
    z-index: 10000000; display: flex; align-items: center; justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  `;

  const container = document.createElement("div");
  container.style.cssText = `
    background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px; width: 560px; max-width: 90%; padding: 28px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
    color: #f8fafc; display: flex; flex-direction: column; gap: 20px;
    animation: ytOtoFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  `;

  if (!document.getElementById("yt-oto-animation-styles")) {
    const styleSheet = document.createElement("style");
    styleSheet.id = "yt-oto-animation-styles";
    styleSheet.textContent = `
      @keyframes ytOtoFadeIn {
        from { opacity: 0; transform: scale(0.95) translateY(10px); }
        to { opacity: 1; transform: scale(1) translateY(0); }
      }
    `;
    document.head.appendChild(styleSheet);
  }

  const header = document.createElement("div");
  header.style.cssText = `
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 16px;
  `;
  header.innerHTML = `
    <div>
      <h3 style="margin: 0; font-size: 19px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
        💡 Fikir İşleme Raporu
      </h3>
      <span style="font-size: 12px; color: #94a3b8; font-family: monospace;">Kanal: ${channelName}</span>
    </div>
  `;
  container.appendChild(header);

  const body = document.createElement("div");
  body.style.cssText = `
    max-height: 380px; overflow-y: auto; display: flex; flex-direction: column; gap: 20px;
    padding-right: 4px;
  `;

  if (addedTitles && addedTitles.length > 0) {
    const addedSec = document.createElement("div");
    addedSec.innerHTML = `
      <h4 style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #34d399; display: flex; align-items: center; gap: 6px;">
        ✅ Yeni Eklenen Fikirler (${addedCount})
      </h4>
      <ul style="margin: 0; padding-left: 20px; font-size: 13.5px; color: #cbd5e1; line-height: 1.6;">
        ${addedTitles.map(t => `<li style="margin-bottom: 4px;">${t}</li>`).join("")}
      </ul>
    `;
    body.appendChild(addedSec);
  }

  if (skippedTitles && skippedTitles.length > 0) {
    const skippedSec = document.createElement("div");
    skippedSec.innerHTML = `
      <h4 style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #f43f5e; display: flex; align-items: center; gap: 6px;">
        🚫 Zaten Mevcut / Elenen Fikirler (${skippedCount})
      </h4>
      <p style="margin: 0 0 8px 20px; font-size: 12px; color: #94a3b8; font-style: italic;">
        (Yapay zeka mevcut içerik planındaki konularla semantik çakışmaları filtreledi)
      </p>
      <ul style="margin: 0; padding-left: 20px; font-size: 13.5px; color: #94a3b8; line-height: 1.6; list-style-type: circle;">
        ${skippedTitles.map(t => `<li style="margin-bottom: 4px;">${t}</li>`).join("")}
      </ul>
    `;
    body.appendChild(skippedSec);
  }

  if ((!addedTitles || addedTitles.length === 0) && (!skippedTitles || skippedTitles.length === 0)) {
    const emptyMsg = document.createElement("div");
    emptyMsg.style.cssText = "text-align: center; color: #94a3b8; font-size: 14px; padding: 20px 0;";
    emptyMsg.textContent = "Herhangi bir fikir işlenemedi.";
    body.appendChild(emptyMsg);
  }

  container.appendChild(body);

  const footer = document.createElement("div");
  footer.style.cssText = `
    display: flex; justify-content: flex-end; border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 16px; margin-top: 8px;
  `;
  const closeBtn = document.createElement("button");
  closeBtn.textContent = "Kapat";
  closeBtn.style.cssText = `
    background: #475569; color: #f8fafc; border: none; padding: 8px 20px;
    border-radius: 8px; font-size: 13.5px; font-weight: 600; cursor: pointer;
    transition: background 0.2s;
  `;
  closeBtn.addEventListener("mouseenter", () => closeBtn.style.background = "#64748b");
  closeBtn.addEventListener("mouseleave", () => closeBtn.style.background = "#475569");
  closeBtn.addEventListener("click", () => {
    modal.remove();
  });

  footer.appendChild(closeBtn);
  container.appendChild(footer);
  modal.appendChild(container);
  document.body.appendChild(modal);
}


// ── Gemini Web Automation Assistant ────────────────────────────

let geminiRunning = false;
let geminiConsole = null;
let geminiLogsList = [];
let geminiChannelsList = [];
let geminiQueue = [];
let geminiActiveTab = "single";

function logGemini(msg, type = "info") {
  console.log(`[GEMINI-AUTO] [${type.toUpperCase()}] ${msg}`);
  const timeStr = new Date().toLocaleTimeString();
  
  chrome.storage.local.get("gemini_auto_logs", (data) => {
    const list = (data && data.gemini_auto_logs && Array.isArray(data.gemini_auto_logs)) ? data.gemini_auto_logs : [];
    list.push({ time: timeStr, msg, type });
    geminiLogsList = list;
    chrome.storage.local.set({ gemini_auto_logs: list });
  });

  if (geminiConsole) {
    const color = type === "error" ? "#f43f5e" : (type === "success" ? "#10b981" : (type === "warning" ? "#f59e0b" : "#94a3b8"));
    const div = document.createElement("div");
    div.style.cssText = `color: ${color}; margin-bottom: 4px; font-size: 13px; line-height: 1.4;`;
    div.textContent = `[${timeStr}] ${msg}`;
    geminiConsole.appendChild(div);
    geminiConsole.scrollTop = geminiConsole.scrollHeight;
  }
}

function getApiUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["apiUrl"], (res) => {
      resolve((res.apiUrl || "http://127.0.0.1:8000").replace(/\/$/, ""));
    });
  });
}

function simulateTyping(el, value) {
  el.focus();
  if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
    el.value = value;
  } else {
    el.innerHTML = '';
    el.textContent = value;
  }
  
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  
  try {
    const textEvent = new TextEvent('textInput', {
      bubbles: true,
      cancelable: true,
      data: value
    });
    el.dispatchEvent(textEvent);
  } catch (e) {}
}

function clickSendButton() {
  const selectors = [
    'button[aria-label*="Send" i]',
    'button[aria-label*="Gönder" i]',
    'button[aria-label*="Generate" i]',
    'button[aria-label*="Oluştur" i]',
    'button[aria-label*="Create" i]',
    'button.send-button',
    'button[type="submit"]',
    'button:has(mat-icon[fonticon="arrow_upward"])',
    'button:has(mat-icon[data-mat-icon-name="arrow_upward"])',
    'button:has(mat-icon[fonticon="send"])',
    'button:has(mat-icon[data-mat-icon-name="send"])',
    'mat-icon[fonticon="arrow_upward"]',
    'mat-icon[data-mat-icon-name="arrow_upward"]',
    '[data-mat-icon-name="arrow_upward"]',
    'mat-icon[fonticon="send"]',
    '[data-mat-icon-name="send"]'
  ];
  
  for (let sel of selectors) {
    try {
      const el = document.querySelector(sel);
      if (el) {
        const btn = (el.tagName === 'MAT-ICON' || el.tagName === 'SPAN') ? (el.closest('button') || el) : el;
        if (isVisible(btn)) {
          btn.click();
          return true;
        }
      }
    } catch (e) {}
  }
  
  // Scans all mat-icons as fallback
  const matIcons = Array.from(document.querySelectorAll('mat-icon'));
  for (let icon of matIcons) {
    const iconName = (icon.getAttribute('fonticon') || icon.getAttribute('data-mat-icon-name') || '').toLowerCase();
    if (iconName === 'arrow_upward' || iconName === 'send' || iconName.includes('arrow')) {
      const btn = icon.closest('button') || icon;
      if (isVisible(btn)) {
        btn.click();
        return true;
      }
    }
  }
  
  return false;
}

function getTurnCount() {
  const selectors = ['model-response', 'model-turn', '.model-turn', '[data-turn-role="model"]', 'p-chat-turn', 'chat-turn'];
  for (let sel of selectors) {
    const els = document.querySelectorAll(sel);
    if (els.length > 0) return els.length;
  }
  return 0;
}

async function toggleTemporaryChatIfNeeded(useTempChat) {
  const isAlreadyTemp = document.body.textContent.includes("Geçici sohbet etkin") ||
                        document.body.textContent.includes("Temporary chat enabled") ||
                        (document.body.textContent.includes("Geçici sohbet") && (location.href.includes("temporary") || document.querySelector('.temporary-chat-indicator') || document.body.innerHTML.includes("temporary")));
  
  const selectors = [
    '[aria-label*="Geçici sohbet"]',
    '[aria-label*="Temporary chat"]',
    '[title*="Geçici sohbet"]',
    '[title*="Temporary chat"]'
  ];
  let btn = null;
  for (let sel of selectors) {
    btn = document.querySelector(sel);
    if (btn) break;
  }
  if (!btn) {
    const buttons = Array.from(document.querySelectorAll('button, div[role="button"], a'));
    for (let b of buttons) {
      const label = (b.getAttribute('aria-label') || b.title || b.textContent || '').toLowerCase();
      if (label.includes('geçici sohbet') || label.includes('temporary chat')) {
        btn = b;
        break;
      }
    }
  }

  if (useTempChat) {
    if (!isAlreadyTemp && btn) {
      logGemini("Geçici sohbet butonu tıklanıyor...", "info");
      btn.click();
      await new Promise(r => setTimeout(r, 2000));
    } else if (isAlreadyTemp) {
      logGemini("Geçici sohbet zaten aktif.", "info");
    }
  } else {
    // Normal sohbet modu istendi
    if (isAlreadyTemp && btn) {
      logGemini("Geçici sohbet kapatılıyor, normal sohbete geçiliyor...", "info");
      btn.click();
      await new Promise(r => setTimeout(r, 2000));
    } else {
      logGemini("Normal sohbet modu aktif.", "info");
    }
  }
}

async function startNewChat() {
  logGemini("Temiz ve bağımsız yeni sohbet oturumu açılıyor...", "info");

  // Eğer /images sayfasındaysak veya spesifik bir sohbet ID'sindeysek (/app/<id>) doğrudan ana /app'e yönlendir
  const currentPath = window.location.pathname;
  if (currentPath.includes('/images') || (currentPath.startsWith('/app/') && currentPath !== '/app')) {
    // 1. Önce SPA linklerini dene (sayfa yenilemeden ana sohbet ekranına geçebilmek için)
    const spaLinks = document.querySelectorAll('a[data-test-id="new-chat-button"], a[href="/app"], a[href*="/app"]');
    for (const link of spaLinks) {
      if (link && isVisible(link)) {
        try {
          link.click();
          await new Promise(r => setTimeout(r, 1200));
          if (!window.location.pathname.includes('/images') && window.location.pathname === '/app') {
            logGemini("Ana sohbet ekranına (/app) SPA ile geçildi.", "success");
            return true;
          }
        } catch (e) {}
      }
    }

    logGemini("Temiz sohbet için ana sayfaya (/app) yönlendiriliyor...", "info");
    const currentUrl = new URL(window.location.href);
    const authUser = currentUrl.searchParams.get("authuser");
    let target = "https://gemini.google.com/app";
    if (authUser) target += `?authuser=${authUser}`;
    window.location.href = target;
    return false; // Sayfa yeniden yüklenecek
  }

  // 1. Selector ile "Yeni sohbet" / "New chat" butonunu bul ve tıkla
  const selectors = [
    'a[data-test-id="new-chat-button"]',
    'button[data-test-id="new-chat-button"]',
    'a[href="/app"]',
    '[aria-label*="Yeni sohbet"]',
    '[aria-label*="New chat"]',
    '[title*="Yeni sohbet"]',
    '[title*="New chat"]',
    'button[aria-label*="Yeni sohbet"]',
    '.side-nav-new-chat-button'
  ];

  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && isVisible(el)) {
      try {
        el.click();
        await new Promise(r => setTimeout(r, 1200));
        return true;
      } catch (e) {}
    }
  }

  // 2. Metin içeren butonları ara
  const allBtns = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
  for (const b of allBtns) {
    const txt = (b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
    if (txt === "yeni sohbet" || txt === "new chat" || txt.includes("yeni sohbet") || txt.includes("new chat")) {
      if (isVisible(b)) {
        try {
          b.click();
          await new Promise(r => setTimeout(r, 1200));
          return true;
        } catch (e) {}
      }
    }
  }

  // 3. Eğer menü kapalıysa menüyü açıp tekrar dene
  const menuBtn = document.querySelector('button[data-test-id="side-nav-toggle"], [aria-label*="Menü"], [aria-label*="Menu"]');
  if (menuBtn && isVisible(menuBtn)) {
    try {
      menuBtn.click();
      await new Promise(r => setTimeout(r, 500));
      for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el && isVisible(el)) {
          el.click();
          await new Promise(r => setTimeout(r, 1200));
          return true;
        }
      }
    } catch (e) {}
  }

  return true;
}

async function waitForPromptInput(timeoutMs = 12000) {
  const start = Date.now();
  const selectors = [
    'div[contenteditable="true"][aria-label*="prompt" i]',
    'div[contenteditable="true"][aria-label*="resim" i]',
    'div[contenteditable="true"][aria-label*="image" i]',
    'div[contenteditable="true"][aria-label*="oluştur" i]',
    'div[contenteditable="true"][aria-label*="create" i]',
    'div[contenteditable="true"][aria-label*="describe" i]',
    'rich-textarea [contenteditable="true"]',
    'rich-textarea div[contenteditable="true"]',
    'div[contenteditable="true"]',
    'textarea',
    '[data-placeholder*="prompt" i]',
    '[data-placeholder*="resim" i]',
    '[data-placeholder*="image" i]',
    '[data-placeholder*="describe" i]',
    '[data-placeholder*="oluştur" i]',
    '[data-placeholder*="create" i]'
  ];
  while (Date.now() - start < timeoutMs) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && isVisible(el)) return el;
    }
    await new Promise(r => setTimeout(r, 500));
  }
  return null;
}

function isGeminiGenerating() {
  const stopSelectors = [
    'button[aria-label*="Stop"]',
    'button[aria-label*="Durdur"]',
    'button[aria-label*="stop"]',
    'button[aria-label*="durdur"]',
    '[title*="Stop"]',
    '[title*="Durdur"]'
  ];
  for (let sel of stopSelectors) {
    const btn = document.querySelector(sel);
    if (btn && isVisible(btn)) {
      return true;
    }
  }

  const loadingSelectors = [
    'mat-progress-bar',
    'mwc-linear-progress',
    '.generating',
    '.is-generating',
    '.loading',
    '.typing'
  ];
  for (let sel of loadingSelectors) {
    const el = document.querySelector(sel);
    if (el && isVisible(el)) {
      return true;
    }
  }

  return false;
}

async function waitForGeminiGeneration(initialTurns = null) {
  let isGenerating = true;
  let stableCount = 0;
  
  if (initialTurns !== null) {
    // 1. Yeni turn'ün başlamasını bekle (max 15 saniye)
    let turnStarted = false;
    const start = Date.now();
    while (Date.now() - start < 15000) {
      if (getTurnCount() > initialTurns || isGeminiGenerating()) {
        turnStarted = true;
        break;
      }
      await new Promise(r => setTimeout(r, 500));
    }
    if (!turnStarted) {
      console.warn("[YT-OTO] Yanıt sırası başlamadı, gönder butonu tekrar deneniyor...");
      clickSendButton();
      const retryStart = Date.now();
      while (Date.now() - retryStart < 8000) {
        if (getTurnCount() > initialTurns || isGeminiGenerating()) {
          turnStarted = true;
          break;
        }
        await new Promise(r => setTimeout(r, 500));
      }
    }
    if (turnStarted) {
      console.log("[YT-OTO] Yeni yanıt sırası başarıyla başladı.");
    } else {
      throw new Error("Gemini yeni senaryo yanıtını başlatamadı. Önceki videonun senaryosunu tekrarlamamak için işlem durduruldu.");
    }
  }

  // Yavaş başlangıçlar için ekstra 1.5 saniye bekle (spinner'ın/stop butonunun yüklenmesi için)
  await new Promise(r => setTimeout(r, 1500));

  while (isGenerating && (geminiRunning || geminiPlanRunning)) {
    await new Promise(r => setTimeout(r, 1000));
    const generatingNow = isGeminiGenerating();
    if (generatingNow) {
      stableCount = 0;
    } else {
      stableCount++;
      // En az 3 saniye stabil (false) kalmasını bekliyoruz
      if (stableCount >= 3) {
        isGenerating = false;
      }
    }
  }
}

function getLastTurnElement() {
  const turnSelectors = [
    'model-response', 'model-turn', '.model-turn',
    '[data-turn-role="model"]', 'p-chat-turn', 'chat-turn'
  ];
  for (const sel of turnSelectors) {
    const turns = document.querySelectorAll(sel);
    if (turns.length > 0) {
      return turns[turns.length - 1];
    }
  }
  return null;
}

function getLastResponseText() {
  const lastTurn = getLastTurnElement();
  if (lastTurn) {
    const allCodeBlocks = lastTurn.querySelectorAll('code-block, pre');
    if (allCodeBlocks.length > 1) {
      const turnText = (lastTurn.innerText || lastTurn.textContent || '').trim();
      if (turnText.length > 0) return turnText;
    } else if (allCodeBlocks.length === 1) {
      const txt = (allCodeBlocks[0].innerText || allCodeBlocks[0].textContent || '').trim();
      if (txt.length > 30) return txt;
    }
    const innerCode = lastTurn.querySelector('.markdown, div.markdown, .markdown-main-panel, message-content');
    if (innerCode) {
      const txt = (innerCode.innerText || innerCode.textContent || '').trim();
      if (txt.length > 30) return txt;
    }
    const turnText = (lastTurn.innerText || lastTurn.textContent || '').trim();
    if (turnText.length > 0) return turnText;
  }

  const selectors = [
    'model-response', 'model-turn', '.model-turn',
    'message-content', '.message-content',
    '.response-container-content', '[role="text"]',
    'code-block', 'pre', 'code', 'div.markdown', '.markdown',
    '[data-turn-role="model"]', 'p-chat-turn', 'chat-turn',
    '.markdown-main-panel', 'structured-content'
  ];

  let bestText = '';
  for (const sel of selectors) {
    const els = document.querySelectorAll(sel);
    if (els.length > 0) {
      const last = els[els.length - 1];
      const candidate = (last.innerText || last.textContent || '').trim();
      if (candidate.length > bestText.length) {
        bestText = candidate;
      }
    }
  }
  return bestText;
}

function getLastResponseImages() {
  const selectors = [
    'model-response', 'model-turn', '.model-turn',
    'message-content', '.message-content',
    '.response-container-content', '[role="text"]',
    'code-block', 'pre', 'code', 'div.markdown', '.markdown',
    '[data-turn-role="model"]', 'p-chat-turn', 'chat-turn',
    '.markdown-main-panel', 'structured-content'
  ];
  
  let lastContainer = null;
  for (let sel of selectors) {
    const els = document.querySelectorAll(sel);
    if (els.length > 0) {
      lastContainer = els[els.length - 1];
      break;
    }
  }
  
  if (lastContainer) {
    const images = Array.from(lastContainer.querySelectorAll('img'));
    const urls = images.map(img => img.src).filter(src => src && (
      src.includes('googleusercontent') || 
      src.includes('google') || 
      src.startsWith('blob:') || 
      src.startsWith('data:')
    ));
    if (urls.length > 0) return urls;
  }
  
  const allImgs = Array.from(document.querySelectorAll('img'));
  const validUrls = allImgs.map(img => img.src).filter(src => src && (
    src.includes('googleusercontent') || 
    src.includes('google') || 
    src.startsWith('blob:') || 
    src.startsWith('data:')
  ));
  
  if (validUrls.length > 0) {
    return [validUrls[validUrls.length - 1]];
  }
  
  return [];
}

function isAvatarOrIcon(img) {
  if (!img) return true;
  const src = img.src || img.currentSrc || "";
  if (!src) return true;
  
  // Exclude avatars and Google account profiles
  if (img.classList.contains('avatar') || img.classList.contains('mavatar-image') || 
      img.closest('.avatar-container') || img.closest('.user-avatar') || 
      img.closest('[aria-label*="Google Hesabı" i]') || img.closest('[aria-label*="Account" i]') ||
      img.closest('gem-user-avatar')) {
    return true;
  }
  
  // Exclude navigation, sidebar, headers
  if (img.closest('header') || img.closest('nav') || img.closest('.side-nav') || img.closest('mat-sidenav')) {
    return true;
  }
  
  // Exclude tiny icons (UI action buttons, emojis, icons)
  if ((img.naturalWidth > 0 && img.naturalWidth < 100) || (img.width > 0 && img.width < 100) || (img.clientWidth > 0 && img.clientWidth < 100)) {
    return true;
  }
  
  return false;
}

function getUnprocessedImages(beforeSrcs = null) {
  const isImageValid = (img) => {
    if (!img) return false;
    const src = img.src || img.currentSrc || "";
    if (!src) return false;
    if (beforeSrcs && (beforeSrcs.has(src) || (img.currentSrc && beforeSrcs.has(img.currentSrc)))) {
      return false;
    }
    if (img.getAttribute('data-yt-oto-processed') === 'true') {
      return false;
    }
    if (isAvatarOrIcon(img)) {
      return false;
    }
    
    const isValidSrc = (
      src.startsWith('http://') || 
      src.startsWith('https://') || 
      src.startsWith('blob:') || 
      src.startsWith('data:image')
    );
    return isValidSrc;
  };

  // 1. Önce görsel üretimi özel container'ları
  const containerSelectors = [
    'single-image img',
    'generated-image img',
    '.attachment-container img',
    'image-container img',
    '.image-container img',
    '.image-gallery img',
    '.generated-media img',
    'model-turn img',
    '.model-turn img',
    'message-content img',
    '.response-container-content img'
  ];
  
  for (const sel of containerSelectors) {
    const list = Array.from(document.querySelectorAll(sel)).filter(isImageValid);
    if (list.length > 0) return list;
  }

  // 2. Dokümandaki tüm geçerli görseller
  return Array.from(document.querySelectorAll('img')).filter(isImageValid);
}

async function navigateToResimlerGem() {
  logGemini("Resimler Gem'ine geçiş yapılıyor...", "info");

  // Eğer zaten /images sayfasındaysak devam et
  if (window.location.pathname.includes('/images')) {
    logGemini("Zaten Resimler Gem'indeyiz (/images).", "success");
    return true;
  }

  const selectors = [
    '[data-test-id="images-side-nav-entry-button"] a',
    'gem-nav-list-item[data-test-id="images-side-nav-entry-button"] a',
    '[data-test-id="images-side-nav-entry-button"]',
    'a[href="/images"]',
    'a[href*="/images"]',
    'a[aria-label="Resimler"]',
    'a[aria-label*="Resimler"]',
    'a[aria-label="Images"]',
    '[data-mat-icon-name="image_create"]'
  ];

  let targetEl = null;
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) {
      targetEl = el;
      break;
    }
  }

  if (!targetEl) {
    const navItems = document.querySelectorAll('gem-nav-list-item, a, button, [role="listitem"]');
    for (const item of navItems) {
      const text = (item.innerText || item.textContent || '').trim();
      const href = item.getAttribute('href') || (item.querySelector('a') ? item.querySelector('a').getAttribute('href') : '');
      if (text.includes("Resimler") || text.includes("Images") || (href && href.includes('/images'))) {
        targetEl = item.tagName === 'A' ? item : (item.querySelector('a') || item);
        break;
      }
    }
  }

  if (targetEl) {
    logGemini("Resimler Gem bağlantısı bulundu. Resimler moduna geçiliyor...", "info");
    try {
      targetEl.click();
    } catch(e) {
      const clickEvent = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
      targetEl.dispatchEvent(clickEvent);
    }
    await new Promise(r => setTimeout(r, 1500));
  } else {
    logGemini("Resimler Gem düğmesi menüde bulunamadı. Adrese doğrudan yönlendiriliyor (/images)...", "warning");
    const currentUrl = new URL(window.location.href);
    const authUser = currentUrl.searchParams.get("authuser");
    let targetUrl = "https://gemini.google.com/images";
    if (authUser) {
      targetUrl += `?authuser=${authUser}`;
    }
    window.location.href = targetUrl;
    return false;
  }

  const startTime = Date.now();
  while (Date.now() - startTime < 3500) {
    if (window.location.pathname.includes('/images')) {
      logGemini("Resimler Gem'i başarıyla açıldı.", "success");
      return true;
    }
    await new Promise(r => setTimeout(r, 500));
  }

  // Eğer SPA tıklamasıyla URL /images olmadıysa adrese doğrudan yönlendir
  if (!window.location.pathname.includes('/images')) {
    logGemini("Resimler Gem'ine adrese doğrudan yönlendiriliyor (/images)...", "info");
    const currentUrl = new URL(window.location.href);
    const authUser = currentUrl.searchParams.get("authuser");
    let targetUrl = "https://gemini.google.com/images";
    if (authUser) {
      targetUrl += `?authuser=${authUser}`;
    }
    window.location.href = targetUrl;
    return false;
  }

  logGemini("Resimler Gem hazır.", "info");
  return true;
}

async function waitForResponseImages(timeoutMs = 45000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const newImgs = getUnprocessedImages();
    if (newImgs.length > 0) {
      return newImgs;
    }
    await new Promise(r => setTimeout(r, 1000));
  }
  return [];
}

async function getBase64FromUrl(url, imgElement = null) {
  if (!url) return "";
  if (typeof url === 'string' && url.startsWith('data:image')) {
    return url;
  }
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch (fetchErr) {
    // Canvas fallback
    if (imgElement && imgElement.naturalWidth > 0) {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = imgElement.naturalWidth;
        canvas.height = imgElement.naturalHeight;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(imgElement, 0, 0);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.95);
        if (dataUrl && dataUrl.length > 100) return dataUrl;
      } catch (cErr) {}
    }
    // Background fetch fallback
    try {
      const bgRes = await fetchFromBackground(url, {}, true);
      if (bgRes && bgRes.ok && bgRes.data) {
        return `data:image/jpeg;base64,${bgRes.data}`;
      }
    } catch (bgErr) {}
    throw fetchErr;
  }
}

// Perchance text-to-image-plugin API aracılığıyla doğrudan arka planda görsel üretir
async function generateImageViaPerchanceAPI(imagePrompt, isShorts, isAvatar) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({
      type: "GENERATE_PERCHANCE_IMAGE",
      prompt: imagePrompt,
      isShorts: !!isShorts,
      isAvatar: !!isAvatar
    }, (res) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (res && res.ok && res.base64) {
        resolve(res.base64);
      } else {
        reject(new Error((res && res.error) || "Perchance API görsel oluşturamadı."));
      }
    });
  });
}

function cleanMarkdownJson(text) {
  if (!text || typeof text !== "string") return "{}";
  const parsed = robustCleanAndParseJson(text);
  if (parsed) {
    try {
      return JSON.stringify(parsed);
    } catch(e) {}
  }
  return text.trim();
}

function isValidScriptData(scriptData) {
  if (!scriptData) return false;
  if (Array.isArray(scriptData.scenes) && scriptData.scenes.length > 0) return true;
  if (Array.isArray(scriptData.messages) && scriptData.messages.length > 0) return true;
  if (typeof scriptData === 'object' && !Array.isArray(scriptData)) {
    const keys = Object.keys(scriptData);
    const langKeys = keys.filter(k => ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko", "ar", "hi", "zh", "nl", "pl", "sv"].includes(k.toLowerCase()));
    if (langKeys.length > 0) {
      return langKeys.some(lk => {
        const item = scriptData[lk];
        if (!item) return false;
        return (Array.isArray(item.scenes) && item.scenes.length > 0) ||
               (Array.isArray(item.messages) && item.messages.length > 0);
      });
    }
  }
  return false;
}

function getScriptTitle(scriptData) {
  if (!scriptData) return "Video Senaryosu";
  if (scriptData.title) return scriptData.title;
  if (typeof scriptData === 'object' && !Array.isArray(scriptData)) {
    const keys = Object.keys(scriptData);
    const langKeys = keys.filter(k => ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko", "ar", "hi", "zh", "nl", "pl", "sv"].includes(k.toLowerCase()));
    if (langKeys.length > 0 && scriptData[langKeys[0]]) {
      return scriptData[langKeys[0]].title || "Grup Video Senaryosu";
    }
  }
  return "Video Senaryosu";
}

function detectIsGroupChat(scriptData) {
  if (!scriptData) return false;
  if (scriptData.is_group === true || scriptData.isGroup === true || scriptData.is_group === "true" || scriptData.isGroup === "true") return true;
  if (scriptData.group_name && String(scriptData.group_name).trim().length > 0) return true;
  if (scriptData.group_participants && String(scriptData.group_participants).trim().length > 0) return true;

  const cName = String(scriptData.contact_name || scriptData.title || "").toLowerCase();
  const groupTerms = [
    "apartman", "sakinleri", "halı saha", "hali saha", "futbol", "takım", "fc ", "united", 
    "team", "squad", "meclisi", "aile", "family", "roommates", "arkadaşlar", "grup", "group", 
    "tayfa", "ofis", "şirket", "sohbeti", "official", "league", "bina", "site ", "yönetim"
  ];
  if (groupTerms.some(t => cName.includes(t))) return true;

  const msgs = scriptData.messages || [];
  if (Array.isArray(msgs) && msgs.length > 0) {
    const incomingSenders = getUniqueIncomingSenders(msgs, scriptData);
    if (incomingSenders.length > 1) return true;
  }
  return false;
}

function getUniqueIncomingSenders(messages, scriptData) {
  const incomingSenders = [];
  if (Array.isArray(messages)) {
    for (const m of messages) {
      const sender = (m.sender || m.gonderen || "").toLowerCase();
      const isMe = sender === "user" || sender === "me" || sender === "ben" || sender === "outgoing" || m.is_outgoing || m.me;
      let sName = (m.sender_name || m.name || m.kisi || m.senderName || "").trim();
      if (!sName && sender && !["user", "me", "ben", "outgoing", "contact", "other", "bot"].includes(sender)) {
        sName = (m.sender || m.gonderen || "").trim();
      }
      if (!isMe && sName && !["me", "ben", "sen", "you", "user"].includes(sName.toLowerCase())) {
        if (!incomingSenders.some(existing => existing.toLowerCase() === sName.toLowerCase())) {
          incomingSenders.push(sName);
        }
      }
    }
  }
  if (incomingSenders.length === 0 && scriptData && scriptData.group_participants) {
    const parts = String(scriptData.group_participants).split(/[,;]+/).map(s => s.trim()).filter(Boolean);
    for (const p of parts) {
      if (!["sen", "me", "you", "ben", "user"].includes(p.toLowerCase()) && !incomingSenders.some(e => e.toLowerCase() === p.toLowerCase())) {
        incomingSenders.push(p);
      }
    }
  }
  return incomingSenders;
}

function buildGroupAvatarPrompt(scriptData) {
  const groupName = (scriptData && (scriptData.group_name || scriptData.contact_name)) || "";
  const title = (scriptData && scriptData.title) || "";
  const topicDesc = `${groupName} ${title}`.trim();
  const lower = topicDesc.toLowerCase();

  let themeDetail = "aesthetic thematic community emblem badge";
  if (lower.match(/halı saha|futbol|spor|match|football|soccer|fc|team|united|league|squad/i)) {
    themeDetail = "vibrant sports team soccer club crest and football emblem, athletic shield badge";
  } else if (lower.match(/apartman|bina|site|rezidans|komşu|yönetim|building|apartment/i)) {
    themeDetail = "modern stylish architectural residential building emblem, minimalist real estate icon badge";
  } else if (lower.match(/aile|family|evim|home|akraba|kuzen/i)) {
    themeDetail = "warm cozy home cottage icon emblem, welcoming fireplace aesthetic badge";
  } else if (lower.match(/oto|tamir|garaj|araba|motor|garage|car/i)) {
    themeDetail = "vintage automotive garage badge, sleek wrench and classic car emblem";
  } else if (lower.match(/iş|ofis|şirket|mesai|patron|work|office|agency|corporate/i)) {
    themeDetail = "sleek minimalist modern corporate business emblem, abstract geometric logo badge";
  } else if (lower.match(/kanka|dost|kızlar|tayfa|gıybet|sohbet|dedikodu|chat|fun|party/i)) {
    themeDetail = "vibrant pop-art aesthetic neon coffee cup and chat bubble emblem, fun playful badge";
  } else if (topicDesc.length > 0) {
    themeDetail = `creative thematic emblem and symbol representing "${topicDesc}", minimalist community badge`;
  }

  return `A high quality centered square 1:1 circular emblem symbol of ${themeDetail}, authentic WhatsApp group profile photo avatar, clean crisp graphic design, aesthetic modern badge, strictly NO humans, no human faces, no personal selfie portrait, no text, no watermark, professional studio lighting, 4k`;
}

function detectCharacterDemographics(name, scriptData = null, fallbackGender = null) {
  const rawName = (name || "").trim();
  // Emojileri ve özel karakterleri temizle
  const cleanName = rawName.replace(/[\p{Extended_Pictographic}\u200d\uFE0F]/gu, "").replace(/[^\p{L}\p{N}\s]/gu, " ").trim();
  const nameLower = cleanName.toLowerCase();
  const words = nameLower.split(/\s+/).filter(Boolean);

  const explicitGender = (scriptData && (scriptData.contact_avatar_gender || scriptData.gender)) || fallbackGender;
  const roleType = (scriptData && (scriptData.contact_role_type || scriptData.role_type || "")) || "";
  const roleTypeLower = roleType.toLowerCase();

  const matchesKeyword = (list) => {
    return list.some(k => {
      const kLower = k.toLowerCase();
      return nameLower.includes(kLower) || words.some(w => w === kLower || w.startsWith(kLower)) || roleTypeLower.includes(kLower);
    });
  };

  // 1. YAŞLI / DEDE / AMCA / NİNE / TEYZE (60-75 Yaş) - Yaşlı Türk Büyüğü
  const elderlyMaleKeywords = [
    "amca", "dayı", "dayi", "dede", "büyükbaba", "buyukbaba", "hacı", "haci", "ihtiyar",
    "yaşlı", "yasli", "pir", "moruk", "grandpa", "grandfather", "pops", "granddad", "uncle"
  ];
  const elderlyFemaleKeywords = [
    "nine", "babaanne", "anneanne", "büyükanne", "buyukanne", "teyze", "hacı teyze", "haci teyze",
    "grandma", "grandmother", "granny"
  ];

  // 2. ORTA YAŞ / OLGUN / ANNE / BABA / PATRON (45-55 Yaş)
  const matureMaleKeywords = [
    "baba", "peder", "patron", "usta", "ev sahibi", "müdür", "mudur", "kayınpeder", "kayinpeder",
    "enişte", "eniste", "muhtar", "komiser", "şef", "sef", "hoca", "doktor", "avukat", "kasap",
    "bakkal", "taksici", "yönetici", "yonetici", "dad", "father", "boss", "landlord", "coach"
  ];
  const matureFemaleKeywords = [
    "anne", "valide", "kaynana", "kayınvalide", "kayinvalide", "teyze", "hala", "yenge",
    "müdüre", "mudure", "mom", "mother", "aunt", "landlady"
  ];

  // 3. SPOR / ATLETİK
  const sportsKeywords = ["kaptan", "captain", "kaleci", "keeper", "striker", "midfielder", "oyuncu", "sporty", "futbolcu"];

  // 4. ERGEN / GENÇ ÇOCUK (14-17 Yaş)
  const teenKeywords = ["yeğen", "yegen", "ufaklık", "ufaklik", "velet", "çocuk", "cocuk", "liseli", "teen", "kid", "nephew", "niece"];

  // 5. CİNSİYET TESPİTİ
  const femaleIndicators = [
    "anne", "nine", "babaanne", "anneanne", "teyze", "hala", "yenge", "abla", "kaynana", "hatun",
    "karım", "karim", "kız", "kiz", "prenses", "gelin", "valide", "mom", "mother", "grandma",
    "aunt", "sister", "wife", "lady", "merve", "ayşe", "ayse", "zeynep", "fatma", "elif", "eda",
    "selin", "büşra", "busra", "ceren", "gamze", "ebru", "duygu", "yasemin", "esra", "kübra",
    "kubra", "irem", "seda", "hilal", "hatice", "emine", "aslı", "asli", "özlem", "ozlem",
    "pınar", "pinar", "hande", "dilek", "sevgi", "gül", "gul", "nur", "filiz", "melek", "leyla",
    "sarah", "emily", "jessica", "anna", "lisa", "jenny", "michelle", "amy", "emma"
  ];
  const maleIndicators = [
    "amca", "dayı", "dayi", "dede", "baba", "peder", "patron", "usta", "ev sahibi", "hacı", "haci",
    "müdür", "mudur", "abi", "ağabey", "agabey", "enişte", "eniste", "kayınpeder", "kayinpeder",
    "damat", "muhtar", "komiser", "kasap", "bakkal", "taksici", "yönetici", "yonetici", "dad",
    "father", "uncle", "grandpa", "mr", "boss", "bro", "brother", "husband", "hüseyin", "huseyin",
    "mehmet", "ahmet", "ali", "hasan", "mustafa", "ibrahim", "osman", "ömer", "omer", "halil",
    "can", "burak", "emre", "murat", "kaan", "onur", "serkan", "tolga", "mert", "kerem", "cem",
    "deniz", "oğuz", "oguz", "koray", "selim", "erhan", "kemal", "turgut", "süleyman", "suleyman",
    "ismail", "ramazan", "recep", "şaban", "saban", "rıza", "riza", "faruk", "bekir", "salih",
    "orhan", "sinan", "kenan", "yusuf", "adem", "john", "mike", "david", "alex"
  ];

  let isFemale = false;
  if (explicitGender === "female") {
    isFemale = true;
  } else if (explicitGender === "male") {
    isFemale = false;
  } else if (matchesKeyword(femaleIndicators)) {
    isFemale = true;
  } else if (matchesKeyword(maleIndicators)) {
    isFemale = false;
  } else {
    isFemale = nameLower.endsWith("a") || nameLower.endsWith("e");
  }

  let category = "young_adult";
  if (matchesKeyword(elderlyMaleKeywords)) {
    category = "elderly_man";
    isFemale = false;
  } else if (matchesKeyword(elderlyFemaleKeywords)) {
    category = "elderly_woman";
    isFemale = true;
  } else if (matchesKeyword(matureMaleKeywords)) {
    category = "mature_man";
    isFemale = false;
  } else if (matchesKeyword(matureFemaleKeywords)) {
    category = "mature_woman";
    isFemale = true;
  } else if (matchesKeyword(teenKeywords)) {
    category = isFemale ? "teen_woman" : "teen_man";
  } else if (matchesKeyword(sportsKeywords)) {
    category = isFemale ? "sports_woman" : "sports_man";
  } else {
    category = isFemale ? "young_woman" : "young_man";
  }

  return {
    rawName,
    displayName: cleanName || rawName || "Person",
    isFemale,
    category
  };
}

function buildCharacterAvatarPrompt(characterName, scriptData = null, fallbackGender = null) {
  const demo = detectCharacterDemographics(characterName, scriptData, fallbackGender);
  const name = demo.displayName;

  switch (demo.category) {
    case "elderly_man":
      return `A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish man named ${name}, authentic elderly uncle (amca) figure, realistic weathered wrinkled face, receding gray and white hair, neat gray mustache, warm wise grandfatherly expression, authentic Turkish senior citizen, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid authentic photography, photorealistic, strictly NO young person, NO teenager, NO modern teen selfie, no text, no watermark, no frame`;

    case "elderly_woman":
      return `A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish woman named ${name}, authentic elderly grandmother / aunt (teyze/nine) figure, gentle wrinkled weathered face, wearing a modest traditional headscarf or silver gray hair, gentle kind smile and warm maternal gaze, authentic Turkish senior citizen, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid authentic photography, photorealistic, strictly NO young person, NO teenager, NO modern teen selfie, no text, no watermark, no frame`;

    case "mature_man":
      return `A realistic casual smartphone photo portrait of a mature 50-year-old middle-aged Turkish man named ${name}, authentic father and respected adult figure, seasoned natural facial features, neat slight graying stubble and hair, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid photography, no text, no watermark, no frame`;

    case "mature_woman":
      return `A realistic casual smartphone photo portrait of a mature 48-year-old middle-aged Turkish woman named ${name}, authentic mother and respected adult figure, warm welcoming maternal smile, seasoned natural facial features, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid photography, no text, no watermark, no frame`;

    case "teen_man":
      return `A realistic casual smartphone photo portrait of a 16-year-old Turkish teenager boy named ${name}, authentic youth, casual modern haircut, friendly authentic WhatsApp profile avatar, square 1:1 aspect ratio, close-up face portrait, natural lighting, candid photography, no text, no frame`;

    case "teen_woman":
      return `A realistic casual smartphone photo portrait of a 16-year-old Turkish teenager girl named ${name}, authentic youth, friendly natural expression, authentic WhatsApp profile avatar, square 1:1 aspect ratio, close-up face portrait, natural lighting, candid photography, no text, no frame`;

    case "sports_man":
      return `A realistic casual smartphone selfie profile photo of an athletic 26-year-old sports captain man named ${name}, sporty appearance, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid photography, no text, no frame`;

    case "sports_woman":
      return `A realistic casual smartphone selfie profile photo of an athletic 25-year-old sporty woman named ${name}, sporty appearance, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up human face portrait, natural ambient lighting, candid photography, no text, no frame`;

    case "young_woman":
      return `A realistic casual smartphone selfie profile photo of a 23-year-old young adult Turkish woman named ${name}, natural friendly smile, authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up friendly human face portrait, natural ambient lighting, candid authentic photography, no text, no frame`;

    case "young_man":
    default:
      return `A realistic casual smartphone selfie profile photo of a 24-year-old young adult Turkish man named ${name}, modern casual haircut, friendly authentic WhatsApp personal profile avatar, square 1:1 aspect ratio, close-up friendly human face portrait, natural ambient lighting, candid authentic photography, no text, no frame`;
  }
}

function refineAvatarPrompt(existingPrompt, characterName, scriptData = null) {
  if (!existingPrompt || typeof existingPrompt !== "string" || existingPrompt.trim().length === 0) {
    return buildCharacterAvatarPrompt(characterName, scriptData);
  }
  const promptLower = existingPrompt.toLowerCase();
  if (promptLower.includes("whatsapp_chat")) {
    return buildCharacterAvatarPrompt(characterName, scriptData);
  }

  const demo = detectCharacterDemographics(characterName, scriptData);
  let refined = existingPrompt.trim();

  if (demo.category === "elderly_man") {
    const hasElderlyWord = /(elderly|senior|wrinkled|weathered|graying hair|mustache|6\d-year-old|7\d-year-old|grandfather|grandpa|old man)/i.test(refined);
    refined = refined.replace(/casual smartphone selfie profile photo/gi, "candid phone camera portrait photo")
                     .replace(/smartphone selfie/gi, "candid phone camera portrait photo");
    if (!hasElderlyWord) {
      refined = `A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish man named ${demo.displayName}, authentic elderly uncle (amca) figure, realistic wrinkled weathered face, receding gray and white hair, neat gray mustache, authentic Turkish senior citizen, ${refined}, strictly NO young person, NO teenager, NO modern teen selfie`;
    }
  } else if (demo.category === "elderly_woman") {
    const hasElderlyWord = /(elderly|senior|wrinkled|weathered|headscarf|silver hair|6\d-year-old|7\d-year-old|grandmother|grandma|old woman)/i.test(refined);
    refined = refined.replace(/casual smartphone selfie profile photo/gi, "candid phone camera portrait photo")
                     .replace(/smartphone selfie/gi, "candid phone camera portrait photo");
    if (!hasElderlyWord) {
      refined = `A realistic candid phone camera portrait photo of an elderly 68-year-old senior Turkish woman named ${demo.displayName}, authentic elderly grandmother / aunt figure, gentle wrinkled face, wearing traditional headscarf or silver hair, ${refined}, strictly NO young person, NO teenager, NO modern teen selfie`;
    }
  } else if (demo.category === "mature_man") {
    const hasMatureWord = /(mature|middle-aged|5\d-year-old|4\d-year-old|father|dad)/i.test(refined);
    if (!hasMatureWord) {
      refined = refined.replace(/casual smartphone selfie profile photo/gi, "casual smartphone photo portrait")
                       .replace(/smartphone selfie/gi, "casual smartphone photo portrait");
      refined = `A realistic smartphone photo portrait of a mature 50-year-old middle-aged Turkish man named ${demo.displayName}, authentic father figure, ${refined}`;
    }
  } else if (demo.category === "mature_woman") {
    const hasMatureWord = /(mature|middle-aged|5\d-year-old|4\d-year-old|mother|mom)/i.test(refined);
    if (!hasMatureWord) {
      refined = refined.replace(/casual smartphone selfie profile photo/gi, "casual smartphone photo portrait")
                       .replace(/smartphone selfie/gi, "casual smartphone photo portrait");
      refined = `A realistic smartphone photo portrait of a mature 48-year-old middle-aged Turkish woman named ${demo.displayName}, authentic mother figure, ${refined}`;
    }
  }

  return refined;
}

function buildParticipantAvatarPrompt(senderName, scriptData) {
  const initial = buildCharacterAvatarPrompt(senderName, scriptData);
  return refineAvatarPrompt(initial, senderName, scriptData);
}

function getScriptScenes(scriptData) {
  if (!scriptData) return [];

  const isWhatsapp = (
    (scriptData.category && String(scriptData.category).includes("whatsapp")) ||
    (Array.isArray(scriptData.messages) && scriptData.messages.length > 0)
  );

  // WhatsApp senaryolarında sahneler her zaman katılımcı mesajlarından ve grup durumundan dinamik üretilmelidir!
  if (isWhatsapp && Array.isArray(scriptData.messages) && scriptData.messages.length > 0) {
    const isGroup = detectIsGroupChat(scriptData);
    if (isGroup) {
      const incomingSenders = getUniqueIncomingSenders(scriptData.messages, scriptData);
      const groupScenes = [];
      // Sahne 1 (Index 0): Grup Profil Amblem / Logosu (Asla insan yüzü/selfie değil!)
      groupScenes.push({
        scene_id: 1,
        type: "group_avatar",
        narration: scriptData.group_name || scriptData.contact_name || scriptData.title || "Grup Profil Logosu",
        image_prompt: buildGroupAvatarPrompt(scriptData)
      });
      // Sahne 2..N+1: Her benzersiz katılımcı için kendi özgün insan profil avatarı
      const effectiveSenders = incomingSenders.length > 0 ? incomingSenders : ["Grup Üyesi 1", "Grup Üyesi 2"];
      effectiveSenders.forEach((sender, idx) => {
        groupScenes.push({
          scene_id: idx + 2,
          type: "participant_avatar",
          sender_name: sender,
          narration: `${sender} Profil Fotoğrafı`,
          image_prompt: buildParticipantAvatarPrompt(sender, scriptData)
        });
      });
      return groupScenes;
    } else {
      // 1-e-1 Bireysel Sohbet: Karşı tarafın kişisel profil fotoğrafı (1 adet)
      const contactName = scriptData.contact_name || "Friend";
      const initialPrompt = scriptData.contact_avatar_prompt || buildCharacterAvatarPrompt(contactName, scriptData);
      return [{
        scene_id: 1,
        type: "contact_avatar",
        sender_name: contactName,
        narration: scriptData.title || `${contactName} Profil Fotoğrafı`,
        image_prompt: refineAvatarPrompt(initialPrompt, contactName, scriptData)
      }];
    }
  }

  // Diğer senaryolar (Reddit, Long-form vb.):
  if (Array.isArray(scriptData.scenes) && scriptData.scenes.length > 0) return scriptData.scenes;
  if (typeof scriptData === 'object' && !Array.isArray(scriptData)) {
    const keys = Object.keys(scriptData);
    const langKeys = keys.filter(k => ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko", "ar", "hi", "zh", "nl", "pl", "sv"].includes(k.toLowerCase()));
    if (langKeys.length > 0 && scriptData[langKeys[0]] && Array.isArray(scriptData[langKeys[0]].scenes) && scriptData[langKeys[0]].scenes.length > 0) {
      return scriptData[langKeys[0]].scenes;
    }
  }

  return [];
}

function saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene) {
  if (!customImages || !base64Data) return;
  customImages[i.toString()] = base64Data;
  if (isGroupChat) {
    if (i === 0) {
      customImages["group"] = base64Data;
      customImages["avatar"] = base64Data;
      customImages["0"] = base64Data;
    } else {
      customImages["p_" + i] = base64Data;
      customImages["participant_" + i] = base64Data;
      if (scene && scene.sender_name) {
        customImages[scene.sender_name] = base64Data;
        customImages[scene.sender_name.toLowerCase()] = base64Data;
        const cleanName = scene.sender_name.replace(/[^\p{L}\p{N}\s]/gu, "").trim().toLowerCase();
        if (cleanName) {
          customImages[cleanName] = base64Data;
          const firstWord = cleanName.split(/\s+/)[0];
          if (firstWord) customImages[firstWord] = base64Data;
        }
      }
    }
  } else {
    customImages["0"] = base64Data;
    customImages["group"] = base64Data;
    customImages["avatar"] = base64Data;
    customImages["contact"] = base64Data;
  }
}

function normalizeScriptData(parsed) {
  if (!parsed) return null;

  // 1. Doğrudan veya alt sarmalayıcıda (languages, scripts, data, result vb.) çok dilli nesne kontrolü
  if (typeof parsed === 'object' && !Array.isArray(parsed)) {
    let checkObj = parsed;
    if (parsed.languages && typeof parsed.languages === 'object') checkObj = parsed.languages;
    else if (parsed.scripts && typeof parsed.scripts === 'object') checkObj = parsed.scripts;
    else if (parsed.result && typeof parsed.result === 'object') checkObj = parsed.result;
    else if (parsed.data && typeof parsed.data === 'object') checkObj = parsed.data;
    else if (parsed.output && typeof parsed.output === 'object') checkObj = parsed.output;

    const langKeys = Object.keys(checkObj).filter(k => ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko", "ar", "hi", "zh", "nl", "pl", "sv"].includes(k.toLowerCase()));
    if (langKeys.length > 0) {
      const multiResult = {};
      for (const lk of langKeys) {
        const subParsed = checkObj[lk];
        if (!subParsed || typeof subParsed !== 'object') continue;

        let subTitle = subParsed.title || subParsed.baslik || subParsed.konu || "Video Senaryosu";
        let subScenes = subParsed.scenes || subParsed.sahne || subParsed.sahneler || subParsed.items || subParsed.data;
        let subMessages = subParsed.messages || subParsed.mesajlar || subParsed.dialogue || null;

        // WhatsApp senaryolarında her zaman katılımcı avatarları ve grup amblemi türet
        const isSubWhatsapp = (subParsed.category && String(subParsed.category).includes("whatsapp")) || (Array.isArray(subMessages) && subMessages.length > 0);
        if (isSubWhatsapp && Array.isArray(subMessages) && subMessages.length > 0) {
          subScenes = getScriptScenes(subParsed);
        } else if ((!subScenes || !Array.isArray(subScenes) || subScenes.length === 0) && Array.isArray(subMessages) && subMessages.length > 0) {
          subScenes = getScriptScenes(subParsed);
        }

        if (Array.isArray(subScenes)) {
          const normSubScenes = [];
          for (let i = 0; i < subScenes.length; i++) {
            const s = subScenes[i];
            if (!s || typeof s !== 'object') continue;
            const sceneId = s.scene_id || s.id || s.sahne_no || (i + 1);
            const narration = s.narration || s.seslendirme || s.metin || s.text || s.anlatim || "";
            const imagePrompt = s.image_prompt || s.gorsel_prompt || s.gorsel || s.prompt || s.visual_prompt || "";
            if (narration || imagePrompt) {
              normSubScenes.push({
                scene_id: typeof sceneId === 'number' ? sceneId : parseInt(sceneId) || (i + 1),
                narration: String(narration).replace(/\r?\n/g, " ").trim(),
                image_prompt: String(imagePrompt).replace(/\r?\n/g, " ").trim(),
                character: s.character || undefined,
                character_quote: s.character_quote || undefined,
                visual_type: s.visual_type || undefined,
                emotion: s.emotion || undefined,
                sender_name: s.sender_name || undefined,
                type: s.type || undefined
              });
            }
          }
          if (normSubScenes.length > 0 || (Array.isArray(subMessages) && subMessages.length > 0)) {
            multiResult[lk.toLowerCase()] = {
              title: String(subTitle).trim(),
              description: subParsed.description || subParsed.aciklama || undefined,
              tags: Array.isArray(subParsed.tags) ? subParsed.tags : (Array.isArray(subParsed.etiketler) ? subParsed.etiketler : undefined),
              keywords: Array.isArray(subParsed.keywords) ? subParsed.keywords : (Array.isArray(subParsed.anahtar_kelimeler) ? subParsed.anahtar_kelimeler : undefined),
              vehicle_name: subParsed.vehicle_name || undefined,
              vehicle_type: subParsed.vehicle_type || undefined,
              vehicle_nickname: subParsed.vehicle_nickname || undefined,
              key_specs: subParsed.key_specs || undefined,
              style_prompt: subParsed.style_prompt || undefined,
              scenes: normSubScenes,
              messages: Array.isArray(subMessages) ? subMessages : undefined,
              is_group: subParsed.is_group ?? subParsed.isGroup ?? detectIsGroupChat(subParsed),
              group_name: subParsed.group_name || subParsed.grup_adi || undefined,
              group_participants: subParsed.group_participants || subParsed.katilimcilar || undefined,
              contact_name: subParsed.contact_name || subParsed.kisi_adi || undefined,
              contact_avatar_gender: subParsed.contact_avatar_gender || subParsed.cinsiyet || undefined,
              contact_avatar_prompt: subParsed.contact_avatar_prompt || subParsed.avatar_prompt || undefined,
              contact_role_type: subParsed.contact_role_type || undefined,
              user_gender: subParsed.user_gender || subParsed.user_avatar_gender || undefined,
              user_role_type: subParsed.user_role_type || undefined,
              bgm_track: subParsed.bgm_track || undefined,
              category: subParsed.category || (subMessages ? "whatsapp_stories" : undefined),
              question: subParsed.question || subParsed.soru || "",
              subreddit: subParsed.subreddit || "r/AskReddit",
              author: subParsed.author || "u/StoryTeller99",
              upvotes: subParsed.upvotes || "45.2k"
            };
          }
        }
      }
      if (Object.keys(multiResult).length > 0) {
        return multiResult;
      }
    }
  }

  let title = "Otomatik Video Senaryosu";
  let scenes = null;
  let messages = null;
  let contact_name = null;
  let contact_avatar_gender = null;
  let contact_avatar_prompt = null;
  let contact_role_type = null;
  let user_gender = null;
  let user_role_type = null;
  let bgm_track = null;
  let category = null;
  let is_group = false;
  let group_name = null;
  let group_participants = null;

  if (Array.isArray(parsed)) {
    scenes = parsed;
    if (parsed.length > 0 && (parsed[0].title || parsed[0].baslik)) {
      title = parsed[0].title || parsed[0].baslik;
    }
  } else if (typeof parsed === 'object') {
    title = parsed.title || parsed.baslik || parsed.konu || parsed.name || title;
    scenes = parsed.scenes || parsed.sahne || parsed.sahneler || parsed.sahne_listesi || parsed.bolumler || parsed.items || parsed.list || parsed.data;
    messages = parsed.messages || parsed.mesajlar || parsed.dialogue || null;
    contact_name = parsed.contact_name || parsed.kisi_adi || null;
    contact_avatar_gender = parsed.contact_avatar_gender || parsed.cinsiyet || null;
    contact_avatar_prompt = parsed.contact_avatar_prompt || parsed.avatar_prompt || null;
    contact_role_type = parsed.contact_role_type || null;
    user_gender = parsed.user_gender || parsed.user_avatar_gender || null;
    user_role_type = parsed.user_role_type || null;
    bgm_track = parsed.bgm_track || null;
    category = parsed.category || null;
    is_group = parsed.is_group ?? parsed.isGroup ?? detectIsGroupChat(parsed);
    group_name = parsed.group_name || parsed.grup_adi || null;
    group_participants = parsed.group_participants || parsed.katilimcilar || null;
  }

  // WhatsApp senaryolarında her zaman katılımcı avatarları ve grup amblemi sahnelerini dinamik türet
  const isWhatsappMain = (category && String(category).includes("whatsapp")) || (Array.isArray(messages) && messages.length > 0);
  if (isWhatsappMain && Array.isArray(messages) && messages.length > 0) {
    scenes = getScriptScenes({
      title,
      category,
      messages,
      contact_name,
      contact_avatar_gender,
      contact_avatar_prompt,
      is_group,
      group_name,
      group_participants
    });
  } else if ((!scenes || !Array.isArray(scenes) || scenes.length === 0) && Array.isArray(messages) && messages.length > 0) {
    scenes = getScriptScenes({
      title,
      category,
      messages,
      contact_name,
      contact_avatar_gender,
      contact_avatar_prompt,
      is_group,
      group_name,
      group_participants
    });
  }

  if (!scenes || !Array.isArray(scenes) || scenes.length === 0) {
    return null;
  }

  const normalizedScenes = [];
  for (let i = 0; i < scenes.length; i++) {
    const s = scenes[i];
    if (!s || typeof s !== 'object') continue;

    const sceneId = s.scene_id || s.id || s.sahne_no || s.no || (i + 1);
    const narration = s.narration || s.seslendirme || s.metin || s.text || s.anlatim || s.aciklama || "";
    const imagePrompt = s.image_prompt || s.gorsel_prompt || s.gorsel || s.prompt || s.visual_prompt || s.image || "";

    if (narration || imagePrompt) {
      normalizedScenes.push({
        scene_id: typeof sceneId === 'number' ? sceneId : parseInt(sceneId) || (i + 1),
        narration: String(narration).replace(/\r?\n/g, " ").trim(),
        image_prompt: String(imagePrompt).replace(/\r?\n/g, " ").trim(),
        character: s.character || undefined,
        character_quote: s.character_quote || undefined,
        visual_type: s.visual_type || undefined,
        emotion: s.emotion || undefined,
        sender_name: s.sender_name || undefined,
        type: s.type || undefined
      });
    }
  }

  if (normalizedScenes.length === 0 && (!messages || !Array.isArray(messages) || messages.length === 0)) return null;

  return {
    title: String(title).trim(),
    description: parsed.description || parsed.aciklama || undefined,
    tags: Array.isArray(parsed.tags) ? parsed.tags : (Array.isArray(parsed.etiketler) ? parsed.etiketler : undefined),
    keywords: Array.isArray(parsed.keywords) ? parsed.keywords : (Array.isArray(parsed.anahtar_kelimeler) ? parsed.anahtar_kelimeler : undefined),
    vehicle_name: parsed.vehicle_name || undefined,
    vehicle_type: parsed.vehicle_type || undefined,
    vehicle_nickname: parsed.vehicle_nickname || undefined,
    key_specs: parsed.key_specs || undefined,
    style_prompt: parsed.style_prompt || undefined,
    scenes: normalizedScenes,
    messages: Array.isArray(messages) ? messages : undefined,
    is_group: is_group,
    group_name: group_name || undefined,
    group_participants: group_participants || undefined,
    contact_name: contact_name || undefined,
    contact_avatar_gender: contact_avatar_gender || undefined,
    contact_avatar_prompt: contact_avatar_prompt || undefined,
    contact_role_type: contact_role_type || undefined,
    user_gender: user_gender || undefined,
    user_role_type: user_role_type || undefined,
    bgm_track: bgm_track || undefined,
    category: category || (messages ? "whatsapp_stories" : undefined),
    question: parsed.question || parsed.soru || "",
    subreddit: parsed.subreddit || "r/AskReddit",
    author: parsed.author || "u/StoryTeller99",
    upvotes: parsed.upvotes || "45.2k"
  };
}

function robustCleanAndParseJson(text) {
  if (!text || typeof text !== "string") return null;

  let s = text.trim();

  // 1) Normalize Gemini/DOM smart quotes, typographer quotes, dashes, ellipses
  s = s
    .replace(/[“”„‟″‶]/g, '"')
    .replace(/[‘’‚‛′‵]/g, "'")
    .replace(/–|—/g, '-')
    .replace(/…/g, '...');

  // 2) Strip markdown code block markers ```json ... ```
  s = s.replace(/```(?:json)?\s*([\s\S]*?)\s*```/gi, "$1").trim();

  // 3) Extract outermost JSON object or array
  const braceStart = s.indexOf('{');
  const bracketStart = s.indexOf('[');
  let startIdx = -1;
  let endIdx = -1;

  if (braceStart !== -1 && (bracketStart === -1 || braceStart < bracketStart)) {
    startIdx = braceStart;
    endIdx = s.lastIndexOf('}');
  } else if (bracketStart !== -1) {
    startIdx = bracketStart;
    endIdx = s.lastIndexOf(']');
  }

  if (startIdx !== -1) {
    if (endIdx !== -1 && endIdx > startIdx) {
      s = s.substring(startIdx, endIdx + 1);
    } else {
      s = s.substring(startIdx);
    }
  }

  const tryParse = (str) => {
    try {
      return JSON.parse(str);
    } catch(e) {
      return null;
    }
  };

  // Direct parse attempt
  let parsed = tryParse(s);
  if (parsed) return parsed;

  // Pass 1: Missing commas between objects, arrays, and properties
  let pass1 = s
    .replace(/\}\s*(?:\r?\n\s*)*\{/g, '},\n{')
    .replace(/\]\s*(?:\r?\n\s*)*\[/g, '],\n[')
    .replace(/\}\s*(?:\r?\n\s*)*\"/g, '},\n"')
    .replace(/\]\s*(?:\r?\n\s*)*\"/g, '],\n"')
    .replace(/,\s*([\]\}])/g, '$1');

  parsed = tryParse(pass1);
  if (parsed) return parsed;

  // Pass 2: Missing commas between consecutive key-value pairs
  let pass2 = pass1.replace(/(\"[\s\S]*?\")\s*(?:\r?\n\s*)+(\"[a-zA-Z0-9_.-]+\"\s*:)/g, '$1,\n$2');
  parsed = tryParse(pass2);
  if (parsed) return parsed;

  // Pass 3: Fix unescaped control characters inside string literals
  let parts = [];
  let inString = false;
  let escaped = false;
  for (let i = 0; i < pass2.length; i++) {
    const ch = pass2[i];
    if (escaped) { parts.push(ch); escaped = false; continue; }
    if (ch === '\\') { parts.push(ch); escaped = true; continue; }
    if (ch === '"') { inString = !inString; parts.push(ch); continue; }
    if (inString) {
      if (ch === '\n') { parts.push('\\n'); continue; }
      if (ch === '\r') { parts.push('\\r'); continue; }
      if (ch === '\t') { parts.push('\\t'); continue; }
    }
    parts.push(ch);
  }
  let pass3 = parts.join('').replace(/,\s*([\]\}])/g, '$1');
  parsed = tryParse(pass3);
  if (parsed) return parsed;

  // Pass 4: Auto-balance unclosed brackets/braces for truncated or interrupted JSON
  let openBraces = 0;
  let openBrackets = 0;
  inString = false;
  escaped = false;
  for (let i = 0; i < pass3.length; i++) {
    const ch = pass3[i];
    if (escaped) { escaped = false; continue; }
    if (ch === '\\') { escaped = true; continue; }
    if (ch === '"') { inString = !inString; continue; }
    if (!inString) {
      if (ch === '{') openBraces++;
      else if (ch === '}') openBraces = Math.max(0, openBraces - 1);
      else if (ch === '[') openBrackets++;
      else if (ch === ']') openBrackets = Math.max(0, openBrackets - 1);
    }
  }

  let pass4 = pass3;
  if (inString) pass4 += '"';
  while (openBrackets > 0) { pass4 += ']'; openBrackets--; }
  while (openBraces > 0) { pass4 += '}'; openBraces--; }
  pass4 = pass4.replace(/,\s*([\]\}])/g, '$1');

  parsed = tryParse(pass4);
  if (parsed) return parsed;

  // Pass 5: Regex-based extraction fallback for script structure
  try {
    const titleMatch = s.match(/\"(?:title|baslik|konu)\"\s*:\s*\"([^\"]+)\"/i);
    const scenes = [];
    const objectRegex = /\{[^{}]*(?:narration|seslendirme|metin|image_prompt|gorsel_prompt)[^{}]*\}/gi;
    let match;
    let idx = 1;
    while ((match = objectRegex.exec(s)) !== null) {
      const objStr = match[0];
      const narrM = objStr.match(/\"(?:narration|seslendirme|metin|text|anlatim)\"\s*:\s*\"((?:\\\"|[^\"])*)\"/i);
      const imgM = objStr.match(/\"(?:image_prompt|gorsel_prompt|gorsel|prompt|visual_prompt)\"\s*:\s*\"((?:\\\"|[^\"])*)\"/i);
      const idM = objStr.match(/\"(?:scene_id|id|sahne_no|no)\"\s*:\s*(\d+)/i);
      
      if (narrM || imgM) {
        scenes.push({
          scene_id: idM ? parseInt(idM[1]) : idx++,
          narration: narrM ? narrM[1].replace(/\\"/g, '"').replace(/\\n/g, ' ').trim() : "",
          image_prompt: imgM ? imgM[1].replace(/\\"/g, '"').replace(/\\n/g, ' ').trim() : ""
        });
      }
    }
    if (scenes.length > 0) {
      return {
        title: titleMatch ? titleMatch[1] : "Otomatik Üretilen Senaryo",
        scenes: scenes
      };
    }
  } catch(e) {}

  // Pass 6: Array regex extraction fallback
  try {
    if (bracketStart !== -1) {
      const items = [];
      const itemRegex = /\{[\s\S]*?\"(?:baslik|title|id)\"[\s\S]*?\}/gi;
      let m;
      while ((m = itemRegex.exec(s)) !== null) {
        try {
          const itemParsed = JSON.parse(m[0].replace(/,\s*([\]\}])/g, '$1'));
          if (itemParsed) items.push(itemParsed);
        } catch(err) {}
      }
      if (items.length > 0) return items;
    }
  } catch(e) {}

  return null;
}

function parseMaterialsOrTopicsResponse(rawText, expectedItems = []) {
  if (!rawText || typeof rawText !== "string") return [];

  let text = rawText.trim()
    .replace(/[“”„‟″‶]/g, '"')
    .replace(/[‘’‚‛′‵]/g, "'")
    .replace(/–|—/g, '-')
    .replace(/…/g, '...');

  const tryParse = (str) => {
    try { return JSON.parse(str); } catch { return null; }
  };

  const unwrapCandidate = (obj) => {
    if (!obj) return [];
    if (Array.isArray(obj)) return obj;
    if (typeof obj === "object") {
      // Çok dilli grup senaryosu kontrolü ({ "tr": {...}, "en": {...} })
      const hasLangKeys = Object.keys(obj).some(k => ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko"].includes(k));
      if (hasLangKeys) {
        return [{ script: obj }];
      }
      // Tekil bir video senaryosu nesnesi ise (scenes dizisi veya script nesnesi varsa), tekil olarak paketle
      if (Array.isArray(obj.scenes) || obj.script) {
        return [obj];
      }
      const candidates = [
        obj.materials, obj.topics, obj.items, obj.scripts, obj.plan, obj.data
      ];
      for (const c of candidates) {
        if (Array.isArray(c) && c.length > 0) return c;
      }
      if (obj.row_id || obj.baslik || obj.title) {
        return [obj];
      }
    }
    return [];
  };

  // 1. Check for multiple markdown code blocks ```json ... ```
  const codeBlockRegex = /```(?:json)?\s*([\s\S]*?)\s*```/gi;
  let codeBlocks = [];
  let match;
  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match[1] && match[1].trim().length > 10) {
      codeBlocks.push(match[1].trim());
    }
  }

  if (codeBlocks.length > 0) {
    let collectedFromBlocks = [];
    for (const block of codeBlocks) {
      let p = tryParse(block) || robustCleanAndParseJson(block);
      const items = unwrapCandidate(p);
      if (items.length > 0) {
        collectedFromBlocks.push(...items);
      }
    }
    if (collectedFromBlocks.length > 0) {
      return normalizeMaterialsList(collectedFromBlocks, expectedItems);
    }
  }

  // 2. Direct array slice [...]
  const firstBracket = text.indexOf('[');
  const lastBracket = text.lastIndexOf(']');
  if (firstBracket !== -1 && lastBracket > firstBracket) {
    const arraySlice = text.substring(firstBracket, lastBracket + 1);
    let p = tryParse(arraySlice) || robustCleanAndParseJson(arraySlice);
    const items = unwrapCandidate(p);
    if (items.length > 0) {
      return normalizeMaterialsList(items, expectedItems);
    }
  }

  // 3. Outermost object or array attempt
  let directParsed = tryParse(text) || robustCleanAndParseJson(text);
  const unwrapped = unwrapCandidate(directParsed);
  if (unwrapped.length > 0) {
    return normalizeMaterialsList(unwrapped, expectedItems);
  }

  // 4. Scanner for individual JSON objects { ... } containing topic/script properties
  const extractedObjects = extractBalancedJsonObjects(text);
  if (extractedObjects.length > 0) {
    return normalizeMaterialsList(extractedObjects, expectedItems);
  }

  return [];
}

function extractBalancedJsonObjects(text) {
  const results = [];
  let depth = 0;
  let startIdx = -1;
  let inString = false;
  let escape = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (escape) { escape = false; continue; }
    if (ch === '\\') { escape = true; continue; }
    if (ch === '"') { inString = !inString; continue; }
    if (inString) continue;

    if (ch === '{') {
      if (depth === 0) startIdx = i;
      depth++;
    } else if (ch === '}') {
      depth--;
      if (depth === 0 && startIdx !== -1) {
        const candidate = text.substring(startIdx, i + 1);
        try {
          const parsed = JSON.parse(candidate);
          if (parsed && typeof parsed === 'object') {
            if (parsed.row_id || parsed.script || parsed.scenes || parsed.baslik || parsed.title) {
              results.push(parsed);
            }
          }
        } catch {
          const repaired = robustCleanAndParseJson(candidate);
          if (repaired && typeof repaired === 'object' && !Array.isArray(repaired)) {
            if (repaired.row_id || repaired.script || repaired.scenes || repaired.baslik || repaired.title) {
              results.push(repaired);
            }
          }
        }
        startIdx = -1;
      }
    }
  }
  return results;
}

function normalizeMaterialsList(items, expectedItems = []) {
  if (!Array.isArray(items)) return [];

  const normalized = [];
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    if (!it || typeof it !== 'object') continue;

    let exp = null;
    if (Array.isArray(expectedItems) && expectedItems.length > 0) {
      const rawId = String(it.row_id || it.id || "").trim();
      if (rawId) {
        exp = expectedItems.find(e => String(e.id || e.row_id).trim() === rawId);
      }
      if (!exp && expectedItems[i]) {
        exp = expectedItems[i];
      }
    }

    const rowId = String(it.row_id || it.id || (exp ? exp.id : (i + 1))).trim();
    let baslik = it.baslik;
    if (!baslik && it.title && it.title !== "Otomatik Üretilen Senaryo") {
      baslik = it.title;
    }
    if ((!baslik || baslik === "Otomatik Üretilen Senaryo") && exp) {
      baslik = exp.baslik || exp.konu;
    }
    if (!baslik) {
      baslik = (it.title && it.title !== "Otomatik Üretilen Senaryo") ? it.title : (exp ? (exp.baslik || exp.konu) : `Konu ${i + 1}`);
    }
    const konu = (it.konu && it.konu !== "Otomatik Üretilen Senaryo") ? it.konu : (exp ? (exp.konu || exp.baslik) : baslik);

    let script = it.script || (it.scenes ? it : null);
    if (!script && it && typeof it === "object") {
      const hasLangKeys = Object.keys(it).some(k => ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko"].includes(k));
      if (hasLangKeys) {
        script = it;
      }
    }
    let hasRealScript = false;
    if (script && typeof script === "object") {
      if (Array.isArray(script.scenes) && script.scenes.length > 0) {
        hasRealScript = true;
      } else {
        const hasLangKeys = Object.keys(script).some(k => ["tr", "en", "de", "es", "fr", "it", "ru", "pt", "ja", "ko"].includes(k));
        if (hasLangKeys) hasRealScript = true;
      }
    }

    if (!baslik && script) {
      if (script.tr && script.tr.title) baslik = script.tr.title;
      else if (script.en && script.en.title) baslik = script.en.title;
    }

    if (script && !script.title && typeof script === "object" && !script.scenes) {
      // Çok dilli nesne ise veya başlık yoksa
      if (script.tr && script.tr.title) script.title = script.tr.title;
      else if (script.en && script.en.title) script.title = script.en.title;
      else script.title = baslik;
    } else if (script && (!script.title || script.title === "Otomatik Üretilen Senaryo")) {
      script.title = baslik;
    }

    const itemObj = {
      row_id: rowId,
      baslik: baslik,
      konu: konu
    };
    if (it.yonergeler) itemObj.yonergeler = it.yonergeler;
    if (hasRealScript) {
      const isTr = /[çğıöşüÇĞİÖŞÜ]/.test(baslik || "") || /[çğıöşüÇĞİÖŞÜ]/.test(script.title || "") || /[çğıöşüÇĞİÖŞÜ]/.test(konu || "");
      // Eksik description ve tags alanlarını otomatik tamamla (asla boş kalmaz)
      if (!script.description || typeof script.description !== "string" || script.description.trim().length === 0) {
        if (script.vehicle_name || script.vehicle_type || script.key_specs) {
          const vName = script.vehicle_name || script.title || baslik;
          const vNick = script.vehicle_nickname ? ` (${script.vehicle_nickname})` : "";
          const specsObj = script.key_specs || {};
          let specsText = "";
          for (const [k, v] of Object.entries(specsObj)) {
            specsText += `• ${k.replace(/_/g, ' ').toUpperCase()}: ${v}\n`;
          }
          if (isTr) {
            script.description = `${script.title || baslik}\n\n${vName}${vNick} hakkında kapsamlı askeri teknoloji, mühendislik ve savunma bütçesi analizi.\n\n🎖️ TEKNİK ÖZELLİKLER & DOSYA BİLGİLERİ:\n${specsText}\nSizce tarihin en akıl almaz askeri bütçe israfı hangisi? Düşüncelerinizi yorumlarda belirtin! 👇\n\n🔔 Haftalık taktik analizler, blueprint incelemeleri ve askeri araç dosyaları için kanalımıza abone olun!\n\n#TacticalCrayon #AskeriTeknoloji #SavunmaSanayii #Mühendislik #Belgesel #CrayonCombat`;
          } else {
            script.description = `${script.title || baslik}\n\nForensic military tech breakdown of ${vName}${vNick}.\n\n🎖️ VEHICLE / EQUIPMENT INTEL:\n${specsText}\nWhat is the most ridiculous military budget overrun you have ever seen? Let us know in the comments below! 👇\n\n🔔 Subscribe to Tactical Crayon for weekly forensic military hardware breakdowns, blueprint autopsies, and defense contractor reality checks!\n\n#TacticalCrayon #MilitaryTech #DefenseSatire #Pentagon #Engineering #VideoEssay #CrayonCombat #Military #Documentary`;
          }
        } else {
          if (isTr) {
            script.description = `${script.title || baslik}\n\nDaha fazla derinlemesine video analizi ve belgesel için videoyu beğenmeyi ve kanalımıza abone olmayı unutmayın! 🔔\n\n#VideoEssay #Belgesel #Viral`;
          } else {
            script.description = `${script.title || baslik}\n\nDon't forget to like, subscribe, and turn on notifications for more awesome video essays! 🔔\n\n#VideoEssay #Documentary #Viral`;
          }
        }
      }
      if (!Array.isArray(script.tags) || script.tags.length === 0) {
        if (script.vehicle_name || script.vehicle_type || script.key_specs) {
          if (isTr) {
            script.tags = [
              "Tactical Crayon", "Askeri Teknoloji", "Savunma Sanayii", "Mühendislik",
              "Pentagon", "Askeri Bütçe", "Savaş Uçakları", "Tanklar", "Belgesel",
              "Crayon Combat", "Hiciv", "Silahlar", "Harp Tarihi"
            ];
          } else {
            script.tags = [
              "Tactical Crayon", "Military Tech", "Crayon Combat", "Defense Contractor", 
              "Pentagon", "Military Budget", "Engineering Breakdown", "Video Essay", 
              "Military Documentary", "OverSimplified", "Crayon Capital", "Fighter Jet", 
              "Weapons", "Warfare", "Satire"
            ];
          }
        } else {
          script.tags = isTr ? ["Video Analiz", "Belgesel", "İnceleme", "Hikaye", "Eğitici"] : ["Video Essay", "Documentary", "Educational", "Deep Dive", "Story"];
        }
      }
      if (!Array.isArray(script.keywords) || script.keywords.length === 0) {
        script.keywords = isTr ? ["tactical crayon", "askeri hiciv", "savunma sanayii", "askeri teknoloji", "crayon combat"] : ["tactical crayon", "military satire", "defense spending", "pentagon budget", "military hardware", "crayon combat"];
      }
      itemObj.script = script;
    }

    normalized.push(itemObj);
  }
  return normalized;
}

function findScriptInChatHistory() {
  const selectors = [
    'model-response', 'model-turn', '.model-turn',
    'message-content', '.message-content',
    '.response-container-content', '[role="text"]',
    'code-block', 'pre', 'code', 'div.markdown', '.markdown',
    '[data-turn-role="model"]', 'p-chat-turn', 'chat-turn',
    'rich-textarea', '.markdown-main-panel', 'structured-content'
  ];

  const candidateSet = new Set();
  const candidates = [];
  for (const sel of selectors) {
    const els = document.querySelectorAll(sel);
    els.forEach(el => {
      if (!candidateSet.has(el)) { candidateSet.add(el); candidates.push(el); }
    });
  }

  for (let i = candidates.length - 1; i >= 0; i--) {
    const el = candidates[i];
    const rawText = (el.innerText || el.textContent || '').trim();
    if (!rawText || rawText.length < 30) continue;

    const data = robustCleanAndParseJson(rawText);
    const normalized = normalizeScriptData(data);
    if (normalized) {
      return { scriptData: normalized, element: el };
    }
  }

  return null;
}

async function runGeminiAutomation(channelId, useTempChat, videoCount, nasaOption = "mixed", startLoop = 0, startVideosProduced = 0, resumedCustomImages = null, resumedRowId = null, resumedScriptData = null, resumeCurrentChat = false, initialImageProvider = null) {
  geminiRunning = true;
  let isNavigatingRedirect = false;
  const apiUrl = await getApiUrl();
  
  // Görsel üretim motoru tercihi ("gemini" veya "perchance")
  const providerData = await new Promise(r => chrome.storage.local.get("gemini_auto_image_provider", r));
  let activeImageProvider = initialImageProvider || providerData.gemini_auto_image_provider || "gemini";

  // Yerel SD zorlama bayrağını oku
  const storageData = await new Promise(resolve => chrome.storage.local.get("gemini_auto_fallback_local", resolve));
  const forceLocalSD = !!storageData.gemini_auto_fallback_local;
  
  if (forceLocalSD) {
    logGemini("⚠️ Limitlerden dolayı görsel üretimi doğrudan yerel SD (Stable Diffusion) moduna geçirildi.", "warning");
  }


  // Çalışma durumunu ve parametreleri hemen hafızaya kaydet
  chrome.storage.local.set({
    gemini_auto_active: true,
    gemini_auto_channel_id: channelId,
    gemini_auto_use_temp_chat: useTempChat,
    gemini_auto_video_count: videoCount,
    gemini_auto_image_provider: activeImageProvider,
    gemini_auto_nasa_option: nasaOption,
    gemini_auto_loop: startLoop,
    gemini_auto_videos_produced: startVideosProduced,
    gemini_auto_custom_images: resumedCustomImages || {},
    gemini_auto_row_id: resumedRowId,
    gemini_auto_script_data: resumedScriptData
  });

  logGemini(`Otomasyon başlatıldı. Hedef: ${videoCount} video. Başlangıç: Video ${startLoop + 1}. Backend: ${apiUrl}`, "info");

  const thinkingBar = document.getElementById("gemini-thinking-bar");
  if (thinkingBar) thinkingBar.style.display = "block";

  const selectGroup = document.getElementById("gemini-channel-group");
  const modeGroup = document.getElementById("gemini-mode-group");
  const countGroup = document.getElementById("gemini-video-count-group");
  const nasaGroup = document.getElementById("gemini-nasa-option-group");
  if (selectGroup) selectGroup.style.display = "none";
  if (modeGroup) modeGroup.style.display = "none";
  if (countGroup) countGroup.style.display = "none";
  if (nasaGroup) nasaGroup.style.display = "none";

  const creature = document.getElementById("gemini-working-creature");
  if (creature) creature.style.display = "flex";

  let videosProduced = startVideosProduced;
  const isGroup = (channelId || "").startsWith("group:");
  const targetId = isGroup ? (channelId || "").replace("group:", "") : channelId;

  // Oturum boyunca işlenen satır ID'lerini takip et (Tekrarları önlemek ve sırayla gitmek için)
  const storedProcessed = await new Promise(r => chrome.storage.local.get("gemini_auto_processed_row_ids", r));
  let sessionProcessedRowIds = (storedProcessed && Array.isArray(storedProcessed.gemini_auto_processed_row_ids)) 
    ? storedProcessed.gemini_auto_processed_row_ids.map(x => x.toString()) 
    : [];

  if (startLoop === 0 && !resumedRowId) {
    sessionProcessedRowIds = [];
    chrome.storage.local.set({ gemini_auto_processed_row_ids: [] });
  }

  // Hazırlanan videoların hafızası (Toplu üretim için paketlenir)
  let stagedBatch = [];
  const storedStaged = await new Promise(r => chrome.storage.local.get("gemini_staged_batch", r));
  if (storedStaged && Array.isArray(storedStaged.gemini_staged_batch)) {
    if (startLoop > 0) {
      stagedBatch = storedStaged.gemini_staged_batch;
    } else {
      chrome.storage.local.remove(["gemini_staged_batch"]);
    }
  }

  try {
    for (let loop = startLoop; loop < videoCount; loop++) {
      if (!geminiRunning) {
        logGemini("Otomasyon kullanıcı tarafından durduruldu.", "error");
        break;
      }

      const isResumeOfCurrentVideo = (loop === startLoop && resumedRowId && resumedScriptData);
      if (!isResumeOfCurrentVideo && !resumeCurrentChat) {
        const existingTurns = document.querySelectorAll('model-response, model-turn, .model-turn, [data-turn-role="model"], p-chat-turn, chat-turn');
        if (loop > startLoop || existingTurns.length > 0) {
          logGemini(`[Video ${loop + 1}/${videoCount}] Yeni video için temiz sohbet oturumu açılıyor...`, "info");
          const ready = await startNewChat();
          if (!ready) {
            isNavigatingRedirect = true;
            return;
          }
          await new Promise(r => setTimeout(r, 1200));
        }
      }

      let rowId = null;
      let scriptData = null;
      let item = null;
      let channel = null;
      let category = isGroup ? "reddit_stories" : "space"; // Fallback category
      let customImages = (loop === startLoop && resumedCustomImages) ? resumedCustomImages : {};
      let resumeCurrentChatHandled = false;
      if (resumeCurrentChat && loop === startLoop) {
        logGemini("[Sürdür] Mevcut sohbet geçmişi taranıyor...", "info");
        
        let found = null;
        const maxWaitMs = 4000;
        const checkInterval = 400;
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWaitMs) {
          found = findScriptInChatHistory();
          if (found) break;
          await new Promise(r => setTimeout(r, checkInterval));
        }

        if (found) {
          scriptData = found.scriptData;
          logGemini(`[Sürdür] Senaryo sohbetten başarıyla yüklendi: "${getScriptTitle(scriptData)}"`, "success");

          logGemini(`[Video ${loop + 1}/${videoCount}] Sıradaki konu planı alınıyor...`, "info");
          const excludeQuery = sessionProcessedRowIds.length > 0 ? `?exclude_ids=${sessionProcessedRowIds.join(',')}` : '';
          const planUrl = isGroup ? `${apiUrl}/api/groups/${targetId}/plan/next-unproduced${excludeQuery}` : `${apiUrl}/api/channels/${targetId}/plan/next-unproduced${excludeQuery}`;
          const planRes = await fetchFromBackground(planUrl);
          if (!planRes.ok) throw new Error(`Plan alınamadı: HTTP ${planRes.status}`);
          const planData = await planRes.json();

          if (!planData.success || (!planData.has_unproduced && !planData.item)) {
            logGemini("Üretilecek konu bulunamadı. İşlem sonlandırıldı.", "success");
            break;
          }

          item = planData.item;
          channel = planData.channel;
          rowId = item.id;
          category = channel ? channel.topic_category : (isGroup ? "reddit_stories" : "space");

          if (rowId && !sessionProcessedRowIds.includes(rowId.toString())) {
            sessionProcessedRowIds.push(rowId.toString());
            chrome.storage.local.set({ gemini_auto_processed_row_ids: sessionProcessedRowIds });
          }

          logGemini(`[Sürdür] Konu eşleştirildi: "${item.baslik}" [Sıra ID: ${rowId}]`, "info");

          // Sayfadaki mevcut görselleri geri yükle
          const chatImgs = [];
          const imageElements = document.querySelectorAll('model-turn img, .model-turn img, message-content img, .message-content img, generated-image img, single-image img, [role="text"] img');
          imageElements.forEach(img => {
            const src = img.src || '';
            const isGoogleContent = src.includes('googleusercontent.com') || src.startsWith('blob:');
            const isAvatar = img.classList.contains('avatar') || img.classList.contains('mavatar-image') || img.closest('.avatar-container') || img.closest('[aria-label*="Google Hesabı"]') || img.closest('[aria-label*="Account"]');
            if (isGoogleContent && !isAvatar && !chatImgs.includes(img)) {
              chatImgs.push(img);
            }
          });

          logGemini(`Mevcut sohbette ${chatImgs.length} adet geçerli görsel tespit edildi. Çözümleniyor...`, "info");
          
          const scriptScenes = getScriptScenes(scriptData);
          for (let idx = 0; idx < chatImgs.length && idx < scriptScenes.length; idx++) {
            const imgUrl = chatImgs[idx].src;
            try {
              const base64 = await getBase64FromUrl(imgUrl);
              customImages[idx.toString()] = base64;
              logGemini(`[Sürdür - Geri Yüklendi] Sahne ${idx+1}/${scriptScenes.length} görseli alındı.`, "success");
            } catch(e) {
              logGemini(`Sahne ${idx+1} görseli alınırken hata: ${e.message}`, "warning");
            }
          }

          // Durumu anında storage'a yedekle
          chrome.storage.local.set({
            gemini_auto_active: true,
            gemini_auto_channel_id: channelId,
            gemini_auto_use_temp_chat: false,
            gemini_auto_video_count: videoCount,
            gemini_auto_nasa_option: nasaOption,
            gemini_auto_loop: loop,
            gemini_auto_videos_produced: videosProduced,
            gemini_auto_custom_images: customImages,
            gemini_auto_row_id: rowId,
            gemini_auto_script_data: scriptData
          });

          resumeCurrentChatHandled = true;
        } else {
          logGemini("⚠️ [Sürdür] Sohbet geçmişinde hazır senaryo bulunamadı. İçerik planındaki sıradaki konu ile üretime geçiliyor...", "warning");
        }
      }

      if (!resumeCurrentChatHandled) {
        if (isResumeOfCurrentVideo) {
        logGemini(`[Kurtarma] Önceki hesaptan kaydedilen senaryo geri yükleniyor (Plan ID: ${resumedRowId})...`, "success");
        rowId = resumedRowId;
        scriptData = resumedScriptData;
        
        // Kanal ayarlarını backend'den çek
        if (!isGroup) {
          const chRes = await fetchFromBackground(`${apiUrl}/api/channels`);
          if (chRes.ok) {
            const channelsList = await chRes.json();
            channel = channelsList.find(c => c.channel_id === channelId);
            if (channel) {
              category = channel.topic_category || "space";
            }
          }
        }
      } else {
        let targetRowId = null;
        if (loop === 0) {
          const incompleteSelect = document.getElementById("gemini-incomplete-select");
          if (incompleteSelect && incompleteSelect.value) {
            targetRowId = incompleteSelect.value;
            incompleteSelect.value = ""; // Sıradaki videolarda içerik planına geri dönmesi için sıfırla
          }
        }

        if (targetRowId) {
          logGemini(`[Seçili Video] ID: ${targetRowId} konusuna ait bilgiler getiriliyor...`, "info");
          const planUrl = isGroup ? `${apiUrl}/api/groups/${targetId}/plan` : `${apiUrl}/api/channels/${targetId}/plan`;
          const planRes = await fetchFromBackground(planUrl);
          if (!planRes.ok) throw new Error("Plan satırları alınamadı.");
          const planData = planRes.data || (await planRes.json());
          
          item = planData.plan.find(p => p.id.toString() === targetRowId.toString());
          if (!item) throw new Error(`Seçili plan satırı (ID: ${targetRowId}) bulunamadı.`);
          
          rowId = item.id;
          const topic = item.konu;
          category = channel ? channel.topic_category : (isGroup ? "reddit_stories" : "space");
          
          logGemini(`[Seçili Video] Konu: "${item.baslik || topic}" (${topic}) [Sıra ID: ${rowId}]`, "info");
        } else {
          logGemini(`[Video ${loop + 1}/${videoCount}] Sıradaki üretilmemiş konu planı alınıyor...`, "info");
          const excludeQuery = sessionProcessedRowIds.length > 0 ? `?exclude_ids=${sessionProcessedRowIds.join(',')}` : '';
          const planUrl = isGroup 
            ? `${apiUrl}/api/groups/${targetId}/plan/next-unproduced${excludeQuery}` 
            : `${apiUrl}/api/channels/${targetId}/plan/next-unproduced${excludeQuery}`;
          const planRes = await fetchFromBackground(planUrl);
          if (!planRes.ok) throw new Error(`Plan alınamadı: HTTP ${planRes.status}`);
          const planData = await planRes.json();

          if (!planData.success || (!planData.has_unproduced && !planData.item)) {
            logGemini("Üretilecek konu kalmadı veya tüm konular tamamlandı. Otomasyon sonlandırıldı.", "success");
            break;
          }

          item = planData.item;
          channel = planData.channel || null;
          rowId = item.id;
          const topic = item.konu;
          category = channel ? channel.topic_category : (isGroup ? "reddit_stories" : "space");

          logGemini(`[Video ${loop + 1}/${videoCount}] Konu: "${item.baslik || topic}" (${topic}) [Sıra ID: ${rowId}]`, "info");
        }

        // Satır ID'sini oturum listesine ekle ve sakla
        if (rowId && !sessionProcessedRowIds.includes(rowId.toString())) {
          sessionProcessedRowIds.push(rowId.toString());
          chrome.storage.local.set({ gemini_auto_processed_row_ids: sessionProcessedRowIds });
        }

        if (useTempChat) {
          logGemini("Geçici sohbet modu kontrol ediliyor...", "info");
          await toggleTemporaryChatIfNeeded(true);
        }

        logGemini("Senaryo promptu hazırlanıyor...", "info");
        const promptUrl = isGroup ? `${apiUrl}/api/groups/${targetId}/plan/${rowId}/gemini-prompt` : `${apiUrl}/api/channels/${targetId}/plan/${rowId}/gemini-prompt`;
        const promptRes = await fetchFromBackground(promptUrl, {
          method: "POST"
        });
        if (!promptRes.ok) throw new Error(`Prompt alınamadı: HTTP ${promptRes.status}`);
        
        const promptData = await promptRes.json();

        if (promptData.custom_script) {
          logGemini("Önceden hazırlanmış Shorts senaryosu bulundu. Gemini arayüzüne yazmadan doğrudan görsel üretimine geçiliyor...", "success");
          scriptData = promptData.custom_script;
        } else {
          const promptText = promptData.prompt;
          logGemini("Senaryo promptu Gemini'a yazılıyor...", "info");
          const inputArea = await waitForPromptInput();
          if (!inputArea) throw new Error("Prompt giriş alanı bulunamadı.");

          simulateTyping(inputArea, promptText);
          await new Promise(r => setTimeout(r, 500));

          logGemini("Senaryo oluşturulması için prompt gönderildi. Cevap bekleniyor...", "info");
          const initialTurns = getTurnCount();
          const clickSuccess = clickSendButton();
          if (!clickSuccess) throw new Error("Gönder butonu bulunamadı.");
          await new Promise(r => setTimeout(r, 1000));
    
          await waitForGeminiGeneration(initialTurns);
          logGemini("Senaryo cevabı alındı. Ayrıştırılıyor...", "success");

          const rawText = getLastResponseText();
          let parsed = robustCleanAndParseJson(rawText);
          scriptData = normalizeScriptData(parsed);

          // 1. Fallback: Full chat history scan
          if (!isValidScriptData(scriptData)) {
            logGemini("Doğrudan yanıtta senaryo bulunamadı, sohbet geçmişi taranıyor...", "warning");
            const found = findScriptInChatHistory();
            if (found && found.scriptData) {
              scriptData = normalizeScriptData(found.scriptData);
            }
          }

          // 2. Fallback: All model-turn elements scan in DOM
          if (!isValidScriptData(scriptData)) {
            const allTurns = Array.from(document.querySelectorAll('model-response, model-turn, .model-turn, message-content, [data-turn-role="model"], p-chat-turn, chat-turn, code-block, pre, .markdown'));
            for (let t = allTurns.length - 1; t >= 0; t--) {
              const turnText = (allTurns[t].innerText || allTurns[t].textContent || '').trim();
              if (turnText && turnText.length > 50) {
                const turnParsed = robustCleanAndParseJson(turnText);
                const norm = normalizeScriptData(turnParsed);
                if (isValidScriptData(norm)) {
                  scriptData = norm;
                  break;
                }
              }
            }
          }

          if (!isValidScriptData(scriptData)) {
            logGemini("JSON Ayrıştırma hatası! Ham veri console loga yazıldı.", "error");
            console.log("[GEMINI-AUTO-RAW-TEXT]:", rawText);
            throw new Error("Gemini geçerli bir JSON yanıtı üretmedi. Lütfen tekrar deneyin.");
          }
          await new Promise((resolve) => {
            chrome.storage.local.set({
              gemini_auto_active: true,
              gemini_auto_channel_id: channelId,
              gemini_auto_use_temp_chat: useTempChat,
              gemini_auto_video_count: videoCount,
              gemini_auto_nasa_option: nasaOption,
              gemini_auto_loop: loop,
              gemini_auto_videos_produced: videosProduced,
              gemini_auto_row_id: rowId,
              gemini_auto_script_data: scriptData,
              gemini_auto_custom_images: customImages,
              last_selected_channel: channelId
            }, resolve);
          });
        }
      }
    }


      logGemini("Senaryo başarıyla ayrıştırıldı. Başlık: " + getScriptTitle(scriptData), "success");

      // customImages is already defined at the loop start

      let shouldGenerateImagesWithGemini = true;
      if (category === "reddit_stories" || category === "reddit") {
        shouldGenerateImagesWithGemini = false;
        logGemini("Reddit Hikayeleri kategorisi: Görseller sistem tarafından telifsiz ASMR video ve Reddit soru kartı olarak otomatik oluşturulacak.", "info");
      } else if (category === "aviation") {
        shouldGenerateImagesWithGemini = false;
        logGemini("Havacılık kategorisi: Görseller ve videolar sistem tarafından Pixabay 1080p B-roll ve Wikimedia NTSB arşivi olarak otomatik temin edilecek.", "info");
      } else if (category === "crayon_combat" || category === "military" || category === "military_tech" || String(category).includes("combat") || String(category).includes("crayon")) {
        shouldGenerateImagesWithGemini = false;
        logGemini("Crayon Combat kategorisi: Görseller sistem tarafından Vektörel Çöp Adam ve Taktik Blueprint motoru ile otomatik üretilecek.", "info");
      } else if (forceLocalSD) {
        shouldGenerateImagesWithGemini = false;
        logGemini("Görsel kaynağı tercihi: Zorunlu Yerel SD Fallback Aktif (Limit/Kota Sıfırlanma Aşıldı).", "info");
      } else if (category === "space") {
        if (nasaOption === "nasa") {
          shouldGenerateImagesWithGemini = false;
          logGemini("Görsel kaynağı tercihi: NASA API ile Devam Et. Görsel üretimi NASA API'ye bırakılıyor.", "info");
        } else if (nasaOption === "gemini") {
          shouldGenerateImagesWithGemini = true;
          logGemini("Görsel kaynağı tercihi: Görsel Oluşturarak Devam Et. Görseller Gemini ile üretilecek.", "info");
        } else {
          // mixed / karışık (default)
          const notesLower = (item.notlar || "").toLowerCase();
          const topicLower = (item.konu || "").toLowerCase();
          const titleLower = (item.baslik || "").toLowerCase();
          if (notesLower.includes("nasa") || topicLower.includes("nasa") || titleLower.includes("nasa")) {
            shouldGenerateImagesWithGemini = false;
            logGemini("Görsel kaynağı tercihi: Karışık. Planda NASA API belirtildiği için görsel üretimi NASA API'ye bırakılıyor.", "info");
          } else {
            logGemini("Görsel kaynağı tercihi: Karışık. Planda NASA belirtilmemiş; görseller Gemini ile üretilecek.", "info");
          }
        }
      }

      if (!shouldGenerateImagesWithGemini) {
        if (category === "reddit_stories" || category === "reddit") {
          logGemini("Görseller sistem tarafından ASMR video ve soru kartı olarak otomatik üretilecek.", "info");
        } else if (category === "aviation") {
          logGemini("Görseller/videolar sistem tarafından Pixabay 1080p B-roll ve Wikimedia NTSB arşivi olarak otomatik temin edilecek.", "info");
        } else {
          logGemini("Görsel üretimi sistem entegrasyonu (NASA / Yerel Motor) üzerinden sağlanacağı için Gemini görsel üretimi atlanıyor.", "info");
        }
      } else {
        const isWhatsapp = (category === "whatsapp_stories" || category === "whatsapp_chat" || category === "whatsapp");
        const isShorts = isWhatsapp ? true : !!(channel && channel.shorts_mode);
        const resolution = isWhatsapp ? "512x512" : (isShorts ? "512x768" : "768x512");
        let scenes = getScriptScenes(scriptData);
        const isGroupChat = isWhatsapp && detectIsGroupChat(scriptData);
        if (isWhatsapp) {
          if (isGroupChat) {
            logGemini(`WhatsApp Grup Sohbeti: Grup için 1 tematik amblem ve ${scenes.length - 1} katılımcı avatarı üretilecek (Toplam ${scenes.length} görsel).`, "info");
          } else {
            logGemini("WhatsApp Mesajlaşma kategorisi: Sohbet başlığı için 1 adet 1:1 profil avatarı üretilecek.", "info");
            if (scenes.length > 1) {
              scenes = [scenes[0]];
            }
          }
        }

        if (activeImageProvider === "perchance") {
          logGemini(`Görsel üretimi Perchance API ile başlatılıyor. Toplam ${scenes.length} sahne var. Format: ${isWhatsapp ? '1:1 (WhatsApp Profil Avatarı - 512x512)' : (isShorts ? '9:16 (Shorts - 512x768)' : '16:9 (Yatay - 768x512)')}`, "info");
        } else {
          logGemini("Senaryo hafızaya alındı. Görselleri üretmek için Resimler Gem'ine geçiliyor...", "info");
          await new Promise((resolve) => {
            chrome.storage.local.set({
              gemini_auto_active: true,
              gemini_auto_channel_id: channelId,
              gemini_auto_use_temp_chat: useTempChat,
              gemini_auto_video_count: videoCount,
              gemini_auto_nasa_option: nasaOption,
              gemini_auto_loop: loop,
              gemini_auto_videos_produced: videosProduced,
              gemini_auto_row_id: rowId,
              gemini_auto_script_data: scriptData,
              gemini_auto_custom_images: customImages,
              gemini_auto_image_provider: activeImageProvider,
              last_selected_channel: channelId
            }, resolve);
          });
          const navOk = await navigateToResimlerGem();
          if (!navOk) {
            isNavigatingRedirect = true;
            logGemini("Resimler Gem'ine yönlendiriliyor. Sayfa yüklendiğinde otomasyon otomatik devam edecek.", "info");
            return;
          }
          logGemini(`Resimler Gem'inde görsel üretimi başlıyor. Toplam ${scenes.length} sahne var.`, "info");
        }

        // Sayfadaki mevcut tüm görselleri önceden 'işlenmiş' olarak işaretle
        document.querySelectorAll('img').forEach(img => {
          img.setAttribute('data-yt-oto-processed', 'true');
        });

        for (let i = 0; i < scenes.length; i++) {
          if (!geminiRunning) {
            logGemini("Kullanıcı tarafından durduruldu.", "error");
            break;
          }

          if (customImages[i.toString()]) {
            logGemini(`Sahne ${i+1}/${scenes.length} görseli önceki oturumdan zaten alınmış, geçiliyor.`, "success");
            continue;
          }

          // Sahne başlamadan önce sayfadaki mevcut görselleri snapshot'a al
          const beforeSrcs = new Set();
          document.querySelectorAll('img').forEach(img => {
            if (img.src) beforeSrcs.add(img.src);
            if (img.currentSrc) beforeSrcs.add(img.currentSrc);
          });

          const scene = scenes[i];
          let imagePrompt = scene.image_prompt;
          if (isWhatsapp) {
            if (isGroupChat) {
              if (!imagePrompt || imagePrompt.toLowerCase().includes("whatsapp_chat")) {
                if (i === 0) {
                  imagePrompt = buildGroupAvatarPrompt(scriptData);
                } else {
                  imagePrompt = buildParticipantAvatarPrompt(scene.sender_name || `Participant ${i}`, scriptData);
                }
              }
            } else {
              const contactName = (scriptData && scriptData.contact_name) || "friend";
              if (scriptData && scriptData.contact_avatar_prompt) {
                imagePrompt = refineAvatarPrompt(scriptData.contact_avatar_prompt, contactName, scriptData);
              } else if (!imagePrompt || imagePrompt.toLowerCase().includes("whatsapp_chat")) {
                imagePrompt = buildCharacterAvatarPrompt(contactName, scriptData);
              } else {
                imagePrompt = refineAvatarPrompt(imagePrompt, contactName, scriptData);
              }
            }
          }
          logGemini(`Sahne ${i+1}/${scenes.length} görseli üretiliyor: "${imagePrompt}"`, "info");

          let success = false;
          let retries = 0;
          const maxRetries = 3;

          // ── SEÇENEK 1: Perchance API ile Üretim ──
          if (activeImageProvider === "perchance") {
            while (!success && retries < maxRetries) {
              if (!geminiRunning) break;
              try {
                logGemini(`Sahne ${i+1} Perchance API ile üretiliyor (${resolution})...`, "info");
                const base64Data = await generateImageViaPerchanceAPI(imagePrompt, isShorts, isWhatsapp);
                saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                chrome.storage.local.set({
                  gemini_auto_custom_images: customImages
                });
                logGemini(`Sahne ${i+1} görseli Perchance API ile başarıyla üretildi (${resolution}).`, "success");
                success = true;
              } catch (err) {
                retries++;
                logGemini(`Sahne ${i+1} Perchance API hatası: ${err.message} (${retries}/${maxRetries})`, "warning");
                await new Promise(r => setTimeout(r, 2000));
              }
            }
          } else {
            // ── SEÇENEK 2: Gemini ile Üretim ve Limit Bitince Kesintisiz Perchance API Fallback ──
            while (!success && retries < maxRetries) {
              if (!geminiRunning) break;
              if (retries > 0) {
                logGemini(`Sahne ${i+1} için görsel üretimi başarısız oldu. Yeniden deneniyor (${retries}/${maxRetries})...`, "warning");
              }

              try {
                const promptInput = await waitForPromptInput(12000);
                if (!promptInput) throw new Error("Görsel prompt giriş alanı bulunamadı.");

                const imgPromptText = isWhatsapp
                  ? (isGroupChat && i === 0
                      ? `Generate exactly one image (square 1:1 aspect ratio, authentic circular emblem badge symbol for a WhatsApp group profile photo, aesthetic graphic icon, clean composition, strictly NO humans, no human faces, no selfie portrait, no text, no frame, no borders, no watermark): ${imagePrompt}. Respond ONLY with the generated image.`
                      : `Generate exactly one image (square 1:1 aspect ratio, authentic close-up smartphone selfie photo for a WhatsApp profile picture, photorealistic human face portrait, natural casual lighting, high resolution, no text, no frame, no borders, no watermark): ${imagePrompt}. Respond ONLY with the generated image.`)
                  : (isShorts 
                    ? `Generate exactly one image (only 1 image, no multiple options, no variations) of: ${imagePrompt} in 9:16 aspect ratio. Respond only with the image.`
                    : `Generate exactly one image (only 1 image, no multiple options, no variations) of: ${imagePrompt} in 16:9 aspect ratio. Respond only with the image.`);
                
                simulateTyping(promptInput, imgPromptText);
                await new Promise(r => setTimeout(r, 600));

                const clickSuccessImg = clickSendButton();
                if (!clickSuccessImg) {
                  const enterDown = new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true });
                  promptInput.dispatchEvent(enterDown);
                }
                await new Promise(r => setTimeout(r, 1500));

                // Görsel veya kota uyarısını bekle (max 45 sn)
                const startWait = Date.now();
                let foundImage = null;

                while (Date.now() - startWait < 45000 && geminiRunning) {
                  // 1. Kota aşımı kontrolü
                  const lastText = (getLastResponseText() || "").toLowerCase();
                  const alertTexts = Array.from(document.querySelectorAll('[role="alert"], gem-snack-bar, .snack-bar, .error-message, mat-snack-bar-container, .toast, [role="status"]')).map(el => (el.innerText || el.textContent || '').toLowerCase()).join(" ");
                  const combinedCheck = (lastText + " " + alertTexts).toLowerCase();

                  const isQuotaExceeded = combinedCheck.includes("limit resets") ||
                    combinedCheck.includes("usage in settings") ||
                    combinedCheck.includes("quota exceeded") ||
                    combinedCheck.includes("limit doldu") ||
                    combinedCheck.includes("kota doldu") ||
                    combinedCheck.includes("günlük limit") ||
                    combinedCheck.includes("rate limit") ||
                    combinedCheck.includes("too many requests") ||
                    (combinedCheck.includes("limit") && (combinedCheck.includes("reset") || combinedCheck.includes("sıfırla") || combinedCheck.includes("doldu") || combinedCheck.includes("sınır") || combinedCheck.includes("bitti")));

                  if (isQuotaExceeded) {
                    logGemini(`⚠️ Sahne ${i+1} için Gemini görsel üretim limiti doldu! Sayfa terk edilmeden Perchance API sistemine geçiliyor...`, "warning");
                    activeImageProvider = "perchance";
                    chrome.storage.local.set({ gemini_auto_image_provider: "perchance" });
                    logGemini(`Sahne ${i+1} Perchance API ile üretiliyor (${resolution})...`, "info");
                    const base64Data = await generateImageViaPerchanceAPI(imagePrompt, isShorts, isWhatsapp);
                    saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                    chrome.storage.local.set({ gemini_auto_custom_images: customImages });
                    logGemini(`Sahne ${i+1} görseli Perchance API ile başarıyla tamamlandı (${resolution}). Kalan sahneler Perchance API ile üretilecek.`, "success");
                    success = true;
                    break;
                  }

                  // 2. Yeni görsel kontrolü (en yeni/en alttaki görselden başlayarak geriye doğru tara)
                  const candidateImgs = getUnprocessedImages(beforeSrcs);
                  for (let k = candidateImgs.length - 1; k >= 0; k--) {
                    const cImg = candidateImgs[k];
                    const isLoaded = cImg.complete || cImg.naturalWidth > 0;
                    const isBig = cImg.naturalWidth >= 100 || cImg.clientWidth >= 100 || cImg.width >= 100;
                    if (isLoaded && isBig) {
                      foundImage = cImg;
                      break;
                    }
                  }

                  if (foundImage) {
                    break;
                  }

                  await new Promise(r => setTimeout(r, 1000));
                }

                if (success) {
                  break;
                }

                if (foundImage) {
                  foundImage.setAttribute('data-yt-oto-processed', 'true');
                  beforeSrcs.add(foundImage.src);
                  if (foundImage.currentSrc) beforeSrcs.add(foundImage.currentSrc);
                  const imgUrl = foundImage.src || foundImage.currentSrc;
                  const base64Data = await getBase64FromUrl(imgUrl, foundImage);
                  saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                  chrome.storage.local.set({ gemini_auto_custom_images: customImages });
                  logGemini(`Sahne ${i+1} görseli başarıyla alındı.`, "success");
                  success = true;
                } else {
                  retries++;
                  logGemini(`Sahne ${i+1} için görsel bulunamadı (Zaman aşımı - ${retries}/${maxRetries}).`, "warning");
                  if (retries >= maxRetries) {
                    logGemini(`Gemini yanıt vermedi. Sahne ${i+1} Perchance API'ye aktarılıyor...`, "warning");
                    activeImageProvider = "perchance";
                    chrome.storage.local.set({ gemini_auto_image_provider: "perchance" });
                    try {
                      const base64Data = await generateImageViaPerchanceAPI(imagePrompt, isShorts, isWhatsapp);
                      saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                      chrome.storage.local.set({ gemini_auto_custom_images: customImages });
                      logGemini(`Sahne ${i+1} görseli Perchance API ile tamamlandı.`, "success");
                      success = true;
                    } catch (pErr) {
                      logGemini(`Perchance fallback hatası: ${pErr.message}`, "error");
                    }
                  }
                }
              } catch (gErr) {
                retries++;
                logGemini(`Gemini görsel denemesi hatası (${retries}/${maxRetries}): ${gErr.message}`, "warning");
                if (retries >= maxRetries) {
                  logGemini(`Gemini hatası nedeniyle Perchance API sistemine geçiliyor...`, "warning");
                  activeImageProvider = "perchance";
                  chrome.storage.local.set({ gemini_auto_image_provider: "perchance" });
                  try {
                    const base64Data = await generateImageViaPerchanceAPI(imagePrompt, isShorts, isWhatsapp);
                    saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                    chrome.storage.local.set({ gemini_auto_custom_images: customImages });
                    logGemini(`Sahne ${i+1} görseli Perchance API ile üretildi.`, "success");
                    success = true;
                  } catch (pErr) {
                    logGemini(`Perchance fallback hatası: ${pErr.message}`, "error");
                  }
                }
                await new Promise(r => setTimeout(r, 2000));
              }
            }
          }

          if (!success) {
            logGemini(`Uyarı: Sahne ${i+1} için görsel üretilemedi!`, "error");
          }
          if (isWhatsapp && success) {
            if (!isGroupChat || i === scenes.length - 1) {
              logGemini("WhatsApp profil görselleri başarıyla hazırlandı. Video üretimine geçiliyor...", "success");
              break;
            }
          }
        }
      }

      // ── VİDEO PAKETİNİ OLUŞTUR VE HAFIZAYA AL (HENÜZ ÜRETİM / SEKME BAŞLATMA) ──
      if (!isValidScriptData(scriptData)) {
        throw new Error("Geçerli bir senaryo verisi bulunamadı. Video paketi oluşturulamadı.");
      }

      const imageCount = Object.keys(customImages).length;
      const videoTitle = getScriptTitle(scriptData);
      const videoBundle = {
        index: loop + 1,
        is_group: isGroup,
        channel_id: isGroup ? null : targetId,
        group_id: isGroup ? targetId : null,
        target_id: targetId,
        row_id: rowId.toString(),
        script: scriptData,
        images: customImages,
        title: videoTitle
      };

      stagedBatch.push(videoBundle);
      videosProduced = stagedBatch.length;

      // 1. Tarayıcı extension hafızasına anında kaydet (veri kaybını önler)
      await chrome.storage.local.set({
        gemini_staged_batch: stagedBatch,
        gemini_auto_loop: loop + 1,
        gemini_auto_videos_produced: videosProduced,
        gemini_auto_row_id: null,
        gemini_auto_script_data: null,
        gemini_auto_custom_images: {}
      });

      // 2. Arka uç diskine de stage et (sayfa kapansa bile veriler asla kaybolmaz)
      try {
        await produceViaBackground(`${apiUrl}/api/staging/gemini-item`, videoBundle);
      } catch (stgErr) {
        console.warn("[YT-OTO] Arka uç disk staging uyarısı:", stgErr);
      }

      logGemini(`[Video ${loop + 1}/${videoCount}] Senaryo ve ${imageCount} görsel başarıyla hafızaya alındı: "${videoTitle}"`, "success");

      // Videolar arasında kısa bekleme süresi veriyoruz
      if (loop + 1 < videoCount) {
        logGemini(`[Video ${loop + 1}/${videoCount}] tamamlandı. Sıradaki video (${loop + 2}/${videoCount}) için Gemini sohbeti açılıyor...`, "info");
        await new Promise(r => setTimeout(r, 2000));
      }
    }

    // ── TÜM VİDEOLARIN GEMINI AŞAMASI BİTTİĞİNDE ARKA UÇTA SIRALI ÜRETİMİ BAŞLAT ──
    const validBatch = stagedBatch.filter(item => item && item.script && typeof item.script === "object");
    if (validBatch.length > 0) {
      logGemini(`🎉 İstenen tüm videoların (${validBatch.length}/${videoCount}) senaryo ve görselleri Gemini tarafında başarıyla hazırlandı!`, "success");
      
      const envData = await new Promise(r => chrome.storage.local.get(["gemini_auto_target_env", "gemini_auto_sync_mac"], r));
      const targetEnv = envData.gemini_auto_target_env || "local";
      const autoSyncMac = (typeof envData.gemini_auto_sync_mac === "boolean") ? envData.gemini_auto_sync_mac : true;

      validBatch.forEach(item => {
        item.target_env = targetEnv;
        item.auto_youtube_upload = false;
        item.auto_sync_mac = autoSyncMac;
      });

      logGemini(`Videolar ${targetEnv === 'remote' ? 'Oracle Cloud sunucusunda (nice 19)' : 'lokal arka uçta'} sırayla üretilmek üzere sisteme gönderiliyor...`, "info");

      const batchRes = await produceViaBackground(`${apiUrl}/api/produce-gemini-batch`, {
        items: validBatch,
        target_env: targetEnv,
        auto_sync_mac: autoSyncMac
      });

      if (!batchRes.ok) {
        const errDetail = batchRes.data ? JSON.stringify(batchRes.data) : "Bilinmeyen hata";
        throw new Error(`Sıralı video üretimi başlatılamadı: ${errDetail}`);
      }

      const batchData = await batchRes.json();
      const execId = batchData.exec_id;

      logGemini(`Sıralı üretim başarıyla başlatıldı! Görev ID: ${execId}`, "success");
      logGemini(`Yönetim paneli tek bir sekmede açılıyor, ${stagedBatch.length} video bu sekmede sırayla üretilecek...`, "info");

      // Hafızadaki staged batch'i temizle
      await chrome.storage.local.remove(["gemini_staged_batch"]);

      // SADECE TEK BİR SEKME AÇILIR!
      window.open(`${apiUrl}/?exec_id=${execId}`, '_blank');
    }

    logGemini(`Otomasyon tamamlandı! Toplam ${videosProduced}/${videoCount} video başarıyla işlendi.`, "success");

  } catch (err) {
    logGemini(`Hata oluştu: ${err.message}`, "error");
  } finally {
    geminiRunning = false;
    toggleStartButtonState(false);
    
    if (!isNavigatingRedirect) {
      chrome.storage.local.remove([
        "gemini_auto_active",
        "gemini_auto_provider",
        "gemini_auto_fallback_local",
        "gemini_auto_custom_images",
        "gemini_auto_row_id",
        "gemini_auto_script_data",
        "gemini_auto_processed_row_ids"
      ]);
    }

    if (thinkingBar) thinkingBar.style.display = "none";
    if (creature) creature.style.display = "none";
    if (selectGroup) selectGroup.style.display = "flex";
    if (modeGroup) modeGroup.style.display = "flex";
    if (countGroup) countGroup.style.display = "flex";
    
    // Eğer seçili kanal uzay kanalıysa Görsel Kaynağı alanını tekrar göster
    const select = document.getElementById("gemini-channel-select");
    if (select && nasaGroup) {
      const channelId = select.value;
      const channel = geminiChannelsList.find(c => c.channel_id === channelId);
      if (channel && channel.topic_category === "space") {
        nasaGroup.style.display = "flex";
      }
    }
  }
}

async function runGeminiQueueAutomation(queueList, options = {}) {
  geminiRunning = true;
  let isNavigatingRedirect = false;
  const apiUrl = await getApiUrl();
  
  const useTempChat = !!options.useTempChat;
  let activeImageProvider = options.imgProvider || "gemini";
  const targetEnv = options.targetEnv || "local";
  const autoSyncMac = (typeof options.autoSyncMac === "boolean") ? options.autoSyncMac : true;

  // Kurtarma / devam etme parametreleri
  const startQIdx = (typeof options.startQIdx === "number") ? options.startQIdx : 0;
  const startVIdx = (typeof options.startVIdx === "number") ? options.startVIdx : 0;
  let currentPhase = options.resumedPhase || "script"; // "script" veya "images"
  let resumedRowId = options.resumedRowId || null;
  let resumedScriptData = options.resumedScriptData || null;
  let resumedCustomImages = options.resumedCustomImages || {};
  let resumedCategory = options.resumedCategory || null;
  let resumedItem = options.resumedItem || null;
  let resumedChannel = options.resumedChannel || null;

  // Yerel SD zorlama bayrağı
  const storageData = await new Promise(resolve => chrome.storage.local.get("gemini_auto_fallback_local", resolve));
  const forceLocalSD = !!storageData.gemini_auto_fallback_local;

  const totalVideos = (queueList || []).reduce((acc, q) => acc + (q.count || 0), 0);

  chrome.storage.local.set({
    gemini_auto_active: true,
    gemini_auto_mode: "queue",
    gemini_auto_queue: queueList,
    gemini_auto_use_temp_chat: useTempChat,
    gemini_auto_image_provider: activeImageProvider,
    gemini_auto_target_env: targetEnv,
    gemini_auto_sync_mac: autoSyncMac,
    gemini_queue_q_idx: startQIdx,
    gemini_queue_v_idx: startVIdx,
    gemini_queue_phase: currentPhase
  });

  logGemini(`📋 Kuyruk otomasyonu devrede! Toplam ${queueList.length} kanal, ${totalVideos} video işlenecek. Hedef: ${targetEnv === 'remote' ? 'Oracle Cloud Sunucusu (132.226.187.103)' : 'Lokal (Mac)'}`, "info");

  const thinkingBar = document.getElementById("gemini-thinking-bar");
  if (thinkingBar) thinkingBar.style.display = "block";
  const creature = document.getElementById("gemini-working-creature");
  if (creature) creature.style.display = "flex";

  const paneSingle = document.getElementById("gemini-pane-single");
  const paneQueue = document.getElementById("gemini-pane-queue");
  if (paneSingle) paneSingle.style.display = "none";
  if (paneQueue) paneQueue.style.display = "none";

  // Oturum boyunca işlenen satır ID'leri
  let sessionProcessedRowIds = [];
  const storedProcessed = await new Promise(r => chrome.storage.local.get("gemini_auto_processed_row_ids", r));
  if (storedProcessed && Array.isArray(storedProcessed.gemini_auto_processed_row_ids)) {
    sessionProcessedRowIds = storedProcessed.gemini_auto_processed_row_ids.map(x => x.toString());
  }

  let stagedBatch = [];
  const storedStaged = await new Promise(r => chrome.storage.local.get("gemini_staged_batch", r));
  if (storedStaged && Array.isArray(storedStaged.gemini_staged_batch)) {
    if (startQIdx > 0 || startVIdx > 0 || currentPhase === "images") {
      stagedBatch = storedStaged.gemini_staged_batch.filter(b => b && b.script && typeof b.script === "object");
    } else {
      chrome.storage.local.remove(["gemini_staged_batch"]);
    }
  }

  let completedQueueVideos = stagedBatch.length;

  try {
    for (let qIdx = startQIdx; qIdx < queueList.length; qIdx++) {
      if (!geminiRunning) break;
      const qItem = queueList[qIdx];
      const channelId = qItem.id;
      const isGroup = qItem.type === "group" || channelId.startsWith("group:");
      const targetId = isGroup ? channelId.replace("group:", "") : channelId;
      const channelName = qItem.raw_name || qItem.name;
      const countForChannel = qItem.count || 1;

      logGemini(`▶️ [Kanal Sırası ${qIdx + 1}/${queueList.length}] "${channelName}" (${countForChannel} video)`, "info");

      const vStart = (qIdx === startQIdx) ? startVIdx : 0;

      for (let vIdx = vStart; vIdx < countForChannel; vIdx++) {
        if (!geminiRunning) {
          logGemini("Otomasyon kullanıcı tarafından durduruldu.", "error");
          break;
        }

        const isResumingImages = (qIdx === startQIdx && vIdx === startVIdx && currentPhase === "images" && resumedScriptData);

        let scriptData = isResumingImages ? resumedScriptData : null;
        let rowId = isResumingImages ? resumedRowId : null;
        let item = isResumingImages ? resumedItem : null;
        let channel = isResumingImages ? resumedChannel : null;
        let category = isResumingImages ? (resumedCategory || (channel ? channel.topic_category : (isGroup ? "reddit_stories" : "space"))) : (isGroup ? "reddit_stories" : "space");
        let customImages = isResumingImages ? (resumedCustomImages || {}) : {};

        if (!isResumingImages) {
          completedQueueVideos++;
          logGemini(`[Kuyruk Video ${completedQueueVideos}/${totalVideos}] "${channelName}" (Video ${vIdx + 1}/${countForChannel}) için temiz sohbet açılıyor...`, "info");

          // Durumu hafızaya al
          await chrome.storage.local.set({
            gemini_queue_q_idx: qIdx,
            gemini_queue_v_idx: vIdx,
            gemini_queue_phase: "script",
            gemini_queue_row_id: null,
            gemini_queue_script_data: null,
            gemini_queue_custom_images: {}
          });

          // Her yeni video için temiz sohbet aç
          const ready = await startNewChat();
          if (!ready) {
            isNavigatingRedirect = true;
            return;
          }
        await new Promise(r => setTimeout(r, 1200));

        // Sıradaki üretilmemiş konuyu çek
        const excludeQuery = sessionProcessedRowIds.length > 0 ? `?exclude_ids=${sessionProcessedRowIds.join(',')}` : '';
        const planUrl = isGroup 
          ? `${apiUrl}/api/groups/${targetId}/plan/next-unproduced${excludeQuery}` 
          : `${apiUrl}/api/channels/${targetId}/plan/next-unproduced${excludeQuery}`;
        
        const planRes = await fetchFromBackground(planUrl);
        if (!planRes.ok) throw new Error(`Plan satırı alınamadı: HTTP ${planRes.status}`);
        const planData = await planRes.json();

        if (!planData.success || (!planData.has_unproduced && !planData.item)) {
          logGemini(`⚠️ "${channelName}" için üretilecek yeni konu bulunamadı. Sonraki kanala geçiliyor...`, "warning");
          break;
        }

        item = planData.item;
        channel = planData.channel || null;
        rowId = item.id;
        const topic = item.konu;
        category = channel ? channel.topic_category : (isGroup ? "reddit_stories" : "space");
        if (qItem.topic_category) category = qItem.topic_category;

        if (rowId && !sessionProcessedRowIds.includes(rowId.toString())) {
          sessionProcessedRowIds.push(rowId.toString());
          chrome.storage.local.set({ gemini_auto_processed_row_ids: sessionProcessedRowIds });
        }

        logGemini(`[Konu Eşleşti] "${item.baslik || topic}" [Sıra ID: ${rowId}]`, "info");

        if (useTempChat) {
          await toggleTemporaryChatIfNeeded(true);
        }

        // Prompt al
        const promptUrl = isGroup 
          ? `${apiUrl}/api/groups/${targetId}/plan/${rowId}/gemini-prompt` 
          : `${apiUrl}/api/channels/${targetId}/plan/${rowId}/gemini-prompt`;
        const promptRes = await fetchFromBackground(promptUrl, { method: "POST" });
        if (!promptRes.ok) throw new Error(`Prompt alınamadı: HTTP ${promptRes.status}`);
        const promptData = await promptRes.json();

        scriptData = null;
        if (promptData.custom_script) {
          logGemini("Hazır Shorts senaryosu kullanılıyor.", "success");
          scriptData = promptData.custom_script;
        } else {
          const promptText = promptData.prompt;
          const inputArea = await waitForPromptInput();
          if (!inputArea) throw new Error("Prompt giriş alanı bulunamadı.");

          simulateTyping(inputArea, promptText);
          await new Promise(r => setTimeout(r, 500));

          const initialTurns = getTurnCount();
          const clickSuccess = clickSendButton();
          if (!clickSuccess) throw new Error("Gönder butonu bulunamadı.");
          await new Promise(r => setTimeout(r, 1000));

          await waitForGeminiGeneration(initialTurns);
          logGemini("Senaryo cevabı alındı. Ayrıştırılıyor...", "success");

          const rawText = getLastResponseText();
          let parsed = robustCleanAndParseJson(rawText);
          scriptData = normalizeScriptData(parsed);

          if (!isValidScriptData(scriptData)) {
            const found = findScriptInChatHistory();
            if (found && found.scriptData) scriptData = normalizeScriptData(found.scriptData);
          }

          if (!isValidScriptData(scriptData)) {
            const allTurns = Array.from(document.querySelectorAll('model-response, model-turn, .model-turn, message-content, [data-turn-role="model"], p-chat-turn, chat-turn, code-block, pre, .markdown'));
            for (let t = allTurns.length - 1; t >= 0; t--) {
              const turnText = (allTurns[t].innerText || allTurns[t].textContent || '').trim();
              if (turnText && turnText.length > 50) {
                const turnParsed = robustCleanAndParseJson(turnText);
                const norm = normalizeScriptData(turnParsed);
                if (isValidScriptData(norm)) {
                  scriptData = norm;
                  break;
                }
              }
            }
          }

          if (!isValidScriptData(scriptData)) {
            throw new Error(`Senaryo geçerli JSON formatında oluşturulamadı (Kanal: ${channelName}, ID: ${rowId})`);
          }
        }

        logGemini(`Senaryo hazır: "${getScriptTitle(scriptData)}"`, "success");
      } else {
        logGemini(`[Kuyruk Kurtarma] "${getScriptTitle(scriptData)}" senaryosu hafızadan geri yüklendi. Görseller üretiliyor...`, "success");
      }

      // Görselleri hazırla
      const isWhatsapp = (category === "whatsapp_stories" || category === "whatsapp_chat" || category === "whatsapp");
      const isReddit = (category === "reddit_stories" || category === "reddit");
      const isAviation = (category === "aviation");
      const isShorts = isWhatsapp ? true : !!(channel && channel.shorts_mode);
      const resolution = isWhatsapp ? "512x512" : (isShorts ? "512x768" : "768x512");

      let shouldGenerateImages = true;
      if (isReddit || isAviation || forceLocalSD) {
        shouldGenerateImages = false;
        if (isAviation) {
          logGemini("Havacılık kategorisi: Görseller ve videolar sistem tarafından Pixabay 1080p B-roll ve Wikimedia NTSB arşivi olarak otomatik temin edilecek.", "info");
        } else if (isReddit) {
          logGemini("Reddit kategorisi: Görseller sistem tarafından telifsiz ASMR video ve soru kartı olarak otomatik temin edilecek.", "info");
        }
      } else if (category === "space") {
        const notesLower = (item?.notlar || "").toLowerCase();
        const topicLower = (item?.konu || "").toLowerCase();
        const titleLower = (item?.baslik || "").toLowerCase();
        if (notesLower.includes("nasa") || topicLower.includes("nasa") || titleLower.includes("nasa")) {
          shouldGenerateImages = false;
          logGemini("Görseller NASA API üzerinden otomatik temin edilecek.", "info");
        }
      }

      if (shouldGenerateImages) {
        let scenes = getScriptScenes(scriptData);
        const isGroupChat = isWhatsapp && detectIsGroupChat(scriptData);
        if (isWhatsapp && !isGroupChat && scenes.length > 1) {
          scenes = [scenes[0]];
        }

        // Durumu hafızaya al (görsel üretimi fazına geçildi)
        await chrome.storage.local.set({
          gemini_queue_q_idx: qIdx,
          gemini_queue_v_idx: vIdx,
          gemini_queue_phase: "images",
          gemini_queue_row_id: rowId,
          gemini_queue_script_data: scriptData,
          gemini_queue_custom_images: customImages,
          gemini_queue_category: category,
          gemini_queue_item: item,
          gemini_queue_channel: channel
        });

        if (activeImageProvider === "gemini") {
          logGemini("Görselleri Imagen ile üretmek için Resimler Gem'ine (/images) geçiliyor...", "info");
          const navOk = await navigateToResimlerGem();
          if (!navOk) {
            isNavigatingRedirect = true;
            logGemini("Resimler Gem'ine yönlendiriliyor. Sayfa yüklendiğinde kuyruk otomatik devam edecek.", "info");
            return;
          }
        }

        logGemini(`Görseller hazırlanıyor (Toplam ${scenes.length} görsel, Motor: ${activeImageProvider === 'perchance' ? 'Perchance API' : 'Gemini /images'})...`, "info");

        // Sayfadaki mevcut görselleri işlenmiş olarak işaretle
        document.querySelectorAll('img').forEach(img => {
          img.setAttribute('data-yt-oto-processed', 'true');
        });

        for (let i = 0; i < scenes.length; i++) {
          if (!geminiRunning) break;

          if (customImages[i.toString()]) {
            logGemini(`Sahne ${i+1}/${scenes.length} görseli önceki oturumdan hazır, geçiliyor.`, "success");
            continue;
          }

          // Sahne başlamadan önce sayfadaki mevcut görselleri snapshot'a al
          const beforeSrcs = new Set();
          document.querySelectorAll('img').forEach(img => {
            if (img.src) beforeSrcs.add(img.src);
            if (img.currentSrc) beforeSrcs.add(img.currentSrc);
          });

          const scene = scenes[i];
          let imagePrompt = (typeof scene === "string") ? scene : (scene.visual_prompt || scene.gorsel_betimleme || scene.image_prompt || scene.description || scene.text || scene.konusma || "");
          
          if (isWhatsapp) {
            if (isGroupChat) {
              if (!imagePrompt || imagePrompt.toLowerCase().includes("whatsapp_chat")) {
                if (i === 0) {
                  imagePrompt = buildGroupAvatarPrompt(scriptData);
                } else {
                  imagePrompt = buildParticipantAvatarPrompt(scene.sender_name || `Participant ${i}`, scriptData);
                }
              }
            } else {
              const contactName = (scriptData && scriptData.contact_name) || "friend";
              if (scriptData && scriptData.contact_avatar_prompt) {
                imagePrompt = refineAvatarPrompt(scriptData.contact_avatar_prompt, contactName, scriptData);
              } else if (!imagePrompt || imagePrompt.toLowerCase().includes("whatsapp_chat")) {
                imagePrompt = buildCharacterAvatarPrompt(contactName, scriptData);
              } else {
                imagePrompt = refineAvatarPrompt(imagePrompt, contactName, scriptData);
              }
            }
          }

          logGemini(`Sahne ${i+1}/${scenes.length} görseli üretiliyor: "${imagePrompt}"`, "info");

          let success = false;
          let retries = 0;
          const maxRetries = 3;

          // 1. Perchance API ile Üretim
          if (activeImageProvider === "perchance") {
            while (!success && retries < maxRetries) {
              if (!geminiRunning) break;
              try {
                logGemini(`Sahne ${i+1}/${scenes.length} Perchance API ile üretiliyor (${resolution})...`, "info");
                const base64Data = await generateImageViaPerchanceAPI(imagePrompt, isShorts, isWhatsapp);
                saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                chrome.storage.local.set({ gemini_queue_custom_images: customImages });
                logGemini(`Sahne ${i+1}/${scenes.length} görseli Perchance API ile tamamlandı (${resolution}).`, "success");
                success = true;
              } catch (pErr) {
                retries++;
                logGemini(`Perchance hata (${retries}/${maxRetries}): ${pErr.message}`, "warning");
                await new Promise(r => setTimeout(r, 2000));
              }
            }
          } else {
            // 2. Gemini /images ile Üretim (Kota dolarsa otomatik Perchance fallback)
            while (!success && retries < maxRetries) {
              if (!geminiRunning) break;
              if (retries > 0) {
                logGemini(`Sahne ${i+1} için yeniden deneniyor (${retries}/${maxRetries})...`, "warning");
              }

              try {
                const promptInput = await waitForPromptInput(12000);
                if (!promptInput) throw new Error("Görsel prompt alanı bulunamadı.");

                const imgPromptText = isWhatsapp
                  ? (isGroupChat && i === 0
                      ? `Generate exactly one image (square 1:1 aspect ratio, authentic circular emblem badge symbol for a WhatsApp group profile photo, aesthetic graphic icon, clean composition, strictly NO humans, no human faces, no selfie portrait, no text, no frame, no borders, no watermark): ${imagePrompt}. Respond ONLY with the generated image.`
                      : `Generate exactly one image (square 1:1 aspect ratio, authentic close-up smartphone selfie photo for a WhatsApp profile picture, photorealistic human face portrait, natural casual lighting, high resolution, no text, no frame, no borders, no watermark): ${imagePrompt}. Respond ONLY with the generated image.`)
                  : (isShorts 
                    ? `Generate exactly one image (only 1 image, no multiple options, no variations) of: ${imagePrompt} in 9:16 aspect ratio. Respond only with the image.`
                    : `Generate exactly one image (only 1 image, no multiple options, no variations) of: ${imagePrompt} in 16:9 aspect ratio. Respond only with the image.`);
                
                simulateTyping(promptInput, imgPromptText);
                await new Promise(r => setTimeout(r, 600));

                const sendOk = clickSendButton();
                if (!sendOk) {
                  const enterDown = new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true });
                  promptInput.dispatchEvent(enterDown);
                }
                await new Promise(r => setTimeout(r, 1500));

                // Yanıt / Görsel bekleme döngüsü (max 45 sn)
                const startWait = Date.now();
                let foundImage = null;

                while (Date.now() - startWait < 45000 && geminiRunning) {
                  // 1. Kota aşımı ve rate limit kontrolü
                  const lastText = (getLastResponseText() || "").toLowerCase();
                  const alertTexts = Array.from(document.querySelectorAll('[role="alert"], gem-snack-bar, .snack-bar, .error-message, mat-snack-bar-container, .toast, [role="status"]')).map(el => (el.innerText || el.textContent || '').toLowerCase()).join(" ");
                  const combinedCheck = (lastText + " " + alertTexts).toLowerCase();

                  const isQuotaExceeded = combinedCheck.includes("limit resets") ||
                    combinedCheck.includes("usage in settings") ||
                    combinedCheck.includes("quota exceeded") ||
                    combinedCheck.includes("limit doldu") ||
                    combinedCheck.includes("kota doldu") ||
                    combinedCheck.includes("günlük limit") ||
                    combinedCheck.includes("rate limit") ||
                    combinedCheck.includes("too many requests") ||
                    (combinedCheck.includes("limit") && (combinedCheck.includes("reset") || combinedCheck.includes("sıfırla") || combinedCheck.includes("doldu") || combinedCheck.includes("sınır") || combinedCheck.includes("bitti")));

                  if (isQuotaExceeded) {
                    logGemini(`⚠️ Gemini görsel üretim kotası doldu! Kesintisiz olarak Perchance API sistemine geçiliyor...`, "warning");
                    activeImageProvider = "perchance";
                    chrome.storage.local.set({ gemini_auto_image_provider: "perchance" });
                    logGemini(`Sahne ${i+1} Perchance API ile üretiliyor (${resolution})...`, "info");
                    const base64Data = await generateImageViaPerchanceAPI(imagePrompt, isShorts, isWhatsapp);
                    saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                    await chrome.storage.local.set({ gemini_queue_custom_images: customImages });
                    logGemini(`Sahne ${i+1} görseli Perchance API ile başarıyla üretildi (${resolution}). Kalan sahneler de Perchance ile üretilecek.`, "success");
                    success = true;
                    break;
                  }

                  // 2. Yeni görsel kontrolü (en yeni/en alttaki görselden başlayarak geriye doğru tara)
                  const candidateImgs = getUnprocessedImages(beforeSrcs);
                  for (let k = candidateImgs.length - 1; k >= 0; k--) {
                    const cImg = candidateImgs[k];
                    const isLoaded = cImg.complete || cImg.naturalWidth > 0;
                    const isBig = cImg.naturalWidth >= 100 || cImg.clientWidth >= 100 || cImg.width >= 100;
                    if (isLoaded && isBig) {
                      foundImage = cImg;
                      break;
                    }
                  }

                  if (foundImage) {
                    break;
                  }

                  await new Promise(r => setTimeout(r, 1000));
                }

                if (success) {
                  break;
                }

                if (foundImage) {
                  foundImage.setAttribute('data-yt-oto-processed', 'true');
                  beforeSrcs.add(foundImage.src);
                  if (foundImage.currentSrc) beforeSrcs.add(foundImage.currentSrc);
                  const imgUrl = foundImage.src || foundImage.currentSrc;
                  const base64Data = await getBase64FromUrl(imgUrl, foundImage);
                  saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                  await chrome.storage.local.set({ gemini_queue_custom_images: customImages });
                  logGemini(`Sahne ${i+1}/${scenes.length} görseli Gemini /images üzerinden başarıyla alındı.`, "success");
                  success = true;
                } else {
                  retries++;
                  logGemini(`Sahne ${i+1} için görsel bulunamadı (Zaman aşımı - ${retries}/${maxRetries}).`, "warning");
                  if (retries >= maxRetries) {
                    logGemini(`Gemini yanıt vermedi. Sahne ${i+1} Perchance API'ye aktarılıyor...`, "warning");
                    activeImageProvider = "perchance";
                    chrome.storage.local.set({ gemini_auto_image_provider: "perchance" });
                    try {
                      const base64Data = await generateImageViaPerchanceAPI(imagePrompt, isShorts, isWhatsapp);
                      saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                      await chrome.storage.local.set({ gemini_queue_custom_images: customImages });
                      logGemini(`Sahne ${i+1} görseli Perchance API ile tamamlandı.`, "success");
                      success = true;
                    } catch(pErr) {
                      logGemini(`Perchance fallback hatası: ${pErr.message}`, "error");
                    }
                  }
                }
              } catch (gErr) {
                retries++;
                logGemini(`Gemini görsel denemesi hatası (${retries}/${maxRetries}): ${gErr.message}`, "warning");
                if (retries >= maxRetries) {
                  logGemini(`Gemini hatası nedeniyle Perchance API sistemine geçiliyor...`, "warning");
                  activeImageProvider = "perchance";
                  chrome.storage.local.set({ gemini_auto_image_provider: "perchance" });
                  try {
                    const base64Data = await generateImageViaPerchanceAPI(imagePrompt, isShorts, isWhatsapp);
                    saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
                    await chrome.storage.local.set({ gemini_queue_custom_images: customImages });
                    logGemini(`Sahne ${i+1} görseli Perchance API ile üretildi.`, "success");
                    success = true;
                  } catch (pErr) {
                    logGemini(`Perchance fallback hatası: ${pErr.message}`, "error");
                  }
                }
                await new Promise(r => setTimeout(r, 2000));
              }
            }
          }

          if (!success) {
            logGemini(`Uyarı: Sahne ${i+1} için görsel temin edilemedi!`, "error");
          }

          if (isWhatsapp && success && (!isGroupChat || i === scenes.length - 1)) {
            break;
          }
        }
      }

      // ── VİDEO BUNDLE'I HAFIZAYA VE SUNUCUYA STAGE ET ──
      if (!isValidScriptData(scriptData)) {
        throw new Error(`Geçerli bir senaryo verisi bulunamadı ("${channelName}", Konu ID: ${rowId}). Video paketi oluşturulamadı.`);
      }

      const videoTitle = getScriptTitle(scriptData);
      const videoBundle = {
        index: stagedBatch.length + 1,
        is_group: isGroup,
        channel_id: isGroup ? null : targetId,
        group_id: isGroup ? targetId : null,
        target_id: targetId,
        row_id: rowId ? rowId.toString() : "",
        script: scriptData,
        images: customImages,
        title: videoTitle,
        target_env: targetEnv,
        auto_sync_mac: autoSyncMac,
        auto_youtube_upload: false
      };

      stagedBatch.push(videoBundle);
      await chrome.storage.local.set({ gemini_staged_batch: stagedBatch });
      try {
        await produceViaBackground(`${apiUrl}/api/staging/gemini-item`, videoBundle);
      } catch (stgErr) {
        console.warn("[YT-OTO] Staging uyarısı:", stgErr);
      }

      logGemini(`[Kuyruk Video ${stagedBatch.length}/${totalVideos}] "${videoTitle}" senaryo ve görselleri hafızaya alındı!`, "success");

      // Sıradaki video için durum ayarla
      currentPhase = "script";
      resumedScriptData = null;
      resumedRowId = null;
      resumedCustomImages = {};

      let nextQ = qIdx;
      let nextV = vIdx + 1;
      if (nextV >= countForChannel) {
        nextQ = qIdx + 1;
        nextV = 0;
      }

      await chrome.storage.local.set({
        gemini_queue_q_idx: nextQ,
        gemini_queue_v_idx: nextV,
        gemini_queue_phase: "script",
        gemini_queue_row_id: null,
        gemini_queue_script_data: null,
        gemini_queue_custom_images: {},
        gemini_queue_category: null,
        gemini_queue_item: null,
        gemini_queue_channel: null
      });

      // Eğer kuyrukta başka video varsa ve şu an /images sayfasındaysak, ana sohbet (/app) sayfasına geç
      const hasMoreVideos = (nextQ < queueList.length);
      if (hasMoreVideos && window.location.pathname.includes('/images')) {
        logGemini("Sıradaki video için ana sohbet ekranına (/app) yönlendiriliyor...", "info");
        const ready = await startNewChat();
        if (!ready) {
          isNavigatingRedirect = true;
          return;
        }
      }

      await new Promise(r => setTimeout(r, 1200));
    }
  }

  // Toplu üretim gönderimi
  const validBatchItems = stagedBatch.filter(b => b && b.script && typeof b.script === "object");
  if (validBatchItems.length > 0) {
    logGemini(`🎉 Kuyruktaki tüm videolar (${validBatchItems.length} adet) için senaryo ve görseller hazırlandı!`, "success");
    logGemini(`Videolar ${targetEnv === 'remote' ? 'Oracle Cloud sunucusunda (nice 19)' : 'lokal arka uçta'} sırayla üretilmek üzere sisteme gönderiliyor...`, "info");

    const batchRes = await produceViaBackground(`${apiUrl}/api/produce-gemini-batch`, {
      items: validBatchItems,
      target_env: targetEnv,
      auto_sync_mac: autoSyncMac
    });

    if (!batchRes.ok) {
      const errText = await batchRes.text().catch(() => "");
      throw new Error(`Sıralı video üretimi başlatılamadı: HTTP ${batchRes.status} ${errText}`);
    }

    const batchData = await batchRes.json();
    const execId = batchData.exec_id;
    logGemini(`Sıralı üretim başarıyla başlatıldı! Görev ID: ${execId}`, "success");
    logGemini(`Yönetim paneli tek bir sekmede açılıyor...`, "info");

    await chrome.storage.local.remove([
      "gemini_staged_batch",
      "gemini_auto_queue",
      "gemini_queue_q_idx",
      "gemini_queue_v_idx",
      "gemini_queue_phase",
      "gemini_queue_row_id",
      "gemini_queue_script_data",
      "gemini_queue_custom_images",
      "gemini_queue_category",
      "gemini_queue_item",
      "gemini_queue_channel"
    ]);
    geminiQueue = [];
    updateQueueUI();

    window.open(`${apiUrl}/?exec_id=${execId}`, '_blank');
  }

  logGemini(`Otomasyon tamamlandı! Toplam ${stagedBatch.length} video işlendi.`, "success");

} catch (err) {
  logGemini(`Kuyruk hatası: ${err.message}`, "error");
} finally {
  geminiRunning = false;
  toggleStartButtonState(false);
  if (!isNavigatingRedirect) {
    chrome.storage.local.remove([
      "gemini_auto_active",
      "gemini_auto_mode",
      "gemini_auto_custom_images",
      "gemini_auto_row_id",
      "gemini_auto_script_data",
      "gemini_auto_processed_row_ids",
      "gemini_queue_q_idx",
      "gemini_queue_v_idx",
      "gemini_queue_phase",
      "gemini_queue_row_id",
      "gemini_queue_script_data",
      "gemini_queue_custom_images",
      "gemini_queue_category",
      "gemini_queue_item",
      "gemini_queue_channel"
    ]);
  }
  if (thinkingBar) thinkingBar.style.display = "none";
  if (creature) creature.style.display = "none";
  if (geminiActiveTab === "queue") {
    if (paneQueue) paneQueue.style.display = "flex";
  } else {
    if (paneSingle) paneSingle.style.display = "flex";
  }
}
}

async function checkGeminiLoginState(targetAuthUser) {
  for (let attempt = 0; attempt < 10; attempt++) {
    const avatar = document.querySelector('a[gem-open-account-menu], .mavatar-container, .mavatar-footer-row, .mavatar-footer-left');
    if (avatar) return true;
    
    // Check if there is a sign in button or if the url is signin options
    if (document.body.textContent.includes("Oturum açın") || document.body.textContent.includes("Sign in")) {
      return false;
    }
    await new Promise(r => setTimeout(r, 500));
  }
  return false;
}

async function tryRotateGoogleAccount(channelId, useTempChat, videoCount, nasaOption, currentLoop, videosProduced, customImages, rowId, scriptData) {
  logGemini("Diğer signed-in Google hesapları taranıyor...", "info");
  
  // Parse current authuser from URL
  const urlParams = new URLSearchParams(window.location.search);
  let currentAuthUser = parseInt(urlParams.get("authuser") || "0");
  
  // Try to extract signed-in indices from the DOM first
  let signedInIndices = [];
  try {
    const accountBtn = document.querySelector('a[gem-open-account-menu], .mavatar-footer-left, .mavatar-footer-row a');
    if (accountBtn) {
      accountBtn.click();
      await new Promise(r => setTimeout(r, 1200));
      const links = document.querySelectorAll('a[href*="authuser="]');
      links.forEach(a => {
        const match = a.href.match(/authuser=(\d+)/);
        if (match) {
          const idx = parseInt(match[1]);
          if (!signedInIndices.includes(idx)) signedInIndices.push(idx);
        }
      });
      // Close menu
      accountBtn.click();
    }
  } catch (e) {
    console.warn("[YT-OTO] Failed to scan account menu:", e);
  }
  
  // If we couldn't find any other accounts, fallback to incrementing
  let nextAuthUser = -1;
  if (signedInIndices.length > 0) {
    signedInIndices.sort((a, b) => a - b);
    const nextIdx = signedInIndices.find(idx => idx > currentAuthUser);
    if (nextIdx !== undefined) {
      nextAuthUser = nextIdx;
    }
  } else {
    nextAuthUser = currentAuthUser + 1;
  }
  
  if (nextAuthUser === -1 || nextAuthUser > 10) {
    logGemini("Kullanılabilir başka bir Google hesabı bulunamadı.", "warning");
    return false;
  }
  
  logGemini(`Hesap ${currentAuthUser} -> Hesap ${nextAuthUser} geçişi yapılıyor. Sayfa yeniden yüklenecek...`, "info");
  
  // Save current automation state to storage
  const state = {
    gemini_auto_active: true,
    gemini_auto_channel_id: channelId,
    gemini_auto_use_temp_chat: useTempChat,
    gemini_auto_video_count: videoCount,
    gemini_auto_nasa_option: nasaOption,
    gemini_auto_videos_produced: videosProduced,
    gemini_auto_loop: currentLoop,
    gemini_auto_custom_images: customImages,
    gemini_auto_authuser: nextAuthUser,
    gemini_auto_row_id: rowId,
    gemini_auto_script_data: scriptData
  };
  
  await new Promise(resolve => chrome.storage.local.set(state, resolve));
  
  // Navigate to the next account
  const nextUrl = new URL(window.location.href);
  nextUrl.searchParams.set("authuser", nextAuthUser.toString());
  window.location.href = nextUrl.toString();
  return true;
}


function openGeminiModal() {
  const existing = document.getElementById("gemini-oto-modal");
  if (existing) {
    existing.style.display = "flex";
    loadChannelsDropdown();
    if (geminiActiveTab === "queue") {
      loadQueueChannelsList();
    }
    return;
  }

  // Inject CSS keyframes and custom scrollbars
  if (!document.getElementById("gemini-oto-styles")) {
    const style = document.createElement("style");
    style.id = "gemini-oto-styles";
    style.textContent = `
      @keyframes ytOtoFadeIn {
        from { opacity: 0; transform: translateY(8px) scale(0.99); }
        to { opacity: 1; transform: translateY(0) scale(1); }
      }
      @keyframes shine {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
      }
      @keyframes telemetryScan {
        0% { stroke-dashoffset: 100; opacity: 0.35; }
        50% { stroke-dashoffset: 0; opacity: 1; }
        100% { stroke-dashoffset: -100; opacity: 0.35; }
      }
      @keyframes liveStatusPulse {
        0% { opacity: 0.4; transform: scale(0.9); }
        100% { opacity: 1; transform: scale(1.15); box-shadow: 0 0 8px #10b981; }
      }
      #gemini-modal-body::-webkit-scrollbar, #gemini-queue-channels-list::-webkit-scrollbar {
        width: 5px;
      }
      #gemini-modal-body::-webkit-scrollbar-track, #gemini-queue-channels-list::-webkit-scrollbar-track {
        background: #090d16;
        border-radius: 4px;
      }
      #gemini-modal-body::-webkit-scrollbar-thumb, #gemini-queue-channels-list::-webkit-scrollbar-thumb {
        background: #1e293b;
        border-radius: 4px;
      }
      #gemini-modal-body::-webkit-scrollbar-thumb:hover, #gemini-queue-channels-list::-webkit-scrollbar-thumb:hover {
        background: #334155;
      }
    `;
    document.head.appendChild(style);
  }

  const modal = document.createElement("div");
  modal.id = "gemini-oto-modal";
  modal.style.cssText = `
    position: fixed; bottom: 84px; right: 24px; width: 440px; max-width: calc(100vw - 48px);
    max-height: calc(100vh - 100px);
    background: #090d16; border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.04);
    color: #f8fafc; display: flex; flex-direction: column;
    z-index: 10000000;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    animation: ytOtoFadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    overflow: hidden; box-sizing: border-box;
  `;

  // ── 1. HEADER (Pinned at top) ─────────────────────────────
  const header = document.createElement("div");
  header.style.cssText = `
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 18px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #0b0f19; flex-shrink: 0; box-sizing: border-box;
  `;
  header.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px;">
      <span style="font-family: ui-monospace, SFMono-Regular, monospace; font-size: 10px; font-weight: 700; color: #38bdf8; background: rgba(2, 132, 199, 0.15); border: 1px solid rgba(56, 189, 248, 0.25); padding: 2px 6px; border-radius: 4px; letter-spacing: 0.04em;">YT-OTO</span>
      <h3 style="margin: 0; font-size: 13.5px; font-weight: 700; color: #f8fafc; letter-spacing: -0.01em;">
        Gemini Core Assistant
      </h3>
    </div>
  `;
  
  const closeBtn = document.createElement("button");
  closeBtn.textContent = "✕";
  closeBtn.style.cssText = `
    background: transparent; border: none; color: #94a3b8; font-size: 16px;
    cursor: pointer; padding: 4px; line-height: 1; transition: color 0.15s;
  `;
  closeBtn.addEventListener("mouseenter", () => closeBtn.style.color = "#f8fafc");
  closeBtn.addEventListener("mouseleave", () => closeBtn.style.color = "#94a3b8");
  closeBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });
  header.appendChild(closeBtn);
  modal.appendChild(header);

  // ── 2. TAB NAVIGATION BAR (Pinned under header) ───────────
  const navTabs = document.createElement("div");
  navTabs.id = "gemini-modal-tabs";
  navTabs.style.cssText = `
    display: flex; gap: 6px; padding: 8px 14px;
    background: #0b0f19; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    flex-shrink: 0; box-sizing: border-box;
  `;

  const tabSingle = document.createElement("button");
  tabSingle.id = "gemini-tab-btn-single";
  tabSingle.textContent = "⚡ Tekli Üretim";
  tabSingle.style.cssText = `
    background: #0284c7; color: #ffffff; font-weight: 600; border-radius: 6px;
    padding: 6px 12px; font-size: 12px; border: 1px solid rgba(56, 189, 248, 0.35); cursor: pointer; transition: all 0.15s ease;
  `;

  const tabQueue = document.createElement("button");
  tabQueue.id = "gemini-tab-btn-queue";
  tabQueue.innerHTML = `📋 Kuyruk <span id="gemini-queue-badge" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; font-size: 10px; padding: 1px 5px; border-radius: 8px; margin-left: 4px; font-weight: 700;">0</span>`;
  tabQueue.style.cssText = `
    background: transparent; color: #94a3b8; font-weight: 500; border-radius: 6px;
    padding: 6px 12px; font-size: 12px; border: 1px solid transparent; cursor: pointer; transition: all 0.15s ease;
  `;

  navTabs.appendChild(tabSingle);
  navTabs.appendChild(tabQueue);
  modal.appendChild(navTabs);

  // ── 3. SCROLLABLE MODAL BODY ──────────────────────────────
  const modalBody = document.createElement("div");
  modalBody.id = "gemini-modal-body";
  modalBody.style.cssText = `
    flex: 1 1 auto; overflow-y: auto; overflow-x: hidden;
    padding: 14px 18px; display: flex; flex-direction: column; gap: 12px;
    box-sizing: border-box;
  `;

  // ── 3A. PANE 1: TEKLİ ÜRETİM ─────────────────────────────
  const paneSingle = document.createElement("div");
  paneSingle.id = "gemini-pane-single";
  paneSingle.style.cssText = `display: flex; flex-direction: column; gap: 12px;`;

  // 1. Hedef Kanal
  const group = document.createElement("div");
  group.id = "gemini-channel-group";
  group.style.cssText = `display: flex; flex-direction: column; gap: 6px;`;
  group.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">1. Hedef Kanal Seçin</label>
    <select id="gemini-channel-select" style="background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 8px 10px; border-radius: 8px; font-size: 13.5px; outline: none; cursor: pointer;"></select>
  `;
  paneSingle.appendChild(group);

  const selectEl = group.querySelector("#gemini-channel-select");
  selectEl.addEventListener("change", () => {
    const channelId = selectEl.value;
    if (channelId) {
      chrome.storage.local.set({
        gemini_auto_channel_id: channelId,
        last_selected_channel: channelId
      });
    }
    const channel = geminiChannelsList.find(c => c.channel_id === channelId || c.id === channelId);
    const nasaGroup = document.getElementById("gemini-nasa-option-group");
    if (channel && channel.topic_category === "space") {
      if (nasaGroup) nasaGroup.style.display = "flex";
    } else {
      if (nasaGroup) nasaGroup.style.display = "none";
    }
    loadIncompleteVideos(channelId);
  });

  // Uzay Görsel Kaynağı
  const nasaOptionGroup = document.createElement("div");
  nasaOptionGroup.id = "gemini-nasa-option-group";
  nasaOptionGroup.style.cssText = `display: none; flex-direction: column; gap: 6px;`;
  nasaOptionGroup.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">Görsel Kaynağı (Uzay Kanalı)</label>
    <select id="gemini-nasa-option-select" style="background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 8px 10px; border-radius: 8px; font-size: 13.5px; outline: none; cursor: pointer;">
      <option value="mixed">Karışık (Plandaki Yönergeye Göre)</option>
      <option value="nasa">NASA API ile Devam Et</option>
      <option value="gemini">Görsel Oluşturarak Devam Et</option>
    </select>
  `;
  paneSingle.appendChild(nasaOptionGroup);

  // 2. Sohbet Tercihi
  const modeGroup = document.createElement("div");
  modeGroup.id = "gemini-mode-group";
  modeGroup.style.cssText = `display: flex; flex-direction: column; gap: 6px;`;
  modeGroup.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">2. Sohbet Tercihi</label>
    <div style="display: flex; gap: 16px; margin-top: 4px;">
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-chat-mode" value="normal" checked style="accent-color: #38bdf8;">
        Devam Et (Normal)
      </label>
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-chat-mode" value="temp" style="accent-color: #38bdf8;">
        Geçici Sohbet
      </label>
    </div>
  `;
  paneSingle.appendChild(modeGroup);

  // 3. Yarım Kalanı Baştan Üret
  const incompleteGroup = document.createElement("div");
  incompleteGroup.id = "gemini-incomplete-group";
  incompleteGroup.style.cssText = `display: flex; flex-direction: column; gap: 6px; margin-bottom: 2px;`;
  incompleteGroup.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">3. Yarım Kalanı Baştan Üret (İsteğe Bağlı)</label>
    <select id="gemini-incomplete-select" style="background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 8px 10px; border-radius: 8px; font-size: 13.5px; outline: none; cursor: pointer; max-width: 100%;">
      <option value="">-- Sıradaki Üretilmemiş Konu --</option>
    </select>
  `;
  paneSingle.appendChild(incompleteGroup);

  // 4. Görsel Üretim Motoru
  const providerGroup = document.createElement("div");
  providerGroup.id = "gemini-provider-group";
  providerGroup.style.cssText = `display: flex; flex-direction: column; gap: 6px; margin-bottom: 2px;`;
  providerGroup.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">4. Görsel Üretim Motoru</label>
    <div style="display: flex; gap: 14px; margin-top: 2px;">
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-img-provider" value="gemini" checked style="accent-color: #38bdf8;">
        Gemini ile Üret
      </label>
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-img-provider" value="perchance" style="accent-color: #38bdf8;">
        Perchance ile Üret (Hızlı API)
      </label>
    </div>
    <span style="font-size: 11px; color: #64748b;">(Gemini kotası dolduğunda otomatik olarak Perchance ile devam edilir)</span>
  `;
  paneSingle.appendChild(providerGroup);

  chrome.storage.local.get(["gemini_auto_image_provider"], (data) => {
    if (data.gemini_auto_image_provider) {
      const radio = providerGroup.querySelector(`input[name="gemini-img-provider"][value="${data.gemini_auto_image_provider}"]`);
      if (radio) radio.checked = true;
    }
  });

  providerGroup.querySelectorAll('input[name="gemini-img-provider"]').forEach(r => {
    r.addEventListener('change', () => {
      chrome.storage.local.set({ gemini_auto_image_provider: r.value });
      // Queue tab radio sync
      const qRadio = document.querySelector(`input[name="gemini-queue-img-provider"][value="${r.value}"]`);
      if (qRadio) qRadio.checked = true;
    });
  });

  // 5. Video Üretim Yeri & YouTube Dağıtımı
  const envGroup = document.createElement("div");
  envGroup.id = "gemini-env-group";
  envGroup.style.cssText = `
    display: flex; flex-direction: column; gap: 8px; margin-bottom: 4px;
    padding: 10px 12px; background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px;
  `;
  envGroup.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between;">
      <label style="font-size: 12px; font-weight: 600; color: #38bdf8;">5. Video Üretim Yeri & Mac'e İndirme</label>
      <span id="gemini-server-badge" style="font-size: 10.5px; color: #10b981; font-family: monospace; display: flex; align-items: center; gap: 4px;">
        <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
        Oracle Cloud Aktif
      </span>
    </div>
    <div style="display: flex; gap: 14px; margin-top: 2px;">
      <label style="display: flex; align-items: center; gap: 6px; font-size: 12.5px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-target-env" value="local" checked style="accent-color: #38bdf8;">
        Lokal (Mac)
      </label>
      <label style="display: flex; align-items: center; gap: 6px; font-size: 12.5px; cursor: pointer; color: #38bdf8; font-weight: 600;">
        <input type="radio" name="gemini-target-env" value="remote" style="accent-color: #38bdf8;">
        Oracle Cloud Sunucusu (132.226.187.103)
      </label>
    </div>
    <label style="display: flex; align-items: center; gap: 6px; font-size: 11.5px; cursor: pointer; color: #e2e8f0; margin-top: 2px;">
      <input type="checkbox" id="gemini-auto-sync-mac" checked style="accent-color: #10b981;">
      <span>Üretim bitince otomatik Mac 'yuklenecek' klasörüne indir ve sunucudan sil</span>
    </label>
  `;
  paneSingle.appendChild(envGroup);

  chrome.storage.local.get(["gemini_auto_target_env", "gemini_auto_sync_mac"], (data) => {
    if (data.gemini_auto_target_env) {
      const radio = envGroup.querySelector(`input[name="gemini-target-env"][value="${data.gemini_auto_target_env}"]`);
      if (radio) radio.checked = true;
    }
    if (typeof data.gemini_auto_sync_mac === "boolean") {
      const chk = envGroup.querySelector("#gemini-auto-sync-mac");
      if (chk) chk.checked = data.gemini_auto_sync_mac;
    }
  });

  envGroup.querySelectorAll('input[name="gemini-target-env"]').forEach(r => {
    r.addEventListener('change', () => {
      chrome.storage.local.set({ gemini_auto_target_env: r.value });
      const qRadio = document.querySelector(`input[name="gemini-queue-target-env"][value="${r.value}"]`);
      if (qRadio) qRadio.checked = true;
    });
  });

  const syncChk = envGroup.querySelector("#gemini-auto-sync-mac");
  if (syncChk) {
    syncChk.addEventListener('change', () => {
      chrome.storage.local.set({ gemini_auto_sync_mac: syncChk.checked });
      const qChk = document.getElementById("gemini-queue-auto-sync-mac");
      if (qChk) qChk.checked = syncChk.checked;
    });
  }

  // Özel Bölge Sansürü Akordiyonu
  const censorAccordion = document.createElement("div");
  censorAccordion.style.cssText = `
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px; background: #0f172a; padding: 10px;
    display: flex; flex-direction: column; gap: 8px;
  `;
  censorAccordion.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between; cursor: pointer;" id="gemini-censor-toggle-btn">
      <span style="font-size: 12.5px; font-weight: 600; color: #38bdf8;">🔧 Görsel Özel Bölge Sansürü</span>
      <span id="gemini-censor-arrow" style="font-size: 12px; color: #94a3b8;">▼</span>
    </div>
    <div id="gemini-censor-content" style="display: none; flex-direction: column; gap: 8px; margin-top: 6px;">
      <div style="display: flex; gap: 10px; align-items: center; justify-content: space-between;">
        <div style="display: flex; gap: 6px; align-items: center;">
          <span style="font-size: 12px; color: #94a3b8;">Format:</span>
          <select id="gemini-censor-format" style="background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 4px 6px; border-radius: 6px; font-size: 12px; outline: none; cursor: pointer;">
            <option value="landscape">Yatay (16:9)</option>
            <option value="portrait">Dikey (9:16)</option>
          </select>
        </div>
        <label style="display: flex; align-items: center; gap: 4px; font-size: 12px; cursor: pointer; color: #cbd5e1;">
          <input type="checkbox" id="gemini-censor-enabled" style="accent-color: #38bdf8;">
          Aktif
        </label>
      </div>
      <div style="display: flex; flex-direction: column; gap: 4px;">
        <span style="font-size: 11px; color: #94a3b8;">Referans Görsel Seç (Çizerek Alan Seçmek İçin):</span>
        <input type="file" id="gemini-censor-file-input" accept="image/*" style="font-size: 11px; color: #94a3b8; cursor: pointer;" />
      </div>
      <div id="gemini-censor-canvas-container" style="position: relative; display: none; margin: 6px 0; border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; overflow: hidden; background: #000; user-select: none; cursor: crosshair;">
        <img id="gemini-censor-preview-img" style="width: 100%; display: block; pointer-events: none;" />
        <div id="gemini-censor-selector" style="position: absolute; border: 2px solid #ef4444; background: rgba(239, 68, 68, 0.35); box-shadow: 0 0 8px rgba(239, 68, 68, 0.5); display: none; pointer-events: none; z-index: 99;"></div>
      </div>
      <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 4px;">
        <div id="gemini-censor-coords" style="font-size: 11px; color: #38bdf8; font-family: monospace;">Koordinat çizilmedi.</div>
        <button id="gemini-censor-save-btn" style="background: #10b981; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;">Kaydet</button>
      </div>
    </div>
  `;

  const toggleBtn = censorAccordion.querySelector("#gemini-censor-toggle-btn");
  const arrowEl = censorAccordion.querySelector("#gemini-censor-arrow");
  const contentEl = censorAccordion.querySelector("#gemini-censor-content");
  const formatSelect = censorAccordion.querySelector("#gemini-censor-format");
  const enabledCheckbox = censorAccordion.querySelector("#gemini-censor-enabled");
  const fileInput = censorAccordion.querySelector("#gemini-censor-file-input");
  const canvasContainer = censorAccordion.querySelector("#gemini-censor-canvas-container");
  const previewImg = censorAccordion.querySelector("#gemini-censor-preview-img");
  const selector = censorAccordion.querySelector("#gemini-censor-selector");
  const coordsDiv = censorAccordion.querySelector("#gemini-censor-coords");
  const saveBtn = censorAccordion.querySelector("#gemini-censor-save-btn");

  let tempCoords = { x: 0, y: 0, w: 0, h: 0 };
  let isDrawing = false;
  let startX = 0, startY = 0;

  toggleBtn.addEventListener("click", () => {
    if (contentEl.style.display === "none") {
      contentEl.style.display = "flex";
      arrowEl.textContent = "▲";
      loadCensorSettings();
    } else {
      contentEl.style.display = "none";
      arrowEl.textContent = "▼";
    }
  });

  async function loadCensorSettings() {
    try {
      const apiUrl = await getApiUrl();
      const res = await fetchFromBackground(`${apiUrl}/api/settings`);
      if (res && res.ok && res.data) {
        const settings = res.data;
        const isPortrait = formatSelect.value === "portrait";
        const prefix = isPortrait ? "censor_custom_portrait" : "censor_custom_landscape";
        
        enabledCheckbox.checked = !!settings[`${prefix}_enabled`];
        const x = settings[`${prefix}_x`] || 0;
        const y = settings[`${prefix}_y`] || 0;
        const w = settings[`${prefix}_w`] || 0;
        const h = settings[`${prefix}_h`] || 0;
        
        tempCoords = { x, y, w, h };
        coordsDiv.textContent = `X: ${x}px, Y: ${y}px, W: ${w}px, H: ${h}px`;
        selector.style.display = "none";
      }
    } catch (e) {
      console.error("[YT-OTO] Ayarlar yüklenirken hata:", e);
    }
  }

  formatSelect.addEventListener("change", loadCensorSettings);

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        previewImg.src = evt.target.result;
        canvasContainer.style.display = "block";
        selector.style.display = "none";
      };
      reader.readAsDataURL(file);
    }
  });

  canvasContainer.addEventListener("mousedown", (evt) => {
    if (evt.button !== 0) return;
    const rect = canvasContainer.getBoundingClientRect();
    startX = evt.clientX - rect.left;
    startY = evt.clientY - rect.top;
    isDrawing = true;
    selector.style.left = startX + "px";
    selector.style.top = startY + "px";
    selector.style.width = "0px";
    selector.style.height = "0px";
    selector.style.display = "block";
  });

  canvasContainer.addEventListener("mousemove", (evt) => {
    if (!isDrawing) return;
    const rect = canvasContainer.getBoundingClientRect();
    const currentX = Math.max(0, Math.min(evt.clientX - rect.left, rect.width));
    const currentY = Math.max(0, Math.min(evt.clientY - rect.top, rect.height));
    const x = Math.min(startX, currentX);
    const y = Math.min(startY, currentY);
    const w = Math.abs(startX - currentX);
    const h = Math.abs(startY - currentY);
    selector.style.left = x + "px";
    selector.style.top = y + "px";
    selector.style.width = w + "px";
    selector.style.height = h + "px";
  });

  canvasContainer.addEventListener("mouseup", (evt) => {
    if (!isDrawing) return;
    isDrawing = false;
    const rect = canvasContainer.getBoundingClientRect();
    const currentX = Math.max(0, Math.min(evt.clientX - rect.left, rect.width));
    const currentY = Math.max(0, Math.min(evt.clientY - rect.top, rect.height));
    const x = Math.min(startX, currentX);
    const y = Math.min(startY, currentY);
    const w = Math.abs(startX - currentX);
    const h = Math.abs(startY - currentY);
    const isPortrait = formatSelect.value === "portrait";
    const orgW = isPortrait ? 1080 : 1920;
    const orgH = isPortrait ? 1920 : 1080;
    const realX = Math.round((x / rect.width) * orgW);
    const realY = Math.round((y / rect.height) * orgH);
    const realW = Math.round((w / rect.width) * orgW);
    const realH = Math.round((h / rect.height) * orgH);
    tempCoords = { x: realX, y: realY, w: realW, h: realH };
    coordsDiv.textContent = `X: ${realX}px, Y: ${realY}px, W: ${realW}px, H: ${realH}px`;
  });

  saveBtn.addEventListener("click", async () => {
    saveBtn.disabled = true;
    saveBtn.textContent = "Kaydediliyor...";
    try {
      const apiUrl = await getApiUrl();
      const isPortrait = formatSelect.value === "portrait";
      const prefix = isPortrait ? "censor_custom_portrait" : "censor_custom_landscape";
      const payload = {
        [`${prefix}_enabled`]: enabledCheckbox.checked,
        [`${prefix}_x`]: tempCoords.x,
        [`${prefix}_y`]: tempCoords.y,
        [`${prefix}_w`]: tempCoords.w,
        [`${prefix}_h`]: tempCoords.h
      };
      const res = await fetchFromBackground(`${apiUrl}/api/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res && res.ok) {
        coordsDiv.textContent = "✓ Başarıyla kaydedildi!";
        setTimeout(() => {
          coordsDiv.textContent = `X: ${tempCoords.x}px, Y: ${tempCoords.y}px, W: ${tempCoords.w}px, H: ${tempCoords.h}px`;
        }, 2000);
      } else {
        alert("Sansür ayarları kaydedilemedi!");
      }
    } catch (err) {
      alert("Bağlantı hatası: " + err.message);
    }
    saveBtn.disabled = false;
    saveBtn.textContent = "Kaydet";
  });

  paneSingle.appendChild(censorAccordion);

  // Tekli mod bilgi kutucuğu
  const singleHint = document.createElement("div");
  singleHint.style.cssText = `
    font-size: 11.5px; color: #38bdf8; background: rgba(56, 189, 248, 0.08);
    border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 6px; padding: 6px 10px;
    display: flex; align-items: center; gap: 6px;
  `;
  singleHint.innerHTML = `<span>⚡</span><span>Tekli üretim modunda Başlat'a basıldığında sıradaki <strong>1 adet video</strong> üretilir. Birden fazla video veya kanal için <strong>Kuyruk</strong> sekmesini kullanabilirsiniz.</span>`;
  paneSingle.appendChild(singleHint);

  modalBody.appendChild(paneSingle);

  // ── 3B. PANE 2: KUYRUK ─────────────────────────────────────
  const paneQueue = document.createElement("div");
  paneQueue.id = "gemini-pane-queue";
  paneQueue.style.cssText = `display: none; flex-direction: column; gap: 12px;`;

  // Kuyruk Üst Başlık ve Butonlar
  const queueHeaderRow = document.createElement("div");
  queueHeaderRow.style.cssText = `display: flex; justify-content: space-between; align-items: center;`;
  queueHeaderRow.innerHTML = `
    <label style="font-size: 12.5px; font-weight: 700; color: #38bdf8;">Aktif Kanallar & Sıralı Kuyruk</label>
    <div style="display: flex; align-items: center; gap: 6px;">
      <button id="gemini-queue-refresh-btn" style="background: transparent; border: 1px solid rgba(56, 189, 248, 0.35); color: #38bdf8; font-size: 11px; padding: 3px 8px; border-radius: 6px; cursor: pointer; transition: all 0.2s;">🔄 Yenile</button>
      <button id="gemini-queue-clear-btn" style="background: transparent; border: 1px solid #475569; color: #94a3b8; font-size: 11px; padding: 3px 8px; border-radius: 6px; cursor: pointer; transition: all 0.2s;">Temizle</button>
    </div>
  `;
  paneQueue.appendChild(queueHeaderRow);

  const queueHint = document.createElement("div");
  queueHint.style.cssText = `font-size: 11.5px; color: #94a3b8; line-height: 1.4;`;
  queueHint.textContent = "Kanal kartına tıklayarak üretim adedini artırın (+1). Tıkladığınız ilk kanal ilk sırada üretilir. Planı tükenen kanallar döngüsel olarak devam eder.";
  paneQueue.appendChild(queueHint);

  // Kanallar Listesi Konteyneri
  const queueChannelsList = document.createElement("div");
  queueChannelsList.id = "gemini-queue-channels-list";
  queueChannelsList.style.cssText = `
    display: flex; flex-direction: column; gap: 6px; max-height: 200px;
    overflow-y: auto; padding-right: 4px;
  `;
  queueChannelsList.innerHTML = `<div style="color: #64748b; font-size: 12px; text-align: center; padding: 12px;">Kanallar yükleniyor...</div>`;
  paneQueue.appendChild(queueChannelsList);

  // Sıra Önizleme Kutusu
  const queueOrderPreview = document.createElement("div");
  queueOrderPreview.id = "gemini-queue-order-preview";
  queueOrderPreview.style.cssText = `
    background: #0f172a; border: 1px dashed #334155; border-radius: 8px;
    padding: 8px 10px; font-size: 11.5px; min-height: 32px;
  `;
  queueOrderPreview.innerHTML = `<span style="color: #64748b;">Kuyruk boş. Yukarıdaki kanallara tıklayarak ekleyin.</span>`;
  paneQueue.appendChild(queueOrderPreview);

  // Kuyruk Tercihleri
  const queuePreferencesGroup = document.createElement("div");
  queuePreferencesGroup.style.cssText = `display: flex; flex-direction: column; gap: 10px; margin-top: 2px;`;

  // 1. Kuyruk Sohbet Tercihi
  const queueModeGroup = document.createElement("div");
  queueModeGroup.id = "gemini-queue-mode-group";
  queueModeGroup.style.cssText = `display: flex; flex-direction: column; gap: 6px;`;
  queueModeGroup.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">1. Sohbet Tercihi</label>
    <div style="display: flex; gap: 16px; margin-top: 2px;">
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-queue-chat-mode" value="normal" checked style="accent-color: #38bdf8;">
        Devam Et (Normal)
      </label>
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-queue-chat-mode" value="temp" style="accent-color: #38bdf8;">
        Geçici Sohbet
      </label>
    </div>
  `;
  queuePreferencesGroup.appendChild(queueModeGroup);

  // 2. Kuyruk Görsel Üretim Motoru
  const queueProviderGroup = document.createElement("div");
  queueProviderGroup.id = "gemini-queue-provider-group";
  queueProviderGroup.style.cssText = `display: flex; flex-direction: column; gap: 6px;`;
  queueProviderGroup.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">2. Görsel Üretim Motoru</label>
    <div style="display: flex; gap: 14px; margin-top: 2px;">
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-queue-img-provider" value="gemini" checked style="accent-color: #38bdf8;">
        Gemini ile Üret
      </label>
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-queue-img-provider" value="perchance" style="accent-color: #38bdf8;">
        Perchance ile Üret (Hızlı API)
      </label>
    </div>
    <span style="font-size: 11px; color: #64748b;">(Gemini kotası dolduğunda otomatik olarak Perchance API ile devam edilir)</span>
  `;
  queuePreferencesGroup.appendChild(queueProviderGroup);

  chrome.storage.local.get(["gemini_auto_image_provider"], (data) => {
    if (data.gemini_auto_image_provider) {
      const radio = queueProviderGroup.querySelector(`input[name="gemini-queue-img-provider"][value="${data.gemini_auto_image_provider}"]`);
      if (radio) radio.checked = true;
    }
  });

  queueProviderGroup.querySelectorAll('input[name="gemini-queue-img-provider"]').forEach(r => {
    r.addEventListener('change', () => {
      chrome.storage.local.set({ gemini_auto_image_provider: r.value });
      const sRadio = document.querySelector(`input[name="gemini-img-provider"][value="${r.value}"]`);
      if (sRadio) sRadio.checked = true;
    });
  });

  // 3. Kuyruk Video Üretim Yeri & Mac'e İndirme
  const queueEnvGroup = document.createElement("div");
  queueEnvGroup.id = "gemini-queue-env-group";
  queueEnvGroup.style.cssText = `
    display: flex; flex-direction: column; gap: 8px;
    padding: 10px 12px; background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px;
  `;
  queueEnvGroup.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between;">
      <label style="font-size: 12px; font-weight: 600; color: #38bdf8;">3. Video Üretim Yeri & Mac'e İndirme</label>
      <span style="font-size: 10.5px; color: #10b981; font-family: monospace; display: flex; align-items: center; gap: 4px;">
        <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
        Oracle Cloud Aktif
      </span>
    </div>
    <div style="display: flex; gap: 14px; margin-top: 2px;">
      <label style="display: flex; align-items: center; gap: 6px; font-size: 12.5px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-queue-target-env" value="local" checked style="accent-color: #38bdf8;">
        Lokal (Mac)
      </label>
      <label style="display: flex; align-items: center; gap: 6px; font-size: 12.5px; cursor: pointer; color: #38bdf8; font-weight: 600;">
        <input type="radio" name="gemini-queue-target-env" value="remote" style="accent-color: #38bdf8;">
        Oracle Cloud Sunucusu (132.226.187.103)
      </label>
    </div>
    <label style="display: flex; align-items: center; gap: 6px; font-size: 11.5px; cursor: pointer; color: #e2e8f0; margin-top: 2px;">
      <input type="checkbox" id="gemini-queue-auto-sync-mac" checked style="accent-color: #10b981;">
      <span>Üretim bitince otomatik Mac 'yuklenecek' klasörüne indir ve sunucudan sil</span>
    </label>
  `;
  queuePreferencesGroup.appendChild(queueEnvGroup);

  chrome.storage.local.get(["gemini_auto_target_env", "gemini_auto_sync_mac"], (data) => {
    if (data.gemini_auto_target_env) {
      const radio = queueEnvGroup.querySelector(`input[name="gemini-queue-target-env"][value="${data.gemini_auto_target_env}"]`);
      if (radio) radio.checked = true;
    }
    if (typeof data.gemini_auto_sync_mac === "boolean") {
      const chk = queueEnvGroup.querySelector("#gemini-queue-auto-sync-mac");
      if (chk) chk.checked = data.gemini_auto_sync_mac;
    }
  });

  queueEnvGroup.querySelectorAll('input[name="gemini-queue-target-env"]').forEach(r => {
    r.addEventListener('change', () => {
      chrome.storage.local.set({ gemini_auto_target_env: r.value });
      const sRadio = document.querySelector(`input[name="gemini-target-env"][value="${r.value}"]`);
      if (sRadio) sRadio.checked = true;
    });
  });

  const queueSyncChk = queueEnvGroup.querySelector("#gemini-queue-auto-sync-mac");
  if (queueSyncChk) {
    queueSyncChk.addEventListener('change', () => {
      chrome.storage.local.set({ gemini_auto_sync_mac: queueSyncChk.checked });
      const sChk = document.getElementById("gemini-auto-sync-mac");
      if (sChk) sChk.checked = queueSyncChk.checked;
    });
  }

  paneQueue.appendChild(queuePreferencesGroup);
  modalBody.appendChild(paneQueue);

  // Queue header buttons listener
  const refreshBtn = queueHeaderRow.querySelector("#gemini-queue-refresh-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      refreshBtn.textContent = "⏳...";
      loadQueueChannelsList().finally(() => {
        refreshBtn.textContent = "🔄 Yenile";
      });
    });
  }

  const clearBtn = queueHeaderRow.querySelector("#gemini-queue-clear-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      geminiQueue = [];
      updateQueueUI();
    });
  }

  // ── 3C. SHARED WORKING TELEMETRY PANEL ────────────────────
  const creature = document.createElement("div");
  creature.id = "gemini-working-creature";
  creature.style.cssText = `
    display: none; align-items: center; justify-content: space-between; padding: 10px 14px;
    background: #090d16; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.3);
    margin-bottom: 6px; animation: ytOtoFadeIn 0.25s ease;
  `;
  creature.innerHTML = `
    <div style="display: flex; align-items: center; gap: 12px; width: 100%;">
      <div style="position: relative; width: 64px; height: 32px; background: rgba(15, 23, 42, 0.8); border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.2); overflow: hidden; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
        <svg width="64" height="32" viewBox="0 0 64 32" style="display: block;">
          <defs>
            <linearGradient id="telemetryPulseGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#0284c7" stop-opacity="0.3" />
              <stop offset="50%" stop-color="#38bdf8" stop-opacity="1" />
              <stop offset="100%" stop-color="#0284c7" stop-opacity="0.3" />
            </linearGradient>
          </defs>
          <line x1="0" y1="16" x2="64" y2="16" stroke="rgba(56, 189, 248, 0.15)" stroke-width="1" stroke-dasharray="2 2" />
          <path d="M 0,16 L 14,16 L 20,6 L 26,26 L 31,11 L 36,21 L 40,16 L 64,16" fill="none" stroke="url(#telemetryPulseGrad)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="stroke-dasharray: 80; animation: telemetryScan 1.6s ease-in-out infinite;" />
        </svg>
        <div style="position: absolute; top: 3px; right: 3px; width: 5px; height: 5px; border-radius: 50%; background: #10b981; animation: liveStatusPulse 1.2s infinite alternate;"></div>
      </div>
      <div style="display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1;">
        <div style="display: flex; align-items: center; gap: 6px;">
          <span style="font-family: ui-monospace, monospace; font-size: 9.5px; font-weight: 700; color: #10b981; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.25); padding: 1px 4px; border-radius: 3px;">PIPELINE</span>
          <span style="font-size: 12px; font-weight: 700; color: #f8fafc; letter-spacing: -0.01em;">OTOMASYON ÇALIŞIYOR</span>
        </div>
        <div style="font-family: ui-monospace, monospace; font-size: 10px; color: #94a3b8; display: flex; align-items: center; gap: 6px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">
          <span style="color: #38bdf8;">ENGINE ACTIVE</span>
          <span style="color: #475569;">•</span>
          <span style="color: #cbd5e1;">Senaryo ve görsel üretim devrede</span>
        </div>
      </div>
    </div>
  `;
  modalBody.appendChild(creature);

  // ── 3D. SHARED CONSOLE LOG ────────────────────────────────
  const consoleGroup = document.createElement("div");
  consoleGroup.style.cssText = `display: flex; flex-direction: column; gap: 6px; flex-shrink: 0;`;
  consoleGroup.innerHTML = `
    <label style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">İşlem Günlüğü (Console)</label>
  `;

  const thinkingBar = document.createElement("div");
  thinkingBar.id = "gemini-thinking-bar";
  thinkingBar.style.cssText = `
    height: 3px; background: linear-gradient(90deg, transparent 0%, #0284c7 35%, #38bdf8 50%, #0284c7 65%, transparent 100%);
    background-size: 200% 100%; animation: shine 1.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    border-radius: 2px; margin-bottom: 6px; display: none;
  `;
  consoleGroup.appendChild(thinkingBar);
  
  const consoleDiv = document.createElement("div");
  consoleDiv.id = "gemini-console";
  consoleDiv.style.cssText = `
    background: #080c14; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;
    height: 120px; padding: 10px; overflow-y: auto; font-family: ui-monospace, monospace;
    font-size: 11px; color: #94a3b8; display: flex; flex-direction: column;
  `;
  consoleDiv.innerHTML = `<div style="color: #64748b;">Hazır. Otomasyonu başlatmak için butona tıklayın...</div>`;
  consoleGroup.appendChild(consoleDiv);
  modalBody.appendChild(consoleGroup);
  
  geminiConsole = consoleDiv;

  // Restore saved logs if any
  chrome.storage.local.get("gemini_auto_logs", (data) => {
    if (data.gemini_auto_logs && data.gemini_auto_logs.length > 0) {
      geminiLogsList = data.gemini_auto_logs;
      if (geminiConsole) {
        geminiConsole.innerHTML = "";
        geminiLogsList.forEach(logItem => {
          const color = logItem.type === "error" ? "#f43f5e" : (logItem.type === "success" ? "#10b981" : (logItem.type === "warning" ? "#f59e0b" : "#94a3b8"));
          const div = document.createElement("div");
          div.style.cssText = `color: ${color}; margin-bottom: 4px; font-size: 13px; line-height: 1.4;`;
          div.textContent = `[${logItem.time}] ${logItem.msg}`;
          geminiConsole.appendChild(div);
        });
        geminiConsole.scrollTop = geminiConsole.scrollHeight;
      }
    }
  });

  modal.appendChild(modalBody);

  // ── 4. ACTIONS FOOTER (Pinned at bottom) ──────────────────
  const actions = document.createElement("div");
  actions.style.cssText = `
    display: flex; gap: 10px; border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding: 12px 18px; background: #1e293b; flex-shrink: 0; box-sizing: border-box;
  `;
  
  const startBtn = document.createElement("button");
  startBtn.id = "gemini-start-btn";
  startBtn.textContent = "Başlat (1 Video)";
  startBtn.style.cssText = `
    background: #0284c7; color: white; border: none; padding: 10px 20px;
    border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer;
    flex-grow: 1; transition: background 0.2s;
  `;
  
  const resumeBtn = document.createElement("button");
  resumeBtn.id = "gemini-resume-btn";
  resumeBtn.textContent = "Sohbeti Sürdür";
  resumeBtn.style.cssText = `
    background: #10b981; color: white; border: none; padding: 10px 20px;
    border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer;
    flex-grow: 1; transition: background 0.2s;
  `;

  actions.appendChild(startBtn);
  actions.appendChild(resumeBtn);
  modal.appendChild(actions);

  // ── 5. TAB SWITCHING LOGIC ────────────────────────────────
  function switchGeminiTab(tabName) {
    geminiActiveTab = tabName;
    if (tabName === "single") {
      tabSingle.style.background = "#0284c7";
      tabSingle.style.color = "#ffffff";
      tabSingle.style.fontWeight = "700";
      tabQueue.style.background = "transparent";
      tabQueue.style.color = "#94a3b8";
      tabQueue.style.fontWeight = "500";
      paneSingle.style.display = "flex";
      paneQueue.style.display = "none";
      if (!geminiRunning) {
        startBtn.textContent = "Başlat (1 Video)";
        resumeBtn.style.display = "block";
      }
    } else {
      tabQueue.style.background = "#0284c7";
      tabQueue.style.color = "#ffffff";
      tabQueue.style.fontWeight = "700";
      tabSingle.style.background = "transparent";
      tabSingle.style.color = "#94a3b8";
      tabSingle.style.fontWeight = "500";
      paneSingle.style.display = "none";
      paneQueue.style.display = "flex";
      loadQueueChannelsList();
      updateQueueUI();
      if (!geminiRunning) {
        const totalVids = geminiQueue.reduce((acc, q) => acc + q.count, 0);
        startBtn.textContent = totalVids > 0 ? `Kuyruğu Başlat (${totalVids} Video)` : "Kuyruğu Başlat";
        resumeBtn.style.display = "none";
      }
    }
  }

  tabSingle.addEventListener("click", () => switchGeminiTab("single"));
  tabQueue.addEventListener("click", () => switchGeminiTab("queue"));

  // ── 6. BUTTON EVENT LISTENERS ─────────────────────────────
  startBtn.addEventListener("click", () => {
    if (geminiRunning) {
      geminiRunning = false;
      logGemini("Otomasyon kullanıcı tarafından durduruluyor...", "error");
      toggleStartButtonState(false);
      chrome.storage.local.remove([
        "gemini_auto_active",
        "gemini_auto_mode",
        "gemini_auto_queue",
        "gemini_queue_q_idx",
        "gemini_queue_v_idx",
        "gemini_queue_phase",
        "gemini_queue_row_id",
        "gemini_queue_script_data",
        "gemini_queue_custom_images",
        "gemini_queue_category",
        "gemini_queue_item",
        "gemini_queue_channel"
      ]);
    } else {
      if (geminiActiveTab === "queue") {
        const totalVideos = geminiQueue.reduce((acc, q) => acc + q.count, 0);
        if (geminiQueue.length === 0 || totalVideos === 0) {
          logGemini("Hata: Kuyrukta video üretilecek kanal bulunmuyor. Lütfen listeden kanal seçerek adedi artırın.", "error");
          return;
        }
        const useTempChat = document.querySelector('input[name="gemini-queue-chat-mode"]:checked')?.value === "temp";
        const imgProvider = document.querySelector('input[name="gemini-queue-img-provider"]:checked')?.value || "gemini";
        const envRadio = document.querySelector('input[name="gemini-queue-target-env"]:checked');
        const targetEnv = envRadio ? envRadio.value : "local";
        const autoSyncMac = !!document.getElementById("gemini-queue-auto-sync-mac")?.checked;

        toggleStartButtonState(true);
        runGeminiQueueAutomation([...geminiQueue], {
          useTempChat,
          imgProvider,
          targetEnv,
          autoSyncMac
        });
      } else {
        // Tekli Üretim: Her zaman 1 video üretilir
        const select = document.getElementById("gemini-channel-select");
        const channelId = select?.value;
        if (!channelId && !location.href.includes("perchance.org")) {
          logGemini("Hata: Herhangi bir kanal seçilmedi.", "error");
          return;
        }
        const useTempChat = document.querySelector('input[name="gemini-chat-mode"]:checked')?.value === "temp";
        const videoCount = 1; // Tekli üretimde kesin olarak 1 adet
        
        const nasaSelect = document.getElementById("gemini-nasa-option-select");
        const nasaOption = nasaSelect ? nasaSelect.value : "mixed";
        
        const imgProvider = document.querySelector('input[name="gemini-img-provider"]:checked')?.value || "gemini";
        chrome.storage.local.set({ gemini_auto_image_provider: imgProvider });

        toggleStartButtonState(true);
        if (location.href.includes("perchance.org")) {
          chrome.storage.local.get([
            "gemini_auto_channel_id",
            "gemini_auto_loop",
            "gemini_auto_videos_produced",
            "gemini_auto_custom_images",
            "gemini_auto_row_id",
            "gemini_auto_script_data"
          ], (data) => {
            const chId = channelId || data.gemini_auto_channel_id;
            runPerchanceAutomation(
              chId,
              1,
              data.gemini_auto_loop || 0,
              data.gemini_auto_videos_produced || 0,
              data.gemini_auto_custom_images || {},
              data.gemini_auto_row_id || null,
              data.gemini_auto_script_data || null
            );
          });
        } else {
          runGeminiAutomation(channelId, useTempChat, 1, nasaOption, 0, 0, null, null, null, false, imgProvider);
        }
      }
    }
  });

  resumeBtn.addEventListener("click", () => {
    if (geminiRunning) {
      geminiRunning = false;
      logGemini("Otomasyon kullanıcı tarafından durduruluyor...", "error");
      toggleStartButtonState(false);
    } else {
      const select = document.getElementById("gemini-channel-select");
      const channelId = select?.value;
      if (!channelId && !location.href.includes("perchance.org")) {
        logGemini("Hata: Herhangi bir kanal seçilmedi.", "error");
        return;
      }
      
      const nasaSelect = document.getElementById("gemini-nasa-option-select");
      const nasaOption = nasaSelect ? nasaSelect.value : "mixed";
      
      const imgProvider = document.querySelector('input[name="gemini-img-provider"]:checked')?.value || "gemini";
      chrome.storage.local.set({ gemini_auto_image_provider: imgProvider });

      toggleStartButtonState(true);
      if (location.href.includes("perchance.org")) {
        chrome.storage.local.get([
          "gemini_auto_channel_id",
          "gemini_auto_loop",
          "gemini_auto_videos_produced",
          "gemini_auto_custom_images",
          "gemini_auto_row_id",
          "gemini_auto_script_data"
        ], (data) => {
          const chId = channelId || data.gemini_auto_channel_id;
          runPerchanceAutomation(
            chId,
            1,
            data.gemini_auto_loop || 0,
            data.gemini_auto_videos_produced || 0,
            data.gemini_auto_custom_images || {},
            data.gemini_auto_row_id || null,
            data.gemini_auto_script_data || null
          );
        });
      } else {
        runGeminiAutomation(channelId, false, 1, nasaOption, 0, 0, null, null, null, true, imgProvider);
      }
    }
  });

  document.body.appendChild(modal);

  loadChannelsDropdown();
}

// ── KUYRUK LİSTELEME VE GÜNCELLEME FONKSİYONLARI ──────────────

function renderQueueChannelsList() {
  const container = document.getElementById("gemini-queue-channels-list");
  if (!container) return;

  if (!geminiChannelsList || geminiChannelsList.length === 0) {
    container.innerHTML = `<div style="color: #64748b; font-size: 12px; text-align: center; padding: 12px;">Kanal veya grup bulunamadı.</div>`;
    return;
  }

  container.innerHTML = "";
  
  geminiChannelsList.forEach(c => {
    const val = c.type === "group" ? `group:${c.id}` : c.id;
    const isGroup = c.type === "group";
    const queueIdx = geminiQueue.findIndex(q => q.id === val);
    const queueItem = queueIdx >= 0 ? geminiQueue[queueIdx] : null;
    const count = queueItem ? queueItem.count : 0;
    const hasPlan = c.has_plan !== undefined ? !!c.has_plan : true;
    const unproducedCount = c.unproduced_count !== undefined ? c.unproduced_count : 0;
    const totalPlanCount = c.total_plan_count !== undefined ? c.total_plan_count : 0;

    // Kanal sadece açıkça has_plan === false ve total_plan_count === 0 ise pasif olsun
    const isAvailable = !(c.has_plan === false && totalPlanCount <= 0);

    const card = document.createElement("div");
    card.setAttribute("data-channel-id", val);
    
    // Aktif plan ve kuyruk durumuna göre stil
    if (!isAvailable) {
      card.style.cssText = `
        display: flex; align-items: center; justify-content: space-between;
        padding: 8px 12px; border-radius: 8px;
        background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.05);
        opacity: 0.45; cursor: not-allowed; user-select: none;
      `;
    } else if (count > 0) {
      card.style.cssText = `
        display: flex; align-items: center; justify-content: space-between;
        padding: 8px 12px; border-radius: 8px;
        background: rgba(2, 132, 199, 0.12); border: 1px solid #0284c7;
        cursor: pointer; user-select: none; transition: all 0.15s ease;
      `;
    } else {
      card.style.cssText = `
        display: flex; align-items: center; justify-content: space-between;
        padding: 8px 12px; border-radius: 8px;
        background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08);
        cursor: pointer; user-select: none; transition: all 0.15s ease;
      `;
      card.addEventListener("mouseenter", () => {
        card.style.borderColor = "rgba(56, 189, 248, 0.4)";
        card.style.background = "#172033";
      });
      card.addEventListener("mouseleave", () => {
        card.style.borderColor = "rgba(255, 255, 255, 0.08)";
        card.style.background = "#0f172a";
      });
    }

    // Sol bilgi alanı
    const leftDiv = document.createElement("div");
    leftDiv.style.cssText = `display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; margin-right: 8px;`;
    
    const titleRow = document.createElement("div");
    titleRow.style.cssText = `display: flex; align-items: center; gap: 6px; flex-wrap: wrap;`;
    
    if (count > 0) {
      const orderBadge = document.createElement("span");
      orderBadge.textContent = `#${queueIdx + 1} Sırada`;
      orderBadge.style.cssText = `background: #0284c7; color: white; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px; flex-shrink: 0;`;
      titleRow.appendChild(orderBadge);
    }

    const nameSpan = document.createElement("span");
    nameSpan.textContent = c.name;
    nameSpan.style.cssText = `font-size: 12.5px; font-weight: 600; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;`;
    titleRow.appendChild(nameSpan);

    leftDiv.appendChild(titleRow);

    const badgeSpan = document.createElement("span");
    if (!isAvailable) {
      badgeSpan.textContent = `🚫 Plan Tanımlanmamış`;
      badgeSpan.style.cssText = `font-size: 10.5px; color: #64748b; font-weight: 500;`;
    } else if (unproducedCount > 0) {
      badgeSpan.textContent = `🎯 ${unproducedCount} Konu Hazır`;
      badgeSpan.style.cssText = `font-size: 10.5px; color: #10b981; font-weight: 600;`;
    } else if (totalPlanCount > 0) {
      badgeSpan.textContent = `🔄 ${totalPlanCount} Konu (Döngüde)`;
      badgeSpan.style.cssText = `font-size: 10.5px; color: #38bdf8; font-weight: 600;`;
    } else {
      badgeSpan.textContent = `⚡ Hazır`;
      badgeSpan.style.cssText = `font-size: 10.5px; color: #10b981; font-weight: 500;`;
    }
    leftDiv.appendChild(badgeSpan);
    card.appendChild(leftDiv);

    // Sağ aksiyon / sayaç alanı
    const rightDiv = document.createElement("div");
    rightDiv.style.cssText = `display: flex; align-items: center; gap: 6px; flex-shrink: 0;`;

    if (!isAvailable) {
      const lockSpan = document.createElement("span");
      lockSpan.textContent = "Pasif";
      lockSpan.style.cssText = `font-size: 10.5px; color: #64748b; background: rgba(100, 116, 139, 0.15); padding: 3px 8px; border-radius: 6px; font-weight: 600;`;
      rightDiv.appendChild(lockSpan);
    } else if (count > 0) {
      // Eksiltme butonu (-)
      const minusBtn = document.createElement("button");
      minusBtn.textContent = "−";
      minusBtn.style.cssText = `
        width: 24px; height: 24px; border-radius: 6px; border: 1px solid #475569;
        background: #1e293b; color: #f8fafc; font-size: 14px; font-weight: bold;
        display: flex; align-items: center; justify-content: center; cursor: pointer;
        transition: all 0.15s;
      `;
      minusBtn.addEventListener("mouseenter", () => minusBtn.style.background = "#ef4444");
      minusBtn.addEventListener("mouseleave", () => minusBtn.style.background = "#1e293b");
      minusBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (queueItem) {
          queueItem.count--;
          if (queueItem.count <= 0) {
            geminiQueue = geminiQueue.filter(q => q.id !== val);
          }
        }
        updateQueueUI();
      });
      rightDiv.appendChild(minusBtn);

      // Adet yazısı
      const countBadge = document.createElement("span");
      countBadge.textContent = `${count} Adet`;
      countBadge.style.cssText = `
        font-size: 12px; font-weight: 700; color: #38bdf8; min-width: 44px; text-align: center;
      `;
      rightDiv.appendChild(countBadge);

      // Artırma butonu (+)
      const plusBtn = document.createElement("button");
      plusBtn.textContent = "+";
      plusBtn.style.cssText = `
        width: 24px; height: 24px; border-radius: 6px; border: 1px solid #0284c7;
        background: #0284c7; color: white; font-size: 14px; font-weight: bold;
        display: flex; align-items: center; justify-content: center; cursor: pointer;
        transition: all 0.15s;
      `;
      plusBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (queueItem) {
          queueItem.count++;
        }
        updateQueueUI();
      });
      rightDiv.appendChild(plusBtn);

    } else {
      // Ekle butonu
      const addBtn = document.createElement("span");
      addBtn.textContent = "+ Ekle";
      addBtn.style.cssText = `
        font-size: 11px; font-weight: 600; color: #38bdf8; background: rgba(56, 189, 248, 0.12);
        padding: 4px 8px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.3);
      `;
      rightDiv.appendChild(addBtn);
    }

    card.appendChild(rightDiv);

    // Karta tıklayınca ekleme / artırma (İlk tıklanan ilk sırada kalır!)
    if (isAvailable) {
      card.addEventListener("click", () => {
        if (queueItem) {
          queueItem.count++;
        } else {
          geminiQueue.push({
            id: val,
            type: c.type,
            name: c.name,
            raw_name: c.raw_name,
            topic_category: c.topic_category,
            count: 1,
            unproduced_count: unproducedCount,
            total_plan_count: totalPlanCount,
            shorts_mode: c.shorts_mode
          });
        }
        updateQueueUI();
      });
    }

    container.appendChild(card);
  });
}

function updateQueueUI() {
  const totalVideos = geminiQueue.reduce((acc, q) => acc + q.count, 0);
  
  // Tab başlığındaki rozet
  const queueBadge = document.getElementById("gemini-queue-badge");
  if (queueBadge) {
    queueBadge.textContent = totalVideos.toString();
  }

  // Sıra önizleme alanı
  const previewDiv = document.getElementById("gemini-queue-order-preview");
  if (previewDiv) {
    if (geminiQueue.length === 0) {
      previewDiv.innerHTML = `<span style="color: #64748b;">Kuyruk boş. Yukarıdaki kanallara tıklayarak ekleyin.</span>`;
    } else {
      let html = `<div style="display: flex; flex-direction: column; gap: 4px;">`;
      html += `<div style="font-size: 11px; font-weight: 600; color: #38bdf8;">Çalışma Sırası (${totalVideos} Video):</div>`;
      html += `<div style="display: flex; flex-wrap: wrap; gap: 6px;">`;
      geminiQueue.forEach((q, idx) => {
        html += `<span style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155; padding: 3px 8px; border-radius: 6px; font-size: 11.5px; color: #cbd5e1; display: flex; align-items: center; gap: 4px;">
          <strong style="color: #38bdf8;">#${idx + 1}</strong> ${q.raw_name || q.name}: <strong style="color: #10b981;">${q.count} video</strong>
        </span>`;
      });
      html += `</div></div>`;
      previewDiv.innerHTML = html;
    }
  }

  // Başlat butonundaki metin
  if (geminiActiveTab === "queue" && !geminiRunning) {
    const startBtn = document.getElementById("gemini-start-btn");
    if (startBtn) {
      startBtn.textContent = totalVideos > 0 ? `Kuyruğu Başlat (${totalVideos} Video)` : "Kuyruğu Başlat";
    }
  }

  renderQueueChannelsList();
}

async function loadQueueChannelsList() {
  const container = document.getElementById("gemini-queue-channels-list");
  if (!container) return;

  try {
    const apiUrl = await getApiUrl();
    const res = await fetchFromBackground(`${apiUrl}/api/channels-and-groups`);
    if (res && res.ok) {
      geminiChannelsList = (typeof res.json === 'function' ? await res.json() : res.data) || [];
    }
  } catch(e) {
    console.warn("[YT-OTO] Kuyruk kanalları yükleme uyarısı:", e);
  }

  renderQueueChannelsList();
}

function toggleStartButtonState(running) {
  const startBtn = document.getElementById("gemini-start-btn");
  const resumeBtn = document.getElementById("gemini-resume-btn");
  if (startBtn) {
    if (running) {
      startBtn.textContent = "Durdur";
      startBtn.style.background = "#ef4444";
      if (resumeBtn) {
        resumeBtn.disabled = true;
        resumeBtn.style.opacity = "0.5";
        resumeBtn.style.cursor = "not-allowed";
      }
    } else {
      startBtn.style.background = "#0284c7";
      if (geminiActiveTab === "queue") {
        const totalVids = geminiQueue.reduce((acc, q) => acc + q.count, 0);
        startBtn.textContent = totalVids > 0 ? `Kuyruğu Başlat (${totalVids} Video)` : "Kuyruğu Başlat";
        if (resumeBtn) {
          resumeBtn.style.display = "none";
        }
      } else {
        startBtn.textContent = "Başlat (1 Video)";
        if (resumeBtn) {
          resumeBtn.style.display = "block";
          resumeBtn.disabled = false;
          resumeBtn.style.opacity = "1";
          resumeBtn.style.cursor = "pointer";
        }
      }
    }
  }
}

async function loadChannelsDropdown() {
  const select = document.getElementById("gemini-channel-select");
  if (!select) return;
  
  select.innerHTML = "<option value=''>Kanallar yükleniyor...</option>";
  
  try {
    const apiUrl = await getApiUrl();
    const res = await fetchFromBackground(`${apiUrl}/api/channels-and-groups`);
    if (res.ok) {
      geminiChannelsList = (typeof res.json === 'function') ? await res.json() : (res.data || []);
      if (geminiChannelsList && geminiChannelsList.length > 0) {
        const storageData = await new Promise(r => chrome.storage.local.get(["gemini_auto_channel_id", "last_selected_channel"], r));
        const preferredId = storageData.gemini_auto_channel_id || storageData.last_selected_channel;

        select.innerHTML = geminiChannelsList.map(c => {
          const val = c.type === "group" ? `group:${c.id}` : c.id;
          return `<option value="${val}">${c.name}</option>`;
        }).join("");
        
        const firstVal = geminiChannelsList[0].type === "group" ? `group:${geminiChannelsList[0].id}` : geminiChannelsList[0].id;
        if (preferredId && geminiChannelsList.some(c => (c.type === "group" ? `group:${c.id}` : c.id) === preferredId)) {
          select.value = preferredId;
        } else if (geminiChannelsList.length > 0) {
          select.value = firstVal;
        }
        
        select.dispatchEvent(new Event("change"));
        renderQueueChannelsList();
      } else {
        select.innerHTML = "<option value=''>Kanal veya grup bulunamadı.</option>";
      }
    } else {
      select.innerHTML = "<option value=''>Kanallar yüklenemedi (HTTP Hata).</option>";
    }
  } catch (err) {
    select.innerHTML = "<option value=''>Bağlantı hatası.</option>";
  }
}

async function loadIncompleteVideos(channelId) {
  const select = document.getElementById("gemini-incomplete-select");
  if (!select) return;
  
  select.innerHTML = "<option value=''>Yükleniyor...</option>";
  
  try {
    const apiUrl = await getApiUrl();
    const isGroup = channelId.startsWith("group:");
    const targetId = isGroup ? channelId.replace("group:", "") : channelId;
    const planUrl = isGroup ? `${apiUrl}/api/groups/${targetId}/plan` : `${apiUrl}/api/channels/${targetId}/plan`;
    const res = await fetchFromBackground(planUrl);
    if (res.ok && res.data) {
      const planData = res.data;
      if (planData.success && planData.plan) {
        const incompleteRows = planData.plan.filter(row => row.recompose_available);
        if (incompleteRows.length > 0) {
          let html = `<option value="">-- Sıradaki Üretilmemiş Konu --</option>`;
          incompleteRows.forEach(row => {
            html += `<option value="${row.id}">ID: ${row.id} - ${row.baslik || row.konu}</option>`;
          });
          select.innerHTML = html;
        } else {
          select.innerHTML = "<option value=''>Yarım kalan video bulunamadı.</option>";
        }
      } else {
        select.innerHTML = "<option value=''>Plan alınamadı.</option>";
      }
    } else {
      select.innerHTML = "<option value=''>Hata oluştu.</option>";
    }
  } catch (err) {
    select.innerHTML = "<option value=''>Bağlantı hatası.</option>";
  }
}

function injectGeminiFAB() {
  if (document.getElementById("gemini-oto-fab")) return;

  const fab = document.createElement("div");
  fab.id = "gemini-oto-fab";
  fab.style.cssText = `
    position: fixed; bottom: 24px; right: 24px; z-index: 999999;
    background: #0f172a; border: 1px solid rgba(56, 189, 248, 0.35);
    color: #f8fafc; width: 44px; height: 44px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; font-size: 20px; font-weight: bold;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05);
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    overflow: hidden; white-space: nowrap;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;
  
  const text = document.createElement("span");
  text.style.cssText = `
    opacity: 0; width: 0; display: inline-block; font-size: 13px;
    font-weight: 600; margin-left: 0; transition: all 0.2s ease; color: #f8fafc;
  `;
  text.textContent = "Gemini Asistanı";

  const icon = document.createElement("span");
  icon.textContent = "⚡";
  
  fab.appendChild(icon);
  fab.appendChild(text);
  document.body.appendChild(fab);

  fab.addEventListener("mouseenter", () => {
    fab.style.width = "156px";
    fab.style.borderRadius = "22px";
    fab.style.borderColor = "#38bdf8";
    fab.style.background = "#1e293b";
    fab.style.boxShadow = "0 8px 28px rgba(2, 132, 199, 0.35)";
    text.style.opacity = "1";
    text.style.width = "auto";
    text.style.marginLeft = "8px";
  });
  fab.addEventListener("mouseleave", () => {
    fab.style.width = "44px";
    fab.style.borderRadius = "50%";
    fab.style.borderColor = "rgba(56, 189, 248, 0.35)";
    fab.style.background = "#0f172a";
    fab.style.boxShadow = "0 8px 24px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05)";
    text.style.opacity = "0";
    text.style.width = "0";
    text.style.marginLeft = "0";
  });

  fab.addEventListener("click", openGeminiModal);
}

if (location.href.includes("gemini.google.com") || location.href.includes("perchance.org")) {
  const tryInject = () => {
    if (window === window.top) {
      injectGeminiFAB();
      if (location.href.includes("gemini.google.com")) {
        injectGeminiPlanFAB();
        injectGeminiVideoQAFAB();
      }
    }
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryInject);
  } else {
    tryInject();
  }
  setInterval(tryInject, 1000);
}


// ── Video Analiz Özelliği (Mükerrer Konu Tespiti) ─────────────────

function cleanTitle(title) {
  if (!title) return "";
  return title
    .toLowerCase()
    .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"']/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function getOverlapSimilarity(title1, title2) {
  const t1 = cleanTitle(title1);
  const t2 = cleanTitle(title2);
  if (!t1 || !t2) return 0;
  if (t1 === t2) return 1.0; // Birebir aynı

  const words1 = t1.split(" ").filter(w => w.length > 2);
  const words2 = t2.split(" ").filter(w => w.length > 2);
  if (words1.length === 0 || words2.length === 0) return 0;
  
  const set1 = new Set(words1);
  const set2 = new Set(words2);
  
  let intersection = 0;
  for (const w of set1) {
    if (set2.has(w)) intersection++;
  }
  
  return intersection / Math.min(set1.size, set2.size);
}

function getVideoTitleFromRow(row) {
  if (!row) return "";
  const titleEl = queryShadow('#video-title', row) || 
                  queryShadow('#title-text', row) || 
                  queryShadow('#video-title-link', row) ||
                  queryShadow('.video-title', row) ||
                  queryShadow('[id*="title"]', row);
  if (titleEl) {
    return titleEl.textContent.trim();
  }
  return "";
}

function resolveActiveChannelName() {
  if (location.href.includes("instagram.com")) {
    const igUser = getActiveInstagramProfile();
    if (igUser) return igUser;
  }
  const name1 = getActiveChannelName();
  if (name1) return name1;
  const name2 = getActiveChannelNameFromDOM();
  if (name2) return name2;
  return null;
}

function getStudioActiveCategory() {
  if (location.href.includes("/shorts")) return "shorts";
  
  // DOM check fallback
  const shortsHeader = queryShadow('#short-header-name') || queryShadow('[aria-label="Shorts videosu"]');
  if (shortsHeader) return "shorts";
  
  return "uploads";
}

async function checkUploadConflict(video) {
  const videoCategory = video.shorts_mode ? "shorts" : "uploads";
  const studioCategory = getStudioActiveCategory();

  const isInstagram = location.href.includes("instagram.com");
  const isYouTube = location.href.includes("studio.youtube.com") || location.href.includes("youtube.com");
  const isTikTok = location.href.includes("tiktok.com");

  // 1. DOM'daki yüklü videoları tara (sadece aktif sekme yüklenecek video tipi ile eşleşiyorsa)
  const domVideos = [];
  if (videoCategory === studioCategory) {
    const rows = document.querySelectorAll('ytcp-video-row');
    rows.forEach((row) => {
      const title = getVideoTitleFromRow(row);
      if (title) {
        domVideos.push({
          title: title,
          source: "Studio'da Yüklü"
        });
      }
    });
  }

  // 2. Local backend veritabanını tara
  const backendVideos = [];
  const activeChannelName = resolveActiveChannelName();
  try {
    const responseData = await fetchFromBackground("http://127.0.0.1:8000/api/output");
    const videos = responseData.data || [];
    
    videos.forEach(v => {
      if (v.archived) return;
      
      // 1. Aynı olay/video grubuna ait olanları hariç tut (örn: uzun video ve onun alt shorts'ları veya isimlendirme benzerlikleri)
      const vBaseFolder = (v.folder || "").split('/shorts_')[0].replace(/_shorts$/, "");
      const videoBaseFolder = (video.folder || "").split('/shorts_')[0].replace(/_shorts$/, "");
      if (vBaseFolder === videoBaseFolder) return;

      // 2. Sadece aktif platformda gerçekten yüklenmiş videoları çakışma olarak kabul et
      if (isYouTube && !v.uploaded_youtube) return;
      if (isInstagram && !v.uploaded_instagram) return;
      if (isTikTok && !v.uploaded_tiktok) return;
      
      // Kanal adını eşleştir
      if (activeChannelName) {
        const targetName = activeChannelName.trim().toLowerCase();
        
        // Klasör isminin (ilk bölümünün) kanal ismi ile eşleştiğini doğrula
        const folderParts = (v.folder || "").split("/");
        const folderChanId = folderParts[0] ? folderParts[0].trim().toLowerCase() : "";
        
        const vChanName = (v.channel_name || "").trim().toLowerCase();
        const vChanId = (v.channel_id || "").trim().toLowerCase();
        
        const matchesPrefix = (folderChanId === targetName || targetName.includes(folderChanId) || folderChanId.includes(targetName));
        const matchesMetaName = (vChanName === targetName || targetName.includes(vChanName) || vChanName.includes(targetName));
        const matchesMetaId = (vChanId === targetName || targetName.includes(vChanId) || vChanId.includes(targetName));
        
        if (!matchesPrefix && !matchesMetaName && !matchesMetaId) return;
      }

      // Kategoriye göre filtrele (Shorts vs Normal)
      const targetIsShorts = !!video.shorts_mode;
      const vIsShorts = !!v.shorts_mode;
      if (vIsShorts !== targetIsShorts) return;
      
      backendVideos.push({
        title: v.title,
        source: "Sistem Veritabanı"
      });
    });
  } catch (e) {
    console.warn("[YT-OTO] Backend videoları karşılaştırma için alınamadı:", e);
  }

  // Videoları birleştir (DOM + veritabanı)
  const allVideos = [...domVideos];
  backendVideos.forEach(bv => {
    const alreadyInDom = domVideos.some(dv => cleanTitle(dv.title) === cleanTitle(bv.title));
    if (!alreadyInDom) {
      allVideos.push(bv);
    }
  });

  // Çakışanları bul (benzerlik >= 80% olanlar)
  const conflicts = [];
  allVideos.forEach(item => {
    const sim = getOverlapSimilarity(video.title, item.title);
    if (sim >= 0.8) {
      conflicts.push(item);
    }
  });

  return conflicts;
}

function showConflictWarningModal(video, conflicts, onConfirm) {
  const existing = document.getElementById("yt-oto-conflict-modal");
  if (existing) existing.remove();

  const modal = document.createElement("div");
  modal.id = "yt-oto-conflict-modal";
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px);
    z-index: 10000005; display: flex; align-items: center; justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  const container = document.createElement("div");
  container.style.cssText = `
    background: #1e293b; border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 16px; width: 560px; max-width: 90%; padding: 28px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.6);
    color: #f8fafc; display: flex; flex-direction: column; gap: 20px;
  `;

  const header = document.createElement("div");
  header.style.cssText = `display: flex; align-items: center; gap: 12px;`;
  
  const icon = document.createElement("div");
  icon.style.cssText = `font-size: 32px;`;
  icon.textContent = "⚠️";
  
  const title = document.createElement("h3");
  title.style.cssText = `margin: 0; font-size: 18px; font-weight: 700; color: #fbbf24;`;
  title.textContent = "Mükerrer İçerik Uyarısı";

  header.appendChild(icon);
  header.appendChild(title);
  container.appendChild(header);

  const body = document.createElement("div");
  body.style.cssText = `font-size: 13.5px; color: #cbd5e1; line-height: 1.5; display: flex; flex-direction: column; gap: 14px;`;
  
  const desc = document.createElement("div");
  desc.innerHTML = `Yüklemek üzere olduğunuz video ile <strong>aynı veya benzer konuya sahip</strong> başka videolar tespit edildi:`;
  body.appendChild(desc);

  const targetBox = document.createElement("div");
  targetBox.style.cssText = `
    background: rgba(255, 255, 255, 0.04); border-radius: 8px; padding: 12px;
    font-size: 13px; border-left: 4px solid #38bdf8;
  `;
  targetBox.innerHTML = `<span style="color: #38bdf8; font-weight: 600;">Yüklenecek:</span><br>${video.shorts_mode ? "📱 " : "🎬 "}${video.title}`;
  body.appendChild(targetBox);

  const conflictList = document.createElement("div");
  conflictList.style.cssText = `display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto;`;
  
  conflicts.forEach(c => {
    const item = document.createElement("div");
    item.style.cssText = `
      background: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.15);
      border-radius: 6px; padding: 8px 12px; font-size: 12.5px; display: flex; justify-content: space-between; align-items: center;
    `;
    item.innerHTML = `
      <span style="color: #f1f5f9; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 75%;">${c.title}</span>
      <span style="font-size: 11px; color: #94a3b8; background: rgba(255, 255, 255, 0.05); padding: 2px 6px; border-radius: 4px;">${c.source}</span>
    `;
    conflictList.appendChild(item);
  });
  body.appendChild(conflictList);

  const question = document.createElement("div");
  question.style.cssText = `font-weight: 600; color: #fbbf24; margin-top: 6px;`;
  question.textContent = "Bu videoyu yine de yüklemek istiyor musunuz?";
  body.appendChild(question);

  container.appendChild(body);

  const footer = document.createElement("div");
  footer.style.cssText = `display: flex; justify-content: flex-end; gap: 12px; margin-top: 10px;`;

  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "İptal Et";
  cancelBtn.style.cssText = `
    background: #475569; color: #f8fafc; border: none; border-radius: 8px;
    padding: 10px 20px; font-size: 13.5px; font-weight: 600; cursor: pointer;
    transition: background 0.2s;
  `;
  cancelBtn.addEventListener("mouseenter", () => cancelBtn.style.background = "#334155");
  cancelBtn.addEventListener("mouseleave", () => cancelBtn.style.background = "#475569");
  cancelBtn.addEventListener("click", () => modal.remove());

  const confirmBtn = document.createElement("button");
  confirmBtn.textContent = "Yine de Yükle";
  confirmBtn.style.cssText = `
    background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: none; border-radius: 8px;
    padding: 10px 20px; font-size: 13.5px; font-weight: 600; cursor: pointer;
    transition: all 0.2s ease; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
  `;
  confirmBtn.addEventListener("mouseenter", () => {
    confirmBtn.style.transform = "translateY(-1px)";
    confirmBtn.style.boxShadow = "0 6px 16px rgba(245, 158, 11, 0.45)";
  });
  confirmBtn.addEventListener("mouseleave", () => {
    confirmBtn.style.transform = "none";
    confirmBtn.style.boxShadow = "0 4px 12px rgba(245, 158, 11, 0.3)";
  });
  
  confirmBtn.addEventListener("click", () => {
    modal.remove();
    onConfirm();
  });

  footer.appendChild(cancelBtn);
  footer.appendChild(confirmBtn);
  container.appendChild(footer);
  modal.appendChild(container);
  document.body.appendChild(modal);
}


// ── YouTube.com Esinlenme ve İlham Al Enjektörü ──────────────────────
if (location.href.includes("youtube.com") && !location.href.includes("studio.youtube.com")) {
  initYouTubeInspirationInjector();
}

function initYouTubeInspirationInjector() {
  console.log("[YT-OTO] YouTube.com İlham Al enjektörü başlatıldı.");
  setInterval(() => {
    injectInspirationButtons();
  }, 2500);
}

function injectInspirationButtons() {
  const videoCards = document.querySelectorAll(
    'ytd-rich-grid-media, ytd-grid-video-renderer, ytd-video-renderer, ytd-compact-video-renderer'
  );
  
  videoCards.forEach(card => {
    if (card.querySelector('.yt-oto-inspiration-btn')) return;
    
    const titleEl = card.querySelector('#video-title-link') || 
                    card.querySelector('#video-title') ||
                    card.querySelector('h3 a');
                    
    if (!titleEl) return;
    
    const videoTitle = titleEl.textContent.trim();
    let videoUrl = "";
    if (titleEl.tagName === 'A' && titleEl.href) {
      videoUrl = titleEl.href;
    } else {
      const a = card.querySelector('a[href*="/watch"]');
      if (a) videoUrl = a.href;
    }
    
    if (!videoTitle) return;
    
    const dismissible = card.querySelector('#dismissible') || card;
    const metadataContainer = dismissible.querySelector('#metadata-line') || 
                               dismissible.querySelector('#metadata') ||
                               dismissible;
                               
    if (!metadataContainer) return;
    
    const btn = document.createElement('button');
    btn.className = 'yt-oto-inspiration-btn';
    btn.innerHTML = '💡 İlham Al';
    btn.style.cssText = `
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: #38bdf8;
      font-size: 11px;
      font-weight: 600;
      border-radius: 4px;
      padding: 3px 8px;
      margin-top: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.2s ease;
      font-family: inherit;
    `;
    
    btn.addEventListener('mouseenter', () => {
      btn.style.background = 'rgba(56, 189, 248, 0.3)';
      btn.style.borderColor = 'rgba(56, 189, 248, 0.5)';
      btn.style.transform = 'translateY(-0.5px)';
    });
    
    btn.addEventListener('mouseleave', () => {
      btn.style.background = 'rgba(56, 189, 248, 0.15)';
      btn.style.borderColor = 'rgba(56, 189, 248, 0.3)';
      btn.style.transform = 'none';
    });
    
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      openInspirationModal(videoTitle, videoUrl);
    });
    
    metadataContainer.appendChild(btn);
  });
}

async function openInspirationModal(videoTitle, videoUrl) {
  let channels = [];
  try {
    const res = await fetch('http://127.0.0.1:8000/api/channels');
    channels = await res.json();
  } catch (err) {
    console.error("[YT-OTO] Kanallar yüklenemedi:", err);
  }
  
  if (!channels || channels.length === 0) {
    alert("Hata: Arka plan API sunucusu çalışmıyor veya kayıtlı kanal bulunamadı.");
    return;
  }
  
  const modal = document.createElement("div");
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(8px);
    display: flex; align-items: center; justify-content: center; z-index: 999999;
    font-family: system-ui, -apple-system, sans-serif; color: #f8fafc;
  `;
  
  const container = document.createElement("div");
  container.style.cssText = `
    background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08);
    width: 100%; max-width: 440px; border-radius: 12px; padding: 24px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column; gap: 16px;
  `;
  
  const header = document.createElement("div");
  header.style.cssText = `display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px;`;
  
  const title = document.createElement("h3");
  title.textContent = "💡 İlham Al (Özgün İçerik Üret)";
  title.style.cssText = "margin: 0; font-size: 16px; font-weight: 700; color: #38bdf8;";
  header.appendChild(title);
  
  const closeBtn = document.createElement("button");
  closeBtn.innerHTML = "&times;";
  closeBtn.style.cssText = "background: none; border: none; font-size: 20px; color: #94a3b8; cursor: pointer; padding: 0 4px;";
  closeBtn.addEventListener("click", () => modal.remove());
  header.appendChild(closeBtn);
  
  header.appendChild(title);
  header.appendChild(closeBtn);
  container.appendChild(header);
  
  const sourceInfo = document.createElement("div");
  sourceInfo.style.cssText = "background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 12px; border-radius: 8px;";
  sourceInfo.innerHTML = `
    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 4px;">Esinlenilen Video:</div>
    <div style="font-size: 13px; font-weight: 600; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${videoTitle}</div>
  `;
  container.appendChild(sourceInfo);
  
  const formGroup = document.createElement("div");
  formGroup.style.cssText = "display: flex; flex-direction: column; gap: 8px;";
  
  const label = document.createElement("label");
  label.textContent = "Hedef Kanal Seçin:";
  label.style.cssText = "font-size: 12px; font-weight: 600; color: #94a3b8;";
  formGroup.appendChild(label);
  
  const select = document.createElement("select");
  select.style.cssText = `
    background: #1e293b; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px;
    padding: 8px 12px; color: #f8fafc; font-size: 13px; outline: none; cursor: pointer;
  `;
  channels.forEach(ch => {
    const opt = document.createElement("option");
    opt.value = ch.channel_id;
    opt.textContent = ch.name;
    select.appendChild(opt);
  });
  formGroup.appendChild(select);
  container.appendChild(formGroup);
  
  const statusDiv = document.createElement("div");
  statusDiv.style.cssText = "font-size: 12px; min-height: 18px; color: #94a3b8;";
  container.appendChild(statusDiv);
  
  const footer = document.createElement("div");
  footer.style.cssText = "display: flex; gap: 12px; justify-content: flex-end; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 16px;";
  
  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "İptal";
  cancelBtn.style.cssText = "background: #334155; border: none; border-radius: 6px; padding: 8px 16px; color: white; font-size: 13px; font-weight: 600; cursor: pointer;";
  cancelBtn.addEventListener("click", () => modal.remove());
  
  const submitBtn = document.createElement("button");
  submitBtn.textContent = "Özgün İçerik Üret";
  submitBtn.style.cssText = "background: #38bdf8; border: none; border-radius: 6px; padding: 8px 16px; color: #0f172a; font-size: 13px; font-weight: 600; cursor: pointer;";
  
  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    cancelBtn.disabled = true;
    select.disabled = true;
    submitBtn.textContent = "Üretiliyor...";
    statusDiv.style.color = "#38bdf8";
    statusDiv.textContent = "⏳ Yapay zeka ile özgün konu tasarlanıyor...";
    
    try {
      const res = await fetch('http://127.0.0.1:8000/api/inspiration/generate', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel_id: select.value,
          source_title: videoTitle,
          source_url: videoUrl
        })
      });
      
      const data = await res.json();
      if (data.success) {
        statusDiv.style.color = "#10b981";
        statusDiv.innerHTML = `✅ <strong>Başarılı!</strong> Özgün içerik planlayıcıya eklendi:<br><span style="color: #f8fafc">${data.topic.baslik}</span>`;
        setTimeout(() => modal.remove(), 4000);
      } else {
        throw new Error(data.detail || "Üretim sırasında hata oluştu.");
      }
    } catch (err) {
      submitBtn.disabled = false;
      cancelBtn.disabled = false;
      select.disabled = false;
      submitBtn.textContent = "Özgün İçerik Üret";
      statusDiv.style.color = "#f87171";
      statusDiv.textContent = "❌ Hata: " + err.message;
    }
  });
  
  footer.appendChild(cancelBtn);
  footer.appendChild(submitBtn);
  container.appendChild(footer);
  modal.appendChild(container);
  
  document.body.appendChild(modal);
}


// ── YouTube Studio Geçmişi Analiz Et Özelliği ───────────────────────

function updateAnalyzeButtonVisibility() {
  const isContentPage = location.href.includes('/videos') || location.href.includes('/content');
  const btn = document.getElementById('yt-oto-analyze-history-btn');
  
  if (isContentPage) {
    if (!btn) {
      injectAnalyzeButton();
    } else {
      btn.style.display = 'inline-flex';
    }
  } else {
    if (btn) {
      btn.style.display = 'none';
    }
  }
}

function injectAnalyzeButton() {
  if (document.getElementById('yt-oto-analyze-history-btn')) return;
  
  const studioLogo = queryShadow('ytcp-home-button') || queryShadow('#home-button') || document.querySelector('ytcp-home-button');
  if (!studioLogo) return;
  
  const btn = document.createElement('button');
  btn.id = 'yt-oto-analyze-history-btn';
  btn.innerHTML = '📊 Geçmişi Analiz Et';
  btn.style.cssText = `
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
    border: none;
    border-radius: 20px;
    padding: 6px 14px;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    margin-left: 16px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s ease;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
    align-self: center;
    z-index: 999;
  `;
  
  btn.addEventListener('mouseenter', () => {
    btn.style.transform = 'translateY(-0.5px)';
    btn.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.45)';
  });
  
  btn.addEventListener('mouseleave', () => {
    btn.style.transform = 'none';
    btn.style.boxShadow = '0 2px 8px rgba(16, 185, 129, 0.3)';
  });
  
  btn.addEventListener('click', () => {
    runHistoryAnalysis(btn);
  });
  
  if (studioLogo.parentNode) {
    studioLogo.parentNode.insertBefore(btn, studioLogo.nextSibling);
  }
}

async function runHistoryAnalysis(btn) {
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '🔄 Analiz Ediliyor...';
  btn.style.opacity = '0.7';
  
  try {
    const rows = document.querySelectorAll('ytcp-video-row');
    if (rows.length === 0) {
      alert("Hata: YouTube Studio tablosunda yüklü video bulunamadı. Lütfen videoların yüklenmesini bekleyin.");
      btn.disabled = false;
      btn.innerHTML = originalText;
      btn.style.opacity = '1';
      return;
    }
    
    const scrapedVideos = [];
    rows.forEach(row => {
      const titleEl = queryShadow('#video-title', row) || queryShadow('.video-title', row);
      const visibilityEl = queryShadow('.tablecell-visibility', row);
      const viewsEl = queryShadow('.tablecell-views', row);
      const dateEl = queryShadow('.tablecell-date', row);
      
      if (titleEl && visibilityEl && viewsEl) {
        const title = titleEl.textContent.trim();
        const visibility = visibilityEl.textContent.trim();
        const viewsText = viewsEl.textContent.trim();
        const dateText = dateEl ? dateEl.textContent.trim() : "";
        
        const isPublic = visibility.toLowerCase().includes('herkese açık') || 
                         visibility.toLowerCase().includes('public') || 
                         visibility.toLowerCase().includes('açık') ||
                         visibility.toLowerCase().includes('planlandı') ||
                         visibility.toLowerCase().includes('scheduled');
                         
        if (isPublic) {
          let views = 0;
          const cleanViews = viewsText.replace(/\./g, '').replace(/,/g, '').trim();
          if (cleanViews.toLowerCase().includes('b') || cleanViews.toLowerCase().includes('k')) {
            views = parseFloat(cleanViews) * 1000;
          } else if (cleanViews.toLowerCase().includes('m')) {
            views = parseFloat(cleanViews) * 1000000;
          } else {
            views = parseInt(cleanViews) || 0;
          }
          
          scrapedVideos.push({
            title: title,
            views: views,
            viewsText: viewsText,
            dateText: dateText,
            visibility: visibility
          });
        }
      }
    });
    
    if (scrapedVideos.length === 0) {
      alert("Hata: Görünürlüğü 'Herkese Açık' veya 'Planlandı' olan video bulunamadı.");
      btn.disabled = false;
      btn.innerHTML = originalText;
      btn.style.opacity = '1';
      return;
    }
    
    const activeChannelName = resolveActiveChannelName();
    if (!activeChannelName) {
      alert("Hata: Aktif kanal adı tespit edilemedi.");
      btn.disabled = false;
      btn.innerHTML = originalText;
      btn.style.opacity = '1';
      return;
    }
    
    const channelsRes = await fetchFromBackground('http://127.0.0.1:8000/api/channels');
    const channels = await channelsRes.json();
    
    const cleanStr = (s) => s ? s.toLowerCase().replace(/[^a-z0-9]/g, "") : "";
    const cleanActive = cleanStr(activeChannelName);
    
    let matchedChannel = channels.find(c => {
      const cleanChName = cleanStr(c.name);
      return cleanChName === cleanActive || cleanActive.includes(cleanChName) || cleanChName.includes(cleanActive);
    });
    
    if (!matchedChannel) {
      matchedChannel = channels[0];
      if (!matchedChannel) {
        alert("Hata: Sistemde kayıtlı kanal bulunamadı.");
        btn.disabled = false;
        btn.innerHTML = originalText;
        btn.style.opacity = '1';
        return;
      }
    }
    
    const channelId = matchedChannel.channel_id;
    
    const analyzeRes = await fetchFromBackground(`http://127.0.0.1:8000/api/channels/${channelId}/analyze-history`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ videos: scrapedVideos })
    });
    
    const result = await analyzeRes.json();
    if (result.success) {
      showAnalysisReportModal(result.analysis, activeChannelName);
    } else {
      alert("Analiz başarısız: " + (result.detail || result.error || "Bilinmeyen hata"));
    }
    
  } catch (err) {
    console.error("Geçmiş analizi sırasında hata:", err);
    alert("Hata: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
    btn.style.opacity = '1';
  }
}

function showAnalysisReportModal(analysisReportText, channelName) {
  const existing = document.getElementById("yt-oto-analysis-report-modal");
  if (existing) existing.remove();
  
  const modal = document.createElement("div");
  modal.id = "yt-oto-analysis-report-modal";
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(8px);
    display: flex; align-items: center; justify-content: center; z-index: 999999;
    font-family: system-ui, -apple-system, sans-serif; color: #f8fafc;
  `;
  
  const container = document.createElement("div");
  container.style.cssText = `
    background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08);
    width: 100%; max-width: 550px; border-radius: 12px; padding: 24px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column; gap: 16px;
  `;
  
  const header = document.createElement("div");
  header.style.cssText = `display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px;`;
  
  const title = document.createElement("h3");
  title.textContent = `📊 ${channelName} - Performans Analiz Raporu`;
  title.style.cssText = "margin: 0; font-size: 16px; font-weight: 700; color: #10b981;";
  header.appendChild(title);
  
  const closeBtn = document.createElement("button");
  closeBtn.innerHTML = "&times;";
  closeBtn.style.cssText = "background: none; border: none; font-size: 20px; color: #94a3b8; cursor: pointer; padding: 0 4px;";
  closeBtn.addEventListener("click", () => modal.remove());
  header.appendChild(closeBtn);
  
  container.appendChild(header);
  
  const textContainer = document.createElement("div");
  textContainer.style.cssText = "font-size: 13px; line-height: 1.6; color: #e2e8f0; max-height: 350px; overflow-y: auto; white-space: pre-wrap; background: rgba(255,255,255,0.02); padding: 16px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);";
  textContainer.textContent = analysisReportText;
  container.appendChild(textContainer);
  
  const noticeDiv = document.createElement("div");
  noticeDiv.style.cssText = "font-size: 11px; color: #10b981; font-weight: 600; display: flex; align-items: center; gap: 6px;";
  noticeDiv.innerHTML = "💡 Zihin haritanız, yüksek performans gösteren konuları önceliklendirecek şekilde AI tarafından başarıyla güncellendi!";
  container.appendChild(noticeDiv);
  
  const footer = document.createElement("div");
  footer.style.cssText = "display: flex; justify-content: flex-end; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 16px;";
  
  const confirmBtn = document.createElement("button");
  confirmBtn.textContent = "Kapat ve Uygula";
  confirmBtn.style.cssText = "background: #10b981; border: none; border-radius: 6px; padding: 8px 16px; color: #0f172a; font-size: 13px; font-weight: 600; cursor: pointer;";
  confirmBtn.addEventListener("click", () => modal.remove());
  
  footer.appendChild(confirmBtn);
  container.appendChild(footer);
  modal.appendChild(container);
  document.body.appendChild(modal);
}

function getActiveInstagramProfile() {
  const profileLinks = document.querySelectorAll('a[href^="/"]');
  for (const a of profileLinks) {
    if (a.href.includes("instagram.com") && a.querySelector('img')) {
      const username = a.getAttribute('href').replace(/\//g, '');
      if (username && !["explore", "direct", "create", "reels", "messages", "notifications", "emails"].includes(username.toLowerCase())) {
        return username;
      }
    }
  }
  if (location.pathname.length > 1) {
    const pathUser = location.pathname.split("/")[1];
    if (pathUser && !["explore", "direct", "create", "reels", "messages", "notifications", "emails"].includes(pathUser.toLowerCase())) {
      return pathUser;
    }
  }
  return null;
}

function normalizeIgText(str) {
  if (!str) return "";
  return String(str)
    .replace(/İ/g, "i")
    .replace(/I/g, "ı")
    .toLocaleLowerCase("tr-TR")
    .trim();
}

function findInstagramActionButton(labels) {
  const normalizedLabels = labels.map(label => normalizeIgText(label));

  // 1. Önce aria-label veya title taşıyan tüm elemanları (SVG dahil) kontrol et
  const ariaCandidates = document.querySelectorAll("[aria-label], [title]");
  for (const el of ariaCandidates) {
    const aria = normalizeIgText(el.getAttribute("aria-label") || el.getAttribute("title") || "");
    if (normalizedLabels.some(c => aria === c || aria.includes(c))) {
      const btn = el.closest("button, a, div[role='button'], div[role='menuitem'], div[tabindex]") || el;
      if (!btn.disabled && btn.getAttribute("aria-disabled") !== "true") {
        return btn;
      }
    }
  }

  // 2. Metin veya title içeren butonlar
  const candidates = document.querySelectorAll("button, a, div[role='button'], div[role='menuitem'], div[tabindex='0']");
  for (const element of candidates) {
    const svgAria = normalizeIgText(element.querySelector("svg")?.getAttribute("aria-label") || "");
    const text = normalizeIgText(element.textContent);
    if (normalizedLabels.some(c => text === c || text.startsWith(c) || svgAria === c)) {
      if (
        !element.disabled &&
        element.getAttribute("aria-disabled") !== "true" &&
        element.getClientRects().length > 0
      ) return element;
    }
  }

  // 3. Yaprak metin elemanları (span, div)
  const allLeafEls = document.querySelectorAll("span, div");
  for (const el of allLeafEls) {
    if (el.children.length === 0) {
      const txt = normalizeIgText(el.textContent);
      if (normalizedLabels.some(c => txt === c)) {
        const clickable = el.closest("button, a, div[role='button'], div[role='menuitem'], div[tabindex], div.x9f619") || el;
        if (clickable && clickable.getClientRects().length > 0) return clickable;
      }
    }
  }

  return null;
}

function getExistingInstagramPostFileInput() {
  const dialog = document.querySelector('div[role="dialog"]');
  if (dialog) {
    const inputs = dialog.querySelectorAll('input[type="file"]');
    for (const inp of inputs) {
      const acc = (inp.getAttribute("accept") || "").toLowerCase();
      // Profil resmi input'u sadece resim kabul eder; gönderi input'u video kabul eder
      if (acc.includes("video") || !acc.includes("image/jpeg,image/png")) {
        return inp;
      }
    }
  }
  return null;
}

function findInstagramCreateButton() {
  const createLabels = ["yeni gönderi", "yeni gonderi", "new post", "create", "oluştur", "olustur"];
  const allSvgs = document.querySelectorAll("svg[aria-label], svg");
  for (const svg of allSvgs) {
    const aria = normalizeIgText(svg.getAttribute("aria-label") || svg.querySelector("title")?.textContent || "");
    if (createLabels.some(lbl => aria === lbl || aria.includes(lbl))) {
      const clickable = svg.closest("a, div[role='button'], div[role='link'], div[tabindex], div.x9f619") || svg.parentElement;
      if (clickable && clickable.getClientRects().length > 0) return clickable;
    }
  }

  const allTextEls = document.querySelectorAll("span, div");
  for (const el of allTextEls) {
    if (el.children.length === 0) {
      const txt = normalizeIgText(el.textContent);
      if (txt === "oluştur" || txt === "olustur" || txt === "create") {
        const clickable = el.closest("a, div[role='button'], div[role='link'], div[tabindex], div.x9f619") || el;
        if (clickable && clickable.getClientRects().length > 0) return clickable;
      }
    }
  }

  return findInstagramActionButton(["Yeni Gönderi", "Yeni gönderi", "New post", "Create", "Oluştur"]);
}

function findInstagramPostOption() {
  const postLabels = ["gönderi", "gonderi", "post"];
  const allSvgs = document.querySelectorAll("svg[aria-label], svg");
  for (const svg of allSvgs) {
    const aria = normalizeIgText(svg.getAttribute("aria-label") || svg.querySelector("title")?.textContent || "");
    if (postLabels.some(lbl => aria === lbl || aria.includes(lbl))) {
      const clickable = svg.closest("div[role='menuitem'], div[role='button'], a, div[tabindex], .html-div, div.x9f619") || svg.parentElement;
      if (clickable && clickable.getClientRects().length > 0) return clickable;
    }
  }

  const allTextEls = document.querySelectorAll("span, div");
  for (const el of allTextEls) {
    if (el.children.length === 0) {
      const txt = normalizeIgText(el.textContent);
      if (txt === "gönderi" || txt === "gonderi" || txt === "post") {
        const clickable = el.closest("div[role='menuitem'], div[role='button'], a, div[tabindex], .html-div, div.x9f619") || el;
        if (clickable && clickable.getClientRects().length > 0) return clickable;
      }
    }
  }

  return findInstagramActionButton(["Gönderi", "Post"]);
}

async function adjustInstagramAspectRatioToVertical() {
  showNotification("📐 Video oranı 9:16 Reels formatına ayarlanıyor...");
  await new Promise(resolve => setTimeout(resolve, 800));

  const dialog = document.querySelector('div[role="dialog"]');
  const scope = dialog || document;

  // 1. Kırpma (Crop) butonunu bul (Sol alttaki kırpma butonu)
  const cropLabels = ["kırpmayı seç", "kırpmayi sec", "select crop", "kırp", "crop", "kırpma"];
  let cropBtn = null;

  const svgs = scope.querySelectorAll("svg[aria-label], svg");
  for (const svg of svgs) {
    const aria = normalizeIgText(svg.getAttribute("aria-label") || svg.querySelector("title")?.textContent || "");
    if (cropLabels.some(lbl => aria === lbl || aria.includes(lbl))) {
      cropBtn = svg.closest("button, div[role='button'], div[tabindex]") || svg.parentElement;
      break;
    }
  }

  if (!cropBtn) {
    const candidateBtns = scope.querySelectorAll('button[aria-label], div[role="button"][aria-label]');
    for (const btn of candidateBtns) {
      const aria = normalizeIgText(btn.getAttribute("aria-label") || "");
      if (cropLabels.some(lbl => aria.includes(lbl))) {
        cropBtn = btn;
        break;
      }
    }
  }

  // Fallback: Dialog içindeki medya alanında bulunan ilk daire buton
  if (!cropBtn && dialog) {
    const mediaContainer = dialog.querySelector('div[style*="overflow"], div[role="dialog"]');
    if (mediaContainer) {
      const circleBtns = mediaContainer.querySelectorAll('button, div[role="button"]');
      for (const b of circleBtns) {
        if (b.querySelector('svg') && !b.textContent.includes("İleri") && !b.textContent.includes("Paylaş")) {
          cropBtn = b;
          break;
        }
      }
    }
  }

  if (cropBtn) {
    console.log("[IG-OTO] Kırpma menüsü açılıyor...", cropBtn);
    clickElementReliably(cropBtn);
    await new Promise(resolve => setTimeout(resolve, 600));

    // 2. Oran seçeneklerinden "9:16" veya "Orijinal" seç
    let ratioSelected = false;

    // A. Metin ile "9:16" veya "16:9" ara
    const allEls = document.querySelectorAll("span, div, button, p");
    for (const el of allEls) {
      if (el.children.length === 0) {
        const txt = el.textContent.trim();
        if (txt === "9:16" || txt === "16:9") {
          const clickable = el.closest("button, div[role='button'], div[role='menuitem'], div[tabindex]") || el;
          clickElementReliably(clickable);
          ratioSelected = true;
          console.log("[IG-OTO] ✅ 9:16 oranı seçildi!");
          break;
        }
      }
    }

    // B. Eğer 9:16 bulunamadıysa "Orijinal" seçeneğini ara (dikey videoyu tam boy 9:16 yapar)
    if (!ratioSelected) {
      for (const el of allEls) {
        if (el.children.length === 0) {
          const txt = normalizeIgText(el.textContent);
          if (txt === "orijinal" || txt === "original") {
            const clickable = el.closest("button, div[role='button'], div[role='menuitem'], div[tabindex]") || el;
            clickElementReliably(clickable);
            ratioSelected = true;
            console.log("[IG-OTO] ✅ Orijinal (9:16) oranı seçildi!");
            break;
          }
        }
      }
    }

    // C. SVG aria-label ile ara
    if (!ratioSelected) {
      const ratioSvgs = document.querySelectorAll('svg[aria-label], [aria-label]');
      for (const item of ratioSvgs) {
        const aria = normalizeIgText(item.getAttribute("aria-label") || "");
        if (aria.includes("9:16") || aria.includes("orijinal") || aria.includes("original")) {
          const clickable = item.closest("button, div[role='button'], div[role='menuitem'], div[tabindex]") || item;
          clickElementReliably(clickable);
          ratioSelected = true;
          console.log("[IG-OTO] ✅ Aria-label ile oran seçildi:", aria);
          break;
        }
      }
    }

    await new Promise(resolve => setTimeout(resolve, 500));

    // Kırpma menüsünü kapat
    try {
      clickElementReliably(cropBtn);
    } catch (e) {}
    await new Promise(resolve => setTimeout(resolve, 400));
  } else {
    console.warn("[IG-OTO] Kırpma butonu bulunamadı, varsayılan oranla devam ediliyor.");
  }
}

async function prepareInstagramPostFileInput(timeoutMs = 25000) {
  // 1. Eğer zaten "Yeni gönderi oluştur" modalı açıksa direkt kullan
  const existing = getExistingInstagramPostFileInput();
  if (existing) return existing;

  // 2. Sol menüdeki "Oluştur / Yeni Gönderi" butonunu tıkla
  try {
    const createBtn = findInstagramCreateButton();
    if (createBtn) {
      showNotification("🎬 Instagram 'Oluştur' menüsü açılıyor...");
      clickElementReliably(createBtn);
      await new Promise(r => setTimeout(r, 700));

      let postOption = findInstagramPostOption();
      if (!postOption) {
        await new Promise(r => setTimeout(r, 600));
        postOption = findInstagramPostOption();
      }
      if (postOption) {
        showNotification("📂 'Gönderi' seçeneği açılıyor...");
        clickElementReliably(postOption);
        await new Promise(r => setTimeout(r, 900));
      }
    }
  } catch (err) {
    console.warn("[IG-OTO] Menü açma uyarısı:", err);
  }

  // 3. Modal açılana ve video kabul eden file input hazır olana kadar bekle
  showNotification("💡 Video için 'Gönderi' penceresi bekleniyor...");
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const dialogInput = getExistingInstagramPostFileInput();
    if (dialogInput) return dialogInput;

    const dialog = document.querySelector('div[role="dialog"]');
    if (dialog) {
      const inp = dialog.querySelector('input[type="file"]');
      if (inp) return inp;
    }

    const vidInp = document.querySelector('input[type="file"][accept*="video"]');
    if (vidInp) return vidInp;

    await new Promise(r => setTimeout(r, 400));
  }

  throw new Error("Instagram 'Gönderi' yükleme alanı (modal) açılamadı. Lütfen sol menüden 'Oluştur' ➔ 'Gönderi'yi açıp tekrar 'Reels Yükle'ye tıklayın.");
}

async function waitForInstagramElement(selector, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const element = document.querySelector(selector);
    if (element) return element;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error("Instagram yükleme alanı zaman aşımına uğradı; Instagram oturumunu ve sayfayı kontrol edin.");
}

async function waitForInstagramButton(labels, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const button = findInstagramActionButton(labels);
    if (button) return button;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error(`Instagram'da '${labels[0]}' butonu bulunamadı; sayfa yükleniyor olabilir.`);
}

async function uploadToInstagram(payload, isScheduled = false) {
  if (!location.hostname.includes("instagram.com")) {
    throw new Error("Yükleme Instagram sekmesinde başlatılamadı. Lütfen instagram.com sekmesinde olun.");
  }
  const expectedUsername = String(payload.instagram_username || "").replace(/^@/, "").toLowerCase();
  const activeUsername = String(getActiveInstagramProfile() || "").replace(/^@/, "").toLowerCase();
  if (document.querySelector('input[name="username"], input[name="password"]')) {
    throw new Error("Instagram oturumu açık değil. Instagram'a giriş yapıp tekrar deneyin.");
  }
  if (expectedUsername && activeUsername && activeUsername !== expectedUsername) {
    throw new Error(`Açık Instagram hesabı @${activeUsername || "belirlenemedi"}; hedeflenen hesap @${expectedUsername}. Lütfen doğru Instagram hesabına geçin.`);
  }

  const { apiUrl = "http://127.0.0.1:8000" } = await chrome.storage.local.get("apiUrl");
  const apiBase = apiUrl.replace(/\/$/, "");

  let fetchUrl;
  if (payload.id && !payload.video_path && !payload.video_url) {
    fetchUrl = `${apiBase}/api/instagram/schedules/${encodeURIComponent(payload.id)}/video`;
  } else if (payload.video_path) {
    fetchUrl = `${apiBase}/api/video-file?path=${encodeURIComponent(payload.video_path)}`;
  } else if (payload.video_url) {
    fetchUrl = `${apiBase}${payload.video_url}`;
  } else if (payload.folder) {
    fetchUrl = `${apiBase}/api/video-file?path=${encodeURIComponent(payload.folder)}`;
  } else {
    throw new Error("Video dosya konumu belirlenemedi.");
  }

  showNotification("⏳ Video sunucudan alınıyor...");
  const videoResponse = await chrome.runtime.sendMessage({
    type: "FETCH_API",
    url: fetchUrl,
    asArrayBuffer: true,
  });
  if (!videoResponse?.ok || (!videoResponse.storageKey && !videoResponse.isBinary && !videoResponse.data)) {
    throw new Error(videoResponse?.error || "Video yerel sunucudan alınamadı.");
  }

  let file;
  try {
    let arrayBuffer;
    if (videoResponse.storageKey) {
      const stored = await chrome.storage.local.get(videoResponse.storageKey);
      const base64 = stored[videoResponse.storageKey];
      await chrome.storage.local.remove(videoResponse.storageKey);
      if (!base64) throw new Error("İndirilen video geçici depoda bulunamadı.");
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let offset = 0; offset < binary.length; offset += 8192) {
        const end = Math.min(offset + 8192, binary.length);
        for (let i = offset; i < end; i++) bytes[i] = binary.charCodeAt(i);
      }
      arrayBuffer = bytes.buffer;
    } else if (videoResponse.isBinary) {
      const binary = atob(videoResponse.data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      arrayBuffer = bytes.buffer;
    } else {
      arrayBuffer = videoResponse.data;
    }

    const safeName = String(payload.title || "instagram-reel").replace(/[\\/:*?"<>|]/g, "_");
    file = new File([new Blob([arrayBuffer], { type: "video/mp4" })], `${safeName}.mp4`, { type: "video/mp4" });
  } catch (decErr) {
    throw new Error(`Video verisi çözülemedi: ${decErr.message}`);
  }

  showNotification("🎬 Instagram'a video aktarılıyor...");
  const fileInput = await prepareInstagramPostFileInput(25000);

  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  fileInput.dispatchEvent(new Event("change", { bubbles: true }));
  fileInput.dispatchEvent(new Event("input", { bubbles: true }));

  showNotification("⏳ Video işleniyor, 'İleri' adımı bekleniyor...");
  await new Promise(resolve => setTimeout(resolve, 2000));

  // Olası "Tamam / Anladım" (Videolar artık Reels olarak paylaşılıyor) bilgilendirme modalı
  try {
    const okBtn = findInstagramActionButton(["Tamam", "OK", "Got it", "Anladım"]);
    if (okBtn) clickElementReliably(okBtn);
  } catch (e) {}

  // ── 1:1 Kare Kırpmayı Önle ➔ 9:16 Dikey Reels Oranına Ayarla ──
  await adjustInstagramAspectRatioToVertical();

  // 1. İleri (Kırpma / Boyut adımı)
  await waitForInstagramButton(["Next", "İleri"]);
  const next1 = findInstagramActionButton(["Next", "İleri"]);
  if (!next1) throw new Error("İlk 'İleri' düğmesi bulunamadı.");
  clickElementReliably(next1);
  await new Promise(resolve => setTimeout(resolve, 1500));

  // 2. İleri (Filtreler / Düzenleme adımı)
  await waitForInstagramButton(["Next", "İleri"]);
  const next2 = findInstagramActionButton(["Next", "İleri"]);
  if (!next2) throw new Error("İkinci 'İleri' düğmesi bulunamadı.");
  clickElementReliably(next2);
  await new Promise(resolve => setTimeout(resolve, 1500));

  showNotification("✍️ Açıklama ve etiketler yazılıyor...");
  const captionArea = await waitForInstagramElement('div[role="dialog"] [contenteditable="true"], [contenteditable="true"]');
  const caption = String(payload.caption || payload.description || "").slice(0, 2200);
  captionArea.focus();
  document.execCommand("insertText", false, caption);
  if (captionArea.textContent.trim() !== caption.trim()) captionArea.textContent = caption;
  captionArea.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: caption }));

  await new Promise(resolve => setTimeout(resolve, 800));

  // ── AÇIKLAMA YAZILDIKTAN SONRA EKLENTİNİN İŞİ BİTER ──
  // Paylaşma düğmesi kullanıcıya bırakılır, eklenti işlemi burada tamamlar.

  // 1. Backend output durumunu güncelle (uploaded_instagram: true)
  if (payload.folder) {
    try {
      const statusUrl = `${apiBase}/api/output/${encodeURIComponent(payload.folder)}/status`;
      const statusResp = await fetchFromBackground(statusUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instagram: true }),
      });
      const resObj = statusResp?.data || statusResp || {};
      if (resObj.archived) {
        showNotification("📦 Instagram hazır! Başka platform gerekmediği için video 'yuklenen' klasörüne taşındı. (Paylaş butonuna basabilirsiniz)");
      } else {
        showNotification("✅ Açıklama yapıştırıldı! (Diğer platformlar beklendiği için dosya 'yuklenecek'te saklandı — Paylaş'a basabilirsiniz)");
      }
    } catch (err) {
      console.warn("[IG-OTO] Output durumu güncellenemedi:", err);
      showNotification("✅ Açıklama yapıştırıldı! Paylaş butonuna basabilirsiniz.");
    }
  } else {
    showNotification("✅ Açıklama yapıştırıldı! Paylaş butonuna basabilirsiniz.");
  }

  // 2. Zamanlanmış görev varsa tamamlandı olarak kaydet
  if (isScheduled && payload.id) {
    try {
      await finishScheduledInstagramUpload(payload.id, { success: true });
    } catch (error) {
      console.warn("[IG-OTO] Planlama sonucu kaydedilemedi:", error);
    }
  }

  // 3. Rozet sayacını tazele
  if (typeof updateInstagramReadyCount === "function") {
    updateInstagramReadyCount();
  }

  return { success: true };
}

async function runScheduledInstagramUpload(schedule) {
  return uploadToInstagram(schedule, true);
}

async function finishScheduledInstagramUpload(scheduleId, result) {
  const { apiUrl = "http://127.0.0.1:8000" } = await chrome.storage.local.get("apiUrl");
  const response = await chrome.runtime.sendMessage({
    type: "FETCH_API",
    url: `${apiUrl.replace(/\/$/, "")}/api/instagram/schedules/${encodeURIComponent(scheduleId)}/result`,
    options: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result),
    },
  });
  if (!response?.ok) throw new Error(response?.error || "Planlama sonucu yerel sunucuya kaydedilemedi.");
  chrome.runtime.sendMessage({ type: "INSTAGRAM_SCHEDULE_FINISHED" });
}

// ═══════════════════════════════════════════════════════════════
// ⚡ INSTAGRAM OTO YÜKLE BUTONLARI VE EYLEMLERİ
// ═══════════════════════════════════════════════════════════════

async function updateInstagramReadyCount() {
  try {
    const res = await fetchFromBackground("http://127.0.0.1:8000/api/output");
    const videos = (res && res.data) || [];
    const readyVideos = videos.filter(v => !v.archived && !v.uploaded_instagram);
    const count = readyVideos.length;

    const badge = document.getElementById("ig-oto-badge");
    if (badge) {
      badge.textContent = count;
      badge.style.display = count > 0 ? "inline-block" : "none";
    }

    const sideBadge = document.getElementById("ig-oto-sidebar-badge");
    if (sideBadge) {
      sideBadge.textContent = count;
      sideBadge.style.display = count > 0 ? "inline-flex" : "none";
    }
  } catch (e) {
    // Backend ulaşılamazsa sessiz geç
  }
}

function injectInstagramContentActions() {
  if (!location.href.includes("instagram.com")) return;

  // 1. Sidebar Enjeksiyonu dene
  injectInstagramSidebarAction();

  // 2. Zaten floating bar ekliyse badge'i tazele ve çık
  if (document.getElementById("ig-oto-content-actions")) {
    return;
  }

  const container = document.createElement("div");
  container.id = "ig-oto-content-actions";
  container.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 28px;
    z-index: 9999999;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(15, 23, 42, 0.94);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1.5px solid rgba(225, 48, 108, 0.45);
    border-radius: 9999px;
    padding: 6px 12px 6px 8px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(225, 48, 108, 0.25);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  `;

  // "⚡ Reels Yükle" Butonu
  const btnUpload = document.createElement("button");
  btnUpload.id = "ig-oto-main-btn";
  btnUpload.innerHTML = `
    <span style="display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #f09433, #dc2743, #bc1888); color: #ffffff; font-size: 15px; font-weight: bold; margin-right: 8px; box-shadow: 0 2px 8px rgba(220, 39, 67, 0.4);">⚡</span>
    <span style="font-size: 13.5px; font-weight: 700; color: #ffffff; letter-spacing: 0.2px;">Reels Yükle</span>
    <span id="ig-oto-badge" style="display: none; background: #e1306c; color: #ffffff; border-radius: 12px; padding: 2px 8px; font-size: 11px; font-weight: 700; margin-left: 8px;">0</span>
  `;
  btnUpload.style.cssText = `
    background: transparent;
    color: #ffffff;
    border: none;
    border-radius: 9999px;
    padding: 2px 4px;
    font-family: inherit;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    transition: all 0.2s ease;
  `;

  container.addEventListener("mouseenter", () => {
    container.style.transform = "translateY(-2px)";
    container.style.borderColor = "rgba(225, 48, 108, 0.8)";
    container.style.boxShadow = "0 14px 36px rgba(0, 0, 0, 0.6), 0 0 28px rgba(225, 48, 108, 0.45)";
  });
  container.addEventListener("mouseleave", () => {
    container.style.transform = "none";
    container.style.borderColor = "rgba(225, 48, 108, 0.45)";
    container.style.boxShadow = "0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(225, 48, 108, 0.25)";
  });

  btnUpload.addEventListener("click", openOtoYukleModal);

  // "⚙️" Ayarlar / Yenile Butonu
  const btnSettings = document.createElement("button");
  btnSettings.id = "ig-oto-settings-btn";
  btnSettings.innerHTML = "⚙️";
  btnSettings.title = "Kanal & Yükleme Ayarları";
  btnSettings.style.cssText = `
    background: rgba(255, 255, 255, 0.08);
    color: #f8fafc;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 50%;
    width: 32px;
    height: 32px;
    font-size: 13.5px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  `;
  btnSettings.addEventListener("mouseenter", () => {
    btnSettings.style.background = "rgba(255, 255, 255, 0.16)";
  });
  btnSettings.addEventListener("mouseleave", () => {
    btnSettings.style.background = "rgba(255, 255, 255, 0.08)";
  });
  btnSettings.addEventListener("click", () => openChannelUploadSettingsModal());

  container.appendChild(btnUpload);
  container.appendChild(btnSettings);
  document.body.appendChild(container);

  updateInstagramReadyCount();
}

function injectInstagramSidebarAction() {
  if (document.getElementById("ig-oto-sidebar-item")) return;

  // Instagram Sol Gezinti Çubuğunu Bul
  let navTarget = null;
  const createSvg = document.querySelector('svg[aria-label="New post"], svg[aria-label="Yeni gönderi"], svg[aria-label="Create"], svg[aria-label="Oluştur"]');
  if (createSvg) {
    navTarget = createSvg.closest("a, div[role='button'], div[role='link']");
  }

  if (!navTarget) {
    const directLink = document.querySelector('a[href*="/direct/"]');
    if (directLink) {
      navTarget = directLink.closest("div");
    }
  }

  if (!navTarget || !navTarget.parentNode) return;

  const sidebarItem = document.createElement("div");
  sidebarItem.id = "ig-oto-sidebar-item";
  sidebarItem.style.cssText = `
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 12px;
    margin: 4px 0;
    border-radius: 12px;
    cursor: pointer;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #f8fafc;
    transition: background 0.18s ease;
    user-select: none;
  `;

  sidebarItem.innerHTML = `
    <div style="width: 28px; height: 28px; border-radius: 8px; background: linear-gradient(135deg, #f09433, #dc2743, #bc1888); display: flex; align-items: center; justify-content: center; font-size: 15px; color: white; flex-shrink: 0; box-shadow: 0 2px 8px rgba(220, 39, 67, 0.35);">
      ⚡
    </div>
    <span style="font-size: 14px; font-weight: 600; white-space: nowrap; flex: 1;">Reels Yükle</span>
    <span id="ig-oto-sidebar-badge" style="display: none; background: #e1306c; color: white; border-radius: 10px; padding: 2px 7px; font-size: 11px; font-weight: 700;">0</span>
  `;

  sidebarItem.addEventListener("mouseenter", () => {
    sidebarItem.style.background = "rgba(255, 255, 255, 0.08)";
  });
  sidebarItem.addEventListener("mouseleave", () => {
    sidebarItem.style.background = "transparent";
  });
  sidebarItem.addEventListener("click", openOtoYukleModal);

  navTarget.parentNode.insertBefore(sidebarItem, navTarget.nextSibling);
  updateInstagramReadyCount();
}

// ── Gemini Web Automation - İçerik Planlama Eklentisi ──────────

let geminiPlanRunning = false;
let geminiPlanConsole = null;
let geminiPlanExecutionMode = "new"; // "new" | "retro"
let geminiPlanPendingCache = null;

function logGeminiPlan(msg, type = "info") {
  console.log(`[GEMINI-PLAN] [${type.toUpperCase()}] ${msg}`);
  if (geminiPlanConsole) {
    const color = type === "error" ? "#f43f5e" : (type === "success" ? "#10b981" : "#94a3b8");
    const div = document.createElement("div");
    div.style.cssText = `color: ${color}; margin-bottom: 4px; font-size: 13px; line-height: 1.4;`;
    div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    geminiPlanConsole.appendChild(div);
    geminiPlanConsole.scrollTop = geminiPlanConsole.scrollHeight;
  }
}

function injectGeminiPlanFAB() {
  if (document.getElementById("gemini-plan-fab")) return;

  const fab = document.createElement("div");
  fab.id = "gemini-plan-fab";
  fab.style.cssText = `
    position: fixed; bottom: 84px; right: 24px; z-index: 999999;
    background: linear-gradient(135deg, #10b981, #34d399);
    color: white; width: 48px; height: 48px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; font-size: 22px; font-weight: bold;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.45);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden; white-space: nowrap;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  `;
  
  const text = document.createElement("span");
  text.style.cssText = `
    opacity: 0; width: 0; display: inline-block; font-size: 13.5px;
    font-weight: 600; margin-left: 0; transition: all 0.25s ease;
  `;
  text.textContent = "İçerik Planla";

  const icon = document.createElement("span");
  icon.textContent = "💡";
  
  fab.appendChild(icon);
  fab.appendChild(text);
  document.body.appendChild(fab);

  fab.addEventListener("mouseenter", () => {
    fab.style.width = "140px";
    fab.style.borderRadius = "24px";
    text.style.opacity = "1";
    text.style.width = "auto";
    text.style.marginLeft = "8px";
  });
  fab.addEventListener("mouseleave", () => {
    fab.style.width = "48px";
    fab.style.borderRadius = "50%";
    text.style.opacity = "0";
    text.style.width = "0";
    text.style.marginLeft = "0";
  });

  fab.addEventListener("click", openGeminiPlanModal);
}

function openGeminiPlanModal() {
  const existing = document.getElementById("gemini-plan-modal");
  if (existing) {
    existing.style.display = "flex";
    if (geminiPlanExecutionMode === "retro") {
      loadRetroactiveChannelsDropdown();
    } else {
      loadPlanChannelsDropdown();
    }
    return;
  }

  const modal = document.createElement("div");
  modal.id = "gemini-plan-modal";
  modal.style.cssText = `
    position: fixed; bottom: 144px; right: 24px; width: 390px;
    background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px; padding: 20px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
    color: #f8fafc; display: flex; flex-direction: column; gap: 13px;
    z-index: 10000000;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    animation: ytOtoFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  `;

  const header = document.createElement("div");
  header.style.cssText = `
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 10px;
  `;
  header.innerHTML = `
    <div>
      <h3 style="margin: 0; font-size: 15px; font-weight: 700; color: #10b981; display: flex; align-items: center; gap: 8px;">
        💡 Gemini İçerik & Senaryo Planlayıcı
      </h3>
      <div id="gemini-plan-modal-sub" style="font-size: 11px; color: #94a3b8; margin-top: 3px; line-height: 1.35;">
        Yeni konular planlayın veya mevcut plandaki eksik materyalleri geçmişe dönük üretin.
      </div>
    </div>
  `;
  
  const closeBtn = document.createElement("button");
  closeBtn.textContent = "✕";
  closeBtn.style.cssText = `
    background: transparent; border: none; color: #94a3b8; font-size: 18px;
    cursor: pointer; padding: 4px; line-height: 1; transition: color 0.2s;
  `;
  closeBtn.addEventListener("mouseenter", () => closeBtn.style.color = "#f8fafc");
  closeBtn.addEventListener("mouseleave", () => closeBtn.style.color = "#94a3b8");
  closeBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });
  header.appendChild(closeBtn);
  modal.appendChild(header);

  // ── Mod Seçimi: Yeni Plan vs Geçmişe Dönük Materyal ──
  const modeSwitch = document.createElement("div");
  modeSwitch.style.cssText = `
    display: flex; gap: 4px; background: #0f172a; padding: 4px; border-radius: 10px;
    border: 1px solid #334155; margin-bottom: 2px;
  `;
  modeSwitch.innerHTML = `
    <button type="button" id="gemini-mode-new-btn" style="flex: 1; padding: 7px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${geminiPlanExecutionMode === "new" ? "#10b981" : "transparent"}; color: ${geminiPlanExecutionMode === "new" ? "#fff" : "#94a3b8"};">
      ✨ Yeni Plan
    </button>
    <button type="button" id="gemini-mode-retro-btn" style="flex: 1; padding: 7px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; background: ${geminiPlanExecutionMode === "retro" ? "linear-gradient(135deg, #06b6d4, #6366f1)" : "transparent"}; color: ${geminiPlanExecutionMode === "retro" ? "#fff" : "#94a3b8"};">
      📦 Geçmişe Dönük Üret
    </button>
  `;
  modal.appendChild(modeSwitch);

  const retroNotice = document.createElement("div");
  retroNotice.id = "gemini-plan-retro-notice";
  retroNotice.style.cssText = `
    display: ${geminiPlanExecutionMode === "retro" ? "block" : "none"}; padding: 8px 10px; border-radius: 8px; font-size: 11px; line-height: 1.4;
    background: rgba(6, 182, 212, 0.1); border: 1px solid rgba(6, 182, 212, 0.3); color: #22d3ee;
  `;
  retroNotice.innerHTML = `
    <strong>🔄 Geçmişe Dönük Mod:</strong> Aktif kanalların mevcut içerik planında yer alan henüz üretilmemiş konuları taranır ve senaryo/prompt materyalleri eksiksiz üretilir.
  `;
  modal.appendChild(retroNotice);

  const group = document.createElement("div");
  group.style.cssText = `display: flex; flex-direction: column; gap: 6px;`;
  group.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">1. Hedef Kanal Seçin</label>
    <select id="gemini-plan-channel-select" style="background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 8px 10px; border-radius: 8px; font-size: 13.5px; outline: none; cursor: pointer;"></select>
  `;
  modal.appendChild(group);

  const countGroup = document.createElement("div");
  countGroup.style.cssText = `display: flex; flex-direction: column; gap: 6px;`;
  countGroup.innerHTML = `
    <label id="gemini-plan-count-label" style="font-size: 12px; font-weight: 600; color: #94a3b8;">
      ${geminiPlanExecutionMode === "retro" ? "2. İşlenecek Konu Sayısı (Her Kanal İçin)" : "2. Planlanacak Konu Sayısı"}
    </label>
    <input type="number" id="gemini-plan-count-input" value="5" min="1" max="25" style="background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 8px 10px; border-radius: 8px; font-size: 13.5px; outline: none;" />
  `;
  modal.appendChild(countGroup);

  const materialsOptionGroup = document.createElement("div");
  materialsOptionGroup.id = "gemini-plan-materials-opt-group";
  materialsOptionGroup.style.cssText = `display: ${geminiPlanExecutionMode === "new" ? "flex" : "none"}; flex-direction: column; gap: 6px;`;
  materialsOptionGroup.innerHTML = `
    <label style="display: flex; align-items: flex-start; gap: 8px; font-size: 12px; cursor: pointer; color: #38bdf8; background: rgba(56, 189, 248, 0.08); padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.25);">
      <input type="checkbox" id="gemini-plan-full-materials-chk" checked style="accent-color: #38bdf8; margin-top: 2px;">
      <div>
        <strong style="display: block; color: #f8fafc;">Eksiksiz Senaryo & Üretim Materyalleri Üret</strong>
        <span style="font-size: 11px; color: #94a3b8; display: block; margin-top: 2px;">
          Her içerik için sahneleri ve görsel promptlarını hazırlar; sistem sayfasından tek tıkla üretime hazır hale getirir.
        </span>
      </div>
    </label>
  `;
  modal.appendChild(materialsOptionGroup);

  const modeGroup = document.createElement("div");
  modeGroup.style.cssText = `display: flex; flex-direction: column; gap: 6px;`;
  modeGroup.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">3. Sohbet Tercihi</label>
    <div style="display: flex; gap: 16px; margin-top: 4px;">
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-plan-chat-mode" value="normal" checked style="accent-color: #10b981;">
        Devam Et (Normal)
      </label>
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; color: #cbd5e1;">
        <input type="radio" name="gemini-plan-chat-mode" value="temp" style="accent-color: #10b981;">
        Geçici Sohbet
      </label>
    </div>
  `;
  modal.appendChild(modeGroup);

  const consoleGroup = document.createElement("div");
  consoleGroup.style.cssText = `display: flex; flex-direction: column; gap: 6px; flex-grow: 1;`;
  consoleGroup.innerHTML = `
    <label style="font-size: 12px; font-weight: 600; color: #94a3b8;">İşlem Günlüğü (Console)</label>
  `;

  const thinkingBar = document.createElement("div");
  thinkingBar.id = "gemini-plan-thinking-bar";
  thinkingBar.style.cssText = `
    height: 4px;
    background: linear-gradient(90deg, #10b981, #34d399, #6ee7b7, #10b981);
    background-size: 200% auto;
    animation: shine 2s linear infinite;
    border-radius: 4px;
    margin-bottom: 6px;
    display: none;
  `;
  consoleGroup.appendChild(thinkingBar);
  
  const consoleDiv = document.createElement("div");
  consoleDiv.id = "gemini-plan-console";
  consoleDiv.style.cssText = `
    background: #0f172a; border: 1px solid #334155; border-radius: 8px;
    height: 140px; padding: 10px; overflow-y: auto; font-family: monospace;
    font-size: 11px; color: #94a3b8; display: flex; flex-direction: column;
  `;
  consoleDiv.innerHTML = `<div style="color: #64748b;">Hazır. İçerik planlamasını başlatmak için butona tıklayın...</div>`;
  consoleGroup.appendChild(consoleDiv);
  modal.appendChild(consoleGroup);
  
  geminiPlanConsole = consoleDiv;

  const actions = document.createElement("div");
  actions.style.cssText = `
    display: flex; gap: 10px; border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 14px; margin-top: 4px;
  `;
  
  const startBtn = document.createElement("button");
  startBtn.id = "gemini-plan-start-btn";
  startBtn.textContent = geminiPlanExecutionMode === "retro" ? "🚀 Geçmişe Dönük Materyal Üret" : "Planlamayı Başlat";
  startBtn.style.cssText = `
    background: ${geminiPlanExecutionMode === "retro" ? "linear-gradient(135deg, #06b6d4, #6366f1)" : "#10b981"};
    color: white; border: none; padding: 10px 18px;
    border-radius: 8px; font-size: 13.5px; font-weight: 600; cursor: pointer;
    flex-grow: 1; transition: background 0.2s;
  `;
  
  // Mod Butonları Olay Dinleyicileri
  const newBtn = modeSwitch.querySelector("#gemini-mode-new-btn");
  const retroBtn = modeSwitch.querySelector("#gemini-mode-retro-btn");
  
  newBtn.addEventListener("click", () => {
    geminiPlanExecutionMode = "new";
    newBtn.style.background = "#10b981";
    newBtn.style.color = "#fff";
    retroBtn.style.background = "transparent";
    retroBtn.style.color = "#94a3b8";
    retroNotice.style.display = "none";
    materialsOptionGroup.style.display = "flex";
    document.getElementById("gemini-plan-count-label").textContent = "2. Planlanacak Konu Sayısı";
    startBtn.textContent = "Planlamayı Başlat";
    startBtn.style.background = "#10b981";
    loadPlanChannelsDropdown();
  });

  retroBtn.addEventListener("click", () => {
    geminiPlanExecutionMode = "retro";
    retroBtn.style.background = "linear-gradient(135deg, #06b6d4, #6366f1)";
    retroBtn.style.color = "#fff";
    newBtn.style.background = "transparent";
    newBtn.style.color = "#94a3b8";
    retroNotice.style.display = "block";
    materialsOptionGroup.style.display = "none";
    document.getElementById("gemini-plan-count-label").textContent = "2. İşlenecek Konu Sayısı (Her Kanal İçin)";
    startBtn.textContent = "🚀 Geçmişe Dönük Materyal Üret";
    startBtn.style.background = "linear-gradient(135deg, #06b6d4, #6366f1)";
    loadRetroactiveChannelsDropdown();
  });

  startBtn.addEventListener("click", () => {
    if (geminiPlanRunning) {
      geminiPlanRunning = false;
      logGeminiPlan("Planlama kullanıcı tarafından durduruluyor...", "error");
      togglePlanStartButtonState(false);
    } else {
      const select = document.getElementById("gemini-plan-channel-select");
      const channelId = select.value;
      if (!channelId) {
        logGeminiPlan("Hata: Herhangi bir kanal seçilmedi.", "error");
        return;
      }
      const countInput = document.getElementById("gemini-plan-count-input");
      const count = parseInt(countInput.value) || 5;
      const useTempChat = document.querySelector('input[name="gemini-plan-chat-mode"]:checked').value === "temp";
      const fullMaterials = document.getElementById("gemini-plan-full-materials-chk")?.checked ?? true;
      
      togglePlanStartButtonState(true);
      if (geminiPlanExecutionMode === "retro") {
        runGeminiRetroactiveMaterialsAutomation(channelId, count, useTempChat);
      } else {
        runGeminiPlanAutomation(channelId, count, useTempChat, fullMaterials);
      }
    }
  });
  
  const cleanBtn = document.createElement("button");
  cleanBtn.id = "gemini-plan-clean-btn";
  cleanBtn.textContent = "Tekrarları Temizle";
  cleanBtn.style.cssText = `
    background: #6366f1; color: white; border: none; padding: 10px 14px;
    border-radius: 8px; font-size: 13.5px; font-weight: 600; cursor: pointer;
    flex-grow: 0; transition: background 0.2s;
  `;
  
  cleanBtn.addEventListener("click", () => {
    if (geminiPlanRunning) {
      geminiPlanRunning = false;
      logGeminiPlan("İşlem kullanıcı tarafından durduruluyor...", "error");
      toggleCleanButtonState(false);
    } else {
      const select = document.getElementById("gemini-plan-channel-select");
      const channelId = select.value;
      if (!channelId) {
        logGeminiPlan("Hata: Herhangi bir kanal seçilmedi.", "error");
        return;
      }
      toggleCleanButtonState(true);
      runGeminiCleanAutomation(channelId);
    }
  });
  
  actions.appendChild(startBtn);
  actions.appendChild(cleanBtn);
  modal.appendChild(actions);
  document.body.appendChild(modal);

  // Kanal seçimi değiştiğinde retro bildirimini güncelle
  const chanSelect = document.getElementById("gemini-plan-channel-select");
  chanSelect.addEventListener("change", () => {
    if (geminiPlanExecutionMode === "retro" && geminiPlanPendingCache) {
      const val = chanSelect.value;
      const notice = document.getElementById("gemini-plan-retro-notice");
      if (!notice) return;
      if (val === "all_active") {
        notice.innerHTML = `<strong>🔄 Geçmişe Dönük Mod:</strong> Toplam <strong>${geminiPlanPendingCache.total_pending}</strong> adet üretilmemiş plan konusu bulundu. Tüm aktif kanallar sırayla işlenecektir.`;
      } else {
        const found = (geminiPlanPendingCache.channels || []).find(c => c.channel_id === val);
        if (found) {
          notice.innerHTML = `<strong>🔄 ${found.name}:</strong> Materyali bulunmayan <strong>${found.pending_count}</strong> adet içerik konusu tespit edildi.`;
        }
      }
    }
  });

  if (geminiPlanExecutionMode === "retro") {
    loadRetroactiveChannelsDropdown();
  } else {
    loadPlanChannelsDropdown();
  }
}

function togglePlanStartButtonState(running) {
  const btn = document.getElementById("gemini-plan-start-btn");
  if (btn) {
    if (running) {
      btn.textContent = "Durdur";
      btn.style.background = "#ef4444";
    } else {
      if (geminiPlanExecutionMode === "retro") {
        btn.textContent = "🚀 Geçmişe Dönük Materyal Üret";
        btn.style.background = "linear-gradient(135deg, #06b6d4, #6366f1)";
      } else {
        btn.textContent = "Planlamayı Başlat";
        btn.style.background = "#10b981";
      }
    }
  }
}

async function loadRetroactiveChannelsDropdown() {
  const select = document.getElementById("gemini-plan-channel-select");
  if (!select) return;

  select.innerHTML = "<option value=''>Bekleyen planlar taranıyor...</option>";

  try {
    const apiUrl = await getApiUrl();
    const res = await fetchFromBackground(`${apiUrl}/api/active-channels/pending-plan`);
    if (res.ok) {
      const data = await res.json();
      geminiPlanPendingCache = data;
      const channels = data.channels || [];
      const totalPending = data.total_pending || 0;

      let html = `<option value="all_active">⚡ TÜM AKTİF KANALLAR & GRUPLAR (${totalPending} Bekleyen Konu)</option>`;
      
      const groups = channels.filter(c => c.type === "group" || c.is_group);
      const standalones = channels.filter(c => c.type !== "group" && !c.is_group);

      if (groups.length > 0) {
        html += `<optgroup label="📁 Kanal Grupları (Çok Dilli)">`;
        groups.forEach(g => {
          const val = (g.channel_id || "").startsWith("group:") ? g.channel_id : `group:${g.group_id || g.channel_id}`;
          const count = g.pending_count || 0;
          const gLabel = g.raw_name ? `📁 [GRUP] ${g.raw_name}` : (g.name || g.channel_id);
          const disabledAttr = count === 0 ? " disabled style='color: #64748b;'" : "";
          const statusText = count === 0 ? " - Tamamlandı (0 bekleyen)" : ` (${count} bekleyen)`;
          html += `<option value="${val}"${disabledAttr}>${gLabel}${statusText}</option>`;
        });
        html += `</optgroup>`;
      }

      if (standalones.length > 0) {
        html += `<optgroup label="📺 Tekil Kanallar">`;
        standalones.forEach(c => {
          const flag = (c.language === "tr" ? "🇹🇷" : c.language === "en" ? "🇺🇸" : "🌐");
          const count = c.pending_count || 0;
          const disabledAttr = count === 0 ? " disabled style='color: #64748b;'" : "";
          const statusText = count === 0 ? " - Tamamlandı (0 bekleyen)" : ` (${count} bekleyen)`;
          html += `<option value="${c.channel_id}"${disabledAttr}>${flag} ${c.name || c.channel_id}${statusText}</option>`;
        });
        html += `</optgroup>`;
      }

      select.innerHTML = html;
      logGeminiPlan(`Geçmişe dönük mod: ${channels.length} hedef (${groups.length} grup, ${standalones.length} tekil kanal), toplam ${totalPending} bekleyen konu listelendi.`, "info");
      
      const retroNotice = document.getElementById("gemini-plan-retro-notice");
      if (retroNotice) {
        retroNotice.innerHTML = `<strong>🔄 Geçmişe Dönük Mod:</strong> Toplam <strong>${totalPending}</strong> adet üretilmemiş konu bulundu. Seçtiğiniz kanal veya kanal grubu için senaryo ve görsel materyalleri üretilecektir.`;
      }
    } else {
      select.innerHTML = "<option value=''>Bekleyen planlar alınamadı.</option>";
    }
  } catch (err) {
    select.innerHTML = "<option value=''>Bağlantı hatası.</option>";
  }
}

function toggleCleanButtonState(running) {
  const btn = document.getElementById("gemini-plan-clean-btn");
  if (btn) {
    if (running) {
      btn.textContent = "Durdur";
      btn.style.background = "#ef4444";
    } else {
      btn.textContent = "Tekrarları Temizle";
      btn.style.background = "#6366f1";
    }
  }
}

async function runGeminiCleanAutomation(channelId) {
  geminiPlanRunning = true;
  logGeminiPlan(`Tekrar temizleme otomasyonu başlatıldı.`, "info");
  
  const thinkingBar = document.getElementById("gemini-plan-thinking-bar");
  if (thinkingBar) thinkingBar.style.display = "block";
  
  try {
    const apiUrl = await getApiUrl();
    
    // 1. İçerik planını çek
    logGeminiPlan("Kanalın içerik planı backend'den alınıyor...", "info");
    const planRes = await fetchFromBackground(`${apiUrl}/api/channels/${channelId}/plan`);
    if (!planRes.ok) throw new Error("İçerik planı alınamadı.");
    const planData = await planRes.json();
    
    const planArray = (planData && Array.isArray(planData.plan)) ? planData.plan : [];
    if (planArray.length === 0) {
      logGeminiPlan("İçerik planı boş, temizlenecek bir şey yok.", "warning");
      return;
    }
    
    // Sadece gerekli alanları prompt için sadeleştir (id, baslik, uretildi)
    const simplifiedPlan = planArray.map(item => ({
      id: item.id,
      baslik: item.baslik || item.konu || "",
      uretildi: item.uretildi || "Hayır"
    }));

    // 2. Prompt hazırla
    logGeminiPlan("Tekrar analizi promptu hazırlanıyor...", "info");
    const promptText = `Aşağıdaki YouTube içerik planındaki konuları incele. Semantik olarak birbirini tekrar eden (mükerrer) konuları tespit et.
Eğer bir konu, daha önceki bir konuyla (veya üretilmiş bir konuyla) çok benzer veya aynıysa ve bu benzer konu henüz üretilmediyse (uretildi: "Hayır" veya "No" veya "false" ise), bu satırın silinmesi gerekir.
Lütfen silinmesi gereken mükerrer ve üretilmemiş satırların ID'lerini içeren bir JSON listesi döndür.
Döneceğin format sadece geçerli bir JSON dizisi olmalıdır: ["row_id_1", "row_id_2"]
Başka hiçbir açıklama, markdown işareti veya ek metin ekleme.

Konu Listesi:
${JSON.stringify(simplifiedPlan, null, 2)}`;

    // 3. Promptu yaz ve gönder
    logGeminiPlan("Prompt Gemini'a yazılıyor...", "info");
    const inputArea = await waitForPromptInput();
    if (!inputArea) throw new Error("Prompt giriş alanı bulunamadı.");

    simulateTyping(inputArea, promptText);
    await new Promise(r => setTimeout(r, 500));

    logGeminiPlan("Tekrar analizi talebi gönderildi. Yanıt bekleniyor...", "info");
    const initialTurns = getTurnCount();
    const clickSuccess = clickSendButton();
    if (!clickSuccess) throw new Error("Gönder butonu bulunamadı.");
    await new Promise(r => setTimeout(r, 1000));

    // 4. Gemini yanıtını bekle
    await waitForGeminiGeneration(initialTurns);
    logGeminiPlan("Gemini yanıtı alındı.", "success");

    const rawText = getLastResponseText();
    let deleteIds = robustCleanAndParseJson(rawText);
    
    if (!deleteIds || !Array.isArray(deleteIds)) {
      logGeminiPlan("JSON Ayrıştırma hatası! Ham veri console loga yazıldı.", "error");
      console.log("[GEMINI-CLEAN-RAW-TEXT]:", rawText);
      throw new Error("Gemini geçerli bir JSON array yanıtı üretmedi.");
    }

    if (!Array.isArray(deleteIds)) {
      throw new Error("Yapay zeka yanıtı bir JSON array/liste olmalıdır.");
    }
    
    if (deleteIds.length === 0) {
      logGeminiPlan("Mükerrer içerik bulunamadı. İçerik planınız temiz! 🎉", "success");
      showNotification("🎉 Mükerrer içerik bulunamadı. Planınız temiz!");
      return;
    }
    
    logGeminiPlan(`Gemini tarafından ${deleteIds.length} adet mükerrer ve üretilmemiş içerik tespit edildi. Kaldırılıyor...`, "info");
    
    let deletedCount = 0;
    // 5. Her bir ID'yi silmek için backend API'sini çağır
    for (const rowId of deleteIds) {
      if (!geminiPlanRunning) {
        logGeminiPlan("İşlem kullanıcı tarafından durduruldu.", "error");
        break;
      }
      try {
        logGeminiPlan(`İçerik #${rowId} siliniyor...`, "info");
        const deleteRes = await fetchFromBackground(`${apiUrl}/api/channels/${channelId}/plan/${rowId}`, {
          method: "DELETE"
        });
        if (deleteRes.ok) {
          deletedCount++;
        } else {
          logGeminiPlan(`Uyarı: İçerik #${rowId} silinemedi.`, "warning");
        }
      } catch (err) {
        logGeminiPlan(`Hata: #${rowId} silinirken hata: ${err.message}`, "error");
      }
    }
    
    logGeminiPlan(`Başarılı! ${deletedCount} adet mükerrer içerik plan listesinden otomatik olarak kaldırıldı! 🎉`, "success");
    showNotification(`🎉 ${deletedCount} Mükerrer içerik başarıyla kaldırıldı!`);
    
  } catch (err) {
    logGeminiPlan(`Temizleme başarısız: ${err.message}`, "error");
    showNotification(`❌ Temizleme Hatası: ${err.message}`);
  } finally {
    geminiPlanRunning = false;
    toggleCleanButtonState(false);
    if (thinkingBar) thinkingBar.style.display = "none";
  }
}

async function loadPlanChannelsDropdown() {
  const select = document.getElementById("gemini-plan-channel-select");
  if (!select) return;
  
  select.innerHTML = "<option value=''>Kanallar yükleniyor...</option>";
  
  try {
    const apiUrl = await getApiUrl();
    const res = await fetchFromBackground(`${apiUrl}/api/channels-and-groups`);
    if (res.ok) {
      const items = await res.json();
      if (items && items.length > 0) {
        const groups = items.filter(c => c.type === "group");
        const standalones = items.filter(c => c.type !== "group");
        let html = "";
        if (groups.length > 0) {
          html += `<optgroup label="📁 Kanal Grupları (Çok Dilli)">`;
          groups.forEach(g => {
            html += `<option value="group:${g.id}">📁 ${g.name || g.id}</option>`;
          });
          html += `</optgroup>`;
        }
        if (standalones.length > 0) {
          html += `<optgroup label="📺 Tekil Kanallar">`;
          standalones.forEach(c => {
            html += `<option value="${c.id}">${c.name || c.id}</option>`;
          });
          html += `</optgroup>`;
        }
        select.innerHTML = html;
      } else {
        select.innerHTML = "<option value=''>Kanal veya grup bulunamadı.</option>";
      }
    } else {
      select.innerHTML = "<option value=''>Kanallar yüklenemedi (HTTP Hata).</option>";
    }
  } catch (err) {
    select.innerHTML = "<option value=''>Bağlantı hatası.</option>";
  }
}

async function runGeminiPlanAutomation(channelId, count, useTempChat, fullMaterials = true) {
  geminiPlanRunning = true;
  logGeminiPlan(fullMaterials 
    ? `İçerik planlama ve üretim materyalleri otomasyonu başlatıldı (${count} adet).` 
    : `İçerik planlama otomasyonu başlatıldı (${count} adet).`, "info");
  
  const thinkingBar = document.getElementById("gemini-plan-thinking-bar");
  if (thinkingBar) thinkingBar.style.display = "block";
  
  try {
    const apiUrl = await getApiUrl();
    const isGroup = channelId.startsWith("group:");
    const targetId = isGroup ? channelId.replace("group:", "") : channelId;
    
    // 1. Zihin haritası veya grup bilgisi
    logGeminiPlan(isGroup ? "Grup bilgileri ve planı backend'den alınıyor..." : "Kanalın zihin haritası backend'den alınıyor...", "info");
    let mindMapData = {};
    if (!isGroup) {
      const mindMapRes = await fetchFromBackground(`${apiUrl}/api/channels/${targetId}/mind-map`);
      if (mindMapRes.ok) mindMapData = await mindMapRes.json();
    }
    
    // 1.5. Mevcut içerik planını çek
    let planData = null;
    try {
      const planUrl = isGroup ? `${apiUrl}/api/groups/${targetId}/plan` : `${apiUrl}/api/channels/${targetId}/plan`;
      const planRes = await fetchFromBackground(planUrl);
      if (planRes.ok) planData = await planRes.json();
    } catch (e) {
      logGeminiPlan("Uyarı: Mevcut içerik planı alınamadı, devam ediliyor...", "warning");
    }

    const planArray = (planData && Array.isArray(planData.plan)) ? planData.plan : [];
    const existingTitles = planArray
      .map(item => (item.baslik || item.konu || "").trim())
      .filter(t => t.length > 0);
    
    // 2. Ayarları sorgula
    let channelLanguage = "tr";
    let channelCategory = "space";
    let channelName = "";
    let customTopics = [];
    let channelObj = null;
    
    try {
      if (isGroup) {
        const grpRes = await fetchFromBackground(`${apiUrl}/api/groups`);
        if (grpRes.ok) {
          const groupsList = await grpRes.json();
          const grp = groupsList.find(g => g.id === targetId);
          if (grp) {
            channelCategory = grp.topic_category || "reddit_stories";
            channelName = grp.name;
            channelLanguage = (grp.languages && grp.languages[0]) || "tr";
          }
        }
      } else {
        const channelsRes = await fetchFromBackground(`${apiUrl}/api/channels`);
        if (channelsRes.ok) {
          const channelsList = await channelsRes.json();
          const ch = channelsList.find(c => c.channel_id === targetId);
          if (ch) {
            channelObj = ch;
            if (ch.language) channelLanguage = ch.language;
            if (ch.topic_category) channelCategory = ch.topic_category.toLowerCase().trim();
            if (ch.name) channelName = ch.name;
            if (ch.custom_topics && Array.isArray(ch.custom_topics)) customTopics = ch.custom_topics;
          }
        }
      }
    } catch (infoErr) {
      logGeminiPlan(`Kanal/Grup detayları alınırken uyarı: ${infoErr.message}, varsayılanlarla devam ediliyor...`, "warning");
    }

    const catLower = (channelCategory || "").toLowerCase().trim();
    const isTrLang = (channelLanguage || "tr").toLowerCase().startsWith("tr");
    const cfgDuration = channelObj && channelObj.edit_options && parseInt(channelObj.edit_options.video_duration);
    const isCrayonEssay = (catLower === "crayon_combat" || catLower === "military" || catLower === "military_tech" || catLower.includes("combat") || catLower.includes("crayon"));
    const isLongVideo = !isGroup && channelObj && (channelObj.shorts_mode === false || (cfgDuration && cfgDuration > 90) || isCrayonEssay);
    
    let targetScenes = "4 ila 6";
    let durationDesc = "yaklaşık 45-50 saniye";
    if (isLongVideo) {
      if (isCrayonEssay || (cfgDuration && cfgDuration >= 600)) {
        targetScenes = "32 ila 42";
        durationDesc = "KESİNLİKLE EN AZ 11 DAKİKA, EN FAZLA 15 DAKİKA (yaklaşık 12-14 dakika / 720-840 saniye, ~2200-2500 kelime)";
      } else {
        targetScenes = "20 ila 25";
        durationDesc = "yaklaşık 5 ila 6 dakika (300 saniye)";
      }
    }
    const planOnlyFirst = isLongVideo && fullMaterials;
    const effectiveFullMaterials = fullMaterials && !planOnlyFirst;
    
    // 3. Sohbet modunu ayarla
    logGeminiPlan(useTempChat ? "Geçici sohbet modu kontrol ediliyor..." : "Normal sohbet modu kontrol ediliyor...", "info");
    await toggleTemporaryChatIfNeeded(useTempChat);
    
    // 4. Prompt hazırla
    logGeminiPlan(effectiveFullMaterials 
      ? "İçerik planı + tam senaryo üretim promptu hazırlanıyor..." 
      : (planOnlyFirst ? (isCrayonEssay ? `Crayon Combat (11-15 dk, 32-42 sahne, ${count} konu) için konu planlama promptu hazırlanıyor...` : `Uzun video (${count} konu, 20-25 sahne) için konu planlama promptu hazırlanıyor...`) : "Planlama promptu hazırlanıyor..."), "info");
    const mindMapJson = JSON.stringify(mindMapData, null, 2);
    
    let existingTitlesPrompt = "";
    if (existingTitles.length > 0) {
      existingTitlesPrompt = `\n\nMevcut İçerik Planındaki (Zaten Planlanmış/Üretilmiş) Konular:\n` + 
        existingTitles.map(t => `- ${t}`).join("\n") + 
        `\n\nÖNEMLİ KURAL: Yukarıda listelenen mevcut içerik planındaki konularla ÇAKIŞMAYAN, onlara benzer veya aynı olmayan, tamamen yeni ve benzersiz konular üretmelisin. Bu konuların kopyasını veya çok benzerini kesinlikle önerme.`;
    }

    let customTopicsPrompt = "";
    if (customTopics.length > 0) {
      customTopicsPrompt = `\n\nKanalın Özel İlgi Alanları / Odak Konuları:\n` + 
        customTopics.map(t => `- ${t}`).join("\n");
    }

    let categoryGuide = "";
    if (catLower === "whatsapp_stories" || catLower === "whatsapp" || catLower === "whatsapp_chat") {
      if (isTrLang) {
        categoryGuide = `
KANAL KONSEPTİ VE KATEGORİSİ: "WhatsApp Mesajlaşma Hikayeleri (Viral Chat Diyalogları, Komedi, Durum Mizahı)"
Bu kanal, iki veya daha fazla kişi arasında geçen WhatsApp yazışmalarını, şoke edici mesajlaşmaları, komik ve absürt diyalogları, aile ve komşuluk krizlerini dikey video formatında sunan son derece viral bir YouTube Shorts kanalıdır.

İSLAMİ & HELAL İÇERİK ANLAYIŞI: Kesinlikle sevgili, flört, aldatma, zina, gayrimeşru ilişki, küfür veya argo unsuru ÜRETME. Komedi ve absürtlük (aile, apartman, esnaf, halısaha vb.) odaklı olmalıdır.`;
      } else {
        categoryGuide = `
CHANNEL CONCEPT & CATEGORY: "WhatsApp Text Message Stories (Viral Chat Banter, Comedy & Absurd Twists)"
Viral simulated WhatsApp conversation Shorts with hilarious clean banter, roommate disputes, family moments and wacky twists in ${channelLanguage}. Strictly NO dating/romance or indecency.`;
      }
    } else if (catLower === "reddit_stories" || catLower === "reddit") {
      categoryGuide = `
KANAL KONSEPTİ VE KATEGORİSİ: "Reddit Hikayeleri & İtiraflar (AskReddit / Gizem / Şok Edici İtiraf / AITAH)"
VİRAL KANCA VE IN MEDIA RES FORMÜLÜ (ZORUNLU):
- Her başlık ('baslik') mutlaka 1. tekil şahıs ağzından, olayın şok edici doruk noktasıyla başlayan, kaydırmayı anında durduran merak boşluğu (curiosity gap) kancası olmalıdır! (Örn: "22 Yaşımda Ailemin 15 Yıllık Organize Kaçakçılık Çetesini Öğrendim (AITAH?)", "Ortak Hesabımızdaki 250 Bin TL'yi Eşimin Ailesi Maldivler Tatilinde Harcamış!", "Düğünüme 2 Saat Kala Nişanlımın Gizli Telefonunu Buldum...").
- "Bir Aile Sırrı", "Geçmişin İtirafı" gibi yavaş, klasik ve pasif başlıklar KESİNLİKLE YASAKTIR.
- Sahne 1 anlatımı ('narration') da giriş yapmadan DOĞRUDAN bu şok edici itirafın/olayın merkezinden başlamalıdır.`;
    } else if (catLower === "aviation") {
      categoryGuide = `
KANAL KONSEPTİ VE KATEGORİSİ: "Havacılık Olayları & Kara Kutu ATC Telsiz Kayıtları (Black Box Audio)"
Gerçek dünyada yaşanmış resmi uçuş acil durumları, kokpit ve kule telsiz diyalogları ve kaza kırım analizleri.`;
    } else if (catLower === "crayon_combat" || catLower === "military" || catLower === "military_tech" || catLower.includes("combat") || catLower.includes("crayon")) {
      if (isTrLang) {
        categoryGuide = `
KANAL KONSEPTİ VE KATEGORİSİ: "Crayon Combat (Askeri Araçlar, Savunma Sanayii Hicvi & Çöp Adam Animasyonu)"
Kurzgesagt, OverSimplified ve Crayon Capital tarzında askeri teknoloji analizleri, F-35/B-21/Abrams gibi araçların taktik blueprint şemaları, çılgın bütçe aşımları ve savunma sanayii skandalları (Açgözlü Savunma CEO'su, Panikleyen Pentagon Generali, Terleyen Test Pilotu hicvi). Yüksek tıklanma (CTR) odaklı, merak uyandıran video kurguları.`;
      } else {
        categoryGuide = `
CHANNEL CONCEPT & CATEGORY: "Crayon Combat / Tactical Crayon (Military Hardware, Defense Contractor Satire & Stickman Animation)"
In the viral YouTube video essay style of Crayon Capital, OverSimplified, and Perun. Forensic military engineering breakdowns of fighter jets, tanks, warships, and weapons programs combined with biting defense budget satire (screaming Pentagon generals over budget overruns, smug defense contractor CEOs with money bags, sweating test pilots, technical blueprint dimension callouts, and tactical HUD radar overlays). High-CTR titles highlighting shocking costs, engineering blunders, and combat physics.`;
      }
    } else {
      categoryGuide = `
KANAL KONSEPTİ VE KATEGORİSİ: "${(channelCategory || "Genel").toUpperCase()}"
"${channelCategory}" nişinde özgün, merak uyandırıcı ve yüksek izlenme potansiyeline sahip YouTube videoları.`;
    }

    let promptText = "";

    if (effectiveFullMaterials) {
      if (isCrayonEssay) {
        promptText = isTrLang
          ? `Sen YouTube askeri teknoloji, savunma sanayii ve video essay mimarısın.
Aşağıda bilgileri verilen YouTube kanalı için tam olarak ${count} adet yeni, özgün, viral askeri araç konusu VE HER BİRİNİN EKSİKSİZ CRAYON COMBAT VİDEO ESSAY SENARYO MATERYALLERİNİ (script: başlık, açıklama, etiketler, araç bilgileri, teknik özellikler, 4 hiciv arketipi replikleri ve taktik blueprint/çöp adam görsel promptları) üretmeni istiyorum.

ÖNEMLİ VE TAVİZSİZ KURALLAR:
1. SÜRE VE SAHNE KURALI (KRİTİK): Her bir içerik için KESİNLİKLE EN AZ 32, EN FAZLA 42 SAHNE üret. Toplam anlatım süresi KESİNLİKLE 11 ila 15 dakika arasında (~2200-2500 kelime) olmalıdır. 32 sahneden az KESİNLİKLE ÜRETME.
2. AÇIKLAMA VE ETİKETLER (ZORUNLU): 'description' (150-250 kelimelik zengin YouTube açıklaması, araç bilgileri ve #hashtag'ler) ve 'tags' (12-15 adet zengin etiket) alanları %100 ZORUNLUDUR. Asla boş bırakma.
3. HİCİV KARAKTERLERİ: Her sahnede 4 hiciv arketipinden birini ([DEFENSE_CEO], [GENERAL], [PILOT], [SPY]) ve komik bir repliğini ('character_quote') dahil et.
4. GÖRSELLER: "blueprint_spec" (taktik cyan blueprint teknik şeması) veya "stickman_reaction" (beyaz fonda dış hatları kalın karikatür çöp adam) görsel tiplerini kullan.
5. Yanıtını KESİNLİKLE SADECE geçerli bir JSON array formatında ver. Başka hiçbir açıklama veya markdown ekleme.

Kanal / Grup Adı: ${channelName || targetId}
Kategori: ${channelCategory}
Yayın Dili: ${channelLanguage}
${categoryGuide}
${customTopicsPrompt}
${existingTitlesPrompt}

HER BİR İÇERİK İÇİN DÖNÜLECEK KESİN JSON ŞEMASI:
[
  {
    "baslik": "Askeri araç video başlığı (Örn: F-35: 1.7 Trilyon Dolarlık Uçan iPhone)",
    "konu": "Ana araç veya askeri skandal konusu",
    "yonergeler": "Kurgu ve animasyon yönergeleri",
    "script": {
      "title": "Askeri hiciv başlığı (Örn: F-35: 1.7 Trilyon Dolarlık Uçan iPhone)",
      "description": "Kapsamlı YouTube video açıklaması (150-250 kelime). Aracın bütçe aşımlarını, teknik skandallarını, izleyiciye tartışma sorusunu ve hashtagleri içerir (#TacticalCrayon #AskeriTeknoloji #SavunmaSanayii #CrayonCombat)",
      "tags": ["Tactical Crayon", "Askeri Teknoloji", "Savunma Sanayii", "Mühendislik", "Pentagon", "Askeri Bütçe", "Savaş Uçakları", "Crayon Combat", "Hiciv", "Belgesel"],
      "keywords": ["tactical crayon", "askeri hiciv", "savunma sanayii", "askeri teknoloji", "crayon combat"],
      "vehicle_name": "Resmi Askeri Araç Adı (Örn: Lockheed Martin F-35 Lightning II)",
      "vehicle_type": "5. Nesil Hayalet Avcı Uçağı",
      "key_specs": {
        "unit_cost": "109 Milyon Dolar",
        "program_cost": "1.7 Trilyon Dolar",
        "top_speed": "Mach 1.6",
        "primary_flaw": "Kask ekranı boyun ağrısına ve yazılım kilitlenmesine yol açıyor"
      },
      "style_prompt": "Crayon Combat vector cartoon stick figures, dark cyan tactical blueprint schematics, high contrast military briefing",
      "scenes": [
        {
          "scene_num": 1,
          "narration": "1. Sahnenin sürükleyici anlatım metni (~55-70 kelime, ${channelLanguage} dilinde)",
          "character": "DEFENSE_CEO",
          "character_quote": "Bize güvenin generalim, bu uçak Mach 2 hızında espresso bile yapıyor!",
          "visual_type": "stickman_reaction",
          "image_prompt": "Defense contractor CEO in a sharp black suit holding giant sack of cash with dollar signs in his eyes, clean vector cartoon stick figure on solid white background",
          "emotion": "satirical"
        },
        {
          "scene_num": 2,
          "narration": "2. Sahnenin teknik anlatım metni (~55-70 kelime, ${channelLanguage} dilinde)",
          "character": "GENERAL",
          "character_quote": "Tek bir titanyum vida nasıl 42 bin dolar olabilir?!",
          "visual_type": "blueprint_spec",
          "image_prompt": "Detailed technical blueprint schematic of stealth fighter jet showing exploded parts and measurement callouts on dark cyan tactical grid",
          "emotion": "shocked"
        }
      ]
    }
  }
]

Zihin Haritası Verileri:
${mindMapJson}`
          : `You are a senior military tech documentary writer and satire video essay architect.
Generate exactly ${count} unique, viral military hardware breakdown topics AND COMPLETE CRAYON COMBAT VIDEO ESSAY SCRIPTS for the channel below.

CRITICAL & UNCOMPROMISING RULES:
1. DURATION & SCENES (STRICT): Provide STRICTLY between 32 and 42 scenes per topic. Total spoken narration MUST be strictly between 11 and 15 minutes (approx 2,100 to 2,500 words total across all scenes). NEVER generate fewer than 32 scenes!
2. MANDATORY DESCRIPTION & TAGS: The 'description' (150-250 words with vehicle intel & hashtags) and 'tags' (12-15 items) fields are 100% MANDATORY in the JSON output. Never leave them empty or omit them.
3. CHARACTER REACTIONS: Incorporate character reactions from the 4 satirical archetypes: [DEFENSE_CEO], [GENERAL], [PILOT], [SPY] along with their 'character_quote'.
4. VISUAL TYPES: Alternate between "blueprint_spec" (technical HUD / blueprint schematics) and "stickman_reaction" (expressive cartoon stick figures on pure white background).
5. Respond ONLY with a valid JSON array. No markdown fences, no commentary.

Channel / Group Name: ${channelName || targetId}
Category: ${channelCategory}
Language: ${channelLanguage}
${categoryGuide}
${customTopicsPrompt}
${existingTitlesPrompt}

STRICT JSON SCHEMA FOR EACH TOPIC:
[
  {
    "baslik": "Topic title in ${channelLanguage} (e.g. 'F-35: The $1.7 Trillion Flying iPhone')",
    "konu": "Core military vehicle or defense budget scandal",
    "yonergeler": "Animation and script guidelines",
    "script": {
      "title": "Satirical military tech video title (e.g. 'F-35: The $1.7 Trillion Flying iPhone')",
      "description": "Comprehensive, high-CTR YouTube video description (150-250 words) detailing the vehicle specs, funny premise, discussion question, and 6-8 trending hashtags (#TacticalCrayon #MilitaryTech #DefenseSatire #Pentagon #VideoEssay)",
      "tags": ["Tactical Crayon", "Military Tech", "Crayon Combat", "Defense Contractor", "Pentagon", "Military Budget", "Engineering Breakdown", "Video Essay", "Military Documentary", "Fighter Jet", "Weapons", "Warfare", "Satire"],
      "keywords": ["tactical crayon", "military satire", "defense spending", "pentagon budget", "military hardware", "crayon combat"],
      "vehicle_name": "Official Military Designation (e.g. Lockheed Martin F-35 Lightning II)",
      "vehicle_type": "5th Gen Stealth Multi-role Fighter",
      "key_specs": {
        "unit_cost": "$109 Million",
        "program_cost": "$1.7 Trillion",
        "top_speed": "Mach 1.6",
        "primary_flaw": "Helmet display causes neck strain & software freezes"
      },
      "style_prompt": "Crayon Combat vector cartoon stick figures, dark cyan tactical blueprint schematics, high contrast military briefing",
      "scenes": [
        {
          "scene_num": 1,
          "narration": "Compelling scene narration text in ${channelLanguage} (~55-70 words)...",
          "character": "DEFENSE_CEO",
          "character_quote": "Trust us General, this jet practically prints freedom at Mach 2!",
          "visual_type": "stickman_reaction",
          "image_prompt": "Defense contractor CEO in a sharp dark suit with dollar signs in his eyes, smug grin, holding giant sack of cash, clean vector cartoon stick figure on solid white background",
          "emotion": "satirical"
        },
        {
          "scene_num": 2,
          "narration": "Compelling scene narration text in ${channelLanguage} (~55-70 words)...",
          "character": "GENERAL",
          "character_quote": "Why does a single titanium washer cost forty-two thousand dollars?!",
          "visual_type": "blueprint_spec",
          "image_prompt": "Detailed technical blueprint schematic of stealth fighter jet showing exploded parts and measurement callouts on dark cyan tactical grid",
          "emotion": "shocked"
        }
      ]
    }
  }
]

Provide exactly ${targetScenes} scenes per topic (total duration ${durationDesc}). Respond ONLY with a valid JSON array. No markdown fences, no commentary.

Mind Map Data:
${mindMapJson}`;
      } else {
        promptText = isTrLang
          ? `Sen YouTube içerik planlama ve video senaryo mimarısın.
Aşağıda bilgileri verilen YouTube kanalı/grubu için tam olarak ${count} adet yeni, özgün, viral içerik konusu VE HER BİRİNİN EKSİKSİZ VİDEO SENARYO MATERYALLERİNİ (script: başlık, açıklama, etiketler, görsel stili, sahne sahne anlatım metinleri ve Stable Diffusion görsel promptları) üretmeni istiyorum.

Kanal / Grup Adı: ${channelName || targetId}
Kategori: ${channelCategory}
Yayın Dili: ${channelLanguage}
${categoryGuide}
${customTopicsPrompt}
${existingTitlesPrompt}

HER BİR İÇERİK İÇİN DÖNÜLECEK KESİN JSON ŞEMASI:
[
  {
    "baslik": "Video başlığı / soru (${channelLanguage} dilinde)",
    "konu": "Ana kriz / konu başlığı (${channelLanguage} dilinde)",
    "yonergeler": "Görsel ve kurgu yönergeleri (${channelLanguage} dilinde)",
    "script": {
      "title": "Video başlığı (SEO uyumlu, merak uyandırıcı, ${channelLanguage} dilinde)",
      "description": "Video açıklaması (120-200 kelime, hashtagler ile birlikte, ${channelLanguage} dilinde)",
      "tags": ["etiket1", "etiket2", "etiket3", "etiket4"],
      "keywords": ["anahtar1", "anahtar2"],
      "style_prompt": "Tüm sahnelere uygulanacak tutarlı İngilizce görsel stili (Örn: Photorealistic cinematic documentary footage, 8k resolution, dramatic lighting)",
      "scenes": [
        {
          "scene_num": 1,
          "narration": "1. Sahnenin akıcı anlatım metni (${channelLanguage} dilinde)",
          "image_prompt": "Ayrıntılı İngilizce Stable Diffusion görsel promptu (Örn: Cockpit view of Boeing 747 in dark stormy clouds, instrument glow, ultra realistic 8k)",
          "emotion": "dramatic"
        },
        {
          "scene_num": 2,
          "narration": "2. Sahnenin akıcı anlatım metni (${channelLanguage} dilinde)",
          "image_prompt": "Ayrıntılı İngilizce görsel promptu",
          "emotion": "mysterious"
        },
        {
          "scene_num": 3,
          "narration": "3. Sahnenin akıcı anlatım metni (${channelLanguage} dilinde)",
          "image_prompt": "Ayrıntılı İngilizce görsel promptu",
          "emotion": "excited"
        },
        {
          "scene_num": 4,
          "narration": "4. Sahnenin final vuruş anlatım metni (${channelLanguage} dilinde)",
          "image_prompt": "Ayrıntılı İngilizce görsel promptu",
          "emotion": "dramatic"
        }
      ]
    }
  }
]

ÖNEMLİ KURAL: Her içerik için tam ${targetScenes} sahne üret (${durationDesc} süresinde). Açıklama ('description') ve etiketler ('tags') alanları %100 zorunludur. Yanıtını KESİNLİKLE SADECE geçerli bir JSON array formatında ver. Başka hiçbir açıklama veya markdown ekleme.

Zihin Haritası Verileri:
${mindMapJson}`
          : `You are a senior YouTube content strategist and video script architect.
Generate exactly ${count} unique, viral, high-retention video topics AND COMPLETE VIDEO PRODUCTION SCRIPTS (title, description, tags, keywords, style_prompt, and full scene-by-scene narrations and Stable Diffusion image prompts) for the channel below.

Channel / Group Name: ${channelName || targetId}
Category: ${channelCategory}
Language: ${channelLanguage}
${categoryGuide}
${customTopicsPrompt}
${existingTitlesPrompt}

STRICT JSON SCHEMA FOR EACH TOPIC:
[
  {
    "baslik": "Topic title in ${channelLanguage}",
    "konu": "Core topic subject in ${channelLanguage}",
    "yonergeler": "Detailed plot twist and production guidelines in ${channelLanguage}",
    "script": {
      "title": "Catchy SEO video title in ${channelLanguage}",
      "description": "Detailed video description with tags in ${channelLanguage}",
      "tags": ["tag1", "tag2", "tag3"],
      "keywords": ["keyword1", "keyword2"],
      "style_prompt": "Consistent visual style prompt in English (e.g., Cinematic photorealistic documentary, 8k, dramatic lighting)",
      "scenes": [
        {
          "scene_num": 1,
          "narration": "Compelling scene narration text in ${channelLanguage}",
          "image_prompt": "Detailed English Stable Diffusion image prompt for this scene",
          "emotion": "dramatic"
        },
        {
          "scene_num": 2,
          "narration": "Compelling scene narration text in ${channelLanguage}",
          "image_prompt": "Detailed English Stable Diffusion image prompt for this scene",
          "emotion": "mysterious"
        },
        {
          "scene_num": 3,
          "narration": "Compelling scene narration text in ${channelLanguage}",
          "image_prompt": "Detailed English Stable Diffusion image prompt for this scene",
          "emotion": "excited"
        },
        {
          "scene_num": 4,
          "narration": "Final climax narration text in ${channelLanguage}",
          "image_prompt": "Detailed English Stable Diffusion image prompt for this scene",
          "emotion": "dramatic"
        }
      ]
    }
  }
]

Provide exactly ${targetScenes} scenes per topic (total duration ${durationDesc}). The 'description' and 'tags' fields are mandatory. Respond ONLY with a valid JSON array. No markdown fences, no commentary.

Mind Map Data:
${mindMapJson}`;
      }
    } else {
      // Sadece konu planı
      promptText = isTrLang
        ? `Sen YouTube içerik planlama ve büyüme uzmanısın.
Aşağıda bilgileri verilen YouTube kanalı/grubu için tam olarak ${count} adet yeni, özgün, viral ve yüksek etkileşimli içerik fikri (başlığı) üretmeni istiyorum.

Kanal / Grup Adı: ${channelName || targetId}
Kategori: ${channelCategory}
Yayın Dili: ${channelLanguage}
${categoryGuide}
${customTopicsPrompt}
${existingTitlesPrompt}

Her bir fikir için:
- baslik: Video başlığı/konusu (${channelLanguage} dilinde)
- yonergeler: AI video oluşturucu için görsel ve anlatım yönergeleri (${channelLanguage} dilinde)

Yanıtını KESİNLİKLE SADECE geçerli bir JSON array formatında ver:
[
  {
    "baslik": "fikir başlığı / soru",
    "yonergeler": "detaylı görsel ve anlatım yönergeleri"
  }
]

Zihin Haritası Verileri:
${mindMapJson}`
        : `Generate exactly ${count} unique topic ideas for channel ${channelName || targetId}.
Category: ${channelCategory}, Language: ${channelLanguage}
${categoryGuide}
${customTopicsPrompt}
${existingTitlesPrompt}

JSON Format:
[
  {
    "baslik": "topic title in ${channelLanguage}",
    "yonergeler": "guidelines in ${channelLanguage}"
  }
]
Mind Map: ${mindMapJson}`;
    }

    // 5. Promptu yaz ve gönder
    logGeminiPlan("Prompt Gemini'a yazılıyor...", "info");
    const inputArea = await waitForPromptInput();
    if (!inputArea) throw new Error("Prompt giriş alanı bulunamadı.");

    simulateTyping(inputArea, promptText);
    await new Promise(r => setTimeout(r, 500));

    logGeminiPlan("İçerik planı talebi gönderildi. Yanıt bekleniyor...", "info");
    const initialTurns = getTurnCount();
    const clickSuccess = clickSendButton();
    if (!clickSuccess) throw new Error("Gönder butonu bulunamadı.");
    await new Promise(r => setTimeout(r, 1000));

    // 6. Gemini yanıtını bekle
    await waitForGeminiGeneration(initialTurns);
    logGeminiPlan("Gemini yanıtı alındı.", "success");

    const rawText = getLastResponseText();
    let topicsList = parseMaterialsOrTopicsResponse(rawText);
    
    if (!topicsList || !Array.isArray(topicsList) || topicsList.length === 0) {
      logGeminiPlan("JSON Ayrıştırma hatası! Ham veri console loga yazıldı.", "error");
      console.log("[GEMINI-PLAN-RAW-TEXT]:", rawText);
      throw new Error("Gemini geçerli bir JSON array yanıtı üretmedi.");
    }
    
    logGeminiPlan(`Ayrıştırıldı. Toplam ${topicsList.length} içerik ve üretim materyali sisteme aktarılıyor...`, "success");
    
    // 7. Backend'e göndererek planı veya hem planı hem "Üretim Metaryalleri"ni kaydet
    const importUrl = (!fullMaterials || planOnlyFirst)
      ? (isGroup ? `${apiUrl}/api/groups/${targetId}/plan/import` : `${apiUrl}/api/channels/${targetId}/plan/import`)
      : (isGroup ? `${apiUrl}/api/groups/${targetId}/plan-and-materials` : `${apiUrl}/api/channels/${targetId}/plan-and-materials`);

    let importRes = await fetchFromBackground(importUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topics: topicsList })
    });
    
    if (!importRes.ok && fullMaterials && !planOnlyFirst) {
      // Geriye dönük uyumluluk: plan-and-materials endpointi yanıt vermezse standart import dene
      logGeminiPlan("plan-and-materials yanıt vermedi, standart plana aktarılıyor...", "warning");
      const fallbackUrl = isGroup ? `${apiUrl}/api/groups/${targetId}/plan/import` : `${apiUrl}/api/channels/${targetId}/plan/import`;
      importRes = await fetchFromBackground(fallbackUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topics: topicsList })
      });
    }

    if (importRes.ok) {
      if (planOnlyFirst) {
        logGeminiPlan(`✓ ${topicsList.length} adet uzun video konusu içerik planına kaydedildi.`, "success");
        logGeminiPlan(`Şimdi her konu için 20-25 sahnelik resmi senaryo ve görsel materyalleri sırayla üretiliyor...`, "info");
        await runGeminiRetroactiveMaterialsAutomation(channelId, topicsList.length, useTempChat);
        return;
      }
      const resultData = await importRes.json();
      const matsCount = resultData.materials_count || resultData.count || topicsList.length;
      logGeminiPlan(`Başarılı! ${topicsList.length} konu planlandı ve ${matsCount} adet tam senaryo paketi "Üretim Metaryalleri" klasörüne kaydedildi! 🎉`, "success");
      logGeminiPlan(`👉 Artık videoları üretmek için sistem paneline (Dashboard) geçebilir, "Üretim Materyalleri" sayfasından Tekli veya Kuyruk olarak başlatabilirsiniz!`, "info");
      showNotification(`🎉 ${matsCount} Video Üretim Materyali 'Üretim Metaryalleri'ne Kaydedildi!`);
    } else {
      const errText = await importRes.text().catch(() => "Bilinmeyen backend hatası");
      throw new Error(`Backend içe aktarma hatası: ${errText}`);
    }
    
  } catch (err) {
    logGeminiPlan(`Planlama başarısız: ${err.message}`, "error");
    showNotification(`❌ Planlama Hatası: ${err.message}`);
  } finally {
    geminiPlanRunning = false;
    togglePlanStartButtonState(false);
    if (thinkingBar) thinkingBar.style.display = "none";
  }
}

function buildRetroactivePrompt(channel, items) {
  const channelName = channel.name || channel.channel_id;
  const channelLanguage = channel.language || "tr";
  const channelCategory = (channel.topic_category || "aviation").toLowerCase().trim();
  const isTrLang = channelLanguage.toLowerCase().startsWith("tr");
  const cfgDuration = channel && channel.edit_options && parseInt(channel.edit_options.video_duration);
  const isCrayonEssay = (channelCategory === "crayon_combat" || channelCategory === "military" || channelCategory === "military_tech" || channelCategory.includes("combat") || channelCategory.includes("crayon"));
  const isLongVideo = (channel.shorts_mode === false) || (cfgDuration && cfgDuration > 90) || isCrayonEssay;
  
  let targetScenes = "4 ila 6";
  let durationDesc = "yaklaşık 45-50 saniye";
  if (isLongVideo) {
    if (isCrayonEssay || (cfgDuration && cfgDuration >= 600)) {
      targetScenes = "32 ila 42";
      durationDesc = "KESİNLİKLE EN AZ 11 DAKİKA, EN FAZLA 15 DAKİKA (yaklaşık 12-14 dakika / 720-840 saniye, ~2200-2500 kelime)";
    } else {
      targetScenes = "20 ila 25";
      durationDesc = "yaklaşık 5 ila 6 dakika (300 saniye)";
    }
  }

  let categoryGuide = "";
  if (channelCategory === "whatsapp_stories" || channelCategory === "whatsapp" || channelCategory === "whatsapp_chat") {
    if (isTrLang) {
      categoryGuide = `\nKANAL KONSEPTİ VE KATEGORİSİ: "WhatsApp Mesajlaşma Hikayeleri (Viral Chat Diyalogları, Komedi, Durum Mizahı)"\nTemiz, esprili ve absürt aile/apartman/arkadaş mesajlaşmaları. Kesinlikle argo veya gayrimeşru flört unsuru üretme.`;
    } else {
      categoryGuide = `\nCHANNEL CONCEPT & CATEGORY: "WhatsApp Text Message Stories (Viral Chat Banter, Comedy & Absurd Twists)"\nViral simulated WhatsApp conversation Shorts with hilarious clean banter and twists.`;
    }
  } else if (channelCategory === "reddit_stories" || channelCategory === "reddit") {
    categoryGuide = `\nKANAL KONSEPTİ VE KATEGORİSİ: "Reddit Hikayeleri & İtiraflar (AskReddit / Gizem / Paranormal)"\nPopüler başlıklar, viral sorular, gizemli olaylar ve sürükleyici gerçek yaşam anlatıları.`;
  } else if (channelCategory === "aviation") {
    categoryGuide = `\nKANAL KONSEPTİ VE KATEGORİSİ: "Havacılık Olayları & Kara Kutu ATC Telsiz Kayıtları (Black Box Audio)"\nGerçek dünyada yaşanmış resmi uçuş acil durumları, kokpit ve kule telsiz diyalogları ve kaza kırım analizleri.`;
  } else if (channelCategory === "crayon_combat" || channelCategory === "military" || channelCategory === "military_tech" || channelCategory.includes("combat") || channelCategory.includes("crayon")) {
    if (isTrLang) {
      categoryGuide = `\nKANAL KONSEPTİ VE KATEGORİSİ: "Crayon Combat (Askeri Araçlar & Savunma Sanayii Hicvi - Çöp Adam Animasyonu)"\nSavaş uçakları, tanklar, taktik blueprint teknik şemaları ve savunma bütçesi hicvi (Kurzgesagt / Crayon Capital / OverSimplified tarzında).`;
    } else {
      categoryGuide = `\nCHANNEL CONCEPT & CATEGORY: "Crayon Combat / Tactical Crayon (Military Hardware & Defense Satire - Stickman Style)"\nForensic military engineering, blueprint schematics, defense contractor cost overruns, and stickman animation video essays (Crayon Capital / OverSimplified style).`;
    }
  } else {
    categoryGuide = `\nKANAL KONSEPTİ VE KATEGORİSİ: "${channelCategory.toUpperCase()}"\n"${channelCategory}" nişinde özgün, merak uyandırıcı ve yüksek izlenme potansiyeline sahip YouTube videoları.`;
  }

  const simplifiedItems = items.map(it => ({
    row_id: String(it.id || ""),
    baslik: String(it.baslik || it.konu || "").trim(),
    konu: String(it.konu || it.baslik || "").trim(),
    notlar: String(it.notlar || "").trim()
  }));

  if (isCrayonEssay) {
    if (isTrLang) {
      return `Sen YouTube askeri teknoloji, savunma sanayii ve video essay mimarısın.
Aşağıda verilen YouTube kanalı için ZATEN MEVCUT İÇERİK PLANINDA yer alan ve ID'leri belirtilen tam ${items.length} adet askeri araç/konu için EKSİKSİZ CRAYON COMBAT VİDEO ESSAY SENARYO MATERYALLERİNİ (script: başlık, açıklama, etiketler, araç bilgileri, teknik özellikler, 4 hiciv arketipi replikleri ve taktik blueprint/çöp adam görsel promptları) üretmeni istiyorum.

ÖNEMLİ VE TAVİZSİZ KURALLAR:
1. Konuların başlığını, konusunu ve 'row_id' değerlerini KESİNLİKLE DEĞİŞTİRMEDEN KORU.
2. SÜRE VE SAHNE KURALI (KRİTİK): Her bir içerik için KESİNLİKLE EN AZ 32, EN FAZLA 42 SAHNE üret. Toplam anlatım süresi KESİNLİKLE 11 ila 15 dakika arasında (~2200-2500 kelime) olmalıdır. 32 sahneden az KESİNLİKLE ÜRETME.
3. AÇIKLAMA VE ETİKETLER (ZORUNLU): 'description' (150-250 kelimelik zengin YouTube açıklaması, araç bilgileri ve #hashtag'ler) ve 'tags' (12-15 adet zengin etiket) alanları %100 ZORUNLUDUR. Asla boş bırakma.
4. HİCİV KARAKTERLERİ: Her sahnede 4 hiciv arketipinden birini ([DEFENSE_CEO], [GENERAL], [PILOT], [SPY]) ve komik bir repliğini ('character_quote') dahil et.
5. GÖRSELLER: "blueprint_spec" (taktik cyan blueprint teknik şeması) veya "stickman_reaction" (beyaz fonda dış hatları kalın karikatür çöp adam) görsel tiplerini kullan.
6. Çıktın KESİNLİKLE doğrudan '[' karakteri ile başlamalı ve ']' ile bitmelidir. SADECE geçerli bir JSON array üret.

Kanal Adı: ${channelName}
Kategori: ${channelCategory}
Yayın Dili: ${channelLanguage}
${categoryGuide}

İŞLENECEK MEVCUT KONULAR:
${JSON.stringify(simplifiedItems, null, 2)}

HER BİR KONU İÇİN DÖNÜLECEK KESİN JSON ŞEMASI:
[
  {
    "row_id": "mevcut_id",
    "baslik": "Mevcut Başlık",
    "konu": "Mevcut Konu",
    "script": {
      "title": "Askeri hiciv başlığı (Örn: F-35: 1.7 Trilyon Dolarlık Uçan iPhone)",
      "description": "Kapsamlı YouTube video açıklaması (150-250 kelime). Aracın bütçe aşımlarını, teknik skandallarını, izleyiciye tartışma sorusunu ve hashtagleri içerir (#TacticalCrayon #AskeriTeknoloji #SavunmaSanayii #CrayonCombat)",
      "tags": ["Tactical Crayon", "Askeri Teknoloji", "Savunma Sanayii", "Mühendislik", "Pentagon", "Askeri Bütçe", "Savaş Uçakları", "Crayon Combat", "Hiciv", "Belgesel"],
      "keywords": ["tactical crayon", "askeri hiciv", "savunma sanayii", "askeri teknoloji", "crayon combat"],
      "vehicle_name": "Resmi Askeri Araç Adı (Örn: Lockheed Martin F-35 Lightning II)",
      "vehicle_type": "5. Nesil Hayalet Avcı Uçağı",
      "key_specs": {
        "unit_cost": "109 Milyon Dolar",
        "program_cost": "1.7 Trilyon Dolar",
        "top_speed": "Mach 1.6",
        "primary_flaw": "Kask ekranı boyun ağrısına ve yazılım kilitlenmesine yol açıyor"
      },
      "style_prompt": "Crayon Combat vector cartoon stick figures, dark cyan tactical blueprint schematics, high contrast military briefing",
      "scenes": [
        {
          "scene_num": 1,
          "narration": "1. Sahnenin sürükleyici anlatım metni (~55-70 kelime, ${channelLanguage} dilinde)",
          "character": "DEFENSE_CEO",
          "character_quote": "Bize güvenin generalim, bu uçak Mach 2 hızında espresso bile yapıyor!",
          "visual_type": "stickman_reaction",
          "image_prompt": "Defense contractor CEO in a sharp black suit holding giant sack of cash with dollar signs in his eyes, clean vector cartoon stick figure on solid white background",
          "emotion": "satirical"
        },
        {
          "scene_num": 2,
          "narration": "2. Sahnenin teknik anlatım metni (~55-70 kelime, ${channelLanguage} dilinde)",
          "character": "GENERAL",
          "character_quote": "Tek bir titanyum vida nasıl 42 bin dolar olabilir?!",
          "visual_type": "blueprint_spec",
          "image_prompt": "Detailed technical blueprint schematic of stealth fighter jet showing exploded parts and measurement callouts on dark cyan tactical grid",
          "emotion": "shocked"
        }
      ]
    }
  }
]`;
    } else {
      return `You are a senior military tech documentary writer and satire video essay architect.
The YouTube channel below already has pre-planned topics in its content calendar.
Generate COMPLETE CRAYON COMBAT VIDEO ESSAY PRODUCTION SCRIPTS for each of the following ${items.length} EXISTING topics.

CRITICAL & UNCOMPROMISING RULES:
1. PRESERVE the exact 'row_id', 'baslik' and 'konu' values from the input list. Do not change them.
2. DURATION & SCENES (STRICT): Provide STRICTLY between 32 and 42 scenes per topic. Total spoken narration MUST be strictly between 11 and 15 minutes (approx 2,100 to 2,500 words total across all scenes). NEVER generate fewer than 32 scenes!
3. MANDATORY DESCRIPTION & TAGS: The 'description' (150-250 words with vehicle intel & hashtags) and 'tags' (12-15 items) fields are 100% MANDATORY in the JSON output. Never leave them empty or omit them.
4. CHARACTER REACTIONS: Incorporate character reactions from the 4 satirical archetypes: [DEFENSE_CEO], [GENERAL], [PILOT], [SPY] along with their 'character_quote'.
5. VISUAL TYPES: Alternate between "blueprint_spec" (technical HUD / blueprint schematics) and "stickman_reaction" (expressive cartoon stick figures on pure white background).
6. Your output MUST start directly with '[' and end with ']'. Do NOT wrap in an outer object and do NOT output any conversational preamble.

Channel Name: ${channelName}
Category: ${channelCategory}
Language: ${channelLanguage}
${categoryGuide}

EXISTING TOPICS TO PROCESS:
${JSON.stringify(simplifiedItems, null, 2)}

STRICT JSON SCHEMA FOR EACH TOPIC:
[
  {
    "row_id": "existing_id",
    "baslik": "Original Topic Title",
    "konu": "Original Topic Subject",
    "script": {
      "title": "Satirical military tech video title (e.g. 'F-35: The $1.7 Trillion Flying iPhone')",
      "description": "Comprehensive, high-CTR YouTube video description (150-250 words) detailing the vehicle specs, funny premise, discussion question, and 6-8 trending hashtags (#TacticalCrayon #MilitaryTech #DefenseSatire #Pentagon #VideoEssay)",
      "tags": ["Tactical Crayon", "Military Tech", "Crayon Combat", "Defense Contractor", "Pentagon", "Military Budget", "Engineering Breakdown", "Video Essay", "Military Documentary", "Fighter Jet", "Weapons", "Warfare", "Satire"],
      "keywords": ["tactical crayon", "military satire", "defense spending", "pentagon budget", "military hardware", "crayon combat"],
      "vehicle_name": "Official Military Designation (e.g. Lockheed Martin F-35 Lightning II)",
      "vehicle_type": "5th Gen Stealth Multi-role Fighter",
      "key_specs": {
        "unit_cost": "$109 Million",
        "program_cost": "$1.7 Trillion",
        "top_speed": "Mach 1.6",
        "primary_flaw": "Helmet display causes neck strain & software freezes"
      },
      "style_prompt": "Crayon Combat vector cartoon stick figures, dark cyan tactical blueprint schematics, high contrast military briefing",
      "scenes": [
        {
          "scene_num": 1,
          "narration": "Compelling scene narration text in ${channelLanguage} (~55-70 words)...",
          "character": "DEFENSE_CEO",
          "character_quote": "Trust us General, this jet practically prints freedom at Mach 2!",
          "visual_type": "stickman_reaction",
          "image_prompt": "Defense contractor CEO in a sharp dark suit with dollar signs in his eyes, smug grin, holding giant sack of cash, clean vector cartoon stick figure on solid white background",
          "emotion": "satirical"
        },
        {
          "scene_num": 2,
          "narration": "Compelling scene narration text in ${channelLanguage} (~55-70 words)...",
          "character": "GENERAL",
          "character_quote": "Why does a single titanium washer cost forty-two thousand dollars?!",
          "visual_type": "blueprint_spec",
          "image_prompt": "Detailed technical blueprint schematic of stealth fighter jet showing exploded parts and measurement callouts on dark cyan tactical grid",
          "emotion": "shocked"
        }
      ]
    }
  }
]`;
    }
  }

  if (isTrLang) {
    return `Sen YouTube içerik planlama ve video senaryo mimarısın.
Aşağıda verilen YouTube kanalı için ZATEN MEVCUT İÇERİK PLANINDA yer alan ve ID'leri belirtilen tam ${items.length} adet konu için EKSİKSİZ VİDEO SENARYO MATERYALLERİNİ (script: başlık, açıklama, etiketler, keywords, görsel stili, sahne sahne anlatım metinleri ve Stable Diffusion promptları) üretmeni istiyorum.

ÖNEMLİ KURALLAR:
1. Konuların başlığını, konusunu ve 'row_id' değerlerini KESİNLİKLE DEĞİŞTİRMEDEN KORU.
2. Her bir içerik için tam ${targetScenes} sahne üret (${durationDesc} süresinde kapsamlı anlatım).
3. AÇIKLAMA VE ETİKETLER (ZORUNLU): 'description' (150-250 kelimelik zengin açıklama ve hashtagler) ve 'tags' (12-15 adet etiket) alanları %100 ZORUNLUDUR. Asla boş bırakma.
4. Sahne anlatımlarını kanal dilinde (${channelLanguage}), Stable Diffusion görsel promptlarını ise detaylı İngilizce olarak hazırla.
5. Çıktın KESİNLİKLE doğrudan '[' karakteri ile başlamalı ve ']' ile bitmelidir. Dışında hiçbir wrapper nesne ({"materials": ...} gibi) veya giriş/çıkış açıklaması olmamalıdır. SADECE geçerli bir JSON array üret.

Kanal Adı: ${channelName}
Kategori: ${channelCategory}
Yayın Dili: ${channelLanguage}
${categoryGuide}

İŞLENECEK MEVCUT KONULAR:
${JSON.stringify(simplifiedItems, null, 2)}

HER BİR KONU İÇİN DÖNÜLECEK KESİN JSON ŞEMASI:
[
  {
    "row_id": "mevcut_id",
    "baslik": "Mevcut Başlık",
    "konu": "Mevcut Konu",
    "script": {
      "title": "Video başlığı (SEO uyumlu, merak uyandırıcı, ${channelLanguage} dilinde)",
      "description": "Video açıklaması (120-200 kelime, hashtagler ile birlikte, ${channelLanguage} dilinde)",
      "tags": ["etiket1", "etiket2", "etiket3", "etiket4"],
      "keywords": ["anahtar1", "anahtar2"],
      "style_prompt": "Tüm sahnelere uygulanacak tutarlı İngilizce görsel stili (Örn: Photorealistic cinematic documentary footage, 8k resolution, dramatic lighting)",
      "scenes": [
        {
          "scene_num": 1,
          "narration": "1. Sahnenin akıcı anlatım metni (${channelLanguage} dilinde)",
          "image_prompt": "Ayrıntılı İngilizce Stable Diffusion görsel promptu",
          "emotion": "dramatic"
        },
        {
          "scene_num": 2,
          "narration": "2. Sahnenin akıcı anlatım metni (${channelLanguage} dilinde)",
          "image_prompt": "Ayrıntılı İngilizce Stable Diffusion görsel promptu",
          "emotion": "mysterious"
        },
        {
          "scene_num": 3,
          "narration": "3. Sahnenin akıcı anlatım metni (${channelLanguage} dilinde)",
          "image_prompt": "Ayrıntılı İngilizce Stable Diffusion görsel promptu",
          "emotion": "excited"
        },
        {
          "scene_num": 4,
          "narration": "4. Sahnenin final anlatım metni (${channelLanguage} dilinde)",
          "image_prompt": "Ayrıntılı İngilizce Stable Diffusion görsel promptu",
          "emotion": "dramatic"
        }
      ]
    }
  }
]`;
  } else {
    return `You are a senior YouTube content strategist and video script architect.
The YouTube channel below already has pre-planned topics in its content calendar.
Generate COMPLETE VIDEO PRODUCTION SCRIPTS (title, description, tags, keywords, style_prompt, and full scene-by-scene narrations and Stable Diffusion image prompts) for each of the following ${items.length} EXISTING topics.

CRITICAL RULES:
1. PRESERVE the exact 'row_id', 'baslik' and 'konu' values from the input list. Do not change them.
2. Provide exactly ${targetScenes} scenes per topic (total spoken duration ${durationDesc}).
3. MANDATORY DESCRIPTION & TAGS: The 'description' (150-250 words with tags) and 'tags' (12-15 items) fields are 100% MANDATORY in the JSON output. Never leave them empty or omit them.
4. Narrations in ${channelLanguage}, and Stable Diffusion prompts in detailed English.
5. Your output MUST start directly with '[' and end with ']'. Do NOT wrap in an outer object (such as {"materials": [...]}) and do NOT output any conversational text.

Channel Name: ${channelName}
Category: ${channelCategory}
Language: ${channelLanguage}
${categoryGuide}

EXISTING TOPICS TO PROCESS:
${JSON.stringify(simplifiedItems, null, 2)}

STRICT JSON SCHEMA FOR EACH TOPIC:
[
  {
    "row_id": "existing_id",
    "baslik": "Original Topic Title",
    "konu": "Original Topic Subject",
    "script": {
      "title": "Catchy SEO video title in ${channelLanguage}",
      "description": "Detailed video description with hashtags in ${channelLanguage}",
      "tags": ["tag1", "tag2", "tag3"],
      "keywords": ["keyword1", "keyword2"],
      "style_prompt": "Consistent visual style prompt in English (e.g. Cinematic documentary footage, 8k, dramatic lighting)",
      "scenes": [
        {
          "scene_num": 1,
          "narration": "Compelling scene narration text in ${channelLanguage}",
          "image_prompt": "Detailed English Stable Diffusion image prompt for this scene",
          "emotion": "dramatic"
        },
        {
          "scene_num": 2,
          "narration": "Compelling scene narration text in ${channelLanguage}",
          "image_prompt": "Detailed English Stable Diffusion image prompt for this scene",
          "emotion": "mysterious"
        },
        {
          "scene_num": 3,
          "narration": "Compelling scene narration text in ${channelLanguage}",
          "image_prompt": "Detailed English Stable Diffusion image prompt for this scene",
          "emotion": "excited"
        },
        {
          "scene_num": 4,
          "narration": "Climax scene narration text in ${channelLanguage}",
          "image_prompt": "Detailed English Stable Diffusion image prompt for this scene",
          "emotion": "dramatic"
        }
      ]
    }
  }
]`;
  }
}

async function runGeminiRetroactiveMaterialsAutomation(channelId, count, useTempChat) {
  geminiPlanRunning = true;
  logGeminiPlan("Geçmişe dönük üretim materyalleri otomasyonu başlatıldı...", "info");

  const thinkingBar = document.getElementById("gemini-plan-thinking-bar");
  if (thinkingBar) thinkingBar.style.display = "block";

  try {
    const apiUrl = await getApiUrl();

    // 1. Hedef kanalları ve satırları tespit et
    let targetChannels = [];
    if (channelId === "all_active") {
      logGeminiPlan("Tüm aktif kanalların ve grupların bekleyen içerik planları çekiliyor...", "info");
      const res = await fetchFromBackground(`${apiUrl}/api/active-channels/pending-plan`);
      if (!res.ok) throw new Error("Aktif kanalların bekleyen planları alınamadı.");
      const data = await res.json();
      targetChannels = (data.channels || []).filter(c => c.pending_count > 0);
      if (targetChannels.length === 0) {
        logGeminiPlan("Tüm aktif kanalların ve grupların materyalleri zaten tam! Bekleyen konu yok. 🎉", "success");
        alert("Tüm aktif kanalların ve grupların materyalleri zaten eksiksiz hazır!");
        return;
      }
      logGeminiPlan(`Materyal bekleyen ${targetChannels.length} aktif hedef (kanal/grup) işlenecek.`, "info");
    } else {
      const isGroup = (channelId || "").startsWith("group:");
      const targetId = isGroup ? channelId.replace("group:", "") : channelId;
      logGeminiPlan(`${isGroup ? "Grubun" : "Kanalın"} (${isGroup ? targetId : channelId}) bekleyen plan satırları alınıyor...`, "info");
      
      const planEndpoint = isGroup 
        ? `${apiUrl}/api/groups/${targetId}/pending-plan?limit=${count}`
        : `${apiUrl}/api/channels/${channelId}/pending-plan?limit=${count}`;
      const res = await fetchFromBackground(planEndpoint);
      if (!res.ok) throw new Error("Bekleyen içerik planı alınamadı.");
      const data = await res.json();
      const rows = data.pending_rows || [];
      if (rows.length === 0) {
        logGeminiPlan("Bu hedefte materyali eksik olan konu bulunamadı. Tüm planlar hazır! 🎉", "success");
        alert("Bu hedefte materyali eksik olan konu bulunamadı!\n\nSeçtiğiniz hedef için mevcut içerik planındaki tüm konuların materyalleri zaten hazır durumdadır.\n\nYeni konular eklemek için 'Yeni Konular Planla' sekmesine geçip 'Planlamayı Başlat' butonuna tıklayabilirsiniz.");
        return;
      }

      let chInfo = {
        channel_id: channelId,
        is_group: isGroup,
        group_id: isGroup ? targetId : null,
        name: channelId,
        language: isGroup ? "multi" : "tr",
        topic_category: "reddit_stories"
      };

      if (isGroup) {
        try {
          const gRes = await fetchFromBackground(`${apiUrl}/api/groups`);
          if (gRes.ok) {
            const glist = await gRes.json();
            const gMatch = glist.find(g => g.id === targetId);
            if (gMatch) {
              chInfo = {
                channel_id: channelId,
                is_group: true,
                group_id: targetId,
                name: `📁 [GRUP] ${gMatch.name || targetId}`,
                topic_category: gMatch.topic_category || "reddit_stories",
                language: "multi",
                member_channels: gMatch.channel_ids || []
              };
            }
          }
        } catch {}
      } else {
        try {
          const allRes = await fetchFromBackground(`${apiUrl}/api/channels`);
          if (allRes.ok) {
            const list = await allRes.json();
            const match = list.find(c => c.channel_id === channelId);
            if (match) chInfo = { ...match, is_group: false };
          }
        } catch {}
      }

      targetChannels = [{
        ...chInfo,
        pending_count: rows.length,
        pending_rows: rows
      }];
    }

    // 2. Sohbet modunu ayarla
    logGeminiPlan(useTempChat ? "Geçici sohbet modu ayarlanıyor..." : "Normal sohbet modu kontrol ediliyor...", "info");
    await toggleTemporaryChatIfNeeded(useTempChat);

    let totalSaved = 0;

    // 3. Kanalları ve Grupları sırayla işle
    for (let i = 0; i < targetChannels.length; i++) {
      if (!geminiPlanRunning) {
        logGeminiPlan("İşlem kullanıcı tarafından durduruldu.", "error");
        break;
      }

      const chan = targetChannels[i];
      const itemsToProcess = (chan.pending_rows || []).slice(0, count);
      if (itemsToProcess.length === 0) continue;

      const isGroup = chan.is_group || (chan.channel_id || "").startsWith("group:");
      const targetId = isGroup ? (chan.group_id || chan.channel_id.replace("group:", "")) : chan.channel_id;

      const chanCat = (chan.topic_category || "").toLowerCase().trim();
      const isCrayonEssay = (chanCat === "crayon_combat" || chanCat === "military" || chanCat === "military_tech" || chanCat.includes("combat") || chanCat.includes("crayon"));
      const isLongVideo = (!isGroup) && ((chan.shorts_mode === false) || (chan.edit_options && parseInt(chan.edit_options.video_duration) > 90) || isCrayonEssay);
      const CHUNK_SIZE = (isLongVideo || isGroup) ? 1 : 2; // Gruplarda ve uzun videolarda her istemde 1 konu

      const totalChunks = Math.ceil(itemsToProcess.length / CHUNK_SIZE);
      const formatLabel = isGroup ? "Kanal Grubu (Çok Dilli)" : (isCrayonEssay ? "Crayon Combat (11-15 dk, 32-42 sahne)" : (isLongVideo ? "Uzun Video (~5-6 dk, 20-25 sahne)" : "Shorts (~45-50 sn)"));
      logGeminiPlan(`[${i + 1}/${targetChannels.length}] "${chan.name || chan.channel_id}" [${formatLabel}] için ${itemsToProcess.length} adet konu (${totalChunks} paket) işlenecek...`, "info");

      for (let c = 0; c < itemsToProcess.length; c += CHUNK_SIZE) {
        if (!geminiPlanRunning) break;
        const chunkItems = itemsToProcess.slice(c, c + CHUNK_SIZE);
        const chunkIndex = Math.floor(c / CHUNK_SIZE) + 1;

        logGeminiPlan(`"${chan.name || chan.channel_id}" - Paket ${chunkIndex}/${totalChunks} (${chunkItems.length} konu) Gemini'a gönderiliyor...`, "info");

        // Prompt hazırla:
        let promptText = "";
        if (isGroup && chunkItems.length === 1) {
          try {
            const pRes = await fetchFromBackground(`${apiUrl}/api/groups/${targetId}/plan/${chunkItems[0].id}/gemini-prompt`, { method: "POST" });
            if (pRes.ok) {
              const pData = await pRes.json();
              if (pData.prompt) {
                promptText = pData.prompt;
              }
            }
          } catch(e) {
            console.warn("[RETROACTIVE-GROUP-PROMPT-FAIL]:", e);
          }
        } else if (isLongVideo && chunkItems.length === 1) {
          try {
            const pRes = await fetchFromBackground(`${apiUrl}/api/channels/${chan.channel_id}/plan/${chunkItems[0].id}/gemini-prompt`, { method: "POST" });
            if (pRes.ok) {
              const pData = await pRes.json();
              if (pData.prompt) {
                promptText = pData.prompt;
              }
            }
          } catch(e) {
            console.warn("[RETROACTIVE-LONG-PROMPT-FAIL]:", e);
          }
        }

        if (!promptText) {
          promptText = buildRetroactivePrompt(chan, chunkItems);
        }

        // Promptu yaz ve gönder
        const inputArea = await waitForPromptInput();
        if (!inputArea) throw new Error("Prompt giriş alanı bulunamadı.");

        simulateTyping(inputArea, promptText);
        await new Promise(r => setTimeout(r, 500));

        const initialTurns = getTurnCount();
        const clickSuccess = clickSendButton();
        if (!clickSuccess) throw new Error("Gönder butonu bulunamadı.");
        await new Promise(r => setTimeout(r, 1000));

        // Yanıtı bekle
        logGeminiPlan(`Gemini'dan ${isGroup ? "çok dilli grup senaryoları" : "senaryolar ve görsel istemleri"} bekleniyor (Paket ${chunkIndex}/${totalChunks})...`, "info");
        await waitForGeminiGeneration(initialTurns);
        logGeminiPlan(`Gemini yanıtı alındı, JSON ayrıştırılıyor...`, "info");

        const rawText = getLastResponseText();
        let materialsList = parseMaterialsOrTopicsResponse(rawText, chunkItems);

        if (!materialsList || !Array.isArray(materialsList) || materialsList.length === 0) {
          logGeminiPlan(`JSON ayrıştırma hatası! Ham veri console loga yazıldı.`, "error");
          console.error("[RETROACTIVE-RAW-TEXT]:", rawText);
          throw new Error(`Gemini geçerli bir JSON yanıtı üretmedi (Paket ${chunkIndex}/${totalChunks}).`);
        }

        // Eğer grup ise materyalleri işaretle
        if (isGroup) {
          materialsList.forEach(m => {
            m.is_group = true;
            m.group_id = targetId;
            m.channel_id = `group:${targetId}`;
          });
        }

        logGeminiPlan(`Paket ${chunkIndex}/${totalChunks} (${materialsList.length} materyal) "Üretim Metaryalleri"ne kaydediliyor...`, "info");

        // Backend'e kaydet
        const saveEndpoint = isGroup 
          ? `${apiUrl}/api/groups/${targetId}/materials-for-existing-plan`
          : `${apiUrl}/api/channels/${chan.channel_id}/materials-for-existing-plan`;

        const saveRes = await fetchFromBackground(saveEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ materials: materialsList })
        });

        if (!saveRes.ok) {
          const errText = await saveRes.text().catch(() => "Bilinmeyen hata");
          throw new Error(`Kayıt hatası: ${errText}`);
        }

        const resData = await saveRes.json();
        const savedCount = resData.saved_count || materialsList.length;
        totalSaved += savedCount;
        logGeminiPlan(`✓ "${chan.name || chan.channel_id}" Paket ${chunkIndex}/${totalChunks} (${savedCount} materyal) başarıyla kaydedildi!`, "success");

        if (c + CHUNK_SIZE < itemsToProcess.length) {
          await new Promise(r => setTimeout(r, 2000));
        }
      }

      if (i < targetChannels.length - 1) {
        logGeminiPlan(`Sonraki kanala/gruba geçilmeden önce 3 saniye bekleniyor...`, "info");
        await new Promise(r => setTimeout(r, 3000));
      }
    }

    logGeminiPlan(`🎉 Tamamlandı! Toplam ${totalSaved} adet konu için eksiksiz senaryo ve görsel istemleri "Üretim Metaryalleri"ne eklendi!`, "success");
    logGeminiPlan(`👉 Sistem sayfasındaki "Üretim Materyalleri" merkezinden Tekli veya Kuyruk olarak üretime başlayabilirsiniz!`, "info");
    showNotification(`🎉 Toplam ${totalSaved} adet materyal başarıyla üretildi ve kaydedildi!`);
  } catch (err) {
    logGeminiPlan(`Geçmişe dönük üretim hatası: ${err.message}`, "error");
    showNotification(`❌ Hata: ${err.message}`);
  } finally {
    geminiPlanRunning = false;
    togglePlanStartButtonState(false);
    if (thinkingBar) thinkingBar.style.display = "none";
  }
}


// Sayfa yüklendiğinde otomasyon kurtarma tetikleyicisi
setTimeout(() => {
  if (window !== window.top) return;
  if (window.__yt_oto_recovered) return;
  if (location.href.includes("gemini.google.com") || location.href.includes("perchance.org")) {
    chrome.storage.local.get([
      "gemini_auto_active",
      "gemini_auto_mode",
      "gemini_auto_queue",
      "gemini_auto_image_provider",
      "gemini_auto_target_env",
      "gemini_auto_sync_mac",
      "gemini_auto_provider",
      "gemini_auto_channel_id",
      "gemini_auto_use_temp_chat",
      "gemini_auto_video_count",
      "gemini_auto_nasa_option",
      "gemini_auto_videos_produced",
      "gemini_auto_loop",
      "gemini_auto_custom_images",
      "gemini_auto_authuser",
      "gemini_auto_row_id",
      "gemini_auto_script_data",
      "gemini_queue_q_idx",
      "gemini_queue_v_idx",
      "gemini_queue_phase",
      "gemini_queue_row_id",
      "gemini_queue_script_data",
      "gemini_queue_custom_images",
      "gemini_queue_category",
      "gemini_queue_item",
      "gemini_queue_channel"
    ], async (data) => {
      if (data.gemini_auto_active || (location.href.includes("perchance.org") && (data.gemini_auto_script_data || data.gemini_auto_provider === "perchance"))) {
        window.__yt_oto_recovered = true;
        
        openGeminiModal();
        
        setTimeout(() => {
          toggleStartButtonState(true);
          if (data.gemini_auto_mode === "queue" && data.gemini_auto_queue && data.gemini_auto_queue.length > 0) {
            if (typeof switchGeminiTab === "function") switchGeminiTab("queue");
            runGeminiQueueAutomation(data.gemini_auto_queue, {
              useTempChat: !!data.gemini_auto_use_temp_chat,
              imgProvider: data.gemini_auto_image_provider || "gemini",
              targetEnv: data.gemini_auto_target_env || "local",
              autoSyncMac: (typeof data.gemini_auto_sync_mac === "boolean") ? data.gemini_auto_sync_mac : true,
              startQIdx: data.gemini_queue_q_idx || 0,
              startVIdx: data.gemini_queue_v_idx || 0,
              resumedPhase: data.gemini_queue_phase || "script",
              resumedRowId: data.gemini_queue_row_id || null,
              resumedScriptData: data.gemini_queue_script_data || null,
              resumedCustomImages: data.gemini_queue_custom_images || {},
              resumedCategory: data.gemini_queue_category || null,
              resumedItem: data.gemini_queue_item || null,
              resumedChannel: data.gemini_queue_channel || null
            });
          } else if (data.gemini_auto_provider === "perchance" || location.href.includes("perchance.org")) {
            runPerchanceAutomation(
              data.gemini_auto_channel_id,
              data.gemini_auto_video_count || 1,
              data.gemini_auto_loop || 0,
              data.gemini_auto_videos_produced || 0,
              data.gemini_auto_custom_images || {},
              data.gemini_auto_row_id || null,
              data.gemini_auto_script_data || null
            );
          } else {
            runGeminiAutomation(
              data.gemini_auto_channel_id,
              data.gemini_auto_use_temp_chat,
              data.gemini_auto_video_count || 1,
              data.gemini_auto_nasa_option,
              data.gemini_auto_loop || 0,
              data.gemini_auto_videos_produced || 0,
              data.gemini_auto_custom_images || {},
              data.gemini_auto_row_id || null,
              data.gemini_auto_script_data || null
            );
          }
        }, 2000);
      }
    });
  }
}, 2500);

// ── Perchance In-Frame Generator Dinleyicisi (all_frames: true) ─────────────
if (location.href.includes("perchance.org")) {
  window.addEventListener("message", async (event) => {
    if (event.data && event.data.type === "PERCHANCE_GENERATE_REQUEST") {
      const promptText = event.data.prompt;
      const sceneIndex = event.data.sceneIndex;

      // Sadece gerçek generator öğelerini içeren frame işlem yapsın
      const hasGenerator = !!document.querySelector('textarea[data-name="description"], textarea.paragraph-input, #generateButtonEl, #resultImgEl, textarea');
      if (!hasGenerator) {
        return; // Generator olmayan dış/boş frame'ler pas geçsin
      }

      try {
        const resultSrc = await performInFramePerchanceGeneration(promptText);
        const resp = {
          type: "PERCHANCE_GENERATE_RESPONSE",
          sceneIndex: sceneIndex,
          imgSrc: resultSrc,
          success: true
        };
        try { window.top.postMessage(resp, "*"); } catch(e) {}
        try { window.parent.postMessage(resp, "*"); } catch(e) {}
      } catch (err) {
        const errResp = {
          type: "PERCHANCE_GENERATE_RESPONSE",
          sceneIndex: sceneIndex,
          error: err.message,
          success: false
        };
        try { window.top.postMessage(errResp, "*"); } catch(e) {}
        try { window.parent.postMessage(errResp, "*"); } catch(e) {}
      }
    }
  });
}

function getAllAccessibleDocuments() {
  const docs = [document];
  const iframes = document.querySelectorAll('iframe');
  for (const ifr of iframes) {
    try {
      const idoc = ifr.contentDocument || ifr.contentWindow.document;
      if (idoc && !docs.includes(idoc)) {
        docs.push(idoc);
        const subIframes = idoc.querySelectorAll('iframe');
        for (const subIfr of subIframes) {
          try {
            const sdoc = subIfr.contentDocument || subIfr.contentWindow.document;
            if (sdoc && !docs.includes(sdoc)) docs.push(sdoc);
          } catch(e) {}
        }
      }
    } catch(e) {}
  }
  return docs;
}

async function performInFramePerchanceGeneration(promptText) {
  let promptEl = null;
  let btnEl = null;
  let targetDoc = document;

  const promptSelectors = [
    'textarea[data-name="description"]',
    'textarea.paragraph-input',
    'textarea[placeholder*="chinese" i]',
    'textarea',
    '#promptInput',
    '#prompt',
    '[name="prompt"]',
    'input[type="text"]',
    '[placeholder*="prompt" i]',
    '[placeholder*="describe" i]',
    '[placeholder*="type" i]'
  ];

  const btnSelectors = [
    '#generateButtonEl',
    '#generateButton',
    '#generateBtn',
    '#generate',
    'button[id*="generate" i]',
    'button[class*="generate" i]',
    'button'
  ];

  for (let attempt = 0; attempt < 35; attempt++) {
    const docs = getAllAccessibleDocuments();
    for (const doc of docs) {
      for (const sel of promptSelectors) {
        const el = doc.querySelector(sel);
        if (el && (el.offsetParent !== null || el.offsetWidth > 0)) { promptEl = el; targetDoc = doc; break; }
        if (el && !promptEl) { promptEl = el; targetDoc = doc; }
      }
      if (promptEl) {
        for (const bsel of btnSelectors) {
          const btns = doc.querySelectorAll(bsel);
          for (const b of btns) {
            const txt = (b.innerText || b.textContent || b.value || '').toLowerCase();
            if (b.id === 'generateButtonEl' || b.id === 'generateButton' || txt.includes('generate') || txt.includes('üret') || txt.includes('create')) {
              btnEl = b;
              break;
            }
          }
          if (btnEl) break;
        }
        if (!btnEl) btnEl = doc.querySelector('#generateButtonEl') || doc.querySelector('button');
      }
      if (promptEl && btnEl) break;
    }
    if (promptEl && btnEl) break;
    await new Promise(r => setTimeout(r, 400));
  }

  if (!promptEl) throw new Error("Perchance prompt giriş alanı (textarea[data-name='description']) bulunamadı.");
  if (!btnEl) throw new Error("Perchance Generate butonu (#generateButtonEl) bulunamadı.");

  const getResultImg = () => {
    const docs = getAllAccessibleDocuments();
    for (const d of docs) {
      const el = d.querySelector('#resultImgEl') || d.querySelector('img[id*="result" i]');
      if (el) return el;
    }
    return null;
  };

  const initialImg = getResultImg();
  const initialSrc = initialImg ? (initialImg.src || initialImg.getAttribute('src') || '') : '';
  const initialTitle = initialImg ? (initialImg.getAttribute('title') || '') : '';

  // 1) Description textarea'yı önce tamamen sil
  promptEl.focus();
  promptEl.value = "";
  promptEl.dispatchEvent(new Event('input', { bubbles: true }));
  promptEl.dispatchEvent(new Event('change', { bubbles: true }));
  try {
    if (typeof promptEl.oninput === 'function') {
      promptEl.oninput(new Event('input'));
    }
  } catch(e) {}
  await new Promise(r => setTimeout(r, 200));

  // 2) Yeni istem metnini yaz
  promptEl.value = promptText;
  promptEl.dispatchEvent(new Event('input', { bubbles: true }));
  promptEl.dispatchEvent(new Event('change', { bubbles: true }));
  try {
    if (typeof promptEl.oninput === 'function') {
      promptEl.oninput(new Event('input'));
    }
  } catch(e) {}
  simulateTyping(promptEl, promptText);
  await new Promise(r => setTimeout(r, 400));

  try {
    btnEl.click();
  } catch(e) {
    btnEl.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
  }

  const startTime = Date.now();
  const timeoutMs = 45000;
  let foundSrc = null;

  while (Date.now() - startTime < timeoutMs) {
    const resImg = getResultImg();
    if (resImg) {
      const src = resImg.src || resImg.getAttribute('src') || '';
      const title = resImg.getAttribute('title') || '';
      if (src && (src.startsWith('data:image') || src.includes('user-uploads.perchance.org') || src.includes('huggingface') || src.includes('perchance.org/api'))) {
        if (src !== initialSrc || (title && title !== initialTitle) || (Date.now() - startTime > 3000)) {
          foundSrc = src;
          break;
        }
      }
    }

    const docs = getAllAccessibleDocuments();
    for (const d of docs) {
      const imgs = d.querySelectorAll('img');
      for (const img of imgs) {
        const src = img.src || img.getAttribute('src') || '';
        if (!src) continue;
        const isPerchanceImg = src.startsWith('data:image') ||
                               src.includes('user-uploads.perchance.org') ||
                               src.includes('perchance.org/api') ||
                               src.includes('huggingface') ||
                               src.startsWith('blob:');
        if (isPerchanceImg && src !== initialSrc) {
          foundSrc = src;
          break;
        }
      }
      if (foundSrc) break;
    }
    if (foundSrc) break;
    await new Promise(r => setTimeout(r, 800));
  }

  if (foundSrc) {
    try {
      promptEl.value = "";
      promptEl.dispatchEvent(new Event('input', { bubbles: true }));
      promptEl.dispatchEvent(new Event('change', { bubbles: true }));
      if (typeof promptEl.oninput === 'function') {
        promptEl.oninput(new Event('input'));
      }
    } catch(e) {}
    return foundSrc;
  }

  throw new Error("Perchance görsel üretimi zaman aşımına uğradı.");
}

async function runPerchanceAutomation(channelId, videoCount, startLoop = 0, startVideosProduced = 0, resumedCustomImages = null, resumedRowId = null, resumedScriptData = null) {
  geminiRunning = true;
  const apiUrl = await getApiUrl();
  let rowId = resumedRowId;
  let scriptData = resumedScriptData;
  let customImages = resumedCustomImages || {};
  let targetChannelId = channelId;

  if (!scriptData || !rowId) {
    const storageData = await new Promise(r => chrome.storage.local.get([
      "gemini_auto_channel_id",
      "last_selected_channel",
      "gemini_auto_row_id",
      "gemini_auto_script_data",
      "gemini_auto_custom_images",
      "gemini_auto_video_count"
    ], r));

    if (!scriptData && storageData.gemini_auto_script_data) {
      scriptData = storageData.gemini_auto_script_data;
    }
    if (!rowId && storageData.gemini_auto_row_id) {
      rowId = storageData.gemini_auto_row_id;
    }
    if (!targetChannelId) {
      targetChannelId = storageData.gemini_auto_channel_id || storageData.last_selected_channel;
    }
    if (storageData.gemini_auto_custom_images && Object.keys(customImages).length === 0) {
      customImages = storageData.gemini_auto_custom_images;
    }
  }

  if (!isValidScriptData(scriptData)) {
    if (targetChannelId) {
      try {
        logGemini("Hafızadaki senaryo aranıyor, içerik planı sorgulanıyor...", "info");
        const planRes = await fetchFromBackground(`${apiUrl}/api/channels/${targetChannelId}/plan`);
        if (planRes.ok) {
          const planData = await planRes.json();
          const unproduced = (planData && Array.isArray(planData.plan)) ? planData.plan.find(p => !p.produced) : null;
          if (unproduced) {
            rowId = unproduced.id;
            const promptRes = await fetchFromBackground(`${apiUrl}/api/channels/${targetChannelId}/plan/${rowId}/gemini-prompt`, { method: "POST" });
            if (promptRes.ok) {
              const promptData = await promptRes.json();
              if (promptData.custom_script && isValidScriptData(promptData.custom_script)) {
                scriptData = promptData.custom_script;
              }
            }
          }
        }
      } catch (err) {
        console.warn("[YT-OTO] Backend plan fallback error:", err);
      }
    }
  }

  if (!isValidScriptData(scriptData)) {
    logGemini("Perchance otomasyonu için geçerli senaryo verisi bulunamadı! Lütfen önce Gemini'dan bir konu başlatın.", "error");
    geminiRunning = false;
    toggleStartButtonState(false);
    return;
  }

  logGemini(`Perchance AI Otomasyonu Devrede. Senaryo: "${getScriptTitle(scriptData)}". Geriye kalan görseller üretiliyor...`, "info");

  const thinkingBar = document.getElementById("gemini-thinking-bar");
  if (thinkingBar) thinkingBar.style.display = "block";
  const creature = document.getElementById("gemini-working-creature");
  if (creature) creature.style.display = "flex";

  try {
    let scenes = getScriptScenes(scriptData);
    let isShorts = false;
    let isWhatsapp = false;
    if (targetChannelId) {
      const chObj = geminiChannelsList.find(c => c.channel_id === targetChannelId);
      const catLower = (chObj && chObj.topic_category ? chObj.topic_category : "").toLowerCase();
      if (catLower === "whatsapp_stories" || catLower === "whatsapp" || catLower === "whatsapp_chat" || (scriptData && (scriptData.category === "whatsapp_stories" || !!scriptData.messages))) {
        isWhatsapp = true;
      }
      if (chObj && chObj.shorts_mode) isShorts = true;
    }
    const isGroupChat = isWhatsapp && detectIsGroupChat(scriptData);
    if (isWhatsapp) {
      isShorts = true;
      if (!isGroupChat && scenes.length > 1) {
        scenes = [scenes[0]];
      }
    }
    const resolution = isWhatsapp ? "512x512" : (isShorts ? "512x768" : "768x512");

    for (let i = 0; i < scenes.length; i++) {
      if (!geminiRunning) {
        logGemini("Kullanıcı tarafından durduruldu.", "error");
        break;
      }

      if (customImages[i.toString()]) {
        logGemini(`Sahne ${i+1}/${scenes.length} görseli önceden üretilmiş, geçiliyor.`, "success");
        continue;
      }

      const scene = scenes[i];
      let imagePrompt = scene.image_prompt;
      if (isWhatsapp) {
        if (isGroupChat) {
          if (!imagePrompt || imagePrompt.toLowerCase().includes("whatsapp_chat")) {
            if (i === 0) {
              imagePrompt = buildGroupAvatarPrompt(scriptData);
            } else {
              imagePrompt = buildParticipantAvatarPrompt(scene.sender_name || `Participant ${i}`, scriptData);
            }
          }
        } else {
          const contactName = (scriptData && scriptData.contact_name) || "friend";
          if (scriptData && scriptData.contact_avatar_prompt) {
            imagePrompt = refineAvatarPrompt(scriptData.contact_avatar_prompt, contactName, scriptData);
          } else if (!imagePrompt || imagePrompt.toLowerCase().includes("whatsapp_chat")) {
            imagePrompt = buildCharacterAvatarPrompt(contactName, scriptData);
          } else {
            imagePrompt = refineAvatarPrompt(imagePrompt, contactName, scriptData);
          }
        }
      }
      logGemini(`[Perchance AI] Sahne ${i+1}/${scenes.length} üretiliyor: "${imagePrompt}"`, "info");

      let success = false;
      let retries = 0;
      const maxRetries = 3;

      while (!success && retries < maxRetries) {
        if (!geminiRunning) break;
        try {
          const imgUrl = await generatePerchanceImage(imagePrompt, i);
          logGemini(`Sahne ${i+1} Perchance görseli alınıyor...`, "info");
          const base64Data = await getBase64FromUrl(imgUrl);
          saveAvatarToCustomImages(customImages, i, base64Data, isGroupChat, scene);
          chrome.storage.local.set({
            gemini_auto_custom_images: customImages
          });
          logGemini(`Sahne ${i+1} görseli Perchance AI ile başarıyla üretildi.`, "success");
          success = true;
        } catch (err) {
          logGemini(`Sahne ${i+1} Perchance üretme hatası: ${err.message} (Yeniden deneniyor ${retries+1}/${maxRetries})`, "warning");
          retries++;
          await new Promise(r => setTimeout(r, 2000));
        }
      }

      if (isWhatsapp && success) {
        if (!isGroupChat || i === scenes.length - 1) {
          logGemini("WhatsApp profil fotoğrafları başarıyla hazırlandı. Video üretimine geçiliyor...", "success");
          break;
        }
      }

      if (!success) {
        logGemini(`Sahne ${i+1} için Perchance görseli üretilemedi.`, "error");
      }
    }

    const envData = await new Promise(r => chrome.storage.local.get(["gemini_auto_target_env", "gemini_auto_sync_mac"], r));
    const targetEnv = envData.gemini_auto_target_env || "local";
    const autoSyncMac = (typeof envData.gemini_auto_sync_mac === "boolean") ? envData.gemini_auto_sync_mac : true;

    logGemini(`Tüm görseller hazır. Veriler sisteme aktarılıyor (${targetEnv === 'remote' ? 'Oracle Cloud Sunucusunda (nice 19)' : 'Lokalde'} üretim başlatılıyor)...`, "info");
    const produceRes = await produceViaBackground(
      `${apiUrl}/api/channels/${channelId}/plan/${rowId}/produce-gemini`,
      { 
        script: scriptData, 
        images: customImages,
        target_env: targetEnv,
        auto_youtube_upload: false,
        auto_sync_mac: autoSyncMac
      }
    );

    if (!produceRes.ok) {
      const errDetail = produceRes.data ? JSON.stringify(produceRes.data) : "Bilinmeyen hata";
      throw new Error(`Video üretimi başlatılamadı: ${errDetail}`);
    }
    const produceData = await produceRes.json();
    const execId = produceData.exec_id;

    logGemini(`Video üretimi başlatıldı! Görev ID: ${execId}`, "success");
    window.open(`${apiUrl}/?exec_id=${execId}`, '_blank');

  } catch (err) {
    logGemini(`Perchance Otomasyon hatası: ${err.message}`, "error");
  } finally {
    geminiRunning = false;
    toggleStartButtonState(false);
    chrome.storage.local.remove([
      "gemini_auto_active",
      "gemini_auto_provider",
      "gemini_auto_custom_images",
      "gemini_auto_row_id",
      "gemini_auto_script_data",
      "gemini_auto_logs"
    ]);
  }
}

// ══════════════════════════════════════════════════════════════════
// ── Gemini Video Kalite Kontrol & Otomatik Sunucu Düzeltme Modülü ──
// ══════════════════════════════════════════════════════════════════

let geminiQARunning = false;
let geminiQAConsole = null;
let geminiQAVideosCache = [];

function logGeminiQA(msg, type = "info") {
  console.log(`[GEMINI-QA] [${type.toUpperCase()}] ${msg}`);
  if (geminiQAConsole) {
    const color = type === "error" ? "#f43f5e" : (type === "success" ? "#10b981" : (type === "warn" ? "#f59e0b" : "#94a3b8"));
    const div = document.createElement("div");
    div.style.cssText = `color: ${color}; margin-bottom: 4px; font-size: 12px; line-height: 1.4; word-break: break-word;`;
    div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    geminiQAConsole.appendChild(div);
    geminiQAConsole.scrollTop = geminiQAConsole.scrollHeight;
  }
}

function injectGeminiVideoQAFAB() {
  if (document.getElementById("gemini-qa-fab")) return;

  const fab = document.createElement("div");
  fab.id = "gemini-qa-fab";
  fab.style.cssText = `
    position: fixed; bottom: 144px; right: 24px; z-index: 999999;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white; width: 48px; height: 48px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; font-size: 20px; font-weight: bold;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.45);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden; white-space: nowrap;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  `;
  
  const text = document.createElement("span");
  text.id = "gemini-qa-fab-text";
  text.style.cssText = `
    opacity: 0; width: 0; display: inline-block; font-size: 13.5px;
    font-weight: 600; margin-left: 0; transition: all 0.25s ease;
  `;
  text.textContent = "Video Kontrol";

  const icon = document.createElement("span");
  icon.textContent = "🎬";

  // Sayı Rozeti (Badge)
  const badge = document.createElement("div");
  badge.id = "gemini-qa-fab-badge";
  badge.style.cssText = `
    position: absolute; top: -3px; right: -3px; background: #ef4444; color: white;
    font-size: 11px; font-weight: 800; border-radius: 10px; min-width: 18px; height: 18px;
    display: none; align-items: center; justify-content: center; padding: 0 4px;
    border: 2px solid #0f172a; box-shadow: 0 2px 5px rgba(0,0,0,0.4);
  `;
  
  fab.appendChild(icon);
  fab.appendChild(text);
  fab.appendChild(badge);
  document.body.appendChild(fab);

  fab.addEventListener("mouseenter", () => {
    fab.style.width = "146px";
    fab.style.borderRadius = "24px";
    text.style.opacity = "1";
    text.style.width = "auto";
    text.style.marginLeft = "8px";
  });
  fab.addEventListener("mouseleave", () => {
    fab.style.width = "48px";
    fab.style.borderRadius = "50%";
    text.style.opacity = "0";
    text.style.width = "0";
    text.style.marginLeft = "0";
  });

  fab.addEventListener("click", openGeminiVideoQAModal);

  // Kontrol klasörü periyodik rozet sorgusu
  updateKontrolBadge();
  setInterval(updateKontrolBadge, 15000);
}

async function updateKontrolBadge() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/video-patch/kontrol-videos");
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById("gemini-qa-fab-badge");
      if (badge) {
        if (data.count > 0) {
          badge.textContent = data.count;
          badge.style.display = "flex";
        } else {
          badge.style.display = "none";
        }
      }
    }
  } catch (e) {}
}

function openGeminiVideoQAModal() {
  const existing = document.getElementById("gemini-qa-modal");
  if (existing) {
    existing.style.display = "flex";
    loadKontrolVideosList();
    return;
  }

  const modal = document.createElement("div");
  modal.id = "gemini-qa-modal";
  modal.style.cssText = `
    position: fixed; bottom: 204px; right: 24px; width: 440px; max-height: 82vh;
    background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px; padding: 20px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
    color: #f8fafc; display: flex; flex-direction: column; gap: 14px;
    z-index: 10000000;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    animation: ytOtoFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  `;

  const header = document.createElement("div");
  header.style.cssText = `
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 12px;
  `;
  header.innerHTML = `
    <div>
      <h3 style="margin: 0; font-size: 16px; font-weight: 700; color: #818cf8; display: flex; align-items: center; gap: 8px;">
        🎬 Gemini Video Kalite Kontrolü
      </h3>
      <div style="font-size: 11.5px; color: #94a3b8; margin-top: 3px; line-height: 1.4;">
        Kontrol klasöründeki videoları seçip Gemini 1.5 Pro ile derinlemesine denetleyin.
      </div>
    </div>
  `;
  
  const closeBtn = document.createElement("button");
  closeBtn.textContent = "✕";
  closeBtn.style.cssText = `
    background: transparent; border: none; color: #94a3b8; font-size: 18px;
    cursor: pointer; padding: 4px; line-height: 1; transition: color 0.2s;
  `;
  closeBtn.addEventListener("mouseenter", () => closeBtn.style.color = "#f8fafc");
  closeBtn.addEventListener("mouseleave", () => closeBtn.style.color = "#94a3b8");
  closeBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });
  header.appendChild(closeBtn);
  modal.appendChild(header);

  // Video Listesi Kartı
  const listWrapper = document.createElement("div");
  listWrapper.style.cssText = `
    display: flex; flex-direction: column; gap: 8px; max-height: 240px; overflow-y: auto;
    padding-right: 4px;
  `;
  listWrapper.id = "gemini-qa-video-list";
  listWrapper.innerHTML = `
    <div style="text-align: center; color: #94a3b8; font-size: 12px; padding: 20px;">
      ⏳ Kontrol klasörü taranıyor...
    </div>
  `;
  modal.appendChild(listWrapper);

  // Aksiyon Barı (Tümünü Seç / Yenile)
  const actionBar = document.createElement("div");
  actionBar.style.cssText = `display: flex; justify-content: space-between; align-items: center; font-size: 12px;`;
  actionBar.innerHTML = `
    <button type="button" id="gemini-qa-select-all" style="background: transparent; border: none; color: #818cf8; cursor: pointer; font-weight: 600; padding: 0;">
      ☑️ Tümünü Seç / Kaldır
    </button>
    <button type="button" id="gemini-qa-refresh-btn" style="background: transparent; border: none; color: #94a3b8; cursor: pointer; display: flex; align-items: center; gap: 4px;">
      🔄 Yenile
    </button>
  `;
  modal.appendChild(actionBar);

  // Döngü Modu (Auto Fix Loop)
  const loopOption = document.createElement("label");
  loopOption.style.cssText = `
    display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: #cbd5e1;
    background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.2);
    padding: 10px 12px; border-radius: 10px; cursor: pointer; line-height: 1.4;
  `;
  loopOption.innerHTML = `
    <input type="checkbox" id="gemini-qa-autofix-chk" checked style="margin-top: 2px; cursor: pointer;" />
    <div>
      <strong style="color: #a5b4fc;">Otomatik Düzeltme & Doğrulama Döngüsü</strong>
      <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
        Gemini bir kusur tespit ederse yerel yama uygulanır ve güncellenen video aynı sohbete tekrar sorularak onay alınana kadar döngü işletilir.
      </div>
    </div>
  `;
  modal.appendChild(loopOption);

  // Başlat Butonu
  const startBtn = document.createElement("button");
  startBtn.id = "gemini-qa-start-btn";
  startBtn.textContent = "🚀 Seçilen Videoları Gemini ile Kontrol Et";
  startBtn.style.cssText = `
    background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none;
    padding: 12px; border-radius: 10px; font-size: 13.5px; font-weight: 700; cursor: pointer;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4); transition: all 0.2s;
  `;
  startBtn.addEventListener("mouseenter", () => startBtn.style.opacity = "0.92");
  startBtn.addEventListener("mouseleave", () => startBtn.style.opacity = "1");
  startBtn.addEventListener("click", startGeminiVideoQAProcess);
  modal.appendChild(startBtn);

  // Canlı Log Konsolu
  const consoleBox = document.createElement("div");
  consoleBox.id = "gemini-qa-console";
  consoleBox.style.cssText = `
    background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px;
    height: 110px; overflow-y: auto; font-family: monospace; font-size: 11.5px;
    display: flex; flex-direction: column; gap: 3px;
  `;
  consoleBox.innerHTML = `<div style="color: #64748b;">[Bilgi] Denetim başlatıldığında canlı adımlar burada görüntülenecek...</div>`;
  modal.appendChild(consoleBox);
  geminiQAConsole = consoleBox;

  document.body.appendChild(modal);

  // Buton Eventleri
  document.getElementById("gemini-qa-refresh-btn").addEventListener("click", loadKontrolVideosList);
  document.getElementById("gemini-qa-select-all").addEventListener("click", () => {
    const chks = document.querySelectorAll(".gemini-qa-video-chk");
    const allChecked = Array.from(chks).every(c => c.checked);
    chks.forEach(c => c.checked = !allChecked);
  });

  loadKontrolVideosList();
}

async function loadKontrolVideosList() {
  const container = document.getElementById("gemini-qa-video-list");
  if (!container) return;

  container.innerHTML = `<div style="text-align: center; color: #94a3b8; font-size: 12px; padding: 20px;">⏳ Kontrol klasörü taranıyor...</div>`;
  try {
    const res = await fetch("http://127.0.0.1:8000/api/video-patch/kontrol-videos");
    if (!res.ok) throw new Error("Sunucuya bağlanılamadı.");
    const data = await res.json();
    geminiQAVideosCache = data.videos || [];

    if (geminiQAVideosCache.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 24px 10px; background: rgba(15, 23, 42, 0.6); border-radius: 12px; border: 1px dashed #334155;">
          <div style="font-size: 26px; margin-bottom: 6px;">📭</div>
          <div style="font-size: 13px; font-weight: 600; color: #e2e8f0;">Kontrol Bekleyen Video Yok</div>
          <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">Sunucudan 'kontrol/' klasörüne yeni video indiğinde burada listelenecek.</div>
        </div>
      `;
      const btn = document.getElementById("gemini-qa-start-btn");
      if (btn) btn.disabled = true;
      return;
    }

    const btn = document.getElementById("gemini-qa-start-btn");
    if (btn) btn.disabled = false;

    container.innerHTML = "";
    geminiQAVideosCache.forEach((v, idx) => {
      const card = document.createElement("div");
      card.style.cssText = `
        display: flex; align-items: center; gap: 10px; background: #0f172a; border: 1px solid #334155;
        padding: 10px 12px; border-radius: 10px; transition: border-color 0.15s;
      `;
      card.innerHTML = `
        <input type="checkbox" class="gemini-qa-video-chk" data-idx="${idx}" checked style="cursor: pointer; width: 16px; height: 16px;" />
        <div style="flex: 1; min-width: 0;">
          <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 2px;">
            <span style="font-size: 10px; font-weight: 700; background: rgba(99, 102, 241, 0.2); color: #a5b4fc; padding: 2px 6px; border-radius: 4px;">
              ${v.channel_id}
            </span>
            <span style="font-size: 11px; color: #64748b;">${v.size_mb} MB • ${v.duration_str}</span>
          </div>
          <div style="font-size: 12.5px; font-weight: 600; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${v.title}">
            ${v.title}
          </div>
        </div>
      `;
      container.appendChild(card);
    });

  } catch (err) {
    container.innerHTML = `
      <div style="color: #f43f5e; font-size: 12px; text-align: center; padding: 15px;">
        ⚠️ Video listesi alınamadı: ${err.message}<br/>(Lokal FastAPI sunucusunun çalıştığından emin olun).
      </div>
    `;
  }
}

async function startGeminiVideoQAProcess() {
  if (geminiQARunning) {
    alert("Zaten aktif bir denetim süreci çalışıyor.");
    return;
  }

  const selectedChks = document.querySelectorAll(".gemini-qa-video-chk:checked");
  if (selectedChks.length === 0) {
    alert("Lütfen denetlemek için en az bir video seçin.");
    return;
  }

  const selectedVideos = Array.from(selectedChks).map(c => geminiQAVideosCache[parseInt(c.dataset.idx)]);
  const autoFixLoop = document.getElementById("gemini-qa-autofix-chk")?.checked ?? true;

  geminiQARunning = true;
  const startBtn = document.getElementById("gemini-qa-start-btn");
  if (startBtn) {
    startBtn.disabled = true;
    startBtn.textContent = "⏳ Gemini Denetimi Sürüyor...";
  }

  try {
    for (let i = 0; i < selectedVideos.length; i++) {
      const video = selectedVideos[i];
      logGeminiQA(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`, "info");
      logGeminiQA(`🎬 [${i+1}/${selectedVideos.length}] Video İşleniyor: '${video.title}'`, "info");

      // 1. Video Blob'unu yerel API'den indir
      logGeminiQA(`📥 Video yerel sunucudan çekiliyor (${video.size_mb} MB)...`, "info");
      const streamUrl = `http://127.0.0.1:8000/api/video-patch/stream-file?path=${encodeURIComponent(video.video_path)}`;
      const fileRes = await fetch(streamUrl);
      if (!fileRes.ok) throw new Error(`Video çekilemedi (HTTP ${fileRes.status})`);
      const blob = await fileRes.blob();
      const videoFile = new File([blob], video.video_file || "final.mp4", { type: "video/mp4" });

      // 2. Gemini web file input'una iliştir
      logGeminiQA(`📎 Video Gemini sohbetine iliştiriliyor...`, "info");
      let fileInput = document.querySelector('input[type="file"]');
      if (!fileInput) {
        const attachBtns = document.querySelectorAll('button[aria-label*="Dosya" i], button[aria-label*="Add file" i], button[aria-label*="Upload" i], button[aria-label*="ekle" i]');
        for (let b of attachBtns) {
          if (isVisible(b)) {
            b.click();
            await new Promise(r => setTimeout(r, 600));
            fileInput = document.querySelector('input[type="file"]');
            if (fileInput) break;
          }
        }
      }

      const dt = new DataTransfer();
      dt.items.add(videoFile);
      if (fileInput) {
        fileInput.files = dt.files;
        fileInput.dispatchEvent(new Event("input", { bubbles: true }));
        fileInput.dispatchEvent(new Event("change", { bubbles: true }));
      } else {
        const dropTarget = document.querySelector('rich-textarea') || document.querySelector('div[contenteditable="true"]') || document.body;
        dropTarget.dispatchEvent(new DragEvent('dragenter', { bubbles: true, dataTransfer: dt }));
        dropTarget.dispatchEvent(new DragEvent('dragover', { bubbles: true, dataTransfer: dt }));
        dropTarget.dispatchEvent(new DragEvent('drop', { bubbles: true, dataTransfer: dt }));
      }

      // Gemini'nin videoyu yüklemesini ve işlemeye almasını bekle
      logGeminiQA(`⏳ Gemini video yüklemesinin tamamlanması bekleniyor (8-10 saniye)...`, "info");
      await new Promise(r => setTimeout(r, 8000));

      // 3. Denetim promptunu yaz
      const promptText = `Lütfen iliştirdiğim bu videoyu ("${video.title}") profesyonel bir belgesel editörü ve kaza kırım araştırmacısı titizliğiyle saniye saniye incele.
Olay / Konu: ${video.title}

Özellikle şu 5 kritik uyuşmazlığı denetle:
1. Uyuşmazlıklar & Yabancı Göstergeler: Ekranda anlatılan kaza/uçuş dışında başka bir olayın telemetrisi veya HUD göstergesi (örn. başka bir uçağın adı, yanlış havayolu başlığı, alakasız rota grafiği) var mı?
2. Absürt / Yanlış Stoklar: Olayın geçtiği hava şartları ve coğrafya ile çelişen (örn: Kış fırtınasında karlı Fuji dağı, güneşli yaz manzarası, sakura/kiraz çiçekleri, ilgisiz şehirler/metrolar) görüntüler var mı?
3. Başlık ve Grafik Katman Hataları: Üst üste binen, çakışan, okunmayan NTSB veya spiker başlıkları var mı?
4. CVR ve Karakter Rolleri: Konuşma balonundaki pilot isimleri ve rolleri (Kaptan vs İkinci Pilot) doğru mu?
5. Kronoloji: Uçak havalanmadan önce kaza sonrası enkaz veya kurtarma fotoğrafları gösterilmiş mi?

Eğer videoda HİÇBİR hata yoksa yanıtına "ONAYLANDI - VİDEO KUSURSUZ" ifadesiyle başla.
Eğer uyuşmazlık veya hata varsa:
Her bir hatayı saniye aralığıyla ve net gerekçesiyle listele:
- [00:00 - 00:00]: Hatanın açıklaması ve önerilen düzeltme`;

      const inputEl = await waitForGeminiInput();
      if (!inputEl) throw new Error("Gemini metin giriş kutusu bulunamadı.");
      inputEl.focus();
      inputEl.innerText = promptText;
      inputEl.dispatchEvent(new Event("input", { bubbles: true }));
      await new Promise(r => setTimeout(r, 1000));

      // 4. Gönder
      logGeminiQA(`🚀 Denetim sorusu Gemini'ye gönderiliyor...`, "info");
      const initialTurns = getTurnCount();
      clickSendButton();

      // 5. Yanıtı bekle
      logGeminiQA(`🧠 Gemini videoyu saniye saniye izleyip analiz ediyor...`, "info");
      await waitForGeminiGeneration(initialTurns);

      const responseText = getLastResponseText();
      logGeminiQA(`📝 Gemini analizi tamamlandı!`, "success");

      // 6. Yanıtı analiz et
      const hasApproval = /onaylandı|kusursuz|uyuşmazlık bulunamadı|sorunsuz|tümüyle tutarlı|mükemmel/i.test(responseText) &&
                          !/düzeltilmesi gereken|kritik hata|uyumsuzluk tespit|mutlaka düzeltil/i.test(responseText);

      if (hasApproval) {
        logGeminiQA(`🎉 '${video.title}' ONAYLANDI! 'yuklenecek/' klasörüne taşınıyor...`, "success");
        const appRes = await fetch("http://127.0.0.1:8000/api/video-patch/approve-video", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ folder_path: video.folder_path, critique_text: responseText })
        });
        const appData = await appRes.json();
        if (appData.success) {
          logGeminiQA(`🚀 Video başarıyla yüklenecek klasörüne aktarıldı!`, "success");
        }
      } else {
        logGeminiQA(`⚠️ Gemini videoda düzeltilmesi gereken hususlar tespit etti.`, "warn");

        if (autoFixLoop) {
          logGeminiQA(`🛠️ Tespit edilen hatalar için In-Place yama uygulanıyor...`, "info");
          const patchRes = await fetch("http://127.0.0.1:8000/api/video-patch/apply-critique-local", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_path: video.folder_path, critique_text: responseText })
          });
          const patchData = await patchRes.json();
          if (patchData.success && patchData.patches && patchData.patches.length > 0) {
            logGeminiQA(`✅ ${patchData.patches.length} sahne yamalandı! Güncellenmiş video aynı sohbete tekrar yükleniyor...`, "success");

            // Yamalanan videoyu aynı sohbete tekrar yükle
            await new Promise(r => setTimeout(r, 2000));
            const reRes = await fetch(streamUrl);
            const reBlob = await reRes.blob();
            const reFile = new File([reBlob], video.video_file || "final.mp4", { type: "video/mp4" });

            let fi = document.querySelector('input[type="file"]');
            if (fi) {
              const dt2 = new DataTransfer();
              dt2.items.add(reFile);
              fi.files = dt2.files;
              fi.dispatchEvent(new Event("input", { bubbles: true }));
              fi.dispatchEvent(new Event("change", { bubbles: true }));
            }
            await new Promise(r => setTimeout(r, 6000));

            // Takip sorusu gönder
            const followInput = await waitForGeminiInput();
            if (followInput) {
              followInput.focus();
              followInput.innerText = `Belirttiğin hatalar ("${patchData.patches.map(p => p.issue_title).join(', ')}") doğrultusunda sahneler düzeltildi ve güncellendi. Yeni videoda hala herhangi bir uyuşmazlık veya kusur var mı?`;
              followInput.dispatchEvent(new Event("input", { bubbles: true }));
              await new Promise(r => setTimeout(r, 1000));

              const turns2 = getTurnCount();
              clickSendButton();
              logGeminiQA(`🧠 Gemini güncellenmiş yeni videoyu tekrar inceliyor...`, "info");
              await waitForGeminiGeneration(turns2);

              const responseText2 = getLastResponseText();
              if (/onaylandı|kusursuz|uyuşmazlık bulunamadı|sorunsuz|tümüyle tutarlı|mükemmel/i.test(responseText2)) {
                logGeminiQA(`🎉 Düzeltme sonrası video ONAYLANDI! 'yuklenecek/' klasörüne aktarılıyor...`, "success");
                await fetch("http://127.0.0.1:8000/api/video-patch/approve-video", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ folder_path: video.folder_path, critique_text: responseText2 })
                });
                logGeminiQA(`🚀 Video başarıyla yüklenecek klasörüne aktarıldı!`, "success");
              } else {
                logGeminiQA(`ℹ️ İkinci tur analiz raporu kaydedildi.`, "info");
              }
            }
          } else {
            logGeminiQA(`ℹ️ Somut zaman aralığı içeren yama bulunamadı. Rapor kaydedildi.`, "warn");
          }
        }
      }
    }

    logGeminiQA(`✨ Tüm seçilen videoların denetim süreci tamamlandı!`, "success");
    await loadKontrolVideosList();
    await updateKontrolBadge();

  } catch (err) {
    logGeminiQA(`❌ Denetim hatası: ${err.message}`, "error");
  } finally {
    geminiQARunning = false;
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.textContent = "🚀 Seçilen Videoları Gemini ile Kontrol Et";
    }
  }
}

