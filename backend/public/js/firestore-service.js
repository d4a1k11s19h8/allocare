/* ═══════════════════════════════════════════════════════════
   AlloCare — Firestore Data Service
   Real-time listeners + CRUD + Demo data seeding
   ═════════════════════════════════════════════════════════ */

// ── Real-time listener for need reports ────────────────────
function initializeData() {
  listenToNeeds();
  listenToVolunteers();
}

function listenToNeeds() {
  db.collection("need_reports")
    .where("status", "in", ["open", "assigned", "flagged"])
    .orderBy("urgency_score", "desc")
    .limit(100)
    .onSnapshot(snapshot => {
      AppState.needs = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data(),
      }));
      renderNeedsFeed();
      updateMapMarkers();
      updateCounts();
    }, error => {
      console.error("Needs listener error:", error);
      // If Firestore unavailable, use demo data
      if (AppState.needs.length === 0) {
        loadDemoData();
      }
    });
}

function listenToVolunteers() {
  db.collection("volunteers")
    .orderBy("impact_points", "desc")
    .limit(50)
    .onSnapshot(snapshot => {
      AppState.volunteers = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data(),
      }));
      renderVolunteerList();
    }, error => {
      console.error("Volunteers listener error:", error);
    });
}

// ── CRUD Operations ───────────────────────────────────────
async function createNeedReport(data) {
  try {
    const docRef = await db.collection("need_reports").add({
      ...data,
      org_id: AppState.orgId,
      status: "open",
      urgency_score: 0,
      urgency_label: "low",
      created_at: firebase.firestore.FieldValue.serverTimestamp(),
    });
    return docRef.id;
  } catch (error) {
    console.error("Create report error:", error);
    throw error;
  }
}

async function assignVolunteer(needId, volunteer, matchScore, explanation) {
  try {
    const assignmentRef = await db.collection("assignments").add({
      need_report_id: needId,
      volunteer_id: volunteer.id,
      org_id: AppState.orgId,
      status: "pending",
      match_score: matchScore,
      match_explanation: explanation,
      assigned_at: firebase.firestore.FieldValue.serverTimestamp(),
    });

    // Update volunteer status
    await db.collection("volunteers").doc(volunteer.id).update({
      status: "assigned",
    });

    // Update need status
    await db.collection("need_reports").doc(needId).update({
      status: "assigned",
    });

    return assignmentRef.id;
  } catch (error) {
    console.error("Assignment error:", error);
    throw error;
  }
}

async function flagUrgencyScore(needId, correctScore, reason) {
  try {
    await db.collection("urgency_corrections").add({
      need_id: needId,
      corrected_score: correctScore,
      reason: reason,
      flagged_by: AppState.user.uid,
      flagged_at: firebase.firestore.FieldValue.serverTimestamp(),
    });

    let label = "low";
    if (correctScore >= 86) label = "critical";
    else if (correctScore >= 61) label = "high";
    else if (correctScore >= 31) label = "medium";

    await db.collection("need_reports").doc(needId).update({
      urgency_score: correctScore,
      urgency_label: label,
      status: "flagged",
      flagged_by: AppState.user.uid,
      flag_reason: reason,
    });

    showToast("Urgency score updated to " + correctScore, "success");
  } catch (error) {
    console.error("Flag error:", error);
    showToast("Failed to update score", "error");
  }
}

// ── Demo Data (when Firestore is unavailable) ─────────────
function loadDemoData() {
  AppState.needs = generateDemoNeeds();
  AppState.volunteers = generateDemoVolunteers();
  renderNeedsFeed();
  renderVolunteerList();
  updateMapMarkers();
  updateCounts();
}

