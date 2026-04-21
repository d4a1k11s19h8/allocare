"""
vision_client.py — Google Cloud Vision API for paper survey OCR
"""
import os
import logging
from google.cloud import vision

logger = logging.getLogger(__name__)


def extract_text_from_image(image_url: str) -> str:
    """
    Calls Cloud Vision DOCUMENT_TEXT_DETECTION on the given image URL.
    Supports printed and handwritten text, multiple languages.

    Args:
        image_url: Firebase Storage download URL or GCS URI

    Returns:
        Extracted text string, or empty string on failure.
    """
    client = vision.ImageAnnotatorClient()

    image = vision.Image()
    image.source.image_uri = image_url

    image_context = vision.ImageContext(
        language_hints=["en", "hi", "mr", "ta", "bn", "te", "kn", "ml"]
    )

    try:
        response = client.document_text_detection(
            image=image,
            image_context=image_context,
        )

        if response.error.message:
            logger.error(f"[Vision API] Error: {response.error.message}")
            return ""

        full_text = response.full_text_annotation.text if response.full_text_annotation else ""

        # Check confidence
        if response.full_text_annotation.pages:
            avg_confidence = sum(
                block.confidence
                for page in response.full_text_annotation.pages
                for block in page.blocks
            ) / max(1, sum(len(page.blocks) for page in response.full_text_annotation.pages))

            if avg_confidence < 0.6:
                logger.warning(f"[Vision API] Low confidence ({avg_confidence:.2f}) — flagging for review")
                # Still return text but caller will check this

        logger.info(f"[Vision API] Extracted {len(full_text)} characters")
        return full_text.strip()

    except Exception as e:
        logger.error(f"[Vision API] Exception: {e}", exc_info=True)
        return ""


def extract_text_from_bytes(image_bytes: bytes) -> str:
    """
    Alternate: takes raw image bytes instead of URL.
    Used when image is uploaded directly to Cloud Functions.
    """
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    image_context = vision.ImageContext(
        language_hints=["en", "hi", "mr", "ta", "bn", "te"]
    )

    try:
        response = client.document_text_detection(image=image, image_context=image_context)
        if response.error.message:
            return ""
        return response.full_text_annotation.text.strip() if response.full_text_annotation else ""
    except Exception as e:
        logger.error(f"[Vision API bytes] {e}")
        return ""
