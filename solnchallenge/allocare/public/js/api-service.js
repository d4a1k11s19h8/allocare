/* ═══════════════════════════════════════════════════════════
   AlloCare — API Service (replaces Firestore)
   REST API calls to our FastAPI backend
   ═════════════════════════════════════════════════════════ */

// ── Load data from backend API ─────────────────────────────
async function initializeData() {
  await Promise.all([fetchNeeds(), fetchVolunteers()]);
  // Pre-load auth screen stats
  updateCounts();
}

async function fetchNeeds() {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/needs?limit=100`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    AppState.needs = data.needs || [];
    renderNeedsFeed();
    updateMapMarkers();
    updateCounts();
  } catch (e) {
    console.error("Fetch needs error:", e);
    // Fallback to demo data
    if (AppState.needs.length === 0) {
      loadDemoData();
    }
  }
}

async function fetchVolunteers() {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/volunteers?limit=50`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    AppState.volunteers = data.volunteers || [];
    renderVolunteerList();
  } catch (e) {
    console.error("Fetch volunteers error:", e);
  }
}

// ── CRUD Operations ───────────────────────────────────────
async function createNeedReport(data) {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/needs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        raw_text: data.raw_text || data.summary || "",
        source: data.source || "manual",
        zone: data.zone || "",
        issue_type: data.issue_type || "other",
        severity_score: data.severity_score || 5,
        affected_count: data.affected_count || null,
      }),
    });
    const result = await resp.json();
    // Refresh data
    await fetchNeeds();
    return result.id;
  } catch (error) {
    console.error("Create report error:", error);
    throw error;
  }
}

async function processReport(rawText, source = "manual") {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/process_report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText, source: source }),
    });
    const result = await resp.json();
    // Refresh data to get processed report
    await fetchNeeds();
    return result;
  } catch (error) {
    console.error("Process report error:", error);
    throw error;
  }
}

async function assignVolunteer(needId, volunteer, matchScore, explanation) {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/assignments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        need_id: needId,
        volunteer_id: volunteer.id || volunteer.volunteer_id,
        org_id: AppState.orgId,
        match_score: matchScore,
        match_explanation: explanation,
      }),
    });
    const result = await resp.json();
    // Refresh data
    await Promise.all([fetchNeeds(), fetchVolunteers()]);
    return result.assignment_id;
  } catch (error) {
    console.error("Assignment error:", error);
    throw error;
  }
}

async function flagUrgencyScore(needId, correctScore, reason) {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/flag_urgency_score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        need_id: needId,
        correct_score: correctScore,
        reason: reason,
        flagged_by: AppState.user?.uid || "coordinator",
      }),
    });
    const result = await resp.json();
    showToast("Urgency score updated to " + correctScore, "success");
    // Refresh data
    await fetchNeeds();
    return result;
  } catch (error) {
    console.error("Flag error:", error);
    showToast("Failed to update score", "error");
  }
}

