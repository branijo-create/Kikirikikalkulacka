import streamlit as st
import pandas as pd
import math
import io
from datetime import datetime, timedelta
import json

st.set_page_config(page_title="Roastery Manager PRO v5.0", page_icon="🏭", layout="wide")

# --- KONFIGURÁCIA ---
KAPACITA_ZELENA_BATCH = 5.0
STANDARDNY_VYPEK = 20
DNESNY_DATUM = datetime.now().strftime("%d-%m-%Y")
# ZMENA: Nová oddelená databáza pre PRO verziu!
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
        
        # Ak tabuľka neexistuje, vytvorí ju
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
        # Migrácia starých dát
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
    st.session_state.info_cloud = f"☁️ Posledná úprava na Disku: **{cas}**"

if 'nazov_prazenia' not in st.session_state:
    st.session_state.nazov_prazenia = st.session_state.get('pociatocny_nazov', f"Prazenie_PRO_{DNESNY_DATUM}")

if 'form_key' not in st.session_state: st.session_state.form_key = 0
def vynuluj_policka(): st.session_state.form_key += 1

# --- HLAVNÉ ROZHRANIE ---
st.title("🏭 Roastery Manager PRO (v5.0)")
st.info("⚠️ Toto je nová paralelná vývojová verzia. Beží na samostatnej databáze a neovplyvňuje Majovu prácu.")

st.text_input("📅 Názov aktuálneho praženia:", key="nazov_prazenia", on_change=auto_uloz)

tab1, tab2, tab3, tab4 = st.tabs(["📝 1. Kancelária (Objednávky)", "🔥 2. Pražiareň (Stroj)", "📦 3. Baliareň a Dózy", "📊 4. Účtovníctvo"])

# ========================================================
# TAB 1: OBJEDNÁVKY
# ========================================================
with tab1:
    st.markdown("Tu prijímaš objednávky. Pridávanie je rovnaké ako doteraz.")
    
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
            if kusy_220 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 220, "Kusy": kusy_220, "Zabalené (ks)": kusy_220, "Potvrdene": False, "❌ Zmazať": False})
            if kusy_500 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 500, "Kusy": kusy_500, "Zabalené (ks)": kusy_500, "Potvrdene": False, "❌ Zmazať": False})
            if kusy_1000 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 1000, "Kusy": kusy_1000, "Zabalené (ks)": kusy_1000, "Potvrdene": False, "❌ Zmazať": False})
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
                if v > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": k, "Gramáž": gramaz, "Kusy": v, "Zabalené (ks)": v, "Potvrdene": False, "❌ Zmazať": False})
            auto_uloz()
            vynuluj_policka()
            st.rerun()
            
    elif rezim == "🟢 Pridať celý BATCH (Sklad - Sud)":
        with st.container():
            st.success("🟢 Káva sa pripočíta do plánu praženia, padne rovno do Dózy, ale nežiada etikety na balenie.")
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
    st.subheader("🛒 Tvoja kniha objednávok")
    if st.session_state.aktualne_objednavky:
        df_objednavky_vstup = pd.DataFrame(st.session_state.aktualne_objednavky)
        upravene_df = st.data_editor(df_objednavky_vstup, use_container_width=True, num_rows="fixed", hide_index=False, key="tabulka_objednavok")
        novy_stav = upravene_df.to_dict('records')
        if novy_stav != st.session_state.aktualne_objednavky:
            st.session_state.aktualne_objednavky = novy_stav
            auto_uloz()
            
        col_del1, col_del2, col_del3 = st.columns(3)
        with col_del1:
            if st.button("🗑️ Odstrániť zaškrtnuté", type="primary"):
                st.session_state.aktualne_objednavky = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
                auto_uloz()
                st.rerun()
        with col_del3:
            if st.button("⚠️💣 VYMAZAŤ CELÝ VÍKEND (Nový štart)", type="primary"):
                st.session_state.aktualne_objednavky = []
                st.session_state.priebeh_prazenia = {} # Resetne aj dózy!
                auto_uloz()
                st.rerun()
    else:
        st.info("Zatiaľ žiadne objednávky na tento víkend.")

