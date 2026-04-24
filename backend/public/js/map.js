/* ═══════════════════════════════════════════════════════════
   AlloCare — Map Module
   • Leaflet.js + OpenStreetMap (FREE, no API key)
   • Leaflet Control Geocoder (FREE Places API alternative)
   • Shows both Need markers + Volunteer markers
   ═════════════════════════════════════════════════════════ */

let mapInstance = null;
let mapMarkers = [];          // need markers
let volunteerMarkers = [];    // volunteer markers
let routePolylines = [];      // route lines
let heatmapLayer = null;
let geocoderControl = null;
let showVolunteers = true;    // toggle state
let mapLayerFilter = "both";  // 'both', 'heatmap', 'volunteers'

function applyMapLayerFilter() {
  const select = document.getElementById("filter-map-layers");
  if (select) {
    mapLayerFilter = select.value;
    updateMapMarkers();
    updateVolunteerMarkers();
    fitMapToAllMarkers();
  }
}

// ── Custom Volunteer Icon ───────────────────────────────────
function createVolunteerIcon(status) {
  const color = status === "available" ? "#3B82F6" : "#F59E0B";
  const borderColor = status === "available" ? "#93C5FD" : "#FCD34D";

  return L.divIcon({
    className: "volunteer-marker-icon",
    html: `<div style="
      width: 28px; height: 28px;
      background: ${color};
      border: 2.5px solid ${borderColor};
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 0 10px ${color}60, 0 2px 8px rgba(0,0,0,0.4);
      transition: transform 0.2s;
      cursor: pointer;
    ">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
      </svg>
    </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
}

// ── Initialize Map ──────────────────────────────────────────
function initMap() {
  if (mapInstance) return;

  const indiaCenter = [21.0, 78.0];

  mapInstance = L.map("map", {
    center: indiaCenter,
    zoom: 5,
    zoomControl: false,
    attributionControl: false,
  });

  // Zoom control — top-left
  L.control.zoom({ position: "topleft" }).addTo(mapInstance);

  // ── Tile Layer: CartoDB Dark Matter (free, no API key) ────
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    subdomains: "abcd",
  }).addTo(mapInstance);

  // Attribution
  L.control.attribution({
    position: "bottomright",
    prefix: false,
  }).addAttribution('© <a href="https://www.openstreetmap.org/copyright">OSM</a> © <a href="https://carto.com/">CARTO</a>').addTo(mapInstance);

  // ── Geocoder: FREE Places API Alternative (Nominatim) ─────
  if (typeof L.Control.Geocoder !== "undefined") {
    geocoderControl = L.Control.Geocoder.nominatim({
      geocodingQueryParams: {
        countrycodes: "in",   // Bias results to India
        limit: 6,
      }
    });

    const searchControl = L.Control.geocoder({
      geocoder: geocoderControl,
      position: "topright",
      placeholder: "Search places (Nagpur, Delhi, Mumbai...)",
      defaultMarkGeocode: false,
      collapsed: true,
      showUniqueResult: true,
      suggestMinLength: 3,
      errorMessage: "No results found",
    }).on("markgeocode", function(e) {
      // When user selects a search result, fly to that location
      const bbox = e.geocode.bbox;
      if (bbox) {
        mapInstance.fitBounds(bbox, { maxZoom: 14, animate: true });
      } else {
        mapInstance.setView(e.geocode.center, 13, { animate: true });
      }
      // Add a temporary marker
      const marker = L.marker(e.geocode.center, {
        icon: L.divIcon({
          className: "search-result-marker",
          html: `<div style="
            width: 20px; height: 20px;
            background: #8B5CF6;
            border: 3px solid #C4B5FD;
            border-radius: 50%;
            box-shadow: 0 0 12px #8B5CF680;
          "></div>`,
          iconSize: [20, 20],
          iconAnchor: [10, 10],
        })
      }).addTo(mapInstance)
        .bindPopup(`<div style="font-family:Inter,sans-serif;font-size:13px;">
          <strong>📍 ${e.geocode.name}</strong>
        </div>`)
        .openPopup();

      // Remove after 10 seconds
      setTimeout(() => mapInstance.removeLayer(marker), 10000);
    }).addTo(mapInstance);
  }

  // Render markers if data is already loaded
  if (AppState.needs.length > 0) {
    updateMapMarkers();
  }
  if (AppState.volunteers && AppState.volunteers.length > 0) {
    updateVolunteerMarkers();
  }
}

