# --- NEAR BAKERY & CO. EXECUTIVE ERP UNIFIED TERMINAL ---
# Version: 2.0 (Unified Single-File Edition)
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
# 1. DATABASE ENGINE (INTEGRATED)
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
        self._last_id = None
        self._current_result = None
    def cursor(self): return PostgresCursor(self)
    def execute(self, query, params=None):
        try:
            if isinstance(query, str):
                query = query.replace('?', '%s')
                if params:
                    if not isinstance(params, (list, tuple)): params = (params,)
                    res = self.conn.execute(text(query), params)
                else:
                    res = self.conn.execute(text(query))
                self._current_result = res
                if res.returns_rows:
                    self.description = [(col, None, None, None, None, None, None) for col in res.keys()]
                else: self.description = None
                self.rowcount = res.rowcount
                return res
            return self.conn.execute(query, params)
        except Exception as e:
            st.error(f"DB Exec Error: {e}\nQuery: {query}")
            raise e
    def fetchone(self):
        if self._current_result:
            row = self._current_result.fetchone()
            return row._asdict().values() if row and hasattr(row, '_asdict') else row
        return None
    def fetchall(self):
        if self._current_result:
            rows = self._current_result.fetchall()
            return [tuple(row._asdict().values()) for row in rows] if rows and hasattr(rows[0], '_asdict') else rows
        return []
    @property
    def lastrowid(self):
        res = self.conn.execute(text("SELECT lastval()"))
        return res.scalar()
    def commit(self): pass # SQLAlchemy handles via context
    def close(self): pass

def get_connection():
    db = SessionLocal()
    return PostgresCompat(db)

