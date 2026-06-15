import streamlit as st
import os
import sys
from pathlib import Path
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

def show_camera_page(current_dir, encoded_logo_full):
    if encoded_logo_full:
        st.markdown(f'<div class="logo-container-camera"><img src="data:image/png;base64,{encoded_logo_full}" width="110"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="logo-container-camera"><h3 style="margin:0;">Azota</h3></div>', unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<p class="viewfinder-text-title">Scan or Upload Exam Sheets</p>', unsafe_allow_html=True)
    st.markdown('<p class="viewfinder-text-sub">Select what you want to upload to manage your exam process.</p>', unsafe_allow_html=True)

    # 3 OPTIES: Blank exam, Student submissions of de Excel sleutel
    upload_type = st.radio(
        "What do you want to upload?",
        ["Blank exam sheet", "Student submissions", "Excel answer sheet"],
        horizontal=True,
        key="upload_type",
        label_visibility="collapsed"
    )

    # =================================================================
    # 📄 TABS 1: BLANK EXAM SHEET (To generate Excel)
    # =================================================================
    if upload_type == "Blank exam sheet":
        st.markdown("### Upload Blank Exam Sheet")
        st.markdown("<p style='font-size:14px; opacity:0.8;'>Upload a clear photo or scan of the empty exam. The system will automatically generate an Excel answer sheet template for you.</p>", unsafe_allow_html=True)
        
        blank_file = st.file_uploader(
            "Upload blank exam image",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed",
            key="blank_uploader"
        )

        if blank_file is not None:
            try:
                upload_dir = os.path.join(current_dir, "frontend", "img")
                os.makedirs(upload_dir, exist_ok=True)
                saved_path = os.path.join(upload_dir, "blank_template.png")

                image = Image.open(blank_file)
                fixed_image = ImageOps.exif_transpose(image)
                fixed_image.save(saved_path)

                st.session_state.temp_raw_path = saved_path

                with st.spinner("Analyzing layout & generating Excel template..."):
                    if _STANDARDIZATION_AVAILABLE:
                        # (Je bestaande backend logica om de template te bouwen)
                        pass

                st.success("🎉 Blank sheet processed! Redirecting to preview/download...")
                st.session_state.screen = "preview"
                st.rerun()

            except Exception as e:
                st.error(f"Error processing blank sheet: {e}")

    # =================================================================
    # 📝 TAB 2: STUDENT SUBMISSIONS (To grade)
    # =================================================================
    elif upload_type == "Student submissions":
        st.markdown("### Upload Student Submissions")
        st.markdown("<p style='font-size:14px; opacity:0.8;'>Upload the filled-in exam sheets from your students to check and grade them against your answer key.</p>", unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Upload student exam image",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed",
            key="image_uploader"
        )

        if uploaded_file is not None:
            try:
                upload_dir = os.path.join(current_dir, "frontend", "img")
                os.makedirs(upload_dir, exist_ok=True)
                saved_path = os.path.join(upload_dir, "captured_submission.png")

                image = Image.open(uploaded_file)
                fixed_image = ImageOps.exif_transpose(image)
                fixed_image.save(saved_path)

                st.session_state.temp_raw_path = saved_path

                with st.spinner("Standardizing student submission..."):
                    if _STANDARDIZATION_AVAILABLE:
                        try:
                            std_out = _project_root / "frontend" / "img" / "standardized_output"
                            output_dirs = create_output_dirs(str(std_out))
                            method = standardize_single_image(Path(saved_path), output_dirs)
                            readable_path = str(output_dirs["readable"] / f"{Path(saved_path).stem}_readable.png")
                            if os.path.exists(readable_path):
                                st.session_state.standardized_image_path = readable_path
                                st.session_state.standardization_method = method
                            else:
                                st.session_state.standardized_image_path = saved_path
                                st.session_state.standardization_method = "error"
                        except Exception as e:
                            st.warning(f"Standardization failed: {e}")
                            st.session_state.standardized_image_path = saved_path
                            st.session_state.standardization_method = "error"
                    else:
                        st.session_state.standardized_image_path = saved_path
                        st.session_state.standardization_method = "unavailable"

                st.session_state.screen = "preview"
                st.rerun()

            except Exception as e:
                st.error(f"Fout bij image verwerking: {e}")

    # =================================================================
    # 📊 TAB 3: EXCEL ANSWER SHEET (The key)
    # =================================================================
    else:
        st.markdown("### Upload Excel Answer Sheet")
        st.markdown("<p style='font-size:14px; opacity:0.8;'>Upload the filled-in Excel template containing the correct answers so the system can calculate student grades.</p>", unsafe_allow_html=True)

        exam_name = st.text_input("Name of exam", placeholder="e.g. Midterm 1")
        subject = st.text_input("Subject", placeholder="e.g. Math, Physics")

        if st.query_params.get("clear_excel") == "true":
            st.query_params.clear()
            if "excel_uploader" in st.session_state:
                del st.session_state["excel_uploader"]
            st.rerun()

        excel_file = st.file_uploader(
            "Upload Excel answer sheet",
            type=["xlsx"],
            label_visibility="collapsed",
            key="excel_uploader"
        )

        if excel_file is not None:
            st.markdown("""
                <div style="text-align: right; margin-top: -10px; margin-bottom: 15px;">
                    <a href="?clear_excel=true" target="_self" style="
                        color: #FF4B4B;
                        font-family: 'Quicksand', sans-serif;
                        font-weight: 700;
                        font-size: 13px;
                        text-decoration: none;
                        display: inline-flex;
                        align-items: center;
                        gap: 4px;
                    " onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">
                        🗑️ Delete file
                    </a>
                </div>
            """, unsafe_allow_html=True)

        # Custom outlined button styling injecteren voor dit tabblad
        st.markdown("""
            <style>
            div[data-testid="stButton"] button[key="azota_excel_submit_btn"],
            .stApp div[data-testid="stButton"] button {
                background-color: transparent !important;
                color: #0052CC !important;
                border: 2px solid #0052CC !important;
                border-radius: 50px !important;
                min-height: 50px !important;
                height: 50px !important;
                font-family: 'Quicksand', sans-serif !important;
                font-weight: 700 !important;
                letter-spacing: 1px !important;
                text-transform: uppercase !important;
                font-size: 16px !important;
                width: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                transition: all 0.3s ease !important;
                box-shadow: none !important;
                margin-top: 15px !important;
            }
            
            div[data-testid="stButton"] button:hover {
                background-color: rgba(0, 82, 204, 0.08) !important;
                color: #0041A3 !important;
                border-color: #0041A3 !important;
            }
            
            div[data-testid="stButton"] button p {
                font-family: 'Quicksand', sans-serif !important;
                font-weight: 700 !important;
                color: inherit !important;
                font-size: 16px !important;
                text-transform: uppercase !important;
                letter-spacing: 1px !important;
                margin: 0 !important;
                text-shadow: none !important;
            }
            </style>
        """, unsafe_allow_html=True)

        if st.button("Upload Excel", key="azota_excel_submit_btn", use_container_width=True):
            if not exam_name or not subject:
                st.error("Please fill in exam name and subject.")
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

                db.insert_exam_file(
                    exam_name,
                    subject,
                    file_bytes
                )

                st.success("✅ Excel file uploaded successfully!")

                st.session_state.excel_path = None
                st.session_state.exam_name = None
                st.session_state.subject = None

                import time
                time.sleep(1)

                st.session_state.screen = "camera"
                st.rerun()
                
            except Exception as e:
                st.error(f"Database error: {e}")

    st.markdown('</div>', unsafe_allow_html=True)