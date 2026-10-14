import streamlit as st
import pandas as pd
import math
import io
from datetime import datetime, timedelta
import json

st.set_page_config(page_title="Roastery Manager PRO v5.2", page_icon="🏭", layout="wide")

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
        st.session_state.info_cloud = f"☁️ **Stav na Google Disku:** {len(aktivne)} aktívnych položiek | 🕒 Posledná úprava: **{cas_poslednej_upravy}**"
        st.session_state.msg_uspech = True
    else:
        st.session_state.info_cloud = "☁️ **Stav na Google Disku:** Prázdny stôl (žiadne aktívne objednávky)."
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
    st.session_state.info_cloud = f"☁️ **Stav na Google Disku:** {len(aktivne_start)} aktívnych položiek | 🕒 Posledná úprava: **{cas}**"

if 'nazov_prazenia' not in st.session_state:
    st.session_state.nazov_prazenia = st.session_state.get('pociatocny_nazov', f"Prazenie_PRO_{DNESNY_DATUM}")

if 'form_key' not in st.session_state: st.session_state.form_key = 0
def vynuluj_policka(): st.session_state.form_key += 1

# --- HLAVNÉ ROZHRANIE ---
st.title("🏭 Roastery Manager PRO (v5.2)")
st.info("⚠️ Toto je nová paralelná vývojová verzia (Rýchle odklikávanie v pražiarni). Beží na samostatnej databáze.")

st.text_input("📅 Názov aktuálneho praženia:", key="nazov_prazenia", on_change=auto_uloz)

tab1, tab2, tab3, tab4 = st.tabs(["📝 1. Kancelária (Objednávky)", "🔥 2. Pražiareň (Stroj)", "📦 3. Baliareň a Dózy", "📊 4. Účtovníctvo"])

