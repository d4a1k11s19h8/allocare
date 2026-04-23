/* ═══════════════════════════════════════════════════════════
   AlloCare — Authentication (No Firebase)
   Direct demo mode access
   ═════════════════════════════════════════════════════════ */

function toggleAuthForms() {
  const loginCard = document.getElementById("login-card");
  const registerCard = document.getElementById("register-card");
  if (loginCard.style.display === "none") {
    loginCard.style.display = "block";
    registerCard.style.display = "none";
  } else {
    loginCard.style.display = "none";
    registerCard.style.display = "block";
  }
}

async function handleLogin() {
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  
  try {
    const res = await fetch(`${FUNCTIONS_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");
    
    AppState.user = data.user;
    localStorage.setItem("allocare_user", JSON.stringify(data.user));
    showToast("Login successful!", "success");
    showDashboard();
    initializeData();
  } catch (e) {
    showToast(e.message, "error");
  }
}

async function handleRegister() {
  const name = document.getElementById("reg-name").value;
  const email = document.getElementById("reg-email").value;
  const password = document.getElementById("reg-password").value;
  const role = document.getElementById("reg-role").value;
  
  try {
    const res = await fetch(`${FUNCTIONS_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, display_name: name, role })
    });
    
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Registration failed");
    
    AppState.user = data.user;
    localStorage.setItem("allocare_user", JSON.stringify(data.user));
    showToast("Registration successful!", "success");
    showDashboard();
    initializeData();
  } catch (e) {
    showToast(e.message, "error");
  }
}

function signOut() {
  AppState.user = null;
  localStorage.removeItem("allocare_user");
  document.getElementById("dashboard").style.display = "none";
  document.getElementById("auth-screen").style.display = "flex";

  // Reset role-based UI
  const volStyle = document.getElementById("volunteer-restrictions");
  if (volStyle) volStyle.remove();
  document.querySelectorAll(".nav-volunteer-only").forEach(el => el.style.display = "none");
  document.querySelectorAll(".nav-admin-only").forEach(el => el.style.display = "flex");
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  const dashNav = document.querySelector('[data-view="dashboard"]');
  if (dashNav) dashNav.classList.add("active");
}

function showDashboard() {
  document.getElementById("auth-screen").style.display = "none";
  document.getElementById("dashboard").style.display = "flex";

  // Update user info in topbar
  const initialEl = document.getElementById("user-initial");
  if (AppState.user) {
    initialEl.textContent = getInitials(AppState.user.display_name || AppState.user.displayName || "User");
    document.getElementById("topbar-org").textContent = AppState.user.display_name || AppState.user.displayName || "User";
  }

  const isVolunteer = AppState.user && AppState.user.role === "volunteer";

  // ── Role-based sidebar visibility ──
  document.querySelectorAll(".nav-volunteer-only").forEach(el => {
    el.style.display = isVolunteer ? "flex" : "none";
  });
  document.querySelectorAll(".nav-admin-only").forEach(el => {
    el.style.display = isVolunteer ? "none" : "flex";
  });

  // ── Role-based restrictions ──
  // Remove any previous restriction style
  const oldStyle = document.getElementById("volunteer-restrictions");
  if (oldStyle) oldStyle.remove();

  if (isVolunteer) {
    const style = document.createElement("style");
    style.id = "volunteer-restrictions";
    style.innerHTML = `
      /* Hide admin-only action buttons on need cards */
      .card-action-btn.flag { display: none !important; }
      /* Hide upload button in topbar */
      #upload-btn { display: none !important; }
      /* Hide volunteer panel on dashboard (right side) */
      .volunteer-panel { display: none !important; }
      /* Hide matching/assign buttons in need detail modal */
      .need-detail-body .btn-primary:has(.material-icons-outlined:contains('person_search')) { display: none !important; }
    `;
    document.head.appendChild(style);
  }
}


// Auto-login check
document.addEventListener("DOMContentLoaded", () => {
  const savedUser = localStorage.getItem("allocare_user");
  if (savedUser) {
    try {
      AppState.user = JSON.parse(savedUser);
      showDashboard();
      initializeData();
    } catch (e) {
      localStorage.removeItem("allocare_user");
    }
  }
});

function toggleUserMenu() {
  const dropdown = document.getElementById("user-dropdown");
  if (!dropdown) return;
  const isVisible = dropdown.style.display !== "none";
  dropdown.style.display = isVisible ? "none" : "block";

  // Update dropdown content
  if (!isVisible && AppState.user) {
    const nameEl = document.getElementById("dropdown-name");
    const roleEl = document.getElementById("dropdown-role");
    if (nameEl) nameEl.textContent = AppState.user.display_name || AppState.user.displayName || "User";
    if (roleEl) roleEl.textContent = (AppState.user.role || "organization").charAt(0).toUpperCase() + (AppState.user.role || "organization").slice(1);
  }

  // Close on outside click
  if (!isVisible) {
    setTimeout(() => {
      document.addEventListener("click", function closeDropdown(e) {
        if (!e.target.closest(".user-menu-wrapper")) {
          dropdown.style.display = "none";
          document.removeEventListener("click", closeDropdown);
        }
      });
    }, 10);
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

