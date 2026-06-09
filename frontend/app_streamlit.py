import streamlit as st
import os
import base64
from PIL import Image, ImageOps

# --- CONFIGURATIE & THEMA ---
st.set_page_config(page_title="Azota AI Production App", page_icon="🎯", layout="centered")

COLOR_PRIMARY = "#0052CC"
COLOR_SECONDARY = "#172B4D"
COLOR_BG_LIGHT = "#F4F5F7"
COLOR_CARD_WHITE = "#FFFFFF"

# --- DESIGN CSS (Perfect gecentreerd en compact) ---
st.markdown(f"""
    <style>
    /* Basis app styling */
    .stApp {{ 
        background-color: {COLOR_BG_LIGHT}; 
    }}
    
    /* VERWIJDER DE STANDAARD STREAMLIT WITRUIMTE BOVENAAN */
    div[data-testid="stMainBlockContainer"] {{
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}
    
    /* Haal ook de automatische extra witruimte TUSSEN elementen weg */
    div[data-testid="stVerticalBlock"] {{
        gap: 0.5rem !important;
    }}
    
    /* Verberg Streamlit rommel */
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* DRIEDELIGE PIXEL-PERFECTE TOPBAR */
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
    
    /* Klikbare back chevron in HTML */
    .topbar-arrow-clickable {{
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 32px;
        font-weight: 200;
        color: #000000;
        cursor: pointer;
        width: 40px;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        user-select: none;
        -webkit-user-select: none;
        text-decoration: none !important;
    }}
    
    .topbar-title-centered {{
        color: {COLOR_SECONDARY};
        font-family: sans-serif;
        font-size: 18px;
        font-weight: bold;
        text-align: center;
        flex-grow: 1;
        margin-top: 2px;
    }}
    
    .topbar-logo-right {{
        width: 40px;
        display: flex;
        align-items: center;
        justify-content: flex-end;
    }}
    
    /* SCHUIF DE CONTENT COMPACTER TEGEN DE TOPBAR AAN */
    .main-content {{
        margin-top: 55px !important; 
    }}
    
    /* Teksten */
    .viewfinder-text-title {{
        color: {COLOR_SECONDARY};
        font-family: sans-serif;
        font-size: 18px;
        font-weight: bold;
        text-align: center;
        margin-top: 5px;
        margin-bottom: 0px;
    }}
    .viewfinder-text-sub {{
        color: {COLOR_SECONDARY};
        font-family: sans-serif;
        font-size: 13px;
        text-align: center;
        margin-bottom: 15px;
        padding: 0 10px;
    }}
    
    /* Wit metadata kaartje */
    .info-box {{
        background-color: {COLOR_CARD_WHITE}; 
        padding: 12px 15px; 
        border-radius: 12px;
        margin-bottom: 5px;
        border: 1px solid #E2E8F0;
    }}

    /* 🛠️ ULTIEME HORIZONTALE CENTRERING FIX */
    /* We pakken de Streamlit kolommen-container en dwingen hem smal en gecentreerd in het midden te staan */
    div[data-testid="stHorizontalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        justify-content: center !important; 
        align-items: center !important;
        gap: 12px !important; /* Compacte ruimte tussen Retake en Submit */
        width: 100% !important;
        max-width: 250px !important; /* Dwingt ze dicht naar elkaar toe */
        margin: 20px auto 0 auto !important; /* Centreert het gehele blok op je scherm */
    }}
    
    /* Zorg dat beide kolommen exact evenveel ruimte innemen */
    div[data-testid="stHorizontalBlock"] > div {{
        flex: 1 !important;
        min-width: 0 !important;
        width: auto !important;
    }}

    /* Algemene styling voor BEIDE Azota-knoppen */
    div[data-testid="stHorizontalBlock"] .stButton > button {{
        width: 100% !important;
        height: 44px !important;
        font-weight: bold !important;
        font-size: 15px !important;
        border-radius: 50px !important; /* Prachtige capsule pilvorm */
        letter-spacing: 0.5px !important;
        transition: all 0.2s ease !important;
    }}

    /* 🔵 RECHTER KNOP: SUBMIT (Volledig blauw ingekleurd + zachte schaduw) */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) .stButton > button {{
        background-color: #0052CC !important;
        color: white !important;
        border: none !important;
        box-shadow: 0px 4px 12px rgba(0, 82, 204, 0.2) !important;
    }}

    /* ⚪ LINKER KNOP: RETAKE (Transparante achtergrond + blauwe rand) */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton > button {{
        background-color: transparent !important;
        color: #0052CC !important;
        border: 2px solid #0052CC !important;
        box-shadow: none !important;
    }}
    </style>
""", unsafe_allow_html=True)

