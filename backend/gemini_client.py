"""
gemini_client.py — Gemini 2.0 Flash integration for AlloCare
All three prompt templates from the masterplan implemented here.
Gracefully degrades when GEMINI_API_KEY is not set.
"""
import os
import json
import logging
import re

logger = logging.getLogger(__name__)

# ── Lazy initialisation — avoids crash when key is absent ─────────────────────
_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_models_initialised = False
_MODEL = None
_EXPLAIN_MODEL = None
_IMPACT_MODEL = None


def _init_models():
    """Lazy init: create model objects only when first needed."""
    global _models_initialised, _MODEL, _EXPLAIN_MODEL, _IMPACT_MODEL
    if _models_initialised:
        return _API_KEY != ""
    _models_initialised = True

    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        logger.warning("[gemini_client] No GEMINI_API_KEY set — using fallback responses.")
        return False

    try:
        import google.generativeai as genai
        genai.configure(api_key=key)

        _MODEL = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
            system_instruction=(
                "You are a humanitarian field analyst for Indian NGOs. "
                "Extract structured data from community field reports. "
                "Always return ONLY valid JSON with exactly the fields requested. "
                "No markdown, no explanation, no preamble."
            ),
        )

        _EXPLAIN_MODEL = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.4,
                max_output_tokens=300,
            ),
            system_instruction=(
                "You are Dr. Priya Sharma, a compassionate humanitarian coordinator explaining "
                "community needs to volunteer coordinators. Be direct, empathetic, and specific. "
                "Maximum 120 words. No bullet points. One paragraph."
            ),
        )

        _IMPACT_MODEL = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.5,
                max_output_tokens=80,
            ),
            system_instruction=(
                "You write motivating impact statements for volunteers (max 25 words). "
                "Focus on the human impact. Use present tense. Be specific not generic."
            ),
        )
        logger.info("[gemini_client] Gemini models initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"[gemini_client] Failed to init Gemini: {e}")
        return False


def _sanitize_json(raw: str) -> str:
    """Strip markdown fences and other wrappers from Gemini output."""
    text = raw.strip()
    # Remove ```json ... ``` wrappers
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


# ── Prompt 1: Urgency Extraction ─────────────────────────────────────────────
def extract_urgency(raw_text: str) -> dict | None:
    """
    Takes raw field report text (English), returns structured urgency data.
    Returns None on failure, or uses rule-based fallback if Gemini unavailable.
    """
    if not _init_models() or not _MODEL:
        return _fallback_extract(raw_text)

    prompt = f"""Extract urgency data from this field report:

"{raw_text}"

Return JSON with exactly these fields:
{{
  "issue_type": "one of: food, water, health, housing, education, safety, other",
  "location_text": "extracted location name or address in India",
  "severity_score": "integer 1-10 (1=minor inconvenience, 10=life-threatening)",
  "affected_count": "estimated integer number of people affected, or null if unknown",
  "summary": "one sentence plain English summary of the need",
  "required_skills": ["array", "of", "skill", "strings"],
  "recommended_volunteer_count": "integer 1-10",
  "language_detected": "ISO 639-1 code of original language before translation"
}}"""

    for attempt in range(3):
        try:
            response = _MODEL.generate_content(prompt)
            cleaned = _sanitize_json(response.text)
            result = json.loads(cleaned)

            # Validate and clamp
            valid_types = {"food", "water", "health", "housing", "education", "safety", "other"}
            if result.get("issue_type") not in valid_types:
                result["issue_type"] = "other"
            result["severity_score"] = max(1, min(10, int(result.get("severity_score", 5))))
            result["recommended_volunteer_count"] = max(1, min(10, int(result.get("recommended_volunteer_count", 2))))
            if result.get("affected_count"):
                result["affected_count"] = max(1, int(result["affected_count"]))
            if not isinstance(result.get("required_skills"), list):
                result["required_skills"] = ["general volunteering"]

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"[extract_urgency] Attempt {attempt+1} JSON parse error: {e}")
            if attempt == 2:
                return _fallback_extract(raw_text)
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                import time
                time.sleep(2 ** attempt)
                continue
            logger.error(f"[extract_urgency] Gemini error: {e}")
            return _fallback_extract(raw_text)

    return _fallback_extract(raw_text)


