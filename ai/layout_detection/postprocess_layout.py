"""
Post-process YOLO layout detections for Azota exam sheets.

Raw YOLO detections are treated as proposals.
This file cleans them using document-specific rules, for example:
- use class-specific confidence thresholds
- keep only one student_info_region
- keep only one candidate_id_region
- keep only one exam_code_region
- keep only four main registration markers
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class Detection:
    class_name: str
    confidence: float
    box: Tuple[float, float, float, float]  # x1, y1, x2, y2


MIN_CONF_BY_CLASS: Dict[str, float] = {
    "candidate_id_region": 0.60,
    "exam_code_region": 0.60,
    "student_info_region": 0.60,
    "mcq_region": 0.50,
    "true_false_region": 0.60,
    "numeric_region": 0.60,
    "essay_region": 0.60,
    "score_field_region": 0.50,
    "registration_marker": 0.35,
}


SINGLE_INSTANCE_CLASSES = {
    "student_info_region",
    "candidate_id_region",
    "exam_code_region",
    "essay_region",
    "score_field_region",
}


def box_center(box: Tuple[float, float, float, float]) -> Tuple[float, float]:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, (y1 + y2) / 2


def box_area(box: Tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)

def box_iou(
    box_a: Tuple[float, float, float, float],
    box_b: Tuple[float, float, float, float],
) -> float:
    """
    Calculate IoU between two boxes.

    IoU = intersection area / union area.
    If IoU is high, the boxes are mostly covering the same region.
    """
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_width = max(0, inter_x2 - inter_x1)
    inter_height = max(0, inter_y2 - inter_y1)
    intersection_area = inter_width * inter_height

    area_a = box_area(box_a)
    area_b = box_area(box_b)

    union_area = area_a + area_b - intersection_area

    if union_area == 0:
        return 0.0

    return intersection_area / union_area

def filter_by_confidence(detections: List[Detection]) -> List[Detection]:
    filtered = []

    for det in detections:
        min_conf = MIN_CONF_BY_CLASS.get(det.class_name, 0.50)

        if det.confidence >= min_conf:
            filtered.append(det)

    return filtered


def keep_best_single_instances(detections: List[Detection]) -> List[Detection]:
    """
    For classes that should usually appear once, keep only the highest-confidence box.
    Example: student_info_region should not appear twice.
    """
    best_by_class: Dict[str, Detection] = {}
    remaining: List[Detection] = []

    for det in detections:
        if det.class_name in SINGLE_INSTANCE_CLASSES:
            current_best = best_by_class.get(det.class_name)

            if current_best is None or det.confidence > current_best.confidence:
                best_by_class[det.class_name] = det
        else:
            remaining.append(det)

    remaining.extend(best_by_class.values())
    return remaining


def keep_four_corner_registration_markers(
    detections: List[Detection],
    image_width: int,
    image_height: int,
) -> List[Detection]:
    """
    Keep at most one registration marker per page corner.

    This does not require perfect detections.
    If YOLO detects too many black squares, this selects the marker closest
    to each page corner.
    """
    non_markers = [
        det for det in detections
        if det.class_name != "registration_marker"
    ]

    markers = [
        det for det in detections
        if det.class_name == "registration_marker"
    ]

    if not markers:
        return non_markers

    corners = {
        "top_left": (0, 0),
        "top_right": (image_width, 0),
        "bottom_left": (0, image_height),
        "bottom_right": (image_width, image_height),
    }

    selected_markers: List[Detection] = []

    for _, corner_point in corners.items():
        corner_x, corner_y = corner_point

        best_marker = None
        best_score = None

        for marker in markers:
            center_x, center_y = box_center(marker.box)

            distance_to_corner = (
                (center_x - corner_x) ** 2
                + (center_y - corner_y) ** 2
            ) ** 0.5

            # Lower score is better.
            # Confidence helps when two markers are similarly close.
            score = distance_to_corner - (marker.confidence * 50)

            if best_score is None or score < best_score:
                best_marker = marker
                best_score = score

        if best_marker is not None and best_marker not in selected_markers:
            selected_markers.append(best_marker)

    return non_markers + selected_markers

def remove_overlapping_conflicting_regions(
    detections: List[Detection],
    iou_threshold: float = 0.80,
) -> List[Detection]:
    """
    Remove detections that strongly overlap with another detection.

    Example:
    If the same bottom-right region is detected as both numeric_region
    and mcq_region, keep the higher-confidence detection.
    """
    sorted_detections = sorted(
        detections,
        key=lambda det: det.confidence,
        reverse=True,
    )

    kept: List[Detection] = []

    for det in sorted_detections:
        should_keep = True

        for kept_det in kept:
            overlap = box_iou(det.box, kept_det.box)

            if overlap >= iou_threshold:
                should_keep = False
                break

        if should_keep:
            kept.append(det)

    return kept

def postprocess_detections(
    detections: List[Detection],
    image_width: int,
    image_height: int,
) -> List[Detection]:
    """
    Main function to clean YOLO detections.
    """
    detections = filter_by_confidence(detections)

    detections = remove_overlapping_conflicting_regions(
        detections,
        iou_threshold=0.80,
    )

    detections = keep_best_single_instances(detections)

    detections = keep_four_corner_registration_markers(
        detections,
        image_width=image_width,
        image_height=image_height,
    )

    return detections