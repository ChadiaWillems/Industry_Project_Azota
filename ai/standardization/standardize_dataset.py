"""
Standardize exam-sheet photos for YOLO annotation and OMR processing.

Drop raw phone photos into:  data/input/
Run:  python ai/standardization/standardize_dataset.py
Outputs appear in:  data/standardized/

Four outputs per image:
  corrected/   perspective-corrected color A4 image
  readable/    grayscale + enhanced contrast, used for YOLO / Roboflow
  binary/      adaptive threshold, used for OMR bubble detection
  debug/       original image with detected contour and method label

Three detection methods tried in order:
  markers    — finds the 4 black corner registration squares (most robust)
  paper_mask — finds the bright paper area against the background
  edges      — edge-based page boundary (last resort before fallback)
  fallback   — simple crop + resize if all detection methods fail
"""

from pathlib import Path
import argparse
import cv2
import numpy as np


A4_WIDTH  = 1240
A4_HEIGHT = 1754

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_INPUT  = str(_PROJECT_ROOT / "data" / "input")
DEFAULT_OUTPUT = str(_PROJECT_ROOT / "data" / "standardized")


# ── Geometry helpers ───────────────────────────────────────────────────────────

def order_points(pts):
    """Order 4 points as: top-left, top-right, bottom-right, bottom-left."""
    pts = pts.reshape(4, 2).astype("float32")
    ordered = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    ordered[0] = pts[np.argmin(s)]   # TL
    ordered[2] = pts[np.argmax(s)]   # BR
    ordered[1] = pts[np.argmin(d)]   # TR
    ordered[3] = pts[np.argmax(d)]   # BL
    return ordered


def resize_for_processing(image, max_width=1600):
    """Downscale large images for faster detection. Returns (resized, scale)."""
    h, w = image.shape[:2]
    if w <= max_width:
        return image.copy(), 1.0
    scale = max_width / w
    resized = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return resized, scale


def is_valid_page_quad(pts, image_shape, min_area_ratio=0.30):
    """
    Check whether 4 points form a plausible full-page quadrilateral.
    Returns (valid: bool, score: float).
    """
    ih, iw = image_shape[:2]
    pts = pts.reshape(4, 2).astype(np.float32)
    area = cv2.contourArea(pts)
    ratio = area / (iw * ih)
    if ratio < min_area_ratio:
        return False, 0.0
    _, _, w, h = cv2.boundingRect(pts.astype(np.int32))
    if w == 0 or h == 0:
        return False, 0.0
    ar = w / h
    a4 = A4_WIDTH / A4_HEIGHT
    err = min(abs(ar - a4), abs(ar - 1 / a4))
    if err > 0.55:
        return False, 0.0
    return True, ratio - err * 0.5


# ── Detection method 1: registration markers ──────────────────────────────────

def find_page_by_markers(image):
    """
    Detect the 4 solid black squares printed near each corner of the exam sheet.

    These registration markers are the most distinctive feature on every sheet
    layout. Detecting them directly gives more precise corner alignment than
    looking at the overall page boundary.

    Returns (contour, "markers") or (None, reason_string).
    """
    resized, scale = resize_for_processing(image, max_width=1600)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    h, w = resized.shape[:2]

    # Markers are near-black even in bright photos
    _, dark = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)

    # Remove fine noise (thin lines, small dots from printed text)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, k)

    contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, "markers_no_dark_blobs"

    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # At 1600px wide, markers are roughly 20–120px wide → area 400–15000
        if area < 400 or area > 15000:
            continue
        bx, by, bw, bh = cv2.boundingRect(cnt)
        if bh == 0:
            continue
        if not (0.4 < bw / bh < 2.5):          # square-ish
            continue
        if area / (bw * bh) < 0.65:            # solid fill (not hollow)
            continue
        candidates.append((bx + bw / 2, by + bh / 2))

    if len(candidates) < 4:
        return None, f"markers_only_{len(candidates)}_found"

    # Pick the best marker in each image quadrant, nearest to the outer corner
    quadrants = [
        (0,   0,   w/2, h/2, 0, 0),    # TL
        (w/2, 0,   w,   h/2, w, 0),    # TR
        (0,   h/2, w/2, h,   0, h),    # BL
        (w/2, h/2, w,   h,   w, h),    # BR
    ]

    corners = []
    for qx1, qy1, qx2, qy2, rx, ry in quadrants:
        in_q = [(cx, cy) for cx, cy in candidates if qx1 <= cx < qx2 and qy1 <= cy < qy2]
        if not in_q:
            return None, "markers_missing_corner"
        best = min(in_q, key=lambda p: (p[0] - rx) ** 2 + (p[1] - ry) ** 2)
        corners.append(best)

    pts = (np.array(corners, dtype=np.float32) / scale).reshape(4, 1, 2)
    valid, _ = is_valid_page_quad(pts, image.shape, min_area_ratio=0.25)
    if not valid:
        return None, "markers_invalid_quad"

    return pts, "markers"


