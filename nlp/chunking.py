"""
nlp/chunking.py
------------------
NLP Pipeline Stage 6: Chunking (shallow parsing).

Extracts noun phrase and verb phrase chunks from a question, e.g.
"Explain the Porter Stemming algorithm in detail" ->
    NP chunks: ["the Porter Stemming algorithm"]
    VP head:   "Explain"

This is the same shallow-parsing concept the papers ask students to
apply manually via CFG rules / parse trees (see Q5b in the May-2025
paper) - here it is produced automatically for every question.
"""

from nlp.preprocessing import normalize_text
from nlp.spacy_singleton import get_nlp


def chunk_text(text: str) -> dict:
    doc = get_nlp()(normalize_text(text))

    noun_chunks = [chunk.text for chunk in doc.noun_chunks]

    verb_phrases = []
    for tok in doc:
        if tok.pos_ == "VERB":
            phrase_tokens = [tok.text] + [
                child.text
                for child in tok.children
                if child.dep_ in ("dobj", "prt", "advmod", "xcomp")
            ]
            verb_phrases.append(" ".join(phrase_tokens))

    return {
        "noun_phrases": noun_chunks,
        "verb_phrases": verb_phrases,
    }
