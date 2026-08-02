"""
utils/wordcloud_gen.py
-------------------------
Feature 6: Word Cloud.

Renders a word cloud PNG from all extracted (stopword-free, lemmatized)
question text for a given analysis run, saved under static/generated/ so
the dashboard can simply <img src="..."> it.
"""

import os

from wordcloud import WordCloud

from config import Config
from nlp.preprocessing import lemmatize


def generate_wordcloud(texts: list, run_id: str) -> str:
    """
    Build a word cloud image from the corpus and return its path relative
    to /static (ready to drop into an <img> src in the templates).
    """
    all_lemmas = []
    for text in texts:
        all_lemmas.extend(lem for lem in lemmatize(text) if lem.isalpha() and len(lem) > 2)

    joined_text = " ".join(all_lemmas) or "no data"

    wc = WordCloud(
        width=1000,
        height=500,
        background_color="white",
        colormap="viridis",
        collocations=True,
        max_words=120,
    ).generate(joined_text)

    filename = f"wordcloud_{run_id}.png"
    output_path = os.path.join(Config.GENERATED_FOLDER, filename)
    wc.to_file(output_path)

    return f"generated/{filename}"
