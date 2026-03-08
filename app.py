import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import base64
import uuid
from PIL import Image
import io

# ── Konfiguracja strony ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ewidencja Sprzedaży",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');
html, body, [class*="css"] { font-family: 'Nunito', sans-serif !important; }
.main .block-container { padding: 1rem 1rem 5rem; max-width: 620px; }
#MainMenu, footer, header { visibility: hidden; }

.top-header {
    background: linear-gradient(135deg, #1d4ed8, #3b82f6);
    color: white; border-radius: 16px;
    padding: 18px 20px; margin-bottom: 20px;
    display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 4px 16px rgba(29,78,216,0.3);
}
.top-header h1 { font-size: 21px; font-weight: 900; margin: 0; }
.top-header .count { background: rgba(255,255,255,0.22); padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 800; }

.sale-card {
    background: white; border-radius: 16px; padding: 16px;
    margin-bottom: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border-left: 5px solid #3b82f6;
}
.sale-product { font-size: 18px; font-weight: 900; color: #0f172a; margin-bottom: 2px; }
.sale-date { font-size: 12px; color: #94a3b8; font-weight: 600; margin-bottom: 10px; }

.price-grid {
    display: grid; grid-template-columns: 1fr 1fr 1fr;
    gap: 8px; margin: 10px 0;
}
.price-box {
    background: #f8fafc; border-radius: 10px;
    padding: 10px 8px; text-align: center;
}
.price-box .pb-label { font-size: 10px; font-weight: 800; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 3px; }
.price-box .pb-val { font-size: 16px; font-weight: 900; }
.pb-blue { color: #2563eb; }
.pb-gray { color: #475569; }
.pb-green { color: #16a34a; }
.pb-orange { color: #ea580c; }

.profit-row {
    display: flex; justify-content: space-between; align-items: center;
    background: #f0fdf4; border-radius: 10px; padding: 10px 14px; margin-top: 8px;
}
.profit-label { font-size: 13px; font-weight: 800; color: #64748b; }
.profit-val { font-size: 18px; font-weight: 900; }
.profit-pos { color: #16a34a; }
.profit-neg { color: #ef4444; }

.stat-box { background: white; border-radius: 14px; padding: 14px 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
.stat-num { font-size: 28px; font-weight: 900; }
.stat-label { font-size: 11px; font-weight: 700; color: #64748b; margin-top: 2px; }

.fin-box { background: white; border-radius: 14px; padding: 18px 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); margin-bottom: 10px; }
.fin-label { font-size: 13px; font-weight: 700; color: #64748b; margin-bottom: 4px; }
.fin-val { font-size: 30px; font-weight: 900; }
</style>
""", unsafe_allow_html=True)

# ── Google Sheets ────────────────────────────────────────────────────────────
HEADERS = ["id","product","qty","unit_price","total_cost","sale_price","total_sale","profit","created","photo"]

@st.cache_resource
def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(st.secrets["spreadsheet_name"]).sheet1

def ensure_headers(sheet):
    first = sheet.row_values(1)
    if not first or first[0] != "id":
        sheet.clear()
        sheet.append_row(HEADERS)

def load_sales():
    try:
        sheet = get_sheet()
        ensure_headers(sheet)
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"❌ Błąd połączenia: {e}")
        return []

def append_sale(sale: dict):
    sheet = get_sheet()
    ensure_headers(sheet)
    sheet.append_row([sale.get(h,"") for h in HEADERS])

def update_sale(sale: dict):
    sheet = get_sheet()
    records = sheet.get_all_records()
    for i, r in enumerate(records, start=2):
        if str(r.get("id")) == str(sale["id"]):
            sheet.update(f"A{i}:{chr(64+len(HEADERS))}{i}", [[sale.get(h,"") for h in HEADERS]])
            return

def delete_sale(sale_id: str):
    sheet = get_sheet()
    records = sheet.get_all_records()
    for i, r in enumerate(records, start=2):
        if str(r.get("id")) == str(sale_id):
            sheet.delete_rows(i)
            return

def delete_all():
    sheet = get_sheet()
    sheet.clear()
    sheet.append_row(HEADERS)

def img_to_b64(f) -> str:
    img = Image.open(f)
    img.thumbnail((500, 500))
    # Konwertuj RGBA/P do RGB (PNG z przezroczystością nie zapisze się jako JPEG)
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
    try: return f"{float(v):.2f} zł"
    except: return "— zł"

def profit_color(v):
    try: return "profit-pos" if float(v) >= 0 else "profit-neg"
    except: return "profit-pos"

# ── Stan aplikacji ───────────────────────────────────────────────────────────
if "tab" not in st.session_state: st.session_state.tab = "lista"
if "editing" not in st.session_state: st.session_state.editing = None
if "sales" not in st.session_state: st.session_state.sales = None

if st.session_state.sales is None:
    st.session_state.sales = load_sales()
sales = st.session_state.sales

# ── Nagłówek ─────────────────────────────────────────────────────────────────
total_sprzedaz = sum(float(s.get("total_sale",0) or 0) for s in sales)
st.markdown(f"""
<div class="top-header">
    <h1>🛒 Ewidencja Sprzedaży</h1>
    <span class="count">{len(sales)} wpisów</span>
</div>
""", unsafe_allow_html=True)

# ── Nawigacja ─────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("📋 Lista", use_container_width=True,
                 type="primary" if st.session_state.tab=="lista" else "secondary"):
        st.session_state.tab="lista"; st.session_state.editing=None; st.rerun()
with c2:
    if st.button("➕ Dodaj wpis", use_container_width=True,
                 type="primary" if st.session_state.tab=="dodaj" else "secondary"):
        st.session_state.tab="dodaj"; st.session_state.editing=None; st.rerun()
with c3:
    if st.button("📊 Podsumowanie", use_container_width=True,
                 type="primary" if st.session_state.tab=="stats" else "secondary"):
        st.session_state.tab="stats"; st.session_state.editing=None; st.rerun()

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# LISTA
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.tab == "lista":

    col_s, col_r = st.columns([4,1])
    with col_s:
        search = st.text_input("Szukaj", placeholder="🔍 Szukaj produktu...", label_visibility="collapsed")
    with col_r:
        if st.button("🔄", use_container_width=True, help="Odśwież"):
            st.session_state.sales = load_sales(); st.rerun()

    filtered = [s for s in sales if search.lower() in str(s.get("product","")).lower()] if search else sales

    if not filtered:
        st.markdown("""
        <div style="text-align:center;padding:48px 20px;color:#94a3b8">
            <div style="font-size:52px;margin-bottom:12px">📭</div>
            <p style="font-size:16px;font-weight:700">Brak wpisów sprzedaży</p>
            <small>Dodaj pierwszy wpis klikając ➕</small>
        </div>""", unsafe_allow_html=True)
    else:
        for s in reversed(filtered):
            sid = str(s.get("id",""))
            photo = s.get("photo","")
            profit = s.get("profit", 0)

            # Zdjęcie produktu
            if photo:
                try:
                    st.image(base64.b64decode(photo), use_container_width=True,
                             output_format="JPEG")
                except: pass

            st.markdown(f"""
            <div class="sale-card">
                <div class="sale-product">📦 {s.get('product','—')}</div>
                <div class="sale-date">📅 {s.get('created','')}</div>
                <div class="price-grid">
                    <div class="price-box">
                        <div class="pb-label">Ilość</div>
                        <div class="pb-val pb-gray">{s.get('qty','—')} szt.</div>
                    </div>
                    <div class="price-box">
                        <div class="pb-label">Cena jedn.</div>
                        <div class="pb-val pb-blue">{fmt_pln(s.get('unit_price'))}</div>
                    </div>
                    <div class="price-box">
                        <div class="pb-label">Koszt całość</div>
                        <div class="pb-val pb-orange">{fmt_pln(s.get('total_cost'))}</div>
                    </div>
                </div>
                <div class="price-grid">
                    <div class="price-box" style="grid-column: span 2">
                        <div class="pb-label">Cena sprzedaży (łącznie)</div>
                        <div class="pb-val pb-green">{fmt_pln(s.get('total_sale'))}</div>
                    </div>
                    <div class="price-box">
                        <div class="pb-label">Cena sprzed. / szt.</div>
                        <div class="pb-val pb-green">{fmt_pln(s.get('sale_price'))}</div>
                    </div>
                </div>
                <div class="profit-row">
                    <span class="profit-label">💰 Zysk</span>
                    <span class="profit-val {profit_color(profit)}">{fmt_pln(profit)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            ca, cb = st.columns(2)
            with ca:
                if st.button("✏️ Edytuj", key=f"e_{sid}", use_container_width=True):
                    st.session_state.editing = s
                    st.session_state.tab = "dodaj"
                    st.rerun()
            with cb:
                if st.button("🗑️ Usuń", key=f"d_{sid}", use_container_width=True):
                    with st.spinner("Usuwanie..."):
                        delete_sale(sid)
                        st.session_state.sales = load_sales()
                    st.rerun()
            st.markdown("<hr style='margin:4px 0 16px;border-color:#f1f5f9'>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# DODAJ / EDYTUJ
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.tab == "dodaj":
    ed = st.session_state.editing
    is_edit = ed is not None

    st.markdown(f"### {'✏️ Edytuj wpis' if is_edit else '➕ Nowy wpis sprzedaży'}")

    product = st.text_input("Nazwa produktu *",
        value=ed.get("product","") if is_edit else "",
        placeholder="np. Koszulka bawełniana biała")

    col1, col2 = st.columns(2)
    with col1:
        qty = st.number_input("Ilość sztuk *",
            min_value=1, step=1,
            value=int(ed.get("qty",1)) if is_edit else 1)
    with col2:
        unit_price = st.number_input("Cena jednostkowa (zł) *",
            min_value=0.0, step=0.01, format="%.2f",
            value=float(ed.get("unit_price",0)) if is_edit else 0.0,
            help="Cena zakupu jednej sztuki")

    # Auto-wyliczony koszt całości
    total_cost = round(qty * unit_price, 2)
    st.markdown(f"""
    <div style="background:#fef3c7;border-radius:12px;padding:12px 16px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:14px;font-weight:800;color:#92400e">📦 Koszt całości (auto)</span>
        <span style="font-size:20px;font-weight:900;color:#b45309">{total_cost:.2f} zł</span>
    </div>
    """, unsafe_allow_html=True)

    sale_price = st.number_input("Cena sprzedaży za sztukę (zł) *",
        min_value=0.0, step=0.01, format="%.2f",
        value=float(ed.get("sale_price",0)) if is_edit else 0.0,
        help="Za ile sprzedajesz jedną sztukę")

    total_sale = round(qty * sale_price, 2)
    profit = round(total_sale - total_cost, 2)

    # Podgląd wyliczeń na żywo
    profit_color_style = "#16a34a" if profit >= 0 else "#ef4444"
    profit_icon = "📈" if profit >= 0 else "📉"
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

    # Zdjęcie
    st.markdown("**📷 Zdjęcie produktu**")
    uploaded = st.file_uploader("Zdjęcie produktu", type=["jpg","jpeg","png","webp"], label_visibility="collapsed")

    existing_photo = ""
    if is_edit and ed.get("photo"):
        existing_photo = ed["photo"]
        try:
            st.image(base64.b64decode(existing_photo), width=200, caption="Aktualne zdjęcie")
        except: pass
        if st.checkbox("🗑️ Usuń zdjęcie"):
            existing_photo = ""

    st.markdown("")
    cs, cc = st.columns([2,1])
    with cs:
        save_clicked = st.button(
            "💾 Zapisz zmiany" if is_edit else "💾 Dodaj wpis",
            use_container_width=True, type="primary")
    with cc:
        if is_edit and st.button("Anuluj", use_container_width=True):
            st.session_state.editing = None
            st.session_state.tab = "lista"
            st.rerun()

    if save_clicked:
        if not product.strip():
            st.error("⚠️ Podaj nazwę produktu!")
        else:
            photo_b64 = img_to_b64(uploaded) if uploaded else existing_photo

            sale = {
                "id": ed.get("id") if is_edit else str(uuid.uuid4())[:8],
                "product": product.strip(),
                "qty": qty,
                "unit_price": unit_price,
                "total_cost": total_cost,
                "sale_price": sale_price,
                "total_sale": total_sale,
                "profit": profit,
                "created": ed.get("created") if is_edit else date.today().strftime("%d.%m.%Y"),
                "photo": photo_b64,
            }

            with st.spinner("Zapisywanie..."):
                if is_edit:
                    update_sale(sale)
                else:
                    append_sale(sale)
                st.session_state.sales = load_sales()

            st.success("✅ Zapisano!")
            st.session_state.editing = None
            st.session_state.tab = "lista"
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# PODSUMOWANIE
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.tab == "stats":

    def fsum(key):
        return sum(float(s.get(key,0) or 0) for s in sales)

    total_cost_all  = fsum("total_cost")
    total_sale_all  = fsum("total_sale")
    total_profit    = fsum("profit")
    total_qty       = sum(int(s.get("qty",0) or 0) for s in sales)

    # Górne statsy
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#2563eb">{len(sales)}</div><div class="stat-label">📋 Wpisów sprzedaży</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#7c3aed">{total_qty}</div><div class="stat-label">📦 Łącznie sztuk</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Finansowe
    profit_color_fin = "#16a34a" if total_profit >= 0 else "#ef4444"
    st.markdown(f"""
    <div class="fin-box">
        <div class="fin-label">🛒 Łączna sprzedaż</div>
        <div class="fin-val" style="color:#2563eb">{total_sale_all:.2f} zł</div>
    </div>
    <div class="fin-box">
        <div class="fin-label">📦 Łączny koszt zakupu</div>
        <div class="fin-val" style="color:#ea580c">{total_cost_all:.2f} zł</div>
    </div>
    <div class="fin-box">
        <div class="fin-label">💰 Łączny zysk</div>
        <div class="fin-val" style="color:{profit_color_fin}">{total_profit:.2f} zł</div>
    </div>
    """, unsafe_allow_html=True)

    # Marża
    if total_sale_all > 0:
        marza = (total_profit / total_sale_all) * 100
        st.markdown(f"""
        <div class="fin-box">
            <div class="fin-label">📈 Marża</div>
            <div class="fin-val" style="color:{'#16a34a' if marza>=0 else '#ef4444'}">{marza:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # TOP produkty
    if sales:
        st.markdown("#### 🏆 Top produkty wg zysku")
        sorted_sales = sorted(sales, key=lambda x: float(x.get("profit",0) or 0), reverse=True)
        for i, s in enumerate(sorted_sales[:5], 1):
            p = float(s.get("profit",0) or 0)
            color = "#16a34a" if p >= 0 else "#ef4444"
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:10px 14px;background:white;border-radius:10px;margin-bottom:6px;
                        box-shadow:0 1px 6px rgba(0,0,0,0.05)">
                <span style="font-weight:800;font-size:14px">#{i} {s.get('product','—')}</span>
                <span style="font-weight:900;font-size:15px;color:{color}">{p:.2f} zł</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### ⚠️ Strefa niebezpieczna")
    if st.button("🗑️ Usuń wszystkie wpisy", use_container_width=True):
        if st.session_state.get("confirm_del_all"):
            with st.spinner("Usuwanie..."):
                delete_all()
                st.session_state.sales = load_sales()
                st.session_state.confirm_del_all = False
            st.success("Usunięto!")
            st.rerun()
        else:
            st.session_state.confirm_del_all = True
            st.warning("⚠️ Kliknij jeszcze raz żeby potwierdzić!")
