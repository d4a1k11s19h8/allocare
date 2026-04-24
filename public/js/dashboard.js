/* ═══════════════════════════════════════════════════════════
   AlloCare — Dashboard Controller
   Rendering, filtering, navigation, card interactions,
   Analytics charts (Chart.js)
   ═════════════════════════════════════════════════════════ */

// ── Render Need Cards ───────────────────────────────────────
function renderNeedsFeed() {
  const feed = document.getElementById("needs-feed");
  if (!feed) return;
  const filteredNeeds = getFilteredNeeds();

  if (filteredNeeds.length === 0) {
    feed.innerHTML = `
      <div class="loading-state">
        <span class="material-icons-outlined" style="font-size:48px;color:var(--text-muted);">check_circle</span>
        <p>No matching needs found</p>
      </div>`;
    return;
  }

  feed.innerHTML = filteredNeeds.map((need, i) => createNeedCard(need, i)).join("");
}

function createNeedCard(need, index) {
  const issueType = ISSUE_TYPES[need.issue_type] || ISSUE_TYPES.other;
  const urgency = need.urgency_label || "low";
  const urgencyConfig = URGENCY_LEVELS[urgency] || URGENCY_LEVELS.low;
  const skills = (need.required_skills || []).slice(0, 3);
  const created = timeAgo(need.created_at);
  const sourceIcons = { photo: "📸", csv: "📄", manual: "✍️", whatsapp: "💬", sms: "💬" };
  const sourceLabel = sourceIcons[need.source] || "📋";
  const sourceClass = need.source || "manual";
  const status = need.status || "open";
  const isResolved = status === "resolved";
  const isAssigned = status === "assigned" || status === "offered";

  // Status badge for assigned/resolved
  let statusTag = "";
  if (isResolved) {
    statusTag = `<span style="padding:2px 8px;border-radius:var(--radius-full);font-size:10px;font-weight:700;text-transform:uppercase;background:rgba(14,159,110,0.15);color:var(--green);margin-left:6px;">✓ Resolved</span>`;
  } else if (isAssigned) {
    statusTag = `<span style="padding:2px 8px;border-radius:var(--radius-full);font-size:10px;font-weight:700;text-transform:uppercase;background:rgba(26,86,219,0.15);color:var(--primary);margin-left:6px;">⏳ Assigned</span>`;
  }

  // Action buttons: hide for resolved, show "Find More" for assigned
  let actionBtns = "";
  if (!isResolved && !isAssigned) {
    actionBtns = `
      <div class="need-card-actions">
        <button class="card-action-btn" onclick="event.stopPropagation(); matchVolunteers('${need.id}')" title="Find volunteers">
          <span class="material-icons-outlined">person_search</span>
        </button>
        <button class="card-action-btn flag" onclick="event.stopPropagation(); openFlagDialog('${need.id}')" title="Flag score">
          <span class="material-icons-outlined">flag</span>
        </button>
      </div>`;
  } else if (isAssigned) {
    actionBtns = `
      <div class="need-card-actions">
        <button class="card-action-btn" onclick="event.stopPropagation(); matchVolunteers('${need.id}')" title="Find more volunteers">
          <span class="material-icons-outlined">person_search</span>
        </button>
      </div>`;
  }

  return `
    <div class="need-card border-${urgency}" onclick="selectNeed('${need.id}')" style="animation-delay:${index * 50}ms;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;">
          <span style="font-size:18px;flex-shrink:0;">${issueType.icon}</span>
          <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-secondary);flex-shrink:0;">${issueType.label}</span>
          <span class="source-badge ${sourceClass}" style="flex-shrink:0;">${sourceLabel} ${need.source || "manual"}</span>
          ${statusTag}
          <span style="color:var(--text-muted);font-size:11px;margin:0 2px;">—</span>
          <span style="font-size:12px;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${(need.summary || "Need report").slice(0, 60)}</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;margin-left:12px;">
          <span style="font-size:13px;font-weight:800;font-family:'Courier New',monospace;color:${urgencyConfig.color};">${need.urgency_score || 0}</span>
          <span class="urgency-badge ${urgency}">${urgencyConfig.label}</span>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text-muted);margin-top:4px;">
        <span class="material-icons-outlined" style="font-size:13px;">location_on</span>
        ${need.zone || "Unknown"}
        <span style="margin:0 3px;">·</span>
        <span class="material-icons-outlined" style="font-size:12px;">schedule</span>
        ${created}
        ${need.affected_count ? `<span style="margin:0 3px;">·</span><span style="color:var(--green);font-weight:600;">👥 ~${need.affected_count}</span>` : ""}
        ${skills.length > 0 ? `<span style="margin:0 3px;">·</span>${skills.map(s => `<span style="padding:1px 6px;background:var(--bg-elevated);border-radius:10px;font-size:10px;color:var(--text-muted);">${s}</span>`).join(" ")}` : ""}
      </div>
    </div>`;
}

