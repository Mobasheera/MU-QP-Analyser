"""
nlp/ngram.py
--------------
NLP Pipeline Stage 8: N-Gram Extraction.

Surfaces the most common bigrams/trigrams across the whole question
corpus (e.g. "hidden markov", "word sense", "pos tagging") - these are
the recurring phrase-level patterns behind Feature 7 (N-Gram Analysis)
on the dashboard.
"""

from collections import Counter

from sklearn.feature_extraction.text import CountVectorizer

from nlp.preprocessing import lemmatize


def _lemmatized_corpus(texts: list) -> list:
    """Join lemmas back into a string per question so CountVectorizer can
    build n-grams over cleaned, stopword-free tokens."""
    cleaned = []
    for text in texts:
        lemmas = [
            lem for lem in lemmatize(text)
            if lem.isalpha() and len(lem) > 1
        ]
        cleaned.append(" ".join(lemmas))
    return cleaned


def top_ngrams(texts: list, n: int = 2, top_k: int = 15) -> list:
    """
    Return the top_k most frequent n-grams (n=2 -> bigrams, n=3 -> trigrams)
    across the full set of question texts, as [{"phrase": ..., "count": ...}].
    """
    corpus = [t for t in _lemmatized_corpus(texts) if t.strip()]
    if not corpus:
        return []

    vectorizer = CountVectorizer(
        ngram_range=(n, n),
        stop_words="english",
        min_df=1,
    )
    matrix = vectorizer.fit_transform(corpus)
    counts = matrix.sum(axis=0).A1
    vocab = vectorizer.get_feature_names_out()

    counter = Counter(dict(zip(vocab, counts)))
    return [
        {"phrase": phrase, "count": int(count)}
        for phrase, count in counter.most_common(top_k)
    ]


def bigrams_and_trigrams(texts: list, top_k: int = 15) -> dict:
    return {
        "bigrams": top_ngrams(texts, n=2, top_k=top_k),
        "trigrams": top_ngrams(texts, n=3, top_k=top_k),
    }
