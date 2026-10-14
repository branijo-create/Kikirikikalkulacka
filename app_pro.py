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

# --- GLOBÁLNY VÝPOČET STAVU SKLADU (Dózy aj Hotové obaly) ---
stav_doz = {}
regal_obalov = {}  # "Káva_Gramáž": ks

if 'priebeh_prazenia' in st.session_state:
    for zrno, data in st.session_state.priebeh_prazenia.items():
        if data.get("davky_hotovo", 0) > 0 or data.get("hotovo"):
            stav_doz[zrno] = stav_doz.get(zrno, 0.0) + data.get("uprazena_real", 0.0)
            
if 'aktualne_objednavky' in st.session_state:
    aktivne_obj_sklad = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
    for o in aktivne_obj_sklad:
        if o.get("Sudy") != True:
            kluc_obalu = f"{o['Káva']}_{o['Gramáž']}"
            zabalene_ks = int(o.get('Zabalené (ks)', 0))
            expedovane = o.get('Potvrdene') == True
            
            # 1. Odpísať kávu z Dóz za každý ZABALENÝ kus (ešte pred expedíciou)
            if zabalene_ks > 0:
                zabalena_vaha_kg = zabalene_ks * o["Gramáž"] / 1000.0
                if o["Káva"] in kavy_recepty:
                    recept = kavy_recepty[o["Káva"]]["recept"]
                    for zrno, podiel in recept.items():
                        if zrno in stav_doz:
                            stav_doz[zrno] -= (zabalena_vaha_kg * podiel)
            
            # 2. Strážiť počet dostupných obalov v Regáli
            if not expedovane:
                regal_obalov[kluc_obalu] = regal_obalov.get(kluc_obalu, 0) + zabalene_ks

# --- HLAVIČKA A LOGO ---
col_head_left, col_head_right = st.columns([3, 1])

with col_head_left:
    st.title("Kikiriki Roastery PRO")
    st.caption("Verzia 8.4 | Výroba & Logistika")

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "**OBJEDNÁVKY**", 
    "**PRAŽIAREŇ**", 
    "**BALENIE**", 
    "**SKLAD**", 
    "**EXPED.**",
    "**ÚČTOVNÍCTVO**"
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
            auto_uloz()
            st.success("Aktuálny zoznam uložený.")
            st.rerun()

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
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_plan_excel.to_excel(writer, index=False, sheet_name='Plan_Prazenia')
                    df_objednavky_export.drop(columns=['❌ Zmazať'], errors='ignore').to_excel(writer, index=False, sheet_name='Spracovane_Objednavky')
                st.download_button(
                    label="Stiahnuť Kikiriki Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Kikiriki_PRO_{st.session_state.nazov_prazenia}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True
                )

# ========================================================
# TAB 2: PRAŽIAREŇ
# ========================================================
with tab2:
    st.markdown("### Panel pri stroji")
    
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
        st.info("Plán praženia je prázdny.")
    else:
        for zrno, teoreticka_vaha_zelena in potreba_zelenej_podla_zrna.items():
            davky_plan = math.ceil(teoreticka_vaha_zelena / KAPACITA_ZELENA_BATCH)
            stav_z_cloudu = st.session_state.priebeh_prazenia.get(zrno, {"davky_hotovo": 0, "zelena_real": 0.0, "uprazena_real": 0.0, "hotovo": False})
            
            davky_hotovo = stav_z_cloudu.get("davky_hotovo", davky_plan if stav_z_cloudu.get("hotovo") else 0)
            davky_zostava = max(0, davky_plan - davky_hotovo)
            je_hotovo = davky_hotovo >= davky_plan
            ma_navyse = davky_hotovo > davky_plan
            
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
                    st.markdown(f"**Cieľový plán:** {davky_plan} dávok")
                    st.markdown(f"**V sklade (Dózy):** {davky_hotovo} dávok")
                    if davky_zostava > 0: st.warning(f"**Zostáva dokončiť:** {davky_zostava} dávok")
                    elif ma_navyse: st.info(f"**Odpražené o {davky_hotovo - davky_plan} dávok navyše.**")
                    else: st.success("**Plán je splnený!**")
                
                with col_input:
                    pridat_davky = st.number_input("Počet práve odpražených dávok:", min_value=1, value=davky_zostava if davky_zostava > 0 else 1, step=1, key=f"davky_{zrno}")
                    if st.button(f"Potvrdiť {pridat_davky} dávok do Skladu", key=f"btn_praz_{zrno}", type="primary"):
                        nova_zelena = pridat_davky * KAPACITA_ZELENA_BATCH
                        st.session_state.priebeh_prazenia[zrno] = {
                            "davky_hotovo": davky_hotovo + pridat_davky,
                            "zelena_real": stav_z_cloudu.get("zelena_real", 0.0) + nova_zelena,
                            "uprazena_real": stav_z_cloudu.get("uprazena_real", 0.0) + (nova_zelena * (1 - (STANDARDNY_VYPEK / 100.0))),
                            "hotovo": (davky_hotovo + pridat_davky) >= davky_plan
                        }
                        auto_uloz()
                        st.rerun()