// ── Render Volunteer List ───────────────────────────────────
function renderVolunteerList() {
  const list = document.getElementById("volunteer-list");
  if (!list) return;
  const available = AppState.volunteers.filter(v => v.status === "available");
  const others = AppState.volunteers.filter(v => v.status !== "available");

  const countEl = document.getElementById("volunteer-count");
  if (countEl) countEl.textContent = `${available.length} available`;

  let html = "";
  [...available, ...others].forEach(v => {
    const color = getAvatarColor(v.display_name);
    const initials = getInitials(v.display_name);
    html += `
      <div class="volunteer-card" onclick="viewVolunteerDetail('${v.id}')">
        <div class="volunteer-avatar" style="background:${color}">${initials}</div>
        <div class="volunteer-info">
          <div class="volunteer-name">${v.display_name}</div>
          <div class="volunteer-skills">${(v.skills || []).slice(0, 3).join(", ")}</div>
        </div>
        <div class="volunteer-status ${v.status}"></div>
      </div>`;
  });

  list.innerHTML = html;

  // Update impact stats
  const totalResolved = AppState.volunteers.reduce((sum, v) =>
    sum + (v.impact_stats?.total_tasks_completed || 0), 0);
  const totalPeople = AppState.volunteers.reduce((sum, v) =>
    sum + (v.impact_stats?.total_people_helped || 0), 0);

  const el = (id) => document.getElementById(id);
  if (el("impact-resolved")) el("impact-resolved").textContent = totalResolved;
  if (el("impact-people")) el("impact-people").textContent = totalPeople.toLocaleString();
  if (el("impact-hours")) el("impact-hours").textContent = Math.round(totalResolved * 3);
  if (el("impact-volunteers")) el("impact-volunteers").textContent = available.length;
}

// ── Update Counts ───────────────────────────────────────────
function updateCounts() {
  const needs = AppState.needs;
  const critical = needs.filter(n => n.urgency_label === "critical").length;
  const high = needs.filter(n => n.urgency_label === "high").length;
  const medium = needs.filter(n => n.urgency_label === "medium").length;
  const low = needs.filter(n => n.urgency_label === "low").length;
  const open = needs.filter(n => n.status === "open" || n.status === "flagged").length;
  const assigned = needs.filter(n => n.status === "assigned").length;
  const resolved = needs.filter(n => n.status === "resolved").length;

  const el = (id) => document.getElementById(id);
  if (el("count-critical")) el("count-critical").textContent = `${critical} Critical`;
  if (el("count-high")) el("count-high").textContent = `${high} High`;
  if (el("count-medium")) el("count-medium").textContent = `${medium} Medium`;
  if (el("count-low")) el("count-low").textContent = `${low} Low`;
  if (el("sidebar-open")) el("sidebar-open").textContent = open;
  if (el("sidebar-assigned")) el("sidebar-assigned").textContent = assigned;
  if (el("sidebar-resolved")) el("sidebar-resolved").textContent = resolved;

  // Auth screen stats
  if (el("stat-needs")) el("stat-needs").textContent = open || needs.length;
  if (el("stat-volunteers")) el("stat-volunteers").textContent = AppState.volunteers.length || "12";
  if (el("stat-resolved")) el("stat-resolved").textContent = resolved || "147";
}

