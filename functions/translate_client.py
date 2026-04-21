"""
translate_client.py — Google Cloud Translation API for multilingual field reports
Auto-detects language and translates to English before NLP processing.
Supports Hindi, Marathi, Tamil, Bengali, Telugu, Kannada, Malayalam + more.
"""
import os
import logging
from google.cloud import translate_v2 as translate

logger = logging.getLogger(__name__)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = translate.Client()
    return _client


def detect_and_translate(text: str) -> tuple[str, str]:
    """
    Detects language and translates to English if needed.

    Args:
        text: Raw field report text (any language)

    Returns:
        Tuple of (english_text, detected_language_code)
        If already English, returns original text with 'en'.
    """
    if not text or not text.strip():
        return text, "en"

    try:
        client = _get_client()

        # Step 1: Detect language
        detection = client.detect_language(text)
        detected_lang = detection.get("language", "en")
        confidence = detection.get("confidence", 0)

        logger.info(f"[Translate] Detected language: {detected_lang} (confidence: {confidence:.2f})")

        # Step 2: Skip translation if already English
        if detected_lang == "en" and confidence > 0.5:
            return text, "en"

        # Step 3: Translate to English
        result = client.translate(text, target_language="en", source_language=detected_lang)
        translated = result.get("translatedText", text)

        # Unescape HTML entities from translation API
        import html
        translated = html.unescape(translated)

        logger.info(f"[Translate] Translated from {detected_lang}: '{text[:50]}...' -> '{translated[:50]}...'")
        return translated, detected_lang

    except Exception as e:
        logger.error(f"[Translate] Error: {e}", exc_info=True)
        # Fallback: return original text, assume English
        return text, "en"


def translate_text(text: str, target_language: str = "en", source_language: str = None) -> str:
    """
    Simple translate helper for any direction.
    """
    try:
        client = _get_client()
        params = {"target_language": target_language}
        if source_language:
            params["source_language"] = source_language
        result = client.translate(text, **params)
        import html
        return html.unescape(result.get("translatedText", text))
    except Exception as e:
        logger.error(f"[translate_text] {e}")
        return text
