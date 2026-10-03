from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

_model = None


def get_model():
    global _model

    if _model is None:
        # Import only when embeddings are actually needed.
        from sentence_transformers import SentenceTransformer

        logger.info("Loading sentence-transformer '%s' ...", Config.SENTENCE_MODEL)
        _model = SentenceTransformer(Config.SENTENCE_MODEL)
        logger.info("Sentence-transformer loaded.")

    return _model


def embed_questions(texts: list):
    model = get_model()
    return model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True
    )