// ── Select Need ─────────────────────────────────────────────
function selectNeed(needId) {
  AppState.selectedNeedId = needId;
  const need = AppState.needs.find(n => n.id === needId);
  if (!need) return;

  // Highlight card
  document.querySelectorAll(".need-card").forEach(c => c.style.outline = "none");
  const cards = document.querySelectorAll(".need-card");
  const filteredNeeds = getFilteredNeeds();
  const idx = filteredNeeds.findIndex(n => n.id === needId);
  if (cards[idx]) {
    cards[idx].style.outline = `2px solid ${(URGENCY_LEVELS[need.urgency_label] || URGENCY_LEVELS.low).color}`;
    cards[idx].scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Center map
  centerMapOnNeed(need);

  // Auto-run matching
  matchVolunteers(needId);

  // Show detail modal
  showNeedDetail(need);
}

function showNeedDetail(need) {
  const issueType = ISSUE_TYPES[need.issue_type] || ISSUE_TYPES.other;
  const urgency = URGENCY_LEVELS[need.urgency_label] || URGENCY_LEVELS.low;
  const status = need.status || "open";
  const isResolved = status === "resolved";
  const isAssigned = status === "assigned" || status === "offered";

  document.getElementById("detail-title").innerHTML = `
    <span style="font-size:24px;">${issueType.icon}</span>
    ${need.zone || "Unknown"} — ${issueType.label}
    <span class="urgency-badge ${need.urgency_label}" style="margin-left:8px;">${urgency.label}</span>
    <span style="margin-left:8px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;
      background:${isResolved ? 'rgba(14,159,110,0.15)' : isAssigned ? 'rgba(26,86,219,0.15)' : 'rgba(234,179,8,0.15)'};
      color:${isResolved ? 'var(--green)' : isAssigned ? 'var(--primary)' : 'var(--amber)'};">${status}</span>`;

  const body = document.getElementById("need-detail-body");

  // Build status-specific banner
  let statusBanner = "";
  if (isResolved) {
    statusBanner = `
    <div class="detail-section" style="background:rgba(14,159,110,0.1);border:1px solid rgba(14,159,110,0.3);border-radius:var(--radius-md);padding:var(--space-md);display:flex;align-items:center;gap:var(--space-sm);">
      <span class="material-icons-outlined" style="color:var(--green);font-size:28px;">check_circle</span>
      <div>
        <div style="color:var(--green);font-weight:700;">Need Resolved</div>
        <div style="color:var(--text-secondary);font-size:var(--font-xs);">This need has been resolved by a volunteer.</div>
      </div>
    </div>`;
  }

  // Build assigned volunteer placeholder
  let assignedSection = "";
  if (isAssigned || isResolved) {
    assignedSection = `
    <div class="detail-section" id="assigned-vol-section">
      <h3><span class="material-icons-outlined" style="vertical-align:middle;">person</span> Assigned Volunteer</h3>
      <div id="assigned-vol-info" style="padding:var(--space-sm);">
        <div class="loading-spinner" style="width:20px;height:20px;border-width:2px;margin:8px auto;"></div>
      </div>
    </div>`;
  }

  // Build action buttons (only for open/flagged needs)
  let actionButtons = "";
  if (!isResolved && !isAssigned) {
    actionButtons = `
    <div class="detail-section" style="display:flex;gap:var(--space-md);">
      <button class="btn-primary" onclick="matchVolunteers('${need.id}'); closeNeedDetail();">
        <span class="material-icons-outlined">person_search</span> Find Volunteers
      </button>
      <button class="btn-secondary" onclick="openFlagDialog('${need.id}')">
        <span class="material-icons-outlined">flag</span> Flag Score
      </button>
    </div>`;
  } else if (isAssigned) {
    actionButtons = `
    <div class="detail-section" style="display:flex;gap:var(--space-md);">
      <button class="btn-primary" onclick="matchVolunteers('${need.id}'); closeNeedDetail();">
        <span class="material-icons-outlined">person_search</span> Find More Volunteers
      </button>
    </div>`;
  }

  body.innerHTML = `
    ${statusBanner}

    <div class="detail-section">
      <h3>Summary</h3>
      <p style="font-size:var(--font-base);line-height:1.6;">${need.summary || "No summary available"}</p>
    </div>

    ${need.coordinator_explanation ? `
    <div class="detail-section">
      <h3>AI Analysis</h3>
      <p style="font-size:var(--font-sm);color:var(--text-secondary);line-height:1.5;font-style:italic;">
        "${need.coordinator_explanation}"
      </p>
    </div>` : ""}

    <div class="detail-section">
      <h3>Urgency Formula (Transparent AI)</h3>
      <div class="detail-formula">
        Score = (severity × log(frequency + 1)) / days_since_report<br>
        = (${need.severity_score || "?"} × log(${need.report_frequency_30d || "?"}+1)) / max(1, days)<br>
        = <strong style="color:${urgency.color};">${need.urgency_score || 0}/100 (${urgency.label})</strong>
      </div>
      <p style="font-size:var(--font-xs);color:var(--text-muted);margin-top:var(--space-xs);">
        🛡️ Coordinators can override this score via the "Flag" button. All corrections are logged.
      </p>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:var(--space-md);">
      <div class="impact-card">
        <span class="impact-value" style="color:${urgency.color};">${need.urgency_score || 0}</span>
        <span class="impact-label">Urgency Score</span>
      </div>
      <div class="impact-card">
        <span class="impact-value">${need.affected_count || "?"}</span>
        <span class="impact-label">People Affected</span>
      </div>
      <div class="impact-card">
        <span class="impact-value">${need.recommended_volunteer_count || 2}</span>
        <span class="impact-label">Volunteers Needed</span>
      </div>
    </div>

    ${assignedSection}

    <div class="detail-section">
      <h3>Required Skills</h3>
      <div style="display:flex;gap:6px;flex-wrap:wrap;">
        ${(need.required_skills || []).map(s => `<span class="skill-chip" style="padding:4px 12px;">${s}</span>`).join("")}
      </div>
    </div>

    ${actionButtons}`;

  document.getElementById("need-detail-modal").style.display = "flex";

  // Fetch assigned volunteer info asynchronously
  if (isAssigned || isResolved) {
    fetchAssignedVolunteer(need.id);
  }
}

async function fetchAssignedVolunteer(needId) {
  const infoEl = document.getElementById("assigned-vol-info");
  if (!infoEl) return;

  try {
    const res = await fetch(`${FUNCTIONS_BASE}/api/needs/${needId}/assignments`);
    if (!res.ok) throw new Error("Failed to fetch");
    const data = await res.json();

    if (data.total === 0) {
      infoEl.innerHTML = `<p style="color:var(--text-muted);font-size:var(--font-sm);">No volunteer assigned yet.</p>`;
      return;
    }

    infoEl.innerHTML = data.assignments.map(a => {
      const vol = a.volunteer || {};
      const color = getAvatarColor(vol.display_name || "V");
      const initials = getInitials(vol.display_name || "V");
      const statusColors = { offered: "var(--cyan)", accepted: "var(--primary)", completed: "var(--green)", declined: "var(--red)" };
      const statusColor = statusColors[a.status] || "var(--amber)";
      const skills = (vol.skills || []).slice(0, 3).join(", ");

      return `
        <div style="display:flex;align-items:center;gap:var(--space-md);padding:var(--space-sm) 0;border-bottom:1px solid var(--border);">
          <div class="volunteer-avatar" style="background:${color};width:40px;height:40px;font-size:14px;flex-shrink:0;">${initials}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-weight:600;color:var(--text-primary);">${vol.display_name || "Unknown"}</div>
            <div style="font-size:var(--font-xs);color:var(--text-muted);">${skills || "General support"} · ${vol.zone || ""}</div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
            <span style="padding:3px 8px;border-radius:12px;font-size:10px;font-weight:700;text-transform:uppercase;
              background:${statusColor}22;color:${statusColor};">${a.status}</span>
            ${vol.impact_points ? `<span style="font-size:10px;color:var(--amber);">⭐ ${vol.impact_points} pts</span>` : ""}
          </div>
        </div>`;
    }).join("");
  } catch (e) {
    infoEl.innerHTML = `<p style="color:var(--text-muted);font-size:var(--font-sm);">Could not load assignment info.</p>`;
  }
}

function closeNeedDetail() {
  document.getElementById("need-detail-modal").style.display = "none";
}

// ── Filter Functions ────────────────────────────────────────
function applyFilters() {
  AppState.filters.type = document.getElementById("filter-type").value;
  AppState.filters.urgency = document.getElementById("filter-urgency").value;
  renderNeedsFeed();
  updateMapMarkers();
}

function filterNeeds(searchTerm) {
  AppState.filters.search = searchTerm;
  renderNeedsFeed();
  updateMapMarkers();
}

// ── Flag Dialog ─────────────────────────────────────────────
function openFlagDialog(needId) {
  const need = AppState.needs.find(n => n.id === needId);
  if (!need) return;

  const newScore = prompt(
    `Current urgency score: ${need.urgency_score}/100\n\nEnter corrected score (0–100):`,
    need.urgency_score
  );

  if (newScore === null) return;
  const score = parseInt(newScore);
  if (isNaN(score) || score < 0 || score > 100) {
    showToast("Invalid score. Must be 0–100.", "error");
    return;
  }

  const reason = prompt("Reason for correction (optional):", "");
  flagUrgencyScore(needId, score, reason || "Coordinator override");
}

// ── View Toggle ─────────────────────────────────────────────
function switchView(view) {
  // Update sidebar active state
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  const navItem = document.querySelector(`[data-view="${view}"]`);
  if (navItem) navItem.classList.add("active");

  // Hide all sections, show selected
  document.querySelectorAll(".view-section").forEach(sec => {
    sec.style.display = "none";
    sec.classList.remove("active");
  });

  const targetView = document.getElementById(`view-${view}`);
  if (targetView) {
    targetView.style.display = "flex";
    targetView.classList.add("active");
  }

  // Render content based on view
  if (view === "dashboard") {
    setTimeout(() => {
      if (mapInstance) mapInstance.invalidateSize();
    }, 200);
  } else if (view === "reports") {
    renderReportsTable();
  } else if (view === "volunteers") {
    renderVolunteersGrid();
  } else if (view === "analytics") {
    renderAnalytics();
  } else if (view === "my-tasks") {
    renderMyTasks();
  } else if (view === "api-monitor") {
    renderAPIHealth();
  }
}

// ── My Tasks (Volunteer View) ───────────────────────────────
async function renderMyTasks() {
  const grid = document.getElementById("my-tasks-grid");
  const emptyEl = document.getElementById("my-tasks-empty");
  const countEl = document.getElementById("my-tasks-count");
  if (!grid) return;

  // Get volunteer ID from logged-in user
  const user = AppState.user;
  if (!user || !user.id) {
    grid.innerHTML = "";
    if (emptyEl) { emptyEl.style.display = "block"; }
    return;
  }

  // Update profile summary
  const avatarEl = document.getElementById("vol-profile-avatar");
  const nameEl = document.getElementById("vol-profile-name");
  const skillsEl = document.getElementById("vol-profile-skills");
  if (avatarEl) avatarEl.textContent = getInitials(user.display_name || "V");
  if (nameEl) nameEl.textContent = user.display_name || "Volunteer";

  // Fetch volunteer details for skills/points
  try {
    const volRes = await fetch(`${FUNCTIONS_BASE}/api/volunteers/${user.id}`);
    if (volRes.ok) {
      const vol = await volRes.json();
      if (skillsEl) skillsEl.textContent = (vol.skills || []).join(", ") || "No skills listed";
      const pointsEl = document.getElementById("vol-impact-points");
      const tasksEl = document.getElementById("vol-impact-tasks");
      const peopleEl = document.getElementById("vol-impact-people");
      if (pointsEl) pointsEl.textContent = vol.impact_points || 0;
      if (tasksEl) tasksEl.textContent = (vol.impact_stats || {}).total_tasks_completed || 0;
      if (peopleEl) peopleEl.textContent = (vol.impact_stats || {}).total_people_helped || 0;
    }
  } catch (e) { /* ignore */ }

  // Fetch assignments
  try {
    const res = await fetch(`${FUNCTIONS_BASE}/api/volunteers/${user.id}/assignments`);
    if (!res.ok) throw new Error("Failed to fetch assignments");
    const data = await res.json();

    if (countEl) countEl.textContent = `${data.total} task${data.total !== 1 ? "s" : ""}`;

    if (data.total === 0) {
      grid.innerHTML = "";
      if (emptyEl) emptyEl.style.display = "block";
      return;
    }

    if (emptyEl) emptyEl.style.display = "none";
    grid.innerHTML = data.assignments.map(a => createTaskCard(a)).join("");
  } catch (e) {
    grid.innerHTML = `<div class="loading-state"><p style="color:var(--red);">Error loading tasks: ${e.message}</p></div>`;
  }
}

function createTaskCard(assignment) {
  const need = assignment.need || {};
  const issueType = ISSUE_TYPES[need.issue_type] || ISSUE_TYPES.other;
  const urgency = URGENCY_LEVELS[need.urgency_label] || URGENCY_LEVELS.low;
  const status = assignment.status || "pending";

  const statusColors = {
    offered: "var(--cyan)",
    pending: "var(--amber)",
    accepted: "var(--primary)",
    completed: "var(--green)",
    declined: "var(--red)"
  };
  const statusIcons = {
    offered: "new_releases",
    pending: "schedule",
    accepted: "play_arrow",
    completed: "check_circle",
    declined: "cancel"
  };

  const actions = status === "offered" ? `
    <div style="display:flex; gap: var(--space-sm); margin-top: var(--space-md);">
      <button class="btn-primary btn-sm" onclick="event.stopPropagation(); acceptTask('${assignment.assignment_id}')">
        <span class="material-icons-outlined" style="font-size:16px;">thumb_up</span> Accept
      </button>
      <button class="btn-primary btn-sm" style="background: transparent; border: 1px solid var(--red); color: var(--red);" onclick="event.stopPropagation(); declineTask('${assignment.assignment_id}')">
        <span class="material-icons-outlined" style="font-size:16px;">thumb_down</span> Decline
      </button>
    </div>
  ` : status === "accepted" || status === "pending" ? `
    <div style="display:flex; gap: var(--space-sm); margin-top: var(--space-md);">
      <button class="btn-primary btn-sm" style="background: var(--green);" onclick="event.stopPropagation(); completeMyTask('${assignment.assignment_id}')">
        <span class="material-icons-outlined" style="font-size:16px;">task_alt</span> Mark Complete
      </button>
    </div>
  ` : status === "declined" ? `
    <div style="margin-top: var(--space-md); display:flex; align-items:center; gap:6px; color: var(--red); font-weight:600; font-size: var(--font-sm);">
      <span class="material-icons-outlined" style="font-size:18px;">cancel</span> Declined
    </div>
  ` : `
    <div style="margin-top: var(--space-md); display:flex; align-items:center; gap:6px; color: var(--green); font-weight:600; font-size: var(--font-sm);">
      <span class="material-icons-outlined" style="font-size:18px;">verified</span> Completed
    </div>
  `;

  return `
    <div class="glass-card" style="padding: var(--space-lg); transition: transform 0.2s, box-shadow 0.2s; cursor:default;"
         onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 30px rgba(0,0,0,0.3)';"
         onmouseout="this.style.transform='none'; this.style.boxShadow='none';">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: var(--space-sm);">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:20px;">${issueType.icon}</span>
          <span style="font-weight:600; color: var(--text-primary);">${issueType.label}</span>
        </div>
        <div style="display:flex; align-items:center; gap:6px; padding:4px 10px; border-radius:20px; background:${statusColors[status] || statusColors.pending}22; color:${statusColors[status] || statusColors.pending}; font-size: var(--font-xs); font-weight:600; text-transform:uppercase;">
          <span class="material-icons-outlined" style="font-size:14px;">${statusIcons[status] || statusIcons.pending}</span>
          ${status}
        </div>
      </div>
      <p style="color: var(--text-secondary); font-size: var(--font-sm); line-height:1.5; margin: var(--space-sm) 0;">
        ${need.summary || "No details available"}
      </p>
      <div style="display:flex; align-items:center; gap:6px; color: var(--text-muted); font-size: var(--font-xs); margin-bottom: var(--space-xs);">
        <span class="material-icons-outlined" style="font-size:14px;">location_on</span>
        ${need.zone || "Unknown"}
      </div>
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
        <span class="urgency-badge ${need.urgency_label}" style="font-size:11px;">${urgency.label}</span>
        ${need.affected_count ? `<span style="font-size:var(--font-xs); color:var(--text-muted);">~${need.affected_count} people</span>` : ""}
        ${assignment.match_score ? `<span style="font-size:var(--font-xs); color:var(--primary);">Match: ${Math.round(assignment.match_score * 100)}%</span>` : ""}
      </div>
      ${actions}
    </div>`;
}

async function acceptTask(assignmentId) {
  try {
    const res = await fetch(`${FUNCTIONS_BASE}/api/assignments/${assignmentId}/accept`, {
      method: "POST"
    });
    if (!res.ok) throw new Error("Failed to accept task");
    
    showToast("Task accepted! Navigate to the location to help.", "success");
    fetchNotifications();
    renderMyTasks();
  } catch (e) {
    showToast("Failed to accept task", "error");
  }
}

async function declineTask(assignmentId) {
  const reason = prompt("Please state a reason for declining this task:");
  if (!reason) {
    showToast("Reason is required to decline a task.", "error");
    return;
  }
  
  try {
    const res = await fetch(`${FUNCTIONS_BASE}/api/assignments/${assignmentId}/decline`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: reason })
    });
    if (!res.ok) throw new Error("Failed to decline task");
    
    showToast("Task declined.", "info");
    fetchNotifications();
    renderMyTasks();
  } catch (e) {
    showToast("Failed to decline task", "error");
  }
}

