"""
Full OMR pipeline: YOLO layout detection → region cropping → bubble reading.

Loads a trained YOLO model, detects regions on exam sheet images, crops them,
reads which bubbles are filled, and writes results as JSON.
Pass --debug to also save annotated images for each detected region.

Example:
    python ai/omr/read_sheet.py \\
        --weights runs/detect/azota_layout/yolov8m_layout_v1_batch2/weights/best.pt \\
        --source data/evaluation/unseen_templates/readable \\
        --output runs/omr_results/demo

    # With debug images:
    python ai/omr/read_sheet.py \\
        --weights ... --source ... --output ... --debug
"""

import sys
import json
import argparse
from pathlib import Path

import cv2
from ultralytics import YOLO

sys.path.insert(0, str(Path(__file__).parent.parent / "layout_detection"))

from postprocess_layout import Detection, postprocess_detections
from crop_regions import crop_graded_regions
from bubble_reader import (
    detect_bubble_grid, draw_bubble_grid, draw_sheet_with_bubbles,
    filter_grid_for_section, read_region, BubbleGrid,
)


def _yolo_result_to_detections(result) -> list[Detection]:
    detections = []
    if result.boxes is None:
        return detections
    names = result.names
    for box in result.boxes:
        class_id = int(box.cls[0].item())
        detections.append(Detection(
            class_name=names[class_id],
            confidence=float(box.conf[0].item()),
            box=tuple(box.xyxy[0].tolist()),
        ))
    return detections


def parse_args():
    parser = argparse.ArgumentParser(description="Run OMR bubble reading on exam sheet images.")

    parser.add_argument("--weights", required=True,
                        help="Path to trained YOLO weights (best.pt).")
    parser.add_argument("--source", required=True,
                        help="Path to a single readable image or a folder of images.")
    parser.add_argument("--conf", type=float, default=0.25,
                        help="YOLO confidence threshold (keep low; post-processing applies stricter thresholds).")
    parser.add_argument("--imgsz", type=int, default=1024,
                        help="YOLO inference image size.")
    parser.add_argument("--device", default="0",
                        help="Device for YOLO inference: '0' for GPU or 'cpu'.")
    parser.add_argument("--output", default="runs/omr_results",
                        help="Folder where JSON results will be saved.")
    parser.add_argument("--fill-threshold", type=float, default=0.35,
                        help="Dark-pixel fraction above which a bubble counts as filled (0–1).")
    parser.add_argument("--debug", action="store_true",
                        help="Save annotated crop images for each detected region.")

    return parser.parse_args()


def process_image(
    image_path: Path,
    model,
    args,
    output_dir: Path,
    debug_dir: Path | None,
) -> dict:
    """Run the full OMR pipeline on one image and return the result dict."""
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    results = model.predict(
        source=str(image_path),
        conf=args.conf,
        imgsz=args.imgsz,
        device=args.device,
        verbose=False,
    )

    result = results[0]
    h, w = image.shape[:2]
    raw_detections = _yolo_result_to_detections(result)
    detections = postprocess_detections(raw_detections, image_width=w, image_height=h)

    regions = crop_graded_regions(image, detections)

    sheet_result: dict = {
        "image": image_path.name,
        "image_size": {"width": w, "height": h},
        "sections": {},
    }

    # Collect (bbox, grid) pairs so we can draw all bubbles on the full sheet.
    region_grids: list[tuple[tuple, BubbleGrid]] = []

    for section_type, crops in regions.items():
        section_readings = []

        for idx, (detection, crop) in enumerate(crops):
            # Compute the grid once — reuse for both interpretation and visualization.
            grid = detect_bubble_grid(crop, fill_threshold=args.fill_threshold)
            # Filter to answer bubbles only: removes header rows (A/B/C/D, Đ/S)
            # and label columns so false-positive circles don't appear in output.
            filtered = filter_grid_for_section(grid, section_type)
            region_grids.append((detection.box, filtered))

            reading = read_region(
                crop,
                section_type,
                fill_threshold=args.fill_threshold,
            )
            reading["region_index"] = idx
            reading["bbox"] = [round(v, 1) for v in detection.box]
            reading["confidence"] = round(detection.confidence, 4)
            section_readings.append(reading)

            if debug_dir is not None:
                vis = draw_bubble_grid(crop, grid)
                debug_name = f"{image_path.stem}_{section_type}_{idx}.png"
                cv2.imwrite(str(debug_dir / debug_name), vis)
                binary_name = f"{image_path.stem}_{section_type}_{idx}_binary.png"
                from bubble_reader import _binarize
                if crop.ndim == 3 and crop.shape[2] == 3:
                    gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                elif crop.ndim == 3:
                    gray_crop = crop[:, :, 0]
                else:
                    gray_crop = crop
                cv2.imwrite(str(debug_dir / binary_name), _binarize(gray_crop))

        sheet_result["sections"][section_type] = section_readings

    # Full-sheet annotation: draw every bubble at its original position.
    sheet_vis = draw_sheet_with_bubbles(image, region_grids)
    annotated_path = output_dir / f"{image_path.stem}_annotated.png"
    cv2.imwrite(str(annotated_path), sheet_vis)

    return sheet_result


def _print_summary(sheet_result: dict) -> None:
    print(f"  {sheet_result['image']}")
    sections = sheet_result.get("sections", {})
    if not sections:
        print("    (no gradable regions detected)")
        return
    for section_type, readings in sections.items():
        print(f"    {section_type}: {len(readings)} region(s)")
        for r in readings:
            idx = r.get("region_index", "?")
            if "answers" in r:
                answered = sum(1 for v in r["answers"].values() if v is not None)
                total = len(r["answers"])
                print(f"      [{idx}] {answered}/{total} answered")
            elif "value" in r:
                print(f"      [{idx}] value = {r['value']!r}")
            elif "grid" in r:
                rows = len(r["grid"])
                cols = len(r["grid"][0]) if r["grid"] else 0
                print(f"      [{idx}] raw grid {rows}x{cols}")


def main():
    args = parse_args()

    weights_path = Path(args.weights)
    source_path = Path(args.source)
    output_dir = Path(args.output)

    if not weights_path.exists():
        print(f"Error: weights not found: {weights_path}", file=sys.stderr)
        sys.exit(1)
    if not source_path.exists():
        print(f"Error: source not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    debug_dir: Path | None = None
    if args.debug:
        debug_dir = output_dir / "debug_crops"
        debug_dir.mkdir(exist_ok=True)

    print()
    print("=" * 60)
    print("Azota OMR — Bubble Reader")
    print("=" * 60)
    print(f"Weights:        {weights_path}")
    print(f"Source:         {source_path}")
    print(f"Output:         {output_dir}")
    print(f"Fill threshold: {args.fill_threshold}")
    print(f"Debug images:   {'yes' if args.debug else 'no'}")
    print("=" * 60)
    print()

    model = YOLO(str(weights_path))

    if source_path.is_dir():
        image_paths = sorted(
            list(source_path.glob("*.png")) + list(source_path.glob("*.jpg"))
        )
    else:
        image_paths = [source_path]

    if not image_paths:
        print("No images found.")
        sys.exit(0)

    print(f"Processing {len(image_paths)} image(s)...\n")

    all_results = []
    for image_path in image_paths:
        sheet_result = process_image(image_path, model, args, output_dir, debug_dir)
        all_results.append(sheet_result)
        _print_summary(sheet_result)

        out_path = output_dir / f"{image_path.stem}_omr.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(sheet_result, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"Done. Results saved to: {output_dir}")
    if debug_dir:
        print(f"Debug crops saved to:  {debug_dir}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
