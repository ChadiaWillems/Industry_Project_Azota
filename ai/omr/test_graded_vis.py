"""
Quick test for graded_visualization.py — no Excel answer key needed.

Runs the full OMR pipeline on one image, then builds a synthetic grading result
that alternates correct/wrong across questions so you can see all three
bubble states (green, red, green-outline) in the output.

Usage:
    python ai/omr/test_graded_vis.py \
        --weights runs/detect/runs/azota_layout/yolov8l_layout_v2/weights/best.pt \
        --image data/test_filled/readable/000_readable.png \
        --output runs/omr_results/test_graded_vis

Optional:
    --all-correct   Mark every detected answer as correct (all green)
    --all-wrong     Mark every detected answer as wrong  (all red + outlines)
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "layout_detection"))

import cv2
from ultralytics import YOLO

from grading.compare import flatten_omr, compare
from graded_visualization import save_graded_visualization
from read_sheet import process_image, make_ocr_reader


_MCQ_OPTIONS = ["A", "B", "C", "D"]


def _build_fake_key(flat: dict, mode: str) -> dict:
    """Build a synthetic answer key from the student's OMR output.

    mode="alternate" — even-numbered questions correct, odd-numbered wrong.
    mode="all_correct" — student's answer is always the correct answer.
    mode="all_wrong"   — correct answer is always a different option.
    """
    key: dict = {"MCQ": {}, "TF": {}, "NUM": {}}

    for q, student in flat["MCQ"].items():
        ans = student if (student and student != "MULTIPLE") else "A"
        if mode == "all_correct":
            key["MCQ"][q] = ans
        elif mode == "all_wrong":
            wrong = next((o for o in _MCQ_OPTIONS if o != ans), "A")
            key["MCQ"][q] = wrong
        else:  # alternate
            if q % 2 == 0:
                key["MCQ"][q] = ans
            else:
                wrong = next((o for o in _MCQ_OPTIONS if o != ans), "A")
                key["MCQ"][q] = wrong

    for q, student in flat["TF"].items():
        correct_bool = True if student is not None and student is not False else False
        if mode == "all_correct":
            key["TF"][q] = correct_bool
        elif mode == "all_wrong":
            key["TF"][q] = not correct_bool
        else:  # alternate
            key["TF"][q] = correct_bool if q % 2 == 0 else (not correct_bool)

    for q, student in flat["NUM"].items():
        key["NUM"][q] = student if student else "0"

    return key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", default="runs/omr_results/test_graded_vis")
    parser.add_argument("--device", default="0")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=1024)
    parser.add_argument("--fill-threshold", type=float, default=0.35)
    parser.add_argument("--debug", action="store_true")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--all-correct", action="store_true")
    mode_group.add_argument("--all-wrong", action="store_true")

    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = output_dir / "debug_crops" if args.debug else None
    if debug_dir:
        debug_dir.mkdir(exist_ok=True)

    image_path = Path(args.image)
    print(f"Image:   {image_path}")
    print(f"Weights: {args.weights}")

    ocr_reader = make_ocr_reader(gpu=True)
    model = YOLO(args.weights)

    print("\nRunning OMR pipeline...")
    sheet_result, image, region_grids = process_image(
        image_path, model, args, output_dir, debug_dir, ocr_reader
    )

    flat = flatten_omr(sheet_result)
    n_mcq = len(flat["MCQ"])
    n_tf  = len(flat["TF"])
    n_num = len(flat["NUM"])
    print(f"Detected: MCQ={n_mcq}  TF={n_tf}  NUM={n_num}")

    if n_mcq + n_tf + n_num == 0:
        print("No gradable answers detected — nothing to visualise.")
        sys.exit(0)

    mode = "all_correct" if args.all_correct else ("all_wrong" if args.all_wrong else "alternate")
    print(f"Grading mode: {mode}")

    fake_key = _build_fake_key(flat, mode)
    grading = compare(flat, fake_key)
    score = grading["score"]
    print(f"Synthetic score: {score['earned']}/{score['total']}")

    graded_path = output_dir / f"{image_path.stem}_graded.png"
    save_graded_visualization(image, region_grids, sheet_result, grading, graded_path)
    print(f"\nGraded image saved: {graded_path}")
    print("(Also check the _annotated.png in the same folder for comparison.)")


if __name__ == "__main__":
    main()
