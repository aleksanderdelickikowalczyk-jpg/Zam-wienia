import streamlit as st
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

.top-header { background: linear-gradient(135deg, #1d4ed8, #3b82f6); color: white; border-radius: 16px; padding: 18px 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 16px rgba(29,78,216,0.3); }
.top-header h1 { font-size: 21px; font-weight: 900; margin: 0; }
.top-header .count { background: rgba(255,255,255,0.22); padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 800; }

.card-produkt { background: white; border-radius: 16px; padding: 16px; margin-bottom: 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-left: 5px solid #3b82f6; }
.card-skladnik { background: white; border-radius: 16px; padding: 16px; margin-bottom: 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-left: 5px solid #8b5cf6; }

.item-name { font-size: 18px; font-weight: 900; color: #0f172a; margin-bottom: 2px; }
.item-date { font-size: 12px; color: #94a3b8; font-weight: 600; margin-bottom: 10px; }

.type-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; margin-bottom: 8px; }
.badge-produkt { background: #dbeafe; color: #1d4ed8; }
.badge-skladnik { background: #ede9fe; color: #6d28d9; }

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
</style>
""", unsafe_allow_html=True)

# ── Google Sheets ─────────────────────────────────────────────
HEADERS = ["id","type","product","qty","unit_price","total_cost","sale_price","total_sale","profit","created","photo","ingredients"]

@st.cache_resource
def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.Client(auth=creds)
    return client.open(st.secrets["spreadsheet_name"]).sheet1

def ensure_headers(sheet):
    first = sheet.row_values(1)
    if not first or first[0] != "id":
        sheet.clear()
        sheet.append_row(HEADERS)

def load_items():
    try:
        sheet = get_sheet()
        ensure_headers(sheet)
        records = sheet.get_all_records()
        return list(records)
    except Exception as e:
        st.error(f"❌ Błąd połączenia: {type(e).__name__}: {e}")
        return []

def safe_val(v):
    if isinstance(v, (float, int)):
        return v
    try:
        return float(str(v).replace(",","."))
    except:
        return v

NUMERIC = {"qty","unit_price","total_cost","sale_price","total_sale","profit"}

def append_item(item: dict):
    sheet = get_sheet()
    ensure_headers(sheet)
    row = [safe_val(item.get(h,"")) if h in NUMERIC else item.get(h,"") for h in HEADERS]
    sheet.append_row(row, value_input_option="USER_ENTERED")

def update_item(item: dict):
    sheet = get_sheet()
    records = list(sheet.get_all_records())
    for i, r in enumerate(records, start=2):
        if str(r.get("id")) == str(item["id"]):
            row = [safe_val(item.get(h,"")) if h in NUMERIC else item.get(h,"") for h in HEADERS]
            sheet.update(f"A{i}:{chr(64+len(HEADERS))}{i}", [row], value_input_option="USER_ENTERED")
            return

def delete_item(item_id: str):
    sheet = get_sheet()
    records = list(sheet.get_all_records())
    for i, r in enumerate(records, start=2):
        if str(r.get("id")) == str(item_id):
            sheet.delete_rows(i)
            return

def delete_all():
    sheet = get_sheet()
    sheet.clear()
    sheet.append_row(HEADERS)

def img_to_b64(f) -> str:
    img = Image.open(f)
    img.thumbnail((500, 500))
    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72)
    return base64.b64encode(buf.getvalue()).decode()

def fmt_pln(v):
    try:
        s = str(v).strip().replace(",",".")
        return f"{float(s):.2f} zł"
    except: return "— zł"

def safe_float(v):
    try:
        s = str(v).strip().replace(",",".")
        return float(s)
    except: return 0.0

def calc_ingredients_cost(ing_list: list, skladniki_map: dict) -> float:
    total = 0.0
    for ing in ing_list:
        name = ing.get("name", "")
        qpp  = float(ing.get("qty_per_product", 1))
        if name in skladniki_map:
            unit_price = safe_float(skladniki_map[name].get("unit_price", 0))
            total += unit_price * qpp
    return round(total, 2)

# ── Stan ──────────────────────────────────────────────────────
for k, v in [("tab","lista"),("editing",None),("wpisy",None)]:
    if k not in st.session_state: st.session_state[k] = v

if st.session_state.wpisy is None:
    loaded = load_items()
    st.session_state.wpisy = loaded if isinstance(loaded, list) else []
items = st.session_state.wpisy if isinstance(st.session_state.wpisy, list) else []

produkty      = [x for x in items if x.get("type","") == "produkt"]
skladniki     = [x for x in items if x.get("type","") == "skladnik"]
skladniki_map = {s.get("product",""): s for s in skladniki}

# ── Nagłówek ──────────────────────────────────────────────────
st.markdown(f"""
<div class="top-header">
    <h1>🛒 Ewidencja Sprzedaży</h1>
    <span class="count">🏷️ {len(produkty)} prod. · 🧩 {len(skladniki)} skł.</span>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("📋 Lista", use_container_width=True, type="primary" if st.session_state.tab=="lista" else "secondary"):
        st.session_state.tab="lista"; st.session_state.editing=None; st.rerun()
with c2:
    if st.button("➕ Dodaj", use_container_width=True, type="primary" if st.session_state.tab=="dodaj" else "secondary"):
        st.session_state.tab="dodaj"; st.session_state.editing=None; st.rerun()
with c3:
    if st.button("📊 Podsumowanie", use_container_width=True, type="primary" if st.session_state.tab=="stats" else "secondary"):
        st.session_state.tab="stats"; st.session_state.editing=None; st.rerun()

st.markdown("---")

# ── Funkcja parsowania cen ──────────────────────────────
def parse_price(s):
    """
    Zamienia input użytkownika na float.
    Obsługuje: 6,92 ; 6.92 ; "6,92" ; "6.92"
    """
    try:
        if isinstance(s, (int, float)):
            return float(s)
        s = str(s).strip()
        if not s:
            return 0.0
        s = s.replace(",", ".")
        return float(s)
    except:
        return 0.0

    col1, col2 = st.columns(2)
    with col1:
        qty = st.number_input("Ilość sztuk *", min_value=1, step=1,
            value=int(ed.get("qty",1)) if is_edit else 1)
    with col2:
        unit_price_str = st.text_input(
            "Cena jednostkowa (zł) *",
            value=str(ed.get("unit_price","0")),
        )
        unit_price = parse_price(unit_price_str)

    # ── Lista składników (tylko produkt gotowy) ───────────────────────────────
    ingredients_json = "[]"
    ingredients_cost = 0.0

    if not is_skladnik:
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
                ing_qpp = st.number_input("Ilość/szt.", min_value=0.1, step=0.1, value=1.0, format="%.1f",
                    help="Ile sztuk tego składnika potrzeba na 1 produkt gotowy")
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
            ingredients_cost = calc_ingredients_cost(st.session_state.ing_list, skladniki_map)
            for idx, ing in enumerate(st.session_state.ing_list):
                s_data   = skladniki_map.get(ing.get("name",""), {})
                up       = safe_float(s_data.get("unit_price", 0))
                qpp      = float(ing.get("qty_per_product", 1))
                ing_cost = round(up * qpp, 2)
                ic1, ic2, ic3 = st.columns([4, 2, 1])
                with ic1:
                    st.markdown(f"🧩 **{ing['name']}**")
                with ic2:
                    st.markdown(f"<div style='padding-top:6px;font-size:13px;font-weight:700;color:#7c3aed'>{qpp:.1f} szt. → {ing_cost:.2f} zł</div>", unsafe_allow_html=True)
                with ic3:
                    if st.button("✕", key=f"rmi_{idx}", use_container_width=True):
                        st.session_state.ing_list.pop(idx)
                        st.rerun()

            st.markdown(f"""
            <div style="background:#ede9fe;border-radius:10px;padding:10px 16px;margin:8px 0;
                        display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:13px;font-weight:800;color:#6d28d9">💜 Koszt składników / 1 szt. produktu</span>
                <span style="font-size:18px;font-weight:900;color:#7c3aed">{ingredients_cost:.2f} zł</span>
            </div>
            """, unsafe_allow_html=True)

        ingredients_json = json.dumps(st.session_state.get("ing_list", []), ensure_ascii=False)

    # ── Koszt całości ─────────────────────────────────────────────────────────
    st.markdown("---")
    has_ingredients = not is_skladnik and bool(st.session_state.get("ing_list"))
    if has_ingredients:
        total_cost = round(ingredients_cost * qty, 2)
        label      = "📦 Koszt całości (ze składników × ilość)"
    else:
        total_cost = round(qty * unit_price, 2)
        label      = "📦 Koszt całości (auto)"

    st.markdown(f"""
    <div style="background:#fef3c7;border-radius:12px;padding:12px 16px;margin-bottom:12px;
                display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:14px;font-weight:800;color:#92400e">{label}</span>
        <span style="font-size:20px;font-weight:900;color:#b45309">{total_cost:.2f} zł</span>
    </div>
    """, unsafe_allow_html=True)

    sale_price = 0.0
    total_sale = 0.0
    profit     = 0.0
    if not is_skladnik:
        sale_price_str = st.text_input("Cena sprzedaży za sztukę (zł) *",
            value=str(ed.get("sale_price","0")).replace(".",",") if is_edit else "0",
            placeholder="np. 19,99")
        sale_price = parse_price(sale_price_str)
        total_sale = round(qty * sale_price, 2)
        profit     = round(total_sale - total_cost, 2)
        profit_color_style = "#16a34a" if profit >= 0 else "#ef4444"
        profit_icon        = "📈" if profit >= 0 else "📉"
        st.markdown(f"""
        <div style="background:#f0fdf4;border-radius:12px;padding:14px 16px;margin-bottom:16px">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <span style="font-size:13px;font-weight:700;color:#64748b">💵 Łączna cena sprzedaży</span>
                <span style="font-size:17px;font-weight:900;color:#16a34a">{total_sale:.2f} zł</span>
            </div>
            <div style="display:flex;justify-content:space-between">
                <span style="font-size:13px;font-weight:700;color:#64748b">{profit_icon} Zysk</span>
                <span style="font-size:17px;font-weight:900;color:{profit_color_style}">{profit:.2f} zł</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("**📷 Zdjęcie**")
    uploaded = st.file_uploader("Zdjęcie", type=["jpg","jpeg","png","webp"], label_visibility="collapsed")
    existing_photo = ""
    if is_edit and ed.get("photo"):
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
            st.rerun()

    if save_clicked:
        if not product.strip():
            st.error("⚠️ Podaj nazwę!")
        else:
            photo_b64 = img_to_b64(uploaded) if uploaded else existing_photo
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
# PODSUMOWANIE
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.tab == "stats":

    def fsum(lst, key):
        return sum(safe_float(s.get(key, 0)) for s in lst)

    total_cost_all = fsum(produkty, "total_cost")
    total_sale_all = fsum(produkty, "total_sale")
    total_profit   = fsum(produkty, "profit")
    total_qty_p    = sum(int(safe_float(s.get("qty",0))) for s in produkty)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#2563eb">{len(produkty)}</div><div class="stat-label">🏷️ Produkty gotowe</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#7c3aed">{len(skladniki)}</div><div class="stat-label">🧩 Składniki</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#0891b2">{total_qty_p}</div><div class="stat-label">📦 Sztuk produktów</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    profit_color_fin = "#16a34a" if total_profit >= 0 else "#ef4444"
    st.markdown(f"""
    <div class="fin-box"><div class="fin-label">🛒 Łączna sprzedaż (produkty)</div><div class="fin-val" style="color:#2563eb">{total_sale_all:.2f} zł</div></div>
    <div class="fin-box"><div class="fin-label">📦 Łączny koszt (produkty)</div><div class="fin-val" style="color:#ea580c">{total_cost_all:.2f} zł</div></div>
    <div class="fin-box"><div class="fin-label">💰 Łączny zysk</div><div class="fin-val" style="color:{profit_color_fin}">{total_profit:.2f} zł</div></div>
    """, unsafe_allow_html=True)

    if total_sale_all > 0:
        marza = (total_profit / total_sale_all) * 100
        st.markdown(f'<div class="fin-box"><div class="fin-label">📈 Marża</div><div class="fin-val" style="color:{"#16a34a" if marza>=0 else "#ef4444"}">{marza:.1f}%</div></div>', unsafe_allow_html=True)

    if produkty:
        st.markdown("#### 🏆 Top produkty wg zysku")
        for i, s in enumerate(sorted(produkty, key=lambda x: safe_float(x.get("profit",0)), reverse=True)[:5], 1):
            p     = float(s.get("profit",0) or 0)
            color = "#16a34a" if p >= 0 else "#ef4444"
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;
                        background:white;border-radius:10px;margin-bottom:6px;box-shadow:0 1px 6px rgba(0,0,0,0.05)">
                <span style="font-weight:800;font-size:14px">#{i} {s.get('product','—')}</span>
                <span style="font-weight:900;font-size:15px;color:{color}">{p:.2f} zł</span>
            </div>""", unsafe_allow_html=True)

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
