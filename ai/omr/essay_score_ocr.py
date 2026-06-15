"""
essay_score_ocr.py — extract the teacher's handwritten numeric score from
a score_field_region crop.

Two crop formats are encountered in practice:

  Box format   — small handwritten digit boxes at the TOP of the crop,
                 with a bubble grid below (teachers fill the boxes, not bubbles).
                 Target: top ~35 % of the crop.

  Table format — printed table such as "Phan I: ....d / Tong: ....d" with
                 some cells filled in by the teacher.
                 Target: bottommost filled numeric value (closest to Tong row).

Strategy: run easyocr without an allowlist (allowlist causes mis-identification
of printed Vietnamese letters as digits) and extract numeric values from the
free-form OCR output via regex.  A 2x upscale fallback is applied when the
natural-scale pass finds nothing, to catch faint handwriting.

Returns a dict: {"score": float|None, "raw_text": str, "confidence": float}
"""

import re

import cv2
import numpy as np


# Matches "X,Y", "X.Y" or OCR artefacts like "X,.Y" (multiple separators).
_DECIMAL_RE = re.compile(r'\d+[.,]+\d+')
_INTEGER_RE = re.compile(r'\d+')

# Lines that contain no digits at all are printed label lines (e.g. "Phan I:").
_LABEL_ONLY_RE = re.compile(r'^[^\d]+$')

# Count alphabetic characters — used to skip section-label tokens like
# "9. Diem tu luan" where "9" is a section number, not a teacher score.
_ALPHA_RE = re.compile(r'[a-zA-Z]')
_MAX_ALPHA_IN_SCORE_TOKEN = 3


def _parse_score(text: str) -> float | None:
    """Parse a raw OCR string into a float score, or return None.

    Handles:
      "8"        -> 8.0
      "7,5"      -> 7.5   (Vietnamese comma decimal separator)
      "8.5"      -> 8.5
      "8/10"     -> 8.0   (X/Y -> take numerator)
      "5,252"    -> 5.252 (OCR artefact for "5,25" -- accepted; close enough)
      "5,.25"    -> 5.25  (double-separator OCR artefact: comma then dot)
      "5,25. d"  -> 5.25  (strip trailing unit/punctuation)
    """
    text = text.strip()
    if not text:
        return None

    # Strip ALL trailing non-digit characters (unit markers, stray letters, punctuation).
    text = re.sub(r'[^\d]+$', '', text)

    # X/Y format -> take numerator.
    if '/' in text:
        text = text.split('/', 1)[0].strip()

    # Vietnamese comma decimal separator -> dot.
    text = text.replace(',', '.')

    # Remove any characters that are not digits or dot.
    text = re.sub(r'[^\d.]', '', text)

    # Collapse consecutive dots (OCR artefact "5,.25" -> "5..25" -> "5.25").
    text = re.sub(r'\.{2,}', '.', text).strip('.')

    if not text:
        return None

    try:
        val = float(text)
    except ValueError:
        return None

    # Vietnamese exam scores are 0-10 or 0-20; filter implausible noise.
    if val <= 0 or val > 20:
        return None

    return val


def _extract_candidates(ocr_results: list, y_scale: float = 1.0) -> list[tuple[float, float, float]]:
    """Return (score, confidence, y_bottom) triples from an OCR result list.

    ocr_results: easyocr detail=1 list of (bbox, text, conf).
    y_scale: divide y coordinates by this factor when results come from an
             upscaled image, so that sorting by y is comparable across passes.
    """
    candidates = []
    for bbox, text, conf in ocr_results:
        # Skip lines that contain no digits at all (printed labels like "Phan I:").
        if _LABEL_ONLY_RE.match(text.strip()):
            continue
        # Skip tokens dominated by alphabetic chars: these are section-label lines
        # like "9. Diem tu luan" where "9" is a section number, not a score.
        if len(_ALPHA_RE.findall(text)) > _MAX_ALPHA_IN_SCORE_TOKEN:
            continue

        y_bottom = max(pt[1] for pt in bbox) / y_scale

        # Prefer decimal matches (more specific); fall back to integers.
        matches = _DECIMAL_RE.findall(text) or _INTEGER_RE.findall(text)
        for num_str in matches:
            parsed = _parse_score(num_str)
            if parsed is not None:
                candidates.append((parsed, float(conf), y_bottom))

    return candidates


def extract_essay_score(crop: np.ndarray, ocr_reader) -> dict:
    """Extract the teacher's handwritten numeric score from a score_field crop.

    Args:
        crop: grayscale numpy array of the score_field_region crop.
        ocr_reader: an initialised easyocr.Reader instance (reused from read_sheet.py).

    Returns:
        {
            "score":      float | None,   # parsed numeric score; None if blank or unreadable
            "raw_text":   str,            # all OCR text concatenated (for display/debug)
            "confidence": float,          # OCR confidence of the best match (0-1)
        }
    """
    result: dict = {"score": None, "raw_text": "", "confidence": 0.0}

    # Fast-path: nearly white crop -> blank field, skip OCR.
    if float(np.mean(crop)) > 240:
        return result

    h, w = crop.shape[:2]

    # Regions to try in order:
    #   top 35 % at 1x  — catches clear handwriting in box-format digit boxes
    #   top 35 % at 2x  — catches faint/small digit boxes before falling to full crop
    #                      (avoids bubble-grid row labels at the crop bottom winning)
    #   full crop at 1x — catches table format where Tong row can be anywhere
    #   full crop at 2x — last-resort for faint handwriting in table format
    top_strip = crop[:max(1, int(h * 0.35)), :]
    regions = [
        ("top",     top_strip, 1),
        ("top_2x",  top_strip, 2),
        ("full",    crop,      1),
        ("full_2x", crop,      2),
    ]

    all_raw_texts: list[str] = []

    for _label, region, scale in regions:
        if scale > 1:
            region_ocr = cv2.resize(
                region,
                (w * scale, region.shape[0] * scale),
                interpolation=cv2.INTER_LINEAR,
            )
        else:
            region_ocr = region

        try:
            ocr_results = ocr_reader.readtext(region_ocr, detail=1, paragraph=False)
        except Exception:
            continue

        if not ocr_results:
            continue

        all_raw_texts.extend(text for _, text, _ in ocr_results)

        candidates = _extract_candidates(ocr_results, y_scale=float(scale))
        if not candidates:
            continue

        # Among valid candidates, prefer the bottommost one (most likely Tong row).
        candidates.sort(key=lambda c: c[2], reverse=True)
        best_score, best_conf, _ = candidates[0]

        result["score"] = best_score
        result["confidence"] = best_conf
        result["raw_text"] = " ".join(all_raw_texts)
        return result

    result["raw_text"] = " ".join(all_raw_texts)
    return result
