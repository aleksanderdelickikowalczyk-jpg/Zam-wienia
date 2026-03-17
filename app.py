import streamlit as st
import re
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import base64
import uuid
import json
from PIL import Image
import io

st.set_page_config(page_title="Ewidencja Sprzedaży", page_icon="🛒", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');
html, body, [class*="css"] { font-family: 'Nunito', sans-serif !important; }
.main .block-container { padding: 1rem 1rem 5rem; max-width: 640px; }
#MainMenu, footer, header { visibility: hidden; }

.top-header {
    background: linear-gradient(135deg, #1d4ed8, #3b82f6);
    color: white; border-radius: 16px; padding: 18px 20px; margin-bottom: 20px;
    display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 4px 16px rgba(29,78,216,0.3);
}
.top-header h1 { font-size: 21px; font-weight: 900; margin: 0; }
.top-header .count { background: rgba(255,255,255,0.22); padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 800; }

.card-produkt { background: white; border-radius: 16px; padding: 16px; margin-bottom: 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-left: 5px solid #3b82f6; overflow:hidden; }
.card-skladnik { background: white; border-radius: 16px; padding: 16px; margin-bottom: 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-left: 5px solid #8b5cf6; overflow:hidden; }
.card-wyposazenie { background: white; border-radius: 16px; padding: 16px; margin-bottom: 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-left: 5px solid #0891b2; overflow:hidden; }

.card-photo { width:100%; max-height:160px; object-fit:cover; border-radius:10px; margin-bottom:10px; display:block; }

.item-name { font-size: 18px; font-weight: 900; color: #0f172a; margin-bottom: 2px; }
.item-date { font-size: 12px; color: #94a3b8; font-weight: 600; margin-bottom: 10px; }

.type-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; margin-bottom: 8px; }
.badge-produkt { background: #dbeafe; color: #1d4ed8; }
.badge-skladnik { background: #ede9fe; color: #6d28d9; }
.badge-wyposazenie { background: #cffafe; color: #0e7490; }

.price-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin: 10px 0; }
.price-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 10px 0; }
.price-box { background: #f8fafc; border-radius: 10px; padding: 10px 8px; text-align: center; }
.price-box .pb-label { font-size: 10px; font-weight: 800; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 3px; }
.price-box .pb-val { font-size: 16px; font-weight: 900; }
.pb-blue { color: #2563eb; } .pb-gray { color: #475569; } .pb-green { color: #16a34a; }
.pb-orange { color: #ea580c; } .pb-purple { color: #7c3aed; }

.profit-row { display: flex; justify-content: space-between; align-items: center; background: #f0fdf4; border-radius: 10px; padding: 10px 14px; margin-top: 8px; }
.profit-label { font-size: 13px; font-weight: 800; color: #64748b; }
.profit-val { font-size: 18px; font-weight: 900; }
.profit-pos { color: #16a34a; } .profit-neg { color: #ef4444; }

.skladnik-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #ede9fe; font-size: 13px; font-weight: 700; color: #374151; }
.skladnik-row:last-child { border-bottom: none; }

.stat-box { background: white; border-radius: 14px; padding: 14px 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
.stat-num { font-size: 28px; font-weight: 900; }
.stat-label { font-size: 11px; font-weight: 700; color: #64748b; margin-top: 2px; }
.fin-box { background: white; border-radius: 14px; padding: 18px 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); margin-bottom: 10px; }
.fin-label { font-size: 13px; font-weight: 700; color: #64748b; margin-bottom: 4px; }
.fin-val { font-size: 30px; font-weight: 900; }

/* Małe czerwone przyciski ✕ w podglądzie importu — widoczne na jasnym tle */
button[data-testid="baseButton-secondary"][aria-label="Usuń"] p,
button[kind="secondary"] p { font-size: 11px !important; }
</style>
""", unsafe_allow_html=True)

# ── Google Sheets ─────────────────────────────────────────────────────────────
HEADERS  = ["id","type","product","qty","unit_price","total_cost","sale_price","total_sale","profit","created","photo","ingredients","wzorki","lp"]
NUMERIC  = {"qty","unit_price","total_cost","sale_price","total_sale","profit"}

@st.cache_resource
def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds  = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.Client(auth=creds)
    return client.open(st.secrets["spreadsheet_name"]).sheet1

def ensure_headers(sheet):
    first = sheet.row_values(1)
    if not first or first[0] != "id":
        sheet.clear()
        sheet.append_row(HEADERS)
    else:
        for i, h in enumerate(HEADERS):
            if i >= len(first) or first[i] != h:
                col_letter = chr(65 + i)
                try:
                    sheet.update(f"{col_letter}1", [[h]])
                except: pass

def load_items():
    try:
        sheet = get_sheet()
        ensure_headers(sheet)
        return list(sheet.get_all_records(numericise_ignore=["all"]))
    except Exception as e:
        st.error(f"❌ Błąd połączenia: {type(e).__name__}: {e}")
        return []

def safe_num(v):
    try:
        return round(float(str(v).strip().replace(",", ".")), 2)
    except:
        return 0.0

def row_vals(item):
    return [safe_num(item.get(h, 0)) if h in NUMERIC else item.get(h, "") for h in HEADERS]

def append_item(item):
    sheet = get_sheet()
    ensure_headers(sheet)
    if "lp" not in item or not item.get("lp"):
        records = list(sheet.get_all_records(numericise_ignore=["all"]))
        max_lp = 0
        for r in records:
            try: max_lp = max(max_lp, int(r.get("lp",0)))
            except: pass
        item["lp"] = max_lp + 1
    sheet.append_row(row_vals(item), value_input_option="USER_ENTERED")

def update_item(item):
    sheet = get_sheet()
    records = list(sheet.get_all_records(numericise_ignore=["all"]))
    for i, r in enumerate(records, start=2):
        if str(r.get("id")) == str(item["id"]):
            sheet.update(f"A{i}:{chr(64+len(HEADERS))}{i}", [row_vals(item)], value_input_option="USER_ENTERED")
            return

def delete_item(item_id):
    sheet = get_sheet()
    records = list(sheet.get_all_records(numericise_ignore=["all"]))
    for i, r in enumerate(records, start=2):
        if str(r.get("id")) == str(item_id):
            sheet.delete_rows(i)
            return

def delete_all():
    sheet = get_sheet()
    sheet.clear()
    sheet.append_row(HEADERS)

def img_to_b64(f):
    img = Image.open(f)
    img.thumbnail((300, 300))
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P": img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA","LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    for quality in [60, 45, 30]:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        b64 = base64.b64encode(buf.getvalue()).decode()
        if len(b64) < 40000:
            return b64
    return ""

def fmt(v):
    try: return f"{safe_num(v):.2f} zł"
    except: return "— zł"

def is_valid_photo(p):
    return isinstance(p, str) and len(p) > 100

def calc_ing_cost(ing_list, smap):
    total = 0.0
    for ing in ing_list:
        name = ing.get("name","")
        qpp  = safe_num(ing.get("qty_per_product", 1))
        if name in smap:
            total += safe_num(smap[name].get("unit_price", 0)) * qpp
    return round(total, 2)

def parse_price(s):
    try:
        s = str(s).strip().replace(",",".")
        return round(float(s), 2)
    except:
        return 0.0

# ── Sortowanie alfabetyczne ───────────────────────────────────────────────────
def sort_alpha(lst):
    return sorted(lst, key=lambda x: str(x.get("product","")).lower())

# ── PDF generowanie ───────────────────────────────────────────────────────────
def generate_pdf_html(items_list, sort_label="🔤 Nazwa A → Z"):
    # Lista przekazana już w wybranej kolejności sortowania

    rows = ""
    for x in items_list:
        xtype = "Produkt" if x.get("type") == "produkt" else "Składnik"
        photo = x.get("photo", "")
        if is_valid_photo(photo):
            img_tag = f'<img src="data:image/jpeg;base64,{photo.strip()}" style="width:60px;height:60px;object-fit:cover;border-radius:6px;display:block">'
        else:
            img_tag = '<div style="width:60px;height:60px;background:#f1f5f9;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:20px">📦</div>'

        rows += (
            "<tr>"
            f"<td style='width:70px;padding:6px 4px'>{img_tag}</td>"
            f"<td style='font-weight:700;font-size:11px'>{x.get('product','—')}</td>"
            f"<td><span style='background:{'#dbeafe' if x.get('type')=='produkt' else '#ede9fe'};color:{'#1d4ed8' if x.get('type')=='produkt' else '#6d28d9'};padding:2px 7px;border-radius:10px;font-size:10px;font-weight:800'>{'Produkt' if x.get('type')=='produkt' else 'Składnik'}</span></td>"
            f"<td style='text-align:center'>{x.get('qty','—')}</td>"
            f"<td>{fmt(x.get('unit_price'))}</td>"
            f"<td>{fmt(x.get('total_cost'))}</td>"
            f"<td>{fmt(x.get('sale_price')) if x.get('type')=='produkt' else '—'}</td>"
            f"<td style='color:{'#16a34a' if safe_num(x.get('profit',0))>=0 else '#ef4444'};font-weight:800'>{fmt(x.get('profit')) if x.get('type')=='produkt' else '—'}</td>"
            f"<td style='color:#94a3b8;font-size:10px'>{x.get('created','')}</td>"
            "</tr>"
        )

    total_sprzedaz  = sum(safe_num(x.get("total_sale",0)) for x in items_list if x.get("type")=="produkt")
    total_koszt     = sum(safe_num(x.get("total_cost",0)) for x in items_list if x.get("type")=="produkt")
    total_zysk      = sum(safe_num(x.get("profit",0)) for x in items_list if x.get("type")=="produkt")
    total_koszt_skl = sum(safe_num(x.get("total_cost",0)) for x in items_list if x.get("type")=="skladnik")
    n_skl           = sum(1 for x in items_list if x.get("type")=="skladnik")
    total_koszt_wyp = sum(safe_num(x.get("total_cost",0)) for x in items_list if x.get("type")=="wyposazenie")
    n_wyp           = sum(1 for x in items_list if x.get("type")=="wyposazenie")

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; font-size: 11px; margin: 20px; color: #0f172a; }}
        h2 {{ color: #1d4ed8; margin-bottom: 4px; font-size: 20px; }}
        .subtitle {{ color: #64748b; font-size: 10px; margin-bottom: 16px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #1d4ed8; color: white; padding: 8px 6px; text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.4px; }}
        td {{ padding: 6px 6px; border-bottom: 1px solid #e2e8f0; vertical-align: middle; }}
        tr:hover {{ background: #f8fafc; }}
        .summary {{ margin-top: 16px; background: #f0fdf4; padding: 14px 18px; border-radius: 8px; border: 1px solid #bbf7d0; }}
        .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 8px; }}
        .sum-item {{ text-align: center; }}
        .sum-label {{ font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; }}
        .sum-val {{ font-size: 18px; font-weight: 900; }}
        @media print {{
            button {{ display: none !important; }}
            body {{ margin: 10px; }}
            tr {{ page-break-inside: avoid; }}
        }}
    </style>
    </head><body>
    <h2>🛒 Ewidencja Sprzedaży</h2>
    <div class="subtitle">Wygenerowano: {date.today().strftime('%d.%m.%Y')} &nbsp;·&nbsp; Łącznie wpisów: {len(items_list)} &nbsp;·&nbsp; Sortowanie: {sort_label}</div>
    <table>
        <thead><tr>
            <th>Zdjęcie</th><th>Nazwa</th><th>Typ</th><th>Ilość</th>
            <th>Cena jedn.</th><th>Koszt całość</th>
            <th>Cena sprzed./szt.</th><th>Zysk</th><th>Data</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <div class="summary">
        <b style="color:#0e7490">🔧 Wyposażenie:</b><br>
        Łączny koszt: <b style="color:#0891b2">{total_koszt_wyp:.2f} zł</b> &nbsp;·&nbsp; Pozycji: <b>{n_wyp}</b>
        <br><br>
        <b style="color:#7c3aed">🧩 Zakupione materiały (składniki):</b><br>
        Łączny koszt zakupów: <b style="color:#7c3aed">{total_koszt_skl:.2f} zł</b> &nbsp;·&nbsp; Pozycji: <b>{n_skl}</b>
        <br><br>
        <b style="color:#1d4ed8">🏷️ Produkty gotowe:</b><br>
        Łączna sprzedaż: <b style="color:#1d4ed8">{total_sprzedaz:.2f} zł</b> &nbsp;|&nbsp;
        Łączny koszt: <b style="color:#ea580c">{total_koszt:.2f} zł</b> &nbsp;|&nbsp;
        Łączny zysk: <b style="color:{'#16a34a' if total_zysk>=0 else '#ef4444'}">{total_zysk:.2f} zł</b>
    </div>
    <br><button onclick="window.print()">🖨️ Drukuj</button>
    </body></html>"""
    return html

# ── Stan ──────────────────────────────────────────────────────────────────────
for k, v in [("tab","lista"),("editing",None),("wpisy",None)]:
    if k not in st.session_state: st.session_state[k] = v

if st.session_state.wpisy is None:
    loaded = load_items()
    st.session_state.wpisy = loaded if isinstance(loaded, list) else []

items = st.session_state.wpisy if isinstance(st.session_state.wpisy, list) else []

_needs_save = [x for x in items if not str(x.get("lp","")).strip().isdigit() or int(str(x.get("lp","")).strip()) <= 0]

if _needs_save:
    try:
        _sheet = get_sheet()
        _all_rows = _sheet.get_all_values()
        _id_col = 0
        _lp_col_idx = HEADERS.index("lp")
        if _all_rows:
            header_row = _all_rows[0]
            try: _lp_col_sheet = header_row.index("lp")
            except ValueError: _lp_col_sheet = _lp_col_idx

        _used_lp = set()
        for row in _all_rows[1:]:
            if len(row) > _lp_col_sheet:
                v = str(row[_lp_col_sheet]).strip()
                if v.isdigit() and int(v) > 0:
                    _used_lp.add(int(v))

        _next_lp = 1
        _batch = []
        for x in _needs_save:
            while _next_lp in _used_lp:
                _next_lp += 1
            x["lp"] = _next_lp
            _used_lp.add(_next_lp)
            xid = str(x.get("id",""))
            for ri, row in enumerate(_all_rows[1:], start=2):
                if row and str(row[0]).strip() == xid:
                    col_letter = chr(65 + _lp_col_sheet)
                    _batch.append({"range": f"{col_letter}{ri}", "values": [[_next_lp - 1]]})
                    break
            _next_lp += 1

        if _batch:
            _sheet.batch_update(_batch, value_input_option="USER_ENTERED")
    except Exception as _e:
        pass

produkty      = [x for x in items if x.get("type","") == "produkt"]
skladniki     = [x for x in items if x.get("type","") == "skladnik"]
wyposazenie   = [x for x in items if x.get("type","") == "wyposazenie"]
skladniki_map = {s.get("product",""): s for s in skladniki}

# ── Nagłówek ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-header">
    <h1>🛒 Ewidencja Sprzedaży</h1>
    <span class="count">🏷️ {len(produkty)} · 🧩 {len(skladniki)} · 🔧 {len(wyposazenie)}</span>
</div>
""", unsafe_allow_html=True)

r1c1, r1c2 = st.columns(2)
with r1c1:
    if st.button("📋 Lista", use_container_width=True, type="primary" if st.session_state.tab=="lista" else "secondary"):
        st.session_state.tab="lista"; st.session_state.editing=None; st.rerun()
with r1c2:
    if st.button("➕ Dodaj", use_container_width=True, type="primary" if st.session_state.tab=="dodaj" else "secondary"):
        st.session_state.tab="dodaj"; st.session_state.editing=None; st.rerun()
r2c1, r2c2 = st.columns(2)
with r2c1:
    if st.button("📊 Podsumowanie", use_container_width=True, type="primary" if st.session_state.tab=="stats" else "secondary"):
        st.session_state.tab="stats"; st.session_state.editing=None; st.rerun()
with r2c2:
    if st.button("📥 Import", use_container_width=True, type="primary" if st.session_state.tab=="import" else "secondary"):
        st.session_state.tab="import"; st.session_state.editing=None; st.rerun()

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# LISTA
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.tab == "lista":

    col_s, col_f, col_r = st.columns([3, 2, 1])
    with col_s:
        search = st.text_input("Szukaj", placeholder="🔍 Szukaj...", label_visibility="collapsed")
    with col_f:
        filtr_typ = st.selectbox("Typ", ["Wszystkie", "🏷️ Produkty gotowe", "🧩 Składniki", "🔧 Wyposażenie"], label_visibility="collapsed")
    with col_r:
        if st.button("🔄", use_container_width=True, help="Odśwież"):
            st.session_state.wpisy = load_items(); st.rerun()

    # ── Sortowanie ────────────────────────────────────────────────────────────
    SORT_OPTIONS = {
        "🔤 Nazwa A → Z":          ("product",    False, "str"),
        "🔤 Nazwa Z → A":          ("product",    True,  "str"),
        "🔢 Nr. porządkowy ↑":     ("lp",         False, "num"),
        "🔢 Nr. porządkowy ↓":     ("lp",         True,  "num"),
        "💰 Koszt rosnąco":        ("total_cost",  False, "num"),
        "💰 Koszt malejąco":       ("total_cost",  True,  "num"),
        "🏷️ Cena sprzedaży ↑":    ("total_sale",  False, "num"),
        "🏷️ Cena sprzedaży ↓":    ("total_sale",  True,  "num"),
    }
    sort_choice = st.selectbox(
        "Sortuj według",
        list(SORT_OPTIONS.keys()),
        label_visibility="collapsed",
        key="sort_choice"
    )
    sort_key, sort_rev, sort_type = SORT_OPTIONS[sort_choice]

    filtered = list(items)
    if search:
        filtered = [x for x in filtered if search.lower() in str(x.get("product","")).lower() or search.strip("#") == str(x.get("lp",""))]
    if filtr_typ == "🏷️ Produkty gotowe":
        filtered = [x for x in filtered if x.get("type") == "produkt"]
    elif filtr_typ == "🧩 Składniki":
        filtered = [x for x in filtered if x.get("type") == "skladnik"]
    elif filtr_typ == "🔧 Wyposażenie":
        filtered = [x for x in filtered if x.get("type") == "wyposazenie"]

    # Zastosuj wybrane sortowanie
    if sort_type == "str":
        filtered = sorted(filtered, key=lambda x: str(x.get(sort_key,"")).lower(), reverse=sort_rev)
    else:
        filtered = sorted(filtered, key=lambda x: safe_num(x.get(sort_key, 0)), reverse=sort_rev)

    # PDF / Drukuj
    if filtered:
        if st.button("🖨️ Drukuj / Pobierz PDF", use_container_width=True):
            pdf_html = generate_pdf_html(filtered, sort_label=sort_choice)
            b64_html = base64.b64encode(pdf_html.encode("utf-8")).decode()
            st.markdown(
                f'<a href="data:text/html;base64,{b64_html}" download="ewidencja.html" '
                f'style="display:block;text-align:center;background:#1d4ed8;color:white;'
                f'padding:10px;border-radius:10px;font-weight:800;text-decoration:none;margin-bottom:12px">'
                f'⬇️ Pobierz plik (otwórz i drukuj)</a>',
                unsafe_allow_html=True
            )

    if not filtered:
        st.markdown("""
        <div style="text-align:center;padding:48px 20px;color:#94a3b8">
            <div style="font-size:52px;margin-bottom:12px">📭</div>
            <p style="font-size:16px;font-weight:700">Brak wpisów</p>
            <small>Dodaj pierwszy wpis klikając ➕</small>
        </div>""", unsafe_allow_html=True)
    else:
        # Znacznik aktywnego sortowania
        st.markdown(
            f'<div style="text-align:right;font-size:11px;color:#94a3b8;font-weight:700;margin-bottom:6px">{sort_choice}</div>',
            unsafe_allow_html=True
        )

        for idx_card, x in enumerate(filtered, start=1):
            xid   = str(x.get("id",""))
            xtype = x.get("type","produkt")
            photo = x.get("photo","")

            photo_html = ""
            if is_valid_photo(photo):
                photo_html = '<img src="data:image/jpeg;base64,' + photo.strip() + '" class="card-photo">'

            if xtype == "produkt":
                profit     = x.get("profit", 0)
                profit_cls = "profit-pos" if safe_num(profit) >= 0 else "profit-neg"

                ing_list = []
                try:
                    raw = x.get("ingredients","")
                    if raw: ing_list = json.loads(raw)
                except: pass

                st.markdown(
                    '<div class="card-produkt">'
                    + photo_html +
                    '<span class="type-badge badge-produkt">🏷️ Produkt gotowy</span>'
                    f'<div class="item-name"><span style="color:#94a3b8;font-size:13px;font-weight:700;margin-right:6px">#{x.get("lp","—")}</span>{x.get("product","—")}</div>'
                    f'<div class="item-date">📅 {x.get("created","")}</div>'
                    '<div class="price-grid">'
                    f'<div class="price-box"><div class="pb-label">Ilość</div><div class="pb-val pb-gray">{x.get("qty","—")} szt.</div></div>'
                    f'<div class="price-box"><div class="pb-label">Cena jedn.</div><div class="pb-val pb-blue">{fmt(x.get("unit_price"))}</div></div>'
                    f'<div class="price-box"><div class="pb-label">Koszt całość</div><div class="pb-val pb-orange">{fmt(x.get("total_cost"))}</div></div>'
                    '</div>'
                    '<div class="price-grid">'
                    f'<div class="price-box" style="grid-column:span 2"><div class="pb-label">Cena sprzedaży (łącznie)</div><div class="pb-val pb-green">{fmt(x.get("total_sale"))}</div></div>'
                    f'<div class="price-box"><div class="pb-label">Cena sprzed./szt.</div><div class="pb-val pb-green">{fmt(x.get("sale_price"))}</div></div>'
                    '</div>'
                    f'<div class="profit-row"><span class="profit-label">💰 Zysk</span><span class="profit-val {profit_cls}">{fmt(profit)}</span></div>'
                    '</div>',
                    unsafe_allow_html=True
                )

                wzorki_display = []
                try:
                    wraw = x.get("wzorki","")
                    if wraw: wzorki_display = json.loads(wraw)
                except: pass
                if wzorki_display:
                    with st.expander(f"🎨 Wzorki kompletu ({len(wzorki_display)} szt.)", expanded=False):
                        whtml = ""
                        for wz in wzorki_display:
                            whtml += (
                                f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                                f'border-bottom:1px solid #dcfce7;font-size:13px;font-weight:700">'
                                f'<span style="color:#0f172a">🎨 {wz.get("name","—")}</span>'
                                f'<span style="color:#16a34a">{wz.get("price",0):.2f} zł</span></div>'
                            )
                        total_w = sum(wz.get("price",0) for wz in wzorki_display)
                        whtml += f'<div style="display:flex;justify-content:space-between;margin-top:8px;font-weight:900"><span style="color:#166534">💚 Suma</span><span style="color:#16a34a">{total_w:.2f} zł</span></div>'
                        st.markdown(f'<div style="background:#f0fdf4;border-radius:10px;padding:10px 14px">{whtml}</div>', unsafe_allow_html=True)

                if ing_list:
                    with st.expander(f"🧩 Składniki ({len(ing_list)} pozycji)", expanded=False):
                        rows_html = ""
                        for ing in ing_list:
                            s_data   = skladniki_map.get(ing.get("name",""), {})
                            up       = safe_num(s_data.get("unit_price", 0))
                            qpp      = safe_num(ing.get("qty_per_product", 1))
                            ing_cost = round(up * qpp, 2)
                            rows_html += (
                                f'<div class="skladnik-row">'
                                f'<span>🧩 {ing.get("name","—")}</span>'
                                f'<span style="display:flex;gap:14px;align-items:center">'
                                f'<span style="color:#64748b;font-size:12px;font-weight:700">{qpp:.1f} szt./produkt</span>'
                                f'<span style="color:#7c3aed;font-weight:800">{ing_cost:.2f} zł</span>'
                                f'</span></div>'
                            )
                        ing_total = calc_ing_cost(ing_list, skladniki_map)
                        rows_html += (
                            f'<div style="display:flex;justify-content:space-between;align-items:center;'
                            f'margin-top:10px;padding-top:10px;border-top:2px solid #c4b5fd">'
                            f'<span style="font-size:12px;font-weight:800;color:#6d28d9">💜 Suma / szt.</span>'
                            f'<span style="font-size:16px;font-weight:900;color:#7c3aed">{ing_total:.2f} zł</span></div>'
                        )
                        st.markdown('<div style="background:#faf5ff;border-radius:10px;padding:12px 14px">' + rows_html + '</div>', unsafe_allow_html=True)

            elif xtype == "skladnik":
                st.markdown(
                    '<div class="card-skladnik">'
                    + photo_html +
                    '<span class="type-badge badge-skladnik">🧩 Składnik</span>'
                    f'<div class="item-name"><span style="color:#94a3b8;font-size:13px;font-weight:700;margin-right:6px">#{x.get("lp","—")}</span>{x.get("product","—")}</div>'
                    f'<div class="item-date">📅 {x.get("created","")}</div>'
                    '<div class="price-grid-2">'
                    f'<div class="price-box"><div class="pb-label">Ilość</div><div class="pb-val pb-gray">{x.get("qty","—")} szt.</div></div>'
                    f'<div class="price-box"><div class="pb-label">Cena jedn.</div><div class="pb-val pb-purple">{fmt(x.get("unit_price"))}</div></div>'
                    '</div>'
                    '<div class="price-grid-2" style="margin-top:0">'
                    f'<div class="price-box"><div class="pb-label">Koszt całość</div><div class="pb-val pb-orange">{fmt(x.get("total_cost"))}</div></div>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True
                )

            elif xtype == "wyposazenie":
                st.markdown(
                    '<div class="card-wyposazenie">'
                    + photo_html +
                    '<span class="type-badge badge-wyposazenie">🔧 Wyposażenie</span>'
                    f'<div class="item-name" style="color:#0f172a"><span style="color:#94a3b8;font-size:13px;font-weight:700;margin-right:6px">#{x.get("lp","—")}</span>{x.get("product","—")}</div>'
                    f'<div class="item-date">📅 {x.get("created","")}</div>'
                    '<div class="price-grid-2">'
                    f'<div class="price-box"><div class="pb-label">Ilość</div><div class="pb-val pb-gray">{x.get("qty","—")} szt.</div></div>'
                    f'<div class="price-box"><div class="pb-label">Koszt całość</div><div class="pb-val pb-orange">{fmt(x.get("total_cost"))}</div></div>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True
                )

            ca, cb = st.columns(2)
            with ca:
                if st.button("✏️ Edytuj", key=f"e_{xid}", use_container_width=True):
                    st.session_state.editing = x
                    st.session_state.tab = "dodaj"
                    st.rerun()
            with cb:
                if st.button("🗑️ Usuń", key=f"d_{xid}", use_container_width=True):
                    with st.spinner("Usuwanie..."):
                        delete_item(xid)
                        st.session_state.wpisy = load_items()
                    st.rerun()
            st.markdown("<hr style='margin:8px 0 16px;border-color:#f1f5f9'>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# DODAJ / EDYTUJ
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.tab == "dodaj":
    ed      = st.session_state.editing
    is_edit = ed is not None

    st.markdown(f"### {'✏️ Edytuj wpis' if is_edit else '➕ Nowy wpis'}")

    type_options  = ["🏷️ Produkt gotowy", "🧩 Składnik", "🔧 Wyposażenie"]
    if is_edit and ed.get("type") == "skladnik": default_type = 1
    elif is_edit and ed.get("type") == "wyposazenie": default_type = 2
    else: default_type = 0
    selected_type  = st.selectbox("Typ wpisu *", type_options, index=default_type)
    is_skladnik    = selected_type == "🧩 Składnik"
    is_wyposazenie = selected_type == "🔧 Wyposażenie"
    xtype          = "skladnik" if is_skladnik else ("wyposazenie" if is_wyposazenie else "produkt")

    product = st.text_input("Nazwa *",
        value=ed.get("product","") if is_edit else "",
        placeholder="np. Koszulka bawełniana" if not is_skladnik else "np. Bawełna 100g")

    def parse_price(s):
        try: return round(float(str(s).strip().replace(",",".")), 2)
        except: return 0.0

    col1, col2 = st.columns(2)
    with col1:
        qty = st.number_input("Ilość sztuk *", min_value=1, step=1,
            value=int(safe_num(ed.get("qty",1))) if is_edit else 1)
    with col2:
        up_default = str(ed.get("unit_price","0")).replace(".",",") if is_edit else "0"
        unit_price_str = st.text_input("Cena jednostkowa (zł) *", value=up_default, placeholder="np. 6,92")
        unit_price = parse_price(unit_price_str)

    # ── Składniki (tylko produkt) ─────────────────────────────────────────────
    ingredients_json = "[]"
    ingredients_cost = 0.0

    if not is_skladnik and not is_wyposazenie:
        st.markdown("---")
        st.markdown("**🧩 Składniki produktu**")

        edit_key = ed.get("id") if is_edit else "new"
        if "ing_list" not in st.session_state or st.session_state.get("ing_editing_id") != edit_key:
            if is_edit and ed.get("ingredients"):
                try:    st.session_state.ing_list = json.loads(ed["ingredients"])
                except: st.session_state.ing_list = []
            else:
                st.session_state.ing_list = []
            st.session_state.ing_editing_id = edit_key

        skladniki_names = [s.get("product","") for s in skladniki]
        if skladniki_names:
            ci1, ci2, ci3 = st.columns([3, 1, 1])
            with ci1:
                ing_name = st.selectbox("Składnik", ["— wybierz —"] + skladniki_names)
            with ci2:
                ing_qpp = st.number_input("Ilość/szt.", min_value=0.1, step=0.1, value=1.0, format="%.1f")
            with ci3:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button("➕ Dodaj", use_container_width=True) and ing_name != "— wybierz —":
                    existing = next((i for i, x in enumerate(st.session_state.ing_list) if x["name"] == ing_name), None)
                    if existing is not None:
                        st.session_state.ing_list[existing]["qty_per_product"] = ing_qpp
                    else:
                        st.session_state.ing_list.append({"name": ing_name, "qty_per_product": ing_qpp})
                    st.rerun()
        else:
            st.info("ℹ️ Najpierw dodaj składniki (typ: 🧩 Składnik), żeby móc je tu przypisać.")

        if st.session_state.get("ing_list"):
            ingredients_cost = calc_ing_cost(st.session_state.ing_list, skladniki_map)
            for idx, ing in enumerate(st.session_state.ing_list):
                s_data   = skladniki_map.get(ing.get("name",""), {})
                up       = safe_num(s_data.get("unit_price", 0))
                qpp      = safe_num(ing.get("qty_per_product", 1))
                ing_cost = round(up * qpp, 2)
                ic1, ic2, ic3 = st.columns([4, 2, 1])
                with ic1: st.markdown(f"🧩 **{ing['name']}**")
                with ic2: st.markdown(f"<div style='padding-top:6px;font-size:13px;font-weight:700;color:#7c3aed'>{qpp:.1f} szt. → {ing_cost:.2f} zł</div>", unsafe_allow_html=True)
                with ic3:
                    if st.button("✕", key=f"rmi_{idx}", use_container_width=True):
                        st.session_state.ing_list.pop(idx)
                        st.rerun()

            st.markdown(
                f'<div style="background:#ede9fe;border-radius:10px;padding:10px 16px;margin:8px 0;'
                f'display:flex;justify-content:space-between;align-items:center">'
                f'<span style="font-size:13px;font-weight:800;color:#6d28d9">💜 Koszt składników / 1 szt.</span>'
                f'<span style="font-size:18px;font-weight:900;color:#7c3aed">{ingredients_cost:.2f} zł</span></div>',
                unsafe_allow_html=True
            )

        ingredients_json = json.dumps(st.session_state.get("ing_list", []), ensure_ascii=False)

    # ── Koszt całości ─────────────────────────────────────────────────────────
    st.markdown("---")
    has_ing = not is_skladnik and not is_wyposazenie and bool(st.session_state.get("ing_list"))
    if has_ing:
        total_cost = round(ingredients_cost * qty, 2)
        label = "📦 Koszt całości (ze składników × ilość)"
    else:
        total_cost = round(qty * unit_price, 2)
        label = "📦 Koszt całości (auto)"

    st.markdown(
        f'<div style="background:#fef3c7;border-radius:12px;padding:12px 16px;margin-bottom:12px;'
        f'display:flex;justify-content:space-between;align-items:center">'
        f'<span style="font-size:14px;font-weight:800;color:#92400e">{label}</span>'
        f'<span style="font-size:20px;font-weight:900;color:#b45309">{total_cost:.2f} zł</span></div>',
        unsafe_allow_html=True
    )

    sale_price = 0.0
    total_sale = 0.0
    profit     = 0.0
    if not is_skladnik and not is_wyposazenie:
        st.markdown("---")
        komplet_key = f"komplet_{ed.get('id','new') if is_edit else 'new'}"
        if komplet_key not in st.session_state:
            saved_wzorki = []
            if is_edit:
                try: saved_wzorki = json.loads(ed.get("wzorki","[]") or "[]")
                except: pass
            st.session_state[komplet_key] = bool(saved_wzorki)
        
        is_komplet = st.checkbox("🎨 To jest komplet z różnymi wzorkami/wariantami", value=st.session_state[komplet_key], key=f"cb_{komplet_key}")
        st.session_state[komplet_key] = is_komplet

        wzorki_key = f"wzorki_{ed.get('id','new') if is_edit else 'new'}"
        if wzorki_key not in st.session_state:
            if is_edit:
                try: st.session_state[wzorki_key] = json.loads(ed.get("wzorki","[]") or "[]")
                except: st.session_state[wzorki_key] = []
            else:
                st.session_state[wzorki_key] = []

        if is_komplet:
            st.markdown("**🎨 Wzorki / warianty**")
            st.caption("Dodaj poszczególne wzorki i ich ceny sprzedaży — suma będzie ceną całego kompletu")
            
            wc1, wc2, wc3 = st.columns([3, 2, 1])
            with wc1:
                wzor_name = st.text_input("Nazwa wzorku", placeholder="np. Wzór morski", key="wzor_name_inp")
            with wc2:
                wzor_price_str = st.text_input("Cena (zł)", placeholder="np. 15,99", key="wzor_price_inp")
            with wc3:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button("➕", use_container_width=True, key="add_wzor"):
                    if wzor_name.strip():
                        st.session_state[wzorki_key].append({
                            "name": wzor_name.strip(),
                            "price": parse_price(wzor_price_str)
                        })
                        st.rerun()

            wzorki_list = st.session_state.get(wzorki_key, [])
            if wzorki_list:
                wzorki_html = ""
                for wi, wz in enumerate(wzorki_list):
                    wzorki_html += (
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'padding:7px 12px;background:#f0fdf4;border-radius:8px;margin-bottom:5px">'
                        f'<span style="font-weight:700;font-size:13px;color:#166534">🎨 {wz["name"]}</span>'
                        f'<span style="font-weight:900;color:#16a34a">{wz["price"]:.2f} zł</span>'
                        f'</div>'
                    )
                st.markdown(wzorki_html, unsafe_allow_html=True)
                
                wdel = st.selectbox("Usuń wzorek:", ["— wybierz —"] + [w["name"] for w in wzorki_list], key="wzor_del")
                if wdel != "— wybierz —":
                    if st.button("🗑️ Usuń ten wzorek", key="del_wzor_btn"):
                        st.session_state[wzorki_key] = [w for w in wzorki_list if w["name"] != wdel]
                        st.rerun()

                total_wzorki = sum(w["price"] for w in wzorki_list)
                sale_price = round(total_wzorki / qty, 2) if qty > 0 else 0.0
                total_sale = round(total_wzorki * qty, 2)
                st.markdown(
                    f'<div style="background:#dcfce7;border-radius:10px;padding:10px 16px;margin:8px 0;'
                    f'display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="font-size:13px;font-weight:800;color:#166534">💚 Suma wzorków / komplet</span>'
                    f'<span style="font-size:18px;font-weight:900;color:#16a34a">{total_wzorki:.2f} zł</span></div>',
                    unsafe_allow_html=True
                )
            else:
                total_wzorki = 0.0
                sale_price = 0.0
                total_sale = 0.0
        else:
            st.session_state[wzorki_key] = []
            wzorki_list = []
            sp_default = str(ed.get("sale_price","0")).replace(".",",") if is_edit else "0"
            sale_price_str = st.text_input("Cena sprzedaży za sztukę (zł) *", value=sp_default, placeholder="np. 19,99")
            sale_price = parse_price(sale_price_str)
            total_sale = round(qty * sale_price, 2)
            wzorki_list = []

        profit = round(total_sale - total_cost, 2)
        pcol = "#16a34a" if profit >= 0 else "#ef4444"
        picon = "📈" if profit >= 0 else "📉"
        st.markdown(
            f'<div style="background:#f0fdf4;border-radius:12px;padding:14px 16px;margin-bottom:16px">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:6px">'
            f'<span style="font-size:13px;font-weight:700;color:#64748b">💵 Łączna cena sprzedaży</span>'
            f'<span style="font-size:17px;font-weight:900;color:#16a34a">{total_sale:.2f} zł</span></div>'
            f'<div style="display:flex;justify-content:space-between">'
            f'<span style="font-size:13px;font-weight:700;color:#64748b">{picon} Zysk</span>'
            f'<span style="font-size:17px;font-weight:900;color:{pcol}">{profit:.2f} zł</span></div></div>',
            unsafe_allow_html=True
        )
    elif is_wyposazenie:
        wzorki_list = []
    else:
        wzorki_list = []

    st.markdown("**📷 Zdjęcie**")
    uploaded = st.file_uploader("Zdjęcie", type=["jpg","jpeg","png","webp"], label_visibility="collapsed")
    existing_photo = ""
    if is_edit and is_valid_photo(ed.get("photo","")):
        existing_photo = ed["photo"]
        try: st.image(base64.b64decode(existing_photo), width=200, caption="Aktualne zdjęcie")
        except: pass
        if st.checkbox("🗑️ Usuń zdjęcie"):
            existing_photo = ""

    st.markdown("")
    cs, cc = st.columns([2, 1])
    with cs:
        save_clicked = st.button("💾 Zapisz zmiany" if is_edit else "💾 Dodaj wpis", use_container_width=True, type="primary")
    with cc:
        if is_edit and st.button("Anuluj", use_container_width=True):
            st.session_state.editing = None
            st.session_state.tab = "lista"
            if "ing_list" in st.session_state: del st.session_state["ing_list"]
            edit_id = ed.get("id","new") if is_edit else "new"
            for k in [f"wzorki_{edit_id}", f"komplet_{edit_id}"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()

    if save_clicked:
        if not product.strip():
            st.error("⚠️ Podaj nazwę!")
        else:
            photo_b64 = img_to_b64(uploaded) if uploaded else existing_photo
            wzorki_key_save = f"wzorki_{ed.get('id','new') if is_edit else 'new'}"
            wzorki_json = json.dumps(st.session_state.get(wzorki_key_save, []), ensure_ascii=False)
            item = {
                "id":          ed.get("id") if is_edit else str(uuid.uuid4())[:8],
                "type":        xtype,
                "product":     product.strip(),
                "qty":         qty,
                "unit_price":  unit_price,
                "total_cost":  total_cost,
                "sale_price":  sale_price,
                "total_sale":  total_sale,
                "profit":      profit,
                "created":     ed.get("created") if is_edit else date.today().strftime("%d.%m.%Y"),
                "photo":       photo_b64,
                "ingredients": ingredients_json if not is_skladnik else "[]",
                "wzorki":      wzorki_json if not is_skladnik else "[]",
            }
            with st.spinner("Zapisywanie..."):
                if is_edit: update_item(item)
                else:       append_item(item)
                st.session_state.wpisy = load_items()
            st.success("✅ Zapisano!")
            st.session_state.editing = None
            st.session_state.tab = "lista"
            if "ing_list" in st.session_state: del st.session_state["ing_list"]
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# IMPORT — zakładki: Temu i Vinted
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.tab == "import":
    st.markdown("### 📥 Import zamówień")

    import_source = st.radio(
        "Źródło importu:",
        ["🛒 Temu", "👗 Vinted"],
        horizontal=True,
        label_visibility="collapsed"
    )

    # ── TEMU ─────────────────────────────────────────────────────────────────
    if import_source == "🛒 Temu":
        st.markdown("#### 🛒 Import z Temu")
        st.markdown("""
        **Jak pobrać plik?**
        1. Wejdź na Temu → Historia zamówień → otwórz zamówienie
        2. Kliknij **"Udostępnij"** → skopiuj link i otwórz w przeglądarce
        3. Kliknij prawym → **Zapisz jako... → Strona internetowa, kompletna**
        4. Wgraj plik HTML poniżej (folder `_files` nie jest potrzebny)
        """)

        uploaded_html = st.file_uploader("Wgraj plik HTML z Temu", type=["html","htm"], label_visibility="visible")

        import_type = st.selectbox("Importuj jako:", ["🧩 Składniki (materiały zakupione)", "🏷️ Produkty gotowe"])
        xtype_import = "skladnik" if "Składniki" in import_type else "produkt"

        if uploaded_html:
            try:
                html_content = uploaded_html.read().decode("utf-8", errors="ignore")

                match = re.search(r'window\.rawData=(\{)', html_content)
                if not match:
                    st.error("❌ Nie znaleziono danych produktów w tym pliku.")
                    st.info("💡 Upewnij się że to plik z Temu — Szczegóły zamówienia lub Udostępnij zamówienie")
                else:
                    start = match.start(1)
                    try:
                        data, _ = json.JSONDecoder().raw_decode(html_content, start)
                        raw_str = True
                    except Exception as je:
                        try:
                            err_pos = int(str(je).split("char ")[1].rstrip(")")) if "char " in str(je) else 0
                            data = json.loads(html_content[start:start+err_pos])
                            raw_str = True
                        except:
                            raw_str = None

                    if not raw_str:
                        st.error("❌ Nie udało się sparsować danych.")
                    else:
                        store = data.get("store", {})
                        products_raw = store.get("orderInfoList", [])
                        fmt_temu = "details"

                        if not products_raw:
                            products_raw = store.get("shareOrderDetail",{}).get("shareOrderInfo",{}).get("orderGoodsList",[])
                            fmt_temu = "share"

                        if not products_raw:
                            st.error("❌ Brak produktów w pliku.")
                        else:
                            # Inicjuj listę pozycji do importu w session_state
                            temu_key = f"temu_preview_{hash(uploaded_html.name)}"
                            if temu_key not in st.session_state:
                                preview_list = []
                                for p in products_raw:
                                    if fmt_temu == "details":
                                        price_str = p.get("goodsPriceWithSymbolDisplay", p.get("goodsPriceDisplay","0"))
                                        qty_p = int(p.get("goodsNumber", 1))
                                    else:
                                        price_str = p.get("goodsPriceDisplay","0")
                                        qty_p = 1
                                    price = parse_price(price_str.replace(" zł","").replace(",","."))
                                    preview_list.append({
                                        "name":      p.get("goodsName",""),
                                        "qty":       qty_p,
                                        "price":     price,
                                        "thumb_url": p.get("thumbUrl",""),
                                        "spec":      p.get("spec",""),
                                    })
                                st.session_state[temu_key] = preview_list

                            temu_list = st.session_state[temu_key]

                            st.success(f"✅ Znaleziono {len(products_raw)} produktów · do importu: **{len(temu_list)}**")

                            # Nagłówek tabeli
                            st.markdown(
                                '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px 10px 0 0;'
                                'padding:5px 10px 5px 10px;display:grid;grid-template-columns:1fr 100px 34px;gap:6px;margin-top:8px">'
                                '<span style="font-size:10px;font-weight:800;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Nazwa</span>'
                                '<span style="font-size:10px;font-weight:800;color:#64748b;text-transform:uppercase;letter-spacing:.5px;text-align:right">Ilość / cena</span>'
                                '<span></span></div>',
                                unsafe_allow_html=True
                            )

                            for ti, item_p in enumerate(temu_list):
                                is_last = ti == len(temu_list) - 1
                                spec = f" · {item_p['spec']}" if item_p.get("spec") else ""
                                border_radius = "border-radius:0 0 10px 10px" if is_last else ""
                                c_row, c_del = st.columns([11, 1])
                                with c_row:
                                    st.markdown(
                                        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-top:0;{border_radius};'
                                        f'display:grid;grid-template-columns:1fr 100px;align-items:center;padding:4px 10px;gap:6px">'
                                        f'<span style="font-size:11px;font-weight:600;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                                        f'{item_p["name"][:58]}{"…" if len(item_p["name"])>58 else ""}'
                                        f'<span style="color:#94a3b8;font-size:10px"> {spec}</span></span>'
                                        f'<span style="font-size:11px;font-weight:800;color:#2563eb;text-align:right;white-space:nowrap">'
                                        f'{item_p["qty"]}× {item_p["price"]:.2f} zł</span>'
                                        f'</div>',
                                        unsafe_allow_html=True
                                    )
                                with c_del:
                                    if st.button("✕", key=f"temu_del_{ti}", use_container_width=True, help="Usuń"):
                                        st.session_state[temu_key].pop(ti)
                                        st.rerun()

                            if temu_list:
                                total_temu = sum(i["price"] * i["qty"] for i in temu_list)
                                st.markdown(
                                    f'<div style="background:#eff6ff;border-radius:10px;padding:10px 16px;margin:8px 0;'
                                    f'display:flex;justify-content:space-between;align-items:center">'
                                    f'<span style="font-size:13px;font-weight:800;color:#1d4ed8">🛒 Łączna wartość importu ({len(temu_list)} pozycji)</span>'
                                    f'<span style="font-size:18px;font-weight:900;color:#2563eb">{total_temu:.2f} zł</span></div>',
                                    unsafe_allow_html=True
                                )

                                if st.button("💾 Importuj do aplikacji", use_container_width=True, type="primary"):
                                    today_str = date.today().strftime("%d.%m.%Y")
                                    all_items = []
                                    progress = st.progress(0)
                                    status_txt = st.empty()
                                    for i, item_p in enumerate(temu_list):
                                        photo_b64 = ""
                                        thumb_url = item_p.get("thumb_url","")
                                        if thumb_url:
                                            try:
                                                import urllib.request
                                                req = urllib.request.Request(thumb_url, headers={"User-Agent":"Mozilla/5.0"})
                                                with urllib.request.urlopen(req, timeout=8) as r:
                                                    raw_img = r.read()
                                                img_obj = Image.open(io.BytesIO(raw_img))
                                                img_obj.thumbnail((120, 120))
                                                if img_obj.mode != "RGB": img_obj = img_obj.convert("RGB")
                                                buf = io.BytesIO()
                                                img_obj.save(buf, format="JPEG", quality=35)
                                                b64 = base64.b64encode(buf.getvalue()).decode()
                                                if len(b64) < 40000:
                                                    photo_b64 = b64
                                            except: pass

                                        status_txt.text(f"Pobieram zdjęcie {i+1}/{len(temu_list)}...")
                                        progress.progress((i+1) / len(temu_list))
                                        qty_p = item_p["qty"]
                                        price = item_p["price"]
                                        all_items.append({
                                            "id":          str(uuid.uuid4())[:8],
                                            "type":        xtype_import,
                                            "product":     item_p["name"],
                                            "qty":         qty_p,
                                            "unit_price":  price,
                                            "total_cost":  round(price * qty_p, 2),
                                            "sale_price":  0.0,
                                            "total_sale":  0.0,
                                            "profit":      0.0,
                                            "created":     today_str,
                                            "photo":       photo_b64,
                                            "ingredients": "[]",
                                        })

                                    status_txt.text(f"Zapisuję {len(all_items)} produktów do arkusza...")
                                    sheet = get_sheet()
                                    ensure_headers(sheet)
                                    records = list(sheet.get_all_records(numericise_ignore=["all"]))
                                    max_lp = 0
                                    for r in records:
                                        try: max_lp = max(max_lp, int(r.get("lp",0)))
                                        except: pass
                                    for i2, item in enumerate(all_items):
                                        item["lp"] = max_lp + i2 + 1
                                    rows_data = [row_vals(item) for item in all_items]
                                    sheet.append_rows(rows_data, value_input_option="USER_ENTERED")
                                    status_txt.empty()
                                    if temu_key in st.session_state:
                                        del st.session_state[temu_key]
                                    st.session_state.wpisy = load_items()
                                    st.success(f"✅ Zaimportowano {len(all_items)} produktów!")
                                    st.session_state.tab = "lista"
                                    st.rerun()
                            else:
                                st.warning("⚠️ Lista jest pusta — wszystkie pozycje zostały usunięte.")
            except Exception as e:
                st.error(f"❌ Błąd: {e}")

    # ── VINTED ───────────────────────────────────────────────────────────────
    else:
        st.markdown("#### 👗 Import z Vinted")
        st.markdown("""
        **Jak pobrać plik?**
        1. Zaloguj się na **vinted.pl** → kliknij swój profil → **Moje zamówienia**
        2. Kliknij prawym przyciskiem myszy → **Zapisz jako...**
        3. Wybierz **„Strona internetowa, tylko HTML"** (sam plik `.html`, bez folderu `_files`)
        4. Wgraj plik poniżej
        
        > ℹ️ Zdjęcia produktów nie są dostępne w zapisanym pliku — zostaną pominięte.
        """)

        uploaded_vinted = st.file_uploader("Wgraj plik HTML z Vinted", type=["html","htm"], key="vinted_upload")

        vinted_import_type = st.selectbox(
            "Importuj jako:",
            ["🧩 Składniki (materiały zakupione)", "🏷️ Produkty gotowe"],
            key="vinted_import_type"
        )
        xtype_vinted = "skladnik" if "Składniki" in vinted_import_type else "produkt"

        # Opcja filtrowania po statusie
        vinted_filter = st.selectbox(
            "Filtruj zamówienia:",
            ["Wszystkie", "Tylko zrealizowane", "Tylko w toku", "Bez anulowanych i nieudanych", "Bez anulowanych", "Bez nieudanych"],
            key="vinted_filter"
        )

        if uploaded_vinted:
            try:
                from bs4 import BeautifulSoup

                html_content = uploaded_vinted.read().decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html_content, "html.parser")

                titles   = soup.find_all("div", attrs={"data-testid": "my-orders-item--title"})
                contents = soup.find_all("div", attrs={"data-testid": "my-orders-item--content"})
                prefixes = soup.find_all("div", attrs={"data-testid": "my-orders-item--prefix"})

                if not titles:
                    st.error("❌ Nie znaleziono zamówień w tym pliku.")
                    st.info("💡 Upewnij się, że to strona 'Moje zamówienia' z Vinted i że zapisałeś ją jako HTML.")
                else:
                    # Zbuduj listę surowych zamówień
                    raw_orders = []
                    for t, c, p in zip(titles, contents, prefixes):
                        name       = t.get_text(strip=True)
                        content_tx = c.get_text(strip=True)
                        status_tx  = p.get_text(strip=True)

                        # Wyciągnij cenę (np. "20,99 zł")
                        price_match = re.search(r'(\d+[,\.]\d+)\s*(?:\xa0)?zł', content_tx)
                        price = parse_price(price_match.group(1)) if price_match else 0.0

                        # Normalizuj status
                        status_lower = status_tx.lower()
                        if "zrealizowane" in status_lower or "zrealizowano" in status_lower:
                            status_norm = "zrealizowane"
                        elif "anulowano" in status_lower or "zwrot zakończył się pomyślnie" in status_lower:
                            status_norm = "anulowane"
                        elif "nie wysłano" in status_lower or "pieniądze zostały zwrócone" in status_lower:
                            status_norm = "nieudane"
                        elif "w toku" in status_lower:
                            status_norm = "w_toku"
                        else:
                            status_norm = "inne"

                        raw_orders.append({
                            "name":   name,
                            "price":  price,
                            "status": status_norm,
                            "status_raw": status_tx,
                        })

                    # Filtrowanie
                    if vinted_filter == "Tylko zrealizowane":
                        filtered_orders = [o for o in raw_orders if o["status"] == "zrealizowane"]
                    elif vinted_filter == "Tylko w toku":
                        filtered_orders = [o for o in raw_orders if o["status"] == "w_toku"]
                    elif vinted_filter == "Bez anulowanych i nieudanych":
                        filtered_orders = [o for o in raw_orders if o["status"] not in ("anulowane", "nieudane")]
                    elif vinted_filter == "Bez anulowanych":
                        filtered_orders = [o for o in raw_orders if o["status"] != "anulowane"]
                    elif vinted_filter == "Bez nieudanych":
                        filtered_orders = [o for o in raw_orders if o["status"] != "nieudane"]
                    else:
                        filtered_orders = raw_orders

                    if not filtered_orders:
                        st.warning("⚠️ Brak zamówień po zastosowaniu filtra.")
                    else:
                        # Inicjuj listę w session_state (klucz zależy od pliku + filtra)
                        vinted_key = f"vinted_preview_{hash(uploaded_vinted.name)}_{vinted_filter}"
                        if vinted_key not in st.session_state:
                            st.session_state[vinted_key] = [
                                {
                                    "name":       o["name"],
                                    "price":      o["price"],
                                    "status":     o["status"],
                                    "status_raw": o["status_raw"],
                                }
                                for o in filtered_orders
                            ]

                        vinted_list = st.session_state[vinted_key]

                        status_emoji = {
                            "zrealizowane": "✅",
                            "anulowane":    "❌",
                            "nieudane":     "⚠️",
                            "w_toku":       "🔄",
                            "inne":         "ℹ️",
                        }

                        st.success(f"✅ Znaleziono **{len(titles)}** zamówień · po filtrze: **{len(filtered_orders)}** · do importu: **{len(vinted_list)}**")

                        # Nagłówek tabeli
                        st.markdown(
                            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px 10px 0 0;'
                            'padding:5px 10px;display:grid;grid-template-columns:24px 1fr 80px 34px;gap:6px;margin-top:8px">'
                            '<span></span>'
                            '<span style="font-size:10px;font-weight:800;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Nazwa</span>'
                            '<span style="font-size:10px;font-weight:800;color:#64748b;text-transform:uppercase;letter-spacing:.5px;text-align:right">Cena</span>'
                            '<span></span></div>',
                            unsafe_allow_html=True
                        )

                        for vi, o in enumerate(vinted_list):
                            is_last = vi == len(vinted_list) - 1
                            border_radius = "border-radius:0 0 10px 10px" if is_last else ""
                            emoji = status_emoji.get(o["status"], "ℹ️")
                            c_row, c_del = st.columns([11, 1])
                            with c_row:
                                st.markdown(
                                    f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-top:0;{border_radius};'
                                    f'display:grid;grid-template-columns:20px 1fr 80px;align-items:center;padding:4px 10px;gap:6px">'
                                    f'<span style="font-size:12px">{emoji}</span>'
                                    f'<span style="font-size:11px;font-weight:600;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                                    f'{o["name"][:58]}{"…" if len(o["name"])>58 else ""}</span>'
                                    f'<span style="font-size:11px;font-weight:800;color:#16a34a;text-align:right;white-space:nowrap">'
                                    f'{o["price"]:.2f} zł</span>'
                                    f'</div>',
                                    unsafe_allow_html=True
                                )
                            with c_del:
                                if st.button("✕", key=f"vinted_del_{vi}", use_container_width=True, help="Usuń"):
                                    st.session_state[vinted_key].pop(vi)
                                    st.rerun()

                        if vinted_list:
                            total_val = sum(o["price"] for o in vinted_list)
                            st.markdown(
                                f'<div style="background:#f0fdf4;border-radius:10px;padding:10px 16px;margin:8px 0;'
                                f'display:flex;justify-content:space-between;align-items:center">'
                                f'<span style="font-size:13px;font-weight:800;color:#166534">💚 Łączna wartość importu ({len(vinted_list)} pozycji)</span>'
                                f'<span style="font-size:18px;font-weight:900;color:#16a34a">{total_val:.2f} zł</span></div>',
                                unsafe_allow_html=True
                            )

                            if st.button("💾 Importuj do aplikacji", use_container_width=True, type="primary", key="vinted_import_btn"):
                                today_str = date.today().strftime("%d.%m.%Y")
                                all_items = []
                                for o in vinted_list:
                                    price = o["price"]
                                    all_items.append({
                                        "id":          str(uuid.uuid4())[:8],
                                        "type":        xtype_vinted,
                                        "product":     o["name"],
                                        "qty":         1,
                                        "unit_price":  price,
                                        "total_cost":  price,
                                        "sale_price":  0.0,
                                        "total_sale":  0.0,
                                        "profit":      0.0,
                                        "created":     today_str,
                                        "photo":       "",
                                        "ingredients": "[]",
                                        "wzorki":      "[]",
                                    })

                                with st.spinner(f"Zapisuję {len(all_items)} pozycji..."):
                                    sheet = get_sheet()
                                    ensure_headers(sheet)
                                    records = list(sheet.get_all_records(numericise_ignore=["all"]))
                                    max_lp = 0
                                    for r in records:
                                        try: max_lp = max(max_lp, int(r.get("lp",0)))
                                        except: pass
                                    for i2, item in enumerate(all_items):
                                        item["lp"] = max_lp + i2 + 1
                                    rows_data = [row_vals(item) for item in all_items]
                                    sheet.append_rows(rows_data, value_input_option="USER_ENTERED")

                                if vinted_key in st.session_state:
                                    del st.session_state[vinted_key]
                                st.session_state.wpisy = load_items()
                                st.success(f"✅ Zaimportowano {len(all_items)} pozycji z Vinted!")
                                st.session_state.tab = "lista"
                                st.rerun()
                        else:
                            st.warning("⚠️ Lista jest pusta — wszystkie pozycje zostały usunięte.")

            except ImportError:
                st.error("❌ Brakuje biblioteki `beautifulsoup4`. Dodaj `beautifulsoup4` do `requirements.txt`.")
            except Exception as e:
                st.error(f"❌ Błąd: {e}")


# ════════════════════════════════════════════════════════════════════════════
# PODSUMOWANIE
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.tab == "stats":

    def fsum(lst, key):
        return sum(safe_num(s.get(key, 0)) for s in lst)

    total_cost_prod  = fsum(produkty, "total_cost")
    total_sale_all   = fsum(produkty, "total_sale")
    total_profit     = fsum(produkty, "profit")
    total_qty_p      = sum(int(safe_num(s.get("qty",0))) for s in produkty)
    total_cost_skl   = fsum(skladniki, "total_cost")
    total_qty_skl    = sum(int(safe_num(s.get("qty",0))) for s in skladniki)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#2563eb">{len(produkty)}</div><div class="stat-label">🏷️ Produkty gotowe</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#7c3aed">{len(skladniki)}</div><div class="stat-label">🧩 Składniki</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#0891b2">{total_qty_skl}</div><div class="stat-label">📦 Sztuk składników</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    total_cost_wyp = sum(safe_num(x.get("total_cost",0)) for x in wyposazenie)
    if wyposazenie:
        st.markdown('<div style="font-size:13px;font-weight:800;color:#0e7490;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px">🔧 Wyposażenie</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="fin-box" style="border-left:4px solid #0891b2"><div class="fin-label">🔧 Łączny koszt wyposażenia</div><div class="fin-val" style="color:#0891b2">{total_cost_wyp:.2f} zł</div></div>',
            unsafe_allow_html=True
        )

    if skladniki:
        st.markdown('<div style="font-size:13px;font-weight:800;color:#6d28d9;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px">🧩 Zakupione materiały</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="fin-box" style="border-left:4px solid #8b5cf6"><div class="fin-label">💜 Łączny koszt zakupów (składniki)</div><div class="fin-val" style="color:#7c3aed">{total_cost_skl:.2f} zł</div></div>',
            unsafe_allow_html=True
        )
        st.markdown("**📦 Najdroższe zakupy:**")
        for i, s in enumerate(sorted(skladniki, key=lambda x: safe_num(x.get("total_cost",0)), reverse=True)[:5], 1):
            tc = safe_num(s.get("total_cost",0))
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 14px;'
                f'background:white;border-radius:10px;margin-bottom:5px;box-shadow:0 1px 6px rgba(0,0,0,0.05);border-left:3px solid #8b5cf6">'
                f'<span style="font-weight:700;font-size:12px;color:#374151">#{i} {s.get("product","—")[:50]}</span>'
                f'<span style="font-weight:900;font-size:14px;color:#7c3aed">{tc:.2f} zł</span></div>',
                unsafe_allow_html=True
            )

    if produkty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:13px;font-weight:800;color:#1d4ed8;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px">🏷️ Produkty gotowe</div>', unsafe_allow_html=True)
        pcolor = "#16a34a" if total_profit >= 0 else "#ef4444"
        st.markdown(
            f'<div class="fin-box" style="border-left:4px solid #3b82f6"><div class="fin-label">🛒 Łączna sprzedaż</div><div class="fin-val" style="color:#2563eb">{total_sale_all:.2f} zł</div></div>'
            f'<div class="fin-box" style="border-left:4px solid #ea580c"><div class="fin-label">📦 Łączny koszt produkcji</div><div class="fin-val" style="color:#ea580c">{total_cost_prod:.2f} zł</div></div>'
            f'<div class="fin-box" style="border-left:4px solid {pcolor}"><div class="fin-label">💰 Łączny zysk</div><div class="fin-val" style="color:{pcolor}">{total_profit:.2f} zł</div></div>',
            unsafe_allow_html=True
        )
        if total_sale_all > 0:
            marza = (total_profit / total_sale_all) * 100
            mc = "#16a34a" if marza >= 0 else "#ef4444"
            st.markdown(f'<div class="fin-box"><div class="fin-label">📈 Marża</div><div class="fin-val" style="color:{mc}">{marza:.1f}%</div></div>', unsafe_allow_html=True)

        st.markdown("**🏆 Top produkty wg zysku:**")
        for i, s in enumerate(sorted(produkty, key=lambda x: safe_num(x.get("profit",0)), reverse=True)[:5], 1):
            p     = safe_num(s.get("profit",0))
            color = "#16a34a" if p >= 0 else "#ef4444"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 14px;'
                f'background:white;border-radius:10px;margin-bottom:5px;box-shadow:0 1px 6px rgba(0,0,0,0.05);border-left:3px solid #3b82f6">'
                f'<span style="font-weight:700;font-size:12px;color:#0f172a">#{i} {s.get("product","—")[:50]}</span>'
                f'<span style="font-weight:900;font-size:14px;color:{color}">{p:.2f} zł</span></div>',
                unsafe_allow_html=True
            )

    if not produkty and not skladniki:
        st.info("Brak danych — dodaj wpisy żeby zobaczyć statystyki.")

    st.markdown("---")
    st.markdown("#### ⚠️ Strefa niebezpieczna")
    if st.button("🗑️ Usuń wszystkie wpisy", use_container_width=True):
        if st.session_state.get("confirm_del_all"):
            with st.spinner("Usuwanie..."):
                delete_all()
                st.session_state.wpisy = load_items()
                st.session_state.confirm_del_all = False
            st.success("Usunięto!")
            st.rerun()
        else:
            st.session_state.confirm_del_all = True
            st.warning("⚠️ Kliknij jeszcze raz żeby potwierdzić!")
