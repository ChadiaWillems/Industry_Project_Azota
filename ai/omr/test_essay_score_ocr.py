"""
Standalone test for essay_score_ocr.extract_essay_score.

Since YOLO does not yet detect score_field_region in the test images, this script
manually crops the visible "Điểm" (Score) table from two readable images and runs
the OCR function on those crops so the logic can be verified independently of YOLO.

Usage:
    python ai/omr/test_essay_score_ocr.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np

# Allow importing from the same directory without installing.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from essay_score_ocr import extract_essay_score

try:
    import easyocr
    _reader = easyocr.Reader(['en'], gpu=True, verbose=False)
except Exception as e:
    print(f"easyocr not available: {e}")
    sys.exit(1)

# -----------------------------------------------------------------------
# Test crops: (image_path, crop_box_xyxy, expected_score_approx)
# Crop coordinates were estimated visually from the annotated pipeline output.
# "at 15.17.41" has "Phần III: 5,25 đ" filled in the Điểm table.
# "at 15.17.42 (1)" has "Phần IV: 1,4 đ" filled in the Điểm table.
# -----------------------------------------------------------------------
READABLE_DIR = Path("data/test_score_field/readable")
SAVE_DIR = Path("runs/omr_results/score_field_test/essay_ocr_test_crops")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

TEST_CASES = [
    {
        "stem": "WhatsApp Image 2026-06-14 at 15.17.41_readable",
        "crop": (800, 360, 1240, 650),
        "expected_approx": 5.25,
    },
    {
        "stem": "WhatsApp Image 2026-06-14 at 15.17.42 (1)_readable",
        "crop": (800, 360, 1240, 650),
        "expected_approx": 1.4,
    },
]

print()
print("=" * 60)
print("Essay Score OCR — standalone test")
print("=" * 60)

for tc in TEST_CASES:
    img_path = READABLE_DIR / f"{tc['stem']}.png"
    if not img_path.exists():
        print(f"\nSKIP  {tc['stem']} (file not found)")
        continue

    image = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"\nSKIP  {tc['stem']} (could not read image)")
        continue

    x1, y1, x2, y2 = tc["crop"]
    crop = image[y1:y2, x1:x2]

    # Save the crop for visual inspection.
    crop_save = SAVE_DIR / f"{tc['stem']}_diem_crop.png"
    cv2.imwrite(str(crop_save), crop)

    result = extract_essay_score(crop, _reader)

    match = "OK" if (
        result["score"] is not None and
        abs(result["score"] - tc["expected_approx"]) < 0.5
    ) else "MISMATCH"

    print(f"\n{tc['stem']}")
    print(f"  crop size  : {crop.shape[1]}x{crop.shape[0]} px, mean={crop.mean():.1f}")
    print(f"  raw_text   : {result['raw_text']!r}")
    print(f"  score      : {result['score']}")
    print(f"  confidence : {result['confidence']:.3f}")
    print(f"  expected   : ~{tc['expected_approx']}  [{match}]")
    print(f"  crop saved : {crop_save}")

print()
print("=" * 60)
print(f"Crop images saved to: {SAVE_DIR}")
print("=" * 60)
print()
