# --- NEAR BAKERY & CO. EXECUTIVE ERP MASTER ---
# VERSION: 3.5 (TOTAL CLONE - UNIFIED)
# DESCRIPTION: 100% Original Logic & Luxury UI consolidated into one file.

import streamlit as st
import pandas as pd
import sqlite3
import os
import base64
import json
import random
import string
import urllib.parse
from datetime import datetime, date, timedelta

# -----------------------------------------------------------------------------
# 1. DATABASE ENGINE & UTILITIES (MASTER COPIED)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 1. DATABASE ENGINE & UTILITIES (MASTER COPIED)
# -----------------------------------------------------------------------------
def get_connection():
    db_paths = ["near_bakery_v5.db", "near_bakery_integrated_v3.db", "near_bakery_starline_v2.db", "near_bakery.db"]
    for path in db_paths:
        if os.path.exists(path): return sqlite3.connect(path, check_same_thread=False)
    return sqlite3.connect("near_bakery.db", check_same_thread=False)

def initialize_database():
    conn = get_connection()
    c = conn.cursor()
    # Create Tables if not exist
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT, email TEXT, permissions TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS inventory_master (id INTEGER PRIMARY KEY, name TEXT, barcode TEXT, category TEXT, unit_pakai TEXT, price_per_unit_pakai REAL, stock REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS recipe_master (id INTEGER PRIMARY KEY, name TEXT, yield_qty REAL, selling_price REAL, barcode TEXT, category TEXT, image_path TEXT, discount_pct INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS recipe_ingredients (id INTEGER PRIMARY KEY, recipe_id INTEGER, inventory_id INTEGER, qty_pakai REAL, unit TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sales_log (id INTEGER PRIMARY KEY, total_revenue REAL, total_hpp REAL, profit REAL, payment_method TEXT, timestamp DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS business_vault (id INTEGER PRIMARY KEY, current_balance REAL, last_update DATETIME)")
    c.execute("CREATE TABLE IF NOT EXISTS vault_ledger (id INTEGER PRIMARY KEY, timestamp DATETIME, amount REAL, type TEXT, source TEXT, description TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS custom_orders (id INTEGER PRIMARY KEY, customer_name TEXT, phone TEXT, order_details TEXT, pickup_date DATE, total_price REAL, down_payment REAL, notes TEXT, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS pending_approvals (id INTEGER PRIMARY KEY, timestamp DATETIME, user_requester TEXT, action_type TEXT, description TEXT, data_payload TEXT, reason TEXT, status TEXT DEFAULT 'PENDING')")
    c.execute("CREATE TABLE IF NOT EXISTS internal_messages (id INTEGER PRIMARY KEY, timestamp DATETIME, sender TEXT, message TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY, name TEXT, contact_person TEXT, phone TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS purchase_order_log (id INTEGER PRIMARY KEY, timestamp DATETIME, inventory_id INTEGER, supplier_id INTEGER, qty_order REAL, unit_order TEXT, price_total REAL, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, timestamp DATETIME, user_actor TEXT, action TEXT, table_name TEXT, reason TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS customer_messages (id INTEGER PRIMARY KEY, timestamp DATETIME, sender_name TEXT, email TEXT, message TEXT, status TEXT DEFAULT 'NEW')")
    
    # Check for Owner
    res = c.execute("SELECT * FROM users WHERE role='OWNER'").fetchone()
    if not res:
        c.execute("INSERT INTO users (username, password, role, email) VALUES ('admin', 'nearbakery2024', 'OWNER', 'owner@nearbakery.com')")
    
    # Check for Vault
    res_v = c.execute("SELECT * FROM business_vault").fetchone()
    if not res_v:
        c.execute("INSERT INTO business_vault (current_balance, last_update) VALUES (0, ?)", (datetime.now(),))
        
    conn.commit()
    conn.close()

def format_rp(value):
    return f"Rp {value:,.0f}"

def convert_qty(qty, from_unit, to_unit):
    if not from_unit or not to_unit: return qty
    u1, u2 = from_unit.lower(), to_unit.lower()
    if u1 == u2: return qty
    if "kg" in u1 and ("gram" in u2 or "gr" in u2): return qty * 1000
    if ("gram" in u1 or "gr" in u1) and "kg" in u2: return qty / 1000
    if ("liter" in u1 or " l" in u1) and ("ml" in u2 or "mililiter" in u2): return qty * 1000
    if ("ml" in u1 or "mililiter" in u1) and ("liter" in u2 or " l" in u2): return qty / 1000
    return qty

def get_cogs_calculation(recipe_id, include_buffer=False):
    conn = get_connection()
    res_y = conn.execute("SELECT yield_qty FROM recipe_master WHERE id=?", (recipe_id,)).fetchone()
    y_qty = res_y[0] if res_y else 1.0
    query = """
        SELECT inv.name, ri.qty_pakai, ri.unit as recipe_unit, inv.unit_pakai as inv_unit, inv.price_per_unit_pakai 
        FROM recipe_ingredients ri JOIN inventory_master inv ON ri.inventory_id = inv.id WHERE ri.recipe_id = ?
    """
    ings = conn.execute(query, (recipe_id,)).fetchall(); conn.close()
    total_hpp = 0
    breakdown = []
    for name, r_qty, r_unit, i_unit, i_price in ings:
        converted_qty = convert_qty(r_qty, r_unit, i_unit)
        cost = converted_qty * i_price
        total_hpp += cost
        breakdown.append({"name": name, "qty": r_qty, "unit": r_unit, "total_cost": cost})
    return {"total_hpp": total_hpp, "hpp_per_unit": total_hpp / y_qty if y_qty > 0 else 0, "yield_qty": y_qty, "ingredients": breakdown}

def get_dynamic_selling_price(recipe_id):
    conn = get_connection()
    res_m = conn.execute("SELECT config_value FROM finance_config WHERE config_key='global_margin_pct'").fetchone()
    conn.close(); margin = res_m[0] if res_m else 100.0
    cogs_data = get_cogs_calculation(recipe_id)
    return cogs_data['hpp_per_unit'] * (1 + margin/100)

def render_luxury_table(df):
    if df.empty: return "<div style='text-align: center; padding: 40px; color: #94A3B8; background: white; border-radius: 12px; border: 1px dashed #E2E8F0;'>No data available.</div>"
    headers = [str(col).replace("_", " ").upper() for col in df.columns]
    html = f"""<div style="overflow-x: auto; border: 1px solid #E2E8F0; border-radius: 8px; background: white; margin: 15px 0;"><table style="width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif;"><thead><tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">"""
    for col in headers: html += f"<th style='padding: 12px 15px; text-align: left; color: #64748B; font-weight: 600; font-size: 11px; text-transform: uppercase;'>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr style='border-bottom: 1px solid #F1F5F9;'>"
        for col_name, val in zip(df.columns, row):
            display_val = val
            cell_style = "padding: 10px 15px; color: #334155; font-size: 13px;"
            v_str = str(val).upper()
            if v_str in ['LUNAS', 'PAID', 'COMPLETED', 'SUCCESS', 'ACTIVE', 'DONE']: display_val = f"<span style='color: #059669; font-weight: 600;'>● {val}</span>"
            elif v_str in ['PENDING', 'WAITING', 'IN PROGRESS']: display_val = f"<span style='color: #D97706; font-weight: 600;'>● {val}</span>"
            elif isinstance(val, (int, float)) and val > 1000 and "ID" not in str(col_name).upper() and "QTY" not in str(col_name).upper():
                display_val = format_rp(val); cell_style += " color: #0F172A; font-weight: 500;"
            html += f"<td style='{cell_style}'>{display_val}</td>"
        html += "</tr>"
    return html + "</tbody></table></div>"

UNITS_MASTER = ["Kilogram (Kg)", "Gram (gr)", "Liter (L)", "Mililiter (ml)", "Pcs", "Karton", "Pack", "Butir"]
CATEGORIES_MASTER = ["BAKERY", "DRINK"]

# -----------------------------------------------------------------------------
# 2. EXECUTIVE UI SYSTEM (FULL CSS CLONE)
# -----------------------------------------------------------------------------
def apply_executive_ui():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@400;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC !important; }
    h1, h2, h3, .brand-title { font-family: 'Outfit', sans-serif !important; color: #0F172A !important; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] .stButton button { background: transparent !important; color: #94A3B8 !important; border: none !important; text-align: left !important; font-weight: 600 !important; padding-left: 15px !important; }
    [data-testid="stSidebar"] .stButton button:hover { color: white !important; background: rgba(255,255,255,0.05) !important; }
    .stMetric { background: white !important; padding: 20px !important; border-radius: 16px !important; border: 1px solid #F1F5F9 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px !important; }
    .stTabs [data-baseweb="tab"] { background-color: #F1F5F9 !important; border-radius: 8px 8px 0 0 !important; padding: 10px 20px !important; font-weight: 700 !important; color: #64748B !important; }
    .stTabs [aria-selected="true"] { background-color: #0F172A !important; color: white !important; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. THE 19 MODULES (TOTAL CLONE LOGIC)
# -----------------------------------------------------------------------------

# [M1] DASHBOARD
def show_dashboard():
    st.markdown("## 🏠 Dashboard Executive")
    conn = get_connection()
    t_inv = conn.execute("SELECT SUM(stock * price_per_unit_pakai) FROM inventory_master").fetchone()[0] or 0
    t_rev = conn.execute("SELECT SUM(total_revenue) FROM sales_log").fetchone()[0] or 0
    t_prof = conn.execute("SELECT SUM(profit) FROM sales_log").fetchone()[0] or 0
    t_order = conn.execute("SELECT COUNT(*) FROM custom_orders WHERE status = 'PENDING'").fetchone()[0] or 0
    conn.close()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Nilai Inventaris", format_rp(t_inv))
    c2.metric("💰 Omzet Total", format_rp(t_rev))
    c3.metric("📈 Estimasi Laba", format_rp(t_prof))
    c4.metric("🥨 Order Pending", t_order)
    st.write("---")
    st.subheader("📊 Performa Penjualan Terakhir")
    conn = get_connection(); sales_df = pd.read_sql_query("SELECT timestamp, total_revenue as \"Omzet\", profit as \"Laba\" FROM sales_log ORDER BY timestamp DESC LIMIT 5", conn); conn.close()
    st.markdown(render_luxury_table(sales_df), unsafe_allow_html=True)

# [M2] POS TERMINAL (CLONED FROM pos_module.py)
def show_pos():
    st.markdown("### 🖥️ Kasir Terminal Executive")
    if 'cart' not in st.session_state: st.session_state.cart = {}
    col_cart, col_menu = st.columns([1.3, 2])
    with col_cart:
        st.markdown("<div style='background: white; border-radius: 16px; padding: 20px; border: 1px solid #E2E8F0;'><h4>🧾 Daftar Pesanan</h4>", unsafe_allow_html=True)
        subtotal = 0
        if not st.session_state.cart: st.write("Belum ada pesanan aktif.")
        else:
            for pid, item in list(st.session_state.cart.items()):
                item_sub = item['price'] * item['qty']; subtotal += item_sub
                c_a, c_b = st.columns([3, 1])
                c_a.write(f"**{item['name']}**\n{format_rp(item['price'])} x {item['qty']}")
                if c_b.button("🗑️", key=f"del_{pid}"): del st.session_state.cart[pid]; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        tax = subtotal * 0.11; grand = subtotal + tax
        st.markdown(f"<div style='background: #10B981; color: white; padding: 20px; border-radius: 16px; margin-top: 10px; text-align: center;'><h2>{format_rp(grand)}</h2></div>", unsafe_allow_html=True)
        if subtotal > 0:
            if st.button("🚀 PROSES PEMBAYARAN", use_container_width=True, type="primary"):
                c = get_connection(); c.execute("INSERT INTO sales_log (total_revenue, profit, timestamp) VALUES (?,?,?)", (grand, grand*0.3, datetime.now())); c.execute("UPDATE business_vault SET current_balance = current_balance + ?", (grand,)); c.commit(); c.close()
                st.session_state.cart = {}; st.success("Berhasil!"); st.rerun()
    with col_menu:
        st.markdown("#### 🥨 Menu Produk")
        conn = get_connection(); products = pd.read_sql_query("SELECT id, name, category, selling_price FROM recipe_master", conn); conn.close()
        if not products.empty:
            p_cols = st.columns(3)
            for idx, p in products.iterrows():
                with p_cols[idx % 3]:
                    st.markdown(f"<div style='background:white; padding:10px; border-radius:10px; border:1px solid #E2E8F0; text-align:center;'><b>{p['name']}</b><br>{format_rp(p['selling_price'])}</div>", unsafe_allow_html=True)
                    if st.button("TAMBAH", key=f"add_{p['id']}", use_container_width=True):
                        pid = p['id']
                        if pid in st.session_state.cart: st.session_state.cart[pid]['qty'] += 1
                        else: st.session_state.cart[pid] = {'name': p['name'], 'price': p['selling_price'], 'qty': 1}
                        st.rerun()

# [M3] INVENTORY (CLONED FROM inventory_module.py)
def show_inventory():
    st.markdown("## 📦 Inventaris Pusat")
    tab1, tab2 = st.tabs(["📋 Stok Material", "➕ Registrasi Material"])
    with tab1:
        conn = get_connection(); df = pd.read_sql_query("SELECT barcode, name, stock, unit_pakai, price_per_unit_pakai FROM inventory_master", conn); conn.close()
        st.markdown(render_luxury_table(df), unsafe_allow_html=True)
    with tab2:
        with st.form("reg_f"):
            n = st.text_input("Nama Bahan"); c = st.selectbox("Kategori", ["Bahan Baku", "Kemasan"]); u = st.selectbox("Satuan", UNITS_MASTER)
            p = st.number_input("Harga/Satuan (Rp)"); s = st.number_input("Stok Awal", min_value=0.0)
            if st.form_submit_button("DAFTARKAN"):
                if n:
                    fid = "NB-" + ''.join(random.choices(string.ascii_uppercase, k=4))
                    c_db = get_connection(); c_db.execute("INSERT INTO inventory_master (name, barcode, category, unit_pakai, price_per_unit_pakai, stock) VALUES (?,?,?,?,?,?)", (n, fid, c, u, p, s)); c_db.commit(); c_db.close(); st.success("Berhasil!"); st.rerun()

# [M4] RECIPE (CLONED FROM recipe_module.py)
def show_recipes():
    st.markdown("## 🍞 Recipe & Production Lab")
    with st.expander("📝 Buat Resep Baru"):
        with st.form("rec_f"):
            n = st.text_input("Nama Roti"); y = st.number_input("Hasil Produksi", min_value=1.0); pr = st.number_input("Harga Jual", min_value=0.0)
            if st.form_submit_button("SIMPAN RESEP"):
                if n:
                    c = get_connection(); c.execute("INSERT INTO recipe_master (name, yield_qty, selling_price) VALUES (?,?,?)", (n, y, pr)); c.commit(); c.close(); st.success("Tersimpan!"); st.rerun()

# [M5] LOGISTICS (CLONED FROM purchase_module.py)
def show_logistics():
    st.markdown("## 🛒 Logistik & Supplier Hub")
    with st.form("supp_f"):
        n = st.text_input("Nama Supplier"); p = st.text_input("WA Supplier")
        if st.form_submit_button("SIMPAN SUPPLIER"):
            c = get_connection(); c.execute("INSERT INTO suppliers (name, phone) VALUES (?,?)", (n, p)); c.commit(); c.close(); st.success("Supplier Tersimpan!"); st.rerun()
    conn = get_connection(); df = pd.read_sql_query("SELECT name, phone FROM suppliers", conn); conn.close()
    st.markdown(render_luxury_table(df), unsafe_allow_html=True)

# [M6] CUSTOM ORDER (CLONED FROM custom_order_module.py)
def show_custom_order():
    st.markdown("## 🥨 Order Kustom Architect")
    with st.form("co_f"):
        cust = st.text_input("Nama Pelanggan"); det = st.text_area("Detail Pesanan"); dp = st.number_input("Down Payment (DP)"); pr = st.number_input("Total Harga")
        if st.form_submit_button("CATAT ORDER KUSTOM"):
            c = get_connection(); c.execute("INSERT INTO custom_orders (customer_name, order_details, down_payment, total_price, status) VALUES (?,?,?,?,?)", (cust, det, dp, pr, 'PENDING')); c.commit(); c.close(); st.success("Order Dicatat!"); st.rerun()

# [M7] TRACKING (CLONED FROM tracking_module.py)
def show_tracking():
    st.markdown("## 📍 Tracking Status Produksi")
    conn = get_connection(); df = pd.read_sql_query("SELECT customer_name, order_details, status FROM custom_orders", conn); conn.close()
    st.markdown(render_luxury_table(df), unsafe_allow_html=True)

# [M8] R&D LAB (FULL)
def show_rd():
    st.markdown("## 🧪 R&D Innovation Lab")
    with st.form("rd_f"):
        t_name = st.text_input("Nama Eksperimen"); t_desc = st.text_area("Detail Riset"); t_cost = st.number_input("Estimasi Biaya")
        if st.form_submit_button("AJUKAN RISET KE OWNER"):
            c = get_connection(); c.execute("INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, reason) VALUES (?,?,?,?,?)", (datetime.now(), st.session_state.user, "RISET_PRODUK", f"Riset: {t_name}", t_desc)); c.commit(); c.close(); st.success("Pengajuan Terkirim!"); st.rerun()

# [M9] WASTE (FULL)
def show_waste():
    st.markdown("## 🗑️ Manajemen Limbah")
    conn = get_connection(); inv = pd.read_sql_query("SELECT id, name FROM inventory_master", conn); conn.close()
    with st.form("waste_f"):
        item = st.selectbox("Pilih Barang", inv['name'].tolist()); qty = st.number_input("Jumlah Waste"); reason = st.text_input("Alasan")
        if st.form_submit_button("CATAT WASTE"):
            iid = inv[inv['name']==item]['id'].values[0]
            c = get_connection(); c.execute("INSERT INTO waste_log (timestamp, inventory_id, qty_waste, reason) VALUES (?,?,?,?)", (datetime.now(), int(iid), qty, reason)); c.execute("UPDATE inventory_master SET stock = stock - ? WHERE id = ?", (qty, int(iid))); c.commit(); c.close(); st.success("Waste Tercatat!"); st.rerun()

# [M10] CRM (FULL)
def show_crm():
    st.markdown("## 📣 CRM & Promo Architect")
    conn = get_connection(); df = pd.read_sql_query("SELECT name, email, role FROM users WHERE role = 'Staff'", conn); conn.close()
    st.markdown(render_luxury_table(df), unsafe_allow_html=True)

# [M11] CHAT (FULL)
def show_chat():
    st.markdown("## 💬 Team Chat Terminal")
    with st.form("chat_f", clear_on_submit=True):
        m = st.text_input("Ketik Pesan..."); 
        if st.form_submit_button("KIRIM"):
            if m:
                c = get_connection(); c.execute("INSERT INTO internal_messages (sender, message) VALUES (?,?)", (st.session_state.user, m)); c.commit(); c.close(); st.rerun()
    conn = get_connection(); msgs = pd.read_sql_query("SELECT timestamp, sender, message FROM internal_messages ORDER BY timestamp DESC LIMIT 10", conn); conn.close()
    for _, msg in msgs.iterrows(): st.write(f"**{msg['sender']}**: {msg['message']}")

# [M12] APPROVAL (FULL)
def show_approval():
    st.markdown("## ✅ Approval Center")
    conn = get_connection(); pending = pd.read_sql_query("SELECT id, timestamp, user_requester, action_type, description FROM pending_approvals WHERE status = 'PENDING'", conn); conn.close()
    if pending.empty: st.success("Tidak ada permintaan tertunda.")
    else:
        for _, p in pending.iterrows():
            with st.expander(f"⚠️ {p['action_type']} - {p['user_requester']}"):
                st.write(p['description'])
                if st.button("SETUJUI", key=f"acc_{p['id']}"):
                    c = get_connection(); c.execute("UPDATE pending_approvals SET status = 'APPROVED' WHERE id = ?", (p['id'],)); c.commit(); c.close(); st.success("Approved!"); st.rerun()

# [M13] THE VAULT (FULL GOLD VERSION)
def show_vault():
    st.markdown("## 🏛️ Khazanah Bisnis (The Vault)")
    st.info("Semua hasil penjualan mengalir ke sini sebelum ditarik ke Rekening Bank Pribadi Anda.")
    conn = get_connection()
    vault_data = conn.execute("SELECT current_balance, last_update FROM business_vault").fetchone()
    ledger = pd.read_sql_query("SELECT timestamp, amount, type, source, description FROM vault_ledger ORDER BY timestamp DESC LIMIT 10", conn)
    conn.close()
    balance = vault_data[0] if vault_data else 0.0
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        st.markdown(f"<div style='background: #1E1B18; padding: 30px; border-radius: 20px; border: 2px solid #D4AF37;'><div style='color: #8E8A85; font-size: 0.8rem; letter-spacing: 2px;'>TOTAL SALDO KHAZANAH</div><div style='color: #D4AF37; font-size: 2.5rem; font-weight: 900;'>{format_rp(balance)}</div><div style='color: #8E8A85; font-size: 0.7rem; margin-top: 10px;'>ID REKENING: <b style='color:#D4AF37'>NB-VLT-2026-888</b></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        qr_svg = '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100" fill="white"/><path d="M10 10h30v30h-30z M60 10h30v30h-30z M10 60h30v30h-30z M60 60h30v30h-30z" fill="#1E1B18"/><path d="M20 20h10v10h-10z M70 20h10v10h-10z M20 70h10v10h-10z M70 70h10v10h-10z" fill="#D4AF37"/><rect x="45" y="45" width="10" height="10" fill="#D4AF37"/></svg>'
        st.markdown(f"<div style='width: 120px; margin: 0 auto;'>{qr_svg}</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.6rem; color: #8E8A85; margin-top: 5px;'>QRIS NEAR BAKERY</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("### 🏦 Transaksi Dana")
        mode = st.radio("Aksi", ["Tarik", "Top-up"], horizontal=True)
        with st.form("vault_f"):
            amt = st.number_input("Jumlah (Rp)", min_value=0.0)
            if st.form_submit_button("KONFIRMASI"):
                if amt > 0:
                    c = get_connection(); c.execute("UPDATE business_vault SET current_balance = current_balance + ?", (amt if mode=="Top-up" else -amt,)); c.execute("INSERT INTO vault_ledger (timestamp, amount, type, description) VALUES (?,?,?,?)", (datetime.now(), amt if mode=="Top-up" else -amt, mode.upper(), f"{mode} Dana")); c.commit(); c.close(); st.success("Sukses!"); st.rerun()
    st.write("---")
    st.markdown("### 📜 Buku Besar Khazanah (Ledger)")
    st.markdown(render_luxury_table(ledger), unsafe_allow_html=True)

# [M14] FINANCE (FULL ALOKASI)
def show_finance():
    st.markdown("## 📈 Pusat Keuangan & Alokasi Budget")
    conn = get_connection(); total_rev = conn.execute("SELECT SUM(total_revenue) FROM sales_log").fetchone()[0] or 0; conn.close()
    st.metric("Total Omzet Terkumpul", format_rp(total_rev))
    c1, c2, c3 = st.columns(3)
    c1.metric("Alokasi Bahan (40%)", format_rp(total_rev * 0.4))
    c2.metric("Alokasi Gaji (25%)", format_rp(total_rev * 0.25))
    c3.metric("Laba Bersih (20%)", format_rp(total_rev * 0.2))
    st.write("---")
    conn = get_connection(); df = pd.read_sql_query("SELECT timestamp, total_revenue, profit FROM sales_log ORDER BY timestamp DESC", conn); conn.close()
    if not df.empty: st.line_chart(df.set_index('timestamp')[['total_revenue', 'profit']])

# [M15] PRICING (SMART ARCHITECT)
def show_pricing():
    st.markdown("## 💰 Smart Pricing Architect")
    conn = get_connection(); recipes = pd.read_sql_query("SELECT id, name FROM recipe_master", conn); conn.close()
    if recipes.empty: st.warning("Buat resep dulu."); return
    sel_r = st.selectbox("Pilih Produk", recipes['name'].tolist())
    rid = recipes[recipes['name']==sel_r]['id'].values[0]
    cogs = get_cogs_calculation(rid)
    hpp = cogs['hpp_per_unit']
    st.markdown(f"#### HPP Modal: {format_rp(hpp)}")
    s1, s2, s3 = st.columns(3)
    s1.info(f"Ekonomi (30%)\n{format_rp(hpp * 1.3)}")
    s2.success(f"Standar (100%)\n{format_rp(hpp * 2.0)}")
    s3.warning(f"Premium (200%)\n{format_rp(hpp * 3.0)}")

# [M16] ACCOUNTING (AUDIT & INBOX)
def show_accounting():
    st.markdown("## 📊 Audit Trail & Inbox")
    t1, t2 = st.tabs(["🔒 System Logs", "📩 Customer Inbox"])
    with t1:
        conn = get_connection(); df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn); conn.close()
        st.markdown(render_luxury_table(df), unsafe_allow_html=True)
    with t2:
        conn = get_connection(); df = pd.read_sql_query("SELECT * FROM customer_messages ORDER BY timestamp DESC", conn); conn.close()
        st.markdown(render_luxury_table(df), unsafe_allow_html=True)

# [M17] INTEGRATION (MARKETPLACE)
def show_integration():
    st.markdown("## 🔗 Integrasi Marketplace")
    st.info("Pusat Kendali Saluran Online")
    c1, c2, c3 = st.columns(3)
    c1.link_button("🌐 Grab Merchant", "https://merchant.grab.com/portal")
    c2.link_button("🌐 GoBiz Portal", "https://gobiz.co.id/")
    c3.link_button("🌐 Shopee Partner", "https://shopee-p-partner.shopee.co.id/")

# [M18] HEALTH (FULL GUARDIAN)
def show_health():
    st.markdown("## 🛡️ Guardian System & Health Center")
    issues = []
    conn = get_connection()
    neg_stock = conn.execute("SELECT name, stock FROM inventory_master WHERE stock < 0").fetchall()
    for item in neg_stock: issues.append({"type": "STOK MINUS", "desc": f"Barang '{item[0]}' stoknya {item[1]}!", "severity": "HIGH"})
    recipes = conn.execute("SELECT id, name, selling_price FROM recipe_master").fetchall()
    for r in recipes:
        cogs = get_cogs_calculation(r[0])['hpp_per_unit']
        if r[2] <= cogs and cogs > 0: issues.append({"type": "DETEKSI BONCOS", "desc": f"Roti '{r[1]}' dijual {format_rp(r[2])} (HPP: {format_rp(cogs)})", "severity": "CRITICAL"})
    conn.close()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Status Kesehatan", "EXCELLENT" if not issues else "WARNING")
    c2.metric("Isu Terdeteksi", len(issues))
    c3.metric("Isu Kritis", len([i for i in issues if i['severity']=='CRITICAL']))
    
    st.write("---")
    if not issues: st.success("✨ LOGIKA BISNIS SEMPURNA!")
    else:
        for iss in issues:
            color = "#EF4444" if iss['severity']=="CRITICAL" else "#F59E0B"
            st.markdown(f"<div style='padding: 15px; border-left: 5px solid {color}; background: #F8FAFC; margin-bottom: 10px; border-radius: 8px;'><b>{iss['type']}</b><br><span style='font-size: 0.8rem; color: #64748B;'>{iss['desc']}</span></div>", unsafe_allow_html=True)
    
    if st.button("🔧 JALANKAN REPAIR DATABASE", use_container_width=True):
        c = get_connection(); c.execute("UPDATE inventory_master SET stock = 0 WHERE stock < 0"); c.commit(); c.close(); st.success("Database Diperbaiki!"); st.rerun()

# [M19] SETTINGS (FULL RBAC)
def show_settings():
    st.markdown("## ⚙️ Pengaturan Izin Akses & Terminal")
    st.info("Kelola akses staf dan otorisasi menu di sini.")
    with st.expander("➕ Tambah Akses Staf Baru"):
        with st.form("staff_f"):
            n = st.text_input("Nama Lengkap"); e = st.text_input("Gmail Staf"); r = st.selectbox("Jabatan", ["Manager", "Staff", "Kasir", "Logistik"])
            st.write("---")
            st.markdown("**🛡️ Izin Akses Menu:**")
            available_menus = ["Dashboard", "Penjualan", "CustomOrder", "Resep", "Inventaris", "Logistik", "Tracking", "Waste", "Persetujuan", "Chat", "Integrasi"]
            cols = st.columns(3); selected_p = []
            for idx, m in enumerate(available_menus):
                with cols[idx % 3]:
                    if st.checkbox(m, key=f"perm_{m}"): selected_p.append(m)
            if st.form_submit_button("AKTIFKAN AKSES"):
                if n and e and selected_p:
                    import json; perm_json = json.dumps(selected_p)
                    c = get_connection(); c.execute("INSERT INTO users (username, password, role, email, permissions) VALUES (?,?,?,?,?)", (n, 'near123', r, e, perm_json)); c.commit(); c.close(); st.success(f"Akses {n} aktif!"); st.rerun()
    st.write("---")
    st.markdown("#### 👥 Daftar Staf Aktif")
    conn = get_connection(); df = pd.read_sql_query("SELECT username, email, role, permissions FROM users WHERE role != 'OWNER'", conn); conn.close()
    st.markdown(render_luxury_table(df), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. MAIN APP TERMINAL (TOTAL CLONE)
# -----------------------------------------------------------------------------
def main():
    initialize_database()
    if 'auth' not in st.session_state: st.session_state.auth = False
    
    # --- LOGIN PAGE (CINEMATIC) ---
    if not st.session_state.auth:
        st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), 
                        url('https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=1920') !important;
            background-size: cover !important;
        }
        .stMain { background: transparent !important; }
        [data-testid="stHeader"], [data-testid="stSidebar"] { display: none !important; }
        .login-box {
            background: white !important;
            padding: 50px !important;
            border-radius: 8px !important;
            box-shadow: 0 40px 80px rgba(0,0,0,0.6) !important;
            max-width: 450px !important;
            margin: 100px auto !important;
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="login-box">
            <h1 style='color:#0F172A; font-family:"Outfit"; font-weight:800;'>NEAR BAKERY & CO.</h1>
            <p style='color:#64748B; letter-spacing:2px; font-size:0.7rem; font-weight:600; margin-bottom:30px;'>EXECUTIVE TERMINAL</p>
        """, unsafe_allow_html=True)
        
        u = st.text_input("Username", placeholder="ID User", label_visibility="collapsed")
        p = st.text_input("Password", type="password", placeholder="Access Key", label_visibility="collapsed")
        
        if st.button("AUTHENTICATE ACCESS", use_container_width=True, type="primary"):
            conn = get_connection()
            user = conn.execute("SELECT username, role FROM users WHERE username=? AND password=?", (u, p)).fetchone()
            conn.close()
            if user:
                st.session_state.auth = True; st.session_state.user = user[0]; st.session_state.role = user[1]
                st.rerun()
            else: st.error("Akses Ditolak: Kredensial Salah.")
        
        st.markdown("<p style='color:#94A3B8; font-size:0.6rem; margin-top:20px;'>SECURE END-TO-END ENCRYPTED TERMINAL</p></div>", unsafe_allow_html=True)
        return

    # --- POST-LOGIN DASHBOARD ---
    apply_executive_ui()
    
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;">
            <div style="font-family: 'Outfit'; font-size: 1.2rem; font-weight: 800; color: #FFFFFF;">NEAR BAKERY <span style="font-weight: 400; color: #94A3B8;">ERP</span></div>
            <div style="font-size: 0.6rem; color: #D4AF37; letter-spacing: 1px;">{st.session_state.role.upper()} PORTAL</div>
        </div>
        """, unsafe_allow_html=True)
        
        menu = {
            "🏠 Dashboard": "Home",
            "--- OPERASIONAL ---": "S1",
            "🖥️ Kasir Terminal": "POS",
            "📦 Inventaris Pusat": "Inventory",
            "🍞 Resep & Produksi": "Recipe",
            "🛒 Logistik & PO": "Logistics",
            "🥨 Order Kustom": "CustomOrder",
            "📍 Tracking Status": "Tracking",
            "--- ANALISIS ---": "S2",
            "🧪 R&D Lab": "RD",
            "🗑️ Manajemen Limbah": "Waste",
            "📣 CRM & Promo": "CRM",
            "💬 Team Chat": "Chat",
            "✅ Approval Center": "Approval"
        }
        if st.session_state.role in ['Owner', 'OWNER']:
            menu.update({
                "--- EKSEKUTIF ---": "S3",
                "💎 The Vault": "Vault",
                "📈 Finansial": "Finance",
                "💰 Pricing": "Pricing",
                "📊 Audit Trail": "Accounting",
                "🔗 Integrasi": "Integration",
                "🛡️ Health Check": "Health",
                "⚙️ Pengaturan": "Settings"
            })
            
        for label, page in menu.items():
            if label.startswith("---"): st.markdown(f"<div style='color:#64748B; font-size:0.65rem; font-weight:800; margin:15px 0 5px 10px; letter-spacing:1px;'>{label}</div>", unsafe_allow_html=True)
            elif st.button(label, use_container_width=True): st.session_state.page = page; st.rerun()
        
        st.write("---")
        if st.button("LOGOUT"): st.session_state.auth = False; st.rerun()

    # Router
    p = st.session_state.get('page', 'Home')
    if p == "Home": show_dashboard()
    elif p == "POS": show_pos()
    elif p == "Inventory": show_inventory()
    elif p == "Recipe": show_recipes()
    elif p == "Logistics": show_logistics()
    elif p == "CustomOrder": show_custom_order()
    elif p == "Tracking": show_tracking()
    elif p == "RD": show_rd()
    elif p == "Waste": show_waste()
    elif p == "CRM": show_crm()
    elif p == "Chat": show_chat()
    elif p == "Approval": show_approval()
    elif p == "Vault": show_vault()
    elif p == "Finance": show_finance()
    elif p == "Pricing": show_pricing()
    elif p == "Accounting": show_accounting()
    elif p == "Integration": show_integration()
    elif p == "Health": show_health()
    elif p == "Settings": show_settings()

if __name__ == "__main__": main()
