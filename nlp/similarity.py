"""
nlp/similarity.py
--------------------
NLP Pipeline Stage 11: Sentence Similarity.

Powers two dashboard features directly:
    - Feature 3: Repeated Question Detection (same/near-identical question
      reused across different years' papers).
    - Feature 4: Semantic Similarity (paraphrased questions that keyword
      matching alone would miss).

Both are built on cosine similarity over the sentence embeddings from
nlp/embeddings.py, NOT on string/keyword overlap.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import Config
from nlp.embeddings import embed_questions


def similarity_matrix(texts: list) -> np.ndarray:
    """Full pairwise cosine similarity matrix over all questions."""
    embeddings = embed_questions(texts)
    return cosine_similarity(embeddings)


def find_repeated_questions(questions: list, threshold: float = None) -> list:
    """
    questions: list of Question.to_dict()-shaped dicts (must include 'id',
    'label', 'text', 'source_file', 'year').

    Returns pairs of near-duplicate questions across different source
    files, sorted by similarity descending - i.e. genuinely "repeated
    across years", not two sub-parts of the same paper that happen to be
    similar.
    """
    threshold = threshold or Config.REPEAT_SIMILARITY_THRESHOLD
    texts = [q["text"] for q in questions]

    if len(texts) < 2:
        return []

    sim = similarity_matrix(texts)
    pairs = []

    for i in range(len(questions)):
        for j in range(i + 1, len(questions)):
            if questions[i]["source_file"] == questions[j]["source_file"]:
                continue  # only care about repeats across different papers/years
            score = float(sim[i][j])
            if score >= threshold:
                pairs.append(
                    {
                        "question_a": questions[i],
                        "question_b": questions[j],
                        "similarity": round(score * 100, 1),
                    }
                )

    pairs.sort(key=lambda p: p["similarity"], reverse=True)
    return pairs


def most_similar_to(query_text: str, questions: list, top_k: int = 5) -> list:
    """Rank every question by semantic similarity to an arbitrary query
    string - used by the Question Search feature for concept-based
    (not just keyword) search."""
    texts = [q["text"] for q in questions] + [query_text]
    sim = similarity_matrix(texts)
    query_row = sim[-1][:-1]

    ranked_indices = np.argsort(query_row)[::-1][:top_k]
    return [
        {**questions[i], "similarity": round(float(query_row[i]) * 100, 1)}
        for i in ranked_indices
    ]
