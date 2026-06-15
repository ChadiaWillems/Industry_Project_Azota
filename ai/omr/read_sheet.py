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

# grading is an optional peer package — import lazily so read_sheet.py works
# even without the grading module present.
try:
    _grading_root = Path(__file__).parent.parent
    if str(_grading_root) not in sys.path:
        sys.path.insert(0, str(_grading_root))
    from grading.answer_key import load_answer_key as _load_answer_key
    from grading.compare import flatten_omr as _flatten_omr, compare as _compare
    _GRADING_AVAILABLE = True
except ImportError:
    _GRADING_AVAILABLE = False

try:
    from graded_visualization import save_graded_visualization as _save_graded_vis
    _GRADED_VIS_AVAILABLE = True
except ImportError:
    _GRADED_VIS_AVAILABLE = False

try:
    _grading_root = Path(__file__).parent.parent
    if str(_grading_root) not in sys.path:
        sys.path.insert(0, str(_grading_root))
    from grading.template_generator import generate_answer_key_template as _generate_template
    _TEMPLATE_AVAILABLE = True
except ImportError:
    _TEMPLATE_AVAILABLE = False

try:
    from essay_score_ocr import extract_essay_score as _extract_essay_score
    _ESSAY_OCR_AVAILABLE = True
except ImportError:
    _ESSAY_OCR_AVAILABLE = False

try:
    from detection_visualization import save_detection_image as _save_detection_image
    _DETECTION_VIS_AVAILABLE = True
except ImportError:
    _DETECTION_VIS_AVAILABLE = False

import cv2
import numpy as np
from ultralytics import YOLO

try:
    import easyocr as _easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).parent.parent / "layout_detection"))

from postprocess_layout import Detection, postprocess_detections
from crop_regions import crop_graded_regions, CROP_PADDING
from bubble_reader import (
    detect_bubble_grid, draw_bubble_grid, draw_sheet_with_bubbles,
    filter_grid_for_section, read_region, BubbleGrid,
)


def _binary_path(readable_path: Path) -> Path:
    """Derive the binary/ counterpart of a readable/ image path.

    data/test_filled/readable/000_readable.png
    → data/test_filled/binary/000_binary.png
    """
    parts = list(readable_path.parts)
    try:
        idx = parts.index("readable")
    except ValueError:
        return Path()
    parts[idx] = "binary"
    stem = readable_path.stem.replace("_readable", "_binary")
    return Path(*parts).with_name(stem + readable_path.suffix)


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


def make_ocr_reader(gpu: bool = True):
    """Create an easyocr Reader for digit recognition. Returns None if unavailable."""
    if not _EASYOCR_AVAILABLE:
        print("Warning: easyocr not installed — question numbers will not be read from sheet.")
        return None
    try:
        print("Loading OCR model (first run downloads ~100 MB)...")
        reader = _easyocr.Reader(['en'], gpu=gpu, verbose=False)
        print("OCR model ready.")
        return reader
    except Exception as e:
        print(f"Warning: could not initialise easyocr ({e}) — question numbers will not be read.")
        return None


