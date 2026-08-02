"""
nlp/pipeline.py
------------------
Orchestrates the full NLP pipeline (stages 1-12) over a batch of already
question-segmented documents, and assembles every dashboard feature's
data in one place.

    Document Pipeline (backend/)          NLP Pipeline (nlp/, this module)
    -----------------------------         ---------------------------------
    PDF upload                            9.  TF-IDF Keyword Extraction
    -> text extraction / OCR              10. Semantic Embedding
    -> question segmentation      ---->   11. Sentence Similarity
                                           12. Topic Clustering
                                           (1-8 run per-question, on demand,
                                            via preprocessing/pos_tagging/
                                            chunking/ner/ngram)

Everything in this module works on plain dicts (Question.to_dict()), never
raw spaCy/embedding objects, so the result can be JSON-serialized straight
back to the frontend.
"""

import uuid

from nlp.ner import extract_entities
from nlp.ngram import bigrams_and_trigrams
from nlp.pos_tagging import pos_distribution
from nlp.preprocessing import preprocess_question
from nlp.similarity import find_repeated_questions
from nlp.tfidf_keywords import compute_tfidf_keywords, corpus_keyword_frequency
from nlp.topic_clustering import cluster_questions, topic_frequency
from utils.logger import get_logger
from utils.wordcloud_gen import generate_wordcloud

logger = get_logger(__name__)


def run_pipeline(questions: list, papers_meta: list) -> dict:
    """
    questions: list of Question.to_dict() dicts pooled across every
               uploaded paper.
    papers_meta: list of {"filename", "year", "ocr_used", "page_count"}
                 one entry per uploaded PDF - used for the stats cards.

    Returns the full analysis payload consumed by the dashboard.
    """
    run_id = uuid.uuid4().hex[:10]
    texts = [q["text"] for q in questions]

    logger.info("Running NLP pipeline on %d questions from %d papers", len(questions), len(papers_meta))

    # Stage 9: TF-IDF keywords, attached per-question.
    keywords_per_question, _, _ = compute_tfidf_keywords(texts, top_k=6)
    for q, kws in zip(questions, keywords_per_question):
        q["keywords"] = kws

    # Stage 12 (built on Stage 10 embeddings): topic clustering.
    questions = cluster_questions(questions)

    # Stage 11: semantic similarity -> repeated-question detection (Feature 3).
    repeated_pairs = find_repeated_questions(questions)

    # Feature 5: topic frequency table.
    topics = topic_frequency(questions)

    # Feature 7: n-gram analysis over the whole corpus.
    ngrams = bigrams_and_trigrams(texts, top_k=15)

    # Feature 6: word cloud image.
    wordcloud_path = generate_wordcloud(texts, run_id)

    # Corpus-wide keyword frequency (feeds "important concepts" summary).
    keyword_frequency = corpus_keyword_frequency(texts, top_k=20)

    # POS distribution across the whole corpus (nice aggregate chart).
    pos_dist = pos_distribution(texts)

    # Optional feature: topic timeline (topic x year presence grid).
    timeline = _build_topic_timeline(questions)

    stats = {
        "paper_count": len(papers_meta),
        "question_count": len(questions),
        "topic_count": len(topics),
        "repeated_count": len(repeated_pairs),
        "ocr_pages_used": sum(1 for p in papers_meta if p.get("ocr_used")),
    }

    return {
        "run_id": run_id,
        "stats": stats,
        "papers": papers_meta,
        "questions": questions,
        "topics": topics,
        "repeated_pairs": repeated_pairs,
        "ngrams": ngrams,
        "keyword_frequency": keyword_frequency,
        "pos_distribution": pos_dist,
        "wordcloud_path": wordcloud_path,
        "timeline": timeline,
    }


def inspect_question(question: dict) -> dict:
    """
    On-demand, per-question deep dive used by the Question Viewer modal:
    stages 1-4 (tokenize/stopwords/lemmatize/morphology), 5 (POS), 6
    (chunking) and 7 (NER) - the stages that are too granular to compute
    for every question up front, but are cheap to compute for just one.
    """
    from nlp.chunking import chunk_text
    from nlp.pos_tagging import pos_tag

    text = question["text"]
    return {
        **preprocess_question(text),
        "pos_tags": pos_tag(text),
        "chunks": chunk_text(text),
        "entities": extract_entities(text),
    }


def _build_topic_timeline(questions: list) -> list:
    """[{"topic": ..., "years": {"2024": True, "2025": True, ...}}, ...]"""
    topic_years = {}
    all_years = sorted({q["year"] for q in questions if q.get("year") and q["year"] != "Unknown"})

    for q in questions:
        topic = q.get("topic", "Unclassified")
        year = q.get("year", "Unknown")
        topic_years.setdefault(topic, set()).add(year)

    timeline = []
    for topic, years in sorted(topic_years.items(), key=lambda kv: -len(kv[1])):
        timeline.append(
            {
                "topic": topic,
                "years": {year: (year in years) for year in all_years},
            }
        )

    return {"years": all_years, "rows": timeline}
