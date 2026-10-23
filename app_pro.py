import streamlit as st
import pandas as pd
import math
import io
import os
import hmac
import copy
import time
from datetime import datetime as _dt, timedelta
from zoneinfo import ZoneInfo

class datetime(_dt):
    """datetime.now() vždy v slovenskom čase (server Streamlitu beží v UTC)."""
    @classmethod
    def now(cls, tz=None):
        return _dt.now(tz or ZoneInfo("Europe/Bratislava")).replace(tzinfo=None)
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
MAX_ZAZNAMOV_HISTORIE = 300

# Log: jeden riadok za každú zmenu skladu / akciu
NAZOV_LISTU_LOG = "Log"
LOG_HLAVICKA = ["Čas", "Identifikátor", "Akcia", "Detail", "Sklad", "SKU", "Názov", "Pred", "Po", "Zmena"]
NAZVY_SKLADU = {"zelena": "GC Zelená", "uprazena": "RC Dózy", "zabalena": "Zabalená PC", "obaly": "Obaly", "samolepky": "Samolepky"}
# Kategórie skladových kariet: typ -> (názov hárku, merná jednotka)
KATEGORIE_KARIET = {"zelena": ("GC", "kg"), "uprazena": ("RC", "kg"), "zabalena": ("Zabalená-PC", "ks"),
                    "obaly": ("Obaly", "ks"), "samolepky": ("Samolepky", "ks")}
TYPY_SKLADU = ["zelena", "uprazena", "zabalena", "obaly", "samolepky"]
TYPY_MATERIAL = ["obaly", "samolepky"]   # karty spravované v 🔒 Správe skladu

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

# Obalový materiál – predvolené skladové karty (ďalšie sa pridávajú v 🔒 Správa skladu → Skladové karty)
#   odpis: {"druh": "gramaz", "hodnota": 220}  -> 1 ks na každý zabalený sáčok danej gramáže
#          {"druh": "kava", "hodnota": "Peru"} -> 1 ks na každý zabalený sáčok danej kávy
#          {"druh": "ziadny"}                  -> bez automatiky, výdaj sa zadáva ručne
def predvolene_karty():
    karty = {}
    for g in gramaze_list:
        karty[f"OB{g}"] = {"typ": "obaly", "nazov": f"Prázdny sáčok {g} g", "mj": "ks", "odpis": {"druh": "gramaz", "hodnota": g}, "aktivna": True}
    for menu, rc in MENU_KAVY.items():
        karty[f"SA{rc[2:]}"] = {"typ": "samolepky", "nazov": f"Samolepka {menu}", "mj": "ks", "odpis": {"druh": "kava", "hodnota": menu}, "aktivna": True}
    return karty

def popis_odpisu(odpis):
    d = (odpis or {}).get("druh", "ziadny")
    if d == "gramaz": return f"Pri balení – sáčok {odpis['hodnota']} g"
    if d == "kava": return f"Pri balení – káva {odpis['hodnota']}"
    return "Bez automatiky (ručný výdaj)"

MOZNOSTI_ODPISU = (["Bez automatiky (ručný výdaj)"] + [f"Pri balení – sáčok {g} g" for g in gramaze_list]
                   + [f"Pri balení – káva {k}" for k in MENU_KAVY])

def odpis_z_popisu(text):
    for g in gramaze_list:
        if text == f"Pri balení – sáčok {g} g": return {"druh": "gramaz", "hodnota": g}
    for k in MENU_KAVY:
        if text == f"Pri balení – káva {k}": return {"druh": "kava", "hodnota": k}
    return {"druh": "ziadny"}

def karty_materialu(len_aktivne=True):
    karty = st.session_state.sklad.get("karty", {})
    return {s_: k for s_, k in karty.items() if (k.get("aktivna", True) or not len_aktivne)}

def karty_na_odpis(kava, gramaz):
    """Karty, z ktorých sa odpíše 1 ks za každý zabalený sáčok danej kávy a gramáže."""
    vysledok = []
    for s_, k in karty_materialu().items():
        o = k.get("odpis", {})
        if (o.get("druh") == "gramaz" and int(o.get("hodnota", 0)) == int(gramaz)) or (o.get("druh") == "kava" and o.get("hodnota") == kava):
            vysledok.append(s_)
    return vysledok

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

def uloz_snapshot_historie(spreadsheet, cas, nazov, kusky, akcia=""):
    ws_h = ziskaj_list(spreadsheet, NAZOV_LISTU_HISTORIA, riadky=MAX_ZAZNAMOV_HISTORIE + 20, stlpce=max(10, len(kusky) + 4))
    if ws_h.col_count < len(kusky) + 3:
        ws_h.resize(cols=len(kusky) + 3)
    # 3. stĺpec: "#A:<akcia>" – popis, po akej akcii vznikla záloha (JSON nikdy nezačína "#A:")
    ws_h.append_row([cas, nazov, "#A:" + str(akcia)[:300]] + kusky, value_input_option="RAW")
    pocet = len(ws_h.col_values(1))
    if pocet > MAX_ZAZNAMOV_HISTORIE:
        ws_h.delete_rows(1, pocet - MAX_ZAZNAMOV_HISTORIE)

# --- LOG FUNKCIE ---
def nazov_sku(typ, sku):
    if typ == "zelena": return NAZVY_ZELENA.get(sku, "")
    if typ == "uprazena": return NAZVY_UPRAZENA.get(sku, "")
    if typ in TYPY_MATERIAL:
        try: return st.session_state.sklad.get("karty", {}).get(sku, {}).get("nazov", "")
        except Exception: return ""
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


# --- EXCEL: STAV SKLADU A SKLADOVÉ KARTY ---
def _zapis_harok(writer, df, nazov, skupina=None):
    wb = writer.book
    if df.empty: df = pd.DataFrame({"Info": ["(prázdne)"]})
    df.to_excel(writer, sheet_name=nazov, index=False)
    ws = writer.sheets[nazov]
    hl = wb.add_format({"bold": True, "bg_color": "#2B5098", "font_color": "white", "border": 1})
    f1 = wb.add_format({"border": 1, "bg_color": "#FFFFFF"}); f2 = wb.add_format({"border": 1, "bg_color": "#E8EEF8"})
    fz = wb.add_format({"border": 1, "font_color": "#C0392B", "bold": True})
    for c, col in enumerate(df.columns):
        ws.write(0, c, str(col), hl)
        ws.set_column(c, c, max(10, min(50, int(df[col].map(lambda v: len(str(v))).max() if len(df) else 8) + 2)))
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, len(df), len(df.columns) - 1)
    farba, posledna = True, None
    for r_i in range(len(df)):
        if skupina and skupina in df.columns:
            v = df.iloc[r_i][skupina]
            if posledna is not None and v != posledna: farba = not farba
            posledna = v
        else:
            farba = r_i % 2 == 0
        for c_i, col in enumerate(df.columns):
            val = df.iloc[r_i, c_i]
            fmt = f1 if farba else f2
            if isinstance(val, (int, float)) or hasattr(val, "item"):
                val = float(val)
                if val < 0 and col not in ("Výdaj", "Zmena"): fmt = fz
                if math.isnan(val): ws.write(r_i + 1, c_i, "", fmt)
                else: ws.write_number(r_i + 1, c_i, val, fmt)
            else:
                ws.write(r_i + 1, c_i, "" if val is None else str(val), fmt)

