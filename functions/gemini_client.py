"""
gemini_client.py: Gemini 3.1 Pro integration for AlloCare
All three prompt templates from the masterplan implemented here.
"""
import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

# ── configure Gemini ───────────────────────────────────────────────────────────
_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=_API_KEY)

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


# ── Prompt 1: Urgency Extraction ───────────────────────────────────────────────
def extract_urgency(raw_text: str) -> dict | None:
    """
    Takes raw field report text (English), returns structured urgency data.
    Returns None on failure.
    """
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

    try:
        response = _MODEL.generate_content(prompt)
        result = json.loads(response.text)

        # Validate and clamp severity_score
        result["severity_score"] = max(1, min(10, int(result.get("severity_score", 5))))
        result["recommended_volunteer_count"] = max(1, min(10, int(result.get("recommended_volunteer_count", 2))))
        if result.get("affected_count"):
            result["affected_count"] = max(1, int(result["affected_count"]))

        return result

    except json.JSONDecodeError as e:
        logger.error(f"[extract_urgency] JSON parse error: {e} | Raw: {response.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"[extract_urgency] Gemini error: {e}", exc_info=True)
        return None


# ── Prompt 2: Coordinator Explanation ─────────────────────────────────────────
def generate_coordinator_explanation(
    issue_type: str,
    severity: int,
    affected_count: int | None,
    location: str,
    frequency: int,
    days: int,
) -> str:
    """
    Generates a plain-English explanation for NGO coordinators.
    Returns explanation string or fallback message.
    """
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
        return (
            f"A {issue_type} issue in {location} has been reported {frequency} times "
            f"with severity {severity}/10, affecting approximately {affected_count or 'an unknown number of'} people."
        )


# ── Prompt 3: Volunteer Impact Framing ───────────────────────────────────────
def generate_impact_framing(
    issue_type: str,
    affected_count: int | None,
    location: str,
    required_skills: list[str],
) -> str:
    """
    Generates a motivating impact statement for volunteer task cards.
    Max 25 words. Returns statement or fallback.
    """
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
