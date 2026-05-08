import streamlit as st
import pandas as pd
from datetime import datetime
from database_engine import get_connection
from utils import format_rp, UNITS_MASTER
import json

def show_rd():
    
    st.markdown("## 🧪 Eksperimen & Research and Development (R&D)")
    
    conn = get_connection()
    # Get R&D Budget room target vs actual
    res_b = conn.execute("SELECT target_pct FROM budget_allocation WHERE room_name = 'R&D (Riset Produk)'").fetchone()
    target_pct = res_b[0] if res_b else 5.0
    total_sales = conn.execute("SELECT SUM(total_revenue) FROM sales_log").fetchone()[0] or 0
    budget_val = (target_pct / 100) * total_sales
    
    actual = conn.execute("SELECT SUM(amount) FROM budget_usage_log WHERE room_name = 'R&D (Riset Produk)'").fetchone()[0] or 0
    conn.close()
    
    st.markdown(f"#### 🛡️ Status Budget R&D: {format_rp(actual)} / {format_rp(budget_val)}")
    st.progress(min(1.0, actual/budget_val if budget_val > 0 else 0))
    
    with st.expander("➕ Ajukan Eksperimen Baru (Uji Coba Menu)"):
        st.info("Setiap riset yang menggunakan bahan baku harus disetujui Owner sebelum stok dipotong.")
        trial_name = st.text_input("Nama Eksperimen (Contoh: Croissant Trial v2)")
        
        conn = get_connection()
        inv_list = pd.read_sql_query("SELECT id, name, unit_pakai, price_per_unit_pakai FROM inventory_master", conn)
        conn.close()
        
        if 'temp_rd' not in st.session_state:
            st.session_state.temp_rd = [{'material': '', 'qty': 0.0, 'unit': ''}]
            
        total_trial_cost = 0
        for i, item in enumerate(st.session_state.temp_rd):
            c_m, c_q, c_u, c_d = st.columns([3, 1, 1, 0.5])
            item['material'] = c_m.selectbox(f"Bahan #{i+1}", [""] + inv_list['name'].tolist(), key=f"rd_m_{i}")
            item['qty'] = c_q.number_input("Qty", key=f"rd_q_{i}", min_value=0.0)
            
            default_unit = ""
            price_gudang = 0
            if item['material']:
                row = inv_list[inv_list['name'] == item['material']].iloc[0]
                default_unit = row['unit_pakai']
                price_gudang = row['price_per_unit_pakai']
            
            item['unit'] = c_u.selectbox(f"Satuan #{i}", UNITS_MASTER, index=UNITS_MASTER.index(default_unit) if default_unit in UNITS_MASTER else 0, key=f"rd_u_{i}")
            
            q_conv = item['qty']
            if item['unit'] == "Kilogram (Kg)" and default_unit == "Gram (gr)": q_conv *= 1000
            elif item['unit'] == "Gram (gr)" and default_unit == "Kilogram (Kg)": q_conv /= 1000
            
            total_trial_cost += q_conv * price_gudang
            if c_d.button("🗑️", key=f"rd_del_{i}"):
                st.session_state.temp_rd.pop(i); st.rerun()
                
        if st.button("➕ Tambah Baris Bahan R&D"):
            st.session_state.temp_rd.append({'material': '', 'qty': 0.0, 'unit': ''}); st.rerun()
            
        st.write("---")
        st.subheader(f"Total Biaya Eksperimen: {format_rp(total_trial_cost)}")
        reason = st.text_input("Alasan/Tujuan Riset (Wajib untuk Approval)")
        
        if st.button("🚀 AJUKAN RISET KE OWNER", type="primary", use_container_width=True):
            if trial_name and reason and any(it['material'] != '' for it in st.session_state.temp_rd):
                ings_payload = []
                for it in st.session_state.temp_rd:
                    if it['material']:
                        row = inv_list[inv_list['name'] == it['material']].iloc[0]
                        q_c = it['qty']
                        d_u = row['unit_pakai']
                        if it['unit'] == "Kilogram (Kg)" and d_u == "Gram (gr)": q_c *= 1000
                        elif it['unit'] == "Gram (gr)" and d_u == "Kilogram (Kg)": q_c /= 1000
                        ings_payload.append({'inv_id': int(row['id']), 'qty': q_c, 'name': it['material']})
                
                payload = {"name": trial_name, "cost": total_trial_cost, "ingredients": ings_payload}
                
                conn = get_connection()
                conn.execute("""
                    INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason)
                    VALUES (?,?,?,?,?,?)
                """, (datetime.now(), st.session_state.user, "RISET_PRODUK", 
                     f"Riset Menu: {trial_name} (Estimasi Biaya: {format_rp(total_trial_cost)})", 
                     json.dumps(payload), reason))
                conn.commit(); conn.close()
                st.info("Pengajuan Riset terkirim ke Owner."); st.session_state.temp_rd = [{'material': '', 'qty': 0.0, 'unit': ''}]; st.rerun()

    st.write("---")
    st.subheader("📋 Riwayat Eksperimen yang Disetujui")
    conn = get_connection()
    rd_history = pd.read_sql_query("SELECT * FROM rd_trials ORDER BY timestamp DESC", conn)
    conn.close()
    if not rd_history.empty:
        for _, trial in rd_history.iterrows():
            with st.expander(f"🔬 {trial['name']} | {format_rp(trial['total_cost'])} | {trial['timestamp']}"):
                conn = get_connection()
                ings = pd.read_sql_query("SELECT i.name, ri.qty_pakai, i.unit_pakai FROM rd_trial_ingredients ri JOIN inventory_master i ON ri.inventory_id = i.id WHERE ri.trial_id = ?", conn, params=(trial['id'],))
                conn.close(); st.table(ings)
    else: st.info("Belum ada riwayat eksperimen.")
    
