"""
backend/question_segmenter.py
-------------------------------
Stage 2 of the document pipeline: turn one long block of extracted paper
text into a list of standalone question units.

Mumbai University NLP papers follow a fairly consistent shape:

    1        Attempt any FOUR                                   [20]
    a        What is word sense disambiguation?
    b        Explain reference resolution in detail
    ...
    2   a    Design FST for regular and plural nouns.            [10]
        b    Explain the preprocessing operations in NLP         [10]

Every examinable sub-part becomes its own Question object.  This module
also performs a small amount of OCR/text-layer cleanup so POS-tagging
artifacts, HTML-like sentence markers, hash-like OCR garbage and odd
control/symbol characters do not leak into the dashboard.
"""

import re
import unicodedata

# "2   a   Design FST ..."  -> main number + sub-letter combined on one line
MAIN_AND_SUB_RE = re.compile(r"^\s*Q?\.?\s*(\d{1,2})\s+([a-h])\s*[\.\):]?\s+(\S.*)$")

# "a   What is word sense disambiguation?" -> sub-letter only (continues current main)
SUB_ONLY_RE = re.compile(r"^\s*([a-h])\s*[\.\):]?\s+(\S.*)$")

# "1   Attempt any FOUR" -> main-number-only instruction line
MAIN_ONLY_RE = re.compile(r"^\s*Q?\.?\s*(\d{1,2})\s+(\S.*)$")

# Supports [10], [10M], [10 m], etc.
MARKS_RE = re.compile(r"\[\s*(\d{1,3})\s*[Mm]?\s*\]")

NOISE_LINE_RE = re.compile(
    r"^\s*(N\.?B\.?|Duration|Max\s*Marks|Paper\s*/\s*Subject|QP\s*Code|Prog\.?\s*Code|"
    r"BE\s*/|Page\s+\d+|\*{3,})",
    re.IGNORECASE,
)

# POS-tag suffixes commonly present in pasted/text-layer corpus examples.
# These are removed only when they occur after a word, e.g. students/NN.
POS_SUFFIX_RE = re.compile(
    r"(?<=\w)/(?:NN|NNS|NNP|NNPS|VB|VBD|VBG|VBN|VBP|VBZ|V|DT|JJ|JJR|JJS|"
    r"RB|RBR|RBS|IN|PRP|PRP\$|CC|CD|MD|TO|P|PDT|POS|WDT|WP|WP\$|WRB|EX|UH|RP|SYM)\b",
    re.IGNORECASE,
)

# Sentence boundary markers occasionally survive from tagged corpora.
SENTENCE_TAG_RE = re.compile(r"<\s*/?\s*(?:s|sentence)\s*>", re.IGNORECASE)

# Long hexadecimal/alphanumeric strings are typically OCR artefacts, not
# meaningful question text. The second pattern catches strings containing
# OCR-confused letters such as O in an otherwise hash-like token.
HEX_GARBAGE_RE = re.compile(r"\b[0-9A-Fa-f]{20,}\b")
LONG_ALNUM_GARBAGE_RE = re.compile(
    r"\b(?=[A-Za-z0-9]{24,}\b)(?=[A-Za-z0-9]*\d)(?:[A-Za-z0-9]+)\b"
)

# Symbols seen in OCR output that do not add useful question content.
ODD_SYMBOL_RE = re.compile(r"[©®™�¤§¥≈≠]")


def clean_question_text(text: str) -> str:
    """Return readable question text while preserving normal punctuation."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("\u00a0", " ").replace("\u200b", " ").replace("\ufeff", " ")

    # Remove sentence markers first, then POS suffixes such as /NN and /DT.
    text = SENTENCE_TAG_RE.sub(" ", text)
    text = POS_SUFFIX_RE.sub("", text)

    # Remove long hash/OCR tokens. Re-run after punctuation normalization so
    # an artefact surrounded by punctuation is still recognized.
    text = HEX_GARBAGE_RE.sub(" ", text)
    text = LONG_ALNUM_GARBAGE_RE.sub(" ", text)
    text = ODD_SYMBOL_RE.sub(" ", text)

    # Keep ordinary exam punctuation but discard control characters.
    text = "".join(ch if ch.isprintable() else " " for ch in text)
    text = re.sub(r"\s+", " ", text).strip()

    # Avoid dangling separators left behind by removed tagged tokens.
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([({\[])\s+", r"\1", text)
    text = re.sub(r"\s+([)}\]])", r"\1", text)
    return text.strip(" \t-–—")


class Question:
    """One examinable unit: a single lettered sub-question (or a standalone
    main question that has no sub-parts)."""

    def __init__(self, main_number, sub_label, text, marks, source_file, year):
        self.main_number = main_number
        self.sub_label = sub_label
        self.text = clean_question_text(text)
        self.marks = marks
        self.source_file = source_file
        self.year = year

    @property
    def question_id(self) -> str:
        suffix = f"{self.sub_label}" if self.sub_label else ""
        return f"{self.source_file}::Q{self.main_number}{suffix}"

    @property
    def label(self) -> str:
        suffix = f"({self.sub_label})" if self.sub_label else ""
        return f"Q{self.main_number}{suffix}"

    def to_dict(self) -> dict:
        return {
            "id": self.question_id,
            "label": self.label,
            "main_number": self.main_number,
            "sub_label": self.sub_label,
            "text": self.text,
            "marks": self.marks,
            "source_file": self.source_file,
            "year": self.year,
        }


def _extract_marks(text: str):
    match = MARKS_RE.search(text)
    if match:
        return int(match.group(1)), MARKS_RE.sub("", text).strip()
    return None, text


def segment_questions(full_text: str, source_file: str, year: str) -> list:
    """Parse raw paper text into a flat list of Question objects."""
    lines = [ln.rstrip() for ln in full_text.splitlines()]

    questions = []
    current_main = None
    current_sub = None
    buffer = []

    def flush():
        if current_main is None or not buffer:
            return
        raw_text = " ".join(buffer).strip()
        if not raw_text:
            return
        marks, clean_text = _extract_marks(raw_text)
        clean_text = clean_question_text(clean_text)
        if not clean_text:
            return
        # Skip pure instruction lines like "Attempt any FOUR" with no real
        # question content - they carry no NLP signal of their own.
        if current_sub is None and len(clean_text.split()) <= 4:
            return
        questions.append(
            Question(current_main, current_sub, clean_text, marks, source_file, year)
        )

    for line in lines:
        if not line.strip() or NOISE_LINE_RE.match(line):
            continue

        combined = MAIN_AND_SUB_RE.match(line)
        sub_only = SUB_ONLY_RE.match(line) if not combined else None
        main_only = MAIN_ONLY_RE.match(line) if not combined and not sub_only else None

        if combined:
            flush()
            current_main, current_sub = combined.group(1), combined.group(2)
            buffer = [combined.group(3)]
        elif sub_only and current_main is not None:
            flush()
            current_sub = sub_only.group(1)
            buffer = [sub_only.group(2)]
        elif main_only and _looks_like_new_main_question(line, main_only):
            flush()
            current_main, current_sub = main_only.group(1), None
            buffer = [main_only.group(2)]
        else:
            if current_main is not None:
                buffer.append(line.strip())

    flush()

    if not questions:
        cleaned = clean_question_text(" ".join(l.strip() for l in lines if l.strip()))
        if cleaned:
            questions.append(Question("1", None, cleaned, None, source_file, year))

    return questions


def _looks_like_new_main_question(line: str, match: re.Match) -> bool:
    """Mumbai University papers normally use no more than ~6 main questions."""
    number = int(match.group(1))
    return 1 <= number <= 9
