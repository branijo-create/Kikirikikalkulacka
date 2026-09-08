import streamlit as st
import pandas as pd
import math
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="Roastery Manager v2.8", page_icon="☕", layout="wide")

# --- KONFIGURÁCIA Z TVOJHO KÓDU ---
KAPACITA_ZELENA_BATCH = 5.0
STANDARDNY_VYPEK = 20
DNESNY_DATUM = datetime.now().strftime("%d-%m-%Y")

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

if 'form_key' not in st.session_state:
    st.session_state.form_key = 0

def vynuluj_policka():
    st.session_state.form_key += 1

# --- HLAVNÉ ROZHRANIE ---
st.title("☕ Roastery Manager v2.8")

# --- IMPORT Z EXCELU ---
st.subheader("📁 Import objednávok z Excelu")
st.write("Excel musí obsahovať stĺpce s presnými názvami: **Odberateľ**, **Káva**, **Gramáž**, **Kusy**")
nahraty_subor = st.file_uploader("Nahraj .xlsx súbor", type=["xlsx"])

if nahraty_subor is not None:
    try:
        xl = pd.ExcelFile(nahraty_subor)
        if 'Spracovane_Objednavky' in xl.sheet_names:
            df_import = xl.parse('Spracovane_Objednavky')
        else:
            df_import = xl.parse(0)

        if st.button("📥 Načítať dáta z tohto Excelu"):
            for index, row in df_import.iterrows():
                st.session_state.aktualne_objednavky.append({
                    "Odberateľ": str(row.get("Odberateľ", "Neznámy")),
                    "Káva": str(row.get("Káva", "")),
                    "Gramáž": int(row.get("Gramáž", 0)),
                    "Kusy": int(row.get("Kusy", 0)),
                    "Zabalené (ks)": int(row.get("Kusy", 0))
                })
            st.success("Objednávky boli úspešne načítané do zoznamu nižšie!")
    except Exception as e:
        st.error(f"Chyba pri čítaní súboru. Uisti sa, že je to správny Excel. Detaily: {e}")

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
        if kusy_220 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 220, "Kusy": kusy_220, "Zabalené (ks)": kusy_220})
        if kusy_500 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 500, "Kusy": kusy_500, "Zabalené (ks)": kusy_500})
        if kusy_1000 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 1000, "Kusy": kusy_1000, "Zabalené (ks)": kusy_1000})
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
                st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": k, "Gramáž": gramaz, "Kusy": v, "Zabalené (ks)": v})
        vynuluj_policka()
        st.rerun()

st.divider()

col_zoznam, col_vypocet = st.columns([2, 3])

