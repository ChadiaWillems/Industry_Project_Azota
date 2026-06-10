import streamlit as st

# =========================
# 🎨 AZOTA DESIGN TOKENS
# =========================
COLOR_PRIMARY = "#0052CC"
COLOR_SECONDARY = "#172B4D"
COLOR_BG_LIGHT = "#F4F5F7"
COLOR_CARD_WHITE = "#FFFFFF"

FONT_FAMILY = "'Quicksand', sans-serif"


# =========================
# 🎯 GLOBAL CSS INJECTION
# =========================
def inject_global_css():
    st.markdown(f"""
    <style>

    /* App background */
    .stApp {{
        background-color: {COLOR_BG_LIGHT};
    }}

    /* Hide Streamlit chrome */
    header, footer {{
        visibility: hidden;
    }}

    /* Layout spacing */
    div[data-testid="stMainBlockContainer"] {{
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}

    /* =========================
       TOPBARS
    ========================= */
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

    .main-content {{
        margin-top: 75px !important;
        text-align: center;
    }}

    /* =========================
       TEXT STYLES
    ========================= */
    .viewfinder-text-title {{
        color: {COLOR_SECONDARY};
        font-size: 18px;
        font-weight: bold;
        text-align: center;
    }}

    .viewfinder-text-sub {{
        color: {COLOR_SECONDARY};
        font-size: 13px;
        text-align: center;
        opacity: 0.8;
    }}

    .evaluation-title {{
        color: black;
        font-size: 22px;
        font-weight: bold;
        text-align: center;
    }}

    /* =========================
       FILE UPLOADER AZOTA STYLE
    ========================= */

    div[data-testid="stFileUploader"] {{
    background-color: {COLOR_CARD_WHITE};
    border: 1px dashed {COLOR_PRIMARY};
    border-radius: 14px;
    padding: 12px;
}}

div[data-testid="stFileUploader"] button {{
    background-color: {COLOR_PRIMARY} !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: bold !important;
    border: none !important;
    padding: 6px 14px !important;
}}

div[data-testid="stFileUploader"] button:hover {{
    background-color: #0041A3 !important;
}}

div[data-testid="stFileUploader"] section {{
    color: {COLOR_SECONDARY} !important;
}}

    /* =========================
       RADIO / CHECKBOX PRIMARY COLOR
    ========================= */
    div[data-testid="stRadio"] label span:first-child {{
        border-color: {COLOR_PRIMARY} !important;
    }}

    div[data-testid="stRadio"] input:checked + div span:first-child div {{
        background-color: {COLOR_PRIMARY} !important;
    }}

    div[data-testid="stRadio"] label:hover span:first-child {{
        border-color: {COLOR_PRIMARY} !important;
    }}

    </style>
""", unsafe_allow_html=True)