def excel_stav_skladu():
    sk = st.session_state.sklad
    harky, prehlad = [], []
    for typ, (harok, mj) in KATEGORIE_KARIET.items():
        riadky = []
        for sku_, v in sk.get(typ, {}).items():
            r_ = {"SKU": sku_, "Názov": nazov_sku(typ, sku_)}
            if typ == "zabalena":
                g = gramaz_z_pc(sku_); r_["Gramáž (g)"] = g
                r_[f"Stav ({mj})"] = int(v); r_["Váha (kg)"] = round(int(v) * g / 1000.0, 2)
            elif mj == "ks":
                r_[f"Stav ({mj})"] = int(v); r_["Minimum (ks)"] = int(sk.get("minima", {}).get(sku_, 0))
            else:
                r_[f"Stav ({mj})"] = round(float(v), 3)
            riadky.append(r_)
        df_ = pd.DataFrame(riadky)
        harky.append((df_, harok))
        col = f"Stav ({mj})"
        prehlad.append({"Sklad": harok, "Počet kariet": len(df_),
                        "Kariet so zásobou": int((df_[col] > 0).sum()) if len(df_) else 0,
                        "Spolu": round(float(df_[col].sum()), 3) if len(df_) else 0, "MJ": mj,
                        "Záporné stavy": int((df_[col] < 0).sum()) if len(df_) else 0})
    df_p = pd.DataFrame(prehlad)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        _zapis_harok(writer, df_p, "Prehľad")
        writer.sheets["Prehľad"].write(len(df_p) + 2, 0, f"Stav k {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        for df_, harok in harky:
            _zapis_harok(writer, df_, harok)
    return buffer.getvalue()

def typ_podla_sku(sku_):
    for typ in TYPY_SKLADU:
        if sku_ in st.session_state.sklad.get(typ, {}): return typ
    return None

def skladove_karty_df(df_log):
    """Z logu urobí pohyby po kartách: najstaršie hore, s príjmom, výdajom a zostatkom."""
    if df_log is None or df_log.empty or "SKU" not in df_log.columns:
        return pd.DataFrame(columns=["SKU", "Názov", "Kategória", "Dátum", "Pohyb", "Detail", "Príjem", "Výdaj", "Zostatok"])
    d = df_log[df_log["SKU"].astype(str).str.len() > 0].iloc[::-1].copy()
    num = lambda x: pd.to_numeric(d[x].astype(str).str.replace(",", "."), errors="coerce").fillna(0)
    d["_zmena"], d["_po"] = num("Zmena"), num("Po")
    d["_cas"] = pd.to_datetime(d["Čas"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
    d["_typ"] = d["SKU"].map(typ_podla_sku)
    d = d.sort_values(["SKU", "_cas"], kind="stable")
    return pd.DataFrame({
        "SKU": d["SKU"], "Názov": [nazov_sku(t, s_) if t else n for t, s_, n in zip(d["_typ"], d["SKU"], d["Názov"])],
        "Kategória": d["_typ"].map(lambda t: KATEGORIE_KARIET.get(t, ("?", ""))[0]),
        "Dátum": d["Čas"], "Pohyb": d["Akcia"], "Detail": d["Detail"],
        "Príjem": d["_zmena"].clip(lower=0).round(3), "Výdaj": (-d["_zmena"].clip(upper=0)).round(3), "Zostatok": d["_po"].round(3),
    }).reset_index(drop=True)

def excel_skladove_karty(df_karty):
    sk = st.session_state.sklad
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        zoznam = []
        for typ, (harok, mj) in KATEGORIE_KARIET.items():
            for sku_, v in sk.get(typ, {}).items():
                pohyby = df_karty[df_karty["SKU"] == sku_]
                zoznam.append({"SKU": sku_, "Názov": nazov_sku(typ, sku_), "Kategória": harok, "MJ": mj,
                               "Aktuálny stav": round(float(v), 3), "Príjem spolu": round(float(pohyby["Príjem"].sum()), 3),
                               "Výdaj spolu": round(float(pohyby["Výdaj"].sum()), 3), "Počet pohybov": len(pohyby),
                               "Posledný pohyb": pohyby["Dátum"].iloc[-1] if len(pohyby) else ""})
        _zapis_harok(writer, pd.DataFrame(zoznam), "Zoznam kariet", skupina="Kategória")
        for typ, (harok, mj) in KATEGORIE_KARIET.items():
            _zapis_harok(writer, df_karty[df_karty["Kategória"] == harok].drop(columns=["Kategória"]), harok, skupina="SKU")
    return buffer.getvalue()

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


# ==========================================
# 🛒 E-SHOP (WooCommerce, kikiriki.sk)
# ==========================================
NAZOV_LISTU_ESHOP = "Eshop_import"          # pamäť už importovaných objednávok (proti zdvojeniu)
ESHOP_HLAVICKA = ["Číslo obj.", "Importované", "Zákazník", "Položky"]
ESHOP_STAVY = ["processing"]                 # ktoré stavy objednávok sťahovať (zaplatené, čakajú na spracovanie)

# ID produktu v e-shope -> názov kávy v appke (podľa MENU_KAVY). None = appka sa opýta, kam to zaradiť.
ESHOP_MAPOVANIE = {
    20644: "Cucflek",          # Cucflek
    20631: "K52%",             # Kopaničiarska 52%
    19888: "Brazília",         # Brazília – Na každý deň
    19369: "Etiopia BG",       # Etiópia – Banko Gotiti
    18680: "Columbia",         # Kolumbia – Huila Condor
    18674: "India",            # India Plantation AA
    5481:  "Honduras",         # Honduras – SHG EP San Andrés
    5495:  "Etiopia Yerg.",    # Etiópia – Yirgacheffe
    10866: "Frištuk",          # Fristuk
    12032: "Aranka",           # Aranka
    11879: None,               # Brazília – Donas do Café  -> nie je v menu appky, vyber ručne
}

# Záchranné mapovanie podľa názvu (keď ID produktu nie je v ESHOP_MAPOVANIE – napr. nový/testovací produkt)
ESHOP_MAPOVANIE_NAZOV = [
    ("cucflek", "Cucflek"), ("52", "K52%"), ("kopani", "K52%"), ("aranka", "Aranka"), ("fri", "Frištuk"),
    ("banko", "Etiopia BG"), ("gotiti", "Etiopia BG"), ("yirg", "Etiopia Yerg."), ("etiop", "Etiopia Yerg."),
    ("kolumb", "Columbia"), ("columb", "Columbia"), ("india", "India"), ("honduras", "Honduras"),
    ("peru", "Peru"), ("rwanda", "Rwanda"), ("indonez", "Indonezia"), ("brazil", "Brazília"),
]

def eshop_kava_podla_nazvu(nazov):
    n = str(nazov).lower()
    for kluc, kava in ESHOP_MAPOVANIE_NAZOV:
        if kluc in n:
            return kava
    return ""

def eshop_nastaveny():
    return all(st.secrets.get(k, "") for k in ("woo_url", "woo_ck", "woo_cs"))

def eshop_gramaz_z_textu(text):
    """'Balenie 500 g' / '1kg' / 'Aranka - 220g' -> 500 / 1000 / 220. Neznáme -> 0."""
    import re
    m = re.search(r"(\d+[.,]?\d*)[\s-]*(kg|g)\b", str(text).lower())
    if not m:
        return 0
    cislo = float(m.group(1).replace(",", "."))
    gram = int(round(cislo * 1000)) if m.group(2) == "kg" else int(round(cislo))
    return gram if gram in gramaze_list else 0

def eshop_stiahni_objednavky():
    """Vráti zoznam objednávok z WooCommerce REST API (iba stavy v ESHOP_STAVY)."""
    import requests
    url = st.secrets["woo_url"].rstrip("/") + "/wp-json/wc/v3/orders"
    auth = (st.secrets["woo_ck"], st.secrets["woo_cs"])
    vsetky = []
    for stav in ESHOP_STAVY:
        strana = 1
        while True:
            r = requests.get(url, auth=auth, timeout=20,
                             params={"status": stav, "per_page": 50, "page": strana, "orderby": "date", "order": "asc"})
            r.raise_for_status()
            davka = r.json()
            vsetky.extend(davka)
            if len(davka) < 50:
                break
            strana += 1
    return vsetky

def eshop_riadky_z_objednavky(obj):
    """Jedna objednávka z e-shopu -> riadky pre Knihu objednávok (Odberateľ/Káva/Gramáž/Kusy)."""
    b = obj.get("billing", {}) or {}
    meno = (b.get("company") or f"{b.get('first_name', '')} {b.get('last_name', '')}").strip() or f"E-shop #{obj.get('id')}"
    riadky = []
    for pol in obj.get("line_items", []):
        pid = int(pol.get("product_id") or 0)
        kava = ESHOP_MAPOVANIE.get(pid, None)
        if not kava:
            kava = eshop_kava_podla_nazvu(pol.get("name", ""))
        gramaz = 0
        for meta in pol.get("meta_data", []) or []:
            if "balenie" in str(meta.get("key", "")).lower():
                gramaz = eshop_gramaz_z_textu(meta.get("value", ""))
                break
        if not gramaz:
            gramaz = eshop_gramaz_z_textu(pol.get("name", ""))
        riadky.append({
            "Číslo obj.": str(obj.get("number") or obj.get("id")),
            "Odberateľ": meno,
            "Produkt (e-shop)": pol.get("name", ""),
            "ID produktu": f"{pid}/{pol.get('variation_id') or 0}",
            "Káva": kava or "",
            "Gramáž": gramaz,
            "Kusy": int(pol.get("quantity") or 0),
        })
    return riadky

def eshop_nacitaj_importovane():
    try:
        spreadsheet = otvor_tabulku(get_client())
        ws = spreadsheet.worksheet(NAZOV_LISTU_ESHOP)
        return {r[0] for r in ws.get_all_values()[1:] if r and r[0]}
    except Exception:
        return set()

def eshop_zapis_importovane(zaznamy):
    """zaznamy: list [cislo_obj, cas, zakaznik, polozky]"""
    import gspread
    spreadsheet = otvor_tabulku(get_client())
    try:
        ws = spreadsheet.worksheet(NAZOV_LISTU_ESHOP)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=NAZOV_LISTU_ESHOP, rows=1000, cols=len(ESHOP_HLAVICKA))
        ws.append_row(ESHOP_HLAVICKA, value_input_option="RAW")
    ws.append_rows(zaznamy, value_input_option="RAW")

def eshop_blok_ui():
    st.markdown("### 🛒 Objednávky z e-shopu (kikiriki.sk)")
    if not eshop_nastaveny():
        st.info("E-shop nie je pripojený – v Streamlit Secrets chýbajú `woo_url`, `woo_ck`, `woo_cs`.")
        return

    c1, c2 = st.columns([2, 3])
    with c1:
        if st.button("🛒 Načítať nové objednávky z e-shopu", use_container_width=True):
            try:
                with st.spinner("Sťahujem objednávky…"):
                    importovane = eshop_nacitaj_importovane()
                    objednavky = [o for o in eshop_stiahni_objednavky()
                                  if str(o.get("number") or o.get("id")) not in importovane]
                    riadky = [r for o in objednavky for r in eshop_riadky_z_objednavky(o)]
                st.session_state["eshop_nahlad"] = riadky
                st.session_state["eshop_preskocene"] = len(importovane)
            except Exception as e:
                st.error(f"Nepodarilo sa stiahnuť objednávky: {e}")
    with c2:
        st.caption(f"Sťahujú sa objednávky v stave: {', '.join(ESHOP_STAVY)}. Už importované sa preskakujú "
                   f"(pamäť v hárku „{NAZOV_LISTU_ESHOP}“).")

    nahlad = st.session_state.get("eshop_nahlad")
    if nahlad is None:
        return
    if not nahlad:
        st.success("Žiadne nové objednávky – všetko je už v knihe.")
        return

    st.write(f"**Nové riadky: {len(nahlad)}** (objednávok: {len({r['Číslo obj.'] for r in nahlad})}). "
             "Skontroluj mapovanie a potom pridaj do knihy.")
    moznosti = [""] + list(MENU_KAVY.keys())
    df_n = pd.DataFrame(nahlad)
    df_n["Gramáž"] = df_n["Gramáž"].astype(int)
    upraveny = st.data_editor(
        df_n,
        key="eshop_editor",
        use_container_width=True,
        hide_index=True,
        disabled=["Číslo obj.", "Produkt (e-shop)", "ID produktu"],
        column_config={
            "Káva": st.column_config.SelectboxColumn("Káva", options=moznosti, required=False),
            "Gramáž": st.column_config.SelectboxColumn("Gramáž", options=[0] + gramaze_list),
            "Kusy": st.column_config.NumberColumn("Kusy", min_value=0, step=1),
        },
    )
    chybne = upraveny[(upraveny["Káva"] == "") | (upraveny["Gramáž"] == 0) | (upraveny["Kusy"] <= 0)]
    if not chybne.empty:
        st.warning(f"{len(chybne)} riadkov nemá priradenú kávu/gramáž – doplň ich v tabuľke (alebo daj Kusy 0, ak sa majú vynechať).")

    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("➕ Pridať do knihy objednávok", type="primary", use_container_width=True,
                     disabled=not chybne[chybne["Kusy"] > 0].empty):
            pocet_pred = len(st.session_state.aktualne_objednavky)
            platne = upraveny[upraveny["Kusy"] > 0]
            for _, r in platne.iterrows():
                st.session_state.aktualne_objednavky.append({
                    "Odberateľ": str(r["Odberateľ"]), "Káva": str(r["Káva"]), "Gramáž": int(r["Gramáž"]),
                    "Kusy": int(r["Kusy"]), "Zabalené (ks)": 0, "Potvrdene": False, "Sudy": False, "❌ Zmazať": False,
                })
            nove = st.session_state.aktualne_objednavky[pocet_pred:]
            cas = datetime.now().strftime("%d.%m.%Y %H:%M")
            zaznamy = []
            for cislo, sk in upraveny.groupby("Číslo obj."):
                zaznamy.append([str(cislo), cas, str(sk["Odberateľ"].iloc[0]),
                                "; ".join(f"{a['Káva']} {a['Gramáž']}g x{a['Kusy']}" for _, a in sk.iterrows() if a["Kusy"] > 0)])
            try:
                eshop_zapis_importovane(zaznamy)
            except Exception as e:
                st.toast(f"⚠️ Objednávky pridané, ale pamäť importu sa nezapísala: {e}", icon="⚠️")
            auto_uloz(akcia="Import z e-shopu", detail=f"{len(nove)} riadkov, obj. {', '.join(z[0] for z in zaznamy)}: " + "; ".join(popis_obj(o) for o in nove))
            st.session_state.pop("eshop_nahlad", None)
            st.session_state.pop("eshop_editor", None)
            st.success(f"Pridaných {len(nove)} riadkov z {len(zaznamy)} objednávok.")
            st.rerun()
    with cb2:
        if st.button("Zahodiť náhľad", use_container_width=True):
            st.session_state.pop("eshop_nahlad", None)
            st.rerun()


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
        if r[2].startswith("#A:"):
            zaznamy.append({"cas": r[0], "nazov": r[1], "akcia": r[2][3:], "data": "".join(r[3:])})
        else:
            zaznamy.append({"cas": r[0], "nazov": r[1], "akcia": "", "data": "".join(r[2:])})
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

def uloz_do_google_sheets(data_dict, nazov_prazenia, historia=False, log=None, popis_zalohy=""):
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
            uloz_snapshot_historie(spreadsheet, cas_ulozenia, str(nazov_prazenia), kusky, popis_zalohy)
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
    # Každá zapísaná akcia vytvorí aj zálohu v Obnove -> dá sa vrátiť ku ktorémukoľvek kroku
    if akcia: historia = True
    popis = f"{akcia}: {detail}" if akcia and detail else (akcia or "Ručné uloženie")
    uspech, chyba = uloz_do_google_sheets(data_na_ulozenie, aktualny_nazov, historia=historia, log=log, popis_zalohy=popis[:300])
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
    sklad["karty"] = {}
    if nacitany_sklad:
        for t in TYPY_SKLADU + ["minima", "karty"]:
            sklad[t] = copy.deepcopy(dict(nacitany_sklad.get(t, {}) or {}))
        # migrácia: staré "etikety" (ET…) -> "samolepky" (SA…)
        for sku_e, v in (nacitany_sklad.get("etikety", {}) or {}).items():
            sklad["samolepky"].setdefault("SA" + sku_e[2:] if sku_e.startswith("ET") else sku_e, v)
        for sku_e in list(sklad["minima"]):
            if sku_e.startswith("ET"): sklad["minima"].setdefault("SA" + sku_e[2:], sklad["minima"].pop(sku_e))
    if not sklad["karty"]:
        sklad["karty"] = predvolene_karty()
    for sku_k, k in sklad["karty"].items():
        sklad.setdefault(k["typ"], {}).setdefault(sku_k, 0)
    
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
                ws.set_column(c, c, max(12, min(45, int(df[col].map(lambda v: len(str(v))).max() if len(df) else 10) + 2)))
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
        hárok(pd.DataFrame([{"SKU": k, "Názov": NAZVY_ZABALENA.get(k, ""), "Stav (ks)": int(v)} for k, v in stav["sklad"]["zabalena"].items()]), "Sklad Zabalená PC")
        hárok(pd.DataFrame([{"SKU": k, "Názov": stav["sklad"].get("karty", {}).get(k, {}).get("nazov", ""), "Stav (ks)": int(v),
                             "Minimum (ks)": int(stav["sklad"].get("minima", {}).get(k, 0)),
                             "Odpis": popis_odpisu(stav["sklad"].get("karty", {}).get(k, {}).get("odpis")),
                             "Aktívna": stav["sklad"].get("karty", {}).get(k, {}).get("aktivna", True)}
                            for t in TYPY_MATERIAL for k, v in stav["sklad"].get(t, {}).items()]), "Obaly a samolepky")
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

# Doplnenie chýbajúcich častí skladu (napr. session spustená pred aktualizáciou appky alebo starší stav v cloude)
if 'sklad' in st.session_state:
    _sk = st.session_state.sklad
    if not _sk.get("karty") or any(t not in _sk for t in TYPY_SKLADU) or "etikety" in _sk:
        st.session_state.sklad = inicializuj_sklad(_sk)

if 'nazov_prazenia' not in st.session_state:
    st.session_state.nazov_prazenia = st.session_state.get('pociatocny_nazov', f"Prazenie_PRO_{DNESNY_DATUM}")

if 'form_key' not in st.session_state: st.session_state.form_key = 0
def vynuluj_policka(): st.session_state.form_key += 1

# --- SPRÁVA: ZÁMOK (inventúra, log, obnova) ---
def sprava_kariet():
    """🗂️ Skladové karty materiálu (obaly, samolepky): pridanie, úprava, archivácia."""
    sk = st.session_state.sklad
    karty = sk.setdefault("karty", {})
    minima = sk.setdefault("minima", {})
    msg = st.session_state.pop("msg_karty", None)
    if msg: (st.success if msg[0] == "ok" else st.error)(msg[1])

    st.caption("Karty obalov a samolepiek. Pravidlo odpisu určuje, kedy sa karta pri balení automaticky odpíše. "
               "Kávy (GC / RC / PG) sa tu nespravujú.")

    # --- ÚPRAVA EXISTUJÚCICH ---
    riadky = [{"Kód": s_, "Kategória": KATEGORIE_KARIET[k["typ"]][0], "Názov": k["nazov"],
               "Minimum (ks)": int(minima.get(s_, 0)), "Odpis": popis_odpisu(k.get("odpis")),
               "Na sklade": int(sk.get(k["typ"], {}).get(s_, 0)), "Aktívna": bool(k.get("aktivna", True))}
              for s_, k in sorted(karty.items(), key=lambda x: (x[1]["typ"], x[0]))]
    ed = st.data_editor(pd.DataFrame(riadky), hide_index=True, use_container_width=True, key="ed_karty",
                        disabled=["Kód", "Kategória", "Na sklade"],
                        column_config={"Odpis": st.column_config.SelectboxColumn(options=MOZNOSTI_ODPISU, required=True, width="large"),
                                       "Minimum (ks)": st.column_config.NumberColumn(min_value=0, step=1),
                                       "Aktívna": st.column_config.CheckboxColumn(help="Neaktívna = archivovaná: zmizne zo skladu, história ostane")})
    if st.button("💾 Uložiť úpravy kariet", type="primary", key="btn_ulozit_karty"):
        zmeny, chyby = [], []
        for r_ in ed.to_dict("records"):
            s_ = r_["Kód"]; k = karty[s_]
            novy_nazov = str(r_["Názov"] or "").strip() or k["nazov"]
            novy_odpis = odpis_z_popisu(r_["Odpis"])
            try: nove_min = max(0, int(float(r_["Minimum (ks)"])))
            except (TypeError, ValueError): nove_min = 0
            nova_akt = bool(r_["Aktívna"])
            if not nova_akt and k.get("aktivna", True) and int(sk[k["typ"]].get(s_, 0)) != 0:
                chyby.append(f"{s_}: archivovať sa dá len karta so stavom 0 (teraz {int(sk[k['typ']].get(s_, 0))} ks)."); continue
            if novy_nazov != k["nazov"]: zmeny.append(f"{s_} názov „{k['nazov']}“→„{novy_nazov}“"); k["nazov"] = novy_nazov
            if novy_odpis != k.get("odpis"): zmeny.append(f"{s_} odpis → {popis_odpisu(novy_odpis)}"); k["odpis"] = novy_odpis
            if nove_min != int(minima.get(s_, 0)): zmeny.append(f"{s_} minimum → {nove_min}"); minima[s_] = nove_min
            if nova_akt != k.get("aktivna", True): zmeny.append(f"{s_} {'aktivovaná' if nova_akt else 'archivovaná'}"); k["aktivna"] = nova_akt
        if zmeny:
            auto_uloz(historia=True, akcia="Úprava skladových kariet", detail="; ".join(zmeny))
        st.session_state.msg_karty = ("err", " ".join(chyby)) if chyby else ("ok", f"Uložené ({len(zmeny)} zmien)." if zmeny else "Žiadne zmeny.")
        st.session_state.pop("ed_karty", None)
        st.rerun(scope="fragment")

    # --- NOVÁ KARTA ---
    st.markdown("##### ➕ Nová skladová karta")
    with st.form("form_nova_karta", clear_on_submit=True):
        n1, n2, n3 = st.columns([1.4, 1.2, 3])
        with n1: kat = st.selectbox("Kategória:", TYPY_MATERIAL, format_func=lambda t: KATEGORIE_KARIET[t][0])
        with n2: kod = st.text_input("Kód:", placeholder="napr. OB250, SA010, KR01").strip().upper()
        with n3: nazov_n = st.text_input("Názov:", placeholder="napr. Kartónová krabica malá").strip()
        n4, n5, n6 = st.columns([3, 1.2, 1.2])
        with n4: odpis_n = st.selectbox("Pravidlo odpisu:", MOZNOSTI_ODPISU)
        with n5: min_n = st.number_input("Minimum (ks):", min_value=0, step=10)
        with n6: stav_n = st.number_input("Počiatočný stav (ks):", min_value=0, step=10)
        ok_n = st.form_submit_button("➕ Založiť kartu", type="primary")
    if ok_n:
        vsetky_kody = set(karty) | {s_ for t in TYPY_SKLADU for s_ in sk.get(t, {})}
        if not kod or not nazov_n:
            st.error("Vyplň kód aj názov.")
        elif kod in vsetky_kody:
            st.error(f"Kód {kod} už existuje.")
        else:
            sklad_pred = copy.deepcopy(sk)
            karty[kod] = {"typ": kat, "nazov": nazov_n, "mj": "ks", "odpis": odpis_z_popisu(odpis_n), "aktivna": True}
            sk.setdefault(kat, {})[kod] = int(stav_n)
            if min_n: minima[kod] = int(min_n)
            auto_uloz(historia=True, akcia="Nová skladová karta", detail=f"{kod} – {nazov_n} ({KATEGORIE_KARIET[kat][0]}, {odpis_n}, počiatočný stav {int(stav_n)} ks)", sklad_pred=sklad_pred)
            st.session_state.msg_karty = ("ok", f"Karta {kod} – {nazov_n} založená.")
            st.session_state.pop("ed_karty", None)
            st.rerun(scope="fragment")

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
    st.caption("Inventúra je odomknutá v podzáložkách GC / RC / Zabalená – PC / Obaly a samolepky v záložke Sklad.")

    tab_log, tab_obnova, tab_karty = st.tabs(["**📜 Log**", "**⏪ Obnova**", "**🗂️ Skladové karty**"])
    with tab_karty:
        sprava_kariet()
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
        st.caption("Záloha vzniká po každej akcii a ukazuje stav PO nej. Ak chceš zrušiť posledné 2 objednávky, "
                   "vyber zálohu tesne pred nimi. Aktuálny stav sa pred obnovou uloží, takže obnova sa dá vrátiť.")
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
                               format_func=lambda i: f"{zoznam[i]['cas']} | {(zoznam[i].get('akcia') or zoznam[i]['nazov'])[:90]}", key="vyber_zalohy")
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
    st.caption("Verzia 11.9 | Výroba, Sklad & ERP Kódy")
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "**OBJEDNÁVKY**", "**PRAŽIAREŇ**", "**BALENIE**", "**SKLAD**", "**EXPED.**", "**ÚČTOVNÍCTVO**", "**ŠTATISTIKY**"
])

