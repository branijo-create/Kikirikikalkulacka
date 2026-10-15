import streamlit as st
import pandas as pd
import math
import io
import os
import hmac
import copy
import time
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

# Log: jeden riadok za každú zmenu skladu / akciu
NAZOV_LISTU_LOG = "Log"
LOG_HLAVICKA = ["Čas", "Identifikátor", "Akcia", "Detail", "Sklad", "SKU", "Názov", "Pred", "Po", "Zmena"]
NAZVY_SKLADU = {"zelena": "Zelená", "uprazena": "Dózy", "zabalena": "Regál", "obaly": "Obaly", "etikety": "Etikety"}
TYPY_SKLADU = ["zelena", "uprazena", "zabalena", "obaly", "etikety"]

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
NAZVY_ZABALENA = {get_pc_sku(rc, g): f"{menu} {g}g" for menu, rc in MENU_KAVY.items() for g in gramaze_list}
PC_NA_KAVU = {get_pc_sku(rc, g): (menu, g) for menu, rc in MENU_KAVY.items() for g in gramaze_list}

# Obalový materiál: prázdne sáčky podľa gramáže, etikety podľa kávy
SKU_OBAL = {g: f"OB{g}" for g in gramaze_list}                                  # OB220, OB500, OB1000
NAZVY_OBALY = {f"OB{g}": f"Prázdny sáčok {g} g" for g in gramaze_list}
SKU_ETIKETA = {menu: f"ET{rc[2:]}" for menu, rc in MENU_KAVY.items()}             # ET001 … ETB004
NAZVY_ETIKETY = {v: f"Etiketa {k}" for k, v in SKU_ETIKETA.items()}

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

# --- LOG FUNKCIE ---
def nazov_sku(typ, sku):
    if typ == "zelena": return NAZVY_ZELENA.get(sku, "")
    if typ == "uprazena": return NAZVY_UPRAZENA.get(sku, "")
    if typ == "obaly": return NAZVY_OBALY.get(sku, "")
    if typ == "etikety": return NAZVY_ETIKETY.get(sku, "")
    return NAZVY_ZABALENA.get(sku, "")

def diff_skladu(pred, po):
    zmeny = []
    for typ in TYPY_SKLADU:
        a_d = (pred or {}).get(typ, {})
        b_d = (po or {}).get(typ, {})
        for sku in sorted(set(a_d) | set(b_d)):
            a = float(a_d.get(sku, 0) or 0)
            b = float(b_d.get(sku, 0) or 0)
            if abs(a - b) > 1e-9:
                zmeny.append((typ, sku, a, b))
    return zmeny

def priprav_log(cas, nazov, akcia, detail, sklad_pred, sklad_po):
    detail = str(detail)[:1000]
    zmeny = diff_skladu(sklad_pred, sklad_po) if sklad_pred is not None else []
    if not zmeny:
        return [[cas, nazov, akcia, detail, "", "", "", "", "", ""]]
    return [[cas, nazov, akcia, detail, NAZVY_SKLADU[t], sku, nazov_sku(t, sku), round(a, 3), round(b, 3), round(b - a, 3)]
            for t, sku, a, b in zmeny]

def ziskaj_log_list(spreadsheet):
    import gspread
    try:
        return spreadsheet.worksheet(NAZOV_LISTU_LOG)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=NAZOV_LISTU_LOG, rows=1000, cols=len(LOG_HLAVICKA))
        ws.append_row(LOG_HLAVICKA, value_input_option="RAW")
        return ws

def nacitaj_log():
    import gspread
    spreadsheet = otvor_tabulku(get_client())
    try:
        ws = spreadsheet.worksheet(NAZOV_LISTU_LOG)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame(columns=LOG_HLAVICKA)
    riadky = ws.get_all_values()
    if len(riadky) < 2:
        return pd.DataFrame(columns=LOG_HLAVICKA)
    df = pd.DataFrame(riadky[1:], columns=riadky[0])
    return df.iloc[::-1].reset_index(drop=True)

NAZOV_LISTU_EVICKA = "Evicka_Logy"

def uloz_export_pre_evicku(odberatel, txt_obsah):
    try:
        import gspread
        spreadsheet = otvor_tabulku(get_client())
        try:
            ws = spreadsheet.worksheet(NAZOV_LISTU_EVICKA)
        except gspread.exceptions.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=NAZOV_LISTU_EVICKA, rows=1000, cols=3)
            ws.append_row(["Čas exportu", "Odberateľ", "TXT Obsah"], value_input_option="RAW")
        ws.append_row([datetime.now().strftime("%d.%m.%Y %H:%M:%S"), odberatel, txt_obsah], value_input_option="RAW")
        return True
    except Exception:
        return False

def nacitaj_exporty_pre_evicku():
    try:
        spreadsheet = otvor_tabulku(get_client())
        zaznamy = spreadsheet.worksheet(NAZOV_LISTU_EVICKA).get_all_values()[1:]
        return list(reversed(zaznamy))
    except Exception:
        return []

def nacitaj_historiu():
    import gspread
    spreadsheet = otvor_tabulku(get_client())
    try:
        ws = spreadsheet.worksheet(NAZOV_LISTU_HISTORIA)
    except gspread.exceptions.WorksheetNotFound:
        return []
    zaznamy = []
    for r in ws.get_all_values():
        if len(r) < 3 or not r[0]: continue
        zaznamy.append({"cas": r[0], "nazov": r[1], "data": "".join(r[2:])})
    zaznamy.reverse()
    return zaznamy

def _norm(v):
    if hasattr(v, "item"):
        try: v = v.item()
        except Exception: pass
    if v is None: return None
    if isinstance(v, bool): return v
    if isinstance(v, float):
        if math.isnan(v): return None
        if v.is_integer(): return int(v)
    return v

def diff_objednavok(stare, nove):
    zmeny = []
    for i, (a, b) in enumerate(zip(stare, nove)):
        for k in sorted(set(a) | set(b)):
            va, vb = _norm(a.get(k)), _norm(b.get(k))
            if va != vb:
                zmeny.append(f"#{i+1} {b.get('Odberateľ','')}/{b.get('Káva','')} {b.get('Gramáž','')}g: {k} {va}→{vb}")
    if len(stare) != len(nove):
        zmeny.append(f"Počet riadkov {len(stare)}→{len(nove)}")
    return zmeny

def je_duplicitny_klik(kluc, hodnota, okno_s=2.0):
    """True, ak rovnaká akcia s rovnakou hodnotou prišla znova do `okno_s` sekúnd (dvojklik)."""
    teraz = time.time()
    posledny = st.session_state.get(f"_klik_{kluc}")
    st.session_state[f"_klik_{kluc}"] = (hodnota, teraz)
    return posledny is not None and posledny[0] == hodnota and (teraz - posledny[1]) < okno_s

def popis_obj(o):
    return f"{o.get('Odberateľ','')}: {o.get('Kusy',0)}× {o.get('Káva','')} {o.get('Gramáž','')}g"

def uloz_do_google_sheets(data_dict, nazov_prazenia, historia=False, log=None):
    cas_ulozenia = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    spreadsheet = None
    try:
        client = get_client()
        spreadsheet = otvor_tabulku(client)
        ws = ziskaj_list(spreadsheet, NAZOV_LISTU_STAV, riadky=200, stlpce=2)

        kusky = rozdel_na_kusky(json.dumps(data_dict, ensure_ascii=False))

        potrebne_riadky = 3 + len(kusky)
        if ws.row_count < potrebne_riadky:
            ws.resize(rows=potrebne_riadky + 50)

        # Najprv dáta, potom hlavička s počtom kúskov (pri páde sa číta stále starý počet)
        ws.update(range_name=f"A4:A{3 + len(kusky)}", values=[[k] for k in kusky], value_input_option="RAW")
        ws.update(range_name="A1:A3", values=[[cas_ulozenia], [str(nazov_prazenia)], [str(len(kusky))]], value_input_option="RAW")

        if historia:
            uloz_snapshot_historie(spreadsheet, cas_ulozenia, str(nazov_prazenia), kusky)
    except Exception as e:
        chyba = str(e)
        if "200" not in chyba:
            return False, chyba

    if log:
        try:
            akcia, detail, sklad_pred = log
            riadky = priprav_log(cas_ulozenia, str(nazov_prazenia), akcia, detail, sklad_pred, data_dict["sklad"])
            if spreadsheet is None:
                spreadsheet = otvor_tabulku(get_client())
            ziskaj_log_list(spreadsheet).append_rows(riadky, value_input_option="RAW")
        except Exception as e:
            return True, f"Stav uložený, ale log sa nepodarilo zapísať: {e}"
    return True, None

def auto_uloz(historia=False, akcia=None, detail="", sklad_pred=None):
    aktualny_nazov = st.session_state.get('nazov_prazenia', f"Prazenie_PRO_{DNESNY_DATUM}")
    data_na_ulozenie = {
        "objednavky": st.session_state.aktualne_objednavky,
        "prazenie": st.session_state.priebeh_prazenia,
        "sklad": st.session_state.sklad,
        "expedicia": st.session_state.get("expedicia_rozpracovane", {})
    }
    log = (akcia, detail, sklad_pred) if akcia else None
    uspech, chyba = uloz_do_google_sheets(data_na_ulozenie, aktualny_nazov, historia=historia, log=log)
    if not uspech: st.toast(f"⚠️ Zlyhalo ukladanie: {chyba}", icon="❌")
    elif chyba: st.toast(f"⚠️ {chyba}", icon="⚠️")

def over_heslo(zadane):
    spravne = st.secrets.get("inventura_heslo", "")
    if not spravne:
        return None  # heslo nie je nastavené
    return hmac.compare_digest(str(zadane), str(spravne))

# --- AUTO-LOAD A INICIALIZÁCIA SKLADU ---
def inicializuj_sklad(nacitany_sklad):
    sklad = {t: {} for t in TYPY_SKLADU}
    sklad["minima"] = {}
    if nacitany_sklad:
        for t in TYPY_SKLADU + ["minima"]:
            sklad[t] = dict(nacitany_sklad.get(t, {}) or {})
    for sku in SKU_OBAL.values():
        sklad["obaly"].setdefault(sku, 0)
    for sku in SKU_ETIKETA.values():
        sklad["etikety"].setdefault(sku, 0)
    
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
        st.session_state.expedicia_rozpracovane = zaloha_dict.get("expedicia", {})
        if n_prazenia: st.session_state.nazov_prazenia = n_prazenia
        aktivne = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
        st.session_state.info_cloud = f"Synchronizované: {len(aktivne)} položiek | Posledná úprava: {cas_poslednej_upravy}"
        st.session_state.msg_uspech = True
    else:
        st.session_state.info_cloud = f"Chyba synchronizácie: {cas_poslednej_upravy}"
        st.session_state.msg_chyba = True
    st.session_state.pop("tabulka_objednavok", None)

# --- KOMPLETNÁ ZÁLOHA DO EXCELU (všetky stavy: objednávky, praženie, sklad, expedícia) ---
LIST_STAV_EXCEL = "_STAV"
EXCEL_KUSOK = 30000  # bunka v Exceli unesie max. 32 767 znakov

