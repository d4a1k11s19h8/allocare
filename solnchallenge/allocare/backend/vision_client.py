"""
vision_client.py — OCR using Gemini Vision (multimodal), no extra API key needed.
Replaces Google Cloud Vision API (paid) with Gemini 2.0 Flash vision capabilities.
Uses the same free GEMINI_API_KEY from AI Studio.
"""
import os
import base64
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def _get_vision_model():
    genai.configure(api_key=_API_KEY)
    return genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=2048,
        ),
    )


def extract_text_from_image_bytes(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    Uses Gemini Vision to extract text from image bytes.
    Works with printed and handwritten text, multiple languages.

    Args:
        image_bytes: Raw image bytes
        mime_type: Image MIME type (image/jpeg, image/png)

    Returns:
        Extracted text string, or empty string on failure.
    """
    if not _API_KEY:
        logger.error("[Vision] No GEMINI_API_KEY — cannot extract text")
        return ""

    try:
        model = _get_vision_model()

        # Use Gemini's multimodal capability
        response = model.generate_content([
            "You are an OCR assistant. Extract ALL text visible in this image exactly as written. "
            "This may be a paper survey, field report, or handwritten note. "
            "Include all text, numbers, dates, and any handwritten content. "
            "If text is in Hindi, Marathi, Tamil, or any Indian language, transcribe it exactly. "
            "Return ONLY the extracted text with no commentary or formatting.",
            {
                "mime_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            },
        ])

        text = response.text.strip()
        logger.info(f"[Vision/Gemini] Extracted {len(text)} characters")
        return text

    except Exception as e:
        logger.error(f"[Vision/Gemini] Exception: {e}", exc_info=True)
        return ""


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
