"""
config.py
---------
Central configuration for the Mumbai University Question Paper Analyzer.
Keeping configuration in one object makes it trivial to switch between
development / testing / production setups without touching business logic.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "mu-nlp-analyzer-dev-key")
    DEBUG = True

    # Folders
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    PROCESSED_FOLDER = os.path.join(BASE_DIR, "processed")
    GENERATED_FOLDER = os.path.join(BASE_DIR, "static", "generated")

    ALLOWED_EXTENSIONS = {"pdf"}
    MAX_CONTENT_LENGTH = 60 * 1024 * 1024  # 60 MB total upload cap

    # OCR
    OCR_DPI = 300
    OCR_LANG = "eng"
    # If Tesseract is not on PATH (common on Windows), set the full binary
    # path here, e.g. r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    TESSERACT_CMD = os.environ.get("TESSERACT_CMD", None)
    # Same idea for Poppler (needed by pdf2image) on Windows.
    POPPLER_PATH = os.environ.get("POPPLER_PATH", None)

    # NLP
    SPACY_MODEL = "en_core_web_sm"
    SENTENCE_MODEL = "all-MiniLM-L6-v2"

    # A page is considered "text-native" (no OCR needed) if PyMuPDF can pull
    # at least this many characters of text out of it.
    MIN_TEXT_CHARS_PER_PAGE = 40

    # Two questions are flagged as "repeated" when their semantic similarity
    # is at or above this threshold (cosine similarity, 0-1).
    REPEAT_SIMILARITY_THRESHOLD = 0.80

    # Number of topic clusters to fit when auto-detecting topics.
    # Actual number used is min(this, number_of_questions).
    MAX_TOPIC_CLUSTERS = 12


def ensure_directories():
    for folder in (
        Config.UPLOAD_FOLDER,
        Config.PROCESSED_FOLDER,
        Config.GENERATED_FOLDER,
    ):
        os.makedirs(folder, exist_ok=True)
