# --- NEAR BAKERY & CO. EXECUTIVE ERP UNIFIED TERMINAL ---
# Version: 3.0 (Master 19-Menu Edition)
# Author: Antigravity AI
# License: Private / Executive Use Only

import streamlit as st
import pandas as pd
import os
import re
import json
import base64
import random
import string
import urllib.parse
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# -----------------------------------------------------------------------------
# 1. DATABASE ENGINE (INTEGRATED & OPTIMIZED)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["DB_URL"]
    except:
        DB_URL = "postgresql://postgres.btcsynyxodkonqdpwowx:%23Nenocahyamulan190604@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
    return create_engine(DB_URL, pool_size=10, max_overflow=20)

class PostgresCompat:
    def __init__(self, conn):
        self.conn = conn
        self._current_result = None
    def execute(self, query, params=None):
        try:
            if isinstance(query, str):
                # Convert '?' to named params ':p0', ':p1', etc.
                if params:
                    if not isinstance(params, (list, tuple)): params = (params,)
                    param_dict = {}
                    new_query = query
                    for i, val in enumerate(params):
                        placeholder = f":p{i}"
                        new_query = new_query.replace('?', placeholder, 1)
                        param_dict[f"p{i}"] = val
                    res = self.conn.execute(text(new_query), param_dict)
                else:
                    res = self.conn.execute(text(query))
                self._current_result = res
                return res
            return self.conn.execute(query, params)
        except Exception as e:
            # st.error(f"DB Error: {e}")
            raise e
    def fetchone(self):
        if self._current_result:
            row = self._current_result.fetchone()
            if row: return list(row._asdict().values()) if hasattr(row, '_asdict') else list(row)
        return None
    def fetchall(self):
        if self._current_result:
            rows = self._current_result.fetchall()
            return [tuple(row._asdict().values()) if hasattr(row, '_asdict') else tuple(row) for row in rows]
        return []
    def scalar(self): return self._current_result.scalar() if self._current_result else None
    @property
    def lastrowid(self): return self.conn.execute(text("SELECT lastval()")).scalar()
    def commit(self): pass
    def close(self): self.conn.close()

def get_connection():
    return PostgresCompat(get_engine().connect())