async function completeMyTask(assignmentId) {
  try {
    const res = await fetch(`${FUNCTIONS_BASE}/api/complete_task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assignment_id: assignmentId })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Task completed! +${data.scorecard.points_earned} impact points earned! 🎉`, "success");
      renderMyTasks();
    } else {
      showToast("Failed to complete task", "error");
    }
  } catch (e) {
    showToast("Error: " + e.message, "error");
  }
}


function renderReportsTable() {
  const tbody = document.getElementById("reports-table-body");
  if (!tbody) return;

  tbody.innerHTML = AppState.needs.map(need => {
    const issueType = ISSUE_TYPES[need.issue_type] || ISSUE_TYPES.other;
    const urgency = URGENCY_LEVELS[need.urgency_label] || URGENCY_LEVELS.low;
    const statusColor = need.status === 'open' ? 'var(--amber)' : (need.status === 'resolved' ? 'var(--green)' : 'var(--primary)');

    return `
      <tr style="border-bottom: 1px solid var(--border); transition: background 0.3s; cursor: pointer;" onmouseover="this.style.backgroundColor='var(--bg-card-hover)'" onmouseout="this.style.backgroundColor='transparent'" onclick="selectNeed('${need.id}')">
        <td style="padding: var(--space-md); font-family: monospace;">${(need.id || '').substring(0, 8)}</td>
        <td style="padding: var(--space-md);"><span style="margin-right: 8px;">${issueType.icon}</span>${issueType.label}</td>
        <td style="padding: var(--space-md);">${need.zone || "Unknown"}</td>
        <td style="padding: var(--space-md);"><span class="urgency-badge ${need.urgency_label}">${urgency.label}</span></td>
        <td style="padding: var(--space-md); text-transform: uppercase; font-size: 11px; font-weight: bold; color: ${statusColor};">${need.status}</td>
      </tr>
    `;
  }).join("");
}

