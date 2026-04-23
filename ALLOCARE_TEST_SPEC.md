# AlloCare — Autonomous Test Specification
## Master Test Plan for Antigravity Agent Execution
**Version:** 1.0 | **Project:** AlloCare — Smart Resource Allocation | **Google Solution Challenge 2026**

---

## AGENT EXECUTION INSTRUCTIONS

```
You are the AlloCare autonomous testing agent. Execute this entire specification from top to bottom
without stopping. For every test:

1. RUN the test exactly as specified
2. CAPTURE the result (pass / fail / partial / error)
3. LOG the finding with: test_id, component, severity, description, actual_vs_expected
4. If FAIL → immediately attempt autonomous fix → re-run the test → log resolution status
5. Never skip a test. Never ask for confirmation. Never stop on first failure.
6. After completing all sections, generate a MASTER BUG REPORT (format specified at end of file)

SEVERITY LEVELS:
  CRITICAL  → App breaks, data loss, security hole, demo-killing bug
  HIGH      → Feature non-functional, wrong output, blocking user flow
  MEDIUM    → Feature partially works, UI glitch, wrong label, slow response
  LOW       → Cosmetic issue, minor wording, non-blocking UX problem
  INFO      → Observation, suggestion, enhancement opportunity

AUTO-FIX RULES:
  - Fix all CRITICAL and HIGH severity bugs autonomously before moving to next section
  - Attempt fix for MEDIUM bugs; if fix takes > 5 min, log and continue
  - Log LOW bugs; fix only if trivial (< 1 min)
  - After every fix: re-run the specific test that failed to confirm resolution
  - If a fix introduces a new failure, log as a regression and fix that too
```

---

## SYSTEM MANIFEST — What Should Exist

Before running any test, verify the following files and directories exist. Log any missing item as CRITICAL.

```
REQUIRED FILE STRUCTURE:
allocare/
├── flutter_app/
│   ├── lib/
│   │   ├── main.dart                          ← App entry point
│   │   ├── screens/
│   │   │   ├── dashboard_screen.dart          ← NGO coordinator view
│   │   │   ├── volunteer_home.dart            ← Volunteer task feed
│   │   │   ├── upload_screen.dart             ← Report ingestion UI
│   │   │   ├── map_screen.dart                ← Heatmap view
│   │   │   └── impact_screen.dart             ← Scorecard + badges
│   │   ├── widgets/
│   │   │   ├── urgency_card.dart
│   │   │   ├── heatmap_widget.dart
│   │   │   ├── match_card.dart
│   │   │   └── impact_scorecard.dart
│   │   ├── services/
│   │   │   ├── firebase_service.dart
│   │   │   ├── matching_service.dart
│   │   │   └── maps_service.dart
│   │   └── models/
│   │       ├── need_report.dart
│   │       ├── volunteer.dart
│   │       └── assignment.dart
│   └── pubspec.yaml
├── functions/
│   ├── main.py                                ← Cloud Functions entry
│   ├── urgency_scorer.py                      ← Urgency algorithm
│   ├── matching_engine.py                     ← Volunteer matching
│   ├── gemini_client.py                       ← Gemini API wrapper
│   └── requirements.txt
├── firebase.json
├── firestore.rules
├── firestore.indexes.json
└── README.md

MISSING FILE ACTION: Create stub file with correct structure, log as HIGH, flag for implementation.
```

---

## SECTION 1 — ENVIRONMENT & CONFIGURATION TESTS

### 1.1 Firebase Project Configuration

```
TEST_ID: ENV-001
COMPONENT: Firebase / Environment
DESCRIPTION: Verify Firebase project is correctly initialized and all services are enabled
ACTION:
  1. Read firebase.json — confirm projectId is set and not placeholder
  2. Check .firebaserc — confirm default project alias exists
  3. Verify firebase-admin SDK is initialized in functions/main.py
  4. Confirm Firestore, Auth, Storage, Functions, Hosting are all enabled
  5. Check that environment variables (GEMINI_API_KEY, MAPS_API_KEY) are set in
     Firebase Functions config — NOT hardcoded in source files
EXPECTED: All services initialized, no API keys in source code
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Initialize missing services, move hardcoded keys to environment config
```

```
TEST_ID: ENV-002
COMPONENT: API Keys Security Scan
DESCRIPTION: Scan entire codebase for hardcoded API keys or secrets
ACTION:
  1. grep -r "AIza" . --include="*.dart" --include="*.py" --include="*.js"
  2. grep -r "sk-" . --include="*.dart" --include="*.py"
  3. grep -r "firebase_api_key" . --include="*.dart"
  4. Check pubspec.yaml for any embedded credentials
  5. Check functions/requirements.txt for any credentials
EXPECTED: Zero hardcoded secrets found anywhere in source
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Move all found keys to environment variables / Firebase Functions config
```

```
TEST_ID: ENV-003
COMPONENT: Dependencies
DESCRIPTION: Verify all required dependencies are declared and installable
ACTION:
  FLUTTER — verify pubspec.yaml contains:
  - firebase_core, firebase_auth, cloud_firestore, firebase_storage
  - google_maps_flutter OR flutter_map
  - http, provider or riverpod
  - image_picker, geolocator, firebase_messaging
  - fl_chart or syncfusion_flutter_charts
  Run: flutter pub get (must complete with zero errors)
  Run: flutter analyze (capture all warnings and errors)

  PYTHON FUNCTIONS — verify requirements.txt contains:
  - firebase-admin, google-cloud-firestore
  - google-cloud-vision, google-cloud-translate
  - google-generativeai
  - pandas, numpy, googlemaps
  - functions-framework
  Run: pip install -r requirements.txt (check for conflicts)
EXPECTED: All deps install cleanly, flutter analyze shows 0 errors
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Add missing packages, resolve version conflicts
```

```
TEST_ID: ENV-004
COMPONENT: Firestore Security Rules
DESCRIPTION: Validate security rules — not open to public
ACTION:
  1. Read firestore.rules
  2. Verify rules DENY unauthenticated reads/writes on all collections
  3. Verify coordinators can only read/write their own org_id data
  4. Verify volunteers can only write to assignments/{their_own_uid}
  5. Verify no collection has: allow read, write: if true
  6. Simulate:
     - Unauthenticated user → read need_reports → MUST DENY
     - Coordinator user → read own org need_reports → MUST ALLOW
     - Volunteer → write another volunteer's assignment → MUST DENY
EXPECTED: All three simulations return correct allow/deny
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Write correct security rules for all collections
```

```
TEST_ID: ENV-005
COMPONENT: Firestore Indexes
DESCRIPTION: Verify all required composite indexes are defined
ACTION:
  1. Read firestore.indexes.json
  2. Verify these indexes exist:
     - need_reports: (org_id ASC, urgency_score DESC)
     - need_reports: (status ASC, issue_type ASC, created_at DESC)
     - volunteers: (status ASC, zone ASC)
EXPECTED: All 3 composite indexes defined
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add missing index definitions to firestore.indexes.json
```

---

## SECTION 2 — AUTHENTICATION TESTS

```
TEST_ID: AUTH-001
COMPONENT: Firebase Auth / Google Sign-In
DESCRIPTION: Verify Google Sign-In is implemented and functional
ACTION:
  1. Check main.dart — confirm Firebase.initializeApp() called before runApp()
  2. Verify GoogleAuthProvider is used
  3. After sign-in, verify user UID is stored and accessible
  4. Verify sign-in cancellation handled gracefully
  5. Verify sign-in network error shows appropriate UI message
EXPECTED: Sign-in flow complete, UID accessible, errors handled
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Implement complete Google Sign-In flow with error handling
```

```
TEST_ID: AUTH-002
COMPONENT: Role-Based Access / Custom Claims
DESCRIPTION: Verify user roles are correctly assigned and enforced
ACTION:
  1. Locate where custom claims are set
  2. Verify coordinator role: {role: "coordinator", org_id: "<id>"}
  3. Verify volunteer role: {role: "volunteer"}
  4. Simulate: volunteer user accessing coordinator dashboard → must redirect/deny
  5. Verify dashboard_screen.dart checks role before rendering
EXPECTED: Roles enforced at both UI and Firestore rule level
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Implement role check middleware in Flutter route guards
```

