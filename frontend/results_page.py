# frontend/results_page.py
import streamlit as st
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from ai.grading.answer_key import load_answer_key
    from ai.grading.compare import flatten_omr, compare as grade_compare
    _GRADING_AVAILABLE = True
except ImportError:
    _GRADING_AVAILABLE = False


def _find_weights() -> str | None:
    """Return path to the best available YOLO weights, or None."""
    env_path = os.environ.get("AZOTA_WEIGHTS")
    if env_path and os.path.exists(env_path):
        return env_path

    candidates = [
        _project_root / "runs/detect/runs/azota_layout/yolov8l_layout_v2/weights/best.pt",
        _project_root / "runs/detect/runs/azota_layout/yolov8m_layout_v1_batch2/weights/best.pt",
        _project_root / "models/baselines/yolov8s_layout_v1/weights/best.pt",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


@st.cache_resource(show_spinner=False)
def _load_yolo_model(weights_path: str):
    from ultralytics import YOLO
    return YOLO(weights_path)


@st.cache_resource(show_spinner=False)
def _load_ocr_reader():
    omr_dir = str(_project_root / "ai" / "omr")
    if omr_dir not in sys.path:
        sys.path.insert(0, omr_dir)
    from read_sheet import make_ocr_reader
    return make_ocr_reader(gpu=True)


def _run_omr(image_path: str) -> dict | None:
    """Run the full OMR pipeline on one image. Returns the sheet_result dict or None."""
    weights = _find_weights()
    if weights is None:
        return None

    try:
        import argparse

        omr_dir = str(_project_root / "ai" / "omr")
        if omr_dir not in sys.path:
            sys.path.insert(0, omr_dir)

        from read_sheet import process_image

        model = _load_yolo_model(weights)
        ocr_reader = _load_ocr_reader()

        args = argparse.Namespace(
            conf=0.25,
            imgsz=1024,
            device="cpu",
            fill_threshold=0.35,
            debug=False,
        )

        output_dir = _project_root / "runs" / "omr_results" / "frontend_temp"
        output_dir.mkdir(parents=True, exist_ok=True)

        sheet_result, image, region_grids, detections = process_image(
            Path(image_path),
            model,
            args,
            output_dir,
            debug_dir=None,
            ocr_reader=ocr_reader,
        )

        # Store visualization data for use across rerenders.
        st.session_state["_omr_np_image"] = image
        st.session_state["_omr_region_grids"] = region_grids
        st.session_state["_omr_output_dir"] = str(output_dir)
        st.session_state["_omr_stem"] = Path(image_path).stem

        # Crop student_info_region so the summary panel can display it.
        student_info_det = next(
            (d for d in detections if d.class_name == "student_info_region"), None
        )
        if student_info_det is not None:
            h, w = image.shape[:2]
            x1, y1, x2, y2 = (int(v) for v in student_info_det.box)
            x1, y1 = max(0, x1 - 4), max(0, y1 - 4)
            x2, y2 = min(w, x2 + 4), min(h, y2 + 4)
            st.session_state["_omr_student_info_crop"] = image[y1:y2, x1:x2]
        else:
            st.session_state["_omr_student_info_crop"] = None

        return sheet_result

    except Exception as e:
        st.warning(f"OMR pipeline error: {e}")
        return None


def _compute_grading(omr_result: dict, answer_key_bytes: bytes) -> dict | None:
    """Load answer key bytes and compare against OMR output. Returns grading dict or None."""
    if not _GRADING_AVAILABLE:
        return None
    try:
        key = load_answer_key(answer_key_bytes)
        flat = flatten_omr(omr_result)
        return grade_compare(flat, key)
    except ValueError as e:
        st.warning(f"Answer key error: {e}")
        return None


def _section_score(grading: dict, type_key: str) -> tuple[int, int]:
    """Return (earned, total) for one section type from a grading result."""
    section = grading.get(type_key, {})
    earned = sum(1 for v in section.values() if v.get("is_correct") is True)
    total  = sum(1 for v in section.values() if v.get("correct") is not None)
    return earned, total


def _ensure_graded_image(omr_result: dict | None, grading: dict | None) -> None:
    """Generate the graded bubble visualization once and cache the path in session state."""
    if grading is None or omr_result is None:
        return
    if "_omr_graded_path" in st.session_state:
        return  # already generated this session

    image       = st.session_state.get("_omr_np_image")
    region_grids = st.session_state.get("_omr_region_grids")
    output_dir  = st.session_state.get("_omr_output_dir")
    stem        = st.session_state.get("_omr_stem")
    if image is None or region_grids is None or not output_dir or not stem:
        return

    try:
        omr_dir = str(_project_root / "ai" / "omr")
        if omr_dir not in sys.path:
            sys.path.insert(0, omr_dir)
        from graded_visualization import save_graded_visualization
        graded_path = Path(output_dir) / f"{stem}_graded.png"
        save_graded_visualization(image, region_grids, omr_result, grading, graded_path)
        st.session_state["_omr_graded_path"] = str(graded_path)
    except Exception as e:
        st.warning(f"Could not generate graded visualization: {e}")


def show_results_page(logo_html, local_img_path):
    # --- 1. GLOBALE PAGINA STYLING ---
    st.markdown("""
        <style>
        .logo-container-preview {
            background-color: #E0E0E0 !important;
            border-bottom: 1px solid #CCCCCC !important;
        }
        .topbar-title-centered {
            color: #000000 !important;
            font-size: 20px !important;
            font-weight: 500 !important;
        }
        .topbar-arrow-clickable {
            color: #000000 !important;
            font-size: 28px !important;
        }
        .right-score-display {
            text-align: right;
            font-size: 24px;
            font-weight: 500;
            color: #000000;
            margin-top: 15px;
            margin-bottom: 10px;
            padding-right: 15px;
            font-family: sans-serif;
        }
        .info-text-screenshot {
            text-align: left;
            font-size: 13px;
            color: #222222;
            font-family: sans-serif;
            margin-bottom: 15px;
            padding-left: 10px;
        }
                
                /* Grade next sheet knop */
div[data-testid="stButton"] > button {
    background-color: #0052CC !important;
    color: white !important;
    border: none !important;
    border-radius: 50px !important;
    height: 44px !important;
    font-size: 15px !important;
    font-weight: bold !important;
    letter-spacing: 0.5px;
    transition: background-color 0.2s ease;
}

div[data-testid="stButton"] > button:hover {
    background-color: #0043A4 !important;
    color: white !important;
}
        
        /* 🚀 GLOBALE SELECTOR OM DE NATIVE STREAMLIT KNOP VOLLEDIG TE VERBERGEN */
        div[data-testid="stMainBlockContainer"] div:has(> button[key="hidden_save_btn"]) {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    params = st.query_params
    if "action" in params and params["action"] == "go_back":
        st.query_params.clear()
        st.session_state.screen = "preview"
        st.rerun()

    st.markdown(f"""
    <div class="logo-container-preview">
        <a href="?action=go_back" target="_self" class="topbar-arrow-clickable">‹</a>
        <div class="topbar-title-centered">Review submission</div>
        <div class="topbar-logo-right">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    # --- Run OMR pipeline (cached in session state to avoid re-running on every rerun) ---
    if "omr_result" not in st.session_state:
        image_path = st.session_state.get("standardized_image_path", "")
        if image_path and os.path.exists(image_path):
            with st.spinner("Reading exam sheet..."):
                st.session_state.omr_result = _run_omr(image_path)
        else:
            st.session_state.omr_result = None

    omr_result = st.session_state.get("omr_result")

    # --- Grade against answer key if available ---
    answer_key_bytes = st.session_state.get("answer_key_bytes")
    grading = None

    if omr_result is not None and answer_key_bytes is not None and _GRADING_AVAILABLE:
        # Use cached grading result; recompute only if answer key changed.
        cached_key_id = st.session_state.get("_grading_key_id")
        current_key_id = id(answer_key_bytes)
        if "grading_result" not in st.session_state or cached_key_id != current_key_id:
            grading = _compute_grading(omr_result, answer_key_bytes)
            st.session_state.grading_result = grading
            st.session_state["_grading_key_id"] = current_key_id
        else:
            grading = st.session_state.grading_result

    # Generate graded visualization once (idempotent).
    _ensure_graded_image(omr_result, grading)

    # --- Score display ---
    if grading is not None:
        score = grading["score"]
        score_text = f"{score['earned']}/{score['total']}"
    elif omr_result is not None and answer_key_bytes is None:
        score_text = "Upload answer key to grade"
    elif omr_result is None and _find_weights() is None:
        score_text = "No model weights found"
    else:
        score_text = "—"

    st.markdown(f'<div class="right-score-display">{score_text}</div>', unsafe_allow_html=True)
    st.markdown('<p class="info-text-screenshot">&#x24D8; This is the autocorrected and auto-graded version.</p>', unsafe_allow_html=True)

    # --- Warnings ---
    if grading and grading.get("warnings"):
        for w in grading["warnings"]:
            st.warning(w)

    # --- Two-column image display: detection | graded (or annotated) ---
    output_dir = st.session_state.get("_omr_output_dir", "")
    stem       = st.session_state.get("_omr_stem", "")
    detection_path = str(Path(output_dir) / f"{stem}_detection.png") if output_dir and stem else ""
    annotated_path = str(Path(output_dir) / f"{stem}_annotated.png") if output_dir and stem else ""
    graded_path    = st.session_state.get("_omr_graded_path", "")

    fallback = st.session_state.get("standardized_image_path", "") or local_img_path

    left_img  = detection_path if os.path.exists(detection_path) else fallback
    right_img = (graded_path    if graded_path and os.path.exists(graded_path)
                 else annotated_path if os.path.exists(annotated_path)
                 else fallback)

    col_l, col_r = st.columns(2)
    with col_l:
        st.caption("Detection (YOLO layout)")
        if os.path.exists(left_img):
            st.image(left_img, use_container_width=True)
        else:
            st.info("Detection image not available.")
    with col_r:
        right_label = "Graded bubbles" if graded_path and os.path.exists(graded_path) else "Detected bubbles"
        st.caption(right_label)
        if os.path.exists(right_img):
            st.image(right_img, use_container_width=True)
        else:
            st.info("Bubble image not available.")

    # --- Summary panel ---
    _show_summary_panel(omr_result, grading)

    # --- Per-question detail (collapsible) ---
    if grading is not None:
        _show_answer_breakdown(grading)

    # Native knop (wordt nu gegarandeerd onzichtbaar gemaakt door de globale CSS in de hoofdband)
    if st.button("Grade next sheet", key="hidden_save_btn", use_container_width=True):
        for key in (
            "omr_result", "grading_result", "_grading_key_id",
            "_omr_np_image", "_omr_region_grids", "_omr_output_dir",
            "_omr_stem", "_omr_graded_path", "_omr_student_info_crop",
        ):
            st.session_state.pop(key, None)
        st.session_state.screen = "camera"
        st.rerun()
        
    st.markdown('</div>', unsafe_allow_html=True)


def _show_summary_panel(omr_result: dict | None, grading: dict | None) -> None:
    """Student info crop, per-section scores, editable essay score, and running total."""
    st.divider()

    student_info_crop = st.session_state.get("_omr_student_info_crop")
    if student_info_crop is not None:
        st.markdown("**Student info** *(unverified — please check)*")
        st.image(student_info_crop, use_container_width=True)

    if grading is None:
        return

    mcq_e, mcq_t = _section_score(grading, "MCQ")
    tf_e,  tf_t  = _section_score(grading, "TF")
    num_e, num_t = _section_score(grading, "NUM")
    bubble_earned = grading["score"]["earned"]
    bubble_total  = grading["score"]["total"]

    rows = []
    if mcq_t > 0: rows.append(("MCQ",      f"{mcq_e}/{mcq_t}"))
    if tf_t  > 0: rows.append(("True/False", f"{tf_e}/{tf_t}"))
    if num_t > 0: rows.append(("Numeric",  f"{num_e}/{num_t}"))
    rows.append(("Bubble total", f"{bubble_earned}/{bubble_total}"))

    for label, val in rows:
        a, b = st.columns([3, 1])
        with a: st.write(label)
        with b: st.write(f"**{val}**")

    # Essay score: editable field pre-filled from OCR result.
    essay_ocr = omr_result.get("essay_score") if omr_result else None
    try:
        essay_default = float(essay_ocr) if essay_ocr is not None else 0.0
    except (ValueError, TypeError):
        essay_default = 0.0

    essay_score = st.number_input(
        "Essay score (teacher-editable)",
        min_value=0.0,
        max_value=20.0,
        value=essay_default,
        step=0.5,
        format="%.1f",
        key="essay_score_input",
    )
    if essay_ocr is not None:
        st.caption(f"OCR suggestion: {essay_ocr} — unverified, please confirm")

    total = bubble_earned + essay_score
    st.markdown(f"**Total: {bubble_earned} + {essay_score:.1f} = {total:.1f}**")


def _show_answer_breakdown(grading: dict) -> None:
    """Compact per-section correct/incorrect breakdown in collapsible expanders."""
    for section_label, type_key in [("MCQ", "MCQ"), ("True/False", "TF"), ("Numeric", "NUM")]:
        section = grading.get(type_key, {})
        if not section:
            continue
        with st.expander(section_label, expanded=False):
            rows = []
            for q in sorted(section.keys()):
                entry = section[q]
                student = entry["student"]
                correct = entry["correct"]
                is_correct = entry["is_correct"]
                if is_correct is None:
                    icon = "—"
                elif is_correct:
                    icon = "✓"
                else:
                    icon = "✗"
                rows.append(f"Q{q}: {icon}  student={student!r}  correct={correct!r}")
            st.text("\n".join(rows))