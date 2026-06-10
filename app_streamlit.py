# app_streamlit.py (Plaatsen in de ROOT-map)
import streamlit as st
import os
import base64

# Importeer de 3 netjes opgesplitste pagina-functies uit de frontend map
from frontend.camera_page import show_camera_page
from frontend.preview_page import show_preview_page
from frontend.results_page import show_results_page
from frontend.edit_result_page import show_edit_result_page

# --- 1. PAGE CONFIGURATION & THEME ---
st.set_page_config(page_title="Azota AI Production App", page_icon="🎯", layout="centered")

COLOR_PRIMARY = "#0052CC"
COLOR_SECONDARY = "#172B4D"
COLOR_BG_LIGHT = "#F4F5F7"
COLOR_CARD_WHITE = "#FFFFFF"

# --- 2. GLOBAL PIXEL-PERFECT AZOTA CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG_LIGHT}; }}
    
    /* Witruimte minimaliseren voor een native web-app gevoel op mobiel */
    div[data-testid="stMainBlockContainer"] {{ 
        padding-top: 0px !important; 
        padding-bottom: 0px !important; 
        padding-left: 1rem !important; 
        padding-right: 1rem !important; 
    }}
    header, footer {{ visibility: hidden; }}
    
    /* Topbar & Header Navigatie Styling */
    .logo-container-preview {{ 
        background-color: {COLOR_CARD_WHITE}; 
        height: 65px; 
        display: flex; 
        flex-direction: row; 
        align-items: center; 
        justify-content: space-between; 
        width: 100%; 
        position: fixed; 
        top: 0; 
        left: 0; 
        z-index: 9999; 
        border-bottom: 1px solid #E2E8F0; 
        padding: 0 20px; 
    }}
    .logo-container-camera {{ 
        background-color: {COLOR_CARD_WHITE}; 
        height: 65px; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        width: 100%; 
        position: fixed; 
        top: 0; 
        left: 0; 
        z-index: 9999; 
        border-bottom: 1px solid #E2E8F0; 
    }}
    .topbar-title-centered {{ 
        color: {COLOR_SECONDARY}; 
        font-family: sans-serif; 
        font-size: 18px; 
        font-weight: bold; 
        text-align: center; 
        flex-grow: 1; 
    }}
    .main-content {{ margin-top: 75px !important; text-align: center; }}
    
    /* Teksten, Titels & Badges */
    .viewfinder-text-title {{ color: {COLOR_SECONDARY}; font-family: sans-serif; font-size: 18px; font-weight: bold; text-align: center; margin-top: 10px; }}
    .viewfinder-text-sub {{ color: {COLOR_SECONDARY}; font-family: sans-serif; font-size: 13px; text-align: center; margin-bottom: 15px; }}
    .evaluation-title {{ color: black; font-family: sans-serif; font-size: 22px; font-weight: bold; text-align: center; margin-top: 15px; }}
    .score-badge {{ background-color: green; color: white; font-weight: bold; font-size: 16px; padding: 8px 20px; border-radius: 15px; text-align: center; width: fit-content; margin: 10px auto 20px auto; }}

    /* Knoppen Containers (Gecentreerd, ontworpen voor mobiel) */
    .custom-btn-container {{ 
        display: flex !important; 
        flex-direction: row !important; 
        justify-content: center !important; 
        align-items: center !important; 
        gap: 12px !important; 
        width: 100% !important; 
        max-width: 320px !important; 
        margin: 20px auto 30px auto !important; 
    }}
    .custom-btn-container div {{ flex: 1 !important; }}
    .custom-btn-container .stButton>button {{ 
        width: 100% !important; 
        height: 45px !important; 
        font-weight: bold !important; 
        font-size: 15px !important; 
        border-radius: 22px !important; 
    }}
    
    /* Rechter/Primaire knop (Volledig blauw gekleurd) */
    .custom-btn-container div:nth-child(2) .stButton>button {{ background-color: {COLOR_PRIMARY} !important; color: white !important; border: none !important; }}
    /* Linker/Secundaire knop (Transparant met blauwe rand) */
    .custom-btn-container div:nth-child(1) .stButton>button {{ background-color: transparent !important; color: {COLOR_PRIMARY} !important; border: 2px solid {COLOR_PRIMARY} !important; }}
    </style>
""", unsafe_allow_html=True)

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

# Verkeersregelaar: Toon de juiste pagina op basis van st.session_state.screen
# Onderaan in je centrale app_streamlit.py:
if st.session_state.screen == "camera":
    show_camera_page(current_dir, encoded_logo_full)

elif st.session_state.screen == "preview":
    show_preview_page(logo_html, COLOR_SECONDARY)

elif st.session_state.screen == "results":
    show_results_page(logo_html, local_img_path)

elif st.session_state.screen == "edit_results":
    show_edit_result_page(logo_html)