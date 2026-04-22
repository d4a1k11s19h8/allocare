"""
translate_client.py — Free translation using deep-translator (no API key needed).
Auto-detects language and translates to English before NLP processing.
Supports Hindi, Marathi, Tamil, Bengali, Telugu, Kannada, Malayalam + more.
"""
import logging
import re

logger = logging.getLogger(__name__)

# Try to import deep_translator, fallback gracefully
_translator_available = False
try:
    from deep_translator import GoogleTranslator
    _translator_available = True
except ImportError:
    logger.warning("[Translate] deep-translator not installed — translation disabled")


def detect_and_translate(text: str) -> tuple:
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

    if not _translator_available:
        return text, "en"

    try:
        # Quick heuristic: check if text contains non-ASCII characters
        # (indicates non-English text like Hindi, Marathi, etc.)
        non_ascii_ratio = sum(1 for c in text if ord(c) > 127) / max(len(text), 1)

        if non_ascii_ratio < 0.1:
            # Likely English — skip translation
            return text, "en"

        # Translate to English using auto-detection
        translated = GoogleTranslator(source="auto", target="en").translate(text)

        if not translated:
            return text, "auto"

        # Infer the source language from the presence of specific scripts
        detected_lang = _detect_language_heuristic(text)

        logger.info(f"[Translate] Translated from {detected_lang}: '{text[:50]}...' -> '{translated[:50]}...'")
        return translated, detected_lang

    except Exception as e:
        logger.error(f"[Translate] Error: {e}", exc_info=True)
        # Fallback: return original text, assume English
        return text, "en"


def _detect_language_heuristic(text: str) -> str:
    """Simple script-based language detection."""
    # Devanagari (Hindi, Marathi)
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"
    # Tamil
    if re.search(r'[\u0B80-\u0BFF]', text):
        return "ta"
    # Bengali
    if re.search(r'[\u0980-\u09FF]', text):
        return "bn"
    # Telugu
    if re.search(r'[\u0C00-\u0C7F]', text):
        return "te"
    # Kannada
    if re.search(r'[\u0C80-\u0CFF]', text):
        return "kn"
    # Malayalam
    if re.search(r'[\u0D00-\u0D7F]', text):
        return "ml"
    # Gujarati
    if re.search(r'[\u0A80-\u0AFF]', text):
        return "gu"
    # Arabic/Urdu
    if re.search(r'[\u0600-\u06FF]', text):
        return "ur"
    return "auto"


def translate_text(text: str, target_language: str = "en", source_language: str = None) -> str:
    """
    Simple translate helper for any direction.
    """
    if not _translator_available:
        return text

    try:
        source = source_language or "auto"
        result = GoogleTranslator(source=source, target=target_language).translate(text)
        return result or text
    except Exception as e:
        logger.error(f"[translate_text] {e}")
        return text