def _ocr_mcq_start_question(
    crop: np.ndarray,
    filtered_grid: BubbleGrid,
    ocr_reader,
    n_questions: int,
) -> int | None:
    """Read the starting question number from the left margin of an MCQ crop.

    MCQ blocks have printed row numbers (e.g. "31", "32", ..., "40") in a narrow
    strip to the left of the bubble columns.  Strategy:
    1. Extract the first answer row's horizontal band from that strip and OCR it.
    2. If nothing found, fall back to the full strip at 2x scale.
    3. Snap the minimum detected number to the nearest valid block start to
       correct small misreads (e.g. "11" read as "13" → snaps to 11, tol ≤ 3).
    """
    if not filtered_grid.bubbles:
        return None

    h, w = crop.shape[:2]
    all_bubbles = [b for row in filtered_grid.bubbles for b in row]
    if not all_bubbles:
        return None

    min_bubble_x = min(b.center_x - b.radius for b in all_bubbles)
    strip_w = max(5, int(min_bubble_x) - 4)
    if strip_w >= w:
        return None

    def _parse(results, conf_thresh=0.25):
        return [int(t) for _, t, c in results if t.isdigit() and int(t) > 0 and c > conf_thresh]

    # Primary: band covering first 3 answer rows at natural scale (no min_size
    # override — keep default to avoid spurious small-text noise detections).
    n_sample = min(3, len(filtered_grid.bubbles))
    sample_bubbles = [b for i in range(n_sample) for b in filtered_grid.bubbles[i]]
    top_y = float(min(b.center_y for b in sample_bubbles))
    bot_y = float(max(b.center_y for b in sample_bubbles))
    row_r = float(np.mean([b.radius for b in sample_bubbles]))
    band_y1 = max(0, int(top_y - row_r * 1.2))
    band_y2 = min(h, int(bot_y + row_r * 1.2))
    band = crop[band_y1:band_y2, :strip_w]

    numbers = []
    try:
        numbers = _parse(ocr_reader.readtext(
            band, allowlist='0123456789', detail=1, paragraph=False,
        ))
    except Exception:
        pass

    # Fallback: full strip at 2x scale with lower min_size, for thin single digits
    # like "1" that easyocr misses at natural scale.
    if not numbers:
        try:
            strip = crop[:, :strip_w]
            strip2x = cv2.resize(strip, (strip_w * 2, h * 2), interpolation=cv2.INTER_LINEAR)
            numbers = _parse(ocr_reader.readtext(
                strip2x, allowlist='0123456789', detail=1, paragraph=False, min_size=5,
            ))
        except Exception as e:
            print(f"    OCR error: {e}")

    if not numbers:
        return None

    detected_min = min(numbers)

    # Snap to nearest valid block start; only when deviation ≤ 3 so we don't
    # accidentally correct a genuinely wrong OCR reading with a large offset.
    snapped = round((detected_min - 1) / n_questions) * n_questions + 1
    if abs(detected_min - snapped) <= 3:
        return max(1, snapped)
    return detected_min