```
TEST_ID: AUTH-003
COMPONENT: Session Persistence
DESCRIPTION: Verify user stays logged in after app restart
ACTION:
  1. Verify Firebase Auth persistence set to LOCAL
  2. Simulate app restart — verify no re-login required
  3. Verify authStateChanges() stream used in main.dart
  4. Verify loading state shown while auth resolves
EXPECTED: Session persists, no unnecessary re-login
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Set auth persistence to local, add authStateChanges listener
```

```
TEST_ID: AUTH-004
COMPONENT: Sign-Out
DESCRIPTION: Verify sign-out clears all state and redirects to login
ACTION:
  1. Trigger sign-out
  2. Verify Firebase Auth signOut() called
  3. Verify local state cleared
  4. Verify navigation redirects to login
  5. Verify back button does NOT return to authenticated screens
EXPECTED: Complete state clear, navigation reset
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Implement complete sign-out with state disposal and route clearing
```

---

## SECTION 3 — F1: MULTI-SOURCE DATA INGESTION TESTS

```
TEST_ID: F1-OCR-001
COMPONENT: Cloud Vision OCR / Photo Upload
DESCRIPTION: Test complete photo upload → OCR → Gemini extraction pipeline
ACTION:
  1. Upload TEST_IMAGE_1: Clear printed English survey
     Content: "Zone: Dharavi | Issue: Water shortage | Affected: 47 families | Severity: High"
  2. Verify image uploads to Firebase Storage at /reports/{org_id}/{timestamp}/{filename}
  3. Verify Cloud Vision API called with uploaded image URL
  4. Verify extracted text returned within 5 seconds
  5. Verify text passed to Gemini for structuring
  6. Verify Firestore document contains: zone, issue_type, severity_score, summary
  7. Verify heatmap updates within 2 seconds of Firestore write
EXPECTED: Full pipeline completes in < 15s, Firestore doc has all required fields
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Debug each pipeline stage, fix broken API calls, ensure async/await chains
```

```
TEST_ID: F1-OCR-002
COMPONENT: Cloud Vision OCR — Edge Cases
DESCRIPTION: Test OCR with problematic images
ACTION:
  TEST CASE A — Blurry image:
    Upload low-resolution blurry image
    Verify confidence < 0.6 → UI shows "Image unclear, please retake"
    Verify no phantom Firestore document created

  TEST CASE B — Handwritten survey:
    Upload handwritten text on lined paper
    Verify DOCUMENT_TEXT_DETECTION used (not TEXT_DETECTION)
    Verify partial extraction surfaced for manual correction

  TEST CASE C — Empty/blank image:
    Upload blank white image
    Verify graceful error: "No text detected in image"

  TEST CASE D — Non-image file disguised as .jpg:
    Upload .pdf renamed as survey.jpg
    Verify file type validation rejects before upload
EXPECTED: Each edge case handled with correct UI message, no silent failures
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add confidence threshold check, file type validation, proper error states
```

```
TEST_ID: F1-OCR-003
COMPONENT: Hindi / Regional Language OCR
DESCRIPTION: Test multilingual OCR and translation pipeline
ACTION:
  1. Upload TEST_IMAGE_HINDI: Printed Hindi survey
     Content: "क्षेत्र: गोवंडी | समस्या: खाद्य असुरक्षा | प्रभावित: 23 परिवार"
  2. Verify Vision API language_hints includes "hi"
  3. Verify Google Translate API called when language_detected != "en"
  4. Verify translated English text passed to Gemini
  5. Verify Firestore document has language_detected: "hi"
  6. Verify translated summary shown in coordinator dashboard
EXPECTED: Hindi report correctly processed, translated, scored, stored
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add language detection check, implement Translate API in pipeline
```

```
TEST_ID: F1-CSV-001
COMPONENT: CSV Import Endpoint
DESCRIPTION: Test bulk CSV import via processCSVUpload Cloud Function
ACTION:
  1. POST /processCSVUpload with TEST_CSV_50_RECORDS.csv
  2. Verify HTTP 200 response within 10 seconds
  3. Verify response: {imported: 50, errors: []}
  4. Verify all 50 documents in Firestore need_reports collection
  5. Verify correct field types (severity is integer, not string)
  6. Verify Firestore batch write limit respected (max 500 docs/batch)
  7. Verify each new document triggers onReportCreated
EXPECTED: 50 records imported, all scored, response within 10s
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Fix pandas column normalization, add type coercion, implement batch writes
```

```
TEST_ID: F1-CSV-002
COMPONENT: CSV Import — Error Handling
DESCRIPTION: Test CSV import with malformed data
ACTION:
  TEST CASE A: CSV missing "zone" column → 400 error with clear message
  TEST CASE B: severity = "HIGH" (string not integer) → auto-convert or flag per row
  TEST CASE C: Empty CSV (headers only) → {imported: 0, errors: []}
  TEST CASE D: Oversized CSV > 5MB → graceful size limit error
  TEST CASE E: .xlsx format → verify XLSX parser works
EXPECTED: Each error returns meaningful error object, no crashes
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add column validation, type coercion, file size check, XLSX parser
```

```
TEST_ID: F1-MANUAL-001
COMPONENT: Manual Report Form
DESCRIPTION: Test manual text entry form submission
ACTION:
  1. Open upload_screen → Manual Entry mode
  2. Verify form fields: report_text, zone, optional num_affected
  3. Submit valid data, verify Firestore write with source: "manual"
  4. Verify onReportCreated triggers
  5. Submit empty form → verify required field errors
  6. Submit report_text < 10 chars → verify minimum length validation
  7. Submit XSS payload → verify sanitization
  8. Submit SQL injection attempt → verify sanitization
EXPECTED: Valid submission processed, invalid submissions rejected with clear errors
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add form validation, input sanitization, success/error state handling
```

```
TEST_ID: F1-WHATSAPP-001
COMPONENT: Twilio Webhook / whatsappWebhook Cloud Function
DESCRIPTION: Test WhatsApp message intake pipeline
ACTION:
  1. POST to /whatsappWebhook with Twilio webhook body:
     {From: "whatsapp:+919876543210", Body: "Report: food shortage in Dharavi, 40 families", MessageSid: "SM_TEST"}
  2. Verify function parses sender number
  3. Verify org lookup by sender number
  4. Verify Firestore document created with source: "whatsapp"
  5. Verify HTTP 200 TwiML acknowledgment response
  6. Unknown sender number → graceful response, no crash
  7. Empty message body → error handling
  8. Non-UTF-8 characters → Unicode handling
EXPECTED: Valid webhook creates Firestore doc, errors handled gracefully
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Implement sender lookup, Unicode decode, TwiML response
```

---

## SECTION 4 — F2: GEMINI URGENCY SCORING ENGINE TESTS

```
TEST_ID: F2-GEMINI-001
COMPONENT: Gemini API / Urgency Extraction
DESCRIPTION: Verify Gemini returns correctly structured JSON
ACTION:
  Call extract_urgency() with:
  "Water supply disruption in Dharavi Ward 8. 47 families without water for 3 days.
   Children falling sick. Need medical help also."

  Verify response:
  1. Valid JSON (json.loads() succeeds)
  2. All required fields present: issue_type, location_text, severity_score (1-10),
     affected_count, summary, required_skills[], recommended_volunteer_count, language_detected
  3. severity_score >= 7 for this high-severity input
  4. issue_type is "water" or "health"
EXPECTED: Valid JSON with all fields, appropriate severity
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Fix Gemini prompt, add JSON parsing error handling, add field validation
```

```
TEST_ID: F2-GEMINI-002
COMPONENT: Gemini API — Response Robustness
DESCRIPTION: Test Gemini response handling for edge cases
ACTION:
  A: Gemini returns markdown-wrapped JSON (```json...```) → verify strip before parse
  B: Truncated JSON (missing closing brace) → verify JSONDecodeError caught, fallback used
  C: Gemini 429 rate limit → verify exponential backoff (3 attempts), then pending state
  D: Wrong issue_type not in enum → verify fallback to "other", log for drift tracking
EXPECTED: All edge cases handled, no crashes, graceful degradation
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add JSON sanitization, retry logic, enum validation, fallback values
```

