"""
AlloCare API — FastAPI Backend
Fully functional with free APIs only. No cloud billing required.
Only needs: GEMINI_API_KEY (free from AI Studio)

Supports two deployment modes (set via DEPLOYMENT env var):
  - "firebase" (default): Uses Firebase/Firestore
  - "render": Uses local JSON file store, no Firebase deps needed
"""
import os
import io
import json
import base64
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Form, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

# ── Deployment mode ────────────────────────────────────────────────────────────
DEPLOYMENT = os.environ.get("DEPLOYMENT", "render").lower()

if DEPLOYMENT == "firebase":
    from firebase_functions import https_fn
    from firebase_admin import initialize_app
    from a2wsgi import ASGIMiddleware
    initialize_app()

# ── initialise ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Choose data store based on deployment mode
if DEPLOYMENT == "firebase":
    from data_store import store
else:
    from data_store_local import store

from urgency_scorer import calculate_urgency_score, detect_trend

# Seed demo data on first run
store.seed_demo_data()

app = FastAPI(
    title="AlloCare API",
    description="AI-powered volunteer deployment platform. Free APIs only.",
    version="2.0.0",
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    email: str
    password: str
    display_name: str
    role: str # "organization" or "volunteer"
    skills: Optional[List[str]] = []
    zone: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register", tags=["auth"])
async def register(user: UserCreate):
    # Check if email exists
    existing = store.query("users", filters={"email": user.email}, limit=1)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    password_hash = store.hash_password(user.password)
    new_user = {
        "email": user.email,
        "password_hash": password_hash,
        "display_name": user.display_name,
        "role": user.role
    }
    user_id = store.add("users", new_user)
    
    # If volunteer, also create a volunteer profile
    if user.role == "volunteer":
        vol_profile = {
            "user_id": user_id,
            "display_name": user.display_name,
            "email": user.email,
            "skills": user.skills,
            "zone": user.zone or "Unknown",
            "status": "available",
            "impact_points": 0,
            "impact_stats": {"total_tasks_completed": 0, "total_people_helped": 0},
            "lat": 0.0, # Would need real geocoding ideally
            "lng": 0.0
        }
        store.add("volunteers", vol_profile)
        
    return {"message": "Registration successful", "user": {"id": user_id, "email": user.email, "role": user.role, "display_name": user.display_name}}

@app.post("/api/auth/login", tags=["auth"])
async def login(credentials: UserLogin):
    users = store.query("users", filters={"email": credentials.email}, limit=1)
    if not users:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    user = users[0]
    if user.get("password_hash") != store.hash_password(credentials.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # Return user without password_hash
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    safe_user["id"] = safe_user.get("_id", "")  # Ensure 'id' is always present
    return {"message": "Login successful", "user": safe_user}


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH & SYSTEM ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/system/keys/health", tags=["system"])
async def api_keys_health():
    """Super Admin endpoint: Returns the health of the Gemini Key Pool."""
    import gemini_client
    import traceback
    try:
        if gemini_client._init_models() and gemini_client._gemini_pool:
            health_list = gemini_client._gemini_pool.health()
            
            healthy_keys = sum(1 for k in health_list if k["status"] == "HEALTHY")
            rate_limited = sum(1 for k in health_list if k["status"] in ("RATE_LIMITED", "QUOTA_EXHAUSTED", "SERVER_ERROR"))
            retired = sum(1 for k in health_list if k["status"] == "RETIRED")
            
            keys_dict = {}
            for i, k in enumerate(health_list):
                st = k["status"]
                frontend_status = "active" if st == "HEALTHY" else "retired" if st == "RETIRED" else "rate_limited"
                keys_dict[f"key{i}"] = {
                    "status": frontend_status,
                    "key_suffix": k["key_suffix"],
                    "rpm_used": k["rpm_used_last_min"],
                    "rpd_used": k["rpd_used_today"],
                    "failure_count": k["failures"],
                    "cooldown_remaining_s": k["cooldown_remaining_s"]
                }
                
            return {
                "status": "success", 
                "keys": {
                    "summary": {
                        "total_keys": len(health_list),
                        "healthy_keys": healthy_keys,
                        "rate_limited_keys": rate_limited,
                        "retired_keys": retired
                    },
                    "keys": keys_dict
                }
            }
        
        # If we got here, it returned false
        return {"status": "error", "message": "Gemini pool not configured or failed to init (returned False)."}
    except Exception as e:
        return {"status": "error", "message": f"Exception during init: {str(e)}", "traceback": traceback.format_exc()}

@app.get("/api/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    gemini_key = bool(os.environ.get("GEMINI_API_KEY"))
    need_count = store.count("need_reports")
    vol_count = store.count("volunteers")
    return {
        "status": "healthy",
        "version": "2.0.0",
        "gemini_api_key_configured": gemini_key,
        "data": {"needs": need_count, "volunteers": vol_count},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/demo/seed", tags=["system"])
async def seed_demo_data():
    """Force re-seed demo data (clears existing data)."""
    store.clear_collection("need_reports")
    store.clear_collection("volunteers")
    store.clear_collection("assignments")
    store.seed_demo_data()
    return {"status": "success", "message": "Demo data seeded"}


# ═══════════════════════════════════════════════════════════════════════════════
# NEED REPORTS — CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/needs", tags=["needs"])
async def list_needs(
    status: Optional[str] = None,
    issue_type: Optional[str] = None,
    urgency_label: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """List need reports with optional filters."""
    filters = {}
    if status:
        filters["status"] = status.split(",")
    if issue_type and issue_type != "all":
        filters["issue_type"] = issue_type
    if urgency_label and urgency_label != "all":
        filters["urgency_label"] = urgency_label

    needs = store.query("need_reports", filters=filters, order_by="urgency_score", descending=True, limit=limit)
    # Add id field from _id
    for n in needs:
        n["id"] = n.get("_id", "")
    return {"needs": needs, "total": len(needs)}


@app.get("/api/needs/{need_id}", tags=["needs"])
async def get_need(need_id: str):
    """Get a single need report."""
    need = store.get("need_reports", need_id)
    if not need:
        raise HTTPException(status_code=404, detail="Need not found")
    need["id"] = need.get("_id", need_id)
    return need


class CreateNeedRequest(BaseModel):
    raw_text: str
    source: str = "manual"
    zone: Optional[str] = ""
    issue_type: Optional[str] = "other"
    severity_score: Optional[int] = 5
    affected_count: Optional[int] = None

@app.post("/api/needs", tags=["needs"])
async def create_need(payload: CreateNeedRequest):
    """Create a new need report and optionally process with AI."""
    doc_id = store.add("need_reports", {
        "raw_text": payload.raw_text,
        "source": payload.source,
        "zone": payload.zone or "Unknown",
        "issue_type": payload.issue_type,
        "severity_score": payload.severity_score,
        "affected_count": payload.affected_count,
        "status": "open",
        "urgency_score": 0,
        "urgency_label": "low",
        "org_id": "demo_org",
    })
    return {"id": doc_id, "status": "created"}


# ═══════════════════════════════════════════════════════════════════════════════
# AI PROCESSING PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

class ProcessReportRequest(BaseModel):
    report_id: Optional[str] = None
    raw_text: Optional[str] = None
    source: str = "manual"

@app.post("/api/process_report", tags=["ai"])
async def process_report(payload: ProcessReportRequest):
    """
    Full AI processing pipeline:
    1. Language detection + translation (free via deep-translator)
    2. Gemini extraction (free via AI Studio)
    3. Geocoding (free via Nominatim)
    4. Urgency scoring (local algorithm)
    5. Coordinator explanation (free via Gemini)
    """
    report_id = payload.report_id
    raw_text = payload.raw_text

    # If report_id provided, fetch from store
    if report_id:
        data = store.get("need_reports", report_id)
        if not data:
            raise HTTPException(status_code=404, detail="Report not found")
        raw_text = data.get("raw_text", raw_text)
    elif raw_text:
        # Create new report
        report_id = store.add("need_reports", {
            "raw_text": raw_text,
            "source": payload.source,
            "status": "open",
            "urgency_score": 0,
            "urgency_label": "low",
            "org_id": "demo_org",
        })
    else:
        raise HTTPException(status_code=400, detail="Either report_id or raw_text required")

    logger.info(f"[processReport] Processing report {report_id}")

    try:
        # Step 1 — Language detection + translation (FREE)
        from translate_client import detect_and_translate
        english_text, detected_lang = detect_and_translate(raw_text)

        # Step 2 — Gemini extraction (FREE via AI Studio)
        from gemini_client import extract_urgency, generate_coordinator_explanation
        extracted = extract_urgency(english_text)

        if not extracted:
            store.update("need_reports", report_id, {
                "status": "flagged",
                "flag_reason": "Gemini extraction failed",
            })
            return {"status": "error", "message": "Gemini extraction failed", "report_id": report_id}

        # Step 3 — Geocoding (FREE via Nominatim)
        from maps_client import geocode_location
        location_text = extracted.get("location_text", "Mumbai")
        geo = geocode_location(location_text)

        # Step 4 — Frequency count
        frequency = store.count("need_reports", filters={
            "zone": extracted.get("location_text", ""),
            "issue_type": extracted.get("issue_type", "other"),
        })
        frequency = max(1, frequency)

        # Step 5 — Urgency scoring (LOCAL algorithm)
        score_data = calculate_urgency_score(
            severity=extracted.get("severity_score", 5),
            frequency=frequency,
            days_since_first_report=1,
        )

        # Step 6 — Coordinator explanation (FREE via Gemini)
        explanation = generate_coordinator_explanation(
            issue_type=extracted.get("issue_type", "other"),
            severity=extracted.get("severity_score", 5),
            affected_count=extracted.get("affected_count"),
            location=extracted.get("location_text", ""),
            frequency=frequency,
            days=1,
        )

        # Step 7 — Update report in store
        update_payload = {
            "raw_text": raw_text,
            "language_detected": detected_lang,
            "issue_type": extracted.get("issue_type", "other"),
            "zone": extracted.get("location_text", "Unknown"),
            "severity_score": extracted.get("severity_score", 5),
            "affected_count": extracted.get("affected_count"),
            "summary": extracted.get("summary", ""),
            "required_skills": extracted.get("required_skills", []),
            "recommended_volunteer_count": extracted.get("recommended_volunteer_count", 2),
            "urgency_score": score_data["score"],
            "urgency_label": score_data["label"],
            "report_frequency_30d": frequency,
            "coordinator_explanation": explanation,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "status": "open",
            "trend_direction": "stable",
        }

        if geo:
            update_payload["lat"] = geo["lat"]
            update_payload["lng"] = geo["lng"]

        store.update("need_reports", report_id, update_payload)

        return {
            "status": "success",
            "report_id": report_id,
            "score": score_data["score"],
            "label": score_data["label"],
            "summary": extracted.get("summary", ""),
            "zone": extracted.get("location_text", ""),
            "issue_type": extracted.get("issue_type", ""),
            "lat": geo["lat"] if geo else None,
            "lng": geo["lng"] if geo else None,
        }

    except Exception as e:
        logger.error(f"[processReport] Failed: {e}", exc_info=True)
        store.update("need_reports", report_id, {
            "status": "flagged",
            "flag_reason": f"Processing error: {str(e)[:200]}",
        })
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# OCR ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class OCRRequest(BaseModel):
    image_data: str  # base64 encoded image

@app.post("/api/ocr", tags=["ai"])
async def ocr_extract(payload: OCRRequest):
    """Extract text from image using Gemini Vision (free)."""
    from vision_client import extract_text_from_base64

    text = extract_text_from_base64(payload.image_data)
    if not text:
        return {"text": "", "error": "Could not extract text from image"}

    return {"text": text, "characters": len(text)}


@app.post("/api/ocr/upload", tags=["ai"])
async def ocr_upload(file: UploadFile = File(...)):
    """Extract text from uploaded image file using Gemini Vision."""
    from vision_client import extract_text_from_image_bytes

    content = await file.read()
    mime_type = file.content_type or "image/jpeg"
    text = extract_text_from_image_bytes(content, mime_type)

    if not text:
        return {"text": "", "error": "Could not extract text from image"}

    return {"text": text, "characters": len(text)}


# ═══════════════════════════════════════════════════════════════════════════════
# CSV UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/process_csv", tags=["ai"])
async def process_csv_upload(file: UploadFile = File(...)):
    """Import needs from CSV file."""
    try:
        import pandas as pd

        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))

        column_map = {
            "location": "zone", "area": "zone", "place": "zone",
            "problem": "raw_text", "description": "raw_text", "issue": "raw_text",
            "people": "affected_count", "households": "affected_count",
            "severity": "severity_score", "priority": "severity_score",
        }
        df.rename(columns={k: v for k, v in column_map.items() if k in df.columns}, inplace=True)

        imported = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                raw_text = str(row.get("raw_text", row.get("zone", "Unknown issue")))
                zone = str(row.get("zone", "Unknown"))

                severity = 5
                try:
                    severity = int(row.get("severity_score", 5))
                except (ValueError, TypeError):
                    pass

                affected = None
                try:
                    val = row.get("affected_count")
                    if pd.notna(val):
                        affected = int(val)
                except (ValueError, TypeError):
                    pass

                store.add("need_reports", {
                    "org_id": "demo_org",
                    "raw_text": raw_text,
                    "zone": zone,
                    "source": "csv",
                    "status": "open",
                    "severity_score": severity,
                    "affected_count": affected,
                    "urgency_score": 0,
                    "urgency_label": "low",
                })
                imported += 1

            except Exception as row_err:
                errors.append({"row": idx + 2, "reason": str(row_err)})

        return {"imported": imported, "errors": errors}

    except Exception as e:
        logger.error(f"[processCSVUpload] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# VOLUNTEER MATCHING
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/match_volunteers", tags=["matching"])
async def get_matched_volunteers(need_id: str):
    """Find top-3 matched volunteers for a need."""
    from matching_engine import match_volunteers

    need = store.get("need_reports", need_id)
    if not need:
        raise HTTPException(status_code=404, detail="Need not found")
    need["id"] = need_id

    volunteers = store.query("volunteers", filters={"status": "available"}, limit=50)
    for v in volunteers:
        v["id"] = v.get("_id", "")

    if not volunteers:
        return {"matches": [], "message": "No available volunteers"}

    top3 = match_volunteers(need, volunteers)
    return {"matches": top3, "need_id": need_id}


# ═══════════════════════════════════════════════════════════════════════════════
# VOLUNTEERS — CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/volunteers", tags=["volunteers"])
async def list_volunteers(limit: int = 50):
    """List all volunteers."""
    volunteers = store.query("volunteers", order_by="impact_points", descending=True, limit=limit)
    for v in volunteers:
        v["id"] = v.get("_id", "")
    return {"volunteers": volunteers, "total": len(volunteers)}


@app.get("/api/volunteers/{vol_id}", tags=["volunteers"])
async def get_volunteer(vol_id: str):
    vol = store.get("volunteers", vol_id)
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    vol["id"] = vol.get("_id", vol_id)
    return vol


@app.get("/api/volunteers/{vol_id}/assignments", tags=["volunteers"])
async def get_volunteer_assignments(vol_id: str):
    """Get all assignments for a specific volunteer, enriched with need details."""
    vol = store.get("volunteers", vol_id)
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found")

    all_assignments = store.query("assignments")
    vol_assignments = [a for a in all_assignments if a.get("volunteer_id") == vol_id]

    # Enrich each assignment with need report data
    enriched = []
    for a in vol_assignments:
        need_id = a.get("need_report_id")
        need = store.get("need_reports", need_id) if need_id else None
        enriched.append({
            "assignment_id": a.get("_id", ""),
            "status": a.get("status", "pending"),
            "match_score": a.get("match_score", 0),
            "match_explanation": a.get("match_explanation", ""),
            "created_at": a.get("created_at", ""),
            "need": {
                "id": need_id or "",
                "summary": (need or {}).get("summary", "No details"),
                "zone": (need or {}).get("zone", "Unknown"),
                "issue_type": (need or {}).get("issue_type", "other"),
                "urgency_score": (need or {}).get("urgency_score", 0),
                "urgency_label": (need or {}).get("urgency_label", "low"),
                "affected_count": (need or {}).get("affected_count", 0),
                "required_skills": (need or {}).get("required_skills", []),
                "lat": (need or {}).get("lat"),
                "lng": (need or {}).get("lng"),
                "status": (need or {}).get("status", "open"),
            } if need else None,
        })

    return {"assignments": enriched, "total": len(enriched)}


# ═══════════════════════════════════════════════════════════════════════════════
# ASSIGNMENTS
# ═══════════════════════════════════════════════════════════════════════════════

class AssignmentRequest(BaseModel):
    need_id: str
    volunteer_id: str
    org_id: str = "demo_org"
    match_score: Optional[float] = 0
    match_explanation: Optional[str] = ""

@app.post("/api/assignments", tags=["tasks"])
async def create_assignment(payload: AssignmentRequest):
    """Assign a volunteer to a need."""
    try:
        doc_id = store.add("assignments", {
            "need_report_id": payload.need_id,
            "volunteer_id": payload.volunteer_id,
            "org_id": payload.org_id,
            "status": "pending",
            "match_score": payload.match_score,
            "match_explanation": payload.match_explanation,
        })

        store.update("volunteers", payload.volunteer_id, {"status": "assigned"})
        store.update("need_reports", payload.need_id, {"status": "assigned"})

        return {"success": True, "assignment_id": doc_id}
    except Exception as e:
        logger.error(f"[createAssignment] {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CompleteTaskRequest(BaseModel):
    assignment_id: str
    proof_photo_url: Optional[str] = ""

@app.post("/api/complete_task", tags=["tasks"])
async def complete_task(payload: CompleteTaskRequest):
    """Mark an assignment as completed and award impact points."""
    try:
        assignment = store.get("assignments", payload.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        volunteer_id = assignment.get("volunteer_id")
        need_id = assignment.get("need_report_id")
        points_awarded = 20

        store.update("assignments", payload.assignment_id, {
            "status": "completed",
            "proof_photo_url": payload.proof_photo_url,
            "volunteer_impact_points_awarded": points_awarded,
        })

        store.update("volunteers", volunteer_id, {"status": "available"})
        store.increment("volunteers", volunteer_id, "impact_points", points_awarded)
        store.set_nested("volunteers", volunteer_id, "impact_stats.total_tasks_completed", 1)

        if need_id:
            need = store.get("need_reports", need_id)
            if need:
                affected = need.get("affected_count", 0) or 0
                store.set_nested("volunteers", volunteer_id, "impact_stats.total_people_helped", affected)
                store.update("need_reports", need_id, {"status": "resolved"})

        vol = store.get("volunteers", volunteer_id) or {}

        # Generate impact framing
        from gemini_client import generate_impact_framing
        impact_framing = generate_impact_framing(
            issue_type=assignment.get("issue_type", "general"),
            affected_count=assignment.get("affected_count", 0),
            location=assignment.get("zone", "your area"),
            required_skills=assignment.get("required_skills", []),
        )

        scorecard = {
            "points_earned": points_awarded,
            "total_points": vol.get("impact_points", 0),
            "total_tasks": vol.get("impact_stats", {}).get("total_tasks_completed", 0),
            "total_people_helped": vol.get("impact_stats", {}).get("total_people_helped", 0),
            "impact_message": impact_framing,
        }

        return {"success": True, "scorecard": scorecard}

    except Exception as e:
        logger.error(f"[completeTask] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# URGENCY FLAGGING
# ═══════════════════════════════════════════════════════════════════════════════

class FlagScoreRequest(BaseModel):
    need_id: str
    correct_score: int
    reason: Optional[str] = ""
    flagged_by: Optional[str] = "coordinator"

@app.post("/api/flag_urgency_score", tags=["needs"])
async def flag_urgency_score(payload: FlagScoreRequest):
    """Human-in-the-loop: coordinator overrides AI urgency score."""
    try:
        store.add("urgency_corrections", {
            "need_id": payload.need_id,
            "corrected_score": payload.correct_score,
            "reason": payload.reason,
            "flagged_by": payload.flagged_by,
        })

        score = payload.correct_score
        label = "critical" if score >= 86 else ("high" if score >= 61 else ("medium" if score >= 31 else "low"))

        store.update("need_reports", payload.need_id, {
            "urgency_score": score,
            "urgency_label": label,
            "status": "flagged",
            "flagged_by": payload.flagged_by,
            "flag_reason": payload.reason,
        })

        return {"success": True, "new_score": score, "new_label": label}

    except Exception as e:
        logger.error(f"[flagUrgencyScore] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/analytics", tags=["analytics"])
async def get_analytics():
    """Dashboard analytics data for Chart.js."""
    needs = store.list_all("need_reports")
    volunteers = store.list_all("volunteers")

    # Urgency distribution
    urgency_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for n in needs:
        label = n.get("urgency_label", "low")
        if label in urgency_dist:
            urgency_dist[label] += 1

    # Issue type distribution
    issue_dist = {}
    for n in needs:
        itype = n.get("issue_type", "other")
        issue_dist[itype] = issue_dist.get(itype, 0) + 1

    # Zone distribution
    zone_dist = {}
    for n in needs:
        zone = n.get("zone", "Unknown")
        zone_dist[zone] = zone_dist.get(zone, 0) + 1

    # Status distribution
    status_dist = {}
    for n in needs:
        status = n.get("status", "open")
        status_dist[status] = status_dist.get(status, 0) + 1

    # Volunteer stats
    vol_available = len([v for v in volunteers if v.get("status") == "available"])
    vol_assigned = len([v for v in volunteers if v.get("status") == "assigned"])
    total_people_helped = sum(v.get("impact_stats", {}).get("total_people_helped", 0) for v in volunteers)
    total_tasks_completed = sum(v.get("impact_stats", {}).get("total_tasks_completed", 0) for v in volunteers)

    # Source distribution
    source_dist = {}
    for n in needs:
        src = n.get("source", "unknown")
        source_dist[src] = source_dist.get(src, 0) + 1

    return {
        "urgency_distribution": urgency_dist,
        "issue_type_distribution": issue_dist,
        "zone_distribution": zone_dist,
        "status_distribution": status_dist,
        "source_distribution": source_dist,
        "volunteer_stats": {
            "total": len(volunteers),
            "available": vol_available,
            "assigned": vol_assigned,
            "total_people_helped": total_people_helped,
            "total_tasks_completed": total_tasks_completed,
        },
        "totals": {
            "needs": len(needs),
            "volunteers": len(volunteers),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC FILE SERVING (Frontend)
# ═══════════════════════════════════════════════════════════════════════════════

FRONTEND_DIR = Path(__file__).parent / "public"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = Path(__file__).parent.parent / "public"

@app.get("/", tags=["frontend"])
async def serve_index():
    """Serve the main dashboard."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "AlloCare API is running. Frontend not found at /public/"}


# Mount static file directories
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    if (FRONTEND_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

# Serve root-level static files (sw.js, manifest.json)
@app.get("/sw.js", tags=["frontend"])
async def serve_sw():
    sw_file = FRONTEND_DIR / "sw.js"
    if sw_file.exists():
        return FileResponse(sw_file, media_type="application/javascript")
    return JSONResponse(status_code=404, content={"error": "sw.js not found"})

@app.get("/manifest.json", tags=["frontend"])
async def serve_manifest():
    mf = FRONTEND_DIR / "manifest.json"
    if mf.exists():
        return FileResponse(mf, media_type="application/json")
    return JSONResponse(status_code=404, content={"error": "manifest.json not found"})


# ═══════════════════════════════════════════════════════════════════════════════
# FIREBASE EXPORT (only when deployed to Firebase)
# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING & NEARBY VOLUNTEERS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/route")
async def get_route_api(
    from_lat: float = Query(...), from_lng: float = Query(...),
    to_lat: float = Query(...), to_lng: float = Query(...),
    profile: str = Query("driving")
):
    """Get route between two points using OSRM (free, no API key)."""
    try:
        from routing_client import get_route
        route = get_route(from_lat, from_lng, to_lat, to_lng, profile)
        return route
    except Exception as e:
        logger.error(f"Route error: {e}")
        return {"distance_km": 0, "duration_min": 0, "polyline": [], "source": "error"}


@app.get("/api/nearby_volunteers")
async def nearby_volunteers_api(
    lat: float = Query(...), lng: float = Query(...),
    radius_km: float = Query(50)
):
    """Find all volunteers near a location, sorted by distance."""
    import math
    volunteers = store.list_all("volunteers")
    results = []
    for v in volunteers:
        if not v.get("lat") or not v.get("lng"):
            continue
        # Haversine distance
        R = 6371.0
        phi1, phi2 = math.radians(lat), math.radians(v["lat"])
        dphi = math.radians(v["lat"] - lat)
        dlam = math.radians(v["lng"] - lng)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        if dist <= radius_km:
            road_dist = round(dist * 1.4, 1)
            results.append({
                "id": v.get("id") or v.get("_id", ""),
                "display_name": v.get("display_name", ""),
                "lat": v["lat"], "lng": v["lng"],
                "zone": v.get("zone", ""),
                "skills": v.get("skills", []),
                "status": v.get("status", "available"),
                "distance_km": round(dist, 1),
                "road_distance_km": road_dist,
                "impact_points": v.get("impact_points", 0),
            })
    results.sort(key=lambda x: x["distance_km"])
    return {"volunteers": results, "total": len(results)}


# ═══════════════════════════════════════════════════════════════════════════════
# SMS GATEWAY (Offline fallback)
# ═══════════════════════════════════════════════════════════════════════════════

class SMSReport(BaseModel):
    sender: str
    message: str

@app.post("/api/sms/receive")
async def receive_sms(report: SMSReport):
    """Parse an incoming SMS into a need report. Format: NEED <location> <type> <description>"""
    msg = report.message.strip()
    if not msg.upper().startswith("NEED"):
        return {"status": "ignored", "message": "SMS must start with NEED keyword"}
    
    parts = msg.split(None, 3)  # NEED <location> <type> <description>
    location = parts[1] if len(parts) > 1 else "Unknown"
    issue_type = parts[2].lower() if len(parts) > 2 else "other"
    description = parts[3] if len(parts) > 3 else msg
    
    valid_types = ["food", "water", "health", "housing", "education", "safety"]
    if issue_type not in valid_types:
        description = (issue_type + " " + description).strip()
        issue_type = "other"
    
    # Process as a regular report
    report_data = {
        "raw_text": description,
        "source": "sms",
        "sender": report.sender,
        "zone": location,
    }
    
    try:
        result = process_report(report_data["raw_text"], "sms")
        return {"status": "processed", "need_id": result.get("id", ""), "message": f"Report from {location} logged"}
    except Exception as e:
        # Fallback: save raw
        need = {
            "zone": location, "issue_type": issue_type,
            "summary": description[:200], "severity_score": 5,
            "urgency_score": 50, "urgency_label": "medium",
            "status": "open", "source": "sms",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        store.add("need_reports", need)
        return {"status": "saved_raw", "message": f"Saved SMS report from {report.sender}"}


if DEPLOYMENT == "firebase":
    wsgi_app = ASGIMiddleware(app)

    @https_fn.on_request(max_instances=1)
    def api(req: https_fn.Request) -> https_fn.Response:
        return https_fn.Response.from_wsgi(wsgi_app, req.environ)


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP (Local)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"\n>>> AlloCare API starting on http://localhost:{port}")
    print(f"    Swagger docs: http://localhost:{port}/docs")
    print(f"    Dashboard:    http://localhost:{port}/")
    gemini_configured = "YES" if os.environ.get("GEMINI_API_KEY") else "NO (add GEMINI_API_KEY to .env)"
    print(f"    Gemini API Key: {gemini_configured}\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