# ========================================================
# TAB 1: OBJEDNÁVKY A PLÁN PRAŽENIA
# ========================================================
with tab1:
    st.info(st.session_state.info_cloud)

    if st.session_state.get('aktualne_objednavky'):
        with st.expander("👀 Klikni sem pre zobrazenie toho, čo je aktuálne uložené na Disku"):
            df_ukazka = pd.DataFrame([o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)])
            if not df_ukazka.empty:
                st.dataframe(df_ukazka[['Odberateľ', 'Káva', 'Gramáž', 'Kusy']], use_container_width=True, hide_index=True)

    st.subheader("☁️ Spoločná zdieľaná pamäť")
    if st.session_state.pop('msg_uspech', False):
        st.success("✅ Dáta úspešne načítané!")
    if st.session_state.pop('msg_chyba', False):
        st.warning("Záloha na Google Drive je zatiaľ prázdna.")

    col_load, col_save = st.columns(2)
    with col_load:
        st.button("🔄 Načítať prácu z Google disku", type="primary", use_container_width=True, on_click=nacitaj_vsetko_z_cloudu_callback)

    with col_save:
        if st.button("💾 Uložiť aktuálny zoznam do Cloudu", type="primary", use_container_width=True):
            auto_uloz()
            cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            aktivne = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
            st.session_state.info_cloud = f"☁️ **Stav na Google Disku:** {len(aktivne)} aktívnych položiek | 🕒 Posledná úprava: **{cas_ulozenia}**"
            st.success("✅ Tvoj aktuálny zoznam a priebeh praženia bol uložený!")
            st.rerun()

    st.divider()

    st.markdown("### 📁 Import z Excelu")
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
                st.success("Dáta importované a uložené do cloudu!")
                st.rerun()
        except Exception as e:
            st.error("Chyba Excelu.")

    st.divider()

    st.subheader("1. Manuálne pridanie objednávky")
    col1, col2 = st.columns(2)
    with col1:
        meno = st.text_input("Odberateľ:", placeholder="Meno")
        rezim = st.radio("Režim zadávania:", ["Podľa kávy", "Podľa gramáže", "🟢 Pridať celý BATCH (Sklad - Sud)"], horizontal=True, on_change=vynuluj_policka)

    if rezim == "Podľa kávy":
        with col1: kava = st.selectbox("Káva:", list(kavy_recepty.keys()), on_change=vynuluj_policka)
        with col2:
            kusy_220 = st.number_input("220g (ks):", min_value=0, step=1, key=f"k_220_{st.session_state.form_key}")
            kusy_500 = st.number_input("500g (ks):", min_value=0, step=1, key=f"k_500_{st.session_state.form_key}")
            kusy_1000 = st.number_input("1000g (ks):", min_value=0, step=1, key=f"k_1000_{st.session_state.form_key}")

        if st.button("➕ Pridať do zoznamu", type="secondary"):
            if kusy_220 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 220, "Kusy": kusy_220, "Zabalené (ks)": kusy_220, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            if kusy_500 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 500, "Kusy": kusy_500, "Zabalené (ks)": kusy_500, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            if kusy_1000 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 1000, "Kusy": kusy_1000, "Zabalené (ks)": kusy_1000, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            auto_uloz()
            vynuluj_policka()
            st.rerun()
            
    elif rezim == "Podľa gramáže":
        with col1: gramaz = st.selectbox("Gramáž:", gramaze_list, on_change=vynuluj_policka)
        with col2:
            inputs_kavy = {}
            for k in kavy_recepty.keys(): inputs_kavy[k] = st.number_input(f"{k} (ks):", min_value=0, step=1, key=f"k_{k}_{st.session_state.form_key}")
        if st.button("➕ Pridať do zoznamu", type="secondary"):
            for k, v in inputs_kavy.items():
                if v > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": k, "Gramáž": gramaz, "Kusy": v, "Zabalené (ks)": v, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            auto_uloz()
            vynuluj_policka()
            st.rerun()
            
    elif rezim == "🟢 Pridať celý BATCH (Sklad - Sud)":
        with st.container():
            st.success("🟢 Káva sa pripočíta do plánu praženia a pôjde do Dózy, ale nežiada etikety na balenie.")
            col_b1, col_b2 = st.columns(2)
            with col_b1: kava_batch = st.selectbox("Káva do pražičky:", list(kavy_recepty.keys()), key=f"kava_b_{st.session_state.form_key}")
            with col_b2: davky_batch = st.number_input("Počet celých dávok (á 5kg zelenej):", min_value=1, step=1, key=f"davky_b_{st.session_state.form_key}")
            if st.button("➕ Pridať BATCH do praženia", type="primary"):
                st.session_state.aktualne_objednavky.append({
                    "Odberateľ": "📦 SKLAD (Sudy)", "Káva": kava_batch, "Gramáž": 0, "Kusy": davky_batch, "Zabalené (ks)": 0, "Potvrdene": True, "Sudy": True, "❌ Zmazať": False
                })
                auto_uloz()
                vynuluj_policka()
                st.rerun()

    st.divider()

    col_zoznam, col_vypocet = st.columns([2, 3])
    
    with col_zoznam:
        st.subheader("🛒 Tvoja kniha objednávok")
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
                
            col_del1, col_del2, col_del3 = st.columns(3)
            with col_del1:
                if st.button("🗑️ Odstrániť zaškrtnuté", type="primary"):
                    st.session_state.aktualne_objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
                    auto_uloz()
                    st.rerun()
            with col_del3:
                if st.button("⚠️💣 VYMAZAŤ CELÝ VÍKEND", type="primary"):
                    st.session_state.aktualne_objednavky = []
                    st.session_state.priebeh_prazenia = {} 
                    auto_uloz()
                    st.rerun()
        else:
            st.info("Zatiaľ žiadne objednávky na tento víkend.")

    with col_vypocet:
        st.subheader("Plán praženia a EXCEL")
        if st.button("🚀 VYPOČÍTAŤ PLÁN A STIAHNUŤ", type="primary", use_container_width=True):
            if not st.session_state.aktualne_objednavky:
                st.warning("Prázdne! Najprv pridaj nejaké objednávky.")
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
                    finalny_plan.append({"Zelené zrno": zrno, "Potrebné upražiť (kg)": round(uprazena_potreba, 2), "Dávky (á 5kg)": davky, "Navážiť zelenú (kg)": skutocna_zelena, "Zostatok (kg upraž.)": round(zostatok_uprazena, 2)})
                
                df_plan = pd.DataFrame(finalny_plan)
                st.dataframe(df_plan, use_container_width=True, hide_index=True)
                
                celkovo_davok = int(df_plan['Dávky (á 5kg)'].sum())
                celkova_zelena = df_plan['Navážiť zelenú (kg)'].sum()
                celkova_uprazena = celkova_zelena * (1 - (STANDARDNY_VYPEK / 100.0))
                
                st.markdown(f"### 🔥 Celkový počet pražení: **{celkovo_davok} dávok**")
                st.markdown(f"### ⚖️ Spolu: **{celkova_zelena:.1f} kg** zelenej ➡️ **{celkova_uprazena:.1f} kg** upraženej (Plán)")
                
                total_row_plan = {"Zelené zrno": "🔥 SPOLU:", "Potrebné upražiť (kg)": round(celkova_uprazena, 2), "Dávky (á 5kg)": celkovo_davok, "Navážiť zelenú (kg)": round(celkova_zelena, 2), "Zostatok (kg upraž.)": ""}
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
                    sum_pivot_ex.loc['🔥 SPOLU SÁČKOV'] = sum_pivot_ex.sum(numeric_only=True)
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

                    write_styled_sheet(df_plan_excel, 'Plan_Prazenia')
                    write_styled_sheet(df_objednavky_export.drop(columns=['❌ Zmazať'], errors='ignore'), 'Spracovane_Objednavky')
                    if not df_blendov.empty: 
                        write_styled_sheet(df_blendov, 'Plan_Blendov', group_by_col='Názov blendu')
                    write_styled_sheet(sum_pivot_ex, 'Sumar_Obalov')

                nazov_suboru = f"KIKIRIKI_plan_PRO_{st.session_state.nazov_prazenia}.xlsx"
                st.download_button(
                    label="💾 Stiahnuť profi 3-hárok (s Filtrami a Farbami)", data=buffer.getvalue(), file_name=nazov_suboru,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary"
                )

