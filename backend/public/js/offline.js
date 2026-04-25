/* ═══════════════════════════════════════════════════════════
   AlloCare — Offline Support (IndexedDB + Sync Queue)
   ═════════════════════════════════════════════════════════ */

const OfflineStore = {
  DB_NAME: "allocare_offline",
  DB_VERSION: 1,
  db: null,

  async init() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(this.DB_NAME, this.DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains("needs")) db.createObjectStore("needs", { keyPath: "id" });
        if (!db.objectStoreNames.contains("volunteers")) db.createObjectStore("volunteers", { keyPath: "id" });
        if (!db.objectStoreNames.contains("pendingReports")) db.createObjectStore("pendingReports", { keyPath: "id", autoIncrement: true });
      };
      req.onsuccess = (e) => { this.db = e.target.result; resolve(); };
      req.onerror = () => reject(req.error);
    });
  },

  async saveNeeds(needs) {
    if (!this.db) await this.init();
    const tx = this.db.transaction("needs", "readwrite");
    const store = tx.objectStore("needs");
    needs.forEach(n => { if (n.id) store.put(n); });
  },

  async saveVolunteers(volunteers) {
    if (!this.db) await this.init();
    const tx = this.db.transaction("volunteers", "readwrite");
    const store = tx.objectStore("volunteers");
    volunteers.forEach(v => { if (v.id) store.put(v); });
  },

  async getAll(storeName) {
    if (!this.db) await this.init();
    return new Promise((resolve) => {
      const tx = this.db.transaction(storeName, "readonly");
      const req = tx.objectStore(storeName).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  },

  async queueReport(report) {
    if (!this.db) await this.init();
    const tx = this.db.transaction("pendingReports", "readwrite");
    tx.objectStore("pendingReports").add({ ...report, queued_at: new Date().toISOString() });
  },

  async getPendingReports() {
    return this.getAll("pendingReports");
  },

  async clearPendingReports() {
    if (!this.db) await this.init();
    const tx = this.db.transaction("pendingReports", "readwrite");
    tx.objectStore("pendingReports").clear();
  },
};

// ── Network Status Detection ────────────────────────────────
let isOnline = navigator.onLine;

function updateOnlineStatus() {
  isOnline = navigator.onLine;
  const badge = document.getElementById("offline-badge");
  if (badge) badge.style.display = isOnline ? "none" : "inline-flex";

  if (isOnline) {
    syncPendingReports();
    showToast("✅ Back online — syncing data...", "success");
  } else {
    showToast("⚡ You're offline — reports will be queued", "info");
  }
}

window.addEventListener("online", updateOnlineStatus);
window.addEventListener("offline", updateOnlineStatus);

// Set initial state on load
document.addEventListener("DOMContentLoaded", () => {
  const badge = document.getElementById("offline-badge");
  if (badge && !navigator.onLine) badge.style.display = "inline-flex";
  OfflineStore.init().catch(e => console.log("[Offline] IndexedDB init:", e));
});

// ── Sync Pending Reports ────────────────────────────────────
async function syncPendingReports() {
  try {
    const pending = await OfflineStore.getPendingReports();
    if (pending.length === 0) return;

    let synced = 0;
    for (const report of pending) {
      try {
        await fetch(`${FUNCTIONS_BASE}/api/process_report`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_text: report.raw_text, source: report.source || "offline" }),
        });
        synced++;
      } catch (e) { break; }
    }

    if (synced > 0) {
      await OfflineStore.clearPendingReports();
      showToast(`✅ Synced ${synced} offline report(s)`, "success");
      fetchNeeds();
    }
  } catch (e) {
    console.log("[Offline] Sync error:", e);
  }
}

// ── Cache API Data for Offline Use ──────────────────────────
async function cacheDataForOffline() {
  try {
    if (AppState.needs.length > 0) await OfflineStore.saveNeeds(AppState.needs);
    if (AppState.volunteers.length > 0) await OfflineStore.saveVolunteers(AppState.volunteers);
  } catch (e) { console.log("[Offline] Cache error:", e); }
}

// Auto-cache after data loads
const _origFetchNeeds = typeof fetchNeeds !== "undefined" ? fetchNeeds : null;
if (_origFetchNeeds) {
  // Will be called after fetchNeeds completes via api-service.js
  setInterval(() => { if (AppState.needs.length > 0) cacheDataForOffline(); }, 30000);
}