def vytvor_excel_stavu():
    stav = {
        "verzia": 1,
        "vytvorene": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "nazov_prazenia": st.session_state.get("nazov_prazenia", ""),
        "objednavky": st.session_state.aktualne_objednavky,
        "prazenie": st.session_state.priebeh_prazenia,
        "sklad": st.session_state.sklad,
        "expedicia": st.session_state.get("expedicia_rozpracovane", {}),
    }
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        wb = writer.book
        hl = wb.add_format({"bold": True, "bg_color": "#2B5098", "font_color": "white", "border": 1})

        def hárok(df, nazov):
            if df.empty: df = pd.DataFrame({"Info": ["(prázdne)"]})
            df.to_excel(writer, sheet_name=nazov, index=False)
            ws = writer.sheets[nazov]
            for c, col in enumerate(df.columns):
                ws.write(0, c, str(col), hl)
                ws.set_column(c, c, max(12, min(45, int(df[col].astype(str).map(len).max() if len(df) else 10) + 2)))
            ws.freeze_panes(1, 0)

        info = pd.DataFrame([
            {"Položka": "Identifikátor praženia", "Hodnota": stav["nazov_prazenia"]},
            {"Položka": "Záloha vytvorená", "Hodnota": stav["vytvorene"]},
            {"Položka": "Počet riadkov objednávok", "Hodnota": len(stav["objednavky"])},
            {"Položka": "Pozor", "Hodnota": "Na obnovu sa používa skrytý hárok _STAV. Úpravy v ostatných hárkoch sa pri načítaní neprenesú."},
        ])
        hárok(info, "Info")
        hárok(pd.DataFrame(stav["objednavky"]).drop(columns=["❌ Zmazať"], errors="ignore"), "Objednávky")
        hárok(pd.DataFrame([{"Zrno": z, "Dávky hotovo": v.get("davky_hotovo", 0), "Zelená (kg)": round(v.get("zelena_real", 0.0), 2),
                             "Upražená (kg)": round(v.get("uprazena_real", 0.0), 2), "Hotovo": v.get("hotovo", False)}
                            for z, v in stav["prazenie"].items()]), "Pražiareň")
        hárok(pd.DataFrame([{"SKU": k, "Názov": NAZVY_ZELENA.get(k, ""), "Stav (kg)": round(float(v), 2)} for k, v in stav["sklad"]["zelena"].items()]), "Sklad GC")
        hárok(pd.DataFrame([{"SKU": k, "Názov": NAZVY_UPRAZENA.get(k, ""), "Stav (kg)": round(float(v), 2)} for k, v in stav["sklad"]["uprazena"].items()]), "Sklad RC")
        hárok(pd.DataFrame([{"SKU": k, "Názov": NAZVY_ZABALENA.get(k, ""), "Stav (ks)": int(v)} for k, v in stav["sklad"]["zabalena"].items()]), "Sklad Výrobky")
        hárok(pd.DataFrame([{"SKU": k, "Názov": {**NAZVY_OBALY, **NAZVY_ETIKETY}.get(k, ""), "Stav (ks)": int(v),
                             "Minimum (ks)": int(stav["sklad"].get("minima", {}).get(k, 0))}
                            for t in ("obaly", "etikety") for k, v in stav["sklad"].get(t, {}).items()]), "Obaly a etikety")
        hárok(pd.DataFrame([{"Zákazník": z, "Krabica": i + 1, "SKU": s_, "Názov": NAZVY_ZABALENA.get(s_, s_), "Ks": n}
                            for z, r in stav["expedicia"].items() for i, k in enumerate(r.get("krabice", [])) for s_, n in k.items()]), "Expedícia rozprac.")

        text = json.dumps(stav, ensure_ascii=False)
        ws_s = wb.add_worksheet(LIST_STAV_EXCEL)
        ws_s.write(0, 0, "KIKIRIKI_STAV_V1")
        for i in range(0, len(text), EXCEL_KUSOK):
            ws_s.write_string(1 + i // EXCEL_KUSOK, 0, text[i:i + EXCEL_KUSOK])
        ws_s.hide()
    return buffer.getvalue()

def nacitaj_stav_z_excelu_callback():
    subor = st.session_state.get("upl_stav_excel")
    if subor is None:
        return
    try:
        df = pd.read_excel(io.BytesIO(subor.getvalue()), sheet_name=LIST_STAV_EXCEL, header=None, dtype=str)
        if str(df.iloc[0, 0]) != "KIKIRIKI_STAV_V1":
            raise ValueError("toto nie je záloha z Kikiriki PRO")
        stav = json.loads("".join(str(x) for x in df.iloc[1:, 0].dropna()))
    except Exception as e:
        st.session_state.msg_excel_stav = ("error", f"Súbor sa nepodarilo načítať: {e}")
        return
    # aktuálny stav najprv do histórie, aby sa dalo vrátiť
    auto_uloz(historia=True, akcia="Záloha pred načítaním Excelu", detail="Automatický snapshot")
    sklad_pred = copy.deepcopy(st.session_state.sklad)
    st.session_state.aktualne_objednavky = stav.get("objednavky", [])
    st.session_state.priebeh_prazenia = stav.get("prazenie", {})
    st.session_state.sklad = inicializuj_sklad(stav.get("sklad", {}))
    st.session_state.expedicia_rozpracovane = stav.get("expedicia", {})
    if stav.get("nazov_prazenia"):
        st.session_state.nazov_prazenia = stav["nazov_prazenia"]
    st.session_state.pop("tabulka_objednavok", None)
    auto_uloz(akcia="Načítanie stavu z Excelu", detail=f"Záloha z {stav.get('vytvorene', '?')} | {stav.get('nazov_prazenia', '')}", sklad_pred=sklad_pred)
    st.session_state.msg_excel_stav = ("success", f"Načítaný kompletný stav zo zálohy {stav.get('vytvorene', '')}. Predošlý stav je v histórii.")

def obnov_zo_zalohy_callback():
    zoznam = st.session_state.get("historia_zoznam", [])
    idx = st.session_state.get("vyber_zalohy")
    if idx is None or idx >= len(zoznam):
        return
    z = zoznam[idx]
    try:
        data = json.loads(z["data"])
        if isinstance(data, list):
            data = {"objednavky": data, "prazenie": {}, "sklad": {}}
    except Exception as e:
        st.session_state.msg_obnova = ("error", f"Zálohu sa nepodarilo prečítať: {e}")
        return

    # Aktuálny stav sa najprv uloží do histórie, aby sa dala obnova vrátiť
    auto_uloz(historia=True, akcia="Záloha pred obnovou", detail=f"Pred obnovou na {z['cas']}")
    sklad_pred = copy.deepcopy(st.session_state.sklad)

    st.session_state.aktualne_objednavky = data.get("objednavky", [])
    st.session_state.expedicia_rozpracovane = data.get("expedicia", {})
    st.session_state.priebeh_prazenia = data.get("prazenie", {})
    st.session_state.sklad = inicializuj_sklad(data.get("sklad", {}))
    if z.get("nazov"):
        st.session_state.nazov_prazenia = z["nazov"]
    st.session_state.pop("tabulka_objednavok", None)

    auto_uloz(akcia="Obnova zo zálohy", detail=f"Snapshot {z['cas']} | {z.get('nazov','')}", sklad_pred=sklad_pred)
    st.session_state.historia_zoznam = []
    st.session_state.potvrdenie_obnovy = False
    st.session_state.msg_obnova = ("success", f"Obnovené na stav z {z['cas']}. Predošlý stav je uložený v histórii.")
    st.session_state._po_obnove = True

if 'sklad' not in st.session_state:
    zaloha_dict, cas, n_prazenia = nacitaj_z_google_sheets()
    if zaloha_dict is not None:
        st.session_state.aktualne_objednavky = zaloha_dict.get("objednavky", [])
        st.session_state.priebeh_prazenia = zaloha_dict.get("prazenie", {})
        st.session_state.sklad = inicializuj_sklad(zaloha_dict.get("sklad", {}))
        st.session_state.expedicia_rozpracovane = zaloha_dict.get("expedicia", {})
        aktivne_start = [o for o in st.session_state.aktualne_objednavky if not o.get('❌ Zmazať', False)]
        st.session_state.info_cloud = f"Synchronizované: {len(aktivne_start)} položiek | Posledná úprava: {cas}"
    else:
        st.session_state.aktualne_objednavky = []
        st.session_state.priebeh_prazenia = {}
        st.session_state.sklad = inicializuj_sklad({})
        st.session_state.expedicia_rozpracovane = {}
        st.session_state.info_cloud = f"Sme offline / Tabuľka je prázdna. (Detail: {cas})"
    st.session_state.pociatocny_nazov = n_prazenia if n_prazenia else f"Prazenie_PRO_{DNESNY_DATUM}"

if 'nazov_prazenia' not in st.session_state:
    st.session_state.nazov_prazenia = st.session_state.get('pociatocny_nazov', f"Prazenie_PRO_{DNESNY_DATUM}")

if 'form_key' not in st.session_state: st.session_state.form_key = 0
def vynuluj_policka(): st.session_state.form_key += 1

# --- SPRÁVA: ZÁMOK (inventúra, log, obnova) ---
@st.dialog("🔒 Správa skladu", width="large")
def spravca_dialog():
    if st.session_state.pop("_po_obnove", False):
        st.rerun()
    if not st.session_state.get("admin_odomknute", False):
        if not st.secrets.get("inventura_heslo", ""):
            st.warning("Heslo nie je nastavené v Secrets (kľúč `inventura_heslo`).")
            return
        with st.form("form_heslo", clear_on_submit=True):
            heslo = st.text_input("Heslo:", type="password")
            ok = st.form_submit_button("Odomknúť", type="primary")
        if ok:
            if over_heslo(heslo):
                st.session_state.admin_odomknute = True
                st.rerun(scope="fragment")
            else:
                st.error("Nesprávne heslo.")
        return

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📦 Zavrieť a ísť na inventúru", use_container_width=True):
            st.rerun()
    with col_b:
        if st.button("🔒 Zamknúť", use_container_width=True):
            st.session_state.admin_odomknute = False
            st.rerun()
    st.caption("Inventúra je odomknutá v podzáložkách GC / RC / Výrobky v záložke Sklad.")

    tab_log, tab_obnova = st.tabs(["**📜 Log**", "**⏪ Obnova**"])
    with tab_log:
        st.caption("Každá akcia v appke = riadok v liste „Log“ v Google tabuľke. Najnovšie hore.")
        if st.button("Načítať / obnoviť log", key="btn_log"):
            try:
                st.session_state.log_df = nacitaj_log()
            except Exception as e:
                st.error(f"Log sa nepodarilo načítať: {e}")
        df_log = st.session_state.get("log_df")
        if df_log is not None:
            if df_log.empty:
                st.info("Log je zatiaľ prázdny.")
            else:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filtr_akcia = st.multiselect("Akcia:", sorted(df_log["Akcia"].unique()), key="filtr_akcia")
                with col_f2:
                    filtr_text = st.text_input("Hľadať (SKU, názov, odberateľ…):", key="filtr_text")
                df_view = df_log
                if filtr_akcia:
                    df_view = df_view[df_view["Akcia"].isin(filtr_akcia)]
                if filtr_text:
                    maska = df_view.apply(lambda r: filtr_text.lower() in " ".join(r.astype(str)).lower(), axis=1)
                    df_view = df_view[maska]
                st.caption(f"Zobrazených {min(len(df_view), 2000)} z {len(df_view)} riadkov.")
                st.dataframe(df_view.head(2000), use_container_width=True, hide_index=True, height=500)
                st.download_button("Stiahnuť log (.csv)", data=df_view.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"Kikiriki_Log_{DNESNY_DATUM}.csv", mime="text/csv")

    with tab_obnova:
        st.caption("Vráti appku do stavu z vybraného snapshotu. Aktuálny stav sa pred obnovou automaticky uloží do histórie, takže obnova sa dá vrátiť.")
        msg = st.session_state.pop("msg_obnova", None)
        if msg:
            (st.success if msg[0] == "success" else st.error)(msg[1])
        if st.button("Načítať zoznam záloh", key="btn_hist"):
            try:
                st.session_state.historia_zoznam = nacitaj_historiu()
            except Exception as e:
                st.error(f"Históriu sa nepodarilo načítať: {e}")
        zoznam = st.session_state.get("historia_zoznam", [])
        if zoznam:
            idx = st.selectbox("Vyber snapshot:", options=list(range(len(zoznam))),
                               format_func=lambda i: f"{zoznam[i]['cas']} | {zoznam[i]['nazov']}", key="vyber_zalohy")
            try:
                nahlad = json.loads(zoznam[idx]["data"])
                obj = nahlad.get("objednavky", []) if isinstance(nahlad, dict) else nahlad
                sklad_n = nahlad.get("sklad", {}) if isinstance(nahlad, dict) else {}
                c1, c2, c3 = st.columns(3)
                c1.metric("Objednávky", len([o for o in obj if not o.get("❌ Zmazať")]))
                c2.metric("Zelená spolu", f"{sum(sklad_n.get('zelena', {}).values()):.1f} kg")
                c3.metric("Sáčky v regáli", int(sum(sklad_n.get('zabalena', {}).values())))
            except Exception:
                st.warning("Náhľad tohto snapshotu sa nedá zobraziť.")
            st.checkbox("Rozumiem, že prepíšem aktuálny stav appky týmto snapshotom.", key="potvrdenie_obnovy")
            st.button("⏪ Obnoviť tento stav", type="primary", disabled=not st.session_state.get("potvrdenie_obnovy", False),
                      on_click=obnov_zo_zalohy_callback)
        elif "historia_zoznam" in st.session_state:
            st.info("História je zatiaľ prázdna.")


# --- HLAVIČKA A LOGO ---
def logo_html():
    import base64
    for subor, mime in (("logo.png", "image/png"), ("logo.svg", "image/svg+xml")):
        if os.path.exists(subor):
            with open(subor, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f"<div style='text-align:right;'><img src='data:{mime};base64,{b64}' style='width:110px;'></div>"
    return "<div style='text-align:right;'><span style='font-family: \"Barlow Condensed\", sans-serif; font-weight: 900; color: #2B5098; font-size: 1.8rem; letter-spacing: 2px;'>KIKIRIKI</span></div>"

col_head_left, col_head_lock, col_head_logo = st.columns([14, 1, 2], vertical_alignment="center")
with col_head_left:
    st.title("Kikiriki Roastery PRO")
    st.caption("Verzia 10.3 | Výroba, Sklad & ERP Kódy")
with col_head_lock:
    ikona = "🔓" if st.session_state.get("admin_odomknute", False) else "🔒"
    if st.button(ikona, key="btn_zamok", help="Inventúra, log a obnova"):
        spravca_dialog()
with col_head_logo:
    st.markdown(logo_html(), unsafe_allow_html=True)

msg_obn = st.session_state.pop("msg_obnova", None)
if msg_obn:
    (st.success if msg_obn[0] == "success" else st.error)(msg_obn[1])

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
        st.button("Načítať stav z Cloudu", type="secondary", use_container_width=True, on_click=nacitaj_vsetko_z_cloudu_callback)
    with col_save:
        if st.button("Uložiť aktuálny stav do Cloudu", type="primary", use_container_width=True):
            auto_uloz(historia=True, akcia="Ručné uloženie", detail="Snapshot do histórie")
            st.success("Aktuálny zoznam uložený (aj do histórie).")
            st.rerun()

    with st.expander("💾 Kompletná záloha do Excelu (objednávky, pražiareň, baliareň, sklad, expedícia)"):
        msg_xs = st.session_state.pop("msg_excel_stav", None)
        if msg_xs: (st.success if msg_xs[0] == "success" else st.error)(msg_xs[1])
        st.caption("Uloží všetko presne tak, ako to teraz je. Keď ho neskôr načítaš, pokračuješ tam, kde si skončil.")
        cx1, cx2 = st.columns(2)
        with cx1:
            st.download_button("💾 Stiahnuť kompletný stav (.xlsx)", data=vytvor_excel_stavu(),
                               file_name=f"Kikiriki_STAV_{st.session_state.nazov_prazenia}_{datetime.now().strftime('%Y-%m-%d_%H%M')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
        with cx2:
            st.file_uploader("Načítať stav zo zálohy:", type=["xlsx"], key="upl_stav_excel")
            st.button("📂 Obnoviť appku z tohto súboru", use_container_width=True, on_click=nacitaj_stav_z_excelu_callback,
                      disabled=st.session_state.get("upl_stav_excel") is None)

    st.divider()

    st.markdown("### Import údajov")
    nahraty_subor = st.file_uploader("Nahraj .xlsx súbor z tabuľky", type=["xlsx"])
    if nahraty_subor is not None:
        try:
            xl = pd.ExcelFile(nahraty_subor)
            df_import = xl.parse('Spracovane_Objednavky') if 'Spracovane_Objednavky' in xl.sheet_names else xl.parse(0)
            if st.button("Spracovať Excel a pridať objednávky", type="primary"):
                pocet_pred = len(st.session_state.aktualne_objednavky)
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
                nove = st.session_state.aktualne_objednavky[pocet_pred:]
                auto_uloz(akcia="Import z Excelu", detail=f"{len(nove)} riadkov ({nahraty_subor.name}): " + "; ".join(popis_obj(o) for o in nove))
                st.success("Dáta importované a uložené do cloudu.")
                st.rerun()
        except Exception as e:
            st.error("Chyba pri spracovaní Excelu.")

    st.divider()

    st.markdown("### Manuálny príjem objednávok")
    col1, col2 = st.columns(2)
    with col1:
        meno = st.text_input("Odberateľ:", placeholder="Meno zákazníka alebo prevádzky...")
        rezim = st.radio("Režim zadávania:", ["Podľa kávy", "Podľa gramáže", "Skladový BATCH (Dávka)"], horizontal=True, on_change=vynuluj_policka)

    if rezim == "Podľa kávy":
        with col1: kava = st.selectbox("Vyber kávu:", list(kavy_recepty.keys()), on_change=vynuluj_policka)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            col2_1, col2_2, col2_3 = st.columns(3)
            with col2_1: kusy_220 = st.number_input("220g (ks):", min_value=0, step=1, key=f"k_220_{st.session_state.form_key}")
            with col2_2: kusy_500 = st.number_input("500g (ks):", min_value=0, step=1, key=f"k_500_{st.session_state.form_key}")
            with col2_3: kusy_1000 = st.number_input("1000g (ks):", min_value=0, step=1, key=f"k_1000_{st.session_state.form_key}")

        if st.button("Zapísať do knihy", type="secondary"):
            pocet_pred = len(st.session_state.aktualne_objednavky)
            if kusy_220 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 220, "Kusy": kusy_220, "Zabalené (ks)": 0, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            if kusy_500 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 500, "Kusy": kusy_500, "Zabalené (ks)": 0, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            if kusy_1000 > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": kava, "Gramáž": 1000, "Kusy": kusy_1000, "Zabalené (ks)": 0, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            nove = st.session_state.aktualne_objednavky[pocet_pred:]
            auto_uloz(akcia="Nová objednávka", detail="; ".join(popis_obj(o) for o in nove))
            vynuluj_policka()
            st.rerun()
            
    elif rezim == "Podľa gramáže":
        with col1: gramaz = st.selectbox("Gramáž sáčku:", gramaze_list, on_change=vynuluj_policka)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            inputs_kavy = {}
            for k in kavy_recepty.keys(): inputs_kavy[k] = st.number_input(f"{k} (ks):", min_value=0, step=1, key=f"k_{k}_{st.session_state.form_key}")
        if st.button("Zapísať do knihy", type="secondary"):
            pocet_pred = len(st.session_state.aktualne_objednavky)
            for k, v in inputs_kavy.items():
                if v > 0: st.session_state.aktualne_objednavky.append({"Odberateľ": meno or "Neznámy", "Káva": k, "Gramáž": gramaz, "Kusy": v, "Zabalené (ks)": 0, "Potvrdene": False, "❌ Zmazať": False, "Sudy": False})
            nove = st.session_state.aktualne_objednavky[pocet_pred:]
            auto_uloz(akcia="Nová objednávka", detail="; ".join(popis_obj(o) for o in nove))
            vynuluj_policka()
            st.rerun()
            
    elif rezim == "Skladový BATCH (Dávka)":
        with st.container():
            st.info("Pridá dávky priamo do plánu praženia a následne do Skladu (Dóz). Tieto položky sa nebalia do sáčkov.")
            col_b1, col_b2 = st.columns(2)
            with col_b1: kava_batch = st.selectbox("Vyber zrno:", list(kavy_recepty.keys()), key=f"kava_b_{st.session_state.form_key}")
            with col_b2: davky_batch = st.number_input("Počet plných dávok (á 5kg zelenej):", min_value=1, step=1, key=f"davky_b_{st.session_state.form_key}")
            if st.button("Pridať BATCH", type="primary"):
                st.session_state.aktualne_objednavky.append({
                    "Odberateľ": "SKLAD (Dávka)", "Káva": kava_batch, "Gramáž": 0, "Kusy": davky_batch, "Zabalené (ks)": 0, "Potvrdene": True, "Sudy": True, "❌ Zmazať": False
                })
                auto_uloz(akcia="Nový BATCH (Dávka)", detail=f"{kava_batch}: {davky_batch} dávok")
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
                
            zmeny_knihy = diff_objednavok(st.session_state.aktualne_objednavky, novy_stav)
            if zmeny_knihy:
                st.session_state.aktualne_objednavky = novy_stav
                auto_uloz(akcia="Úprava knihy objednávok", detail="; ".join(zmeny_knihy))

            col_del1, col_del2 = st.columns([1, 1])
            with col_del1:
                if st.button("Odstrániť označené", type="secondary"):
                    zmazane = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') == True]
                    st.session_state.aktualne_objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
                    auto_uloz(akcia="Zmazanie objednávok", detail="; ".join(popis_obj(o) for o in zmazane))
                    st.rerun()
            with col_del2:
                if st.button("Vyčistiť stôl (Nový víkend)", type="secondary"):
                    # Pred vyčistením uložiť snapshot do histórie
                    pocet = len(st.session_state.aktualne_objednavky)
                    auto_uloz(historia=True)
                    st.session_state.aktualne_objednavky = []
                    st.session_state.priebeh_prazenia = {}
                    st.session_state.expedicia_rozpracovane = {}
                    auto_uloz(akcia="Vyčistenie stola", detail=f"Odstránených {pocet} riadkov + rozpracované krabice (stav pred je v histórii)")
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
                    if st.button(f"Potvrdiť {pridat_davky} dávok do Skladu", key=f"btn_praz_{zrno}", type="primary") and not je_duplicitny_klik(f"praz_{zrno}", pridat_davky):
                        sklad_pred = copy.deepcopy(st.session_state.sklad)
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

                        auto_uloz(akcia="Praženie", detail=f"{zrno}: +{pridat_davky} dávok ({davky_hotovo + pridat_davky}/{davky_plan})", sklad_pred=sklad_pred)
                        st.rerun()

                    if davky_hotovo > 0:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Vrátiť späť (Zrušiť všetko praženie tohto zrna z aktuálnej zmeny)", key=f"undo_{zrno}", type="secondary"):
                            sklad_pred = copy.deepcopy(st.session_state.sklad)
                            storno_zelena = stav_z_cloudu.get("zelena_real", 0.0)
                            storno_uprazena = stav_z_cloudu.get("uprazena_real", 0.0)
                            
                            gc_sku = SKU_ZELENA.get(zrno)
                            rc_sku = SKU_UPRAZENA.get(zrno)
                            if gc_sku: st.session_state.sklad["zelena"][gc_sku] += storno_zelena
                            if rc_sku: st.session_state.sklad["uprazena"][rc_sku] -= storno_uprazena
                            
                            st.session_state.priebeh_prazenia[zrno] = {
                                "davky_hotovo": 0, "zelena_real": 0.0, "uprazena_real": 0.0, "hotovo": False
                            }
                            auto_uloz(akcia="Storno praženia", detail=f"{zrno}: zrušených {davky_hotovo} dávok", sklad_pred=sklad_pred)
                            st.rerun()

# ========================================================
# TAB 3: BALENIE (ČISTÁ VÝROBA, zapisuje pevne do Skladu)
# ========================================================
with tab3:
    st.markdown("### Baliareň")
    
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
            RIADOK_SPOLU = '📦 SÁČKY SPOLU'
            sum_pivot_tab3.loc[RIADOK_SPOLU] = sum_pivot_tab3.sum(numeric_only=True)
            sum_pivot_tab3 = sum_pivot_tab3[['Etikety spolu', 220, 500, 1000]]
            sum_pivot_tab3.columns = ['Etikety spolu', '220 g', '500 g', '1000 g']
            sum_pivot_tab3.index.name = 'Káva'
            # Vlastné HTML: tučný je len stĺpec "Etikety spolu" a spodný riadok (globálne CSS by inak stučnilo všetko)
            N, B = "font-weight:400 !important;", "font-weight:800 !important;"
            bunka = "padding:6px 12px;border-bottom:1px solid rgba(43,80,152,0.15);"
            hl = "".join(f"<th style='{bunka}{N}text-align:{'left' if c == 'Káva' else 'right'};color:#2B5098;'>{c}</th>"
                         for c in ['Káva'] + list(sum_pivot_tab3.columns))
            telo = ""
            for kava_r, riadok in sum_pivot_tab3.iterrows():
                je_spolu = kava_r == RIADOK_SPOLU
                pozadie = "background:rgba(43,80,152,0.08);" if je_spolu else ""
                telo += f"<tr style='{pozadie}'><td style='{bunka}{B if je_spolu else N}'>{kava_r}</td>"
                for stlpec, hodnota in riadok.items():
                    tucne = je_spolu or stlpec == 'Etikety spolu'
                    text = f"Celkový počet etikiet: {int(hodnota)}" if (je_spolu and stlpec == 'Etikety spolu') else int(hodnota)
                    telo += f"<td style='{bunka}{B if tucne else N}text-align:right;'>{text}</td>"
                telo += "</tr>"
            st.markdown(f"<table style='width:100%;border-collapse:collapse;'><thead><tr>{hl}</tr></thead><tbody>{telo}</tbody></table>",
                        unsafe_allow_html=True)
        else: st.success("Všetky sáčky sú pripravené v regáli.")
            
        st.divider()

        # Zákazníci s neexpedovanými objednávkami (pre roletku)
        VSETCI = "Všetci zákazníci"
        zostava_zak = {}
        for o in aktivne_balenie:
            if o.get('Potvrdene'): continue
            zostava_zak[o['Odberateľ']] = zostava_zak.get(o['Odberateľ'], 0) + max(0, int(o['Kusy']) - int(o.get('Zabalené (ks)', 0)))
        moznosti_zak = [VSETCI] + sorted(zostava_zak)
        if st.session_state.get("balenie_zakaznik") not in moznosti_zak:
            st.session_state.balenie_zakaznik = VSETCI

        def popis_zakaznika(z):
            if z == VSETCI: return VSETCI
            return f"✅ {z} – nabalené" if zostava_zak[z] == 0 else f"{z} – zostáva {zostava_zak[z]} ks"

        col_ul, col_zak = st.columns([3, 2], vertical_alignment="bottom")
        with col_ul:
            st.markdown("#### 📦 Úlohy pre baliča (Sáčkovanie)")
        with col_zak:
            vybrany_zak = st.selectbox("Balím pre:", moznosti_zak, format_func=popis_zakaznika, key="balenie_zakaznik")

        msg_bal = st.session_state.pop("msg_balenie", None)
        if msg_bal: st.info(msg_bal)

        if vybrany_zak == VSETCI:
            plan_ulohy = plan_balenia
            prednost = None
        else:
            prednost = vybrany_zak
            plan_ulohy = {}
            for o in aktivne_balenie:
                if o['Odberateľ'] != vybrany_zak or o.get('Potvrdene'): continue
                kluc = f"{o['Káva']}_{o['Gramáž']}"
                if kluc not in plan_ulohy: plan_ulohy[kluc] = {"kava": o['Káva'], "gramaz": o['Gramáž'], "ciel": 0, "hotovo": 0}
                plan_ulohy[kluc]["ciel"] += int(o['Kusy'])
                plan_ulohy[kluc]["hotovo"] += int(o.get('Zabalené (ks)', 0))
            if zostava_zak.get(vybrany_zak, 0) == 0:
                st.success(f"✅ {vybrany_zak} je kompletne nabalený – môžeš ho expedovať.")

        def pridaj_sacky(k, g, pridavam, prednost=None):
            """Zapíše presne `pridavam` sáčkov. Najprv pokryje objednávky zákazníka `prednost`,
            potom ostatných. Vráti počet kusov navyše nad otvorené objednávky."""
            sklad_pred = copy.deepcopy(st.session_state.sklad)
            zvysok = pridavam
            objednavky = st.session_state.aktualne_objednavky
            poradie = sorted(range(len(objednavky)), key=lambda i: 0 if (prednost and objednavky[i].get('Odberateľ') == prednost) else 1)
            for idx_o in poradie:
                obj = objednavky[idx_o]
                if zvysok <= 0: break
                if obj.get('❌ Zmazať') or obj.get('Sudy') or obj.get('Potvrdene'): continue
                if obj['Káva'] == k and obj['Gramáž'] == g:
                    aktualne_v_obj = int(obj.get('Zabalené (ks)', 0))
                    potreba_v_obj = int(obj['Kusy']) - aktualne_v_obj
                    if potreba_v_obj > 0:
                        dam = min(zvysok, potreba_v_obj)
                        st.session_state.aktualne_objednavky[idx_o]['Zabalené (ks)'] = aktualne_v_obj + dam
                        zvysok -= dam

            # ZÁPIS DO PEVNÉHO SKLADU
            vaha_do_sackov = pridavam * g / 1000.0
            pc_sku = get_pc_sku(MENU_KAVY.get(k), g)
            st.session_state.sklad["zabalena"][pc_sku] = st.session_state.sklad["zabalena"].get(pc_sku, 0) + pridavam
            # Obalový materiál: 1 prázdny sáčok + 1 etiketa na každý zabalený kus
            ob_sku, et_sku = SKU_OBAL.get(g), SKU_ETIKETA.get(k)
            if ob_sku: st.session_state.sklad["obaly"][ob_sku] = int(st.session_state.sklad["obaly"].get(ob_sku, 0)) - pridavam
            if et_sku: st.session_state.sklad["etikety"][et_sku] = int(st.session_state.sklad["etikety"].get(et_sku, 0)) - pridavam
            if k in kavy_recepty:
                for zrno, podiel in kavy_recepty[k]["recept"].items():
                    zrno_sku = SKU_UPRAZENA.get(zrno)
                    if zrno_sku: st.session_state.sklad["uprazena"][zrno_sku] -= (vaha_do_sackov * podiel)

            detail = f"{k} {g}g: +{pridavam} ks ({pc_sku})" + (f" pre {prednost}" if prednost else "") + (f", z toho {zvysok} ks navyše" if zvysok > 0 else "")
            auto_uloz(akcia="Balenie", detail=detail, sklad_pred=sklad_pred)
            return zvysok

        kavy_na_balenie = sorted(list(set([v['kava'] for v in plan_ulohy.values()])))
        
        for kava in kavy_na_balenie:
            polozky_pre_kavu = [v for v in plan_ulohy.values() if v['kava'] == kava]
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
                    if chýba_ks > 0:
                        ob_s, et_s = SKU_OBAL.get(p['gramaz']), SKU_ETIKETA.get(p['kava'])
                        ma_ob = int(st.session_state.sklad["obaly"].get(ob_s, 0)); ma_et = int(st.session_state.sklad["etikety"].get(et_s, 0))
                        nedost = [f"sáčkov {p['gramaz']} g (máš {ma_ob})" if ma_ob < chýba_ks else "",
                                  f"etikiet {p['kava']} (máš {ma_et})" if ma_et < chýba_ks else ""]
                        nedost = [x for x in nedost if x]
                        if nedost: st.warning(f"⚠️ Na {chýba_ks} ks {p['kava']} {p['gramaz']} g nie je dosť " + " a ".join(nedost) + ".")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if chýba_ks <= 0: st.markdown(f"✅ **{p['gramaz']}g** sáčok - Vyrobených {p['hotovo']} / {p['ciel']} ks")
                        else: st.markdown(f"➡️ **{p['gramaz']}g** sáčok - Už vyrobené {p['hotovo']} ks (Chýba dorobiť **{chýba_ks} ks**)")
                    with col2:
                        if chýba_ks > 0:
                            with st.form(key=f"form_bag_{p['kava']}_{p['gramaz']}", clear_on_submit=True):
                                pocet_ks = st.number_input("Počet sáčkov (ks):", min_value=0, value=0, step=1, key=f"add_bag_{p['kava']}_{p['gramaz']}")
                                odoslat = st.form_submit_button("✅ Potvrdiť", use_container_width=True)
                            if odoslat and pocet_ks > 0:
                                if je_duplicitny_klik(f"bag_{p['kava']}_{p['gramaz']}", int(pocet_ks)):
                                    st.warning("Dvojklik zachytený – započítané len raz.")
                                else:
                                    navyse = pridaj_sacky(p['kava'], p['gramaz'], int(pocet_ks), prednost=prednost)
                                    if navyse > 0:
                                        st.session_state.msg_balenie = f"{navyse} ks navyše nad objednávky išlo do regálu ako voľný sklad."
                                    st.rerun()

# ========================================================
# TAB 4: SKLAD (GC / RC / Výrobky + Inventúra, Log, Obnova)
# ========================================================
def gramaz_z_pc(sku):
    try: return int(sku[2:sku.index("-")])
    except Exception: return 0

def zafarbi_zaporne(v):
    try: return "color: #C0392B; font-weight: 800;" if float(v) < 0 else ""
    except Exception: return ""

def inventura_editor(typ, jednotka, akcia, odomknute):
    if not odomknute:
        st.caption("🔒 Inventúru odomkneš zámkom 🔒 vedľa loga vpravo hore.")
        return
    with st.expander("🔒 Inventúra – ručne prepísať stav", expanded=False):
        st.warning("Úpravou v tabuľke natvrdo prepíšeš evidenčné stavy. Zmena sa zapíše do logu aj histórie.")
        je_ks = typ in ("zabalena", "obaly", "etikety")
        riadky = []
        for sku, hodnota in st.session_state.sklad[typ].items():
            h = int(hodnota) if je_ks else round(float(hodnota), 2)
            riadky.append({"SKU": sku, "Názov": nazov_sku(typ, sku), f"Systém ({jednotka})": h, f"Fyzicky ({jednotka})": h})
        ed = st.data_editor(pd.DataFrame(riadky), hide_index=True, use_container_width=True,
                            disabled=["SKU", "Názov", f"Systém ({jednotka})"], key=f"inv_editor_{typ}")
        if st.button(f"⚠️ Potvrdiť inventúru – {akcia}", type="primary", key=f"inv_btn_{typ}"):
            sklad_pred = copy.deepcopy(st.session_state.sklad)
            for row in ed.to_dict("records"):
                hodnota = row[f"Fyzicky ({jednotka})"]
                st.session_state.sklad[typ][row["SKU"]] = int(hodnota) if je_ks else float(hodnota)
            auto_uloz(historia=True, akcia=f"Inventúra – {akcia}", detail="Ručná korekcia stavu", sklad_pred=sklad_pred)
            st.rerun()

with tab4:
    st.markdown("### Sklad")

    odomknute = st.session_state.get("admin_odomknute", False)

    tab_gc, tab_rc, tab_pc, tab_ob = st.tabs(["**GC – Zelená káva**", "**RC – Upražená (dózy)**", "**Výrobky – Sáčky**", "**Obaly a etikety**"])

    # ---------- GC ----------
    with tab_gc:
        st.caption("Zelená káva vo vreciach. Stav sa napĺňa inventúrou, praženie ho automaticky znižuje.")
        df_gc = pd.DataFrame([{"SKU": sku, "Názov": NAZVY_ZELENA.get(sku, ""), "Stav (kg)": round(float(v), 2)}
                              for sku, v in st.session_state.sklad["zelena"].items()])
        c1, c2 = st.columns(2)
        c1.metric("Zelená spolu", f"{df_gc['Stav (kg)'].sum():.2f} kg")
        c2.metric("Druhov na sklade", int((df_gc["Stav (kg)"] > 0).sum()))
        st.dataframe(df_gc.style.map(zafarbi_zaporne, subset=["Stav (kg)"]).format({"Stav (kg)": "{:.2f}"}),
                     use_container_width=True, hide_index=True)
        inventura_editor("zelena", "kg", "GC Zelená", odomknute)

    # ---------- RC ----------
    with tab_rc:
        st.caption("Upražená, zatiaľ nezabalená káva v dózach. Praženie pridáva, balenie odoberá.")
        df_rc = pd.DataFrame([{"SKU": sku, "Názov": NAZVY_UPRAZENA.get(sku, ""), "Stav (kg)": round(float(v), 2)}
                              for sku, v in st.session_state.sklad["uprazena"].items()])
        c1, c2 = st.columns(2)
        c1.metric("V dózach spolu", f"{df_rc['Stav (kg)'].sum():.2f} kg")
        c2.metric("Plných dóz", int((df_rc["Stav (kg)"] > 0).sum()))
        st.dataframe(df_rc.style.map(zafarbi_zaporne, subset=["Stav (kg)"]).format({"Stav (kg)": "{:.2f}"}),
                     use_container_width=True, hide_index=True)
        inventura_editor("uprazena", "kg", "RC Dózy", odomknute)

    # ---------- VÝROBKY ----------
    with tab_pc:
        st.caption("Hotové zabalené sáčky na sklade. Balenie pridáva, expedícia odoberá.")
        rows_pc = []
        for sku, ks in st.session_state.sklad["zabalena"].items():
            g = gramaz_z_pc(sku)
            rows_pc.append({"SKU": sku, "Názov": NAZVY_ZABALENA.get(sku, ""), "Gramáž": g, "Stav (ks)": int(ks), "Váha (kg)": round(int(ks) * g / 1000.0, 2)})
        df_pc = pd.DataFrame(rows_pc)
        c1, c2, c3 = st.columns(3)
        c1.metric("Sáčkov spolu", int(df_pc["Stav (ks)"].sum()))
        c2.metric("Váha spolu", f"{df_pc['Váha (kg)'].sum():.2f} kg")
        c3.metric("Výrobkov na sklade", int((df_pc["Stav (ks)"] > 0).sum()))
        aj_nulove = st.toggle("Zobraziť aj výrobky s nulovým stavom", value=False, key="pc_aj_nulove")
        df_pc_view = df_pc if aj_nulove else df_pc[df_pc["Stav (ks)"] != 0]
        if df_pc_view.empty:
            st.info("Na sklade nie sú žiadne zabalené sáčky.")
        else:
            st.dataframe(df_pc_view.style.map(zafarbi_zaporne, subset=["Stav (ks)", "Váha (kg)"]).format({"Váha (kg)": "{:.2f}"}),
                         use_container_width=True, hide_index=True)
        inventura_editor("zabalena", "ks", "Výrobky", odomknute)

    # ---------- OBALY A ETIKETY ----------
    with tab_ob:
        st.caption("Prázdne sáčky a etikety. Každý zabalený kus v Baliarni automaticky odpíše 1 sáčok a 1 etiketu.")
        sk = st.session_state.sklad
        minima = sk.setdefault("minima", {})

        # potreba na ešte nezabalené otvorené objednávky
        potreba_ob, potreba_et = {}, {}
        for o in st.session_state.aktualne_objednavky:
            if o.get('❌ Zmazať') or o.get('Sudy') or o.get('Potvrdene'): continue
            chyba_zab = max(0, int(o.get('Kusy', 0)) - int(o.get('Zabalené (ks)', 0)))
            if not chyba_zab: continue
            ob_s, et_s = SKU_OBAL.get(o.get('Gramáž')), SKU_ETIKETA.get(o.get('Káva'))
            if ob_s: potreba_ob[ob_s] = potreba_ob.get(ob_s, 0) + chyba_zab
            if et_s: potreba_et[et_s] = potreba_et.get(et_s, 0) + chyba_zab

        def tabulka_mat(typ, nazvy, potreba):
            riadky = []
            for s_, v in sk[typ].items():
                stav = int(v); mn = int(minima.get(s_, 0)); pot = int(potreba.get(s_, 0))
                po_zabaleni = stav - pot
                if stav < 0 or po_zabaleni < 0: sig = "🔴 Chýba"
                elif mn and po_zabaleni < mn: sig = "🟠 Objednať"
                else: sig = "🟢 OK"
                riadky.append({"Stav": sig, "SKU": s_, "Názov": nazvy.get(s_, s_), "Na sklade (ks)": stav,
                               "Treba na otvorené obj.": pot, "Zostane po zabalení": po_zabaleni, "Minimum": mn,
                               "Dokúpiť (ks)": max(0, (mn - po_zabaleni) if mn else -po_zabaleni)})
            return pd.DataFrame(riadky)

        df_ob = tabulka_mat("obaly", NAZVY_OBALY, potreba_ob)
        df_et = tabulka_mat("etikety", NAZVY_ETIKETY, potreba_et)
        na_nakup = pd.concat([df_ob, df_et])
        na_nakup = na_nakup[na_nakup["Dokúpiť (ks)"] > 0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Prázdne sáčky spolu", int(df_ob["Na sklade (ks)"].sum()))
        c2.metric("Etikety spolu", int(df_et["Na sklade (ks)"].sum()))
        c3.metric("Položiek na nákup", len(na_nakup))
        if not na_nakup.empty:
            st.error("🛒 **Treba nakúpiť:** " + ", ".join(f"{r['Názov']} – {r['Dokúpiť (ks)']} ks" for _, r in na_nakup.iterrows()))

        farba = lambda v: ("color:#C0392B;font-weight:800;" if str(v).startswith("🔴") else ("color:#D35400;font-weight:800;" if str(v).startswith("🟠") else ""))
        st.markdown("##### Prázdne sáčky")
        st.dataframe(df_ob.style.map(farba, subset=["Stav"]).map(zafarbi_zaporne, subset=["Na sklade (ks)", "Zostane po zabalení"]),
                     use_container_width=True, hide_index=True)
        st.markdown("##### Etikety")
        aj_nul_et = st.toggle("Zobraziť aj etikety s nulovým stavom a bez potreby", value=True, key="et_aj_nulove")
        df_et_v = df_et if aj_nul_et else df_et[(df_et["Na sklade (ks)"] != 0) | (df_et["Treba na otvorené obj."] > 0)]
        st.dataframe(df_et_v.style.map(farba, subset=["Stav"]).map(zafarbi_zaporne, subset=["Na sklade (ks)", "Zostane po zabalení"]),
                     use_container_width=True, hide_index=True)

        # --- PRÍJEM (nákup) ---
        with st.expander("📥 Príjem na sklad (prišiel nákup)"):
            vsetky_mat = {**{s_: NAZVY_OBALY[s_] for s_ in sk["obaly"] if s_ in NAZVY_OBALY},
                          **{s_: NAZVY_ETIKETY[s_] for s_ in sk["etikety"] if s_ in NAZVY_ETIKETY}}
            with st.form("form_prijem_mat", clear_on_submit=True):
                p1, p2 = st.columns([3, 1])
                with p1: mat_sku = st.selectbox("Položka:", list(vsetky_mat), format_func=lambda x: f"{vsetky_mat[x]} ({x})")
                with p2: mat_ks = st.number_input("Prijaté (ks):", min_value=0, step=50)
                poznamka = st.text_input("Poznámka (dodávateľ, faktúra):")
                ok_prijem = st.form_submit_button("📥 Naskladniť", type="primary")
            if ok_prijem and mat_ks > 0:
                if not je_duplicitny_klik(f"prijem_{mat_sku}", int(mat_ks)):
                    sklad_pred = copy.deepcopy(sk)
                    typ_m = "obaly" if mat_sku in sk["obaly"] else "etikety"
                    sk[typ_m][mat_sku] = int(sk[typ_m].get(mat_sku, 0)) + int(mat_ks)
                    auto_uloz(historia=True, akcia="Príjem obalov/etikiet", detail=f"{vsetky_mat[mat_sku]}: +{int(mat_ks)} ks" + (f" | {poznamka}" if poznamka else ""), sklad_pred=sklad_pred)
                    st.session_state.msg_prijem = f"📥 Naskladnené: {vsetky_mat[mat_sku]} +{int(mat_ks)} ks"
                    st.rerun()
        msg_pr = st.session_state.pop("msg_prijem", None)
        if msg_pr: st.success(msg_pr)

        # --- MINIMÁ (kedy nakúpiť) ---
        if odomknute:
            with st.expander("⚙️ Minimálne zásoby (od akého stavu hlásiť nákup)"):
                df_min = pd.DataFrame([{"SKU": s_, "Názov": {**NAZVY_OBALY, **NAZVY_ETIKETY}.get(s_, s_), "Minimum (ks)": int(minima.get(s_, 0))}
                                       for s_ in list(sk["obaly"]) + list(sk["etikety"])])
                ed_min = st.data_editor(df_min, hide_index=True, use_container_width=True, disabled=["SKU", "Názov"], key="ed_minima")
                if st.button("💾 Uložiť minimá", key="btn_minima"):
                    for r_ in ed_min.to_dict("records"):
                        minima[r_["SKU"]] = int(r_["Minimum (ks)"] or 0)
                    auto_uloz(akcia="Nastavenie miním", detail="; ".join(f"{k}={v}" for k, v in minima.items() if v))
                    st.rerun()
        inventura_editor("obaly", "ks", "Prázdne sáčky", odomknute)
        inventura_editor("etikety", "ks", "Etikety", odomknute)


# ========================================================
# TAB 5: EXPEDÍCIA (LOGISTIKA)
# ========================================================
with tab5:
    aktivne = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True and not o.get('Sudy', False)]
    cakajuce_expedicia = [o for o in aktivne if not o.get('Potvrdene')]
    hotove_expedicia = [o for o in aktivne if o.get('Potvrdene')]
    if "expedicia_rozpracovane" not in st.session_state:
        st.session_state.expedicia_rozpracovane = {}
    rozpr = st.session_state.expedicia_rozpracovane
    regal = st.session_state.sklad["zabalena"]

    def expeduj(odb, mnozstva, detail_extra="", mimo_objednavky=None, zrusit_zvysok=False):
        """mnozstva: {index_v_knihe: ks}. Plný riadok -> odoslaný. Čiastočný -> odoslaná časť + zvyšok,
        ktorý ostane otvorený, alebo sa zruší (zrusit_zvysok=True, zákazník dostane menej).
        mimo_objednavky: {pc_sku: ks} náhrada/navyše – pridá sa ako nový odoslaný riadok."""
        sklad_pred = copy.deepcopy(st.session_state.sklad)
        povodne = st.session_state.aktualne_objednavky
        nova_kniha, odoslane, zrusene = [], [], []
        for i, o in enumerate(povodne):
            otvoreny_odb = (o.get('Odberateľ') == odb and not o.get('Potvrdene') and not o.get('❌ Zmazať') and not o.get('Sudy'))
            n = int(mnozstva.get(i, 0))
            if n <= 0:
                if otvoreny_odb and zrusit_zvysok:
                    zrusene.append(o); continue
                nova_kniha.append(o); continue
            kusy = int(o['Kusy'])
            n = min(n, kusy)
            pc_sku = get_pc_sku(MENU_KAVY.get(o['Káva']), o['Gramáž'])
            st.session_state.sklad["zabalena"][pc_sku] = st.session_state.sklad["zabalena"].get(pc_sku, 0) - n
            if n == kusy:
                o = dict(o); o['Zabalené (ks)'] = kusy; o['Potvrdene'] = True
                nova_kniha.append(o)
            else:
                odoslana_cast = dict(o); odoslana_cast.update({'Kusy': n, 'Zabalené (ks)': n, 'Potvrdene': True})
                nova_kniha.append(odoslana_cast)
                zvysok = dict(o); zvysok.update({'Kusy': kusy - n, 'Zabalené (ks)': max(0, int(o.get('Zabalené (ks)', 0)) - n)})
                if zrusit_zvysok: zrusene.append(zvysok)
                else: nova_kniha.append(zvysok)
            odoslane.append({**o, 'Kusy': n})
        for pc_sku, n in (mimo_objednavky or {}).items():
            if n <= 0 or pc_sku not in PC_NA_KAVU: continue
            kava_m, g_m = PC_NA_KAVU[pc_sku]
            st.session_state.sklad["zabalena"][pc_sku] = st.session_state.sklad["zabalena"].get(pc_sku, 0) - n
            novy = {"Odberateľ": odb, "Káva": kava_m, "Gramáž": g_m, "Kusy": n, "Zabalené (ks)": n,
                    "Potvrdene": True, "Sudy": False, "❌ Zmazať": False, "Poznámka": "mimo objednávky"}
            nova_kniha.append(novy)
            odoslane.append(novy)
        st.session_state.aktualne_objednavky = nova_kniha
        st.session_state.pop("tabulka_objednavok", None)
        celkovo = sum(int(o['Kusy']) for o in povodne if o.get('Odberateľ') == odb and not o.get('Potvrdene') and not o.get('❌ Zmazať') and not o.get('Sudy'))
        akcia = "Expedícia" if (sum(mnozstva.values()) >= celkovo and not zrusene) else ("Expedícia so zmenou" if zrusene or mimo_objednavky else "Čiastočná expedícia")
        detail = "; ".join(popis_obj(o) for o in odoslane)
        if zrusene: detail += " | ZRUŠENÉ (zákazník dostal menej): " + "; ".join(popis_obj(o) for o in zrusene)
        if mimo_objednavky: detail += " | MIMO OBJEDNÁVKY: " + ", ".join(f"{n}× {k}" for k, n in mimo_objednavky.items())
        if detail_extra: detail += f" | {detail_extra}"
        auto_uloz(akcia=akcia, detail=detail, sklad_pred=sklad_pred)

    def stav_odb(odb):
        """Riadky zákazníka zoskupené podľa SKU: objednané, zabalené, v regáli, indexy riadkov v knihe."""
        polozky = {}
        for i, o in enumerate(st.session_state.aktualne_objednavky):
            if o.get('Odberateľ') != odb or o.get('Potvrdene') or o.get('❌ Zmazať') or o.get('Sudy'): continue
            sku = get_pc_sku(MENU_KAVY.get(o['Káva']), o['Gramáž'])
            p = polozky.setdefault(sku, {"sku": sku, "kava": o['Káva'], "gramaz": o['Gramáž'], "objednane": 0, "zabalene": 0, "indexy": []})
            p["objednane"] += int(o['Kusy'])
            p["zabalene"] += min(int(o.get('Zabalené (ks)', 0)), int(o['Kusy']))
            p["indexy"].append(i)
        return polozky

    def rozpr_odb(odb):
        r = rozpr.setdefault(odb, {"krabice": []})
        # prechod zo staršieho formátu (otvorená "aktualna" krabica)
        if r.get("aktualna"):
            r.setdefault("krabice", []).append(r["aktualna"])
        r.pop("aktualna", None)
        r.setdefault("krabice", [])
        return r

    def vybrane_spolu(r, sku):
        return sum(k.get(sku, 0) for k in r["krabice"])

    def ma_rozpracovane(z):
        return any(sum(k.values()) for k in rozpr.get(z, {}).get("krabice", [])) or bool(rozpr.get(z, {}).get("aktualna"))

    # --- callbacky (bežia pred prekreslením, takže sa každé kliknutie započíta presne raz) ---
    def cb_pridaj(odb, sku, max_mozne):
        kluc = f"exp_pocet_{odb}_{sku}"
        n = int(st.session_state.get(kluc, 0) or 0)
        r = rozpr_odb(odb)
        n = min(n, max(0, max_mozne - vybrane_spolu(r, sku)))
        if n > 0:
            idx = int(st.session_state.get(f"exp_krabica_{odb}", 0))
            if idx >= len(r["krabice"]):
                r["krabice"].append({}); idx = len(r["krabice"]) - 1
            r["krabice"][idx][sku] = r["krabice"][idx].get(sku, 0) + n
            st.session_state[f"exp_krabica_{odb}"] = idx
            st.session_state.msg_exp = f"➕ {n}× {NAZVY_ZABALENA.get(sku, sku)} → krabica č. {idx + 1}"
            auto_uloz()
        st.session_state[kluc] = 0

    def cb_uber(odb, idx, sku, vsetko=False):
        r = rozpr_odb(odb)
        if idx < len(r["krabice"]) and sku in r["krabice"][idx]:
            r["krabice"][idx][sku] = 0 if vsetko else r["krabice"][idx][sku] - 1
            if r["krabice"][idx][sku] <= 0: r["krabice"][idx].pop(sku)
            auto_uloz()

    def cb_zmaz_krabicu(odb, idx):
        r = rozpr_odb(odb)
        if idx < len(r["krabice"]):
            r["krabice"].pop(idx)
            st.session_state[f"exp_krabica_{odb}"] = max(0, len(r["krabice"]) - 1)
            auto_uloz()

    def cb_zrus(odb):
        rozpr.pop(odb, None)
        st.session_state.pop(f"exp_krabica_{odb}", None)
        auto_uloz()

    # --- HLAVIČKA S ROLETKOU ---
    NIKTO = "— vyber zákazníka —"
    odberatelia = sorted(set(o['Odberateľ'] for o in cakajuce_expedicia))

    # Upratanie: krabice zákazníkov, ktorí už nemajú žiadnu otvorenú objednávku (napr. zmazané objednávky)
    osirele = [z for z in list(rozpr) if z not in odberatelia]
    if osirele:
        for z in osirele:
            rozpr.pop(z, None)
            st.session_state.pop(f"exp_krabica_{z}", None)
        auto_uloz(akcia="Expedícia – upratanie krabíc", detail="Bez otvorených objednávok: " + ", ".join(osirele))

    def cb_reset_expedicie():
        pocet = len([z for z in rozpr if ma_rozpracovane(z)])
        rozpr.clear()
        for k in [k for k in st.session_state.keys() if str(k).startswith("exp_krabica_")]:
            st.session_state.pop(k, None)
        st.session_state.exp_reset_potvrd = False
        auto_uloz(akcia="Expedícia – reset krabíc", detail=f"Vymazané rozpracované krabice ({pocet} zákazníkov)")
        st.session_state.msg_exp_hotovo = "🗑️ Všetky rozpracované krabice boli vymazané. Sklad (regál) sa nemenil."
    def popis_odb(z):
        if z == NIKTO: return NIKTO
        st_o = stav_odb(z)
        obj = sum(p["objednane"] for p in st_o.values()); zab = sum(p["zabalene"] for p in st_o.values())
        ik = "✅" if zab >= obj else ("🟡" if zab > 0 else "⏳")
        rozpr_ik = " · 📦 rozpracované" if ma_rozpracovane(z) else ""
        return f"{ik} {z} – zabalené {zab}/{obj} ks{rozpr_ik}"
    moznosti = [NIKTO] + odberatelia
    if st.session_state.get("exp_zakaznik") not in moznosti:
        st.session_state.exp_zakaznik = NIKTO

    col_h, col_r = st.columns([3, 2], vertical_alignment="bottom")
    with col_h:
        st.markdown("### Expedícia (Kuriér)")
    with col_r:
        odb = st.selectbox("Zákazník:", moznosti, format_func=popis_odb, key="exp_zakaznik", disabled=not odberatelia)

    msg_hotovo = st.session_state.pop("msg_exp_hotovo", None)
    if msg_hotovo: st.success(msg_hotovo)

    if any(ma_rozpracovane(z) for z in rozpr):
        with st.expander("🗑️ Reset expedície – vymazať všetky rozpracované krabice"):
            st.caption("Vymaže krabice všetkých zákazníkov. Objednávky ani regál sa nemenia – nič sa neodošle.")
            st.checkbox("Áno, chcem vymazať všetky rozpracované krabice.", key="exp_reset_potvrd")
            st.button("🗑️ Vymazať všetky krabice", key="exp_reset_btn", on_click=cb_reset_expedicie,
                      disabled=not st.session_state.get("exp_reset_potvrd", False))

    if not cakajuce_expedicia:
        st.success("Všetky zákazky sú expedované.")
    elif odb == NIKTO:
        st.info("Vyber zákazníka v roletke vpravo hore.")
        prehlad = []
        for z in odberatelia:
            st_o = stav_odb(z)
            prehlad.append({"Zákazník": z, "Objednané (ks)": sum(p["objednane"] for p in st_o.values()),
                            "Zabalené (ks)": sum(p["zabalene"] for p in st_o.values()),
                            "Rozpracované krabice": len([k for k in rozpr.get(z, {}).get("krabice", []) if k])})
        st.dataframe(pd.DataFrame(prehlad), hide_index=True, use_container_width=True)
    else:
        polozky = stav_odb(odb)
        r = rozpr_odb(odb)
        krabice = r["krabice"]
        k_mimo = f"exp_mimo_{odb}"
        # položky mimo objednávky (náhrada / navyše): už vybrané v krabiciach + pri zapnutom prepínači všetko z regálu
        pol = dict(polozky)
        skus_mimo = {s_ for k in krabice for s_ in k if s_ not in polozky}
        if st.session_state.get(k_mimo, False):
            skus_mimo |= {s_ for s_, ks in regal.items() if int(ks) > 0 and s_ not in polozky and s_ in PC_NA_KAVU}
        for s_ in skus_mimo:
            kava_m, g_m = PC_NA_KAVU.get(s_, (s_, 0))
            pol[s_] = {"sku": s_, "kava": kava_m, "gramaz": g_m, "objednane": 0, "zabalene": 0, "indexy": [], "mimo": True}

        def limit_sku(s_):
            v_reg = int(regal.get(s_, 0))
            return v_reg if pol[s_].get("mimo") else max(0, min(pol[s_]["objednane"], v_reg))

        obj_spolu = sum(p["objednane"] for p in polozky.values())
        vybrane_vsetko = sum(vybrane_spolu(r, s_) for s_ in polozky)
        vybrane_mimo = sum(vybrane_spolu(r, s_) for s_ in pol if pol[s_].get("mimo"))

        c1, c2, c3 = st.columns(3)
        c1.metric("Objednané", f"{obj_spolu} ks")
        c2.metric("Vybrané do krabíc", f"{vybrane_vsetko} ks", delta=f"+{vybrane_mimo} mimo obj." if vybrane_mimo else None, delta_color="off")
        c3.metric("Krabíc", len([k for k in krabice if k]))

        # ---------- VÝBER: krabica + krížové filtre káva / gramáž ----------
        st.markdown("#### 📦 Čo dávam do krabice")
        VSETKY = "Všetky"
        def zostava_sku(s_):
            if pol[s_].get("mimo"): return max(0, int(regal.get(s_, 0)) - vybrane_spolu(r, s_))
            return pol[s_]["objednane"] - vybrane_spolu(r, s_)

        k_krab, k_kava, k_gram, k_hotove = f"exp_krabica_{odb}", f"exp_kava_{odb}", f"exp_gramaz_{odb}", f"exp_hotove_{odb}"
        aj_hotove = st.session_state.get(k_hotove, False)
        kandidati = [s_ for s_ in pol if aj_hotove or zostava_sku(s_) > 0]

        moznosti_krab = list(range(len(krabice) + 1))
        if st.session_state.get(k_krab) not in moznosti_krab:
            st.session_state[k_krab] = max(0, len(krabice) - 1) if krabice else 0

        # krížové filtre: káva ponúka len kávy s vybranou gramážou a naopak
        vyb_kava = st.session_state.get(k_kava, VSETKY)
        vyb_gram = st.session_state.get(k_gram, VSETKY)
        kavy_moz = sorted({pol[s_]["kava"] for s_ in kandidati if vyb_gram == VSETKY or pol[s_]["gramaz"] == vyb_gram})
        gram_moz = sorted({pol[s_]["gramaz"] for s_ in kandidati if vyb_kava == VSETKY or pol[s_]["kava"] == vyb_kava})
        if vyb_kava != VSETKY and vyb_kava not in kavy_moz: st.session_state[k_kava] = VSETKY
        if vyb_gram != VSETKY and vyb_gram not in gram_moz: st.session_state[k_gram] = VSETKY
        vyb_kava = st.session_state.get(k_kava, VSETKY); vyb_gram = st.session_state.get(k_gram, VSETKY)
        kavy_moz = sorted({pol[s_]["kava"] for s_ in kandidati if vyb_gram == VSETKY or pol[s_]["gramaz"] == vyb_gram})
        gram_moz = sorted({pol[s_]["gramaz"] for s_ in kandidati if vyb_kava == VSETKY or pol[s_]["kava"] == vyb_kava})

        def zost_kava(k):
            return sum(zostava_sku(s_) for s_ in pol if pol[s_]["kava"] == k and (vyb_gram == VSETKY or pol[s_]["gramaz"] == vyb_gram))
        def zost_gram(g):
            return sum(zostava_sku(s_) for s_ in pol if pol[s_]["gramaz"] == g and (vyb_kava == VSETKY or pol[s_]["kava"] == vyb_kava))

        f1, f2, f3, f4 = st.columns([1.6, 2, 1.6, 1.4], vertical_alignment="bottom")
        with f1:
            st.selectbox("Krabica:", moznosti_krab, key=k_krab,
                         format_func=lambda i: f"Krabica č. {i+1} ({sum(krabice[i].values())} ks)" if i < len(krabice) else f"➕ Nová krabica č. {i+1}")
        with f2:
            st.selectbox("Káva:", [VSETKY] + kavy_moz, key=k_kava,
                         format_func=lambda k: k if k == VSETKY else f"{k} – zostáva {zost_kava(k)} ks")
        with f3:
            st.selectbox("Gramáž:", [VSETKY] + gram_moz, key=k_gram,
                         format_func=lambda g: g if g == VSETKY else f"{g} g – zostáva {zost_gram(g)} ks")
        with f4:
            st.toggle("Aj hotové", key=k_hotove, help="Zobrazí aj položky, ktoré sú už celé v krabiciach")
            st.toggle("Mimo objednávky", key=k_mimo, help="Náhrada alebo navyše: ponúkne všetko, čo je v regáli, aj keď to zákazník nemá objednané")

        zobrazene = sorted([s_ for s_ in kandidati
                            if (vyb_kava == VSETKY or pol[s_]["kava"] == vyb_kava)
                            and (vyb_gram == VSETKY or pol[s_]["gramaz"] == vyb_gram)],
                           key=lambda s_: (bool(pol[s_].get("mimo")), pol[s_]["kava"], pol[s_]["gramaz"]))
        cielova = st.session_state.get(k_krab, 0)
        st.caption(f"Pridávaš do: **{'Krabica č. ' + str(cielova + 1) if cielova < len(krabice) else '➕ Nová krabica č. ' + str(cielova + 1)}**")

        if not zobrazene:
            st.success("Pre tento filter už nič nezostáva – všetko je v krabiciach.")
        for s_ in zobrazene:
            p_ = pol[s_]
            v_regali = int(regal.get(s_, 0))
            vyb = vybrane_spolu(r, s_)
            max_mozne = limit_sku(s_)
            mozno_pridat = max(0, max_mozne - vyb)
            je_mimo = bool(p_.get("mimo"))
            ca, cb, cc, cd = st.columns([3.2, 3, 1.5, 1.3], vertical_alignment="bottom")
            with ca:
                ikona_r = "➕" if je_mimo else ("✅" if vyb >= p_['objednane'] else "➡️")
                st.markdown(f"{ikona_r} **{p_['kava']} {p_['gramaz']}g**  \n<small>{s_}{' · mimo objednávky' if je_mimo else ''}</small>", unsafe_allow_html=True)
            with cb:
                upoz = " · ⚠️ treba dobaliť" if (not je_mimo and mozno_pridat == 0 and vyb < p_["objednane"]) else ""
                vyb_txt = f"Vybrané **{vyb}** (náhrada / navyše)" if je_mimo else f"Vybrané **{vyb} / {p_['objednane']}**"
                st.markdown(f"{vyb_txt}  \n<small>v regáli {v_regali} · môžeš pridať {mozno_pridat}{upoz}</small>", unsafe_allow_html=True)
            with cc:
                st.number_input("Počet (ks):", min_value=0, max_value=mozno_pridat, step=1,
                                key=f"exp_pocet_{odb}_{s_}", disabled=mozno_pridat == 0)
            with cd:
                st.button("✅ Potvrdiť", key=f"exp_potvrd_{odb}_{s_}", type="primary", use_container_width=True,
                          on_click=cb_pridaj, args=(odb, s_, max_mozne), disabled=mozno_pridat == 0)

        msg_exp = st.session_state.pop("msg_exp", None)
        if msg_exp: st.toast(msg_exp)

        # ---------- PREHĽAD SKU ----------
        with st.expander("📋 Prehľad objednávky zákazníka", expanded=False):
            prehlad = []
            for s_, p in sorted(polozky.items(), key=lambda x: (x[1]["kava"], x[1]["gramaz"])):
                vyb = vybrane_spolu(r, s_)
                prehlad.append({"": "✅" if vyb >= p["objednane"] else ("🟡" if vyb else "⏳"),
                                "Káva": p["kava"], "Gramáž": p["gramaz"], "SKU": s_, "Objednané": p["objednane"],
                                "Vybrané": vyb, "Zostáva": p["objednane"] - vyb, "V regáli": int(regal.get(s_, 0))})
            for s_ in sorted(s_ for s_ in pol if pol[s_].get("mimo") and vybrane_spolu(r, s_) > 0):
                prehlad.append({"": "➕", "Káva": pol[s_]["kava"], "Gramáž": pol[s_]["gramaz"], "SKU": s_, "Objednané": 0,
                                "Vybrané": vybrane_spolu(r, s_), "Zostáva": 0, "V regáli": int(regal.get(s_, 0))})
            st.dataframe(pd.DataFrame(prehlad), hide_index=True, use_container_width=True)

        # ---------- OBSAH KRABÍC ----------
        if any(krabice):
            st.markdown("#### Obsah krabíc")
            for i_k, k in enumerate(krabice):
                with st.container(border=True):
                    h1, h2 = st.columns([5, 1.3], vertical_alignment="center")
                    h1.markdown(f"**Krabica č. {i_k + 1}** – {sum(k.values())} ks")
                    h2.button("🗑️ Vymazať krabicu", key=f"exp_zmaz_k_{odb}_{i_k}", on_click=cb_zmaz_krabicu, args=(odb, i_k), use_container_width=True)
                    if not k:
                        st.caption("Prázdna krabica.")
                    for s_, n in sorted(k.items()):
                        r1, r2, r3 = st.columns([5, 0.8, 0.8], vertical_alignment="center")
                        r1.markdown(f"{n}× {NAZVY_ZABALENA.get(s_, s_)} <small>({s_})</small>", unsafe_allow_html=True)
                        r2.button("↩️", key=f"exp_uber_{odb}_{i_k}_{s_}", on_click=cb_uber, args=(odb, i_k, s_), help="Vybrať 1 ks späť", use_container_width=True)
                        r3.button("✖", key=f"exp_uber_all_{odb}_{i_k}_{s_}", on_click=cb_uber, args=(odb, i_k, s_, True), help="Vybrať všetky kusy tohto SKU z krabice", use_container_width=True)
            st.caption("Rozpracované krabice sa ukladajú do cloudu pri každom potvrdení – prestávka nič nepokazí.")

        st.divider()
        chyby = [f"{s_}: vybrané {vybrane_spolu(r, s_)} ks, v regáli je len {int(regal.get(s_, 0))} ks."
                 for s_ in pol if vybrane_spolu(r, s_) > int(regal.get(s_, 0))]
        for ch in chyby: st.error(ch)
        plne_krabice = [k for k in krabice if k]
        zvysok_ks = max(0, obj_spolu - vybrane_vsetko)
        zrusit_zvysok = False
        if zvysok_ks > 0 and (vybrane_vsetko + vybrane_mimo) > 0:
            volba = st.radio(f"Čo so zvyškom objednávky ({zvysok_ks} ks), ktorý nejde v tejto zásielke?",
                             ["Nechať otvorený – dobalíme a pošleme neskôr", "Zrušiť – zákazník dostane menej"],
                             key=f"exp_zvysok_{odb}", horizontal=True)
            zrusit_zvysok = volba.startswith("Zrušiť")
            if zrusit_zvysok:
                st.warning(f"Zvyšných {zvysok_ks} ks sa z objednávky natrvalo odstráni (zapíše sa do logu). Už zabalené sáčky ostanú v regáli ako voľný sklad.")
        spolu_odoslat = vybrane_vsetko + vybrane_mimo
        if zvysok_ks == 0:
            popis_btn = f"🚚 Expedovať všetko ({spolu_odoslat} ks, {len(plne_krabice)} krab.)"
        elif zrusit_zvysok:
            popis_btn = f"🚚 Expedovať {spolu_odoslat} ks a zvyšok zrušiť ({len(plne_krabice)} krab.)"
        else:
            popis_btn = f"🚚 Expedovať čiastočne ({vybrane_vsetko} z {obj_spolu} ks, {len(plne_krabice)} krab.)"
        if vybrane_mimo:
            popis_btn += f" · +{vybrane_mimo} mimo obj."
        e1, e2 = st.columns([3, 1])
        with e1:
            if st.button(popis_btn, key=f"exp_odosli_{odb}", type="primary", disabled=bool(chyby) or spolu_odoslat == 0, use_container_width=True):
                if not je_duplicitny_klik(f"exp_{odb}", spolu_odoslat):
                    mnozstva = {}
                    for s_, p in polozky.items():
                        zostava = vybrane_spolu(r, s_)
                        for i in p["indexy"]:
                            if zostava <= 0: break
                            n = min(zostava, int(st.session_state.aktualne_objednavky[i]['Kusy']))
                            mnozstva[i] = n; zostava -= n
                    popis_krabic = "; ".join(f"Krabica {j}: " + ", ".join(f"{n}× {s_}" for s_, n in sorted(k.items()))
                                             for j, k in enumerate(plne_krabice, start=1))
                    rozpr.pop(odb, None)
                    st.session_state.pop(k_krab, None)
                    mimo = {s_: vybrane_spolu(r, s_) for s_ in pol if pol[s_].get("mimo") and vybrane_spolu(r, s_) > 0}
                    expeduj(odb, mnozstva, detail_extra=popis_krabic, mimo_objednavky=mimo, zrusit_zvysok=zrusit_zvysok)
                    st.session_state.msg_exp_hotovo = (f"🚚 {odb}: odoslaných {spolu_odoslat} ks v {len(plne_krabice)} krabiciach."
                                                       + (f" Zrušených {zvysok_ks} ks z objednávky." if zrusit_zvysok else ""))
                    st.rerun()
        with e2:
            st.button("🗑️ Zrušiť rozpracované", key=f"exp_zrus_{odb}", on_click=cb_zrus, args=(odb,),
                      disabled=not ma_rozpracovane(odb), use_container_width=True)

    if hotove_expedicia:
        st.divider()
        with st.expander("🚚 Odoslané zásielky (Archív)"):
            for i, o in enumerate(st.session_state.aktualne_objednavky):
                if o.get('Potvrdene') and not o.get('❌ Zmazať'):
                    def revert_expedicia_callback(idx=i):
                        val = st.session_state[f"rev_{idx}"]
                        sklad_pred = copy.deepcopy(st.session_state.sklad)
                        st.session_state.aktualne_objednavky[idx]['Potvrdene'] = val
                        obj = st.session_state.aktualne_objednavky[idx]
                        rc_kod = MENU_KAVY.get(obj['Káva'])
                        pc_sku = get_pc_sku(rc_kod, obj['Gramáž'])
                        
                        if not val: st.session_state.sklad["zabalena"][pc_sku] += obj['Kusy']
                        else: st.session_state.sklad["zabalena"][pc_sku] -= obj['Kusy']
                        auto_uloz(akcia="Opätovná expedícia" if val else "Storno expedície", detail=popis_obj(obj), sklad_pred=sklad_pred)
                        
                    st.checkbox(f"{o['Odberateľ']} | {o['Káva']} {o['Gramáž']}g ({o['Kusy']} ks)", value=True, key=f"rev_{i}", on_change=revert_expedicia_callback)

# ========================================================
# TAB 6: ÚČTOVNÍCTVO
# ========================================================
with tab6:
    st.markdown("### Účtovníctvo – export pre KROS Omega")

    SUBOR_CENNIK = "Kalkulacia stefi posledna prazenie 7.9.2026..xlsx"
    PREKLAD_CENNIK = {"Brazília": "Brazília – Donas do Café", "Etiopia Yerg.": "Etiópia – Yirgacheffe", "Etiopia BG": "Etiópia – Banko Gotiti",
                      "Honduras": "Honduras – SHG EP San Andrés", "Columbia": "Kolumbia – Huila condor", "Indonezia": "Indinezia",
                      "India": "India Plantation AA", "Aranka": "Aranka", "Frištuk": "Frištuk", "K52%": "K52% / Cucflek",
                      "Cucflek": "K52% / Cucflek", "Peru": "Peru", "Rwanda": "Rwanda"}
    PREKLAD_FAKTURA = {"Brazília": "Brazília – Donas do Café", "Etiopia Yerg.": "Etiópia – Yirgacheffe", "Etiopia BG": "Etiópia – Banko Gotiti",
                       "Honduras": "Honduras – SHG EP San Andrés", "Columbia": "Kolumbia – Huila condor", "Indonezia": "Indonézia",
                       "India": "India Plantation AA", "Aranka": "Aranka", "Frištuk": "Frištuk", "K52%": "Kopaničiarska 52%",
                       "Cucflek": "Cucflek", "Peru": "Peru", "Rwanda": "Rwanda"}

    @st.cache_data
    def nacitaj_cennik(obsah=None):
        zdroj = io.BytesIO(obsah) if obsah is not None else SUBOR_CENNIK
        return pd.read_excel(zdroj, sheet_name='Cenník kávy', skiprows=4)

    df_cennik = None
    if os.path.exists(SUBOR_CENNIK):
        try: df_cennik = nacitaj_cennik()
        except Exception as e: st.error(f"Cenník sa nepodarilo načítať: {e}")
    else:
        st.warning(f"Súbor s cenníkom **{SUBOR_CENNIK}** nie je v repozitári pri appke. Nahraj ho sem (hárok „Cenník kávy“):")
        nahrany_cennik = st.file_uploader("Cenník (.xlsx)", type=["xlsx"], key="upl_cennik")
        if nahrany_cennik is not None:
            try: df_cennik = nacitaj_cennik(nahrany_cennik.getvalue())
            except Exception as e: st.error(f"Cenník sa nepodarilo načítať: {e}")

    # Podklad = expedované (odoslané) riadky
    aj_fakturovane = st.toggle("Zahrnúť aj už vyfakturované", value=False, key="uct_aj_fakt",
                               help="Štandardne sa ponúka len to, čo ešte nešlo do Omegy – aby nevznikla faktúra dvakrát.")
    odoslane_idx = [i for i, o in enumerate(st.session_state.aktualne_objednavky)
                    if o.get('Potvrdene') and not o.get('Sudy') and not o.get('❌ Zmazať')
                    and int(o.get('Kusy', 0)) > 0 and (aj_fakturovane or not o.get('Vyfakturované'))]
    odberatelia_uct = sorted(set(st.session_state.aktualne_objednavky[i]['Odberateľ'] for i in odoslane_idx))

    if not odoslane_idx:
        st.info("Žiadne expedované položky na fakturáciu. Podkladom sú odoslané zásielky zo záložky EXPED.")
    elif df_cennik is not None:
        vyber_uct = st.selectbox("Odberateľ pre export:", ["Všetci"] + odberatelia_uct, key="uct_odberatel")
        idx_export = [i for i in odoslane_idx if vyber_uct == "Všetci" or st.session_state.aktualne_objednavky[i]['Odberateľ'] == vyber_uct]

        df_vypocet = pd.DataFrame([{**st.session_state.aktualne_objednavky[i], "_idx": i} for i in idx_export])
        df_vypocet['Hladat_v_cenniku'] = df_vypocet['Káva'].map(PREKLAD_CENNIK).fillna(df_vypocet['Káva'])
        df_vypocet['Produkt_Faktura'] = df_vypocet['Káva'].map(PREKLAD_FAKTURA).fillna(df_vypocet['Káva'])
        df_vypocet['Množstvo (ks)'] = df_vypocet['Kusy'].astype(int)
        df_vypocet['Gramaz_text'] = df_vypocet['Gramáž'].apply(lambda x: "1 000 g" if int(x) == 1000 else f"{int(x)} g")
        df_vypocet = df_vypocet.drop(columns=['Gramáž'])

        df_export = pd.merge(df_vypocet, df_cennik, left_on=['Hladat_v_cenniku', 'Gramaz_text'], right_on=['Produkt', 'Gramáž'], how='left')
        bez_ceny = df_export[df_export['Cena pre obchodníka (€)'].isna()]
        df_export['Cena pre obchodníka (€)'] = df_export['Cena pre obchodníka (€)'].fillna(0).round(2)
        df_export['Produkt'] = df_export['Produkt_Faktura']
        df_export['Gramáž'] = df_export['Gramaz_text']
        df_export = df_export[['Odberateľ', 'Produkt', 'Gramáž', 'Množstvo (ks)', 'Cena pre obchodníka (€)']]
        df_export = df_export.rename(columns={'Cena pre obchodníka (€)': 'Jednotková cena (€)'})
        df_export['Celková suma (€)'] = (df_export['Množstvo (ks)'] * df_export['Jednotková cena (€)']).round(2)

        if not bez_ceny.empty:
            chybaju = ", ".join(sorted(set(f"{r['Hladat_v_cenniku']} {r['Gramaz_text']}" for _, r in bez_ceny.iterrows())))
            st.error(f"⚠️ V cenníku chýba cena pre: {chybaju}. Vo faktúre budú za 0 €.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Odberateľov", df_export['Odberateľ'].nunique())
        c2.metric("Kusov", int(df_export['Množstvo (ks)'].sum()))
        c3.metric("Suma spolu", f"{df_export['Celková suma (€)'].sum():.2f} €")
        st.dataframe(df_export, hide_index=True, use_container_width=True,
                     column_config={"Jednotková cena (€)": st.column_config.NumberColumn(format="%.2f €"),
                                    "Celková suma (€)": st.column_config.NumberColumn(format="%.2f €")})

        # --- Excel pre Evičku (štýlovaný) ---
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
                        elif isinstance(cell_val, (int, float)) or hasattr(cell_val, "item"): worksheet.write_number(r_idx + 1, c_idx, float(cell_val), fmt)
                        else: worksheet.write(r_idx + 1, c_idx, str(cell_val), fmt)
        excel_data = excel_buffer.getvalue()

        # --- TXT pre KROS Omega (rovnaký formát ako v starej verzii) ---
        lines = ["R00\tT01"]
        today_str = datetime.now().strftime("%d.%m.%Y")
        due_str = (datetime.now() + timedelta(days=14)).strftime("%d.%m.%Y")
        invoice_counter = 1
        for odberatel, group in df_export.groupby('Odberateľ'):
            cislo_dokladu = f"EXP{datetime.now().strftime('%Y%m%d')}{invoice_counter:02d}"
            suma_celkom = group['Celková suma (€)'].sum()
            lines.append("\t".join(["R01", cislo_dokladu, str(odberatel), "", today_str, due_str, today_str, "0.00", f"{suma_celkom:.2f}", "", "", "", "", "", "", "", "", "11"]))
            for _, row in group.iterrows():
                lines.append("\t".join(["R02", f"{row['Produkt']} {row['Gramáž']}", str(int(row['Množstvo (ks)'])), "ks", f"{row['Jednotková cena (€)']:.2f}", "V", "0.00", f"{row['Jednotková cena (€)']:.2f}", "0", "V"]))
            invoice_counter += 1
        raw_txt_string = "\n".join(lines)
        txt_data = raw_txt_string.encode('windows-1250', errors='replace')

        meno_do_suboru = "Vsetci" if vyber_uct == "Všetci" else vyber_uct.replace(" ", "_")
        nazov_excelu = f"Kikiriki_Prehlad_Evicka_{meno_do_suboru}_{st.session_state.nazov_prazenia}.xlsx"
        nazov_txt = f"Kikiriki_Import_Omega_{meno_do_suboru}_{st.session_state.nazov_prazenia}.txt"

        def cb_txt_stiahnuty(odberatel, txt, indexy):
            uloz_export_pre_evicku(odberatel, txt)
            for i in indexy:
                if i < len(st.session_state.aktualne_objednavky):
                    st.session_state.aktualne_objednavky[i]['Vyfakturované'] = True
            st.session_state.pop("tabulka_objednavok", None)
            auto_uloz(akcia="Export pre Omegu", detail=f"{odberatel}: {len(indexy)} riadkov označených ako vyfakturované")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button("📊 Stiahnuť Excel pre Evičku", data=excel_data, file_name=nazov_excelu,
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with col_dl2:
            st.download_button("⚙️ Stiahnuť TXT pre KROS + ☁️ Uložiť pre Evičku", data=txt_data, file_name=nazov_txt, mime="text/plain",
                               on_click=cb_txt_stiahnuty, args=(vyber_uct, raw_txt_string, idx_export), type="primary", use_container_width=True)
        st.caption("Stiahnutím TXT sa export uloží do archívu pre Evičku a položky sa označia ako vyfakturované.")

    # --- ARCHÍV PRE EVIČKU ---
    st.divider()
    with st.expander("🔒 Archív exportov pre Evičku"):
        odomknute_uct = st.session_state.get("admin_odomknute", False) or st.session_state.get("evicka_odomknute", False)
        if not odomknute_uct:
            if not st.secrets.get("evicka_heslo", ""):
                st.caption("Prístup Evičky nastavíš v Secrets (kľúč `evicka_heslo`). Ty sa sem dostaneš aj cez zámok 🔒 vpravo hore.")
            with st.form("form_evicka", clear_on_submit=True):
                heslo_e = st.text_input("Heslo:", type="password")
                ok_e = st.form_submit_button("Otvoriť archív")
            if ok_e:
                spravne_e = st.secrets.get("evicka_heslo", "")
                if (spravne_e and hmac.compare_digest(str(heslo_e), str(spravne_e))) or over_heslo(heslo_e):
                    st.session_state.evicka_odomknute = True
                    st.rerun()
                else:
                    st.error("Nesprávne heslo.")
        else:
            if st.button("📥 Načítať dostupné exporty", key="btn_evicka"):
                st.session_state.evicka_exporty = nacitaj_exporty_pre_evicku()
            exporty = st.session_state.get("evicka_exporty")
            if exporty is not None:
                if not exporty:
                    st.info("Archív je zatiaľ prázdny.")
                else:
                    idx_e = st.selectbox("Vyber export:", list(range(len(exporty))),
                                         format_func=lambda i: f"{exporty[i][0]} | Odberateľ: {exporty[i][1]}", key="evicka_vyber")
                    vybrany = exporty[idx_e]
                    st.download_button("⚙️ Stiahnuť vybraný TXT pre KROS Omegu", data=vybrany[2].encode('windows-1250', errors='replace'),
                                       file_name=f"Kikiriki_Omega_{vybrany[0][:10].replace('.', '')}_{str(vybrany[1]).replace(' ', '_')}.txt",
                                       mime="text/plain", type="primary", use_container_width=True)
