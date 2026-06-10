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

    saved_path = st.session_state.get("temp_raw_path", "")
    if os.path.exists(saved_path):
        st.image(saved_path, use_container_width=True)

    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Retake", key="retake_btn"):
            st.session_state.screen = "camera"
            st.rerun()
            
    with col2:
        if st.button("Submit", key="submit_btn"):
            with st.spinner("AI is grading the sheet..."):
                # [MOCK DATA VOOR FRONTEND TESTING]
                mock_answers = [
                    {"question": 1, "ai": "A", "is_correct": 1},
                    {"question": 2, "ai": "B", "is_correct": 0},
                    {"question": 3, "ai": "C", "is_correct": 1},
                    {"question": 4, "ai": "A", "is_correct": 1},
                    {"question": 5, "ai": "D", "is_correct": 0}
                ]
                
                # 🚫 TIJDELIJK BEVROREN: We slaan nog even niets op in SQLite
                # scan_id = db.insert_new_scan(
                #     score_earned=initial_score,
                #     score_total=len(mock_answers),
                #     img_raw=saved_path,
                #     img_standardized=saved_path,
                #     img_sections=saved_path,
                #     img_graded=saved_path,
                #     answers_list=mock_answers
                # )
                
                # 🎯 DIRECT DOOR NAAR DE RESULTATEN MET EEN TEST-ID
                st.session_state.current_scan_id = 1  # Fake ID voor de frontend
                st.session_state.screen = "results"
                st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)