async function extractOCR(imageData) {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/ocr`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_data: imageData }),
    });
    const result = await resp.json();
    return result.text || "";
  } catch (error) {
    console.error("OCR error:", error);
    return "";
  }
}

async function uploadCSV(file) {
  try {
    const formData = new FormData();
    formData.append("file", file);
    const resp = await fetch(`${FUNCTIONS_BASE}/api/process_csv`, {
      method: "POST",
      body: formData,
    });
    const result = await resp.json();
    await fetchNeeds();
    return result;
  } catch (error) {
    console.error("CSV upload error:", error);
    throw error;
  }
}

async function fetchAnalytics() {
  try {
    const resp = await fetch(`${FUNCTIONS_BASE}/api/analytics`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (e) {
    console.error("Analytics fetch error:", e);
    return null;
  }
}

// ── Demo Data (when backend is unavailable) ─────────────
function loadDemoData() {
  AppState.needs = generateDemoNeeds();
  AppState.volunteers = generateDemoVolunteers();
  renderNeedsFeed();
  renderVolunteerList();
  updateMapMarkers();
  updateCounts();
}

function generateDemoNeeds() {
  return [
    { id: "n1", zone: "Dharavi", lat: 19.0441, lng: 72.8557, issue_type: "food", severity_score: 9, urgency_score: 95, urgency_label: "critical", affected_count: 200, summary: "Severe food shortage affecting over 200 families. Children and elderly most affected.", required_skills: ["food distribution", "hindi speaking"], recommended_volunteer_count: 5, status: "open", source: "photo", created_at: new Date(Date.now() - 2*3600000).toISOString(), report_frequency_30d: 8, trend_direction: "rising", coordinator_explanation: "In Dharavi's sector 5, a severe food crisis is unfolding. Over 200 families need immediate assistance." },
    { id: "n2", zone: "Dharavi", lat: 19.0438, lng: 72.8560, issue_type: "water", severity_score: 8, urgency_score: 88, urgency_label: "critical", affected_count: 150, summary: "Water supply contaminated in sector 5. Residents with stomach illness.", required_skills: ["water purification", "plumbing"], recommended_volunteer_count: 3, status: "open", source: "manual", created_at: new Date(Date.now() - 4*3600000).toISOString(), report_frequency_30d: 5, trend_direction: "rising" },
    { id: "n3", zone: "Dharavi", lat: 19.0430, lng: 72.8550, issue_type: "health", severity_score: 9, urgency_score: 92, urgency_label: "critical", affected_count: 175, summary: "Medical camp urgently needed — increasing dengue cases. 3 children hospitalized.", required_skills: ["medical first aid", "nursing"], recommended_volunteer_count: 4, status: "open", source: "whatsapp", created_at: new Date(Date.now() - 1*3600000).toISOString(), report_frequency_30d: 6, trend_direction: "rising" },
    { id: "n4", zone: "Kurla", lat: 19.0724, lng: 72.8787, issue_type: "health", severity_score: 7, urgency_score: 72, urgency_label: "high", affected_count: 80, summary: "Healthcare facility severely understaffed. Patients waiting 6+ hours.", required_skills: ["medical doctor", "patient care"], recommended_volunteer_count: 2, status: "open", source: "csv", created_at: new Date(Date.now() - 12*3600000).toISOString(), report_frequency_30d: 3, trend_direction: "stable" },
    { id: "n5", zone: "Govandi", lat: 19.0537, lng: 72.9148, issue_type: "housing", severity_score: 8, urgency_score: 85, urgency_label: "high", affected_count: 60, summary: "Multiple families in structurally damaged housing. Monsoon risk.", required_skills: ["construction", "civil engineering"], recommended_volunteer_count: 3, status: "open", source: "manual", created_at: new Date(Date.now() - 6*3600000).toISOString(), report_frequency_30d: 4, trend_direction: "rising" },
    { id: "n6", zone: "Malad", lat: 19.1860, lng: 72.8485, issue_type: "education", severity_score: 6, urgency_score: 62, urgency_label: "high", affected_count: 120, summary: "School closed due to structural issues. 120 students need temporary facility.", required_skills: ["teaching", "event coordination"], recommended_volunteer_count: 3, status: "open", source: "csv", created_at: new Date(Date.now() - 24*3600000).toISOString(), report_frequency_30d: 2, trend_direction: "stable" },
    { id: "n7", zone: "Bandra East", lat: 19.0596, lng: 72.8413, issue_type: "safety", severity_score: 5, urgency_score: 42, urgency_label: "medium", affected_count: 300, summary: "Broken street lights creating dangerous conditions at night.", required_skills: ["electrical"], recommended_volunteer_count: 2, status: "open", source: "manual", created_at: new Date(Date.now() - 48*3600000).toISOString(), report_frequency_30d: 2, trend_direction: "stable" },
    { id: "n8", zone: "Kurla", lat: 19.0740, lng: 72.8800, issue_type: "water", severity_score: 8, urgency_score: 90, urgency_label: "critical", affected_count: 200, summary: "Clean drinking water crisis. Municipal water tanker absent 5 days.", required_skills: ["water purification", "logistics"], recommended_volunteer_count: 3, status: "open", source: "photo", created_at: new Date(Date.now() - 3*3600000).toISOString(), report_frequency_30d: 7, trend_direction: "rising" },
  ];
}

function generateDemoVolunteers() {
  return [
    { id: "v1", display_name: "Priya Sharma", email: "priya@example.com", lat: 19.0450, lng: 72.8570, zone: "Dharavi", skills: ["food distribution", "medical first aid", "hindi speaking"], status: "available", impact_points: 580, impact_stats: { total_tasks_completed: 23, total_people_helped: 456 } },
    { id: "v2", display_name: "Rahul Deshmukh", email: "rahul@example.com", lat: 19.0730, lng: 72.8790, zone: "Kurla", skills: ["construction", "plumbing", "electrical"], status: "available", impact_points: 320, impact_stats: { total_tasks_completed: 12, total_people_helped: 180 } },
    { id: "v3", display_name: "Anita Patel", email: "anita@example.com", lat: 19.0540, lng: 72.9150, zone: "Govandi", skills: ["teaching", "counseling"], status: "available", impact_points: 680, impact_stats: { total_tasks_completed: 18, total_people_helped: 540 } },
    { id: "v4", display_name: "Mohammed Shaikh", email: "mohammed@example.com", lat: 19.0440, lng: 72.8555, zone: "Dharavi", skills: ["cooking", "food distribution", "driving"], status: "available", impact_points: 1450, impact_stats: { total_tasks_completed: 45, total_people_helped: 1200 } },
    { id: "v5", display_name: "Sneha Nair", email: "sneha@example.com", lat: 19.1200, lng: 72.8470, zone: "Andheri East", skills: ["nursing", "medical first aid", "patient care"], status: "available", impact_points: 890, impact_stats: { total_tasks_completed: 31, total_people_helped: 620 } },
    { id: "v6", display_name: "Vikram Singh", email: "vikram@example.com", lat: 19.1870, lng: 72.8490, zone: "Malad East", skills: ["construction", "carpentry", "heavy lifting"], status: "assigned", impact_points: 210, impact_stats: { total_tasks_completed: 8, total_people_helped: 85 } },
  ];
}