function generateDemoNeeds() {
  const needs = [
    { id: "n1", zone: "Dharavi", lat: 19.0441, lng: 72.8557, issue_type: "food", severity_score: 9, urgency_score: 95, urgency_label: "critical", affected_count: 200, summary: "Severe food shortage affecting over 200 families. Children and elderly most affected.", required_skills: ["food distribution", "hindi speaking"], recommended_volunteer_count: 5, status: "open", source: "photo", created_at: new Date(Date.now() - 2*3600000), report_frequency_30d: 8, trend_direction: "rising" },
    { id: "n2", zone: "Dharavi", lat: 19.0438, lng: 72.8560, issue_type: "water", severity_score: 8, urgency_score: 88, urgency_label: "critical", affected_count: 150, summary: "Water supply contaminated in sector 5. Residents with stomach illness.", required_skills: ["water purification", "plumbing"], recommended_volunteer_count: 3, status: "open", source: "manual", created_at: new Date(Date.now() - 4*3600000), report_frequency_30d: 5, trend_direction: "rising" },
    { id: "n3", zone: "Dharavi", lat: 19.0430, lng: 72.8550, issue_type: "health", severity_score: 9, urgency_score: 92, urgency_label: "critical", affected_count: 175, summary: "Medical camp urgently needed — increasing dengue cases. 3 children hospitalized.", required_skills: ["medical first aid", "nursing"], recommended_volunteer_count: 4, status: "open", source: "whatsapp", created_at: new Date(Date.now() - 1*3600000), report_frequency_30d: 6, trend_direction: "rising" },
    { id: "n4", zone: "Kurla", lat: 19.0724, lng: 72.8787, issue_type: "health", severity_score: 7, urgency_score: 72, urgency_label: "high", affected_count: 80, summary: "Healthcare facility severely understaffed. Patients waiting 6+ hours.", required_skills: ["medical doctor", "patient care"], recommended_volunteer_count: 2, status: "open", source: "csv", created_at: new Date(Date.now() - 12*3600000), report_frequency_30d: 3, trend_direction: "stable" },
    { id: "n5", zone: "Govandi", lat: 19.0537, lng: 72.9148, issue_type: "housing", severity_score: 8, urgency_score: 85, urgency_label: "high", affected_count: 60, summary: "Multiple families in structurally damaged housing. Monsoon risk.", required_skills: ["construction", "civil engineering"], recommended_volunteer_count: 3, status: "open", source: "manual", created_at: new Date(Date.now() - 6*3600000), report_frequency_30d: 4, trend_direction: "rising" },
    { id: "n6", zone: "Malad", lat: 19.1860, lng: 72.8485, issue_type: "education", severity_score: 6, urgency_score: 62, urgency_label: "high", affected_count: 120, summary: "School closed due to structural issues. 120 students need temporary facility.", required_skills: ["teaching", "event coordination"], recommended_volunteer_count: 3, status: "open", source: "csv", created_at: new Date(Date.now() - 24*3600000), report_frequency_30d: 2, trend_direction: "stable" },
    { id: "n7", zone: "Bandra East", lat: 19.0596, lng: 72.8413, issue_type: "safety", severity_score: 5, urgency_score: 42, urgency_label: "medium", affected_count: 300, summary: "Broken street lights creating dangerous conditions at night.", required_skills: ["electrical"], recommended_volunteer_count: 2, status: "open", source: "manual", created_at: new Date(Date.now() - 48*3600000), report_frequency_30d: 2, trend_direction: "stable" },
    { id: "n8", zone: "Kurla", lat: 19.0740, lng: 72.8800, issue_type: "water", severity_score: 8, urgency_score: 90, urgency_label: "critical", affected_count: 200, summary: "Clean drinking water crisis. Municipal water tanker absent 5 days.", required_skills: ["water purification", "logistics"], recommended_volunteer_count: 3, status: "open", source: "photo", created_at: new Date(Date.now() - 3*3600000), report_frequency_30d: 7, trend_direction: "rising" },
    { id: "n9", zone: "Andheri West", lat: 19.1360, lng: 72.8264, issue_type: "health", severity_score: 8, urgency_score: 82, urgency_label: "high", affected_count: 200, summary: "Community health clinic lost its doctor. 200 patients/week without medical access.", required_skills: ["medical doctor", "nursing"], recommended_volunteer_count: 2, status: "open", source: "manual", created_at: new Date(Date.now() - 8*3600000), report_frequency_30d: 4, trend_direction: "rising" },
    { id: "n10", zone: "Sion", lat: 19.0404, lng: 72.8620, issue_type: "food", severity_score: 8, urgency_score: 87, urgency_label: "critical", affected_count: 100, summary: "Food bank running low — only 3 days of supply remaining. Serves 100 families daily.", required_skills: ["food distribution", "cooking"], recommended_volunteer_count: 4, status: "open", source: "csv", created_at: new Date(Date.now() - 5*3600000), report_frequency_30d: 5, trend_direction: "rising" },
    { id: "n11", zone: "Vikhroli", lat: 19.0980, lng: 72.9167, issue_type: "water", severity_score: 8, urgency_score: 86, urgency_label: "critical", affected_count: 350, summary: "Water pipeline burst — entire neighborhood without water for 3 days.", required_skills: ["plumbing", "construction"], recommended_volunteer_count: 4, status: "open", source: "whatsapp", created_at: new Date(Date.now() - 1*3600000), report_frequency_30d: 3, trend_direction: "rising" },
    { id: "n12", zone: "Worli", lat: 19.0088, lng: 72.8170, issue_type: "housing", severity_score: 8, urgency_score: 78, urgency_label: "high", affected_count: 60, summary: "Unsafe building with cracks in walls. 12 families at risk.", required_skills: ["structural assessment", "civil engineering"], recommended_volunteer_count: 2, status: "open", source: "manual", created_at: new Date(Date.now() - 18*3600000), report_frequency_30d: 2, trend_direction: "stable" },
    { id: "n13", zone: "Kurla West", lat: 19.0730, lng: 72.8770, issue_type: "safety", severity_score: 9, urgency_score: 91, urgency_label: "critical", affected_count: 15, summary: "Street children sleeping under bridge near railway station. Need shelter and food.", required_skills: ["social work", "child care"], recommended_volunteer_count: 3, status: "open", source: "manual", created_at: new Date(Date.now() - 2*3600000), report_frequency_30d: 6, trend_direction: "rising" },
    { id: "n14", zone: "Mankhurd", lat: 19.0635, lng: 72.9277, issue_type: "education", severity_score: 5, urgency_score: 35, urgency_label: "medium", affected_count: 45, summary: "Children not attending school — nearest school is 4km away. Need transport.", required_skills: ["driving", "teaching"], recommended_volunteer_count: 2, status: "open", source: "csv", created_at: new Date(Date.now() - 72*3600000), report_frequency_30d: 1, trend_direction: "stable" },
    { id: "n15", zone: "Dharavi", lat: 19.0445, lng: 72.8540, issue_type: "housing", severity_score: 9, urgency_score: 93, urgency_label: "critical", affected_count: 40, summary: "8 families displaced after fire in 13th compound. Currently sleeping on streets.", required_skills: ["construction", "carpentry", "logistics"], recommended_volunteer_count: 5, status: "open", source: "photo", created_at: new Date(Date.now() - 0.5*3600000), report_frequency_30d: 9, trend_direction: "rising" },
    { id: "n16", zone: "Kandivali", lat: 19.2045, lng: 72.8403, issue_type: "food", severity_score: 7, urgency_score: 68, urgency_label: "high", affected_count: 150, summary: "Community kitchen running out of funds. Feeds 150 people daily.", required_skills: ["cooking", "food distribution", "event coordination"], recommended_volunteer_count: 3, status: "open", source: "manual", created_at: new Date(Date.now() - 10*3600000), report_frequency_30d: 3, trend_direction: "stable" },
    { id: "n17", zone: "Dharavi", lat: 19.0446, lng: 72.8541, issue_type: "safety", severity_score: 9, urgency_score: 94, urgency_label: "critical", affected_count: 8, summary: "Child labor reported in leather workshop. 8 children aged 10-14 found working.", required_skills: ["social work", "legal aid"], recommended_volunteer_count: 2, status: "open", source: "manual", created_at: new Date(Date.now() - 1*3600000), report_frequency_30d: 4, trend_direction: "rising" },
    { id: "n18", zone: "Chembur", lat: 19.0620, lng: 72.8978, issue_type: "health", severity_score: 8, urgency_score: 75, urgency_label: "high", affected_count: 25, summary: "Elderly in Old Age Home running out of medications. Diabetes and BP medicines finished.", required_skills: ["pharmacy", "medical first aid"], recommended_volunteer_count: 1, status: "open", source: "csv", created_at: new Date(Date.now() - 14*3600000), report_frequency_30d: 2, trend_direction: "stable" },
    { id: "n19", zone: "Dharavi", lat: 19.0435, lng: 72.8545, issue_type: "education", severity_score: 4, urgency_score: 22, urgency_label: "low", affected_count: 60, summary: "Educational materials needed for community learning center. 60 students need textbooks.", required_skills: ["teaching"], recommended_volunteer_count: 1, status: "open", source: "csv", created_at: new Date(Date.now() - 96*3600000), report_frequency_30d: 1, trend_direction: "stable" },
    { id: "n20", zone: "Jogeshwari", lat: 19.1371, lng: 72.8570, issue_type: "safety", severity_score: 7, urgency_score: 65, urgency_label: "high", affected_count: 100, summary: "Women's safety patrol needed — multiple eve-teasing incidents near public toilet.", required_skills: ["women safety", "social work"], recommended_volunteer_count: 3, status: "open", source: "whatsapp", created_at: new Date(Date.now() - 15*3600000), report_frequency_30d: 3, trend_direction: "rising" },
  ];
  return needs;
}

