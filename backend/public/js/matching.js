/* ═══════════════════════════════════════════════════════════
   AlloCare: Volunteer Matching (Client-Side)
   Calls backend API or runs local matching for demo mode.
   Shows top-3 matched volunteers with explainability.
   ═════════════════════════════════════════════════════════ */

async function matchVolunteers(needId) {
  const need = AppState.needs.find(n => n.id === needId);
  if (!need) return;

  const matchSection = document.getElementById("match-section");
  const matchResults = document.getElementById("match-results");

  matchSection.style.display = "block";
  matchResults.innerHTML = `
    <div style="text-align:center;padding:var(--space-lg);">
      <div class="loading-spinner" style="margin:0 auto;"></div>
      <p style="color:var(--text-muted);font-size:var(--font-xs);margin-top:var(--space-sm);">
        Finding best matches...
      </p>
    </div>`;

  try {
    // Try backend API first
    const response = await fetch(`${FUNCTIONS_BASE}/api/match_volunteers?need_id=${needId}`);
    if (response.ok) {
      const data = await response.json();
      if (data.matches && data.matches.length > 0) {
        renderMatchResults(data.matches, needId);
        return;
      }
    }
  } catch (e) {
    console.log("Using local matching:", e.message);
  }

  // Local matching algorithm (same logic as server)
  const matches = runLocalMatching(need, AppState.volunteers);

  // Simulate processing delay for visual effect
  await new Promise(resolve => setTimeout(resolve, 800));
  renderMatchResults(matches, needId);

  // Draw routes on map
  if (need.lat && need.lng && matches.length > 0) {
    drawVolunteerRoutes(matches, need.lat, need.lng);
  }
}

function runLocalMatching(need, volunteers) {
  const requiredSkills = (need.required_skills || []).map(s => s.toLowerCase());
  const candidates = [];

  const availableVols = volunteers.filter(v => v.status === "available");

  for (const v of availableVols) {
    const volSkills = (v.skills || []).map(s => s.toLowerCase());

    // Skill overlap score [0, 1]
    let skillScore;
    let matchedSkills;
    if (requiredSkills.length > 0) {
      matchedSkills = requiredSkills.filter(rs =>
        volSkills.some(vs => vs.includes(rs) || rs.includes(vs))
      );
      skillScore = matchedSkills.length / requiredSkills.length;
    } else {
      matchedSkills = [];
      skillScore = 0.5;
    }

    // Proximity score: Haversine distance
    let distKm = 5.0; // default
    if (v.lat && v.lng && need.lat && need.lng) {
      distKm = haversine(v.lat, v.lng, need.lat, need.lng);
    } else if (v.zone && need.zone && v.zone.toLowerCase() === need.zone.toLowerCase()) {
      distKm = 1.0;
    }

    // Hard cutoff: relaxed for pan-India
    const maxDist = v.max_distance_km || 30;
    if (distKm > maxDist * 3) continue;  // only skip if 3x beyond range

    const beyondRange = distKm > maxDist;
    const proximityScore = 1.0 / (1.0 + distKm * 0.1);

    // Availability score
    const availScore = v.status === "available" ? 1.0 : 0.3;

    // Composite score with range penalty
    const rangeFactor = beyondRange ? 0.5 : 1.0;
    const matchScore = skillScore * proximityScore * availScore * rangeFactor;

    // Build explanation
    const parts = [];
    if (matchedSkills.length > 0) {
      parts.push(`${matchedSkills.join(", ")} ✓`);
    } else if (requiredSkills.length === 0) {
      parts.push("No specific skills required ✓");
    }
    parts.push(`${distKm.toFixed(1)}km away ✓`);
    if (availScore >= 1.0) parts.push("Available now ✓");

    candidates.push({
      volunteer_id: v.id,
      volunteer_name: v.display_name,
      lat: v.lat || 0,
      lng: v.lng || 0,
      skills: v.skills || [],
      skills_matched: matchedSkills,
      distance_km: Math.round(distKm * 10) / 10,
      road_distance_km: Math.round(distKm * 1.4 * 10) / 10,
      match_score: Math.round(matchScore * 10000) / 10000,
      explanation: "Matched because: " + parts.join(" · "),
      impact_points: v.impact_points || 0,
      beyond_range: beyondRange,
    });
  }

  // Sort by match_score descending, return top 5
  candidates.sort((a, b) => b.match_score - a.match_score);
  return candidates.slice(0, 5);
}

