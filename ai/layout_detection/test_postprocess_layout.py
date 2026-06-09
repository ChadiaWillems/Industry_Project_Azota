"""
Small manual test for postprocess_layout.py.

Run from project root:

python ai/layout_detection/test_postprocess_layout.py
"""

from postprocess_layout import Detection, postprocess_detections


def print_detections(title, detections):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)

    for det in detections:
        print(
            f"{det.class_name:25s} "
            f"conf={det.confidence:.2f} "
            f"box={det.box}"
        )


def main():
    image_width = 750
    image_height = 1050

    raw_detections = [
        # Duplicate student info: should keep only highest confidence
        Detection("student_info_region", 0.84, (200, 100, 500, 220)),
        Detection("student_info_region", 0.82, (200, 220, 500, 350)),

        # Low-confidence true/false: should be removed
        Detection("true_false_region", 0.29, (300, 600, 600, 650)),

        # Good MCQ: should stay
        Detection("mcq_region", 0.96, (40, 350, 180, 620)),

        # Registration markers: too many, should keep max 4 corner-like ones
        Detection("registration_marker", 0.78, (25, 25, 45, 45)),
        Detection("registration_marker", 0.76, (710, 25, 730, 45)),
        Detection("registration_marker", 0.75, (25, 1010, 45, 1030)),
        Detection("registration_marker", 0.37, (710, 1010, 730, 1030)),

        # Internal marker: should be ignored because it is far from corners
        Detection("registration_marker", 0.90, (350, 500, 370, 520)),
    ]

    cleaned_detections = postprocess_detections(
        raw_detections,
        image_width=image_width,
        image_height=image_height,
    )

    print_detections("RAW DETECTIONS", raw_detections)
    print_detections("CLEANED DETECTIONS", cleaned_detections)


if __name__ == "__main__":
    main()