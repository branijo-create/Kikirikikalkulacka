import streamlit as st
import pandas as pd
import math
import io
import os
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
    
    /* VÝRAZNÉ ZVÄČŠENIE NÁZVOV KÁVY V PRAŽIARNI */
    div[data-testid="stExpander"] summary p {
        font-size: 1.15rem !important;
    }
    div[data-testid="stExpander"] summary p strong {
        font-size: 1.65rem !important; /* O číslo väčšie */
        color: #1A3568 !important;     /* Tmavšia modrá pre lepší kontrast */
        letter-spacing: 0.5px !important;
    }
</style>
"""
st.markdown(firemny_dizajn, unsafe_allow_html=True)

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
        
        try: 
            spreadsheet = client.open(NAZOV_TABULKY_ZALOHA)
        except gspread.exceptions.SpreadsheetNotFound:
            spreadsheet = client.create(NAZOV_TABULKY_ZALOHA)
            spreadsheet.share(None, perm_type='anyone', role='writer')
            
        sheet = spreadsheet.sheet1
        hodnoty = sheet.row_values(1)
        
        val_data = hodnoty[0] if len(hodnoty) > 0 else None
        val_cas = hodnoty[1] if len(hodnoty) > 1 else "Neznámy čas"
        val_nazov = hodnoty[2] if len(hodnoty) > 2 else ""
        
        if val_data and val_data.strip():
            data = json.loads(val_data)
        else:
            data = {"objednavky": [], "prazenie": {}}
            
        if isinstance(data, list): 
            data = {"objednavky": data, "prazenie": {}}
            
        return data, val_cas, val_nazov
    except Exception as e:
        return None, str(e), None

def uloz_do_google_sheets(data_dict, nazov_prazenia):
    try:
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet = client.open(NAZOV_TABULKY_ZALOHA)
        sheet1 = spreadsheet.sheet1
        
        cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        bunky = sheet1.range('A1:C1')
        bunky[0].value = json.dumps(data_dict, ensure_ascii=False)
        bunky[1].value = cas_ulozenia
        bunky[2].value = str(nazov_prazenia)
        
        sheet1.update_cells(bunky)
        return True, None
    except Exception as e:
        chyba = str(e)
        if "200" in chyba:
            return True, None
        return False, chyba

def auto_uloz():
    aktualny_nazov = st.session_state.get('nazov_prazenia', f"Prazenie_PRO_{DNESNY_DATUM}")
    data_na_ulozenie = {
        "objednavky": st.session_state.aktualne_objednavky,
        "prazenie": st.session_state.priebeh_prazenia
    }
    uspech, chyba = uloz_do_google_sheets(data_na_ulozenie, aktualny_nazov)
    
    if not uspech:
        st.toast(f"⚠️ Zlyhalo ukladanie: {chyba}", icon="❌")

def nacitaj_vsetko_z_cloudu_callback():
    zaloha_dict, cas_poslednej_upravy, n_prazenia = nacitaj_z_google_sheets()
    if zaloha_dict is not None:
        st.session_state.aktualne_objednavky = zaloha_dict.get("objednavky", [])
        st.session_state.priebeh_prazenia = zaloha_dict.get("prazenie", {})
        if n_prazenia:
            st.session_state.nazov_prazenia = n_prazenia
        aktivne = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
        st.session_state.info_cloud = f"Synchronizované: {len(aktivne)} položiek | Posledná úprava: {cas_poslednej_upravy}"
        st.session_state.msg_uspech = True
    else:
        st.session_state.info_cloud = f"Chyba synchronizácie: {cas_poslednej_upravy}"
        st.session_state.msg_chyba = True

# --- NÚDZOVÉ ČISTENIE DISKU ---
def vycisti_disk_robota():
    try:
        import gspread
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        subory = client.list_spreadsheet_files()
        zmazane = 0
        for f in subory:
            client.del_spreadsheet(f['id'])
            zmazane += 1
        return True, zmazane
    except Exception as e:
        return False, str(e)

# --- AUTO-LOAD PRI ŠTARTE ---
if 'aktualne_objednavky' not in st.session_state:
    zaloha_dict, cas, n_prazenia = nacitaj_z_google_sheets()
    if zaloha_dict is not None:
        st.session_state.aktualne_objednavky = zaloha_dict.get("objednavky", [])
        st.session_state.priebeh_prazenia = zaloha_dict.get("prazenie", {})
        aktivne_start = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
        st.session_state.info_cloud = f"Synchronizované: {len(aktivne_start)} položiek | Posledná úprava: {cas}"
    else:
        st.session_state.aktualne_objednavky = []
        st.session_state.priebeh_prazenia = {}
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
    st.caption("Verzia 7.9 | Výrobný manažment")

with col_head_right:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=110)
    elif os.path.exists("logo.svg"):
        st.image("logo.svg", width=110)
    else:
        st.markdown(
            """
            <div style="text-align: right; padding-top: 10px;">
                <span style="font-family: 'Barlow Condensed', sans-serif; font-weight: 900; color: #2B5098; font-size: 1.8rem; letter-spacing: 2px;">
                    KIKIRIKI
                </span>
            </div>
            """, 
            unsafe_allow_html=True
        )

st.text_input("Identifikátor praženia:", key="nazov_prazenia", on_change=auto_uloz)

# ========================================================
# 🚀 ZÁLOŽKY
# ========================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "**OBJEDNÁVKY**", 
    "**PRAŽIAREŇ**", 
    "**BALENIE**", 
    "**SKLAD**", 
    "**ÚČTOVNÍCTVO**"
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
                st.dataframe(df_ukazka[['Odberateľ', 'Káva', 'Gramáž', 'Kusy']], use_container_width=True, hide_index=True)

    if st.session_state.pop('msg_uspech', False):
        st.success("Dáta úspešne stiahnuté a zosynchronizované.")
    if st.session_state.pop('msg_chyba', False):
        st.error("Nepodarilo sa načítať zálohu z Cloudu.")

    col_load, col_save = st.columns(2)
    with col_load:
        if st.button("Načítať stav z Cloudu", type="secondary", use_container_width=True):
            nacitaj_vsetko_z_cloudu_callback()
            st.rerun()

    with col_save:
        if st.button("Uložiť aktuálny stav do Cloudu", type="primary", use_container_width=True):
            auto_uloz()
            cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            aktivne = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
            st.session_state.info_cloud = f"Synchronizované: {len(aktivne)} položiek | Posledná úprava: {cas_ulozenia}"
            st.success("Aktuálny zoznam a priebeh praženia bol bezpečne uložený.")
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
                    zabalene_hist = int(row.get("Zabalené (ks)", kusy_zaklad)) 
                    potvrdene_hist = bool(row.get("Potvrdene", False))
                    sudy_hist = bool(row.get("Sudy", False)) if pd.notna(row.get("Sudy")) else False
                    st.session_state.aktualne_objednavky.append({
                        "Odberateľ": str(row.get("Odberateľ", "Neznámy")),
                        "Káva": str(row.get("Káva", "")),
                        "Gramáž": int(row.get("Gramáž", 0)),
                        "Kusy": kusy_zaklad,
                        "Zabalené (ks)": zabalene_hist,
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
            if kusy_220 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 220, "Kusy": kusy_220, "Zabalené (ks)": kusy_220, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            if kusy_500 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 500, "Kusy": kusy_500, "Zabalené (ks)": kusy_500, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            if kusy_1000 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 1000, "Kusy": kusy_1000, "Zabalené (ks)": kusy_1000, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
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
                if v > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": k, "Gramáž": gramaz, "Kusy": v, "Zabalené (ks)": v, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
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
            
            upravene_df = st.data_editor(df_objednavky_vstup, use_container_width=True, num_rows="fixed", hide_index=False, key="tabulka_objednavok")
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
                    st.session_state.aktualne_objednavky = []
                    st.session_state.priebeh_prazenia = {} 
                    auto_uloz()
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
                
                celkovo_davok = int(df_plan['Dávky'].sum())
                celkova_zelena = df_plan['Zelená (kg)'].sum()
                celkova_uprazena = celkova_zelena * (1 - (STANDARDNY_VYPEK / 100.0))
                
                st.markdown(f"**Celkový výkon:** {celkovo_davok} dávok")
                st.markdown(f"**Spotreba:** {celkova_zelena:.1f} kg zelenej -> {celkova_uprazena:.1f} kg upraženej")
                
                total_row_plan = {"Zelené zrno": "SPOLU:", "Upražiť (kg)": round(celkova_uprazena, 2), "Dávky": celkovo_davok, "Zelená (kg)": round(celkova_zelena, 2), "Zostatok (kg)": ""}
                df_plan_excel = pd.concat([df_plan, pd.DataFrame([total_row_plan])], ignore_index=True)
                
                finalny_plan_blendov = []
                for meno_blendu, celkova_vaha_blendu in potreba_skladania_blendov.items():
                    recept = kavy_recepty[meno_blendu]["recept"]
                    for zrno, podiel in recept.items():
                        finalny_plan_blendov.append({"Názov blendu": meno_blendu, "Celková hmotnosť (kg)": round(celkova_vaha_blendu, 2), "Kávová zložka": zrno, "Podiel v blende": f"{int(podiel * 100)}%", "Hmotnosť zložky (kg)": round(celkova_vaha_blendu * podiel, 2)})
                
                df_blendov = pd.DataFrame(finalny_plan_blendov) if finalny_plan_blendov else pd.DataFrame()
                
                df_objednavky_export_balenie = [o for o in aktivne_objednavky if not o.get('Sudy', False)]
                if df_objednavky_export_balenie:
                    df_sum_obalov = pd.DataFrame(df_objednavky_export_balenie).groupby(['Káva', 'Gramáž'])['Kusy'].sum().reset_index()
                    sum_pivot_ex = df_sum_obalov.pivot(index='Káva', columns='Gramáž', values='Kusy').fillna(0).astype(int)
                    for g in [220, 500, 1000]:
                        if g not in sum_pivot_ex.columns: sum_pivot_ex[g] = 0
                    sum_pivot_ex['Spolu etikiet'] = sum_pivot_ex.sum(axis=1)
                    sum_pivot_ex.loc['SPOLU SÁČKOV'] = sum_pivot_ex.sum(numeric_only=True)
                    sum_pivot_ex = sum_pivot_ex[['Spolu etikiet', 220, 500, 1000]].reset_index()
                    sum_pivot_ex.rename(columns={'index': 'Káva', 220: '220g', 500: '500g', 1000: '1000g'}, inplace=True) 
                else:
                    sum_pivot_ex = pd.DataFrame(columns=['Káva', 'Spolu etikiet', '220g', '500g', '1000g'])

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    
                    def write_styled_sheet(df, sheet_name, group_by_col=None):
                        worksheet = workbook.add_worksheet(sheet_name)
                        max_row, max_col = df.shape
                        if max_row == 0: return

                        worksheet.autofilter(0, 0, max_row, max_col - 1)
                        header_format = workbook.add_format({'bold': True, 'bg_color': '#2B5098', 'font_color': 'white', 'border': 1})
                        for col_num, value in enumerate(df.columns):
                            worksheet.write(0, col_num, str(value), header_format)
                            max_len = max(df[df.columns[col_num]].astype(str).map(len).max(), len(str(value))) + 2
                            worksheet.set_column(col_num, col_num, max_len)
                            
                        format_z1 = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1})
                        format_z2 = workbook.add_format({'bg_color': '#F9F9F9', 'border': 1}) 
                        format_total = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA', 'border': 1}) 
                        
                        for r_idx in range(max_row):
                            is_total = str(df.iloc[r_idx, 0]).startswith('SPOLU')
                            fmt = format_total if is_total else (format_z1 if r_idx % 2 == 0 else format_z2)
                            for c_idx in range(max_col):
                                cell_val = df.iloc[r_idx, c_idx]
                                if pd.isna(cell_val): worksheet.write(r_idx + 1, c_idx, "", fmt)
                                else:
                                    if isinstance(cell_val, (int, float)): worksheet.write_number(r_idx + 1, c_idx, cell_val, fmt)
                                    else: worksheet.write(r_idx + 1, c_idx, str(cell_val), fmt)

                    write_styled_sheet(df_plan_excel, 'Plan_Prazenia')
                    write_styled_sheet(df_objednavky_export.drop(columns=['❌ Zmazať'], errors='ignore'), 'Spracovane_Objednavky')
                    if not df_blendov.empty: write_styled_sheet(df_blendov, 'Plan_Blendov', group_by_col='Názov blendu')
                    write_styled_sheet(sum_pivot_ex, 'Sumar_Obalov')

                st.download_button(
                    label="Stiahnuť Kikiriki Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Kikiriki_PRO_{st.session_state.nazov_prazenia}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True
                )

# ========================================================
# TAB 2: PRAŽIAREŇ
# ========================================================
with tab2:
    st.markdown("### Panel pri stroji")
    st.caption("Evidencia reálneho pokroku voči pôvodnému plánu. Každá potvrdená dávka ide rovno do Skladu.")
    
    aktivne_objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
    potreba_zelenej_podla_zrna = {}
    
    for o in aktivne_objednavky:
        je_sud = o.get("Sudy") == True
        if je_sud:
            zelena_kg_zaklad = o["Kusy"] * KAPACITA_ZELENA_BATCH
        else:
            uprazena_kg = (o["Kusy"] * o["Gramáž"] / 1000.0)
            zelena_kg_zaklad = uprazena_kg / (1 - (STANDARDNY_VYPEK / 100.0))
        
        if o["Káva"] in kavy_recepty:
            recept = kavy_recepty[o["Káva"]]["recept"]
            for zrno, podiel in recept.items():
                potreba_zelenej_podla_zrna[zrno] = potreba_zelenej_podla_zrna.get(zrno, 0) + (zelena_kg_zaklad * podiel)

    if not potreba_zelenej_podla_zrna:
        st.info("Plán praženia je prázdny. Začni pridaním objednávok v Objednávkach.")
    else:
        for zrno, teoreticka_vaha_zelena in potreba_zelenej_podla_zrna.items():
            davky_plan = math.ceil(teoreticka_vaha_zelena / KAPACITA_ZELENA_BATCH)
            
            stav_z_cloudu = st.session_state.priebeh_prazenia.get(zrno, {"davky_hotovo": 0, "zelena_real": 0.0, "uprazena_real": 0.0, "hotovo": False})
            
            if "davky_hotovo" not in stav_z_cloudu:
                if stav_z_cloudu.get("hotovo") == True:
                    davky_hotovo = davky_plan
                else:
                    davky_hotovo = 0
            else:
                davky_hotovo = stav_z_cloudu["davky_hotovo"]
                
            davky_zostava = max(0, davky_plan - davky_hotovo)
            je_hotovo = davky_hotovo >= davky_plan
            ma_navyse = davky_hotovo > davky_plan
            
            # NOVÁ LOGIKA PRE IKONKY STAVU
            if ma_navyse:
                stav_text = "✅ ⬆️ Hotovo (Navyše)"
            elif je_hotovo:
                stav_text = "✅ Hotovo"
            elif davky_hotovo > 0:
                stav_text = "🔄 Rozpracované"
            else:
                stav_text = "⏳ Na rade"
                
            expander_title = f"{stav_text}: **{zrno}** ({davky_hotovo} / {davky_plan} dávok)"
            
            with st.expander(expander_title, expanded=not je_hotovo):
                col_info, col_input = st.columns([1, 1])
                
                with col_info:
                    st.markdown(f"**Cieľový plán (podľa objednávok):** {davky_plan} dávok")
                    st.markdown(f"**Už odpražené a naskladnené:** {davky_hotovo} dávok")
                    
                    if davky_zostava > 0:
                        st.warning(f"**Zostáva dokončiť:** {davky_zostava} dávok")
                    elif ma_navyse:
                        st.info(f"**Odpražené o {davky_hotovo - davky_plan} dávok navyše.**")
                    else:
                        st.success(f"**Plán je presne splnený!**")
                
                with col_input:
                    st.markdown("**Zapísať reálne odpražené dávky:**")
                    
                    default_pridat = davky_zostava if davky_zostava > 0 else 1
                    
                    pridat_davky = st.number_input(
                        "Počet práve odpražených dávok:", 
                        min_value=1, 
                        value=default_pridat, 
                        step=1, 
                        key=f"davky_{zrno}"
                    )
                    
                    if st.button(f"Potvrdiť odpraženie {pridat_davky} dávok", key=f"btn_praz_{zrno}", type="primary"):
                        nova_zelena = pridat_davky * KAPACITA_ZELENA_BATCH
                        nova_uprazena = nova_zelena * (1 - (STANDARDNY_VYPEK / 100.0))
                        
                        st.session_state.priebeh_prazenia[zrno] = {
                            "davky_hotovo": davky_hotovo + pridat_davky,
                            "zelena_real": stav_z_cloudu.get("zelena_real", 0.0) + nova_zelena,
                            "uprazena_real": stav_z_cloudu.get("uprazena_real", 0.0) + nova_uprazena,
                            "hotovo": (davky_hotovo + pridat_davky) >= davky_plan
                        }
                        auto_uloz()
                        st.rerun()
                        
                    if davky_hotovo > 0:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Vrátiť späť (Zrušiť všetko praženie tohto zrna)", key=f"undo_{zrno}", type="secondary"):
                            st.session_state.priebeh_prazenia[zrno] = {
                                "davky_hotovo": 0, "zelena_real": 0.0, "uprazena_real": 0.0, "hotovo": False
                            }
                            auto_uloz()
                            st.rerun()

# ========================================================
# TAB 3: BALENIE
# ========================================================
with tab3:
    st.markdown("### Priebeh balenia sáčkov")
    st.caption("Odškrtávaj hotové balenia. Množstvo sa automaticky odpočíta zo Skladu.")
    
    def zmena_balenia_pro_callback(index_v_liste):
        st.session_state.aktualne_objednavky[index_v_liste]['Zabalené (ks)'] = st.session_state[f"pro_pocet_{index_v_liste}"]
        st.session_state.aktualne_objednavky[index_v_liste]['Potvrdene'] = st.session_state[f"pro_chk_{index_v_liste}"]
        auto_uloz() 

    aktivne_balenie = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True and not o.get('Sudy', False)]
    
    if not aktivne_balenie:
        st.info("Žiadne položky na balenie.")
    else:
        for i, obj in enumerate(st.session_state.aktualne_objednavky):
            if obj.get('❌ Zmazať') == True or obj.get('Sudy') == True: continue
                
            with st.container():
                aktualne_zabalene = int(obj.get('Zabalené (ks)', obj['Kusy']))
                objednane = int(obj['Kusy'])
                potvrdene = obj.get('Potvrdene') == True
                
                col_text, col_cisla, col_chk = st.columns([4, 1, 1])
                with col_text:
                    if potvrdene and aktualne_zabalene == objednane:
                        st.markdown(f"**{obj['Odberateľ']}** | {obj['Káva']} ({obj['Gramáž']}g) - {objednane} ks (Hotovo)")
                    else:
                        st.markdown(f"**{obj['Odberateľ']}** | {obj['Káva']} ({obj['Gramáž']}g) - Objednané: {objednane} ks")
                
                with col_cisla:
                    st.number_input("Zabalené:", min_value=0, value=aktualne_zabalene, step=1, key=f"pro_pocet_{i}", on_change=zmena_balenia_pro_callback, args=(i,), label_visibility="collapsed")
                with col_chk:
                    st.checkbox("Hotovo", value=potvrdene, key=f"pro_chk_{i}", on_change=zmena_balenia_pro_callback, args=(i,))
            st.markdown("---")

# ========================================================
# TAB 4: SKLAD
# ========================================================
with tab4:
    st.markdown("### Aktuálny stav skladu (Dózy)")
    st.caption("Fyzický zostatok vypraženej kávy po odpočítaní zabalených sáčkov.")
    
    stav_doz = {}
    for zrno, data in st.session_state.priebeh_prazenia.items():
        if data.get("davky_hotovo", 0) > 0 or data.get("hotovo"):
            stav_doz[zrno] = stav_doz.get(zrno, 0.0) + data.get("uprazena_real", 0.0)
            
    aktivne_objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
    for o in aktivne_objednavky:
        if o.get("Potvrdene") == True and o.get("Sudy") != True:
            zabalena_vaha_kg = o["Zabalené (ks)"] * o["Gramáž"] / 1000.0
            if o["Káva"] in kavy_recepty:
                recept = kavy_recepty[o["Káva"]]["recept"]
                for zrno, podiel in recept.items():
                    if zrno in stav_doz:
                        stav_doz[zrno] -= (zabalena_vaha_kg * podiel)

    if not stav_doz:
        st.info("Sklad je prázdny. Zatiaľ nebolo nič upražené.")
    else:
        dozy_cols = st.columns(len(stav_doz))
        for idx, (zrno, vaha) in enumerate(stav_doz.items()):
            with dozy_cols[idx % len(dozy_cols)]:
                st.metric(label=zrno, value=f"{vaha:.2f} kg", delta="Zostatok" if vaha >= 0 else "Chýba do sáčkov", delta_color="normal" if vaha>=0 else "inverse")

# ========================================================
# TAB 5: ÚČTOVNÍCTVO
# ========================================================
with tab5:
    st.markdown("### Generovanie exportov pre KROS Omega")
    st.info("Pripravuje sa...")

# ========================================================
# NÚDZOVÝ SERVISNÝ PANEL
# ========================================================
st.divider()
with st.expander("🛠️ Servisný panel (Oprava Google Disku)"):
    st.warning("Ak ti systém hlási chybu 'Drive storage quota has been exceeded', klikni na tlačidlo nižšie. Systém vymaže všetky staré testovacie súbory, ktoré zahltili pamäť skrytého robota.")
    if st.button("🚨 Vymazať staré súbory robota a uvoľniť pamäť", type="primary"):
        uspech, sprava = vycisti_disk_robota()
        if uspech:
            st.success(f"Hotovo! Zmazaných súborov: {sprava}. Pamäť je uvoľnená, môžeš normálne pokračovať.")
        else:
            st.error(f"Chyba pri mazaní: {sprava}")
