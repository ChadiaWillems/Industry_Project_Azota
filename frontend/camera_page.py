import streamlit as st
import os
from PIL import Image, ImageOps

def show_camera_page(current_dir, encoded_logo_full):
    if encoded_logo_full:
        st.markdown(f'<div class="logo-container-camera"><img src="data:image/png;base64,{encoded_logo_full}" width="110"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="logo-container-camera"><h3 style="margin:0;">Azota</h3></div>', unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<p class="viewfinder-text-title">Scan or Upload Exam Sheet</p>', unsafe_allow_html=True)
    st.markdown('<p class="viewfinder-text-sub">Click below to take a live photo with your camera or select a file from your photo library.</p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose an action", 
        type=["png", "jpg", "jpeg"], 
        label_visibility="collapsed", 
        key="main_file_uploader"
    )
    st.markdown('</div>', unsafe_allow_html=True)

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
            st.error(f"Fout bij het verwerken van de afbeelding: {e}")