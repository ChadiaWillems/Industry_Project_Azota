"""
OMR bubble reader for Azota exam sheets.

Detects which bubbles are filled in a cropped region and interprets the result
based on the section type (MCQ, true/false, numeric).

Images are standardized A4 at 1240x1754px, so bubbles are roughly 8-20px radius
in raw crops.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class Bubble:
    row: int
    col: int
    center_x: float
    center_y: float
    radius: float
    fill_ratio: float
    filled: bool


@dataclass
class BubbleGrid:
    bubbles: list[list[Bubble]]  # [row][col]

    @property
    def n_rows(self) -> int:
        return len(self.bubbles)

    @property
    def n_cols(self) -> int:
        all_cols = {b.col for row in self.bubbles for b in row}
        return max(all_cols, default=-1) + 1

    def filled_in_row(self, row_idx: int) -> list[int]:
        if row_idx >= len(self.bubbles):
            return []
        return [b.col for b in self.bubbles[row_idx] if b.filled]

    def filled_in_col(self, col_idx: int) -> list[int]:
        result = []
        for row in self.bubbles:
            for b in row:
                if b.col == col_idx and b.filled:
                    result.append(b.row)
        return result


def _binarize(gray: np.ndarray, debug_path: str | None = None) -> np.ndarray:
    """Convert grayscale to binary with dark regions white (inverted for contour finding)."""
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    # blockSize must be odd; scale to crop size so small crops use smaller blocks.
    h, w = gray.shape[:2]
    block = max(11, (min(h, w) // 15) | 1)
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=block,
        C=2,
    )
    # Close small gaps in circle outlines so fragmented arcs merge into
    # complete rings. Thin printed circles get broken into arc segments by
    # thresholding; closing reconnects them so contour detection works.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    if debug_path is not None:
        cv2.imwrite(debug_path, binary)
    return binary


def detect_bubble_grid(
    crop: np.ndarray,
    min_radius: int = 4,
    max_radius: int = 22,
    fill_threshold: float = 0.35,
    circularity_min: float = 0.35,  # kept for API compatibility, not used by Hough
    _debug_binary_path: str | None = None,
) -> BubbleGrid:
    """
    Detect bubbles in a cropped region and return them as a 2D grid.

    Args:
        crop: Grayscale or BGR image of the region.
        min_radius: Minimum bubble radius in pixels.
        max_radius: Maximum bubble radius in pixels.
        fill_threshold: Dark-pixel fraction above which a bubble is considered filled.

    Returns:
        BubbleGrid with rows sorted top-to-bottom and columns left-to-right.
    """
    # Normalise to 2D grayscale regardless of input shape.
    if crop.ndim == 3:
        if crop.shape[2] == 1:
            gray = crop[:, :, 0]
        else:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop.copy()

    # Save binary debug image if requested.
    if _debug_binary_path is not None:
        _binarize(gray, debug_path=_debug_binary_path)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adapt sensitivity to image quality: darker paper (photocopies, phone photos)
    # needs a lower accumulator threshold so faint circle outlines are still found.
    # Formula: param2 ≈ paper_brightness * 0.10, clamped [12, 25].
    # bright scans (paper ~230): param2 ≈ 23  — confident, few false positives
    # phone photos (paper ~200): param2 ≈ 20
    # grey photocopy (paper ~150): param2 ≈ 15
    paper_brightness = float(np.percentile(gray, 90))
    param2 = int(np.clip(paper_brightness * 0.10, 12, 25))

    hough = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=max(int(min_radius * 2), 8),
        param1=50,
        param2=param2,
        minRadius=min_radius,
        maxRadius=max_radius,
    )

    candidates: list[tuple[float, float, float]] = []
    if hough is not None:
        for cx, cy, r in hough[0]:
            candidates.append((float(cx), float(cy), float(r)))

    if not candidates:
        return BubbleGrid(bubbles=[])

    # Remove duplicates: if two candidates are very close together, keep the larger one.
    candidates = _deduplicate_candidates(candidates)

    # Compute fill ratio for each candidate using the original grayscale image.
    # Use an adaptive dark threshold: 85% of the crop's 90th-percentile brightness
    # (≈ paper brightness). This handles phone photos where CLAHE pushes the paper
    # to ~180 px — a fixed threshold of 190 would falsely count empty bubbles as dark.
    # Cap at 190 (the calibrated threshold for clean scans) so we only adapt DOWN
    # for dark images, never UP — raising it above 190 causes false fills on bright scans.
    paper_brightness = float(np.percentile(gray, 90))
    dark_threshold = int(np.clip(paper_brightness * 0.85, 120, 190))

    bubble_data: list[tuple[float, float, float, float, bool]] = []
    for cx, cy, radius in candidates:
        mask = np.zeros(gray.shape, dtype=np.uint8)
        inner_r = max(1, int(radius * 0.72))
        cv2.circle(mask, (int(cx), int(cy)), inner_r, 255, -1)

        roi_pixels = gray[mask == 255]
        if len(roi_pixels) == 0:
            continue

        dark_count = int(np.sum(roi_pixels < dark_threshold))
        fill_ratio = dark_count / len(roi_pixels)
        bubble_data.append((cx, cy, radius, fill_ratio, fill_ratio >= fill_threshold))

    if not bubble_data:
        return BubbleGrid(bubbles=[])

    # Cluster into rows by Y coordinate using gap-based splitting.
    bubble_data.sort(key=lambda b: b[1])
    median_r = float(np.median([b[2] for b in bubble_data]))
    row_gap = median_r * 1.4

    rows_raw: list[list] = []
    current_row = [bubble_data[0]]
    for b in bubble_data[1:]:
        # Compare against the mean Y of the current row (more stable than last element).
        mean_y = sum(x[1] for x in current_row) / len(current_row)
        if b[1] - mean_y > row_gap:
            rows_raw.append(current_row)
            current_row = [b]
        else:
            current_row.append(b)
    rows_raw.append(current_row)

    # Cluster all detected X positions into global column groups so that col
    # indices are consistent across rows even when circles are missing in some
    # rows (e.g. the row-label column is undetected in the top rows of a numeric
    # section). Without this, a row missing its leftmost circle has all remaining
    # circles shifted down by one col index, making column-based reading unreliable.
    all_xs = sorted({cx for row in rows_raw for cx, *_ in row})
    x_groups: list[list[float]] = [[all_xs[0]]]
    for x in all_xs[1:]:
        if x - float(np.mean(x_groups[-1])) > row_gap:
            x_groups.append([x])
        else:
            x_groups[-1].append(x)
    col_centers = [float(np.mean(g)) for g in x_groups]

    def _assign_col(cx: float) -> int:
        return min(range(len(col_centers)), key=lambda i: abs(cx - col_centers[i]))

    grid: list[list[Bubble]] = []
    for row_idx, row in enumerate(rows_raw):
        row_sorted = sorted(row, key=lambda b: b[0])
        grid.append([
            Bubble(
                row=row_idx,
                col=_assign_col(cx),
                center_x=cx,
                center_y=cy,
                radius=radius,
                fill_ratio=fill_ratio,
                filled=filled,
            )
            for (cx, cy, radius, fill_ratio, filled) in row_sorted
        ])

    # Snap each bubble's display position to (median_col_x, median_row_y).
    # HoughCircles centers are typically 2-4 px off; the column/row median
    # across all bubbles in a section is a more stable estimate of the true
    # grid position. We update center_x/center_y for clean visualization but
    # keep the original fill_ratio so that sheets with slight physical curvature
    # do not cause fill-mask regressions.
    row_ys: dict[int, list[float]] = {}
    col_xs: dict[int, list[float]] = {}
    for row in grid:
        for b in row:
            row_ys.setdefault(b.row, []).append(b.center_y)
            col_xs.setdefault(b.col, []).append(b.center_x)
    reg_row_y = {r: float(np.median(ys)) for r, ys in row_ys.items()}
    reg_col_x = {c: float(np.median(xs)) for c, xs in col_xs.items()}
    all_radii = [b.radius for row in grid for b in row]
    reg_radius = float(np.median(all_radii)) if all_radii else median_r

    snapped: list[list[Bubble]] = []
    for row in grid:
        new_row: list[Bubble] = []
        for b in row:
            new_row.append(Bubble(
                row=b.row, col=b.col,
                center_x=reg_col_x.get(b.col, b.center_x),
                center_y=reg_row_y.get(b.row, b.center_y),
                radius=reg_radius,
                fill_ratio=b.fill_ratio,
                filled=b.filled,
            ))
        snapped.append(new_row)

    return BubbleGrid(bubbles=snapped)


def _deduplicate_candidates(
    candidates: list[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    """Remove near-duplicate detections by keeping the larger circle when two overlap."""
    # Sort largest first so we keep the more-representative circle.
    sorted_c = sorted(candidates, key=lambda c: c[2], reverse=True)
    kept: list[tuple[float, float, float]] = []
    for cx, cy, r in sorted_c:
        too_close = any(
            ((cx - kx) ** 2 + (cy - ky) ** 2) ** 0.5 < (r + kr) * 0.5
            for kx, ky, kr in kept
        )
        if not too_close:
            kept.append((cx, cy, r))
    return kept


# ── Section interpreters ───────────────────────────────────────────────────────

_MCQ_OPTIONS = ["A", "B", "C", "D"]


def filter_grid_for_section(
    grid: BubbleGrid,
    section_type: str,
    n_options: int = 4,
) -> BubbleGrid:
    """
    Return only the bubbles that are actual answer positions for this section.

    Removes:
    - Row 0 in MCQ / true-false: the A/B/C/D or Đ/S printed-label row at the top.
    - Extra left columns in MCQ / true-false: question-number circles (e.g. "10" → "0").
    - Column 0 in numeric: the printed row-label circles (-, ,, 0–9).

    Used for both visualization (so false-positive circles aren't drawn) and
    interpretation (consistent question numbering starting from 1).
    """
    if section_type == "mcq_region":
        rows = []
        for row_idx, row in enumerate(grid.bubbles):
            if row_idx == 0:
                continue  # printed A/B/C/D header row
            if len(row) < n_options:
                continue
            rows.append(row[-n_options:])
        return BubbleGrid(bubbles=rows)

    if section_type == "true_false_region":
        rows = []
        for row_idx, row in enumerate(grid.bubbles):
            if row_idx == 0:
                continue  # printed Đ/S header row
            if len(row) < 2:
                continue
            rows.append(row[-2:])
        return BubbleGrid(bubbles=rows)

    if section_type == "numeric_region" and grid.n_cols > 1:
        # Column 0 holds the printed row-label circles (-, ,, 0-9); skip them.
        rows = [[b for b in row if b.col > 0] for row in grid.bubbles]
        rows = [row for row in rows if row]
        return BubbleGrid(bubbles=rows)

    return grid


def read_mcq_region(
    crop: np.ndarray,
    n_options: int = 4,
    **kwargs,
) -> dict[int, Optional[str]]:
    """
    Read an MCQ region.

    Row 0 is always the printed A/B/C/D header — skipped automatically.
    The rightmost n_options columns per row are the answer bubbles.
    Question numbers start at 1.

    Returns:
        {question_number: "A"|"B"|"C"|"D"|"MULTIPLE"|None}
    """
    grid = detect_bubble_grid(crop, **kwargs)
    options = _MCQ_OPTIONS[:n_options]
    result: dict[int, Optional[str]] = {}
    q_num = 0

    for row_idx, row in enumerate(grid.bubbles):
        if row_idx == 0:
            continue  # skip printed A/B/C/D header row
        if len(row) < n_options:
            continue

        q_num += 1
        option_bubbles = row[-n_options:]
        filled = [i for i, b in enumerate(option_bubbles) if b.filled]

        if len(filled) == 0:
            # Best-match fallback: pick the clearly dominant bubble if nothing
            # crossed fill_threshold (handles light pencil marks in phone photos).
            ratios = sorted(
                ((b.fill_ratio, i) for i, b in enumerate(option_bubbles)),
                reverse=True,
            )
            best_r, best_i = ratios[0]
            second_r = ratios[1][0] if len(ratios) > 1 else 0.0
            if best_r >= 0.15 and best_r >= max(second_r * 1.5, second_r + 0.05):
                result[q_num] = options[best_i] if best_i < len(options) else None
            else:
                result[q_num] = None
        elif len(filled) == 1:
            idx = filled[0]
            result[q_num] = options[idx] if idx < len(options) else None
        else:
            # Multiple bubbles above threshold: resolve to the dominant one if its
            # fill_ratio is at least 2× the second-highest, OR if the absolute
            # difference is ≥ 0.15 (catches ratio < 2× cases like 0.6 vs 0.4).
            filled_ratios = sorted(
                ((option_bubbles[i].fill_ratio, i) for i in filled),
                reverse=True,
            )
            top_r, top_i = filled_ratios[0]
            sec_r = filled_ratios[1][0]
            if top_r >= sec_r * 2.0 or (top_r - sec_r) >= 0.15:
                result[q_num] = options[top_i] if top_i < len(options) else None
            else:
                result[q_num] = "MULTIPLE"

    return result


def read_true_false_region(
    crop: np.ndarray,
    **kwargs,
) -> dict[int, Optional[bool | str]]:
    """
    Read a true/false region.

    Row 0 is the printed header row (Đúng/Sai labels) — skipped automatically.
    The rightmost 2 columns per row are [Đúng, Sai].
    Question numbers start at 1.

    Returns:
        {question_number: True|False|"MULTIPLE"|None}
    """
    grid = detect_bubble_grid(crop, **kwargs)
    result: dict[int, Optional[bool | str]] = {}
    q_num = 0

    for row_idx, row in enumerate(grid.bubbles):
        if row_idx == 0:
            continue  # skip printed header row
        if len(row) < 2:
            continue

        q_num += 1
        option_bubbles = row[-2:]
        filled = [i for i, b in enumerate(option_bubbles) if b.filled]

        if len(filled) == 0:
            # Best-match fallback: same logic as MCQ.
            ratios = sorted(
                ((b.fill_ratio, i) for i, b in enumerate(option_bubbles)),
                reverse=True,
            )
            best_r, best_i = ratios[0]
            second_r = ratios[1][0] if len(ratios) > 1 else 0.0
            if best_r >= 0.15 and best_r >= max(second_r * 1.5, second_r + 0.05):
                result[q_num] = (best_i == 0)
            else:
                result[q_num] = None
        elif len(filled) == 1:
            result[q_num] = (filled[0] == 0)  # col 0 = Đúng/True, col 1 = Sai/False
        else:
            # Resolve MULTIPLE if one bubble clearly dominates (2× ratio or ≥0.15 difference).
            filled_ratios = sorted(
                ((option_bubbles[i].fill_ratio, i) for i in filled),
                reverse=True,
            )
            top_r, top_i = filled_ratios[0]
            sec_r = filled_ratios[1][0]
            if top_r >= sec_r * 2.0 or (top_r - sec_r) >= 0.15:
                result[q_num] = (top_i == 0)
            else:
                result[q_num] = "MULTIPLE"

    return result


# Row labels for numeric regions.
# Some templates have: -, ',', 0–9 (comma = decimal separator before digits).
# Others have just: -, 0–9.
_NUMERIC_ROW_LABELS = ["-", ",", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


def read_numeric_region(crop: np.ndarray, **kwargs) -> Optional[str]:
    """
    Read a numeric region.

    Column 0 is the printed row-label column (-, ,, 0–9) — skipped automatically.
    Remaining columns left→right represent digit positions.
    Rows top→bottom map to _NUMERIC_ROW_LABELS.

    Returns the answer as a string (e.g. "-12", "3") or None if no bubbles found.
    Positions with no filled bubble or multiple filled bubbles are shown as "?".
    """
    grid = detect_bubble_grid(crop, **kwargs)
    if grid.n_cols == 0:
        return None

    # Skip column 0 (printed row-label circles for -, ,, 0-9).
    start_col = 1 if grid.n_cols > 1 else 0

    digits: list[str] = []
    for col_idx in range(start_col, grid.n_cols):
        filled_rows = grid.filled_in_col(col_idx)
        if len(filled_rows) == 1:
            row = filled_rows[0]
            label = _NUMERIC_ROW_LABELS[row] if row < len(_NUMERIC_ROW_LABELS) else "?"
            digits.append(label)
        elif len(filled_rows) == 0:
            # Best-match fallback: nothing crossed fill_threshold, but pick the
            # most-filled bubble if it clearly dominates the others.
            col_bubbles = sorted(
                [b for row in grid.bubbles for b in row if b.col == col_idx],
                key=lambda b: b.fill_ratio,
                reverse=True,
            )
            if col_bubbles and col_bubbles[0].fill_ratio >= 0.18:
                second = col_bubbles[1].fill_ratio if len(col_bubbles) > 1 else 0.0
                if col_bubbles[0].fill_ratio >= max(second * 1.5, second + 0.05):
                    row_idx = col_bubbles[0].row
                    label = _NUMERIC_ROW_LABELS[row_idx] if row_idx < len(_NUMERIC_ROW_LABELS) else "?"
                    digits.append(label)
                else:
                    digits.append("?")
            else:
                digits.append("?")
        else:
            digits.append("?")

    return "".join(digits) if digits else None


def read_region(crop: np.ndarray, section_type: str, **kwargs) -> dict:
    """
    Unified entry point: read a cropped region and return structured results.

    Args:
        crop: Cropped image of the region.
        section_type: "mcq_region", "true_false_region", or "numeric_region".
        **kwargs: Forwarded to detect_bubble_grid (e.g. fill_threshold).

    Returns:
        dict with "section_type" plus section-specific keys:
            mcq_region       → {"answers": {q_num: option|None}}
            true_false_region → {"answers": {q_num: bool|None}}
            numeric_region   → {"value": "123"|None}
            other            → {"grid": [[bool, ...], ...]}
    """
    if section_type == "mcq_region":
        return {"section_type": section_type, "answers": read_mcq_region(crop, **kwargs)}

    if section_type == "true_false_region":
        return {"section_type": section_type, "answers": read_true_false_region(crop, **kwargs)}

    if section_type == "numeric_region":
        return {"section_type": section_type, "value": read_numeric_region(crop, **kwargs)}

    grid = detect_bubble_grid(crop, **kwargs)
    raw = [[b.filled for b in row] for row in grid.bubbles]
    return {"section_type": section_type, "grid": raw}


# ── Debug visualization ────────────────────────────────────────────────────────

def draw_bubble_grid(crop: np.ndarray, grid: BubbleGrid) -> np.ndarray:
    """
    Draw detected bubbles on a copy of the crop for visual debugging.

    Green circle  = filled bubble
    Red circle    = empty bubble
    Numbers show (row, col) indices.
    """
    if crop.ndim == 2:
        vis = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    elif crop.ndim == 3 and crop.shape[2] == 1:
        vis = cv2.cvtColor(crop[:, :, 0], cv2.COLOR_GRAY2BGR)
    else:
        vis = crop.copy()

    for row in grid.bubbles:
        for b in row:
            color = (0, 200, 0) if b.filled else (0, 0, 200)
            cv2.circle(vis, (int(b.center_x), int(b.center_y)), int(b.radius), color, 1)
            cv2.putText(
                vis,
                f"{b.row},{b.col}",
                (int(b.center_x) - 8, int(b.center_y) + 3),
                cv2.FONT_HERSHEY_PLAIN,
                0.6,
                color,
                1,
                cv2.LINE_AA,
            )

    return vis


def draw_sheet_with_bubbles(
    image: np.ndarray,
    region_grids: list[tuple[tuple, BubbleGrid]],
    thickness: int = 2,
) -> np.ndarray:
    """
    Draw all detected bubbles from every region onto the full sheet image.

    Bubble coordinates are stored relative to each crop, so the crop's top-left
    corner (x1, y1) from the YOLO bounding box is added back here.

    Args:
        image: Full sheet image (grayscale or BGR).
        region_grids: List of (bbox, grid) where bbox is (x1, y1, x2, y2).
        thickness: Circle stroke thickness in pixels.

    Returns:
        BGR image of the full sheet with green (filled) and red (empty) circles.
    """
    if image.ndim == 2:
        vis = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 1:
        vis = cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
    else:
        vis = image.copy()

    for (x1, y1, _x2, _y2), grid in region_grids:
        x_off, y_off = int(x1), int(y1)
        for row in grid.bubbles:
            for b in row:
                cx = int(b.center_x) + x_off
                cy = int(b.center_y) + y_off
                r = max(1, int(b.radius))
                color = (0, 200, 0) if b.filled else (0, 0, 200)
                cv2.circle(vis, (cx, cy), r, color, thickness)

    return vis
