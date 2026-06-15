import argparse
import os
import sys
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps

from backend import database as db

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from ai.standardization.standardize_dataset import standardize_single_image, create_output_dirs
    _STANDARDIZATION_AVAILABLE = True
except ImportError:
    _STANDARDIZATION_AVAILABLE = False

_OMR_AVAILABLE = True        # checked lazily on first use
_TEMPLATE_GEN_AVAILABLE = True  # checked lazily on first use


def _find_weights() -> str | None:
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
def _get_ocr_reader():
    _omr_dir = str(_project_root / "ai" / "omr")
    if _omr_dir not in sys.path:
        sys.path.insert(0, _omr_dir)
    from read_sheet import make_ocr_reader
    return make_ocr_reader(gpu=True)


def _standardize(raw_path: str, out_subdir: str) -> str:
    """Standardize an image and return the readable path. Falls back to raw_path on error."""
    if not _STANDARDIZATION_AVAILABLE:
        return raw_path
    try:
        std_out = _project_root / "frontend" / "img" / out_subdir
        out_dirs = create_output_dirs(str(std_out))
        standardize_single_image(Path(raw_path), out_dirs)
        readable = out_dirs["readable"] / f"{Path(raw_path).stem}_readable.png"
        return str(readable) if readable.exists() else raw_path
    except Exception:
        return raw_path


