import streamlit as st
import os
from PIL import Image, ImageOps
from backend import database as db

def show_camera_page(current_dir, encoded_logo_full):
    if encoded_logo_full:
        st.markdown(f'<div class="logo-container-camera"><img src="data:image/png;base64,{encoded_logo_full}" width="110"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="logo-container-camera"><h3 style="margin:0;">Azota</h3></div>', unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<p class="viewfinder-text-title">Scan or Upload Exam Sheet</p>', unsafe_allow_html=True)
    st.markdown('<p class="viewfinder-text-sub">Upload a photo of the exam OR an Excel answer sheet.</p>', unsafe_allow_html=True)

    # CHOICE: image of excel
    upload_type = st.radio(
    "What do you want to upload?",
    ["Exam image", "Excel answer sheet"],
    horizontal=True,
    key="upload_type",
    label_visibility="collapsed"
)

    # =========================
    # IMAGE FLOW
    # =========================
    if upload_type == "Exam image":
        uploaded_file = st.file_uploader(
            "Upload exam image",
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
                st.session_state.screen = "preview"
                st.rerun()

            except Exception as e:
                st.error(f"Fout bij image verwerking: {e}")

    # =========================
    # 📄 EXCEL FLOW
    # =========================
    else:
        st.markdown("### Upload Excel answer sheet")

        exam_name = st.text_input("Name of exam", placeholder="e.g. Midterm 1")
        subject = st.text_input("Subject", placeholder="e.g. Math, Physics")

        excel_file = st.file_uploader(
            "Upload Excel answer sheet",
            type=["xlsx"],
            label_visibility="collapsed",
            key="excel_uploader"
        )

        if st.button("Upload Excel"):
            if not exam_name or not subject:
                st.error("Please fill in exam name and subject.")
                st.stop()

            if excel_file is None:
                st.error("Please upload an Excel file.")
                st.stop()

            upload_dir = os.path.join(current_dir, "frontend", "excel")
            os.makedirs(upload_dir, exist_ok=True)

            saved_path = os.path.join(upload_dir, excel_file.name)

            with open(saved_path, "wb") as f:
                f.write(excel_file.getbuffer())

            db.insert_exam_file(exam_name, subject, saved_path)

            # RESET STATE (belangrijk)
            st.session_state.excel_path = None
            st.session_state.exam_name = None
            st.session_state.subject = None

            # popup
            st.success("✅ Excel file uploaded successfully!")

            # ⏳ korte delay UX (optioneel)
            import time
            time.sleep(1)

            # terug naar home
            st.session_state.screen = "camera"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)