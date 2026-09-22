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
            st.warning("Záloha na Google Drive je zatiaľ prázdna.")

    with col_save:
        if st.button("💾 Uložiť aktuálny zoznam pre ostatných", type="primary", use_container_width=True):
            if st.session_state.aktualne_objednavky:
                auto_uloz()
                cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                aktivne = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
                st.session_state.info_cloud = f"☁️ **Stav na Google Disku:** {len(aktivne)} aktívnych položiek | 🕒 Posledná úprava: **{cas_ulozenia}**"
                st.session_state.zaloha_data = aktivne
                st.success("✅ Tvoj aktuálny zoznam bol bezpečne uložený do spoločnej pamäte!")
                st.rerun()
            else:
                if uloz_do_google_sheets([], st.session_state.nazov_prazenia):
                    cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                    st.session_state.info_cloud = f"☁️ **Stav na Google Disku:** Prázdny stôl | 🕒 Posledná úprava: **{cas_ulozenia}**"
                    st.session_state.zaloha_data = []
                    st.success("✅ Spoločná pamäť bola úspešne vymazaná (pripravené na nový týždeň).")
                    st.rerun()

    st.divider()

    st.subheader("📁 Import z Excelu")
    nahraty_subor = st.file_uploader("Nahraj .xlsx súbor", type=["xlsx"])
    if nahraty_subor is not None:
        try:
            xl = pd.ExcelFile(nahraty_subor)
            df_import = xl.parse('Spracovane_Objednavky') if 'Spracovane_Objednavky' in xl.sheet_names else xl.parse(0)
            if st.button("📥 Načítať dáta z tohto Excelu"):
                for index, row in df_import.iterrows():
                    kusy_zaklad = int(row.get("Kusy", 0))
                    zabalene_hist = int(row.get("Zabalené (ks)", kusy_zaklad)) 
                    potvrdene_hist = bool(row.get("Potvrdene", False))
                    st.session_state.aktualne_objednavky.append({
                        "Odberateľ": str(row.get("Odberateľ", "Neznámy")),
                        "Káva": str(row.get("Káva", "")),
                        "Gramáž": int(row.get("Gramáž", 0)),
                        "Kusy": kusy_zaklad,
                        "Zabalené (ks)": zabalene_hist,
                        "Potvrdene": potvrdene_hist,
                        "❌ Zmazať": False
                    })
                auto_uloz()
                st.success("Dáta importované a uložené do cloudu!")
        except Exception as e:
            st.error("Chyba Excelu.")

    st.divider()

    st.subheader("1. Manuálne pridanie objednávky")
    col1, col2 = st.columns(2)
    with col1:
        meno = st.text_input("Odberateľ:", placeholder="Meno")
        rezim = st.radio("Režim zadávania:", ["Podľa kávy", "Podľa gramáže"], horizontal=True, on_change=vynuluj_policka)

    if rezim == "Podľa kávy":
        with col1:
            kava = st.selectbox("Káva:", list(kavy_recepty.keys()), on_change=vynuluj_policka)
        with col2:
            kusy_220 = st.number_input("220g (ks):", min_value=0, step=1, key=f"k_220_{st.session_state.form_key}")
            kusy_500 = st.number_input("500g (ks):", min_value=0, step=1, key=f"k_500_{st.session_state.form_key}")
            kusy_1000 = st.number_input("1000g (ks):", min_value=0, step=1, key=f"k_1000_{st.session_state.form_key}")

        if st.button("➕ Pridať do zoznamu", type="secondary"):
            if kusy_220 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 220, "Kusy": kusy_220, "Zabalené (ks)": kusy_220, "Potvrdene": False, "❌ Zmazať": False})
            if kusy_500 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 500, "Kusy": kusy_500, "Zabalené (ks)": kusy_500, "Potvrdene": False, "❌ Zmazať": False})
            if kusy_1000 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 1000, "Kusy": kusy_1000, "Zabalené (ks)": kusy_1000, "Potvrdene": False, "❌ Zmazať": False})
            auto_uloz()
            vynuluj_policka()
            st.rerun()
    else:
        with col1:
            gramaz = st.selectbox("Gramáž:", gramaze_list, on_change=vynuluj_policka)
        with col2:
            inputs_kavy = {}
            for k in kavy_recepty.keys():
                inputs_kavy[k] = st.number_input(f"{k} (ks):", min_value=0, step=1, key=f"k_{k}_{st.session_state.form_key}")

        if st.button("➕ Pridať do zoznamu", type="secondary"):
            for k, v in inputs_kavy.items():
                if v > 0:
                    st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": k, "Gramáž": gramaz, "Kusy": v, "Zabalené (ks)": v, "Potvrdene": False, "❌ Zmazať": False})
            auto_uloz()
            vynuluj_policka()
            st.rerun()

    st.divider()

    col_zoznam, col_vypocet = st.columns([2, 3])
    with col_zoznam:
        st.subheader("🛒 Aktuálne objednávky")
        if st.session_state.aktualne_objednavky:
            df_objednavky_vstup = pd.DataFrame(st.session_state.aktualne_objednavky)
            upravene_df = st.data_editor(df_objednavky_vstup, use_container_width=True, num_rows="fixed", hide_index=False, key="tabulka_objednavok")
            
            novy_stav = upravene_df.to_dict('records')
            if novy_stav != st.session_state.aktualne_objednavky:
                st.session_state.aktualne_objednavky = novy_stav
                auto_uloz()

            col_del1, col_del2 = st.columns(2)
            with col_del1:
                if st.button("🗑️ Odstrániť zaškrtnuté", type="primary"):
                    st.session_state.aktualne_objednavky = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
                    auto_uloz()
                    st.rerun()
            with col_del2:
                if st.button("💣 Vymazať všetko", type="primary"):
                    st.session_state.aktualne_objednavky = []
                    auto_uloz()
                    st.rerun()
        else:
            st.info("Zoznam je zatiaľ prázdny.")

    with col_vypocet:
        st.subheader("Plán praženia")
        if st.button("🚀 VYPOČÍTAŤ PLÁN A STIAHNUŤ", type="primary", use_container_width=True):
            if not st.session_state.aktualne_objednavky:
                st.warning("Prázdne! Najprv pridaj nejaké objednávky.")
            else:
                aktivne_objednavky = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
                df_objednavky_export = pd.DataFrame(aktivne_objednavky)
                
                potreba_zelenej_podla_zrna = {}
                potreba_uprazenej_podla_zrna = {}
                potreba_skladania_blendov = {}
                
                for o in aktivne_objednavky:
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
                    finalny_plan.append({"Zelené zrno": zrno, "Potrebné upražiť (kg)": round(uprazena_potreba, 2), "Dávky (á 5kg)": davky, "Navážiť zelenú (kg)": skutocna_zelena, "Zostatok (kg upraž.)": round(zostatok_uprazena, 2)})
                
                df_plan = pd.DataFrame(finalny_plan)
                st.dataframe(df_plan, use_container_width=True, hide_index=True)
                st.markdown(f"### 🔥 Celkový počet pražení: **{int(df_plan['Dávky (á 5kg)'].sum())} dávok**")
                
                finalny_plan_blendov = []
                for meno_blendu, celkova_vaha_blendu in potreba_skladania_blendov.items():
                    recept = kavy_recepty[meno_blendu]["recept"]
                    for zrno, podiel in recept.items():
                        finalny_plan_blendov.append({"Názov blendu": meno_blendu, "Celková hmotnosť (kg)": round(celkova_vaha_blendu, 2), "Kávová zložka": zrno, "Podiel v blende": f"{int(podiel * 100)}%", "Hmotnosť zložky (kg)": round(celkova_vaha_blendu * podiel, 2)})
                
                df_blendov = pd.DataFrame(finalny_plan_blendov) if finalny_plan_blendov else pd.DataFrame()
                
                # Celkový sumár obalov (pre Excel)
                df_sum_obalov = df_objednavky_export.groupby(['Káva', 'Gramáž'])['Kusy'].sum().reset_index()
                sum_pivot_ex = df_sum_obalov.pivot(index='Káva', columns='Gramáž', values='Kusy').fillna(0).astype(int)
                for g in [220, 500, 1000]:
                    if g not in sum_pivot_ex.columns: sum_pivot_ex[g] = 0
                sum_pivot_ex['Spolu etikiet'] = sum_pivot_ex.sum(axis=1)
                sum_pivot_ex.loc['🔥 SPOLU SÁČKOV'] = sum_pivot_ex.sum(numeric_only=True)
                sum_pivot_ex = sum_pivot_ex[['Spolu etikiet', 220, 500, 1000]].reset_index()
                sum_pivot_ex.rename(columns={'index': 'Káva', 220: '220g', 500: '500g', 1000: '1000g'}, inplace=True) 

                # --- EXCEL PROFI FORMÁTOVANIE ---
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    
                    def write_styled_sheet(df, sheet_name, group_by_col=None):
                        worksheet = workbook.add_worksheet(sheet_name)
                        max_row, max_col = df.shape
                        if max_row == 0: return

                        worksheet.autofilter(0, 0, max_row, max_col - 1)
                        
                        header_format = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1})
                        for col_num, value in enumerate(df.columns):
                            worksheet.write(0, col_num, str(value), header_format)
                            max_len = max(df[df.columns[col_num]].astype(str).map(len).max(), len(str(value))) + 2
                            worksheet.set_column(col_num, col_num, max_len)
                            
                        format_z1 = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1})
                        format_z2 = workbook.add_format({'bg_color': '#F2F2F2', 'border': 1}) 
                        format_total = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1}) 
                        
                        if group_by_col and group_by_col in df.columns:
                            group_col_idx = list(df.columns).index(group_by_col)
                            format_b1 = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1})
                            format_b2 = workbook.add_format({'bg_color': '#DCE6F1', 'border': 1}) 
                            use_f1 = True
                            current_val = None
                            for r_idx in range(max_row):
                                val = df.iloc[r_idx, group_col_idx]
                                is_total = str(df.iloc[r_idx, 0]).startswith('🔥')
                                
                                if current_val is None: current_val = val
                                elif val != current_val:
                                    current_val = val
                                    use_f1 = not use_f1
                                
                                fmt = format_total if is_total else (format_b1 if use_f1 else format_b2)
                                for c_idx in range(max_col):
                                    cell_val = df.iloc[r_idx, c_idx]
                                    if pd.isna(cell_val): worksheet.write(r_idx + 1, c_idx, "", fmt)
                                    else:
                                        if isinstance(cell_val, (int, float)): worksheet.write_number(r_idx + 1, c_idx, cell_val, fmt)
                                        else: worksheet.write(r_idx + 1, c_idx, str(cell_val), fmt)
                        else:
                            for r_idx in range(max_row):
                                is_total = str(df.iloc[r_idx, 0]).startswith('🔥')
                                fmt = format_total if is_total else (format_z1 if r_idx % 2 == 0 else format_z2)
                                for c_idx in range(max_col):
                                    cell_val = df.iloc[r_idx, c_idx]
                                    if pd.isna(cell_val): worksheet.write(r_idx + 1, c_idx, "", fmt)
                                    else:
                                        if isinstance(cell_val, (int, float)): worksheet.write_number(r_idx + 1, c_idx, cell_val, fmt)
                                        else: worksheet.write(r_idx + 1, c_idx, str(cell_val), fmt)

                    write_styled_sheet(df_plan, 'Plan_Prazenia')
                    write_styled_sheet(df_objednavky_export.drop(columns=['❌ Zmazať'], errors='ignore'), 'Spracovane_Objednavky')
                    if not df_blendov.empty: 
                        write_styled_sheet(df_blendov, 'Plan_Blendov', group_by_col='Názov blendu')
                    write_styled_sheet(sum_pivot_ex, 'Sumar_Obalov')

                nazov_suboru = f"KIKIRIKI_plan_{st.session_state.nazov_prazenia}.xlsx"
                st.download_button(
                    label="💾 Stiahnuť profi 3-hárok (s Filtrami a Farbami)", data=buffer.getvalue(), file_name=nazov_suboru,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary"
                )

