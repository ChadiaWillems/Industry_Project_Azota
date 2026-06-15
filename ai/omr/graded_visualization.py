"""
Graded bubble visualization for Azota exam sheets.

Colours each bubble according to the grading result from ai/grading/compare.py:
  - Student's correct answer: green circle
  - Student's wrong answer:   red circle
  - Correct answer bubble when student was wrong: green outline
  - No answer (None) or MULTIPLE on MCQ: grey circle
  - Numeric regions: normal fill colours (green=filled, red=empty), no grading
  - Questions not in the grading result: normal fill colours
"""

import cv2
import numpy as np
from pathlib import Path

from bubble_reader import BubbleGrid

# BGR colour palette
_GREEN     = (0, 200, 0)
_RED       = (0, 0, 200)
_GREY      = (160, 160, 160)
_THICKNESS = 2


def _to_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.ndim == 3 and image.shape[2] == 1:
        return cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
    return image.copy()


def _col_indices(grid: BubbleGrid) -> list[int]:
    """Sorted unique column indices across all rows in a filtered grid."""
    return sorted({b.col for row in grid.bubbles for b in row})


def _match_mcq_reading(padded_box: tuple, omr_json: dict) -> dict | None:
    """Return the MCQ reading whose YOLO x2, y2 matches this padded_box.

    padded_box[2] and padded_box[3] are the raw YOLO x2, y2 (not padded),
    matching reading["bbox"][2] and reading["bbox"][3] directly.
    """
    x2, y2 = padded_box[2], padded_box[3]
    for reading in omr_json.get("sections", {}).get("mcq_region", []):
        bbox = reading.get("bbox", [])
        if len(bbox) >= 4 and abs(bbox[2] - x2) < 2 and abs(bbox[3] - y2) < 2:
            return reading
    return None


def _infer_section_type(filtered_grid: BubbleGrid) -> str:
    """Infer T/F vs Numeric from grid shape when MCQ bbox matching failed."""
    cols = _col_indices(filtered_grid)
    if len(cols) <= 2 and filtered_grid.n_rows <= 4:
        return "true_false_region"
    return "numeric_region"


def _draw_region_normal(
    vis: np.ndarray, x_off: int, y_off: int, filtered_grid: BubbleGrid
) -> None:
    """Draw bubbles with standard green (filled) / red (empty) colours."""
    for row in filtered_grid.bubbles:
        for b in row:
            cx = int(b.center_x) + x_off
            cy = int(b.center_y) + y_off
            r = max(1, int(b.radius))
            cv2.circle(vis, (cx, cy), r, _GREEN if b.filled else _RED, _THICKNESS)


def _draw_mcq_region(
    vis: np.ndarray,
    x_off: int,
    y_off: int,
    filtered_grid: BubbleGrid,
    reading: dict,
    mcq_grading: dict,
) -> None:
    """Colour MCQ bubbles per grading result.

    Mapping: filtered_grid.bubbles[i] ↔ q_keys[i] (the i-th question sorted by
    question number in reading["answers"]). Columns map to A/B/C/D via sorted
    global col indices.
    """
    answers = reading.get("answers", {})
    q_keys = sorted(answers.keys(), key=lambda k: int(k))
    cols = _col_indices(filtered_grid)
    col_to_opt = {c: i for i, c in enumerate(cols)}
    options = ["A", "B", "C", "D"]

    n = min(len(q_keys), len(filtered_grid.bubbles))
    for row_idx in range(n):
        q_num = int(q_keys[row_idx])
        row_by_col = {b.col: b for b in filtered_grid.bubbles[row_idx]}
        entry = mcq_grading.get(q_num)

        for col_idx, b in row_by_col.items():
            cx = int(b.center_x) + x_off
            cy = int(b.center_y) + y_off
            r = max(1, int(b.radius))

            opt_idx = col_to_opt.get(col_idx)
            letter = options[opt_idx] if (opt_idx is not None and opt_idx < len(options)) else None

            if entry is None or letter is None:
                cv2.circle(vis, (cx, cy), r, _GREEN if b.filled else _RED, _THICKNESS)
                continue

            student    = entry.get("student")
            correct    = entry.get("correct")
            is_correct = entry.get("is_correct")

            if is_correct is None:
                # No answer key entry for this question.
                cv2.circle(vis, (cx, cy), r, _GREEN if b.filled else _RED, _THICKNESS)
            elif student is None or student == "MULTIPLE":
                cv2.circle(vis, (cx, cy), r, _GREY, _THICKNESS)
            elif is_correct:
                if letter == student:
                    cv2.circle(vis, (cx, cy), r, _GREEN, _THICKNESS)
                # other option bubbles in a correctly-answered row are not drawn
            else:
                if letter == student:
                    cv2.circle(vis, (cx, cy), r, _RED, _THICKNESS)
                elif letter == correct:
                    cv2.circle(vis, (cx, cy), r, _GREEN, _THICKNESS)
                # other irrelevant bubbles in row are not drawn