# ── Detection method 2: bright paper region ───────────────────────────────────

def find_page_by_paper_mask(image):
    """Detect the bright paper area against a darker background."""
    resized, scale = resize_for_processing(image)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  cv2.getStructuringElement(cv2.MORPH_RECT, (9,  9 )))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, "paper_mask_empty"

    candidates = []
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        pts4 = None
        for eps in [0.01, 0.02, 0.03, 0.04, 0.06]:
            approx = cv2.approxPolyDP(cnt, eps * peri, True)
            if len(approx) == 4:
                pts4 = approx.reshape(4, 2)
                break
        if pts4 is None:
            rect = cv2.minAreaRect(cnt)
            pts4 = cv2.boxPoints(rect)
        valid, score = is_valid_page_quad(pts4, resized.shape, min_area_ratio=0.35)
        if valid:
            candidates.append((score, pts4))

    if not candidates:
        return None, "paper_mask_no_valid_quad"

    candidates.sort(key=lambda x: x[0], reverse=True)
    pts = (candidates[0][1].reshape(4, 1, 2).astype("float32")) / scale
    return pts, "paper_mask"


# ── Detection method 3: edge-based ────────────────────────────────────────────

def find_page_by_edges(image):
    """Edge-based page detection — avoids internal answer boxes."""
    resized, scale = resize_for_processing(image)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 30, 100)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, "edges_empty"

    candidates = []
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        pts4 = approx.reshape(4, 2)
        valid, score = is_valid_page_quad(pts4, resized.shape, min_area_ratio=0.35)
        if valid:
            candidates.append((score, pts4))

    if not candidates:
        return None, "edges_no_valid_quad"

    candidates.sort(key=lambda x: x[0], reverse=True)
    pts = (candidates[0][1].reshape(4, 1, 2).astype("float32")) / scale
    return pts, "edges"


# ── Detection orchestration ───────────────────────────────────────────────────

def find_page_contour(image):
    """
    Try all detection methods in order of reliability.
    Returns (contour_or_None, method_string).
    """
    for fn in (find_page_by_markers, find_page_by_paper_mask, find_page_by_edges):
        contour, method = fn(image)
        if contour is not None:
            return contour, method
    return None, "fallback"


# ── Image transformation ──────────────────────────────────────────────────────

def perspective_correct(image, contour):
    """Warp the detected page quad to a fixed A4-proportioned canvas."""
    src = order_points(contour)
    dst = np.array([
        [0,          0          ],
        [A4_WIDTH-1, 0          ],
        [A4_WIDTH-1, A4_HEIGHT-1],
        [0,          A4_HEIGHT-1],
    ], dtype="float32")
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image, M, (A4_WIDTH, A4_HEIGHT))


def fill_warp_artifacts(image):
    """
    Fill black corner triangles introduced by perspective warping with white.

    warpPerspective leaves black (0,0,0) pixels where the warped quad does not
    cover the output canvas. These confuse YOLO and adaptive thresholding.
    Only regions connected to the actual image corners are affected.
    """
    h, w = image.shape[:2]
    result = image.copy()
    fill_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)

    for seed_x, seed_y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if np.all(result[seed_y, seed_x] < 25):
            cv2.floodFill(result, fill_mask, (seed_x, seed_y),
                          (255, 255, 255), (25, 25, 25), (25, 25, 25))
    return result


def fallback_resize(image):
    """Crop to A4 ratio and resize — used only when no contour is found."""
    h, w = image.shape[:2]
    target = A4_WIDTH / A4_HEIGHT
    if (w / h) > target:
        nw = int(h * target)
        image = image[:, (w - nw) // 2:(w - nw) // 2 + nw]
    else:
        nh = int(w / target)
        image = image[(h - nh) // 2:(h - nh) // 2 + nh, :]
    return cv2.resize(image, (A4_WIDTH, A4_HEIGHT), interpolation=cv2.INTER_AREA)


# ── Image enhancement ─────────────────────────────────────────────────────────

def create_readable_image(corrected):
    """
    Grayscale + CLAHE + unsharp mask for YOLO input and Roboflow annotation.

    Larger CLAHE tiles (16x16) adapt better to exam sheets that have many
    distinct regions with different local brightness levels.
    The unsharp mask keeps bubble circles and text crisp.
    No final blur is applied — sharpness matters more than smoothness here.
    """
    gray = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16, 16))
    enhanced = clahe.apply(gray)

    # Unsharp mask: boost fine detail without adding noise
    blur = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
    sharpened = cv2.addWeighted(enhanced, 1.4, blur, -0.4, 0)

    return sharpened