function generateDemoVolunteers() {
  return [
    { id: "v1", display_name: "Priya Sharma", email: "priya@example.com", lat: 19.0450, lng: 72.8570, zone: "Dharavi", skills: ["food distribution", "medical first aid", "hindi speaking"], status: "available", impact_points: 580, impact_stats: { total_tasks_completed: 23, total_people_helped: 456 }, badges: ["first_responder", "streak_hero"] },
    { id: "v2", display_name: "Rahul Deshmukh", email: "rahul@example.com", lat: 19.0730, lng: 72.8790, zone: "Kurla", skills: ["construction", "plumbing", "electrical"], status: "available", impact_points: 320, impact_stats: { total_tasks_completed: 12, total_people_helped: 180 }, badges: ["data_pioneer"] },
    { id: "v3", display_name: "Anita Patel", email: "anita@example.com", lat: 19.0540, lng: 72.9150, zone: "Govandi", skills: ["teaching", "counseling"], status: "available", impact_points: 680, impact_stats: { total_tasks_completed: 18, total_people_helped: 540 }, badges: ["community_champion", "streak_hero"] },
    { id: "v4", display_name: "Mohammed Shaikh", email: "mohammed@example.com", lat: 19.0440, lng: 72.8555, zone: "Dharavi", skills: ["cooking", "food distribution", "driving"], status: "available", impact_points: 1450, impact_stats: { total_tasks_completed: 45, total_people_helped: 1200 }, badges: ["first_responder", "community_champion", "streak_hero"] },
    { id: "v5", display_name: "Sneha Nair", email: "sneha@example.com", lat: 19.1200, lng: 72.8470, zone: "Andheri East", skills: ["nursing", "medical first aid", "patient care"], status: "available", impact_points: 890, impact_stats: { total_tasks_completed: 31, total_people_helped: 620 }, badges: ["first_responder", "community_champion"] },
    { id: "v6", display_name: "Vikram Singh", email: "vikram@example.com", lat: 19.1870, lng: 72.8490, zone: "Malad East", skills: ["construction", "carpentry", "heavy lifting"], status: "assigned", impact_points: 210, impact_stats: { total_tasks_completed: 8, total_people_helped: 85 }, badges: [] },
    { id: "v7", display_name: "Fatima Khan", email: "fatima@example.com", lat: 19.0596, lng: 72.8413, zone: "Bandra East", skills: ["social work", "counseling", "legal aid"], status: "available", impact_points: 420, impact_stats: { total_tasks_completed: 15, total_people_helped: 275 }, badges: ["first_responder"] },
    { id: "v8", display_name: "Arjun Mehta", email: "arjun@example.com", lat: 19.0620, lng: 72.8980, zone: "Chembur", skills: ["pharmacy", "medical first aid", "data entry"], status: "available", impact_points: 250, impact_stats: { total_tasks_completed: 10, total_people_helped: 150 }, badges: [] },
    { id: "v9", display_name: "Ravi Kumar", email: "ravi@example.com", lat: 19.0404, lng: 72.8625, zone: "Sion", skills: ["driving", "food distribution", "logistics"], status: "available", impact_points: 1100, impact_stats: { total_tasks_completed: 35, total_people_helped: 900 }, badges: ["first_responder", "community_champion", "streak_hero"] },
    { id: "v10", display_name: "Kavitha Reddy", email: "kavitha@example.com", lat: 19.0197, lng: 72.8440, zone: "Dadar", skills: ["medical doctor", "patient care"], status: "offline", impact_points: 340, impact_stats: { total_tasks_completed: 8, total_people_helped: 160 }, badges: ["first_responder"] },
    { id: "v11", display_name: "Tushar Patil", email: "tushar@example.com", lat: 19.0088, lng: 72.8175, zone: "Worli", skills: ["civil engineering", "structural assessment"], status: "available", impact_points: 190, impact_stats: { total_tasks_completed: 6, total_people_helped: 120 }, badges: [] },
    { id: "v12", display_name: "Hassan Ali", email: "hassan@example.com", lat: 19.2045, lng: 72.8400, zone: "Kandivali", skills: ["cooking", "food distribution", "event coordination"], status: "available", impact_points: 820, impact_stats: { total_tasks_completed: 28, total_people_helped: 700 }, badges: ["first_responder", "streak_hero"] },
  ];
}