# --- MAPSTRUCTUUR & ASSETS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
logo_full = os.path.join(current_dir, "img", "Azota_logo_full.png")
logo_simple = os.path.join(current_dir, "img", "Azota_logo.png")

# --- BASE64 LOGO HELPERS ---
def get_base64_img(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

encoded_logo_full = get_base64_img(logo_full)
encoded_logo_simple = get_base64_img(logo_simple)

# --- NAVIGATIE STATE ---
if "screen" not in st.session_state:
    st.session_state.screen = "camera"

# Query parameters gebruiken om de HTML-klik op te vangen
params = st.query_params
if "action" in params and params["action"] == "go_back":
    st.query_params.clear()
    st.session_state.screen = "camera"
    st.rerun()

# ==========================================
# SCHERM 1: SCAN / UPLOAD SCHERM
# ==========================================
if st.session_state.screen == "camera":
    if encoded_logo_full:
        st.markdown(f'<div class="logo-container-camera"><img src="data:image/png;base64,{encoded_logo_full}" width="110"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="logo-container-camera"><h3 style="margin:0;">Azota</h3></div>', unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<p class="viewfinder-text-title">Scan or Upload Exam Sheet</p>', unsafe_allow_html=True)
    st.markdown('<p class="viewfinder-text-sub">Click below to take a live photo with your camera or select a file from your photo library.</p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Choose an action", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file is not None:
        upload_dir = os.path.join(current_dir, "img")
        os.makedirs(upload_dir, exist_ok=True)
        saved_path = os.path.join(upload_dir, "captured_submission.png")
        
        image = Image.open(uploaded_file)
        fixed_image = ImageOps.exif_transpose(image)
        fixed_image.save(saved_path)
            
        st.session_state.screen = "preview"
        st.rerun()

# ==========================================
# SCHERM 2: PREVIEW SCHERM
# ==========================================
elif st.session_state.screen == "preview":
    logo_html = f'<img src="data:image/png;base64,{encoded_logo_simple}" height="28">' if encoded_logo_simple else '🎯'
    
    st.markdown(f"""
    <div class="logo-container-preview">
        <a href="?action=go_back" target="_self" class="topbar-arrow-clickable">‹</a>
        <div class="topbar-title-centered">Preview submission</div>
        <div class="topbar-logo-right">{logo_html}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="
        padding: 12px; 
        border-radius: 8px; 
        margin-bottom: 12px;
        text-align: center;
    ">
        <span style="color: {COLOR_SECONDARY}; font-size: 13px; font-family: sans-serif;">
            ⚠️ <b>Make sure all answers are clearly legible before submitting.</b>
        </span>
    </div>
    """, unsafe_allow_html=True)

    saved_path = os.path.join(current_dir, "img", "captured_submission.png")
    if os.path.exists(saved_path):
        st.image(saved_path, use_container_width=True)

    st.write("")
    
    # Gebruik weer st.columns zodat Streamlit ze horizontaal zet, 
    # maar onze nieuwe CSS dwingt ze nu kaarsrecht én compact naar het midden!
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Retake", key="retake_btn"):
            st.session_state.screen = "camera"
            st.rerun()
            
    with col2:
        if st.button("Submit", key="submit_btn"):
            st.success("Exam submitted successfully! Moving to results...")
            st.session_state.screen = "results"
            
    st.markdown('</div>', unsafe_allow_html=True) # Sluit main-content

# ==========================================
# SCHERM 3: RESULTS
# ==========================================
elif st.session_state.screen == "results":
    if encoded_logo_full:
        st.markdown(f'<div class="logo-container-camera"><img src="data:image/png;base64,{encoded_logo_full}" width="110"></div>', unsafe_allow_html=True)
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    st.markdown('<p class="viewfinder-text-title">Results Screen</p>', unsafe_allow_html=True)
    st.info("Hier sluit de ResultsView van je groepsgenoten nu op aan.")
    
    if st.button("🔄 Scan another sheet"):
        st.session_state.screen = "camera"
        st.rerun()
        
    st.markdown('</div>', unsafe_allow_html=True)