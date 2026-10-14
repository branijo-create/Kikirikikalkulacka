import streamlit as st
import pandas as pd
import math
import io
from datetime import datetime, timedelta
import json

st.set_page_config(page_title="Roastery Manager v3.7", page_icon="☕", layout="wide")

# --- KONFIGURÁCIA Z TVOJHO KÓDU ---
KAPACITA_ZELENA_BATCH = 5.0
STANDARDNY_VYPEK = 20
DNESNY_DATUM = datetime.now().strftime("%d-%m-%Y")
NAZOV_TABULKY_ZALOHA = "Kikiriki_Zaloha_Balenia"

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
    if isinstance(creds_data, str):
        creds_dict = json.loads(creds_data)
    else:
        creds_dict = dict(creds_data)
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    return Credentials.from_service_account_info(creds_dict, scopes=scopes)

def nacitaj_z_google_sheets():
    try:
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        sheet = client.open(NAZOV_TABULKY_ZALOHA).sheet1
        
        try:
            hodnoty = sheet.row_values(1)
            val_data = hodnoty[0] if len(hodnoty) > 0 else None
            val_cas = hodnoty[1] if len(hodnoty) > 1 else "Neznámy čas"
            val_nazov = hodnoty[2] if len(hodnoty) > 2 and hodnoty[2].strip() != "" else ""
        except:
            val_data = None
            val_cas = "Neznámy čas"
            val_nazov = ""
            
        data = json.loads(val_data) if val_data else None
        return data, val_cas, val_nazov
    except Exception as e:
        return None, None, None

def uloz_do_google_sheets(data, nazov_prazenia):
    try:
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet = client.open(NAZOV_TABULKY_ZALOHA)
        
        sheet1 = spreadsheet.sheet1
        cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        sheet1.update_acell('A1', json.dumps(data, ensure_ascii=False))
        sheet1.update_acell('B1', cas_ulozenia)
        sheet1.update_acell('C1', str(nazov_prazenia))
        
        try:
            log_sheet = spreadsheet.worksheet("Logy")
        except:
            log_sheet = spreadsheet.add_worksheet(title="Logy", rows="1000", cols="3")
            log_sheet.append_row(["Čas uloženia", "Názov praženia", "Dáta (JSON)"])
        
        log_sheet.append_row([cas_ulozenia, str(nazov_prazenia), json.dumps(data, ensure_ascii=False)])
        return True
    except Exception as e:
        return False

def auto_uloz():
    aktualny_nazov = st.session_state.get('nazov_prazenia', f"Prazenie_{DNESNY_DATUM}")
    uloz_do_google_sheets(st.session_state.aktualne_objednavky, aktualny_nazov)

# --- OPRAVA CHYBY: CALLBACK FUNKCIA NA NAČÍTANIE ---
def nacitaj_vsetko_z_cloudu_callback():
    zaloha, cas_poslednej_upravy, n_prazenia = nacitaj_z_google_sheets()
    if zaloha:
        st.session_state.aktualne_objednavky = zaloha
        if n_prazenia:
            st.session_state.nazov_prazenia = n_prazenia
        aktivne = [o for o in zaloha if not o.get('❌ Zmazať', False)]
        st.session_state.info_cloud = f"☁️ **Stav na Google Disku:** {len(aktivne)} aktívnych položiek | 🕒 Posledná úprava: **{cas_poslednej_upravy}**"
        st.session_state.zaloha_data = aktivne
        st.session_state.msg_uspech = True
    else:
        st.session_state.info_cloud = "☁️ **Stav na Google Disku:** Prázdny stôl (žiadne aktívne objednávky)."
        st.session_state.zaloha_data = []
        st.session_state.msg_chyba = True

def uloz_export_pre_evicku(odberatel, txt_obsah):
    try:
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet = client.open(NAZOV_TABULKY_ZALOHA)
        try:
            evicka_sheet = spreadsheet.worksheet("Evicka_Logy")
        except:
            evicka_sheet = spreadsheet.add_worksheet(title="Evicka_Logy", rows="1000", cols="3")
            evicka_sheet.append_row(["Čas exportu", "Odberateľ", "TXT Obsah"])
        
        cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        evicka_sheet.append_row([cas_ulozenia, odberatel, txt_obsah])
        return True
    except Exception as e:
        return False

def nacitaj_exporty_pre_evicku():
    try:
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet = client.open(NAZOV_TABULKY_ZALOHA)
        evicka_sheet = spreadsheet.worksheet("Evicka_Logy")
        zaznamy = evicka_sheet.get_all_values()[1:] 
        return list(reversed(zaznamy))
    except Exception as e:
        return []

def nacitaj_logy_z_google_sheets():
    try:
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet = client.open(NAZOV_TABULKY_ZALOHA)
        log_sheet = spreadsheet.worksheet("Logy")
        zaznamy = log_sheet.get_all_values()[1:] 
        return list(reversed(zaznamy)) 
    except Exception as e:
        return []

# --- AUTO-LOAD PRI ŠTARTE ---
if 'aktualne_objednavky' not in st.session_state:
    zaloha, cas, n_prazenia = nacitaj_z_google_sheets()
    st.session_state.aktualne_objednavky = zaloha if zaloha else []
    st.session_state.pociatocny_nazov = n_prazenia if n_prazenia else f"Prazenie_{DNESNY_DATUM}"

