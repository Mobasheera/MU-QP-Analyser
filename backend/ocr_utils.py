"""
backend/ocr_utils.py
---------------------
OCR fallback for scanned Mumbai University question papers.

NOTE (per project brief): OCR is a document-digitization concern, not an
NLP technique in itself - it only exists so the real NLP pipeline
(nlp/pipeline.py) always has clean text to work with, regardless of
whether the source PDF was typed or a scanned photocopy.

Handles, in order:
    1. Rendering the target PDF page to an image (pdf2image / Poppler).
    2. Deskewing rotated scans (common with photocopied papers).
    3. Denoising + adaptive thresholding to lift text off stamps/watermarks.
    4. Running Tesseract OCR on the cleaned image.
"""

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path

from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

if Config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD


def _deskew(image: np.ndarray) -> np.ndarray:
    """Estimate and correct small rotation angles from a scanned page."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if coords.shape[0] == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Ignore near-zero corrections; avoids nudging already-straight pages.
    if abs(angle) < 0.3:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def _clean_for_ocr(image: np.ndarray) -> np.ndarray:
    """Denoise + threshold so faint stamps/watermarks don't confuse Tesseract."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=15)
    cleaned = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    return cleaned


def ocr_pdf_page(pdf_path: str, page_index: int) -> str:
    """
    Render a single PDF page (0-indexed) to an image and OCR it.
    Falls back to an empty string (logged) if OCR fails outright, so a
    single unreadable page never crashes the whole upload.
    """
    try:
        images = convert_from_path(
            pdf_path,
            dpi=Config.OCR_DPI,
            first_page=page_index + 1,
            last_page=page_index + 1,
            poppler_path=Config.POPPLER_PATH,
        )
        if not images:
            return ""

        pil_image = images[0]
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        cv_image = _deskew(cv_image)
        cleaned = _clean_for_ocr(cv_image)

        text = pytesseract.image_to_string(cleaned, lang=Config.OCR_LANG)
        return text
    except Exception as exc:  # noqa: BLE001 - a single bad page shouldn't crash the batch
        logger.warning("OCR failed on page %d: %s", page_index + 1, exc)
        return ""
