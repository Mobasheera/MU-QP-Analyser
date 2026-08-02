"""
nlp/pos_tagging.py
--------------------
NLP Pipeline Stage 5: Part-of-Speech Tagging.

Fittingly, several actual exam questions in the dataset ask students to
perform POS tagging by hand (e.g. "What is hybrid POS tagging?") - this
module lets the dashboard demonstrate the same concept automatically on
every extracted question.
"""

from nlp.preprocessing import normalize_text
from nlp.spacy_singleton import get_nlp


def pos_tag(text: str) -> list:
    """Return [{token, pos, tag, explanation}, ...] for a question string."""
    doc = get_nlp()(normalize_text(text))
    tags = []
    for tok in doc:
        if tok.is_space:
            continue
        tags.append(
            {
                "token": tok.text,
                "pos": tok.pos_,          # coarse tag, e.g. NOUN, VERB
                "tag": tok.tag_,          # fine-grained Penn Treebank tag
                "explanation": _spacy_glossary(tok.pos_),
            }
        )
    return tags


def pos_distribution(texts: list) -> dict:
    """Aggregate POS tag counts across many questions - powers the
    'POS distribution' chart on the dashboard."""
    nlp = get_nlp()
    counts = {}
    for text in texts:
        doc = nlp(normalize_text(text))
        for tok in doc:
            if tok.is_space or tok.is_punct:
                continue
            counts[tok.pos_] = counts.get(tok.pos_, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


def _spacy_glossary(pos_tag_value: str) -> str:
    glossary = {
        "NOUN": "Noun",
        "PROPN": "Proper noun",
        "VERB": "Verb",
        "AUX": "Auxiliary verb",
        "ADJ": "Adjective",
        "ADV": "Adverb",
        "PRON": "Pronoun",
        "DET": "Determiner",
        "ADP": "Adposition (preposition/postposition)",
        "CCONJ": "Coordinating conjunction",
        "SCONJ": "Subordinating conjunction",
        "NUM": "Numeral",
        "PART": "Particle",
        "INTJ": "Interjection",
        "SYM": "Symbol",
        "X": "Other",
    }
    return glossary.get(pos_tag_value, pos_tag_value)