def create_binary_image(readable):
    """
    Adaptive threshold for OMR bubble detection.

    Smaller block size (25 vs 31) and lower C (10 vs 15) give tighter,
    cleaner boundaries around filled bubbles.
    Morphological opening removes isolated noise pixels.
    """
    binary = cv2.adaptiveThreshold(
        readable, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        25,
        10,
    )
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k)
    return binary


# ── Debug visualization ───────────────────────────────────────────────────────

def draw_debug_image(image, contour, method):
    """Draw the detected page boundary and method name on the original image."""
    debug = image.copy()
    color = (0, 210, 0) if method != "fallback" else (0, 60, 255)
    if contour is not None:
        cv2.drawContours(debug, [contour.astype(np.int32)], -1, color, 8)
    cv2.putText(debug, f"[{method.upper()}]", (40, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 1.6, color, 4, cv2.LINE_AA)
    return debug


# ── Per-image and batch orchestration ────────────────────────────────────────

def standardize_single_image(image_path, output_dirs, skip_existing=False):
    """
    Process one image end-to-end.
    Returns the detection method used, or 'skipped' / 'error'.
    """
    base = Path(image_path).stem

    if skip_existing and (output_dirs["readable"] / f"{base}_readable.png").exists():
        return "skipped"

    image = cv2.imread(str(image_path))
    if image is None:
        print(f"  [ERROR        ] Cannot read: {image_path.name}")
        return "error"

    contour, method = find_page_contour(image)

    if contour is not None:
        corrected = perspective_correct(image, contour)
        corrected = fill_warp_artifacts(corrected)
    else:
        corrected = fallback_resize(image)

    readable = create_readable_image(corrected)
    binary   = create_binary_image(readable)
    debug    = draw_debug_image(image, contour, method)

    cv2.imwrite(str(output_dirs["corrected"] / f"{base}_corrected.png"), corrected)
    cv2.imwrite(str(output_dirs["readable"]  / f"{base}_readable.png"),  readable)
    cv2.imwrite(str(output_dirs["binary"]    / f"{base}_binary.png"),    binary)
    cv2.imwrite(str(output_dirs["debug"]     / f"{base}_debug.jpg"),     debug,
                [cv2.IMWRITE_JPEG_QUALITY, 90])

    print(f"  [{method:14s}] {image_path.name}")
    return method


def collect_image_files(input_dir):
    files = []
    for ext in ["*.jpeg", "*.jpg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
        files.extend(Path(input_dir).rglob(ext))
    return sorted(set(files))


def create_output_dirs(output_dir):
    dirs = {name: Path(output_dir) / name for name in ("corrected", "readable", "binary", "debug")}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def parse_args():
    p = argparse.ArgumentParser(
        description="Standardize exam-sheet photos to A4.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Defaults: input={DEFAULT_INPUT}, output={DEFAULT_OUTPUT}",
    )
    p.add_argument("--input",         default=DEFAULT_INPUT,  help="Folder with raw photos.")
    p.add_argument("--output",        default=DEFAULT_OUTPUT, help="Output folder.")
    p.add_argument("--skip-existing", action="store_true",
                   help="Skip images that already have a readable output.")
    return p.parse_args()


def main():
    args = parse_args()
    input_dir  = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created input folder: {input_dir}")
        print("Drop your exam sheet photos there and re-run.")
        return

    files = collect_image_files(input_dir)
    if not files:
        print(f"No images found in: {input_dir}")
        return

    output_dirs = create_output_dirs(output_dir)

    print(f"Standardizing {len(files)} image(s)")
    print(f"  Input:  {input_dir}")
    print(f"  Output: {output_dir}")
    print()

    counts = {}
    for path in files:
        method = standardize_single_image(path, output_dirs, args.skip_existing)
        counts[method] = counts.get(method, 0) + 1

    print()
    print("Done.")
    for m in ["markers", "paper_mask", "edges", "fallback", "skipped", "error"]:
        if counts.get(m):
            note = " <-- check debug/ images" if m in ("fallback", "error") else ""
            print(f"  {m:14s}: {counts[m]}{note}")
    print()
    print(f"YOLO / Roboflow images : {output_dirs['readable']}")
    print(f"OMR binary images      : {output_dirs['binary']}")
    print(f"Debug (check failures) : {output_dirs['debug']}")


if __name__ == "__main__":
    main()
