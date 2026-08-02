"""
nlp/tfidf_keywords.py
------------------------
NLP Pipeline Stage 9: TF-IDF Keyword Extraction.

Identifies the words that are distinctively important to *each* question
relative to the whole corpus - e.g. "Viterbi" scores high for the one
question that mentions it, while generic exam words ("explain", "define")
score low everywhere because they appear in almost every question.
"""

from sklearn.feature_extraction.text import TfidfVectorizer

from nlp.preprocessing import lemmatize


def _lemmatized_corpus(texts: list) -> list:
    cleaned = []
    for text in texts:
        lemmas = [lem for lem in lemmatize(text) if lem.isalpha() and len(lem) > 1]
        cleaned.append(" ".join(lemmas))
    return cleaned


def compute_tfidf_keywords(texts: list, top_k: int = 6):
    """
    Fit TF-IDF over the whole corpus once, then return the top_k highest
    scoring terms for every individual question.

    Returns: (per_question_keywords: list[list[str]], vectorizer, matrix)
    The vectorizer/matrix are also returned so callers (e.g. topic
    clustering) can reuse the same TF-IDF space instead of recomputing it.
    """
    corpus = _lemmatized_corpus(texts)
    non_empty = [c if c.strip() else "empty" for c in corpus]

    vectorizer = TfidfVectorizer(stop_words="english", max_df=0.85, min_df=1)
    matrix = vectorizer.fit_transform(non_empty)
    vocab = vectorizer.get_feature_names_out()

    per_question_keywords = []
    for row in range(matrix.shape[0]):
        row_data = matrix[row].toarray().flatten()
        top_indices = row_data.argsort()[::-1][:top_k]
        keywords = [vocab[i] for i in top_indices if row_data[i] > 0]
        per_question_keywords.append(keywords)

    return per_question_keywords, vectorizer, matrix


def corpus_keyword_frequency(texts: list, top_k: int = 25) -> list:
    """Global keyword frequency table, used to seed the Word Cloud + the
    'important NLP concepts' topic-detection heuristics."""
    per_question_keywords, _, _ = compute_tfidf_keywords(texts, top_k=10)
    freq = {}
    for keywords in per_question_keywords:
        for kw in keywords:
            freq[kw] = freq.get(kw, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [{"term": term, "count": count} for term, count in ranked]
