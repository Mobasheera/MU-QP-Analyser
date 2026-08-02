"""
utils/file_utils.py
--------------------
Small, reusable filesystem helpers. Kept separate from business logic so
routes.py and the NLP pipeline don't need to know how files are named,
validated, or stored on disk.
"""

import os
import re
import uuid

from config import Config


def allowed_file(filename: str) -> bool:
    """True if the filename has an extension we accept (currently: pdf)."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


def safe_slug(text: str, max_len: int = 60) -> str:
    """Turn arbitrary text into a filesystem/URL-safe slug."""
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.strip().lower())
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:max_len] or "file"

def unique_upload_path(original_filename: str) -> str:
    """
    Build a collision-free path inside the upload folder while preserving
    a human-readable prefix of the original filename (helps debugging and
    keeps the UI's "detected filename" honest).
    """
    base, ext = os.path.splitext(original_filename)
    slug = safe_slug(base)
    unique_name = f"{slug}-{uuid.uuid4().hex[:8]}{ext}"
    return os.path.join(Config.UPLOAD_FOLDER, unique_name)


def guess_academic_year(filename: str, extracted_text: str) -> str:
    """
    Best-effort guess of the exam year, used purely for the "Topic Timeline"
    feature. Looks for a 4-digit year in the filename first, then in the
    first page of extracted text (handwritten exam-office date stamps like
    "30/11/2024" or "06.06.2025" commonly appear on Mumbai University papers).
    """
    year_pattern = re.compile(r"(20\d{2})")

    match = year_pattern.search(filename)
    if match:
        return match.group(1)

    match = year_pattern.search(extracted_text[:800])
    if match:
        return match.group(1)

    return "Unknown"