```
TEST_ID: F2-URGENCY-001
COMPONENT: Urgency Scoring Formula
DESCRIPTION: Verify algorithm produces mathematically correct results
ACTION:
  Test calculate_urgency_score() with known inputs:

  TEST A: severity=9, frequency=5, days=1
    Formula: (9 × log(6)) / 1 = 9 × 1.792 = 16.13 → normalized = 100
    Expected: score=100, label="CRITICAL"

  TEST B: severity=3, frequency=1, days=30
    Formula: (3 × log(2)) / 30 ≈ 0.069 → normalized ≈ 1
    Expected: score 0-30, label="LOW"

  TEST C: severity=5, frequency=3, days=7
    Expected: score 31-60, label="MEDIUM"

  BOUNDARY CONDITIONS:
  - severity=0 → no division error, minimum score
  - severity=11 → capped at 10 (input validation)
  - days_since_first=0 → max(1, days) prevents division by zero
  - frequency=0 → log(1)=0 → urgency=0
EXPECTED: All test cases return correct score and label, no math errors
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Fix formula implementation, add input bounds validation
```

```
TEST_ID: F2-URGENCY-002
COMPONENT: Urgency Thresholds and Labels
DESCRIPTION: Verify all four severity bands are correct
ACTION:
  Test these scores and verify label + color:
  score=15 → label="LOW",      color="#0E9F6E"
  score=45 → label="MEDIUM",   color="#E3A008"
  score=70 → label="HIGH",     color="#F97316"
  score=90 → label="CRITICAL", color="#E02424"
  score=30 → label="LOW"       (boundary — inclusive)
  score=31 → label="MEDIUM"    (boundary)
  score=86 → label="CRITICAL"  (boundary)
  Verify colors match in Flutter urgency_card.dart
EXPECTED: Correct label and hex color for all inputs including boundaries
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Fix threshold conditions, update color constants in Python and Dart
```

```
TEST_ID: F2-REALTIME-001
COMPONENT: onReportCreated Cloud Function
DESCRIPTION: Verify Firestore trigger fires correctly and completes pipeline
ACTION:
  1. Write test need_report document directly to Firestore
  2. Monitor Cloud Function logs for onReportCreated trigger
  3. Verify function fires within 3 seconds of document write
  4. Verify pipeline: OCR→Translate→Gemini→Score→Geocode→FCM
  5. Verify same Firestore document updated with all extracted fields
  6. Verify processed_at timestamp set after completion
  7. Verify function does NOT fire again on update (idempotency)
  8. Verify total execution time < 30 seconds
EXPECTED: Function triggers, pipeline completes, no infinite loop
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Add idempotency check (if processed_at exists → skip), fix pipeline chain
```

```
TEST_ID: F2-FLAG-001
COMPONENT: flagUrgencyScore / Human-in-the-Loop
DESCRIPTION: Verify coordinators can override AI urgency scores
ACTION:
  1. POST /flagUrgencyScore: {need_id: "test_001", correct_score: 85, reason: "Cholera risk"}
  2. Verify HTTP 200 response
  3. Verify urgency_corrections collection receives document
  4. Verify need_report urgency_score updated to 85
  5. Verify flagged_by and flag_reason set on need_report
  6. Verify dashboard reflects updated score immediately
  7. Invalid need_id → 404 error
  8. Score > 100 → validation error
EXPECTED: Override works, correction logged, dashboard updated, errors handled
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add validation, implement Firestore transaction for atomic update
```

---

## SECTION 5 — F3: GOOGLE MAPS URGENCY HEATMAP TESTS

```
TEST_ID: F3-MAP-001
COMPONENT: Google Maps Initialization
DESCRIPTION: Verify Google Maps loads correctly in Flutter Web
ACTION:
  1. Verify Maps JavaScript API loaded (check script tag in index.html)
  2. Verify API key loaded from environment (NOT hardcoded)
  3. Verify map initializes at Mumbai (lat: 19.0760, lng: 72.8777)
  4. Verify map renders within 2 seconds
  5. Check browser console for "Google Maps JavaScript API error" → FAIL if present
  6. Verify zoom controls functional
  7. Verify responsive resize behavior
  8. Verify deck.gl HeatmapLayer used (NOT deprecated native heatmap)
EXPECTED: Map renders at Mumbai, no API errors, deck.gl confirmed
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Fix API key injection, replace deprecated heatmap with deck.gl HeatmapLayer
```

```
TEST_ID: F3-MAP-002
COMPONENT: Heatmap Data Rendering
DESCRIPTION: Verify urgency points render as correctly colored heatmap
ACTION:
  Pre-seed Firestore with 10 test need_reports:
  - 3 records: urgency_score=90 — Dharavi coordinates (must appear RED)
  - 4 records: urgency_score=50 — Kurla coordinates (must appear AMBER)
  - 3 records: urgency_score=15 — Bandra coordinates (must appear GREEN)

  1. Load heatmap — verify all 10 points plotted
  2. Verify Dharavi cluster appears RED
  3. Verify Kurla cluster appears AMBER
  4. Verify Bandra cluster appears GREEN
  5. Verify getWeight: d => d.urgency_score implemented (not equal weighting)
  6. Verify colorRange: green → amber → orange → red
EXPECTED: Correct color intensity mapping for all urgency levels
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Fix colorRange array, fix getWeight function, fix Firestore listener
```

```
TEST_ID: F3-MAP-003
COMPONENT: Real-Time Heatmap Updates
DESCRIPTION: Verify heatmap updates live when new report added
ACTION:
  1. Open heatmap view in browser
  2. Write new CRITICAL need_report to Firestore (urgency_score=95, Dharavi coords)
  3. Measure time from write to heatmap visual update
  4. Verify new red cluster appears at Dharavi coordinates
  5. Verify update occurs within 2 seconds (onSnapshot listener)
  6. Verify old points NOT removed or duplicated
  7. Rapid writes (5 docs in 2 seconds) → verify no render crash
EXPECTED: Real-time update < 2s, no duplicates, no crash
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Add Firestore onSnapshot listener, implement proper state management
```

```
TEST_ID: F3-MAP-004
COMPONENT: Heatmap Click Interaction
DESCRIPTION: Verify clicking cluster shows need detail cards
ACTION:
  1. Click HIGH urgency cluster
  2. Verify popup shows: urgency badge, issue_type icon, summary, affected_count,
     zone name, coordinator_explanation
  3. Verify "Assign Volunteers" button present
  4. Click "Assign Volunteers" → opens matching results
  5. Click outside popup → closes cleanly
  6. Click area with no needs → nothing breaks
EXPECTED: Click shows detail popup, buttons functional, no crash on empty click
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add onTap handler to HeatmapLayer, implement detail panel widget
```

```
TEST_ID: F3-MAP-005
COMPONENT: Choropleth District View
DESCRIPTION: Verify district-level view toggle works
ACTION:
  1. Toggle to choropleth mode
  2. Verify district boundaries appear
  3. Verify districts colored by average urgency within them
  4. Verify clicking district shows list of all needs in that district
  5. Toggle back to heatmap → smooth transition
EXPECTED: Both view modes work, district aggregation correct
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Implement choropleth layer with GeoJSON district boundaries
```

---

## SECTION 6 — F4: VOLUNTEER MATCHING ALGORITHM TESTS

```
TEST_ID: F4-MATCH-001
COMPONENT: Volunteer Matching Algorithm — Core Logic
DESCRIPTION: Verify match_volunteers() returns correct top-3
ACTION:
  Setup test need: issue_type="health", required_skills=["medical_first_aid","translation_hindi"]
  Location: Dharavi (19.0522, 72.8573)

  Test volunteer pool:
  V1: skills=[medical_first_aid,translation_hindi], Dharavi, available=true  ← BEST MATCH
  V2: skills=[medical_first_aid], Kurla 3km, available=true
  V3: skills=[translation_hindi], Dharavi, available=true
  V4: skills=[food_distribution], Dharavi, available=true                    ← NO skill match
  V5: skills=[medical_first_aid,translation_hindi], Delhi 1400km             ← too far
  V6: skills=[medical_first_aid], Dharavi, available=false                   ← avail_score=0.3
  V7: skills=[medical_first_aid,translation_hindi], max_distance=1km, Kurla  ← hard cutoff
  V8: skills=[medical_first_aid], Andheri 8km, available=true
  V9: skills=[medical_first_aid,translation_hindi], Dadar 5km, available=true
  V10: skills=[child_care], Dharavi, available=true                          ← NO skill match

  1. Call getMatchedVolunteers(need_id)
  2. Verify exactly 3 returned
  3. Verify V1 ranked #1 (perfect skill + closest)
  4. Verify V4, V10 NOT in results (zero skill overlap)
  5. Verify V7 NOT in results (hard distance cutoff)
  6. Verify V1 match_explanation contains both skills + distance info
  7. Verify results sorted by match_score descending
EXPECTED: V1=#1, V4/V7/V10 excluded, explanations accurate
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Debug matching algorithm, fix skill intersection, fix distance hard cutoff
```

