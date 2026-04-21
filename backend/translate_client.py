"""
translate_client.py — Free translation using deep-translator (no API key needed).
Auto-detects language and translates to English before NLP processing.
Supports Hindi, Marathi, Tamil, Bengali, Telugu, Kannada, Malayalam + more.
"""
import logging
from deep_translator import GoogleTranslator, single_detection

logger = logging.getLogger(__name__)


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
        # Step 1: Detect language using Google Translate
        detected_lang = GoogleTranslator(source="auto", target="en").detect(text)
        if not detected_lang:
            detected_lang = "en"

        logger.info(f"[Translate] Detected language: {detected_lang}")

        # Step 2: Skip translation if already English
        if detected_lang == "en":
            return text, "en"

        # Step 3: Translate to English
        translated = GoogleTranslator(source=detected_lang, target="en").translate(text)

        if not translated:
            return text, detected_lang

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
        source = source_language or "auto"
        result = GoogleTranslator(source=source, target=target_language).translate(text)
        return result or text
    except Exception as e:
        logger.error(f"[translate_text] {e}")
        return text
