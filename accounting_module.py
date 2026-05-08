import streamlit as st
import pandas as pd
from database_engine import get_connection
from utils import render_luxury_table, format_rp

def show_accounting():
    
    st.markdown("## 📊 Analisis & Keamanan Data (Audit Trail)")
    
    tab_report, tab_inbox, tab_audit = st.tabs(["📈 Laporan Penjualan", "📩 Inbox Pelanggan", "🔒 Audit Trail & Keamanan"])
    
    # --- TAB: INBOX PELANGGAN ---
    with tab_inbox:
        st.subheader("📬 Pesan dari Website Online")
        conn = get_connection()
        msg_df = pd.read_sql_query("SELECT * FROM customer_messages ORDER BY timestamp DESC", conn)
        
        if not msg_df.empty:
            st.markdown(render_luxury_table(msg_df), unsafe_allow_html=True)
            
            st.write("---")
            sel_msg = st.selectbox("Pilih Pesan untuk Ditandai 'Selesai/Dibaca'", ["None"] + msg_df['id'].tolist())
            if sel_msg != "None":
                if st.button("✅ TANDAI SUDAH DIBACA"):
                    conn.execute("UPDATE customer_messages SET status = 'READ' WHERE id = ?", (sel_msg,))
                    conn.commit()
                    st.success("Pesan diperbarui!")
                    st.rerun()
        else:
            st.info("Kotak masuk kosong. Belum ada pesan dari pelanggan.")
        conn.close()
    
    # --- TAB 1: LAPORAN ---
    with tab_report:
        st.subheader("💰 Ringkasan Penjualan")
        conn = get_connection()
        sales_df = pd.read_sql_query("SELECT id, timestamp, total_revenue, total_hpp, profit, payment_method FROM sales_log ORDER BY timestamp DESC", conn)
        conn.close()
        
        if not sales_df.empty:
            # Stats
            t_rev = sales_df['total_revenue'].sum()
            t_prof = sales_df['profit'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Omzet", format_rp(t_rev))
            c2.metric("Total Profit Bersih", format_rp(t_prof))
            c3.metric("Margin Rata-rata", f"{(t_prof/t_rev*100):.1f}%" if t_rev > 0 else "0%")
            
            st.write("---")
            st.markdown("#### 📜 Detail Transaksi")
            
            # Action: Delete Transaction with Audit
            sel_id = st.selectbox("Pilih ID Transaksi untuk Dihapus (ADMIN ONLY)", ["None"] + sales_df['id'].tolist())
            if sel_id != "None":
                reason = st.text_input("Alasan Penghapusan (Wajib untuk Persetujuan Owner)")
                if st.button("🚨 AJUKAN PENGHAPUSAN KE OWNER"):
                    if reason:
                        import json
                        conn = get_connection()
                        # Get old data info
                        old_data = conn.execute("SELECT * FROM sales_log WHERE id=?", (sel_id,)).fetchone()
                        payload = {"sales_id": sel_id, "amount": old_data[2]}
                        
                        # Request Approval instead of direct delete
                        conn.execute("""
                            INSERT INTO pending_approvals (timestamp, user_requester, action_type, description, data_payload, reason)
                            VALUES (?,?,?,?,?,?)
                        """, (pd.Timestamp.now(), st.session_state.user, "HAPUS_TRANSAKSI", 
                             f"Menghapus Transaksi ID: {sel_id} (Nilai: {format_rp(old_data[2])})", 
                             json.dumps(payload), reason))
                        
                        conn.commit(); conn.close()
                        st.info("Permintaan penghapusan telah dikirim ke Pusat Persetujuan Owner."); st.rerun()
                    else:
                        st.warning("Mohon isi alasan penghapusan.")

            st.markdown(render_luxury_table(sales_df.head(20)), unsafe_allow_html=True)
        else:
            st.info("Belum ada data penjualan.")

    # --- TAB 2: AUDIT TRAIL ---
    with tab_audit:
        st.subheader("🔒 Log Keamanan Sistem")
        st.info("Setiap perubahan harga bahan baku atau penghapusan transaksi tercatat di sini.")
        
        conn = get_connection()
        audit_df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn)
        conn.close()
        
        if not audit_df.empty:
            st.markdown(render_luxury_table(audit_df), unsafe_allow_html=True)
        else:
            st.info("Belum ada aktivitas audit yang tercatat.")
            
    