```
TEST_ID: F4-MATCH-002
COMPONENT: Distance Matrix API Integration
DESCRIPTION: Verify Distance Matrix is called correctly and efficiently
ACTION:
  1. Verify ALL volunteer origins grouped in ONE API call (not per-volunteer)
  2. Verify mode is "driving"
  3. Verify proximity_score = 1 / (1 + distance_km)
  4. Volunteer at same coordinates → distance ≈ 0, proximity ≈ 1.0
  5. Volunteer 10km away → proximity = 1/11 ≈ 0.09
  6. API 429 error → falls back to Haversine formula
EXPECTED: Batch API call, correct proximity scores, Haversine fallback
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Implement batch Distance Matrix call, add Haversine fallback
```

```
TEST_ID: F4-MATCH-003
COMPONENT: Matching — Edge Cases
DESCRIPTION: Test algorithm with unusual inputs
ACTION:
  A: All volunteers offline → {matches:[], message:"No volunteers available"}, no crash
  B: Need with empty required_skills → all volunteers qualify, rank by proximity
  C: Only 1 volunteer available → return array with 1 match (not crash)
  D: Volunteer with skills:[] → skill_score=0, appears last or excluded
EXPECTED: All edge cases handled gracefully
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add guards for empty arrays, handle 0/1-match cases
```

---

## SECTION 7 — F5: NGO COORDINATOR DASHBOARD TESTS

```
TEST_ID: F5-DASH-001
COMPONENT: Dashboard Layout and Components
DESCRIPTION: Verify all required dashboard panels render correctly
ACTION:
  Log in as coordinator. Verify:
  1. Left panel: org logo, nav items (Dashboard/Reports/Volunteers/Analytics/Settings)
  2. Center panel: Google Maps heatmap (60% viewport height), Upload Report CTA,
     tabbed panels (Active Needs / Resolved / Trends)
  3. Right panel: Volunteer Pool header, volunteer cards with name/skill chips/status dot
     (green=available, yellow=assigned, gray=offline)
  4. Top bar: notifications bell, user avatar, sign-out option
  5. Zero null pointer exceptions in widget tree
EXPECTED: All panels render, no missing widgets, no null errors
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Implement missing panels, fix null safety in widget tree
```

```
TEST_ID: F5-DASH-002
COMPONENT: Urgency-Ranked Need Feed
DESCRIPTION: Verify need feed is sorted highest urgency first
ACTION:
  1. Seed 5 needs with urgency: [45, 92, 18, 67, 88]
  2. Verify feed order: 92, 88, 67, 45, 18
  3. Verify each card has: urgency badge, issue type icon, summary (2-line truncate),
     location zone, days since reported, Assign button
  4. New report → appears at correct sorted position (not bottom)
  5. 100+ records → verify list performance (no jank)
EXPECTED: Feed sorted correctly, all card elements present, performant
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Fix sorting query (orderBy urgency_score DESC), fix card widget
```

```
TEST_ID: F5-DASH-003
COMPONENT: Real-Time Dashboard Updates
DESCRIPTION: Verify dashboard reflects live Firestore changes without refresh
ACTION:
  1. Note current CRITICAL need count
  2. Write new CRITICAL need from another session
  3. Verify dashboard updates within 2 seconds without page refresh:
     - New card at top of Active Needs feed
     - New red cluster on heatmap
     - Notification bell shows new alert
  4. Mark existing need as resolved → verify it moves to Resolved tab
EXPECTED: Real-time sync for all three UI areas
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Implement Firestore onSnapshot listeners
```

```
TEST_ID: F5-DASH-004
COMPONENT: Impact Analytics Chart
DESCRIPTION: Verify 30-day trend chart renders correctly
ACTION:
  1. Seed 30 days of historical data
  2. Verify chart renders with x-axis as 30-day timeline
  3. Verify two series: "Needs Resolved" (green) and "Active Needs" (red/amber)
  4. Verify current values match live Firestore counts
  5. Zero historical data → verify empty state: "No data yet"
EXPECTED: Chart renders with correct data, handles empty state
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Add empty state handling, fix chart data binding
```

```
TEST_ID: F5-DASH-005
COMPONENT: Upload Report Flow from Dashboard
DESCRIPTION: Verify Upload CTA launches all intake modes
ACTION:
  1. Click "Upload Report"
  2. Verify 4 options appear: Upload Photo, Import CSV, Manual Entry, WhatsApp
  3. Each option opens correct flow
  4. Cancel at each step → modal closes cleanly (no state leaks)
EXPECTED: All 4 modes accessible, cancel works
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Implement intake mode selector, add proper Navigator.pop() on cancel
```

---

## SECTION 8 — F6: VOLUNTEER MOBILE APP TESTS

```
TEST_ID: F6-VOL-001
COMPONENT: Volunteer Onboarding Flow
DESCRIPTION: Verify complete 8-step onboarding
ACTION:
  1. Welcome screen: "Be the reason someone's problem gets solved today"
  2. Google Sign-In screen
  3. Skills selection: 16 skill chips, multi-select, minimum 1 required
  4. Location permission screen with clear explanation
  5. Availability grid: 7 days × 3 time slots
  6. Max travel distance slider (1-20km)
  7. Cause preferences (optional)
  8. First matched task appears immediately after completion
  9. Back navigation preserves data at each step
EXPECTED: All 8 steps correct, validation works, data persists
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Implement missing steps, fix navigation stack
```

```
TEST_ID: F6-VOL-002
COMPONENT: Volunteer Task Feed
DESCRIPTION: Verify personalized task feed
ACTION:
  Log in as test volunteer (skills: medical_first_aid, location: Dharavi)
  1. Verify tasks personalized to this volunteer's skills
  2. Each card: urgency badge, issue icon, summary, impact framing in green,
     distance chip, time estimate, Accept button
  3. Health task ranks higher than food task for medical volunteer
  4. Empty state: "You're all caught up — check back soon"
  5. Pull-to-refresh loads fresh data
EXPECTED: Feed personalized, all card elements present, empty state works
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Fix match score query, add null safety for distance/impact fields
```

```
TEST_ID: F6-VOL-003
COMPONENT: Task Acceptance → Check-In → Completion Flow
DESCRIPTION: Verify complete 3-step task execution
ACTION:
  ACCEPT:
  1. Tap Accept → task detail screen + Google Maps directions
  2. Confirm → assignment created (status=accepted)
  3. Task moves from Available to My Tasks

  CHECK-IN:
  4. Tap Check In → GPS captured
  5. Within 500m of task → status=checked_in
  6. Wrong location (5km away) → warning shown

  COMPLETE:
  7. Tap Mark Complete → photo proof upload (optional)
  8. Assignment status → completed
  9. Volunteer impact_stats updated atomically
  10. Impact scorecard animation triggers
EXPECTED: Full 3-step flow, all status transitions, stats updated
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Implement missing status transitions, fix GPS proximity check
```

```
TEST_ID: F6-VOL-004
COMPONENT: Push Notifications
DESCRIPTION: Verify FCM notifications sent for critical needs
ACTION:
  1. Verify valid FCM token stored in volunteer document
  2. Create CRITICAL need in volunteer's zone
  3. Verify notification arrives within 30 seconds:
     title: "CRITICAL Need Near You"
     body: "{summary} — {distance}km away"
  4. Tap notification → app opens to specific task detail
  5. Permission denied → graceful fallback (in-app alert)
EXPECTED: Notifications sent, tap opens correct screen
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Fix FCM token refresh, fix notification payload
```

---

## SECTION 9 — F7: GAMIFICATION TESTS

