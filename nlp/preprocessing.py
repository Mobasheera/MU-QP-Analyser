"""
nlp/preprocessing.py
----------------------
NLP Pipeline Stages 1-4:
    1. Tokenization
    2. Stopword Removal
    3. Lemmatization
    4. Morphological Analysis

Each function returns plain Python data (lists/dicts) rather than raw
spaCy objects, so downstream stages and the Flask JSON API don't need to
know anything about spaCy internals.
"""

import re

from nltk.stem import PorterStemmer

from nlp.spacy_singleton import get_nlp

_WHITESPACE_RE = re.compile(r"\s+")
_stemmer = PorterStemmer()


def normalize_text(text: str) -> str:
    """Collapse whitespace/newlines left over from PDF/OCR extraction."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def tokenize(text: str) -> list:
    """Stage 1: Tokenization - split question text into word tokens."""
    doc = get_nlp()(normalize_text(text))
    return [tok.text for tok in doc if not tok.is_space]


def remove_stopwords(text: str) -> list:
    """Stage 2: Stopword Removal - keep only content-bearing tokens."""
    doc = get_nlp()(normalize_text(text))
    return [
        tok.text
        for tok in doc
        if not tok.is_stop and not tok.is_punct and not tok.is_space
    ]


def lemmatize(text: str) -> list:
    """Stage 3: Lemmatization - reduce words to their dictionary base form."""
    doc = get_nlp()(normalize_text(text))
    return [
        tok.lemma_.lower()
        for tok in doc
        if not tok.is_punct and not tok.is_space
    ]


def stem_tokens(text: str) -> list:
    """
    Bonus stage: Porter Stemming (NLTK) alongside spaCy lemmatization.
    Included specifically because several papers in the dataset ask
    students to explain the Porter Stemming algorithm directly - the
    dashboard can show it running on the very questions that describe it,
    and the lemma/stem contrast (e.g. "studies" -> lemma "study",
    stem "studi") is itself a useful morphology talking point.
    """
    doc = get_nlp()(normalize_text(text))
    return [
        _stemmer.stem(tok.text.lower())
        for tok in doc
        if not tok.is_punct and not tok.is_space
    ]


def morphological_analysis(text: str) -> list:
    """
    Stage 4: Morphological Analysis - for every token, report its
    lemma (spaCy), Porter stem (NLTK), coarse POS, and the full
    morphological feature set (e.g. Number=Sing, Tense=Past, Degree=Cmp).
    This is what lets the dashboard show, e.g., that "chases" -> lemma
    "chase", stem "chase", Tense=Pres | Number=Sing | Person=3.
    """
    doc = get_nlp()(normalize_text(text))
    analysis = []
    for tok in doc:
        if tok.is_punct or tok.is_space:
            continue
        analysis.append(
            {
                "token": tok.text,
                "lemma": tok.lemma_,
                "stem": _stemmer.stem(tok.text.lower()),
                "pos": tok.pos_,
                "morphology": str(tok.morph) or "—",
            }
        )
    return analysis


def preprocess_question(text: str) -> dict:
    """Bundle stages 1-4 for a single question - used by the per-question
    'inspect' view in the dashboard's Question Viewer."""
    return {
        "tokens": tokenize(text),
        "tokens_no_stopwords": remove_stopwords(text),
        "lemmas": lemmatize(text),
        "stems": stem_tokens(text),
        "morphology": morphological_analysis(text),
    }