with col_zoznam:
    st.subheader("🛒 Aktuálne objednávky")
    st.write("*(Dvojklikom prepíšeš údaje. Pre vymazanie označ riadok vľavo a stlač Delete)*")
    
    if st.session_state.aktualne_objednavky:
        for obj in st.session_state.aktualne_objednavky:
            if 'Zabalené (ks)' not in obj:
                obj['Zabalené (ks)'] = obj['Kusy']

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
            potreba_skladania_blendov = {}
            
            for o in st.session_state.aktualne_objednavky:
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
                realny_vynos_uprazena = skutocna_zelena * (1 - (STANDARDNY_VYPEK / 100.0))
                zostatok_uprazena = realny_vynos_uprazena - uprazena_potreba

                finalny_plan.append({
                    "Zelené zrno": zrno,
                    "Potrebné upražiť (kg)": round(uprazena_potreba, 2),
                    "Dávky (á 5kg)": davky,
                    "Navážiť zelenú (kg)": skutocna_zelena,
                    "Zostatok (kg upraž.)": round(zostatok_uprazena, 2)
                })
            
            df_plan = pd.DataFrame(finalny_plan)
            st.success(f"Vypočítané pre fixnú kapacitu {KAPACITA_ZELENA_BATCH}kg zelenej kávy na dávku.")
            st.dataframe(df_plan, use_container_width=True, hide_index=True)
            
            celkovo_davok = int(df_plan["Dávky (á 5kg)"].sum())
            st.markdown(f"### 🔥 Celkový počet pražení: **{celkovo_davok} dávok**")
            
            finalny_plan_blendov = []
            for meno_blendu, celkova_vaha_blendu in potreba_skladania_blendov.items():
                recept = kavy_recepty[meno_blendu]["recept"]
                for zrno, podiel in recept.items():
                    vaha_zlozky_kg = celkova_vaha_blendu * podiel
                    finalny_plan_blendov.append({
                        "Názov blendu": meno_blendu,
                        "Celková hmotnosť blendu (kg)": round(celkova_vaha_blendu, 2),
                        "Kávová zložka": zrno,
                        "Podiel v blende": f"{int(podiel * 100)}%",
                        "Hmotnosť zložky (kg)": round(vaha_zlozky_kg, 2)
                    })
            
            if finalny_plan_blendov:
                df_blendov = pd.DataFrame(finalny_plan_blendov)
            else:
                df_blendov = pd.DataFrame(columns=["Názov blendu", "Celková hmotnosť blendu (kg)", "Kávová zložka", "Podiel v blende", "Hmotnosť zložky (kg)"])
            
            st.divider()
            st.subheader("🥣 Plán miešania blendov (Receptúry po upražení)")
            if not df_blendov.empty:
                st.dataframe(df_blendov, use_container_width=True, hide_index=True)
            else:
                st.info("V aktuálnych objednávkach sa nenachádzajú žiadne zmesové kávy (blendy).")
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_plan.to_excel(writer, index=False, sheet_name='Plan_Prazenia')
                df_objednavky_export.to_excel(writer, index=False, sheet_name='Spracovane_Objednavky')
                df_blendov.to_excel(writer, index=False, sheet_name='Plan_Blendov')
            
            st.divider()
            st.download_button(
                label="💾 Stiahnuť kompletný 3-hárok do Excelu",
                data=buffer.getvalue(),
                file_name=f"KIKIRIKI_kompletny_plan_{DNESNY_DATUM}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )


# ---------------------------------------------------------
# EXPORTY PRE EVIČKU (ÚČTOVNÍCTVO) A KONTROLA BALENIA
# ---------------------------------------------------------
st.markdown("---")
st.subheader("✅ Potvrdenie balenia a Export pre Evičku")

@st.cache_data
def nacitaj_cennik():
    return pd.read_excel("Kalkulacia stefi posledna prazenie 7.9.2026..xlsx", sheet_name='Cenník kávy', skiprows=4)

if st.session_state.aktualne_objednavky:
    
    DRAFT_FILE = "rozpracovane_balenie.json"

    # Tlačidlo na načítanie nedokončenej práce
    if os.path.exists(DRAFT_FILE):
        if st.button("🔄 Načítať rozpísané balenie (obnova)", type="secondary"):
            try:
                with open(DRAFT_FILE, "r", encoding="utf-8") as f:
                    st.session_state.aktualne_objednavky = json.load(f)
                st.success("Obnovené! Môžeš pokračovať v balení.")
                st.rerun()
            except Exception as e:
                st.error("Nepodarilo sa načítať zálohu.")

    st.markdown("### 📱 Mobilná kontrola balenia")
    st.info("Ťukaj na + a - pre úpravu kusov. Keď zabalíš časť, klikni na **Uložiť priebežne**.")

    upravene_objednavky = []
    
    # Generovanie veľkých vertikálnych kariet pre mobil
    for i, obj in enumerate(st.session_state.aktualne_objednavky):
        with st.container():
            st.markdown(f"**{obj['Odberateľ']}** | {obj['Káva']} ({obj['Gramáž']}g)")
            
            novy_pocet = st.number_input(
                "Zabalené ks:", 
                min_value=0, 
                value=int(obj.get('Zabalené (ks)', obj['Kusy'])), 
                step=1, 
                key=f"mob_balenie_{i}"
            )
            
            upraveny_obj = obj.copy()
            upraveny_obj['Zabalené (ks)'] = novy_pocet
            upravene_objednavky.append(upraveny_obj)
            st.markdown("---") 

    st.session_state.aktualne_objednavky = upravene_objednavky
    upravene_balenie_df = pd.DataFrame(st.session_state.aktualne_objednavky)

    # Tlačidlo na bezpečné priebežné uloženie počas balenia
    if st.button("💾 Uložiť priebežne (počas balenia)", type="primary", use_container_width=True):
        with open(DRAFT_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.aktualne_objednavky, f, ensure_ascii=False, indent=2)
        st.toast("Progres bol bezpečne uložený!", icon="✅")
    
    st.write("---")
    
    zoznam_odberatelov = ["Všetci"] + sorted(list(upravene_balenie_df['Odberateľ'].unique()))
    vybrany_odberatel = st.selectbox("Filtrovať export podľa odberateľa (pre Evičku):", zoznam_odberatelov)
    
    try:
        df_cennik = nacitaj_cennik()
        
        df_vypocet = upravene_balenie_df.copy()
        
        # Automatické vyradenie položiek, kde si pri balení zadal 0 ks
        df_vypocet = df_vypocet[df_vypocet['Zabalené (ks)'] > 0]
        
        if vybrany_odberatel != "Všetci":
            df_vypocet = df_vypocet[df_vypocet['Odberateľ'] == vybrany_odberatel]
            
        preklad_cennik = {
            "Brazília": "Brazília – Donas do Café",
            "Etiopia Yerg.": "Etiópia – Yirgacheffe",
            "Etiopia BG": "Etiópia – Banko Gotiti",
            "Honduras": "Honduras – SHG EP San Andrés",
            "Columbia": "Kolumbia – Huila condor",
            "Indonezia": "Indinezia", 
            "India": "India Plantation AA",
            "Aranka": "Aranka",
            "Frištuk": "Frištuk",
            "K52%": "K52% / Cucflek",
            "Cucflek": "K52% / Cucflek",
            "Peru": "Peru",
            "Rwanda": "Rwanda"
        }

        preklad_faktura = {
            "Brazília": "Brazília – Donas do Café",
            "Etiopia Yerg.": "Etiópia – Yirgacheffe",
            "Etiopia BG": "Etiópia – Banko Gotiti",
            "Honduras": "Honduras – SHG EP San Andrés",
            "Columbia": "Kolumbia – Huila condor",
            "Indonezia": "Indonézia", 
            "India": "India Plantation AA",
            "Aranka": "Aranka",
            "Frištuk": "Frištuk",
            "K52%": "Kopaničiarska 52%",
            "Cucflek": "Cucflek",
            "Peru": "Peru",
            "Rwanda": "Rwanda"
        }
        
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
            
            # ---------------------------------------------------------
            # EXCEL EXPORT PRE EVIČKU
            # ---------------------------------------------------------
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Prehľad pre Evičku')
                workbook = writer.book
                worksheet = writer.sheets['Prehľad pre Evičku']
                header_format = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white'})
                for col_num, value in enumerate(df_export.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    worksheet.set_column(col_num, col_num, 20)
                    
            excel_data = excel_buffer.getvalue()

            # ---------------------------------------------------------
            # TXT EXPORT PRE KROS OMEGU
            # ---------------------------------------------------------
            lines = []
            lines.append("R00\tT01")
            
            grouped = df_export.groupby('Odberateľ')
            invoice_counter = 1
            
            today_str = datetime.now().strftime("%d.%m.%Y")
            due_str = (datetime.now() + timedelta(days=14)).strftime("%d.%m.%Y")
            
            for odberatel, group in grouped:
                cislo_dokladu = f"EXP{datetime.now().strftime('%Y%m%d')}{invoice_counter:02d}"
                suma_celkom = group['Celková suma (€)'].sum()
                
                r01 = [
                    "R01",
                    cislo_dokladu,
                    str(odberatel),
                    "",
                    today_str,
                    due_str,
                    today_str,
                    "0.00",
                    f"{suma_celkom:.2f}"
                ]
                lines.append("\t".join(r01))
                
                for _, row in group.iterrows():
                    r02 = [
                        "R02",
                        f"{row['Produkt']} {row['Gramáž']}",
                        str(row['Množstvo (ks)']),
                        "ks",
                        f"{row['Jednotková cena (€)']:.2f}",
                        "V",
                        "0.00",
                        f"{row['Jednotková cena (€)']:.2f}",
                        "0",
                        "V"
                    ]
                    lines.append("\t".join(r02))
                    
                invoice_counter += 1
                
            txt_data = "\n".join(lines).encode('windows-1250', errors='replace')
            
            if vybrany_odberatel == "Všetci":
                meno_do_suboru = "Vsetci"
            else:
                meno_do_suboru = vybrany_odberatel.replace(" ", "_")

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📊 Stiahnuť Excel pre Evičku",
                    data=excel_data,
                    file_name=f"Kikiriki_Prehlad_Evicka_{meno_do_suboru}_{DNESNY_DATUM}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_excel_ucto"
                )
            with col2:
                st.download_button(
                    label="⚙️ Stiahnuť TXT pre Kros",
                    data=txt_data,
                    file_name=f"Kikiriki_Import_Omega_{meno_do_suboru}_{DNESNY_DATUM}.txt",
                    mime="text/plain",
                    key="btn_txt_ucto"
                )
        else:
            st.warning("Pre tohto odberateľa nie sú zaznamenané žiadne zabalené kusy.")

    except Exception as e:
        st.error(f"Technická chyba pre Braňa: {e}")
else:
    st.info("Pridaj nejaké objednávky vyššie, aby sa ti aktivovali tlačidlá na export pre Evičku.")