if 'nazov_prazenia' not in st.session_state:
    st.session_state.nazov_prazenia = st.session_state.get('pociatocny_nazov', f"Prazenie_{DNESNY_DATUM}")

if 'form_key' not in st.session_state:
    st.session_state.form_key = 0

def vynuluj_policka():
    st.session_state.form_key += 1


# --- TAJNÝ BOČNÝ PANEL (HESLÁ) ---
with st.sidebar:
    st.write("")
    tajne_heslo = st.text_input("🔑", type="password", help="Zadaj prístupový kód")
    
    if tajne_heslo == "kikiriki":
        st.warning("🛠️ **TAJNÝ SERVISNÝ REŽIM (BRAŇO)**")
        if st.button("📥 Načítať archív logov", use_container_width=True):
            st.session_state.logy_data_zoznam = nacitaj_logy_z_google_sheets()
            
        if st.session_state.get('logy_data_zoznam'):
            logy = st.session_state.logy_data_zoznam
            if logy:
                moznosti = []
                for r in logy:
                    if len(r) >= 3: moznosti.append(f"{r[0]} | {r[1]}")
                    else: moznosti.append(f"{r[0]}")
                
                vybrany_cas = st.selectbox("Vyber čas na obnovenie:", moznosti)
                if st.button("⚠️ OBNOVIŤ TENTO ČAS", type="primary", use_container_width=True):
                    idx = moznosti.index(vybrany_cas)
                    vybrany_json = logy[idx][-1] 
                    try:
                        obnovene_data = json.loads(vybrany_json)
                        st.session_state.aktualne_objednavky = obnovene_data
                        if len(logy[idx]) >= 3:
                            st.session_state.nazov_prazenia = logy[idx][1]
                        auto_uloz()
                        st.success("✅ Systém bol úspešne vrátený v čase!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Chyba pri obnove: {e}")

    elif tajne_heslo == "cicky":
        st.success("👋 **VITAJ, EVIČKA (Účtovný portál)**")
        if st.button("📥 Načítať dostupné exporty", use_container_width=True):
            st.session_state.evicka_exporty = nacitaj_exporty_pre_evicku()
            
        if st.session_state.get('evicka_exporty') is not None:
            exporty = st.session_state.evicka_exporty
            if exporty:
                moznosti_evicka = [f"{r[0]} | Odberateľ: {r[1]}" for r in exporty]
                vybrany_export = st.selectbox("Vyber si export pre stiahnutie:", moznosti_evicka)
                vybrany_txt = next(r[2] for r in exporty if f"{r[0]} | Odberateľ: {r[1]}" == vybrany_export)
                
                st.download_button(
                    label="⚙️ Stiahnuť vybraný TXT pre Kros Omegu",
                    data=vybrany_txt.encode('windows-1250', errors='replace'),
                    file_name=f"Kikiriki_Omega_{vybrany_export[:10].replace('.', '')}.txt",
                    mime="text/plain",
                    type="primary",
                    use_container_width=True
                )

# --- HLAVNÉ ROZHRANIE ---
st.title("☕ Roastery Manager v3.7")

st.text_input("📅 Názov aktuálneho praženia (Tento názov si systém pamätá, neprepisuj ho každý deň):", key="nazov_prazenia", on_change=auto_uloz)

tab1, tab2 = st.tabs(["🛒 1. Objednávky a Praženie", "📦 2. Kontrola balenia a Export"])

# ========================================================
# TAB 1: OBJEDNÁVKY A PRAŽENIE
# ========================================================
with tab1:
    if 'info_cloud' not in st.session_state:
        zaloha, cas, _ = nacitaj_z_google_sheets()
        if not zaloha:
            st.session_state.info_cloud = "☁️ **Stav na Google Disku:** Prázdny stôl (žiadne aktívne objednávky)."
            st.session_state.zaloha_data = []
        else:
            aktivne = [o for o in zaloha if not o.get('❌ Zmazať', False)]
            st.session_state.info_cloud = f"☁️ **Stav na Google Disku:** {len(aktivne)} aktívnych položiek | 🕒 Posledná úprava: **{cas}**"
            st.session_state.zaloha_data = aktivne

    st.info(st.session_state.info_cloud)

    if st.session_state.get('zaloha_data'):
        with st.expander("👀 Klikni sem pre zobrazenie toho, čo je aktuálne uložené na Disku"):
            df_ukazka = pd.DataFrame(st.session_state.zaloha_data)
            if not df_ukazka.empty:
                st.dataframe(df_ukazka[['Odberateľ', 'Káva', 'Gramáž', 'Kusy']], use_container_width=True, hide_index=True)

    st.subheader("☁️ Spoločná zdieľaná pamäť (Braňo / Majo)")
    col_load, col_save = st.columns(2)

    with col_load:
        # Používame bezpečný callback, ktorý všetko vybaví na pozadí
        st.button("🔄 Načítať spoločnú prácu z Google disku", type="primary", use_container_width=True, on_click=nacitaj_vsetko_z_cloudu_callback)
        if st.session_state.pop('msg_uspech', False):
            st.success("✅ Dáta úspešne načítané!")
        if st.session_state.pop('msg_chyba', False):
            st