# ========================================================
# TAB 1: OBJEDNÁVKY
# ========================================================
def excel_na_poziadanie(popis, generator, nazov_suboru, kluc, **kw):
    """Excel sa vytvorí až po kliknutí (nie pri každom prekreslení stránky – appka je tak rýchlejšia)."""
    if st.button(popis, key=f"{kluc}_priprav", **kw):
        st.session_state[kluc] = (generator(), nazov_suboru)
    if st.session_state.get(kluc):
        data_x, meno_x = st.session_state[kluc]
        st.download_button("⬇️ Stiahnuť", data=data_x, file_name=meno_x, key=f"{kluc}_dl", type="primary",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True,
                           on_click=lambda: st.session_state.pop(kluc, None))

def stabilny_selectbox(label, options, state_key, format_func=str, v_adrese=False, **kw):
    """Roletka, ktorá si pamätá výber, aj keď sa jej popisky menia (napr. „zostáva 12 ks“ → „zostáva 6 ks“).
    Streamlit by inak pri zmene popisiek vytvoril novú roletku a výber by skočil na prvú položku."""
    ulozene = st.session_state.get(state_key)
    if ulozene is None and v_adrese:                    # po obnovení stránky / znovupripojení si výber vezme z adresy
        ulozene = st.query_params.get(state_key)
    if ulozene not in options:
        ulozene = options[0] if options else None
    popisky = tuple(str(format_func(o)) for o in options)
    wkey = f"{state_key}__w{abs(hash(popisky)) % 10**8}"
    if wkey in st.session_state and st.session_state[wkey] != ulozene:
        del st.session_state[wkey]                     # výber zmenil kód (napr. reset filtra) -> roletka sa nastaví podľa neho
    def _sync():
        st.session_state[state_key] = st.session_state[wkey]
    val = st.selectbox(label, options, index=options.index(ulozene) if ulozene in options else 0,
                       format_func=format_func, key=wkey, on_change=_sync, **kw)
    st.session_state[state_key] = val
    if v_adrese:
        try:
            if st.query_params.get(state_key) != str(val): st.query_params[state_key] = str(val)
        except Exception: pass
    return val

def zapis_balenia_do_skladu(k, g, n):
    """Zabalenie n sáčkov kávy k / gramáž g: dózy (RC podľa receptu) −, regál (PC) +, obaly a samolepky −."""
    sk = st.session_state.sklad
    pc_sku = get_pc_sku(MENU_KAVY.get(k), g)
    sk["zabalena"][pc_sku] = sk["zabalena"].get(pc_sku, 0) + n
    for mat_sku in karty_na_odpis(k, g):
        typ_m = sk["karty"][mat_sku]["typ"]
        sk[typ_m][mat_sku] = int(sk[typ_m].get(mat_sku, 0)) - n
    vaha = n * g / 1000.0
    if k in kavy_recepty:
        for zrno, podiel in kavy_recepty[k]["recept"].items():
            rc = SKU_UPRAZENA.get(zrno)
            if rc: sk["uprazena"][rc] = sk["uprazena"].get(rc, 0.0) - vaha * podiel
    return pc_sku

# --- ZOSTÁVA: pruh pod záložkami (koľko dávok dopražiť a koľko sáčkov zabaliť) ---
UPRAZENA_NA_DAVKU = KAPACITA_ZELENA_BATCH * (1 - STANDARDNY_VYPEK / 100.0)   # 5 kg zelenej -> 4 kg praženej

def sudy_zostava_zelena():
    """Skladové dávky (BATCH): koľko kg ZELENEJ ešte treba upražiť po zrnách.
    Plnia sa pražením (poznačí sa do riadku), nie stavom dózy – inak by sa pri balení z dózy
    skladová dávka „vrátila“ a appka by chcela pražiť znova."""
    zostava = {}
    for o in st.session_state.aktualne_objednavky:
        if o.get('❌ Zmazať') == True or not o.get("Sudy") or o.get("Káva") not in kavy_recepty: continue
        try: hotovo = json.loads(o.get("Sudy_upr") or "{}")
        except Exception: hotovo = {}
        for zrno, podiel in kavy_recepty[o["Káva"]]["recept"].items():
            treba = float(o.get("Kusy", 0)) * KAPACITA_ZELENA_BATCH * podiel - float(hotovo.get(zrno, 0))
            if treba > 1e-9: zostava[zrno] = zostava.get(zrno, 0) + treba
    return zostava

def pripis_sudy(zrno, kg_zelenej):
    """Pripíše upraženú zelenú skladovým dávkam daného zrna (najstaršie prvé). Vráti, koľko sa pripísalo."""
    pripisane = 0.0
    for o in st.session_state.aktualne_objednavky:
        if kg_zelenej - pripisane <= 1e-9: break
        if o.get('❌ Zmazať') == True or not o.get("Sudy") or o.get("Káva") not in kavy_recepty: continue
        podiel = kavy_recepty[o["Káva"]]["recept"].get(zrno)
        if not podiel: continue
        try: hotovo = json.loads(o.get("Sudy_upr") or "{}")
        except Exception: hotovo = {}
        volne = float(o.get("Kusy", 0)) * KAPACITA_ZELENA_BATCH * podiel - float(hotovo.get(zrno, 0))
        if volne <= 1e-9: continue
        dam = min(volne, kg_zelenej - pripisane)
        hotovo[zrno] = round(float(hotovo.get(zrno, 0)) + dam, 4)
        o["Sudy_upr"] = json.dumps(hotovo)
        pripisane += dam
    return pripisane

