"""
vision_client.py — Gemini Vision API integration for AlloCare using google-genai
Provides OCR and structured data extraction from images of field reports.
Gracefully degrades when GEMINI_API_KEY is not set.
"""
import os
import json
import logging
import base64
import re
import time
from typing import Dict, Any, Optional

from google.genai import types

logger = logging.getLogger(__name__)

# ── Lazy initialisation ───────────────────────────────────────────────────────
_vision_initialised = False
_gemini_pool = None


def _init_vision() -> bool:
    """Lazy init: create the pool only when first needed."""
    global _vision_initialised, _gemini_pool
    if _vision_initialised:
        return _gemini_pool is not None

    _vision_initialised = True

    try:
        from .gemini_key_pool import build_pool_from_env
        
        # Determine if any key is set
        has_key = False
        for k in os.environ:
            if k.startswith("GEMINI_API_KEY") and os.environ.get(k, "").strip():
                has_key = True
                break
                
        if not has_key:
            logger.warning("[vision_client] No GEMINI_API_KEY set — using fallback responses.")
            return False

        _gemini_pool = build_pool_from_env(
            model_name="gemini-2.5-flash",
            max_retries=3
        )
        logger.info("[vision_client] Gemini Key Pool initialized successfully.")
        return True
    except EnvironmentError:
        logger.warning("[vision_client] No GEMINI_API_KEY found — using fallback responses.")
        return False
    except Exception as e:
        logger.error(f"[vision_client] Failed to init Gemini Key Pool: {e}")
        return False


# ── Enhanced OCR Prompt ───────────────────────────────────────────────────────

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
    if not _init_vision() or not _gemini_pool:
        logger.error("[Vision] Model not available — returning empty text")
        return ""

    for attempt in range(3):
        try:
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            )
            
            response = _gemini_pool.generate(
                contents=[RAW_OCR_PROMPT, image_part]
            )

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
    if not _init_vision() or not _gemini_pool:
        return _fallback_structured_extract(ocr_text)

    prompt = STRUCTURED_EXTRACT_PROMPT.format(text=ocr_text[:2000])
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
    )

    try:
        response = _gemini_pool.generate(contents=prompt, config=config)
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