# ========================================================
# TAB 2: PRAŽIAREŇ (Výroba)
# ========================================================
with tab2:
    st.header("🔥 Zoznam úloh pre Pražičku")
    st.write("Môžeš upražiť jedným klikom (Automat na 20%), alebo si manuálne zadať presné váhy a anomálie.")
    
    aktivne_objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
    potreba_zelenej_podla_zrna = {}
    potreba_uprazenej_podla_zrna = {}
    
    for o in aktivne_objednavky:
        je_sud = o.get("Sudy") == True
        if je_sud:
            zelena_kg_zaklad = o["Kusy"] * KAPACITA_ZELENA_BATCH
            uprazena_kg = zelena_kg_zaklad * (1 - (STANDARDNY_VYPEK / 100.0))
        else:
            uprazena_kg = (o["Kusy"] * o["Gramáž"] / 1000.0)
            zelena_kg_zaklad = uprazena_kg / (1 - (STANDARDNY_VYPEK / 100.0))
        
        if o["Káva"] in kavy_recepty:
            recept = kavy_recepty[o["Káva"]]["recept"]
            for zrno, podiel in recept.items():
                potreba_zelenej_podla_zrna[zrno] = potreba_zelenej_podla_zrna.get(zrno, 0) + (zelena_kg_zaklad * podiel)
                potreba_uprazenej_podla_zrna[zrno] = potreba_uprazenej_podla_zrna.get(zrno, 0) + (uprazena_kg * podiel)

    if not potreba_zelenej_podla_zrna:
        st.info("Zatiaľ nie je v pláne nič na praženie.")
    else:
        for zrno, teoreticka_vaha_zelena in potreba_zelenej_podla_zrna.items():
            davky_plan = math.ceil(teoreticka_vaha_zelena / KAPACITA_ZELENA_BATCH)
            zelena_plan = davky_plan * KAPACITA_ZELENA_BATCH
            uprazena_teoria = zelena_plan * (1 - (STANDARDNY_VYPEK / 100.0))
            
            stav = st.session_state.priebeh_prazenia.get(zrno, {"hotovo": False, "zelena_real": 0.0, "uprazena_real": 0.0})
            
            with st.expander(f"{'✅ Hotovo' if stav['hotovo'] else '⏳ Čaká:'} Zrnko: {zrno} (Plán: {davky_plan} dávok)", expanded=not stav['hotovo']):
                col_info, col_input = st.columns([1, 1])
                
                with col_info:
                    st.markdown("**Čo hovorí plán:**")
                    st.write(f"- Navážiť zelenú: **{zelena_plan:.1f} kg** ({davky_plan} batchov)")
                    st.write(f"- Očakávaný výstup (pri {STANDARDNY_VYPEK}% výpeku): **{uprazena_teoria:.2f} kg**")
                
                with col_input:
                    if not stav['hotovo']:
                        # Voliteľný manuálny režim
                        manual_mode = st.checkbox("⚖️ Zadať presnú váhu manuálne (anomálie)", key=f"manual_{zrno}")
                        
                        if not manual_mode:
                            st.info(f"Rýchly režim: Zaráta do dózy presne {uprazena_teoria:.1f} kg.")
                            if st.button(f"✅ Odpražiť {davky_plan} dávok (Automat {STANDARDNY_VYPEK}%)", key=f"auto_{zrno}", type="primary"):
                                st.session_state.priebeh_prazenia[zrno] = {
                                    "zelena_real": zelena_plan,
                                    "uprazena_real": uprazena_teoria,
                                    "hotovo": True
                                }
                                auto_uloz()
                                st.rerun()
                        else:
                            st.markdown("**Manuálne zadanie:**")
                            def update_priebeh(z=zrno):
                                z_real = st.session_state[f"z_real_{z}"]
                                u_real = st.session_state[f"u_real_{z}"]
                                hotovo = st.session_state[f"hotovo_{z}"]
                                st.session_state.priebeh_prazenia[z] = {"zelena_real": z_real, "uprazena_real": u_real, "hotovo": hotovo}
                                auto_uloz()
                            
                            st.number_input("Nasypaná zelená (kg):", value=float(stav["zelena_real"] or zelena_plan), step=0.1, key=f"z_real_{zrno}", on_change=update_priebeh)
                            st.number_input("Vysypaná upražená (kg):", value=float(stav["uprazena_real"]), step=0.1, key=f"u_real_{zrno}", on_change=update_priebeh)
                            
                            z_vaha = st.session_state[f"z_real_{zrno}"]
                            u_vaha = st.session_state[f"u_real_{zrno}"]
                            if z_vaha > 0 and u_vaha > 0:
                                vypek = (1 - (u_vaha / z_vaha)) * 100
                                st.caption(f"Výpek na tomto zrne: **{vypek:.1f}%**")
                                
                            st.checkbox("✅ Potvrdiť a poslať do Dózy", value=stav["hotovo"], key=f"hotovo_{zrno}", on_change=update_priebeh)
                    else:
                        st.success(f"🎉 **Úspešne odpražené!** \nMinutá zelená: {stav['zelena_real']} kg ➡️ V Dóze pribudlo: {stav['uprazena_real']} kg")
                        if st.button("🔄 Zrušiť (Vrátiť späť do pražiarne)", key=f"undo_{zrno}"):
                            st.session_state.priebeh_prazenia[zrno]["hotovo"] = False
                            auto_uloz()
                            st.rerun()

