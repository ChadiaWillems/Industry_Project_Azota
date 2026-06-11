"""
Standalone test for the bubble reader — no YOLO needed.

Opens an image and lets you draw a rectangle over a region.
The bubble reader runs on that crop and saves a debug image showing
detected bubbles (green = filled, red = empty).

Usage:
    python ai/omr/test_bubble_reader.py --image data/evaluation/unseen_templates/readable/unseen_omr_01_readable.png

Controls in the selection window:
    Draw rectangle → select region
    SPACE or ENTER → confirm selection and run bubble reader
    C              → cancel / redraw
    Q              → quit without running
"""

import argparse
import sys
import cv2
import numpy as np
from pathlib import Path

from bubble_reader import detect_bubble_grid, draw_bubble_grid, read_region

SECTION_TYPES = ["mcq_region", "true_false_region", "numeric_region", "raw"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Path to a readable exam sheet image.")
    parser.add_argument(
        "--type", default="mcq_region", choices=SECTION_TYPES,
        help="Section type to interpret the selection as.",
    )
    parser.add_argument("--fill-threshold", type=float, default=0.40,
                        help="Dark-pixel fraction to count a bubble as filled.")
    parser.add_argument("--min-radius", type=int, default=7)
    parser.add_argument("--max-radius", type=int, default=22)
    parser.add_argument("--output", default=None,
                        help="Optional path to save the debug image (PNG).")
    return parser.parse_args()


def main():
    args = parse_args()
    image_path = Path(args.image)

    if not image_path.exists():
        print(f"Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"Could not read image: {image_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Image loaded: {image_path.name}  ({image.shape[1]}x{image.shape[0]})")
    print(f"Section type: {args.type}")
    print(f"Fill threshold: {args.fill_threshold}")
    print()
    print("Draw a rectangle around the section you want to test, then press SPACE/ENTER.")
    print("Press C to redraw, Q to quit.")
    print()

    # Scale down for display if the image is large.
    max_display_h = 900
    scale = min(1.0, max_display_h / image.shape[0])
    display = cv2.resize(image, (int(image.shape[1] * scale), int(image.shape[0] * scale)))

    roi = cv2.selectROI("Select region (SPACE=confirm, C=cancel, Q=quit)", display, showCrosshair=True)
    cv2.destroyAllWindows()

    x, y, rw, rh = roi
    if rw == 0 or rh == 0:
        print("No region selected.")
        sys.exit(0)

    # Scale back to original image coordinates.
    x = int(x / scale)
    y = int(y / scale)
    rw = int(rw / scale)
    rh = int(rh / scale)

    crop = image[y:y + rh, x:x + rw]
    print(f"Crop: x={x} y={y} w={rw} h={rh}  →  {crop.shape[1]}x{crop.shape[0]} px")

    grid = detect_bubble_grid(
        crop,
        min_radius=args.min_radius,
        max_radius=args.max_radius,
        fill_threshold=args.fill_threshold,
    )

    print(f"\nDetected grid: {grid.n_rows} rows × {grid.n_cols} cols  ({sum(len(r) for r in grid.bubbles)} bubbles total)")

    filled_count = sum(b.filled for row in grid.bubbles for b in row)
    print(f"Filled bubbles: {filled_count}")

    # Print grid visually.
    if grid.bubbles:
        print("\nGrid (F=filled, .=empty):")
        max_cols = grid.n_cols
        for row_idx, row in enumerate(grid.bubbles):
            # Pad to max_cols in case rows have different lengths.
            cells = {b.col: b.filled for b in row}
            symbols = ["F" if cells.get(c, False) else "." for c in range(max_cols)]
            print(f"  row {row_idx:2d}: {' '.join(symbols)}")

    # Interpret as section type.
    if args.type != "raw":
        result = read_region(
            crop,
            args.type,
            min_radius=args.min_radius,
            max_radius=args.max_radius,
            fill_threshold=args.fill_threshold,
        )
        print(f"\nInterpreted result ({args.type}):")
        if "answers" in result:
            for q, ans in result["answers"].items():
                print(f"  Q{q:2d}: {ans}")
        elif "value" in result:
            print(f"  value: {result['value']!r}")
        elif "grid" in result:
            print(f"  raw grid: {result['grid']}")

    # Debug visualization.
    vis = draw_bubble_grid(crop, grid)

    if args.output:
        out_path = Path(args.output)
        cv2.imwrite(str(out_path), vis)
        print(f"\nDebug image saved: {out_path}")
    else:
        out_path = image_path.parent / f"{image_path.stem}_omr_debug.png"
        cv2.imwrite(str(out_path), vis)
        print(f"\nDebug image saved: {out_path}")

    cv2.imshow("Bubble detection result (any key to close)", vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
