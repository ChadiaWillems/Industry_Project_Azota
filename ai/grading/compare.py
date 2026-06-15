"""
Compare flattened OMR answers to an answer key and produce a grading result.

Typical usage:
    from ai.grading.answer_key import load_answer_key
    from ai.grading.compare import flatten_omr, compare

    key = load_answer_key("answers.xlsx")
    flat = flatten_omr(omr_json)        # omr_json from read_sheet.py
    result = compare(flat, key)
    print(result["score"])              # {"earned": 8, "total": 15}
    print(result["warnings"])           # list of mismatch warnings
"""

import re
from typing import Any


def _cau_number(key: str) -> int | None:
    """Extract the integer from a 'Câu X' key."""
    m = re.search(r'\d+', str(key))
    return int(m.group()) if m else None


def flatten_omr(omr_json: dict) -> dict:
    """Map per-region OMR output into flat global question maps.

    The OMR JSON produced by read_sheet.py stores answers split across multiple
    region dicts (for MCQ) or merged into "Câu X" keys (for T/F and Numeric).
    This function collapses everything into three flat dicts keyed by integer
    question numbers that match the answer key format.

    Returns:
        {
            "MCQ": {1: "A", 2: None, ...},      # None = blank, "MULTIPLE" = conflict
            "TF":  {1: True, 2: False, ...},    # sequential across all Câu groups
            "NUM": {1: "42", 2: None, ...},     # Câu number → value string or None
        }
    """
    sections = omr_json.get("sections", {})
    flat: dict = {"MCQ": {}, "TF": {}, "NUM": {}}

    # MCQ: regions are already globally numbered by _finalize_mcq_numbering.
    for region in sections.get("mcq_region", []):
        for q_str, ans in region.get("answers", {}).items():
            try:
                q = int(q_str)
            except (ValueError, TypeError):
                continue
            flat["MCQ"][q] = ans  # "A"/"B"/"C"/"D"/"MULTIPLE"/None

    # T/F: {"Câu 1": {"a": True, "b": False, ...}, ...}
    # Sub-questions are numbered sequentially across all groups, sorted by Câu number.
    tf_groups = sections.get("true_false_region", {})
    if isinstance(tf_groups, dict):
        sub_num = 1
        letter_order = ["a", "b", "c", "d"]
        for cau_key in sorted(tf_groups.keys(), key=lambda k: (_cau_number(k) or 0)):
            group = tf_groups[cau_key]
            for letter in letter_order:
                if letter in group:
                    flat["TF"][sub_num] = group[letter]  # True/False/"MULTIPLE"/None
                    sub_num += 1

    # Numeric: {"Câu 1": "42", ...} → {1: "42", ...}
    num_groups = sections.get("numeric_region", {})
    if isinstance(num_groups, dict):
        for cau_key, value in num_groups.items():
            n = _cau_number(cau_key)
            if n is not None:
                flat["NUM"][n] = value  # string or None

    return flat


def _normalize_numeric(s: Any) -> float | str | None:
    """Normalise a numeric answer for comparison.

    Returns a float when both sides are parseable, raw string otherwise,
    or None when the value is unresolvable (None / all-'?').
    """
    if s is None:
        return None
    s_str = str(s).strip()
    if not s_str or all(c == "?" for c in s_str):
        return None
    s_str = s_str.replace(",", ".")
    try:
        return float(s_str)
    except ValueError:
        return s_str


def compare(omr_flat: dict, answer_key: dict) -> dict:
    """Compare flattened student answers to the answer key.

    Args:
        omr_flat:   output of flatten_omr()
        answer_key: output of load_answer_key()

    Returns:
        {
            "MCQ": {
                1: {"student": "A", "correct": "C", "is_correct": False},
                ...
            },
            "TF": {
                1: {"student": True, "correct": True, "is_correct": True},
                ...
            },
            "NUM": {
                1: {"student": "42", "correct": "42", "is_correct": True},
                ...
            },
            "score": {"earned": 8, "total": 15},
            "warnings": ["MCQ: questions [12, 13] are in the answer key but not detected ...", ...]
        }

    Scoring: 1 point per question, equal weighting.
    Unanswered (None) and MULTIPLE both score 0, no penalty.
    Numeric answers are compared as floats when both sides parse; string otherwise.
    """
    result: dict = {
        "MCQ": {},
        "TF": {},
        "NUM": {},
        "score": {"earned": 0, "total": 0},
        "warnings": [],
    }
    earned = 0
    total = 0
    warnings: list[str] = []

    for type_key in ("MCQ", "TF", "NUM"):
        student_answers = omr_flat.get(type_key, {})
        correct_answers = answer_key.get(type_key, {})

        in_key_not_omr = sorted(set(correct_answers) - set(student_answers))
        in_omr_not_key = sorted(set(student_answers) - set(correct_answers))

        if in_key_not_omr:
            warnings.append(
                f"{type_key}: questions {in_key_not_omr} are in the answer key but "
                f"not detected in the exam — check that the answer key matches this sheet."
            )
        if in_omr_not_key:
            warnings.append(
                f"{type_key}: questions {in_omr_not_key} were detected in the exam "
                f"but have no answer key entry."
            )

        all_q = sorted(set(student_answers) | set(correct_answers))

        for q in all_q:
            student = student_answers.get(q)
            correct = correct_answers.get(q)

            if correct is None:
                result[type_key][q] = {"student": student, "correct": None, "is_correct": None}
                continue

            total += 1

            if student is None or student == "MULTIPLE":
                is_correct = False
            elif type_key == "NUM":
                s_norm = _normalize_numeric(student)
                c_norm = _normalize_numeric(correct)
                if s_norm is None or c_norm is None:
                    is_correct = False
                elif isinstance(s_norm, float) and isinstance(c_norm, float):
                    is_correct = abs(s_norm - c_norm) < 1e-6
                else:
                    is_correct = str(s_norm) == str(c_norm)
            else:
                is_correct = (student == correct)

            if is_correct:
                earned += 1

            result[type_key][q] = {
                "student": student,
                "correct": correct,
                "is_correct": is_correct,
            }

    result["score"] = {"earned": earned, "total": total}
    result["warnings"] = warnings
    return result
