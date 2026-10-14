import streamlit as st
import pandas as pd
import math
import io
from datetime import datetime, timedelta
import json

# --- NASTAVENIE STRÁNKY ---
st.set_page_config(page_title="Kikiriki Roastery PRO", page_icon="☕", layout="wide")

# ==========================================
# 🎨 FIREMNÝ DIZAJN (BARLOW, MASÍVNE BOLD ZÁLOŽKY & FARBY)
# ==========================================
firemny_dizajn = """
<style>
    /* Natiahnutie fontov Barlow a Barlow Condensed z Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=Barlow:wght@400;500;600;700&display=swap');

    /* Celkové nastavenie písma */
    html, body, [class*="css"] {
        font-family: 'Barlow', sans-serif !important;
        font-weight: 500;
    }

    /* Všetky nadpisy v Barlow Condensed a firemnej modrej */
    h1, h2, h3, .stMarkdown h3 {
        font-family: 'Barlow Condensed', sans-serif !important;
        color: #2B5098 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 700 !important;
    }
    
    /* Metriky v dózach */
    [data-testid="stMetricValue"] {
        font-family: 'Barlow Condensed', sans-serif !important;
        color: #2B5098 !important;
        font-weight: 800 !important;
        font-size: 2rem !important;
    }

    /* ========================================================= */
    /* 🔥 NEPRIESTRELNÉ ZACIELENIE PRE ZÁLOŽKY (TABS): BOLD + VÄČŠIE */
    /* ========================================================= */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        border-bottom: 2px solid #2B5098 !important;
        padding-bottom: 4px;
    }
    
    .stTabs [data-baseweb="tab"],
    .stTabs button[data-baseweb="tab"],
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] div {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 1.35rem !important;      /* Výrazne zväčšené */
        font-weight: 800 !important;        /* Extra tučné (Bold) */
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
    }

    /* Neaktívne záložky */
    .stTabs [data-baseweb="tab"] {
        background-color: #EDE4D4 !important;
        color: #2B5098 !important;
        border-radius: 8px 8px 0px 0px !important;
        padding: 10px 28px !important;
        border: 1px solid #D8CABE !important;
        border-bottom: none !important;
        transition: all 0.2s ease-in-out;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #E2D5C1 !important;
        color: #1A3568 !important;
    }

    /* Aktívna vybratá záložka */
    .stTabs [aria-selected="true"],
    .stTabs [aria-selected="true"] p {
        background-color: #2B5098 !important;
        color: #FFFFFF !important;
        border: 1px solid #2B5098 !important;
        border-bottom: none !important;
    }

    /* Tabuľky a tlačidlá */
    .stDataFrame, th, td, .stButton>button {
        font-weight: 600 !important;
    }
    
    /* Expandery v pražiarni */
    .streamlit-expanderHeader p {
        font-family: 'Barlow', sans-serif !important;
        font-size: 1.15rem !important;
        color: #2B5098 !important;
    }
</style>
"""
st.markdown(firemny_dizajn, unsafe_allow_html=True)
# ==========================================

# --- KONFIGURÁCIA ---
KAPACITA_ZELENA_BATCH = 5.0
STANDARDNY_VYPEK = 20
DNESNY_DATUM = datetime.now().strftime("%d-%m-%Y")
NAZOV_TABULKY_ZALOHA = "Kikiriki_Zaloha_PRO"

kavy_recepty = {
    "Brazília": {"vypek": STANDARDNY_VYPEK, "recept": {"Brazília Santos": 1.0}},
    "Etiopia Yerg.": {"vypek": STANDARDNY_VYPEK, "recept": {"Etiópia Yirgacheffe": 1.0}},
    "Etiopia BG": {"vypek": STANDARDNY_VYPEK, "recept": {"Etiopia BG": 1.0}},
    "Peru": {"vypek": STANDARDNY_VYPEK, "recept": {"Peru": 1.0}},
    "Honduras": {"vypek": STANDARDNY_VYPEK, "recept": {"Honduras": 1.0}},
    "Columbia": {"vypek": STANDARDNY_VYPEK, "recept": {"Columbia": 1.0}},
    "Indonezia": {"vypek": STANDARDNY_VYPEK, "recept": {"Indonezia": 1.0}},
    "Rwanda": {"vypek": STANDARDNY_VYPEK, "recept": {"Rwanda": 1.0}},
    "India": {"vypek": STANDARDNY_VYPEK, "recept": {"India": 1.0}},
    "Aranka": {"vypek": STANDARDNY_VYPEK, "recept": {"Brazília Santos": 0.5, "Indonezia": 0.3, "Etiópia Yirgacheffe": 0.2}},
    "Frištuk": {"vypek": STANDARDNY_VYPEK, "recept": {"Brazília Santos": 0.5, "Columbia": 0.3, "Robusta KR": 0.2}},
    "K52%": {"vypek": STANDARDNY_VYPEK, "recept": {"Brazília Santos": 0.3, "India": 0.22, "Indonezia": 0.18, "Honduras": 0.2, "Robusta KR": 0.1}},
    "Cucflek": {"vypek": STANDARDNY_VYPEK, "recept": {"Brazília Santos": 0.4, "Honduras": 0.25, "Etiópia Yirgacheffe": 0.2, "India": 0.15}}
}

gramaze_list = [220, 500, 1000]

# --- GOOGLE API FUNKCIE ---
@st.cache_resource
def get_google_credentials():
    from google.oauth2.service_account import Credentials
    creds_data = st.secrets["google_credentials_json"]
    if isinstance(creds_data, str): creds_dict = json.loads(creds_data)
    else: creds_dict = dict(creds_data)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    return Credentials.from_service_account_info(creds_dict, scopes=scopes)