```
TEST_ID: F7-GAME-001
COMPONENT: Impact Scorecard
DESCRIPTION: Verify post-completion scorecard renders correctly
ACTION:
  After task completion, verify scorecard shows:
  1. "You helped X families today" (X = affected_count)
  2. "You resolved a CRITICAL/HIGH/MEDIUM/LOW need"
  3. Cumulative stats: total_tasks, total_people_helped, total_hours
  4. Community rank position
  5. Streak information
  6. Newly earned badges
  7. Animation plays correctly
  8. "Find Next Task" → returns to feed
EXPECTED: All data correct, animations work, buttons functional
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Fix data binding from Firestore stats
```

```
TEST_ID: F7-GAME-002
COMPONENT: Points System
DESCRIPTION: Verify impact points are correctly awarded
ACTION:
  Verify points awarded atomically (FieldValue.increment):
  - Accept task: +5
  - Complete regular task: +20
  - Complete CRITICAL (urgency > 85): +50
  - Upload photo proof: +5
  - First-ever task: +25 welcome bonus
  - 3 tasks same week: 1.5× streak multiplier applied
  - Points cannot go negative
EXPECTED: Correct points, multiplier works, atomic updates
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Implement FieldValue.increment, fix multiplier logic
```

```
TEST_ID: F7-GAME-003
COMPONENT: Badge System
DESCRIPTION: Verify badges awarded correctly
ACTION:
  - Complete CRITICAL task → "First Responder 🚨" badge
  - 500 total people helped → "Community Champion 🏆" badge
  - 7 consecutive days → "Streak Hero 🔥" badge
  - 5 Hindi reports submitted → "Multilingual Helper 🌐" badge
  - 10 paper photos uploaded → "Data Pioneer 📊" badge
  - Already-earned badge → NOT awarded twice
  - New badge → triggers animation/notification
EXPECTED: Correct badge conditions, no duplicates, visual feedback
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Implement badge conditions as Firestore transactions
```

```
TEST_ID: F7-GAME-004
COMPONENT: Leaderboard
DESCRIPTION: Verify district leaderboard works
ACTION:
  1. Top 10 volunteers for current zone, sorted by impact_points DESC
  2. Current user's rank highlighted
  3. Opt-out toggle → shows as "Anonymous Volunteer"
  4. Real-time updates when points change
  5. Fewer than 10 volunteers → shows all available
EXPECTED: Sorted, opt-out works, real-time, empty state handled
SEVERITY_IF_FAIL: LOW
AUTO_FIX: Add opt-out field, fix sort query
```

---

## SECTION 10 — BACKEND API TESTS

```
TEST_ID: API-001
COMPONENT: All Cloud Functions Deployment
DESCRIPTION: Verify all 7 functions deployed and responsive
ACTION:
  1. Run: firebase functions:list
  2. Verify these 7 functions exist and are ACTIVE:
     - onReportCreated (Firestore trigger)
     - processCSVUpload (HTTP POST)
     - getMatchedVolunteers (HTTP GET)
     - flagUrgencyScore (HTTP POST)
     - completeTask (HTTP POST)
     - whatsappWebhook (HTTP POST)
     - scheduledTrendUpdate (Cron)
  3. CORS headers present on all HTTP functions
  4. Minimum 256MB memory for Gemini-calling functions
EXPECTED: All 7 functions deployed, CORS configured
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Deploy missing functions, add CORS middleware, increase memory allocation
```

```
TEST_ID: API-002
COMPONENT: API Error Handling
DESCRIPTION: Verify all HTTP endpoints return correct error codes
ACTION:
  For each HTTP Cloud Function, test:
  - Missing required fields → 400 + field-specific message
  - Invalid authentication → 401
  - Insufficient permissions → 403
  - Non-existent resource → 404
  - Server error → 500 (never expose stack trace)
  - Oversized payload > 10MB → 413
  
  All error responses: {error: "<message>", code: "<code>"}
  No stack traces or internal details exposed to client
EXPECTED: Correct HTTP codes for all error scenarios
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add error handling middleware, consistent error response format
```

```
TEST_ID: API-003
COMPONENT: scheduledTrendUpdate
DESCRIPTION: Verify cron function calculates trends correctly
ACTION:
  Seed 30 days data for Dharavi/food zone:
  - Rising pattern: 2→3→5→8 reports per week
  - Trigger scheduledTrendUpdate manually
  - Verify trend_direction = "RISING"
  - Declining pattern (8→5→3→2) → "FALLING"
  - Flat pattern (4→4→4→4) → "STABLE"
  - RISING zones → FCM notification to coordinators
EXPECTED: Correct trend for all 3 patterns, notifications sent
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Fix linear regression, fix FCM topic targeting
```

---

## SECTION 11 — DATABASE INTEGRITY TESTS

```
TEST_ID: DB-001
COMPONENT: Firestore Schema Validation
DESCRIPTION: Verify all documents conform to defined schema
ACTION:
  Sample 20 random documents from each collection. Verify:

  need_reports:
  - report_id: string (non-empty)
  - lat: number (-90 to 90), lng: number (-180 to 180)
  - issue_type ∈ [food, water, health, housing, education, safety, other]
  - severity_score: integer 1-10
  - urgency_score: integer 0-100
  - status ∈ [open, assigned, in_progress, resolved, flagged]
  - source ∈ [photo, csv, manual, whatsapp, sms]
  - created_at: valid Timestamp

  volunteers:
  - lat/lng rounded to 2 decimal places (privacy requirement)
  - skills: array (never null)
  - impact_stats.total_people_helped: non-negative integer

  assignments:
  - status transitions valid (never skip steps)
EXPECTED: 100% schema compliance, no nulls, no invalid enums
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add write validation in Cloud Functions before storing documents
```

```
TEST_ID: DB-002
COMPONENT: Data Consistency
DESCRIPTION: Verify referential integrity across collections
ACTION:
  1. Every assignment has valid need_report_id (no orphans)
  2. Every assignment has valid volunteer_id (no ghosts)
  3. Every need_report has valid org_id (against organizations collection)
  4. Volunteer total_tasks_completed = count of completed assignments for that volunteer
  5. Need report open_slots = recommended_volunteer_count - active assignment count
  6. Resolved needs have no open assignments
EXPECTED: Zero consistency violations
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add referential checks, implement Firestore transactions
```

```
TEST_ID: DB-003
COMPONENT: Duplicate Detection
DESCRIPTION: Verify duplicate report detection works
ACTION:
  1. Submit two identical reports (same zone + issue_type) within 24 hours
  2. Verify second submission increments report_frequency_30d (not creates new doc)
  3. Verify urgency_score recalculated with new frequency
  4. Same report after 48+ hours → creates NEW document
EXPECTED: Duplicates merged within 48h, new docs after window
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Implement deduplication in onReportCreated
```

```
TEST_ID: DB-004
COMPONENT: Firestore Offline Persistence
DESCRIPTION: Verify app works offline and syncs on reconnect
ACTION:
  1. Enable offline persistence in Flutter
  2. Disable network → verify cached data shown (no crash)
  3. Submit manual report offline → verify locally queued
  4. Re-enable network → verify queued report synced within 5 seconds
  5. Dashboard refreshes with new remote data
EXPECTED: Works offline with cached data, sync on reconnect
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Enable Firestore offline persistence, add sync status indicator
```

---

## SECTION 12 — FRONTEND UI/UX TESTS

```
TEST_ID: UI-001
COMPONENT: Design System Compliance
DESCRIPTION: Verify colors match spec
ACTION:
  Scan all Dart files for color usage. Verify:
  - #1A56DB: CTAs, active nav, links
  - #0E9F6E: success states, resolved needs, low urgency
  - #E3A008: medium urgency, warnings
  - #E02424: critical needs, alerts
  - No hardcoded hex values outside AppColors constants class
  - Material Icons used (not mixed icon packs)
  - No deprecated Colors.accentColor in Flutter
EXPECTED: All colors match spec, centralized constants
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Extract to AppColors class, replace deprecated APIs
```

```
TEST_ID: UI-002
COMPONENT: Responsive Design
DESCRIPTION: Verify UI at all viewport sizes
ACTION:
  Test at: 375px, 414px, 768px, 1024px, 1280px, 1920px
  For each:
  - No horizontal scroll
  - No text overflow / clipping
  - All tap targets >= 44×44px
  - Heatmap fills available space
  - Zero RenderFlex overflow errors in console
EXPECTED: Zero overflow errors at all sizes
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add LayoutBuilder/MediaQuery responsive breakpoints
```