def odpis_sudy(zrno, kg_zelenej):
    """Opačný krok k pripis_sudy (storno praženia) – od najnovších."""
    zostava = kg_zelenej
    for o in reversed(st.session_state.aktualne_objednavky):
        if zostava <= 1e-9: break
        if not o.get("Sudy"): continue
        try: hotovo = json.loads(o.get("Sudy_upr") or "{}")
        except Exception: hotovo = {}
        if float(hotovo.get(zrno, 0)) <= 0: continue
        uber = min(float(hotovo[zrno]), zostava)
        hotovo[zrno] = round(float(hotovo[zrno]) - uber, 4)
        o["Sudy_upr"] = json.dumps(hotovo)
        zostava -= uber

def vypocet_planu_prazenia():
    """Jednotný plán praženia (pruh, Pražiareň aj Excel):
    objednávky: potreba = NEZABALENÉ sáčky otvorených objednávok (po zrnách, blendy na zložky) − to, čo je v dóze
    skladové dávky: pevný počet dávok, odpočítava sa len pražením
    dávky = objednávky (kg / 0,8 / 5 kg nahor) + zvyšné skladové dávky"""
    potreba = {}
    for o in st.session_state.aktualne_objednavky:
        if o.get('❌ Zmazať') == True or o.get("Káva") not in kavy_recepty: continue
        if o.get("Sudy") or o.get("Potvrdene"): continue          # skladové dávky zvlášť; odoslané = už zabalené
        nezabalene = max(0, int(o.get("Kusy", 0)) - int(o.get("Zabalené (ks)", 0)))
        kg = nezabalene * float(o.get("Gramáž", 0)) / 1000.0
        if kg <= 0: continue
        for zrno, podiel in kavy_recepty[o["Káva"]]["recept"].items():
            potreba[zrno] = potreba.get(zrno, 0) + kg * podiel
    sudy = sudy_zostava_zelena()
    plan = {}
    for zrno in set(potreba) | set(sudy):
        kg = potreba.get(zrno, 0.0)
        v_doze = max(0.0, float(st.session_state.sklad["uprazena"].get(SKU_UPRAZENA.get(zrno), 0.0)))
        chyba = max(0.0, kg - v_doze)
        davky_obj = math.ceil(round(chyba / (1 - STANDARDNY_VYPEK / 100.0), 4) / KAPACITA_ZELENA_BATCH) if chyba > 1e-9 else 0
        davky_sud = math.ceil(round(sudy.get(zrno, 0.0), 4) / KAPACITA_ZELENA_BATCH) if sudy.get(zrno, 0) > 1e-9 else 0
        davky = davky_obj + davky_sud
        plan[zrno] = {"potreba": kg, "v_doze": v_doze, "chyba": chyba, "davky": davky,
                      "davky_obj": davky_obj, "davky_sud": davky_sud,
                      "zelena": davky * KAPACITA_ZELENA_BATCH,
                      "zostatok": v_doze + davky_obj * UPRAZENA_NA_DAVKU - kg}
    return plan

def zostava_pruh():
    objednavky = [o for o in st.session_state.aktualne_objednavky if o.get('❌ Zmazať') != True]
    if not objednavky:
        return
    # Pražiareň – po zrnách v dávkach
    praz = []
    for zrno, pl in sorted(vypocet_planu_prazenia().items()):
        zost = pl["davky"]
        if zost: praz.append(f"<b>{zrno}</b> {zost} {'dávka' if zost == 1 else ('dávky' if zost < 5 else 'dávok')} ({zost * UPRAZENA_NA_DAVKU:g} kg)")
    spolu_d = sum(int(x.split('</b> ')[1].split(' ')[0]) for x in praz) if praz else 0
    # Baliareň – len obaly podľa gramáže
    obaly = {g: 0 for g in gramaze_list}
    for o in objednavky:
        if o.get("Sudy") or o.get("Potvrdene"): continue
        g = int(o.get("Gramáž", 0))
        if g in obaly: obaly[g] += max(0, int(o.get("Kusy", 0)) - int(o.get("Zabalené (ks)", 0)))
    bal = [f"<b>{g} g × {n}</b>" for g, n in obaly.items() if n]

    riadok_p = ("🔥 <b>Zostáva dopražiť:</b> " + " · ".join(praz) + f" &nbsp;=&nbsp; <b>{spolu_d} {'dávka' if spolu_d == 1 else ('dávky' if spolu_d < 5 else 'dávok')} spolu</b>") if praz else "🔥 <b>Pražiareň:</b> ✅ všetko dopražené"
    riadok_b = ("📦 <b>Zostáva zabaliť:</b> " + " · ".join(bal)) if bal else "📦 <b>Baliareň:</b> ✅ všetko zabalené"
    st.markdown(
        "<div style='background:rgba(43,80,152,0.07);border-left:4px solid #2B5098;border-radius:6px;"
        "padding:8px 14px;margin:0 0 12px 0;line-height:1.7;font-size:0.98rem;'>"
        f"{riadok_p}<br>{riadok_b}</div>", unsafe_allow_html=True)

