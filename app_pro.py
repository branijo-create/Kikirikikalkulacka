import streamlit as st
import pandas as pd
import math
import io
import os
import hmac
from datetime import datetime, timedelta
import json

# --- NASTAVENIE STRÁNKY ---
st.set_page_config(page_title="Kikiriki Roastery PRO", page_icon="☕", layout="wide")

# ==========================================
# 🎨 FIREMNÝ DIZAJN
# ==========================================
firemny_dizajn = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800;900&family=Barlow:wght@500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Barlow', sans-serif !important;
        font-weight: 500;
    }

    h1, h2, h3, .stMarkdown h3 {
        font-family: 'Barlow Condensed', sans-serif !important;
        color: #2B5098 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 800 !important;
    }
    
    [data-testid="stMetricValue"] {
        font-family: 'Barlow Condensed', sans-serif !important;
        color: #2B5098 !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
    }

    button[role="tab"] {
        padding: 8px 20px !important;
    }

    button[role="tab"] p,
    button[role="tab"] strong {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.8px !important;
        color: #2B5098 !important;
        text-transform: uppercase !important;
    }

    button[role="tab"][aria-selected="true"] {
        border-bottom: 3px solid #2B5098 !important;
    }

    button[kind="primary"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    .stDataFrame, th, td {
        font-weight: 600 !important;
    }
    
    div[data-testid="stExpander"] summary p {
        font-size: 1.15rem !important;
    }
    div[data-testid="stExpander"] summary p strong {
        font-size: 1.65rem !important;
        color: #1A3568 !important;
        letter-spacing: 0.5px !important;
    }
</style>
"""
st.markdown(firemny_dizajn, unsafe_allow_html=True)

# --- KONFIGURÁCIA A SKU (SKLADOVÉ KARTY) ---
KAPACITA_ZELENA_BATCH = 5.0
STANDARDNY_VYPEK = 20
DNESNY_DATUM = datetime.now().strftime("%d-%m-%Y")

NAZOV_TABULKY_ZALOHA = "Kikiriki_Zaloha_PRO"

# Ukladanie: stav sa delí na kúsky (limit bunky v Google Sheets je 50 000 znakov)
NAZOV_LISTU_STAV = "Stav"
NAZOV_LISTU_HISTORIA = "Historia"
VELKOST_KUSKU = 40000
MAX_ZAZNAMOV_HISTORIE = 100

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

# SKU MAPOVANIE
SKU_ZELENA = {
    "Brazília Santos": "GC001",
    "Columbia": "GC002",
    "Etiopia BG": "GC003",
    "Etiópia Yirgacheffe": "GC004",
    "Honduras": "GC005",
    "India": "GC006",
    "Indonezia": "GC007",
    "Peru": "GC008",
    "Rwanda": "GC009",
    "Robusta KR": "GCR001"
}

SKU_UPRAZENA = {
    "Brazília Santos": "RC001",
    "Columbia": "RC002",
    "Etiopia BG": "RC003",
    "Etiópia Yirgacheffe": "RC004",
    "Honduras": "RC005",
    "India": "RC006",
    "Indonezia": "RC007",
    "Peru": "RC008",
    "Rwanda": "RC009",
    "Robusta KR": "RCR001",
    "Aranka": "RCB001",
    "Cucflek": "RCB002",
    "Frištuk": "RCB003",
    "K52%": "RCB004"
}

MENU_KAVY = {
    "Brazília": "RC001",
    "Columbia": "RC002",
    "Etiopia BG": "RC003",
    "Etiopia Yerg.": "RC004",
    "Honduras": "RC005",
    "India": "RC006",
    "Indonezia": "RC007",
    "Peru": "RC008",
    "Rwanda": "RC009",
    "Aranka": "RCB001",
    "Cucflek": "RCB002",
    "Frištuk": "RCB003",
    "K52%": "RCB004"
}

def get_pc_sku(rc_sku, gramaz):
    if rc_sku.startswith("RCB"):
        return f"PC{gramaz}-B{rc_sku[3:]}"
    elif rc_sku.startswith("RC") or rc_sku.startswith("RCR"):
        return f"PC{gramaz}-{rc_sku[2:]}"
    return f"PC{gramaz}-XXX"

# Názvy reverzne (pre zobrazenie v UI podľa SKU)
NAZVY_ZELENA = {v: k for k, v in SKU_ZELENA.items()}
NAZVY_UPRAZENA = {v: k for k, v in SKU_UPRAZENA.items()}

PRAZDNY_STAV = {"objednavky": [], "prazenie": {}, "sklad": {"zelena": {}, "uprazena": {}, "zabalena": {}}}

# --- GOOGLE API FUNKCIE ---
@st.cache_resource
def get_google_credentials():
    from google.oauth2.service_account import Credentials
    creds_data = st.secrets["google_credentials_json"]
    if isinstance(creds_data, str): creds_dict = json.loads(creds_data)
    else: creds_dict = dict(creds_data)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    return Credentials.from_service_account_info(creds_dict, scopes=scopes)

def get_client():
    import gspread
    return gspread.authorize(get_google_credentials())

def zabezpec_zdielanie(client, spreadsheet):
    """Odstráni verejný prístup 'ktokoľvek s linkom' a zdieľa tabuľku len s majiteľom."""
    try:
        for p in spreadsheet.list_permissions():
            if p.get("type") == "anyone":
                client.remove_permission(spreadsheet.id, p["id"])
    except Exception:
        pass
    owner_email = st.secrets.get("owner_email", "")
    if owner_email:
        try:
            uz_zdielane = any(p.get("emailAddress", "").lower() == owner_email.lower() for p in spreadsheet.list_permissions())
            if not uz_zdielane:
                spreadsheet.share(owner_email, perm_type="user", role="writer", notify=False)
        except Exception:
            pass

def otvor_tabulku(client):
    import gspread
    try:
        spreadsheet = client.open(NAZOV_TABULKY_ZALOHA)
    except gspread.exceptions.SpreadsheetNotFound:
        spreadsheet = client.create(NAZOV_TABULKY_ZALOHA)
    return spreadsheet

def ziskaj_list(spreadsheet, nazov, riadky=200, stlpce=5):
    import gspread
    try:
        return spreadsheet.worksheet(nazov)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=nazov, rows=riadky, cols=stlpce)

def rozdel_na_kusky(text):
    return [text[i:i + VELKOST_KUSKU] for i in range(0, len(text), VELKOST_KUSKU)] or [""]

def nacitaj_z_google_sheets():
    try:
        import gspread
        client = get_client()
        spreadsheet = otvor_tabulku(client)
        zabezpec_zdielanie(client, spreadsheet)

        try:
            ws = spreadsheet.worksheet(NAZOV_LISTU_STAV)
            stlpec = ws.col_values(1)
            val_cas = stlpec[0] if len(stlpec) > 0 else "Neznámy čas"
            val_nazov = stlpec[1] if len(stlpec) > 1 else ""
            pocet = int(stlpec[2]) if len(stlpec) > 2 and stlpec[2].isdigit() else 0
            val_data = "".join(stlpec[3:3 + pocet])
        except gspread.exceptions.WorksheetNotFound:
            # Migrácia zo starého formátu (všetko v Sheet1!A1:C1)
            hodnoty = spreadsheet.sheet1.row_values(1)
            val_data = hodnoty[0] if len(hodnoty) > 0 else None
            val_cas = hodnoty[1] if len(hodnoty) > 1 else "Neznámy čas"
            val_nazov = hodnoty[2] if len(hodnoty) > 2 else ""

        if val_data and val_data.strip():
            data = json.loads(val_data)
        else:
            data = json.loads(json.dumps(PRAZDNY_STAV))

        if isinstance(data, list):
            data = {"objednavky": data, "prazenie": {}, "sklad": {"zelena": {}, "uprazena": {}, "zabalena": {}}}

        return data, val_cas, val_nazov
    except Exception as e:
        return None, str(e), None

def uloz_snapshot_historie(spreadsheet, cas, nazov, kusky):
    ws_h = ziskaj_list(spreadsheet, NAZOV_LISTU_HISTORIA, riadky=MAX_ZAZNAMOV_HISTORIE + 20, stlpce=max(10, len(kusky) + 3))
    if ws_h.col_count < len(kusky) + 2:
        ws_h.resize(cols=len(kusky) + 2)
    ws_h.append_row([cas, nazov] + kusky, value_input_option="RAW")
    pocet = len(ws_h.col_values(1))
    if pocet > MAX_ZAZNAMOV_HISTORIE:
        ws_h.delete_rows(1, pocet - MAX_ZAZNAMOV_HISTORIE)

def uloz_do_google_sheets(data_dict, nazov_prazenia, historia=False):
    try:
        client = get_client()
        spreadsheet = otvor_tabulku(client)
        ws = ziskaj_list(spreadsheet, NAZOV_LISTU_STAV, riadky=200, stlpce=2)

        cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        kusky = rozdel_na_kusky(json.dumps(data_dict, ensure_ascii=False))

        potrebne_riadky = 3 + len(kusky)
        if ws.row_count < potrebne_riadky:
            ws.resize(rows=potrebne_riadky + 50)

        # Najprv dáta, potom hlavička s počtom kúskov (pri páde sa číta stále starý počet)
        ws.update(range_name=f"A4:A{3 + len(kusky)}", values=[[k] for k in kusky], value_input_option="RAW")
        ws.update(range_name="A1:A3", values=[[cas_ulozenia], [str(nazov_prazenia)], [str(len(kusky))]], value_input_option="RAW")

        if historia:
            uloz_snapshot_historie(spreadsheet, cas_ulozenia, str(nazov_prazenia), kusky)
        return True, None
    except Exception as e:
        chyba = str(e)
        if "200" in chyba: return True, None
        return False, chyba

def auto_uloz(historia=False):
    aktualny_nazov = st.session_state.get('nazov_prazenia', f"Prazenie_PRO_{DNESNY_DATUM}")
    data_na_ulozenie = {
        "objednavky": st.session_state.aktualne_objednavky,
        "prazenie": st.session_state.priebeh_prazenia,
        "sklad": st.session_state.sklad
    }
    uspech, chyba = uloz_do_google_sheets(data_na_ulozenie, aktualny_nazov, historia=historia)
    if not uspech: st.toast(f"⚠️ Zlyhalo ukladanie: {chyba}", icon="❌")

def over_heslo(zadane):
    spravne = st.secrets.get("inventura_heslo", "")
    if not spravne:
        return None  # heslo nie je nastavené
    return hmac.compare_digest(str(zadane), str(spravne))

# --- AUTO-LOAD A INICIALIZÁCIA SKLADU ---
def inicializuj_sklad(nacitany_sklad):
    sklad = {"zelena": {}, "uprazena": {}, "zabalena": {}}
    if nacitany_sklad:
        sklad["zelena"] = nacitany_sklad.get("zelena", {})
        sklad["uprazena"] = nacitany_sklad.get("uprazena", {})
        sklad["zabalena"] = nacitany_sklad.get("zabalena", {})
    
    for sku in SKU_ZELENA.values():
        if sku not in sklad["zelena"]: sklad["zelena"][sku] = 0.0
    for sku in SKU_UPRAZENA.values():
        if sku not in sklad["uprazena"]: sklad["uprazena"][sku] = 0.0
    for menu_nazov, rc_sku in MENU_KAVY.items():
        for g in gramaze_list:
            pc_sku = get_pc_sku(rc_sku, g)
            if pc_sku not in sklad["zabalena"]: sklad["zabalena"][pc_sku] = 0
    return sklad

def nacitaj_vsetko_z_cloudu_callback():
    zaloha_dict, cas_poslednej_upravy, n_prazenia = nacitaj_z_google_sheets()
    if zaloha_dict is not None:
        st.session_state.aktualne_objednavky = zaloha_dict.get("objednavky", [])
        st.session_state.priebeh_prazenia = zaloha_dict.get("prazenie", {})
        st.session_state.sklad = inicializuj_sklad(zaloha_dict.get("sklad", {}))
        if n_prazenia: st.session_state.nazov_prazenia = n_prazenia
        aktivne = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
        st.session_state.info_cloud = f"Synchronizované: {len(aktivne)} položiek | Posledná úprava: {cas_poslednej_upravy}"
        st.session_state.msg_uspech = True
    else:
        st.session_state.info_cloud = f"Chyba synchronizácie: {cas_poslednej_upravy}"
        st.session_state.msg_chyba = True

if 'sklad' not in st.session_state:
    zaloha_dict, cas, n_prazenia = nacitaj_z_google_sheets()
    if zaloha_dict is not None:
        st.session_state.aktualne_objednavky = zaloha_dict.get("objednavky", [])
        st.session_state.priebeh_prazenia = zaloha_dict.get("prazenie", {})
        st.session_state.sklad = inicializuj_sklad(zaloha_dict.get("sklad", {}))
        aktivne_start = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
        st.session_state.info_cloud = f"Synchronizované: {len(aktivne_start)} položiek | Posledná úprava: {cas}"
    else:
        st.session_state.aktualne_objednavky = []
        st.session_state.priebeh_prazenia = {}
        st.session_state.sklad = inicializuj_sklad({})
        st.session_state.info_cloud = f"Sme offline / Tabuľka je prázdna. (Detail: {cas})"
    st.session_state.pociatocny_nazov = n_prazenia if n_prazenia else f"Prazenie_PRO_{DNESNY_DATUM}"

if 'nazov_prazenia' not in st.session_state:
    st.session_state.nazov_prazenia = st.session_state.get('pociatocny_nazov', f"Prazenie_PRO_{DNESNY_DATUM}")

if 'form_key' not in st.session_state: st.session_state.form_key = 0
def vynuluj_policka(): st.session_state.form_key += 1

# --- HLAVIČKA A LOGO ---
col_head_left, col_head_right = st.columns([3, 1])
with col_head_left:
    st.title("Kikiriki Roastery PRO")
    st.caption("Verzia 8.7 | Výroba, Sklad & ERP Kódy")
with col_head_right:
    if os.path.exists("logo.png"): st.image("logo.png", width=110)
    elif os.path.exists("logo.svg"): st.image("logo.svg", width=110)
    else: st.markdown("<div style='text-align: right; padding-top: 10px;'><span style='font-family: \"Barlow Condensed\", sans-serif; font-weight: 900; color: #2B5098; font-size: 1.8rem; letter-spacing: 2px;'>KIKIRIKI</span></div>", unsafe_allow_html=True)

st.text_input("Identifikátor praženia:", key="nazov_prazenia", on_change=auto_uloz)

# ========================================================
# 🚀 ZÁLOŽKY
# ========================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "**OBJEDNÁVKY**", "**PRAŽIAREŇ**", "**BALENIE**", "**SKLAD**", "**EXPED.**", "**ÚČTOVNÍCTVO**"
])

# ========================================================
# TAB 1: OBJEDNÁVKY
# ========================================================
with tab1:
    st.info(st.session_state.info_cloud)

    col_load, col_save = st.columns(2)
    with col_load:
        if st.button("Načítať stav z Cloudu", type="secondary", use_container_width=True):
            nacitaj_vsetko_z_cloudu_callback()
            st.rerun()
    with col_save:
        if st.button("Uložiť aktuálny stav do Cloudu", type="primary", use_container_width=True):
            auto_uloz(historia=True)
            st.success("Aktuálny zoznam uložený (aj do histórie).")
            st.rerun()

    st.divider()

    st.markdown("### Import údajov")
    nahraty_subor = st.file_uploader("Nahraj .xlsx súbor z tabuľky", type=["xlsx"])
    if nahraty_subor is not None:
        try:
            xl = pd.ExcelFile(nahraty_subor)
            df_import = xl.parse('Spracovane_Objednavky') if 'Spracovane_Objednavky' in xl.sheet_names else xl.parse(0)
            if st.button("Spracovať Excel a pridať objednávky", type="primary"):
                for index, row in df_import.iterrows():
                    kusy_zaklad = int(row.get("Kusy", 0))
                    potvrdene_hist = bool(row.get("Potvrdene", False))
                    sudy_hist = bool(row.get("Sudy", False)) if pd.notna(row.get("Sudy")) else False
                    st.session_state.aktualne_objednavky.append({
                        "Odberateľ": str(row.get("Odberateľ", "Neznámy")),
                        "Káva": str(row.get("Káva", "")),
                        "Gramáž": int(row.get("Gramáž", 0)),
                        "Kusy": kusy_zaklad,
                        "Zabalené (ks)": 0,
                        "Potvrdene": potvrdene_hist,
                        "Sudy": sudy_hist,
                        "❌ Zmazať": False
                    })
                auto_uloz()
                st.success("Dáta importované a uložené do cloudu.")
                st.rerun()
        except Exception as e:
            st.error("Chyba pri spracovaní Excelu.")

    st.divider()

    st.markdown("### Manuálny príjem objednávok")
    col1, col2 = st.columns(2)
    with col1:
        meno = st.text_input("Odberateľ:", placeholder="Meno zákazníka alebo prevádzky...")
        rezim = st.radio("Režim zadávania:", ["Podľa kávy", "Podľa gramáže", "Skladový BATCH (Sudy)"], horizontal=True, on_change=vynuluj_policka)

    if rezim == "Podľa kávy":
        with col1: kava = st.selectbox("Vyber kávu:", list(kavy_recepty.keys()), on_change=vynuluj_policka)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            col2_1, col2_2, col2_3 = st.columns(3)
            with col2_1: kusy_220 = st.number_input("220g (ks):", min_value=0, step=1, key=f"k_220_{st.session_state.form_key}")
            with col2_2: kusy_500 = st.number_input("500g (ks):", min_value=0, step=1, key=f"k_500_{st.session_state.form_key}")
            with col2_3: kusy_1000 = st.number_input("1000g (ks):", min_value=0, step=1, key=f"k_1000_{st.session_state.form_key}")

        if st.button("Zapísať do knihy", type="secondary"):
            if kusy_220 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 220, "Kusy": kusy_220, "Zabalené (ks)": 0, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            if kusy_500 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 500, "Kusy": kusy_500, "Zabalené (ks)": 0, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            if kusy_1000 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 1000, "Kusy": kusy_1000, "Zabalené (ks)": 0, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            auto_uloz()
            vynuluj_policka()
            st.rerun()
            
    elif rezim == "Podľa gramáže":
        with col1: gramaz = st.selectbox("Gramáž sáčku:", gramaze_list, on_change=vynuluj_policka)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            inputs_kavy = {}
            for k in kavy_recepty.keys(): inputs_kavy[k] = st.number_input(f"{k} (ks):", min_value=0, step=1, key=f"k_{k}_{st.session_state.form_key}")
        if st.button("Zapísať do knihy", type="secondary"):
            for k, v in inputs_kavy.items():
                if v > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": k, "Gramáž": gramaz, "Kusy": v, "Zabalené (ks)": 0, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            auto_uloz()
            vynuluj_policka()
            st.rerun()
            
    elif rezim == "Skladový BATCH (Sudy)":
        with st.container():
            st.info("Pridá dávky priamo do plánu praženia a následne do Skladu (Dóz). Tieto položky sa nebalia do sáčkov.")
            col_b1, col_b2 = st.columns(2)
            with col_b1: kava_batch = st.selectbox("Vyber zrno:", list(kavy_recepty.keys()), key=f"kava_b_{st.session_state.form_key}")
            with col_b2: davky_batch = st.number_input("Počet plných dávok (á 5kg zelenej):", min_value=1, step=1, key=f"davky_b_{st.session_state.form_key}")
            if st.button("Pridať BATCH", type="primary"):
                st.session_state.aktualne_objednavky.append({
                    "Odberateľ": "SKLAD (Sudy)", "Káva": kava_batch, "Gramáž": 0, "Kusy": davky_batch, "Zabalené (ks)": 0, "Potvrdene": True, "Sudy": True, "❌ Zmazať": False
                })
                auto_uloz()
                vynuluj_policka()
                st.rerun()

    st.divider()

    col_zoznam, col_vypocet = st.columns([5, 4])
    
    with col_zoznam:
        st.markdown("### Kniha objednávok")
        if st.session_state.aktualne_objednavky:
            df_objednavky_vstup = pd.DataFrame(st.session_state.aktualne_objednavky)
            if 'Sudy' not in df_objednavky_vstup.columns: df_objednavky_vstup['Sudy'] = False
            df_objednavky_vstup['Sudy'] = df_objednavky_vstup['Sudy'].fillna(False).astype(bool)
            
            upravene_df = st.data_editor(
                df_objednavky_vstup, 
                use_container_width=True, 
                num_rows="fixed", 
                hide_index=False, 
                key="tabulka_objednavok",
                column_order=["Odberateľ", "Káva", "Gramáž", "Kusy", "Zabalené (ks)", "Potvrdene", "Sudy", "❌ Zmazať"],
                column_config={
                    "Kusy": st.column_config.NumberColumn("Obj. (ks)"),
                    "Potvrdene": st.column_config.CheckboxColumn("Vybavené a odoslané (Expedícia)")
                }
            )
            novy_stav = upravene_df.to_dict('records')
            for item in novy_stav:
                if pd.isna(item.get('Sudy')): item['Sudy'] = False
                else: item['Sudy'] = bool(item['Sudy'])
                
            if novy_stav != st.session_state.aktualne_objednavky:
                st.session_state.aktualne_objednavky = novy_stav
                auto_uloz()
                
            col_del1, col_del2 = st.columns([1, 1])
            with col_del1:
                if st.button("Odstrániť označené", type="secondary"):
                    st.session_state.aktualne_objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
                    auto_uloz()
                    st.rerun()
            with col_del2:
                if st.button("Vyčistiť stôl (Nový víkend)", type="secondary"):
                    # Pred vyčistením uložiť snapshot do histórie
                    auto_uloz(historia=True)
                    st.session_state.aktualne_objednavky = []
                    st.session_state.priebeh_prazenia = {} 
                    auto_uloz()
                    st.success("Stôl bol vyčistený (predošlý stav je v histórii). Fyzický sklad zostal nedotknutý.")
                    st.rerun()
        else:
            st.info("Kniha je čistá, čaká na nové zadania.")

    with col_vypocet:
        st.markdown("### Spracovanie a Export")
        if st.button("Vypočítať technický plán a stiahnuť Excel", type="primary", use_container_width=True):
            if not st.session_state.aktualne_objednavky:
                st.warning("Najprv pridaj dáta do knihy.")
            else:
                aktivne_objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
                df_objednavky_export = pd.DataFrame(aktivne_objednavky)
                
                potreba_zelenej_podla_zrna = {}
                potreba_uprazenej_podla_zrna = {}
                potreba_skladania_blendov = {}
                
                for o in aktivne_objednavky:
                    je_sud = o.get("Sudy") == True
                    if je_sud:
                        zelena_kg_zaklad = o["Kusy"] * KAPACITA_ZELENA_BATCH
                        uprazena_kg = zelena_kg_zaklad * (1 - (STANDARDNY_VYPEK / 100.0))
                    else:
                        uprazena_kg = (o["Kusy"] * o["Gramáž"] / 1000.0)
                        zelena_kg_zaklad = uprazena_kg / (1 - (STANDARDNY_VYPEK / 100.0))
                    
                    if o["Káva"] in kavy_recepty:
                        if len(kavy_recepty[o["Káva"]]["recept"]) > 1:
                            potreba_skladania_blendov[o["Káva"]] = potreba_skladania_blendov.get(o["Káva"], 0) + uprazena_kg
                            
                        recept = kavy_recepty[o["Káva"]]["recept"]
                        for zrno, podiel in recept.items():
                            potreba_zelenej_podla_zrna[zrno] = potreba_zelenej_podla_zrna.get(zrno, 0) + (zelena_kg_zaklad * podiel)
                            potreba_uprazenej_podla_zrna[zrno] = potreba_uprazenej_podla_zrna.get(zrno, 0) + (uprazena_kg * podiel)

                finalny_plan = []
                for zrno, teoreticka_vaha_zelena in potreba_zelenej_podla_zrna.items():
                    uprazena_potreba = potreba_uprazenej_podla_zrna[zrno]
                    davky = math.ceil(round(teoreticka_vaha_zelena, 4) / KAPACITA_ZELENA_BATCH)
                    skutocna_zelena = davky * KAPACITA_ZELENA_BATCH
                    zostatok_uprazena = (skutocna_zelena * (1 - (STANDARDNY_VYPEK / 100.0))) - uprazena_potreba
                    finalny_plan.append({"Zelené zrno": zrno, "Upražiť (kg)": round(uprazena_potreba, 2), "Dávky": davky, "Zelená (kg)": skutocna_zelena, "Zostatok (kg)": round(zostatok_uprazena, 2)})
                
                df_plan = pd.DataFrame(finalny_plan)
                st.dataframe(df_plan, use_container_width=True, hide_index=True)
                
                total_row_plan = {"Zelené zrno": "SPOLU:", "Upražiť (kg)": df_plan['Upražiť (kg)'].sum(), "Dávky": df_plan['Dávky'].sum(), "Zelená (kg)": df_plan['Zelená (kg)'].sum(), "Zostatok (kg)": ""}
                df_plan_excel = pd.concat([df_plan, pd.DataFrame([total_row_plan])], ignore_index=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_plan_excel.to_excel(writer, index=False, sheet_name='Plan_Prazenia')
                    df_objednavky_export.drop(columns=['❌ Zmazať'], errors='ignore').to_excel(writer, index=False, sheet_name='Spracovane_Objednavky')
                st.download_button("Stiahnuť Kikiriki Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Kikiriki_PRO_{st.session_state.nazov_prazenia}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)

# ========================================================
# TAB 2: PRAŽIAREŇ (Zapisuje pevne do Skladu)
# ========================================================
with tab2:
    st.markdown("### Panel pri stroji")
    
    aktivne_objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
    potreba_zelenej_podla_zrna = {}
    
    for o in aktivne_objednavky:
        je_sud = o.get("Sudy") == True
        zelena_kg_zaklad = o["Kusy"] * KAPACITA_ZELENA_BATCH if je_sud else (o["Kusy"] * o["Gramáž"] / 1000.0) / (1 - (STANDARDNY_VYPEK / 100.0))
        if o["Káva"] in kavy_recepty:
            for zrno, podiel in kavy_recepty[o["Káva"]]["recept"].items():
                potreba_zelenej_podla_zrna[zrno] = potreba_zelenej_podla_zrna.get(zrno, 0) + (zelena_kg_zaklad * podiel)

    if not potreba_zelenej_podla_zrna:
        st.info("Plán praženia je prázdny. Začni pridaním objednávok.")
    else:
        for zrno, teoreticka_vaha_zelena in potreba_zelenej_podla_zrna.items():
            davky_plan = math.ceil(teoreticka_vaha_zelena / KAPACITA_ZELENA_BATCH)
            stav_z_cloudu = st.session_state.priebeh_prazenia.get(zrno, {"davky_hotovo": 0, "zelena_real": 0.0, "uprazena_real": 0.0, "hotovo": False})
            
            davky_hotovo = stav_z_cloudu.get("davky_hotovo", 0)
            davky_zostava = max(0, davky_plan - davky_hotovo)
            je_hotovo = davky_hotovo >= davky_plan
            ma_navyse = davky_hotovo > davky_plan
            
            if ma_navyse: stav_text = "✅ ⬆️ Hotovo (Navyše)"
            elif je_hotovo: stav_text = "✅ Hotovo"
            elif davky_hotovo > 0: stav_text = "🔄 Rozpracované"
            else: stav_text = "⏳ Na rade"
                
            with st.expander(f"{stav_text}: **{zrno}** ({davky_hotovo} / {davky_plan} dávok)", expanded=not je_hotovo):
                col_info, col_input = st.columns([1, 1])
                with col_info:
                    st.markdown(f"**Cieľový plán:** {davky_plan} dávok")
                    st.markdown(f"**Vyrobené na túto zmenu:** {davky_hotovo} dávok")
                    if davky_zostava > 0: st.warning(f"**Zostáva dokončiť:** {davky_zostava} dávok")
                    elif ma_navyse: st.info(f"**Odpražené o {davky_hotovo - davky_plan} dávok navyše.**")
                    else: st.success("**Plán je splnený!**")
                
                with col_input:
                    pridat_davky = st.number_input("Počet práve odpražených dávok:", min_value=1, value=davky_zostava if davky_zostava > 0 else 1, step=1, key=f"davky_{zrno}")
                    if st.button(f"Potvrdiť {pridat_davky} dávok do Skladu", key=f"btn_praz_{zrno}", type="primary"):
                        nova_zelena = pridat_davky * KAPACITA_ZELENA_BATCH
                        nova_uprazena = nova_zelena * (1 - (STANDARDNY_VYPEK / 100.0))
                        
                        st.session_state.priebeh_prazenia[zrno] = {
                            "davky_hotovo": davky_hotovo + pridat_davky,
                            "zelena_real": stav_z_cloudu.get("zelena_real", 0.0) + nova_zelena,
                            "uprazena_real": stav_z_cloudu.get("uprazena_real", 0.0) + nova_uprazena,
                            "hotovo": (davky_hotovo + pridat_davky) >= davky_plan
                        }
                        
                        # ZÁPIS DO PEVNÉHO SKLADU
                        gc_sku = SKU_ZELENA.get(zrno)
                        rc_sku = SKU_UPRAZENA.get(zrno)
                        if gc_sku: st.session_state.sklad["zelena"][gc_sku] -= nova_zelena
                        if rc_sku: st.session_state.sklad["uprazena"][rc_sku] += nova_uprazena
                        
                        auto_uloz()
                        st.rerun()

                    if davky_hotovo > 0:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Vrátiť späť (Zrušiť všetko praženie tohto zrna z aktuálnej zmeny)", key=f"undo_{zrno}", type="secondary"):
                            storno_zelena = stav_z_cloudu.get("zelena_real", 0.0)
                            storno_uprazena = stav_z_cloudu.get("uprazena_real", 0.0)
                            
                            gc_sku = SKU_ZELENA.get(zrno)
                            rc_sku = SKU_UPRAZENA.get(zrno)
                            if gc_sku: st.session_state.sklad["zelena"][gc_sku] += storno_zelena
                            if rc_sku: st.session_state.sklad["uprazena"][rc_sku] -= storno_uprazena
                            
                            st.session_state.priebeh_prazenia[zrno] = {
                                "davky_hotovo": 0, "zelena_real": 0.0, "uprazena_real": 0.0, "hotovo": False
                            }
                            auto_uloz()
                            st.rerun()

# ========================================================
# TAB 3: BALENIE (ČISTÁ VÝROBA, zapisuje pevne do Skladu)
# ========================================================
with tab3:
    st.markdown("### Stanica Balenia (Výroba)")
    
    aktivne_balenie = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True and not o.get('Sudy', False)]
    plan_balenia = {}
    for o in aktivne_balenie:
        kluc = f"{o['Káva']}_{o['Gramáž']}"
        if kluc not in plan_balenia: plan_balenia[kluc] = {"kava": o['Káva'], "gramaz": o['Gramáž'], "ciel": 0, "hotovo": 0}
        plan_balenia[kluc]["ciel"] += o['Kusy']
        plan_balenia[kluc]["hotovo"] += int(o.get('Zabalené (ks)', 0))

    if not plan_balenia:
        st.info("Žiadne položky na balenie.")
    else:
        st.markdown("#### 🏷️ Prípravovňa (Potrebné obaly a etikety)")
        rezim_pripravovne = st.radio("Zobraziť kalkuláciu etikiet a obalov pre:", ["Celkový plán (Všetko spolu)", "V procese (Len to, čo ešte chýba vyrobiť)"], horizontal=True)
        
        sumar_data = []
        for v in plan_balenia.values():
            ks = v["ciel"] if rezim_pripravovne == "Celkový plán (Všetko spolu)" else max(0, v["ciel"] - v["hotovo"])
            if ks > 0: sumar_data.append({"Káva": v["kava"], "Gramáž": v["gramaz"], "Kusy": ks})
                
        if sumar_data:
            df_cak = pd.DataFrame(sumar_data)
            sum_pivot_tab3 = df_cak.groupby(['Káva', 'Gramáž'])['Kusy'].sum().reset_index()
            sum_pivot_tab3 = sum_pivot_tab3.pivot(index='Káva', columns='Gramáž', values='Kusy').fillna(0).astype(int)
            for g in [220, 500, 1000]:
                if g not in sum_pivot_tab3.columns: sum_pivot_tab3[g] = 0
            sum_pivot_tab3['Etikety spolu'] = sum_pivot_tab3[[220, 500, 1000]].sum(axis=1)
            sum_pivot_tab3.loc['📦 OBALY SPOLU'] = sum_pivot_tab3.sum(numeric_only=True)
            sum_pivot_tab3 = sum_pivot_tab3[['Etikety spolu', 220, 500, 1000]]
            st.dataframe(sum_pivot_tab3, use_container_width=True)
        else: st.success("Všetky sáčky sú pripravené v regáli.")
            
        st.divider()

        st.markdown("#### 📦 Úlohy pre baliča (Sáčkovanie)")
        kavy_na_balenie = sorted(list(set([v['kava'] for v in plan_balenia.values()])))
        
        for kava in kavy_na_balenie:
            polozky_pre_kavu = [v for v in plan_balenia.values() if v['kava'] == kava]
            vaha_potrebna_chýba = sum([max(0, v['ciel'] - v['hotovo']) * v['gramaz'] / 1000.0 for v in polozky_pre_kavu])
            je_vsetko_kava_hotovo = vaha_potrebna_chýba <= 0
            
            mame_dost = True
            chyba_text = ""
            if not je_vsetko_kava_hotovo and kava in kavy_recepty:
                for zrno, podiel in kavy_recepty[kava]["recept"].items():
                    potreba_zrna = vaha_potrebna_chýba * podiel
                    rc_sku = SKU_UPRAZENA.get(zrno)
                    dostupne = st.session_state.sklad["uprazena"].get(rc_sku, 0.0)
                    if dostupne < potreba_zrna:
                        mame_dost = False
                        chyba_text += f" Chýba {potreba_zrna - dostupne:.2f} kg {zrno}."

            stav_title = "✅ Vyrobené" if je_vsetko_kava_hotovo else "⏳ Vo výrobe"
            with st.expander(f"{stav_title}: **{kava}** (Chýba nasáčkovať {vaha_potrebna_chýba:.2f} kg)", expanded=not je_vsetko_kava_hotovo):
                if not je_vsetko_kava_hotovo:
                    if mame_dost: st.success("✅ Dózy v Sklade sú plné, môžeš začať baliť.")
                    else: st.error(f"⚠️ Pražiar musí ešte dorobiť kávu!{chyba_text}")
                
                for p in polozky_pre_kavu:
                    chýba_ks = max(0, p['ciel'] - p['hotovo'])
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if chýba_ks <= 0: st.markdown(f"✅ **{p['gramaz']}g** sáčok - Vyrobených {p['hotovo']} / {p['ciel']} ks")
                        else: st.markdown(f"➡️ **{p['gramaz']}g** sáčok - Už vyrobené {p['hotovo']} ks (Chýba dorobiť **{chýba_ks} ks**)")
                    with col2:
                        if chýba_ks > 0:
                            def pridaj_sacky(k=p['kava'], g=p['gramaz']):
                                pridavam = st.session_state[f"add_bag_{k}_{g}"]
                                if pridavam > 0:
                                    zvysok_na_rozdelenie = pridavam
                                    for idx, obj in enumerate(st.session_state.aktualne_objednavky):
                                        if obj.get('❌ Zmazať') or obj.get('Sudy') or obj.get('Potvrdene'): continue
                                        if obj['Káva'] == k and obj['Gramáž'] == g:
                                            aktualne_v_obj = int(obj.get('Zabalené (ks)', 0))
                                            potreba_v_obj = obj['Kusy'] - aktualne_v_obj
                                            if potreba_v_obj > 0:
                                                dam = min(zvysok_na_rozdelenie, potreba_v_obj)
                                                st.session_state.aktualne_objednavky[idx]['Zabalené (ks)'] = aktualne_v_obj + dam
                                                zvysok_na_rozdelenie -= dam
                                            if zvysok_na_rozdelenie == 0: break
                                    
                                    # ZÁPIS DO PEVNÉHO SKLADU
                                    vaha_do_sackov = pridavam * g / 1000.0
                                    rc_kod_kavy = MENU_KAVY.get(k)
                                    pc_sku = get_pc_sku(rc_kod_kavy, g)
                                    
                                    st.session_state.sklad["zabalena"][pc_sku] = st.session_state.sklad["zabalena"].get(pc_sku, 0) + pridavam
                                    
                                    if k in kavy_recepty:
                                        for zrno, podiel in kavy_recepty[k]["recept"].items():
                                            zrno_sku = SKU_UPRAZENA.get(zrno)
                                            if zrno_sku: st.session_state.sklad["uprazena"][zrno_sku] -= (vaha_do_sackov * podiel)
                                    
                                    auto_uloz()
                                st.session_state[f"add_bag_{k}_{g}"] = 0
                                
                            st.number_input("Odložiť do regálu (ks):", min_value=0, value=0, step=1, key=f"add_bag_{p['kava']}_{p['gramaz']}", on_change=pridaj_sacky)

# ========================================================
# TAB 4: SKLAD (Trezor a Inventúra)
# ========================================================
with tab4:
    st.markdown("### Aktuálny stav Skladu")
    
    col_dozy, col_sacky = st.columns(2)
    with col_dozy:
        st.markdown("#### 🛢️ Fyzické Dózy (kg)")
        st.caption("Pevný stav upraženej kávy (Kód RC).")
        for sku, vaha in st.session_state.sklad["uprazena"].items():
            if vaha != 0:
                nazov = NAZVY_UPRAZENA.get(sku, "Neznáme")
                st.metric(label=f"{sku} - {nazov}", value=f"{vaha:.2f} kg", delta_color="normal" if vaha>=0 else "inverse")
                
    with col_sacky:
        st.markdown("#### 🛍️ Regál so sáčkami (ks)")
        st.caption("Hotové sáčky čakajúce na Kuriéra (Kód PC).")
        ma_sacky = False
        for sku, ks in st.session_state.sklad["zabalena"].items():
            if ks > 0:
                ma_sacky = True
                st.markdown(f"**{sku}**: {ks} ks")
        if not ma_sacky: st.info("Regál je prázdny.")

    st.divider()
    st.markdown("### 🔒 Zabezpečená zóna: Inventúra")
    heslo_inv = st.text_input("Pre úpravu fyzického skladu zadaj heslo:", type="password", key="heslo_inv")
    vysledok_hesla = over_heslo(heslo_inv) if heslo_inv else False

    if vysledok_hesla is None:
        st.warning("Heslo pre inventúru nie je nastavené v Secrets (kľúč `inventura_heslo`). Inventúra je zamknutá.")
    elif vysledok_hesla:
        st.success("Trezor Skladu odomknutý. Úpravou v tabuľke natvrdo prepíšeš evidenčné stavy.")
        tab_inv_g, tab_inv_r, tab_inv_p = st.tabs(["**Zelená káva (Vrecia)**", "**Upražená káva (Dózy)**", "**Zabalená káva (Regál)**"])
        
        with tab_inv_g:
            df_g = []
            for sku, hodnota in st.session_state.sklad["zelena"].items():
                df_g.append({"Kód (SKU)": sku, "Názov": NAZVY_ZELENA.get(sku, ""), "Systém (kg)": round(hodnota, 2), "Fyzicky_navážené_(kg)": round(hodnota, 2)})
            
            ed_g = st.data_editor(pd.DataFrame(df_g), hide_index=True, disabled=["Kód (SKU)", "Názov", "Systém (kg)"], use_container_width=True)
            if st.button("⚠️ Potvrdiť inventúru Zelenej kávy", type="primary"):
                for row in ed_g.to_dict('records'):
                    st.session_state.sklad["zelena"][row["Kód (SKU)"]] = row["Fyzicky_navážené_(kg)"]
                auto_uloz(historia=True)
                st.rerun()

        with tab_inv_r:
            df_r = []
            for sku, hodnota in st.session_state.sklad["uprazena"].items():
                df_r.append({"Kód (SKU)": sku, "Názov": NAZVY_UPRAZENA.get(sku, ""), "Systém (kg)": round(hodnota, 2), "Fyzicky_navážené_(kg)": round(hodnota, 2)})
            
            ed_r = st.data_editor(pd.DataFrame(df_r), hide_index=True, disabled=["Kód (SKU)", "Názov", "Systém (kg)"], use_container_width=True)
            if st.button("⚠️ Potvrdiť inventúru Upraženej kávy (Dóz)", type="primary"):
                for row in ed_r.to_dict('records'):
                    st.session_state.sklad["uprazena"][row["Kód (SKU)"]] = row["Fyzicky_navážené_(kg)"]
                auto_uloz(historia=True)
                st.rerun()

        with tab_inv_p:
            df_p = []
            for sku, ks in st.session_state.sklad["zabalena"].items():
                df_p.append({"Kód (SKU)": sku, "Systém (ks)": int(ks), "Fyzicky_na_regáli_(ks)": int(ks)})
            
            ed_p = st.data_editor(pd.DataFrame(df_p), hide_index=True, disabled=["Kód (SKU)", "Systém (ks)"], use_container_width=True)
            if st.button("⚠️ Potvrdiť inventúru Zabalených sáčkov", type="primary"):
                for row in ed_p.to_dict('records'):
                    st.session_state.sklad["zabalena"][row["Kód (SKU)"]] = row["Fyzicky_na_regáli_(ks)"]
                auto_uloz(historia=True)
                st.rerun()
    elif heslo_inv != "":
        st.error("Nesprávne heslo.")

# ========================================================
# TAB 5: EXPEDÍCIA (LOGISTIKA)
# ========================================================
with tab5:
    st.markdown("### Expedícia (Kuriér)")
    
    aktivne = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True and not o.get('Sudy', False)]
    cakajuce_expedicia = [o for o in aktivne if not o.get('Potvrdene')]
    hotove_expedicia = [o for o in aktivne if o.get('Potvrdene')]
    
    if not cakajuce_expedicia: st.success("Všetky zákazky sú expedované.")
    else:
        odberatelia = sorted(list(set([o['Odberateľ'] for o in cakajuce_expedicia])))
        
        for odb in odberatelia:
            obj_pre_odb = [o for o in cakajuce_expedicia if o['Odberateľ'] == odb]
            celkovo_ks = sum([o['Kusy'] for o in obj_pre_odb])
            
            mame_vsetky_sacky = True
            chyba_sacky = ""
            for o in obj_pre_odb:
                rc_kod = MENU_KAVY.get(o['Káva'])
                pc_sku = get_pc_sku(rc_kod, o['Gramáž'])
                dostupne_v_regali = st.session_state.sklad["zabalena"].get(pc_sku, 0)
                
                if dostupne_v_regali < o['Kusy']:
                    mame_vsetky_sacky = False
                    chyba_sacky += f" Chýba {o['Kusy'] - dostupne_v_regali}ks {pc_sku}."

            with st.expander(f"📦 **{odb}** (Zostáva odoslať: {celkovo_ks} ks)"):
                if mame_vsetky_sacky:
                    st.success("✅ Všetky sáčky sú pripravené v regáli. Môžeš odoslať balík.")
                    if st.button(f"Expedovať všetko pre: {odb}", key=f"exp_{odb}", type="primary"):
                        for i, o in enumerate(st.session_state.aktualne_objednavky):
                            if o.get('Odberateľ') == odb and not o.get('Potvrdene') and not o.get('❌ Zmazať'):
                                rc_kod = MENU_KAVY.get(o['Káva'])
                                pc_sku = get_pc_sku(rc_kod, o['Gramáž'])
                                st.session_state.sklad["zabalena"][pc_sku] -= o['Kusy']
                                st.session_state.aktualne_objednavky[i]['Potvrdene'] = True
                        auto_uloz()
                        st.rerun()
                else:
                    st.error(f"⚠️ Zákazník sa nedá odoslať, čakáme na Výrobu!{chyba_sacky}")
                    
                st.markdown("**Detail balíka:**")
                for o in obj_pre_odb:
                    rc_kod = MENU_KAVY.get(o['Káva'])
                    pc_sku = get_pc_sku(rc_kod, o['Gramáž'])
                    st.markdown(f"- {o['Kusy']}x **{o['Káva']}** ({o['Gramáž']}g) -> *Kód: {pc_sku}*")

    if hotove_expedicia:
        st.divider()
        with st.expander("🚚 Odoslané zásielky (Archív)"):
            for i, o in enumerate(st.session_state.aktualne_objednavky):
                if o.get('Potvrdene') and not o.get('❌ Zmazať'):
                    def revert_expedicia_callback(idx=i):
                        val = st.session_state[f"rev_{idx}"]
                        st.session_state.aktualne_objednavky[idx]['Potvrdene'] = val
                        obj = st.session_state.aktualne_objednavky[idx]
                        rc_kod = MENU_KAVY.get(obj['Káva'])
                        pc_sku = get_pc_sku(rc_kod, obj['Gramáž'])
                        
                        if not val: st.session_state.sklad["zabalena"][pc_sku] += obj['Kusy']
                        else: st.session_state.sklad["zabalena"][pc_sku] -= obj['Kusy']
                        auto_uloz()
                        
                    st.checkbox(f"{o['Odberateľ']} | {o['Káva']} {o['Gramáž']}g ({o['Kusy']} ks)", value=True, key=f"rev_{i}", on_change=revert_expedicia_callback)

# ========================================================
# TAB 6: ÚČTOVNÍCTVO
# ========================================================
with tab6:
    st.markdown("### Generovanie exportov pre KROS Omega")
    st.info("Pripravuje sa...")
