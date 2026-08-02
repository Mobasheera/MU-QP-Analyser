"""
backend/routes.py
--------------------
All Flask routes for the app. No database is used (per the project
brief) - each analysis run's results are cached in-memory in
ANALYSIS_STORE, keyed by a short run_id, for the lifetime of the Flask
process. This is fine for a local single-user demo/presentation; see the
README for how you'd swap in persistence if needed later.
"""

import os
import traceback

from flask import Blueprint, current_app, jsonify, render_template, request

from backend.pdf_processor import extract_document
from backend.question_segmenter import segment_questions
from nlp.pipeline import inspect_question, run_pipeline
from nlp.similarity import most_similar_to
from utils.file_utils import allowed_file, guess_academic_year, unique_upload_path
from utils.logger import get_logger

logger = get_logger(__name__)

bp = Blueprint("main", __name__)

# In-memory cache of completed analysis runs: run_id -> pipeline result dict.
ANALYSIS_STORE = {}


@bp.route("/")
def landing():
    return render_template("index.html")


@bp.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("papers")

    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files were selected."}), 400

    papers_meta = []
    all_questions = []

    for uploaded_file in files:
        if not uploaded_file or uploaded_file.filename == "":
            continue
        if not allowed_file(uploaded_file.filename):
            return jsonify({"error": f"'{uploaded_file.filename}' is not a PDF."}), 400

        save_path = unique_upload_path(uploaded_file.filename)
        uploaded_file.save(save_path)

        try:
            extraction = extract_document(save_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to extract '%s': %s", uploaded_file.filename, exc)
            logger.error(traceback.format_exc())
            return jsonify({"error": f"Could not read '{uploaded_file.filename}': {exc}"}), 500

        year = guess_academic_year(uploaded_file.filename, extraction["full_text"])
        questions = segment_questions(
            extraction["full_text"], uploaded_file.filename, year
        )

        papers_meta.append(
            {
                "filename": uploaded_file.filename,
                "year": year,
                "page_count": extraction["page_count"],
                "ocr_used": extraction["ocr_used"],
                "question_count": len(questions),
            }
        )
        all_questions.extend(q.to_dict() for q in questions)

    if not all_questions:
        return jsonify({"error": "No questions could be extracted from the uploaded PDFs."}), 422

    try:
        result = run_pipeline(all_questions, papers_meta)
    except Exception as exc:  # noqa: BLE001
        logger.error("Pipeline failed: %s", exc)
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Analysis failed: {exc}"}), 500

    ANALYSIS_STORE[result["run_id"]] = result

    return jsonify({"run_id": result["run_id"]})


@bp.route("/dashboard/<run_id>")
def dashboard(run_id):
    result = ANALYSIS_STORE.get(run_id)
    if not result:
        return render_template("index.html", error="That analysis run was not found. Please upload again."), 404
    return render_template("dashboard.html", data=result)


@bp.route("/api/analysis/<run_id>")
def api_analysis(run_id):
    result = ANALYSIS_STORE.get(run_id)
    if not result:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(result)


@bp.route("/api/question/<run_id>/<path:question_id>")
def api_question_inspect(run_id, question_id):
    result = ANALYSIS_STORE.get(run_id)
    if not result:
        return jsonify({"error": "Run not found"}), 404

    question = next((q for q in result["questions"] if q["id"] == question_id), None)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    try:
        details = inspect_question(question)
    except Exception as exc:  # noqa: BLE001
        logger.error("Inspection failed for %s: %s", question_id, exc)
        return jsonify({"error": str(exc)}), 500

    return jsonify({"question": question, "analysis": details})


@bp.route("/api/search/<run_id>")
def api_search(run_id):
    result = ANALYSIS_STORE.get(run_id)
    if not result:
        return jsonify({"error": "Run not found"}), 404

    query = request.args.get("q", "").strip()
    mode = request.args.get("mode", "keyword")  # "keyword" or "semantic"

    if not query:
        return jsonify({"results": []})

    if mode == "semantic":
        matches = most_similar_to(query, result["questions"], top_k=10)
        matches = [m for m in matches if m["similarity"] >= 40]
    else:
        query_lower = query.lower()
        matches = [
            q for q in result["questions"]
            if query_lower in q["text"].lower()
        ]

    return jsonify({"results": matches})
