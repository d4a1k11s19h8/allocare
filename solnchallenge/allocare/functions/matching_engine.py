"""
matching_engine.py — AlloCare Volunteer Matching Algorithm
match_score = skill_overlap_score × proximity_score × availability_score
Returns top-3 ranked matches with explainability strings.
"""
import os
import math
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

MAPS_API_KEY = os.environ.get("MAPS_API_KEY", "")
DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


def match_volunteers(need: dict, volunteers: list[dict]) -> list[dict]:
    """
    Scores all available volunteers against a need and returns top-3.

    Args:
        need: need_report dict with keys: lat, lng, required_skills, zone
        volunteers: list of volunteer dicts from Firestore

    Returns:
        List of up to 3 dicts: {volunteer_id, name, score, explanation, distance_km, skills_matched}
    """
    need_lat = need.get("lat")
    need_lng = need.get("lng")
    required_skills = need.get("required_skills", [])

    if not volunteers:
        return []

    # ── Batch Distance Matrix API call ────────────────────────────────────────
    # Max 25 origins per call
    distance_map = {}
    vol_with_location = [v for v in volunteers if v.get("lat") and v.get("lng")]

    if vol_with_location and need_lat and need_lng:
        for batch_start in range(0, len(vol_with_location), 25):
            batch = vol_with_location[batch_start:batch_start + 25]
            origins = "|".join([f"{v['lat']},{v['lng']}" for v in batch])
            destination = f"{need_lat},{need_lng}"

            try:
                resp = requests.get(DISTANCE_MATRIX_URL, params={
                    "origins": origins,
                    "destinations": destination,
                    "mode": "driving",
                    "units": "metric",
                    "key": MAPS_API_KEY,
                }, timeout=8)
                data = resp.json()

                if data.get("status") == "OK":
                    rows = data.get("rows", [])
                    for i, row in enumerate(rows):
                        elements = row.get("elements", [])
                        if elements and elements[0].get("status") == "OK":
                            dist_m = elements[0]["distance"]["value"]
                            distance_map[batch[i]["id"]] = dist_m / 1000.0  # km
                        else:
                            # Fallback: Haversine straight-line distance
                            distance_map[batch[i]["id"]] = _haversine(
                                batch[i]["lat"], batch[i]["lng"], need_lat, need_lng
                            )
                else:
                    # Fallback for entire batch
                    for v in batch:
                        distance_map[v["id"]] = _haversine(v["lat"], v["lng"], need_lat, need_lng)

            except Exception as e:
                logger.warning(f"[match_volunteers] Distance Matrix error: {e}. Using Haversine.")
                for v in batch:
                    distance_map[v["id"]] = _haversine(v["lat"], v["lng"], need_lat, need_lng)

    # ── Score each volunteer ──────────────────────────────────────────────────
    now = datetime.utcnow()
    candidates = []

    for v in volunteers:
        vol_id = v.get("id", "")
        max_dist = v.get("max_distance_km", 10)
        dist_km = distance_map.get(vol_id)

        # If no location data, use zone matching (1 = same zone, 5 = different zone)
        if dist_km is None:
            dist_km = 1.0 if v.get("zone", "").lower() == need.get("zone", "").lower() else 5.0

        # Hard cutoff: volunteer's max travel distance
        if dist_km > max_dist:
            continue

        # 1. Skill overlap score [0, 1]
        vol_skills = [s.lower() for s in v.get("skills", [])]
        req_skills = [s.lower() for s in required_skills] if required_skills else []

        if req_skills:
            matched_skills = [s for s in req_skills if any(s in vs or vs in s for vs in vol_skills)]
            skill_score = len(matched_skills) / len(req_skills)
        else:
            matched_skills = []
            skill_score = 0.5  # No specific skills required — partial credit

        # 2. Proximity score [0, 1] — decays with distance
        proximity_score = 1.0 / (1.0 + dist_km)

        # 3. Availability score [0, 1]
        avail_score = _calculate_availability_score(v, now)

        # Composite match score
        match_score = skill_score * proximity_score * avail_score

        # Build explainability string
        explanation = _build_explanation(v, need, matched_skills, req_skills, dist_km, avail_score)

        candidates.append({
            "volunteer_id": vol_id,
            "volunteer_name": v.get("display_name", "Volunteer"),
            "email": v.get("email", ""),
            "skills": v.get("skills", []),
            "skills_matched": matched_skills,
            "distance_km": round(dist_km, 1),
            "match_score": round(match_score, 4),
            "skill_score": round(skill_score, 2),
            "proximity_score": round(proximity_score, 2),
            "availability_score": round(avail_score, 2),
            "explanation": explanation,
            "status": v.get("status", "available"),
            "impact_points": v.get("impact_points", 0),
        })

    # Sort by match_score descending, return top 3
    candidates.sort(key=lambda x: x["match_score"], reverse=True)
    return candidates[:3]


def _calculate_availability_score(volunteer: dict, now: datetime) -> float:
    """Returns 1.0 if available now, 0.3 if not (based on availability grid)."""
    if volunteer.get("status") != "available":
        return 0.0

    availability = volunteer.get("availability", {})
    if not availability:
        return 0.7  # Unknown availability — partial credit

    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_key = day_names[now.weekday()]
    hour = now.hour

    if hour < 12:
        slot = f"{day_key}_am"
    elif hour < 17:
        slot = f"{day_key}_pm"
    else:
        slot = f"{day_key}_eve"

    return 1.0 if availability.get(slot, False) else 0.3


def _build_explanation(
    volunteer: dict,
    need: dict,
    matched_skills: list,
    required_skills: list,
    dist_km: float,
    avail_score: float,
) -> str:
    """Builds a human-readable explanation for the match."""
    parts = []

    if matched_skills:
        parts.append(f"{', '.join(matched_skills)} skill{'s' if len(matched_skills) > 1 else ''} ✓")
    elif not required_skills:
        parts.append("No specific skills required ✓")
    else:
        parts.append(f"Partial skill match ({len(matched_skills)}/{len(required_skills)} required skills)")

    parts.append(f"{dist_km:.1f}km away ✓" if dist_km <= volunteer.get("max_distance_km", 10) else f"{dist_km:.1f}km away")

    if avail_score >= 1.0:
        parts.append("Available now ✓")
    elif avail_score > 0.0:
        parts.append("Availability unconfirmed")

    return "Matched because: " + " · ".join(parts)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculates straight-line distance between two lat/lng points in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