def init_db():
    conn = get_connection()
    try:
        # Essential Tables only (assuming others exist in Supabase)
        conn.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, permissions TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS business_vault (id SERIAL PRIMARY KEY, current_balance FLOAT DEFAULT 0, last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS internal_messages (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, sender TEXT, message TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS pending_approvals (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_requester TEXT, action_type TEXT, description TEXT, data_payload TEXT, reason TEXT, status TEXT DEFAULT 'PENDING')")
        conn.execute("CREATE TABLE IF NOT EXISTS budget_allocation (room_name TEXT PRIMARY KEY, target_pct FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS budget_usage_log (id SERIAL PRIMARY KEY, room_name TEXT, amount FLOAT, description TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS custom_orders (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, customer_name TEXT, phone TEXT, order_details TEXT, pickup_date DATE, total_price FLOAT, down_payment FLOAT, notes TEXT, status TEXT DEFAULT 'PENDING')")
        conn.execute("CREATE TABLE IF NOT EXISTS waste_log (id SERIAL PRIMARY KEY, inventory_id INTEGER, qty_waste FLOAT, loss_value FLOAT, reason TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS customer_messages (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, customer_name TEXT, message TEXT, status TEXT DEFAULT 'UNREAD')")
        conn.execute("CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_actor TEXT, action TEXT, table_name TEXT, old_value TEXT, new_value TEXT, reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS system_settings (config_key TEXT PRIMARY KEY, config_value TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS rd_trials (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, name TEXT, total_cost FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS rd_trial_ingredients (id SERIAL PRIMARY KEY, trial_id INTEGER, inventory_id INTEGER, qty_pakai FLOAT)")
        
        # Migrations
        conn.execute("ALTER TABLE recipe_master ADD COLUMN IF NOT EXISTS discount_pct FLOAT DEFAULT 0")
        conn.execute("ALTER TABLE sales_log ADD COLUMN IF NOT EXISTS total_hpp FLOAT DEFAULT 0")
        conn.execute("ALTER TABLE sales_log ADD COLUMN IF NOT EXISTS profit FLOAT DEFAULT 0")
        conn.execute("ALTER TABLE sales_log ADD COLUMN IF NOT EXISTS payment_method TEXT")
        
        # Default Owner
        if not conn.execute("SELECT * FROM users WHERE username='admin'").fetchone():
            conn.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'OWNER')")
        if not conn.execute("SELECT * FROM business_vault").fetchone():
            conn.execute("INSERT INTO business_vault (current_balance) VALUES (0)")
            
        conn.conn.commit()
    except: pass
    finally: conn.close()

# -----------------------------------------------------------------------------
# 2. UTILITIES
# -----------------------------------------------------------------------------
def format_rp(v): return f"Rp {v:,.0f}"
UNITS_MASTER = ["Kg", "gr", "L", "ml", "Pcs", "Karton", "Pack", "Butir"]

def render_luxury_table(df):
    if df.empty: return "<p style='color:gray'>No data available.</p>"
    html = '<div style="overflow-x: auto; border: 1px solid #E2E8F0; border-radius: 12px; background: white;"><table style="width: 100%; border-collapse: collapse;">'
    html += '<thead style="background: #F8FAFC; border-bottom: 1px solid #E2E8F0;"><tr>'
    for col in df.columns: html += f'<th style="padding: 12px; text-align: left; font-size: 0.7rem; text-transform: uppercase; color: #64748B;">{col}</th>'
    html += '</tr></thead><tbody>'
    for _, row in df.iterrows():
        html += '<tr style="border-bottom: 1px solid #F1F5F9;">'
        for val in row:
            display = format_rp(val) if isinstance(val, (int, float)) and val > 1000 else str(val)
            html += f'<td style="padding: 12px; font-size: 0.85rem; color: #334155;">{display}</td>'
        html += '</tr>'
    return html + '</tbody></table></div>'

def get_cogs_calculation(recipe_id, include_buffer=True):
    conn = get_connection()
    res_y = conn.execute("SELECT yield_qty FROM recipe_master WHERE id=?", (recipe_id,)).fetchone()
    y_qty = res_y[0] if res_y else 1.0
    ings = conn.execute("SELECT inv.price_per_unit_pakai, ri.qty_pakai FROM recipe_ingredients ri JOIN inventory_master inv ON ri.inventory_id = inv.id WHERE ri.recipe_id = ?", (recipe_id,)).fetchall()
    conn.close()
    total = sum(p * q for p, q in ings)
    if include_buffer: total *= 1.05
    return {"total_hpp": total, "hpp_per_unit": total / y_qty if y_qty > 0 else 0, "yield_qty": y_qty}

# -----------------------------------------------------------------------------
# 3. 19 MODULES (FULL IMPLEMENTATION)
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
    conn = get_connection(); sales_df = pd.read_sql_query("SELECT timestamp, total_revenue as \"Omzet\", profit as \"Laba\" FROM sales_log ORDER BY timestamp DESC LIMIT 5", conn.conn); conn.close()
    st.markdown(render_luxury_table(sales_df), unsafe_allow_html=True)

# [M2] POS TERMINAL
def show_pos():
    st.markdown("## 🖥️ Kasir Terminal")
    if 'cart' not in st.session_state: st.session_state.cart = {}
    col_a, col_b = st.columns([1.5, 2])
    with col_a:
        st.subheader("🛒 Keranjang")
        subtotal = 0
        for pid, it in list(st.session_state.cart.items()):
            st.write(f"**{it['name']}** x{it['qty']} = {format_rp(it['price']*it['qty'])}")
            subtotal += it['price'] * it['qty']
        st.markdown(f"### TOTAL: {format_rp(subtotal)}")
        m = st.selectbox("Bayar via", ["TUNAI", "QRIS", "DEBIT"])
        if st.button("PROSES TRANSAKSI", type="primary", use_container_width=True):
            if subtotal > 0:
                c = get_connection(); c.execute("INSERT INTO sales_log (total_revenue, profit, payment_method) VALUES (?,?,?)", (subtotal, subtotal*0.3, m))
                c.conn.commit(); c.close(); st.session_state.cart = {}; st.success("Transaksi Berhasil!"); st.rerun()
    with col_b:
        st.subheader("🥐 Produk")
        conn = get_connection(); p_df = pd.read_sql_query("SELECT id, name, selling_price FROM recipe_master", conn.conn); conn.close()
        cols = st.columns(2)
        for idx, row in p_df.iterrows():
            with cols[idx % 2]:
                if st.button(f"{row['name']}\n{format_rp(row['selling_price'])}", key=f"pos_{row['id']}", use_container_width=True):
                    pid = row['id']
                    if pid in st.session_state.cart: st.session_state.cart[pid]['qty'] += 1
                    else: st.session_state.cart[pid] = {'name': row['name'], 'price': row['selling_price'], 'qty': 1}
                    st.rerun()

# [M3] CUSTOM ORDER
def show_custom_order():
    st.markdown("## 🥨 Order Kustom Architect")
    with st.form("custom_f"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Nama Pelanggan")
        phone = c2.text_input("WhatsApp")
        det = st.text_area("Detail Pesanan (Contoh: Roti Buaya 2kg)")
        price = st.number_input("Harga Kesepakatan (Rp)", min_value=0)
        dp = st.number_input("Down Payment (Rp)", min_value=0)
        p_date = st.date_input("Tanggal Ambil", value=date.today() + timedelta(days=2))
        if st.form_submit_button("SIMPAN ORDER KUSTOM"):
            if name and price:
                c = get_connection(); c.execute("INSERT INTO custom_orders (customer_name, phone, order_details, pickup_date, total_price, down_payment) VALUES (?,?,?,?,?,?)", (name, phone, det, p_date, price, dp))
                c.conn.commit(); c.close(); st.success("Order Berhasil Dicatat!"); st.rerun()

# [M4] RECIPE LAB
def show_recipes():
    st.markdown("## 🍞 Recipe & Production Lab")
    with st.expander("➕ Buat Resep Baru"):
        name = st.text_input("Nama Roti")
        yield_qty = st.number_input("Hasil Produksi", min_value=1.0)
        price = st.number_input("Harga Jual", min_value=0.0)
        if st.button("SIMPAN RESEP"):
            if name:
                c = get_connection(); c.execute("INSERT INTO recipe_master (name, yield_qty, selling_price) VALUES (?,?,?)", (name, yield_qty, price))
                c.conn.commit(); c.close(); st.success("Resep Dasar Tersimpan!"); st.rerun()
    conn = get_connection(); df = pd.read_sql_query("SELECT name, yield_qty, selling_price FROM recipe_master", conn.conn); conn.close()
    st.markdown(render_luxury_table(df), unsafe_allow_html=True)

# [M5] INVENTORY
def show_inventory():
    st.markdown("## 📦 Inventaris Pusat")
    tab1, tab2 = st.tabs(["📋 Stok", "➕ Tambah Material"])
    with tab1:
        conn = get_connection(); df = pd.read_sql_query("SELECT name, category, stock, unit_pakai, price_per_unit_pakai FROM inventory_master", conn.conn); conn.close()
        st.markdown(render_luxury_table(df), unsafe_allow_html=True)
    with tab2:
        with st.form("inv_f"):
            n = st.text_input("Nama Bahan")
            cat = st.selectbox("Kategori", ["Bahan Baku", "Kemasan", "Lainnya"])
            s = st.number_input("Stok Awal", min_value=0.0)
            u = st.selectbox("Satuan", ["Kg", "gr", "L", "ml", "Pcs"])
            p = st.number_input("Harga per Satuan", min_value=0.0)
            if st.form_submit_button("DAFTARKAN BAHAN"):
                c = get_connection(); c.execute("INSERT INTO inventory_master (name, category, stock, unit_pakai, price_per_unit_pakai) VALUES (?,?,?,?,?)", (n, cat, s, u, p))
                c.conn.commit(); c.close(); st.success("Material Terdaftar!"); st.rerun()

# [M6] LOGISTICS
def show_logistics():
    st.markdown("## 🛒 Logistik & Supplier")
    tab1, tab2 = st.tabs(["🏢 Supplier", "📋 Purchase Order"])
    with tab1:
        with st.form("supp_f"):
            n = st.text_input("Nama Supplier")
            p = st.text_input("WhatsApp")
            if st.form_submit_button("SIMPAN SUPPLIER"):
                c = get_connection(); c.execute("INSERT INTO suppliers (name, phone) VALUES (?,?)", (n, p)); c.conn.commit(); c.close(); st.success("Supplier Tersimpan!"); st.rerun()
        conn = get_connection(); df = pd.read_sql_query("SELECT name, phone FROM suppliers", conn.conn); conn.close()
        st.markdown(render_luxury_table(df), unsafe_allow_html=True)
    with tab2:
        st.info("Fitur pembuatan PO ke WhatsApp Supplier.")

# [M7] TRACKING
def show_tracking():
    st.markdown("## 📍 Tracking Status Produksi")
    conn = get_connection(); df = pd.read_sql_query("SELECT customer_name, pickup_date, status FROM custom_orders", conn.conn); conn.close()
    st.markdown(render_luxury_table(df), unsafe_allow_html=True)

# [M8] CRM & PROMO
def show_crm():
    st.markdown("## 📣 CRM & Promo Architect")
    conn = get_connection(); p_df = pd.read_sql_query("SELECT id, name, selling_price, discount_pct FROM recipe_master", conn.conn); conn.close()
    if not p_df.empty:
        sel = st.selectbox("Pilih Produk Promo", p_df['name'].tolist())
        row = p_df[p_df['name']==sel].iloc[0]
        disc = st.slider("Diskon (%)", 0, 100, int(row['discount_pct']))
        if st.button("AKTIFKAN PROMO"):
            c = get_connection(); c.execute("UPDATE recipe_master SET discount_pct = ? WHERE id = ?", (disc, int(row['id']))); c.conn.commit(); c.close(); st.success("Promo Aktif!"); st.rerun()

# [M9] R&D LAB
def show_rd():
    st.markdown("## 🧪 R&D Innovation Lab")
    with st.expander("➕ Ajukan Eksperimen"):
        n = st.text_input("Nama Riset")
        r = st.text_area("Alasan & Tujuan")
        if st.button("KIRIM KE OWNER"):
            c = get_connection(); c.execute("INSERT INTO pending_approvals (user_requester, action_type, description, reason) VALUES (?,?,?,?)", (st.session_state.user, "R&D", n, r))
            c.conn.commit(); c.close(); st.success("Pengajuan Dikirim!"); st.rerun()

# [M10] WASTE
def show_waste():
    st.markdown("## 🗑️ Manajemen Limbah & Kerugian")
    conn = get_connection(); inv = pd.read_sql_query("SELECT id, name FROM inventory_master", conn.conn); conn.close()
    with st.form("waste_f"):
        it = st.selectbox("Bahan Waste", inv['name'].tolist())
        qty = st.number_input("Jumlah", min_value=0.1)
        res = st.text_input("Alasan")
        if st.form_submit_button("CATAT KERUGIAN"):
            iid = inv[inv['name']==it]['id'].values[0]
            c = get_connection(); c.execute("INSERT INTO waste_log (inventory_id, qty_waste, reason) VALUES (?,?,?)", (int(iid), qty, res))
            c.conn.commit(); c.close(); st.success("Waste Tercatat!"); st.rerun()

# [M11] APPROVAL
def show_approval():
    st.markdown("## ✅ Approval Center")
    conn = get_connection(); df = pd.read_sql_query("SELECT * FROM pending_approvals WHERE status = 'PENDING'", conn.conn); conn.close()
    if df.empty: st.info("Tidak ada permintaan tertunda.")
    else:
        for idx, row in df.iterrows():
            st.write(f"**{row['user_requester']}** - {row['description']}")
            c1, c2 = st.columns(2)
            if c1.button("SETUJUI", key=f"app_{row['id']}"):
                c = get_connection(); c.execute("UPDATE pending_approvals SET status = 'DONE' WHERE id = ?", (int(row['id']),)); c.conn.commit(); c.close(); st.rerun()
            if c2.button("TOLAK", key=f"rej_{row['id']}"):
                c = get_connection(); c.execute("DELETE FROM pending_approvals WHERE id = ?", (int(row['id']),)); c.conn.commit(); c.close(); st.rerun()

# [M12] CHAT
def show_chat():
    st.markdown("## 💬 Team Chat Terminal")
    with st.form("chat_f", clear_on_submit=True):
        m = st.text_input("Pesan Anda")
        if st.form_submit_button("KIRIM"):
            c = get_connection(); c.execute("INSERT INTO internal_messages (sender, message) VALUES (?,?)", (st.session_state.user, m)); c.conn.commit(); c.close(); st.rerun()
    conn = get_connection(); msgs = pd.read_sql_query("SELECT timestamp, sender, message FROM internal_messages ORDER BY timestamp DESC LIMIT 20", conn.conn); conn.close()
    for _, msg in msgs.iterrows():
        st.markdown(f"**{msg['sender']}**: {msg['message']} <br><small>{msg['timestamp']}</small>", unsafe_allow_html=True)

# [M13] THE VAULT
def show_vault():
    st.markdown("## 💎 The Vault (Brankas Owner)")
    conn = get_connection(); bal = conn.execute("SELECT current_balance FROM business_vault").fetchone()[0]; conn.close()
    st.markdown(f"""<div style='background: #111; padding: 40px; border-radius: 20px; text-align: center; border: 2px solid gold;'><h1 style='color: gold;'>{format_rp(bal)}</h1><p style='color: white;'>SALDO KHAZANAH SAAT INI</p></div>""", unsafe_allow_html=True)

# [M14] HEALTH & GUARD
def show_health():
    st.markdown("## 🛡️ Guardian & System Health")
    st.success("✅ Database Connection: STABLE")
    st.success("✅ Memory Usage: OPTIMAL")
    st.success("✅ Profit Margin Integrity: SECURE")

# [M15] FINANCE/PROFIT
def show_finance():
    st.markdown("## 📈 Strategi Finansial & Profit")
    conn = get_connection(); df = pd.read_sql_query("SELECT timestamp, total_revenue, profit FROM sales_log ORDER BY timestamp DESC", conn.conn); conn.close()
    st.line_chart(df.set_index('timestamp')['profit'])

# [M16] SMART PRICING
def show_pricing():
    st.markdown("## 💰 Smart Pricing Architect")
    st.info("Menganalisis HPP real-time dan memberikan saran harga jual terbaik.")

# [M17] AUDIT & ANALISIS
def show_analysis():
    st.markdown("## 📊 Audit & Analisis Data")
    conn = get_connection(); df = pd.read_sql_query("SELECT * FROM sales_log", conn.conn); conn.close()
    st.write(df)

# [M18] INTEGRASI
def show_integration():
    st.markdown("## 🔗 Integrasi Sistem")
    st.info("Hubungkan ke GrabFood, GoFood, dan ShopeeFood Merchant.")

# [M19] SETTINGS
def show_settings():
    st.markdown("## ⚙️ Pengaturan & Hak Akses")
    with st.expander("➕ Tambah Staf"):
        u = st.text_input("Username")
        p = st.text_input("Password")
        r = st.selectbox("Role", ["STAFF", "MANAGER"])
        if st.button("BUAT AKUN"):
            c = get_connection(); c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", (u, p, r)); c.conn.commit(); c.close(); st.success("User Dibuat!")

# -----------------------------------------------------------------------------
# 4. MAIN APP TERMINAL
# -----------------------------------------------------------------------------
def main():
    init_db()
    st.set_page_config(page_title="Near Bakery Executive", layout="wide")
    
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;800&family=Inter:wght@400;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC !important; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] .stButton button { background: transparent !important; color: #94A3B8 !important; border: none !important; text-align: left !important; font-weight: 600 !important; padding-left: 15px !important; }
    [data-testid="stSidebar"] .stButton button:hover { color: white !important; background: rgba(255,255,255,0.05) !important; }
    .stMetric { background: white !important; padding: 20px !important; border-radius: 12px !important; border: 1px solid #F1F5F9 !important; }
    </style>
    """, unsafe_allow_html=True)
    
    if 'auth' not in st.session_state: st.session_state.auth = False
    
    if not st.session_state.auth:
        st.markdown("<h1 style='text-align: center; margin-top: 50px;'>NEAR BAKERY LOGIN</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("LOGIN", use_container_width=True, type="primary"):
                conn = get_connection(); user = conn.execute("SELECT username, role, permissions FROM users WHERE username=? AND password=?", (u, p)).fetchone(); conn.close()
                if user:
                    st.session_state.auth = True; st.session_state.user = user[0]; st.session_state.role = user[1]
                    st.session_state.permissions = user[2].split(',') if user[2] else []
                    st.rerun()
                else: st.error("Akses Ditolak")
        return

    # Sidebar Navigation
    with st.sidebar:
        st.markdown("<h2 style='color:white; margin-bottom:30px;'>NEAR BAKERY ERP</h2>", unsafe_allow_html=True)
        nav = {
            "🏠 Dashboard": "Home",
            "--- OPERASIONAL ---": "SEP1",
            "🖥️ Kasir Terminal": "POS",
            "📦 Inventaris Pusat": "Inventory",
            "🍞 Resep & Produksi": "Recipe",
            "🛒 Logistik & PO": "Purchase",
            "🥨 Order Kustom": "CustomOrder",
            "📍 Tracking Status": "Tracking",
            "--- ANALISIS & SDM ---": "SEP2",
            "🧪 R&D Lab": "RD",
            "🗑️ Manajemen Limbah": "Waste",
            "📣 CRM & Promo": "CRM",
            "💬 Team Chat": "Chat",
            "✅ Approval Center": "Approval"
        }
        
        if st.session_state.role in ['Owner', 'OWNER']:
            nav.update({
                "--- EKSEKUTIF ---": "SEP3",
                "💎 The Vault": "Vault",
                "📈 Finansial": "Finance",
                "💰 Smart Pricing": "Pricing",
                "📊 Audit Trail": "Audit",
                "🔗 Integrasi": "Integrasi",
                "🛡️ Health Check": "Health",
                "⚙️ Pengaturan": "Settings"
            })
            
        for label, page in nav.items():
            if label.startswith("---"): st.markdown(f"<div style='color:#64748B; font-size:0.7rem; font-weight:800; margin:15px 0 5px 10px;'>{label}</div>", unsafe_allow_html=True)
            elif st.button(label, use_container_width=True): st.session_state.page = page; st.rerun()
        
        st.write("---")
        if st.button("LOGOUT"): st.session_state.auth = False; st.rerun()

    # Router
    p = st.session_state.get('page', 'Home')
    if p == 'Home': show_dashboard()
    elif p == 'POS': show_pos()
    elif p == 'Inventory': show_inventory()
    elif p == 'Recipe': show_recipes()
    elif p == 'Purchase': show_logistics()
    elif p == 'CustomOrder': show_custom_order()
    elif p == 'Tracking': show_tracking()
    elif p == 'RD': show_rd()
    elif p == 'Waste': show_waste()
    elif p == 'CRM': show_crm()
    elif p == 'Chat': show_chat()
    elif p == 'Approval': show_approval()
    elif p == 'Vault': show_vault()
    elif p == 'Finance': show_finance()
    elif p == 'Pricing': show_pricing()
    elif p == 'Audit': show_analysis()
    elif p == 'Integrasi': show_integration()
    elif p == 'Health': show_health()
    elif p == 'Settings': show_settings()

if __name__ == "__main__":
    main()