function renderVolunteersGrid() {
  const grid = document.getElementById("volunteers-grid");
  if (!grid) return;

  grid.innerHTML = AppState.volunteers.map(v => {
    const color = getAvatarColor(v.display_name);
    const initials = getInitials(v.display_name);
    const skills = (v.skills || []).slice(0, 3).map(s => `<span class="skill-chip" style="font-size: 10px;">${s}</span>`).join("");
    const pts = v.impact_points || 0;

    return `
      <div class="glass-card" style="padding: var(--space-md); display: flex; flex-direction: column; align-items: center; text-align: center; cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-5px)'" onmouseout="this.style.transform='none'">
        <div class="volunteer-avatar" style="background:${color}; width: 64px; height: 64px; font-size: 24px; margin-bottom: var(--space-sm);">${initials}</div>
        <h3 style="margin-bottom: var(--space-xs); font-size: var(--font-base);">${v.display_name}</h3>
        <p style="color: var(--text-muted); font-size: var(--font-xs); margin-bottom: var(--space-sm);">${v.zone || 'Any Zone'}</p>
        <div style="display: flex; gap: 4px; flex-wrap: wrap; justify-content: center; margin-bottom: var(--space-md);">
          ${skills}
        </div>
        <div style="margin-top: auto; padding-top: var(--space-sm); border-top: 1px solid var(--border); width: 100%; display: flex; justify-content: space-around;">
          <div><strong style="color: var(--primary);">${pts}</strong><div style="font-size: 10px; color: var(--text-muted);">Points</div></div>
          <div><strong style="color: var(--green);">${v.impact_stats?.total_tasks_completed || 0}</strong><div style="font-size: 10px; color: var(--text-muted);">Tasks</div></div>
        </div>
      </div>
    `;
  }).join("");
}

