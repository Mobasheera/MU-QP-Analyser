"""
nlp/topic_clustering.py
--------------------------
NLP Pipeline Stage 12: Topic Clustering.

Groups semantically similar questions together (Feature 2: Topic
Detection) using K-Means over the sentence embeddings from
nlp/embeddings.py, then labels each cluster with either a matching
canonical NLP-syllabus topic name (nlp/topics_gazetteer.py) or, failing
that, its most distinctive TF-IDF keyword - so every cluster gets a
name a student would recognize, not "Cluster 4".

This also directly produces Feature 5 (Topic Frequency Analysis): once
every question has a topic label, frequency/percentage is a simple
group-by.
"""

from sklearn.cluster import KMeans

from config import Config
from nlp.embeddings import embed_questions
from nlp.tfidf_keywords import compute_tfidf_keywords
from nlp.topics_gazetteer import best_matching_topic


def cluster_questions(questions: list) -> list:
    """
    questions: list of dicts (Question.to_dict()) - mutated in place with
    a "topic" key added to each, and also returned as the same list for
    convenience.
    """
    if not questions:
        return questions

    texts = [q["text"] for q in questions]
    n_clusters = max(1, min(Config.MAX_TOPIC_CLUSTERS, len(questions)))

    embeddings = embed_questions(texts)
    keywords_per_question, _, _ = compute_tfidf_keywords(texts, top_k=5)

    if n_clusters == 1:
        labels = [0] * len(questions)
    else:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

    # Gather keywords per cluster to derive a topic name.
    cluster_keywords = {}
    for label, kws in zip(labels, keywords_per_question):
        cluster_keywords.setdefault(label, []).extend(kws)

    cluster_names = {}
    for label, kws in cluster_keywords.items():
        topic_name = best_matching_topic(kws)
        if not topic_name:
            # Fall back to the single most common distinctive keyword,
            # title-cased so it reads like a topic ("Stemming" not "stemming").
            top_kw = _most_common(kws)
            topic_name = top_kw.title() if top_kw else f"Miscellaneous {label + 1}"
        cluster_names[label] = topic_name

    for question, label in zip(questions, labels):
        question["topic"] = cluster_names[label]
        question["cluster_id"] = int(label)

    return questions


def topic_frequency(questions: list) -> list:
    """Feature 5: Topic Frequency Analysis -> [{topic, count, percentage}]."""
    total = len(questions) or 1
    counts = {}
    for q in questions:
        topic = q.get("topic", "Unclassified")
        counts[topic] = counts.get(topic, 0) + 1

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [
        {
            "topic": topic,
            "count": count,
            "percentage": round(100 * count / total, 1),
        }
        for topic, count in ranked
    ]


def _most_common(items: list):
    if not items:
        return None
    counts = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]
