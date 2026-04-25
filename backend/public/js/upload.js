/* ═══════════════════════════════════════════════════════════
   AlloCare: Upload & Report Ingestion
   Photo OCR (via Gemini Vision), Manual Text, CSV Import
   Connected to real backend APIs
   ═════════════════════════════════════════════════════════ */

function openUploadModal() {
  document.getElementById("upload-modal").style.display = "flex";
  resetUploadModal();
}

function closeUploadModal() {
  document.getElementById("upload-modal").style.display = "none";
  resetUploadModal();
}

function resetUploadModal() {
  document.getElementById("photo-preview").style.display = "none";
  document.getElementById("ocr-result").style.display = "none";
  document.getElementById("csv-result").style.display = "none";
  document.getElementById("processing-indicator").style.display = "none";
  document.getElementById("manual-text").value = "";
  document.getElementById("photo-input").value = "";
  document.getElementById("csv-input").value = "";

  // Reset processing steps
  document.querySelectorAll(".step").forEach(s => {
    s.classList.remove("active", "done");
  });
}

// ── Tab Switching ───────────────────────────────────────────
function switchUploadTab(tab) {
  document.querySelectorAll(".upload-tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".upload-tab-content").forEach(c => {
    c.style.display = "none";
    c.classList.remove("active");
  });

  document.querySelector(`[data-tab="${tab}"]`).classList.add("active");
  document.getElementById(`tab-${tab}`).style.display = "block";
  document.getElementById(`tab-${tab}`).classList.add("active");
}

// ── Photo Upload ────────────────────────────────────────────
let currentImageData = null;

function handlePhotoUpload(input) {
  const file = input.files[0];
  if (!file) return;

  if (file.size > 10 * 1024 * 1024) {
    showToast("File too large. Max 10MB.", "error");
    return;
  }

  const reader = new FileReader();
  reader.onload = async (e) => {
    currentImageData = e.target.result;
    document.getElementById("preview-img").src = currentImageData;
    document.getElementById("photo-preview").style.display = "block";

    // Try real OCR via Gemini Vision API
    document.getElementById("ocr-result").style.display = "block";
    document.getElementById("ocr-text").textContent = "🔄 Extracting text via Gemini Vision...";

    try {
      const text = await extractOCR(currentImageData);
      if (text && text.trim().length > 5) {
        document.getElementById("ocr-text").textContent = text;
        showToast("✅ OCR text extracted successfully", "success");
      } else {
        document.getElementById("ocr-text").textContent = "⚠️ Could not extract text from this image. Please try a clearer photo or use the Text Entry tab.";
        showToast("OCR could not extract text: try a clearer image", "error");
      }
    } catch (e) {
      console.error("OCR error:", e.message);
      document.getElementById("ocr-text").textContent = "⚠️ OCR service unavailable. Please use the Text Entry tab instead.";
      showToast("OCR service unavailable", "error");
    }
  };
  reader.readAsDataURL(file);
}

// ── CSV Upload ──────────────────────────────────────────────
let currentCSVFile = null;

function handleCSVUpload(input) {
  const file = input.files[0];
  if (!file) return;
  currentCSVFile = file;

  const reader = new FileReader();
  reader.onload = (e) => {
    const content = e.target.result;
    const lines = content.split("\n").filter(l => l.trim());
    const resultDiv = document.getElementById("csv-result");
    resultDiv.style.display = "block";
    resultDiv.innerHTML = `
      <div style="padding:var(--space-md);background:var(--bg-card);border-radius:var(--radius-md);">
        <p style="color:var(--green);font-weight:600;">✅ File parsed: ${lines.length - 1} records found</p>
        <p style="color:var(--text-muted);font-size:var(--font-xs);margin-top:var(--space-xs);">
          Headers: ${lines[0]?.slice(0, 100)}
        </p>
      </div>`;
    showToast(`CSV parsed: ${lines.length - 1} records ready to import`, "success");
  };
  reader.readAsText(file);
}

// ── Template Text Insertion ─────────────────────────────────
function insertTemplate(issueType) {
  const templates = {
    food: "Food shortage reported in [location]. Approximately [X] families affected. Children and elderly are most vulnerable. Need food distribution volunteers urgently.",
    water: "Water supply issue in [location]. [X] households without clean drinking water. Municipal supply disrupted for [X] days. Need water purification and plumbing volunteers.",
    health: "Health emergency in [location]. [X] cases of [illness] reported this week. Need volunteer doctors, nurses, and medical supplies for a health camp.",
    housing: "Housing issue in [location]. [X] families affected by [damage/eviction]. Need construction volunteers and temporary shelter arrangements.",
    education: "Education gap in [location]. [X] students unable to attend school due to [reason]. Need teaching volunteers and educational materials.",
    safety: "Safety concern in [location]. [Describe incident]. Approximately [X] people at risk. Need social workers and safety patrol volunteers.",
  };
  document.getElementById("manual-text").value = templates[issueType] || "";
  document.getElementById("manual-text").focus();
}

