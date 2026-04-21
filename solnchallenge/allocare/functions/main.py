import os
import json
import math
import logging
from datetime import datetime, timezone
from firebase_functions import firestore_fn, https_fn, options, scheduler_fn
from firebase_admin import initialize_app, firestore, credentials
from google.cloud.firestore_v1.base_query import FieldFilter

# ── initialise ─────────────────────────────────────────────────────────────────
initialize_app()
db = firestore.client()
logger = logging.getLogger(__name__)

# ── import helpers ─────────────────────────────────────────────────────────────
from gemini_client import extract_urgency, generate_coordinator_explanation, generate_impact_framing
from urgency_scorer import calculate_urgency_score
from matching_engine import match_volunteers


# ═══════════════════════════════════════════════════════════════════════════════
# TRIGGER 1 — onReportCreated
# Fires every time a new document lands in need_reports collection.
# Pipeline: OCR → Translate → Gemini extraction → Geocode → Score → Notify
# ═══════════════════════════════════════════════════════════════════════════════
@firestore_fn.on_document_created(document="need_reports/{reportId}", region="asia-south1")
def on_report_created(event: firestore_fn.Event[firestore_fn.DocumentSnapshot]) -> None:
    report_id = event.params["reportId"]
    data = event.data.to_dict()
    logger.info(f"[onReportCreated] Processing report {report_id}")

    try:
        raw_text = data.get("raw_text", "")
        image_url = data.get("image_url")
        org_id = data.get("org_id", "")

        # Step 1 — OCR (if image uploaded)
        if image_url and not raw_text:
            from vision_client import extract_text_from_image
            raw_text = extract_text_from_image(image_url)
            if not raw_text:
                _flag_report(report_id, "OCR returned empty text")
                return

        if not raw_text:
            _flag_report(report_id, "No text or image provided")
            return

        # Step 2 — Language detection + translation
        from translate_client import detect_and_translate
        english_text, detected_lang = detect_and_translate(raw_text)

        # Step 3 — Gemini extraction
        extracted = extract_urgency(english_text)
        if not extracted:
            _flag_report(report_id, "Gemini extraction failed")
            return

        # Step 4 — Geocoding
        from maps_client import geocode_location
        location_text = extracted.get("location_text", "") + ", India"
        geo = geocode_location(location_text)

        # Step 5 — Frequency count (same zone + issue_type in last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        freq_query = (
            db.collection("need_reports")
            .where(filter=FieldFilter("zone", "==", extracted.get("location_text", "")))
            .where(filter=FieldFilter("issue_type", "==", extracted.get("issue_type", "other")))
            .where(filter=FieldFilter("created_at", ">=", thirty_days_ago))
            .count()
        )
        freq_result = freq_query.get()
        frequency = freq_result[0][0].value if freq_result else 1

        # Step 6 — Urgency scoring
        days_since = (datetime.now(timezone.utc) - data.get("created_at", datetime.now(timezone.utc))).days
        score_data = calculate_urgency_score(
            severity=extracted.get("severity_score", 5),
            frequency=frequency,
            days_since_first_report=max(1, days_since)
        )

        # Step 7 — Coordinator explanation (Gemini Prompt 2)
        explanation = generate_coordinator_explanation(
            issue_type=extracted.get("issue_type", "other"),
            severity=extracted.get("severity_score", 5),
            affected_count=extracted.get("affected_count"),
            location=extracted.get("location_text", ""),
            frequency=frequency,
            days=max(1, days_since)
        )

        # Step 8 — Write all processed fields back to Firestore
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
            "processed_at": firestore.SERVER_TIMESTAMP,
            "status": "open",
            "trend_direction": "stable",
        }

        if geo:
            update_payload["lat"] = geo["lat"]
            update_payload["lng"] = geo["lng"]

        db.collection("need_reports").document(report_id).update(update_payload)
        logger.info(f"[onReportCreated] Report {report_id} processed. Score={score_data['score']} ({score_data['label']})")

        # Step 9 — Push notifications if urgency >= 70
        if score_data["score"] >= 70:
            _notify_nearby_volunteers(
                zone=extracted.get("location_text", ""),
                skills=extracted.get("required_skills", []),
                need_id=report_id,
                summary=extracted.get("summary", ""),
                urgency_score=score_data["score"],
                lat=geo.get("lat") if geo else None,
                lng=geo.get("lng") if geo else None,
            )

    except Exception as e:
        logger.error(f"[onReportCreated] Failed for {report_id}: {e}", exc_info=True)
        _flag_report(report_id, f"Processing error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2 — processCSVUpload
# HTTP POST: multipart form with CSV file
# Returns: { imported: N, errors: [{row, reason}] }
# ═══════════════════════════════════════════════════════════════════════════════
@https_fn.on_request(region="asia-south1", cors=options.CorsOptions(cors_origins="*", cors_methods=["POST"]))
def process_csv_upload(req: https_fn.Request) -> https_fn.Response:
    if req.method != "POST":
        return https_fn.Response("Method not allowed", status=405)

    try:
        import pandas as pd
        import io

        file = req.files.get("file")
        org_id = req.form.get("org_id", "demo_org")
        if not file:
            return https_fn.Response(json.dumps({"error": "No file uploaded"}), status=400,
                                     mimetype="application/json")

        content = file.read()
        df = pd.read_csv(io.BytesIO(content))

        # Normalize columns to internal schema
        column_map = {
            "location": "zone", "area": "zone", "place": "zone",
            "problem": "raw_text", "description": "raw_text", "issue": "raw_text",
            "people": "affected_count", "households": "affected_count",
            "severity": "severity_score", "priority": "severity_score",
        }
        df.rename(columns={k: v for k, v in column_map.items() if k in df.columns}, inplace=True)

        imported = 0
        errors = []
        batch = db.batch()
        batch_count = 0

        for idx, row in df.iterrows():
            try:
                raw_text = str(row.get("raw_text", row.get("zone", "Unknown issue")))
                zone = str(row.get("zone", "Unknown"))
                doc_ref = db.collection("need_reports").document()
                batch.set(doc_ref, {
                    "org_id": org_id,
                    "raw_text": raw_text,
                    "zone": zone,
                    "source": "csv",
                    "status": "open",
                    "severity_score": int(row.get("severity_score", 5)),
                    "affected_count": int(row.get("affected_count", 0)) if row.get("affected_count") else None,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "urgency_score": 0,
                    "urgency_label": "low",
                })
                batch_count += 1
                imported += 1

                # Commit in batches of 500
                if batch_count >= 490:
                    batch.commit()
                    batch = db.batch()
                    batch_count = 0

            except Exception as row_err:
                errors.append({"row": idx + 2, "reason": str(row_err)})

        if batch_count > 0:
            batch.commit()

        return https_fn.Response(
            json.dumps({"imported": imported, "errors": errors}),
            status=200, mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"[processCSVUpload] {e}", exc_info=True)
        return https_fn.Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3 — getMatchedVolunteers
# HTTP GET ?need_id=<id>
# Returns top-3 matched volunteers with explanation strings
# ═══════════════════════════════════════════════════════════════════════════════
@https_fn.on_request(region="asia-south1", cors=options.CorsOptions(cors_origins="*", cors_methods=["GET"]))
def get_matched_volunteers(req: https_fn.Request) -> https_fn.Response:
    if req.method != "GET":
        return https_fn.Response("Method not allowed", status=405)

    need_id = req.args.get("need_id")
    if not need_id:
        return https_fn.Response(json.dumps({"error": "need_id required"}), status=400,
                                 mimetype="application/json")

    try:
        need_doc = db.collection("need_reports").document(need_id).get()
        if not need_doc.exists:
            return https_fn.Response(json.dumps({"error": "Need not found"}), status=404,
                                     mimetype="application/json")

        need = need_doc.to_dict()
        need["id"] = need_id

        # Fetch available volunteers
        volunteers_query = (
            db.collection("volunteers")
            .where(filter=FieldFilter("status", "==", "available"))
            .limit(50)
        )
        volunteers = [{"id": v.id, **v.to_dict()} for v in volunteers_query.stream()]

        if not volunteers:
            return https_fn.Response(json.dumps({"matches": [], "message": "No available volunteers"}),
                                     status=200, mimetype="application/json")

        top3 = match_volunteers(need, volunteers)

        return https_fn.Response(
            json.dumps({"matches": top3, "need_id": need_id}),
            status=200, mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"[getMatchedVolunteers] {e}", exc_info=True)
        return https_fn.Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4 — flagUrgencyScore
# HTTP POST: { need_id, correct_score, reason }
# ═══════════════════════════════════════════════════════════════════════════════
@https_fn.on_request(region="asia-south1", cors=options.CorsOptions(cors_origins="*", cors_methods=["POST"]))
def flag_urgency_score(req: https_fn.Request) -> https_fn.Response:
    if req.method != "POST":
        return https_fn.Response("Method not allowed", status=405)

    try:
        body = req.get_json(silent=True) or {}
        need_id = body.get("need_id")
        correct_score = body.get("correct_score")
        reason = body.get("reason", "")
        flagged_by = body.get("flagged_by", "coordinator")

        if not need_id or correct_score is None:
            return https_fn.Response(json.dumps({"error": "need_id and correct_score required"}),
                                     status=400, mimetype="application/json")

        # Log correction
        db.collection("urgency_corrections").add({
            "need_id": need_id,
            "corrected_score": int(correct_score),
            "reason": reason,
            "flagged_by": flagged_by,
            "flagged_at": firestore.SERVER_TIMESTAMP,
        })

        # Update report with override
        score = int(correct_score)
        if score >= 86:
            label = "critical"
        elif score >= 61:
            label = "high"
        elif score >= 31:
            label = "medium"
        else:
            label = "low"

        db.collection("need_reports").document(need_id).update({
            "urgency_score": score,
            "urgency_label": label,
            "status": "flagged",
            "flagged_by": flagged_by,
            "flag_reason": reason,
        })

        return https_fn.Response(json.dumps({"success": True, "new_score": score, "new_label": label}),
                                 status=200, mimetype="application/json")

    except Exception as e:
        logger.error(f"[flagUrgencyScore] {e}", exc_info=True)
        return https_fn.Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 5 — completeTask
# HTTP POST: { assignment_id, proof_photo_url }
# ═══════════════════════════════════════════════════════════════════════════════
@https_fn.on_request(region="asia-south1", cors=options.CorsOptions(cors_origins="*", cors_methods=["POST"]))
def complete_task(req: https_fn.Request) -> https_fn.Response:
    if req.method != "POST":
        return https_fn.Response("Method not allowed", status=405)

    try:
        body = req.get_json(silent=True) or {}
        assignment_id = body.get("assignment_id")
        proof_url = body.get("proof_photo_url", "")

        if not assignment_id:
            return https_fn.Response(json.dumps({"error": "assignment_id required"}),
                                     status=400, mimetype="application/json")

        assignment_ref = db.collection("assignments").document(assignment_id)
        assignment = assignment_ref.get()
        if not assignment.exists:
            return https_fn.Response(json.dumps({"error": "Assignment not found"}), status=404,
                                     mimetype="application/json")

        data = assignment.to_dict()
        volunteer_id = data.get("volunteer_id")
        need_id = data.get("need_report_id")
        points_awarded = 20  # base

        # Update assignment
        assignment_ref.update({
            "status": "completed",
            "completed_at": firestore.SERVER_TIMESTAMP,
            "proof_photo_url": proof_url,
            "volunteer_impact_points_awarded": points_awarded,
        })

        # Update volunteer stats
        volunteer_ref = db.collection("volunteers").document(volunteer_id)
        volunteer_ref.update({
            "status": "available",
            "impact_points": firestore.Increment(points_awarded),
            "impact_stats.total_tasks_completed": firestore.Increment(1),
        })

        # Update need report
        if need_id:
            need_ref = db.collection("need_reports").document(need_id)
            need_doc = need_ref.get()
            if need_doc.exists:
                need_data = need_doc.to_dict()
                affected = need_data.get("affected_count", 0) or 0
                volunteer_ref.update({
                    "impact_stats.total_people_helped": firestore.Increment(affected),
                })
                need_ref.update({"status": "resolved", "resolved_at": firestore.SERVER_TIMESTAMP})

        # Generate impact scorecard data
        vol_doc = volunteer_ref.get().to_dict()
        impact_framing = generate_impact_framing(
            issue_type=data.get("issue_type", "general"),
            affected_count=data.get("affected_count", 0),
            location=data.get("zone", "your area"),
            required_skills=data.get("required_skills", [])
        ) if volunteer_id else ""

        scorecard = {
            "points_earned": points_awarded,
            "total_points": vol_doc.get("impact_points", 0),
            "total_tasks": vol_doc.get("impact_stats", {}).get("total_tasks_completed", 0),
            "total_people_helped": vol_doc.get("impact_stats", {}).get("total_people_helped", 0),
            "impact_message": impact_framing,
        }

        return https_fn.Response(json.dumps({"success": True, "scorecard": scorecard}),
                                 status=200, mimetype="application/json")

    except Exception as e:
        logger.error(f"[completeTask] {e}", exc_info=True)
        return https_fn.Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 6 — whatsappWebhook
# HTTP POST: Twilio webhook body
# ═══════════════════════════════════════════════════════════════════════════════
@https_fn.on_request(region="asia-south1", cors=options.CorsOptions(cors_origins="*", cors_methods=["POST"]))
def whatsapp_webhook(req: https_fn.Request) -> https_fn.Response:
    try:
        from_number = req.form.get("From", "").replace("whatsapp:", "")
        body_text = req.form.get("Body", "")

        if not body_text:
            return https_fn.Response("OK", status=200)

        # Look up org by sender number
        org_query = (
            db.collection("organizations")
            .where(filter=FieldFilter("whatsapp_number", "==", from_number))
            .limit(1)
        )
        orgs = list(org_query.stream())
        org_id = orgs[0].id if orgs else "unknown_org"

        # Create need_report doc — onReportCreated will process it
        db.collection("need_reports").add({
            "org_id": org_id,
            "raw_text": body_text,
            "source": "whatsapp",
            "whatsapp_sender": from_number,
            "status": "open",
            "urgency_score": 0,
            "urgency_label": "low",
            "created_at": firestore.SERVER_TIMESTAMP,
        })

        return https_fn.Response(
            '<?xml version="1.0" encoding="UTF-8"?><Response><Message>✅ Report received. Our team will process it shortly.</Message></Response>',
            status=200, mimetype="text/xml"
        )

    except Exception as e:
        logger.error(f"[whatsappWebhook] {e}", exc_info=True)
        return https_fn.Response("Error", status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 7 — createAssignment (coordinator assigns volunteer to need)
# HTTP POST: { need_id, volunteer_id, org_id }
# ═══════════════════════════════════════════════════════════════════════════════
@https_fn.on_request(region="asia-south1", cors=options.CorsOptions(cors_origins="*", cors_methods=["POST"]))
def create_assignment(req: https_fn.Request) -> https_fn.Response:
    if req.method != "POST":
        return https_fn.Response("Method not allowed", status=405)
    try:
        body = req.get_json(silent=True) or {}
        need_id = body.get("need_id")
        volunteer_id = body.get("volunteer_id")
        org_id = body.get("org_id")
        match_score = body.get("match_score", 0)
        match_explanation = body.get("match_explanation", "")

        if not all([need_id, volunteer_id, org_id]):
            return https_fn.Response(json.dumps({"error": "need_id, volunteer_id, org_id required"}),
                                     status=400, mimetype="application/json")

        doc_ref = db.collection("assignments").document()
        doc_ref.set({
            "assignment_id": doc_ref.id,
            "need_report_id": need_id,
            "volunteer_id": volunteer_id,
            "org_id": org_id,
            "status": "pending",
            "match_score": match_score,
            "match_explanation": match_explanation,
            "assigned_at": firestore.SERVER_TIMESTAMP,
        })

        # Mark volunteer as assigned
        db.collection("volunteers").document(volunteer_id).update({"status": "assigned"})
        # Mark need as assigned
        db.collection("need_reports").document(need_id).update({"status": "assigned"})

        return https_fn.Response(json.dumps({"success": True, "assignment_id": doc_ref.id}),
                                 status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"[createAssignment] {e}", exc_info=True)
        return https_fn.Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED — scheduledTrendUpdate (runs daily)
# ═══════════════════════════════════════════════════════════════════════════════
@scheduler_fn.on_schedule(schedule="every 24 hours", region="asia-south1")
def scheduled_trend_update(event: scheduler_fn.ScheduledEvent) -> None:
    from datetime import timedelta
    from urgency_scorer import detect_trend

    logger.info("[scheduledTrendUpdate] Running daily trend detection")
    zones_query = db.collection("zone_stats").stream()
    zones = [z.id for z in zones_query]

    for zone in zones:
        for issue_type in ["food", "water", "health", "housing", "education", "safety", "other"]:
            trend, label = detect_trend(db, zone, issue_type)
            db.collection("zone_stats").document(f"{zone}_{issue_type}").set({
                "zone": zone,
                "issue_type": issue_type,
                "trend_direction": trend,
                "trend_label": label,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }, merge=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _flag_report(report_id: str, reason: str) -> None:
    db.collection("need_reports").document(report_id).update({
        "status": "flagged",
        "flag_reason": reason,
        "processed_at": firestore.SERVER_TIMESTAMP,
    })
    logger.warning(f"[_flag_report] Report {report_id} flagged: {reason}")


def _notify_nearby_volunteers(zone, skills, need_id, summary, urgency_score, lat, lng):
    """Send FCM push to topic: volunteers_{zone}_{skill}"""
    try:
        from firebase_admin import messaging
        for skill in (skills or ["general"]):
            topic = f"volunteers_{zone.replace(' ', '_').lower()}_{skill.replace(' ', '_').lower()}"
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f"🚨 CRITICAL Need Near You",
                    body=f"{summary[:100]} — {zone}",
                ),
                data={
                    "need_id": need_id,
                    "urgency_score": str(urgency_score),
                    "lat": str(lat or ""),
                    "lng": str(lng or ""),
                    "type": "critical_need",
                },
                topic=topic,
                android=messaging.AndroidConfig(priority="high"),
            )
            messaging.send(message)
            logger.info(f"[FCM] Sent to topic {topic}")
    except Exception as e:
        logger.error(f"[_notify_nearby_volunteers] FCM error: {e}")
