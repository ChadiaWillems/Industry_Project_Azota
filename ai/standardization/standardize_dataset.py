# standardize_dataset.py

"""
Standardize a folder of exam-sheet photos.

Input:
    Phone photos / iPhone images (.jpeg, .jpg, .png)

Output:
    - corrected/: perspective-corrected A4 page
    - readable/: grayscale normalized image for Roboflow annotation
    - binary/: thresholded image for later bubble detection
    - debug/: original image with detected page contour drawn

Run from PowerShell:

    cd "C:\\Users\\Ada\\Documents\\uni\\2025-2026\\Industry Project\\Dataset"
    python standardize_dataset.py
"""

from pathlib import Path
import argparse
import cv2
import numpy as np


# A4 portrait output size.
# 1240 x 1754 keeps enough detail without creating huge files.
A4_WIDTH = 1240
A4_HEIGHT = 1754


def order_points(points):
    """
    Order 4 points as:
    top-left, top-right, bottom-right, bottom-left
    """
    points = points.reshape(4, 2).astype("float32")

    ordered = np.zeros((4, 2), dtype="float32")

    point_sum = points.sum(axis=1)
    point_diff = np.diff(points, axis=1)

    ordered[0] = points[np.argmin(point_sum)]       # top-left
    ordered[2] = points[np.argmax(point_sum)]       # bottom-right
    ordered[1] = points[np.argmin(point_diff)]      # top-right
    ordered[3] = points[np.argmax(point_diff)]      # bottom-left

    return ordered


def resize_for_processing(image, max_width=1400):
    """
    Resize large images for faster contour detection.
    Returns resized image and scale ratio.
    """
    height, width = image.shape[:2]

    if width <= max_width:
        return image.copy(), 1.0

    scale = max_width / width

    resized = cv2.resize(
        image,
        (int(width * scale), int(height * scale)),
        interpolation=cv2.INTER_AREA,
    )

    return resized, scale


def is_reasonable_page_candidate(points, image_shape, min_area_ratio=0.40):
    """
    Check if a 4-point contour is likely to be the full page,
    not an internal table/box.

    This rejects:
    - small internal rectangles
    - very strange aspect ratios
    """
    image_height, image_width = image_shape[:2]
    image_area = image_width * image_height

    points = points.reshape(4, 2).astype(np.float32)

    area = cv2.contourArea(points)
    area_ratio = area / image_area

    if area_ratio < min_area_ratio:
        return False, 0.0

    x, y, w, h = cv2.boundingRect(points.astype(np.int32))

    if w == 0 or h == 0:
        return False, 0.0

    aspect_ratio = w / h
    a4_portrait_ratio = A4_WIDTH / A4_HEIGHT
    a4_landscape_ratio = A4_HEIGHT / A4_WIDTH

    portrait_error = abs(aspect_ratio - a4_portrait_ratio)
    landscape_error = abs(aspect_ratio - a4_landscape_ratio)
    aspect_error = min(portrait_error, landscape_error)

    # Allow perspective distortion, but reject very non-page-like rectangles.
    if aspect_error > 0.50:
        return False, 0.0

    # Prefer large page-like candidates.
    score = area_ratio - aspect_error

    return True, score


def find_page_contour_by_paper_mask(image):
    """
    Detect the page by looking for the bright paper area.

    This helps when the page border itself is faint.
    """
    resized, scale = resize_for_processing(image)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # Separate light paper from darker background.
    _, mask = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    # Clean the mask so the paper becomes one large region.
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))

    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel)

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return None

    candidates = []

    for contour in contours:
        area = cv2.contourArea(contour)

        if area <= 0:
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.03 * perimeter, True)

        if len(approx) == 4:
            points = approx.reshape(4, 2)
        else:
            # If the detected paper contour is not exactly 4 points,
            # approximate it with a rotated rectangle.
            rect = cv2.minAreaRect(contour)
            points = cv2.boxPoints(rect)

        is_valid, score = is_reasonable_page_candidate(
            points,
            resized.shape,
            min_area_ratio=0.40,
        )

        if is_valid:
            candidates.append((score, points))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)

    best_points = candidates[0][1].reshape(4, 1, 2).astype("float32")
    best_points = best_points / scale

    return best_points


def find_page_contour_by_edges(image):
    """
    Detect the page using edges.

    This version is stricter than a basic contour detector,
    so it avoids selecting internal answer tables.
    """
    resized, scale = resize_for_processing(image)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 40, 120)

    # Close small gaps in the outer page boundary.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return None

    candidates = []

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

        if len(approx) != 4:
            continue

        points = approx.reshape(4, 2)

        is_valid, score = is_reasonable_page_candidate(
            points,
            resized.shape,
            min_area_ratio=0.40,
        )

        if is_valid:
            candidates.append((score, points))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)

    best_points = candidates[0][1].reshape(4, 1, 2).astype("float32")
    best_points = best_points / scale

    return best_points


def find_page_contour(image):
    """
    Find the full exam page contour.

    Strategy:
    1. Try detecting the bright paper area.
    2. If that fails, try edge-based page detection.
    3. If both fail, return None and use fallback resize.

    This prevents internal exam boxes from being selected as the page.
    """
    contour = find_page_contour_by_paper_mask(image)

    if contour is not None:
        return contour

    contour = find_page_contour_by_edges(image)

    if contour is not None:
        return contour

    return None