```
TEST_ID: UI-003
COMPONENT: Loading States
DESCRIPTION: Verify all async operations show loading indicators
ACTION:
  Verify loading state shown for:
  - Initial app load
  - Auth check
  - Photo upload (progress indicator with %)
  - OCR processing: "Analyzing image..."
  - Gemini scoring: "AI scoring urgency..."
  - Heatmap initial load
  - Matching: "Finding best volunteers..."
  - CSV import (progress bar with record count)
  - Task acceptance (button loading state — prevents double-tap)
EXPECTED: Every async operation has loading state, no blank screens
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add loading state management to all async widget builders
```

```
TEST_ID: UI-004
COMPONENT: Error States
DESCRIPTION: Verify all errors show friendly messages
ACTION:
  - No internet → "No internet connection" banner (not crash)
  - Gemini error → "AI processing unavailable, try again"
  - Firebase error → "Server error, please retry"
  - Photo too large → "Image too large (max 10MB)"
  - Location denied → "Location needed for matching" explanation
  - No tasks → empty state with illustration + message
  - Session expired → redirect to login with toast
  - GPS unavailable → fallback to manual location input
EXPECTED: Every error shows friendly message, no raw exception strings
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add global error handler, implement error state widgets
```

```
TEST_ID: UI-005
COMPONENT: Navigation and Routing
DESCRIPTION: Verify all navigation works correctly
ACTION:
  1. Bottom nav 4 tabs work: Home, Map, Impact, Profile
  2. Deep link /need/{need_id} → goes to need detail
  3. Back button behavior correct (no stack overflow on double-tap)
  4. Browser URL updates on each route change (Web)
  5. Page title updates in browser tab per route
  6. No double-routes from rapid tapping
EXPECTED: All paths work, browser history correct
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Implement named routes, fix PopScope/WillPopScope
```

---

## SECTION 13 — PERFORMANCE TESTS

```
TEST_ID: PERF-001
COMPONENT: OCR Pipeline Performance
DESCRIPTION: photo upload → urgency score must be < 15 seconds
ACTION:
  1. Upload 2MB test photo, start timer
  2. Stop timer when urgency_score in Firestore
  3. Log individual stage times: upload, OCR, translate, Gemini, scoring
  4. Run 5 times, take average
  5. Verify average < 15s (target 8s)
EXPECTED: Average < 15s, each stage logged
SEVERITY_IF_FAIL: HIGH if > 15s; MEDIUM if 8-15s
AUTO_FIX: Add parallel processing, optimize image compression before upload
```

```
TEST_ID: PERF-002
COMPONENT: Heatmap Render Performance
DESCRIPTION: 50-point heatmap must render < 5 seconds
ACTION:
  1. Seed exactly 50 need_reports, hard-reload dashboard
  2. Measure time to heatmap visible
  3. Run 3 times, take average
  4. Test with 200 points → still acceptable (< 10s)
  5. Check Chrome DevTools for main thread blocking > 50ms
EXPECTED: 50-point heatmap < 5s, no blocking
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Implement data pagination, use WebWorker if needed
```

```
TEST_ID: PERF-003
COMPONENT: Volunteer Matching Performance
DESCRIPTION: Matching API must respond < 8 seconds
ACTION:
  1. Seed 100 volunteer profiles
  2. Call getMatchedVolunteers, measure response time
  3. Run 5 times, average
  4. Verify Distance Matrix is batched (single call)
  5. Test with 500 volunteers → graceful degradation
EXPECTED: Average < 8s, Distance Matrix batched
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Add volunteer zone pre-filter before Distance Matrix call
```

```
TEST_ID: PERF-004
COMPONENT: CSV Import Performance
DESCRIPTION: 50-record import must complete < 30 seconds
ACTION:
  1. Import TEST_CSV_50_RECORDS.csv
  2. Measure from request to response
  3. Verify all 50 in Firestore
  4. Verify < 30s (target 10s)
  5. 500-record CSV → batch write limit respected
EXPECTED: 50 records < 30s, batch limit respected
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Implement chunked Firestore batch writes
```

---

## SECTION 14 — SECURITY TESTS

```
TEST_ID: SEC-001
COMPONENT: Firestore Security Rules — Penetration Test
DESCRIPTION: Simulate unauthorized access attempts
ACTION:
  1. Unauthenticated → read need_reports → MUST DENY
  2. Volunteer A → read volunteer B's profile → MUST DENY
  3. Volunteer → write to need_reports → MUST DENY
  4. Coordinator Org-A → read Org-B need_reports → MUST DENY
  5. Volunteer → increment own impact_points directly → MUST DENY (Cloud Function only)
  6. Admin → read all collections → MUST ALLOW
EXPECTED: All unauthorized access blocked
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Tighten Firestore rules for each failed case
```

```
TEST_ID: SEC-002
COMPONENT: Input Sanitization
DESCRIPTION: Test injection vulnerabilities
ACTION:
  Test in ALL text input fields:
  1. SQL injection: "'; DROP TABLE need_reports; --"
  2. NoSQL injection: {"$gt": ""}
  3. XSS: "<script>alert('xss')</script>"
  4. Path traversal: "../../../etc/passwd"
  5. Oversized input: 100,000 character string
  6. Null bytes: "\u0000"
  7. Gemini prompt injection in report text

  Verify: no crashes, no code execution, no data exposure
EXPECTED: All injection attempts fail safely
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Add input sanitization layer, max length validation
```

```
TEST_ID: SEC-003
COMPONENT: PII Protection
DESCRIPTION: Verify volunteer location anonymized
ACTION:
  1. Create volunteer with precise location: lat=19.052315, lng=72.857359
  2. Read from Firestore → verify lat=19.05, lng=72.86 (2 decimal places only)
  3. Distance Matrix API receives full coordinates from memory (not from Firestore)
  4. Full coordinates NEVER logged in Cloud Function logs
  5. Photo uploads → EXIF metadata stripped before Storage
EXPECTED: Location rounded in DB, EXIF stripped
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add rounding in Firestore write layer, add EXIF strip in upload handler
```

```
TEST_ID: SEC-004
COMPONENT: Rate Limiting
DESCRIPTION: Verify Cloud Functions are rate-limited
ACTION:
  1. Send 101 rapid requests from same IP
  2. Verify requests 101+ return 429 Too Many Requests
  3. Rate limit: 100 req/min per IP
  4. Legitimate requests after cooldown succeed
  5. Firebase App Check enabled
EXPECTED: Rate limiting active, App Check enabled
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add rate limiting middleware, enable Firebase App Check
```

---

## SECTION 15 — ACCESSIBILITY TESTS

```
TEST_ID: A11Y-001
COMPONENT: Color Contrast (WCAG 2.1 AA)
DESCRIPTION: Verify contrast ratios meet minimum
ACTION:
  Test all foreground/background color combinations:
  - White on #E02424 (red badges) → must be >= 4.5:1
  - White on #1A56DB (blue buttons) → must be >= 4.5:1
  - Dark text on #E3A008 (amber) → must be >= 4.5:1
  - Body text #111827 on white → must be >= 7:1
  - Placeholder text → must be >= 4.5:1
EXPECTED: All combinations meet WCAG 2.1 AA
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Adjust colors to meet contrast requirements
```

```
TEST_ID: A11Y-002
COMPONENT: Critical Alerts — Not Color-Only
DESCRIPTION: Urgency communicated through more than color
ACTION:
  - CRITICAL card: has RED color AND "CRITICAL" text label
  - HIGH card: has ORANGE color AND "HIGH" text label
  - Errors: have red border AND descriptive text
  - Map markers: have color AND shape/icon differentiation
EXPECTED: Every urgency indicator uses color + text
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add text labels to all color-coded elements
```

```
TEST_ID: A11Y-003
COMPONENT: Screen Reader / Semantics
DESCRIPTION: Verify Flutter Semantics wrappers implemented
ACTION:
  1. Enable accessibility testing mode
  2. Verify Semantics labels on all interactive elements:
     - UrgencyCard: "CRITICAL need: Food shortage in Dharavi"
     - Accept button: "Accept task: Food distribution"
     - Map: "Urgency heatmap, tap to explore needs"
  3. All images have alt text
  4. Form fields have associated labels
  5. Run flutter_test with AccessibilityGuideline
EXPECTED: Zero accessibility widget failures
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Add Semantics wrapper to all custom widgets
```