# ========================================================
# TAB 3: BALENIE (ČISTÁ VÝROBA)
# ========================================================
with tab3:
    st.markdown("### Stanica Balenia (Výroba)")
    st.caption("Úlohou baliča je iba naplniť sáčky podľa zoznamu nižšie a odložiť ich do regálu pre kuriéra. Odberateľov nerieši.")
    
    aktivne_balenie = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True and not o.get('Sudy', False)]
    
    # Výpočet toho, čo treba CELKOVO vyrobiť, a odpočítanie toho, čo už JE ZABALENÉ
    plan_balenia = {} # "Káva_Gramáž": {"ciel": 0, "hotovo": 0}
    
    for o in aktivne_balenie:
        kluc = f"{o['Káva']}_{o['Gramáž']}"
        if kluc not in plan_balenia:
            plan_balenia[kluc] = {"kava": o['Káva'], "gramaz": o['Gramáž'], "ciel": 0, "hotovo": 0}
        plan_balenia[kluc]["ciel"] += o['Kusy']
        plan_balenia[kluc]["hotovo"] += int(o.get('Zabalené (ks)', 0))

    if not plan_balenia:
        st.info("Žiadne položky na balenie.")
    else:
        # SUMÁR OBALOV S PREPÍNAČOM
        st.markdown("#### 🏷️ Prípravovňa (Potrebné obaly a etikety)")
        rezim_pripravovne = st.radio("Zobraziť kalkuláciu etikiet a obalov pre:", ["Celkový plán (Všetko spolu)", "V procese (Len to, čo ešte chýba vyrobiť)"], horizontal=True)
        
        sumar_data = []
        for v in plan_balenia.values():
            ks = v["ciel"] if rezim_pripravovne == "Celkový plán (Všetko spolu)" else max(0, v["ciel"] - v["hotovo"])
            if ks > 0:
                sumar_data.append({"Káva": v["kava"], "Gramáž": v["gramaz"], "Kusy": ks})
                
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
        else:
            st.success("Všetky sáčky sú pripravené v regáli.")
            
        st.divider()

        # ZOZNAM NA VÝROBU (BEZ ODBERATEĽOV)
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
                    dostupne = stav_doz.get(zrno, 0.0)
                    if dostupne < potreba_zrna:
                        mame_dost = False
                        chyba_text += f" Chýba {potreba_zrna - dostupne:.2f} kg {zrno}."

            stav_title = "✅ Vyrobené" if je_vsetko_kava_hotovo else "⏳ Vo výrobe"
            with st.expander(f"{stav_title}: **{kava}** (Chýba nasáčkovať {vaha_potrebna_chýba:.2f} kg)", expanded=not je_vsetko_kava_hotovo):
                if not je_vsetko_kava_hotovo:
                    if mame_dost: st.success("✅ Dózy sú plné, môžeš začať baliť.")
                    else: st.error(f"⚠️ Pražiar musí ešte dorobiť kávu!{chyba_text}")
                
                # Zobrazenie jednotlivých gramáží pre túto kávu
                for p in polozky_pre_kavu:
                    chýba_ks = max(0, p['ciel'] - p['hotovo'])
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if chýba_ks <= 0:
                            st.markdown(f"✅ **{p['gramaz']}g** sáčok - Vyrobených {p['hotovo']} / {p['ciel']} ks")
                        else:
                            st.markdown(f"➡️ **{p['gramaz']}g** sáčok - Už vyrobené {p['hotovo']} ks (Chýba dorobiť **{chýba_ks} ks**)")
                    with col2:
                        if chýba_ks > 0:
                            def pridaj_sacky(k=p['kava'], g=p['gramaz']):
                                pridavam = st.session_state[f"add_bag_{k}_{g}"]
                                if pridavam > 0:
                                    # Rozdistribuuje vyrobené kusy naprieč objednávkami
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
                                    auto_uloz()
                                st.session_state[f"add_bag_{k}_{g}"] = 0 # reset input
                                
                            st.number_input("Odložené do regálu (ks):", min_value=0, value=0, step=1, key=f"add_bag_{p['kava']}_{p['gramaz']}", on_change=pridaj_sacky)

