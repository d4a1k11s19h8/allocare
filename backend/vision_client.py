"""
vision_client.py — OCR using Gemini Vision (multimodal), no extra API key needed.
Replaces Google Cloud Vision API (paid) with Gemini 2.0 Flash vision capabilities.
Uses the same free GEMINI_API_KEY from AI Studio.
Gracefully degrades when API key is not set.

Enhanced OCR with:
- Two-pass extraction (raw text → structured humanitarian data)
- Retry with exponential backoff
- Multi-language support (Hindi, Marathi, Tamil, Bengali, etc.)
- Confidence scoring
"""
import os
import base64
import logging
import time
import json
import re

logger = logging.getLogger(__name__)

_vision_model = None
_structured_model = None
_init_attempted = False


def _get_vision_model():
    """Lazy init: only create model when first called."""
    global _vision_model, _structured_model, _init_attempted
    if _init_attempted:
        return _vision_model
    _init_attempted = True

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("[Vision] No GEMINI_API_KEY — OCR will return empty text")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        # Model for raw text extraction — low temperature for accuracy
        _vision_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.05,
                max_output_tokens=4096,
            ),
        )

        # Model for structured data extraction from OCR text
        _structured_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
            system_instruction=(
                "You are a humanitarian field data extractor. "
                "Extract structured information from OCR text of field reports, surveys, and notes. "
                "Always return valid JSON."
            ),
        )

        logger.info("[Vision] Gemini Vision model initialized successfully.")
        return _vision_model
    except Exception as e:
        logger.error(f"[Vision] Failed to init Gemini Vision: {e}")
        return None


# ── Enhanced OCR Prompt ──────────────────────────────────────────────────────

RAW_OCR_PROMPT = """You are an expert OCR system specialized in reading humanitarian field reports from India.

TASK: Extract ALL text visible in this image with maximum accuracy.

RULES:
1. Extract EVERY word, number, date, and symbol visible in the image
2. Preserve the original layout and structure (headers, bullet points, tables)
3. If text is handwritten, do your best to transcribe it accurately
4. For Indian languages (Hindi, Marathi, Tamil, Bengali, Telugu, Kannada, Malayalam, Gujarati, Urdu):
   - Transcribe the text in its original script
   - Also provide an English translation in [brackets] after each non-English line
5. Extract ALL numbers — especially: affected counts, dates, phone numbers, severity ratings
6. For survey forms: extract field labels AND their filled values
7. For tables: preserve row/column structure using | separators
8. If any text is unclear, write [unclear] but still attempt your best guess in parentheses

OUTPUT FORMAT:
- Return ONLY the extracted text
- Use line breaks to separate lines as they appear in the image
- Do NOT add any commentary, headers, or markdown formatting
- Do NOT say "I can see..." or "The image shows..."
"""

STRUCTURED_EXTRACT_PROMPT = """Extract structured humanitarian data from this OCR text:

"{text}"

Return JSON with these fields:
{{
  "location": "extracted location/area name (city, zone, district)",
  "issue_type": "one of: food, water, health, housing, education, safety, other",
  "severity_indicators": ["list of words/phrases indicating severity"],
  "affected_count": number or null,
  "key_needs": ["list of specific needs mentioned"],
  "contact_info": "any phone numbers or names mentioned",
  "date_mentioned": "any dates found",
  "summary": "one-sentence summary of the situation",
  "confidence": "high, medium, or low — how confident you are in the extraction"
}}"""