// ── Update Need Markers (urgency heatmap) ───────────────────
function updateMapMarkers() {
  if (!mapInstance) {
    const mapEl = document.getElementById("map");
    if (mapEl && mapEl.offsetHeight > 0) initMap();
    if (!mapInstance) return;
  }

  // Clear existing need markers
  mapMarkers.forEach(m => mapInstance.removeLayer(m));
  mapMarkers = [];

  // Clear existing heatmap
  if (heatmapLayer) {
    mapInstance.removeLayer(heatmapLayer);
    heatmapLayer = null;
  }

  if (mapLayerFilter === "volunteers") {
    // Only show volunteers, so skip rendering needs and heatmap
    return;
  }

  const filteredNeeds = getFilteredNeeds();
  const heatData = [];

  filteredNeeds.forEach(need => {
    if (!need.lat || !need.lng) return;

    const urgency = URGENCY_LEVELS[need.urgency_label] || URGENCY_LEVELS.low;
    const issueType = ISSUE_TYPES[need.issue_type] || ISSUE_TYPES.other;
    const markerSize = getMarkerSize(need.urgency_score);

    // Only create individual circle markers if we're not just showing the heatmap
    if (mapLayerFilter !== "heatmap") {
      const marker = L.circleMarker([need.lat, need.lng], {
        radius: markerSize,
        fillColor: urgency.color,
        fillOpacity: 0.85,
        color: urgency.color,
        weight: 2,
        opacity: 0.4,
      }).addTo(mapInstance);

      // Popup on hover
      const popupContent = `
        <div style="font-family:Inter,sans-serif;max-width:280px;padding:4px;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
            <span style="font-size:18px;">${issueType.icon}</span>
            <strong style="font-size:13px;">${need.zone || "Unknown"}</strong>
            <span style="padding:2px 6px;border-radius:20px;font-size:10px;font-weight:700;
              background:${urgency.color}20;color:${urgency.color};">${urgency.label}</span>
          </div>
          <p style="font-size:12px;color:#666;margin:0 0 4px;line-height:1.3;">${(need.summary || "").slice(0, 120)}</p>
          <div style="font-size:11px;color:#999;">
            Score: ${need.urgency_score}/100 · ~${need.affected_count || "?"} people affected
          </div>
        </div>`;

      marker.bindPopup(popupContent, { closeButton: false, className: "custom-popup" });
      marker.on("mouseover", function() { this.openPopup(); });
      marker.on("mouseout", function() { this.closePopup(); });
      marker.on("click", function() { selectNeed(need.id); });

      mapMarkers.push(marker);
    }

    heatData.push([need.lat, need.lng, (need.urgency_score || 10) / 100]);
  });

  // Create heatmap overlay
  if (heatData.length > 0 && typeof L.heatLayer !== "undefined") {
    heatmapLayer = L.heatLayer(heatData, {
      radius: 35,
      blur: 25,
      maxZoom: 15,
      max: 1.0,
      gradient: {
        0.0: "rgba(14, 159, 110, 0)",
        0.3: "rgba(14, 159, 110, 0.4)",
        0.5: "rgba(227, 160, 8, 0.5)",
        0.7: "rgba(249, 115, 22, 0.6)",
        0.85: "rgba(224, 36, 36, 0.8)",
        1.0: "rgba(224, 36, 36, 1)",
      },
    }).addTo(mapInstance);
  }

  // Auto-fit to show ALL markers (needs + volunteers)
  fitMapToAllMarkers();

  setTimeout(() => mapInstance.invalidateSize(), 100);
}

// ── Update Volunteer Markers ────────────────────────────────
function updateVolunteerMarkers() {
  if (!mapInstance) return;

  // Clear existing volunteer markers
  volunteerMarkers.forEach(m => mapInstance.removeLayer(m));
  volunteerMarkers = [];

  if (!showVolunteers || mapLayerFilter === "heatmap") return;

  const volunteers = AppState.volunteers || [];

  volunteers.forEach(vol => {
    if (!vol.lat || !vol.lng) return;

    const icon = createVolunteerIcon(vol.status || "available");

    const marker = L.marker([vol.lat, vol.lng], { icon: icon }).addTo(mapInstance);

    // Volunteer popup
    const skills = (vol.skills || []).slice(0, 3).join(", ");
    const statusClass = vol.status === "available" ? "available" : "assigned";
    const statusLabel = vol.status === "available" ? "✓ Available" : "⏳ Assigned";

    const popupContent = `
      <div class="volunteer-popup" style="max-width:240px;">
        <div class="vol-name">👤 ${vol.display_name || "Volunteer"}</div>
        <div class="vol-skills">${skills || "General support"}</div>
        <div style="display:flex;align-items:center;gap:6px;margin-top:4px;">
          <span class="vol-status ${statusClass}">${statusLabel}</span>
          <span style="font-size:10px;color:#888;">📍 ${vol.zone || "—"}</span>
        </div>
        ${vol.impact_points ? `<div style="font-size:10px;color:#F59E0B;margin-top:3px;">⭐ ${vol.impact_points} pts</div>` : ""}
      </div>`;

    marker.bindPopup(popupContent, { closeButton: false });
    marker.on("mouseover", function() { this.openPopup(); });
    marker.on("mouseout", function() { this.closePopup(); });

    volunteerMarkers.push(marker);
  });

  // Re-fit bounds to include volunteers
  fitMapToAllMarkers();
}

// ── Toggle Volunteer Visibility ─────────────────────────────
function toggleVolunteerMarkers() {
  showVolunteers = !showVolunteers;
  updateVolunteerMarkers();

  // Update toggle button visual
  const btn = document.getElementById("toggle-volunteers-btn");
  if (btn) {
    btn.classList.toggle("active", showVolunteers);
    btn.title = showVolunteers ? "Hide Volunteers on Map" : "Show Volunteers on Map";
  }
}