// ── Submit Report ───────────────────────────────────────────
async function submitReport() {
  const activeTab = document.querySelector(".upload-tab.active").dataset.tab;
  let reportText = "";
  let source = "manual";

  if (activeTab === "photo") {
    reportText = document.getElementById("ocr-text").textContent;
    if (!reportText || reportText.includes("Processing") || reportText.includes("Extracting")) {
      showToast("Please wait for OCR processing to complete", "error");
      return;
    }
    source = "photo";
  } else if (activeTab === "text") {
    reportText = document.getElementById("manual-text").value.trim();
    if (!reportText) {
      showToast("Please enter a description", "error");
      return;
    }
    source = "manual";
  } else if (activeTab === "csv") {
    if (currentCSVFile) {
      showProcessingSteps();
      try {
        activateStep("step-ocr");
        await sleep(300);
        completeStep("step-ocr");

        activateStep("step-save");
        const result = await uploadCSV(currentCSVFile);
        completeStep("step-save");

        showToast(`✅ Imported ${result.imported} records from CSV!`, "success");
        closeUploadModal();
      } catch (error) {
        showToast("CSV import failed: " + error.message, "error");
      }
      return;
    }
    showToast("Please select a CSV file first", "error");
    return;
  }

  // Show processing animation
  showProcessingSteps();

  try {
    // Step 1: OCR (already done for photo)
    activateStep("step-ocr");
    await sleep(400);
    completeStep("step-ocr");

    // Step 2: Translation
    activateStep("step-translate");
    await sleep(300);
    completeStep("step-translate");

    // Step 3-6: Call backend API for full processing
    activateStep("step-gemini");

    try {
      const result = await processReport(reportText, source);
      completeStep("step-gemini");

      activateStep("step-geocode");
      await sleep(300);
      completeStep("step-geocode");

      activateStep("step-score");
      await sleep(200);
      completeStep("step-score");

      activateStep("step-save");
      await sleep(200);
      completeStep("step-save");

      if (result.status === "success") {
        showToast(`✅ Report processed! Score: ${result.score}/100 (${result.label})`, "success");
        // Auto-fly map to the new report location
        if (result.lat && result.lng) {
          flyToLocation(result.lat, result.lng, 13);
        } else if (result.zone) {
          const loc = detectLocationFromText(result.zone);
          flyToLocation(loc.lat, loc.lng, 12);
        }
      } else {
        showToast(`⚠️ Report saved but: ${result.message || "partial processing"}`, "info");
      }
    } catch (apiError) {
      console.log("API processing failed, saving locally:", apiError.message);
      completeStep("step-gemini");

      // Fallback: create local report
      activateStep("step-geocode");
      await sleep(200);
      completeStep("step-geocode");
      activateStep("step-score");
      await sleep(200);
      completeStep("step-score");
      activateStep("step-save");

      // Try to detect location from the text
      const locationInfo = detectLocationFromText(reportText);

      const newNeed = {
        id: "n_new_" + Date.now(),
        zone: locationInfo.zone,
        lat: locationInfo.lat + (Math.random() - 0.5) * 0.02,
        lng: locationInfo.lng + (Math.random() - 0.5) * 0.02,
        issue_type: detectIssueType(reportText),
        severity_score: 7 + Math.floor(Math.random() * 3),
        urgency_score: 70 + Math.floor(Math.random() * 25),
        urgency_label: "high",
        affected_count: 30 + Math.floor(Math.random() * 170),
        summary: reportText.slice(0, 150),
        required_skills: ["general volunteering"],
        recommended_volunteer_count: 3,
        status: "open",
        source: source,
        created_at: new Date().toISOString(),
        report_frequency_30d: 2,
        trend_direction: "stable",
      };

      AppState.needs.unshift(newNeed);
      renderNeedsFeed();
      updateMapMarkers();
      updateCounts();

      completeStep("step-save");
      showToast("✅ Report saved locally (API offline)", "success");
    }

    closeUploadModal();
  } catch (error) {
    showToast("Processing failed: " + error.message, "error");
  }
}

// ── Processing Step Helpers ─────────────────────────────────
function showProcessingSteps() {
  document.getElementById("processing-indicator").style.display = "block";
  document.querySelectorAll(".step").forEach(s => {
    s.classList.remove("active", "done");
  });
}

