import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import format_rp, render_luxury_table
import os
import json

def show_finance():
    st.markdown("## 🏛️ Pusat Keuangan & Budgeting")
    
    tab_alloc, tab_usage, tab_owner, tab_settings = st.tabs(["📊 Alokasi Dana", "💸 Pengajuan", "💎 Owner Intelligence", "⚙️ Konfigurasi"])

    conn = get_connection()
    alloc_df = pd.read_sql_query("SELECT room_name, target_pct FROM budget_allocation", conn)
    
    if alloc_df.empty:
        standards = [
            ('Bahan Baku (HPP)', 40.0), ('Kemasan & Ops POS', 5.0), 
            ('R&D (Riset Produk)', 5.0), ('Waste & Loss Reserve', 5.0), 
            ('Operational (Gaji, Listrik)', 25.0), ('Laba Bersih (Owner)', 20.0)
        ]
        for name, pct in standards:
            conn.execute("INSERT INTO budget_allocation (room_name, target_pct) VALUES (?,?)", (name, pct))
        conn.commit()
        alloc_df = pd.read_sql_query("SELECT room_name, target_pct FROM budget_allocation", conn)
    
    total_sales = conn.execute("SELECT SUM(total_revenue) FROM sales_log").fetchone()[0] or 0
    conn.close()

    # --- TAB 1: ALOKASI DANA ---
    with tab_alloc:
        st.markdown("### 📊 Simulasi Aliran Dana (Setiap Penjualan 100%)")
        st.info(f"Total Omzet Terkumpul: **{format_rp(total_sales)}**")
        
        cols = st.columns(3)
        for idx, row in alloc_df.iterrows():
            with cols[idx % 3]:
                room_money = (row['target_pct'] / 100) * total_sales
                c = get_connection()
                spent = c.execute("SELECT SUM(amount) FROM budget_usage_log WHERE room_name=?", (row['room_name'],)).fetchone()[0] or 0
                c.close()
                st.metric(row['room_name'], f"{row['target_pct']}%", delta=f"Sisa: {format_rp(room_money - spent)}", delta_color="normal")
                st.progress(max(0.0, min(1.0, (room_money - spent) / room_money)) if room_money > 0 else 0)

    # --- TAB 2: PENGAJUAN PENGELUARAN ---
    with tab_usage:
        st.subheader("💸 Ajukan Pengeluaran Dana")
        with st.form("usage_form"):
            u_room = st.selectbox("Gunakan Budget Dari Kamar:", alloc_df['room_name'].tolist())
            u_amount = st.number_input("Jumlah Pengeluaran (Rp)", min_value=0.0)
            u_desc = st.text_input("Keterangan")
            if st.form_submit_button("AJUKAN DANA"):
                if u_amount > 0 and u_desc:
                    payload = {"room": u_room, "amount": u_amount, "desc": u_desc}
                    c = get_connection()
                    c.execute("INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason) VALUES (?,?,?,?,?,?)",
                             (pd.Timestamp.now(), st.session_state.user, "PENGELUARAN_DANA", f"Dana dari {u_room}: {format_rp(u_amount)}", json.dumps(payload), u_desc))
                    c.commit(); c.close(); st.success("Pengajuan Terkirim!"); st.rerun()
        
        st.write("---")
        c = get_connection()
        logs = pd.read_sql_query("SELECT timestamp, room_name, amount, description FROM budget_usage_log ORDER BY timestamp DESC LIMIT 10", c)
        c.close()
        if not logs.empty:
            st.markdown(render_luxury_table(logs), unsafe_allow_html=True)

    # --- TAB 3: OWNER INTELLIGENCE ---
    with tab_owner:
        st.markdown("### 💎 Executive Profit Monitoring")
        c = get_connection()
        this_week = c.execute("SELECT SUM(total_revenue) FROM sales_log WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'").fetchone()[0] or 0
        last_week = c.execute("SELECT SUM(total_revenue) FROM sales_log WHERE timestamp < CURRENT_DATE - INTERVAL '7 days' AND timestamp >= CURRENT_DATE - INTERVAL '14 days'").fetchone()[0] or 0
        
        p_row = c.execute("SELECT target_pct FROM budget_allocation WHERE room_name = 'Laba Bersih (Owner)'").fetchone()
        profit_pct = p_row[0] if p_row else 20.0
        total_rev = c.execute("SELECT SUM(total_revenue) FROM sales_log").fetchone()[0] or 0
        total_tkn = c.execute("SELECT SUM(amount) FROM budget_usage_log WHERE room_name = 'Laba Bersih (Owner)'").fetchone()[0] or 0
        
        current_profit = (profit_pct/100 * total_rev) - total_tkn
        
        col1, col2 = st.columns(2)
        growth = ((this_week - last_week) / last_week * 100) if last_week > 0 else 0
        col1.metric("Omzet 7 Hari Terakhir", format_rp(this_week), delta=f"{growth:.1f}%")
        col2.metric("Saldo Laba Siap Tarik", format_rp(current_profit), delta="💰", delta_color="normal")
        
        st.write("---")
        with st.form("withdraw"):
            amt = st.number_input("Jumlah Penarikan Laba (Rp)", min_value=0.0, max_value=float(max(0, current_profit)))
            if st.form_submit_button("TARIK LABA SEKARANG"):
                if amt > 0:
                    c.execute("INSERT INTO budget_usage_log (timestamp, room_name, amount, description) VALUES (?,?,?,?)",
                             (pd.Timestamp.now(), "Laba Bersih (Owner)", amt, "Penarikan Laba oleh Owner"))
                    c.commit(); st.success("Penarikan Berhasil!"); st.rerun()
        c.close()

    # --- TAB 4: CONFIG ---
    with tab_settings:
        st.subheader("⚙️ Konfigurasi Strategi")
        if st.button("RESET KE STANDAR NEAR BAKERY"):
            c = get_connection()
            standards = [('Bahan Baku (HPP)', 40.0), ('Kemasan & Ops POS', 5.0), ('R&D (Riset Produk)', 5.0), ('Waste & Loss Reserve', 5.0), ('Operational (Gaji, Listrik)', 25.0), ('Laba Bersih (Owner)', 20.0)]
            for n, p in standards: c.execute("UPDATE budget_allocation SET target_pct=? WHERE room_name=?", (p, n))
            c.commit(); c.close(); st.rerun()