def show_camera_page(current_dir, encoded_logo_full):
    if encoded_logo_full:
        st.markdown(
            f'<div class="logo-container-camera"><img src="data:image/png;base64,{encoded_logo_full}" width="110"></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="logo-container-camera"><h3 style="margin:0;">Azota</h3></div>', unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<p class="viewfinder-text-title">Scan or Upload Exam Sheets</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="viewfinder-text-sub">Select what you want to upload to manage your exam process.</p>',
        unsafe_allow_html=True,
    )

    upload_type = st.radio(
        "What do you want to upload?",
        ["Blank exam sheet", "Student submissions", "Excel answer sheet"],
        horizontal=True,
        key="upload_type",
        label_visibility="collapsed",
    )

    # =========================================================================
    # TAB 1: BLANK EXAM SHEET — generate Excel template
    # =========================================================================
    if upload_type == "Blank exam sheet":
        st.markdown("### Upload Blank Exam Sheet")
        st.markdown(
            "<p style='font-size:14px; opacity:0.8;'>Upload a clear photo or scan of the empty exam. "
            "The system will detect all question regions and generate an Excel template for you to fill in.</p>",
            unsafe_allow_html=True,
        )

        col_name, col_subj = st.columns(2)
        with col_name:
            blank_exam_name = st.text_input("Exam name", placeholder="e.g. Midterm 1", key="blank_exam_name_input")
        with col_subj:
            blank_subject = st.text_input("Subject", placeholder="e.g. Math", key="blank_subject_input")

        blank_file = st.file_uploader(
            "Upload blank exam image",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed",
            key="blank_uploader",
        )

        if blank_file is not None:
            file_key = f"{blank_file.name}_{blank_file.size}"

            if st.session_state.get("_blank_file_key") != file_key:
                # Save raw image
                upload_dir = Path(current_dir) / "frontend" / "img"
                upload_dir.mkdir(parents=True, exist_ok=True)
                raw_path = str(upload_dir / "blank_template.png")
                ImageOps.exif_transpose(Image.open(blank_file)).save(raw_path)

                with st.spinner("Analyzing layout & generating Excel template…"):
                    std_path = _standardize(raw_path, "blank_standardized")

                    weights = _find_weights()
                    if not weights:
                        st.error("No YOLO model weights found — cannot analyse layout.")
                    else:
                        try:
                            _omr_dir = str(_project_root / "ai" / "omr")
                            if _omr_dir not in sys.path:
                                sys.path.insert(0, _omr_dir)
                            from read_sheet import process_image as _rs_process_image
                            from ai.grading.template_generator import generate_answer_key_template as _generate_template

                            model = _load_yolo_model(weights)
                            ocr_reader = _get_ocr_reader()
                            args = argparse.Namespace(conf=0.25, imgsz=1024, device="0", fill_threshold=0.35, debug=False)
                            out_dir = _project_root / "runs" / "omr_results" / "blank_template"
                            out_dir.mkdir(parents=True, exist_ok=True)

                            sheet_result, _img, _grids, _dets = _rs_process_image(
                                Path(std_path), model, args, out_dir, None, ocr_reader
                            )

                            tmpl_path = out_dir / f"{Path(std_path).stem}_template.xlsx"
                            _generate_template(sheet_result, tmpl_path)

                            det_path = out_dir / f"{Path(std_path).stem}_detection.png"

                            with open(tmpl_path, "rb") as f:
                                tmpl_bytes = f.read()

                            st.session_state["_blank_file_key"] = file_key
                            st.session_state["_blank_template_bytes"] = tmpl_bytes
                            st.session_state["_blank_template_name"] = (
                                f"{blank_exam_name or 'exam'}_template.xlsx"
                            )
                            st.session_state["_blank_detection_path"] = (
                                str(det_path) if det_path.exists() else ""
                            )
                            # Save to DB so it can be loaded as an answer key later
                            if blank_exam_name and blank_subject:
                                try:
                                    db.insert_exam_file(blank_exam_name, blank_subject, tmpl_bytes)
                                except Exception:
                                    pass  # Non-critical — teacher can still download

                        except Exception as e:
                            st.error(f"Error generating template: {e}")

        # Show results (persisted in session state)
        if st.session_state.get("_blank_template_bytes"):
            det_path = st.session_state.get("_blank_detection_path", "")
            if det_path and os.path.exists(det_path):
                st.markdown("**Detected layout:**")
                st.image(det_path, use_container_width=True)
                st.caption("Verify that all question regions (MCQ, True/False, Numeric) are detected correctly.")

            st.success("✅ Template ready!")
            st.info(
                "1. Download the Excel template below.\n"
                "2. Fill in the **answer** column for each question.\n"
                "3. Upload the filled file via the *Excel Answer Sheet* tab."
            )
            st.download_button(
                "⬇ Download Excel Template",
                data=st.session_state["_blank_template_bytes"],
                file_name=st.session_state.get("_blank_template_name", "template.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="blank_template_download",
            )

    # =========================================================================
    # TAB 2: STUDENT SUBMISSIONS — grade against answer key
    # =========================================================================
    elif upload_type == "Student submissions":
        st.markdown("### Upload Student Submissions")
        st.markdown(
            "<p style='font-size:14px; opacity:0.8;'>Upload the filled-in exam sheets from your students "
            "to check and grade them against your answer key.</p>",
            unsafe_allow_html=True,
        )

        # Answer key selector ─────────────────────────────────────────────────
        st.markdown("#### Answer key")
        current_key_name = st.session_state.get("answer_key_name", "")
        if current_key_name:
            st.caption(f"Currently loaded: **{current_key_name}**")

        # Only show exams that have a filled answer key (not blank templates).
        try:
            from ai.grading.answer_key import load_answer_key as _validate_key
        except ImportError:
            _validate_key = None

        all_saved = db.list_exam_files()
        valid_keys = []
        if _validate_key is not None:
            for row in all_saved:
                db_row = db.get_exam_file(row[0])
                if db_row and db_row[2]:
                    try:
                        _validate_key(db_row[2])
                        valid_keys.append(row)
                    except ValueError:
                        pass  # blank template or bad format — skip
        else:
            valid_keys = all_saved

        if valid_keys:
            options = ["— select —"] + [
                f"{row[1]} ({row[2]})  ·  {str(row[3])[:10]}" for row in valid_keys
            ]
            selected_idx = st.selectbox(
                "Load saved answer key:",
                range(len(options)),
                format_func=lambda i: options[i],
                key="saved_key_selectbox",
            )
            if selected_idx > 0:
                chosen_row = valid_keys[selected_idx - 1]
                db_row = db.get_exam_file(chosen_row[0])
                if db_row and db_row[2]:
                    st.session_state.answer_key_bytes = db_row[2]
                    st.session_state.answer_key_name = f"{db_row[0]}_{db_row[1]}.xlsx"
        else:
            st.caption("No filled answer keys saved yet. Upload a filled Excel via the *Excel Answer Sheet* tab first.")

        # File uploader ───────────────────────────────────────────────────────
        uploaded_file = st.file_uploader(
            "Upload student exam image",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed",
            key="image_uploader",
        )

        if uploaded_file is not None:
            try:
                upload_dir = os.path.join(current_dir, "frontend", "img")
                os.makedirs(upload_dir, exist_ok=True)
                saved_path = os.path.join(upload_dir, "captured_submission.png")

                ImageOps.exif_transpose(Image.open(uploaded_file)).save(saved_path)
                st.session_state.temp_raw_path = saved_path

                with st.spinner("Standardizing student submission..."):
                    std_path = _standardize(saved_path, "standardized_output")
                    st.session_state.standardized_image_path = std_path
                    st.session_state.standardization_method = "ok" if std_path != saved_path else "fallback"

                # Clear cached OMR result so the results page re-runs for the new image.
                for key in ("omr_result", "grading_result", "_omr_np_image", "_omr_region_grids",
                            "_omr_output_dir", "_omr_stem", "_omr_graded_path", "_omr_student_info_crop"):
                    st.session_state.pop(key, None)

                st.session_state.screen = "preview"
                st.rerun()

            except Exception as e:
                st.error(f"Error processing image: {e}")

    # =========================================================================
    # TAB 3: EXCEL ANSWER SHEET — upload filled template
    # =========================================================================
    else:
        st.markdown("### Upload Excel Answer Sheet")
        st.markdown(
            "<p style='font-size:14px; opacity:0.8;'>Upload the filled-in Excel template containing the correct "
            "answers so the system can calculate student grades.</p>",
            unsafe_allow_html=True,
        )

        saved_exams = db.list_exam_files()
        exam_options = ["— Create new —"] + [
            f"{row[1]} ({row[2]})" for row in saved_exams
        ]
        selected_exam_idx = st.selectbox(
            "Select existing exam or create new:",
            range(len(exam_options)),
            format_func=lambda i: exam_options[i],
            key="excel_exam_selectbox",
        )

        if selected_exam_idx == 0:
            exam_name = st.text_input("Exam name", placeholder="e.g. Midterm 1", key="excel_new_name")
            subject   = st.text_input("Subject",   placeholder="e.g. Math, Physics", key="excel_new_subject")
            _selected_exam_id = None
        else:
            chosen = saved_exams[selected_exam_idx - 1]
            exam_name = chosen[1]
            subject   = chosen[2]
            _selected_exam_id = chosen[0]
            st.caption(f"Will update answer key for: **{exam_name}** ({subject})")

        if st.query_params.get("clear_excel") == "true":
            st.query_params.clear()
            if "excel_uploader" in st.session_state:
                del st.session_state["excel_uploader"]
            st.rerun()

        excel_file = st.file_uploader(
            "Upload Excel answer sheet",
            type=["xlsx"],
            label_visibility="collapsed",
            key="excel_uploader",
        )

        if excel_file is not None:
            st.markdown("""
                <div style="text-align: right; margin-top: -10px; margin-bottom: 15px;">
                    <a href="?clear_excel=true" target="_self" style="
                        color: #FF4B4B; font-family: 'Quicksand', sans-serif;
                        font-weight: 700; font-size: 13px; text-decoration: none;
                        display: inline-flex; align-items: center; gap: 4px;
                    " onmouseover="this.style.textDecoration='underline'"
                       onmouseout="this.style.textDecoration='none'">
                        🗑️ Delete file
                    </a>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("""
            <style>
            div[data-testid="stButton"] button[key="azota_excel_submit_btn"],
            .stApp div[data-testid="stButton"] button {
                background-color: transparent !important; color: #0052CC !important;
                border: 2px solid #0052CC !important; border-radius: 50px !important;
                min-height: 50px !important; height: 50px !important;
                font-family: 'Quicksand', sans-serif !important; font-weight: 700 !important;
                letter-spacing: 1px !important; text-transform: uppercase !important;
                font-size: 16px !important; width: 100% !important;
                display: flex !important; align-items: center !important;
                justify-content: center !important; transition: all 0.3s ease !important;
                box-shadow: none !important; margin-top: 15px !important;
            }
            div[data-testid="stButton"] button:hover {
                background-color: rgba(0, 82, 204, 0.08) !important;
                color: #0041A3 !important; border-color: #0041A3 !important;
            }
            div[data-testid="stButton"] button p {
                font-family: 'Quicksand', sans-serif !important; font-weight: 700 !important;
                color: inherit !important; font-size: 16px !important;
                text-transform: uppercase !important; letter-spacing: 1px !important;
                margin: 0 !important; text-shadow: none !important;
            }
            </style>
        """, unsafe_allow_html=True)

        if st.button("Upload Excel", key="azota_excel_submit_btn", use_container_width=True):
            if not exam_name or not subject:
                st.error("Please fill in exam name and subject (or select an existing exam above).")
                st.stop()
            if excel_file is None:
                st.error("Please upload an Excel file.")
                st.stop()

            try:
                upload_dir = os.path.join(current_dir, "frontend", "excel")
                os.makedirs(upload_dir, exist_ok=True)
                saved_path = os.path.join(upload_dir, excel_file.name)
                with open(saved_path, "wb") as f:
                    f.write(excel_file.getbuffer())

                file_bytes = excel_file.getvalue()
                if _selected_exam_id is not None:
                    db.update_exam_file(_selected_exam_id, file_bytes)
                else:
                    db.insert_exam_file(exam_name, subject, file_bytes)

                st.session_state.answer_key_bytes = file_bytes
                st.session_state.answer_key_name = excel_file.name

                st.success("✅ Excel file uploaded successfully!")

                import time
                time.sleep(1)
                st.session_state.screen = "camera"
                st.rerun()

            except Exception as e:
                st.error(f"Database error: {e}")

    st.markdown('</div>', unsafe_allow_html=True)