# ========================================================
# TAB 2: KONTROLA BALENIA A EXPORT
# ========================================================
with tab2:
    st.subheader("☁️ Záchranná brzda pre synchronizáciu")
    col_l, col_s = st.columns(2)
    with col_l:
        st.button("🔄 Znovu načítať dáta z Disku (Napríklad na inom PC)", type="primary", use_container_width=True, on_click=nacitaj_vsetko_z_cloudu_callback)
    with col_s:
        if st.button("💾 Uložiť aktuálny stav do Cloudu", type="primary", use_container_width=True):
            auto_uloz()
            st.toast("Uložené!", icon="✅")

    st.divider()

    if st.session_state.aktualne_objednavky:
        aktivne_balenie = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
        
        # --- ROZBALENIE FILTROV PRE BALENIE ---
        st.markdown("### 📱 Filtre pre Sklad a Balenie")
        col_f1, col_f2 = st.columns(2)
        zoznam_odberatelov = ["Všetci"] + sorted(list(set([o['Odberateľ'] for o in aktivne_balenie])))
        zoznam_kav = ["Všetky"] + sorted(list(set([o['Káva'] for o in aktivne_balenie])))
        
        with col_f1: filter_odb = st.selectbox("Filtrovať Odberateľa:", zoznam_odberatelov)
        with col_f2: filter_kava = st.selectbox("Filtrovať Kávu:", zoznam_kav)

        df_filtered = pd.DataFrame([o for o in aktivne_balenie if (filter_odb == "Všetci" or o['Odberateľ'] == filter_odb) and (filter_kava == "Všetky" or o['Káva'] == filter_kava)])

        # --- SUMÁR OBALOV (OBROVSKÝ BOLD TEXT + STATICKÁ TABUĽKA) ---
        if not df_filtered.empty:
            total_220 = df_filtered[df_filtered['Gramáž']==220]['Kusy'].sum() if 220 in df_filtered['Gramáž'].values else 0
            total_500 = df_filtered[df_filtered['Gramáž']==500]['Kusy'].sum() if 500 in df_filtered['Gramáž'].values else 0
            total_1000 = df_filtered[df_filtered['Gramáž']==1000]['Kusy'].sum() if 1000 in df_filtered['Gramáž'].values else 0
            total_all = total_220 + total_500 + total_1000

            st.markdown(f"## 🔥 **CELKOVO POTREBUJEŠ: {total_all} sáčkov**")
            st.markdown(f"### **Z toho: 220g: {total_220} ks | 500g: {total_500} ks | 1000g: {total_1000} ks**")

            df_sum = df_filtered.groupby(['Káva', 'Gramáž'])['Kusy'].sum().reset_index()
            sum_pivot = df_sum.pivot(index='Káva', columns='Gramáž', values='Kusy').fillna(0).astype(int)
            for g in [220, 500, 1000]:
                if g not in sum_pivot.columns: sum_pivot[g] = 0
            sum_pivot['Spolu etikiet'] = sum_pivot.sum(axis=1)
            
            sum_pivot.loc['🔥 SPOLU SÁČKOV'] = sum_pivot.sum(numeric_only=True)
            sum_pivot = sum_pivot[['Spolu etikiet', 220, 500, 1000]].reset_index()
            
            # Premenovanie stĺpcov pre krajšie zobrazenie
            sum_pivot.rename(columns={'index': 'Káva', 220: '220g', 500: '500g', 1000: '1000g'}, inplace=True)
            
            # Statická tabuľka = nedá sa do nej klikať = súčet je dole napevno
            st.table(sum_pivot)
        else:
            st.warning("Pre tento filter neexistujú žiadne sáčky na balenie.")

        st.divider()

        # --- SKLAD EXPANDER ---
        with st.expander("➕ Zvýšila ti káva pri pražení? Pridať položku do tabuľky (napr. pre Sklad)"):
            col_ex1, col_ex2, col_ex3 = st.columns(3)
            with col_ex1: ex_odberatel = st.text_input("Odberateľ:", value="Sklad", key="ex_odb")
            with col_ex2: ex_kava = st.selectbox("Káva:", list(kavy_recepty.keys()), key="ex_kava")
            with col_ex3:
                ex_gramaz = st.selectbox("Gramáž:", gramaze_list, key="ex_gramaz")
                ex_kusy = st.number_input("Kusy:", min_value=1, step=1, key="ex_kusy")
            
            if st.button("Pridať položku navyše do zoznamu", type="secondary"):
                st.session_state.aktualne_objednavky.append({
                    "Odberateľ": ex_odberatel,
                    "Káva": ex_kava,
                    "Gramáž": ex_gramaz,
                    "Kusy": ex_kusy,
                    "Zabalené (ks)": ex_kusy,
                    "Potvrdene": True,
                    "❌ Zmazať": False
                })
                auto_uloz()
                st.success(f"Pridané {ex_kusy}ks {ex_kava} ({ex_gramaz}g) pre {ex_odberatel}.")
                st.rerun()

        st.divider()

        # --- SAMOTNÁ KONTROLA BALENIA ---
        st.markdown("### Odškrtávanie sáčkov")

        def zmena_balenia_callback(index_v_liste):
            novy_pocet = st.session_state[f"pocet_{index_v_liste}"]
            potvrdene = st.session_state[f"chk_{index_v_liste}"]
            st.session_state.aktualne_objednavky[index_v_liste]['Zabalené (ks)'] = novy_pocet
            st.session_state.aktualne_objednavky[index_v_liste]['Potvrdene'] = potvrdene
            auto_uloz() 

        st.info("Karta zasvieti nazeleno až vtedy, keď odškrtneš balenie. Všetko sa okamžite a samo ukladá do Google Disku.")

        for i, obj in enumerate(st.session_state.aktualne_objednavky):
            if obj.get('❌ Zmazať', False): continue
                
            zhoda_odb = (filter_odb == "Všetci" or obj['Odberateľ'] == filter_odb)
            zhoda_kava = (filter_kava == "Všetky" or obj['Káva'] == filter_kava)
            
            if zhoda_odb and zhoda_kava:
                with st.container():
                    aktualne_zabalene = int(obj.get('Zabalené (ks)', obj['Kusy']))
                    objednane = int(obj['Kusy'])
                    potvrdene = obj.get('Potvrdene', False)
                    
                    if not potvrdene:
                        st.markdown(f"#### 📦 **{obj['Odberateľ']}** | {obj['Káva']} ({obj['Gramáž']}g)")
                    elif aktualne_zabalene == objednane:
                        st.markdown(f"#### ✅ :green[**{obj['Odberateľ']}** | {obj['Káva']} ({obj['Gramáž']}g)]")
                    else:
                        st.markdown(f"#### ⚠️ :orange[**{obj['Odberateľ']}** | {obj['Káva']} ({obj['Gramáž']}g)]")
                        
                    st.write(f"*Objednané:* **{objednane} ks**")
                    
                    st.number_input("Skutočne zabalené:", min_value=0, value=aktualne_zabalene, step=1, key=f"pocet_{i}", on_change=zmena_balenia_callback, args=(i,))
                    st.checkbox("Potvrdiť balenie", value=potvrdene, key=f"chk_{i}", on_change=zmena_balenia_callback, args=(i,))
                    st.markdown("---") 

        # --- EXPORT PRE EVIČKU ---
        st.markdown("### 📤 Finálny Export pre účtovníctvo")
        
        sumar_vsetky = pd.DataFrame(aktivne_balenie)
        if not sumar_vsetky.empty:
            vybrany_export_odberatel = st.selectbox("Filtrovať export do Omegy (pre Evičku):", zoznam_odberatelov)
            
            @st.cache_data
            def get_cennik(): return pd.read_excel("Kalkulacia stefi posledna prazenie 7.9.2026..xlsx", sheet_name='Cenník kávy', skiprows=4)
            
            try:
                df_cennik = get_cennik()
                df_vypocet = sumar_vsetky[(sumar_vsetky['Zabalené (ks)'] > 0) & (sumar_vsetky['Potvrdene'] == True)].copy()
                
                if vybrany_export_odberatel != "Všetci":
                    df_vypocet = df_vypocet[df_vypocet['Odberateľ'] == vybrany_export_odberatel]
                    
                preklad_cennik = {"Brazília": "Brazília – Donas do Café", "Etiopia Yerg.": "Etiópia – Yirgacheffe", "Etiopia BG": "Etiópia – Banko Gotiti", "Honduras": "Honduras – SHG EP San Andrés", "Columbia": "Kolumbia – Huila condor", "Indonezia": "Indinezia", "India": "India Plantation AA", "Aranka": "Aranka", "Frištuk": "Frištuk", "K52%": "K52% / Cucflek", "Cucflek": "K52% / Cucflek", "Peru": "Peru", "Rwanda": "Rwanda"}
                preklad_faktura = {"Brazília": "Brazília – Donas do Café", "Etiopia Yerg.": "Etiópia – Yirgacheffe", "Etiopia BG": "Etiópia – Banko Gotiti", "Honduras": "Honduras – SHG EP San Andrés", "Columbia": "Kolumbia – Huila condor", "Indonezia": "Indonézia", "India": "India Plantation AA", "Aranka": "Aranka", "Frištuk": "Frištuk", "K52%": "Kopaničiarska 52%", "Cucflek": "Cucflek", "Peru": "Peru", "Rwanda": "Rwanda"}
                
                if not df_vypocet.empty:
                    df_vypocet['Hladat_v_cenniku'] = df_vypocet['Káva'].map(preklad_cennik).fillna(df_vypocet['Káva'])
                    df_vypocet['Produkt_Faktura'] = df_vypocet['Káva'].map(preklad_faktura).fillna(df_vypocet['Káva'])
                    df_vypocet.rename(columns={'Zabalené (ks)': 'Množstvo (ks)'}, inplace=True)
                    df_vypocet['Gramaz_text'] = df_vypocet['Gramáž'].apply(lambda x: "1 000 g" if x == 1000 else f"{x} g")
                    
                    df_export = pd.merge(df_vypocet, df_cennik, left_on=['Hladat_v_cenniku', 'Gramaz_text'], right_on=['Produkt', 'Gramáž'], how='left')
                    df_export['Cena pre obchodníka (€)'] = df_export['Cena pre obchodníka (€)'].fillna(0).round(2)
                    df_export['Produkt'] = df_export['Produkt_Faktura']
                    df_export['Gramáž'] = df_export['Gramaz_text']
                    df_export = df_export[['Odberateľ', 'Produkt', 'Gramáž', 'Množstvo (ks)', 'Cena pre obchodníka (€)']]
                    df_export.rename(columns={'Cena pre obchodníka (€)': 'Jednotková cena (€)'}, inplace=True)
                    df_export['Celková suma (€)'] = (df_export['Množstvo (ks)'] * df_export['Jednotková cena (€)']).round(2)
                    
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        workbook = writer.book
                        worksheet = workbook.add_worksheet('Prehľad pre Evičku')
                        max_row, max_col = df_export.shape
                        if max_row > 0:
                            worksheet.autofilter(0, 0, max_row, max_col - 1)
                            header_format = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1})
                            for col_num, value in enumerate(df_export.columns):
                                worksheet.write(0, col_num, str(value), header_format)
                                max_len = max(df_export[df_export.columns[col_num]].astype(str).map(len).max(), len(str(value))) + 2
                                worksheet.set_column(col_num, col_num, max_len)
                            
                            format_z1 = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1})
                            format_z2 = workbook.add_format({'bg_color': '#F2F2F2', 'border': 1}) 
                            for r_idx in range(max_row):
                                fmt = format_z1 if r_idx % 2 == 0 else format_z2
                                for c_idx in range(max_col):
                                    cell_val = df_export.iloc[r_idx, c_idx]
                                    if pd.isna(cell_val): worksheet.write(r_idx + 1, c_idx, "", fmt)
                                    else:
                                        if isinstance(cell_val, (int, float)): worksheet.write_number(r_idx + 1, c_idx, cell_val, fmt)
                                        else: worksheet.write(r_idx + 1, c_idx, str(cell_val), fmt)

                    excel_data = excel_buffer.getvalue()

                    lines = ["R00\tT01"]
                    invoice_counter = 1
                    today_str = datetime.now().strftime("%d.%m.%Y")
                    due_str = (datetime.now() + timedelta(days=14)).strftime("%d.%m.%Y")
                    for odberatel, group in df_export.groupby('Odberateľ'):
                        cislo_dokladu = f"EXP{datetime.now().strftime('%Y%m%d')}{invoice_counter:02d}"
                        suma_celkom = group['Celková suma (€)'].sum()
                        lines.append("\t".join(["R01", cislo_dokladu, str(odberatel), "", today_str, due_str, today_str, "0.00", f"{suma_celkom:.2f}", "", "", "", "", "", "", "", "", "11"]))
                        for _, row in group.iterrows():
                            lines.append("\t".join(["R02", f"{row['Produkt']} {row['Gramáž']}", str(row['Množstvo (ks)']), "ks", f"{row['Jednotková cena (€)']:.2f}", "V", "0.00", f"{row['Jednotková cena (€)']:.2f}", "0", "V"]))
                        invoice_counter += 1
                    
                    raw_txt_string = "\n".join(lines)
                    txt_data = raw_txt_string.encode('windows-1250', errors='replace')
                    
                    meno_do_suboru = "Vsetci" if vybrany_export_odberatel == "Všetci" else vybrany_export_odberatel.replace(" ", "_")
                    nazov_excelu = f"Kikiriki_Prehlad_Evicka_{meno_do_suboru}_{st.session_state.nazov_prazenia}.xlsx"
                    nazov_txt = f"Kikiriki_Import_Omega_{meno_do_suboru}_{st.session_state.nazov_prazenia}.txt"
                    
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.download_button("📊 Stiahnuť profi Excel pre Evičku", data=excel_data, file_name=nazov_excelu, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
                    with col_dl2:
                        st.download_button(
                            label="⚙️ Stiahnuť TXT pre Kros + ☁️ Uložiť pre Evičku", 
                            data=txt_data, file_name=nazov_txt, mime="text/plain", 
                            on_click=uloz_export_pre_evicku, args=(vybrany_export_odberatel, raw_txt_string),
                            type="primary"
                        )
                else:
                    st.warning("Pre tohto odberateľa nie sú potvrdené žiadne zabalené kusy.")
            except Exception as e:
                st.error("Chyba pri generovaní exportu.")
    else:
        st.info("Zoznam je prázdny. Pridaj objednávky v záložke 1.")
