"""
nlp/ner.py
------------
NLP Pipeline Stage 7: Named Entity Recognition.

Question papers reference named algorithms, models, and people
(e.g. "Hidden Markov Model", "Viterbi algorithm", "Naive Bayes",
"Maximum Entropy", "Hobbs' Algorithm", "Centering Theory"). Standard
spaCy NER is trained on general text and won't label these as a custom
"ALGORITHM" entity type, so this module pairs spaCy's general-purpose
NER (PERSON, ORG, GPE, etc.) with a lightweight rule-based gazetteer of
known NLP/CS terminology - giving a much more useful entity list for
this specific academic domain than either approach alone.
"""

import re

from nlp.preprocessing import normalize_text
from nlp.spacy_singleton import get_nlp

# Small domain gazetteer of recurring NLP/CS terms that plain spaCy NER
# (trained on news text) would otherwise miss entirely.
NLP_TERM_GAZETTEER = [
    "Hidden Markov Model", "HMM", "Viterbi Algorithm", "Naive Bayes",
    "Maximum Entropy", "MaxEnt", "Hobbs Algorithm", "Centering Theory",
    "Porter Stemming", "Porter Stemmer", "Word Sense Disambiguation", "WSD",
    "Part of Speech", "POS Tagging", "N-gram", "Bigram", "Trigram",
    "Finite State Transducer", "FST", "Context Free Grammar", "CFG",
    "CYK Algorithm", "CKY Algorithm", "Shift Reduce Parser",
    "Machine Translation", "Named Entity Recognition", "Text Summarization",
    "Question Answering", "Yarowsky", "Hyperlex", "Anaphora Resolution",
    "Co-reference Resolution", "Regular Expression", "Parse Tree",
    "Recursive Descent Parser", "Semantic Role Labeling",
]

_gazetteer_pattern = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in NLP_TERM_GAZETTEER) + r")\b",
    re.IGNORECASE,
)


def extract_entities(text: str) -> list:
    """Return [{text, label}] combining spaCy general NER + the NLP gazetteer."""
    normalized = normalize_text(text)
    doc = get_nlp()(normalized)

    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    seen = {e["text"].lower() for e in entities}
    for match in _gazetteer_pattern.finditer(normalized):
        term = match.group(1)
        if term.lower() not in seen:
            entities.append({"text": term, "label": "NLP_CONCEPT"})
            seen.add(term.lower())

    return entities
