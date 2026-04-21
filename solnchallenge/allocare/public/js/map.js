/* ═══════════════════════════════════════════════════════════
   AlloCare — Map (Leaflet.js + OpenStreetMap — FREE, no API key)
   Replaces Google Maps JavaScript API + deck.gl
   ═════════════════════════════════════════════════════════ */

let mapInstance = null;
let mapMarkers = [];
let heatmapLayer = null;

function initMap() {
  if (mapInstance) return; // Already initialized

  const mumbaiCenter = [19.0760, 72.8777];

  mapInstance = L.map("map", {
    center: mumbaiCenter,
    zoom: 12,
    zoomControl: true,
    attributionControl: false,
  });

  // CartoDB Dark Matter tiles (free, matches dark theme)
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    subdomains: "abcd",
  }).addTo(mapInstance);

  // Attribution (required by CartoDB)
  L.control.attribution({
    position: "bottomright",
    prefix: false,
  }).addAttribution('© <a href="https://www.openstreetmap.org/copyright">OSM</a> © <a href="https://carto.com/">CARTO</a>').addTo(mapInstance);

  // If data is already loaded, render markers
  if (AppState.needs.length > 0) {
    updateMapMarkers();
  }
}

function updateMapMarkers() {
  if (!mapInstance) {
    // Try to init map if container exists
    const mapEl = document.getElementById("map");
    if (mapEl && mapEl.offsetHeight > 0) {
      initMap();
    }
    if (!mapInstance) return;
  }

  // Clear existing markers
  mapMarkers.forEach(m => mapInstance.removeLayer(m));
  mapMarkers = [];

  // Clear existing heatmap
  if (heatmapLayer) {
    mapInstance.removeLayer(heatmapLayer);
    heatmapLayer = null;
  }

  const filteredNeeds = getFilteredNeeds();
  const heatData = [];

  filteredNeeds.forEach(need => {
    if (!need.lat || !need.lng) return;

    const urgency = URGENCY_LEVELS[need.urgency_label] || URGENCY_LEVELS.low;
    const issueType = ISSUE_TYPES[need.issue_type] || ISSUE_TYPES.other;
    const markerSize = getMarkerSize(need.urgency_score);

    // Create circle marker
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

    marker.bindPopup(popupContent, {
      closeButton: false,
      className: "custom-popup",
    });

    marker.on("mouseover", function() { this.openPopup(); });
    marker.on("mouseout", function() { this.closePopup(); });

    // Click to select need
    marker.on("click", function() {
      selectNeed(need.id);
    });

    mapMarkers.push(marker);

    // Add to heatmap data [lat, lng, intensity]
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

  // Invalidate size to fix rendering
  setTimeout(() => mapInstance.invalidateSize(), 100);
}

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
    if (AppState.filters.search) {
      const searchLower = AppState.filters.search.toLowerCase();
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

// Initialize map when the dashboard becomes visible
document.addEventListener("DOMContentLoaded", () => {
  // Use MutationObserver to detect when dashboard is shown
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
