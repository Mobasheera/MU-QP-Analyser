"""
nlp/topics_gazetteer.py
--------------------------
A curated list of recurring Mumbai University NLP-syllabus topics, each
with a set of keyword cues used to give an auto-detected question cluster
a human-readable name (e.g. "POS Tagging" instead of "Cluster 3").

This is intentionally small and domain-specific rather than a generic
topic-modeling vocabulary - it mirrors the actual NLP (DLOC-III) syllabus
that these question papers are drawn from.
"""

CANONICAL_TOPICS = {
    "POS Tagging": ["pos", "tagging", "tag", "hmm", "markov", "maxent", "entropy", "viterbi"],
    "Morphology": ["morphological", "morphology", "derivational", "inflectional", "stemming", "fst", "transducer"],
    "Word Sense Disambiguation": ["sense", "disambiguation", "wsd", "yarowsky", "hyperlex", "supervise"],
    "Language Models & N-grams": ["gram", "bigram", "trigram", "corpus", "probability", "language model"],
    "Parsing & Grammar": ["parse", "parser", "grammar", "cfg", "cyk", "cky", "shift", "reduce", "tree"],
    "Co-reference & Anaphora": ["reference", "coreference", "anaphora", "hobbs", "centering", "ambiguity"],
    "Machine Translation": ["translation", "rule", "bilingual", "transfer"],
    "Text Summarization": ["summarization", "summary", "abstractive", "extractive"],
    "Question Answering": ["question answering", "answering", "qa system"],
    "Preprocessing & Regex": ["preprocessing", "regular expression", "regex", "tokenization", "normalization"],
    "Semantic Role Labeling": ["semantic role", "predicate", "argument"],
    "Named Entity Recognition": ["entity", "ner", "named"],
}


def best_matching_topic(keywords: list) -> str:
    """Score each canonical topic by keyword overlap and return the best
    match, or None if nothing scores above zero (caller should fall back
    to a keyword-derived label in that case)."""
    joined = " ".join(keywords).lower()
    best_topic, best_score = None, 0

    for topic, cues in CANONICAL_TOPICS.items():
        score = sum(1 for cue in cues if cue in joined)
        if score > best_score:
            best_topic, best_score = topic, score

    return best_topic
