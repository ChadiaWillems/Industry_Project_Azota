"""
Crop detected regions from a full exam sheet image.

Takes YOLO detections (already post-processed) and returns tight crops for each
gradable section type, sorted top-to-bottom by position on the page.
"""

import cv2
import numpy as np
from typing import NamedTuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "layout_detection"))
from postprocess_layout import Detection


# Section types that the OMR reader handles.
GRADABLE_SECTION_TYPES = {"mcq_region", "true_false_region", "numeric_region"}


class RegionCrop(NamedTuple):
    detection: Detection
    crop: np.ndarray


def crop_region(image: np.ndarray, detection: Detection, padding: int = 4) -> np.ndarray:
    """Crop a bounding box from the full sheet image with optional pixel padding."""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = detection.box
    x1 = max(0, int(x1) - padding)
    y1 = max(0, int(y1) - padding)
    x2 = min(w, int(x2) + padding)
    y2 = min(h, int(y2) + padding)
    return image[y1:y2, x1:x2]


def crop_graded_regions(
    image: np.ndarray,
    detections: list[Detection],
    padding: int = 0,
) -> dict[str, list[RegionCrop]]:
    """
    Crop all gradable regions from a sheet image, grouped by section type.

    Args:
        image: Full sheet image (grayscale or BGR).
        detections: Post-processed YOLO detections for this image.
        padding: Extra pixels to include around each bounding box.

    Returns:
        Dict mapping section_type → list of RegionCrop, sorted top-to-bottom.
        Only includes mcq_region, true_false_region, and numeric_region.
    """
    regions: dict[str, list[RegionCrop]] = {}

    for det in detections:
        if det.class_name not in GRADABLE_SECTION_TYPES:
            continue

        crop = crop_region(image, det, padding=padding)
        if crop.size == 0:
            continue

        regions.setdefault(det.class_name, []).append(RegionCrop(det, crop))

    for section_type in regions:
        regions[section_type].sort(key=lambda rc: rc.detection.box[1])

    return regions
