import streamlit as st
import pandas as pd
import math
import io

st.set_page_config(page_title="Roastery Manager v2.8", page_icon="☕", layout="wide")

# --- KONFIGURÁCIA Z TVOJHO KÓDU ---
KAPACITA_ZELENA_BATCH = 5.0
STANDARDNY_VYPEK = 20

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

# --- PAMÄŤ APLIKÁCIE ---
if 'aktualne_objednavky' not in st.session_state:
    st.session_state.aktualne_objednavky = []

# FUNKCIA NA VYNULOVANIE VŠETKÝCH POLÍČOK
def vynuluj_policka():
    for g in gramaze_list:
        if f"kusy_{g}" in st.session_state:
            st.session_state[f"kusy_{g}"] = 0
    for k in kavy_recepty.keys():
        if f"kusy_{k}" in st.session_state:
            st.session_state[f"kusy_{k}"] = 0

# --- HLAVNÉ ROZHRANIE ---
st.title("☕ Roastery Manager v2.8")

# --- IMPORT Z EXCELU ---
st.subheader("📁 Import objednávok z Excelu")
st.write("Excel musí obsahovať stĺpce s presnými názvami: **Odberateľ**, **Káva**, **Gramáž**, **Kusy**")
nahraty_subor = st.file_uploader("Nahraj .xlsx súbor", type=["xlsx"])

if nahraty_subor is not None:
    try:
        df_import = pd.read_excel(nahraty_subor)
        if st.button("📥 Načítať dáta z tohto Excelu"):
            for index, row in df_import.iterrows():
                st.session_state.aktualne_objednavky.append({
                    "Odberateľ": str(row.get("Odberateľ", "Neznámy")),
                    "Káva": str(row.get("Káva", "")),
                    "Gramáž": int(row.get("Gramáž", 0)),
                    "Kusy": int(row.get("Kusy", 0))
                })
            st.success("Objednávky boli úspešne načítané do zoznamu nižšie!")
    except Exception as e:
        st.error(f"Chyba pri čítaní súboru. Uisti sa, že je to správny Excel. Detaily: {e}")

st.divider()

st.subheader("1. Manuálne pridanie objednávky")
col1, col2 = st.columns(2)

with col1:
    meno = st.text_input("Odberateľ:", placeholder="Meno")
    # Pri zmene režimu sa zavolá "vynuluj_policka"
    rezim = st.radio("Režim zadávania:", ["Podľa kávy", "Podľa gramáže"], horizontal=True, on_change=vynuluj_policka)

if rezim == "Podľa kávy":
    with col1:
        # Pri zmene kávy sa zavolá "vynuluj_policka"
        kava = st.selectbox("Káva:", list(kavy_recepty.keys()), on_change=vynuluj_policka)
    with col2:
        kusy_220 = st.number_input("220g (ks):", min_value=0, step=1, key="kusy_220")
        kusy_500 = st.number_input("500g (ks):", min_value=0, step=1, key="kusy_500")
        kusy_1000 = st.number_input("1000g (ks):", min_value=0, step=1, key="kusy_1000")

    if st.button("➕ Pridať do zoznamu", type="secondary"):
        if kusy_220 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 220, "Kusy": kusy_220})
        if kusy_500 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 500, "Kusy": kusy_500})
        if kusy_1000 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 1000, "Kusy": kusy_1000})
        vynuluj_policka() # Vynuluje políčka po úspešnom pridaní
        st.rerun()

else:
    with col1:
        # Pri zmene gramáže sa zavolá "vynuluj_policka"
        gramaz = st.selectbox("Gramáž:", gramaze_list, on_change=vynuluj_policka)
    with col2:
        inputs_kavy = {}
        for k in kavy_recepty.keys():
            inputs_kavy[k] = st.number_input(f"{k} (ks):", min_value=0, step=1, key=f"kusy_{k}")

    if st.button("➕ Pridať do zoznamu", type="secondary"):
        for k, v in inputs_kavy.items():
            if v > 0:
                st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": k, "Gramáž": gramaz, "Kusy": v})
        vynuluj_policka() # Vynuluje políčka po úspešnom pridaní
        st.rerun()

st.divider()

# --- ZOZNAM A VÝPOČET ---
col_zoznam, col_vypocet = st.columns([2, 3])

with col_zoznam:
    st.subheader("🛒 Aktuálne objednávky")
    st.write("*(Dvojklikom prepíšeš údaje. Pre vymazanie označ riadok vľavo a stlač Delete)*")
    
    if st.session_state.aktualne_objednavky:
        df_objednavky_vstup = pd.DataFrame(st.session_state.aktualne_objednavky)
        
        upravene_df = st.data_editor(
            df_objednavky_vstup, 
            use_container_width=True, 
            num_rows="dynamic",
            hide_index=False
        )
        
        st.session_state.aktualne_objednavky = upravene_df.to_dict('records')
        
        if st.button("🗑️ Vymazať úplne všetko"):
            st.session_state.aktualne_objednavky = []
            st.rerun()
    else:
        st.info("Zoznam je zatiaľ prázdny.")

with col_vypocet:
    st.subheader("Plán praženia")
    if st.button("🚀 VYPOČÍTAŤ PLÁN", type="primary", use_container_width=True):
        if not st.session_state.aktualne_objednavky:
            st.warning("Prázdne! Najprv pridaj nejaké objednávky.")
        else:
            df_objednavky_export = pd.DataFrame(st.session_state.aktualne_objednavky)
            potreba_zelenej_podla_zrna = {}
            potreba_uprazenej_podla_zrna = {}
            
            for o in st.session_state.aktualne_objednavky:
                uprazena_kg = (o["Kusy"] * o["Gramáž"] / 1000.0)
                zelena_kg_zaklad = uprazena_kg / (1 - (STANDARDNY_VYPEK / 100.0))
                
                if o["Káva"] in kavy_recepty:
                    recept = kavy_recepty[o["Káva"]]["recept"]
                    for zrno, podiel in recept.items():
                        potreba_zelenej_podla_zrna[zrno] = potreba_zelenej_podla_zrna.get(zrno, 0) + (zelena_kg_zaklad * podiel)
                        potreba_uprazenej_podla_zrna[zrno] = potreba_uprazenej_podla_zrna.get(zrno, 0) + (uprazena_kg * podiel)

            finalny_plan = []
            for zrno, teoreticka_vaha_zelena in potreba_zelenej_podla_zrna.items():
                uprazena_potreba = potreba_uprazenej_podla_zrna[zrno]
                davky = math.ceil(round(teoreticka_vaha_zelena, 4) / KAPACITA_ZELENA_BATCH)
                skutocna_zelena = davky * KAPACITA_ZELENA_BATCH
                realny_vynos_uprazena = skutocna_zelena * (1 - (STANDARDNY_VYPEK / 100.