function viewVolunteerDetail(volId) {
  const vol = AppState.volunteers.find(v => v.id === volId);
  if (!vol) return;
  showToast(`${vol.display_name} — ${vol.impact_points} impact points, ${vol.impact_stats?.total_tasks_completed || 0} tasks completed`, "info");
}

// ── Notifications ───────────────────────────────────────────
async function fetchNotifications() {
  if (!AppState.user) return;
  try {
    const res = await fetch(`${FUNCTIONS_BASE}/api/users/${AppState.user.id}/notifications`);
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById("notif-badge");
      const list = document.getElementById("notification-list");
      
      const count = data.notifications.length;
      if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? "flex" : "none";
      }
      
      if (list) {
        if (count === 0) {
          list.innerHTML = `<div style="padding: 12px; text-align: center; color: var(--text-muted); font-size: 13px;">No new notifications</div>`;
        } else {
          list.innerHTML = data.notifications.map(n => `
            <div style="padding: 10px; border-bottom: 1px solid var(--border); font-size: 13px;">
              <div style="color: var(--text-primary); margin-bottom: 4px;">${n.message}</div>
              <div style="color: var(--text-muted); font-size: 11px;">${timeAgo(n.timestamp)}</div>
            </div>
          `).join('');
        }
      }
    }
  } catch (e) {
    console.error("Failed to fetch notifications", e);
  }
}

