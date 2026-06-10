# app_streamlit.py (Plaatsen in de ROOT-map)
import streamlit as st
import os
import base64
from backend.database import init_db

init_db()

# Importeer de 3 netjes opgesplitste pagina-functies uit de frontend map
from frontend.camera_page import show_camera_page
from frontend.preview_page import show_preview_page
from frontend.results_page import show_results_page
from frontend.edit_result_page import show_edit_result_page

from frontend.theme import inject_global_css, COLOR_SECONDARY, COLOR_PRIMARY, COLOR_BG_LIGHT, COLOR_CARD_WHITE, FONT_FAMILY

st.set_page_config(
    page_title="Azota AI Production App",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

inject_global_css()

# --- 3. GLOBAL ASSETS LOADERS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
local_img_path = os.path.join(current_dir, "frontend", "img", "autocorrection_img.png")
local_logo_path = os.path.join(current_dir, "frontend", "img", "Azota_logo.png")
logo_full_path = os.path.join(current_dir, "frontend", "img", "Azota_logo_full.png")

def get_base64_img(path):
    if os.path.exists(path):
        with open(path, "rb") as f: 
            return base64.b64encode(f.read()).decode('utf-8')
    return ""

encoded_logo = get_base64_img(local_logo_path)
encoded_logo_full = get_base64_img(logo_full_path)
logo_html = f'<img src="data:image/png;base64,{encoded_logo}" height="28">' if encoded_logo else '🎯'

# --- 4. NAVIGATION ROUTER (State Machine) ---
if "screen" not in st.session_state:
    st.session_state.screen = "camera"

if st.session_state.screen == "camera":
    show_camera_page(current_dir, encoded_logo_full)

elif st.session_state.screen == "preview":
    show_preview_page(logo_html, COLOR_SECONDARY)

elif st.session_state.screen == "results":
    show_results_page(logo_html, local_img_path)

elif st.session_state.screen == "edit_results":
    show_edit_result_page(logo_html)
