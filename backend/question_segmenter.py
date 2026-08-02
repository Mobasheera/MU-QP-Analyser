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

i.e. a main question number (1-6), each carrying lettered sub-parts
(a, b, c, ...), often with a marks allocation in square brackets, and
sub-question text that can run across several lines until the next
letter or number appears. This module never looks at whole PDFs as one
blob - every sub-part becomes its own Question object, which is what the
rest of the NLP pipeline (nlp/pipeline.py) actually analyzes.
"""

import re

# "2   a   Design FST ..."  -> main number + sub-letter combined on one line
MAIN_AND_SUB_RE = re.compile(r"^\s*Q?\.?\s*(\d{1,2})\s+([a-h])\s*[\.\):]?\s+(\S.*)$")

# "a   What is word sense disambiguation?" -> sub-letter only (continues current main)
SUB_ONLY_RE = re.compile(r"^\s*([a-h])\s*[\.\):]?\s+(\S.*)$")

# "1   Attempt any FOUR   [20]" -> main-number-only instruction line
MAIN_ONLY_RE = re.compile(r"^\s*Q?\.?\s*(\d{1,2})\s+(\S.*)$")

MARKS_RE = re.compile(r"\[\s*(\d{1,3})\s*\]")

# Lines that are pure noise: page furniture, exam instructions, signatures.
NOISE_LINE_RE = re.compile(
    r"^\s*(N\.?B\.?|Duration|Max\s*Marks|Paper\s*/\s*Subject|QP\s*Code|Prog\.?\s*Code|"
    r"BE\s*/|Page\s+\d+|\*{3,})",
    re.IGNORECASE,
)


class Question:
    """One examinable unit: a single lettered sub-question (or a standalone
    main question that has no sub-parts)."""

    def __init__(self, main_number, sub_label, text, marks, source_file, year):
        self.main_number = main_number
        self.sub_label = sub_label
        self.text = text.strip()
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
    """
    Parse raw paper text into a flat list of Question objects.
    Falls back to treating the whole page as one question if nothing
    matches the expected pattern, so a paper with an unusual layout still
    produces usable output instead of an empty result.
    """
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
            # Continuation of whatever sub-question we're currently building.
            if current_main is not None:
                buffer.append(line.strip())

    flush()

    if not questions:
        # Fallback: no recognizable structure found (unusual layout / heavy
        # OCR noise) - keep the paper's text as a single analyzable unit
        # rather than silently dropping it.
        cleaned = " ".join(l.strip() for l in lines if l.strip())
        if cleaned:
            questions.append(Question("1", None, cleaned, None, source_file, year))

    return questions


def _looks_like_new_main_question(line: str, match: re.Match) -> bool:
    """
    Guards against false positives such as a stray "80" (max marks) or a
    year-like number being mistaken for a new main question number. Mumbai
    University papers only go up to ~6 main questions per paper.
    """
    number = int(match.group(1))
    return 1 <= number <= 9