def perspective_correct(image, contour):
    """
    Apply perspective transform to create a fixed-size A4 image.
    """
    src = order_points(contour)

    dst = np.array(
        [
            [0, 0],
            [A4_WIDTH - 1, 0],
            [A4_WIDTH - 1, A4_HEIGHT - 1],
            [0, A4_HEIGHT - 1],
        ],
        dtype="float32",
    )

    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(image, matrix, (A4_WIDTH, A4_HEIGHT))

    return warped


def fallback_resize(image):
    """
    If page contour detection fails, resize the full image to A4 ratio.

    This is not ideal, but it lets you inspect failures instead of losing them.
    """
    height, width = image.shape[:2]

    target_ratio = A4_WIDTH / A4_HEIGHT
    current_ratio = width / height

    if current_ratio > target_ratio:
        # Image is too wide, crop left/right.
        new_width = int(height * target_ratio)
        x1 = (width - new_width) // 2
        cropped = image[:, x1:x1 + new_width]
    else:
        # Image is too tall, crop top/bottom.
        new_height = int(width / target_ratio)
        y1 = (height - new_height) // 2
        cropped = image[y1:y1 + new_height, :]

    resized = cv2.resize(
        cropped,
        (A4_WIDTH, A4_HEIGHT),
        interpolation=cv2.INTER_AREA,
    )

    return resized


def create_readable_image(corrected):
    """
    Create a readable grayscale image for Roboflow annotation/model training.
    """
    gray = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY)

    # Improve local contrast.
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    readable = clahe.apply(gray)

    # Light denoising.
    readable = cv2.GaussianBlur(readable, (3, 3), 0)

    return readable


def create_binary_image(readable):
    """
    Create binary image for future OMR/bubble detection.
    """
    binary = cv2.adaptiveThreshold(
        readable,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )

    return binary


def draw_debug_contour(image, contour, status):
    """
    Draw detected contour on original image for debugging.
    """
    debug = image.copy()

    if contour is not None:
        contour_int = contour.astype(np.int32)
        cv2.drawContours(debug, [contour_int], -1, (0, 255, 0), 8)

        cv2.putText(
            debug,
            status.upper(),
            (40, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 255, 0),
            4,
            cv2.LINE_AA,
        )
    else:
        cv2.putText(
            debug,
            "NO PAGE CONTOUR FOUND - USED FALLBACK RESIZE",
            (40, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 0, 255),
            3,
            cv2.LINE_AA,
        )

    return debug


def standardize_single_image(image_path, output_dirs):
    """
    Process one image and save corrected/readable/binary/debug outputs.
    """
    image = cv2.imread(str(image_path))

    if image is None:
        print(f"[SKIP] Could not read image: {image_path}")
        return False

    contour = find_page_contour(image)

    if contour is not None:
        corrected = perspective_correct(image, contour)
        status = "ok"
    else:
        corrected = fallback_resize(image)
        status = "fallback"

    readable = create_readable_image(corrected)
    binary = create_binary_image(readable)
    debug = draw_debug_contour(image, contour, status)

    base_name = image_path.stem

    corrected_path = output_dirs["corrected"] / f"{base_name}_corrected.png"
    readable_path = output_dirs["readable"] / f"{base_name}_readable.png"
    binary_path = output_dirs["binary"] / f"{base_name}_binary.png"
    debug_path = output_dirs["debug"] / f"{base_name}_debug.jpg"

    cv2.imwrite(str(corrected_path), corrected)
    cv2.imwrite(str(readable_path), readable)
    cv2.imwrite(str(binary_path), binary)
    cv2.imwrite(str(debug_path), debug)

    print(f"[{status.upper()}] {image_path.name}")

    return status == "ok"


def collect_image_files(input_dir):
    """
    Collect supported image files recursively.
    """
    extensions = [
        "*.jpeg",
        "*.jpg",
        "*.png",
        "*.JPG",
        "*.JPEG",
        "*.PNG",
    ]

    image_files = []

    for extension in extensions:
        image_files.extend(input_dir.rglob(extension))

    return sorted(image_files)


def create_output_dirs(output_dir):
    """
    Create output folders.
    """
    output_dirs = {
        "corrected": output_dir / "corrected",
        "readable": output_dir / "readable",
        "binary": output_dir / "binary",
        "debug": output_dir / "debug",
    }

    for folder in output_dirs.values():
        folder.mkdir(parents=True, exist_ok=True)

    return output_dirs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Standardize exam-sheet photos for Roboflow annotation."
    )

    parser.add_argument(
        "--input",
        type=str,
        default=r"C:\Users\Ada\Documents\uni\2025-2026\Industry Project\Dataset\iphone",
        help="Input folder containing original exam photos.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=r"C:\Users\Ada\Documents\uni\2025-2026\Industry Project\Dataset\standardized",
        help="Output folder for standardized images.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input folder does not exist: {input_dir}")

    output_dirs = create_output_dirs(output_dir)
    image_files = collect_image_files(input_dir)

    if not image_files:
        print(f"No image files found in: {input_dir}")
        return

    print(f"Found {len(image_files)} image(s).")
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print()

    success_count = 0
    fallback_count = 0

    for image_path in image_files:
        success = standardize_single_image(image_path, output_dirs)

        if success:
            success_count += 1
        else:
            fallback_count += 1

    print()
    print("Finished standardizing dataset.")
    print(f"Successful page contour detections: {success_count}")
    print(f"Fallback resized images:            {fallback_count}")
    print()
    print("Upload these images to Roboflow:")
    print(output_dirs["readable"])
    print()
    print("Check this folder for failures/debugging:")
    print(output_dirs["debug"])


if __name__ == "__main__":
    main()