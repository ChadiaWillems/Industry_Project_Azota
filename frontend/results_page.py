# frontend/results_page.py
import streamlit as st
import os

def show_results_page(logo_html, local_img_path):
    # --- 1. SCHERMSPECIFIEKE DESIGN OVERRIDES (CSS) ---
    st.markdown("""
        <style>
        /* Grijze topbar override zoals in het screenshot */
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
        
        /* Grote score rechtsboven */
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
        
        /* Subtiele info tekst met info-icoon */
        .info-text-screenshot {
            text-align: left;
            font-size: 13px;
            color: #222222;
            font-family: sans-serif;
            margin-bottom: 15px;
            padding-left: 10px;
        }
        
        /* Grijze knoppen styling onderaan */
        .screenshot-btn-container {
            display: flex !important;
            flex-direction: row !important;
            justify-content: center !important;
            align-items: center !important;
            gap: 15px !important;
            width: 100% !important;
            max-width: 240px !important;
            margin: 20px auto 30px auto !important;
        }
        .screenshot-btn-container div { flex: 1 !important; }
        .screenshot-btn-container .stButton>button {
            background-color: #D6D6D6 !important;
            color: #000000 !important;
            border: none !important;
            height: 38px !important;
            font-size: 15px !important;
            font-weight: normal !important;
            border-radius: 20px !important;
            box-shadow: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. TOP BAR ACTIE ---
    params = st.query_params
    if "action" in params and params["action"] == "go_back":
        st.query_params.clear()
        st.session_state.screen = "preview"
        st.rerun()

    # Driedelige topbar conform screenshot
    st.markdown(f"""
    <div class="logo-container-preview">
        <a href="?action=go_back" target="_self" class="topbar-arrow-clickable">‹</a>
        <div class="topbar-title-centered">Review submission</div>
        <div class="topbar-logo-right">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # Start hoofdcontent container
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # --- 3. SCORE DISPLAY (Rechtsboven) ---
    # Hardcoded 10/15 zoals gevraagd voor de perfecte demo-look
    st.markdown('<div class="right-score-display">10/15</div>', unsafe_allow_html=True)
    
    # --- 4. INFO TEXT LINE ---
    st.markdown('<p class="info-text-screenshot">🛈 This is the autocorrected and auto-graded version.</p>', unsafe_allow_html=True)
    
    # --- 5. IMAGE CANVAS ---
    if os.path.exists(local_img_path):
        st.image(local_img_path, use_container_width=True)
    else:
        # Fallback naar de upload als de mock_img er onverhoopt niet staat
        real_photo_path = st.session_state.get("temp_raw_path", "")
        if real_photo_path and os.path.exists(real_photo_path):
            st.image(real_photo_path, use_container_width=True)
        else:
            st.error("Submission image not found.")
        
    # --- 6. BUTTONS AREA (Edit & Save gecentreerd onder de afbeelding) ---
    st.markdown('<div class="screenshot-btn-container">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Edit", key="screenshot_edit_btn"):
            st.session_state.screen = "edit_results"
            st.rerun()
            
    with col2:
        if st.button("Save", key="screenshot_save_btn"):
            st.session_state.screen = "camera"
            st.rerun()
            
    st.markdown('</div></div>', unsafe_allow_html=True)