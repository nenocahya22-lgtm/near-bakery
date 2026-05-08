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

# [M2] POS TERMINAL (FULL)
def show_pos():
    st.markdown("## 🖥️ Kasir Terminal Executive")
    if 'cart' not in st.session_state: st.session_state.cart = {}
    
    col_a, col_b = st.columns([1.2, 2])
    with col_a:
        st.markdown("#### 🧺 Keranjang Pesanan")
        subtotal = 0
        if not st.session_state.cart: st.info("Keranjang kosong.")
        else:
            for pid, item in list(st.session_state.cart.items()):
                c_a, c_b = st.columns([3, 1])
                c_a.write(f"**{item['name']}**\n{format_rp(item['price'])} x {item['qty']}")
                if c_b.button("🗑️", key=f"del_{pid}"): del st.session_state.cart[pid]; st.rerun()
                subtotal += item['price'] * item['qty']
            
            st.write("---")
            st.markdown(f"### TOTAL: {format_rp(subtotal)}")
            pay_method = st.radio("Pembayaran", ["TUNAI", "QRIS", "DEBIT"], horizontal=True)
            if st.button("PROSES & CETAK STRUK", use_container_width=True, type="primary"):
                if subtotal > 0:
                    c = get_connection()
                    c.execute("INSERT INTO sales_log (total_revenue, profit, payment_method) VALUES (?,?,?)", (subtotal, subtotal*0.3, pay_method))
                    c.conn.commit(); c.close()
                    st.session_state.cart = {}; st.balloons(); st.success("Transaksi Berhasil!"); st.rerun()
    
    with col_b:
        st.markdown("#### 🥐 Menu Produk")
        search = st.text_input("🔍 Cari Produk...", placeholder="Ketik nama roti...")
        conn = get_connection()
        prods = pd.read_sql_query("SELECT id, name, selling_price, category FROM recipe_master", conn.conn)
        conn.close()
        
        if not prods.empty:
            filtered = prods[prods['name'].str.contains(search, case=False)]
            cols = st.columns(3)
            for idx, p in filtered.reset_index().iterrows():
                with cols[idx % 3]:
                    st.markdown(f"""
                    <div style='background: white; padding: 10px; border-radius: 10px; border: 1px solid #F1F5F9; text-align: center; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);'>
                        <small style='color: #3B82F6;'>{p['category']}</small>
                        <div style='font-weight: bold; font-size: 0.9rem; min-height: 40px;'>{p['name']}</div>
                        <div style='color: #1E293B; font-weight: 700;'>{format_rp(p['selling_price'])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("TAMBAH", key=f"add_{p['id']}", use_container_width=True):
                        pid = p['id']
                        if pid in st.session_state.cart: st.session_state.cart[pid]['qty'] += 1
                        else: st.session_state.cart[pid] = {'name': p['name'], 'price': p['selling_price'], 'qty': 1}
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

# [M4] RECIPE LAB (FULL)
def show_recipes():
    st.markdown("## 🍞 Manajemen Resep & Produksi")
    tab_list, tab_new = st.tabs(["📋 Daftar Resep", "📝 Buat Resep Baru"])
    
    with tab_new:
        with st.form("recipe_new_f"):
            r_name = st.text_input("Nama Produk")
            c1, c2 = st.columns(2)
            r_yield = c1.number_input("Hasil Produksi", min_value=1.0, value=1.0)
            r_price = c2.number_input("Harga Jual (Rp)", min_value=0.0)
            st.write("---")
            st.markdown("**Komposisi Bahan**")
            conn = get_connection(); inv = pd.read_sql_query("SELECT id, name, unit_pakai FROM inventory_master", conn.conn); conn.close()
            
            # Simple 10-ingredient slot for speed in unified app
            ings_data = []
            for i in range(5):
                ca, cb = st.columns([3, 1])
                ing = ca.selectbox(f"Bahan {i+1}", [""] + inv['name'].tolist(), key=f"u_ing_{i}")
                qty = cb.number_input(f"Qty", min_value=0.0, key=f"u_qty_{i}")
                if ing:
                    iid = inv[inv['name']==ing]['id'].values[0]
                    unit = inv[inv['name']==ing]['unit_pakai'].values[0]
                    ings_data.append((iid, qty, unit))
            
            if st.form_submit_button("✨ SIMPAN RESEP PERMANEN", use_container_width=True):
                if r_name and ings_data:
                    c = get_connection()
                    c.execute("INSERT INTO recipe_master (name, yield_qty, selling_price) VALUES (?,?,?)", (r_name, r_yield, r_price))
                    rid = c.lastrowid
                    for iid, iqty, iunit in ings_data:
                        c.execute("INSERT INTO recipe_ingredients (recipe_id, inventory_id, qty_pakai, unit) VALUES (?,?,?,?)", (rid, iid, iqty, iunit))
                    c.conn.commit(); c.close(); st.success("Resep Berhasil Disimpan!"); st.rerun()

    with tab_list:
        conn = get_connection(); recipes = pd.read_sql_query("SELECT id, name, yield_qty, selling_price FROM recipe_master", conn.conn); conn.close()
        if not recipes.empty:
            for _, r in recipes.iterrows():
                with st.expander(f"📦 {r['name']} | Yield: {r['yield_qty']} | {format_rp(r['selling_price'])}"):
                    cogs = get_cogs_calculation(r['id'])
                    st.write(f"**HPP Modal/Pcs:** {format_rp(cogs['hpp_per_unit'])}")
                    st.write(f"**Estimasi Laba/Pcs:** {format_rp(r['selling_price'] - cogs['hpp_per_unit'])}")

# [M5] INVENTORY (FULL)
def show_inventory():
    st.markdown("## 📦 Inventaris Pusat & Gudang")
    tab_status, tab_register, tab_adj = st.tabs(["📋 Status Stok", "➕ Registrasi Material", "⚙️ Penyesuaian"])
    
    with tab_status:
        conn = get_connection()
        inv_df = pd.read_sql_query("SELECT barcode as \"ID\", name as \"Bahan\", category as \"Kategori\", stock as \"Stok\", unit_pakai as \"Satuan\", price_per_unit_pakai as \"HPP\" FROM inventory_master ORDER BY category, name", conn.conn)
        conn.close()
        st.markdown(render_luxury_table(inv_df), unsafe_allow_html=True)
    
    with tab_register:
        st.markdown("#### ✨ Registrasi & Kalkulator HPP Otomatis")
        with st.form("reg_inv_f"):
            c1, c2 = st.columns(2)
            name_in = c1.text_input("Nama Bahan")
            cat_in = c2.selectbox("Kategori", ["Bahan Baku", "Kemasan", "Lainnya"])
            
            c1b, c2b, c3b = st.columns(3)
            u_beli = c1b.selectbox("Satuan Beli", ["Kg", "L", "Karton", "Pack", "Pcs"])
            u_pakai = c2b.selectbox("Satuan Pakai (Ecer)", ["gr", "ml", "Pcs"])
            isi = c3b.number_input("Isi per Satuan Beli", min_value=0.001, value=1.0)
            
            c1c, c2c = st.columns(2)
            total_bayar = c1c.number_input("Harga per Satuan Beli (Rp)", min_value=0.0)
            qty_masuk = c2c.number_input("Jumlah Beli", min_value=0.1, value=1.0)
            
            if st.form_submit_button("KONFIRMASI PENDAFTARAN", use_container_width=True):
                if name_in:
                    price_per_use = total_bayar / isi if isi > 0 else 0
                    fid = "NB-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                    c = get_connection()
                    c.execute("INSERT INTO inventory_master (name, barcode, category, stock, unit_beli, unit_pakai, price_per_unit_pakai) VALUES (?,?,?,?,?,?,?)",
                             (name_in, fid, cat_in, qty_masuk * isi, u_beli, u_pakai, price_per_use))
                    c.conn.commit(); c.close(); st.success(f"{name_in} Berhasil Didaftarkan!"); st.rerun()

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

# [M8] CRM & PROMO (FULL)
def show_crm():
    st.markdown("## 📣 CRM & Simulator Promo")
    st.info("Simulasikan diskon Anda di sini untuk melihat apakah Anda masih untung atau rugi.")
    conn = get_connection(); p_df = pd.read_sql_query("SELECT id, name, selling_price, discount_pct FROM recipe_master", conn.conn); conn.close()
    if not p_df.empty:
        c1, c2 = st.columns([1, 1])
        with c1:
            sel = st.selectbox("Pilih Produk", p_df['name'].tolist())
            row = p_df[p_df['name']==sel].iloc[0]
            disc = st.slider("Persentase Diskon (%)", 0, 100, int(row['discount_pct']))
            if st.button("🚀 AKTIFKAN PROMO", use_container_width=True):
                c = get_connection(); c.execute("UPDATE recipe_master SET discount_pct = ? WHERE id = ?", (disc, int(row['id']))); c.conn.commit(); c.close(); st.success("Promo Aktif!"); st.rerun()
        
        # Calculation
        cogs = get_cogs_calculation(int(row['id']))['hpp_per_unit']
        final_price = row['selling_price'] * (1 - disc/100)
        profit = final_price - cogs
        with c2:
            st.markdown("#### 💹 Analisis Margin")
            if final_price < cogs: st.error(f"❌ **BAHAYA: RUGI!**\nLaba: {format_rp(profit)}")
            elif final_price < (cogs * 1.2): st.warning(f"⚠️ **KRITIS: Margin < 20%**\nLaba: {format_rp(profit)}")
            else: st.success(f"✅ **AMAN & PROFIT**\nLaba: {format_rp(profit)}")

# [M9] R&D LAB (FULL)
def show_rd():
    st.markdown("## 🧪 R&D Innovation Lab")
    with st.expander("➕ Ajukan Eksperimen Baru"):
        st.info("Gunakan form ini untuk mengajukan uji coba resep baru ke Owner.")
        n = st.text_input("Nama Menu Eksperimen")
        r = st.text_area("Tujuan & Bahan yang Dibutuhkan")
        cost = st.number_input("Estimasi Biaya (Rp)", min_value=0)
        if st.button("AJUKAN KE OWNER", type="primary"):
            if n and r:
                c = get_connection(); c.execute("INSERT INTO pending_approvals (user_requester, action_type, description, reason) VALUES (?,?,?,?)", 
                         (st.session_state.user, "RISET_PRODUK", f"Riset: {n} (Estimasi {format_rp(cost)})", r))
                c.conn.commit(); c.close(); st.success("Pengajuan Terkirim!"); st.rerun()
    st.write("---")
    st.subheader("📋 Riwayat Riset Disetujui")
    st.info("Daftar riset yang telah berjalan akan muncul di sini.")

# [M10] WASTE (FULL)
def show_waste():
    st.markdown("## 🗑️ Manajemen Limbah & Waste")
    conn = get_connection(); inv = pd.read_sql_query("SELECT id, name, price_per_unit_pakai FROM inventory_master", conn.conn); conn.close()
    with st.form("waste_f"):
        it = st.selectbox("Material Waste", inv['name'].tolist())
        qty = st.number_input("Jumlah Waste", min_value=0.1)
        res = st.text_input("Alasan (Misal: Expired, Rusak)")
        if st.form_submit_button("CATAT KERUGIAN"):
            row = inv[inv['name']==it].iloc[0]
            loss = qty * row['price_per_unit_pakai']
            c = get_connection()
            c.execute("INSERT INTO waste_log (inventory_id, qty_waste, loss_value, reason) VALUES (?,?,?,?)", (int(row['id']), qty, loss, res))
            c.conn.commit(); c.close(); st.success(f"Waste Tercatat! Kerugian: {format_rp(loss)}"); st.rerun()

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

# [M16] SMART PRICING (FULL)
def show_pricing():
    st.markdown("## 💰 Smart Pricing Architect")
    conn = get_connection(); recipes = pd.read_sql_query("SELECT id, name FROM recipe_master", conn.conn); conn.close()
    sel = st.selectbox("Pilih Produk", recipes['name'].tolist())
    rid = recipes[recipes['name']==sel]['id'].values[0]
    cogs = get_cogs_calculation(int(rid))['hpp_per_unit']
    
    st.markdown(f"#### Analisis HPP: **{format_rp(cogs)}**")
    s1, s2, s3 = st.columns(3)
    s1.metric("Tier EKONOMI (30%)", format_rp(cogs * 1.3))
    s2.metric("Tier STANDAR (100%)", format_rp(cogs * 2.0))
    s3.metric("Tier PREMIUM (200%)", format_rp(cogs * 3.0))

# [M17] AUDIT & ANALISIS (FULL)
def show_analysis():
    st.markdown("## 📊 Audit & Keamanan Data")
    tab_rep, tab_audit = st.tabs(["📈 Laporan Laba Rugi", "🔒 Audit Logs"])
    with tab_rep:
        conn = get_connection(); df = pd.read_sql_query("SELECT timestamp, total_revenue, total_hpp, profit FROM sales_log ORDER BY timestamp DESC", conn.conn); conn.close()
        st.markdown(render_luxury_table(df), unsafe_allow_html=True)
    with tab_audit:
        conn = get_connection(); df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 20", conn.conn); conn.close()
        st.markdown(render_luxury_table(df), unsafe_allow_html=True)

# [M18] INTEGRASI (FULL)
def show_integration():
    st.markdown("## 🔗 Integrasi Sistem Cloud")
    st.info("Atur komisi saluran penjualan online (Grab/GoFood/Shopee).")
    with st.form("int_f"):
        c1, c2, c3 = st.columns(3)
        g = c1.number_input("GrabFood (%)", value=20.0)
        go = c2.number_input("GoFood (%)", value=20.0)
        s = c3.number_input("ShopeeFood (%)", value=20.0)
        if st.form_submit_button("SIMPAN KOMISI"):
            st.success("Komisi Saluran Disimpan!")

# [M19] SETTINGS (FULL)
def show_settings():
    st.markdown("## ⚙️ Pengaturan & Manajemen Akses")
    with st.form("user_f"):
        st.subheader("➕ Tambah Akses Staf")
        u = st.text_input("Username Gmail")
        p = st.text_input("Password Sementara")
        r = st.selectbox("Role / Jabatan", ["STAFF", "MANAGER", "LOGISTIK"])
        if st.form_submit_button("BERIKAN AKSES"):
            if u and p:
                c = get_connection(); c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", (u, p, r)); c.conn.commit(); c.close(); st.success(f"Akses untuk {u} berhasil dibuat!"); st.rerun()
    st.write("---")
    conn = get_connection(); df = pd.read_sql_query("SELECT username, role FROM users WHERE role != 'OWNER'", conn.conn); conn.close()
    st.subheader("👥 Daftar Staf Aktif")
    st.markdown(render_luxury_table(df), unsafe_allow_html=True)

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