---

## SECTION 16 — INTEGRATION & END-TO-END TESTS

```
TEST_ID: E2E-001
COMPONENT: Full Pipeline — The Demo Money Shot
DESCRIPTION: THE most critical test. Validates the exact hackathon demo flow.
ACTION:
  This test MUST pass perfectly. It is the judge demo.

  1. START TIMER
  2. Open coordinator dashboard (logged in)
  3. Verify heatmap loaded with seed data
  4. Click Upload Report → Upload Photo
  5. Upload TEST_IMAGE_HANDWRITTEN_HINDI.jpg (Hindi handwritten survey)
  6. CHECKPOINT 1 (<5s): Upload succeeds, processing indicator shown
  7. CHECKPOINT 2 (<15s): New need_report in Firestore
  8. CHECKPOINT 3 (<17s): New red marker on heatmap at correct coordinates
  9. CHECKPOINT 4 (<20s): Urgency score shown on new need card in feed
  10. Click Assign Volunteers on new card
  11. CHECKPOINT 5 (<23s): Top-3 matched volunteers appear with explanations
  12. Confirm assignment for top match
  13. CHECKPOINT 6 (<25s): Assignment created in Firestore
  14. Switch to volunteer app
  15. CHECKPOINT 7 (<27s): New task in volunteer's feed
  16. STOP TIMER

  PASS: All 7 checkpoints pass within time budgets
  DEMO REQUIREMENT: Total < 30 seconds (target 20-25 seconds)
EXPECTED: All checkpoints pass, total < 30s
SEVERITY_IF_FAIL: CRITICAL — Fix this before anything else
AUTO_FIX: Profile each stage, optimize slowest bottleneck first
```

```
TEST_ID: E2E-002
COMPONENT: Full Volunteer Journey
DESCRIPTION: Complete volunteer experience from login to scorecard
ACTION:
  1. New volunteer logs in (first time)
  2. Completes 8-step onboarding
  3. Views personalized task feed
  4. Accepts CRITICAL task
  5. Receives push notification confirmation
  6. GPS check-in at location
  7. Marks complete with photo
  8. Views impact scorecard
  9. Verifies impact_points increased correctly
  10. Checks badge gallery for new badges
  11. Checks leaderboard position

  Verify no crashes, correct state transitions at every step
EXPECTED: Complete journey without any manual intervention
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Fix broken state transitions
```

```
TEST_ID: E2E-003
COMPONENT: CSV Import → Heatmap → Match Pipeline
DESCRIPTION: Complete bulk import flow
ACTION:
  1. Import TEST_CSV_50_RECORDS.csv via dashboard
  2. All 50 records within 30 seconds
  3. Heatmap shows 50 points across Mumbai zones
  4. Filter to CRITICAL needs → correct subset shown
  5. Select CRITICAL need → run matching → top-3 volunteers returned
  6. Trend detection runs on new data, zone_stats updated
EXPECTED: Full bulk pipeline works end-to-end
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Debug import → score → visualize pipeline
```

```
TEST_ID: E2E-004
COMPONENT: Multi-Session Real-Time Sync
DESCRIPTION: Two simultaneous users see consistent real-time state
ACTION:
  1. Coordinator open in Browser A, Volunteer in Browser B
  2. Browser A uploads CRITICAL report → Browser B sees new task (< 5s)
  3. Browser B accepts task → Browser A sees assignment update (< 5s)
  4. Browser B completes task → Browser A sees Resolved tab update (< 5s)
EXPECTED: Both sessions in sync within 5 seconds of each change
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Ensure all writes use onSnapshot listeners on both clients
```

---

## SECTION 17 — CONTENT & COPY TESTS

```
TEST_ID: COPY-001
COMPONENT: Impact Framing Text (Gemini Prompt 3)
DESCRIPTION: Verify impact messages are specific and motivating
ACTION:
  Test with: issue_type=food, affected_count=47, location=Dharavi
  - MUST contain: specific number (47), location (Dharavi), action word
  - MUST NOT contain: "make a difference", "help the community" (generic)
  - MUST be <= 25 words
  - MUST use present tense

  Test with null affected_count → estimated range used gracefully
  Test with large count (200) → urgency conveyed
EXPECTED: Specific messages <= 25 words, handles null, present tense
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Adjust Gemini Prompt 3 for word count and specificity
```

```
TEST_ID: COPY-002
COMPONENT: Error Messages and Empty States
DESCRIPTION: All user-facing copy is helpful and professional
ACTION:
  Verify across entire app:
  1. No raw error codes shown (PERMISSION_DENIED → "You don't have access")
  2. No stack traces shown to users
  3. All empty states: illustration + message + action button
  4. Loading messages are specific (not just "Loading...")
  5. Form validation messages specific (not "Invalid input")
  6. Dates in Indian locale format (DD/MM/YYYY, IST)
EXPECTED: All copy user-friendly, no technical jargon
SEVERITY_IF_FAIL: MEDIUM
AUTO_FIX: Replace all raw error codes with friendly messages
```

---

## SECTION 18 — DEMO READINESS TESTS

```
TEST_ID: DEMO-001
COMPONENT: Demo Data Seeding
DESCRIPTION: Verify Firestore populated with compelling realistic data
ACTION:
  Verify Firestore contains:
  - need_reports: 50+ documents
    Dharavi: 12+ (food/water/health, highest urgency)
    Kurla: 10+, Govandi: 10+, Mankhurd: 8+, Vikhroli: 8+
  - At least 3 CRITICAL needs (score > 85)
  - At least 5 different issue_types
  - At least 3 Hindi-language reports
  - At least 2 reports with source="photo"
  - volunteers: 20+ profiles varied across zones
  - organizations: 1 test NGO with coordinator account
EXPECTED: Rich realistic demo data, heatmap visually compelling
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Run demo seeding script to populate all collections
```

```
TEST_ID: DEMO-002
COMPONENT: Firebase Hosting Live URL
DESCRIPTION: Verify live URL is accessible
ACTION:
  1. Navigate to Firebase Hosting URL (from README.md)
  2. Verify load within 5 seconds on first visit
  3. Verify Google Sign-In button visible
  4. No SSL certificate errors
  5. Works on Chrome Android
  6. Works on Safari iOS/Mac
  7. No critical console errors on page load
EXPECTED: Works on all browsers, loads < 5s, no console errors
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Run firebase deploy --only hosting, fix build errors
```

```
TEST_ID: DEMO-003
COMPONENT: README.md Completeness
DESCRIPTION: GitHub README meets submission requirements
ACTION:
  Verify ALL present:
  1. "Live Demo" link at very top of file
  2. Architecture diagram (Mermaid.js code block)
  3. Setup instructions (3 commands or less)
  4. At least 5 screenshots
  5. Tech stack badges (Flutter/Firebase/Gemini/Google Maps)
  6. Team profiles section
  7. SDG alignment statement (SDG 1, 10, 17)
  8. Research references section
  9. "Built for Google Solution Challenge 2026"
  10. GitHub topics: [smart-resource-allocation, volunteer-coordination,
      google-gemini, flutter, firebase, ngo-tech, solution-challenge-2026]
EXPECTED: All 10 elements present, GitHub topics set
SEVERITY_IF_FAIL: HIGH
AUTO_FIX: Add missing sections to README.md
```

---

## SECTION 19 — REGRESSION & SMOKE TESTS

```
TEST_ID: SMOKE-001
COMPONENT: App Boot Sequence
DESCRIPTION: Verify clean cold-launch startup
ACTION:
  1. Hard refresh (clear cache + reload)
  2. AlloCare logo shown (not blank)
  3. Auth check completes within 3 seconds
  4. If logged in → dashboard (not login)
  5. If logged out → login (not dashboard)
  6. No uncaught exceptions in first 10 seconds
  7. No "null check operator used on null value" in console
EXPECTED: Clean boot, correct routing, zero null exceptions
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Fix null safety issues, fix auth check timing
```

```
TEST_ID: SMOKE-002
COMPONENT: Core User Journeys — Rapid Smoke
DESCRIPTION: Rapid validation of 3 critical flows
ACTION:
  Flow 1 (< 2 min): Coordinator logs in → sees dashboard → uploads photo →
                     heatmap updates → assigns volunteer

  Flow 2 (< 2 min): Volunteer logs in → task feed → accepts task →
                     marks complete → impact scorecard

  Flow 3 (< 2 min): Coordinator imports CSV → 50 records on heatmap →
                     flags urgency score → score updated

  ALL three flows must complete without error.
  If any fails: fix immediately before continuing.
EXPECTED: All 3 flows complete in under 2 minutes each
SEVERITY_IF_FAIL: CRITICAL
AUTO_FIX: Fix immediately before running remaining tests
```

