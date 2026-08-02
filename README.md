# Mumbai University Question Paper Analyzer

An NLP-based web application (Semester 7 NLP Lab Mini Project) that analyzes
Mumbai University question papers to surface recurring concepts, repeated
questions, and topic trends — using real NLP techniques, not PDF diffing.

Upload a few years of a subject's question papers and the app will:

- extract every question as an individual unit (not one PDF-sized blob)
- run a 12-stage NLP pipeline over them (tokenization → topic clustering)
- detect questions that are semantically repeated across years, even when reworded
- cluster questions into syllabus topics automatically
- generate a word cloud, n-gram tables, and a searchable question viewer

## Tech stack

| Layer      | Tools |
|------------|-------|
| Frontend   | HTML5, CSS3, Bootstrap 5, Chart.js, vanilla JavaScript |
| Backend    | Python, Flask |
| NLP        | spaCy, NLTK, scikit-learn, sentence-transformers |
| Documents  | PyMuPDF, pytesseract, pdf2image, OpenCV |
| Data/viz   | pandas, NumPy, matplotlib, wordcloud |
| Storage    | None — everything runs in-memory, locally, for the life of the process |

## NLP pipeline

1. Tokenization
2. Stopword Removal
3. Lemmatization *(spaCy)* + Porter Stemming *(NLTK)*
4. Morphological Analysis
5. POS Tagging
6. Chunking (noun/verb phrases)
7. Named Entity Recognition (spaCy NER + a small NLP-syllabus gazetteer)
8. N-Gram Extraction (bigrams/trigrams)
9. TF-IDF Keyword Extraction
10. Semantic Embedding *(sentence-transformers, `all-MiniLM-L6-v2`)*
11. Sentence Similarity → repeated-question detection
12. Topic Clustering *(K-Means over embeddings)* → topic frequency

Stages 1–7 run on demand per-question (the dashboard's "Question Viewer"
inspect modal); stages 8–12 run once across the whole uploaded corpus.

## Project structure

```
mu_nlp_analyzer/
├── app.py                     # Flask entry point / app factory
├── config.py                  # Central configuration
├── requirements.txt
├── backend/
│   ├── routes.py               # All Flask routes + in-memory run cache
│   ├── pdf_processor.py        # Text extraction, text-vs-scan detection
│   ├── ocr_utils.py            # Deskew/denoise + Tesseract OCR fallback
│   └── question_segmenter.py   # Splits paper text into Q1(a), Q1(b), ...
├── nlp/
│   ├── spacy_singleton.py      # Loads spaCy model once
│   ├── preprocessing.py        # Stages 1-4
│   ├── pos_tagging.py          # Stage 5
│   ├── chunking.py             # Stage 6
│   ├── ner.py                  # Stage 7
│   ├── ngram.py                # Stage 8
│   ├── tfidf_keywords.py       # Stage 9
│   ├── embeddings.py           # Stage 10
│   ├── similarity.py           # Stage 11
│   ├── topics_gazetteer.py     # Canonical NLP-syllabus topic list
│   ├── topic_clustering.py     # Stage 12
│   └── pipeline.py             # Orchestrates everything above
├── utils/
│   ├── file_utils.py           # Upload validation, year-guessing, slugs
│   ├── wordcloud_gen.py        # Feature 6: word cloud image
│   └── logger.py
├── static/
│   ├── css/style.css
│   ├── js/{main,dashboard,theme}.js
│   └── generated/              # word cloud PNGs land here at runtime
├── templates/
│   ├── base.html, index.html, dashboard.html
├── uploads/                    # uploaded PDFs (created at runtime)
└── processed/                  # reserved for any cached intermediate output
```

## Setup

**Requirements:** Python 3.10+, and two OS-level binaries used for OCR:

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (`tesseract`)
- [Poppler](https://poppler.freedesktop.org/) (`pdftoppm`, needed by `pdf2image`)

On Ubuntu/Debian: `sudo apt install tesseract-ocr poppler-utils`
On macOS: `brew install tesseract poppler`
On Windows: install both separately and either put them on PATH, or set
`TESSERACT_CMD` / `POPPLER_PATH` environment variables (see `config.py`).

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Download the spaCy model
python -m spacy download en_core_web_sm

# 4. Download NLTK data (Porter stemmer needs no corpus, but this keeps
#    NLTK quiet on first run)
python -m nltk.downloader punkt

# 5. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** and drag in a few question paper PDFs.

> First run will be slow: spaCy and the sentence-transformer model are
> downloaded/loaded once and then cached in memory for the process lifetime.

## Notes & known limitations

- **No database, by design.** Each analysis run is cached in memory
  (`backend/routes.py:ANALYSIS_STORE`) keyed by a short run ID, so results
  persist only until the Flask process restarts. Fine for a local
  demo/presentation; swap in SQLite/Redis if you need persistence.
- **Question segmentation is heuristic.** It's tuned to the standard MU
  layout (`1  Attempt any FOUR`, `2  a  ...`, `b  ...`) seen across the
  sample papers. Unusual layouts fall back to treating the page as one
  question rather than silently dropping it — check the dashboard's
  paper stats if a paper's question count looks too low.
- **OCR quality depends on scan quality.** Heavily skewed, low-DPI, or
  handwritten-over-printed pages may still need a manual text correction
  pass; `backend/ocr_utils.py` applies deskewing and denoising but isn't
  a full document-restoration pipeline.
- **Repeated-question threshold** (`Config.REPEAT_SIMILARITY_THRESHOLD`,
  default `0.80`) and **topic cluster count**
  (`Config.MAX_TOPIC_CLUSTERS`, default `12`) are tunable in `config.py`
  without touching any pipeline code.
