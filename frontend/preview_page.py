import streamlit as st
import os
from backend import database as db

def show_preview_page(logo_html, COLOR_SECONDARY):
    params = st.query_params
    if "action" in params and params["action"] == "go_back":
        st.query_params.clear()
        st.session_state.screen = "camera"
        st.rerun()

    st.markdown(f"""
    <div class="logo-container-preview">
        <a href="?action=go_back" target="_self" class="topbar-arrow-clickable">‹</a>
        <div class="topbar-title-centered">Preview submission</div>
        <div class="topbar-logo-right">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="padding: 12px; border-radius: 8px; margin-bottom: 12px; text-align: center;">
        <span style="color: {COLOR_SECONDARY}; font-size: 13px; font-family: sans-serif;">
            ⚠️ <b>Make sure all answers are clearly legible before submitting.</b>
        </span>
    </div>
    """, unsafe_allow_html=True)

    display_path = st.session_state.get("standardized_image_path") or st.session_state.get("temp_raw_path", "")
    if os.path.exists(display_path):
        st.image(display_path, use_container_width=True)
        method = st.session_state.get("standardization_method", "")
        if method and method not in ("error", "unavailable"):
            st.caption(f"Standardized · method: {method}")

    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Retake", key="retake_btn"):
            for _k in ("omr_result", "grading_result", "_grading_key_id",
                       "_omr_np_image", "_omr_region_grids", "_omr_output_dir",
                       "_omr_stem", "_omr_graded_path", "_omr_student_info_crop"):
                st.session_state.pop(_k, None)
            st.session_state.screen = "camera"
            st.rerun()
            
    with col2:
        if st.button("Submit", key="submit_btn"):
            st.session_state.current_scan_id = 1
            st.session_state.screen = "results"
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)