---

## SECTION 20 — FINAL VALIDATION CHECKLIST

```
TEST_ID: FINAL-001
COMPONENT: Masterplan P0 Feature Coverage
DESCRIPTION: Verify all 7 P0 features from masterplan are implemented
ACTION:
  Check each P0 feature:
  ✓/✗ F1 — Multi-Source Data Ingestion (photo, CSV, manual, WhatsApp)
  ✓/✗ F2 — Gemini Urgency Scoring Engine
  ✓/✗ F3 — Google Maps Urgency Heatmap (deck.gl, color gradient, clickable)
  ✓/✗ F4 — Smart Volunteer Matching (skill × proximity × availability, top-3)
  ✓/✗ F5 — NGO Coordinator Dashboard (real-time feed, heatmap, analytics)
  ✓/✗ F6 — Volunteer App (task feed, accept, check-in, complete)
  ✓/✗ F7 — Impact Scorecard & Gamification (points, badges, leaderboard)

  For each ✗: log CRITICAL, create stub implementation
  For each ✓: confirm it passed tests in sections above
EXPECTED: All 7 P0 features implemented and passing tests
SEVERITY_IF_FAIL: CRITICAL for any missing P0 feature
AUTO_FIX: Implement missing features per masterplan architecture spec
```

```
TEST_ID: FINAL-002
COMPONENT: Google Technology Coverage
DESCRIPTION: Verify all required Google technologies actively used in code
ACTION:
  Verify code ACTUALLY CALLS these APIs (not just mentioned in docs):
  ✓/✗ Gemini 1.5 Pro API
  ✓/✗ Cloud Vision API
  ✓/✗ Google Maps Platform (heatmap + distance matrix + geocoding)
  ✓/✗ Google Translate API
  ✓/✗ Firebase Auth (Google Sign-In)
  ✓/✗ Firestore (real-time listeners)
  ✓/✗ Firebase Cloud Functions
  ✓/✗ Firebase Storage
  ✓/✗ Firebase Hosting
  ✓/✗ Firebase Cloud Messaging
  ✓/✗ Flutter

  Count: minimum 8 required for strong submission (target: 11/11)
EXPECTED: Minimum 8 Google technologies actively used
SEVERITY_IF_FAIL: HIGH if < 8; MEDIUM if 8-10
AUTO_FIX: Integrate missing critical Google services
```

---

## BUG REPORT FORMAT

After completing all tests, generate a structured bug report in this exact format:

```markdown
# AlloCare Autonomous Test Report
Generated: {timestamp}
Agent: Antigravity Autonomous Test Agent
Total Tests Run: {count}
Tests Passed: {count}
Tests Failed: {count}
Auto-Fixed: {count}
Remaining Open Issues: {count}

---

## CRITICAL BUGS (Fix before demo)
| ID | Component | Description | Root Cause | Fix Applied | Status |
|----|-----------|-------------|------------|-------------|--------|
| BUG-001 | ... | ... | ... | ... | FIXED/OPEN |

## HIGH SEVERITY BUGS
| ID | Component | Description | Root Cause | Fix Applied | Status |
|----|-----------|-------------|------------|-------------|--------|

## MEDIUM SEVERITY BUGS
| ID | Component | Description | Root Cause | Fix Applied | Status |
|----|-----------|-------------|------------|-------------|--------|

## LOW SEVERITY BUGS
| ID | Component | Description | Root Cause | Fix Applied | Status |
|----|-----------|-------------|------------|-------------|--------|

---

## PERFORMANCE SUMMARY
| Operation | Target | Measured Avg | Status |
|-----------|--------|--------------|--------|
| OCR Pipeline | < 15s | {value}s | PASS/FAIL |
| Heatmap Render | < 5s | {value}s | PASS/FAIL |
| Volunteer Matching | < 8s | {value}s | PASS/FAIL |
| CSV Import (50 records) | < 30s | {value}s | PASS/FAIL |
| Real-time Heatmap Update | < 2s | {value}s | PASS/FAIL |

---

## GOOGLE TECHNOLOGY COVERAGE
Total Google APIs integrated: {count}/11
Missing APIs: {list or "none"}

---

## P0 FEATURE COMPLETION
F1 Multi-Source Ingestion: {COMPLETE/PARTIAL/MISSING}
F2 Gemini Urgency Scoring: {COMPLETE/PARTIAL/MISSING}
F3 Google Maps Heatmap: {COMPLETE/PARTIAL/MISSING}
F4 Volunteer Matching: {COMPLETE/PARTIAL/MISSING}
F5 NGO Dashboard: {COMPLETE/PARTIAL/MISSING}
F6 Volunteer App: {COMPLETE/PARTIAL/MISSING}
F7 Gamification: {COMPLETE/PARTIAL/MISSING}

---

## SECURITY POSTURE
Hardcoded API keys found: {YES/NO}
Firestore public access: {YES/NO — must be NO}
Input sanitization: {PASS/FAIL}
PII protection: {PASS/FAIL}
Rate limiting active: {YES/NO}

---

## ACCESSIBILITY SCORE
Color contrast WCAG 2.1 AA: {PASS/FAIL}
Color-only alerts: {NONE — PASS / FOUND — FAIL}
Screen reader support: {PASS/FAIL}

---

## DEMO READINESS SCORE: {score}/100
- Core Demo Flow (E2E-001): {PASS/FAIL}
- Live URL accessible: {PASS/FAIL}
- Demo data seeded: {PASS/FAIL}
- README complete: {PASS/FAIL}
- Performance benchmarks met: {PASS/FAIL}
- All P0 features functional: {PASS/FAIL}
- Google tech coverage >= 8: {PASS/FAIL}

---

## FINAL VERDICT
{DEMO READY | NEEDS WORK — {count} critical issues remain | NOT READY}

## PRIORITY FIX LIST (in order — fix top to bottom)
1. {BUG-ID}: {fix description} — estimated time: {time}
2. {BUG-ID}: {fix description} — estimated time: {time}
3. {BUG-ID}: {fix description} — estimated time: {time}
```

---

## APPENDIX — TEST DATA SPECIFICATIONS

### TEST_CSV_50_RECORDS.csv Schema
```
report_id,zone,lat,lng,issue_type,severity,affected_count,report_text,language
R001,Dharavi,19.0522,72.8573,food,8,47,"Severe food shortage in Ward 8...",en
R002,Govandi,19.0604,72.9209,health,9,23,"Medical camp needed urgently...",en
R003,Kurla,19.0728,72.8826,water,7,61,"Water supply cut for 4 days...",en
...
(Include 3 Hindi language rows with language=hi)
(Include at least 5 CRITICAL severity rows with severity >= 9)
(Spread across 5 zones: Dharavi, Kurla, Govandi, Mankhurd, Vikhroli)
```

### TEST VOLUNTEER PROFILES (20 required)
```
Seed 20 volunteers with:
- Mix of skills from taxonomy
- Spread across 5 Mumbai zones
- 5 volunteers with Hindi language skill
- 5 volunteers currently offline (status=offline)
- Varied max_distance_km (1km to 20km)
- Mix of availability patterns
```

### TEST IMAGE FILES NEEDED
```
TEST_IMAGE_1.jpg         — Clear printed English survey (text readable)
TEST_IMAGE_HINDI.jpg     — Printed Hindi survey text
TEST_IMAGE_HANDWRITTEN.jpg — Handwritten mixed-language survey
TEST_IMAGE_BLURRY.jpg    — Out-of-focus survey (for OCR failure test)
TEST_IMAGE_BLANK.jpg     — White/blank image (for empty detection test)
```

---

*AlloCare Test Specification v1.0 | 95 total tests across 20 sections*
*Google Solution Challenge 2026 | Hack2Skill × GDG × Google*
*Feed this entire file to the Antigravity agent without modification.*
*All 95 tests must execute. No skipping. No approximations.*
*Agent must auto-fix all CRITICAL and HIGH severity findings before completing.*
