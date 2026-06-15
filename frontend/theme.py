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
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@500;700&display=swap');
                
    /* Alleen basisteksten en labels, GEEN knoppen globaal forceren */
    .stApp, .stApp label, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
        font-family: {FONT_FAMILY} !important;
    }}

    div[data-testid="stFileUploader"] button span[data-testid="stWidgetLabel"] {{
        display: none !important;
    }}
    div[data-testid="stFileUploader"] button span::before,
    div[data-testid="stFileUploader"] button span::after {{
        display: none !important;
    }}

    .stApp svg, .stApp svg * {{
        font-family: inherit !important;
    }}

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
       AZOTA BUTTON STYLES
    ========================= */
    
    /* Gedeelde basisstijlen voor de overkoepelende knop-containers */
    div[data-testid*="azota_"] {{
        border-radius: 50px !important;
        min-height: 50px !important;
        padding: 0 !important;
        display: inline-block !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
    }}

    /* De daadwerkelijke knop binnen de container resetten en stylen */
    div[data-testid*="azota_"] button {{
        background-color: transparent !important;
        border: none !important;
        width: 100% !important;
        min-height: 50px !important;
        font-family: {FONT_FAMILY} !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        padding: 12px 40px !important;
        font-size: 16px !important;
        color: inherit !important;
    }}
    
    div[data-testid*="azota_"] button p {{
        font-weight: 700 !important;
        text-shadow: 0.5px 0px 0px currentColor, -0.5px 0px 0px currentColor, 0px 0.5px 0px currentColor, 0px -0.5px 0px currentColor !important;
    }}

    div[data-testid*="azota_filled"] {{
        background-color: {COLOR_PRIMARY} !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(0, 82, 204, 0.2) !important;
        border: none !important;
    }}

    div[data-testid*="azota_filled"]:hover {{
        background-color: #0041A3 !important;
        box-shadow: 0 6px 16px rgba(0, 82, 204, 0.3) !important;
        transform: translateY(-1px);
    }}

   /* =============================================================
       SPECIFIEKE STYLING VOOR DE NIEUWE VEILIGE EXCEL SUBMIT BUTTON
       ============================================================= */
    .azota-outlined-container {{
        margin-top: 15px !important;
        width: 100% !important;
        display: block !important;
    }}

    /* We dwingen ELKE button die binnen onze custom container leeft naar de capsule look */
    .azota-outlined-container button,
    .azota-outlined-container div[data-testid*="stBaseButton"] button,
    .azota-outlined-container [data-testid="stBaseButton"] button {{
        background-color: transparent !important;
        color: #0052CC !important;
        border: 2px solid #0052CC !important;
        border-radius: 50px !important;
        min-height: 50px !important;
        height: 50px !important;
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        font-size: 16px !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    /* De hover state met zachtblauwe gloed gekoppeld aan de container */
    .azota-outlined-container button:hover,
    .azota-outlined-container div[data-testid*="stBaseButton"] button:hover {{
        background-color: rgba(0, 82, 204, 0.08) !important;
        color: #0041A3 !important;
        border-color: #0041A3 !important;
    }}

    /* Tekst binnen de knop dwingen */
    .azota-outlined-container button p,
    .azota-outlined-container div[data-testid*="stBaseButton"] button p {{
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
        color: inherit !important;
        font-size: 16px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        margin: 0 !important;
        text-shadow: none !important;
    }}

    /* =========================
       FILE UPLOADER AZOTA STYLE
    ========================= */

    div[data-testid="stFileUploader"] {{
        background-color: {COLOR_CARD_WHITE};
        border: 1px dashed #CBD5E1;
        border-radius: 14px;
        padding: 16px;
    }}

    /* De grote hoofd-uploadknop krijgt z'n styling onvoorwaardelijk */
    div[data-testid="stFileUploader"] button {{
        background-color: {COLOR_PRIMARY} !important;
        color: white !important;
        border-radius: 50px !important;
        font-family: {FONT_FAMILY} !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        padding: 10px 32px !important;
        min-height: 46px !important;
        font-size: 15px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0, 82, 204, 0.2) !important;
        transition: all 0.3s ease !important;
        width: auto !important;
    }}

    div[data-testid="stFileUploader"] button:hover {{
        background-color: #0041A3 !important;
        box-shadow: 0 6px 16px rgba(0, 82, 204, 0.3) !important;
        transform: translateY(-1px);
    }}

    div[data-testid="stFileUploader"] button p {{
        font-weight: 700 !important;
        font-size: 15px !important;
        color: white !important;
        text-shadow: none !important;
    }}

    div[data-testid="stFileUploader"] button svg {{
        fill: white !important;
        stroke: white !important;
        stroke-width: 3px !important;
        filter: drop-shadow(0.5px 0px 0px white) drop-shadow(-0.5px 0px 0px white);
        transform: scale(1.15);
    }}

    /* VERBERG ALLEEN DE STANDAARD VUILNISBAK-KNOP VAN STREAMLIT */
    div[data-testid="stFileUploader"] button[aria-label*="Remove"],
    div[data-testid="stFileUploader"] button[aria-label*="Delete"],
    div[data-testid="stFileUploader"] button:nth-of-type(2) {{
        display: none !important;
    }}

    /* ZORG DAT DE PLUS-KNOP ER WEER NORMAAL EN SUBTIEL UITZIET (GEEN DIK BLAUW BLOK) */
    div[data-testid="stFileUploader"] button[aria-label*="Add"] {{
        background-color: transparent !important;
        color: #0052CC !important;
        border: 1px solid #0052CC !important;
        box-shadow: none !important;
        min-height: unset !important;
        height: 32px !important;
        width: 32px !important;
        padding: 0 !important;
        border-radius: 50px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    div[data-testid="stFileUploader"] button[aria-label*="Add"]:hover {{
        background-color: rgba(0, 82, 204, 0.08) !important;
        transform: none !important;
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