def _ocr_tf_question_group(crop: np.ndarray, filtered_grid: BubbleGrid, ocr_reader) -> int | None:
    """Read the question group number from the 'Câu X' header of a T/F crop.

    T/F blocks have a text header like 'Câu 7' above the Đ/S bubble rows.
    Sub-questions are labeled a/b/c/d (not digits), so we cannot read them from
    the left strip.  Instead we OCR the header area above the first bubble row
    with a digits-only allowlist — 'Câu 7' → '7'.
    """
    if not filtered_grid.bubbles:
        return None

    h, w = crop.shape[:2]
    first_row = filtered_grid.bubbles[0]
    row_y = float(np.mean([b.center_y for b in first_row]))
    row_r = float(np.mean([b.radius for b in first_row]))

    # Use the top half of the crop to ensure "Câu X" text is captured regardless
    # of where the first answer bubble sits.  The bottom half has answer bubbles.
    header_y2 = max(1, h // 2)
    header = crop[:header_y2, :]

    import re as _re
    try:
        # Read without digit-only restriction so "Câu 41" is captured as a full
        # string rather than being split into "4" and "1" tokens.
        results = ocr_reader.readtext(header, detail=1, paragraph=False, min_size=5)
        # Sort top-to-bottom; "Câu X" appears at the very top of the crop.
        results.sort(key=lambda r: min(pt[1] for pt in r[0]))
        for _, text, conf in results:
            if conf < 0.2:
                continue
            m = _re.search(r'\d+', text)
            if m:
                num = int(m.group())
                if 1 <= num <= 200:
                    return num
    except Exception as e:
        print(f"    OCR error (T/F header): {e}")
    return None


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
    parser.add_argument("--answer-key", default=None,
                        help="Path to Excel answer key (.xlsx). When provided, grades each sheet "
                             "and adds a 'grading' key to the JSON output.")
    parser.add_argument("--generate-template", action="store_true",
                        help="Generate a pre-filled Excel answer key template for each processed "
                             "sheet and save it as {stem}_template.xlsx in the output folder.")

    return parser.parse_args()


def process_image(
    image_path: Path,
    model,
    args,
    output_dir: Path,
    debug_dir: Path | None,
    ocr_reader=None,
) -> dict:
    """Run the full OMR pipeline on one image and return the result dict."""
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    # Load the corresponding binary/ image for fill ratio measurement (T/F + Numeric).
    bin_path = _binary_path(image_path)
    binary_image = cv2.imread(str(bin_path), cv2.IMREAD_GRAYSCALE) if bin_path.exists() else None

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
            # score_field_region: skip bubble reading; run essay score OCR instead.
            if section_type == "score_field_region":
                if _ESSAY_OCR_AVAILABLE and ocr_reader is not None:
                    essay_ocr = _extract_essay_score(crop, ocr_reader)
                else:
                    essay_ocr = {"score": None, "raw_text": "", "confidence": 0.0}
                reading = {
                    "region_index": idx,
                    "bbox": [round(v, 1) for v in detection.box],
                    "confidence": round(detection.confidence, 4),
                    "essay_score": essay_ocr,
                }
                section_readings.append(reading)
                if debug_dir is not None:
                    debug_name = f"{image_path.stem}_{section_type}_{idx}.png"
                    cv2.imwrite(str(debug_dir / debug_name), crop)
                continue

            # Binary fill measurement for T/F and Numeric only.
            # MCQ is excluded: 4 tightly-packed columns cause ring-pixel bleed in
            # the binary image that inflates fill ratios → more MULTIPLE detections.
            h_img, w_img = image.shape[:2]
            if binary_image is not None and section_type != "mcq_region":
                pad_x1 = max(0, int(detection.box[0]) - CROP_PADDING)
                pad_y1 = max(0, int(detection.box[1]) - CROP_PADDING)
                pad_x2 = min(w_img - 1, int(detection.box[2]) + CROP_PADDING)
                pad_y2 = min(h_img - 1, int(detection.box[3]) + CROP_PADDING)
                binary_crop: np.ndarray | None = binary_image[pad_y1:pad_y2, pad_x1:pad_x2]
            else:
                binary_crop = None

            # Compute the grid once — reuse for both interpretation and visualization.
            grid = detect_bubble_grid(crop, fill_threshold=args.fill_threshold, binary_crop=binary_crop)
            # Filter to answer bubbles only: removes header rows (A/B/C/D, Đ/S)
            # and label columns so false-positive circles don't appear in output.
            filtered = filter_grid_for_section(grid, section_type)

            # Bubble centers are relative to the padded crop, so the drawing offset
            # must be the padded top-left corner of the crop, not the raw YOLO box.
            # Using the raw YOLO box shifts all circles CROP_PADDING px right and down.
            pad_x1 = max(0, int(detection.box[0]) - CROP_PADDING)
            pad_y1 = max(0, int(detection.box[1]) - CROP_PADDING)
            padded_box = (pad_x1, pad_y1, detection.box[2], detection.box[3])
            region_grids.append((padded_box, filtered))

            reading = read_region(
                crop,
                section_type,
                fill_threshold=args.fill_threshold,
                binary_crop=binary_crop,
            )
            reading["region_index"] = idx
            reading["bbox"] = [round(v, 1) for v in detection.box]
            reading["confidence"] = round(detection.confidence, 4)

            # MCQ: read printed row numbers from left strip → remap answer keys globally.
            if section_type == "mcq_region" and "answers" in reading:
                n_q = len(reading["answers"])
                start_q = _ocr_mcq_start_question(crop, filtered, ocr_reader, n_q)
                reading["question_start"] = start_q
                if start_q is not None:
                    reading["answers"] = {
                        str(start_q + int(k) - 1): v
                        for k, v in reading["answers"].items()
                    }

            # T/F: read 'Câu X' from header → store group number, keep a/b/c/d as 1-4.
            if section_type == "true_false_region" and "answers" in reading:
                group = _ocr_tf_question_group(crop, filtered, ocr_reader)
                reading["question_group"] = group

            # Numeric: read 'Câu X' from header → store group number for finalization.
            if section_type == "numeric_region":
                group = _ocr_tf_question_group(crop, filtered, ocr_reader)
                reading["question_group"] = group

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

    # Validate MCQ question numbering; apply position-based fallback if OCR was
    # inconsistent (duplicate starts or None values across blocks).
    if "mcq_region" in sheet_result["sections"]:
        _finalize_mcq_numbering(sheet_result["sections"]["mcq_region"])

    # Merge T/F blocks into {"Câu X": {"a": bool, ...}} and replace the raw list.
    if "true_false_region" in sheet_result["sections"]:
        sheet_result["sections"]["true_false_region"] = _finalize_tf_numbering(
            sheet_result["sections"]["true_false_region"]
        )

    # Merge numeric blocks into {"Câu X": value} and replace the raw list.
    if "numeric_region" in sheet_result["sections"]:
        sheet_result["sections"]["numeric_region"] = _finalize_numeric_numbering(
            sheet_result["sections"]["numeric_region"]
        )

    # Collect essay score: take the first non-None score from score_field readings.
    essay_score = None
    for r in sheet_result["sections"].get("score_field_region", []):
        candidate = r.get("essay_score", {}).get("score")
        if candidate is not None:
            essay_score = candidate
            break
    sheet_result["essay_score"] = essay_score

    # Full-sheet annotation: draw every bubble at its original position.
    sheet_vis = draw_sheet_with_bubbles(image, region_grids)
    annotated_path = output_dir / f"{image_path.stem}_annotated.png"
    cv2.imwrite(str(annotated_path), sheet_vis)

    # Detection image: YOLO boxes with class labels.
    if _DETECTION_VIS_AVAILABLE:
        detection_path = output_dir / f"{image_path.stem}_detection.png"
        _save_detection_image(image, detections, detection_path)

    return sheet_result, image, region_grids, detections


_TF_LETTERS = {1: "a", 2: "b", 3: "c", 4: "d"}


def _finalize_tf_numbering(section_readings: list[dict]) -> dict:
    """Merge T/F blocks into {"Câu X": {"a": bool, "b": bool, "c": bool, "d": bool}}.

    T/F blocks on Vietnamese exam sheets are arranged right-to-left:
    the rightmost block = highest Câu number.  We infer the starting Câu
    number using per-block OCR results (question_group) and majority voting:
    for a block at sorted right-to-left rank i, start = group - (n-1-i).
    Falls back to Câu 1 when OCR gives no usable signal.
    """
    blocks = [r for r in section_readings if "answers" in r]
    if not blocks:
        return {}

    n = len(blocks)
    sorted_blocks = sorted(blocks, key=lambda r: r["bbox"][0], reverse=True)

    # Infer starting Câu number from OCR-detected groups.
    inferred_starts = []
    for rank, block in enumerate(sorted_blocks):
        g = block.get("question_group")
        if g is not None:
            inferred_starts.append(g - (n - 1 - rank))

    if inferred_starts:
        from collections import Counter
        start = max(1, Counter(inferred_starts).most_common(1)[0][0])
    else:
        start = 1

    merged: dict[str, dict] = {}
    for rank, block in enumerate(sorted_blocks):
        cau_num = start + (n - 1 - rank)
        key = f"Câu {cau_num}"
        raw = block.get("answers", {})
        letter_answers = {
            _TF_LETTERS.get(int(k), k): v
            for k, v in sorted(raw.items(), key=lambda x: int(x[0]))
        }
        merged[key] = letter_answers

    return merged


def _finalize_numeric_numbering(section_readings: list[dict]) -> dict:
    """Merge numeric blocks into {"Câu X": value_string_or_None}.

    Like T/F, numeric blocks on Vietnamese exam sheets are arranged right-to-left:
    rightmost block = highest Câu number.  Câu numbers are inferred from per-block
    OCR results (question_group) via majority voting, falling back to Câu 1.
    """
    from collections import Counter as _Counter
    blocks = [r for r in section_readings if "section_type" in r]
    if not blocks:
        return {}

    n = len(blocks)
    sorted_blocks = sorted(blocks, key=lambda r: r["bbox"][0], reverse=True)

    inferred_starts = []
    for rank, block in enumerate(sorted_blocks):
        g = block.get("question_group")
        if g is not None:
            inferred_starts.append(g - (n - 1 - rank))

    start = max(1, _Counter(inferred_starts).most_common(1)[0][0]) if inferred_starts else 1

    merged: dict[str, object] = {}
    for rank, block in enumerate(sorted_blocks):
        cau_num = start + (n - 1 - rank)
        merged[f"Câu {cau_num}"] = block.get("value")

    return merged


def _finalize_mcq_numbering(section_readings: list[dict]) -> None:
    """Validate OCR-detected MCQ question starts; fall back to position ordering if needed.

    OCR can partially misread — e.g. "31" → "1" (leading digit dropped), or
    "35" → "5" (off-by-one block).  We accept OCR results only when all three
    checks pass:
      1. Every block has a non-None start.
      2. All starts are unique.
      3. Every start is a valid block boundary: (start - 1) % n_questions == 0.
         This catches "5" (not a valid start for 10-question blocks) or "35".
      4. Starts are monotonically increasing left-to-right (ascending x), which
         is the standard Vietnamese exam layout for MCQ.
    If any check fails, all blocks are renumbered by left-to-right x-position.
    """
    answer_blocks = [r for r in section_readings if "answers" in r]
    if not answer_blocks:
        return

    starts = [r.get("question_start") for r in answer_blocks]
    n_q = max(len(r["answers"]) for r in answer_blocks)

    def _is_valid():
        if not all(s is not None for s in starts):
            return False
        if len(set(starts)) != len(starts):
            return False
        if not all((s - 1) % n_q == 0 for s in starts):
            return False
        # Starts must increase left-to-right (standard Vietnamese MCQ layout).
        by_x = sorted(answer_blocks, key=lambda r: r["bbox"][0])
        x_starts = [r.get("question_start") for r in by_x]
        if x_starts != sorted(x_starts):
            return False
        return True

    if _is_valid():
        return

    # Fall back to left-to-right position ordering.
    sorted_blocks = sorted(answer_blocks, key=lambda r: r["bbox"][0])
    offset = 0
    for block in sorted_blocks:
        old_items = sorted(block["answers"].items(), key=lambda x: int(x[0]))
        block["answers"] = {str(offset + i + 1): v for i, (_, v) in enumerate(old_items)}
        block["question_start"] = offset + 1
        offset += len(old_items)


def _print_summary(sheet_result: dict) -> None:
    print(f"  {sheet_result['image']}")
    sections = sheet_result.get("sections", {})
    if not sections:
        print("    (no gradable regions detected)")
        return
    for section_type, readings in sections.items():
        # T/F and numeric are now merged dicts keyed by "Câu X".
        if isinstance(readings, dict):
            print(f"    {section_type}: {len(readings)} question(s)")
            for cau, val in readings.items():
                if isinstance(val, dict):
                    answered = sum(1 for v in val.values() if v is not None)
                    print(f"      {cau}: {answered}/{len(val)} answered")
                else:
                    print(f"      {cau}: {val!r}")
            continue

        print(f"    {section_type}: {len(readings)} region(s)")
        for r in readings:
            idx = r.get("region_index", "?")
            if "answers" in r:
                answered = sum(1 for v in r["answers"].values() if v is not None)
                total = len(r["answers"])
                start_q = r.get("question_start")
                label = f" (q{start_q}–q{start_q + total - 1})" if start_q is not None else ""
                print(f"      [{idx}] {answered}/{total} answered{label}")
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

    ocr_reader = make_ocr_reader(gpu=True)

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

    answer_key = None
    if getattr(args, "answer_key", None):
        if not _GRADING_AVAILABLE:
            print("Warning: grading module not found — --answer-key ignored.", file=sys.stderr)
        else:
            try:
                answer_key = _load_answer_key(args.answer_key)
                totals = {t: len(v) for t, v in answer_key.items() if v}
                print(f"Answer key loaded: {totals}")
            except ValueError as e:
                print(f"Error loading answer key: {e}", file=sys.stderr)
                sys.exit(1)

    all_results = []
    for image_path in image_paths:
        sheet_result, image, region_grids, detections = process_image(image_path, model, args, output_dir, debug_dir, ocr_reader)

        if answer_key is not None and _GRADING_AVAILABLE:
            flat = _flatten_omr(sheet_result)
            grading = _compare(flat, answer_key)
            sheet_result["grading"] = grading
            if _GRADED_VIS_AVAILABLE:
                graded_path = output_dir / f"{image_path.stem}_graded.png"
                _save_graded_vis(image, region_grids, sheet_result, grading, graded_path)
            score = grading["score"]
            print(f"  Score: {score['earned']}/{score['total']}")
            for w in grading["warnings"]:
                print(f"  Warning: {w}")

        if getattr(args, "generate_template", False) and _TEMPLATE_AVAILABLE:
            try:
                tmpl_path = output_dir / f"{image_path.stem}_template.xlsx"
                _generate_template(sheet_result, tmpl_path)
                print(f"  Template saved: {tmpl_path.name}")
            except ValueError as e:
                print(f"  Template warning: {e}", file=sys.stderr)

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