function renderMatchResults(matches, needId) {
  const matchResults = document.getElementById("match-results");

  if (!matches || matches.length === 0) {
    matchResults.innerHTML = `
      <div style="text-align:center;padding:var(--space-lg);color:var(--text-muted);">
        <span class="material-icons-outlined" style="font-size:32px;">person_off</span>
        <p style="font-size:var(--font-sm);margin-top:var(--space-sm);">No available volunteers match</p>
      </div>`;
    return;
  }

  matchResults.innerHTML = matches.map((match, i) => {
    const color = getAvatarColor(match.volunteer_name);
    const initials = getInitials(match.volunteer_name);
    const scorePercent = Math.max(1, Math.round(match.match_score * 100));
    const scoreColor = scorePercent >= 50 ? "var(--green)" : scorePercent >= 20 ? "var(--amber)" : "var(--cyan)";

    // Component scores from backend
    const skillPct = match.skill_score != null ? Math.round(match.skill_score * 100) : null;
    const proxPct = match.proximity_score != null ? Math.round(match.proximity_score * 100) : null;
    const availPct = match.availability_score != null ? Math.round(match.availability_score * 100) : null;

    const componentBars = (skillPct != null) ? `
      <div style="display:flex;gap:var(--space-xs);margin:var(--space-xs) 0 var(--space-sm);flex-wrap:wrap;">
        <span style="font-size:10px;padding:2px 6px;border-radius:8px;background:rgba(14,159,110,0.15);color:#0E9F6E;">Skill ${skillPct}%</span>
        <span style="font-size:10px;padding:2px 6px;border-radius:8px;background:rgba(26,86,219,0.15);color:#1A56DB;">Proximity ${proxPct}%</span>
        <span style="font-size:10px;padding:2px 6px;border-radius:8px;background:rgba(234,179,8,0.15);color:#E3A008;">Avail ${availPct}%</span>
      </div>` : "";

    return `
      <div class="match-card" style="animation-delay:${i * 150}ms;">
        <div class="match-card-header">
          <div style="display:flex;align-items:center;gap:var(--space-sm);">
            <span class="match-card-rank">${i + 1}</span>
            <div class="volunteer-avatar" style="background:${color};width:32px;height:32px;font-size:11px;">
              ${initials}
            </div>
          </div>
          <span class="match-card-score" style="color:${scoreColor};">${scorePercent}% match</span>
        </div>
        <div class="match-card-name">${match.volunteer_name}</div>
        <div class="match-card-explanation">${match.explanation}</div>
        ${componentBars}
        <div style="display:flex;gap:var(--space-sm);margin-bottom:var(--space-sm);">
          <span class="skill-chip" style="background:var(--primary-light);color:var(--primary);">
            📍 ${match.road_distance_km || match.distance_km}km road
          </span>
          <span class="skill-chip" style="background:var(--green-light);color:var(--green);">
            ⭐ ${match.impact_points} pts
          </span>
          ${match.beyond_range ? '<span class="skill-chip" style="background:rgba(234,179,8,0.15);color:#E3A008;">⚠️ Far</span>' : ''}
        </div>
        <div class="match-card-actions">
          <button class="btn-assign" onclick="handleAssignVolunteer('${needId}', '${match.volunteer_id}', ${match.match_score}, '${match.explanation.replace(/'/g, "\\'")}')">
            <span class="material-icons-outlined" style="font-size:14px;margin-right:4px;">send</span>
            Assign Volunteer
          </button>
        </div>
      </div>`;
  }).join("");
}

async function handleAssignVolunteer(needId, volunteerId, matchScore, explanation) {
  const volunteer = AppState.volunteers.find(v => v.id === volunteerId);
  if (!volunteer) return;

  try {
    await assignVolunteer(needId, volunteer, matchScore, explanation);
    showToast(`✅ ${volunteer.display_name} assigned successfully!`, "success");

    // Update local state
    volunteer.status = "assigned";
    const need = AppState.needs.find(n => n.id === needId);
    if (need) need.status = "assigned";

    renderVolunteerList();
    renderNeedsFeed();
    updateMapMarkers();
    updateCounts();

    // Hide match results
    document.getElementById("match-section").style.display = "none";
  } catch (error) {
    // For demo mode, update locally
    volunteer.status = "assigned";
    showToast(`✅ ${volunteer.display_name} assigned successfully!`, "success");
    renderVolunteerList();
  }
}

// ── Haversine Distance ──────────────────────────────────────
function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function toRad(deg) { return deg * Math.PI / 180; }
