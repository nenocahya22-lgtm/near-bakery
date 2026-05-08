import streamlit as st
import pandas as pd
from datetime import datetime
from database_engine import get_connection
from utils import format_rp, UNITS_MASTER, render_luxury_table
import os
import json

def show_waste():
    
    st.markdown("## 🗑️ Manajemen Waste & Kerugian")
    
    tab_bahan, tab_alat = st.tabs(["🍞 Waste Bahan Baku", "🛠️ Waste Peralatan (Asset)"])
    
    # --- TAB 1: WASTE BAHAN BAKU ---
    with tab_bahan:
        st.subheader("🍞 Kerugian Bahan & Produk")
        with st.expander("➕ Ajukan Waste Bahan Baru"):
            inv_df = pd.read_sql_query("SELECT id, name, price_per_unit_pakai, unit_pakai FROM inventory_master", get_connection())
            if not inv_df.empty:
                with st.form("waste_bahan_form"):
                    item_name = st.selectbox("Pilih Bahan/Produk", inv_df['name'].tolist())
                    qty = st.number_input("Jumlah Waste", min_value=0.01)
                    reason = st.text_input("Alasan (Misal: Expired, Gosong)")
                    if st.form_submit_button("AJUKAN WASTE KE OWNER"):
                        row = inv_df[inv_df['name'] == item_name].iloc[0]
                        loss = qty * row['price_per_unit_pakai']
                        payload = {"inv_id": int(row['id']), "item_name": item_name, "qty": qty, "loss": loss}
                        
                        c = get_connection()
                        c.execute("""
                            INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason)
                            VALUES (?,?,?,?,?,?)
                        """, (datetime.now(), st.session_state.user, "CATAT_WASTE_BAHAN", 
                             f"Waste {item_name}: {qty} {row['unit_pakai']} (Nilai: {format_rp(loss)})", 
                             json.dumps(payload), reason))
                        c.commit(); c.close(); st.info("Pengajuan Waste terkirim ke Owner."); st.rerun()
            else: st.info("Input bahan di Inventaris dulu.")

        st.write("---")
        conn = get_connection()
        history = pd.read_sql_query("""
            SELECT w.id, w.timestamp, i.name as "Item", w.qty_waste as "Qty", i.unit_pakai as "Satuan", w.loss_value as "Kerugian", w.reason as "Alasan"
            FROM waste_log w JOIN inventory_master i ON w.inventory_id = i.id ORDER BY w.timestamp DESC
        """, conn)
        conn.close()
        if not history.empty:
            history['Kerugian'] = history['Kerugian'].apply(format_rp)
            st.markdown(render_luxury_table(history), unsafe_allow_html=True)

    # --- TAB 2: WASTE PERALATAN ---
    with tab_alat:
        st.subheader("🛠️ Kerusakan Alat & Inventaris")
        with st.expander("➕ Ajukan Kerusakan Alat"):
            with st.form("waste_alat_form"):
                a_name = st.text_input("Nama Alat")
                a_reason = st.text_input("Penyebab Kerusakan")
                a_photo = st.file_uploader("📸 Unggah Foto Bukti Kerusakan", type=["jpg", "png", "jpeg"])
                
                if st.form_submit_button("AJUKAN KERUSAKAN ALAT KE OWNER"):
                    if a_name:
                        img_path = None
                        if a_photo:
                            if not os.path.exists("uploads"): os.makedirs("uploads")
                            img_path = f"uploads/waste_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            with open(img_path, "wb") as f: f.write(a_photo.getbuffer())
                        
                        payload = {"asset_name": a_name, "loss": 0, "image": img_path}
                        c = get_connection()
                        c.execute("""
                            INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason)
                            VALUES (?,?,?,?,?,?)
                        """, (datetime.now(), st.session_state.user, "CATAT_WASTE_ALAT", 
                             f"Kerusakan Alat: {a_name}", 
                             json.dumps(payload), a_reason))
                        c.commit(); c.close(); st.info("Pengajuan Kerusakan Alat terkirim ke Owner."); st.rerun()

        st.write("---")
        conn = get_connection()
        a_history = pd.read_sql_query("SELECT timestamp, asset_name as \"Alat\", reason as \"Penyebab\", image_path FROM asset_waste_log ORDER BY timestamp DESC", conn)
        conn.close()
        if not a_history.empty:
            st.markdown(render_luxury_table(a_history.drop(columns=['image_path'])), unsafe_allow_html=True)
            for _, row in a_history.iterrows():
                if row['image_path'] and os.path.exists(row['image_path']):
                    with st.expander(f"🖼️ Lihat Bukti Foto: {row['Alat']}"):
                        st.image(row['image_path'])

    
