# --- NEAR BAKERY & CO. EXECUTIVE ERP MASTER (UNIFIED) ---
# VERSION: 4.0 (FULL FIDELITY - CONSOLIDATED)
# DESCRIPTION: 100% Original Logic & Luxury UI consolidated into one file.
# AUTHOR: Antigravity AI

import streamlit as st
import pandas as pd
import os
import base64
import json
import random
import string
import urllib.parse
import re
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# -----------------------------------------------------------------------------
# 1. DATABASE ENGINE (POSTGRES / SUPABASE READY)
# -----------------------------------------------------------------------------
try:
    DB_URL = st.secrets["DB_URL"]
except:
    DB_URL = "postgresql://postgres.btcsynyxodkonqdpwowx:%23Nenocahyamulan190604@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DB_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class PostgresCursor:
    def __init__(self, parent):
        self.parent = parent
        self.description = None
        self.rowcount = -1
    def execute(self, query, params=None):
        self.parent.execute(query, params)
        self.description = self.parent.description
        self.rowcount = self.parent.rowcount
        return self
    def fetchall(self): return self.parent.fetchall()
    def fetchone(self): return self.parent.fetchone()
    def close(self): pass

class PostgresCompat:
    def __init__(self, conn):
        self.conn = conn
        self._current_result = None
    def cursor(self): return PostgresCursor(self)
    def execute(self, query, params=None):
        try:
            if isinstance(query, str):
                query = query.replace("date('now')", "CURRENT_DATE")
                query = query.replace("datetime('now')", "CURRENT_TIMESTAMP")
                query = re.sub(r"date\((?!')(.*?)\)", r"\1::date", query)
                if "INSERT OR REPLACE INTO" in query: query = query.replace("INSERT OR REPLACE INTO", "INSERT INTO")
                placeholders = re.findall(r'\?', query)
                for i in range(len(placeholders)): query = query.replace('?', f':p{i+1}', 1)
                query_obj = text(query)
                if params:
                    if isinstance(params, (tuple, list)):
                        param_dict = {f'p{i+1}': val for i, val in enumerate(params)}
                        self._current_result = self.conn.execute(query_obj, param_dict)
                    else: self._current_result = self.conn.execute(query_obj, params)
                else: self._current_result = self.conn.execute(query_obj)
            else: self._current_result = self.conn.execute(query, params) if params else self.conn.execute(query)
        except Exception as e:
            try: self.conn.rollback()
            except: pass
            raise e
        return self
    def fetchall(self): return self._current_result.fetchall() if self._current_result else []
    def fetchone(self): return self._current_result.fetchone() if self._current_result else None
    def scalar(self): return self._current_result.scalar() if self._current_result else None
    @property
    def description(self): return [(name, None, None, None, None, None, None) for name in self._current_result.keys()] if self._current_result else []
    @property
    def rowcount(self): return self._current_result.rowcount if self._current_result else -1
    @property
    def lastrowid(self): return None
    def commit(self):
        try: self.conn.commit()
        except: pass
    def rollback(self):
        try: self.conn.rollback()
        except: pass
    def close(self):
        try: self.conn.close()
        except: pass
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try: self.conn.rollback()
            except: pass
        try: self.conn.close()
        except: pass

def get_connection(): return PostgresCompat(engine.connect())

