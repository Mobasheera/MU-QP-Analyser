"""
nlp/spacy_singleton.py
------------------------
Loads the spaCy pipeline exactly once and hands the same instance to every
NLP module. Loading `en_core_web_sm` is the single most expensive step in
the whole request lifecycle, so re-loading it per-request (or per-module)
would make the dashboard feel sluggish for no reason.
"""

import spacy

from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        logger.info("Loading spaCy model '%s' ...", Config.SPACY_MODEL)
        try:
            _nlp = spacy.load(Config.SPACY_MODEL)
        except OSError as exc:
            raise RuntimeError(
                f"spaCy model '{Config.SPACY_MODEL}' is not installed. "
                f"Run: python -m spacy download {Config.SPACY_MODEL}"
            ) from exc
        logger.info("spaCy model loaded.")
    return _nlp