with tab1:
    zostava_pruh()
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
            excel_na_poziadanie("💾 Pripraviť kompletný stav (.xlsx)", vytvor_excel_stavu,
                                f"Kikiriki_STAV_{st.session_state.nazov_prazenia}_{datetime.now().strftime('%Y-%m-%d_%H%M')}.xlsx",
                                "xls_zaloha", use_container_width=True)
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

    eshop_blok_ui()
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
                    auto_uloz(akcia="Stav pred vyčistením stola", detail=f"{pocet} riadkov v knihe")
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
                for zrno, pl in sorted(vypocet_planu_prazenia().items()):
                    finalny_plan.append({"Zelené zrno": zrno, "Treba na nezabalené (kg)": round(pl["potreba"], 2), "V dóze (kg)": round(pl["v_doze"], 2),
                                         "Potrebné upražiť (kg)": round(pl["chyba"], 2), "Dávky na sklad": pl["davky_sud"], "Dávky (á 5kg)": pl["davky"],
                                         "Navážiť zelenú (kg)": pl["zelena"], "Zostatok (kg upraž.)": round(pl["zostatok"], 2)})

                df_plan = pd.DataFrame(finalny_plan)
                st.dataframe(df_plan, use_container_width=True, hide_index=True)

                celkovo_davok = int(df_plan['Dávky (á 5kg)'].sum())
                celkova_zelena = float(df_plan['Navážiť zelenú (kg)'].sum())
                celkova_uprazena = celkova_zelena * (1 - (STANDARDNY_VYPEK / 100.0))
                st.markdown(f"### 🔥 Celkový počet pražení: **{celkovo_davok} dávok**")
                st.markdown(f"### ⚖️ Spolu: **{celkova_zelena:.1f} kg** zelenej ➡️ **{celkova_uprazena:.1f} kg** upraženej (Plán)")
                st.caption(f"Z dóz sa využije {df_plan['V dóze (kg)'].clip(upper=df_plan['Treba na nezabalené (kg)']).sum():.1f} kg už upraženej kávy.")

                total_row_plan = {"Zelené zrno": "🔥 SPOLU:", "Treba na nezabalené (kg)": round(df_plan["Treba na nezabalené (kg)"].sum(), 2),
                                  "V dóze (kg)": round(df_plan["V dóze (kg)"].sum(), 2), "Potrebné upražiť (kg)": round(df_plan["Potrebné upražiť (kg)"].sum(), 2),
                                  "Dávky na sklad": int(df_plan["Dávky na sklad"].sum()),
                                  "Dávky (á 5kg)": celkovo_davok, "Navážiť zelenú (kg)": round(celkova_zelena, 2), "Zostatok (kg upraž.)": ""}
                df_plan_excel = pd.concat([df_plan, pd.DataFrame([total_row_plan])], ignore_index=True)

                # Plán skladania blendov
                finalny_plan_blendov = []
                for meno_blendu, celkova_vaha_blendu in potreba_skladania_blendov.items():
                    for zrno, podiel in kavy_recepty[meno_blendu]["recept"].items():
                        finalny_plan_blendov.append({"Názov blendu": meno_blendu, "Celková hmotnosť (kg)": round(celkova_vaha_blendu, 2),
                                                     "Kávová zložka": zrno, "Podiel v blende": f"{int(round(podiel * 100))}%",
                                                     "Hmotnosť zložky (kg)": round(celkova_vaha_blendu * podiel, 2)})
                df_blendov = pd.DataFrame(finalny_plan_blendov)

                # Sumár obalov (bez dávok do skladu)
                obj_balenie = [o for o in aktivne_objednavky if not o.get('Sudy', False)]
                if obj_balenie:
                    df_sum_obalov = pd.DataFrame(obj_balenie).groupby(['Káva', 'Gramáž'])['Kusy'].sum().reset_index()
                    sum_pivot_ex = df_sum_obalov.pivot(index='Káva', columns='Gramáž', values='Kusy').fillna(0).astype(int)
                    for g in [220, 500, 1000]:
                        if g not in sum_pivot_ex.columns: sum_pivot_ex[g] = 0
                    sum_pivot_ex['Spolu etikiet'] = sum_pivot_ex[[220, 500, 1000]].sum(axis=1)
                    sum_pivot_ex.loc['🔥 SPOLU SÁČKOV'] = sum_pivot_ex.sum(numeric_only=True)
                    sum_pivot_ex = sum_pivot_ex[['Spolu etikiet', 220, 500, 1000]].reset_index()
                    sum_pivot_ex.columns = ['Káva', 'Spolu etikiet', '220g', '500g', '1000g']
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
                        worksheet.freeze_panes(1, 0)
                        header_format = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1})
                        for col_num, value in enumerate(df.columns):
                            worksheet.write(0, col_num, str(value), header_format)
                            max_len = max(df[df.columns[col_num]].map(lambda v: len(str(v))).max(), len(str(value))) + 2
                            worksheet.set_column(col_num, col_num, max_len)
                        format_z1 = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1})
                        format_z2 = workbook.add_format({'bg_color': '#F2F2F2', 'border': 1})
                        format_total = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})
                        format_b1 = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1})
                        format_b2 = workbook.add_format({'bg_color': '#DCE6F1', 'border': 1})
                        group_col_idx = list(df.columns).index(group_by_col) if group_by_col in df.columns else None
                        use_f1, current_val = True, None
                        for r_idx in range(max_row):
                            is_total = str(df.iloc[r_idx, 0]).startswith('🔥')
                            if group_col_idx is not None:
                                val = df.iloc[r_idx, group_col_idx]
                                if current_val is None: current_val = val
                                elif val != current_val: current_val = val; use_f1 = not use_f1
                                fmt = format_total if is_total else (format_b1 if use_f1 else format_b2)
                            else:
                                fmt = format_total if is_total else (format_z1 if r_idx % 2 == 0 else format_z2)
                            for c_idx in range(max_col):
                                cell_val = df.iloc[r_idx, c_idx]
                                if pd.isna(cell_val) if not isinstance(cell_val, str) else False:
                                    worksheet.write(r_idx + 1, c_idx, "", fmt)
                                elif isinstance(cell_val, (int, float)) or hasattr(cell_val, "item"):
                                    worksheet.write_number(r_idx + 1, c_idx, float(cell_val), fmt)
                                else:
                                    worksheet.write(r_idx + 1, c_idx, str(cell_val), fmt)

                    write_styled_sheet(df_plan_excel, 'Plan_Prazenia')
                    write_styled_sheet(df_objednavky_export.drop(columns=['❌ Zmazať'], errors='ignore'), 'Spracovane_Objednavky')
                    if not df_blendov.empty:
                        write_styled_sheet(df_blendov, 'Plan_Blendov', group_by_col='Názov blendu')
                    write_styled_sheet(sum_pivot_ex, 'Sumar_Obalov')

                st.download_button("💾 Stiahnuť profi Excel (plán, objednávky, blendy, obaly)", data=buffer.getvalue(),
                                   file_name=f"KIKIRIKI_plan_{st.session_state.nazov_prazenia}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)

# ========================================================
# TAB 2: PRAŽIAREŇ (Zapisuje pevne do Skladu)
# ========================================================
with tab2:
    zostava_pruh()
    st.markdown("### Panel pri stroji")
    
    st.caption("Plán už počíta s tým, čo je upražené v dózach (aj zo včera) – pražíš len to, čo naozaj chýba na nezabalené objednávky.")
    plan_praz = vypocet_planu_prazenia()

    if not plan_praz:
        st.info("Plán praženia je prázdny. Začni pridaním objednávok.")
    else:
        for zrno, pl in sorted(plan_praz.items(), key=lambda x: (x[1]["davky"] == 0, x[0])):
            stav_z_cloudu = st.session_state.priebeh_prazenia.get(zrno, {"davky_hotovo": 0, "zelena_real": 0.0, "uprazena_real": 0.0, "hotovo": False})
            davky_hotovo = int(stav_z_cloudu.get("davky_hotovo", 0))
            davky_zostava = pl["davky"]
            davky_plan = davky_zostava
            je_hotovo = davky_zostava == 0

            if je_hotovo: stav_text = "✅ V dóze je dosť"
            elif davky_hotovo > 0: stav_text = "🔄 Rozpracované"
            else: stav_text = "⏳ Na rade"

            nadpis = f"{stav_text}: **{zrno}** (" + ("hotovo" if je_hotovo else f"zostáva {davky_zostava} {'dávka' if davky_zostava == 1 else ('dávky' if davky_zostava < 5 else 'dávok')}") + ")"
            with st.expander(nadpis, expanded=not je_hotovo):
                col_info, col_input = st.columns([1, 1])
                with col_info:
                    st.markdown(f"**Treba na nezabalené objednávky:** {pl['potreba']:.2f} kg praženej  \n"
                                f"**V dóze už je:** {pl['v_doze']:.2f} kg  \n"
                                f"**Chýba upražiť:** {pl['chyba']:.2f} kg → {pl['davky_obj']} dávok  \n"
                                + (f"**Skladové dávky (BATCH):** ešte {pl['davky_sud']} dávok  \n" if pl['davky_sud'] else "")
                                + f"**Upražené na túto zmenu:** {davky_hotovo} dávok")
                    if davky_zostava > 0: st.warning(f"**Zostáva upražiť: {davky_zostava} dávok** ({pl['zelena']:g} kg zelenej). Po pražení ostane v dóze navyše {pl['zostatok']:.2f} kg.")
                    else: st.success(f"**Dóza pokrýva objednávky.** Po zabalení ostane v dóze {pl['zostatok']:.2f} kg.")

                with col_input:
                    pridat_davky = st.number_input("Počet práve odpražených dávok:", min_value=1, value=davky_zostava if davky_zostava > 0 else 1, step=1, key=f"davky_{zrno}_{davky_zostava}")
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

                        # najprv sa pokryjú objednávky, čo ostane, ide na skladové dávky
                        na_sudy = max(0, pridat_davky - pl["davky_obj"]) * KAPACITA_ZELENA_BATCH
                        pripisane = pripis_sudy(zrno, na_sudy) if na_sudy else 0.0
                        st.session_state.priebeh_prazenia[zrno]["sudy_zelena"] = stav_z_cloudu.get("sudy_zelena", 0.0) + pripisane
                        st.session_state.pop("tabulka_objednavok", None)

                        auto_uloz(akcia="Praženie", detail=f"{zrno}: +{pridat_davky} dávok (pred pražením chýbalo {davky_plan}"
                                  + (f", z toho {pripisane / KAPACITA_ZELENA_BATCH:g} na sklad" if pripisane else "") + ")", sklad_pred=sklad_pred)
                        st.rerun()

                    if pl["davky_sud"] > 0:
                        if st.button(f"✔️ Skladové dávky {zrno} sú už upražené (len označiť)", key=f"sud_ok_{zrno}",
                                     help="Pre dávky na sklad, ktoré si upražil skôr, napr. včera. Sklad sa nemení, len sa prestanú počítať do plánu."):
                            zostava_sud = sudy_zostava_zelena().get(zrno, 0.0)
                            pripis_sudy(zrno, zostava_sud)
                            st.session_state.pop("tabulka_objednavok", None)
                            auto_uloz(akcia="Skladové dávky označené ako upražené", detail=f"{zrno}: {zostava_sud / KAPACITA_ZELENA_BATCH:g} dávok (bez pohybu skladu)")
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
                            if stav_z_cloudu.get("sudy_zelena", 0.0): odpis_sudy(zrno, stav_z_cloudu["sudy_zelena"])
                            st.session_state.pop("tabulka_objednavok", None)
                            
                            st.session_state.priebeh_prazenia[zrno] = {
                                "davky_hotovo": 0, "zelena_real": 0.0, "uprazena_real": 0.0, "hotovo": False
                            }
                            auto_uloz(akcia="Storno praženia", detail=f"{zrno}: zrušených {davky_hotovo} dávok", sklad_pred=sklad_pred)
                            st.rerun()

# ========================================================
# TAB 3: BALENIE (ČISTÁ VÝROBA, zapisuje pevne do Skladu)
# ========================================================
with tab3:
    zostava_pruh()
    st.markdown("### Baliareň")

    # ---------- RUČNÉ BALENIE (mimo objednávok) ----------
    msg_rb = st.session_state.pop("msg_rucne_balenie", None)
    if msg_rb: st.success(msg_rb)
    if st.toggle("✋ Ručné balenie – mimo objednávok (z toho, čo je v dózach)", key="rb_otvorene"):
      with st.container(border=True):
          NOVY_ZAK, DO_SKLADU = "➕ Nový zákazník…", "📦 Do skladu (bez zákazníka)"
          if st.session_state.pop("_rb_reset", False):
              st.session_state.rb_n = 0
          zakaznici = sorted({o.get('Odberateľ') for o in st.session_state.aktualne_objednavky
                              if not o.get('❌ Zmazať') and not o.get('Sudy') and o.get('Odberateľ')})
          rb1, rb2, rb3, rb4 = st.columns([2.2, 2, 1.2, 1.2], vertical_alignment="bottom")
          with rb1: rb_zak = st.selectbox("Pre koho:", zakaznici + [NOVY_ZAK, DO_SKLADU], key="rb_zak")
          with rb2: rb_kava = st.selectbox("Káva:", list(kavy_recepty.keys()), key="rb_kava")
          with rb3: rb_g = st.selectbox("Gramáž:", gramaze_list, key="rb_g", format_func=lambda x: f"{x} g")
          with rb4: rb_n = st.number_input("Počet (ks):", min_value=0, step=1, key="rb_n")
          rb_novy = st.text_input("Meno nového zákazníka:", key="rb_novy").strip() if rb_zak == NOVY_ZAK else ""

          # kontrola dóz pre zvolenú kávu
          potreba_rb = rb_n * rb_g / 1000.0
          stav_doz = []
          for zrno, podiel in kavy_recepty[rb_kava]["recept"].items():
              v_doze = float(st.session_state.sklad["uprazena"].get(SKU_UPRAZENA.get(zrno), 0.0))
              stav_doz.append((zrno, v_doze, potreba_rb * podiel))
          st.caption("V dóze: " + " · ".join(f"{z} {v:.2f} kg" + (f" (treba {p:.2f})" if rb_n else "") for z, v, p in stav_doz))
          chyba_rb = [f"{z}: chýba {p - v:.2f} kg" for z, v, p in stav_doz if rb_n and p > v + 1e-9]
          if chyba_rb: st.warning("⚠️ V dóze nie je dosť – " + ", ".join(chyba_rb) + ". Zabaliť sa dá, stav dózy pôjde do mínusu.")

          meno_rb = rb_novy if rb_zak == NOVY_ZAK else rb_zak
          if st.button("✅ Zabalené – zapísať", type="primary", key="rb_ok", disabled=(rb_n == 0 or (rb_zak == NOVY_ZAK and not rb_novy))):
              if not je_duplicitny_klik("rucne_balenie", (meno_rb, rb_kava, rb_g, int(rb_n))):
                  sklad_pred = copy.deepcopy(st.session_state.sklad)
                  pc_rb = zapis_balenia_do_skladu(rb_kava, rb_g, int(rb_n))
                  if rb_zak != DO_SKLADU:
                      # zákazníkovi pribudne zabalená položka -> objaví sa v Expedícii aj v Účtovníctve
                      st.session_state.aktualne_objednavky.append({
                          "Odberateľ": meno_rb, "Káva": rb_kava, "Gramáž": rb_g, "Kusy": int(rb_n), "Zabalené (ks)": int(rb_n),
                          "Potvrdene": False, "Sudy": False, "❌ Zmazať": False, "Poznámka": "ručné balenie"})
                      st.session_state.pop("tabulka_objednavok", None)
                  komu = "do skladu" if rb_zak == DO_SKLADU else f"pre {meno_rb}"
                  auto_uloz(akcia="Ručné balenie", detail=f"{rb_kava} {rb_g}g: +{int(rb_n)} ks ({pc_rb}) {komu}", sklad_pred=sklad_pred)
                  st.session_state.msg_rucne_balenie = (f"✅ Zabalené {int(rb_n)}× {rb_kava} {rb_g} g {komu}. "
                                                        + ("Nájdeš ho v Expedícii." if rb_zak != DO_SKLADU else "Je v regáli (Zabalená – PC)."))
                  st.session_state._rb_reset = True
                  st.rerun()
    
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
        if st.session_state.get("balenie_zakaznik") is None:
            st.session_state.balenie_zakaznik = st.query_params.get("balenie_zakaznik")
        if st.session_state.get("balenie_zakaznik") not in moznosti_zak:
            st.session_state.balenie_zakaznik = VSETCI

        def popis_zakaznika(z):
            if z == VSETCI: return VSETCI
            if zostava_zak[z] == 0: return f"✅ {z} – nabalené"
            pol = len({(o['Káva'], o['Gramáž']) for o in aktivne_balenie if o['Odberateľ'] == z and not o.get('Potvrdene')
                       and int(o['Kusy']) > int(o.get('Zabalené (ks)', 0))})
            return f"{z} – zostáva spolu {zostava_zak[z]} ks ({pol} {'položka' if pol == 1 else ('položky' if pol < 5 else 'položiek')})"

        col_ul, col_zak = st.columns([3, 2], vertical_alignment="bottom")
        with col_ul:
            st.markdown("#### 📦 Úlohy pre baliča (Sáčkovanie)")
        with col_zak:
            vybrany_zak = stabilny_selectbox("Balím pre:", moznosti_zak, "balenie_zakaznik", format_func=popis_zakaznika, v_adrese=True)

        msg_bal = st.session_state.pop("msg_balenie", None)
        if msg_bal: st.success(msg_bal)
        msg_bal_ch = st.session_state.pop("msg_balenie_chyba", None)
        if msg_bal_ch: st.error(msg_bal_ch)
        if vybrany_zak == VSETCI:
            st.caption("👥 Počty nižšie sú **za všetkých zákazníkov spolu**. Ak bališ pre konkrétneho, vyber ho vpravo.")
        else:
            st.markdown(f"<div style='font-size:1.05rem;'>👤 Balíš <b>len pre: {vybrany_zak}</b> – počty nižšie sú len jeho.</div>", unsafe_allow_html=True)

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
            """Zapíše presne `pridavam` sáčkov. Pri vybranom zákazníkovi (`prednost`) idú LEN jemu,
            inak postupne na otvorené objednávky. Vráti (navyše, rozdelenie {zákazník: ks})."""
            sklad_pred = copy.deepcopy(st.session_state.sklad)
            zvysok = pridavam
            rozdelenie = {}
            objednavky = st.session_state.aktualne_objednavky
            for idx_o in range(len(objednavky)):
                obj = objednavky[idx_o]
                if zvysok <= 0: break
                if obj.get('❌ Zmazať') or obj.get('Sudy') or obj.get('Potvrdene'): continue
                if prednost and obj.get('Odberateľ') != prednost: continue
                if obj['Káva'] == k and obj['Gramáž'] == g:
                    aktualne_v_obj = int(obj.get('Zabalené (ks)', 0))
                    potreba_v_obj = int(obj['Kusy']) - aktualne_v_obj
                    if potreba_v_obj > 0:
                        dam = min(zvysok, potreba_v_obj)
                        st.session_state.aktualne_objednavky[idx_o]['Zabalené (ks)'] = aktualne_v_obj + dam
                        rozdelenie[obj['Odberateľ']] = rozdelenie.get(obj['Odberateľ'], 0) + dam
                        zvysok -= dam

            # ZÁPIS DO PEVNÉHO SKLADU
            pc_sku = zapis_balenia_do_skladu(k, g, pridavam)

            detail = (f"{k} {g}g: +{pridavam} ks ({pc_sku}) → " + ", ".join(f"{z} {n}" for z, n in rozdelenie.items())
                      + (f", {zvysok} ks navyše do regálu" if zvysok > 0 else ""))
            auto_uloz(akcia="Balenie", detail=detail, sklad_pred=sklad_pred)
            return zvysok, rozdelenie

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
                        nedost = []
                        for mat_sku in karty_na_odpis(p['kava'], p['gramaz']):
                            karta_m = st.session_state.sklad["karty"][mat_sku]
                            ma = int(st.session_state.sklad[karta_m["typ"]].get(mat_sku, 0))
                            if ma < chýba_ks: nedost.append(f"{karta_m['nazov']} (máš {ma})")
                        if nedost: st.warning(f"⚠️ Na {chýba_ks} ks {p['kava']} {p['gramaz']} g nie je dosť " + " a ".join(nedost) + ".")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if chýba_ks <= 0: st.markdown(f"✅ **{p['gramaz']}g** sáčok - Vyrobených {p['hotovo']} / {p['ciel']} ks")
                        else: st.markdown(f"➡️ **{p['gramaz']}g** sáčok - Už vyrobené {p['hotovo']} ks (Chýba dorobiť **{chýba_ks} ks**)")
                    with col2:
                        if chýba_ks > 0:
                            with st.form(key=f"form_bag_{p['kava']}_{p['gramaz']}", clear_on_submit=True):
                                pocet_ks = st.number_input("Počet sáčkov (ks):", min_value=0, value=0, step=1,
                                                           key=f"add_bag_{p['kava']}_{p['gramaz']}",
                                                           help=f"Najviac {chýba_ks} ks – toľko chýba {'pre ' + prednost if prednost else 'na všetky objednávky'}. Navyše bal cez ✋ Ručné balenie.")
                                odoslat = st.form_submit_button("✅ Potvrdiť", use_container_width=True)
                            if odoslat and pocet_ks > chýba_ks:
                                st.session_state.msg_balenie_chyba = (
                                    f"⚠️ Nič som nezapísal: zadal si {int(pocet_ks)} ks {p['kava']} {p['gramaz']} g, ale "
                                    + (f"pre **{prednost}**" if prednost else "na všetky objednávky") + f" chýba len **{chýba_ks} ks**. "
                                    "Zobrazenie sa medzitým prepočítalo (napr. po výbere zákazníka) – skontroluj a zadaj znova. "
                                    "Viac kusov zabalíš cez ✋ Ručné balenie.")
                                st.rerun()
                            elif odoslat and pocet_ks > 0:
                                if je_duplicitny_klik(f"bag_{p['kava']}_{p['gramaz']}", int(pocet_ks)):
                                    st.warning("Dvojklik zachytený – započítané len raz.")
                                else:
                                    navyse, rozdel = pridaj_sacky(p['kava'], p['gramaz'], int(pocet_ks), prednost=prednost)
                                    st.session_state.msg_balenie = (f"✅ {int(pocet_ks)}× {p['kava']} {p['gramaz']} g → "
                                                                    + ", ".join(f"**{z}** {n} ks" for z, n in rozdel.items())
                                                                    + (f" · {navyse} ks navyše do regálu" if navyse else ""))
                                    st.rerun()

# ========================================================
# TAB 4: SKLAD (GC / RC / Zabalená PC / Obaly a samolepky + Inventúra)
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
        je_ks = typ in ["zabalena"] + TYPY_MATERIAL
        riadky = []
        for sku, hodnota in st.session_state.sklad[typ].items():
            if typ in TYPY_MATERIAL and not st.session_state.sklad.get("karty", {}).get(sku, {}).get("aktivna", True): continue
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
    zostava_pruh()
    hs1, hs2, hs3 = st.columns([3, 1.3, 1.3], vertical_alignment="bottom")
    with hs1:
        st.markdown("### Sklad")
    with hs2:
        excel_na_poziadanie("📊 Stav skladu (.xlsx)", excel_stav_skladu,
                            f"Kikiriki_Stav_skladu_{datetime.now().strftime('%Y-%m-%d_%H%M')}.xlsx", "xls_stav_skladu",
                            use_container_width=True, help="Aktuálny stav – každý sklad na samostatnom hárku (GC, RC, Zabalená-PC, Obaly, Samolepky)")
    with hs3:
        if st.button("📒 Skladové karty", use_container_width=True, help="Všetky pohyby po kartách s príjmom, výdajom a zostatkom"):
            st.session_state.karty_otvorene = True
            try:
                st.session_state.karty_df = skladove_karty_df(nacitaj_log())
            except Exception as e:
                st.session_state.karty_df = None
                st.error(f"Pohyby sa nepodarilo načítať z cloudu: {e}")

    if st.session_state.get("karty_otvorene") and st.session_state.get("karty_df") is not None:
        df_k = st.session_state.karty_df
        with st.container(border=True):
            k1, k2, k3 = st.columns([2.5, 1.3, 0.6], vertical_alignment="bottom")
            vsetky_karty = [(t, s_) for t in KATEGORIE_KARIET for s_ in st.session_state.sklad.get(t, {})]
            with k1:
                vyb_k = st.selectbox("📒 Skladová karta:", list(range(len(vsetky_karty))), key="karta_vyber",
                                     format_func=lambda i: f"{vsetky_karty[i][1]} – {nazov_sku(*vsetky_karty[i])} ({KATEGORIE_KARIET[vsetky_karty[i][0]][0]})")
            with k2:
                st.download_button("⬇️ Všetky karty (.xlsx)", data=excel_skladove_karty(df_k),
                                   file_name=f"Kikiriki_Skladove_karty_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="primary")
            with k3:
                if st.button("✖", key="karty_zavriet", help="Zavrieť", use_container_width=True):
                    st.session_state.karty_otvorene = False; st.rerun()
            t_k, s_k = vsetky_karty[vyb_k]
            pohyby_k = df_k[df_k["SKU"] == s_k].drop(columns=["SKU", "Názov", "Kategória"])
            mj_k = KATEGORIE_KARIET[t_k][1]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Aktuálny stav", f"{float(st.session_state.sklad[t_k][s_k]):g} {mj_k}")
            m2.metric("Príjem spolu", f"{pohyby_k['Príjem'].sum():g} {mj_k}")
            m3.metric("Výdaj spolu", f"{pohyby_k['Výdaj'].sum():g} {mj_k}")
            m4.metric("Pohybov", len(pohyby_k))
            if pohyby_k.empty:
                st.caption("Na tejto karte zatiaľ nie je žiadny pohyb.")
            else:
                st.dataframe(pohyby_k.iloc[::-1], hide_index=True, use_container_width=True, height=min(400, 38 + 35 * len(pohyby_k)))
            st.caption("Karty sa skladajú z logu – rozširujú sa samy pri každom praženiu, balení, expedícii, príjme a inventúre.")

    odomknute = st.session_state.get("admin_odomknute", False)

    tab_gc, tab_rc, tab_pc, tab_ob = st.tabs(["**GC – Zelená káva**", "**RC – Upražená (dózy)**", "**Zabalená – PC**", "**Obaly a samolepky**"])

    # ---------- GC ----------
    with tab_gc:
        st.caption("Zelená káva vo vreciach. Stav sa napĺňa inventúrou, praženie ho automaticky znižuje.")
        df_gc = pd.DataFrame([{"SKU": sku, "Názov": NAZVY_ZELENA.get(sku, ""), "Stav (kg)": round(float(v), 2)}
                              for sku, v in st.session_state.sklad["zelena"].items()])
        c1, c2 = st.columns(2)
        c1.metric("Zelená spolu", f"{df_gc['Stav (kg)'].sum():.2f} kg")
        c2.metric("Druhov na sklade", int((df_gc["Stav (kg)"] > 0).sum()))
        fx1, fx2 = st.columns([3, 1], vertical_alignment="bottom")
        with fx1: f_t_gc = st.text_input("Hľadať:", key="gc_f_text", placeholder="kód, názov…")
        with fx2: f_n_gc = st.toggle("Aj nulové", value=True, key="gc_aj_nulove")
        if f_t_gc: df_gc = df_gc[df_gc.apply(lambda r_: f_t_gc.lower() in " ".join(map(str, r_.values)).lower(), axis=1)]
        if not f_n_gc: df_gc = df_gc[df_gc["Stav (kg)"] != 0]
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
        fx1, fx2 = st.columns([3, 1], vertical_alignment="bottom")
        with fx1: f_t_rc = st.text_input("Hľadať:", key="rc_f_text", placeholder="kód, názov…")
        with fx2: f_n_rc = st.toggle("Aj nulové", value=True, key="rc_aj_nulove")
        if f_t_rc: df_rc = df_rc[df_rc.apply(lambda r_: f_t_rc.lower() in " ".join(map(str, r_.values)).lower(), axis=1)]
        if not f_n_rc: df_rc = df_rc[df_rc["Stav (kg)"] != 0]
        st.dataframe(df_rc.style.map(zafarbi_zaporne, subset=["Stav (kg)"]).format({"Stav (kg)": "{:.2f}"}),
                     use_container_width=True, hide_index=True)
        inventura_editor("uprazena", "kg", "RC Dózy", odomknute)

    # ---------- VÝROBKY ----------
    with tab_pc:
        st.caption("Hotové zabalené sáčky na sklade. Balenie pridáva, expedícia odoberá.")
        rows_pc = []
        for sku, ks in st.session_state.sklad["zabalena"].items():
            g = gramaz_z_pc(sku)
            kava_pc = PC_NA_KAVU.get(sku, (NAZVY_ZABALENA.get(sku, sku), g))[0]
            rows_pc.append({"Káva": kava_pc, "Gramáž": g, "SKU": sku, "Stav (ks)": int(ks), "Váha (kg)": round(int(ks) * g / 1000.0, 2)})
        df_pc = pd.DataFrame(rows_pc)

        # --- filtre ako v Exceli ---
        fp1, fp2, fp3, fp4 = st.columns([2.2, 1.6, 1.6, 1.2], vertical_alignment="bottom")
        with fp1: f_kava = st.multiselect("Káva:", sorted(df_pc["Káva"].unique()), key="pc_f_kava", placeholder="všetky")
        with fp2: f_gram = st.multiselect("Gramáž:", gramaze_list, key="pc_f_gram", placeholder="všetky", format_func=lambda x: f"{x} g")
        with fp3: f_text = st.text_input("Hľadať:", key="pc_f_text", placeholder="kód, názov…")
        with fp4: aj_nulove = st.toggle("Aj nulové", value=False, key="pc_aj_nulove")
        df_f = df_pc.copy()
        if f_kava: df_f = df_f[df_f["Káva"].isin(f_kava)]
        if f_gram: df_f = df_f[df_f["Gramáž"].isin(f_gram)]
        if f_text: df_f = df_f[df_f.apply(lambda r_: f_text.lower() in " ".join(map(str, r_.values)).lower(), axis=1)]
        if not aj_nulove: df_f = df_f[df_f["Stav (ks)"] != 0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Sáčkov (vo filtri)", int(df_f["Stav (ks)"].sum()))
        c2.metric("Váha (vo filtri)", f"{df_f['Váha (kg)'].sum():.2f} kg")
        c3.metric("Druhov", int((df_f["Stav (ks)"] != 0).sum()))

        if df_f.empty:
            st.info("Pre tento filter nie sú na sklade žiadne zabalené sáčky.")
        else:
            # Prehľad káva × gramáž
            piv_pc = df_f.pivot_table(index="Káva", columns="Gramáž", values="Stav (ks)", aggfunc="sum", fill_value=0)
            for g_ in gramaze_list:
                if g_ not in piv_pc.columns: piv_pc[g_] = 0
            piv_pc = piv_pc[[g_ for g_ in gramaze_list if (not f_gram or g_ in f_gram)]]
            piv_pc["Spolu (ks)"] = piv_pc.sum(axis=1)
            piv_pc["Spolu (kg)"] = sum(piv_pc[g_] * g_ for g_ in piv_pc.columns if isinstance(g_, int)) / 1000.0
            piv_pc = piv_pc.rename(columns={g_: f"{g_} g" for g_ in gramaze_list})
            if not aj_nulove: piv_pc = piv_pc[piv_pc["Spolu (ks)"] != 0]
            st.markdown("##### Prehľad: káva × gramáž (ks)")
            st.dataframe(piv_pc.style.map(zafarbi_zaporne).map(lambda v: "color:#BBBBBB;" if v == 0 else "", subset=[c for c in piv_pc.columns if c.endswith(" g")])
                         .format({"Spolu (kg)": "{:.2f}"}),
                         use_container_width=True)
            with st.expander("Detail po kartách (SKU)"):
                st.dataframe(df_f.sort_values(["Káva", "Gramáž"]).style.map(zafarbi_zaporne, subset=["Stav (ks)", "Váha (kg)"]).format({"Váha (kg)": "{:.2f}"}),
                             use_container_width=True, hide_index=True)
            st.caption("Tip: kliknutím na hlavičku stĺpca tabuľku zoradíš.")
        inventura_editor("zabalena", "ks", "Zabalená PC", odomknute)

    # ---------- OBALY A SAMOLEPKY ----------
    with tab_ob:
        st.caption("Prázdne sáčky a samolepky. Pri balení sa automaticky odpisujú podľa pravidla na karte. "
                   "Karty pridáš a upravíš v 🔒 Správa skladu → 🗂️ Skladové karty.")
        sk = st.session_state.sklad
        minima = sk.setdefault("minima", {})
        karty_akt = karty_materialu()

        # potreba na ešte nezabalené otvorené objednávky (podľa pravidiel odpisu)
        potreba = {}
        for o in st.session_state.aktualne_objednavky:
            if o.get('❌ Zmazať') or o.get('Sudy') or o.get('Potvrdene'): continue
            chyba_zab = max(0, int(o.get('Kusy', 0)) - int(o.get('Zabalené (ks)', 0)))
            if chyba_zab:
                for mat_sku in karty_na_odpis(o.get('Káva'), o.get('Gramáž', 0)):
                    potreba[mat_sku] = potreba.get(mat_sku, 0) + chyba_zab

        def tabulka_mat(typ):
            riadky = []
            for s_, k in karty_akt.items():
                if k["typ"] != typ: continue
                stav = int(sk[typ].get(s_, 0)); mn = int(minima.get(s_, 0)); pot = int(potreba.get(s_, 0))
                po_zabaleni = stav - pot
                if stav < 0 or po_zabaleni < 0: sig = "🔴 Chýba"
                elif mn and po_zabaleni < mn: sig = "🟠 Objednať"
                else: sig = "🟢 OK"
                riadky.append({"Stav": sig, "SKU": s_, "Názov": k["nazov"], "Na sklade (ks)": stav,
                               "Treba na otvorené obj.": pot, "Zostane po zabalení": po_zabaleni, "Minimum": mn,
                               "Dokúpiť (ks)": max(0, (mn - po_zabaleni) if mn else -po_zabaleni), "Odpis": popis_odpisu(k.get("odpis"))})
            return pd.DataFrame(riadky, columns=["Stav", "SKU", "Názov", "Na sklade (ks)", "Treba na otvorené obj.",
                                                 "Zostane po zabalení", "Minimum", "Dokúpiť (ks)", "Odpis"])

        df_ob, df_sa = tabulka_mat("obaly"), tabulka_mat("samolepky")
        na_nakup = pd.concat([df_ob, df_sa]); na_nakup = na_nakup[na_nakup["Dokúpiť (ks)"] > 0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Obaly spolu", int(df_ob["Na sklade (ks)"].sum()))
        c2.metric("Samolepky spolu", int(df_sa["Na sklade (ks)"].sum()))
        c3.metric("Položiek na nákup", len(na_nakup))
        if not na_nakup.empty:
            st.error("🛒 **Treba nakúpiť:** " + ", ".join(f"{r['Názov']} – {r['Dokúpiť (ks)']} ks" for _, r in na_nakup.iterrows()))

        farba = lambda v: ("color:#C0392B;font-weight:800;" if str(v).startswith("🔴") else ("color:#D35400;font-weight:800;" if str(v).startswith("🟠") else ""))
        for nadpis, df_m, kluc in (("Obaly", df_ob, "ob"), ("Samolepky", df_sa, "sa")):
            st.markdown(f"##### {nadpis}")
            if df_m.empty:
                st.caption("Žiadne aktívne karty.")
                continue
            st.dataframe(df_m.style.map(farba, subset=["Stav"]).map(zafarbi_zaporne, subset=["Na sklade (ks)", "Zostane po zabalení"]),
                         use_container_width=True, hide_index=True)

        # --- PRÍJEM / VÝDAJ ---
        vsetky_mat = {s_: k["nazov"] for s_, k in karty_akt.items()}
        msg_pr = st.session_state.pop("msg_prijem", None)
        if msg_pr: st.success(msg_pr)
        if vsetky_mat:
            with st.expander("📥 Príjem / 📤 Výdaj materiálu"):
                with st.form("form_pohyb_mat", clear_on_submit=True):
                    p0, p1, p2 = st.columns([1.3, 3, 1.3])
                    with p0: smer = st.radio("Pohyb:", ["📥 Príjem", "📤 Výdaj"], horizontal=False)
                    with p1: mat_sku = st.selectbox("Položka:", list(vsetky_mat), format_func=lambda x: f"{vsetky_mat[x]} ({x})")
                    with p2: mat_ks = st.number_input("Počet (ks):", min_value=0, step=10)
                    poznamka = st.text_input("Poznámka (dodávateľ, faktúra, dôvod výdaja):")
                    ok_pohyb = st.form_submit_button("💾 Zapísať pohyb", type="primary")
                st.caption("Výdaj použi pri kartách bez automatiky alebo pri škode / poškodení. Bežné balenie sa odpisuje samo.")
            if ok_pohyb and mat_ks > 0:
                if not je_duplicitny_klik(f"pohyb_{mat_sku}_{smer}", int(mat_ks)):
                    sklad_pred = copy.deepcopy(sk)
                    typ_m = sk["karty"][mat_sku]["typ"]
                    znamienko = 1 if smer.startswith("📥") else -1
                    sk[typ_m][mat_sku] = int(sk[typ_m].get(mat_sku, 0)) + znamienko * int(mat_ks)
                    akcia_m = "Príjem materiálu" if znamienko > 0 else "Výdaj materiálu"
                    auto_uloz(historia=True, akcia=akcia_m, detail=f"{vsetky_mat[mat_sku]}: {'+' if znamienko > 0 else '−'}{int(mat_ks)} ks" + (f" | {poznamka}" if poznamka else ""), sklad_pred=sklad_pred)
                    st.session_state.msg_prijem = f"{smer.split()[0]} {vsetky_mat[mat_sku]}: {'+' if znamienko > 0 else '−'}{int(mat_ks)} ks"
                    st.rerun()

        inventura_editor("obaly", "ks", "Obaly", odomknute)
        inventura_editor("samolepky", "ks", "Samolepky", odomknute)


# ========================================================
# TAB 5: EXPEDÍCIA (LOGISTIKA)
# ========================================================
with tab5:
    zostava_pruh()
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
    if st.session_state.get("exp_zakaznik") is None:
        st.session_state.exp_zakaznik = st.query_params.get("exp_zakaznik")
    if st.session_state.get("exp_zakaznik") not in moznosti:
        st.session_state.exp_zakaznik = NIKTO

    col_h, col_r = st.columns([3, 2], vertical_alignment="bottom")
    with col_h:
        st.markdown("### Expedícia (Kuriér)")
    with col_r:
        odb = stabilny_selectbox("Zákazník:", moznosti, "exp_zakaznik", format_func=popis_odb, v_adrese=bool(odberatelia), disabled=not odberatelia)

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
            stabilny_selectbox("Krabica:", moznosti_krab, k_krab,
                               format_func=lambda i: f"Krabica č. {i+1} ({sum(krabice[i].values())} ks)" if i < len(krabice) else f"➕ Nová krabica č. {i+1}")
        with f2:
            stabilny_selectbox("Káva:", [VSETKY] + kavy_moz, k_kava,
                               format_func=lambda k: k if k == VSETKY else f"{k} – zostáva {zost_kava(k)} ks")
        with f3:
            stabilny_selectbox("Gramáž:", [VSETKY] + gram_moz, k_gram,
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
                    max_len = max(df_export[df_export.columns[col_num]].map(lambda v: len(str(v))).max(), len(str(value))) + 2
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


# ========================================================
# TAB 7: ŠTATISTIKY (automaticky z logu – praženie, balenie, expedícia)
# ========================================================
AKCIA_START_STAT = "Štart štatistík"
AKCIA_RUCNE_PRAZENIE = "Ručný záznam praženia"
AKCIA_KOREKCIA_STAT = "Štatistika – korekcie"

def statistiky_z_logu(df_log):
    """Z logu vytiahne pohyby: praženie (GC−, RC+), balenie (PC+), expedícia (PC−).
    Počíta sa len od posledného „Štart štatistík“ (skúšobné a zmazané pohyby pred ním sa ignorujú)
    + ručné záznamy praženia (napr. dávky upražené pred štartom evidencie). Vráti DataFrame pohybov."""
    if df_log is None or df_log.empty or "SKU" not in df_log.columns:
        return pd.DataFrame()
    df_log = df_log.copy()
    df_log["_cas"] = pd.to_datetime(df_log["Čas"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
    starty = df_log.loc[df_log["Akcia"].astype(str) == AKCIA_START_STAT, "_cas"].dropna()
    start = starty.max() if len(starty) else None
    if start is not None:
        df_log = df_log[df_log["_cas"] >= start]
    # ručné záznamy praženia -> umelé riadky GC−/RC+ s dátumom, ktorý zadal používateľ
    umele = []
    for _, r_ in df_log[df_log["Akcia"].astype(str) == AKCIA_RUCNE_PRAZENIE].iterrows():
        try:
            pole = dict(x.split("=", 1) for x in str(r_["Detail"]).split(";") if "=" in x)
            zrno, davky, datum = pole["ZRNO"], float(pole["DAVKY"]), pole["DATUM"]
        except Exception:
            continue
        cas_txt = f"{datum} 12:00:00"
        umele.append({"Čas": cas_txt, "Akcia": "Praženie (ručný záznam)", "Detail": f"{zrno}: {davky:g} dávok",
                      "SKU": SKU_ZELENA.get(zrno, "GC?"), "Názov": zrno, "Zmena": str(-davky * KAPACITA_ZELENA_BATCH), "_kcas": r_["Čas"]})
        umele.append({"Čas": cas_txt, "Akcia": "Praženie (ručný záznam)", "Detail": f"{zrno}: {davky:g} dávok",
                      "SKU": SKU_UPRAZENA.get(zrno, "RC?"), "Názov": zrno, "Zmena": str(davky * UPRAZENA_NA_DAVKU), "_kcas": r_["Čas"]})
    # korekcie zo štatistiky (vylúčiť / zmeniť počet dávok) – posledná úprava platí
    korekcie = {}
    for _, r_ in df_log[df_log["Akcia"].astype(str) == AKCIA_KOREKCIA_STAT].sort_values("_cas").iterrows():
        try: korekcie.update(json.loads(str(r_["Detail"])))
        except Exception: pass
    if "_kcas" not in df_log.columns: df_log["_kcas"] = df_log["Čas"]
    df_log["_kcas"] = df_log["_kcas"].fillna(df_log["Čas"])
    if umele:
        df_log = pd.concat([df_log, pd.DataFrame(umele)], ignore_index=True)
    d = df_log[df_log["SKU"].astype(str).str.len() > 0].copy()
    d["zmena"] = pd.to_numeric(d["Zmena"].astype(str).str.replace(",", "."), errors="coerce").fillna(0)
    d["cas"] = pd.to_datetime(d["Čas"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
    d = d.dropna(subset=["cas"])
    d["mesiac"] = d["cas"].dt.to_period("M")
    d["den"] = d["cas"].dt.date
    akc = d["Akcia"].astype(str)
    sku = d["SKU"].astype(str)
    d["druh"] = None
    d.loc[akc.str.startswith(("Praženie", "Storno praženia")) & sku.str.startswith("GC"), "druh"] = "zelena"
    d.loc[akc.str.startswith(("Praženie", "Storno praženia")) & sku.str.startswith("RC"), "druh"] = "uprazena"
    d.loc[akc.str.startswith(("Balenie", "Ručné balenie")) & sku.str.startswith("PC"), "druh"] = "zabalene"
    d.loc[akc.str.contains("xpedíc", regex=False) & sku.str.startswith("PC"), "druh"] = "expedovane"
    d = d[d["druh"].notna()].copy()
    d["gramaz"] = d["SKU"].map(lambda x: gramaz_z_pc(x) if str(x).startswith("PC") else 0)
    d["nazov"] = [n if n else s_ for n, s_ in zip(d["Názov"].astype(str), d["SKU"])]
    # kľúč praženia (spája GC− a RC+ riadok tej istej udalosti)
    zrno_z_sku = {**{v: k for k, v in SKU_ZELENA.items()}, **{v: k for k, v in SKU_UPRAZENA.items()}}
    d["kluc"] = [f"{kc}|{sk_}" if str(sk_).startswith("PC") else f"{kc}|{zrno_z_sku.get(sk_, n_)}"
                 for kc, sk_, n_ in zip(d["_kcas"].astype(str), d["SKU"].astype(str), d["nazov"])]
    d["vylucene"] = False
    for kl, k in korekcie.items():
        m = d["kluc"] == kl
        if not m.any(): continue
        if k.get("x"):
            d.loc[m, "vylucene"] = True
        elif k.get("d") is not None:
            dv_ = float(k["d"])
            d.loc[m & (d["druh"] == "zelena"), "zmena"] = -dv_ * KAPACITA_ZELENA_BATCH
            d.loc[m & (d["druh"] == "uprazena"), "zmena"] = dv_ * UPRAZENA_NA_DAVKU
            d.loc[m & (d["druh"] == "zabalene"), "zmena"] = dv_
            d.loc[m & (d["druh"] == "expedovane"), "zmena"] = -dv_
    d.attrs["start"] = start
    return d

with tab7:
    st.markdown("### Štatistiky")
    st.caption("Počítané automaticky z logu – pražené dávky, zabalené sáčky a expedícia. Bez ručného zadávania.")
    if st.button("🔄 Načítať štatistiky z cloudu", type="primary", key="btn_stat"):
        try:
            st.session_state.stat_df = statistiky_z_logu(nacitaj_log())
        except Exception as e:
            st.session_state.stat_df = None
            st.error(f"Log sa nepodarilo načítať: {e}")

    def nacitaj_stat():
        st.session_state.stat_df = statistiky_z_logu(nacitaj_log())

    msg_st = st.session_state.pop("msg_stat", None)
    if msg_st: st.success(msg_st)

    # --- Úprava štatistík (len odomknuté) ---
    with st.expander("⚙️ Úprava štatistík – štart odznova a ručné záznamy"):
        if not st.session_state.get("admin_odomknute", False):
            st.caption("🔒 Odomkni zámkom vpravo hore.")
        else:
            st.markdown("**1) Začať štatistiky odznova** – všetko pred týmto okamihom (skúšky, zmazané pokusy) sa prestane počítať. "
                        "Log ani sklad sa nemažú.")
            potvrd_start = st.checkbox("Áno, chcem začať štatistiky od teraz.", key="stat_start_ok")
            if st.button("🧹 Začať štatistiky od teraz", disabled=not potvrd_start, key="stat_start_btn"):
                auto_uloz(akcia=AKCIA_START_STAT, detail="Štatistiky sa počítajú od tohto okamihu")
                try: nacitaj_stat()
                except Exception: pass
                st.session_state.msg_stat = "Štatistiky začínajú od teraz. Ak chceš doplniť skoršie reálne praženia, zapíš ich nižšie."
                st.rerun()
            st.markdown("**2) Ručný záznam praženia** – doplní do štatistiky dávky upražené skôr (napr. včerajších 17). "
                        "**Sklad sa nemení.**")
            with st.form("form_rucne_prazenie", clear_on_submit=True):
                q1, q2, q3 = st.columns([1.3, 2, 1])
                with q1: rz_datum = st.date_input("Dátum:", value=datetime.now().date() - timedelta(days=1), format="DD.MM.YYYY")
                with q2: rz_zrno = st.selectbox("Zrno:", list(SKU_ZELENA.keys()))
                with q3: rz_davky = st.number_input("Dávky:", min_value=0, step=1)
                ok_rz = st.form_submit_button("➕ Zapísať do štatistiky", type="primary")
            if ok_rz and rz_davky > 0:
                auto_uloz(akcia=AKCIA_RUCNE_PRAZENIE, detail=f"ZRNO={rz_zrno};DAVKY={int(rz_davky)};DATUM={rz_datum.strftime('%d.%m.%Y')}")
                try: nacitaj_stat()
                except Exception: pass
                st.session_state.msg_stat = f"Zapísané: {rz_zrno} {int(rz_davky)} dávok ({rz_datum.strftime('%d.%m.%Y')})."
                st.rerun()

    d_vsetko = st.session_state.get("stat_df")
    d = d_vsetko[~d_vsetko["vylucene"]] if (d_vsetko is not None and not d_vsetko.empty and "vylucene" in d_vsetko.columns) else d_vsetko
    if d is not None:
        d.attrs = dict(getattr(d_vsetko, "attrs", {}))
    if d is not None and d.attrs.get("start") is not None:
        st.caption(f"📍 Štatistiky sa počítajú od {d.attrs['start'].strftime('%d.%m.%Y %H:%M')} (+ ručné záznamy).")
    if d is not None and d.empty:
        st.info("V logu zatiaľ nie sú žiadne praženia, balenia ani expedície.")
    elif d is not None:
        mesiace = sorted(d["mesiac"].unique(), reverse=True)
        moznosti_obd = ["Všetko"] + [m.strftime("%m / %Y") for m in mesiace]
        obd = st.selectbox("Obdobie:", moznosti_obd, key="stat_obdobie")
        dv = d if obd == "Všetko" else d[d["mesiac"].map(lambda m: m.strftime("%m / %Y")) == obd]

        zel = -dv.loc[dv["druh"] == "zelena", "zmena"].sum()
        upr = dv.loc[dv["druh"] == "uprazena", "zmena"].sum()
        zab = dv[dv["druh"] == "zabalene"]; exp_ = dv[dv["druh"] == "expedovane"]
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Upražených dávok", f"{zel / KAPACITA_ZELENA_BATCH:.0f}")
        k2.metric("Zelenej spotrebované", f"{zel:.1f} kg")
        k3.metric("Upraženej", f"{upr:.1f} kg")
        k4.metric("Zabalených sáčkov", int(zab["zmena"].sum()))
        k5.metric("Expedovaných sáčkov", int(-exp_["zmena"].sum()))

        # Súhrn po mesiacoch
        def suhrn(skupina):
            g = d.groupby(skupina)
            out = pd.DataFrame({
                "Dávky": g.apply(lambda x: -x.loc[x["druh"] == "zelena", "zmena"].sum() / KAPACITA_ZELENA_BATCH),
                "Zelená (kg)": g.apply(lambda x: -x.loc[x["druh"] == "zelena", "zmena"].sum()),
                "Upražená (kg)": g.apply(lambda x: x.loc[x["druh"] == "uprazena", "zmena"].sum()),
                "Zabalené (ks)": g.apply(lambda x: x.loc[x["druh"] == "zabalene", "zmena"].sum()),
                "Zabalené (kg)": g.apply(lambda x: (x.loc[x["druh"] == "zabalene", "zmena"] * x.loc[x["druh"] == "zabalene", "gramaz"]).sum() / 1000),
                "Expedované (ks)": g.apply(lambda x: -x.loc[x["druh"] == "expedovane", "zmena"].sum()),
            }).round(2)
            return out
        st.markdown("#### 📅 Súhrn po mesiacoch")
        sm = suhrn("mesiac").sort_index(ascending=False)
        sm.index = [m.strftime("%m / %Y") for m in sm.index]; sm.index.name = "Mesiac"
        st.dataframe(sm, use_container_width=True)

        st.markdown(f"#### 🔥 Praženie po zrnách ({obd})")
        pz = dv[dv["druh"] == "zelena"].groupby("nazov")["zmena"].sum().mul(-1)
        if pz.empty:
            st.caption("V tomto období sa nepražilo.")
        else:
            df_pz = pd.DataFrame({"Zelená (kg)": pz.round(1), "Dávky": (pz / KAPACITA_ZELENA_BATCH).round(1)}).sort_values("Zelená (kg)", ascending=False)
            df_pz.index.name = "Zrno"
            c_a, c_b = st.columns([1, 1])
            c_a.dataframe(df_pz, use_container_width=True)
            c_b.bar_chart(df_pz["Dávky"], horizontal=True, height=max(220, 32 * len(df_pz)))

        zv = d_vsetko if obd == "Všetko" else d_vsetko[d_vsetko["mesiac"].map(lambda m: m.strftime("%m / %Y")) == obd]

        def editor_zoznamu(nadpis, druh, stlpec, prepocet, kluc_ed):
            """Zoznam udalostí jedného druhu s možnosťou zmeniť množstvo alebo zaškrtnúť Nepočítať."""
            with st.expander(f"📋 {nadpis} ({obd}) – čo sa započítalo · úprava a mazanie"):
                zp = zv[zv["druh"] == druh].copy()
                if zp.empty:
                    st.caption("Žiadne záznamy."); return
                zp[stlpec] = (zp["zmena"] * prepocet).round(2)
                zp["Nepočítať"] = zp["vylucene"]
                tab_zp = (zp.sort_values("cas", ascending=False)[["Čas", "nazov", stlpec, "Nepočítať", "Akcia", "Detail", "kluc"]]
                          .rename(columns={"nazov": "Položka"}))
                if not st.session_state.get("admin_odomknute", False):
                    st.dataframe(tab_zp.drop(columns=["kluc"]), hide_index=True, use_container_width=True)
                    st.caption("🔒 Úpravu a mazanie odomkneš zámkom vpravo hore."); return
                st.caption(f"Uprav **{stlpec}** alebo zaškrtni **Nepočítať** (skúšky, omyly) a daj Uložiť. Log ani sklad sa nemenia – mení sa len štatistika.")
                ed_zp = st.data_editor(tab_zp, hide_index=True, use_container_width=True, key=f"ed_{kluc_ed}_{obd}",
                                       disabled=["Čas", "Položka", "Akcia", "Detail", "kluc"], column_config={
                                           "kluc": None,
                                           stlpec: st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%g"),
                                           "Nepočítať": st.column_config.CheckboxColumn()})
                if st.button("💾 Uložiť úpravy štatistiky", key=f"btn_ulozit_{kluc_ed}", type="primary"):
                    povodne = {r_["kluc"]: r_ for r_ in tab_zp.to_dict("records")}
                    zmeny = {}
                    for r_ in ed_zp.to_dict("records"):
                        p_ = povodne.get(r_["kluc"])
                        if p_ is None: continue
                        if bool(r_["Nepočítať"]) != bool(p_["Nepočítať"]) or abs(float(r_[stlpec] or 0) - float(p_[stlpec])) > 1e-9:
                            zmeny[r_["kluc"]] = {"x": True} if r_["Nepočítať"] else {"x": False, "d": float(r_[stlpec] or 0)}
                    if zmeny:
                        polozky_z = list(zmeny.items())
                        for i_z in range(0, len(polozky_z), 10):     # po 10 kusoch (detail v logu má limit dĺžky)
                            auto_uloz(akcia=AKCIA_KOREKCIA_STAT, detail=json.dumps(dict(polozky_z[i_z:i_z + 10]), ensure_ascii=False))
                        try: nacitaj_stat()
                        except Exception: pass
                        st.session_state.msg_stat = f"Štatistika upravená ({len(zmeny)} zmien)."
                    st.rerun()

        editor_zoznamu("Zoznam pražení", "zelena", "Dávky", -1 / KAPACITA_ZELENA_BATCH, "praz")
        editor_zoznamu("Zoznam balení", "zabalene", "Kusy", 1, "bal")
        editor_zoznamu("Zoznam expedícií", "expedovane", "Kusy", -1, "exp")

        st.markdown(f"#### 📦 Zabalené po výrobkoch ({obd})")
        if zab.empty:
            st.caption("V tomto období sa nebalilo.")
        else:
            df_zab = zab.groupby(["nazov", "gramaz"])["zmena"].sum().reset_index()
            piv = df_zab.pivot(index="nazov", columns="gramaz", values="zmena").fillna(0).astype(int)
            for g_ in gramaze_list:
                if g_ not in piv.columns: piv[g_] = 0
            piv = piv[gramaze_list]; piv.columns = [f"{g_} g" for g_ in gramaze_list]
            piv["Spolu (ks)"] = piv.sum(axis=1)
            piv.index = [str(i).rsplit(" ", 1)[0] for i in piv.index]; piv = piv.groupby(level=0).sum()
            piv.index.name = "Káva"
            st.dataframe(piv.sort_values("Spolu (ks)", ascending=False), use_container_width=True)

        st.markdown("#### 📈 Praženie po dňoch")
        dni = d[d["druh"] == "zelena"].groupby("den")["zmena"].sum().mul(-1 / KAPACITA_ZELENA_BATCH)
        if not dni.empty:
            st.bar_chart(dni.rename("Dávky"), height=220)

        buf_s = io.BytesIO()
        with pd.ExcelWriter(buf_s, engine="xlsxwriter") as writer:
            _zapis_harok(writer, sm.reset_index(), "Súhrn po mesiacoch")
            if not pz.empty: _zapis_harok(writer, df_pz.reset_index(), "Praženie po zrnách")
            if not zab.empty: _zapis_harok(writer, piv.reset_index(), "Zabalené")
            _zapis_harok(writer, d[["Čas", "Akcia", "Detail", "SKU", "nazov", "zmena"]].rename(columns={"nazov": "Názov", "zmena": "Zmena"}), "Pohyby")
        st.download_button("💾 Stiahnuť štatistiky (.xlsx)", data=buf_s.getvalue(), file_name=f"Kikiriki_Statistiky_{DNESNY_DATUM}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