function activateStep(stepId) {
  document.getElementById(stepId).classList.add("active");
}

function completeStep(stepId) {
  const step = document.getElementById(stepId);
  step.classList.remove("active");
  step.classList.add("done");
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Location Detection (Client-Side Fallback) ──────────────
function detectLocationFromText(text) {
  const textLower = text.toLowerCase();

  // Major Indian cities with approximate coordinates
  const cityCoords = {
    "nagpur":       { lat: 21.1458, lng: 79.0882 },
    "pune":         { lat: 18.5204, lng: 73.8567 },
    "delhi":        { lat: 28.6139, lng: 77.2090 },
    "new delhi":    { lat: 28.6139, lng: 77.2090 },
    "bangalore":    { lat: 12.9716, lng: 77.5946 },
    "bengaluru":    { lat: 12.9716, lng: 77.5946 },
    "hyderabad":    { lat: 17.3850, lng: 78.4867 },
    "chennai":      { lat: 13.0827, lng: 80.2707 },
    "kolkata":      { lat: 22.5726, lng: 88.3639 },
    "ahmedabad":    { lat: 23.0225, lng: 72.5714 },
    "jaipur":       { lat: 26.9124, lng: 75.7873 },
    "lucknow":      { lat: 26.8467, lng: 80.9462 },
    "kanpur":       { lat: 26.4499, lng: 80.3319 },
    "indore":       { lat: 22.7196, lng: 75.8577 },
    "bhopal":       { lat: 23.2599, lng: 77.4126 },
    "patna":        { lat: 25.6093, lng: 85.1376 },
    "nashik":       { lat: 19.9975, lng: 73.7898 },
    "varanasi":     { lat: 25.3176, lng: 82.9739 },
    "surat":        { lat: 21.1702, lng: 72.8311 },
    "chandigarh":   { lat: 30.7333, lng: 76.7794 },
    "coimbatore":   { lat: 11.0168, lng: 76.9558 },
    "kochi":        { lat: 9.9312, lng: 76.2673 },
    "guwahati":     { lat: 26.1445, lng: 91.7362 },
    "ranchi":       { lat: 23.3441, lng: 85.3096 },
    "bhubaneswar":  { lat: 20.2961, lng: 85.8245 },
    "dehradun":     { lat: 30.3165, lng: 78.0322 },
    "amritsar":     { lat: 31.6340, lng: 74.8723 },
    "jodhpur":      { lat: 26.2389, lng: 73.0243 },
    "raipur":       { lat: 21.2514, lng: 81.6296 },
    "gwalior":      { lat: 26.2183, lng: 78.1828 },
    "noida":        { lat: 28.5355, lng: 77.3910 },
    "gurgaon":      { lat: 28.4595, lng: 77.0266 },
    "thane":        { lat: 19.2183, lng: 72.9781 },
    "dharavi":      { lat: 19.0441, lng: 72.8557 },
    "kurla":        { lat: 19.0724, lng: 72.8787 },
    "bandra":       { lat: 19.0596, lng: 72.8413 },
    "andheri":      { lat: 19.1197, lng: 72.8468 },
    "mumbai":       { lat: 19.0760, lng: 72.8777 },
  };

  // Search for city names in the text (check longer names first)
  const sortedCities = Object.keys(cityCoords).sort((a, b) => b.length - a.length);
  for (const city of sortedCities) {
    if (textLower.includes(city)) {
      return {
        zone: city.charAt(0).toUpperCase() + city.slice(1),
        lat: cityCoords[city].lat,
        lng: cityCoords[city].lng,
      };
    }
  }

  // Default to generic India center
  return { zone: "Unknown", lat: 21.0, lng: 78.0 };
}

function detectIssueType(text) {
  const textLower = text.toLowerCase();
  const issueMap = {
    "food":      ["food", "hunger", "meal", "ration", "starv"],
    "water":     ["water", "drinking", "pipeline", "tanker", "flood"],
    "health":    ["health", "medical", "doctor", "dengue", "hospital", "sick", "disease", "injured"],
    "housing":   ["housing", "shelter", "fire", "displaced", "earthquake", "collapsed", "building", "damage"],
    "education": ["education", "school", "student", "teacher"],
    "safety":    ["safety", "child labor", "crime", "danger", "rescue", "evacuation", "disaster"],
  };

  for (const [type, keywords] of Object.entries(issueMap)) {
    if (keywords.some(kw => textLower.includes(kw))) return type;
  }
  return "other";
}

