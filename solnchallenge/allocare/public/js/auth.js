/* ═══════════════════════════════════════════════════════════
   AlloCare — Authentication (No Firebase)
   Direct demo mode access
   ═════════════════════════════════════════════════════════ */

function signInDemo() {
  AppState.user = {
    uid: "demo-user-001",
    displayName: "Demo Coordinator",
    email: "demo@allocare.org",
    photoURL: null,
  };
  showDashboard();
  initializeData();
  showToast("Welcome to AlloCare Demo!", "success");
}

function signOut() {
  AppState.user = null;
  document.getElementById("dashboard").style.display = "none";
  document.getElementById("auth-screen").style.display = "flex";
}

function showDashboard() {
  document.getElementById("auth-screen").style.display = "none";
  document.getElementById("dashboard").style.display = "flex";

  // Update user info in topbar
  const initialEl = document.getElementById("user-initial");
  if (AppState.user) {
    initialEl.textContent = getInitials(AppState.user.displayName);
  }
}

function toggleUserMenu() {
  if (confirm("Sign out?")) {
    signOut();
  }
}

// Check API health on load
async function checkApiHealth() {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/health`);
    const data = await resp.json();
    const statusEl = document.getElementById("settings-api-status");
    if (statusEl) {
      statusEl.textContent = data.status === "healthy" ? "✅ Healthy" : "⚠️ Degraded";
      statusEl.style.color = data.status === "healthy" ? "var(--green)" : "var(--amber)";
    }
    showToast(`API: ${data.status} | Needs: ${data.data.needs} | Volunteers: ${data.data.volunteers} | Gemini: ${data.gemini_api_key_configured ? '✅' : '❌'}`, "info");
  } catch (e) {
    const statusEl = document.getElementById("settings-api-status");
    if (statusEl) {
      statusEl.textContent = "❌ Offline";
      statusEl.style.color = "var(--red)";
    }
    showToast("API is offline — using demo data", "error");
  }
}

// Pre-load auth screen stats on page load
document.addEventListener("DOMContentLoaded", async () => {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/health`);
    const data = await resp.json();
    const el = (id) => document.getElementById(id);
    if (el("stat-needs")) el("stat-needs").textContent = data.data?.needs || "20";
    if (el("stat-volunteers")) el("stat-volunteers").textContent = data.data?.volunteers || "12";
    // Also pre-fetch needs to count resolved
    const needsResp = await fetch(`${FUNCTIONS_BASE}/api/needs?limit=500`);
    const needsData = await needsResp.json();
    const resolved = (needsData.needs || []).filter(n => n.status === "resolved").length;
    if (el("stat-resolved")) el("stat-resolved").textContent = resolved || "0";
  } catch (e) {
    // Silently set fallback stats
    const el = (id) => document.getElementById(id);
    if (el("stat-needs")) el("stat-needs").textContent = "20";
    if (el("stat-volunteers")) el("stat-volunteers").textContent = "12";
    if (el("stat-resolved")) el("stat-resolved").textContent = "0";
  }
});