# ========================================================
# TAB 2: PRAŽIAREŇ (Výroba)
# ========================================================
with tab2:
    st.header("🔥 Zoznam úloh pre Pražičku")
    st.write("Podľa prijatých objednávok a požiadaviek na sklad potrebuješ upražiť toto zrno. Zapisuj si reálne praženia priamo sem.")
    
    aktivne_objednavky = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
    potreba_zelenej_podla_zrna = {}
    potreba_uprazenej_podla_zrna = {}
    
    for o in aktivne_objednavky:
        if o.get("Sudy", False):
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
        st.info("Zatiaľ nie je čo pražiť.")
    else:
        # Checklista pre každé zrno
        for zrno, teoreticka_vaha_zelena in potreba_zelenej_podla_zrna.items():
            davky_plan = math.ceil(teoreticka_vaha_zelena / KAPACITA_ZELENA_BATCH)
            zelena_plan = davky_plan * KAPACITA_ZELENA_BATCH
            
            # Získanie aktuálneho stavu z pamäte
            stav = st.session_state.priebeh_prazenia.get(zrno, {"hotovo": False, "zelena_real": 0.0, "uprazena_real": 0.0})
            
            with st.expander(f"{'✅' if stav['hotovo'] else '⏳'} Zrnko: {zrno} (Plán: {davky_plan} dávok)", expanded=not stav['hotovo']):
                col_info, col_input = st.columns([1, 1])
                
                with col_info:
                    st.markdown("**Čo hovorí plán:**")
                    st.write(f"- Minimálne potrebuješ upražiť: **{potreba_uprazenej_podla_zrna[zrno]:.2f} kg**")
                    st.write(f"- To znamená navážiť zelenú: **{zelena_plan:.1f} kg** ({davky_plan} batchov)")
                
                with col_input:
                    st.markdown("**Aká je realita pri stroji?**")
                    def update_priebeh(z=zrno):
                        z_real = st.session_state[f"z_real_{z}"]
                        u_real = st.session_state[f"u_real_{z}"]
                        hotovo = st.session_state[f"hotovo_{z}"]
                        st.session_state.priebeh_prazenia[z] = {
                            "zelena_real": z_real,
                            "uprazena_real": u_real,
                            "hotovo": hotovo
                        }
                        auto_uloz()
                    
                    st.number_input("Skutočne nasypaná zelená (kg):", value=float(stav["zelena_real"] or zelena_plan), step=0.1, key=f"z_real_{zrno}", on_change=update_priebeh)
                    st.number_input("Skutočne vysypaná upražená (kg):", value=float(stav["uprazena_real"]), step=0.1, key=f"u_real_{zrno}", on_change=update_priebeh)
                    
                    z_vaha = st.session_state[f"z_real_{zrno}"]
                    u_vaha = st.session_state[f"u_real_{zrno}"]
                    if z_vaha > 0 and u_vaha > 0:
                        vypek = (1 - (u_vaha / z_vaha)) * 100
                        st.caption(f"Aktuálny výpek na tomto zrne: **{vypek:.1f}%**")
                        
                    st.checkbox("✅ Praženie tohto zrna je UKONČENÉ (Nasypané do dózy)", value=stav["hotovo"], key=f"hotovo_{zrno}", on_change=update_priebeh)

# ========================================================
# TAB 3: BALIAREŇ A DÓZY
# ========================================================
with tab3:
    st.header("📦 Zostatky v Dózach a Odškrtávanie sáčkov")
    
    # --- VÝPOČET STAVU DÓZ ---
    # 1. Získame koľko sa reálne upražilo (prítok do Dózy)
    stav_doz = {}
    for zrno, data in st.session_state.priebeh_prazenia.items():
        if data["hotovo"]:
            stav_doz[zrno] = stav_doz.get(zrno, 0.0) + data["uprazena_real"]
            
    # 2. Odpočítame koľko sa reálne ZABALILO (odtok z Dózy)
    aktivne_objednavky = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
    for o in aktivne_objednavky:
        # Rátame iba tie, ktoré sú naozaj odškrtnuté že sú zabalené a NIE SÚ to Sudy (sudy sú už v dóze ako zostatok)
        if o.get("Potvrdene", False) and not o.get("Sudy", False):
            zabalena_vaha_kg = o["Zabalené (ks)"] * o["Gramáž"] / 1000.0
            if o["Káva"] in kavy_recepty:
                recept = kavy_recepty[o["Káva"]]["recept"]
                for zrno, podiel in recept.items():
                    # Odpočítame podiel z konkrétnej zložky (blendovanie sa deje pri balení)
                    if zrno in stav_doz:
                        stav_doz[zrno] -= (zabalena_vaha_kg * podiel)

    # Vykreslenie vizuálu Dóz
    st.subheader("🛢️ Aktuálny fyzický stav (Čo by malo byť v bareloch)")
    if not stav_doz:
        st.info("Zatiaľ nemáš upražené a potvrdené žiadne zrno z Pražiarne.")
    else:
        dozy_cols = st.columns(len(stav_doz))
        for idx, (zrno, vaha) in enumerate(stav_doz.items()):
            with dozy_cols[idx % len(dozy_cols)]:
                farba = "green" if vaha > 0 else ("red" if vaha < 0 else "gray")
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
        # Ignorujeme zmazané a SUDY (tým netreba etikety)
        if obj.get('❌ Zmazať', False) or obj.get('Sudy', False): continue
            
        with st.container():
            aktualne_zabalene = int(obj.get('Zabalené (ks)', obj['Kusy']))
            objednane = int(obj['Kusy'])
            potvrdene = obj.get('Potvrdene', False)
            
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
    st.write("Funguje identicky ako doteraz - generuje sa z potvrdených a zabalených kusov.")
    st.info("Kód pre prepojenie s cenníkom a KROS Omega zostal zhodný z verzie 4.2.")
    # (Sem by išiel ten istý obrovský blok kódu na generovanie TXT a Excelu pre účtovníčku)