# ========================================================
# TAB 4: SKLAD
# ========================================================
with tab4:
    st.markdown("### Aktuálny stav Skladu")
    
    col_dozy, col_sacky = st.columns(2)
    
    with col_dozy:
        st.markdown("#### 🛢️ Fyzické Dózy (kg)")
        st.caption("Vypražená káva, ktorá ešte nie je v sáčkoch.")
        if not stav_doz: st.info("Prázdne.")
        else:
            for zrno, vaha in stav_doz.items():
                st.metric(label=zrno, value=f"{vaha:.2f} kg", delta_color="normal" if vaha>=0 else "inverse")
                
    with col_sacky:
        st.markdown("#### 🛍️ Regál so sáčkami (ks)")
        st.caption("Hotové sáčky čakajúce na Kuriéra (Expedíciu).")
        if not regal_obalov: st.info("Regál je prázdny.")
        else:
            for kluc, ks in regal_obalov.items():
                if ks > 0:
                    kava, gramaz = kluc.split('_')
                    st.markdown(f"**{kava} ({gramaz}g):** {ks} ks")

# ========================================================
# TAB 5: EXPEDÍCIA (LOGISTIKA)
# ========================================================
with tab5:
    st.markdown("### Expedícia (Kuriér)")
    st.caption("Odoslanie hotových sáčkov zákazníkovi. Odkliknutím sa zníži stav v 'Regáli so sáčkami'.")
    
    aktivne = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True and not o.get('Sudy', False)]
    cakajuce_expedicia = [o for o in aktivne if not o.get('Potvrdene')]
    hotove_expedicia = [o for o in aktivne if o.get('Potvrdene')]
    
    if not cakajuce_expedicia:
        st.success("Všetky zákazky sú expedované.")
    else:
        odberatelia = sorted(list(set([o['Odberateľ'] for o in cakajuce_expedicia])))
        
        for odb in odberatelia:
            obj_pre_odb = [o for o in cakajuce_expedicia if o['Odberateľ'] == odb]
            celkovo_ks = sum([o['Kusy'] for o in obj_pre_odb])
            
            # Kontrola s regálom sáčkov
            mame_vsetky_sacky = True
            chyba_sacky = ""
            for o in obj_pre_odb:
                kluc = f"{o['Káva']}_{o['Gramáž']}"
                dostupne_v_regali = regal_obalov.get(kluc, 0)
                # Kuriér potrebuje VŠETKY kusy pre túto objednávku, inak nemôže poslať balík
                if dostupne_v_regali < o['Kusy']:
                    mame_vsetky_sacky = False
                    chyba_sacky += f" Chýba {o['Kusy'] - dostupne_v_regali}ks {o['Káva']} {o['Gramáž']}g."

            with st.expander(f"📦 **{odb}** (Zostáva odoslať: {celkovo_ks} ks)"):
                if mame_vsetky_sacky:
                    st.success("✅ Všetky sáčky sú pripravené v regáli. Môžeš odoslať.")
                    if st.button(f"Expedovať všetko pre: {odb}", key=f"exp_{odb}", type="primary"):
                        for i, o in enumerate(st.session_state.aktualne_objednavky):
                            if o.get('Odberateľ') == odb and not o.get('Potvrdene') and not o.get('❌ Zmazať'):
                                st.session_state.aktualne_objednavky[i]['Potvrdene'] = True
                        auto_uloz()
                        st.rerun()
                else:
                    st.error(f"⚠️ Zákazník sa nedá odoslať, čakáme na Výrobu!{chyba_sacky}")
                    
                st.markdown("**Detail balíka:**")
                for o in obj_pre_odb:
                    st.markdown(f"- {o['Kusy']}x **{o['Káva']}** ({o['Gramáž']}g)")

    if hotove_expedicia:
        st.divider()
        with st.expander("🚚 Odoslané zásielky (Archív)"):
            for i, o in enumerate(st.session_state.aktualne_objednavky):
                if o.get('Potvrdene') and not o.get('❌ Zmazať'):
                    st.markdown(f"✅ {o['Odberateľ']} | {o['Káva']} {o['Gramáž']}g ({o['Kusy']} ks)")

# ========================================================
# TAB 6: ÚČTOVNÍCTVO
# ========================================================
with tab6:
    st.markdown("### Generovanie exportov pre KROS Omega")
    st.info("Pripravuje sa...")

# ========================================================
# NÚDZOVÝ SERVISNÝ PANEL (ZAMKNUTÝ HESLOM)
# ========================================================
st.divider()
with st.expander("🛠️ Servisný panel (Oprava Google Disku)"):
    st.warning("Ak ti systém hlási chybu 'Drive storage quota has been exceeded', panel vymaže staré testovacie súbory.")
    heslo_servis = st.text_input("Zadaj heslo pre odomknutie panela:", type="password")
    if heslo_servis == "kikiriki":
        if st.button("🚨 Vymazať staré súbory robota a uvoľniť pamäť", type="primary"):
            uspech, sprava = vycisti_disk_robota()
            if uspech: st.success(f"Hotovo! Zmazaných súborov: {sprava}. Pamäť je uvoľnená, môžeš normálne pokračovať.")
            else: st.error(f"Chyba pri mazaní: {sprava}")
    elif heslo_servis != "":
        st.error("Nesprávne heslo.")