# ========================================================
# TAB 3: BALIAREŇ A DÓZY
# ========================================================
with tab3:
    st.header("📦 Zostatky v Dózach a Odškrtávanie sáčkov")
    
    stav_doz = {}
    for zrno, data in st.session_state.priebeh_prazenia.items():
        if data["hotovo"]:
            stav_doz[zrno] = stav_doz.get(zrno, 0.0) + data["uprazena_real"]
            
    aktivne_objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
    for o in aktivne_objednavky:
        if o.get("Potvrdene") == True and o.get("Sudy") != True:
            zabalena_vaha_kg = o["Zabalené (ks)"] * o["Gramáž"] / 1000.0
            if o["Káva"] in kavy_recepty:
                recept = kavy_recepty[o["Káva"]]["recept"]
                for zrno, podiel in recept.items():
                    if zrno in stav_doz:
                        stav_doz[zrno] -= (zabalena_vaha_kg * podiel)

    st.subheader("🛢️ Aktuálny fyzický stav (Čo by malo byť v bareloch)")
    if not stav_doz:
        st.info("Zatiaľ nemáš upražené a potvrdené žiadne zrno z Pražiarne.")
    else:
        dozy_cols = st.columns(len(stav_doz))
        for idx, (zrno, vaha) in enumerate(stav_doz.items()):
            with dozy_cols[idx % len(dozy_cols)]:
                farba = "green" if vaha >= 0 else "red"
                st.metric(label=zrno, value=f"{vaha:.2f} kg", delta="Na sklade" if vaha >= 0 else "Chýba!", delta_color="normal" if vaha>=0 else "inverse")

    st.divider()
    
    st.subheader("🏷️ Zoznam na balenie (Odoberá z dóz)")
    
    def zmena_balenia_pro_callback(index_v_liste):
        novy_pocet = st.session_state[f"pro_pocet_{index_v_liste}"]
        potvrdene = st.session_state[f"pro_chk_{index_v_liste}"]
        st.session_state.aktualne_objednavky[index_v_liste]['Zabalené (ks)'] = novy_pocet
        st.session_state.aktualne_objednavky[index_v_liste]['Potvrdene'] = potvrdene
        auto_uloz() 

    for i, obj in enumerate(st.session_state.aktualne_objednavky):
        if obj.get('❌ Zmazať') == True or obj.get('Sudy') == True: continue
            
        with st.container():
            aktualne_zabalene = int(obj.get('Zabalené (ks)', obj['Kusy']))
            objednane = int(obj['Kusy'])
            potvrdene = obj.get('Potvrdene') == True
            
            col_text, col_cisla, col_chk = st.columns([3, 1, 1])
            with col_text:
                if potvrdene and aktualne_zabalene == objednane:
                    st.markdown(f"✅ :green[**{obj['Odberateľ']}** | {obj['Káva']} ({obj['Gramáž']}g) - {objednane} ks]")
                else:
                    st.markdown(f"📦 **{obj['Odberateľ']}** | {obj['Káva']} ({obj['Gramáž']}g) - Objednané: {objednane} ks")
            
            with col_cisla:
                st.number_input("Hotovo (ks):", min_value=0, value=aktualne_zabalene, step=1, key=f"pro_pocet_{i}", on_change=zmena_balenia_pro_callback, args=(i,), label_visibility="collapsed")
            with col_chk:
                st.checkbox("Zabalené", value=potvrdene, key=f"pro_chk_{i}", on_change=zmena_balenia_pro_callback, args=(i,))
        st.markdown("---")

# ========================================================
# TAB 4: ÚČTOVNÍCTVO
# ========================================================
with tab4:
    st.header("📤 Generovanie TXT pre Evičku (Omega)")
    st.write("Dáta pre export a fakturáciu zatiaľ pripravujeme na ostrej verzii 4.2.")
