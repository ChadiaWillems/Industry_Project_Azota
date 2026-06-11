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
        return max((len(row) for row in self.bubbles), default=0)

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


def _binarize(gray: np.ndarray) -> np.ndarray:
    """Convert grayscale to binary with dark regions white (inverted for contour finding)."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # blockSize must be odd; scale to crop size so small crops use smaller blocks.
    h, w = gray.shape[:2]
    block = max(11, (min(h, w) // 15) | 1)
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=block,
        C=4,
    )
    return binary


def detect_bubble_grid(
    crop: np.ndarray,
    min_radius: int = 4,
    max_radius: int = 22,
    fill_threshold: float = 0.35,
    circularity_min: float = 0.45,
) -> BubbleGrid:
    """
    Detect bubbles in a cropped region and return them as a 2D grid.

    Args:
        crop: Grayscale or BGR image of the region.
        min_radius: Minimum bubble radius in pixels.
        max_radius: Maximum bubble radius in pixels.
        fill_threshold: Dark-pixel fraction above which a bubble is considered filled.
        circularity_min: Minimum circularity score (0–1) to accept a contour as a bubble.

    Returns:
        BubbleGrid with rows sorted top-to-bottom and columns left-to-right.
    """
    # Normalise to 2D grayscale regardless of input shape.
    # cv2.IMREAD_GRAYSCALE gives (h,w); some pipelines produce (h,w,1) or (h,w,3).
    if crop.ndim == 3:
        if crop.shape[2] == 1:
            gray = crop[:, :, 0]
        else:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop.copy()

    binary = _binarize(gray)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[tuple[float, float, float]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < np.pi * min_radius ** 2 * 0.35:
            continue
        if area > np.pi * max_radius ** 2 * 1.8:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter < 1:
            continue

        circularity = (4 * np.pi * area) / (perimeter ** 2)
        if circularity < circularity_min:
            continue

        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        if not (min_radius <= radius <= max_radius):
            continue

        candidates.append((float(cx), float(cy), float(radius)))

    if not candidates:
        return BubbleGrid(bubbles=[])

    # Remove duplicates: if two candidates are very close together, keep the larger one.
    candidates = _deduplicate_candidates(candidates)

    # Compute fill ratio for each candidate using the original grayscale image.
    bubble_data: list[tuple[float, float, float, float, bool]] = []
    for cx, cy, radius in candidates:
        mask = np.zeros(gray.shape, dtype=np.uint8)
        inner_r = max(1, int(radius * 0.72))
        cv2.circle(mask, (int(cx), int(cy)), inner_r, 255, -1)

        roi_pixels = gray[mask == 255]
        if len(roi_pixels) == 0:
            continue

        # Threshold at 190 (not 128) to catch pencil marks, which are light grey
        # (~140–180) after CLAHE enhancement, not dark ink.
        dark_count = int(np.sum(roi_pixels < 190))
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

    grid: list[list[Bubble]] = []
    for row_idx, row in enumerate(rows_raw):
        row_sorted = sorted(row, key=lambda b: b[0])
        grid.append([
            Bubble(
                row=row_idx,
                col=col_idx,
                center_x=cx,
                center_y=cy,
                radius=radius,
                fill_ratio=fill_ratio,
                filled=filled,
            )
            for col_idx, (cx, cy, radius, fill_ratio, filled) in enumerate(row_sorted)
        ])

    return BubbleGrid(bubbles=grid)


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
            result[q_num] = None
        elif len(filled) == 1:
            idx = filled[0]
            result[q_num] = options[idx] if idx < len(options) else None
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
            result[q_num] = None
        elif len(filled) == 1:
            result[q_num] = (filled[0] == 0)  # col 0 = Đúng/True, col 1 = Sai/False
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