def extract_text_from_image_bytes(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    Uses Gemini Vision to extract text from image bytes.
    Enhanced with retry logic and better prompts.

    Args:
        image_bytes: Raw image bytes
        mime_type: Image MIME type (image/jpeg, image/png)

    Returns:
        Extracted text string, or empty string on failure.
    """
    model = _get_vision_model()
    if not model:
        logger.error("[Vision] Model not available — returning empty text")
        return ""

    for attempt in range(3):
        try:
            response = model.generate_content([
                RAW_OCR_PROMPT,
                {
                    "mime_type": mime_type,
                    "data": base64.b64encode(image_bytes).decode("utf-8"),
                },
            ])

            text = response.text.strip()

            # Filter out non-OCR responses (model refusing or commenting)
            skip_phrases = [
                "i can't", "i cannot", "i'm unable", "no text visible",
                "the image shows", "this image contains", "i can see",
            ]
            if any(phrase in text.lower()[:100] for phrase in skip_phrases):
                logger.warning(f"[Vision] Model refused or commented instead of extracting: {text[:100]}")
                if attempt < 2:
                    time.sleep(1)
                    continue
                return ""

            logger.info(f"[Vision/Gemini] Extracted {len(text)} characters (attempt {attempt + 1})")
            return text

        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < 2:
                wait_time = 2 ** (attempt + 1)
                logger.warning(f"[Vision] Rate limited, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            logger.error(f"[Vision/Gemini] Exception on attempt {attempt + 1}: {e}", exc_info=True)
            if attempt < 2:
                time.sleep(1)
                continue
            return ""

    return ""


def extract_structured_from_ocr(ocr_text: str) -> dict:
    """
    Second pass: Extract structured humanitarian data from raw OCR text.
    Returns a dict with location, issue_type, affected_count, etc.
    """
    global _structured_model
    if not _structured_model:
        _get_vision_model()
    if not _structured_model:
        return _fallback_structured_extract(ocr_text)

    prompt = STRUCTURED_EXTRACT_PROMPT.format(text=ocr_text[:2000])

    try:
        response = _structured_model.generate_content(prompt)
        cleaned = response.text.strip()
        # Strip markdown fences
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        result = json.loads(cleaned.strip())
        return result
    except Exception as e:
        logger.error(f"[Vision] Structured extraction failed: {e}")
        return _fallback_structured_extract(ocr_text)


def _fallback_structured_extract(text: str) -> dict:
    """Rule-based structured extraction when Gemini unavailable."""
    text_lower = text.lower()

    # Issue detection
    issue_map = {
        "food": ["food", "hunger", "meal", "ration", "starv"],
        "water": ["water", "drinking", "pipeline", "tanker", "flood"],
        "health": ["health", "medical", "doctor", "dengue", "hospital", "sick", "disease"],
        "housing": ["housing", "shelter", "fire", "displaced", "earthquake", "collapsed"],
        "education": ["education", "school", "student", "teacher"],
        "safety": ["safety", "child labor", "crime", "danger", "rescue"],
    }
    issue_type = "other"
    for itype, keywords in issue_map.items():
        if any(kw in text_lower for kw in keywords):
            issue_type = itype
            break

    # Extract numbers
    numbers = re.findall(r'(\d+)\s*(?:families|people|households|residents|children|patients|victims|affected)', text_lower)
    affected = int(numbers[0]) if numbers else None

    return {
        "location": "Unknown",
        "issue_type": issue_type,
        "severity_indicators": [],
        "affected_count": affected,
        "key_needs": [],
        "contact_info": "",
        "date_mentioned": "",
        "summary": text[:150].replace("\n", " ").strip(),
        "confidence": "low",
    }


def extract_text_from_base64(base64_data: str, mime_type: str = "image/jpeg") -> str:
    """
    Extract text from base64-encoded image data.
    Handles data URLs (data:image/jpeg;base64,...).
    """
    try:
        # Strip data URL prefix if present
        if "," in base64_data:
            header, base64_data = base64_data.split(",", 1)
            if "png" in header:
                mime_type = "image/png"
            elif "jpeg" in header or "jpg" in header:
                mime_type = "image/jpeg"
            elif "webp" in header:
                mime_type = "image/webp"

        image_bytes = base64.b64decode(base64_data)
        return extract_text_from_image_bytes(image_bytes, mime_type)

    except Exception as e:
        logger.error(f"[Vision] Base64 decode error: {e}")
        return ""


# Keep backward compatibility
def extract_text_from_image(image_url: str) -> str:
    """Legacy: accepts URL — downloads and processes."""
    try:
        import requests
        resp = requests.get(image_url, timeout=10)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "image/jpeg")
            return extract_text_from_image_bytes(resp.content, content_type)
        return ""
    except Exception as e:
        logger.error(f"[Vision] URL download error: {e}")
        return ""