def nacitaj_z_google_sheets():
    try:
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        try: spreadsheet = client.open(NAZOV_TABULKY_ZALOHA)
        except gspread.exceptions.SpreadsheetNotFound:
            spreadsheet = client.create(NAZOV_TABULKY_ZALOHA)
            spreadsheet.share(None, perm_type='anyone', role='writer')
            
        sheet = spreadsheet.sheet1
        try:
            hodnoty = sheet.row_values(1)
            val_data = hodnoty[0] if len(hodnoty) > 0 else None
            val_cas = hodnoty[1] if len(hodnoty) > 1 else "Neznámy čas"
            val_nazov = hodnoty[2] if len(hodnoty) > 2 and hodnoty[2].strip() != "" else ""
        except:
            val_data, val_cas, val_nazov = None, "Neznámy čas", ""
            
        data = json.loads(val_data) if val_data else {"objednavky": [], "prazenie": {}}
        if isinstance(data, list): data = {"objednavky": data, "prazenie": {}}
        return data, val_cas, val_nazov
    except Exception as e:
        return None, None, None

def uloz_do_google_sheets(data_dict, nazov_prazenia):
    try:
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet = client.open(NAZOV_TABULKY_ZALOHA)
        sheet1 = spreadsheet.sheet1
        cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        sheet1.update_acell('A1', json.dumps(data_dict, ensure_ascii=False))
        sheet1.update_acell('B1', cas_ulozenia)
        sheet1.update_acell('C1', str(nazov_prazenia))
        return True
    except Exception as e:
        return False

def auto_uloz():
    aktualny_nazov = st.session_state.get('nazov_prazenia', f"Prazenie_PRO_{DNESNY_DATUM}")
    data_na_ulozenie = {
        "objednavky": st.session_state.aktualne_objednavky,
        "prazenie": st.session_state.priebeh_prazenia
    }
    uloz_do_google_sheets(data_na_ulozenie, aktualny_nazov)

def nacitaj_vsetko_z_cloudu_callback():
    zaloha_dict, cas_poslednej_upravy, n_prazenia = nacitaj_z_google_sheets()
    if zaloha_dict:
        st.session_state.aktualne_objednavky = zaloha_dict.get("objednavky", [])
        st.session_state.priebeh_prazenia = zaloha_dict.get("prazenie", {})
        if n_prazenia:
            st.session_state.nazov_prazenia = n_prazenia
        aktivne = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
        st.session_state.info_cloud = f"Synchronizované: {len(aktivne)} položiek | Posledná úprava: {cas_poslednej_upravy}"
        st.session_state.msg_uspech = True
    else:
        st.session_state.info_cloud = "Synchronizované: Prázdny stôl."
        st.session_state.msg_chyba = True

# --- AUTO-LOAD PRI ŠTARTE ---
if 'aktualne_objednavky' not in st.session_state:
    zaloha_dict, cas, n_prazenia = nacitaj_z_google_sheets()
    if zaloha_dict:
        st.session_state.aktualne_objednavky = zaloha_dict.get("objednavky", [])
        st.session_state.priebeh_prazenia = zaloha_dict.get("prazenie", {})
    else:
        st.session_state.aktualne_objednavky = []
        st.session_state.priebeh_prazenia = {}
    st.session_state.pociatocny_nazov = n_prazenia if n_prazenia else f"Prazenie_PRO_{DNESNY_DATUM}"
    aktivne_start = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
    st.session_state.info_cloud = f"Synchronizované: {len(aktivne_start)} položiek | Posledná úprava: {cas}"

if 'nazov_prazenia' not in st.session_state:
    st.session_state.nazov_prazenia = st.session_state.get('pociatocny_nazov', f"Prazenie_PRO_{DNESNY_DATUM}")

if 'form_key' not in st.session_state: st.session_state.form_key = 0
def vynuluj_policka(): st.session_state.form_key += 1

# --- HLAVNÉ ROZHRANIE (HLAVIČKA S LOGOM VPRAVO HORE) ---
col_head_left, col_head_right = st.columns([3, 1])

with col_head_left:
    st.title("Kikiriki Roastery PRO")
    st.caption("Verzia 6.8 | Výrobný manažment")

with col_head_right:
    # Oficiálne logo KIKIRIKI v pravej hornej časti
    logo_html = """
    <div style="display: flex; flex-direction: column; align-items: flex-end; justify-content: center; padding-top: 5px;">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" fill="#2B5098"/>
        </svg>
        <span style="font-family: 'Barlow Condensed', sans-serif; font-weight: 800; color: #2B5098; font-size: 1.25rem; letter-spacing: 1.5px; text-transform: uppercase;">KIKIRIKI</span>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

st.text_input("Identifikátor praženia:", key="nazov_prazenia", on_change=auto_uloz)

# ========================================================
# 🚀 VÝRAZNÉ, VEĽKÉ A TUČNÉ ZÁLOŽKY
# ========================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "OBJEDNÁVKY", 
    "PRAŽIAREŇ", 
    "BALENIE", 
    "SKLAD", 
    "ÚČTOVNÍCTVO"
])

# ========================================================
# TAB 1: OBJEDNÁVKY
# ========================================================
with tab1:
    st.info(st.session_state.info_cloud)

    if st.session_state.get('aktualne_objednavky'):
        with st.expander("Zobraziť surové dáta z Cloudu"):
            df_ukazka = pd.DataFrame([o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)])
            if not df_ukazka.empty:
                st.