function toggleNotifications() {
  const dropdown = document.getElementById("notification-dropdown");
  if (!dropdown) return;
  
  if (dropdown.style.display === "none" || dropdown.style.display === "") {
    dropdown.style.display = "block";
    fetchNotifications();
  } else {
    dropdown.style.display = "none";
  }
}

// Call fetchNotifications periodically (e.g. every 30s)
setInterval(fetchNotifications, 30000);

// ── Toast System ────────────────────────────────────────────
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const icons = {
    success: "check_circle",
    error: "error",
    info: "info",
  };

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="material-icons-outlined">${icons[type] || "info"}</span>
    <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ═══════════════════════════════════════════════════════════════
// ANALYTICS — Chart.js Integration
// ═══════════════════════════════════════════════════════════════

let analyticsCharts = {};

async function renderAnalytics() {
  // Try to get analytics from backend
  let data = await fetchAnalytics();

  // Fallback: compute from local data
  if (!data) {
    data = computeLocalAnalytics();
  }

  // Destroy old charts
  Object.values(analyticsCharts).forEach(c => { if (c) c.destroy(); });
  analyticsCharts = {};

  const chartDefaults = {
    color: '#94A3B8',
    borderColor: 'rgba(255,255,255,0.08)',
    font: { family: 'Inter' },
  };
  Chart.defaults.color = chartDefaults.color;
  Chart.defaults.borderColor = chartDefaults.borderColor;

  // 1. Urgency Distribution (Doughnut)
  const urgCtx = document.getElementById("chart-urgency");
  if (urgCtx) {
    analyticsCharts.urgency = new Chart(urgCtx, {
      type: "doughnut",
      data: {
        labels: ["Critical", "High", "Medium", "Low"],
        datasets: [{
          data: [
            data.urgency_distribution?.critical || 0,
            data.urgency_distribution?.high || 0,
            data.urgency_distribution?.medium || 0,
            data.urgency_distribution?.low || 0,
          ],
          backgroundColor: ["#E02424", "#F97316", "#E3A008", "#0E9F6E"],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { padding: 16, usePointStyle: true } },
        },
        cutout: "65%",
      },
    });
  }

  // 2. Issue Types (Bar)
  const issueCtx = document.getElementById("chart-issues");
  if (issueCtx) {
    const issueLabels = Object.keys(data.issue_type_distribution || {});
    const issueCounts = Object.values(data.issue_type_distribution || {});
    const issueColors = issueLabels.map(l => (ISSUE_TYPES[l] || ISSUE_TYPES.other).color);

    analyticsCharts.issues = new Chart(issueCtx, {
      type: "bar",
      data: {
        labels: issueLabels.map(l => (ISSUE_TYPES[l] || ISSUE_TYPES.other).label),
        datasets: [{
          label: "Reports",
          data: issueCounts,
          backgroundColor: issueColors.map(c => c + "CC"),
          borderColor: issueColors,
          borderWidth: 1,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.05)" } },
          x: { grid: { display: false } },
        },
      },
    });
  }

  // 3. Top Zones (Horizontal Bar)
  const zoneCtx = document.getElementById("chart-zones");
  if (zoneCtx) {
    const zonePairs = Object.entries(data.zone_distribution || {}).sort((a, b) => b[1] - a[1]).slice(0, 8);
    analyticsCharts.zones = new Chart(zoneCtx, {
      type: "bar",
      data: {
        labels: zonePairs.map(z => z[0]),
        datasets: [{
          label: "Needs",
          data: zonePairs.map(z => z[1]),
          backgroundColor: "rgba(26, 86, 219, 0.6)",
          borderColor: "#1A56DB",
          borderWidth: 1,
          borderRadius: 6,
        }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { grid: { display: false } },
        },
      },
    });
  }

  // 4. Data Sources (Pie)
  const srcCtx = document.getElementById("chart-sources");
  if (srcCtx) {
    const srcLabels = Object.keys(data.source_distribution || {});
    const srcCounts = Object.values(data.source_distribution || {});
    const srcColors = ["#1A56DB", "#7C3AED", "#DB2777", "#06B6D4", "#F59E0B"];

    analyticsCharts.sources = new Chart(srcCtx, {
      type: "pie",
      data: {
        labels: srcLabels.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
        datasets: [{
          data: srcCounts,
          backgroundColor: srcColors.slice(0, srcLabels.length),
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { padding: 16, usePointStyle: true } },
        },
      },
    });
  }

  // 5. Volunteer Stats (Bar)
  const volCtx = document.getElementById("chart-volunteers");
  if (volCtx) {
    const vs = data.volunteer_stats || {};
    analyticsCharts.volunteers = new Chart(volCtx, {
      type: "bar",
      data: {
        labels: ["Total", "Available", "Assigned", "Tasks Done", "People Helped (÷10)"],
        datasets: [{
          label: "Count",
          data: [vs.total || 0, vs.available || 0, vs.assigned || 0, vs.total_tasks_completed || 0, Math.round((vs.total_people_helped || 0) / 10)],
          backgroundColor: ["#1A56DB99", "#0E9F6E99", "#F9731699", "#7C3AED99", "#06B6D499"],
          borderColor: ["#1A56DB", "#0E9F6E", "#F97316", "#7C3AED", "#06B6D4"],
          borderWidth: 1,
          borderRadius: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.05)" } },
          x: { grid: { display: false } },
        },
      },
    });
  }

  // 6. Status Distribution (Doughnut)
  const statusCtx = document.getElementById("chart-status");
  if (statusCtx) {
    const statusLabels = Object.keys(data.status_distribution || {});
    const statusCounts = Object.values(data.status_distribution || {});
    const statusColors = { open: "#E3A008", assigned: "#1A56DB", resolved: "#0E9F6E", flagged: "#E02424" };

    analyticsCharts.status = new Chart(statusCtx, {
      type: "doughnut",
      data: {
        labels: statusLabels.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
        datasets: [{
          data: statusCounts,
          backgroundColor: statusLabels.map(s => statusColors[s] || "#6B7280"),
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { padding: 16, usePointStyle: true } },
        },
        cutout: "65%",
      },
    });
  }
}

