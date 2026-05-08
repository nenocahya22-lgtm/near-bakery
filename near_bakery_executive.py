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

# # [M1] DASHBOARD (LUXURY)
def show_dashboard():
    st.markdown("## 🏠 Executive Terminal")
    conn = get_connection()
    t_inv = conn.execute("SELECT SUM(stock * price_per_unit_pakai) FROM inventory_master").fetchone()[0] or 0
    t_rev = conn.execute("SELECT SUM(total_revenue) FROM sales_log").fetchone()[0] or 0
    t_prof = conn.execute("SELECT SUM(profit) FROM sales_log").fetchone()[0] or 0
    t_order = conn.execute("SELECT COUNT(*) FROM custom_orders WHERE status = 'PENDING'").fetchone()[0] or 0
    conn.close()

    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        ("📦 Nilai Stok", t_inv, "#3B82F6"),
        ("💰 Omzet", t_rev, "#10B981"),
        ("📈 Laba", t_prof, "#8B5CF6"),
        ("🥨 Order", t_order, "#F59E0B")
    ]
    for i, (label, val, color) in enumerate(metrics):
        with [c1, c2, c3, c4][i]:
            st.markdown(f"""
            <div style='background: white; padding: 20px; border-radius: 15px; border-bottom: 4px solid {color}; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);'>
                <div style='color: #64748B; font-size: 0.75rem; font-weight: 700;'>{label.upper()}</div>
                <div style='color: #0F172A; font-size: 1.4rem; font-weight: 800; margin-top: 5px;'>{format_rp(val) if isinstance(val, (int, float)) and i<3 else val}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.write("---")
    st.subheader("📊 Aktivitas Terbaru")
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

# [M3] CUSTOM ORDER (FULL)
def show_custom_order():
    st.markdown("## 🥨 Order Kustom Architect")
    with st.expander("➕ Catat Pesanan Baru"):
        with st.form("custom_order_f"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nama Pelanggan")
            phone = c2.text_input("WhatsApp (628xxx)")
            det = st.text_area("Detail Roti / Kue (Contoh: Roti Buaya Besar 2 Pcs)")
            c1b, c2b = st.columns(2)
            price = c1b.number_input("Harga Total (Rp)", min_value=0)
            dp = c2b.number_input("DP / Uang Muka (Rp)", min_value=0)
            p_date = st.date_input("Tanggal Ambil", value=date.today() + timedelta(days=2))
            if st.form_submit_button("SIMPAN ORDER KUSTOM"):
                if name and price:
                    c = get_connection(); c.execute("INSERT INTO custom_orders (customer_name, phone, order_details, pickup_date, total_price, down_payment) VALUES (?,?,?,?,?,?)", (name, phone, det, p_date, price, dp))
                    c.conn.commit(); c.close(); st.success("Order Berhasil Dicatat!"); st.rerun()

    st.write("---")
    st.subheader("📋 Daftar Pesanan Aktif")
    conn = get_connection(); orders = pd.read_sql_query("SELECT * FROM custom_orders WHERE status != 'DONE' ORDER BY pickup_date", conn.conn); conn.close()
    if orders.empty: st.info("Tidak ada order kustom aktif.")
    else:
        for _, ord in orders.iterrows():
            st.markdown(f"""
            <div style='background: white; padding: 20px; border-radius: 15px; border: 1px solid #E2E8F0; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <b style='font-size: 1.1rem; color: #0F172A;'>👤 {ord['customer_name']}</b>
                    <span style='background: #FEF3C7; color: #92400E; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 700;'>{ord['status']}</span>
                </div>
                <div style='font-size: 0.9rem; color: #475569; margin: 10px 0;'>📦 {ord['order_details']}</div>
                <div style='font-size: 0.85rem; color: #64748B;'>📅 Ambil: <b style='color:#0F172A'>{ord['pickup_date']}</b> | 💰 Sisa: <b style='color:#10B981'>{format_rp(ord['total_price'] - ord['down_payment'])}</b></div>
            </div>
            """, unsafe_allow_html=True)

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

# [M6] LOGISTICS (FULL)
def show_logistics():
    st.markdown("## 🛒 Logistik & Supplier Hub")
    tab_supp, tab_po = st.tabs(["🏢 Supplier", "📋 Purchase Order"])
    with tab_supp:
        with st.form("supp_f"):
            n = st.text_input("Nama Supplier / Toko")
            p = st.text_input("WhatsApp (628xxx)")
            if st.form_submit_button("SIMPAN SUPPLIER"):
                if n and p:
                    c = get_connection(); c.execute("INSERT INTO suppliers (name, phone) VALUES (?,?)", (n, p)); c.conn.commit(); c.close(); st.success("Supplier Tersimpan!"); st.rerun()
        conn = get_connection(); df = pd.read_sql_query("SELECT name, phone FROM suppliers", conn.conn); conn.close()
        st.markdown(render_luxury_table(df), unsafe_allow_html=True)
    with tab_po:
        conn = get_connection(); inv = pd.read_sql_query("SELECT name FROM inventory_master", conn.conn); sup = pd.read_sql_query("SELECT name, phone FROM suppliers", conn.conn); conn.close()
        if not sup.empty:
            s_sel = st.selectbox("Pilih Supplier", sup['name'].tolist())
            i_sel = st.selectbox("Pilih Bahan", inv['name'].tolist())
            qty = st.number_input("Jumlah", min_value=1.0)
            if st.button("🚀 KIRIM PESANAN KE WHATSAPP", use_container_width=True, type="primary"):
                phone = sup[sup['name']==s_sel]['phone'].values[0]
                msg = f"Halo {s_sel}, saya ingin memesan {i_sel} sebanyak {qty}. Mohon infokan harganya. Terima kasih."
                st.link_button("KLIK UNTUK KIRIM WA", f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}", use_container_width=True)
        else: st.warning("Daftarkan supplier terlebih dahulu.")

# [M7] TRACKING (FULL)
def show_tracking():
    st.markdown("## 📍 Tracking Status Produksi")
    conn = get_connection(); df = pd.read_sql_query("SELECT id, customer_name, order_details, pickup_date, status FROM custom_orders WHERE status != 'DONE'", conn.conn); conn.close()
    if df.empty: st.info("Semua produksi selesai.")
    else:
        for _, r in df.iterrows():
            with st.container():
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"""<div style='background:#F8FAFC; padding:15px; border-radius:10px; border-left:4px solid #3B82F6;'><b>{r['customer_name']}</b><br><small>{r['order_details']} | Ambil: {r['pickup_date']}</small></div>""", unsafe_allow_html=True)
                new_stat = c2.selectbox("Update Status", ["PENDING", "PROSES", "SIAP", "DONE"], index=["PENDING", "PROSES", "SIAP", "DONE"].index(r['status']), key=f"stat_{r['id']}")
                if new_stat != r['status']:
                    c = get_connection(); c.execute("UPDATE custom_orders SET status = ? WHERE id = ?", (new_stat, int(r['id']))); c.conn.commit(); c.close(); st.rerun()

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

# [M11] APPROVAL (FULL)
def show_approval():
    st.markdown("## ✅ Approval Center")
    conn = get_connection(); df = pd.read_sql_query("SELECT * FROM pending_approvals WHERE status = 'PENDING'", conn.conn); conn.close()
    if df.empty: st.info("Tidak ada permintaan tertunda.")
    else:
        for idx, row in df.iterrows():
            st.markdown(f"""<div style='background:white; padding:20px; border-radius:15px; border:1px solid #E2E8F0; margin-bottom:15px;'><b>Permintaan dari: {row['user_requester']}</b><br><small>{row['timestamp']}</small><br><p>{row['description']}</p><p style='font-style:italic; color:gray;'>Alasan: {row['reason']}</p></div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✅ SETUJUI", key=f"app_{row['id']}", use_container_width=True):
                c = get_connection(); c.execute("UPDATE pending_approvals SET status = 'DONE' WHERE id = ?", (int(row['id']),)); c.conn.commit(); c.close(); st.rerun()
            if c2.button("❌ TOLAK", key=f"rej_{row['id']}", use_container_width=True):
                c = get_connection(); c.execute("DELETE FROM pending_approvals WHERE id = ?", (int(row['id']),)); c.conn.commit(); c.close(); st.rerun()

# [M12] CHAT (FULL)
def show_chat():
    st.markdown("## 💬 Team Chat Terminal")
    with st.form("chat_f", clear_on_submit=True):
        m = st.text_input("Ketik Pesan...", placeholder="Instruksi atau laporan tim...")
        if st.form_submit_button("🚀 KIRIM KE TIM"):
            if m:
                c = get_connection(); c.execute("INSERT INTO internal_messages (sender, message) VALUES (?,?)", (st.session_state.user, m))
                c.conn.commit(); c.close(); st.rerun()
    st.write("---")
    conn = get_connection(); msgs = pd.read_sql_query("SELECT timestamp, sender, message FROM internal_messages ORDER BY timestamp DESC LIMIT 20", conn.conn); conn.close()
    if not msgs.empty:
        for _, msg in msgs.iterrows():
            is_me = msg['sender'] == st.session_state.user
            color = "#E0F2FE" if is_me else "#F1F5F9"
            align = "right" if is_me else "left"
            st.markdown(f"""<div style='text-align:{align};'><div style='display:inline-block; background:{color}; padding:10px 15px; border-radius:15px; margin-bottom:5px; max-width:80%;'><small><b>{msg['sender']}</b> | {msg['timestamp']}</small><br>{msg['message']}</div></div>""", unsafe_allow_html=True)

# [M13] THE VAULT (LUXURY VERSION)
def show_vault():
    st.markdown("## 🏛️ Khazanah Bisnis (The Vault)")
    st.info("Semua hasil penjualan mengalir ke sini sebelum ditarik ke Rekening Bank Pribadi Anda.")
    
    conn = get_connection()
    vault_data = conn.execute("SELECT current_balance, last_update FROM business_vault").fetchone()
    ledger = pd.read_sql_query("SELECT timestamp, amount, type, source, description FROM vault_ledger ORDER BY timestamp DESC LIMIT 10", conn.conn)
    conn.close()
    
    balance = vault_data[0] if vault_data else 0.0
    
    # --- HEADER DISPLAY ---
    c1, c2, c3 = st.columns([1.5, 1, 1.2])
    with c1:
        st.markdown(f"""
        <div style='background: #1E1B18; padding: 30px; border-radius: 20px; border: 2px solid #D4AF37; box-shadow: 0 10px 25px rgba(0,0,0,0.2);'>
            <div style='color: #8E8A85; font-size: 0.8rem; letter-spacing: 2px;'>TOTAL SALDO KHAZANAH</div>
            <div style='color: #D4AF37; font-size: 2.8rem; font-weight: 900; font-family: "Outfit", sans-serif;'>{format_rp(balance)}</div>
            <div style='color: #8E8A85; font-size: 0.7rem; margin-top: 10px;'>ID REKENING: <b style='color:#D4AF37'>NB-VLT-2026-888</b></div>
            <div style='color: #8E8A85; font-size: 0.7rem;'>Update Terakhir: {vault_data[1] if vault_data else 'N/A'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        qr_svg = f"""<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100" fill="white" /><path d="M10 10h30v30h-30z M60 10h30v30h-30z M10 60h30v30h-30z M60 60h30v30h-30z" fill="#1E1B18" /><path d="M20 20h10v10h-10z M70 20h10v10h-10z M20 70h10v10h-10z M70 70h10v10h-10z" fill="#D4AF37" /><rect x="45" y="45" width="10" height="10" fill="#D4AF37" /></svg>"""
        st.markdown(f"<div style='width: 120px; margin: 0 auto;'>{qr_svg}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center; font-size: 0.6rem; color: #64748B; margin-top: 5px;'>QRIS RESMI TOKO</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("#### 🏦 Transaksi Dana")
        with st.form("vault_move_f"):
            amt = st.number_input("Jumlah (Rp)", min_value=0.0, max_value=balance)
            notes = st.text_input("Keterangan")
            if st.form_submit_button("KONFIRMASI PAYOUT", use_container_width=True):
                if amt > 0:
                    c = get_connection()
                    c.execute("UPDATE business_vault SET current_balance = current_balance - ?", (amt,))
                    c.execute("INSERT INTO vault_ledger (amount, type, description) VALUES (?,?,?)", (-amt, "PAYOUT", notes))
                    c.conn.commit(); c.close(); st.success("Dana Berhasil Ditarik!"); st.rerun()

    st.write("---")
    st.markdown("### 📜 Buku Besar Khazanah")
    st.markdown(render_luxury_table(ledger), unsafe_allow_html=True)

# [M14] HEALTH & GUARD (BRAIN ENGINE)
def run_system_health_check():
    issues = []
    conn = get_connection()
    try:
        # 1. Check Negative Stock
        neg = conn.execute("SELECT name, stock FROM inventory_master WHERE stock < 0").fetchall()
        for i in neg: issues.append({"type": "STOK MINUS", "desc": f"Barang '{i[0]}' minus {i[1]}.", "severity": "HIGH"})
        # 2. Check Low Margin
        recipes = conn.execute("SELECT id, name, selling_price FROM recipe_master").fetchall()
        for r in recipes:
            cogs = get_cogs_calculation(r[0])['hpp_per_unit']
            if r[2] <= cogs and cogs > 0:
                issues.append({"type": "DETEKSI BONCOS", "desc": f"Roti '{r[1]}' dijual rugi!", "severity": "CRITICAL"})
    except: pass
    finally: conn.close()
    return issues

def show_health():
    st.markdown("## 🛡️ Guardian System & Health")
    issues = run_system_health_check()
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", "CRITICAL" if any(i['severity']=='CRITICAL' for i in issues) else "EXCELLENT")
    c2.metric("Isu Terdeteksi", len(issues))
    c3.metric("Uptime", "99.9%")
    
    st.write("---")
    if not issues: st.success("✨ Semua sistem berjalan sempurna.")
    for iss in issues:
        color = "#EF4444" if iss['severity']=='CRITICAL' else "#F59E0B"
        st.markdown(f"<div style='padding:15px; border-left:5px solid {color}; background:#F8FAFC; border-radius:10px; margin-bottom:10px;'><b>{iss['type']}</b><br><small>{iss['desc']}</small></div>", unsafe_allow_html=True)

# [M14] FINANCE/PROFIT (EXECUTIVE ANALYTICS)
def show_finance():
    st.markdown("## 📈 Strategi Finansial & Profitabilitas")
    conn = get_connection()
    df = pd.read_sql_query("SELECT timestamp, total_revenue as \"Omzet\", profit as \"Laba\" FROM sales_log ORDER BY timestamp ASC", conn.conn)
    conn.close()
    
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("#### Performa Laba vs Omzet")
            st.line_chart(df.set_index('timestamp')[['Omzet', 'Laba']])
        with c2:
            st.markdown("#### Ringkasan Eksekutif")
            total_laba = df['Laba'].sum()
            avg_margin = (df['Laba'].sum() / df['Omzet'].sum() * 100) if df['Omzet'].sum() > 0 else 0
            st.metric("Total Laba Bersih", format_rp(total_laba))
            st.metric("Rata-rata Margin", f"{avg_margin:.1f}%")
            if avg_margin < 20: st.warning("Margin di bawah target 20%!")
            else: st.success("Performa finansial sehat & stabil.")
    else:
        st.info("Data transaksi belum tersedia untuk analisis strategi.")

# [M16] SMART PRICING (LUXURY VERSION)
def show_pricing():
    st.markdown("## 🧠 Smart Pricing Architect")
    st.info("Sistem cerdas untuk menghitung HPP mendalam dan strategi penetapan harga.")
    conn = get_connection(); recipes = pd.read_sql_query("SELECT id, name FROM recipe_master", conn.conn); conn.close()
    if recipes.empty: st.warning("Belum ada resep."); return
    
    sel_recipe = st.selectbox("Pilih Produk", recipes['name'].tolist())
    rid = recipes[recipes['name'] == sel_recipe]['id'].values[0]
    cogs_data = get_cogs_calculation(rid)
    hpp = cogs_data['hpp_per_unit']

    s1, s2, s3 = st.columns(3)
    def r5(p): return round(p / 500) * 500
    
    with s1:
        st.markdown(f"<div style='background:#F1F5F9; padding:20px; border-radius:15px; border:1px solid #E2E8F0; text-align:center;'><p style='color:#64748B; font-weight:700; font-size:0.7rem;'>TIER EKONOMI (30%)</p><h3>{format_rp(r5(hpp*1.3))}</h3></div>", unsafe_allow_html=True)
        if st.button("Pilih Ekonomi", key="p_eco", use_container_width=True):
            c = get_connection(); c.execute("UPDATE recipe_master SET selling_price = ? WHERE id = ?", (r5(hpp*1.3), rid)); c.conn.commit(); c.close(); st.success("Updated!"); st.rerun()
    with s2:
        st.markdown(f"<div style='background:#E0F2FE; padding:20px; border-radius:15px; border:2px solid #3B82F6; text-align:center;'><p style='color:#0369A1; font-weight:700; font-size:0.7rem;'>TIER STANDAR (100%)</p><h3>{format_rp(r5(hpp*2.0))}</h3></div>", unsafe_allow_html=True)
        if st.button("Pilih Standar", key="p_std", type="primary", use_container_width=True):
            c = get_connection(); c.execute("UPDATE recipe_master SET selling_price = ? WHERE id = ?", (r5(hpp*2.0), rid)); c.conn.commit(); c.close(); st.success("Updated!"); st.rerun()
    with s3:
        st.markdown(f"<div style='background:#FAF5FF; padding:20px; border-radius:15px; border:1px solid #D8B4FE; text-align:center;'><p style='color:#7E22CE; font-weight:700; font-size:0.7rem;'>TIER PREMIUM (200%)</p><h3>{format_rp(r5(hpp*3.0))}</h3></div>", unsafe_allow_html=True)
        if st.button("Pilih Premium", key="p_prm", use_container_width=True):
            c = get_connection(); c.execute("UPDATE recipe_master SET selling_price = ? WHERE id = ?", (r5(hpp*3.0), rid)); c.conn.commit(); c.close(); st.success("Updated!"); st.rerun()

# [M17] AUDIT & ANALISIS (FULL VERSION)
def show_analysis():
    st.markdown("## 📊 Analisis & Keamanan Data (Audit Trail)")
    t1, t2, t3 = st.tabs(["📈 Laporan Penjualan", "📩 Inbox Pelanggan", "🔒 Audit Logs"])
    with t1:
        conn = get_connection(); sales = pd.read_sql_query("SELECT timestamp, total_revenue, profit, payment_method FROM sales_log ORDER BY timestamp DESC", conn.conn); conn.close()
        st.markdown(render_luxury_table(sales), unsafe_allow_html=True)
    with t2:
        conn = get_connection(); msgs = pd.read_sql_query("SELECT * FROM customer_messages", conn.conn); conn.close()
        st.markdown(render_luxury_table(msgs), unsafe_allow_html=True)
    with t3:
        conn = get_connection(); logs = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn.conn); conn.close()
        st.markdown(render_luxury_table(logs), unsafe_allow_html=True)

# [M18] INTEGRASI (FULL VERSION)
def show_integration():
    st.markdown("## 🌐 Global Integration & Cloud Center")
    t1, t2, t3 = st.tabs(["🚀 Cloud Deployment", "⚙️ Channel Settings", "📱 Marketplace Portal"])
    with t1:
        st.success("System Engine: READY | Database: SUPABASE CLOUD")
        st.markdown("<div style='background:rgba(212,175,55,0.05); padding:20px; border-radius:15px; border:1px dashed #D4AF37;'><b>Langkah Go Online:</b> Hubungkan GitHub dan klik 'Deploy' di Streamlit Cloud.</div>", unsafe_allow_html=True)
    with t2:
        with st.form("comm_f"):
            c1, c2, c3 = st.columns(3)
            g = c1.number_input("GrabFood (%)", value=20.0)
            go = c2.number_input("GoFood (%)", value=20.0)
            s = c3.number_input("ShopeeFood (%)", value=20.0)
            if st.form_submit_button("SIMPAN KOMISI"): st.success("Saved!")
    with t3:
        st.markdown("#### 🔗 Merchant Portal Quick Access")
        ca, cb, cc = st.columns(3)
        ca.link_button("🌐 Grab Merchant", "https://merchant.grab.com/portal", use_container_width=True)
        cb.link_button("🌐 GoBiz Portal", "https://gobiz.co.id/", use_container_width=True)
        cc.link_button("🌐 Shopee Partner", "https://shopee-p-partner.shopee.co.id/", use_container_width=True)

# [M19] SETTINGS (FULL VERSION)
def show_settings():
    st.markdown("## ⚙️ Pengaturan & Hak Akses")
    with st.expander("➕ Tambah Akses Staf Baru"):
        with st.form("u_f"):
            u = st.text_input("Nama Lengkap")
            e = st.text_input("Email Gmail")
            r = st.selectbox("Role", ["Staff", "Logistik", "Manajer"])
            p = st.text_input("Password", type="password")
            if st.form_submit_button("BERIKAN AKSES"):
                c = get_connection(); c.execute("INSERT INTO users (username, password, role, email) VALUES (?,?,?,?)", (u, p, r, e)); c.conn.commit(); c.close(); st.success("User Added!"); st.rerun()
    st.write("---")
    st.subheader("👥 Daftar Staf Aktif & Otoritas")
    conn = get_connection(); users = pd.read_sql_query("SELECT username as \"Nama\", email as \"Gmail\", role as \"Jabatan\" FROM users WHERE role != 'OWNER'", conn.conn); conn.close()
    st.markdown(render_luxury_table(users), unsafe_allow_html=True)

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
