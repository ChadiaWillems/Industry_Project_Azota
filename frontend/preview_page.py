import streamlit as st
import os
from backend import database as db

def show_preview_page(logo_html, COLOR_SECONDARY):
    # --- 1. PARAMS & NAVIGATION ---
    params = st.query_params
    if "action" in params and params["action"] == "go_back":
        st.query_params.clear()
        st.session_state.screen = "camera"
        st.rerun()

    # --- 2. TOPBAR RENDERING ---
    st.markdown(f"""
    <div class="logo-container-preview">
        <a href="?action=go_back" target="_self" class="topbar-arrow-clickable">‹</a>
        <div class="topbar-title-centered">Preview submission</div>
        <div class="topbar-logo-right">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    # --- 3. WARNING ACCENT BOX ---
    st.markdown(f"""
    <div style="padding: 12px; border-radius: 8px; margin-bottom: 12px; text-align: center;">
        <span style="color: {COLOR_SECONDARY}; font-size: 13px; font-family: sans-serif;">
            ⚠️ <b>Make sure all answers are clearly legible before submitting.</b>
        </span>
    </div>
    """, unsafe_allow_html=True)

    # --- 4. SUBMISSION IMAGE DISPLAY ---
    display_path = st.session_state.get("standardized_image_path") or st.session_state.get("temp_raw_path", "")
    if os.path.exists(display_path):
        st.image(display_path, use_container_width=True)
        method = st.session_state.get("standardization_method", "")
        if method and method not in ("error", "unavailable"):
            st.caption(f"Standardized · method: {method}")

    st.write("")
    
    # --- 5. BUTTON CALLBACK FUNCTIONS ---
    def on_retake_clicked():
        for _k in ("omr_result", "grading_result", "_grading_key_id",
                   "_omr_np_image", "_omr_region_grids", "_omr_output_dir",
                   "_omr_stem", "_omr_graded_path", "_omr_student_info_crop"):
            st.session_state.pop(_k, None)
        st.session_state.screen = "camera"

    def on_submit_clicked():
        st.session_state.current_scan_id = 1
        st.session_state.screen = "results"

    # --- 6. GLOBAAL EN DIRECT CSS PAD (Kogelvrij via Column Indexing) ---
    st.html("""
        <style>
        /* Versmal en centreer de knoppen-balk */
        div[data-testid="stHorizontalBlock"] {
            max-width: 320px !important;
            margin: 25px auto !important;
            gap: 16px !important;
            display: flex !important;
            justify-content: center !important;
        }

        /* Basis layout voor beide knoppen */
        div[data-testid="stHorizontalBlock"] button {
            height: 44px !important;
            font-weight: bold !important;
            font-size: 15px !important;
            border-radius: 50px !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
        }

        /* ⚪ LINKER KOLOM: RETAKE */
        div[data-testid="stHorizontalBlock"] > div:nth-child(1) button {
            background-color: transparent !important;
            color: #0052CC !important;
            border: 2px solid #0052CC !important;
            box-shadow: none !important;
        }

        /* 🔵 RECHTER KOLOM: SUBMIT */
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
            background-color: #0052CC !important;
            color: white !important;
            border: none !important;
            box-shadow: 0px 4px 12px rgba(0, 82, 204, 0.2) !important;
        }
        
        /* Hover effecten voor de finishing touch */
        div[data-testid="stHorizontalBlock"] > div:nth-child(1) button:hover {
            background-color: rgba(0, 82, 204, 0.05) !important;
        }
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) button:hover {
            background-color: #0043A4 !important;
        }
        </style>
    """)

    # --- 7. CLEAN BUTTON RENDER ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.button("Retake", key="retake_btn", on_click=on_retake_clicked, use_container_width=True)
            
    with col2:
        st.button("Submit", key="submit_btn", on_click=on_submit_clicked, use_container_width=True)
            
    st.markdown('</div>', unsafe_allow_html=True)