function computeLocalAnalytics() {
  const needs = AppState.needs;
  const volunteers = AppState.volunteers;

  const urgency_distribution = { critical: 0, high: 0, medium: 0, low: 0 };
  const issue_type_distribution = {};
  const zone_distribution = {};
  const status_distribution = {};
  const source_distribution = {};

  needs.forEach(n => {
    urgency_distribution[n.urgency_label] = (urgency_distribution[n.urgency_label] || 0) + 1;
    issue_type_distribution[n.issue_type] = (issue_type_distribution[n.issue_type] || 0) + 1;
    zone_distribution[n.zone || "Unknown"] = (zone_distribution[n.zone || "Unknown"] || 0) + 1;
    status_distribution[n.status || "open"] = (status_distribution[n.status || "open"] || 0) + 1;
    source_distribution[n.source || "unknown"] = (source_distribution[n.source || "unknown"] || 0) + 1;
  });

  return {
    urgency_distribution,
    issue_type_distribution,
    zone_distribution,
    status_distribution,
    source_distribution,
    volunteer_stats: {
      total: volunteers.length,
      available: volunteers.filter(v => v.status === "available").length,
      assigned: volunteers.filter(v => v.status === "assigned").length,
      total_people_helped: volunteers.reduce((s, v) => s + (v.impact_stats?.total_people_helped || 0), 0),
      total_tasks_completed: volunteers.reduce((s, v) => s + (v.impact_stats?.total_tasks_completed || 0), 0),
    },
  };
}

// -- API Key Monitor (SuperAdmin) ---------------------------------
async function renderAPIHealth() {
  const tbody = document.getElementById("api-keys-table-body");
  if (!tbody) return;

  try {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 2rem;">Loading API health data...</td></tr>';
    
    // Add token if using auth
    const headers = { "Content-Type": "application/json" };
    // Call the new health endpoint
    const resp = await fetch(`${FUNCTIONS_BASE}/api/system/keys/health`, { headers });
    
    if (!resp.ok) {
      throw new Error(`HTTP error! status: ${resp.status}`);
    }
    
    const data = await resp.json();
    
    if (data.status !== "success" || !data.keys) {
      throw new Error(data.message || "Failed to load API health");
    }

    const { summary, keys } = data.keys;

    // Update summary stats
    document.getElementById("api-total-keys").textContent = summary.total_keys || 0;
    document.getElementById("api-healthy-keys").textContent = summary.healthy_keys || 0;
    document.getElementById("api-rate-limited").textContent = summary.rate_limited_keys || 0;
    document.getElementById("api-retired-keys").textContent = summary.retired_keys || 0;

    // Render table
    tbody.innerHTML = "";
    
    const sortedKeys = Object.entries(keys || {}).sort((a, b) => {
      const statusOrder = { active: 1, rate_limited: 2, retired: 3 };
      return (statusOrder[a[1].status] || 9) - (statusOrder[b[1].status] || 9);
    });

    if (sortedKeys.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 2rem; color: var(--text-muted);">No Gemini API keys configured.</td></tr>';
      return;
    }

    for (const [keyIndex, info] of sortedKeys) {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-color)";
      
      let statusHtml = "";
      if (info.status === "active") statusHtml = '<span class="urgency-badge low">Active</span>';
      else if (info.status === "rate_limited") statusHtml = '<span class="urgency-badge medium">Rate Limited</span>';
      else statusHtml = '<span class="urgency-badge critical">Retired</span>';

      const cooldown = info.cooldown_remaining_s > 0 ? info.cooldown_remaining_s.toFixed(1) + 's' : '-';
      
      tr.innerHTML = `
        <td style="padding: var(--space-md); font-family: monospace;">...${info.key_suffix || ''}</td>
        <td style="padding: var(--space-md);">${statusHtml}</td>
        <td style="padding: var(--space-md);">${info.rpm_used || 0}</td>
        <td style="padding: var(--space-md);">${info.rpd_used || 0}</td>
        <td style="padding: var(--space-md); color: ${info.failure_count > 0 ? 'var(--danger-color)' : 'inherit'};">${info.failure_count || 0}</td>
        <td style="padding: var(--space-md);">${cooldown}</td>
      `;
      tbody.appendChild(tr);
    }
    
  } catch (err) {
    console.error("API Health error:", err);
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem; color: var(--danger-color);"><span class="material-icons-outlined">error</span> ${err.message}</td></tr>`;
  }
}
