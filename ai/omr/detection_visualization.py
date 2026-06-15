"""
Detection image visualization for Azota exam sheets.

Draws YOLO bounding boxes with class labels on the full sheet,
using a fixed colour per class for easy visual distinction.
"""

import cv2
import numpy as np
from pathlib import Path

# BGR colour map for all 9 YOLO classes
_CLASS_COLOURS = {
    "mcq_region":           (255, 120,   0),   # vivid blue
    "true_false_region":    ( 50, 200,  50),   # green
    "numeric_region":       (200,   0, 200),   # magenta/purple
    "essay_region":         (  0, 200, 200),   # yellow
    "score_field_region":   (  0,  80, 255),   # red-orange
    "student_info_region":  (200, 180,   0),   # cyan
    "candidate_id_region":  (  0, 165, 255),   # orange
    "exam_code_region":     (255,   0, 128),   # pink
    "registration_marker":  (160, 160, 160),   # grey
}
_DEFAULT_COLOUR = (200, 200, 200)


def draw_detection_image(image: np.ndarray, detections: list) -> np.ndarray:
    """
    Draw YOLO bounding boxes with class labels on the full sheet.

    Args:
        image: grayscale or BGR numpy array of the full exam sheet
        detections: list of Detection(class_name, confidence, box) from postprocess_detections()

    Returns:
        BGR numpy array with coloured boxes and labels drawn
    """
    if image.ndim == 2:
        vis = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 1:
        vis = cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
    else:
        vis = image.copy()

    h, w = vis.shape[:2]

    for det in detections:
        colour = _CLASS_COLOURS.get(det.class_name, _DEFAULT_COLOUR)
        x1, y1, x2, y2 = (int(v) for v in det.box)

        if det.class_name == "registration_marker":
            cv2.rectangle(vis, (x1, y1), (x2, y2), colour, 1)
            continue

        cv2.rectangle(vis, (x1, y1), (x2, y2), colour, 2)

        label = f"{det.class_name} {det.confidence:.2f}"
        font       = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness  = 1
        (lw, lh), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        # Place label above the box; fall back to inside top edge near the image border.
        label_y = y1 - 4
        if label_y - lh < 0:
            label_y = y1 + lh + 4

        cv2.rectangle(
            vis,
            (x1, label_y - lh - baseline),
            (x1 + lw, label_y + baseline),
            colour,
            cv2.FILLED,
        )
        cv2.putText(vis, label, (x1, label_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    return vis


def save_detection_image(
    image: np.ndarray,
    detections: list,
    output_path: "Path | str",
) -> Path:
    """Render the detection image and write it to output_path as a PNG.

    Args:
        image: Full sheet image (grayscale or BGR numpy array).
        detections: list of Detection from postprocess_detections().
        output_path: Destination file path.

    Returns:
        The resolved output Path.
    """
    output_path = Path(output_path)
    vis = draw_detection_image(image, detections)
    cv2.imwrite(str(output_path), vis)
    return output_path