def _fallback_extract(text: str) -> dict:
    """Rule-based extraction when Gemini is unavailable."""
    text_lower = text.lower()

    # Issue type detection — earthquake/flood/cyclone map to safety or housing
    issue_map = {
        "food": ["food", "hunger", "meal", "ration", "starv", "eat"],
        "water": ["water", "drinking", "pipeline", "tanker", "thirst", "tap", "flood", "flooding"],
        "health": ["health", "medical", "doctor", "dengue", "hospital", "sick", "disease", "medicine",
                    "injury", "injured", "casualties", "epidemic"],
        "housing": ["housing", "shelter", "fire", "displaced", "roof", "building", "construction",
                     "earthquake", "collapsed", "damage", "cyclone", "tornado", "landslide"],
        "education": ["education", "school", "student", "teacher", "textbook", "learn"],
        "safety": ["safety", "child labor", "crime", "danger", "theft", "violence", "women",
                    "rescue", "evacuation", "disaster", "emergency relief"],
    }
    issue_type = "other"
    for itype, keywords in issue_map.items():
        if any(kw in text_lower for kw in keywords):
            issue_type = itype
            break

    # Estimate severity from keywords
    severity = 5
    if any(w in text_lower for w in ["critical", "urgent", "emergency", "life-threatening", "hospitalized",
                                      "earthquake", "collapsed", "casualties", "disaster", "cyclone"]):
        severity = 9
    elif any(w in text_lower for w in ["severe", "serious", "dangerous", "shortage", "flood", "injured"]):
        severity = 8
    elif any(w in text_lower for w in ["moderate", "concern", "issue"]):
        severity = 6

    # Extract numbers for affected count
    import re
    numbers = re.findall(r'(\d+)\s*(?:families|people|households|residents|children|patients|victims)', text_lower)
    # Also try to extract magnitude numbers like "7.0 magnitude"
    if not numbers:
        magnitude = re.findall(r'(\d+(?:\.\d+)?)\s*(?:magnitude|richter)', text_lower)
        if magnitude:
            severity = min(10, max(8, int(float(magnitude[0]))))

    affected = int(numbers[0]) if numbers else None

    # Location extraction — comprehensive Indian city + zone matching
    # First try major Indian cities (beyond Mumbai)
    location = None
    indian_cities = [
        "nagpur", "pune", "delhi", "new delhi", "bangalore", "bengaluru", "hyderabad",
        "chennai", "kolkata", "ahmedabad", "jaipur", "lucknow", "kanpur", "indore",
        "bhopal", "patna", "vadodara", "ludhiana", "agra", "nashik", "varanasi",
        "surat", "chandigarh", "coimbatore", "kochi", "thiruvananthapuram", "guwahati",
        "visakhapatnam", "mysuru", "mysore", "ranchi", "bhubaneswar", "dehradun",
        "amritsar", "jodhpur", "raipur", "gwalior", "jabalpur", "allahabad", "prayagraj",
        "noida", "gurgaon", "gurugram", "faridabad", "ghaziabad", "thane", "navi mumbai",
        "aurangabad", "solapur", "kolhapur", "sangli", "satara", "ratnagiri",
        # Mumbai zones
        "dharavi", "kurla", "govandi", "malad", "bandra", "sion", "worli", "andheri",
        "kandivali", "chembur", "vikhroli", "mankhurd", "jogeshwari", "dadar", "mumbai",
    ]
    for city in indian_cities:
        if city in text_lower:
            location = city.title()
            break

    # If no known city found, try to extract capitalized proper nouns from original text
    if not location:
        # Look for "in <Place>" pattern
        in_pattern = re.findall(r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
        if in_pattern:
            location = in_pattern[-1]  # take the last "in <Place>" match

    # Final fallback
    if not location:
        location = "Unknown"

    summary = text[:150].replace("\n", " ").strip()
    if len(summary) > 120:
        summary = summary[:117] + "..."

    # Map issue type to relevant required skills
    skills_map = {
        "food": ["food distribution", "cooking", "logistics"],
        "water": ["plumbing", "water purification", "logistics"],
        "health": ["medical first aid", "nursing", "patient care"],
        "housing": ["construction", "civil engineering", "disaster relief"],
        "education": ["teaching", "counseling"],
        "safety": ["social work", "legal aid", "disaster relief"],
    }
    required_skills = skills_map.get(issue_type, ["general volunteering"])

    return {
        "issue_type": issue_type,
        "location_text": location,
        "severity_score": severity,
        "affected_count": affected,
        "summary": summary,
        "required_skills": required_skills,
        "recommended_volunteer_count": max(1, min(5, (affected or 30) // 30)),
        "language_detected": "en",
    }


# ── Prompt 2: Coordinator Explanation ─────────────────────────────────────────
def generate_coordinator_explanation(
    issue_type: str,
    severity: int,
    affected_count: int | None,
    location: str,
    frequency: int,
    days: int,
) -> str:
    """Generates a plain-English explanation for NGO coordinators."""
    if not _init_models() or not _EXPLAIN_MODEL:
        return _fallback_explanation(issue_type, severity, affected_count, location, frequency, days)

    prompt = f"""Explain this urgency analysis to the NGO coordinator:

Issue type: {issue_type} | Severity: {severity}/10
Affected: ~{affected_count or 'unknown'} people | Location: {location}
Reports this week: {frequency} | Days since first report: {days}

What is happening, who is affected, and why does this need attention today?"""

    try:
        response = _EXPLAIN_MODEL.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"[generate_coordinator_explanation] {e}")
        return _fallback_explanation(issue_type, severity, affected_count, location, frequency, days)


def _fallback_explanation(issue_type, severity, affected_count, location, frequency, days):
    affected_str = f"approximately {affected_count}" if affected_count else "an unknown number of"
    return (
        f"A {issue_type} issue in {location} has been reported {frequency} times "
        f"with severity {severity}/10, affecting {affected_str} people. "
        f"This situation requires immediate coordinator attention."
    )


# ── Prompt 3: Volunteer Impact Framing ───────────────────────────────────────
def generate_impact_framing(
    issue_type: str,
    affected_count: int | None,
    location: str,
    required_skills: list[str],
) -> str:
    """Generates a motivating impact statement for volunteer task cards."""
    if not _init_models() or not _IMPACT_MODEL:
        return f"Your skills will help ~{affected_count or 'many'} people in {location} today."

    skills_str = ", ".join(required_skills) if required_skills else "general volunteering"
    prompt = f"""Write an impact statement for a volunteer accepting this task:

Issue: {issue_type} | Affected: {affected_count or 'many'} people | Location: {location}
Your skills needed: {skills_str}

Example: "Your food distribution skills will help ~47 families in Dharavi avoid hunger tonight."
"""

    try:
        response = _IMPACT_MODEL.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"[generate_impact_framing] {e}")
        return f"Your skills will help ~{affected_count or 'many'} people in {location} today."