def _draw_tf_region(
    vis: np.ndarray,
    x_off: int,
    y_off: int,
    filtered_grid: BubbleGrid,
    sub_q_start: int,
    tf_grading: dict,
) -> None:
    """Colour T/F bubbles per grading result.

    The leftmost of the two answer columns = Đúng (True); rightmost = Sai (False).
    Row i in filtered_grid corresponds to sub-question (sub_q_start + i).
    """
    cols = _col_indices(filtered_grid)
    true_col  = cols[0] if cols else None
    false_col = cols[1] if len(cols) > 1 else None

    for row_idx, row in enumerate(filtered_grid.bubbles):
        q_num = sub_q_start + row_idx
        row_by_col = {b.col: b for b in row}
        entry = tf_grading.get(q_num)

        for col_idx, b in row_by_col.items():
            cx = int(b.center_x) + x_off
            cy = int(b.center_y) + y_off
            r = max(1, int(b.radius))

            this_value = (True  if col_idx == true_col  else
                          False if col_idx == false_col else None)

            if entry is None or this_value is None:
                cv2.circle(vis, (cx, cy), r, _GREEN if b.filled else _RED, _THICKNESS)
                continue

            student    = entry.get("student")
            correct    = entry.get("correct")
            is_correct = entry.get("is_correct")

            if is_correct is None:
                cv2.circle(vis, (cx, cy), r, _GREEN if b.filled else _RED, _THICKNESS)
            elif student is None or student == "MULTIPLE":
                cv2.circle(vis, (cx, cy), r, _GREY, _THICKNESS)
            elif is_correct:
                if this_value == student:
                    cv2.circle(vis, (cx, cy), r, _GREEN, _THICKNESS)
            else:
                if this_value == student:
                    cv2.circle(vis, (cx, cy), r, _RED, _THICKNESS)
                elif this_value == correct:
                    cv2.circle(vis, (cx, cy), r, _GREEN, _THICKNESS)


def draw_graded_sheet(
    image: np.ndarray,
    region_grids: list[tuple[tuple, BubbleGrid]],
    omr_json: dict,
    grading_result: dict,
) -> np.ndarray:
    """Draw detected bubbles on the full sheet, coloured by grading result.

    Args:
        image: Full sheet image (grayscale or BGR numpy array).
        region_grids: List of (padded_box, filtered_grid). padded_box is
            (x1, y1, x2, y2) in full-sheet pixel coordinates. filtered_grid is
            a BubbleGrid of answer bubbles only (header row and label columns
            removed by filter_grid_for_section in read_sheet.py).
        omr_json: Full OMR result dict from process_image().
        grading_result: Dict from compare() in ai/grading/compare.py, shaped:
            {"MCQ": {q: {"student": .., "correct": .., "is_correct": ..}},
             "TF":  {q: ...}, "NUM": {q: ...}, "score": {...}, "warnings": [...]}

    Returns:
        BGR numpy array with bubbles coloured:
            Green circle  — student's correct answer
            Red circle    — student's wrong answer
            Green outline — correct answer when student answered wrong
            Grey circles  — unanswered row (None or MULTIPLE)
            Green/Red     — Numeric regions (no grading colour applied)
    """
    vis = _to_bgr(image)

    if not grading_result:
        for padded_box, filtered_grid in region_grids:
            _draw_region_normal(vis, int(padded_box[0]), int(padded_box[1]), filtered_grid)
        return vis

    mcq_grading = grading_result.get("MCQ", {})
    tf_grading  = grading_result.get("TF", {})

    # Separate T/F entries so they can be sorted left-to-right before assigning
    # sequential sub-question numbers.  This ordering must match flatten_omr()
    # which processes Câu groups in ascending Câu number = left-to-right order.
    tf_entries:  list[tuple[tuple, BubbleGrid]] = []
    other_entries: list[tuple[tuple, BubbleGrid, str, dict | None]] = []

    for padded_box, filtered_grid in region_grids:
        reading = _match_mcq_reading(padded_box, omr_json)
        if reading is not None:
            other_entries.append((padded_box, filtered_grid, "mcq_region", reading))
        else:
            stype = _infer_section_type(filtered_grid)
            if stype == "true_false_region":
                tf_entries.append((padded_box, filtered_grid))
            else:
                other_entries.append((padded_box, filtered_grid, stype, None))

    # Sort T/F blocks left-to-right (ascending x1).
    tf_entries.sort(key=lambda e: e[0][0])

    sub_q = 1
    for padded_box, filtered_grid in tf_entries:
        _draw_tf_region(
            vis, int(padded_box[0]), int(padded_box[1]),
            filtered_grid, sub_q, tf_grading,
        )
        sub_q += filtered_grid.n_rows

    for padded_box, filtered_grid, stype, reading in other_entries:
        x_off, y_off = int(padded_box[0]), int(padded_box[1])
        if stype == "mcq_region" and reading is not None:
            _draw_mcq_region(vis, x_off, y_off, filtered_grid, reading, mcq_grading)
        else:
            # Numeric and any unrecognised section: normal fill colours.
            _draw_region_normal(vis, x_off, y_off, filtered_grid)

    return vis


def save_graded_visualization(
    image: np.ndarray,
    region_grids: list[tuple[tuple, BubbleGrid]],
    omr_json: dict,
    grading_result: dict,
    output_path: "Path | str",
) -> Path:
    """Render the graded sheet and write it to output_path as a PNG.

    Args:
        image, region_grids, omr_json, grading_result: see draw_graded_sheet.
        output_path: Destination file path.

    Returns:
        The resolved output Path.
    """
    output_path = Path(output_path)
    vis = draw_graded_sheet(image, region_grids, omr_json, grading_result)
    cv2.imwrite(str(output_path), vis)
    return output_path