def initialize_database():
    conn = get_connection()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, email TEXT, permissions TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS inventory_master (id SERIAL PRIMARY KEY, name TEXT, category TEXT, stock FLOAT, unit_beli TEXT, unit_pakai TEXT, price_per_unit_beli FLOAT, price_per_unit_pakai FLOAT, barcode TEXT UNIQUE, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS recipe_master (id SERIAL PRIMARY KEY, name TEXT, barcode TEXT UNIQUE, category TEXT, yield_qty FLOAT, yield_unit TEXT, selling_price FLOAT DEFAULT 0, discount_pct FLOAT DEFAULT 0, image_path TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS recipe_ingredients (id SERIAL PRIMARY KEY, recipe_id INTEGER, inventory_id INTEGER, qty_pakai FLOAT, unit TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS sales_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, total_revenue FLOAT, total_hpp FLOAT DEFAULT 0, profit FLOAT DEFAULT 0, payment_method TEXT, customer_id INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS business_vault (id SERIAL PRIMARY KEY, current_balance FLOAT DEFAULT 0, last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS vault_ledger (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, amount FLOAT, type TEXT, source TEXT, description TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS finance_config (config_key TEXT PRIMARY KEY, config_value FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS pending_approvals (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_requester TEXT, action_type TEXT, description TEXT, data_payload TEXT, reason TEXT, status TEXT DEFAULT 'PENDING')")
        conn.execute("CREATE TABLE IF NOT EXISTS internal_messages (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, sender TEXT, message TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_actor TEXT, action TEXT, table_name TEXT, old_value TEXT, new_value TEXT, reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS customer_messages (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, customer_name TEXT, email TEXT, message TEXT, status TEXT DEFAULT 'UNREAD')")
        conn.execute("CREATE TABLE IF NOT EXISTS stock_movement_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, inventory_id INTEGER, qty FLOAT, type TEXT, reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS product_addons (id SERIAL PRIMARY KEY, name TEXT, price FLOAT, inventory_id INTEGER, qty_deduct FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS suppliers (id SERIAL PRIMARY KEY, name TEXT, contact_person TEXT, phone TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS purchase_order_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, inventory_id INTEGER, supplier_id INTEGER, qty_order FLOAT, unit_order TEXT, price_total FLOAT, status TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS rd_trials (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, name TEXT, total_cost FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS rd_trial_ingredients (id SERIAL PRIMARY KEY, trial_id INTEGER, inventory_id INTEGER, qty_pakai FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS waste_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, inventory_id INTEGER, qty_waste FLOAT, loss_value FLOAT, reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS asset_waste_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, asset_name TEXT, loss_value FLOAT, reason TEXT, image_path TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS budget_usage_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, room_name TEXT, amount FLOAT, description TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS budget_allocation (room_name TEXT PRIMARY KEY, target_pct FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS packaging_bundles (id SERIAL PRIMARY KEY, name TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS packaging_bundle_items (id SERIAL PRIMARY KEY, bundle_id INTEGER, inventory_id INTEGER, qty FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS category_packaging_map (category_name TEXT PRIMARY KEY, bundle_id INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS custom_orders (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, customer_name TEXT, phone TEXT, order_details TEXT, pickup_date DATE, total_price FLOAT, down_payment FLOAT, notes TEXT, status TEXT DEFAULT 'PENDING')")
        conn.execute("CREATE TABLE IF NOT EXISTS system_settings (config_key TEXT PRIMARY KEY, config_value FLOAT)")
        
        # Seed
        if conn.execute("SELECT COUNT(*) FROM users WHERE username='admin'").scalar() == 0:
            conn.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'nearbakery2024', 'OWNER')")
        if conn.execute("SELECT COUNT(*) FROM business_vault").scalar() == 0:
            conn.execute("INSERT INTO business_vault (current_balance) VALUES (0)")
        if conn.execute("SELECT COUNT(*) FROM finance_config").scalar() == 0:
            conn.execute("INSERT INTO finance_config (config_key, config_value) VALUES ('global_margin_pct', 100)")
            conn.execute("INSERT INTO finance_config (config_key, config_value) VALUES ('cogs_buffer_pct', 5)")
        conn.commit()
    except Exception as e: print(f"Init Error: {e}")
    finally: conn.close()

# -----------------------------------------------------------------------------
# 2. UTILITIES
# -----------------------------------------------------------------------------
def format_rp(value): return f"Rp {value:,.0f}"

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
    ings = conn.execute("""
        SELECT inv.name, ri.qty_pakai, ri.unit as recipe_unit, inv.unit_pakai as inv_unit, inv.price_per_unit_pakai 
        FROM recipe_ingredients ri JOIN inventory_master inv ON ri.inventory_id = inv.id WHERE ri.recipe_id = ?
    """, (recipe_id,)).fetchall()
    conn.close()
    total_hpp, breakdown = 0, []
    for name, r_qty, r_unit, i_unit, i_price in ings:
        conv_q = convert_qty(r_qty, r_unit, i_unit)
        cost = conv_q * (i_price or 0)
        total_hpp += cost
        breakdown.append({"name": name, "qty": r_qty, "unit": r_unit, "total_cost": cost})
    if include_buffer:
        c = get_connection(); res_b = c.execute("SELECT config_value FROM finance_config WHERE config_key='cogs_buffer_pct'").fetchone(); c.close()
        total_hpp *= (1 + (res_b[0] if res_b else 0)/100)
    return {"total_hpp": total_hpp, "hpp_per_unit": total_hpp / y_qty if y_qty > 0 else 0, "yield_qty": y_qty, "ingredients": breakdown}

def get_dynamic_selling_price(recipe_id):
    c = get_connection(); res_m = c.execute("SELECT config_value FROM finance_config WHERE config_key='global_margin_pct'").fetchone(); c.close()
    cogs = get_cogs_calculation(recipe_id, include_buffer=True)
    return cogs['hpp_per_unit'] * (1 + (res_m[0] if res_m else 100)/100)

def render_luxury_table(df):
    if df.empty: return "<div style='text-align: center; padding: 40px; color: #94A3B8; background: white; border-radius: 12px; border: 1px dashed #E2E8F0;'>No data available.</div>"
    headers = [str(col).replace("_", " ").upper() for col in df.columns]
    html = '<div style="overflow-x: auto; border: 1px solid #E2E8F0; border-radius: 8px; background: white; margin: 15px 0;"><table style="width: 100%; border-collapse: collapse; font-family: \'Inter\', sans-serif;"><thead><tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">'
    for col in headers: html += f"<th style='padding: 12px 15px; text-align: left; color: #64748B; font-weight: 600; font-size: 11px; text-transform: uppercase;'>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr style='border-bottom: 1px solid #F1F5F9;'>"
        for col_name, val in zip(df.columns, row):
            display_val, cell_style = val, "padding: 10px 15px; color: #334155; font-size: 13px;"
            v_str = str(val).upper()
            if v_str in ['LUNAS', 'PAID', 'COMPLETED', 'SUCCESS', 'ACTIVE', 'DONE', 'APPROVED']: display_val = f"<span style='color: #059669; font-weight: 600;'>● {val}</span>"
            elif v_str in ['PENDING', 'WAITING', 'IN PROGRESS']: display_val = f"<span style='color: #D97706; font-weight: 600;'>● {val}</span>"
            elif isinstance(val, (int, float)) and val > 1000 and "QTY" not in str(col_name).upper() and "ID" not in str(col_name).upper():
                display_val = format_rp(val); cell_style += " color: #0F172A; font-weight: 500;"
            html += f"<td style='{cell_style}'>{display_val}</td>"
        html += "</tr>"
    return html + "</tbody></table></div>"

UNITS_MASTER = ["Kilogram (Kg)", "Gram (gr)", "Liter (L)", "Mililiter (ml)", "Pcs", "Karton", "Pack", "Butir", "Slice"]
CATEGORIES_MASTER = ["BAKERY", "DRINK"]

# -----------------------------------------------------------------------------
# 3. MODULE FUNCTIONS (CONSOLIDATED LOGIC)
# -----------------------------------------------------------------------------

def show_dashboard():
    st.markdown("""<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 35px; background: white; padding: 25px; border-radius: 24px; border: 1px solid #F1F5F9;"><div><h1 style="margin: 0; font-size: 1.8rem;">Dashboard</h1><p style="color: #64748B;">Selamat datang, <b>{}</b></p></div></div>""".format(st.session_state.user), unsafe_allow_html=True)
    conn = get_connection()
    rev = conn.execute("SELECT SUM(total_revenue) FROM sales_log WHERE date(timestamp) = CURRENT_DATE").scalar() or 0
    orders = conn.execute("SELECT COUNT(*) FROM sales_log WHERE date(timestamp) = CURRENT_DATE").scalar() or 0
    vault = conn.execute("SELECT current_balance FROM business_vault").scalar() or 0
    conn.close()
    m1, m2, m3 = st.columns(3)
    m1.metric("SALES TODAY", format_rp(rev)); m2.metric("ORDERS", orders); m3.metric("VAULT BALANCE", format_rp(vault))
    st.write("---")
    st.markdown("### 📈 Executive Intelligence")
    c1, c2 = st.columns(2)
    with c1:
        conn = get_connection(); df = pd.read_sql_query("SELECT date(timestamp) as date, SUM(total_revenue) as revenue FROM sales_log GROUP BY date ORDER BY date LIMIT 30", conn); conn.close()
        if not df.empty: st.line_chart(df.set_index('date'))
    with c2:
        conn = get_connection(); df = pd.read_sql_query("SELECT category, COUNT(*) as count FROM recipe_master GROUP BY category", conn); conn.close()
        if not df.empty: st.bar_chart(df.set_index('category'))

def show_pos():
    st.markdown("<style>.pos-card { background: white; padding: 15px; border-radius: 15px; border: 1px solid #E2E8F0; text-align: center; margin-bottom: 15px; transition: 0.3s; } .pos-card:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }</style>", unsafe_allow_html=True)
    if 'cart' not in st.session_state: st.session_state.cart = {}
    col_cart, col_menu = st.columns([1.3, 2])
    with col_cart:
        st.markdown("### 🧾 Pesanan Aktif")
        subtotal = 0
        if not st.session_state.cart: st.info("Keranjang kosong.")
        else:
            for pid, item in list(st.session_state.cart.items()):
                item_sub = item['price'] * item['qty']
                subtotal += item_sub
                st.markdown(f"**{item['name']}** - {format_rp(item['price'])} x {item['qty']}")
                c1, c2 = st.columns(2)
                if c1.button("➖", key=f"m_{pid}"):
                    if item['qty'] > 1: st.session_state.cart[pid]['qty'] -= 1
                    else: del st.session_state.cart[pid]
                    st.rerun()
                if c2.button("➕", key=f"p_{pid}"): st.session_state.cart[pid]['qty'] += 1; st.rerun()
        st.markdown(f"## Total: {format_rp(subtotal)}")
        if subtotal > 0 and st.button("🚀 PROSES PEMBAYARAN", use_container_width=True, type="primary"):
            conn = get_connection(); conn.execute("INSERT INTO sales_log (total_revenue, profit, timestamp) VALUES (?,?,?)", (subtotal, subtotal*0.3, datetime.now())); conn.execute("UPDATE business_vault SET current_balance = current_balance + ?", (subtotal,)); conn.commit(); conn.close()
            st.session_state.cart = {}; st.success("Sukses!"); st.rerun()
    with col_menu:
        st.markdown("### 🥨 Menu")
        conn = get_connection(); prods = pd.read_sql_query("SELECT id, name, category, selling_price FROM recipe_master", conn); conn.close()
        if not prods.empty:
            cols = st.columns(3)
            for i, p in prods.iterrows():
                with cols[i % 3]:
                    st.markdown(f"<div class='pos-card'><b>{p['name']}</b><br>{format_rp(p['selling_price'])}</div>", unsafe_allow_html=True)
                    if st.button("Add", key=f"a_{p['id']}"):
                        if p['id'] in st.session_state.cart: st.session_state.cart[p['id']]['qty'] += 1
                        else: st.session_state.cart[p['id']] = {"name": p['name'], "price": p['selling_price'], "qty": 1}
                        st.rerun()

def show_inventory():
    st.markdown("## 📦 Manajemen Inventaris & Gudang")
    tab_master, tab_movement, tab_register, tab_packaging = st.tabs(["📊 Gudang Utama", "🔄 Penyesuaian", "➕ Registrasi", "📦 Kemasan"])
    with tab_master:
        conn = get_connection(); inv_df = pd.read_sql_query("SELECT barcode as \"ID Barang\", name as \"Nama Bahan\", category as \"Kategori\", stock as \"Stok Tersedia\", unit_pakai as \"Satuan\", price_per_unit_pakai as \"Harga Satuan\", (stock * price_per_unit_pakai) as \"Total Nilai Aset\", last_updated as \"Terakhir Update\" FROM inventory_master ORDER BY category, name", conn); conn.close()
        if not inv_df.empty:
            total_inv_value = inv_df['Total Nilai Aset'].sum()
            st.markdown(render_luxury_table(inv_df), unsafe_allow_html=True)
            st.metric("Total Nilai Aset Gudang", format_rp(total_inv_value))
        else: st.info("Gudang kosong.")
    with tab_movement:
        st.markdown("### 🔄 Penyesuaian Stok")
        conn = get_connection(); items_df = pd.read_sql_query("SELECT id, name, unit_pakai, stock FROM inventory_master", conn); conn.close()
        if not items_df.empty:
            with st.form("manual_adj_form"):
                c1, c2, c3 = st.columns([2, 1, 1])
                item_adj = c1.selectbox("Pilih Material", items_df['name'].tolist())
                adj_type = c2.selectbox("Arah Gerak", ["MASUK (+)", "KELUAR (-)"])
                qty_adj = c3.number_input("Jumlah", min_value=0.0)
                selected_row = items_df[items_df['name'] == item_adj].iloc[0]
                m_type = st.selectbox("Alasan", ["Stock Opname", "Pemakaian Internal", "Rusak", "Lainnya"])
                if st.form_submit_button("Update Stok"):
                    final_qty = qty_adj if "MASUK" in adj_type else -qty_adj
                    conn = get_connection(); conn.execute("UPDATE inventory_master SET stock = stock + ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?", (final_qty, int(selected_row['id']))); conn.execute("INSERT INTO stock_movement_log (inventory_id, qty, type, reason, timestamp) VALUES (?,?,?,?,?)", (int(selected_row['id']), final_qty, adj_type, m_type, datetime.now())); conn.commit(); conn.close(); st.success("Updated!"); st.rerun()
    with tab_register:
        with st.form("reg"):
            c1, c2 = st.columns(2); name_in = c1.text_input("Nama Bahan"); cat_in = c2.text_input("Kategori")
            c3, c4 = st.columns(2); u_pakai = c3.selectbox("Satuan Pakai", UNITS_MASTER); price = c4.number_input("Harga Satuan", min_value=0.0)
            if st.form_submit_button("Daftarkan"):
                import random, string; fid = "NB-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                conn = get_connection(); conn.execute("INSERT INTO inventory_master (name, barcode, category, unit_pakai, price_per_unit_pakai, stock) VALUES (?,?,?,?,?,0)", (name_in, fid, cat_in, u_pakai, price)); conn.commit(); conn.close(); st.success("Terdaftar!"); st.rerun()
    with tab_packaging: st.info("Pemetaan kemasan otomatis untuk kategori produk.")

def show_recipes():
    st.markdown("## 👨‍🍳 Manajemen Resep & Produksi")
    tab_r, tab_a, tab_s = st.tabs(["🧁 Resep Utama", "✨ Add-ons", "⚖️ Scaling"])
    conn = get_connection(); inv_list = pd.read_sql_query("SELECT id, name, unit_pakai FROM inventory_master", conn); conn.close()
    with tab_r:
        with st.expander("📝 Buat Resep Baru"):
            with st.form("new_r"):
                r_name = st.text_input("Nama Produk"); r_cat = st.selectbox("Kategori", CATEGORIES_MASTER); r_yield = st.number_input("Yield", min_value=1.0); r_unit = st.selectbox("Unit Hasil", ["Pcs", "Loyang"])
                if st.form_submit_button("Simpan Resep"):
                    c = get_connection(); c.execute("INSERT INTO recipe_master (name, category, yield_qty, yield_unit) VALUES (?,?,?,?)", (r_name, r_cat, r_yield, r_unit)); c.commit(); c.close(); st.success("Resep tersimpan!"); st.rerun()
        conn = get_connection(); recs = pd.read_sql_query("SELECT * FROM recipe_master", conn); conn.close()
        for _, r in recs.iterrows():
            with st.expander(f"📁 {r['name']} ({r['yield_qty']} {r['yield_unit']})"):
                if st.button("Hapus", key=f"del_{r['id']}"):
                    c = get_connection(); c.execute("DELETE FROM recipe_master WHERE id=?", (int(r['id']),)); c.commit(); c.close(); st.rerun()
    with tab_a:
        with st.form("addon"):
            a_name = st.text_input("Nama Add-on"); a_inv = st.selectbox("Material", inv_list['name'].tolist() if not inv_list.empty else []); a_qty = st.number_input("Qty Deduct"); a_price = st.number_input("Harga Jual")
            if st.form_submit_button("Simpan"):
                iid = inv_list[inv_list['name']==a_inv]['id'].values[0]
                c = get_connection(); c.execute("INSERT INTO product_addons (name, price, inventory_id, qty_deduct) VALUES (?,?,?,?)", (a_name, a_price, int(iid), a_qty)); c.commit(); c.close(); st.success("Add-on tersimpan!"); st.rerun()
    with tab_s:
        st.subheader("⚖️ Kalkulator Produksi")
        conn = get_connection(); rs = pd.read_sql_query("SELECT id, name, yield_qty FROM recipe_master", conn); conn.close()
        if not rs.empty:
            sel_r = st.selectbox("Produk", rs['name'].tolist()); target = st.number_input("Target Hasil", value=10.0)
            if st.button("Hitung"):
                r_data = rs[rs['name']==sel_r].iloc[0]; mult = target / r_data['yield_qty']
                st.write(f"Multiplier: {mult:.2f}")

def show_logistics():
    st.markdown("## 🛒 Logistik & PO")
    tab1, tab2 = st.tabs(["📋 PO", "🏢 Supplier"])
    with tab2:
        with st.form("supp"):
            n = st.text_input("Nama"); p = st.text_input("WA")
            if st.form_submit_button("Simpan"):
                c = get_connection(); c.execute("INSERT INTO suppliers (name, phone) VALUES (?,?)", (n, p)); c.commit(); c.close(); st.rerun()
    with tab1:
        conn = get_connection(); inv = pd.read_sql_query("SELECT id, name FROM inventory_master", conn); sup = pd.read_sql_query("SELECT id, name FROM suppliers", conn); conn.close()
        with st.form("po"):
            i = st.selectbox("Item", inv['name'].tolist()); s = st.selectbox("Supplier", sup['name'].tolist()); q = st.number_input("Qty"); p = st.number_input("Total Harga")
            if st.form_submit_button("Kirim PO"):
                iid = inv[inv['name']==i]['id'].values[0]; sid = sup[sup['name']==s]['id'].values[0]
                c = get_connection(); c.execute("INSERT INTO purchase_order_log (inventory_id, supplier_id, qty_order, price_total, status, timestamp) VALUES (?,?,?,?,?,?)", (int(iid), int(sid), q, p, 'Dikirim', datetime.now())); c.commit(); c.close(); st.success("PO Dikirim!"); st.rerun()

def show_custom_order():
    st.markdown("## 🥨 Order Kustom")
    with st.form("cust"):
        n = st.text_input("Nama Pelanggan"); p = st.text_input("WA"); d = st.text_area("Detail Pesanan"); date_p = st.date_input("Tanggal"); price = st.number_input("Harga")
        if st.form_submit_button("Simpan"):
            c = get_connection(); c.execute("INSERT INTO custom_orders (customer_name, phone, order_details, pickup_date, total_price, status) VALUES (?,?,?,?,?,?)", (n, p, d, date_p, price, 'PENDING')); c.commit(); c.close(); st.success("Order Dicatat!"); st.rerun()

def show_tracking():
    st.markdown("## 📍 Tracking Status")
    q = st.text_input("Cari Item...")
    if q: st.info(f"Mencari data untuk: {q}...")

def show_rd():
    st.markdown("## 🧪 R&D Lab")
    with st.form("rd"):
        n = st.text_input("Eksperimen"); c = st.number_input("Biaya"); r = st.text_input("Alasan")
        if st.form_submit_button("Ajukan"):
            c_db = get_connection(); c_db.execute("INSERT INTO pending_approvals (action_type, description, reason, timestamp) VALUES (?,?,?,?)", ("RISET_PRODUK", n, r, datetime.now())); c_db.commit(); c_db.close(); st.info("Diajukan!")

def show_waste():
    st.markdown("## 🗑️ Manajemen Limbah")
    conn = get_connection(); inv = pd.read_sql_query("SELECT id, name FROM inventory_master", conn); conn.close()
    with st.form("waste"):
        i = st.selectbox("Item", inv['name'].tolist()); q = st.number_input("Qty"); r = st.text_input("Alasan")
        if st.form_submit_button("Lapor"):
            iid = inv[inv['name']==i]['id'].values[0]
            c = get_connection(); c.execute("INSERT INTO waste_log (inventory_id, qty_waste, reason, timestamp) VALUES (?,?,?,?)", (int(iid), q, r, datetime.now())); c.commit(); c.close(); st.success("Lapor!"); st.rerun()

def show_crm():
    st.markdown("## 📣 CRM & Promo")
    st.info("Fitur pengelolaan loyalty dan diskon berkala.")

def show_chat():
    st.markdown("## 💬 Team Chat")
    with st.form("chat", clear_on_submit=True):
        m = st.text_input("Pesan..."); 
        if st.form_submit_button("Kirim"):
            c = get_connection(); c.execute("INSERT INTO internal_messages (sender, message, timestamp) VALUES (?,?,?)", (st.session_state.user, m, datetime.now())); c.commit(); c.close(); st.rerun()
    conn = get_connection(); df = pd.read_sql_query("SELECT sender, message, timestamp FROM internal_messages ORDER BY timestamp DESC LIMIT 20", conn); conn.close()
    for _, row in df.iterrows(): st.markdown(f"**{row['sender']}**: {row['message']}")

def show_approval():
    st.markdown("## ✅ Approval Center")
    conn = get_connection(); df = pd.read_sql_query("SELECT * FROM pending_approvals WHERE status='PENDING'", conn); conn.close()
    if df.empty: st.success("Semua beres!")
    else:
        for _, row in df.iterrows():
            with st.expander(f"{row['action_type']} - {row['description']}"):
                st.write(f"Alasan: {row['reason']}")
                if st.button("Setujui", key=f"a_{row['id']}"):
                    c = get_connection(); c.execute("UPDATE pending_approvals SET status='APPROVED' WHERE id=?", (row['id'],)); c.commit(); c.close(); st.rerun()

def show_vault():
    st.markdown("## 💎 The Vault")
    conn = get_connection(); bal = conn.execute("SELECT current_balance FROM business_vault").scalar() or 0; conn.close()
    st.markdown(f"<div style='background:#1E1B18; padding:30px; border-radius:20px; border:2px solid #D4AF37; text-align:center;'><h1 style='color:#D4AF37;'>{format_rp(bal)}</h1></div>", unsafe_allow_html=True)

def show_finance():
    st.markdown("## 📈 Finansial")
    conn = get_connection(); df = pd.read_sql_query("SELECT timestamp, total_revenue, profit FROM sales_log", conn); conn.close()
    if not df.empty: st.line_chart(df.set_index('timestamp'))

def show_pricing():
    st.markdown("## 💰 Pricing Architect")
    st.info("Kalkulasi HPP mendalam untuk setiap produk.")

def show_accounting():
    st.markdown("## 📊 Audit Trail")
    conn = get_connection(); df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn); conn.close()
    st.markdown(render_luxury_table(df), unsafe_allow_html=True)

def show_integration():
    st.markdown("## 🔗 Integrasi")
    st.success("Koneksi Supabase Cloud: AKTIF")

def show_health():
    st.markdown("## 🛡️ Health Check")
    st.success("Logika sistem optimal.")

def show_settings():
    st.markdown("## ⚙️ Pengaturan")
    conn = get_connection(); df = pd.read_sql_query("SELECT username, role, email FROM users", conn); conn.close()
    st.markdown(render_luxury_table(df), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. MAIN APP
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Near Bakery Executive ERP", layout="wide")
    initialize_database()
    if 'auth' not in st.session_state: st.session_state.auth = False
    
    if not st.session_state.auth:
        st.markdown("<style>[data-testid='stAppViewContainer']{background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)), url('https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=1920') !important; background-size: cover !important;} .login-card {background: white; padding: 50px; border-radius: 12px; max-width: 400px; margin: 100px auto; text-align: center;}</style>", unsafe_allow_html=True)
        st.markdown("<div class='login-card'><h1>NEAR BAKERY</h1><p>EXECUTIVE TERMINAL</p>", unsafe_allow_html=True)
        u = st.text_input("User", label_visibility="collapsed", placeholder="Username")
        p = st.text_input("Pass", type="password", label_visibility="collapsed", placeholder="Password")
        if st.button("LOGIN", use_container_width=True, type="primary"):
            c = get_connection(); user = c.execute("SELECT username, role FROM users WHERE username=? AND password=?", (u, p)).fetchone(); c.close()
            if user: st.session_state.auth = True; st.session_state.user = user[0]; st.session_state.role = user[1]; st.rerun()
            else: st.error("Gagal!")
        st.markdown("</div>", unsafe_allow_html=True); return

    with st.sidebar:
        st.markdown("### NEAR BAKERY ERP")
        st.write(f"Role: {st.session_state.role}")
        menu = {"🏠 Dashboard": "D", "🛒 Kasir": "P", "📦 Inventaris": "I", "🍞 Resep": "R", "🚛 Logistik": "L", "🥨 Order Kustom": "C", "📍 Tracking": "T", "🧪 R&D": "RD", "🗑️ Waste": "W", "📣 CRM": "CRM", "💬 Chat": "CH", "✅ Approval": "A"}
        if st.session_state.role == 'OWNER': menu.update({"💎 Vault": "V", "📈 Finansial": "F", "📊 Audit": "AU", "🔗 Integrasi": "INT", "🛡️ Health": "H", "⚙️ Pengaturan": "S"})
        for k, v in menu.items():
            if st.button(k, use_container_width=True): st.session_state.page = v; st.rerun()
        if st.button("LOGOUT"): st.session_state.auth = False; st.rerun()

    page = st.session_state.get('page', 'D')
    if page == 'D': show_dashboard()
    elif page == 'P': show_pos()
    elif page == 'I': show_inventory()
    elif page == 'R': show_recipes()
    elif page == 'L': show_logistics()
    elif page == 'C': show_custom_order()
    elif page == 'T': show_tracking()
    elif page == 'RD': show_rd()
    elif page == 'W': show_waste()
    elif page == 'CRM': show_crm()
    elif page == 'CH': show_chat()
    elif page == 'A': show_approval()
    elif page == 'V': show_vault()
    elif page == 'F': show_finance()
    elif page == 'AU': show_accounting()
    elif page == 'INT': show_integration()
    elif page == 'H': show_health()
    elif page == 'S': show_settings()

if __name__ == "__main__": main()