def init_db():
    conn = get_connection()
    try:
        # Core Tables
        conn.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, email TEXT, permissions TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS inventory_master (id SERIAL PRIMARY KEY, name TEXT, category TEXT, stock FLOAT, unit_beli TEXT, unit_pakai TEXT, price_per_unit_beli FLOAT, price_per_unit_pakai FLOAT, barcode TEXT UNIQUE, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS recipe_master (id SERIAL PRIMARY KEY, name TEXT, barcode TEXT UNIQUE, category TEXT, yield_qty FLOAT, yield_unit TEXT, selling_price FLOAT DEFAULT 0, discount_pct FLOAT DEFAULT 0, image_path TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS recipe_ingredients (id SERIAL PRIMARY KEY, recipe_id INTEGER, inventory_id INTEGER, qty_pakai FLOAT, unit TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS sales_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, total_revenue FLOAT, total_hpp FLOAT DEFAULT 0, profit FLOAT DEFAULT 0, payment_method TEXT, customer_id INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS stock_movement_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, inventory_id INTEGER, qty FLOAT, type TEXT, reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS custom_orders (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, customer_name TEXT, phone TEXT, order_details TEXT, pickup_date DATE, total_price FLOAT, down_payment FLOAT, notes TEXT, status TEXT DEFAULT 'PENDING')")
        conn.execute("CREATE TABLE IF NOT EXISTS finance_config (config_key TEXT PRIMARY KEY, config_value FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS business_vault (id SERIAL PRIMARY KEY, current_balance FLOAT DEFAULT 0, last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS pending_approvals (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_requester TEXT, action_type TEXT, description TEXT, data_payload TEXT, reason TEXT, status TEXT DEFAULT 'PENDING')")
        conn.execute("CREATE TABLE IF NOT EXISTS packaging_bundles (id SERIAL PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS packaging_bundle_items (id SERIAL PRIMARY KEY, bundle_id INTEGER, inventory_id INTEGER, qty FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS category_packaging_map (category_name TEXT PRIMARY KEY, bundle_id INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS product_addons (id SERIAL PRIMARY KEY, name TEXT, price FLOAT, inventory_id INTEGER, qty_deduct FLOAT)")
        conn.execute("CREATE TABLE IF NOT EXISTS suppliers (id SERIAL PRIMARY KEY, name TEXT, contact_person TEXT, phone TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS purchase_order_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, inventory_id INTEGER, supplier_id INTEGER, qty_order FLOAT, unit_order TEXT, price_total FLOAT, status TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS waste_log (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, inventory_id INTEGER, qty_waste FLOAT, loss_value FLOAT, reason TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS budget_usage_log (id SERIAL PRIMARY KEY, room_name TEXT, amount FLOAT, description TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS budget_allocation (room_name TEXT PRIMARY KEY, target_pct FLOAT)")
        
        # MIGRATIONS
        conn.execute("ALTER TABLE inventory_master ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        conn.execute("ALTER TABLE recipe_ingredients ADD COLUMN IF NOT EXISTS unit TEXT")
        conn.execute("ALTER TABLE sales_log ADD COLUMN IF NOT EXISTS total_hpp FLOAT DEFAULT 0")
        conn.execute("ALTER TABLE sales_log ADD COLUMN IF NOT EXISTS profit FLOAT DEFAULT 0")
        conn.execute("ALTER TABLE sales_log ADD COLUMN IF NOT EXISTS payment_method TEXT")
        
        # Default Data
        if not conn.execute("SELECT * FROM users WHERE username='owner'").fetchone():
            conn.execute("INSERT INTO users (username, password, role) VALUES ('owner', 'near123', 'OWNER')")
        if not conn.execute("SELECT * FROM users WHERE username='staff'").fetchone():
            conn.execute("INSERT INTO users (username, password, role, permissions) VALUES ('staff', 'staff123', 'STAFF', 'Dashboard,POS,Inventory')")
        if not conn.execute("SELECT * FROM business_vault").fetchone():
            conn.execute("INSERT INTO business_vault (current_balance) VALUES (0)")
        
        conn.conn.commit()
    except Exception as e:
        print(f"Init DB Error: {e}")
    finally: conn.close()

# -----------------------------------------------------------------------------
# 2. UTILITIES (INTEGRATED)
# -----------------------------------------------------------------------------
def format_rp(value): return f"Rp {value:,.0f}"

UNITS_MASTER = ["Kilogram (Kg)", "Gram (gr)", "Liter (L)", "Mililiter (ml)", "Pcs", "Karung", "Karton", "Botol", "Pack", "Butir", "Ikat", "Sdm", "Sdt", "Slice", "Bungkus"]
CATEGORIES_MASTER = ["BAKERY", "DRINK"]

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
    ings = conn.execute("SELECT inv.name, ri.qty_pakai, ri.unit, inv.unit_pakai, inv.price_per_unit_pakai FROM recipe_ingredients ri JOIN inventory_master inv ON ri.inventory_id = inv.id WHERE ri.recipe_id = ?", (recipe_id,)).fetchall()
    conn.close()
    total_hpp = 0
    for name, r_qty, r_unit, i_unit, i_price in ings:
        total_hpp += convert_qty(r_qty, r_unit, i_unit) * i_price
    if include_buffer:
        c = get_connection(); res_b = c.execute("SELECT config_value FROM finance_config WHERE config_key = 'cogs_buffer_pct'").fetchone(); c.close()
        total_hpp *= (1 + (res_b[0]/100 if res_b else 0))
    return {"total_hpp": total_hpp, "hpp_per_unit": total_hpp / y_qty if y_qty > 0 else 0, "yield_qty": y_qty}

def get_dynamic_selling_price(recipe_id):
    c = get_connection()
    res_m = c.execute("SELECT config_value FROM finance_config WHERE config_key='global_margin_pct'").fetchone()
    c.close()
    margin = res_m[0] if res_m else 100.0
    cogs = get_cogs_calculation(recipe_id, include_buffer=True)
    return cogs['hpp_per_unit'] * (1 + margin/100)

def render_luxury_table(df):
    if df.empty: return "<div style='text-align: center; padding: 40px; color: #94A3B8; background: white; border-radius: 12px; border: 1px dashed #E2E8F0;'>No data.</div>"
    headers = [str(col).replace("_", " ").upper() for col in df.columns]
    html = '<div style="overflow-x: auto; border: 1px solid #E2E8F0; border-radius: 8px; background: white; margin: 15px 0;"><table style="width: 100%; border-collapse: collapse; font-family: \'Inter\', sans-serif;"><thead><tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">'
    for col in headers: html += f"<th style='padding: 12px 15px; text-align: left; color: #64748B; font-weight: 600; font-size: 11px; text-transform: uppercase;'>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr style='border-bottom: 1px solid #F1F5F9;'>"
        for col_name, val in zip(df.columns, row):
            display_val, cell_style = val, "padding: 10px 15px; color: #334155; font-size: 13px;"
            if str(val).upper() in ['LUNAS', 'PAID', 'SUCCESS', 'ACTIVE', 'DONE']: display_val = f"<span style='color: #059669; font-weight: 600;'>● {val}</span>"
            elif str(val).upper() in ['PENDING', 'WAITING']: display_val = f"<span style='color: #D97706; font-weight: 600;'>● {val}</span>"
            elif isinstance(val, (int, float)) and val > 1000 and "QTY" not in str(col_name).upper() and "ID" not in str(col_name).upper():
                display_val, cell_style = format_rp(val), cell_style + " color: #0F172A; font-weight: 500;"
            html += f"<td style='{cell_style}'>{display_val}</td>"
        html += "</tr>"
    return html + "</tbody></table></div>"

# -----------------------------------------------------------------------------
# 3. MODULES (INTEGRATED)
# -----------------------------------------------------------------------------

# [DASHBOARD]
def show_dashboard():
    conn = get_connection()
    total_inv = conn.execute("SELECT SUM(stock * price_per_unit_pakai) FROM inventory_master").fetchone()[0] or 0
    total_rev = conn.execute("SELECT SUM(total_revenue) FROM sales_log").fetchone()[0] or 0
    total_prof = conn.execute("SELECT SUM(profit) FROM sales_log").fetchone()[0] or 0
    pending_orders = conn.execute("SELECT COUNT(*) FROM custom_orders WHERE status = 'PENDING'").fetchone()[0] or 0
    conn.close()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Nilai Inventaris", format_rp(total_inv))
    c2.metric("💰 Total Omzet", format_rp(total_rev))
    c3.metric("📈 Estimasi Laba", format_rp(total_prof))
    c4.metric("🥨 Order Pending", pending_orders)
    
    st.write("---")
    st.subheader("📊 Analisis Penjualan & Performa")
    # Add chart logic if needed

# [INVENTORY]
def show_inventory():
    st.markdown("### 📦 Inventaris Pusat & Gudang")
    tab_status, tab_adj, tab_register = st.tabs(["📋 Status Stok Real-Time", "⚙️ Penyesuaian Stok", "➕ Registrasi Material Baru"])
    
    with tab_status:
        conn = get_connection()
        inv_df = pd.read_sql_query("""
            SELECT barcode as "ID Barang", name as "Nama Bahan", category as "Kategori", 
                   stock as "Stok Tersedia", unit_pakai as "Satuan",
                   price_per_unit_pakai as "Harga Satuan",
                   (stock * price_per_unit_pakai) as "Total Nilai Aset",
                   last_updated as "Terakhir Update"
            FROM inventory_master
            ORDER BY category, name
        """, conn.conn)
        conn.close()
        
        if not inv_df.empty:
            dupes = inv_df[inv_df.duplicated('Nama Bahan')]['Nama Bahan'].unique()
            if len(dupes) > 0: st.warning(f"⚠️ **PERHATIAN: Ada data ganda!** ({', '.join(dupes)})")
            
            total_inv_value = inv_df['Total Nilai Aset'].sum()
            display_df = inv_df.copy()
            display_df['Harga Satuan'] = display_df['Harga Satuan'].apply(format_rp)
            display_df['Total Nilai Aset'] = display_df['Total Nilai Aset'].apply(format_rp)
            
            st.markdown(render_luxury_table(display_df), unsafe_allow_html=True)
            st.metric("Total Nilai Aset Gudang", format_rp(total_inv_value))
    
    with tab_adj:
        st.subheader("⚙️ Penyesuaian Stok Manual")
        conn = get_connection()
        items = pd.read_sql_query("SELECT id, name, stock, unit_pakai FROM inventory_master", conn.conn)
        conn.close()
        if not items.empty:
            sel_item = st.selectbox("Pilih Material", items['name'].tolist())
            row = items[items['name'] == sel_item].iloc[0]
            c1, c2 = st.columns(2)
            adj_type = c1.radio("Jenis Penyesuaian", ["STOK MASUK (+)", "STOK KELUAR (-)"])
            qty_adj = c2.number_input(f"Jumlah ({row['unit_pakai']})", min_value=0.0)
            reason = st.text_input("Alasan / Keterangan")
            if st.button("UPDATE STOK", use_container_width=True):
                delta = qty_adj if "MASUK" in adj_type else -qty_adj
                c = get_connection()
                c.execute("UPDATE inventory_master SET stock = stock + ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?", (delta, int(row['id'])))
                c.execute("INSERT INTO stock_movement_log (timestamp, inventory_id, qty, type, reason) VALUES (?,?,?,?,?)",
                         (datetime.now(), int(row['id']), delta, adj_type, reason))
                c.conn.commit(); c.close(); st.success("Stok Diperbarui!"); st.rerun()
        
    with tab_register:
        st.markdown("#### ✨ Registrasi Material & Kalkulator HPP")
        c1, c2, c3 = st.columns(3)
        name_in = c1.text_input("Nama Bahan")
        cat_in = c3.selectbox("Kategori", ["Bahan Baku", "Kemasan", "Lainnya"])
        
        c1b, c2b, c3b = st.columns(3)
        u_beli_in = c1b.selectbox("Satuan Beli", UNITS_MASTER)
        use_conv = st.checkbox("Gunakan Konversi (Grosir ke Ecer)?", value=False)
        if use_conv:
            u_pakai_in = c2b.selectbox("Satuan Pakai (Ecer)", UNITS_MASTER)
            isi = c3b.number_input("Isi per Satuan Beli", min_value=0.001, value=1.0)
        else:
            u_pakai_in, isi = u_beli_in, 1.0
            
        c1c, c2c = st.columns(2)
        total_bayar = c1c.number_input("Total Harga di Nota (Rp)", min_value=0.0, step=500.0)
        jumlah_masuk = c2c.number_input(f"Total Jumlah {u_beli_in} yang Diterima", min_value=0.001, value=1.0)
        
        price_per_use = total_bayar / (jumlah_masuk * isi) if jumlah_masuk * isi > 0 else 0
        st.markdown(f"""
        <div style='background: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin: 15px 0;'>
            <p style='margin: 0; color: #64748B; font-size: 0.8rem; font-weight: 700;'>📊 HASIL HITUNG HPP OTOMATIS:</p>
            <h3 style='margin: 10px 0; color: #0F172A;'>{format_rp(price_per_use)} <span style='font-size: 0.9rem; font-weight: 400;'>per {u_pakai_in}</span></h3>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("KONFIRMASI PENDAFTARAN", use_container_width=True, type="primary"):
            if name_in:
                fid = "NB-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                c = get_connection()
                try:
                    c.execute("INSERT INTO inventory_master (name, barcode, category, stock, unit_beli, unit_pakai, price_per_unit_pakai) VALUES (?,?,?,?,?,?,?)",
                             (name_in, fid, cat_in, jumlah_masuk * isi, u_beli_in, u_pakai_in, price_per_use))
                    c.conn.commit(); st.toast(f"✅ {name_in} Tersimpan!"); st.rerun()
                except Exception as e: st.error(e)
                finally: c.close()

# [POS / KASIR]
def show_pos():
    st.markdown("### 🖥️ Kasir Terminal")
    if 'cart' not in st.session_state: st.session_state.cart = {}
    col_cart, col_menu = st.columns([1.2, 2])
    
    with col_cart:
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
            if st.button("PROSES BAYAR & CETAK", use_container_width=True, type="primary"):
                c = get_connection()
                c.execute("INSERT INTO sales_log (total_revenue, profit, payment_method) VALUES (?,?,?)", (subtotal, subtotal*0.3, pay_method))
                c.conn.commit(); c.close()
                st.session_state.cart = {}; st.balloons(); st.success("Transaksi Berhasil!"); st.rerun()
            
    with col_menu:
        st.markdown("#### 🥐 Menu Produk")
        search = st.text_input("🔍 Cari...", placeholder="Ketik nama roti...")
        conn = get_connection()
        prods = pd.read_sql_query("SELECT id, name, selling_price, category FROM recipe_master", conn.conn)
        conn.close()
        
        if not prods.empty:
            filtered = prods[prods['name'].str.contains(search, case=False)]
            cols = st.columns(3)
            for idx, p in filtered.reset_index().iterrows():
                with cols[idx % 3]:
                    st.markdown(f"""
                    <div style='background: white; padding: 10px; border-radius: 10px; border: 1px solid #F1F5F9; text-align: center; margin-bottom: 10px;'>
                        <small style='color: #3B82F6;'>{p['category']}</small>
                        <div style='font-weight: bold;'>{p['name']}</div>
                        <div style='color: #1E293B;'>{format_rp(p['selling_price'])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("TAMBAH", key=f"add_{p['id']}", use_container_width=True):
                        pid = p['id']
                        if pid in st.session_state.cart: st.session_state.cart[pid]['qty'] += 1
                        else: st.session_state.cart[pid] = {'name': p['name'], 'price': p['selling_price'], 'qty': 1}
                        st.rerun()

# [PURCHASE]
def show_purchase():
    st.markdown("### 🛒 Logistik & Pengadaan (Purchase Order)")
    tab_po, tab_supplier = st.tabs(["📋 Pesanan Pembelian (PO)", "🏢 Manajemen Supplier"])
    
    with tab_supplier:
        with st.expander("➕ Tambah Supplier Baru"):
            s_name = st.text_input("Nama Supplier")
            s_phone = st.text_input("Nomor WhatsApp (628...)")
            if st.button("SIMPAN SUPPLIER"):
                if s_name and s_phone:
                    c = get_connection(); c.execute("INSERT INTO suppliers (name, phone) VALUES (?,?)", (s_name, s_phone)); c.conn.commit(); c.close(); st.success("Supplier Tersimpan!"); st.rerun()
        
        conn = get_connection(); supps = pd.read_sql_query("SELECT name as \"Supplier\", phone as \"WA\" FROM suppliers", conn.conn); conn.close()
        st.markdown(render_luxury_table(supps), unsafe_allow_html=True)

    with tab_po:
        conn = get_connection()
        inv_items = pd.read_sql_query("SELECT id, name FROM inventory_master", conn.conn)
        suppliers = pd.read_sql_query("SELECT id, name, phone FROM suppliers", conn.conn)
        conn.close()
        
        with st.expander("📝 Buat PO Baru"):
            if inv_items.empty or suppliers.empty: st.warning("Isi data Gudang & Supplier dulu.")
            else:
                c1, c2 = st.columns(2)
                item = c1.selectbox("Material", inv_items['name'].tolist())
                supp = c2.selectbox("Supplier", suppliers['name'].tolist())
                qty = st.number_input("Jumlah Pesanan", min_value=1.0)
                price = st.number_input("Estimasi Total Harga (Rp)", min_value=0.0)
                if st.button("KONFIRMASI & SIMPAN PO"):
                    iid = inv_items[inv_items['name']==item]['id'].values[0]
                    sid = suppliers[suppliers['name']==supp]['id'].values[0]
                    s_phone = suppliers[suppliers['name']==supp]['phone'].values[0]
                    c = get_connection()
                    c.execute("INSERT INTO purchase_order_log (timestamp, inventory_id, supplier_id, qty_order, price_total, status) VALUES (?,?,?,?,?)",
                             (datetime.now(), int(iid), int(sid), qty, price, 'Dikirim'))
                    c.conn.commit(); c.close()
                    msg = f"*PO NEAR BAKERY*\n\nMaterial: {item}\nQty: {qty}\nTotal: {format_rp(price)}"
                    wa_link = f"https://wa.me/{s_phone}?text={urllib.parse.quote(msg)}"
                    st.session_state.last_wa_link = wa_link
                    st.toast("✅ PO Tercatat!"); st.rerun()
        
        if 'last_wa_link' in st.session_state:
            st.markdown(f'<a href="{st.session_state.last_wa_link}" target="_blank"><button style="background: #25D366; color: white; border: none; padding: 15px; border-radius: 8px; width: 100%; font-weight: bold;">📲 KIRIM PO KE WHATSAPP</button></a>', unsafe_allow_html=True)
            if st.button("Tutup Link"): del st.session_state.last_wa_link; st.rerun()

# [RECIPE]
def show_recipes():
    st.markdown("### 🍞 Manajemen Resep & Produksi")
    with st.expander("📝 Buat Resep Baru"):
        r_name = st.text_input("Nama Produk")
        r_yield = st.number_input("Hasil Produksi", min_value=1.0, value=1.0)
        r_price = st.number_input("Harga Jual (Rp)", min_value=0.0)
        
        st.write("---")
        st.markdown("**Komposisi Bahan**")
        conn = get_connection(); inv = pd.read_sql_query("SELECT id, name, unit_pakai FROM inventory_master", conn.conn); conn.close()
        
        if 'unified_recipe_rows' not in st.session_state: st.session_state.unified_recipe_rows = 1
        ings_data = []
        for i in range(st.session_state.unified_recipe_rows):
            ca, cb = st.columns([3, 1])
            ing = ca.selectbox(f"Bahan {i+1}", inv['name'].tolist(), key=f"u_ing_{i}")
            qty = cb.number_input(f"Qty", min_value=0.0, key=f"u_qty_{i}")
            iid = inv[inv['name']==ing]['id'].values[0]
            unit = inv[inv['name']==ing]['unit_pakai'].values[0]
            ings_data.append((iid, qty, unit))
            
        c_b1, c_b2, c_b3 = st.columns(3)
        if c_b1.button("➕ TAMBAH BARIS"): st.session_state.unified_recipe_rows += 1; st.rerun()
        if c_b2.button("❌ KURANGI BARIS"): 
            if st.session_state.unified_recipe_rows > 1: st.session_state.unified_recipe_rows -= 1; st.rerun()
        
        if c_b3.button("✨ SIMPAN RESEP", type="primary", use_container_width=True):
            if r_name:
                c = get_connection()
                c.execute("INSERT INTO recipe_master (name, yield_qty, selling_price) VALUES (?,?,?)", (r_name, r_yield, r_price))
                rid = c.lastrowid
                for iid, iqty, iunit in ings_data:
                    c.execute("INSERT INTO recipe_ingredients (recipe_id, inventory_id, qty_pakai, unit) VALUES (?,?,?,?)", (rid, iid, iqty, iunit))
                c.conn.commit(); c.close(); st.session_state.unified_recipe_rows = 1; st.success("Resep Tersimpan!"); st.rerun()

# [FINANCE]
def show_finance():
    st.markdown("### 💰 Strategi Finansial & Profit")
    tab_profit, tab_vault, tab_budget = st.tabs(["📈 Analisis Laba/Rugi", "💎 The Vault", "📊 Alokasi Anggaran"])
    
    with tab_vault:
        conn = get_connection(); balance = conn.execute("SELECT current_balance FROM business_vault").fetchone()[0]; conn.close()
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0F172A, #1E293B); padding: 40px; border-radius: 20px; text-align: center; color: white;'>
            <p style='margin: 0; font-size: 0.9rem; font-weight: 600; color: #94A3B8;'>SALDO BUSINESS VAULT SAAT INI</p>
            <h1 style='margin: 10px 0; font-size: 3.5rem; color: #FACC15;'>{format_rp(balance)}</h1>
        </div>
        """, unsafe_allow_html=True)

    with tab_profit:
        conn = get_connection()
        sales = pd.read_sql_query("SELECT timestamp, total_revenue as \"Omzet\", profit as \"Laba\" FROM sales_log ORDER BY timestamp DESC LIMIT 10", conn.conn)
        conn.close()
        st.markdown("#### 10 Transaksi Terakhir")
        st.markdown(render_luxury_table(sales), unsafe_allow_html=True)

# [APPROVAL]
def show_approval():
    st.markdown("### ✅ Pusat Approval Eksekutif")
    conn = get_connection()
    pendings = pd.read_sql_query("SELECT * FROM pending_approvals WHERE status = 'PENDING'", conn.conn)
    conn.close()
    
    if pendings.empty: st.info("Tidak ada permintaan approval tertunda.")
    else:
        for idx, row in pendings.iterrows():
            with st.container():
                st.markdown(f"**Permintaan dari:** {row['user_requester']} | **Aksi:** {row['action_type']}")
                st.write(f"Deskripsi: {row['description']}")
                st.write(f"Alasan: {row['reason']}")
                c1, c2 = st.columns(2)
                if c1.button("SETUJUI", key=f"app_{row['id']}"):
                    c = get_connection(); c.execute("UPDATE pending_approvals SET status = 'APPROVED' WHERE id = ?", (int(row['id']),)); c.conn.commit(); c.close()
                    st.success("Disetujui!"); st.rerun()
                if c2.button("TOLAK", key=f"rej_{row['id']}"):
                    c = get_connection(); c.execute("UPDATE pending_approvals SET status = 'REJECTED' WHERE id = ?", (int(row['id']),)); c.conn.commit(); c.close()
                    st.error("Ditolak!"); st.rerun()
                st.write("---")

# -----------------------------------------------------------------------------
# 4. MAIN NAVIGATION & UI
# -----------------------------------------------------------------------------
def main():
    init_db()
    st.set_page_config(page_title="Near Bakery & Co.", layout="wide")
    
    # CSS MASTER
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;800&family=Inter:wght@400;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC !important; }
    h1, h2, h3 { font-family: 'Outfit', sans-serif !important; color: #0F172A !important; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] .stButton button { background: transparent !important; color: #94A3B8 !important; border: none !important; text-align: left !important; font-weight: 600 !important; }
    [data-testid="stSidebar"] .stButton button:hover { color: white !important; background: rgba(255,255,255,0.05) !important; }
    .stButton>button { border-radius: 8px !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)
    
    if 'auth' not in st.session_state: st.session_state.auth = False
    
    if not st.session_state.auth:
        st.title("NEAR BAKERY & CO. LOGIN")
        u = st.text_input("Username"); p = st.text_input("Password", type="password")
        if st.button("LOGIN", use_container_width=True):
            if u == "owner" and p == "near123":
                st.session_state.auth = True; st.session_state.user = u; st.session_state.role = "OWNER"; st.rerun()
            else: st.error("Akses Ditolak")
        return

    # Sidebar Navigation
    with st.sidebar:
        st.markdown("### 🥨 NEAR BAKERY ERP")
        nav = {
            "🏠 Dashboard": "Home",
            "--- OPERASIONAL ---": "SEP1",
            "🖥️ Kasir Terminal": "POS",
            "📦 Inventaris Pusat": "Inventory",
            "🍞 Resep & Produksi": "Recipe",
            "🛒 Logistik & PO": "Purchase",
            "--- EKSEKUTIF ---": "SEP2",
            "💰 Keuangan": "Finance"
        }
        for label, page in nav.items():
            if label.startswith("---"): st.markdown(f"<small style='color:gray'>{label}</small>", unsafe_allow_html=True)
            elif st.button(label, use_container_width=True): st.session_state.page = page; st.rerun()
        
        st.write("---")
        if st.button("LOGOUT"): st.session_state.auth = False; st.rerun()

    # Page Router
    p = st.session_state.get('page', 'Home')
    if p == 'Home': show_dashboard()
    elif p == 'Inventory': show_inventory()
    elif p == 'POS': show_pos()
    elif p == 'Recipe': show_recipes()
    elif p == 'Purchase': show_purchase()
    elif p == 'Finance': show_finance()

if __name__ == "__main__":
    main()
