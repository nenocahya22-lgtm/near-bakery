import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp, render_luxury_table, get_cogs_calculation

def show_custom_order():
    
    st.markdown("## 🥨 Custom Order Architect")
    st.info("Rakit pesanan khusus pelanggan dan hitung HPP secara cerdas.")
    
    # 1. Selection Mode
    mode = st.radio("Metode Rakit", ["Pilih dari Resep Dasar", "Rakit dari Bahan Mentah"], horizontal=True)
    
    conn = get_connection()
    inventory = pd.read_sql_query("SELECT id, name, price_per_unit_pakai, unit_pakai FROM inventory_master", conn)
    recipes = pd.read_sql_query("SELECT id, name FROM recipe_master", conn)
    
    if 'custom_items' not in st.session_state: st.session_state.custom_items = []
    
    c1, c2 = st.columns([1, 1])
    
    if not recipes.empty:
        with c1:
            st.subheader("🛠️ Tambah Bahan/Resep")
            if mode == "Pilih dari Resep Dasar":
                sel_r = st.selectbox("Pilih Resep", recipes['name'].tolist())
                if sel_r:
                    r_id = recipes[recipes['name'] == sel_r]['id'].values[0]
                    if st.button("➕ Tambahkan Resep ke Custom", width="stretch"):
                        cogs_res = get_cogs_calculation(r_id)
                        cost = cogs_res['total_hpp']
                        st.session_state.custom_items.append({"name": f"BASE: {sel_r}", "cost": cost, "qty": 1})
            else:
                if not inventory.empty:
                    sel_i = st.selectbox("Pilih Bahan Mentah", inventory['name'].tolist())
                    i_row = inventory[inventory['name'] == sel_i].iloc[0]
                    qty = st.number_input(f"Jumlah ({i_row['unit_pakai']})", min_value=0.01, value=1.0)
                    if st.button("➕ Tambahkan Bahan ke Custom", width="stretch"):
                        cost = i_row['price_per_unit_pakai'] * qty
                        st.session_state.custom_items.append({"name": sel_i, "cost": cost, "qty": qty})
                else:
                    st.warning("Belum ada bahan baku di gudang.")
    else:
        st.warning("Silakan buat resep dasar terlebih dahulu di menu RESEP & PRODUKSI.")
                
    with c2:
        st.subheader("📋 Ringkasan HPP Custom")
        if not st.session_state.custom_items:
            st.write("Belum ada bahan yang ditambahkan.")
        else:
            total_hpp = 0
            for idx, item in enumerate(st.session_state.custom_items):
                st.markdown(f"**{item['name']}** - {format_rp(item['cost'])}")
                total_hpp += item['cost']
                if st.button("🗑️", key=f"del_c_{idx}"):
                    st.session_state.custom_items.pop(idx)
                    st.rerun()
            
            st.write("---")
            st.markdown(f"### TOTAL HPP CUSTOM: <span style='color: #FF6B35;'>{format_rp(total_hpp)}</span>", unsafe_allow_html=True)
            
            # Smart Pricing Suggestion
            margin = st.slider("Margin Keuntungan (%)", 50, 300, 100)
            suggested_price = total_hpp * (1 + margin/100)
            st.success(f"Harga Jual Rekomendasi: {format_rp(suggested_price)}")
            
            with st.form("custom_order_save"):
                st.markdown("#### 👤 Data Pemesan & Pengambilan")
                cust_name = st.text_input("Nama Pelanggan")
                cust_phone = st.text_input("No. WhatsApp")
                pickup_date = st.date_input("Tanggal Pengambilan (Jatuh Tempo)")
                order_notes = st.text_area("Catatan Khusus (Misal: Kurangi gula, tulisan di kue)")
                
                if st.form_submit_button("💾 SIMPAN SEBAGAI PESANAN KHUSUS", type="primary", use_container_width=True):
                    if cust_name and cust_phone:
                        details = ", ".join([f"{i['name']} (x{i['qty']})" for i in st.session_state.custom_items])
                        c = get_connection()
                        c.execute("""
                            INSERT INTO custom_orders (customer_name, phone, order_details, pickup_date, total_price, down_payment, notes, status)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (cust_name, cust_phone, details, pickup_date, suggested_price, 0, order_notes, 'PENDING'))
                        c.commit(); c.close()
                        st.session_state.custom_items = []
                        st.balloons()
                        st.success(f"Pesanan Custom {cust_name} berhasil dicatat! Jatuh tempo: {pickup_date}")
                        st.rerun()
                    else:
                        st.error("Lengkapi data pelanggan!")
    
    conn.close()
    