// ── Fit Map to All Markers ──────────────────────────────────
function fitMapToAllMarkers() {
  if (!mapInstance) return;

  const allMarkers = [...mapMarkers, ...volunteerMarkers];
  if (allMarkers.length > 0) {
    const group = L.featureGroup(allMarkers);
    mapInstance.fitBounds(group.getBounds().pad(0.15), {
      maxZoom: 14,
      animate: true,
    });
  }
}

// ── Helper Functions ────────────────────────────────────────
function getMarkerSize(urgencyScore) {
  if (urgencyScore >= 86) return 14;
  if (urgencyScore >= 61) return 11;
  if (urgencyScore >= 31) return 8;
  return 6;
}

function getFilteredNeeds() {
  return AppState.needs.filter(need => {
    if (AppState.filters.type !== "all" && need.issue_type !== AppState.filters.type) return false;
    if (AppState.filters.urgency !== "all" && need.urgency_label !== AppState.filters.urgency) return false;
    if (AppState.filters.search && AppState.filters.search.trim() !== "") {
      const searchLower = AppState.filters.search.toLowerCase().trim();
      const searchFields = [
        need.zone, need.summary, need.issue_type,
        ...(need.required_skills || []),
      ].filter(Boolean).join(" ").toLowerCase();
      if (!searchFields.includes(searchLower)) return false;
    }
    return true;
  });
}

function centerMapOnNeed(need) {
  if (!mapInstance || !need.lat || !need.lng) return;
  mapInstance.setView([need.lat, need.lng], 15, { animate: true });
}

// ── Init on Dashboard Show ──────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const observer = new MutationObserver(() => {
    const dashboard = document.getElementById("dashboard");
    if (dashboard && dashboard.style.display !== "none") {
      setTimeout(() => {
        initMap();
        if (mapInstance) mapInstance.invalidateSize();
      }, 200);
    }
  });

  const dashboard = document.getElementById("dashboard");
  if (dashboard) {
    observer.observe(dashboard, { attributes: true, attributeFilter: ["style"] });
  }
});

// ── Fly To Location (auto-redirect after report) ────────────
function flyToLocation(lat, lng, zoom = 13) {
  if (!mapInstance) {
    initMap();
    if (!mapInstance) return;
  }
  mapInstance.flyTo([lat, lng], zoom, { animate: true, duration: 1.5 });

  // Add a pulsing marker to highlight the area
  const pulseMarker = L.circleMarker([lat, lng], {
    radius: 20, fillColor: "#8B5CF6", fillOpacity: 0.4,
    color: "#8B5CF6", weight: 2, opacity: 0.8,
    className: "pulse-marker",
  }).addTo(mapInstance);

  // Animate pulse and remove
  let r = 20;
  const pulse = setInterval(() => {
    r += 2;
    pulseMarker.setRadius(r);
    pulseMarker.setStyle({ fillOpacity: Math.max(0, 0.4 - (r - 20) * 0.02) });
    if (r > 50) { clearInterval(pulse); mapInstance.removeLayer(pulseMarker); }
  }, 50);
}

// ── Draw Routes from Volunteers to Need ─────────────────────
function drawVolunteerRoutes(matches, needLat, needLng) {
  if (!mapInstance) return;
  clearRoutePolylines();

  const colors = ["#3B82F6", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981"];

  matches.forEach((match, i) => {
    if (!match.lat || !match.lng) return;
    const color = colors[i % colors.length];

    // Try to get real route from backend
    fetch(`${FUNCTIONS_BASE}/api/route?from_lat=${match.lat}&from_lng=${match.lng}&to_lat=${needLat}&to_lng=${needLng}`)
      .then(r => r.json())
      .then(route => {
        if (route.polyline && route.polyline.length > 1) {
          const line = L.polyline(route.polyline, {
            color: color, weight: 3, opacity: 0.7,
            dashArray: "8, 6", className: "route-line",
          }).addTo(mapInstance);

          // Add distance label at midpoint
          const mid = route.polyline[Math.floor(route.polyline.length / 2)];
          const label = L.marker(mid, {
            icon: L.divIcon({
              className: "route-label",
              html: `<div style="background:${color};color:#fff;padding:2px 6px;border-radius:10px;font-size:10px;font-weight:600;white-space:nowrap;">${route.distance_km}km · ${route.duration_min}min</div>`,
              iconSize: [80, 20], iconAnchor: [40, 10],
            })
          }).addTo(mapInstance);

          routePolylines.push(line, label);
        } else {
          drawFallbackLine(match, needLat, needLng, color);
        }
      })
      .catch(() => drawFallbackLine(match, needLat, needLng, color));
  });
}

function drawFallbackLine(match, needLat, needLng, color) {
  const line = L.polyline(
    [[match.lat, match.lng], [needLat, needLng]],
    { color: color, weight: 2, opacity: 0.5, dashArray: "6, 8" }
  ).addTo(mapInstance);
  routePolylines.push(line);
}

function clearRoutePolylines() {
  routePolylines.forEach(p => mapInstance.removeLayer(p));
  routePolylines = [];
}
