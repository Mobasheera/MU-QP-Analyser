"""
nlp/embeddings.py
--------------------
NLP Pipeline Stage 10: Semantic Embedding.

Encodes every question into a dense vector using a pretrained sentence
transformer, so that "Explain POS Tagging" and "Describe Part of Speech
Tagging" land near each other in vector space even though they share
almost no exact words. This is the representation every downstream
semantic-similarity and topic-clustering feature is built on - the
project deliberately avoids keyword-only (TF-IDF/N-gram) matching for
these features, per the brief.
"""

from sentence_transformers import SentenceTransformer

from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

_model = None


def get_model():
    global _model
    if _model is None:
        logger.info("Loading sentence-transformer '%s' ...", Config.SENTENCE_MODEL)
        _model = SentenceTransformer(Config.SENTENCE_MODEL)
        logger.info("Sentence-transformer loaded.")
    return _model


def embed_questions(texts: list):
    """Return an (n_questions, embedding_dim) numpy array."""
    model = get_model()
    return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
