"""
backend/pdf_processor.py
-------------------------
Stage 1 of the document pipeline: turn an uploaded PDF into raw text,
per page, deciding per-page whether the embedded text layer is usable
or whether the page must fall back to OCR.

Mumbai University question papers are a mixed bag: some are digitally
typeset, some are flatbed-scanned photocopies, some are rotated, and
almost all of them carry a diagonal watermark (e.g. "muquestionpapers.com")
that pollutes both the text layer and OCR output if not filtered out.
"""

import re

import fitz  # PyMuPDF

from config import Config
from backend.ocr_utils import ocr_pdf_page
from utils.logger import get_logger

logger = get_logger(__name__)

# Watermark / boilerplate lines that repeat across MU papers and add no
# semantic value to the NLP pipeline - stripped before question segmentation.
WATERMARK_PATTERNS = [
    re.compile(r"muquestionpapers\.com", re.IGNORECASE),
    re.compile(r"^\s*\*{5,}\s*$"),
    re.compile(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
]


def _clean_page_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if any(pattern.search(line) for pattern in WATERMARK_PATTERNS):
            continue
        lines.append(line)
    return "\n".join(lines)


def extract_document(pdf_path: str) -> dict:
    """
    Extract text from every page of a PDF.

    Returns a dict:
        {
            "pages": [ {"page_number": 1, "text": "...", "source": "text"|"ocr"} , ...],
            "full_text": "<all pages concatenated>",
            "ocr_used": bool,
            "page_count": int,
        }
    """
    doc = fitz.open(pdf_path)
    pages = []
    ocr_used = False

    for index in range(len(doc)):
        page = doc[index]
        raw_text = page.get_text("text") or ""

        if len(raw_text.strip()) >= Config.MIN_TEXT_CHARS_PER_PAGE:
            source = "text"
            page_text = raw_text
        else:
            # Not enough embedded text -> treat as a scanned page and OCR it.
            logger.info("Page %d has no usable text layer, running OCR", index + 1)
            page_text = ocr_pdf_page(pdf_path, index)
            source = "ocr"
            ocr_used = True

        pages.append(
            {
                "page_number": index + 1,
                "text": _clean_page_text(page_text),
                "source": source,
            }
        )

    doc.close()

    full_text = "\n".join(p["text"] for p in pages)

    return {
        "pages": pages,
        "full_text": full_text,
        "ocr_used": ocr_used,
        "page_count": len(pages),
    }
